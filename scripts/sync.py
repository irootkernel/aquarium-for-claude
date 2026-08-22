#!/usr/bin/env python3
"""Generate the Claude Code plugin from the pinned upstream Codex plugin.

The upstream repository at `upstream/` is the single source of truth. This
script performs a deterministic transformation into `plugins/aquarium/`,
which is committed so the plugin installs even when the submodule is absent.

Run `sync.py` to regenerate, or `sync.py --check` to fail on drift.
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
UPSTREAM = REPOSITORY / "upstream"
UPSTREAM_PLUGIN = UPSTREAM / "plugins" / "aquarium"
OUTPUT = REPOSITORY / "plugins" / "aquarium"
OVERRIDES = REPOSITORY / "overrides"
OVERRIDE_MANIFEST = OVERRIDES / "manifest.json"
CODEX_EXEMPTIONS = OVERRIDES / "codex-exemptions.json"
SYNC_MANIFEST = "sync-manifest.json"

COPIED_DIRECTORIES = ("skills", "references", "assets", "hooks")
TEXT_SUFFIXES = (".md",)
SCRIPT_SUFFIXES = (".py",)
DATA_SUFFIXES = (".json",)
# Everything copied that host-specific text could hide in. `.yaml` is scanned but
# never rewritten: the Podway procedure IDs are load-bearing identifiers, and the
# integration contract requires the installed copies to match these bytes.
SCANNED_SUFFIXES = TEXT_SUFFIXES + SCRIPT_SUFFIXES + DATA_SUFFIXES + (".yaml",)

# Ordered literal substitutions applied to copied Markdown. Order matters: a
# later rule must never rewrite text that an earlier rule already produced.
#
# `AGENTS.md` is deliberately absent. Upstream `dev-setup/SKILL.md` contains
# "Do not edit nested AGENTS.md, CLAUDE.md, ...", which a blanket rule would
# corrupt into "nested CLAUDE.md, CLAUDE.md". Instruction-file wording is
# handled by full-file overrides instead.
SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("$aquarium:", "/aquarium:"),
    # `$use-podway`, `$use-sanho`, `$use-mulgae`, `$use-gaori`. A prefix rule
    # covers the family and any later sibling; `/use-` cannot re-match it.
    ("$use-", "/use-"),
    ("$lore-commits", "/lore-commits"),
    ("$lore-query", "/lore-query"),
    ("$orca-cli", "/orca-cli"),
    # Ouroboros installs as a Claude Code plugin, so its skills carry the
    # `ouroboros:` namespace. Codex installs them user-scoped and addresses them
    # bare, which is why upstream writes `$interview` rather than a prefixed
    # form. Deslop installs user-scoped on both hosts and keeps a bare name.
    ("$interview", "/ouroboros:interview"),
    ("$deslop", "/deslop"),
    ("$seed", "/ouroboros:seed"),
    ("$pm", "/ouroboros:pm"),
    ("$qa", "/ouroboros:qa"),
    ("`request_user_input`", "`AskUserQuestion`"),
    ("Codex goal", "Claude Code todo list"),
    ("a fresh Codex reviewer", "a fresh independent reviewer"),
    ("one fresh Codex reviewer", "one fresh independent reviewer"),
    ("supervised Codex reviewer", "supervised independent reviewer"),
    ("a fresh Codex in the current", "a fresh independent reviewer in the current"),
    ("fresh Codex audit", "fresh from-scratch audit"),
    ("direct Codex audit", "direct from-scratch audit"),
    (" for Codex.", " for Claude Code."),
    # Ouroboros registers its skills with the host agent, so the component whose
    # health `dev-setup` establishes is the Claude Code one here. The bundle
    # skill names the same component in a list of Ouroboros setup mutations.
    ("Codex skill health", "Claude Code skill health"),
    (
        "Ouroboros package, Codex, and runtime components",
        "Ouroboros package, host integration, and runtime components",
    ),
    # Lora installs per host, so the catalog's scope wording and `--agent` value
    # both move. These phrases are long enough not to collide with the
    # instruction-file text handled by overrides.
    ("Configure it for Codex user-global scope.", "Configure it for the Claude Code user-global scope."),
    ("--agent codex", "--agent claude-code"),
    ("the Codex user-global skill directory", "the Claude Code user-global skill directory"),
    # Singular form covers the plural; upstream v0.1.9 introduced "another
    # Codex skill root" alongside the existing "Codex skill roots".
    ("Codex skill root", "agent skill root"),
    ("a new Codex user-scoped", "a new user-scoped"),
    (
        "restart Codex so a new session loads the skill snapshot",
        "restart Claude Code so a new session loads the skill snapshot",
    ),
    (
        "restart Codex if the skill does not appear in the active session",
        "restart Claude Code if the skill does not appear in the active session",
    ),
    ("will not load until Codex restarts", "will not load until Claude Code restarts"),
    (
        "the full Lore protocol into AGENTS.md",
        "the full Lore protocol into the repository instruction file",
    ),
)

# Substitutions for bundled scripts. Kept separate from Markdown because
# `CODEX_HOME` is a real environment variable the generated script still reads:
# a Claude Code user may also have Codex skills installed.
SCRIPT_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    (
        '    codex_home = os.environ.get("CODEX_HOME")\n'
        "    if codex_home:\n"
        '        candidates.append(Path(codex_home).expanduser().joinpath("skills"))\n'
        "    candidates.extend(\n"
        '        [Path.home().joinpath(".codex/skills"), Path.home().joinpath(".agents/skills")]\n'
        "    )\n",
        '    for variable in ("CLAUDE_CONFIG_DIR", "CODEX_HOME"):\n'
        "        configured = os.environ.get(variable)\n"
        "        if configured:\n"
        '            candidates.append(Path(configured).expanduser().joinpath("skills"))\n'
        "    candidates.extend(\n"
        "        [\n"
        '            Path.home().joinpath(".claude/skills"),\n'
        '            Path.home().joinpath(".codex/skills"),\n'
        '            Path.home().joinpath(".agents/skills"),\n'
        "        ]\n"
        "    )\n",
    ),
    # `claude mcp get` reports a definite not-found as `No MCP server named
    # "<name>". Configured servers: ...`, which the Codex `... found.`
    # full-match rejects, degrading the missing case instead of naming it.
    (
        "        not_found = re.fullmatch(\n"
        "            r\"(?:Error:\\s*)?No MCP server named ['\\\"]?ouroboros['\\\"]? found\\.?\",\n"
        "            stderr,\n"
        "        )\n",
        "        not_found = re.match(\n"
        "            r\"No MCP server named ['\\\"]?[^'\\\"]+['\\\"]?\\.\",\n"
        "            stderr,\n"
        "        )\n",
    ),
    # The Codex probe returns typed JSON; the Claude one returns a rendered
    # block, so the enabled/disabled decision moves to its `Status:` line.
    (
        "    parsed = parse_json_probe(raw_probe)\n"
        "    if parsed.get(\"error_code\") == \"invalid_json\":\n"
        "        probe[\"error_code\"] = \"invalid_json\"\n"
        "        probe[\"reason\"] = \"registration_invalid_json\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "    result = parsed.get(\"result\")\n"
        "    if not isinstance(result, dict):\n"
        "        probe[\"reason\"] = \"registration_result_invalid\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "    if result.get(\"enabled\") is True:\n"
        "        return {\"status\": \"configured\", \"probe\": probe}\n"
        "    if result.get(\"enabled\") is False:\n"
        "        probe[\"reason\"] = \"registration_disabled\"\n"
        "    elif \"enabled\" not in result:\n"
        "        probe[\"reason\"] = \"registration_enabled_missing\"\n"
        "    else:\n"
        "        probe[\"reason\"] = \"registration_enabled_invalid\"\n"
        "    return {\"status\": \"degraded\", \"probe\": probe}\n"
        "\n",
        "    # `claude mcp get` prints a human-readable block rather than typed JSON, so\n"
        "    # the registration is read from its `Status:` line. A server that resolves\n"
        "    # but cannot connect is registered and unhealthy, not unregistered.\n"
        "    status_line = \"\"\n"
        "    for line in raw_probe.get(\"stdout\", \"\").splitlines():\n"
        "        stripped = line.strip()\n"
        "        if stripped.startswith(\"Status:\"):\n"
        "            status_line = stripped\n"
        "            break\n"
        "    if not status_line:\n"
        "        probe[\"reason\"] = \"registration_status_missing\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "    if \"Connected\" in status_line:\n"
        "        return {\"status\": \"configured\", \"probe\": probe}\n"
        "    probe[\"reason\"] = \"registration_not_connected\"\n"
        "    return {\"status\": \"degraded\", \"probe\": probe}\n",
    ),
    # Upstream probes Codex for the Ouroboros MCP registration, so on Claude
    # Code the component could never report `configured` and every design
    # skill stayed blocked. Ouroboros registers its Claude MCP server through
    # its own plugin, which is what this probes instead.
    (
        "    codex = shutil.which(\"codex\")\n"
        "    if codex:\n"
        "        registration_raw = run_command(\n"
        "            [\n"
        "                str(Path(codex).resolve()),\n"
        "                \"mcp\",\n"
        "                \"get\",\n"
        "                \"ouroboros\",\n"
        "                \"--json\",\n"
        "            ],\n"
        "            repository,\n"
        "            timeout_seconds,\n"
        "        )\n"
        "        tool[\"mcp_registration\"] = classify_ouroboros_registration(\n"
        "            registration_raw\n"
        "        )\n"
        "    else:\n"
        "        tool[\"mcp_registration\"] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"probe\": skipped_probe(\"codex_executable_missing\"),\n"
        "        }\n",
        "    claude = shutil.which(\"claude\")\n"
        "    if claude:\n"
        "        # Ouroboros ships its Claude Code integration as a plugin, so the MCP\n"
        "        # server it registers is plugin-scoped. Whether that name resolves at all\n"
        "        # is the integration signal, because it proves the plugin is installed\n"
        "        # and enabled and therefore that the `/ouroboros:*` skills the design\n"
        "        # workflows call are present. Those skills do not need the server, so a\n"
        "        # resolved-but-unhealthy entry degrades the registration, not the\n"
        "        # integration. A bare `ouroboros` entry proves only that some MCP server\n"
        "        # was registered by hand, which leaves the skills unaccounted for.\n"
        "        claude_executable = str(Path(claude).resolve())\n"
        "        plugin_scoped = classify_ouroboros_registration(\n"
        "            run_command(\n"
        "                [claude_executable, \"mcp\", \"get\", \"plugin:ouroboros:ouroboros\"],\n"
        "                repository,\n"
        "                timeout_seconds,\n"
        "            )\n"
        "        )\n"
        "        if plugin_scoped[\"status\"] == \"missing\":\n"
        "            direct = classify_ouroboros_registration(\n"
        "                run_command(\n"
        "                    [claude_executable, \"mcp\", \"get\", \"ouroboros\"],\n"
        "                    repository,\n"
        "                    timeout_seconds,\n"
        "                )\n"
        "            )\n"
        "            tool[\"mcp_registration\"] = direct\n"
        "            host_integration = {\n"
        "                \"status\": \"unverifiable\"\n"
        "                if direct[\"status\"] == \"configured\"\n"
        "                else \"missing\",\n"
        "                \"probe\": plugin_scoped[\"probe\"],\n"
        "            }\n"
        "        else:\n"
        "            tool[\"mcp_registration\"] = plugin_scoped\n"
        "            host_integration = {\n"
        "                \"status\": \"configured\",\n"
        "                \"probe\": {\n"
        "                    key: value\n"
        "                    for key, value in plugin_scoped[\"probe\"].items()\n"
        "                    if key != \"reason\"\n"
        "                },\n"
        "            }\n"
        "    else:\n"
        "        tool[\"mcp_registration\"] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"probe\": skipped_probe(\"claude_executable_missing\"),\n"
        "        }\n"
        "        host_integration = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"probe\": skipped_probe(\"claude_executable_missing\"),\n"
        "        }\n",
    ),
    # `ooo codex doctor` has no Claude Code counterpart, so the integration
    # component is taken from the plugin-scoped registration above.
    (
        "    codex_doctor = run_command(\n"
        "        [tool[\"executable\"], \"codex\", \"doctor\"], repository, timeout_seconds\n"
        "    )\n"
        "    tool[\"codex_integration\"] = {\n"
        "        \"status\": \"configured\" if codex_doctor[\"ok\"] else \"degraded\",\n"
        "        \"probe\": {\n"
        "            key: codex_doctor[key]\n"
        "            for key in (\"attempted\", \"ok\", \"exit_code\", \"timed_out\")\n"
        "        },\n"
        "    }\n",
        "    # `ooo codex doctor` verifies another host's routing artifacts and has no\n"
        "    # Claude Code counterpart. The plugin-scoped registration resolved above is\n"
        "    # the host-integration signal here, so it is recorded rather than reprobed.\n"
        "    tool[\"host_integration\"] = host_integration\n",
    ),
    # The reported component is the host's own integration here, not Codex's.
    (
        "        tool[\"codex_integration\"] = {\n"
        "            \"status\": \"missing\",\n"
        "            \"probe\": skipped_probe(\"executable_missing\"),\n"
        "        }\n",
        "        tool[\"host_integration\"] = {\n"
        "            \"status\": \"missing\",\n"
        "            \"probe\": skipped_probe(\"executable_missing\"),\n"
        "        }\n",
    ),
    # ...and the readiness rollup reads the renamed component.
    (
        "        and tool[\"codex_integration\"][\"status\"] == \"configured\"\n",
        "        and tool[\"host_integration\"][\"status\"] == \"configured\"\n",
    ),
    # Upstream reads this component from the doctor's exit code, which cannot
    # succeed on a host whose MCP 2 server lives outside the CLI environment.
    (
        "    tool[\"mcp_runtime\"] = {\n"
        "        \"status\": \"configured\" if mcp_doctor[\"ok\"] else \"degraded\",\n"
        "        \"probe\": normalized_probe(mcp_doctor),\n"
        "    }\n",
        "    # `ooo mcp doctor` reports the CLI's own environment. This host deliberately\n"
        "    # keeps MCP 1.x there while the plugin launches the MCP 2 server in an\n"
        "    # isolated process, so its `mcp_import` check \u2014 and the exit code with it \u2014\n"
        "    # fails on a correctly configured machine. The remaining checks carry runtime\n"
        "    # health here; the server's own health is the registration component.\n"
        "    doctor_checks = mcp_doctor.get(\"result\")\n"
        "    runtime_probe = normalized_probe(mcp_doctor)\n"
        "    if isinstance(doctor_checks, list):\n"
        "        failed = sorted(\n"
        "            str(check.get(\"name\"))\n"
        "            for check in doctor_checks\n"
        "            if isinstance(check, dict)\n"
        "            and check.get(\"status\") == \"fail\"\n"
        "            and check.get(\"name\") != \"mcp_import\"\n"
        "        )\n"
        "        if failed:\n"
        "            runtime_probe[\"reason\"] = \"doctor_checks_failed\"\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"degraded\" if failed else \"configured\",\n"
        "            \"failed_checks\": failed,\n"
        "            \"probe\": runtime_probe,\n"
        "        }\n"
        "    else:\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"degraded\",\n"
        "            \"probe\": runtime_probe,\n"
        "        }\n",
    ),
    # `hooks/task_commit_gate.py` names the remediation skill in the text the
    # user sees when a commit is denied. Markdown rules do not reach `.py`.
    ("$aquarium:", "/aquarium:"),
)

# Substitutions for copied JSON. Claude Code expands `${CLAUDE_PLUGIN_ROOT}`;
# `PLUGIN_ROOT` is a Codex-only spelling. Left alone, the shell expands it to
# nothing, `python3` cannot open `/hooks/task_commit_gate.py`, and it exits 2 —
# which PreToolUse reads as an unconditional deny. The bundled hook would then
# block every Bash call in every repository, so this rule is load-bearing.
DATA_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_ROOT}"),
)

# Text that must exist after transformation. A script substitution that quietly
# stops matching would otherwise ship a script searching only Codex paths, and
# the Markdown forbidden-check cannot see it.
REQUIRED_TEXT: tuple[tuple[str, str], ...] = (
    ("skills/dev-setup/scripts/inspect_tools.py", "CLAUDE_CONFIG_DIR"),
    ("skills/dev-setup/scripts/inspect_tools.py", '".claude/skills"'),
    # The Ouroboros probes are a multi-line block match, so a reformat upstream
    # would stop them matching and silently restore the Codex-only inspection.
    ("skills/dev-setup/scripts/inspect_tools.py", "plugin:ouroboros:ouroboros"),
    ("skills/dev-setup/scripts/inspect_tools.py", '"host_integration"'),
    ("skills/dev-setup/scripts/inspect_tools.py", "doctor_checks_failed"),
    ("hooks/hooks.json", "${CLAUDE_PLUGIN_ROOT}"),
    ("hooks/task_commit_gate.py", "/aquarium:task-commit"),
)

# Strings that must not survive into the generated tree. Each entry pairs a
# needle with the remedy, so a failure names its own fix.
FORBIDDEN: tuple[tuple[str, str], ...] = (
    ("$aquarium:", "add a substitution rule"),
    ("$use-", "add a substitution rule"),
    ("$lore-", "add a substitution rule"),
    ("$orca-cli", "add a substitution rule"),
    ("request_user_input", "add a substitution rule or an override"),
    ("--agent codex", "add an override"),
    ("${PLUGIN_ROOT}", "Claude Code expands ${CLAUDE_PLUGIN_ROOT}; add a data substitution"),
    ("Codex", "add a substitution rule, an override, or a reviewed exemption"),
)

# Every lowercase `$name` in upstream Markdown is a Codex skill invocation.
# `FORBIDDEN` names one needle per sigil family that already exists, so a family
# upstream introduces later passes both the substitution table and the forbidden
# scan and ships Codex invocation syntax to a Claude Code user in silence. That
# is how `$interview`, `$pm`, `$seed`, `$qa`, and `$deslop` arrived in v0.1.9.
# Uppercase spellings are environment variables the generated tree still needs
# (`${CLAUDE_PLUGIN_ROOT}`, `$CODEX_HOME`) and deliberately do not match.
SIGIL = re.compile(r"\$[a-z][a-z0-9:_-]*")


class SyncError(RuntimeError):
    """A condition that must stop generation rather than produce partial output."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upstream_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SyncError(
            "cannot resolve the upstream commit; run `git submodule update --init`"
        )
    return result.stdout.strip()


def require_upstream() -> None:
    """Refuse to generate from a missing or partially initialized submodule.

    Claude Code treats a failed submodule clone as non-fatal, so an empty
    `upstream/` is a realistic state. Generating from it would silently delete
    the committed plugin.
    """
    marker = UPSTREAM_PLUGIN / ".codex-plugin" / "plugin.json"
    if not marker.is_file():
        raise SyncError(
            f"upstream plugin not found at {marker}; "
            "run `git submodule update --init --recursive` before syncing"
        )
    for name in ("skills", "hooks"):
        if not (UPSTREAM_PLUGIN / name).is_dir():
            raise SyncError(f"upstream is missing `{name}/`; refusing to generate")
    check_upstream_directories()


def check_upstream_directories() -> None:
    """Refuse to generate when upstream grows a directory nobody decided about.

    `COPIED_DIRECTORIES` is an allowlist with no counterpart check, so `hooks/`
    appeared upstream and was dropped in silence. Whether a new directory belongs
    in a Claude artifact is a decision, and skipping it is not a safe default.
    """
    known = set(COPIED_DIRECTORIES) | {".codex-plugin"}
    unknown = sorted(
        path.name
        for path in UPSTREAM_PLUGIN.iterdir()
        if path.is_dir() and path.name not in known
    )
    if unknown:
        raise SyncError(
            "upstream has directories this transformation does not handle: "
            + ", ".join(unknown)
            + "; add them to COPIED_DIRECTORIES or exclude them deliberately"
        )


def apply_substitutions(text: str) -> str:
    for old, new in SUBSTITUTIONS:
        text = text.replace(old, new)
    return text


def read_sidecar_policy(skill: Path) -> bool:
    """Return `allow_implicit_invocation` for one upstream skill.

    The Codex sidecar is the single source of truth for invocation policy, so
    the Claude frontmatter flag cannot drift from it. A missing or malformed
    sidecar is an error: guessing a default would risk letting a mutating
    skill fire without the user asking for it.
    """
    sidecar = skill / "agents" / "openai.yaml"
    if not sidecar.is_file():
        raise SyncError(
            f"skill `{skill.name}` has no agents/openai.yaml; "
            "invocation policy cannot be derived and will not be guessed"
        )
    match = re.search(
        r"^\s*allow_implicit_invocation:\s*(true|false)\s*$",
        sidecar.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise SyncError(
            f"skill `{skill.name}` sidecar has no boolean allow_implicit_invocation"
        )
    return match.group(1) == "true"


def gate_frontmatter(text: str, skill_name: str, allow_implicit: bool) -> str:
    """Insert `disable-model-invocation: true` when implicit invocation is off.

    Claude Code has no analogue of the Codex sidecar, so the policy has to move
    into the frontmatter. Codex's own plugin validator rejects this key, which
    is precisely why the generated tree is a separate artifact.
    """
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise SyncError(f"skill `{skill_name}` has no frontmatter block")
    if allow_implicit:
        return text
    body = match.group(1)
    if "disable-model-invocation" in body:
        raise SyncError(f"skill `{skill_name}` already declares disable-model-invocation")
    return text.replace(
        match.group(0),
        f"---\n{body}\ndisable-model-invocation: true\n---\n",
        1,
    )


def copy_tree(destination: Path) -> None:
    for name in COPIED_DIRECTORIES:
        source = UPSTREAM_PLUGIN / name
        if source.is_dir():
            shutil.copytree(source, destination / name)


def transform_skills(destination: Path) -> None:
    skills = destination / "skills"
    for skill in sorted(p for p in skills.iterdir() if p.is_dir()):
        allow_implicit = read_sidecar_policy(UPSTREAM_PLUGIN / "skills" / skill.name)
        skill_md = skill / "SKILL.md"
        if not skill_md.is_file():
            raise SyncError(f"skill `{skill.name}` has no SKILL.md")
        skill_md.write_text(
            gate_frontmatter(skill_md.read_text(encoding="utf-8"), skill.name, allow_implicit),
            encoding="utf-8",
        )
        # The Codex sidecar has no meaning for Claude Code and its `$` prompts
        # would contradict the generated text, so it is dropped.
        shutil.rmtree(skill / "agents", ignore_errors=True)


def transform_text(destination: Path) -> None:
    for path in sorted(destination.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in TEXT_SUFFIXES:
            rules = SUBSTITUTIONS
        elif path.suffix in SCRIPT_SUFFIXES:
            rules = SCRIPT_SUBSTITUTIONS
        elif path.suffix in DATA_SUFFIXES:
            rules = DATA_SUBSTITUTIONS
        else:
            continue
        original = path.read_text(encoding="utf-8")
        replaced = original
        for old, new in rules:
            replaced = replaced.replace(old, new)
        if replaced != original:
            path.write_text(replaced, encoding="utf-8")


def check_required(destination: Path) -> None:
    missing: list[str] = []
    for relative, needle in REQUIRED_TEXT:
        path = destination / relative
        if not path.is_file():
            missing.append(f"  {relative}: file not generated")
        elif needle not in path.read_text(encoding="utf-8"):
            missing.append(f"  {relative}: missing `{needle}` — a substitution stopped matching")
    if missing:
        raise SyncError("required text is absent from the generated tree:\n" + "\n".join(missing))


def upstream_manifest() -> dict[str, Any]:
    return json.loads(
        (UPSTREAM_PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )


def load_override_manifest() -> dict[str, str]:
    if not OVERRIDE_MANIFEST.is_file():
        return {}
    return json.loads(OVERRIDE_MANIFEST.read_text(encoding="utf-8"))


def check_codex_exemptions() -> set[str]:
    """Return the paths whose remaining `Codex` mentions were reviewed and kept.

    Some upstream text names the Codex CLI as a third-party tool rather than as
    the host running the skill — a Mulgae provider, a required CLI version. That
    text is correct in a Claude artifact and cannot be renamed without making it
    false, but it still trips the `Codex` needle after an override is applied,
    because overrides do not exempt their own content.

    An exemption records that a human read every remaining mention in one file
    and confirmed each is third-party. That judgement holds only for the bytes it
    was made against, so an upstream edit stops the run instead of widening the
    exemption in silence.
    """
    if not CODEX_EXEMPTIONS.is_file():
        return set()
    recorded_all: dict[str, str] = json.loads(CODEX_EXEMPTIONS.read_text(encoding="utf-8"))
    for relative, recorded in sorted(recorded_all.items()):
        source = UPSTREAM_PLUGIN / relative
        if not source.is_file():
            raise SyncError(
                f"`Codex` exemption targets `{relative}`, which no longer exists "
                "upstream; remove the exemption or retarget it"
            )
        current = digest(source)
        if current != recorded:
            raise SyncError(
                f"`Codex` exemption stale: `{relative}` changed upstream\n"
                f"  recorded {recorded}\n"
                f"  current  {current}\n"
                "re-read every remaining `Codex` mention, confirm each still names "
                "the third-party CLI, then update overrides/codex-exemptions.json"
            )
    return set(recorded_all)


def apply_overrides(destination: Path) -> list[str]:
    """Replace files whose Claude form diverges semantically from upstream.

    Every override records the SHA-256 of the upstream file it was derived
    from. When upstream changes that file the override is stale, and merging
    it silently would ship guidance that no longer matches the source. That is
    the one failure mode that quietly breaks a fork, so it stops the run.
    """
    manifest = load_override_manifest()
    applied: list[str] = []
    for relative, recorded in sorted(manifest.items()):
        source = UPSTREAM_PLUGIN / relative
        override = OVERRIDES / relative
        if not override.is_file():
            raise SyncError(f"override file missing: {override}")
        if not source.is_file():
            raise SyncError(
                f"override targets `{relative}`, which no longer exists upstream; "
                "remove the override or retarget it"
            )
        current = digest(source)
        if current != recorded:
            raise SyncError(
                f"override stale: `{relative}` changed upstream\n"
                f"  recorded {recorded}\n"
                f"  current  {current}\n"
                "re-derive the override from the new upstream content, then update "
                "overrides/manifest.json"
            )
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(override, target)
        applied.append(relative)
    return applied


def write_plugin_manifest(destination: Path) -> None:
    """Derive the Claude manifest from the Codex one so versions cannot diverge."""
    codex = upstream_manifest()
    interface = codex.get("interface", {})
    manifest: dict[str, Any] = {
        "name": codex["name"],
        "displayName": interface.get("displayName", codex["name"]),
        "version": codex["version"],
        "description": apply_substitutions(codex["description"]),
        "author": codex["author"],
        "homepage": codex["homepage"],
        "repository": codex["repository"],
        "license": codex["license"],
        "keywords": codex["keywords"],
        "skills": "./skills/",
        "metadata": {
            "generatedFrom": codex["repository"],
            "brandColor": interface.get("brandColor"),
            "icon": interface.get("composerIcon"),
            "logo": interface.get("logo"),
            "privacyPolicyURL": interface.get("privacyPolicyURL"),
            "termsOfServiceURL": interface.get("termsOfServiceURL"),
        },
    }
    manifest["metadata"] = {k: v for k, v in manifest["metadata"].items() if v is not None}
    directory = destination / ".claude-plugin"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "plugin.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def check_forbidden(destination: Path, codex_exemptions: set[str]) -> None:
    """Scan every generated text file for host-specific text.

    Scripts and YAML are included. `CODEX_HOME` survives in the inspection script
    on purpose — a Claude Code user may also have Codex skills installed — and it
    is not a match, because the needle is `Codex` rather than `CODEX`.

    Only the `Codex` needle is skipped, and only for reviewed exemptions; every
    other needle applies to every file.
    """
    failures: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        relative = path.relative_to(destination)
        text = path.read_text(encoding="utf-8")
        for needle, remedy in FORBIDDEN:
            if needle == "Codex" and str(relative) in codex_exemptions:
                continue
            if needle in text:
                failures.append(f"  {relative}: contains `{needle}` — {remedy}")
    if failures:
        raise SyncError("host-specific text survived transformation:\n" + "\n".join(failures))


def check_sigils(destination: Path) -> None:
    """Fail on any Codex skill sigil that no substitution rule rewrote.

    This closes the class rather than the known instances: an unmapped sigil is
    a silent failure, because it is valid Markdown that simply names a command
    the reader's host does not have.
    """
    failures: list[str] = []
    for path in sorted(destination.rglob("*.md")):
        if not path.is_file():
            continue
        found = sorted(set(SIGIL.findall(path.read_text(encoding="utf-8"))))
        if found:
            failures.append(f"  {path.relative_to(destination)}: {', '.join(found)}")
    if failures:
        raise SyncError(
            "Codex skill sigils survived transformation:\n"
            + "\n".join(failures)
            + "\nadd a substitution rule naming each sigil's Claude form"
        )


def write_sync_manifest(
    destination: Path, repository: str, commit: str, overrides: list[str]
) -> None:
    files = {
        str(path.relative_to(destination)): digest(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name != SYNC_MANIFEST
    }
    payload = {
        "upstream": {
            "repository": repository,
            "commit": commit,
        },
        "overrides": overrides,
        "files": files,
    }
    (destination / SYNC_MANIFEST).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def generate(destination: Path) -> tuple[str, list[str]]:
    commit = upstream_commit()
    codex_exemptions = check_codex_exemptions()
    copy_tree(destination)
    transform_text(destination)
    # Overrides replace whole files, so they run before gating. Otherwise an
    # override would overwrite the frontmatter key and quietly reintroduce the
    # policy drift the sidecar is meant to prevent.
    overrides = apply_overrides(destination)
    transform_skills(destination)
    write_plugin_manifest(destination)
    check_forbidden(destination, codex_exemptions)
    check_sigils(destination)
    check_required(destination)
    write_sync_manifest(destination, upstream_manifest()["repository"], commit, overrides)
    return commit, overrides


def differences(left: Path, right: Path, prefix: Path = Path()) -> list[str]:
    comparison = filecmp.dircmp(str(left), str(right))
    found = [f"only in committed output: {prefix / name}" for name in sorted(comparison.left_only)]
    found += [f"only in regenerated output: {prefix / name}" for name in sorted(comparison.right_only)]
    found += [f"differs: {prefix / name}" for name in sorted(comparison.diff_files)]
    for name in sorted(comparison.common_dirs):
        found += differences(left / name, right / name, prefix / name)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed output matches a fresh regeneration",
    )
    arguments = parser.parse_args()

    try:
        require_upstream()
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "aquarium"
            staged.mkdir()
            commit, overrides = generate(staged)

            if arguments.check:
                if not OUTPUT.is_dir():
                    print("error: plugins/aquarium/ has not been generated", file=sys.stderr)
                    return 1
                drift = differences(OUTPUT, staged)
                if drift:
                    print("error: committed output is stale:", file=sys.stderr)
                    for entry in drift:
                        print(f"  {entry}", file=sys.stderr)
                    print("\nrun `python3 scripts/sync.py` and commit the result", file=sys.stderr)
                    return 1
                print(f"in sync with upstream {commit[:9]} ({len(overrides)} overrides)")
                return 0

            if OUTPUT.exists():
                shutil.rmtree(OUTPUT)
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(staged, OUTPUT)
    except SyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    skills = sorted(p.name for p in (OUTPUT / "skills").iterdir() if p.is_dir())
    gated = sum(
        1
        for name in skills
        if "disable-model-invocation: true" in (OUTPUT / "skills" / name / "SKILL.md").read_text(
            encoding="utf-8"
        )
    )
    print(f"generated {len(skills)} skills from upstream {commit[:9]}")
    print(f"  {gated} gated against model invocation, {len(skills) - gated} model-invocable")
    print(f"  {len(overrides)} overrides applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate the Claude Code plugin from the pinned upstream Codex plugin.

The upstream repository at `upstream/` is the single source of truth. This
script performs a deterministic transformation into `plugins/aquarium/`,
which is committed so the plugin installs even when the submodule is absent.

Run `sync.py` to regenerate, or `sync.py --check` to fail on drift.
"""

from __future__ import annotations

import argparse
import ast
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
ADDITIONS = REPOSITORY / "additions"
SYNC_MANIFEST = "sync-manifest.json"

COPIED_DIRECTORIES = ("skills", "references", "assets", "hooks")
TEXT_SUFFIXES = (".md",)
SCRIPT_SUFFIXES = (".py",)
DATA_SUFFIXES = (".json",)
# Everything copied that host-specific text could hide in. `.yaml` is scanned but
# never rewritten: the Podway procedure IDs are load-bearing identifiers, and the
# integration contract requires the installed copies to match these bytes.
SCANNED_SUFFIXES = TEXT_SUFFIXES + SCRIPT_SUFFIXES + DATA_SUFFIXES + (".yaml",)

# Files added to the generated tree that have no upstream counterpart. An
# explicit allowlist rather than a directory walk, so a stray file cannot ship
# by accident, and a path that collides with an upstream-derived file is an
# error: that case is what `overrides/` is for. There is no upstream digest to
# gate against, so additions pass through every check that scans copied text.
ADDED_PATHS: tuple[str, ...] = (
    # A plugin subagent Claude Code discovers from the plugin-root `agents/`
    # directory: the read-only Opus reviewer `independent-review` dispatches.
    "agents/independent-reviewer.md",
)

# Upstream files deliberately left out of the generated plugin. Each entry pairs
# the path with the reason it does not belong in a Claude Code artifact. The
# path must still exist upstream: an exclusion that quietly stops applying is
# the same failure class as a substitution rule that stops matching.
EXCLUDED_FILES: tuple[tuple[str, str], ...] = (
    (
        "assets/hero.png",
        "a 2.3 MB banner for the upstream repository README; upstream removed the "
        "manifest icon and logo fields in v0.1.10, so nothing in the plugin or in "
        "Claude Code's plugin UI can reference it",
    ),
)

# Ordered literal substitutions applied to copied Markdown. Order matters: a
# later rule must never rewrite text that an earlier rule already produced.
#
# Every rule must rewrite text that ships. Generation counts matches outside the
# override targets and fails on a rule that matched nothing, so a dead rule is
# deleted or re-derived deliberately instead of rotting: v0.1.10 dropped one
# Oxford comma and a rule stopped matching in silence, leaving `Codex` in a
# Claude artifact. Phrases that only ever occurred inside an override target
# were deleted for the same reason; the forbidden needles and the sigil scan
# still catch that text if an override is ever retired.
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
    ("fresh Codex audit", "fresh from-scratch audit"),
    # Ouroboros registers its skills with the host agent, so the component whose
    # health `dev-setup` establishes is the Claude Code one here. The bundle
    # skill names the same component in a list of Ouroboros setup mutations;
    # the anchor is the shortest unique phrase so the next punctuation edit
    # cannot break it again.
    ("Codex skill health", "Claude Code skill health"),
    ("Codex and runtime components", "host integration and runtime components"),
)

# Substitutions for bundled scripts, kept separate from Markdown because they
# rewrite executable behavior rather than prose. Skill discovery narrows to the
# Claude Code roots: this artifact diagnoses one host, and a copy sitting in
# another host's root is neither reachable here nor a duplicate of anything.
SCRIPT_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    (
        '    codex_home = os.environ.get("CODEX_HOME")\n'
        "    if codex_home:\n"
        '        candidates.append(Path(codex_home).expanduser().joinpath("skills"))\n'
        "    candidates.extend(\n"
        '        [Path.home().joinpath(".codex/skills"), Path.home().joinpath(".agents/skills")]\n'
        "    )\n",
        "    # Only Claude Code skill roots count here. A skill installed in\n"
        "    # another host's root is not reachable from this one, and counting it\n"
        "    # would report a cross-host copy as a duplicate installation and\n"
        "    # degrade a diagnosis that is about this host.\n"
        '    configured = os.environ.get("CLAUDE_CONFIG_DIR")\n'
        "    if configured:\n"
        '        candidates.append(Path(configured).expanduser().joinpath("skills"))\n'
        '    candidates.append(Path.home().joinpath(".claude/skills"))\n',
    ),
    # `claude mcp get` reports a definite not-found on stderr as `No MCP server
    # named "<name>". Configured servers: ...`, which carries neither the
    # `Error:` prefix nor the ` found.` tail the shared matcher requires, so the
    # missing case would degrade instead of naming itself. The rewrite stays
    # local to the Ouroboros call site: upstream v0.1.10 moved the regex into
    # `named_mcp_server_missing`, which the Mulgae and Gaori inspectors call as
    # well, and a helper-wide rewrite would change their classification too.
    (
        "        not_found = named_mcp_server_missing(raw_probe, \"ouroboros\")\n",
        "        # `claude mcp get` reports a definite not-found on stderr as `No MCP\n"
        "        # server named \"<name>\". Configured servers: ...`, without the `Error:`\n"
        "        # prefix or the ` found.` tail the shared matcher requires, so the\n"
        "        # missing case would degrade instead of naming itself. The match stays\n"
        "        # local to this call site because the shared helper also serves the\n"
        "        # Mulgae and Gaori inspectors.\n"
        "        not_found = bool(\n"
        "            raw_probe[\"exit_code\"] == 1\n"
        "            and not raw_probe[\"timed_out\"]\n"
        "            and not raw_probe.get(\"stdout\", \"\").strip()\n"
        "            and re.match(\n"
        "                r\"No MCP server named ['\\\"]?[^'\\\"]+['\\\"]?\\.\",\n"
        "                raw_probe.get(\"stderr\", \"\").strip(),\n"
        "            )\n"
        "        )\n",
    ),
    # The Codex probe returns typed JSON whose transport upstream now compares
    # against the discovered `ooo` executable; the Claude one returns a rendered
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
        "    transport = result.get(\"transport\")\n"
        "    command = transport.get(\"command\") if isinstance(transport, dict) else None\n"
        "    args = transport.get(\"args\") if isinstance(transport, dict) else None\n"
        "    resolved_command: Path | None = None\n"
        "    if isinstance(command, str) and command:\n"
        "        candidate = Path(command).expanduser()\n"
        "        if (\n"
        "            candidate.is_absolute()\n"
        "            and candidate.is_file()\n"
        "            and os.access(candidate, os.X_OK)\n"
        "        ):\n"
        "            resolved_command = candidate.resolve()\n"
        "        elif not candidate.is_absolute():\n"
        "            discovered = shutil.which(command)\n"
        "            if discovered:\n"
        "                resolved_command = Path(discovered).resolve()\n"
        "    registration_matches = bool(\n"
        "        result.get(\"name\") == \"ouroboros\"\n"
        "        and result.get(\"enabled\") is True\n"
        "        and isinstance(transport, dict)\n"
        "        and transport.get(\"type\") == \"stdio\"\n"
        "        and args == [\"mcp\", \"serve\"]\n"
        "        and resolved_command\n"
        "        and ouroboros_executable\n"
        "        and resolved_command == Path(ouroboros_executable).resolve()\n"
        "    )\n"
        "    if registration_matches:\n"
        "        return {\"status\": \"configured\", \"probe\": probe}\n"
        "    if result.get(\"enabled\") is True:\n"
        "        probe[\"reason\"] = \"registration_mismatch\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "    if result.get(\"enabled\") is False:\n"
        "        probe[\"reason\"] = \"registration_disabled\"\n"
        "    elif \"enabled\" not in result:\n"
        "        probe[\"reason\"] = \"registration_enabled_missing\"\n"
        "    else:\n"
        "        probe[\"reason\"] = \"registration_enabled_invalid\"\n"
        "    return {\"status\": \"degraded\", \"probe\": probe}\n",
        "    # `claude mcp get` prints a human-readable block rather than typed JSON, so\n"
        "    # the registration is read from its `Status:` line. A server that resolves\n"
        "    # but cannot connect is registered and unhealthy, not unregistered. The\n"
        "    # transport fields upstream verifies are absent for a plugin-scoped server,\n"
        "    # which prints only `Scope:` and `Status:`, so `ouroboros_executable` cannot\n"
        "    # be compared here.\n"
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
    # its own plugin, which is what this probes instead. The classifier keeps
    # its upstream arity, so `tool["executable"]` is passed at both call sites
    # even though the Claude classifier cannot use it.
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
        "            registration_raw, tool[\"executable\"]\n"
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
        "            ),\n"
        "            tool[\"executable\"],\n"
        "        )\n"
        "        if plugin_scoped[\"status\"] == \"missing\":\n"
        "            direct = classify_ouroboros_registration(\n"
        "                run_command(\n"
        "                    [claude_executable, \"mcp\", \"get\", \"ouroboros\"],\n"
        "                    repository,\n"
        "                    timeout_seconds,\n"
        "                ),\n"
        "                tool[\"executable\"],\n"
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
        "    # isolated process, so its `mcp_import` check — and the exit code with it —\n"
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
    # Upstream inspects the Mulgae and Gaori MCP registrations through the Codex
    # CLI: `codex mcp get --json` from a neutral cwd for the global view, the
    # same probe with `CODEX_HOME` pointed at `.codex/` for the local view, and
    # `.codex/config.toml` presence as the local gate. None of that exists on
    # Claude Code, so the catalog could tell the user to register a server the
    # inspector structurally could not see, and `--require-mulgae-mcp` degraded
    # the tool forever. The replacement reads the three Claude Code views from
    # configuration alone — user scope and the private per-project scope from
    # the user configuration, project scope from `.mcp.json` — and derives the
    # effective view from the documented precedence. It never calls
    # `claude mcp get`, which health-checks an approved server and so starts
    # it; setup must not start the server. Whole functions are replaced so the
    # anchors are the most stable text upstream has; the per-scope classifiers
    # upstream keeps become unreachable and stay untouched.
    (
        "def inspect_mulgae_mcp(\n"
        "    repository: Path, mulgae_executable: str | None, timeout_seconds: float\n"
        ") -> dict[str, Any]:\n"
        "    project_config_present, project_config_symlinked = safe_managed_file_state(\n"
        "        repository / \".codex\" / \"config.toml\", repository\n"
        "    )\n"
        "    registration: dict[str, Any] = {\n"
        "        \"status\": \"missing\",\n"
        "        \"preferred_scope\": \"global\",\n"
        "        \"effective_scope\": \"none\",\n"
        "        \"local_confirmation_required\": None,\n"
        "        \"codex_version\": None,\n"
        "    }\n"
        "    codex_executable = shutil.which(\"codex\")\n"
        "    if not codex_executable:\n"
        "        registration.update(\n"
        "            {\n"
        "                \"status\": \"unavailable\",\n"
        "                \"effective_scope\": \"unverifiable\",\n"
        "                \"reason\": \"codex_executable_missing\",\n"
        "                \"global\": {\"status\": \"unavailable\"},\n"
        "                \"local\": {\n"
        "                    \"status\": \"unverifiable\"\n"
        "                    if project_config_symlinked\n"
        "                    else \"unavailable\",\n"
        "                    \"project_config_present\": project_config_present,\n"
        "                    \"project_config_symlinked\": project_config_symlinked,\n"
        "                },\n"
        "            }\n"
        "        )\n"
        "        return registration\n"
        "    version_probe = run_command(\n"
        "        [codex_executable, \"--version\"], repository, timeout_seconds\n"
        "    )\n"
        "    if version_probe[\"ok\"]:\n"
        "        registration[\"codex_version\"] = codex_version_from_output(\n"
        "            version_probe[\"stdout\"]\n"
        "        )\n"
        "    neutral_cwd = Path(repository.anchor)\n"
        "    global_raw, global_probe = mcp_registration_probe(\n"
        "        codex_executable, \"mulgae\", neutral_cwd, timeout_seconds\n"
        "    )\n"
        "    global_registration = classify_mulgae_mcp_scope(\n"
        "        global_raw, global_probe, mulgae_executable, repository, \"global\"\n"
        "    )\n"
        "    if global_probe[\"ok\"]:\n"
        "        global_registration[\"_result\"] = global_probe.get(\"result\")\n"
        "\n"
        "    if project_config_symlinked:\n"
        "        local_registration = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"reason\": \"project_configuration_symlinked\",\n"
        "        }\n"
        "    elif not project_config_present:\n"
        "        local_registration = missing_mcp_scope(\"project_configuration_missing\")\n"
        "    else:\n"
        "        local_raw, local_probe = mcp_registration_probe(\n"
        "            codex_executable,\n"
        "            \"mulgae\",\n"
        "            neutral_cwd,\n"
        "            timeout_seconds,\n"
        "            {\"CODEX_HOME\": str(repository / \".codex\")},\n"
        "        )\n"
        "        local_registration = classify_mulgae_mcp_scope(\n"
        "            local_raw, local_probe, mulgae_executable, repository, \"local\"\n"
        "        )\n"
        "        if local_probe[\"ok\"]:\n"
        "            local_registration[\"_result\"] = local_probe.get(\"result\")\n"
        "    local_registration.update(\n"
        "        {\n"
        "            \"project_config_present\": project_config_present,\n"
        "            \"project_config_symlinked\": project_config_symlinked,\n"
        "        }\n"
        "    )\n"
        "\n"
        "    effective_raw, effective_probe = mcp_registration_probe(\n"
        "        codex_executable, \"mulgae\", repository, timeout_seconds\n"
        "    )\n"
        "    status, effective_scope, reason = effective_mcp_registration(\n"
        "        \"mulgae\",\n"
        "        global_registration,\n"
        "        local_registration,\n"
        "        project_config_symlinked,\n"
        "        effective_raw,\n"
        "        effective_probe,\n"
        "    )\n"
        "    global_registration.pop(\"_result\", None)\n"
        "    local_registration.pop(\"_result\", None)\n"
        "    local_confirmable = (\n"
        "        None if project_config_symlinked else local_registration[\"status\"] != \"missing\"\n"
        "    )\n"
        "    registration.update(\n"
        "        {\n"
        "            \"status\": status,\n"
        "            \"effective_scope\": effective_scope,\n"
        "            \"local_confirmation_required\": local_confirmable,\n"
        "            \"global\": global_registration,\n"
        "            \"local\": local_registration,\n"
        "            \"recommendation\": (\n"
        "                \"resolve_symlinked_local_configuration\"\n"
        "                if project_config_symlinked\n"
        "                else mcp_recommendation(\n"
        "                    global_registration[\"status\"],\n"
        "                    bool(local_confirmable),\n"
        "                )\n"
        "            ),\n"
        "        }\n"
        "    )\n"
        "    if reason:\n"
        "        registration[\"reason\"] = reason\n"
        "    return registration\n",
        "def claude_configuration_path() -> Path:\n"
        "    \"\"\"Return the Claude Code user configuration that holds MCP registrations.\n"
        "\n"
        "    User-scope servers live in its top-level `mcpServers`; a private per-project\n"
        "    registration lives under `projects.<absolute root>.mcpServers`; the approval\n"
        "    state of a shared `.mcp.json` server lives under the same project entry.\n"
        "    `CLAUDE_CONFIG_DIR` relocates the whole file.\n"
        "    \"\"\"\n"
        "    configured = os.environ.get(\"CLAUDE_CONFIG_DIR\")\n"
        "    root = Path(configured).expanduser() if configured else Path.home()\n"
        "    return root / \".claude.json\"\n"
        "\n"
        "\n"
        "def load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:\n"
        "    \"\"\"Read one JSON object, returning `(object, None)` or `(None, reason)`.\"\"\"\n"
        "    if path.is_symlink():\n"
        "        return None, \"symlinked\"\n"
        "    if not path.is_file():\n"
        "        return None, \"missing\"\n"
        "    try:\n"
        "        loaded = json.loads(path.read_text(encoding=\"utf-8\"))\n"
        "    except (OSError, UnicodeDecodeError):\n"
        "        return None, \"unreadable\"\n"
        "    except json.JSONDecodeError:\n"
        "        return None, \"invalid_json\"\n"
        "    if not isinstance(loaded, dict):\n"
        "        return None, \"invalid_json\"\n"
        "    return loaded, None\n"
        "\n"
        "\n"
        "def claude_version_from_output(output: str) -> str | None:\n"
        "    match = re.search(r\"(\\d+\\.\\d+\\.\\d+(?:[-+][0-9A-Za-z.-]+)?)\", output)\n"
        "    return match.group(1) if match else None\n"
        "\n"
        "\n"
        "def claude_mcp_arguments_match(\n"
        "    tool: str, scope: str, args: Any, repository: Path\n"
        ") -> tuple[bool, bool]:\n"
        "    \"\"\"Return `(arguments_match, repository_bound)` for one registration's `args`.\n"
        "\n"
        "    A user-scope server inherits each session's working directory and must not\n"
        "    pin a repository; a repository-scoped server binds the canonical root\n"
        "    through the tool's own flag, because a Claude Code stdio entry has no `cwd`.\n"
        "    \"\"\"\n"
        "    if not isinstance(args, list) or not all(isinstance(argument, str) for argument in args):\n"
        "        return False, scope == \"global\"\n"
        "    if scope == \"global\":\n"
        "        return args == [\"mcp\"], True\n"
        "    if tool == \"mulgae\":\n"
        "        bound_root = args[2] if len(args) == 3 and args[:2] == [\"mcp\", \"--project-root\"] else None\n"
        "    else:\n"
        "        bound_root = args[1] if len(args) == 3 and args[0] == \"--repo\" and args[2] == \"mcp\" else None\n"
        "    if bound_root is None:\n"
        "        return False, False\n"
        "    try:\n"
        "        repository_bound = Path(bound_root).expanduser().resolve() == repository\n"
        "    except OSError:\n"
        "        repository_bound = False\n"
        "    return repository_bound, repository_bound\n"
        "\n"
        "\n"
        "def classify_claude_mcp_entry(\n"
        "    tool: str,\n"
        "    entry: Any,\n"
        "    selected_executable: str | None,\n"
        "    repository: Path,\n"
        "    scope: str,\n"
        ") -> dict[str, Any]:\n"
        "    \"\"\"Classify one Claude Code MCP entry read from configuration.\n"
        "\n"
        "    Claude Code registrations carry only `command`, `args`, `env`, and an\n"
        "    optional `type`; there is no per-server `required` flag and no timeout\n"
        "    field, so those are reported as host concerns rather than as mismatches.\n"
        "    \"\"\"\n"
        "    if not isinstance(entry, dict):\n"
        "        return {\"status\": \"degraded\", \"reason\": \"invalid_registration_result\"}\n"
        "    transport_type = entry.get(\"type\", \"stdio\")\n"
        "    resolved_command = resolve_mcp_command(entry.get(\"command\"))\n"
        "    arguments_match, repository_bound = claude_mcp_arguments_match(\n"
        "        tool, scope, entry.get(\"args\", []), repository\n"
        "    )\n"
        "    binary_matches = bool(\n"
        "        resolved_command\n"
        "        and selected_executable\n"
        "        and resolved_command == Path(selected_executable).resolve()\n"
        "    )\n"
        "    registration = {\n"
        "        \"status\": \"degraded\",\n"
        "        \"enabled\": True,\n"
        "        \"stdio\": transport_type == \"stdio\",\n"
        "        \"repository_bound\": repository_bound,\n"
        "        \"arguments_match\": arguments_match,\n"
        "        \"command_resolvable\": resolved_command is not None,\n"
        "        \"binary_matches_selected\": binary_matches,\n"
        "        \"required_verification\": \"not_applicable\",\n"
        "        \"tool_timeout_sec\": None,\n"
        "        \"tool_timeout_source\": \"host\",\n"
        "    }\n"
        "    if registration[\"stdio\"] and arguments_match and binary_matches:\n"
        "        registration[\"status\"] = \"configured\"\n"
        "    else:\n"
        "        registration[\"reason\"] = \"registration_mismatch\"\n"
        "    return registration\n"
        "\n"
        "\n"
        "def claude_mcp_project_approval(project_state: Any, name: str) -> str:\n"
        "    \"\"\"Return `approved`, `disabled`, or `pending` for one `.mcp.json` server.\n"
        "\n"
        "    Claude Code records approval per project in the user configuration. The\n"
        "    keys are written only once touched, so an absent key means the default,\n"
        "    not an unknown state: nothing approved, nothing disabled.\n"
        "    \"\"\"\n"
        "    if not isinstance(project_state, dict):\n"
        "        return \"pending\"\n"
        "    disabled = project_state.get(\"disabledMcpjsonServers\", [])\n"
        "    enabled = project_state.get(\"enabledMcpjsonServers\", [])\n"
        "    if isinstance(disabled, list) and name in disabled:\n"
        "        return \"disabled\"\n"
        "    if project_state.get(\"enableAllProjectMcpServers\") is True:\n"
        "        return \"approved\"\n"
        "    if isinstance(enabled, list) and name in enabled:\n"
        "        return \"approved\"\n"
        "    return \"pending\"\n"
        "\n"
        "\n"
        "def inspect_claude_mcp(\n"
        "    tool: str, repository: Path, selected_executable: str | None, timeout_seconds: float\n"
        ") -> dict[str, Any]:\n"
        "    \"\"\"Inspect one tool's Claude Code MCP registration from configuration alone.\n"
        "\n"
        "    Three views are read without starting a server: the user-global entry and\n"
        "    the private per-project entry from the user configuration, and the shared\n"
        "    project entry from `.mcp.json`. The effective view follows Claude Code's\n"
        "    documented precedence, in which the private per-project entry shadows\n"
        "    `.mcp.json`, which shadows the user-global entry. `claude mcp get` is not\n"
        "    used because it health-checks an approved server, which starts it.\n"
        "    \"\"\"\n"
        "    project_config_present, project_config_symlinked = safe_managed_file_state(\n"
        "        repository / \".mcp.json\", repository\n"
        "    )\n"
        "    registration: dict[str, Any] = {\n"
        "        \"status\": \"missing\",\n"
        "        \"preferred_scope\": \"global\",\n"
        "        \"effective_scope\": \"none\",\n"
        "        \"effective_source\": \"configuration\",\n"
        "        \"local_confirmation_required\": None,\n"
        "        \"claude_version\": None,\n"
        "    }\n"
        "    claude_executable = shutil.which(\"claude\")\n"
        "    if claude_executable:\n"
        "        version_probe = run_command(\n"
        "            [claude_executable, \"--version\"], repository, timeout_seconds\n"
        "        )\n"
        "        if version_probe[\"ok\"]:\n"
        "            registration[\"claude_version\"] = claude_version_from_output(\n"
        "                version_probe[\"stdout\"]\n"
        "            )\n"
        "\n"
        "    user_configuration, user_reason = load_json_object(claude_configuration_path())\n"
        "    if user_configuration is None:\n"
        "        if user_reason == \"missing\":\n"
        "            global_registration = missing_mcp_scope(\"user_configuration_missing\")\n"
        "        else:\n"
        "            global_registration = {\n"
        "                \"status\": \"unverifiable\",\n"
        "                \"reason\": f\"user_configuration_{user_reason}\",\n"
        "            }\n"
        "        project_state: Any = None\n"
        "    else:\n"
        "        servers = user_configuration.get(\"mcpServers\")\n"
        "        entry = servers.get(tool) if isinstance(servers, dict) else None\n"
        "        global_registration = (\n"
        "            classify_claude_mcp_entry(tool, entry, selected_executable, repository, \"global\")\n"
        "            if entry is not None\n"
        "            else missing_mcp_scope()\n"
        "        )\n"
        "        projects = user_configuration.get(\"projects\")\n"
        "        project_state = projects.get(str(repository)) if isinstance(projects, dict) else None\n"
        "\n"
        "    private_servers = (\n"
        "        project_state.get(\"mcpServers\") if isinstance(project_state, dict) else None\n"
        "    )\n"
        "    private_entry = private_servers.get(tool) if isinstance(private_servers, dict) else None\n"
        "\n"
        "    if project_config_symlinked:\n"
        "        local_registration: dict[str, Any] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"reason\": \"project_configuration_symlinked\",\n"
        "        }\n"
        "    elif private_entry is not None:\n"
        "        local_registration = classify_claude_mcp_entry(\n"
        "            tool, private_entry, selected_executable, repository, \"local\"\n"
        "        )\n"
        "        local_registration[\"source\"] = \"local\"\n"
        "    elif not project_config_present:\n"
        "        local_registration = missing_mcp_scope(\"project_configuration_missing\")\n"
        "    else:\n"
        "        project_configuration, project_reason = load_json_object(repository / \".mcp.json\")\n"
        "        project_servers = (\n"
        "            project_configuration.get(\"mcpServers\")\n"
        "            if isinstance(project_configuration, dict)\n"
        "            else None\n"
        "        )\n"
        "        project_entry = (\n"
        "            project_servers.get(tool) if isinstance(project_servers, dict) else None\n"
        "        )\n"
        "        if project_configuration is None:\n"
        "            local_registration = {\n"
        "                \"status\": \"degraded\",\n"
        "                \"reason\": f\"project_configuration_{project_reason}\",\n"
        "            }\n"
        "        elif project_entry is None:\n"
        "            local_registration = missing_mcp_scope()\n"
        "        else:\n"
        "            local_registration = classify_claude_mcp_entry(\n"
        "                tool, project_entry, selected_executable, repository, \"local\"\n"
        "            )\n"
        "            local_registration[\"source\"] = \"project\"\n"
        "            approval = claude_mcp_project_approval(project_state, tool)\n"
        "            local_registration[\"approval\"] = approval\n"
        "            if approval == \"disabled\":\n"
        "                local_registration[\"status\"] = \"degraded\"\n"
        "                local_registration[\"reason\"] = \"registration_disabled\"\n"
        "            elif approval == \"pending\":\n"
        "                local_registration[\"status\"] = \"unverifiable\"\n"
        "                local_registration[\"reason\"] = \"registration_pending_approval\"\n"
        "    local_registration.update(\n"
        "        {\n"
        "            \"project_config_present\": project_config_present,\n"
        "            \"project_config_symlinked\": project_config_symlinked,\n"
        "            \"private_local_present\": private_entry is not None,\n"
        "        }\n"
        "    )\n"
        "\n"
        "    if project_config_symlinked:\n"
        "        status, effective_scope, reason = (\n"
        "            \"unverifiable\",\n"
        "            \"unverifiable\",\n"
        "            \"project_configuration_symlinked\",\n"
        "        )\n"
        "    elif local_registration[\"status\"] != \"missing\":\n"
        "        status, effective_scope, reason = (\n"
        "            local_registration[\"status\"],\n"
        "            \"local\",\n"
        "            local_registration.get(\"reason\"),\n"
        "        )\n"
        "    elif global_registration[\"status\"] != \"missing\":\n"
        "        status, effective_scope, reason = (\n"
        "            global_registration[\"status\"],\n"
        "            \"global\",\n"
        "            global_registration.get(\"reason\"),\n"
        "        )\n"
        "    else:\n"
        "        status, effective_scope, reason = \"missing\", \"none\", \"registration_not_found\"\n"
        "\n"
        "    local_confirmable = (\n"
        "        None if project_config_symlinked else local_registration[\"status\"] != \"missing\"\n"
        "    )\n"
        "    registration.update(\n"
        "        {\n"
        "            \"status\": status,\n"
        "            \"effective_scope\": effective_scope,\n"
        "            \"local_confirmation_required\": local_confirmable,\n"
        "            \"global\": global_registration,\n"
        "            \"local\": local_registration,\n"
        "            \"recommendation\": (\n"
        "                \"resolve_symlinked_local_configuration\"\n"
        "                if project_config_symlinked\n"
        "                else mcp_recommendation(\n"
        "                    global_registration[\"status\"],\n"
        "                    bool(local_confirmable),\n"
        "                )\n"
        "            ),\n"
        "        }\n"
        "    )\n"
        "    if reason:\n"
        "        registration[\"reason\"] = reason\n"
        "    return registration\n"
        "\n"
        "\n"
        "def inspect_mulgae_mcp(\n"
        "    repository: Path, mulgae_executable: str | None, timeout_seconds: float\n"
        ") -> dict[str, Any]:\n"
        "    return inspect_claude_mcp(\"mulgae\", repository, mulgae_executable, timeout_seconds)\n",
    ),
    (
        "def inspect_gaori_mcp(\n"
        "    repository: Path, gaori_executable: str | None, timeout_seconds: float\n"
        ") -> dict[str, Any]:\n"
        "    project_config_present, project_config_symlinked = safe_managed_file_state(\n"
        "        repository / \".codex\" / \"config.toml\", repository\n"
        "    )\n"
        "    registration: dict[str, Any] = {\n"
        "        \"status\": \"missing\",\n"
        "        \"preferred_scope\": \"global\",\n"
        "        \"effective_scope\": \"none\",\n"
        "        \"local_confirmation_required\": None,\n"
        "    }\n"
        "    codex_executable = shutil.which(\"codex\")\n"
        "    if not codex_executable:\n"
        "        registration.update(\n"
        "            {\n"
        "                \"status\": \"unavailable\",\n"
        "                \"effective_scope\": \"unverifiable\",\n"
        "                \"reason\": \"codex_executable_missing\",\n"
        "                \"global\": {\"status\": \"unavailable\"},\n"
        "                \"local\": {\n"
        "                    \"status\": \"unverifiable\"\n"
        "                    if project_config_symlinked\n"
        "                    else \"unavailable\",\n"
        "                    \"project_config_present\": project_config_present,\n"
        "                    \"project_config_symlinked\": project_config_symlinked,\n"
        "                },\n"
        "            }\n"
        "        )\n"
        "        return registration\n"
        "\n"
        "    neutral_cwd = Path(repository.anchor)\n"
        "    global_raw, global_probe = mcp_registration_probe(\n"
        "        codex_executable, \"gaori\", neutral_cwd, timeout_seconds\n"
        "    )\n"
        "    global_registration = classify_gaori_mcp_scope(\n"
        "        global_raw, global_probe, gaori_executable, repository, \"global\"\n"
        "    )\n"
        "    if global_probe[\"ok\"]:\n"
        "        global_registration[\"_result\"] = global_probe.get(\"result\")\n"
        "\n"
        "    if project_config_symlinked:\n"
        "        local_registration = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"reason\": \"project_configuration_symlinked\",\n"
        "        }\n"
        "    elif not project_config_present:\n"
        "        local_registration = missing_mcp_scope(\"project_configuration_missing\")\n"
        "    else:\n"
        "        local_raw, local_probe = mcp_registration_probe(\n"
        "            codex_executable,\n"
        "            \"gaori\",\n"
        "            neutral_cwd,\n"
        "            timeout_seconds,\n"
        "            {\"CODEX_HOME\": str(repository / \".codex\")},\n"
        "        )\n"
        "        local_registration = classify_gaori_mcp_scope(\n"
        "            local_raw, local_probe, gaori_executable, repository, \"local\"\n"
        "        )\n"
        "        if local_probe[\"ok\"]:\n"
        "            local_registration[\"_result\"] = local_probe.get(\"result\")\n"
        "    local_registration.update(\n"
        "        {\n"
        "            \"project_config_present\": project_config_present,\n"
        "            \"project_config_symlinked\": project_config_symlinked,\n"
        "        }\n"
        "    )\n"
        "\n"
        "    effective_raw, effective_probe = mcp_registration_probe(\n"
        "        codex_executable, \"gaori\", repository, timeout_seconds\n"
        "    )\n"
        "    status, effective_scope, reason = effective_mcp_registration(\n"
        "        \"gaori\",\n"
        "        global_registration,\n"
        "        local_registration,\n"
        "        project_config_symlinked,\n"
        "        effective_raw,\n"
        "        effective_probe,\n"
        "    )\n"
        "    global_registration.pop(\"_result\", None)\n"
        "    local_registration.pop(\"_result\", None)\n"
        "    local_confirmable = (\n"
        "        None if project_config_symlinked else local_registration[\"status\"] != \"missing\"\n"
        "    )\n"
        "    registration.update(\n"
        "        {\n"
        "            \"status\": status,\n"
        "            \"effective_scope\": effective_scope,\n"
        "            \"local_confirmation_required\": local_confirmable,\n"
        "            \"global\": global_registration,\n"
        "            \"local\": local_registration,\n"
        "            \"recommendation\": (\n"
        "                \"resolve_symlinked_local_configuration\"\n"
        "                if project_config_symlinked\n"
        "                else mcp_recommendation(\n"
        "                    global_registration[\"status\"],\n"
        "                    bool(local_confirmable),\n"
        "                )\n"
        "            ),\n"
        "        }\n"
        "    )\n"
        "    if reason:\n"
        "        registration[\"reason\"] = reason\n"
        "    return registration\n",
        "def inspect_gaori_mcp(\n"
        "    repository: Path, gaori_executable: str | None, timeout_seconds: float\n"
        ") -> dict[str, Any]:\n"
        "    return inspect_claude_mcp(\"gaori\", repository, gaori_executable, timeout_seconds)\n",
    ),
    # The configuration inventory names the local registration file. Both the
    # Mulgae and the Gaori inventories carry this identical line, so one rule
    # rewrites both and is expected to match twice.
    (
        '        configuration_entry(repository, ".codex/config.toml", timeout_seconds),\n',
        '        configuration_entry(repository, ".mcp.json", timeout_seconds),\n',
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

RULE_TABLES: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("SUBSTITUTIONS", SUBSTITUTIONS),
    ("SCRIPT_SUBSTITUTIONS", SCRIPT_SUBSTITUTIONS),
    ("DATA_SUBSTITUTIONS", DATA_SUBSTITUTIONS),
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
    ("skills/dev-setup/scripts/inspect_tools.py", "not_found = bool("),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_status_missing"),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_not_connected"),
    # The Mulgae and Gaori probes are whole-function block matches; these names
    # exist only in their Claude replacement.
    ("skills/dev-setup/scripts/inspect_tools.py", "def inspect_claude_mcp("),
    ("skills/dev-setup/scripts/inspect_tools.py", '".mcp.json"'),
    ("skills/dev-setup/scripts/inspect_tools.py", "enabledMcpjsonServers"),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_pending_approval"),
    # The test-setup inspector is host-neutral and copied untouched; this pins
    # the schema it must keep announcing.
    ("skills/test-setup/scripts/inspect_testing.py", "aquarium-test-setup-inspection.v1"),
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
    ("~/.agents/skills", "Claude Code loads ~/.claude/skills; add a substitution rule"),
    ("${PLUGIN_ROOT}", "Claude Code expands ${CLAUDE_PLUGIN_ROOT}; add a data substitution"),
    (".codex/config", "Claude Code registers MCP servers in .claude.json and .mcp.json; add a substitution rule"),
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


def check_excluded_files() -> None:
    """Refuse an exclusion whose target no longer exists upstream.

    An exclusion names a file upstream ships and this artifact does not. Once
    upstream renames or removes that file the entry is dead, and a dead entry
    would hide a differently named replacement behind a decision nobody made.
    """
    for relative, _reason in EXCLUDED_FILES:
        if not (UPSTREAM_PLUGIN / relative).is_file():
            raise SyncError(
                f"exclusion targets `{relative}`, which no longer exists upstream; "
                "remove the exclusion or retarget it"
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


def remove_excluded(destination: Path) -> list[str]:
    excluded: list[str] = []
    for relative, _reason in EXCLUDED_FILES:
        (destination / relative).unlink()
        excluded.append(relative)
    return excluded


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


def rules_for(path: Path) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    if path.suffix in TEXT_SUFFIXES:
        return RULE_TABLES[0]
    if path.suffix in SCRIPT_SUFFIXES:
        return RULE_TABLES[1]
    if path.suffix in DATA_SUFFIXES:
        return RULE_TABLES[2]
    return None


def transform_text(destination: Path, shadowed: set[str]) -> dict[tuple[str, int], int]:
    """Apply the substitution tables and count how often each rule rewrote shipped text.

    Files an override replaces are transformed too, which is harmless, but a
    match there is not counted: the override discards it, so a rule that only
    ever matched inside an override target rewrites nothing a user sees.
    """
    usage = {
        (table, index): 0
        for table, rules in RULE_TABLES
        for index in range(len(rules))
    }
    for path in sorted(destination.rglob("*")):
        if not path.is_file():
            continue
        selected = rules_for(path)
        if selected is None:
            continue
        table, rules = selected
        counted = str(path.relative_to(destination)) not in shadowed
        original = path.read_text(encoding="utf-8")
        replaced = original
        for index, (old, new) in enumerate(rules):
            matches = replaced.count(old)
            if counted:
                usage[(table, index)] += matches
            if matches:
                replaced = replaced.replace(old, new)
        if replaced != original:
            path.write_text(replaced, encoding="utf-8")
    return usage


def check_rule_usage(usage: dict[tuple[str, int], int]) -> None:
    """Fail on any substitution rule that rewrote nothing the artifact ships.

    A literal table is brittle to punctuation and to refactoring. v0.1.10
    dropped one Oxford comma and extracted one helper, four Markdown rules and
    three script rules stopped matching, and nothing noticed until a forbidden
    needle happened to trip downstream. A rule that matched nothing is either
    dead and must be deleted, or stale and must be re-derived; neither is a
    decision generation may take by itself.
    """
    tables = dict(RULE_TABLES)
    dead = [
        f"  {table}[{index}]: {tables[table][index][0].splitlines()[0]!r}"
        for (table, index), count in usage.items()
        if count == 0
    ]
    if dead:
        raise SyncError(
            "substitution rules matched nothing that ships:\n"
            + "\n".join(dead)
            + "\ndelete each dead rule or re-derive it against the new upstream text"
        )


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
    the host running the skill — a Mulgae provider, a required CLI version, one
    of several selectable review providers. That text is correct in a Claude
    artifact and cannot be renamed without making it false, but it still trips
    the `Codex` needle, because neither overrides nor copies exempt their own
    content.

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


def apply_additions(destination: Path) -> list[str]:
    """Copy the host-only files that have no upstream counterpart.

    `transform_skills` deletes each skill's own `agents/` sidecar directory; the
    plugin-root `agents/` directory created here is unrelated to those and is
    where Claude Code discovers plugin subagents.
    """
    added: list[str] = []
    for relative in ADDED_PATHS:
        source = ADDITIONS / relative
        target = destination / relative
        if not source.is_file():
            raise SyncError(f"addition file missing: {source}")
        if target.exists():
            raise SyncError(
                f"addition `{relative}` collides with an upstream-derived file; "
                "use an override for a file upstream ships"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        added.append(relative)
    return added


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


def positional_arity_errors(tree: ast.Module) -> list[tuple[int, str]]:
    """Report direct calls that pass a positional count a same-module signature rejects.

    A block substitution that drifts can produce code that parses but cannot
    run: v0.1.10 gave `classify_ouroboros_registration` a second parameter, and
    a replacement block that kept calling it with one would have raised
    `TypeError` on every inspection. Only simple shapes are checked — functions
    without `*args`, `**kwargs`, or keyword-only parameters, called by bare name
    with positional arguments only — which is exactly the shape the bundled
    scripts use.
    """
    signatures: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        arguments = node.args
        if arguments.vararg or arguments.kwarg or arguments.kwonlyargs:
            continue
        positional = arguments.posonlyargs + arguments.args
        signatures[node.name] = (len(positional) - len(arguments.defaults), len(positional))
    errors: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        signature = signatures.get(node.func.id)
        if signature is None or node.keywords:
            continue
        if any(isinstance(argument, ast.Starred) for argument in node.args):
            continue
        required, total = signature
        if not required <= len(node.args) <= total:
            expected = str(total) if required == total else f"{required}-{total}"
            errors.append(
                (
                    node.lineno,
                    f"{node.func.id}: {len(node.args)} positional argument(s), expected {expected}",
                )
            )
    return errors


def check_generated_python(destination: Path) -> None:
    """Refuse generated scripts that cannot parse or call their own functions.

    `ast.parse` rather than `py_compile`: the latter writes `__pycache__` into
    the staged tree, which `--check` would then report as drift.
    """
    failures: list[str] = []
    for path in sorted(destination.rglob("*.py")):
        relative = path.relative_to(destination)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        except SyntaxError as error:
            failures.append(f"  {relative}:{error.lineno}: {error.msg}")
            continue
        failures.extend(
            f"  {relative}:{line}: {message}" for line, message in positional_arity_errors(tree)
        )
    if failures:
        raise SyncError(
            "generated Python cannot run — a script substitution drifted:\n" + "\n".join(failures)
        )


def check_excluded_references(destination: Path) -> None:
    """Fail when generated text still names a file the exclusion removed."""
    failures: list[str] = []
    for relative, _reason in EXCLUDED_FILES:
        basename = Path(relative).name
        for path in sorted(destination.rglob("*")):
            if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
                continue
            if basename in path.read_text(encoding="utf-8"):
                failures.append(f"  {path.relative_to(destination)}: references excluded `{relative}`")
    if failures:
        raise SyncError(
            "generated text references an excluded file:\n"
            + "\n".join(failures)
            + "\nstop excluding it or rewrite the reference"
        )


def write_sync_manifest(
    destination: Path,
    repository: str,
    commit: str,
    overrides: list[str],
    excluded: list[str],
    additions: list[str],
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
        "excluded": excluded,
        "additions": additions,
        "files": files,
    }
    (destination / SYNC_MANIFEST).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def generate(destination: Path) -> tuple[str, list[str]]:
    commit = upstream_commit()
    codex_exemptions = check_codex_exemptions()
    check_excluded_files()
    copy_tree(destination)
    excluded = remove_excluded(destination)
    usage = transform_text(destination, set(load_override_manifest()))
    check_rule_usage(usage)
    # Overrides replace whole files, so they run before gating. Otherwise an
    # override would overwrite the frontmatter key and quietly reintroduce the
    # policy drift the sidecar is meant to prevent.
    overrides = apply_overrides(destination)
    transform_skills(destination)
    additions = apply_additions(destination)
    write_plugin_manifest(destination)
    check_forbidden(destination, codex_exemptions)
    check_sigils(destination)
    check_generated_python(destination)
    check_excluded_references(destination)
    check_required(destination)
    write_sync_manifest(
        destination, upstream_manifest()["repository"], commit, overrides, excluded, additions
    )
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
    print(
        f"  {len(overrides)} overrides applied, {len(EXCLUDED_FILES)} upstream files excluded, "
        f"{len(ADDED_PATHS)} host-only files added"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

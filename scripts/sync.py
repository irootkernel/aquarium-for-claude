#!/usr/bin/env python3
"""Generate the Claude Code plugin from the pinned upstream Codex plugin.

The upstream repository at `upstream/` is the single source of truth. This
script performs a deterministic transformation into `plugins/root-kernel/`,
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
UPSTREAM_PLUGIN = UPSTREAM / "plugins" / "root-kernel"
OUTPUT = REPOSITORY / "plugins" / "root-kernel"
OVERRIDES = REPOSITORY / "overrides"
OVERRIDE_MANIFEST = OVERRIDES / "manifest.json"
SYNC_MANIFEST = "sync-manifest.json"

COPIED_DIRECTORIES = ("skills", "references", "assets")
TEXT_SUFFIXES = (".md",)
SCRIPT_SUFFIXES = (".py",)

# Ordered literal substitutions applied to copied Markdown. Order matters: a
# later rule must never rewrite text that an earlier rule already produced.
#
# `AGENTS.md` is deliberately absent. Upstream `dev-setup/SKILL.md` contains
# "Do not edit nested AGENTS.md, CLAUDE.md, ...", which a blanket rule would
# corrupt into "nested CLAUDE.md, CLAUDE.md". Instruction-file wording is
# handled by full-file overrides instead.
SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("$root-kernel:", "/root-kernel:"),
    ("$lore-commits", "/lore-commits"),
    ("$lore-query", "/lore-query"),
    ("$orca-cli", "/orca-cli"),
    ("`request_user_input`", "`AskUserQuestion`"),
    ("the Codex goal", "the Claude Code todo list"),
    ("a fresh Codex reviewer", "a fresh independent reviewer"),
    ("one fresh Codex reviewer", "one fresh independent reviewer"),
    ("supervised Codex reviewer", "supervised independent reviewer"),
    ("a fresh Codex in the current", "a fresh independent reviewer in the current"),
    ("fresh Codex audit", "fresh from-scratch audit"),
    ("direct Codex audit", "direct from-scratch audit"),
    (" for Codex.", " for Claude Code."),
    # Lora installs per host, so the catalog's scope wording and `--agent` value
    # both move. These phrases are long enough not to collide with the
    # instruction-file text handled by overrides.
    ("Configure it for Codex user-global scope.", "Configure it for the Claude Code user-global scope."),
    ("--agent codex", "--agent claude-code"),
    ("the Codex user-global skill directory", "the Claude Code user-global skill directory"),
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
)

# Text that must exist after transformation. A script substitution that quietly
# stops matching would otherwise ship a script searching only Codex paths, and
# the Markdown forbidden-check cannot see it.
REQUIRED_TEXT: tuple[tuple[str, str], ...] = (
    ("skills/dev-setup/scripts/inspect_tools.py", "CLAUDE_CONFIG_DIR"),
    ("skills/dev-setup/scripts/inspect_tools.py", '".claude/skills"'),
)

# Strings that must not survive into the generated tree. Each entry pairs a
# needle with the remedy, so a failure names its own fix.
FORBIDDEN: tuple[tuple[str, str], ...] = (
    ("$root-kernel:", "add a substitution rule"),
    ("$lore-", "add a substitution rule"),
    ("$orca-cli", "add a substitution rule"),
    ("request_user_input", "add a substitution rule or an override"),
    ("--agent codex", "add an override"),
    ("Codex", "add a substitution rule or an override"),
)


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
    for name in ("skills",):
        if not (UPSTREAM_PLUGIN / name).is_dir():
            raise SyncError(f"upstream is missing `{name}/`; refusing to generate")


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


def load_override_manifest() -> dict[str, str]:
    if not OVERRIDE_MANIFEST.is_file():
        return {}
    return json.loads(OVERRIDE_MANIFEST.read_text(encoding="utf-8"))


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
    codex = json.loads(
        (UPSTREAM_PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
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


def check_forbidden(destination: Path) -> None:
    """Scan generated Markdown and the generated manifest for host-specific text.

    Bundled scripts are excluded: they legitimately still read `CODEX_HOME`,
    because a Claude Code user may also have Codex skills installed.
    """
    failures: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES + (".json",):
            continue
        text = path.read_text(encoding="utf-8")
        for needle, remedy in FORBIDDEN:
            if needle in text:
                relative = path.relative_to(destination)
                failures.append(f"  {relative}: contains `{needle}` — {remedy}")
    if failures:
        raise SyncError("host-specific text survived transformation:\n" + "\n".join(failures))


def write_sync_manifest(destination: Path, commit: str, overrides: list[str]) -> None:
    files = {
        str(path.relative_to(destination)): digest(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name != SYNC_MANIFEST
    }
    payload = {
        "upstream": {
            "repository": "https://github.com/irootkernel/root-kernel-dev-skills",
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
    copy_tree(destination)
    transform_text(destination)
    # Overrides replace whole files, so they run before gating. Otherwise an
    # override would overwrite the frontmatter key and quietly reintroduce the
    # policy drift the sidecar is meant to prevent.
    overrides = apply_overrides(destination)
    transform_skills(destination)
    write_plugin_manifest(destination)
    check_forbidden(destination)
    check_required(destination)
    write_sync_manifest(destination, commit, overrides)
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
            staged = Path(temporary) / "root-kernel"
            staged.mkdir()
            commit, overrides = generate(staged)

            if arguments.check:
                if not OUTPUT.is_dir():
                    print("error: plugins/root-kernel/ has not been generated", file=sys.stderr)
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

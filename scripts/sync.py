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
import fnmatch
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
    # The edition-owned upgrade lifecycle. Additions land after
    # `transform_skills`, so this skill never sees the sidecar-derived
    # decoration: its frontmatter — the gating flag included — is authored
    # final, and `apply_additions` refuses a skill addition that omits it.
    "skills/upgrade/SKILL.md",
    "skills/upgrade/references/rederivation.md",
    # The repository-state inspector this edition's independent review runs for
    # its no-mutation baseline. Upstream shipped it beside `orca-review` and
    # removed it in v0.1.14; the edition owns it now, under the skill that
    # actually calls it, which also retires the cross-skill path nothing watched.
    "skills/independent-review/scripts/inspect_repository_state.py",
)

# Slash-menu hints for the skills that take arguments. Claude Code shows the
# hint after the command name in the `/` menu; the Codex sidecar has no
# counterpart, so the table lives here. It is keyed by skill so a skill that
# disappears upstream stops the sync instead of leaving a stale hint, and it
# uses the argument vocabulary of each skill's description, which is the
# user-facing contract. Skills that take free text carry no hint.
ARGUMENT_HINTS: dict[str, str] = {
    "epic-handler": "<roadmap-path> <epic-id>",
    "epic-validator": "<roadmap-path> <epic-id>",
    "task-handler": "<roadmap-path> <task-id>",
    "task-plan": "<roadmap-path> <task-id>",
    "task-implement": "<roadmap-path> <task-id>",
    "task-verify": "<roadmap-path> <task-id>",
    "task-refine": "<roadmap-path> <task-id>",
    "task-document": "<roadmap-path> <task-id>",
    "task-review": "<roadmap-path> <task-id>",
    "task-close": "<roadmap-path> <task-id>",
    "release-handler": "[version]",
    "release-qa": "[version]",
    "dev-setup-bundle": "<manifest-path>",
    "independent-review": "<target> [task-or-epic-id]",
    "mulgae-review": "<target> [task-or-epic-id]",
    "orca-review": "<target> [task-or-epic-id]",
}

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
    (
        "references/dolgorae-review-contract.md",
        "the consumer contract for the Dolgorae capture backend upstream adopted in "
        "v0.1.14; that backend runs a fresh Codex Reviewer, this artifact's "
        "independent review dispatches host subagents instead, and its Orca review "
        "is forbidden to use Dolgorae, so no skill here routes through it and the "
        "contract would document a lifecycle this edition does not have; upstream "
        "disabled that route in v0.1.16 and this edition's route never used it",
    ),
    (
        "references/development-contract.md",
        "the shared contract for the `aquarium-dev` producers and host manager "
        "upstream bundled under `tools/` in v0.1.15; that development channel is "
        "excluded from this artifact, so the contract would document a lifecycle "
        "this edition does not have",
    ),
    (
        "skills/dev-setup-global/scripts/inspect_ouroboros.py",
        "per-Codex-home Ouroboros inspection: it resolves `CODEX_HOME` and `~/.codex`, "
        "imports `ouroboros.codex.artifacts`, and compares packaged Codex rules against "
        "each discovered home; Ouroboros reaches Claude Code as a plugin rather than as "
        "per-home rules and skills, so every dimension it measures is absent here and "
        "`inspect_tools.py` already carries this edition's plugin-scoped probe",
    ),
)

# Upstream skills this artifact does not ship, removed whole before any text
# rule runs so their text neither ships nor keeps a rule alive. A skill cannot
# be excluded file by file: `transform_skills` refuses a skill directory without
# `SKILL.md`, and a basename reference check on `SKILL.md` would match every
# skill. The skill must still exist upstream, and generated text must not name
# it, for the same reasons an excluded file must not.
EXCLUDED_SKILLS: tuple[tuple[str, str], ...] = (
    (
        "status",
        "v0.1.17's production-setup status report: every step it takes — the scoped "
        "`aquarium-status` inspection, `aquarium-status show`, and `forget` — runs the "
        "ledger runtime under the excluded plugin-root `tools/`, it reports enrollment "
        "in the `aquarium-dev` channel this edition does not ship, and its record "
        "envelopes are specified only in upstream's repository-level `docs/specs/`, "
        "outside the plugin; the ledger lifecycle upstream wired into `dev-setup` and "
        "`dev-setup-bundle` is removed with it",
    ),
)

# Upstream plugin-root entries this transformation never copies. `copy_tree`
# walks `COPIED_DIRECTORIES` and no top-level file at all, so both a new
# directory and a new file are decisions, and each entry pairs the name with the
# reason it does not belong in a Claude Code artifact. The entry must still
# exist upstream, for the same reason an exclusion must.
EXCLUDED_PLUGIN_ROOT: tuple[tuple[str, str], ...] = (
    (
        "tools",
        "the `aquarium-dev` CLI and stdio MCP runtime upstream bundled in v0.1.15: a "
        "Darwin arm64 development channel that builds unreleased local-main artifacts "
        "of Aquarium and its producer CLIs under `~/.aquarium-dev`, passes `CODEX_HOME` "
        "through to them, and produces Codex plugin artifacts; no skill in this artifact "
        "routes through it, and its 37 KB hash-pinned wheel lock would ship dead weight. "
        "v0.1.17 added the `aquarium-status` production-setup ledger runtime beside it: "
        "an Apple Silicon-only hash-pinned Python runtime and launcher under "
        "`~/.aquarium/status-runtime`, shared with the other host's edition, that the "
        "excluded `status` skill reports and upstream's `dev-setup` records into",
    ),
    (
        ".mcp.json",
        "the plugin-level registration for that development channel, in Codex's "
        "`mcp_servers` shape with `cwd` and `tool_timeout_sec`; the channel is excluded, "
        "and a translated registration would start a server no installation provides and "
        "report a failed MCP connection in every session of every repository",
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
    # Upstream v0.1.16 disabled its Dolgorae-backed Independent Review and this
    # sentence now says so directly. This edition keeps Independent Review live
    # on host subagents, but that backend holds no immutable capture either, so
    # it is still not a fallback for the two capture-only scopes; the
    # replacement keeps the exclusion and says why in this edition's own terms.
    (
        "`workspace` and `dirty` remain outside this workflow. Report the unsupported Orca scope and ask for an explicitly selected supported target or review route; Independent Review is disabled and is not a fallback. Never stage paths or reinterpret state merely to manufacture an Orca Review target.",
        "`workspace` and `dirty` remain outside this workflow. Report the unsupported Orca scope and ask for an explicitly selected supported target or review route; Independent Review does not support those scopes either and is not a fallback. Never stage paths or reinterpret state merely to manufacture an Orca Review target.",
    ),
    # The shared disposition contract lists every route that can still deliver
    # findings now that upstream v0.1.16 disabled its Dolgorae-backed
    # Independent Review, and it routes a caller to an explicitly selected
    # "native Codex" (host-native) subagent instead. On this host Independent
    # Review IS that native subagent route and stays enabled, so the contract
    # names it directly rather than describing it as disabled or dormant. The
    # first anchor still holds unsubstituted `$aquarium:` sigils, so this pair
    # must run before the `$aquarium:` rule.
    (
        "The disabled `$aquarium:independent-review` route itself only reports its refusal and alternative guidance; that refusal launches nothing. Exactly one explicitly preselected supported Orca or native Codex alternative may run only under its own contract, and native Codex additionally requires host fresh delegation. Multiple preselected alternatives require the user to choose one before anything launches. A direct `$aquarium:task-review`, standalone `$aquarium:mulgae-review`, or standalone `$aquarium:orca-review` is report-only.",
        "A standalone `/aquarium:independent-review` dispatches fresh read-only reviewer subagents through this host's own subagent mechanism under its own contract. A direct `/aquarium:task-review` or a standalone `/aquarium:independent-review`, `/aquarium:mulgae-review`, or `/aquarium:orca-review` is report-only.",
    ),
    (
        "from Mulgae Review, Orca Review, an explicitly selected native Codex review subagent, a workflow review waiver, or the dormant Independent Review contract if that route is re-enabled.",
        "from Mulgae Review, Orca Review, Independent Review, an explicitly selected native Claude Code review subagent, or a workflow review waiver.",
    ),
    # Upstream v0.1.17 wired its production-setup ledger into `dev-setup` and
    # `dev-setup-bundle`: a gate that blocks every repository mutation until the
    # `aquarium-status` runtime reads the predecessor row, attempt creation, a
    # recording section, and the bundle's attempt and receipt handoff. The
    # runtime lives under the excluded plugin-root `tools/` and the `status`
    # skill is excluded whole, so these spans are deleted or rewritten without
    # the ledger. Counted substitutions rather than an override: upstream edits
    # both files nearly every release, the new text is hard-wrapped, and the
    # rules below for their other spans would die inside an override. Anchors
    # still carry `$aquarium:` sigils, so they run before that rule.
    (
        "Before preparing any terminal attempt, require the scoped global inspector to\n"
        "report `aquarium-status` as `current`. A missing, outdated, or broken runtime is\n"
        "a `$aquarium:dev-setup-global` continuation with its own proposal and approval;\n"
        "an unsafe or unknown launcher is a blocker. Do not begin repository mutation\n"
        "until the current runtime can read the predecessor row revision.\n"
        "\n"
        "After canonical Git identity and full or scoped component intent are fixed, use\n"
        "the canonical Git root's final NFC-normalized path component as the project\n"
        "label. General setup without an explicit component limit is full; every\n"
        "explicit component request or continuation is scoped to its sorted unique\n"
        "component names, including `agents-guidance` when guidance is selected. Then\n"
        "create one `aquarium-production-status-attempt/v1` immediately before\n"
        "the first persistent setup mutation. For a terminal no-op, create it immediately\n"
        "before settlement. Read the current row revision through `aquarium-status show\n"
        "--format json`; a missing row uses revision 0. A bundle-supplied attempt replaces\n"
        "local creation and must be preserved byte-for-byte. Diagnosis, Plan Mode, and\n"
        "work stopped before execution approval do not create an attempt.\n"
        "\n",
        "",
    ),
    (
        "## Record Terminal Setup\n"
        "\n"
        "For every attempt created here or supplied by the bundle, submit exactly one\n"
        "`aquarium-production-status-record/v1` after the target reaches `ready`,\n"
        "`partial`, `failed`, or `declined`. Populate completion time and only settled\n"
        "`sanho` or `aquarium_dev` component observations. Run the current bundled\n"
        "recorder through the verified `aquarium-status` dependency runtime so the\n"
        "recorded Aquarium version belongs to this plugin, not a stale PATH payload. Use\n"
        "`python3 <plugin-root>/tools/aquarium-status/install.py run-bundled --source\n"
        "<plugin-root>/tools/aquarium-status record` with the closed document on standard\n"
        "input; do not import a cache path into the current agent process.\n"
        "\n"
        "Return `aquarium-production-status-recording-result/v1` with exactly `schema`,\n"
        "`status`, `attempt_id`, `receipt`, `retry_request`, and `problem_code`. Preserve\n"
        "setup success if recording fails: return `failed`, the exact original record\n"
        "document as `retry_request`, a closed problem code, and make the enclosing setup\n"
        "result `partial`. A retry submits only that identical document to `record`; it\n"
        "must not re-enter or repeat setup. If canonical identity was unavailable, return\n"
        "`not_recordable` with a null attempt ID and do not write a row. Use the exact\n"
        "fields, nullability rules, and closed problem codes in the\n"
        "[production-status specification](../../../../docs/specs/production-status.md).\n"
        "\n",
        "",
    ),
    ("status-recording result or exact record-only retry, ", ""),
    (
        "Pass the normalized `shared_tools` union, manifest digest, requesting skill, and\n"
        "the infrastructure component `aquarium-status` to `$aquarium:dev-setup-global`.\n"
        "The global skill maps each selected name to one `--component <name>` inspector\n"
        "argument and runs no other component. `aquarium-status` is common bundle\n"
        "infrastructure, not a new manifest tool, so this preserves\n"
        "`aquarium.dev-setup-bundle/v1` and its existing vocabulary.\n",
        "Pass the normalized `shared_tools` union, manifest digest, and requesting skill to `/aquarium:dev-setup-global`. The global skill maps each selected name to one `--component <name>` inspector argument and runs no other component, which preserves `aquarium.dev-setup-bundle/v1` and its existing vocabulary.\n",
    ),
    (
        "For each ready target, after manifest revalidation and canonical identity freeze,\n"
        "read its current row through `aquarium-status show --format json` and create one\n"
        "`aquarium-production-status-attempt/v1` with exactly `schema`, a new UUIDv4\n"
        "`attempt_id`, that `expected_row_revision` or 0, the canonical `git_root`, the\n"
        "project label equal to the canonical Git root's final NFC-normalized path\n"
        "component, the UTC `started_at`, and a scoped component `scope`. Its component\n"
        "list is the sorted unique effective `tools` list plus `agents-guidance` exactly\n"
        "when the effective guidance policy is `propose`. A bundle target is never a\n"
        "full attempt, because the manifest is an explicit component selection; this\n"
        "prevents it from advancing `last_full_ready`. The\n"
        "[production-status specification](../../../../docs/specs/production-status.md)\n"
        "owns this closed envelope. Pass it with the requesting\n"
        "skill, manifest digest, target index, canonical Git root, complete effective tool\n"
        "list, explicit local MCP overrides, and guidance policy to `$aquarium:dev-setup`.\n"
        "The repository skill interprets the list as target intent, preserves that attempt\n"
        "unchanged, and never repeats global installation or freshness work.\n",
        "For each ready target, after manifest revalidation and canonical identity freeze, pass the requesting skill, manifest digest, target index, canonical Git root, complete effective tool list, explicit local MCP overrides, and guidance policy to `/aquarium:dev-setup`. The repository skill interprets the list as target intent and never repeats global installation or freshness work.\n",
    ),
    (
        "Once a target enters `dev-setup`, accept its recording receipt only when the\n"
        "attempt ID, canonical root, predecessor row revision, and resulting revisions\n"
        "match the handoff contract. Never record that target a second time. If a target\n"
        "settles before entry, complete and record the bundle-owned original attempt once.\n"
        "On recording failure, preserve the exact record-only retry request and never\n"
        "repeat target mutations. Validate the closed recording-result fields and problem\n"
        "codes against the same specification. Continue independent targets.\n"
        "\n",
        "",
    ),
    # Upstream's host goal is a Codex goal the model creates, completes, and
    # marks blocked through a tool. Claude Code's counterpart is the session
    # `/goal`: the user sets or clears it, and an evaluator judges it from the
    # conversation after every turn and ends it once it holds or is impossible, while the todo tools this edition
    # used to name are off by default on Fable 5.1 and Opus 5.5. Sentences
    # whose verbs would create, complete, or block the goal are rewritten to
    # work under it and report; this one carries a `$aquarium:` sigil, so it
    # runs before that rule, and the rest precede the generic mapping below.
    (
        "When a Codex goal is authorized, keep it active through every phase. Mark it complete only after `$aquarium:task-close` succeeds and no required task work or authorized lifecycle action remains. Mark the goal blocked only when the host's goal tool defines a blocked state and its own repeated-blocker rule is met by the same unresolved external blocker persisting across consecutive goal turns with no authorized action remaining; otherwise keep it active and report the exact gap.",
        "When the user has set a Claude Code session goal, keep working toward it through every phase. Report it met only after `/aquarium:task-close` succeeds and no required task work or authorized lifecycle action remains. Report it unreachable only when the same unresolved external blocker persists across consecutive turns with no authorized action remaining, because the evaluator may then end it as impossible; otherwise keep working and report the exact gap.",
    ),
    ("$aquarium:", "/aquarium:"),
    # The shared disposition contract credits re-review after remediation to
    # every route — v0.1.17 added the native subagent route and the waiver —
    # and hedges only for a dormant Independent Review upstream could
    # re-enable. This edition's Independent Review reads the live target
    # exactly as Orca's reviewer does, so it is never dormant here and
    # upstream's hedge is false in this artifact.
    (
        "Mulgae creates a fresh native capture, Orca reads the corrected live target, native Codex requires a fresh report-only subagent, and a waiver requires a new coordinator assessment. Independent Review would require a fresh capture if separately re-enabled.",
        "Mulgae creates a fresh native capture, Independent Review and Orca read the corrected live target, native Claude Code requires a fresh report-only subagent, and a waiver requires a new coordinator assessment.",
    ),
    # Upstream v0.1.17 lets Task, Epic, and validation workflows select one
    # review route, one of which is a fresh host-native subagent it names
    # "native Codex". On this host that route is Claude Code's own subagent
    # review, so the prose renames it; the `native-codex` route ID and the
    # Podway Procedure labels stay byte-canonical (see `CANONICAL_PHRASES`).
    # The routing contract also says Independent Review remains disabled, which
    # is false here: it stays a live standalone entry point, though still not a
    # selectable workflow route. Every rule whose anchor contains the phrase
    # runs before the generic rename at the end of this block.
    (
        "Independent Review remains disabled and is not a\nselectable route.",
        "On this host the `native-codex` route ID and the Podway Procedure labels and criteria that name this route keep upstream's canonical bytes and mean Claude Code's native subagent review, which dispatches the bundled `aquarium:independent-reviewer` agent once over the complete Review Brief. `/aquarium:independent-review` stays live as a standalone report-only entry point and is not a selectable route.",
    ),
    (
        "Do not describe native Codex\nas Independent Review, Dolgorae, Orca, or Mulgae.",
        "Do not describe native Claude Code as Dolgorae, Orca, or Mulgae, or report its checkpoint as a standalone Independent Review run, although both dispatch the bundled reviewer agent.",
    ),
    # The `native-codex` route runs through the bundled `aquarium:independent-reviewer`:
    # its tool allowlist removes the editing, writing, and agent-dispatch
    # tools the route forbids, its prompt forbids writing through Bash, and it
    # reviews the whole Review Brief in one pass. Three of these anchors
    # contain the upstream phrase, so the block precedes the generic rename.
    (
        "For `native-codex`, create one fresh host subagent with the exact bounded target, complete Review Brief, and static report-only instructions. Require no edits, tests, nested agents, or lifecycle mutation. Preserve the host delegation identity and reviewer provenance without calling it independent review.",
        "For `native-codex`, dispatch one fresh `aquarium:independent-reviewer` subagent through this host's own subagent mechanism with the exact bounded target, the complete Review Brief, and static report-only instructions, and have it review the whole brief in one pass rather than through a single lens. Leave it on its Opus default unless the user explicitly asked for Fable. Its tools already exclude the editing, writing, and agent-dispatch tools; the specification must still forbid edits through Bash, tests, and lifecycle mutation. If that agent is unavailable, record a preflight failure for this route and stop for user direction rather than substituting another subagent type. Preserve the dispatch identity and reviewer provenance without reporting it as a standalone Independent Review run.",
    ),
    (
        "native Codex through one fresh report-only host subagent",
        "native Claude Code through one fresh report-only `aquarium:independent-reviewer` subagent reviewing the whole brief in one pass",
    ),
    (
        "native Codex through one fresh static report-only host subagent",
        "native Claude Code through one fresh static report-only `aquarium:independent-reviewer` subagent reviewing the whole brief in one pass",
    ),
    (
        "For `native-codex`, require fresh host delegation.",
        "For `native-codex`, require that this host's subagent mechanism offers the bundled `aquarium:independent-reviewer` agent.",
    ),
    (
        "Native Codex\n"
        "requires fresh host delegation.",
        "Native Claude Code\n"
        "requires the bundled `aquarium:independent-reviewer` agent.",
    ),
    # The leading space keeps a word that merely ends in "native", such as
    # "alternative", from being renamed; a capital N already starts a word.
    (" native Codex", " native Claude Code"),
    ("Native Codex", "Native Claude Code"),
    # `$use-podway`, `$use-sanho`, `$use-mulgae`, `$use-gaori`. A prefix rule
    # covers the family and any later sibling; `/use-` cannot re-match it.
    ("$use-", "/use-"),
    # `$create-podway-procedure`, new in v0.1.13. A prefix rule covers the
    # family like `$use-`; the maintainer authoring skill installs user-scoped
    # on both hosts and keeps a bare name. Its one shipped occurrence is
    # references/podway-integration.md — the agents-guidance.md occurrence
    # lives inside an override and is not counted.
    ("$create-", "/create-"),
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
    # task-close hedges its structured closeout ask on availability because the
    # Codex tool is optional there. `AskUserQuestion` is always present on this
    # host, so the hedge would read as permission to fall back to prose. Must
    # run before the generic `request_user_input` rule, whose output the anchor
    # would otherwise never contain — the orca-supervision precedent.
    (
        "Use structured `request_user_input` when available and ask all three questions together",
        "Use structured `AskUserQuestion` and ask all three questions together",
    ),
    ("`request_user_input`", "`AskUserQuestion`"),
    # Podway's goal-separation section keeps two more mentions after the mapping
    # below, and both name the host rather than a goal. The anchor spans the pair
    # so one rule settles the sentence, and it precedes the mapping because the
    # anchor still carries the unmapped phrase.
    (
        "does not independently prove the Codex objective complete. Verify the actual requirements and external results, and continue any remaining authorized work. A Podway blocker does not automatically block a Codex goal: follow the current Codex tool contract, including any recurrence threshold, and continue useful independent work.",
        "does not independently prove the host objective complete. Verify the actual requirements and external results, and continue any remaining authorized work. A Podway blocker does not by itself make a Claude Code session goal unreachable: report it as the exact Podway blocker rather than as goal impossibility, and continue useful independent work.",
    ),
    # The one defining sentence lives in the Podway contract, which every
    # goal-coordinating skill reads; `/goal` is named only where the user is
    # handed a condition to type.
    (
        "Codex goals and Podway goals have separate creation rules and lifecycles. Create a Codex goal only when explicitly requested under its current tool contract; a Podway goal does not authorize one.",
        "Claude Code session goals and Podway goals have separate creation rules and lifecycles. A Claude Code session goal is the completion condition the user sets with `/goal <condition>` or clears with `/goal clear`, distinct from a Podway session's goal; after each turn an evaluator judges it from the conversation alone and ends it once it holds or is judged impossible, so surface completion evidence or the exact blocker there instead of trying to mark it, and never propose one merely because a Podway goal exists.",
    ),
    (
        "Create a separate Codex goal only on explicit user request under its tool contract",
        "Work under a separate Claude Code session goal only when the user sets one",
    ),
    (
        "Create a Codex goal only on explicit user request under its tool contract",
        "Work under a Claude Code session goal only when the user has set one",
    ),
    (
        "create a Codex goal only on explicit request",
        "work under a Claude Code session goal only when the user sets one",
    ),
    (
        "Create a Codex goal only after plan approval and an explicit user request under its tool contract. When authorized, inspect the current goal, continue it when it represents the same task, create one containing the task ID and evidence boundary when none exists, and stop rather than replace a different unfinished goal. Otherwise proceed without a Codex goal. Omit a token budget unless the user explicitly supplied one.",
        "Work under a Claude Code session goal only after plan approval and only when the user sets one. When the user asks for one, give them the exact `/goal` condition naming the task ID and evidence boundary, and tell them that setting it replaces any different goal already active, because a session holds one goal at a time. Otherwise proceed without proposing a Claude Code session goal.",
    ),
    (
        "When a Codex goal is explicitly authorized, create one or continue the matching existing goal under its tool contract, and omit a token budget unless the user supplied one.",
        "When the user explicitly asks for a Claude Code session goal, give them the exact `/goal` condition for this task, or continue the matching goal already set.",
    ),
    (
        "Complete an authorized Codex goal only",
        "Report an authorized Claude Code session goal met only",
    ),
    (
        "complete the Codex goal as achieved",
        "report the Claude Code session goal met",
    ),
    (
        "Do not create the handoff file, a Codex goal, or a Podway session",
        "Do not create the handoff file or a Podway session, or propose a Claude Code session goal,",
    ),
    ("Codex goal", "Claude Code session goal"),
    ("fresh Codex audit", "fresh from-scratch audit"),
    # Ouroboros registers its skills with the host agent, so the component whose
    # health `dev-setup` establishes is the Claude Code one here. The bundle
    # skill names the same component in a list of Ouroboros setup mutations;
    # the anchor is the shortest unique phrase so the next punctuation edit
    # cannot break it again.
    ("Codex skill health", "Claude Code skill health"),
    (
        "Use the global v3 inspector's `current_home_readiness`, not `all_discovered_homes_readiness`. Require rules and skills in the current Codex home, the matching MCP package, and a `home_binding` to that same home; shared `~/.agents/skills` copies prevent readiness until migrated.",
        "Use the global inspector's `ouroboros` component. Require a supported CLI and a plugin-scoped MCP registration that resolves; this host installs Ouroboros once as a plugin, so there is no per-home readiness, `home_binding`, or MCP package pin to require.",
    ),
    (
        "For Ouroboros, this means one CLI upgrade and one integration update per distinct discovered Codex home, not one installation per repository.",
        "For Ouroboros, this means one CLI upgrade; its Claude Code integration is one plugin installation that global setup diagnoses rather than installs.",
    ),
    # `dev-setup` was a full-file override until v0.1.15 moved user-global
    # installation into `dev-setup-global`. What it still diverges on is three
    # literal spans, two of which carry a forbidden needle and would need a rule
    # whether or not the override stayed, so the override is retired and these
    # take its place. Each anchor occurs exactly once in upstream Markdown.
    (
        "For a canonical user-global skill path under `~/.agents/skills`, or the active canonical Codex skill root where an upstream contract requires it, check only whether the path exists.",
        "For a canonical user-global skill path under the configured Claude Code skill root \u2014 `$CLAUDE_CONFIG_DIR/skills` when that variable is set, otherwise `~/.claude/skills` \u2014 check only whether the path exists.",
    ),
    (
        "Create, change, or remove a project-local registration only when the user explicitly requested local scope or repository authority already requires it. Preserve unrelated Codex configuration.",
        "Create, change, or remove a project-local `.mcp.json` registration only when the user explicitly requested local scope or repository authority already requires it. Preserve unrelated Claude Code configuration.",
    ),
    # Claude Code resolves a `@AGENTS.md` import before the first turn but never
    # reads `AGENTS.md` on its own, so prose-only delegation silently leaves the
    # canonical guidance unloaded. `agents-guidance.md` owns the delegation file;
    # this makes the skill that reviews the pair report the gap.
    (
        "Reuse verified repository facts while assessing structure, behavior, duplication, and project-specific constraints. An explicit diagnosis-only request reports findings without drafting a proposal.\n",
        "Reuse verified repository facts while assessing structure, behavior, duplication, and project-specific constraints. An explicit diagnosis-only request reports findings without drafting a proposal.\n"
        "\n"
        "Claude Code loads CLAUDE.md but never reads AGENTS.md on its own, so a CLAUDE.md that delegates in prose alone leaves the canonical guidance unloaded. Report that as a gap and propose the delegation file in `agents-guidance.md`, whose `@AGENTS.md` line Claude Code resolves as a real import before the first turn.\n",
    ),
    # release-qa's dispatch instructions are host-neutral because Codex has no
    # first-class subagents. This host does, and independent subagents launched
    # in a single message is what parallel dispatch concretely means here.
    # Naming the mechanism follows upstream's own charter of making supported
    # native capabilities readily usable; the tool's own name is deliberately
    # not spelled, because Claude Code has already renamed it once and a stale
    # name would send the model looking for a tool it does not have. Workers
    # request `opus`, the baseline for every delegated role here: a worker with
    # no explicit model inherits the coordinator's, so a Fable session would
    # otherwise fan out Fable workers. Fable stays an explicit user choice.
    (
        "Use the available agent delegation surface to dispatch fresh subagents for independent risk clusters.",
        "Use the host's own subagent mechanism to dispatch fresh subagents for independent risk clusters, requesting the `opus` model for every worker unless the user explicitly asked for Fable, because a worker without an explicit model inherits the coordinator's.",
    ),
    (
        "Parallelize independent clusters when capacity allows without weakening isolation.",
        "Parallelize independent clusters by launching their workers in a single message when capacity allows, without weakening isolation.",
    ),
    # `epic-handler` may add an optional fresh read-only perspective and names
    # no model for it, so on a Fable session it would inherit Fable; it requests
    # `opus` like every other delegated role here.
    (
        "Use a fresh read-only subagent for an additional perspective when task risk or uncertainty merits it.",
        "Use a fresh read-only subagent for an additional perspective when task risk or uncertainty merits it, requesting the `opus` model unless the user explicitly asked for Fable.",
    ),
)

# Substitutions for bundled scripts, kept separate from Markdown because they
# rewrite executable behavior rather than prose. Skill discovery narrows to the
# Claude Code roots: this artifact diagnoses one host, and a copy sitting in
# another host's root is neither reachable here nor a duplicate of anything.
SCRIPT_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    (
        "    codex_home = os.environ.get(\"CODEX_HOME\")\n"
        "    if codex_home:\n"
        "        try:\n"
        "            candidates.append(Path(codex_home).expanduser().joinpath(\"skills\"))\n"
        "        except (OSError, ValueError, RuntimeError):\n"
        "            pass\n"
        "    candidates.extend(\n"
        "        [Path.home().joinpath(\".codex/skills\"), Path.home().joinpath(\".agents/skills\")]\n"
        "    )\n",
        "    # Only Claude Code skill roots count here. A skill installed in\n"
        "    # another host's root is not reachable from this one, and counting it\n"
        "    # would report a cross-host copy as a duplicate installation and\n"
        "    # degrade a diagnosis that is about this host. The guard upstream added\n"
        "    # in v0.1.15 is kept: the configured root comes from the environment and\n"
        "    # an unexpandable value must not take the whole inspection down.\n"
        "    configured = os.environ.get(\"CLAUDE_CONFIG_DIR\")\n"
        "    if configured:\n"
        "        try:\n"
        "            candidates.append(Path(configured).expanduser().joinpath(\"skills\"))\n"
        "        except (OSError, ValueError, RuntimeError):\n"
        "            pass\n"
        "    candidates.append(Path.home().joinpath(\".claude/skills\"))\n",
    ),
    # Upstream v0.1.16 restructured `classify_ouroboros_registration`'s failure
    # branch around a `presence` key that only its own `mcp_registration_probe`
    # sets, which broke both of this edition's separate block anchors inside
    # it. `claude mcp get` still prints a human-readable block rather than
    # typed JSON, so the Claude replacement still reads a definite not-found
    # from stderr and health from the `Status:` line rather than from
    # `presence`. The two former anchors are collapsed into one whole-function
    # rule so the next upstream reshuffle fails loudly instead of drifting.
    (
        "def classify_ouroboros_registration(\n"
        "    registration_probe: dict[str, Any], ouroboros_executable: str | None\n"
        ") -> dict[str, Any]:\n"
        "    probe = {\n"
        "        key: registration_probe[key]\n"
        "        for key in (\"attempted\", \"ok\", \"exit_code\", \"timed_out\")\n"
        "    }\n"
        "    if not registration_probe[\"ok\"]:\n"
        "        missing = registration_probe.get(\"presence\") == \"missing\"\n"
        "        if registration_probe.get(\"error_code\") and (\n"
        "            registration_probe[\"error_code\"] != \"invalid_json\"\n"
        "            or registration_probe.get(\"response_invalid\")\n"
        "        ):\n"
        "            probe[\"error_code\"] = registration_probe[\"error_code\"]\n"
        "        probe[\"reason\"] = (\n"
        "            \"registration_not_found\"\n"
        "            if missing\n"
        "            else \"registration_probe_timed_out\"\n"
        "            if registration_probe[\"timed_out\"]\n"
        "            else \"registration_invalid_json\"\n"
        "            if registration_probe.get(\"response_invalid\")\n"
        "            else \"registration_probe_failed\"\n"
        "        )\n"
        "        return {\n"
        "            \"status\": \"missing\" if missing else \"degraded\",\n"
        "            \"probe\": probe,\n"
        "        }\n"
        "\n"
        "    result = registration_probe.get(\"result\")\n"
        "    if not isinstance(result, dict):\n"
        "        probe[\"reason\"] = \"registration_result_invalid\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "    transport = result.get(\"transport\")\n"
        "    direct_registration_matches = bool(\n"
        "        result.get(\"name\") == \"ouroboros\"\n"
        "        and result.get(\"enabled\") is True\n"
        "        and ouroboros_direct_launcher_matches(transport, ouroboros_executable)\n"
        "    )\n"
        "    isolated_registration_matches = bool(\n"
        "        result.get(\"name\") == \"ouroboros\"\n"
        "        and result.get(\"enabled\") is True\n"
        "        and ouroboros_isolated_launcher_matches(transport)\n"
        "    )\n"
        "    if direct_registration_matches or isolated_registration_matches:\n"
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
        "def classify_ouroboros_registration(\n"
        "    registration_probe: dict[str, Any], ouroboros_executable: str | None\n"
        ") -> dict[str, Any]:\n"
        "    # `claude mcp get` prints a human-readable block rather than typed JSON,\n"
        "    # and this host has no structural inventory that proves absence: `claude\n"
        "    # mcp list` health-checks every approved server and so starts it. The\n"
        "    # definite not-found is still read from stderr (`No MCP server named\n"
        "    # \"<name>\". Configured servers: ...`) and health from the `Status:` line;\n"
        "    # the transport fields upstream compares are absent for a plugin-scoped\n"
        "    # server, so `ouroboros_executable` cannot be compared.\n"
        "    probe = {\n"
        "        key: registration_probe[key]\n"
        "        for key in (\"attempted\", \"ok\", \"exit_code\", \"timed_out\")\n"
        "    }\n"
        "    if registration_probe[\"timed_out\"]:\n"
        "        probe[\"reason\"] = \"registration_probe_timed_out\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "    if registration_probe.get(\"error_code\"):\n"
        "        probe[\"error_code\"] = registration_probe[\"error_code\"]\n"
        "        probe[\"reason\"] = \"registration_probe_failed\"\n"
        "        return {\"status\": \"degraded\", \"probe\": probe}\n"
        "\n"
        "    if not registration_probe[\"ok\"]:\n"
        "        not_found = bool(\n"
        "            registration_probe[\"exit_code\"] == 1\n"
        "            and not registration_probe[\"timed_out\"]\n"
        "            and not registration_probe.get(\"stdout\", \"\").strip()\n"
        "            and re.match(\n"
        "                r\"No MCP server named ['\\\"]?[^'\\\"]+['\\\"]?\\.\",\n"
        "                registration_probe.get(\"stderr\", \"\").strip(),\n"
        "            )\n"
        "        )\n"
        "        probe[\"reason\"] = (\n"
        "            \"registration_not_found\" if not_found else \"registration_probe_failed\"\n"
        "        )\n"
        "        return {\n"
        "            \"status\": \"missing\" if not_found else \"degraded\",\n"
        "            \"probe\": probe,\n"
        "        }\n"
        "\n"
        "    # `claude mcp get` prints a human-readable block rather than typed JSON, so\n"
        "    # the registration is read from its `Status:` line. A server that resolves\n"
        "    # but cannot connect is registered and unhealthy, not unregistered. The\n"
        "    # transport fields upstream verifies are absent for a plugin-scoped server,\n"
        "    # which prints only `Scope:` and `Status:`, so `ouroboros_executable` cannot\n"
        "    # be compared here.\n"
        "    status_line = \"\"\n"
        "    for line in registration_probe.get(\"stdout\", \"\").splitlines():\n"
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
    # Upstream v0.1.17 changed one line of this function: the reported range,
    # because `supported_ouroboros_version` dropped its `<0.54` bound. The
    # replacement reports the same range, since `inspect_ouroboros_cli` still
    # runs upstream's check and a bound it no longer enforces would contradict
    # the `version_supported` reported beside it.
    (
        "def inspect_ouroboros(\n"
        "    repository: Path,\n"
        "    timeout_seconds: float,\n"
        "    *,\n"
        "    codex_home: Path | None = None,\n"
        "    cli_observation: dict[str, Any] | None = None,\n"
        ") -> dict[str, Any]:\n"
        "    tool = (\n"
        "        dict(cli_observation)\n"
        "        if cli_observation is not None\n"
        "        else inspect_ouroboros_cli(repository, timeout_seconds)\n"
        "    )\n"
        "    tool[\"supported_range\"] = \">=0.51.1\"\n"
        "    environment = {\"CODEX_HOME\": str(codex_home)} if codex_home else None\n"
        "    tool[\"home_binding\"] = {\n"
        "        \"status\": \"unverifiable\",\n"
        "        \"reason\": \"registration_unavailable\",\n"
        "    }\n"
        "    tool[\"runtime_package\"] = {\"status\": \"unverifiable\", \"version\": None}\n"
        "    if codex_home is not None and codex_home.exists() and not codex_home.is_dir():\n"
        "        reason = \"home_not_a_directory\"\n"
        "        tool[\"status\"] = \"degraded\"\n"
        "        for key in (\"codex_integration\", \"mcp_registration\", \"mcp_runtime\"):\n"
        "            tool[key] = {\"status\": \"unverifiable\", \"probe\": skipped_probe(reason)}\n"
        "        tool[\"home_binding\"] = {\"status\": \"unverifiable\", \"reason\": reason}\n"
        "        tool[\"runtime_package\"] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"version\": None,\n"
        "            \"reason\": reason,\n"
        "        }\n"
        "        return tool\n"
        "    codex = shutil.which(\"codex\")\n"
        "    direct_runtime_configured = False\n"
        "    isolated_runtime_configured = False\n"
        "    if codex:\n"
        "        registration_probe = mcp_registration_probe(\n"
        "            str(Path(codex).resolve()),\n"
        "            \"ouroboros\",\n"
        "            repository,\n"
        "            timeout_seconds,\n"
        "            environment,\n"
        "        )\n"
        "        tool[\"mcp_registration\"] = classify_ouroboros_registration(\n"
        "            registration_probe, tool[\"executable\"]\n"
        "        )\n"
        "        registration_result = registration_probe.get(\"result\")\n"
        "        registration_transport = (\n"
        "            registration_result.get(\"transport\")\n"
        "            if isinstance(registration_result, dict)\n"
        "            else None\n"
        "        )\n"
        "        if isinstance(registration_transport, dict):\n"
        "            registered_env = registration_transport.get(\"env\", {})\n"
        "            registered_home = (\n"
        "                registered_env.get(\"CODEX_HOME\")\n"
        "                if isinstance(registered_env, dict)\n"
        "                else None\n"
        "            )\n"
        "            if codex_home is not None:\n"
        "                if registered_home is None:\n"
        "                    tool[\"home_binding\"] = {\n"
        "                        \"status\": \"unverifiable\",\n"
        "                        \"reason\": \"home_not_explicit\",\n"
        "                    }\n"
        "                elif (\n"
        "                    isinstance(registered_home, str)\n"
        "                    and Path(registered_home).is_absolute()\n"
        "                ):\n"
        "                    try:\n"
        "                        matches = (\n"
        "                            Path(registered_home).resolve() == codex_home.resolve()\n"
        "                        )\n"
        "                        if not matches:\n"
        "                            try:\n"
        "                                matches = Path(registered_home).samefile(codex_home)\n"
        "                            except FileNotFoundError:\n"
        "                                matches = False\n"
        "                        tool[\"home_binding\"] = {\n"
        "                            \"status\": \"configured\" if matches else \"degraded\",\n"
        "                            \"reason\": \"home_matches\" if matches else \"home_mismatch\",\n"
        "                        }\n"
        "                    except (OSError, ValueError, RuntimeError):\n"
        "                        tool[\"home_binding\"] = {\n"
        "                            \"status\": \"degraded\",\n"
        "                            \"reason\": \"home_invalid\",\n"
        "                        }\n"
        "                else:\n"
        "                    tool[\"home_binding\"] = {\n"
        "                        \"status\": \"degraded\",\n"
        "                        \"reason\": \"home_invalid\",\n"
        "                    }\n"
        "            args = registration_transport.get(\"args\", [])\n"
        "            if isinstance(args, list) and len(args) > 4 and isinstance(args[4], str):\n"
        "                package = OUROBOROS_MCP_PACKAGE.fullmatch(args[4])\n"
        "                if package:\n"
        "                    tool[\"runtime_package\"] = {\n"
        "                        \"status\": \"pinned\" if package.group(1) else \"unverifiable\",\n"
        "                        \"version\": package.group(1),\n"
        "                    }\n"
        "        direct_runtime_configured = tool[\"mcp_registration\"][\n"
        "            \"status\"\n"
        "        ] == \"configured\" and ouroboros_direct_launcher_matches(\n"
        "            registration_transport, tool[\"executable\"]\n"
        "        )\n"
        "        isolated_runtime_configured = tool[\"mcp_registration\"][\n"
        "            \"status\"\n"
        "        ] == \"configured\" and ouroboros_isolated_launcher_matches(\n"
        "            registration_transport\n"
        "        )\n"
        "    else:\n"
        "        tool[\"mcp_registration\"] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"probe\": skipped_probe(\"codex_executable_missing\"),\n"
        "        }\n"
        "\n"
        "    if not tool[\"installed\"]:\n"
        "        tool[\"version_supported\"] = False\n"
        "        tool[\"probes\"][\"version\"] = skipped_probe(\"executable_missing\")\n"
        "        tool[\"codex_integration\"] = {\n"
        "            \"status\": \"missing\",\n"
        "            \"probe\": skipped_probe(\"executable_missing\"),\n"
        "        }\n"
        "        if isolated_runtime_configured:\n"
        "            runtime_probe = normalized_probe(registration_probe)\n"
        "            runtime_probe[\"reason\"] = \"isolated_launcher_configured\"\n"
        "            tool[\"mcp_runtime\"] = {\n"
        "                \"status\": \"configured\",\n"
        "                \"probe\": runtime_probe,\n"
        "            }\n"
        "        elif codex:\n"
        "            registration_reason = (\n"
        "                tool[\"mcp_registration\"].get(\"probe\", {}).get(\"reason\")\n"
        "            )\n"
        "            runtime_reason = (\n"
        "                \"registration_not_supported_launcher\"\n"
        "                if registration_reason in {None, \"registration_mismatch\"}\n"
        "                else registration_reason\n"
        "            )\n"
        "            tool[\"mcp_runtime\"] = {\n"
        "                \"status\": \"unverifiable\",\n"
        "                \"probe\": skipped_probe(runtime_reason),\n"
        "            }\n"
        "        else:\n"
        "            tool[\"mcp_runtime\"] = {\n"
        "                \"status\": \"missing\",\n"
        "                \"probe\": skipped_probe(\"executable_missing\"),\n"
        "            }\n"
        "        return tool\n"
        "\n"
        "    codex_doctor = run_command(\n"
        "        [tool[\"executable\"], \"codex\", \"doctor\"],\n"
        "        repository,\n"
        "        timeout_seconds,\n"
        "        environment_overrides=environment,\n"
        "    )\n"
        "    tool[\"codex_integration\"] = {\n"
        "        \"status\": \"configured\" if codex_doctor[\"ok\"] else \"degraded\",\n"
        "        \"probe\": {\n"
        "            key: codex_doctor[key]\n"
        "            for key in (\"attempted\", \"ok\", \"exit_code\", \"timed_out\")\n"
        "        },\n"
        "    }\n"
        "\n"
        "    if isolated_runtime_configured:\n"
        "        runtime_probe = normalized_probe(registration_probe)\n"
        "        runtime_probe[\"reason\"] = \"isolated_launcher_configured\"\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"configured\",\n"
        "            \"probe\": runtime_probe,\n"
        "        }\n"
        "    elif direct_runtime_configured:\n"
        "        mcp_doctor = json_probe(\n"
        "            [tool[\"executable\"], \"mcp\", \"doctor\", \"--json\"],\n"
        "            repository,\n"
        "            timeout_seconds,\n"
        "            environment_overrides=environment,\n"
        "        )\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"configured\" if mcp_doctor[\"ok\"] else \"degraded\",\n"
        "            \"probe\": normalized_probe(mcp_doctor),\n"
        "        }\n"
        "    else:\n"
        "        registration_reason = tool[\"mcp_registration\"].get(\"probe\", {}).get(\"reason\")\n"
        "        runtime_reason = (\n"
        "            \"registration_not_supported_launcher\"\n"
        "            if registration_reason in {None, \"registration_mismatch\"}\n"
        "            else registration_reason\n"
        "        )\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"probe\": skipped_probe(runtime_reason),\n"
        "        }\n"
        "\n"
        "    if direct_runtime_configured:\n"
        "        tool[\"runtime_package\"] = {\"status\": \"selected_cli\", \"version\": tool[\"version\"]}\n"
        "    if (\n"
        "        tool[\"runtime_package\"][\"status\"] == \"pinned\"\n"
        "        and tool[\"runtime_package\"][\"version\"] != tool[\"version\"]\n"
        "    ):\n"
        "        tool[\"runtime_package\"][\"status\"] = \"different\"\n"
        "    components_ready = (\n"
        "        tool[\"version_supported\"]\n"
        "        and (codex_home is None or tool[\"home_binding\"][\"status\"] == \"configured\")\n"
        "        and tool[\"codex_integration\"][\"status\"] == \"configured\"\n"
        "        and tool[\"mcp_runtime\"][\"status\"] == \"configured\"\n"
        "        and tool[\"mcp_registration\"][\"status\"] == \"configured\"\n"
        "    )\n"
        "    tool[\"status\"] = \"configured\" if components_ready else \"degraded\"\n"
        "    return tool\n",
        "def inspect_ouroboros(\n"
        "    repository: Path,\n"
        "    timeout_seconds: float,\n"
        "    *,\n"
        "    codex_home: Path | None = None,\n"
        "    cli_observation: dict[str, Any] | None = None,\n"
        ") -> dict[str, Any]:\n"
        "    # Upstream probes the other host for the Ouroboros MCP registration and\n"
        "    # measures per-home rules and skills, so on Claude Code the component could\n"
        "    # never report `configured` and every design skill stayed blocked. Ouroboros\n"
        "    # reaches this host as a plugin instead: one installation, no per-home\n"
        "    # binding, and an MCP server the plugin registers under a plugin-scoped\n"
        "    # name. The whole function is replaced because upstream's `codex_home`\n"
        "    # threading, `environment_overrides`, transport parsing, and the two\n"
        "    # launcher matchers all read locals this host cannot produce; a narrower cut\n"
        "    # would ship NameErrors the AST gate cannot see. `codex_home` stays in the\n"
        "    # signature because the caller contract is upstream's, and the dimension it\n"
        "    # names is reported as absent rather than silently passing.\n"
        "    tool = (\n"
        "        dict(cli_observation)\n"
        "        if cli_observation is not None\n"
        "        else inspect_ouroboros_cli(repository, timeout_seconds)\n"
        "    )\n"
        "    tool[\"supported_range\"] = \">=0.51.1\"\n"
        "    tool[\"home_binding\"] = {\"status\": \"unverifiable\", \"reason\": \"home_not_applicable\"}\n"
        "    tool[\"runtime_package\"] = {\n"
        "        \"status\": \"unverifiable\",\n"
        "        \"version\": None,\n"
        "        \"reason\": \"plugin_scoped_registration\",\n"
        "    }\n"
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
        "        }\n"
        "\n"
        "    if not tool[\"installed\"]:\n"
        "        tool[\"version_supported\"] = False\n"
        "        tool[\"probes\"][\"version\"] = skipped_probe(\"executable_missing\")\n"
        "        tool[\"host_integration\"] = {\n"
        "            \"status\": \"missing\",\n"
        "            \"probe\": skipped_probe(\"executable_missing\"),\n"
        "        }\n"
        "        if host_integration[\"status\"] == \"configured\":\n"
        "            runtime_probe = dict(host_integration[\"probe\"])\n"
        "            runtime_probe[\"reason\"] = \"plugin_launcher_configured\"\n"
        "            tool[\"mcp_runtime\"] = {\n"
        "                \"status\": \"configured\",\n"
        "                \"probe\": runtime_probe,\n"
        "            }\n"
        "        else:\n"
        "            tool[\"mcp_runtime\"] = {\n"
        "                \"status\": \"missing\",\n"
        "                \"probe\": skipped_probe(\"executable_missing\"),\n"
        "            }\n"
        "        return tool\n"
        "\n"
        "    # `ooo codex doctor` verifies another host's routing artifacts and has no\n"
        "    # Claude Code counterpart. The plugin-scoped registration resolved above is\n"
        "    # the host-integration signal here, so it is recorded rather than reprobed.\n"
        "    tool[\"host_integration\"] = host_integration\n"
        "\n"
        "    # The plugin launches the MCP 2 server in an isolated process, the Claude\n"
        "    # analog of upstream's isolated `uvx` launcher, so the plugin-scoped\n"
        "    # registration resolved above is the runtime signal. `ooo mcp doctor`\n"
        "    # inspects the CLI's own package environment and is not evidence about\n"
        "    # that server, so it is never run here.\n"
        "    if host_integration[\"status\"] == \"configured\":\n"
        "        runtime_probe = dict(host_integration[\"probe\"])\n"
        "        runtime_probe[\"reason\"] = \"plugin_launcher_configured\"\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"configured\",\n"
        "            \"probe\": runtime_probe,\n"
        "        }\n"
        "    else:\n"
        "        registration_reason = tool[\"mcp_registration\"].get(\"probe\", {}).get(\"reason\")\n"
        "        tool[\"mcp_runtime\"] = {\n"
        "            \"status\": \"unverifiable\",\n"
        "            \"probe\": skipped_probe(\n"
        "                registration_reason or \"registration_not_supported_launcher\"\n"
        "            ),\n"
        "        }\n"
        "\n"
        "    # Upstream reads the pinned `ouroboros-mcp` version out of the registration\n"
        "    # transport, which a plugin-scoped entry does not print, and `home_binding`\n"
        "    # measures a per-home contract this host does not have. Neither joins the\n"
        "    # readiness rollup, so an absent dimension cannot mark a healthy plugin\n"
        "    # installation degraded.\n"
        "    components_ready = (\n"
        "        tool[\"version_supported\"]\n"
        "        and tool[\"host_integration\"][\"status\"] == \"configured\"\n"
        "        and tool[\"mcp_runtime\"][\"status\"] == \"configured\"\n"
        "        and tool[\"mcp_registration\"][\"status\"] == \"configured\"\n"
        "    )\n"
        "    tool[\"status\"] = \"configured\" if components_ready else \"degraded\"\n"
        "    return tool\n",
    ),
    # Upstream v0.1.17 expects Humanizer in the shared cross-agent root, or in
    # the active Codex home when only that one holds it, and im-not-ai in the
    # active Codex home, and searches both roots through the new `roots`
    # parameter. Claude Code loads neither, so both tools would report every
    # correct installation as missing, and `inspect_writing_skill` marks a tool
    # ready only when the one discovered installation sits at the expected
    # target. Both functions are replaced whole: v0.1.17 changed the target the
    # one-line Humanizer rule anchored on, added `roots`, and renamed both
    # release pins to minimum versions, and a whole-function anchor fails loudly
    # on the next such change instead of drifting. The target is
    # `skill_roots()[0]`, the effective root with `CLAUDE_CONFIG_DIR` included,
    # and omitting `roots` falls back to the substituted `skill_roots()`, which
    # searches the Claude Code roots alone.
    (
        "def inspect_humanizer() -> dict[str, Any]:\n"
        "    return inspect_writing_skill(\n"
        "        skill_name=\"humanizer\",\n"
        "        expected_files=HUMANIZER_SKILL_FILES,\n"
        "        expected_target=humanizer_expected_target(),\n"
        "        minimum_version=HUMANIZER_MINIMUM_VERSION,\n"
        "        roots=humanizer_skill_roots(),\n"
        "    )\n",
        "def inspect_humanizer() -> dict[str, Any]:\n"
        "    # Upstream expects Humanizer in the shared cross-agent root, or in the\n"
        "    # active `CODEX_HOME` skill root when only that one holds it, and searches\n"
        "    # both. Claude Code loads neither, so the target is the effective Claude\n"
        "    # Code root, and with no `roots` the search falls back to `skill_roots()`,\n"
        "    # which covers the Claude Code roots alone.\n"
        "    return inspect_writing_skill(\n"
        "        skill_name=\"humanizer\",\n"
        "        expected_files=HUMANIZER_SKILL_FILES,\n"
        "        expected_target=skill_roots()[0] / \"humanizer\",\n"
        "        minimum_version=HUMANIZER_MINIMUM_VERSION,\n"
        "    )\n",
    ),
    (
        "def inspect_im_not_ai() -> dict[str, Any]:\n"
        "    try:\n"
        "        root = effective_codex_skill_root()\n"
        "        target = root / \"humanize-korean\"\n"
        "        shared_root = Path.home() / \".agents/skills\"\n"
        "        roots = (root, shared_root) if root != shared_root else (root,)\n"
        "    except (OSError, ValueError, RuntimeError):\n"
        "        target = None\n"
        "        roots = None\n"
        "    result = inspect_writing_skill(\n"
        "        skill_name=\"humanize-korean\",\n"
        "        expected_files=HUMANIZE_KOREAN_SKILL_FILES,\n"
        "        expected_target=target,\n"
        "        minimum_version=IM_NOT_AI_MINIMUM_VERSION,\n"
        "        require_version=False,\n"
        "        roots=roots,\n"
        "    )\n"
        "    if target is None:\n"
        "        result[\"reason\"] = \"home_resolution_failed\"\n"
        "    return result\n",
        "def inspect_im_not_ai() -> dict[str, Any]:\n"
        "    # Upstream targets the active `CODEX_HOME` skill root and also searches the\n"
        "    # shared cross-agent root, both unreachable here, so this reads exactly\n"
        "    # like its Humanizer sibling. The substituted `skill_roots()` already\n"
        "    # guards the configured root and is never empty, so the target stays\n"
        "    # unconditional and upstream's resolution guard has no counterpart.\n"
        "    return inspect_writing_skill(\n"
        "        skill_name=\"humanize-korean\",\n"
        "        expected_files=HUMANIZE_KOREAN_SKILL_FILES,\n"
        "        expected_target=skill_roots()[0] / \"humanize-korean\",\n"
        "        minimum_version=IM_NOT_AI_MINIMUM_VERSION,\n"
        "        require_version=False,\n"
        "    )\n",
    ),
    # v0.1.15 added a presence-only trust table for the paired and third-party
    # skills, hard-coded under the shared cross-agent root; v0.1.17 resolves
    # the Humanizer entry through `humanizer_expected_target()` and im-not-ai's
    # through the active Codex home. Claude Code loads neither root, so every
    # one of these checks would look where this host never reads and report a
    # correct installation as absent. `skill_roots()[0]` is the effective Claude
    # Code root, `CLAUDE_CONFIG_DIR` included, and the same root the installation
    # proposals target. The Python spelling carries no tilde, so the
    # `~/.agents/skills` needle never saw these; the needle is `.agents/skills`
    # now, which is what makes a future one abort instead of shipping.
    (
        "    trusted_global_skills = {\n"
        "        name: {\n"
        "            \"canonical_path\": str(path),\n"
        "            \"present\": path.exists(),\n"
        "            \"verification_scope\": \"presence_only\",\n"
        "        }\n"
        "        for name, path in {\n"
        "            \"use-sanho\": Path.home() / \".agents/skills/use-sanho\",\n"
        "            \"use-dolgorae\": Path.home() / \".agents/skills/use-dolgorae\",\n"
        "            \"use-mulgae\": Path.home() / \".agents/skills/use-mulgae\",\n"
        "            \"use-gaori\": Path.home() / \".agents/skills/use-gaori\",\n"
        "            \"use-gaori-status\": Path.home() / \".agents/skills/use-gaori-status\",\n"
        "            \"use-sorage\": Path.home() / \".agents/skills/use-sorage\",\n"
        "            \"use-podway\": Path.home() / \".agents/skills/use-podway\",\n"
        "            \"lore-commits\": Path.home() / \".agents/skills/lore-commits\",\n"
        "            \"lore-query\": Path.home() / \".agents/skills/lore-query\",\n"
        "            \"deslop\": Path.home() / \".agents/skills/deslop\",\n"
        "            \"humanizer\": humanizer_expected_target(),\n"
        "            \"humanize-korean\": effective_codex_skill_root() / \"humanize-korean\",\n"
        "        }.items()\n"
        "    }\n",
        "    trusted_root = skill_roots()[0]\n"
        "    trusted_global_skills = {\n"
        "        name: {\n"
        "            \"canonical_path\": str(trusted_root / name),\n"
        "            \"present\": (trusted_root / name).exists(),\n"
        "            \"verification_scope\": \"presence_only\",\n"
        "        }\n"
        "        for name in (\n"
        "            \"use-sanho\",\n"
        "            \"use-dolgorae\",\n"
        "            \"use-mulgae\",\n"
        "            \"use-gaori\",\n"
        "            \"use-gaori-status\",\n"
        "            \"use-sorage\",\n"
        "            \"use-podway\",\n"
        "            \"lore-commits\",\n"
        "            \"lore-query\",\n"
        "            \"deslop\",\n"
        "            \"humanizer\",\n"
        "            \"humanize-korean\",\n"
        "        )\n"
        "    }\n",
    ),
    # v0.1.17 added two helpers that resolve Humanizer's roots and target
    # through the shared cross-agent root and `effective_codex_skill_root`. The
    # Humanizer and trust-table rules above retire every caller, so both go
    # rather than ship paths this host never reads. `effective_codex_skill_root`
    # itself stays, defined without callers, which `tests/validate.rb` pins with
    # upstream's other uncalled helpers.
    (
        "def humanizer_skill_roots() -> tuple[Path, ...]:\n"
        "    return tuple(\n"
        "        dict.fromkeys((effective_codex_skill_root(), Path.home() / \".agents/skills\"))\n"
        "    )\n"
        "\n"
        "\n",
        "",
    ),
    (
        "def humanizer_expected_target() -> Path:\n"
        "    shared = Path.home() / \".agents/skills/humanizer\"\n"
        "    active = effective_codex_skill_root() / \"humanizer\"\n"
        "    if (active.exists() or active.is_symlink()) and not (\n"
        "        shared.exists() or shared.is_symlink()\n"
        "    ):\n"
        "        return active\n"
        "    return shared\n"
        "\n"
        "\n",
        "",
    ),
    # Lore and Deslop discover installations by walking `skill_roots()`, which
    # the rule above narrows to the Claude Code roots, and then require the one
    # installation to sit at a shared-root path those roots can never produce.
    # Left alone, both tools report `degraded` for every correct installation.
    (
        "        == str(Path.home() / \".agents/skills\" / name)\n",
        "        == str(skill_roots()[0] / name)\n"
    ),
    (
        "        and installations[0][\"location\"] == str(Path.home() / \".agents/skills/deslop\")\n",
        "        and installations[0][\"location\"] == str(skill_roots()[0] / \"deslop\")\n"
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
        "    global_probe = mcp_registration_probe(\n"
        "        codex_executable, \"mulgae\", neutral_cwd, timeout_seconds\n"
        "    )\n"
        "    global_registration = classify_mulgae_mcp_scope(\n"
        "        global_probe, mulgae_executable, repository, \"global\"\n"
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
        "        local_probe = mcp_registration_probe(\n"
        "            codex_executable,\n"
        "            \"mulgae\",\n"
        "            neutral_cwd,\n"
        "            timeout_seconds,\n"
        "            {\"CODEX_HOME\": str(repository / \".codex\")},\n"
        "        )\n"
        "        local_registration = classify_mulgae_mcp_scope(\n"
        "            local_probe, mulgae_executable, repository, \"local\"\n"
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
        "    effective_probe = mcp_registration_probe(\n"
        "        codex_executable, \"mulgae\", repository, timeout_seconds\n"
        "    )\n"
        "    status, effective_scope, reason = effective_mcp_registration(\n"
        "        global_registration,\n"
        "        local_registration,\n"
        "        project_config_symlinked,\n"
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
        "    global_probe = mcp_registration_probe(\n"
        "        codex_executable, \"gaori\", neutral_cwd, timeout_seconds\n"
        "    )\n"
        "    global_registration = classify_gaori_mcp_scope(\n"
        "        global_probe, gaori_executable, repository, \"global\"\n"
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
        "        local_probe = mcp_registration_probe(\n"
        "            codex_executable,\n"
        "            \"gaori\",\n"
        "            neutral_cwd,\n"
        "            timeout_seconds,\n"
        "            {\"CODEX_HOME\": str(repository / \".codex\")},\n"
        "        )\n"
        "        local_registration = classify_gaori_mcp_scope(\n"
        "            local_probe, gaori_executable, repository, \"local\"\n"
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
        "    effective_probe = mcp_registration_probe(\n"
        "        codex_executable, \"gaori\", repository, timeout_seconds\n"
        "    )\n"
        "    status, effective_scope, reason = effective_mcp_registration(\n"
        "        global_registration,\n"
        "        local_registration,\n"
        "        project_config_symlinked,\n"
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
    # Upstream moved the neutral-cwd probe into the project inspector in
    # v0.1.16, so the rule moves with it: the global inspector's one-line
    # delegation to `inspect_global_mcp_scope` already ships unchanged. The
    # previous rule rewrote the global inspector's own `inspect_global_mcp`
    # instead; this one rewrites the project inspector function it now calls.
    (
        "def inspect_global_mcp_scope(\n"
        "    name: str,\n"
        "    executable: str | None,\n"
        "    root: Path,\n"
        "    timeout_seconds: float,\n"
        ") -> dict[str, Any]:\n"
        "    codex_executable = shutil.which(\"codex\")\n"
        "    if not codex_executable:\n"
        "        return {\"status\": \"unavailable\", \"reason\": \"codex_executable_missing\"}\n"
        "    classifiers = {\n"
        "        \"mulgae\": classify_mulgae_mcp_scope,\n"
        "        \"gaori\": classify_gaori_mcp_scope,\n"
        "    }\n"
        "    classifier = classifiers.get(name)\n"
        "    if classifier is None:\n"
        "        raise ValueError(f\"unsupported global MCP component: {name}\")\n"
        "    probe = mcp_registration_probe(\n"
        "        codex_executable, name, Path(root.anchor), timeout_seconds\n"
        "    )\n"
        "    return classifier(probe, executable, root, \"global\")\n",
        "def inspect_global_mcp_scope(\n"
        "    name: str,\n"
        "    executable: str | None,\n"
        "    root: Path,\n"
        "    timeout_seconds: float,\n"
        ") -> dict[str, Any]:\n"
        "    # The user-scope view is the same configuration read the project inspector\n"
        "    # performs for all three scopes, and no host CLI probe runs here: on Claude\n"
        "    # Code every registration lookup health-checks the server and so starts it.\n"
        "    return inspect_claude_mcp(name, root, executable, timeout_seconds)[\"global\"]\n",
    ),
    # The configuration inventory names the local registration file. Both the
    # Mulgae and the Gaori inventories carry this identical line, so one rule
    # rewrites both and is expected to match twice.
    (
        '        configuration_entry(repository, ".codex/config.toml", timeout_seconds),\n',
        '        configuration_entry(repository, ".mcp.json", timeout_seconds),\n',
    ),
    # `inspect_ouroboros.py` measures per-home rules, skills, and MCP registration
    # for the other host and is excluded, so the import that would fail at startup
    # goes with it, and the components of the bundled development channel and,
    # since v0.1.17, the bundled status runtime leave the catalog rather than
    # probing installers this artifact does not ship. Ouroboros itself stays: the
    # shrunken component below calls the project inspector's plugin-scoped probe.
    (
        "from inspect_ouroboros import InvalidCodexHome, inspect_ouroboros\n",
        "",
    ),
    (
        "    \"podway\",\n"
        "    \"ouroboros\",\n"
        "    \"aquarium-dev\",\n"
        "    \"aquarium-status\",\n"
        ")\n",
        "    \"podway\",\n"
        "    \"ouroboros\",\n"
        ")\n",
    ),
    # Upstream's canonical location for a paired skill is the shared cross-agent
    # root, which Claude Code never loads: every correct installation would be
    # reported as absent from its canonical path and degraded. `skill_roots()[0]`
    # is the effective Claude Code root the installation proposals also target.
    (
        "    canonical_path = Path.home() / \".agents/skills\" / name\n",
        "    canonical_path = inspector.skill_roots()[0] / name\n",
    ),
    # The per-home options name a dimension this host does not have. They are
    # removed from the signature, the parser, and the call site together, so the
    # generated-script arity gate proves no caller was left behind.
    (
        "    components: tuple[str, ...] | None = None,\n"
        "    codex_homes: tuple[str, ...] = (),\n"
        "    verify_ouroboros_release: bool = False,\n"
        ") -> dict[str, Any]:\n",
        "    components: tuple[str, ...] | None = None,\n"
        ") -> dict[str, Any]:\n",
    ),
    # Ouroboros reaches this host as a Claude Code plugin: one installation, no
    # per-home rules, skills, or registration, and an MCP server the plugin
    # launches under a plugin-scoped name. The project inspector's
    # `inspect_ouroboros` is exactly that probe, so the component keeps a real
    # diagnosis while the excluded per-home module and its release comparison go.
    (
        "    if \"ouroboros\" in requested_components:\n"
        "        try:\n"
        "            tools[\"ouroboros\"] = inspect_ouroboros(\n"
        "                inspector,\n"
        "                neutral_cwd,\n"
        "                timeout_seconds,\n"
        "                codex_homes,\n"
        "                verify_ouroboros_release,\n"
        "            )\n"
        "        except InvalidCodexHome as error:\n"
        "            raise InspectionError(\n"
        "                \"invalid_codex_home\", \"Codex home is unavailable or invalid\"\n"
        "            ) from error\n",
        "    if \"ouroboros\" in requested_components:\n"
        "        tools[\"ouroboros\"] = inspector.inspect_ouroboros(neutral_cwd, timeout_seconds)\n",
    ),
    (
        "    if \"aquarium-dev\" in requested_components:\n"
        "        script = Path(__file__).resolve().parents[3] / \"tools/aquarium-dev/install.py\"\n"
        "        try:\n"
        "            probe = subprocess.run(\n"
        "                [sys.executable, \"-B\", str(script), \"diagnose\"],\n"
        "                cwd=neutral_cwd,\n"
        "                capture_output=True,\n"
        "                text=True,\n"
        "                timeout=timeout_seconds,\n"
        "                check=False,\n"
        "            )\n"
        "            if probe.returncode:\n"
        "                failure = {\n"
        "                    \"status\": \"unverifiable\",\n"
        "                    \"reason\": \"probe_failed\",\n"
        "                    \"exit_code\": probe.returncode,\n"
        "                    \"problem\": probe.stderr.strip(),\n"
        "                }\n"
        "                try:\n"
        "                    failure[\"diagnostic\"] = json.loads(probe.stderr)\n"
        "                except ValueError:\n"
        "                    pass\n"
        "                tools[\"aquarium-dev\"] = failure\n"
        "            else:\n"
        "                tools[\"aquarium-dev\"] = json.loads(probe.stdout)\n"
        "        except subprocess.TimeoutExpired as error:\n"
        "            tools[\"aquarium-dev\"] = {\n"
        "                \"status\": \"unverifiable\",\n"
        "                \"reason\": \"probe_timeout\",\n"
        "                \"timeout_seconds\": timeout_seconds,\n"
        "                \"problem\": str(error),\n"
        "            }\n"
        "        except (OSError, ValueError, subprocess.SubprocessError) as error:\n"
        "            tools[\"aquarium-dev\"] = {\n"
        "                \"status\": \"unverifiable\",\n"
        "                \"reason\": \"invalid_json\"\n"
        "                if isinstance(error, ValueError)\n"
        "                else \"probe_failed\",\n"
        "                \"problem\": str(error),\n"
        "            }\n",
        "",
    ),
    # v0.1.17 bundled an `aquarium-status` runtime under `tools/`, which this
    # artifact never copies, and its component probe executes that runtime's
    # installer in process. The component left the catalog above, so the parser
    # rejects it and the default run never requests it; the probe and its call
    # site go the way of the development channel's rather than ship a loader
    # for a file that does not exist.
    (
        "def inspect_aquarium_status() -> dict[str, Any]:\n"
        "    script = Path(__file__).resolve().parents[3] / \"tools/aquarium-status/install.py\"\n"
        "    spec = importlib.util.spec_from_file_location(\"aquarium_status_installer\", script)\n"
        "    if spec is None or spec.loader is None:\n"
        "        raise InspectionError(\n"
        "            \"inspector_unavailable\", \"aquarium-status inspector is unavailable\"\n"
        "        )\n"
        "    module = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(module)\n"
        "    payload = module.diagnose(script.parent)\n"
        "    required = {\n"
        "        \"schema\",\n"
        "        \"status\",\n"
        "        \"bundled\",\n"
        "        \"installed\",\n"
        "        \"launcher\",\n"
        "        \"runtime_root\",\n"
        "        \"action\",\n"
        "    }\n"
        "    if (\n"
        "        not isinstance(payload, dict)\n"
        "        or set(payload) != required\n"
        "        or payload.get(\"schema\") != \"aquarium-status-runtime-inspection/v1\"\n"
        "    ):\n"
        "        raise InspectionError(\n"
        "            \"inspection_failed\", \"aquarium-status inspection contract is invalid\", 1\n"
        "        )\n"
        "    return payload\n"
        "\n"
        "\n",
        "",
    ),
    (
        "    if \"aquarium-status\" in requested_components:\n"
        "        tools[\"aquarium-status\"] = inspect_aquarium_status()\n",
        "",
    ),
    (
        "    parser.add_argument(\n"
        "        \"--codex-home\",\n"
        "        action=\"append\",\n"
        "        default=[],\n"
        "        help=\"Additional Ouroboros Codex home to inspect; repeat for multiple homes\",\n"
        "    )\n"
        "    parser.add_argument(\n"
        "        \"--verify-ouroboros-release\",\n"
        "        action=\"store_true\",\n"
        "        help=\"Compare Ouroboros with official PyPI stable releases\",\n"
        "    )\n",
        "",
    ),
    (
        "    if any(not value.strip() for value in arguments.codex_home):\n"
        "        raise InspectionError(\"invalid_arguments\", \"--codex-home must not be blank\")\n",
        "",
    ),
    (
        "    if (\n"
        "        arguments.codex_home or arguments.verify_ouroboros_release\n"
        "    ) and \"ouroboros\" not in selected_components:\n"
        "        raise InspectionError(\n"
        "            \"invalid_arguments\", \"Ouroboros options require the ouroboros component\"\n"
        "        )\n",
        "",
    ),
    (
        "                arguments.include_sorage_initialization,\n"
        "                arguments.component,\n"
        "                tuple(arguments.codex_home),\n"
        "                arguments.verify_ouroboros_release,\n",
        "                arguments.include_sorage_initialization,\n"
        "                arguments.component,\n",
    ),
    # `subprocess` had exactly one user in this module, the development-channel
    # component removed above, and an unused import is the visible residue of a
    # block rule that deleted more than its own anchor.
    (
        "import importlib.util\n"
        "import json\n"
        "import math\n"
        "import subprocess\n"
        "import sys\n",
        "import importlib.util\n"
        "import json\n"
        "import math\n"
        "import sys\n",
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
    # The runtime component derives from the plugin-scoped registration and
    # never runs `ooo mcp doctor`; both reasons exist only in the replacement.
    ("skills/dev-setup/scripts/inspect_tools.py", "plugin_launcher_configured"),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_not_supported_launcher"),
    ("skills/dev-setup/scripts/inspect_tools.py", "not_found = bool("),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_status_missing"),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_not_connected"),
    # The Mulgae and Gaori probes are whole-function block matches; these names
    # exist only in their Claude replacement.
    ("skills/dev-setup/scripts/inspect_tools.py", "def inspect_claude_mcp("),
    ("skills/dev-setup/scripts/inspect_tools.py", '".mcp.json"'),
    ("skills/dev-setup/scripts/inspect_tools.py", "enabledMcpjsonServers"),
    ("skills/dev-setup/scripts/inspect_tools.py", "registration_pending_approval"),
    # The user-scope delegation exists only in the replacement; upstream's
    # global inspector calls the shrunken form under the same name.
    (
        "skills/dev-setup/scripts/inspect_tools.py",
        'return inspect_claude_mcp(name, root, executable, timeout_seconds)["global"]',
    ),
    # The writing-skill targets are single-line matches inside a call, so a
    # reformat upstream would restore targets this host cannot reach.
    ("skills/dev-setup/scripts/inspect_tools.py", 'expected_target=skill_roots()[0] / "humanizer"'),
    ("skills/dev-setup/scripts/inspect_tools.py", 'expected_target=skill_roots()[0] / "humanize-korean"'),
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
    ("$create-", "add a substitution rule"),
    ("$lore-", "add a substitution rule"),
    ("$orca-cli", "add a substitution rule"),
    ("request_user_input", "add a substitution rule or an override"),
    ("--agent codex", "add a substitution rule or an override"),
    (".agents/skills", "Claude Code loads ~/.claude/skills; add a substitution rule"),
    ("${PLUGIN_ROOT}", "Claude Code expands ${CLAUDE_PLUGIN_ROOT}; add a data substitution"),
    (".codex/config", "Claude Code registers MCP servers in .claude.json and .mcp.json; add a substitution rule"),
    ("Codex", "add a substitution rule, an override, or a reviewed exemption"),
    # The production-setup ledger runtime and its specification are excluded
    # with the `status` skill; generated text naming either would send a Claude
    # session to a runtime this artifact does not ship, or to the other host's
    # copy of it on the same machine.
    ("aquarium-status", "the ledger runtime is excluded; delete or rewrite the reference"),
    ("production-status", "the ledger specification is excluded; delete or rewrite the reference"),
)

# Almost every lowercase `$name` in upstream Markdown is a Codex skill
# invocation. `FORBIDDEN` names one needle per sigil family that already exists,
# so a family upstream introduces later passes both the substitution table and
# the forbidden scan and ships Codex invocation syntax to a Claude Code user in
# silence. That is how `$interview`, `$pm`, `$seed`, `$qa`, and `$deslop`
# arrived in v0.1.9. Uppercase spellings are environment variables the generated
# tree still needs (`${CLAUDE_PLUGIN_ROOT}`, `$CODEX_HOME`) and deliberately do
# not match.
SIGIL = re.compile(r"\$[a-z][a-z0-9:_-]*")

# The exceptions are lowercase `$name` tokens that are shell variables rather
# than skill invocations: v0.1.14 pins the commit identity through `git -c
# user.name="$aquarium_commit_name"`, which the scan read as an unmapped sigil.
# Dropping `_` from the pattern would close this case and silently admit any
# future `$snake_case` skill, so each exception is named instead, and
# `check_sigil_literals` requires it to still occur upstream: a token that stops
# shipping is removed deliberately rather than left masking the next sigil it
# happens to spell.
SIGIL_LITERALS: tuple[str, ...] = (
    "$aquarium_commit_name",
    "$aquarium_commit_email",
)

# Phrases the forbidden scan tolerates inside files that are never rewritten,
# each paired with the glob its tolerance is limited to. Podway requires the
# installed Procedure copies to match the bundled bytes, so v0.1.17's route
# labels and criteria that call the host-native review route "native Codex"
# must ship as upstream wrote them; the prose elsewhere says native Claude
# Code. Only the phrase is masked, and only where it starts a word, so a word
# such as "alternative" never hides behind it; every other needle still
# applies, and `check_canonical_phrases` stops generation when a phrase no
# longer occurs or its scope reaches a file a rule could rewrite. `fnmatch`
# lets `*` cross `/`.
CANONICAL_PHRASES: tuple[tuple[str, str], ...] = (
    ("assets/podway/procedures/*.yaml", "native Codex"),
    ("assets/podway/procedures/*.yaml", "Native Codex"),
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
    for name in ("skills", "hooks"):
        if not (UPSTREAM_PLUGIN / name).is_dir():
            raise SyncError(f"upstream is missing `{name}/`; refusing to generate")
    check_upstream_directories()
    check_upstream_files()
    check_excluded_plugin_root()


def check_upstream_directories() -> None:
    """Refuse to generate when upstream grows a directory nobody decided about.

    `COPIED_DIRECTORIES` is an allowlist with no counterpart check, so `hooks/`
    appeared upstream and was dropped in silence. Whether a new directory belongs
    in a Claude artifact is a decision, and skipping it is not a safe default.
    """
    known = (
        set(COPIED_DIRECTORIES)
        | {".codex-plugin"}
        | {name for name, _reason in EXCLUDED_PLUGIN_ROOT}
    )
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


def check_upstream_files() -> None:
    """Refuse to generate when upstream grows a plugin-root file nobody decided about.

    `check_upstream_directories` filters on `path.is_dir()`, and nothing copies a
    top-level file, so v0.1.15's `.mcp.json` would have vanished without a word:
    the same failure class the `hooks/` incident closed for directories, still
    open for files. Whether a plugin-root file belongs in a Claude Code artifact
    is a decision, and a file that reaches the generated tree needs a copier
    written for it rather than a silent default. The test is `not is_dir()` rather
    than `is_file()`, so it partitions the plugin root with the directory scan and
    an entry that is neither — a broken symlink — cannot fall between them.
    """
    known = {name for name, _reason in EXCLUDED_PLUGIN_ROOT}
    unknown = sorted(
        path.name
        for path in UPSTREAM_PLUGIN.iterdir()
        if not path.is_dir() and path.name not in known
    )
    if unknown:
        raise SyncError(
            "upstream has plugin-root files this transformation does not handle: "
            + ", ".join(unknown)
            + "; copy them deliberately or exclude them deliberately"
        )


def check_excluded_plugin_root() -> None:
    """Refuse a plugin-root exclusion whose target no longer exists upstream.

    Same contract as `check_excluded_files`: an exclusion that quietly stops
    applying would hide a differently named replacement behind a decision nobody
    made. The entry may name a directory or a file, so both shapes count.
    """
    for name, _reason in EXCLUDED_PLUGIN_ROOT:
        if not (UPSTREAM_PLUGIN / name).exists():
            raise SyncError(
                f"plugin-root exclusion targets `{name}`, which no longer exists "
                "upstream; remove the exclusion or retarget it"
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


def check_excluded_skills() -> None:
    """Refuse a skill exclusion whose skill no longer exists upstream.

    Same contract as `check_excluded_files`. An addition may not live under an
    excluded skill either: once the directory is gone, `apply_additions` could no
    longer see the collision that makes such a file an override's job.
    """
    for name, _reason in EXCLUDED_SKILLS:
        if not (UPSTREAM_PLUGIN / "skills" / name / "SKILL.md").is_file():
            raise SyncError(
                f"skill exclusion targets `{name}`, which upstream no longer ships; "
                "remove the exclusion or retarget it"
            )
        prefix = f"skills/{name}/"
        inside = [relative for relative in ADDED_PATHS if relative.startswith(prefix)]
        if inside:
            raise SyncError(
                f"additions live under the excluded skill `{name}`: " + ", ".join(inside)
            )


def check_canonical_phrases() -> None:
    """Refuse a canonical-phrase tolerance that no longer guards anything real.

    Each phrase must hold a forbidden needle, or the tolerance is dead weight;
    it must still occur upstream inside its scope, or it would mask the next
    phrase that happens to spell it; and its scope may reach only files no rule
    rewrites, because the tolerance exists only for bytes this artifact must not
    change.
    """
    needles = [needle for needle, _remedy in FORBIDDEN]
    for scope, phrase in CANONICAL_PHRASES:
        if not any(needle in phrase for needle in needles):
            raise SyncError(f"canonical phrase `{phrase}` holds no forbidden needle; remove it")
        scoped = [
            path
            for path in sorted(UPSTREAM_PLUGIN.rglob("*"))
            if path.is_file()
            and fnmatch.fnmatchcase(path.relative_to(UPSTREAM_PLUGIN).as_posix(), scope)
        ]
        rewritten = [path for path in scoped if rules_for(path) is not None]
        if rewritten:
            raise SyncError(
                f"canonical phrase scope `{scope}` reaches rewritten files: "
                + ", ".join(str(path.relative_to(UPSTREAM_PLUGIN)) for path in rewritten)
            )
        if not any(canonical_phrase_pattern(phrase).search(path.read_text(encoding="utf-8")) for path in scoped):
            raise SyncError(
                f"canonical phrase `{phrase}` no longer occurs upstream in `{scope}`; "
                "remove it so it cannot mask a future mention"
            )


def check_sigil_literals() -> None:
    """Refuse a sigil exception whose token no longer occurs in any source Markdown.

    The exception exists to stop one shell variable tripping the sigil scan. Once
    nothing writes that token, keeping the entry would blind the scan to a future
    skill sigil that happens to have the same name. Additions are read as well as
    upstream, because `check_sigils` scans them too and an edition-owned file may
    be the only thing that needs an exception.
    """
    source_markdown = "".join(
        path.read_text(encoding="utf-8")
        for root in (UPSTREAM_PLUGIN, ADDITIONS)
        for path in sorted(root.rglob("*.md"))
        if path.is_file()
    )
    dead = [literal for literal in SIGIL_LITERALS if literal not in source_markdown]
    if dead:
        raise SyncError(
            "sigil exceptions no longer occur in upstream or addition Markdown: "
            + ", ".join(dead)
            + "; remove each dead exception so it cannot mask a future sigil"
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


def decorate_frontmatter(
    text: str, skill_name: str, allow_implicit: bool, argument_hint: str | None
) -> str:
    """Add the Claude Code frontmatter keys the Codex sidecar cannot carry.

    `disable-model-invocation: true` is inserted when implicit invocation is
    off: Claude Code has no analogue of the Codex sidecar, so the policy has to
    move into the frontmatter, and Codex's own plugin validator rejects the key,
    which is precisely why the generated tree is a separate artifact.
    `argument-hint` is inserted for the skills in `ARGUMENT_HINTS`.
    """
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise SyncError(f"skill `{skill_name}` has no frontmatter block")
    body = match.group(1)
    for key in ("disable-model-invocation", "argument-hint"):
        if key in body:
            raise SyncError(f"skill `{skill_name}` already declares {key}")
    lines = [body]
    if argument_hint is not None:
        # Quoted: a hint such as `[version]` would otherwise parse as a YAML list.
        lines.append(f"argument-hint: {json.dumps(argument_hint)}")
    if not allow_implicit:
        lines.append("disable-model-invocation: true")
    if len(lines) == 1:
        return text
    return text.replace(match.group(0), "---\n" + "\n".join(lines) + "\n---\n", 1)


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


def remove_excluded_skills(destination: Path) -> list[str]:
    """Delete excluded skills whole, before any rule counts their text."""
    removed: list[str] = []
    for name, _reason in EXCLUDED_SKILLS:
        shutil.rmtree(destination / "skills" / name)
        removed.append(name)
    return removed


def transform_skills(destination: Path) -> None:
    skills = destination / "skills"
    names = sorted(p.name for p in skills.iterdir() if p.is_dir())
    unknown = sorted(set(ARGUMENT_HINTS) - set(names))
    if unknown:
        raise SyncError(
            "ARGUMENT_HINTS names skills upstream no longer ships: " + ", ".join(unknown)
        )
    for name in names:
        skill = skills / name
        allow_implicit = read_sidecar_policy(UPSTREAM_PLUGIN / "skills" / name)
        skill_md = skill / "SKILL.md"
        if not skill_md.is_file():
            raise SyncError(f"skill `{name}` has no SKILL.md")
        skill_md.write_text(
            decorate_frontmatter(
                skill_md.read_text(encoding="utf-8"),
                name,
                allow_implicit,
                ARGUMENT_HINTS.get(name),
            ),
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
        segments = relative.split("/")
        if (
            len(segments) == 3
            and segments[0] == "skills"
            and segments[2] == "SKILL.md"
            and "disable-model-invocation: true"
            not in source.read_text(encoding="utf-8")
        ):
            # An addition skill bypasses the sidecar-derived gating, so a
            # missing flag would ship a model-invocable mutating skill.
            raise SyncError(
                f"addition skill `{relative}` must declare "
                "disable-model-invocation: true in its own frontmatter"
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


def canonical_phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Match a tolerated phrase only where it starts a word."""
    return re.compile(rf"(?<![A-Za-z]){re.escape(phrase)}")


def mask_canonical_phrases(text: str, relative: Path) -> str:
    """Remove the tolerated phrases from one file's text before the needle scan."""
    for scope, phrase in CANONICAL_PHRASES:
        if fnmatch.fnmatchcase(relative.as_posix(), scope):
            text = canonical_phrase_pattern(phrase).sub("", text)
    return text


def check_forbidden(destination: Path, codex_exemptions: set[str]) -> None:
    """Scan every generated text file for host-specific text.

    Scripts and YAML are included. `CODEX_HOME` survives in the inspection script
    on purpose — a Claude Code user may also have Codex skills installed — and it
    is not a match, because the needle is `Codex` rather than `CODEX`.

    Only the `Codex` needle is skipped, and only for reviewed exemptions; every
    other needle applies to every file. A byte-canonical file has only its
    `CANONICAL_PHRASES` masked, so any other forbidden text in it still fails.
    """
    failures: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        relative = path.relative_to(destination)
        text = mask_canonical_phrases(path.read_text(encoding="utf-8"), relative)
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
    the reader's host does not have. `SIGIL_LITERALS` carries the named
    exceptions, each one a shell variable the pattern cannot tell apart.
    """
    failures: list[str] = []
    for path in sorted(destination.rglob("*.md")):
        if not path.is_file():
            continue
        found = sorted(
            token
            for token in set(SIGIL.findall(path.read_text(encoding="utf-8")))
            if token not in SIGIL_LITERALS
        )
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
    """Fail when generated text still names something an exclusion removed.

    Files are matched by basename. A skill is matched by its invocation and its
    directory paths, but not by its bare name: `status` is an ordinary word. An
    excluded plugin-root directory hides everything upstream puts under it, so
    a path into any of its children fails too — v0.1.17 added a second tool
    under the excluded `tools/` with no abort.
    """
    needles: list[tuple[str, re.Pattern[str] | str]] = [
        (relative, Path(relative).name) for relative, _reason in EXCLUDED_FILES
    ]
    for name, _reason in EXCLUDED_SKILLS:
        needles.append((f"skills/{name}", re.compile(rf"aquarium:{re.escape(name)}(?![A-Za-z0-9_-])")))
        needles.append((f"skills/{name}", f"skills/{name}/"))
        needles.append((f"skills/{name}", f"../{name}/"))
    for name, _reason in EXCLUDED_PLUGIN_ROOT:
        source = UPSTREAM_PLUGIN / name
        if source.is_dir():
            for child in sorted(source.iterdir()):
                needles.append((f"{name}/{child.name}", f"{name}/{child.name}"))
    failures: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for excluded, needle in needles:
            found = needle.search(text) if isinstance(needle, re.Pattern) else needle in text
            if found:
                failures.append(f"  {path.relative_to(destination)}: references excluded `{excluded}`")
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
    excluded_skills: list[str],
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
        "excluded_skills": excluded_skills,
        "excluded_plugin_root": [name for name, _reason in EXCLUDED_PLUGIN_ROOT],
        "additions": additions,
        "argument_hints": dict(sorted(ARGUMENT_HINTS.items())),
        "files": files,
    }
    (destination / SYNC_MANIFEST).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def generate(destination: Path) -> tuple[str, list[str]]:
    commit = upstream_commit()
    codex_exemptions = check_codex_exemptions()
    check_excluded_files()
    check_excluded_skills()
    check_sigil_literals()
    check_canonical_phrases()
    copy_tree(destination)
    excluded = remove_excluded(destination)
    excluded_skills = remove_excluded_skills(destination)
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
        destination,
        upstream_manifest()["repository"],
        commit,
        overrides,
        excluded,
        excluded_skills,
        additions,
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
        f"  {len(overrides)} overrides applied, "
        f"{len(EXCLUDED_FILES) + len(EXCLUDED_SKILLS) + len(EXCLUDED_PLUGIN_ROOT)} upstream entries excluded, "
        f"{len(ADDED_PATHS)} host-only files added"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

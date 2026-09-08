---
name: dev-setup-global
description: "Diagnose, install, and update Aquarium user-global development tools. Use when the user invokes /aquarium:dev-setup-global or a workflow reports a missing global CLI, paired skill, global MCP registration, service, Lore, Deslop, Humanizer, im-not-ai, or Ouroboros component. Use /aquarium:dev-setup for repository-local configuration."
disable-model-invocation: true
---

# Global Development Setup

Own user-global installation, exact-upstream freshness, upgrades, and services without inspecting or changing repository configuration.

Read the selected sections of [the shared tool catalog](../../references/tool-catalog.md). Do not read repository-local `.podway`, `.mulgae`, `.gaori`, `.sorage`, `.mcp.json`, AGENTS.md, or CLAUDE.md as global setup evidence.

## Diagnose Automatically

1. On a direct invocation without a component list, select every supported global component. On a scoped continuation, select only the named components and their direct prerequisites.
2. A direct invocation authorizes bounded read-only official metadata and raw-file freshness requests for all selected components. A scoped continuation authorizes only its selected sources. Disclose the official endpoints before contact.
3. Resolve this skill's directory and run `python3 <skill-directory>/scripts/inspect_global_tools.py --verify-dolgorae-release` on a direct unscoped invocation. For a scoped continuation, add one `--component <name>` argument for each selected component in catalog order, add `--verify-dolgorae-release` only when Dolgorae is selected, and run no unselected component probe.

   Outside Plan Mode, disclose the Sorage open-and-migrate diagnostic side effect, then add `--include-sorage-initialization` when Sorage is selected. The same disclosure applies to a scoped Sorage continuation.
4. Treat `--repository <existing-directory>` only as a compatibility input. Validate that it is an existing directory, but never use it as command or configuration scope, so diagnosis also works outside a Git worktree.
5. Diagnose local installation, supported version, canonical target, exact-upstream tree, duplicate and symlink state, paired-skill compatibility, services, and global MCP independently.
6. Do not ask the user to choose install, diagnose, or skip. Report current components without a question and propose actions only for missing, incompatible, unsafe, duplicated, or stale components.

If a freshness lookup, download, validation, or comparison fails, report `freshness_unverifiable`, clean ephemeral payloads, and do not propose installation or replacement from that payload.

## Owned Components

- Sanho, Dolgorae, Mulgae, Gaori, Sorage, and Podway user-global CLIs.
- `use-sanho`, `use-dolgorae`, `use-mulgae`, `use-gaori`, `use-gaori-status`, `use-sorage`, and `use-podway` under the configured Claude Code skill root — `$CLAUDE_CONFIG_DIR/skills` when that variable is set, otherwise `~/.claude/skills`.
- Mulgae and Gaori user-global MCP registrations.
- Podway's per-user production daemon and Sorage's minimal user-global initialization.
- Lora's `lore-commits` and `lore-query`, upstream Deslop, Humanizer, and im-not-ai's `humanize-korean`, `humanize`, and `humanize-redo` under that same skill root, with the four subagents im-not-ai's installer selects by default under the matching `agents/` directory.
- The Ouroboros CLI and its configuration. Its Claude Code integration arrives as a plugin rather than as per-home rules, skills, and MCP registration, so the component here is one installation: `--component ouroboros` reports the CLI version and the plugin-scoped MCP registration through the project inspector's probe, and there is no per-home readiness, home binding, MCP package pin, or release comparison to diagnose. Installing or upgrading the plugin itself belongs to `claude plugin`, not to this skill.
- Aquarium production-binary readiness requires supported global Podway, Mulgae, and Gaori executables and fails closed when any is missing. Sanho remains optional and is excluded from this baseline, and so is Dolgorae: no skill in this artifact routes a review through it, so its readiness is reported as third-party rather than gating Aquarium.

Do not install provider CLIs, authenticate, read credentials, contact providers, transmit repository source, initialize repository workspaces, change project MCP, edit repository guidance, start tests or reviews, or invoke Ouroboros workflows.

## Exact-Upstream and Update Policy

Use one exact supported release tag or disclosed full commit SHA according to the shared catalog. Verify downloaded archives, manifests, checksums, signatures, frontmatter, complete regular-file trees, and expected source provenance before proposing an action. Never install from a moving branch or execute unverified fetched content.

For each selected paired or third-party skill, compare the verified source with its canonical target. Treat missing or extra files, different bytes, invalid frontmatter, symlinks, and duplicate installations as independent gaps. The shipped inspector diagnoses only im-not-ai's `humanize-korean` skill; its other two skills and its four subagents are established by this comparison alone.

Apply this duplicate rule to shared-location skills. Other agent skill roots remain diagnostic evidence only. When another copy exists, report the duplicate risk and never create a known duplicate. Do not propose installation at the canonical target until the user separately approves removal or migration of the alternate copy so that one canonical target remains.

`dev-setup` trusting an existing canonical path is not freshness evidence.

## Respect Host Mode and Approval Boundaries

In Plan Mode, perform local and network read-only diagnosis and return exact proposals without mutation. Defer Sorage doctor or initialization checks that may update its database or journal to execution mode.

Outside Plan Mode, disclose any selected Sorage diagnostic side effect before running it. Keep release lookup, archive download, executable installation, skill installation or replacement, daemon changes, Sorage initialization, global MCP changes, and Ouroboros package changes and setup or refresh as distinct actions.

Before every persistent action:

1. Show the exact command, endpoints, targets, changed paths, expected side effects, and verification.
2. Establish the shared backup policy before the first overwrite or removal.
3. Obtain action-specific approval. Do not repeat approval for covered actions.
4. Re-read the target and invalidate approval if its snapshot changed.
5. Execute only the approved action and verify through the owning CLI and exact tree comparison.

## Apply the Shared Backup Policy

Use `Choose a Backup Policy for Existing State` in the shared tool catalog for every overwrite or removal. The shared policy owns the request-scoped choice, loss and recovery disclosure, restoration evidence, and the rule that preparing an incoming payload is not a backup.

Never use `sudo`, `--force`, unapproved removal, provider invocation, source transmission, staging, committing, or pushing. Tell the user when Claude Code must restart.

## Bundle Intake

Accept a bounded `dev-setup-bundle` handoff containing the manifest digest and union of selected global components. Prepare each global component at most once. Preserve all per-action approvals and return independent results for the bundle's target processing. Never read the manifest or infer repositories.

## Report

Report every selected component as current, missing, incompatible, different, duplicated, unsafe, or freshness-unverifiable; include resolved versions and sources, exact canonical targets, actions and exit status, backup and restoration evidence, cleanup, restart requirements, and remaining gaps. State explicitly that no repository configuration, staging, commit, or publication was performed.

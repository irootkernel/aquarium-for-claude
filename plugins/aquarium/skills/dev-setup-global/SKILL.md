---
name: dev-setup-global
description: "Diagnose, install, and update supported user-global development tools and integrations. Excludes Aquarium plugin installation or updates. Use when the user invokes /aquarium:dev-setup-global or a workflow reports a missing global CLI, paired skill, global MCP registration, service, Lore, Deslop, Humanizer, im-not-ai, or Ouroboros component. Use /aquarium:dev-setup for repository-local configuration."
disable-model-invocation: true
---

# Global Development Setup

> **Claude Code delegation:** when this skill, or a reference or Procedure node it follows, hands a step to another Aquarium skill — however it phrases the hand-off, and whether it writes `/aquarium:<name>` or names the skill bare — read that skill's `SKILL.md` in full from this plugin (`../<name>/SKILL.md` from this skill's directory) and follow it as the delegated step instead of calling the Skill tool. Claude Code reserves most Aquarium skills for the user to type: it refuses the Skill tool for them and, once it has refused, forbids carrying out their workflow any other way. When you hand such a step to a subagent, put that file's absolute path in its assignment and have it read the file, because a subagent cannot load a gated skill through the Skill tool. Running another skill's bundled script is not a hand-off. A continuation request, routed repair, offer, or recommendation that the text has you return or report to the user is not a delegation: name its slash command, do not run it yourself, and stop where the text stops.

Read [commit-attribution.md](../../references/commit-attribution.md) for message formatting and change origins, within this skill's existing effect boundaries.

Own installation, exact-upstream freshness, upgrades, and services for the supported components listed below without inspecting or changing repository configuration.

Adaptive launchers need an explicitly selected available Python environment with YAML and `jsonschema`. Reuse a compatible installed environment when available; end-user repositories need no Aquarium development checkout or `.venv`. Missing dependencies remain a diagnosed/manual prerequisite gap: no current Aquarium global component provisions both imports. Do not invent an installer or package pin. Any separately proposed environment provisioning needs its own supported source and authority; plugin update and repository configuration do not grant it. See [the Podway catalog](../../references/tool-catalog.md#podway).

## Check Request Scope Before Loading References

Aquarium plugin installation and updates belong to Claude Code's own plugin management — `claude plugin marketplace update aquarium-for-claude` and `claude plugin update aquarium@aquarium-for-claude`, or `/plugin` inside a session. A request to install or update only the Aquarium plugin, including a specific version, does not select this skill. If this skill was selected for that request, return to that flow before reading the tool catalog or running any diagnostic. Do not infer a global tool setup request from plugin installation.

Use this skill for an explicit global development setup request or a workflow continuation naming a global component that needs attention.

Read the selected sections of [the shared tool catalog](../../references/tool-catalog.md). Do not read repository-local `.podway`, `.mulgae`, `.gaori`, `.sorage`, `.mcp.json`, AGENTS.md, or CLAUDE.md as global setup evidence.

## Diagnose Automatically

1. On a direct invocation without a component list, select every supported global component. On a scoped continuation, select only the named components and their direct prerequisites.
2. A direct invocation authorizes disclosed read-only official release, tag, and commit metadata lookup for selected components. Only the six paired-tool sources receive the catalog's complete-tree and commit-pinned raw-file freshness comparison; selected Lora or Deslop also includes official npm installer metadata. A scoped continuation selects only its named sources. Follow the catalog's exact lookup boundary; materialization, installation and execution remain separate actions.
3. Resolve this skill's directory and run `python3 <skill-directory>/scripts/inspect_global_tools.py` on a direct unscoped invocation. For a scoped continuation, add one `--component <name>` argument for each selected component in catalog order and run no unselected component probe.

   Start Sorage with the version-only probe. Outside Plan Mode, disclose the native database and journal effects, then rerun a scoped Sorage inspection with `--component sorage --include-sorage-initialization`. The inspector skips a pre-Memo database, a missing database in a nonempty home, an incomplete or mismatched installation configuration, and an unverifiable state. After the catalog's v0.1.2 backup and restore preflight, add `--sorage-upgrade-preflight-complete` to distinguish a prepared pre-Memo database from one still needing preparation. On `upgrade_migration_required`, propose the catalog's separately approved native reconfiguration and rerun diagnosis after it succeeds. On `installation_recovery_required` or `upgrade_state_unverifiable`, preserve the installation and report the unresolved state without running doctor. The same rule applies to a scoped Sorage continuation.
4. Treat `--repository <existing-directory>` only as a compatibility input. Validate that it is an existing directory, but never use it as command or configuration scope, so diagnosis also works outside a Git worktree.
5. Diagnose local installation, supported version, canonical target, exact-upstream tree, duplicate and symlink state, paired-skill compatibility, services, and global MCP independently.
6. Do not ask the user to choose install, diagnose, or skip. Report current components without a question and propose actions only for missing, incompatible, unsafe, duplicated, or stale components.

When `dev-setup-bundle` supplies `required_global_mcp`, keep CLI, paired-skill, and other global component diagnosis for every selected tool, but require or prepare a Mulgae or Gaori global MCP registration only for names in that union. A selected tool with no global MCP request must not make local-only targets depend on global MCP readiness. Preserve any existing global registration; no MCP request means unrequested, not disabled.

If a freshness lookup, download, validation, or comparison fails, report `freshness_unverifiable`, clean ephemeral payloads, and do not propose installation or replacement from that payload.

## Owned Components

- Sanho, Dolgorae, Mulgae, Gaori, Sorage, and Podway user-global CLIs.
- `use-sanho`, `use-dolgorae`, `use-mulgae`, `use-gaori`, `use-gaori-status`, `use-sorage`, and `use-podway` under the configured Claude Code skill root — `$CLAUDE_CONFIG_DIR/skills` when that variable is set, otherwise `~/.claude/skills`.
- Mulgae and Gaori user-global MCP registrations.
- Podway's single Direct CLI identity and Sorage's minimal user-global initialization.
- Lora's `lore-commits` and `lore-query`, upstream Deslop, Humanizer, and im-not-ai's `humanize-korean`, `humanize`, and `humanize-redo` under that same skill root, with the four subagents im-not-ai's installer selects by default under the matching `agents/` directory.
- The Ouroboros CLI and its configuration. Its Claude Code integration arrives as a plugin rather than as per-home rules, skills, and MCP registration, so the component here is one installation: `--component ouroboros` reports the CLI version and the plugin-scoped MCP registration through the project inspector's probe, and there is no per-home readiness, home binding, MCP package pin, or release comparison to diagnose. Installing or upgrading the plugin itself belongs to `claude plugin`, not to this skill.
- Aquarium production-binary readiness requires supported global Podway, Mulgae, and Gaori executables and fails closed when any is missing. Dolgorae and Sanho remain optional and are excluded from this baseline. No skill in this artifact routes a review through Dolgorae, so its readiness is reported as third-party rather than gating Aquarium.

Do not install provider CLIs, authenticate, read credentials, contact providers, transmit repository source, initialize repository workspaces, change project MCP, edit repository guidance, start tests or reviews, or invoke Ouroboros workflows.

## Exact-Upstream and Update Policy

Use one exact supported release tag or disclosed full commit SHA according to the shared catalog. Verify downloaded archives, manifests, checksums, signatures, frontmatter, complete regular-file trees, and expected source provenance before proposing an action. Never install from a moving branch or execute unverified fetched content.

For each selected paired or third-party skill, compare the verified source with its canonical target. Treat missing or extra files, different bytes, invalid frontmatter, symlinks, and duplicate installations as independent gaps. The shipped inspector diagnoses only im-not-ai's `humanize-korean` skill; its other two skills and its four subagents are established by this comparison alone.

Apply this duplicate rule to shared-location skills. Other agent skill roots remain diagnostic evidence only. When another copy would be loaded beside the selected target, report the duplicate risk and never create a known duplicate. Do not propose installation at the canonical target until the user separately approves removal or migration of the conflicting copy.

`dev-setup` trusting an existing canonical path is not freshness evidence.

## Respect Host Mode and Approval Boundaries

In Plan Mode, perform local and network read-only diagnosis and return exact proposals without mutation. Defer Sorage doctor or initialization checks that may update its database or journal to execution mode.

Outside Plan Mode, use the version-only result to identify a pre-v0.1.2 installation before any Sorage doctor call. For an existing pre-Memo installation, prepare the upstream format-1 backup and separate restore drill before replacing the binary or opening it with v0.1.2. A v0.1.2 executable alone does not prove that preparation occurred. The inspector admits a missing or empty home and a database already carrying the Project Memo migration without upgrade confirmation; a nonempty home with no database or an incomplete installation configuration requires recovery. Disclose any selected Sorage diagnostic side effect before running it. Keep release lookup, archive download, executable installation, skill installation or replacement, legacy Podway service retirement, Sorage initialization or reconfiguration, global MCP changes, Ouroboros package changes, and Ouroboros setup or refresh as distinct actions.

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

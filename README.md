# Aquarium for Claude

Aquarium development skills packaged as a Claude Code plugin marketplace. This repository is a **generated artifact**: the source of truth is the Codex plugin at [irootkernel/aquarium](https://github.com/irootkernel/aquarium), pinned here as a submodule and transformed by `scripts/sync.py`.

By [Root Kernel](https://home.rootkernel.xyz) · Support: [cs@rootkernel.xyz](mailto:cs@rootkernel.xyz)

## Install

```bash
claude plugin marketplace add irootkernel/aquarium-for-claude
claude plugin install aquarium@aquarium-for-claude
```

Inside a session, use `/plugin marketplace add irootkernel/aquarium-for-claude` then `/plugin install aquarium@aquarium-for-claude`. Start a new session after installing or upgrading so the active session reloads the skill snapshot.

The generated plugin is committed, so installation never depends on the submodule being fetched.

### Migrating from Root Kernel

The plugin id and the command prefix both changed, so an existing installation does not upgrade in place.

```bash
claude plugin uninstall root-kernel@root-kernel-dev-claude-skills
claude plugin marketplace remove root-kernel-dev-claude-skills
claude plugin marketplace add irootkernel/aquarium-for-claude
claude plugin install aquarium@aquarium-for-claude
```

Repositories that used the Podway integration must finish or explicitly dispose of any active session before migrating, then replace the managed `root-kernel-{task,goal,validation}-v2.yaml` procedures through a separately approved `/aquarium:dev-setup` run. The inspection schema is now `aquarium-dev-setup-inspection.v7`.

## Skills

| Skill | Purpose | Invocation |
|---|---|---|
| `new-project` | Shape a greenfield project into an approved PRD and initial roadmap with Ouroboros, without implementing it. | `/aquarium:new-project` |
| `new-feature` | Shape one feature epic and its Design Gate impact for an existing project. | `/aquarium:new-feature` |
| `refactor` | Shape one refactor epic with compatibility, migration, rollback, and gate impact. | `/aquarium:refactor` |
| `war-room` | Diagnose one difficult bug and propose a task, epic, or incomplete investigation without a fix. | `/aquarium:war-room` |
| `design-qa` | Create, change, reactivate, or retire durable local Design Gates behind an approved exact diff. | `/aquarium:design-qa` |
| `epic-handler` | Orchestrate an epic through sequential task goals and a convergent epic-wide audit. | `/aquarium:epic-handler` with a roadmap path and one epic ID |
| `epic-validator` | Cold-validate a completed epic and converge confirmed gaps through remediation goals. | `/aquarium:epic-validator` with a roadmap path and one epic ID |
| `task-handler` | Strengthen the procedure around one task goal through focused phase skills and verified transitions. | `/aquarium:task-handler` with a roadmap path and one task ID |
| `task-commit` | Reconcile roadmap task lifecycle state and create one authorized commit that preserves unrelated work. | Automatic for commit requests, or `/aquarium:task-commit` |
| `release-handler` | Own one stable release lifecycle: settle the cumulative changelog, gate release QA, and publish one version behind separate approvals. | `/aquarium:release-handler` |
| `release-qa` | Exercise the current release candidate through read-only user scenarios covering every change since the previous stable release. | `/aquarium:release-qa` with an intended or confirmed version |
| `dev-setup` | Diagnose and configure selected development tools, and propose reference-based instruction-file guidance behind separate approvals. | `/aquarium:dev-setup` |
| `dev-setup-bundle` | Apply development-tool setup to explicit Git repositories from one external YAML manifest. | `/aquarium:dev-setup-bundle` with a manifest path |
| `test-setup` | Audit, propose, and configure the common Make or Bun testing contract for one repository, including evidence-backed legacy waivers. | `/aquarium:test-setup` |
| `docs-setup` | Audit, establish, adopt, or migrate the repository's canonical documentation structure and roadmap IDs. | `/aquarium:docs-setup` |
| `independent-review` | Run the canonical static review contract with fresh read-only reviewer subagents, then adjudicate their findings. | `/aquarium:independent-review` with a staged, commit, range, task, epic, or special-request target |
| `orca-review` | Run the same review contract through a user-selected Claude Fable, Kimi, Agy, or Cursor Agent in Orca, then adjudicate locally. | `/aquarium:orca-review` with a staged, commit, range, task, epic, or special-request target |

The five design skills drive Ouroboros as a bounded leaf capability and need it installed and pinned to `>=0.51.1,<0.52.0`; `/aquarium:dev-setup` diagnoses and configures it behind separate approvals. They shape documents only and never implement.

`task-handler` loads seven phase skills in order — `task-plan`, `task-implement`, `task-verify`, `task-refine`, `task-document`, `task-review`, `task-close`. Invoke one directly only to resume that exact phase with its required task context.

Both review skills share one backend-neutral contract, `references/review-contract.md`, which owns target selection, the dirty decision, static-review limits, and the result envelope, plus one target inspector shipped inside `independent-review`. `orca-review` drives the Orca app rather than host subagents, so it also loads `references/orca-supervision.md` and needs the separately installed `orca-cli` Claude Code skill in the active catalog and a running Orca app; it loads Orca's orchestration guide through the Orca executable itself and stops, rather than approximating that contract, when the skill is absent. `independent-review` remains the subagent-based path, starts no Orca worker, and needs nothing extra.

### Roadmap commit guard

The plugin ships a `PreToolUse` hook that inspects `Bash` commands and denies a direct `git commit` in a repository whose tracked roadmap carries task lifecycle state, routing it through `task-commit` instead. The hook is local, reads only the proposed command and the working directory, and fails open when it cannot parse its input. Because Claude Code merges an enabled plugin's hooks with your own, review it under `/hooks` after installing.

### Bundled reviewer subagent

The plugin ships one subagent, `aquarium:independent-reviewer`, from `additions/agents/`. It has no upstream counterpart: Codex has no plugin subagents, so upstream's review skill leans on Orca, and the Claude override leaned on prose asking for "a subagent type without editing tools". The bundled agent turns the two requirements that matter into configuration — a tool allowlist of `Read`, `Grep`, `Glob`, and `Bash` with no editing tool, and `model: opus` — and carries a review-focused system prompt derived from the skill's reviewer requirements. Bash stays in the allowlist because a reviewer must read `git diff --cached` and `git show`; its read-only discipline is plan mode plus the prompt, which is stated rather than hidden. The cost is that the agent's description is loaded into every session where the plugin is enabled, which is why it is worded narrowly and negatively; the skill falls back to any editing-free subagent type when the bundled one is absent.

### Invocation gating

Every skill except `task-commit` carries `disable-model-invocation: true`, so Claude cannot start it on its own; you invoke it with `/aquarium:<skill>`. Several of these skills stage, commit, or mutate roadmap state, and the upstream workflow requires explicit invocation. The flag is derived from each upstream skill's `agents/openai.yaml` at sync time, so it can never disagree with the Codex policy.

The skills that take arguments also carry an `argument-hint`, which Claude Code shows after the command name in the `/` menu — `/aquarium:epic-handler <roadmap-path> <epic-id>`, for example. The Codex sidecar has no counterpart, so the hints come from one table in `scripts/sync.py`, recorded in the sync manifest and asserted against every skill's frontmatter; a skill that upstream drops stops the sync rather than leaving a stale hint.

This is also why the plugin is a separate artifact rather than a second manifest in the upstream repository: Codex's plugin validator rejects `disable-model-invocation` outright, while Claude Code needs it for the same guarantee.

## How generation works

```
upstream/                        git submodule, pinned to one upstream commit
  plugins/aquarium/              the Codex plugin — never edited here
overrides/
  manifest.json                  path → SHA-256 of the upstream file each override was derived from
  codex-exemptions.json          path → SHA-256 of an upstream file whose remaining "Codex" mentions were reviewed
  skills/...                     full-file replacements for host-specific divergence
additions/
  agents/...                     host-only files with no upstream counterpart
scripts/sync.py                  the transformation
plugins/aquarium/                generated output, committed
  agents/                        the bundled reviewer subagent
  hooks/                         the roadmap commit guard
  sync-manifest.json             upstream commit, overrides, exclusions, and per-file hashes
```

`sync.py` copies the upstream plugin, drops the files excluded by name, applies literal substitutions, applies overrides, derives invocation gating from the upstream sidecars and drops them, then adds the host-only files. It refuses to run against an empty submodule, refuses to run when upstream grows a directory the transformation does not handle, fails if host-specific text survives, fails if a substitution rule matched nothing that ships, and fails if a generated script cannot run.

Four files diverge semantically and are kept as overrides rather than substitutions:

| Override | Why |
|---|---|
| `skills/independent-review/SKILL.md` | Keeps upstream's shared review contract and target inspector but replaces its Orca-and-Codex backend with fresh read-only subagents dispatched through the host's own mechanism, preferring the bundled `aquarium:independent-reviewer`. A reviewer runs under the same provider as the coordinator, so the skill claims a fresh context rather than an independent provider, keeps depth on Opus and breadth on Sonnet, and buys coverage by giving several reviewers distinct lenses. The shared contract is written for one out-of-process reviewer, so the override also maps its singular reviewer, verdict, and backend-lifecycle fields onto one row per dispatched subagent. |
| `skills/dev-setup/SKILL.md` | Keeps upstream's AGENTS.md-canonical repository guidance and verifies the CLAUDE.md delegation as a real `@AGENTS.md` import; offers Mulgae and Gaori MCP as a user-scope registration with `.mcp.json` as the explicit project override. The two-stage approval gate is unchanged. |
| `skills/dev-setup/references/agents-guidance.md` | Same four-section structure as upstream. Claude Code does not read `AGENTS.md` on its own but does resolve a `@AGENTS.md` import before the first turn, so the delegation file carries the import rather than a request to go read the file, and diagnosis reports prose-only delegation as a gap. |
| `skills/dev-setup/references/tool-catalog.md` | Registers Mulgae and Gaori MCP with `claude mcp add -s user`, keeps `.mcp.json` as the explicit project override, and verifies the user, project, and effective views from the configuration files rather than from `.codex/config.toml` and typed `codex mcp get --json` output. |

Everything else is a literal substitution: the `$aquarium:` sigil becomes `/aquarium:`, the `$use-*` skill sigils become `/use-*`, the Ouroboros sigils `$interview`, `$pm`, `$seed`, and `$qa` become `/ouroboros:*` because Ouroboros installs as a Claude Code plugin rather than user-scoped skills, the separately installed `$deslop` becomes `/deslop`, `request_user_input` becomes `AskUserQuestion`, Lora installs with `--agent claude-code`, the inspection script resolves skills from the Claude Code roots alone — `CLAUDE_CONFIG_DIR` and `~/.claude/skills` — and diagnoses Ouroboros against this host instead of Codex, user-scoped skills install into `~/.claude/skills`, upstream's shared Orca supervision reference loses its `independent-review` clause because this port dispatches host subagents rather than an Orca worker, `orca-review`'s `non-Codex` becomes `third-party` because the reviewer it is contrasted with is a Claude subagent here, and the hook command resolves `${CLAUDE_PLUGIN_ROOT}` instead of Codex's `${PLUGIN_ROOT}`.

That last one is load-bearing. `PLUGIN_ROOT` is unset under Claude Code, so the unsubstituted command expands to `/hooks/task_commit_gate.py`, `python3` exits 2, and `PreToolUse` reads exit 2 as a denial — blocking every `Bash` call. A forbidden needle and a required-text assertion both guard it.

Upstream diagnoses Ouroboros by asking Codex — `ooo codex doctor` for its integration artifacts and `codex mcp get ouroboros --json` for its registration. Copied verbatim, neither component can ever report `configured` under Claude Code, and because the readiness rollup requires all four, Ouroboros would report `degraded` forever and every design skill would stay blocked. The generated inspector probes `claude mcp get plugin:ouroboros:ouroboros` instead: Ouroboros ships its Claude Code integration as a plugin, so a name that resolves proves the plugin is installed and enabled and therefore that the `/ouroboros:*` skills are reachable, while its `Status:` line carries the server's health. The skills do not need the server, so a resolved but unconnected entry degrades the registration and leaves the integration intact. Two required-text assertions guard the block match.

Skill discovery narrows for the same reason. Upstream resolves user-scoped skills from the Codex and shared cross-agent roots, and the first version of this fork merely added `~/.claude/skills` alongside them. That reported a skill installed only in another host's root as present here, where it cannot be invoked, and counted a cross-host copy of a skill as a duplicate installation — which upstream's provenance rules reject, so correctly installed paired skills came back degraded. The generated inspector now resolves the Claude Code roots alone, and `dev-setup` installs user-scoped skills into `~/.claude/skills`, because one host's artifact should diagnose one host.

An unmapped sigil is the quiet failure: it is valid Markdown naming a command the reader's host does not have, so neither a forbidden needle nor a required-text assertion notices it, and one needle per known sigil only ever catches the sigils that already exist. Generation therefore rejects any remaining lowercase `$name` in generated Markdown, which is what caught the five Ouroboros and Deslop sigils upstream introduced in v0.1.9. Uppercase spellings are environment variables the generated tree still needs and do not match.

A literal substitution rule fails just as quietly in the other direction. v0.1.10 dropped one Oxford comma from `Ouroboros package, Codex, and runtime components` and the rule stopped matching without a word, and three script rules died in the same release when upstream extracted a shared helper and added a parameter. Every rule must now rewrite text that ships: generation counts matches outside the override targets and fails naming any rule that matched nothing, so a dead rule is deleted or re-derived deliberately instead of rotting. The phrases that only ever occurred inside an override target were deleted for the same reason; the forbidden needles and the sigil scan still catch that text if an override is ever retired.

A block substitution that drifts can also produce a script that parses but cannot run. Generation compiles every generated script and checks that each call to a function defined in the same file passes an argument count its signature accepts, which is precisely what the second parameter v0.1.10 added to `classify_ouroboros_registration` would otherwise have broken on every inspection.

Upstream removed `assets/logo-*.png` and the manifest's `composerIcon` and `logo` fields in v0.1.10, so the generated manifest simply loses `metadata.icon` and `metadata.logo`. It also added a 2.3 MB `assets/hero.png` banner for its own README, which nothing in the plugin references and Claude Code never renders. That file is excluded by name, with the exclusion gated on the file still existing upstream and on no generated text naming it, so it cannot quietly stop applying or quietly hide a reference.

The `Codex` name is otherwise forbidden in generated text. One file is exempt: `tool-catalog.md` names the Codex CLI as a Mulgae review provider and a required CLI version, which stays true here. The exemption records the upstream digest it was judged against, so the sync stops when that file changes. v0.1.11 rewrote `orca-review/references/provider-contracts.md` around named providers and left no `Codex` mention in it, so that exemption was retired rather than rotated.

The Mulgae and Gaori MCP probes are re-targeted for the same reason. Upstream reads them through `codex mcp get --json`, with `CODEX_HOME` pointed at `.codex/` for the local view, so on this host the inspector could never see the registration its own catalog tells the user to create, and `--require-mulgae-mcp` reported the tool degraded forever. The generated inspector reads Claude Code's three views from configuration alone — the user-scope entry and the private per-project entry from `.claude.json`, honouring `CLAUDE_CONFIG_DIR`, and the shared entry from `.mcp.json` with its approval state — and derives the effective view from the documented precedence. It deliberately never calls `claude mcp get`, because that health-checks an approved server and so starts it, and setup must not start the server. A `.mcp.json` server that nobody has approved yet is `unverifiable` with `registration_pending_approval`, not degraded. Two whole functions are replaced so the anchors are the most stable text upstream has, and `tests/test_claude_mcp_inspection.py` exercises the shipped bytes against configuration fixtures under a private `CLAUDE_CONFIG_DIR`.

## Upgrade

```bash
git submodule update --init --recursive
git -C upstream fetch --tags origin
git -C upstream checkout <new-tag>
python3 scripts/sync.py
ruby tests/validate.rb
git add -A && git commit
```

Each override records the SHA-256 of the upstream file it came from. When upstream changes one of those files the sync stops and names it, because merging a stale override would ship guidance that no longer matches its source. Re-derive the override against the new upstream content and update `overrides/manifest.json`.

## Validate

```bash
python3 scripts/sync.py --check
ruby tests/validate.rb
python3 -m unittest tests/test_claude_mcp_inspection.py
git diff --check
claude plugin validate --strict plugins/aquarium
```

`--check` regenerates into a temporary directory and fails if the committed output drifted. The Ruby validation covers only what this repository is responsible for — invocation gating against the upstream sidecars, host-neutral generated text, the commit hook's Claude Code contract, byte-identical Podway procedures, manifest agreement, deliberate exclusions, compiled generated scripts, and the marketplace shape. The Python test covers the one piece of behaviour this repository authors, the Claude Code MCP inspection. Upstream owns the prose contract and validates it in its own CI. The last command is Claude Code's own plugin validator and runs locally rather than in CI.

## Documentation style

Do not hard-wrap prose. Keep each prose paragraph on one source line; use line breaks only for structural Markdown, code, tables, lists, or other syntax where the break is meaningful.

## License

MIT, inherited from upstream. This repository vendors no third-party skill source: Deslop and Lora are installed from their own upstream repositories by `/aquarium:dev-setup`, each keeping its original licence.

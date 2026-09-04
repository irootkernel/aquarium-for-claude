# Aquarium for Claude

Aquarium development skills packaged as a Claude Code plugin marketplace. This repository is a **generated artifact**: the source of truth is the Codex plugin at [irootkernel/aquarium](https://github.com/irootkernel/aquarium), pinned here as a submodule and transformed by `scripts/sync.py`.

English · [한국어](README.ko.md)

By [Root Kernel](https://home.rootkernel.xyz) · Support: [cs@rootkernel.xyz](mailto:cs@rootkernel.xyz)

## Aquarium Editions

- [Aquarium](https://github.com/irootkernel/aquarium) — Codex
- [Aquarium for Kimi](https://github.com/irootkernel/aquarium-for-kimi)
- [Aquarium for GLM](https://github.com/irootkernel/aquarium-for-glm)

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

Repositories that used the Podway integration must finish or explicitly dispose of any active session before migrating, then replace the managed `root-kernel-{task,goal,validation}-v2.yaml` procedures through a separately approved `/aquarium:dev-setup` run. The inspection schema is now `aquarium-dev-setup-inspection.v10`.

## Skills

| Skill | Purpose | Invocation |
|---|---|---|
| `new-project` | Shape a greenfield project into an approved PRD and initial roadmap with Ouroboros, without implementing it. | `/aquarium:new-project` |
| `new-feature` | Shape one feature epic for an existing project without implementing it. | `/aquarium:new-feature` |
| `refactor` | Shape one refactor epic with compatibility, migration, and rollback impact. | `/aquarium:refactor` |
| `war-room` | Diagnose one difficult bug and propose a task, epic, or incomplete investigation without a fix. | `/aquarium:war-room` |
| `epic-handler` | Orchestrate an epic through sequential task goals and a convergent epic-wide audit. | `/aquarium:epic-handler` with a roadmap path and one epic ID |
| `epic-validator` | Cold-validate a completed epic and converge confirmed gaps through remediation goals. | `/aquarium:epic-validator` with a roadmap path and one epic ID |
| `task-handler` | Strengthen the procedure around one task goal through focused phase skills and verified transitions. | `/aquarium:task-handler` with a roadmap path and one task ID |
| `task-commit` | Reconcile roadmap task lifecycle state and create one authorized commit that preserves unrelated work. | Automatic for commit requests, or `/aquarium:task-commit` |
| `release-handler` | Own one stable release lifecycle: settle the cumulative changelog, gate release QA, and publish one version behind separate approvals. | `/aquarium:release-handler` with an intended or planned version |
| `release-qa` | Exercise the current release candidate through read-only user scenarios covering every change since the previous stable release. | `/aquarium:release-qa` with an intended or confirmed version |
| `dev-setup` | Diagnose and configure selected development tools, and propose reference-based instruction-file guidance behind separate approvals. | `/aquarium:dev-setup` |
| `dev-setup-bundle` | Apply development-tool setup to explicit Git repositories from one external YAML manifest. | `/aquarium:dev-setup-bundle` with a manifest path |
| `aquarium-dev` | Diagnose, enroll, and expose the isolated Aquarium development channel that builds local-main tool artifacts under `~/.aquarium-dev`. | `/aquarium:aquarium-dev` |
| `test-setup` | Audit, propose, and configure the common Make or Bun testing contract for one repository, including evidence-backed legacy waivers. | `/aquarium:test-setup` |
| `docs-setup` | Audit, establish, adopt, or migrate the repository's canonical documentation structure and roadmap IDs. | `/aquarium:docs-setup` |
| `independent-review` | Run the canonical static review contract with fresh read-only reviewer subagents, then adjudicate their findings. | `/aquarium:independent-review` with a staged, `HEAD`, commit, range, task, epic, or special-request target |
| `orca-review` | Run the same review contract through a requested native reviewer that Orca owns and supervises, then adjudicate locally. | Automatic when you name both a target and a reviewer, or `/aquarium:orca-review` with a staged, `HEAD`, commit, range, task, epic, or special-request target |
| `upgrade` | Adopt a newly released upstream Aquarium version in this generator repository through orchestrated subagents, then publish the reviewed tag and GitHub Release. | `/aquarium:upgrade` with an optional released upstream version |

The four design skills drive Ouroboros as a bounded leaf capability and need it installed and pinned to `>=0.51.1,<0.52.0`; `/aquarium:dev-setup` diagnoses and configures it behind separate approvals. They shape documents only and never implement.

`task-handler` loads seven phase skills in order — `task-plan`, `task-implement`, `task-refine`, `task-verify`, `task-document`, `task-review`, `task-close`. Invoke one directly only to resume that exact phase with its required task context.

Both review skills share one contract, `references/review-contract.md`, which owns the source scopes, consent, static-review limits, and the result envelope, plus `references/finding-disposition.md` for adjudication, and one target inspector and one repository-state inspector shipped inside `independent-review`. `orca-review` drives the Orca app rather than host subagents, so it also loads `references/orca-supervision.md` and needs the separately installed `orca-cli` Claude Code skill in the active catalog and a running Orca app; it loads Orca's orchestration guide through the Orca executable itself and stops, rather than approximating that contract, when the skill is absent. `independent-review` remains the subagent-based path, starts no Orca worker, uses no Dolgorae capture, and needs nothing extra. Because neither backend holds an immutable capture here, both support the same four scopes — `staged`, `head`, `commit`, and `range` — and upstream's capture-only `workspace` and `dirty` scopes are unsupported.

### Roadmap commit guard

The plugin ships a `PreToolUse` hook that inspects `Bash` commands and denies a direct `git commit` in a repository whose tracked roadmap carries task lifecycle state, routing it through `task-commit` instead. The hook is local, reads only the proposed command and the working directory, and fails open when it cannot parse its input. Because Claude Code merges an enabled plugin's hooks with your own, review it under `/hooks` after installing.

### Bundled reviewer subagent

The plugin ships one subagent, `aquarium:independent-reviewer`, from `additions/agents/`. It has no upstream counterpart: Codex has no plugin subagents, so upstream's review skill leans on Orca, and the Claude override leaned on prose asking for "a subagent type without editing tools". The bundled agent turns the two requirements that matter into configuration — a tool allowlist of `Read`, `Grep`, `Glob`, and `Bash` with no editing tool, and `model: opus` — and carries a review-focused system prompt derived from the skill's reviewer requirements. Bash stays in the allowlist because a reviewer must read `git diff --cached` and `git show`; its read-only discipline is plan mode plus the prompt, which is stated rather than hidden. The prompt also carries the one boundary an in-session reviewer cannot inherit from its tools: a subagent runs as the same operating-system user in the same worktree, so reading the target through Git objects rather than working-tree copies, and leaving the excluded dirty remainder unopened, is a rule rather than a sandbox. The cost is that the agent's description is loaded into every session where the plugin is enabled, which is why it is worded narrowly and negatively; the skill falls back to any editing-free subagent type when the bundled one is absent.

### Edition upgrade skill

The plugin ships one edition-owned skill, `upgrade`, from `additions/skills/`. It has no upstream counterpart because it operates this generator repository itself: it pins the submodule to a released upstream tag, resolves every sync abort through orchestrated Opus and Sonnet subagents while the invoking conversation decides, reviews, and validates, and publishes the reviewed tag, GitHub Release, and local installation refresh behind explicit approvals. It refuses to run outside this repository, and its `references/rederivation.md` records the override re-derivation method and the adoption traps that are invisible in the code. Like every addition it is authored in final form: the gating flag is self-declared, generation refuses a skill addition without it, and `tests/validate.rb` asserts that a sidecar-less skill is a recorded addition and gated.

### Invocation gating

Every skill except `task-commit` and `orca-review` carries `disable-model-invocation: true`, so Claude cannot start it on its own; you invoke it with `/aquarium:<skill>`. Several of these skills stage, commit, or mutate roadmap state, and the upstream workflow requires explicit invocation. Upstream opened `orca-review` in v0.1.14 on the same bounded trigger as `task-commit`: naming both a review target and a reviewer is itself the request. The flag is derived from each upstream skill's `agents/openai.yaml` at sync time, so it can never disagree with the Codex policy; the edition-owned `upgrade` skill has no sidecar, so it declares the flag itself and both generation and validation assert it.

The skills that take arguments also carry an `argument-hint`, which Claude Code shows after the command name in the `/` menu — `/aquarium:epic-handler <roadmap-path> <epic-id>`, for example. The Codex sidecar has no counterpart, so the hints come from one table in `scripts/sync.py`, recorded in the sync manifest and asserted against every upstream skill's frontmatter; a skill that upstream drops stops the sync rather than leaving a stale hint, and the edition-owned `upgrade` skill carries its hint inline because that table deliberately rejects names upstream does not ship.

This is also why the plugin is a separate artifact rather than a second manifest in the upstream repository: Codex's plugin validator rejects `disable-model-invocation` outright, while Claude Code needs it for the same guarantee.

## How generation works

```
upstream/                        git submodule, pinned to one upstream commit
  plugins/aquarium/              the Codex plugin — never edited here
overrides/
  manifest.json                  path → SHA-256 of the upstream file each override was derived from
  codex-exemptions.json          path → SHA-256 of an upstream file whose remaining "Codex" mentions were reviewed
  skills/... references/...      full-file replacements for host-specific divergence
additions/
  agents/...                     host-only plugin subagents with no upstream counterpart
  skills/...                     edition-owned skill files, carried into the generated plugin
scripts/sync.py                  the transformation
plugins/aquarium/                generated output, committed
  agents/                        the bundled reviewer subagent
  hooks/                         the roadmap commit guard
  sync-manifest.json             upstream commit, overrides, exclusions, and per-file hashes
```

`sync.py` copies the upstream plugin, drops the files excluded by name, applies literal substitutions, applies overrides, derives invocation gating from the upstream sidecars and drops them, then adds the host-only files — the bundled reviewer subagent, the edition-owned `upgrade` skill, which must declare its own gating or generation refuses it, and the repository-state inspector `independent-review` runs. It refuses to run against an empty submodule, refuses to run when upstream grows a directory the transformation does not handle, fails if host-specific text survives, fails if a substitution rule matched nothing that ships, and fails if a generated script cannot run.

Five files diverge semantically and are kept as overrides rather than substitutions:

| Override | Why |
|---|---|
| `references/review-contract.md` | v0.1.14 rewrote the shared contract around upstream's new backend split and bound independent review to a Dolgorae immutable capture running a fresh Codex Reviewer. Neither half is true here, and the divergence runs through the scope table, backend ownership, settlement, and the result envelope rather than through one clause. The override keeps upstream's scope meanings, consent, static limits, and disposition rules, marks the two capture-only scopes unsupported for the same reason they are unsupported for Orca Review, and replaces the capture with a repository-state baseline that proves nobody mutated the repository during the review rather than that the target was immutable. |
| `skills/independent-review/SKILL.md` | Replaces upstream's Dolgorae-and-Codex backend with fresh read-only subagents dispatched through the host's own mechanism, preferring the bundled `aquarium:independent-reviewer`. A reviewer runs under the same provider as the coordinator, so the skill claims a fresh context rather than an independent provider, keeps depth on Opus and breadth on Sonnet, and buys coverage by giving several reviewers distinct lenses. The shared contract is written for one out-of-process reviewer, so the override also maps its singular reviewer, verdict, and backend-lifecycle fields onto one row per dispatched subagent. |
| `skills/dev-setup/SKILL.md` | Keeps upstream's AGENTS.md-canonical repository guidance and verifies the CLAUDE.md delegation as a real `@AGENTS.md` import; offers Mulgae and Gaori MCP as a user-scope registration with `.mcp.json` as the explicit project override. The two-stage approval gate is unchanged. |
| `skills/dev-setup/references/agents-guidance.md` | Same four-section structure as upstream. Claude Code does not read `AGENTS.md` on its own but does resolve a `@AGENTS.md` import before the first turn, so the delegation file carries the import rather than a request to go read the file, and diagnosis reports prose-only delegation as a gap. |
| `skills/dev-setup/references/tool-catalog.md` | Registers Mulgae and Gaori MCP with `claude mcp add -s user`, keeps `.mcp.json` as the explicit project override, and verifies the user, project, and effective views from the configuration files rather than from `.codex/config.toml` and typed `codex mcp get --json` output. |

Everything else is a literal substitution: the `$aquarium:` sigil becomes `/aquarium:`, the `$use-*` skill sigils become `/use-*`, the `$create-podway-procedure` maintainer-skill sigil becomes `/create-podway-procedure`, the Ouroboros sigils `$interview`, `$pm`, `$seed`, and `$qa` become `/ouroboros:*` because Ouroboros installs as a Claude Code plugin rather than user-scoped skills, the separately installed `$deslop` becomes `/deslop`, `request_user_input` becomes `AskUserQuestion` — and task-close's "when available" hedge on it is dropped, because the tool is always present on this host, Lora installs with `--agent claude-code`, the `Codex goal` a workflow mirrors becomes the Claude Code todo list — written through `TodoWrite` where the Ouroboros integration names the mechanism — the inspection script resolves skills from the Claude Code roots alone — `CLAUDE_CONFIG_DIR` and `~/.claude/skills` — and diagnoses Ouroboros against this host instead of Codex, user-scoped skills install into `~/.claude/skills`, `release-qa`'s host-neutral "available agent delegation surface" becomes the Task tool with parallel clusters launched in a single message, `orca-review` loses its referral to independent review for the two capture-only scopes because neither backend supports them here, the shared disposition contract stops grouping independent review with the backends that capture, the writing-skill inspection expects Humanizer and im-not-ai in the Claude Code skill root rather than the shared cross-agent root and the Codex home, and the hook command resolves `${CLAUDE_PLUGIN_ROOT}` instead of Codex's `${PLUGIN_ROOT}`.

That last one is load-bearing. `PLUGIN_ROOT` is unset under Claude Code, so the unsubstituted command expands to `/hooks/task_commit_gate.py`, `python3` exits 2, and `PreToolUse` reads exit 2 as a denial — blocking every `Bash` call. A forbidden needle and a required-text assertion both guard it.

Upstream diagnoses Ouroboros by asking Codex — `ooo codex doctor` for its integration artifacts and `codex mcp get ouroboros --json` for its registration. Copied verbatim, neither component can ever report `configured` under Claude Code, and because the readiness rollup requires all four, Ouroboros would report `degraded` forever and every design skill would stay blocked. The generated inspector probes `claude mcp get plugin:ouroboros:ouroboros` instead: Ouroboros ships its Claude Code integration as a plugin, so a name that resolves proves the plugin is installed and enabled and therefore that the `/ouroboros:*` skills are reachable, while its `Status:` line carries the server's health. The skills do not need the server, so a resolved but unconnected entry degrades the registration and leaves the integration intact. The runtime component follows the same reasoning: upstream v0.1.13 runs `ooo mcp doctor --json` only when Codex directly launches the selected executable and accepts its isolated `uvx` launcher from the registration alone, and the plugin-scoped registration is exactly that isolated launcher's Claude analog, so the generated inspector derives `mcp_runtime` from it as `plugin_launcher_configured` and never runs the doctor, whose `mcp_import` check fails by design in the CLI's own MCP 1.x environment. Required-text assertions guard the block matches.

Skill discovery narrows for the same reason. Upstream resolves user-scoped skills from the Codex and shared cross-agent roots, and the first version of this fork merely added `~/.claude/skills` alongside them. That reported a skill installed only in another host's root as present here, where it cannot be invoked, and counted a cross-host copy of a skill as a duplicate installation — which upstream's provenance rules reject, so correctly installed paired skills came back degraded. The generated inspector now resolves the Claude Code roots alone, and `dev-setup` installs user-scoped skills into `~/.claude/skills`, because one host's artifact should diagnose one host.

An unmapped sigil is the quiet failure: it is valid Markdown naming a command the reader's host does not have, so neither a forbidden needle nor a required-text assertion notices it, and one needle per known sigil only ever catches the sigils that already exist. Generation therefore rejects any remaining lowercase `$name` in generated Markdown, which is what caught the five Ouroboros and Deslop sigils upstream introduced in v0.1.9. Uppercase spellings are environment variables the generated tree still needs and do not match.

Not every lowercase `$name` is a sigil, though, and v0.1.14 proved it: `task-commit` pins the commit identity through `git -c user.name="$aquarium_commit_name"`, a shell variable the scan read as an unmapped invocation. Dropping `_` from the pattern would close that case and silently admit any future `$snake_case` skill, so the exceptions are named instead. Each one must still occur in upstream Markdown, or generation stops and asks for it to be removed, and the two lists — one in `scripts/sync.py`, one in `tests/validate.rb` — are compared as sets like the forbidden needles.

A literal substitution rule fails just as quietly in the other direction. v0.1.10 dropped one Oxford comma from `Ouroboros package, Codex, and runtime components` and the rule stopped matching without a word, and three script rules died in the same release when upstream extracted a shared helper and added a parameter. Three script rules died again in v0.1.13, when upstream extracted the Ouroboros transport comparison into two launcher matchers and split the runtime component across the installed and not-installed paths, and were re-derived against the new anchors. Every rule must now rewrite text that ships: generation counts matches outside the override targets and fails naming any rule that matched nothing, so a dead rule is deleted or re-derived deliberately instead of rotting. The phrases that only ever occurred inside an override target were deleted for the same reason; the forbidden needles and the sigil scan still catch that text if an override is ever retired.

A block substitution that drifts can also produce a script that parses but cannot run. Generation compiles every generated script and checks that each call to a function defined in the same file passes an argument count its signature accepts, which is precisely what the second parameter v0.1.10 added to `classify_ouroboros_registration` would otherwise have broken on every inspection.

Upstream removed `assets/logo-*.png` and the manifest's `composerIcon` and `logo` fields in v0.1.10, so the generated manifest simply loses `metadata.icon` and `metadata.logo`. It also added a 2.3 MB `assets/hero.png` banner for its own README, which nothing in the plugin references and Claude Code never renders. That file is excluded by name, with the exclusion gated on the file still existing upstream and on no generated text naming it, so it cannot quietly stop applying or quietly hide a reference.

v0.1.14 added the second exclusion. Upstream routed independent review through a Dolgorae immutable capture that runs a Codex Reviewer, and shipped `references/dolgorae-review-contract.md` to define that backend's candidate, capture, and settlement rules. This artifact dispatches host subagents instead, and its `orca-review` is forbidden to use Dolgorae, so nothing here routes through that contract and it would document a lifecycle the edition does not have. Dolgorae itself stays in the tool catalog as a selectable third-party CLI; only the consumer contract is dropped, and the same reference check keeps the two review overrides from naming it.

The `Codex` name is otherwise forbidden in generated text. Three files are exempt: `tool-catalog.md` names the Codex CLI as a Mulgae review provider and a required CLI version, which stays true here, and v0.1.14's new `aquarium-dev` skill and its development contract name the other host as a third party — six of their seven mentions are constraints on what the development channel must never touch, and the seventh names the Codex plugin artifact that upstream's frozen v1 producer contract actually builds. The exemption records the upstream digest it was judged against, so the sync stops when that file changes. v0.1.11 rewrote `orca-review/references/provider-contracts.md` around named providers and left no `Codex` mention in it, so that exemption was retired rather than rotated. The v0.1.13 rotation re-read every mention the override ships and left only the Mulgae-provider ones standing, because the Claude re-derivation replaced upstream's new Codex-only isolated-launcher grammar outright.

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

`/aquarium:upgrade` walks this sequence end to end — subagent-gathered delta analysis, approved re-derivations, validation, release, and the local installation refresh — behind explicit approvals at every mutating boundary.

## Validate

```bash
python3 scripts/sync.py --check
ruby tests/validate.rb
python3 -m unittest tests/test_claude_mcp_inspection.py
git diff --check
claude plugin validate --strict plugins/aquarium
```

`--check` regenerates into a temporary directory and fails if the committed output drifted. The Ruby validation covers only what this repository is responsible for — invocation gating against the upstream sidecars, host-neutral generated text, the commit hook's Claude Code contract, byte-identical Podway procedures, manifest agreement, deliberate exclusions, compiled generated scripts, and the marketplace shape. The forbidden-needle lists and the sigil exceptions are each compared as sets across `scripts/sync.py` and `tests/validate.rb`, because the guard is only as wide as its narrower half and an entry added to one side alone reports healthy. The Python test covers the one piece of behaviour this repository authors, the Claude Code MCP inspection. Upstream owns the prose contract and validates it in its own CI. The last command is Claude Code's own plugin validator and runs locally rather than in CI.

## Documentation style

Do not hard-wrap prose. Keep each prose paragraph on one source line; use line breaks only for structural Markdown, code, tables, lists, or other syntax where the break is meaningful.

## License

MIT, inherited from upstream. This repository vendors no third-party skill source: Deslop and Lora are installed from their own upstream repositories by `/aquarium:dev-setup`, each keeping its original licence.

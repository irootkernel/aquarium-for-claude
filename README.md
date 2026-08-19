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

Repositories that used the Podway integration must finish or explicitly dispose of any active session before migrating, then replace the managed `root-kernel-{task,goal,validation}-v2.yaml` procedures through a separately approved `/aquarium:dev-setup` run. The inspection schema is now `aquarium-dev-setup-inspection.v4`.

## Skills

| Skill | Purpose | Invocation |
|---|---|---|
| `epic-handler` | Orchestrate an epic through sequential task goals and a convergent epic-wide audit. | `/aquarium:epic-handler` with a roadmap path and one epic ID |
| `epic-validator` | Cold-validate a completed epic and converge confirmed gaps through remediation goals. | `/aquarium:epic-validator` with a roadmap path and one epic ID |
| `task-handler` | Strengthen the procedure around one task goal through focused phase skills and verified transitions. | `/aquarium:task-handler` with a roadmap path and one task ID |
| `task-commit` | Reconcile roadmap task lifecycle state and create one authorized commit that preserves unrelated work. | Automatic for commit requests, or `/aquarium:task-commit` |
| `release-qa` | Exercise the current release candidate through read-only user scenarios covering every change since the previous stable release. | `/aquarium:release-qa` with an intended or confirmed version |
| `dev-setup` | Diagnose and configure selected development tools, and propose reference-based instruction-file guidance behind separate approvals. | `/aquarium:dev-setup` |
| `independent-review` | Run a supervised read-only requirements and code review with fresh reviewer subagents, then adjudicate their findings. | `/aquarium:independent-review` with one epic or task |
| `deslop` | Remove task-introduced AI code slop without changing behavior or unrelated work. | Automatic when relevant, or `/aquarium:deslop` |

`task-handler` loads seven phase skills in order — `task-plan`, `task-implement`, `task-verify`, `task-refine`, `task-document`, `task-review`, `task-close`. Invoke one directly only to resume that exact phase with its required task context.

### Roadmap commit guard

The plugin ships a `PreToolUse` hook that inspects `Bash` commands and denies a direct `git commit` in a repository whose tracked roadmap carries task lifecycle state, routing it through `task-commit` instead. The hook is local, reads only the proposed command and the working directory, and fails open when it cannot parse its input. Because Claude Code merges an enabled plugin's hooks with your own, review it under `/hooks` after installing.

### Invocation gating

Every skill except `deslop` and `task-commit` carries `disable-model-invocation: true`, so Claude cannot start it on its own; you invoke it with `/aquarium:<skill>`. Several of these skills stage, commit, or mutate roadmap state, and the upstream workflow requires explicit invocation. The flag is derived from each upstream skill's `agents/openai.yaml` at sync time, so it can never disagree with the Codex policy.

This is also why the plugin is a separate artifact rather than a second manifest in the upstream repository: Codex's plugin validator rejects `disable-model-invocation` outright, while Claude Code needs it for the same guarantee.

## How generation works

```
upstream/                        git submodule, pinned to one upstream commit
  plugins/aquarium/              the Codex plugin — never edited here
overrides/
  manifest.json                  path → SHA-256 of the upstream file each override was derived from
  codex-exemptions.json          path → SHA-256 of an upstream file whose remaining "Codex" mentions were reviewed
  skills/...                     full-file replacements for host-specific divergence
scripts/sync.py                  the transformation
plugins/aquarium/                generated output, committed
  hooks/                         the roadmap commit guard
  sync-manifest.json             upstream commit and per-file hashes
```

`sync.py` copies the upstream plugin, applies literal substitutions, applies overrides, then derives invocation gating from the upstream sidecars and drops them. It refuses to run against an empty submodule, refuses to run when upstream grows a directory the transformation does not handle, and fails if host-specific text survives.

Four files diverge semantically and are kept as overrides rather than substitutions:

| Override | Why |
|---|---|
| `skills/independent-review/SKILL.md` | Replaces Orca orchestration with fresh read-only Opus subagents dispatched through the host's own mechanism. Because a subagent shares the coordinator's model, the skill claims a fresh context rather than an independent model, and buys coverage by giving several reviewers distinct lenses. |
| `skills/dev-setup/SKILL.md` | Resolves one instruction-file target — `AGENTS.md` or `CLAUDE.md`, asking when both exist — and defaults to `CLAUDE.md`. The two-stage approval gate is unchanged. |
| `skills/dev-setup/references/agents-guidance.md` | The whole file is instruction-file editing guidance, which is exactly what differs per host. |
| `skills/dev-setup/references/tool-catalog.md` | Registers Mulgae and Gaori MCP servers in `.mcp.json` and verifies them with `claude mcp get`, rather than `.codex/config.toml` and typed `codex mcp get --json` output. |

Everything else is a literal substitution: the `$aquarium:` sigil becomes `/aquarium:`, the `$use-*` skill sigils become `/use-*`, `request_user_input` becomes `AskUserQuestion`, Lora installs with `--agent claude-code`, the inspection script also searches `CLAUDE_CONFIG_DIR` and `~/.claude/skills`, and the hook command resolves `${CLAUDE_PLUGIN_ROOT}` instead of Codex's `${PLUGIN_ROOT}`.

That last one is load-bearing. `PLUGIN_ROOT` is unset under Claude Code, so the unsubstituted command expands to `/hooks/task_commit_gate.py`, `python3` exits 2, and `PreToolUse` reads exit 2 as a denial — blocking every `Bash` call. A forbidden needle and a required-text assertion both guard it.

The `Codex` name is otherwise forbidden in generated text. `tool-catalog.md` is exempt because it names the Codex CLI as a Mulgae provider and a required CLI version, which stays true here. The exemption records the upstream digest it was judged against, so the sync stops when that file changes.

## Upgrade

```bash
git submodule update --remote upstream
python3 scripts/sync.py
ruby tests/validate.rb
git add -A && git commit
```

Each override records the SHA-256 of the upstream file it came from. When upstream changes one of those files the sync stops and names it, because merging a stale override would ship guidance that no longer matches its source. Re-derive the override against the new upstream content and update `overrides/manifest.json`.

## Validate

```bash
python3 scripts/sync.py --check
ruby tests/validate.rb
git diff --check
```

`--check` regenerates into a temporary directory and fails if the committed output drifted. The Ruby validation covers only what this repository is responsible for — invocation gating against the upstream sidecars, host-neutral generated text, the commit hook's Claude Code contract, byte-identical Podway procedures, manifest agreement, and the marketplace shape. Upstream owns the prose contract and validates it in its own CI.

## Documentation style

Do not hard-wrap prose. Keep each prose paragraph on one source line; use line breaks only for structural Markdown, code, tables, lists, or other syntax where the break is meaningful.

## License

MIT, inherited from upstream. The bundled `deslop` skill is derived from Cursor Team Kit and retains its separate upstream MIT notice.

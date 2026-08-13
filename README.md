# Root Kernel Dev Claude Skills

Root Kernel development skills packaged as a Claude Code plugin marketplace. This repository is a **generated artifact**: the source of truth is the Codex plugin at [irootkernel/root-kernel-dev-skills](https://github.com/irootkernel/root-kernel-dev-skills), pinned here as a submodule and transformed by `scripts/sync.py`.

Website: [home.rootkernel.xyz](https://home.rootkernel.xyz) · Support: [cs@rootkernel.xyz](mailto:cs@rootkernel.xyz)

## Install

```bash
claude plugin marketplace add irootkernel/root-kernel-dev-claude-skills
claude plugin install root-kernel@root-kernel-dev-claude-skills
```

Inside a session, use `/plugin marketplace add irootkernel/root-kernel-dev-claude-skills` then `/plugin install root-kernel@root-kernel-dev-claude-skills`. Start a new session after installing or upgrading so the active session reloads the skill snapshot.

The generated plugin is committed, so installation never depends on the submodule being fetched.

## Skills

| Skill | Purpose | Invocation |
|---|---|---|
| `epic-handler` | Orchestrate an epic through sequential task goals and a convergent epic-wide audit. | `/root-kernel:epic-handler` with a roadmap path and one epic ID |
| `epic-validator` | Cold-validate a completed epic and converge confirmed gaps through remediation goals. | `/root-kernel:epic-validator` with a roadmap path and one epic ID |
| `task-handler` | Strengthen the procedure around one task goal through focused phase skills and verified transitions. | `/root-kernel:task-handler` with a roadmap path and one task ID |
| `dev-setup` | Diagnose and configure selected development tools, and propose reference-based instruction-file guidance behind separate approvals. | `/root-kernel:dev-setup` |
| `independent-review` | Run a supervised read-only requirements and code review with a fresh independent agent, then adjudicate its findings. | `/root-kernel:independent-review` with one EPIC or TASK ID |
| `deslop` | Remove task-introduced AI code slop without changing behavior or unrelated work. | Automatic when relevant, or `/root-kernel:deslop` |

`task-handler` loads seven phase skills in order — `task-plan`, `task-implement`, `task-verify`, `task-refine`, `task-document`, `task-review`, `task-close`. Invoke one directly only to resume that exact phase with its required task context.

### Invocation gating

Every skill except `deslop` carries `disable-model-invocation: true`, so Claude cannot start it on its own; you invoke it with `/root-kernel:<skill>`. Several of these skills stage, commit, or mutate roadmap state, and the upstream workflow requires explicit invocation. The flag is derived from each upstream skill's `agents/openai.yaml` at sync time, so it can never disagree with the Codex policy.

This is also why the plugin is a separate artifact rather than a second manifest in the upstream repository: Codex's plugin validator rejects `disable-model-invocation` outright, while Claude Code needs it for the same guarantee.

## How generation works

```
upstream/                        git submodule, pinned to one upstream commit
  plugins/root-kernel/           the Codex plugin — never edited here
overrides/
  manifest.json                  path → SHA-256 of the upstream file each override was derived from
  skills/...                     full-file replacements for host-specific divergence
scripts/sync.py                  the transformation
plugins/root-kernel/             generated output, committed
  sync-manifest.json             upstream commit and per-file hashes
```

`sync.py` copies the upstream plugin, applies literal substitutions, applies overrides, then derives invocation gating from the upstream sidecars and drops them. It refuses to run against an empty submodule, and fails if host-specific text survives.

Three files diverge semantically and are kept as overrides rather than substitutions:

| Override | Why |
|---|---|
| `skills/independent-review/SKILL.md` | Discovers available reviewer agents and asks which to use, instead of hardcoding `--agent codex`. Prefers an agent other than the host, since a reviewer sharing the coordinator's model shares its blind spots. |
| `skills/dev-setup/SKILL.md` | Resolves one instruction-file target — `AGENTS.md` or `CLAUDE.md`, asking when both exist — and defaults to `CLAUDE.md`. The two-stage approval gate is unchanged. |
| `skills/dev-setup/references/agents-guidance.md` | The whole file is instruction-file editing guidance, which is exactly what differs per host. |

Everything else is a literal substitution: the `$root-kernel:` sigil becomes `/root-kernel:`, `request_user_input` becomes `AskUserQuestion`, Lora installs with `--agent claude-code`, and the inspection script also searches `CLAUDE_CONFIG_DIR` and `~/.claude/skills`.

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

`--check` regenerates into a temporary directory and fails if the committed output drifted. The Ruby validation covers only what this repository is responsible for — invocation gating against the upstream sidecars, host-neutral generated text, manifest agreement, and the marketplace shape. Upstream owns the prose contract and validates it in its own CI.

## Documentation style

Do not hard-wrap prose. Keep each prose paragraph on one source line; use line breaks only for structural Markdown, code, tables, lists, or other syntax where the break is meaningful.

## License

MIT, inherited from upstream. The bundled `deslop` skill is derived from Cursor Team Kit and retains its separate upstream MIT notice.

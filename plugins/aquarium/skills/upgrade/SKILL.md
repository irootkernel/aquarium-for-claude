---
name: upgrade
description: "Upgrade this edition to a newly released upstream Aquarium version through orchestrated subagents: pin the submodule, resolve every sync abort, re-derive overrides and exemptions, validate, and publish the reviewed tag and GitHub Release. Use when the user explicitly invokes /aquarium:upgrade with one released upstream version; do not use for unreleased upstream commits or unrelated repository work."
argument-hint: "[version]"
disable-model-invocation: true
---

# Upgrade

Bring this generated edition from its pinned upstream Aquarium release to a newly released one through the repository's deterministic transformation, then publish and install it behind explicit user review. The upstream submodule at `upstream/` is read-only evidence: nothing beyond the tag checkout ever touches it, and every mutation stays in this repository.

## Authorization

Explicit invocation authorizes read-only inspection of this repository, the upstream submodule, and the configured Git remote. It does not authorize credential inspection, authentication changes, destructive state repairs, or publication mutations. Obtain separate approval at each mutating boundary — the pin, the first edit, each commit, the push, the tag, the release, and the local installation refresh — and put every material decision through AskUserQuestion.

## Orchestration Contract

The invoking conversation is the orchestrator: it plans, decides, reviews every subagent product, tracks goal achievement, and confirms every material decision with the user through AskUserQuestion; subagents gather evidence and apply approved edits, and nothing else.

- Mirror the phase plan into the Claude Code todo list through TodoWrite when the upgrade begins and keep it current as phases complete, so the active goal stays visible end to end.
- Gather evidence through read-only subagents dispatched through the host's own subagent mechanism in one message: an Opus subagent for the judgment-heavy upstream delta analysis — the absorbed changelogs, release notes, and per-file diffs ranked by adaptation impact — and Sonnet subagents for mechanical collection: override and exemption digest triage, substitution-rule survival against the new upstream text, and host-fact probes.
- Synthesize the gathered evidence into one adaptation plan yourself; subagents inform the plan and never own a decision.
- Apply the approved plan through subagents: Sonnet for mechanical re-derivations whose exact old and new text the orchestrator has already fixed — counted swaps and digest rotations — and Opus for semantically delicate override re-derivations; give each one the exact files, the derivation constraints, and its acceptance checks in the dispatch prompt.
- Review each subagent product against the plan before the next gate; when a product fails review, redo it or take it over rather than patching around it.
- Before proposing any commit, dispatch one fresh read-only Opus subagent to review the full generated diff against the adaptation plan, and settle its findings first.

## Establish the Request

1. Verify the working directory is this marketplace repository: `scripts/sync.py` exists, `.claude-plugin/marketplace.json` names `aquarium-for-claude`, and `upstream/` is the pinned submodule. Refuse to run anywhere else.
2. Take the intended upstream release in tag form (`vX.Y.Z`) from the argument, or discover the newest released upstream tag and confirm it with the user. Refuse an unreleased branch or commit: upstream `main` regularly carries an open development cycle.
3. Record the starting state before touching anything: the checked-out branch and its cleanliness — a dirty tree stops the run — the pinned upstream commit, the generated version in `plugins/aquarium/.claude-plugin/plugin.json`, and the intended version. Work happens directly on `main`.
4. Confirm the intended version is newer than the generated one. A downgrade or a re-pin of the already adopted version needs an explicit user decision before continuing.

## Pin Upstream

1. Run `git submodule update --init --recursive`, then `git -C upstream fetch --tags origin`, then `git -C upstream checkout vX.Y.Z`, then `git add upstream`, and record the resolved commit. The tag, never a branch, is the pin.
2. Read the absorbed range whole — the upstream changelog, the release notes, and the commit log since the previous pin — because one upgrade may absorb several upstream releases whose changes land at once.

## Gather Evidence Through Subagents

Dispatch the read-only fan-out from the Orchestration Contract and collect its products before planning: the ranked upstream delta dossier, the override and exemption digest triage, the substitution-rule survival table, and the host-fact notes. Nothing in this phase mutates the repository.

## Decide the Adaptation

Synthesize the gathered evidence into one adaptation plan: the resolution for each expected sync abort, each override and exemption re-derivation as a counted swap against the new upstream text following `references/rederivation.md`, and any host-specific improvement the delta makes possible. Present the plan and obtain the user's approval before the first edit.

## Resolve the Sync Loop

Run `python3 scripts/sync.py` repeatedly. Every abort names its own fix and stops generation rather than producing partial output; resolve one class at a time and re-run until generation succeeds. Read `references/rederivation.md` before resolving the first abort — it records the counted-swap method and this edition's known traps. Work the classes in this order, because earlier states gate later checks:

1. **Stale override** — an upstream file an override was derived from changed. Re-derive the override from the new upstream text, porting this edition's divergence onto it — never patch the previous override — and rotate its digest in `overrides/manifest.json`.
2. **Stale exemption** — the surviving third-party CLI mentions changed, appeared, or vanished. Re-read every remaining mention in the shipped file, confirm each still names the third party rather than this host, and rotate the digest in `overrides/codex-exemptions.json`.
3. **Dead substitution rule** — a rule matched nothing that ships. Delete it or re-derive it against the new upstream text; a rule whose only matches are override-shadowed counts as dead.
4. **Surviving host-specific text** — apply the cost ladder: a literal substitution when the divergence is textual, an override when it is semantic, a reviewed exemption only when the mention is a true third-party reference.
5. **New skill sigil family** — upstream prose invokes a skill through a dollar-prefixed sigil this edition has no rule for. Add the substitution rule naming its slash form, and add the matching forbidden needle to both lists — the Python table in `scripts/sync.py` and the Ruby list in `tests/validate.rb` — which the validator compares as sets.
6. **Moved required-text marker** — text a substitution or a script rule anchors on stopped matching. Move the marker to the surviving text and add arrival markers for new host-neutral scripts.
7. **Generated-script failure** — the compile or call-shape check rejects the transformed script. Re-derive the affected block rules so they swallow every downstream reader of the locals they delete, and extend the unit tests when new inspection behavior ships.
8. **Excluded-file reference** — generated text still names a file excluded by name. Extend the substitutions or revisit the exclusion decision.
9. **Unknown upstream directory** — upstream grew a plugin directory the copy allowlist does not carry. Decide explicitly whether to copy or exclude it, and record the decision in the README.

Apply the resolutions through subagents under the Orchestration Contract, and review each product before re-running the gate.

## Verify Host Facts When Semantics Move

When upstream changes behavior this edition adapts — the tool inspection surgery, the catalog's registration contracts, version floors — do not encode upstream's prose as this host's truth. Confirm the host fact read-only first: this host's CLI help output, its configuration files, and the installed package source. The v0.1.13 adoption kept one such claim out this way: `claude mcp get` connects to the probed server and so starts it, which makes upstream's statement that the probes never start a server false on this host, and it was not imported.

## Validate and Document

1. Extend `tests/validate.rb` for any new invariant first, then run all five commands: `python3 scripts/sync.py --check`, `ruby tests/validate.rb`, `python3 -m unittest tests/test_claude_mcp_inspection.py`, `git diff --check`, and `claude plugin validate --strict plugins/aquarium`.
2. Prove gating live: a `claude --plugin-dir plugins/aquarium -p` listing must show exactly the skills whose upstream sidecars allow implicit invocation, and no others. That set is upstream's to change — v0.1.14 opened `orca-review` alongside `task-commit` — so read it from the sidecars rather than from a remembered count.
3. Update `README.md` and `README.ko.md` together — the Skills table, the generation prose for any new rule or marker, and the overrides table when a divergence changed — and record shipped outcomes under the open `Unreleased` section of `CHANGELOG.md`.

## Commit Behind Review

Create separate bisectable commits in this repository's style: one `[INT]` adoption commit carrying the pin, the regenerated tree, and the re-derivations together, then focused commits for host-specific improvements, each with the Lore trailers this repository requires on non-trivial commits. Then stop: no push, tag, release, or installation without the user's explicit approval.

## Release After Approval

1. Push `main`.
2. Create the annotated tag `vX.Y.Z` titled `Aquarium for Claude vX.Y.Z` with the body `Generated from upstream irootkernel/aquarium vX.Y.Z (<full-commit>).`, and push it.
3. Publish the GitHub release with `gh release create` in the established format: an intro line naming the upstream release and commit, then the What's new, Upstream changes, Claude Code improvements, Validation, and Install sections.
4. Set the release date on the matching `CHANGELOG.md` heading, open the next `Unreleased` section above it, and commit that documentation state.
5. Verify that remote `main`, the peeled tag, and the GitHub release all resolve to the same commit.

## Refresh the Local Installation

When the user asks, refresh this machine's installation: run `claude plugin marketplace update aquarium-for-claude`, then `claude plugin update aquarium@aquarium-for-claude`, and tell the user a new session is required before the updated skill snapshot loads.

## Report

Return the adopted upstream tag and commit, the edition version, each commit hash, the tag hash, the push result, the release URL, the validation outcomes, and any remaining manual steps or warnings.

## Boundaries

- Never edit `plugins/aquarium/` by hand; every change flows through `scripts/sync.py`, `overrides/`, or `additions/`, and the regenerated tree commits together with its source change.
- Never push to, tag, or mutate the upstream repository; the submodule is read-only evidence.
- Never pin upstream `main` or an unreleased commit; released tags only.
- Never push, tag, publish, or install before the user explicitly approves the reviewed state.
- Never bypass a sync abort; each one marks a decision this edition must make deliberately.

# AGENTS.md

Aquarium for Claude is a generated Claude Code plugin marketplace, and this file is its local agent guidance.

## Core Behavior

### 1. Inspect Before Acting

- Resolve repository facts and named authorities before implementation.
- State material assumptions, surface trade-offs, and ask when unresolved ambiguity would materially change the result.
- Push back when a request conflicts with repository authority, safety, or the user's stated goal.

### 2. Prefer the Smallest Complete Solution

- Implement only the verified requirement and reuse established patterns.
- Avoid speculative features, abstractions, configurability, and compatibility layers.
- Simplify an implementation whose size or complexity is not justified by its behavior.

### 3. Make Surgical Changes

- Touch only what the requested outcome and its verification require.
- Preserve unrelated work and match local style.
- Remove only artifacts made obsolete by the current change.

### 4. Work Toward Verifiable Goals

- Define success checks before implementation.
- Match verification strength to the claimed behavior and relevant failure paths.
- Continue until the result is verified or a concrete blocker is established; report skipped checks and remaining uncertainty.

## Master Preferences

- Respond to Master in Korean using polite speech. When directly addressing the user, use exactly `Master`.
- Keep repository artifacts in the repository's established language and style. When no convention exists, use English unless Master requests otherwise.
- Report concise conclusions and useful evidence without exposing private chain-of-thought.

## Aquarium Development Guide

- Use `/lore-commits` for non-trivial commit messages and `/lore-query` to inspect recorded decision context.
- This repository is the generator of the Aquarium plugin, not a roadmap project: do not drive changes to it through the Aquarium workflow skills.
- Repository-specific rules in `Project Configuration` override these defaults.

## Project Configuration

### Repository Index and Authorities

- Purpose: a Claude Code plugin marketplace generated from the Codex plugin pinned as the `upstream/` submodule; the generated tree under `plugins/aquarium/` is committed so installation never depends on the submodule.
- `scripts/sync.py` is the transformation and the authority on every difference between upstream and the artifact: substitution rules, excluded files, added files, required text, and forbidden text.
- `overrides/manifest.json` and `overrides/codex-exemptions.json` pin the upstream digests each override and exemption was judged against; `overrides/skills/**` hold the full-file replacements and `additions/agents/**` the host-only files.
- `tests/validate.rb` asserts the artifact's invariants, `tests/test_claude_mcp_inspection.py` covers the Claude Code MCP inspection the sync injects, and `.github/workflows/validate.yml` runs both after `python3 scripts/sync.py --check`.
- `README.md` is the public explanation of the generation model and must stay aligned with `scripts/sync.py`.
- Canonical commands: `python3 scripts/sync.py`, `python3 scripts/sync.py --check`, `ruby tests/validate.rb`, `python3 -m unittest tests/test_claude_mcp_inspection.py`, `git diff --check`, and `claude plugin validate --strict plugins/aquarium`.

### Commit Messages

- Start every commit title with exactly one uppercase header and one imperative summary. This repository's own history uses `[INT]` for upstream adoption and other cross-cutting contract changes, `[FIX]` for defect corrections, `[FEAT]` for new user-facing capabilities, `[DEV]` for development-tool and internal integration changes, and `[BRAND]` for the marketplace rename; upstream's `AGENTS.md` defines the wider set `[FEAT]`, `[FIX]`, `[DEV]`, `[TEST]`, `[DOC]`, `[CI]`, `[REL]`, and `[INT]`, which applies here for concerns this history has not yet needed.
- Write Lore trailers — `Constraint:`, `Rejected:`, `Directive:`, `Tested:`, `Not-tested:`, `Confidence:`, `Scope-risk:`, `Reversibility:` — on every non-trivial commit.

### Project-Specific Operating Rules

- Never edit `plugins/aquarium/` by hand. Change `scripts/sync.py`, `overrides/`, or `additions/`, run `python3 scripts/sync.py`, and commit the regenerated tree together with its source change.
- Re-derive an override from the new upstream text with counted swaps rather than patching the old override, then rotate its digest in `overrides/manifest.json`; re-read every remaining `Codex` mention before rotating an exemption digest.
- A substitution rule must rewrite text that ships; text that occurs only inside an override target belongs in the override, and generation rejects a rule that matched nothing.
- Keep every prose paragraph in Markdown on one source line; line breaks are for structural Markdown only, and `tests/validate.rb` enforces it across the repository.
- Upgrade with `git submodule update --init --recursive`, `git -C upstream fetch --tags origin`, `git -C upstream checkout <tag>`, then `git add upstream` so the gitlink matches the sync manifest.
- Do not push or create tags without explicit direction.

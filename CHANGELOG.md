# Changelog

This file records concise shipped outcomes of the Aquarium for Claude edition. Releases before v0.1.14 are recorded in this repository's Git tags and GitHub releases; upstream outcomes live in the [Aquarium changelog](https://github.com/irootkernel/aquarium/blob/main/CHANGELOG.md).

## v0.1.14 - Unreleased

### Added

- Add the edition-owned `/aquarium:upgrade` skill: one full upstream release adoption run as an orchestrated lifecycle — Opus and Sonnet subagents gather the delta and apply approved re-derivations while the invoking conversation decides, reviews, and validates — ending in the reviewed tag, GitHub Release, and local installation refresh behind explicit approvals, with `references/rederivation.md` recording the counted-swap method and the known adoption traps.
- Teach the generation and validation to carry edition-owned skills: `additions/skills/**` ships through the `ADDED_PATHS` allowlist, generation refuses a skill addition that does not declare its own model-invocation gating, and the validator asserts the generated skill set is upstream plus the recorded additions.
- Own the repository-state inspector `independent-review` runs for its no-mutation baseline. Upstream shipped it beside `orca-review` and removed it in v0.1.14; it is now an edition addition under the skill that calls it, which also retires the cross-skill path nothing in the sync watched.
- Name the shell variables the sigil scan cannot tell apart from skill invocations. `task-commit` pins the commit identity through `git -c user.name="$aquarium_commit_name"`, so generation carries an explicit exception list, requires each entry to still occur upstream, and compares it with the validator's copy as a set rather than narrowing the pattern and admitting every future `$snake_case` skill.

### Changed

- Adopt upstream Aquarium v0.1.14: the `aquarium-dev` development channel, official Dolgorae v0.1.1 support, exact-upstream Humanizer and im-not-ai installation, the shared finding-disposition contract, dossier-scoped epic execution, Podway v0.2.8, and repository-local commit identities.
- Keep independent review on host subagents where upstream moved it onto a Dolgorae immutable capture running a fresh Codex Reviewer. `references/review-contract.md` becomes the fifth override so the scope table, backend ownership, settlement, and result envelope describe the backend this artifact actually has; the two capture-only scopes are unsupported for the same reason they are unsupported for Orca Review, and the excluded Dolgorae consumer contract documents a lifecycle this edition does not run. Two shipped references that still described the upstream backend are corrected in place: `orca-review` no longer refers a caller to independent review for scopes neither backend supports here, and the shared disposition contract no longer groups independent review with the backends that capture.
- Install and diagnose Humanizer and im-not-ai on this host rather than another. im-not-ai's own installer has a first-class Claude mode that materializes a different payload — three skills and four subagents rather than one skill — so `dev-setup` discloses that command and compares that tree, and the generated inspector expects both skills in the Claude Code skill root instead of the shared cross-agent root and the Codex home, where every correct installation would have reported degraded forever.
- Follow upstream in opening `orca-review` to implicit invocation: naming both a review target and a reviewer is now itself the request, as it already was for a commit request and `task-commit`.

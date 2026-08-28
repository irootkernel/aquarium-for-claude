# Changelog

This file records concise shipped outcomes of the Aquarium for Claude edition. Releases before v0.1.14 are recorded in this repository's Git tags and GitHub releases; upstream outcomes live in the [Aquarium changelog](https://github.com/irootkernel/aquarium/blob/main/CHANGELOG.md).

## v0.1.14 - Unreleased

### Added

- Add the edition-owned `/aquarium:upgrade` skill: one full upstream release adoption run as an orchestrated lifecycle — Opus and Sonnet subagents gather the delta and apply approved re-derivations while the invoking conversation decides, reviews, and validates — ending in the reviewed tag, GitHub Release, and local installation refresh behind explicit approvals, with `references/rederivation.md` recording the counted-swap method and the known adoption traps.
- Teach the generation and validation to carry edition-owned skills: `additions/skills/**` ships through the `ADDED_PATHS` allowlist, generation refuses a skill addition that does not declare its own model-invocation gating, and the validator asserts the generated skill set is upstream plus the recorded additions.

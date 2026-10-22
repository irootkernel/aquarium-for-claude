---
name: task-plan
description: "Plan one named roadmap task without mutation. Use when /aquarium:task-handler delegates its planning phase or when the user explicitly invokes /aquarium:task-plan to resume that phase with a repository, roadmap path, and exactly one task ID."
argument-hint: "<roadmap-path> <task-id>"
disable-model-invocation: true
---

# Task Plan

> **Claude Code delegation:** when this skill, or a reference or Procedure node it follows, hands a step to another Aquarium skill — however it phrases the hand-off, and whether it writes `/aquarium:<name>` or names the skill bare — read that skill's `SKILL.md` in full from this plugin (`../<name>/SKILL.md` from this skill's directory) and follow it as the delegated step instead of calling the Skill tool. Claude Code reserves most Aquarium skills for the user to type: it refuses the Skill tool for them and, once it has refused, forbids carrying out their workflow any other way. When you hand such a step to a subagent, put that file's absolute path in its assignment and have it read the file, because a subagent cannot load a gated skill through the Skill tool. Running another skill's bundled script is not a hand-off. A continuation request, routed repair, offer, or recommendation that the text has you return or report to the user is not a delegation: name its slash command, do not run it yourself, and stop where the text stops.

Under an ordinary `task-handler`, follow [Task orchestration](../../references/task-orchestration.md). Return the node-specific `aquarium.executor-handoff/v3` with exact target, original requirements, actual results, available public handles, performed and omitted checks, authority and gaps. The Coordinator owns Podway records and Decisions; the independent Evaluator assesses coherent delivery phases. Admitted formal snapshots retain their original v1 contract. Direct invocation keeps this phase's existing authority.

Read [commit-attribution.md](../../references/commit-attribution.md) for message formatting and change origins, within this skill's existing effect boundaries.

Plan only one task. Require the repository, canonical roadmap path, and exact task ID established by `/aquarium:task-handler`; when invoked directly, reconstruct and validate those inputs before proceeding.

Read [epic-execution-sot.md](../../references/epic-execution-sot.md).

## Explore Without Mutation

Read applicable repository instructions, the task entry, its parent epic, the handler-resolved execution SOT and any active dossier, `docs/README.md`, every relevant canonical role owner, current architecture, Git state, existing tests, CI and task runners, documentation synchronization rules, and configured development-tool guidance. Resolve those authorities from the canonical roadmap; do not require the user to name document paths.

Follow [directory agent guidance](../../references/directory-agent-guidance.md)
from the affected implementation paths: read applicable root, ancestor and
directory guides, the adoption declaration in the documentation index, and the
relevant original canonical sources. Include affected document and guide
maintenance in the plan, including new feature boundaries within declared
coverage and existing guide or reference moves. Report uncovered areas without
backfill; guide absence alone does not block legacy delivery.

When invoked directly, perform the shared semantic discovery and return the resolved dossier or composite execution SOT to the owning handler. Do not create a dossier or route to `docs-setup`. When no dossier is declared, its absence is not a semantic gap; disclose the composite execution SOT in the plan without requiring a dossier waiver. Treat a declared dossier whose link cannot be resolved as a semantic gap, and report the exact missing or ambiguous semantic owner when the canonical sources are incomplete.

Do not create a goal, edit files, generate code, run rewriting formatters, stage changes, invoke providers, or alter external state.

Adaptive fit planning may read approved source locations under the
[shared preparation contract](../../references/adaptive-procedures.md#selection-and-source-only-preparation).
Preserve complete original requirement sources and unresolved semantic coverage.
Use only its `plan-only` mode here; source rendering and native authoring belong
to the owning handler's approved preparation interval. The handler owns adaptive selection and approval; this phase retains its read-only mutation boundary.

## Produce and Approve the Plan

Produce a decision-complete plan containing:

- the execution SOT source paths and requirement owners, with the active dossier or its explicit absence;
- goal, requirements, non-goals, lifecycle meaning, and task boundaries;
- current architecture observations and affected behavior;
- implementation approach and meaningful tradeoffs;
- requirement-to-verification matrix;
- specifications, architecture, decision, implementation-tip, operations, public-documentation, rollout, and review impact;
- exact repository-native verification commands;
- review finding remediation, affected checks, exact restaging of already staged affected paths, and any provider re-review budget;
- known permission, tool, provider, and environment gaps.

When delegated, return the proposed plan to the Coordinator for its one explicit approval conversation; do not ask separately. On direct invocation, ask once for explicit approval of the plan. If approval is refused or withheld, stop, report the exact missing decision, and do not enter implementation. A material change to the approved source set or requirements requires an updated plan and renewed approval.

If the host is in Plan mode, remain there and end with a continuation prompt that explicitly invokes `/aquarium:task-handler` with the same repository, roadmap path, task ID, and handler-selected mode. `plan-only` ends without mutation, while `plan-handoff` prepares the approved handoff rather than implementing it. Return the plan, approval state, inspected authority paths, and unresolved gaps to the coordinator.

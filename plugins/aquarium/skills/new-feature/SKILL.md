---
name: new-feature
description: "Shape one feature epic for an existing project with Ouroboros, without implementing it. Use on an explicit /aquarium:new-feature request or an eligible pre-execution /aquarium:epic-handler design route."
disable-model-invocation: true
---

# New Feature

> **Claude Code delegation:** when this skill, or a reference or Procedure node it follows, hands a step to another Aquarium skill — however it phrases the hand-off, and whether it writes `/aquarium:<name>` or names the skill bare — read that skill's `SKILL.md` in full from this plugin (`../<name>/SKILL.md` from this skill's directory) and follow it as the delegated step instead of calling the Skill tool. Claude Code reserves most Aquarium skills for the user to type: it refuses the Skill tool for them and, once it has refused, forbids carrying out their workflow any other way. When you hand such a step to a subagent, put that file's absolute path in its assignment and have it read the file, because a subagent cannot load a gated skill through the Skill tool. Running another skill's bundled script is not a hand-off. A continuation request, routed repair, offer, or recommendation that the text has you return or report to the user is not a delegation: name its slash command, do not run it yourself, and stop where the text stops.

Read [commit-attribution.md](../../references/commit-attribution.md) for message formatting and change origins, within this skill's existing effect boundaries.

Create or revise exactly one feature epic in an existing project's canonical roadmap. Do not implement or publish. Staging and committing approved documents require the separate delivery-input boundary in the shared integration contract.

On a pre-execution route from `/aquarium:epic-handler`, continue in the same conversation for the exact repository, roadmap, and existing epic ID. Preserve the existing epic ID. Keep the task membership unless the user explicitly approves a task-structure change in this design workflow. Create or revise one dossier only when the shared threshold requires it; update its TODO index entry and roadmap link as needed. Resolve any identified semantic gap in its canonical owner. A material change to the epic's goal or scope needs an explicit user decision in this design workflow. Use the selected Design Procedure, independent execution envelope, provider and exact-diff approvals, and delivery-input commit boundary. After successful design delivery, report the applied paths, committed revision when required, remaining worktree state, and an exact new-conversation request naming the repository root, canonical roadmap, epic ID, and `/aquarium:epic-handler`. If a required commit remains unauthorized or a blocker remains, report that boundary as the next action instead of claiming execution is ready.

Always read [evidence-residency.md](../../references/evidence-residency.md), then read [ouroboros-integration.md](../../references/ouroboros-integration.md), [documentation-governance.md](../../references/documentation-governance.md), and [epic-execution-sot.md](../../references/epic-execution-sot.md), and follow [adaptive Design execution](../../references/adaptive-execution.md#design-entrypoints).

Resolve the target roadmap's recorded identity contract before allocating an epic or task ID. Establish repository authority, current architecture and behavior, epic identity, user outcome, non-goals, dependencies, migration needs, failure behavior, rollout boundary, and acceptance evidence.

After the approved envelope, use installed upstream `/ouroboros:interview`, `/ouroboros:pm`, or `/ouroboros:seed` only as needed. Before `/ouroboros:pm`, apply the shared [PM file and clipboard boundary](../../references/ouroboros-integration.md#pm-files-and-clipboard): disclose draft writes and obtain authority to replace the clipboard. Produce one coherent epic with ordered work units and explicit ownership. Apply the shared execution-SOT threshold; create or revise one scope-local dossier only when required, otherwise keep the complete execution contract in the roadmap and at most two requirement-bearing canonical documents.

Run upstream `/ouroboros:qa`, adjudicate the draft, show the exact roadmap and documentation diff, and apply it only after explicit approval and snapshot recheck. End with the epic identity, applied paths, validation, and implementation blockers.

Apply the shared QA outcome mapping and [delivery-input commit boundary](../../references/ouroboros-integration.md#commit-approved-delivery-input). Report whether documents are applied or committed before naming the next explicit workflow.

## Ordinary native orchestration

Follow [Design and diagnosis orchestration](../../references/design-diagnosis-orchestration.md) for ordinary v3 native assignments, grouped independent assessments, original evidence and recovery. Preserve this skill's original leaf, exact approval and effect boundaries. No native history, role snapshot or configuration qualification is required. Existing formal snapshots retain their original contracts; source updates do not authorize managed-file rollout.

## Adaptive Design execution

Before Podway discovery or source preparation, branch on explicit Podway opt-out and, for `new-project`, non-Git scope. Continue the original ordinary Executor/Evaluator and document approval workflow with Podway inapplicable; do not initialize Git or Podway. On the native path, follow [adaptive Design execution](../../references/adaptive-execution.md#design-entrypoints) for actual fit, exact admission and same-session recovery. Prefer adequate unchanged Design sources and preserve their first due grouped assessment. Keep this entrypoint's artifacts, upstream leaves, selected reviews and effect authority.

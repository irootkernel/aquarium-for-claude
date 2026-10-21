---
name: refactor
description: "Shape one major refactor or behavior-change epic with Ouroboros, without implementing it. Use when the user explicitly invokes /aquarium:refactor."
disable-model-invocation: true
---

# Refactor

> **Claude Code delegation:** when this skill, or a reference or Procedure node it follows, hands a step to another Aquarium skill — however it phrases the hand-off, and whether it writes `/aquarium:<name>` or names the skill bare — read that skill's `SKILL.md` in full from this plugin (`../<name>/SKILL.md` from this skill's directory) and follow it as the delegated step instead of calling the Skill tool. Claude Code reserves most Aquarium skills for the user to type: it refuses the Skill tool for them and, once it has refused, forbids carrying out their workflow any other way. When you hand such a step to a subagent, put that file's absolute path in its assignment and have it read the file, because a subagent cannot load a gated skill through the Skill tool. Running another skill's bundled script is not a hand-off. A continuation request, routed repair, offer, or recommendation that the text has you return or report to the user is not a delegation: name its slash command, do not run it yourself, and stop where the text stops.

Create or revise exactly one refactor epic in the canonical roadmap. Do not implement, stage, commit, or publish.

Always read [evidence-residency.md](../../references/evidence-residency.md), then read [ouroboros-integration.md](../../references/ouroboros-integration.md), [documentation-governance.md](../../references/documentation-governance.md), and [epic-execution-sot.md](../../references/epic-execution-sot.md), and use the default `aquarium-design-v2` Podway path.

Resolve the target roadmap's recorded identity contract before allocating an epic or task ID. Trace current contracts, consumers, data and runtime seams, compatibility guarantees, migration ordering, rollback, observability, failure containment, and proof of behavior preservation or intentional change.

After the approved envelope, use installed upstream `/ouroboros:interview` and `/ouroboros:seed` as needed. Produce one ordered epic with explicit compatibility, migration, rollback, and verification ownership. Apply the shared execution-SOT threshold; create or revise one scope-local dossier only when required, otherwise keep the complete execution contract in the roadmap and at most two requirement-bearing canonical documents.

Run upstream `/ouroboros:qa`, adjudicate the draft, show the exact diff, and apply only after explicit approval and snapshot recheck. End with the epic identity, affected contracts, validation, and unresolved migration risks.

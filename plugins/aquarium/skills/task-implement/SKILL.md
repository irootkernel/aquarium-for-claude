---
name: task-implement
description: "Implement the approved plan for one named roadmap task. Use when /aquarium:task-handler delegates implementation or when the user explicitly invokes /aquarium:task-implement to resume that phase with an approved plan and exact task identity."
argument-hint: "<roadmap-path> <task-id>"
disable-model-invocation: true
---

# Task Implement

> **Claude Code delegation:** when this skill, or a reference or Procedure node it follows, hands a step to another Aquarium skill — however it phrases the hand-off, and whether it writes `/aquarium:<name>` or names the skill bare — read that skill's `SKILL.md` in full from this plugin (`../<name>/SKILL.md` from this skill's directory) and follow it as the delegated step instead of calling the Skill tool. Claude Code reserves most Aquarium skills for the user to type: it refuses the Skill tool for them and, once it has refused, forbids carrying out their workflow any other way. When you hand such a step to a subagent, put that file's absolute path in its assignment and have it read the file, because a subagent cannot load a gated skill through the Skill tool. Running another skill's bundled script is not a hand-off. A continuation request, routed repair, offer, or recommendation that the text has you return or report to the user is not a delegation: name its slash command, do not run it yourself, and stop where the text stops.

Implement only the approved plan for the task established by `/aquarium:task-handler`. Consume the selected `record-plan.plan-summary` and current `prepare-implementation.implementation-entry-summary`; neither is inherited from graph order alone. When invoked directly, require the repository, roadmap path, task ID, and explicit plan approval; stop if the plan or current task-owned boundary cannot be reconstructed safely.

## Re-establish the Baseline

Before editing, re-read applicable instructions, the task entry, approved plan, current Git state, and affected architecture. Report material drift that invalidates the plan instead of silently redesigning it.

## Implement the Approved Scope

Implement the smallest maintainable change that satisfies the approved requirements:

- follow local architecture, naming, error, data, and dependency patterns;
- avoid speculative configuration, extensibility, compatibility layers, and unrelated cleanup;
- remove imports, variables, helpers, and branches made unused by the task;
- preserve all pre-existing staged, unstaged, and untracked work;
- add a focused reproducer before a bug fix when practical;
- verify each meaningful increment with the narrowest authoritative check.

Continue diagnosing task-caused failures until the focused implementation is sound or a real authority or environment blocker appears. Do not stage, update lifecycle documentation, invoke Mulgae, commit, or publish in this phase.

Return the implemented requirements, task-owned paths, focused commands and exit codes, remaining verification work, and blockers to the orchestrator.

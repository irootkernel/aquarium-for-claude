---
name: independent-review
description: "Run one supervised static review with fresh read-only reviewer subagents against staged changes, a commit or range, one task or epic, or a roadmap-independent investigation. Use when the user explicitly invokes /aquarium:independent-review and asks for an independent verdict without remediation."
argument-hint: "<target> [task-or-epic-id]"
disable-model-invocation: true
---

# Independent Review

Run the canonical Aquarium review contract with one or more fresh reviewer subagents. The execution backend is this host's own subagent mechanism, but target selection and review semantics are backend-independent. Use `/aquarium:orca-review` only when the user wants the review to run in a separate provider process.

## Load the Contracts

1. Read [review-contract.md](../../references/review-contract.md) completely. It owns target selection, dirty-state handling, consent, static-review limits, and the result envelope.
2. Read that contract's reviewer as a fresh subagent of this session. Nothing leaves this host, so its transmission wording authorizes dispatch over the named scope rather than disclosure to a separate process; its same-user visibility disclosure is unconditional here, because a subagent reads the same filesystem under the same account; and its backend lifecycle status is each reviewer's dispatch status. Targets, the dirty decision, static limits, finding fields, and the result envelope apply unchanged. This skill starts no Orca worker, so the Orca supervision contract does not apply to it.
3. Resolve this skill directory and use `scripts/inspect_review_target.py` from it. Do not copy or approximate the inspector contract.

## Establish the Request

1. Resolve one current Git root and classify the request as `staged`, `commit`, `range`, `task`, `epic`, or `special request`.
2. For a task or epic, inspect its roadmap and linked authority first. Select a Git target automatically only when the authority identifies one unambiguous staged candidate, commit, or range; otherwise ask the user to choose among the concrete candidates.
3. For a special request, establish the exact question, then always ask the user to confirm staged, `HEAD`, one commit, or one explicit two-dot or three-dot range.
4. Inspect HEAD, branch, upstream, staged, unstaged, untracked, ignored, and conflicted state. Resolve any staged-target dirty decision exactly as the shared contract requires. Never review dirty working-tree content as a target.
5. Run the target inspector after all required choices or staging operations. Bind its complete JSON result and the resolved authority paths to every reviewer specification.

Explicit invocation with an exact target authorizes dispatching one or more fresh read-only reviewer subagents over that scope. Do not ask for duplicate approval unless the target, included paths, reviewer set, or execution scope changes. The workflow authorizes no source edits, tests, builds, generators, formatters, linters, provider reviews, commits, pushes, publication, or remediation. The only permitted mutation is exact-path staging that the user separately approved under the dirty decision.

## Dispatch Fresh Reviewer Subagents

Dispatch at least one reviewer subagent through the host's own subagent mechanism, and dispatch several when the target spans distinct review dimensions. Prefer this plugin's own `aquarium:independent-reviewer` subagent type, which has no editing tools and runs on Opus; when the host's catalog does not offer it, use any subagent type without editing tools and state the read-only constraint in the specification, because for a general-purpose type the specification is the only constraint there is. Stop with the exact gap when no subagent mechanism is available, when a dispatch fails, or when a reviewer returns no usable output, and never substitute the coordinator's own review, a chat delegation, an ad hoc terminal, or a raw agent CLI: the coordinator has already reasoned about this target and cannot review it independently.

Several reviewers are still one review of one target. Give each a distinct lens — requirements conformance, implementation correctness, test and coverage adequacy, or a broad trace over callers, tests, and documentation — so that additional reviewers buy coverage rather than repetition, and never let a lens widen, narrow, or change the target. Keep the requirements and correctness lenses on Opus and request Sonnet for a broad tracing lens, so depth and breadth come from different models. Launch every reviewer in a single message so they run concurrently, and record which lens and which requested model each one received. A reviewer subagent runs under the same provider as the coordinator: a different requested model buys a different model, not an independent provider, and the durable guarantee is a fresh context that has not seen the coordinator's reasoning.

Each reviewer specification must include:

- the absolute repository root, target-inspector result, review focus, assigned lens, and authority paths;
- exact included and excluded state, including the same-user visibility disclosure when dirty content is excluded;
- instructions to use index blobs for staged targets and resolved commit blobs for commit, range, or `HEAD` targets rather than later working-tree copies;
- the static-only restrictions and `runtime unverified` requirement from the shared contract;
- the required finding fields and exact `APPROVE` condition;
- the user's test-status statement only as context, never as independently verified evidence.

Do not seed any reviewer with suspected findings or intended fixes. Require each one to modify no files, leave its complete review in its final response, and report the lens it applied and the target it examined.

## Supervise and Adjudicate

Before dispatch, disclose and record one cumulative 30-minute liveness budget of wall-clock time unless the user explicitly selected another duration. Wait for each reviewer to report rather than predicting its result, give the user a progress update while waiting, and answer reviewer questions only from established repository facts; ask the user when an answer requires product intent or wider authority. When the budget elapses first, stop waiting, leave any running reviewer alone, and report the review as operationally incomplete with each reviewer's dispatch status; further waiting requires an explicit user request, and never re-dispatch, cancel, or replace a running reviewer automatically. Keep technical review status separate from dispatch status, so a reviewer that never reported is never read as a clean verdict.

After every dispatched reviewer has reported or the budget has expired, independently check every finding against the exact target, authority, production callers, persistence and concurrency boundaries, and existing tests without running checks or changing files. Classify findings as Valid, Invalid, or Needs confirmation under the shared result contract. A functionality claim that still requires execution remains `runtime unverified`. Merge overlapping findings once before classifying and keep disagreements visible: a finding one reviewer raised and another contradicted is a needs-confirmation item with both positions stated, never an averaged verdict.

Return the complete shared result envelope, reading its single reviewer identity, verdict, and backend lifecycle status as one row per dispatched reviewer — subagent type, assigned lens, requested model, its own verdict, and its dispatch status — over one adjudicated result for the whole review, and identify this host's subagent mechanism as the backend. Return `APPROVE` only when every dispatched reviewer reported, each examined the intended target and authority, and no actionable finding remains. Wrong scope, modified files, missing output, or a failed or unreported dispatch prevents a clean verdict.

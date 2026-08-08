# AI delegation and review

Status: Operational under Accepted DR-0001 Revision 5

Use this workflow whenever the main thread considers delegating work or
requesting model-backed independent review under the accepted DR-0001 Revision 5
governance process. It preserves safety and ownership boundaries, while product,
specification, and architecture proposals remain provisional.

## Ownership boundary

The main `gpt-5.6-sol` thread owns:

- discussion with the human project owner;
- planning and task decomposition;
- product and architecture synthesis;
- assignment and integration of delegated work;
- consolidated validation;
- Git, branch, commit, and pull-request operations;
- CI and review orchestration;
- external side effects;
- the final repository recommendation.

A subagent may collect evidence, implement a bounded decision already supported
by canonical design, or challenge a proposal. It must not make product or
architecture decisions. An independent reviewer recommends; the human decision
owner decides.

## Round and batch pipeline

The main thread groups roughly two to five related decisions or talking points
into one discussion batch and finishes the discussion with Ben. Luna applies
non-trivial document edits, evidence gathering, and bounded mechanical work;
the main thread inspects and integrates the batch and commits it. At the end of
every substantive design-cycle handoff, the main thread explicitly states
`Recommended adversarial level: None|Single|Double — <one-line reason>` as
advice to Ben and a durable planning signal, not automatic acceptance. `None`
is for purely mechanical/reversible work or discussion with no created or
materially revised consequential DR and no novel evidence-bearing claim; it
cannot satisfy the review prerequisite for a created or materially revised
consequential DR, which still needs review or Ben's explicit recorded waiver.
`Single` is the normal default for a consequential DR or meaningful bounded
design batch and means one fresh independent pass. `Double` is exceptional for
direction-setting, cross-cutting, hard-to-reverse or locking, technically
complex, strongly evidence-dependent, disputed, or difficult-to-audit work; it
means two genuinely independent fresh passes with distinct named lenses,
normally Sol medium for foundational work. Do not send duplicate prompts and
call them diversity. More than Double or Sol above medium requires Ben's
explicit approval. Ben may raise or lower the recommendation or waive as
already governed. A material proposal revision makes older reviews stale; when
Double remains justified by the decision's impact, the revised current version
normally receives Double again unless Ben changes or waives it. Double is one
pass per reviewer on the current revision, not review-until-clean. The main
thread consolidates duplicate and contradictory findings and presents only
actionable findings. Independent research for the next batch may proceed when
dependencies permit. Decision-bearing findings are not auto-fixed and the
process does not run a review-until-clean loop; mechanical defects faithful to
settled intent may be corrected, while a new scope, trade-off, or authority
choice returns to Ben. Unaccepted material remains clearly labelled Proposed or
provisional.

## Model routing

- Delegate to `gpt-5.6-luna` at `high` for routine bounded investigation,
  mechanical patches, straightforward test updates, and multi-step search or
  tool-driven work. Prefer Luna when it preserves Sol context or lowers cost,
  even if the bounded task is straightforward.
- Use Luna at `xhigh` for substantial delegated work and independent review. This
  is the normal Luna ceiling.
- Luna at `max` is an exceptional tier governed by the admission gate below. It
  is not the automatic next step after `xhigh`.
- Escalate to `gpt-5.6-sol` at `medium` when broad synthesis, ambiguous evidence,
  or general reasoning matters more than coding-agent throughput. This is a
  task-type escalation, not the automatic next tier after Luna.
- For a Single foundational adversarial review, use a fresh `gpt-5.6-sol`
  reviewer at `medium` by default. For a Double review, use two genuinely
  independent fresh passes with distinct named lenses, normally Sol at medium
  for foundational work. Use Luna at xhigh for narrow convergence,
  implementation, or bounded technical review when that better fits the corpus.
- Sol at `high` is the absolute subagent ceiling and requires explicit human
  approval. Do not use Terra as a normal routing tier.

These choices are intentionally explicit even though model availability changes.
Update this document and the root summary deliberately when the project owner
changes the preferred routing.

### Luna max admission gate

The main thread may select Luna at `max` without separate human approval only
when all of these conditions hold:

- The work is known-hard cross-file correctness work, an exhaustive bounded
  audit, or a prior `xhigh` attempt whose evidence shows insufficient reasoning
  depth or coverage.
- The prompt pins the exact file, document, artifact, or item corpus.
- The prompt defines a concrete deliverable, coverage ledger or equivalent
  completion evidence, and an explicit stop condition.
- Product and architecture decisions remain outside the delegated task.
- The worker must return partial or incomplete evidence when it cannot finish the
  bounded scope; it must not widen scope, retry itself, or create a continuation
  loop.

An `xhigh` attempt that failed because the task was ambiguous, incorrectly scoped,
blocked by missing authority, or based on competing target states is not eligible
for `max`. The main thread must clarify, decompose, or reroute it instead.

## When to delegate

Delegate when bounded work provides meaningful context preservation,
independence, turnaround, or cost savings. A simple task can still be worth
delegating when it requires several searches, reads, or tool calls that Luna can
perform economically. Appropriate work includes:

- bulk reading with a defined evidence question;
- focused investigation of one library, algorithm, or contract;
- mechanical edits with an exact writable file set;
- implementation of a decision already owned by canonical design;
- test or fixture updates with explicit expected behaviour;
- fresh-context adversarial review.

Keep a trivial single-read or single-command task in the main thread when
delegation overhead would clearly cost more than it saves.

## Delegation prompt contract

Every delegated task must state:

- the absolute worktree path and expected branch;
- whether the task is read-only or its exclusive writable file set;
- the authoritative read-only context it may inspect;
- the bounded question, deliverable, and success conditions;
- the exact validation commands the subagent may run;
- any canonical contract, DR revision, or research question that constrains the
  work;
- the required evidence and output format.

Before any delegated work, including read-only investigation, a subagent must run
`pwd` and `git branch --show-current`, compare both with the assigned values, and
stop if either differs.

If the assigned task conflicts with a named canonical source or exposes competing
target states, the subagent stops and reports the contradiction. It does not
choose a new product or architecture direction.

Parallel editing tasks must have disjoint write scopes. The main thread resolves
any cross-task interaction after the workers return.

Subagent validation is a closed allowlist. A subagent may run only the validation
commands named in its task. If none are named, it reports validation as deferred.
The main thread runs consolidated validation after integration.

A delegated task ends when its assigned work and named checks are complete. It
must not add unrequested cleanup, wording passes, structural audits, or substitute
validation. It must not start its own continuation or retry loop; any follow-up is
a new main-thread decision based on the returned evidence.

## Required safety boundary

Unless the prompt delegates an exact action with any required human authorization,
a subagent must not:

- inspect or alter review, CI, or pull-request state;
- invoke hosted or CLI CodeRabbit or another external review service;
- post review commands, resolve review threads, or trigger or rerun CI;
- commit, stage, push, retarget branches, open, merge, or close pull requests;
- wait for or poll CI, reviews, deployments, or other external systems;
- revert, delete, overwrite, or clean concurrent edits outside its assigned set.

The subagent preserves unrelated dirty work. It stops only when assigned-file
changes overlap ambiguously or the requested intent is unclear or risky, and it
reports that condition to the main thread.

The main thread must repeat this boundary in every delegation prompt. A short
reference to this file is not a substitute because a subagent may not receive the
same repository context.

## Independent review evidence

- Use a fresh-context reviewer that did not implement the target material for
  consequential initial review when practical.
- Require the reviewer to state the exact DR revision under review and its
  independence. Documents consulted may be listed when useful, but no exact
  source inventory is required.
- Reviewers report blocking issues first, avoid praise and restatement, and cap a
  normal convergence pass at five high-value findings.
- The main thread checks evidence, merges duplicates, identifies contradictions,
  and returns the findings to Ben; it does not auto-fix decision-bearing issues
  or start a review-until-clean loop.
- Stop after the selected level's passes, with at most five high-value findings
  per pass. Double is one pass per reviewer on the current revision, not
  review-until-clean. A later review is a new main-thread decision when a
  material revision or new batch warrants it.

Use the [fresh-reread preamble](../decisions/reviews/fresh-reread-preamble.md)
for DR and design convergence passes.

## Creature Kernel review lanes

Activate lanes only when enough design exists to review them. Candidate cohesive
lanes are:

1. Semantic body grammar and procedural schema.
2. Geometry, topology, meshing, and materials.
3. Rigging, IK, animation, and retargeting.
4. Collision, contact, deformation, and soft-body approximation.
5. Compiler/runtime boundaries, determinism, quality levels, and performance.
6. CLI/API workflows, exports, external assets, and host-engine adapters.

Use a few lanes that match the active decision set rather than spawning one agent
per question. The main thread owns cross-lane synthesis.

## External review services

CodeRabbit and similar hosted services are not an automatic Creature Kernel
dependency or merge gate. Agents must not install, enable, configure, invoke, or
submit repository content to an external review service without explicit human
authorization. Existing GitHub App access does not constitute that authorization.

Repository configuration can alter a service's behaviour but does not revoke its
platform permissions. Access removal belongs in the GitHub App installation
settings.

## Handoff

Every subagent return states:

- whether it changed files or supplied evidence only;
- every changed file, when applicable;
- reasoning-sensitive choices or assumptions;
- validation performed, including explicit `deferred` or `unavailable` states;
- unresolved concerns, incomplete coverage, and relevant concurrent-work risks.

The main thread reads every returned diff directly rather than treating the
worker's summary as proof. It reconciles interactions and runs consolidated
validation against the integrated work.

Every final handoff is brief and auditable. First provide one concise line per
subagent in the form `Subagent: <bounded role>; model: <model>; reasoning
effort: <effort>; <edited files: <paths> | evidence only>`. State the model and
reasoning effort explicitly, using `unknown` only when the runtime did not
expose them. Then provide one concise validation line covering both
subagent-scoped checks and the main consolidated checks, including explicit
`deferred` or `unavailable` states. The handoff also states the number of
subagents used and any explicitly authorized model-routing deviation or
incomplete review coverage; it does not require a prose summary.

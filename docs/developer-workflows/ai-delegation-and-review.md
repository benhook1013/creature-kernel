# AI delegation and review

Status: Proposed transition guidance; current safety and authority controls
remain operational under Accepted DR-0001 Revision 5

Use this workflow whenever the main thread considers delegating work or
requesting model-backed independent review. It preserves safety and ownership
boundaries while DR-0001 Revision 6 is Proposed. Ben approved the autonomous
engineering workflow direction on 2026-08-13 and the current review is
complete, but formal acceptance remains pending Ben's disposition. Product, specification, and architecture
proposals remain provisional unless their canonical decision status says
otherwise.

## Ownership boundary

The main `gpt-5.6-sol` thread owns:

- discussion with the human project owner;
- planning and task decomposition;
- product and architecture synthesis, without silently changing retained
  human direction;
- assignment and integration of delegated work;
- consolidated validation;
- Git, branch, commit, and pull-request operations;
- CI and review orchestration;
- external side effects;
- the final repository recommendation.

### Retained human authority

Ben retains decisions about product purpose and scope, user-visible experience
and quality targets, supported morphology or runtime promises, material
platform or engine lock-in, licensing, cost, privacy, external side effects,
large irreversible trade-offs, and acceptance or rejection of product or
direction-setting DRs. If a technical finding would change one of those
boundaries, the main thread asks Ben rather than resolving it autonomously.

### Proposed autonomous engineering lane

Within the retained boundaries, the main thread may settle exact schemas and
field names, deterministic and numeric algorithms, diagnostics and status
implementation, build integrity, code and test organization, reversible
dependencies and tools, implementation details, and defect resolution. A
technical choice can still require durable reasoning in a DR, design note,
issue, or implementation evidence, but it is not a routine user discussion
queue. This lane does not accept a DR, alter canonical product or architecture
direction, authorize external side effects, or grant subagents independent
product or architecture authority.

The main thread classifies findings as follows: correctness needed now is
fixed; a retained-human direction or material trade-off is escalated to Ben;
an implementation- or evidence-dependent question is recorded with its
trigger and deferred; speculative hardening without a present need is not
built. Review, tests, experiments, and evidence remain active and risk-scaled.
The lane supports extended research/implementation/test/review cycles until a
tangible milestone or a retained-human choice requires a handoff; it does not
run endless theoretical or review-until-clean loops.

Routine developer instrumentation, CLI JSON, metadata tables, diagnostics, and
correctness plumbing remain autonomous implementation even when surfaced in a
browser. Do not infer that browser-visible means product-visually meaningful: a
retained-human visual checkpoint requires actual rendered spatial, form,
appearance, motion, or interaction output for which subjective judgment is
useful, unless Ben explicitly asks to inspect the tooling or UI itself. Before
interrupting Ben for appraisal, state what subjective judgment he can make. If
the honest answer is only technical correctness already addressed by tests or
review, do not present it as his checkpoint. Continue small internal and
reversible work autonomously within the recorded runway and merge authority
until a genuine retained-human design choice or useful visual result is ready.

A subagent may collect evidence, implement a bounded decision already supported
by canonical design, or challenge a proposal. It must not make product or
architecture decisions independently. An independent reviewer recommends; the
human decision owner decides. A subagent may implement a technical choice
already settled by the main thread, but the main thread owns integration and
the delegated technical disposition.

## Round and batch pipeline

For product, direction-setting, architecture-boundary, or external-impact
choices, the main thread groups roughly two to five related decisions or
talking points into one discussion batch and finishes the discussion with Ben.
Routine technical implementation proceeds in the proposed autonomous lane
without a separate decision round. Luna applies non-trivial document edits,
evidence gathering, and bounded mechanical or implementation work; the main
thread inspects and integrates the batch and controls commits and other
external side effects. At the end of every substantive design-cycle handoff,
the main thread explicitly states
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
dependencies permit. Product, direction-setting, architecture-boundary, and
external-impact findings are not auto-fixed and the process does not run a
review-until-clean loop; mechanical defects faithful to settled intent may be
corrected. For technical findings inside the delegated boundary, the main
thread may fix correctness now or record an implementation/evidence trigger
for later. A new scope, trade-off, or authority choice returns to Ben.
Unaccepted material remains clearly labelled Proposed or provisional.

### Pre-proposal ideation

When generating a materially complex direction-setting, cross-cutting, or
hard-to-reverse product or architecture idea, the main thread first frames the
question and launches at least two separate fresh-context `gpt-5.6-luna`
passes at `xhigh`, each with a distinct named lens. Each pass must generate
candidate options rather than merely review an existing choice. The main thread
then compares their option spaces and contributes its own synthesis before
forming a proposal; explorations are inputs, not delegated project direction.
This is not required for bounded factual investigation, routine or small
technical choices, or implementation of an already-decided direction. Avoid
ceremonial duplicate prompts. These pre-proposal explorations do not satisfy or
replace any risk-scaled post-proposal adversarial review. Existing model
ceilings, Ben's authority, main-thread ownership, and cost/risk discipline
continue to apply.

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

### Capacity retry (provisional)

When a subagent launch or turn fails specifically because the selected model is
at capacity, the main thread waits 30–60 seconds and retries the same model at
the same reasoning tier once. It may escalate or fall back only when that
same-tier retry also fails, or when the task independently warrants a different
tier. The main thread reports to Ben immediately with the failed model/tier,
first-failure time, actual wait duration, wait/retry count, retry result, and
fallback model/tier, if any; it repeats the routing deviation and those details
in the end-of-round subagent status. The 30–60 second wait is provisional, and
these outcome reports are used to tune it without adding heavyweight telemetry.
Capacity retry does not apply to non-capacity failures and must never become an
unbounded retry loop.

### Thread-slot recovery (provisional)

First inspect the authoritative live-thread list and statuses. Treat an
`agent thread limit reached` failure as a structural slot condition, not model
capacity; do not apply model fallback or capacity retry. If an obsolete
interrupted or idle thread appears to occupy a slot, send it a no-work close-out
message, trigger one bounded follow-up turn instructing it to return
immediately without reads or edits, verify that it becomes `completed`, and
retry the blocked spawn once. Do not interrupt useful active work or recycle a
thread when fresh-context independence is required; wait for a genuine slot
instead. The harness has no delete/archive operation. If this bounded recovery
does not free a slot, report the authoritative statuses and stop rather than
starting an unbounded recovery loop.

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

## Hands-on feature trials

Before merging a PR that adds or materially changes an operable CLI, API,
viewer, tool, or similar user/integrator-facing feature, normally use two fresh
independent `gpt-5.6-luna` agents at `high` reasoning effort on the completed
local candidate, after implementation and focused checks and before the first
push or PR presentation. These are execution trials, not code reviews or
reruns of existing unit tests. Give the agents distinct lenses:

- first-use and operator usability;
- realistic and adversarial scenario behaviour.

Each prompt bounds the feature entrypoint, the claims or scenarios to exercise,
allowed temporary data, a stop condition, and prohibited side effects. For a
cost-bounded trial, exercise only the PR's new or materially affected
entrypoint and directly connected claims or flows, never the whole application
by default. Prefer headless CLI/API execution and reusable smoke harnesses; use
computer-use or screenshots only when the changed claim is visual or
interactive. Sample representative success and failure paths rather than the
full matrix. A broad release-level whole-application trial requires an
explicit scoped decision. Each report records the commands or scenarios run,
observed outputs, correctness defects, usability concerns or suggestions, and
untested gaps.

The main thread reproduces correctness findings, fixes merge blockers, and
reports remaining usability findings before merge. If findings cause material
fixes, rerun the affected hands-on scenario before push; tiny/local fixes need
only focused regression where appropriate. Later changes retain the
before-merge trial safeguard. Hands-on trials complement automated tests and
adversarial design/code review; they do not replace either or create a
review-until-clean loop. A purely internal change without an operable
entrypoint may use one focused integration-consumer exercise when two user
trials add no value.

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

CodeRabbit is authorized for deliberate advisory review under Ben's 2026-08-25
approval. It is not an automatic Creature Kernel dependency or merge gate. The
root `.coderabbit.yaml` expresses the repository policy: no inherited settings,
label or description opt-ins, automatic initial or incremental reviews, or
automatic chat replies. Higher-priority service-wide global overrides may still
supersede repository YAML. Neither the main thread nor a subagent may invoke,
post, or otherwise trigger a hosted CodeRabbit command, including
`@coderabbitai configuration` or `@coderabbitai full review`, unless Ben
explicitly requests that particular hosted invocation. CLI unavailability,
rate limiting, or incomplete coverage is not standing authorization to fall
back to hosted review.

Reserve CodeRabbit CLI for at most one optional end-of-PR pass over a completed,
committed candidate; do not use it during implementation or as an iterative
review-until-clean loop. While hosted and CLI allowance sharing across Ben's
projects remains unverified, Creature Kernel yields that allowance to FireMUD:
run the optional CLI pass only when Ben confirms FireMUD is not consuming the
allowance or explicitly authorizes the Creature Kernel pass. When warranted,
use `coderabbit review --agent --committed` with
`--base <remote>/<base-ref>` against a fetched remote-tracking base. Consume and
disposition the result before merge. Skipping CodeRabbit is not a merge blocker;
continue normal bounded subagent review, hands-on trials, local validation, and
CI without waiting for or substituting CodeRabbit.

Treat the current account's hosted, CLI, and usage-based availability across
Ben's projects as unverified until checked against the active plan and live
service response. Do not invoke either review interface while FireMUD or another
project is actively reviewing or while availability is unclear. Do not install
or invoke autonomous CodeRabbit skills that could consume quota outside this
deliberate workflow. Report unavailable or rate-limited review honestly rather
than bypassing or repeatedly retrying it. For the next hosted-allowance test,
Ben intends to trigger FireMUD first and then explicitly authorize Creature
Kernel's hosted invocation; Creature Kernel agents must not trigger, comment on,
or otherwise mutate FireMUD to arrange that sequence.

Other hosted review services still require explicit human authorization before
agents install, enable, configure, invoke, or submit repository content to them.
Existing GitHub App access alone does not constitute that authorization.

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

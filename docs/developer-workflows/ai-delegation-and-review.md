# AI delegation and review

Status: Proposed transition guidance; current safety and authority controls
remain operational under Accepted DR-0001 Revision 5

Use this workflow whenever work involves delegation, model-backed review,
hands-on feature trials, AI-control-plane changes, pull-request or
external-review activity, or merge activity. This is the sole
conditional detailed procedure for delegation, model routing, hands-on trials,
independent model review, PR batching, CodeRabbit and other external review,
merge gates, observation escalation, and subagent handoff. `AGENTS.md` remains
the always-on repository safety and authority kernel; this document supplies
the conditional procedure when its trigger applies.

## Main-thread ownership

The main `gpt-5.6-sol` thread owns:

- discussion with the human project owner;
- planning and decomposition into bounded steps;
- synthesis of product, architecture, research, and review evidence;
- assignment and integration of delegated work;
- consolidated validation;
- Git, branch, commit, pull-request, and merge operations;
- CI and review orchestration;
- external effects; and
- final repository decisions and recommendations.

Subagents are bounded executors, evidence gatherers, hands-on operators, or
independent reviewers; they do not make product or architecture decisions.
Reviewers recommend; the human decision owner accepts, rejects, or changes a
direction. The main thread owns integration and final disposition.

The recorded `Active runway` in `docs/project/status.md` is the destination
for autonomous progress. The main thread may advance direct, internal,
reversible prerequisites while it remains active and stops at the named human
checkpoint or another retained-human boundary. It does not replace that
checkpoint with an internal tooling, evidence, governance, or infrastructure
milestone.

Routine technical choices inside an accepted boundary may be settled by the
main thread, including implementation details, deterministic or numeric
algorithms, diagnostics, status plumbing, build integrity, code and test
organization, and reversible dependencies or tools. The main thread records
reasoning in the appropriate durable document when the choice warrants it.
It classifies findings as follows:

- correctness needed now: fix it;
- retained-human direction or material trade-off: ask the human owner;
- implementation- or evidence-dependent: record the trigger and defer; and
- speculative hardening without a present need: do not build it now.

Detailed decision-record states, acceptance prerequisites, review records, and
the acceptance operation remain owned by `docs/decisions/README.md`. This
workflow does not accept a DR, change a canonical product or architecture
contract, or grant a subagent authority that the canonical owner does not
have. Unaccepted material remains labelled `Candidate`, `Proposed`, `Under
Review`, or `provisional`, as appropriate to its state.

## Batches and research passes

The main thread groups related product, direction-setting, architecture-boundary,
or external-impact decisions into a discussion batch of roughly two to five
talking points. It finishes the discussion with Ben, has bounded edits or
evidence prepared, inspects and integrates the result, and then selects the
risk-scaled review level. Routine technical implementation proceeds without a
separate decision round. The main thread advances a substantial coherent PR or
direct prerequisite rather than creating slice churn or delegating an entire
autonomous runway as one task.

At the end of every substantive design-cycle handoff, the main thread states:
`Recommended adversarial level: None|Single|Double — <one-line reason>`

This is advice and a durable planning signal, not automatic acceptance. The
meaning of each level is defined in [Independent model review](#independent-model-review).

### Direction-setting ideation

For materially complex direction-setting, cross-cutting, or hard-to-reverse
product or architecture ideas, the main thread frames the question first and
launches two genuinely independent fresh-context `gpt-5.6-luna` passes at
`xhigh`, with distinct named lenses. Each pass generates candidate options;
neither pass merely validates a choice already made. The main thread compares
the option spaces and contributes its own synthesis before forming a proposal.
These passes are not delegated direction and do not replace post-proposal
adversarial review. Bounded factual investigation, routine or small technical
choices, and implementation of an already-decided direction do not require
this two-pass ideation.

### Morphology dossiers

When the morphology-dossier research lane is activated, the main thread uses
two independent fresh `gpt-5.6-sol` passes at `medium`, with distinct lenses
and source-backed factual or shape-knowledge questions. The main thread
synthesizes the two results and presents the outcome for human review. The
dossiers are research input, not executable truth, a schema, a supported
morphology promise, or an accepted product or architecture contract. If the
lane is not activated, these passes are not required.

## Model routing

- Use `gpt-5.6-luna` at `high` for routine bounded investigation, mechanical
  patches, straightforward test updates, and multi-step search or tool-driven
  work. Prefer this route when it preserves main-thread context or lowers cost.
- Use `gpt-5.6-luna` at `xhigh` for substantial delegated work and independent
  review. This is the normal Luna ceiling.
- Use `gpt-5.6-luna` at `max` only under the admission gate below.
- Use `gpt-5.6-sol` at `medium` when broad synthesis, ambiguous evidence, or
  general reasoning matters more than coding-agent throughput. This is a
  task-type escalation, not an automatic next tier after Luna.
- Use fresh Sol-medium review for foundational adversarial work by default
  when its breadth and authority boundaries require it. Use Luna-xhigh for
  narrow convergence, implementation, or bounded technical review when that
  better fits the corpus.
- `gpt-5.6-sol` at `high` requires explicit human approval and is the absolute
  subagent ceiling. Sol above medium is never implicit.
- Terra is not a normal routing tier.

### Luna max admission gate

The main thread may select Luna at `max` without a separate approval round only
when every condition below holds:

- the task is known-hard cross-file correctness work, an exhaustive bounded
  audit, or an `xhigh` attempt whose evidence shows insufficient reasoning
  depth or coverage;
- the prompt pins the exact file, document, artifact, or item corpus;
- the prompt defines a concrete deliverable, coverage ledger or equivalent
  completion evidence, and an explicit stop condition;
- product and architecture decisions remain outside the task; and
- the worker returns partial or incomplete evidence when it cannot finish and
  does not widen scope, retry itself, or create a continuation loop.

An `xhigh` failure caused by ambiguity, wrong scope, missing authority, or
competing target states is not a `max` admission. The main thread clarifies,
decomposes, or reroutes it instead.

### Capacity failures

Capacity handling applies only when the selected model reports a capacity
failure. The main thread records the first-failure time, waits an actual
30–60 seconds, and retries the same model at the same reasoning tier once.
It escalates or falls back only after that same-tier retry also fails, or when
the task independently warrants another tier. It does not retry non-capacity
failures or start an unbounded loop.

The main thread reports the failed model and tier, first-failure time, actual
wait duration, wait/retry count, retry result, and any fallback model and tier
to Ben immediately. It repeats the routing deviation and those details in the
end-of-round subagent status. The wait interval remains a lightweight,
outcome-reported operating rule rather than a telemetry project.

### Structural thread-slot failures

An `agent thread limit reached` result is a structural slot condition, not a
capacity failure. The main thread first inspects authoritative live-thread
statuses. If an obsolete interrupted or idle thread occupies a slot, it sends
one no-work close-out, gives it one bounded follow-up that instructs immediate
return without reads or edits, verifies that it becomes `completed`, and
retries the blocked spawn once. It does not interrupt useful work or recycle
a thread when fresh-context independence is required. If this bounded recovery
does not free a slot, the main thread reports the authoritative statuses and
stops rather than starting an unbounded recovery loop.

Before interrupting, killing, recycling, or duplicating a worker because a GUI
counter appears stale, the main thread inspects authoritative live-thread
status and messages or waits on the existing worker as appropriate.

## Delegation contract

Delegate liberally when a bounded task preserves context, provides
independence, improves turnaround, or lowers cost. Suitable tasks include
focused investigation or research, mechanical edits, settled implementation,
focused tests, hands-on trials, and fresh review. Keep a trivial single-read
local when delegation overhead costs more than it saves. Delegate one bounded
step at a time; the main thread chooses the next step after inspecting it.

A bounded subagent must not spawn descendants unless the main thread explicitly
authorizes a specifically bounded nested delegation. If a Luna task appears
to need descendants, it stops and reports. For non-direction-setting synthesis
only, the main thread may decompose the work into disjoint bounded Luna lanes
or route genuinely broad or ambiguous synthesis to Sol at medium; it may also
narrow scope, stop, or accept incomplete evidence. This fallback cannot replace
or reduce the two independent fresh-context Luna `xhigh` passes required for
direction-setting ideation, or the two independent fresh-context Sol `medium`
passes required for an activated morphology dossier lane. For either required
lane, incomplete evidence does not satisfy the required pass count. No worker
may self-escalate, widen scope, or decide product or architecture direction.

Every delegation prompt states all of the following:

- the absolute worktree path and expected branch;
- the required `pwd` and `git branch --show-current` preflight;
- whether the task is read-only or its exclusive writable file set;
- the exact read-only context and corpus it may inspect;
- the bounded question, deliverable, success conditions, and stop condition;
- the exact validation commands it may run;
- the canonical contracts, decision revisions, research records, or other
  constraints that govern the task;
- the required evidence and return format; and
- the prohibited Git, PR, CI, review, external, and destructive actions.

Before reading or editing, the worker runs `pwd` and
`git branch --show-current`, compares both outputs with the assigned values,
and stops if either differs. It reports the mismatch without touching files.
If the assigned scope conflicts with a canonical source or exposes competing
target states, it stops and reports the contradiction; it does not select a
new product or architecture direction.

The writable set is exact and exclusive. Parallel workers have disjoint write
scopes, and the main thread resolves any cross-task interaction after return.
Workers preserve unrelated dirty work and do not revert, delete, overwrite,
or clean files outside their assigned set. A read-only task does not acquire
write permission by implication.

Validation is a closed allowlist. A worker runs only commands named in its
prompt; when none are named, it reports validation as `deferred`. The main
thread performs consolidated validation after integration. A worker stops when
its deliverable and named checks are complete. It does not add cleanup,
unrequested wording or structural audits, substitute different validation, or
start a continuation or retry loop.

Unless an exact action is delegated with any required human authorization, a
worker does not inspect or alter Git, pull-request, CI, review, deployment, or
other external state; invoke or post to CodeRabbit or another external review
service; commit, stage, push, open, merge, close, or retarget a PR; trigger or
rerun CI; wait for or poll external systems; or perform destructive actions.
The main thread repeats this boundary in every delegation prompt. An exact
delegated action does not remove a required human approval.

When JavaScript tool-runner source composes a prompt, it uses an array of
ordinary quoted strings joined with newlines or structured text items. It does
not put delegation prose in a JavaScript template literal, because Markdown
backticks can terminate or alter the source before the worker starts. A
resulting syntax error is a payload-construction defect: correct it once and
report that no worker started.

For repository search, place every `rg` option before `--`, for example:
`rg -n -C 2 -- 'pattern' paths`.

A yielded long-running command has one owner and one live session. Its owner
resumes or inspects that exact session rather than reissuing the stage. Before
replacing a lost session, the owner inspects live processes and the exact
output target. A necessary retry publishes to a fresh staging or output path;
two writers never target one publication.

## Hands-on feature trials

Before merging a PR that adds or materially changes an operable CLI, API,
viewer, tool, or similar user/integrator-facing feature, the main thread
normally runs two fresh independent `gpt-5.6-luna` trials at `high` on the
completed local candidate. The trials run after implementation and focused
checks and before the first push or PR presentation when applicable. They are
execution trials, not code reviews or repetitions of existing unit tests.

The two trials use distinct lenses:

- first use and operator usability; and
- realistic and adversarial scenario behaviour.

Each trial prompt bounds the entrypoint, claims or scenarios, temporary data,
stop condition, and prohibited side effects. It exercises only the new or
materially affected entrypoint and directly connected flows, not the whole
application by default. Prefer headless CLI/API execution and reusable smoke
harnesses. Use computer-use or screenshots only for changed visual or
interactive claims. Sample representative success and failure paths rather
than the full matrix. A broad whole-application trial requires an explicit
scoped decision.

Each trial report records commands or scenarios, observed outputs, correctness
defects, usability concerns or suggestions, and untested gaps. The main thread
reproduces correctness findings, fixes merge blockers, and reports remaining
usability findings before merge. Material fixes rerun the affected trial
before push; tiny local fixes need only focused regression when appropriate.
Later changes retain this safeguard. A purely internal change without an
operable entrypoint uses one focused integration-consumer exercise when two
user trials add no value.

## Independent model review

Use a fresh-context reviewer that did not implement the material under review
when practical. The reviewer states the exact target or DR revision, its
independence, recommendation, confidence, blockers, limitations, and no more
than five high-value findings in a normal convergence pass. It reports
blocking issues first and avoids praise or restatement.

The risk-scaled levels are:

- `None` applies to purely mechanical or reversible work, or discussion with
  no created or materially revised consequential DR and no novel
  evidence-bearing claim. `None` cannot satisfy the review prerequisite for a
  created or materially revised consequential DR.
- `Single` is the normal default for a consequential DR or meaningful bounded
  design batch and means one fresh independent pass.
- `Double` is exceptional for direction-setting, cross-cutting,
  hard-to-reverse or locking, technically complex, strongly evidence-dependent,
  disputed, or difficult-to-audit work. It means two genuinely independent
  fresh passes with distinct named lenses, normally Sol at `medium` for
  foundational work.

More than `Double`, or Sol above `medium`, requires explicit human approval.
A material change to a proposal, constraints, alternatives, or consequences
makes older reviews stale. When `Double` remains justified, the current
revision normally receives two new passes. `Double` is one pass per reviewer
on the current revision, not review-until-clean. Ben may raise, lower, or
waive the recommendation under the decision-record process.

The main thread consolidates duplicates and contradictions and presents only
actionable findings. It may fix technical correctness faithful to settled
intent or record an implementation/evidence-dependent deferral. It does not
auto-fix decision-bearing findings, silently choose a new scope or trade-off,
or run a review-until-clean loop. A later review is a new main-thread decision
when a material revision or new batch warrants it. Detailed DR acceptance
remains governed by `docs/decisions/README.md`.

## Pull-request batching and merge gates

The main thread prepares substantial coherent PRs that make a reviewable unit
of progress. It combines directly related implementation, evidence, and
correctness work when their interactions matter, while preserving disjoint
reversible prerequisites where separation improves safety. It does not create
small slice churn merely to manufacture review events.

Autonomous merging is limited to the recorded active runway. The main thread
may merge an internal, reversible preparatory PR only after its required local
checks, hands-on trial or integration exercise when applicable, independent
review, CI gates, external-review gates, and finding dispositions are
complete, and only before the named human checkpoint is reached. The first
PR that reaches that checkpoint, changes user-visible CLI/viewer/API behaviour
for Ben's appraisal, or crosses a retained-human boundary is presented to Ben
before merge, must not be merged autonomously, and requires Ben's explicit,
recorded authorization.

Control-plane changes—including this workflow, review or automation
configuration, permissions, or merge policy—are presented to Ben and require
his explicit, recorded authorization before merge. Routine auto-merge,
unattended merge loops, administrator bypass, and an unrecorded runway are not
merge authority.

## CodeRabbit and external review

For a substantial PR that is final-review-ready, the main thread launches the
hosted CodeRabbit pass and the committed-diff CLI pass in parallel as one
deliberate cycle. Both review the same clean, immutable pushed OID. Before
launching, the main thread fetches the PR branch, requires a clean worktree,
verifies local `HEAD` equals the remote PR-head OID, and records that OID with
both results.

The CLI pass supports the hosted pass but cannot satisfy the hosted taper gate.
Every changed pushed head receives a fresh hosted-plus-CLI cycle; findings
from an earlier OID do not cover a later head. While the hosted pass runs, the
main thread does not push or mutate the remote PR head. It may prepare local
fixes without presenting them as reviewed.

After both results complete, the main thread verifies each finding, fixes or
explicitly dispositions it, runs the required local and CI checks, and pushes
the next head only when the result is ready for a new cycle. Hosted taper is
reached when a fresh hosted pass produces no new material findings, or only
repeats, non-actionable findings, disproportionate suggestions, or
out-of-scope items. Remaining items have recorded dispositions.

When warranted, the committed-diff command is
`coderabbit review --agent --committed --base <remote>/<base-ref>` against a
fetched remote-tracking base. This supporting command does not replace the
hosted pass, internal review, tests, hands-on trials, CI, or human gates.

If hosted CodeRabbit is unavailable or rate-limited, the main thread records
that outcome honestly and waits for availability while doing safe,
non-conflicting work, or stops for an explicit Ben waiver. It does not merge
without the waiver. Keep the immutable-head restriction until the hosted pass
reaches a terminal state. After one bounded wait and one status recheck,
record a service-declared failure or cancellation as terminal. If a stale run
exposes neither a terminal state nor a cancellation route, abandon that pass
as unavailable, record its reviewed OID and outcome, release the restriction,
and treat later output as stale. No unattended polling, automatic retry loop,
or timer continues the cycle.

Automatic initial and incremental reviews and automatic review/chat responses
remain disabled. The main thread may invoke CodeRabbit autonomously under this
procedure; a subagent invokes or posts to it only when the exact action is
delegated. Other hosted or external review services require explicit human
authorization before installation, enablement, configuration, invocation, or
submission of repository content. Review allowances, projects, and external
systems are not coordinated or coupled across repositories; the main thread
does not mutate another project.

## Operational observations

Every worker reports unexpected operational friction that forces a retry,
workaround, or changed tool path. The report includes the command or tool
category, exact error, attempt count, workaround, and what is known versus
inferred about the cause. Qualifying friction is unexpected, evidenced, and
recurring, reusable, or likely to save future retries or work rounds.

When qualifying friction occurs, the main thread searches
`docs/project/ai-observations.md` narrowly for a matching pattern, deduplicates
against existing entries, and records only a recurring or reusable evidenced
pattern before the round closes. A matching entry is reported as a recurrence,
not duplicated or silently bypassed. A subagent returns a concise `AI
observation candidate` unless it has explicitly exclusive inbox ownership;
the main thread is the default writer so parallel write scopes remain disjoint.

Ordinary work does not read the inbox. Existing entries are changed only in an
intentional tooling or instruction-maintenance round. That round resolves,
promotes, or removes entries deliberately. A repeated issue closes through a
concrete bounded fix to a repository wrapper, preflight, active instruction,
or other available tool path; restating the observation is not closure.

## Subagent handoff

Every subagent return states, concisely:

- whether it edited files or supplied evidence only;
- every changed file, when applicable;
- reasoning-sensitive choices and assumptions;
- validation performed, including explicit `deferred` or `unavailable`;
- unresolved concerns, incomplete coverage, and concurrent-work risks; and
- any capacity retry, routing deviation, or operational-observation candidate.

The main thread reads every returned diff directly rather than treating a
summary as proof, reconciles interactions, and performs consolidated
validation against the integrated result. It does not create an external
effect merely because a worker reports completion.

The final handoff is brief and auditable. Use one line per subagent:

`Subagent: <bounded role>; model: <model>; reasoning effort: <effort>; <edited files: <paths> | evidence only>`

Then provide one validation line covering subagent-scoped and main
consolidated checks, including explicit `deferred` or `unavailable` states.
State the number of subagents used, any explicitly authorized routing
deviation, and any incomplete review coverage. Do not substitute a prose
summary for these auditable lines.

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

## Main Worker and Overseer ownership

The Main Worker role owns:

- discussion with the human project owner;
- routine planning and decomposition into bounded steps;
- synthesis of product, architecture, research, and review evidence;
- assignment and integration of delegated work;
- direct visual inspection;
- consolidated validation;
- Git, branch, commit, push, and pull-request preparation under Runway and
  merge control;
- CI and review orchestration;
- external effects other than merge or auto-merge execution; and
- technical repository decisions and readiness recommendations.

The explicitly assigned Overseer role provides concise prioritization and
coordination, reviews consequential evidence, and makes direction
recommendations. Ben assigns final merge decisions and execution exclusively
to the Overseer. The Main Worker never merges or enables auto-merge, including
after an Overseer readiness acknowledgment. Ben's retained boundaries in
`AGENTS.md` remain unchanged.
Main Worker and Overseer are roles rather than model identities. Persistent
Astra use applies only to Ben's explicitly recorded task/role assignment and
its authorized scope and duration; it grants no permission for other or new
tasks or extensions. There is no serial permission gate for routine work, and
this split adds no descendant authority; the separately scoped
instruction-maintenance exception remains governed below.

At an already applicable merge or checkpoint gate, the Overseer may cheaply
inspect actual review outcomes and check status, verify the agreed taper and
standing user preferences, and catch omitted or forgotten instructions. This
lightweight coordination check does not repeat technical audits or tests,
create new ledgers or proof machinery, or open a routine permission round.
Existing consequential strategic and visual oversight remains unchanged.

The Main Worker proactively reports concise high-level progress and recommends
closure when useful review returns have diminished to minor improvements. It
does not wait for Ben to ask or chase perfect or zero-finding reviews. The
handoff summarizes the recent review trend and significance, current fixes,
and consequential remaining gaps, using existing evidence. The Overseer
assesses that recommendation promptly and decides whether to merge, request a
specific necessary fix, or raise a retained-human decision. This creates no
new ledger or acknowledgment loop; independent authorized work continues.

The Main Worker and Overseer delegate routine reading, writing, and tests by
default; they retain technical reasoning, decisive evidence inspection, and
narrow source-ambiguity review, and do not duplicate bulk investigations.
Executors and independent reviewers do not make product or architecture
decisions. Reviewers recommend; Ben accepts, rejects, or changes a direction.
The Main Worker owns integration and disposition of delegated work; the
Overseer owns final merge decisions and execution.

The recorded `Active runway` in `docs/project/status.md` is the destination
for autonomous progress. The main thread may advance direct, internal,
reversible prerequisites while it remains active and stops at the named human
checkpoint or another retained-human boundary. It does not replace that
checkpoint with an internal tooling, evidence, governance, or infrastructure
milestone.

Routine technical choices inside an accepted boundary may be settled by the
Main Worker within the active runway, including implementation details,
deterministic or numeric algorithms, diagnostics, status plumbing, build
integrity, code and test organization, and reversible dependencies or tools.
The Main Worker records
reasoning in the appropriate durable document when the choice warrants it.
It classifies findings as follows:

- correctness needed now: fix it;
- retained-human direction or material trade-off: ask the human owner;
- implementation- or evidence-dependent: record the trigger and defer; and
- speculative hardening without a present need: do not build it now.

### Coordination, status, and yields

Status and feedback replies steer the active mandate; they do not by
themselves pause or terminate it. Reports are nonblocking and do not require
an acknowledgement loop. A real yield states the scoped reason, continuation
owner, and actual continuation mechanism. Sending a message does not guarantee
that it wakes the recipient. Explicit pauses and named human checkpoints
remain authoritative.

The Main Worker continues independent authorized work while a scoped
consequential decision is pending unless Ben explicitly pauses that work. The
Overseer may select and direct bounded experimental next steps already within
Ben's recorded runway. Ben retains product and architecture acceptance and all
retained boundaries; routine technical progress does not require human
permission at every step or an obligatory extra review.

Detailed decision-record states, acceptance prerequisites, review records, and
the acceptance operation remain owned by `docs/decisions/README.md`. This
workflow does not accept a DR, change a canonical product or architecture
contract, or grant a subagent authority that the canonical owner does not
have. Unaccepted material remains labelled `Candidate`, `Proposed`, `Under
Review`, or `provisional`, as appropriate to its state.

## Cost-aware Main Worker orchestration

Before beginning a multi-step execution task, the Main Worker delegates a
bounded step when it is independently runnable. Settled implementation, test
writing, tool operation, monitoring, and evidence collection—including
inventories and hashes—belong to Luna by default, especially while the Main
Worker is an explicitly authorized Astra run. The Main Worker keeps technical
reasoning, scope and test selection, integration decisions, and direct
consequential geometry/vision inspection; it need not perform a worker's bulk
operations itself.

The Main Worker must not drift into a worker's job because tools are available
or because the work can be labelled verification. Review is targeted inspection
of decisive diffs and evidence, not repeated scans or execution. Delegated
validation execution may satisfy consolidated checks when the Main Worker
inspects and accepts the result. While useful independent work remains,
dispatch it before long local reading or polling; do not create slot quotas,
makework, or fill idle lanes. Exceptions are limited to trivial
latency-sensitive reads/edits or reasoning genuinely inseparable from Main
work, not broad loopholes. Do not duplicate worker scans or tests, or
repeatedly poll without a concrete need. This adds no rigid command budgets or
approval gates. “Main Worker” and “Overseer” are roles, not model names;
existing model authorization, routing, and human boundaries remain unchanged,
and this does not grant global Astra orchestration.

The responsible Main Worker or Overseer may read a short, cohesive instruction
document in full when judging a change. This semantic review is not duplication
of bulk fact gathering: delegate mechanical work, but a summary or isolated
diff cannot replace responsible whole-document assessment.

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
- `gpt-5.6-sol` at `high` or above requires explicit human approval. Sol above
  medium is never implicit.
- Astra-high is an exceptional advisory route for direction adjudication,
  difficult 3D or visual reasoning, or a high-consequence technical impasse
  when Astra can materially improve the path. Astra advises; the main thread
  still synthesizes and integrates, and Ben retains all product, architecture,
  quality, and other human decisions.
- Before every Astra call, the main thread announces the purpose and bounded
  scope to Ben. For one major checkpoint or decision batch, one primary Astra
  call plus at most one adversarial follow-up is allowed without another
  permission round. Additional calls require Ben's explicit approval. The
  main thread reports Astra use and its material recommendations in the
  handoff so Ben can see what informed the path. These announcement and
  separate-call cap rules apply to advisory Astra invocations, not every turn
  of a Ben-authorized persistent Astra Main Worker or Overseer; they do not
  authorize a global Astra orchestrator.
- Astra-max/ultra, Astra as an orchestrator, and routine Astra use are
  explicit-approval-only. Astra is not used for mechanical patches, ordinary
  tests or CI, CodeRabbit, bookkeeping, or as a throughput substitute for
  Luna. Promotional or reset capacity is temporary availability, not durable
  policy or authority.
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
For capture-before-geometry work, tests or helpers that calculate candidate
vertices or faces (for example `_append_ear`) are geometry and remain blocked
until the executor has captured the source; implementation-only delegates may
run syntax or static checks, but not those helper tests.

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
thread owns consolidated validation after integration: it may delegate
execution or collection of named checks, then inspects and accepts the results.
A worker stops when its deliverable and named checks are complete. It does not
add cleanup, unrequested wording or structural audits, substitute different
validation, or start a continuation or retry loop.

Unless an exact action is delegated with any required human authorization, a
worker does not inspect or alter Git, pull-request, CI, review, deployment, or
other external state; invoke or post to CodeRabbit or another external review
service; commit, stage, push, open, merge, close, or retarget a PR; trigger or
rerun CI; wait for or poll external systems; or perform destructive actions.
The main thread repeats this boundary in every delegation prompt. An exact
delegated action does not remove a required human approval.

Merge and auto-merge execution cannot be delegated to the Main Worker or any
subagent; they remain exclusively with the assigned Overseer.

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

More than `Double` still requires explicit human approval, and Sol above
`medium` remains explicit-approval-only. Astra-high follows its separate
exceptional-use limit in [Model routing](#model-routing): at most one primary
call and one adversarial follow-up per major checkpoint or decision batch
without further permission. An Astra recommendation is advisory and cannot
accept a direction, DR, contract, or human checkpoint.

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

Autonomous merging is limited to the recorded active runway. The assigned
Overseer may merge an internal, reversible preparatory PR only after its required local
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

Ben has separately authorized the assigned Overseer to originate, create, push,
review, and auto-merge small future instruction-maintenance PRs. An
eligible PR changes only `AGENTS.md` and/or this workflow, and only to update
reusable AI working instructions, links, or routing clarifications; it contains
no runtime code or feature work and does not change product purpose or scope,
product/specification/architecture contracts, the Active runway, retained-human
decisions, morphology or runtime promises, platform, licensing, cost, privacy,
or feature-PR merge authority. A bounded subagent prepares the change under the
normal delegation contract and must not spawn descendants. The Overseer
personally inspects the exact small diff and runs applicable documentation
validation and CI before merging; all ordinary review gates still apply. If an
active PR already owns either file,
integrate through its owner or defer; do not create a competing PR. This
standing authorization is Ben's explicit control-plane approval and merge
authorization only for that future class; it grants no broader authority and
waives no check. A mixed-scope or otherwise ineligible PR remains outside this
class; the Main Worker reports that gate. This maintenance permission does not
restrict separately authorized Overseer merges of implementation PRs.

## CodeRabbit and external review

For a substantial PR, the main thread pushes its first coherent, review-useful
head early enough for external review to run in parallel with later disjoint
work in the same PR. It does not wait for every planned addition to be complete
before starting the review clock. For each review-useful pushed head, launch the
hosted CodeRabbit pass on the current pushed head and a committed-diff CLI pass
in parallel as one cycle. Keep the remote head immutable while hosted review
runs. Every CLI pass reviews the entire current PR against the actual fetched
PR base; for a stacked PR, use its immediate lower branch as the base. Fetch
that exact base before each pass so the command targets the current whole-PR
diff. A partial, latest-commit-only, selected-path, or previous-delta review is
not a review cycle.

While hosted review runs, the main thread may continue useful whole-PR CLI
cycles on evolving local commits without waiting for hosted review. Each cycle
has a deliberate, finite purpose; unattended or purposeless repeats are not
allowed. A deliberate second hosted confirmation pass on an unchanged remote
head is allowed to establish consecutive convergence and needs no fake code
edit. Fix validated useful findings and rerun the affected whole-PR review.
Stop when the candidate and review findings are ready, or when another existing
gate applies. Do not push a local candidate until hosted review of the current
pushed head reaches a terminal state.

Practical taper is reached only when hosted CodeRabbit has stopped finding
meaningful or useful improvements on the actual final candidate. Usually this
means two consecutive hosted passes for that candidate, each producing roughly
0–2 findings, with every finding judged not to be a meaningful or useful
improvement (normally a false positive or tiny wording issue). This is a normal
stopping signal, not an arbitrary mandatory count of clean rounds. A substantive
change makes earlier review stale and requires review of the actual final
candidate. Meaningful or useful improvements include worthwhile correctness
fixes, tests, and maintainability improvements even when nonblocking. The Main
Worker judges usefulness and may reject false, disproportionate, non-actionable,
or out-of-scope suggestions without expanding scope. A raw zero-finding or
“zero material blockers” result, or a large count of prior passes, does not
establish taper by itself.

The whole-PR CLI runs independently on evolving local commits during the hosted
remote freeze and must also cease yielding accepted useful findings before the
final candidate is ready. This supports the hosted significance judgment
without creating a second mandatory clean-round or zero-finding gate; CLI
convergence cannot replace hosted convergence. Ordinary validation and CI,
finding disposition, independent review, external-review, checkpoint, and
human merge gates still apply. The committed-diff command is
`coderabbit review --agent --committed --base <remote>/<base-ref>` with the
actual fetched PR base; it supports but does not replace hosted review, internal
review, tests, hands-on trials, CI, or human gates.
GitHub checks and actual review outputs suffice as operational evidence. Keep
only transient base/head context needed to target running reviews; do not create
ledgers, review evidence documents, or routine PR disposition comments beyond
the count-only checkpoint comments specified in PR reports after each distinct
adjudicated completed hosted or CLI round, or persistent OID/command records
merely to prove that review occurred.

If hosted CodeRabbit is unavailable or rate-limited, the main thread reports
that outcome honestly and waits for availability while doing safe,
non-conflicting work, or reports the need for an explicit Ben waiver to the
Overseer. The Overseer does not merge without the required hosted review or an
explicit Ben waiver. Keep the
immutable-head restriction until the hosted pass reaches a terminal state. After
one bounded wait and one status recheck,
recognize a service-declared failure or cancellation as unavailable. If a stale
run exposes neither a terminal state nor a cancellation route, treat that pass
as unavailable, release the restriction, and treat later output as stale. No
unattended polling, automatic retry loop, or timer continues the cycle.

Automatic initial and incremental reviews and automatic review/chat responses
remain disabled. The main thread may invoke CodeRabbit autonomously under this
procedure; a subagent invokes or posts to it only when the exact action is
delegated. Other hosted or external review services require explicit human
authorization before installation, enablement, configuration, invocation, or
submission of repository content. Review allowances, projects, and external
systems are not coordinated or coupled across repositories; the main thread
does not mutate another project.

### PR reports

The PR is the shared reporting record; do not create a separately maintained
review chain. When reporting, read existing PR hosted summaries or threads and
the hosted and CLI count-only checkpoint comments, then present the actual
completion order including late posts,
ask the owner only for meaningful missing or ambiguous counts, and mark missing
evidence. Order PRs by merge priority while respecting dependencies, and state
the purpose, owner, and base, the review chain, and fix status separately from
gaps and readiness. Show each hosted round as `hosted (R/A)` and each CLI round
as `CLI R/A`, where R is raw findings and A is accepted useful findings.
Accepted means judged useful, whether or not blocking; it does not mean fixed.
Distinct completed rounds on the same SHA each count; exclude failed or
rate-limited rounds and include zero-finding rounds.

After each distinct adjudicated completed hosted or CLI round, check whether its
count snapshot is already present and, if absent, promptly post exactly one
short count-only PR comment. Use `**Hosted: 8 found / 6 accepted**` for hosted
rounds and `**CLI: 8 found / 6 accepted**` for CLI rounds; optionally include
the actual review time in Pacific/Auckland and an abbreviated SHA. Do not
include finding lists, explanations, validation inventories, or fix-tracking
promises in either comment. A read-only PR report does not trigger reviews,
resume work, merge, or routine chat reconstruction.

## Operational observations

Every executor reports unexpected operational friction that forces a retry,
workaround, or changed tool path. The report includes the command or tool
category, exact error, attempt count, workaround, and what is known versus
inferred about the cause. Qualifying friction is unexpected, evidenced, and
recurring, reusable, or likely to save future retries or work rounds.

The protected `docs/project/ai-observations.md` is the durable-record owner.
The Main Worker is the default durable-record writer and deduplication owner
when access is authorized, subject to this workflow's explicit inbox
restrictions. The Overseer adjudicates escalated recurring coordination and
instruction patterns and commissions bounded fixes. Neither role grants access
to the protected inbox, and the inbox is not authority over this workflow.
Severe blockers may escalate immediately. Executors return concise, evidenced
`AI observation candidate` reports; a matching candidate is reported as a
recurrence rather than duplicated or silently bypassed. Ordinary work does not
read the inbox, and no second backlog, inbox-zero obligation, or always-on
reading is created. Existing-entry changes remain limited to the intentional
tooling or instruction-maintenance round and its explicit access restrictions.
Future cleanup is explicitly authorized maintenance only; it addresses entries
whose evidence is resolved, obsolete, or disproved, preserves unrelated and
concurrent entries, and does not create an inbox-zero obligation.

### Selective process-improvement stewardship

At meaningful existing oversight or checkpoint boundaries, the explicitly
assigned Overseer considers reported, evidenced candidates for reusable
process, tooling, evidence, validation, or context-efficiency improvements.
The Overseer may delegate bounded fact gathering and evidence checks, then
personally judge usefulness, priority, and scope before commissioning the Main
Worker or an executor.

Recurrence is not required for an obvious, evidenced, low-cost improvement;
same-task bugs remain immediate implementation work. Prefer existing tools and
weigh benefit against implementation and maintenance cost. Existing authorized
reversible fixes may proceed; retained-human decisions go to Ben. This
stewardship uses reported or separately access-authorized material, preserves
protected-inbox access restrictions and human boundaries, and creates no fixed
cadence, whole-inbox scan, second backlog, or new suite.

A repeated issue closes through a concrete bounded fix to a repository wrapper,
preflight, active instruction, or other available tool path; restating the
observation is not closure.

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

The final handoff is concise and truthful: state the actual changes or evidence,
meaningful validation, unresolved blockers or limitations, and any routing
deviation when relevant. Actual outputs plus concise reporting are sufficient;
no fixed per-agent template or agent count is required.

# DR-0001: Documentation authority and decision-record process

ID: DR-0001

Scope: Governance

Status: Proposed

Revision: 6

Decision owner: Ben

Owner approval: Ben approved the workflow direction on 2026-08-13; formal
Revision 6 acceptance is pending current-revision review

Review status: Pending

Date proposed: 2026-08-13

Date decided: —

Supersedes: Revision 5 of this DR

Superseded by: —

## Context

Creature Kernel begins with consequential graphics, geometry, physics, and
runtime choices outside the project owner's established expertise. A previous
project introduced an architecture-only ADR mechanism and validation after a
large design corpus already existed, making reconstruction expensive and
ambiguous. That revision-1 proposal shape is retained here as history; it was
not an accepted predecessor.

The project needs explicit separation between product outcomes and externally
observable requirements; normative specifications and semantics; target
architecture and invariants; decision rationale; research questions and
references; experiments and evidence; developer workflows; project status and
roadmap; and implementation, tests, fixtures, benchmarks, and other proof.
Each authority may link to the others, but none may silently redefine another
authority's contract.

The process should preserve reasoning for consequential choices without making
ordinary wording, derived detail, or reversible implementation ceremonial. It
should give Ben a concise record, useful alternatives, and a proportionate
independent challenge before an important proposal is accepted, while
remaining proportionate to a hobby project. The working process has now been
exercised through several actual rounds. Ben requested proportional review
recommendations so review quality is retained without spending the default
token budget on unnecessary duplicate passes.

Revision 5's discussion-first workflow has now become a bottleneck for routine
engineering work. Ben's explicit direction on 2026-08-13 is to retain human
ownership of product direction and material external-impact choices while
delegating ordinary technical engineering decisions to the main thread. The
project still needs durable reasoning, adversarial challenge, evidence, and
clear escalation; it does not need a user-facing queue for every exact field
name, algorithm, diagnostic detail, build choice, or reversible implementation
decision. This revision proposes that bounded autonomous lane and keeps the
existing accepted safeguards in force until the revision is reviewed and
accepted.

## Decision

Adopt one neutral Decision Record (DR) system in `docs/decisions/` for
consequential choices. A DR may cover Governance, Product, Specification,
Architecture, or a cross-cutting combination. Its `Scope:` metadata and
registry row identify the canonical authorities affected; the DR explains
rationale and links to those authorities but does not replace them.

### Bootstrap history and continuing effect

The provisional condition authorized during Ben's 2026-08-08 governance round
ended when Ben accepted Revision 5 on 2026-08-09. The contributor instructions,
workflow guidance, repository-safety checks, authority separation, proposal
labels, review evidence, and explicit human ownership safeguards continue under
this accepted Governance DR. Acceptance does not make product, specification,
or architecture proposals binding merely because working documents describe
them. Any later supersession or material replacement of DR-0001 requires a
controlled migration that preserves proposal and review history.

Revision 6 is Proposed and materially supersedes Revision 5's workflow, but
does not silently change its status. Until Ben accepts the current revision,
Revision 5 remains the accepted governance baseline: authority separation,
proposal labels, review prerequisites, repository safety, explicit human
ownership, and restrictions on external side effects continue to apply. Ben's
explicit 2026-08-13 workflow direction is recorded here as a controlled
transition instruction for the autonomous engineering lane below; it is not
formal acceptance of this DR.

Require a DR only for a choice that is hard to reverse, cross-cutting,
contractual or public, performance-defining, dependency/portability/licensing
locking, or likely to be disputed. Ordinary wording, derived detail, and
reversible implementation stay lightweight unless they later cross one of
those thresholds.

### Retained human authority and delegated engineering lane

Ben retains decisions about product purpose and scope, user-visible
experience and quality targets, supported morphology or runtime promises,
material platform or engine lock-in, licensing, cost, privacy, external side
effects, large irreversible trade-offs, and acceptance or rejection of
Product, Architecture, or other direction-setting DRs. The main thread must
escalate when a technical proposal would change one of those boundaries.

Within those boundaries, the main thread has delegated authority to settle
technical engineering choices: exact schemas and field names; deterministic
and numeric algorithms; diagnostics and status implementation; build
integrity; code and test organization; reversible dependencies and tools;
implementation details; and defect resolution. Consequential technical
reasoning remains durable in a DR, issue, design note, or implementation
evidence, but it is not a queue of routine user decisions. A technical DR
remains Proposed until its review and human disposition requirements are met;
delegated implementation authority does not accept a DR or alter canonical
product or architecture direction.

Review findings use four dispositions. The main thread fixes correctness that
is needed now; asks Ben when a finding reaches a retained-human boundary or
material trade-off; records a trigger and defers questions that require
implementation or evidence; and does not build speculative hardening without
a present need. Risk-scaled adversarial review, tests, experiments, and
implementation checkpoints remain required where useful. The process does
not skip substantive review, run endless theoretical rounds, or run
review-until-clean loops. The main thread may continue research,
implementation, testing, and bounded review until a tangible milestone or a
retained-human choice requires a handoff.

Use the following round-based working pipeline:

1. For product, direction-setting, architecture-boundary, or external-impact
   choices, the main thread discusses and resolves a batch of roughly two to
   five related decisions or talking points with Ben. Routine technical
   implementation work proceeds in the autonomous engineering lane without a
   separate decision round.
2. Luna applies bounded documentation, evidence, mechanical, or implementation
   work supported by settled direction. The main thread inspects and
   integrates every change, resolves delegated technical findings, and
   controls commits and other external side effects.
3. At the end of every substantive design-cycle handoff, the main thread
   explicitly states `Recommended adversarial level: None|Single|Double —
   <one-line reason>`. This is advice to Ben and a durable planning signal,
   not automatic acceptance. The selected risk-scaled level examines the
   exact edit batch and affected canonical documents in the following round,
   while the next independent research batch may proceed when dependencies
   permit. `None` is for purely mechanical/reversible work or discussion with
   no created or materially revised consequential DR and no novel
   evidence-bearing claim; it cannot satisfy the review prerequisite for a
   created or materially revised consequential DR, which still needs review or
   Ben's explicit recorded waiver. `Single` is the normal default and means
   one fresh independent pass. `Double` is exceptional for direction-setting,
   cross-cutting, hard-to-reverse or locking, technically complex, strongly
   evidence-dependent, disputed, or difficult-to-audit work; it means two
   genuinely independent fresh passes with distinct named lenses, normally Sol
   medium for foundational work. Duplicate prompts do not constitute
   diversity. More than Double or Sol above medium requires Ben's explicit
   approval. Ben may raise or lower the recommendation or waive as already
   governed. When Double remains justified by the decision's technical or
   directional impact, a material revision normally receives Double again
   unless Ben changes or waives it.
4. At a design handoff, the main thread returns a concise synthesized review
   status with the next decision batch. For autonomous engineering work, it
   may disposition technical findings and correct defects within the delegated
   boundary. A finding that changes scope, a product or architecture
   boundary, a material trade-off, or an external side effect returns to Ben.
   Neither lane runs a review-until-clean loop.

Important DRs normally receive a current-revision adversarial review at the
recommended level before acceptance. Double means one pass per reviewer on the
current revision, not review-until-clean; the main thread consolidates duplicate
or contradictory findings and presents only actionable findings. Ben may
explicitly waive a review by recording `Review status: Waived` and one
non-placeholder `Waiver reason:` line. Only Ben accepts or rejects a DR;
proposals remain Proposed until reviewed or explicitly waived and Ben gives a
disposition.

The main `gpt-5.6-sol` thread owns human discussion, decomposition, synthesis,
integration, validation, Git and pull-request operations, review orchestration,
external side effects, and final recommendations. `gpt-5.6-luna` is preferred
for non-trivial document edits, evidence gathering, mechanical work, and
bounded technical audits. Fresh `gpt-5.6-sol` at medium is the default for
foundational adversarial review. Luna at xhigh remains suitable for narrow
convergence or implementation review. Sol above medium requires Ben's explicit
approval, and Luna max remains subject to its separate admission gate.

Material without Ben's explicit disposition remains clearly labelled `Proposed`
or `provisional`; assistant-synthesized product and architecture content must
not be described as an accepted active baseline.

## Consequences

- Product, specification, architecture, rationale, evidence, workflow, status,
  and implementation authorities remain inspectable and separately maintained.
- A neutral DR captures governance, product, specification, architecture, or
  cross-cutting choices without implying that every consequential choice is
  architectural.
- The high trigger threshold keeps routine editing and reversible implementation
  lightweight while preserving reasoning for disputed or locking choices.
- Risk-scaled review preserves useful distance from the authoring context while
  keeping a Single pass as the normal default. Always-double review would
  waste tokens and duplicate correlated findings; no or Single review could
  under-review technically hard direction changes. Distinct-lens Double is
  reserved for cases where its added coverage is justified, without requiring
  a review-until-clean process.
- Proposals may remain useful before acceptance, but their provisional status
  must remain visible to contributors and tooling.
- Git history is sufficient revision history for this project; no separate
  provenance system is required by the process.
- The main thread carries integration and validation responsibility while
  bounded delegation preserves context and independent challenge.
- Routine technical decisions no longer block on a user-facing discussion
  round, while consequential reasoning remains durable and inspectable.
- The main thread must recognize when implementation evidence crosses into a
  retained product, architecture, or external-impact boundary; escalation is
  the safety valve for that failure mode.
- Longer autonomous engineering cycles increase throughput but make checkpoint
  summaries, tests, review evidence, and explicit escalation triggers more
  important.
- The process should be revisited if its review and registry cost outweighs the
  reasoning it preserves.

## Alternatives Considered

The review-selection alternatives for the current revision are:

### Option 1: No routine independent review

This minimizes token use and turnaround for every batch. It is not selected
because technically hard, cross-cutting, or direction-setting changes could
pass without a fresh challenge, and `None` cannot satisfy the review
prerequisite for a created or materially revised consequential DR.

### Option 2: Always Single

One fresh independent pass for every consequential batch is simple and keeps a
useful review boundary. It is not selected as the universal rule because a
Single pass can under-review technically complex, disputed, strongly
evidence-dependent, or difficult-to-audit direction changes.

### Option 3: Always Double

Two independent passes would increase coverage for high-impact changes. It is
not selected as the universal rule because it would waste tokens on routine
consequential batches and can duplicate correlated findings when reviewers
share the same lens; a second pass is useful only when its distinct lens is
justified.

### Option 4: Risk-scaled None/Single/Double

Recommend `None` for purely mechanical/reversible work or discussion with no
created or materially revised consequential DR and no novel evidence-bearing
claim, `Single` as the normal default for consequential DRs and meaningful
bounded design batches, and distinct-lens `Double` for exceptional
direction-setting, cross-cutting, hard-to-reverse or locking, technically
complex, strongly evidence-dependent, disputed, or difficult-to-audit work.
`Double` means one current-revision pass per genuinely independent reviewer,
not review-until-clean. This retains review quality while scaling effort to
risk and preserving Ben's ability to raise, lower, or waive the recommendation.
Recommendation for review selection: Option 4. Revision 6 additionally
selects Option 5 for the workflow authority boundary below.

### Option 5: Autonomous engineering lane inside retained human boundaries

This keeps Ben in control of product direction, architecture boundaries,
material external effects, and acceptance of direction-setting DRs while the
main thread resolves routine technical engineering choices. It is selected
for Revision 6 because it removes ceremonial implementation rounds without
removing review, evidence, durable reasoning, or escalation. It does not
authorize the main thread or a subagent to silently change the product,
architecture target, public promises, licensing, cost, privacy posture, or
external systems.

### Option 6: Continue requiring Ben's review of every technical choice

This would preserve the existing discussion-first workflow, but it is not
selected because it spends the owner's attention on decisions he explicitly
delegated and delays implementation evidence that would answer many questions
more reliably. The retained-human boundary and risk-scaled review provide a
more useful control point.

### Option 7: Delegate all technical and direction decisions

This would maximize throughput, but it is rejected because it would blur
product intent, architecture ownership, external-impact authority, and DR
acceptance. Subagents remain bounded executors or reviewers, and the main
thread must escalate retained-human choices.

### Historical structural alternatives

#### Informal Markdown and chat only

Lowest immediate effort, but authority boundaries, rationale, objections, and
decision state become difficult to recover. A small registry and concise DR
provide durable memory without requiring every edit to become a decision.

#### Lightweight owner map and decision log only

This would reduce ceremony further and may suit many routine choices. The
neutral DR retains a little more rationale, alternatives, and review context
for the consequential choices most likely to be disputed, while the high
trigger keeps the mechanism from covering ordinary work.

#### Full mature-project governance immediately

Machine-validated provenance, immutable review bundles, structured objection
ledgers, and reconciliation machinery would provide stronger controls, but are
disproportionate before implementation exists. Revision 2 and Revision 3
reviews explored those audit-heavy recommendations; Revision 5 deliberately
does not require them.

#### Separate architecture-only mechanism

The revision-1 architecture-only proposal shape kept useful rationale and
review discipline, but classified governance, product, and cross-cutting
choices too narrowly. Neutral DRs preserve the useful reasoning while making
scope explicit. This proposal does not claim that the earlier mechanism was
accepted.

#### Immediate review within the discussion batch

This would reduce latency, but the authoring context and canonical documents
would often be reviewed before the batch settled. The next-round risk-scaled
review creates a useful fresh-context boundary at a deliberate delay.

## Adversarial Review Response

[Revision 2 review](reviews/DR-0001-rev-02-review-01.md) and
[Revision 3 review](reviews/DR-0001-rev-03-review-01.md) are preserved as
historical `Revise` recommendations. They raised bootstrap/status and
review-evidence concerns, followed by narrower concerns about binding
technical guidance and mutable exact-revision evidence. Ben deliberately chose
the lighter hobby-project process in Revision 4 after considering those
audit-heavy recommendations.

The [Revision 4 review](reviews/DR-0001-rev-04-review-01.md) is historical and
stale for Revision 5. It recommends `Accept` with high confidence and found no
blockers for Revision 4, while leaving three non-blocking risks visible and
deferred: lightweight Git-based exact-batch reconstruction, duplicated
model-routing guidance that may drift, and the removed validator unit-test
suite, which should be revisited if the validator grows or gives a false
acceptance signal. Those findings do not satisfy the current Revision 5 review
prerequisite.

The [Revision 5 architecture/governance review](reviews/DR-0001-rev-05-review-01.md)
and Ben's acceptance of Revision 5 remain valid historical evidence for that
revision only. They are stale for Revision 6 and do not satisfy its current
review prerequisite. Ben explicitly approved the workflow direction on
2026-08-13; that approval is recorded in the metadata as owner input, not as
formal acceptance of this proposed revision. Revision 6 current-revision
review is Pending. Recommended adversarial level: Double — this is a material
governance change with a broad workflow effect, so two independent fresh
passes should test the retained-human boundary and the quality/escalation
controls.

## Implementation and Proof Obligations

- Maintain the authority index, neutral DR registry, concise templates, review
  records, and visible status vocabulary.
- Keep proposals and provisional canonical documents visibly distinct from
  accepted contracts.
- Record the selected risk level, current revision, recommendation, limitations,
  and material findings in each adversarial review; Ben may waive the review as
  described above. A `None` recommendation cannot substitute for review of a
  created or materially revised consequential DR.
- Keep the proposed autonomous lane visibly distinct from the currently
  accepted Revision 5 baseline until this revision is reviewed and accepted;
  after acceptance, update the navigation and operational summaries that
  still identify Revision 5 as current.
- At implementation checkpoints, retain concise evidence of technical choices,
  tests, review findings, deferred triggers, and any escalations. Do not turn
  those records into a routine approval queue.
- Preserve rejected, superseded, and stale reviews as historical reasoning.
- Revisit batch size, model routing, trigger threshold, and review overhead
  after enough rounds provide evidence that the lightweight process is or is not
  useful.

## Canonical Design Links

- [Documentation authority and navigation](../README.md)
- [Decision record process](README.md)
- [Repository evolution](../project/repository-evolution.md)
- [Contributor instructions](../../AGENTS.md)
- [AI delegation and review workflow](../developer-workflows/ai-delegation-and-review.md)

## Reversibility and Revisit Triggers

The process is documentation and workflow guidance, so it is reversible. Revisit
if DR overhead delays ordinary work, reviewers cannot distinguish canonical
owners, review quality is poor, model routing no longer fits available
expertise, validation becomes costly, or important choices bypass review. Any
material governance change receives a new DR revision and the next-round review
rule applies again. Escalate or revisit this lane if the main thread repeatedly
crosses retained-human boundaries, technical records become too thin to audit,
implementation evidence is routinely ignored, or autonomous work causes an
external-impact or product-direction surprise.

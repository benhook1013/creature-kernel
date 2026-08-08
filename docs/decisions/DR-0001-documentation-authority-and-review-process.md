# DR-0001: Documentation authority and decision-record process

ID: DR-0001

Scope: Governance

Status: Proposed

Revision: 5

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Supersedes: —

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

## Decision

Adopt one neutral Decision Record (DR) system in `docs/decisions/` for
consequential choices. A DR may cover Governance, Product, Specification,
Architecture, or a cross-cutting combination. Its `Scope:` metadata and
registry row identify the canonical authorities affected; the DR explains
rationale and links to those authorities but does not replace them.

### Provisional bootstrap trial

Ben's 2026-08-08 governance-round direction authorizes this mechanism as a
provisional operational trial until DR-0001 receives a disposition. Contributor
instructions, workflow guidance, and repository-safety checks may operate
provisionally during the trial to preserve authority separation, proposal
labels, review evidence, repository safety, and explicit human ownership.
Product, specification, and architecture proposals are not binding merely
because working documents describe them. Trial operation is not acceptance of
DR-0001 or DR-0002–0005 and cannot accept any DR automatically. If Ben rejects
or materially replaces DR-0001, the main thread retires or migrates trial-only
controls while preserving proposal and review history. Documents must
distinguish an active or operational structure from an accepted contract.

Require a DR only for a choice that is hard to reverse, cross-cutting,
contractual or public, performance-defining, dependency/portability/licensing
locking, or likely to be disputed. Ordinary wording, derived detail, and
reversible implementation stay lightweight unless they later cross one of
those thresholds.

Use the following round-based working pipeline:

1. The main thread discusses and resolves a batch of roughly two to five
   related decisions or talking points with Ben.
2. Luna applies non-trivial documentation, evidence, or mechanical changes
   supported by that settled discussion. The main thread inspects and
   integrates the changes and commits them.
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
4. The main thread returns a concise synthesized review status with the next
   decision batch. Decision-bearing findings are not auto-fixed and the process
   does not run a review-until-clean loop. Mechanical defects faithful to
   settled intent may be corrected; a new scope, trade-off, or authority choice
   returns to Ben.

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
Recommendation: Option 4

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

The current [Revision 5 architecture/governance review](reviews/DR-0001-rev-05-review-01.md)
recommends `Accept` with High confidence and found no actionable findings.
Revision 5 remains Proposed with Review status Complete and owner approval
pending; the review recommendation does not imply Ben's disposition.

## Implementation and Proof Obligations

- Maintain the authority index, neutral DR registry, concise templates, review
  records, and visible status vocabulary.
- Keep proposals and provisional canonical documents visibly distinct from
  accepted contracts.
- Record the selected risk level, current revision, recommendation, limitations,
  and material findings in each adversarial review; Ben may waive the review as
  described above. A `None` recommendation cannot substitute for review of a
  created or materially revised consequential DR.
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
rule applies again.

# DR-0001: Documentation authority and decision-record process

ID: DR-0001

Scope: Governance

Status: Proposed

Revision: 4

Decision owner: Ben

Owner approval: Pending

Review status: Pending

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
should give Ben a concise record, useful alternatives, and one fresh challenge
before an important proposal is accepted, while remaining proportionate to a
hobby project.

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
3. One fresh adversarial review examines the exact edit batch and affected
   canonical documents in the following round, while the next independent
   research batch may proceed when dependencies permit.
4. The main thread returns a concise synthesized review status with the next
   decision batch. Decision-bearing findings are not auto-fixed and the process
   does not run a review-until-clean loop. Mechanical defects faithful to
   settled intent may be corrected; a new scope, trade-off, or authority choice
   returns to Ben.

Important DRs normally receive one current-revision adversarial review before
acceptance. Ben may explicitly waive a review by recording `Review status:
Waived` and one non-placeholder `Waiver reason:` line. Only Ben accepts or
rejects a DR; proposals remain Proposed until reviewed or explicitly waived and
Ben gives a disposition.

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
- A next-round fresh review creates useful distance from the authoring context
  without requiring an audit or a review-until-clean process.
- Proposals may remain useful before acceptance, but their provisional status
  must remain visible to contributors and tooling.
- Git history is sufficient revision history for this project; no separate
  provenance system is required by the process.
- The main thread carries integration and validation responsibility while
  bounded delegation preserves context and independent challenge.
- The process should be revisited if its review and registry cost outweighs the
  reasoning it preserves.

## Alternatives Considered

### Informal Markdown and chat only

Lowest immediate effort, but authority boundaries, rationale, objections, and
decision state become difficult to recover. A small registry and concise DR
provide durable memory without requiring every edit to become a decision.

### Lightweight owner map and decision log only

This would reduce ceremony further and may suit many routine choices. The
neutral DR retains a little more rationale, alternatives, and review context
for the consequential choices most likely to be disputed, while the high
trigger keeps the mechanism from covering ordinary work.

### Full mature-project governance immediately

Machine-validated provenance, immutable review bundles, structured objection
ledgers, and reconciliation machinery would provide stronger controls, but are
disproportionate before implementation exists. Revision 2 and Revision 3
reviews explored those audit-heavy recommendations; Revision 4 deliberately
does not require them.

### Separate architecture-only mechanism

The revision-1 architecture-only proposal shape kept useful rationale and
review discipline, but classified governance, product, and cross-cutting
choices too narrowly. Neutral DRs preserve the useful reasoning while making
scope explicit. This proposal does not claim that the earlier mechanism was
accepted.

### Immediate review within the discussion batch

This would reduce latency, but the authoring context and canonical documents
would often be reviewed before the batch settled. A single next-round review
creates a useful fresh-context boundary at modest deliberate delay.

## Adversarial Review Response

[Revision 2 review](reviews/DR-0001-rev-02-review-01.md) and
[Revision 3 review](reviews/DR-0001-rev-03-review-01.md) are preserved as
historical `Revise` recommendations. They raised bootstrap/status and
review-evidence concerns, followed by narrower concerns about binding
technical guidance and mutable exact-revision evidence. Ben deliberately chose
the lighter hobby-project process in Revision 4 after considering those
audit-heavy recommendations. Revision 4 is Proposed and awaits one fresh
review of this edit batch; this response does not claim that an earlier finding
was independently re-reviewed or that any DR is accepted.

## Implementation and Proof Obligations

- Maintain the authority index, neutral DR registry, concise templates, review
  records, and visible status vocabulary.
- Keep proposals and provisional canonical documents visibly distinct from
  accepted contracts.
- Record a current revision, recommendation, limitations, and material findings
  in an important adversarial review; Ben may waive the review as described
  above.
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

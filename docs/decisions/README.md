# Decision record process

Status: Active process proposal

This directory records consequential decisions and their rationale. Decision
Records (DRs) do not replace canonical product, specification, or architecture
documents. An accepted DR must identify and update the contracts it affects.

## When a DR is required

Use a DR only when a choice is consequential because it is one or more of:

- hard to reverse;
- cross-cutting across authorities or components;
- contractual or public;
- performance-defining;
- locking a dependency, portability boundary, or licence; or
- likely to be disputed.

Ordinary wording, derived detail, and reversible implementation do not require
a DR unless they later cross one of these thresholds.

Each DR declares a `Scope:` using one or more of `Governance`, `Product`,
`Specification`, and `Architecture`. A cross-cutting scope names every
affected authority. The scope classifies the record; it does not grant the DR
authority to replace the canonical documents.

## States

- `Candidate`: named in the registry but not yet a concrete proposal.
- `Proposed`: a complete proposal exists and can be challenged.
- `Under Review`: adversarial review is active for the current revision.
- `Accepted`: Ben, the human decision owner, approved the reviewed revision.
- `Rejected`: considered and intentionally not selected.
- `Superseded`: replaced by a later accepted DR.
- `Withdrawn`: proposal removed before a decision.

Unaccepted material remains clearly labelled `Proposed` or `provisional`. A
plausible assistant synthesis is not an accepted product or architecture
baseline.

## Revision and review rule

Every proposal has an integer revision. A material change to the decision,
constraints, alternatives, or consequences increments its revision. Reviews name
the exact revision they assessed. An older review does not satisfy acceptance
for a newer revision.

Acceptance is round-delayed:

1. Finish a discussion batch of roughly two to five related decisions or
   talking points.
2. Integrate the canonical document changes and Proposed DR revisions for the
   batch, then validate the integrated result.
3. In the next round, request a fresh review of the exact current revision and
   its canonical review bundle: affected product, specification, architecture,
   governance, research, and experiment documents as applicable. Start
   independent research for the next batch concurrently when dependencies
   permit.
4. Record responses and any revision, then ask Ben for an explicit disposition
   only after the current revision has been reviewed. Return a short synthesized
   review status and name the next discussion batch.

The review recommends; it does not decide. A DR may become `Accepted` only when:

1. An adversarial review covers its current revision and affected canonical
   documents.
2. Material objections have an explicit response.
3. Required experiments are complete or explicitly deferred with risk recorded.
4. Canonical design links and proof obligations are identified.
5. Ben explicitly approves it.

A human waiver may replace a missing review or proof obligation, but the DR must
record the waiver, reason, and accepted risk. A waived review is not implicit
owner approval. Record explicit acceptance as
`Owner approval: Approved by <Decision owner>` in the DR metadata. Until then
use `Owner approval: Pending`. When `Review status` is `Waived`, record
non-placeholder `Waiver reason` and `Accepted risk` lines in the review response.

The validator checks metadata, scope and registry agreement, revision and links,
owner approval, and waiver fields. Human review remains responsible for judging
whether objections were answered adequately and whether experiment deferrals or
accepted risks are reasonable.

## Workflow and ownership

1. The main thread groups related discussion into a batch of roughly two to five
   decisions or talking points.
2. Add candidates to [the registry](registry.md), then write concrete proposals
   from [the decision record template](decision-record-template.md).
3. Keep new records `Proposed`, with review `Pending` and revision `1` unless a
   documented material revision is being prepared.
4. Before the next round, integrate the batch and identify its canonical review
   bundle. Do not treat the batch as accepted.
5. In the next round, commission a fresh-context adversarial review using [the
   review template](reviews/adversarial-review-template.md). Use the
   [fresh-reread preamble](reviews/fresh-reread-preamble.md) for convergence.
6. Record responses, revise when necessary, and retain earlier revisions and
   reviews as history.
7. Ben accepts, rejects, withdraws, requests another revision, or leaves the DR
   proposed with a named blocker.
8. Update canonical documents and track implementation and proof obligations
   only as the accepted decision requires.

The main `gpt-5.6-sol` thread owns human discussion, decomposition, synthesis,
integration, validation, Git and pull-request operations, CI and review
orchestration, external side effects, and the final repository recommendation.
It does not delegate product or architecture decisions. Luna is preferred for
non-trivial document edits, evidence gathering, mechanical work, and bounded
technical audits. Fresh Sol-medium reviewers are the default for foundational
adversarial review; Luna-xhigh is suitable for narrow convergence and
implementation review. Sol above medium requires explicit Ben approval, and
Luna max remains subject to its admission gate.

## Independence

When practical, the adversarial reviewer should use a fresh context, separate
agent/model, or external domain expert rather than the reasoning context that
authored the proposal. The review must state its independence and limitations.

## Naming

- Decision record: `DR-NNNN-short-title.md`
- Review: `DR-NNNN-rev-RR-review-NN.md`

Numbers are never reused. `Scope` is required in both every DR and its registry
row.

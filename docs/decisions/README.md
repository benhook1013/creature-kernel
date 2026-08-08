# Decision record process

Status: Provisional operational trial

This directory records consequential decisions and their rationale. Decision
Records (DRs) do not replace canonical product, specification, or architecture
documents. An accepted DR identifies and updates the contracts it affects.

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
affected authority. Scope classifies the record; it does not grant a DR
authority to replace canonical documents.

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
baseline. The registry, process, and review structure are active/operational
under the DR-0001 Revision 4 bootstrap trial; that operational state is not an
accepted governance contract.

## Revision and review rule

Every proposal has an integer revision. A material change to the decision,
constraints, alternatives, or consequences increments its revision. Reviews
name the revision they assessed. An older review does not satisfy acceptance
for a newer revision.

The review recommends; it does not decide. Important DRs normally receive one
current-revision adversarial review before acceptance. Ben may explicitly waive
a review by recording `Review status: Waived` and one non-placeholder `Waiver
reason:` line. A DR may become `Accepted` only when the current proposal has
been reviewed or explicitly waived, required evidence and proof obligations are
identified or deferred with a stated reason, canonical design links are
identified, and Ben explicitly approves it. Until then use
`Owner approval: Pending`.

Reviews are advisory memory, not audit records. A concise review states its
target DR and revision, reviewer, independence, date, recommendation,
confidence, at most five high-value issues, blockers, follow-ups, and
limitations. `Documents Consulted` is optional guidance. No exact source list,
immutable bundle, content identity, structured objection ledger, or response
status is required.

## Workflow and ownership

1. The main thread groups roughly two to five related decisions or talking
   points into one discussion batch and finishes the discussion with Ben.
2. Luna applies non-trivial document edits, evidence gathering, and bounded
   mechanical work supported by that settled discussion.
3. The main thread inspects and integrates the batch, then commits it and starts
   one fresh adversarial review of the exact edit batch in the next round.
4. Independent research for the next batch may proceed concurrently when
   dependencies permit. The main thread returns concise findings with the next
   researched batch.
5. Decision-bearing findings are not auto-fixed and the process does not run a
   review-until-clean loop. Mechanical defects faithful to settled intent may
   be corrected; a new scope, trade-off, or authority choice returns to Ben.
6. Ben accepts, rejects, withdraws, requests another revision, or leaves the DR
   Proposed with a named blocker.

Use the [decision record template](decision-record-template.md), the
[review template](reviews/adversarial-review-template.md), and, when useful,
the [fresh-reread preamble](reviews/fresh-reread-preamble.md). Preserve earlier
revisions and reviews as historical reasoning.

The main `gpt-5.6-sol` thread owns human discussion, decomposition, synthesis,
integration, validation, Git and pull-request operations, review orchestration,
external side effects, and the final repository recommendation. It does not
delegate product or architecture decisions. Luna is preferred for non-trivial
document edits, evidence gathering, mechanical work, and bounded technical
audits. Fresh Sol-medium reviewers are the default for foundational adversarial
review; Luna-xhigh is suitable for narrow convergence and implementation
review. Sol above medium requires explicit Ben approval, and Luna max remains
subject to its admission gate.

## Independence

When practical, the adversarial reviewer should use a fresh context, separate
agent/model, or external domain expert rather than the reasoning context that
authored the proposal. The review must state its independence and limitations.

## Naming

- Decision record: `DR-NNNN-short-title.md`
- Review: `DR-NNNN-rev-RR-review-NN.md`

Numbers are never reused. `Scope` is required in every DR and its registry row.

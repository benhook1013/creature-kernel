# Project status

Status date: 2026-08-08

## Phase

Foundation and round-based adversarial design.

## Current outcome

The foundation scaffold and Round 3 proposal edits are integrated. DR-0001
Revision 4 and DR-0005 Revision 1 are Proposed with Review Complete and Ben's
owner disposition pending. Round 3 is integrated as Proposed: DR-0002 Revision
2, DR-0004 Revision 2, and DR-0006 Revision 1 are all Review Pending. No DR is
Accepted. Product and architecture prose remains proposed or provisional until
the relevant proposal has Ben's explicit disposition.

## Current round

- Round 0: completed — foundation scaffold integrated and repository safeguards
  established.
- Round 1: active/proposed — DR-0001 Revision 4 is Proposed with Review
  Complete. Its fresh review recommends Accept with High confidence and found
  no blockers; lightweight Git-based batch reconstruction, duplicated
  model-routing guidance, and the removed validator unit-test suite remain
  visible non-blocking risks. The Revision 2 and Revision 3 reviews remain
  historical; their findings are preserved and are not being resolved or
  re-reviewed in this batch. Later source, runtime, and automation proposals
  were deferred to subsequent rounds.
- Round 2: active/proposed — DR-0005 Revision 1 records the four proposed
  product-identity choices and is Proposed with Review Complete. Its fresh
  review recommends Accept with Medium confidence and found no blockers;
  abstraction, downstream usability, stress-case generalization, upstream
  detail constraints, and README wording risks remain visible or deferred. It
  does not accept or settle DR-0002, DR-0003, or DR-0004.
- Round 3: active/proposed — the source-set/resolved-graph, semantic/artifact
  identity, specialized-derivation, and shared-operation proposal boundaries
  are integrated. DR-0002 Revision 2, DR-0004 Revision 2, and DR-0006 Revision
  1 are Proposed and Review Pending.
- Review lane: one fresh adversarial review of the integrated Round 3 batch is
  next. No review-until-clean loop is implied; findings return to Ben and the
  main thread for disposition.
- Next research in parallel: Round 4 compile/runtime boundary research remains
  next and provisional; DR-0003 is still Proposed and no DR is Accepted.

## Active work

- Keep DR-0001 Revision 4 and DR-0005 Revision 1 Proposed pending Ben's owner
  disposition after their completed reviews.
- Prepare one fresh adversarial review of the integrated Round 3 proposal batch
  covering DR-0002 Revision 2, DR-0004 Revision 2, and DR-0006 Revision 1.
- Begin Round 4 compile/runtime boundary research in parallel, keeping it
  provisional and separate from the pending Round 3 review.
- Preserve historical review responses and keep later proof, morphology,
  geometry, runtime, and implementation topics in their provisional rounds.
- Keep the neutral registry, authority indexes, workflow, and validator
  operational while acceptance remains pending.

## Proposed decisions and review state

- [DR-0001](../decisions/DR-0001-documentation-authority-and-review-process.md):
  documentation authority and decision-record process — Revision 4, Governance
  scope; Proposed and Review Complete, Accept recommendation with High
  confidence, no blockers, owner disposition pending.
- [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md):
  authoritative semantic source set and resolved body graph — Revision 2,
  Specification and architecture scope; Proposed and Pending review.
- [DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md):
  real-time-first compiled avatar boundary — Revision 1, Product and
  architecture scope; Proposed and Pending review.
- [DR-0004](../decisions/DR-0004-external-automation-through-cli-and-api.md):
  shared deterministic domain operations for external automation — Revision 2,
  Product and architecture scope; Proposed and Pending review.
- [DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md):
  initial product boundary and reference workflow — Revision 1, Product and
  architecture scope; Proposed and Review Complete, Accept recommendation with
  Medium confidence, no blockers, owner disposition pending.
- [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md):
  durable semantic and artifact/build identity — Revision 1, Specification and
  architecture scope; Proposed and Pending review.

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Provisional structure and validator integrated; review complete; Ben's disposition pending |
| Decision-record and review workflow | partial | unverified | DR-0001 Revision 4 and DR-0005 Revision 1 Proposed with completed reviews; Round 3 review pending; no acceptance completed |
| Research/experiment workflow | partial | unverified | Templates exist; no experiment registered |
| Body specification | design-unresolved | not-applicable | Contract boundary remains proposed |
| Creature compiler | not-implemented | not-applicable | No language or backend selected |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

- Record Ben's explicit disposition after the review responses; both DRs remain
  Proposed until then.
- Run one fresh adversarial review of the integrated Round 3 proposal batch.
- Start the provisional Round 4 compile/runtime boundary research in parallel.
- Prepare the evidence plan for the initial surface-generation choice.

## Explicitly not started

- Implementation packages.
- Large asset or dataset storage.
- External mesh conformance.
- Production distribution, operations, or release automation.

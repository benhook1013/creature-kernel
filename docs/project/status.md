# Project status

Status date: 2026-08-09

## Phase

Foundation and round-based adversarial design.

## Current outcome

The foundation scaffold and Round 3 proposal edits are integrated. DR-0001
Revision 4 and DR-0005 Revision 1 are Proposed with Review Complete and Ben's
owner disposition pending. Round 3 remains integrated as Proposed: DR-0002
Revision 2, DR-0004 Revision 2, and DR-0006 Revision 1 are all Review Complete,
with fresh Accept recommendations at Medium confidence and no decision
blockers. The DR-0004 review found one mechanical system-overview diagram
ordering defect; the diagram was corrected without changing the decision or
architecture prose. Round 4 is integrated as Proposed: DR-0003 Revision 2 has
Review Complete with an Accept recommendation at Medium confidence and no
blockers; Ben's owner disposition remains pending. Round 5 is integrated as
Proposed: DR-0007 Revision 1 records the three-stage first-proof charter and
DR-0008 Revision 1 records the bounded digitigrade family, fixed fixture
envelope, and minimal Stage 1 embodiment hooks; the Round 5 review is Complete
with Revise recommendations at High confidence and three unresolved blocking
issues. Round 6 surface-research evidence is prepared for human discussion. No
DR is Accepted. Product and architecture prose remains proposed or provisional
until the relevant proposal has Ben's explicit disposition.

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
  1 are Proposed with Review Complete, Accept recommendations at Medium
  confidence, and no decision blockers; owner dispositions remain pending.
- Review lane: the fresh adversarial review of the integrated Round 3 batch is
  complete. The one mechanical diagram-ordering defect was corrected; no
  decision change or review-until-clean loop is implied.
- Round 4: integrated/proposed — DR-0003 Revision 2 records the settled
  compile/runtime boundary: Option 2 time domain, Option 3 hybrid runtime
  representation, compatible in-place parameters versus recompilation for
  structural changes, blocking authoring reload initially with async hot swap
  later, bounded capability tiers/fallbacks, and scoped determinism. Its fresh
  adversarial review is Complete with an Accept recommendation at Medium
  confidence and no blockers; owner disposition remains pending.
- Round 5: integrated/proposed — DR-0007 Revision 1 and DR-0008 Revision 1
  record the settled first-proof stages, morphology envelope, fixed fixtures,
  and minimal Stage 1 embodiment hooks; both remain Proposed with Review
  Complete, Revise recommendations at High confidence, and three unresolved
  blocking issues. No DR is Accepted.
- Round 6: discussion prepared/provisional — surface-generation research is
  available for human discussion; the geometry decision remains unresolved.

## Active work

- Keep DR-0001 Revision 4 and DR-0005 Revision 1 Proposed pending Ben's owner
  disposition after their completed reviews.
- Preserve the completed Round 3 review responses and obtain owner dispositions
  for DR-0002 Revision 2, DR-0004 Revision 2, and DR-0006 Revision 1.
- Obtain Ben's owner disposition for the completed DR-0003 Revision 2 review
  and the Round 5 proposals, while keeping all of them provisional and separate
  from acceptance; resolve the three Round 5 blockers before accepting either
  Round 5 DR.
- Discuss the prepared Round 6 surface-generation research against the fixed
  qualitative fixture envelope and the separate visual-evaluation protocol.
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
  Specification and architecture scope; Proposed and Review Complete, Accept
  recommendation with Medium confidence, no decision blockers, owner
  disposition pending.
- [DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md):
  compiled avatar and bounded real-time execution — Revision 2, Product and
  architecture scope; Proposed and Pending one fresh review.
- [DR-0004](../decisions/DR-0004-external-automation-through-cli-and-api.md):
  shared deterministic domain operations for external automation — Revision 2,
  Product and architecture scope; Proposed and Review Complete, Accept
  recommendation with Medium confidence, no decision blockers, owner
  disposition pending.
- [DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md):
  initial product boundary and reference workflow — Revision 1, Product and
  architecture scope; Proposed and Review Complete, Accept recommendation with
  Medium confidence, no blockers, owner disposition pending.
- [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md):
  durable semantic and artifact/build identity — Revision 1, Specification and
  architecture scope; Proposed and Review Complete, Accept recommendation with
  Medium confidence, no decision blockers, owner disposition pending.
- [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md): staged
  first-proof charter and claim boundaries — Revision 1, Product scope;
  Proposed and Review Complete, Revise recommendation at High confidence, with
  three unresolved blocking issues; owner disposition pending.
- [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md):
  first digitigrade morphology and Stage 1 embodiment envelope — Revision 1,
  Product, Specification and architecture scope; Proposed and Review Complete,
  Revise recommendation at High confidence, with three unresolved blocking
  issues; owner disposition pending.

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Provisional structure and validator integrated; review complete; Ben's disposition pending |
| Decision-record and review workflow | partial | unverified | DR-0001 Revision 4, DR-0005 Revision 1, the Round 3 proposals, DR-0003 Revision 2, DR-0007 Revision 1, and DR-0008 Revision 1 have completed reviews; no acceptance completed |
| Research/experiment workflow | partial | unverified | Templates exist; no experiment registered |
| Body specification | design-unresolved | not-applicable | Contract boundary remains proposed |
| Creature compiler | not-implemented | not-applicable | No language or backend selected |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

- Record Ben's explicit disposition after the review responses; all Round 3 and
  Round 4 DRs remain Proposed until then.
- Resolve the three blocking findings from the completed Round 5 review and
  obtain Ben's explicit dispositions for DR-0007, DR-0008, and the completed
  DR-0003 review.
- Discuss Round 6 surface research using the fixed fixture envelope and
  visual-evaluation evidence plan.
- Prepare the evidence plan for the initial surface-generation choice.

## Explicitly not started

- Implementation packages.
- Large asset or dataset storage.
- External mesh conformance.
- Production distribution, operations, or release automation.

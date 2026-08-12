# Product documentation

Status: Proposed product authority

This directory owns Creature Kernel's intended outcomes, scope, users, and
externally observable requirements. It must not embed implementation choices
unless the choice itself is a product constraint.

## Documents

- [Vision and scope](vision-and-scope.md)
- [Requirements](requirements.md)
- [Users and workflows](users-and-workflows.md)
- Batch 11 focused contract owners: [semantic-address](../../spec/semantic-address/README.md),
  [canonical-data](../../spec/canonical-data/README.md),
  [numeric-frame-profile](../../spec/numeric-frame-profile/README.md), and
  [diagnostics](../../spec/diagnostics/README.md).

Product documents outrank architecture when defining what the project is trying
to accomplish. Architecture determines how to satisfy those outcomes and must
surface conflicts rather than quietly weakening them. The current product
content is a proposed, assistant-synthesized baseline pending governance and
product review; it is not an accepted project contract.

The four Round 2 initial-boundary choices are recorded in
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md):
engine-independent compiler/runtime identity, the developer/researcher-first
workflow, stylized furry and adult-interaction stress cases with general
mechanisms, and native generation before external-mesh conformance. They remain
proposals recorded under DR-0005.

Related Proposed boundaries are recorded in [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md),
[DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
The canonical specification owners are the [body-document](../../spec/body-document/README.md),
[body-graph](../../spec/body-graph/README.md), [build-operation](../../spec/build-operation/README.md),
and [fixture-manifest](../../spec/fixture-manifest/README.md) contracts.

Prior CK-KICK-012 revisions and review artifacts remain preserved as historical
evidence. Ben's Batch 5, Batch 8, Batch 9, Batch 10, Batch 11, and Batch 12
resolutions are discussion-approved and incorporated here as Proposed product
outcomes only. DR-0002 Revision 11 and DR-0008 Revision 11 remain Proposed
with Owner approval Pending and Review Complete. DR-0006 Revision 8 remains
Proposed with Owner approval Pending and Review Complete, with unresolved C1,
C3, and C4 contract findings retained for the next Ben discussion. The three
materially revised records are now DR-0011 Revision 11, DR-0012 Revision 10,
and DR-0013 Revision 8; each remains Proposed with Owner approval Pending and
Review Pending. The Batch 11 review artifacts targeted commit
`053dba58fd344ed636420e0974cf617862fe265f` and are stale only for those three
revised records. Review evidence is not acceptance; no implementation or
readiness gate activates.
Recommendations and the next discussion are summarized in the [current review
state](../project/status.md#current-review-and-future-activation-obligations).
The cross-cutting proposal is [DR-0012:
initial body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
This documentation records intended product outcomes; exact syntax details,
machine schema, exact numeric bounds, and implementation mechanisms remain
deferred to their owning specifications and architecture work. Batch 11 and
Batch 12 propose typed machine addresses with separate display names, a
right-handed metre semantic basis with +Y up and +Z creature-forward, finite
binary64 numeric semantics with correctly rounded decimal admission,
canonical quaternion handling, typed comparison profiles with deterministic
all-pairs claim evaluation, project canonical JSON with domain-separated
SHA-256 digests, and a small versioned diagnostic registry. Batch 12 also
proposes the preregistered independent-oracle, held-out/adversarial corpus,
conditioning, metamorphic, and compiler-mode evidence needed before numeric
activation. Host-adapter conformance remains deferred until adapter activation.
These are Proposed consequences only and do not activate implementation or
readiness gates.

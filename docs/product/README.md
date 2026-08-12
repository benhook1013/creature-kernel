# Product documentation

Status: Proposed product authority

This directory owns Creature Kernel's intended outcomes, scope, users, and
externally observable requirements. It must not embed implementation choices
unless the choice itself is a product constraint.

## Documents

- [Vision and scope](vision-and-scope.md)
- [Requirements](requirements.md)
- [Users and workflows](users-and-workflows.md)

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

Prior CK-KICK-012 revisions and review artifacts remain preserved as historical
evidence. Ben's Batch 5, Batch 8, and Batch 9 resolutions are discussion-
approved and incorporated here as Proposed product outcomes only. The current
six-record set is DR-0002 Revision 11, DR-0006 Revision 5, DR-0008 Revision 11,
DR-0011 Revision 7, DR-0012 Revision 6, and DR-0013 Revision 4. All six remain
Proposed with Owner approval Pending and Review Complete. The completed Batch 9
Double review targeted commit `6cf17270fda2827756c24a8d0fb301bef358f98f`;
Review Complete is evidence, not a clean review or acceptance. Its actionable
findings await Ben discussion; no implementation or readiness gate activates.
Recommendations and the next discussion are summarized in the [current review
state](../project/status.md#current-review-and-future-activation-obligations).
The cross-cutting proposal is [DR-0012:
initial body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
This documentation records intended product outcomes; exact syntax details,
machine schema, phase/code serialization, numeric budgets, and implementation
mechanisms remain deferred to their owning specifications and architecture
work.

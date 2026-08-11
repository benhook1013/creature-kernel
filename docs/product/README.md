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

Related Proposed boundaries are recorded in [DR-0002 Revision 5](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md),
[DR-0006 Revision 4](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008 Revision 5](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011 Revision 1](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).

These four CK-KICK-012-related records remain Proposed with Owner approval
Pending and Review Pending until their current revisions receive the required
Double review. This documentation records intended product outcomes; exact
syntax, schema, phase names/codes, and implementation mechanisms remain
deferred to their owning specification and architecture work.

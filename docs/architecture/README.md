# Architecture documentation

Status: Provisional architecture baseline

This directory owns Creature Kernel's target technical boundaries, data flow,
invariants, and component responsibilities. Normative serialized formats and
semantic vocabularies belong in [`spec/`](../../spec/).

## Documents

- [System overview](system-overview.md)
- [Execution model](execution-model.md)
- [Component responsibilities](component-responsibilities.md)
- [Repository structure](repository-structure.md)
- [Decision records](../decisions/README.md)

## Architectural authority

- Product requirements define the outcomes architecture must satisfy.
- Specifications define the contracts architecture consumes and produces.
- Architecture defines target responsibilities and invariants.
- Decision records explain consequential choices and identify canonical documents
  to update.
- Research and experiments provide evidence but are not automatically normative.
- Implementation may lag architecture; project tracking must report that gap.

Architecture documents must label unresolved areas rather than presenting a
plausible proposal as an accepted contract. The current content is a proposed,
assistant-synthesized target pending review; it is not an accepted architecture
baseline.

The Round 2 product-boundary proposal in
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md)
keeps Creature Kernel's initial target engine-independent and downstream of a
real-time game integration. Related Proposed source, operation, and identity
boundaries are recorded in [DR-0002 Revision 2](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md),
and [DR-0006 Revision 1](../decisions/DR-0006-durable-semantic-and-artifact-identity.md).
Those records do not settle physical formats or identity syntax. The related
Proposed compile/runtime boundary is recorded in
[DR-0003 Revision 2](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)
and described in the execution model; exact interface schemas, compatibility,
budgets, and runtime mutation details remain open.

Round 6 records two Proposed Stage 1 experiment hypotheses in
[DR-0009 Revision 4](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
and [DR-0010 Revision 4](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md).
Revision 4 incorporates the approved evidence classification, strict
comparative precedence, fairness and interaction-registration controls, and
the separate mandatory visual floor for DR-0009. It also incorporates the
canonical non-negative semantic-lineage distribution and independent oracle
coverage for DR-0010. Both remain Proposed with Owner approval Pending and
Review Pending; their Revision 3 Double reviews are historical and stale after
the material revision, and the approved findings await new review. The
[first surface experiment design](../research/first-surface-experiment-design.md)
remains a neutral Proposed, manually maintained evidence plan; it does not
register EXP-0001 or create evidence. These materials guide falsifiable
evidence only; none settles permanent surface architecture, animation-ready
topology, runtime field representation, implementation language, or a geometry
backend.

## Current maturity

The architecture is pre-implementation. Component names describe provisional
responsibility boundaries, not approved packages, processes, repositories, or
technologies.

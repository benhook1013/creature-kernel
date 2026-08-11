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
- [Proposed body-document contract](../../spec/body-document/README.md)
- [Proposed body-graph contract](../../spec/body-graph/README.md)
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
boundaries are recorded in [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md),
and [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md).
Those records now settle the minimum inspectable, non-authoritative graph
boundary, structured semantic-address identity, ownership/relation separation,
and result-envelope boundary, while deferring physical formats, schema
technology, identity serialization syntax, and identity lifecycle/remap rules.
The related
Proposed compile/runtime boundary is recorded in
[DR-0003 Revision 2](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)
and described in the execution model; exact interface schemas, compatibility,
budgets, and runtime mutation details remain open. The typed semantic
vocabulary, measurement ownership, and frame-conversion boundary are Proposed
in [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
CK-KICK-012 Batch 6 resolutions are discussion-approved and are reflected in
the canonical specifications as Proposed material. The current CK-KICK-012
Batch 6 Double review is Complete. DR-0002 Revision 8, DR-0008 Revision 8,
DR-0011 Revision 4, and DR-0012 Revision 3 remain Proposed with Owner
approval Pending and Review Complete. Seven findings are pending Ben
discussion and owner disposition; see the [decision registry](../decisions/registry.md).
The CK-KICK-012 Batch 5
review at commit `a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical
evidence; no clean review or acceptance is implied.
DR-0006 remains Proposed with its current revision's review evidence. The
cross-cutting proposal is [DR-0012: initial body-document encoding, resolution,
and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The body-document and body-graph proposals are the canonical specification
owners; this architecture layer records only their target boundaries and
consumers, including explicit Part containment, relation-independent graph
validation, Attachment composition, and canonical local frame handoff.

The [first surface experiment design](../research/first-surface-experiment-design.md)
and its linked [DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
and [DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
are parked, Proposed confirmatory-research material. They are non-blocking and
do not settle permanent surface architecture, animation-ready topology,
runtime field representation, or a geometry backend; CK-KICK-013 separately
tracks the Proposed implementation-platform direction.
Their detailed records and reviews remain preserved evidence; no Revision 9,
owner disposition, or additional review is active. They may be reactivated when
at least two runnable candidate surface implementations exist and a comparative
outcome is intended to justify production architecture, or when Ben explicitly
reactivates them. Until then, exploratory prototypes may produce observations
but may not claim formal DR-0009/0010 support or reject.

The CK-KICK-013 platform proposal is also discussion-approved as Proposed
material, not an accepted implementation decision. Proposed DR-0013 Revision 1
has Owner approval Pending and Review Complete; its findings are pending Ben
discussion and owner disposition. It describes a
stable Rust production semantic/compiler core in a Cargo workspace: an
engine-independent Rust compiler library, a thin CLI, and a replaceable
geometry boundary, with no initial daemon or service. Stage 1 would use an
in-process Rust CPU dense-field evaluator/extractor. If measured required
capability or performance is missing, an isolated C++ worker/backend is the
first escape hatch; in-process C ABI/FFI is considered only if that worker is
proven insufficient. This is not a Rust-only-forever promise or an advanced
Rust-geometry maturity claim. Python remains suitable for disposable
experiments, evidence/render tooling, and the visual workbench, but is not a
production compiler dependency. The initial reproducible workbench target is
Linux x86_64 under WSL or native Linux; portability is preserved while native
Windows and host-engine targets are deferred. The compiler writes ordinary
versioned artifacts plus a manifest, and an independent visual workbench
consumes filesystem artifacts; this does not settle final avatar-package
serialization or compatibility. Performance claims require a reproducible
benchmark and hardware profile. The language/build acceptance trigger remains
unsatisfied, so no implementation package is activated.

## Current maturity

The architecture is pre-implementation. Component names describe provisional
responsibility boundaries, not approved packages, processes, repositories, or
technologies.

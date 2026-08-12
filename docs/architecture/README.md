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
- [Proposed fixture-manifest and admission contract](../../spec/fixture-manifest/README.md)
- [Proposed build-operation contract](../../spec/build-operation/README.md)
- [Proposed semantic-address contract](../../spec/semantic-address/README.md)
- [Proposed canonical-data contract](../../spec/canonical-data/README.md)
- [Proposed numeric-frame-profile contract](../../spec/numeric-frame-profile/README.md)
- [Proposed diagnostics contract](../../spec/diagnostics/README.md)
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
CK-KICK-012 Batch 6/7/8/9/10/11/12 resolutions are discussion-approved and are
reflected in the canonical specifications as Proposed material. DR-0002
Revision 11 and DR-0008 Revision 11 remain Proposed with Owner approval Pending
and Review Complete. DR-0006 Revision 8 remains Proposed with Owner approval
Pending and Review Complete; unresolved C1/C3/C4 contract findings remain.
DR-0011 Revision 11, DR-0012 Revision 10, and DR-0013 Revision 8 remain
Proposed with Owner approval Pending and Review Pending after the Batch 12
numeric-resolution update. The fresh Batch 11 Double review targeted commit
`053dba58fd344ed636420e0974cf617862fe265f`; its artifacts are stale only for
those three materially revised records. The completed Batch 9 Double review targeted commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`; its evidence is stale for the
revised records and is not acceptance. No implementation or readiness gate
activates. See
the [current review state](../project/status.md#current-review-and-future-activation-obligations)
for the two review lenses, recommendations, and findings. Earlier review
evidence remains stale. See the
[decision registry](../decisions/registry.md). The CK-KICK-012 Batch 5 review
at commit `a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical
evidence; no clean review or acceptance is implied.
The cross-cutting proposal is [DR-0012: initial body-document encoding, resolution,
and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The body-document, body-graph, and fixture-manifest proposals are the canonical
specification owners; this architecture layer records only their target
boundaries and consumers, including explicit Part containment,
relation-independent graph validation, Attachment composition, canonical local
frame handoff, and immutable fixture admission. The
[build-operation contract](../../spec/build-operation/README.md) is the
canonical Proposed owner for the public derived-output, artifact lifecycle,
publication, collision, and inspection boundary; this layer records only its
component responsibilities and data-flow consequences.

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
material, not an accepted implementation decision. Proposed DR-0013 Revision 8
has Owner approval Pending and Review Pending after the Batch 12 numeric
resolution. The completed
Batch 9 Double review targeted commit `6cf17270fda2827756c24a8d0fb301bef358f98f`;
its evidence is stale for the revised record and is not acceptance. No
implementation or readiness gate activates.
See the [current review state](../project/status.md#current-review-and-future-activation-obligations)
for recommendations and findings. The
four readiness stages are: DR-0013
acceptance activates only the empty Cargo shell; a versioned, preflighted
fixture manifest, its listed fixture files, the exact schema, and
parser/bootstrap must be admitted together in one review-branch activation
transaction; canonical numeric/frame rules plus frozen expected graph outputs
activate semantic resolution and in-memory snapshot handoff; and a working
resolver plus provisional geometry profile and project-owned seam activates
exploratory Stage 1 geometry. It describes a stable Rust
production semantic/compiler core, a thin CLI, and a project-owned versioned,
backend-neutral GeometryRequest/GeometryResult seam, with no initial daemon or
service. Stage 1 would use an in-process Rust CPU dense-field evaluator/
extractor. If measured capability/performance or a justified isolation,
security, portability, or licensing need exposes a gap, evaluate an isolated
C++ worker/backend first; in-process C ABI/FFI is considered only if that
worker is proven insufficient. Python remains for disposable experiments,
evidence/render tooling, and the visual workbench, not production compiler
execution. Complete success outputs use one authoritative build
envelope across geometry and publication, immutable build-scoped sibling
staging, manifest-last atomic no-replace publication, and manifest validation
of build/artifact identity, relative paths, hashes, and sizes; trusted
derived-output/publication failure is `output-failure`; failed operations
initially return the authoritative envelope without a persisted failure bundle;
consumers reject
symlinked, unlisted, incomplete, mixed-build, and stale bundles. Future workers
must negotiate protocol/version, obey bounded time/resources, map crash/timeout/
resource outcomes, validate outputs, and leave the compiler surviving failure.
Exact serialization remains deferred. The first reproducible path is a
WSL2 x86_64 GNU environment, with later native-Linux portability
smoke; record rust-toolchain.toml, Cargo.lock, target/profile/rustc -Vv and
reference metadata, and perform lightweight license/unsafe/native/portability/
security dependency review without Git pinning or audit bureaucracy.

Batch 10 adds the initial filesystem profile (tested WSL `/home` only),
process-crash-safe namespace publication without a sudden-power-loss claim, a
profile-defined unambiguous safe-ASCII candidate path mapping, and a separate
inspection read operation with closed non-success statuses. Producer/output
trust is separate from coordinator/reporter/publisher trust; a trusted parent
may report only its own observed worker failure in the authoritative envelope
and cannot adopt output after worker trust loss. The [fixture-manifest
contract](../../spec/fixture-manifest/README.md) owns the manifest payload and
separate readiness/decision content-identity binding, successor history, and
Readiness 2/3 corpus admission.

Batch 11 and Batch 12's derived architectural consequences are: typed
restricted-ASCII machine addresses with separate Unicode display names; a
right-handed metre semantic basis (+Y up, +Z creature-forward) with adapter
conversion; finite binary64 values with correctly rounded decimal admission
and canonical quaternion handling with exact bounds pending evidence;
fixed-order operations with an initial no-reassociation/no-implicit-FMA/
no-FTZ/no-DAZ direction; typed comparison profiles with deterministic all-pairs
claim evaluation and a separate Readiness 3 snapshot transaction; restricted
canonical JSON and domain-separated SHA-256 identity; and a small versioned
diagnostic registry. The planned numeric experiment now preregisters intended
domains, separate semantic error budgets, independent exact/higher-precision
oracles, frozen development/held-out/adversarial corpora, condition estimates,
metamorphic checks, and a validation margin whose formula/constant remain open.
Adapter conformance remains deferred until adapter activation. These remain
Proposed consequences and do not activate packages, schemas, fixtures, or
resolver work.

## Current maturity

The architecture is pre-implementation. Component names describe provisional
responsibility boundaries, not approved packages, processes, repositories, or
technologies.

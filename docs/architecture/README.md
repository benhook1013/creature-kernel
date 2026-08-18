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
real-time game integration. The accepted semantic-foundation source and
identity directions are recorded in
[DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md)
and [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md);
the related operation boundary remains Proposed under
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md).
Those records now settle the minimum inspectable, non-authoritative graph
boundary, structured semantic-address identity, ownership/relation separation,
and result-envelope boundary, while deferring physical formats, schema
technology, identity serialization syntax, and identity lifecycle/remap rules.
The related Proposed compile/runtime boundary is recorded in
[DR-0003 Revision 2](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)
and described in the execution model; exact interface schemas, compatibility,
budgets, and runtime mutation details remain open. The typed semantic
vocabulary, measurement ownership, and frame-conversion direction is an accepted
semantic-foundation direction under
[DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md);
concrete profiles, schemas, and activation bindings remain Proposed or gated.
CK-KICK-012 Batch 6/7/8/9/10/11/12/13 resolutions are discussion-approved and are
reflected in the canonical specifications as Proposed material. DR-0002
Revision 11, DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14
are accepted semantic-foundation directions with Owner approval Approved by Ben
and Review Complete, decided 2026-08-17; their concrete architecture,
specification, profile, and activation consequences remain Proposed or gated.
DR-0008 Revision 14 remains Proposed with Owner approval Pending and Review
Pending after the Revision 13 Double review at exact target `117544a`; Review 01
found no findings and Review 02 recommended Revise at High confidence with
three taxonomy findings, dispositioned in Revision 14. Its Revision 13 and
earlier artifacts remain preserved stale historical evidence.
DR-0013 Revision 12 is Accepted,
with Owner approval Approved by Ben and Review Complete at that exact target, decided
2026-08-13. Review scope is record-specific: DR-0002 Revision 11's current Double
review targeted exact commit `6cf17270fda2827756c24a8d0fb301bef358f98f`; the
current Double reviews for DR-0006 Revision 12, DR-0011 Revision 15, DR-0012
Revision 14, and DR-0013 Revision 12 targeted exact commit
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. Accepted DR-0001 Revision 5
remains the operative governance baseline while DR-0001 Revision 6 is Proposed
transition guidance with Ben's workflow direction approved and current review
complete; formal acceptance remains pending Ben's disposition. The reviews of
the earlier-predecessor revisions at commit
`763cff22d10f6491a05a28312a25250704543dcf` are stale exact-target evidence;
G1/G2 were fixed mechanically, T1–T3 were resolved in the successors, and
T4 remains unselected and deferred, requiring Ben's retained-human disposition
before adapter profile/schema activation; it does not block the current
preparatory Rust slices. The immediate-predecessor review at exact commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is also stale; its findings were
corrected in the current revisions. The 9c governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. Review Complete is evidence only. Readiness 1
remains active for the Cargo workspace, `creature-kernel-core` library shell,
and thin `creature-kernel` CLI shell. Readiness 2 is also active for the
admitted exact body and manifest schemas, manifest, nine fixtures, Rust
parser/bootstrap, and Python preflight/evidence. The provisional structural
address/index, validator, and `inspect-structure` command remain preparatory.
The standalone `creature_kernel_core::numeric` module is also preparatory: it
checks strict JSON-number grammar, requires caller-enforced resource limits, uses
pinned Rust 1.97.1 direct correctly-rounded binary64 final conversion, returns
typed overflow/nonzero-underflow failures, admits finite subnormals, normalizes
lexical zero to `+0`, and has focused boundary tests. It is not wired into
body-document admission and does not activate numeric semantics or Readiness 3.
The standalone `creature_kernel_core::frame` module is also preparatory: it
provides a normalized-binary64 structural transform carrier, exact signed-axis
source-basis mapping, and symbolic length-unit ratios. The public
`creature_kernel_core::source_preparation::prepare_single_source` API accepts
raw source bytes plus a sealed `ResourceProfile`, performs admission and
structural validation, then prepares the source basis and complete semantic
numeric inventory. Its maps cover part/joint/socket/attachment transforms,
landmark positions, dimensions, and named frames under stable semantic
addresses or owner/role keys; retained graph source records and context provide
semantic provenance. Raw lexical spelling/provenance is not recovered. The
internal `frame_preparation` adapter is an implementation detail and cannot
provide a public record-level admission bypass. This preparation does not
apply basis/unit values or quaternion semantics, expand dependencies/modules,
produce claims/snapshots or serialization, or activate a resolver or Readiness
3. See
the [current review state](../project/status.md#current-review-and-future-activation-obligations)
for the two review lenses, recommendations, and findings. Earlier review
evidence remains stale. See the
[decision registry](../decisions/registry.md). The CK-KICK-012 Batch 5 review
at commit `a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical
evidence; no clean review or acceptance is implied.
The cross-cutting semantic-foundation direction is [DR-0012: initial body-document encoding, resolution,
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

The CK-KICK-013 platform direction is accepted in DR-0013 Revision 12, with
Owner approval Approved by Ben and Review Complete at exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`, decided 2026-08-13. The earlier-
predecessor review at exact commit `763cff22d10f6491a05a28312a25250704543dcf`
is stale exact-target evidence; T1–T3 were resolved and T4 remains unselected and deferred, requiring
Ben's retained-human disposition before adapter profile/schema activation; it does
not block the current preparatory Rust slices. The immediate-predecessor review at exact
commit `9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in the current revisions. The 9c technical pass found no findings /
Ready for PR at High confidence; Review Complete is evidence only.
Readiness 1 remains active for the Cargo workspace, `creature-kernel-core`
library shell, and thin `creature-kernel` CLI shell. Readiness 2 is also active
for the admitted exact body and manifest schemas, manifest, nine fixtures, Rust
parser/bootstrap, and Python preflight/evidence. The provisional structural
address/index, validator, and `inspect-structure` command remain preparatory.
The standalone `creature_kernel_core::numeric` module is preparatory only: it
checks strict JSON-number grammar, uses pinned Rust 1.97.1 direct correctly-
rounded binary64 final conversion, returns typed overflow/nonzero-underflow
failures, admits finite subnormals, normalizes lexical zero to `+0`, and has
focused boundary tests. It is not wired into body-document admission and does
not activate numeric semantics or Readiness 3. The standalone
`creature_kernel_core::frame` module is preparatory only and is not wired into
source admission or resolver/snapshot behavior; it does not apply unit scaling
or perform quaternion/transform algebra or comparison. The public
`source_preparation::prepare_single_source` operation accepts raw bytes and a
sealed `ResourceProfile`, admits and structurally validates one source, and
prepares its basis plus complete numeric maps for transforms, landmark
positions, dimensions, and named frames. Stable address/owner-role keys and
component locations provide semantic provenance; raw lexical spelling is not
recovered. The internal `frame_preparation` adapter cannot bypass record-level
admission. No dependency/module expansion, basis/unit application, quaternion
semantics, claims/snapshots/serialization, resolver, or Readiness 3 activation
exists.
See the [current review state](../project/status.md#current-review-and-future-activation-obligations)
for recommendations and findings. The
four readiness stages are: DR-0013 acceptance activated Readiness 1 for the
Cargo workspace, compiler/core library shell, and thin CLI shell; the
versioned, preflighted fixture manifest, its listed fixture files, exact
schema, and parser/bootstrap are the admitted and active Readiness 2
transaction; canonical numeric/frame rules plus frozen expected graph outputs
activate semantic resolution and in-memory snapshot handoff in a distinct
Readiness 3 transaction; and a working resolver plus provisional geometry
profile and project-owned seam activates exploratory Stage 1 geometry. It
describes a stable Rust
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

Batch 13's derived architectural consequences preserve the typed restricted-
ASCII machine-address, canonical-data, and diagnostic owners, and add a
deterministic comparator boundary: same-target claims normalize into one
canonical local-to-parent frame, translations compare directly, rotations use
q/-q, scalar predicates use exact bounded dyadic arithmetic, and quaternion
comparison uses an offline-derived half-chord bound with no runtime
transcendental or norm operation. Structured source-derived claim IDs retain
all occurrences/provenance, detect same-ID collisions, evaluate valid pairs in
sorted-ID order, and select the smallest declared value tuple; local claim
identity remains separate from generic graph collection keys. The proposed
normalization path fixes max-absolute scaling, component order, left-to-right
square accumulation, correctly rounded square root, sign canonicalization,
and floating-point environment controls, while near-zero/drift thresholds,
ranges, constants, validation margin/error formula, and implementation
bindings remain evidence-gated. The unregistered experiment covers rational and
ULP boundaries, H derivation, normalization/platform fixtures, and order/
identity cases. A future adapter uses signed permutation `C` plus positive
scale `s` (vector lengths use `sC`, scalar lengths use `s`), with
storage/output-only default and optional runtime-conformance tiers, explicit
precision/domain narrowing, and FTZ/DAZ/subnormal probes.
The diagnostic owner proposes nine domains—source-admission, dependency,
semantic-identity, graph-structure, frame-numeric, resource, execution-trust,
publication, and inspection—with one tiny mandatory bootstrap registry/profile
for unknown registry/profile negotiation; exact codes and fields remain
fixture-gated.
Readiness implementation binding remains a separate scoped content-identity
transaction from fixture payloads and expected snapshots.

These remain Proposed consequences and do not change the admitted Readiness 2
identity or activate Readiness 3 resolver/adapter work.

## Current exact-placement foundation

The current implementation contains a deliberately restricted foundation that
consumes one already prepared source: exact canonical metres in a right-handed
basis (`+Y` up, `+Z` forward), identity rotations, and bounded exact-integer
translations for Part placements plus Attachment host/mating Socket frames and
offsets. It derives reference placement by composing parent-local Part deltas
through explicit containment and verifies exact agreement between the
Attachment equation and an authored attached-root delta. Unrelated Joint and
named-frame transforms are not validated or resolved by this operation. This
is implementation evidence for a narrow primitive, not a general basis/unit/
quaternion transform system or the semantic resolver boundary. It does not
activate Readiness 3, produce geometry or surfaces, or provide a user-facing
rendered creature.

The corrected authored example now uses parent-local deltas instead of
world-looking values while retaining its intended derived reference positions.
The candidate architectural consumer directly consumes this exact-placement
result through prepared-source inspection/publication. Its browser output is a
deliberately crude deterministic point/line scaffold with Part markers,
containment links, Joint endpoint links, attachment-root distinction, semantic
labels, and front (x/y), side (z/y), and top (x/z) SVG views. Joint frame
transforms are not interpreted. This supplied the first genuine human visual
checkpoint; Ben confirmed on 2026-08-15 that the diagrams were decodable and
spatially accurate for the intended straight tail. It is not geometry/mesh/surface/volume/anatomical quality,
rigging, pose/animation, IK, deformation, physics, general transforms,
resolver activation, or runtime evidence. These statements do not accept or
revise any decision record.

## Current maturity

The target architecture remains pre-implementation beyond the active Readiness
1 shell and the admitted Readiness 2 schema/manifest/fixture/parser/bootstrap/
preflight transaction. The provisional structural address/index, validator,
inspection command, and single-source preparation API remain preparatory
implementation outside Readiness 3. The internal numeric/frame-preparation
adapters are not public admission routes and do not activate numeric
semantics. The remaining
component names describe provisional responsibility boundaries, not activated
Readiness 3 packages, processes, repositories, or technologies.

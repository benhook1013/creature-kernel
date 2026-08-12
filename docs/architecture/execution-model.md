# Execution model

Status: Provisional conceptual baseline

## Decision direction

A real-time game is the primary downstream target. Expensive invariant creature
generation compiles outside the frame loop, while a hybrid compiled package
exposes bounded runtime representations. A higher-quality cinematic path is
supplementary. This direction is Proposed for formal acceptance under
[DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md).

CK-KICK-013 is a discussion-approved but unaccepted platform proposal.
Proposed DR-0013 Revision 4 has Owner approval Pending and Review Complete. The
completed Batch 9 Double review targeted commit
`6cf17270fda2827756c24a8d0fb301bef358f`;
Review Complete is evidence, not a clean review or acceptance; actionable
findings await Ben discussion, and no implementation or readiness gate
activates. See the [current review state](../project/status.md#current-review-and-future-activation-obligations)
for recommendations and findings. Earlier review evidence is stale after this
revision. Its four
readiness stages are: acceptance activates only the empty Cargo shell; a
versioned, preflighted fixture manifest, its listed files, the exact schema, and
parser/bootstrap must be admitted together in one review-branch activation
transaction; canonical numeric/frame rules plus frozen expected graph outputs
activate semantic resolution and in-memory snapshot handoff; and a working
resolver plus provisional geometry profile and project-owned seam activates
exploratory Stage 1 geometry. Acceptance therefore does not activate
the parser, resolver, fixtures, or geometry proof. It
proposes a stable Rust production semantic/compiler core in a Cargo workspace,
exposed as an engine-independent Rust compiler library and thin CLI with a
versioned project-owned backend-neutral GeometryRequest/GeometryResult seam.
No initial daemon or service is part of this proposal. Stage 1 uses an
in-process Rust CPU dense-field evaluator/extractor. If measured capability or
performance, or a justified isolation/security/portability/licensing need,
exposes a gap, an isolated C++ worker/backend is evaluated first; in-process C
ABI/FFI is only considered if that worker is proven insufficient. This is a
bounded platform direction, not a Rust-only-forever promise or an advanced-
Rust-geometry maturity claim.

## Time domains

```text
Authoritative semantic source set
      |
      v
[1] Resolve source set and compile invariant data
      |
      v
[2] Hybrid runtime avatar package
      |
      v
[3] Bounded real-time game simulation
      |
      v
[4] Optional cinematic or offline enhancement
```

## Platform and artifact flow (Proposed)

The initial reproducible execution/workbench target is WSL2 x86_64 GNU. Record
exact `rust-toolchain.toml`, committed
`Cargo.lock`, target/profile, `rustc -Vv`, and reference-environment metadata;
perform a later native-Linux portability smoke. Native Windows and host-engine
targets are deferred. When dependencies are added, review license, unsafe or
native code, and portability/security relevance without Git commit pinning or
heavyweight audit bureaucracy. Python remains available for disposable
experiments, evidence/render tooling, and the visual workbench; it is not a
production compiler dependency.

The [build-operation contract](../../spec/build-operation/README.md) owns the
complete success/failure bundle lifecycle through one authoritative envelope:
candidate versus committed artifact identity, explicit-output-root target
derivation, immutable sibling staging, atomic no-replace publication,
idempotent success, target conflict, failure-bundle trust, and lineage-checked
inspection. An independent visual workbench consumes those artifacts rather
than becoming part of the compiler or a daemon/service. This boundary does not
settle final avatar-package serialization or compatibility.
Performance claims must be backed by a reproducible benchmark and hardware
profile. The language/build acceptance trigger remains unsatisfied, so no
implementation package is activated. Any future worker must negotiate protocol/
version compatibility, obey bounded time/resource budgets, map crash/timeout/
resource outcomes, validate outputs before publication, and leave the compiler
surviving worker failure; exact worker serialization remains deferred.

## Creature compilation

Resolution and compilation may run in an external tool, preview/authoring
session, loading screen, background worker, or import step. Expensive invariant
generation is not frame-loop work. Candidate work includes:

- resolving and validating the source set into a per-build semantic body graph
  snapshot;
- combining body volumes and extracting a surface;
- remeshing, simplifying, and generating LODs;
- generating skeletons, skinning, collision, and distance fields;
- constructing deformation cages and regional simulation meshes;
- binding simulation output to render surfaces;
- generating material attributes, GPU resources, and other conventional prepared
  runtime assets;
- running pose, geometry, collision, and capability tests.

The result is a derived hybrid runtime avatar package with separate artifact/build
identity and provenance. It combines conventional mesh, LOD, rig, collision,
material, and prepared deformation assets with selected semantic fields, cages,
signed-distance data, and regional simulation data. It is neither fully live
implicit generation by default nor semantics-free conventional assets.

### Source admission and semantic resolution

The initial source path accepts one strict UTF-8 JSON document. Duplicate keys,
comments, includes, and evaluation are rejected. Structural validation uses
the proposed JSON Schema Draft 2020-12 vocabulary; CK semantic resolution then
owns the resolved body graph. Source text, the normalized admission model, and
the resolved success snapshot are separate representations. Exact semantic
contract family and revision recognition is required; migration is explicit
and creates a new source. Unknown core members fail. An unsupported required
extension is unsupported, while an unsupported optional namespaced extension
is preserved opaquely and has no core semantic effect.

The resolver runs the following ordered phases inside one operation-result
envelope:

1. resource and input admission;
2. syntax, structural-schema, and contract recognition;
3. dependency admission and exact-revision checks;
4. namespaces, identity, and references;
5. ownership and typed relations;
6. unit/frame normalization and value derivation;
7. semantic invariants; and
8. in-memory resolved-snapshot finalization and handoff.

Fatal failure blocks dependent phases, but independent diagnostics within one
phase accumulate in deterministic order. Complete acquisition is required
before invalid-source. Internal trust loss takes precedence, then a qualifying
resource-limit, then the earliest applicable phase unable to produce its
required output. In a mixed dependency phase, dependency-failure precedes
invalid-source and then unsupported; parse/semantic invalid-source precedes
unsupported. All mandatory independent checks capable of changing status or
primary run unless resource/trust interruption prevents them. Processing is
complete when all applicable work establishing/trusting the selected outcome
ran; blocked phases are inapplicable. Diagnostic completeness is complete when
all applicable profile-required diagnostics were retained; ordinary truncation
is not resource-limit when processing/trust continue, and optional checks
cannot change status or primary. The primary is the first diagnostic
establishing the final status under that ordering, and reserved diagnostic
capacity preserves it (or reserves the resource/truncation diagnostic when
arena exhaustion changes the final status). Provenance distinguishes authored,
defaulted, and derived values. Required unresolved or ambiguous values, and
measurement claims that conflict after normalization by owner address,
property role, and frame/context, cannot publish success. A conflict is a
semantic-invalid deterministic diagnostic; no valid-supported snapshot is
finalized. Successful `resolve` requires the in-memory snapshot; external
serialization, staging, and publication are `build` responsibilities under
the [build-operation contract](../../spec/build-operation/README.md). Resource
admission uses finite implementation-profile limits for
source and aggregate bytes; string lengths/counts; nesting depth; object/array
members; graph entities/relations; ownership depth; module/reference
expansion; extension count/payload; numeric admissibility; diagnostics; and
aggregate work and memory. Exact values and accounting remain deferred.
The profile is selected during admission, and its guards remain active through
later phases whose expansion, graph, diagnostic, work, or memory use cannot be
known before parsing.

Machine-readable diagnostic identity and order are stable contract data; human
messages are explanatory rather than compatibility keys. Semantic equivalence
compares durable identities, relations, frames, normalized values, provenance,
and outcome, not source ordering or generated topology. Semantic contract
identity remains separate from compiler/build/configuration/seed, dependency,
and artifact identities.

## Real-time simulation

The runtime may perform bounded stateful work:

- pose, animation, root motion, retargeting, motion warping, and IK;
- analytic or signed-distance contact queries and contact response;
- contact constraints, balance, and physical reaction;
- parameterized bone, morph, cage, and GPU surface deformation;
- procedural material evaluation;
- selected activated cloth, secondary motion, and regional soft-body simulation.

Resolution, solver iterations, active regions, character count, and available
hardware budget require explicit bounds. A high-end PC increases the finite
budget; it does not remove the quality ladder or fallback requirement.

## Baked and dynamic data

| Compiled | Dynamic |
| --- | --- |
| Mesh connectivity and LODs | Poses and IK targets |
| Skin weights | Contacts and forces |
| Collision fields and proxies | Constraint state |
| Deformation cages and bindings | Cage offsets and morph weights |
| Regional simulation topology | Low-resolution solver state |
| Semantic surface attributes | Interaction and material parameters |

Precomputation does not predetermine interaction. It prepares bounded numerical
representations for live use.

## Mutation categories and package lifecycle (Proposed)

Proven-compatible parameter changes may update the active package in place.
Topology changes, body-plan changes, and other major structural changes require
recompilation and validation; they are not arbitrary live gameplay edits. A
loading screen is an allowed fallback when a structural package is needed.

The initial preview/authoring workflow may block or freeze while the new
package compiles and validates. A valid replacement reloads without closing or
reopening the scene or session. If compilation or validation fails, the old
validated avatar remains active and diagnostics are reported. A later
asynchronous in-session swap may keep the old package active while compiling,
but it is not an initial requirement. Such a future swap must not promise stable
topology indices or preserve transient solver state that is incompatible with
the replacement.

## Local quality activation

```text
Distant character
    -> animation and basic IK

Nearby character
    -> contact collision and cage deformation

Actively interacting region
    -> higher-quality local deformation
    -> optional regional soft-body simulation
```

Quality may vary by character, body region, interaction, visibility, distance,
and hardware budget.

## Bounded quality ladder (Proposed)

Capability tiers and fallbacks are bounded by character, body region,
interaction, visibility, distance, and hardware. Names such as base, enhanced,
high-end, and cinematic may explain the ladder, but exact names, thresholds,
and numerical budgets are non-normative until benchmarks establish them.

## Provisional feasibility classification

This is an expectation to test, not benchmark evidence. The classes below are
conceptual examples, not normative tier names or promises.

| Feature | Expected path |
| --- | --- |
| Skeletal animation, IK, and motion warping | Real time |
| Analytic collision and distance queries | Real time |
| Morph, bone, cage, and GPU surface deformation | Real time |
| Procedural colours and markings | Real time |
| Simplified cloth and secondary motion | Real time |
| Local low-resolution soft regions | High-end real time, subject to proof |
| Several interacting soft regions | Strictly budgeted, subject to proof |
| Whole-character volumetric simulation | Difficult |
| Multiple high-resolution soft characters | Primarily offline or reduced quality |
| Surface remeshing during interaction | Background or authoring work |
| Arbitrary topology change every frame | Out of scope |
| Dense two-way soft-body self-collision | Primarily cinematic or offline |

## Offline-only failure boundary

The runtime becomes impractical if it simultaneously requires render-resolution
physics, full volumetric characters, dense two-way self-collision, arbitrary
topology mutation, dense fur and cloth collision, unbounded convergence, and no
fallback or LOD. High-end hardware increases the budget but does not remove the
need for bounds.

## Determinism boundary (Proposed)

Compilation must be reproducible from the authoritative source, compiler
version, configuration, and seed, or report why it cannot be. Bit-exact
simulation, networking, and replay determinism are deferred pending explicit
requirements, contracts, and evidence.

## Pending decisions

- Reference frame rate, resolution, and hardware.
- Compile-time budget and allowed execution locations.
- Visible, nearby, and actively interacting character counts.
- Maximum high-quality deformable regions.
- Geometry libraries/backend, any isolated worker boundary, and GPU-vendor
  requirements.
- Simulation, network, and replay determinism requirements and proof level.
- Collision ownership after visible deformation.
- Minimum fallback experience.
- Relationship between live and cinematic outputs.

# Execution model

Status: Provisional conceptual baseline

## Decision direction

A real-time game is the primary downstream target. Expensive invariant creature
generation compiles outside the frame loop, while a hybrid compiled package
exposes bounded runtime representations. A higher-quality cinematic path is
supplementary. This direction is Proposed for formal acceptance under
[DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md).

CK-KICK-013 is accepted through DR-0013 Revision 12, with Owner approval
Approved and Review Complete at exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`, decided 2026-08-13.
Accepted DR-0001 Revision 5 remains the operative
governance baseline while DR-0001 Revision 6 is Proposed transition guidance
with Ben's workflow direction approved and current review complete; formal
acceptance remains pending Ben's disposition. The reviews of the earlier
predecessor revisions at commit `763cff22d10f6491a05a28312a25250704543dcf`
are stale exact-target evidence;
G1/G2 were fixed mechanically, T1–T3 were resolved in the successor, and
T4 remains unselected and deferred, requiring Ben's retained-human disposition
before adapter profile/schema activation; it does not block the empty first Rust
slice. The immediate-predecessor review at exact commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in the current revision. The 9c technical pass found no findings /
Ready for PR at High confidence; Review Complete is evidence only. Readiness 1
remains the only active gate and its accepted scope is only the Cargo
workspace, empty `creature-kernel-core` library shell, and thin
`creature-kernel` CLI shell. The exact body and manifest schemas, manifest,
nine fixtures, Rust parser/bootstrap, and Python preflight/evidence are present
as a Proposed Readiness 2 candidate, not an admitted or active gate. No
Readiness 3 resolver, numeric semantic activation, adapter, experiment, or
Readiness 3 geometry implementation exists.
See the [current review state](../project/status.md#current-review-and-future-activation-obligations)
for recommendations and findings. Its four
readiness stages are: acceptance has activated Readiness 1, which is only the
empty Cargo shell; a
versioned, preflighted fixture manifest, its listed files, the exact schema, and
parser/bootstrap must be admitted together in one review-branch activation
transaction; canonical numeric/frame rules plus frozen expected graph outputs
activate semantic resolution and in-memory snapshot handoff; and a working
resolver plus provisional geometry profile and project-owned seam activates
exploratory Stage 1 geometry. Acceptance therefore does not admit or activate
the Readiness 2 candidate or any resolver/geometry proof. The accepted
direction uses a stable Rust production semantic/compiler core in a Cargo
workspace,
exposed as an engine-independent Rust compiler library and thin CLI with a
versioned project-owned backend-neutral GeometryRequest/GeometryResult seam.
No initial daemon or service is part of this boundary. Stage 1 uses an
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

The initial reproducible execution/workbench target is WSL2 x86_64 GNU. The
filesystem publication profile is narrower: only tested local Linux under
`/home` is supported initially; `/mnt/c`, network, removable, and unspecified
filesystems are excluded. Same-filesystem sibling staging, capability probe,
atomic no-replace, immutable committed outputs, cooperating builders, and
post-collision inspection provide process-crash-safe namespace publication, not
sudden-power-loss durability. The exact safe-ASCII candidate path mapping is an
activation prerequisite. Malicious or privileged concurrent mutation is outside
scope, but inspection verifies complete output or rejects it. Record
exact `rust-toolchain.toml`, committed
`Cargo.lock`, target/profile, `rustc -Vv`, and reference-environment metadata;
perform a later native-Linux portability smoke. Native Windows and host-engine
targets are deferred. When dependencies are added, review license, unsafe or
native code, and portability/security relevance without Git commit pinning or
heavyweight audit bureaucracy. Python remains available for disposable
experiments, evidence/render tooling, and the visual workbench; it is not a
production compiler dependency.

The [build-operation contract](../../spec/build-operation/README.md) owns the
complete success-output lifecycle through one authoritative envelope:
candidate versus committed artifact identity, explicit-output-root target
derivation, immutable sibling staging, atomic no-replace publication,
idempotent success, worker trust, and lineage-checked inspection. Failed
operations initially return the authoritative envelope and do not persist a
diagnostics-only failure bundle. An independent visual workbench consumes
successful derived artifacts rather
than becoming part of the compiler or a daemon/service. This boundary does not
settle final avatar-package serialization or compatibility.
Build requests include all outcome-affecting source/dependency,
compiler/toolchain, contract/schema/profile, configuration/seed,
backend-capability/protocol, and target-platform inputs. Attempt identity is
unique for tracing and staging only; it cannot alter target or idempotent
equality. Candidate identity derives from deterministic request, artifact role,
and identity-rule revision. Canonical serialization/hash is proposed as
restricted canonical JSON with domain-separated SHA-256 digests and remains
required before activation. Inspection is a separate read operation with
closed statuses and shared completeness/diagnostic conventions. Producer/output
trust is distinct from coordinator/reporter/publisher trust; worker trust loss
invalidates worker output and validation cannot rehabilitate it. The
[fixture-manifest specification](../../spec/fixture-manifest/README.md) owns
the manifest payload and separate content-identity readiness/decision
admission and successor history.
Performance claims must be backed by a reproducible benchmark and hardware
profile. Beyond the active Readiness 1 shell, the Readiness 2 candidate remains
unadmitted and no Readiness 3 implementation package is activated. Any future
worker must negotiate protocol/
version compatibility, obey bounded time/resource budgets, map crash/timeout/
resource outcomes, validate outputs before publication, and leave the compiler
surviving worker failure; exact worker serialization remains deferred. The
conceptual mapping is closed: unsupported protocol negotiation is
`unsupported`; trusted parent termination or transport closure after an
established configured timeout or resource breach is `resource-limit`;
unexpected or unqualified termination, unexplained exit, transport loss,
failed termination invariant, truncated framing, or corrupt framing is
`internal-failure`; well-framed decoded
contract-invalid output is `output-failure`; and a well-framed worker-declared
domain failure is validated before mapping to its governed status. Loss of
coordinator, reporter, or publisher trust is `internal-failure` with no
publication. A trusted parent may report its own observation after worker trust
loss, but cannot adopt worker output.

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
The conceptual top-level shape is `contract`, `source`, `basis`, `profiles`,
`body`, and `extensions`; `body` uses explicit typed collections and stable
references, with core collections present even when empty and no generic union.
The required basis is length unit, handedness, up, and forward. Stage 1 frame
roles are owner-specific: Part local/reference, Joint proximal/distal, and
Socket intrinsic interface; Attachment host/mating are contextual endpoint
roles. Source profiles initially name only semantic numeric-domain profiles.
Readiness 2 uses a rigid transform carrier with exactly three translation and
four explicit `xyzw` quaternion components and no scale/shear fields; Readiness
3 freezes numeric basis, normalization, conditioning, and tolerances. Identity,
containment, module presence, basis, and grammar-required
values are explicit. Omission requires one exact deterministic
contract/profile-owned default with stable rule identity and `defaulted`
provenance; null-as-missing, implicit zero, neighbour inference, and hidden
equations are not allowed.

Machine addresses use the proposed typed semantic-address profile rather than
filesystem-like strings, and display names are not identity. The semantic
numeric basis is proposed as right-handed metres, +Y up, and +Z
creature-forward. Values are finite binary64 and rigid transforms use the
Readiness 2 translation/quaternion carrier. Batch 13's Proposed direction adds
correctly rounded decimal admission, round-to-nearest ties-to-even, fixed
operation order, and no reassociation, implicit FMA contraction, FTZ, or DAZ.
Same-target claims normalize into one canonical local-to-parent frame and use
direct componentwise translation and q/-q rotation comparison. Scalar
predicates are exact bounded dyadic/integer comparisons. Quaternion
normalization uses the specified correctly rounded square root; its
already-normalized tuple-distance predicate uses an offline-derived half-chord
bound with no square root, norm, `asin`, or `sin`. Structured claim IDs retain
occurrences/provenance, reject same-ID
collisions, sort pair evaluation, and select the smallest tuple; generic graph
collection keys remain separate. The deterministic normalization path and
floating-point controls are fixed directions, while ranges, near-zero/drift
thresholds, constants, margins/error formula, and implementation bindings
remain evidence-gated. The planned
[numeric/frame profile experiment](../research/numeric-frame-profile-experiment.md)
preregisters rational/ULP, H-derivation, normalization/sqrt, identity/order,
and compiler-mode fixtures, separate semantic budgets, independent oracles,
frozen corpora, condition estimates, and metamorphic checks. Diagnostic
codes and profiles are owned by the proposed
[diagnostics contract](../../spec/diagnostics/README.md).

Future host adapters remain a separate post-Readiness-3 transaction. Their
proposed boundary declares signed permutation `C` and finite positive scale `s`
in engine-units/metre: vector lengths use `sC`, scalar lengths use `s`,
directions and normalized normals use `C`, and rigid transforms use `D H D^-1`
for `D = diag(sC, 1)`. Storage/output
conformance is the default tier and makes no runtime arithmetic claim; an
optional runtime tier adds probes and fixtures. Target precision, domain,
narrowing, overflow/underflow/subnormal policy, and angular/translation budgets
are explicit. Binary32 subnormal claims require FTZ/DAZ probing; missing
capability is unsupported. Core snapshots remain binary64.

Diagnostic compatibility remains separately owned and Proposed: nine initial
domains cover source admission, dependencies, semantic identity, graph
structure, frame/numeric rules, resources, execution trust, publication, and
inspection. A tiny mandatory bootstrap registry/profile handles unknown
registry/profile negotiation without adding an operation phase.

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
version, configuration, and seed, or report why it cannot. The initial numeric
evidence target is WSL x86_64 plus native-Linux smoke; a materially different
architecture/toolchain is required before any broader cross-platform
reproducibility claim. Bit-exact
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

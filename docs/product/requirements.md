# Product requirements

Status: Proposed product baseline

These requirements describe intended outcomes. `Must` indicates a foundational
constraint; `should` indicates a desired outcome that may be staged. Proof
methods remain provisional until experiments establish useful metrics.

## Initial product boundary (Proposed)

The current Round 2 proposal defines four bounded product choices:

- Creature Kernel is an engine-independent procedural creature compiler and
  embodiment runtime, not initially a game, editor, or general-purpose engine;
  a real-time game is the first downstream proof and integration target.
- The earliest workflow serves the project developer or researcher through
  structured source, CLI/API operations, diagnostics, and reproducible
  evidence; technical artists and game developers are downstream review and
  integration users.
- Stylized furry characters are the initial domain, with demanding
  close-contact and deformation scenarios as motivating stress cases and
  reusable mechanisms kept general.
- Native programmatic generation without a handcrafted base mesh is the first
  reference path; external authored-mesh conformance is later and must not be
  foreclosed by early contracts.

These choices are recorded under DR-0005, which defers source semantics, the
detailed compile/runtime boundary, automation contract detail, detailed
morphology ranges, backend, and budget decisions. DR-0008 now records the
Proposed bounded first morphology family and grammar envelope.

## First-proof boundary (Proposed)

The first proof is deliberately staged. Stage 1 is the first continuation gate
and may claim only deterministic generation of the bounded morphology family,
semantic regions and appearance inputs, structured diagnostics, and
source-linked semantic joint frames and region intent/lineage. It must not be
used to claim a usable bone hierarchy, bind weights/skinning, analytic
collision proxies, actual contact artifacts, shared pose or animation,
contact behaviour, deformation, or real-time interaction. Every declared valid-supported
fixed fixture must pass every mandatory structural check and the recorded
subjective visual floor; a failed or inconclusive valid-supported fixture leaves
the gate open and remains evidence, while non-success fixtures must produce
their expected outcomes/diagnostics and are not counted as valid pass fixtures.
Every fixture expected outcome is
frozen as valid-supported, semantically invalid, or well-formed-but-unsupported;
every non-success fixture also freezes its primary diagnostic class/code. Only
valid-supported fixtures count toward the Stage 1 gate. Before EXP-0001
execution or evidence, stable fixture IDs, concrete source inputs,
discriminating parameters, seed/configuration, provenance, and these expected
outcomes must be frozen, although hypotheses may be selected earlier. Stage 2
separately proves embodiment by generating a usable skeleton, skin weights, and
collision proxies and proving one shared pose/control scenario. Stage 3 proves bounded
real-time interaction, including actual contact, localized deformation,
physical response, and declared budget evidence.

The first Readiness 3 resolver/fixture transaction is limited to the bounded
stylized digitigrade furry-biped family and its fixed fixture envelope. It
binds exactly one explicit authored-conflict comparison profile for competing
authored root-local and Attachment-equation-derived placement. The profile
identity and constants must be derived and frozen by a bounded successor
experiment; exact-zero comparison, indefinite caller-selected tolerances, and
post-hoc widening are not permitted. Once admitted, disagreement that fails
the profile's bounds is an `invalid-source` outcome with no successful
snapshot. Until that successor transaction is admitted, Readiness 3 remains
inactive.

The initial family is a stylized digitigrade furry biped with required
torso/pelvis, head/simplified muzzle, two arms/simplified hands-paws, and two
digitigrade legs/simplified feet-paws. Predefined ears and tail are optional
through named sockets. Qualitative variation spans stature, torso width and
depth, head/muzzle scale, arm and leg length, foot size and angle, and optional
ear and tail shape. It is tested with at least four fixed profiles:

- compact, broad, short-limbed, large-head;
- tall, narrow, long-legged;
- slender, long-limbed; and
- stocky, broad-chested.

At least one profile contrasts optional-module presence, absence, or style;
exact ratios and parameter ranges remain deferred. Extra limbs, wings,
quadrupeds, arbitrary joints or graphs, detailed digits, arbitrary anatomy,
and other families are deferred.

The fixed profiles must be generated through the same shared operations with
no per-fixture patches. Evidence combines objective structural checks with a
modest recorded human visual assessment; the [visual-quality evaluation
protocol](../research/visual-quality-evaluation.md) owns that method rather
than this product requirement.

## Programmable source and determinism

### CK-PROD-001: Authoritative semantic source set

The system must preserve durable authored intent in an authoritative semantic
source set. Initially this may be one structured, human-readable document;
future explicit semantic override layers may also be authored inputs. The
source set alone is authored authority. Every outcome-affecting external
authored asset is an exactly versioned source-set dependency. Every operation
must return one authoritative result envelope, including failures before
semantic resolution. The semantic resolver envelope exposes exactly one of
`success`, `input-failure`, `invalid-source`, `unsupported`,
`dependency-failure`, `resource-limit`, or `internal-failure`; it also reports
processing and diagnostic completeness. The authoritative public build
operation extends this closed vocabulary with `output-failure` for trusted
derived-output or publication failure. A validated, inspectable, reproducible,
per-build semantic body-graph snapshot is required for successful semantic
`resolve` and may be omitted by operations such as `validate` only when their
own contract permits it. Snapshot finalization is an in-memory resolver
handoff; serialization and publication are build/output responsibilities.
Semantically invalid and well-formed-but-unsupported partial graphs are
non-compilable, non-contractual debug data. Mesh, rig, runtime, and other
artifacts remain further derived outputs. See
[DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md).

Diagnostic compatibility is Proposed and separately owned: the initial
registry has nine domains—source-admission, dependency, semantic-identity,
graph-structure, frame-numeric, resource, execution-trust, publication, and
inspection—and one tiny mandatory bootstrap registry/profile for unknown
registry/profile negotiation. Exact code membership and serialized fields
remain fixture-gated.

The initial adapter admits one strict UTF-8 JSON document, rejects duplicate
members and comments/includes/evaluation, and uses the proposed JSON Schema
Draft 2020-12 vocabulary for structural validation before CK semantic
resolution. It must require a top-level object and exactly one version-neutral
family/revision discriminator; missing or malformed discriminator data is
invalid-source, while an unknown family or unsupported revision is reported as
unsupported before a current schema is applied. Unknown core members fail.
Explicit migration produces a new source. Source text, normalized source model,
and resolved snapshot remain distinct. Exact field names, schema files, and
migration serialization remain deferred to the owning specifications. The
canonical admission, status, diagnostic, and resource rules are in the
[body-document contract](../../spec/body-document/README.md).
The conceptual document shape is `contract`, `source`, `basis`, `profiles`,
`body`, and `extensions`, with explicit typed body collections and stable
references; exact shape and omission/default rules remain owned by that
contract. Required basis is length unit, handedness, up, and forward, with no
initial per-value unit override.

### CK-PROD-002: Deterministic compilation

Given the same complete build request, the system must produce semantically
equivalent output or report why reproducibility cannot be guaranteed. A build
request includes all outcome-affecting source/dependency, compiler/toolchain,
contract/schema/profile, configuration/seed, backend-capability/protocol, and
target-platform inputs. A unique per-attempt identity is for tracing only and
must not change target selection or idempotent equality. EXP-0001 evidence
additionally requires frozen fixture IDs,
concrete source inputs, discriminating parameters, seed/configuration, and
provenance.

Compilation reproducibility is an initial requirement. Bit-exact simulation,
network, and replay determinism are deferred until their requirements and
evidence are defined.

Batch 13 adds a Proposed consequence for this requirement only: semantic
decimal admission uses correctly rounded binary64 conversion with
round-to-nearest, ties-to-even and explicit overflow, underflow, subnormal,
and non-finite handling. The initial canonical numeric direction uses a fixed
operation order and prohibits reassociation, implicit FMA contraction, FTZ, and
DAZ. Same-target claims normalize into one canonical local-to-parent frame;
translations compare directly and rotations use q/-q equivalence. Scalar and
translation predicates use exact bounded dyadic/integer arithmetic, and
quaternion comparison uses an offline-derived binary64 half-chord bound. The
deterministic quaternion normalization requires the specified correctly rounded
binary64 square root; only the already-normalized tuple-distance predicate uses
no square root, norm, `asin`, or `sin`. Structured source-derived claim
IDs retain multiplicity/provenance, detect same-ID collisions, evaluate pairs
in sorted-ID order, and select the smallest declared value tuple. These local
claim rules remain distinct from generic graph collection keys. The numeric
experiment preregisters rational/ULP, normalization/sqrt, H-derivation,
order/identity, and compiler-mode evidence before any evaluated run. Exact
constants, ranges, profile IDs, and validation-margin/error formula remain
open; this paragraph is not an activation or acceptance decision.

The proposed canonical-data profile uses restricted canonical JSON and
domain-separated SHA-256 digests for source, normalized graph, build request,
fixture manifest, and published artifact domains. Attempt IDs, timestamps,
filesystem paths, logs, allocation order, and human diagnostic text are not
outcome identity inputs. Exact canonical numeric and address rules remain
prerequisites to activation; see the [canonical-data specification](../../spec/canonical-data/README.md).

### CK-PROD-003: Durable semantic and artifact identity

Durable semantic identity must identify exactly Part, Joint, Socket,
Attachment, Region, Capability, and Field across regeneration through a
structured semantic address: source namespace, authored stable module-instance
anchors, semantic concept kind, and role-local key. Each source namespace has exactly
one owner in a resolved source set. A namespace collision requires an authored,
deterministic, collision-free remapping across every contributed semantic
address; implicit shared namespace ownership is not allowed. Identity
continuity is promised only while the authored address and concept remain
unchanged across regeneration; structural-edit lifecycle rules remain
deferred. Artifact/build identity and provenance are separate, and external
authored assets retain their exact dependency revisions. Module is an authored
reusable scope that instantiates concepts, not an embodied graph concept;
landmark, anchor, dimension, and frame are typed owner+role records. See
[DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md).

Batch 11 proposes that machine semantic addresses use a typed, restricted
ASCII representation with ordered anchor segments, concept kind, and role key;
Unicode display names remain separate presentation data. The exact profile is
owned by the [semantic-address specification](../../spec/semantic-address/README.md).

Claim identity for repeated authoritative properties is a separate local
contract: it includes the canonical target, claim kind, source/namespace,
stable authored semantic record/property address, and an explicit authored key
for intentional multiplicity. It is not derived from a JSON pointer, array or
traversal order, allocation, thread, time, or generated ID. Graph concept
collections retain their own structured owner-role/claim collection keys.

### CK-PROD-004: Shared deterministic domain operations

One deterministic domain-operation model must cover query, semantic mutation,
resolution/compilation, validation, diagnostics, artifact inspection, and future
transaction semantics. CLI, programmatic API, future GUI, tests, scripts, and
external AI agents are adapters over these operations and may not add private
core behaviour. The first implementation may be an in-process library plus CLI
adapter. See [DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md).

### CK-PROD-005: No embedded-AI dependency

The platform must remain fully usable without an embedded language model.
External AI agents may operate the same deterministic interfaces as other users.

### CK-PROD-006: Public build output lineage

The public `build` operation must carry one authoritative result envelope from
source resolution through derived output and publication. Its staged manifest
uses a non-authoritative candidate artifact identity; successful atomic
publication promotes that same identity to the committed artifact identity.
Attempt identity is trace-only and must not enter committed success bytes or
identity/equality. The initial contract persists no diagnostics-only failure
bundle; failed operations return the authoritative envelope. The explicit
output root and candidate identity determine a safe deterministic target,
existing different or unverifiable occupants are never overwritten, and
inspection requires expected build/artifact lineage rather than guessing
whether stale output is current. The full collision, publication, worker,
encoding, staging, and trust contract is owned by the [Proposed build-operation
specification](../../spec/build-operation/README.md), including post-collision
byte-divergence failure, the initial local-WSL filesystem profile, separate
inspection statuses, and producer/coordinator trust boundaries.

### CK-PROD-007: Immutable fixture admission

Readiness fixtures use an immutable manifest payload containing suite kind,
fixture paths/content hashes, profiles, provenance, expected results, and
expected snapshot references where applicable. The payload never contains its
own digest, approval, or active pointer. A separate readiness/decision record
names the reviewed source commit, manifest path, manifest digest, path-scoped
payload digest/tree identity, preflight result, and Ben approval. Preflight
proves internal consistency, not expectation correctness; it reruns on the
merged target by comparing those content identities rather than an unchanged
merge commit. Successors are recorded explicitly, rollback or deactivation is
explicitly approved, and unlisted fixtures do not activate.
Operation status remains separate from semantic fixture taxonomy, with a
primary diagnostic required for every non-success. The canonical conceptual
field groups and Readiness 2/3 corpus are owned by the [fixture-manifest
specification](../../spec/fixture-manifest/README.md).

Readiness 3 is a distinct later activation transaction. It admits a successor
fixture manifest, expected graph snapshots, a comparison-profile identity, and
the resolver/implementation binding only after numeric, frame, address,
canonical-data, and diagnostic prerequisites are available. This is a project
ledger boundary, not a claim that those fixtures or implementations exist.

## Generated embodiment

### CK-PROD-010: Unified derivation

Geometry, semantic regions, skeleton, collision, materials, deformation,
packaging, and runtime representations must share the resolved semantic body
graph as lineage or identify an explicitly linked authored input. Unified
derivation does not require one mesh, topology, geometry field, numerical
representation, or universal solver. In Stage 1, any claimed joint frames,
semantic region intent, and related lineage must remain linked to the same
semantic source and build lineage. Usable bone hierarchies, bind
weights/skinning, analytic collision proxies, actual contact artifacts, shared
pose, and actual contact/deformation are later-stage claims.

### CK-PROD-011: Composable body grammar

The first body model must support the bounded typed Part-containment tree for
the proposed digitigrade biped family. Every embodied Part, including a
present optional module root, must have exactly one path to the embodied root;
relations cannot create or repair containment, and containment supplies
reference-transform inheritance. Containment cycles and typed-relation cycles
must be validated independently. Required Stage 1 axial and limb Joints must
connect the structural parent Part to its immediate containment child.

The identity-bearing concepts are exactly Part, Joint, Socket, Attachment,
Region, Capability, and Field. A Joint is directed, with one proximal and one
distal Part, and the resolved graph must expose canonical proximal- and
distal-frame records in the corresponding Part-local bases with provenance.
Each Socket is a Part-owned interface with one intrinsic interface frame in the
owning Part basis. Attachment host and mating roles are contextual endpoints
that reference Sockets, not intrinsic Socket frame roles. The normalized model
separately declares each module instance with
a stable authored declaration address, module/root-role/template reference,
anchor/provenance, presence/optionality, and Attachment requirement; absence
and present-but-unattached are distinct. An absent optional declaration emits
or reserves no Part, no graph relation may target its non-embodied root role,
and it participates in declaration uniqueness rather than the Part namespace.
If later present, its Part identity derives deterministically from the
module-instance anchor and root role. For a present optional module, an
Attachment must connect exactly one host Socket to one mating Socket, agree
with the host-Part/module-root containment declaration, and initially be the
sole incoming Attachment for that attached root. Each Socket has total active
capacity one across host and mating roles; cross-role reuse is invalid.
Host/mating Socket frames, an optional typed Attachment offset, and the inverse
mating frame determine the module-root placement; a competing authored
placement must agree within the one R3 authored-conflict comparison profile or
be semantically `invalid-source` with no successful snapshot. Duplicate,
detached, cyclic, or invalid endpoint cases fail.
Attachment never implies a Joint. Module is an authored reusable scope, not an
embodied graph concept; landmark, anchor, dimension, and frame are typed
owner+role records. Region never owns, Capability is not an implementation,
and Field carries representation-neutral intent/lineage. Readiness 2 uses a
rigid transform carrier with exactly three translation components and four
quaternion components in explicit `xyzw` order, with no scale or shear fields;
Readiness 3 freezes numeric basis, normalization, conditioning, and tolerance
semantics. These are semantic roles and frames, not a bone, solver, rig,
limits, runtime representation, or anatomy-fidelity claim. See [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
[DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
and the [body-graph contract](../../spec/body-graph/README.md).

The required functional chain remains root-reference frame owned by pelvis →
pelvis → spine Joint → torso/chest Part → neck-base Joint → neck Part →
head-base Joint → head; arms use shoulder/elbow/wrist Joints connecting torso,
upper-arm, forearm, and hand/paw Parts to terminal paw-base landmark/Socket
roles; legs use hip/knee/hock-or-ankle Joints connecting pelvis, thigh,
lower-leg, and foot/paw Parts to terminal paw-base landmark/Socket roles.
Ear/tail modules use Attachment, and a movable tail also uses a separate Joint;
ears require no articulation.

Transforms own reference-frame placement; typed dimensions own size/extents;
anchors and landmarks are stable with authored, defaulted, or derived
provenance; ratios are derived only. Claims target owner address, property role,
and frame/context and normalize into one canonical local-to-parent frame before
direct componentwise translation and q/-q rotation comparison. Authored claims
and explicit invariants must be jointly satisfiable within contract tolerance;
derived or defaulted values never override authored claims, and hidden inferred
equations are not allowed. A composition residual may be retained as a
separately named diagnostic/snapshot check, not as the same-target validity
predicate. A conflict is a deterministic semantic-invalid diagnostic and no
success snapshot. Each source declares units, handedness, up, and forward.
Resolution converts to a contract-revision canonical internal basis and records
conversion provenance. Distinguish Part local/reference, Joint proximal/distal,
Socket intrinsic interface, Attachment host/mating endpoint context, derived
resolved world/reference, and runtime-pose frames. Every transform
entering Attachment composition must be finite, non-degenerate, and invertible
under the declared profile. A source violation is `invalid-source`; an
implementation failure on an admissible transform is `internal-failure`.
Readiness 2 uses a rigid transform carrier with exactly three translation
components and four explicit `xyzw` quaternion components, with no scale or
shear fields. Canonical axes, unit, finite-number and normalization semantics,
and comparison shapes are fixed Proposed material. Exact bounded dyadic scalar
arithmetic, deterministic quaternion normalization, offline half-chord bounds,
structured claim IDs, sorted pair reporting, and smallest-tuple selection are
fixed directions; exact conditioning, numeric ranges, constants,
validation-margin/error formula, deterministic evaluation bindings, and
tolerances remain deferred to Readiness 3. Claim identity remains separate
from generic graph collection keys.

### CK-PROD-012: Connected visible surface

The native generation path should produce a coherent renderable surface for
the bounded first body family without requiring a handcrafted base character
mesh. Objective structural checks and recorded human visual assessment are
separate evidence classes; the visual floor and evidence procedure are owned
by the [visual-quality evaluation protocol](../research/visual-quality-evaluation.md).

### CK-PROD-013: Runtime avatar package

Compilation must produce a bounded runtime representation suitable for loading
by a game or engine adapter.

The proposed package combines conventional prepared mesh, LOD, rig, collision,
material, and deformation assets with selected semantic fields, cages,
signed-distance data, and regional simulation data. It must not require either
fully live implicit generation by default or semantics-free conventional
assets.

### CK-PROD-014: Procedural appearance inputs

The native path should generate semantic material inputs sufficient for basic
stylized colours, markings, and body-region distinctions without unique painted
textures. Stage 1 does not require dense fur/hair, clothing/cloth, cinematic
rendering, or detailed facial and digit features; these remain deferred or
semantic-only until later evidence.

### CK-PROD-015: Deferred external-tracking compatibility

Future embodiment and control design must not make animation clips the
exclusive pose source or foreclose external tracked pose or target inputs. When
that capability is activated, it must define explicit control bindings,
coordinate calibration, and retargeting across supported generated
proportions.

This is a required compatibility constraint on later design, not a Stage 2
implementation or current evidence gate. External-tracking implementation,
tracking-loss and fallback behaviour, headset APIs, OpenXR, device integration,
first-person rendering, concrete schemas, and exact tracked-node sets remain
deferred and unselected.

## Real-time experience

### CK-PROD-020: Real-time-first downstream target

A real-time interactive game is the primary downstream experience. Offline
compilation is permitted, but normal interaction must not depend on rendering or
simulating every output frame in advance.

### CK-PROD-021: Bounded runtime work

Runtime systems must expose explicit budgets, quality levels, or activation
limits rather than assuming maximum simulation fidelity everywhere.

### CK-PROD-022: Graceful fallback

Characters and interactions should negotiate supported capabilities and retain
a useful lower-quality path when an advanced deformation or GPU feature is
unavailable.

### CK-PROD-023: Semantic interaction

Interaction logic should target semantic body capabilities and regions rather
than requiring animation authored for one exact pair of meshes.

### CK-PROD-024: Selective deformation

The platform should support localized compression, sliding, shear, and recovery
with visual deformation and physical response, without requiring full-character
high-resolution soft-body simulation.

Beyond the bounded Stage 3 proof, potential later outcomes include compliant
boundary regions and internal contact paths, through-thickness coupling so
internal contact can produce controlled external regional displacement, and
optional bounded regional shape adaptation. Structural body-plan changes remain
build/recompile-time changes. These are provisional outcome-level goals; exact
representations, algorithms, solvers, and activation boundaries remain
deferred.

Live work is bounded to pose, contact, parameterized deformation, and activated
regional solvers. A larger high-end-PC budget remains finite, and capability
tiers must retain useful fallbacks when a tier cannot be activated.

### CK-PROD-025: Structural mutation and preview reload

Proven-compatible parameter changes should be able to update an active avatar
in place. Topology, body-plan, and other major structural changes must trigger
recompilation and validation rather than arbitrary live gameplay mutation. In
the initial preview/authoring workflow, compilation may block or freeze the
session without requiring the user to close and reopen the scene or session; a
valid replacement reloads in place, while failure retains the previous
validated avatar and reports diagnostics. A loading-screen fallback is allowed
when a structural package is needed. Later asynchronous in-session swaps are a
possible evolution, not an initial requirement.

## Validation and evidence

### CK-PROD-030: Structured diagnostics

Generation and validation must report one structured operation result rather
than only visual failure. Semantic resolution has the closed status set
`success`, `input-failure`, `invalid-source`, `unsupported`,
`dependency-failure`, `resource-limit`, and `internal-failure`; the authoritative
build operation additionally uses `output-failure` for trusted derived-output
or publication failure. Status mapping is deterministic: internal trust loss
comes first, then a qualifying resource interruption, then the earliest
applicable phase unable to produce its required output. In dependency phases,
`dependency-failure` outranks `invalid-source`, which outranks `unsupported`;
parse and semantic phases use `invalid-source` before `unsupported`. All
mandatory independent checks capable of changing status or primary run unless
resource/trust interruption prevents them; optional checks cannot change
status or primary. Reached earlier diagnostics remain available when
dependent phases are blocked.
Every non-success result has a primary diagnostic matching its status.
Processing is complete when all work applicable to establishing and trusting the
selected outcome ran; blocked phases are inapplicable. Diagnostic completeness
is complete when all applicable profile-required diagnostics were retained;
ordinary truncation makes it false but is not `resource-limit` unless it
prevented processing or trust. Diagnostics are bounded and sorted by phase,
severity/category, normalized source path/offset, code, and semantic address;
human text is not a key. See
the [body-document contract](../../spec/body-document/README.md).
Resolver phase 8 is in-memory snapshot finalization/handoff, not filesystem
serialization. External serialization, staging, and publication failures are
owned by the [build-operation specification](../../spec/build-operation/README.md)
and report `output-failure` when trusted derived-output handling remains
possible.

### CK-PROD-031: Headless proof

Core workflows should support headless tests, debug renders, and machine-readable
results so they can run in automation and external-agent loops.

### CK-PROD-032: Reproducible performance evidence

Performance claims must identify the body input, compiler/runtime version,
quality settings, scene, reference hardware, metric, and reproduction command.

### CK-PROD-033: Hostile-input resource bounds

The operation must handle untrusted input with a finite implementation profile
and streaming/token-aware guards. Raw bytes, incremental UTF-8/tokens,
string/number token lengths before conversion, nesting and member counts,
per-dependency and aggregate budgets, graph/reference/module expansion, work,
memory, and diagnostics must be charged before unbounded materialization or
allocation. A configured breach reports `resource-limit` through the same
envelope only when it prevents required processing or trusted completion;
diagnostic truncation alone does not. A true operating-system/process
out-of-memory termination is outside the operation guarantee, while a surviving
implementation that loses trust reports `internal-failure`. Exact thresholds
and deterministic work units are profile-specific and deferred.

## Extensibility

### CK-PROD-040: Engine-independent core boundary

Core semantic formats and compilation concepts should not require one host game
engine, even if the first implementation uses a particular engine or tool.

The Batch 13 planning consequence is that host-adapter numeric/frame
conformance remains deferred until an adapter is activated. The future boundary
uses signed permutation `C` plus finite positive engine-units/metre scale `s`:
vector lengths use `sC`, scalar lengths use `s`, directions and normalized normals use `C`, and
rigid transforms use `D H D^-1` for `D = diag(sC, 1)`. Storage/output-only is
the default tier with no runtime arithmetic claim; an optional runtime tier
adds probes and fixtures. Both tiers declare precision/domain/narrowing and
overflow/underflow/subnormal policy; binary32 subnormal claims require an
FTZ/DAZ probe. This is Proposed follow-up evidence, not a current adapter
requirement or support claim. Before any adapter profile/schema activation,
Ben must explicitly dispose of the retained-human request-validation/status
mapping choice.

### CK-PROD-041: External mesh path

The architecture should leave a path for externally authored meshes to map onto
the same semantic runtime contract as an explicitly linked or mapped authored
input. External-mesh conformance and capability details remain deferred.

### CK-PROD-042: Versioned contracts

Serialized body and avatar contracts must eventually define versioning,
compatibility, migration, and unknown-field behaviour before third-party use.

## Unresolved requirement thresholds

The following require decisions or experiments before they can become measurable
acceptance criteria:

- exact parameter ranges and generator details for the supported first
  morphology;
- acceptable surface and deformation quality;
- compile-time budget;
- runtime frame target, resolution, and hardware profile;
- active character and high-quality region counts;
- deterministic replay or networking requirements;
- minimum fallback hardware and capabilities;
- external mesh conformance level for an initial release;
- exact capability-tier names, quality labels, and numerical budgets;
- package-swap state, topology-index, and transient solver-state compatibility
  rules for a future asynchronous path.

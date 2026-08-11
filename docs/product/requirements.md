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
- Stylized furry characters are the initial domain, with adult interactions as
  motivating contact/deformation stress cases and reusable mechanisms kept
  general.
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
authored asset is an exactly versioned source-set dependency. Compilation
returns one authoritative operation-result envelope covering loading,
syntax/schema/contract, dependency, resource, semantic-resolution, and
invariant diagnostics. A validated, inspectable, reproducible, per-build
semantic body-graph snapshot is an optional validated success payload only for
valid-supported input; any snapshot diagnostics are a derived persisted subset
of the envelope. Semantically invalid and well-formed-but-unsupported partial
graphs are non-compilable, non-contractual debug data. Mesh, rig, runtime, and
other artifacts remain further derived outputs. See
[DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md).

The current Proposed body-document contract initially admits one strict UTF-8
JSON document, rejects duplicate keys and comments/includes/evaluation, and
uses JSON Schema Draft 2020-12 for structural validation before CK semantic
resolution. Unknown core members fail. An explicit namespaced extension
envelope distinguishes unsupported required extensions from optional opaque
extensions, which are preserved without core semantic effect. Contract family
and revision are recognized exactly; migration is explicit and produces a new
source. Source text, normalized source model, and resolved snapshot remain
distinct. Exact field names, schema files, and migration serialization remain
deferred to the owning specifications.

Resolution proceeds through resource/input admission; syntax/schema/contract;
dependencies; namespaces/identity/references; ownership/typed relations;
unit/frame normalization and value derivation; semantic invariants; and
success publication. Fatal phases block dependent work while independent
diagnostics within a phase accumulate deterministically. Machine diagnostic
identity and order are stable compatibility data; human messages are not.
Required unresolved or ambiguous values cannot succeed. The implementation
profile has finite limits for source and aggregate bytes, string lengths/counts,
nesting depth, object/array members, graph entities/relations, ownership depth,
module/reference expansion, extension count/payload, numeric admissibility,
diagnostics, and aggregate work/memory, with exact limits deferred. The profile
is selected during input admission, and its guards remain active through later
phases whose graph, expansion, work, or memory use cannot be known before
parsing.

### CK-PROD-002: Deterministic compilation

Given the same source, compiler version, configuration, and seed, the system
must produce semantically equivalent output or report why reproducibility cannot
be guaranteed. EXP-0001 evidence additionally requires frozen fixture IDs,
concrete source inputs, discriminating parameters, seed/configuration, and
provenance.

Compilation reproducibility is an initial requirement. Bit-exact simulation,
network, and replay determinism are deferred until their requirements and
evidence are defined.

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

The first body model must support a bounded typed ownership tree for the
proposed digitigrade biped family, plus exactly these identity-bearing
concepts: Part is structural/owned; Joint is a directed articulation relation
with exactly one proximal and one distal Part and endpoint frames relative to
each; Socket is a Part-owned named interface; Attachment connects one host
Socket to one mating Socket and is not automatically a joint; Region is an
overlapping spatial designation and never ownership; Capability is a queryable
affordance, not an implementation; and Field carries spatial semantic
intent/channel with lineage and representation-neutral meaning. Module is an
authored reusable scope that instantiates these concepts, not an embodied graph
concept. Landmark, anchor, dimension, and frame are typed owner+role records.
Part-to-Part ownership is the sole structural body-containment tree;
declarative ownership of other concepts and typed records scopes identity and
lifecycle without adding a structural body edge. Durable non-structural
concepts may be reified and connected through multiple role-labelled
relations. Invalid or
unsupported assemblies must receive the operation-result envelope with
structured diagnostics. The required functional articulation is root-reference
frame owned by pelvis → pelvis → spine Joint → torso/chest Part → neck-base
Joint → neck Part → head-base Joint → head; arms use shoulder/elbow/wrist
Joints connecting torso, upper-arm, forearm, and hand/paw Parts to a terminal
paw-base landmark/Socket; and legs use hip/knee/hock-or-ankle Joints connecting
pelvis, thigh, lower-leg, and foot/paw Parts to a terminal paw-base
landmark/Socket. Ear/tail modules use Attachment, and a movable tail also uses
a separate Joint. Ears require no articulation. These are semantic roles and
frames, not a bone, solver, rig, or anatomy-fidelity claim. See [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
and [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).

Transforms own reference-frame placement; typed dimensions own size/extents;
anchors and landmarks are stable with authored, defaulted, or derived
provenance; ratios are derived only. Claims target owner address, property role,
and frame/context and compare after normalization. Authored claims and explicit
invariants must be jointly satisfiable within contract tolerance; derived or
defaulted values never override authored claims, and hidden inferred equations
are not allowed. A conflict is a deterministic semantic-invalid diagnostic and
no success snapshot. Each source declares units, handedness, up, and forward.
Resolution converts to a contract-revision canonical internal basis and records
conversion provenance. Distinguish local/reference, joint, socket/mating,
derived resolved world/reference, and runtime-pose frames. Exact canonical
axes, units, rotation, scale, shear, numeric ranges, and tolerances remain
deferred.

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

The platform should support localized visual deformation and physical response
without requiring full-character high-resolution soft-body simulation.

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

Generation and validation must report structured, actionable diagnostics rather
than only visual failure.

### CK-PROD-031: Headless proof

Core workflows should support headless tests, debug renders, and machine-readable
results so they can run in automation and external-agent loops.

### CK-PROD-032: Reproducible performance evidence

Performance claims must identify the body input, compiler/runtime version,
quality settings, scene, reference hardware, metric, and reproduction command.

## Extensibility

### CK-PROD-040: Engine-independent core boundary

Core semantic formats and compilation concepts should not require one host game
engine, even if the first implementation uses a particular engine or tool.

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

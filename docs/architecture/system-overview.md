# System architecture overview

Status: Provisional conceptual baseline

## System purpose

Creature Kernel is proposed as an engine-independent procedural creature
compiler and embodiment runtime. It resolves an authoritative semantic source
set into one operation-result envelope and, for valid-supported success, an
optional per-build semantic body-graph snapshot, then derives specialized
representations for an embodied runtime avatar. It provides bounded systems for
animation, contact, deformation, and engine integration. It is not initially a
game, editor, or general-purpose engine; a real-time game is the first
downstream proof and integration target. This boundary remains Proposed under
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).
The current semantic boundaries are Proposed under [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).

```text
Human, script, test, or external AI
              |
              v
   Operation adapters (CLI/API/GUI)
              |
              v
   Shared domain operations
              |
              v
 Authoritative semantic source set
              |
              v
 Operation result envelope
              |
              v
 Optional valid-supported resolved semantic body graph
              |
              v
      Specialized compilers
   +----------+----------+-----------+
   |          |          |           |
   v          v          v           v
Body graph  Surface   Skeleton   Collision and
and fields   mesh     and skin   deformation data
   +----------+----------+-----------+
              |
              v
   Hybrid runtime avatar package
              |
              v
       Embodiment runtime
              |
              v
        Host-engine adapter
```

## Principal representations

### Authoritative semantic source set

The proposed authored inputs that preserve durable semantic intent. Initially
this may be one human-readable document; future explicit semantic override
layers may also be authored inputs. Every outcome-affecting external authored
asset is an exactly versioned dependency of the source set; an external mesh is
authored input but not semantic truth. The source set alone is authored
authority. Strict UTF-8 JSON and JSON Schema Draft 2020-12 are the Proposed
initial encoding and structural-validation technologies; exact source-set
layering and precedence remain open.

### Operation result envelope and resolved semantic body graph snapshot

Every phase and diagnostic—loading, syntax/schema/contract, dependencies,
resources, semantic resolution, and invariants—belongs to one authoritative
operation-result envelope with deterministic outcome and structured
diagnostics. Exact phase names and diagnostic codes remain deferred. A
validated, inspectable per-build semantic lineage snapshot is an optional
validated success payload only for valid-supported input. Snapshot diagnostics
are a derived persisted subset of the envelope. Semantically invalid and
well-formed-but-unsupported partial graphs are non-compilable,
non-contractual debug information; they cannot be consumed as a body graph.
Mesh, rig, runtime, and other artifacts remain further derived outputs.

The source and graph contracts deliberately separate source text, a normalized
admission model, and a resolved success snapshot. The initial source adapter is
one strict UTF-8 JSON document: duplicate keys, comments, includes, and
evaluation are rejected. Structural validation uses the proposed JSON Schema
Draft 2020-12 vocabulary, while CK semantic resolution owns identity,
relations, frames, provenance, and invariants. Exact semantic contract family
and revision must be recognized; migration is explicit and produces a new
source. Unknown core members fail, while namespaced optional extensions remain
opaque and have no core semantic effect. See the [body-document
contract](../../spec/body-document/README.md) and [body-graph
contract](../../spec/body-graph/README.md). Exact field names, schema files,
canonical bytes, and hashes remain deferred.

### First body grammar boundary

The first grammar is a bounded typed ownership tree for the proposed
digitigrade biped family. Its identity-bearing embodied concepts are exactly
Part, Joint, Socket, Attachment, Region, Capability, and Field. Module is an
authored reusable scope that instantiates those concepts, not an embodied
graph concept. Landmark, anchor, dimension, and frame are typed owned records
addressed through owner and role. Part is structural/owned; Joint is a
directed identity-bearing articulation relation with exactly one proximal and
one distal Part and endpoint frames relative to those Parts; Socket is a
Part-owned named interface; Attachment connects exactly one host Socket to one
mating Socket and does not imply articulation; Region may overlap and never
owns; Capability is a queryable affordance; and Field is representation-neutral
spatial intent/channel with lineage. Part-to-Part ownership is the sole
structural body-containment tree; declarative owners of other concepts and
typed records scope identity/lifecycle without creating structural body edges.
Non-structural concepts are reified through typed, role-labelled relations.

The pelvis Part owns the root-reference frame. The minimum Stage 1 chain is
pelvis → spine Joint → torso/chest Part → neck-base Joint → neck Part →
head-base Joint → head. Each arm uses shoulder, elbow, and wrist Joints connecting torso,
upper-arm, forearm, and hand/paw Parts, then a terminal paw-base
landmark/Socket. Each leg uses hip, knee, and hock-or-ankle Joints connecting
pelvis, thigh, lower-leg, and foot/paw Parts, then a terminal paw-base
landmark/Socket. Ear and tail modules use Attachment; a movable tail also has
a separate Joint. Ears require no articulation. These are semantic roles and
frames, not a bone hierarchy, solver, rig, joint-limit, or anatomy-fidelity
claim. Arbitrary anatomy and user-defined graph kinds are unsupported in this
first family.

Units, handedness, up, and forward are declared; normalization to a
contract-revision canonical internal basis records conversion provenance.
Claims compare after normalization by owner address, property role, and
frame/context. Authored claims and explicit invariants must be jointly
satisfiable within contract tolerance; derived/defaulted values never
override authored values, hidden inferred equations are not allowed, and a
conflict is a semantic-invalid diagnostic with no success snapshot. Exact
axes, units, rotation, scale, shear, ranges, tolerances, surface primitives,
serialized fields, and machine-schema contents remain deferred. Strict JSON
and JSON Schema Draft 2020-12 are the Proposed initial encoding and
structural-validation technologies.

### Simulation representation

Skeletons, joint limits, analytic collision, signed-distance fields, deformation
cages, regional simulation meshes, mass properties, and semantic contact regions.

### Visible representation

Renderable surface geometry, normals, material attributes, LODs, attachments,
and bindings to the simulation representation.

### Runtime avatar package

A derived, bounded hybrid package containing conventional prepared mesh, LOD,
rig, collision, material, and deformation assets plus selected semantic fields,
cages, signed-distance data, and regional simulation data required by a runtime
adapter. It is not a promise of fully live implicit generation or
semantics-free conventional assets. Artifact/build identity and provenance
distinguish generated packages from durable semantic identity. Exact
serialization, compatibility, and streaming behaviour remain undecided.

### Stage 1 surface experiment hypotheses

The Stage 1 surface proposals are deliberately narrower than this conceptual
runtime architecture. The [first surface experiment design](../research/first-surface-experiment-design.md)
and linked [DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
and [DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
are parked, Proposed confirmatory-research material. Their detailed records and
reviews are preserved, but no Revision 9, owner disposition, or additional
review is active. They become relevant only when at least two runnable candidate
surface implementations exist and a comparative outcome is intended to justify
production architecture, or when Ben explicitly reactivates them. Exploratory
prototypes may proceed before then, but their observations cannot claim formal
DR-0009/0010 support or reject. Permanent surface and topology architecture,
runtime field representation, animation-ready edge flow, retopology, and
backend choice remain unresolved.

## Architectural principles

### One source relationship

Geometry, rigging, collision, materials, deformation, packaging, and runtime
representations must derive from the same resolved semantic graph or explicitly
identify a linked authored input. This shared lineage does not require one mesh,
topology, geometry field, or universal solver.

### Semantic stability

Durable behaviour targets parts, regions, joints, attachments, local frames, and
capabilities through structured semantic addresses composed of source
namespace, authored module-instance anchors, concept kind, and role-local key.
Each source namespace has one unique owner in a resolved source set. Namespace
collisions require an authored, deterministic, collision-free remapping across
every contributed semantic address; implicit shared namespace ownership is not
allowed. Addresses are not derived from incidental path,
ordering, geometry, artifact identity, topology, or content hash. Artifact/build
identity and provenance remain separate; generated topology indices are
ephemeral through topology changes. Exact serialized address syntax and
clone/rename/split/merge/replacement lifecycle and remap rules remain deferred.

Only valid-supported input produces an optional compilable validated graph
snapshot; semantically invalid and well-formed-but-unsupported input are
distinct outcomes in the result envelope, with any rejected partial graph
explicitly non-compilable and non-contractual debug information.

Transforms own reference-frame placement, typed dimensions own size/extents,
and anchors/landmarks retain authored or derived provenance. Ratios are derived
only; conflicting constraints diagnose rather than silently choosing a winner.
The contract distinguishes local/reference, joint, socket/mating, derived
resolved world/reference, and runtime-pose frames.

### Deterministic core

Resolution and compilation should be reproducible from authored inputs, compiler
version, configuration, and seed. Query, mutation, resolution/compilation,
validation, diagnostics, and artifact inspection use one deterministic domain
operation model. Nondeterministic stages must be isolated and reported.

The resolver phases are resource/input admission; syntax/schema/contract;
dependencies; namespaces/identity/references; ownership/typed relations;
unit/frame normalization and value derivation; semantic invariants; and
success publication. Fatal failure blocks dependent phases, while independent
diagnostics within a phase accumulate deterministically. Provenance records
authored, defaulted, or derived values. Required unresolved or ambiguous
values cannot succeed. The implementation profile uses finite resource limits
across source and aggregate bytes; string lengths/counts; nesting depth;
object/array members; graph entities/relations; ownership depth;
module/reference expansion; extension count/payload; numeric admissibility;
diagnostics; and aggregate work and memory. Exact profile values and
accounting remain deferred. The profile is selected at admission, while its
guards remain active through all later phases.

The operation-result envelope also carries compatibility outcomes. Stable
machine diagnostic identity and deterministic order are contract data; human
messages are not compatibility keys. Semantic equivalence concerns durable
IDs, relations, frames, normalized values, provenance, and outcome, not source
ordering or incidental topology. Compiler/build/configuration/seed,
dependency, and artifact identities remain separate from semantic contract
identity.

### Engine-independent contracts

The proposed semantic model and runtime package concepts should not depend on one
host engine. Adapters translate those concepts into engine-specific systems;
the detailed package and interface contracts remain open under Proposed
[DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md).

### Compile/runtime separation

Expensive invariant generation is outside the frame loop. The runtime performs
bounded live pose, contact, parameterized deformation, and activated regional
solver work against the hybrid package. Compatible parameter changes may update
in place; topology, body-plan, and major structural changes require
recompilation and validation. The initial preview workflow may block while it
reloads a valid replacement in the same session, while a failed replacement
retains the old validated avatar.

### Specialized solvers

Animation, IK, collision, balance, cage deformation, cloth, and volumetric
simulation remain specialized layers coordinated through explicit data and
ownership. No universal solver is assumed.

### Bounded quality

Runtime work must be budgeted by capability, region, distance, interaction, and
hardware. Advanced systems require lower-cost fallbacks.

### Evidence before commitment

Uncertain geometry, animation, physics, and performance choices should advance
through research questions, experiments, adversarial review, and decision
records.

## System boundary

Creature Kernel initially owns (proposed boundary):

- authored semantic-source parsing and validation;
- semantic body resolution;
- native procedural creature compilation;
- avatar packaging and diagnostics;
- runtime semantic capabilities and interaction coordination;
- shared domain operations and CLI/API adapters;
- host-engine adapter contracts.

It does not initially own:

- a complete renderer or general-purpose editor;
- game logic unrelated to creature embodiment;
- online accounts, commerce, or SaaS infrastructure;
- a language model;
- cinematic-quality simulation as a mandatory runtime dependency.

## Major unresolved choices

- Exact body-document fields, schema contents, and later source-set layering.
- Permanent surface and topology generation strategy (the Stage 1 hypotheses in
  DR-0009 and DR-0010 do not resolve it).
- Implementation language and geometry libraries.
- Exact morphology ranges and generator set for the selected first family.
- Skinning and joint-correction approach.
- Runtime engine and adapter interface.
- Collision and deformable-body backends.
- Avatar-package serialization and versioning.
- Performance envelope and reference hardware.
- Capability-tier labels, finite quality budgets, and fallback thresholds.
- Future asynchronous package-swap state and compatibility rules.
- Bit-exact simulation, network, and replay determinism requirements.
- Artifact storage and reproducibility strategy.

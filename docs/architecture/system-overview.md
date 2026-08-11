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
The current semantic boundaries are Proposed under [DR-0002 Revision 5](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006 Revision 4](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008 Revision 5](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011 Revision 1](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).

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
authority; physical format, schema technology, and precedence remain open.

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

### First body grammar boundary

The first grammar is a bounded typed ownership tree for the proposed
digitigrade biped family. Part is structural/owned; Joint is an articulation
semantic relation with frames, not a bone or solver; Socket is a host interface
frame; Attachment maps a module to a socket and is not automatically a joint;
Region is an overlapping spatial designation and never ownership; Capability
is a queryable affordance, not an implementation; and Field is a spatial
semantic intent/channel with lineage and representation-neutral meaning.
Ownership is the sole containment tree; durable non-ownership concepts may be
reified and connected through role-labelled relations. Functional articulation
is root reference → pelvis → chest → neck → head; arms shoulder → elbow → wrist
→ terminal paw-base; legs hip → knee → one hock/ankle articulation → terminal
paw-base; and a present tail has a tail-base with later segments optional.
Ears require no articulation. These roles are not a bone, solver, rig, or
anatomy-fidelity claim. Arbitrary anatomy and arbitrary user-defined graph
kinds are unsupported in this first family. Units, handedness, up, and forward
are declared; normalization to a contract-revision canonical internal basis
records conversion provenance. Exact axes, units, rotation, scale, and shear,
as well as numeric ranges, surface primitives, and schema technology, remain
deferred.

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

- Body-document representation and schema technology.
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

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
CK-KICK-012 Batch 6 blocker resolutions are discussion-approved and represented
here as Proposed architecture consequences. The material canonical updates
require a fresh current Double review. DR-0002 Revision 8, DR-0008 Revision 8,
DR-0011 Revision 4, and DR-0012 Revision 3 are Proposed with Owner approval
Pending and current Double review Pending; the CK-KICK-012 Batch 5 review at
commit `a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical evidence.
No acceptance or clean review is implied.

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
authority. The initial adapter is proposed strict UTF-8 JSON with JSON Schema
Draft 2020-12 structural validation; the complete admission and compatibility
boundary is owned by the [body-document contract](../../spec/body-document/README.md).

### Operation result envelope and resolved semantic body graph snapshot

Every phase and diagnostic belongs to one authoritative operation-result
envelope with a closed status, completeness indication, deterministic bounded
diagnostics, and an optional validated per-build snapshot only for complete
valid-supported success. The body-document contract owns bootstrap order,
status precedence, diagnostic retention/order, and hostile-input resource
guards. The graph contract owns resolved semantic structure. Mesh, rig,
runtime, and other artifacts remain further derived outputs. See the
[body-document contract](../../spec/body-document/README.md) and
[body-graph contract](../../spec/body-graph/README.md); exact fields, codes,
canonical bytes, and hashes remain deferred.

### Proposed production platform and artifact/workbench boundary

CK-KICK-013 is a discussion-approved platform proposal, not an accepted
implementation decision. Proposed DR-0013 Revision 1 has Owner approval
Pending and current Double review Pending. Its target is a stable Rust
production semantic/compiler core in a Cargo workspace: an
engine-independent Rust compiler library, a thin CLI, and a replaceable
geometry boundary, with no initial daemon or service. Stage 1 uses an
in-process Rust CPU dense-field evaluator/extractor. If measured required
capability or performance is missing, evaluate an isolated C++ worker/backend
first; use in-process C ABI/FFI only if that worker is proven insufficient.
This leaves room for a backend change and makes no advanced-Rust-geometry
maturity claim.

Python remains the disposable host for experiments, evidence/render tooling,
and visual workbench tasks; it is not a production compiler dependency. The
initial reproducible execution/workbench target is Linux x86_64 under WSL or
native Linux. Portability is preserved while native Windows and host-engine
targets are deferred. The compiler writes ordinary versioned artifacts plus a
manifest, and an independent visual workbench consumes those filesystem
artifacts. This boundary does not settle final avatar-package serialization or
compatibility. Any performance claim requires a reproducible benchmark and
hardware profile. The language/build acceptance trigger remains unsatisfied,
so this proposal does not activate implementation packages.

### First body grammar boundary

The first grammar is a bounded typed Part-containment tree for the proposed
digitigrade biped family plus the seven typed concepts and relation semantics
owned by the [body-graph contract](../../spec/body-graph/README.md). Its
architectural boundary is explicit: every embodied Part has one containment
path, containment supplies transform inheritance, relations cannot repair
containment, and containment and relation cycles are checked independently.
Required Stage 1 Joints connect structural parents to immediate children.
Attachment composition derives the attached root's sole child-local containment
placement from the host Socket, optional offset, and the mating Socket frame
after composing the attached-root-to-Socket-owner containment transform;
descendants inherit only through containment and the no-implied-Joint rule is
preserved.
Resolved Joint and Socket frame records are canonical semantic handoff data,
not rig or runtime data. The architecture consumes these rules and does not
restate serialized spellings or numeric conventions; see the canonical graph
contract for the minimum axial/limb chain, provenance, and invariants.

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

The resolver uses the ordered phases and closed result-status rules in the
[body-document contract](../../spec/body-document/README.md). Fatal phases
block dependent work while independent diagnostics in a reached phase may
accumulate; the envelope retains reached diagnostics and marks incomplete
processing when phases or diagnostic retention are cut short. Resource guards
remain active through parsing, dependency/reference expansion, graph work, and
publication. Trust loss precedes configured resource-limit when completeness is
lost, which precedes the earliest fatal phase; within that phase,
invalid-source outranks unsupported when both are established. The primary is
the first diagnostic establishing the final status under that ordering, and
reserved diagnostic capacity preserves it despite ordinary truncation (or
reserves the resource/truncation diagnostic when arena exhaustion changes the
final status). The architecture requires deterministic work and bounded
diagnostics but leaves profile values and accounting detail to the canonical
specification. Semantic equivalence and identity remain separate from source
ordering, compiler/build/configuration/seed, dependency, artifact, and
incidental topology identities.

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
- Production implementation platform is proposed as Rust/Cargo under
  CK-KICK-013; geometry libraries/backend and any C++ worker boundary remain
  evidence-driven and unresolved.
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

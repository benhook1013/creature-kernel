# System architecture overview

Status: Provisional conceptual baseline

## System purpose

Creature Kernel is proposed as an engine-independent procedural creature
compiler and embodiment runtime. It resolves an authoritative semantic source
set into a per-build semantic body-graph snapshot, then derives specialized
representations for an embodied runtime avatar. It provides bounded systems for
animation, contact, deformation, and engine integration. It is not initially a
game, editor, or general-purpose engine; a real-time game is the first
downstream proof and integration target. This boundary remains Proposed under
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).

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
 Per-build resolved semantic body graph
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
layers may also be authored inputs. Physical format and precedence remain open.

### Resolved semantic body graph snapshot

The validated per-build semantic lineage produced after the source set is
resolved. It is derived for that build and is not a competing authored source.

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

The Round 6 proposals are deliberately narrower than this conceptual runtime
architecture. [DR-0009 Revision 4](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
proposes testing semantic skeleton/radius structures with implicit blending
where useful and reusable specialized generators for muzzle, paws, ears, feet,
and tail through a bounded five-branch nested ablation. Its Revision 4
experiment controls include strict evidence/outcome precedence, frozen
fairness and search contracts, per-criterion interaction contrasts, and a
separate mandatory visual floor versus comparative visual frontier.
[DR-0010 Revision 4](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
proposes a disposable deterministic pinned uniform-grid Lewiner Marching Cubes
policy, a common normalized field contract with three-grid convergence, and
parallel semantic-contributor propagation with analytical oracles. Its settled
local controls include sub-voxel phase checks, six-face field clearance,
prospective topology invariants, and a canonical non-negative distribution over
durable `(semantic_id, chart_id)` keys with deterministic ties, residuals,
parallel categorical/chart validity, and independent closed-form oracles. Both
remain Proposed with Owner approval Pending and Review Pending. Their Revision
3 Double reviews are historical and stale after the material revision; the
approved findings await new review. The [first surface experiment
design](../research/first-surface-experiment-design.md) remains a neutral
Proposed, manually maintained evidence design; it does not register EXP-0001,
create fixtures, or provide evidence. These are Proposed experiment
hypotheses, not accepted production contracts. Permanent surface and topology
architecture, runtime field representation, animation-ready edge flow,
retopology, and backend choice remain unresolved pending evidence.

## Architectural principles

### One source relationship

Geometry, rigging, collision, materials, deformation, packaging, and runtime
representations must derive from the same resolved semantic graph or explicitly
identify a linked authored input. This shared lineage does not require one mesh,
topology, geometry field, or universal solver.

### Semantic stability

Durable behaviour targets parts, regions, joints, attachments, local frames, and
capabilities through semantic identity. Artifact/build identity and provenance
remain separate; generated topology indices are ephemeral through topology
changes.

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
- First morphology family and generator set.
- Skinning and joint-correction approach.
- Runtime engine and adapter interface.
- Collision and deformable-body backends.
- Avatar-package serialization and versioning.
- Performance envelope and reference hardware.
- Capability-tier labels, finite quality budgets, and fallback thresholds.
- Future asynchronous package-swap state and compatibility rules.
- Bit-exact simulation, network, and replay determinism requirements.
- Artifact storage and reproducibility strategy.

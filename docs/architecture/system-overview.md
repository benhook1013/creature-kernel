# System architecture overview

Status: Active conceptual baseline

## System purpose

Creature Kernel converts a declarative semantic body definition into an embodied
runtime avatar and provides bounded systems for animation, contact, deformation,
and engine integration.

```text
Human, script, or external AI
              |
              v
       CLI / programmatic API
              |
              v
      Creature source document
              |
              v
         Creature compiler
   +----------+----------+-----------+
   |          |          |           |
   v          v          v           v
Body graph  Surface   Skeleton   Collision and
and fields   mesh     and skin   deformation data
   +----------+----------+-----------+
              |
              v
       Runtime avatar package
              |
              v
       Embodiment runtime
              |
              v
        Host-engine adapter
```

## Principal representations

### Creature source

The editable, deterministic declaration of parts, relationships, measurements,
capabilities, generators, materials, and compilation parameters.

### Resolved body graph

The validated semantic structure produced after defaults, references,
attachments, symmetry, inheritance, and generator parameters are resolved.

### Simulation representation

Skeletons, joint limits, analytic collision, signed-distance fields, deformation
cages, regional simulation meshes, mass properties, and semantic contact regions.

### Visible representation

Renderable surface geometry, normals, material attributes, LODs, attachments,
and bindings to the simulation representation.

### Runtime avatar package

A versioned, bounded package containing the data required by a runtime adapter.
Its exact serialization, compatibility, and streaming behaviour remain undecided.

## Architectural principles

### One source relationship

Geometry, semantics, rigging, collision, and deformation data must derive from
the same resolved body or explicitly declare another authoritative source.

### Semantic stability

Durable behaviour targets parts, regions, local frames, and capabilities rather
than generated mesh indices.

### Deterministic core

Compilation should be reproducible from source, compiler version, configuration,
and seed. Nondeterministic stages must be isolated and reported.

### Engine-independent contracts

The semantic model and runtime package concepts should not depend on one host
engine. Adapters translate those contracts into engine-specific systems.

### Specialized solvers

Animation, IK, collision, balance, cage deformation, cloth, and volumetric
simulation remain specialized layers coordinated through explicit data and
ownership. No universal solver is assumed.

### Bounded quality

Runtime work must be budgeted by capability, region, distance, interaction, and
hardware. Advanced systems require lower-cost fallbacks.

### Evidence before commitment

Uncertain geometry, animation, physics, and performance choices should advance
through research questions, experiments, adversarial review, and ADRs.

## System boundary

Creature Kernel initially owns:

- body-document parsing and validation;
- semantic body resolution;
- native procedural creature compilation;
- avatar packaging and diagnostics;
- runtime semantic capabilities and interaction coordination;
- CLI/API automation;
- host-engine adapter contracts.

It does not initially own:

- a complete renderer or general-purpose editor;
- game logic unrelated to creature embodiment;
- online accounts, commerce, or SaaS infrastructure;
- a language model;
- cinematic-quality simulation as a mandatory runtime dependency.

## Major unresolved choices

- Body-document representation and schema technology.
- Surface and topology generation strategy.
- Implementation language and geometry libraries.
- First morphology family and generator set.
- Skinning and joint-correction approach.
- Runtime engine and adapter interface.
- Collision and deformable-body backends.
- Avatar-package serialization and versioning.
- Performance envelope and reference hardware.
- Artifact storage and reproducibility strategy.

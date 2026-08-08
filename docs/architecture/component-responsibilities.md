# Component responsibilities

Status: Proposed responsibility map

These are conceptual boundaries, not approved packages or technologies. Code
directories should be created only after the relevant boundary is accepted and
its activation trigger is met.

| Component | Responsibilities | Explicit non-responsibilities |
| --- | --- | --- |
| Body document | Parse source, preserve user intent, report schema errors | Generate meshes or run gameplay |
| Semantic body resolver | Resolve parts, attachments, frames, dimensions, capabilities, defaults | Host-engine objects |
| Geometry field system | Evaluate part volumes, composition, semantic fields | Choose runtime animation |
| Surface compiler | Extract, repair, remesh, simplify, and attribute visible surfaces | Define semantic truth |
| Rigging compiler | Generate joints, limits, skinning, correctives, and bindings | Own interaction intent |
| Physics compiler | Generate collision, mass, cages, and regional simulation data | Run unbounded render-mesh physics |
| Appearance compiler | Produce semantic material inputs and generated attachments | Require unique painted textures |
| Avatar packager | Validate and serialize versioned runtime data | Redefine source semantics |
| Embodiment runtime | Coordinate animation, IK, contact, deformation, and quality tiers | Compile arbitrary topology every frame |
| Interaction system | Resolve semantic participants, phases, constraints, and fallbacks | Depend on exact mesh identities |
| CLI/API | Expose deterministic creation, inspection, build, test, and export operations | Contain AI-specific reasoning |
| Validation system | Produce structural, geometric, visual, and performance evidence | Declare product decisions automatically |
| Host adapters | Translate core packages and runtime contracts into engine-specific systems | Leak engine types into core contracts |

## Dependency direction

The intended direction is:

```text
Specifications and core data model
              |
              v
Compiler components and runtime contracts
              |
              v
CLI, validation, and host-engine adapters
```

Host adapters may depend on core contracts. Core contracts must not depend on a
host adapter.

## Cross-cutting obligations

Every component that becomes real should document:

- inputs and outputs;
- semantic and lifecycle invariants;
- deterministic and nondeterministic behaviour;
- error and diagnostic contracts;
- performance and memory expectations;
- capability and fallback behaviour;
- proof commands and fixtures;
- platform or backend limitations.

# Creature Kernel

Creature Kernel is an early research and engineering project for a programmable
creature-generation and embodiment platform.

The intended system begins with a semantic description of a creature rather
than a handcrafted mesh. It compiles that description into a connected body,
surface geometry, skeleton, skinning, collision representation, deformation
metadata, materials, and runtime interaction capabilities.

```text
Body program
    -> semantic body graph
    -> volumes and attachment rules
    -> generated surface
    -> rig, skinning, collision, and deformers
    -> interactive creature runtime
```

The initial creative focus is stylized furry characters. The architecture is
not intended to hard-code one species, one skeleton, or one rendering style.

## Project principles

- The editable source of truth is a deterministic body document, not a mesh.
- Geometry, semantic meaning, rigging, collision, and deformation derive from
  the same body definition.
- Body parts are composable generators with structure, capabilities, material
  regions, and physical properties.
- A CLI/API is a first-class interface. Humans, scripts, and external AI agents
  should be able to use the same operations.
- The core application does not depend on an embedded AI assistant.
- A real-time game is the primary downstream experience. Expensive creature
  generation may happen ahead of time or asynchronously, while compiled avatars
  expose bounded runtime representations and fallbacks.
- Specialized animation, contact, and deformation solvers cooperate through a
  shared representation; no single solver is expected to solve everything.
- Capability levels and fallbacks should let characters participate even when
  they do not support the highest simulation quality.

## Status

This repository currently records the project foundation. No implementation or
technology stack has been selected yet.

See [docs/FOUNDATION.md](docs/FOUNDATION.md) for the conversation-derived vision,
decisions, architecture, known unknowns, and prospective next questions.

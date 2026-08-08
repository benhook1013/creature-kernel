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

## Proposed project principles

These principles are proposed, provisional, assistant-synthesized project
direction under the DR-0001 Revision 3 operational trial. They are not accepted
product or architecture contracts. The body-document source proposal is
[DR-0002](docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
the real-time boundary proposal is
[DR-0003](docs/decisions/DR-0003-real-time-first-compiled-avatar-boundary.md),
and the CLI/API proposal is
[DR-0004](docs/decisions/DR-0004-external-automation-through-cli-and-api.md).

- The editable source of truth is a deterministic body document, not a mesh
  ([DR-0002](docs/decisions/DR-0002-declarative-body-document-source-of-truth.md)).
- Geometry, semantic meaning, rigging, collision, and deformation derive from
  the same body definition.
- Body parts are composable generators with structure, capabilities, material
  regions, and physical properties.
- A CLI/API is a first-class interface. Humans, scripts, and external AI agents
  should be able to use the same operations
  ([DR-0004](docs/decisions/DR-0004-external-automation-through-cli-and-api.md)).
- The core application does not depend on an embedded AI assistant.
- A real-time game is the primary downstream experience. Expensive creature
  generation may happen ahead of time or asynchronously, while compiled avatars
  expose bounded runtime representations and fallbacks
  ([DR-0003](docs/decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)).
- Specialized animation, contact, and deformation solvers cooperate through a
  shared representation; no single solver is expected to solve everything.
- Capability levels and fallbacks should let characters participate even when
  they do not support the highest simulation quality.

## Repository navigation

- [Documentation authority and reading order](docs/README.md)
- [Product vision and scope](docs/product/vision-and-scope.md)
- [Architecture](docs/architecture/README.md)
- [Decision record registry](docs/decisions/registry.md)
- [Open research questions](docs/research/open-questions.md)
- [Current project status](docs/project/status.md)

## Status

The project is in its foundation and adversarial design phase. No implementation
language, geometry backend, runtime engine, or asset format has been selected;
the linked DR-0002–0004 proposals remain Proposed.

See [docs/FOUNDATION.md](docs/FOUNDATION.md) for the historical
conversation-derived record. Current contracts are owned by the documentation
areas linked above.

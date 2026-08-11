# Creature Kernel

Creature Kernel is an early research and engineering project for a programmable
creature-generation and embodiment platform.

The intended system begins with an authoritative semantic source set rather
than a handcrafted mesh. It resolves that source set through one operation
result envelope into a connected body, then derives surface geometry, skeleton,
skinning, collision representation, deformation metadata, materials, and
runtime interaction capabilities.

```text
Authoritative semantic source set
    -> operation result envelope
    -> optional per-build resolved semantic body graph snapshot (success only)
    -> volumes and attachment rules
    -> prepared assets plus selected semantic runtime data
    -> bounded pose, contact, deformation, and regional solvers
    -> interactive creature runtime
```

The initial creative focus is stylized furry characters. The architecture is
not intended to hard-code one species, one skeleton, or one rendering style.

## Proposed project principles

These principles remain proposed, provisional, assistant-synthesized project
direction under the accepted DR-0001 Revision 5 governance process. They are
not accepted product or architecture contracts. The source-set proposal is
[DR-0002 Revision 5](docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
the semantic/artifact identity proposal is
[DR-0006 Revision 4](docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md),
the semantic vocabulary, measurements, and frames proposal is
[DR-0011 Revision 1](docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
the real-time boundary proposal is
[DR-0003 Revision 2](docs/decisions/DR-0003-real-time-first-compiled-avatar-boundary.md),
and the CLI/API proposal is
[DR-0004 Revision 2](docs/decisions/DR-0004-external-automation-through-cli-and-api.md).
The initial product boundary and reference workflow are proposed in
[DR-0005](docs/decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).

- Durable authored intent lives in an authoritative semantic source set. Every
  operation reports through one authoritative result envelope; the resolved
  graph and generated outputs remain derived, and a validated snapshot is
  optional and exists only for valid-supported success
  ([DR-0002](docs/decisions/DR-0002-declarative-body-document-source-of-truth.md)).
- Durable semantic identity is separate from artifact/build identity and
  provenance; generated topology indices are ephemeral
  ([DR-0006](docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md)).
- Specialized representations and solvers share the resolved semantic graph as
  lineage; this does not require one mesh, topology, or universal solver.
- Body parts are composable generators with typed structural ownership. Joints,
  sockets, attachments, regions, capabilities, and fields are distinct typed
  semantic concepts and relations, not implicit ownership or implementation
  mechanisms.
- The first functional articulation is root reference → pelvis → chest → neck
  → head; arms are shoulder → elbow → wrist → terminal paw-base, and legs are
  hip → knee → one hock/ankle articulation → terminal paw-base. A present tail
  has a tail-base and optional later segments; ears require no articulation.
  These are semantic roles, not a bone, solver, rig, or anatomy-fidelity claim
  ([DR-0008 Revision 5](docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)).
- Measurements keep transforms as reference-frame placement, typed dimensions
  as size/extents, and anchors/landmarks as stable authored or derived values;
  ratios are derived, and conflicting constraints produce diagnostics. Sources
  declare units, handedness, up, and forward; conversion to a contract-revision
  canonical basis records provenance. Exact axes, units, rotation, scale, and
  shear remain deferred
  ([DR-0011 Revision 1](docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)).
- CLI/API, future GUI, tests, scripts, and external AI agents are adapters over
  one deterministic domain-operation model
  ([DR-0004](docs/decisions/DR-0004-external-automation-through-cli-and-api.md)).
- The core application does not depend on an embedded AI assistant.
- A real-time game is the primary downstream experience. Expensive invariant
  generation happens outside the frame loop; hybrid compiled avatars expose
  bounded runtime representations and fallbacks
  ([DR-0003](docs/decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)).
- Specialized animation, contact, and deformation solvers cooperate through a
  shared representation; no single solver is expected to solve everything.
- Capability levels and fallbacks should let characters participate even when
  they do not support the highest simulation quality.
- The initial product is an engine-independent procedural creature compiler and
  embodiment runtime, not a game, editor, or general-purpose engine. A
  real-time game is the first downstream proof and integration target.
- The earliest workflow is the project developer or researcher using structured
  source, CLI/API operations, diagnostics, and reproducible evidence. Technical
  artists and game developers remain important downstream review and integration
  users.
- Stylized furry characters are the initial domain. Adult interactions are
  motivating difficult contact and deformation stress cases, while reusable
  body, contact, and solver mechanisms remain general.
- Native programmatic generation without a handcrafted base mesh is the first
  reference path. External authored-mesh conformance is a later path that early
  contracts must not foreclose.

## Repository navigation

- [Documentation authority and reading order](docs/README.md)
- [Product vision and scope](docs/product/vision-and-scope.md)
- [Architecture](docs/architecture/README.md)
- [Decision record registry](docs/decisions/registry.md)
- [Open research questions](docs/research/open-questions.md)
- [Current project status](docs/project/status.md)

## Status

The project is in its foundation and adversarial design phase. No implementation
language, geometry backend, runtime engine, or asset format has been selected.
See [current project status](docs/project/status.md) for the live round,
review, and owner-disposition state.

See [docs/FOUNDATION.md](docs/FOUNDATION.md) for the historical
conversation-derived record. Current contracts are owned by the documentation
areas linked above.

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

These choices are recorded under DR-0005, which defers source semantics,
the detailed compile/runtime boundary, automation contract detail, morphology,
backend, and budget decisions.

## Programmable source and determinism

### CK-PROD-001: Authoritative semantic source set

The system must preserve durable authored intent in an authoritative semantic
source set. Initially this may be one structured, human-readable document;
future explicit semantic override layers may also be authored inputs. Compilation
resolves the source set into a per-build semantic body-graph snapshot. The
resolved graph and generated outputs remain derived and cannot silently become
competing sources of truth. See [DR-0002 Revision 2](../decisions/DR-0002-declarative-body-document-source-of-truth.md).

### CK-PROD-002: Deterministic compilation

Given the same source, compiler version, configuration, and seed, the system
must produce semantically equivalent output or report why reproducibility cannot
be guaranteed.

Compilation reproducibility is an initial requirement. Bit-exact simulation,
network, and replay determinism are deferred until their requirements and
evidence are defined.

### CK-PROD-003: Durable semantic and artifact identity

Durable semantic identity must identify parts, regions, joints, attachments,
capabilities, and related concepts across regeneration. Artifact/build identity
and provenance are separate. Mesh, vertex, face, triangle, LOD, and array
indices are ephemeral and must not be promised stable through topology changes.
See [DR-0006 Revision 1](../decisions/DR-0006-durable-semantic-and-artifact-identity.md).

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
representation, or universal solver.

### CK-PROD-011: Composable body grammar

The body model must support composition through parts, attachments, joints,
local frames, measurements, capabilities, and material/deformation properties.

### CK-PROD-012: Connected visible surface

The native generation path should produce a coherent renderable surface for
supported body plans without requiring a handcrafted base character mesh.

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
textures.

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

- first supported morphology and parameter range;
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

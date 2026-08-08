# Product requirements

Status: Active baseline

These requirements describe intended outcomes. `Must` indicates a foundational
constraint; `should` indicates a desired outcome that may be staged. Proof
methods remain provisional until experiments establish useful metrics.

## Programmable source and determinism

### CK-PROD-001: Declarative creature source

The system must accept a structured, human-readable creature definition as the
editable source of truth.

### CK-PROD-002: Deterministic compilation

Given the same source, compiler version, configuration, and seed, the system
must produce semantically equivalent output or report why reproducibility cannot
be guaranteed.

### CK-PROD-003: Stable semantic identity

Durable contracts must identify body parts and regions semantically rather than
depending on generated vertex indices or incidental mesh ordering.

### CK-PROD-004: External automation

All core creation, inspection, compilation, validation, and export operations
must be available through a documented CLI or programmatic API.

### CK-PROD-005: No embedded-AI dependency

The platform must remain fully usable without an embedded language model.
External AI agents may operate the same deterministic interfaces as other users.

## Generated embodiment

### CK-PROD-010: Unified derivation

Geometry, semantic regions, skeleton, collision, and deformation metadata must
derive from the same resolved body definition or from explicitly linked sources.

### CK-PROD-011: Composable body grammar

The body model must support composition through parts, attachments, joints,
local frames, measurements, capabilities, and material/deformation properties.

### CK-PROD-012: Connected visible surface

The native generation path should produce a coherent renderable surface for
supported body plans without requiring a handcrafted base character mesh.

### CK-PROD-013: Runtime avatar package

Compilation must produce a bounded runtime representation suitable for loading
by a game or engine adapter.

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
the same semantic runtime contract, with explicit capability levels when full
conformance is unavailable.

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
- external mesh conformance level for an initial release.

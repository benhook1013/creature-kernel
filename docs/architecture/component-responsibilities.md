# Component responsibilities

Status: Proposed responsibility map

These are conceptual boundaries, not approved packages or technologies. Code
directories should be created only after the relevant boundary is accepted and
its activation trigger is met.

| Component | Responsibilities | Explicit non-responsibilities |
| --- | --- | --- |
| Authoritative semantic source set | Admit one initial strict UTF-8 JSON document, preserve authored intent, track exact revisions of outcome-affecting authored dependencies, classify extensions, report source errors, and provide the sole authored authority | Generate meshes or run gameplay, or treat an external mesh as semantic truth |
| Semantic body resolver | Run resource/input, syntax/schema/contract, dependency, namespace/identity/reference, ownership/relation, normalization/derivation, invariant, and publication phases inside one authoritative operation-result envelope; only valid-supported input yields an optional compilable inspectable per-build graph snapshot with typed concepts, directed Joint endpoints, declared frames, resolved transforms, provenance, intent/lineage, and structured diagnostics | Host-engine objects, become an authored source, or make derived artifacts authoritative; rejected partial graphs are non-compilable, debug-only, and non-contractual |
| Geometry field system | Evaluate part volumes, composition, semantic fields | Choose runtime animation |
| Surface compiler | Extract, repair, remesh, simplify, and attribute visible surfaces | Define semantic truth |
| Rigging compiler | Generate joints, limits, skinning, correctives, and bindings | Own interaction intent |
| Physics compiler | Generate collision, mass, cages, and regional simulation data | Run unbounded render-mesh physics |
| Appearance compiler | Produce semantic material inputs and generated attachments | Require unique painted textures |
| Avatar packager | Validate and serialize the derived hybrid runtime package with artifact/build identity and provenance | Redefine source semantics or durable semantic identity |
| Embodiment runtime | Coordinate bounded pose, IK, contact, parameterized deformation, activated regional solvers, quality tiers, and fallbacks | Compile arbitrary topology every frame or require fully live implicit generation |
| Interaction system | Resolve semantic participants, phases, constraints, and fallbacks through queryable capabilities and regions | Depend on exact mesh identities or treat capability implementation as semantic contract |
| Shared domain operations and adapters | Define deterministic query, semantic mutation, resolution/compilation, validation, diagnostics, and artifact inspection for CLI/API and future adapters | Contain AI-specific reasoning or private client behaviour |
| Validation system | Produce structural, semantic, geometric, visual, and performance evidence, including invalid/unsupported-assembly diagnostics in the shared result envelope | Declare product decisions automatically or silently choose among conflicting constraints |
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

The semantic resolver preserves the typed vocabulary: Part is structural and
owned; Joint is an articulation relation with frames; Socket is a host interface
frame; Attachment maps a module to a socket and is not automatically a joint;
Region is an overlapping spatial designation, never ownership; Capability is a
queryable affordance; and Field carries representation-neutral spatial intent
and lineage. Transforms own reference-frame placement, dimensions own extents,
anchors/landmarks carry authored or derived provenance, ratios are derived, and
conflicting constraints become diagnostics. Source-declared units,
handedness, up, and forward are converted to a contract-revision canonical
basis with provenance; local/reference, joint, socket/mating, derived
world/reference, and runtime-pose frames remain distinct.

The graph contract makes the typing executable at the boundary: Joint is
directed with exactly one proximal and one distal Part and endpoint frames
relative to each; Socket is Part-owned; Attachment has one host Socket and one
mating Socket and does not imply articulation. Module is authored reusable
scope, not an embodied graph concept. Landmark, anchor, dimension, and frame
are typed owner+role records. Claims compare after normalization by owner
address, property role, and frame/context; authored claims and explicit
invariants must be jointly satisfiable, derived/defaulted values cannot
override authored claims, and conflict is semantic-invalid with no success
snapshot.

Resolver implementation must stop dependent phases after a fatal failure while
accumulating independent diagnostics within a phase. Required unresolved or
ambiguous values cannot succeed. Machine diagnostic identity and order are
stable contract data; human messages are not compatibility keys. Finite
implementation-profile limits cover source and aggregate bytes, string
lengths/counts, nesting depth, object/array members, graph entities/relations,
ownership depth, module/reference expansion, extension count/payload, numeric
admissibility, diagnostics, and aggregate work/memory, without selecting
numeric limits here.

## Walking-skeleton exploratory seam (provisional and disposable)

The first executable slice may use the following project-owned conceptual
boundaries inside the disposable discovery host:

| Exploratory boundary | Bounded responsibility | Status and limits |
| --- | --- | --- |
| Body resolution | Turn temporary input into a bounded resolved semantic graph and graph snapshot | Provisional and disposable; not a body-document or body-graph contract |
| Field evaluation | Evaluate analytic capsule/ellipsoid volumes, rigid transforms, and the deterministic union/smooth blend on a fixed dense grid | Provisional exploration only; no permanent field or topology representation |
| Surface extraction | Convert the sampled field into one visible debug mesh with marching cubes and retain source-region attribution | Provisional exploration only; no production surface architecture or mesh contract |
| Mesh validation | Emit structured validation and mesh diagnostics for valid and intentionally invalid fixtures | Diagnostic exploration only; does not declare product acceptance or a Stage 1 gate |
| Artifact writing | Write the graph snapshot, provisional debug mesh, semantic-region data, diagnostics JSON, and build/provenance identity | Provisional artifact plumbing; exact CLI, file, schema, and preview formats remain reversible |

NumPy, scikit-image, and trimesh types must remain internal to these disposable
adapters rather than becoming semantic graph or public artifact contracts. No
implementation package or directory is implied, and a later Rust, C++,
OpenVDB, GPU, or engine implementation must remain replaceable in principle.

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

Package lifecycle and reload behaviour should distinguish in-place compatible
parameter updates from structural recompilation. Initial preview reload may
block within the same session; future asynchronous swapping must define
replacement compatibility rather than assuming stable topology indices or
transient solver state.

# Component responsibilities

Status: Proposed responsibility map

These are conceptual boundaries, not approved packages or technologies. Code
directories should be created only after the relevant boundary is accepted and
its activation trigger is met.

The CK-KICK-012 Batch 6 resolutions are discussion-approved and represented as
Proposed responsibility consequences. DR-0002 Revision 8, DR-0008 Revision 8,
DR-0011 Revision 4, and DR-0012 Revision 3 are Proposed with Owner approval
Pending and current Double review Pending. The CK-KICK-012 Batch 5 review is
stale historical evidence. Proposed DR-0013 Revision 1 likewise records the
discussion-approved Rust-first platform direction with Owner approval Pending
and current Double review Pending; no acceptance or implementation package is
implied.

| Component | Responsibilities | Explicit non-responsibilities |
| --- | --- | --- |
| Authoritative semantic source set | Admit the initial strict UTF-8 JSON source through the bootstrap and resource rules in the [body-document contract](../../spec/body-document/README.md), preserve authored intent, track exact revisions of outcome-affecting authored dependencies, classify extensions, report one result envelope, and provide the sole authored authority | Generate meshes or run gameplay, or treat an external mesh as semantic truth |
| Semantic body resolver | Execute the canonical admission, bootstrap, dependency, explicit-containment/typed-relation, normalization, invariant, and publication boundaries inside one result envelope; only complete valid-supported input yields an optional compilable inspectable graph snapshot with canonical Joint/Socket frame records and provenance | Host-engine objects, become an authored source, or make derived artifacts authoritative; rejected partial graphs are non-compilable, debug-only, and non-contractual |
| Proposed Rust compiler core | Own the engine-independent production semantic/compiler library boundary and coordinate replaceable geometry evaluation; Stage 1's in-process CPU dense-field evaluator/extractor is the proposed first path | Lock a permanent geometry library, require a daemon/service, or make Rust a forever-only backend promise; no package is activated before DR-0013 acceptance |
| Proposed thin CLI and artifact boundary | Expose the compiler library through a thin headless CLI and write ordinary versioned artifacts plus a manifest for independent filesystem consumers | Become a visual workbench, settle final avatar-package serialization/compatibility, or require a service transport |
| Independent visual workbench | Consume compiler artifacts and manifests from the filesystem for visual inspection, evidence/render tooling, and disposable workflows | Become a production compiler dependency or silently redefine semantic/artifact contracts |
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

The resolver consumes the typed vocabulary and explicit containment rules in
the [body-graph contract](../../spec/body-graph/README.md): every Part has one
root path, containment supplies transform inheritance, relation traversal does
not repair containment, and containment/relation cycle checks are independent.
The graph handoff exposes directed Joints with canonical proximal/distal frame
records in the corresponding Part-local bases and Part-owned Sockets with
interface-frame records. A mating Socket may be descendant-owned; its frame is
composed through the module-root containment path before Attachment alignment,
which yields the attached root's sole child-local containment placement.
Descendants inherit only through containment, and repeated endpoint pairs,
host Socket reuse, zero incoming for a present root, and multiple incoming are
separate cardinality errors. Attachment composition remains semantic data,
never an implied Joint or runtime rig.

Resolver implementation follows the body-document contract's closed statuses,
precedence, deterministic diagnostic key, phase blocking, and bounded
streaming/token-aware resource guards. Trust loss precedes configured
resource-limit when completeness is lost, then earliest fatal phase, with
invalid-source ahead of unsupported within that phase. Required unresolved or
ambiguous values cannot succeed; exact serialized names, profile values, and
implementation technology remain outside this responsibility map.

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

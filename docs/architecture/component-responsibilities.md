# Component responsibilities

Status: Proposed responsibility map

These are conceptual boundaries, not approved packages or technologies. Code
directories should be created only after the relevant boundary is accepted and
its activation trigger is met.

The CK-KICK-012 Batch 6/7/8/9 resolutions are discussion-approved and represented
as Proposed responsibility consequences. The current six-record set is
DR-0002 Revision 11, DR-0006 Revision 5, DR-0008 Revision 11, DR-0011
Revision 7, DR-0012 Revision 6, and Proposed DR-0013 Revision 4. All six remain
Proposed with Owner approval Pending and Review Pending. The prior current
Double review is stale after Batch 9; its evidence is preserved from commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`. Its seven consolidated findings
are historical evidence and were resolved by Batch 9 discussion; they are not
awaiting discussion. A fresh current-revision Double review of all six records
is required before owner disposition. No acceptance or implementation package
is implied.

| Component | Responsibilities | Explicit non-responsibilities |
| --- | --- | --- |
| Authoritative semantic source set | Admit the initial strict UTF-8 JSON source through the bootstrap and resource rules in the [body-document contract](../../spec/body-document/README.md), preserve authored intent, track exact revisions of outcome-affecting authored dependencies, classify extensions, report one result envelope, and provide the sole authored authority | Generate meshes or run gameplay, or treat an external mesh as semantic truth |
| Semantic body resolver | Execute the canonical admission, bootstrap, dependency, explicit-containment/typed-relation, normalization, invariant, and in-memory snapshot-finalization boundaries inside one result envelope; successful `resolve` yields the required compilable inspectable graph snapshot with canonical Joint/Socket frame records and provenance | Host-engine objects, become an authored source, serialize or publish filesystem artifacts, or make derived artifacts authoritative; rejected partial graphs are non-compilable, debug-only, and non-contractual |
| Proposed Rust compiler core | Own the engine-independent production semantic/compiler library boundary, versioned project-owned GeometryRequest/GeometryResult concepts, and coordinate replaceable geometry evaluation; Stage 1's in-process CPU dense-field evaluator/extractor is the proposed first path | Leak backend-native types, lock a permanent geometry library/surface, claim DR-0009/0010 evidence, require a daemon/service, or make Rust a forever-only backend promise; acceptance of DR-0013 alone activates only the empty shell, while exact schema/admitted fixtures gate parser/resolver work |
| Proposed thin CLI and artifact boundary | Expose the compiler library through a thin headless CLI; delegate the public derived-output and publication contract to the [build-operation specification](../../spec/build-operation/README.md), carrying geometry and publication through one authoritative build envelope. The proposed boundary uses immutable build-scoped sibling staging, manifest-last atomic no-replace, and independent validation of build/artifact identity, paths, hashes, and sizes; trusted derived-output/publication failures normalize as `output-failure`. | Become a visual workbench, settle final avatar-package serialization/compatibility, publish symlinked/unlisted/incomplete/mixed/stale bundles, replace an existing target, or require a service transport |
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
Absent optional module declarations retain a stable authored declaration address
and non-embodied root-role/template reference, emit no Part, reserve no Part
identity, and cannot be relation targets; a later present root derives its Part
identity from the module-instance anchor and root role. This is declaration
identity, not an eighth embodied graph concept.
The graph handoff exposes directed Joints with canonical proximal/distal frame
records in the corresponding Part-local bases and Part-owned Sockets with
interface-frame records. A mating Socket may be descendant-owned; its frame is
composed through the module-root containment path before Attachment alignment,
which yields the attached root's sole child-local containment placement. Each
Socket has total active capacity one across host and mating roles, so cross-role
reuse is invalid. Every transform entering Attachment composition is finite,
non-degenerate, and invertible under the declared profile; a source violation
is `invalid-source`, while an implementation failure on an admissible transform
is `internal-failure`. Exact conditioning and tolerance remain deferred to
resolver activation.
Descendants inherit only through containment, and repeated endpoint pairs,
host Socket reuse, mating Socket reuse by distinct active Attachments (including
distinct hosts or nested attached roots), zero incoming for a present root, and
multiple incoming are separate cardinality errors. Mating Socket reuse has its
own deterministic diagnostic concept. Attachment composition remains semantic
data, never an implied Joint or runtime rig, and follows the typed transform
equation in the graph contract without freezing matrix layout or serialization.

Resolver implementation follows the body-document contract's closed statuses,
precedence, deterministic diagnostic key, phase blocking, and bounded
streaming/token-aware resource guards. Complete acquisition is required before
invalid-source; internal trust loss precedes a qualifying resource-limit, then
the earliest applicable phase unable to produce its required output. In a
mixed dependency phase, dependency-failure precedes invalid-source and then
unsupported; parse/semantic invalid-source precedes unsupported. All mandatory
independent checks capable of changing status or primary run unless resource
or trust interruption prevents them. Processing is complete when all work
applicable to establishing/trusting the selected outcome ran; blocked phases
are inapplicable. Diagnostic completeness concerns retention of all applicable
profile-required diagnostics; ordinary truncation alone is not resource-limit,
and optional checks cannot change status or primary. Required unresolved or ambiguous values cannot succeed; exact
serialized names, profile values, and implementation technology remain outside
this responsibility map. Resolver phase 8 is an in-memory snapshot handoff;
filesystem serialization and publication are owned by the linked
build-operation specification.

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

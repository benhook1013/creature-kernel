# DR-0013: First production implementation platform and geometry boundary

ID: DR-0013

Scope: Specification and architecture

Status: Proposed

Revision: 4

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-12

Supersedes: —

Superseded by: —

## Context

Creature Kernel is moving from disposable geometry exploration toward a first
production semantic/compiler core. The CK-KICK-012 body-document and body-graph
proposals define an engine-independent semantic boundary, but they do not
select an implementation language, build system, geometry backend, process
model, or visual workbench. The exploratory host in CK-KICK-009 and the
CK-KICK-010 walking skeleton are evidence and tooling, not production platform
commitments.

The first platform must make the semantic contract executable, headless, and
reproducible without turning an exploratory visual tool or a game engine into a
hidden compiler dependency. It must also leave a credible path for geometry
capabilities that may not fit the first implementation language. Stage 1 needs
an executable geometry proof, but that proof must not silently settle the
permanent surface, topology, or runtime architecture.

The build operation, artifact staging, inspection, and publication boundary
requires a canonical build-operation specification. The canonical
`spec/build-operation/README.md` owns the exact Proposed build-operation
contract, including field spelling and format. This record assigns the
operation and publication responsibilities without inventing that canonical
serialized contract. DR-0006 owns candidate versus committed artifact
identity and lineage at the identity level.

## Decision

This is a proposed first-production platform boundary. Readiness 1 through
Readiness 4 below are technical gates, not approval ceremonies. They state the
conceptual owner, authoritative prerequisite, and evidence; exact ledger field
spelling may remain in project documentation. No Readiness gate is activated by this
Proposed record.

| Readiness stage | Sole trigger and technical action | Authoritative prerequisite/owner | Evidence concept |
| --- | --- | --- | --- |
| Readiness 1 — empty production shell | DR-0013 is Accepted; create the Cargo workspace and empty compiler/library/CLI shell | DR-0013 acceptance and this platform boundary | Workspace and empty shell exist; no parser, resolver, fixture, or geometry implementation is implied |
| Readiness 2 — parser/bootstrap and admitted fixtures | One exact activation transaction on a review branch containing the exact JSON Schema, a versioned fixture manifest, all referenced fixture files, and parser/bootstrap implementation | DR-0012 owns schema/bootstrap; DR-0002/DR-0008/DR-0011 own linked semantic fixture obligations; Ben owns admission | Parser-independent preflight proves manifest, paths, hashes, profiles, expected outcomes/diagnostics, provenance, and completeness agree before explicit Ben approval and merge/activation |
| Readiness 3 — semantic resolver and snapshot handoff | Canonical basis/units/rotation/scale-shear/numeric representation/tolerances plus frozen expected graph outputs; activate semantic resolution and successful in-memory snapshot finalization/handoff | DR-0011 owns frame/numeric prerequisites; DR-0002/DR-0012 own graph and result-envelope obligations | Resolver outputs match frozen expected graph snapshots with provenance and trusted success envelope; external serialization remains a later build/output operation |
| Readiness 4 — exploratory Stage 1 geometry proof | Working resolver plus a provisional geometry profile and project-owned GeometryRequest/GeometryResult seam; activate exploratory Stage 1 geometry proof / CK-KICK-014 | DR-0013 owns the seam/platform; DR-0008 owns Stage 1 claim boundary | Bounded exploratory proof evidence under the provisional profile; no accepted/reactivated surface decision is required |

Readiness 2 admission is one exact activation transaction on a review branch:
the schema, a versioned manifest, every referenced fixture file, and the
parser/bootstrap implementation may coexist there, but merge or activation
occurs only as one transaction. Ben is the admission owner and must explicitly
approve before merge/activation. A generic/parser-independent preflight checks
paths, hashes, profile references, expected status and primary diagnostics,
provenance, and completeness. The manifest requires an immutable revision/ID,
schema revision/hash, fixture paths/hashes/provenance, expected status and
primary diagnostic, diagnostic/resource profile IDs, and completeness. The
production parser must not self-admit the corpus circularly.

Acceptance of DR-0013 itself is the sole trigger for Readiness 1. Creating this
Proposed DR does not activate implementation packages, schemas, compiler
fixtures, or a production geometry commitment. Readiness 2 creates its
manifest-listed fixture files and parser/bootstrap implementation together in
the one admitted transaction; neither first compiler consumption nor an
unlisted fixture can activate it. Readiness 3 is separate from
parser/bootstrap and requires canonical frame/numeric rules plus frozen
expected graph outputs; successful `resolve` requires the in-memory snapshot
handoff, while external serialization remains a build/output concern.
Readiness 4 triggers exploratory Stage 1 geometry / CK-KICK-014. It does not
require acceptance or reactivation of parked DR-0009/DR-0010; those records
remain nonblocking and are needed only for later formal comparative surface
evidence or production architecture selection. The exploratory proof itself
requires no surface decision.

### Core language and workspace

Use stable Rust as the first production semantic/compiler core in a Cargo
workspace. The core is a library with engine-independent semantic resolution,
diagnostics, provenance, and artifact production boundaries. A thin CLI is the
first human/script entry point. The core and CLI must not require a game engine
or a visual workbench to perform headless compilation.

The initial implementation should keep public boundaries ordinary and
replaceable: semantic/compiler library, thin CLI, artifact/manifest writer,
and a replaceable geometry boundary. This record does not fix crate names,
public API syntax, source schema files, artifact field spelling, or package
serialization. No daemon or service is part of the first implementation.

### Geometry boundary and first proof

The project-owned geometry seam consists of versioned `GeometryRequest` and
`GeometryResult` concepts (names remain conceptual/provisional). The request
and result cover resolved graph and geometry intent, configuration and
capability metadata, semantic/artifact lineage, bounded diagnostics, and
bounded geometry outputs/results sufficient for the caller to validate the
operation. Backend-native or third-party library types must not leak through
the semantic, CLI, artifact, or host-engine contracts. The seam is a
replaceable project boundary, not a permanent surface or backend selection.
Stage 1 seam work may support CK-KICK-014, but it does not establish a
permanent surface choice and cannot claim DR-0009 or DR-0010 evidence.

Stage 1 geometry proof uses an in-process Rust CPU dense-field evaluator and
extractor behind the replaceable geometry boundary. This is a bounded proof
host, not a claim that Rust geometry is universally mature or that the chosen
dense-field/extraction method is the permanent surface architecture. It must
remain possible to compare or replace the geometry implementation without
rewriting semantic resolution or the CLI contract.

Rust-only geometry is not a permanent promise. If reproducible measurements, a
required capability, or a justified isolation, security, portability, or
licensing need exposes a credible in-process Rust boundary gap, evaluate an
isolated C++ worker/backend first. Consider in-process C ABI/FFI only if the
worker boundary is demonstrated insufficient for the required use. Any such
change requires evidence, a defined ownership and failure boundary, and the
appropriate later decision; it is not implied by this DR.

### Tooling and workbench

Python remains suitable for disposable experiments, evidence and render
tooling, and the visual workbench. Python is not a production compiler
dependency. An independent visual workbench consumes ordinary compiler
artifacts and their manifest; it does not own semantic resolution or silently
recompile the source through a second implementation.

The compiler publishes a complete success or failure bundle using immutable,
build-scoped sibling staging, writes the manifest last, and atomically
publishes it with no replacement of an existing bundle. The manifest identifies
the build and artifact identity and records relative paths with hashes and
sizes. Consumers reject absolute or traversal paths, symlinked or unlisted
outputs, incomplete or mixed-build bundles, and stale bundles. These artifacts
are an initial inspection and workbench interchange boundary, not the final
avatar-package serialization or compatibility contract. Exact artifact names,
manifest field spelling, package bytes, and compatibility rules remain
deferred to later specification and decision work.

Any future isolated worker must negotiate protocol/version compatibility, obey
bounded time and resource budgets, map crash/timeout/resource outcomes, have
its outputs validated before publication, and leave the compiler process
surviving worker failure. Detailed worker serialization remains deferred.

### Authoritative build operation and publication

Geometry execution and artifact publication are explicit phases or suboperations
of one authoritative public `build` operation. The operation-result envelope is
the sole public status/diagnostic authority; backend, worker, geometry, and
publisher diagnostics are normalized into it and never become competing status
channels. The public status vocabulary is closed and includes `output-failure`
for a derived-output or artifact-publication failure after accepted input and
semantic work, when result trust is not lost and no higher-priority internal or
resource failure applies. Precedence is global internal trust loss, then a
qualifying resource-limit, then the earliest applicable phase unable to produce
its required output, with same-phase rules inherited from DR-0002/DR-0012.
This is the public build-envelope vocabulary: the initial semantic resolver
outcomes remain owned by DR-0012, while this build boundary adds the derived-
output `output-failure` outcome.
Geometry, output encoding, staging, and publication failures map to
`output-failure` unless source-caused semantic invalidity, worker resource
failure, internal trust loss, or another higher/earlier outcome already
determines the result.

A canonical build-operation specification is required before this boundary is
implemented; the canonical `spec/build-operation/README.md` owns its exact
Proposed operation schema, field spelling, and format. At this conceptual
boundary, a staging manifest carries a
non-authoritative candidate artifact identity. The output target is derived
deterministically from the explicit output root and that candidate identity;
exact spelling belongs to the canonical specification. Successful atomic
publication promotes the same candidate identity to committed artifact
identity, as owned at the identity level by DR-0006.

A verified identical existing target—matching identity, lineage, manifest, and
hashes—is idempotent already-published success. A different or unverifiable
occupant is an `output-failure` target-conflict and is never replaced. If the
platform cannot provide the required atomic no-replace publication primitive,
the operation fails as `output-failure`; it does not adopt or overwrite a
target. Cleanup removes only invocation-owned staging. Artifact inspection is
given expected build/artifact lineage and validates against it; it does not
guess or silently accept stale state.

A build/operation identity always exists, including failure. A committed
artifact identity exists only for a successfully published artifact or bundle.
A compile or geometry failure may publish a diagnostics-only failure bundle when
publication succeeds, but that bundle is trusted only when its
publisher/reporter remains independently trusted from the failed component.
Otherwise only the reserved CLI/API envelope may report the failure. If
publication itself fails, the authoritative envelope is returned through the
CLI/API and no final bundle exists; the operation cannot promise to publish its
own failure bundle. Preserve the root diagnostic even when top-level status is
normalized.

The complete build outcome contract must cover source, dependency,
capability/protocol, timeout/resource, worker crash, malformed output,
invariant loss, encoding, staging, collision, and publication failures. These
are normalized into the one authoritative build envelope with precedence
inherited from DR-0002/DR-0012; resolver in-memory snapshot handoff is not
external serialization, and filesystem serialization/publication failures map
to `output-failure` here.

Domain operations remain separate in general, but the first public `build` path
uses one envelope across semantic resolution, geometry, and publication.
Artifact inspection remains a separate read operation and does not create a
second build-status channel.

Two future activation obligations remain nonblocking: before an isolated worker
activates, define containment, process-tree, output/log/handle/network/protocol/
cleanup/status bounds appropriate to its threat model; before evidence-bearing
portability or performance claims, freeze the lightweight exact build/reference
environment and dependency source/feature inputs, with native smoke preceding
native portability claims.

### First reproducible execution target

Use ordinary `rust-toolchain.toml` for exact toolchain selection and commit
`Cargo.lock`. Record the initial target triple, build profile, `rustc -Vv`, and
reference-environment metadata with each reproducible build. The first
reference path is WSL2 x86_64 GNU; a native-Linux
portability smoke follows later as stated by the design. Native Windows
execution and host-engine integration are later activation targets, not
first-platform requirements. The target does not prohibit later support for
other operating systems, architectures, or engines.

When a dependency is added, perform a lightweight review of its license,
unsafe or native code, and portability/security relevance. This does not
require Git commit pinning, an enterprise audit trail, or heavyweight
dependency bureaucracy.

### Performance and rationale

No performance claim follows from this platform choice without a reproducible
benchmark and recorded hardware profile. Rust is selected for memory and type
safety, deterministic headless tooling, a practical CLI/core throughput path,
and a credible bounded CPU proof for Stage 1. The selection is not based on an
assertion that advanced Rust geometry is universally mature, nor does it
prejudge a later geometry worker/backend.

## Consequences

- The first production semantic/compiler path has one reproducible stable-Rust
  implementation and a Cargo workspace once DR-0013 is accepted, while the
  semantic boundary remains engine-independent; exact schema and admitted
  fixtures still gate Readiness 2 parser/resolver work.
- A library plus thin CLI supports headless use and keeps visual tooling from
  becoming a compiler dependency; no daemon or service lifecycle is required
  for the first implementation.
- Stage 1 can produce bounded CPU geometry evidence in-process, while the
  versioned project-owned GeometryRequest/GeometryResult seam preserves a
  replaceable path to an isolated C++ worker/backend if a measured capability,
  performance, isolation, security, portability, or licensing need appears.
  The seam does not select a permanent surface or create DR-0009/DR-0010
  evidence.
- Python exploratory and visual tooling can continue without silently defining
  production semantics or compiler dependencies.
- A canonical build-operation specification is a prerequisite for exact
  operation fields and serialization. Immutable build-scoped sibling staging,
  manifest-last atomic no-replace publication, candidate-to-committed identity
  promotion, and manifest path/hash/size validation let the workbench reject
  incomplete, mixed, stale, symlinked, or path-escaping bundles. A verified
  identical target is idempotent already-published success; a different or
  unverifiable occupant is an unreplaced `target-conflict` output failure.
  This remains an initial interchange boundary and does not establish final
  avatar-package serialization or compatibility rules.
- A committed Cargo.lock, exact rust-toolchain.toml selection, recorded target,
  profile, rustc/reference metadata, and lightweight dependency review make
  the first WSL2 x86_64 GNU path reproducible without heavyweight
  audit policy. Portability, native Windows, and engine integration remain
  later work.
- Rust's safety and tooling rationale is testable, but every performance claim
  remains subject to reproducible benchmark and hardware evidence.
- A future worker must negotiate protocol/version compatibility, obey bounded
  time/resource limits, map crash/timeout/resource outcomes, validate outputs,
  and preserve compiler-process survival; its detailed serialization remains
  deferred.
- Readiness 1 through Readiness 4 make activation auditable: acceptance creates
  only the empty shell; one Ben-approved transaction containing the schema,
  versioned manifest, referenced fixtures, and parser/bootstrap activates
  Readiness 2; canonical frame/numeric rules plus expected graph outputs
  activate resolver/in-memory snapshot handoff; and a working resolver plus
  provisional geometry profile activates exploratory Stage 1 geometry /
  CK-KICK-014. Parked DR-0009/0010 remain nonblocking and are needed only for
  later formal comparison or production architecture selection.
- Geometry and publication contribute to one authoritative public build
  envelope. `output-failure` covers trusted derived-output/publication failure
  after accepted input/semantic work, subject to internal/resource/earlier
  precedence. Build identity always exists; DR-0006 owns candidate versus
  committed artifact identity, with the same candidate promoted on successful
  publication. A diagnostics-only failure bundle is trusted only when its
  publisher/reporter remains independently trusted from the failed component;
  otherwise the reserved CLI/API envelope alone reports failure. Publication
  failure returns the envelope with no final bundle, preserves the root
  diagnostic, and cannot publish its own failure bundle. Invocation-owned
  staging is the only cleanup scope, and atomic no-replace publication fails
  closed when unsupported.
- The platform is reversible at the geometry boundary and at process/tooling
  boundaries, but a production compiler API and artifact lineage will create
  migration cost; a later change must preserve or explicitly migrate those
  contracts.

## Alternatives Considered

### C++ day one

C++ offers mature geometry and graphics libraries and may reduce friction for a
future geometry backend. It would also increase memory-safety and build
complexity in the first semantic/compiler path, and could encourage geometry
and engine concerns to leak across the semantic boundary. It remains the
strongest alternative if measurements or required geometry capabilities make
the bounded Rust proof inadequate; the isolated-worker trigger preserves that
option without making it an unmeasured first dependency.

### C#/.NET

C#/.NET provides strong tooling, libraries, and a comfortable CLI/application
ecosystem. It introduces a different runtime and deployment surface and does
not by itself resolve the engine-independent geometry boundary. It may become
appropriate for a later integration or workbench, but it is not selected for
the first semantic/compiler core.

### Production Python

Python minimizes iteration cost and reuses the exploratory host, but makes the
production compiler more dependent on interpreter and native-extension
environments and weakens the headless distribution boundary. Python remains
appropriate for disposable experiments, evidence/render tooling, and the
visual workbench.

### Rust-only permanent backend

Making Rust the permanent geometry backend would simplify one-language
ownership, but would turn the first platform choice into an unsupported
long-term capability claim. It is explicitly not selected; reproducible gap,
required capability, or justified isolation, security, portability, or
licensing need can trigger an isolated C++ worker/backend.

### Immediate in-process C++ FFI or hybrid

Immediate FFI could access mature libraries quickly, but couples the first
compiler process to native ABI, toolchain, memory-ownership, and failure-mode
details before a worker boundary is shown insufficient. The selected order is
in-process Rust proof, isolated C++ worker/backend if evidence requires it,
and in-process C ABI/FFI only if that worker boundary cannot satisfy the
required use.

### Daemon or service first

A daemon could support persistent sessions and remote workbenches, but adds
process lifecycle, protocol, deployment, and security contracts before the
semantic/compiler boundary is proven. The first implementation uses a library
and thin CLI; a service can be added later if reproducible workflow or
integration requirements justify it.

### Broader first-platform matrix

Supporting native Windows, multiple architectures, host engines, and several
workbench environments immediately would broaden portability testing and
integration cost before one reproducible proof exists. The Linux x86_64 target
is a first execution target, not a portability rejection; additional targets
activate when evidence and users justify them.

## Adversarial Review Response

This is CK-KICK-013 Revision 4, proposed and discussion-approved on 2026-08-12.
The exact Revision 1 Double review examined commit
`c64b1b98948304d631eecea6a354c9e42c89c510`. The independent [review 01](reviews/DR-0013-rev-01-review-01.md)
and [review 02](reviews/DR-0013-rev-01-review-02.md) both recommended **Revise**
at **High** confidence. Those exact reviews are stale historical evidence, not
a clean review or acceptance. Ben approved the F4–F7 resolutions in discussion
on 2026-08-11: DR acceptance is the sole shell-creation trigger; the
project-owned versioned GeometryRequest/GeometryResult seam is backend-neutral;
artifact publication and future worker failures are bounded and validated; and
the Rust/toolchain/dependency baseline and broadened isolation trigger are
lightweight and reproducible. Revision 3 records Ben's 2026-08-12 discussion
approval of five Recommendation 1 resolutions: the four ordered technical
readiness gates, authoritative build/publication outcome with `output-failure`,
and the linked status, module/Socket, and transform-contract consequences.
This discussion approval is not DR acceptance. The prior Revision 2 Double
review examined
target commit `88004388f9537a37617ae248bdaad4625e6f3f03` in [review 01](reviews/DR-0013-rev-02-review-01.md)
and [review 02](reviews/DR-0013-rev-02-review-02.md); both independent passes
recommended **Revise** at **High** confidence. The prior Review Complete state
records evidence rather than a clean review or acceptance. Those Revision 2
artifacts are now stale historical evidence after this proposal change. The
fresh current Double review of Revision 3 was complete at target commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`: [review 01](reviews/DR-0013-rev-03-review-01.md)
and [review 02](reviews/DR-0013-rev-03-review-02.md) both recommend **Revise**
at **High** confidence. The seven consolidated findings C1–C7 were findings of
that now-stale review; Ben resolved them in Batch 9 discussion. Applicable
consolidated findings were C1–C3 and C5–C7; C4 was owned by the linked semantic
records. Review completion is evidence, not a clean review or acceptance. This
record does not
claim owner acceptance, a production implementation, a permanent geometry
backend or surface architecture, a final artifact/package format, or a
performance result. Exact schema, fixture, and later evidence obligations
remain with their owning records. The prior `c64b1b...` review remains stale
historical evidence.

Those Revision 3 artifacts and findings are preserved as stale historical
evidence after the material Revision 4 change and do not satisfy the pending
current-revision review. Ben's Batch 9 resolutions assign DR-0013 the
canonical build-operation/publication boundary, Readiness 2 manifest admission,
candidate-target collision rules, trusted diagnostics-only reporting, and
Readiness 4's exploratory CK-KICK-014 trigger. Review status is Pending. Owner
approval remains Pending and Status remains Proposed. Only Ben may accept or
reject this proposal.

## Implementation and Proof Obligations

- If this DR is accepted, create only the Cargo workspace and empty
  compiler/library/CLI shell boundary; no second repository trigger or approval
  ceremony is required. Then enforce the readiness gates: exact JSON Schema
  plus a frozen/admitted fixture manifest activates creation of the
  manifest-listed fixture files and parser/bootstrap implementation together;
  canonical basis/units/rotation/scale-shear/numeric representation/tolerances
  plus frozen expected graph outputs activate semantic resolver and successful
  in-memory snapshot finalization/handoff; and a working resolver plus
  provisional geometry profile and project-owned seam activates exploratory
  Stage 1 geometry / CK-KICK-014. Readiness 2 is one Ben-approved transaction
  containing schema, versioned manifest, referenced fixtures, and
  parser/bootstrap; parser-independent preflight validates paths, hashes,
  profile references, expected status/primary diagnostics, provenance, and
  completeness. Production parsing must not self-admit the corpus.
  This Proposed record itself creates no packages, fixtures, parser, resolver,
  or geometry implementation. DR-0009/0010 remain parked and nonblocking.
- Keep semantic resolution, diagnostics, provenance, and the CLI independent
  of geometry implementation, visual workbench, and host engine.
- Define the project-owned versioned conceptual `GeometryRequest` and
  `GeometryResult` seam for resolved graph/geometry intent, configuration and
  capability metadata, lineage, bounded diagnostics, and bounded outputs.
  Keep backend-native types out of semantic, CLI, artifact, and host-engine
  contracts. Implement the Stage 1 in-process Rust CPU dense-field
  evaluator/extractor only after the relevant proof inputs and fixture
  obligations are activated by their owning records. Seam work may support
  CK-KICK-014 but cannot establish a permanent surface choice or claim
  DR-0009/DR-0010 evidence.
- Record reproducible build/toolchain, target, seed/configuration, and source
  provenance for every proof run. Do not report performance without a
  reproducible benchmark and hardware profile.
- Make geometry and artifact publication explicit phases/suboperations of one
  authoritative public `build` operation-result envelope, as specified by a
  separate canonical build-operation specification. Normalize backend, worker,
  geometry, and publisher diagnostics into that envelope; preserve root
  diagnostics even when status is normalized; and cover source, dependency,
  capability/protocol, timeout/resource, worker crash, malformed output,
  invariant loss, encoding, staging, collision, and publication failures.
  Add closed public status `output-failure` for trusted derived-output/
  publication failure after accepted input/semantic work, subject to
  internal/resource/earlier precedence. A staging manifest carries a
  non-authoritative candidate artifact ID; DR-0006 owns its promotion unchanged
  to committed identity on successful atomic publication. Derive the target
  from explicit output root plus candidate identity. A verified identical
  target (identity, lineage, manifest, hashes) is idempotent already-published
  success; a different or unverifiable occupant is `output-failure`
  `target-conflict` and is never replaced. If atomic no-replace is unavailable,
  fail closed with `output-failure` without adoption/overwrite. Artifact
  inspection receives expected build/artifact lineage and must not guess stale
  state. A diagnostics-only failure bundle is trusted only when its
  publisher/reporter remains independently trusted from the failed component;
  otherwise the reserved CLI/API envelope alone reports failure. Publication
  failure returns that envelope with no final bundle. Clean only
  invocation-owned staging. Defer final avatar-package serialization,
  exact primitive/platform mapping, and exact manifest/operation field spelling
  to the canonical specification.
- If reproducible measurements, a required capability, or a justified
  isolation, security, portability, or licensing need identifies a credible
  in-process Rust geometry gap, document it and evaluate an isolated C++
  worker/backend first. Require future worker protocol/version negotiation,
  bounded time/resources, crash/timeout/resource mapping, output validation,
  and compiler-process survival. Consider in-process C ABI/FFI only after
  evidence shows the worker boundary is insufficient; record resulting
  ownership, failure, portability, and licensing implications later. Worker
  serialization remains deferred.
- Use ordinary rust-toolchain.toml for exact toolchain selection, commit
  Cargo.lock, and record target triple, build profile, rustc -Vv, and
  reference-environment metadata. Establish WSL2 x86_64 GNU
  reference path first; perform native-Linux portability smoke later. When a
  dependency is added, review its license, unsafe/native code, and
  portability/security relevance without Git commit pinning, enterprise audit
  trail, or heavyweight process.
- Keep Python dependencies confined to disposable experiments, evidence/render
  tooling, and the visual workbench; prove that production headless compiler
  execution does not import them.

## Canonical Design Links

- [Architecture index](../architecture/README.md)
- [System overview](../architecture/system-overview.md)
- [Execution model](../architecture/execution-model.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Initial body-document encoding, resolution, and compatibility](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [Proposed build-operation contract](../../spec/build-operation/README.md)
- [Staged first-proof charter](DR-0007-staged-first-proof-charter.md)
- [First digitigrade morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)

## Reversibility and Revisit Triggers

Revisit the core platform if stable-Rust toolchain constraints prevent a
reproducible semantic/compiler workflow, if the Cargo/library boundary cannot
serve required consumers, or if portability evidence exposes an unjustified
target restriction. Revisit the in-process geometry boundary when reproducible
measurements, a required capability, or a justified isolation, security,
portability, or licensing need shows a credible boundary gap. Evaluate an
isolated C++ worker/backend before in-process FFI; choose FFI only if the
worker boundary is proven insufficient. Revisit the no-daemon choice if
persistent or remote workflows become an activated requirement. Revisit the
filesystem artifact/manifest handoff before final avatar-package persistence or
compatibility is promised. Native Windows and host-engine integration activate
only after their reproducibility and integration obligations are defined.

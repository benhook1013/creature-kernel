# DR-0013: First production implementation platform and geometry boundary

ID: DR-0013

Scope: Architecture

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-11

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

## Decision

This is a proposed first-production platform boundary. It becomes an
implementation trigger only if Ben accepts this DR and the existing
repository-evolution trigger is satisfied. Creating this Proposed DR does not
activate implementation packages, schemas, compiler fixtures, or a production
geometry commitment.

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

Stage 1 geometry proof uses an in-process Rust CPU dense-field evaluator and
extractor behind the replaceable geometry boundary. This is a bounded proof
host, not a claim that Rust geometry is universally mature or that the chosen
dense-field/extraction method is the permanent surface architecture. It must
remain possible to compare or replace the geometry implementation without
rewriting semantic resolution or the CLI contract.

Rust-only geometry is not a permanent promise. If reproducible measurements or
a required capability expose a credible Rust geometry gap, evaluate an
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

The compiler emits ordinary versioned filesystem artifacts plus a manifest.
Those artifacts are an initial inspection and workbench interchange boundary,
not the final avatar-package serialization or compatibility contract. Exact
artifact names, manifest fields, package bytes, and compatibility rules remain
deferred to later specification and decision work.

### First reproducible execution target

The first reproducible execution and workbench target is Linux x86_64, running
under WSL or native Linux. The implementation should preserve portability in
source and boundary design. Native Windows execution and host-engine
integration are later activation targets, not first-platform requirements.
The first target does not prohibit later support for other operating systems,
architectures, or engines.

### Performance and rationale

No performance claim follows from this platform choice without a reproducible
benchmark and recorded hardware profile. Rust is selected for memory and type
safety, deterministic headless tooling, a practical CLI/core throughput path,
and a credible bounded CPU proof for Stage 1. The selection is not based on an
assertion that advanced Rust geometry is universally mature, nor does it
prejudge a later geometry worker/backend.

## Consequences

- The first production semantic/compiler path has one reproducible stable-Rust
  implementation and a Cargo workspace, while the semantic boundary remains
  engine-independent.
- A library plus thin CLI supports headless use and keeps visual tooling from
  becoming a compiler dependency; no daemon or service lifecycle is required
  for the first implementation.
- Stage 1 can produce bounded CPU geometry evidence in-process, while the
  replaceable geometry boundary preserves a measured path to an isolated C++
  worker/backend if a credible Rust gap appears.
- Python exploratory and visual tooling can continue without silently defining
  production semantics or compiler dependencies.
- Filesystem artifacts and a manifest give the workbench a simple initial
  interchange boundary, but do not establish final avatar-package
  serialization, compatibility, or artifact identity rules.
- Linux x86_64 under WSL or native Linux narrows the first reproducible target;
  portability, native Windows, and engine integration remain later work.
- Rust's safety and tooling rationale is testable, but every performance claim
  remains subject to reproducible benchmark and hardware evidence.
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
long-term capability claim. It is explicitly not selected; reproducible gap or
required-capability evidence can trigger an isolated C++ worker/backend.

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

This is CK-KICK-013 Revision 1, proposed and discussion-approved on
2026-08-11. The current Revision 1 Double review examined commit
`c64b1b98948304d631eecea6a354c9e42c89c510`. The independent [review 01](reviews/DR-0013-rev-01-review-01.md)
and [review 02](reviews/DR-0013-rev-01-review-02.md) both recommend **Revise**
at **High** confidence. Review status is Complete, recording evidence only;
it is not acceptance or a clean review. This record does not claim owner
acceptance, a production implementation, a permanent geometry backend, a
final artifact/package format, or a performance result. The seven consolidated
findings are listed in the [decision registry](registry.md); DR-0013 is
affected by F4, F5, F6, and F7, pending Ben discussion and owner disposition.

The principal review obligations are to challenge the Rust and Cargo choice,
the sufficiency and portability of the Linux x86_64 first target, the
replaceable geometry and worker/FFI boundary, the artifact/manifest handoff,
the absence of a first daemon, and the reversibility and evidence triggers for
each alternative. Any material proposal change makes this revision's review
stale and requires a new revision before review.

## Implementation and Proof Obligations

- If this DR is accepted and repository-evolution activation is separately
  triggered, create the Rust/Cargo implementation only through the applicable
  repository workflow; this Proposed record itself creates no packages.
- Keep semantic resolution, diagnostics, provenance, and the CLI independent
  of geometry implementation, visual workbench, and host engine.
- Define the replaceable geometry boundary and implement the Stage 1 in-process
  Rust CPU dense-field evaluator/extractor only after the relevant proof inputs
  and fixture obligations are activated by their owning records.
- Record reproducible build/toolchain, target, seed/configuration, and source
  provenance for every proof run. Do not report performance without a
  reproducible benchmark and hardware profile.
- Emit ordinary versioned filesystem artifacts and a manifest sufficient for
  the independent workbench, while deferring final avatar-package
  serialization/compatibility and exact artifact identity rules.
- Preserve portability in the Rust/library and boundary design; verify the
  first target under WSL or native Linux x86_64 before activating native
  Windows or engine integration.
- If a reproducible measurement or required capability identifies a credible
  Rust geometry gap, document the gap and evaluate an isolated C++ worker or
  backend first. Consider in-process C ABI/FFI only after evidence shows the
  worker boundary is insufficient; record the resulting ownership, failure,
  portability, and licensing implications in the later decision.
- Keep Python dependencies confined to disposable experiments, evidence/render
  tooling, and the visual workbench; prove that production headless compiler
  execution does not import them.

## Canonical Design Links

- [Architecture index](../architecture/README.md)
- [System overview](../architecture/system-overview.md)
- [Execution model](../architecture/execution-model.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Initial body-document encoding, resolution, and compatibility](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [Staged first-proof charter](DR-0007-staged-first-proof-charter.md)
- [First digitigrade morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)

## Reversibility and Revisit Triggers

Revisit the core platform if stable-Rust toolchain constraints prevent a
reproducible semantic/compiler workflow, if the Cargo/library boundary cannot
serve required consumers, or if portability evidence exposes an unjustified
target restriction. Revisit the in-process geometry boundary when reproducible
measurements or a required capability show a credible Rust geometry gap.
Evaluate an isolated C++ worker/backend before in-process FFI; choose FFI only
if the worker boundary is proven insufficient. Revisit the no-daemon choice if
persistent or remote workflows become an activated requirement. Revisit the
filesystem artifact/manifest handoff before final avatar-package persistence or
compatibility is promised. Native Windows and host-engine integration activate
only after their reproducibility and integration obligations are defined.

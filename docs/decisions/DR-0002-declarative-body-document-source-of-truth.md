# DR-0002: Authoritative semantic source set and resolved body graph

ID: DR-0002

Scope: Specification and architecture

Status: Proposed

Revision: 6

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Discussion approval date: 2026-08-11

Supersedes: —

Superseded by: —

## Context

The project needs a durable place for authored intent while generating geometry,
rigging, collision, deformation, materials, packaging, and runtime state. An
incidental generated output cannot carry all of the construction intent needed
for regeneration, automation, validation, and interaction across body
variation. A single initial document is useful, but future explicit semantic
override layers may also be authored inputs.

Revision 1 described a single declarative body document. Revision 2 recorded the
broader source-set boundary and made the resolved semantic graph a per-build
derived snapshot. Revision 3 recorded the CK-KICK-012 Batch 1 source and graph
boundary. Revision 4 recorded its first review-resolution batch. Revision 5
recorded the CK-KICK-012 Batch 3 resolutions: one owner per source namespace
and one authoritative operation-result envelope. On 2026-08-11 Ben approved
the CK-KICK-012 Batch 4 source/model/snapshot boundary recorded here, with the
initial encoding, resolution phases, compatibility, extensions, diagnostics,
and resource-profile contract owned by new [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
This discussion approval is not DR acceptance: this revision remains Proposed
with Owner approval Pending until a current-revision review and Ben's owner
disposition are recorded. All earlier revisions and their reviews remain
historical evidence; the Revision 5 reviews, as well as earlier reviews, are
stale for this revision.

## Decision

Durable authored intent lives in an authoritative semantic source set. Every
outcome-affecting external authored asset is an exactly versioned dependency
of that source set. Initially the source set may be one
human-readable document; future explicit semantic override layers may also be
authored inputs. The source set alone is authored authority. An external mesh
is authored input, not semantic truth; its semantic mapping and exact
dependency revision are retained in source/build provenance. Conformance
details remain deferred.

A validated, inspectable, per-build semantic body-graph snapshot is derived
from the source set through resolution. Source text, the resolver's normalized
semantic model, and the resolved snapshot are distinct stages; neither the
normalized model nor the snapshot becomes authored authority. One
operation-result envelope is authoritative for every phase and diagnostic.
The phase sequence, provenance requirements, resource limits, extension
policy, and diagnostic fields are defined by [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The envelope owns the outcome status and deterministically ordered diagnostics.
It may contain an optional validated snapshot only for valid-supported success.
Diagnostics persisted inside a successful snapshot are a derived subset or
annotation, not a competing status channel.
Semantically invalid and well-formed-but-unsupported input must be
distinguished; a rejected partial graph may be
exposed only as explicitly non-compilable, non-contractual debug information.
Exact diagnostic field spelling, human text, and diagnostic codes remain later
specification detail under DR-0012.

Within each resolved source set, exactly one authoritative source owns each
source namespace. Every imported namespace must therefore be unique. A
namespace collision is invalid unless the import contains an explicit,
authored, deterministic, collision-free remap covering every semantic address
contributed under that imported namespace. Namespace ownership is never
implicit or shared. Exact import and remap syntax remains later specification
detail.

The snapshot contains source references, durable semantic nodes and relations,
declared local frames and resolved transforms, relevant intent and lineage, and
structured diagnostics. It is reproducible and build-scoped, but is not
authoritative and must not silently become a competing source. Mesh, rig,
collision, material, deformation, packaging, runtime, and other artifacts
remain further derived outputs.

The resolved graph supplies shared semantic lineage for derived mesh, rig,
collider, material, deformation, packaging, runtime-state, and other outputs.
Those outputs are derived and must not silently become competing sources of
truth. Part-to-Part ownership is the sole structural body-containment tree.
Declarative ownership of other concepts and typed records scopes identity and
lifecycle without adding structural body edges. Durable non-structural
semantic concepts may be reified and connected through multiple role-labelled
relations; later specification work owns permissible cycles, additional frame
placement, and multi-part region membership. The
selected Joint, Socket, and Attachment endpoint roles and cardinalities are
owned by DR-0008 and DR-0011; later specification work retains the deferred
cycle, additional-frame, and multi-part-region rules.

The initial source encoding and structural validation boundary are owned by
DR-0012. This record still defers override representation and
precedence/conflict rules, runtime mutation/recompilation, and external-mesh
conformance details. Durable semantic identity and separate artifact/build
identity are defined at the boundary in
[DR-0006](DR-0006-durable-semantic-and-artifact-identity.md).

## Consequences

- Generation, regeneration, diffing, shared operations, and deterministic
  testing receive authored inputs and a validated, inspectable resolved
  per-build snapshot.
- Semantic lineage remains distinct from generated outputs and can survive mesh
  replacement or remeshing.
- The graph boundary exposes enough semantic structure for inspection and
  diagnostics without making graph meaning depend on the selected encoding or
  structural-schema technology.
- Source-set representation, override policy, precedence, and migration policy
  become long-lived contracts, but remain deferred here.
- Edits made directly to derived output cannot silently become authored truth.
- Imported meshes require an explicitly linked or mapped authored-input path
  with an exact dependency revision in provenance.
- Invalid and unsupported inputs cannot publish an ordinary compilable graph;
  their result envelope remains deterministic and inspectable.
- Failures before semantic resolution remain in the same operation-result
  envelope rather than creating a second error/status protocol.
- A successful snapshot may retain useful diagnostics for inspection only as a
  derived persisted subset or annotation; consumers must use the envelope
  status as authority.
- Imported sources have an auditable namespace owner. Collisions either fail
  deterministically or use an authored remap that covers the full contribution
  of the imported namespace; no partial or implicit remap is valid.

## Alternatives Considered

### Generated output as source of truth

Works with conventional asset tools but loses authored construction intent and
makes semantic regeneration difficult.

### One fixed document forever

Keeps the initial representation simple, but prevents future explicit semantic
override layers from being authored inputs and would make later source needs an
implicit competing path.

### Fixed template mesh with morph parameters

Provides excellent topology correspondence but conflicts with the initial goal
of generating bodies without a handcrafted base mesh and limits topology change.

### Opaque procedural scene graph

Could generate bodies but would be difficult to diff, version, validate, and
operate through external tools.

### External authored assets outside the source set

This resembles conventional tool pipelines, but permits build output to change
through an unversioned second authored input and breaks the source set's
reproducibility boundary.

### External meshes as a peer semantic authority

This could preserve artist edits directly, but creates competing semantic
truth and requires conflict rules between a mesh and its semantic mapping.

### Publish a rejected partial graph as compilable output

This can expose more errors in one pass, but downstream consumers could treat
invalid or unsupported state as usable. A partial graph is therefore allowed
only as explicitly non-compilable, non-contractual debug information.

### Allow shared or implicitly merged namespace ownership

This would reduce import friction, but makes semantic-address ownership and
collision outcomes dependent on load order or hidden conventions. It is not
selected: one source owns each namespace, and collisions require an authored
deterministic remap covering the imported namespace's complete contribution.

### Fail without a structured result envelope

An exception-only boundary is simpler for one implementation but weakens
deterministic CLI/API diagnostics and makes invalid versus unsupported input
harder for external tools to distinguish.

### Use separate envelopes for loading, resolution, and compilation

Separate phase-specific error channels could mirror implementation stages, but
would make status precedence and diagnostic ordering ambiguous for clients. One
operation-result envelope is authoritative across all phases; DR-0012 fixes
the initial phase sequence, while exact diagnostic-code vocabulary remains
deferred.

### Learned latent representation

May generate varied shapes but is difficult to make deterministic, semantically
precise, editable, and compatible across model versions.

## Adversarial Review Response

The Revision 3 authority, identity, and compatibility review
([review 01](reviews/DR-0002-rev-03-review-01.md)), morphology, graph, and
graphics-system review ([review 02](reviews/DR-0002-rev-03-review-02.md)), the
Revision 4 reviews ([authority](reviews/DR-0002-rev-04-review-01.md),
[morphology](reviews/DR-0002-rev-04-review-02.md)), and the Revision 5 reviews
([contract](reviews/DR-0002-rev-05-review-01.md),
[graphics-system](reviews/DR-0002-rev-05-review-02.md)) remain preserved as
stale historical evidence.

The current Revision 6 Double review is Complete at commit
`7dba9346c91c59ff99f10b94630690bf732d6b28`: the fresh independent Sol-medium
contract/schema/security pass ([review 01](reviews/DR-0002-rev-06-review-01.md))
recommends **Revise** with **High** confidence, and the fresh independent
Sol-medium semantic-graph/graphics/runtime pass
([review 02](reviews/DR-0002-rev-06-review-02.md)) also recommends **Revise**
with **High** confidence.

Applicable findings are the envelope's unresolved outcome/status algebra,
precedence, primary diagnostic, truncation, and distinction between semantic
fixture taxonomy and parser/dependency/resource outcomes; contract-discriminator
and schema bootstrap ordering; and minimum hostile-input resource enforcement
(Review 01; its mechanical secondary-architecture wording finding was aligned
after review without changing this proposal). Review 02 additionally finds
optional-module structural insertion and socket-frame placement/conflict,
duplicate/cycle/detached validity; canonical Joint endpoint-frame owner, role,
basis, provenance, and equivalence; containment reachability separate from
relation traversal/cycles and transform inheritance; and overlapping
phase/outcome/diagnostic precedence. The latter graph rules are cross-DR
dependencies on DR-0008, DR-0011, and DR-0012. Classification and measurement
blockers are closed; articulation is only partially closed because frame and
Attachment gaps remain. Fixture-matrix and specialist obligations remain
nonblocking. Review Complete records evidence, not acceptance or a clean
review; Owner approval remains Pending and Status remains Proposed. The exact
dependency-revision meaning remains a nonblocking later obligation. Only Ben
may accept or reject this proposal.

## Implementation and Proof Obligations

- Specify the source-set, source-text, normalized-model, resolved-graph, and
  derived-output relationships, including source references, durable semantic
  nodes/relations, local frames, resolved transforms, intent/lineage, and
  structured diagnostics. Use DR-0012 for the initial encoding and resolution
  boundary.
- Define the one operation-result envelope across loading,
  syntax/schema/contract recognition, dependency and resource checks,
  semantic resolution, and invariant checks; specify status/category,
  deterministic diagnostic ordering, valid/supported snapshot conditions, and
  the non-contractual partial-graph debug boundary.
- Specify namespace ownership, imported-namespace collision detection, and the
  authored deterministic remap that must cover all semantic addresses
  contributed by an imported namespace.
- Define semantic identity separately from artifact/build identity under DR-0006.
- Build fixtures proving semantic lineage across shape variation and derived
  output changes.
- Define exact source-set dependency/version recording for outcome-affecting
  authored assets (the exact dependency-revision meaning remains a nonblocking
  later obligation), then define overrides, precedence/conflict rules, runtime
  mutation/recompilation, external-mesh mapping, and future migration before
  promising those contracts. The initial source encoding and structural
  validation boundary are owned by DR-0012.

## Canonical Design Links

- [Product requirements](../product/requirements.md)
- [System overview](../architecture/system-overview.md)
- [Specification boundary](../../spec/README.md)
- [Durable semantic and artifact identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [Initial body-document encoding, resolution, and compatibility](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)

## Reversibility and Revisit Triggers

Changing the source-set and resolved-graph relationship becomes expensive after
documents and tools exist. Revisit if authored inputs cannot express required
morphology, if derived output cannot preserve artist intent, or if a hybrid
asset model proves necessary through experiments. The initial encoding,
overrides, runtime mutation, and external-mesh conformance remain separately
revisitable under their owning records.

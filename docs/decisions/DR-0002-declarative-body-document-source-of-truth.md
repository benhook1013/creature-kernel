# DR-0002: Authoritative semantic source set and resolved body graph

ID: DR-0002

Scope: Specification and architecture

Status: Proposed

Revision: 7

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
and one authoritative operation-result envelope. Revision 6 recorded the
CK-KICK-012 Batch 4 source/model/snapshot boundary, with initial encoding,
resolution phases, compatibility, extensions, diagnostics, and resource-profile
work owned by [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
On 2026-08-11 Ben approved the CK-KICK-012 Batch 5 blocker-resolution
selections recorded in Revision 7: explicit containment and transform
inheritance, Attachment composition boundaries, canonical resolved relation
records, and the linked operation status/bootstrap/resource rules. This
discussion approval is not DR acceptance: this revision remains Proposed with
Owner approval Pending. Its required current-revision Double review is now
Complete, with findings pending Ben discussion; all earlier revisions and their
reviews remain historical evidence.

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
The phase sequence, closed status set, status mapping and precedence,
provenance requirements, resource limits, extension policy, and diagnostic
fields are defined by [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The envelope owns the outcome status and deterministically ordered diagnostics.
It may contain an optional validated snapshot only for valid-supported success.
Diagnostics persisted inside a successful snapshot are a derived subset or
annotation, not a competing status channel.
Semantically invalid and well-formed-but-unsupported input must be
distinguished; a rejected partial graph may be
exposed only as explicitly non-compilable, non-contractual debug information.
Diagnostics from an earlier reached phase remain available when a later phase
is blocked, but are marked incomplete; one primary diagnostic must match the
top-level status. Exact diagnostic field spelling, human text, and diagnostic
codes remain later specification detail under DR-0012.

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
Every embodied Part, including an optional module Part, has exactly one
containment path to the embodied root. Joint, Attachment, Region, and every
other typed relation cannot create or repair that path. Containment owns
reference-transform inheritance; containment reachability and containment
cycles are validated separately from typed-relation cycles. For the bounded
Stage 1 axial and limb grammar, required Joint edges connect the structural
parent Part to its immediate child Part. A module Attachment's host Part and
module-root child must agree with their separately declared containment, and
initially an attached module root has at most one incoming Attachment. All
embodied Parts must remain connected.

Declarative ownership of other concepts and typed records scopes identity and
lifecycle without adding structural body edges. Durable non-structural
semantic concepts may be reified and connected through multiple role-labelled
relations. The selected Joint, Socket, and Attachment endpoint roles,
placement, cardinalities, and canonical records are owned by DR-0008 and
DR-0011; later specification work retains only the explicitly deferred
additional relation/frame and multi-part-region details.

The normalized graph materializes canonical Joint proximal- and distal-frame
records and the canonical Socket interface-frame record, with source-reference
provenance retained. These records are semantic data, not a bone hierarchy,
solver, limits, rig, or runtime representation.

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
- Structural containment is independently auditable: every embodied Part has
  one root path, containment owns reference-transform inheritance, and typed
  relations neither substitute for nor repair containment.
- Attachment composition cannot hide a disconnected, multiply owned, or
  multiply attached module root; its host/mating placement and independently
  declared containment must agree before publication.
- The operation has one closed status vocabulary at the contract boundary,
  while exact diagnostic code spellings and profile values remain deferred.

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

### Derive containment from relations

Using Joint, Attachment, or arbitrary relation traversal to infer the body tree
would make root reachability depend on whichever relation kinds an
implementation happens to traverse. It would also make transform inheritance
ambiguous and allow a relation to repair a structurally disconnected Part.
The explicit Part containment tree is selected; relation traversal and
relation-cycle validation remain separate.

### Leave endpoint frames as source references or ambiguous records

Allowing a resolved Joint to merely refer to either source endpoint record
would permit competing owner, role, basis, and provenance interpretations in
downstream consumers. The resolved graph therefore materializes one canonical
proximal and distal typed record in the corresponding Part local basis; source
references feed that record but do not replace it.

### Leave diagnostics unbounded or implementation-defined

An unbounded diagnostic list can exhaust memory on hostile or highly invalid
input and produces non-reproducible truncation across implementations. A
bounded diagnostic arena, deterministic ordering, and reserved terminal
capacity preserve a trusted primary status and resource/truncation report.

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

The Revision 6 Double review is preserved as stale evidence at commit
`7dba9346c91c59ff99f10b94630690bf732d6b28`, with both independent passes
recommending **Revise** at **High** confidence. The current CK-KICK-012 Batch 5
Double review examined Revision 7 at commit
`a282dbabffd83afa4e62577086934d00f98e12c7`: the independent
[contract/schema/security pass](reviews/DR-0002-rev-07-review-01.md) recommended
**Revise** at **High** confidence, and the independent
[semantic-graph/graphics/runtime pass](reviews/DR-0002-rev-07-review-02.md) also
recommended **Revise** at **High** confidence.

The contract pass identifies the same-phase mixed-fatal-status and primary-
diagnostic-selection gap: after the existing internal/resource overrides, the
remaining same-phase fatal statuses are not totally ordered, and the primary is
not explicitly the first retained status-establishing diagnostic under the
normative order, including after truncation. The graph/runtime pass identifies
an Attachment composition gap:
descendant-owned mating Socket placement is not normatively composed back
through the module-root containment path or stated as the attached root's sole
child-local containment placement. It further identifies an unresolved
`at-most-one` versus `exactly-one` incoming Attachment rule, including host
Socket capacity/reuse and repeated endpoint-pair identity. These findings remain
pending Ben discussion and are not resolved here. DR-0012 owns the directly
linked status/bootstrap details; DR-0008 and DR-0011 own the linked morphology
and typed-vocabulary consequences. The exact dependency-revision meaning,
serialized field spellings and diagnostic codes, concrete resource thresholds,
canonical axes/units/rotation/scale/shear, canonical bytes/hashing, and fixture
evidence remain deferred. Review status is Complete; Owner approval remains
Pending and Status remains Proposed. Only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Specify the source-set, source-text, normalized-model, resolved-graph, and
  derived-output relationships, including source references, durable semantic
  nodes/relations, local frames, resolved transforms, intent/lineage, and
  structured diagnostics. Use DR-0012 for the initial encoding and resolution
  boundary.
- Define the one operation-result envelope across loading,
  syntax/schema/contract recognition, dependency and resource checks,
  semantic resolution, and invariant checks; use DR-0012's closed status set,
  phase precedence, primary-diagnostic rule, bounded ordering, incomplete
  markers, valid/supported snapshot conditions, and non-contractual
  partial-graph debug boundary.
- Prove separately that every embodied Part has exactly one containment path,
  that containment owns reference-transform inheritance, and that relation
  traversal cannot repair containment or change its cycle checks. For Stage 1,
  verify required Joint edges connect structural parents to immediate children
  and that attached module roots agree with separately declared containment.
- Preserve canonical resolved Joint endpoint and Socket interface records with
  source-reference provenance while keeping bones, solvers, limits, rigs, and
  runtime pose outside this graph boundary.
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

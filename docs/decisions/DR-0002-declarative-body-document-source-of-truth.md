# DR-0002: Authoritative semantic source set and resolved body graph

ID: DR-0002

Scope: Specification and architecture

Status: Proposed

Revision: 8

Decision owner: Ben

Owner approval: Pending

Review status: Pending

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
records, and the linked operation status/bootstrap/resource rules. The exact-
revision CK-KICK-012 Batch 5 Double review of Revision 7 is stale historical
evidence. Its three findings motivated the CK-KICK-012 Batch 6 resolutions in
this proposal set: this revision resolves the authoritative status/primary
diagnostic and descendant-owned Attachment composition/cardinality boundaries,
with linked detail in DR-0008, DR-0011, and DR-0012. This discussion approval is
not DR acceptance. Revision 8 remains Proposed with Owner approval Pending and
Review status Pending; its current-revision Double review is pending. All
earlier revisions and their reviews remain historical evidence.

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
top-level status. Final status selection retains internal-failure trust-loss
precedence, then configured resource-limit when completeness is lost, then the
earliest fatal reached phase. Within the selected earliest fatal phase,
invalid-source outranks unsupported when both are established; other ordinary
status choices retain their phase-specific mapping. The primary diagnostic is
the first diagnostic establishing the final status under the normative
deterministic diagnostic order. Reserved primary capacity preserves the
minimal matching candidate despite ordinary diagnostic truncation; when
diagnostic-arena exhaustion itself establishes resource-limit, its reserved
resource/truncation diagnostic follows the same final-status-primary rule.
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
Every embodied Part, including an optional module Part, has exactly one
containment path to the embodied root. Joint, Attachment, Region, and every
other typed relation cannot create or repair that path. Containment owns
reference-transform inheritance; containment reachability and containment
cycles are validated separately from typed-relation cycles. For the bounded
Stage 1 axial and limb grammar, required Joint edges connect the structural
parent Part to its immediate child Part. A module Attachment's host Part and
module-root child must agree with their separately declared containment. A
present attached module root has exactly one incoming active Attachment, while
an absent optional module has none; each host Socket has an initial capacity of
one active Attachment. Repeated endpoint pairs, host Socket reuse, zero
incoming Attachments for a present attached module root, and multiple incoming
Attachments are distinct rejected conditions. All embodied Parts must remain
connected.

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

An Attachment may use a mating Socket owned by any Part in the attached
module-root containment subtree. Its placement composes the module-root-to-
mating-Socket-owner containment transform with the mating Socket's owner-local
frame before inversion/alignment with the host Part/frame, host Socket, and
optional authored Attachment offset. The Attachment-derived result is the
attached root's sole resolved child-local containment placement relative to its
host parent. Descendants inherit placement only through containment; the
Attachment adds no parallel transform-inheritance path. Any competing authored
root-local placement is compared against that same canonical derived
child-local value within the later-defined tolerance. Provenance for every
source frame, containment transform, offset, and composition step remains in
the result.

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
  multiply attached module root; a present module root has exactly one incoming
  Attachment, an absent optional module has none, and each host Socket accepts
  one. Repeated endpoint pairs, host Socket reuse, zero incoming, and multiple
  incoming cases are distinct rejected conditions. A mating Socket owned by a
  descendant is composed through the module-root containment path, and the
  result is the root's sole child-local placement; descendants inherit only
  through containment. Competing authored root-local placement compares with
  that same canonical value and retains provenance for all inputs.
- The operation has one closed status vocabulary at the contract boundary,
  while final-status precedence and the status-establishing primary diagnostic
  are deterministic; exact diagnostic code spellings and profile values remain
  deferred.

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

### Resolve a descendant mating Socket without containment composition

Treating a mating Socket as if it were owned by the module root would lose the
descendant's authored local frame. Treating the Attachment as a second
transform-inheritance path would make descendants depend on attachment order
and could produce two placements. The selected rule composes the
module-root-to-Socket-owner containment transform with the owner-local Socket
frame, then resolves the root's sole child-local containment placement.

### Permit optional or reusable Attachment endpoints

An at-most-one rule or reusable host Socket would permit absent or multiply
attached module roots and make endpoint identity errors depend on traversal
order. The initial grammar instead requires exactly one incoming Attachment
for each present attached module root, none for an absent optional module, one
active Attachment per host Socket, and distinct rejection of repeated endpoint
pairs, host reuse, zero incoming, and multiple incoming cases.

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

### Leave final status and primary selection to implementation order

Without an explicit trust-loss/resource/phase precedence, a result could vary
when multiple fatal diagnostics are established in one phase. Without a
status-establishing primary rule and reserved matching capacity, ordinary
truncation could also leave a primary diagnostic that does not explain the
final status. The selected rules keep the envelope deterministic while
retaining phase-specific ordinary mappings.

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
recommending **Revise** at **High** confidence. The exact-revision CK-KICK-012 Batch 5
Double review examined Revision 7 at commit
`a282dbabffd83afa4e62577086934d00f98e12c7`: the independent
[contract/schema/security pass](reviews/DR-0002-rev-07-review-01.md) recommended
**Revise** at **High** confidence, and the independent
[semantic-graph/graphics/runtime pass](reviews/DR-0002-rev-07-review-02.md) also
recommended **Revise** at **High** confidence.

The three Batch 5 findings in those exact-revision reviews motivated the
current CK-KICK-012 Batch 6 proposal text and are resolved across the current
records. This revision resolves the final-status precedence and
status-establishing primary-diagnostic rule, and resolves the descendant-owned
mating Socket composition, sole root placement, and Attachment cardinality
rules; DR-0008 and DR-0011 carry the linked morphology and typed-vocabulary
consequences, while DR-0012 owns the detailed status/bootstrap/resource
boundary. The prior exact-revision review is stale historical evidence, not a
clean review or acceptance. The current Revision 8 Double review is pending.
The exact dependency-revision meaning, serialized field spellings and
diagnostic codes, concrete resource thresholds, canonical
axes/units/rotation/scale/shear, canonical bytes/hashing, and fixture evidence
remain deferred. Review status is Pending; Owner approval remains Pending and
Status remains Proposed. Only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Specify the source-set, source-text, normalized-model, resolved-graph, and
  derived-output relationships, including source references, durable semantic
  nodes/relations, local frames, resolved transforms, intent/lineage, and
  structured diagnostics. Use DR-0012 for the initial encoding and resolution
  boundary.
- Define the one operation-result envelope across loading,
  syntax/schema/contract recognition, dependency and resource checks,
  semantic resolution, and invariant checks; use DR-0012's closed status set,
  internal/resource/phase precedence, invalid-source-over-unsupported tie-break,
  first status-establishing primary-diagnostic rule, bounded ordering and
  reserved candidate, incomplete markers, valid/supported snapshot conditions,
  and non-contractual partial-graph debug boundary.
- Prove separately that every embodied Part has exactly one containment path,
  that containment owns reference-transform inheritance, and that relation
  traversal cannot repair containment or change its cycle checks. For Stage 1,
  verify required Joint edges connect structural parents to immediate children
  and that attached module roots agree with separately declared containment.
  Prove that each present attached module root has exactly one incoming active
  Attachment, absent optional modules have none, each host Socket accepts one,
  and repeated endpoint pairs, host reuse, zero incoming, and multiple incoming
  are distinct rejected conditions.
- Prove descendant-owned mating Socket composition by composing the
  module-root-to-Socket-owner containment transform with the owner-local Socket
  frame before inversion/alignment; verify that the derived value is the
  root's sole child-local containment placement, that descendants inherit only
  through containment, and that competing authored root-local placement is
  compared with the same value while preserving all provenance.
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

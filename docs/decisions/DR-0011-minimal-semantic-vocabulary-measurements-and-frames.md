# DR-0011: Minimal semantic vocabulary, measurements, and frames

ID: DR-0011

Scope: Specification and architecture

Status: Proposed

Revision: 7

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-12

Supersedes: —

Superseded by: —

## Context

Creature Kernel needs a small semantic vocabulary that can survive geometry,
rig, and runtime implementation changes. A single generic tag node would make
ownership, articulation, attachment, spatial designation, affordance, and
procedural intent indistinguishable. It would also make measurements and frame
conversions implicit, which would undermine deterministic diagnostics and
source-linked lineage.

This record owns the CK-KICK-012 Batch 3 decisions for distinct semantic
concepts, measurements, and frames/conversions. It complements the authoritative
source and resolved-graph boundary in [DR-0002](DR-0002-declarative-body-document-source-of-truth.md),
the durable identity boundary in
[DR-0006](DR-0006-durable-semantic-and-artifact-identity.md), and the first
morphology envelope in
[DR-0008](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md).
It does not replace those records, select a serialized syntax, or accept any
of them. On 2026-08-11 Ben approved the wider seven-decision CK-KICK-012 batch
in discussion; this record owns its three vocabulary, measurement, and frame
decisions. On 2026-08-11 Ben approved the CK-KICK-012 Batch 4 semantic
classification, directed articulation, and measurement-conflict resolutions
recorded in Revision 2. On 2026-08-11 Ben approved the CK-KICK-012 Batch 5
blocker-resolution selections recorded in Revision 3: canonical resolved Joint
and Socket frame records, explicit containment and Attachment boundaries, and
the linked operation outcome/bootstrap/resource rules. The exact-revision
CK-KICK-012 Batch 5 Double review of Revision 3 is stale historical evidence.
Its three findings motivated the CK-KICK-012 Batch 6 resolutions recorded in
Revision 4. The exact Revision 4 Double review at commit
`c64b1b98948304d631eecea6a354c9e42c89c510` then identified F2–F3 for this
record. Ben approved those finding resolutions in discussion on 2026-08-11;
Revision 5 then resolved the typed descendant-owned Attachment composition and
mating-Socket cardinality consequences, while DR-0002, DR-0008, and DR-0012
carried linked graph, morphology, and status details. Revision 6 records Ben's
2026-08-12 discussion approval of five Recommendation 1 resolutions: the
total status/completeness rule, normalized module-instance declaration and
global Socket capacity, Attachment transform admissibility, the four readiness
gates, and the authoritative build/publication outcome. This discussion
approval is not DR acceptance. Revision 6 remains Proposed with Owner approval
Pending and Review status Complete. Initial source encoding,
phase sequencing, diagnostics, compatibility, and resource limits are owned
by [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The prior Revision 5 Double review examined target commit
`88004388f9537a37617ae248bdaad4625e6f3f03` in [review 01](reviews/DR-0011-rev-05-review-01.md)
and [review 02](reviews/DR-0011-rev-05-review-02.md); both independent passes
recommended **Revise** at **High** confidence. The prior Review Complete state
records evidence, not a clean review or acceptance. Those Revision 5 artifacts
are now stale historical evidence after this proposal change and a fresh
current Double review is required. The Revision 4 and earlier reviews remain
stale historical evidence.
Ben's 2026-08-12 Batch 9 discussion approval adds the absent-module
declaration identity rule and cross-links the resolver snapshot handoff and
DR-0013 build/output boundary. This material Revision 7 change makes the
Revision 6 current-review artifacts stale; Revision 7 remains Proposed with
Owner approval Pending and Review status Pending.

## Decision

### Typed semantic concepts and ownership

The identity-bearing semantic concepts are exactly **Part**, **Joint**,
**Socket**, **Attachment**, **Region**, **Capability**, and **Field**. They are
distinct typed concepts rather than one generic tag node:

- **Part** is an owned structural body element. Ownership is the containment
  relationship and is not implied by any other concept.
- **Joint** is a directed, identity-bearing articulation relation. It connects
  exactly one proximal Part to exactly one distal Part and canonically owns a
  proximal-frame record and a distal-frame record. Each record is expressed in
  its corresponding Part's local basis and retains provenance for any source
  reference that fed it. It is not a bone, a bone hierarchy, solver
  constraint, limit, rig, or runtime representation.
- **Socket** is a named interface owned by a Part. It provides a host or mating
  interface and owns exactly one interface frame expressed in that Part's
  basis; it does not imply articulation.
- **Attachment** connects exactly one host Socket to exactly one mating Socket.
  It maps or connects module composition, but does not imply articulation. The
  mating Socket may be owned by any Part in the attached module-root
  containment subtree. A present attached module root has exactly one active
  incoming Attachment, an absent optional module has none, and each Socket has
  total active capacity one across host and mating roles. A Socket used by two
  active Attachments in any role combination, including one host use plus one
  mating use, is invalid. Repeated endpoint pairs, host reuse, mating reuse,
  cross-role reuse, zero incoming Attachments for a present root, multiple
  incoming Attachments, invalid or detached endpoints, duplicate Attachments,
  and Attachment cycles are distinct semantic-invalid outcomes or have an
  explicit deterministic diagnostic mapping.
- **Region** is a potentially overlapping spatial designation. It never owns
  the parts it designates.
- **Capability** is a queryable affordance. It is not an implementation,
  backend, or proof that a runtime system can execute it.
- **Field** is a spatially varying semantic intent or channel with lineage. It
  is not necessarily a signed-distance field, storage format, mesh attribute,
  or physics field.

**Module** is not an embodied graph concept. It is an authored reusable source
scope whose instantiation emits identity-bearing concepts. A Module therefore
does not receive an embodied-graph identity in place of the concepts it emits.
The normalized model separately declares each module instance (module, root
Part, instance anchor/provenance, presence/optionality, and whether Attachment
composition is required) without introducing an eighth identity-bearing
concept. An absent optional module has a stable authored module-instance
declaration address plus a non-embodied module root-role/template reference.
It emits or reserves no Part, and no graph relation may target it. It
participates in declaration uniqueness, not the Part namespace. If later
present, its Part identity derives deterministically from the module-instance
anchor plus root role. This declaration is not an eighth identity-bearing
embodied graph concept. Optional absence is distinct from present-but-unattached
state before Attachment cardinality checking; a present Attachment-required
root with zero incoming active Attachments is invalid. Nested module instances
require distinct Socket instances.
Landmarks, anchors, dimensions, and frames are typed records or values owned by
a named identity-bearing concept and addressed through the owner plus role.
They do not acquire independent embodied-graph identity merely because they
have a name. These concepts and records participate in the role-labelled,
non-structural relations described by DR-0002 and DR-0008. Part-to-Part
ownership is the only structural body-containment relation in the first
grammar. A concept or typed record may still have one declarative owner for
identity, lifecycle, and owner-plus-role addressing; that ownership does not
make it a structural Part or create another body-containment edge. Exact
identity serialization and syntax remain later specification work.

### Measurements and provenance

Authored local transforms own reference-frame placement. Typed dimensions own
declared size and extents. Named landmarks and anchors provide stable semantic
locations and record whether each value is authored or derived. Ratios are
derived and inspectable; they are not authored authority.

A measurement claim targets an owner semantic address, a property role, and a
reference frame or context. Claims are compared only after unit and frame
normalization. Multiple authoritative authored claims for the same target must
agree within a contract-defined tolerance; derived or defaulted values never
override authored values. Cross-property constraints exist only when an
invariant is explicitly declared. If authoritative claims or explicit
invariants cannot be jointly satisfied within tolerance, resolution returns a
semantically invalid result with a deterministic diagnostic in the
authoritative operation-result envelope and publishes no success snapshot.
Exact measurement vocabulary, units beyond source declarations, numeric
ranges, tolerance values, and diagnostic codes remain later specification
detail.

### Frames and conversion

Every source declares its length units, handedness, up axis, and forward axis.
The resolver normalizes source values into one contract-revision canonical
internal basis and records conversion provenance. The semantic frame boundary
distinguishes:

- a local/reference frame, which is authored relative placement;
- joint frames, which are semantic articulation interfaces;
- socket and mating frames, which are attachment interfaces;
- a resolved world/reference transform, which is derived build output; and
- runtime pose transforms, which are separate runtime state.

Part-to-Part containment is the only structural body relation. Every embodied
Part, including optional module Parts, has exactly one containment path to the
root; Joint, Attachment, Region, and other relations cannot create or repair
that path. Containment owns reference-transform inheritance. Validate
containment reachability and containment cycles separately from typed-relation
cycles. In the bounded Stage 1 axial/limb grammar, required Joint edges connect
the structural parent Part to its immediate child Part. An Attachment's host
Part and module-root child must agree with separately declared containment.

Attachment placement uses a typed transform contract. `T_A←B` maps coordinates
expressed in B into A. Let H be the host Part, R the attached subtree root Part,
M the mating Socket owner Part, and `S_h` and `S_m` the host and mating Socket
frames. Let `O_(S_h←S_m)` map mating-Socket coordinates into host-Socket
coordinates; identity makes the frames coincident. The conceptual host-local
equation is:

`T_H←R = T_H←S_h · O_(S_h←S_m) · (T_R←M · T_M←S_m)^−1`

Composition is understood in the stated coordinate bases and order, with the
rightmost transform applied first. Matrix layout and serialized
representation remain deferred. An optional explicit authored Attachment
offset, if admitted, is part of the host/mating alignment transform `O` in
that typed basis; exact field spelling and tolerance remain deferred. The
resulting value is the attached root's sole resolved child-local containment
placement relative to its host parent. Descendants inherit only through
containment; Attachment adds no parallel transform-inheritance path. If
separately authored root-local placement controls the same degrees of freedom,
it must agree with that same canonical derived child-local value within the
later-defined tolerance or the document is semantic-invalid. The resolved
graph materializes canonical owned records and preserves source-reference
provenance for all frames, containment transforms, offsets, and composition
steps; it does not choose a bone, solver, limit, rig, or runtime
representation. Every transform entering Attachment composition must be finite,
non-degenerate, and invertible under the declared transform profile. A
source-caused violation is semantic `invalid-source` with a deterministic
diagnostic and preserved provenance; implementation failure on an admissible
transform is `internal-failure`. Exact representation, allowed scale/shear,
conditioning threshold, comparison tolerances, and matrix storage remain
resolver-activation prerequisites or deferred specification details.

The canonical axes and unit, rotation representation, and scale/shear policy
are later specification and platform work. Their deferral does not defer the
requirement that sources declare their basis or that normalization provenance
be retained.

## Consequences

- Consumers can distinguish the seven identity-bearing concepts, ownership,
  articulation, attachment, spatial intent, affordance, and varying semantic
  channels without inferring meaning from a generic tag. Module scopes and
  owner-plus-role records cannot silently become additional graph concepts.
- An absent optional module has a unique authored declaration address and
  non-embodied root-role/template reference only. It emits or reserves no Part,
  cannot be a relation target, and is unique among declarations rather than
  Parts; when present, its Part identity derives from the instance anchor plus
  root role without creating an eighth graph concept.
- Regions may overlap without corrupting the ownership tree, and attachments
  do not accidentally promise articulation or a solver representation. Joint
  direction, endpoint cardinality, and endpoint-frame ownership are explicit.
- Measurements retain authored authority and provenance while exposing ratios
  and derived landmarks for inspection.
- Conflicting authored claims become deterministic semantic-invalid diagnostics
  in the authoritative envelope instead of hidden precedence behaviour, and a
  success snapshot is not published for an unsatisfied claim set.
- Source basis conversion is explicit and auditable, while build-derived world
  transforms and runtime pose state cannot be mistaken for authored placement.
- Structural containment is explicit and independently checked: relations do
  not supply root reachability or transform inheritance. A descendant-owned
  mating Socket is composed through the module-root containment path, and the
  Attachment result is the root's sole child-local placement; descendants
  inherit only through containment. The normalized module-instance declaration
  is owned by DR-0002 and does not add an identity-bearing concept. A present
  module root has exactly one incoming Attachment, an absent optional module
  has none, and each Socket has total active capacity one across host and mating
  roles. Repeated endpoint pairs, host reuse, mating reuse, cross-role reuse,
  zero incoming, and multiple incoming are distinct rejected conditions or have
  an explicit deterministic diagnostic mapping. Competing authored root-local
  placement compares to the same canonical value and retains provenance.
  Every transform entering composition is finite, non-degenerate, and
  invertible under the declared profile; source violations are semantic
  `invalid-source`, while implementation failure on admissible transforms is
  `internal-failure`.
- The vocabulary and frame boundary remain engine-independent, but exact
  syntax, canonical numeric conventions, and storage representations require
  later specification and evidence.

## Alternatives Considered

### One generic tag or node type

This is compact and easy to extend, but it hides ownership and makes clients
reconstruct whether a tag is an articulation, attachment, region, capability,
or field. It also invites implementation-specific meaning. It is not selected.

### Treat every relation as a joint or bone-like edge

This could simplify an embodiment implementation, but sockets, attachments,
regions, and capabilities have different semantics and lifecycles. It would
also prematurely select a rig or solver model. The typed concepts keep those
boundaries explicit.

### Treat Module and helper records as embodied graph concepts

Giving an authored Module, landmark, anchor, dimension, or frame an independent
graph identity would make reusable source scope, owned values, and semantic
concepts compete in the same identity space. It would also make owner and
role-based references ambiguous across instantiation. Module remains authored
source scope, while the helper records remain owned typed values addressed by
owner and role; only the seven listed concepts are identity-bearing.

### Make regions owned parts

This would simplify traversal for non-overlapping examples, but overlapping
spatial designations are required and a region is not a structural element.
Regions therefore never own parts.

### Author ratios and infer dimensions

Ratios are convenient for procedural variation, but making them authoritative
would make physical size and extents ambiguous and hide conflicting constraints.
Dimensions and authored placement remain authoritative; ratios are derived and
inspectable.

### Silently choose a winning measurement constraint

Precedence could make some inputs compile, but it would discard authored intent
without an explicit diagnostic and make results depend on hidden ordering.
Conflicts diagnose failure until a later specification defines any deliberate
constraint mechanism.

### Preserve source coordinate bases into every downstream consumer

This avoids conversion work, but forces every consumer to support every source
convention and makes cross-source composition fragile. Normalization into one
contract-revision basis with recorded provenance is the selected boundary.

### Use one frame for authoring, attachment, build output, and runtime pose

This is superficially simple, but conflates authored intent with derived
resolution and mutable runtime state. Separate frame roles preserve provenance
and make runtime state changes non-authoritative.

### Derive containment from Joint or Attachment relations

This would reduce one apparent edge type, but would let relation traversal
repair disconnected Parts and would make reference-transform inheritance
depend on relation kind or traversal order. It is rejected: Part containment is
the sole structural body relation, and containment cycles/reachability are
checked separately from relation cycles.

### Leave Joint endpoint records as ambiguous source references

Keeping only source references would preserve authoring flexibility, but allows
different consumers to choose different endpoint owners, roles, bases, or
provenance. The resolved graph therefore owns exactly one proximal and distal
record in the corresponding Part bases; source references remain provenance.

### Let authored Attachment placement silently win over Socket composition

That would discard host/mating interface semantics; letting Socket composition
silently win would discard an explicit authored offset. The selected
composition combines host Part/frame, host Socket, optional offset, and the
inverse of the mating Socket's owner-local frame after module-root containment
composition. It resolves the root's sole child-local placement, rejects a
same-degree-of-freedom disagreement within a later-defined tolerance, and keeps
provenance for every composition input.

### Treat Attachment cardinality as optional or reuse host Sockets

An at-most-one rule would permit a present module root with no incoming
Attachment, while reusable host Sockets would make placement and endpoint
identity depend on traversal order. The initial boundary requires exactly one
incoming Attachment for each present module root, none for an absent optional
module, total active capacity one per Socket across host and mating roles, and
distinct rejection or deterministic mapping of repeated endpoint pairs, host
reuse, mating reuse, cross-role reuse, zero incoming, and multiple incoming
cases.

## Adversarial Review Response

The Revision 1 current-revision Double review remains preserved as stale
historical evidence in the [contract pass](reviews/DR-0011-rev-01-review-01.md)
and [graphics-system pass](reviews/DR-0011-rev-01-review-02.md); both recommended
Revise at High confidence. The Revision 2 Double review is preserved as stale
evidence at commit `7dba9346c91c59ff99f10b94630690bf732d6b28`: the fresh
independent Sol-medium contract/schema/security pass
([review 01](reviews/DR-0011-rev-02-review-01.md)) recommended **Accept** with
**High** confidence and found no DR-0011-specific blocker, while the fresh
independent semantic-graph/graphics/runtime pass
([review 02](reviews/DR-0011-rev-02-review-02.md)) recommended **Revise** with
**High** confidence. The latter's blockers motivated Revision 3's explicit
containment, Attachment composition, and canonical frame-record selections;
the linked operation status, bootstrap, and hostile-input resource rules are
owned by DR-0002/DR-0012.

Revision 3's exact-revision CK-KICK-012 Batch 5 Double review examined commit
`a282dbabffd83afa4e62577086934d00f98e12c7`: the independent
[contract/schema/security pass](reviews/DR-0011-rev-03-review-01.md) recommended
**Accept** at **High** confidence and identified no DR-0011-specific blocker;
the independent [semantic-graph/graphics/runtime pass](reviews/DR-0011-rev-03-review-02.md)
recommended **Revise** at **High** confidence.

The three Batch 5 findings in that exact-revision review motivated the current
CK-KICK-012 Batch 6 proposal text and are resolved across the current records.
This revision resolves the typed descendant-owned mating Socket composition
and exact Attachment cardinality. DR-0002 and DR-0008 own the linked source-
set, morphology, and containment consequences; DR-0002 and DR-0012 own the
operation status/bootstrap/resource boundary. Ben approved these F2–F3
resolutions in discussion on 2026-08-11. The exact Revision 4 Double review at
commit `c64b1b98948304d631eecea6a354c9e42c89c510` is stale historical evidence,
not a clean review or acceptance. Its independent [review 01](reviews/DR-0011-rev-04-review-01.md)
and [review 02](reviews/DR-0011-rev-04-review-02.md) both recommended **Revise**
at **High** confidence. The current Revision 5 Double review examined target
commit `88004388f9537a37617ae248bdaad4625e6f3f03`; [review 01](reviews/DR-0011-rev-05-review-01.md)
and [review 02](reviews/DR-0011-rev-05-review-02.md) both recommended **Revise**
at **High** confidence. Those ten artifacts and their five findings are now
stale historical evidence after the Revision 6 proposal change. Their findings
are dispositioned for the next review as follows: (1) total status/completeness
is owned by DR-0002/DR-0012 and cross-linked here; (2) module-root observability
and global cross-role Socket capacity are revised here with graph ownership in
DR-0002; (3) Attachment transform admissibility and source-versus-
implementation mapping are revised here and in DR-0002/DR-0008; (4) the four
technical readiness gates are owned by DR-0013; and (5) authoritative
build/publication outcome and `output-failure` are owned by DR-0013. The latter
two are cross-links, not additional DR-0011 decisions. The fresh current
Double review of Revision 6 was complete at target commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`: [review 01](reviews/DR-0011-rev-06-review-01.md)
recommended **Revise** at **Medium** confidence and [review 02](reviews/DR-0011-rev-06-review-02.md)
records **Ready for owner disposition** at **High** confidence with no
DR-0011-specific blocker. Applicable consolidated finding is C4; C1–C3 and
C5–C7 remain cross-cutting evidence owned by the linked records, chiefly
DR-0002/DR-0012/DR-0013. All seven consolidated current findings await Ben's
discussion and owner disposition; review completion is evidence, not a
clean review or acceptance. Exact serialized field spellings, canonical
axes/units/rotation/scale/shear, conditioning/comparison tolerances,
diagnostic codes, and fixture evidence remain deferred. Those Revision 6
artifacts and findings are preserved as stale historical evidence after the
material Revision 7 change and do not satisfy the pending current-revision
review. The Batch 9 absent-module identity resolution is cross-linked to the
resolver snapshot handoff and DR-0013 build/output boundary. Owner approval
remains Pending and Status remains Proposed; Review status is Pending. Only
Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the seven identity-bearing concepts, Module source-scope treatment,
  owner-plus-role records for landmarks/anchors, dimensions, and frames,
  ownership restrictions, directed Joint endpoint roles/cardinality, and valid
  relations in the body-document and body-graph specifications; ensure no
  generic tag node becomes a semantic escape hatch.
- Materialize canonical Joint proximal/distal records and one Socket interface
  frame in their owning Part bases, retaining source-reference provenance and
  rejecting competing owner/role interpretations; do not introduce a bone,
  solver, limits, rig, or runtime representation.
- Specify explicit Part containment, one root path for every embodied Part,
  containment-owned reference-transform inheritance, separate containment and
  relation cycle checks, Stage 1 immediate-child Joint edges, and Attachment
  host/child containment agreement. Use the DR-0002 normalized module-instance
  declaration for module, root Part, instance anchor/provenance,
  presence/optionality, and Attachment-required state without making Module an
  eighth identity-bearing concept. For an absent declaration, preserve the
  stable authored declaration address and non-embodied root-role/template
  reference, emit or reserve no Part, reject graph-relation targets, and keep
  uniqueness in the declaration namespace; if present, derive Part identity
  from the instance anchor plus root role. Require exactly one incoming active
  Attachment for each present module root, none for an absent optional module,
  and total active Socket capacity one across host and mating roles; distinguish
  repeated endpoint pairs, host reuse, mating reuse, cross-role reuse, zero
  incoming, and multiple incoming cases with deterministic diagnostics or
  explicit mapping. Nested module instances require distinct Socket instances.
- Test Attachment placement with `T_A←B` and the conceptual equation
  `T_H←R = T_H←S_h · O_(S_h←S_m) · (T_R←M · T_M←S_m)^−1`, where O maps
  mating-Socket coordinates into host-Socket coordinates. Prove that the
  result is the root's sole child-local containment placement, descendants
  inherit only via containment, and competing authored root-local placement
  compares with the same canonical value. Preserve provenance for every input
  and composition; reject same-degree-of-freedom disagreement within the
  later-defined tolerance, duplicate/detached/invalid endpoints, mating and
  cross-role Socket reuse, and Attachment cycles. Every incoming transform must
  be finite, non-degenerate, and invertible under the declared profile; source
  violations map to semantic `invalid-source` with deterministic
  diagnostic/provenance, while implementation failure on an admissible
  transform maps to `internal-failure`. Exact representation, scale/shear,
  conditioning, comparison tolerance, matrix layout, and serialized
  representation remain resolver-activation prerequisites or deferred
  specification details.
- Create fixtures that distinguish Part, Joint, Socket, Attachment, Region,
  Capability, and Field, including overlapping regions and an attachment that
  is not a joint.
- Define typed dimensions, authored local transforms, named landmarks/anchors,
  owner-plus-role addressing, authored-versus-derived provenance, ratio
  derivation, claim targets, normalization context, conflict diagnostics,
  tolerances, and exact measurement vocabulary before promising those details.
- Prove that conflicting authoritative claims or explicit invariants fail
  deterministically, within the declared tolerance rule, rather than silently
  applying precedence, and that no success snapshot is published.
- Require every source fixture to declare units, handedness, up, and forward
  axes; prove normalization into one contract-revision canonical basis and
  inspectable conversion provenance.
- Test that local/reference, joint, socket/mating, resolved world/reference,
  and runtime pose frames remain distinct across source resolution and runtime
  updates.
- Freeze the cross-DR fixture matrix covering durable identities, typed
  articulation endpoints, measurement/frame cases, expected outcomes, and
  diagnostics before treating implementation evidence as proof.
- Later settle canonical axes/unit, rotation representation, scale/shear
  policy, exact serialized syntax, and platform-specific conversion details.

## Canonical Design Links

- [Product requirements](../product/requirements.md)
- [Specification boundary](../../spec/README.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [First digitigrade morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [Architecture index](../architecture/README.md)

## Reversibility and Revisit Triggers

Revisit the vocabulary if a required semantic distinction cannot be expressed
without implementation leakage or if evidence shows a concept needs a new
cross-cutting contract. Revisit measurements if authored intent, derived values,
or conflict diagnostics cannot remain distinguishable. Revisit frame conversion
if cross-source composition or downstream consumers require a different
canonical basis, while preserving the separation between authored, derived,
and runtime state.

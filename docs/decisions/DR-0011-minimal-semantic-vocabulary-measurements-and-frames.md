# DR-0011: Minimal semantic vocabulary, measurements, and frames

ID: DR-0011

Scope: Specification and architecture

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-11

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
recorded in Revision 2. Initial source encoding, phase sequencing, diagnostics,
compatibility, and resource limits are owned by [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
This discussion approval is not DR acceptance: this Proposed record remains
subject to current-revision review and owner disposition.

## Decision

### Typed semantic concepts and ownership

The identity-bearing semantic concepts are exactly **Part**, **Joint**,
**Socket**, **Attachment**, **Region**, **Capability**, and **Field**. They are
distinct typed concepts rather than one generic tag node:

- **Part** is an owned structural body element. Ownership is the containment
  relationship and is not implied by any other concept.
- **Joint** is a directed, identity-bearing articulation relation. It connects
  exactly one proximal Part to exactly one distal Part and owns or refers to
  proximal and distal endpoint frames expressed relative to those Parts. It is
  not a bone, a bone hierarchy, or a solver constraint.
- **Socket** is a named interface owned by a Part. It provides a host or mating
  interface frame without implying articulation.
- **Attachment** connects exactly one host Socket to exactly one mating Socket.
  It maps or connects module composition, but does not imply articulation.
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

The canonical axes and unit, rotation representation, and scale/shear policy
are later specification and platform work. Their deferral does not defer the
requirement that sources declare their basis or that normalization provenance
be retained.

## Consequences

- Consumers can distinguish the seven identity-bearing concepts, ownership,
  articulation, attachment, spatial intent, affordance, and varying semantic
  channels without inferring meaning from a generic tag. Module scopes and
  owner-plus-role records cannot silently become additional graph concepts.
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

## Adversarial Review Response

The Revision 1 current-revision Double review is preserved as stale historical
evidence in the [contract pass](reviews/DR-0011-rev-01-review-01.md) and
[graphics-system pass](reviews/DR-0011-rev-01-review-02.md). Both recommended
Revise at High confidence: the contract pass found Module,
landmark/anchor, dimension, and frame insufficiently classified, while the
graphics pass found articulation endpoint typing ambiguous and measurement
conflict semantics undefined. On 2026-08-11 Ben approved the resulting
CK-KICK-012 Batch 4 semantic-classification, articulation, and measurement
resolution for Revision 2. No current-revision review has been run; Review
Pending records that required evidence is still outstanding. The cross-DR
fixture-matrix obligation remains open. Only Ben may accept or reject this
proposal.

## Implementation and Proof Obligations

- Define the seven identity-bearing concepts, Module source-scope treatment,
  owner-plus-role records for landmarks/anchors, dimensions, and frames,
  ownership restrictions, directed Joint endpoint roles/cardinality, and valid
  relations in the body-document and body-graph specifications; ensure no
  generic tag node becomes a semantic escape hatch.
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

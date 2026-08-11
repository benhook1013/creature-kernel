# DR-0011: Minimal semantic vocabulary, measurements, and frames

ID: DR-0011

Scope: Specification and architecture

Status: Proposed

Revision: 1

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
decisions. This Proposed record remains subject to review and owner disposition.

## Decision

### Typed semantic concepts

The minimal vocabulary uses distinct typed concepts rather than one generic
tag node:

- **Part** is an owned structural body element. Ownership is the containment
  relationship and is not implied by any other concept.
- **Joint** is a semantic articulation relation and its frames. It is not a
  bone, a bone hierarchy, or a solver constraint.
- **Socket** is a named host interface frame.
- **Attachment** is the mapping or connection of a module to a socket. An
  attachment is not automatically a joint.
- **Region** is a potentially overlapping spatial designation. It never owns
  the parts it designates.
- **Capability** is a queryable affordance. It is not an implementation,
  backend, or proof that a runtime system can execute it.
- **Field** is a spatially varying semantic intent or channel with lineage. It
  is not necessarily a signed-distance field, storage format, mesh attribute,
  or physics field.

These types may participate in the role-labelled, non-ownership relations
described by DR-0002 and DR-0008, while Part remains the only ownership-bearing
concept in the first grammar. Exact endpoint roles, cardinality, identity
serialization, and syntax remain later specification work.

### Measurements and provenance

Authored local transforms own reference-frame placement. Typed dimensions own
declared size and extents. Named landmarks and anchors provide stable semantic
locations and record whether each value is authored or derived. Ratios are
derived and inspectable; they are not authored authority. When dimensions,
transforms, landmarks, or other constraints conflict, resolution diagnoses a
failure rather than silently choosing a precedence rule. Exact measurement
vocabulary, units beyond source declarations, numeric ranges, tolerance, and
constraint codes remain later specification detail.

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

- Consumers can distinguish ownership, articulation, attachment, spatial
  intent, affordance, and varying semantic channels without inferring meaning
  from a generic tag.
- Regions may overlap without corrupting the ownership tree, and attachments
  do not accidentally promise articulation or a solver representation.
- Measurements retain authored authority and provenance while exposing ratios
  and derived landmarks for inspection.
- Conflicting constraints become deterministic diagnostics instead of hidden
  precedence behaviour.
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

No current-revision adversarial review has been run. The discussion approval on
2026-08-11 is not a review, clean-review finding, or acceptance. Review status
is Pending, and only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the typed concept vocabulary, ownership restrictions, endpoint roles,
  identity treatment, and valid relations in the body-document and body-graph
  specifications; ensure no generic tag node becomes a semantic escape hatch.
- Create fixtures that distinguish Part, Joint, Socket, Attachment, Region,
  Capability, and Field, including overlapping regions and an attachment that
  is not a joint.
- Define typed dimensions, authored local transforms, named landmarks/anchors,
  authored-versus-derived provenance, ratio derivation, conflict diagnostics,
  tolerances, and exact measurement vocabulary before promising those details.
- Prove that conflicting measurement constraints fail deterministically rather
  than silently applying precedence.
- Require every source fixture to declare units, handedness, up, and forward
  axes; prove normalization into one contract-revision canonical basis and
  inspectable conversion provenance.
- Test that local/reference, joint, socket/mating, resolved world/reference,
  and runtime pose frames remain distinct across source resolution and runtime
  updates.
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

# Resolved body-graph contract

Status: Proposed contract; CK-KICK-012 Batch 4 discussion-approved and
pending the new current-revision Double review, DR-0012, and Ben's owner
disposition

This document is the provisional specification authority for the resolved,
per-build semantic body graph. It describes typed concepts, durable semantic
identity, directed relations, frames, provenance, invariants, and publication
conditions. It consumes the admitted source model owned by the
[body-document contract](../body-document/README.md); it does not redefine
source encoding, structural schema, extension syntax, or source-side resource
admission.

The graph proposal is deliberately engine-independent and does not choose a
machine schema, exact serialized names, numeric ranges, tolerances, canonical
axes/units/rotation/scale/shear, source-map encoding, or canonical bytes and
hashing. All technical material remains Proposed pending the current-revision
Double review and Ben's later owner disposition.

## Graph authority and identity

The graph is derived, build-scoped, inspectable, and reproducible when the
source, compiler/build identity, configuration, seed, and dependencies permit
reproduction. It is never a competing authored source. A validated snapshot
may be published only for valid-supported success; invalid and unsupported
partial graphs are non-compilable, non-contractual debug data.

Identity-bearing embodied concepts are exactly:

- **Part**, the structural element in the ownership tree;
- **Joint**, a directed articulation relation;
- **Socket**, a Part-owned named interface;
- **Attachment**, a connection between sockets;
- **Region**, an overlapping spatial designation;
- **Capability**, a queryable affordance; and
- **Field**, a spatial semantic intent or channel with lineage.

Module is an authored reusable scope that instantiates these concepts. It is
not itself an embodied graph concept and does not add a body-containment or
articulation meaning. Landmark, anchor, dimension, and frame are typed owned
records addressed through their owner and role. They carry values, placement,
or context and may be authored, defaulted, or derived as allowed by their
owner; they are not an untyped escape hatch for graph identity.

Each identity-bearing concept uses a structured semantic address whose
components include source namespace, authored stable module-instance anchors,
concept kind, and role-local key. Exactly one source owns each namespace in a
resolved source set. A collision requires an authored, deterministic,
collision-free remap covering every contributed address from the imported
namespace. Exact address serialization and structural-edit lifecycle rules
remain deferred. Mesh, vertex, face, topology, LOD, and array positions are
artifact-local and never durable semantic identity.

## Typed relations and frames

### Joint

A Joint is directed and identity-bearing. It has exactly one proximal Part and
exactly one distal Part, with an endpoint frame relative to each Part. The
direction and endpoint roles are semantic relation data; they do not imply a
bone, fixed bone hierarchy, solver constraint, joint limit, or anatomy-fidelity
claim. Joint frames remain distinct from authored local/reference frames,
socket/mating frames, derived world/reference transforms, and mutable runtime
pose transforms.

### Socket and Attachment

A Socket is a named interface owned by one Part. An Attachment connects exactly
one host Socket to exactly one mating Socket. It maps or composes authored
module scope at that interface but does not imply articulation. A movable tail,
for example, uses an explicit Joint in addition to any socket-based module
Attachment. Socket and mating frames retain their own provenance and are not
silently treated as Joint endpoint frames.

### Other concepts

Regions may designate multiple Parts and may overlap; they never own those
Parts. Capabilities describe queryable affordances and do not prove a runtime
implementation. Fields carry representation-neutral semantic intent and
lineage; they are not necessarily signed-distance fields, mesh attributes, or
physics storage. Part-to-Part ownership is the sole structural body-containment
tree. Declarative ownership of a concept or typed record scopes identity and
lifecycle without adding a structural body edge. Other relations are reified,
role-labelled, typed, and bounded by this contract rather than an unrestricted
user-defined graph.

## Minimum Stage 1 graph

The first supported morphology is a bounded stylized digitigrade biped. The
minimum typed chain is:

```text
pelvis Part (owns root-reference frame)
  -> spine Joint
  -> torso/chest Part
  -> neck-base Joint
  -> neck Part
  -> head-base Joint
  -> head Part
```

Each arm has shoulder, elbow, and wrist Joints connecting the torso, upper-arm,
forearm, and hand/paw Parts, followed by a terminal paw-base landmark or
Socket. Each leg has hip, knee, and hock-or-ankle Joints connecting the
pelvis, thigh, lower-leg, and foot/paw Parts, followed by a terminal paw-base
landmark or Socket. The role chain is a semantic minimum, not serialized
syntax or a required bone count. Predefined ears and tail modules use
Attachment. A movable tail also has a separate Joint; an ear needs no
articulation. Additional anatomy, arbitrary limbs, arbitrary relation kinds,
and solver-specific structures are outside this first envelope.

## Values, normalization, and provenance

Authored local transforms own reference-frame placement. Typed dimensions own
declared size or extents. Landmark and anchor records retain owner, role,
frame/context, and authored/defaulted/derived provenance. Ratios are derived
and inspectable, not authored authority. Sources declare units, handedness, up,
and forward axes; resolution normalizes values into one contract-revision
canonical basis and records conversion provenance. The actual canonical basis,
rotation representation, scale/shear policy, ranges, and tolerance remain
deferred.

When a claim targets the same owner address, property role, and frame/context,
the resolver compares values after normalization. Authored claims and explicit
invariants must be jointly satisfiable within the contract tolerance. Derived
or defaulted values never override authored claims, and no hidden inferred
equation may manufacture a winner. A conflict is a semantic-invalid outcome
with a deterministic diagnostic in the operation-result envelope and no
success snapshot. Required unresolved or ambiguous values likewise cannot
succeed.

## Resolver and publication relationship

The [body-document contract](../body-document/README.md) owns the single
ordered source-to-graph operation and its phase sequence. This graph contract
defines the graph-side work performed by the namespace/identity/reference,
ownership/typed-relation, normalization/derivation, invariant, and publication
phases. It does not create a second pipeline or result envelope. Fatal failure
blocks dependent work, independent failures within a reached phase may
accumulate deterministically, and only complete valid-supported resolution may
publish this graph as a successful snapshot.

## Invariants and equivalence

Minimum Stage 1 graph invariants include unique semantic addresses; acyclic
single-owner containment; one embodied root Part with its pelvis-owned
root-reference frame; every required Part reachable through valid typed
relations; the required typed axial, arm, and leg Joint/Part chain; exactly one
proximal and distal Part endpoint for every Joint; valid Joint and Attachment
endpoints; no dangling references; a Part-owned Socket for each socket
interface; one host and one mating Socket per Attachment; no Attachment-only
articulation claim; finite normalized values; complete authored/defaulted/
derived provenance; valid owner+role addressing for typed records; declared
source basis with recorded normalization provenance; required values resolved
and unambiguous; and deterministic ordering and lineage. These checks
establish semantic lineage and intent only. They do not prove a usable
skeleton, skinning, collision, contact, deformation, animation, or runtime
performance.

Semantic equivalence compares durable identities, relations, endpoint frames,
normalized values, provenance, and operation outcome. It ignores source text
ordering and incidental derived topology. A deterministic debug JSON view may
assist comparison, but canonical byte identity and hashing remain deferred.

Fixtures must cover bilateral/repeated modules, namespace ownership and full
remapping, the typed articulation chain, overlapping regions, a non-articulated
socket Attachment, authored/defaulted/derived values, frame normalization,
measurement conflicts, invalid/unsupported outcomes, resource limits, and the
cross-DR fixture matrix. The fixture set is evidence planning, not proof yet.

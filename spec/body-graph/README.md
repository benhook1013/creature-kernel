# Resolved body-graph contract

Status: Proposed contract; CK-KICK-012 Batch 6 discussion-approved canonical
update; the current CK-KICK-012 Batch 6 Double review is Complete. DR-0002
Revision 8, DR-0008 Revision 8, DR-0011 Revision 4, and DR-0012 Revision 3
remain Proposed with Owner approval Pending and Review Complete. The seven
findings are pending Ben discussion and owner disposition; see the [decision
registry](../../docs/decisions/registry.md). Review evidence is not acceptance
or a clean review.
The CK-KICK-012 Batch 5 review at commit `a282dbabffd83afa4e62577086934d00f98e12c7`
is stale historical evidence. No acceptance is implied.

This document is the canonical specification authority for the resolved,
per-build semantic body graph. It owns typed concepts, explicit Part
containment, durable semantic identity, typed relations, Attachment
composition and placement, canonical frame records, provenance, graph-side
invariants, and success-publication conditions. It consumes the admitted source
model and operation envelope owned by the
[body-document contract](../body-document/README.md); it does not redefine
source encoding or bootstrap/status/resource admission.

The contract is conceptual and engine-independent. Exact serialized member
names, diagnostic codes, numeric ranges, tolerances, canonical axes/units,
rotation/scale/shear policy, source-map encoding, canonical bytes, hashing, and
runtime representations remain deferred. Owner disposition remains pending
for the materially revised decision records.

## Graph authority and identity

The graph is derived, build-scoped, inspectable, and reproducible when the
source, compiler/build identity, configuration, seed, and dependencies permit
reproduction. It is never a competing authored source. A validated snapshot
may be published only for complete valid-supported success. Invalid and
unsupported partial graphs are non-compilable, non-contractual debug data.

The identity-bearing embodied concepts are exactly:

- **Part**, a structural element in the explicit containment tree;
- **Joint**, a directed articulation relation;
- **Socket**, a Part-owned named interface;
- **Attachment**, a host-to-mating socket composition relation;
- **Region**, an overlapping spatial designation;
- **Capability**, a queryable affordance; and
- **Field**, a spatial semantic intent or channel with lineage.

Module is an authored reusable source scope that instantiates these concepts;
it is not an embodied graph concept and does not add containment or
articulation by itself. Landmark, anchor, dimension, and frame are typed owned
records addressed through owner and role; they are not an untyped escape hatch
for graph identity.

Each identity-bearing concept uses a structured semantic address whose
components include source namespace, authored stable module-instance anchors,
concept kind, and role-local key. Exactly one source owns each namespace in a
resolved source set. A colliding import requires an authored, deterministic,
collision-free remap covering every contributed address from that namespace.
Exact address serialization and structural-edit lifecycle rules remain
deferred. Mesh, vertex, face, topology, LOD, and array positions are
artifact-local and never durable semantic identity.

## Explicit Part containment

Part-to-Part containment is the sole structural body-containment relation. The
resolved graph has one embodied root Part. Every embodied Part, including the
root of an optional attached module, has exactly one containment path to that
root: the root has no containment parent and every other Part has exactly one
containment parent. A Part with no path, more than one parent, or more than one
root path is invalid. An omitted optional module is allowed; a present module
root is not allowed to remain detached.

Containment is not inferred from, repaired by, or traversed through a Joint,
Attachment, Region, Capability, Field, or any other typed relation. It is the
topology that provides reference-transform inheritance: a child Part's
resolved reference placement is derived from its declared containment parent
and child-local placement. Relation endpoints may refer to Parts, but relation
reachability never substitutes for containment reachability.

Containment cycles are checked as a structural graph and are invalid. Typed
relation cycles are checked separately, using the rule for each relation
family; a relation-cycle diagnostic neither repairs nor replaces a containment
diagnostic. For the initial structural Joint and Attachment composition, a
cycle that would make a required Part or attached module root repeat in its
structural path is invalid. The two checks are independent so an operation
can retain diagnostics from both reached checks without making traversal order
define the body tree.

For Stage 1, every required axial or limb Joint connects the structural parent
Part to its immediate containment child Part. A Joint that merely connects two
Parts through a relation while their containment path is disconnected,
reversed, or non-immediate does not satisfy the required chain and is
semantically invalid. This requirement establishes the body tree; it does not
select a bone hierarchy or runtime traversal.

## Typed relations and canonical frame records

### Joint

A Joint is directed and identity-bearing. It has exactly one proximal Part and
exactly one distal Part. The resolved graph materializes two canonical typed
records owned by the Joint: a proximal-frame record expressed in the proximal
Part's local/reference basis and a distal-frame record expressed in the distal
Part's local/reference basis. Source references may provide or feed those
records, but a source reference is not a substitute for a resolved record.
Each record retains provenance for the source claims and any permitted
normalization or derivation.

Joint direction and endpoint roles are semantic relation data. They do not
select a bone, bone hierarchy, solver, joint limit, rig, skinning method, or
runtime representation. Joint frames remain distinct from authored
Part-local/reference placement, Socket interface frames, derived resolved
world/reference transforms, and mutable runtime-pose transforms.

### Socket and Attachment

Each Socket is owned by exactly one Part and owns one interface-frame record
expressed in that owning Part's local/reference basis. A Socket may be the host
interface or mating interface of an Attachment; the role is supplied by the
Attachment, not inferred from a generic relation.

An Attachment connects exactly one host Socket to exactly one mating Socket.
For the initial module composition, the host Socket is owned by the host Part,
the mating Socket may be owned by any Part in the attached root's containment
subtree, and that attached root is the explicitly declared containment child of
the host Part. The mating Socket's owner and frame are resolved through that
subtree. Thus the host Part, attached-root child, and Attachment must agree: an
Attachment cannot silently insert a Part under a different parent or make a
relation-only connection. Descendants inherit transforms only through
containment; Attachment is not a parallel transform-inheritance path.

The initial cardinality rules are explicit. A present attached root has exactly
one incoming active Attachment, while an absent optional module has none. Each
host Socket has capacity one active Attachment. Repeated endpoint-pair use,
host Socket reuse, zero incoming Attachments for a present attached root, and
multiple incoming Attachments for a present attached root are separate invalid
conditions. Attachment cycles, invalid or dangling endpoints, and a mismatch
between Attachment endpoints and the declared containment parent are also
invalid.

Attachment placement is the attached root's sole resolved child-local
containment placement relative to its host Part. To compose it, first compose
the module-root-to-mating-Socket-owner containment transform with the mating
Socket owner's local interface frame. That composed mating frame, the host
Socket interface frame, and any authored Attachment offset determine the
alignment in the host Part's local/reference basis. The exact transform
serialization and multiplication convention are deferred, but every semantic
input and its provenance are required. Descendant placement is subsequently
inherited only by the ordinary containment path. If an independently authored
root-local placement controls the same degrees of freedom, it must compare
with this same canonical resolved child-local value within the later-defined
contract tolerance; disagreement is semantically invalid, while both authored
and derived provenance are preserved rather than silently choosing a winner.

Attachment is composition only. It never implies a Joint, articulation,
mobility, solver constraint, or runtime pose. A movable tail therefore has a
separate explicit Joint in addition to its Attachment; an ear needs no Joint in
the first family.

### Other concepts

Regions may designate multiple Parts and may overlap; they never own Parts.
Capabilities describe queryable affordances and do not prove that a runtime
implementation can execute them. Fields carry representation-neutral spatial
intent and lineage; they are not necessarily signed-distance fields, mesh
attributes, or physics storage. Other relations are reified, role-labelled,
typed, and bounded by this contract rather than an unrestricted user-defined
graph.

## Minimum Stage 1 graph

The first supported morphology is a bounded stylized digitigrade biped. The
minimum typed axial chain is:

```text
pelvis Part (owns root-reference frame)
  -> spine Joint
  -> torso/chest Part
  -> neck-base Joint
  -> neck Part
  -> head-base Joint
  -> head Part
```

In each required Joint above, the proximal Part is the structural parent and
the distal Part is its immediate containment child. Each arm has shoulder,
elbow, and wrist Joints connecting the torso, upper-arm, forearm, and hand/paw
Parts in the same parent-to-immediate-child manner, followed by a terminal
paw-base landmark or Socket. Each leg has hip, knee, and hock-or-ankle Joints
connecting the pelvis, thigh, lower-leg, and foot/paw Parts in that manner,
followed by a terminal paw-base landmark or Socket. Predefined ears and tail
modules use Attachment; a movable tail also uses a separate Joint. Additional
anatomy, arbitrary limbs, arbitrary relation kinds, and solver-specific
structures are outside this first envelope.

## Values, normalization, and provenance

Authored local/reference transforms own reference-frame placement. Typed
dimensions own declared size or extents. Landmark and anchor records retain
owner, role, frame/context, and authored/defaulted/derived provenance. Ratios
are derived and inspectable, not authored authority. Sources declare units,
handedness, up, and forward axes; resolution normalizes values into one
contract-revision canonical basis and records conversion provenance. The
actual canonical basis, rotation representation, scale/shear policy, ranges,
and tolerance remain deferred.

When a claim targets the same owner address, property role, and frame/context,
the resolver compares values after normalization. Authored claims and explicit
invariants must be jointly satisfiable within the later-defined contract
tolerance. Derived or defaulted values never override authored claims, and no
hidden inferred equation may manufacture a winner. A conflict is a
semantic-invalid outcome with a deterministic diagnostic in the single
operation-result envelope and no success snapshot. Required unresolved or
ambiguous values likewise cannot succeed.

## Resolver and publication relationship

The [body-document contract](../body-document/README.md) owns the single
ordered source-to-graph operation, closed status algebra, precedence, and
diagnostic/resource rules. This graph contract defines graph-side work for
namespace/identity/reference, containment/typed-relation, normalization/
derivation, invariant, and publication phases. It does not create a second
pipeline or result envelope. Fatal failure blocks dependent work, independent
failures within a reached phase may accumulate deterministically, and only
complete valid-supported resolution may publish this graph as a successful
snapshot.

## Invariants and equivalence

Minimum Stage 1 graph invariants include:

- unique semantic addresses and one owner for each source namespace;
- one embodied root Part and exactly one containment path for every embodied
  Part, including every present optional module root;
- acyclic containment, with containment-cycle checks independent from typed
  relation-cycle checks;
- containment-provided reference-transform inheritance;
- the required axial, arm, and leg Joint/Part chain, with each required Joint
  linking structural parent to immediate child;
- exactly one proximal and one distal Part endpoint and one canonical typed
  frame record in each corresponding Part-local basis for every Joint;
- one Part-owned interface frame per Socket;
- exactly one host and one mating Socket per Attachment, with endpoint owners
  agreeing with host/module-root containment;
- exactly one incoming active Attachment per present attached module root and
  no incoming Attachment for an absent optional module;
- one active Attachment per host Socket initially; repeated endpoint pairs,
  host Socket reuse, zero incoming for a present attached root, and multiple
  incoming Attachments for a present attached root are separate invalid
  conditions, as are detached, cyclic, or dangling endpoints;
- sole resolved attached-root child-local containment placement derived in the
  host Part's local/reference basis from the host Socket, optional offset, and
  the inverse of the mating
  Socket frame after composing module-root-to-Socket-owner containment with
  that owner's local frame; any competing authored root-local placement must
  agree with this same canonical value within the later-defined tolerance,
  with provenance preserved;
- no Attachment-only articulation claim;
- finite normalized values, complete provenance, valid owner-plus-role
  addressing, declared source basis with recorded normalization provenance,
  and required values resolved and unambiguous; and
- deterministic ordering and lineage.

Violating containment, relation, endpoint, placement, provenance, or semantic
invariants yields an invalid-source or unsupported operation status according
to the body-document status mapping and never a compilable snapshot. A
relation cannot repair a failed containment invariant. These checks establish
semantic lineage and intent only; they do not prove a usable skeleton,
skinning, collision, contact, deformation, animation, or runtime performance.

Semantic equivalence compares durable identities, containment and typed
relations, canonical endpoint/interface frame records, normalized values,
provenance, and operation outcome. It ignores source text ordering and
incidental derived topology. A deterministic debug JSON view may assist
comparison, but canonical byte identity and hashing remain deferred.

Fixtures must cover bilateral/repeated modules; namespace ownership and full
remapping; explicit containment versus relation-only connectivity; the typed
articulation chain and immediate-child rule; optional-module placement,
offset, duplicate, and detached cases; overlapping regions; canonical frame
records and provenance; authored/defaulted/derived values; frame
normalization; measurement conflicts; invalid/unsupported outcomes; resource
limits and diagnostic truncation; and the cross-DR fixture matrix. The fixture
set is evidence planning, not proof yet.

# Resolved body-graph contract

Status: Proposed conceptual contract; CK-KICK-012 Batch 13/14 discussion-approved
canonical update. DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012
Revision 14 are Accepted with Owner approval Approved by Ben and Review
Complete after the current Double review at exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. DR-0013 Revision 12 is Accepted,
with Owner approval Approved by Ben and Review Complete at that exact target,
decided 2026-08-13. The earlier-predecessor
review at `763cff22d10f6491a05a28312a25250704543dcf` and immediate-predecessor
review at `9b96d18b115126ef09e54ad8c6f21749d5559ff6` are stale, with their
findings corrected in these revisions. The 9c governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. Review Complete is preserved evidence for the
accepted decisions. This document records those accepted comparator, claim
identity, and graph-collection-key directions as a Proposed concrete contract;
no acceptance of this specification, implementation, or readiness gate is
implied. See the [current review state](../../docs/project/status.md#current-review-and-future-activation-obligations)
and [decision registry](../../docs/decisions/registry.md) for DR ownership.
The CK-KICK-012 Batch 5 review at commit `a282dbabffd83afa4e62577086934d00f98e12c7`
is stale historical evidence. No acceptance is implied.

This document is the canonical specification authority for the resolved,
per-build semantic body graph. It owns typed concepts, explicit Part
containment, durable semantic identity, typed relations, Attachment
composition and placement, canonical frame records, provenance, graph-side
invariants, and successful in-memory snapshot-handoff conditions. It consumes the admitted source
model and operation envelope owned by the
[body-document contract](../body-document/README.md); it does not redefine
source encoding or bootstrap/status/resource admission.

The contract is conceptual and engine-independent. The authored document shape,
closed core vocabulary, explicit typed records, and stable references are owned
by the [body-document contract](../body-document/README.md); this document owns
their resolved graph meaning. The [semantic-address profile](../semantic-address/README.md)
owns exact durable address representation and equality. The [numeric and frame
profile](../numeric-frame-profile/README.md) owns canonical axes/units, numeric
ranges, rigid transforms, and typed tolerances. The [canonical-data profile](../canonical-data/README.md)
owns canonical bytes and hashing. Runtime representations remain outside this
contract. The concrete graph contract remains Proposed; its accepted
semantic-foundation direction does not activate runtime representations or a
readiness gate.

## Graph authority and identity

The graph is derived, build-scoped, inspectable, and reproducible when the
source, compiler/build identity, configuration, seed, and dependencies permit
reproduction. It is never a competing authored source. A validated snapshot
may be finalized and handed off in memory only for complete valid-supported
success. Invalid and unsupported partial graphs are non-compilable,
non-contractual debug data. Filesystem serialization and publication are
derived-output responsibilities of the [build-operation contract](../build-operation/README.md).

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

Each identity-bearing concept uses the structured address defined by the
[semantic-address profile](../semantic-address/README.md): `namespace`, ordered
outer-to-inner `anchors`, closed `kind`, and lexical `role`. Exactly one source
owns each namespace in a resolved source set. A colliding import requires an
authored, deterministic, collision-free remap covering every contributed
address from that namespace. Mesh, vertex, face, topology, LOD, and array
positions are artifact-local and never durable semantic identity.

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

The normalized model declares module instances separately from this tree; it
does not add a new identity-bearing graph concept. Each declaration has a
stable authored module-instance declaration address and records the module,
root-role/template reference, root Part when present,
module-instance anchor/provenance, presence and optionality, and whether
Attachment composition is required. An absent optional declaration retains its
declaration address and non-embodied root-role/template reference, but emits or
reserves no Part and no graph relation may target it. It participates in
declaration uniqueness, not the Part namespace. If the declaration later
becomes present, its Part identity is derived deterministically from the
module-instance anchor and root role. This does not add an eighth
identity-bearing graph concept. Optional absence and a present-but-unattached
root are distinct states. A present Attachment-required root with zero incoming
active Attachments is invalid. Nested module instances use distinct Socket
instances and preserve their containment/source provenance.

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

Each Socket is owned by exactly one Part and owns one intrinsic interface-frame
record expressed in that owning Part's local/reference basis. Host and mating
are contextual endpoint roles supplied by an Attachment that references the
Socket; neither role changes the Socket's intrinsic frame semantics.

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
Socket has total active capacity one across host and mating roles, so cross-role
reuse is invalid as well as same-role reuse.
Repeated endpoint-pair use, host Socket reuse, mating Socket reuse by distinct
active Attachments (including distinct hosts or nested attached roots), zero
incoming Attachments for a present attached root, and multiple incoming
Attachments for a present attached root are separate invalid conditions.
Mating Socket reuse has its own deterministic diagnostic concept, distinct from
host reuse and repeated endpoint pairs. Attachment cycles, invalid or dangling
endpoints, and a mismatch between Attachment endpoints and the declared
containment parent are also invalid.

Attachment placement is the attached root's sole resolved child-local
containment placement relative to its host Part. For the typed transform
contract, `T_A←B` maps coordinates expressed in B into A. Let H be the host
Part, R the attached subtree root Part, M the mating Socket owner Part, and
`S_h` and `S_m` the host and mating Socket frames. Let `O_(S_h←S_m)` map
mating-Socket coordinates into host-Socket coordinates. The conceptual
host-local equation is:

`T_H←R = T_H←S_h · O_(S_h←S_m) · (T_R←M · T_M←S_m)^−1`

Composition uses the stated coordinate bases and order, with the rightmost
transform applied first. Every transform entering this composition must be
finite, non-degenerate, and invertible under the declared transform profile.
A source-caused violation is `invalid-source`; an implementation failure on an
admissible transform is `internal-failure`. Readiness 2 fixes the structural
carrier as exactly three translation components plus four explicit `xyzw`
quaternion components, with no scale or shear fields, as defined by the
[numeric and frame profile](../numeric-frame-profile/README.md). Readiness 3
is a distinct successor transaction that admits canonical numeric semantics,
conditioning thresholds, ranges, tolerances, and expected graph snapshots; it
cannot replace the Readiness 2 carrier. An optional authored
Attachment offset, if admitted, is part of the
host/mating alignment transform `O` in that typed basis. Descendant placement is
subsequently inherited only by the ordinary containment path. If an
independently authored root-local placement controls the same degrees of
freedom, it must compare with this same canonical resolved child-local value
using the one R3 authored-conflict comparison profile; disagreement that fails
the profile's bounds is semantically `invalid-source`, with no warning-only
success, silent overwrite, repair, winner, or successful snapshot. Authored
and derived provenance are preserved.

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

## Frames, profiles, and values

The resolved graph consumes the required source basis: length unit,
handedness, up, and forward. Every measurement and transform retains its
owner, role, and frame/context. Stage 1 uses owner-specific roles: a Part has a
local/reference frame, a Joint has proximal and distal frames, and a Socket has
one intrinsic interface frame. Host and mating are contextual endpoint roles
on an Attachment that references Sockets; they are not intrinsic Socket frame
roles. Source profiles initially reference only the semantic numeric-domain
profile; operational resource and diagnostic profiles remain operation/fixture
context. There is no per-value unit override initially. Readiness 2 checks
shape, references, provenance, and the rigid-transform carrier: exactly three
translation components and exactly four quaternion components in explicit
`xyzw` order, with no scale or shear fields. The [numeric and frame
profile](../numeric-frame-profile/README.md) owns the canonical basis, finite-
number and normalization semantics, ranges, conditioning, and tolerances.
Readiness 3 admits those rules in a separate successor transaction and never
reselects the carrier.

## Values, normalization, and provenance

Authored local/reference transforms own reference-frame placement. Typed
dimensions own declared size or extents. Landmark and anchor records retain
owner, role, frame/context, and authored/defaulted/derived provenance. Ratios
are derived and inspectable, not authored authority. Sources declare units,
handedness, up, and forward axes; resolution normalizes values into the
canonical basis owned by the [numeric and frame profile](../numeric-frame-profile/README.md)
and records conversion provenance. The profile owns finite-number and
normalization semantics, ranges, and tolerances; the initial structural
carrier has no scale or shear fields. Resolved values that use a
permitted exact contract/profile default retain `defaulted` provenance and the
stable default-rule identity. Identity, containment, module presence, basis,
and grammar-required values are explicit; no null-as-missing, implicit zero,
neighbour inference, or hidden equation is admitted. Core typed collections
remain present even when empty under the source contract.

When a claim targets the same owner address, property role, and frame/context,
the resolver first normalizes every value into the identical canonical
local-to-parent frame. Authored claims and explicit invariants must be jointly
satisfiable by direct componentwise translation comparison and the q/-q
rotation predicate in the numeric/frame profile. Derived or defaulted values
never override authored claims, and no hidden inferred equation may manufacture
a winner. A composition residual may be retained separately for diagnostics or
snapshot checks, but it is not the same-target validity predicate. A conflict
is a semantic-invalid outcome with a deterministic diagnostic in the single
operation-result envelope and no success snapshot. Required unresolved or
ambiguous values likewise cannot succeed.

### Normative claim comparison and representative outcome

The [numeric and frame profile](../numeric-frame-profile/README.md) owns the
comparison arithmetic; this graph contract owns grouping claims by the
normalized target and the resulting graph/provenance outcome. Exact discrete
claims remain exact. Scalar and translation components use the profile's exact
inclusive absolute-plus-relative predicate with componentwise L-infinity
translation semantics. Quaternion claims are normalized and compared with the
profile's q/-q canonical-tuple chord predicate and dot-zero `+1` sign tie;
after deterministic normalization, the tuple-distance predicate uses no square
root, norm, or transcendental operation. The normalization itself uses the
required correctly rounded binary64 square root owned by the numeric/frame
profile. The profile's
finite `H` is an inclusive Euclidean half-threshold over post-normalization
canonical tuples, not an angular guarantee. Transform claims are normalized into the
same canonical local-to-parent frame for direct comparison. A residual
`B * inverse(A)` may remain a separately named composition diagnostic or
snapshot check with its own profile semantics; no approximate-identity shortcut
is allowed for claim validity.

For competing authoritative claims with the same target, every unordered pair
must pass. Group by structured claim ID first: same ID with the same normalized
value is evaluated once while retaining all occurrences and provenance; same ID
with a different normalized value is an invalid-source collision. Valid pairs
are sorted by claim ID and the first failing sorted pair is reported
deterministically, while pair validity remains unordered. The resolver must not
use transitive clustering, a first winner, approximate identity, or
deduplication. One failing pair makes the source deterministically
`invalid-source` with a conflict diagnostic; no passing pair can rescue it.
The normalized binary64 representative tuple is value-type-specific: scalar
`(value)`; translation/vector `(x,y,z)` in declared semantic component order;
quaternion `(x,y,z,w)` after normalization and q/-q/sign canonicalization; and
rigid transform `(tx,ty,tz,qx,qy,qz,qw)`. Any later numeric type must define its
tuple in the numeric/frame profile before use. Lexicographic comparison uses an
exact mathematical total order (or equivalent sign-aware bit key) over
normalized finite binary64 values, with `-0` already `+0`; claim ID breaks ties
only when the entire value tuple is exactly equal. Preserve provenance for
every claim, including claims not selected as the representative.

Stable claim identity is conceptual versioned `claim-id-1`, structured from
canonical target, closed claim kind, typed source-document/namespace identity,
stable authored record address, typed property role, and explicit authored claim
key or absence for intentional multiplicity. Its wire-independent total order
is owned by the [semantic-address profile](../semantic-address/README.md). Its
exact six-field component precedence is canonical target, claim kind, source-
document namespace, authored record address, typed property role, and explicit
claim key or absent. The canonical target uses its owning
structured address order; closed claim kind and typed property role use
profile-defined semantic tag ranks; typed namespace and address segments use
normalized identifier Unicode-scalar lexical order with structured
prefix-before-extension ordering; and absent claim keys sort before present
keys, whose values use that same identifier order. The claim-kind and
typed-property-role rank tables are mandatory, versioned activation inputs,
complete and injective over each admitted closed set; missing, duplicate, or
unknown kind, role, or rank entries fail activation. An activated schema must
bijectively map wire values to those conceptual types/ranks and must not infer
order from wire spelling. No canonical claim ordering, digest, or resolver
activation occurs before both tables exist. It never uses a raw
JSON pointer, array/traversal/allocation order, thread, time, or generated
identifier; a raw pointer is diagnostic provenance only. Same-ID/same-value
occurrences are evaluated once while provenance remains, same-ID/different-
value is an invalid-source identity collision, and different IDs use all-pairs
evaluation in sorted order. Exact wire fields/enums are schema-gated; an
activated schema must provide stable record address, typed property role, and
multiplicity keys.
Local claim-ID and multiplicity semantics are separate from the generic
canonical collection key.
Adding a passing claim can change the representative and therefore a snapshot;
a changed comparison profile or expected fixture requires its profile/fixture
successor process.
Authored-conflict and expected-snapshot comparisons remain separate profiles,
and their constants remain experiment-gated. R3 binds exactly one separately
content-bound authored-conflict profile, frozen from a bounded successor
experiment. The activation closure separately binds (a) the profile
definition/content identity, (b) the resolver/source implementation closure,
and (c) a resolver binding plus complete build request that reference exactly
one authored-conflict profile. Mismatch across these activation inputs fails
closed; there is no caller-selected or global-default tolerance fallback. The
generic resolver implementation need not itself reference the exact profile.
Exact zero and post-hoc widening are not allowed. Until that profile and its
resolver binding are admitted, R3 remains inactive.

This local claim representative rule is not a canonical key for unrelated
unordered collections. Every graph concept collection still uses the generic
structured collection address plus its declared owner-role/claim collection
key, with that owner retained by the canonical-data profile. Claim identity
and claim multiplicity must not be substituted for collection identity.

## Resolver and publication relationship

The [body-document contract](../body-document/README.md) owns the single
ordered source-to-graph operation, closed status algebra, precedence, and
diagnostic/resource rules. This graph contract defines graph-side work for
namespace/identity/reference, containment/typed-relation, normalization/
derivation, and invariant phases. It does not create a second pipeline or
result envelope. Fatal failure blocks dependent work, independent failures
within a reached phase may accumulate deterministically, and only complete
valid-supported resolution may finalize and hand off this graph as a successful
in-memory snapshot. The [build-operation contract](../build-operation/README.md)
separately owns serialization, staging, publication, and artifact identity.

## Invariants and equivalence

Minimum Stage 1 graph invariants include:

- unique semantic addresses and one owner for each source namespace;
- unique authored module-instance declaration addresses, including absent
  optional declarations; absent declarations reserve no Part identity and no
  relation endpoint may target their non-embodied root role;
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
- one active Attachment per host and present mating Socket initially; repeated
  endpoint pairs, host Socket reuse, mating Socket reuse by distinct active
  Attachments (including distinct hosts or nested attached roots), zero
  incoming for a present attached root, and multiple incoming Attachments for a
  present attached root are separate invalid conditions, with a distinct
  mating-reuse diagnostic concept; detached, cyclic, or dangling endpoints are
  also invalid;
- sole resolved attached-root child-local containment placement derived in the
  host Part's local/reference basis from the host Socket, optional offset, and
  the inverse of the mating
  Socket frame after composing module-root-to-Socket-owner containment with
  that owner's local frame; any competing authored root-local placement must
  agree with this same canonical value within the one R3 authored-conflict
  comparison profile, with provenance preserved; disagreement is
  `invalid-source` and produces no successful snapshot;
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
comparison; canonical bytes and digest domains are governed by the
[canonical-data profile](../canonical-data/README.md).

Fixtures must cover bilateral/repeated modules; namespace ownership and full
remapping; explicit containment versus relation-only connectivity; the typed
articulation chain and immediate-child rule; optional-module placement,
offset, duplicate, and detached cases; overlapping regions; canonical frame
records and provenance; authored/defaulted/derived values; deterministic
normalization and correctly rounded square-root fixtures; direct common-frame
comparison and order reversal; measurement conflicts; duplicate/collision
claim IDs, pair ordering, and smallest representative tuples; pairwise claim
permutations and non-transitive triples; q/-q and dot-zero sign ties; transform
residual diagnostics; representative-selection and provenance-retention
consequences; invalid/
unsupported outcomes; resource limits and diagnostic truncation; and the
cross-DR fixture matrix. The fixture set is evidence planning, not proof yet.
The minimum R3 morphology boundary additionally includes representative valid
bounded-family, semantically invalid bounded-family, and well-formed
outside-envelope fixtures, including an extra-limb/quadruped (or equivalent)
request and an arbitrary/unbounded attachment graph. A recognized
bounded-family contradiction is `semantically invalid` / `invalid-source`;
recognized outside-envelope input is `well-formed-but-unsupported` /
`unsupported`. Malformed or unrecognized input remains under body-document
rules, and the cases do not imply exhaustive arbitrary-morphology support.
The [fixture-manifest and admission contract](../fixture-manifest/README.md)
owns the immutable reviewed tree and payload binding, preflight, and staged
Readiness 2/3 corpus; it does not change graph semantics or activate these
fixtures.

# DR-0006: Durable semantic and artifact/build identity

ID: DR-0006

Scope: Specification and architecture

Status: Proposed

Revision: 12

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Discussion approval date: 2026-08-13

Supersedes: —

Superseded by: —

## Context

Creature Kernel must refer to semantic parts and relationships across
regeneration while distinguishing the generated artifacts and builds that
implement those semantics. Generated topology can change as methods, parameters,
or quality levels change. Mesh or array positions therefore cannot be durable
identity.

This is an asset and semantic design boundary, not a governance audit
provenance model. Repository history and decision-record review evidence remain
governed by the existing process.

Revision 2 recorded Ben's CK-KICK-012 Batch 1 identity selection, and Revision
3 recorded its first review-resolution batch. On 2026-08-11 Ben approved the
CK-KICK-012 Batch 3 namespace-resolution decision recorded in Revision 4. On
2026-08-12 Ben approved the Batch 9 candidate-versus-committed artifact
identity lifecycle at the identity boundary, and then approved the Batch 10
stable request/artifact identity and collision-resolution rules recorded in
Revision 6. These discussion approvals are not DR acceptance: this revision
remains Proposed with
Owner approval Pending until a current-revision review and Ben's owner
disposition are recorded. All earlier revisions and their reviews remain
preserved as stale historical evidence; the Revision 4 current-review
artifacts are stale after this material Revision 5 change, and a fresh current
review is pending. The Revision 5 current-review artifacts are also stale
after this material Revision 6 change. Ben approved the Batch 10 C1 identity
resolution and its DR-0006 consequence of a simplified, externally admitted
fixture route on 2026-08-12. This material Revision 7 change makes the
Revision 6 current-review artifacts stale; a fresh current review is pending.
On 2026-08-12 Ben approved the next machine-contract batch: typed semantic
address encoding and the project-owned canonical-byte and digest profile.
This material Revision 8 change makes the Revision 7 review evidence stale;
a fresh current review is pending.

On 2026-08-13 Ben approved all five CK-KICK-012/013 Batch 13 resolution
directions in discussion: deterministic same-target comparison and authored
claim identity; a future adapter's unit-scale and two-tier guarantee boundary;
typed total keys for every semantically unordered collection; a separate
scoped implementation-content binding for readiness transactions; and one
diagnostics owner with a mandatory bootstrap registry/profile. This discussion
approval revises the proposal only. It accepts no DR, creates no schema,
fixture, parser/resolver, implementation, adapter, experiment, or package, and
activates no readiness gate. The Revision 8 review artifacts are stale after
this material Revision 9 change; their findings and history remain preserved
below. Owner approval remains Pending and a fresh current-revision review is
required.

On 2026-08-13 Ben approved the four Batch 13 review-resolution directions
for this record in discussion: canonical-tuple chord comparison without an
angular guarantee; versioned structured claim identity; a mechanically closed
and filesystem-safe readiness implementation binding; and explicit separation
of implementation, fixture, request, attempt, and artifact identities. This
Revision 10 records those settled directions as Proposed only. It creates no
schema, fixture, parser/resolver, readiness gate, implementation, adapter,
experiment, or package. The Batch 13 Revision 9 review is stale evidence after
this material revision and remains preserved below; Owner approval remains
Pending and a fresh current-revision review is required.

On 2026-08-13 the fresh technical-review dispositions were applied in the
Revision 11 proposal: build requests now reference the exact implementation-
content-binding and dependency-closure identities used for execution; the
wire-independent `claim-id-1` comparator is defined by conceptual type/rank
and normalized identifier order; the quaternion normalization versus
already-normalized tuple-distance wording is corrected; and adapter profile
validation status remains an explicit pre-activation choice rather than a
source-admission mapping. The exact-target Double review at commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale for this Revision 12
successor. Revision 12 applies the final comparator/rank-table gate, removes
the stray numeric `Runtime` wording, and preserves the retained-human T4 gate;
the current Double review at `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`
is Complete. Its governance findings were corrected mechanically and its
technical pass found no findings / Ready for PR at High confidence. The record
remains Proposed with Owner approval Pending; review evidence is not acceptance.

## Decision

Use two identity levels and an explicit semantic-address boundary:

1. Durable semantic identity names parts, regions, joints, attachments,
   capabilities, and related semantic concepts across regeneration. Each
   concept uses a structured semantic address composed of the source namespace,
   authored stable module-instance anchors, semantic concept kind, and a
   role-local key. Module-instance anchors are authored semantic scope, not an
   incidental ownership path or array order. The exact address must be unique
   within a resolved source set. Exactly one authoritative source owns each
   source namespace in that set; every imported namespace must be unique, with
   no implicit or shared ownership. A collision is invalid unless the import
   contains an explicit, authored, deterministic, collision-free remap covering
   every semantic address contributed under that imported namespace. Source,
   import, and remap syntax remain deferred; the machine identity profile is
   proposed below.
2. Separate artifact/build identity and provenance distinguish generated outputs,
   including the resolved graph snapshot, mesh, rig, colliders, runtime package,
   and other build products.

### Structured semantic-address profile

The machine form of a semantic address is a typed JSON object with exactly
`namespace`, ordered `anchors`, `kind`, and `role` members. `namespace` and
each anchor are authored scope identifiers; `kind` is a closed concept-kind
identifier; and `role` is the key local to that concept kind. Machine
identifiers use a versioned restricted lower-case ASCII profile. Anchor order
is significant, object-member order is not, and structural equality compares
the typed members rather than a delimited string. The profile performs no case
folding, delimiter parsing, filesystem mapping, or implicit index insertion.
Unicode display labels are separate non-identity data. Address profile
revision is part of the identity-rule inputs and must be recorded with any
identity digest.

This typed object is deliberately a machine identity boundary, not a promise
about source syntax or user-facing labels. The source representation may
choose a later syntax only if it resolves to this profile without changing
address equality or namespace ownership rules.

When an address is used as an ordering key, compare components in exactly this
precedence: `namespace`, ordered `anchors`, `kind` by rank, then `role`. The
current address-kind rank table is frozen in vocabulary order: `part` 0,
`joint` 1, `socket` 2, `attachment` 3, `region` 4, `capability` 5, and
`field` 6. The table is part of the versioned address profile; changing it or
the closed vocabulary requires a profile successor.

### Conceptual authored claim identity

Versioned conceptual `claim-id-1` is a structured tuple, not a serialized
string: `(canonical_target, claim_kind, source_document_namespace,
authored_record_address, typed_property_role, explicit_claim_key_or_absent)`.
The target is
the canonical semantic target; the claim kind is a closed kind owned by the
active contract; source-document/namespace identity is typed and normalized;
the authored record address and typed property role are durable and stable; and
the explicit claim key is present only when the schema permits intentional
repeated claims.
The tuple has the wire-independent total order owned by the
[semantic-address profile](../../spec/semantic-address/README.md):
`canonical_target` uses its owning structured semantic-address order;
`claim_kind` and `typed_property_role` use profile-defined semantic tag ranks,
not wire enum spelling; typed source-document/namespace identity, authored
record-address segments, and present claim keys use the profile's restricted
normalized identifier Unicode-scalar lexical order (the current ASCII subset);
structured address sequences compare lexicographically with prefix before
extension; and the claim-key sum type orders absent before present. An
activated schema must bijectively map wire values to these conceptual types
and ranks and must not infer order from serialized spelling. Unordered pairs
are represented conceptually as `(min_id, max_id)`; the same ID with the same
normalized value is one semantic claim for evaluation while every occurrence
and provenance is retained, and the same ID with a different value is an
identity collision. Different IDs are evaluated as all unordered pairs in
this order, with the first failing pair the deterministic conflict
representative and the lexicographically smallest value tuple selected only
after all pairs pass. The claim-kind and typed-property-role rank tables are
mandatory, versioned activation inputs. Each table must be complete and
injective over its admitted closed set; a missing, duplicate, or unknown kind,
role, or rank entry fails activation. No canonical claim ordering, digest, or
resolver activation may occur before both tables exist, and serialized wire
spelling is never an ordering fallback. A raw JSON pointer is diagnostic
provenance only; an activated schema must supply the stable record address,
typed property role, and any multiplicity key.

### Canonical bytes and digest profile

Use a project-owned canonical JSON profile after semantic normalization. It is
strict duplicate-free UTF-8 JSON with deterministic object ordering. Every
semantically unordered collection or projection has an owner-defined typed
total key and an explicit uniqueness or multiplicity rule; no canonicalizer
may fall back to source order/index, traversal or allocation order, object
serialization, or raw element bytes. Unicode is not normalized, machine
identifiers remain within the restricted ASCII profile, and numeric
representation follows the versioned semantic numeric profile owned by
DR-0011. The profile uses unambiguous versioned framing and domain-separated
SHA-256 digests, rendered as `sha256:` followed by lower-case hexadecimal.

The initial canonical-key ownership is explicit. Graph concepts use their
structured semantic address. Module declarations use a tagged declaration
address. Owner-role records use a tagged kind, owner address, and role, with
frame/context/claim identity when required. Fixture entries use fixture ID;
duplicate IDs or paths are invalid. External path sets use a normalized safe
relative path as the key, with mode and content retained in the entry
projection. Dependencies use locator and role plus a distinguishing revision
identity. Other build arrays must receive an owner-defined key before
activation. Diagnostics use a profile-defined occurrence key and are not
silently deduplicated. Duplicate keys fail only where the owner declares a
uniqueness collection; legitimate multisets, repeated claims, and diagnostics
declare multiplicity or occurrence/claim identity. Canonicalization fails when
the owner has not supplied the required key/rule.

The initial digest domains are exact source bytes, normalized source, resolved
graph, build request, fixture manifest, and raw published artifact. Raw-byte
and semantic digests remain distinct. Attempt IDs, timestamps, staging and
host paths, allocation order, logs, and human-readable diagnostic text are
excluded unless a later domain explicitly owns them. The initial profile does
not add CBOR, signatures, Merkle structures, or multiple digest algorithms.
Exact framing, field spelling, and the numeric canonicalization constants are
activation prerequisites and belong to the canonical specifications; they are
not implementation freedom once activated.

For same-target authored claims, use conceptual `claim-id-1` as defined above:
typed canonical target, closed claim kind, typed source-document/namespace
identity, stable authored record address, typed property role, and explicit
claim key or absence. It is never an array, traversal, allocation, thread, time, or
generated index. Claim IDs use the wire-independent component order defined by
the semantic-address profile, and canonical unordered pairs are
`(min_id,max_id)`. Same-ID/same-value
occurrences are evaluated once while every occurrence and provenance is
retained; same-ID/different-value is an invalid-source identity collision;
different IDs use all-pairs evaluation in sorted order. DR-0011 owns the
comparison mathematics; this identity boundary owns the durable identity
inputs, order, multiplicity, and their exclusion of incidental ordering.

Diagnostics have one owner: the diagnostics specification owns registry,
domain, class, occurrence, profile, ordering, and compatibility meaning.
Body-document and build-operation contracts own only top-level status and
precedence. The initial closed domains are source-admission, dependency,
semantic-identity, graph-structure, frame-numeric, resource, execution-trust,
publication, and inspection; narrower categories such as resolver-invariant
and worker-protocol are stable classes within that owner. A resource profile
is operational input, not diagnostic meaning. A tiny mandatory bootstrap
registry/profile is always known. An unknown required registry/profile uses
the existing unsupported status and effective bootstrap profile, carries
bounded requested identifiers, and selects a deterministic primary; it never
emits under an unknown profile or silently downgrades. Exact ordinary codes,
field spellings, and profile identifiers remain fixture-gated.

### Deterministic same-target comparison boundary

Same-target transform claims are first normalized into the same canonical
local-to-parent frame. Translation is compared directly componentwise; rotation
uses the q/-q-invariant rule below. Swapping claims therefore produces exactly
the same result. A residual transform is permitted only as a separately named
diagnostic/composition comparison; it is not authored same-target equality.

The scalar predicate
`abs(a-b) <= A + R*max(abs(a),abs(b))` is decided over exact dyadic values
decoded from admitted finite binary64 values, using bounded integer/dyadic
arithmetic. Rounded floating intermediates and an undefined “equivalent
monotonic” evaluation are not permitted at the inclusive boundary. After
deterministic quaternion normalization, the already-normalized
tuple-distance predicate uses no square root, norm, `asin`, or `sin`. The
normalization itself uses the required correctly rounded binary64 square root
specified below. The admitted
profile stores finite binary64 half-threshold `H` for canonical-tuple chord
semantics: after deterministic normalization and sign selection, `H` is the
half-threshold in the Euclidean space of the canonical quaternion tuples. Choose
the quaternion sign from the exact dyadic dot product (zero chooses `+1`),
compute `di = qa_i - s*qb_i`, and accept iff `sum(di^2) <= (2H)^2` with exact
dyadic arithmetic, inclusively. `H` and any nominal angular `theta` are
profile/calibration metadata only; this contract does not claim that `H` or
`theta` bounds represented angular error. A future represented-direction or
angular guarantee requires a new comparison-profile revision and successor
evidence. Runtime transcendental recomputation is forbidden.

Source quaternion normalization is deterministic: exact max-absolute-component
scaling, fixed `xyzw` divisions, fixed left-to-right squared-sum without
reassociation or FMA, correctly rounded binary64 square root, fixed divisions,
drift/near-zero validation, then canonical sign by the first nonzero `wxyz`
component being positive. The profile assumes round-to-nearest ties-to-even,
no FTZ/DAZ, and no ambient rounding mode; a platform unable to provide the
required square root is unsupported. Numeric bounds remain experiment-gated.

Unordered claim pairs are evaluated in sorted claim-ID order; the first failing
sorted pair supplies deterministic conflict detail. After all pairs pass, select
the lexicographically smallest value-type tuple under the exact finite-binary64
total order (`-0` is already `+0`); claim ID breaks exact tuple ties only.
All occurrences and provenance remain available.

At the artifact-identity level, distinguish a staged candidate from a
committed artifact. A staging manifest carries a non-authoritative candidate
artifact identity; it is not a committed artifact and must not be adopted by
inspection as one. Successful atomic publication promotes that same candidate
identity to committed artifact identity; publication does not mint a second
artifact identity. Every invocation has a unique `attempt_id`, including when
failure prevents a complete request from being established. A deterministic
`build_request_id` exists when the complete outcome-affecting request is
available and is stable across retries; neither it nor `attempt_id` is a
committed artifact identity. A committed artifact identity exists only for a
successfully published artifact or bundle. An identical already-published target may be
recognized as the same committed identity by the build operation; a different
or unverifiable target is not adopted. DR-0006 owns this candidate-versus-
committed identity lifecycle and lineage relationship; DR-0013 owns the
operation, staging, collision, and publication boundaries, and a canonical
build-operation specification owns exact field spelling and format.

### Stable request identity and publication comparison

The per-execution `attempt_id` is unique to one invocation and is never part of
committed or hashed bytes, output-location derivation, candidate identity, or
idempotent lineage equality. It exists only in the returned operation envelope,
invocation-owned staging metadata, and logs. A deterministic
`build_request_id` is stable across retries of the same outcome-affecting
request. It includes the authoritative source or source-set identity, an
exact reference to the implementation-content-binding identity used for
execution, an exact reference to the dependency-closure identity used for
execution, compiler/toolchain/build-implementation identity, contract/schema/
profile revisions, configuration, seed, backend/capability/protocol revision,
and every output-affecting target or platform-profile input. These are
identity references only: the request projection does not inline raw
implementation path/mode/content entries or raw dependency sets, which remain
owned by their separate binding domains. Fixture-payload identity is an
admission input, not a build-request identity input, and attempt identity is
excluded. Omitting an outcome-affecting input or either exact execution
binding reference is an identity error, not an implementation choice.

For each artifact role, the candidate artifact identity is derived from the
`build_request_id`, that artifact role, and an artifact-identity-rule revision.
Successful publication promotes that same candidate identity; it does not
mint a new identity. The proposed canonical-byte and digest profile below is
an activation prerequisite for this identity boundary, not optional
implementation freedom.

Committed success artifacts and their manifests contain no attempt-local data.
Diagnostics-only failure bundles are not persisted as committed artifacts in
this initial boundary; failure returns the authoritative CLI/API envelope. A
future persisted failure-evidence facility requires a separately decided
attempt-evidence identity and lifecycle.

After an atomic no-replace publication reports a concurrent collision such as
`EEXIST`, the operation inspects the winner. A complete manifest with identical
committed identity, stable build-request lineage, hashes, and sizes is an
already-published success. A different lineage or identity is an
`output-failure` target conflict. If the same deterministic request and
candidate identity produce byte-different output, comparing the deterministic
committed manifest projection plus every listed output hash and size, the result is
`internal-failure` for nondeterministic output, not semantic equivalence.
The required evidence fixtures cover a first build, a retry with a new attempt
and the same request, a concurrent identical winner, a lineage change, and
same-request byte divergence.

Every outcome-affecting external authored asset, including an artist mesh, is
an exactly versioned dependency of the authoritative source set. Its
semantic mapping and exact dependency revision belong to source/build
provenance; the mesh itself does not become semantic truth.

Readiness transactions retain the existing fixture-payload scope: manifest,
declared schema, fixtures, and snapshots. Separately, each transaction that
activates implementation includes an external, domain-separated,
versioned implementation-content binding. The binding is an ordered set of
normalized relative paths, modes, and raw contents plus an aggregate SHA-256.
The closure is explicit and mechanically checkable. The implementation-content
binding owns selected repository paths, modes, and raw contents: Rust/Cargo
production sources and workspace/crate manifests, repository Cargo
configuration or a recorded absence, `Cargo.lock`, the rust-toolchain
declaration, build scripts, and declared compile/code-generation inputs.
Dependency closure separately owns registry, vendored, path-dependency, and
proc-macro provenance/content. Build-request identity separately owns the
selected packages, targets, target triple, features, profile, approved
environment/tool/configuration inputs, and exact locked/offline command. The
activation closure manifest binds or references all three, while keeping
implementation binding, dependency closure, build-request identity, attempt
identity, and fixture-payload binding distinct. Opaque Git/native/codegen
inputs require an explicitly reviewed vendored snapshot escalation. Reviewed
commit provenance is evidence, not equality binding; generic host, rustc, and
hardware metadata is evidence unless a platform-reproducibility claim binds it.
A locked/offline, private read-only activation snapshot is rooted at an opened
repository descriptor and uses descriptor-relative no-follow reads. Traversal,
absolute paths, symlinks, special files, and submodules are rejected in entries
or ancestor components. Ancestors must be descriptor-opened no-follow
directories; a final regular-file entry is rejected when `st_nlink != 1` and is
eligible only with mode `100644` or `100755`. Descriptor identity, type, and size are checked
consistently. Normal directory hardlink counts are not rejected. The profile
excludes the whole repository, mutable caches, unlisted inputs,
approval/successor records, Git commit identity, and unspecified host state. It
is proportional to the current hobby threat model, not a general sandbox.
Post-merge and immediately pre-trigger, implementation content and dependency
content are recomputed from a fresh immutable snapshot, while build-request
identity is revalidated against the exact bound request. A mismatch blocks
activation and requires an explicit successor. This remains a Proposed contract
and does not claim that the preflight or snapshot machinery is implemented.

Future adapter profiles are orthogonal identity inputs, not alternate semantic
identity. A post-R3 profile declares a signed-permutation `C`, finite positive
scale `s` (engine length units per canonical metre), target precision, domain
and narrowing/overflow/underflow/subnormal policy, and a guarantee tier. Length
points, positions, translations, displacements, dimensions, radii, and extents
map by `sC/s`; directions and normalized normals by `C`; rotations by
`C R C^-1`; and rigid transforms by `D H_c D^-1` for `D = diag(sC,1)`, with
inverse `D^-1`. Quaternion conversion derives from the rotation map or a
proven equivalent. The default/minimal tier promises storage/output
conversion only; an optional runtime-conformance tier adds engine arithmetic,
probes, and fixtures. Binary32 may exclude subnormal-dependent values, and a
profile promising subnormal runtime preservation must probe FTZ/DAZ. A failed
required capability is unsupported; an in-domain overflow or disallowed
underflow during trusted conversion is output-failure. The core binary64
snapshot is unchanged. Malformed adapter profile/request status ownership
remains a retained-human choice: Ben must explicitly dispose of the
request-validation mapping before any adapter profile or schema activates.

Mesh, vertex, face, triangle, LOD, and array indices are ephemeral and must not
be promised stable through topology changes. Semantic addresses must not be
derived from incidental path, ordering, geometry, artifact identity, topology,
or content hash. Clone, rename, split, merge, and replacement require explicit
future alias, remap, and lifecycle rules; those exact rules remain deferred, as
do migration, runtime swap behaviour, and external mapping rules. The
canonical address and digest profile below is proposed, while exact source
field spelling and later lifecycle rules remain activation obligations.

Identity continuity is promised only while the authored semantic address and
concept remain unchanged across parameter, geometry, topology, LOD, and compiler
regeneration. Rename, deletion/reuse, clone, split, merge, replacement,
aliases, and remaps have no continuity promise until those lifecycle rules are
defined.

## Consequences

- Semantic references for an unchanged authored address and concept can survive
  regeneration without requiring stable mesh topology.
- Structured authored semantic addresses are independent of incidental
  structure and remain inspectable across regeneration.
- Artifact/build inspection can distinguish derived outputs without making them
  competing authored sources.
- External authored assets can be traced to the exact source dependency revision
  that affected a build without confusing the asset with semantic identity.
- Topology-index references are valid only within their ephemeral artifact/build
  context.
- Namespace ownership and collision handling are part of the semantic-address
  boundary: load order and hidden merge rules cannot decide identity. A full
  authored remap is required when an import intentionally enters a colliding
  namespace.
- Specification must define the relation between semantic concepts and derived
  artifacts, plus lifecycle/remap behaviour, before durable external contracts
  are promised.
- Candidate artifact identity is non-authoritative while staged and is promoted
  unchanged to committed identity only by successful atomic publication. Build
  identity remains independent and exists for failures; an already-published
  identical target can be recognized as the same committed identity, while an
  inconsistent or unverifiable target cannot be adopted. DR-0013 owns the
  operation/publication mechanics and the canonical build-operation
  specification owns exact format.
- The exact meaning and admissible form of an external dependency revision is
  a nonblocking later obligation; it must be settled before external authored
  dependencies activate.
- A retry can use a new `attempt_id` without changing target location or
  idempotent lineage equality, while every outcome-affecting request input,
  including exact implementation-binding and dependency-closure references,
  is included in deterministic `build_request_id` construction. Candidate
  identity is role- and identity-rule-revision-derived, and a successful
  publication preserves it unchanged.
- Concurrent collision inspection distinguishes an identical committed winner
  from a target conflict; same-request byte divergence is a trust failure, not
  semantic equivalence. Canonical identity bytes/hashing must be selected
  before activation.
- Committed success bytes and manifests exclude attempt-local data. The initial
  failure path returns the authoritative operation envelope rather than a
  committed diagnostics-only bundle; any future persisted failure evidence
  needs a separate attempt-evidence identity decision.
- Semantic addresses can be compared without delimiter escaping, display-name
  localization, filesystem rules, or array-order accidents. A profile revision
  makes any future machine-address change explicit rather than silently
  changing identity.
- Domain-separated canonical digests make source, normalized semantic, build,
  fixture, and raw-artifact identity distinct. Human diagnostics and execution
  traces cannot change a deterministic committed identity.

## Alternatives Considered

### One identity space for semantic concepts and generated artifacts

Simple initially, but topology changes would conflate meaning with
representation and make regeneration or LOD changes break durable references.

### Generated mesh and array indices as durable identity

Readily available to geometry tooling, but incidental to the semantic body and
not stable through topology changes.

### Semantic identity without artifact/build identity

Preserves meaning, but loses the ability to distinguish derived outputs, build
provenance, and the concrete representation being inspected or loaded.

### Explicitly key every expanded concept

This avoids resolver-derived addresses, but forces authors to flatten every
repeated or bilateral module and undermines reusable procedural grammar.

### Opaque UUID identity

Opaque UUIDs avoid textual collisions but do not by themselves define stable
identity for repeated template instances, concept kinds, or deterministic
regeneration, and are harder for humans and external agents to author.

### Broad continuity across structural edits

Promising identity across rename, deletion/reuse, clone, split, merge, or
replacement would be convenient for consumers, but continuity is ambiguous
without explicit alias/remap lifecycle semantics. Revision 3 therefore limits
the promise to an unchanged authored semantic address and concept.

### Permit implicit namespace sharing or partial collision remaps

This might make imports shorter, but it would leave ownership and the affected
semantic addresses dependent on loader order or incomplete declarations. It is
not selected: each namespace has one owner, and a collision requires an
authored deterministic remap covering the imported namespace's full semantic
contribution.

### Use per-invocation attempt identity for output targeting

This would make retries and concurrent builders appear distinct, but would
break deterministic target derivation and idempotent publication. A unique
attempt identifier is retained for execution provenance only; stable request
lineage owns retry equality and candidate derivation.

### Treat same-request byte divergence as semantic equivalence

This would hide a determinism failure behind a stable semantic request. It is
rejected: identical request and candidate identity with different bytes loses
implementation trust and reports `internal-failure`.

### Persist diagnostics-only failure bundles as ordinary artifacts

This would mix invocation-local evidence with deterministic committed outputs
and make retries difficult to compare. It is not selected initially: the
authoritative operation envelope reports failure, and a future persisted
failure-evidence facility must define a separate attempt-evidence identity and
lifecycle.

### Use escaped strings as the semantic-address machine form

Delimited strings are compact and readable, but escaping and delimiter rules
would become part of identity and are easy for independent clients to
implement inconsistently. They are not selected: typed members make structural
comparison and validation explicit, while display labels remain separate.

### Use one generic serialization or digest for every identity domain

A single byte stream would blur authored source, normalized semantics, build
requests, fixture admission, and raw artifacts, and could accidentally include
attempt or host-local data. The selected domain-separated profile keeps those
meanings distinct and excludes execution-local fields from deterministic
identity.

### Use CBOR, signatures, or digest agility initially

Those may be useful for a later interchange or trust boundary, but add
canonicalization, key-management, or compatibility surface before the first
semantic proof. The initial hobby-project boundary uses a narrow project-owned
canonical JSON profile and SHA-256; later additions require explicit evidence
and a new decision.

### Use a bespoke append-only fixture-admission ledger

This would preserve a custom active-pointer protocol but introduces
self-referential manifest/tree binding and more hobby-project machinery than is
needed. It is not selected: a generic fixture payload manifest plus a separate
readiness/decision record supplies the reviewed digest, scoped payload identity,
and Ben approval while ordinary Git history preserves supersession.

## Adversarial Review Response

[The Revision 2 authority, identity, and compatibility review](reviews/DR-0006-rev-02-review-01.md),
[morphology, graph, and graphics-system review](reviews/DR-0006-rev-02-review-02.md),
and the Revision 3 current-revision reviews
([authority](reviews/DR-0006-rev-03-review-01.md),
[morphology](reviews/DR-0006-rev-03-review-02.md)) are preserved as stale
historical evidence. On 2026-08-11 Ben approved the resulting CK-KICK-012
namespace resolution for Revision 4. Its Revision 4 current-revision Double
review is preserved as stale evidence in the [contract pass](reviews/DR-0006-rev-04-review-01.md) and
[graphics-system pass](reviews/DR-0006-rev-04-review-02.md). Both recommend
Accept at High confidence with no blocking finding. The graphics pass records a
nonblocking cross-DR fixture-matrix obligation; exact dependency-revision
meaning remains a nonblocking later obligation. Review Complete records
evidence, not owner acceptance. Those artifacts are stale after the material
Revision 5 change and did not satisfy the then-pending current-revision review. The
Batch 9 candidate-versus-committed identity lifecycle is now recorded at this
identity boundary, with operation/publication mechanics cross-linked to
DR-0013.

The fresh current Batch 9 Double review examined exact target commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`: [review 01](reviews/DR-0006-rev-05-review-01.md)
recommended **Revise** at **High** confidence under the contract/schema,
determinism, and security lens, and [review 02](reviews/DR-0006-rev-05-review-02.md)
recommended **Revise** at **High** confidence under the platform/failure,
reversibility, and publication lens. Consolidated finding **C1 (High)** applies:
stable request, attempt, candidate, and committed identity, retry, and
concurrent publication semantics remain to be discussed. C1 awaits Ben's
discussion and owner disposition. Review completion is evidence only; it is not
a clean review or acceptance. Owner approval remains Pending and Status remains
Proposed. Only Ben may accept or reject this proposal.

The Batch 10 revision was discussion-approved by Ben on 2026-08-12. The
Revision 6 review artifacts above are stale historical evidence after the
material identity and fixture-route resolution in Revision 7. The prior fresh
Batch 10 Double review examined commit `f27008f319cfc460f4a27efe31594e5607e7721e`:
[review 01](reviews/DR-0006-rev-06-review-01.md)
recommended **Revise** at **High** confidence under the contract/schema,
determinism, identity, security, and fixture-admission lens; [review 02](reviews/DR-0006-rev-06-review-02.md)
recommended **Revise** at **High** confidence under the platform/filesystem,
publication, reversibility, numeric-frame, and runtime-portability lens.
The prior consolidated finding **C1 (High)** and the DR-0006 build-proof
consequence of **C2 (High)** are resolved in this Proposed revision: committed
bytes exclude attempt-local data, diagnostics-only failure bundles are not
committed initially, and the generic fixture-manifest payload plus separate
readiness/decision record admits the build/publication fixtures without a
self-referential ledger. The filesystem proof follow-up remains nonblocking
evidence work. Ben's resolution is discussion approval, not acceptance. Review
status is Complete for the new current revision after the Double review below;
Owner approval remains Pending and Status remains Proposed. Only Ben may accept
or reject this proposal.

The fresh current-revision Double review examined exact target commit
`28c83c7a21cf55f23274aeaf5d2ccc0a3e9e3b53`. [Review 01](reviews/DR-0006-rev-07-review-01.md)
used the contract/schema, identity, determinism, security, and fixture-admission
lens and recommended **Revise** at **High** confidence, identifying one scoped
build-proof identity consequence that is principally owned by DR-0013. [Review
02](reviews/DR-0006-rev-07-review-02.md) used the platform, failure,
reversibility, numeric-frame, adapter-portability, and future-runtime lens and
recommended **Accept** at **High** confidence with no DR-0006-specific finding;
its filesystem proof note is nonblocking follow-up evidence. Both were fresh,
independent `gpt-5.6-sol` medium passes. Consolidated **C3 (High)** applies to
the DR-0013 fixture-manifest boundary with this DR-0006 build-proof consequence.
The current review is evidence only; the proposal remains Proposed with Owner
approval Pending and no activation follows.

Ben approved the Batch 11 machine-contract resolutions in discussion on
2026-08-12. This Revision 8 proposal adds the typed semantic-address profile,
canonical JSON normalization, and domain-separated SHA-256 digest domains.
The Revision 7 review artifacts are stale historical evidence. The fresh
current-revision Double review examined exact target commit
`053dba58fd344ed636420e0974cf617862fe265f`: [Review 01](reviews/DR-0006-rev-08-review-01.md)
and [Review 02](reviews/DR-0006-rev-08-review-02.md) were independent fresh
`gpt-5.6-sol` medium passes; both recommend **Revise** at **High** confidence.
Actionable findings remain for Ben's discussion, including cross-record numeric,
diagnostic, and Readiness 3 binding issues. Review status is Complete for
evidence only; Owner approval remains Pending, Status remains Proposed, and no
acceptance or activation follows.

Ben approved all five Batch 13 resolution directions in discussion on
2026-08-13. Revision 9 integrates them as Proposed identity and activation
constraints: canonical-frame comparison is symmetric and exact at inclusive
boundaries, quaternion thresholds and normalization are deterministic and
offline-admitted, claim identity is authored and stable, every unordered
collection has an owner-defined typed key/rule, implementation activation has
a separate scoped content binding, future adapter guarantees distinguish
storage conversion from runtime conformance, and the diagnostics profile is
the sole owner with a known bootstrap. The Revision 8 review artifacts are
stale for this materially revised record; their findings and history remain
preserved. Review status is Complete for the current evidence, Owner approval
remains Pending, and no DR acceptance, schema, fixture, parser/resolver,
implementation, adapter, experiment, or package activation follows.

The fresh current-revision Batch 13 Double review examined exact target commit
`8c38c501eb1262a1b85af0b8605220625601772f`. [Review 01](reviews/DR-0006-rev-09-review-01.md)
and [Review 02](reviews/DR-0006-rev-09-review-02.md) were complete-coverage,
independent fresh `gpt-5.6-sol` medium passes with no edits; both recommend
**Revise** at **High** confidence. Review 01 records unresolved **D1–D3**:
the unproven conservative angular interpretation of `H`, incomplete
mechanically checkable implementation-binding closure, and underspecified
versioned claim-ID components/order/stable property address. Review 02 records
unresolved **P1–P3**: symlink/special-file/ancestor no-follow binding rules,
post-operation `-0` canonicalization, and malformed-versus-unsupported-versus
conversion-failure adapter status mapping. The findings remain cross-linked to
the DR-0011, DR-0012, DR-0013, canonical-data, diagnostics, and
fixture-manifest owners as identified in the artifacts. Review status is
Complete for evidence only; Owner approval remains Pending and Status remains
Proposed. No identity profile, readiness binding, adapter, schema, fixture,
implementation, or package is accepted or activated by this review.

The Batch 13 findings were dispositioned in the prior Revision 10 as follows.
D1 was resolved at this identity boundary by removing the unproven angular
interpretation: `H` is an inclusive canonical-tuple Euclidean threshold, while
any represented-angular guarantee requires successor evidence. D2 and P1 were
resolved by the explicit implementation-closure and root-descriptor,
no-follow, regular-file-only binding profile cross-linked to the fixture
manifest and platform records. D3 was resolved by conceptual `claim-id-1`, its
typed component order, canonical unordered-pair form, stable property address,
and multiplicity rule. P2 was owned by DR-0011's produced-zero `+0` rule and
P3 was provisionally described as owned by the build-operation/platform status
mapping. Revision 11 corrects the comparator details, request-binding
identity references, and numeric wording above; it records P3 as deferred
until adapter activation. The prior reviews remain stale evidence; Review
status is Pending and this Proposed revision activates none of the described
machinery.

The fresh successor-target reviews are [Review 01](reviews/DR-0006-rev-10-review-01.md)
and [Review 02](reviews/DR-0006-rev-10-review-02.md). They are exact-target
evidence for Revision 10 only and are stale for this Revision 12 successor.
Their G1/G2 mechanical findings were fixed in the successor; T1–T3 were
resolved here, while T4/P3 is explicitly deferred until adapter activation and
is not a first Rust slice blocker. At that stage, the Revision 12 current
review was still pending; no acceptance or activation followed.

The final Double-review [Review 01](reviews/DR-0006-rev-11-review-01.md) and
[Review 02](reviews/DR-0006-rev-11-review-02.md) examined exact target commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` and are stale for this successor.
Revision 12 corrects the comparator/rank-table and sqrt wording, removes the
stray numeric `Runtime`, and preserves T4 as a deferred retained-human gate;
the then-pending successor review is recorded below.

The current-revision Double review examined exact target commit
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`: [Review 01](reviews/DR-0006-rev-12-review-01.md)
records governance findings G3/G4 as mechanical cross-summary corrections
handled without material DR revision, and [Review 02](reviews/DR-0006-rev-12-review-02.md)
records no technical findings and recommends **Ready for PR**. These artifacts
are exact-target current evidence until a successor revision. Review status is
Complete for evidence only; Owner approval remains Pending, Status remains
Proposed, and no identity profile, schema, fixture, parser, resolver, adapter,
implementation, or package is accepted or activated.

## Implementation and Proof Obligations

- Define the semantic concepts requiring durable identity in the body and
  resolved-graph specifications.
- Define the structured semantic address, its authored module-instance anchors,
  concept kind, role-local key, source-set collision domain, one-owner namespace
  rule, and import-remap behaviour without deriving identity from incidental
  structure. The remap must cover every semantic address contributed under the
  imported namespace.
- Freeze the versioned typed address profile: `namespace`, ordered `anchors`,
  closed `kind`, and role-local `role`, using restricted lower-case ASCII
  machine identifiers, structural equality, no case folding, delimiter or
  filesystem semantics, and separate Unicode display labels.
- Define their relation to derived artifact/build identity before external
  persistence is promised.
- Define candidate artifact identity as non-authoritative staging identity and
  committed artifact identity as the same identity after successful atomic
  publication; keep per-invocation attempt identity available even when a
  complete build request cannot be established. Define identical-target
  recognition without adopting different or unverifiable occupants. Leave
  operation/publication mechanics to DR-0013
  and exact fields to the canonical build-operation specification.
- Define unique per-execution `attempt_id` separately from deterministic stable
  `build_request_id`; include source/source-set identity, exact references to
  the implementation-content-binding and dependency-closure identities used
  for execution, compiler/toolchain/build implementation, contract/schema/
  profile revisions, configuration, seed, backend/capability/protocol revision,
  and output-affecting target/platform profile in the request identity. Keep
  those as references to separate domains rather than inlining raw file or
  dependency sets, and exclude attempt and fixture-payload identities.
- Keep `attempt_id` only in the returned operation envelope, invocation-owned
  staging metadata, and logs. Exclude it from committed/hashed bytes, target
  derivation, candidate identity, and idempotent comparison. Do not persist a
  diagnostics-only failure bundle as a committed artifact initially; define a
  separate attempt-evidence identity/lifecycle before changing that boundary.
- Define candidate identity from build request, artifact role, and
  artifact-identity-rule revision; preserve it through successful publication.
  Implement the project-owned canonical JSON profile after semantic
  normalization, deterministic ordering and numeric/address rules, explicit
  versioned framing, domain-separated SHA-256, and the excluded execution-local
  fields. Keep raw-byte and semantic digest domains distinct.
- For every semantically unordered collection or projection, require its owner
  to declare a typed total key and uniqueness or multiplicity rule before
  canonicalization. Use structured graph addresses; tagged module declaration
  addresses; tagged owner-kind/address/role plus required frame/context/claim
  identity; fixture ID; normalized safe-relative path with mode/content in the
  entry projection; dependency locator/role plus distinguishing revision; and
  profile-defined diagnostic occurrences. Reject missing keys and duplicate
  keys only for declared uniqueness collections; preserve legitimate repeated
  claims, multisets, and diagnostics by explicit multiplicity/occurrence
  identity. Never use source/traversal/allocation/index order, serialization,
  or raw bytes as fallback keys.
- Define conceptual versioned `claim-id-1` as the structured tuple of
  canonical target, closed claim kind, typed source-document/namespace
  identity, stable authored record address, typed property role, and explicit
  authored claim key or absence. Freeze the wire-independent semantic-address
  comparator: owning structured address order; profile-defined semantic ranks
  for closed claim kind and typed property role; normalized identifier
  Unicode-scalar lexical order with structured prefix-before-extension; and
  absent-before-present claim keys. The activated schema must bijectively map
  wire values to those conceptual types/ranks. Require complete, injective,
  versioned rank tables for the admitted claim-kind and typed-property-role
  closed sets; missing, duplicate, or unknown entries fail activation, and do
  not activate canonical claim ordering, digest, or resolution before the
  tables exist. Use conceptual unordered pair
  `(min_id, max_id)`. Evaluate same-ID/same-value
  occurrences once while retaining all provenance; reject same-ID/different-
  value identity collisions. Evaluate different-ID all-pairs in sorted claim-ID
  order, report the first failing sorted pair, and choose the smallest exact
  tuple only after all pairs pass. Exact wire fields/enums remain schema-gated;
  raw JSON pointers are diagnostic provenance only.
- Bind every Readiness 2/3 implementation activation to the separate,
  domain-separated ordered normalized repository path/mode/raw-content set and
  aggregate SHA-256 described above. Recompute fixture payload, implementation
  binding, dependency closure, and build-request identity post-merge and
  immediately before the trigger; block mismatch and require a successor. The
  implementation binding covers selected gate-affecting source, manifests,
  configuration, scripts/inputs, lockfile, and toolchain declaration.
  Dependency closure covers registry/vendored/path-dependency/proc-macro
  provenance/content. Build-request identity covers selected packages,
  targets, target triple, features, profile, approved environment/tool/config,
  and the exact locked/offline command. Treat reviewed commit provenance as
  non-equality evidence and keep all identities distinct.
- Prove post-collision inspection: identical committed identity, lineage,
  manifest, hashes, and sizes is already-published success; different lineage
  or identity is target conflict; same request/candidate with byte-divergent
  output is internal nondeterministic-output failure. Add first-build, retry,
  concurrent-winner, lineage-change, and byte-divergence fixtures.
- Prove same-target normalization into one canonical local-to-parent frame,
  direct componentwise translation, q/-q-invariant canonical-tuple chord
  comparison, and exact dyadic scalar/half-chord predicates. Admit finite
  binary64 `H` as a post-normalization canonical-tuple Euclidean threshold;
  theta, if retained, is informational/calibration metadata only and supplies
  no represented-angular guarantee. Any future angular guarantee requires a
  new comparison-profile revision and successor evidence. Use fixed
  max-component quaternion normalization with the specified correctly rounded
  binary64 square root, checked drift/near-zero bounds, canonical sign, and no
  runtime transcendental or ambient-mode dependence in the already-normalized
  tuple-distance predicate.
- Admit those build/publication fixtures through the generic fixture-suite
  payload manifest and a separate readiness/decision record naming its digest,
  source commit, exact ordered path/mode/content set, digest profile, and Ben
  approval. The scope includes only the manifest and declared schema, fixtures,
  and snapshots; it excludes readiness/approval/successor records, mutable
  pointers, and Git commit identity. Do not use a self-referential manifest
  digest or custom active-pointer ledger.
- Prove through regeneration fixtures that semantic references survive topology
  and LOD changes while ephemeral indices remain artifact/build-scoped.
- Record exact revisions and semantic mappings for every outcome-affecting
  external authored asset in source/build provenance.
- Define post-R3 adapter profiles with signed-permutation `C`, positive length
  scale `s`, target precision, narrowing/overflow/underflow/subnormal policy,
  and an explicit storage-only or runtime-conformance tier. Use `sC/s` for
  length-bearing values, `C` for directions/normals, `C R C^-1` for rotations,
  and `D H_c D^-1` for rigid transforms. Probe FTZ/DAZ when runtime subnormal
  preservation is promised; unsupported capabilities fail closed, while
  trusted in-domain conversion overflow/disallowed underflow is output-failure.
  Keep the core snapshot binary64 and unchanged.
- Define the exact dependency-revision meaning before any external authored
  dependency is activated; this remains a nonblocking later obligation at this
  boundary.
- Later decide delimiter/serialized syntax, clone/rename/split/merge/
  replacement alias and remap lifecycle rules, hashes/manifests, versioning,
  migration, runtime swaps, and external mapping when their contracts are
  triggered.

## Canonical Design Links

- [Product requirements](../product/requirements.md)
- [Specification boundary](../../spec/README.md)
- [System overview](../architecture/system-overview.md)
- [Component responsibilities](../architecture/component-responsibilities.md)

## Reversibility and Revisit Triggers

Revisit if regeneration, LOD, or artifact inspection cannot preserve required
semantic references, or if experiments show a different identity boundary is
needed for external assets. Exact syntax and storage remain separately
revisitable when their contracts become active.

# DR-0006: Durable semantic and artifact/build identity

ID: DR-0006

Scope: Specification and architecture

Status: Proposed

Revision: 5

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Discussion approval date: 2026-08-12

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
identity lifecycle at the identity boundary. This discussion approval is not
DR acceptance: this revision remains Proposed with
Owner approval Pending until a current-revision review and Ben's owner
disposition are recorded. All earlier revisions and their reviews remain
preserved as stale historical evidence; the Revision 4 current-review
artifacts are stale after this material Revision 5 change, and a fresh current
review is pending.

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
   every semantic address contributed under that imported namespace. Exact
   delimiter, import/remap syntax, and serialization remain deferred.
2. Separate artifact/build identity and provenance distinguish generated outputs,
   including the resolved graph snapshot, mesh, rig, colliders, runtime package,
   and other build products.

At the artifact-identity level, distinguish a staged candidate from a
committed artifact. A staging manifest carries a non-authoritative candidate
artifact identity; it is not a committed artifact and must not be adopted by
inspection as one. Successful atomic publication promotes that same candidate
identity to committed artifact identity; publication does not mint a second
artifact identity. A build/operation identity exists independently, including
for failure, while a committed artifact identity exists only for a successfully
published artifact or bundle. An identical already-published target may be
recognized as the same committed identity by the build operation; a different
or unverifiable target is not adopted. DR-0006 owns this candidate-versus-
committed identity lifecycle and lineage relationship; DR-0013 owns the
operation, staging, collision, and publication boundaries, and a canonical
build-operation specification owns exact field spelling and format.

Every outcome-affecting external authored asset, including an artist mesh, is
an exactly versioned dependency of the authoritative source set. Its
semantic mapping and exact dependency revision belong to source/build
provenance; the mesh itself does not become semantic truth.

Mesh, vertex, face, triangle, LOD, and array indices are ephemeral and must not
be promised stable through topology changes. Semantic addresses must not be
derived from incidental path, ordering, geometry, artifact identity, topology,
or content hash. Clone, rename, split, merge, and replacement require explicit
future alias, remap, and lifecycle rules; those exact rules remain deferred, as
do hashes or manifests, versioning, migration, runtime swap behaviour, and
external mapping rules.

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

## Implementation and Proof Obligations

- Define the semantic concepts requiring durable identity in the body and
  resolved-graph specifications.
- Define the structured semantic address, its authored module-instance anchors,
  concept kind, role-local key, source-set collision domain, one-owner namespace
  rule, and import-remap behaviour without deriving identity from incidental
  structure. The remap must cover every semantic address contributed under the
  imported namespace.
- Define their relation to derived artifact/build identity before external
  persistence is promised.
- Define candidate artifact identity as non-authoritative staging identity and
  committed artifact identity as the same identity after successful atomic
  publication; keep build/operation identity independent and available for
  failures. Define identical-target recognition without adopting different or
  unverifiable occupants. Leave operation/publication mechanics to DR-0013
  and exact fields to the canonical build-operation specification.
- Prove through regeneration fixtures that semantic references survive topology
  and LOD changes while ephemeral indices remain artifact/build-scoped.
- Record exact revisions and semantic mappings for every outcome-affecting
  external authored asset in source/build provenance.
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

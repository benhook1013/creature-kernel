# DR-0006: Durable semantic and artifact/build identity

ID: DR-0006

Scope: Specification and architecture

Status: Proposed

Revision: 3

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

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

Revision 2 recorded Ben's CK-KICK-012 Batch 1 identity selection. On
2026-08-11 Ben approved the seven Batch 1 review resolutions recorded in
Revision 3. This discussion approval is not DR acceptance: this revision
remains Proposed until a current-revision Double review and Ben's owner
disposition are recorded. All earlier revisions and their reviews remain
preserved as stale historical evidence; the Revision 2 reviews are stale for
this revision.

## Decision

Use two identity levels and an explicit semantic-address boundary:

1. Durable semantic identity names parts, regions, joints, attachments,
   capabilities, and related semantic concepts across regeneration. Each
   concept uses a structured semantic address composed of the source namespace,
   authored stable module-instance anchors, semantic concept kind, and a
   role-local key. Module-instance anchors are authored semantic scope, not an
   incidental ownership path or array order. The exact address must be unique
   within a resolved source set; exact collisions are invalid unless an import
   explicitly remaps them. An authoritative semantic source root declares and
   owns its source namespace; imported semantic sources retain their declared
   namespace unless explicitly remapped. Exact delimiter and serialization
   remain deferred.
2. Separate artifact/build identity and provenance distinguish generated outputs,
   including the resolved graph snapshot, mesh, rig, colliders, runtime package,
   and other build products.

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
- Specification must define the relation between semantic concepts and derived
  artifacts, plus lifecycle/remap behaviour, before durable external contracts
  are promised.

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

## Adversarial Review Response

[The Revision 2 authority, identity, and compatibility review](reviews/DR-0006-rev-02-review-01.md)
and [morphology, graph, and graphics-system review](reviews/DR-0006-rev-02-review-02.md)
are preserved as stale historical evidence. On 2026-08-11 Ben approved their
seven resolution outcomes for this Revision 3. The current-revision Double
review is Complete in the [authority, identity, and compatibility pass](reviews/DR-0006-rev-03-review-01.md)
and [morphology, graph, and graphics-system pass](reviews/DR-0006-rev-03-review-02.md).
The authority pass recommends Revise at High confidence because namespace
ownership/remapping remains ambiguous, while recording exact
dependency-revision meaning as a nonblocking later obligation. The morphology
pass recommends Accept at High confidence with no findings. The namespace
finding awaits Ben's disposition. Review Complete records evidence, not a clean
review or acceptance. Only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the semantic concepts requiring durable identity in the body and
  resolved-graph specifications.
- Define the structured semantic address, its authored module-instance anchors,
  concept kind, role-local key, source-set collision domain, and import-remap
  behaviour without deriving identity from incidental structure.
- Define their relation to derived artifact/build identity before external
  persistence is promised.
- Prove through regeneration fixtures that semantic references survive topology
  and LOD changes while ephemeral indices remain artifact/build-scoped.
- Record exact revisions and semantic mappings for every outcome-affecting
  external authored asset in source/build provenance.
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

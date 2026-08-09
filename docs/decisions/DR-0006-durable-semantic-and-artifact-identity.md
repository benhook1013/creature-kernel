# DR-0006: Durable semantic and artifact/build identity

ID: DR-0006

Scope: Specification and architecture

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Pending

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

Revision 2 records Ben's settled CK-KICK-012 Batch 1 identity selection on
2026-08-09. The discussion selection is not DR acceptance: this revision
remains Proposed until a current-revision Double review and Ben's owner
disposition are recorded. Revision 1 and its review remain preserved as stale
historical evidence.

## Decision

Use two identity levels and an explicit semantic-key boundary:

1. Durable semantic identity names parts, regions, joints, attachments,
   capabilities, and related semantic concepts across regeneration. Each
   concept uses an author-declared stable local semantic key under an explicit
   source namespace (conceptually namespace plus local key). Keys are unique
   within their namespace.
2. Separate artifact/build identity and provenance distinguish generated outputs,
   including the resolved graph snapshot, mesh, rig, colliders, runtime package,
   and other build products.

Mesh, vertex, face, triangle, LOD, and array indices are ephemeral and must not
be promised stable through topology changes. Semantic keys must not be derived
from path, ordering, geometry, artifact identity, topology, or content hash.
The namespace and local-key relationship is selected, but its delimiter or
serialized syntax is not. Clone, rename, split, merge, and replacement require
explicit future alias, remap, and lifecycle rules; those exact rules remain
deferred, as do hashes or manifests, versioning, migration, runtime swap
behaviour, and external mapping rules.

## Consequences

- Semantic references can survive regeneration without requiring stable mesh
  topology.
- Author-declared namespace/local-key identity is independent of incidental
  structure and remains inspectable across regeneration.
- Artifact/build inspection can distinguish derived outputs without making them
  competing authored sources.
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

## Adversarial Review Response

[Round 3 Revision 1 adversarial review](reviews/DR-0006-rev-01-review-01.md)
is preserved as stale historical evidence for Revision 1. It recommended
Accept with Medium confidence for that earlier boundary; it does not review
Revision 2. A current-revision Double review is required before acceptance.
The lifecycle, alias/remap, mapping, manifest, migration, runtime-swap, and
external-persistence obligations remain deferred pending owner disposition and
later specification work.

## Implementation and Proof Obligations

- Define the semantic concepts requiring durable identity in the body and
  resolved-graph specifications.
- Define the explicit source namespace and unique author-declared local-key
  relationship without deriving keys from incidental structure.
- Define their relation to derived artifact/build identity before external
  persistence is promised.
- Prove through regeneration fixtures that semantic references survive topology
  and LOD changes while ephemeral indices remain artifact/build-scoped.
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

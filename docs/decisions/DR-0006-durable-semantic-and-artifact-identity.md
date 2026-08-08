# DR-0006: Durable semantic and artifact/build identity

ID: DR-0006

Scope: Specification and architecture

Status: Proposed

Revision: 1

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

## Decision

Use two identity levels:

1. Durable semantic identity names parts, regions, joints, attachments,
   capabilities, and related semantic concepts across regeneration.
2. Separate artifact/build identity and provenance distinguish generated outputs,
   including the resolved graph snapshot, mesh, rig, colliders, runtime package,
   and other build products.

Mesh, vertex, face, triangle, LOD, and array indices are ephemeral and must not
be promised stable through topology changes. Exact ID syntax, namespace rules,
hashes or manifests, versioning, migration, runtime swap behaviour, and external
mapping rules are deferred.

## Consequences

- Semantic references can survive regeneration without requiring stable mesh
  topology.
- Artifact/build inspection can distinguish derived outputs without making them
  competing authored sources.
- Topology-index references are valid only within their ephemeral artifact/build
  context.
- Specification must define the relation between semantic concepts and derived
  artifacts before durable external contracts are promised.

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
recommends Accept with Medium confidence. The response is clean: no blocker and
no revision is required. The lifecycle, namespace, mapping, manifest, migration,
runtime-swap, and external-persistence obligations remain deferred pending owner
disposition and later specification work.

## Implementation and Proof Obligations

- Define the semantic concepts requiring durable identity in the body and
  resolved-graph specifications.
- Define their relation to derived artifact/build identity before external
  persistence is promised.
- Prove through regeneration fixtures that semantic references survive topology
  and LOD changes while ephemeral indices remain artifact/build-scoped.
- Later decide syntax, namespaces, hashes/manifests, versioning, migration,
  runtime swaps, and external mapping when their contracts are triggered.

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

# DR-0002: Authoritative semantic source set and resolved body graph

ID: DR-0002

Scope: Specification and architecture

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-08

Date decided: —

Supersedes: —

Superseded by: —

## Context

The project needs a durable place for authored intent while generating geometry,
rigging, collision, deformation, materials, packaging, and runtime state. An
incidental generated output cannot carry all of the construction intent needed
for regeneration, automation, validation, and interaction across body
variation. A single initial document is useful, but future explicit semantic
override layers may also be authored inputs.

Revision 1 described a single declarative body document. Revision 2 records the
broader source-set boundary and makes the resolved semantic graph a per-build
derived snapshot. Revision 1 remains historical through Git; no duplicate
revision snapshot is maintained here.

## Decision

Durable authored intent lives in an authoritative semantic source set. Initially
the source set may be one human-readable document; future explicit semantic
override layers may also be authored inputs. Compilation resolves that source
set into a per-build semantic body-graph snapshot.

The resolved graph supplies shared semantic lineage for derived mesh, rig,
collider, material, deformation, packaging, runtime-state, and other outputs.
Those outputs are derived and must not silently become competing sources of
truth. External artist meshes may later enter as explicitly linked or mapped
authored inputs.

This record defers physical source formats, override representation,
precedence/conflict rules, runtime mutation/recompilation, and external-mesh
conformance details. Durable semantic identity and separate artifact/build
identity are defined at the boundary in [DR-0006](DR-0006-durable-semantic-and-artifact-identity.md).

## Consequences

- Generation, regeneration, diffing, shared operations, and deterministic
  testing receive authored inputs and a resolved per-build snapshot.
- Semantic lineage remains distinct from generated outputs and can survive mesh
  replacement or remeshing.
- Source-set representation, override policy, and migration policy become
  long-lived contracts, but remain deferred here.
- Edits made directly to derived output cannot silently become authored truth.
- Imported meshes require an explicitly linked or mapped authored-input path.

## Alternatives Considered

### Generated output as source of truth

Works with conventional asset tools but loses authored construction intent and
makes semantic regeneration difficult.

### One fixed document forever

Keeps the initial representation simple, but prevents future explicit semantic
override layers from being authored inputs and would make later source needs an
implicit competing path.

### Fixed template mesh with morph parameters

Provides excellent topology correspondence but conflicts with the initial goal
of generating bodies without a handcrafted base mesh and limits topology change.

### Opaque procedural scene graph

Could generate bodies but would be difficult to diff, version, validate, and
operate through external tools.

### Learned latent representation

May generate varied shapes but is difficult to make deterministic, semantically
precise, editable, and compatible across model versions.

## Adversarial Review Response

[Round 3 Revision 2 adversarial review](reviews/DR-0002-rev-02-review-01.md)
recommends Accept with Medium confidence. The response is clean: no blocker and
no revision is required. The source-format, resolver, fixture, migration,
runtime-mutation, and external-mesh obligations remain deferred pending owner
disposition and later specification work.

## Implementation and Proof Obligations

- Specify the source-set, resolved-graph, and derived-output relationships.
- Define deterministic resolution and diagnostic behaviour.
- Define semantic identity separately from artifact/build identity under DR-0006.
- Build fixtures proving semantic lineage across shape variation and derived
  output changes.
- Later define source formats, overrides, runtime mutation/recompilation,
  external-mesh mapping, versioning, and migration before promising those
  contracts.

## Canonical Design Links

- [Product requirements](../product/requirements.md)
- [System overview](../architecture/system-overview.md)
- [Specification boundary](../../spec/README.md)
- [Durable semantic and artifact identity](DR-0006-durable-semantic-and-artifact-identity.md)

## Reversibility and Revisit Triggers

Changing the source-set and resolved-graph relationship becomes expensive after
documents and tools exist. Revisit if authored inputs cannot express required
morphology, if derived output cannot preserve artist intent, or if a hybrid
asset model proves necessary through experiments. Exact formats, overrides,
runtime mutation, and external-mesh conformance remain separately revisitable.

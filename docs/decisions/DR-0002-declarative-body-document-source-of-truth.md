# DR-0002: Authoritative semantic source set and resolved body graph

ID: DR-0002

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

The project needs a durable place for authored intent while generating geometry,
rigging, collision, deformation, materials, packaging, and runtime state. An
incidental generated output cannot carry all of the construction intent needed
for regeneration, automation, validation, and interaction across body
variation. A single initial document is useful, but future explicit semantic
override layers may also be authored inputs.

Revision 1 described a single declarative body document. Revision 2 recorded the
broader source-set boundary and made the resolved semantic graph a per-build
derived snapshot. Revision 3 records Ben's settled CK-KICK-012 Batch 1 source
and graph boundary on 2026-08-09. The discussion selection is not DR acceptance:
this revision remains Proposed until a current-revision Double review and
Ben's owner disposition are recorded. Earlier revisions and their reviews
remain historical evidence; the Revision 2 review is stale for this revision.

## Decision

Durable authored intent lives in an authoritative semantic source set. Initially
the source set may be one human-readable document; future explicit semantic
override layers may also be authored inputs. The source set alone is authored
authority. A validated, inspectable, per-build semantic body-graph snapshot is
derived from it through resolution.

The snapshot contains source references, durable semantic nodes and relations,
declared local frames and resolved transforms, relevant intent and lineage, and
structured diagnostics. It is reproducible and build-scoped, but is not
authoritative and must not silently become a competing source. Mesh, rig,
collision, material, deformation, packaging, runtime, and other artifacts
remain further derived outputs.

The resolved graph supplies shared semantic lineage for derived mesh, rig,
collider, material, deformation, packaging, runtime-state, and other outputs.
Those outputs are derived and must not silently become competing sources of
truth. External artist meshes may later enter as explicitly linked or mapped
authored inputs.

This record defers physical source formats, schema technology, override
representation and precedence/conflict rules, runtime mutation/recompilation,
and external-mesh conformance details. Durable semantic identity and separate
artifact/build identity are defined at the boundary in
[DR-0006](DR-0006-durable-semantic-and-artifact-identity.md).

## Consequences

- Generation, regeneration, diffing, shared operations, and deterministic
  testing receive authored inputs and a validated, inspectable resolved
  per-build snapshot.
- Semantic lineage remains distinct from generated outputs and can survive mesh
  replacement or remeshing.
- The graph boundary exposes enough semantic structure for inspection and
  diagnostics without selecting a concrete syntax or schema technology.
- Source-set representation, override policy, precedence, and migration policy
  become long-lived contracts, but remain deferred here.
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
is preserved as stale historical evidence for Revision 2. It recommended
Accept with Medium confidence for that earlier boundary; it does not review
Revision 3. The current-revision Double review is complete in the [authority,
identity, and compatibility pass](reviews/DR-0002-rev-03-review-01.md) and the
[morphology, graph, and graphics-system pass](reviews/DR-0002-rev-03-review-02.md).
Both recommend Revise at High confidence. Findings remain unresolved pending
Ben's disposition: define the semantic identity collision domain and reusable
expansion identity, classify external authored dependencies, define the graph
relation/result envelope for framed relations and invalid or unsupported
assemblies, and qualify the broad regeneration-survival guarantee. This review
completion records evidence, not a clean review or acceptance. Only Ben may
accept or reject this proposal.

## Implementation and Proof Obligations

- Specify the source-set, resolved-graph, and derived-output relationships,
  including source references, durable semantic nodes/relations, local frames,
  resolved transforms, intent/lineage, and structured diagnostics.
- Define deterministic resolution and diagnostic behaviour for valid,
  invalid, and unsupported assemblies.
- Define semantic identity separately from artifact/build identity under DR-0006.
- Build fixtures proving semantic lineage across shape variation and derived
  output changes.
- Later define source formats, schema technology, overrides,
  precedence/conflict rules, runtime mutation/recompilation,
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

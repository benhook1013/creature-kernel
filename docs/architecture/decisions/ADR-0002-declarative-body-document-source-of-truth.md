# ADR-0002: Declarative body document as source of truth

ID: ADR-0002

Status: Proposed

Revision: 1

Decision owner: Ben

Review status: Pending

Date proposed: 2026-08-05

Date decided: —

Supersedes: —

Superseded by: —

## Context

The project aims to generate geometry, rigging, collision, deformation, and
semantic regions programmatically. Treating an incidental generated mesh as the
primary asset would discard much of the structure needed for regeneration,
automation, validation, and interaction across body variation.

The alternative source must remain editable by humans and tools and support
stable semantic identity when generated topology changes.

## Decision

Use a declarative semantic body document as the editable source of truth.
Compilation resolves that document into a body graph and derives visible and
simulation representations.

Durable contracts reference semantic parts, regions, attachments, local frames,
and capabilities rather than generated vertex indices. Externally authored
meshes may later attach to or conform with the same semantic model.

The concrete format and schema technology remain separate decisions.

## Consequences

- Generation, regeneration, diffing, CLI automation, and deterministic testing
  receive a stable input.
- Semantic information survives mesh replacement or remeshing.
- The body language and migration policy become major long-lived contracts.
- Some edits made directly to generated output may not round-trip to source.
- Imported meshes require explicit mapping rather than becoming semantic truth
  automatically.

## Alternatives Considered

### Generated mesh as source of truth

Works with conventional tools but loses construction intent and makes semantic
regeneration difficult.

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

Pending review of revision 1.

## Implementation and Proof Obligations

- Specify semantic identity, coordinates, units, capabilities, and references.
- Define deterministic resolution and diagnostic behaviour.
- Build fixtures proving stable semantics across substantial shape variation.
- Define how generated output and external overrides relate to source.
- Define versioning and migration before third-party contract stability is claimed.

## Canonical Design Links

- [Product requirements](../../product/requirements.md)
- [System overview](../system-overview.md)
- [Specification boundary](../../../spec/README.md)

## Reversibility and Revisit Triggers

Changing the source-of-truth model becomes expensive after documents and tools
exist. Revisit if a declarative graph cannot express required morphology, if
generated output cannot preserve artist intent, or if a hybrid asset model proves
necessary through experiments.

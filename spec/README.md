# Normative specifications

Status: Active authority boundary; no formats accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

## Planned specification families

- Creature/body document.
- Semantic body graph.
- Identifiers, namespaces, coordinates, units, and measurements.
- Capabilities, regions, attachments, joints, and material/deformation metadata.
- Runtime avatar package.
- Interaction and quality negotiation.
- Diagnostic and artifact manifests.

## Specification obligations

Every accepted format must define:

- purpose and authority;
- normative vocabulary;
- required and optional fields;
- validation and error behaviour;
- ordering and determinism where relevant;
- versioning, compatibility, and migration;
- unknown-field and extension behaviour;
- security and resource limits for untrusted input;
- representative valid and invalid fixtures;
- a machine-readable schema when practical.

No concrete schema or serialization technology is selected yet.

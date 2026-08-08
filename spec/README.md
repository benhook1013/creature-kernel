# Normative specifications

Status: Active authority boundary; no formats accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

## Planned specification families

- Authoritative semantic source set.
- Resolved semantic graph snapshot.
- Durable semantic identities and separate artifact/build identity and provenance.
- Capabilities, regions, attachments, joints, and material/deformation metadata.
- A planned supported-morphology and validity envelope for the bounded first
  body family, including required modules, optional named-socket attachments,
  deferred families, and invalid/unsupported assemblies.
- A planned fixture-profile contract describing stable profile identity,
  concrete source inputs, discriminating parameters, seed/configuration,
  provenance, shared-generation expectations, validity/diagnostic status, and
  the distinction between fixture evidence and product claims. Exact fixture
  definitions must be frozen before EXP-0001 execution or evidence; selecting
  experiment hypotheses may precede that freeze.
- A planned staged embodiment contract describing Stage 1 source-linked
  semantic joint frames and semantic region intent/lineage, and the later
  ownership of usable skeletons, skin weights, collision proxies, contact, and
  deformation claims.
- Runtime avatar package.
- Interaction and quality negotiation.
- Shared domain-operation and diagnostic contracts (eventually).
- Artifact inspection and manifests.

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

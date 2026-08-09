# Normative specifications

Status: Active authority boundary; no formats accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

## Planned specification families

- Authoritative semantic source set (the sole authored authority; initially
  potentially one human-readable document).
- Resolved semantic graph snapshot: a validated, inspectable, reproducible,
  per-build derived snapshot with source references, durable semantic
  nodes/relations, declared local frames, resolved transforms, relevant
  intent/lineage, and structured diagnostics. It is not authoritative.
- Durable semantic identities through author-declared stable local semantic keys
  under an explicit source namespace, and separate artifact/build identity and
  provenance. Exact key serialization and lifecycle/remap rules remain open.
- Capabilities, regions, attachments, joints, and material/deformation metadata.
- A planned supported-morphology and validity envelope for the bounded first
  digitigrade biped family, including its typed ownership tree, distinct typed
  relation edges for joints, sockets/attachments, capabilities, and regions,
  required modules, optional named-socket attachments, deferred families, and
  invalid/unsupported assemblies. The representation must not permanently
  require every relationship to be a tree, and arbitrary anatomy/user-defined
  graph kinds are unsupported in the first family.
- Declared units and coordinate basis, explicit local frames and resolved
  transforms, and structured diagnostics. Exact coordinate convention, ranges,
  surface primitives, and schema or syntax technology remain deferred.
- A planned fixture-profile contract describing stable profile identity,
  concrete source inputs, discriminating parameters, seed/configuration,
  provenance, shared-generation expectations, validity/diagnostic status, and
  the distinction between fixture evidence and product claims. Exact fixture
  definitions must be frozen if the deferred EXP-0001 protocol is activated
  before its execution or evidence; selecting hypotheses may precede that
  freeze.
- The [first surface experiment design](../docs/research/first-surface-experiment-design.md)
  is parked, non-blocking confirmatory research. It is not a normative schema,
  does not register EXP-0001, and does not provide evidence until its activation
  trigger is met.
- A planned staged embodiment contract describing Stage 1 source-linked
  semantic joint frames and semantic region intent/lineage, and the later
  ownership of usable skeletons, skin weights, collision proxies, contact, and
  deformation claims.
- A deferred sampled-field and semantic-lineage direction may later be informed
  by [DR-0010 Revision 8](../docs/decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md).
  Its detailed confirmatory sampling, convergence, and semantic-field rules
  remain in that parked decision record and are not current specification
  requirements. No storage layout or serialization format is selected.
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

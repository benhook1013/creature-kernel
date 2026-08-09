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
- The [Proposed first surface experiment design](../docs/research/first-surface-experiment-design.md)
  is a neutral research/evidence design for the fixture identities, five
  comparison branches, and common three-grid evidence structure. It is not a
  normative schema, does not register EXP-0001, and does not provide evidence.
- A planned staged embodiment contract describing Stage 1 source-linked
  semantic joint frames and semantic region intent/lineage, and the later
  ownership of usable skeletons, skin weights, collision proxies, contact, and
  deformation claims.
- A planned Proposed Stage 1 sampled-field and semantic-lineage direction,
  informed by [DR-0010 Revision 5](../docs/decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md),
  including common-domain phase/convergence checks and scoped determinism.
  Semantic lineage is directionally defined as a raw non-negative measure over
  durable `(semantic_id, chart_id)` keys: unit leaves, raw composition
  `μ = Σᵢ aᵢ Tᵢ(μᵢ)`, raw duplicate-key coalescence, finite positive total,
  and observation-only normalization. Equivalence is by flattened masses and
  path weights; unweighted unions sum masses and weighted paths preserve
  coefficients. Naive local binary averages are not reassociation-equivalent.
  Post-normalization views include top-k values, residual mass, deterministic
  ties, ambiguity, and parallel categorical/chart-validity fields. Independent
  closed-form oracles cover reassociation and counterexamples, duplicates,
  scaling, order, coefficients, ties, residuals, and incompatible charts. This
  remains a Proposed semantic direction only; no storage layout or
  serialization format is selected.
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

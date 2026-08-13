# Adversarial review: DR-0012 revision 12

Target DR: DR-0012

Target revision: 12

Review status: Complete

Execution state: Complete

Coverage: Complete

Batch context: CK-KICK-012/013 Batch 13 exact-target Double review, technical
pass

Review lens: Source admission/resolution, canonical identity, numeric
comparison, readiness binding, adapter status, and cross-spec consistency

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate read-only pass; no authorship or edits

Date: 2026-08-13

Recommendation: Revise

Confidence: High

Reviewed commit: `763cff22d10f6491a05a28312a25250704543dcf`

Staleness: This artifact is exact-target evidence for Revision 12 only. Any
successor revision present on disk makes this review stale for that successor;
it does not satisfy a successor review or accept any proposal.

This artifact records evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 12 keeps source, resolution, canonical identity, and build identity
boundaries coherent, but the parser/resolver activation path still depends on
cross-record identity closure, unambiguous numeric wording, and explicit
status ownership. The proposal should remain Proposed.

## Blocking Objections

1. **High — T1 (cross-linked to DR-0006/DR-0013):** The readiness
   `build_request_id` does not explicitly contain exact implementation-content-
   binding and dependency-closure identity references. Define those references
   as exact inputs before parser/resolver readiness can be claimed.
2. **High — T2 (cross-linked to DR-0006/DR-0011):** `claim-id-1` is described
   as componentwise lexicographic, but no wire-independent total order is
   defined for every component, including absent versus present optional claim
   keys. Define typed ordering and pair encoding before deterministic conflict
   resolution.
3. **Medium — T3 (cross-linked to DR-0011):** The numeric specification has a
   broken or ambiguous square-root sentence: normalization requires a square
   root while the tuple predicate does not. Clarify which operation performs
   normalization and which predicate is evaluated.
4. **Medium — T4 (cross-linked to DR-0013):** The malformed-profile
   `invalid-source` mapping lacks explicit source ownership. Assign the status
   meaning to its owning operation/diagnostics contract. This retained-human
   choice is deferable and not a first-slice blocker.

## Non-blocking Risks

The source and resolver boundaries, tuple semantics, `+0` handling, and
multiplicity direction were otherwise coherent. Exact field/code/profile
spellings and fixtures remain activation prerequisites.

## Conditions for Acceptance

Cross-bind request identity to implementation/dependency closure, define the
complete claim-ID order, repair the numeric wording, and assign malformed-
profile status ownership. Preserve the Proposed state and do not activate a
parser, resolver, adapter, or readiness gate from this review.

## Review Limitations

No parser, resolver, canonical serializer, readiness preflight, numeric oracle,
adapter, status registry, or fixture corpus was available. This pass does not
choose field spellings, constants, status codes, or implementation tools.

## Documents Consulted

- DR-0012 Revision 12 and linked DR-0006, DR-0011, and DR-0013 proposals
- Body-document, body-graph, canonical-data, diagnostics, fixture-manifest,
  build-operation, and numeric/frame specifications
- Architecture, product, project status, registry, and review artifacts

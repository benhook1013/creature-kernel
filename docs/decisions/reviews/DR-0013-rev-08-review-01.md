# Adversarial review: DR-0013 revision 8

Target DR: DR-0013

Target revision: 8

Review status: Complete

Execution state: Complete

Coverage: Complete

Batch context: CK-KICK-012/013 Batch 12 current-revision Double review

Review lens: Exact decimal/binary64, canonical numeric identity, comparator mathematics, multi-claim determinism, edge cases, cross-spec consistency

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-12

Recommendation: Revise

Confidence: High

Reviewed commit: `730a2f77840cc0caa1f838c30dac4ff20f985e69`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 8 correctly keeps numeric/frame activation before Readiness 3, but the
platform and readiness boundary inherit unresolved comparison symmetry,
arithmetic, and representative-identity risks. These are cross-linked to the
numeric/frame and source/graph owners and prevent a reproducible activation
claim. The proposal remains Proposed.

## Blocking Objections

1. **High — A1 (cross-linked to DR-0011/DR-0012):** `E = B * inverse(A)`
   comparison is asymmetric despite unordered-pair semantics; reverse order can
   change componentwise translation pass/fail. Require a symmetric predicate
   (both orientations or one symmetric common-frame metric) and an order-reversal
   fixture.
2. **High — A2 (cross-linked to DR-0011/DR-0012):** Comparator arithmetic is
   insufficiently bound: an “equivalent monotonic” scalar evaluation can differ
   at an inclusive boundary; norm/normalization scaling is unspecified; binary64
   `asin` algorithm behaviour is not deterministic. Define exact-vs-rounded
   semantics, stable norm/normalization, and deterministic elementary-function
   implementation or binding; add ULP-boundary fixtures.
3. **High — A3 (cross-linked to DR-0011/DR-0012):** The owning specifications
   do not say to select the lexicographically smallest representative even
   though the DR text does; stable claim identity is undefined and could depend
   on source/allocation order. Require “smallest” explicitly and define a
   source-derived, permutation-independent claim ID.

## Non-blocking Risks

4. **Medium — A4 (mechanical consistency):** Product and architecture summaries
   say formulas remain open even though the normative formula shapes are fixed.
   Narrow the open set to constants, ranges, the validation-margin/error
   formula, and deterministic evaluation bindings.

## Conditions for Acceptance

Resolve A1–A3 in the owning contracts and bind their order/boundary fixtures to
the Readiness 3 successor transaction. Apply A4 mechanically. No readiness
gate, implementation package, or adapter is activated by this review.

## Review Limitations

No readiness transaction, resolver, comparison implementation, numeric
experiment, fixture corpus, or adapter was available. This pass does not
select numeric constants, implementation bindings, or canonical identity
encodings.

## Documents Consulted

- DR-0013 Revision 8 and linked current decision records
- Numeric/frame, body-document, body-graph, canonical-data, fixture-manifest, and build-operation proposals
- Current architecture, product summaries, project status, registry, and Batch 11 review artifacts

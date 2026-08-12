# Adversarial review: DR-0012 revision 10

Target DR: DR-0012

Target revision: 10

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

Revision 10 gives source admission and resolution a more precise numeric
direction, but the source-to-graph contract still inherits unresolved
order-sensitivity and identity gaps from the numeric/frame profile. These gaps
can change conflict outcomes or snapshots without changing the authored claim
set. The proposal remains Proposed and requires revision before acceptance or
Readiness 3 activation.

## Blocking Objections

1. **High — A1 (cross-linked to DR-0011):** `E = B * inverse(A)` comparison is
   asymmetric despite unordered-pair semantics; reverse order can change
   componentwise translation pass/fail. Require a symmetric predicate (both
   orientations or one symmetric common-frame metric) and an order-reversal
   fixture.
2. **High — A2 (cross-linked to DR-0011):** Comparator arithmetic is
   insufficiently bound: an “equivalent monotonic” scalar evaluation can differ
   at an inclusive boundary; norm/normalization scaling is unspecified; binary64
   `asin` algorithm behaviour is not deterministic. Define exact-vs-rounded
   semantics, stable norm/normalization, and deterministic elementary-function
   implementation or binding; add ULP-boundary fixtures.
3. **High — A3:** The owning specifications do not say to select the
   lexicographically smallest representative even though the DR text does;
   stable claim identity is undefined and could depend on source/allocation
   order. Require “smallest” explicitly and define a source-derived,
   permutation-independent claim ID.

## Non-blocking Risks

4. **Medium — A4 (mechanical consistency):** Product and architecture summaries
   say formulas remain open even though the normative formula shapes are fixed.
   Narrow the open set to constants, ranges, the validation-margin/error
   formula, and deterministic evaluation bindings. This does not resolve the
   comparison or canonicalization findings.

## Conditions for Acceptance

Resolve A1–A3 in the owning numeric/frame and graph contracts, provide
permutation/order-reversal and ULP-boundary fixtures, and apply A4 mechanically.
Retain C1/C3/C4 and the separate diagnostic bootstrap obligation; no parser,
resolver, or readiness gate activates from this review.

## Review Limitations

No parser, resolver, claim evaluator, canonical serializer, numeric experiment,
or fixture corpus was available. This pass does not select comparison
constants, elementary-function bindings, or claim-ID encoding.

## Documents Consulted

- DR-0012 Revision 10 and linked current decision records
- Numeric/frame, body-document, body-graph, canonical-data, and fixture-manifest proposals
- Current architecture, product summaries, project status, registry, and Batch 11 review artifacts

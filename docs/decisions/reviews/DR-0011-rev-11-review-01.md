# Adversarial review: DR-0011 revision 11

Target DR: DR-0011

Target revision: 11

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

Revision 11 usefully fixes the intended decimal-admission and typed-comparison
shapes, but the current normative text does not yet make unordered comparison,
boundary arithmetic, or representative identity permutation-independent and
reproducible. The proposal remains Proposed and requires revision before
acceptance or Readiness 3 activation.

## Blocking Objections

1. **High — A1:** `E = B * inverse(A)` comparison is asymmetric despite
   unordered-pair semantics; reverse order can change componentwise translation
   pass/fail. Require a symmetric predicate (both orientations or one symmetric
   common-frame metric) and an order-reversal fixture.
2. **High — A2:** Comparator arithmetic is insufficiently bound: an
   “equivalent monotonic” scalar evaluation can differ at an inclusive
   boundary; norm/normalization scaling is unspecified; binary64 `asin`
   algorithm behaviour is not deterministic. Define exact-vs-rounded
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
   formula, and deterministic evaluation bindings. This is a stale-summary
   correction, not a substantive resolution of A1–A3.

## Conditions for Acceptance

Resolve A1–A3 with symmetric comparison mathematics, fully bound arithmetic and
elementary functions, source-derived claim identity, and order/boundary
fixtures. Apply A4 mechanically while preserving the Proposed status and the
remaining C1/C3/C4 findings.

## Review Limitations

No executable resolver, comparison implementation, numeric experiment, frozen
fixture corpus, or adapter conformance suite was available. This pass does not
select tolerance constants, an elementary-function library, or a claim-ID
encoding.

## Documents Consulted

- DR-0011 Revision 11 and linked current decision records
- Numeric/frame, body-document, body-graph, canonical-data, and fixture-manifest proposals
- Current architecture, product summaries, project status, registry, and Batch 11 review artifacts

# Adversarial review: DR-0012 revision 8

Target DR: DR-0012

Target revision: 8

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012/013 Batch 10 current-revision Double review

Review lens: Platform, failure, reversibility, numeric-frame, adapter portability, and future runtime

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-12

Recommendation: Revise

Confidence: High

Reviewed commit: `28c83c7a21cf55f23274aeaf5d2ccc0a3e9e3b53`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 8 establishes the intended staged encoding boundary, but its R2/R3
wording can still make the initial transform carrier appear disposable. A
portable implementation needs a structural carrier that is fixed before the
later numeric semantics become exact.

## Blocking Objections

1. **High — C1:** State that Readiness 2 freezes the translation-plus-`xyzw`
   quaternion carrier, while Readiness 3 owns canonical basis, validity,
   normalization/sign, ranges, conditioning, composition, and comparison
   semantics. Readiness 3 must not reselect the structural carrier or rotation
   representation; adapters may derive downstream forms.

## Non-blocking Risks

Exact schema fields, numeric values, compatibility rules, canonical bytes, and
fixture evidence remain open and should not be inferred from this review.

## Conditions for Acceptance

Resolve the R2/R3 wording boundary across DR-0011, DR-0012, and DR-0013, then
provide transition fixtures and numeric/frame evidence before owner acceptance.

## Review Limitations

No implementation, filesystem or portability probe, schema fixture corpus,
snapshot comparator, or runtime evidence was available.

## Documents Consulted

- DR-0012 Revision 8 and linked current decision records
- Body-document, body-graph, build-operation, and fixture-manifest proposals
- Current architecture, project status, readiness, and prior review evidence

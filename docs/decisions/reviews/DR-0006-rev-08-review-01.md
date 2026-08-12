# Adversarial review: DR-0006 revision 8

Target DR: DR-0006

Target revision: 8

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012/013 Batch 11 current-revision Double review

Review lens: Semantic identity, canonicalization/digest, schema/fixture admission, diagnostics compatibility, path security, interoperability, migration/reversibility

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-12

Recommendation: Revise

Confidence: High

Reviewed commit: `053dba58fd344ed636420e0974cf617862fe265f`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 8 establishes the typed semantic-address and project-owned canonical
JSON/digest direction, but its activation boundary remains under-specified for
unordered collections, numeric admission, and reviewed implementation binding.
Diagnostic vocabulary and bootstrap compatibility also require cross-record
resolution before identity or fixture admission can activate.

## Blocking Objections

1. **High — C1:** Canonical JSON sorts unordered collections only by semantic
   address, but module declarations, owner-role records, manifest/build
   collections, and other projections may lack one of the seven semantic-address
   kinds. Define a total canonical key, including duplicate/tie handling, for
   every unordered collection/projection before `ck-json-1` activation.
2. **High — C2 (cross-linked to DR-0011/DR-0012):** Decimal-to-binary64
   admission is ambiguous for values such as `0.1`, midpoint cases, excessive
   precision, subnormal/underflow, and overflow. Select exact conversion,
   rounding, and rejection behaviour with boundary fixtures.
3. **High — C3 (cross-linked to DR-0013):** The R2/R3 payload binding excludes
   implementation bytes and records the commit only as mutable provenance. A
   merge or rebase could therefore activate unreviewed parser/resolver code.
   Preserve the approved fixture payload scope, but add a separately verified
   immutable parser/resolver implementation path/mode/content binding or exact
   tree identity, checked after merge before the ledger trigger.
4. **High — C4 (cross-linked to DR-0012):** Canonical and DR-0012 diagnostic
   domain vocabularies conflict, and an unknown required registry/profile cannot
   itself be reported with a contract-valid primary without a bootstrap profile
   or reserved-envelope diagnostic. Reconcile one domain mapping and define
   bootstrap negotiation diagnostics.

## Non-blocking Risks

Exact canonical field spelling, framing, digest constants, and path mappings
remain activation prerequisites. The implementation-binding and diagnostic
issues above are cross-record concerns and are not resolved by this review.

## Conditions for Acceptance

Define total canonical ordering and ties, exact numeric admission, immutable
implementation binding for R2/R3, and compatible diagnostic/bootstrap profiles;
then provide the corresponding boundary fixtures and migration evidence.

## Review Limitations

No canonical serializer, parser/resolver implementation, fixture corpus,
ledger trigger, path-security harness, interoperability adapter, or migration
benchmark was available.

## Documents Consulted

- DR-0006 Revision 8 and linked current decision records
- Canonical-data, semantic-address, numeric/frame, diagnostics, body-document,
  body-graph, build-operation, and fixture-manifest proposals
- Current architecture, project status, registry, and prior review evidence

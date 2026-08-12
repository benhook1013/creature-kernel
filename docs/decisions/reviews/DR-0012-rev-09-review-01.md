# Adversarial review: DR-0012 revision 9

Target DR: DR-0012

Target revision: 9

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

Revision 9 defines a strict source envelope, typed collections, and a versioned
diagnostic direction. The source admission boundary still needs total
canonicalization, exact numeric conversion, implementation binding for later
readiness, and a bootstrap-compatible diagnostic vocabulary.

## Blocking Objections

1. **High — C1:** Canonical JSON sorting by semantic address is incomplete for
   module declarations, owner-role records, and manifest/build collections that
   may lack one of the seven address kinds. Define a total canonical key and
   duplicate/tie handling for every unordered collection/projection before
   `ck-json-1` activation.
2. **High — C2:** Decimal-to-binary64 admission is ambiguous (`0.1`, midpoint,
   excessive precision, subnormal/underflow, and overflow). Select exact
   conversion/rounding and rejection behaviour with boundary fixtures.
3. **High — C3 (cross-linked to DR-0013):** R2/R3 payload binding excludes
   implementation bytes and mutable commit provenance is insufficient against
   merge/rebase activation of unreviewed parser/resolver code. Add a separately
   verified immutable implementation path/mode/content binding or exact tree
   identity, checked after merge before the ledger trigger.
4. **High — C4:** Canonical and DR-0012 diagnostic domains conflict, and unknown
   required registry/profile revisions need a bootstrap profile or reserved-
   envelope diagnostic so the primary remains contract-valid. Reconcile the
   domain mapping and bootstrap negotiation diagnostics.

## Non-blocking Risks

Exact schema fields, diagnostic codes, profile identifiers, canonical bytes, and
fixture evidence remain deferred; this review does not select them.

## Conditions for Acceptance

Resolve total collection ordering, exact numeric admission, immutable readiness
implementation binding, and bootstrap-compatible diagnostics, then provide
strict-admission boundary fixtures and compatibility evidence.

## Review Limitations

No parser, schema, canonical serializer, diagnostic registry, readiness
preflight, fixture corpus, or migration/compatibility harness was available.

## Documents Consulted

- DR-0012 Revision 9 and linked current decision records
- Body-document, body-graph, build-operation, fixture-manifest, canonical-data,
  numeric/frame, and diagnostics proposals
- Current architecture, project status, registry, and prior review evidence

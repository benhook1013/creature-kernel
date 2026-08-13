# Adversarial review: DR-0013 revision 7

Target DR: DR-0013

Target revision: 7

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

Revision 7 makes Readiness 3 a distinct successor transaction and links the
machine-contract profiles, but the admission route still needs total collection
identity, exact numeric and diagnostic bootstrap rules, and immutable binding of
the implementation being activated.

## Blocking Objections

1. **High — C1:** Canonical JSON sorting by semantic address is incomplete for
   module declarations, owner-role records, and manifest/build collections that
   may lack one of the seven address kinds. Define a total canonical key and
   duplicate/tie handling for every unordered collection/projection before
   `ck-json-1` activation.
2. **High — C2 (cross-linked to DR-0011/DR-0012):** Decimal-to-binary64
   admission is ambiguous (`0.1`, midpoint, excessive precision,
   subnormal/underflow, and overflow). Select exact conversion/rounding and
   rejection behaviour with boundary fixtures.
3. **High — C3:** R2/R3 payload binding excludes implementation bytes and mutable
   commit provenance cannot prevent merge/rebase activation of unreviewed
   parser/resolver code. Add separately verified immutable implementation
   path/mode/content binding or exact tree identity, checked after merge before
   the ledger trigger.
4. **High — C4 (cross-linked to DR-0012):** Canonical and DR-0012 diagnostic
   vocabularies conflict, and unknown required registry/profile revisions need a
   bootstrap profile or reserved-envelope diagnostic. Reconcile one domain
   mapping and bootstrap negotiation diagnostics.

## Non-blocking Risks

The WSL filesystem proof remains a separate activation obligation. Exact
readiness field spelling, digest framing, and implementation binding profile are
not selected by this review.

## Conditions for Acceptance

Resolve C1–C4 across the readiness, numeric, canonical-data, and diagnostics
owners and provide post-merge binding, bootstrap, and boundary-fixture evidence.

## Review Limitations

No readiness transaction, parser/resolver tree binding, canonical serializer,
fixture corpus, diagnostics negotiation, or path-security harness was available.

## Documents Consulted

- DR-0013 Revision 7 and linked current decision records
- Build-operation, fixture-manifest, body-document, canonical-data,
  numeric/frame, diagnostics, and semantic-address proposals
- Current architecture, project status, registry, and prior review evidence

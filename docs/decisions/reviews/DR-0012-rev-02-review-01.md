# Adversarial review: DR-0012 revision 2

Target DR: DR-0012

Target revision: 2

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 5 current-revision double review

Review lens: Contract, schema, and hostile-input/security boundaries

Reviewer: Fresh gpt-5.6-sol contract/schema/security reviewer

Reasoning effort: Medium

Independence: Fresh separate agent; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: a282dbabffd83afa4e62577086934d00f98e12c7

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 2 closes bootstrap, hostile-input boundaries conceptually,
containment/reachability, Attachment composition/validity, canonical
Joint/Socket records, and secondary architecture-mismatch concerns under this
lens. The operation outcome algebra remains partial and is a high-confidence
blocker for this DR because its encoding/resolution phases can retain multiple
fatal findings without a total status and primary-diagnostic rule.

## Prior-blocker closure

Outcome algebra remains partial and blocking. Bootstrap, hostile-input
handling, containment/reachability, Attachment composition/validity,
canonical Joint/Socket records, and the secondary architecture mismatch are
closed under this lens.

## Blocking Objections

1. **High — Status algebra and the primary-diagnostic rule are non-total for
   multiple fatal findings in one phase.**

   **Failure scenario:** Phase 5 can discover both a disconnected Part
   (`invalid-source`) and an unsupported relation/assembly (`unsupported`).
   The earliest fatal phase does not choose the status. The primary diagnostic
   is only said to be deterministic, not tied to the first status-establishing
   diagnostic under normative order. The same input can therefore produce
   different authoritative envelopes across implementations.

   **Recommended resolution:** After internal/resource overrides, define
   ordered fatal subphases or normative within-phase status precedence. Select
   the primary explicitly as the first retained status-establishing diagnostic
   under the normative key, including reserved-primary behavior after
   truncation. Apply the resulting rule consistently to DR-0002 and DR-0008.

## Non-blocking Risks

- Normalize at-most/exactly-one Attachment wording.
- Separate processing completeness from diagnostic completeness.
- Define later exact ordering, multi-address behavior, sentinels, and codes.
- Define cancellation/stalled acquisition before network activation.
- Obtain parser/schema security and fuzz evidence.
- Pin dependency revision and integrity semantics.
- Define provenance-path determinism.
- Bound optional extension payloads.
- Produce fixture and resource-limit evidence.

Suggested evidence includes a JSON/schema specialist, fuzz/property tests, a
differential fixture oracle, and instrumented pre-allocation limits.

## Conditions for Acceptance

Resolve the shared status and primary-diagnostic algebra, preserve the closed
Batch 5 resolutions, and retain the later implementation/evidence obligations.
Ben’s owner disposition and current-revision review requirements remain
governed by the repository process.

## Review Limitations

Fresh, conceptual, read-only review of the exact commit. No schemas, parser or
resolver code, fixtures, fuzz/property tests, benchmarks, or specialist
security evidence were available.

## Documents Consulted

- [DR-0012 Revision 2](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [DR-0002 Revision 7](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008 Revision 7](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- Decision-record review process and CK-KICK-012 Batch 5 resolutions

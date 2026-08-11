# Adversarial review: DR-0011 revision 5

Target DR: DR-0011

Target revision: 5

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 7 current-revision double review

Review lens: Platform, build, geometry, reversibility, and host-integration boundaries

Reviewer: Fresh gpt-5.6-sol platform/build/geometry/reversibility/host-integration reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 88004388f9537a37617ae248bdaad4625e6f3f03

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 5 usefully separates semantic concepts, authored measurements, and
frame roles. A module-root observability gap remains blocking, while exact
numeric and fixture contracts remain a non-blocking but necessary activation
obligation for a deterministic resolver.

## Blocking Objections

1. **High — A present attached module root is not independently observable when
   its required Attachment is missing.**

   **Failure scenario:** `Module` is not a graph concept, yet Attachment
   cardinality is used to infer module presence. A normalized semantic consumer
   cannot distinguish a present root missing its required relation from an absent
   optional module or an undeclared root, so diagnostics and provenance are not
   backend-neutral.

   **Recommended resolution:** Add a normalized module-root declaration carrying
   source provenance and explicit presence/optionality, and validate Attachment
   cardinality against that declaration.

## Non-blocking Risks

1. **Medium — Exact schema and fixtures do not yet activate a deterministic
   frame resolver.**

   The later contract still needs canonical axes and units, rotation
   representation, scale/shear policy, numeric representation, and tolerances.
   It should distinguish parser/bootstrap acceptance from semantic normalization
   and resolved-snapshot publication; otherwise an exact parser schema and an
   admitted fixture set can be mistaken for a complete frame contract. This is
   an activation/evidence obligation, not a demand to freeze all representation
   detail in this decision record.

No additional independent DR-0011 issue was identified from this platform and
geometry lens beyond the linked status, Socket-role, transform-domain, and
DR-0013 activation/publication concerns.

## Conditions for Acceptance

Define the normalized module-root declaration. Before resolver activation,
separately gate parser/bootstrap fixtures and semantic normalization/snapshot
fixtures, and record canonical numeric/frame rules and tolerances sufficient to
make conversion deterministic.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
schema, resolver, geometry backend, host integration, fixture corpus,
benchmarks, or portability evidence was available.

## Documents Consulted

- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [DR-0013](../DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
- Decision-record review process and CK-KICK-012 Batch 7 review brief

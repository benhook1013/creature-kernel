# Adversarial review: DR-0008 revision 9

Target DR: DR-0008

Target revision: 9

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

Revision 9 states the bounded family and required Attachment relation clearly.
One observability gap remains material: a present attached module root is not an
independent graph concept when its required Attachment is missing.

## Blocking Objections

1. **High — A present attached module root is not independently observable when
   its required Attachment is missing.**

   **Failure scenario:** The grammar treats `Module` as non-graph structure and
   expresses presence through an Attachment. A resolver or geometry host cannot
   therefore distinguish a declared present root whose required relation is
   missing from an absent optional module or an undeclared root using only the
   normalized graph. Diagnostics and fixture expectations can diverge.

   **Recommended resolution:** Define a backend-neutral normalized module-root
   declaration with source provenance and explicit presence/optionality, then
   validate the exact zero/one/multiple-Attachment rule against it.

## Non-blocking Risks

No additional DR-0008-specific issue was identified from this lens beyond the
linked status, Socket-role, transform-domain, and implementation activation
obligations. Those remain cross-record concerns; the recommendation faithfully
remains Revise because the module-root observability gap affects this grammar.

## Conditions for Acceptance

Add the normalized module-root declaration and fixtures distinguishing absent,
present-without-Attachment, present-with-one-Attachment, and present-with-
multiple-Attachments. Keep this distinction independent of any selected
geometry backend or host engine.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
schema, resolver, geometry backend, host integration, fixture corpus,
benchmarks, or portability evidence was available.

## Documents Consulted

- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- Decision-record review process and CK-KICK-012 Batch 7 review brief

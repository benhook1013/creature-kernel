# Adversarial review: DR-0011 revision 4

Target DR: DR-0011

Target revision: 4

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 6 current-revision double review

Review lens: Semantic graph, graphics/geometry, build, portability, and runtime boundaries

Reviewer: Fresh gpt-5.6-sol semantic-graph/graphics/geometry/build/portability/runtime reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: c64b1b98948304d631eecea6a354c9e42c89c510

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 4 gives the semantic vocabulary a clear Attachment and frame
direction, but the geometry-facing meaning is still under-specified. A unique
typed transform-space contract and a closed mating-Socket reuse policy are
needed before the vocabulary can guarantee consistent graph placement.

## Blocking Objections

1. **High — Attachment placement lacks a unique typed transform-space
   contract.**

   **Failure scenario:** The prose combines host Part/frame, host Socket,
   optional offset, containment, and inverse mating Socket frame without
   uniquely defining from-space/to-space types, offset basis, or composition
   order. Different semantic consumers can derive different child-local
   placements while accepting the same record.

   **Recommended resolution:** Add backend-neutral typed transform spaces,
   explicit offset basis and order, and a conceptual host-local equation.
   Matrix and serialization convention may remain deferred.

2. **High — Mating Socket capacity and reuse are not fully classified.**

   **Failure scenario:** Host Socket capacity one leaves mating-Socket reuse,
   dependency/cycle semantics, and provenance open. Shared references can
   alter graph topology or placement in ways not represented by the vocabulary.

   **Recommended resolution:** Prohibit mating-Socket reuse initially with a
   capacity-one rule and distinct diagnostic, or define the complete allowed
   reuse semantics.

## Non-blocking Risks

None identified beyond deferred representation conventions and implementation
evidence.

## Conditions for Acceptance

Normatively define transform spaces, offset basis/order, and mating-Socket
reuse. Add semantic fixtures for descendant-owned Sockets, placement, and
repeated mating references. This evidence does not accept DR-0011.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
matrices, geometry fixtures, runtime integration, benchmarks, or specialist
portability evidence were available.

## Documents Consulted

- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- Decision-record review process and CK-KICK-012 Batch 6 review brief

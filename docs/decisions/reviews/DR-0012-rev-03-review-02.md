# Adversarial review: DR-0012 revision 3

Target DR: DR-0012

Target revision: 3

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 6 current-revision double review

Review lens: Semantic graph, graphics/geometry, build, portability, and runtime boundaries

Reviewer: Fresh gpt-5.6-sol semantic-graph/graphics/geometry/build/portability/runtime reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: Medium

Reviewed commit: c64b1b98948304d631eecea6a354c9e42c89c510

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 3 gives document resolution a useful phase and resource boundary and
links Attachment semantics to the other records. Two geometry/graph contracts
remain open: Attachment placement has no unique typed transform-space meaning,
and mating Socket capacity/reuse is not classified. These are high-value
semantic risks, though confidence in the overall assessment is medium because
no implementation or fixtures were available.

## Blocking Objections

1. **High — Attachment placement lacks a unique typed transform-space
   contract.**

   **Failure scenario:** Host/mating frames, containment, and optional offset
   are named without unique from-space/to-space meanings, offset basis, or
   before/after order. Independent resolvers can emit different attached
   module placements from the same document.

   **Recommended resolution:** Define backend-neutral transform-space types,
   offset basis, composition order, and a conceptual host-local equation.
   Matrix/serialization conventions may remain deferred.

2. **High — Mating Socket capacity and reuse are not fully classified.**

   **Failure scenario:** Host capacity one does not define whether mating
   Sockets may be reused, or how shared use affects dependency, cycle, and
   provenance behavior. Resolution and geometry consumers may disagree.

   **Recommended resolution:** Initially prohibit mating-Socket reuse with
   capacity one and a distinct diagnostic, or specify complete allowed-reuse
   semantics.

## Non-blocking Risks

None identified beyond deferred representation conventions and later runtime
and geometry evidence.

## Conditions for Acceptance

Close the transform-space and mating-Socket reuse contracts, then add document
fixtures that exercise offset order, descendant-owned Sockets, and repeated
mating references. This review does not accept the decision record.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
schemas, matrices, geometry fixtures, runtime integration, benchmarks, or
specialist portability evidence were available.

## Documents Consulted

- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- Decision-record review process and CK-KICK-012 Batch 6 review brief

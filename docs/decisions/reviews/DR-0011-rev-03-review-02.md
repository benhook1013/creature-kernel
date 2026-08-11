# Adversarial review: DR-0011 revision 3

Target DR: DR-0011

Target revision: 3

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 5 current-revision double review

Review lens: Semantic graph, technical art, graphics, and runtime handoff

Reviewer: Fresh gpt-5.6-sol semantic-graph/technical-art/graphics/runtime reviewer

Reasoning effort: Medium

Independence: Fresh separate agent; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: a282dbabffd83afa4e62577086934d00f98e12c7

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 3 closes canonical frame records and status/bootstrap/resource
concerns conceptually under this lens, but its canonical Joint/Socket and
Attachment handoff still needs explicit placement composition and cardinality
rules. These are graph/runtime blockers in the body graph that DR-0011
participates in, while the current rules do not select a rig, engine, or
solver.

## Prior-blocker closure

Explicit containment is partial because placement ownership is not fully
closed. Attachment composition is partial because descendant-owned mating
Sockets are not reduced to one canonical placement. Canonical frames, status,
bootstrap, and hostile-resource handling are closed conceptually under this
lens; the first two partial items remain blockers below.

## Blocking Objections

1. **High — Attachment placement does not close into the single
   containment-transform topology when the mating Socket is owned by a
   descendant in the attached module-root subtree.**

   **Failure scenario:** The contract does not normatively compose the
   module-root containment path to the mating-Socket owner, nor require the
   resulting placement to be the attached root’s sole child-local containment
   placement. Descendants and authored child-local placements can therefore
   produce competing runtime transforms.

   **Recommended resolution:** Compose the containment path and interface frame
   to derive the canonical module-root-to-mating-interface transform. Make the
   Attachment result the root’s sole resolved child-local containment
   placement; descendants inherit only through containment. Check competing
   authored child-local placement against that value and retain provenance.
   Apply the corresponding body-graph wording in DR-0002 and DR-0008.

2. **Medium — Attachment cardinality and Socket reuse are inconsistent or
   undefined.**

   **Failure scenario:** The canonical graph and DR-0012 say `exactly one`,
   while DR-0002, DR-0008, and related wording say `at most one`. A present
   root with zero incoming Attachments may diverge. Host Socket capacity,
   duplicate endpoint-pair identity, host reuse, multiple incoming Attachments,
   and zero incoming Attachments are not defined.

   **Recommended resolution:** Define a present attached optional root as
   having exactly one incoming active Attachment and an absent module as having
   none. Choose initial host-Socket capacity/multiplicity, then separately
   define repeated endpoint pairs, host reuse, multiple incoming Attachments,
   and zero incoming Attachments across the linked product/body-graph contract.

## Non-blocking Risks

- Add relation-family cycle fixtures.
- Add semantic-equivalence and provenance cases.
- Measure transform-caching performance when a resolver exists.
- Require new contracts for future morphologies.
- The current rules do not select a rig, engine, or solver.

Minimum fixtures should cover root and descendant mating Sockets; nonidentity
transforms, offsets, and bases; authored agreement/disagreement and tolerance;
zero, two, repeated, and host-reuse cases; detached, mismatch, and cycle
cases; movable tail versus static ear; canonical-frame provenance; and reversed
or non-immediate Joints. Technical-artist, rigging, and runtime
transform-consumer evidence is recommended.

## Conditions for Acceptance

Define descendant Socket placement composition, sole attached-root placement,
authored-placement agreement, and Attachment/Socket cardinality and reuse in
the canonical linked body-graph contracts. Add the minimum fixtures and
specialist evidence when implementation begins. Ben’s owner disposition and
current-revision review requirements remain governed by the repository process.

## Review Limitations

Fresh, conceptual, read-only review of the exact commit. No resolver, schema,
fixtures, captures, benchmarks, or specialist technical-art, rigging, or
runtime evidence were available.

## Documents Consulted

- [DR-0011 Revision 3](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0002 Revision 7](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008 Revision 7](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0012 Revision 2](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 5 resolutions

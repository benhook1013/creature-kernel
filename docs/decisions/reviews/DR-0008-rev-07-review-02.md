# Adversarial review: DR-0008 revision 7

Target DR: DR-0008

Target revision: 7

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

Revision 7 closes canonical frames, status, bootstrap, and hostile-resource
concerns conceptually under this lens. The optional-module Attachment still
does not reduce a descendant-owned mating Socket to one canonical containment
placement, and Attachment cardinality/Socket reuse is inconsistent or absent.
These findings affect the morphology envelope, its body graph, and linked
DR-0002/DR-0011 contracts.

## Prior-blocker closure

Explicit containment is partial because placement ownership is not fully
closed. Attachment composition is partial because descendant-owned mating
Sockets are not reduced to one canonical placement. Canonical frames, status,
bootstrap, and hostile-resource handling are closed conceptually under this
lens.

## Blocking Objections

1. **High — Attachment placement does not close into the single
   containment-transform topology when the mating Socket is owned by a
   descendant in the attached module-root subtree.**

   **Failure scenario:** There is no normative composition of the module-root
   containment path to the mating-Socket owner, nor a rule that the result is
   the attached root’s sole child-local containment placement. Descendants can
   consequently inherit different placements or retain competing authored
   placements.

   **Recommended resolution:** Compose the containment path and interface frame
   to derive the canonical module-root-to-mating-interface transform. Make the
   Attachment result the root’s sole resolved child-local containment
   placement; descendants inherit only through containment. Compare competing
   authored child-local placement against that value and retain provenance.
   Apply the same rule to the linked DR-0002 and DR-0011 body-graph text.

2. **Medium — Attachment cardinality and Socket reuse are inconsistent or
   undefined.**

   **Failure scenario:** The canonical graph and DR-0012 say `exactly one`,
   while DR-0002 and DR-0008 say `at most one`. A present root with zero
   incoming Attachments may diverge, and host Socket capacity, duplicate
   endpoint-pair identity, host reuse, multiple incoming Attachments, and zero
   incoming Attachments are undefined.

   **Recommended resolution:** Define a present attached optional root as
   having exactly one incoming active Attachment and an absent module as having
   none. Choose initial host-Socket capacity/multiplicity, then separately
   define repeated endpoint pairs, host reuse, multiple incoming Attachments,
   and zero incoming Attachments across the linked contracts and product/body
   graph.

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
the canonical linked contracts. Add the minimum fixtures and specialist
evidence when implementation begins. Ben’s owner disposition and current-
revision review requirements remain governed by the repository process.

## Review Limitations

Fresh, conceptual, read-only review of the exact commit. No resolver, schema,
fixtures, captures, benchmarks, or specialist technical-art, rigging, or
runtime evidence were available.

## Documents Consulted

- [DR-0008 Revision 7](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0002 Revision 7](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0011 Revision 3](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0012 Revision 2](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 5 resolutions

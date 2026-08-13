# Adversarial review: DR-0011 revision 1

Target DR: DR-0011

Target revision: 1

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 3 review-resolution revision

Review lens: Morphology, graph representation, and graphics-system handoff

Reviewer: Fresh gpt-5.6-sol graphics reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: d554379

This artifact records review evidence only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 1 usefully separates Joint, Part, Socket, Attachment, Region,
Capability, and Field, but its articulation handoff remains cross-cutting and
its measurement-conflict rule is not minimally executable. Both gaps can lead
to incompatible graphics and resolver behavior.

## Prior-finding closure

The earlier articulation finding is partially closed: required ordered roles
and adjacency are now stated, but concept and endpoint typing remains open.
The other three prior blockers—namespace ownership/remapping, the unified
pre-semantic result envelope, and the three-way fixture outcome taxonomy—are
closed. This review does not reopen them.

## Blocking Objections

1. **High — Cross-cutting articulation typing is not defined.**

   **Failure scenario:** DR-0008's required articulation roles and DR-0011's
   Joint vocabulary can be implemented with different endpoint concepts,
   cardinality, direction, or frame placement. A graphics consumer cannot
   determine whether a named role is a Part, landmark/reference designation,
   or Joint endpoint while preserving semantic lineage.

   **Recommended resolution:** Define the Joint relation's typed endpoints and
   role vocabulary jointly with DR-0002 and DR-0008. Specify Part ownership,
   landmark/reference roles, endpoint cardinality/direction, and frame
   placement while retaining the engine-independent no-bone/no-solver claim.

2. **High — Minimum measurement-conflict semantics are undefined.**

   **Failure scenario:** The record says conflicting dimensions, transforms,
   landmarks, or other constraints diagnose failure but does not define the
   minimum conflict set, deterministic status/diagnostic behavior, or whether
   a snapshot may be published. Implementations can silently choose different
   precedence or expose incompatible partial results.

   **Recommended resolution:** Define the minimum conflict semantics now:
   conflicting authored constraints must produce a deterministic failure in
   the authoritative operation-result envelope, with stable diagnostic
   category/order and no valid-supported snapshot. State the participating
   typed values and frame conversions; defer exact numeric tolerances and
   diagnostic codes only if they remain explicitly later specification work.

## Non-blocking Risks

**Medium — Cross-DR fixture-matrix coverage remains a later obligation.**

Before implementation evidence is treated as proof, provide one frozen
fixture matrix that links durable identity/address cases to the typed concepts,
articulation endpoints, measurement/frame cases, expected outcomes, and
diagnostic coverage across DR-0006, DR-0011, and DR-0008. It must include
bilateral/repeated modules through regeneration; a Region spanning multiple
Parts; a rotated or offset mating-frame Attachment that is not a Joint;
equivalent right- and left-handed sources with asymmetric landmarks,
joint/socket frames, winding, and normals; and explicit accepted or rejected
outcomes for negative scale, non-uniform scale, and shear once that policy is
selected.

## Conditions for Acceptance

Define the cross-DR typed articulation vocabulary and minimum deterministic
measurement-conflict behavior, then prove both in the fixture matrix. Ben's
owner disposition and the required current-revision review evidence remain
governed by the repository process.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No resolver, graph,
fixture matrix, rendering, benchmark, validation tooling, or technical-rigging
or data-model specialist evidence was available.

## Documents Consulted

- DR-0011 Revision 1
- DR-0002 Revision 5
- DR-0006 Revision 4
- DR-0008 Revision 5
- CK-KICK-012 Batch 3 discussion resolutions
- Product requirements and specification index

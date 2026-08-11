# Adversarial review: DR-0002 revision 6

Target DR: DR-0002

Target revision: 6

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 4 current-revision double review

Review lens: Semantic graph, graphics, and runtime handoff

Reviewer: Fresh gpt-5.6-sol semantic-graph/graphics/runtime reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 7dba9346c91c59ff99f10b94630690bf732d6b28

This artifact records review evidence only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 6 gives the resolved graph a useful containment-versus-relation
boundary, but several graph and frame rules needed by graphics and runtime
consumers remain implicit. The operation envelope also still lacks deterministic
phase outcome behavior. These gaps cross-link to
[DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
[DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
and [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).

## Prior-blocker closure

The classification and measurement blockers are closed by the Batch 4
resolutions. Articulation typing is only partially closed: directed Joint and
Part roles are selected, but endpoint-frame ownership and optional Attachment
placement remain open. This review does not reopen the closed portions.

## Blocking Objections

1. **High — Optional-module Attachment has no structural ownership insertion or
   socket-frame placement rule.**

   **Failure scenario:** A host/mating Socket pair can be resolved with
   different owners for the attached Parts, different host-to-mating alignment,
   or a conflict between authored placement and socket placement. Duplicate,
   cyclic, detached, and attached-root cases can consequently produce
   incompatible graphs. The absence of an implied Joint is stated, but does
   not by itself define composition.

   **Recommended resolution:** Specify the owner of attached Parts, host and
   mating frame alignment/placement, authored-placement conflict behavior,
   duplicate/cycle/detached validity, and the no-implied-Joint rule jointly in
   DR-0002, DR-0008, and DR-0011.

2. **High — Joint endpoint frames permit competing owner/role interpretations.**

   The `owns or refers` wording allows implementations to assign different
   owner-plus-role addresses to the same endpoint. Select the canonical
   resolved owner, endpoint role, Part basis, Socket/frame treatment,
   provenance, and any equivalence or normalization rule.

3. **High — Root reachability conflates containment with relation traversal.**

   Every embodied Part, including an optional attached Part, needs exactly one
   root containment path. Relation traversal cannot repair a disconnected
   containment tree. Define containment reachability separately from relation
   cycles and state-transform inheritance/topology, with deterministic invalid
   outcomes for disconnected or multiply owned Parts.

4. **Medium — Phase/outcome precedence and reachable diagnostics remain
   unspecified.**

   The envelope names ordered diagnostics but does not state recognition
   suborder, phase/status precedence, which diagnostics are reachable after a
   fatal phase, or how truncation behaves. This overlaps the contract finding
   in the independent review and is required for a deterministic graph
   snapshot boundary.

## Non-blocking Risks

Later fixtures should cover repeated modules; attached-root ownership and
offset sockets; relation-only disconnected containment; multi-Part Regions;
handedness, winding, and normals; value provenance/conflict; scale/shear;
multi-fault, truncation, and resource exhaustion; and semantic equivalence.
The review also advises a specialist data-model and technical-rigging/art
pass. These are evidence obligations, not closure of the blockers above.

## Conditions for Acceptance

Define Attachment composition and containment reachability separately from
relations, choose one endpoint-frame ownership model, and make phase/outcome
precedence and diagnostic reachability deterministic across the linked DRs.
Ben's owner disposition and the required current-revision review evidence
remain governed by the repository process.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No resolver, graph,
runtime, fixture, rendering, benchmark, validation, or specialist
data-model/technical-rigging evidence was available.

## Documents Consulted

- [DR-0002 Revision 6](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008 Revision 6](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0011 Revision 2](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0012 Revision 1](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 4 resolutions

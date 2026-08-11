# Adversarial review: DR-0011 revision 2

Target DR: DR-0011

Target revision: 2

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

Revision 2 provides the needed seven typed concepts and a useful distinction
between containment, articulation, and attachment, but the graph-to-runtime
handoff is not yet uniquely resolvable. Attachment placement, Joint endpoint
frames, and containment reachability need cross-DR rules before the vocabulary
can serve as a stable implementation contract.

## Prior-blocker closure

The prior classification and measurement blockers are closed. Articulation
typing is partially closed: the Joint/Part direction and cardinality are
explicit, but endpoint-frame ownership and Attachment placement remain open.

## Blocking Objections

1. **High — Attachment lacks structural ownership insertion and socket-frame
   placement semantics.**

   Define the owner of attached Parts, host/mating alignment and placement,
   authored-placement conflicts, duplicate/cycle/detached validity, and
   attached-root behavior. Preserve the explicit rule that Attachment does not
   imply a Joint.

2. **High — Joint endpoint frames allow `owns or refers` ambiguity.**

   Select one canonical owner-plus-role address for each endpoint, the
   proximal/distal Part basis, Socket/frame treatment, provenance, and any
   equivalence or normalization rule. Otherwise graphics and runtime consumers
   can derive different transforms from the same Joint.

3. **High — Part root reachability is not separated from relation traversal.**

   Every embodied Part needs exactly one containment path to the root;
   relations cannot repair a disconnected or multiply owned containment tree.
   State relation-cycle rules separately from containment and define the state
   transform-inheritance topology.

4. **Medium — Outcome/diagnostic precedence remains a cross-DR dependency.**

   The semantic-invalid measurement result in this record depends on the
   envelope's phase/status precedence, recognition suborder, reachable
   diagnostics after fatal phases, and truncation rules. Resolve those in
   [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md) and
   [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
   without changing the seven-concept boundary.

## Non-blocking Risks

Fixtures should cover repeated modules; attached roots and offset sockets;
relation-only disconnected containment; multi-Part Regions;
handedness/winding/normals; value provenance/conflict; scale/shear;
multi-fault/truncation/resource behavior; and semantic equivalence. A
specialist data-model and technical-rigging/art pass is advised.

## Conditions for Acceptance

Define canonical Attachment placement and Joint endpoint-frame ownership, make
containment reachability independent of relation traversal, and resolve the
linked envelope dependency. Ben's owner disposition and the required
current-revision review evidence remain governed by the repository process.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No resolver, graph,
runtime, fixture, rendering, benchmark, validation, or specialist
data-model/technical-rigging evidence was available.

## Documents Consulted

- [DR-0011 Revision 2](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0002 Revision 6](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008 Revision 6](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0012 Revision 1](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 4 resolutions

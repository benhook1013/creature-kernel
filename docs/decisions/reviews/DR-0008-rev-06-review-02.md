# Adversarial review: DR-0008 revision 6

Target DR: DR-0008

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

Revision 6 selects typed directed articulation and Socket-to-Socket Attachment,
but leaves the composition and frame handoff under-specified for a graphics or
runtime consumer. Its fixture outcome requirements also depend on the
unresolved deterministic envelope in
[DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).

## Prior-blocker closure

The classification and measurement blockers are closed. Articulation typing is
partially closed: the directed Joint/Part distinction is explicit, while
endpoint-frame ownership and optional Attachment placement remain blockers.

## Blocking Objections

1. **High — Optional-module Attachment lacks structural ownership insertion and
   socket-frame placement semantics.**

   Specify who owns attached Parts, how host and mating frames align or place
   the module, what happens when authored placement conflicts with socket
   placement, and how duplicate, cyclic, detached, or attached-root cases are
   classified. Attachment must remain composition and must not imply a Joint.

2. **High — Joint endpoint frames allow incompatible owner/role resolutions.**

   `owns or refers` can produce different owner-plus-role addresses for the
   same endpoint. Choose the canonical resolved owner and endpoint roles,
   proximal/distal Part basis, Socket/frame treatment, provenance, and any
   equivalence or normalization rule.

3. **High — Root reachability is not separated from relation traversal.**

   Every embodied Part, including optional Parts, must have one root
   containment path; a Joint or other relation cannot repair disconnected
   containment. Specify separate containment reachability and relation-cycle
   rules, plus state transform-inheritance topology.

4. **Medium — Phase/outcome precedence and reachable diagnostics are
   unspecified.**

   Recognition suborder, phase/status precedence, diagnostics reachable after a
   fatal phase, and truncation are not defined. This overlaps the contract
   review's envelope finding and prevents deterministic fixture outcomes.

## Non-blocking Risks

Fixtures should cover repeated modules; attached-root ownership and offset
sockets; relation-only disconnected containment; multi-Part Regions;
handedness/winding/normals; value provenance/conflict; scale/shear;
multi-fault/truncation/resource behavior; and semantic equivalence. A
specialist data-model and technical-rigging/art pass is advised.

## Conditions for Acceptance

Define Attachment ownership and placement, canonical Joint endpoint frames, and
separate containment reachability from relation traversal. Complete the linked
outcome/diagnostic rules and the fixture evidence before acceptance. Ben's owner
disposition and the required current-revision review evidence remain governed
by the repository process.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No resolver, graph,
runtime, fixture, rendering, benchmark, validation, or specialist
data-model/technical-rigging evidence was available.

## Documents Consulted

- [DR-0008 Revision 6](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0002 Revision 6](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0011 Revision 2](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0012 Revision 1](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 4 resolutions

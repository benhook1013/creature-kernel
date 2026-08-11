# Adversarial review: DR-0012 revision 1

Target DR: DR-0012

Target revision: 1

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

Revision 1 establishes a promising admission-to-snapshot phase boundary, but
the minimum invariants and diagnostic behavior are not sufficiently precise for
semantic-graph, graphics, or runtime consumers. Several findings are
cross-DR dependencies on the typed graph records.

## Prior-blocker closure

The classification and measurement blockers in the linked Batch 4 records are
closed. Articulation typing is partially closed: Joint/Part direction and
cardinality are selected, but endpoint-frame ownership and Attachment
placement remain unresolved. This new encoding record must not imply those
gaps are solved by its invariant list.

## Blocking Objections

1. **High — Attachment endpoint validity does not define composition ownership
   or socket-frame placement.**

   The minimum invariant “valid Joint and Attachment endpoints” is not enough
   to resolve optional modules. Define attached-Part ownership, host/mating
   alignment and placement, authored-placement conflicts,
   duplicate/cycle/detached/attached-root validity, and the no-implied-Joint
   rule in [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
   and [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).

2. **High — Joint endpoint frames permit incompatible owner/role resolutions.**

   Select canonical endpoint owner and role, proximal/distal Part basis,
   Socket/frame treatment, provenance, and equivalence or normalization. The
   resolver cannot publish a stable snapshot while `owns or refers` can produce
   different addresses for the same endpoint.

3. **High — The root invariant conflates containment and relation reachability.**

   Every embodied Part, including optional Parts, needs exactly one root
   containment path. Relations cannot repair disconnected containment. Separate
   containment reachability from relation-cycle rules and define the state
   transform-inheritance topology; the current “reachable through valid typed
   relations” wording (line 150) is insufficient.

4. **Medium — Phase/outcome precedence, recognition suborder, and diagnostics
   are unspecified.**

   Define which phases run after each fatal outcome, which diagnostics remain
   reachable, primary selection, multi-fault behavior, and truncation. This
   overlaps the independent contract review's envelope/recognition findings but
   is directly required by this record's promise of deterministic phase-local
   accumulation.

## Non-blocking Risks

Fixtures should cover repeated modules; attached-root ownership and offset
sockets; relation-only disconnected containment; multi-Part Regions;
handedness/winding/normals; value provenance/conflict; scale/shear;
multi-fault/truncation/resource behavior; and semantic equivalence. A
specialist data-model and technical-rigging/art pass is advised. Exact JSON,
extension, canonical-frame, dependency-revision, and hostile-input evidence
remain later obligations from the linked contract review.

## Conditions for Acceptance

Define the linked typed-graph composition and endpoint rules, separate
containment from relation reachability, and complete deterministic outcome and
diagnostic behavior. Ben's owner disposition and the required current-revision
review evidence remain governed by the repository process.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No resolver, graph,
runtime, fixture, rendering, benchmark, validation, or specialist
data-model/technical-rigging evidence was available.

## Documents Consulted

- [DR-0012 Revision 1](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [DR-0002 Revision 6](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008 Revision 6](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0011 Revision 2](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- Decision-record review process and CK-KICK-012 Batch 4 resolutions

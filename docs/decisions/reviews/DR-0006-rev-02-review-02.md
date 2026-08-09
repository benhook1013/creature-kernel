# Adversarial review: DR-0006 revision 2

Target DR: DR-0006

Target revision: 2

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 1 (DR-0002, DR-0006, and DR-0008)

Review lens: Morphology, graph representation, and graphics-system handoff

Reviewer: Fresh gpt-5.6-sol morphology/graph reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-10

Recommendation: Revise

Confidence: High

Reviewed commit: 21790de

This artifact records review evidence only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

The semantic/artifact identity split is useful, but the proposed key rule does
not yet support reusable procedural modules, relation objects, or structural
edits without hidden identity invention.

## Blocking Objections

1. **High — Reusable bilateral modules have no permitted instance identity.**

   **Failure scenario:** One arm module declares `limb`, `elbow`, and `paw`,
   then expands twice. Both instances need separate durable concepts, but every
   concept is required to use an author-declared key and incidental path/order
   derivation is prohibited.

   **Recommended resolution:** Choose explicit per-instance keys or allow
   module-instance anchors plus deterministic role-local descendant identity.
   Define collision behavior for repeated modules and optional replacements.

2. **High — Relation concepts and their frames are not represented clearly
   enough to receive durable identity.**

   **Failure scenario:** A shoulder region spans two parts, a joint has two
   endpoint frames, and a socket has host and mating frames. Treating these as
   typed edges leaves reification, endpoint roles, cardinality, frame placement,
   and independent identity unspecified.

   **Recommended resolution:** Permit non-ownership concepts to be reified and
   multiply related with role labels; define their identity and endpoint/frame
   rules in the later graph specification while keeping ownership as the sole
   containment tree.

3. **Medium — Structural edits make the broad regeneration guarantee unsafe.**

   **Failure scenario:** A region is split or an ear is deleted and recreated
   under the same key. Consumers cannot distinguish continuity from replacement.

   **Recommended resolution:** Limit current guarantees to unchanged authored
   concepts/keys through parameter, topology, LOD, and compiler regeneration;
   defer aliases, remaps, deletion/reuse, split, merge, and replacement rules.

## Non-blocking Risks

None separate from the conditions above.

## Conditions for Acceptance

Define instance identity, reified relation identity, and structural-edit
lifecycle semantics, then prove them with repeated-module and regeneration
fixtures.

## Review Limitations

Fresh read-only conceptual review. No graph implementation, fixtures,
benchmarks, or empirical evidence were available. Graph/data-model and
character technical director/rigging expertise remains appropriate.

## Documents Consulted

- DR-0006 Revision 2
- DR-0002 Revision 3
- DR-0008 Revision 3
- CK-KICK-010 walking-skeleton resolver and results
- Product requirements and specification index

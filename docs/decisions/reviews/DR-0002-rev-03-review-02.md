# Adversarial review: DR-0002 revision 3

Target DR: DR-0002

Target revision: 3

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

The proposals are consistent at the headline level, but the deferred semantic
specification does not yet define enough invariant structure to make reusable
procedural expansion, framed relations, diagnostics, and Stage 2 lineage
reliable.

## Blocking Objections

1. **High — Author-declared keys do not define identity for procedural
   expansion or reusable bilateral modules.**

   **Failure scenario:** A reusable arm module declares `limb`, `elbow`, and
   `paw`, then is instantiated left and right. The resolved graph needs
   distinct durable identities, but the proposal allows neither instance
   scope nor a permitted deterministic role-local derivation. Authors must
   flatten every expansion or the resolver invents identities against DR-0006.

   **Recommended resolution:** Choose whether every expanded concept must be
   explicitly keyed, or whether module-instance anchors plus deterministic
   role-local descendant identity are permitted. Define collision rules without
   relying on incidental tree paths.

2. **High — Typed relation edges are not yet an adequate representation for
   framed joints, sockets, or overlapping regions.**

   **Failure scenario:** A shoulder region spans torso and arm, a joint has
   parent-side and child-side frames, and a socket has host and mating frames.
   Treating these only as typed edges leaves binary versus reified structure,
   endpoint roles, cardinality, frame ownership, and independent identity
   unspecified.

   **Recommended resolution:** State that non-ownership concepts may be
   reified and participate in multiple role-labelled relations. Keep ownership
   as the sole containment tree, and defer endpoint roles, cardinality, cycles,
   frame placement, and multi-module region membership to the specification.

3. **Medium — Diagnostics are ambiguously placed inside a validated snapshot.**

   **Failure scenario:** A cyclic ownership source or missing required module
   cannot produce a validated compilable graph. If diagnostics exist only in
   that snapshot, the resolver must publish an invalid partial graph or fail to
   provide the promised diagnostic-bearing result. A well-formed deferred
   quadruped also needs a distinct unsupported result.

   **Recommended resolution:** Define a result envelope containing diagnostics
   and either a successful validated snapshot or no compilable snapshot.
   Distinguish malformed/invalid, well-formed-but-unsupported, and
   valid/supported outcomes, including any explicitly inspectable rejected
   partial graph.

4. **Medium — Regeneration-survival language exceeds the deferred lifecycle
   rules.**

   **Failure scenario:** An ear is removed and later recreated with the same
   key, or one region is split into two. Consumers cannot know whether the key
   denotes continuity, replacement, or accidental reuse, while the current
   consequences broadly promise survival across regeneration.

   **Recommended resolution:** Qualify the current guarantee to parameter,
   topology, LOD, and compiler regeneration where the authored concept/key is
   unchanged. Do not promise structural-edit continuity, deletion/reuse,
   aliases, or remaps until their lifecycle decision.

## Non-blocking Risks

None separate from the conditions above.

## Conditions for Acceptance

Resolve the identity, relation, and diagnostic result-boundary blockers; narrow
the regeneration guarantee or define lifecycle semantics; then prove the
choices with repeated-module, framed-relation, invalid/unsupported, and
regeneration fixtures.

## Review Limitations

Read-only review of the exact commit. No implementation, fixtures, benchmarks,
or empirical evidence were available. A graph/data-model specialist and
character technical director/rigging specialist should review the deferred
specification.

## Documents Consulted

- DR-0002 Revision 3
- DR-0006 Revision 2
- DR-0008 Revision 3
- CK-KICK-010 walking-skeleton resolver and results
- Product requirements and specification index
- Decision registry and review process

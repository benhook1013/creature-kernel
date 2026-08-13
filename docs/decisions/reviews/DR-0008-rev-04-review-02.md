# Adversarial review: DR-0008 revision 4

Target DR: DR-0008

Target revision: 4

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 1 review-resolution revision

Review lens: Morphology, graph representation, and graphics-system handoff

Reviewer: Fresh gpt-5.6-sol morphology/graph reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 1efb3e4

This artifact records review evidence only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 4 resolves the earlier identity, relation, Stage 1 lineage, and
result-boundary objections. Two morphology-facing ambiguities remain in the
first-family contract: the written articulation roles do not yet state their
cardinality and adjacency unambiguously, and the fixture freeze still uses a
binary valid/invalid classification while the result contract has three
outcomes.

## Prior-finding closure

The Revision 3 morphology findings about reusable identity, reified relations,
minimum articulation, and diagnostic result boundaries are addressed by the
current revision. These two findings are narrower residual ambiguities and do
not reopen the closed identity or graph-boundary resolutions.

## Blocking Objections

1. **Medium — Articulation slash/dash notation leaves cardinality and adjacency
   ambiguous.**

   **Failure scenario:** The strings `shoulder–elbow–wrist/paw-base` and
   `hip–knee–hock-or-ankle–paw-base` can be read as an exact chain, alternatives
   between roles, a slash-separated pair, or a loose list of landmarks. A
   generator could therefore emit one wrist/paw-base relationship, both
   alternatives, or an unspecified number/order of joints while still
   claiming conformance to the same envelope.

   **Recommended resolution:** State the required semantic role set and
   ordered adjacency/cardinality explicitly for each first-family chain. Do
   not use slash, dash, or “or” as overloaded serialization. Exact role names
   and serialized syntax may remain specification detail, but the semantic
   requirement must distinguish alternatives from required adjacent links.

2. **Medium — Binary fixture classification conflicts with the three-way result
   taxonomy.**

   **Failure scenario:** A well-formed quadruped or other deferred-family
   assembly is unsupported, not semantically invalid, yet the fixture freeze
   currently records only valid or invalid. It may be counted as a valid pass,
   assigned an invalid diagnostic, or omitted from the gate differently by
   different experiment runners.

   **Recommended resolution:** Freeze the expected three-way outcome for every
   fixture: valid/supported, semantically invalid, or well-formed but
   unsupported. Freeze the expected primary diagnostic class/code for invalid
   and unsupported fixtures where applicable, and state which outcomes count
   toward the Stage 1 valid-fixture gate.

## Non-blocking Risks

None separate from the objections above.

## Conditions for Acceptance

Define articulation role cardinality and adjacency without overloaded prose,
and align fixture freeze classification with the result envelope's three-way
taxonomy before accepting this revision. Prove the choices with articulation
and invalid/unsupported fixtures.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No implementation,
fixtures, experiments, benchmarks, captures, validation tooling, or specialist
digitigrade anatomy, technical-rigging, or data-model evidence was available.

## Documents Consulted

- DR-0008 Revision 4
- DR-0002 Revision 4
- DR-0006 Revision 3
- CK-KICK-010 walking-skeleton experiment and results
- Product requirements and specification index

# Adversarial review: DR-0009 revision 3

Target DR: DR-0009

Target revision: 3

Review status: Complete

Reviewer: Fresh gpt-5.6-sol geometry/semantics/measurement reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 4dcd3dad6b044d731e06b606eea5b9c885ebe444

## Executive Assessment

The bounded ablation is clearer, but valid measured technology failures remain
too easy to classify as unavailable evidence, and the frontier, empty-frontier,
and interaction rules do not yet support an unambiguous component-attribution
claim.

## Blocking Objections

1. Measured technology failures are misclassified as unavailable evidence.
   Reserve `Inconclusive` for unavailable or invalid oracles and shared
   experiment defects; a valid registered measurement that violates frozen
   clearance, convergence, phase/topology, or budget criteria is a branch
   mandatory technology failure and must contribute to `Reject`.
   Evidence at the reviewed commit: DR-0009 lines 114, 138, and 150; DR-0010
   lines 103, 111, 223, and 229.
2. The empty-frontier rule permits comparative `Support` without comparative
   evidence. Make this `Inconclusive`, or a separately named feasibility-only
   outcome that cannot support non-inferiority or improvement.
   Evidence at the reviewed commit: DR-0009 lines 110, 140, and 145.
3. The Pareto table overlaps and omits visual comparison. Define visual gate
   versus comparison dimension, dominance/non-regression, and explicit
   mixed-tradeoff precedence.
   Evidence at the reviewed commit: DR-0009 lines 123, 141, and 143.
4. Interactions are only reported, not assessed or disposed. Registration must
   define per-criterion interaction contrasts and how direction, ambiguity, or
   disagreement constrain component-attribution and named-improvement claims.
   Evidence at the reviewed commit: DR-0009 lines 211 and 219, the first-surface
   design line 147, and the visual-quality protocol line 45.

## Non-blocking Risks

None beyond the blocking objections.

## Conditions for Acceptance

Separate valid branch failures from unavailable evidence, remove comparative
support from the empty-frontier case, define visual and mixed-tradeoff
precedence, and predeclare interaction contrasts and their effect on claims.

## Review Limitations

This was a conceptual read-only review. No implementation, registered
experiment, fixtures, captures, numerical thresholds, or specialist animation
topology assessment was available. Validation and tests were not run under the
review assignment.

## Documents Consulted

- [DR-0009](../DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [DR-0010](../DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
- [First surface experiment design](../../research/first-surface-experiment-design.md)
- [Visual-quality protocol](../../research/visual-quality-evaluation.md)

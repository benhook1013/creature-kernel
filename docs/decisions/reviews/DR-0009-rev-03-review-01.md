# Adversarial review: DR-0009 revision 3

Target DR: DR-0009

Target revision: 3

Review status: Complete

Reviewer: Fresh gpt-5.6-sol architecture/proof/governance reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 4dcd3dad6b044d731e06b606eea5b9c885ebe444

## Executive Assessment

Revision 3 improves the evidence-first and readiness rules, but the outcome
contract still conflates apparatus failures with valid branch technology
failures and leaves several comparative precedence and fairness rules open.

## Blocking Objections

1. Branch-caused technology failures are classified as evidence failures.
   Clipping, sampling non-convergence, phase/topology instability, and
   effort-budget breach are always `Inconclusive`, without distinguishing
   inadequate shared apparatus from a branch intrinsically violating frozen
   output or budget criteria. Independently demonstrated common-pipeline or
   measurement inadequacy should be `Inconclusive`; after apparatus/readiness
   passes, a branch-specific violation of frozen clearance, convergence,
   phase/topology, or feasibility criteria should contribute to `Reject`;
   genuinely indeterminate attribution should remain `Inconclusive`.
   Evidence at the reviewed commit: DR-0009 lines 114–121 and 145–152,
   DR-0010 lines 223–232, and the first-surface design lines 169–180.
2. The outcome table overlaps `Reject` and `Inconclusive` for frontier
   regression versus unresolved structural/semantic/visual/complexity/effort
   trade-offs. Define regression, distinguish mandatory from nonmandatory
   criteria, and set precedence: mandatory regression is `Reject`; an
   acceptable/non-inferior trade-off continues; an unresolved nonmandatory
   trade-off is `Inconclusive`.
   Evidence at the reviewed commit: DR-0009 lines 134–143 and the first-surface
   design lines 242–255.

## Non-blocking Risks

1. Logging reuse does not control tuning-order and knowledge-transfer bias.
   Freeze permitted shared infrastructure, order/counterbalancing,
   parameter inheritance or knowledge carry-over, and how those costs are
   charged to budgets.
   Evidence at the reviewed commit: DR-0009 lines 193–200 and the first-surface
   design lines 137–145.
2. The frontier omits the visual dimension even though visual trade-offs
   affect outcomes. Include comparative visual assessment in the frontier, or
   make it a gate-only criterion and remove it from frontier-dependent
   trade-off logic.
   Evidence at the reviewed commit: DR-0009 lines 123–132 and 141–143, and the
   visual-quality protocol lines 98–114.

## Conditions for Acceptance

Resolve the causal-failure classification and outcome precedence, then freeze
the reuse/tuning-order controls and the visual comparison policy before
registration. Do not imply acceptance of the proposal.

## Review Limitations

This was a conceptual read-only review. No implementation, registered
experiment, fixtures, captures, benchmarks, or specialist geometry assessment
was available. Validation and tests were not run under the review assignment.

## Documents Consulted

- [DR-0009](../DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [DR-0010](../DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
- [First surface experiment design](../../research/first-surface-experiment-design.md)

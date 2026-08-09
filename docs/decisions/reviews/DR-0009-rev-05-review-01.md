# Adversarial review: DR-0009 revision 5

Target DR: DR-0009

Target revision: 5

Review status: Complete

Reviewer: Fresh gpt-5.6-sol architecture/proof/governance reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: a676b5295a990d9624c53f81dfbe508e002334b7

## Executive Assessment

Revision 5 strengthens the experiment's readiness, comparison, and attribution
controls, but two finite-budget and component-attribution gaps remain blocking
for architectural, proof, and governance reasons.

## Blocking Objections

1. High: The finite readiness clock can start only after unbounded branch
   implementation. Evidence at the reviewed commit: DR-0009 lines 140, 292,
   and 296, and the first-surface design lines 137–153. Registration freezes a
   starting point, but readiness occurs before primary comparison and a
   detected defect starts the budget, allowing unlimited implementation before
   the first readiness attempt. The authoritative start must be before
   branch-specific implementation; remediation counted by the experiment and
   detected defects must consume an already-running budget.
2. High: Bundle Support can survive loss of component-attribution ablation
   evidence. Evidence at the reviewed commit: DR-0009 lines 148–154, 229–234,
   309–348, and 448–474. A failed S+B or S+G branch can be excluded while Full
   still gets Support against a surviving baseline even though required paired
   attribution becomes unresolved. Either require valid paired branches for a
   component claim or explicitly split bundle comparative Support from
   component-attribution outcomes and mark the affected component claim
   Inconclusive.

## Non-blocking Risks

None beyond the blocking objections.

## Conditions for Acceptance

Start the authoritative finite readiness budget before branch-specific
implementation and count detected defects against the already-running budget.
Require valid paired ablation branches for a component claim, or split bundle
comparative Support from component-attribution outcomes and mark affected
component claims Inconclusive. Do not imply acceptance of the proposal.

## Review Limitations

This was a conceptual read-only review of the assigned architecture, proof,
and governance corpus. No implementation, registration, fixtures, thresholds,
captures, benchmarks, or specialist validation were available; broad
validation was not run, and no edits were made.

## Documents Consulted

- [DR-0009](../DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [First surface experiment design](../../research/first-surface-experiment-design.md)

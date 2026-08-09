# Adversarial review: DR-0009 revision 8

Target DR: DR-0009

Target revision: 8

Review status: Complete

Execution state: Complete

Reviewer: Fresh gpt-5.6-sol measurement/protocol reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Review lens: Measurement integrity, visual adjudication, causal attribution,
and closure semantics

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 6bf7f1cd58f9bb38b6b4bf738dc29c04603b6abc

## Executive Assessment

Revision 8 resolves the generic vocabulary and `NA`/`U` representation,
removes the contradictory `combined-hybrid-only` proposal tag, aligns the
run lifecycle fields, and replaces ambiguous generic attribution with
branch/failure attribution. Four measurement and protocol gaps remain:
post-checkpoint repair provenance can permit incomparable selective reruns;
the visual-floor gate lacks independent adjudication; outcome-changing
branch/failure attribution is procedurally underdefined; and component `U`
versus bundle closure remains ambiguous.

## Blocking Objections

1. **High — Post-checkpoint repairs permit adaptive selectively rerun evidence
   across incomparable snapshots.**

   **Evidence:** DR-0009 lines 459-477 and 522-534; first-surface experiment
   design lines 120-132 and 152-177; experiment template lines 21-32.

   **Reason:** A repair author can declare affectedness and inspect outcome
   knowledge while selectively rerunning evidence. This permits mixing
   results from different snapshots and can change the outcome without a
   stable comparison basis.

   **Resolution:** Freeze `C` once primary evidence begins, or require
   preregistered objective repair triggers and a dependency map, independent
   affectedness adjudication, and outcome comparisons on one final snapshot;
   classify older snapshots as exploratory.

2. **High — The mandatory visual-floor gate lacks independent panel and
   deterministic adjudication.**

   **Evidence:** Visual protocol lines 100-125 versus 127-147; DR-0009 lines
   595-608 and 356-366.

   **Reason:** The mandatory floor can influence feasibility and outcomes, but
   its panel independence, masking, individual vote recording, and
   disagreement handling are not sufficiently specified for reproducible
   adjudication.

   **Resolution:** Define a separate visual-floor vote schema and deterministic
   pass/fail/unresolved aggregation with at least three reviewers independent
   of implementation and tuning, masking/randomization where feasible, and
   recorded individual votes.

## Non-blocking Risks

3. **Medium — Outcome-changing branch/failure attribution is procedurally
   underdefined.**

   **Evidence:** DR-0009 lines 203-214, 265-314, 383-394, and 536-557.

   **Reason:** The revised branch/failure vocabulary identifies the intended
   attribution target, but does not yet specify the causal attribution tree,
   diagnostic evidence, adjudicator independence, or the point at which
   attribution must be fixed relative to repair and outcome inspection.

   **Resolution:** Preregister a causal attribution tree and diagnostic
   evidence, require independent adjudication before repair or outcome
   inspection, and keep unresolved attribution `Inconclusive`.

4. **Medium — Complete closure is ambiguous when component `U` includes
   invalid or unavailable evidence.**

   **Evidence:** DR-0009 lines 586-608, 409-421, 292-304, 383-385, and
   411-414.

   **Reason:** The no-block rule for component `U` permits bundle closure, but
   the documents do not clearly distinguish complete bundle outcome evidence
   from component-level attribution evidence or state which `U` causes remain
   compatible with closure.

   **Resolution:** Define bundle-outcome closure separately from
   component-attribution closure, specify which `U` causes are compatible with
   bundle closure, or make the relevant contrasts mandatory and revise the
   no-block rule.

## Resolved Scope

The generic vocabulary and `NA` handling, removal of the
`combined-hybrid-only` tag, lifecycle fields, and branch/failure attribution
wording otherwise resolve the corresponding prior findings. DR-0010's two
known unresolved findings are outside this review's scope.

## Conditions for Acceptance

Resolve the two High findings by fixing checkpoint/repair comparability and
the visual-floor adjudication protocol. Resolve the two Medium findings by
specifying causal attribution timing and evidence, and by separating bundle
outcome closure from component attribution closure. The recommendation remains
`Revise` until these four findings are addressed or Ben records an explicit
waiver.

## Review Limitations

This was a fresh conceptual measurement and protocol review of the reviewed
commit. No implementation, registered runs, fixtures, captures, benchmarks,
or threshold measurements were available.

## Documents Consulted

- `docs/decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md`
- `docs/research/first-surface-experiment-design.md`
- `docs/research/visual-quality-evaluation.md`
- `experiments/experiment-template.md`
- `docs/decisions/reviews/fresh-reread-preamble.md`

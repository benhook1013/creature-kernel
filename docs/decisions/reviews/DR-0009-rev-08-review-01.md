# Adversarial review: DR-0009 revision 8

Target DR: DR-0009

Target revision: 8

Review status: Complete

Execution state: Complete

Reviewer: Fresh gpt-5.6-sol governance/provenance/budget reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 6bf7f1cd58f9bb38b6b4bf738dc29c04603b6abc

This artifact records review evidence only. It accepts no product, specification,
architecture, or decision-record proposal.

## Executive Assessment

Revision 8 closes the previously identified taxonomy, visual/schema,
experiment-lifecycle, and component-attribution ambiguities, but five
provenance, budget-accounting, and repair-epoch risks remain. The repair-log
model is not yet a closed comparison protocol, and its finite accounting
cannot yet be enforced or carried by the supporting experiment records.

## Blocking Objections

1. **High — Repair snapshots are identities but not closed comparison epochs.**

   **Evidence:** DR-0009 lines 472-477, 271-274, and 368-394.

   **Reason:** A repair snapshot identifies a log prefix, but the proposal does
   not close a comparison epoch around the base manifest, snapshot, and branch
   budgets. Evidence can therefore be mixed across snapshots or reset after a
   repair, while the outcome predicates may consume a later C state.

   **Resolution:** Define an immutable comparison epoch for each base-manifest,
   repair-snapshot, and budget tuple. An outcome must use one closed epoch only.
   Close and retain the old epoch after a repair, requiring a full rerun or a
   preregistered, independently reviewable unaffectedness proof. Later C
   exhaustion must not retroactively change a closed epoch's outcome.

2. **High — Post-checkpoint C admission remains outcome-contingent and
   asymmetrically gameable.**

   **Evidence:** DR-0009 lines 225-240 and 459-477.

   **Reason:** The universal-repair admission test can still be applied after
   observing comparative behaviour, and deliberate C exhaustion can influence
   which repairs are admitted or whether the comparison reaches an outcome.

   **Resolution:** Preregister repair classes, admission authority, and the
   branch-neutral trigger. Require the trigger to be independently reproduced
   before comparative outcome inspection. A post-unmask repair must create a
   separately labelled epoch and may be exploratory rather than silently
   extending the primary comparison.

## Non-blocking Risks

3. **Medium — Finite C lacks an enforceable consumption rule.**

   **Evidence:** DR-0009 lines 467-477 and 245-250; experiments README lines
   39-52.

   **Reason:** The record declares C finite but does not define an enforceable
   accounting unit, atomic entry rule, deterministic charge, or minimum charge.
   Zero-cost, split, or unquantifiable entries could therefore avoid the cap.

   **Resolution:** Freeze the C accounting unit and atomic-entry rule. Define a
   deterministic charge, a balance, and either a maximum entry count or a
   strictly positive minimum charge. If effort or charge is unavailable, make
   that a terminal accounting condition rather than treating it as zero.

4. **Medium — The supporting workflow can exclude C from the actual total.**

   **Evidence:** DR-0009 lines 252-262 versus experiments README lines 53-59
   and first-surface design lines 158-163.

   **Reason:** The decision record says actual project effort includes full C
   effort, but supporting workflow language can read as if only incremental
   branch work contributes to the actual total.

   **Resolution:** Define actual total effort as including C exactly once, with
   a separate C breakout. Incremental feasibility may exclude C only when it
   identifies the relevant base-manifest and repair-snapshot IDs.

5. **Medium — The experiment template cannot carry the frozen accounting
   record.**

   **Evidence:** Experiments README lines 61-64 versus experiment template
   lines 21-32.

   **Reason:** The template does not provide fields for ledger and branch-budget
   registration, repair balance and log, evidence-to-snapshot mapping,
   repair-admission evidence, or per-epoch disposition.

   **Resolution:** Add registration tables for ledgers and branch budgets, the
   repair balance/log, evidence-snapshot mappings, repair-admission evidence,
   and each epoch's disposition.

## Conditions for Acceptance

Resolve the two High findings by defining closed immutable comparison epochs
and preregistered, branch-neutral repair admission. Resolve the three Medium
findings by making C consumption enforceable, aligning actual-effort reporting,
and extending the supporting template with the required frozen accounting and
epoch records.

## Review Limitations

This was a fresh conceptual governance, provenance, and budget review of the
reviewed commit. Implementation, registration tooling, fixtures, captures,
benchmarks, specialist validation, and empirical evidence were unavailable.

## Documents Consulted

- DR-0009 Revision 8
- `docs/research/first-surface-experiment-design.md`
- `experiments/README.md`
- `experiments/experiment-template.md`

# Adversarial review: DR-0009 revision 7

Target DR: DR-0009

Target revision: 7

Review status: Complete

Reviewer: Fresh gpt-5.6-sol experiment-design/measurement reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: ff5086eb64101ea9793c0001123097e9b1c7c8e1

## Executive Assessment

Revision 7 resolves the Revision 6 findings on scaffold provenance and effort
allocation, interaction overclaim, component aggregation, quantitative overlap,
and incomplete/abandoned execution status. Four measurement and protocol gaps
remain: qualitative visual adjudication is underconstrained; the complete
matrix cannot represent the visual vocabulary or inapplicable cells; the
combined-hybrid-only condition is contradictory and non-testable; and the run-
status vocabulary conflicts with the canonical lifecycle vocabulary.

## Blocking Objections

1. **High — Qualitative visual adjudication is underconstrained.**

   **Evidence:** DR-0009 lines 499-504; visual protocol lines 102-125 and
   127-142.

   **Reason:** There is no reviewer count or independence requirement,
   masking/randomization rule, per-reviewer vote record, or deterministic
   consensus/disagreement rule. The sole unblinded tuner can decide cells that
   affect the frontier.

   **Resolution:** Preregister reviewers and independence, masking/randomization
   where practical, individual judgments, and a deterministic
   consensus/disagreement-to-`U` rule. Define a criterion-specific comparative
   rubric distinct from the visual-floor rubric.

2. **High — The complete matrix cannot represent the visual vocabulary or
   inapplicable cells.**

   **Evidence:** DR-0009 lines 487-515; first-surface experiment design lines
   63-68 and 179-215; visual protocol lines 127-136.

   **Reason:** The matrix has no visually-equivalent-to-`N` mapping and no
   `NA` state for absent sites, so a complete matrix cannot faithfully encode
   visual criteria or cells that do not apply to a fixture/site.

   **Resolution:** Preregister the domain as applicable cells, keep `NA`
   separate, and use separate matrices or an explicit generic-neutral mapping
   with modality-specific evidence rules.

## Non-blocking Risks

3. **Medium — `combined-hybrid-only` is contradictory and non-testable.**

   **Evidence:** DR-0009 lines 346-358 and 517-522; first-surface experiment
   design lines 215-222.

   **Reason:** DR-0009 permits the tag whenever the combined bundle supports,
   while the design says it applies only when both contributions are present.

   **Resolution:** Rename it to `nonexclusive combined-bundle-supported`, or
   preregister literal `Full` passes and one-layer branches do-not predicates.
   Treat the tag as descriptive, not causal.

4. **Medium — Run-status vocabulary conflicts with the canonical lifecycle
   vocabulary.**

   **Evidence:** `docs/README.md` lines 74-87; DR-0009 lines 233-242;
   first-surface experiment design lines 172-177.

   **Reason:** The canonical vocabulary is `planned`/`running`/`complete`/
   `inconclusive`/`abandoned`, while the proposal introduces `In progress`/
   `Complete`/`Incomplete`/`Abandoned` and uses `Inconclusive` as an outcome.

   **Resolution:** Use a separately named run-closure field while retaining the
   lifecycle vocabulary, or explicitly revise the canonical vocabulary and
   align the affected documents.

## Conditions for Acceptance

Resolve both High findings by specifying the visual-reviewer and adjudication
protocol, and by making matrix applicability, `NA`, and visual-equivalence
encoding exhaustive. Resolve the Medium vocabulary and combined-hybrid-only
issues as described above. The Revision 6 findings remain resolved; the
current recommendation remains `Revise` until these four findings are
addressed.

## Review Limitations

This was a fresh conceptual experiment-design and measurement review of the
reviewed commit. No implementation, registration, fixtures, captures,
benchmarks, or threshold measurements were available.

## Documents Consulted

- `docs/decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md`
- `docs/research/first-surface-experiment-design.md`
- `docs/research/visual-quality-evaluation.md`
- `docs/README.md`
- `docs/decisions/reviews/fresh-reread-preamble.md`

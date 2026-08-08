# Adversarial decision reviews

Status: Provisional operational trial

This directory stores concise reviews of specific DR revisions. Reviews are
evidence and recommendations, not decisions.

## Review qualities

A useful review should:

- target a DR ID and revision;
- state its reviewer, independence, date, recommendation, and confidence;
- steelman the strongest alternative;
- identify hidden assumptions and missing expertise;
- examine failure modes, irreversibility, performance, portability, licensing,
  and integration risk where applicable;
- distinguish blockers from acceptable risk; and
- disclose limitations.

Keep a normal review to at most five high-value issues. A review may optionally
list `Documents Consulted` when that helps the next decision. It need not
produce an exact source inventory, immutable bundle, content identity, or
structured objection ledger.

## Staleness and disposition

When a DR materially changes, increment its revision. Reviews of earlier
revisions remain historically useful but no longer satisfy acceptance of a
newer revision. Important DRs normally receive one current-revision review
before acceptance. Ben may explicitly waive a review with `Review status:
Waived` and one non-placeholder `Waiver reason:` line in the DR. Findings return
to Ben and the main thread; they are not auto-fixed or re-reviewed in a
review-until-clean loop.

## Independence

The review should state whether it used a fresh context, separate AI
agent/model, external expert, project author, or another method. Lack of
independence does not make a review worthless, but it must not be hidden.

Use the [fresh-reread preamble](fresh-reread-preamble.md) for an issue-only,
one-pass convergence review. The broader [AI delegation workflow](../../developer-workflows/ai-delegation-and-review.md)
defines model routing and ownership boundaries.

## Naming

Use `DR-NNNN-rev-RR-review-NN.md`, with two-digit revision and review numbers.

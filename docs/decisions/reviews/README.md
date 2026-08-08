# Adversarial decision reviews

Status: Operational under Accepted DR-0001 Revision 5

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
newer revision. At the end of every substantive design-cycle handoff, the main
thread states `Recommended adversarial level: None|Single|Double — <one-line
reason>` as advice to Ben and a durable planning signal, not automatic
acceptance. `None` is for purely mechanical/reversible work or discussion with
no created or materially revised consequential DR and no novel evidence-bearing
claim; it cannot satisfy the review prerequisite for a created or materially
revised consequential DR. `Single` is the normal default and means one fresh
independent pass. `Double` is exceptional for direction-setting,
cross-cutting, hard-to-reverse or locking, technically complex, strongly
evidence-dependent, disputed, or difficult-to-audit work; it means two
genuinely independent fresh passes with distinct named lenses. More than Double
or Sol above medium requires Ben's explicit approval. Ben may raise, lower, or
waive the recommendation. Double is one pass per reviewer on the current
revision, not review-until-clean; the main thread consolidates duplicates and
contradictions and presents only actionable findings. Ben may explicitly waive
a review with `Review status: Waived` and one non-placeholder `Waiver reason:`
line in the DR. Findings return to Ben and the main thread; they are not
auto-fixed or re-reviewed in a review-until-clean loop.

## Independence

The review should state whether it used a fresh context, separate AI
agent/model, external expert, project author, or another method. Lack of
independence does not make a review worthless, but it must not be hidden.

Use the [fresh-reread preamble](fresh-reread-preamble.md) for an issue-only,
single-pass convergence review when the selected level is Single. The broader
[AI delegation workflow](../../developer-workflows/ai-delegation-and-review.md)
defines model routing and ownership boundaries.

## Naming

Use `DR-NNNN-rev-RR-review-NN.md`, with two-digit revision and review numbers.

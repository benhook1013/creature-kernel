# Adversarial decision reviews

Status: Active process proposal

This directory stores reviews of specific ADR revisions. Reviews are evidence and
recommendations, not decisions.

## Required review qualities

A useful review must:

- target an exact ADR ID and revision;
- state its recommendation and confidence;
- steelman the strongest alternative;
- identify hidden assumptions and missing expertise;
- examine failure modes, irreversibility, performance, portability, licensing,
  and integration risk where applicable;
- request concrete evidence rather than vague reassurance;
- distinguish blockers from acceptable risk;
- disclose limitations of the review.

## Staleness

When an ADR materially changes, increment its revision. Reviews of earlier
revisions remain historically useful but no longer satisfy acceptance.

## Independence record

The review should state whether it used a fresh context, separate AI agent/model,
external expert, project author, or another method. Lack of independence does not
make a review worthless, but it must not be hidden.

## Naming

Use `ADR-NNNN-rev-RR-review-NN.md`, with two-digit revision and review numbers.

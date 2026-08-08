# Adversarial decision reviews

Status: Provisional operational trial

This directory stores reviews of specific DR revisions. Reviews are evidence and
recommendations, not decisions.

## Required review qualities

A useful review must:

- target an exact DR ID and revision;
- state its recommendation and confidence;
- steelman the strongest alternative;
- identify hidden assumptions and missing expertise;
- examine failure modes, irreversibility, performance, portability, licensing,
  and integration risk where applicable;
- request concrete evidence rather than vague reassurance;
- distinguish blockers from acceptable risk;
- identify the exact canonical review bundle and sources actually read;
- record structured responses to material objections;
- disclose limitations of the review.

## Staleness

When a DR materially changes, increment its revision. Reviews of earlier
revisions remain historically useful but no longer satisfy acceptance.

## Canonical Review Bundle

Every complete review must list one local Markdown link per bundle item and must
include the target DR at the exact revision under review. Include all affected
canonical documents and relevant research or experiment evidence. Do not use
fake placeholder links.

## Sources Actually Read

Every complete review must list one local Markdown link per source actually read.
The list must be truthful and may overlap the canonical review bundle.

Current-revision adversarial review is mandatory for acceptance; it cannot be
replaced by a waived review. Explicit waivers or deferrals are limited to
non-review proof or evidence obligations and must record reason and accepted
risk in the target DR.

## Independence record

The review should state whether it used a fresh context, separate AI agent/model,
external expert, project author, or another method. Lack of independence does not
make a review worthless, but it must not be hidden.

Use the [fresh-reread preamble](fresh-reread-preamble.md) for an issue-only
convergence pass. The broader
[AI delegation workflow](../../developer-workflows/ai-delegation-and-review.md)
defines model routing, review evidence, and main-thread synthesis.

## Naming

Use `DR-NNNN-rev-RR-review-NN.md`, with two-digit revision and review numbers.

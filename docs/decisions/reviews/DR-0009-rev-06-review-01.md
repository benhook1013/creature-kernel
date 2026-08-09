# Adversarial review: DR-0009 revision 6

Target DR: DR-0009

Target revision: 6

Review status: Complete

Reviewer: Fresh gpt-5.6-sol architecture/proof/governance reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 0f26240658c1bd1f75e0d2dd92420fbd3243932d

## Executive Assessment

Prior findings 3/4/5 resolved; finding2 boundary resolved but exposes
aggregation gap; finding1 incomplete due subset-shared allocation.

## Blocking Objections

1. **High — Subset-shared operation implementation is unallocated around the
   common-scaffold checkpoint.**

   Evidence: DR-0009 lines 169, 317-324, 328-359; first-surface design line
   138.

   Reason: B, G, and much S benefit subsets rather than all branches, so work
   can be placed pre-checkpoint as shared or charged inconsistently.

   Resolution: Preregister work taxonomy/allocation; restrict scaffold to
   identical all-branch infrastructure/oracles; subset-shared operation work
   occurs after checkpoint and is charged under a frozen auditable rule to
   consuming branches or a separately bounded shared-layer ledger incorporated
   consistently into feasibility/effort.

2. **High — Criterion-level B/N/H/U states do not determine promised
   component-level attribution.**

   Evidence: DR-0009 lines 295, 385-436, 761-781.

   Reason: Mixed criterion vectors have no exhaustive aggregation/precedence
   and permit post-hoc scalarization/selective credit.

   Resolution: Define exhaustive aggregation predicates and precedence
   including mandatory harm and U, or make the full per-criterion matrix the
   only result and remove categorical component outcome.

## Non-blocking Risks

3. **Medium — First-surface design says N/N “No effect” while DR-0009 says
   neutral equivalence within a frozen margin.**

   Evidence: DR-0009 lines 403-415, 423; design lines 183/189.

   Reason: The first-surface design wording does not match the DR-0009
   neutral-equivalence contract.

   Resolution: Use “Neutral equivalence in both contrasts within the frozen
   margin” in design/schemas/reports.

## Conditions for Acceptance

The resolutions stated under the three findings are the conditions for
acceptance.

## Review Limitations

This was a concise conceptual, read-only review; implementation, registration,
fixtures, captures, benchmarks, and specialist validation were unavailable.

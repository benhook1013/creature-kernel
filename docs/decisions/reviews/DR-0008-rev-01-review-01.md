# Adversarial review: DR-0008 revision 1

Target DR: DR-0008

Target revision: 1

Review status: Complete

Reviewer: Fresh gpt-5.6-sol subagent (Round 5 review)

Independence: Fresh context; separate agent instance; read-only; independent of implementation

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 8501a81

## Executive Assessment

The bounded digitigrade family and minimal Stage 1 embodiment envelope give
Round 5 a useful varied target. This revision is not yet ready for Ben's
disposition because its Stage 1/Stage 2 artifact ownership, fixture failure
semantics, and qualitative fixture identities conflict with or remain
underspecified against the staged proof charter.

## Blocking Objections

1. **Stage 1 and Stage 2 embodiment ownership is contradictory.** This DR
   makes Stage 1 emit analytic collision/contact regions and basic
   bind/skinning metadata “where practical,” while DR-0007 assigns generated
   skeletons/skinning to Stage 2 and the roadmap assigns generated collision
   proxies/contact regions to Stage 2. “Where practical” leaves Stage 1 pass
   obligations unclear. Ben should choose the mandatory Stage 1 artifact set.
   A coherent middle option is source-linked semantic joint frames and region
   intent in Stage 1, with generated bind weights and collision proxies in
   Stage 2; alternatively, generated artifacts could be mandatory in Stage 1
   and Stage 2 revised accordingly.

2. **The Stage 1 continuation rule does not define how fixture failures affect
   the claim.** DR-0007 says “several,” this DR requires at least four
   evaluated fixtures, and the protocol permits pass, fail, or inconclusive
   outcomes. Ben should decide whether every fixed valid fixture must meet the
   structural and subjective floor, or define a narrower partial-success claim
   with explicit handling for failure and inconclusive results.

3. **Qualitative fixture labels are not fixed enough to preserve evidence
   across stages.** Exact inputs and ratios are deferred and two profiles
   overlap, so the evidence population could drift. Before evidence is used
   for surface-method selection or the Stage 1 gate (Ben should decide which
   boundary applies), freeze stable fixture identities, concrete source
   inputs, seeds/configuration, and discriminating parameters. Digitigrade
   anatomy and technical rigging expertise may also be needed.

## Non-blocking Risks

No non-blocking findings beyond the blockers above.

## Conditions for Acceptance

Resolve the three blockers in the canonical DRs or their governing protocol,
with Ben's owner disposition remaining explicit. Freeze the family fixture
population and disclose any profile overlap before using its evidence for
method selection or a Stage 1 gate.

## Review Limitations

This was a conceptual, read-only review of DR-0007 Revision 1 and DR-0008
Revision 1 at the exact clean commit listed above. It assessed no
implementation, fixtures, benchmark, external specialist, or web evidence;
validation was deferred. No concurrent-work risk was observed at review
return.

## Documents Consulted

- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0007](../DR-0007-staged-first-proof-charter.md)
- [Decision record registry](../registry.md)
- [Project status](../../project/status.md)
- [Adversarial review process](README.md)
- [Adversarial review template](adversarial-review-template.md)

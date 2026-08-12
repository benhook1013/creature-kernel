# Adversarial review: DR-0013 revision 6

Target DR: DR-0013

Target revision: 6

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012/013 Batch 10 current-revision Double review

Review lens: Platform, failure, reversibility, numeric-frame, adapter portability, and future runtime

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-12

Recommendation: Revise

Confidence: High

Reviewed commit: `28c83c7a21cf55f23274aeaf5d2ccc0a3e9e3b53`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 6 gives the first platform a useful bounded publication and worker
trust model. The remaining issues are the R2/R3 carrier wording and activation
link, the lack of a distinct R3 successor transaction, and two overlapping
failure rules carried from earlier prose.

## Blocking Objections

1. **High — C1:** Make the R2 structural rigid-transform carrier explicit and
   let R3 own numeric/frame semantics rather than reselecting the rotation
   representation. Align the wording and links across DR-0011, DR-0012, and
   DR-0013.
2. **High — C2:** Define the R3 successor transaction separately from the R2
   admission: it must contain the successor manifest, expected snapshots,
   comparison profile/rule, resolver implementation or exact binding, unchanged
   content-identity preflight, and a project-ledger activation trigger.
3. **Medium — C4:** Remove or qualify the old success-or-failure-bundle
   wording; initial failures are envelope-only with staging cleanup unless a
   separately decided evidence facility exists.
4. **Medium — C5:** Distinguish trusted-parent termination after an established
   timeout/resource breach (`resource-limit`) from unexpected termination,
   transport loss, or unqualified failure (`internal-failure`).

## Non-blocking Risks

Before filesystem publication activates, reproduce the exact WSL `/home`
filesystem and no-replace capability profile, crash behaviour, and safe
orphaned-staging reclamation. This is nonblocking follow-up evidence.

## Conditions for Acceptance

Resolve C1–C5 across the platform, build-operation, and fixture-manifest
boundaries, then provide the R3 successor, transform, status, and publication
fixtures before owner acceptance.

## Review Limitations

No implementation, filesystem probe, crash test, fixture corpus, worker
harness, snapshot comparator, publication transaction, or runtime portability
evidence was available.

## Documents Consulted

- DR-0013 Revision 6 and linked current decision records
- Build-operation, body-document, body-graph, and fixture-manifest proposals
- Current architecture, project status, readiness, and prior review evidence

# Adversarial review: DR-0013 revision 4

Target DR: DR-0013

Target revision: 4

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012/013 Batch 9 current-revision Double review

Review lens: Platform, failure, reversibility, and publication

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-12

Recommendation: Revise

Confidence: High

Reviewed commit: `6cf17270fda2827756c24a8d0fb301bef358f98f`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 4 makes the conceptual build/publication operation and Readiness 2
transaction explicit, but retry/concurrent publication, filesystem durability,
trust separation, and reversible immutable admission are not yet contractually
closed. The exact format remains deferred to the canonical build-operation
specification.

## Blocking Objections

1. **High — R2-F1: retry identity and concurrent publication are incoherent.**
   Define stable request lineage versus attempt identity, candidate
   derivation/stable key, comparison fields, and post-`EEXIST` verification that
   converts an identical winner to already-published while leaving a mismatch
   as conflict.
2. **High — R2-F2: atomic publication lacks filesystem durability and
   tamper-safe inspection.** Define the supported filesystem profile/threat
   model, same-filesystem staging, primitive capability probe, sync/durability
   rule if claimed, crash/staging recovery, case/Unicode behavior, and
   stable-handle or explicit non-adversarial immutable-root limits.
3. **High — R2-F3: worker failure status and reporter trust are conflated.**
   Separate producer/output trust from coordinator/reporter/publisher trust;
   a parent may report observed worker failure but never adopt untrusted worker
   output, and coordinator/publisher trust loss forbids publication.
4. **Medium — R2-F4: Readiness 2 admission is not durably pinned or
   reversible.** Pin exact commit/tree and manifest digest, record approval and
   preflight against it, rerun on the merged target, and define append-only
   supersession/deactivation/rollback, separate from evidence for expectation
   correctness.

## Non-blocking Risks

The absent-module rule is consistent. CK-KICK-014 remains exploratory without
a permanent surface selection.

## Conditions for Acceptance

Resolve R2-F1 through R2-F4 and provide the corresponding filesystem,
publication, trust, admission, rollback, and fixture evidence before owner
acceptance.

## Review Limitations

No implementation, filesystem probe, fixture, benchmark, publication
transaction, or worker evidence was available. Coverage included the authority
chain, six DRs, specifications, fixtures, architecture/project material, and
prior reviews as history only.

## Documents Consulted

- DR-0013 Revision 4 and the five linked current DRs
- Relevant specification, fixture, readiness, architecture, and project docs
- Prior review artifacts for formatting and history only

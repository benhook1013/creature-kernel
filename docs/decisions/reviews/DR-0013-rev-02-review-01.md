# Adversarial review: DR-0013 revision 2

Target DR: DR-0013

Target revision: 2

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 7 current-revision double review

Review lens: Contract, schema, determinism, and authority boundaries

Reviewer: Fresh gpt-5.6-sol contract/schema/determinism/authority reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 88004388f9537a37617ae248bdaad4625e6f3f03

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 2 gives the first Rust platform and replaceable geometry boundary a
clearer activation intent and stronger artifact language. Two authority and
activation gaps remain blocking: parser/schema/fixture gates are circular or
ambiguous, and compiler, geometry, worker, and publication outcomes do not yet
share one complete authority model.

## Blocking Objections

1. **High — Parser and fixture activation gates are circular or ambiguous.**

   **Failure scenario:** Acceptance triggers the Cargo shell, while parser and
   resolver work is gated by an exact schema and admitted fixtures. The fixture
   area is described as activating on the first compiler-consumed document,
   while the semantic specification implies that files remain unactivated until
   implementation consumes the contract. Cargo shell, parser/resolver, fixture,
   and geometry/surface decision or CK014 ledger gates therefore do not provide
   one auditable ordering.

   **Recommended resolution:** Publish an explicit ordered activation table with
   sole trigger, prerequisite, owner, and evidence for shell creation,
   parser/bootstrap, semantic normalization/snapshot, admitted fixtures, and
   geometry/surface work. Remove the first-consumption versus not-yet-activated
   contradiction.

2. **High — Compiler, geometry, worker, and publication outcomes lack one
   authority model.**

   **Failure scenario:** Geometry or a future worker can contribute status and
   diagnostics while the compiler envelope claims authoritative outcome, and
   publication can fail after a complete failure result or artifact identity is
   expected. A consumer can then see competing status channels or a supposedly
   complete bundle that was never atomically published.

   **Recommended resolution:** Define compiler outcome versus geometry/worker
   and publication outcomes, their ownership and merge rules, optional artifact
   identities, and the rule that no final bundle exists when publication fails.
   State staging cleanup ownership and prevent derived diagnostics from
   competing with the compiler envelope.

## Non-blocking Risks

No additional DR-0013-specific issue was identified from this contract lens
beyond the deferred worker and reproducibility obligations in the companion
review. Those obligations remain important activation evidence, not a claim
that this review accepts the platform.

## Conditions for Acceptance

Close the activation ordering and outcome/publication authority contracts.
Provide an auditable gate table and failure fixtures covering parser/bootstrap,
semantic resolution, geometry, worker crash/timeout, and publication failure.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
Cargo workspace, worker protocol, geometry backend, artifact publisher,
fixtures, benchmarks, or specialist security/portability audit was available.

## Documents Consulted

- [DR-0013](../DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Repository-evolution ledger and decision-record review process
- Decision-record review process and CK-KICK-012 Batch 7 review brief

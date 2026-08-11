# Adversarial review: DR-0013 revision 2

Target DR: DR-0013

Target revision: 2

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 7 current-revision double review

Review lens: Platform, build, geometry, reversibility, and host-integration boundaries

Reviewer: Fresh gpt-5.6-sol platform/build/geometry/reversibility/host-integration reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 88004388f9537a37617ae248bdaad4625e6f3f03

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 2 makes a sensible stable-Rust, replaceable-geometry, and independent
workbench proposal. Activation ordering and publication failure semantics are
blocking gaps; worker isolation and reproducible-build obligations are
appropriately non-blocking until those capabilities activate.

## Blocking Objections

1. **High — Activation gates are contradictory.**

   **Failure scenario:** Cargo shell creation, exact parser/schema admission,
   resolver activation, fixture admission, and geometry/surface decision or
   CK014 ledger prerequisites are described with incompatible or circular
   ordering. A team cannot determine from the current records when parser,
   resolver, fixtures, or geometry work is authorized.

   **Recommended resolution:** Define one auditable activation table naming the
   sole trigger, prerequisites, owner, and evidence for each stage, and separate
   parser/bootstrap from semantic normalization/snapshot and later geometry or
   surface commitments.

2. **High — A complete failure-bundle promise is impossible when publication
   itself fails.**

   **Failure scenario:** Compiler failure, geometry/worker failure, and artifact
   publication failure are all treated as if they can produce one complete
   immutable bundle. A failed publication can leave no final bundle, and
   inventing a final artifact identity or status would mislead the workbench.

   **Recommended resolution:** Separate compiler outcome from publication
   outcome; make artifact identities optional until publication succeeds; state
   that publication failure yields no final bundle, and define owned staging
   cleanup and status/diagnostic mapping.

## Non-blocking Risks

1. **Medium — Resolver activation needs a staged schema/frame/fixture contract.**

   Exact schema and admitted fixtures are insufficient without canonical axes and
   units, rotation representation, scale/shear policy, numeric representation,
   and tolerances. Distinguish parser/bootstrap from semantic normalization and
   snapshot publication. This corroborates the activation-gate finding and is a
   later activation obligation, not a request for heavyweight process.

2. **Medium — Future worker activation checklist is incomplete.**

   Before activating a worker, record output-root/final-target separation,
   process-tree termination, resource/output/log bounds, handle and network
   policy, a framed protocol, cleanup ownership, and deterministic status
   mapping. These are non-blocking while the worker remains a future trigger.

3. **Medium — Evidence-build reproducibility checklist is incomplete.**

   A reproducible claim should record the exact stable release, targets,
   components, build command and environment, distro/kernel/libc/linker/native
   tools, CPU features, dependency sources/features/checksums or locked Git
   revisions, and a native smoke before a native portability claim. This is a
   lightweight evidence checklist, not heavyweight bureaucracy.

No additional independent DR-0013 issue was identified from this lens beyond
the compiler/publication authority finding and the linked schema activation
concern.

## Conditions for Acceptance

Resolve activation ordering and publication-failure semantics. Before worker or
portability claims activate, record the bounded worker checklist and the
reproducibility metadata needed to reproduce the evidence.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
Cargo workspace, worker protocol, geometry backend, artifact publisher,
fixtures, benchmarks, or portability evidence was available.

## Documents Consulted

- [DR-0013](../DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Repository-evolution ledger and decision-record review process
- Decision-record review process and CK-KICK-012 Batch 7 review brief

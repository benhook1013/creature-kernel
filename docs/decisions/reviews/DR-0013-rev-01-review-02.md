# Adversarial review: DR-0013 revision 1

Target DR: DR-0013

Target revision: 1

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 6 current-revision double review

Review lens: Semantic graph, graphics/geometry, build, portability, and runtime boundaries

Reviewer: Fresh gpt-5.6-sol semantic-graph/graphics/geometry/build/portability/runtime reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: c64b1b98948304d631eecea6a354c9e42c89c510

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 1 appropriately keeps geometry replaceable and the workbench outside
semantic ownership, but its first production boundary is not yet safe to
activate. The replaceable geometry seam, process/filesystem isolation, and
reproducible build target need concrete backend-neutral and publication
contracts.

## Blocking Objections

1. **High — The replaceable geometry boundary lacks a minimum backend-neutral
   seam.**

   **Failure scenario:** Dense-field evaluator/extractor details can leak into
   semantic or CLI surfaces, making a future worker/backend replacement a
   breaking change. The record does not require a versioned request and
   backend-neutral result with bounded diagnostics, configuration/capability
   metadata, and lineage.

   **Recommended resolution:** Define that versioned request/result seam and
   lineage/diagnostic/capability metadata. Keep backend-native types out of
   semantic and CLI contracts, and explicitly avoid treating this seam as a
   permanent surface or as DR-0009/DR-0010 evidence.

2. **High — Filesystem/process failure isolation is insufficient.**

   **Failure scenario:** A crash, timeout, resource exhaustion, stale output,
   symlink/path escape, or partial package can be mistaken for a valid build or
   be consumed by the workbench. Immutable build identity, staging,
   manifest-last/atomic publication, integrity, incomplete-output refusal, and
   future worker protocol/version/output validation are not closed.

   **Recommended resolution:** Specify those publication and integrity rules,
   bounded path/resource behavior, and compiler survival/validation behavior
   for crash, timeout, and malformed worker output.

## Non-blocking Risks

3. **Medium — Stable Rust and WSL/native Linux do not yet establish
   reproducibility.**

   Pin toolchain and dependency proof inputs, record MSRV/update policy,
   target/libc/CPU/reference environment, license/debug/build metadata, and run
   an explicit portability check. Preserve a trigger for capability,
   portability, and resource gaps, not only performance.

## Conditions for Acceptance

Define the versioned backend-neutral geometry seam and isolated, atomic,
integrity-checked artifact publication. Then add reproducible toolchain,
dependency, target, and portability policy. No permanent API or DR-0009/DR-0010
evidence claim follows from this review.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
worker protocol, build/dependency manifests, fixtures, benchmarks, or
specialist graphics, security, or portability evidence were available.

## Documents Consulted

- [DR-0013](../DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
- [DR-0006](../DR-0006-durable-semantic-and-artifact-identity.md)
- [DR-0009](../DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [DR-0010](../DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
- Repository-evolution and decision-record review process

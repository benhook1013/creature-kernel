# Adversarial review: DR-0013 revision 8

Target DR: DR-0013

Target revision: 8

Review status: Complete

Execution state: Complete

Coverage: Complete

Batch context: CK-KICK-012/013 Batch 12 current-revision Double review

Review lens: Experiment validity/proportionality, floating-point build controls, adapter mathematics/portability, activation/reversibility, performance feasibility, project-state alignment

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-12

Recommendation: Revise

Confidence: High

Reviewed commit: `730a2f77840cc0caa1f838c30dac4ff20f985e69`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 8 improves the numeric evidence gate, but the proposed production
platform still lacks deterministic runtime transcendental binding, a complete
adapter unit-scale contract, and an end-to-end FTZ/DAZ guarantee. Mechanical
summary drift also remains. These issues block a reproducible Readiness 3 or
adapter claim; the platform remains Proposed.

## Blocking Objections

1. **High — E1:** Runtime `asin` lacks a deterministic algorithm, version, and
   output rule; the official Rust `f64::asin` does not provide the required
   deterministic precision binding. Bind a deterministic implementation and
   output rule, or compare the half-chord directly against an admitted
   precomputed threshold, removing runtime transcendental evaluation.
2. **Medium — E2:** The adapter lacks a positive unit scale for metre-to-cm/mm
   hosts. Before activation define `s`; distinguish dimensionless
   directions/normals from points, displacements, dimensions, and translations;
   use `t' = s C t` and `D = diag(s C, 1)`; add known-magnitude fixtures.

## Non-blocking Risks

3. **Medium — E3:** The target profile does not distinguish serialization-only
   subnormal bits from target/runtime arithmetic under FTZ/DAZ. Declare the
   guarantee scope, probe actual arithmetic, preserve end-to-end behaviour, or
   exclude/fail affected values with fixtures.
4. **Medium — E4 (mechanical consistency):** Execution-model and component
   summaries wrongly defer fixed formulas and normalization. Narrow their open
   list to constants, ranges, margins/error formula, and deterministic
   evaluation bindings.
5. **Low — E5 (mechanical consistency):** The DR-0013 review response says
   Revision 7 and the project phase stops at Batch 11. Correct the self-label to
   Revision 8 and the current phase to Batch 12.

## Conditions for Acceptance

Resolve E1–E3 with deterministic arithmetic/adapter guarantees and known-value
fixtures, apply E4/E5 mechanically, and retain the unresolved C1/C3/C4
findings. No engine, adapter, readiness gate, or implementation package is
activated by this review.

## Review Limitations

No runtime, adapter, compiler-mode probe, numeric experiment, readiness
transaction, performance benchmark, or target-engine implementation was
available. This pass does not choose an adapter scale, elementary-function
implementation, threshold, or target precision.

## Documents Consulted

- DR-0013 Revision 8 and linked current decision records
- Numeric/frame, body-document, body-graph, build-operation, fixture-manifest, and canonical-data proposals
- Current architecture, product summaries, project status, registry, and Batch 11 review artifacts

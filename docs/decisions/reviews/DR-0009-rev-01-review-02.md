# Adversarial review: DR-0009 revision 1

Target DR: DR-0009

Target revision: 1

Review status: Complete

Reviewer: Fresh Sol-medium geometry/topology/semantic-data review

Independence: Fresh context; separate reviewer/model pass; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 31f9561

## Executive Assessment

The hybrid is a plausible disposable hypothesis for combining semantic control,
organic junctions, and reusable feature generation. A strongest simpler
alternative is a single shared construction rule, which would make causal
interpretation easier. The current branch comparison confounds skeleton
control, selected blending, and specialized generators, and asymmetrically
restricts the baselines, so the experiment cannot establish which contribution
caused an outcome.

## Blocking Objections

1. Branch comparison and attribution are under-specified. Require a frozen
   branch-operation matrix, common semantic-input mapping and output interface,
   tuning/effort budgets, and a strongest credible baseline with the same
   semantic feature vocabulary. Add nested ablations such as
   hybrid-minus-blending and hybrid-minus-specialists, or explicitly limit the
   claim to a combined bundle with no causal attribution.

## Non-blocking Risks

The selected construction rules may still expose topology or feature failures
that require fixture-level diagnosis. Those failures should remain visible and
should not be repaired by adding per-fixture exceptions.

## Conditions for Acceptance

Freeze the branch-operation matrix, common semantic-input/output contract,
tuning and effort budgets, and strongest credible baseline before running or
interpreting EXP-0001. Decide whether bounded ablations are required for the
claim being made.

## Review Limitations

This was an independently fresh, bounded conceptual read-only review with
primary-source checks only; validation was deferred. It did not inspect
implementation, experiment execution, benchmarks, captures, licensing, or
specialist anatomy review.

## Documents Consulted

- [DR-0009](../DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0010](../DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
- [Decision record registry](../registry.md)
- [Project status](../../project/status.md)
- Official scikit-image 0.26 marching-cubes documentation/implementation
- Official OpenVDB 13 ParticlesToLevelSet documentation and 13.0.0 header

# Adversarial review: DR-0010 revision 1

Target DR: DR-0010

Target revision: 1

Review status: Complete

Reviewer: Fresh Sol-medium geometry/topology/semantic-data review

Independence: Fresh context; separate reviewer/model pass; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 31f9561

## Executive Assessment

The pinned uniform-grid extraction and parallel-field direction are useful
disposable controls, but fixed sampling alone does not establish comparable
geometry or semantic lineage. Official scikit-image 0.26 marching-cubes
documentation/implementation and official OpenVDB 13 ParticlesToLevelSet
documentation plus its 13.0.0 header support the bounded capability checks;
they do not support the stronger project-wide lineage claim as written.

## Blocking Objections

1. The common field contract is incomplete. Require coordinates, units, sign,
   isovalue, bounds, padding, interpolation, out-of-domain behavior,
   feature-relative sampling, clipping checks, and a resolution-convergence
   protocol.
   Clarify that the Lewiner guarantee applies only to reconstruction from the
   sampled grid.

2. Vertex sampling alone does not prove semantic lineage. Categorical IDs
   cannot be interpolated like scalar fields, and module local-coordinate
   charts need identity and validity rules. Require construction-operator
   contributor semantics, categorical sampling, raw and top-k contributor
   weights, chart identity/invalidity, missing-field masks, and analytical
   ground-truth fixtures. OpenVDB's user-defined attribute grid support in
   particle rasterization does not establish the stronger multi-field lineage
   claim.

## Non-blocking Risks

Add boundary/non-manifold, genus/Euler, self-intersection, winding/orientation,
and normal checks. Define numeric/process/platform scope, mesh
canonicalization/hashes/tolerances, and stage-level isolation of nondeterminism.

## Conditions for Acceptance

Specify the common field contract and convergence/clipping controls, then
define construction-operator contributor semantics and analytical fixtures for
lineage. Add the listed topology, orientation, determinism, and canonicalization
diagnostics before using the experiment to support a stronger claim.

## Review Limitations

This was an independently fresh, bounded conceptual read-only review with
primary-source checks only; validation was deferred. It did not inspect
implementation, experiment execution, benchmarks, captures, licensing, or
specialist anatomy review.

## Documents Consulted

- [DR-0010](../DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
- [DR-0009](../DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [Decision record registry](../registry.md)
- [Project status](../../project/status.md)
- Official scikit-image 0.26 marching-cubes documentation/implementation
- Official OpenVDB 13 ParticlesToLevelSet documentation and 13.0.0 header

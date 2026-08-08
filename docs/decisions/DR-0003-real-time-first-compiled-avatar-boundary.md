# DR-0003: Real-time-first compiled avatar boundary

ID: DR-0003

Scope: Product and architecture

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-05

Date decided: —

Supersedes: —

Superseded by: —

## Context

Surface generation, remeshing, skinning, collision cooking, and volumetric
preprocessing may not fit a game frame. The motivating outcome nevertheless
remains an interactive game rather than only an offline scene renderer.

The architecture needs to distinguish expensive invariant compilation from
bounded per-frame interaction while preserving an optional higher-fidelity path.

## Decision

Treat a real-time game as the primary downstream constraint. Compile creature
source into a stable runtime avatar package outside the frame loop. Runtime
systems operate on bounded representations with quality tiers, regional
activation, and fallbacks. An optional cinematic path may use the same source at
higher fidelity but must not be required for basic interaction.

The initial frame budget, hardware, character count, solver limits, and runtime
mutation boundary remain open decisions requiring benchmarks.

## Consequences

- Expensive compilation is compatible with a live game.
- Runtime formats and budgets become explicit architectural concerns.
- Topology-changing edits may require loading screens or asynchronous package swaps.
- Maximum fidelity cannot run uniformly across every body and scene.
- Game and cinematic outputs can share source while using different representations.

## Alternatives Considered

### Fully dynamic generation and simulation

Maximizes flexibility but risks unbounded frame work, unstable topology, and
unrealistic performance expectations.

### Offline scene tool only

Permits maximum fidelity but abandons the motivating interactive-game outcome.

### Conventional fixed assets only

Fits existing engines but gives up much of the procedural body and recompilation
vision.

## Adversarial Review Response

Pending review of revision 1.

## Implementation and Proof Obligations

- Define compiled versus dynamic data contracts.
- Establish reference hardware and performance scenarios.
- Benchmark generation, runtime deformation, and quality activation.
- Define package swap, saved-state, and attachment behaviour if asynchronous
  recompilation enters scope.
- Prove a useful fallback path without advanced deformable-body features.

## Canonical Design Links

- [Vision and scope](../product/vision-and-scope.md)
- [Product requirements](../product/requirements.md)
- [Execution model](../architecture/execution-model.md)

## Reversibility and Revisit Triggers

The compile/runtime split can evolve, but package contracts create coupling.
Revisit when benchmarks show more generation can run live, required interactions
cannot fit bounded representations, or the primary product shifts away from games.

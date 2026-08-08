# DR-0003: Compiled avatar and bounded real-time execution

ID: DR-0003

Scope: Product and architecture

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-08

Date decided: —

Supersedes: —

Superseded by: —

## Context

Surface generation, remeshing, skinning, collision cooking, and volumetric
preprocessing may not fit a game frame. The motivating outcome nevertheless
remains an interactive game rather than only an offline scene renderer. The
product requirements therefore require bounded runtime work and graceful
fallbacks, while leaving exact budgets and proof thresholds open.

DR-0002 provides the authoritative source set and per-build semantic graph;
DR-0006 separates durable semantic identity from artifact/build identity. This
record defines how those compiled results are used in time and runtime
contexts. Revision 1 left the time domain, runtime representation, mutation
boundary, authoring reload, capability tiers, and determinism level open.

## Decision

Treat a real-time game as the primary downstream constraint and use the
following proposed boundary:

1. **Time domain — Recommendation: Option 2.**
   - Option 1: compile invariant and expensive work outside the frame loop and
     use only blocking or loading-screen recompilation for structural changes.
   - Option 2: compile invariant and expensive work initially outside the frame
     loop, while permitting a future background recompile that keeps the old
     validated package active. Background compilation is not mandatory for the
     first proof.
   - Option 3: retain fully live procedural generation and structural mutation
     in the frame loop.
   Per-frame work is bounded to pose, contact, parameterized deformation, and
   explicitly activated regional solvers.

2. **Runtime representation — Recommendation: Option 3.**
   - Option 1: retain only conventional bounded assets.
   - Option 2: retain a fully live implicit generator by default.
   - Option 3: use a hybrid: load conventional bounded assets such as meshes
     and LODs, skeleton/skinning, collision, materials, and prepared
     deformation data, plus only selected semantic fields, cages, SDFs, or
     regional structures useful for live behaviour.
   The default is not a fully live implicit generator and does not discard all
   semantic information into conventional assets.

3. **Mutation boundary.** Compatible package parameters may update in place.
   Topology, body-plan, major attachment, collision, or capability changes
   require recompilation. Unsafe or large changes may use a loading-screen
   fallback. A future asynchronous swap may keep the old package active while
   compiling and validating a replacement, then swap at a safe boundary. It
   should attempt to preserve semantic pose/root state, compatible
   attachments, gameplay state, and source-package references. It must not
   promise mesh-index preservation or restoration of incompatible solver state.

4. **Editor and authoring reload — Recommendation: Option 1 initially, with
   Option 2 later.**
   - Option 1: blocking in-session reload. Editing does not require closing and
     reopening the scene or session; preview may pause or freeze while the
     creature compiles, validates, and is replaced. Failure keeps the old
     avatar and reports diagnostics.
   - Option 2: asynchronous in-session hot swap, intended as a later workflow.
   - Option 3: arbitrary fully live structural editing, not required.
   This is an authoring/preview lifecycle, not a promise that ordinary gameplay
   supports every structural edit.

5. **Quality and capabilities.** Use bounded capability tiers and fallbacks. A
   provisional conceptual ladder is Base (skeletal animation, basic IK, and
   analytic collision), Enhanced (morph/cage/GPU deformation and richer
   contact), High-end (strictly limited regional soft or two-way effects), and
   Cinematic/offline (heavy volumetric, fur, cloth, or self-collision work).
   These labels and their numeric budgets are not normative yet. Higher-end
   hardware increases a finite budget; it never authorizes unbounded work.

6. **Determinism.** Require reproducible source resolution and compilation,
   stable semantic IDs, artifact/package provenance, and recorded build
   configuration. Bit-exact cross-machine simulation, rollback/lockstep/server
   authority, cross-version replay, and transient solver restoration are
   deferred until activated requirements justify them.

An optional cinematic or offline path may use the same source at higher
fidelity, but it is not required for basic interaction.

This proposed boundary does not select an engine, language, geometry or physics
backend, package serialization, exact swap protocol, morphology, frame rate,
hardware profile, character count, solver iteration count, or networking
architecture.

## Consequences

- Expensive compilation is compatible with a live game, and the first proof may
  use a blocking authoring reload rather than requiring an asynchronous system.
- Runtime packages retain enough selected semantic data for live behaviour
  without requiring a fully live implicit generator.
- Compatible parameter edits can remain in place; structural edits require a
  validated replacement and may fall back to a loading screen.
- Future package swaps have a semantic-state preservation goal, not a promise
  of mesh-index or incompatible solver-state continuity.
- Runtime quality and capability negotiation must remain finite and provide a
  useful fallback.
- Source resolution, compilation, package provenance, and build configuration
  become reproducibility inputs; stronger simulation determinism remains
  deferred.
- Game and cinematic outputs can share source while using different bounded or
  offline representations.

## Alternatives Considered

### Time-domain alternatives

#### Option 1: Blocking compilation and reload only

Keeps the runtime and first implementation simple, but makes every structural
change interrupt the preview or gameplay flow. It remains the required fallback
when a future background swap is unavailable or unsafe.

#### Option 2: Compile invariant work outside the frame loop

This is the recommended time-domain direction because it protects the real-time
target while leaving room for a future asynchronous compile and swap workflow.
The first proof can remain simpler by compiling outside the frame loop and using
a blocking authoring reload.

#### Option 3: Fully live procedural generation

Maximizes runtime flexibility but risks unbounded frame work, unstable topology,
and unrealistic performance expectations.

### Offline scene tool only

Permits maximum fidelity but abandons the motivating interactive-game outcome.

### Runtime-representation alternatives

#### Option 1: Conventional fixed assets only

Fits existing engines but gives up much of the procedural body and recompilation
vision. It is therefore too narrow for the runtime representation boundary.

#### Option 2: Fully live implicit generation

Preserves maximum procedural flexibility at runtime, but risks unbounded frame
work, difficult fallback behaviour, and coupling gameplay to compilation costs.

#### Option 3: Hybrid runtime representation

Preserves conventional bounded execution while retaining selected semantic data
for live deformation, contact, and regional behaviour. It is the recommended
representation direction, subject to proof of which selected data is useful.

## Adversarial Review Response

Pending a fresh adversarial review of Revision 2.

## Implementation and Proof Obligations

- Define compiled versus dynamic data contracts and measure the operation split
  under RQ-050.
- Establish reference hardware, performance scenarios, and finite capability
  budgets under RQ-053; do not infer numerical targets from this record.
- Benchmark generation, runtime deformation, quality activation, and selected
  semantic runtime data.
- Classify compatible and structural changes under RQ-051 and later specify
  package swap and saved-state behaviour under RQ-052 if asynchronous
  recompilation enters scope.
- Prove a useful fallback path without advanced GPU or regional features under
  RQ-054.
- Evaluate collision ownership and localized representation choices under
  RQ-040 through RQ-045.
- Define the required determinism level for saving, replay, and networking
  under RQ-055 before activating those contracts.
- Defer package serialization, engine integration, backend selection, and
  networking architecture to their own decisions and experiments.

## Canonical Design Links

- [Vision and scope](../product/vision-and-scope.md)
- [Product requirements](../product/requirements.md)
- [Execution model](../architecture/execution-model.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)

## Reversibility and Revisit Triggers

The compile/runtime split can evolve, but package contracts create coupling.
Revisit when benchmarks show more generation can run live, required interactions
cannot fit bounded representations, selected semantic runtime data is
insufficient, or the primary product shifts away from games. Revisit the
authoring reload path when async swap is proven useful; do not infer arbitrary
fully live structural editing from that future workflow.

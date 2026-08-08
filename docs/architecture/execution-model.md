# Execution model

Status: Provisional conceptual baseline

## Decision direction

A real-time game is the primary downstream target. Expensive creature generation
may occur outside the frame loop, while the compiled avatar exposes bounded
runtime representations. A higher-quality cinematic path is supplementary.

This direction is proposed for formal acceptance in
[DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md).

## Time domains

```text
Authoritative semantic source set
      |
      v
[1] Resolve source set and compile a per-build semantic graph snapshot
      |
      v
Runtime avatar package
      |
      v
[2] Real-time game simulation
      |
      v
[3] Optional cinematic or offline enhancement
```

## Creature compilation

Resolution and compilation may run in an external tool, character creator, loading screen,
background worker, or import step. Candidate work includes:

- resolving and validating the source set into a per-build semantic body graph
  snapshot;
- combining body volumes and extracting a surface;
- remeshing, simplifying, and generating LODs;
- generating skeletons, skinning, collision, and distance fields;
- constructing deformation cages and regional simulation meshes;
- binding simulation output to render surfaces;
- generating material attributes and GPU resources;
- running pose, geometry, collision, and capability tests.

The result is a derived runtime avatar package with separate artifact/build
identity and provenance. Invariant compilation work must not be repeated every
frame; the runtime mutation and recompilation boundary remains unresolved.

## Real-time simulation

The runtime may perform bounded stateful work:

- animation, root motion, retargeting, motion warping, and IK;
- analytic or signed-distance contact queries;
- contact constraints, balance, and physical reaction;
- bone, morph, cage, and GPU surface deformation;
- procedural material evaluation;
- selected cloth, secondary motion, and regional soft-body simulation.

Resolution, solver iterations, active regions, and character count require
explicit budgets.

## Baked and dynamic data

| Compiled | Dynamic |
| --- | --- |
| Mesh connectivity and LODs | Poses and IK targets |
| Skin weights | Contacts and forces |
| Collision fields and proxies | Constraint state |
| Deformation cages and bindings | Cage offsets and morph weights |
| Regional simulation topology | Low-resolution solver state |
| Semantic surface attributes | Interaction and material parameters |

Precomputation does not predetermine interaction. It prepares bounded numerical
representations for live use.

## Runtime mutation boundary (unresolved)

No contract is settled for runtime semantic mutation, recompilation, or swapping
derived packages. Future work must determine which authored changes can update
an active build, which require a new compilation, and how runtime state is
handled. DR-0002 does not answer those questions.

## Local quality activation

```text
Distant character
    -> animation and basic IK

Nearby character
    -> contact collision and cage deformation

Actively interacting region
    -> higher-quality local deformation
    -> optional regional soft-body simulation
```

Quality may vary by character, body region, interaction, visibility, distance,
and hardware budget.

## Provisional feasibility classification

This is an expectation to test, not benchmark evidence.

| Feature | Expected path |
| --- | --- |
| Skeletal animation, IK, and motion warping | Real time |
| Analytic collision and distance queries | Real time |
| Morph, bone, cage, and GPU surface deformation | Real time |
| Procedural colours and markings | Real time |
| Simplified cloth and secondary motion | Real time |
| Local low-resolution soft regions | High-end real time, subject to proof |
| Several interacting soft regions | Strictly budgeted, subject to proof |
| Whole-character volumetric simulation | Difficult |
| Multiple high-resolution soft characters | Primarily offline or reduced quality |
| Surface remeshing during interaction | Background or authoring work |
| Arbitrary topology change every frame | Out of scope |
| Dense two-way soft-body self-collision | Primarily cinematic or offline |

## Offline-only failure boundary

The runtime becomes impractical if it simultaneously requires render-resolution
physics, full volumetric characters, dense two-way self-collision, arbitrary
topology mutation, dense fur and cloth collision, unbounded convergence, and no
fallback or LOD. High-end hardware increases the budget but does not remove the
need for bounds.

## Pending decisions

- Reference frame rate, resolution, and hardware.
- Compile-time budget and allowed execution locations.
- Visible, nearby, and actively interacting character counts.
- Maximum high-quality deformable regions.
- GPU-vendor and backend requirements.
- Deterministic replay or networking requirements.
- Collision ownership after visible deformation.
- Minimum fallback experience.
- Relationship between live and cinematic outputs.

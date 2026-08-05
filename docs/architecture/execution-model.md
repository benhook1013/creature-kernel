# Execution model

Status: Active conceptual baseline

## Decision direction

A real-time game is the primary downstream target. Expensive creature generation
may occur outside the frame loop, while the compiled avatar exposes bounded
runtime representations. A higher-quality cinematic path is supplementary.

This direction is proposed for formal acceptance in
[ADR-0003](decisions/ADR-0003-real-time-first-compiled-avatar-boundary.md).

## Time domains

```text
Body document
      |
      v
[1] Creature compilation
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

Compilation may run in an external tool, character creator, loading screen,
background worker, or import step. Candidate work includes:

- resolving and validating the body graph;
- combining body volumes and extracting a surface;
- remeshing, simplifying, and generating LODs;
- generating skeletons, skinning, collision, and distance fields;
- constructing deformation cages and regional simulation meshes;
- binding simulation output to render surfaces;
- generating material attributes and GPU resources;
- running pose, geometry, collision, and capability tests.

The result is a stable runtime avatar package. Invariant compilation work must
not be repeated every frame.

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

## Runtime mutation boundary

- Proportion, colour, material, and some shape changes may preserve topology and
  update through bones, fields, cages, or morphs.
- Adding or removing limbs, replacing major modules, or changing body plans may
  require recompilation.
- A future runtime may compile topology-changing edits asynchronously and swap
  packages at a safe boundary.

The first-version mutation boundary remains unresolved.

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

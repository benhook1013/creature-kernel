# Programmatic root-complex surface

Status: frozen candidate-local trial contract; unregistered exploratory
pre-Readiness-4 work. Lifecycle `planned`; evidence closure `open`; technology
outcome `none`.

This record is an experiment, not product, specification, architecture, or
formal surface-comparison authority. It is not `EXP-0001`, does not claim
formal support or reject, and cannot satisfy Stage 1 or select a production
representation.

## Purpose and scope

The question is the standard-neutral directional root-complex continuation
question from the Active runway: can one programmatic surface-domain and
subdivision-cage route produce a credible ribcage-waist-pelvis assembly with
readable neck, axilla, and hip/thigh-root boundaries? Exact-five expansion is
allowed only after credible main-thread inspection of the neutral result. This
is not Stage 1 and is not production.

The bounded scope is the ribcage, waist, pelvis, neck port, bilateral
shoulder/axilla roots, and bilateral hip/thigh roots. The initial
`standard_neutral_reference` has exactly five open anatomy ports: neck, two
arms, and two thighs. A standard-profile tail-present/tail-absent subcase and
the exact-five profile set may be added later within the same PR, only after
neutral viability; the tail subcase keeps the core outside its local port
unchanged and adds no absent-tail identities.

The governing research context is [the investigation plan](../../docs/research/programmatic-root-complex-surface-investigation.md),
and human visual appraisal follows the [visual-quality evaluation
protocol](../../docs/research/visual-quality-evaluation.md).

## Programmatic admission and ownership

The admission gate accepts only source-derived scalar dimensions or
measurements, rigid frames, individually named landmarks, section stations
with scalar width/depth/offset/taper/squareness, module state, and provenance.
The prepared input is capped at 8 frames, 24 landmarks, 10 stations, and 6
scalars per station. Every numeric value carries source provenance or a
deterministic derivation.

The following are forbidden inputs: cage or mesh vertices, faces, edges, rings,
or connectivity; ordered perimeter samples; point clouds, fields, masks, or
silhouettes; corrective offsets; serialized old output; and any data trivially
reindexed into cage coordinates. In particular, a fixture may not supply a
finished cage, layout, or final shape.

The program owns topology, ring and branch cardinality, seam correspondence,
extraordinary placement, every coordinate, subdivision, and rendering. Every
cage control records one shared formula ID and its prepared-control and
provenance IDs. No complete position may come from literal 3D constants.
Geometry functions cannot receive or read a profile ID; profile identity may
select admitted data and provenance only.

## Selected topology hypothesis

The experiment uses one profile-independent symbolic topology:

- six ordered octagonal axial rings named `neck_collar`,
  `upper_ribcage_shoulder`, `lower_ribcage`, `waist_abdomen`,
  `iliac_overlap`, and `lower_pelvis`;
- bilateral four-control shoulder collars; and
- one fixed pair-of-pants pelvic macro leading to bilateral four-control thigh
  ports.

The macro is reflection-symmetric. With lower-pelvis controls `P0..P7` equal
to ring indices `0..7`, its left route is `P2,P3,P4,P5,P6` with cuff
`Lm,Lf,Ll,Lb,Lm`, its right route is `P2,P1,P0,P7,P6` with cuff
`Rm,Rf,Rl,Rb,Rm`, and its central saddle is `P2,Lm,P6,Rm`. Each cuff remains
ordered medial, front, lateral, back. This candidate therefore has exactly
`V=64`, `E=122`, `F=55`, 24 boundary edges, Euler `-3`, and valence inventory
`((3,22),(4,32),(5,10))`.

The induced directed boundary loops are `neck=(0,1,2,3,4,5,6,7)`,
`left_arm=(48,51,50,49)`, `right_arm=(52,55,54,53)`,
`left_thigh=(56,59,58,57)`, and `right_thigh=(60,61,62,63)`.

The initial caps are 64 cage controls and 96 base quads. Extraordinary
controls must have only the declared valences 3 through 6. The symbolic
topology preflight must prove connected manifold and boundary facts and
Euler's relation before any anatomy coordinates are admitted. If the proposed
count or pelvic macro cannot meet the proof, stop and revise this candidate
record before rendering.

## Shared coordinate formulas

All formulas are shared across sides, regions, and profiles. Initial constants
and frozen exploratory ranges are:

| Formula constant | Initial value | Frozen range |
| --- | ---: | ---: |
| asymmetric-superellipse power `n` | 2.6 | [2.0, 3.2] |
| iliac-overlap blend `lambda` | 0.25 | [0.0, 0.5] |
| shoulder-peak outward factor | 1.0 | [0.8, 1.2] |
| axilla outward factor | 0.55 | [0.35, 0.75] |
| thigh-seat route fraction `eta` | 0.25 | [0.0, 0.5] |
| medial-gap factor `gamma` | 0.08 | [0.04, 0.12] |

The section coordinates use source-derived asymmetric superellipses with the
visible shared power `n`. The iliac overlap uses the shared `lambda` blend.
Shoulder peak and axilla are the upper- and lower-collar centres with shared
factors, never separate profile branches. The thigh seat is derived along the
authored start-to-mid route using shared `eta`; medial separation uses shared
`gamma`. Every other constant must be finite, range-frozen before use, shared
rather than profile data, and count toward the 32 shared-scalar-tunable cap.

For station centre `C`, lateral axis `L`, forward axis `F`, lateral radius
`a`, front extent `f`, back extent `b`, and fixed angle `theta`, the shared
section formula is:

```text
C_depth = C + ((f - b) / 2) F
d = (f + b) / 2
P(theta) = C_depth
  + a sign(cos(theta)) |cos(theta)|^(2/n) L
  + d sign(sin(theta)) |sin(theta)|^(2/n) F
```

The six axial rings use the same fixed eight angles. `iliac_overlap` blends
the source lower-abdomen and upper-pelvis centres and radii by `lambda`.
Shoulder-collar upper and lower pairs derive from the source shoulder-peak and
axilla landmarks plus source arm-root extents and the two shared outward
factors. With `T = normalize(thigh_mid - thigh_start)`, the thigh seat is
`thigh_start + eta * length(thigh_mid - thigh_start) * T`. The medial radius
is clamped only by the shared minimum gap `gamma * lower_pelvis_lateral_radius`;
a non-positive admissible radius rejects the input rather than changing
topology or invoking repair.

The trial scale `S` is the distance from the neck-port centroid to the midpoint
of the two thigh-port centroids and must be finite and greater than zero. The
right-handed frame is +Y up, +X subject-right, and +Z forward. Canonical
anatomical left is therefore `-L/-X` and right is `+L/+X`.

## Checkpoint correctness

The initial neutral checkpoint has `b = 5` declared boundary loops. At the
cage, one-level diagnostic, and two-level checkpoint, require one connected,
orientable quad 2-manifold with exactly the declared simple boundary loops,
finite values, consistent winding, and
`V - E + F = 2 - b` (therefore `-3` for the initial neutral). Also require
every edge length to exceed `1e-8 S`, every face area to exceed `1e-10 S^2`,
and only the declared extraordinary valences.

Use one fixed open-boundary Catmull-Clark rule and exactly two subdivision
levels for the checkpoint; retain cage and one-level diagnostics. The
evaluated surface must remain finite, connected, manifold, and carry the same
declared ports. Its triangulated validation requires triangle area greater
than `1e-12 S^2` and a bounded, fail-closed check for non-adjacent
self-intersection. Render-only movement is forbidden, and diagnostic caps are
never judged as anatomy.

The welded shared topology supplies C0 continuity. Report normal-angle and
fold behavior, but do not claim mathematical C1 or G1 continuity at
extraordinary vertices or open ports.

## Determinism and causality

The checkpoint determinism gate runs two fresh launcher processes with
different `PYTHONHASHSEED` values in the same pinned environment. The prepared
record, cage and evaluated PLY, dependency and metrics manifests, and
metadata-free PNG must be byte-identical. Paths and timestamps are excluded
from identity.

For causality, perturb admitted prepared controls and regenerate every output.
Topology, IDs, and formula IDs must remain unchanged. Every generated control
must depend on admitted prepared data. Geometry outside the declared formula
dependency closure must be bit-identical, and evaluated geometry outside the
affected subdivision stencil must be unchanged. There may be no profile-ID
branch and no direct override. Effect-magnitude and locality numbers are
exploratory screens, not aesthetic passes.

On evaluated skin, use profile-independent landmark probe formulas for the
following exploratory negative-space screens: neck `>= 0.030 S`, axilla
`>= 0.025 S`, groin `>= 0.020 S`, and medial thigh `>= 0.025 S`. Human vision
remains authoritative for whether those spaces read anatomically.

## Human evidence

For the neutral orientation screen, render direct skin from fixed front, side,
and three-quarter views at the same scale and framing as the frozen failed
baseline. Main-thread model vision assesses distinct ribcage/waist/pelvis, neck emergence,
shoulder/axilla, iliac/hip transition, seated thighs, medial separation, and
the absence of primitive blobs, seams, or collapse. Record scoped observations
and uncertainty; do not create an aggregate aesthetic score. This internal
screen only decides whether unchanged-rule exact-five expansion is worth
running; it is not human acceptance.

After the exact-five evidence and required technical gates exist, present the
fixed front, side, and three-quarter final-skin renders to Ben for the named
directional root-complex continuation checkpoint. Ben judges whether the
representation is credible enough to extend. No internal vision result or
numeric score substitutes for that human judgment.

## Complexity boundary and correction stop

Before any gallery work, use only the existing pinned NumPy/Pillow environment;
add no dependency. The hard caps are at most 700 non-test Python LOC, 600 test
LOC, 7 Python files, 64 controls, 96 base quads, two subdivision levels, 12
coordinate-formula functions, and 32 shared scalar tunables. The construction
has one axial template, one bilateral branch-root construction pattern, and
one pelvic macro. It may not add profile-ID geometry branches or
profile-shaped coordinate tables, a generic
framework, optimizer, remesher, field composition, hidden second skin,
post-generation edits, or a gallery before viable geometry.

Allow at most three shared correction rounds, matching the current runway. One
round is one coherent, review-triggered change to already-declared shared
formulas or tunables, applied identically to every relevant side, region, and
profile, followed by full regeneration and inspection. A round cannot change
topology, add formula functions or inputs, relax a gate, branch by profile, or
edit rendered vertices. Such a change starts a newly recorded candidate; it
must not be silently counted as tuning. Stop after three rounds without a
credible neutral root complex.

## Build order

1. Freeze this contract.
2. Prepare the neutral projection.
3. Run symbolic topology preflight.
4. Derive formula coordinates.
5. Apply Catmull-Clark.
6. Render direct cage, one-level, and two-level diagnostics/skin.
7. Stop for main-thread vision inspection.
8. Expand to exact-five only if neutral geometry is credible, using unchanged
   rules.
9. Add only the necessary causality, intersection, and clearance validators.
10. Run static rejection probes.
11. Add the thin gallery adapter last.
12. Present the exact-five evidence to Ben for the named checkpoint.

## Reproduction and outputs

All trial commands use [the root-complex launcher](root_complex_launcher.sh),
which delegates interpreter, pinned-environment, and temporary-root selection
to the current-form preview launcher. There is no bare-Python fallback. Keep
generated outputs in `/tmp` or the approved cache, never in Git. The initial
neutral output set is expected to contain `skin.ply`, `skin.png`, `cage.png`,
`metrics.json`, and `manifest.json`; large artifacts remain uncommitted.

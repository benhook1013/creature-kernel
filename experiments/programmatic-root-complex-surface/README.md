# Programmatic root-complex surface

Status: finished candidate-local trial; unregistered exploratory pre-Readiness-4
work. Lifecycle `finished`; evidence closure `incomplete` because neutral vision
stopped the trial before exact-five evidence and later probes; technology
outcome `none`.

This record is an experiment, not product, specification, architecture, or
formal surface-comparison authority. It is not `EXP-0001`, does not claim
formal support or reject, and cannot satisfy Stage 1 or select a production
representation.

Candidate-evolution ledger (experiment-local; not accepted architecture):

1. The initial six-ring prototype was invalidated before viability because of
   canonical left/right reversal and twisted/asymmetric pelvis correspondence.
2. The symmetric six-ring successor (64 controls, 55 quads) fixed those
   defects, but canonical rendering exposed the lower-ribcage/axilla ownership
   mismatch and it was rejected.
3. The current seven-ring successor (72 controls, 63 quads) adds the derived
   axilla-transition ring; correction round 1 moves the shared shoulder/axilla
   socket-and-collar centre formula toward the authored shoulder and axilla
   landmarks and adds the bounded geometry-correctness gate. Correction round
   2 adds the shared axial min-envelope described below; it improves taper and
   thigh seating but does not establish neutral credibility or exact-five
   readiness. Correction round 3 is the terminal shared superior axial saddle
   described below. Main-thread vision found that its final neutral render does
   not show unmistakable neck emergence, downward shoulder departure, and arm
   ports below it. Exact-five is therefore blocked for this seven-ring candidate,
   the scoped trial stops here, and there is no fourth correction round. This is
   not a formal Stage-1 or global representation rejection.

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
arms, and two thighs. The following pre-terminal continuation plan is retained
for historical reference only and is superseded by the terminal outcome above:
a standard-profile tail-present/tail-absent subcase and the exact-five profile
set could have been added within the same PR after neutral viability; the tail
subcase would keep the core outside its local port unchanged and add no
absent-tail identities.

The governing research context is [the investigation plan](../../docs/research/programmatic-root-complex-surface-investigation.md),
and human visual appraisal follows the [visual-quality evaluation
protocol](../../docs/research/visual-quality-evaluation.md).

## Programmatic admission and ownership

The admission gate accepts only source-derived scalar dimensions or
measurements, rigid frames, individually named landmarks, section stations
with scalar width/depth/offset/taper/squareness, module state, and provenance.
The prepared input is capped at 8 frames, 24 landmarks, 10 stations, and 6
scalars per station. Every numeric value carries source provenance or a
deterministic derivation. The four scalar records emitted by the frozen
projection and the seven declared shared formula-constant override names are
the complete accepted scalar-name set.

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

- seven ordered octagonal axial rings named `neck_collar`,
  `upper_ribcage_shoulder`, `axilla_transition`, `lower_ribcage`,
  `waist_abdomen`, `iliac_overlap`, and `lower_pelvis`;
- bilateral four-control shoulder collars; and
- one fixed pair-of-pants pelvic macro leading to bilateral four-control thigh
  ports.

The macro is reflection-symmetric. With lower-pelvis controls `P0..P7` equal
to ring-6 indices `48..55`, its left route is `P2,P3,P4,P5,P6` with cuff
`Lm,Lf,Ll,Lb,Lm`, its right route is `P2,P1,P0,P7,P6` with cuff
`Rm,Rf,Rl,Rb,Rm`, and its central saddle is `P2,Lm,P6,Rm`. Each cuff remains
stored as medial, front, lateral, back; its directed boundary loop follows
the oriented surface. This candidate therefore has exactly `V=72`, `E=138`,
`F=63`, 24 boundary edges, Euler `-3`, and valence inventory
`((3,22),(4,40),(5,10))`.

The induced directed boundary loops are `neck=(0,1,2,3,4,5,6,7)`,
`left_arm=(56,59,58,57)`, `right_arm=(60,63,62,61)`,
`left_thigh=(64,67,66,65)`, and `right_thigh=(68,69,70,71)`.

The frozen complexity cap permits at most 72 cage controls and 96 base quads;
this candidate uses 72 cage controls and 63 base quads as stated above.
Extraordinary controls must have only the declared valences 3 through 6. The
symbolic topology preflight must prove connected manifold and boundary facts
and Euler's relation before any anatomy coordinates are admitted. If the
proposed count or pelvic macro cannot meet the proof, stop and revise this
candidate record before rendering.

## Shared coordinate formulas

All formulas are shared across sides, regions, and profiles. Initial constants
and frozen exploratory ranges are:

| Formula constant | Initial value | Frozen range |
| --- | ---: | ---: |
| asymmetric-superellipse power `n` | 2.6 | [2.0, 3.2] |
| iliac-overlap blend `lambda` | 0.25 | [0.0, 0.5] |
| shoulder interpolation factor `sigma` | 0.80 | [0.70, 1.00] |
| axilla outward factor | 0.55 | [0.35, 0.75] |
| thigh-seat route fraction `eta` | 0.25 | [0.0, 0.5] |
| medial-gap factor `gamma` | 0.08 | [0.04, 0.12] |
| superior axial saddle `saddle` | 0.45 | [0.30, 0.60] |

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

The seven axial rings use the same fixed eight angles. `iliac_overlap` blends
the source lower-abdomen and upper-pelvis centres and radii by `lambda`.
`axilla_transition` is derived between the lower- and upper-ribcage station
records. Let `U` be the body up axis, let `target` be the mean of the
projections of `axilla_left` and `axilla_right` onto `U`, and let
`t = (target - dot(lower.center,U)) /
dot(upper.center - lower.center,U)`. The input is rejected unless `t` is
finite and strictly between zero and one. Its centre and each of its three
extents are `(1-t)*lower + t*upper`; its controls depend explicitly on both
axilla landmarks, both station records, and the body frame. The shoulder holes
now connect the upper-ribcage and transition rings at segment 3 on the left
and segment 0 on the right. Shoulder-collar upper and lower pairs derive from
the source shoulder-peak and axilla landmarks plus source arm-root extents and
the two shared outward factors. In correction round 1, for side sign `s`
(`-1` left, `+1` right), the shared formula uses `sigma` as follows:

```text
upper_center = axilla + sigma * (shoulder_peak - axilla)
               + s * sigma * arm_root_outward * L
lower_center = axilla + s * axilla_factor * arm_root_outward * L
```

The upper-ribcage and axilla-transition torso socket controls retain their
station subject-side lateral anchor while replacing their up/forward
coordinates with the corresponding centre and `+/- arm_root_depth * F`.
They use the same `shoulder.peak_axilla_collar` formula family as the collars,
with station, landmark, arm-root, factor, and frame dependencies. This
correction responds to the measured shoulder intersections by making each
socket-to-collar bridge a direct lateral correspondence rather than a long
diagonal into a generic ribcage ring. The bilateral thigh seats are
`seat_side = thigh_start_side + eta * (thigh_mid_side - thigh_start_side)`.
The medial radius is clamped only by the shared minimum gap
`gamma * lower_pelvis_lateral_radius`; a non-positive admissible radius rejects
the input rather than changing topology or invoking repair.

Correction round 2 derives one shared, profile-neutral axial min-envelope. Its
seat anchor uses the mean seat projection on `U`, lateral extent
`max(abs(dot(seat_left,L)), abs(dot(seat_right,L))) + thigh_lateral_radius`,
and equal front/back extents `thigh_depth`. Together with the source upper-rib,
waist, and upper-pelvis centres and extents, these form strictly descending
anchors `(u_high,E_high)` through `(u_low,E_low)`. For the first descending
segment containing station position `u`, the exact interpolation is:

```text
q = (u - u_low) / (u_high - u_low)
E_envelope(u) = E_low + q * (E_high - E_low)
E_output(u) = componentwise_min(E_authored(u), E_envelope(u))
```

The envelope anchors `upper_ribcage_shoulder`, `waist_abdomen`, and
`upper_pelvis` remain authored stations with unchanged formula, dependencies,
provenance, and geometry. Clamp candidates are exactly `lower_ribcage`,
`lower_abdomen`, and `lower_pelvis`; station centres, the seven-ring topology,
and `neck_collar` remain unchanged. A candidate records the min-clamp formula
and envelope causality only when at least one envelope component wins or ties.
At an exact interpolation boundary, only the non-zero-weight anchor is a
dependency; when every authored component wins strictly, the station remains
authored and records no envelope dependency. Thus only actually clamped direct
rings receive `station.axial_envelope.min_clamp`; `axilla_transition` and
`iliac_overlap` inherit causality from any clamped source stations they use.
Each clamped control records its authored station, only the contributing
interpolation-boundary station or seat anchors, every bilateral thigh landmark
and radius/depth/`eta` scalar where the seat boundary contributes, and the body
frame with actual provenance. There is no post-generation override, profile
branch, render displacement, new prepared field, topology change, optimizer,
field, repair, or relaxed validation.

Correction round 3 is the terminal shared superior axial saddle. It applies
only to the four non-socket upper-ribcage controls `10, 13, 14, 15`; the direct
shoulder socket controls, collars, neck ring, centres, axial envelope, topology,
and every other control remain unchanged. For each affected control, first
compute the ordinary section point `P_base`, then use the upper station centre
`C_upper`, its lateral radius `a_upper`, the neck centre `C_neck`, and the body
axes:

```text
r = clamp(abs(dot(P_base - C_upper, L)) / a_upper, 0, 1)
w = 1 - r
P_output = P_base + saddle * w * dot(C_neck - C_upper, U) * U
```

The input is rejected when the neck-above-upper separation
`dot(C_neck - C_upper, U)` is non-finite or non-positive; it is never repaired
or clamped. Saddle controls use formula ID
`shoulder.superior_axial_saddle` and exactly the upper station fields, neck
centre, body frame, `n`, and `saddle` in their dependencies and provenance.
The falsifiable visual criterion was that fixed front, side, and three-quarter
renders show unmistakable neck emergence, a downward shoulder departure, and
arm ports visibly below that departure. Main-thread vision did not see those
three cues unmistakably in the final round-3 neutral render. The seven-ring
candidate therefore fails this scoped continuation criterion: exact-five is
blocked, this trial stops, and there is no fourth correction. This result does
not establish a formal Stage-1 or global representation rejection.

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

On every evaluated subdivision level, run the bounded non-adjacent triangle
intersection validator and fail closed for any contact or overlap; the
checkpoint records the individual intersection count for each level. On final
level two only, use these profile-independent landmark probe formulas, with
the listed scale-relative thresholds:

- neck: `min(span_L(neck), span_F(neck)) >= 0.030 S`;
- each axilla: `min(span_U(arm), span_F(arm)) >= 0.025 S`;
- groin: signed `L` separation of the first right and left thigh samples
  `>= 0.020 S`; and
- medial thigh: minimum signed `L` separation across right-versus-left thigh
  loop samples `>= 0.025 S`.

Store and report the five ratios independently; there is no aggregate score.
Human vision remains authoritative for whether those spaces read anatomically.

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
add no dependency. The narrow apparatus amendment for this correction is at
most 975 non-test Python LOC, 775 test LOC, 8 Python files, and 170 non-test
LOC in `mesh_correctness.py`. All geometry, topology, tunable, subdivision,
and correction-round gates remain: 72 controls, 96 base quads, two subdivision
levels, 12 coordinate-formula functions, and 32 shared scalar tunables. The construction
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

## Historical build order (superseded by terminal outcome)

The following pre-terminal build order is retained for reproduction and audit
context only; it is not current continuation after the terminal outcome above.

1. Freeze this contract.
2. Prepare the neutral projection.
3. Run symbolic topology preflight.
4. Derive formula coordinates.
5. Apply Catmull-Clark.
6. Render direct cage, one-level, and two-level diagnostics/skin.
7. Run the bounded intersection checks at levels one and two and the final
   level-two clearance gates.
8. Stop for main-thread vision inspection.
9. Expand to exact-five only if neutral geometry is credible, using unchanged
   rules.
10. Run static rejection probes and retain causality evidence.
11. Add the thin gallery adapter last.
12. Present the exact-five evidence to Ben for the named checkpoint.

## Reproduction and outputs

All trial commands use [the root-complex launcher](root_complex_launcher.sh),
which delegates interpreter, pinned-environment, and temporary-root selection
to the current-form preview launcher. There is no bare-Python fallback. Keep
generated outputs in `/tmp` or the approved cache, never in Git. The initial
neutral output set is expected to contain `prepared.json`, `skin.ply`,
`skin.png`, `cage.png`, `metrics.json`, and `manifest.json`; large artifacts
remain uncommitted. Metrics report the per-level intersection counts, a clear
zero-intersection status, and the five final clearance ratios individually.

From the repository root, copy-paste this standard-neutral build command:

```bash
OUTPUT_DIR="$(mktemp -d /tmp/ck-root-complex.XXXXXX)/standard-neutral" && \
experiments/programmatic-root-complex-surface/root_complex_launcher.sh \
  experiments/programmatic-root-complex-surface/build_root_complex.py \
  examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  "$OUTPUT_DIR"
```

`OUTPUT_DIR` must not exist before the command; the builder creates it and
fails closed if the target already exists or appears during the build.

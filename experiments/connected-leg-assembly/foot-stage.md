# Connected-leg foot stage

Status: FOOT-001 static mechanical success; anthro flipper rejected at L2;
shared refinement authorized; internal prerequisite only

This bounded stage adds one common coarse foot construction to the existing
expanded leg L0. It is not final anatomy, a species contract, a general rig,
or the named Ben checkpoint. The current 005 capture and its immutable root
sources are outside this stage and must not be edited.

## Frozen original candidate and budget

The finite budget for the original candidate was recorded before any foot
geometry execution:

- Initial candidates: exactly 1.
- Shared construction correction: at most 1, only if the initial evidence
  identifies a shared defect and the correction is justified by that evidence.
- Per-case repair, input retuning, alternate construction, repeated review
  cycles, and budget carry-over are forbidden.

The initial candidate is a connected 3x3-perimeter cage using this semantic
order for its dorsal and plantar perimeter:

```text
D0 heel-left, D1 ball-left, D2 toe-left, D3 toe-centre,
D4 toe-right, D5 ball-right, D6 heel-right, D7 heel-centre
```

The existing ordered eight-vertex ankle loop `A` is reused. The candidate
creates `C = lerp(A, D, collar_fraction)` with `collar_fraction = 0.20`, then
connects `A -> C -> D -> P` with eight quad bands per transition. `P0..P7`
reuse the footprint outline and `P8` is the ball-centre. The plantar cap uses
these semantic quad groups, reversing all face winding when required by the
attached ankle-loop orientation:

```text
P0 P1 P8 P7
P1 P2 P3 P8
P8 P3 P4 P5
P7 P8 P5 P6
```

The attached ankle loop's actual cyclic phase and winding are resolved from
its source ankle frame and projected positions. `A0..A7` are never assumed to
mean `D0..D7`. The chosen phase, direction, projected score, frame, source
anchors, ring indices, cap indices, and face-owner ranges are retained in
metadata.

## Inputs and common construction

`foot-inputs.json` contains only the two existing connected-leg cases and
mirrored left/right controls. The foot centreline is not given an authored x:
each side uses `leg_inputs[side].A[0]`. `A` remains the ankle endpoint, not the
heel. The generic source anchors are `H`, `B`, and `T`; the simple footprint
requires `H.z < A.z < B.z < T.z`, and ball width must exceed the measured
ankle-loop lateral half-width. Human-like and raised-heel contrasts are values
of these generic controls, not code branches or species names.

The output preserves the expanded-leg vertices and faces as exact prefixes,
removes only the two ankle boundary declarations, and leaves the neck and two
arm ports as the only boundaries. The new foot is closed by the plantar cap.
No weights are introduced here; later foot vertices inherit corresponding
shank influence and this stage makes no ankle-articulation claim.

The evaluator delegates to the current generic Catmull--Clark evaluator for
zero, one, or two levels. It is not changed or copied. The old ankle loop is
expected to become interior and move under subdivision.

## Rejection gates and limitations

The construction rejects non-finite or malformed inputs, invalid source
relationships, phase ambiguity, folded collar quads, footprint or 3D
self-intersection, degenerate faces, non-manifold or disconnected output,
prefix/topology regression, and any failure to close the ankle boundary. The
former bespoke 3D triangle/AABB check was limited: it could miss a second
triangle and skip the shared one. It has been replaced by the stronger frozen
intersection checker; the replacement is checker-only and does not authorize
or apply any geometry correction. Projected nesting alone is not accepted as
proof of separation.

Direct visual rejection remains required for a future bounded appraisal:
cuff fold, self-intersection, disconnected foot, erased heel or paw mass,
rigid-shoe-like bulb, or limb regression. No full collision, pose, render,
contact, ground-pin, gait, or final-anatomy claim is made here.

## Initial evidence command

The bounded managed-runtime command is:

```bash
PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python bash /home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/current-form-surface-preview/surface_preview_launcher.sh -m unittest discover -s experiments/connected-leg-assembly/tests -p test_foot_construction.py -v
```

The tests include the fresh two-case L0 construction/evaluation for counts,
manifold closure, winding, correspondence, and meaningful source anchors.
They do not run a body capture or pose/collision protocol.

## Initial candidate evidence

The initial candidate was executed once for each canonical existing case in
memory. Both produced a 314-vertex/304-quad connected L0 with 25 new vertices
and 28 new faces per side, then passed delegated zero-, one-, and two-level
generic Catmull--Clark evaluation. The managed test command completed with 9
tests passed and no failures or errors.

The tests also exercised a cyclic phase shift and a reversed attached ankle
loop, confirming that correspondence and output winding are derived from the
actual source loop rather than an `A0..A7` assumption. This is implementation
evidence for the bounded candidate only; no pose, render, full collision, or
anatomy acceptance was run. The remaining risks are the angled-ankle 3D fold
and intersection envelope under future visual inspection, and whether the
coarse closed cage reads as a heel/forefoot rather than a rigid shoe-like
bulb.

## FOOT-001 appraisal and next bounded refinement

FOOT-001 achieved static mechanical success. Main's direct L2 visual appraisal
rejected the anthropomorphic flipper; the human coarse wedge was adequate for
this narrow stage. Neither is polished anatomy acceptance. The original shared
winding correction remains consumed and the remaining geometry budget is `0`.

The Overseer separately authorized one shared forefoot-support refinement with
fixed H/B/T positions, widths, thicknesses, collar, and legs; it may alter only
local foot-support topology or interpolation. The budget is one candidate and
at most one evidence-justified shared adjustment. Its narrow goal is a raised
transition into a low, broad, finite-thickness forefoot while retaining the
elevated heel. No detailed toes, species branch, or input retune is authorized.
Linnaeus is diagnosing the actual sections before a concrete hypothesis.

## Correction ledger and provenance

The initial candidate's first managed test invocation failed during
`setUpClass`, before any test body ran. The original tool output is preserved
verbatim:

```text
ERROR

======================================================================
ERROR: setUpClass (test_foot_construction.FootConstructionTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 795, in build
    _validate_output(output, base_mesh, base_vertex_count, base_face_count,
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 626, in _validate_output
    _validate_topology(vertices, quads, loops, "output")
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 169, in _validate_topology
    _fail(f"{where} has an orientation conflict")
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 40, in _fail
    raise FootConstructionError(message)
foot_construction.FootConstructionError: output has an orientation conflict

----------------------------------------------------------------------
Ran 0 tests in 0.011s

FAILED (errors=1)
```

The measured cause was the shared perimeter orientation between the D-to-P
band and the plantar cap. The one shared correction reversed all four
plantar-cap face windings for output orientation `+1`, while retaining the
semantic cap groups; the inverse rule remains used for reverse output
orientation. The known source delta was:

```diff
-return faces if orientation == 1 else [tuple(reversed(face)) for face in faces]
+# The D->P band uses the P perimeter in ``orientation`` direction.  The
+# closed plantar faces must use the opposite direction on every shared
+# perimeter edge; the semantic face grouping remains unchanged.
+return [tuple(reversed(face)) for face in faces] if orientation == 1 else faces
```

The original candidate's shared geometry-correction budget is consumed:
remaining budget `0`. No further correction to that original candidate, input
retuning, or candidate substitution is authorized; this does not limit the
separately authorized shared forefoot-support refinement above. A later
evaluator-only integration fix added
`metadata["base_vertex_count"] = len(base_control_owners)` after appending
the foot owners; it changed metadata integration only, not geometry, source
points, face grouping, coordinates, or the candidate budget.

The initial pre-correction source was not immutably captured or separately
hashed. No initial-candidate provenance is inferred from the final source
identity.

## Checker status and evidence boundary

Cicero's checker-only replacement is complete. The managed validator result
was 11 tests passed, including the exact regressions
`test_frozen_core_catches_second_triangle_only_hit` and
`test_frozen_core_catches_one_shared_vertex_hit`. Exact pre/post geometry
comparison passed for both canonical cases, and complete frozen-core checking
passed for the 608-triangle L0.

The prepatch source and baseline meshes are preserved at
`/home/ben/.cache/connected-leg-foot-prepatch.1knSpc/foot_construction.py`.
The two regressions above are the recorded reason the former bespoke checker
was replaced; they do not represent geometry changes.

Sol's actual static foot-plus-leg check covered 2,688 triangles and
3,611,328 triangle pairs, with zero reported intersections. This supports a
static capture only; it is not a full-body pass and is not immutable-capture
evidence. The stronger checker is ready for Raman's static capture; no foot
render is authorized until that capture provides a new snapshot.

The geometry candidate is unchanged and the correction budget remains zero:
this update changed only this stage record, with no construction, input, test,
capture, render, or geometry run. The unchanged candidate-file identities are:

```text
5bb0c361e006818027ac5ff5dfe0eec713b6969ecb4ba9de809670490a3418c0  foot_construction.py
6e2d3ee26f28f80388c9ad0d4a8edef1cfbd28b5f90cc07228c295ad2c6a5dd0  foot-inputs.json
493101df145fdd1fc05d803a104b52f8e722b1fd76e4e3734b9064aabbefe6ab  tests/test_foot_construction.py
```

## FOOT-002 initial shared support candidate

This is a new, pre-execution candidate. FOOT-001 remains rejected and its
geometry-correction budget remains exhausted; this candidate has exactly one
initial execution allowance and at most one later shared,
evidence-justified adjustment. No adjustment has been spent.

The fixed H/B/T positions, widths, thicknesses, collar fraction, leg inputs,
A/C/D/P points, and existing D-to-P band are unchanged. For each side, the
new full proximal support ring is:

```text
R_i = lerp(C_i, D_i, 0.75), i=0..7, for x and z
R_i.y = source_dorsal_y(R_i.z)
```

`source_dorsal_y` is the piecewise-linear profile through
`H.plantar_y + H.dorsalthickness`, `B.plantar_y + B.dorsalthickness`, and
`T.plantar_y + T.dorsalthickness`. Any `R.z` outside the strict H..T range is
rejected; it is never clamped. The C-to-D band is replaced by matched C-to-R
and R-to-D eight-quad bands.

The plantar support uses the existing P8 point as its centre, without a
duplicate vertex. Its closed eight-vertex loop is:

```text
S_i = lerp(P_i, P8, beta_i)
beta = [.75, .20, .20, .20, .20, .20, .75, .75]
```

The unchanged P0..P7 perimeter connects to S0..S7 with eight annulus quads;
the inner loop closes with `S0S1P8S7`, `S1S2S3P8`, `P8S3S4S5`, and
`S7P8S5S6`, using the existing orientation rule. Every P edge and every S
edge has complete matching ownership; no perimeter edge is split.

The construction hypothesis is a readable low, broad, finite-thickness
forefoot with the elevated heel retained and the H-to-B rise narrowed by the
near-B rear S supports and the source-profiled R ring. The initial evidence
must measure the same exact triangle-plane sections at `z=B.z` and
`z=(H.z+B.z)/2`, reporting plantar height, dorsal height, thickness, and
halfwidth against source interpolation. This is a response measurement, not
an exact-control interpolation claim.

Acceptance/rejection criteria are: readable low broad finite-thickness
forefoot after a narrow raised transition; readable human foot; elevated heel
retained; and no cuff ridge, folds, tears, flipper, disconnected topology, or
limb regression. The initial result and images should be returned even if
rejected when the existing capture adapter can produce them. The second shape
adjustment is reserved for Main after initial surface and section inspection.

The following are separately labelled source-response counterfactuals, not
input retuning: compare the actual L2 B section after a temporary +10% B
halfwidth perturbation, and after a temporary +0.01 m heel plantar-height
perturbation. Canonical inputs and the candidate remain unchanged by those
diagnostics.

Pre-execution identities were recorded before the initial geometry run:

```text
foot_construction.py  db045ca40af84b7d9dd1402ef7c6ae2de7429ebb1987e2ab4a4b1a55230ed511
foot-inputs.json      6e2d3ee26f28f80388c9ad0d4a8edef1cfbd28b5f90cc07228c295ad2c6a5dd0
inputs.json           1fbd9448bcef2861fc61623b497e67bd2e84a1106818dcac9d84dcf04bd60bda
construction.py       199672cfb8b57d49842d63b7c1043a0a85b1129eb742dd4b0d8016f52b6b765b
foot_trial.py         94a7b1e8aaac6f659fea9bb04013ec9b741f83ecca4752334abd3aa55f4eeedc
frozen checker        4104b70e70e958a469125d1fff544e20fee44b784bf7915d8e724e63d4f39db1
runtime requirements  69a3ce10b1f993d7913f02ca187eabb8d367abf214662ffa2132feacbdeedbec
runtime               Python 3.10.12
```

The existing `foot_trial.py` adapter remains Raman-owned and will be used only
after a source snapshot containing this candidate is ready. No capture or
render is started by this subsection.

### Initial execution result

The initial candidate was run with the managed test command above. It was
rejected at L0 validation on the first canonical case, before any test body,
L2 evaluation, source snapshot, capture, or render. The exact tool output was:

```text
ERROR

======================================================================
ERROR: setUpClass (test_foot_construction.FootConstructionTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/tests/test_foot_construction.py", line 72, in setUpClass
    output = foot_construction.build(base, leg_inputs, foot_inputs)
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 916, in build
    _validate_output(output, base_mesh, base_vertex_count, base_face_count,
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 705, in _validate_output
    _validate_new_faces(vertices, quads, indices, side)
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 596, in _validate_new_faces
    _fail(f"{side} foot quad {face_index} has a cuff fold")
  File "/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor/experiments/connected-leg-assembly/foot_construction.py", line 52, in _fail
    raise FootConstructionError(message)
foot_construction.FootConstructionError: left foot quad 268 has a cuff fold

----------------------------------------------------------------------
Ran 0 tests in 4.576s

ERROR (errors=1)
```

Face 268 is the fifth semantic face of the left R-to-D band. This is an
initial-candidate rejection, not evidence for an input retune. The reserved
shared adjustment remains unused; no geometry bypass, counterfactual,
capture, render, or second shape adjustment was run.

### FOOT-002 adjusted candidate ledger

The single authorized R1..R5 forward-support adjustment was pre-captured at
`/home/ben/.cache/connected-leg-assembly-FOOT-002-adjusted-snapshot` and
executed once by this task through the static adapter, producing
`/home/ben/.cache/connected-leg-assembly-FOOT-002-adjusted-run` with exit 0.
Both canonical constructions completed. Focused tests, counterfactuals,
integrated poses, and other checks remain unrun; exit 0 is not acceptance.

The adjustment budget is now 0 and closed. Main and Overseer rejected this
candidate after reviewing the existing adjusted run and section evidence:
the human remains readable, while the anthropomorphic case is a flipper. The
focused tests, counterfactuals, integrated poses, and other checks remain
unrun; exit 0 is not acceptance. The initial fold failure and its prior
unused-budget record above remain historical candidate state. No trial restart
or further correction is authorized for FOOT-002.

### FOOT-003 longitudinal-grid implementation record

Hypothesis/layout: use one shared closed longitudinal dorsal/plantar grid per
side with rows H, midpoint(H,A.z), A.z, A.z+0.25(B.z-A.z),
A.z+0.625(B.z-A.z), B, midpoint(B,T), T and lateral fractions
[-1,-.65,0,.65,1]. The H-to-B half-width uses the declared u^2
interpolation; B-to-T is linear. The dorsal surface omits only the four
central quads around the unused centre at A, leaving an eight-vertex ankle
hole. The grid closes its two side strips and heel/toe end strips (22 outer
perimeter quads), then attaches the actual ankle loop through the unchanged
collar_fraction=.20 with two eight-quad bands.

Source roles remain explicit: H and B/T are fixed source controls, A supplies
ankle-z attachment context, and derived row fractions are construction
hypotheses rather than anatomy. The implementation preserves the L0 prefix,
retained neck/arm ports, and explicit per-side new vertex/face indices,
source anchors, attachment loop, phase, and winding metadata. Inputs are
unchanged; FOOT-001 and FOOT-002 snapshots and reports are preserved.

Single-review outcome: the requested FOOT-003 preflight approved this layout
for implementation. Risks retained for execution review are tilted-ankle
phase/winding and collar-band folds, dorsal-hole degeneracy, source-profile
height/width response, heel/body collision, and whether the fixed coarse
controls read as a low broad forefoot in both cases. Generic evaluation,
validation, and the frozen collision component are reused; this record makes
no acceptance claim.

### FOOT-003 first-candidate status

The first FOOT-003 candidate mechanically built and its focused tests passed.
Main personally inspected the saved result: the anthropomorphic foot remains a
thin, sloping flipper and is not accepted. One shared correction remains
unused; read-only diagnosis is underway. No trial restart or anatomy
acceptance is claimed, and frozen evidence remains unchanged.

Budget: one initial candidate plus at most one shared correction; this is the
initial candidate and zero corrections have been spent. Raman remains the
sole capture/test/execution owner; the first candidate's saved evidence is
preserved. No trial restart, further correction, or anatomy acceptance is
claimed.

### FOOT-003 disposition

Main closes FOOT-003 rejected without using its optional shared correction; the
correction is waived, not exhausted, and no FOOT-004 is authorized. Fourteen
focused/static construction checks passed mechanically. Direct vision found an
anthropomorphic flipper and a human flat shoe. Full collisions, source
counterfactuals, and poses remain unrun. The saved FOOT-003 evidence is
preserved at its existing recorded paths.

The source-faithful B-to-T interpolation does not establish anatomy. The
linear transverse slab, fixed steep H-to-B profile, and local ankle lift
explain the observed limitations, but do not prove that every fixed topology
is impossible. Luna's invented 5 mm hypothetical is not an acceptance gate.
The next foot source/form clarification is proposed to Overseer and remains
pending.

### FOOT-004 source/form candidate implementation record

Status: a fresh single Sol preflight approved this bounded implementation;
FOOT-003 remains historical and untouched. This candidate adds
`foot_form_construction.py`, `foot-form-inputs.json`, and focused tests without
editing `foot_construction.py` or `foot-inputs.json`.

Hypothesis: retain the FOOT-003 eight-row, five-lateral grid, four-cell dorsal
hole, two eight-quad attachment bands, and 22-quad outer closure, but replace
the slab source with five local centre controls H/R/M/B/T and local-normal
radii rL/rD/rP. R is an ankle-body surface centre, not a joint; actual A and
the actual ankle attachment frame remain the attachment source. Centres are
piecewise linear, R-to-M width uses the fixed u^2 rise rule, rD/rP are linear,
and each section uses the settled `.94` rounded transverse profile. Reference
Y values are contact-plane measurements only; no floor projection is applied.

Input differences and roles are prospective coarse artistic/engineering
calibration, not factual wolf anatomy: the human controls use a near-level
H/R/M/B/T centre path with a modest forefoot; the anthropomorphic controls use
the separately authored raised-heel-to-low-forefoot centre path and radii.
Both sides use the same values in their actual source frames; there are no
species branches. All controls, row derivations, frame axes, and radius
semantics are emitted in per-side metadata.

Risks and rejection criteria: slab/flipper, heel spur, collar flare or fold,
disconnected/intersecting limb, and an unreadable low paw or human foot. The
planned source-response measurements are fixed semantic L2 B rL +10%, R/M
selected normal-radius +10%, and T forward extent; these are labelled
counterfactual diagnostics, not input retuning. If promising, Raman may later
run full collision and modest body poses; neither is part of this candidate
implementation.

Budget: one initial construction candidate plus at most one shared construction
correction; zero corrections are spent and no input retuning is allowed after
freeze. The public API is
`build(base_mesh, leg_inputs, foot_form_case)` where the case is one exact row
from `foot-form-inputs.json` containing `case_id`, `construction`, and
`sides`; `evaluate(mesh, levels=0..2)` delegates to the existing generic
evaluator. The new module reuses FOOT-003 validation, topology, collision,
phase/winding, collar, and evaluation helpers; no shared-core extraction was
needed. Raman is the sole executor and must capture source/dependency/input
identities before the first build. All tests and checks remain UNRUN.

#### FOOT-004 initial execution failure and settled correction

The initial captured execution is preserved at
`/home/ben/.cache/connected-foot-static-004-snapshot`. Its `setUpClass`
failed before any foot candidate was constructed, at `_source_frame`, because
the implementation treated `base_mesh.frames.<side>.X` as the terminal ankle
section axis. In the actual construction output that field is the leg-summary
frame from the thigh/shank chain; it is not required to equal the validated
ankle attachment frame.

The single shared correction is settled: `_source_frame` now takes `X` only
from `_ankle_chain`'s validated `attachment_frame["X"]`, while retaining the
actual A origin, projected global +Y `U`, `F = X cross U` consistency checks,
all fixed FOOT-004 inputs, topology, collar, and formulas. The base mesh leg
summary frame remains unchanged metadata and is not relabelled. A focused
mocked-frame regression covers differing summary and attachment axes.

This is FOOT-004's one permitted shared construction correction. Remaining
correction budget: 0. No geometry build, geometry test, capture trial, or
diagnostic was run after the correction; Raman must capture the corrected
source/dependency/input identities before execution. All broader checks remain
UNRUN.

### FOOT-005 attachment-only initial candidate record

Status: Main selected this single bounded attachment candidate after the
FOOT-004 closure. This record is prospective until Raman captures the exact
source, dependency, and input identities and gives execution approval. The
frozen FOOT-004 source, inputs, source controls, ankle ring, dorsal hole, leg
binding, and all historical reports remain unchanged. The live
`foot_form_construction.py` module now includes only the explicit connector
seam; its default path retains the FOOT-004 collar arithmetic.

The candidate adds `foot_attachment_construction.py` and
`foot-attachment-inputs.json`. It uses the explicit `connector_builder` seam
in `foot_form_construction.build`; omitting the callback retains the original
FOOT-004 collar arithmetic and default behavior. The new callback is invoked
before the shared output validator, so the known old anthro cuff is not
constructed or globally bypassed. Bulk grid arithmetic remains solely owned by
`foot_form_construction.py`.

The authored implicit-versus-explicit default-callback test verifies live seam
routing only; it is not historical FOOT-004 equivalence evidence. Raman must
compare the frozen FOOT-004 default output for the human case and, if needed,
reproduce the frozen default anthropomorphic failure/raw geometry before any
claim about historical output or metadata equivalence.

For each fixed corresponding A/H sector, the connector computes
`S0=A+l0*d_in` and `S1=H-l1*c_out`. `d_in` is the normalized matching
ankle-approach-to-A meridian. The hole boundary tangent is normalized
`Hnext-Hprev`; `n_area` is the consistently wound area-weighted sum of retained
incident foot quads. `c_out=normalize(n_area cross tangent)` is sign-selected
by the projected outside-neighbour centroid; zero or ambiguous orientation
fails. Each length is the settled minimum of chord/3, the half adjacent A/H
edge cap, its respective neighbour cap, and an optional half first-positive
retained-body ray hit. Ray `t` at or below the recorded origin tolerance is
ignored; there is no iterative direction or length search.

The connector has only A→S0, S0→S1, and S1→H eight-quad bands, no caps, and
does not alter source stencils or binding. Chord/conormal/adjacent-direction
dots are recorded diagnostics, not mandatory positive gates. Existing quad
fold threshold and shared topology/winding/degeneracy validation remain gates.
The new module's local ring check currently rejects only zero-length support
edges; ring nonselfintersection and connector-versus-retained-body
intersection remain independently checked execution gates, not claims of full
coverage by the implementation. Later L2 surface checks also remain gates.
Undefined room or orientation fails without a workaround.

Budget: one initial candidate plus at most one evidence-justified shared
correction; zero corrections are spent and no input retuning or initial hole
rim edits are permitted. Tests are authored but remain UNRUN. Raman is the
sole execution owner and must snapshot before any geometry test or build.

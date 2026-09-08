# Pelvis source/anatomy calibration results

Experiment lifecycle: finished

Evidence closure: complete

Technology outcome: inconclusive

Run date: 2026-09-05. The single frozen calibration set completed all seven
cases without exceptions, with source/dependency drift reported as false. This
is calibration evidence, not acceptance of a new architecture or a new body
promise. The old pelvis-to-thigh transition remains closed and rejected.

## Frozen evidence

The captured calibrated-inputs SHA-256 is
`3c0cbe9a3ae81def226f91f3d5eddcff6e07f118360abc88670069fe9b010a8c`.
The protocol SHA-256 is
`12570240c84af9894a46cd6bfdc4c9d3eb8df82d09fb7684e72d3d1844114028`.
The final artifact-manifest SHA-256 is
`f0152de5b6b82a60c35599b0b82af746704d1917446d8fceb88b2ca016275871`.
The main thread's 18 tests passed in the frozen runtime with the captured test
set. For the five unchanged historical controls, all three subdivision levels
had exactly matching vertex and quad arrays against the corresponding
`mesh-level-N.json` files from old final attempt-2 checked seed 17: 15/15
mesh-level comparisons exact. This is not a claim that schemas or complete
serialized files are equal.
The main thread independently verified all 72 output-manifest file hashes,
with zero mismatches. The captured runtime packages and source files are
identified; host standard-library/system-library dependencies are not a fully
hermetic operating-system image.

At level 2, every case had one connected face component, 2,249 vertices,
2,176 quads, 152 boundary edges, and zero non-manifold edges. All fourteen T
samples were inside their joined horizontal sections. For every case, thigh
axis fractions 0, .15, and .30 were inside; .45 reached an open-end
indeterminate or out-of-range condition, and every K was out of the represented
range as expected for the proximal stub.

| Case group | Observed one-to-two contour bracket (display frame) | J-to-T samples |
| --- | --- | --- |
| standard, compact, stocky | `[-.02,-.01]` | diagnostic overlay not applicable |
| tall, slender | `[-.17,-.16]` | diagnostic overlay not applicable |
| calibrated ordinary human | `[-.08,-.07]` | 10/10 inside |
| calibrated upright anthropomorphic | `[-.07,-.06]` | 10/10 inside |

Both new cases had no lower intersections at levels 0, 1, or 2, passed their
exit-loop checks and lower quad-normal checks, and retained the old own-side H
containment failure. Both also had `folds.lower.pass` true.
The old rejected verdict is unchanged. Upper context was not reappraised,
despite local lower-fold diagnostics.

The own-side ray test examines a named hip patch, not the entire joined body.
Its missing medial hit is therefore not, by itself, evidence that T escaped
the whole skin. The new closed-section membership measurement answers a
different question; it does not retroactively relax or pass the old gate.

## Anatomy interpretation and limits

For both new cases, J and trochanter reference points were inside. Crest was
outside by about 15 mm and ASIS by about 18.5 mm. PSIS was outside by about
0.077 mm for the human case and 0.459 mm for the anthropomorphic case; pubis
was outside by about 35.7 mm and 65.2 mm respectively. These are distances to
the horizontal-section boundary, not shortest 3-D distances or hard anatomical
error measurements, so they are not strict 3-D tolerance failures. A
bifurcation bracket does not prove pubic-bone fit.

The parent visual judgment was that recalibration made proximal leg roots much
more proportional and less shelf-like than the old controls in both cases.
The waist-to-pelvis transition remains abrupt and pinched, inner-groin
arching is schematic, and buttock shaping is weak. Faceting is present, but
more subdivision is not claimed to fix that structural shape. The result is a
coarse partial improvement, not a polished anatomy pass.

The preregeneration ratios support the hypothesis that input proportions matter:
old source `D/T-K` was `.55` for standard and `1.55` for tall/slender, while the
new cases were `.157` and `.208`; old pelvis-width ratios were `3.0`, `2.55`,
and `2.4`, versus `.890` and `1.214` for the new cases. The result cannot
attribute all improvement to one changed value, prove generalization, or claim
five calibrated bodies. J remains reference-only; T is the executable input,
so source relationships are not yet closed.

The image legend is: orange T-K, purple J-T, green reference points, blue left
T, and red right T; points are markers, not bones. Lower legs and head were not
generated, and cropped upper context is unchanged. Overlapping legend content
is a known frozen-renderer limitation and was not edited. The main thread
personally viewed the five historical triptychs and both new triptychs,
overlays, and undersides. No new renders were made after the run.

## Reproduction and disposition

The captured launcher has no execute permission, so reproduction uses `bash`
with the frozen runtime. The command used for this one run was:

```bash
ck_calibration_old=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot
ck_calibration_snapshot=/home/ben/.cache/creature-kernel/pelvis-source-calibration-set-1
CK_CURRENT_FORM_SURFACE_PYTHON="$ck_calibration_old/runtime/bin/python" PYTHONDONTWRITEBYTECODE=1 \
  bash "$ck_calibration_old/source/experiments/current-form-surface-preview/surface_preview_launcher.sh" \
  "$ck_calibration_snapshot/source/experiments/pelvis-source-calibration/runner.py" run --snapshot "$ck_calibration_snapshot"
```

The run requires a fresh prepared output; the existing prepared output is
protected. No tuning or geometry change is authorized by this result. The
bounded next recommendation is a small source-semantics/relationship design
that separates executable joint J from T and makes pelvic-landmark-to-evaluated-
skin obligations explicit, before refinements or bending. This is a
recommendation for Ben's next decision, not authorization or implementation.

Local artifact root (not checked into the repository):
`/home/ben/.cache/creature-kernel/pelvis-source-calibration-set-1/run`.
It contains `run-report.json`, `artifact-sha-manifest-before.json`, and
`artifact-sha-manifest-after.json`.

Matched views use identical cameras and pelvis/proximal-thigh crops. Under
that artifact root, `cases/case-05-calibrated_ordinary_human/` and
`cases/case-06-calibrated_upright_anthropomorphic/` each contain `surface.png`,
`landmarks.png`, `surface-underside.png`, `section-evidence.json`, and
`legacy-checks.json`. The five preceding case directories preserve historical
controls. These cache paths are local evidence pointers, not portable
repository links or published artifacts.

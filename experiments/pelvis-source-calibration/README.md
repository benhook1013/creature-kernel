# Pelvis source/anatomy calibration

Experiment lifecycle: finished

Evidence closure: complete

Technology outcome: inconclusive

Declared 2026-09-05. This is a bounded source/anatomy calibration, not a pass
for a new architecture, production surface contract, human-body promise, or
whole-body fixture. The parent-authored [protocol](protocol.json) is the
authoritative pre-generation record; its values were frozen before generated
results. The compact [results record](RESULTS.md) closes this calibration with
a mixed anatomical result; it does not reopen the rejected old trial.

## Fixed scope

The frozen construction is identified by SHA-256
`7fd457e2206165eb5e404ce81732f4157234a2e13a64008d96ae75d6abcf5cdb` and uses
the dependency root
`/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot`.
The budget is one calibration set, zero input refinements, and zero geometry
changes. It compares five unchanged historical controls with two new cases
through the same fixed construction. Shoulder geometry remains context only.

The fixed base transform is scale `0.16`, translation `[0.0, 0.16, 0.0]`.
This is the protocol's display/input frame convention for placing the
comparison origin at the intended joint-centre height; it is not an anatomical
inference about the old source. One fixed diagnostic samples 41 sections over
`y=[-0.24, 0.16]`; no input tuning or shape repair is permitted.

## Semantic trace and generator boundary

| Concept | Current meaning and consequence |
| --- | --- |
| Declared hip `J` | The source hip Joint supplies proximal and distal frame records, both local translations `[0,0,0]` with identity rotation. Under authored Part transforms, the proximal endpoint is the pelvis origin `[0,0,0]`, while the distal endpoint is the thigh Part origin: `[±1,-1,0]` in the ordinary profiles and `[±1,-2,0]` in tall/slender. They do not supply one coincident world-space anatomical hip centre. This is missing anatomical resolution, not necessarily a normative invalid-source result; the spec keeps Joint semantics distinct from a rig or solver. |
| Executable `T` / `H` | `form_leg_profile_thigh_start` is the thigh-local start landmark. The exact-five projection adds the profile Part-placement chain and this landmark, producing `H`, which is also `hips.*.P_s` and the constructor's attachment centre. |
| Pelvis Part origin | The root pelvis Part is at `[0,0,0]`; it is not H. |
| Pelvic axial stations | `form_torso_profile_lower_pelvis`, `upper_pelvis`, `lower_abdomen`, and `waist_abdomen` provide envelope centres and radii. They are form stations, not automatically ASIS, crest, pubis, or other skeletal landmarks. |
| Skin bifurcation | The connected-section transition to two thigh contours is derived from H/K, radii, stations, and fixed transition topology. It is not an input landmark or a universal crotch plane. |

Source and implementation references: [hip Joint](../../examples/body-documents/stylized-digitigrade-biped-authored-form.json) line 49, [thigh-start landmark](../../examples/body-documents/stylized-digitigrade-biped-authored-form.json) line 80, [pelvis Part](../../examples/body-documents/stylized-digitigrade-biped-authored-form.json) line 20, [pelvic station](../../examples/body-documents/stylized-digitigrade-biped-authored-form.json) line 90, [Joint semantics](../../spec/body-graph/README.md) lines 131-144, [exact-five projection](../owned-root-assembly-successor-exact-five/exact_five_runner.py) line 308, and [station projection](../owned-root-assembly-successor/prepared_projection.py) line 293.

The explicit generator obstruction is unchanged: the fixed constructor accepts
only `centre` and `knee` attachments and requires `centre == hips.*.P_s`; it
has no independent `J` or `T` fields ([attachment contract](../pelvis-thigh-transition/construction.py)
lines 111-144). [Case provenance](../pelvis-thigh-transition/cases.py) lines
118-158 retains the hip frame pair as `joint_hint` only. Therefore this
calibration can execute T and diagnose J overlays, but cannot claim independent
J-to-skin causality without a code/contract change outside this budget. No code
change is made.

## Protocol values

The compact values below are preregeneration calculations from the frozen
protocol, not mesh measurements or generated-surface results. The full numeric
inputs remain authoritative in `protocol.json`. `T-K` is the executable
thigh-start-to-knee distance; `D/T-K` is the lower-pelvis-station-to-T vertical
offset divided by that distance; pelvis and thigh width use the corresponding
input envelope widths.

| Case | J-K / stature | T-K (m) | D / T-K | Pelvis width / T-K | Thigh width / T-K |
| --- | ---: | ---: | ---: | ---: | ---: |
| `calibrated_ordinary_human` | `.246` | `.382` | `.157` | `.890` | `.393` |
| `calibrated_upright_anthropomorphic` | `.198` | `.313` | `.208` | `1.214` | `.543` |
| historical standard | — | — | `.55` | `3.00` | — |
| historical tall | — | — | `1.55` | `2.55` | — |
| historical slender | — | — | `1.55` | `2.40` | — |

Tall/slender change thigh Part placement from `y=-1` to `y=-2`, but keep
thigh-local T at `[0,0,0]` and knee at `[0,-1,0]`. Both world landmarks move
down one unit; their distance stays one unit. The lower-pelvis station stays
at `y=-0.45`, so D increases from `0.55` to `1.55`. Profile dimension scaling
also narrows their envelopes but does not lengthen this landmark interval.
The profile names therefore cannot be treated as evidence of anatomically
longer femurs. Compact and stocky retain the standard T/K heights; all five
controls remain unchanged in this experiment.

The human case uses an approximate adult-like calibration hypothesis. Its
quarter-height femur cue is the [Proko artist proportion guide](https://www.proko.com/course-lesson/how-to-draw-legs-bone-anatomy-for-artists), not sourced numeric anthropometry. The anthropomorphic case is an explicit artist-design
hypothesis informed by [stylized upright animal-body reference](https://www.disneyanimation.com/publications/flesh-flab-and-fascia-simulation-on-zootopia/), not a biological
measurement or reconstruction of a named character. [OpenStax](https://openstax.org/books/anatomy-and-physiology-2e/pages/8-3-the-pelvic-girdle-and-pelvis) supplies landmark relationships only; no population measurements are extracted. The protocol
records the stated uncertainties: human J about `±0.02 m`, thigh/pelvic
landmarks about `±0.025 m`, skin dimensions about `±0.03 m`; anthropomorphic
landmarks about `±0.03 m` and proportional allowances about `±20%`.

## Boundary and diagnostic methodology

The completed diagnostic evaluated whether the unchanged construction could show
a coherent pelvic envelope and credible two-contour transition for both new
cases while preserving the source distinction between diagnostic J and
executable T. It describes placement and section topology; it must not
reinterpret a J overlay as an executable joint, infer J-to-skin causality, or
retroactively alter the closed old trial's verdict or gates.

The run completed with no exceptions and no source/dependency drift. A
parent-side synthetic-scale bug was fixed before body generation; it did not
change the frozen protocol values or authorize tuning. Results, limitations,
visual judgment, and the bounded next recommendation are recorded in
[RESULTS.md](RESULTS.md).

The diagnostic implementation is [section_diagnostic.py](section_diagnostic.py),
with separate tests in [tests/test_section_diagnostic.py](tests/test_section_diagnostic.py).
The reproduction command uses the captured launcher through `bash` because its
execute permission is absent; it is recorded in [RESULTS.md](RESULTS.md).

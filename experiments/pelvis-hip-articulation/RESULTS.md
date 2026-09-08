# Local pelvis/hip articulation probe results

Experiment lifecycle: finished

Evidence closure: complete

Technology outcome: support — limited regional baseline binding probe only

This result supports the one declared harmonic-weight/LBS baseline for the two
calibrated regional cases. It is not production rigging, an anatomy result, an
animation validation, or a new architecture contract.

## Scope and execution

The run used one shared method, one finite pose set, and zero binding retunes,
rest-shape changes, geometry replacement, rest-input changes, or topology
changes. It used the preserved calibrated L0/L2 surfaces for
`calibrated_ordinary_human` and `calibrated_upright_anthropomorphic`:

- L0 graph-harmonic three-column weights, propagated by the stored full L2
  subdivision stencils;
- conventional three-joint LBS on the preserved evaluated L2 rest surface;
- `rest`, `left_flex_15`, `left_flex_30`, `right_flex_15`, and `both_flex_20`
  for each case; and
- one diagnostic J-pivot counterfactual per case, with J moved by +0.01 metres
  along source/world +Y while weights and rest vertices stayed unchanged.

## Provenance and integrity

Protocol: `pelvis-hip-articulation-harmonic-lbs-001`.

Exact capture snapshot root:
`/home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot`

Exact output run root:
`/home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-run`

Recorded identities:

- capture snapshot manifest (`manifest.json`):
  `e97406f487569b072c1885667a0fd49084a017b30f03cecb04562b81241bef54`;
- output artifact manifest (`artifact-sha-manifest.json`):
  `c6733a75cbd0f7496e71256bc2ed56adb2b924b4e3136339efbe25c6b89fd9c3`;
- output run report (`run-report.json`):
  `208d2df0d5576b68c7f6a777361d86b0eb600275bf66ba02fdaa8f836baa9ff2`.

The collector verified all 85 output files, 29,378,559 bytes, with zero drift.
The run report and per-case reports contain no errors. The captured source and
frozen runtime produced 33/33 main integrated tests, with 10/10 pose technical
passes and 2/2 binding-method passes.

## Technical result

All declared technical checks passed for both cases, including identity/rest
preservation, exact topology, frames and inverse bind, partition unity and
weight bounds, independent LBS, rigid distal ports, strict pelvis stationarity,
triangle/edge strain screening, gross-normal-flip screening, and zero reported
lower non-adjacent intersection pairs.

The following ranges are the actual `left_flex_30` check values:

| Case | Lower-edge ratio | Triangle-area ratio | Minimum normal dot | Lower intersections |
| --- | ---: | ---: | ---: | ---: |
| Ordinary human | 0.740470–1.379660 | 0.728193–1.354985 | 0.628836 | 0 |
| Upright anthropomorphic | 0.661852–1.449174 | 0.653300–1.429969 | 0.602151 | 0 |

The anthropomorphic lower-edge minimum is near the declared 0.65 screening
floor. These are small-angle screening measurements, not evidence for deeper
bends or material-volume preservation.

The J-pivot counterfactual produced a response while leaving weights and rest
vertices unchanged: `response_over_L` was `0.006084415350198488` for the
ordinary human and `0.007341277288441133` for the anthropomorphic case. This is
a causality diagnostic only; J is not a rest-shape control.

## Main Worker visual judgment

The Main Worker personally inspected all ten front/side/rear-three-quarter
surface triptychs, both L30 diagnostic overlays, the human L30 and
anthropomorphic rest/L30 undersides, and the historical human-rest underside.
There was no obvious new tear, sharp attachment seam, gross collapse, or
interpenetration from the small-angle bending. The same shared rule works on
these two cases as a limited regional baseline. The result is **READY FOR BEN
APPRAISAL** at the limited regional bend checkpoint, not a polished anatomy or
animation validation.

The Overseer independently inspected rest, L30, and both20 views for both
cases, including both L30 undersides, and agrees that the result is ready for
limited appraisal.

Existing pinched waist, schematic groin arch, weak buttocks, and faceting remain;
no rest-shape improvement is claimed. Open thigh boundaries can look capped in
underside views because opposite inner walls are rendered together; no caps are
generated. Overlay legends overlap in some diagnostic views, a presentation
limitation rather than a geometry result.

## Review disposition and limitations

A fresh Luna review identified the weight-method gap. A Sol-medium checker
worker implemented the fix using an independent graph Dirichlet, residual, and
stencil check; the Main Worker inspected and tested the resulting code. This
record does not claim a new independent post-fix full review; none was run.

Adjacent folds are not exhaustively proven by the non-adjacent intersection
checker. The evidence remains visual inspection plus finite strain/normal
screening. The open lower boundaries do not support caps or global solid-volume
claims. Do not extrapolate this result to deeper bends, material volume,
whole-body behaviour, animation quality, or production rigging.

The bounded probe also included local operational corrections for the capture
source/output manifest distinction, exported readback, overlay field lookup,
and synthetic-fixture winding. These did not change the method, inputs,
geometry, rest surface, topology, or retune budget. The historical pelvis
source-calibration and pelvis-to-thigh-transition verdicts remain unchanged.

## Recommendation

Pause for Ben's visual appraisal. Ben should accept or reject this limited bend
evidence, then settle the next scoped quality target with the Overseer. Do not
automatically add poses, alter geometry or topology, expand to the body, build a
general rig framework, publish, push, or merge.

Reproduction commands and the captured-source procedure remain in the
[experiment README](README.md#reproduction).

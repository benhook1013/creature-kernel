# Local pelvis/hip articulation probe

Experiment lifecycle: finished

Evidence closure: complete

Technology outcome: support — limited regional baseline binding probe only

The bounded result is recorded in [RESULTS.md](RESULTS.md).

## Question and authorized outcome

Can a shared automatically generated binding move both calibrated proximal
thighs around intelligible independent hip pivots while keeping their joined
surface credible under modest flexion? Ben authorized this local regional
checkpoint through the Overseer on 2026-09-05. It is not finished anatomy,
whole-body rigging, a production architecture choice or a lower quality goal.
Ordinary human and anthropomorphic bodies remain equally important targets
on the intended path to polished independent-artist animation.

The [protocol](protocol.json) fixes one baseline binding, five poses per body,
one separate pivot-response diagnostic per body, and zero binding retunes,
rest-shape changes or topology changes before execution. Routine tooling
defects may be corrected without changing the method or this budget. A failed
baseline is closed and reported to the Overseer with a bounded recommendation;
it does not silently trigger another method or shape campaign. The Overseer
can direct routine regional follow-up under Ben's authorization. Stop for Ben
at the meaningful visual checkpoint or a retained-human decision.

The [source calibration](../pelvis-source-calibration/README.md) and
[transition trial](../pelvis-thigh-transition/README.md) retain their exact
historical outcomes and exhausted budgets. Neither is restarted here.

## What changes, and what does not

Use the two saved calibrated L0/L2 meshes and exact original inputs. Do not
rebuild or reshape them. The independent J coordinates previously used only
as calibration reference points become **experimental hip pivots** here, with
their anatomical uncertainty retained. T remains thigh start, K remains knee;
their distinct joint-local rest coordinates are transformed with the thigh.
Pelvic landmark estimates remain diagnostics, not constraints forcing skin
through every point. This makes J meaningful for binding and pose without
requiring J to alter resting skin. The 92-component rest construction and
public Joint semantics are unchanged.

Generate one three-column pelvis/left/right weight field from the actual L0
quad-edge graph: ringB/exit vertices anchor each thigh, non-transition
vertices anchor the pelvis, and socket/ringA weights solve the uniform graph
Laplacian. Propagate those weights using the full stored subdivision stencils,
never dominant-owner labels. No hand-painted or case-selected weights exist.
Apply linear blend skinning to the preserved **evaluated L2 rest surface**.
This is not a claim that deforming and subdividing the control cage commute.
Stored subdivision provenance remains rest provenance; posed positions depend
on the recorded rest vertices, weights and actual joint transforms.

Joint rest frames originate at J and use the J-to-K direction; fixed local
T/K coordinates are recorded separately. Inverse-bind then posed-global
transforms supply conventional skinning, as described by the
[Khronos skinning tutorial](https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_020_Skins.html).
This is an experiment-local CPU implementation, not adoption of glTF, an
engine, an export contract or a general skeleton framework.

## Evidence and judgment

Reload exported meshes for independent transform and surface checks. The
protocol declares identity, weighting, frame, rigid distal-port, upper-pelvis
movement, local strain, gross-flip and lower-intersection checks. The full
body has open boundaries: no caps or global solid-volume claims are added.
The represented distal thigh ends must stay at their expected transformed
extent; the missing lower legs are outside scope. Keep inherited upper-body
issues and uncertain anatomical markers separate from new binding failures.

Render matched actual surfaces and separate frame/landmark overlays at rest,
15/30-degree single-hip flexion, mirrored 15-degree flexion, and both hips at
20 degrees. Include underside views for rest and 30 degrees. The Main Worker
personally inspects these results. No moving-mesh or numeric success
alone is visual acceptance; no new pinching, collapse, attachment artifacts
or unwanted pelvic drag should be hidden by framing or overlays.

Exact new code, inputs and existing rest-mesh identities are captured before
execution and checked after. Reuse the already captured managed runtime;
run its `surface_preview_launcher.sh` through `bash` with
`CK_CURRENT_FORM_SURFACE_PYTHON` pointing to the frozen runtime and
`PYTHONDONTWRITEBYTECODE=1`. Local artifact paths and exact run commands will
be recorded with the result. Nothing is published, pushed or merged here.

## Reproduction

Use absent sibling snapshot/output paths. The runner captures its exact source
allowlist and copied inputs; execution must use the captured runner from its
own directory. The example paths are local evidence, not repository files.

```bash
export PYTHONDONTWRITEBYTECODE=1
export CK_CURRENT_FORM_SURFACE_PYTHON=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python
export CK_HIP_LAUNCHER=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/current-form-surface-preview/surface_preview_launcher.sh
bash "$CK_HIP_LAUNCHER" experiments/pelvis-hip-articulation/runner.py prepare --snapshot /home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot
cd /home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot/source/experiments/pelvis-hip-articulation
bash "$CK_HIP_LAUNCHER" -m unittest discover -s tests -v
bash "$CK_HIP_LAUNCHER" runner.py run --snapshot /home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot --output /home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-run
bash "$CK_HIP_LAUNCHER" runner.py verify --snapshot /home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot
```

The existing renderer shows both sides of open surfaces. Opposite inner walls
can resemble end caps in an underside image; no caps are generated. Report
this limitation alongside the matched surface/diagnostic views.

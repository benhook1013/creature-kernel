# EXP-0003: Connected-leg assembly staging

Experiment ID: EXP-0003

Experiment lifecycle: running

Evidence closure: open

Technology outcome: none

Owner: Main Worker; Overseer provides scoped independent review

Date started: —

Date completed: —

Research questions: Pending the Main decision and detailed protocol

Related DRs: —

Related proposal (deferred Layer 3 path: `experiments/connected-leg-assembly/pelvis-foundation-proposal.md`) — Proposed; source003 rejected the shared correction for human admission, no body execution GO.

Related recipe (deferred Layer 3 path: `experiments/connected-leg-assembly/pelvis-foundation-recipe.md`) — initial law and one shared correction evaluated; source003 failed human source admission, no body admitted.

Source evidence (deferred Layer 3 path: `experiments/connected-leg-assembly/pelvis-foundation-source-results.md`) — 001/002 closure plus source003; corrected law failed human source admission and existing-topology construction is rejected.

Successor representation (deferred Layer 3 path: `experiments/connected-leg-assembly/pelvis-boundary-support-proposal.md`) — Proposed Rev2 ten-phase upper-pelvis collar with separate abdomen handoff; fresh review and Main correctness closure complete, unexecuted.

Successor recipe (deferred Layer 3 path: `experiments/connected-leg-assembly/pelvis-boundary-support-recipe.md`) — Proposed Rev2 shared source law, exact 162/146 topology and binding contract; recipe/review prerequisite complete, capture required before evaluation.

Successor review (deferred Layer 3 path: `experiments/connected-leg-assembly/pelvis-boundary-support-review.md`) — Rev1 and fresh Rev2 challenges complete; narrow technical findings closed without changing source coefficients or topology.

## Protocol

The prepared [protocol](protocol.json) and [inputs](inputs.json) record the
current Main baseline. The baseline stages one common
source/frame/subdivision/binding path from each calibrated L0 root through an
explicit knee and shank to open ankle ports. The protocol remains frozen; this
evidence does not update its JSON values or establish a technology outcome.

## Question

Can the current calibrated connected root L0 be staged through the knee and
shank as one evaluated connected surface while reusing source-driven hip frames,
existing subdivision, and automatic hierarchical binding?

## Hypothesis

A common leg staging path may extend the connected root coherently through the
knee and shank while preserving source/frame/binding-driven movement of the
displayed evaluated surface. This is untested evidence, not an architecture or
product claim.

## Decision Impact

The result may inform the next internal whole-character refinement step. The
leg is an internal milestone; the first integrated whole-character refinement
remains the named Ben checkpoint.

## Inputs and Fixtures

Use the immutable roots, matching prior L2 rests, original case/reference
metadata, and prior hip bindings named in [inputs](inputs.json). J remains an
independent pose input; T and K remain the original source points. The
[example brief](example-brief.md) records the appearance scope, not a species
or gait contract.

## Method

Stage the common source-driven leg through the knee and shank, including the
angled anthropomorphic K-to-A rest frame, and test automatic hierarchical
binding on the same evaluated connected surface. The stage ends at open ankle
ports: foot-bearing, heel, sole, and paw geometry are not implemented. Do not
add per-case mesh repairs or disconnected display meshes.

## Environment

The first capture-tool invocation is recorded below as tool-invalid, not
candidate evidence. Baseline002 rest capture and verification are recorded
below, followed by the Baseline003 and Baseline004 outcomes and the later
Baseline005 immutable run. The original protocol and inputs remain frozen from
before these runs, and the exact source, inputs, protocol, frozen mesh
identities, and managed runtime remain those described by the
[protocol](protocol.json). This Layer 2 checkout performs no experiment
execution or geometry validation.

## Metrics and Thresholds

The [protocol](protocol.json) declares topology, source/section, binding,
stencil, intersection, strain, hip-regression, perturbation, and visual checks.
The asymmetric-radius rule does not gate centroid equality with A; anatomy
plausibility remains a separate visual judgment.

## Reproduction

The existing runner's prepare/run/verify command syntax is shown below with
new-path placeholders only; this is reproduction syntax, not an execution
outcome:

```bash
# Placeholders must be fresh absent paths for each reproduction.
trial_python="/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python"
trial_launcher="/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/current-form-surface-preview/surface_preview_launcher.sh"
trial_snapshot="/home/ben/.cache/creature-kernel/connected-leg-assembly-NEW-rest-snapshot"
trial_output="/home/ben/.cache/creature-kernel/connected-leg-assembly-NEW-rest-run"

PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON="$trial_python" bash "$trial_launcher" experiments/connected-leg-assembly/runner.py prepare --snapshot "$trial_snapshot" --rest-only
PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON="$trial_python" bash "$trial_launcher" "${trial_snapshot}/source/experiments/connected-leg-assembly/runner.py" run --snapshot "$trial_snapshot" --output "$trial_output" --rest-only
PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON="$trial_python" bash "$trial_launcher" "${trial_snapshot}/source/experiments/connected-leg-assembly/runner.py" verify --snapshot "$trial_snapshot"
```

The verified focused checker command uses the managed runtime launcher:

```bash
PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python bash /home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/current-form-surface-preview/surface_preview_launcher.sh -m unittest discover -s experiments/connected-leg-assembly/tests -p test_checks.py -v
```

This is checker evidence only; it does not turn the captured or failed
Baselines into candidate acceptance.

Subsequent focused geometry-building tests use the capture-first entrypoint so
the live test is never executed before its source snapshot. The test file and
optional unittest names are logical experiment paths; the entrypoint resolves
their actual captured paths from the runner manifest rather than assuming a
snapshot layout:

```bash
PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python bash /home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/current-form-surface-preview/surface_preview_launcher.sh experiments/connected-leg-assembly/captured_tests.py --snapshot /home/ben/.cache/creature-kernel/connected-leg-captured-tests-NEW-snapshot --test-file tests/test_head_construction.py --test-name HeadConstructionTests.test_declared_controls_reach_actual_l0_and_evaluated_l2_surface
```

The entrypoint calls the existing runner preparation and verification seams,
runs only the selected captured test script with the manifest-recorded managed
interpreter, verifies the snapshot again, and emits a JSON status/path report.
Its tooling-only bootstrap at
`/home/ben/.cache/creature-kernel/connected-leg-captured-tests-001-snapshot`
passed 4 mocked tests with both verifications passing; no geometry test ran.
The captured runtime and external frozen dependencies remain reused rather
than copied, and the existing manifest explicitly does not claim hermetic OS,
loader, or kernel isolation.

## Results

The first capture-tool invocation was tool-invalid, not candidate execution:
the retained paths `/home/ben/.cache/creature-kernel/connected-leg-assembly-001-rest-snapshot`
and `/home/ben/.cache/creature-kernel/connected-leg-assembly-001-rest-run`
record both cases failing construction with `ConstructionError: leg_inputs must
contain both sides and the two shared factors`. No mesh, image, or pose was
generated; the source consumer received the wrong shape, source inputs were
unchanged, and no anatomical verdict or geometry refinement was consumed. The
original runner's top-level status `internal-diagnostic` with exit 0 is not
success; `full_pass: false` and the per-case exceptions are decisive. Old
outputs are preserved. This is a historical 001 record: its `constructor
alignment and runner error propagation underway` and `verification incomplete`
labels apply to that invocation only, not current work. No later exit-0
verification is claimed here without the exact evidence.
At that time, this note recorded only a tool-invalid invocation and the
generic experiment remained planned/open/none. The following running/open/none
wording belongs to that Baseline002 stage record; it does not replace the
later Baseline005 history below.

Baseline002 rest capture and run completed with verification passed at
`/home/ben/.cache/creature-kernel/connected-leg-assembly-002-rest-snapshot` and
`/home/ben/.cache/creature-kernel/connected-leg-assembly-002-rest-run`.
Snapshot SHA-256 is
`f3f885444298e7073aaf2831c3070c22487534d6ea67c5bb5fe3e37c49d4fdc0`; the
artifact manifest SHA-256 is
`975f415790b1ae21a49632a41027363f9de8a1fbbbf9e91fad5011a216531dbe`. Both
cases reported base `264v248q` and L2 `4041v3968q`, with no exceptions,
render errors, or drift. Actual body execution occurred, but this is not a
candidate pass. The remaining experiment interpretation is recorded by the
later stage entries below.

Main directly inspected both rest triptychs and undersides at those exact
paths: the hip, thigh, knee, and shank read as continuous, with no obvious new
seam or gross rest collapse. Retained are the pinched waist, schematic groin,
weak buttock, and faceting; limbs end at open ankles, with no head, arms, or
feet. This is scoped initial static inspection only, not anatomy polish, a
technical pass, or pose acceptance. Main does not request Ben review at this
internal leg milestone. Old 001 outputs remain unchanged.

Baseline003's actual execution at
`/home/ben/.cache/creature-kernel/connected-leg-assembly-003-pose-snapshot` and
`/home/ben/.cache/creature-kernel/connected-leg-assembly-003-pose-run` exposed
a numeric-guard issue; it was fixed without changing weights, but the run
remains a failed diagnostic outcome, not a candidate pass. Separately, the
captured 52-test suite pass for Baseline004 (test count from the execution
record, not presumed from the run report) is at
`/home/ben/.cache/creature-kernel/connected-leg-assembly-004-checked-snapshot`.
The Baseline004 source run report at
`/home/ben/.cache/creature-kernel/connected-leg-assembly-004-checked-run`
records an actual run with runtime integration failures: fourth-pose mirrored
`15_15` label/meaning metadata was forwarded as angles; bent render bounds
were left at rest-only bounds because they finalize after the pose loop;
pose collision checks were unavailable; and perturbations were not reached
after the earlier pose error. `perturbations.py` was captured, so it was not a
missing module. The runner is now fixed; no rerun success is claimed. At that
stage these outcomes left the experiment running/open/none; Baseline005 is the
later immutable run recorded below.

Baseline005 is now an immutable finished run at
`/home/ben/.cache/creature-kernel/connected-leg-assembly-005-integrated-snapshot`
and `/home/ben/.cache/creature-kernel/connected-leg-assembly-005-integrated-run`;
no restart run was made. It captured 59 tests with 0 skips; the full runner
exited 1 on an anthropomorphic calf metric-only reject. All 10 pose checks
completed with full `315m` total-pair coverage and 0 hits. Human perturbations
were 3/3 pass; anthropomorphic perturbations were 2/3, with the signed-calf
metric failing 0 among positives while analytic L2 matched. There were no
exceptions or render errors, and postverify passed. Luna and Sol are
investigating read-only; this does not claim the measurement bug resolved.
Main personally viewed all 10 final surface triptychs at the 005 run, with no
obvious tear, seam, or gross collapse; knees remain schematic/angular and the
inherited waist/chest form defects persist. This is recovered render
diagnostic evidence, not polished body or all-pose acceptance.

## Analysis

Interpretation remains bounded. Baseline005 records the latest captured checks
and perturbations, including an anthropomorphic metric-only reject under
read-only investigation; these execution outcomes do not establish anatomy,
technical, pose, or product acceptance.

## Limitations

This is a bounded leg-staging experiment, not whole-body architecture, a
supported morphology promise, a detailed anatomy study, or the named Ben
checkpoint. Human and loose wolf-like humanoid appearance references share the
common pipeline. The human plantigrade arrangement is a provisional staging
hypothesis; the anthropomorphic case uses an angled shank for its coarse
digitigrade target. Both stop at open ankles, and foot-bearing geometry is not
yet implemented.

Saved-root loading isolates this connection and binding test; it is not the
final source-to-whole-character path. Before the whole-character checkpoint,
assembly must regenerate the root from its recorded source construction and
inputs and demonstrate that the rebuild matches the intended baseline. These
saved meshes must not become hidden authored inputs. This obligation is
preserved here without regenerating the root now or introducing a new
framework.

## Conclusion

Running with open evidence closure and no technology outcome. The tool-invalid
invocation remains historical; Baseline002 is execution evidence, not a
candidate pass, and the protocol remains frozen.

## Recommended Follow-up

Complete the remaining checks and source perturbations only within the Active
runway, then stop for the named whole-character checkpoint or a retained-human
boundary.

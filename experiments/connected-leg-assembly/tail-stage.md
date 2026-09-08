# Connected-tail constructor staging

Status: `implemented`; captured static L2 and visual artifacts are available,
with parent visual review pending and no technology or anatomy outcome

This is a local constructor experiment for the connected-leg assembly. It is
not a universal anatomy adapter, a tail rig, a source-construction replacement,
or a product/whole-character result. The constructor consumes the current
source-built connected-leg L0 mesh and does not change the binder.

## Frozen candidate

The exact candidate is recorded in [tail-inputs.json](tail-inputs.json): one
initial candidate, no correction before execution, and at most one shared
geometry correction if later evidence justifies it. The pinned source host is
face `58`, vertices `[41, 44, 66, 63]`, owner `domain.pelvis`. Its coordinates
and oriented normal are derived from the supplied source-built mesh at build
time; the constructor rejects host identity drift instead of recovering a
different pelvis face.

The host quad is replaced in its existing face-58 slot by the first inset
annulus quad. The remaining three annulus quads, four-corner tail sides, and
one terminal cap are appended. The original host quad is not retained as an
internal closing face. All inherited vertices and all non-host face slots stay
exact. The five total tail rings use fractions `0, .25, .5, .75, 1`; the
collar is the first translated ring. Inset corners use `C + .4(p-C)` and the
collar translates them outward by `0.012 m`. The frozen candidate uses length
`0.45 m`, declared terminal direction `(0, -.25, -1)` normalized by the
constructor, and base/middle/tip radii `.035/.045/.008 m`.

Frames use the actual host phase and projected global `+X` on each cubic path
tangent plane, with `V = X cross tangent` and source-compatible winding. Future
tail transition supports are emitted as convex host-quad metadata targeting
the pelvis; weights remain explicitly unimplemented. No tail joint or
articulation is present. The human case is data-disabled and must return its
source mesh exactly; the anthropomorphic case is data-enabled without a
species branch.

## Reproduction

The candidate inputs and intended geometry design were frozen before the first
geometry-building test. That preliminary invocation found a mechanical
stencil-index bookkeeping error and produced no candidate result; the minimal
correction used the pre-append vertex count, without changing geometry,
inputs, or dependencies. The corrected code, tests, and inputs were then held
fixed for the final candidate run. The focused managed command is:

```bash
PYTHONDONTWRITEBYTECODE=1 CK_CURRENT_FORM_SURFACE_PYTHON=/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python bash /home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/current-form-surface-preview/surface_preview_launcher.sh -m unittest discover -s experiments/connected-leg-assembly/tests -p test_tail_construction.py -v
```

## Result

The final run completed `6/6` tests with no skips or errors. The disabled human
case returned its source-built mesh exactly. The enabled anthropomorphic case
validated the pinned host identity, in-place face-58 replacement, one-to-many
mapping, unchanged non-host vertices/faces/loops/stencils, five rings, cubic
rear/down frames, cap closure, and convex future-support metadata. Hostile
identity/control cases rejected in memory; no rejected payload was persisted.

A subsequent metadata-only preservation patch retained the inherited
construction scheme while adding the tail adapter entry; the same six-test
managed suite was rerun and remained green. Host geometry, controls, and
topology were unchanged.

The original live constructor result contained no integrated capture, rendering,
or L2 evaluation. The later captured static evidence is recorded below and
does not add binding, source retuning, tail articulation, or a
whole-character/anatomy claim.

## Provenance limitation and follow-up capture

The original pre-test exact source/dependency/input snapshot was **not
preserved**. The earlier managed runtime path and immutable source references
were not a substitute for that snapshot, and no rendered trial was captured.
Any later capture is post hoc current-state provenance and must not be relabelled
as the original pre-test snapshot.

The new `captured_tests.py` entrypoint was the required next provenance step.
The initial 008 manifest and captured-test result are retained below; the
allowlist obstacle was resolved for the subsequent 009 capture.

## Post hoc capture attempt (008)

The first capture after the historical gap was performed before any further
tail build, test, or render, using the verified copied managed runtime:

- snapshot: `/home/ben/.cache/creature-kernel/connected-tail-assembly-008-capture`
- manifest: `/home/ben/.cache/creature-kernel/connected-tail-assembly-008-capture/manifest.json`
- result report: `/home/ben/.cache/creature-kernel/connected-tail-assembly-008-capture-report.json`
- runtime: `/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python`
- captured test: `/home/ben/.cache/creature-kernel/connected-tail-assembly-008-capture/source/experiments/connected-leg-assembly/tests/test_tail_construction.py`

Capture pre-verification and post-verification passed. The manifest preserved
the admitted frozen construction, dependencies, and mapped calibration inputs.
It did not capture `tail_construction.py` or `tail-inputs.json`: those files
are absent from the current `runner.CAPTURE_FILES` allowlist, and local import
expansion admits only allowlisted files. The captured tail test therefore
returned `failed` before discovery with:
`ModuleNotFoundError: No module named 'tail_construction'`.

This is a capture-packaging obstacle, not a constructor or geometry result.
No live fallback was run, no captured tail test passed, and no new static L2
derivation or front/side/rear-three-quarter render was produced. The earlier
live constructor evidence remains unchanged and is not relabelled as captured
evidence. No workaround or recapture was applied to 008.

## Captured static L2 and visual evidence (009)

Leibniz's allowlist correction was captured before execution. The captured
focused tail suite then completed `6/6` tests with pre- and post-verification
passed:

- capture: `/home/ben/.cache/creature-kernel/connected-tail-assembly-009-capture`
- manifest: `/home/ben/.cache/creature-kernel/connected-tail-assembly-009-capture/manifest.json`
- test report: `/home/ben/.cache/creature-kernel/connected-tail-assembly-009-capture-report.json`
- managed runtime: `/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/runtime/bin/python`

The unchanged captured constructor was then evaluated through the captured
connected-leg evaluator at L2 and rendered with the manifest-recorded frozen
renderer. The complete static output is retained at
`/home/ben/.cache/creature-kernel/connected-tail-assembly-009-static-frames-adapter`;
its machine report is `render-report.json` and its artifact inventory is
`artifact-manifest.json`.

The ordinary-human regression is tail-disabled and produced `264v/248q` at
L0 and `4041v/3968q` at L2. Its matched render contains front, side, and
rear-three-quarter views at 1600x550, plus an underside companion; tail detail
is explicitly unavailable because the feature is disabled. The
anthropomorphic case produced `284v/268q` at L0 and `4361v/4288q` at L2. It
has the same matched views and underside, a context render with three
centreline control-span overlays, and a tail-detail crop using 345 L2 vertices.
All are labelled `CAPTURED STATIC L2 - VISUAL REVIEW PENDING`; no visual
acceptance is claimed.

The first static derivation attempt is preserved at
`/home/ben/.cache/creature-kernel/connected-tail-assembly-009-static` as a
tool failure: the frozen generic evaluator rejected the constructor's
diagnostic `frames.tail` field because its validator requires exactly
`left/right`, before rendering. The retained 009 static output uses a
memory-only adapter that removes only that non-consumed metadata field before
subdivision; vertices, quads, stencils, inputs, and constructor source are
unchanged. This compatibility limitation is recorded in `render-report.json`.

Capture 008 remains the earlier failed/incomplete discovery attempt and was
not overwritten. No tail binding, pose, collision, whole-character run, or
geometry revision occurred.

## Metadata contract closure (010)

The constructor had already recorded path-frame diagnostics in
`metadata.tail.ring_frames`, but then appended a duplicate `frames.tail` entry
to the root frame mapping. The root `frames` contract is reserved for the
source left/right frames and the frozen evaluator requires exactly those keys.
The correction keeps `frames` equal to the input root frames and stores the
remaining diagnostic fields at `metadata.tail`: `host_normal`, `source_phase`,
`ring_frames`, and `frame_rule`. This is an interface correction only; no
vertices, quads, stencils, inputs, or binding fields changed.

The corrected source was captured before focused tests or L2 derivation:

- capture: `/home/ben/.cache/creature-kernel/connected-tail-assembly-010-frame-metadata-capture`
- manifest: `/home/ben/.cache/creature-kernel/connected-tail-assembly-010-frame-metadata-capture/manifest.json`
- test report: `/home/ben/.cache/creature-kernel/connected-tail-assembly-010-frame-metadata-capture-report.json`
- `tail_construction.py` SHA-256: `d2d2a49395ccafd8c752efdfd1482f56a3f3e494a7dd73fa96a78fa07a53cbbe`
- `tests/test_tail_construction.py` SHA-256: `b3bea3a19fa207bd78b8e4efdffb62f22f9b6f09f9fb125c5de71ba7b2098ce0`

The captured focused suite passed `6/6`, with pre- and post-verification
passed. Direct captured evaluation then proved both cases' L0 geometry and
left/right root frames equal to the saved 009 frames-adapter outputs, and
proved all L2 nonmetadata fields plus root frames equal. The machine record is
`/home/ben/.cache/creature-kernel/connected-tail-assembly-010-frame-metadata-static-identity-replay/geometry-identity.json`.
The L2 geometry hashes are `9ab62ae04825b01908fc44a732ef8a8fac640887973b0765c727a027c08d4702`
(human) and `c4d26df73553736f049e164812dc86791916d00b2cb110c62b1c9031a868f733`
(anthropomorphic); root-frame hashes are respectively
`7075b4fa82de341d5774e9692cb653f75104962896d8b7d935ca316206a2f6e2` and
`703ff29b38949d76f47526cbe995adab8a5584339fabbdfab6456145cc058996`.

Because the nonmetadata/root-frame identity is exact, the 009 matched,
context, diagnostic, underside, and anthropomorphic tail-detail images were
reused by identity; no unnecessary rerender was performed. The original 009
raw evaluator failure and the 009 frames-adapter diagnostic derivation remain
preserved at their recorded paths above.

## Saved-009 rear/overhead measurement view

One rear/overhead detail view was generated directly from the saved 009
anthropomorphic L2 mesh, with no construction or geometry rerun:

- image: `/home/ben/.cache/creature-kernel/connected-tail-assembly-010-rear-overhead-detail/saved-009-L2-tail-rear-overhead.png`
- report: `/home/ben/.cache/creature-kernel/connected-tail-assembly-010-rear-overhead-detail/measurement-report.json`
- image SHA-256: `646737b3dbd1ad949ad32052164183a2243d4b2747af4a2572289f4d874b624b`

The section uses the baseline middle station `f=0.5`, its four-corner source
support and source tangent frame, then exact intersections of all
`domain.tail` L2 triangles with the perpendicular plane. The source section
is `0.090000000000 m` wide in both X and the other normal V, from declared
middle radius `0.045 m`. The actual L2 section is
`0.077490234375 m` in both axes, half-width `0.0387451171875 m`, or
`0.8610026041666666` of that declared radius, across 78 intersection points;
maximum plane residual is `2.168404344971009e-17 m`. This records equal
X/V contraction at that station, not radius faithfulness or anatomy
acceptance, and does not authorize a shape correction.

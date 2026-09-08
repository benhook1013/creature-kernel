# Bounded pelvis-to-thigh transition

Experiment lifecycle: finished

Evidence closure: complete

Technology outcome: reject

Outcome scope: the bounded candidate and appraisal target, not every fixed-topology
method or an accepted whole-body architecture. Completed 2026-09-05 (NZST).

Owner: main technical lead; Ben retains direction and acceptance.

## Authorization and question

Ben authorized this local experiment on 2026-09-05, following read-only
diagnosis of the stopped hip pre-filter. Astra orchestration is explicitly
authorized for this task. This is not acceptance of a whole-body architecture,
production interface, morphology promise, or replacement of the old trial's
gates. Research context: RQ-002, RQ-012, RQ-020 and RQ-021.

Can a single shared pelvic transition separately control pelvic wrap and
thigh descent, while keeping both sides and the adjacent abdomen one welded,
source-linked evaluated surface across the existing five profiles and an
executable ordinary-human reference?

The source-linked hip centre, thigh direction and local frame must have
explicit geometric consumers and meaning on the final surface. Vertex
movement alone is not proof of the expected structural response. Attachment
curves are generated from dimensions and consistent rules, not authored mesh
repairs. Human and anthropomorphic targets are equally important; their
defaults need not be identical. The long-term quality target is polished
independent-artist-quality models and animation. Real-time use remains primary,
with optional offline enhancement; this experiment chooses no new budget or
simulation system.

## Finite budget, fixed before any candidate run

One initial construction plus **at most two shared geometric refinements**:
attempts 0, 1 and 2. Stop at the first technically passing and directly visually
credible candidate, or after attempt 2. Any change that changes generated
coordinates or topology after a candidate run counts, even a geometric bug
fix. No alternate construction, profile-specific repair, input retuning,
threshold relaxation or further refinement is authorized. The chosen local
topology is fixed before attempt 0 and cannot be replaced during refinement.

Pure evidence-tool defects may receive at most two repair/replay batches;
retain the defective outputs and record each batch. Such a batch must not
change geometry, cases or quality thresholds. Abort and report if these bounds
are insufficient. Deterministic repetitions and predeclared perturbations are
evidence runs, not tuning rounds. Do not render or rerun the old pre-filter.

## Construction boundary and cases

Only lower abdomen, pelvis and proximal thigh transitions may change. Preserve
the surrounding upper root as context. Keep promising shoulder evidence
separate: inherited arm/upper-body failures neither disappear nor become
failures caused by the new lower-body construction. No distal anatomy,
rigging, bend implementation, general anatomy framework or simulation.

The construction has one welded bilateral pelvic/groin region with explicit
thigh interfaces and dedicated transition rows. All cases use the same code
and topology; case names never select geometric formulas. Exact inputs, source
pointers, local frame derivation, final layout and numeric acceptance measures
are recorded in `inputs.json` and this README before attempt 0.

Development cases: existing standard neutral, compact/broad and slender.
Required coverage: all existing five profiles without changing their source
projection, plus one concrete simplified ordinary-human pelvic case generated
through the same construction. The human case is an executable challenge to
cross-family coarse proportions, not measured anatomical truth, a human
whole-body fixture or proof of population coverage. Its numeric inputs are
fixed before execution and may not be repaired individually.

Required perturbations: isolated pelvis width, thigh spacing/hip-centre
translation, thigh direction, front/back offset, one asymmetric combination,
and one deliberately incompatible case. Their inputs and expected geometric
responses are declared before running; rejection cannot be rationalized by
inventing source-coherence restrictions after results.

## Evidence and stopping

### Initial layout and structural meaning (fixed before attempt 0)

Keep the predecessor's upper-root surface as context. Replace each eight-quad
hip band with three eight-quad bands: shared socket boundary, ring A, ring B,
and distal exit. This is 152 controls and 136 quads at L0, with five open ports;
two ordinary Catmull-Clark steps yield 544 and 2176 quads. The fixed layout is
shared across every case. There is no evaluated-surface correction stage.

H is the world-space thigh-start landmark, coincident with the thigh part
origin in the existing source. It is this experiment's consistently derived
attachment centre, not a claim that the source's joint-frame hints have been
resolved into a rig. K is the source knee landmark. Direction d is normalize(K-H).
The local frame uses U=-d, X=normalized projection of world +X orthogonal to d,
and F=X cross U. Identity source frames and a downward direction with
dot(d,world-down)>0.9 are admitted here. The distal skin exit is E=H+0.45(K-H),
not H. This ends within the proximal thigh; it adds no knee or distal anatomy.

The eight perimeter directions normalize the predecessor's nonzero (u,q)
pairs to (a,b). The socket uses lateral radius
(lower-pelvis lateral extent minus |H.x-L.x| plus thigh r_x)/2 on its outer
side, and 1.10*r_x on its inner side; front/back depths average the respective
pelvic depth relative to H with thigh r_z. Its upward displacement is
0.35*(L.y-H.y)+0.25*r_y+0.15*(L.y-H.y)*side_sign*a. Thus source r_y controls
proximal vertical flesh extent, not bone length. Negative radii, nonpositive
L.y-H.y, inconsistent H/P_s, or nonpositive nominal medial clearance
(H_right.x-H_left.x-r_x_left-r_x_right) are input rejections, never clamps.

Ring B is elliptical in the source-derived frame at H+0.30(K-H), with r_x/r_z;
the exit has the same ellipse at E. Ring A initially averages socket and ring
B coordinates. Sparse actual subdivision weights carry source construction
contributors to each evaluated vertex. These formulas are hypotheses, not
anatomical facts, and may consume the recorded refinement budget if wrong.

### Quantitative checks fixed before attempt 0

Per-case scale S=max(2*lower_pelvis.rL, hip-centre spacing, hip-to-knee length).

- All levels: valid indexing, finite coordinates, connected orientable welded
  topology, five declared boundary loops, full ownership and lineage coverage;
  edge length >1e-7*S and triangle area >1e-10*S^2. These are numerical
  degeneracy checks, not anatomical quality scores.
- No non-adjacent lower-body self-intersections at L0/L1/L2. Report inherited
  upper-only failures separately; they prohibit whole-root success claims.
- At L2, affected lower-body adjacent-face normal angle <=60 degrees and
  consistent orientation of the two triangles in each quad. L0/L1 normal
  angles are diagnostic, not inherited candidate acceptance thresholds.
- Each evaluated thigh exit: centroid within 1e-6*S of E; plane residual
  <=1e-6*S; outward normal within 5 degrees of d; surface-induced outward
  co-normal within 25 degrees of d. Frame orthonormality tolerance 1e-10.
  Projected half-spans must be 0.75..1.05 times source r_x/r_z, allowing the
  declared eight-control subdivision contraction without erasing dimensions.
- At H, rays along +/-X and +/-F must have odd distinct intersections with
  the actual side's skin and nearest distance 0.6..2.5 times its respective
  source radius. Report the analogous section 0.1 hip-to-knee length above H
  diagnostically. This tests the centre's structural relation to skin rather
  than a moving metadata marker. It is not a bone-clearance or tissue model.
- Source-centre perturbations must move the evaluated exit centroid by the
  same vector within 1e-6*S; direction changes must rotate the exit axis with
  the source direction. Increasing pelvic width must leave exits fixed and
  increase an outer above-H section radius by at least 1e-4*S. Changed source
  cases must change serialized evaluated coordinates, not just metadata.
- Repeat the final evidence under PYTHONHASHSEED=17 and 29, requiring identical
  meshes, numeric reports and PNGs after excluding declared runtime paths.

These thresholds guard this specific candidate's integrity and structural
response. They do not promise final anatomy, deformation or realism. Numerical
success remains insufficient without direct visual inspection.

Retain ownership, welding, winding, finite/nondegenerate geometry, manifold
connectivity with declared open ports, non-self-intersection, deterministic
output and inspectable input-to-evaluated-surface causality. Do not retain the
predecessor's exact control counts or exact affected-vertex cardinalities as
universal requirements. Quantitative checks and scales are fixed before the
initial run. Report L0, L1 and L2 separately rather than equating a coarse cage
fold with visibly folded final skin.

Reject apparent bulb-mounted thighs, sideways attachment instead of descent,
implausible pelvic/groin shape, abrupt abdominal transitions, pinching, folds
or intersecting skin even if numerical checks pass. Actual opaque shaded
surface views are primary evidence. Capture matched front, side and rear
three-quarter views; use underside and lineage/frame overlays only to explain
that same surface. Render numerically rejected meshes where finite valid
indexing makes it safe; label them REJECTED and keep them separate from any
passing candidate. Never hide a failed result behind publication gates.

Every attempt executes from its own captured source tree and concrete inputs,
not the mutable worktree. Record file hashes, runtime/dependency identities,
commands, exact output inventory and any before/after drift. Capture dependency
files, not only a Git OID. Output manifests distinguish technical outcome,
direct visual judgment and human acceptance. Large meshes and images stay in
the local cache, not Git. No gallery publication, network effects, push or
merge is authorized. Return local matched image artifacts to Ben.

Preserve the failed pre-filter's scripts and diagnostics, recovered current
dependency snapshots and explicit concurrency/missing-image limitations.
Recovered dependencies are not falsely labelled original executing code.
Preserve unrelated pending local review fixes, including the protected dirty
observation inbox.

If successful, recommend a separately authorized small hip-bend/binding test
before further body expansion. Static success does not establish animation or
tissue-deformation quality.

## Reproduction

All Python geometry, tests and rendering use the existing pinned environment:

```bash
experiments/current-form-surface-preview/surface_preview_launcher.sh SCRIPT ARGUMENTS
```

The first geometry/render capture uses `preserve_evidence.py --snapshot` to
capture this source tree and the pinned runtime into
`/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-0-snapshot`.
Run its captured `preview_only.py --inputs inputs.json --output ABSENT_PATH`
through the captured launcher, with `CK_CURRENT_FORM_SURFACE_PYTHON` pointing
to the captured `runtime/bin/python` and `PYTHONHASHSEED=17`. Input SHA-256:
`23132147711c792d3617963323d29e86323ed8539c64dbe9f18b32ce6be43db1`.
This first phase deliberately claims no numeric pass. Checks and their final
runner are captured separately after preflight corrections; their replay must
use identical construction, rendering and concrete input bytes.
Preservation scripts using
only the standard library may use `python3`; never use it for Pillow/NumPy work.

## Results

Attempt 0 captured and rendered all twelve cases. Parent visual inspection
rejects the pronounced pelvic shelf and elongated tall-profile pelvic region.
The initial numeric runner rejected its own nested checker report at depth 8;
`attempt-0-checked` preserves these tool errors, not geometric conclusions.
Evidence repair batch 1 raises only that serialization bound to 64 and replays
the identical construction, inputs and checks. Geometry remains unchanged.
Budget consumed: 1 initial run, 2/2 geometric refinements,
2/2 evidence-tool repair batches reserved. The first replay exposed two further
checker defects: the imported collision module lacked Python module registration,
and a generic port-name fallback selected neck/arm instead of thigh exits.
Evidence repair batch 2 fixes only those adapters and preserves the first replay
as tool-invalid. No geometric result is inferred from those false failures.

### Refinement 1 (declared before execution)

Actual L2 thigh-exit checks pass on all six mandatory attempt-0 surfaces.
The inherited j1 axial row switches abruptly between a lateral upper-pelvis
selector and a central lower-abdomen selector, with a boxy superellipse.
Hypothesis: this contributes to the visible pelvic shelf independently of the
now-controlled thigh descent. Replace only this row's formula: u=(i-2.5)/2.5,
q=k-1, t=u²; blend lower-abdomen radii and its centre (y averaged with upper
pelvis) toward upper-pelvis radii/centre with t. Normalize (u,q) onto an ellipse
instead of the previous exponent-2.6 section. No topology, source input, socket,
transition rows, exits, upper context j>=2, evaluator or threshold changes.
This spends refinement 1; it is not yet evidence of anatomical improvement.

### Refinement 2 (declared before execution; final geometry budget)

Direct inspection of all six attempt-1 bodies shows a reduced shelf, but the
high arch between short descending thigh stubs remains visually unconvincing.
Test a lower medial socket while retaining the outer wrap height: with
w=(1+side_sign*a)/2, socket y=H.y+w*(0.50*D+0.25*r_y)-(1-w)*0.10*length.
All other attempt-1 rules and every input remain unchanged. This is a shared
construction change, not an evaluated-surface repair. It tests whether the
existing neighbouring faces can form a credible lower central transition.
It may expose a conflict with the declared individual-side H ray test; that
test is not relaxed. Stop after this candidate's evidence, passing or failing.

Parent has inspected all six mandatory attempts' matched primary views.
Attempt 2 is rejected: the inner opening is lower but the broad bridge/short
thigh-root proportions remain unconvincing, especially in the five inherited
profiles. The synthetic human is more plausible locally, not a whole-body pass.
Attempt-2 source-centre medial rays hit no own-side hip triangles in every main
case. Diagnostic rays against the whole lower surface instead hit the opposite
outer skin once (neutral distance 2.329349334160044; human 0.2838537160302547).
This supports a continuous pelvic envelope, rather than demonstrating H lies
outside the body. It does not replace or pass the frozen individual-side gate.
Final full checks and deterministic repetition are complete; no geometry remains
authorized. All further implementation requires a new user decision.

### Evidence locations and interpretation

All paths below are under
`/home/ben/.cache/creature-kernel/pelvis-thigh-transition/`:

| Attempt | Captured code/runtime | Complete numeric evidence | Parent surface judgment |
| --- | --- | --- | --- |
| 0 | `attempt-0-final-check-snapshot` | `attempt-0-final-check/run-report.json`: all 11 valid cases pass; invalid case rejects | Reject: pelvic shelf and high arch |
| 1 | `attempt-1-snapshot` | `attempt-1-checked/run-report.json`: all 11 valid cases pass; invalid case rejects | Shelf improved; shared anatomical quality still insufficient |
| 2 | `attempt-2-snapshot` | `attempt-2-checked-seed17` and `attempt-2-checked-seed29`: all 11 valid cases fail only the declared H-containment condition; invalid case rejects | Reject at final budget; broad bridge/short-root appearance remains |

`attempt-N-preview/CASE/surface.png` retains matched front, side and rear
three-quarter surfaces for every input, including rejected input diagnostics.
The numeric run case directories also retain full-root context, lower-crop,
underside and separate source-intention overlays. Context is not a shoulder
reappraisal. No whole-root, rigging, bend or animation quality claim is made.

The final closure uses the captured `closure-snapshot` helper
`finish_evidence.py --first .../attempt-2-checked-seed17 --repeat
.../attempt-2-checked-seed29 --output .../final-rejected` with the captured
runtime and launcher. It compares mesh/PNG bytes and numeric reports, then
renders the stored final meshes with an explicit parent rejection label.
It does not construct or repair geometry.

Executing geometry identities, SHA-256 of `construction.py`:

- Attempt 0: `6e8b5157f58dc8f1d02be3d11c19f64eace374b74667a0d21f36f62a87782ecb`.
- Attempt 1: `b65fb1f00df90351e3e31bcc0a3ac382349b1e8cea016b35c5e974a9c74d1bb8`.
- Attempt 2 and closure: `7fd457e2206165eb5e404ce81732f4157234a2e13a64008d96ae75d6abcf5cdb`.

Each snapshot manifest records all copied source and installed runtime files.
The copied venv includes Python executable and site-packages; the host OS,
standard-library base and system libraries remain an explicit reproducibility
boundary, not a fully hermetic operating-system image. Earlier failed pre-filter
files remain in `failed-prefilter-20260905`, with original-vs-recovered provenance
and missing-render limitations retained in `results/prefilter-closure.json`.

The tall/slender source profiles lower H and K together without extending their
hip-to-knee distance. Their elongated pelvic region therefore cannot be
attributed solely to the new surface formula. The generator did not retune these
inputs. No result proves arbitrary morphology generalization or that every
one of the 92 available dimensions has been individually verified.

Luna performed bounded input, construction, checks, rendering and evidence
implementation; Sol-medium supplied one independent pre-run code audit. The
Astra parent settled both shared refinements, inspected critical formulas and
all six mandatory actual-surface sets for each attempt, and owns rejection.
The preserved tool failures also show the synthetic tests initially missed
real report nesting, port selection and dependency-import integration defects.
They are evidence limitations/fixes, not anatomical failures.

### Final result and next decision

All eleven valid final cases pass topology/lineage, finite and nondegenerate
geometry, zero lower intersections at L0/L1/L2, L2 fold/quad orientation, and
source-linked exit/frame/span checks. All six prescribed perturbation responses
pass, including correct rejection of the incompatible input. All eleven valid
cases fail the unchanged individual-side H-containment requirement. The negative
fixture has real intersections/folds; its detailed collision inventory is
truncated at the helper's reporting cap and is explicitly incomplete, not a
precise total or a pass.

Final repetition under hash seeds 17 and 29 is exact: **180/180 mesh/PNG artifacts
match byte-for-byte**, and all 14 numeric/input comparisons match. See
`final-rejected/determinism-report.json` and `final-rejected/output-manifest.json`
(manifest SHA-256 `2df9357a4ad08e416e96440addabf3a1bddae4dd61c2a38d965c0e379db1b0bc`).
All six primary final view sets are at `final-rejected/CASE/surface.png`, labelled
REJECTED - FINAL BUDGET; underside views are separate. No passing gallery exists.

Validation: 33 synthetic tests passed; final actual-surface runs and repeat
checks completed. Documentation/whitespace validation also passed. Budget used:
initial candidate plus 2/2 geometric refinements and 2/2 evidence-tool repair
batches. No push, merge, gallery publication, rig or body expansion occurred.

Recommendation (not authorization): preserve the source-linked transition, but
do not proceed to bending yet. A next bounded scope should first reconcile
pelvic/hip source proportions and define containment of the coherent pelvic
envelope rather than requiring an isolated tube around each H. Re-test coarse
pelvic/groin form with human and contrasting anthropomorphic inputs before a
small bend/binding checkpoint. Neither changing this failed trial's verdict nor
replacing topology is justified by these results. Fine anatomy and animation
quality remain unproved; subdivision or rendering alone cannot supply them.

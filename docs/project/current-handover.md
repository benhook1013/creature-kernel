# Current operational handover

Snapshot: 2026-08-25 NZST

This is a concise operational handoff for continuing the current runway in the
Codex app. It is not a new authority owner: `docs/project/status.md` remains
the canonical owner of the active runway, and the required reading order in
`AGENTS.md` still applies.

## Where to continue

- Primary checkout: `/home/ben/src/creature-kernel` — `main` and
  `origin/main` are at merged PR #112 commit
  `80179614ea693cd45d55743d1d83d044c653a08f`.
- Active worktree:
  `/home/ben/src/creature-kernel-worktrees/structural-embodiment-bridge` — branch
  `codex/structural-embodiment-bridge`, containing checkpoint implementation
  commit
  `aed81e494803cefcc1681301609ac12e8e1cf67d`.
  [Draft PR #114](https://github.com/benhook1013/creature-kernel/pull/114) is
  open, draft, mergeable, and stacked on PR #113; all three PR #114 checks
  passed at the pre-clarity head. The clarity follow-up below has passed
  focused local validation but has not received its current-head CI validation
  yet.
  It reaches the named human checkpoint at
  `http://localhost:8765/review/shared-pose-structural-embodiment-gallery`.
  PR #114 and PR #113 remain unmerged pending Ben's explicit merge
  authorization. Ben's qualified visual appraisal below is not that
  authorization.
- [Draft PR #113](https://github.com/benhook1013/creature-kernel/pull/113)
  is mergeable and draft; all three current CI lanes passed, but it remains
  unmerged pending Ben's explicit merge authorization. Ben's disposition
  accepts its gallery only as bounded exploratory evidence that source-authored
  controls and procedural field routes cover the required regions and produce
  connected whole-body surfaces across the current display variants; it does
  not accept visual region readability or form quality. That disposition is
  not merge authorization, and no further cosmetic repair of the disposable
  candidate is planned.
- [PR #112](https://github.com/benhook1013/creature-kernel/pull/112) merged at
  `80179614ea693cd45d55743d1d83d044c653a08f`. Its authored pelvis/leg profile
  is merged predecessor evidence, not completion or visual-quality acceptance.
- [PR #111](https://github.com/benhook1013/creature-kernel/pull/111) merged at
  `6df6168cdf27477f3b275441616ab4cfd0ab814d`. Its authored arm profile is
  merged predecessor evidence, not completion or visual-quality acceptance.
- [PR #110](https://github.com/benhook1013/creature-kernel/pull/110) merged at
  `a45920df1322bafbbd56ea6939837f8b0b9b8b33`. Its authored head/neck profile
  is merged predecessor evidence, not completion or visual-quality acceptance.
- [PR #109](https://github.com/benhook1013/creature-kernel/pull/109) merged at
  `52b88370f2f81b3c2cc937da7cc34f83d4481a7a`. Its authored torso profile is
  merged predecessor evidence, not completion or visual-quality acceptance.
- [PR #107](https://github.com/benhook1013/creature-kernel/pull/107)
  merged at `f69a0a235152e72bd51279634cf3e8618d776e3f`. It retains the exact
  consumed producer envelope lineage in surface reviews while preserving all
  parked EXP-0002 candidate-closure bytes; it makes no displayed form-quality
  claim.
- [PR #106](https://github.com/benhook1013/creature-kernel/pull/106)
  remains merged at `c94deb0`; it introduced the distinct authored-form source
  and v5 dimension lineage without changing displayed geometry.
- [PR #103](https://github.com/benhook1013/creature-kernel/pull/103)
  merged at `f30bdb2` after all three required CI checks passed. Its merge
  retains useful plumbing and comparison evidence; it does not accept the
  disposable surface as a form-quality success.

The current named human checkpoint is the shared-pose structural embodiment
gallery, an exploratory candidate toward Stage 2. Its frozen four-profile set
satisfies the Proposed product baseline's qualitative profile envelope and is
distinct from the earlier display variants. Generated, not illustrative,
artifacts show the neutral surface with its skeleton and joint/bone overlay, complete
skin-weight/influence evidence, one identity-bound deterministic semantic
pose-transform payload applied without IK or contact solving, the posed surface
and skeleton, neutral/posed collision proxies, and source/build/scenario
lineage for every frozen profile.

Ben's qualified 2026-08-25 visual appraisal is that the shared-pose structural
result "looks good". The only confusion was that the `POSED SKIN + SKELETON`
side panel appeared not exactly side-on because the skeleton looked skewered.
The verified explanation is that `side` is exact orthographic, while the
skeleton rows are non-depth-occluded x-ray overlays. The visible clarification
is implemented in the active working tree: the column is labelled `side (exact
orthographic)`, skeleton rows are labelled `(X-RAY OVERLAY)`, and the publisher
instructions and README explain that the overlay is not depth-occluded.
Focused assertions cover the clarification; geometry and camera behaviour are
unchanged.

The fail-closed gate requires a rooted acyclic hierarchy, complete
semantic-Joint-to-derived-bone mapping, finite/nonnegative/normalized influence
coverage for every vertex, finite nondegenerate lineage-bound proxies with
neutral/posed transforms, deterministic rerun identity, shared operations, no
per-profile patches, and complete results for every profile; any failed or
inconclusive profile keeps the checkpoint open. The derived bone hierarchy,
mapping, skinning method, provisional topology, and proxies are candidate-
scoped evidence only. Ben judges skeleton inhabitation, coherent shared-pose
reading, gross skin following without severe collapse/twisting/detachment, and
proxy coverage/following. The checkpoint does not seek realistic muscles or
anatomy, final surface/topology, contact response, localized deformation
quality, runtime performance, engine/solver/rig-format selection, IK/gait/
balance, or VR/tracking implementation.

The completed bounded structural-embodiment bridge prerequisite defines its
entrypoint, admitted source/neutral-surface inputs, derived outputs, and
reproducible artifact boundary. Stop for evidence and main-thread reevaluation
if semantic frames do not map cleanly, disposable topology cannot support
trustworthy weights, objective checks fail or remain inconclusive, bespoke
profile patches are required, or a material production topology/backend/
engine/anatomy choice becomes necessary. Do not answer those triggers with
more outer-field cosmetic tuning or unnecessary intermediate visual gates. The
human stop gate is now Ben's explicit merge authorization for PR #113 and PR
#114; the qualified appraisal above does not infer or grant that authorization.

Open the active worktree in the Codex app to continue the runway.
Read `AGENTS.md` in the required order, then this handover and the linked
[current status](status.md).

PR #109 was a direct, internal, reversible torso prerequisite and made no
form-quality acceptance claim. Its producer v7 added a source-authored
seven-section pelvis/torso axial profile, two identity frames, seven landmarks,
21 asymmetric lateral/anterior/posterior radii with exact indexed provenance,
and four shared variant projections. Baseline guide v6 retained both depth
sides and lineage. Successor v4 / region v8 consumed a continuous asymmetric
rounded-superellipse torso sweep. The publisher cross-bound producer, guide,
and successor lineage and validated real bundles. The comparator added
Previous/Next controls, arrows, click-to-advance, and zoom.

PR #110 contains the completed internal, reversible source-authored head/neck
prerequisite and remains historical evidence from the then-active authored-form
expressivity gallery runway. Producer v8 adds source-authored
head/neck profile v1: eight indexed stations, seven named
branched connections, head/neck identity frames and landmarks, 24
lateral/up/forward radii with provenance, and four shared variant projections.
Baseline regional guide v7 carries exact profile and compatibility lineage.
Successor v5 / region v9 consumes two reusable vertical neck/cranium and
forward muzzle route sweeps, full three-radius station volumes, and exact
lineage without per-variant tuning. The publisher cross-binds producer,
guide, and successor, retains compact exact producer evidence within the
existing bounds, and completed real end-to-end publication with four groups
and eight assets. Consolidated tests, two fresh browser/operator hands-on
trials, and the final fresh adversarial code review passed their merge gates;
the review's one documentation defect was corrected and its two non-contract
concerns were dispositioned. No user appraisal is requested because this is
an internal region slice, not the complete authored-form gallery.

PR #111 contains the completed internal, reversible shoulder/arm
authored-control prerequisite and remains predecessor evidence on the runway.
Producer v9 carries `authored_arm_profile` v1 with a
bilateral five-station profile per side, 10 landmarks, four identity frames,
30 lateral/up/forward radii, and shared neutral, broad, lean, and
depth-forward factors. Guide v8 projects the exact authored stations and
retains an authored anisotropic upper-arm-owned elbow mass. Successor v6 and
region
`successor-torso-shoulder-head-neck-arm-limb-extremity-tail-profile-sweeps-v10`
consume four arm routes plus two leg sweeps, a shared upper-arm-owned elbow
seam, and all 30 radii; the successor has no arm root bridge, old underarm
supports, or per-variant station tuning.

The real publication retains the exact 143586-byte v9 producer envelope using
XZ/Base64 and a 7290-character subject context under the unchanged 8192
character cap. It produced four groups and eight assets at
`/tmp/ck-authored-arm-publisher.LFm2eK/reviews/authored-arm-v9`. Main-thread
internal visual inspection and two fresh hands-on trials passed the
arm-focused connectivity, spike/lobe, and variant-response checks, along with
the browser, evidence, and HTTP scenarios. No human appraisal was requested:
this merged slice is not the complete authored-form gallery and makes no
form-quality acceptance claim.

The arm-slice checks include 415 Rust workspace tests (47 CLI and 368 core),
52 successor tests, 34 publisher tests, and 25 browser/parity tests passing;
the unchanged baseline suite's 56 tests were already green. Rust formatting,
Clippy with warnings denied, documentation validation, and `git diff --check`
pass. The final adversarial review found one XZ decoder-memory blocker, which
is fixed with an explicit 128 MiB decoder limit and a passing malicious-header
regression. All three required CI lanes passed before PR #111 merged.

PR #112 is merged at `80179614ea693cd45d55743d1d83d044c653a08f`. Its completed
internal, reversible authored pelvis/leg control slice is merged predecessor
evidence and makes no form-quality acceptance claim. Producer v10 carries
`authored_leg_profile` v1 with bilateral
five-station routes, 10 landmarks, four identity frames, 30 radii, and four
shared variant factors. Guide v9 projects the exact anisotropic authored leg
segments, with a thigh-owned knee, shin-owned hock, and preserved foot seam.
Successor v7 / region v11 consumes exactly two authored leg routes and all
radii, retains the existing feet, has no legacy duplicate leg mass, and keeps
exactly four temporary thigh-root/hip bridges. The publisher binds exact v10/
v9/v7 lineage: 175587 raw evidence bytes, 5732 XZ bytes, 7644 Base64
characters, SHA-256
`8702f81b52690ee6c1d32e5b4a6e50ded81e7b09398b9bd2560a7f00b8547adc`, and a
final subject context of 8128 Python-JSON characters (within the 8192 cap).
It successfully published the temporary four-group/eight-image review at
`/tmp/ck-authored-leg-publisher.RM32b9/reviews/authored-leg-v10`.

PR #112's completed gates include 419 Rust workspace tests (51 CLI and 368
core), Clippy/fmt, 107 full visual-review tests, 61 baseline-guide tests, 56
successor tests, 35 publisher tests, and documentation/diff checks. Two fresh
hands-on trials
passed publication, browser interaction, asset integrity, and leg-focused
visual scenarios. The final fresh adversarial review found one contract
mismatch: positive but descending leg-station coordinates were accepted by
the producer and publication boundaries even though the surface consumer's
distal-fraction mapping requires inclusive `[-1, 0]`. That mismatch is fixed
at every boundary with explicit malformed-input regressions; the affected 34
producer, 26 publication/browser-parity, 61 baseline-surface, and 35 publisher
tests pass. Main-thread visual inspection found connected
pelvis/thigh/knee/shin/hock/foot across all four variants, with no point
spikes, detached islands, or duplicate bulb masses; the lower foot chain
remains coarse and is not accepted final quality. This merged slice is an
internal reversible prerequisite, not the complete authored-form gallery, and
no Ben appraisal has been requested. The then-current worktree candidate
reached the former complete authored-form expressivity gallery checkpoint; its
current local diagnostic checks, corrected-route hands-on trials, and final
fresh adversarial review are historical evidence. It was not approved as final
form quality or a production choice. This is historical PR #113 evidence; the
current runway targets the structural embodiment gallery described above.

## Historical PR #113 surface-gallery evidence

The historical PR #113 candidate's exact foot route is `hock -> metatarsal midpoint ->
pad -> pad-toe midpoint -> toe`: the hock is shin-owned, the other four
stations are foot-owned, and the route carries full lateral/up/forward radii,
outer caps, four spans, and exact producer/guide/successor lineage and
cross-binding. The visual-review diagnostic redesign changes the evidence
layout only; it does not change final skin geometry.

The new immutable checkpoint ID is
`authored-form-expressivity-exact-field-components-checkpoint-v2`, with
persistent URL
`http://localhost:8765/review/authored-form-expressivity-exact-field-components-checkpoint-v2`.
Each of the eight baseline/successor images is now a 3x3 sheet with columns
`front`, `side`, and `three-quarter`, and rows `CONTROL GUIDE` (explicitly not
geometry), exact consumed pre-union field-component shells (52 baseline, 27
successor), and neutral final skin. The earlier no-suffix
`authored-form-expressivity-exact-field-components-checkpoint` session is
preserved as historical evidence but superseded because its successor torso
used aggregate rather than exact loft sampling bounds. Corrected v2 uses the
exact loft bounds. Pixel-crop checks prove that every control-guide and
final-skin row is byte/pixel identical between the superseded session and v2;
the geometry and final skin did not change.

Pre-redesign publication measurements are retained as historical evidence:
compact producer envelope 190444
bytes; XZ 6244 bytes; Base64 8328 characters; producer SHA-256
`c48ed001b910549dd1da296bb4c664a4de29cad4838b42403b15aa97773a6d3e`; XZ
SHA-256 `5c42afe0b599b3afff52d687c3e46c9f4ae7d31f7d8e426d0b17e55858331161`;
subject context 8812 bytes; subject-context SHA-256
`0210c5f225869d9030ff82a2898f122be21b4da328dcb668e0b83a674f486fb7`.
Strict decode equality passed for that pre-redesign candidate. These
measurements remain historical and do not describe the corrected v2 session.

This was the former human checkpoint. Publication machinery is evidence
plumbing, not acceptance: PR #113 remains unmerged as a mergeable draft pending
Ben's explicit merge authorization, and this disposition is not that
authorization. The former appraisal concerned the rendered spatial form and
variant response: whether the authored torso, head/neck, shoulder/arm,
pelvis/leg, and digitigrade foot transitions read as controlled continuous
skin rather than joined procedural masses across the four variants.

The hands-on operator trial also found that LAN read-only mode still displays
an enabled Save response control even though the server rejects writes. No
response was submitted or created. This pre-existing UI/usability mismatch is
deferred unrelated cleanup, not a pelvis/leg geometry or publication blocker.

The non-blocking rejected-POST secondary-400 logging concern is deferred
unrelated usability cleanup, not an arm blocker. The PR #113 worktree candidate
is the historical authored-form gallery described above; it is not the current
named human checkpoint.

PR #109 also contained Ben-approved neutral public-facing wording cleanup and
accepted MIT OR Apache-2.0 licensing DR-0014. That ancillary work does not
change the active runway. Root license files, README, and CONTRIBUTING carry the
current terms; Cargo package metadata is deliberately deferred because the
parked Phase 3 evidence closure exact-binds the affected manifest bytes.

The current named human checkpoint is the shared-pose structural embodiment
gallery described above. The complete authored-form expressivity gallery is
historical bounded proof, and no further cosmetic repair of that disposable
candidate is planned.

## Gallery and service

- New immutable checkpoint ID: `authored-form-expressivity-exact-field-components-checkpoint-v2`
- Persistent URL: `http://localhost:8765/review/authored-form-expressivity-exact-field-components-checkpoint-v2`
- Persistent root: `/home/ben/.cache/creature-kernel/visual-reviews`
- The earlier no-suffix
  `authored-form-expressivity-exact-field-components-checkpoint` session is
  preserved but superseded evidence because its successor torso used aggregate
  rather than exact loft sampling bounds. The older
  `authored-form-expressivity-gallery-checkpoint` ID is pre-redesign evidence;
  neither is the current checkpoint.
- The new persistent session exists at
  `/home/ben/.cache/creature-kernel/visual-reviews/authored-form-expressivity-exact-field-components-checkpoint-v2`
  with `review.json`, exactly 8 PNGs, and no `response.json`.
- The systemd user service at
  `/home/ben/.config/systemd/user/creature-kernel-visual-review.service` was
  restarted and is enabled/active on port 8765 in LAN read-only mode from the
  active worktree. The page and API return HTTP 200; all eight API assets
  return HTTP 200 and their served SHA-256 values match the on-disk v2 assets.
- Playwright persistent-route smoke loaded all eight assets at `1800x1500`,
  switched baseline/successor with arrow keys, and found no console or request
  failures. Pixel-crop checks prove the control-guide and final-skin rows are
  byte/pixel identical to the superseded no-suffix session. Current local
  diagnostic results are: baseline full suite 68 tests passed; successor full
  suite 61 passed; full visual-review suite 113 passed via the repository's
  native-temp launcher; the full affected publisher rerun passed 39 tests;
  Python compilation, JavaScript syntax, documentation validation, and `git
  diff --check` passed. A raw system-Python visual-test attempt failed exactly
  two WSL/Windows TEMP parent-swap tests; the repository launcher corrected that
  environment and the suite then passed 113 tests. Two fresh Luna/high
  corrected-route hands-on trials found no correctness blocker. Their first-use
  notes were narrow fit text/details, long metadata, and a description that
  says final skin rather than explicitly neutral although the PNG labels say
  neutral. The adversarial notes were modest variant differences in some front
  views and the pre-existing enabled Save control in LAN read-only mode; no
  Save response was submitted or activated. The final fresh new-code
  adversarial Luna/xhigh review is complete: it found torso-bound and
  publisher-claim validation gaps, which were corrected with exact loft bounds
  and regression coverage, plus bounded validation of the full schema/count,
  owner provenance, recipe histograms, and finite ordered `±100` sampling
  bounds. The publisher does not independently duplicate NumPy/SciPy geometry
  or prove rendered pixels, and this does not select a permanent backend. All
  three current PR #113 CI lanes passed; PR #113 is mergeable/draft and
  unmerged pending Ben's explicit merge authorization.

Useful local checks:

```bash
systemctl --user status creature-kernel-visual-review.service
systemctl --user restart creature-kernel-visual-review.service
```

Because LAN mode is read-only, capture Ben's visual feedback in chat or project
docs; do not expect the gallery to create `response.json`.

## Historical PR #103 disposition and former next checkpoint

Ben's current appraisal is that the v6 disposable successor demonstrates
deterministic connected whole-body generation and plumbing across variants,
but does not demonstrate convincing complex skin/form expressivity. No further
aesthetic polishing of this disposable consumer is planned.
In the project's 2026-08-22 Codex chat, Ben said the goals-and-roadmap write-up
"sounds good" and that "your next visual checkpoint also sounds good," then
instructed, "also we have agreed on your goals roadmap discussion and next
visual checkpoint, ensure that info is baked into repo now too." This approves
the direction to stop aesthetic polishing of this disposable consumer and
prepare the next authored-form expressivity gallery; it did not by itself
authorize the merge. PR #113 fulfilled that historical direction, which Ben's
2026-08-24 disposition supersedes with the structural-embodiment runway above.

On 2026-08-23 Ben said, "i dont care about 103 do what you want," delegating
PR #103's disposition to the main thread. The main thread selects merge after
the required review and checks because the branch retains useful deterministic
generation, publication, and comparison plumbing as a bounded baseline. This
authorization supersedes the earlier merge hold; it does not turn the
disposable surface into a successful form-quality proof.

Ben's exact feedback on the displayed PR #103 successor artifact was: "its got
pointy bulges under the arms again." This remains an artifact-scoped rejection;
no form-quality approval is implied. The bounded response is the
shared v6 successor-generator selection of exactly one distal `deltoid-sweep`
span (index `1`) per side, with anterior/posterior supports retained only as
guide metadata. Fixture-specific tuning, guide derivation, sampling, and
smooth-union parameters remain unchanged.

The regenerated v6 gallery was the served candidate. Its four baseline
PNGs are byte-identical to the rejected gallery and all four successor PNGs
changed. One independent static-capture trial judged the reported lobes
removed; a second still saw a smaller angular root contour. Follow-up isolation
showed that removing the distal deltoid span did not remove that contour, while
removing the temporary upper-arm bridge produced a visibly thinner attachment.
The bounded v6 correction and its evidence are retained as the basis for Ben's
appraisal above, not as a claim of form-quality approval.

The displayed v6 candidate remained coarse. The prior pointy-underarm and
related point observations are artifact-specific feedback on that displayed v6
candidate; they remain scoped to that artifact and are not durable geometry
prescriptions for this successor.

The former named human checkpoint was the complete authored-form expressivity
gallery across the agreed controls and regions. Its local gates are historical
evidence. Ben's 2026-08-24 appraisal of the PR #113 immutable
`authored-form-expressivity-exact-field-components-checkpoint-v2` gallery's
successor v9 accepts only that source-authored controls and procedural field
routes cover the required regions and produce a connected whole-body surface.
Its neck is visibly occluded or lost, its torso and pelvis read as rounded
rectangular/blocky, and the overall body is not convincing realistic or
anatomical skin; visual region readability therefore remains failed or
inconclusive. These limitations are scoped to this disposable candidate, not
canonical geometry prescriptions. No further cosmetic repair is planned.

The current named human checkpoint is the shared-pose structural embodiment
gallery defined near the top of this handover and canonically governed by the
Active runway. Its frozen-profile, fail-closed artifact, human-judgment,
candidate-scope, non-goal, and reevaluation boundaries apply here without
creating another surface-polish checkpoint.

The former checkpoint required richer source-authored dimensions, landmarks,
and profiles to drive shared region-appropriate generator operations across
all four fixed variants, with source provenance and reproducible evidence.
Representative torso, head/neck,
shoulder/arm, pelvis/leg, and digitigrade foot transitions must read as
controlled continuous skin rather than joined procedural masses. Do not use
per-variant or per-fixture patches or a handcrafted base mesh. This remains a
bounded exploratory expressivity checkpoint, not proof of a finished
morphology family or production surface system.

For that former checkpoint, its immutable evidence retained either
the exact producer envelope used by the checkpoint or an integrity-bound
authored-dimension, landmark, frame, and descriptor-role lineage projection,
including indexed authored provenance. The existing source hash alone is not a
self-contained lineage record.

The current fixture's exact squared reference length is `1`. Before a future
large-coordinate fixture exceeds JavaScript's exact-integer domain, align or
tighten the producer/publication/surface/browser numeric bounds. That trigger
is not active for this checkpoint.

The PR #113 surface candidate is historical bounded proof, not the current
appraisal gate, and publication is not acceptance. Rigging, contact,
deformation, VR integration, and permanent backend selection remain outside
the current exploratory scope except for the generated evidence required by
the structural embodiment checkpoint.

The required Rust CI workflow still exercises the parked Phase 3 freeze
manifest, whose 47-path candidate closure includes the current core crate
module surface. PR #107 leaves those frozen paths byte-identical and retains
the consumed producer lineage in unfrozen developer tooling. Treat a
future need to edit a frozen core path as a trigger to resolve the CI/freeze
boundary explicitly, not as authority to regenerate or rebind EXP-0002.

## Evidence and limits

Corrected v2 checkpoint status: the pre-redesign publication measurements and
hashes, strict decode equality, and earlier gates remain historical evidence.
The corrected v2 session, service, HTTP, asset-integrity, pixel-crop, and
Playwright route checks are live-verified as recorded above; all three current
PR #113 CI lanes passed, and the PR remains mergeable/draft and unmerged
pending Ben's explicit merge authorization.

### Historical arm-slice evidence

Current arm-slice checks known: 415 Rust workspace tests (47 CLI and 368 core),
52 successor tests, 34 publisher tests, and 25 browser/publication parity tests
pass; the unchanged baseline suite's 56 tests were already green. Rust
formatting, Clippy with warnings denied, documentation validation, and
`git diff --check` pass. The final adversarial review found one XZ decoder-memory
blocker, which is fixed with an explicit 128 MiB decoder limit and passing
focused/full publisher regressions. All three required CI lanes passed before
PR #111 merged. The real publication produced four groups and eight assets
with no response artifact. Two fresh hands-on trials are complete. They
exercised exact evidence and asset bindings, HTTP success and failure paths,
modal click and keyboard navigation including wrap and Escape focus return,
and browser console/network behavior. Both found the arm-focused successor
meshes connected and visibly variant-sensitive; neither result constitutes
visual acceptance or completion of the named gallery checkpoint.

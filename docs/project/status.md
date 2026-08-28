# Project status

Status date: 2026-08-28

## Phase

Exploratory executable prototype and semantic-contract integration. The
foundation governance and the remaining product, specification, and architecture
proposals remain provisional; the reviewed semantic-foundation directions in
DR-0002/0006/0011/0012 are accepted. Earlier CK-KICK-012 and CK-KICK-013
readiness/publication work remains recorded below; the `Active runway` section
governs what resumes next.

## Active runway

Execution state: the shared-pose structural embodiment gallery reached its
named human checkpoint and PR #114 merged as squash commit
`577b336e0dd007dca6c6e05669f54d4c98291f17` on 2026-08-25. PR #115 then merged
on 2026-08-26. PR #116, [“Admit structural gallery evidence into pinned Godot
probes”](https://github.com/benhook1013/creature-kernel/pull/116), merged at
2026-08-28T06:40:34Z. PR #117 merged by squash at 2026-08-28T08:39:44Z as
`5fb4ce6668f34386e865154bab13e03fefd04e75`; primary `main` and `origin/main`
were verified at that commit and clean when the new worktree was created. The
CodeRabbit App and repository configuration remain live, with automatic reviews
disabled. The updated direction is to launch hosted and committed-diff CLI
review in parallel as one final-readiness cycle, keep it advisory and
non-gating, avoid pushing while hosted reviews hold an immutable head, and run
bounded follow-up cycles until findings taper. Creature Kernel's limits are
independent of FireMUD.

The visual-review systemd service is active from `/home/ben/src/creature-kernel`;
the stable structural review remains
`http://localhost:8765/review/shared-pose-structural-embodiment-gallery`.

The active worktree is
`/home/ben/src/creature-kernel-worktrees/godot-package-input-carrier` on branch
`codex/godot-package-input-carrier`, based on `5fb4ce6`. The current provisional
candidate adds a deterministic, canonical, exactly-two-avatar experiment input
carrier with ordered experiment instance IDs and exact gallery/profile/shared-pose
provenance. The Python skeletal runner revalidates the carrier before and after
launch; the Godot script consumes its validated projection and reports the
exact carrier identity summary it received. This is disposable experiment
evidence only: it is not a runtime package schema, durable artifact identity,
adapter activation, compatibility promise, Readiness 3 result, host commitment,
performance/contact/deformation result, or human visual checkpoint. Carrier
reads, structural-gallery preflight, and publication are descriptor-anchored
against path-swap races, and its cross-process byte count uses an exact
canonical decimal string rather than a coercive JSON number. Carrier tests pass
15/15. The full canonical non-visible Godot suite passes 87 tests with 6
expected renderer skips; the real Xvfb/Godot skeletal suite passes 21/21 in
121.396s. Two fresh hands-on trials passed the documented first-use load-through
and representative fail-closed
tamper/non-overwrite scenarios.
Fresh independent-review findings were fixed and the affected suites rerun.
CodeRabbit and CI remain pending. This carrier candidate is a direct
prerequisite to the named bounded Godot feasibility checkpoint, which remains
the governing human checkpoint; it
is not that checkpoint.

Ben's qualified appraisal of the structural gallery was that it "looks good";
the side-view x-ray overlay wording was clarified without changing geometry or
camera. That gallery remains bounded exploratory evidence for generated
rigging, weights, proxies, and shared pose. It does not establish production
topology, realistic anatomy, contact response, localized deformation quality,
runtime budgets, or a host/solver choice. No further cosmetic repair of that
disposable candidate is planned.

The current named human checkpoint is a bounded Godot feasibility result. After
the direct Creature Kernel and package prerequisites are prepared, the eventual
candidate must load an engine-neutral CK package into two independently
identified generated avatars, inject a host-neutral semantic pose, establish
semantic contact, show localized press/release deformation plus actual physical
response, measure render/collision coherence with named hardware and frame
evidence, and demonstrate a CPU baseline plus a useful fallback. The
[first host runtime evaluation](../research/first-host-runtime-evaluation.md)
records the current evidence and unresolved trial questions.

Ben approved Godot 4.7.2 as the provisional first reference-host feasibility
candidate after current Godot/Unity/Unreal/Bevy research and Double adversarial
review. This is candidate-only evidence gathering: it is not permanent engine
selection, Stage 3 success, a solver or package freeze, or adapter activation.
The post-Readiness-3 adapter gate remains explicit. The main thread may advance
direct Rust and engine-neutral package prerequisites, but stops before any
retained-human Readiness 3 or adapter-activation decision.

After the bounded Godot mechanics/feasibility checkpoint is completed or
dispositioned, the next model-facing human checkpoint is convincing
simplified/stylized anatomy across the four fixed profiles: a readable,
intentional neck, torso and pelvis masses, shoulder/hip transitions, tapered
limbs, and a simplified muzzle and paws/feet. This is not a photorealistic
anatomy, detailed-hands/faces/tissue, or current Godot-mechanics claim.
Immediately before implementation of that later anatomy checkpoint—not now—
activate the public morphology-knowledge lane by creating a provisional
source-backed and reference-safe inventory of functional assemblies,
fine-grained subparts, and optional modules, then pilot only one or two dossiers
under the already recorded research procedure. This does not decide inventory
contents, a schema, file layout, filenames, an executable representation, or
supported new morphology. No broader risk-and-activation map is planned;
checkpoint-specific evidence remains the governing approach.

The active runway remains fail-closed: stop for main-thread reevaluation if the
engine-neutral boundary, semantic pose/contact mapping, render/collision
coherence, physical-response interpretation, CPU fallback, or evidence budget
cannot be made credible without a material architecture or engine commitment.

Current operational snapshot: the [Codex app handover](current-handover.md)
(2026-08-28 NZST) records the primary checkout, active runway worktree,
merged PR state, and the current checkpoint/tooling state. It is a navigation
aid rather than a new authority owner. PR #107 retains the exact consumed
producer lineage in surface reviews while preserving the parked EXP-0002
closure; it intentionally made no displayed form-quality claim.

The PR #113 immutable surface checkpoint ID was
`authored-form-expressivity-exact-field-components-checkpoint-v2`, with
persistent URL
`http://localhost:8765/review/authored-form-expressivity-exact-field-components-checkpoint-v2`.
Each historical baseline or successor image is a 3x3 sheet: columns `front`, `side`, and
`three-quarter`; rows `CONTROL GUIDE` (explicitly control data, not geometry),
exact consumed pre-union field-component shells (52 for baseline, 27 for
successor), and neutral final skin. The earlier no-suffix
`authored-form-expressivity-exact-field-components-checkpoint` session is
preserved as historical evidence but superseded because its successor torso
used aggregate rather than exact loft sampling bounds. Corrected v2 uses the
exact loft bounds. Pixel-crop checks prove that every control-guide and
final-skin row is byte/pixel identical between the superseded session and v2;
the geometry and final skin did not change. This remains historical evidence
for the bounded exploratory proof above, not a current human checkpoint or
approval of a permanent backend.

Ben's 2026-08-24 appraisal of that immutable v2 gallery's successor v9 records
that its neck is visibly occluded or lost, its torso and pelvis read as rounded
rectangular/blocky, and the overall body is not convincing realistic or
anatomical skin. Visual region readability remains failed or inconclusive.
These observations are scoped to this disposable candidate and are not
canonical geometry prescriptions.

Ben's exact feedback on PR #103's successor checkpoint artifact was: "its got
pointy bulges under the arms again." This is rejection of that displayed
artifact only, not a canonical anatomy prescription or approval of any
successor direction. The earlier bounded response was a
shared successor-generator correction: consume exactly the distal
`deltoid-sweep` span at index `1` for each side, retain anterior/posterior
supports as guide-only, and publish the successor region as v6. No per-fixture
tuning, guide-derivation change, sampling change, or smooth-union change is
included.

That regenerated v6 candidate removes the large inferior support-curve lobes
across all four variants while retaining the existing torso-to-arm
connection. Independent static-capture trials disagreed about whether a much
smaller angular root contour still counts as the reported defect. An isolated
no-deltoid trial left that contour unchanged, and removing the temporary
upper-arm bridge made the attachment visibly thinner rather than providing a
better bounded correction. Ben's current appraisal is that the v6 disposable
successor demonstrates deterministic connected whole-body generation and
plumbing across variants, but does not demonstrate convincing complex
skin/form expressivity. No further aesthetic polishing of this disposable
consumer is planned. This appraisal is not a successful form-quality claim.
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

PR #97 was accepted and merged at `e78640e` after Ben appraised the revised
underarm silhouette as better. It was the accepted baseline for subsequent
surface passes; it is not final anatomy or backend approval.

The v6 disposable successor was built with shared generator operations across
all four fixed variants, existing semantic and guide inputs, and no
per-fixture patches or handcrafted base mesh. It remains an exploratory
consumer and does not select a permanent surface/backend or accept a decision
record. No further aesthetic polishing of it is planned.

PR #109 is merged at `52b88370f2f81b3c2cc937da7cc34f83d4481a7`. Its authored
torso profile is merged predecessor evidence and makes no form-quality
acceptance claim. PR #109's producer v7 added a source-authored seven-section
pelvis/torso axial profile, two identity frames, seven landmarks, 21 asymmetric
lateral/anterior/posterior radii with exact indexed provenance, and four shared
variant projections. Baseline guide v6 retained both depth sides and lineage.
Successor v4 / region v8 consumed a continuous asymmetric rounded-superellipse
torso sweep. The publisher cross-bound producer, guide, and successor lineage
and validated real bundles. The comparator added Previous/Next controls,
arrows, click-to-advance, and zoom.

PR #110 is merged at `a45920df1322bafbbd56ea6939837f8b0b9b8b33`. Its completed
internal, reversible source-authored head/neck prerequisite remains evidence
from the then-active authored-form expressivity gallery runway. Producer v8
adds source-authored head/neck profile v1:
eight indexed stations, seven named
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

PR #111 is merged at `6df6168cdf27477f3b275441616ab4cfd0ab814d`. Its completed
internal, reversible shoulder/arm authored-control slice remains predecessor
evidence on the runway. Producer v9 carries `authored_arm_profile` v1 with a
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
local tests, corrected-route hands-on trials, and fresh adversarial review are
preserved as historical evidence. It was not approved as final form quality or
as a production choice.

The hands-on operator trial also found that LAN read-only mode still displays
an enabled Save response control even though the server rejects writes. No
response was submitted or created. This pre-existing UI/usability mismatch is
deferred unrelated cleanup, not a pelvis/leg geometry or publication blocker.

The non-blocking rejected-POST secondary-400 logging concern is deferred
unrelated usability cleanup, not an arm blocker. The related PR #113 surface
candidate is described below as historical evidence.

PR #109 also contained Ben-approved neutral public-facing wording cleanup and
accepted MIT OR Apache-2.0 licensing DR-0014. That ancillary work does not
change the active runway. Root license files, README, and CONTRIBUTING carry the
current terms; Cargo package metadata is deliberately deferred because the
parked Phase 3 evidence closure exact-binds the affected manifest bytes.

The former named human checkpoint was the complete authored-form expressivity
gallery across the agreed controls and regions:
richer source-authored dimensions, landmarks, and profiles drive shared
region-appropriate generator operations across all four fixed variants, with
source provenance and reproducible evidence. Representative torso, head/neck,
shoulder/arm, pelvis/leg, and digitigrade foot transitions must read as
controlled continuous skin rather than joined procedural masses. Do not use
per-variant or per-fixture patches or a handcrafted base mesh. This remains a
bounded exploratory expressivity checkpoint, not proof of a finished
morphology family or production surface system. The current named checkpoint
is the shared-pose structural embodiment gallery described in the Active
runway above.

For that former checkpoint, retain the exact producer envelope used by
the checkpoint or an integrity-bound authored-dimension, landmark, frame, and
descriptor-role lineage projection, including indexed authored provenance, in
immutable review evidence. A source hash without the corresponding lineage
payload is not sufficient for the checkpoint's provenance claim.

The historical PR #113 candidate reached its surface checkpoint with the authored
foot-control route `hock -> metatarsal midpoint -> pad -> pad-toe midpoint ->
toe`: the hock is shin-owned, the remaining four stations are foot-owned, and
the route carries full lateral/up/forward radii, outer caps, four spans, and
exact producer/guide/successor lineage and cross-binding. The diagnostic
redesign changes the review images only; it does not change the final skin
geometry.

Pre-redesign publication measurements are retained as historical evidence:
compact producer envelope 190444
bytes; XZ 6244 bytes; Base64 8328 characters; producer SHA-256
`c48ed001b910549dd1da296bb4c664a4de29cad4838b42403b15aa97773a6d3e`; XZ
SHA-256 `5c42afe0b599b3afff52d687c3e46c9f4ae7d31f7d8e426d0b17e55858331161`;
subject context 8812 bytes; subject-context SHA-256
`0210c5f225869d9030ff82a2898f122be21b4da328dcb668e0b83a674f486fb7`.
Strict decode equality passed for that pre-redesign candidate. Those
measurements remain historical and do not describe the corrected v2 session.
Publication machinery is evidence plumbing, not acceptance. At the time of the
historical surface-gallery snapshot, PR #113 was an unmerged mergeable draft;
it later merged to `main` as squash commit
`eb89245da137e54cc85f9cd564fbcdd6c45eac66` on 2026-08-25 after Ben's explicit
authorization. The surface-gallery disposition itself was not that
authorization.

Current local diagnostic validation is: baseline full suite 68 tests passed;
successor full suite 61 passed; full visual-review suite 113 passed via the
repository's native-temp launcher; the full affected publisher rerun passed
39 tests; Python compilation, JavaScript syntax, documentation validation, and
`git diff --check` passed. A raw system-Python visual-test attempt failed
exactly two WSL/Windows TEMP parent-swap tests; the repository launcher
corrected that environment and the suite then passed 113 tests. Two fresh
Luna/high corrected-route hands-on trials found no correctness blocker. Their
first-use notes were narrow fit text/details, long metadata, and a description
that says final skin rather than explicitly neutral although the PNG labels say
neutral. The adversarial notes were modest variant differences in some front
views and the pre-existing enabled Save control in LAN read-only mode; no Save
response was submitted or activated. The final fresh new-code adversarial
Luna/xhigh review is complete: it found torso-bound and publisher-claim
validation gaps, which were corrected with exact loft bounds and regression
coverage, plus bounded validation of the full schema/count, owner provenance,
recipe histograms, and finite ordered `±100` sampling bounds. The publisher
does not independently duplicate NumPy/SciPy geometry or prove rendered
pixels, and this does not select a permanent backend. Live verification
confirms
the new persistent session at
`/home/ben/.cache/creature-kernel/visual-reviews/authored-form-expressivity-exact-field-components-checkpoint-v2`
contains `review.json`, exactly 8 PNGs, and no `response.json`. The systemd
user service was restarted and is enabled/active on port 8765 in LAN read-only
mode from the active worktree. The page and API return HTTP 200; all eight API
assets return HTTP 200 and their served SHA-256 values match the on-disk v2
assets. Playwright persistent-route smoke loaded all eight assets
at `1800x1500`, switched baseline/successor with arrow keys, and found no
console or request failures. Pixel-crop checks prove the control-guide and
final-skin rows are byte/pixel identical to the superseded no-suffix session.
All three PR #113 CI lanes passed before its merge. PR #113 is now merged to
`main` as squash commit `eb89245da137e54cc85f9cd564fbcdd6c45eac66`.

The active fixture's exact squared reference length is `1`. If a later runway
admits producer output above JavaScript's exact-integer domain, align or tighten
the Rust, publication, surface-consumer, and browser bounds before using that
output visually; speculative large-coordinate hardening is not a prerequisite
for this checkpoint.

The PR #113 surface candidate is historical bounded proof, not the next
appraisal gate. Rigging, contact, deformation, VR integration, and permanent
backend selection remain outside the current exploratory scope except for the
limited generated skeleton, weights, posed surface, and proxy evidence
required by the structural embodiment checkpoint. Do not reactivate the
parked formal comparison or expand scope without the recorded triggers or
Ben's direction.

EXP-0002 and its Gate B/freeze/runtime-attestation continuation are parked and
non-blocking. They are not prerequisites for this visual runway and must not be
resumed without Ben's explicit direction. The existing visual gallery, semantic
body inputs, provisional form producer, disposable surface-preview bridge, and
PR #93 torso result are the starting foundation rather than milestones to
rediscover.

The required Rust CI workflow still runs Phase 3 freeze-manifest tests whose
47-path candidate closure includes the current core crate module surface. PR
#107 therefore keeps every frozen core path byte-identical and carries the
consumed producer lineage in the unfrozen developer tooling. If a later runway
step genuinely requires a frozen core-path edit, first resolve that CI/freeze
boundary explicitly; do not regenerate, rebind, or resume EXP-0002 as an
incidental implementation step.

## Current activation state

The Stage 1 confirmatory surface protocol is parked and non-blocking:

- [DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  remains `Proposed`, Owner approval `Pending`, Review `Complete`. Its two
  current Double-review artifacts recommend `Revise` at High confidence. All
  five findings and review artifacts are preserved; no Revision 9 or further
  finding discussion is active.
- [DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  remains `Proposed`, Owner approval `Pending`, Review `Pending`. Exactly two
  geometry/semantic findings remain preserved. No acceptance is implied.
- The [first surface experiment design](../research/first-surface-experiment-design.md)
  is also deferred, with no active prerequisite. `EXP-0001` is not
  registered and no confirmatory evidence exists.

Reactivate this material only when at least two runnable candidate surface
implementations exist and the project intends to use a comparative outcome to
justify or select production architecture, or when Ben explicitly reactivates
it. Exploratory prototypes may proceed before then, but their observations
cannot claim formal DR-0009/0010 support or reject. This section is the
canonical owner of the current activation state; the detailed DRs and reviews
remain unchanged.

## Current Readiness 2

DR-0013 Readiness 1 remains active. The exact `creature-kernel.body` r1 schema,
`creature-kernel.fixture-manifest` r1 manifest, nine listed fixtures, Rust
parser/bootstrap, and Python preflight are now the Active Readiness 2
parser/bootstrap/schema/manifest/fixture transaction. The preflight checks
internal consistency and emits `ck.path-set.raw.v1`, while the evidence
generator separately binds implementation, admission support, resolved Cargo
dependencies/features, and the build request. The
[Readiness 2 admission record](readiness-2-admission.md) records the exact
post-merge recomputation from merged commit
`766992ab089687e9b1496574e8ffa721388d96f3` (PR #6): every bound identity and
policy matched, and the sanitized runner passed 26 core parser/bootstrap tests
plus target-explicit locked/offline clippy with warnings denied. No Proposed
owning DR is accepted by this activation.
That admission record pins the reviewed source commit, merged commit, and
evidence identities.
Its owner approval is Approved by Ben on 2026-08-13, and its review status is
Waived: the agreed Double adversarial review completed, consolidated validation
passes, and Ben instructed “do it” in response to “approve and waive,” with no
repeat current-candidate review loop. Readiness 2 is current and active; this
does not activate the distinct Readiness 3 resolver/snapshot transaction.

## Current implementation status

EXP-0002 remains a planned experiment with open evidence closure and no
technology outcome. Its phase-one package is the named exact-artifact
persistent-conformance evaluation
`ck.exp-0002.phase1-persistent-conformance-v1`: one persistent candidate
process receives development, then held-out, then adversarial. The
held-out role is non-tuning, not blind or process-isolated, and environment
checkpoints are workload-position-conditioned. The package binds 49 exact
frozen case adjudications plus runner classifications for 26 registered named
case groups, with the four-operation candidate surface for decimal admission,
scalar/translation comparison, and read-only environment inspection
(C/x87 plus raw and decoded MXCSR rounding/FTZ/DAZ bits). Its request/response
boundary, opaque wire request IDs, corpus files, manifest identities, and
bounded runner/oracle/transport are frozen; synthetic checks are implemented.
Attempt-001 completed at source commit
`d88f5eca3ad3c0c0cb00dcf7dd012471be979305` with `run_status: complete` and
`evidence_status: passed`: development 10/10, held-out 13/13, adversarial
26/26, 49/49 cases overall, and 26/26 registered relations. Its wrapper
receipt records `completed-evidence`, `failure: null`, one runner invocation,
and exit `0`; see the [human-readable results summary](../../experiments/EXP-0002-numeric-frame-profile/RESULTS.md)
for the immutable artifact links and hashes. `profile_binding` remains `null`;
there is no profile selection, quaternion support, or Readiness 3 activation.
The exact claim is limited to this
identified candidate and runner adjudicating those frozen cases and classifying
those named groups, including represented boundary/resource/error/environment
observations. Only `lexical-equivalence`, `signed-zero-canonicalization`, and
`environment-repeat` have explicit cross-case checks; the other groups organize
member-case outcomes. No role isolation, fresh-process behavior, order
independence, repeatability, broad generalization, production-domain claim, or
technology outcome can be inferred. Broader tolerances and later experiment
families remain Proposed/open.

PR #65, “Add the phase-two authored-conflict development runner,” merged at
`9bcf2172d0433d35d2d96e6841a83890899d11e9`. Its development-only package adds
the exact unselected strict/micro/stress sweep, a 16-case authored-conflict
corpus, bounded JSONL transport, and a 16-case × 3-profile (48-request)
adjudicator/runner with CI. The actual run passed 48/48: 18 `agree`, 15
`conflict`, 12 `skipped`, and 3 `rejected`, with a report under 128 KiB. This
selects no profile, supplies no held-out or adversarial evidence, and does not
activate Readiness 3. Technical disposition is that this is insufficient to
choose strict/micro/stress: only synthetic scalar ladders and two tiny direct
socket-rotation thresholds discriminate them. A separate development-only
extension now covers the missing evidence with one deterministic three-Part
descendant-tail variant and six cases across the same three profiles (18
requests). The cases combine centimetre units, a left-handed signed basis,
non-identity half-turn rotations, and an independent exact-rational closed
witness oracle. The actual candidate run passed 18/18: 9 `agree` and 9
`conflict`. Hands-on trial and adversarial review found and covered
quaternion-sign canonicalization, source-derived document-identity, and
report-algebra defects. The historical 16-case corpus and 48-request report
remain unchanged. This is still non-authoritative development evidence: it
selects no profile, supplies no held-out or adversarial corpus evidence, and
does not activate Readiness 3.
Evidence synthesis and any production semantic-profile binding remain
explicitly deferred; Readiness 3 activation remains Ben-owned.

The [EXP-0002 phase-three semantic-band conformance preregistration](../../experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/README.md)
is now Proposed and execution-disabled. It tests one analytically derived
semantic-band candidate over 40 deterministic scored cases, with 8 explicit
development cases, 12 controls, certified interval/oracle gates, and two WSL
repeatability attempts plus one native consistency attempt. The exact ledger is
materialized as `development-unfrozen` by the [generator](../../experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/generate_phase3.py),
its [focused test](../../experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_generate_phase3.py),
the three corpora, recipe/artifact manifests, and 12-vector sqrt fixtures;
the package README records the regeneration/check commands. Strict, micro, and
stress remain historical analytical comparisons and are not executed. The
development cases cover the exact translation threshold, near-threshold
rotation (with the exact singleton retained as a direct comparator unit-test
obligation), q/-q, conversion, four-edge composition, Attachment, identity,
and `kappa=999999`. The controls are four gray strictly-inside-band cases, four
dispatched typed zero-quaternion cases, three runner-preflight out-of-domain
cases, and one dispatched negative-relative case. Thus each attempt has 60
case adjudications and 57 candidate wire requests; across three attempts this
is 180 adjudications and 171 candidate requests, with three fresh candidate
processes per attempt and nine total. The three preflight cases remain runner
adjudications, not candidate requests. Current generated records reuse the
existing phase-two protocol/envelope/operation/providers and canonical source
string; no new wire protocol is introduced. The evidence and read-only
preflight contracts now use the canonical phase ID
`exp-0002-phase3-semantic-band-conformance-001`; their earlier mismatch is
corrected. Gate A is complete/passed for this exact development-unfrozen
materialization, with the current Double recorded
in [Review 01](../../experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/reviews/gate-a-review-01-closure-integrity.md)
and [Review 02](../../experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/reviews/gate-a-review-02-numeric-claims.md).
Prior issue-finding reviews remain stale historical working evidence. The
current v3 successor is materialized locally under execution-tool/materialization
snapshot `762b04b8db3397cb1885d94236ad5d47cb321830`, with schema
`ck.exp-0002.phase3.freeze-manifest-3` and manifest SHA-256
`faafe7680fcc3509a245dde6759396a1391e02c40891128ca44d007726adef85`.
It binds the experiment-wide closure, exact runtime contract, fixed binary
cap, exact slot reservation, and runtime/platform evidence. The v2 identities
remain historical evidence: execution-tool commit
`9dca58a84072582db34045b8eac98d6e86d3d5ae`, manifest commit
`cc1531c2e8efe40f8a4896d11b10973147c5636b`, and self-hash
`d7365e99945cb2e57cd6bac45bac241fc032dc1312cda3a94cfdba14cd17933a`.
The v3 bytes still require a fresh current-revision Gate B Double review of
the later commit that contains them, followed by execution-disabled Gate B
admission and artifact-custody records. An exact-attempt/native-dispatch
authorization is created separately only after Ben explicitly authorizes
execution.
No profile-value validation, production binding, or Readiness 3 activation
follows from this package.

The Phase 3 package now includes source oracle, actual nested-response scoring,
bounded runner aggregation, the non-evidence receipt, materialized-package
adapter, the Proposed in-memory result/receipt/attempt-index contracts, and
read-only Gate B preflight, build-only receipt capture, deterministic freeze
manifest generation, and exact runtime authority/custody/transport/adjudication/
publication tooling. The current v3 successor is materialized from execution-
tool/materialization snapshot `762b04b8db3397cb1885d94236ad5d47cb321830` with
schema `ck.exp-0002.phase3.freeze-manifest-3` and manifest SHA-256
`faafe7680fcc3509a245dde6759396a1391e02c40891128ca44d007726adef85`. It binds
the experiment-wide closure tool, current exact-runtime contract, fixed binary
cap, exact experiment-slot reservation, and runtime/platform observations. The
v2 freeze and its two `Revise` reviews remain historical. The consolidated
296-test suite passed before new E
`762b04b8db3397cb1885d94236ad5d47cb321830`; the older 267-test pass before
the historical v2 execution-tool commit
`9dca58a84072582db34045b8eac98d6e86d3d5ae`. The adapter validates the current
package/preregistration/manifests, local generator identity, fixed fixture
declaration/hash (without loading the external fixture), generated source
identities, and sqrt fixture, then projects opaque 8-development/40-held-out/
12-control roles; expected held-out classes remain internal to its synthetic
handoff, while development and controls are observation-only. The new
contracts retain exact request/response bytes and hashes, scorer/oracle and
process/platform/FE/MXCSR/binary/transport observations, partial evidence,
60/57/3 and 8/40/12 accounting, and result/receipt/index cross-binding with a
non-circular index self-hash. The preflight checks current materialized package
and tool identities against the caller-supplied prebound 47-file candidate
closure, but does not recompute closure, freeze, authorize, execute, create
evidence, or pass Gate B. Rust CI's existing `test_phase3_*.py` glob includes
the new focused tests. This plumbing does not execute a candidate, Rust, or
experiment process/attempt and does not change the package's Proposed,
execution-disabled, open-evidence status.

The manual [Gate B native build workflow](../../.github/workflows/phase3-gate-b-native-build.yml)
is build-only and transfer-only: it takes a full commit SHA, runs on Ubuntu
24.04, binds source/dependency/build/toolchain/binary identities, and never
dispatches an exact native experiment attempt. The current v3 freeze is
materialized from execution-tool/materialization snapshot
`762b04b8db3397cb1885d94236ad5d47cb321830` under schema
`ck.exp-0002.phase3.freeze-manifest-3` and manifest SHA-256
`faafe7680fcc3509a245dde6759396a1391e02c40891128ca44d007726adef85`.
No candidate or exact experiment attempt has run and no native dispatch has
occurred. The later commit containing the v3 bytes still requires fresh Double
review, then execution-disabled Gate B admission and artifact-custody records.
An exact-attempt/native-dispatch authorization is created separately only
after Ben explicitly authorizes execution.

The materialized records distinguish `construction_target` (the exact recipe
magnitude before source serialization) from source-derived `I_truth` (computed
from the serialized source and its exact numeric lexemes). Current materialization
contains `I_truth` only: translation truth is exact; rotation truth is a
certified interval for the normalized q/-q-equivalent full chord, computed with
exact rational dot/norm-squared arithmetic and 256-bit integer-`isqrt` directed
enclosures; decimal text is only final outward endpoint encoding. `I_candidate`
and `I_error` are mandatory future scorer/adjudication outputs after candidate
witness data exists; their radius and upper-error caps remain preregistered
obligations, not current artifacts. The current source-derived interval radius
and future error upper endpoint are capped at `1e-10` full chord.
Construction metadata retains complete authored/derived contribution lists,
exact kappa values, and derived canonical/source quaternions, including
non-identity derived rotations in applicable families. Request IDs are unique
across development, held-out, and controls; normalized request-content
uniqueness is checked across the development/held-out roles after removing
`request_id`, while controls remain separately partitioned for typed and
preflight behavior.

Source-derived admission independently reconstructs all 60 records: 53 are
admitted, 4 are typed zero-quaternion controls, and 3 are out-of-domain
runner-preflight controls; all 40 scored records are admitted and certified
`kappa_q <= 2`. The four typed locations are the tail-root part placement, host
tail-mount socket interface, tail attachment offset, and mating tail-mount
socket interface, each retained as an exact typed location. Negative gate tests
fail closed for component, contribution sum, quaternion component/norm, path,
conditioning, and negative-relative tolerance violations.

The unchanged candidate is prebound at base commit
`f4125342211a1d1436ae48b685ec2342700f39c4`, before the Phase 3 path existed.
The complete 47-file candidate/core/build closure includes the compile-time
embedded `spec/body-document/schema/ck-body-document-v1.schema.json`, a
compiled include input. It has path-set SHA-256
`10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc`, content
SHA-256
`21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2`, and
1,494,337 raw bytes; base tree/current-disk recomputation matches. The closure
is immutable from Gate A through exact attempts; any change requires a new
candidate identity plus unseen scored material or exact-public-corpus
adjudication. FE/MXCSR remains external and runner/oracle/scorer code cannot
alter candidate source.

The durable candidate prebinding checker and focused nine-test file are
development tools, not generated corpus outputs or execution evidence. The
checker is 17,745 bytes with SHA-256
`d21c122ecf5256b7e83402ba2a5a150807a1cfc64eef5e8df2002d86b1058c8b`; the test
file is 5,389 bytes with SHA-256
`063206d1e9ecf4a5c2770061cca80e3492dc4bd3d34df56963c380690902d566`. Run:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/check_candidate_prebinding.py
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_candidate_prebinding.py
```

The checker follows production literal `include!`, `include_str!`, and
`include_bytes!` references recursively, rejects dynamic or unbound targets,
checks selected regular-file types, modes, raw content, and relevant Cargo
build/config inputs, and does not sweep ignored target/cache artifacts. It
parses Git's textual `100644` as OCTAL integer `33188` before big-endian u32
framing.

The raw receipt records clean wrapper source checkpoints at the same source
commit. The raw result records runner-side observational identity as
dirty/untracked at that commit. An independently reviewed explanation is the
pre-created empty untracked attempt directory plus differing Git probes, but
the artifacts do not directly encode or prove causation. The audit found no
evidence of source mutation or inadmissibility.

The phase-one package also includes the committed `run_phase1_once.py` one-shot
wrapper. It is orchestration/provenance only, not a second numeric runner and
not evidence itself. Default/help/`--preflight-only` paths cannot run the
authoritative corpus; preflight prints the safe plan without creating an
attempt. Execution requires all three of `--execute`, exact
`--acknowledge RUN-EXP-0002-PHASE1`, and a new `--attempt-id`. It fixes
`x86_64-unknown-linux-gnu`, Cargo dev/debug, and `--locked --offline`, records
the exact clean source commit, and requires synthetic validation and a
successful candidate build before the one authoritative run. Attempts use the
exclusive `experiments/EXP-0002-numeric-frame-profile/results/phase1/<full-commit>/<attempt-id>/`
layout; completed runs retain `result.json` and `receipt.json`, with no
overwrite or automatic retry. The receipt records commands,
target/profile/toolchain, an environment allowlist, hashes, exits, failure
stage, and cross-checks; full evidence remains in the result. Offline
integrity checks do not rerun the corpus. Completed failed or inconclusive
evidence is preserved, and fixes/reruns require a new commit and attempt ID.
This preparatory wrapper remains within the recorded autonomous runway.

Readiness 2 remains active for the admitted schema, manifest, fixtures,
parser/bootstrap, and preflight. The workspace now also contains a provisional
structural address/index and validator plus the `inspect-structure` CLI command
as preparatory implementation over admitted documents. This source-preserving
inspection projection is not a finalized resolved snapshot and does not activate
Readiness 3; resolver, canonical/numeric/frame, geometry, and runtime work remain
gated or absent. The active Readiness 2 admission remains the immutable exact
identity at its recorded merge commit; current structural preparation is outside
that admitted implementation identity and requires a future successor
transaction before any Readiness 3 activation claim.

This implementation batch adds a meaningful authored stylized digitigrade-biped
example that passes provisional structural inspection
(1 module, 18 Parts, 17 Joints, 2 Sockets, 1 Attachment, 4 Regions, 3
Capabilities). The CLI now provides structured help and deterministic success
summary counts. Local visual-review tooling now supports immutable read-only
structure sessions alongside legacy image reviews, exposing containment, joints,
composition, regions, capabilities, diagnostics, raw JSON, and an explicit
no-geometry/no-runtime boundary. Hands-on trials found no blockers; native T3
preview was unavailable, while bounded headless Chromium succeeded. These
preparatory results do not constitute Readiness 3 admission or activation:
they do not activate resolver/numeric semantics, geometry, rigging, animation,
physics, or runtime.

The current implementation now provides provisional developer instrumentation:
`inspect-prepared-source --input <path>` plus its bounded
`publish_prepared_source.py`/localhost-server flow. It preserves the admitted
single-source graph projection and adds the declared basis, prepared counts,
and numeric debug rows with binary64 bits and stable semantic locations. Ben's
2026-08-15 appraisal found that the prepared-source projection adds
developer-visible preparation data but no meaningful creature visualization;
the new spatial candidate was locally validated and appraised successfully on
2026-08-15. He does not want
routine implementation details presented for approval. It remains preparatory
only: it does not
resolve dependencies or produce a snapshot or canonical serialization, apply
basis/unit values, interpret quaternions, expand dependencies/modules, produce
geometry, rigging, animation, physics, or runtime output, or activate Readiness
The earlier PR #14, “Add prepared source developer inspection,” is merged at
commit `150de082dfb02d77d0b5aa0b7571437f65ce410b`; the later PR #65 checkpoint
is recorded above.
This is not blanket merge authority outside the named runway and does not waive
real user-visible or direction-setting decisions.

The current work also contains a provisional preparatory filled-form descriptor
candidate exposed only through the developer CLI
`inspect-provisional-form --input <path>`. It builds four fixed display-only
profiles, maps current semantic roles to ellipsoid, capsule, and tapered-segment
descriptors, and retains exact reference points/segment endpoints with positive
integer permille display tuning. This is provisional preparatory evidence only:
it is not production geometry, mesh, SDF, anatomy, runtime output, or Readiness
3 activation. PR #26 delivered the filled-form gallery and merged at
`240cc055f9536d01152ee401ee342c5f135f3b32`; Ben appraised the intended
straight-tail provisional form as sufficient on 2026-08-16.

The former retained-human visual appraisal candidate was the disposable
`experiments/current-form-surface-preview/` continuous-surface gallery. It is
limited to the question of whether current Rust-derived provisional forms become
one readable surface with acceptable neck, shoulder, hip, limb, and tail
junctions. This is an unregistered exploratory current-source bridge only: it
does not activate Readiness 3 or 4, Stage 1, `EXP-0001`, DR-0009/0010, a
production backend, the production `GeometryRequest`/`GeometryResult` seam, or
any rig, animation, collision, deformation, or runtime claim. The formal
activation order remains Readiness 3's semantic resolver/in-memory snapshot
handoff first, followed by Readiness 4's project-owned geometry seam and Rust
CPU proof. The candidate's visual result was evidence only and did not change
that order.

Ben historically appraised this checkpoint on 2026-08-16 and found that primitive body-part
placement and proportions remain odd in places, as expected while the grammar
uses simple oval and primitive forms. He found the continuous smooth-union
joins sufficient for this stage: corresponding body forms morph together
convincingly. This completed the historical retained-human surface-appraisal checkpoint
for continuing foundational implementation; it does not claim final visual
quality, anatomy, production geometry, Stage 1, Readiness 3/4, DR acceptance,
or solver/runtime evidence. The formal next activation order remains
unchanged: Readiness 3 resolver/snapshot first, followed by Readiness 4
geometry seam and Rust CPU proof.

PR #9, “Add inspectable biped structure workflow,” is merged at commit
`565c32bd35215e23d737fb333604382d3e6958ab`. PR #10, “Add preparatory exact
decimal conversion,” is merged at commit
`fcd071365a9789c81944b2e7e0572f7e21f0d672`. The standalone
`creature_kernel_core::numeric` module is preparatory code only: it
checks strict JSON-number grammar, uses pinned Rust 1.97.1 direct correctly-
rounded binary64 final conversion, returns typed overflow/nonzero-underflow
failures, admits finite subnormals, normalizes lexical zero to `+0`, and has
focused boundary tests. Caller-enforced token/resource limits remain outside
this module. It is not wired into body-document admission, does not alter the
admitted Readiness 2 identity, and does not activate numeric semantics or
Readiness 3. The standalone `creature_kernel_core::frame` module is likewise
preparatory: it provides a normalized-binary64 structural transform carrier,
an exact signed-axis source-basis map, and symbolic length-unit ratios. It does
not apply unit scaling, validate or normalize quaternions, perform transform
algebra or comparison, integrate source documents, resolve graphs, publish
snapshots, or change the active Readiness 2 identity; it does not activate
Readiness 3. The public `creature_kernel_core::source_preparation::prepare_single_source`
operation accepts raw source bytes plus a sealed `ResourceProfile`, performs
whole-document admission, structural validation, basis preparation, and
numeric preparation for one source. Its complete semantic numeric maps cover
part/joint/socket/attachment transforms, landmark positions, dimensions, and
named frames under stable address or owner/role keys; the retained graph source
records and context provide semantic provenance. Raw lexical spelling and
provenance are not recovered. Internal `frame_preparation` helpers cannot
bypass record-level admission. This preparation does not apply basis/unit
values or quaternion semantics, expand dependencies/modules, produce claims,
snapshots, or serialization, or activate a resolver or Readiness 3.
This intentionally retires the provisional public record-level
`frame_preparation` API in favor of the admitted whole-source boundary.

The current implementation also provides a crate-private source-set preparation
projection: it prepares each member independently, retains exact raw bytes and
retained structural source metadata, builds a deterministic `(document,
namespace)` member table, and sorts declared edges deterministically. Every
retained declaration can now be classified, in deterministic edge order, as
naming or not naming an already supplied member by `(document, namespace)`;
declared `content_sha256` remains opaque and unverified. It does not perform
acquisition, revision/hash verification, resolver status/diagnostic mapping,
cross-source merge/remap, snapshot/digest, or Readiness 3 activation; it
remains preparatory and does not accept or revise a Proposed decision record.

The current implementation also provides a crate-private owned restricted
source-set handoff that consumes a successful `PreparedSourceSet`, owns raw
member bytes and prepared projections, and retains deterministic member
roles/keys plus locator-only dependency outcomes with opaque, unverified
hashes. It remains non-resolving, non-serialized, and non-authoritative: it
performs no acquisition, revision/hash verification, namespace merge/remap,
canonical numeric/frame resolution, authoritative snapshot, public resolver
envelope/API, or Readiness 3 activation.

The current implementation also provides a crate-private restricted
single-source snapshot handoff: it owns the exact raw bytes, retains the
prepared source and authored records, computes exact integer Part/Attachment
placements, requires zero declared dependencies, and exposes explicit
unresolved record counts. It is not authoritative resolver success, a public
snapshot or serialization, general frame resolution, geometry, or Readiness 3
activation, and accepts or revises no Proposed DR.

The current implementation also contains a crate-private, non-serialized
resolver-envelope/reducer scaffold. It represents the Proposed seven statuses
and eight ordered phases, with deterministic documented precedence and fatal
reachability, independent processing and diagnostic completeness, explicit
generic primary diagnostics with a caller-supplied ordered diagnostic type, and
fail-closed success/failure payload legality. It adds no public resolver API or
wire format, concrete diagnostic registry/profile/codes, resource accounting,
semantic resolution, snapshot, or Readiness 3 activation, and does not accept
or revise a Proposed DR.

The current implementation also provides a deliberately restricted exact
reference-placement foundation over one prepared source. It accepts only
canonical metres in the right-handed basis (`+Y` up, `+Z` forward), identity
rotations, and translations that are exact bounded integers in the binary64
carrier for Part placements plus Attachment host/mating Socket frames and
offsets. It composes parent-local Part deltas through containment and checks
exact Attachment agreement between the authored attached-root delta and the
derived equation result. Unrelated Joint and named-frame transforms are not
validated or resolved by this operation. This is not general basis/unit/
quaternion transform math, resolver activation, geometry or surface generation,
or a user-facing rendered creature. The stylized example was corrected from
world-looking authored values to contract-compliant parent-local deltas while
retaining the intended derived reference positions.

The current implementation also adds a crate-private deterministic per-member
exact-placement projection over the restricted source-set handoff. It preserves
each member's role and member-local placement `Result`, so one member's failure
does not hide another member's result. It does not resolve dependencies, verify
their hashes, remap namespaces, produce an authoritative snapshot or
serialization, or claim Readiness 3, and it creates no useful visual checkpoint.

The current implementation also provides a crate-private caller-profiled framed
SHA-256 primitive. It selects no production domain/profile, does not interpret or
verify `content_sha256`, establishes no canonical identity/snapshot/resolver
semantics, makes no Readiness 3 claim, and creates no visual checkpoint.

The current candidate source-digest observation computes
deterministic caller-profiled per-member digests over the exact raw bytes owned
by the source-set handoff, retaining root/dependency roles and deterministic
member keys. It performs no `content_sha256` interpretation, comparison, or
verification; establishes no canonical or aggregate identity and no
resolver/snapshot/Readiness 3 claim; and creates no visual checkpoint. It
remains within the recorded autonomous preparatory runway, whose existing
human-stop boundary is unchanged.

The current implementation also provides a crate-private dependency-content
observation over the existing owned source-set handoff. It consumes a
caller-supplied digest profile, parses each retained `sha256:` declaration, and
produces exactly one result per currently admitted dependency edge by hashing
the target's exact raw bytes with framed SHA-256. Outcomes are `matched`,
`missing`, `malformed`, or `mismatch`; each result retains the structural
member identity and owner role. The retained-edge index is observation-only:
current structural admission rejects repeated dependency namespaces, and the
index is not a canonical occurrence identity. This selects no production
profile and performs no acquisition, canonical or aggregate identity,
resolver status/diagnostic mapping, namespace remapping or semantic
resolution, snapshot or serialization, Readiness 3 activation, or visual
checkpoint.

The current implementation also provides a crate-private deterministic
source-set provenance observation. It inventories each supplied member's
source-local semantic addresses, module declarations, and typed owner/role
records with explicit member/role ownership. The document-wide projection now
also builds a deterministic semantic-address occurrence index and a keys-only
collision projection: every member/role occurrence is preserved, exact full
`AddressKey` collisions are separated from namespace-owner collisions, and
neither kind is selected or rejected. It records namespace owners and
multi-owner namespace collisions, and retains dependency declarations in
deterministic order. A root-started traversal over supplied locator topology
records reached edges, missing supplied targets, active-stack back-edges,
reached members, and supplied-but-unreachable members. The index is
observation-only, not canonical occurrence identity; no aggregate source-set
address budget has been selected, and any such bound remains an activation
concern. It performs no hash verification or acquisition, namespace
merge/remap, semantic/numeric resolution, status/diagnostic mapping, snapshot
or serialization, or Readiness 3 activation, and creates no visual checkpoint.
It remains preparatory within the recorded runway and does not complete the
later Readiness 3 successor candidate; the existing human stop before that
activation transaction, or at another retained-human checkpoint, is unchanged.

The current runway also contains a crate-private source-set reference-target
observation. It deterministically enumerates all admitted typed semantic
reference slots, separating full `AddressKey` targets from frame
`OwnerRoleKey` targets, and retains `Unique`, `Missing`, or `Ambiguous`
candidate evidence without selecting a winner. Provenance comes from the same
owned handoff and a once-built frame index; non-semantic Region and Capability
array order does not affect observation equality or ordering. Current
structural admission makes `Missing` unreachable through the public handoff
path, but the representation remains for the later resolver boundary, while
same-namespace cross-document duplicates exercise `Ambiguous`. This is internal,
reversible runway progress only: it performs no namespace merge/remap,
canonical identity, diagnostics/status mapping, serialization or snapshot
work, public API or visual output, or Readiness 3 activation, and does not
accept or change a contract; the existing human stop remains unchanged.

The runway also contains a crate-private source-set typed relation-edge
observation. It emits one deterministic edge per retained reference, using
closed Part-containment, Joint-endpoint, Socket-ownership, Attachment-endpoint,
owner/frame, Region-membership, and Capability-membership families with
expected `Part`, `Socket`, `Frame`, or `AnyIdentity` constraints. Each edge
preserves source member/role, slot, target, and complete `Unique`/`Missing`/
`Ambiguous` candidate provenance; cardinality evidence remains separate from
kind-match evidence and no candidate is selected. Non-semantic array and
member input order is ignored. Current admission makes kind mismatch and
`Missing` unreachable through the public handoff path, but the classifier
representation remains for the later resolver boundary. This is internal,
reversible runway progress only: it establishes no relation validity verdict,
topology/cycle/cardinality enforcement, remap, canonical identity,
diagnostics/status, serialization or snapshot, public API or visual output, or
Readiness 3 activation; the human stop remains unchanged and no contract is
accepted or changed.

The current internal slice is implemented as a crate-private projected
relation-validity reducer. It emits bounded deterministic findings for missing,
ambiguous, and wrong-kind projected references, plus repeated Attachment
endpoint pairs, host Socket reuse, mating Socket reuse, and total cross-role
Socket-capacity reuse for uniquely resolved expected-kind endpoints. Complete
context and provenance are retained, invalid endpoints are excluded from
grouping, and no winner is selected. Current structural admission makes
several adverse states unreachable; test-only synthetic observations exercise
the later reducer boundary. It performs no aggregate resolver/source validity,
public API, diagnostic/status mapping, snapshot/profile selection, or
Readiness 3 activation.

The runway also contains a reviewed crate-private source-set namespace
projection candidate. It consumes a total validated caller/test-supplied
in-memory destination table keyed by original `SourceSetMemberKey`, with the
root namespace fixed while dependency namespaces may change. It projects every
semantic `AddressKey` and embedded owner address of typed `OwnerRoleKey` values
by namespace substitution only, preserving address components, member/role
ownership, and original provenance; `ModuleDeclarationKey` remains unchanged
as neutral source bookkeeping. Deterministic complete coverage and indexes
retain namespace, full-address, and typed-owner-role collision evidence without
selecting a winner. The input is an algorithm candidate only, not authored
authority or syntax. It performs no reference rewriting, candidate selection,
relation verdict, topology/cardinality enforcement, merge, diagnostics/status,
public or wire contract, canonical/digest/profile binding, snapshot or
serialization, fixture or lifecycle work, visual output, or Readiness 3
activation; the human stop remains unchanged. This is internal reversible
runway progress only and accepts or changes no contract.

The runway also contains a reviewed crate-private projected reference-target
observation. It combines the same admitted handoff with a total validated
destination table; current admission guarantees references are source-local,
so each target namespace is projected by its owning member destination while
the original target/outcome and projected target/recomputed outcome remain
visible. Exact `AddressKey` and Frame-only `OwnerRoleKey` indexes classify zero,
one, or many candidates as `Missing`, `Unique`, or `Ambiguous`, retaining all
provenance without owner filtering or winner selection. Divergent destinations
can disambiguate equal original keys; equal destinations preserve ambiguity,
while a namespace collision alone does not imply a full-key collision.
`ModuleRoot` projects its target while retaining its declaration slot key. Index
integrity fails loudly, and collection/member order remains deterministic. This
performs no authored or source mutation, cross-source authored references,
resolver selection, relation verdict, topology/cardinality enforcement, public
or wire contract, canonical/digest/profile binding, snapshot or serialization,
fixture or lifecycle work, visual output, or Readiness 3 activation; the human
stop remains unchanged. It is internal reversible runway progress only and
accepts or changes no contract.

The runway also contains a reviewed crate-private projected-source-set evidence
collector. It emits deterministic fixed-class findings for projected namespace
collisions, full `AddressKey` collisions, typed (`OwnerRoleKey`, record-kind)
collisions, `Missing`/`Ambiguous` references, and target-kind mismatches. Each
reference finding retains owner/role/slot, original and projected targets,
existing relation family and expected kind, and complete candidate provenance.
Namespace collisions remain separate from full-key collisions; cross-kind
owner-role coexistence is legal, ambiguity and kind mismatch are orthogonal,
and no winner is selected. The collector consumes every retained member, and
index corruption fails loudly. This is evidence only: it performs no collision
rejection, pass/fail verdict, diagnostics/status mapping, source mutation,
selection, topology/cycle/cardinality enforcement, public or wire contract,
canonical/digest/profile binding, snapshot or serialization, fixture or
lifecycle work, visual output, or Readiness 3 activation; the human stop
remains unchanged. It is internal reversible runway progress only and accepts
or changes no contract.

The runway also contains a crate-private source-set projected-placement
observation. It consumes canonical source-set placement plus a validated
namespace projection, projects namespace identity only, and retains source-local
keys, member roles, transforms, complete Attachment provenance, and both authored
and derived candidates. It retains exact upstream failure, placement failure,
and success outcomes per member, with deterministic flat Part/Attachment
occurrences, projected-key indexes, and collision-key evidence. Collisions are
retained rather than merged, ranked, or resolved. It performs no remap
generation, winner/status/diagnostic or snapshot work, public API, geometry or
runtime work, or Readiness 3 activation; it is internal reversible runway
progress only and accepts or changes no contract.

The runway also contains an implemented crate-private dependency-topology
evidence reducer. It emits deterministic fixed-class findings for missing
supplied targets, reachable DFS cycle back-edges, and supplied members that
are unreachable from the root. Findings retain complete declaration, target,
or member context, preserve duplicate occurrences, and include missing
declarations owned by unreachable members. This is evidence only: it performs
no validity, status, or diagnostic mapping; dependency selection, acquisition,
or hash verification; namespace policy; per-document Part/Joint/Socket/
Attachment revalidation; public or wire contract; fixture or lifecycle work;
or Readiness 3 activation. It is internal reversible runway progress only and
accepts or changes no contract.

The runway also contains an implemented crate-private exact
`SourceBasisMap` quaternion remapping primitive. For every valid signed source
basis, including reflections, it maps the quaternion vector as
`det(C) * C * v` and leaves `w` unchanged, using only exact component
permutation/sign changes with zero canonicalization before later quaternion
normalization. It performs no normalization, validation gate, square-root
provider or profile-constant selection, unit scaling, transform composition,
public or wire API change, snapshot or serialization, validity/status/
diagnostic mapping, or Readiness 3 activation. It is internal reversible
runway progress only and accepts or changes no contract.

The runway also contains an implemented crate-private exact unit-scaling
candidate. It applies `UnitRatio` to normalized binary64 values and exposes a
`scale_to_metres` candidate for the current metre, centimetre, and millimetre
units using exact integer/rational arithmetic with one round-to-nearest,
ties-to-even result. It handles normal, subnormal, and significand-carry
boundaries, canonicalizes zero, and reports typed invalid-ratio, non-finite,
resource, overflow, and nonzero-underflow failures. The current closed unit
ratios require no profile constants or other policy choice. It is not wired
into source or member preparation and uses neither ambient floating-point
multiplication nor a pre-rounded approximate ratio. It adds no public or wire
contract, status or diagnostic mapping, snapshot or serialization, fixture or
profile binding, or Readiness 3 activation. It is internal reversible runway
progress only and accepts or changes no contract.

The runway also contains an implemented crate-private single-member canonical
frame/value preparation candidate. It covers all seven prepared numeric
collections while retaining source-local keys, member role, and declared
basis; it applies the signed source-basis map followed by exact scaling to
metres for length values, and applies quaternion basis remapping followed by
caller-injected gated normalization for rotations. Evaluation uses a fixed
deterministic order and returns the first precise typed error without a partial
value. The gate and square-root/environment capability remain caller-owned,
and failure remains isolated to the one member. This candidate selects no
source-set aggregate, provider factory, default constants, placement
composition, relation or namespace resolution, public or wire contract,
snapshot, status or diagnostic mapping, fixture binding, or Readiness 3
activation. It is internal reversible runway progress only and accepts or
changes no contract.

The next runway slice adds an implemented crate-private source-set coordinator
around the single-member canonical preparation candidate. It visits admitted
members in deterministic `BTreeMap` key order and invokes a gate factory before
a provider factory for each member; each factory returns owned per-member state,
while an explicit `None` provider represents an unavailable capability. The
owned result retains the source-set root, source-local member keys, member roles,
and an independent result for every admitted member, so one member failure does
not suppress the others. Freshness and permutation-independent factory behavior
are caller preconditions; the coordinator does not prevent factories from
sharing state or depending on invocation order. This candidate selects no
aggregate validity or status, shared-state prevention, concurrency, transform
algebra or placement, namespace or relation resolution, public or wire contract,
snapshot, fixture binding, or Readiness 3 activation. It is internal reversible
runway progress only and accepts or changes no contract.

The following runway slice adds an explicit caller-supplied, reborrowable
binary64 arithmetic capability for add, subtract, multiply, and divide. The
existing canonical quaternion normalization path is retrofitted to a fixed
15-call provider sequence with finite-result checks and produced-zero
canonicalization to `+0`; it selects no default provider. Member and source-set
preparation propagate the capability through their caller-owned factories, for
which fresh state and permutation-independent deterministic behavior remain
caller preconditions. A crate-private fixed-order Hamilton composition
candidate always re-normalizes its product through the same validation gate,
arithmetic capability, and square-root capability. This slice supplies no
native provider or environment attestation, vector rotation, rigid-transform
or placement operation, tolerance or profile selection, aggregate status,
public or stable API, wire format, snapshot, fixture binding, or Readiness 3
activation. It is internal reversible runway progress only and accepts or
changes no contract.

The following runway slice adds crate-private checked canonical 3-vector rotation,
rigid-transform composition, and point application. Rotation uses a fixed
30-call provider sequence; composition uses 76 arithmetic calls and one
caller-supplied square root for quaternion composition and normalization,
right-translation rotation, and translation addition; point application uses
33 arithmetic calls. All arithmetic, gate, and square-root capabilities remain
caller-supplied, with no default provider, and inverse is not included. This
slice adds no placement or resolver/source-set integration, comparison or
profile constants, diagnostics or status, public or wire API, snapshots or
fixtures, geometry or runtime behavior, or Readiness 3 activation. It is
internal reversible runway progress only and accepts or changes no contract.

The successor runway slice adds crate-private exact canonical quaternion
conjugation with the `wxyz` sign representative and `+0` canonicalization. Its
checked rigid inverse computes `t_inv = rotate(q_inv, -t)` with exactly 30
caller-provider calls and no square-root, validation gate, renormalization, or
default provider. No placement/Attachment equation, comparison or profile
selection, status or diagnostics, public or wire API, snapshot, fixture,
geometry, runtime, or Readiness 3 activation is included. It is internal,
reversible runway progress only and accepts or changes no contract.

The next runway slice adds a crate-private, nonactivating canonical placement
candidate for one admitted source-set member and its prepared canonical frame
values. It computes deterministic authored containment references, including a
nonidentity authored root, and the complete source-local Attachment equation,
including a descendant-owned mating Socket. It retains the authored and
derived attached-root local candidates separately, with their source/member
provenance, and does not compare or select a winner. Arithmetic, validation
gates, and square-root operations remain caller-supplied capabilities. This
candidate does not merge or remap members, resolve candidates, assign statuses,
create snapshots or a public API, generate geometry, or activate Readiness 3;
it is internal reversible runway progress only and accepts or changes no
contract.

The current runway also adds a crate-private source-set canonical-placement
coordinator over admitted root and dependency members. It preflights the
source-set root, member set, member roles, and inner successful-value
identities before constructing fresh caller-supplied gate, arithmetic, and
square-root capabilities for that attempted member; an upstream
canonical-frame failure
skips those factories. The coordinator retains the source-set root globally;
each deterministic member-key result retains its member key and role, exact
upstream canonical-frame outcome, and placement state as skipped, typed
failure, or success, while a member failure does not suppress other members
after full preflight. It performs no namespace remap or merge,
candidate resolution or winner selection, aggregate status or diagnostics,
snapshot or public API, geometry or runtime work, or Readiness 3 activation;
it is internal reversible runway progress only and accepts or changes no
contract.

The current runway also contains a crate-private provisional Attachment
placement comparison over `CanonicalSourceSetPlacement`. It consumes each
member's source-local local-to-parent placement, requires caller-supplied
provisional translation/quaternion tolerances, and reuses the existing exact
comparison predicates. It records deterministic per-member and per-Attachment
outcomes, including upstream/placement skips, `Agree`, `Conflict`, and typed
numeric `Skipped` results; complete provenance and both authored and
equation-derived candidates are retained, with member failure isolation. It
does not select a frozen/default profile, winner, representative, aggregate
status or diagnostics, merge/project namespaces, create a snapshot or public
API, perform geometry/runtime work, or activate Readiness 3. This completes
the currently identified internal pre-checkpoint runway; exact profile,
fixture, and resolver activation remain deferred to the recorded human stop.

The runway also contains an implemented crate-private module-binding ingredient
observation. It consumes `RestrictedSourceSetHandoff` and retains one
deterministic record per admitted `Module`: owner/role, all declaration fields
and provenance, the declaration document/namespace locator, separately matching
owner-authored dependency evidence, supplied-member existence/role/structural
root, and the present instance root with its immediate owner-local parent. It
observes ingredients only: it does not claim module-to-dependency/template
binding, compare `root_role`, derive remapped identity or an aggregate
containment edge, infer `Attachment`, verify revision/hash, assign
validity/status/diagnostics, snapshot, select a profile, or activate Readiness
3. Current structural admission guarantees exactly one member structural root
and at most one dependency declaration per namespace; the code asserts the
former and does not pretend duplicate same-locator dependencies are reachable.
It is internal reversible runway progress only and accepts or changes no
contract.

Ben's 2026-08-18 discussion approval records the next R3 direction: the first
resolver/fixture transaction is bounded to the stylized digitigrade anthropomorphic/animal-like biped
family and fixed fixture envelope; exactly one separately content-bound
authored-conflict comparison profile, distinct from expected-snapshot profiles,
is to be derived and frozen by a bounded successor experiment; and once
admitted, disagreement that fails that profile's bounds is `invalid-source`
with no successful snapshot, warning-only success, silent overwrite, repair,
or winner. Exact-zero comparison, indefinite caller-selected tolerances, and
post-hoc widening are excluded. The successor admission must bind immutable
protocol/candidate/corpus/result/receipt identities and the exact resolver
binding; failed or inconclusive runs require a new candidate identity, and
EXP-0002 attempt-001 is ineligible because `profile_binding` is null. The
recognized taxonomy and minimum valid/invalid/unsupported morphology corpus
are recorded in DR-0008 Revision 14. The Revision 13 Double-review artifacts at
exact target `117544a` remain stale evidence for Revision 14; their three
taxonomy findings were dispositioned in Revision 14. R3 remains
inactive and exact profile constants, IDs, fixtures, and activation bindings
are not selected.

Candidate locally validated and appraised by Ben on 2026-08-15: a directly
consuming primitive spatial preview
uses this exact placement result through the existing
`inspect-prepared-source`/`publish_prepared_source.py`/localhost-server flow.
The browser is limited to deterministic semantic point/line scaffolding with
Part markers, containment links, Joint endpoint links, attachment-root
distinction, labels, and front (x/y), side (z/y), and top (x/z) SVG views;
Joint frame transforms are not interpreted. It supplied the first genuine
human-appraisable visual checkpoint; Ben confirmed that its diagrams were
decodable and spatially accurate for the intended straight tail. This remains outside
the Readiness 3 activation boundary and does not claim geometry, mesh, surface,
volume, anatomical quality, rigging, pose/animation, IK, deformation, physics,
general transforms, resolver activation, or runtime evidence.

Ben's 2026-08-15 direction authorizes an autonomous runway of small, internal,
reversible preparatory PRs from this merged checkpoint toward a complete
Readiness 3 successor candidate. Routine numeric/frame, provenance, resolver,
snapshot, diagnostic, fixture, and test implementation may merge after its
required focused checks and risk-scaled review. Stop before merging the
transaction that claims Readiness 3 activation and ask Ben for its required
explicit approval; also stop earlier if work reaches a genuinely useful
rendered-form appraisal or another retained-human boundary. Preparatory merges
do not accept a Proposed DR, freeze activation-gated constants, or activate
Readiness 3.

The first runway slice adds a crate-private, fail-closed exact-dyadic arithmetic
foundation for later typed comparisons. It decodes admitted finite binary64
values without floating-point arithmetic, canonicalizes representation, and
provides checked fixed-shape ordering, addition, subtraction, multiplication,
squaring, and four-term summation under a conservative implementation safety
cap. It supplies no tolerance, profile, claim, resolver, or activation
semantics.

The numeric admission slice now also provides explicit resource-bounded
decimal admission: callers choose token-byte, significant-digit, and
exponent limits before exact conversion. It retains the strict JSON grammar,
correctly-rounded binary64 conversion, finite-subnormal support, and lexical
zero canonicalization. There is no process-wide resource default, and the
slice remains outside body-document admission and Readiness 3.

The next runway slice adds the typed scalar/translation predicate over that
foundation. It remains crate-private in default builds and is exposed only
under the non-default `provisional-r3-numeric-candidate` feature. Callers must
supply finite nonnegative absolute and relative entries explicitly; evaluation
follows the specified inclusive exact dyadic formula and checks all translation
components in fixed order. The feature's public errors map internal exact
arithmetic failures to stable classifications without exposing implementation
types. It selects no profile identity or tolerance values and has no claim,
resolver, diagnostic-status, or activation behavior.

The following runway slice adds deterministic quaternion normalization and
q/-q sign-canonicalization plumbing. Its fixed binary64 operation sequence and
validation hooks are implemented, but it has no default square-root provider:
normalization requires an explicitly injected provider whose environment the
caller has attested. The candidate surface is available only under the same
non-default experimental feature, with public error types kept independent of
internal arithmetic details. No near-zero/drift/range constants or profile are
selected, so this slice cannot normalize production source or activate
quaternion semantics.

The next runway slice adds the exact canonical-tuple quaternion comparison
predicate over already normalized carriers. It uses exact dyadic dot sign
selection (`0` chooses positive), fixed four-component squared distance, and
an inclusive explicit `(2H)^2` bound. It accepts H only when supplied by the
caller, chooses no H, profile identity, fallback, or angular interpretation,
and remains outside Readiness 3.

Ben approved the following deferred planning direction on 2026-08-09 for any
future activation. It is recorded here without accepting or revising either DR:

- A repair after evidence starts would create a new immutable comparison epoch,
  admitted prospectively and independently, with a full primary rerun.
- Registration would define enforceable `C` accounting and extend the
  confirmatory record/template.
- The mandatory visual floor would use at least three
  implementation/tuning-independent deterministic panel adjudicators.
- Outcome-changing failure attribution would use a preregistered diagnostic
  tree and independent verification.
- Bundle-outcome closure and component-attribution completion would remain
  separate, with explicit causes for `U`.

## Current outcome

The foundation scaffold and governance process are integrated. Accepted DR-0001
Revision 5 remains the operative governance baseline while DR-0001 Revision 6
is Proposed transition guidance: Ben approved its workflow direction, but
its current review is Complete and formal acceptance remains pending Ben's
disposition. DR-0002 Revision 11, DR-0006 Revision 12, DR-0011 Revision 15,
and DR-0012 Revision 14 are Accepted with Owner approval Approved by Ben and
Date decided 2026-08-17; DR-0003, DR-0004, DR-0005, DR-0007, and DR-0008 remain
Proposed with their review and owner-disposition history preserved. DR-0013
Revision 12 is Accepted with Owner approval Approved by Ben and Date decided
2026-08-13. Ben's CK-KICK-012 Batch 5, Batch 6, F1–F7, Batch 8, Batch 9, Batch
10, Batch 11, Batch 12, and Batch 13 product/specification/architecture/project
material remains Proposed where owned by the other records; DR-0013's accepted
platform boundary is recorded below. The current six-record set is DR-0002
Revision 11, DR-0006 Revision 12, DR-0008 Revision 14, DR-0011 Revision 15,
DR-0012 Revision 14, and DR-0013 Revision 12. DR-0002 Revision 11, DR-0006
Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14 are Accepted with
Owner approval Approved by Ben and Review Complete; DR-0008 Revision 14
remains Proposed with Owner approval Pending and Review Pending. The Revision 13
Double-review artifacts at exact target `117544a` are stale evidence; Review 01
found no findings and Review 02 recommended Revise at High confidence with
three taxonomy findings, dispositioned in Revision 14. The Revision 11 Double
review at exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a` is stale historical evidence.
The original Batch 13 review at exact commit
`8c38c501eb1262a1b85af0b8605220625601772f` produced D1–D3/P1–P3, which were
dispositioned in DR-0006/0011/0012/0013 Revisions 10/13/12/10. The earlier-
predecessor review at exact commit `763cff22d10f6491a05a28312a25250704543dcf`
produced G1/G2 and T1–T4; its artifacts are stale for these successors. G1/G2
were fixed mechanically, T1–T3 were resolved, and T4 remains unselected and
deferred, requiring Ben's retained-human disposition before adapter profile/
schema activation; it does not block the current Rust implementation slice. The
immediate-predecessor review at exact commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in these revisions. The 9c governance pass corrected two mechanical
history-label issues and its technical pass found no findings / Ready for PR at
High confidence. The review artifacts remain preserved evidence. DR-0013 is
accepted and Readiness 1 is triggered/active for the Cargo workspace, compiler/
core library shell, and thin CLI shell. The provisional structural address/
index, validator, and inspection command are preparatory implementation. The
exact schema, manifest,
nine fixtures, parser/bootstrap, and preflight are the active Readiness 2
transaction after the recorded merge and post-merge identity recomputation;
the later resolver, adapter, experiment, and geometry gates remain inactive.
The current review state and later activation obligations
are recorded below.

CK-KICK-013 is active with its accepted Rust-first platform boundary and
Readiness 1 shell trigger. DR-0013 Revision 12 has Owner approval Approved by Ben,
Date decided 2026-08-13, and Review Complete after
the current Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The original 8c38c501 Batch 13
review produced D/P findings later dispositioned in Revision 10. The earlier
predecessor 763cff22 review produced G1/G2 and T1–T4; G1/G2 were fixed
mechanically, T1–T3 were resolved, and T4 remains unselected and deferred,
requiring Ben's retained-human disposition before adapter profile/schema
activation; it does not block the current Rust implementation slice.
The immediate-predecessor 9b96d18 review is stale; its findings were corrected
in the current revisions. The 9c technical pass found no findings / Ready for
PR at High confidence. Review Complete remains preserved evidence; it does not
replace Ben's acceptance. Readiness 1 is triggered/active for the Cargo
workspace, compiler/core library shell, and thin CLI shell. The provisional
structural address/index, validator, and inspection command remain preparatory.
The exact
schema, manifest, nine fixtures, parser/bootstrap, and preflight are the active
Readiness 2 transaction under the admission record; the distinct Readiness 3
resolver/snapshot transaction is not active.
The review at exact target commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` found stale historical/current
labels, an omitted retained-human checkpoint for T4, an incomplete comparator
precedence/rank gate, product-level sqrt/norm ambiguity, and a stray DR-0006
word. These findings were corrected in current successor revisions
12/15/14/12; that review is stale for the successors. T4 remains
unselected and requires Ben's retained-human disposition before adapter
profile/schema activation; it does not block the current Rust implementation
slice.
The later activation order remains numeric/frame semantics, semantic addresses,
canonical data/digests, diagnostics, and then a distinct Readiness 3 successor
transaction. Those later gates remain inactive until their Proposed contracts
and explicit prerequisites are admitted.
Readiness 1 is now active: accepted DR-0013 activates the Cargo workspace,
compiler/core library shell, and thin CLI shell; the provisional structural
address/index, validator, and inspection command are preparatory only; a
versioned, preflighted fixture manifest, its listed
files, exact JSON Schema, and parser/bootstrap are now active together under
the Readiness 2 admission; the distinct Readiness 3 transaction then activates
canonical numeric/frame rules plus frozen expected graph outputs and semantic
resolver/in-memory snapshot handoff; and a working
resolver plus provisional geometry profile and project-owned seam activates
exploratory Stage 1 geometry. The proposal includes a stable
Rust semantic/compiler core, thin CLI, versioned project-owned
backend-neutral GeometryRequest/GeometryResult seam, one authoritative build
envelope across geometry and publication, immutable build-scoped sibling
staging, manifest-last atomic no-replace publication, identity/path/hash/size
validation, and rejection of symlinked, unlisted, incomplete, mixed-build, or
stale bundles. The [Proposed build-operation contract](../../spec/build-operation/README.md)
owns candidate-to-committed artifact identity, deterministic output-root
targeting, idempotent publication, post-collision identity/lineage/hash
inspection, target conflict, and lineage-checked inspection. `output-failure`
covers trusted derived-output/publication
failure; every invocation has a unique attempt identity, while deterministic
build-request identity exists once the complete outcome-affecting request is
established; artifact identity exists only after successful publication, and
artifact inspection is a separate read operation. Future workers require protocol/version
negotiation, bounded resources/time, crash/timeout/resource mapping, output
validation, and compiler survival. Python remains for disposable experiments,
evidence/render tooling, and visual workbench tasks, not as a production
compiler dependency. Build requests include all outcome-affecting source/
dependency, compiler/toolchain, contract/schema/profile, configuration/seed,
backend-capability/protocol, and target-platform inputs; attempt identity is
unique for tracing only. Candidate identity derives from deterministic request,
artifact role, and identity-rule revision. Canonical serialization/hash is
required before activation. The initial filesystem profile is tested local WSL
`/home` only, excluding `/mnt/c`, network, removable, and unspecified
filesystems; process-crash-safe namespace publication is required without a
sudden-power-loss claim. Producer/output trust is distinct from
coordinator/reporter/publisher trust, and worker trust loss cannot be
rehabilitated by validation. The [fixture-manifest specification](../../spec/fixture-manifest/README.md)
owns immutable reviewed-tree/payload binding, append-only admissions, and the
Readiness 2/3 conceptual corpus. The first reference path is WSL2 x86_64 GNU;
native-Linux portability smoke follows later. Exact
rust-toolchain.toml, Cargo.lock, target/profile/rustc -Vv/reference metadata,
and lightweight license/unsafe/native/portability/security dependency review
are required without Git pinning or audit bureaucracy. Final serialization,
compatibility, and geometry backend remain deferred.

No accepted production surface architecture, geometry backend, numeric budget,
exact fixture, schema, runtime field, topology, or package compatibility is
selected. CK-KICK-010's approved grid, field, bundle, determinism, and
structural-gate values are debug-only spike inputs and do not change that
boundary. Batch 13 additionally keeps future adapters separate: signed
permutation `C` plus finite positive scale `s`, storage/output-only default or
optional runtime-conformance tier, explicit target precision/domain narrowing,
read-only FTZ/DAZ inspection, and any separately evaluated runtime subnormal
probe. This is Proposed planning material only.

## Current review and future activation obligations

DR-0008 Revision 14 is the current Proposed morphology-boundary revision, with
Owner approval Pending and Review status Pending. Its Revision 13 Double-review
artifacts at exact target `117544a` are preserved stale evidence; their three
taxonomy findings were dispositioned in Revision 14. R3 remains inactive, and
no exact profile constants, IDs, fixture files, or activation record are
selected.

Batch 11, Batch 12, and Batch 13 record discussion-approved history. The
accepted DR-0002/0006/0011/0012 semantic-foundation directions cover typed
semantic addresses, canonical bytes/digest domains, numeric/frame comparison
semantics, and a small diagnostic-registry direction; concrete profiles,
constants, and activation bindings remain Proposed or gated.
Exact numeric bounds remain evidence-dependent; the planned
[numeric/frame profile experiment](../research/numeric-frame-profile-experiment.md)
remains registered as planned, with open evidence closure and no technology
outcome. Attempt-001 is the completed phase-one run at source commit
`d88f5eca3ad3c0c0cb00dcf7dd012471be979305`; its immutable result and receipt
are indexed in the [human-readable results summary](../../experiments/EXP-0002-numeric-frame-profile/RESULTS.md).
Its phase-one package is the named
exact-artifact persistent-conformance evaluation
`ck.exp-0002.phase1-persistent-conformance-v1`, with one persistent candidate
process and the fixed development → held-out → adversarial order. Held-out is
non-tuning, not blind or process-isolated; environment observations are
workload-position-conditioned. The exact phase-one claim is limited to this
identified candidate and runner producing 49 exact frozen case adjudications
plus runner classifications for 26 registered named case groups, including
represented boundary/resource/error/environment observations. Only
`lexical-equivalence`, `signed-zero-canonicalization`, and `environment-repeat`
have explicit cross-case checks; the other groupings organize member-case
outcomes. Role isolation, fresh-process behavior, order independence,
repeatability, broad generalization, production-domain suitability, profile
selection, and technology outcome are not inferable.

The package preregisters implemented budgets of 16,384 frame bytes, 256 UTF-8
wire-request-ID bytes, 65,536 stdout bytes, 65,536 stderr bytes, 2.0 seconds
I/O, 2.0 seconds shutdown, 0.02 seconds trailing quiet, 128 cases per corpus,
256 total cases, 256 relations, 4,096 decimal-oracle work digits, and a
268435456-byte (256 MiB) maximum identity artifact read. Its identity object
uses stream-hashed-before-and-after-execution for candidate artifacts and
runner modules, assumes controlled-local-no-adversarial-mid-run-replace-and-
restore, and treats candidate build context as observational-not-provenance.
This is a pragmatic controlled-local pre/post content-and-stat stability check,
not proof against adversarial replace-and-restore; the binary hash remains the
artifact identity. Current `experimental_tolerances` A/R entries are
experimental inputs, not selected profile constants. A completed execution
remains `run_status: complete`; any exact failure takes evidence precedence over
inconclusive/unsupported while counts retain both, and candidate/environment
unsupported is inconclusive only when no failure exists. A fix after observing
a frozen-role result creates a new candidate evaluation and must not overwrite
or be called the original held-out result. The broader Proposed protocol still
requires preregistered intended domains, semantic error budgets, correctly
rounded decimal-admission
rules, fixed operation order and compiler floating-point controls,
rational/ULP boundaries, deterministic normalization/square-root fixtures,
offline H derivation, structured claim identity/order fixtures,
exact/higher-precision independent oracles, later fixtures and checks,
condition estimates, and a validation margin whose formula/constant remain
open. The normative common-frame comparator, exact dyadic arithmetic,
normalization/sign direction, claim-ID, and sorted-pair direction are accepted
semantic-foundation directions; concrete profiles, constants, ranges, margins/
error formula, and deterministic evaluation bindings remain Proposed or gated.
Future adapter evidence covers signed permutation/scale, storage/output and
runtime tiers, precision/domain narrowing, and separately evaluated FTZ/DAZ/
subnormal runtime probes. The remaining activation order is numeric/frame,
address, canonical data, diagnostics, and then a distinct Readiness 3
expected-snapshot/comparison transaction. No later gate or implementation
package beyond the admitted Readiness 2 transaction activates from this status
entry.

Diagnostic compatibility remains Proposed: nine initial domains are
source-admission, dependency, semantic-identity, graph-structure,
frame-numeric, resource, execution-trust, publication, and inspection, with
one tiny mandatory bootstrap registry/profile for unknown registry/profile
negotiation. The exact `ck.diagnostic.r2` candidate codes are documented and
used by the admitted parser/preflight transaction, but the focused diagnostic
owner remains Proposed and no later diagnostic contract is accepted by this
activation. Readiness implementation binding remains a separate scoped
content-identity input from the fixture payload and expected snapshots; the
Readiness 2 binding is active while any Readiness 3 binding remains gated.

The original Batch 13 Double review examined exact target commit
`8c38c501eb1262a1b85af0b8605220625601772f` and produced D1–D3/P1–P3; those
were dispositioned in the immediate successor revisions 10/13/12/10. The
earlier-predecessor review examined exact target commit
`763cff22d10f6491a05a28312a25250704543dcf` and produced G1/G2 and T1–T4; its
artifacts are stale for the current revisions. G1/G2 were fixed mechanically,
T1–T3 were resolved, and T4 remains unselected and deferred, requiring Ben's
retained-human disposition before adapter profile/schema activation; it does not
block the current preparatory Rust slices. The immediate-predecessor review examined
exact target `9b96d18b115126ef09e54ad8c6f21749d5559ff6`; its findings were
corrected in the current revisions. DR-0002 Revision 11's current review
examined exact target `6cf17270fda2827756c24a8d0fb301bef358f98f`; the current
Double reviews for DR-0006 Revision 12, DR-0011 Revision 15, DR-0012 Revision
14, and DR-0013 Revision 12 examined exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The latter governance pass
corrected two mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. The review artifacts remain preserved evidence;
DR-0002 Revision 11, DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012
Revision 14 are Accepted with Owner approval Approved by Ben. DR-0008 Revision
11 remains Proposed with Owner approval Pending. DR-0013 Revision 12 is
Accepted with Owner approval Approved by Ben.
Readiness 1 is triggered/active for the Cargo workspace, compiler/core library
shell, and thin CLI shell. The exact schema, manifest, nine fixtures,
parser/bootstrap, and preflight are the active Readiness 2 transaction after
the merged-commit identity recomputation; the later resolver, adapter,
experiment, and geometry gates are inactive.

The prior Double-review findings and ten artifacts are preserved in the
[decision registry](../decisions/registry.md) as stale historical evidence.
The completed Batch 9 Double review examined the exact target commit
`6cf17270fda2827756c24a8d0fb301bef358f` in two Sol medium passes: Review 01
used the contract/schema/determinism/security lens; Review 02 used the
platform/failure/reversibility/publication lens.

Recommendations (Review 01 / Review 02) are: DR-0002 — Accept High / Accept
Medium; DR-0006 — Revise High / Revise High; DR-0008 — Accept High / Accept High;
DR-0011 — Accept High / Accept High; DR-0012 — Accept High / Accept Medium; and
DR-0013 — Revise High / Revise High. These are review recommendations only, not
Ben acceptance. Review Complete is evidence, not a clean review or acceptance.

The consolidated Batch 9 findings are now discussion-resolved by Batch 10 and
remain preserved as stale historical review history:

- C1 — High — stable request/attempt/candidate/committed identity, retry, and
  concurrent publication (DR-0006/0013).
- C2 — High — filesystem profile, crash durability, and TOCTOU/tamper-safe
  inspection (DR-0013).
- C3 — High — worker-output versus coordinator/reporter/publisher trust
  (DR-0013).
- C4 — High — immutable external binding and supersession/rollback for
  Readiness 2 admission (DR-0013).
- C5 — Medium — closed artifact-inspection non-success status algebra
  (DR-0013).

Batch 10 integrated its approved resolutions as stale Proposed historical
material, and Batch 11 integrated the approved machine-contract resolutions as
current Proposed material:
separate request/attempt/candidate identities and deterministic retry/collision
rules; the initial WSL `/home` filesystem profile and process-crash-safe
namespace publication boundary; separate inspection statuses and shared
completeness/diagnostic conventions; producer/output versus
coordinator/reporter/publisher trust; immutable fixture-manifest reviewed-tree
and activation-payload binding with append-only successor/deactivation rules;
and the conceptual body-document shape, typed collections, basis/frame/profile,
and omission/default rules. Batch 11 adds the typed semantic-address,
numeric/frame, canonical-data, and diagnostic profiles; Batch 12/13 improves
the numeric evidence protocol and makes DR-0006 Revision 12, DR-0011 Revision
15, DR-0012 Revision 14, and DR-0013 Revision 12 current. DR-0006 Revision 12,
DR-0011 Revision 15, and DR-0012 Revision 14 are Accepted with Owner approval
Approved by Ben and Review Complete after the current Double review at exact
target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. Prior Batch 13 review evidence is stale for
these revisions; G1/G2 were fixed mechanically, T1–T3 were resolved, and T4
remains unselected and deferred, requiring Ben's retained-human disposition
before adapter profile/schema activation; it does not block the current Rust
implementation slice. DR-0013 Readiness 1 is triggered/active for the Cargo workspace,
compiler/core library shell, and thin CLI shell. The exact schema, manifest,
nine fixtures, parser/bootstrap, and preflight are the active Readiness 2
transaction under the admission record; the distinct Readiness 3
resolver/snapshot transaction is not active.
DR-0002 Revision 11 is Accepted with Owner approval Approved by Ben and Review
Complete; DR-0008 Revision 14 remains Proposed with Owner approval Pending and
Review Pending; the prior Revision 13 Double-review artifacts at exact target
`117544a` are stale evidence.

Historical inactive planning note: containment/topology validation was not an
honest immediate next slice because source-local rules were already validated,
while aggregate semantics lacked an accepted module/template binding edge. The
then-recorded next safe autonomous implementation was the six-case
development-only realistic composed-transform extension for profile
discrimination. The Active runway now supersedes that next-step selection.
Exact aggregate
module-binding semantics and Readiness 3 activation remain gated; the phase-two
development run remains non-authoritative and insufficient to choose
strict/micro/stress. Readiness 1 and Readiness 2 remain active while Readiness 3
and later transactions remain gated. The sole current retained-human
checkpoint is the shared-pose structural embodiment gallery described in the
Active runway section above. The former authored-form and earlier
rendered-creature or primitive spatial-preview checkpoints are historical and
inactive.
The main thread will autonomously resolve technical correctness findings or
record evidence-dependent triggers under the DR-0001 Revision 6 transition
direction; only a retained-human product, architecture-boundary, material
trade-off, or external-impact finding returns to Ben. No proposal is silently
accepted. The four semantic-foundation acceptances authorize autonomous
construction/review of the exact Readiness 3 successor candidate but do not
activate Readiness 3; no later implementation/readiness gate activates while
its own prerequisites or owning records remain Proposed.
Earlier Batch 8/9 and other
review artifacts remain preserved as stale historical evidence.
Do not activate the Readiness 3 resolver, adapters, or geometry work while
their successor admission, content-identity, and other prerequisites remain
pending.

Two nonblocking obligations apply to later activation: before an isolated
worker activates, define containment, process-tree, output/log/handle/network/
protocol/cleanup/status bounds appropriate to its threat model; before making
evidence-bearing portability or performance claims, freeze the lightweight
exact build/reference environment and dependency source/feature inputs, with
native smoke preceding native portability claims.

On 2026-08-09 Ben settled CK-KICK-012 Batch 1 in discussion. On 2026-08-11
he approved seven Batch 1 resolutions: one unique owner per source namespace
with authored deterministic collision-free remapping for collisions; one
operation-result envelope for every phase and diagnostic, with an optional
validated snapshot only for valid-supported success; required functional
articulation roles; frozen fixture outcomes and primary diagnostics; typed
vocabulary; explicit measurement ownership and conflict diagnostics; and
declared source frames normalized to a revisioned canonical basis with
provenance. He also discussion-approved the Batch 4 encoding, resolution,
compatibility, resource, and fixture resolutions, the six Batch 5 blocker
resolutions, and the Batch 6 status/primary, descendant Socket, and
Attachment-cardinality resolutions, and the Batch 8/9 completeness, module,
transform, readiness, and build/publication resolutions, followed by the
Batch 11 machine-contract resolutions. These discussion approvals do not accept
or silently replace the DRs. The canonical documents now state explicit Part
containment, descendant Socket Attachment placement, canonical resolved frame
records, the closed operation/bootstrap/status/resource contract, the
in-memory snapshot handoff, the build-operation owner, and the resolved
diagnostic/cardinality rules. Earlier review evidence is stale after these
revisions. The Batch 8/9/10/11 resolutions were discussion-approved material at
the time, not acceptance or a clean review; the current DR-0002/0006/0011/0012
semantic-foundation revisions are now accepted under the explicit 2026-08-17
Option 1 decision.
The cross-cutting proposal is [DR-0012: initial
body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The [Proposed body-document contract](../../spec/body-document/README.md),
[Proposed body-graph contract](../../spec/body-graph/README.md),
[Proposed fixture-manifest contract](../../spec/fixture-manifest/README.md),
and [Proposed build-operation contract](../../spec/build-operation/README.md)
are now active canonical specification areas. No implementation package, machine schema,
numeric limit, exact fixture, or geometry backend is selected; the Batch 11
canonical basis and machine profiles are accepted in direction, while exact
constants and activation bindings remain gated;
the accepted Rust/Cargo platform remains bounded to the active Readiness 1
workspace/compiler-core/thin-CLI shell boundary; the provisional structural
slice does not activate Readiness 3.
The meaning and enforcement details of an exact dependency revision remain a
nonblocking obligation before external authored dependencies activate.

## Current round and work state

- Rounds 0–5 are integrated history: governance, product boundary, semantic
  source/identity/operation proposals, compile/runtime boundary, first-proof
  charter, morphology envelope, and provisional visual criteria.
- CK-KICK-008 surface research is integrated as parked confirmatory guidance;
  it is not a blocker and does not require another review round now.
- CK-KICK-009 is complete for the disposable exploratory geometry host:
  Python with NumPy, scikit-image marching cubes, and trimesh, all retained as
  replaceable discovery adapters rather than production selections.
- CK-KICK-010 is implemented with bounded local evidence recorded in
  [`experiments/ck-kick-010-walking-skeleton/RESULTS.md`](../../experiments/ck-kick-010-walking-skeleton/RESULTS.md);
  its selected Single independent implementation review is complete with five
  substantive findings and a trailing-whitespace finding dispositioned in that
  record, not clean. Its provisional inputs and observations do not create a
  schema, DR, Stage 1 result, or production contract, and the evidence record
  does not register `EXP-0001`.
- The reusable local visual-review gallery is implemented at
  [`dev-tools/visual-review/`](../../dev-tools/visual-review/); current
  verification is complete for the implementation. `py_compile`, all 14
  focused unit/integration tests, `git diff --check`, local HTTP smoke for the
  session API and PNG serving, and Ben's real Chromium localhost browser smoke
  passed. One fresh Luna xhigh independent implementation review found three
  filesystem race defects (source replacement during publish, incomplete
  failure cleanup, and parent-directory redirection for assets/responses). A
  follow-up hardening attempt was rejected as disproportionate after growing
  the local utility by roughly 1,100 implementation/test lines while still not
  closing same-user replacement races. Those races are now explicitly outside
  the stable, private, single-user localhost threat model; the existing
  no-follow, path, origin, token, file-type, staging, and atomic-response checks
  remain. T3 product-native browser automation was unavailable; Ben
  subsequently confirmed the revised `subject_context` panel was working in
  his real Chromium browser.
  This remains presentation plumbing only and does not alter the CK-KICK-010
  conclusion or claim visual evidence or Stage 1.
- CK-KICK-011 follows useful exploratory evidence. A formal comparative
  surface decision is optional and risk-driven, not automatic.
- CK-KICK-012 is active with Batches 1, 4, 5, 6, F1–F3, Batch 8, Batch 9, Batch
  10, Batch 11, Batch 12, and Batch 13 integrated as reviewed documentation; its parser/resolver and
  fixture-admission proposals establish the four Proposed specification families. The exact Readiness 2
  schema, manifest, nine fixtures, Rust parser/bootstrap, and Python preflight
  are active under the Readiness 2 admission record; later resolver behavior and
  compiler-consumed Readiness 3 fixtures remain unactivated. The separate
  Readiness 1 Cargo shell is active. The current six-record set is DR-0002
  Revision 11, DR-0006 Revision 12, DR-0008 Revision 14, DR-0011 Revision 15,
  DR-0012 Revision 14, and DR-0013 Revision 12. DR-0002 Revision 11, DR-0006
  Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14 are Accepted with
  Owner approval Approved by Ben and Review Complete; DR-0008 Revision 14
  remains Proposed with Owner approval Pending and Review Pending. The Revision 13
  Double-review artifacts at exact target `117544a` are stale evidence; Review 01
  found no findings and Review 02 recommended Revise at High confidence with
  three taxonomy findings, dispositioned in Revision 14. The Revision 11 Double
  review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a` is stale historical evidence.
  Prior Batch
  13 review evidence is stale historical evidence; G1/G2 were fixed
  mechanically, T1–T3 were resolved, and T4 remains unselected and deferred,
  requiring Ben's retained-human disposition before adapter profile/schema
  activation; it does not block the current preparatory Rust slices. The immediate-predecessor 9b96d18 review is stale; its findings were corrected. The 9c governance pass corrected two mechanical history-label issues and its technical pass found no findings / Ready for PR at High confidence.
  The completed Batch 9 Double review targeted
  `6cf17270fda2827756c24a8d0fb301bef358f` and is stale for the revised records;
  it is evidence, not acceptance.
  See [Current review and future activation obligations](#current-review-and-future-activation-obligations).
  It does not
  depend on CK-KICK-011.
- CK-KICK-013 is active with its accepted Rust-first/Cargo platform boundary
  and Readiness 1 shell trigger. DR-0013 Revision 12 has Owner approval
  Approved by Ben and Review Complete after the current Double review at exact
  target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior Batch 13 review evidence is stale historical evidence, G1/G2 were
  fixed mechanically, T1–T3 were resolved, and T4 remains unselected and
deferred, requiring Ben's retained-human disposition before adapter
profile/schema activation; it does not block the current Rust implementation
slice. Readiness 1 is triggered/active for the Cargo workspace, compiler/core
library shell, and thin CLI shell; the provisional structural address/index,
validator, and inspection command remain preparatory. The immediate-predecessor
9b96d18 review is stale; its findings were corrected. Its later readiness stages gate
  shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry respectively. The disposable Python
  discovery host remains distinct from the accepted production platform.

## Active work

- Advance direct Rust source-preparation and engine-neutral runtime-package
  prerequisites toward the bounded Godot feasibility checkpoint. Keep the
  host-evaluation evidence separate from accepted contracts and
  record its source and measurement conditions.
- Keep the admitted Readiness 2 parser/bootstrap/schema/manifest/fixture
  transaction active, while the distinct Readiness 3 resolver/snapshot
  transaction, adapter profile/schema, runtime package activation, and host
  adapter remain gated. Do not treat a Godot feasibility result as Readiness 3
  success or as a permanent engine/solver/package decision.
- The main thread owns the retained-human boundary: it may integrate bounded
  Rust/package prerequisites, but stops before any Readiness 3 or adapter
  activation decision. Any performance claim requires reproducible benchmark
  and named hardware-profile evidence.
- Preserve the accepted governance process and all historical decision/review
  evidence without reopening the parked confirmatory protocol.

## Decisions and review state

The [decision registry](../decisions/registry.md) is the index for exact DR
metadata. Current non-governance decisions and proposals include:

- [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
  source set and resolved body graph — Revision 11, Accepted, Owner approval
  Approved by Ben, Date decided 2026-08-17, Review Complete; Readiness 3 remains
  inactive pending its exact successor transaction.
- [DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md),
  compiled avatar and bounded real-time execution — Revision 2, Proposed,
  Review Complete, owner disposition pending.
- [DR-0004](../decisions/DR-0004-external-automation-through-cli-and-api.md),
  shared domain operations — Revision 2, Proposed, Review Complete, owner
  disposition pending.
- [DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md),
  initial product boundary — Revision 1, Proposed, Review Complete, owner
  disposition pending.
- [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
  semantic and artifact identity — Revision 12, Accepted, Owner approval
  Approved by Ben, Date decided 2026-08-17, Review Complete after the current
  Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`;
  prior Batch 13 review evidence is stale historical evidence.
- [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md) and
  [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
  first-proof and morphology boundaries — DR-0007 remains Proposed with its
  current review; DR-0008 Revision 14 is Proposed, Owner approval Pending,
  Review Pending; the Revision 13 Double review at exact target `117544a` is
  stale historical evidence. The Revision 11 review is stale
  historical evidence.
- [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
  semantic vocabulary, measurements, and coordinate frames — Revision 15,
  Accepted, Owner approval Approved by Ben, Date decided 2026-08-17, Review
  Complete after the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior Batch 13 review evidence is
  stale historical evidence.
- [DR-0012](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
  initial body-document encoding, resolution, and compatibility — Revision 14,
  Accepted, Owner approval Approved by Ben, Date decided 2026-08-17, Review
  Complete after the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior Batch 13 review evidence is
  stale historical evidence.
- DR-0013, Rust-first production semantic/compiler platform — Revision 12,
  Accepted, Owner approval Approved by Ben, Date decided 2026-08-13, Review Complete
  after the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; Readiness 1 is triggered/active.
- [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  and [DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  are parked as described in [Current activation state](#current-activation-state).

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Operational structure under Accepted DR-0001 Revision 5 |
| Decision-record and review workflow | partial | unverified | Governance accepted; technical/product proposals remain provisional |
| Research/experiment workflow | partial | unverified | Lightweight template exists; EXP-0002 remains planned with open evidence closure and no technology outcome; attempt-001 completed and passed its 49 cases and 26 registered relations, while broader obligations remain open |
| Body specification | partial | unverified | Proposed body-document, body-graph, build-operation, fixture-manifest, and Batch 11/12/13 focused profiles include discussion-approved updates; the Readiness 2 schema, manifest, nine fixtures, parser/bootstrap, and preflight are active under the admission record, while DR-0002 Revision 11, DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14 are Accepted with Owner approval Approved by Ben; DR-0008 remains Revision 14 Proposed with current review Pending |
| Build-operation contract | partial | unverified | Proposed canonical public build/output owner exists; serialization, implementation, and artifact store remain unactivated |
| Production implementation platform | partial | proven | CK-KICK-013/DR-0013 Revision 12 is Accepted with Owner approval Approved by Ben; the Readiness 1 Cargo workspace, compiler/core library shell, and thin CLI shell pass pinned-toolchain checks. Readiness 2's exact schema, manifest, nine fixtures, parser/bootstrap, and preflight are active after merged commit `766992ab089687e9b1496574e8ffa721388d96f3` / PR #6 and successful post-merge identity recomputation. PR #9, the inspectable biped structure workflow, is merged at `565c32bd35215e23d737fb333604382d3e6958ab`; its structural index/validator/inspection remain preparatory. The public single-source preparation operation and internal numeric/frame-preparation helpers remain preparatory; helpers cannot bypass body-document admission, and distinct Readiness 3, adapter, and exploratory geometry remain gated |
| Creature compiler | partial | unverified | Disposable CK-KICK-010 walking skeleton implemented; this is not a production compiler |
| CK-KICK-010 walking skeleton | implemented | audited | Valid/invalid local evidence and the selected Single independent review are complete; five substantive findings plus whitespace were dispositioned in RESULTS, not clean; this is not a production compiler |
| Local visual-review gallery | implemented | audited | Focused tests and local HTTP/browser smoke passed; the PR #113 gallery is bounded exploratory surface evidence, while `subject_context` remains presentation-only and no formal Stage 1 claim is made |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter is selected and no Readiness 3 result exists; the current provisional experiment-local two-avatar carrier and real Skeleton3D/Skin binding probe remain disposable prerequisite evidence only |

## Historical immediate next actions (inactive)

The following section is preserved historical planning context from the earlier
Readiness 3 preparation runway. It is inactive and must not be treated as the
current next actions; the `Active runway` above and the [current operational
handover](current-handover.md) govern current continuation.

Ben authorized an autonomous runway on 2026-08-15 for small, internal,
reversible preparation PRs. The latest relevant checkpoint is PR #65, “Add the
phase-two authored-conflict development runner,” merged at commit
`9bcf2172d0433d35d2d96e6841a83890899d11e9`. The main thread may merge clean
internal bridge
and document-wide preparation/provenance slices along the named runway, but
this is not blanket authority outside it and does not waive real user-visible
or direction-setting decisions. Continue the autonomous preparatory runway
until either the exact Readiness 3 successor/activation decision requires Ben,
another genuine direction-setting decision appears, or the next genuinely
useful visual result is ready. Earlier permission to merge a specific PR does not
authorize merging later PRs outside this recorded runway.

- Use the active Readiness 2 parser/bootstrap and admitted schema, manifest, and
  fixture transaction as the implementation foundation; take bounded
  document-wide resolver preparation/provenance traversal and successor
  evidence. Keep adapters, geometry, and later packages gated.
- For EXP-0002 phase three, retain the development-only deterministic
  ledger/generator/manifests, independent adapter/oracle/scorer/receipt
  tooling, in-memory result/receipt/index contracts, read-only Gate B preflight,
  and exact execution tooling as execution-disabled preparation. The current
  v3 successor is materialized under execution-tool/materialization snapshot
  `762b04b8db3397cb1885d94236ad5d47cb321830`, schema
  `ck.exp-0002.phase3.freeze-manifest-3`, and manifest SHA-256
  `faafe7680fcc3509a245dde6759396a1391e02c40891128ca44d007726adef85`.
  The later commit containing those exact v3 bytes still needs fresh current-
  revision Double review, followed by execution-disabled Gate B admission and
  artifact-custody records. Stop for Ben before creating an exact-attempt or
  native-dispatch authorization, and before any exact attempt, native dispatch,
  profile-value validation, production binding, or Readiness 3 activation.
- Keep Readiness 1 limited to the Cargo workspace, compiler/core library shell,
  and thin CLI shell. Keep the provisional structural address/index, validator,
  and `inspect-structure` command outside the formal Readiness 3 activation
  boundary; Readiness 2 remains active within its recorded
  parser/bootstrap/schema/manifest/fixture boundary.
- Leave DR-0009/0010 parked unless the activation trigger occurs or Ben
  explicitly reactivates them.

## Explicitly not started

- Later implementation packages beyond the active Readiness 2
  parser/bootstrap/schema/manifest/fixture transaction.
- Large asset or dataset storage.
- External mesh conformance.
- Production distribution, operations, or release automation.

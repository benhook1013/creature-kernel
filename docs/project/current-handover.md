# Current operational handover

Snapshot: 2026-08-23 NZST

This is a concise operational handoff for continuing the current runway in the
Codex app. It is not a new authority owner: `docs/project/status.md` remains
the canonical owner of the active runway, and the required reading order in
`AGENTS.md` still applies.

## Where to continue

- Primary checkout: `/home/ben/src/creature-kernel` — `main` and
  `origin/main` are at merged PR #110 commit
  `a45920df1322bafbbd56ea6939837f8b0b9b8b33`.
- Active worktree: `/home/ben/src/creature-kernel-worktrees/authored-arm-profiles`
  — branch `implementation/authored-arm-profiles`, based on that commit; no PR
  exists yet for the current work.
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
prerequisite and remains evidence on the runway toward the unchanged complete
authored-form expressivity gallery checkpoint. Producer v8 adds source-authored
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

The shoulder/arm authored-control slice is now a completed local candidate in
the active worktree. Producer v9 carries `authored_arm_profile` v1 with a
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
the browser, evidence, and HTTP scenarios. This is still an internal
candidate: no PR exists, no merge has occurred, and no human appraisal is
requested. The final human stop remains the complete authored-form gallery;
the candidate does not claim that gallery is complete.

The arm-slice checks include 415 Rust workspace tests (47 CLI and 368 core),
52 successor tests, 34 publisher tests, and 25 browser/parity tests passing;
the unchanged baseline suite's 56 tests were already green. Rust formatting,
Clippy with warnings denied, documentation validation, and `git diff --check`
pass. The final adversarial review, PR, CI, and merge gates remain pending.

The non-blocking rejected-POST secondary-400 logging concern is deferred
unrelated usability cleanup, not an arm blocker. After those review/PR/CI/merge
gates, the next direct region slice toward the same named checkpoint is
pelvis/leg authored control.

PR #109 also contained Ben-approved neutral public-facing wording cleanup and
accepted MIT OR Apache-2.0 licensing DR-0014. That ancillary work does not
change the active runway. Root license files, README, and CONTRIBUTING carry the
current terms; Cargo package metadata is deliberately deferred because the
parked Phase 3 evidence closure exact-binds the affected manifest bytes.

The named human checkpoint remains the complete authored-form expressivity
gallery. Continue through subsequent bounded region slices and small reviewed
PRs until that gallery is ready, unless a retained-human blocker or direction
appears.

## Gallery and service

- Gallery: [successor surface checkpoint](http://localhost:8765/review/successor-surface-checkpoint)
- Persistent root: `/home/ben/.cache/creature-kernel/visual-reviews`
- The checkpoint contains `review.json` and exactly 8 PNGs; it has no
  `response.json` as of this handover.
- User service:
  `/home/ben/.config/systemd/user/creature-kernel-visual-review.service`.
  It is enabled and active on port 8765 and serves LAN read-only.
- The persistent port 8765 service/gallery still serves the earlier
  `successor-surface-checkpoint`; this temporary candidate has not been
  installed there.

Useful local checks:

```bash
systemctl --user status creature-kernel-visual-review.service
systemctl --user restart creature-kernel-visual-review.service
```

Because LAN mode is read-only, capture Ben's visual feedback in chat or project
docs; do not expect the gallery to create `response.json`.

## PR #103 disposition and next checkpoint

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
authorize the merge.

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

The next named human checkpoint remains the complete authored-form expressivity
gallery across the agreed controls and regions:
richer source-authored dimensions, landmarks, and profiles drive shared
region-appropriate generator operations across all four fixed variants, with
source provenance and reproducible evidence. Representative torso, head/neck,
shoulder/arm, pelvis/leg, and digitigrade foot transitions must read as
controlled continuous skin rather than joined procedural masses. Do not use
per-variant or per-fixture patches or a handcrafted base mesh. This remains a
bounded exploratory expressivity checkpoint, not proof of a finished
morphology family or production surface system.

Before that gallery is published, its immutable evidence must retain either
the exact producer envelope used by the checkpoint or an integrity-bound
authored-dimension, landmark, frame, and descriptor-role lineage projection,
including indexed authored provenance. The existing source hash alone is not a
self-contained lineage record.

The current fixture's exact squared reference length is `1`. Before a future
large-coordinate fixture exceeds JavaScript's exact-integer domain, align or
tighten the producer/publication/surface/browser numeric bounds. That trigger
is not active for this checkpoint.

Routine implementation, tests, reviews, and small internal PRs may proceed
autonomously toward the checkpoint. Stop before the first genuinely appraisable
result or any retained-human/material detour. Rigging, contact, deformation, VR
integration, and permanent backend selection remain outside this immediate
runway.

The required Rust CI workflow still exercises the parked Phase 3 freeze
manifest, whose 47-path candidate closure includes the current core crate
module surface. PR #107 leaves those frozen paths byte-identical and retains
the consumed producer lineage in unfrozen developer tooling. Treat a
future need to edit a frozen core path as a trigger to resolve the CI/freeze
boundary explicitly, not as authority to regenerate or rebind EXP-0002.

## Evidence and limits

Current arm-slice checks known: 415 Rust workspace tests (47 CLI and 368 core),
52 successor tests, 34 publisher tests, and 25 browser/publication parity tests
pass; the unchanged baseline suite's 56 tests were already green. Rust
formatting, Clippy with warnings denied, documentation validation, and
`git diff --check` pass. The final adversarial review, PR, CI, and merge gates
remain pending. The real publication produced four groups and eight assets
with no response artifact. Two fresh hands-on trials are complete. They
exercised exact evidence and asset bindings, HTTP success and failure paths,
modal click and keyboard navigation including wrap and Escape focus return,
and browser console/network behavior. Both found the arm-focused successor
meshes connected and visibly variant-sensitive; neither result constitutes
visual acceptance or completion of the named gallery checkpoint.

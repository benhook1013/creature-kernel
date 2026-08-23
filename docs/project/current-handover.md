# Current operational handover

Snapshot: 2026-08-23 NZST

This is a concise operational handoff for continuing the current runway in the
Codex app. It is not a new authority owner: `docs/project/status.md` remains
the canonical owner of the active runway, and the required reading order in
`AGENTS.md` still applies.

## Where to continue

- Primary checkout: `/home/ben/src/creature-kernel` — `main` and
  `origin/main` are at merged PR #108 commit
  `32e8816664b9e94065f8423da2272d4374567b35`.
- Active worktree: `/home/ben/src/creature-kernel-worktrees/authored-torso-profiles`
  — branch `implementation/authored-torso-profiles`, based on that commit;
  [PR #109](https://github.com/benhook1013/creature-kernel/pull/109) is the
  current internal runway candidate.
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

The current candidate is a direct, internal, reversible torso prerequisite and
makes no form-quality acceptance claim. Producer v7 adds a source-authored
seven-section pelvis/torso axial profile, two identity frames, seven landmarks,
21 asymmetric lateral/anterior/posterior radii with exact indexed provenance,
and four shared variant projections. Baseline guide v6 retains both depth sides
and lineage. Successor v4 / region v8 consumes a continuous asymmetric
rounded-superellipse torso sweep. The publisher cross-binds producer, guide,
and successor lineage and validates real bundles. The comparator adds
Previous/Next controls, arrows, click-to-advance, and zoom.

The candidate also contains Ben-approved neutral public-facing wording cleanup
and accepted MIT OR Apache-2.0 licensing DR-0014. That ancillary work does not
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

The current candidate remains coarse. The prior pointy-underarm and related
point observations are artifact-specific feedback on the displayed v6
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
the exact current producer envelope — v7 in this candidate — or an integrity-
bound authored-dimension, landmark, frame, and descriptor-role lineage
projection, including indexed authored provenance. The existing source hash
alone is not a self-contained lineage record.

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

Current checks known: 405 Rust workspace tests, 44 baseline surface tests, 46
successor tests, 92 visual-review tests, 82 Phase 2 Python tests, and 368 Phase 3
Python tests on native `/tmp` pass. Documentation validation,
`git diff --check`, Python/JavaScript syntax, formatting, default Clippy, and
exact CI-readiness checks pass. A fresh real publication produced 4 groups and
8 assets with no response artifact.
Two fresh hands-on trials are complete. The broad adversarial pass completed
55/55 comparator, keyboard, zoom, asset, scoping, wrap, resize, console, and
network checks across all eight assets. A focused first-use pass exposed focus
loss after click/arrow navigation; the repaired candidate then passed a fresh
independent click/arrow/zoom/close-reopen regression across two groups with no
browser errors. This remains implementation evidence only and does not claim
visual acceptance or completion of the named gallery checkpoint.

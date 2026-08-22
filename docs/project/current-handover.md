# Current operational handover

Snapshot: 2026-08-23 NZST

This is a concise operational handoff for continuing the current runway in the
Codex app. It is not a new authority owner: `docs/project/status.md` remains
the canonical owner of the active runway, and the required reading order in
`AGENTS.md` still applies.

## Where to continue

- Primary checkout: `/home/ben/src/creature-kernel` — clean, synchronized
  `main` at `f69a0a235152e72bd51279634cf3e8618d776e3f` / `origin/main`,
  including merged PR #107.
- Active worktree: `/home/ben/src/creature-kernel-worktrees/authored-shoulder-envelope`
  — branch `implementation/authored-shoulder-envelope` at `a98a00f`, based on
  `f69a0a235152e72bd51279634cf3e8618d776e3f`; [PR #108](https://github.com/benhook1013/creature-kernel/pull/108)
  is the current internal runway candidate.
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

The current PR #108 candidate advances the source/producer to the exact
`creature-kernel.provisional-form-preview.v6` envelope. It retains the exact
canonical v6 producer bytes actually consumed by the generators inside each
new surface review's `review.json`, using deterministic zlib plus Base64 with
the original UTF-8 encoding, byte count, and SHA-256. The v6 hash is
cross-bound to the existing producer hash; the validated input body document
is separately identified by its encoding, byte count, and SHA-256 without
duplicating its bytes. The v6 source-authored controls are bilateral shoulder
frames, peak/axilla landmarks, and depth-radius controls with exact provenance.
The baseline private regional guide is
`creature-kernel.disposable-surface-preview-regional-guide.v5`; it strictly
derives and binds those controls, while the new depth control remains
guide-only for baseline shoulder skin.

The disposable successor is
`creature-kernel.disposable-successor-surface-preview.v3`, region
`successor-torso-shoulder-head-neck-limb-extremity-tail-profile-sweeps-v7`.
It uses bilateral five-section authored shoulder-envelope sweeps, replacing
the prior upper-arm root bridges and distal-deltoid fields. Its only retained
temporary bridge is two thigh-root connectors plus two hip transitions (four
fields). This is an internal, reversible direct prerequisite, not the named
human visual checkpoint; it claims neither visual acceptance nor completion.
Continue through subsequent bounded region slices and small reviewed PRs until
the complete named gallery is ready, unless a retained-human blocker or
direction appears.

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
the exact v6 source envelope or an integrity-bound authored-dimension,
landmark, frame, and descriptor-role lineage projection. The existing source
hash alone is not a self-contained lineage record.

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

Current-candidate local validation passed 398 Rust workspace tests, 39 baseline
surface tests, 42 successor geometry/render/input-bound tests, and 85 complete
visual-review tests. Documentation validation, Rust formatting, Python
compilation, JavaScript syntax, and `git diff --check` also passed. A real
default WSL publication with inherited Windows `TEMP`/`TMP` produced the exact
four ordered variant pairs and eight immutable images on a native review-root
filesystem; the publisher independently verified each successor PLY's bounded
ASCII schema, finite triangle geometry, edge incidence, single connected
component, and agreement with topology metrics.

Two fresh hands-on trials exercised first-use and malformed/stale-control
paths. They found one WSL operability defect: process-global temporary storage
could redirect generator staging to DrvFS. The candidate now allocates staging
beside the selected review root, and the default no-override trial passes. One
fresh adversarial code/contract review found four correctness gaps: independent
PLY topology verification, shoulder-socket/upper-arm-root binding, legacy
browser rejection of newer authored fields, and bounded direct-successor input
reading. All four are fixed with focused regressions. None of this evidence is
visual acceptance or completion of the named gallery checkpoint.

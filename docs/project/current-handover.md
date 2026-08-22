# Current operational handover

Snapshot: 2026-08-22 NZST

This is a concise operational handoff for continuing the current runway in the
Codex app. It is not a new authority owner: `docs/project/status.md` remains
the canonical owner of the active runway, and the required reading order in
`AGENTS.md` still applies.

## Where to continue

- Primary checkout: `/home/ben/src/creature-kernel` — clean, synchronized
  `main` at `cdedc914` / `origin/main`.
- Active worktree: `/home/ben/src/creature-kernel-worktrees/successor-gallery-checkpoint`
  — branch `implementation/successor-gallery-checkpoint`; the validated
  implementation candidate runs through `c4fcd38`, followed by this
  operational handover update.
- Draft PR: [#103](https://github.com/benhook1013/creature-kernel/pull/103)
  — mergeable; all three CI checks passed at `c4fcd38` and must be rechecked
  for the current head; no merge or review approval has been given.

Open the active worktree in the Codex app to inspect or continue the candidate.
Read `AGENTS.md` in the required order, then this handover and the linked
[current status](status.md). Do not infer approval to merge from the CI state.

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

## Human gate

Do not merge PR #103 until Ben appraises the gallery and explicitly authorizes
the merge. The required judgment is the active runway checkpoint: overall,
whether the result is a materially more coherent stylized furry biped, including
head/muzzle/neck, shoulder/torso/pelvis, connected limbs/joints, digitigrade
legs, paws, and tail; less like blended primitives; with the variants remaining
meaningfully different.

Ben's exact feedback on the displayed PR #103 successor artifact was: "its got
pointy bulges under the arms again." This remains an artifact-scoped rejection;
PR #103 is unmerged and no approval is implied. The bounded response is the
shared v6 successor-generator selection of exactly one distal `deltoid-sweep`
span (index `1`) per side, with anterior/posterior supports retained only as
guide metadata. Fixture-specific tuning, guide derivation, sampling, and
smooth-union parameters remain unchanged.

The regenerated v6 gallery is now the served candidate. Its four baseline
PNGs are byte-identical to the rejected gallery and all four successor PNGs
changed. One independent static-capture trial judged the reported lobes
removed; a second still saw a smaller angular root contour. Follow-up isolation
showed that removing the distal deltoid span did not remove that contour, while
removing the temporary upper-arm bridge produced a visibly thinner attachment.
The bounded v6 correction is therefore presented for Ben's reappraisal rather
than treated as internally accepted.

If Ben approves, record the explicit authorization and proceed with the normal
PR merge path. If feedback is qualified or rejects the candidate, keep PR #103
unmerged, record the feedback in chat/docs, and make only bounded successor
work consistent with the active runway before presenting the next visual
candidate.

## Evidence and limits

The v6 local validation passed 38 successor geometry/render tests, 16 focused
publication tests, documentation validation, and `git diff --check`. The live
gallery publication contains exactly eight images, reports the v6 successor
region for all four variants, and returns HTTP 200. A fresh code/contract review
found two publication-validation issues; both were fixed with negative tests.
Current-head CI must still be rechecked after push. The earlier viewer-navigation
browser trial remains applicable because v6 changes the captured assets rather
than the viewer interaction.

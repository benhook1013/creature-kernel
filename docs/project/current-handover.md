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

If Ben approves, record the explicit authorization and proceed with the normal
PR merge path. If feedback is qualified or rejects the candidate, keep PR #103
unmerged, record the feedback in chat/docs, and make only bounded successor
work consistent with the active runway before presenting the next visual
candidate.

## Evidence and limits

T3 browser automation was unavailable. Actual publication and the HTTP/image
trial succeeded. The latest validation included 72 geometry/render tests, 72
visual-review tests after the latest root fix, documentation validation, green
CI, and a final fresh review with no findings. This handover does not claim
modal-click testing that was not performed.

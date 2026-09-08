# Current operational handover

This pointer owns no project state. The [Active runway](status.md#active-runway)
in `status.md` is authoritative for current continuation; this file only helps
with live verification and navigation.

## Resumed runway — 2026-09-08

Ben explicitly resumed the exact paused runway through the Overseer on
2026-09-08. The fail-closed PowerShell/stdin invocation repair has now passed
parser, mocks, and both non-launching stdin sentinels (empty-profile and
nonnumeric-port), with both rejected-input child processes exiting nonzero and no trailing sentinel; quoted-argument
preview and fake handoff match, and no execution-policy mutation occurred.
Main's follow-up changed only cleanup-receipt guidance to require current-PID,
executable, and profile verification; no algorithm changed. Revalidate the
pause snapshot and these status pointers before continuing the lowest
integration lane: PR #127 plus up to two dependent follow-ups, with each layer
below 100 changed files. PR #127 currently has 57 prospective paths; the two
planned follow-ups are approximately 92 and 79 paths. Packaging and review remain primary, and upper-work must not
delay the lower lane. A genuine final-review-ready clean immutable head may then
receive the hosted and committed-diff CLI review cycle together. Current
real-browser coverage is deferred; no browser repair or setup lane remains
active. No local native Chromium or Playwright was available; the setup attempt
installed only npm Playwright 1.63.0 packages at
`/home/ben/.cache/pr127-native-browser-IFXwYI`, with no browser download or
launch and no new infrastructure or launcher project. Windows-side execution is
not permanently prohibited, but any future coverage must be provably hidden and
profile-isolated and create no visible Windows desktop windows, tabs, consoles,
focus changes, or popups. Real Windows launch and nonintrusion remain
unverified. No additional broad waiver is granted. Previous source/CLI gallery
hash-based validation remains retained evidence. PR #127's concrete
control-plane gate remains with Ben; this handover grants no merge
authorization. The pause record below is historical.

## Historical pause snapshot — 2026-09-07

Ben explicitly requested a pause at the next safe boundary. All delegates have
returned; no further task, browser action, implementation, commit, push, or
review is authorized during the pause.

- Integration checkout: `/home/ben/src/creature-kernel-worktrees/pr127-integration`,
  branch `codex/pr127-integration`, HEAD
  `4ae0a5c8176c60791248ad6eb5e52dc657a2dd34`. There are 21 dirty paths
  (18 tracked modifications and 3 untracked files), with nothing staged.
- Upper checkout: `/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor`,
  branch `codex/owned-root-assembly-successor`, same HEAD; 181 dirty paths
  (17 tracked modifications, 164 untracked), nothing staged. Protected
  `docs/project/ai-observations.md` remains present and untouched/unread.
- No commit, push, hosted/CLI review cycle, merge, or pelvis implementation
  began during this integration turn. PR #127 remains at the last verified
  51-file draft head above. The unpublished PR-body draft is
  `/tmp/pr127-integration-body.md`; it still contains pending wording.
- Gallery corrections, historical closeout, CLI import correction, and frozen
  LOC-preserving reflow are complete locally. Validation details are in
  [integration evidence](status.md#layer-1-integration-evidence-2026-09-07).
  The active pelvis Rev2 recipe/review prerequisite is complete in the upper
  checkout; its implementation and geometry execution remain unstarted.
- Browser invocation repair is **partial and must not be used to launch**.
  `dev-tools/visual-review/browser_trial.ps1`, its mocked
  `tests/test_browser_trial.ps1`, and the tool README were written. Parser,
  mocked input rejection/default-plan, documentation, and whitespace checks
  passed, but a separate invalid-input sentinel probe **failed**: script
  `exit 1` did not prevent later stdin statements under `powershell.exe -File -`.
  The README's claimed stdin termination is therefore not established.
  Script SHA-256 is
  `de771290fcdf93d982193d0ac5eb8c38dd61930e53acaca4ce5d800cf371237e`;
  mocked-test SHA-256 is
  `8538796228bb1b6128cdb7acb5711cd1b955ac59b540e99951b7487ca8620d3a`.
- No delegate command remains running. Final cleanup found no task Chrome
  process or listener on ports 9223/9230/9231/9232/9234. Main's browser-owner
  exec session 96240 exited. Trial server PID 2210318 is absent and port 46493
  is closed. Pre-existing listener `0.0.0.0:8765` remains untouched. Any tabs
  handed to ordinary Chrome by the empty-profile launch remain unattributed;
  ordinary Chrome was not touched during cleanup.
- Final pause-pointer edits were not followed by another validation command,
  in accordance with Ben's pause. Earlier reported checks cover their recorded
  revisions only.

**First action after Ben resumes:** inspect the partial invocation catch path
and reproduce the non-launching stdin sentinel failure, then make termination
fail closed (the worker proposed host-level `SetShouldExit(1)`, still unverified).
Run parser/mocked/sentinel checks without launching a browser, correct the
README's claim, and rerun documentation/whitespace validation. Only then finish
the draft integration package, refresh exact PR head/file count, and consider
the pending immutable-head review cycle. Real-browser evidence and whole-PR
human merge authority remain unsatisfied; no browser retry is implicit.

## Last-known context

The following values are expected last-known context for this Layer 1
integration checkout and are explicitly untrusted until verified live:

- Checkout/worktree: `/home/ben/src/creature-kernel-worktrees/pr127-integration`
- Branch: `codex/pr127-integration`
- Pull request: PR #127 is an open draft; Main supplied base
  `db5f11efff124d500d875f7839c53fee9a75f395`, head
  `4ae0a5c8176c60791248ad6eb5e52dc657a2dd34`, and 51 changed files
- Copied stage ledger identity: `docs/project/stacked-integration-ledger.md`,
  SHA-256 `c3c34a7f8f5ee2a5ab45913e46f7edef4380a4fc0bfb7d93cfa120a63442d3ba`,
  8,659 bytes
- Copied historical trigger identity: `experiments/owned-root-assembly-successor/results/correction-round-1-preflight-trigger.json`,
  SHA-256 `e7e272f24653e53164ba82b7bc8651cce51f72406ad157205b894bc957bc9d62`,
  22,161 bytes

The original active development checkout remains
`/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor` on
`codex/owned-root-assembly-successor`; pelvis source work continues there and
was not edited by this integration layer.

## Layer 1 integration destination

This checkout packages and tests the historical owned-root and gallery fixes
under the three-PR stack. The four stage-specific documentation overlays record
historical closeout and navigation only; captured regression checks change no
construction and publish no candidate. No parked experiment is reactivated.
The current continuation is the integrated
coarse-to-anatomical whole-character Active runway. Later lower/body paths are
follow-up stack material and remain prose-only until their files arrive here.

PR #127 and the supplied head remain pending CI, independent review, hosted and
CLI checks, and human control-plane gates. This handover grants no merge
authorization. The current integration checks and consolidated review remain
pending.

Focused integration results and their capture paths are recorded in
[Layer 1 integration evidence](status.md#layer-1-integration-evidence-2026-09-07).
Ben stopped browser launches after the trial method caused visible Chrome
errors and failed tabs. Browser coverage remains incomplete; continue with
non-browser checks and the bounded invocation repair. Do not resume the old
launch scripts or a GUI fallback. No task browser processes/debug listeners
remained at cleanup, and the disposable trial gallery server was stopped.

## Live verification checklist

- [ ] Run `pwd` and confirm the intended checkout or worktree.
- [ ] Run `git branch --show-current` and confirm the expected branch.
- [ ] Inspect `git status` and preserve unrelated dirty work.
- [ ] Run `git worktree list` and confirm the expected worktree topology.
- [ ] If the checkout, worktree, or branch does not match the intended task,
      stop task work and resolve or report the mismatch before reading further
      task material or editing repository files.
- [ ] When relevant, verify the PR head, PR state, and CI for the checked-out
      branch; do not rely on the last-known PR entry above.
- [ ] Inspect or use the visual-review service only when the task needs a
      current visual artifact or review session.

## Navigation

- [Active runway](status.md#active-runway) — sole current continuation source.
- [Conditional workflow index](../developer-workflows/README.md) — use only
  when the applicable workflow trigger is present.

This pointer does not own authoritative history, evidence, decisions, or project state.

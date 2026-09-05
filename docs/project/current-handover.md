# Current operational handover

This pointer owns no project state. The [Active runway](status.md#active-runway)
in `status.md` is authoritative for current continuation; this file only helps
with live verification and navigation.

## Last-known context

The following values are expected last-known context and are explicitly
untrusted until verified live:

- Checkout: `/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor`
- Worktree: `/home/ben/src/creature-kernel-worktrees/owned-root-assembly-successor`
- Branch: `codex/owned-root-assembly-successor`
- Pull request: PR #127 is an open draft for `codex/owned-root-assembly-successor`

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

# Current operational handover

This pointer owns no project state. The [Active runway](status.md#active-runway)
in `status.md` is authoritative for current continuation; this file only helps
with live verification and navigation.

## Last-known context

The following values are expected last-known context and are explicitly
untrusted until verified live:

- Primary checkout: `/home/ben/src/creature-kernel`
- Worktree: `/home/ben/src/creature-kernel-worktrees/hybrid-surface-interfaces`
- Branch: `codex/hybrid-surface-interfaces`
- Predecessor PR: #122, merged at commit
  `d976a09506cf4bb1d89fba85cea1f57ddec5d4e4` on 2026-09-02 NZST; verify live.
- Current branch PR: none observed; verify live.

See the [Active runway](status.md#active-runway) in `status.md` for the current
Stage 1 direction, retained candidate evidence, immediate slice, review
disposition, checkpoint, and merge condition. This pointer does not duplicate
that project state.

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

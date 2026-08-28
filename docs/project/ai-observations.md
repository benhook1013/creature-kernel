# AI observations

Status: Operational inbox; 2 open observations

Record only unexpected, evidenced operational friction that is recurring or
likely to save future retries or work rounds. The main thread is the default
writer; a delegated thread writes only with exclusive inbox ownership and
otherwise returns a concise observation candidate. Resolve or promote entries
during a purposeful tooling/instruction improvement round, then remove them;
Git preserves the history.

Copyable entry:

- `YYYY-MM-DD HH:MM TZ`: short title
  - Observation: what happened and where
  - Expected pattern: what should happen instead

- `2026-08-28 19:40 NZST`: Batched `unlink` rejected multiple paths
  - Observation: A verified generated-cache cleanup used `find -exec unlink -- {} +`; GNU `unlink` rejected the second path with `extra operand`, and no file was removed on that attempt.
  - Expected pattern: Pass one verified pathname per `unlink` invocation, or use a separately validated safe multi-file cleanup route.

- `2026-08-28 20:13 NZST`: Direct experiment test bypassed the pinned Python launcher
  - Observation: A focused Xvfb test invoked bare `python3` and failed before reaching Godot because system Python lacks Pillow, despite the experiment README requiring its repository-owned launcher for every experiment Python command.
  - Expected pattern: Invoke current-form and dependent Godot experiment Python through `experiments/current-form-surface-preview/surface_preview_launcher.sh`; do not substitute bare system Python.

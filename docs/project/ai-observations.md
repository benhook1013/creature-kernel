# AI observations

Status: Operational inbox; 8 open observations

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

- `2026-08-28 22:13 NZST`: Direct dynamic import recreated repository bytecode cache
  - Observation: A read-only review dynamically imported `disposable_avatar_carrier.py` outside the canonical wrapper, and an isolated `python -I` projection child ignored the launcher's `PYTHONDONTWRITEBYTECODE`; both routes created repository `__pycache__` files that can invalidate concurrent cache-cleanliness tests.
  - Expected pattern: Set bytecode suppression before `exec_module`, run experiment tests through their canonical wrapper from a cache-clean tree, and pass `-B` explicitly to isolated Python children because `-I` ignores `PYTHON*` environment variables.

- `2026-08-29 00:38 NZST`: Markdown backticks broke an orchestration template string
  - Observation: A subagent launch failed before execution because a Markdown code span inside a JavaScript template-string payload terminated the string and produced `SyntaxError: Unexpected identifier 'validate'`.
  - Expected pattern: Build free-form orchestration prompts from quoted line arrays joined with newlines, or otherwise escape embedded backticks before evaluation.

- `2026-08-29 00:40 NZST`: Invalid `gh api --arg` aggregation repeated before changing route
  - Observation: A read-only CI audit passed jq's `--arg` option directly to `gh api`, received `unknown flag: --arg` 20 times in one loop, and only then switched to successful per-run API queries.
  - Expected pattern: Stop after the first identical command-shape failure, separate `gh api` retrieval from jq argument handling, and validate a single query before placing it in an aggregation loop.

- `2026-08-29 00:47 NZST`: Broad `rm -rf` cleanup rejected by the command safety layer
  - Observation: Main-thread and delegated cleanup attempts both used `rm -rf` for a verified experiment cache or temporary path and were rejected before execution by the command safety layer.
  - Expected pattern: For an exact verified cache directory, delete bounded files with `find <absolute-cache-path> -maxdepth 1 -type f -delete`, then remove the empty directory with `rmdir`; do not retry the rejected broad command form.

- `2026-08-29 00:50 NZST`: CI tail step lost its full-history checkout requirement
  - Observation: A timing audit split the slow Phase 3 test step into a checkout-only job with the default shallow history even though the suite reads fixed historical commits; the isolated command produced 17 failures and 26 errors, and an arbitrary 55-second timeout made the initial report additionally ambiguous.
  - Expected pattern: Before parallelizing sequential CI steps, trace checkout depth, filesystem, build, and environment dependencies and validate one representative dependent test; do not cap a known multi-minute suite below its normal duration and then summarize partial output as validation.

- `2026-08-29 01:28 NZST`: Read-only mapping raced broad validation against active edits
  - Observation: An evidence mapper launched the 102-test and full Xvfb experiment suites while the main thread was editing the same worktree, producing stale parse and runtime failures while consuming the renderer needed for consolidated validation.
  - Expected pattern: Keep read-only mapping to static inspection unless broad validation is explicitly assigned; do not launch long tests against a mutable shared worktree, and leave integrated validation to the main thread.

# AI observations

Status: Operational inbox; 20 open observations

This inbox records only unexpected, evidenced operational friction that is
recurring, reusable, or likely to save future retries or work rounds. Every
worker reports qualifying friction with its category, exact error, attempt
count, workaround, and known-versus-inferred cause. A subagent returns an
`AI observation candidate` unless it has explicitly exclusive inbox ownership;
the main thread searches narrowly, deduplicates against existing entries, and
is the default writer. The main thread records a durable recurring pattern
before the work round closes and reports an existing match as a recurrence
rather than duplicating it.

Ordinary work does not use this inbox as general guidance; qualifying
operational friction is checked narrowly here for duplicates and recording.
During an intentional tooling or instruction-maintenance round, resolve,
promote, or remove entries deliberately. Close repeated issues with a concrete
bounded repository wrapper, preflight, active-instruction, or other tool fix
when available; restating an observation is not closure. Git preserves the
history of removed entries.

Copyable entry scaffold:

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

- `2026-08-29 02:14 NZST`: Native launcher repeatedly reported inherited Windows temp paths
  - Observation: Two projection-tool runs through the repository launcher warned that inherited Windows `TEMP` and `TMP` paths were ignored before successfully selecting native Linux temporary storage.
  - Expected pattern: Treat this known normalization as non-fatal, and prefer a launcher-side cleanup if the repeated warning continues to consume review attention; do not switch to bare system Python or Windows paths.

- `2026-08-29 15:06 NZST`: Profile gallery fixture violated no-replace and lineage boundaries
  - Observation: A Godot deformation fixture run first pre-created the generator's output directory, which the no-replace publisher rejected; an earlier broad attempt also reused one successor bundle across profile-specific sources and failed lineage validation.
  - Expected pattern: Give generators an absent output path whose parent exists, and generate each profile's form, structure, successor, and bridge bundle from that profile's own source before composing the gallery.

- `2026-08-29 15:06 NZST`: Godot experiment test wrapper accepts file selectors only
  - Observation: A focused validation attempt tried to select one unittest method through `experiments/godot-provisional-host-feasibility/test.sh`, but the wrapper accepts only one test filename or discovery pattern.
  - Expected pattern: Use the wrapper's file-level selector and run the complete matched file; do not pass a unittest class or method name to this entrypoint.

- `2026-08-29 16:25 NZST`: Security preflight used an unsuitable Python runtime
  - Observation: A delegated security preflight first used system Python, which lacked `tomllib` and `tomli`; the bundled fallback then exposed Windows-path incompatibility before the review changed route.
  - Expected pattern: Use the repository's documented native WSL validation or security entrypoint when available, and validate one interpreter invocation before launching the full check.

- `2026-08-29 17:22 NZST`: Godot API dumps polluted the selected project path
  - Observation: A read-only API investigation found that `--dump-extension-api` wrote `extension_api.json` and `.godot/` into the selected project, while the headless documentation dump produced output and then aborted with a null-singleton error; `/dev/stdin` was also rejected as a script resource.
  - Expected pattern: Run Godot API introspection only in a fresh native-Linux temporary project, expect a temporary script file rather than standard input, and treat a documentation-dump artifact as incomplete when the command exits nonzero.

- `2026-08-29 17:36 NZST`: CodeRabbit CLI review lost its subscription before a rate-limited retry
  - Observation: A committed-diff CLI review reached the reviewing phase, then failed with `WebSocket subscription completed unexpectedly`; one immediate retry returned the three-review rate limit without yielding findings. It is unknown whether the dropped review consumed the final allowance.
  - Expected pattern: After a late CodeRabbit CLI subscription failure, inspect saved findings and usage before retrying; do not assume a recoverable transport label means the review allowance was preserved.

- `2026-08-29 20:52 NZST`: Broad multi-file review reads repeatedly exceeded useful output limits
  - Observation: A delegated documentation review batched several large files into single inspection commands, repeatedly received truncated output, and had to repeat narrower reads before it could form evidence.
  - Expected pattern: Bound review reads by one relevant section or a small related file set, then expand only around concrete matches; do not begin with broad concatenated document dumps.

- `2026-08-29 21:38 NZST`: Lost Xvfb test session left a busy process alive
  - Observation: A focused Godot test lost its orchestration session while its `xvfb-run` and Python processes continued at full CPU for more than eight minutes, so a replacement run would have duplicated the expensive stage.
  - Expected pattern: When a long-running session disappears, inspect live processes and the exact output target before retrying; terminate only the verified orphan process, then publish any retry to a fresh temporary path.

- `2026-08-29 23:10 NZST`: Bounded subprocess cleanup ignored descendants
  - Observation: A projection-tool review found that timeout and final cleanup killed only the direct child, allowing a descendant that inherited pipes or resources to outlive the bounded command.
  - Expected pattern: On POSIX, launch bounded subprocesses in a dedicated session/process group, terminate that exact group on every exit path, and regression-test a descendant rather than only the direct child.

- `2026-08-30 00:04 NZST`: Diagnostic output pipeline masked a failing test status
  - Observation: A focused unittest command piped output through `tail` without enabling pipeline failure propagation; the test reported one failure while the shell command incorrectly returned exit code zero.
  - Expected pattern: Run validation commands directly when their status is authoritative, or explicitly enable `pipefail` before filtering output and verify the test summary as well as the shell exit code.

- `2026-08-30 00:25 NZST`: Mocked and skip-gated checks concealed a package consumer mismatch
  - Observation: Package unit tests mocked validation and process launch while the real Godot integration class was conditionally skipped, so the suite stayed green even though the producer's five-field source record was rejected by the consumer's three-field validator.
  - Expected pattern: For each new transport shape, keep a real producer-to-consumer scenario whose unavailable prerequisites are reported as missing coverage, and do not treat mocked transport checks as evidence of consumption compatibility.

- `2026-08-30 14:43 NZST`: One deterministic mesh test consumed multiple foreground minutes
  - Observation: A focused successor test that performs eight 56-cubed mesh builds remained CPU-bound after 2m31s and was interrupted during its second build; the complete successor file later took 9m25s.
  - Expected pattern: Reserve repeated full-resolution deterministic mesh construction for consolidated candidate validation, and use focused semantic or numerical regressions during active implementation unless the mesh result itself is under test.

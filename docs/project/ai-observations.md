# AI observations

Status: Operational inbox; 37 open observations

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

- `2026-09-02 14:46 NZST`: Visual readiness was inferred from diagnostics and topology instead of final-skin coverage
  - Observation: The current regional successor explicitly kept shoulder and axilla controls diagnostic-only and tested that they could not affect the final skin, while narrow topology and regression reviews still led the main thread to present the exact-five gallery as internally ready. The named Stage-1 visual floor required specialized shoulder, hip, torso, and neck construction; reviewers completed their narrowed contracts, but main-thread integration did not reconcile every promised visible feature against the actual final field.
  - Expected pattern: Before presenting a visual checkpoint, map every named visual-floor feature to an actual final-skin consumer or explicitly mark it absent. Diagnostics, metadata, topology, overlap certificates, and narrowly scoped regression passes cannot satisfy visible-feature coverage; reconcile a focused regression pass with a fresh open-ended visual critique before claiming readiness.

- `2026-09-02 14:46 NZST`: Merged PR worktrees accumulated without closeout cleanup
  - Observation: Thirty-two registered worktrees accumulated even though only one implementation lane remained active; most were clean historical PR worktrees whose pull requests had already merged. The main thread had no closeout step that retired the worktree and local branch after verifying the merge.
  - Expected pattern: At merged-PR closeout, verify the exact merge and clean worktree, remove the merged worktree and local branch, and inventory existing worktrees before creating another. The normal steady state is primary `main` plus one active lane; preserve and escalate only genuinely dirty, unmerged, or cleanup-blocked exceptions without routine user-facing housekeeping reports.

- `2026-09-02 05:25 NZST`: Subagents defaulted to the primary checkout instead of the active worktree
  - Observation: A bounded publisher worker was given the absolute `hybrid-surface-interfaces` worktree path but edited four same-named untracked files under the primary `/home/ben/src/creature-kernel` checkout; a follow-up transfer worker safely stopped when its root assertion exposed the same default checkout. The main thread verified both trees and retained the accidental files only as a temporary patch source. The exact harness reason the worker ignored the supplied path is unknown.
  - Expected pattern: Every bounded write prompt for a named worktree must begin with an explicit `cd` to its absolute path and require both `pwd` and `git rev-parse --show-toplevel` to equal that path before any edit or test. Stop on mismatch; do not rely on the subagent's default working directory or same-named files in another checkout.

- `2026-09-01 16:44 NZST`: One-off managed-launcher render lost implementation binding
  - Observation: A one-off managed-launcher render met runtime/tool rules but placed generated evidence in `/tmp` and omitted implementation identity/regeneration binding; it had to be copied to durable cache and downgraded to observational evidence.
  - Expected pattern: Evidence-bearing visual captures must use the implementation-hashing immutable publisher, or record the implementation digest and durable target before rendering, rather than an ad hoc one-off.

- `2026-09-01 14:30 NZST`: Bounded evidence subagent spawned an unintended nested worker
  - Observation: One Luna xhigh evidence-only option-generation subagent reported that it attempted an unintended nested delegation before replacing that route with a direct pass. The Codex desktop UI exposed an additional similarly titled Recent item and several duplicate path-only spinner rows, which made the internal worker look like an extra user-owned task. No Git worktree, branch, repository edit, or main task was created; the exact UI persistence behavior remains an app-level inference.
  - Expected pattern: Bounded subagents should complete their assigned read/reason task directly and must not spawn descendants unless the main-thread prompt explicitly authorizes nested delegation. The main thread should close completed agents promptly; treat extra Recent/path rows as internal-worker UI until repository and task state prove otherwise.

- `2026-08-31 11:00 NZST`: Interrupted subagents remained running after their owned commands ended
  - Observation: Two Luna xhigh workers remained authoritatively `running` after their owned test or diagnostic processes had ended and after explicit finish/report messages. The first had been interrupted to stop an out-of-scope broad suite; the second was interrupted after a bounded evidence request produced no return. Repeated bounded waits yielded no completion, so the main thread verified that no owned process remained, preserved the first worker's patch, and closed each worker. The exact model-versus-harness cause is unknown.
  - Expected pattern: After interrupting a worker, verify its owned process state and allow one bounded finish/report turn; if the authoritative status still remains `running` without an owned process or response, preserve any scoped work, close the lane once, and continue validation without an unbounded wait loop.

- `2026-08-31 09:27 NZST`: Parallel Cargo validation contended on the shared target lock
  - Observation: A bounded Rust finding worker ran Cargo validation while another repository task shared the default target directory and waited on Cargo's build-directory lock. The checks completed, but parallel orchestration did not provide parallel build progress.
  - Expected pattern: Serialize Cargo validation that shares the repository target directory, or assign an explicit isolated `CARGO_TARGET_DIR` when concurrent builds materially shorten the round and the additional disk cost is justified.

- `2026-08-31 07:56 NZST`: Independent evidence reviews duplicated an unassigned broad suite on a changing worktree
  - Observation: Two fresh evidence-only hand/paw reviewers independently launched the same full `test_successor_surface_preview.py` suite even though their assigned deliverable was static/adversarial review and consolidated broad validation remained main-thread work. Process inspection exposed both CPU-heavy runs before the main thread redirected each reviewer to stop only its own suite. One reviewer also reported a non-reproducible stale-import `NameError` while implementation edits changed the shared worktree beneath its run, so that partial evidence was discarded. A later stable post-fix reviewer stayed within its allowed focused selector, but that selector still exceeded the intended cheap-check boundary and was stopped without a result after the already-completed main-thread focused pass supplied the evidence. A structural-profile finding worker later started a broader suite beyond its completed focused and module checks; the main thread interrupted it and retained only the completed scoped evidence. A later geometry implementation worker again launched the complete successor module despite an explicit focused-tests-only boundary; process inspection caught the CPU-heavy run after 3m49s, the main thread stopped only that worker's process, and exact repeated `-k` selectors supplied the retained evidence.
  - Expected pattern: Evidence-only review prompts should explicitly prohibit broad suites unless that reviewer owns a named validation lane; reviewers may run narrowly targeted checks only against a stable snapshot, while the main thread assigns each expensive consolidated suite once after overlapping writes finish.

- `2026-08-31 06:35 NZST`: Launcher-selected environment does not imply repository module discovery
  - Observation: A launcher-backed inline/stdin probe imported repository modules and failed before execution with `ModuleNotFoundError` because `surface_preview_launcher.sh` selects the pinned interpreter/environment but does not automatically add experiment or visual-review directories to `sys.path`.
  - Expected pattern: Use unittest discovery/file entrypoints for repository tests, or set a deliberately resolved `PYTHONPATH`/import path for a necessary inline probe; do not assume launcher selection implies repository module discovery.

- `2026-08-31 04:22 NZST`: Focused test selectors were guessed instead of resolved
  - Observation: Ten focused validation attempts in one review round used guessed file, method, or compound `-k` selectors; seven wrapper calls were rejected with `matched no test files`, `method selector ... matched no tests`, or because the current-form `test.sh` could not discover `dev-tools/visual-review/tests`, one raw-launcher call reported `Ran 0 tests`, one guessed compound-selector call ran zero tests, and one direct unittest call raised `AttributeError` for a nonexistent method before exact selectors were resolved. The implementation worker then correctly switched to direct `surface_preview_launcher.sh` discovery. Another independent reviewer repeated the visual-review wrapper/discovery-scope mistake before switching routes. Three later publisher workers added four failed routing attempts—one incorrect launcher path, one mistyped unittest class selector, and two wrapper/discovery mismatches—before using exact pinned-launcher discovery. Two later hosted-fix workers added three more failed routes: one wrapper/discovery-scope rejection for the successor-anatomy gallery, one `test.sh` rejection of an out-of-tree publisher test, and one compound unittest selector that ran zero tests before exact launcher discovery was used. A final local reviewer then repeated one module-qualified discovery failure before switching to the resolved launcher route.
  - Expected pattern: Before invoking a focused wrapper test, resolve the exact file and `def test_...` name with a narrow `rg`, then run one validated selector shape; use the documented launcher directly when the target lives outside the wrapper's discovery tree.

- `2026-08-31 00:43 NZST`: Pointwise smooth-field audit misclassified an explicit transition volume
  - Observation: A shoulder audit inspected raw torso and arm values plus the final smooth union only at the named axilla boundary and classified continuity as smoothing-dependent. An independent decomposed check found that the shoulder sweep itself is the explicit transition volume, overlaps torso and arm at its endpoints, and changes sign immediately outside the boundary; no finite raw gap was reproduced.
  - Expected pattern: Before classifying composed-field continuity from a named boundary sample, inspect every raw operand, identify explicit transition or bridge components, and probe both sides of the boundary. Treat the final smooth-union value alone as insufficient evidence of a missing overlap or bridge.

- `2026-08-31 00:39 NZST`: Promoting a shared frozen fixture invalidated independent historical consumers
  - Observation: The five-profile anatomy work revised the shared `structural_profile_candidates.json` and its base source in place, while the completed four-profile structural gallery and publisher independently pinned the old profile IDs, candidate/source hashes, artifact inventory, and regeneration semantics. Their focused suites then failed before their intended assertions. One compatibility audit traced the readers after the collision; no pre-change consumer audit had separated the active and historical lineages.
  - Expected pattern: Before replacing or promoting a frozen fixture or its source path, enumerate every reader plus independently pinned IDs, hashes, inventories, generator defaults, and publication contracts. Preserve completed historical consumers with an explicit immutable fixture/compatibility route instead of silently reusing the active default.

- `2026-08-31 00:07 NZST`: Direct system-Python publication suites hit `renameat2` `EINVAL`
  - Observation: One worker ran `test_provisional_form_publication.py` and `test_surface_preview_publication.py` directly with system `python3`; seven session-install cases then failed in `publish.py:_rename_noreplace` with `OSError: [Errno 22] Invalid argument`. The same complete suites had passed in the main thread through `experiments/current-form-surface-preview/surface_preview_launcher.sh` (28/28 and 42/42 with one expected skip). Each direct full-suite route was attempted once; focused non-install tests passed, and the exact host-level cause beyond the route/environment difference remains inferred. A later publisher cleanup worker repeated the direct route and reproduced the same `renameat2` `EINVAL` pattern before switching to pinned-launcher discovery.
  - Expected pattern: Run these integrated visual-review publication suites through `surface_preview_launcher.sh`; do not substitute direct system Python after a launcher-backed pass or treat direct-route `renameat2` failures as product regressions without an independent syscall reproduction.

- `2026-08-30 23:26 NZST`: Production-resolution successor builds provide no progress signal
  - Observation: Two independent hands-on trials found that 56-sample successor mesh extraction and five-profile gallery publication can produce no output for roughly 24 seconds to several minutes per stage, making healthy CPU-bound work indistinguishable from a stalled process without an external process inspection. Replaying an existing gallery ID also rebuilt all five meshes for several minutes before the final no-replace check rejected it; the installed inventory and hashes remained unchanged. The same long-running no-progress behavior recurred during this review, with one additional occurrence during the current opt-in integration run.
  - Expected pattern: Long-running successor generation and gallery publication should emit bounded stage/profile/variant progress to stderr without changing deterministic artifacts or machine-readable stdout. Publishers should reject an already-existing destination before expensive generation while retaining the atomic no-replace check at installation for race safety.

- `2026-08-30 21:10 NZST`: Parallel subagent spawn batch partially succeeded before rejection
  - Observation: A two-spawn `Promise.all` call reported only `agent thread limit reached`, but its first spawn had already succeeded without its returned ID being surfaced. Recovering a completed slot and retrying the batch's work created a second worker with the same write scope; completion notifications later exposed the duplicate concurrent documentation edit.
  - Expected pattern: When available slots are uncertain, launch write-capable subagents sequentially and retain each returned ID before starting the next; after any batched spawn rejection, treat earlier calls as potentially successful and reconcile notifications or authoritative live status before retrying overlapping work.

- `2026-08-30 18:18 NZST`: Dynamically composed visual-review IDs failed safe-slug admission
  - Observation: Two independent anatomy-gallery hands-on trials each spent a failed first publication attempt on an invalid explicit review ID: one copied a dot-bearing `mktemp` suffix, while the other used a 68-character attack label beyond the 64-character bound. Both returned status 2 with the generic safe-slug error and required a corrected second attempt; neither failure installed a review directory.
  - Expected pattern: Choose a separate 1–64 character lowercase safe slug using only letters, digits, `_`, or `-` before invoking a visual-review publisher; do not derive the review ID verbatim from a `mktemp` path or an unbounded scenario description.

- `2026-08-28 19:40 NZST`: Batched `unlink` rejected multiple paths
  - Observation: A verified generated-cache cleanup used `find -exec unlink -- {} +`; GNU `unlink` rejected the second path with `extra operand`, and no file was removed on that attempt.
  - Expected pattern: Pass one verified pathname per `unlink` invocation, or use a separately validated safe multi-file cleanup route.

- `2026-08-28 20:13 NZST`: Direct experiment test bypassed the pinned Python launcher
  - Observation: A focused Xvfb test invoked bare `python3` and failed before reaching Godot because system Python lacks Pillow, despite the experiment README requiring its repository-owned launcher for every experiment Python command. A later review repeated the bypass once for a visual-review unittest and failed at import because system Python lacked NumPy. A final historical-integrity reviewer repeated the direct-system-Python route once and again failed because Pillow was unavailable before switching to the pinned launcher.
  - Expected pattern: Invoke current-form and dependent Godot experiment Python through `experiments/current-form-surface-preview/surface_preview_launcher.sh`; do not substitute bare system Python.

- `2026-08-28 22:13 NZST`: Direct dynamic import recreated repository bytecode cache
  - Observation: A read-only review dynamically imported `disposable_avatar_carrier.py` outside the canonical wrapper, and an isolated `python -I` projection child ignored the launcher's `PYTHONDONTWRITEBYTECODE`; both routes created repository `__pycache__` files that can invalidate concurrent cache-cleanliness tests.
  - Expected pattern: Set bytecode suppression before `exec_module`, run experiment tests through their canonical wrapper from a cache-clean tree, and pass `-B` explicitly to isolated Python children because `-I` ignores `PYTHON*` environment variables.

- `2026-08-29 00:38 NZST`: Unescaped text broke orchestration JavaScript strings
  - Observation: A subagent launch failed before execution because a Markdown code span inside a JavaScript template string terminated the string and produced `SyntaxError: Unexpected identifier 'validate'`. A later review command repeated the payload-construction failure once with an unescaped nested double quote and produced `SyntaxError: Invalid or unexpected token` before shell execution.
  - Expected pattern: Build free-form prompts and commands from safely quoted values or line arrays instead of embedding unchecked Markdown or shell text directly in JavaScript string delimiters.

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

- `2026-08-29 15:06 NZST`: Profile gallery fixture violated no-replace and lineage boundaries
  - Observation: A Godot deformation fixture run first pre-created the generator's output directory, which the no-replace publisher rejected; an earlier broad attempt also reused one successor bundle across profile-specific sources and failed lineage validation.
  - Expected pattern: Give generators an absent output path whose parent exists, and generate each profile's form, structure, successor, and bridge bundle from that profile's own source before composing the gallery.

- `2026-08-29 15:06 NZST`: Godot experiment test wrapper accepts file selectors only
  - Observation: A focused validation attempt tried to select one unittest method through `experiments/godot-provisional-host-feasibility/test.sh`, but the wrapper accepts only one test filename or discovery pattern.
  - Expected pattern: Use the wrapper's file-level selector and run the complete matched file; do not pass a unittest class or method name to this entrypoint.

- `2026-08-29 16:25 NZST`: Security preflight used an unsuitable Python runtime
  - Observation: A delegated security preflight first used system Python, which lacked `tomllib` and `tomli`; the bundled fallback then exposed Windows-path incompatibility before the review changed route. Two later reviewers again used Python 3.10 lacking both `tomllib` and `tomli`, so those preflights were unavailable.
  - Expected pattern: Use the repository's documented native WSL validation or security entrypoint when available, and validate one interpreter invocation before launching the full check.

- `2026-08-29 17:22 NZST`: Godot API dumps polluted the selected project path
  - Observation: A read-only API investigation found that `--dump-extension-api` wrote `extension_api.json` and `.godot/` into the selected project, while the headless documentation dump produced output and then aborted with a null-singleton error; `/dev/stdin` was also rejected as a script resource.
  - Expected pattern: Run Godot API introspection only in a fresh native-Linux temporary project, expect a temporary script file rather than standard input, and treat a documentation-dump artifact as incomplete when the command exits nonzero.

- `2026-08-29 17:36 NZST`: CodeRabbit CLI review lost its subscription before a rate-limited retry
  - Observation: A committed-diff CLI review reached the reviewing phase, then failed with `WebSocket subscription completed unexpectedly`; one immediate retry returned the three-review rate limit without yielding findings. It is unknown whether the dropped review consumed the final allowance.
  - Expected pattern: After a late CodeRabbit CLI subscription failure, inspect saved findings and usage before retrying; do not assume a recoverable transport label means the review allowance was preserved.

- `2026-08-29 20:52 NZST`: Broad multi-file review reads repeatedly exceeded useful output limits
  - Observation: A delegated documentation review batched several large files into single inspection commands, repeatedly received truncated output, and had to repeat narrower reads before it could form evidence. A later committed-diff finding triage worker repeated one broad multi-file read that exceeded the useful output limit before switching to narrow finding-specific sections.
  - Expected pattern: Bound review reads by one relevant section or a small related file set, then expand only around concrete matches; do not begin with broad concatenated document dumps.

- `2026-08-29 21:38 NZST`: Lost Xvfb test session left a busy process alive
  - Observation: A focused Godot test lost its orchestration session while its `xvfb-run` and Python processes continued at full CPU for more than eight minutes, so a replacement run would have duplicated the expensive stage.
  - Expected pattern: When a long-running session disappears, inspect live processes and the exact output target before retrying; terminate only the verified orphan process, then publish any retry to a fresh temporary path.

- `2026-08-29 23:10 NZST`: Bounded subprocess cleanup ignored descendants
  - Observation: A projection-tool review found that timeout and final cleanup killed only the direct child, allowing a descendant that inherited pipes or resources to outlive the bounded command. A later hosted review found the same lifecycle gap on successful leader exit in both the projection and surface publisher: each could reap the leader before terminating a surviving private-group descendant, weakening snapshot integrity and releasing the PGID anchor before the final signal. The first safe success-path correction then imposed the full 0.5-second grace on every successful publisher child and, in one local run, increased the 61-test suite from roughly 54 seconds to 331.289 seconds; in a separate local run, immediate success-path escalation restored it to 63 tests in 51.994 seconds while timeout/error cleanup retained the grace period.
  - Expected pattern: On POSIX, launch bounded subprocesses in a dedicated session/process group, observe leader status without reaping, terminate that exact group on every exit path, and reap only after the final signal. Regression-test a descendant rather than only the direct child; use immediate escalation for leftover descendants after successful leader exit and retain grace only for timeout/error cleanup.

- `2026-08-30 00:04 NZST`: Diagnostic output pipeline masked a failing test status
  - Observation: A focused unittest command piped output through `tail` without enabling pipeline failure propagation; the test reported one failure while the shell command incorrectly returned exit code zero.
  - Expected pattern: Run validation commands directly when their status is authoritative, or explicitly enable `pipefail` before filtering output and verify the test summary as well as the shell exit code.

- `2026-08-30 00:25 NZST`: Mocked and skip-gated checks concealed a package consumer mismatch
  - Observation: Package unit tests mocked validation and process launch while the real Godot integration class was conditionally skipped, so the suite stayed green even though the producer's five-field source record was rejected by the consumer's three-field validator.
  - Expected pattern: For each new transport shape, keep a real producer-to-consumer scenario whose unavailable prerequisites are reported as missing coverage, and do not treat mocked transport checks as evidence of consumption compatibility.

- `2026-08-31 12:26 NZST`: WSL tempfile selected a DrvFS path for POSIX FIFO tests
  - Observation: Under WSL, Python `tempfile` resolved to a Windows-mounted DrvFS path where `os.mkfifo` exists but failed with `ENOTSUP`, so POSIX-only tests need to distinguish API/platform support from filesystem capability.
  - Expected pattern: For POSIX-only tests, check both `os.mkfifo`/platform support and filesystem capability, or use a verified native-Linux temp root rather than assuming Python's tempfile path supports FIFOs.

- `2026-09-01 16:49 NZST`: Neutral-alternative tests reused production-derived expectations
  - Observation: Two independent final reviewers found several neutral-alternative tests reconstructing expected lower-body composition, bounds, or metadata with the same production helpers or transformations, so tests passed while semantic attribution, expanded bounds, and malformed `AddressKey` serialization remained wrong.
  - Expected pattern: For semantic ownership, bounds, or compatibility claims, use independent analytical probes, literal canonical fixtures, or frozen behavior signatures rather than production-helper-derived expectations.

- `2026-09-02 01:34 NZST`: Subagent test shell omitted an available Cargo toolchain
  - Observation: One renderer worker reported Cargo unavailable and changed its focused test setup to reuse an existing debug CLI binary before falling back to `cargo run`; the main WSL shell immediately found Cargo at `/home/ben/.cargo/bin/cargo`. The worker made one successful fallback attempt, while the exact subagent PATH difference remains unknown.
  - Expected pattern: Treat a subagent-only missing `cargo` result as an environment/PATH discrepancy until the main thread verifies it. Reuse an existing binary only when its freshness and the unchanged producer scope are explicit; otherwise run the documented build route rather than silently accepting stale executable evidence.

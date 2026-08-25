# AI observations

Status: Operational inbox

This is a low-authority, short-lived inbox for genuinely reusable operational
lessons from AI work: recurring tool misuse, unavailable or broken tool routes,
misleading harness or IDE state, expensive retry patterns, and similar friction
that can save future tokens or rounds. It is not product, specification,
architecture, decision-record, status, or experiment authority, and must not
contradict those sources.

The lifecycle is: observe recurring friction with evidence; identify a missing
or broken tool or instruction; improve the tooling or promote a stable rule into
the authoritative workflow; then remove the resolved observation during
deliberate cleanup. This inbox should not become a collection of warnings that
agents merely memorize.

During ordinary work, any AI thread may append only genuinely reusable
operational lessons, subject to the repository's normal write-scope rules.
Nobody consumes this inbox as task guidance or silently rewrites or deletes
existing entries. The inbox is consumed only during a purposeful,
human-requested AI tooling or instruction improvement round with Ben: assess
observations, improve tooling or instructions, and then deliberately remove or
retain entries as evidence warrants. Resolved, obsolete, disproved, or promoted
entries may be removed in that round; their history remains in Git. No
automation or repository-health workflow is required for this file.

Entry format:

- `YYYY-MM-DD`: short title
  - Context: where it appeared
  - Observation: what was surprising, misleading, or wasteful
  - Expected pattern: what should happen instead

- `2026-08-12`: Misleading subagent UI state
  - Context: delegated work where GUI duration or token counters appear stale or implausible.
  - Observation: display counters do not prove that an agent is still working and can prompt an unnecessary interruption, duplicate launch, or kill.
  - Expected pattern: query authoritative live agent status first; if concern remains, message the existing worker for a bounded status explanation before interrupting, killing, or spawning a duplicate. Record enough context to distinguish live status from display state.

- `2026-08-12`: Untracked files bypass ordinary diff whitespace checks
  - Context: a delegated review recorder created new Markdown files and reported a focused `git diff --check` pass; the staged commit gate later found extra blank lines at EOF in every new file.
  - Observation: ordinary `git diff --check` does not inspect untracked files, so a clean result can be misleading when a task creates files.
  - Expected pattern: before reporting a focused whitespace pass, stage intended new files for `git diff --cached --check` or run an explicit equivalent check over every new file; the orchestrator still repeats the staged check before commit.

- `2026-08-22`: Surface-preview Python dependency environment is repeatedly missed
  - Context: main-thread and delegated WSL runs of the current-form surface preview, tests, and one-off visual trials that import NumPy, scikit-image, or Pillow.
  - Observation: agents have repeatedly invoked bare `python3`, received an avoidable `ModuleNotFoundError`, and retried with `/tmp/ck-current-form-surface-venv/bin/python`. The README already documents activating that temporary environment, but the command surface and delegation pattern do not reliably carry the requirement into later tool calls.
  - Expected pattern: provide or promote a stable repository-owned launcher or preflight that selects and verifies the experiment dependency environment; until then, orchestration prompts and commands for this experiment should name the exact verified interpreter up front rather than relying on remembered shell activation.

- `2026-08-22`: Codex WSL commands inherit a Windows temporary directory
  - Context: current-form successor generator tests use Python `tempfile.TemporaryDirectory()` and require Linux `renameat2(RENAME_NOREPLACE)` for atomic directory publication.
  - Observation: the Codex command environment sets the effective temporary root to `/mnt/c/Users/.../AppData/Local/Temp`; temporary publications therefore run on DrvFS and fail with `OSError: [Errno 95] atomic no-replace directory rename unavailable`. Repeated agent and main-thread retries reproduced the same failure, while an explicit native `/tmp` output succeeded.
  - Expected pattern: the repository-owned experiment launcher or test preflight should force and verify a native Linux temporary root such as `TMPDIR=/tmp` before atomic-publication tests; orchestration should not rely on the host-injected temporary-directory environment for WSL filesystem semantics.

- `2026-08-23`: Codex Playwright route rejects the WSL workspace URI before launch
  - Context: two fresh independent hands-on visual-review agents each attempted to open the same local comparator through the Codex Playwright route from a WSL project.
  - Observation: both trials stopped before navigation or browser launch. The route reported `Mcp error -32602: js: codex/sandbox-state-meta: sandboxCwd is not a local file URI: file:///home/ben/src/creature-kernel`; one environment also had no local Playwright package or browser executable to provide an alternate headless path. Repeating this route left all interaction, console, network, and asset checks untested and forced replacement trials.
  - Expected pattern: visual-review prompts should name the required T3 collaborative preview first and the documented readable PowerShell-stdin Chrome/CDP bridge as fallback. After this WSL URI error, do not retry the same Playwright route; report it and switch once to a supported path. Codex browser tooling should eventually accept a native WSL `file:///home/...` sandbox working directory or expose a clear preflight failure before a trial is delegated.

- `2026-08-23`: Provisioned local browser tooling is not automatically discoverable by delegated trials
  - Context: after the Codex Playwright route failed in WSL, a working isolated Playwright 1.62.1 and Chromium runtime was provisioned under `/home/ben/.cache/creature-kernel`, with the launcher `/home/ben/.cache/creature-kernel/playwright-runtime/ck-playwright-node` setting the browser path, `NODE_PATH`, and a native Linux temporary root.
  - Observation: later browser-trial delegation can still appear to require fresh Playwright setup because subagents do not automatically discover machine-local wrappers or inherit main-thread shell setup. Omitting the verified launcher from a trial prompt risks repeating installation probes, failed imports, or unsupported browser-route calls.
  - Expected pattern: once a local fallback is verified, every bounded browser-trial prompt should name its exact launcher and environment explicitly. If the fallback remains useful, promote it to a repository-owned preflight or wrapper so agents can discover and validate it consistently instead of depending on orchestration memory.

- `2026-08-23`: A repository launcher still needs one stable provisioned environment
  - Context: the new surface-preview launcher correctly rejected both a missing default cache interpreter and a transient `/tmp` interpreter whose installed Pillow version had drifted from the pinned requirements.
  - Observation: adding a launcher does not itself provision dependencies. Falling back to an older transient interpreter after the default preflight fails merely turns a missing-environment error into a package-version error and repeats setup work.
  - Expected pattern: create the launcher's documented cache environment once from the checked-in requirements, then invoke every main-thread and delegated experiment command through the launcher without an interpreter override. Treat a failed preflight as a setup prerequisite to repair, not a reason to bypass the launcher.

- `2026-08-23`: Markdown backticks can break JavaScript-composed orchestration payloads
  - Context: a main-thread subagent launch embedded a Markdown code span inside a JavaScript template literal. The launch failed before execution with `SyntaxError: Unexpected identifier '_validate_authored_torso_profile'`; this payload-construction mistake had occurred in an earlier orchestration round as well.
  - Observation: raw Markdown backticks terminate or alter JavaScript template literals unless escaped, so otherwise valid delegation text can prevent the tool call from reaching the orchestration service. Retrying the same content as an array of ordinary quoted strings joined by newlines succeeded.
  - Expected pattern: compose long orchestration prompts from plain quoted string arrays or structured text items, with no raw Markdown code spans inside JavaScript template literals. Prefer a small reusable payload helper if this pattern recurs again; treat the syntax error as deterministic input construction, not a transient tool glitch.

- `2026-08-23`: Pull-request body stdin is unavailable through the ordinary command wrapper
  - Context: a main-thread `gh pr create --body-file -` call supplied a complete body in orchestration code but did not attach that text to the command process's standard input.
  - Observation: `gh` received immediate EOF, successfully created PR #110 with an empty body, and reported no command error. A follow-up `gh pr view` exposed `"body":""`; writing the intended body to an explicit temporary file and using `gh pr edit --body-file` repaired it.
  - Expected pattern: do not use `--body-file -` with the ordinary non-interactive command wrapper unless its standard input is explicitly supported and populated. Use an explicit reviewed file for long PR bodies, then read the PR back immediately to verify title, body, head, base, and state before treating creation as complete.

- `2026-08-23`: Ripgrep options must precede the explicit pattern separator
  - Context: the main thread twice tried to protect a pattern with `rg --` but placed an option after the separator, first while searching for a pattern beginning with hyphens and later while adding context lines.
  - Observation: every token after `--` is positional, so `rg -n -- "pattern" -C 2` treats `-C` and `2` as paths and reports misleading missing-file errors instead of applying context. The failure is deterministic command construction, not repository or tool instability.
  - Expected pattern: place every option before the separator, for example `rg -n -C 2 -- "pattern" paths`; use `--` immediately before the pattern only when option parsing must end.

- `2026-08-23`: Surface-preview launcher use is still fragile across working directories and focused test selectors
  - Context: a delegated focused regression invoked the repository launcher twice from the tests directory using its worktree-relative path, then once from the worktree root with a top-level unittest module name.
  - Observation: the first two calls failed with exit 127 because the relative launcher path was resolved from the tests directory; the third reached the launcher but failed with `ModuleNotFoundError: No module named 'test_surface_preview'`. Falling back to full discovery succeeded but reran all 61 tests, adding avoidable delay after the prompt had already required the launcher.
  - Expected pattern: delegation prompts and examples should give a worktree-root command using the repository-relative launcher plus a valid discovery command. If focused single-test execution is common, add a documented launcher-supported selector or wrapper that resolves paths independently of the caller's working directory.

- `2026-08-24`: Provisioned Playwright wrapper does not make arbitrary module styles interchangeable
  - Context: a WSL browser trial was given the exact provisioned `ck-playwright-node` launcher but first combined CommonJS `require()` with top-level `await`, then changed to a bare ESM `playwright` import.
  - Observation: the first script failed with `ReferenceError: Cannot determine intended module format because both require() and top-level await are present`; the second failed with `ERR_MODULE_NOT_FOUND` because ESM package resolution did not use the wrapper's CommonJS-oriented module path. An `.mjs` script importing the provisioned `playwright/index.mjs` by its explicit absolute path succeeded.
  - Expected pattern: provide one checked browser-trial script template with a single module style and the provisioned runtime's exact import path, or extend the wrapper to expose a stable script entrypoint. Naming the launcher alone does not prevent repeated JavaScript module-resolution failures.

- `2026-08-24`: Markdown backticks in double-quoted shell searches are executable syntax
  - Context: the main thread combined documentation validation with an `rg` search whose double-quoted shell pattern contained a literal Markdown backtick.
  - Observation: Bash attempted command-substitution parsing and failed before validation with `/bin/bash: unexpected EOF while looking for matching backtick`. One retry using a single-quoted plain pattern succeeded; no repository or external state changed.
  - Expected pattern: never place Markdown backticks in a double-quoted shell command. Use single-quoted fixed patterns or pass text as a structured argument or file; split validation and search commands when that makes quoting easier to audit.

- `2026-08-24`: Browser comparison trials need exact controls, visible hit targets, and coalescing-aware routes
  - Context: repeated Playwright trials of the image-comparison modal selected `Next` ambiguously between the navigation button and displayed image, clicked coordinates outside the visible portion of a zoomed image, and assumed the modal would issue a second PNG request after a matching lazy thumbnail request.
  - Observation: strict locators failed when roles shared similar names; Playwright auto-scrolled off-screen locator coordinates before dispatch and falsely resembled an application pan reset; browser resource coalescing attached modal loading to the already-pending thumbnail request, so request-count waits timed out or failure injection hit the wrong consumer.
  - Expected pattern: target exact aria labels such as `Show next image`; use `elementFromPoint` to prove a pointer coordinate is already visible inside the intended target before clicking; and design delayed/failure routes around one held request that the thumbnail and modal may share rather than requiring a second request.

- `2026-08-25`: Ad-hoc `jq` projections need schema and keyword preflights
  - Context: main-thread and delegated inspection of BodyDocument and structural-profile candidate JSON during the structural-embodiment bridge work.
  - Observation: one query assumed `parts` and related arrays were top-level instead of under `body`, and another used the reserved `label` token in object shorthand; both failed before returning evidence and required corrected retries. These were deterministic query-construction mistakes, not malformed repository JSON.
  - Expected pattern: inspect top-level keys before composing a new structural projection, use explicit aliases for potentially reserved fields such as `label_text: .label`, and promote repeated non-trivial projections into checked scripts or fixtures instead of rebuilding them from memory.

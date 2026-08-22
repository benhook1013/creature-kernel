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

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

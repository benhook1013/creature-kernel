# Gate B v2 Review 02: execution admissibility

Review status: Complete; current only for reviewed execution-tool commit
`9dca58a84072582db34045b8eac98d6e86d3d5ae`, manifest self-hash
`d7365e99945cb2e57cd6bac45bac241fc032dc1312cda3a94cfdba14cd17933a`, and
reviewed HEAD `6d9a812387c0704e5f58ac09556361af609a7e1`; stale for any
successor revision

Gate: B — frozen-package v2 Double review

Result: Revise

Review lens: `execution-admissibility`

Independence: Fresh independent evidence-only pass; no authorship, edits, or
execution.

Reviewer: `/root/gateb_v2_execution_admissibility`

Launch configuration: Requested `gpt-5.6-sol`, reasoning `medium`, by the
orchestrator. Runtime model identity was not independently attested.

Date: 2026-08-19

## Target material

The review covered reviewed E
`9dca58a84072582db34045b8eac98d6e86d3d5ae`, the v2 freeze manifest with
self-hash `d7365e99945cb2e57cd6bac45bac241fc032dc1312cda3a94cfdba14cd17933a`,
and reviewed HEAD `6d9a812387c0704e5f58ac09556361af609a7e1`. The freeze remains
Proposed and execution-disabled. This review does not authorize an exact
attempt or native dispatch, and does not claim that a successor is clean.

## Findings

### High — no experiment-wide exactly-once platform/ordinal reservation

There is no experiment-wide exactly-once platform/ordinal reservation. An
arbitrary output root permits repeats and evidence selection. Add a canonical
manifest + platform + ordinal ledger binding the attempt ID.

### High — frozen platform and filesystem requirements are not admitted

Frozen platform and filesystem requirements are not admitted. Path-specific
probes and required facts must fail or be inconclusive when they are absent or
unresolved; they must not support an attempt.

### High — no frozen cross-attempt adjudicator

There is no frozen cross-attempt adjudicator. A single attempt can report
support before the WSL repeat and native comparison. Add an exact 0/1/2 closure
tool and schema with an experiment-level disposition; per-attempt status is
not experiment support.

### Medium — retained identity is post-exec, not post-run

Post identity is post-exec rather than post-run, and lifecycle observations are
dropped. Retain terminal cwd, lifecycle, signal, reap/kill, partial,
stdout/stderr, startup, and resource evidence, or narrow the claim.

## Coverage and checks

The pass successfully derived E, checked ancestry, matched all 19 tool
identities, verified the freeze self-hash, and confirmed the absence of attempt
and authority records. The review also confirmed that no prohibited candidate,
Rust, Cargo, exact-attempt, native-dispatch, or experiment execution occurred.
These checks do not resolve the findings above or establish execution
admissibility.

No edits were made and no execution was performed. No Ben acceptance or waiver
is implied.

## Disposition and staleness

This is completed historical issue-finding evidence for the exact reviewed v2
materialization only. The verdict is `Revise`. After the findings are
addressed, any corrected successor must receive a fresh current-version Gate B
Double review; this artifact must not be treated as current evidence for that
successor.

# Gate B v2 Review 01: closure and custody

Review status: Complete; current only for reviewed execution-tool commit
`9dca58a84072582db34045b8eac98d6e86d3d5ae`, manifest self-hash
`d7365e99945cb2e57cd6bac45bac241fc032dc1312cda3a94cfdba14cd17933a`, and
reviewed HEAD `6d9a812387c0704e5f58ac09556361af609a7e1`; stale for any
successor revision

Gate: B — frozen-package v2 Double review

Result: Revise

Review lens: `closure-and-custody`

Independence: Fresh independent evidence-only pass; no authorship, edits, or
execution.

Reviewer: `/root/gateb_v2_closure_custody`

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

### High — frozen binaries exceed the exact transport cap

The frozen WSL/native binaries are 100,944,288 and 100,945,304 bytes,
respectively, exceeding the exact transport cap of 64 MiB. Static
compatibility must be checked before reservation; reconcile the cap or rebuild
the binaries, then create a new reviewed E and freeze.

### High — the public exact-attempt entrypoint accepts arbitrary dependencies

The public exact-attempt entrypoint accepts arbitrary dependency callables, and
aliases expose that surface. The public production path must use the frozen
dependencies; dependency injection must be private or test-only.

### Medium — outcome-affecting Python runtime and invocation are not frozen

The outcome-affecting Python runtime and invocation are not frozen or
truthfully retained. Bind the exact implementation, version, invocation, and
actual facts, and document the trusted module-loading boundary.

### Medium — Gate B preflight tests are stale against v2

The Gate B preflight test state is stale against v2: 1 test passed, 1 failed,
and 3 errored. Use immutable v1 fixture bytes together with the current
successor fixtures, then rerun the relevant checks for the successor.

## Coverage and checks

The pass successfully checked reviewed-E ancestry, the freeze self-hash,
materialized projection, the 8 runtime + 7 exact-runtime + 4 provenance tool
identities, candidate prebinding, the current read-only preflight, and the
review diff. These checks do not resolve the findings above or make the
execution package admissible.

No candidate, Rust, Cargo, exact-attempt, native dispatch, or experiment
execution was performed. No Ben acceptance or waiver is implied.

## Disposition and staleness

This is completed historical issue-finding evidence for the exact reviewed v2
materialization only. The verdict is `Revise`. After the findings are
addressed, any corrected successor must receive a fresh current-version Gate B
Double review; this artifact must not be treated as current evidence for that
successor.

# Gate B Review 02: execution admissibility

Review status: Complete; current only for freeze self-hash
`122b0a88bf553e95a887acebfe436d95218389e339ea5aa1f3c85d0f5186fef3` and
stale for any successor revision

Gate: B — frozen-package Double review

Result: Revise

Review lens: Exact executable custody, prelaunch admissibility, wrapper and
dispatch identity, process lifecycle, transport and floating-point controls,
authorization boundaries, and immutable result/receipt publication.

Independence: Fresh independent evidence-only pass; no authorship or edits.

Launch configuration: Requested `gpt-5.6-sol`, reasoning `medium`, by the
orchestrator. Runtime model identity was not independently attested.

Date: 2026-08-19

## Target material

The review covered exact commit
`553d51bd55dd837b01b950d063d288369f61e56d`, the frozen phase-three package,
freeze manifest self-hash
`122b0a88bf553e95a887acebfe436d95218389e339ea5aa1f3c85d0f5186fef3`, WSL and
native receipts, the Gate B preflight and evidence contracts, and the
47-file candidate/source closure. The freeze remains Proposed and
execution-disabled. This review does not claim an executed attempt, native
dispatch, Ben authorization, acceptance, or waiver.

## Findings

### High — no exact executable attempt wrapper and dispatch path are frozen

The package does not freeze an exact executable attempt wrapper/path together
with its `argv`/environment, selected-binary verification, three-process
lifecycle, transport and FE/MXCSR controls, no-retry rule, authorization
verification, and exclusive immutable result/receipt/index publication. Define
and bind the exact WSL/native wrapper and dispatch contract, including these
controls, then make the prelaunch check fail closed unless the selected binary
and all immutable result surfaces match the frozen identities.

### High — exact binaries lack durable admissible custody and prelaunch
verification

Receipt and ELF identities alone do not establish that the exact bytes are in
durable custody or that the prelaunch executable is the byte-identical artifact
that was built and transferred. Preserve the exact bytes with an approved
durable/content-addressed locator and verify them immediately before launch;
otherwise fail closed and refreeze rather than dispatching from an
unverifiable path.

### Medium — atomic finalization publishes a mode-0600 freeze manifest

The atomic finalizer leaves the freeze manifest at `0600`, but the canonical
materialized adapter requires mode `0644`. The current preflight therefore
fails before execution admissibility can be established. Correct the writer,
checker, and tests and regenerate the freeze before relying on prelaunch
admissibility.

### Medium — lifecycle/preflight conflates development materialization with
finalized execution-package freeze

The lifecycle and preflight surfaces do not clearly separate development-
unfrozen corpus materialization from a finalized execution-package freeze.
Consume and bind the actual freeze manifest and receipts while keeping
execution unauthorized; record the immutable Gate A snapshot and explicit
supersession or otherwise align the lifecycle fields so preflight cannot make
development materialization appear executable.

## Coverage and checks

The pass independently matched the freeze self-hash, receipt identities,
binary bindings, and the 47-file closure (path-set SHA-256
`10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc`, content
SHA-256 `21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2`,
and 1,494,337 raw bytes). Self-hash checks and the
freeze, receipt, and evidence focused tests passed. Two of the three current
preflight tests failed on the mode-0600 freeze manifest; the preflight suite
passed on a clean checkout with the expected mode. The review also checked
that the frozen package has no execution result or experiment-run evidence.

The final recorder checks `python3 dev-tools/validation/validate_docs.py` and
`git diff --check` also passed.

No candidate or Rust execution, exact attempt, native dispatch, or experiment
run was performed. No Ben acceptance or waiver is implied.

## Disposition and staleness

This is completed historical issue-finding evidence for the exact reviewed
freeze revision only. The verdict is `Revise`. The fixes require a fresh
current-revision Double review of the successor freeze; this artifact is stale
for that successor and cannot satisfy its review requirement.

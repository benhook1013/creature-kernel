# Gate B Review 01: closure and custody

Review status: Complete; current only for freeze self-hash
`122b0a88bf553e95a887acebfe436d95218389e339ea5aa1f3c85d0f5186fef3` and
stale for any successor revision

Gate: B — frozen-package Double review

Result: Revise

Review lens: Closure integrity, immutable freeze inputs, publication modes,
binary custody, transfer provenance, receipt binding, and the distinction
between preregistration materialization and frozen execution inputs.

Independence: Fresh independent evidence-only pass; no authorship or edits.

Launch configuration: Requested `gpt-5.6-sol`, reasoning `medium`, by the
orchestrator. Runtime model identity was not independently attested.

Date: 2026-08-19

## Target material

The review covered exact commit
`553d51bd55dd837b01b950d063d288369f61e56d`, including the frozen phase-three
package, freeze manifest, WSL/native build receipts, materialized corpora and
manifests, Gate B tooling, and the 47-file candidate/source closure. The
freeze manifest self-hash independently matched
`122b0a88bf553e95a887acebfe436d95218389e339ea5aa1f3c85d0f5186fef3`.
The freeze binds candidate source commit
`647eab5297adca1998764904cce98eca154738e4`, but remains Proposed and
execution-disabled; this review does not authorize an exact attempt or native
dispatch.

## Findings

### High — atomic finalization publishes a mode-0600 freeze manifest

The atomic finalizer leaves `manifests/freeze-manifest.json` at mode `0600`,
while the canonical materialized adapter requires a regular mode-`0644` file.
Consequently Gate B preflight rejects the current frozen package with
`file-mode: freeze manifest sidecar is not mode 0644`. Fix the writer's final
publication mode and make the checker and focused tests assert the published
mode before refreezing the successor candidate.

### High — exact binary custody and causal build provenance are not closed

The freeze binds receipt hashes and ELF/binary identities, but it does not
close exact byte custody and causal build provenance. The native artifact is
described with a 90-day retention window, the run/artifact digest is absent
from the freeze, and the WSL receipt retains a temporary path. The receipt
joins caller-supplied metadata to ELF observations, but does not itself prove
that the bound bytes came from the declared build or that no execution
occurred. Require an approved content-addressed custody record with a durable
locator, bind transfer and run identity, and perform fail-closed byte
verification at each transfer/consumption boundary. Until that evidence exists,
narrow the binary/custody declarations to what is actually attested rather
than implying durable exact-artifact admissibility.

### Medium — frozen manifest and preregistration lifecycle fields need an
explicit snapshot distinction

The frozen manifest is `Proposed`/materialization-state `frozen`, while the
preregistration still carries `pending-freeze`/`development-unfrozen` fields.
Record an immutable Gate A snapshot and explicit supersession relationship, or
align the lifecycle fields, so consumers cannot confuse the development corpus
with the finalized execution-package inputs.

## Coverage and checks

The pass independently matched the freeze manifest self-hash, both receipt
content hashes and self-hashes, both binary bindings, and the 47-file closure
(path-set SHA-256
`10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc`, content
SHA-256 `21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2`,
and 1,494,337 raw bytes).
The freeze checks and the 19 build-receipt tests plus 19 freeze-manifest tests
passed, as did the documentation checks used for the review. The read-only
Gate B preflight was intentionally exercised and failed on the current
mode-0600 freeze manifest, as described in the first finding.

The final recorder checks `python3 dev-tools/validation/validate_docs.py` and
`git diff --check` also passed.

No candidate or Rust execution, exact attempt, native dispatch, or experiment
run was performed. No Ben acceptance or waiver is implied.

## Disposition and staleness

This is completed historical issue-finding evidence for the exact reviewed
freeze revision only. The verdict is `Revise`. After the publication, custody,
provenance, and lifecycle findings are addressed, the successor freeze must
receive a fresh current-revision Double review; this artifact must not be
treated as current evidence for that successor.

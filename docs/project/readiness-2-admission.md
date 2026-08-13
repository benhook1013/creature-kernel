# Readiness 2 admission record

Status: Proposed admission record (not an accepted DR)

Admission owner: Ben

Owner approval: Pending for this admission record

Review status: Pending for this candidate transaction

Activation state: Inactive — Readiness 2 is not admitted or active

## Proposed admission

This record proposes admitting DR-0013 Readiness 2 as one exact transaction:
the `creature-kernel.body` revision 1 schema, the
`creature-kernel.fixture-manifest` revision 1 schema and manifest, all nine
declared fixtures, and the Rust parser/bootstrap implementation at reviewed
source commit
`b114a35d79d777ac55f1200805358aa5a5c1eb10`.

This proposal does not accept any still-Proposed DR, activate semantic
resolution or Readiness 3, select geometry or a host engine, or claim
performance, portability beyond the named reference target, or expected-result
correctness from hashes alone. Until Ben explicitly approves this record and
post-merge recomputation succeeds, Readiness 1 remains the only active gate.

## Exact candidate

| Evidence | Identity or value |
| --- | --- |
| Reviewed source commit | `b114a35d79d777ac55f1200805358aa5a5c1eb10` |
| Readiness 1 predecessor commit | `1c9a6542d9dbad1c13e5d997108a1b24a20b460b` |
| Manifest path | `fixtures/body-documents/readiness-2/manifest.v1.json` |
| Manifest SHA-256 | `4e35af3daf413a46ed2cddb3268c37c996df9a3250db816185b71d00c22140fd` |
| Body schema SHA-256 | `e2a866a911664440928d0343f7bdf9bb954c9ef0e165d3b9d3a0df2a594d1bf9` |
| Manifest schema SHA-256 | `bea3efd4a34aa132eccfe0a1e5f97c116762374da223f07bc87afb478a9f278c` |
| Fixture payload framing | `ck.path-set.raw.v1` |
| Fixture payload SHA-256 | `b6690a2276f8ab7202ec73a6093a1fc8862ecd0591dfd1cc54bad7ebfb94dfcc` |
| Implementation framing | `ck.implementation-path-set.raw.v1` |
| Implementation SHA-256 | `cf01c6a5b5d6eb2fa520b5cf1ddbfe2fe28a104bc3e13ba977f38c8ac7df8b4c` |
| Admission-support framing | `ck.readiness-support-path-set.raw.v1` |
| Admission-support SHA-256 | `96827f6260b49e3496c7568879f53dc90716ebdf2dafcd508bf9bc24dd416aee` |
| Dependency framing | `ck.cargo-lock.dependency-closure.v1` |
| Cargo.lock SHA-256 | `9c8e8b7471bc03f590aacdc6adb2b3987f1c8bfbc1064c120b9ba0b2644b1cc5` |
| Dependency-closure SHA-256 | `ec794e459cc84566174789b2c7ac082797ca29a7c67bdf34a9f1effadfd210af` |
| Build-request framing | `ck.rust-build-request.v1` |
| Build-request SHA-256 | `50a88b87360901fdc1f350603718a33e3caca6f433a67dc983c6684949f37783` |

The implementation binding contains the workspace and member manifests,
`Cargo.lock`, `rust-toolchain.toml`, the core library entry point and parser,
and the exact body schema. It explicitly binds `.cargo/config.toml` as absent.
The separate admission-support binding contains the fixture preflight, evidence
generator, and manifest schema. The dependency projection contains 105 packages
reachable from `creature-kernel-core`, including selected features, checksums,
license expressions, native `links` declarations, and normalized dependency
identities. Repository-local identities are workspace-relative; an exact Git
archive at a different filesystem path reproduced all five binding hashes.

The exact build request is Rust `1.97.1`, target
`x86_64-unknown-linux-gnu`, package `creature-kernel-core`, default features,
development profile, and these locked/offline commands:

```text
cargo test -p creature-kernel-core --all-targets --locked --offline
cargo clippy -p creature-kernel-core --all-targets --locked --offline -- -D warnings
```

Reference environment evidence was `rustc 1.97.1
(8bab26f4f 2026-07-14)`, host `x86_64-unknown-linux-gnu`, LLVM `22.1.6`,
and `cargo 1.97.1 (c980f4866 2026-06-30)`. Environment text is evidence rather
than equality-bound identity beyond the target/toolchain fields in the build
request.

## Candidate checks

At the reviewed source commit:

- parser-independent preflight passed and reproduced the manifest and fixture
  payload identities above;
- a fresh Git-archive snapshot at a different absolute path reproduced the
  fixture, implementation, admission-support, dependency, and build-request
  identities exactly;
- 12 fixture-preflight and 10 evidence-generator unit tests passed;
- 22 core parser/bootstrap tests and all workspace tests passed locked/offline;
- workspace formatting and clippy with warnings denied passed;
- documentation validation and `git diff --check` passed; and
- no third-party package in the resolved projection lacked license metadata.

These are technical checks, not owner approval or activation.

## Review and activation procedure

The current candidate receives two independent fresh reviews: one focused on
schema/parser correctness, hostile-input handling, diagnostics, and contract
alignment; the other focused on admission closure, reproducibility,
dependencies, governance, and future-gate isolation. Actionable technical
correctness findings revise the candidate and make this exact record stale.

If both reviews support admission and Ben explicitly approves this record, the
main thread may merge the transaction. After merge and immediately before
marking Readiness 2 active, it must recreate a fresh private read-only source
snapshot, rerun preflight and evidence generation, and require every
equality-bound candidate identity above to match: the manifest/schema/fixture
payload, implementation, admission-support, dependency-closure, and
build-request identities. The merged Git commit may differ from the reviewed
source commit; commit provenance is not an equality binding. Environment text
is informational except for the target/toolchain fields already bound by the
build request. Any mismatch blocks activation and requires a successor
admission record. Successful recomputation may then update project status and
repository evolution to mark Readiness 2 active; it does not activate Readiness 3.

# Readiness 2 admission record

Status: Active project admission record (not an accepted DR)

Admission owner: Ben

Owner approval: Approved by Ben — 2026-08-13; decision evidence: Ben instructed
“do it” in response to “approve and waive.”

Review status: Waived — the agreed Double adversarial review completed, its
blockers were corrected, and consolidated validation passes. Ben explicitly
directed no repeat review loop, approving and waiving another current-candidate
review on 2026-08-13.

Activation state: Active

## Admitted transaction

This record admits DR-0013 Readiness 2 as one exact transaction:
the `creature-kernel.body` revision 1 schema, the
`creature-kernel.fixture-manifest` revision 1 schema and manifest, all nine
declared fixtures, and the Rust parser/bootstrap implementation at reviewed
source commit
`691ee2ee0946ee2625fc3db8cd1c8a11826be024`.

The merged transaction is recorded at Git commit
`766992ab089687e9b1496574e8ffa721388d96f3` (PR #6). This activation does not
accept any still-Proposed DR, activate semantic resolution or Readiness 3,
select geometry or a host engine, or claim performance, portability beyond the
named reference target, or expected-result correctness from hashes alone.
Readiness 2 is Active only for this parser/bootstrap/schema/manifest/fixture
transaction.

## Exact admitted contents

| Evidence | Identity or value |
| --- | --- |
| Reviewed source commit | `691ee2ee0946ee2625fc3db8cd1c8a11826be024` |
| Merged Git commit | `766992ab089687e9b1496574e8ffa721388d96f3` |
| Merged pull request | `#6` |
| Readiness 1 predecessor commit | `1c9a6542d9dbad1c13e5d997108a1b24a20b460b` |
| Manifest path | `fixtures/body-documents/readiness-2/manifest.v1.json` |
| Manifest SHA-256 | `4e35af3daf413a46ed2cddb3268c37c996df9a3250db816185b71d00c22140fd` |
| Body schema SHA-256 | `e2a866a911664440928d0343f7bdf9bb954c9ef0e165d3b9d3a0df2a594d1bf9` |
| Manifest schema SHA-256 | `bea3efd4a34aa132eccfe0a1e5f97c116762374da223f07bc87afb478a9f278c` |
| Fixture payload framing | `ck.path-set.raw.v1` |
| Fixture payload SHA-256 | `b6690a2276f8ab7202ec73a6093a1fc8862ecd0591dfd1cc54bad7ebfb94dfcc` |
| Implementation framing | `ck.implementation-path-set.raw.v1` |
| Implementation SHA-256 | `11c108d5f6549d95531028c5f478fd9bab46908a2fd1f1ed26ffb7c6f7665ad4` |
| Admission-support framing | `ck.readiness-support-path-set.raw.v1` |
| Admission-support SHA-256 | `beebb0c72c4d8fb11580e30997b0b2507c27d8e2548ff3d0c22bfd8ce032deb2` |
| Dependency framing | `ck.cargo-lock.dependency-closure.v1` |
| Cargo.lock SHA-256 | `9c8e8b7471bc03f590aacdc6adb2b3987f1c8bfbc1064c120b9ba0b2644b1cc5` |
| Dependency-closure SHA-256 | `350d24ef7380530f046687cd8327b1478fed861dab6afd21d0ea3f99460ca962` |
| Build-request framing | `ck.rust-build-request.v1` |
| Build-request SHA-256 | `5c97fef86375787c3d32b116bacbce0f0f62a6cb32afc37c1505f7ef062ced6e` |
| Environment policy | `ck.sanitized-child-environment.v1` |
| Cargo-config policy | `ck.reject-cargo-config-ancestors-and-home.v1` |
| Target projection policy | `ck.exact-workspace-targets.v1` |

The implementation binding contains the workspace and member manifests,
`Cargo.lock`, `rust-toolchain.toml`, the core library entry point and parser,
and the exact body schema. It explicitly binds `.cargo/config.toml` as absent.
The separate admission-support binding contains the fixture preflight, evidence
generator, and manifest schema. The target-filtered dependency projection contains 91 packages
reachable from `creature-kernel-core`, including selected features, checksums,
license expressions, native `links` declarations, and normalized dependency
identities. Repository-local identities are workspace-relative; an exact Git
archive at a different filesystem path reproduced all five binding hashes.

The exact build request is Rust `1.97.1`, target
`x86_64-unknown-linux-gnu`, package `creature-kernel-core`, default features,
development profile, the sanitized-child-environment, rejected Cargo-config
ancestor/home, and exact-workspace-target policies above, and these
target-explicit locked/offline commands:

```text
cargo test -p creature-kernel-core --all-targets --target x86_64-unknown-linux-gnu --locked --offline
cargo clippy -p creature-kernel-core --all-targets --target x86_64-unknown-linux-gnu --locked --offline -- -D warnings
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
- 12 fixture-preflight and 16 evidence-generator unit tests passed;
- the sanitized bound runner passed 26 core parser/bootstrap tests and the
  target-explicit locked/offline clippy command with warnings denied;
- workspace formatting passed with `cargo fmt --all -- --check` under the
  pinned toolchain;
- scoped `git diff --check` passed for these three records; and
- no third-party package in the resolved projection lacked license metadata.

These are technical checks, not owner approval or activation.

## Post-merge recomputation and activation evidence

The agreed Double adversarial review completed with one review focused on
schema/parser correctness, hostile-input handling, diagnostics, and contract
alignment; the other focused on admission closure, reproducibility,
dependencies, governance, and future-gate isolation. Its blockers were
corrected and consolidated validation passes. No repeat current-candidate
review is required under Ben's explicit 2026-08-13 approval and waiver.

Ben's explicit approval and waiver permitted merge without a repeat review. The
required post-merge recomputation completed on 2026-08-13 from a fresh private
Git archive of exact merge commit
`766992ab089687e9b1496574e8ffa721388d96f3`, extracted in a new temporary
directory with archived modes preserved (`git -c tar.umask=0022 archive --format=tar
766992ab089687e9b1496574e8ffa721388d96f3 | tar --extract
--preserve-permissions`). The temporary snapshot was
`/tmp/creature-kernel-readiness2-archive.RLoGA4`; its path is ephemeral, while
the commit, commands, and identities below are the durable evidence.

Inside that snapshot, parser-independent preflight and evidence generation
passed. Every equality-bound identity matched this record:

| Binding | Recorded | Recomputed | Result |
| --- | --- | --- | --- |
| Manifest | `4e35af3daf413a46ed2cddb3268c37c996df9a3250db816185b71d00c22140fd` | `4e35af3daf413a46ed2cddb3268c37c996df9a3250db816185b71d00c22140fd` | Match |
| Body schema | `e2a866a911664440928d0343f7bdf9bb954c9ef0e165d3b9d3a0df2a594d1bf9` | `e2a866a911664440928d0343f7bdf9bb954c9ef0e165d3b9d3a0df2a594d1bf9` | Match |
| Manifest schema | `bea3efd4a34aa132eccfe0a1e5f97c116762374da223f07bc87afb478a9f278c` | `bea3efd4a34aa132eccfe0a1e5f97c116762374da223f07bc87afb478a9f278c` | Match |
| Fixture payload (`ck.path-set.raw.v1`) | `b6690a2276f8ab7202ec73a6093a1fc8862ecd0591dfd1cc54bad7ebfb94dfcc` | `b6690a2276f8ab7202ec73a6093a1fc8862ecd0591dfd1cc54bad7ebfb94dfcc` | Match |
| Implementation (`ck.implementation-path-set.raw.v1`) | `11c108d5f6549d95531028c5f478fd9bab46908a2fd1f1ed26ffb7c6f7665ad4` | `11c108d5f6549d95531028c5f478fd9bab46908a2fd1f1ed26ffb7c6f7665ad4` | Match |
| Admission support (`ck.readiness-support-path-set.raw.v1`) | `beebb0c72c4d8fb11580e30997b0b2507c27d8e2548ff3d0c22bfd8ce032deb2` | `beebb0c72c4d8fb11580e30997b0b2507c27d8e2548ff3d0c22bfd8ce032deb2` | Match |
| Cargo.lock | `9c8e8b7471bc03f590aacdc6adb2b3987f1c8bfbc1064c120b9ba0b2644b1cc5` | `9c8e8b7471bc03f590aacdc6adb2b3987f1c8bfbc1064c120b9ba0b2644b1cc5` | Match |
| Dependency closure (`ck.cargo-lock.dependency-closure.v1`) | `350d24ef7380530f046687cd8327b1478fed861dab6afd21d0ea3f99460ca962` | `350d24ef7380530f046687cd8327b1478fed861dab6afd21d0ea3f99460ca962` | Match |
| Build request (`ck.rust-build-request.v1`) | `5c97fef86375787c3d32b116bacbce0f0f62a6cb32afc37c1505f7ef062ced6e` | `5c97fef86375787c3d32b116bacbce0f0f62a6cb32afc37c1505f7ef062ced6e` | Match |

The recomputed framings and policies also matched: implementation and
admission-support path sets, dependency closure, and build request used the
recorded framing identifiers; environment policy was
`ck.sanitized-child-environment.v1`, Cargo-config policy was
`ck.reject-cargo-config-ancestors-and-home.v1`, and target projection policy
was `ck.exact-workspace-targets.v1`. The implementation binding again recorded
`.cargo/config.toml` as absent. The exact target/toolchain, package, default
feature, profile, and two locked/offline commands matched the build request.

The sanitized bound runner passed with
`python3 dev-tools/readiness-evidence/evidence.py --run-bound-checks
<snapshot>`: 26 core parser/bootstrap tests passed and target-explicit locked/
offline clippy passed with warnings denied. The merged Git commit is provenance,
not an equality binding; all bound hashes and checks matched, so activation
succeeded. This recomputation activates only Readiness 2 and does not activate
Readiness 3.

# Readiness 2 evidence generator

`evidence.py` emits a deterministic JSON evidence bundle for the technical
Readiness 2 admission review. It does not record admission, approval, merge,
activation, or expected-result correctness.

Run from the repository root (the root argument is optional):

```bash
python3 dev-tools/readiness-evidence/evidence.py [REPOSITORY_ROOT]
```

The same module provides the bounded setup/check runner:

```bash
python3 dev-tools/readiness-evidence/evidence.py --fetch-locked .
python3 dev-tools/readiness-evidence/evidence.py --run-bound-checks .
```

Both modes reject legacy/current Cargo config files in the repository, every
ancestor Cargo searches, and the selected Cargo home. They construct one
sanitized child environment that drops ambient `CARGO_*`, `RUST*`, compiler
flags, profile settings, and wrappers, then sets only the pinned toolchain and
default Cargo home. The bound test and clippy commands are locked/offline and
target `x86_64-unknown-linux-gnu` explicitly.

The generator imports `dev-tools/fixture-preflight/preflight.py` and places its
result verbatim under `fixture_payload`. The remaining identities are separate;
none of them records admission, approval, merge, activation, or expected-result
correctness:

* `implementation` uses `ck.implementation-path-set.raw.v1`. Records are sorted
  by UTF-8 path bytes and use the preflight raw framing: ASCII domain plus NUL,
  then each path's big-endian u32 byte length, UTF-8 bytes, big-endian u32 mode,
  big-endian u64 content length, and raw bytes. The eight selected paths are
  listed exactly in `paths`, including both workspace-member manifests because
  Cargo reads the workspace graph even for the core-only request.
  `.cargo/config.toml` is represented explicitly in
  `absent_paths` when absent and is still bound as a mode-zero, zero-byte record;
  if present, it is bound with its regular mode and bytes. Reads are
  descriptor-relative, no-follow, and require a regular singly-linked file with
  mode `100644` or `100755`.
* `admission_support` uses `ck.readiness-support-path-set.raw.v1` with the same
  raw path/mode/content framing and safe reader as `implementation`. Its exact
  paths are `dev-tools/fixture-preflight/preflight.py`, this evidence generator,
  and `spec/fixture-manifest/schema/ck-fixture-manifest-v1.schema.json`. This is
  an admission-support identity, not a claim that any of these files is
  production parser code.
* `dependency_closure` uses `ck.cargo-lock.dependency-closure.v1`, followed by
  the Cargo.lock byte length as a big-endian u64 and raw bytes, then the
  compact sorted-key ASCII-JSON projection byte length as a big-endian u64 and
  its bytes. The projection comes from the same sanitized child environment
  using `cargo metadata --format-version 1 --locked --offline --filter-platform
  x86_64-unknown-linux-gnu`, and is restricted to the graph reachable from
  `creature-kernel-core` (the workspace CLI is not included unless reachable).
  It also contains an exact normalized workspace target projection: only the
  explicit core library and CLI binary may exist; any auto-discovered
  bin/example/test/bench or build-script target fails closed. Each package records a normalized package
  identity, name, version, source, Cargo.lock checksum, license expression,
  native `links` declaration, sorted enabled feature names, and sorted
  dependency identities. Registry/Git identities retain Cargo's stable package
  ID; repository-local identities replace the absolute checkout prefix with a
  workspace-relative manifest directory, name, and version. Package records
  are sorted by normalized identity and every projection key is sorted. The
  projection bytes are ASCII-only
  (`ensure_ascii` JSON) and are declared evidence only; they do not claim that
  downloaded registry crate contents are vendored. Metadata failure is fatal and
  must be resolved by local setup/CI dependency fetching.
* `build_request` uses `ck.rust-build-request.v1` plus a canonical ASCII
  length-prefixed encoding. The fixed field order is target, toolchain,
  package, features, profile, environment policy, Cargo-config policy, target
  projection policy, commands, implementation SHA-256, dependency-closure
  SHA-256, and admission-support SHA-256. A scalar is
  `ASCII_DECIMAL_LENGTH:ASCII` and a list is `ASCII_DECIMAL_COUNT:` followed by
  each scalar encoding. Field names are scalar encoded before their values.
  The three referenced identities are emitted as fields and are not fixture
  payload identity.
* `environment_evidence` contains current `rustc -Vv` and `cargo -V` output as
  informational evidence. The active rustc release and host are checked against
  the fixed request (`1.97.1` and `x86_64-unknown-linux-gnu`); other environment
  values are not equality-bound.

The command performs no file writes. It is a bounded evidence input for a later
human admission record, not an admission gate or activation mechanism.

The evidence closes checkout path and ambient build-override inputs, but does
not claim full machine/container reproducibility: registry cache contents,
host kernel/CPU/filesystem behavior, installed toolchain artifacts, and native
tool behavior remain external evidence rather than vendored inputs.

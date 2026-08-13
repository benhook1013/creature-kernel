# Readiness 2 dependency review

Status: Evidence-only lightweight review; not a licensing decision, security audit, or admission record

Review date: 2026-08-13 (Pacific/Auckland)

Reviewed source commit: `3992b5e7fc0c12ff6c5ffc9ed15155473c423216` (observed `HEAD`)

Target: `x86_64-unknown-linux-gnu`

Toolchain: Rust `1.97.1` (`rustc 1.97.1 (8bab26f4f 2026-07-14)`, Cargo `1.97.1`)

Requested package: `creature-kernel-core`

Requested features/profile: default features (`default` in the build-request projection), development profile

This review covers the locked parser/bootstrap slice and its resolved dependency
closure. The source tree was not clean while this review was performed: the
reviewed commit is the observed provenance point, while the current working
tree also contained uncommitted candidate implementation edits. The review is
therefore not a claim that the commit alone contains the inspected working
tree. Before admission, recompute the locked/offline metadata, projection, and
review after the final candidate transaction is assembled. A later commit,
dependency update, feature change, target/profile change, or distribution
configuration invalidates this review as evidence.

## Inputs and method

The primary resolution check was:

```text
cargo metadata --format-version 1 --locked --offline --filter-platform x86_64-unknown-linux-gnu
```

The current evidence projection was also regenerated with:

```text
python3 dev-tools/readiness-evidence/evidence.py
```

That generator currently invokes `cargo metadata --format-version 1
--locked --offline --filter-platform x86_64-unknown-linux-gnu`, then keeps the
graph reachable from `creature-kernel-core` and records the workspace target
projection. Its dependency projection therefore uses the same target-relevant
package set as this review.
The inspected inputs included the workspace manifests, `Cargo.lock`,
`rust-toolchain.toml`, the cached registry manifests/sources, the current
evidence-generator projection, and the parser's embedded schemas and source.

## Resolution and direct dependencies

The target-filtered metadata contained 92 workspace packages. The graph
reachable from the requested core package contained 91 packages: the project
package plus 90 registry packages. The CLI member is not reachable from the
core-only request. The current evidence generator projection contained the
same 91 reachable packages and had dependency-closure SHA-256
`350d24ef7380530f046687cd8327b1478fed861dab6afd21d0ea3f99460ca962`.
An unfiltered Cargo metadata run would enumerate 105 core-reachable packages,
including 14 target-conditional packages, but those are outside this
target-relevant projection.

The core package has three required direct registry dependencies, all with
`default-features = false`:

| Dependency and enabled features | Parser-slice rationale |
| --- | --- |
| `serde 1.0.229`: `std`, `derive` | Typed serialization/deserialization and derive implementations. |
| `serde_json 1.0.151`: `std`, `float_roundtrip`, `arbitrary_precision`, `raw_value` | JSON input/output, round-trip float handling, preservation of arbitrary-precision number tokens, and grammar/resource preflight without eagerly materializing a value. |
| `jsonschema 0.49.9`: no crate features | Validation against the embedded Draft 2020-12 body schema. |

The enabled features above are the resolved features for the current working
tree. They are part of the dependency review input and must be rechecked if a
candidate edit changes a manifest.

The corresponding locked/offline build-request commands are:

```text
cargo test -p creature-kernel-core --all-targets --target x86_64-unknown-linux-gnu --locked --offline
cargo clippy -p creature-kernel-core --all-targets --target x86_64-unknown-linux-gnu --locked --offline -- -D warnings
```

## License metadata and disposition

Cargo metadata reported an SPDX license expression for all 90 third-party
packages in the target-reachable core closure. The expression distribution was:
40 `MIT OR Apache-2.0`, 18 `Unicode-3.0`, 16 `MIT`, 6 `Apache-2.0 OR MIT`,
2 each `Unlicense OR MIT` and `MIT/Apache-2.0`, and one each of
`(MIT OR Apache-2.0) AND Unicode-3.0`, `MIT-0`, `Zlib`, `Apache-2.0`,
`Apache-2.0/MIT`, and `BSD-2-Clause OR Apache-2.0 OR MIT`.

The project-owned `creature-kernel-core` package has no package license
metadata and is `publish = false`. This review records that absence; it does
not select, recommend, or imply a project license. No third-party license
metadata gap or unusual license expression was found that blocks this parser
slice at this lightweight evidence level. This is not legal approval or a
distribution-license decision.

## Build scripts and procedural macros

Sixteen target-relevant packages expose `build.rs` targets:

`ahash`, `getrandom`, `icu_normalizer_data`, `icu_properties_data`, `libc`,
`num-traits`, `parking_lot_core`, `proc-macro2`, `quote`, `ref-cast`, `serde`,
`serde_core`, `serde_json`, `unicode-general-category`, `zerocopy`, and
`zmij`.

The observed roles are target/configuration probes, Rust compiler-version
probes, generated Rust/private modules or tables, and `cfg` emission. A source
sweep found no `cc`, `cmake`, `pkg-config`, `bindgen`, or native library link
step in these build scripts. Several scripts invoke the selected `rustc` for
version or capability probes and write under Cargo's `OUT_DIR`; those are
build-time inputs and outputs, not network retrieval. The `libc` script also
contains best-effort probes for `emcc` and (under its CI setting)
`freebsd-version`; absent tools are tolerated and these probes do not compile
third-party native code. The Linux GNU target selects the corresponding libc
configuration branch.

Seven target-relevant packages are procedural-macro crates:

`displaydoc`, `ref-cast-impl`, `serde_derive`, `strum_macros`, `yoke-derive`,
`zerofrom-derive`, and `zerovec-derive`.

Their relevance is compile-time code generation for transitive data/utility
crates and the explicitly enabled `serde` derives. `jsonschema`'s optional
`macros` feature is not enabled, so `jsonschema-macros` is not in this target
closure. `proc-macro2`, `quote`, and `syn` are procedural-macro support
libraries in the graph even where their own target kind is not `proc-macro`.

## Unsafe, native, portability, and security observations

Cargo metadata reported no `links` declaration in any of the 91 target-relevant
packages. The graph contains `libc` through target-specific `getrandom` and
`parking_lot_core` paths, so the slice uses Unix/OS interfaces and inherits
the system C-library ABI at runtime; this is a system-interface dependency,
not evidence of a compiled third-party C/C++ library. No `openssl`,
`native-tls`, `cc`, `cmake`, or `pkg-config` package is in the target graph.

The workspace source has `unsafe_code = "forbid"`, and the core source had no
textual `unsafe` occurrence in this inspection. A mechanical textual search of
cached Rust sources found `unsafe` occurrences in 66 of the 90 third-party
packages (including comments, tests, cfg-disabled code, and declarations).
This inventory is deliberately not an unsafe-block audit and does not claim
that every occurrence was manually inspected. It identifies the expected
transitive unsafe surface in low-level crates such as `libc`, `zerocopy`,
`hashbrown`, `memchr`, `parking_lot`, and SIMD helpers; no specific material
concern was established by this bounded review.

The `jsonschema` dependency is selected with `default-features = false` and no
explicit features. Its default feature set would enable `resolve-http`,
`resolve-file`, and a TLS provider, but those features are absent here. The
target graph consequently contains no `reqwest` or `rustls` path for schema
resolution. The transitive `referencing` default retriever is an always-failing
retriever, and both candidate schemas use only local `#/$defs/...` references;
the embedded schema compilation path does not acquire files or network
resources. A future custom retriever, externally supplied schema, or enabled
resolver feature would change this security boundary and requires re-review.

`fancy-regex` remains a transitive `jsonschema` dependency and supports
backtracking patterns. The current schema is repository-owned and embedded;
this review did not assess regex worst-case behaviour or perform a denial-
of-service audit. If untrusted schemas/patterns or broader schema inputs become
part of the runtime contract, the parser resource profile and regex behaviour
need a focused security review.

The target-filtered graph is a portability observation for the named Linux GNU
target only. It is not a native-Linux portability smoke, Windows claim, or
cross-architecture claim. The target-specific `libc`/`getrandom` paths,
compiler probes, generated data, and SIMD/architecture cfgs are the main
portability inputs to revisit when another target is enabled.

## Limitations and re-review triggers

This is a one-pass, read-only dependency review. It did not perform a full
security audit, vulnerability database check, supply-chain audit, legal review,
manual inspection of every unsafe block, binary inspection, network sandbox
test, or native-Linux/Windows portability run. Registry sources were read from
the local Cargo cache; the lockfile and metadata identify the resolved
packages, but sources are not vendored by this review.

Re-review is required for any change to a dependency name/version/source,
`Cargo.lock`, enabled or default features, target triple, Rust toolchain/profile,
build script or proc-macro set, schema-resolution policy, distribution
packaging, or native/system integration. A fresh admission transaction must
also regenerate the evidence-generator projection and verify its distinct
implementation/dependency/build-request identities.

## Admission disposition

**No blocking dependency concern found for the named Readiness 2 parser slice
at this lightweight review level.** This is dependency evidence only; it does
not admit or activate Readiness 2, accept a project license, or replace the
separate admission record and human approval.

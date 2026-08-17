# EXP-0002 candidate adapter

This directory is a disposable research-only downstream Rust consumer of
`creature-kernel-core`. It is not a production CLI, public API, profile
selector, resolver, or R3 activation point.

## Current boundary

The JSONL entrypoint accepts one request per line and emits one response per
line. The candidate receives only an opaque request identifier, an operation,
and the required lexical/bit-string input. It receives no expected value,
oracle result, profile binding, corpus role, tags, or relation metadata; those
belong to the future runner.

The current binary supports decimal admission, scalar comparison, translation
comparison, and same-process environment attestation. Quaternion normalization
and quaternion comparison are deliberately reported as unsupported. The
separate `environment.rs` module also supplies a guarded square-root provider
and synthetic tests for later normalization integration.

## Environment boundary

`environment.rs` is limited to the research adapter. On x86_64 GNU/Linux it
uses a small documented unsafe boundary to read `fegetround` and MXCSR with
`stmxcsr`; it never calls setters or repairs the process state. It rechecks
before and after each dynamic `f64::sqrt`, records raw observations, decoded
MXCSR rounding-control (RC), and call bits, and returns the core provider
failure on any failed observation. The environment observation itself is
read-only: it performs no subnormal arithmetic probe or dynamic subnormal
output claim. The module has a compile-time unsupported implementation
elsewhere for other targets. No unsafe code or environment capability is added
to the core crate.

## Build, test, and synthetic run

From the repository root:

```bash
cargo build --manifest-path experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml --offline
cargo test --manifest-path experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml --offline
cargo run --manifest-path experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml --offline < request.jsonl > response.jsonl
```

These commands exercise only the current synthetic adapter surface. They do
not execute a frozen experiment corpus or produce result claims. An exact
request-byte/line-resource cap is still deferred before any corpus run, as are
toolchain/code-generation identity and independent square-root vectors before
quaternion support.

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

## JSONL transport boundary

Each raw request and serialized response frame is capped at 16,384 bytes,
counting all bytes including CR and an optional LF. An oversized request is
drained through its newline and produces exactly one `resource-limit` response
with error code `request-line-bytes`; the next record is then processed. An
EOF-terminated record is subject to the same cap. Invalid UTF-8, blank input,
and malformed JSON produce `error`/`malformed-request` and do not prevent later
records from being read. Input I/O failures and output serialization, write, or
flush failures propagate as transport failures rather than being converted to
synthetic observations.

The request identifier is limited to 256 UTF-8 bytes before operation dispatch.
An over-limit identifier receives `error`/`malformed-request` without an
echoed identifier. This bound leaves the fixed environment observation,
maximum accepted identifier, JSON escaping, and newline below the response
frame cap; a regression test serializes that maximum environment response.

Operation failures use stable machine-readable codes: decimal admission uses
`rejected` for invalid-number, non-finite/overflow, and nonzero-underflow
conditions; negative tolerances use `rejected` with a `negative-*-tolerance`
code; exact arithmetic failures use `error` with an `exact-arithmetic-*` code.
Existing token, significant-digit, exponent, invalid-input, unsupported, and
malformed-request categories remain distinct.

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
request/response frame cap is implemented here, but this adapter remains
research-only and unrun: it has no frozen profile, profile selector, corpus
result, or R3 activation. Toolchain/code-generation identity and independent
square-root vectors remain deferred before quaternion support.

# EXP-0002 phase-2 authored-conflict candidate

This is a small, standalone JSONL observer for the provisional
`provisional_authored_conflict_candidate` bridge. It is an inspectable
synthetic-observation tool, not an evidence runner. It does not create a
profile, corpus, result, receipt, resolver output, snapshot, or R3 activation.

Build and run it from the repository root with:

```bash
cargo test --manifest-path experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml --locked --offline
cargo run --manifest-path experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml --locked --offline
```

The process reads one bounded record at a time from stdin and writes one JSON
response per record to stdout. The request and response protocol identifiers
are respectively:

```text
ck.exp-0002.r3-authored-conflict-candidate-request-1
ck.exp-0002.r3-authored-conflict-candidate-response-1
```

The only operation is `observe-authored-conflict`. A request is a closed JSON
object with exactly these fields:

```json
{
  "protocol_id": "ck.exp-0002.r3-authored-conflict-candidate-request-1",
  "request_id": "example-1",
  "operation": "observe-authored-conflict",
  "resource_profile": "ordinary",
  "source": "<body document JSON string>",
  "tolerances": {
    "translation_absolute": 0.0,
    "translation_relative": 0.0,
    "rotation_half_chord": 0.0
  },
  "providers": {
    "gate": "allow",
    "arithmetic": "native",
    "sqrt": "native",
    "environment": "unattested-no-probe-v1"
  }
}
```

All tolerance and provider fields are required. `ordinary` is the only
resource profile in this slice. The named provider choices are `allow` or
`reject` for the gate and `native` or `unavailable` for arithmetic and square
root. Native providers are explicitly labelled `unattested`; the environment
choice is a declaration only. The candidate never inspects or changes
FE/MXCSR state.

The source string is decoded once by the request parser and its UTF-8 bytes
are passed directly to the bridge; it is never parsed and reserialized by the
CLI. Responses preserve bridge top-level and member-skip codes verbatim.
Observed members report root/dependency identity and role, compared/skipped
state, Attachment provenance, authored and Attachment-derived transforms,
exact finite binary64 component spellings (`0x` plus 16 hexadecimal digits),
and `agree`, `conflict`, or numeric `skipped` outcomes with component, code,
and detail.

Transport bounds are 64 KiB per request or response line (including LF), 24
KiB decoded source bytes, and 256 UTF-8 bytes for `request_id`. An oversized
request record is drained through LF/EOF and receives one small
`resource-limit`/`request-line-bytes` response before processing continues.
Oversized successful output receives one small
`resource-limit`/`response-line-bytes` response. Bounded EOF-terminated final
records are accepted. Blank, malformed UTF-8/JSON, duplicate-key, unknown,
missing, or wrongly typed requests receive `error`/`malformed-request` and do
not stop subsequent records. Valid request IDs are echoed for syntactically
valid request errors; an over-limit ID is never echoed. Broken output or I/O
remains a process failure.

This bridge currently lacks fine-grained failure causes and equation-step
evidence. Consequently these observations are provisional synthetic
instrumentation only and are not eligible for authoritative corpus or profile
freezing. In particular, the output must not be read as an `invalid-source`,
snapshot, resolver, selected-profile, activation, or evidence-qualified claim.

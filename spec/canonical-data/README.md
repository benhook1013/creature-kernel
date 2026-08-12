# Canonical data and digest profile

Status: Proposed canonical specification; no identity/build activation

The Batch 12 numeric update does not resolve Batch 11 C1 (total canonical
collection ordering), C3 (immutable Readiness 2/3 implementation binding), or
C4 (diagnostic-domain/bootstrap compatibility). Those findings remain open in
the current Proposed decision records; this document resolves none of them.

This document owns Creature Kernel's canonical JSON normalization,
serialization, digest framing, and digest domains. The [semantic-address
profile](../semantic-address/README.md) and [numeric and frame profile](../numeric-frame-profile/README.md)
own the semantic normalization rules that this profile consumes. In particular,
the numeric/frame profile owns JSON decimal admission, binary64 conversion,
negative-zero normalization, and quaternion normalization; canonical data only
consumes the resulting normalized binary64 values and does not redefine their
conversion. The [build-operation contract](../build-operation/README.md) owns
which inputs belong in a build request; this document defines how an already
selected projection is represented and hashed.

## CK canonical JSON

The project profile is `ck-json-1`. It starts from a strict duplicate-free
UTF-8 JSON data model and preserves Unicode scalar content exactly: no Unicode
normalization, locale conversion, or display-label rewriting is performed.
Semantic normalization occurs before serialization and consumes the active
numeric and address profiles. Thus negative-zero and quaternion-sign handling
are applied as already-defined semantic values, not reinterpreted here.
Arrays that are semantically ordered retain their order. A collection must not
be sorted merely because it happens to be represented as an array. Where a
contract supplies a semantic ordering for an unordered collection, that
ordering is consumed; a total key and duplicate/tie rule for every unordered
collection or projection has not yet been selected. The Batch 11 C1 finding
on canonical collection ordering remains unresolved and blocks claiming that
`ck-json-1` is fully activatable; this profile does not invent such a key.

After semantic normalization, serialization follows the rules of
[RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785):
deterministic object-member ordering and escaping, and the specified shortest
representation for applicable binary64 numbers. The underlying JSON model is
the strict syntax described by [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259).
The profile does not permit duplicate members, comments, NaN, infinities, or
implementation-defined number spellings. Object-member order is therefore
not identity-bearing; semantic array order is.

The canonical profile applies to normalized source, resolved graphs, build
requests, and fixture-manifest payloads. A raw-source digest is different: it
hashes the exact supplied source bytes and does not canonicalize, parse, or
repair them first, including preserving lexical negative zero and alternate
decimal spellings. A raw-artifact digest likewise hashes the exact published
artifact bytes.

## Digest domains and framing

The digest algorithm is SHA-256 as specified by
[FIPS 180-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf).
The digest's textual representation is `sha256:` followed by exactly 64
lowercase hexadecimal characters.

Every digest preimage has this unambiguous framing, encoded as ASCII where
specified:

```text
creature-kernel\0<versioned-domain-tag>\0<ASCII-profile-id>\0<payload-bytes>
```

The first three fields are fixed ASCII strings and cannot contain NUL. The
payload is the exact raw bytes for a raw domain or the UTF-8 CK canonical JSON
bytes for a canonical domain. The domain tag is versioned and closed; the
initial tags are:

| Domain tag | Payload |
| --- | --- |
| `ck/v1/exact-source` | exact authoritative source bytes |
| `ck/v1/normalized-source` | canonical normalized source JSON |
| `ck/v1/resolved-graph` | canonical successful resolved-graph JSON |
| `ck/v1/build-request` | canonical deterministic build-request projection |
| `ck/v1/fixture-manifest` | canonical fixture-manifest payload |
| `ck/v1/raw-artifact` | exact bytes of one published artifact |

The profile ID is `raw-bytes-1` for the exact-source and raw-artifact domains,
and `ck-json-1` for the canonical JSON domains. A future domain or profile
revision gets a new identity; it does not reinterpret an old digest.

## Identity exclusions

Attempt IDs, timestamps, staging names, host-specific output paths, allocation
order, logs, and human-readable diagnostic text are excluded from deterministic
identity projections. An output-affecting target/platform profile remains in a
build-request projection. The request projection also excludes any other
invocation-only trace fields while retaining every outcome-affecting source,
dependency, compiler/toolchain, contract/schema/profile, configuration/seed,
backend/capability/protocol, and target/platform input.

The fixture-manifest domain hashes the payload only. Its admission/approval
record, reviewed Git commit, successor/deactivation record, and mutable active
pointer are excluded, as are any fields that would make the manifest contain
its own digest. The [fixture-manifest contract](../fixture-manifest/README.md)
owns the exact declared path/mode/content set used for its external payload
binding.

Canonical data does not provide signatures, encryption, authenticity, or
content-addressed storage policy. Those are separate decisions if required.

## Activation boundary

Canonicalization and digest profiles are required before durable build,
artifact, or fixture identity activates. Activation must admit the exact
semantic-address and numeric/frame profile revisions they consume, the
canonical profile, domain tags, and representative byte/digest fixtures in one
reviewed contract path. No implementation package, schema, or generated
artifact is activated by this Proposed document.

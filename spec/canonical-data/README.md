# Canonical data and digest profile

Status: Proposed canonical specification; CK-KICK-012 Batch 13/14 discussion-approved
C1 resolution; no identity/build activation

Batch 13/14 discussion-approved resolutions add the generic keyed-collection rule
for C1, cross-link the separate Readiness 2/3 implementation binding for C3,
and align diagnostic ordering/identity with the C4 diagnostic profile. These
are Proposed contract updates only. Current Batch 13/14 material is recorded in
DR-0006 Revision 10, DR-0011 Revision 13, DR-0012 Revision 12, and DR-0013
Revision 10; each remains Proposed with Owner approval Pending and Review
Pending after the Batch 13 current-revision Double review. No decision record, schema, serializer, fixture, or readiness gate is
accepted or activated by this document.

This document owns Creature Kernel's canonical JSON normalization,
serialization, digest framing, and digest domains. The [semantic-address
profile](../semantic-address/README.md) and [numeric and frame profile](../numeric-frame-profile/README.md)
own the semantic normalization rules that this profile consumes. In particular,
the numeric/frame profile owns JSON decimal admission, binary64 conversion,
produced-zero-to-`+0` normalization, negative-zero normalization, and quaternion
normalization; canonical data only
consumes the resulting normalized binary64 values and does not redefine their
conversion. The [build-operation contract](../build-operation/README.md) owns
which inputs belong in a build request; this document defines how an already
selected projection is represented and hashed.

## CK canonical JSON

The project profile is `ck-json-1`. It starts from a strict duplicate-free
UTF-8 JSON data model and preserves Unicode scalar content exactly: no Unicode
normalization, locale conversion, or display-label rewriting is performed.
Semantic normalization occurs before serialization and consumes the active
numeric and address profiles. Thus every produced zero is already `+0`, while
raw lexical `-0` is retained only by raw-source identity; negative-zero and
quaternion-sign handling are applied as already-defined semantic values, not
reinterpreted here.
Arrays that are semantically ordered retain their order. A collection must not
be sorted merely because it happens to be represented as an array. Every
semantically unordered collection or projection must instead declare, in its
own canonical owner, a typed total canonical key and an explicit uniqueness or
multiplicity rule before it can enter a canonical projection. The key is
derived from the normalized semantic record; it is not serialized solely to
make sorting possible. A key collision fails closed when uniqueness is
semantic. Legitimate repetitions must declare a multiset/count, occurrence,
claim identity, or other owner-defined multiplicity semantics; canonicalization
must not silently deduplicate them.

The generic keyed-collection algorithm is: (1) normalize every member under
its owning contract; (2) derive its owner-declared typed key; (3) reject a
missing key or malformed key; (4) reject a collision when the owner declares a
unique collection; (5) sort by the key's exact total order; and (6) retain all
members under the declared multiplicity rule. There is no fallback to source
array order, array index, traversal or allocation order, object serialization,
canonical bytes, raw bytes, or any other incidental representation. A change
to a key's type, components, normalization, comparison, or multiplicity rule
changes the canonical profile identity and any affected digest identity.

The initial owner-declared key inventory is:

| Projection owner | Derived typed key and rule |
| --- | --- |
| Resolved body graph | The seven identity-bearing concepts use their structured semantic address; body-graph owns the address cross-link and uniqueness semantics. |
| Module declarations | A declaration address, not an eighth graph kind; declaration uniqueness is checked in its declaration namespace. |
| Landmark, anchor, dimension, and frame records | Record kind + owner semantic address + role, with context and/or conceptual `claim-id-1` when the owner permits repetitions. |
| Fixture entries | Fixture ID; duplicate IDs and duplicate normalized repository paths are invalid. |
| External implementation-binding path entries | Normalized safe relative path, with mode and raw content as bound entry values; paths are unique. The binding profile is separate from the fixture-manifest canonical domain. |
| Dependency entries | Locator + role + a distinguishing revision identity; the owner must define uniqueness for repeated dependencies. |
| Diagnostic occurrences | The diagnostic profile supplies ordering and occurrence identity/multiplicity; occurrences are not silently deduplicated. |
| Other build arrays | The build-operation owner must declare a typed key and uniqueness/multiplicity rule before activation. |

These examples establish key ownership and failure behaviour without selecting
serialized field names, concrete diagnostic codes, profile IDs, or numeric
constants. A key is not an additional authored field unless its owner
independently requires that field in the source or output contract.

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
binding. That contract also owns the separate implementation-binding
aggregate for code-activating readiness gates; it is not a reuse of the
`ck/v1/fixture-manifest` canonical domain.

Canonical data does not provide signatures, encryption, authenticity, or
content-addressed storage policy. Those are separate decisions if required.

## Activation boundary

Canonicalization and digest profiles are required before durable build,
artifact, or fixture identity activates. Activation must admit the exact
semantic-address and numeric/frame profile revisions they consume, the
canonical profile, domain tags, keyed-collection rules, and representative
byte/digest fixtures in one reviewed contract path. The external
implementation-binding profile is admitted with the relevant readiness
transaction, not folded into the fixture-manifest canonical domain. No
implementation package, schema, or generated artifact is activated by this
Proposed document.

# Body-document contract

Status: Proposed contract; CK-KICK-012 Batch 6 discussion-approved canonical
update; the current CK-KICK-012 Batch 6 Double review is Complete. DR-0002
Revision 8, DR-0008 Revision 8, DR-0011 Revision 4, and DR-0012 Revision 3
remain Proposed with Owner approval Pending and Review Complete. The seven
findings are pending Ben discussion and owner disposition; see the [decision
registry](../../docs/decisions/registry.md). Review evidence is not acceptance
or a clean review.
The CK-KICK-012 Batch 5 review at commit `a282dbabffd83afa4e62577086934d00f98e12c7`
is stale historical evidence. No acceptance is implied.

This document is the canonical specification authority for the authored body
document and the end-to-end source-to-graph operation. It owns source
admission, bootstrap and contract recognition, structural validation,
compatibility, ordered resolution phases, operation status, diagnostics, and
resource behaviour. The [body-graph contract](../body-graph/README.md) owns
the resolved semantic graph after this operation has admitted and recognized
the source.

This is a conceptual contract, not a machine schema. Exact serialized member
names, diagnostic code spellings, numeric budgets, tolerances, canonical axes
and units, rotation/scale/shear policy, source-map encoding, canonical bytes,
and hashing remain deferred. Owner disposition remains pending for the
materially revised decision records.

## Authority and representations

The authoritative input is a source set. Initially it contains exactly one
human-readable body document. Future explicit authored override or imported
source layers may be added only as separate source-set inputs. No normalized
model, resolved graph, generated mesh, runtime package, or external asset
silently becomes authored authority. Every outcome-affecting external authored
dependency is recorded with its exact dependency revision; the meaning and
enforcement of that revision remains a later obligation before such
dependencies activate.

The source document, admitted normalized source model, and successful resolved
snapshot are distinct:

```text
source bytes -> admitted/normalized source model -> resolved graph snapshot
  authored          derived admission view          derived success view
```

Normalization may make comparison and resolution deterministic, but it does
not rewrite authored authority or publish a graph. A rejected or unsupported
input may expose debug information only when it is explicitly marked
non-compilable and non-contractual.

## Initial source encoding

The initial source adapter accepts one strict UTF-8 JSON document. Duplicate
object members are rejected, as are comments, includes, expressions, templates,
and evaluation. JSON Schema Draft 2020-12 is the proposed structural
validation vocabulary; CK semantic resolution remains authoritative for graph
meaning, provenance, and invariants. No schema file or implementation package
is activated by this proposal.

## Bootstrap and contract recognition

Admission and recognition have one required conceptual order. Exact member
spelling for the discriminator is deferred, but its role and ordering are not:

| Order | Required operation | Failure classification |
| --- | --- | --- |
| 1 | Acquire the authoritative source input, enforce raw-byte/profile admission, and validate UTF-8 incrementally. | An unavailable, unreadable, or unacquirable source is `input-failure`; invalid UTF-8 in supplied bytes is `invalid-source`; a configured limit breach is `resource-limit`; loss of implementation trust is `internal-failure`. |
| 2 | Strictly parse one JSON document while detecting duplicate members and enforcing token, nesting, and member guards. | Strict JSON syntax errors and duplicate members, including a duplicate discriminator member, are `invalid-source`, unless resource or internal failure has precedence. |
| 3 | Require a top-level object and exactly one minimal, version-neutral contract discriminator carrying a family and revision. A non-object top level or missing/malformed/duplicate discriminator data is `invalid-source`. | `invalid-source` |
| 4 | Recognize the family and revision before applying a current revision schema. An unknown family or unsupported revision is a well-formed `unsupported` result and stops schema application. | `unsupported` |
| 5 | Select the exact schema for the recognized revision, then apply revision-specific structural validation and unknown-member rules. Unknown core members and malformed recognized-source structure are invalid; extensions follow the extension rule below. | `invalid-source` or `unsupported` for an unsupported required extension |

The discriminator is not inferred from a schema, a filename, a dependency, or
an implementation default. No silent migration, downgrade, or reinterpretation
is permitted. Explicit migration is a separate operation that emits a new
authored source; it does not mutate the input in place. Semantic contract
family and revision are separate from compiler/build identity, configuration,
seed, dependency identity, and artifact identity.

## Core members and extensions

The core vocabulary is closed for a recognized revision. An unknown core
member is a structural/source error; it is not ignored or guessed. Extensions
use an explicit namespaced envelope carrying a namespace, revision, required or
optional indication, and opaque payload. An unsupported required extension is
`unsupported`. An unsupported optional extension is preserved opaquely for
inspection or round-trip purposes and has no core semantic effect. Extension
payloads cannot override core values, relations, invariants, or diagnostics by
an undocumented convention. Extension namespaces and semantic source
namespaces are distinct identifier spaces; any semantic addresses contributed
by a supported extension remain subject to the graph namespace-ownership and
remapping rules.

## Operation phases and result envelope

Every operation produces one authoritative result envelope, including failures
before semantic resolution. The envelope has one top-level status, a
completeness indication, deterministic structured diagnostics, and an optional
resolved snapshot only for complete valid-supported success. A rejected or
unsupported partial graph is explicitly non-compilable and non-contractual
debug data.

After the bootstrap sequence, the conceptual resolution phases are:

1. resource and input admission;
2. syntax, structural-schema, and contract recognition;
3. dependency admission and revision checks;
4. namespace, identity, and reference checks;
5. Part containment and typed-relation checks;
6. unit/frame normalization and value derivation;
7. semantic invariant checks; and
8. successful snapshot publication.

The bootstrap steps are the required sub-order of the first two phases. A
fatal phase blocks dependent later phases. Independent diagnostics in a phase
that was reached may still accumulate. Reached diagnostics are retained when
a later phase is blocked; the envelope marks the result incomplete whenever a
required phase was skipped or diagnostic retention was truncated. A complete
non-success result is possible when all applicable checks ran and established
an invalid or unsupported outcome. Publication is possible only after every
required phase succeeds.

### Closed status algebra and precedence

The only operation statuses are:

| Status | Observable meaning |
| --- | --- |
| `success` | The recognized supported source completed all required checks and a validated snapshot may be present. |
| `input-failure` | The authoritative top-level source was unavailable, unreadable, or could not be acquired as input; this is distinct from errors in supplied source bytes. |
| `invalid-source` | Supplied source bytes have invalid UTF-8, strict JSON syntax errors, duplicate members, a non-object top level, missing/malformed/duplicate discriminator data, recognized-revision schema failure, or source-caused semantic/invariant errors. |
| `unsupported` | The source is sufficiently well formed to identify an unknown family, unsupported revision, unsupported required extension, or recognized-but-unsupported feature/assembly. |
| `dependency-failure` | A required outcome-affecting dependency could not be admitted, loaded, or matched to its declared revision. |
| `resource-limit` | A configured profile limit was breached before the operation could retain a complete trusted result. |
| `internal-failure` | The implementation lost trust in the result, such as through an unexpected invariant failure or surviving environment failure. |

Status selection is deterministic. If implementation trust is lost, the
status is `internal-failure`. Otherwise, if a configured resource exhaustion
means the result cannot be complete—including parser, expansion, work, memory,
or diagnostic-arena exhaustion—the status is `resource-limit`. Otherwise the
earliest fatal phase in the bootstrap/phase order determines the status. Within
that selected earliest fatal phase, `invalid-source` outranks `unsupported` if
both are established; other ordinary status candidates use that phase's
specific mapping in the table above. If no fatal phase occurs and all required
work completes, the status is `success`. Later diagnostics cannot replace an
earlier fatal status, except for the explicit `internal-failure` and configured
`resource-limit` precedence just stated. The primary is the first diagnostic
that establishes the final status under this same normative ordering, not merely
the first diagnostic encountered or retained.

The three Stage 1 semantic fixture outcomes are not this status algebra. They
apply only after a recognized, admitted input has reached semantic evaluation:
`valid-supported`, `semantically invalid`, or
`well-formed-but-unsupported`. Parser, discriminator, dependency, configured
resource, and internal failures are separate operation-fixture outcomes and
are not relabelled as one of those three semantic outcomes.

## Diagnostics

Every non-success result has a primary diagnostic whose category maps to the
top-level status. A successful result has no failure primary. The primary is
the first logical diagnostic establishing the selected status under the
normative phase/status/diagnostic ordering; the exact code vocabulary is
deferred. Human-readable text is explanatory and never a compatibility or
ordering key.

Diagnostics are bounded by a profile-selected arena. Ordinary diagnostics are
retained as they are reached until the ordinary capacity is exhausted; reached
earlier diagnostics are not silently replaced by later diagnostics. Primary
selection considers the logical diagnostics in normative order, and reserved
primary capacity preserves the minimal matching candidate even when ordinary
truncation drops other diagnostics. The arena also reserves capacity for a
diagnostic-truncation or resource report. If ordinary capacity is exhausted,
the envelope records the truncation and marks diagnostics incomplete. If arena
exhaustion changes the final status to `resource-limit`, the reserved
resource/truncation diagnostic is the primary and therefore satisfies the
final-status-primary rule, unless `internal-failure` has precedence; the
reserved primary capacity still preserves the minimal matching candidate for
the final status selected under the precedence rules.

The deterministic ordering key is, in order: phase; severity/category;
normalized source path and offset; diagnostic code; and semantic address.
Missing path, offset, code, or address values use stable conceptual sentinels;
their serialized spellings remain deferred. Ties use no human text, timestamps,
allocation order, or incidental object order. The implementation may retain
additional diagnostics only when doing so respects the same bound and key.

## Resource and hostile-input contract

Every implementation profile is finite. Exact thresholds and accounting units
are profile-specific and deferred, but enforcement points are part of this
contract:

- raw source bytes and aggregate admitted bytes are charged before unbounded
  buffering;
- UTF-8 and JSON tokens are processed incrementally, with string and number
  token lengths checked before string materialization or numeric conversion;
- nesting depth, object/array member counts, and token counts are charged as
  the parser encounters them;
- each dependency has a bounded byte/work budget and the operation has an
  aggregate dependency budget;
- graph entities, references, module expansion, relation work, and other
  resolver work are charged before allocation or expansion, so rejected work
  cannot first consume an unbounded structure; and
- diagnostic storage and aggregate memory/work remain guarded after parsing,
  because later phases can exceed what source size alone predicts.

Configured breaches report `resource-limit` through the same envelope and
block dependent work. Deterministic work units are preferred to wall-clock
timeouts; a profile may define a time guard only as an explicit later profile
choice. A true operating-system or process out-of-memory termination is
outside this guarantee; if the process survives and can no longer trust its
result, it reports `internal-failure`.

## Graph handoff and fixture boundary

After successful admission, the [body-graph contract](../body-graph/README.md)
owns Part containment, typed relations, Attachment placement, canonical frame
records, provenance, and semantic invariants. This document does not choose a
bone hierarchy, solver, limits, runtime pose, mesh, or surface representation.

Representative fixtures should cover valid documents, invalid UTF-8/JSON,
duplicate members, non-object top levels, discriminator recognition failures,
unknown core members,
unsupported family/revision, unsupported required and optional extensions,
dependency failures, resource-limit and diagnostic truncation outcomes,
internal-failure handling where testable, and deterministic multi-diagnostic
ordering. The semantic Stage 1 taxonomy is exercised only by admitted,
recognized inputs. Exact fixture files, codes, and numeric profiles remain
unactivated until an implementation consumes this contract.

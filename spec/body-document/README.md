# Body-document contract

Status: Proposed conceptual contract; CK-KICK-012 Batch 13/14 discussion-approved
canonical update. DR-0002 Revision 11 and DR-0008 Revision 11 remain Proposed
with Owner approval Pending and Review Complete. Current Batch 13/14 material is
recorded in DR-0006 Revision 12, DR-0011 Revision 15, DR-0012 Revision 14, and
DR-0013 Revision 12; each remains Proposed with Owner approval Pending and
Review Pending after material technical-review resolution edits. Batch 11/12/13 review artifacts are stale for those materially
revised records and remain evidence only; fresh successor-target review is
pending. This Batch 13/14 update carries the
C1 keyed-collection, C3 implementation-binding, C4 diagnostic/bootstrap, and
Batch 13 resolution directions as Proposed cross-spec contracts; no acceptance, schema, parser,
resolver, implementation binding, or readiness gate activates. See the
[decision registry](../../docs/decisions/registry.md) and [project review
state](../../docs/project/status.md#current-review-and-future-activation-obligations).
Exact comparator arithmetic and adapter algorithms remain owned by the numeric
and frame profile; this document only cross-links their use.

This document is the canonical specification authority for the authored body
document and the end-to-end source-to-graph operation. It owns source
admission, bootstrap and contract recognition, structural validation,
compatibility, ordered resolution phases, operation status, diagnostics, and
resource behaviour. The [body-graph contract](../body-graph/README.md) owns
the resolved semantic graph after this operation has admitted and recognized
the source.

This is a conceptual contract, not a machine schema. Exact serialized member
names, diagnostic code spellings, numeric budgets, and source-map encoding
remain deferred. The [semantic-address profile](../semantic-address/README.md),
[numeric and frame profile](../numeric-frame-profile/README.md),
[canonical-data profile](../canonical-data/README.md), and
[diagnostic profile](../diagnostics/README.md) own their respective exact
machine-facing rules. Those Proposed profiles are activation-gated and do not
activate a parser or schema by themselves. Owner disposition remains pending
for the materially revised decision records.

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

The normalized semantic model also declares each module instance without
adding an eighth identity-bearing graph concept. A declaration has a stable
authored module-instance declaration address and records the instantiated
module, non-embodied root-role/template reference, root Part when present,
module-instance anchor/provenance, presence and optionality, and whether
Attachment composition is required. An absent optional declaration emits or
reserves no Part, no graph relation may target its non-embodied root role, and
it participates in declaration uniqueness rather than the Part namespace. If
later present, its Part identity derives deterministically from the
module-instance anchor and root role. Optional absence is distinct from a
present-but-unattached root; a present Attachment-required root with no
incoming active Attachment is invalid. Nested instances require distinct
Socket instances and retain containment and source provenance.

## Conceptual document shape

The proposed top-level shape is conceptual and has no machine schema yet:

```text
document = contract, source, basis, profiles, body, extensions
```

`contract` owns the version-neutral contract family and revision used for
recognition. `source` identifies authored source/provenance and outcome-
affecting dependencies. `basis` declares the source coordinate basis.
`profiles` references semantic numeric-domain profiles; operational resource and
diagnostic profiles belong to the operation or fixture context, not to source
semantics. `body` contains typed collections for `modules`, `parts`, `joints`,
`sockets`, `attachments`, `landmarks`, `dimensions`, `frames`, `regions`,
`capabilities`, and `fields`. `extensions` is the explicit namespaced
extension envelope described below.

Each collection contains explicit typed records and stable references. There is
no generic union or untyped graph escape hatch. Array order is non-semantic;
canonical ordering of an unordered collection is owned by the
[canonical-data profile](../canonical-data/README.md), which requires the
owner-declared typed total key and uniqueness/multiplicity rule. Core
collections are present even when empty, and the recognized core vocabulary is
closed. An explicitly permitted empty collection is the only initial omission
for a core collection. This source contract does not redefine canonical key
arithmetic or serialized field spelling.

Authored claims use conceptual versioned `claim-id-1`: canonical target, closed
claim kind, typed source-document/namespace identity, stable authored record
address, typed property role, and explicit authored claim key or absence. It has
the wire-independent order owned by the semantic-address profile and canonical
unordered pairs are
`(min_id, max_id)`. Claim identity never comes from a raw JSON pointer, array
index, source traversal, allocation order, or object serialization. A raw
pointer remains diagnostic provenance only; the activated schema must supply
stable record address, typed property role, and multiplicity keys. Body-graph
owns claim grouping, all-pairs satisfiability, representative selection, and
provenance retention; the numeric/frame profile owns comparison formulas and
evaluation semantics. The wire-independent claim-ID comparator is defined by
the [semantic-address profile](../semantic-address/README.md): its exact
six-field component precedence is canonical target, claim kind, source-document
namespace, authored record address, typed property role, and explicit claim key
or absent; canonical-target address order, profile-defined semantic ranks for
closed claim kind and typed property role, normalized identifier Unicode-scalar
lexical order for typed namespace/address segments, structured
prefix-before-extension ordering, and absent-before-present claim-key ordering.
The claim-kind and typed-property-role rank tables are mandatory, versioned
activation inputs, complete and injective over each admitted closed set;
missing, duplicate, or unknown kind, role, or rank entries fail activation. No
canonical claim ordering, digest, or resolver activation occurs before both
tables exist, and wire enum spelling may not supply the order.

## Basis, profiles, and frame roles

Every source declares a required basis consisting of length unit, handedness,
up, and forward. Measurements and transforms name their owner, semantic role,
and frame/context. Stage 1 roles are owner-specific: a Part has a
local/reference frame, a Joint has proximal and distal frames, and a Socket has
one intrinsic interface frame. Host and mating are contextual endpoint roles
on an Attachment that references Sockets; they are not intrinsic Socket frame
roles. Resolved world/reference and runtime-pose frames remain distinct
downstream contexts. A source profile initially references only the semantic
numeric-domain profile. Operational resource and diagnostic profiles are
selected by the operation or fixture admission context. No per-value unit
override is permitted initially.

Readiness 2 validates document shape, typed records, references, and owner/role
addressing, including the structural rigid-transform carrier defined by the
[numeric and frame profile](../numeric-frame-profile/README.md): exactly three
translation components and exactly four quaternion components in explicit
`xyzw` order, with no scale or shear fields. Readiness 3 is a separate
successor transaction that admits the profile's canonical basis, finite-number
and normalization semantics, admissible ranges, conditioning rules,
tolerances, and expected graph snapshots. It does not reselect the Readiness 2
carrier.

## Omission and deterministic defaults

Identity, containment, module presence, basis, and grammar-required values are
explicit. Omission is legal only when an exact contract- or profile-owned
deterministic default applies, that rule has a stable rule identity, and exactly
one applicable owner exists. A resolved value records `defaulted` provenance and
the default-rule identity. There is no null-as-missing convention, implicit
zero, neighbour inference, or hidden equation. Core typed collections are
always present; any permitted omission is explicitly an empty collection under
the contract.

## Initial source encoding

The initial source adapter accepts one strict UTF-8 JSON document. Duplicate
object members are rejected, as are comments, includes, expressions, templates,
and evaluation. JSON Schema Draft 2020-12 is the proposed structural
validation vocabulary; CK semantic resolution remains authoritative for graph
meaning, provenance, and invariants. No schema file or implementation package
is activated by this proposal.

### Numeric admission and source consequences

After strict JSON syntax, number-token, and resource checks, each JSON number
is interpreted as an exact signed decimal rational and converted directly to
binary64 with correctly rounded round-to-nearest, ties-to-even. The conversion
is owned by the [numeric and frame profile](../numeric-frame-profile/README.md):
source admission must not use a host float intermediate, locale, ambient
rounding mode, or implementation-dependent precision. Lexical and exact-rational
work is charged before unbounded materialization.

A finite conversion is admitted, including a finite nonzero subnormal. An
overflow to infinity is `invalid-source`, as is a nonzero exact rational that
rounds to signed zero. Canonical operations must forbid FTZ/DAZ. A lexical
negative zero is valid when its exact rational is zero, then normalizes to
`+0` in the normalized source model and resolved graph; the raw source bytes
remain unchanged. Every semantic numeric-producing stage additionally
normalizes produced zero to `+0` after admission/conversion, composition,
inversion, quaternion normalization/sign, tuple formation, adapter conversion,
and narrowing, before comparison or serialization. A permitted nonzero-to-zero
narrowing emits `+0`; raw lexical `-0` remains distinct only in raw-source
identity. Precision is not rejected by an arbitrary semantic digit
cutoff: values within the declared lexical/resource bound are converted, and
a bound breach is `resource-limit` when it prevents trusted processing.
Alternate decimal spellings can therefore share one normalized binary64 value
while retaining distinct source bytes. Conversion/rounding failures or
non-finite results are source admission failures, not silently repaired values.

Required boundary fixtures cover ordinary inexact decimal `0.1`, exact values,
halfway/tie cases, the maximum-finite boundary and overflow, the smallest
subnormal and underflow-to-zero, excessive precision at the lexical/resource
boundary, lexical signed zero, and alternate decimal spellings. The fixture
manifest owns their expected outcomes and profile bindings; exact profile IDs
and resource constants remain activation-gated.

## Bootstrap and contract recognition

Admission and recognition have one required conceptual order. Exact member
spelling for the discriminator is deferred, but its role and ordering are not:

| Order | Required operation | Failure classification |
| --- | --- | --- |
| 1 | Acquire the complete authoritative source input, enforce raw-byte/profile admission, and validate UTF-8 incrementally. | An unavailable, unreadable, or incomplete acquisition is `input-failure`; invalid UTF-8 in completely supplied bytes is `invalid-source`; a configured limit breach that prevents required processing or trusted completion is `resource-limit`; loss of implementation trust is `internal-failure`. |
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

Diagnostic registry/profile negotiation is not a new bootstrap phase. The
[diagnostic profile](../diagnostics/README.md) always supplies a tiny
unnegotiated bootstrap registry/profile. If a required registry or profile is
unknown, this existing admission/contract-recognition phase returns top-level
`unsupported` with the deterministic bootstrap primary, bootstrap effective
IDs, and bounded opaque requested IDs marked `required=true`; it never emits
under the unknown profile or silently downgrades. The exact bootstrap code
spelling remains fixture-gated only while its conceptual identity stays
unambiguous and non-recursive.

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
completeness indication, deterministic structured diagnostics, and a resolved
snapshot when the operation contract requires one. A successful `resolve`
operation requires a complete validated in-memory snapshot; an operation such
as `validate` may intentionally omit the snapshot only when its own contract
permits that result. A rejected or unsupported partial graph is explicitly
non-compilable and non-contractual debug data.

After the bootstrap sequence, the conceptual resolution phases are:

1. resource and input admission;
2. syntax, structural-schema, and contract recognition;
3. dependency admission and revision checks;
4. namespace, identity, and reference checks;
5. Part containment and typed-relation checks;
6. unit/frame normalization and value derivation;
7. semantic invariant checks; and
8. in-memory resolved-snapshot finalization and handoff.

The bootstrap steps are the required sub-order of the first two phases. A
fatal phase blocks dependent later phases. Independent diagnostics in a phase
that was reached may still accumulate. Reached diagnostics are retained when
a later phase is blocked. Processing completeness is incomplete when a
required phase is skipped; diagnostic completeness is independently incomplete
only when diagnostic retention is truncated. Intentionally blocked later phases
do not by themselves make retained reached-phase diagnostics incomplete. A
complete non-success result is possible when all applicable checks ran and
established an invalid or unsupported outcome. Resolved-snapshot finalization
is possible only after every required resolver phase succeeds. This phase is
an in-memory handoff, not filesystem serialization or artifact publication;
the [build-operation contract](../build-operation/README.md) owns those later
derived-output steps.

### Closed status algebra and precedence

The only operation statuses are:

| Status | Observable meaning |
| --- | --- |
| `success` | The recognized supported source completed all required checks; a validated snapshot is present when required by the operation contract, and `resolve` success always includes it. |
| `input-failure` | The authoritative top-level source was unavailable, unreadable, or could not be acquired as input; this is distinct from errors in supplied source bytes. |
| `invalid-source` | Supplied source bytes have invalid UTF-8, strict JSON syntax errors, duplicate members, a non-object top level, missing/malformed/duplicate discriminator data, recognized-revision schema failure, or source-caused semantic/invariant errors. |
| `unsupported` | The source is sufficiently well formed to identify an unknown family, unsupported revision, unsupported required extension, or recognized-but-unsupported feature/assembly. |
| `dependency-failure` | A required outcome-affecting dependency could not be admitted, loaded, or matched to its declared revision. |
| `resource-limit` | A configured profile limit prevented required processing or trusted completion; ordinary diagnostic truncation alone is not this status. |
| `internal-failure` | The implementation lost trust in the result, such as through an unexpected invariant failure or surviving environment failure. |

Status selection is deterministic and total. Acquisition must obtain the
complete authoritative byte input before a supplied source can be classified as
`invalid-source`; an unavailable, unreadable, or incomplete acquisition is
`input-failure`. If implementation trust is lost, the status is
`internal-failure`. Otherwise, a configured resource breach is
`resource-limit` only when it prevents required processing or trusted result
completion. Ordinary diagnostic capping or truncation while required processing
continues and produces a trusted result does not become `resource-limit`.
Otherwise the earliest phase unable to produce its required output determines
the status. In parse and semantic phases, `invalid-source` outranks
`unsupported` when both are established; dependency acquisition/read/verify/
resolve failure maps to `dependency-failure`, while complete dependency content
uses the ordinary parse/semantic mapping. If no fatal phase occurs and all
required work completes, the status is `success`. A successful `resolve`
operation must include the finalized in-memory snapshot; an operation whose
contract permits validation-only success may omit it. All mandatory independent
checks capable of changing status or primary run unless resource or trust
interruption prevents them; optional/advisory checks cannot change status or
primary. In a mixed dependency phase, `dependency-failure` outranks
`invalid-source`, which outranks `unsupported`. The primary is the first
diagnostic establishing the final status under the same normative ordering, not
merely the first encountered or retained.

Processing completeness and diagnostic completeness are independently
observable conceptual fields (serialized names remain deferred). Processing is
complete when all work applicable to establishing and trusting the selected
outcome ran; normatively blocked later phases are inapplicable. It is
incomplete only when acquisition, dependency, resource, environment, or
internal interruption prevents required outcome processing. Diagnostic
completeness is complete when all applicable profile-required diagnostics were
retained. Truncation makes it incomplete, but is not `resource-limit` unless it
prevented required processing or trusted completion. Optional checks cannot
change status or primary selection.

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

The [diagnostic registry and profile](../diagnostics/README.md) is the sole
owner of registry definitions, the nine domains, stable classes, occurrence
identity/multiplicity, selection profiles, ordering, and compatibility; this
contract owns only operation status and precedence. Diagnostics are bounded by
a profile-selected arena. Ordinary diagnostics are
retained as reached until ordinary capacity is exhausted; earlier diagnostics
are not silently replaced. Primary selection considers logical diagnostics in
normative order, and reserved primary capacity preserves the minimal matching
candidate despite ordinary truncation. If ordinary capacity is exhausted, the
envelope records truncation and marks diagnostic completeness incomplete, but
this is not `resource-limit` when required processing and trusted completion
continue. If arena exhaustion itself prevents trusted completion and establishes
`resource-limit`, the reserved resource/truncation diagnostic is the primary
unless `internal-failure` has precedence.

The diagnostic profile's deterministic ordering key is, in order: phase;
severity/category; normalized source path and offset; diagnostic code; semantic
address; and the profile-defined occurrence identity/multiplicity key. Missing
path, offset, code, or address values use stable conceptual sentinels; the
registry/profile defines their machine treatment. Ties use no human text,
timestamps, source array index, allocation order, or incidental object order.
The implementation may retain additional diagnostics only when doing so
respects the same bound, occurrence semantics, and key.

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

Configured breaches that prevent required processing or trusted completion
report `resource-limit` through the same envelope and block dependent work. A
diagnostic-cap breach that merely truncates diagnostics while required
processing/trusted completion continue reports incomplete diagnostic
completeness instead. Deterministic work units are preferred to wall-clock
timeouts; a profile may define a time guard only as an explicit later profile
choice. A true operating-system or process out-of-memory termination is
outside this guarantee; if the process survives and can no longer trust its
result, it reports `internal-failure`.

## Graph handoff and fixture boundary

After successful admission, the [body-graph contract](../body-graph/README.md)
owns Part containment, typed relations, Attachment placement, canonical frame
records, provenance, and semantic invariants. This document does not choose a
bone hierarchy, solver, limits, runtime pose, mesh, or surface representation.
The resolver's successful snapshot is finalized and handed off in memory; the
[build-operation contract](../build-operation/README.md) owns any later
serialization, staging, and publication of that snapshot or other derived
outputs.

Representative fixtures should cover valid documents, invalid UTF-8/JSON,
duplicate members, non-object top levels, discriminator recognition failures,
unknown core members,
unsupported family/revision, unsupported required and optional extensions,
dependency failures, resource-limit and diagnostic truncation outcomes,
internal-failure handling where testable, and deterministic multi-diagnostic
ordering. The semantic Stage 1 taxonomy is exercised only by admitted,
 recognized inputs. The [fixture-manifest and admission contract](../fixture-manifest/README.md)
owns the manifest payload, separate fixture-payload content binding, external
implementation binding for code-activating readiness gates, preflight,
expected-outcome fields, and Readiness 2/3 corpus admission. Its implementation
binding covers only the relevant parser/bootstrap or resolver closure and is
distinct from the fixture-manifest canonical digest domain. Post-merge and
immediately pre-ledger recomputation must match both bindings or activation is
blocked and a successor is required. Exact fixture files, codes, and numeric
profiles remain unactivated until that admission and the relevant readiness
gate are complete.

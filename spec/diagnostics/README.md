# Diagnostic registry and profile

Status: Proposed canonical specification; transaction-local `ck.diagnostic.r2`
identifiers and codes are used by the active Readiness 2 parser/preflight
transaction

Batch 13/14 resolves the diagnostic-domain and bootstrap-compatibility direction
as Proposed material. Current successor material is recorded in DR-0006 Revision
12, DR-0011 Revision 15, and DR-0012 Revision 14; these remain Proposed with
Owner approval Pending and Review Complete after the current Double review at
exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. DR-0013 Revision 12 is
Accepted, with Owner approval Approved by Ben and Review Complete at that exact
target, decided 2026-08-13. The earlier-predecessor review at
`763cff22d10f6491a05a28312a25250704543dcf` and immediate-predecessor review at
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` are stale, with their findings
corrected in these revisions. The 9c governance pass corrected two mechanical
history-label issues and its technical pass found no findings / Ready for PR at
High confidence. Review Complete is evidence only. The broader diagnostic
registry/profile specification remains Proposed. The active Readiness 2
parser/preflight transaction uses transaction-local `ck.diagnostic.r2`
identifiers and codes; it does not admit this owner specification or future
registry/profile material.

This document is the sole canonical owner of diagnostic registry definitions,
the initial diagnostic domains and stable classes, diagnostic occurrences,
diagnostic-selection profiles, ordering, and diagnostic compatibility. The
[body-document contract](../body-document/README.md) owns the operation
envelope and status/precedence consequences and references this profile. The
[build-operation contract](../build-operation/README.md) owns derived-output
and publication status mappings and references this profile. Resource profiles
are separate operational inputs and are not diagnostic registries or source
semantic profiles. This document does not invent a universal catalogue of
every future error.

## Registry, profiles, and occurrences

The registry is a versioned machine-readable definition set. Each registered
diagnostic code has a stable conceptual code identity, domain/class, applicable
phase, default severity, and compatibility/revision identity. The active
parser/preflight transaction uses the transaction-local `ck.diagnostic.r2`
profile identifier and its exact ten-code vocabulary:

- `ck.resource.source-bytes`
- `ck.resource.json-work`
- `ck.source.invalid-json`
- `ck.source.duplicate-member`
- `ck.contract.invalid-discriminator`
- `ck.contract.unsupported-family`
- `ck.contract.unsupported-revision`
- `ck.source.schema`
- `ck.extension.unsupported-required`
- `ck.internal.schema`

These transaction-local spellings are frozen for the admitted Readiness 2
transaction; they do not admit the broader registry/profile specification.
Future diagnostic domains and codes are not implied to be implemented. The initial registry has
exactly these nine domains:

- `source-admission` — acquisition, UTF-8, strict JSON, bootstrap, and schema;
- `dependency` — authored dependency acquisition and verification;
- `semantic-identity` — namespace ownership, address, reference, and remap;
- `graph-structure` — containment, relation, endpoint, and cardinality;
- `frame-numeric` — basis, transform carrier, numeric, and comparison rules;
- `resource` — configured resource admission, accounting, and exhaustion;
- `execution-trust` — resolver-invariant, environment/internal trust,
  worker-protocol, coordinator, reporter, and publisher trust causes as
  applicable;
- `publication` — output, staging, manifest, collision, and publication; and
- `inspection` — committed-artifact read and expectation checks.

`resolver-invariant`, environment/internal trust, and worker/coordinator/
reporter/publisher causes are classes or causal details under
`execution-trust`, not additional domains. Resource profiles remain separate
operational inputs even when a diagnostic occurrence records a resource-profile
reference. These domains are intentionally a small initial boundary, not a
large frozen code table beyond this candidate. The transaction-local ten-code
set is implemented only in the candidate parser/preflight path.

A diagnostic occurrence is data separate from its registry definition. It
contains the code and registry revision, phase, severity, optional normalized
source location, optional semantic address, and typed details. Human-readable
text is optional presentation data. It is never a compatibility key, ordering
key, canonical-data input, or substitute for a registered code.

Occurrences have profile-defined occurrence identity and multiplicity. The
profile must state when two occurrences are distinct (for example by stable
source identity/path, semantic address, causal reference, claim/occurrence ID,
or another typed identity) and when repetition is a legitimate multiset/count.
It must never silently deduplicate merely because two occurrences have equal
messages or equal serialized details.

For the transaction-local Readiness 2 `ck.diagnostic.r2` profile, a structural-schema
occurrence (`ck.source.schema`) has the exact identity tuple
`(instance_path, schema_path, error_kind)`. `instance_path` and `schema_path`
are normalized JSON Pointer strings (the empty string denotes the document
root), and `error_kind` is the validator's registered keyword/class spelling.
The tuple is compared as machine strings in that order; the human-readable
message is not part of identity. Equal tuples are one logical occurrence and
may be ignored as duplicate reports, while different tuples remain distinct
even when their messages or serialized details match. No source array index,
allocation order, or validator emission order is an identity component.

A diagnostic profile is a versioned selection of registry revision, enabled
domains/codes, severity and ordering rules, retention policy, and primary-
diagnostic policy. A resource profile is separate: it owns limits and
accounting, not diagnostic meaning. A diagnostic occurrence may refer to a
resource profile outcome, but the profile IDs must remain distinct. An unknown
required diagnostic or profile revision is `unsupported`; implementations do
not silently downgrade to a different registry or profile.

### Bootstrap compatibility

One tiny, unnegotiated bootstrap registry/profile is always supported. It is
used only to report inability to negotiate the requested diagnostic registry
or selection profile; it is not an additional operation phase. Bootstrap
compatibility is conceptual and stable even while future registry codes and
field spellings remain Proposed, provided its identity is
unambiguous and non-recursive.

When a required diagnostic registry or profile is unknown, the top-level
operation status is `unsupported`. The result uses the bootstrap effective
registry/profile IDs, selects the deterministic bootstrap primary diagnostic,
and carries the requested registry/profile IDs as bounded opaque values with
`required=true`. It never emits the occurrence under the unknown requested
profile, silently downgrades to a known ordinary profile, or adds a bootstrap
phase. The existing source-admission/contract-recognition phase owns this
failure and its status/precedence remains owned by the body-document contract.
The bootstrap occurrence itself must not require the unknown profile or
registry to interpret its identity.

## Determinism and selection

The candidate retention algorithm has two bounded areas: ordinary diagnostic
retention and one reserved primary slot. Each new logical occurrence is first
eligible for the reserved primary, which independently keeps the minimum
occurrence under the profile's normative ordering key. Ordinary diagnostics
are then retained in reached order until their configured capacity is full;
later occurrences do not evict or replace already retained ordinary entries.
Consequently, the reserved primary may be absent from the ordinary retained
list when a later occurrence is normatively smaller. A zero ordinary capacity
still records that a diagnostic occurred, retains the reserved primary, marks
diagnostic completeness incomplete, and cannot convert an invalid source into
success. Truncation is reported only through diagnostic completeness unless
the separate operation contract determines that required trusted processing
could not continue.

The active diagnostic profile defines a total deterministic order over retained
occurrences. The conceptual order is reached phase, severity/category,
normalized source path and offset, registered code, semantic address, and the
profile-defined occurrence identity/multiplicity key where needed. Human text,
allocation order, thread scheduling, and object-member order do not affect
this order. Missing optional location/address values use profile-defined
conceptual sentinels rather than implementation-dependent null ordering. A
diagnostic profile may not order or deduplicate by source array index.

The operation envelope's top-level status remains separate from diagnostics.
Every non-success result has one primary diagnostic selected by the owning
status/precedence contract; success has no failure primary. A profile may
retain additional occurrences subject to its bounded resource policy. Ordinary
retention truncation marks diagnostic completeness incomplete but does not by
itself change the operation status. If retention/resource exhaustion prevents
required trusted processing, the operation's resource-limit rule applies.

Diagnostic selection never changes a source outcome, repairs invalid input,
or converts a worker-trust loss into trusted output. A publication or
inspection status may add a causal reference to an earlier resolver/worker
occurrence while retaining one authoritative envelope. The operation contracts
own only their status/precedence and output mapping; they do not redefine the
registry domains or compatibility rules here.

## Activation and fixtures

The transaction-local code set and `ck.diagnostic.r2` profile identifier are
documented and used by the active Readiness 2 parser/preflight transaction.
They are frozen only for that transaction, while the broader registry/profile
specification and future registry revisions, domains, and publication/
inspection codes remain separate Proposed material and are not claimed
implemented by this candidate.

The fixture suite must cover deterministic multi-diagnostic ordering, primary
selection, ordinary retention truncation, resource-limit retention failure,
unknown required profile revision, and causal publication/worker observations.
The [fixture-manifest contract](../fixture-manifest/README.md) owns their
payload and admission; the operation contracts own expected status semantics.

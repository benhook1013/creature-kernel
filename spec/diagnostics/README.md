# Diagnostic registry and profile

Status: Proposed canonical specification; exact codes are fixture-gated

This document owns the separation between diagnostic registry definitions,
diagnostic occurrences, diagnostic-selection profiles, resource profiles, and
operation status. The [body-document contract](../body-document/README.md) owns
the operation envelope and status precedence. The [build-operation contract](../build-operation/README.md)
owns derived-output/publication mappings. This document does not replace
those status contracts or invent a universal catalogue of every future error.

## Registry, profiles, and occurrences

The registry is a versioned machine-readable definition set. Each registered
diagnostic code has a stable code, domain/class, applicable phase, default
severity, and compatibility/revision identity. The initial registry domains
are:

- `source-admission` — acquisition, UTF-8, strict JSON, bootstrap, and schema;
- `dependency` — authored dependency acquisition and verification;
- `semantic-identity` — namespace ownership, address, reference, and remap;
- `graph-structure` — containment, relation, endpoint, and cardinality;
- `frame-numeric` — basis, transform carrier, numeric, and comparison rules;
- `resolver-invariant` — admissible-input implementation invariant failure;
- `publication` — output, staging, manifest, collision, and publication; and
- `inspection` — committed-artifact read and expectation checks.

Worker/protocol diagnostics remain an operation/platform domain owned by the
build-operation contract; they may use the same occurrence envelope and
registry revision. These domains are intentionally a small initial boundary,
not a large frozen code table. Exact code strings become frozen only in the
admitted fixture transaction that first consumes them.

A diagnostic occurrence is data separate from its registry definition. It
contains the code and registry revision, phase, severity, optional normalized
source location, optional semantic address, and typed details. Human-readable
text is optional presentation data. It is never a compatibility key, ordering
key, canonical-data input, or substitute for a registered code.

A diagnostic profile is a versioned selection of registry revision, enabled
domains/codes, severity and ordering rules, retention policy, and primary-
diagnostic policy. A resource profile is separate: it owns limits and
accounting, not diagnostic meaning. A diagnostic occurrence may refer to a
resource profile outcome, but the profile IDs must remain distinct. An unknown
required diagnostic or profile revision is `unsupported`; implementations do
not silently downgrade to a different registry or profile.

## Determinism and selection

The active diagnostic profile defines a total deterministic order over retained
occurrences. The conceptual order is reached phase, severity/category,
normalized source path and offset, registered code, and semantic address,
followed by a stable typed-details key where needed. Human text, allocation
order, thread scheduling, and object-member order do not affect this order.
Missing optional location/address values use profile-defined conceptual
sentinels rather than implementation-dependent null ordering.

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
occurrence while retaining one authoritative envelope.

## Activation and fixtures

The exact initial code set, registry revision, diagnostic-profile fields,
resource-profile references, and primary-code expectations are admitted
together with the first parser/graph/publication fixture transaction. Until
then, documents may name the domains and profile boundary but must not claim
an exact code vocabulary or compatibility promise.

The fixture suite must cover deterministic multi-diagnostic ordering, primary
selection, ordinary retention truncation, resource-limit retention failure,
unknown required profile revision, and causal publication/worker observations.
The [fixture-manifest contract](../fixture-manifest/README.md) owns their
payload and admission; the operation contracts own expected status semantics.

# Body-document contract

Status: Proposed contract; CK-KICK-012 Batch 4 discussion-approved and current
Double review Complete, with six consolidated blockers pending Ben discussion
and Ben's owner disposition

This document is the provisional specification authority for the authored body
document and the end-to-end source-to-graph operation: source encoding,
structural shape, contract recognition, extensions, compatibility, admission,
ordered resolution phases, and diagnostics. It does not make a decision record
the contract. The [body-graph
contract](../body-graph/README.md) owns the resolved semantic graph produced
after this document has been admitted and structurally validated.

The proposal is intentionally descriptive rather than a machine schema. It
does not choose serialized field names, numeric ranges, tolerances, a source
map encoding, canonical axes or units, rotation/scale/shear policy, or a
canonicalization and hashing algorithm. Those details remain subject to the
current review and later owner disposition. The cross-cutting encoding/
resolution proposal is [DR-0012: initial body-document encoding,
resolution, and compatibility](../../docs/decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
which remains Proposed pending owner disposition; six consolidated blockers
remain pending Ben discussion.

## Authority and source boundary

The authoritative input is a source set. Initially it contains one
human-readable body document. Future explicit override or imported source
layers may become authored inputs, but no generated graph, mesh, runtime
package, or external asset silently becomes authored authority. Every
outcome-affecting external authored dependency is recorded with its exact
dependency revision; the meaning and enforcement of that revision remains a
nonblocking obligation before external authored dependencies activate.

The source document, an admitted normalized source model, and a successful
resolved graph snapshot are distinct representations:

```text
source text -> admitted/normalized source model -> resolved graph snapshot
   authored             derived admission view             derived success view
```

Normalization may make comparison and resolution deterministic, but it does
not rewrite authored authority or publish a graph. A rejected or unsupported
input may expose debug information only when that information is explicitly
marked non-compilable and non-contractual.

## Initial source encoding

The initial source adapter accepts exactly one strict UTF-8 JSON document. It
rejects duplicate object keys, comments, includes, expressions, templates, and
evaluation. Multiple source syntaxes are not part of the initial contract. A
future restricted YAML adapter is possible only as
an explicit adapter that produces the same admitted source model; it does not
silently add a second semantic contract.

JSON Schema Draft 2020-12 is the proposed structural-validation vocabulary.
Structural validation checks the document's shape and declared contract
before semantic resolution. No JSON Schema file, generated validator, or
implementation package is activated by this proposal.

## Contract recognition and compatibility

An input is admitted only when its semantic contract family and revision are
recognized exactly by the implementation profile. The resolver does not
silently migrate, downgrade, or reinterpret an unrecognized revision. An
explicit migration is a separate authored source that declares its source and
target contracts and can itself be rejected; it does not mutate the original
source in place.

Semantic contract identity is separate from compiler/build identity,
configuration, seed, dependency identity, and artifact identity. Semantic
equivalence is judged from the durable identities, relations, frames, values,
provenance, and outcome of the resolved result—not source text ordering,
whitespace, or incidental output topology. A deterministic debug rendering of
JSON may be useful for inspection, but canonical bytes and hashing are not
defined here.

## Core members and extensions

Core vocabulary is closed for the recognized contract revision. An unknown
core member is a structural/contract error; it is not ignored or guessed.
Extensions use an explicit namespaced envelope with namespace, revision,
required indication, and opaque payload. An unsupported
required extension makes the input unsupported. An unsupported optional
extension is preserved opaquely for round-trip or inspection purposes and has
no core semantic effect. Extension payloads cannot override core values,
relations, invariants, or diagnostics through an undocumented convention.

Extension namespaces and semantic source namespaces are distinct identifier
spaces. Declaring an extension namespace does not claim a semantic source
namespace. If a supported extension contributes semantic addresses, those
addresses remain subject to the body-graph rule that each source namespace has
one owner and a colliding import requires a complete authored deterministic
remap. Exact extension, import, and remap syntax remains deferred.

## Admission, validation, and diagnostics

Source processing is staged and deterministic. Its phases are:

1. resource and input admission;
2. syntax, structural-schema, and contract recognition;
3. dependency admission and revision checks;
4. namespace, identity, and reference checks;
5. ownership and typed-relation checks;
6. unit/frame normalization and value derivation;
7. semantic invariant checks; and
8. success publication.

The operation-result envelope is authoritative for every phase and diagnostic.
A fatal phase blocks dependent phases, while independent diagnostics in one
phase may accumulate in deterministic order. Required unresolved or
ambiguous values cannot publish success. Stable machine diagnostic fields
identify a code, category, phase, path, and zero or more affected semantic
addresses, while diagnostic ordering is deterministic. Human-readable messages
are explanatory and are not compatibility keys. Exact serialized diagnostic
field spelling, codes, and ordering tie-breakers remain to be specified.

## Resource profile

Untrusted input is evaluated under a finite implementation-profile resource
budget. The profile records bounds for source and aggregate bytes; string
lengths and counts; nesting depth; object/array members; graph entities and
relations; ownership depth; module/reference expansion; extension count and
payload; numeric admissibility; diagnostics; and aggregate work and memory.
A limit violation is a deterministic resource outcome in the same
operation-result envelope, not an invitation to continue unbounded work. The
admission phase selects the profile and applies immediately knowable input
limits; resource guards remain active throughout later phases for expansion,
graph, diagnostic, work, and memory limits that cannot be known before parsing.
Numeric limits, accounting units, profile negotiation, and enforcement detail
are deliberately not selected here.

## Cross-links and non-goals

After source admission, the resolver produces the [body-graph
contract](../body-graph/README.md). That contract owns typed semantic concepts,
identity-bearing relations, frames, invariants, provenance, and the conditions
for a validated snapshot. This document does not define a bone hierarchy,
solver, mesh, runtime pose, surface representation, or anatomy-fidelity
promise.

Representative schema-level fixtures must cover valid documents, malformed
documents, duplicate keys, unknown core members, unsupported required and
optional extensions, unsupported contract revisions, resource-limit outcomes,
and deterministic diagnostics. Compiler-consumed generation fixtures remain
unactivated until a compiler reads this contract; the fixture policy and
cross-DR matrix remain the canonical planning owners.

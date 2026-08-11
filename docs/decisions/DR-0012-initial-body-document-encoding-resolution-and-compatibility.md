# DR-0012: Initial body-document encoding, resolution, and compatibility

ID: DR-0012

Scope: Specification and architecture

Status: Proposed

Revision: 3

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-11

Supersedes: —

Superseded by: —

## Context

The CK-KICK-012 Batch 4 discussion needs an initial source representation and
an executable boundary between admission, structural recognition, semantic
resolution, diagnostics, and successful snapshot publication. The existing
source-set and resolved-graph boundary in [DR-0002](DR-0002-declarative-body-document-source-of-truth.md)
establishes authority but deliberately leaves encoding and phase mechanics
open. [DR-0008](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
and [DR-0011](DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
establish the first typed semantic boundary, but do not own source parsing,
compatibility recognition, extension handling, or resource admission.

On 2026-08-11 Ben approved the CK-KICK-012 Batch 4 decisions recorded here,
and then approved the CK-KICK-012 Batch 5 blocker-resolution selections in
Revision 2: the closed operation status set and precedence, discriminator/schema
bootstrap order, and hostile-input enforcement boundary. The exact-revision
CK-KICK-012 Batch 5 Double review of Revision 2 is stale historical evidence.
Its three findings motivated the CK-KICK-012 Batch 6 resolutions in this
proposal set: this revision resolves status and primary-diagnostic selection,
while DR-0002, DR-0008, and DR-0011 resolve the linked Attachment composition
and cardinality consequences. This discussion approval is not DR acceptance.
Revision 3 remains Proposed with Owner approval Pending and Review status
Pending; its current-revision Double review is pending. Exact field spelling,
diagnostic codes, concrete resource values, tolerances, canonical
axes/units/rotation/scale/shear, and the canonical-byte algorithm remain later
specification work.

## Decision

### Initial source encoding and representation boundary

The initial authoritative source encoding is strict UTF-8 JSON, exactly one
document. Duplicate object keys are rejected. Comments, includes, and
evaluation are not part of the initial source language. The document is paired
with JSON Schema Draft 2020-12 for structural validation; the CK resolver owns
semantic validation and resolution rather than delegating semantics to the
schema.

Source text, the normalized semantic model, and the resolved snapshot are
distinct representations:

- **Source text** is the authored representation and the source-set authority.
- **Normalized semantic model** is resolver-owned derived data after structural
  recognition and normalization; it is not a second authored source.
- **Resolved snapshot** is a build-scoped, derived, inspectable success payload
  published only when the operation is valid-supported and all required
  values and invariants resolve.

Deterministic debug JSON may be emitted for inspection. Canonical bytes and
semantic hashing are not selected by this decision. A future restricted YAML
adapter may be added only if it normalizes to the same semantic model and does
not create a competing semantic contract or authority. No multiple authoring
syntaxes are supported initially.

### Deterministic resolution phases and provenance

Resolution proceeds through these ordered phases:

1. raw-byte, UTF-8, and resource admission;
2. strict JSON parsing and contract recognition;
3. dependencies;
4. namespaces/identity/references;
5. ownership/typed relations;
6. unit/frame normalization and value derivation;
7. semantic invariants; and
8. successful snapshot publication.

The operation-result envelope owned by DR-0002 contains diagnostics from all
reached phases. Its closed status set is **success**, **input-failure**,
**invalid-source**, **unsupported**, **dependency-failure**,
**resource-limit**, and **internal-failure**. Input-failure applies only when
the authoritative top-level source is unavailable, unreadable, or cannot be
acquired as input. Invalid UTF-8 in supplied bytes, strict JSON syntax failure,
duplicate keys, a missing/malformed/duplicate discriminator, recognized-
revision schema failure, or source-caused semantic, reference, relation,
measurement, or invariant failure is invalid-source. A well-formed recognized
bootstrap with an unknown family or unsupported revision, or a required
unsupported extension/capability, is unsupported. Dependency unavailable,
unreadable, integrity, or revision failure is dependency-failure; a configured
profile budget that prevents complete processing is resource-limit; and a
compiler invariant/trust-loss failure or outside-guarantee environment/process
failure is internal-failure. A valid-supported operation is success. Exact
diagnostic code spellings remain deferred.

Final status selection is deterministic and ordered as follows: internal-failure
has precedence whenever result trust is lost; otherwise resource-limit has
precedence when a configured resource limit, including diagnostic-arena
exhaustion, prevents completeness; otherwise the earliest fatal reached phase
determines the status. Within that selected earliest fatal phase, when both
invalid-source and unsupported have been established, invalid-source outranks
unsupported. Other ordinary status choices remain determined by the
phase-specific mapping above. Earlier diagnostics from reached phases are
retained when a fatal phase blocks dependent work, but are marked incomplete.

The primary diagnostic is the first diagnostic that establishes the final status
under the normative deterministic diagnostic order. Diagnostic storage is
bounded, but reserved primary capacity preserves the minimal matching candidate
for that rule despite ordinary diagnostic truncation. If diagnostic-arena
exhaustion itself makes the final status resource-limit, the reserved
resource/truncation diagnostic is selected by the same final-status-primary
rule. Independent diagnostics within a reached phase are accumulated and
deterministically ordered by phase, severity/category, normalized source
path/offset, code, and semantic address; human-readable messages are excluded
from ordering.

A fatal phase blocks dependent later phases; a required ambiguous or unresolved
value cannot enter a successful snapshot. Publication occurs only after the
preceding phases complete successfully. The Stage 1 fixture taxonomy of
valid-supported, semantically invalid, and well-formed-but-unsupported applies
only to admitted, recognized semantic fixtures; parser, dependency, resource,
and internal outcomes are operation outcomes outside that taxonomy.

Provenance distinguishes authored, defaulted, and derived values. A derived
value identifies its derivation rule and source semantic addresses. Defaults
are distinguishable from authored values and cannot silently override an
authored claim. The normalized model and snapshot retain enough provenance to
explain value derivation and the outcome without making either representation
authored authority.

### Contract bootstrap and recognition

Admission first enforces the raw-byte and UTF-8/resource boundary. Strict JSON
parsing then preserves duplicate-key detection; parsing does not silently
collapse duplicate members. The parsed value must be a top-level object with
exactly one minimal, version-neutral contract discriminator containing a
contract family and revision. The exact serialized discriminator spelling is
deferred. A non-object top level, or a missing, malformed, or duplicate
discriminator, is invalid-source.

Only after that discriminator is valid does recognition classify the family and
revision. An unknown family or unsupported revision is unsupported before any
current schema is applied. A recognized revision selects its exact paired
schema; revision-specific structural validation and its unknown-member policy
then run. There is no mega-schema and no current-schema-first fallback. Thus a
schema cannot accidentally reinterpret an unknown revision, and a malformed
source cannot be mistaken for a well-formed-but-unsupported contract.

### Core fields, extensions, and diagnostics

Unknown core fields fail structural or contract recognition. Extensions are
allowed only through explicit namespaced extension envelopes declaring a
namespace, revision, required flag, and payload. An unsupported required
extension produces an unsupported outcome. An unsupported optional extension
is preserved opaquely, has no core semantic effect, and is not silently
interpreted by the resolver.

Diagnostics in the authoritative operation-result envelope have stable fields
for a code, category, phase, path, and zero or more affected semantic
addresses, plus human-readable text for people. Diagnostic ordering is
deterministic. Human text is not a compatibility key; consumers must use the
stable diagnostic fields and outcome. Exact field spelling and diagnostic-code
vocabulary remain later specification work.

### Exact contract recognition and identity separation

The resolver initially requires the exact supported semantic contract family
and revision. Once the minimal discriminator is valid, a document from another
family or revision produces an unsupported outcome before a current schema is
applied; it is not silently migrated, downgraded, or treated as the supported
contract. Migration is an explicit operation that produces a new source
document.

The semantic contract family and revision remain separate from compiler/build
identity, configuration identity, seed identity, dependency identity, and
artifact identity. Semantic equivalence is concerned with resolved semantic
identities, relations, frames, values, provenance, and outcome. It does not
depend on source whitespace, object-key order, or generated mesh topology.
Canonical byte and semantic-hash rules remain deferred.

### Resource profiles and minimum Stage 1 invariants

Every implementation profile must impose finite limits for at least: source
and aggregate bytes; string lengths/counts; nesting depth; object/array
members; graph entities and relations; ownership depth; module or reference
expansion; extension count and payload; numeric admissibility; diagnostics; and
aggregate work and memory. Concrete profile values are implementation/profile
detail and must be recorded with each result so resource evidence is
reproducible.

The raw-byte cap and UTF-8/tokenization guards are enforced incrementally while
bytes are admitted; string and number token-length limits are checked before
conversion; and nesting/member accounting occurs during parsing. Per-
dependency and aggregate byte/count/depth limits remain active while
dependencies are admitted. Reference, module, and graph expansion, plus
deterministic work, are charged before allocation or expansion is committed.
Diagnostic storage uses a bounded arena with reserved capacity for the
primary resource/truncation report. These guards remain active through every
later phase because graph, reference, expansion, diagnostic, work, and memory
limits cannot all be known before parsing. A configured profile limit breach
deterministically reports resource-limit and blocks dependent work rather than
being reclassified as an ordinary semantic failure. Deterministic work units
are preferred to wall-clock time for the profile budget.

A true operating-system/process out-of-memory condition outside the configured
and reserved guarantee is an environment/internal failure; the operation does
not promise impossible recovery from it. Exact thresholds, token accounting
units, and profile negotiation remain deferred profile/specification details.

The minimum Stage 1 supported-success invariants are:

- unique semantic addresses;
- acyclic single-owner containment;
- one embodied root Part;
- every embodied Part, including optional module Parts, has exactly one
  containment path to the root and remains connected independently of relation
  traversal;
- required Stage 1 Joint edges connect structural parents to immediate child
  Parts;
- valid Joint and Attachment endpoints;
- canonical Joint proximal/distal records and one Socket interface frame are
  materialized in their owning Part bases with provenance;
- exactly one incoming active Attachment for each present attached module root
  initially, and no incoming Attachment for an absent optional module;
- one active Attachment is the initial capacity of each host Socket;
- repeated endpoint pairs, host Socket reuse, zero incoming Attachments for a
  present attached module root, and multiple incoming Attachments are distinct
  rejected conditions;
- Attachment placement composes the module-root-to-mating-Socket-owner
  containment transform with the mating Socket's owner-local frame before
  inversion/alignment, and the derived result is the attached root's sole
  resolved child-local containment placement relative to its host parent;
- descendants inherit placement only through containment, with no parallel
  Attachment transform-inheritance path;
- any competing authored root-local placement agrees with that same canonical
  derived child-local value within the later-defined tolerance, with
  provenance for every input and composition step retained;
- no dangling references;
- finite normalized values;
- complete provenance;
- required values resolved and unambiguous; and
- deterministic ordering and lineage.

Valid, semantically invalid, and well-formed-but-unsupported fixtures, along
with their expected primary diagnostic classes/codes, must be frozen before
implementation evidence is treated as a claim. The cross-DR fixture matrix
linking identity, typed articulation, measurements/frames, outcomes, and
diagnostics must also be frozen before evidence claims.

## Consequences

- One strict initial authoring path makes structural admission reproducible
  while leaving semantic meaning in the resolver and its owner records.
- Source text, normalized model, and resolved snapshot cannot be confused as
  competing authorities, and debug output cannot become a success artifact by
  implication.
- Phase-local diagnostic accumulation is useful for independent errors while
  fatal phase blocking prevents later consumers from treating incomplete state
  as resolved.
- A closed operation status set and earliest-fatal-phase rule give clients one
  observable outcome; retained earlier diagnostics are explicitly incomplete,
  and a primary diagnostic always agrees with that status. Internal trust loss,
  configured resource-limit completeness failure, phase precedence, the
  invalid-source-over-unsupported tie-break, and the first status-establishing
  diagnostic are ordered explicitly.
- Discriminator-first recognition prevents an unknown family or revision from
  being interpreted by a current schema, while malformed discriminator input
  remains invalid-source.
- Required and optional extension failures have distinct compatibility
  outcomes, and opaque optional payload preservation avoids accidental core
  semantics.
- Exact contract recognition prevents silent downgrade or migration; explicit
  migration remains auditable and produces a new source.
- Finite resource profiles make denial-of-service and pathological expansion
  behaviour part of the input contract, while recorded profile values permit
  later reproducible evidence.
- Incremental admission/tokenization and pre-allocation charging make
  configured resource-limit outcomes deterministic; bounded diagnostics retain
  terminal reporting without promising recovery from true process OOM. Reserved
  primary capacity preserves the minimal matching diagnostic, including when
  arena exhaustion establishes resource-limit.
- Attachment cardinality and placement are auditable: a present module root
  has exactly one incoming active Attachment, an absent optional module has
  none, each host Socket accepts one, and repeated endpoint pairs, host reuse,
  zero incoming, and multiple incoming cases are rejected distinctly. A
  descendant-owned mating Socket is composed through containment and yields the
  root's sole child-local placement; descendants inherit only through
  containment.
- The initial format is intentionally narrow. A future restricted YAML adapter
  must normalize to the same semantic model, and future canonical-byte or
  semantic-hash rules require separate specification work.

## Alternatives Considered

### Multiple authoring syntaxes initially

Supporting JSON, YAML, and a bespoke syntax at launch could improve authoring
ergonomics, but would multiply parser, duplicate-key, extension, and
compatibility behaviour before the semantic model is proven. One strict JSON
path is selected initially; a future adapter must normalize to the same model.

### Let the schema own semantic resolution

Encoding semantic invariants entirely as schema would make structural tooling
convenient, but would couple the semantic contract to schema expressiveness and
obscure provenance and typed resolver behaviour. Draft 2020-12 is selected for
structural validation; CK resolver semantics remain authoritative.

### Silently migrate or downgrade unsupported revisions

Automatic migration would appear convenient, but can change authored meaning,
diagnostics, identity, or defaults without a new source artifact. Exact
family/revision recognition and explicit migration preserve auditability.

### Apply the current schema before contract recognition

A mega-schema or current-schema-first path could reuse one validator, but it
would allow an unknown family or revision to be interpreted under today's
meaning and could turn discriminator mistakes into misleading structural
errors. The selected discriminator-first bootstrap chooses the exact
revision-specific schema only after recognition.

### Ignore unknown fields or interpret all extensions as core

Ignoring unknown core fields would permit misspelled or incompatible input to
appear valid. Treating optional extensions as core would make support depend on
hidden implementation behaviour. Unknown core fields fail; extension envelopes
declare their namespace/revision/required status, and unsupported optional
payloads remain opaque.

### Unbounded input and expansion

Unbounded documents simplify an initial implementation, but make resource
failure nondeterministic and expose the resolver to pathological work and
memory use. Finite implementation-profile categories are required, with
concrete values recorded as profile evidence.

### Check resources only after building a DOM or expanded graph

Post-DOM checks are too late: duplicate keys, token conversion, nesting, and
large references may already have consumed unbounded memory or work, and
different parsers may fail at different points. Streaming admission,
incremental token accounting, and pre-allocation expansion charging are
selected; exact thresholds remain profile detail.

### Let diagnostics grow until processing finishes

An unbounded diagnostic collection permits invalid hostile input to exhaust
the same memory needed to report its failure and makes truncation vary by
implementation. A bounded diagnostic arena reserves terminal capacity for the
primary resource/truncation report and retains deterministic earlier findings.

### Leave same-phase status and primary precedence implicit

Relying on implementation order would make mixed invalid-source and unsupported
failures, as well as truncation, produce different top-level statuses or primary
diagnostics across implementations. The selected precedence and reserved
candidate rule make both outcomes deterministic while preserving the
phase-specific mapping for ordinary cases.

### Publish partial success after a fatal phase

Partial state can expose useful debugging information, but downstream tools
could mistake it for a valid snapshot. The envelope may carry explicitly
non-contractual debug information, while successful snapshot publication is
reserved for complete valid-supported resolution.

### Define canonical bytes and hashes now

Canonicalization could support durable caching and identity immediately, but
it would lock byte-level rules before semantic and artifact identity needs are
understood. Deterministic debug JSON is allowed; canonical bytes and semantic
hashing remain deferred.

## Adversarial Review Response

The Revision 1 Double review is preserved as stale evidence at commit
`7dba9346c91c59ff99f10b94630690bf732d6b28`: the fresh independent Sol-medium
contract/schema/security pass
([review 01](reviews/DR-0012-rev-01-review-01.md)) and the fresh independent
semantic-graph/graphics/runtime pass
([review 02](reviews/DR-0012-rev-01-review-02.md)) both recommended **Revise**
with **High** confidence. Their blockers motivated Revision 2's closed status
algebra, bootstrap order, bounded diagnostics, streaming/pre-allocation
resource enforcement, and explicit graph-side minimum invariants. The
Attachment and canonical frame details remain owned jointly with DR-0008 and
DR-0011; this record does not make those concepts implementation-specific.

Revision 2's exact-revision CK-KICK-012 Batch 5 Double review examined commit
`a282dbabffd83afa4e62577086934d00f98e12c7` and remains stale historical
evidence: the independent
[contract/schema/security pass](reviews/DR-0012-rev-02-review-01.md) recommended
**Revise** at **High** confidence, while the independent
[semantic-graph/graphics/runtime pass](reviews/DR-0012-rev-02-review-02.md)
recommended **Accept** at **Medium** confidence with no DR-0012-specific
blocker.

The three Batch 5 findings motivated the current CK-KICK-012 Batch 6 proposal
text and are resolved here and in the linked records: this revision makes
internal-failure trust loss, resource-limit completeness failure, earliest
fatal phase, the invalid-source-over-unsupported tie-break, and the
status-establishing primary diagnostic explicit; DR-0002, DR-0008, and DR-0011
resolve descendant-owned mating Socket composition and Attachment cardinality.
The exact-revision review is therefore stale historical evidence, not a clean
review or acceptance. The current Revision 3 Double review is pending. Exact
serialized field spellings, diagnostic codes, concrete thresholds,
dependency-revision semantics, canonical axes/units/rotation/scale/shear,
canonical bytes/hashing, and fixture/security evidence remain deferred. Review
status is Pending; Owner approval remains Pending and Status remains Proposed.
Only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the exact source fields and paired JSON Schema Draft 2020-12 while
  preserving the source/model/snapshot boundary and resolver ownership of
  semantics.
- Implement duplicate-key rejection, strict UTF-8 and one-document admission,
  and rejection of comments, includes, evaluation, and unknown core fields.
- Define extension-envelope field spelling, namespace/revision handling,
  required-versus-optional outcomes, opaque preservation, and core semantic
  isolation.
- Define stable diagnostic codes/categories, exact paths and affected-address
  representation, the closed status set and final-status precedence (internal
  trust loss, configured resource-limit completeness failure, earliest fatal
  phase, and the invalid-source-over-unsupported tie-break), the first
  status-establishing primary diagnostic under deterministic ordering,
  retained-but-incomplete earlier diagnostics, bounded arena and terminal
  truncation/resource reporting, and deterministic ordering by phase,
  severity/category, normalized path/offset, code, and semantic address; human
  text must remain non-compatibility data.
- Implement and test the eight ordered phases, phase-local accumulation,
  fatal dependency blocking, successful publication conditions, and provenance
  for authored/defaulted/derived values and derivation source addresses.
- Implement discriminator-first bootstrap: raw-byte/UTF-8/resource admission,
  strict JSON with duplicate detection, one top-level object and one minimal
  family/revision discriminator, unsupported recognition before current-schema
  application, then exact revision-schema and unknown-member validation.
- Enforce streaming byte/token/nesting/member limits, pre-conversion string and
  number token limits, per-dependency and aggregate budgets, pre-allocation
  reference/module/graph/work charging, and reserved diagnostic capacity that
  preserves the minimal matching primary candidate even after ordinary
  truncation; if arena exhaustion establishes resource-limit, its reserved
  resource/truncation diagnostic must obey the same primary rule.
  Record profile values with each result; configured breaches are
  resource-limit, while true outside-guarantee process OOM is an
  environment/internal failure.
- Freeze resource-exhaustion fixtures and the valid, semantically-invalid, and
  unsupported outcomes only after admission/recognition, keeping parser,
  dependency, resource, and internal outcomes separate.
- Prove exact initial Attachment cardinality and host Socket capacity, with
  distinct fixtures for repeated endpoint pairs, host Socket reuse, zero
  incoming Attachments for a present module root, and multiple incoming
  Attachments. Prove descendant-owned mating Socket composition through the
  module-root containment path and that its result is the root's sole
  child-local placement, with no parallel Attachment inheritance.
- Prove the minimum Stage 1 invariant set and freeze the cross-DR fixture
  matrix before treating implementation output as evidence for the contract.
- Defer canonical axes, units, rotation, scale, shear, exact tolerances,
  diagnostic codes, dependency-revision semantics, canonical bytes, semantic
  hashing, and future migration/adapters to their owning specification work.

## Canonical Design Links

- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [First digitigrade morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [Minimal semantic vocabulary, measurements, and frames](DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [Normative specification boundary](../../spec/README.md)

## Reversibility and Revisit Triggers

Revisit the initial encoding if strict JSON prevents the bounded authoring
workflow or if a future adapter cannot normalize without semantic drift. Any
new syntax must preserve the same normalized semantic model and explicit
compatibility recognition. Revisit resource categories or profile values when
measured evidence exposes a missing limit or an unjustified bound. Revisit
canonicalization and migration only through explicit later specification work;
neither is implied by deterministic debug output.

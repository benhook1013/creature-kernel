# DR-0012: Initial body-document encoding, resolution, and compatibility

ID: DR-0012

Scope: Specification and architecture

Status: Proposed

Revision: 5

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-12

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
Its three findings motivated the CK-KICK-012 Batch 6 resolutions recorded in
Revision 3. The exact Revision 3 Double review at commit
`c64b1b98948304d631eecea6a354c9e42c89c510` then identified F1–F3 for this
record. Ben approved those finding resolutions in discussion on 2026-08-11;
Revision 4 then resolved total status/completeness together with the linked
Attachment composition and cardinality consequences owned by DR-0002,
DR-0008, and DR-0011. Revision 5 records Ben's 2026-08-12 discussion approval
of five Recommendation 1 resolutions: the total phase/status/completeness
rule, normalized module-instance declaration and global Socket capacity,
Attachment transform admissibility, the four readiness gates, and the
authoritative build/publication outcome. This discussion approval is not DR
acceptance. Revision 5 remains Proposed with Owner approval Pending and Review
status Pending. The prior Revision 4 Double review examined target commit
`88004388f9537a37617ae248bdaad4625e6f3f03` in [review 01](reviews/DR-0012-rev-04-review-01.md)
and [review 02](reviews/DR-0012-rev-04-review-02.md); both independent passes
recommended **Revise** at **High** confidence. The prior Review Complete state
records evidence, not a clean review or acceptance. Those Revision 4 artifacts
are now stale historical evidence after this proposal change and a fresh
current Double review is required. The Revision 3 and earlier reviews remain
stale historical evidence. Exact field
spelling, diagnostic codes, concrete resource values, tolerances, canonical
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
**resource-limit**, and **internal-failure**. A non-resource acquisition
failure that leaves the authoritative top-level source unavailable, unreadable,
or incomplete is input-failure. Only a completely supplied authoritative byte
sequence may produce invalid-source: invalid UTF-8, strict JSON syntax failure,
duplicate keys, a missing/malformed/duplicate discriminator, recognized-
revision schema failure, or source-caused semantic, reference, relation,
measurement, or invariant failure is invalid-source. A well-formed recognized
bootstrap with an unknown family or unsupported revision, or a required
unsupported extension/capability, is unsupported. In the dependency phase,
inability to acquire, read, verify, or resolve a required dependency is
dependency-failure; complete dependency content that reaches parsing or
semantic validation uses the same invalid-source/unsupported mapping as other
supplied source content. A valid-supported operation is success. Exact
diagnostic code spellings remain deferred.

The conceptual phase/status/completeness matrix is total and is the canonical
rule for this resolver boundary. It is aligned with any later serialized
phase/status/completeness matrix; exact field and code spellings remain
deferred. Its status and continuation rules are:

| Applicable phase or condition | Status and precedence | Processing completeness | Diagnostic completeness |
| --- | --- | --- | --- |
| Raw acquisition/admission cannot obtain the complete authoritative bytes | `input-failure`, unless a higher-priority trust/resource interruption applies | Incomplete when required acquisition or trusted outcome cannot finish | True only if all profile-required retained diagnostics were kept |
| Dependency acquisition/read/verification/resolution is interrupted | `dependency-failure`, subject to global internal-trust-loss and qualifying resource-limit precedence; if mixed with content outcomes in the same phase, it outranks `invalid-source`, which outranks `unsupported` | Incomplete because required dependency/outcome processing could not finish | True only when all applicable profile-required diagnostics were retained |
| Dependency content is complete and establishes source outcomes | Complete dependency content uses the source mapping: `invalid-source` outranks `unsupported`; a same-phase acquisition interruption still takes the higher `dependency-failure` outcome | Complete when all applicable required checks needed to establish and trust the selected outcome ran | True when all applicable profile-required diagnostics were retained |
| Parse/contract or semantic phase establishes mixed source outcomes | `invalid-source` outranks `unsupported`; complete supplied content is required before `invalid-source` | Complete when all applicable mandatory checks establishing/trusting the selected outcome ran, even when later dependent phases are blocked | True when all applicable profile-required diagnostics were retained |
| Configured resource breach prevents required work or trusted result | `resource-limit`, after global internal trust loss | Incomplete when required processing/trusted completion is prevented | True only for the retained diagnostics that the profile requires and can trust |
| Internal or environment interruption loses trust | `internal-failure` | Incomplete when required processing/trusted completion is interrupted | True only for diagnostics retained as trusted under the profile |
| No earlier failure and all applicable work succeeds | `success` | Complete | True when all applicable profile-required diagnostics were retained |

Global internal-failure trust loss has precedence. Otherwise, a configured
resource breach has `resource-limit` precedence only when it prevents required
processing or a trusted result. Otherwise, the earliest applicable phase unable
to produce its required output determines status. All mandatory independent
checks capable of changing final status or the primary diagnostic run, subject
to configured resource or trust interruption. Optional/advisory checks may
stop and cannot change status or the primary diagnostic. A fatal result can be
processing-complete when all work applicable to establishing and trusting that
result ran; normatively blocked later phases are inapplicable and do not make
it incomplete. Processing is incomplete only when acquisition, dependency,
resource, environment, or internal interruption prevents required outcome
processing.

Diagnostic completeness is independently observable: it is true when all
applicable diagnostics required by the selected profile were retained.
Ordinary diagnostic capping/truncation makes it false but is not
`resource-limit` when required processing and a trusted result continue. A
resource-limit outcome requires the breach to prevent required processing or
trusted completion. The primary diagnostic is the first diagnostic that
establishes the final status under the normative deterministic diagnostic
order. Diagnostic storage is bounded, but reserved primary capacity preserves
the minimal matching candidate despite ordinary diagnostic truncation. If
diagnostic-arena exhaustion itself prevents trusted completion and establishes
`resource-limit`, the reserved resource/truncation diagnostic follows the same
final-status-primary rule. Independent diagnostics within a reached phase are
accumulated and deterministically ordered by phase, severity/category,
normalized source path/offset, code, and semantic address; human-readable
messages are excluded from ordering. CK-PROD-033 must be corrected by its
canonical product-document editor to mirror this conceptual matrix; this DR
cross-links that correction and does not silently override product authority.

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
limits cannot all be known before parsing. A configured profile breach that
prevents required processing or trusted-result completion deterministically
reports resource-limit and blocks dependent work rather than being
reclassified as an ordinary semantic failure. A diagnostic cap that merely
drops additional diagnostics while required processing continues is observable
as incomplete diagnostic completeness, not resource-limit. Deterministic work
units are preferred to wall-clock time for the profile budget.

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
- normalized module-instance declarations identify the instantiated module,
  root Part, instance anchor/provenance, presence/optionality, and whether
  Attachment composition is required, without adding an eighth identity-
  bearing graph concept; optional absence differs from present-but-unattached
  state before cardinality checking, and a present Attachment-required root
  with zero incoming active Attachments is invalid;
- required Stage 1 Joint edges connect structural parents to immediate child
  Parts;
- valid Joint and Attachment endpoints;
- canonical Joint proximal/distal records and one Socket interface frame are
  materialized in their owning Part bases with provenance;
- exactly one incoming active Attachment for each present attached module root
  initially, and no incoming Attachment for an absent optional module;
- each Socket has total active capacity one across host and mating roles; a
  Socket used by two active Attachments in any role combination, including one
  host use plus one mating use, is invalid;
- repeated endpoint pairs, host reuse, mating reuse, cross-role reuse, zero
  incoming Attachments for a present attached module root, and multiple
  incoming Attachments are distinct rejected conditions or have an explicit
  deterministic diagnostic mapping;
- Attachment placement uses the typed host-local equation owned by DR-0011 and
  DR-0008, and the derived result is the attached root's sole resolved
  child-local containment placement relative to its host parent;
- descendants inherit placement only through containment, with no parallel
  Attachment transform-inheritance path;
- any competing authored root-local placement agrees with that same canonical
  derived child-local value within the later-defined tolerance, with
  provenance for every input and composition step retained;
- every transform entering Attachment composition is finite, non-degenerate,
  and invertible under the declared transform profile; source-caused violation
  is semantic `invalid-source` with deterministic diagnostic and preserved
  provenance, while implementation failure on an admissible transform is
  `internal-failure`;
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
- A closed operation status set and total phase/status/completeness matrix give
  clients one observable outcome; retained diagnostics from reached phases
  remain valid, and a primary diagnostic always agrees with that status.
  Global internal trust loss dominates, a configured resource breach is
  `resource-limit` only when it prevents required processing or trusted
  completion, and otherwise the earliest unable applicable phase determines
  status. Dependency same-phase precedence is `dependency-failure`, then
  `invalid-source`, then `unsupported`; complete acquisition precedes
  `invalid-source`, and parse/semantic `invalid-source` outranks `unsupported`.
  Mandatory independent checks run subject to interruption, while optional
  checks cannot change status or primary. Processing completeness is relative
  to work applicable to establishing/trusting the selected outcome; blocked
  later phases are inapplicable. Diagnostic completeness is relative to
  profile-required retained diagnostics, so ordinary truncation is not a
  resource outcome when trusted processing continues. CK-PROD-033 must be
  corrected by its canonical editor to mirror this rule.
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
  terminal reporting without promising recovery from true process OOM. The
  independent processing- and diagnostic-completeness concepts distinguish a
  capped diagnostic set from processing failure. Reserved primary capacity
  preserves the minimal matching diagnostic, including when arena exhaustion
  establishes resource-limit.
- Attachment cardinality and placement are auditable: a normalized
  module-instance declaration identifies the module, root Part, anchor/
  provenance, presence/optionality, and Attachment-required state without a
  new graph concept; optional absence differs from present-but-unattached
  state. A present module root has exactly one incoming active Attachment, an
  absent optional module has none, and each Socket has total active capacity one
  across host and mating roles. Repeated endpoint pairs, host reuse, mating
  reuse, cross-role reuse, zero incoming, and multiple incoming cases are
  rejected distinctly or mapped deterministically. A descendant-owned mating
  Socket is composed through the typed host-local equation owned by DR-0008
  and DR-0011 and yields the root's sole child-local placement; descendants
  inherit only through containment. Every transform entering composition is
  finite, non-degenerate, and invertible under its declared profile; source
  violations are semantic `invalid-source`, while implementation failure on
  admissible transforms is `internal-failure`.
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
global internal-failure trust loss, resource-limit only when required
processing/trusted completion is prevented, earliest unable phase, complete
acquisition before invalid-source, the parse/semantic invalid-source-over-
unsupported tie-break, unambiguous dependency mapping, independent
processing/diagnostic completeness, and the status-establishing primary
diagnostic explicit. DR-0002, DR-0008, and DR-0011 resolve descendant-owned
mating Socket composition and Attachment cardinality. Ben approved these F1–F3
resolutions in discussion on 2026-08-11. The exact Revision 3 Double review at
commit `c64b1b98948304d631eecea6a354c9e42c89c510` is stale historical evidence,
not a clean review or acceptance. Its independent [review 01](reviews/DR-0012-rev-03-review-01.md)
recommended **Revise** at **High** confidence, and [review 02](reviews/DR-0012-rev-03-review-02.md)
recommended **Revise** at **Medium** confidence. The prior Revision 4 Double
review examined target commit `88004388f9537a37617ae248bdaad4625e6f3f03` in
[review 01](reviews/DR-0012-rev-04-review-01.md) and [review 02](reviews/DR-0012-rev-04-review-02.md);
both independent passes recommended **Revise** at **High** confidence. Those
ten artifacts and their five findings are now stale historical evidence after
the Revision 5 proposal change. Their findings are dispositioned for the next
review as follows: (1) the total phase/status/completeness matrix, dependency
same-phase precedence, mandatory-check continuation, and CK-PROD-033
cross-link are revised here; (2) module-root observability and global
cross-role Socket capacity are revised here with graph/morphology/vocabulary
ownership in DR-0002/DR-0008/DR-0011; (3) Attachment transform admissibility
and source-versus-implementation mapping are revised here and linked records;
(4) the four technical readiness gates are owned by DR-0013; and (5)
authoritative build/publication outcome and `output-failure` are owned by
DR-0013. The latter two are cross-links, not additional DR-0012 decisions. A
fresh current Double review is required. Exact serialized field spellings,
diagnostic codes, concrete thresholds, dependency-revision semantics,
canonical axes/units/rotation/scale/shear, conditioning/comparison
tolerances, canonical bytes/hashing, and fixture/security evidence remain
deferred. Owner approval remains Pending and Status remains Proposed; Review
status is Pending. Only Ben may accept or reject this proposal.

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
  representation, the closed status set and total final-status selection
  (global internal trust loss, resource-limit only when required
  processing/trusted completion is prevented, earliest unable phase,
  complete-acquisition input-failure, parse/semantic invalid-source-over-
  unsupported, and unambiguous dependency mapping), independent processing and
  diagnostic completeness fields, the first status-establishing primary
  diagnostic under deterministic ordering, retained-but-incomplete earlier
  diagnostics, bounded arena and terminal truncation/resource reporting, and
  deterministic ordering by phase, severity/category, normalized path/offset,
  code, and semantic address; human text must remain non-compatibility data.
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
  truncation. Ordinary diagnostic capping/truncation must leave processing
  successful when required work and trusted result continue, rather than
  becoming resource-limit; if arena exhaustion prevents trusted completion and
  establishes resource-limit, its reserved resource/truncation diagnostic must
  obey the same primary rule. Record profile values with each result;
  configured breaches that prevent required processing or trusted completion
  are resource-limit, while ordinary diagnostic caps are not and true
  outside-guarantee process OOM is an environment/internal failure.
- Freeze resource-exhaustion fixtures and the valid, semantically-invalid, and
  unsupported outcomes only after admission/recognition, keeping parser,
  dependency, resource, and internal outcomes separate.
- Prove exact initial Attachment cardinality and host/mating Socket capacity,
  with distinct fixtures for normalized module-instance presence/optionality,
  repeated endpoint pairs, host reuse, mating reuse, cross-role reuse, zero
  incoming Attachments for a present module root, and multiple incoming
  Attachments; use distinct deterministic diagnostics or explicit mapping.
  Prove descendant-owned mating Socket composition through the typed host-local
  equation owned by DR-0008/DR-0011 and that its result is the root's sole
  child-local placement, with no parallel Attachment inheritance. Every
  incoming transform must be finite, non-degenerate, and invertible under the
  declared profile; source violations are semantic `invalid-source` with
  deterministic diagnostic/provenance, while implementation failure on an
  admissible transform is `internal-failure`.
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

# DR-0012: Initial body-document encoding, resolution, and compatibility

ID: DR-0012

Scope: Specification and architecture

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Complete

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

On 2026-08-11 Ben approved the CK-KICK-012 Batch 4 decisions recorded here.
This discussion approval is not DR acceptance. This record remains Proposed
with Owner approval Pending and Review Complete; the completed review records
evidence, not acceptance or a clean review, pending Ben's owner disposition.
Exact field spelling,
diagnostic codes, concrete resource values, canonical axes/units/rotation/
scale/shear, and the canonical-byte algorithm remain later specification work.

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

1. resource/input admission;
2. syntax/schema/contract recognition;
3. dependencies;
4. namespaces/identity/references;
5. ownership/typed relations;
6. unit/frame normalization and value derivation;
7. semantic invariants; and
8. successful snapshot publication.

The operation-result envelope owned by DR-0002 contains diagnostics from all
reached phases. Independent diagnostics within a phase are accumulated in a
deterministic order. A fatal phase outcome blocks dependent later phases; a
required ambiguous or unresolved value cannot enter a successful snapshot.
Publication occurs only after the preceding phases complete successfully.

Provenance distinguishes authored, defaulted, and derived values. A derived
value identifies its derivation rule and source semantic addresses. Defaults
are distinguishable from authored values and cannot silently override an
authored claim. The normalized model and snapshot retain enough provenance to
explain value derivation and the outcome without making either representation
authored authority.

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
and revision. A well-formed document from another family or revision produces
a well-formed-but-unsupported outcome; it is not silently migrated, downgraded,
or treated as the supported contract. Migration is an explicit operation that
produces a new source document.

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
reproducible. The first phase selects the resource profile and performs input
admission; its guards remain active through every later phase because graph,
reference, expansion, diagnostic, work, and memory limits cannot all be known
before parsing. A limit violation reports a resource outcome through the
authoritative envelope and blocks dependent work rather than being
reclassified as an ordinary semantic failure.

The minimum Stage 1 supported-success invariants are:

- unique semantic addresses;
- acyclic single-owner containment;
- one embodied root Part;
- every required Part reachable through valid typed relations;
- valid Joint and Attachment endpoints;
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
- Required and optional extension failures have distinct compatibility
  outcomes, and opaque optional payload preservation avoids accidental core
  semantics.
- Exact contract recognition prevents silent downgrade or migration; explicit
  migration remains auditable and produces a new source.
- Finite resource profiles make denial-of-service and pathological expansion
  behaviour part of the input contract, while recorded profile values permit
  later reproducible evidence.
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

The current Revision 1 Double review is Complete at commit
`7dba9346c91c59ff99f10b94630690bf732d6b28`: the fresh independent Sol-medium
contract/schema/security pass
([review 01](reviews/DR-0012-rev-01-review-01.md)) recommends **Revise** with
**High** confidence, and the fresh independent Sol-medium
semantic-graph/graphics/runtime pass
([review 02](reviews/DR-0012-rev-01-review-02.md)) also recommends **Revise**
with **High** confidence.

Review 01 directly finds incomplete operation-envelope outcome/status algebra,
precedence, primary diagnostic, truncation, contract-discriminator/schema
bootstrap order, and minimum hostile-input resource enforcement; its mechanical
secondary-architecture wording finding was aligned after review without
changing this proposal. Review 02 finds graph containment reachability versus relation
traversal/cycles and transform inheritance, optional-module Attachment
structural insertion/socket-frame placement and validity, and canonical Joint
endpoint-frame ownership/roles/basis/provenance/equivalence. These graph
findings are cross-DR dependencies of this record's minimum invariants and
success-snapshot promise, owned with DR-0008 and DR-0011. Classification and
measurement blockers are closed; articulation remains partial because frame and
Attachment gaps remain. Fixture-matrix and specialist obligations remain
nonblocking. Review Complete records evidence, not acceptance or a clean
review; Owner approval remains Pending and Status remains Proposed. The exact
dependency-revision meaning remains a nonblocking later obligation. Only Ben
may accept or reject this proposal.

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
  representation, deterministic ordering, and outcome precedence; human text
  must remain non-compatibility data.
- Implement and test the eight ordered phases, phase-local accumulation,
  fatal dependency blocking, successful publication conditions, and provenance
  for authored/defaulted/derived values and derivation source addresses.
- Record implementation-profile values for every resource-limit category with
  each result, then freeze resource-exhaustion fixtures and the valid,
  semantically-invalid, and unsupported fixture outcomes.
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

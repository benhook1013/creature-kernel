# DR-0012: Initial body-document encoding, resolution, and compatibility

ID: DR-0012

Scope: Specification and architecture

Status: Proposed

Revision: 14

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-13

Supersedes: —

Superseded by: —

## Context

The CK-KICK-012 Batch 4 discussion needs an initial source representation and
an executable boundary between admission, structural recognition, semantic
resolution, diagnostics, and in-memory snapshot finalization/handoff. External
filesystem serialization is a later build/output concern owned by DR-0013, not
part of resolver snapshot completion. The existing
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
status Complete. The prior Revision 4 Double review examined target commit
`88004388f9537a37617ae248bdaad4625e6f3f03` in [review 01](reviews/DR-0012-rev-04-review-01.md)
and [review 02](reviews/DR-0012-rev-04-review-02.md); both independent passes
recommended **Revise** at **High** confidence. The prior Review Complete state
records evidence, not a clean review or acceptance. Those Revision 4 artifacts
are now stale historical evidence after this proposal change and a fresh
current Double review is required. The Revision 3 and earlier reviews remain
stale historical evidence. Exact field
spelling, diagnostic codes, concrete resource values, tolerances, canonical
axes/units/rotation/scale/shear, and the canonical-byte algorithm remain later
specification work. The proposed canonical-data and diagnostic profiles below
now define the direction, while exact profile identifiers and activation
constants remain prerequisites. Ben's 2026-08-12 Batch 9 discussion approval adds the
in-memory snapshot finalization/handoff distinction, absent-module declaration
identity, and the DR-0013 build/output ownership boundary. This material
Revision 6 change makes the Revision 5 current-review artifacts stale.
Revision 6 remains Proposed with Owner approval Pending and Review status
Pending. Ben then approved the Batch 10 top-level envelope, numeric-profile,
and omission/default resolutions recorded in Revision 7. Ben approved the
current-review C3/C4 resolutions on 2026-08-12: frame roles are typed by
owning record, and Readiness 2 freezes a structural rigid-transform carrier
while Readiness 3 freezes numeric semantics and admits expected graph snapshots
through the generic fixture route. This material Revision 8 change makes the
Revision 7 current-review artifacts stale; the record remains Proposed with
Owner approval Pending and a fresh current review pending. On 2026-08-12 Ben
approved the project-owned canonical-data and diagnostic-registry/profile
decisions for the machine contract. This material Revision 9 change makes the
Revision 8 review evidence stale; a fresh current review is pending. On
2026-08-12 Ben discussion-approved the four numeric resolution directions from
the Batch 11 review: exact decimal admission, normative comparisons, a
non-circular numeric experiment method, and future adapter conformance. This
is not DR acceptance or activation. Revision 10 makes the Revision 9
current-revision review artifacts stale; their exact findings are preserved
below. C1 canonical collection ordering/tie handling and C3 immutable
Readiness 2/3 implementation binding remain unresolved for the next
discussion; C4 diagnostic-domain/bootstrap compatibility remains unresolved
in this record. Owner approval remains Pending and Review status is Complete
for the current Batch 12 evidence; the proposal remains Proposed.

On 2026-08-13 Ben approved all five CK-KICK-012/013 Batch 13 resolution
directions in discussion: symmetric canonical-frame comparison with exact
dyadic boundary arithmetic and deterministic quaternion normalization;
post-R3 adapter units and storage-only/runtime-conformance tiers; typed total
keys and explicit multiplicity for unordered source/projection collections; a
separate scoped implementation-content binding for readiness transactions;
and diagnostics sole ownership with a mandatory bootstrap registry/profile.
This material revision remains Proposed only. It accepts no DR and activates
no schema, fixture, parser/resolver, implementation, adapter, experiment, or
package. The Revision 10 Batch 12 review artifacts are stale for this change
and remain preserved below; Owner approval remains Pending and Review status
is Pending pending a fresh current-revision review.

On 2026-08-13 Ben approved the four Batch 13 source-resolution directions for
this record in discussion: semantic zero normalization after every producing
stage; conceptual versioned authored claim identity with stable record addresses
and typed property roles; the mechanically closed, filesystem-safe implementation binding;
and explicit adapter-profile status mapping. This Revision 12 records those
settled directions as Proposed only. It creates no schema, fixture,
parser/resolver, readiness gate, implementation, adapter, experiment, or
package. The Batch 13 Revision 11 review is stale evidence after this material
revision and remains preserved below; Owner approval remains Pending and a
fresh current-revision review is required.

On 2026-08-13 the fresh technical-review dispositions were applied in the
Revision 13 proposal: the wire-independent `claim-id-1` ordering now uses
profile-defined semantic ranks and normalized identifier order; numeric wording
distinguishes required-sqrt quaternion normalization from the already-normalized
tuple-distance predicate; and malformed adapter-profile status mapping is
deferred to the adapter-activation prerequisite rather than classified as
source admission. The exact-target Double review at commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale for this Revision 14
successor. Revision 14 applies the mandatory rank-table activation gate and
preserves the retained-human T4 gate. The current Double review at
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a` is Complete: its governance
findings were corrected mechanically and its technical pass found no findings /
Ready for PR at High confidence. Status remains Proposed and Owner approval
remains Pending; review evidence is not acceptance.

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
  finalized and handed off in memory only when the operation is
  valid-supported and all required values and invariants resolve. A successful
  `resolve` requires this snapshot; an operation such as `validate` may omit it
  when its operation contract intentionally says so. External serialization
  remains a DR-0013 build/output concern.

Deterministic debug JSON may be emitted for inspection. Canonical bytes and
semantic hashing follow DR-0006's proposed project-owned canonical-data
profile; exact field spelling and activation constants remain an activation
prerequisite. A future restricted YAML
adapter may be added only if it normalizes to the same semantic model and does
not create a competing semantic contract or authority. No multiple authoring
syntaxes are supported initially.

### Stage 1 document envelope and typed body collections

The exact conceptual top-level members of the recognized Stage 1 document are
`contract`, `source`, `basis`, `profiles`, `body`, and `extensions`. The
`contract` member owns the version-neutral family/revision discriminator and
is recognized before any revision-specific schema is applied. `basis` is
required source basis data, while `source` carries the authoritative authored
source/source-set identity and claims; `profiles` initially references the
versioned semantic numeric-domain profile. Operational resource and diagnostic
profiles remain operation or fixture context, not authored source semantics.

`body` contains explicit typed collections for `modules`, `parts`, `joints`,
`sockets`, `attachments`, `landmarks`, `dimensions`, `frames`, `regions`,
`capabilities`, and `fields`. Records have explicit types and stable semantic
references; there is no generic record union. Array order is non-semantic, and
every core collection is present even when empty. Core members are strict and
closed under the recognized revision; unknown core members fail, while
extensions use the already-governed namespaced required/optional envelope.
This revision activates no machine schema file; JSON Schema Draft 2020-12
remains the proposed structural vocabulary whose exact file and fields are a
Readiness 2 prerequisite.

Every unordered source collection or projection declares its typed total key
and uniqueness or multiplicity rule before canonicalization. Graph concepts
use structured semantic addresses. Module declarations use tagged declaration
addresses. Owner-role records use tagged kind, owner address, and role, plus
frame/context/claim identity where required. Fixture entries use fixture ID;
duplicate IDs or paths are invalid. External path entries use normalized safe
relative paths, with mode and content retained in their entry projection.
Dependencies use locator and role plus a distinguishing revision identity.
Other build arrays need an owner-defined key before activation. Diagnostics use
profile-defined occurrence keys without silent deduplication. Duplicate keys
fail only for declared uniqueness collections; repeated claims, multisets, and
diagnostics declare multiplicity or occurrence/claim identity. Missing key or
rule is a canonicalization failure; source order, traversal/allocation/index
order, object serialization, and raw element bytes are never fallback keys.

The source basis declares length unit, handedness, up, and forward. Measurements
and transforms identify owner, semantic role, and frame/context. No per-value
unit override is admitted initially. Frame roles are typed by owning record:
Part local/reference, Joint proximal/distal, Socket intrinsic interface, and
Attachment host/mating endpoint context; resolved world/reference and runtime
pose are derived contexts. Readiness 2 checks structural shape and references
only and freezes one rigid-transform carrier: three-component translation plus
explicit four-component `xyzw` quaternion, with no scale or shear fields.
Readiness 3 activates DR-0011's canonical basis, validity, normalization/sign,
ranges, conditioning, composition, and typed comparison semantics, while
preserving the fixed Readiness 2 carrier; adapter storage remains downstream
freedom. It admits expected graph
snapshots through a distinct successor transaction with path, digest,
comparison-profile identity, and exact/semantic comparison rule.

The fixture payload scope remains the manifest plus declared schema, fixtures,
and snapshots. Separately, each readiness transaction that activates
implementation requires the explicit external implementation binding defined by
the [fixture-manifest contract](../../spec/fixture-manifest/README.md), separate
from its fixture payload binding. That owner freezes selected Rust/Cargo
repository paths, modes, and raw contents: sources/manifests, Cargo
configuration or recorded absence, lockfile, toolchain, build scripts, and
declared compile/codegen inputs. Dependency closure separately owns registry,
vendored, path-dependency, and proc-macro provenance/content. Build-request
identity separately owns selected packages/targets, target triple, features,
profile, approved environment/tool/configuration inputs, and the exact
locked/offline command. The activation closure manifest binds or references all
three. It also owns locked/offline root-descriptor no-follow reads and
regular-file-only mode/type/size checks: traversal, symlink, special-file, and
submodule rejection applies to entries or ancestor components; ancestors are
descriptor-opened no-follow directories; final regular-file entries are
rejected when `st_nlink != 1`; normal directory hardlink counts are not rejected.
Vendored-snapshot escalation applies to opaque inputs. Implementation binding,
dependency closure, build-request identity, attempt identity, and fixture
payload binding remain distinct. Post-merge and before the trigger, recompute
implementation and dependency content from an immutable snapshot and
revalidate the exact bound build request; mismatch blocks activation
and requires an explicit successor. This Proposed cross-link does not claim the
machinery is implemented and does not bind the whole repository or create a
custom ledger.

### Exact numeric admission and comparison handoff

After strict JSON parsing and number-token resource checks, the resolver
interprets each number token as an exact signed decimal rational and converts it
directly to IEEE-754 binary64 with round-to-nearest, ties-to-even. This path
does not use a host-parser intermediate, locale, ambient rounding mode, or
implementation-defined precision. Admission requires a finite correctly
rounded result, rejects overflow to infinity and any nonzero exact rational
that rounds to signed zero, and accepts finite nonzero subnormals. Excessive
precision is accepted within the lexical/resource bound without an arbitrary
semantic digit limit. Lexical negative zero is accepted but normalized to
positive zero for semantic/canonical models, while exact source bytes remain
distinct; canonical numeric operations prohibit FTZ/DAZ. Every semantic
numeric-producing stage normalizes produced zero to `+0` after
admission/conversion, composition, inversion, quaternion normalization/sign,
tuple formation, adapter conversion, and narrowing, before comparison or
serialization. A permitted nonzero-to-zero narrowing emits `+0`; raw lexical
`-0` remains distinct only in raw-source identity.

The resolver uses DR-0011's normative typed comparisons. Same-target transform
claims are first normalized into the same canonical local-to-parent frame;
translations are compared directly componentwise, so swapping claims has
exactly the same outcome. A residual transform is only a separately named
diagnostic/composition comparison, never authored same-target equality.

The scalar predicate
`abs(a-b) <= A + R*max(abs(a),abs(b))` is decided over exact dyadic values
decoded from admitted finite binary64 values using bounded integer/dyadic
arithmetic. Rounded floating intermediates and undefined “equivalent
monotonic” evaluation cannot decide the inclusive boundary. Rotation uses the
admitted finite-binary64 half-chord threshold `H`: choose q sign from exact
dyadic dot (`0` chooses `+1`), compute `di=qa_i-s*qb_i`, and accept iff
`sum(di^2) <= (2H)^2` with exact dyadic arithmetic, inclusively. `H` is the
finite binary64 post-normalization Euclidean half-threshold in canonical
quaternion tuple space. A nominal `theta`, if presented, is informational/calibration
metadata only; this source contract does not claim that `H` or `theta` bounds
represented angular error. A future represented-direction or angular
 guarantee requires a new comparison-profile revision and successor evidence.
After deterministic quaternion normalization, the already-normalized
tuple-distance predicate uses no square root, norm, `asin`, or `sin`. The
normalization itself uses the required correctly rounded binary64 square root
specified below.

Source quaternion normalization uses exact max-absolute-component scaling,
fixed `xyzw` divisions, fixed left-to-right squared sum without
reassociation/FMA, correctly rounded binary64 square root, fixed divisions,
drift/near-zero validation, and canonical sign by first nonzero `wxyz`
component positive. Round-to-nearest ties-to-even, no FTZ/DAZ, and no ambient
mode are required; a platform without the required square root is unsupported.
Bounds remain experiment-gated. Competing claims use conceptual versioned
`claim-id-1` (canonical target, closed claim kind, typed source-document/
namespace identity, stable authored record address, typed property role, and
explicit authored claim key or absence). Its wire-independent total order is
owned by the [semantic-address profile](../../spec/semantic-address/README.md):
the canonical target uses its structured address order; closed claim kind and
typed property role use profile-defined semantic tag ranks rather than wire
spelling; typed source-document/namespace identity and each address segment
use normalized identifier Unicode-scalar lexical order with structured
prefix-before-extension ordering; and absent claim keys precede present keys,
whose values use that same identifier order. An activated schema must
bijectively map wire values to these conceptual types/ranks and may not infer
order from wire spelling. Unordered pairs are `(min_id, max_id)`. It never uses array/traversal/
allocation/thread/time/generated index. Same ID
and same normalized value is evaluated once while all occurrences/provenance
remain; same ID with a different value is an invalid-source identity collision.
Evaluate unordered pairs in sorted claim-ID order and use the first failing
sorted pair for conflict detail. Every pair must pass; only then choose the
lexicographically smallest value-type tuple under exact finite-binary64 total
order (`-0` is `+0`), with claim ID breaking exact tuple ties only.
The claim-kind and typed-property-role rank tables are mandatory, versioned
activation inputs. Each table must be complete and injective over its admitted
closed set; a missing, duplicate, or unknown kind, role, or rank entry fails
activation. No canonical claim ordering, digest, or resolver activation may
occur before both tables exist, and wire spelling is never an ordering
fallback.

These rules are normative direction, while exact domains, budgets, ranges,
thresholds, tolerances, profile IDs, and serialized spellings remain
evidence-gated. The numeric experiment must pre-register domains and semantic
error budgets, use fixed operation order and round-to-nearest/ties-to-even
without reassociation, implicit FMA contraction, or FTZ/DAZ, and compare
exact/analytic and independent materially higher-precision oracles across
separate frozen development, held-out, and adversarial corpora. It records
sensitivity/conditioning and metamorphic, permutation, and conditioning
coverage, applies a predeclared validation margin, and rejects out-of-domain
cases rather than widening a budget or selecting the smallest observed error.
WSL x86_64 plus native Linux is the bounded initial reference; materially
different architecture/toolchain evidence is needed only before claiming
broader cross-platform reproducibility. Adapter obligations and activation
sequencing remain owned by DR-0011/DR-0013.

For the future adapter boundary, consume the post-R3 profile owned by
DR-0011/DR-0013: it declares signed-permutation `C`, positive scale `s`
(engine length units per canonical metre), target precision, supported domain,
narrowing/overflow/underflow/subnormal policy, and guarantee tier. Map length-
bearing values using `sC/s`, directions and normalized normals using `C`,
rotations using `C R C^-1`, and rigid transforms using `D H_c D^-1` with
`D=diag(sC,1)` and inverse `D^-1`; derive quaternions from that rotation map
or a proven equivalent. The default/minimal tier promises storage/output
conversion only; an optional runtime-conformance tier adds engine arithmetic,
probes, and fixtures. Binary32 may exclude subnormal-dependent values; a
subnormal-preserving runtime promise requires FTZ/DAZ probes. A failed
capability is unsupported, while trusted in-domain overflow/disallowed
underflow is output-failure. The core binary64 snapshot is unchanged and no
adapter activates from this Proposed source contract.

Adapter profile data is a build-request/target-platform input, not
authoritative body-source content. Therefore malformed adapter request/profile
mapping is deliberately unselected here. Before an adapter profile/schema
activates, Ben must explicitly dispose of the retained-human request-validation
mapping, and the owning build-operation/platform contracts must choose and
review that result mapping while preserving the closed operation status set (or
explicitly revising it). A well-formed unknown revision or
unavailable capability remains `unsupported`; a violated admitted-profile
invariant remains `internal-failure`; and valid supported conversion overflow,
disallowed underflow, or malformed output remains `output-failure`. Until then
no adapter activates and malformed adapter-profile input is not classified as
`invalid-source`/source-admission. This request-validation choice is
implementation/evidence-dependent and is not a blocker for the first Rust
slice.

### Deterministic resolution phases and provenance

Resolution proceeds through these ordered phases:

1. raw-byte, UTF-8, and resource admission;
2. strict JSON parsing and contract recognition;
3. dependencies;
4. namespaces/identity/references;
5. ownership/typed relations;
6. unit/frame normalization and value derivation;
7. semantic invariants; and
8. in-memory snapshot finalization/handoff.

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

For `resolve`, the successful row includes in-memory snapshot finalization and
handoff; a success without that snapshot is not a successful resolve. An
operation such as `validate` may intentionally use the same successful row
without a snapshot when its operation contract says so. External filesystem
serialization is not this phase: it is owned by the DR-0013 build/output
boundary and maps serialization or publication failure to `output-failure`.

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
value cannot enter a successful snapshot. In-memory snapshot finalization and
handoff occur only after the preceding phases complete successfully; external
serialization is outside the resolver and belongs to the DR-0013 build/output
boundary. The Stage 1 fixture taxonomy of
valid-supported, semantically invalid, and well-formed-but-unsupported applies
only to admitted, recognized semantic fixtures; parser, dependency, resource,
and internal outcomes are operation outcomes outside that taxonomy.

Provenance distinguishes authored, defaulted, and derived values. A derived
value identifies its derivation rule and source semantic addresses. Defaults
are distinguishable from authored values and cannot silently override an
authored claim. The normalized model and snapshot retain enough provenance to
explain value derivation and the outcome without making either representation
authored authority.

### Explicit omission and deterministic defaults

Identity, containment, module presence, source basis, and every value required
by the selected grammar are explicit. A missing value is legal only when the
exact contract revision or a named semantic profile owns a deterministic
default rule; exactly one applicable rule owns each default. The resolved model
records `defaulted` provenance and the stable default-rule identity. Defaults
cannot override an authored value or resolve an authored conflict.

Null is not a missing-value marker. Implicit zero, neighbouring-value
inference, and hidden equations are not defaults and are rejected. A permitted
omission means empty only when the contract explicitly assigns that meaning;
core typed collections therefore remain present even when empty. DR-0011 owns
the semantic provenance consequence, while this record owns source encoding,
resolution, and compatibility enforcement.

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

Diagnostics in the authoritative operation-result envelope use a small,
versioned machine registry/profile separate from operation status. The
diagnostics specification is the sole owner of registry, domain, class,
occurrence, profile, ordering, and compatibility meaning. An occurrence may
carry stable code, class, phase, severity, optional source path/offset,
optional typed semantic address, and typed details, plus human-readable text;
human text is neither compatibility data nor hash input. Its closed initial
domains are source-admission, dependency, semantic-identity, graph-structure,
frame-numeric, resource, execution-trust, publication, and inspection; narrow
resolver-invariant and worker-protocol categories are stable classes within
those domains. Resource profiles remain separate operational input.

Body-document and build-operation contracts own top-level status and
precedence only; they do not define competing diagnostic registries or
occurrence/order semantics.

A tiny mandatory bootstrap registry/profile is always known. If a required
registry/profile is unknown, the existing `unsupported` status is used with
the effective bootstrap profile, bounded requested identifiers, and a
deterministic primary diagnostic. The resolver never emits under an unknown
profile and never silently downgrades. Exact ordinary code membership, field
spellings, occurrence keys, and profile identifiers remain fixture-gated.

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
Canonical byte and semantic-hash rules follow DR-0006's versioned,
domain-separated profile and must not include attempt-local or host-local data.

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
  bearing graph concept; an absent declaration has a stable authored
  declaration address and non-embodied module root-role/template reference,
  emits or reserves no Part, cannot be a graph-relation target, and participates
  in declaration uniqueness rather than the Part namespace; if later present,
  its Part identity derives deterministically from the module-instance anchor
  plus root role; optional absence differs from present-but-unattached state
  before cardinality checking, and a present Attachment-required root with
  zero incoming active Attachments is invalid;
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
diagnostics must also be frozen before evidence claims. The exact Proposed
fixture-manifest semantics are owned by the canonical fixture-manifest
specification/cross-contract, while this record owns how admitted fixtures
exercise source encoding, omission/default provenance, and resolver outcomes.

## Consequences

- One strict initial authoring path makes structural admission reproducible
  while leaving semantic meaning in the resolver and its owner records.
- Source text, normalized model, and resolved snapshot cannot be confused as
  competing authorities, and debug output cannot become a success artifact by
  implication.
- A successful `resolve` has an in-memory snapshot handoff, while
  operation-contract-specific validation may intentionally omit one. External
  serialization is not resolver completion and maps its own failures to
  `output-failure` at the build/output boundary.
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
- An absent optional module is represented by a unique authored declaration
  address and non-embodied root-role/template reference only: it emits or
  reserves no Part, cannot be a relation target, and is outside the Part
  namespace. If later present, its Part identity derives from the instance
  anchor plus root role without creating another graph concept.
- The initial format is intentionally narrow. A future restricted YAML adapter
  must normalize to the same semantic model, and future canonical-byte or
  semantic-hash rules require separate specification work.
- The recognized Stage 1 envelope has six conceptual top-level members and a
  typed `body` with explicit collections, stable references, non-semantic
  array order, and present-even-when-empty core collections. No generic record
  union or machine schema file is activated by this revision.
- Source basis and semantic numeric-profile references are authored source
  semantics; operational resource/diagnostic profiles remain operation or
  fixture context. Readiness 2 checks shape/references and fixes the rigid
  carrier, while Readiness 3 freezes validity, normalization/sign, basis,
  ranges, conditioning, composition, and comparison semantics.
- Explicit omission and deterministic defaults are auditable: exactly one
  contract/profile rule owns a default, and resolved values carry stable
  `defaulted` provenance. Null, zero, neighbouring inference, and hidden
  equations cannot silently supply required values.

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
non-contractual debug information, while successful in-memory snapshot
finalization/handoff is reserved for complete valid-supported resolution.
External filesystem serialization remains a DR-0013 build/output operation.

### Define canonical bytes and hashes now

Canonicalization could support durable caching and identity immediately, but it
must be owned by the identity boundary rather than silently invented here. The
selected direction follows DR-0006's versioned project-owned canonical JSON
profile and domain-separated digest domains; exact framing and numeric rules
remain activation prerequisites. Deterministic debug JSON is still allowed.

### Use implementation-defined diagnostic codes or a universal catalogue

Implementation-defined codes would make independent clients and fixture
expectations incompatible; a large universal catalogue would freeze unused
surface area. The selected small versioned registry freezes only codes required
by the initial fixtures, with explicit profile extension and ordering rules.

### Defer the transform carrier until numeric semantics are frozen

That would leave the Readiness 2 schema unable to validate transform shape and
would force a knowingly disposable structural contract. The selected boundary
freezes translation plus `xyzw` quaternion structure at Readiness 2, then
activates DR-0011's canonical basis, numeric/sign, ranges, conditioning, and
typed comparison profiles at Readiness 3.

### Use a bespoke fixture-admission ledger

This would make expected snapshots and parser fixtures depend on a custom
active-pointer protocol and could make the manifest bind to itself. The
selected boundary uses one generic fixture-suite payload manifest and a
separate readiness/decision record carrying the reviewed manifest digest,
scoped payload identity, and Ben approval; Git history preserves successors.

### Use a generic body-record union

A generic union would shorten the first schema but make ownership, stable
references, and collection-specific validation ambiguous. Explicit typed
collections keep the Stage 1 grammar closed and make array order irrelevant.

### Treat omission as an implicit value

Implicit zero, null-as-missing, or inferred neighbouring values would erase
authored intent and make defaults dependent on parser or traversal behaviour.
Only one contract/profile-owned default rule may resolve a missing value, with
stable `defaulted` provenance; otherwise the value is required explicitly.

### Delegate numeric admission to the JSON host parser

That would make intermediate precision, locale, ambient rounding mode,
subnormal handling, and overflow behavior parser-dependent. Exact decimal-
rational interpretation followed by direct correctly rounded binary64
conversion keeps source admission reproducible across resolver
implementations. Requiring exact binary64 representability would instead
reject ordinary authored values such as `0.1` without improving semantic
determinism.

### Tune one epsilon or cluster claims by traversal order

A single epsilon cannot express the different error meanings of scalar,
translation, rotation, and transform residuals. Approximate equality is
non-transitive, so first-winner or transitive clustering would make source
resolution depend on array order. The selected typed profiles require all
unordered claim pairs to pass and retain all provenance before choosing a
canonical representative.

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
DR-0013. The latter two are cross-links, not additional DR-0012 decisions. The
fresh current Double review of Revision 5 was complete at target commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`: [review 01](reviews/DR-0012-rev-05-review-01.md)
recommended **Revise** at **High** confidence and [review 02](reviews/DR-0012-rev-05-review-02.md)
records **Ready for owner disposition** at **Medium** confidence with no
DR-0012-specific blocker. Applicable consolidated findings are C1 and C4; C2,
C3, and C5–C7 remain cross-cutting evidence owned by the linked records,
chiefly DR-0002/DR-0013. At that historical Revision 5 state, all seven
consolidated findings awaited Ben's discussion and owner disposition; review
completion was evidence, not a clean review or acceptance. Batch 9/10
discussion later resolved the applicable findings, while the current Revision
7 remains pending its fresh review. Exact serialized field spellings,
diagnostic codes, concrete thresholds, dependency-revision semantics,
canonical axes/units/rotation/scale/shear, conditioning/comparison
tolerances, canonical bytes/hashing, and fixture/security evidence remain
deferred. Those Revision 5 artifacts and findings are preserved as stale
historical evidence after the material Revision 6 change and did not satisfy
the then-pending current-revision review. The Batch 9 resolutions add the
in-memory snapshot finalization/handoff and operation-contract distinction,
absent-module declaration identity, and the DR-0013 build/output boundary.

The fresh current Batch 9 Double review examined exact target commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`: [review 01](reviews/DR-0012-rev-06-review-01.md)
recommended **Accept** at **High** confidence under the contract/schema,
determinism, and security lens, and [review 02](reviews/DR-0012-rev-06-review-02.md)
recommended **Accept** at **Medium** confidence under the platform/failure,
reversibility, and publication lens. No consolidated finding C1–C5 is
actionable against DR-0012 in this review. Review completion is evidence only;
there is no clean-review or acceptance implication. At that historical Revision
6 state, any cross-cutting findings recorded in the linked reviews awaited
Ben's discussion and owner disposition; Batch 10 discussion later resolved the
applicable findings. The current Revision 8 still requires fresh review and
owner disposition. Owner approval remains Pending and Status remains Proposed.
Only Ben may accept or reject this proposal.

The Batch 10 revision was discussion-approved by Ben on 2026-08-12. The
Revision 7 review artifacts above are stale historical evidence after this
material Revision 8 resolution. The prior fresh Batch 10 Double review examined
commit
`f27008f319cfc460f4a27efe31594e5607e7721e`: [review 01](reviews/DR-0012-rev-07-review-01.md)
recommended **Revise** at **High** confidence under the contract/schema,
determinism, identity, security, and fixture-admission lens; [review 02](reviews/DR-0012-rev-07-review-02.md)
recommended **Revise** at **High** confidence under the platform/filesystem,
publication, reversibility, numeric-frame, and runtime-portability lens.
The prior consolidated findings **C3 (High)** and **C4 (High)** are resolved in
this Proposed revision: frame roles are typed by owning record, Readiness 2
freezes the structural rigid-transform carrier, and Readiness 3 freezes numeric
semantics and admits expected graph snapshots through a manifest successor with
path, digest, comparison-profile identity, and exact/semantic comparison rule.
Exact profile identifiers, numeric constants, bytes, and comparison profiles
remain activation prerequisites. Ben's resolution is discussion approval, not acceptance. Review
status is Complete for the new current revision after the Double review below;
Owner approval remains Pending and Status remains Proposed. Only Ben may accept
or reject this proposal.

The fresh current-revision Double review examined exact target commit
`28c83c7a21cf55f23274aeaf5d2ccc0a3e9e3b53`. [Review 01](reviews/DR-0012-rev-08-review-01.md)
used the contract/schema, identity, determinism, security, and fixture-admission
lens and recommended **Accept** at **High** confidence with no DR-0012-specific
finding. [Review 02](reviews/DR-0012-rev-08-review-02.md) used the platform,
failure, reversibility, numeric-frame, adapter-portability, and future-runtime
lens and recommended **Revise** at **High** confidence. It identifies a
High R2/R3 wording conflict: Readiness 2 already freezes the rigid transform
carrier, while Readiness 3 must own numeric/frame semantics rather than reopen
the rotation representation. Consolidated **C1 (High)** applies to DR-0011 and
DR-0012 with a DR-0013 readiness cross-link. Both were fresh, independent
`gpt-5.6-sol` medium passes. The current review is evidence only; the proposal
remains Proposed with Owner approval Pending and no activation follows.

Ben approved the Batch 11 canonical-data and diagnostic-registry/profile
resolutions in discussion on 2026-08-12. This Revision 9 proposal adds the
cross-linked canonical JSON/digest direction, the versioned diagnostic registry
and profile boundary, and their proof obligations. The Revision 8 review
artifacts are stale historical evidence. The fresh current-revision Double
review examined exact target commit
`053dba58fd344ed636420e0974cf617862fe265f`: [Review 01](reviews/DR-0012-rev-09-review-01.md)
and [Review 02](reviews/DR-0012-rev-09-review-02.md) were independent fresh
`gpt-5.6-sol` medium passes; both recommend **Revise** at **High** confidence.
Actionable findings remain for Ben's discussion, including numeric admission,
diagnostic bootstrap, comparison, adapter, and Readiness 3 binding
cross-links. Review status is Complete for evidence only; Owner approval
remains Pending, Status remains Proposed, and no acceptance or activation
follows.

The Batch 11 current-revision review artifacts for Revision 9 are now stale
after this Revision 10 proposal change. Their exact findings are preserved
here for the next review. Review 01 recorded: **C1 — High:** “Canonical JSON
sorting by semantic address is incomplete for module declarations, owner-role
records, and manifest/build collections that may lack one of the seven
address kinds. Define a total canonical key and duplicate/tie handling for
every unordered collection/projection before `ck-json-1` activation.” **C2 —
High:** “Decimal-to-binary64 admission is ambiguous (`0.1`, midpoint,
excessive precision, subnormal/underflow, and overflow). Select exact
conversion/rounding and rejection behaviour with boundary fixtures.” **C3 —
High:** “R2/R3 payload binding excludes implementation bytes and mutable commit
provenance is insufficient against merge/rebase activation of unreviewed
parser/resolver code. Add a separately verified immutable implementation
path/mode/content binding or exact tree identity, checked after merge before
the ledger trigger.” **C4 — High:** “Canonical and DR-0012 diagnostic domain
vocabularies conflict, and unknown required registry/profile revisions need a
bootstrap profile or reserved-envelope diagnostic so the primary remains
contract-valid. Reconcile one domain mapping and bootstrap negotiation
diagnostics.” Review 02 recorded: **N1 — High:** “Define exact
decimal-to-binary64 conversion/rounding, overflow/underflow/subnormal
behaviour, and boundary fixtures at admission.” **N2 — High:** “The
numeric-threshold experiment is circular without semantic error budgets, an
independent oracle, held-out/adversarial data, sensitivity analysis, and
platform/toolchain diversity. Preregister domains/budgets and use higher-
precision or analytic oracle, development and held-out corpora,
metamorphic/conditioning/FMA/optimization coverage, a materially different
architecture/toolchain, and validation margins.” **N3 — High:** “Typed
comparisons need normative formulas, norms, quaternion/transform metrics,
inclusive boundary/tie behaviour, deterministic order-independent multi-claim
satisfiability, and non-transitivity safeguards; add permutation and
non-transitivity fixtures.” **N4 — Medium:** “Host-engine adapter conversion needs a future
conformance obligation for handedness reflection, vector/rotation/rigid-
transform basis change, named-direction preservation, composition commutation,
round trip, and binary64 narrowing policy before adapter activation.” The
mechanical N5 header synchronization remains outside this scoped resolution.

The discussion-approved directions resolve C2 and N1–N4: exact rational
admission, fixed typed comparison algorithms and pairwise conflict semantics,
the pre-registered experiment/oracle/corpus method, and the future adapter
conformance/narrowing obligation are now stated above. C1, C3, and C4 remain
unresolved and are not silently accepted or activated by this revision.

The fresh current-revision Batch 12 Double review examined exact target commit
`730a2f77840cc0caa1f838c30dac4ff20f985e69`: [Review 01](reviews/DR-0012-rev-10-review-01.md)
and [Review 02](reviews/DR-0012-rev-10-review-02.md) were complete-coverage,
independent fresh `gpt-5.6-sol` medium passes. Both recommend **Revise** at
**High** confidence. Review 01 records unresolved A1–A3 comparator/identity
findings and the mechanical A4 summary correction; Review 02 records unresolved
E1 runtime-`asin` and E3 floating-point-scope findings plus the mechanical E4
summary correction. The positive unit-scale adapter finding E2 is recorded in
the DR-0013 platform review. Review status is Complete for evidence only; C1,
C3, and C4 remain unresolved; Owner approval remains Pending and Status remains
Proposed. No parser, resolver, readiness gate, or package is accepted or
activated by this revision.

Ben approved all five Batch 13 resolution directions in discussion on
2026-08-13. Revision 11 integrates symmetric same-target comparison in the
canonical local-to-parent frame, exact dyadic scalar/half-chord arithmetic and
offline conservative `H`, deterministic quaternion normalization and authored
claim identity, typed collection keys/multiplicity, the separate scoped
implementation-content binding, the post-R3 adapter `C`/`s` two-tier boundary,
and the diagnostics sole-owner/bootstrap rule. The Revision 10 Batch 12
artifacts are stale for this material revision; their findings and history are
preserved. Review status is Complete for the current evidence and Owner
approval remains Pending. No DR acceptance, schema, fixture, parser/resolver,
implementation, adapter, experiment, or package activation follows.

The fresh current-revision Batch 13 Double review examined exact target commit
`8c38c501eb1262a1b85af0b8605220625601772f`. [Review 01](reviews/DR-0012-rev-11-review-01.md)
and [Review 02](reviews/DR-0012-rev-11-review-02.md) were complete-coverage,
independent fresh `gpt-5.6-sol` medium passes with no edits; both recommend
**Revise** at **High** confidence. Review 01 records unresolved **D1–D3**:
the half-chord bound's normalization proof gap, incomplete mechanically
checkable implementation-binding closure, and underspecified versioned
claim-ID components/order/stable authored property address. Review 02 records
unresolved **P1–P3**: symlink/special-file/ancestor no-follow rules, possible
post-normalization `-0` changes to canonical bytes, and missing malformed /
unsupported / conversion-failure adapter status distinctions. Findings remain
cross-linked to the DR-0006, DR-0011, DR-0013, diagnostics, and
fixture-manifest owners. Review status is Complete for evidence only; Owner
approval remains Pending and Status remains Proposed. No parser, resolver,
diagnostic profile, readiness gate, adapter, fixture, implementation, or
package is accepted or activated by this review.

The Batch 13 findings were dispositioned in the prior Revision 12 as follows.
D1 was resolved by the canonical-tuple Euclidean `H` contract with no
represented-angular guarantee. D2 and P1 were resolved by the explicit
implementation closure and filesystem-safe root-descriptor/no-follow profile
owned by DR-0006, DR-0013, and the fixture-manifest specification. D3 was
resolved by conceptual typed `claim-id-1` with stable record address, typed
property role, and explicit multiplicity. P2 was resolved by the produced-zero
`+0` rule owned by DR-0011. P3 was previously described as resolved by the
build-operation/platform adapter status mapping; Revision 13 corrects that
disposition and records malformed adapter-profile validation as a deferred
adapter-activation prerequisite. The prior reviews remain stale evidence;
at Revision 13, review status was Pending and that Proposed revision activated
no parser, resolver, schema, adapter, or fixture machinery.

The fresh successor-target reviews are [Review 01](reviews/DR-0012-rev-12-review-01.md)
and [Review 02](reviews/DR-0012-rev-12-review-02.md). They are exact-target
evidence for Revision 12 only and are stale for this Revision 14 successor.
Their G1/G2 mechanical findings were fixed in the successor; T1–T3 were
resolved here, while T4/P3 is explicitly deferred until adapter activation and
is not a first Rust slice blocker. At that stage, the Revision 14 current
review was still pending; no acceptance or activation followed.

The final Double-review [Review 01](reviews/DR-0012-rev-13-review-01.md) and
[Review 02](reviews/DR-0012-rev-13-review-02.md) examined exact target commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` and are stale for this successor.
Revision 14 corrects the comparator/rank-table and sqrt wording and preserves
T4 as a deferred retained-human gate; the then-pending successor review is
recorded below.

The current-revision Double review examined exact target commit
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`: [Review 01](reviews/DR-0012-rev-14-review-01.md)
records governance findings G3/G4 as mechanical cross-summary corrections
handled without material DR revision, and [Review 02](reviews/DR-0012-rev-14-review-02.md)
records no technical findings and recommends **Ready for PR**. These artifacts
are exact-target current evidence until a successor revision. Review status is
Complete for evidence only; Owner approval remains Pending, Status remains
Proposed, and no source encoding, parser, resolver, schema, fixture, adapter,
implementation, or package is accepted or activated.

## Implementation and Proof Obligations

- Define the exact source fields and paired JSON Schema Draft 2020-12 while
  preserving the source/model/snapshot boundary and resolver ownership of
  semantics.
- Encode the exact conceptual Stage 1 top-level members `contract`, `source`,
  `basis`, `profiles`, `body`, and `extensions`; make `contract` the
  version-neutral family/revision owner and keep core members strict/closed.
  Define typed body collections for modules, parts, joints, sockets,
  attachments, landmarks, dimensions, frames, regions, capabilities, and
  fields, with stable references, non-semantic array order, and present-even-
  when-empty collections. Do not activate a machine schema file in this
  revision.
- Before canonicalization, require each unordered collection/projection owner
  to declare a typed total key and uniqueness or multiplicity rule: structured
  graph address; tagged module declaration address; tagged owner kind/address/
  role plus required frame/context/claim identity; fixture ID; normalized safe
  relative path with mode/content in the entry projection; dependency
  locator/role plus distinguishing revision; owner-defined build-array key;
  and profile-defined diagnostic occurrence key. Reject absent keys/rules and
  duplicate keys only for declared uniqueness collections. Preserve repeated
  claims, multisets, and diagnostics explicitly; never use source/traversal/
  allocation/index order, serialization, or raw element bytes as fallback.
- Bind Readiness 2/3 implementation activation separately from the fixture
  payload to a versioned ordered normalized relative path/mode/raw-content set
  and aggregate SHA-256 covering gate-affecting source, manifests/config,
  scripts/inputs, `Cargo.lock`, toolchain declaration, and applicable path
  dependencies. Recompute both bindings post-merge and immediately before the
  trigger; mismatch blocks activation and requires a successor. Commit
  provenance is not equality binding, and whole-repository/custom-ledger
  binding is not selected.
- Require source basis (length unit, handedness, up, forward), owner/role and
  frame/context on measurements and transforms, and initially no per-value
  unit overrides. Bind `profiles` to the versioned semantic numeric-domain
  profile; keep operational profiles in operation/fixture context.
- After strict JSON and number-token resource checks, interpret each number
  token as an exact signed decimal rational and convert directly to binary64
  round-to-nearest/ties-to-even. Do not use host-parser intermediates, locale,
  ambient rounding modes, or implementation-defined precision. Reject
  non-finite/overflow results and nonzero rationals that round to signed zero;
  accept finite nonzero subnormals and excessive lexical precision within the
  resource bound. Normalize lexical negative zero only in semantic/canonical
  models, preserve source-byte distinction, and prohibit FTZ/DAZ in canonical
  operations. Normalize every produced zero to `+0` after
  admission/conversion, composition, inversion, quaternion normalization/sign,
  tuple formation, adapter conversion, and narrowing, before comparison or
  serialization; permitted nonzero-to-zero narrowing emits `+0`, and raw
  lexical `-0` remains distinct only in raw-source identity.
- Implement DR-0011's normative comparisons: normalize same-target transforms
  to one canonical local-to-parent frame and compare translations directly;
  keep residual transforms only as separately named diagnostic/composition
  comparisons. Decide scalar/component bounds over exact dyadic values with
  bounded integer arithmetic. Compare rotations by exact dyadic dot-sign and
  the inclusive canonical-tuple Euclidean half-threshold `H`; after
  deterministic normalization, the tuple-distance predicate uses no square
  root, norm, `asin`, or `sin`, while normalization itself uses the required
  correctly rounded binary64 square root. A nominal theta is
  informational/calibration metadata only, not an angular guarantee. Any future
  angular guarantee requires a new comparison-profile revision and successor
  evidence.
  Normalize source quaternions with fixed max-component scaling, operation
  order, correctly rounded sqrt, drift/near-zero validation, canonical sign,
  RN ties-even, and no FTZ/DAZ/ambient mode. Require structured authored claim
  identity, reject same-ID/different-value collisions, evaluate pairs in sorted
  claim-ID order with the first failing pair as detail, and select the exact
  smallest normalized tuple only after all pairs pass while retaining all
  occurrences/provenance.
- Keep Readiness 2 structural shape/reference checking only and freeze its
  rigid transform carrier as three-component translation plus explicit
  four-component `xyzw` quaternion, without scale or shear fields. At Readiness
  3 activate DR-0011's canonical basis, numeric/sign, ranges, conditioning,
  and typed comparison profiles; admit expected graph snapshots through a
  manifest successor with
  path, digest, comparison-profile identity, and exact/semantic comparison
  rule.
- Specify omission/default rules: identity, containment, module presence,
  source basis, and grammar-required values are explicit; exactly one
  contract/profile-owned deterministic default may resolve a missing value and
  must record stable `defaulted` provenance and rule identity. Reject
  null-as-missing, implicit zero, neighbouring inference, and hidden
  equations; permitted omission means empty only where the contract says so.
- Implement duplicate-key rejection, strict UTF-8 and one-document admission,
  and rejection of comments, includes, evaluation, and unknown core fields.
- Define extension-envelope field spelling, namespace/revision handling,
  required-versus-optional outcomes, opaque preservation, and core semantic
  isolation.
- Define the diagnostics specification as sole owner of registry, domain,
  class, occurrence, profile, ordering, and compatibility. Its versioned
  registry/profile carries stable code, class, phase, severity, optional source
  path/offset, optional typed semantic address, typed details, profile revision,
  extension/order/truncation rules, and non-compatibility human text. Use the
  closed domains source-admission, dependency, semantic-identity,
  graph-structure, frame-numeric, resource, execution-trust, publication, and
  inspection, with resolver-invariant and worker-protocol stable classes.
  Keep resource profiles separate. A tiny mandatory bootstrap registry/profile
  handles unknown required profile/revision via existing `unsupported`, an
  effective bootstrap profile, bounded requested identifiers, and a
  deterministic primary; never emit under an unknown profile or silently
  downgrade. Keep exact ordinary codes, field spellings, and profile IDs
  fixture-gated. Define the closed status set and total final-status selection
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
  fatal dependency blocking, in-memory snapshot finalization/handoff required
  by successful `resolve`, operation-specific snapshot omission such as
  `validate`, and provenance for authored/defaulted/derived values and
  derivation source addresses. External filesystem serialization belongs to
  DR-0013 and maps its failures to `output-failure`.
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
- Prove that an absent optional module has a stable authored declaration
  address and non-embodied root-role/template reference, emits or reserves no
  Part, cannot be targeted by a graph relation, participates in declaration
  uniqueness rather than the Part namespace, and derives a present Part's
  identity from the instance anchor plus root role.
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
- Pre-register numeric domains and semantic error budgets before results; use
  fixed operation order and round-to-nearest/ties-to-even with no
  reassociation, implicit FMA contraction, or FTZ/DAZ. Compare exact/analytic
  and independent materially higher-precision oracles over separate frozen
  development, held-out, and adversarial corpora, record sensitivity and
  conditioning, exercise metamorphic/permutation/conditioning cases, and use
  a predeclared validation margin. Reject out-of-domain cases rather than
  widening budgets or selecting the smallest observed error. The bounded
  initial reference is WSL x86_64 plus native Linux; broader portability needs
  materially different architecture/toolchain evidence.
- Before any host adapter activates, require the post-R3 profile's orthogonal
  signed-permutation `C`, positive scale `s`, target precision, domain,
  narrowing/overflow/underflow/subnormal policy, and storage-only or
  runtime-conformance tier. Map length-bearing values with `sC/s`, directions
  and normals with `C`, rotations with `C*R*C^-1`, and rigid transforms with
  `D*H_c*D^-1`, `D=diag(sC,1)`, including inverse `D^-1` and quaternion
  equivalence. Runtime-conformance adds arithmetic probes/fixtures; the
  minimal tier makes no runtime claim. Probe FTZ/DAZ for subnormal runtime
  preservation, fail unsupported capabilities closed, map trusted in-domain
  overflow/disallowed underflow to `output-failure`, and keep binary64 core
  snapshots unchanged. Adapter activation is separate after Readiness 3 and
  does not select an engine.
- Defer only exact profile identifiers, numeric thresholds/conditioning,
  diagnostic code membership, dependency-revision semantics, canonical-byte
  framing, and future migration details to their owning specification work.
  The canonical basis, finite binary64/quaternion direction, typed comparison
  profiles, diagnostic registry/profile boundary, and domain-separated digest
  direction are now proposed and must not be silently replaced by
  implementation-defined behaviour.

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

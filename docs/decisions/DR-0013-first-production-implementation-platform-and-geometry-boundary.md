# DR-0013: First production implementation platform and geometry boundary

ID: DR-0013

Scope: Specification and architecture

Status: Proposed

Revision: 12

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-11

Date decided: —

Discussion approval date: 2026-08-13

Supersedes: —

Superseded by: —

## Context

Creature Kernel is moving from disposable geometry exploration toward a first
production semantic/compiler core. The CK-KICK-012 body-document and body-graph
proposals define an engine-independent semantic boundary, but they do not
select an implementation language, build system, geometry backend, process
model, or visual workbench. The exploratory host in CK-KICK-009 and the
CK-KICK-010 walking skeleton are evidence and tooling, not production platform
commitments.

The first platform must make the semantic contract executable, headless, and
reproducible without turning an exploratory visual tool or a game engine into a
hidden compiler dependency. It must also leave a credible path for geometry
capabilities that may not fit the first implementation language. Stage 1 needs
an executable geometry proof, but that proof must not silently settle the
permanent surface, topology, or runtime architecture.

The build operation, artifact staging, inspection, and publication boundary
requires a canonical build-operation specification. The canonical
`spec/build-operation/README.md` owns the exact Proposed build-operation
contract, including field spelling and format. This record assigns the
operation and publication responsibilities without inventing that canonical
serialized contract. DR-0006 owns candidate versus committed artifact
identity and lineage at the identity level. Ben's 2026-08-12 Batch 10
discussion approval adds the initial filesystem safety profile, artifact
inspection status algebra, worker/report trust separation, immutable fixture
admission lifecycle, and the stable request/artifact identity consequences.
Ben approved the current-review C1, C2, C4, and C5 resolutions on 2026-08-12:
deterministic committed identity excludes attempt data, fixture admission uses
a generic payload manifest plus separate readiness/decision record, Readiness 2
freezes a rigid-transform carrier, and worker status mapping is explicit. The
filesystem proof remains a nonblocking pre-publication obligation. This
material Revision 6 change makes the Revision 5 current-review artifacts stale;
the record remains Proposed with Owner approval Pending and a fresh current
review pending. On 2026-08-12 Ben approved the next machine-contract batch:
semantic address encoding, canonical basis/numeric/comparison profiles,
canonical bytes/digests, and the diagnostic registry/profile. This material
Revision 7 change makes the Revision 6 review evidence stale; a fresh current
review is pending. On 2026-08-12 Ben discussion-approved the four numeric
resolution directions from the Batch 11 review: exact decimal admission,
normative comparisons, a non-circular numeric experiment method, and future
adapter conformance. This is not DR acceptance or readiness activation.
Revision 8 makes the Revision 7 current-revision review artifacts stale; their
exact findings are preserved below. C1 canonical collection ordering/tie
handling, C3 immutable Readiness 2/3 implementation binding, and C4
diagnostic-domain/bootstrap compatibility remain unresolved for the next
discussion in their owning records. Owner approval remains Pending and Review
status is Complete for the current Batch 12 evidence; the proposal remains
Proposed.

On 2026-08-13 Ben approved all five CK-KICK-012/013 Batch 13 resolution
directions in discussion: symmetric canonical-frame comparison with exact
dyadic boundary arithmetic and deterministic quaternion normalization;
post-R3 adapter units and storage-only/runtime-conformance tiers; typed total
keys and explicit multiplicity for unordered manifest/build/projection
collections; a separate scoped implementation-content binding for readiness
transactions; and diagnostics sole ownership with a mandatory bootstrap
registry/profile. This material revision is Proposed only: it accepts no DR
and activates no schema, fixture, parser/resolver, implementation, adapter,
experiment, or package. The Revision 8 Batch 12 review artifacts are stale for
this change and remain preserved below. Owner approval remains Pending and
Review status is Pending pending a fresh current-revision review.

On 2026-08-13 Ben approved the four Batch 13 platform-resolution directions
for this record in discussion: canonical-tuple comparison without an angular
guarantee; explicit `+0` production-stage normalization; mechanically closed
and filesystem-safe readiness implementation binding; and adapter status
mapping with proof/fixture obligations. This Revision 10 records those
settled directions as Proposed only. It creates no Cargo shell, schema,
fixture, parser/resolver, readiness gate, implementation, adapter, experiment,
or package. The Batch 13 Revision 9 review is stale evidence after this
material revision and remains preserved below; Owner approval remains Pending
and a fresh current-revision review is required.

On 2026-08-13 the fresh technical-review dispositions were applied in the
Revision 11 proposal: build requests now reference the exact implementation-
content-binding and dependency-closure identities used for execution; the
wire-independent `claim-id-1` comparator and normalized identifier ordering
are explicit; numeric wording distinguishes required-sqrt quaternion
normalization from the already-normalized tuple-distance predicate; and
malformed adapter-profile status mapping is deferred to the adapter-activation
prerequisite rather than treated as source admission. The exact-target Double
review at commit `9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale for this
Revision 12 successor. Revision 12 applies the mandatory rank-table activation
gate and preserves the retained-human T4 gate; fresh successor-target review
is pending. This technical correction preserves the Proposed status, Owner
approval Pending, and Review status Pending.

## Decision

This is a proposed first-production platform boundary. Readiness 1 through
Readiness 4 below are technical gates, not approval ceremonies. They state the
conceptual owner, authoritative prerequisite, and evidence; exact ledger field
spelling may remain in project documentation. No Readiness gate is activated by this
Proposed record.

| Readiness stage | Sole trigger and technical action | Authoritative prerequisite/owner | Evidence concept |
| --- | --- | --- | --- |
| Readiness 1 — empty production shell | DR-0013 is Accepted; create the Cargo workspace and empty compiler/library/CLI shell | DR-0013 acceptance and this platform boundary | Workspace and empty shell exist; no parser, resolver, fixture, or geometry implementation is implied |
| Readiness 2 — parser/bootstrap and admitted fixtures | One exact activation transaction on a review branch containing the exact JSON Schema, a versioned fixture manifest, all referenced fixture files, and parser/bootstrap implementation | DR-0012 owns schema/bootstrap; DR-0002/DR-0008/DR-0011 own linked semantic fixture obligations; Ben owns admission | Parser-independent preflight proves manifest, paths, hashes, profiles, expected outcomes/diagnostics, provenance, and completeness agree before explicit Ben approval and merge/activation |
| Readiness 3 — semantic resolver and snapshot handoff | A distinct Ben-approved successor transaction activates DR-0011's canonical basis, validity, normalization/sign, ranges, conditioning, composition, and typed comparison semantics plus frozen expected graph outputs; it then activates semantic resolution and successful in-memory snapshot finalization/handoff without reselecting the Readiness 2 carrier | DR-0011 owns frame/numeric prerequisites; DR-0002/DR-0012 own graph and result-envelope obligations | Resolver outputs match frozen expected graph snapshots with provenance and trusted success envelope; external serialization remains a later build/output operation |
| Readiness 4 — exploratory Stage 1 geometry proof | Working resolver plus a provisional geometry profile and project-owned GeometryRequest/GeometryResult seam; activate exploratory Stage 1 geometry proof / CK-KICK-014 | DR-0013 owns the seam/platform; DR-0008 owns Stage 1 claim boundary | Bounded exploratory proof evidence under the provisional profile; no accepted/reactivated surface decision is required |

Readiness 2 admission is one exact activation transaction on a review branch:
the schema, a versioned manifest, every referenced fixture file, and the
parser/bootstrap implementation may coexist there, but merge or activation
occurs only as one transaction. Ben is the admission owner and must explicitly
approve before merge/activation. A generic/parser-independent preflight checks
paths, hashes, profile references, expected status and primary diagnostics,
provenance, and completeness. The manifest requires an immutable revision/ID,
schema revision/hash, fixture paths/hashes/provenance, expected status and
primary diagnostic, diagnostic/resource profile IDs, and completeness. The
production parser must not self-admit the corpus circularly.

The fixture-suite manifest is a payload, not an admission ledger: it contains
suite kind, fixture paths, content hashes, profile IDs, expected results or
diagnostics/snapshots as applicable, and provenance, but never its own digest or
approval. A separate later readiness/decision record, outside the payload
digest domain, names the reviewed manifest digest, source commit reference,
and exact ordered path/mode/content set digest for the manifest plus its
declared schema, fixtures, and snapshots, and Ben approval. Readiness,
approval, successor, and mutable-pointer records, plus Git commit identity,
are excluded from that payload scope; the digest algorithm/profile is recorded.
After merge,
parser-independent preflight is rerun; commit identity may change, but
activation requires the manifest and path-scoped payload binding to match.
Git history and explicit successor, deactivation, or rollback records preserve
history; no custom append-only active-pointer ledger is required. Preflight
proves internal consistency only. Expected-result correctness is a reviewed
contract or hypothesis and later executable evidence; hashes do not prove it.

Fixture payload binding is deliberately separate from implementation binding.
Each readiness transaction that activates implementation also carries an
external, domain-separated, versioned ordered normalized relative path/mode/
raw-content set and aggregate SHA-256. The closure is explicit and
mechanically checkable. The implementation-content binding owns selected
repository paths, modes, and raw contents: selected Rust/Cargo production
sources and workspace/crate manifests, repository Cargo configuration or
recorded absence, `Cargo.lock`, rust-toolchain declaration, build scripts, and
declared compile/code-generation inputs. Dependency closure separately owns
registry, vendored, path-dependency, and proc-macro provenance/content.
Build-request identity separately owns selected packages, targets, target
triple, features, profile, approved environment/tool/configuration inputs, and
the exact locked/offline command. The activation closure manifest binds or
references all three. Reviewed commit provenance is evidence, not equality
binding; generic host/rustc/hardware metadata is evidence unless a
platform-reproducibility claim binds it. Opaque Git/native/codegen inputs
require a reviewed vendored snapshot escalation. Binding, dependency closure,
build-request identity, attempt identity, and fixture payload binding remain
distinct. Locked/offline preflight reads a private read-only activation
snapshot rooted at an opened repository descriptor and uses descriptor-
relative no-follow reads. It rejects traversal, absolute paths, symlinks,
special files, and submodules in entries or ancestor components. Ancestors are
descriptor-opened no-follow directories; a final regular-file entry is
rejected when `st_nlink != 1` and is eligible only with mode `100644` or
`100755`. Descriptor
identity, type, and size are checked consistently; normal directory hardlink
counts are not rejected. This is proportional to the current hobby threat
model, not a general sandbox. Post-merge and immediately before the trigger,
recompute implementation and dependency content from a fresh immutable snapshot
and revalidate the exact bound build request; mismatch blocks activation and
requires an explicit successor. This Proposed direction does not claim the
preflight or snapshot machinery is implemented.

All unordered manifest, fixture, dependency, and build projections declare an
owner-defined typed total key and uniqueness or multiplicity rule before
activation. Use fixture ID (duplicate ID/path invalid), normalized safe
relative path with mode/content in the entry projection, dependency locator/
role plus distinguishing revision, and an owner-defined key for other build
arrays. No source/traversal/allocation/index order, serialization, or raw
element bytes is a fallback; legitimate repeated claims/multisets and
diagnostics retain explicit occurrence identity.
A generic fixture-suite manifest/admission mechanism covers parser/body-
document, semantic-graph, and build/publication suites. The canonical
fixture-manifest specification owns exact Proposed manifest semantics; this
record owns the admission and activation boundary.

Readiness 2 freezes one structural rigid-transform carrier for parser/schema
work: three-component translation plus explicit four-component `xyzw`
quaternion, with no scale or shear fields. Readiness 2 validates carrier shape
and references only; it does not infer canonical numeric semantics. Readiness 3
activates DR-0011's canonical basis, validity, normalization/sign, ranges,
conditioning, composition, and typed comparison semantics. Its distinct
Ben-approved successor transaction contains the successor suite manifest,
expected graph snapshots, comparison profile/rule, and resolver implementation
or exact implementation binding, with the same content-identity preflight.
The repository-evolution ledger marks this transaction activated only after
that explicit Ben approval and unchanged content preflight; no package or
resolver gate activates before the ledger trigger. It binds an expected graph
snapshot path, digest, comparison-profile identity, and exact or semantic
comparison rule. This boundary selects no geometry, rig, IK,
deformation, runtime, or host-engine representation.

### Numeric readiness and future adapter boundary

Readiness 3 consumes DR-0011's numeric contract; it does not select an engine
or permit an adapter to redefine canonical semantics. After strict JSON and
number-token resource checks, source number tokens are exact signed decimal
rationals converted directly to binary64 with round-to-nearest, ties-to-even.
Host-parser intermediates, locale, ambient rounding modes, and
implementation-defined precision are not permitted. Finite nonzero subnormals
are accepted, overflow to infinity and nonzero rationals that round to signed
zero are rejected, and excessive precision within the lexical/resource bound
has no arbitrary semantic digit limit. Lexical negative zero is accepted but
normalized to positive zero for semantic/canonical models; exact source bytes
remain distinct, and canonical operations prohibit FTZ/DAZ. Every semantic
numeric-producing stage normalizes produced zero to `+0` after
admission/conversion, composition, inversion, quaternion normalization/sign,
tuple formation, adapter conversion, and narrowing, before comparison or
serialization. A permitted nonzero-to-zero narrowing emits `+0`; raw lexical
`-0` remains distinct only in raw-source identity.

Readiness 3 comparison uses exact discrete identity. Same-target transforms are
first normalized into one canonical local-to-parent frame and translations are
compared directly componentwise; swapping claims gives exactly the same
outcome. Residual `E = B * inverse(A)` is only a separately named
diagnostic/composition comparison, never authored same-target equality.

The inclusive scalar predicate is decided over exact dyadic values decoded
from admitted finite binary64 values with bounded integer/dyadic arithmetic.
The rotation profile stores finite binary64 half-chord threshold `H`: choose q
sign by exact dyadic dot (`0` -> `+1`), compute `di=qa_i-s*qb_i`, and accept iff
`sum(di^2) <= (2H)^2` exactly and inclusively. `H` is the finite binary64
post-normalization Euclidean half-threshold in canonical quaternion tuple space. A
nominal `theta`, if retained, is informational/calibration metadata only; this
platform boundary does not claim that `H` or `theta` bounds represented angular
error. A future represented-direction or angular guarantee requires a new
comparison-profile revision and successor evidence. After deterministic
quaternion normalization, the already-normalized tuple-distance predicate uses
no square root, norm, `asin`, or `sin`; normalization itself uses the required
correctly rounded binary64 square root specified below.

Normalize source quaternions with exact max-absolute-component scaling, fixed
`xyzw` divisions, fixed left-to-right squared sum without reassociation/FMA,
correctly rounded binary64 square root, fixed divisions, drift/near-zero
validation, and first-nonzero `wxyz` positive sign. Require RN ties-even, no
FTZ/DAZ, and no ambient mode; unsupported platforms cannot provide this sqrt.
Every unordered claim pair must pass. Conceptual versioned `claim-id-1` is the
structured tuple of canonical target, closed claim kind, typed
source-document/namespace identity, stable authored record address, typed
property role, and explicit authored claim key or absence. Its wire-independent
total order is owned by the [semantic-address profile](../../spec/semantic-address/README.md):
the canonical target uses its structured address order; closed claim kind and
typed property role use profile-defined semantic tag ranks rather than wire
spelling; typed source-document/namespace identity and each address segment use
normalized identifier Unicode-scalar lexical order with structured
prefix-before-extension ordering; and absent claim keys precede present keys,
whose values use that same identifier order. An activated schema must
bijectively map wire values to these conceptual types/ranks and may not infer
order from wire spelling. Unordered pairs are `(min_id, max_id)`. It never uses
array/traversal/allocation/thread/time/generated index. Same ID and same
normalized value evaluates once while all occurrences/provenance remain; same
ID/different value is invalid-source identity collision. Different IDs use
all-pairs evaluation in this order, report the first failing pair, and only
then choose the lexicographically smallest exact finite-binary64 value tuple
(`-0` already `+0`), with claim ID breaking exact tuple ties only.
The claim-kind and typed-property-role rank tables are mandatory, versioned
activation inputs. Each table must be complete and injective over its admitted
closed set; a missing, duplicate, or unknown kind, role, or rank entry fails
activation. No canonical claim ordering, digest, or resolver activation may
occur before both tables exist, and wire spelling is never an ordering
fallback.

The numeric evidence gate pre-registers domains and semantic error budgets,
uses fixed operation order and round-to-nearest/ties-to-even without
reassociation, implicit FMA contraction, or FTZ/DAZ, and compares exact/
analytic and independent materially higher-precision oracles over separate
frozen development, held-out, and adversarial corpora. It covers metamorphic,
permutation, conditioning, and sensitivity cases, uses a predeclared
validation margin, and rejects out-of-domain cases rather than widening a
budget or selecting the smallest observed error. WSL x86_64 plus native Linux
is the bounded initial reference; materially different architecture/toolchain
evidence is required only before claiming broader cross-platform
reproducibility.

Before any host adapter activates, it declares orthogonal signed-permutation
`C`, finite positive scale `s` (engine length units per canonical metre), target
precision, supported domain, narrowing/overflow/underflow/subnormal policy, and
guarantee tier. Length-bearing points, positions, translations, displacements,
dimensions, radii, and extents map by `sC/s`; directions and normalized normals
by `C`; rotations by `C R C^-1`; and rigid transforms by
`D H_c D^-1`, `D=diag(sC,1)`, with inverse `D^-1`. Quaternion conversion is
derived from the rotation map or a proven equivalent. The minimal/default tier
promises storage/output conversion only; optional runtime-conformance adds
engine arithmetic/probes/fixtures. Binary32 may exclude subnormal-dependent
values; subnormal runtime preservation requires FTZ/DAZ probes. Failed required
capability is unsupported; trusted in-domain overflow/disallowed underflow is
output-failure. Core snapshots remain binary64 and unchanged; adapter
activation is separate and after Readiness 3.

Adapter status mapping reuses the existing statuses, but malformed adapter
request/profile mapping is deliberately unselected until adapter activation.
Adapter profile data is a build-request/target-platform input, not
authoritative body-source content. Before an adapter profile/schema activates,
Ben must explicitly dispose of the retained-human request-validation mapping,
and the owning build-operation/platform contracts must choose and review that
result mapping while preserving the closed operation status set (or explicitly
revising it). A well-formed unknown revision or unavailable
claimed capability remains `unsupported`; a violated already-admitted
project-profile invariant remains `internal-failure`; and valid supported
conversion overflow, disallowed underflow, or malformed output remains
`output-failure`. Until then no adapter activates and malformed adapter-profile
input is not classified as `invalid-source`/source-admission. Resource and
trust outcomes retain their existing precedence. Exact codes/field names
remain fixture-gated. This request-validation choice is
implementation/evidence-dependent and is not a blocker for the first Rust
slice. Proof obligations include malformed scale/profile,
unknown revision, unavailable capability, invariant violation, overflow,
disallowed underflow, malformed output, and precedence cases; no fixtures or
adapter activate here.

Acceptance of DR-0013 itself is the sole trigger for Readiness 1. Creating this
Proposed DR does not activate implementation packages, schemas, compiler
fixtures, or a production geometry commitment. Readiness 2 creates its
manifest-listed fixture files and parser/bootstrap implementation together in
the one admitted transaction; neither first compiler consumption nor an
unlisted fixture can activate it. Readiness 3 is separate from
parser/bootstrap and requires canonical frame/numeric rules plus frozen
expected graph outputs; successful `resolve` requires the in-memory snapshot
handoff, while external serialization remains a build/output concern.
Readiness 4 triggers exploratory Stage 1 geometry / CK-KICK-014. It does not
require acceptance or reactivation of parked DR-0009/DR-0010; those records
remain nonblocking and are needed only for later formal comparative surface
evidence or production architecture selection. The exploratory proof itself
requires no surface decision.

### Core language and workspace

Use stable Rust as the first production semantic/compiler core in a Cargo
workspace. The core is a library with engine-independent semantic resolution,
diagnostics, provenance, and artifact production boundaries. A thin CLI is the
first human/script entry point. The core and CLI must not require a game engine
or a visual workbench to perform headless compilation.

The initial implementation should keep public boundaries ordinary and
replaceable: semantic/compiler library, thin CLI, artifact/manifest writer,
and a replaceable geometry boundary. This record does not fix crate names,
public API syntax, source schema files, artifact field spelling, or package
serialization. No daemon or service is part of the first implementation.

### Geometry boundary and first proof

The project-owned geometry seam consists of versioned `GeometryRequest` and
`GeometryResult` concepts (names remain conceptual/provisional). The request
and result cover resolved graph and geometry intent, configuration and
capability metadata, semantic/artifact lineage, bounded diagnostics, and
bounded geometry outputs/results sufficient for the caller to validate the
operation. Backend-native or third-party library types must not leak through
the semantic, CLI, artifact, or host-engine contracts. The seam is a
replaceable project boundary, not a permanent surface or backend selection.
Stage 1 seam work may support CK-KICK-014, but it does not establish a
permanent surface choice and cannot claim DR-0009 or DR-0010 evidence.

Stage 1 geometry proof uses an in-process Rust CPU dense-field evaluator and
extractor behind the replaceable geometry boundary. This is a bounded proof
host, not a claim that Rust geometry is universally mature or that the chosen
dense-field/extraction method is the permanent surface architecture. It must
remain possible to compare or replace the geometry implementation without
rewriting semantic resolution or the CLI contract.

Rust-only geometry is not a permanent promise. If reproducible measurements, a
required capability, or a justified isolation, security, portability, or
licensing need exposes a credible in-process Rust boundary gap, evaluate an
isolated C++ worker/backend first. Consider in-process C ABI/FFI only if the
worker boundary is demonstrated insufficient for the required use. Any such
change requires evidence, a defined ownership and failure boundary, and the
appropriate later decision; it is not implied by this DR.

### Tooling and workbench

Python remains suitable for disposable experiments, evidence and render
tooling, and the visual workbench. Python is not a production compiler
dependency. An independent visual workbench consumes ordinary compiler
artifacts and their manifest; it does not own semantic resolution or silently
recompile the source through a second implementation.

The compiler publishes a complete success bundle using immutable,
build-scoped sibling staging, writes the manifest last, and atomically
publishes it with no replacement of an existing bundle. The manifest identifies
the build and artifact identity and records relative paths with hashes and
sizes. Consumers reject absolute or traversal paths, symlinked or unlisted
outputs, incomplete or mixed-build bundles, and stale bundles. These artifacts
are an initial inspection and workbench interchange boundary, not the final
avatar-package serialization or compatibility contract. Exact artifact names,
manifest field spelling, package bytes, and compatibility rules remain
deferred to later specification and decision work.

### Initial filesystem safety profile

The initial publication reference is a tested local Linux filesystem under
WSL `/home`. `/mnt/c`, network shares, removable filesystems, and unspecified
filesystem profiles are outside this initial reference. Staging is a sibling
on the same filesystem as the target. Publication probes that the required
atomic no-replace primitive is available, uses immutable committed outputs,
assumes cooperating concurrent builders, and inspects a collision winner
before deciding success or conflict.

The profile promises process-crash-safe namespace publication only. It does
not claim survival of sudden power loss; stronger synchronization and
durability belong to a later profile. Malicious or privileged concurrent
filesystem mutation is outside the initial threat model, although inspection
must still verify a complete artifact or reject it. The filesystem component
of candidate identity uses a profile-defined unambiguous safe-ASCII mapping;
the exact spelling and algorithm are activation prerequisites.

Artifact inspection is a separate read operation. It uses the shared envelope
conventions but never overwrites historical build status. Its closed results
are `success`, `absent`, `unavailable`, `mismatch`, `invalid-artifact`,
`unsupported`, `resource-limit`, and `internal-failure`: absent means no target;
unavailable means I/O or access could not establish a trustworthy read;
mismatch means expected lineage differs; invalid-artifact means malformed,
incomplete, tampered, or hash/size-inconsistent content; unsupported means an
unsupported manifest or profile revision; resource-limit means a configured
inspection resource interruption; and internal-failure means implementation or
trust loss. Inspection preserves processing and diagnostic completeness, uses
deterministic primary diagnostics and precedence, and selects the global
internal-trust result first, then a qualifying resource limit, otherwise the
earliest applicable inspection phase/status.

The initial Readiness 2 corpus is intentionally lean: a minimal valid
envelope; an optional absent module; a duplicate member; an invalid
discriminator; an unsupported revision; an unknown core member; an unsupported
required extension; a valid optional extension; and a resource-over-budget
case. Readiness 3 adds a present attached module, a present unattached invalid
module, cross-role Socket reuse invalidity, measurement-conflict invalidity,
and valid defaulted provenance. These fixtures are admitted through the
immutable transaction above and cross-linked to DR-0012's source/default
semantics and DR-0011's measurement/frame semantics.

Any future isolated worker must negotiate protocol/version compatibility, obey
bounded time and resource budgets, map crash/timeout/resource outcomes, have
its outputs validated before publication, and leave the compiler process
surviving worker failure. Detailed worker serialization remains deferred.

### Authoritative build operation and publication

Geometry execution and artifact publication are explicit phases or suboperations
of one authoritative public `build` operation. The operation-result envelope is
the sole public status/diagnostic authority; backend, worker, geometry, and
publisher diagnostics are normalized into it and never become competing status
channels. The public status vocabulary is closed and includes `output-failure`
for a derived-output or artifact-publication failure after accepted input and
semantic work, when result trust is not lost and no higher-priority internal or
resource failure applies. Precedence is global internal trust loss, then a
qualifying resource-limit, then the earliest applicable phase unable to produce
its required output, with same-phase rules inherited from DR-0002/DR-0012.
This is the public build-envelope vocabulary: the initial semantic resolver
outcomes remain owned by DR-0012, while this build boundary adds the derived-
output `output-failure` outcome.
Geometry, output encoding, staging, and publication failures map to
`output-failure` unless source-caused semantic invalidity, worker resource
failure, internal trust loss, or another higher/earlier outcome already
determines the result.

The diagnostics specification is the sole owner of diagnostic registry,
domain, class, occurrence, profile, ordering, and compatibility meaning. The
build operation owns top-level status and precedence only. Its closed initial
domains are source-admission, dependency, semantic-identity, graph-structure,
frame-numeric, resource, execution-trust, publication, and inspection; narrow
resolver-invariant and worker-protocol categories are stable classes. Resource
profiles remain operational inputs. A tiny mandatory bootstrap registry/profile
is always known. Unknown required registry/profile uses existing `unsupported`,
the effective bootstrap profile, bounded requested identifiers, and a
deterministic primary; the operation never emits under an unknown profile or
silently downgrades. Exact ordinary codes, field spellings, and profile IDs
remain fixture-gated.

A canonical build-operation specification is required before this boundary is
implemented; the canonical `spec/build-operation/README.md` owns its exact
Proposed operation schema, field spelling, and format. At this conceptual
boundary, a staging manifest carries a
non-authoritative candidate artifact identity. The output target is derived
deterministically from the explicit output root and that candidate identity;
exact spelling belongs to the canonical specification. Successful atomic
publication promotes the same candidate identity to committed artifact
identity, as owned at the identity level by DR-0006.

The unique per-execution `attempt_id` exists only in the returned operation
envelope, invocation-owned staging metadata, and logs. It is excluded from
committed or hashed bytes, target derivation, candidate identity, and
idempotent lineage equality. The stable deterministic `build_request_id`
contains every outcome-affecting source/source-set, an exact reference to the
implementation-content-binding identity used for execution, an exact reference
to the dependency-closure identity used for execution, compiler/toolchain/build
implementation, contract/schema/profile, configuration, seed,
backend/capability/protocol, and target/platform profile input. These are
references only: the request projection does not inline raw implementation
path/mode/content entries or raw dependency sets, which remain owned by their
separate domains. Fixture-payload identity is admission context and is
excluded, as is attempt identity. Omitting an outcome-affecting input or either
exact execution binding reference is an identity error. Candidate identity
derives from that request identity, artifact role, and identity-rule revision;
successful publication promotes the same
candidate. After atomic no-replace collision/EEXIST, inspect the winner: an
identical committed identity, lineage, complete manifest, hashes, and sizes is
already-published success; a different lineage/identity is target conflict; a
same-request byte difference is `internal-failure` nondeterministic output.
Exact canonical serialization/hash and safe-ASCII path mapping remain
activation prerequisites.

A verified identical existing target—matching identity, lineage, manifest, and
hashes—is idempotent already-published success. A different or unverifiable
occupant is an `output-failure` target-conflict and is never replaced. If the
platform cannot provide the required atomic no-replace publication primitive,
the operation fails as `output-failure`; it does not adopt or overwrite a
target. Cleanup removes only invocation-owned staging. Artifact inspection is
given expected build/artifact lineage and validates against it; it does not
guess or silently accept stale state.

Every invocation has a unique `attempt_id`, including when failure prevents a
complete build request from being established. A deterministic
`build_request_id` is stable across retries when the complete outcome-affecting
request is available; `attempt_id` never changes target or idempotent equality.
A committed artifact identity exists only for a successfully published
artifact or bundle.
Worker producer/output trust is tracked separately from coordinator, reporter,
and publisher trust. A worker crash or protocol corruption invalidates every
worker-produced output and maps through the governed outcome rules, but a
trusted isolated parent may report its independently observed exit, timeout,
or protocol failure. The parent must never adopt worker output after worker
trust loss. Validation cannot rehabilitate output produced across lost worker
trust.

The conceptual worker outcome mapping is closed even while exact protocol fields
remain deferred: unsupported protocol/version negotiation is `unsupported`;
trusted parent termination or transport closure after an established configured
timeout/resource breach is `resource-limit`; unexpected termination,
unexplained exit, transport loss, failed termination invariant, or termination
without a qualifying bound is `internal-failure`; well-framed and decoded but
contract-invalid output is `output-failure`; and a well-framed worker-declared
domain failure is validated before mapping to its governed domain status.
Coordinator, reporter, or publisher invariant/trust loss is `internal-failure`
and forbids publication. No worker-produced output remains adoptable after
worker trust loss.

Initially, a compile or geometry failure is reported through the authoritative
CLI/API envelope rather than persisted as a committed diagnostics-only failure
bundle. When coordinator, reporter, and publisher remain trusted, that
envelope may contain independently trusted parent observations; worker output
is never adopted after worker trust loss. Coordinator, reporter, or publisher
trust loss forbids publication and leaves only the surrounding CLI/launcher
envelope. A future persisted failure-evidence facility requires a separate
attempt-evidence identity and lifecycle decision. If publication itself fails,
the authoritative envelope is returned and no final bundle exists. Preserve
the root diagnostic even when top-level status is normalized.

The complete build outcome contract must cover source, dependency,
capability/protocol, timeout/resource, worker crash, malformed output,
invariant loss, encoding, staging, collision, and publication failures. These
are normalized into the one authoritative build envelope with precedence
inherited from DR-0002/DR-0012; resolver in-memory snapshot handoff is not
external serialization, and filesystem serialization/publication failures map
to `output-failure` here.

Domain operations remain separate in general, but the first public `build` path
uses one envelope across semantic resolution, geometry, and publication.
Artifact inspection remains a separate read operation and does not create a
second build-status channel.

Two future activation obligations remain nonblocking: before an isolated worker
activates, define containment, process-tree, output/log/handle/network/protocol/
cleanup/status bounds appropriate to its threat model; before evidence-bearing
portability or performance claims, freeze the lightweight exact build/reference
environment and dependency source/feature inputs, with native smoke preceding
native portability claims.

### First reproducible execution target

Use ordinary `rust-toolchain.toml` for exact toolchain selection and commit
`Cargo.lock`. Record the initial target triple, build profile, `rustc -Vv`, and
reference-environment metadata with each reproducible build. The first
reference path is WSL2 x86_64 GNU; a native-Linux
portability smoke follows later as stated by the design. Native Windows
execution and host-engine integration are later activation targets, not
first-platform requirements. The target does not prohibit later support for
other operating systems, architectures, or engines.

When a dependency is added, perform a lightweight review of its license,
unsafe or native code, and portability/security relevance. This does not
require Git commit pinning, an enterprise audit trail, or heavyweight
dependency bureaucracy.

### Performance and rationale

No performance claim follows from this platform choice without a reproducible
benchmark and recorded hardware profile. Rust is selected for memory and type
safety, deterministic headless tooling, a practical CLI/core throughput path,
and a credible bounded CPU proof for Stage 1. The selection is not based on an
assertion that advanced Rust geometry is universally mature, nor does it
prejudge a later geometry worker/backend.

## Consequences

- The first production semantic/compiler path has one reproducible stable-Rust
  implementation and a Cargo workspace once DR-0013 is accepted, while the
  semantic boundary remains engine-independent; exact schema and admitted
  fixtures still gate Readiness 2 parser/resolver work.
- A library plus thin CLI supports headless use and keeps visual tooling from
  becoming a compiler dependency; no daemon or service lifecycle is required
  for the first implementation.
- Stage 1 can produce bounded CPU geometry evidence in-process, while the
  versioned project-owned GeometryRequest/GeometryResult seam preserves a
  replaceable path to an isolated C++ worker/backend if a measured capability,
  performance, isolation, security, portability, or licensing need appears.
  The seam does not select a permanent surface or create DR-0009/DR-0010
  evidence.
- Python exploratory and visual tooling can continue without silently defining
  production semantics or compiler dependencies.
- A canonical build-operation specification is a prerequisite for exact
  operation fields and serialization. Immutable build-scoped sibling staging,
  manifest-last atomic no-replace publication, candidate-to-committed identity
  promotion, and manifest path/hash/size validation let the workbench reject
  incomplete, mixed, stale, symlinked, or path-escaping bundles. A verified
  identical target is idempotent already-published success; a different or
  unverifiable occupant is an unreplaced `target-conflict` output failure.
  This remains an initial interchange boundary and does not establish final
  avatar-package serialization or compatibility rules.
- A committed Cargo.lock, exact rust-toolchain.toml selection, recorded target,
  profile, rustc/reference metadata, and lightweight dependency review make
  the first WSL2 x86_64 GNU path reproducible without heavyweight
  audit policy. Portability, native Windows, and engine integration remain
  later work.
- Rust's safety and tooling rationale is testable, but every performance claim
  remains subject to reproducible benchmark and hardware evidence.
- A future worker must negotiate protocol/version compatibility, obey bounded
  time/resource limits, map crash/timeout/resource outcomes, validate outputs,
  and preserve compiler-process survival; its detailed serialization remains
  deferred.
- Readiness 1 through Readiness 4 make activation auditable: acceptance creates
  only the empty shell; one Ben-approved transaction containing the schema,
  versioned manifest, referenced fixtures, and parser/bootstrap activates
  Readiness 2; canonical frame/numeric rules plus expected graph outputs
  activate resolver/in-memory snapshot handoff; and a working resolver plus
  provisional geometry profile activates exploratory Stage 1 geometry /
  CK-KICK-014. Parked DR-0009/0010 remain nonblocking and are needed only for
  later formal comparison or production architecture selection.
- Geometry and publication contribute to one authoritative public build
  envelope. `output-failure` covers trusted derived-output/publication failure
  after accepted input/semantic work, subject to internal/resource/earlier
  precedence. An attempt identity always exists; deterministic build-request
  identity exists once the complete request is available; DR-0006 owns
  candidate versus committed artifact identity, with committed identity only
  after successful publication and the same candidate promoted on successful
  publication. Initially, failure is returned through the authoritative
  CLI/API envelope rather than a committed diagnostics-only bundle. Trusted
  coordinator/reporter/publisher components may include independently observed
  parent diagnostics in that envelope, but cannot adopt worker output after
  worker trust loss. A future persisted failure-evidence facility requires a
  separate attempt-evidence identity/lifecycle decision. Publication failure
  returns the envelope with no final bundle, preserves the root diagnostic, and
  cannot publish its own failure bundle. Invocation-owned staging is the only
  cleanup scope, and atomic no-replace publication fails closed when
  unsupported.
- The platform is reversible at the geometry boundary and at process/tooling
  boundaries, but a production compiler API and artifact lineage will create
  migration cost; a later change must preserve or explicitly migrate those
  contracts.
- The first filesystem promise is deliberately bounded to tested WSL `/home`
  local Linux publication: same-filesystem sibling staging, a capability probe
  for atomic no-replace, immutable committed outputs, cooperating builders,
  and post-collision inspection. It promises process-crash-safe namespace
  publication, not sudden-power-loss survival, and excludes malicious or
  privileged mutation from the initial threat model while still requiring
  complete-artifact verification or rejection.
- Candidate identity's filesystem component requires an unambiguous safe-ASCII
  profile mapping. Artifact inspection is a separate read operation with the
  closed results `success`, `absent`, `unavailable`, `mismatch`,
  `invalid-artifact`, `unsupported`, `resource-limit`, and `internal-failure`;
  it does not rewrite historical build status and retains deterministic
  completeness, primary, and precedence semantics.
- Worker producer/output trust is independent from coordinator/reporter/
  publisher trust. Worker crash or protocol corruption invalidates worker
  output; a trusted parent may report only independent observations through
  the authoritative envelope. No diagnostics-only bundle is committed
  initially; trust loss at coordinator, reporter, or publisher forbids
  publication, and validation cannot rehabilitate output created across lost
  worker trust.
- Readiness 2 admission uses a generic fixture-suite payload manifest plus a
  separate readiness/decision record naming its digest, reviewed source commit,
  exact ordered path/mode/content set and scoped payload digest/profile, and
  Ben approval. The scope contains only the manifest and declared schema,
  fixtures, and snapshots; it excludes readiness/approval/successor records,
  mutable pointers, and Git commit identity. Post-merge preflight allows commit
  identity to change but requires the manifest and scoped payload binding to
  match. Git history and explicit successor/deactivation/rollback records
  preserve history without a custom active-pointer ledger. Preflight proves
  consistency, not expected-result correctness.

## Alternatives Considered

### C++ day one

C++ offers mature geometry and graphics libraries and may reduce friction for a
future geometry backend. It would also increase memory-safety and build
complexity in the first semantic/compiler path, and could encourage geometry
and engine concerns to leak across the semantic boundary. It remains the
strongest alternative if measurements or required geometry capabilities make
the bounded Rust proof inadequate; the isolated-worker trigger preserves that
option without making it an unmeasured first dependency.

### C#/.NET

C#/.NET provides strong tooling, libraries, and a comfortable CLI/application
ecosystem. It introduces a different runtime and deployment surface and does
not by itself resolve the engine-independent geometry boundary. It may become
appropriate for a later integration or workbench, but it is not selected for
the first semantic/compiler core.

### Production Python

Python minimizes iteration cost and reuses the exploratory host, but makes the
production compiler more dependent on interpreter and native-extension
environments and weakens the headless distribution boundary. Python remains
appropriate for disposable experiments, evidence/render tooling, and the
visual workbench.

### Rust-only permanent backend

Making Rust the permanent geometry backend would simplify one-language
ownership, but would turn the first platform choice into an unsupported
long-term capability claim. It is explicitly not selected; reproducible gap,
required capability, or justified isolation, security, portability, or
licensing need can trigger an isolated C++ worker/backend.

### Immediate in-process C++ FFI or hybrid

Immediate FFI could access mature libraries quickly, but couples the first
compiler process to native ABI, toolchain, memory-ownership, and failure-mode
details before a worker boundary is shown insufficient. The selected order is
in-process Rust proof, isolated C++ worker/backend if evidence requires it,
and in-process C ABI/FFI only if that worker boundary cannot satisfy the
required use.

### Daemon or service first

A daemon could support persistent sessions and remote workbenches, but adds
process lifecycle, protocol, deployment, and security contracts before the
semantic/compiler boundary is proven. The first implementation uses a library
and thin CLI; a service can be added later if reproducible workflow or
integration requirements justify it.

### Broader first-platform matrix

Supporting native Windows, multiple architectures, host engines, and several
workbench environments immediately would broaden portability testing and
integration cost before one reproducible proof exists. The Linux x86_64 target
is a first execution target, not a portability rejection; additional targets
activate when evidence and users justify them.

### Promise power-loss durability in the initial profile

Claiming sudden-power-loss survival would require stronger synchronization and
storage-specific evidence than the first local WSL profile provides. The
initial contract promises process-crash-safe namespace publication only;
durability beyond that is a later profile.

### Use attempt identity as the output target

Per-invocation targeting would make retries non-idempotent and would prevent a
concurrent identical winner from being recognized. Stable request lineage and
candidate identity remain separate from attempt provenance under DR-0006.

### Trust worker output after parent-side validation

Validation cannot restore trust lost when the producer or protocol is corrupt.
The parent may publish only independently trusted observations through a
trusted coordinator/reporter/publisher path; worker-produced output is rejected
after worker trust loss.

### Persist diagnostics-only failure bundles in the initial artifact model

This would mix attempt-local evidence with deterministic committed outputs and
would require a second identity and retention lifecycle. It is not selected
initially: the authoritative CLI/API envelope carries trusted parent
observations, and any future persisted failure evidence requires a separate
attempt-evidence decision.

### Use a bespoke append-only fixture-admission ledger

This would preserve a custom active-pointer protocol but creates unnecessary
self-reference and merge-tree binding complexity for the hobby project. It is
not selected: the generic fixture payload manifest is bound by a separate
readiness/decision record naming its digest, scoped payload identity, and Ben
approval; ordinary Git history preserves successor and rollback history.

### Defer the transform carrier until Readiness 3

That would leave the Readiness 2 schema unable to validate transform shape and
would force a knowingly disposable structural contract. The selected boundary
freezes translation plus `xyzw` quaternion structure at Readiness 2, then
defers basis, normalization, ranges, conditioning, and tolerances to
Readiness 3.

### Claim broad portability from one host or require a full matrix immediately

One host result cannot support a broad cross-platform reproducibility claim,
but a formal verification effort and exhaustive architecture/toolchain matrix
would be disproportionate before the bounded profile exists. The selected
initial evidence uses WSL x86_64 and native Linux; materially different
evidence is required only when the claim expands. A future adapter uses basis
conjugation and fixtures because handedness reflection is not an ad hoc
quaternion sign change.

## Adversarial Review Response

This is CK-KICK-013 Revision 11, Proposed and discussion-approved on 2026-08-13.
This section preserves the earlier revision review chronology as historical
evidence before recording the current revision's disposition and pending review.
The exact Revision 1 Double review examined commit
`c64b1b98948304d631eecea6a354c9e42c89c510`. The independent [review 01](reviews/DR-0013-rev-01-review-01.md)
and [review 02](reviews/DR-0013-rev-01-review-02.md) both recommended **Revise**
at **High** confidence. Those exact reviews are stale historical evidence, not
a clean review or acceptance. Ben approved the F4–F7 resolutions in discussion
on 2026-08-11: DR acceptance is the sole shell-creation trigger; the
project-owned versioned GeometryRequest/GeometryResult seam is backend-neutral;
artifact publication and future worker failures are bounded and validated; and
the Rust/toolchain/dependency baseline and broadened isolation trigger are
lightweight and reproducible. Revision 3 records Ben's 2026-08-12 discussion
approval of five Recommendation 1 resolutions: the four ordered technical
readiness gates, authoritative build/publication outcome with `output-failure`,
and the linked status, module/Socket, and transform-contract consequences.
This discussion approval is not DR acceptance. The prior Revision 2 Double
review examined
target commit `88004388f9537a37617ae248bdaad4625e6f3f03` in [review 01](reviews/DR-0013-rev-02-review-01.md)
and [review 02](reviews/DR-0013-rev-02-review-02.md); both independent passes
recommended **Revise** at **High** confidence. The prior Review Complete state
records evidence rather than a clean review or acceptance. Those Revision 2
artifacts are now stale historical evidence after this proposal change. The
fresh current Double review of Revision 3 was complete at target commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`: [review 01](reviews/DR-0013-rev-03-review-01.md)
and [review 02](reviews/DR-0013-rev-03-review-02.md) both recommend **Revise**
at **High** confidence. The seven consolidated findings C1–C7 were findings of
that now-stale review; Ben resolved them in Batch 9 discussion. Applicable
consolidated findings were C1–C3 and C5–C7; C4 was owned by the linked semantic
records. Review completion is evidence, not a clean review or acceptance. This
record does not
claim owner acceptance, a production implementation, a permanent geometry
backend or surface architecture, a final artifact/package format, or a
performance result. Exact schema, fixture, and later evidence obligations
remain with their owning records. The prior `c64b1b...` review remains stale
historical evidence.

Those Revision 3 artifacts and findings are preserved as stale historical
evidence after the material Revision 4 change and do not satisfy the pending
current-revision review. Ben's Batch 9 resolutions assign DR-0013 the
canonical build-operation/publication boundary, Readiness 2 manifest admission,
candidate-target collision rules, trusted diagnostics-only reporting, and
Readiness 4's exploratory CK-KICK-014 trigger.

The fresh current Batch 9 Double review examined exact target commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`: [review 01](reviews/DR-0013-rev-04-review-01.md)
recommended **Revise** at **High** confidence under the contract/schema,
determinism, and security lens, and [review 02](reviews/DR-0013-rev-04-review-02.md)
recommended **Revise** at **High** confidence under the platform/failure,
reversibility, and publication lens. Consolidated findings **C1 (High)**,
**C2 (High)**, **C3 (High)**, **C4 (High)**, and **C5 (Medium)** apply:
identity/retry/concurrent publication; filesystem profile, crash durability,
and TOCTOU/tamper-safe inspection; worker-output versus coordinator/reporter/
publisher trust; immutable Readiness 2 binding and supersession/rollback; and
closed artifact-inspection non-success status algebra. At that historical
Revision 4 state, C1–C5 awaited Ben's discussion and owner disposition. Review
completion was evidence only; it was not a clean review or acceptance. Batch
10 discussion later resolved those findings, while the current Revision 6
still requires fresh review and owner disposition. Owner approval remains
Pending and Status remains Proposed. Only Ben may accept or reject this
proposal.

Ben approved the Batch 10 resolutions in discussion on 2026-08-12. The
Revision 5 review artifacts and C1–C5 findings above are stale historical
evidence after this material Revision 6 resolution. The prior fresh Batch 10
Double review examined commit `f27008f319cfc460f4a27efe31594e5607e7721e`:
[review 01](reviews/DR-0013-rev-05-review-01.md) recommended **Revise** at
**High** confidence under the contract/schema, determinism, identity,
security, and fixture-admission lens; [review 02](reviews/DR-0013-rev-05-review-02.md)
recommended **Revise** at **High** confidence under the platform/filesystem,
publication, reversibility, numeric-frame, and runtime-portability lens.
The prior consolidated findings **C1 (High), C2 (High), C4 (High), and C5
(Medium)** are resolved in this Proposed revision: deterministic committed
identity excludes attempt-local data and initially returns failure through the
authoritative envelope; fixture admission uses a generic payload manifest plus
separate readiness/decision record; Readiness 2 freezes a structural rigid
transform carrier and Readiness 3 admits immutable expected snapshots; and the
worker status/trust mapping is explicit. **C3 (High)** is resolved by linked
DR-0011/DR-0012 and remains cross-cutting context, not an additional DR-0013
decision. The WSL filesystem and staging proof remains a nonblocking
pre-publication obligation. Ben's resolution is discussion approval, not
acceptance. Review status is Complete for the new current revision after the
Double review below; Owner approval remains Pending and Status remains Proposed.
Only Ben may accept or reject this proposal.

The fresh current-revision Double review examined exact target commit
`28c83c7a21cf55f23274aeaf5d2ccc0a3e9e3b53`. [Review 01](reviews/DR-0013-rev-06-review-01.md)
used the contract/schema, identity, determinism, security, and fixture-admission
lens and recommended **Revise** at **High** confidence. It identified a High
success-or-failure-bundle contradiction, a High readiness scoped-hash-membership
gap, and a Medium timeout-versus-forced-termination overlap. [Review 02](reviews/DR-0013-rev-06-review-02.md)
used the platform, failure, reversibility, numeric-frame, adapter-portability,
and future-runtime lens and recommended **Revise** at **High** confidence. It
identified a High R2/R3 wording/link consequence, a High distinct R3 successor
transaction/activation gap, and Medium versions of the failure-bundle and
timeout/termination concerns. Both were fresh, independent `gpt-5.6-sol`
medium passes. The consolidated current findings are **C1 (High)** R2/R3
carrier wording across DR-0011/DR-0012 with this cross-link; **C2 (High)** the
distinct R3 successor transaction and project-ledger trigger; **C3 (High)**
exact scoped fixture payload identity with the DR-0006 build-proof consequence;
**C4 (Medium)** the success-bundle contradiction; and **C5 (Medium)** the
timeout/termination status distinction. They await Ben's discussion and owner
disposition. Review completion is evidence only; Owner approval remains Pending
and Status remains Proposed.

Ben approved the Batch 11 machine-contract resolutions in discussion on
2026-08-12. This Revision 7 proposal adds the typed address, canonical
basis/numeric/comparison profiles, canonical bytes/digest domains, diagnostic
registry/profile, and the distinct Readiness 3 transaction. The Revision 6
review artifacts are stale historical evidence. The fresh current-revision
Double review examined exact target commit
`053dba58fd344ed636420e0974cf617862fe265f`: [Review 01](reviews/DR-0013-rev-07-review-01.md)
and [Review 02](reviews/DR-0013-rev-07-review-02.md) were independent fresh
`gpt-5.6-sol` medium passes; both recommend **Revise** at **High** confidence.
Actionable findings remain for Ben's discussion, including immutable Readiness
3 implementation binding, numeric/experiment/comparison evidence, adapter
portability, and diagnostics/canonicalization cross-links. Review status is
Complete for evidence only; Owner approval remains Pending, Status remains
Proposed, and no acceptance or readiness gate activates.

The Batch 11 current-revision review artifacts for Revision 7 are now stale
after this Revision 8 proposal change. Their exact findings are preserved here
for the next review. Review 01 recorded: **C1 — High:** “Canonical JSON
sorting by semantic address is incomplete for module declarations, owner-role
records, and manifest/build collections that may lack one of the seven address
kinds. Define a total canonical key and duplicate/tie handling for every
unordered collection/projection before `ck-json-1` activation.” **C2 — High:**
“Decimal-to-binary64 admission is ambiguous (`0.1`, midpoint, excessive
precision, subnormal/underflow, and overflow). Select exact conversion/rounding
and rejection behaviour with boundary fixtures.” **C3 — High:** “R2/R3
payload binding excludes implementation bytes and mutable commit provenance
cannot prevent a merge/rebase activation of unreviewed parser/resolver code.
Add separately verified immutable implementation path/mode/content binding or
exact tree identity, checked after merge before the ledger trigger.” **C4 —
High:** “Canonical and DR-0012 diagnostic vocabularies conflict, and unknown
required registry/profile revisions need a bootstrap profile or reserved-
envelope diagnostic. Reconcile one domain mapping and bootstrap negotiation
diagnostics.” Review 02 recorded: **N1 — High:** “Define exact decimal-to-
binary64 conversion/rounding, overflow/underflow/subnormal behaviour, and
boundary fixtures.” **N2 — High:** “The numeric-threshold experiment is
circular without semantic error budgets, an independent oracle,
held-out/adversarial data, sensitivity analysis, and platform/toolchain
diversity. Preregister domains/error budgets; use higher-precision or analytic
oracle, development and held-out corpora, metamorphic/conditioning/FMA/
optimization coverage, a materially different architecture/toolchain, and
validation margins.” **N3 — High:** “Typed comparisons need normative
formulas, norms, quaternion/transform metrics, inclusive boundary/tie rules,
deterministic order-independent multi-claim satisfiability, and safeguards
against non-transitivity, with permutation/non-transitivity fixtures.” **N4 —
Medium:** “Add a future host-adapter conformance obligation for handedness
reflection, vector/rotation/rigid-transform basis change, named-direction
preservation, composition commutation, round trip, and binary64 narrowing
policy before adapter activation.” The mechanical N5 header synchronization
remains outside this scoped resolution.

The discussion-approved directions resolve C2 and N1–N4 as cross-record
numeric/frame prerequisites: exact rational admission, fixed typed comparison
algorithms and pairwise conflict semantics, the pre-registered experiment/
oracle/corpus method, and the future adapter conformance/narrowing obligation
are now stated above. C1, C3, and C4 remain unresolved in their owning
records; this platform revision does not add canonical collection keys,
implementation binding, or diagnostic bootstrap behavior.

The fresh current-revision Batch 12 Double review examined exact target commit
`730a2f77840cc0caa1f838c30dac4ff20f985e69`: [Review 01](reviews/DR-0013-rev-08-review-01.md)
and [Review 02](reviews/DR-0013-rev-08-review-02.md) were complete-coverage,
independent fresh `gpt-5.6-sol` medium passes. Both recommend **Revise** at
**High** confidence. Review 01 records unresolved A1–A3 comparator/identity
cross-links and the mechanical A4 summary correction. Review 02 records
unresolved E1 runtime-`asin`, E2 adapter unit-scale, and E3 floating-point
scope findings, plus mechanical E4 and E5 corrections. Review status is
Complete for evidence only; C1, C3, and C4 remain unresolved; Owner approval
remains Pending and Status remains Proposed. No readiness gate, package,
schema, fixture, resolver, adapter, or engine is accepted or activated.

Ben approved all five Batch 13 resolution directions in discussion on
2026-08-13. Revision 9 integrates the symmetric canonical-frame comparator,
exact dyadic scalar/half-chord arithmetic with offline conservative `H`,
deterministic quaternion normalization and authored claim identity; the
post-R3 adapter `C`/`s` mapping and storage-only/runtime-conformance tiers;
typed unordered collection keys and multiplicity; separate scoped
implementation-content binding recomputed around readiness triggers; and the
diagnostics sole-owner/bootstrap rule. The Revision 8 Batch 12 artifacts are
stale for this material revision; their findings and history remain preserved.
Review status is Complete for the current evidence and Owner approval remains
Pending. No DR acceptance, readiness gate, schema, fixture, resolver, adapter,
engine, experiment, or package activation follows.

The fresh current-revision Batch 13 Double review examined exact target commit
`8c38c501eb1262a1b85af0b8605220625601772f`. [Review 01](reviews/DR-0013-rev-09-review-01.md)
and [Review 02](reviews/DR-0013-rev-09-review-02.md) were complete-coverage,
independent fresh `gpt-5.6-sol` medium passes with no edits; both recommend
**Revise** at **High** confidence. Review 01 records unresolved **D1–D3**:
the unproven conservative `H` angular bound, incomplete mechanically
checkable implementation-binding closure, and underspecified versioned
claim-ID components/order/stable authored property address. Review 02 records
unresolved **P1–P3**: symlink/special-file/ancestor no-follow binding rules,
post-operation `-0` canonicalization, and malformed-versus-unsupported-versus
conversion-failure adapter status mapping. Findings remain cross-linked to the
semantic, identity, source, diagnostics, and fixture-manifest owners. Review
status is Complete for evidence only; Owner approval remains Pending and
Status remains Proposed. No Cargo shell, readiness gate, parser, resolver,
adapter, engine, fixture, implementation, or package is accepted or activated
by this review.

The Batch 13 findings were dispositioned in the prior Revision 10 as follows.
D1 was resolved by the canonical-tuple Euclidean `H` threshold and removal of
any represented-angular guarantee. D2 and P1 were resolved by the explicit
locked/offline implementation closure, immutable activation snapshot, and
root-descriptor no-follow regular-file profile cross-linked to DR-0006 and the
fixture manifest. D3 was resolved by conceptual typed `claim-id-1` and its
stable-address/order/multiplicity rules. P2 was resolved by the produced-zero
`+0` rule in DR-0011. P3 was previously described as resolved by the explicit
adapter status algebra and fixture obligations; Revision 11 corrects that
disposition and records malformed adapter-profile validation as a deferred
adapter-activation prerequisite. The prior reviews remain stale evidence;
Review status is Pending and this Proposed revision activates no Cargo shell,
readiness gate, resolver, adapter, or geometry implementation.

The fresh successor-target reviews are [Review 01](reviews/DR-0013-rev-10-review-01.md)
and [Review 02](reviews/DR-0013-rev-10-review-02.md). They are exact-target
evidence for Revision 10 only and are stale for this Revision 12 successor.
Their G1/G2 mechanical findings were fixed in the successor; T1–T3 were
resolved here, while T4/P3 is explicitly deferred until adapter activation and
is not a first Rust slice blocker. Review status for Revision 12 remains
Pending, and no acceptance or activation follows.

The final Double-review [Review 01](reviews/DR-0013-rev-11-review-01.md) and
[Review 02](reviews/DR-0013-rev-11-review-02.md) examined exact target commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` and are stale for this successor.
Revision 12 corrects the comparator/rank-table and sqrt wording and preserves
T4 as a deferred retained-human gate; fresh successor-target review remains
pending.

## Implementation and Proof Obligations

- If this DR is accepted, create only the Cargo workspace and empty
  compiler/library/CLI shell boundary; no second repository trigger or approval
  ceremony is required. Then enforce the readiness gates: exact JSON Schema
  plus a frozen/admitted fixture manifest activates creation of the
  manifest-listed fixture files and parser/bootstrap implementation together;
  Readiness 2's structural rigid-transform carrier is three-component
  translation plus explicit `xyzw` quaternion with no scale/shear fields;
  the distinct Readiness 3 successor transaction activates canonical basis,
  validity, normalization/sign, ranges, conditioning, composition, and typed
  comparison semantics plus frozen expected graph outputs, without reselecting
  the carrier; and a working resolver plus
  provisional geometry profile and project-owned seam activates exploratory
  Stage 1 geometry / CK-KICK-014. Readiness 2 is one Ben-approved transaction
  containing schema, versioned manifest, referenced fixtures, and
  parser/bootstrap; parser-independent preflight validates paths, hashes,
  profile references, expected status/primary diagnostics, provenance, and
  completeness. Production parsing must not self-admit the corpus.
  This Proposed record itself creates no packages, fixtures, parser, resolver,
  or geometry implementation. DR-0009/0010 remain parked and nonblocking.
- Bind Readiness 2 admission to a fixture-suite payload manifest containing
  suite kind, paths, hashes, profiles, expected results/diagnostics/snapshots,
  and provenance, but no self-digest or approval. A separate readiness/decision
  record names the reviewed manifest digest, source commit, SHA-256 payload
  digest, exact ordered path/mode/content set containing only the manifest and
  declared schema, fixtures, and snapshots, and the versioned external
  path-set framing/profile (exact identifier remains readiness-gated). The
  scope excludes readiness/approval/successor records, mutable pointers,
  self-reference, and Git commit identity. Rerun parser-independent preflight on the merged
  target; commit identity may change, but activation requires the manifest and
  scoped payload binding to match. Corrections, deactivation, and rollback use
  explicit successor/decision records preserved in Git history, not a custom
  active-pointer ledger. Test that preflight proves consistency only, while
  expected-result correctness remains a reviewed contract/hypothesis and later
  executable evidence. The canonical fixture-manifest specification owns exact
  Proposed manifest semantics.
- Keep fixture payload and implementation binding separate. For every Readiness
  2/3 implementation activation, recompute the external versioned ordered
  normalized relative path/mode/raw-content set and aggregate SHA-256 after
  merge and immediately before the trigger from a private immutable snapshot.
  The implementation-content binding covers selected Rust/Cargo repository
  paths, modes, and raw contents: sources/manifests, Cargo configuration or
  recorded absence, lockfile, toolchain, build scripts, and declared
  compile/codegen inputs. Dependency closure separately covers registry,
  vendored, path-dependency, and proc-macro provenance/content. Build-request
  identity separately covers selected packages/targets, target triple,
  features, profile, approved environment/tool/configuration inputs, and the
  exact locked/offline command. The activation closure manifest binds or
  references all three. Use locked/offline resolution; reject traversal,
  absolute paths, symlinks, special files, and submodules in entries/ancestors;
  ancestors are root-FD-anchored no-follow directories, while final regular
  files reject `st_nlink != 1` and require mode 100644/100755, with descriptor
  identity/type/size checks. Normal directory hardlink counts are not rejected.
  Opaque Git/native/codegen inputs need a reviewed vendored snapshot escalation.
  Keep binding, dependency closure, build-request identity, attempt identity,
  and fixture payload binding distinct. Block mismatches and require an
  explicit successor; do not bind the whole repository or create a custom
  ledger/signature. This remains a proportional Proposed hobby-project closure,
  not a general sandbox, and is not claimed implemented here.
- Keep semantic resolution, diagnostics, provenance, and the CLI independent
  of geometry implementation, visual workbench, and host engine.
- Use the diagnostics specification as sole owner of registry, domain, class,
  occurrence, profile, ordering, and compatibility. The initial domains are
  source-admission, dependency, semantic-identity, graph-structure,
  frame-numeric, resource, execution-trust, publication, and inspection;
  resolver-invariant and worker-protocol remain stable classes. Resource
  profiles are operational inputs. A mandatory bootstrap registry/profile
  handles unknown required profiles as `unsupported` under an effective
  bootstrap profile with bounded requested identifiers and a deterministic
  primary; never emit under an unknown profile or silently downgrade. Exact
  ordinary codes, field spellings, and profile IDs are fixture-gated.
- Consume DR-0011's exact numeric admission after strict JSON/token-resource
  checks: exact signed decimal rational to direct binary64 round-to-nearest,
  ties-to-even; reject non-finite/overflow and nonzero rationals rounding to
  signed zero; accept finite nonzero subnormals and excessive precision within
  the lexical/resource bound; normalize lexical negative zero only in
  semantic/canonical models; preserve source-byte distinction; normalize every
  produced zero to `+0` after each semantic numeric-producing stage and before
  comparison/serialization; and prohibit FTZ/DAZ in canonical operations.
- Make Readiness 3 comparisons normative and typed: normalize same-target
  transforms into one canonical local-to-parent frame and compare translations
  directly, while residual `B * inverse(A)` is only a separately named
  diagnostic/composition comparison. Decide inclusive scalar bounds over exact
  dyadic values with bounded integer arithmetic. Use exact dyadic dot-sign and
  finite binary64 canonical-tuple Euclidean half-threshold `H`; a nominal theta
  is informational/calibration metadata only, not an angular guarantee. Any
  future angular guarantee requires a new comparison-profile revision and
  successor evidence. After deterministic normalization, the tuple-distance
  predicate uses no square root, norm, `asin`, or `sin`; normalization itself
  uses the required correctly rounded binary64 square root. Normalize
  quaternions with fixed max-component scaling,
  operation order, correctly rounded sqrt, drift/near-zero validation, canonical
  sign, RN ties-even, and no FTZ/DAZ/ambient mode. Require structured authored
  claim identity, reject same-ID/different-value collisions, evaluate pairs in
  sorted claim-ID order, report the first failing pair, and choose the exact
  smallest tuple only after all pairs pass while retaining all occurrences and
  provenance.
- Before numeric activation, pre-register domains and semantic error budgets;
  fix operation order and round-to-nearest/ties-to-even without reassociation,
  implicit FMA contraction, or FTZ/DAZ; use exact/analytic and independent
  materially higher-precision oracles across frozen development, held-out,
  and adversarial corpora; cover metamorphic/permutation/conditioning and
  sensitivity; use a predeclared validation margin; reject out-of-domain
  cases rather than widening budgets or selecting smallest observations. The
  bounded initial reference is WSL x86_64 plus native Linux; broader claims
  require materially different architecture/toolchain evidence.
- Require unordered manifest/build/projection owners to declare typed total keys
  and uniqueness or multiplicity before activation. Use fixture ID, normalized
  safe-relative path with mode/content projection, dependency locator/role plus
  distinguishing revision, and owner-defined keys for other build arrays;
  reject absent keys/rules and duplicate keys only for uniqueness collections.
  Preserve repeated claims/multisets/diagnostics with explicit occurrence
  identity, never source/traversal/allocation/index order, serialization, or
  raw bytes.
- Before any host adapter activates, require orthogonal signed-permutation `C`,
  finite positive scale `s`, target precision, supported domain,
  narrowing/overflow/underflow/subnormal policy, and a storage-only or
  runtime-conformance tier. Map length-bearing values by `sC/s`, directions and
  normals by `C`, rotations by `C*R*C^-1`, and rigid transforms by
  `D*H_c*D^-1`, `D=diag(sC,1)`, with inverse `D^-1` and quaternion equivalence.
  Runtime-conformance adds engine arithmetic/probes/fixtures; the minimal tier
  makes no runtime claim. Probe FTZ/DAZ for subnormal preservation, fail
  unsupported capabilities closed, map trusted in-domain overflow/disallowed
  underflow to `output-failure`, and keep binary64 snapshots unchanged.
- Define the project-owned versioned conceptual `GeometryRequest` and
  `GeometryResult` seam for resolved graph/geometry intent, configuration and
  capability metadata, lineage, bounded diagnostics, and bounded outputs.
  Keep backend-native types out of semantic, CLI, artifact, and host-engine
  contracts. Implement the Stage 1 in-process Rust CPU dense-field
  evaluator/extractor only after the relevant proof inputs and fixture
  obligations are activated by their owning records. Seam work may support
  CK-KICK-014 but cannot establish a permanent surface choice or claim
  DR-0009/DR-0010 evidence.
- Record reproducible build/toolchain, target, seed/configuration, and source
  provenance for every proof run. Do not report performance without a
  reproducible benchmark and hardware profile.
- Make geometry and artifact publication explicit phases/suboperations of one
  authoritative public `build` operation-result envelope, as specified by a
  separate canonical build-operation specification. Normalize backend, worker,
  geometry, and publisher diagnostics into that envelope; preserve root
  diagnostics even when status is normalized; and cover source, dependency,
  capability/protocol, timeout/resource, worker crash, malformed output,
  invariant loss, encoding, staging, collision, and publication failures.
  Add closed public status `output-failure` for trusted derived-output/
  publication failure after accepted input/semantic work, subject to
  internal/resource/earlier precedence. A staging manifest carries a
  non-authoritative candidate artifact ID; DR-0006 owns its promotion unchanged
  to committed identity on successful atomic publication. Derive the target
  from explicit output root plus candidate identity. A verified identical
  target (identity, lineage, manifest, hashes) is idempotent already-published
  success; a different or unverifiable occupant is `output-failure`
  `target-conflict` and is never replaced. If atomic no-replace is unavailable,
  fail closed with `output-failure` without adoption/overwrite. Artifact
  inspection receives expected build/artifact lineage and must not guess stale
  state. Initially, return trusted parent observations through the authoritative
  CLI/API envelope and do not persist a diagnostics-only failure bundle as a
  committed artifact. A future persisted failure-evidence facility requires a
  separate attempt-evidence identity/lifecycle decision. Publication failure
  returns that envelope with no final bundle. Clean only
  invocation-owned staging. Defer final avatar-package serialization,
  exact primitive/platform mapping, and exact manifest/operation field spelling
  to the canonical specification.
- Keep worker producer/output trust separate from coordinator, reporter, and
  publisher trust. Map unsupported protocol/version negotiation to
  `unsupported`; trusted parent termination/transport closure after an
  established configured timeout/resource breach to `resource-limit`; unexpected
  termination, unexplained exit, transport loss, failed termination invariant,
  or no qualifying bound to `internal-failure`; well-framed and decoded but
  contract-invalid output to `output-failure`; and validate a well-framed
  worker-declared domain failure before mapping it to its governed status.
  Permit a trusted parent to report only independently observed
  exit/timeout/protocol failure, and never adopt worker output after worker
  trust loss. Initially return those trusted parent observations in the
  authoritative envelope rather than a committed diagnostics-only bundle;
  coordinator, reporter, or publisher trust loss forbids publication.
  Validation must not rehabilitate output across lost worker trust.
- Exercise the initial filesystem profile on tested local WSL `/home` Linux,
  excluding `/mnt/c`, network/removable/unspecified filesystems. Use sibling
  same-filesystem staging, probe atomic no-replace, keep committed outputs
  immutable, assume cooperating builders, and inspect winners after collisions.
  Promise process-crash-safe namespace publication only, not power-loss
  durability; use unambiguous safe-ASCII candidate path mapping and fail closed
  for unsupported primitives.
- Implement separate artifact inspection with closed results `success`,
  `absent`, `unavailable`, `mismatch`, `invalid-artifact`, `unsupported`,
  `resource-limit`, and `internal-failure`. Define absent, I/O unavailable,
  lineage mismatch, malformed/incomplete/tampered/hash mismatch,
  unsupported manifest/profile, resource interruption, and trust-loss meanings;
  preserve processing/diagnostic completeness and deterministic primary/
  precedence, without overwriting historical build status.
- Admit and exercise the lean Readiness 2 fixture corpus: minimal valid
  envelope, optional absent module, duplicate member, invalid discriminator,
  unsupported revision, unknown core member, unsupported required extension,
  valid optional extension, and resource-over-budget. Add Readiness 3 fixtures
  for present attached, present unattached invalid, cross-role Socket reuse
  invalid, measurement conflict invalid, and valid defaulted provenance.
- If reproducible measurements, a required capability, or a justified
  isolation, security, portability, or licensing need identifies a credible
  in-process Rust geometry gap, document it and evaluate an isolated C++
  worker/backend first. Require future worker protocol/version negotiation,
  bounded time/resources, crash/timeout/resource mapping, output validation,
  and compiler-process survival. Consider in-process C ABI/FFI only after
  evidence shows the worker boundary is insufficient; record resulting
  ownership, failure, portability, and licensing implications later. Worker
  serialization remains deferred.
- Use ordinary rust-toolchain.toml for exact toolchain selection, commit
  Cargo.lock, and record target triple, build profile, rustc -Vv, and
  reference-environment metadata. Establish WSL2 x86_64 GNU
  reference path first; perform native-Linux portability smoke later. When a
  dependency is added, review its license, unsafe/native code, and
  portability/security relevance without Git commit pinning, enterprise audit
  trail, or heavyweight process.
- Keep Python dependencies confined to disposable experiments, evidence/render
  tooling, and the visual workbench; prove that production headless compiler
  execution does not import them.

## Canonical Design Links

- [Architecture index](../architecture/README.md)
- [System overview](../architecture/system-overview.md)
- [Execution model](../architecture/execution-model.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Initial body-document encoding, resolution, and compatibility](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [Proposed build-operation contract](../../spec/build-operation/README.md)
- [Staged first-proof charter](DR-0007-staged-first-proof-charter.md)
- [First digitigrade morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)

## Reversibility and Revisit Triggers

Revisit the core platform if stable-Rust toolchain constraints prevent a
reproducible semantic/compiler workflow, if the Cargo/library boundary cannot
serve required consumers, or if portability evidence exposes an unjustified
target restriction. Revisit the in-process geometry boundary when reproducible
measurements, a required capability, or a justified isolation, security,
portability, or licensing need shows a credible boundary gap. Evaluate an
isolated C++ worker/backend before in-process FFI; choose FFI only if the
worker boundary is proven insufficient. Revisit the no-daemon choice if
persistent or remote workflows become an activated requirement. Revisit the
filesystem artifact/manifest handoff before final avatar-package persistence or
compatibility is promised. Native Windows and host-engine integration activate
only after their reproducibility and integration obligations are defined.

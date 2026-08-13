# Fixture manifest and admission contract

Status: Proposed conceptual specification; CK-KICK-012 Batch 13/14 discussion-
approved C1/C3/C4 resolutions; no schema, parser, or fixture corpus is
activated

Current Batch 13/14 material is recorded in DR-0006 Revision 12, DR-0011 Revision
15, and DR-0012 Revision 14; these remain Proposed with Owner approval Pending
and Review Complete after the current Double review at exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. DR-0013 Revision 12 is Accepted,
with Owner approval Approved by Ben and Review Complete at that exact target,
decided 2026-08-13. The earlier-predecessor
review at `763cff22d10f6491a05a28312a25250704543dcf` and immediate-predecessor
review at `9b96d18b115126ef09e54ad8c6f21749d5559ff6` are stale, with their
findings corrected in these revisions. The 9c governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. Review Complete is evidence only. Batch 13/14 carries the generic
canonical-key, separate implementation-binding, and diagnostic/bootstrap
directions as Proposed material. Exact identifiers, schema fields, code
membership, and fixture content remain readiness-gated.

This document is the canonical Proposed owner of fixture-manifest and fixture-
admission semantics. It defines the immutable review/admission boundary for a
future readiness corpus; it does not create a machine-readable manifest schema,
fixture files, a parser, or executable preflight. The [fixture policy](../../fixtures/README.md)
describes repository practice, while the [body-document contract](../body-document/README.md)
and [body-graph contract](../body-graph/README.md) own the meanings being tested.
The [build-operation contract](../build-operation/README.md) owns the meaning
of build/publication fixtures; this contract supplies the same manifest and
admission mechanism for that suite kind.

## Admission target and authority

The manifest payload is an immutable fixture-suite description. It contains the
suite kind, manifest and schema revisions, fixture paths and content hashes,
profiles, provenance, expected operation/semantic results and diagnostics, and
expected snapshot references when applicable. It never contains its own digest,
an approval, or an active pointer. The same conceptual payload mechanism covers
parser/body-document, semantic-graph, and build/publication suites.

A separate later readiness or decision record, outside the manifest payload
digest, names the exact reviewed source commit reference, manifest path,
manifest digest, SHA-256 path-scoped payload digest/tree identity, the exact
versioned external path-set framing/profile (its identifier remains
readiness-gated), preflight result, and Ben's approval. The path-scoped payload
digest is computed over one ordered path/mode/content set containing only the
manifest and its declared schema, fixture files, and expected snapshots. This
external ordered path-set binding is distinct from the `ck/v1/fixture-manifest`
canonical-data domain and must not reuse that domain as its framing/profile. It
excludes Git commit identity, approval/readiness records,
successor/deactivation records, mutable active pointers, and any
self-referential admission field. The payload can therefore be hashed without
self-reference and approved without changing the bytes being approved.
Merged-target preflight compares these content identities, not an unchanged
merge-commit identity. Git history and explicit successor records preserve
supersession; deactivation or rollback requires a later explicit approval. No
custom active ledger is needed, and no readiness gate activates from an
unadmitted or merely present manifest, schema, or fixture.

This fixture-payload scope remains exactly the manifest/schema/fixture/
expected-snapshot set above. The implementation binding below is a separate
readiness input and does not expand or alter the fixture payload digest.

### Separate implementation binding

Any readiness gate that activates code must also bind the relevant production
implementation separately from the fixture payload. The binding is a
versioned, domain-separated aggregate SHA-256 over an explicit ordered set of
normalized safe relative paths, file modes, and raw file contents. The exact
identifier and framing spelling remain readiness-gated, but the SHA-256
algorithm, ordered path/mode/raw-content semantics, and domain separation are
fixed Proposed direction. The binding record is outside the bound set and
contains no self-reference; it is not the `ck/v1/fixture-manifest` digest.

The closure is explicit and mechanically checkable, not an implementation
convention. The implementation-content binding owns selected repository paths,
modes, and raw contents: selected Rust/Cargo production sources and
workspace/crate manifests, repository Cargo configuration or a recorded
absence, `Cargo.lock`, the rust-toolchain declaration, build scripts, and
declared compile/code-generation inputs. Dependency closure separately owns
registry, vendored, path-dependency, and proc-macro provenance/content.
Build-request identity separately owns selected packages, targets, target
triple, features, profile, approved environment/tool/configuration inputs, and
the exact locked/offline command. Its request projection references the exact
implementation-content-binding identity and dependency-closure identity used
for execution; it does not inline raw path/content or dependency sets. Fixture-
payload identity and attempt identity remain excluded. Readiness 2 binds the parser/bootstrap
closure; Readiness 3 binds the resolver/source closure. The activation closure
manifest binds or references all three. Opaque Git, native, vendored, or
generated inputs that cannot be represented by this closure require an
explicitly reviewed vendored snapshot escalation before activation. Generic
host, rustc, and hardware evidence is recorded for reproducibility but is not
equality-bound unless the claim explicitly says so. Implementation binding,
dependency closure, build-request identity, attempt identity, and
fixture-payload binding are distinct inputs and identities.

The future preflight is locked/offline and reads from a private read-only
activation snapshot. It is rooted at an opened repository directory descriptor
and uses descriptor-relative, no-follow reads. Traversal, absolute paths,
symlinks, special files, and submodules in entries or ancestor components are
rejected. Ancestors must be descriptor-opened no-follow directories; a final
regular-file entry is rejected when `st_nlink != 1` and is eligible only with
mode `100644` or `100755`. Each read verifies descriptor identity, file type, and size
consistently between admission and hashing. Normal directory hardlink counts
are not rejected. The snapshot is immutable for the transaction. The profile excludes
the whole repository, mutable generated caches, unlisted inputs, approvals,
successor records, Git commit identity, and unspecified host state. This is a
proportional closure and tamper/escape check for the current hobby-project
threat model, not a general sandbox or hostile-privilege boundary.

After merge and immediately before the readiness ledger trigger, recompute the
fixture payload, implementation content, and dependency content from a fresh
immutable snapshot, and revalidate build-request identity against the exact
locked/offline command and other bound request inputs. Any mismatch blocks
activation and requires a successor
transaction; commit provenance alone can never authorize changed bytes. The
activation closure manifest binds or references all three closure inputs and
their distinct identities. Readiness 2 binds parser/bootstrap and Readiness 3
binds the resolver. This is a contract direction only and does not claim that
the preflight or snapshot machinery is implemented now.

Preflight proves internal consistency only. It checks the manifest structure,
paths, hashes, provenance, profile references, expected status/diagnostic
shape, completeness, and the separately recorded content binding. It does not
prove that an expected semantic result is correct. Expectation correctness is a
reviewed contract or hypothesis and later executable evidence.

## Conceptual manifest contents

The future exact encoding must represent these groups. The [canonical-data
profile](../canonical-data/README.md) owns canonical bytes and digest domains;
the exact machine schema and serialized member names remain readiness-gated.
Every unordered manifest collection/projection must use the canonical-data
owner-declared typed total key and explicit uniqueness/multiplicity rule:
fixture entries use fixture ID and reject duplicate IDs or duplicate normalized
paths; implementation-binding entries use normalized safe relative path,
mode, and raw content as bound values and reject duplicate paths. The future
exact machine schema and serialized member names remain readiness-gated:

- suite kind, manifest ID, and manifest revision;
- schema revision and schema hash;
- each fixture ID, repository path, content hash, and provenance;
- operation status;
- semantic outcome where applicable, kept separate from operation status;
- the primary diagnostic, required for every non-success status;
- processing completeness and diagnostic completeness;
- diagnostic-profile and resource-profile IDs; and
- expected snapshot path, digest, and comparison-profile identity where the
  suite requires a graph snapshot.

Diagnostic occurrences retain the diagnostic-profile occurrence identity and
multiplicity rather than being silently deduplicated. A required unknown
registry/profile uses the diagnostic bootstrap effective IDs, deterministic
bootstrap primary, bounded opaque requested IDs, and `required=true`; it is
never emitted under the unknown profile and does not add a phase. The exact
bootstrap code spelling is fixture-gated only while conceptual identity stays
unambiguous.

The separate readiness/decision record carries the reviewed source commit
reference, manifest path, manifest digest, SHA-256 path-scoped payload digest/
tree identity, exact ordered path/mode/content scope, versioned external
path-set framing/profile (identifier readiness-gated), preflight identity,
predecessor/supersession reference, and Ben approval. None of those admission
fields are part of the manifest payload digest.

The operation status uses the closed operation vocabulary owned by the relevant
operation contract. Semantic fixture taxonomy is separate: after recognized,
admitted input reaches semantic evaluation it may be `valid-supported`,
`semantically invalid`, or `well-formed-but-unsupported`. Parser, dependency,
resource, and internal failures are not relabelled as semantic outcomes. A
non-success operation status has a primary diagnostic; a successful status has
no primary, represented as absent or null according to the future exact
encoding.

## Readiness corpus

The lean Readiness 2 corpus is conceptual and contains at least:

- a minimal valid envelope;
- an absent optional module;
- a duplicate member;
- an invalid discriminator;
- an unsupported revision;
- an unknown core member;
- an unsupported required extension;
- an optional extension preserved opaquely; and
- a resource-over-budget input.

Readiness 3 adds a present attached module, a present unattached invalid module,
cross-role Socket reuse invalidity, measurement-conflict invalidity, valid
defaulted provenance, and an expected resolved-graph snapshot reference with
an explicit exact-vs-semantic comparison rule. These cases exercise the
[body-document](../body-document/README.md) shape/admission contract and the
[body-graph](../body-graph/README.md) containment, Socket, measurement, frame,
and provenance rules. Build-operation publication cases such as first build,
retry, concurrent winner, lineage change, and byte divergence use this same
manifest family with `suite_kind: build-publication`; they remain conceptual
until admission.

The numeric/frame successor corpus must also bind every case to the admitted
numeric and comparison profiles. Numeric admission boundaries include an
ordinary inexact decimal `0.1`, exact values, halfway/ties-to-even values,
maximum-finite and overflow values, the smallest subnormal, nonzero
underflow-to-zero rejection, lexical signed zero, excessive precision at the
declared lexical/resource boundary, and alternate decimal spellings that
denote the same rational. In-bound precision must be accepted; excessive
precision is a resource-bound case, not an arbitrary semantic digit cutoff.
Expected results distinguish raw-byte preservation from normalized `+0` and
normalized binary64 values.

Comparison fixtures include inclusive scalar/translation boundaries,
componentwise L-infinity checks, q/-q equivalence and the dot-zero `+1` tie,
the inclusive canonical-tuple Euclidean `H` boundary (without an angular
guarantee), post-operation `+0` bit patterns, transform residual comparison,
pairwise claim permutations, non-transitive
triples, and representative/provenance changes when an additional passing
claim is added. Authored-conflict and expected-snapshot comparison profiles
are distinct bindings. Future adapter fixtures separately cover named
directions, reflections/handedness, composition, inverse, quaternion
round-trips, correctly rounded narrowing, subnormals, nonzero-to-zero
underflow, overflow, malformed zero/negative/nonfinite scale, unknown revision,
unavailable capability, admitted-invariant violation, malformed output, and
status precedence. Exact malformed-adapter-profile status mapping is
deliberately unselected until the adapter request-validation prerequisite is
chosen and reviewed; Ben must explicitly dispose of that retained-human choice
before any adapter profile/schema activation. Malformed profile data is not
classified here as source-admission. This request-validation choice is
implementation/evidence-dependent and is not a blocker for the first Rust
slice. These fixtures are
activated only after Readiness 3 and do not select an engine.

Only listed fixtures participate in an admission. An unlisted fixture, even if
it exists on the review branch or is readable by an implementation, does not
activate and cannot silently expand the corpus.

## Activation boundary

Readiness 2 is one review-branch activation transaction containing the exact
reviewed schema, this admitted manifest, every listed fixture, and the
parser/bootstrap implementation plus its separately bound implementation
closure. Ben owns admission and must explicitly approve the separate
readiness/decision record before merge or activation. Post-merge and
immediately pre-ledger recomputation must match both the fixture payload
binding and implementation binding.
Readiness 3 is a separate successor transaction containing the successor
manifest/payload binding, expected graph snapshots, their comparison profile
and exact-versus-semantic rule, and the resolver implementation closure bound
by the same separate mechanism. It uses the same content-identity preflight
and the same generic suite mechanism; it does not reopen or replace the
Readiness 2 transform carrier. Nothing in this Proposed conceptual document
creates implementation packages or activates a readiness gate.

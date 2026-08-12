# Fixture manifest and admission contract

Status: Proposed conceptual specification; no schema, parser, or fixture corpus
is activated

Batch 12 discussion-approved numeric/frame obligations are recorded here as
expected-fixture categories only. They do not resolve Batch 11 C1 (total
canonical collection ordering), C3 (immutable Readiness 2/3 implementation
binding), or C4 (diagnostic-domain/bootstrap compatibility), which remain open
in the current Proposed decision records.

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
canonical-data domain and must not reuse that domain as its framing/profile. It excludes Git commit identity,
approval/readiness records, successor/deactivation records, mutable active
pointers, and any self-referential admission field. The payload can therefore
be hashed without self-reference and approved without changing the bytes being
approved. Merged-target preflight compares these content identities, not an
unchanged merge-commit identity. Git history and explicit successor records
preserve supersession; deactivation or rollback requires a later explicit
approval. No custom active ledger is needed, and no readiness gate activates
from an unadmitted or merely present manifest, schema, or fixture.

Preflight proves internal consistency only. It checks the manifest structure,
paths, hashes, provenance, profile references, expected status/diagnostic
shape, completeness, and the separately recorded content binding. It does not
prove that an expected semantic result is correct. Expectation correctness is a
reviewed contract or hypothesis and later executable evidence.

## Conceptual manifest contents

The future exact encoding must represent these groups. The [canonical-data
profile](../canonical-data/README.md) owns canonical bytes and digest domains;
the exact machine schema and serialized member names remain readiness-gated:

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
transform residual comparison, pairwise claim permutations, non-transitive
triples, and representative/provenance changes when an additional passing
claim is added. Authored-conflict and expected-snapshot comparison profiles
are distinct bindings. Future adapter fixtures separately cover named
directions, reflections/handedness, composition, inverse, quaternion
round-trips, correctly rounded narrowing, subnormals, nonzero-to-zero
underflow, overflow, and angular/translation budgets; they are activated only
after Readiness 3 and do not select an engine.

Only listed fixtures participate in an admission. An unlisted fixture, even if
it exists on the review branch or is readable by an implementation, does not
activate and cannot silently expand the corpus.

## Activation boundary

Readiness 2 is one review-branch activation transaction containing the exact
reviewed schema, this admitted manifest, every listed fixture, and the
parser/bootstrap implementation. Ben owns admission and must explicitly
approve the separate readiness/decision record before merge or activation.
Readiness 3 is a separate successor transaction containing the successor
manifest/payload binding, expected graph snapshots, their comparison profile
and exact-versus-semantic rule, and the resolver implementation or exact
implementation binding. It uses the same content-identity preflight and the
same generic suite mechanism; it does not reopen or replace the Readiness 2
transform carrier. Nothing in this Proposed conceptual document creates
implementation packages or activates a readiness gate.

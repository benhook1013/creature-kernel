# Fixture manifest and admission contract

Status: Proposed conceptual specification; no schema, parser, or fixture corpus
is activated

This document is the canonical Proposed owner of fixture-manifest and fixture-
admission semantics. It defines the immutable review/admission boundary for a
future readiness corpus; it does not create a machine-readable manifest schema,
fixture files, a parser, or executable preflight. The [fixture policy](../../fixtures/README.md)
describes repository practice, while the [body-document contract](../body-document/README.md)
and [body-graph contract](../body-graph/README.md) own the meanings being tested.
The [build-operation contract](../build-operation/README.md) owns build/output
fixtures rather than this readiness admission record.

## Admission target and authority

An admission binds a manifest to the exact reviewed Git commit/tree and path,
the manifest digest, and an activation-payload digest. The activation-payload
digest covers the exact payload that will activate, excluding the admission
record itself so the binding does not self-reference. The target is immutable:
the preflight identity and Ben's approval must name that exact target, not a
branch tip or a mutable working copy.

The admission workflow reruns preflight on the merged target. Activation is
allowed only when the immutable binding is unchanged. A successor admission is
append-only and names its predecessor or supersession relationship; historical
admissions are never edited. Deactivation or rollback requires explicit Ben
approval and creates a new append-only record. No readiness gate activates from
an unadmitted or merely present manifest, schema, or fixture.

Preflight proves internal consistency only. It checks the immutable binding,
manifest structure, paths, hashes, provenance, profile references, expected
status/diagnostic shape, and completeness. It does not prove that an expected
semantic result is correct. Expectation correctness is a reviewed contract or
hypothesis and later executable evidence.

## Conceptual manifest contents

The future exact encoding must represent these groups, while their serialized
names, hash algorithm, canonical bytes, and schema remain deferred:

- manifest ID and manifest revision;
- schema revision and schema hash;
- each fixture ID, repository path, content hash, and provenance;
- operation status;
- semantic outcome where applicable, kept separate from operation status;
- the primary diagnostic, required for every non-success status;
- processing completeness and diagnostic completeness;
- diagnostic-profile and resource-profile IDs; and
- the admission payload binding: reviewed Git commit/tree and path, manifest
  digest, activation-payload digest excluding this admission record, preflight
  identity, and Ben approval reference.

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
cross-role Socket reuse invalidity, measurement-conflict invalidity, and valid
defaulted provenance. These cases exercise the [body-document](../body-document/README.md)
shape/admission contract and the [body-graph](../body-graph/README.md)
containment, Socket, measurement, frame, and provenance rules. Build-operation
publication cases such as first build, retry, concurrent winner, lineage
change, and byte divergence remain conceptual fixtures of that operation and
are not activated by this manifest family.

Only listed fixtures participate in an admission. An unlisted fixture, even if
it exists on the review branch or is readable by an implementation, does not
activate and cannot silently expand the corpus.

## Activation boundary

Readiness 2 is one review-branch activation transaction containing the exact
reviewed schema, this admitted manifest, every listed fixture, and the
parser/bootstrap implementation. Ben owns admission and must explicitly
approve the immutable binding before merge or activation. Readiness 3 remains
gated on canonical basis, numeric/frame rules, and frozen expected graph
outputs. Nothing in this Proposed conceptual document creates implementation
packages or activates a readiness gate.

# Fixture manifest and admission contract

Status: Proposed conceptual specification; no schema, parser, or fixture corpus
is activated

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
manifest digest, path-scoped payload digest/tree identity, preflight result,
and Ben's approval. The payload can therefore be hashed without self-reference
and approved without changing the bytes being approved. Merged-target
preflight compares those content identities, not an unchanged merge-commit
identity. Git history and explicit successor records preserve supersession;
deactivation or rollback requires a later explicit approval. No custom active
ledger is needed, and no readiness gate activates from an unadmitted or merely
present manifest, schema, or fixture.

Preflight proves internal consistency only. It checks the manifest structure,
paths, hashes, provenance, profile references, expected status/diagnostic
shape, completeness, and the separately recorded content binding. It does not
prove that an expected semantic result is correct. Expectation correctness is a
reviewed contract or hypothesis and later executable evidence.

## Conceptual manifest contents

The future exact encoding must represent these groups, while their serialized
names, hash algorithm, canonical bytes, and schema remain deferred:

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
reference, manifest path, manifest digest, path-scoped payload digest/tree
identity, preflight identity, predecessor/supersession reference, and Ben
approval. None of those admission fields are part of the manifest payload
digest.

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

Only listed fixtures participate in an admission. An unlisted fixture, even if
it exists on the review branch or is readable by an implementation, does not
activate and cannot silently expand the corpus.

## Activation boundary

Readiness 2 is one review-branch activation transaction containing the exact
reviewed schema, this admitted manifest, every listed fixture, and the
parser/bootstrap implementation. Ben owns admission and must explicitly
approve the separate readiness/decision record before merge or activation.
Readiness 3 remains gated on canonical basis, numeric/frame rules, canonical
bytes/digests, and frozen expected graph outputs. Nothing in this Proposed
conceptual document creates implementation packages or activates a readiness
gate.

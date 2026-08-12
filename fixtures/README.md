# Fixtures

Status: Active policy; no body-contract fixtures committed or activated

Fixtures are small, stable inputs used to prove specifications, compiler
behaviour, geometry invariants, interactions, and regressions.

The canonical Proposed owner of fixture-manifest and admission semantics is the
[fixture-manifest specification](../spec/fixture-manifest/README.md). This
policy records repository practice; it does not define a competing manifest or
activate files.

Each fixture must record:

- stable ID and purpose;
- authoritative source or generator;
- license and provenance;
- expected valid or invalid status;
- deterministic seed and version when generated;
- tests or experiments that consume it;
- whether expected outputs are exact, semantic, metric, or visual.

The CK-KICK-012 Batch 10 proposal keeps the corpus conceptual and adds no
implementation fixtures. Schema-level body-document fixtures will
exercise strict UTF-8 JSON admission, duplicate-key rejection, unknown core
members, required and optional extensions, exact contract-family/revision
recognition, deterministic diagnostics, and finite resource-limit outcomes.
Resource fixtures cover source/aggregate bytes, string lengths/counts, nesting
depth, object/array members, graph entities/relations, ownership depth,
module/reference expansion, extension count/payload, numeric admissibility,
diagnostics, and aggregate work/memory.
Resolved body-graph fixtures will exercise namespace ownership/remapping,
typed concepts and directed Joint endpoints, socket/Attachment non-articulation,
the minimum Stage 1 chain, authored/defaulted/derived provenance, frame
normalization, measurement conflicts, and invalid/unsupported outcomes.

Readiness 2 admission is one review-branch activation transaction described by
the [fixture-manifest specification](../spec/fixture-manifest/README.md). The
manifest payload contains suite kind, fixture paths/content hashes, profiles,
provenance, expected results, and expected snapshot references where needed;
it never contains its own digest, approval, or active pointer. A separate
readiness/decision record names the reviewed source commit, manifest path,
manifest digest, path-scoped payload digest/tree identity, preflight result,
and Ben approval. The scoped digest covers an ordered path/mode/content set of
only the manifest and its declared schema, fixtures, and expected snapshots;
approval/readiness, Git commit, successor/deactivation, mutable pointer, and
self-referential admission fields are excluded. Preflight validates internal
consistency only and compares those content identities on the merged target;
it does not require an unchanged merge commit. Successor admissions are
recorded explicitly in Git history, and deactivation/rollback requires a new
explicit Ben-approved record. An unlisted fixture never activates.

The conceptual manifest fields are manifest ID/revision, schema revision/hash,
each fixture ID/path/hash/provenance, operation status, semantic outcome where
applicable, primary diagnostic, processing and diagnostic completeness,
diagnostic/resource profile IDs, and expected snapshot path/digest/
comparison-profile identity where applicable. Operation
status remains separate from semantic taxonomy; every non-success requires a
primary diagnostic, while success has no primary (absent/null in the future
exact encoding). The production parser must consume an admitted record; it
must not self-admit the corpus or create a circular "first fixture" authority.

The lean Readiness 2 corpus is a minimal valid envelope, absent optional
module, duplicate member, invalid discriminator, unsupported revision, unknown
core member, unsupported required extension, preserved optional extension, and
resource-over-budget input. Readiness 3 is a separate successor admission
adding a present attached module, present unattached invalid module, cross-role Socket reuse invalidity,
measurement-conflict invalidity, valid defaulted provenance, and an expected
graph snapshot with an explicit comparison rule and resolver binding. Build-operation
identity/publication cases (first build, retry, concurrent winner, lineage
change, and byte divergence) use the same manifest mechanism as a
build-publication suite and remain conceptual.

Before any fixture is used as proof, a cross-DR matrix must link durable
identity cases to typed concepts, articulation endpoints, measurement/frame
cases, expected outcomes, and diagnostic coverage across DR-0006, DR-0008, and
DR-0011. The exact fixture inputs, machine fields, numeric values, tolerances,
and expected diagnostic codes remain unselected. Compiler-consumed generation
fixtures activate only through the admitted Readiness 2 transaction, not when
an implementation happens to read an unadmitted body document.

Do not commit large generated assets here merely for convenience. Use manifests
and an approved artifact store when size or licensing makes normal Git unsuitable.

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

The CK-KICK-012 Batch 13 proposal keeps the corpus conceptual and adds no
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
normalization, measurement conflicts, and invalid/unsupported outcomes. The
planned numeric evidence corpus is separate from this admission corpus until
its experiment is registered: it must freeze development, held-out, and
adversarial sets covering decimal midpoint/tie, signed-zero,
subnormal/underflow, overflow, cancellation, near-zero quaternion, q/-q, long
chain, ill-conditioned, basis-conversion, and claim-order cases. Exact numeric
values, expected outcomes, and profile IDs remain unselected.

Current material is recorded in DR-0006 Revision 10, DR-0011 Revision 13,
DR-0012 Revision 12, and DR-0013 Revision 10; each remains Proposed with Owner
approval Pending and Review Pending after material resolution edits. The Batch
13 review commit `8c38c501eb1262a1b85af0b8605220625601772f` and findings
D1–D3/P1–P3 are stale historical evidence; those findings are resolved in the
current proposals and fresh review is pending. The directions remain Proposed
policy only, so no fixture corpus, schema, parser/resolver, adapter, Cargo
package, readiness gate, experiment, or implementation is activated.

Readiness 2 admission is one review-branch activation transaction described by
the [fixture-manifest specification](../spec/fixture-manifest/README.md). The
manifest payload contains suite kind, fixture paths/content hashes, profiles,
provenance, expected results, and expected snapshot references where needed;
it never contains its own digest, approval, or active pointer. Unordered
manifest entries use owner-declared keys: fixture ID is unique, and normalized
repository paths are unique; duplicate IDs or paths fail closed. A separate
readiness/decision record names the reviewed source commit, manifest path,
manifest digest, path-scoped payload digest/tree identity, preflight result,
and Ben approval. The scoped digest covers an ordered path/mode/content set of
only the manifest and its declared schema, fixtures, and expected snapshots;
approval/readiness, Git commit, successor/deactivation, mutable pointer, and
self-referential admission fields are excluded. Any readiness gate that
activates code also has a separate, versioned, domain-separated aggregate
SHA-256 binding over an explicit ordered set of normalized safe-relative path,
mode, and raw-content entries. The binding record is outside that set and has
no self-reference. Readiness 2 binds the parser/bootstrap closure; Readiness 3
binds the resolver closure, including relevant source, workspace/crate
manifests/configuration, build/codegen scripts and inputs, Cargo.lock,
rust-toolchain, and applicable path-dependencies. Behaviour-affecting
features/environment/configuration are fixed or request identity inputs;
host/rustc/hardware evidence is recorded but not equality-bound unless
claimed. There is no whole-repository binding, commit equality, signature, or
custom ledger. Recompute both bindings after merge and immediately before the
ledger trigger; mismatch blocks activation and requires a successor.
Preflight validates internal
consistency only and compares those content identities on the merged target;
it does not require an unchanged merge commit. Successor admissions are
recorded explicitly in Git history, and deactivation/rollback requires a new
explicit Ben-approved record. An unlisted fixture never activates.

The conceptual manifest fields are manifest ID/revision, schema revision/hash,
each fixture ID/path/hash/provenance, operation status, semantic outcome where
applicable, primary diagnostic, processing and diagnostic completeness,
diagnostic/resource profile IDs, and expected snapshot path/digest/
comparison-profile identity where applicable. Diagnostic occurrences preserve
the diagnostic profile's occurrence identity and multiplicity; they are not
silently deduplicated. Unknown required diagnostic registry/profile requests
use bootstrap effective IDs, deterministic bootstrap primary, bounded opaque
requested IDs, and `required=true`, without emitting under the unknown profile
or adding a phase. Operation
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

# Fixtures

Status: Active policy; no body-contract fixtures committed

Fixtures are small, stable inputs used to prove specifications, compiler
behaviour, geometry invariants, interactions, and regressions.

Each fixture must record:

- stable ID and purpose;
- authoritative source or generator;
- license and provenance;
- expected valid or invalid status;
- deterministic seed and version when generated;
- tests or experiments that consume it;
- whether expected outputs are exact, semantic, metric, or visual.

The CK-KICK-012 Batch 4 proposal adds two planned fixture families without
activating implementation fixtures. Schema-level body-document fixtures will
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

Readiness 2 admission is one review-branch activation transaction. It must
contain the exact schema, a versioned fixture manifest, every file referenced by
that manifest, and the parser/bootstrap evidence that will consume them.
Ben is the admission owner and must explicitly approve the transaction before
merge or activation. Files may coexist on the review branch while the
transaction is under review; none is active merely because it exists there.

The manifest's proposed fields are an immutable revision/manifest ID, schema
revision and schema hash, each fixture's path, hash, and provenance, expected
status and primary diagnostic, diagnostic and resource profile IDs, and a
completeness declaration. A generic parser-independent preflight must validate
paths, hashes, profile references, expected status/primary diagnostics,
provenance, and completeness before merge. The production parser must consume
this admitted record; it must not self-admit the corpus or create a circular
"first fixture" authority.

Before any fixture is used as proof, a cross-DR matrix must link durable
identity cases to typed concepts, articulation endpoints, measurement/frame
cases, expected outcomes, and diagnostic coverage across DR-0006, DR-0008, and
DR-0011. The exact fixture inputs, machine fields, numeric values, tolerances,
and expected diagnostic codes remain unselected. Compiler-consumed generation
fixtures activate only through the admitted Readiness 2 transaction, not when
an implementation happens to read an unadmitted body document.

Do not commit large generated assets here merely for convenience. Use manifests
and an approved artifact store when size or licensing makes normal Git unsuitable.

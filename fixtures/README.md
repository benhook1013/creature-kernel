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

Before any fixture is used as proof, a cross-DR matrix must link durable
identity cases to typed concepts, articulation endpoints, measurement/frame
cases, expected outcomes, and diagnostic coverage across DR-0006, DR-0008, and
DR-0011. The exact fixture inputs, machine fields, numeric values, tolerances,
and expected diagnostic codes remain unselected. Compiler-consumed generation
fixtures activate only when the first compiler reads a body document.

Do not commit large generated assets here merely for convenience. Use manifests
and an approved artifact store when size or licensing makes normal Git unsuitable.

# Fixtures

Status: Active policy; no fixtures committed

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

Do not commit large generated assets here merely for convenience. Use manifests
and an approved artifact store when size or licensing makes normal Git unsuitable.

# Visual-review browser assets

This directory contains the checked-in browser assets used by the local
[visual-review server](../serve.py): [app.js](app.js) and [style.css](style.css).

The server serves these files as static assets for local review sessions; they
are source files for that served UI, not generated output. See the parent
[visual-review README](../README.md) for workflow and interpretation.

The browser also supports read-only structural-inspection sessions. In the
`GET /api/reviews/<id>` response, the normalized review record carries
`review.kind: "structure"` and `review.structure: <CLI JSON>`, alongside the
current `response` field and the usual `schema_version` envelope. The nested
value is the `inspect-structure` CLI result; the renderer also defensively
accepts the equivalent direct `{ "kind": "structure", "structure": <CLI
JSON> }` shape. The index labels these sessions and the review route renders
their status, source identity, contract, basis, projection format, collection
counts, explicit Part containment, directed joints, composition records,
regions, capabilities, and closed raw JSON. A structural result is provisional
and source-preserving: the UI does not infer a skeleton, render geometry,
describe runtime state, edit data, or execute browser commands. Invalid or
non-success results show status and diagnostics without drawing a partial
containment tree.

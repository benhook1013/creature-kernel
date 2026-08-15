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
containment tree. When the prepared-source payload includes an available exact
placement preview, the same read-only page draws deterministic SVG front
(x/y), side (z/y), and top (x/z) views with semantic Part markers, containment
links, Joint endpoint links, attachment-root distinction, and labels. Joint
frame transforms are not interpreted; this is crude spatial scaffolding, not
geometry, mesh, surface, volume, anatomical quality, rigging, pose/animation,
IK, deformation, physics, general transforms, resolver activation, or runtime
evidence. The view is intended for Ben's human appraisal of spatial layout,
proportions/symmetry, and tail/foot depth before merge.

Filled-form sessions use `review.kind: "provisional-form"` and carry the
validated CLI envelope in `review.provisional_form`. Their page is appraisal
only: it shows four deterministic variants derived from the same exact
placements, each with front x/y, side z/y, and top x/z filled primitive panels.
The client accepts both legacy v1 and corrected v2 envelopes after server-side
validation. Gallery labels are hidden until a part is hovered or focused; an
expanded inspection dialog provides larger projections and a persistent part
legend without enabling review writes.
The renderer uses shared bounds and deterministic AddressKey tie-breaking for
overlap order. It draws only ellipsoids, round-ended capsules, and filled
tapered segments; it does not imply a continuous surface, anatomical
correctness, mesh/topology, rigging, animation/IK, deformation, physics,
runtime behaviour, or Readiness 3.

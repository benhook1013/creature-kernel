# JUNCTION-001 prospective implementation note

Status: implementation prepared, static/AST review only; no candidate geometry,
L2 evaluation, collision result, render, or anatomy acceptance is claimed.

JUNCTION-001 couples the existing ankle-port section and frame to the FOOT-004
bulk grid through one local displacement solve.  The source graph is the
existing 79-vertex, 74-quad grid: the eight old dorsal-hole vertices receive
`actual A - old H` Dirichlet displacement, row 0 and rows 5–7 are fixed, and
plantar rows 1–4 hold local foot-rest `U` displacement at zero while their
`X/F` components remain harmonic unknowns.  Row 5 is the settled `M` frontier.
The solve uses uniform quad-edge weights independently for `X`, `U`, and `F`,
with no regularizer, parameter search, or fallback.

The implementation reuses only FOOT-004's pure `_source_frame` and
`_grid_points` helpers.  It omits the eight old hole vertices and writes the
existing ankle-port `A` indices directly into the surrounding faces.  No
collar/support ring, ankle joint, source retune, or post-L2 correction is
introduced.  Incoming leg controls and the actual `A` ownership, coordinates,
and stencils remain inherited.

The explicit policy is in
[`foot-junction-policy.json`](foot-junction-policy.json), and the implementation
is in [`foot_junction_construction.py`](foot_junction_construction.py).  Focused
tests are execution-owned by Raman and are intentionally not run in this
pre-capture handoff.  They cover graph solvability, direct-mouth welding,
prefix/distal invariants, mirrored/source response, and local fold diagnostics;
full L2 stencil, thickness, intersection, and visual checks remain downstream
capture gates.  If the coupled human/anthropomorphic batch fails, the result
returns to the Overseer before any successor.

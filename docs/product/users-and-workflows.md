# Users and workflows

Status: Proposed product baseline

These workflows describe observable goals. They intentionally avoid committing
to a GUI, geometry backend, language, or runtime engine.

## Initial users and reference workflow (Proposed)

The earliest workflow serves the project developer or researcher. They use an
authoritative semantic source set and shared domain operations, diagnostics, and
reproducible evidence to create, inspect, compile, and validate a native
generated creature.
Technical artists and game developers are important downstream review and
integration users; this ordering does not exclude them from the product.

The initial domain is stylized furry characters. Adult interactions are explicit
motivating use cases and difficult contact/deformation stress cases for the
general body, contact, and solver mechanisms. Those mechanisms remain reusable
and are not defined as adult-only product behavior.

Native programmatic generation without a handcrafted base mesh is the first
reference path. External authored-mesh conformance is a later workflow, while
early contracts must leave that path open. These statements are proposed under
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).

## Body author using structured tools

1. Create an initial human-readable semantic source document from a body-plan
   declaration or empty graph.
2. Add and configure parts using semantic attachments and local coordinates.
3. Compile and validate a preview in the current authoring session.
4. Inspect geometry, skeleton, collision, regions, and diagnostics.
5. Adjust parameters and repeat; compatible changes may update the active
   avatar in place.
6. For a structural change, allow the preview session to block or freeze while
   recompiling and validating; a valid replacement reloads without closing or
   reopening the scene or session.
7. Save a deterministic source and compiled runtime package.

If compilation or validation fails, the previous validated avatar remains
active and the session reports actionable diagnostics. A later asynchronous
in-session replacement may avoid the blocking interval, but is not required by
the initial workflow and this workflow is not a promise of arbitrary live
gameplay structural editing.

## External AI agent

1. Query the supported operations, capabilities, and source inputs.
2. Apply a bounded semantic mutation through the shared operation model.
3. Compile and validate headlessly.
4. Read structured diagnostics and inspect requested derived artifacts.
5. Propose further changes without depending on GUI automation.
6. Present diffs and evidence for human acceptance.

## Technical artist or reviewer

1. Open generated output and debug overlays.
2. Inspect silhouette, joint behaviour, semantic regions, weights, and collision.
3. Identify whether a failure belongs to parameters, a generator, a solver, or
   an unsupported capability.
4. Supply corrections or constraints without destroying the authored-source and
   resolved-graph relationship.
5. Approve, reject, or qualify the result.

## Game integrator

1. Compile or obtain a versioned runtime avatar package.
2. Load it through a host-engine adapter.
3. Query supported capabilities and quality tiers.
4. Drive animation, IK, contact, and deformation through stable runtime contracts.
5. Select fallbacks based on hardware and scene budgets.
6. Record actionable diagnostics when the package or adapter is incompatible.

## Player character customization

1. Change supported proportions, parts, markings, or material parameters.
2. Receive immediate feedback for changes that preserve the active representation.
3. For topology, body-plan, or other major structural changes, wait while the
   preview/authoring session compiles and validates without leaving the scene or
   session.
4. Continue with a valid replacement, or keep the old validated avatar and
   receive a precise diagnostic on failure.
5. Treat later asynchronous in-session swapping as a possible future workflow,
   not an initial editor or gameplay contract.

## Runtime character interaction

1. Participants advertise semantic regions, effectors, constraints, and solver
   capabilities.
2. The interaction selects a compatible quality tier.
3. Root alignment and pose solving establish contact.
4. Collision, localized deformation, and physical response run within budgets.
5. The interaction falls back or terminates predictably when constraints cannot
   be satisfied.

## External mesh contributor

1. Supply a mesh and optional skeleton as a later explicitly linked or mapped
   authored input.
2. Map or fit it to semantic landmarks, parts, and regions.
3. Receive a conformance report and supported capability tier when that later
   workflow is defined.
4. Correct mappings or accept explicit fallbacks.
5. Export the same runtime package interface as a native creature.

# Users and workflows

Status: Proposed product baseline

These workflows describe observable goals. They intentionally avoid committing
to a GUI, geometry backend, language, or runtime engine.

## Body author using structured tools

1. Create a creature document from a body-plan declaration or empty graph.
2. Add and configure parts using semantic attachments and local coordinates.
3. Compile a preview.
4. Inspect geometry, skeleton, collision, regions, and diagnostics.
5. Adjust parameters and repeat.
6. Save a deterministic source and compiled runtime package.

## External AI agent

1. Query the supported schema, generators, capabilities, and command surface.
2. Apply a bounded transaction to a creature document.
3. Compile and validate headlessly.
4. Read structured diagnostics and inspect requested render artifacts.
5. Propose further changes without depending on GUI automation.
6. Present diffs and evidence for human acceptance.

## Technical artist or reviewer

1. Open generated output and debug overlays.
2. Inspect silhouette, joint behaviour, semantic regions, weights, and collision.
3. Identify whether a failure belongs to parameters, a generator, a solver, or
   an unsupported capability.
4. Supply corrections or constraints without destroying the source relationship.
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
3. Wait for bounded background or loading-screen compilation when topology or
   derived assets must change.
4. Continue with a validated avatar or receive a precise incompatibility report.

## Runtime character interaction

1. Participants advertise semantic regions, effectors, constraints, and solver
   capabilities.
2. The interaction selects a compatible quality tier.
3. Root alignment and pose solving establish contact.
4. Collision, localized deformation, and physical response run within budgets.
5. The interaction falls back or terminates predictably when constraints cannot
   be satisfied.

## External mesh contributor

1. Supply a mesh and optional skeleton.
2. Map or fit it to semantic landmarks, parts, and regions.
3. Receive a conformance report and supported capability tier.
4. Correct mappings or accept explicit fallbacks.
5. Export the same runtime package interface as a native creature.

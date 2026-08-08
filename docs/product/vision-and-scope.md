# Vision and scope

Status: Proposed product baseline

## Vision

Creature Kernel is a programmable creature-generation and embodiment platform.
It should construct semantic bodies, surface geometry, rigging, collision,
deformation data, appearance inputs, and runtime capabilities from one
deterministic body definition.

The initial creative focus is stylized furry characters. The larger goal is a
body grammar capable of expressing related morphology families without making
every character a bespoke graphics and physics project.

## Primary outcome

A developer should be able to define or modify a creature through structured
documents and CLI/API operations, compile it into a runtime avatar, and use that
avatar in a real-time interactive game with shared animation, contact, and
deformation systems.

The platform should make a generated creature more than a visible mesh. It must
retain semantic knowledge of body parts, relationships, capabilities, material
regions, and runtime representations.

## Product character

Creature Kernel is intended to become:

- a deterministic creature compiler;
- an engine-independent semantic body and avatar contract;
- a runtime for pose, contact, deformation, and capability negotiation;
- a first-class CLI/API suitable for humans, scripts, and external AI agents;
- a source of game-ready assets and optional higher-quality cinematic output;
- an integration point for existing game engines rather than a replacement for
  every concern of a general-purpose engine.

## Initial scope

- Stylized furry morphology with an intentionally bounded first body family.
- Programmatic body assembly without requiring a handcrafted base character mesh.
- Continuous surface generation from semantic volumetric parts or an alternative
  method selected through evidence and review.
- Generated skeleton, skinning, collision, semantic regions, and basic materials.
- Bounded real-time representations with quality levels and fallbacks.
- Headless generation, inspection, validation, and preview rendering.
- Deterministic source documents and reproducible builds.
- A path for later conformance of externally supplied meshes.

## Explicit non-goals for the first proof

- A complete standalone renderer or general-purpose game engine.
- Equal-quality support for arbitrary fictional anatomy.
- Full render-resolution soft-body simulation over every character.
- Dynamic topology changes every frame.
- Dense strand fur, clothing, and self-collision at cinematic fidelity.
- A built-in language model or chat interface.
- A production SaaS, multiplayer service, marketplace, or deployment platform.
- Automatic replacement of artistic judgment in every generated detail.

## Success shape

The first meaningful proof should generate multiple substantially different
members of one morphology family from body documents and demonstrate that they:

- compile without bespoke mesh or rig work;
- preserve semantic body regions;
- pass defined geometry and pose checks;
- share at least one animation or procedural control scenario;
- expose compatible collision and contact representations;
- render and run within an explicit reference-hardware budget;
- can be reproduced through documented CLI commands.

Exact visual quality, morphology range, performance targets, and runtime engine
remain open decisions.

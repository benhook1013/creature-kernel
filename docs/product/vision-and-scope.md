# Vision and scope

Status: Proposed product baseline

## Vision

Creature Kernel is a programmable creature-generation and embodiment platform.
It should resolve an authoritative semantic source set into a per-build
semantic body-graph snapshot, then derive surface geometry, rigging, collision,
deformation data, appearance inputs, and runtime capabilities from that shared
lineage.

The initial creative focus is stylized furry characters. The larger goal is a
body grammar capable of expressing related morphology families without making
every character a bespoke graphics and physics project.

## Initial product boundary (Proposed)

The initial product is an engine-independent procedural creature compiler and
embodiment runtime, not a game, editor, or general-purpose engine. A real-time
game is the first downstream proof and integration target. The earliest workflow
is the project developer or researcher using structured source, CLI/API
operations, diagnostics, and reproducible evidence; technical artists and game
developers are important downstream review and integration users.

Stylized furry characters are the initial domain. Demanding close-contact and
deformation scenarios are motivating use cases and stress cases, while reusable
body, contact, and solver mechanisms remain general rather than hard-coded to
one interaction domain. Native programmatic generation without a
handcrafted base mesh is the first reference path. External authored-mesh
conformance is later, and early contracts must not foreclose it.

These four initial-boundary statements are proposed under
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).
The compile/runtime direction is Proposed under
[DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md):
expensive invariant generation is outside the frame loop, while a bounded
hybrid package supports live interaction and an initial in-session preview
reload workflow. The source and identity directions are accepted semantic-
foundation directions under [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md)
and [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md);
the operation direction remains Proposed under
[DR-0004](../decisions/DR-0004-external-automation-through-cli-and-api.md).
Exact formats, syntax, budgets, and compatibility details remain open.

## Primary outcome

A developer should be able to define or modify a creature through structured
documents and CLI/API operations, compile it into a runtime avatar, and use that
avatar in a real-time interactive game with shared animation, contact, and
deformation systems.

The platform should make a generated creature more than a visible mesh. It must
retain semantic knowledge of body parts, relationships, capabilities, material
regions, and runtime representations.

The proposed runtime direction combines conventional prepared assets with
selected semantic fields, cages, signed-distance data, and regional simulation
data. Live work remains bounded to pose, contact, parameterized deformation,
and activated regional solvers; it is neither a fully live implicit character
nor a semantics-free conventional asset.

The first Readiness 3 resolver/fixture proof is intentionally narrower than
the long-term platform: it covers the bounded stylized digitigrade furry-biped
family and fixed fixture envelope. It binds one explicit authored-conflict
comparison profile for authored versus Attachment-equation-derived placement,
with identity and constants frozen only from a bounded successor experiment.
Once admitted, disagreement that fails that profile's bounds is invalid source
with no successful snapshot; exact-zero, indefinite caller-selected
tolerances, and post-hoc widening are not part of the proof. Readiness 3
remains inactive until its successor admission transaction is complete.

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

- A bounded stylized digitigrade furry biped family for the first proof:
  required torso/pelvis, head with a simplified muzzle, two arms with
  simplified hands or paws, and two digitigrade legs with simplified feet or
  paws. Predefined ears and tail may be enabled through named sockets. This
  family is a Proposed boundary, not a claim of arbitrary-anatomy support.
- Programmatic body assembly without requiring a handcrafted base character mesh.
- Continuous surface generation from semantic volumetric parts or an alternative
  method selected through evidence and review.
- Stage 1 must preserve source-linked semantic joint frames and semantic
  region intent/lineage. It does not have to generate a usable bone hierarchy,
  bind weights/skinning, analytic collision proxies, or actual contact
  artifacts. Stage 2 generates usable skeletons, skin weights, and collision
  proxies and proves one shared pose/control scenario; Stage 3 owns actual
  contact, deformation, and runtime claims.
- Generated semantic regions and basic material inputs, with bounded runtime
  representations, quality levels, and fallbacks introduced by later stages.
- Bounded real-time representations with quality levels and fallbacks.
- In-session preview recompilation and replacement without closing the scene or
  session; a failed replacement retains the last validated avatar and reports
  diagnostics.
- Headless generation, inspection, validation, and preview rendering.
- Authoritative semantic source inputs and reproducible builds.
- A path for later conformance of externally supplied meshes.

## Explicit non-goals for the first proof

- A complete standalone renderer or general-purpose game engine.
- Extra limbs, wings, quadrupeds, arbitrary joints or graphs, detailed digits,
  arbitrary anatomy, and other morphology families.
- Full render-resolution soft-body simulation over every character.
- Dynamic topology changes every frame.
- Dense fur or hair, clothing or cloth, and self-collision at cinematic
  fidelity.
- Stage 1 claims of shared pose, close-contact behaviour, or visible
  deformation.
- A built-in language model or chat interface.
- A production SaaS, multiplayer service, marketplace, or deployment platform.
- Automatic replacement of artistic judgment in every generated detail.

## Success shape

Success is a staged progression, with each stage making only its own claims.
Stage 1 is the first continuation gate: every declared valid fixed fixture
must pass every mandatory structural check and the recorded subjective visual
floor. It should generate multiple substantially different members of the
bounded family from body documents, without bespoke mesh or rig work, and
provide reproducible geometry, semantic regions, basic appearance inputs,
diagnostics, and the source-linked embodiment lineage described above. A
failed or inconclusive valid fixture means the gate has not passed, while
remaining useful evidence; invalid fixtures must fail expected diagnostics and
are not counted as valid pass fixtures. Before EXP-0001 execution or evidence,
stable fixture IDs, concrete source inputs, discriminating parameters,
seed/configuration, and provenance must be frozen; selecting hypotheses does
not require that freeze. Passing Stage 1 does not claim shared pose,
animation, contact, deformation, or real-time interaction.

Stage 2 is a separate embodiment proof. It must demonstrate generated
skeleton, skin-weight, and collision-proxy behaviour across the fixed
body-profile set, including at least one shared pose or control scenario, while
preserving semantic representations. Stage 3 is a separate bounded real-time
interaction proof; only it may claim actual contact artifacts and behaviour,
localized deformation, physical response, and declared runtime-budget
evidence.

All stages use fixed, substantially different body profiles and shared
generation operations; per-fixture patches are not evidence of a general
family capability. Structural checks and recorded human visual assessment are
separate evidence classes, as described in the [visual-quality evaluation
protocol](../research/visual-quality-evaluation.md).

Exact visual quality, morphology range, performance targets, and runtime engine
remain open decisions. Capability classes and quality names may be useful for
explanation, but exact names and numerical budgets remain non-normative pending
benchmarks; a high-end PC represents a larger finite budget, not an unbounded
mode.

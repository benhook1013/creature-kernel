# Creature Kernel foundation

Status: Historical founding record

Captured: 2026-08-05

Decision state: exploratory, with explicit decisions and unresolved questions

## Purpose of this document

This document durably captures the project concept developed in the founding
conversation. It is not a final technical specification. It distinguishes:

- ideas that are currently treated as decided;
- working architectural hypotheses;
- known limitations and uncertainties;
- questions that need later design or experimentation.

This remains the authoritative record of the discussion that led to Creature
Kernel. It is not the canonical owner of current product, specification, or
architecture contracts; see [documentation authority](README.md).

## Origin and evolution of the idea

The conversation began with the difficulty of creating a 3D adult furry game
with convincing graphics, inverse kinematics, character-to-character contact,
soft-body effects, localized stretching, and deformation. Existing small furry
games often fail during development because their creators encounter a tightly
coupled collection of hard problems:

- animation made for one body does not fit another body;
- inverse kinematics can align bones but cannot deform skin or preserve volume;
- collision can produce unstable or visually undesirable results;
- physically simulated bodies are expensive and difficult to art-direct;
- unusual proportions, digitigrade limbs, tails, wings, and other body plans
  multiply the amount of content and corrective work;
- each new character may require bespoke meshes, rigs, collision, animations,
  and deformation setup.

The idea consequently moved beyond making a single game. It became a platform
problem: define bodies and interactions semantically so that geometry, rigging,
physics, and deformation can be generated and coordinated.

The next step in the discussion removed the assumption that artists must first
provide a conventional base mesh. Creature Kernel instead proposes generating
the body itself from programmatic parts and producing a continuous surface
around them. The platform is therefore a 3D engine in a literal generative
sense: it creates embodied 3D assets rather than only rendering finished ones.

Finally, the intended AI relationship was clarified. Creature Kernel should not
require an AI assistant embedded in its application. It should expose a stable,
deterministic CLI/API that an outside AI, a human, or an ordinary script can use
equally. An external agent may issue precise tool calls, inspect structured
results, request renders, and iterate with human review.

## Working definition

Creature Kernel is a deterministic, agent-ready procedural creature compiler
and embodiment runtime.

It accepts a structured body program and produces an avatar package containing:

- a semantic body graph;
- generated body volumes and a renderable surface;
- a skeleton, joint frames, limits, and IK chains;
- skinning weights and deformation bindings;
- collision proxies or distance fields;
- deformable regions and physical material parameters;
- semantic surface fields and appearance inputs;
- runtime capabilities and interaction affordances.

```text
Intent or exact commands
          |
          v
Declarative body document
          |
          v
Creature compiler
  |       |        |         |          |
  v       v        v         v          v
Body    Surface  Skeleton  Collision  Deformation
graph    mesh     and IK    fields     metadata
          \        |         |          /
           \       |         |         /
            v      v         v        v
               Avatar package
                     |
                     v
              Embodiment runtime
                     |
                     v
               Engine adapter
```

## Decisions currently treated as established

### Product and scope

- The project name is **Creature Kernel** and the repository slug is
  `creature-kernel`.
- The initial domain is stylized furry creatures.
- The project is a platform or engine component, not initially a game by itself.
- A real-time interactive game remains the primary downstream experience and a
  first-class architectural constraint.
- Its core value is the shared representation and compiler that connect body
  generation, semantics, animation, collision, and deformation.
- A conventional game engine may be used for rendering and runtime integration;
  building an unrelated renderer, editor, networking stack, or general-purpose
  game engine is not the initial objective.
- The motivating use cases include difficult adult-character interactions, but
  the core body and interaction technology is general rather than tied to adult
  content.
- Expensive creature generation and preprocessing may occur ahead of time, on a
  loading screen, or asynchronously. This does not make the resulting experience
  noninteractive.
- Every compiled avatar must expose bounded runtime representations, quality
  levels, and fallbacks.
- A cinematic or offline-quality path may supplement the real-time runtime, but
  it is not currently intended to replace the game-oriented path.

### Source of truth

- A creature begins as a semantic, declarative body document.
- The generated polygon mesh is an output, not the primary source of truth.
- Stable semantic identifiers must be used instead of generated vertex indices.
- Builds should be deterministic for a given body document, compiler version,
  configuration, and random seed.

### AI and automation

- Creature Kernel does not require an embedded AI model.
- The engine must be fully usable through a CLI and programmatic API.
- A GUI, CLI, external AI agent, test runner, or build system should all call the
  same core operations.
- External AI assistance should operate through structured tool calls rather
  than GUI clicking when possible.
- Headless rendering and structured diagnostics should enable future automated
  evaluation without making computer-use automation a core dependency.

### Representation

- Characters need both a semantic simulation representation and a visible
  surface representation.
- Body plans should be graphs rather than a single fixed humanoid hierarchy.
- Body components must carry functional capabilities as well as anatomical
  names. Examples include support, manipulation, grasping, reaching, locomotion,
  attachment, collision, and deformation.
- Positions and dimensions should primarily be expressed in parent-local and
  normalized body coordinates. Exact coordinates remain available as a lower
  level operation.
- Semantic regions, normalized coordinates, and capabilities should survive
  changes in proportions and generated mesh topology.

### Geometry hypothesis

- The leading geometry approach is to assemble semantic volumetric primitives
  and generate a continuous surface around their combination.
- Candidate primitives include ellipsoids, spheres, tapered capsules,
  generalized cylinders, rounded boxes, curve-following tubes, wedges, and
  specialized feature generators.
- Smooth union, intersection, and subtraction of signed-distance fields are the
  leading means of composing those primitives.
- Surface extraction converts the combined field into a watertight polygon
  mesh.
- The initial visual target can be smooth, cartoony, low-detail, and coloured by
  procedural material fields.
- Eyes, claws, horns, teeth, and similarly hard or topologically distinct
  features may remain separately generated components.

### Runtime interaction

- Inverse kinematics is only a pose and alignment layer. It is not a complete
  collision, deformation, or physical-response solution.
- A complete interaction is represented as semantic phases and constraints,
  rather than only as an animation authored for a particular pair of bodies.
- Animation, root alignment, IK, collision, deformation, balance, and physical
  response are specialized cooperating layers.
- Simplified analytic collision proxies or distance fields are normally more
  suitable than triangle-level collision against render meshes.
- Purpose-built deformation rigs, cages, morphs, or regional simulations should
  control visual results. Full soft-body simulation is optional and selective.
- Characters and interactions should negotiate a supported capability level and
  degrade gracefully when advanced deformation is unavailable.

## Proposed core model

The primitive concepts currently envisioned are:

```text
Creature
BodyGraph
BodyPart
Joint
Attachment
Socket
Capability
VolumeField
SurfaceField
MaterialField
CollisionShape
DeformableRegion
Interaction
Constraint
SolverProfile
```

A body part is not merely a mesh fragment. It can contain:

- a generator and parameters describing its volume;
- a parent, attachments, sockets, and local coordinate frame;
- one or more skeletal segments and joints;
- dimensions, tapering, mass, and inertia;
- joint limits and preferred bending directions;
- collision and query representations;
- semantic surface and material fields;
- deformable regions, stiffness, damping, and maximum strain;
- functional traits and supported interactions.

For example, a leg may be a chain generator with locomotion and support
capabilities. A tail may use the same general limb concepts but expose a
different set of capabilities. A quadruped forelimb could support weight and,
for some characters, also act as a manipulator.

## Proposed compiler pipeline

The provisional compilation pipeline is:

1. Parse and validate the body document.
2. Build the semantic body graph and resolve attachments.
3. Produce joint frames, skeleton topology, dimensions, and limits.
4. Generate implicit volumes and combine them into body regions.
5. Preserve or propagate part identity and normalized coordinates through the
   combined fields.
6. Extract a surface mesh at the requested quality level.
7. Remesh, simplify, or reorganize topology when required.
8. Generate skinning weights from skeletal and volumetric influence fields.
9. Generate collision proxies, signed-distance fields, and collision filtering.
10. Generate deformation cages or low-resolution volumetric simulation meshes.
11. Generate procedural material inputs and semantic region masks.
12. Run conformance and quality tests.
13. Package the result for a runtime or external engine.

The same body definition should generate the visible character and the hidden
representations used by animation and physics. This is expected to be the main
architectural advantage over importing unrelated assets and attempting to infer
their meaning afterward.

## Execution model: real-time first with compilation

The project should distinguish three time domains rather than requiring every
operation to meet a per-frame deadline.

```text
Body document
      |
      v
[1] Creature compilation
      |
      v
Runtime avatar package
      |
      v
[2] Real-time game simulation
      |
      v
[3] Optional cinematic or offline enhancement
```

### Creature compilation

Compilation may take seconds or, for advanced assets, longer. It can occur in an
external creator, during character creation, on a loading screen, as a background
job, or once when importing a character. Candidate compilation work includes:

- combining body-part volumes and extracting a surface;
- remeshing, simplifying, and generating LODs;
- generating skin weights, collision fields, and analytic proxies;
- constructing deformation cages and regional simulation meshes;
- binding low-resolution simulations to the render surface;
- generating material attributes and GPU resources;
- running conformance, pose, collision, and deformation tests.

The compiled product should be a stable runtime avatar package. The game should
not repeat invariant geometry-processing work every frame.

### Real-time game simulation

The runtime package can perform bounded, stateful work such as:

- animation, root motion, retargeting, motion warping, and full-body IK;
- capsule, convex, or signed-distance contact queries;
- contact constraints and physical reactions;
- bone, morph, cage, and GPU surface deformation;
- procedural material evaluation;
- selected cloth, hair, secondary motion, and regional soft-body simulation.

Runtime does not imply that all features run at maximum fidelity on every body.
Resolution, solver iterations, active regions, and character count must remain
budgeted.

### Optional cinematic or offline path

The same body definition may also drive a higher-quality path for:

- high-resolution volumetric simulation;
- dense fur, cloth, and self-collision;
- cached geometry and record/replay;
- offline training data for learned runtime deformers;
- high-quality scene rendering.

This is a supplementary output of the architecture. It should not become a
requirement for basic interaction or game execution.

### Baked and dynamic data

"Baked" means precomputing stable structures, not predetermining interactions.

| Precomputed or compiled | Dynamic at runtime |
| --- | --- |
| Mesh connectivity and LODs | Poses and IK targets |
| Skinning weights | Contacts and forces |
| Collision fields and proxies | Constraint state |
| Deformation cages and bindings | Cage offsets and morph weights |
| Regional tetrahedral topology | Low-resolution soft-body state |
| Semantic surface attributes | Material and interaction parameters |

Emergent interactions can therefore use prepared numerical representations
without becoming pre-rendered scenes.

### Runtime mutation boundary

Character changes should be classified by whether they preserve topology:

- Proportion, colour, material, and many shape changes may update through bones,
  fields, cages, or morphs while retaining the same runtime surface.
- Adding or removing limbs, replacing major modules, or changing body plans may
  require recompilation.
- A future runtime could compile topology-changing edits asynchronously while
  keeping the previous avatar active, then swap packages at a safe boundary.

The exact first-version boundary remains undecided.

### Local quality activation

Expensive simulation should activate where it matters rather than uniformly:

```text
Distant character
    -> animation and basic IK

Nearby character
    -> contact collision and cage deformation

Actively interacting region
    -> higher-quality local deformation
    -> optional regional soft-body simulation
```

Quality may vary by character, body region, interaction, camera distance, and
hardware budget. One character can simultaneously use inexpensive skeletal
behaviour in most regions and a high-quality solver near an active contact.

### Provisional real-time classification

This table is a working expectation, not a benchmark result:

| Feature | Real-time expectation |
| --- | --- |
| Skeletal animation, IK, and motion warping | Strong |
| Analytic collision and signed-distance queries | Strong |
| Morph, bone, cage, and GPU surface deformation | Strong |
| Procedural colours and markings | Strong |
| Simplified cloth, hair, and secondary motion | Strong |
| Local low-resolution soft-body regions | Plausible on high-end hardware |
| Several interacting soft regions | Plausible with strict budgets |
| Whole-character volumetric simulation | Difficult |
| Multiple high-resolution soft characters | Generally outside normal frame budgets |
| Dynamic surface remeshing during interaction | Background or authoring work |
| Arbitrary topology changes every frame | Not a practical game target |
| Dense two-way soft-body self-collision | Primarily cinematic or offline |

### Boundary that would force an offline scene tool

The project would cease to be a practical game runtime if it required all of the
following at once:

- render-resolution geometry participating directly in physics;
- full volumetric simulation over every character;
- dense two-way soft-body and self-collision;
- arbitrary topology changes during contact;
- dense fur and clothing colliding with every deforming surface;
- unbounded solver iterations to guarantee exact convergence;
- no approximation, LOD, regional activation, or artistic fallback.

High-end hardware expands the available budget but does not make an unbounded
simulation bounded. The platform must preserve quality negotiation even if its
initial game target assumes a powerful desktop PC.

### Learned and cached deformation

Offline simulation can produce caches or training examples for a lighter runtime
deformer. This may efficiently reproduce predictable pose-driven muscle, tissue,
or cloth behaviour. It is not assumed to solve arbitrary unseen contacts, so
procedural contact deformation and selected live simulation remain necessary.

## Procedural appearance

The initial appearance system can avoid unique hand-painted textures. Each
surface point can inherit weighted semantic influences from the volume fields.
Those attributes can drive:

- primary and secondary body colours;
- muzzle, belly, paw, and tail-tip colour regions;
- spots, stripes, patches, and seeded variations;
- material changes for noses, claws, horns, eyes, and similar features;
- stylized roughness, outlines, or simplified fur responses.

Patterns should preferably use semantic or body-local coordinates so that they
remain stable when proportions change. Strand-level fur is not required for the
first visual target.

## External meshes

Externally authored meshes remain important for eventual adoption by artists,
but they are not required for the earliest proof of concept.

The eventual import path may fit or map an external mesh to a generated semantic
body. Compatibility can be tiered:

| Level | Input | Expected support |
| --- | --- | --- |
| Native | Generated by Creature Kernel | Full semantic and deformation support |
| Conformed | Custom mesh bound to a generated cage or field | Most platform features |
| Mapped | Existing rig mapped to semantic joints and regions | IK, animation, and collision |
| Basic | Arbitrary mesh with minimal metadata | Limited interaction and fallback behaviour |

Generated and external characters should ultimately compile to the same avatar
package interface. External meshes do not need identical topology, but advanced
deformation may require additional mapping, cages, or corrective work.

## Interaction and solver architecture

An interaction should describe intent and constraints through phases such as:

```text
approach
    -> root alignment
    -> establish contacts
    -> solve pose and joint limits
    -> enable deformation and physical response
    -> maintain or transition contacts
    -> release
```

The provisional runtime ordering is:

```text
Interaction planner
        |
        v
Root alignment and motion warping
        |
        v
Whole-body pose solver / IK
        ^
        | feedback
        v
Collision and contact constraints
        |
        v
Local deformation solvers
        |
        v
Physical reaction and balance
        |
        v
Final skinning, secondary motion, and rendering
```

The exact ordering and iteration strategy are unresolved. Collision can
invalidate a pose, while reaction forces can move the roots and alter contact.
The system therefore needs explicit ownership, feedback limits, and
stabilization rather than an uncontrolled collection of components.

### Candidate deformation levels

| Tier | Behaviour |
| --- | --- |
| 0 | Authored or procedural animation and root alignment |
| 1 | Whole-body IK and simple collision proxies |
| 2 | Contact-driven deformation bones and morphs |
| 3 | Procedural cage or distance-field deformation |
| 4 | Regional volumetric soft-body simulation |
| 5 | Cached, learned, or offline-quality deformation |

Quality levels may be selected per character, per region, per interaction, and
by runtime distance or performance budget.

### Difficult localized deformation

The original discussion included radial opening deformation, stretching,
compression, and abdominal bulging as examples that expose the limitations of
IK and ordinary rigid collision.

The current hypothesis is a hybrid approach:

- use simplified collision or distance fields to calculate contact position,
  direction, depth, and approximate force;
- drive specialized radial rigs, cages, deformation bones, or morphs for the
  final visible result;
- use volume compensation or regional fields to avoid hollow-looking dents;
- reserve tetrahedral or other volumetric simulation for selected regions where
  unpredictable physical response is important;
- pass reaction forces back into physical animation when two-way response is
  required.

Literal render-mesh collision and unrestricted full-character soft-body
simulation are not currently considered the default solution.

## CLI and external-agent design

The canonical body document should be readable and versionable. The CLI edits
or patches that document and invokes deterministic compiler stages.

Illustrative commands, not a committed interface:

```bash
creature new fox_01 --body-plan biped

creature part add fox_01 \
  --id left_leg \
  --type digitigrade-limb \
  --parent torso \
  --socket pelvis.left

creature part set fox_01 left_leg \
  --length 0.91 \
  --thickness 0.15

creature build fox_01
creature validate fox_01 --format json
creature render fox_01 --preset turntable
creature test fox_01 --scenario locomotion --debug-colliders
```

The external interface should eventually cover:

- document creation, querying, and patching;
- part addition, removal, attachment, mirroring, and parameter changes;
- compilation of volumes, surfaces, skeletons, collision, and deformation data;
- measurement and semantic inspection;
- validation, test poses, simulations, and interaction tests;
- headless previews, debug overlays, and turntables;
- snapshots, diffs, transactions, undo, and acceptance;
- export to runtime and interchange formats.

Structured validation should reduce dependence on visual inspection. Reports
may identify self-intersections, collapsed joints, invalid attachments, bad
weights, excessive strain, balance failure, collision instability, or budget
violations. Visual outputs can include silhouettes, depth, normals, semantic
regions, bones, collision shapes, and deformation heat maps.

An external AI may use those tools and artifacts, but no AI is required for the
core application to function.

## What appears feasible

There is high confidence in the basic possibility of:

- a declarative body graph and deterministic compiler;
- a CLI/API suitable for human and external-agent use;
- generated skeletons from a body graph;
- smooth connected surfaces generated from implicit volumes;
- simple automatic skinning and analytic collision proxies;
- semantic fields and procedural colours;
- exporting generated creatures to an existing runtime engine.

There is meaningful precedent for skeleton-driven base-mesh generation, volume
to mesh conversion, implicit skinning, animation retargeting, GPU distance-field
collision, and regional volumetric soft bodies. Creature Kernel's novelty would
primarily be their unification under one semantic, programmable creature model.

## Known uncertainties

### Surface and topology

- Which surface representation should be primary: signed-distance fields,
  skeleton-and-radius meshes, generalized cylinders, parametric patches, or a
  hybrid?
- Can generated topology deform acceptably around shoulders, hips, mouths,
  paws, and other difficult regions without handcrafted templates?
- Is triangle topology adequate for the initial stylized target?
- When and how should automatic remeshing or retopology occur?
- How are sharp and thin features preserved without unwanted smoothing?

### Generation lifecycle

- What is the maximum acceptable compile time for a new creature?
- Where may compilation occur: external tool, character creator, loading screen,
  background job, or gameplay?
- Are creatures normally compiled once into conventional game assets?
- Which proportion and material changes remain live without recompilation?
- Which structural changes require a new surface and runtime package?
- Can body structure change during gameplay, and if so, how is the replacement
  synchronized with animation, collision, clothing, and saved state?
- Does the implicit representation remain active at runtime or become purely
  compiled data?
- What is baked, what remains procedural, and what can be regenerated safely?

Compilation outside the frame loop is now accepted as compatible with the game
vision. The exact mutation and asynchronous recompilation boundaries have not
been decided.

### Runtime budget and hardware

- Is the primary target 30 FPS, 60 FPS, or a selectable quality mode?
- What display resolution and high-end hardware class define the initial target?
- How many visible, nearby, and actively interacting characters must be supported?
- How many regions may run the highest soft-body tier simultaneously?
- What CPU, GPU, memory, and transfer budgets belong to each solver layer?
- How aggressively should distance, visibility, and interaction state change
  simulation quality?
- Is the first target single-player, deterministic replay, or networked play?
- Which runtime data must be deterministic, authoritative, or recordable?
- Must the GPU path support multiple vendors, or may an initial backend require
  a particular compute platform?
- What minimum fallback must exist when advanced GPU deformation is unavailable?

### Body-grammar scope

- What is the first supported morphology family?
- How are plantigrade and digitigrade structures related?
- When do quadrupeds, tails, wings, additional limbs, or taur body plans enter
  scope?
- Are arbitrary graphs permitted, or only combinations validated by known
  generators?
- How are invalid or physically impossible assemblies reported?

### Animation and control

- How is locomotion produced across different proportions and limb counts?
- Is motion authored, procedural, optimized, learned, or hybrid?
- How are balance, centre of mass, gait, and support transitions represented?
- How do interactions remain stable when body proportions differ radically?
- What should be shared between offline animation generation and runtime IK?

### Deformation and physics

- Which solver owns the final pose?
- How are IK, collision, balance, and physical animation conflicts resolved?
- Which deformation techniques belong in the first implementation?
- Does deformed render geometry also update collision?
- How are incompressibility, maximum strain, recovery, and material style
  represented consistently?
- How much two-way soft-body interaction is practical in real time?
- What degree of determinism is required for recording or networking?

### Detailed anatomy and features

- How are faces, expressions, eyelids, mouths, interiors, paws, fingers, claws,
  teeth, horns, and thin ears generated?
- Which features should be fused into the body surface and which remain separate?
- How do clothing, accessories, hair, and fur bind to regenerated bodies?
- Which specialized generators are essential before generic parts cease to look
  like assembled primitives?

### Visual quality and artistic ownership

- What does the first acceptable visual style look like?
- How much handcrafted artistic knowledge must be encoded in generators and
  presets even if no handcrafted base mesh is used?
- Can appealing results be achieved without a technical artist contributing to
  the generator rules?
- How will naturalistic rendering and deformation be supported later without
  embedding cartoon assumptions in the core body model?

### External assets

- What minimum metadata must an external artist provide?
- How are an existing skeleton and surface mapped to the body graph?
- Can arbitrary external topology be bound reliably to generated cages or fields?
- Which capabilities should be automatic, assisted, or explicitly unsupported?

### Platform and distribution

- Which language and geometry libraries should implement the compiler?
- Should Blender, OpenVDB, Houdini, or a custom geometry kernel be used for the
  earliest experiments?
- Which runtime engine receives the first adapter?
- Which deformable-body and GPU-compute backend receives the first experiment?
- Which asset and interchange formats are canonical?
- Is the eventual project a library, CLI, authoring application, engine plugin,
  open standard, or some combination?
- What licensing and contribution model should be used?

## Confidence assessment

| Area | Current confidence |
| --- | --- |
| Body document, CLI, and deterministic compiler | High |
| Semantic body graph and generated skeleton | High |
| Basic implicit creature surface | High |
| Procedural colours and semantic markings | High |
| Basic collision proxies | High |
| Good animation-ready topology | Medium to low |
| Attractive automatic joint deformation | Medium to low |
| Movement across arbitrary morphologies | Low |
| Stable general soft-body interactions | Low |
| Attractive output without substantial encoded artistic rules | Low |
| Equal-effort support for arbitrary creatures | Very low |

Universality is expected to exist inside the supported grammar. A novel
structure or behaviour outside that grammar will require a new generator,
capability module, or solver rule.

## Prospective proof of concept

No implementation plan has been approved, but the current smallest meaningful
experiment is approximately:

1. Define a minimal body-document schema.
2. Support a small set of volumetric primitives and smooth composition.
3. Generate one upright furry morphology family without a handcrafted base mesh.
4. Generate a skeleton and basic distance-derived skinning.
5. Attach semantic part fields and simple procedural colours.
6. Generate analytic collision proxies.
7. Export the result to an existing 3D runtime.
8. Produce headless turntables, debug overlays, and structured validation.
9. Generate many proportionally different examples from seeds and parameters.
10. Test whether they can all perform one shared pose, locomotion, and contact
    scenario without bespoke per-character setup.

The proof should test the central proposition rather than visual polish: one
body program generates geometry, semantics, rigging, collision, and interaction
metadata together.

## Next-step questions to expand later

The founding conversation intentionally stopped before resolving the following.
These questions should be expanded into design decisions, experiments, or
architecture records:

1. What exact result would prove Creature Kernel is valuable?
2. What is the first supported morphology and its allowed parameter range?
3. Is the first surface generated with SDFs, a skeleton-based skin algorithm,
   parametric patches, or a hybrid?
4. Where and when does first-version creature compilation run?
5. What mesh quality is sufficient for the first animation test?
6. What minimum facial and paw features are needed for the result to read as a
   furry character rather than a generic articulated blob?
7. How are semantic fields represented and preserved through surface extraction?
8. How are skinning weights derived, normalized, and validated?
9. What is the first animation or control test?
10. Which collision and deformation features belong in the first proof?
11. What structured metrics determine pass or failure?
12. Which host tools, libraries, language, and runtime engine minimize unrelated
    work?
13. What should the body-document and CLI interfaces look like?
14. How should deterministic seeds, compiler versions, snapshots, and diffs work?
15. When should external mesh conformance be attempted?
16. Which parts of the project are engineering, graphics research, or encoded
    artistic design?
17. What expertise or collaborators will eventually be required?
18. What licensing and repository strategy should be adopted?
19. What real-time performance target, display resolution, and reference hardware
    define success?
20. How many characters and high-quality deformable regions must run at once?
21. Which features are mandatory in the real-time path, optional at higher tiers,
    or cinematic-only?
22. What changes can occur live without recompilation?
23. Can topology-changing edits compile asynchronously, and what state persists
    across an avatar-package swap?
24. Which runtime representation owns collision after visible deformation?
25. What data must be deterministic for replay, saving, or networking?
26. What is the relationship between the real-time avatar and cinematic output?
27. Should learned deformation be part of the platform contract or only a backend
    optimization?
28. What minimum experience must remain available when advanced GPU features are
    disabled?

## Guiding principle

The central principle produced by the conversation is:

> Generate geometry, meaning, and physical behaviour from the same programmable
> body definition, and expose the entire process through deterministic tools.

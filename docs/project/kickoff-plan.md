# Project kickoff decision plan

Status: Active

Plan owner: Main orchestration thread

Decision owner: Ben

## Purpose

This plan turns the founding concept into an ordered programme of decisions,
research, experiments, and implementation gates. It is a project-management
document: it tracks what must be resolved without deciding product contracts or
architecture by itself.

The project is still pre-implementation. Existing architecture documents and
ADRs are proposals derived from the founding conversation, not inherited facts
that implementation must preserve.

## Working method

- Keep one kickoff item active at a time.
- The main thread prepares the evidence, alternatives, recommendation, and
  consequences before asking the decision owner for input.
- Ask the decision owner one bounded question at a time. Do not present an
  entire technology tree for simultaneous resolution.
- Delegate bounded searches, comparisons, mechanical work, and fresh-context
  review under the [AI delegation workflow](../developer-workflows/ai-delegation-and-review.md).
  Product and architecture synthesis remains in the main thread.
- Treat a prototype tool as disposable unless an ADR explicitly promotes it to
  a project dependency.
- Use experiments when geometry, visual quality, performance, or solver
  behaviour cannot be established from argument alone.
- Do not mark an ADR accepted without a current-revision adversarial review and
  explicit approval from the decision owner.
- Update canonical product, specification, architecture, research, and status
  documents when a decision changes their subject. This plan must not become a
  competing source of truth.

Kickoff item states are `queued`, `active`, `blocked`, `complete`, or `deferred`.
`Deferred` is a plan state, not an ADR state. An architecture proposal that is
not ready for decision remains `Proposed` or `Under Review` with its blocker
recorded.

## Decision presentation contract

For each human checkpoint, the main thread will present:

1. the single decision being requested;
2. the recommended answer and why;
3. credible alternatives and the strongest case for each;
4. what is known, assumed, and still unproven;
5. cost, reversibility, lock-in, licensing, and performance implications;
6. the evidence or follow-up experiment required;
7. the exact documents that will change.

Silence, prior conversational momentum, or implementation convenience does not
count as approval.

## Ordered kickoff sequence

### CK-KICK-000: Integrate the foundation baseline

State: active

Outcome:

- Inspect and integrate the governance-foundation pull request while preserving
  all four founding ADRs as proposals.
- Confirm documentation validation on the integrated revision.
- Establish appropriate default-branch protection and merge hygiene.
- Begin subsequent work from the integrated default branch rather than allowing
  the scaffold review branch to become an accidental long-lived trunk.

Human checkpoint: approve any externally consequential merge or repository-rule
change after the main thread reports the exact proposed action.

### CK-KICK-001: Review the decision process itself

State: queued

Outcome:

- Commission a fresh-context adversarial review of ADR-0001 revision 1.
- Test whether the authority model is useful without creating unnecessary
  process overhead.
- Respond to objections, revise the proposal if necessary, and ask the decision
  owner to accept, reject, request revision, or leave it proposed with a named
  blocker.
- Verify revision-aware review validation before accepting the first ADR.

This is the first architecture decision because every later decision depends on
knowing how proposals, evidence, reviews, and acceptance relate.

### CK-KICK-002: Define the first proof charter

State: queued

Outcome:

- Decide the smallest result that would justify continuing the project.
- Separate Stage 1 generation proof, Stage 2 embodiment proof, and Stage 3
  real-time interaction proof so one prototype is not expected to solve the
  entire vision.
- Define observable exit criteria, representative outputs, and explicit
  exclusions for the first proof.
- Convert RQ-001 through RQ-003 into a bounded experiment direction without
  pretending uncertain quality thresholds are already measurements.

Human questions, asked separately when this item is active:

1. What visible result would make the procedural-generation premise valuable?
2. How much of rigging, animation, contact, and deformation must the first proof
   demonstrate rather than merely preserve a path toward?
3. What stylized visual-quality floor is sufficient for a research prototype?

### CK-KICK-003: Review the semantic source-of-truth proposal

State: queued

Outcome:

- Commission a fresh-context adversarial review of ADR-0002 revision 1.
- Challenge whether a declarative body document and resolved semantic graph can
  remain authoritative across procedural generation, artist overrides, and
  eventual external meshes.
- Keep the high-level source-of-truth decision separate from YAML, JSON, schema,
  database, or programming-language choices.
- Revise and obtain an explicit disposition from the decision owner.

### CK-KICK-004: Review the real-time-first boundary

State: queued

Outcome:

- Commission a fresh-context adversarial review of ADR-0003 revision 1.
- Challenge the compiled-avatar boundary, runtime mutation assumptions, quality
  negotiation, and the risk that the motivating interactions become offline
  only.
- Decide the architectural direction without inventing numerical performance
  claims. Hardware, frame, character, and solver budgets remain evidence-driven.
- Revise and obtain an explicit disposition from the decision owner.

### CK-KICK-005: Review the external automation boundary

State: queued

Outcome:

- Commission a fresh-context adversarial review of ADR-0004 revision 1.
- Challenge whether CLI and API operations can represent interactive editing,
  preview, diagnostics, transactions, and external-agent use without a private
  GUI-only path.
- Keep the interface boundary separate from concrete command syntax, transport,
  or embedded-AI features.
- Revise and obtain an explicit disposition from the decision owner.

### CK-KICK-006: Bound the first morphology family

State: queued

Prerequisite: CK-KICK-002.

Outcome:

- Choose one initial furry body family and a deliberately limited variation
  envelope.
- Define required and optional modules, attachment rules, parameter ranges, and
  invalid assemblies.
- Select a small fixture set containing substantially different proportions so
  the system cannot succeed through one disguised template.
- Name deferred families explicitly rather than claiming arbitrary anatomy.

The initial proposal to evaluate is a stylized digitigrade furry biped family,
including torso, head and muzzle, ears, arms, hands or paws, legs and feet or
paws, and tail. It is not accepted merely because it appears here.

### CK-KICK-007: Define the native visual and semantic quality bar

State: queued

Prerequisite: CK-KICK-006.

Outcome:

- Define what makes generated output read as an intentional furry character
  instead of a collection of blended primitives.
- Select reference poses and views for shoulders, hips, muzzle, paws, branch
  junctions, and silhouette.
- Define watertightness, semantic-region preservation, determinism, and
  diagnostic requirements separately from subjective visual judgment.
- Choose how evidence will be retained through small fixtures, captures,
  metrics, and explicit human visual assessment.

### CK-KICK-008: Research surface-generation strategies

State: queued

Prerequisites: CK-KICK-006 and CK-KICK-007.

Outcome:

- Compare signed-distance fields, skeleton-radius or generalized-cylinder
  methods, patch systems, and credible hybrids against the fixed fixture set.
- Evaluate smooth junctions, thin and separate features, mouths and paws,
  semantic-field preservation, animation topology, remeshing requirements,
  determinism, licensing, platform support, and runtime implications.
- Record current primary references and tool/library constraints.
- Design a falsifiable first geometry experiment. Do not select the production
  surface architecture from a prose survey alone.

### CK-KICK-009: Choose a disposable geometry experiment stack

State: queued

Prerequisite: CK-KICK-008.

Outcome:

- Select the quickest reproducible environment capable of testing the surface
  hypotheses.
- Explicitly state whether it is only an experiment host or a candidate
  production dependency.
- Register the experiment as `EXP-0001`, link its research questions, and update
  their state before execution. This registration satisfies the ledger trigger
  for the first surface-generation experiment.
- Resolve artifact storage first only if the experiment will create large
  outputs; otherwise retain small scripts, inputs, hashes, and summaries in Git.

This avoids choosing the permanent language and engine merely to make the first
mesh.

### CK-KICK-010: Run and review the first surface experiment

State: queued

Prerequisite: CK-KICK-009.

Outcome:

- Generate all fixed morphology fixtures without a handcrafted base mesh.
- Measure structural checks and retain comparable renders for subjective review.
- Test preservation of semantic identity and normalized local fields through
  surface extraction.
- Record failures and inconclusive cases, including features that require
  specialized modules rather than a universal field operation.
- Decide whether evidence supports a surface ADR, another bounded experiment,
  or a narrower proof.

### CK-KICK-011: Decide the initial surface architecture

State: queued

Prerequisite: decision-relevant evidence from CK-KICK-010.

Outcome:

- Write a revisioned surface/topology ADR with explicit alternatives and proof
  limits.
- Commission an independent adversarial review.
- Obtain an explicit human disposition before backend-specific compiler code
  becomes the architecture by accident.

### CK-KICK-012: Specify the minimal body document and body graph

State: queued

Prerequisites: disposition of ADR-0002 and enough evidence from CK-KICK-006
through CK-KICK-011.

Outcome:

- Define stable semantic IDs, namespaces, units, coordinate frames,
  measurements, parts, joints, attachments, sockets, capabilities, fields, and
  diagnostics needed by the first family.
- Define deterministic resolution, invalid input, extension, and resource-limit
  behaviour.
- Add representative schema-level valid and invalid fixtures alongside the
  specification. Compiler-consumed generation fixtures activate later when the
  first compiler reads a body document.
- Keep the semantic contract independent from generated mesh indices and the
  first host engine.

Human decisions will concern semantics and compatibility. Concrete syntax and
schema technology will be recommended separately where they are reversible.

### CK-KICK-013: Select the first implementation platform

State: queued

Prerequisites: CK-KICK-011 and a bounded CK-KICK-012 contract.

Outcome:

- Compare the core language and build system against geometry ecosystem,
  performance, memory safety, deterministic headless tooling, FFI, debugging,
  packaging, and contributor cost.
- Select the first production geometry backend or define an adapter boundary if
  the experiment backend should remain replaceable.
- Decide whether compiler and runtime require one language or an intentional
  cross-language boundary.
- Write and adversarially review the required ADR before creating implementation
  packages.

Candidate comparisons will be researched when this item becomes active because
library versions, licensing, and platform support change. Likely comparison
families include Rust, C++, C#, and a deliberate hybrid; they are not an implied
shortlist or decision.

### CK-KICK-014: Implement and audit the Stage 1 generation proof

State: queued

Prerequisite: accepted implementation and surface decisions.

Outcome:

- Parse and resolve the minimal body document.
- Activate a small compiler-consumed body-document fixture set with deterministic
  expected results.
- Generate the fixed body family, semantic fields, surface, basic appearance
  inputs, and diagnostics through a headless command.
- Prove reproducibility and evaluate the Stage 1 exit criteria.
- Use an independent evidence audit before claiming the generation premise is
  proved.

## Embodiment and runtime sequence

These items are tracked now so early choices preserve their path, but they must
not inflate the first surface proof.

### CK-KICK-015: Prove generated rigging and shared control

State: queued

- Select one shared reference-pose or animation scenario.
- Experiment with generated skeletons, limits, skin weights, and minimum joint
  correctives across the fixed body variation set.
- Define failures structurally and visually before selecting a permanent rigging
  technique.

### CK-KICK-016: Select the first host runtime and reference envelope

State: queued

- Compare current Godot, Unity, Unreal, and any credible narrower host against
  adapter isolation, rendering and compute access, physics integration,
  licensing, distribution constraints, tooling, and developer cost.
- Choose reference hardware, frame target, visible-character scenario, and a
  useful minimum fallback.
- Select an engine adapter only after current evidence is gathered; do not leak
  its object model into core specifications.

### CK-KICK-017: Define the runtime avatar package boundary

State: queued

- Define compiled versus dynamic data and the minimum loader contract.
- Choose provisional serialization for the first adapter.
- Delay durable compatibility and migration promises until the representation is
  sufficiently stable, but decide them before third-party persistence.

### CK-KICK-018: Design the contact and deformation solver stack

State: queued

- Define ownership and scheduling between animation, root alignment, IK,
  collision, balance, physical reaction, visible deformation, and regional
  simulation.
- Evaluate collision, compute, and deformable-body backends against fixed
  scenarios rather than searching for a universal solver.
- Assign effect classes to bones, morphs, cages, fields, or regional volumetric
  simulation with explicit capability negotiation and fallbacks.
- Include the motivating difficult cases: two-character contact, local bulging,
  radial opening or stretching, volume preservation, strain limits, recovery,
  and large body variation.

### CK-KICK-019: Prove bounded real-time interaction

State: queued

- Load generated avatars through the first adapter.
- Establish semantic contact between two substantially different generated
  bodies.
- Demonstrate at least one localized deformation and physical-response scenario
  within the declared reference budget.
- Demonstrate a lower-quality fallback when the advanced path is disabled.
- Record benchmark conditions and visual evidence before claiming real-time
  feasibility.

## Triggered and deferred decisions

These are retained so they are not forgotten, but asking for them during the
foundation phase would create premature work:

- Deterministic replay and networking: before runtime state becomes a durable
  multiplayer or replay contract.
- Large-artifact storage: before committing or publishing large generated
  meshes, caches, captures, or datasets.
- Project licence: before external contribution or distribution.
- External authored-mesh conformance: after native generation and semantic
  embodiment are proved.
- Second morphology family, general locomotion, balance, and package swapping:
  after the first family exposes which abstractions are genuinely reusable.
- Clothing, hair, dense fur, GUI, SDK, release automation, operations, SaaS, and
  cinematic-quality output: after their repository-evolution triggers are met.

## Completion boundary

The project is kicked off, rather than merely scaffolded, when:

- the foundation baseline is integrated;
- the governance proposal has a reviewed human disposition;
- all four founding ADRs have current adversarial reviews and explicit
  dispositions;
- the first proof, morphology family, variation fixtures, and visual criteria are
  bounded;
- the first surface experiment is registered with predeclared evidence;
- implementation begins only behind reviewed semantic, surface, and toolchain
  decisions.

The later embodiment and runtime items remain part of the programme even though
they are not prerequisites for starting the first geometry experiment.

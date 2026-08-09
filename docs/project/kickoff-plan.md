# Project kickoff decision plan

Status: Provisional round-based plan

Plan owner: Main orchestration thread

Decision owner: Ben

## Purpose

This plan turns the founding concept into an ordered programme of discussion
batches, decisions, research, experiments, and implementation gates. It is a
project-management document: it tracks what must be resolved without deciding
product contracts or architecture by itself.

The project is pre-implementation. Existing product and architecture documents
and decision records are proposed or provisional material, not inherited facts
that implementation must preserve.

This plan owns plan history, discussion scope, prerequisites, queued future work,
outputs, and activation triggers. [Project status](status.md) owns live round,
review, and owner state; the [decision registry](../decisions/registry.md) owns
exact decision metadata and review cells.

## Working method

- Work in rounds, with a discussion batch of roughly two to five related
  decisions or talking points.
- Finish the discussion batch before integrating its canonical document changes
  and Proposed decision-record revisions.
- After integration and validation, the main thread states
  `Recommended adversarial level: None|Single|Double — <one-line reason>` at
  the end of the substantive design-cycle handoff, then starts the selected
  risk-scaled adversarial review of the previous edit batch and independent
  next-round research concurrently when dependencies permit. `None` is not a
  substitute for review of a created or materially revised consequential DR;
  `Single` is the normal default, while `Double` uses two independent fresh
  passes with distinct named lenses only when justified.
- The fresh review examines the current proposal revision and affected
  canonical documents. Findings return to Ben and the main thread; decision-
  bearing findings are not auto-fixed and the process does not run a
  review-until-clean loop. Ben accepts, rejects, or requests revision only
  after the review response is recorded.
- The main thread prepares the evidence, alternatives, recommendation, and
  consequences before asking the decision owner for input. Ask one bounded human
  question at a time inside a batch.
- Delegate bounded searches, comparisons, mechanical work, and fresh-context
  review under the [AI delegation workflow](../developer-workflows/ai-delegation-and-review.md).
  Product and architecture synthesis remains in the main thread.
- Treat a prototype tool as disposable unless an accepted DR explicitly promotes
  it to a project dependency.
- Use experiments when geometry, visual quality, performance, or solver
  behaviour cannot be established from argument alone.
- Do not mark a DR accepted without a current-revision adversarial review or an
  explicit Ben waiver recorded in the DR, and explicit Ben approval.
- Update canonical product, specification, architecture, research, and status
  documents when a decision changes their subject. This plan must not become a
  competing source of truth.

Round states are `queued`, `active`, `blocked`, `complete`, and `deferred`.
`Deferred` is a plan state, not a DR state. A proposal that is not ready for
decision remains `Proposed` or `Under Review` with its blocker recorded.

## Decision presentation contract

For each human checkpoint, the main thread will present:

1. the single decision being requested;
2. the recommended answer and why;
3. credible alternatives and the strongest case for each;
4. what is known, assumed, and still unproven;
5. cost, reversibility, lock-in, licensing, and performance implications;
6. the evidence or follow-up experiment required; and
7. the exact documents that will change.

Silence, prior conversational momentum, or implementation convenience does not
count as approval.

## Round 0 — foundation scaffold (completed)

### CK-KICK-000: Integrate the foundation baseline

State: complete

Outcome:

- Inspect and integrate the governance-foundation scaffold while preserving the
  four founding decision records as proposals.
- Confirm documentation validation on the integrated revision.
- Establish appropriate default-branch protection and merge hygiene.
- Begin subsequent work from the integrated default branch rather than allowing
  the scaffold review branch to become an accidental long-lived trunk.

Human checkpoint: approve any externally consequential merge or repository-rule
change after the main thread reports the exact proposed action.

## Round 1 — governance and process (completed plan batch)

This batch established the neutral decision-record process and preserved
product and architecture material as provisional. Historical Revision 2 and
Revision 3 review evidence is preserved; this batch did not resolve or
re-review it. Later source, runtime, and automation proposals were queued for
subsequent rounds.

### CK-KICK-001: Review the decision process itself

Outcome:

- Preserve the historical fresh reviews of DR-0001 Revision 2 and Revision 3
  and their findings as advisory evidence.
- Integrate the Revision 5 governance proposal, neutral registry, templates,
  review naming, validator, authority indexes, and workflow.
- Keep the review evidence and later owner-disposition handoff linked from the
  canonical DR and tracked by the live [project status](status.md).

### Governance batch: authority, trigger, review, and ownership

Discussion topics:

- Keep product outcomes, normative specifications, target architecture,
  decision rationale, research, experiments/evidence, developer workflows,
  project status, and implementation/proof as distinct authorities.
- Replace the architecture-only mechanism with neutral DRs in `docs/decisions/`,
  using `DR-NNNN` identifiers and required `Scope` metadata for Governance,
  Product, Specification, Architecture, or cross-cutting combinations.
- Require a DR only for hard-to-reverse, cross-cutting, contractual/public,
  performance-defining, dependency/portability/licensing-locking, or likely to
  be disputed choices. Ordinary wording, derived detail, and reversible
  implementation stay lightweight.
- Use the batch pipeline: finish discussion, integrate canonical and Proposed
  DR changes, state the recommended risk-scaled review level at handoff, and
  return concise findings with the next batch. Decision-bearing findings return
  to Ben rather than entering an automatic fix/review loop. Double means one
  pass per reviewer on the current revision, not review-until-clean.
- Keep unaccepted assistant-synthesized product and architecture material
  Proposed or provisional.
- Keep the main Sol thread responsible for discussion, decomposition,
  synthesis, integration, validation, Git/PR/CI, and decisions. Prefer Luna for
  non-trivial edits, evidence gathering, and mechanical work; use fresh
  Sol-medium reviewers for foundational adversarial review; retain the
  Luna-xhigh and Luna-max gates and Sol-above-medium approval boundary.

Outputs:

- [DR-0001 Revision 5](../decisions/DR-0001-documentation-authority-and-review-process.md)
  governance proposal integrated, with its review evidence and
  owner-disposition handoff retained on the canonical record.
- [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md)
  through [DR-0004](../decisions/DR-0004-external-automation-through-cli-and-api.md)
  retained as early proposals with later Product, Specification, and
  Architecture review dependencies visible.
- Neutral registry, templates, review naming, validator, authority indexes,
  workflow, and status language operational.

Review and next batch:

- The Revision 2 and Revision 3 reviews remain historical evidence.
- Revision 5 is the lightweight Proposed process selected for the trial after
  considering those historical review recommendations and actual rounds of
  operation; its review selection is risk-scaled, with Single as the normal
  default and Double reserved for justified high-impact work.
- The main thread can independently research the Round 2 product-identity
  questions when dependencies permit.

## Round 2 — product identity and initial users (completed plan batch)

Prerequisite: Round 1 governance review is complete enough to operate the
process; no product decision is implied by this plan.

Discussion batch:

- Platform/compiler/runtime versus game/editor/general engine.
- Initial project developer/researcher versus downstream artist/game-developer
  users.
- Stylized furry focus and adult-interaction stress cases versus general
  embodiment architecture.
- Native generated creatures first and external mesh conformance later.

This batch remains bounded to product identity and initial users. Its discussion
may identify canonical documents or later decision-record work, but it does not
accept a product or architecture direction.

Output: DR-0005 Revision 1 records the four bounded product-identity topics and
defers detailed source semantics, compile/runtime mutation, automation contract
detail, first-proof morphology, backend, and budget questions. Its review
evidence is linked from the canonical DR response; live review and owner state
remain in [project status](status.md) and the [decision registry](../decisions/registry.md).

## Round 3 — source, semantics, and automation (completed plan batch)

Prerequisite: Round 2 product-identity discussion.

### Integrated Round 3 proposal output

The bounded proposal batch was integrated as Proposed; no acceptance is implied
by this plan:

- [DR-0002 Revision 2](../decisions/DR-0002-declarative-body-document-source-of-truth.md)
  records an authoritative semantic source set resolving to a per-build
  semantic body-graph snapshot; derived outputs remain derived.
- [DR-0006 Revision 1](../decisions/DR-0006-durable-semantic-and-artifact-identity.md)
  separates durable semantic identity from artifact/build identity and
  provenance; generated topology and array indices remain artifact-scoped and
  ephemeral.
- Specialized geometry, rig, collision, material, deformation, packaging, and
  runtime representations derive through the resolved graph's shared semantic
  lineage without requiring one mesh, topology, or universal solver.
- [DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md)
  records one shared deterministic domain-operation model for query, semantic
  mutation, resolution/compilation, validation, diagnostics, artifact
  inspection, and future transaction semantics, with user surfaces as adapters.
- The three current-revision review artifacts are linked from their target DR
  responses. The shared system-overview diagram was corrected mechanically
  after review; proposal and architecture prose were unchanged.

### CK-KICK-003: Review the semantic source-of-truth proposal

Outcome:

- Challenge whether a declarative body document and resolved semantic graph can
  remain authoritative across procedural generation, artist overrides, and
  eventual external meshes.
- Keep the high-level source-of-truth decision separate from YAML, JSON, schema,
  database, or programming-language choices.
- DR-0002 Revision 2 records the source-set and resolved-graph boundary above;
  exact formats, overrides, runtime mutation, and external-mesh conformance
  remain deferred.
- Preserve the source-set review obligations and defer exact formats, overrides,
  runtime mutation, and external-mesh conformance to later specification work.

### CK-KICK-005: Review the external automation boundary

Prerequisite: Round 2 product-identity and user-workflow discussion.

Outcome:

- Challenge whether CLI and API operations can represent interactive editing,
  preview, diagnostics, transactions, and external-agent use without a private
  GUI-only path.
- Keep the interface boundary separate from concrete command syntax, transport,
  or embedded-AI features.
- DR-0004 Revision 2 records the shared deterministic operation boundary above;
  concrete interface language, syntax, transport, and transaction details
  remain deferred.
- Preserve the shared-operation boundary while deferring concrete interface
  language, syntax, transport, and transaction details.

## Round 4 — real-time product boundary (completed plan batch)

Prerequisite: Round 2 product-identity discussion.

The Round 4 discussion is complete as a Proposed plan output. The round output
does not by itself accept DR-0003.

### CK-KICK-004: Review the real-time-first boundary

State: complete

Outcome:

- Record the bounded execution direction in [DR-0003 Revision
  2](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md):
  invariant and expensive work is initially outside the frame loop, with an
  optional future background recompilation path; per-frame work is bounded.
- Use a hybrid runtime representation that combines conventional bounded assets
  with only selected semantic fields, cages, SDFs, or regional structures useful
  for live behaviour.
- Permit compatible parameter updates in place while requiring recompilation
  for topology, body-plan, major attachment, collision, or capability changes;
  preserve the old avatar on failed authoring reloads and avoid promising
  mesh-index or incompatible solver-state continuity.
- Start authoring with blocking in-session reload and leave asynchronous hot
  swap as the later workflow; arbitrary fully live structural editing is not
  required.
- Use provisional bounded capability tiers and fallbacks, and require
  reproducible source resolution, compilation, semantic IDs, provenance, and
  build configuration while deferring stronger simulation determinism.
- Keep exact budgets, backends, serialization, morphology, networking, and
  hardware-dependent proof thresholds for later research and decisions.

## Round 5 — first proof boundaries, morphology, and quality (provisional)

Prerequisite: Round 2 product-identity discussion and sufficient user/outcome
context. This is a provisional planning sequence, not an accepted product
scope.

State: integrated/proposed — the settled first-proof charter and morphology
envelope are recorded in [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md)
and [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md).
The visual-quality protocol remains a separate Round 5 output.

### CK-KICK-002: Define the first proof charter

State: integrated/proposed

Discussion topics:

- Decide the smallest result that would justify continuing the project.
- Separate Stage 1 generation proof, Stage 2 embodiment proof, and Stage 3
  real-time interaction proof so one prototype is not expected to solve the
  entire vision.
- Define observable exit criteria, representative outputs, and explicit
  exclusions for the first proof.
- Convert RQ-001 through RQ-003 into a bounded experiment direction without
  pretending uncertain quality thresholds are already measurements.

Output: [DR-0007 Revision 1](../decisions/DR-0007-staged-first-proof-charter.md)
records the recommended three explicit proof stages. Stage 1 is generation
with minimal linked embodiment metadata and no animation, contact, deformation,
or real-time-performance claim; Stage 2 is generated skeleton/skinning plus a
shared pose/control scenario and semantic joint/contact regions without a
contact, deformation, or runtime claim; Stage 3 is semantic two-character
contact, selected localized response, declared hardware/performance evidence,
and a useful fallback. Tested and not-tested claims remain explicit.

Human questions, asked separately when active:

1. What visible result would make the procedural-generation premise valuable?
2. How much rigging, animation, contact, and deformation must the first proof
   demonstrate rather than merely preserve a path toward?
3. What stylized visual-quality floor is sufficient for a research prototype?

### CK-KICK-006: Bound the first morphology family

State: integrated/proposed

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

Output: [DR-0008 Revision 1](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
records the bounded stylized digitigrade furry biped, required semantic
modules, named optional ear and tail sockets, continuous variation categories,
explicitly invalid or deferred assemblies, and the fixed qualitative fixture
profiles. It also records minimal linked Stage 1 embodiment hooks. Exact ratios,
technologies, budgets, and backends remain deferred.

### CK-KICK-007: Define the native visual and semantic quality bar

State: integrated/proposed

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

Output: the proposed [visual-quality evaluation
protocol](../research/visual-quality-evaluation.md) separates reproducible
structural checks from a modest recorded human visual assessment over the fixed
profiles and views. It defines conspicuous seams, detached parts, collapsed
joints, and undifferentiated primitive blobs as failures of the subjective
floor while keeping the judgment explicitly subjective. Detailed facial and
digit features, dense fur/hair, clothing, adult contact/deformation, cinematic
rendering, and arbitrary anatomy remain outside the Stage 1 quality claim.

## Round 6 — surface research and geometry decision (provisional)

Prerequisites: CK-KICK-006 and CK-KICK-007.

### CK-KICK-008: Research surface-generation strategies

State: integrated/proposed

Compare signed-distance fields, skeleton-radius or generalized-cylinder methods,
patch systems, and credible hybrids against the fixed fixture set. Evaluate
smooth junctions, thin and separate features, mouths and paws, semantic-field
preservation, animation topology, remeshing requirements, determinism,
licensing, platform support, and runtime implications. Record references and
tool/library constraints, then design a falsifiable first geometry experiment.
Do not select production surface architecture from a prose survey alone. The
integrated Proposed hypotheses are [DR-0009 Revision 4](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
and [DR-0010 Revision 4](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md);
they guide Stage 1 evidence and do not select a production backend. Revision 4
records the approved evidence classification, strict comparative precedence,
empty-frontier rule, fairness/search controls, separate visual floor and
comparative frontier, and per-criterion interaction registration for DR-0009,
plus the canonical non-negative semantic-lineage distribution and independent
closed-form oracle coverage for DR-0010. Both remain Proposed with Owner
approval Pending and Review Pending. Their Revision 3 Double reviews are
historical and stale after the material revision; the approved findings await
new current-revision review. This plan does not imply acceptance.

### CK-KICK-009: Choose a disposable geometry experiment stack

State: provisional/queued

Prerequisite: CK-KICK-008.

Outcome:

- Select the quickest reproducible environment capable of testing the surface
  hypotheses.
- State whether it is only an experiment host or a candidate production
  dependency.
- Register the experiment as `EXP-0001`, link its research questions, and update
  their state before execution. This satisfies the ledger trigger for the first
  surface-generation experiment.
- Resolve artifact storage first only if large outputs will be created;
  otherwise retain small scripts, inputs, hashes, and summaries in Git.

This avoids choosing the permanent language and engine merely to make the first
mesh.

Current handoff: the neutral first experiment design remains Proposed and
manually maintained, with no evidence; `EXP-0001` remains unregistered and the
disposable experiment host remains unresolved. Next human discussion covers the
disposable host stack, exact four-profile values, grid sizes and resource
budget, and artifact retention.

### CK-KICK-010: Run and review the first surface experiment

State: provisional/queued

Prerequisite: CK-KICK-009.

Outcome:

- Generate all fixed morphology fixtures without a handcrafted base mesh.
- Measure structural checks and retain comparable renders for subjective review.
- Test preservation of semantic identity and normalized local fields through
  surface extraction.
- Record failures and inconclusive cases, including features requiring
  specialized modules rather than a universal field operation.
- Decide whether evidence supports a surface decision record, another bounded
  experiment, or a narrower proof.

### CK-KICK-011: Decide the initial surface architecture

State: provisional/queued

Prerequisite: decision-relevant evidence from CK-KICK-010.

Write a revisioned surface/topology DR with explicit alternatives and proof
limits, commission an independent adversarial review, and obtain Ben's explicit
disposition before backend-specific compiler code becomes the architecture by
accident.

## Round 7 — semantic contract (provisional)

### CK-KICK-012: Specify the minimal body document and body graph

State: provisional/queued

Prerequisites: disposition of DR-0002 and enough evidence from CK-KICK-006
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

Human decisions concern semantics and compatibility. Concrete syntax and schema
technology are recommended separately where they are reversible.

## Round 8 — implementation platform (provisional)

### CK-KICK-013: Select the first implementation platform

State: provisional/queued

Prerequisites: CK-KICK-011 and a bounded CK-KICK-012 contract.

Outcome:

- Compare the core language and build system against geometry ecosystem,
  performance, memory safety, deterministic headless tooling, FFI, debugging,
  packaging, and contributor cost.
- Select the first production geometry backend or define an adapter boundary if
  the experiment backend should remain replaceable.
- Decide whether compiler and runtime require one language or an intentional
  cross-language boundary.
- Write and adversarially review the required DR before creating implementation
  packages.

Candidate comparisons are researched when active because library versions,
licensing, and platform support change. Rust, C++, C#, and deliberate hybrids
are comparison families, not an implied shortlist or decision.

## Round 9 — Stage 1 generation proof (provisional)

### CK-KICK-014: Implement and audit the Stage 1 generation proof

State: provisional/queued

Prerequisite: accepted implementation and surface decisions.

Parse and resolve the minimal body document, activate compiler-consumed fixtures
with deterministic expected results, and generate the fixed body family,
semantic fields, surface, basic appearance inputs, and diagnostics through a
headless command. Prove reproducibility and evaluate Stage 1 exit criteria with
an independent evidence audit before claiming the generation premise is proved.

## Round 10 — embodiment and runtime (provisional)

These topics are tracked now so early choices preserve their path, but they must
not inflate the first surface proof. Each remains gated by the evidence and
accepted decisions from earlier rounds.

### CK-KICK-015: Prove generated rigging and shared control

State: provisional/queued

Prerequisite: Stage 1 generation proof and bounded body contract.

Select one shared reference-pose or animation scenario. Experiment with
generated skeletons, limits, skin weights, and minimum joint correctives across
the fixed body variation set. Define failures structurally and visually before
selecting a permanent rigging technique.

### CK-KICK-016: Select the first host runtime and reference envelope

State: provisional/queued

Prerequisite: Stage 1 proof and relevant runtime boundary disposition.

Compare current Godot, Unity, Unreal, and any credible narrower host against
adapter isolation, rendering and compute access, physics integration, licensing,
distribution constraints, tooling, and developer cost. Choose reference
hardware, frame target, visible-character scenario, and a useful minimum
fallback. Select an engine adapter only after current evidence is gathered; do
not leak its object model into core specifications.

### CK-KICK-017: Define the runtime avatar package boundary

State: provisional/queued

Prerequisite: CK-KICK-016 evidence.

Define compiled versus dynamic data and the minimum loader contract. Choose
provisional serialization for the first adapter. Delay durable compatibility and
migration promises until the representation is sufficiently stable, but decide
them before third-party persistence.

### CK-KICK-018: Design the contact and deformation solver stack

State: provisional/queued

Prerequisite: CK-KICK-015 through CK-KICK-017.

Define ownership and scheduling between animation, root alignment, IK,
collision, balance, physical reaction, visible deformation, and regional
simulation. Evaluate collision, compute, and deformable-body backends against
fixed scenarios rather than searching for a universal solver. Assign effect
classes to bones, morphs, cages, fields, or regional volumetric simulation with
explicit capability negotiation and fallbacks. Include two-character contact,
local bulging, radial opening or stretching, volume preservation, strain limits,
recovery, and large body variation.

### CK-KICK-019: Prove bounded real-time interaction

State: provisional/queued

Prerequisite: accepted runtime boundary, package, and solver decisions.

Load generated avatars through the first adapter, establish semantic contact
between two substantially different generated bodies, demonstrate at least one
localized deformation and physical-response scenario within the declared
reference budget, and demonstrate a lower-quality fallback when the advanced
path is disabled. Record benchmark conditions and visual evidence before
claiming real-time feasibility.

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

- Round 0 foundation baseline is integrated;
- the Round 1 governance proposal has a reviewed human disposition;
- all four founding DRs have current adversarial reviews and explicit
  dispositions;
- the first proof, morphology family, variation fixtures, and visual criteria
  are bounded;
- the first surface experiment is registered with predeclared evidence; and
- implementation begins only behind reviewed semantic, surface, and toolchain
  decisions.

The later embodiment and runtime items remain part of the programme even though
they are not prerequisites for starting the first geometry experiment.

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

- [DR-0002 Revision 5](../decisions/DR-0002-declarative-body-document-source-of-truth.md)
  records an authoritative semantic source set and exactly versioned authored
  dependencies resolving through a deterministic result envelope; only valid,
  supported input yields a compilable per-build semantic graph snapshot.
- [DR-0006 Revision 4](../decisions/DR-0006-durable-semantic-and-artifact-identity.md)
  separates structured semantic addresses from artifact/build identity and
  provenance; generated topology and array indices remain artifact-scoped and
  ephemeral.
- Specialized geometry, rig, collision, material, deformation, packaging, and
  runtime representations derive through the resolved graph's shared semantic
  lineage without requiring one mesh, topology, or universal solver.
- [DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md)
  records one shared deterministic domain-operation model for query, semantic
  mutation, resolution/compilation, validation, diagnostics, artifact
  inspection, and future transaction semantics, with user surfaces as adapters.
- The historical review artifacts remain linked from their target DR responses;
  the DR-0002 and DR-0006 artifacts are stale for the current Batch 1
  revisions, while DR-0004 remains at its reviewed revision. The shared
  system-overview diagram was corrected mechanically after that review; the
  current Batch 1 integration updates the affected canonical proposal and
  architecture prose while preserving the earlier evidence.

### CK-KICK-003: Review the semantic source-of-truth proposal

Outcome:

- Challenge whether a declarative body document and resolved semantic graph can
  remain authoritative across procedural generation, artist overrides, and
  eventual external meshes.
- Keep the high-level source-of-truth decision separate from YAML, JSON, schema,
  database, or programming-language choices.
- DR-0002 Revision 5 records the source-set, authored-dependency,
  result-envelope, and minimum inspectable non-authoritative resolved-graph
  boundary above; exact formats, schema technology, overrides, precedence,
  runtime mutation, and external-mesh conformance remain deferred.
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

Output: [DR-0008 Revision 5](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
records the bounded stylized digitigrade furry biped, its typed ownership tree,
reified non-ownership concepts with role-labelled relations, minimum functional
articulation roles, required semantic modules, named optional ear and tail
sockets, continuous variation categories, explicitly invalid or deferred
assemblies, and the frozen-fixture obligations. Exact ratios, coordinate
convention, surface primitives, technologies, budgets, and backends remain
deferred.

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

State: deferred (integrated; parked)

Compare candidate surface families and record references and tool/library
constraints, but leave production selection to later evidence. The resulting
[DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md),
[DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md),
and [first-surface design](../research/first-surface-experiment-design.md) are
preserved as Proposed confirmatory-research material, but are now parked and
non-blocking. No Revision 9, further review, owner disposition, or finding
discussion is active. Reactivation requires at least two runnable candidate
surface implementations and an intention to use a comparative outcome to
justify or select production architecture, or Ben's explicit reactivation.
Exploratory prototypes before that trigger produce observations only.

### CK-KICK-009: Choose a disposable exploratory geometry host

State: complete (selected for the exploratory slice)

Prerequisite: the parked CK-KICK-008 survey is context only; it is not a
blocker.

Outcome:

- Use a disposable Python discovery host with NumPy for dense fields,
  scikit-image marching cubes for extraction, and trimesh for inspection and
  export. Versions and the environment will be pinned when implementation
  begins.
- Keep project-owned conceptual seams for body resolution, field evaluation,
  surface extraction, mesh validation, and artifact writing. The host libraries
  remain replaceable adapters behind those seams.
- Keep the discovery host distinct from any future production language,
  geometry backend, schema, artifact format, or runtime dependency. Nothing in
  this choice promotes Python or these libraries to production.
- Keep small scripts, inputs, hashes, diagnostics, and summaries attributable;
  defer large-artifact storage until it is actually needed.

This makes the first executable surface useful without registering `EXP-0001`
or making a formal comparative claim. The parked first-surface design remains
preserved and non-blocking. No DR or adversarial review is required for this
reversible exploratory host choice.

### CK-KICK-010: Run the first surface exploration

State: implemented; evidence recorded; Single independent implementation
review completed with findings disposition recorded in `RESULTS.md` (not
clean)

Prerequisite: CK-KICK-009.

Outcome:

- Implement one valid creature fixture and one intentionally invalid fixture.
- For the valid fixture, resolve a small semantic graph; create analytic
  capsule/ellipsoid volumes with rigid transforms and one deterministic
  union/smooth blend; sample a fixed dense grid; extract one visible mesh with
  marching cubes; retain a simple source-linked semantic-region channel; and
  emit structured validation/mesh diagnostics and build/provenance identity
  through one reproducible headless command.
- Produce a graph snapshot, a deterministically ordered debug mesh (provisionally
  PLY with a sidecar or project-owned semantic data, with an optional GLB
  preview), semantic-region data, diagnostics JSON, and build/provenance
  hashes. Exact CLI spelling, temporary fixture syntax, PLY details, and
  preview format remain reversible implementation choices.
- Keep rigging, animation, collision, deformation, physics, engine
  integration, performance claims, the four-profile Stage 1 gate, formal
  comparative experiment/`EXP-0001`, and production surface selection out of
  this slice.
- Record commands, inputs, configuration, observations, failures, and
  limitations using the lightweight experiment workflow. Observations may
  refine the executable spine but must not claim DR-0009/0010 support or reject.

The bounded implementation and its local observations are recorded in
[`experiments/ck-kick-010-walking-skeleton/RESULTS.md`](../../experiments/ck-kick-010-walking-skeleton/RESULTS.md).
The record is deliberately unregistered: it does not create `EXP-0001`, claim
Stage 1, select a production surface, or reactivate the parked DR-0009/0010
material. The selected Single independent implementation review is complete;
its five substantive actionable findings, trailing-whitespace finding, and
dispositions are recorded in `RESULTS.md`. Main consolidated validation passed
after the corrections; no second review or review-until-clean pass was run.
Normal human design discussion resumes at CK-KICK-012 unless the review or
evidence exposes a specific CK-KICK-011 need.

#### Temporary semantic-input choices (Ben-approved; provisional/disposable)

On 2026-08-09 Ben approved all four reviewed boundary corrections and the
technical spike-planning selections below for this walking-skeleton
exploration only. They are reversible implementation-planning inputs, not a
permanent product or specification contract, production architecture, or new
decision record. DR-0009 and DR-0010 remain parked and unchanged.

The temporary semantic input remains a minimal JSON fixture with a small
code-level validator; do not introduce a formal JSON Schema. The temporary
envelope includes `fixture_id`, `spike_revision`, a deterministic `seed`, and
typed body nodes and parameters. Exact fixture syntax and file layout remain
disposable.

The four corrected boundaries are:

1. Resolve the fixture into a rooted typed ownership tree with deterministic
   source-node labels, parent-local transforms, left/right metadata, and named
   attachment sockets. The labels are stable only for deterministic reruns of
   the same input under the same `spike_revision`; they are not durable
   semantic IDs and do not establish a cross-revision namespace. The later
   CK-KICK-012 Batch 1 contract now records durable structured semantic
   addresses in DR-0006 Revision 4. The tree bounds this
   disposable spike's representation and must not imply that the permanent
   graph is restricted to a tree.
2. The valid fixture contains a torso, pelvis, head, muzzle, paired arms with
   simplified hand/paw modules, paired digitigrade thigh/shin-hock/foot-paw
   chains, and one optional predefined ear or tail attachment exercising a
   named socket. The invalid fixture omits `right_shin`. Its primary
   validation result is `MISSING_REQUIRED_MODULE`, with validation-phase
   precedence and early termination before field evaluation or meshing. The
   diagnostic code/path is stable only within the current `spike_revision`.
3. Use a temporary glTF-following coordinate and unit convention:
   right-handed, `+Y` up, `+Z` creature-forward, `-X` creature-right, and
   metres. Keep all transforms parent-local and make resolved world transforms
   explicit. Provenance must record units, coordinate basis, and the actual
   export transform. The valid fixture must include a known asymmetric
   left/right landmark, and export validation must verify that landmark after
   export. If an adapter applies a negative-determinant transform, it must
   correct and test triangle winding and normals. Host adapters may convert
   this convention; it is spike-only and is not a normative `spec/` contract.
4. At each generated vertex, evaluate every named primitive's raw signed
   normalized implicit field, choose the lowest value, and break exact ties by
   source-node label. This is winner-only debug attribution: it is not weighted
   lineage and is not DR-0010 evidence. The winning label is distinct from the
   artifact-local vertex index, which remains ephemeral debug-mesh data.

#### Technical spike-planning selections (2 / 2 / 2 / 3 / 2)

These five selections are also provisional and disposable. They constrain this
spike's implementation and proof surface only; they do not establish Stage 1
thresholds, production surface semantics, or a runtime/rigging/physics
contract.

1. **Selection 2 — signed normalized implicit fields.** Primitive fields are
   not true signed-distance fields or collision-ready distances. For a
   capsule, use `distance-to-segment / radius - 1`; for an ellipsoid, use
   `sqrt((x/rx)^2 + (y/ry)^2 + (z/rz)^2) - 1`. Negative is inside, zero is the
   surface, and positive is outside. Use the zero isovalue. Combine primitives
   through one explicitly deterministic, provisionally fixed smooth-min
   configuration and operand order. Record the exact operator and parameter
   in the run configuration; do not claim production surface semantics.
2. **Selection 2 — resolved-AABB grid.** Derive grid bounds from the resolved
   primitive AABB, expand by provisional `0.10 m` padding, and use fixed
   `128^3` samples. Record bounds, origin, spacing, axis order, padding, and
   isovalue. Fail rather than silently expanding if any sampled domain-face
   value is nonpositive, because that means the sampled exterior is not clear
   of the zero surface. These are debug settings, not Stage 1 thresholds.
3. **Selection 2 — complete staged bundle publication.** Require an explicit
   output path that does not exist; refuse every existing target, including a
   file, directory, or symlink, with no overwrite mode. Reject unsafe or broad
   targets before staging, including at minimum the filesystem root, user
   home, repository root, and disposable host root. Stage in a newly created
   sibling path under the same parent, validate the complete bundle, and
   publish only while the final target remains absent, using a same-filesystem
   atomic rename where supported. A successful provisional bundle contains
   `manifest.json`, `resolved_graph.json`, `mesh.ply`, `semantic_regions.json`,
   and `diagnostics.json`. The invalid fixture publishes its complete
   diagnostics-only bundle to the new target, exits nonzero, and publishes no
   mesh. An unexpected failure or publication race leaves any pre-existing
   target untouched and removes only this invocation's staging directory.
   Repeatability checks use separate new output targets. Deterministic files
   exclude timestamps, absolute paths, random IDs, and temporary names; exact
   staging-name mechanics remain implementation detail.
4. **Selection 3 — scoped artifact determinism.** Canonicalize semantic JSON
   deterministically and SHA-256 every final artifact. The manifest records
   hashes for the other bundle artifacts without self-reference; its own hash
   may be reported outside the manifest. Derive build identity from canonical
   input/configuration, seed, compiler/source revision, and dependency
   versions. Exact same-environment reruns must match the relevant artifact
   hashes. Perform structural and semantic checks separately. Do not claim
   cross-platform bit-exact determinism; mesh indices remain artifact-local.
5. **Selection 2 — structural minimum success gate.** Check unique spike-local
   source labels; a required and connected graph; finite transforms and
   parameters; positive radii; a finite field with inside/outside samples, a
   zero crossing, and only positive samples on every domain face; a nonempty
   finite indexed triangular mesh with no zero-area faces and one connected
   closed component for the valid fixture; and exactly one valid winner label
   per vertex with matching cardinality. Two clean valid reruns must match
   hashes. Two invalid reruns must produce the primary expected diagnostic and
   no mesh. This gate
   explicitly excludes Stage 1 visual, performance, and production claims and
   all runtime, rigging, and physics concerns.

### CK-KICK-011: Decide the initial surface architecture

State: queued (optional; risk-driven)

Prerequisite: useful exploratory evidence from CK-KICK-010 and a genuine need
to justify a production surface choice.

Use exploratory evidence to frame the alternatives and proof limits. Activate
the parked confirmatory protocol only if at least two runnable candidates exist
and a comparative outcome is needed; otherwise make a bounded, reversible
surface decision when appropriate. A consequential production choice still
gets its own DR and review before backend-specific compiler code locks it in.

## Round 7 — semantic contract (provisional)

### CK-KICK-012: Specify the minimal body document and body graph

State: active (Batches 1, 4, 5, and 6 integrated as Proposed documentation;
the current CK-KICK-012 Batch 6 Double review is Complete; DR-0002 Revision 8,
DR-0008 Revision 8, DR-0011 Revision 4, and DR-0012 Revision 3 remain Proposed
with Owner approval Pending and Review Complete; seven findings are pending Ben
discussion and owner disposition; the Batch 5
review is stale historical evidence)

Prerequisites: the exploratory executable spine and enough semantic context to
define a minimal useful input/output; CK-KICK-011 is not required.

Outcome:

- Batch 1 was settled on 2026-08-09 and its seven review resolutions were
  approved on 2026-08-11; all are integrated as Proposed documentation. A
  resolved source set has one unique owner per source namespace. Namespace
  collisions require an authored, deterministic, collision-free remapping
  across every contributed semantic address; implicit shared ownership is not
  allowed. Every outcome-affecting external authored asset remains an exactly
  versioned source-set dependency.
- Every phase and diagnostic belongs to one authoritative operation-result
  envelope: loading, syntax/schema/contract, dependencies, resources,
  semantic resolution, and invariants. A validated snapshot is optional and
  exists only for valid-supported success; snapshot diagnostics are a derived
  persisted subset. Semantically invalid and well-formed-but-unsupported
  partial graphs are non-compilable, non-contractual debug data. Exact phase
  names and diagnostic codes remain deferred.
- The first grammar is a bounded typed ownership tree with reified,
  role-labelled non-ownership concepts. Part is structural/owned; Joint is an
  articulation relation with frames, not a bone/solver; Socket is a host
  interface frame; Attachment maps a module to a socket, not automatically a
  joint; Region is overlapping and never ownership; Capability is a queryable
  affordance; and Field is representation-neutral spatial intent/channel with
  lineage. Batch 4 refines the earlier role shorthand into the typed Part,
  Joint, landmark, Socket, and Attachment chain recorded below. These roles do
  not claim bone, solver, rig, or anatomy fidelity.
- Transforms own reference-frame placement; typed dimensions own size/extents;
  anchors/landmarks have authored or derived provenance; ratios are derived
  only; and conflicting constraints diagnose rather than silently choosing.
  Sources declare units, handedness, up, and forward, then normalize to a
  contract-revision canonical internal basis with conversion provenance.
  Distinct local/reference, joint, socket/mating, derived world/reference,
  and runtime-pose frames are required. Exact canonical axes, units, rotation,
  scale, and shear remain deferred.
- Fixture expected outcomes freeze as valid-supported, semantically invalid, or
  well-formed-but-unsupported, with a primary diagnostic class/code frozen for
  every non-success fixture. Only valid-supported fixtures count toward the
  Stage 1 gate. Representative schema-level fixtures and compiler-consumed
  generation fixtures activate later when the first compiler reads a body
  document.
- Keep the semantic contract independent from generated mesh indices and the
  first host engine. Exact syntax/schema technology, coordinate convention,
  numeric ranges, surface primitives, identity address serialization,
  structural-edit lifecycle/remap semantics, geometry backend, surface,
  animation, physics, and runtime choices remain deferred. The Rust/Cargo
  platform direction is tracked separately in CK-KICK-013 as Proposed.
- The first parser and resolver proposals now activate the
  [`spec/body-document/`](../../spec/body-document/README.md) and
  [`spec/body-graph/`](../../spec/body-graph/README.md) contract families.
  Their implementation packages and compiler-consumed fixtures remain
  unactivated.

- Batch 6 is discussion-approved and integrated below as Proposed material. It
  resolves status/primary ordering, descendant-owned mating Socket placement,
  and Attachment cardinality without accepting or silently replacing the
  decision records. The affected DR revisions remain Proposed with Owner
  approval Pending and Review Complete; seven findings remain pending Ben
  discussion and owner disposition.

The Batch 1 and Batch 4 discussion selections and review resolutions are not DR
acceptance. The prior revisions have complete review evidence. Batch 5 and
Batch 6 are discussion-approved and integrated into the canonical product,
specification, architecture, and project documents as Proposed material. The
CK-KICK-012 Batch 5 Double review at commit
`a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical evidence. The
current CK-KICK-012 Batch 6 Double review is Complete. DR-0002 Revision 8,
DR-0008 Revision 8, DR-0011 Revision 4, and DR-0012 Revision 3 remain Proposed
with Owner approval Pending and Review Complete; seven findings are pending Ben
discussion and owner disposition; no acceptance or clean review is implied.
The prior Batch 4 and Batch 5 reviews remain
preserved as historical evidence.
DR-0006 remains Proposed with its current revision's review evidence. The
cross-cutting proposal is
[DR-0012: initial body-document encoding, resolution, and
compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
CK-KICK-012 remains active; the current review findings require Ben discussion
and owner disposition, so this proposal does not complete the round or imply
owner acceptance.

### Batch 4 — encoding, resolution, and compatibility (discussion-approved)

On 2026-08-11 Ben approved the following CK-KICK-012 Batch 4 resolutions in
discussion. They are integrated here as Proposed contract material only; they
do not accept or silently replace the decision records.

- The identity-bearing embodied concepts are Part, Joint, Socket, Attachment,
  Region, Capability, and Field. Module is an authored reusable scope that
  instantiates concepts, not an embodied graph concept. Landmark, anchor,
  dimension, and frame are typed owned records addressed through owner and
  role.
- Joint is a directed identity-bearing relation with exactly one proximal Part
  and one distal Part, with endpoint frames relative to each. Socket is a
  Part-owned named interface. Attachment connects one host Socket to one
  mating Socket and does not imply articulation.
- The pelvis Part owns the root-reference frame. The minimum typed Stage 1
  chain is pelvis → spine Joint → torso/chest Part → neck-base Joint → neck Part →
  head-base Joint → head. Arms use shoulder/elbow/wrist Joints between the
  named torso, upper-arm, forearm, and hand/paw Parts, ending at a paw-base
  landmark/Socket. Legs use hip/knee/hock-or-ankle Joints between pelvis,
  thigh, lower-leg, and foot/paw Parts, ending at a paw-base landmark/Socket.
  Ear/tail modules use Attachment; a movable tail also uses a separate Joint.
  These are semantic roles and frames, not bone, solver, rig, or anatomy
  fidelity commitments.
- Conflict claims target owner address, property role, and frame/context and
  compare after normalization. Authored claims and explicit invariants must
  be jointly satisfiable within contract tolerance; derived/defaulted values
  never override authored claims and no hidden inferred equations are allowed.
  A conflict is a semantic-invalid deterministic diagnostic and publishes no
  success snapshot.
- Resolver phases are resource/input admission; syntax/schema/contract;
  dependencies; namespaces/identity/references; ownership/typed relations;
  unit/frame normalization and value derivation; semantic invariants; and
  success publication. Fatal phases block dependent work while independent
  diagnostics within a phase accumulate. Provenance distinguishes authored,
  defaulted, and derived values; required unresolved or ambiguous values cannot
  succeed.
- Unknown core members fail. Explicit namespaced extensions carry namespace,
  revision, required/optional indication, and opaque payload. Unsupported
  required extensions are unsupported; unsupported optional extensions are
  preserved opaquely and have no core semantic effect. Machine diagnostic
  identity and order are stable contract data; human messages are not
  compatibility keys.
- The initial source adapter is one strict UTF-8 JSON document: duplicate keys,
  comments, includes, and evaluation are rejected. JSON Schema Draft 2020-12
  is the proposed structural-validation vocabulary, while CK semantic
  resolution owns graph meaning. Exact semantic contract family and revision
  recognition is required; no silent migration or downgrade is allowed, and
  explicit migration emits a new source. Semantic contract identity is separate
  from compiler/build/configuration/seed/dependency/artifact identity.
- Finite implementation-profile resource limits use source and aggregate bytes,
  string lengths/counts, nesting depth, object/array members, graph
  entities/relations, ownership depth, module/reference expansion, extension
  count/payload, numeric admissibility, diagnostics, and aggregate work/memory.
  Exact numeric limits, tolerances, serialized field names, canonical
  axes/units/rotation/scale/shear, source-map encoding, and canonical
  bytes/hashing remain deferred. Semantic equivalence concerns identities,
  relations, frames, values, provenance, and outcome, not text ordering or
  generated topology.
- The minimum Stage 1 graph invariants and outcome/resource fixtures are
  planned, including the cross-DR fixture matrix. The nonblocking exact
  dependency-revision obligation remains open before external authored
  dependencies activate. Compiler packages and compiler-consumed fixtures are
  not activated by this discussion batch.

Further CK-KICK-012 decisions concern exact serialized fields, numeric and frame
conventions, diagnostic codes, dependency revisions, and fixture contents; the
initial syntax and structural-schema technology are now Proposed selections.

Canonical references for the earlier batches are [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
Their prior revisions have review evidence. The current DR-0002 Revision 8,
DR-0008 Revision 8, DR-0011 Revision 4, and DR-0012 Revision 3 are Proposed
with Owner approval Pending and Review Complete. Seven findings are pending
Ben discussion and owner disposition; prior reviews are preserved as stale
historical evidence. Ben's owner disposition remains pending.

### Batch 5 — blocker resolutions (discussion-approved)

On 2026-08-11 Ben approved the six CK-KICK-012 blocker resolutions in
discussion. They are integrated in the canonical documents as Proposed
material only; they do not accept or silently replace the decision records.

- Part-to-Part containment is explicit and separate from typed relations. Every
  embodied Part, including a present optional module root, has exactly one path
  to the embodied root; containment supplies reference-transform inheritance,
  and containment/relation cycle checks are independent. Required Stage 1
  axial and limb Joints connect structural parent Parts to immediate children.
  An Attachment's host Part and module-root child must agree with declared
  containment; initially an attached root has one incoming Attachment.
- Attachment placement is derived conceptually from host Part/frame, host
  Socket, optional Attachment offset, and inverse mating Socket frame. A
  competing authored placement must agree within a later-defined tolerance or
  is semantic-invalid. Duplicate, detached, cyclic, or invalid endpoints are
  invalid; Attachment never implies a Joint.
- Resolved Joints materialize canonical proximal- and distal-frame typed
  records in the corresponding Part-local bases. Sockets materialize their
  interface frame in the owning-Part basis. Source references feed these
  records with provenance; no rig, bone, solver, limit, or runtime
  representation is selected.
- The operation status set is closed to success, input-failure,
  invalid-source, unsupported, dependency-failure, resource-limit, and
  internal-failure. Trust loss takes precedence, then configured resource
  exhaustion when completeness is lost, otherwise the earliest fatal phase;
  reached diagnostics remain, incomplete results are marked, and the primary
  diagnostic matches the status. Stage 1's three semantic fixture outcomes are
  separate from parser/dependency/resource/internal operation outcomes.
- Bootstrap order is byte/UTF-8/resource admission; strict duplicate-detecting
  JSON parse; top-level object and exactly one version-neutral family/revision
  discriminator; unsupported family/revision rejection before current-schema
  application; then exact revision-schema validation and unknown-field rules.
  Exact serialized spelling remains deferred.
- Hostile input uses streaming/token-aware limits for raw bytes, incremental
  UTF-8/tokens, pre-conversion string/number lengths, parse nesting/members,
  per-dependency and aggregate budgets, and pre-allocation graph/reference/
  module/work charging. Configured breaches are resource-limit; true process
  OOM is outside the guarantee and a surviving untrusted implementation is
  internal-failure. Exact profile thresholds remain deferred.

At the Batch 5 revision, these resolutions left exact serialized member and
diagnostic names, numeric budgets and tolerances, canonical
axes/units/rotation/scale/shear, dependency revision meaning, canonical
bytes/hashing, implementation language, and compiler fixture contents deferred.
CK-KICK-013 now tracks the separate Proposed Rust/Cargo platform direction.
At that historical revision, the affected decision records had completed their
review and three consolidated findings remained pending Ben discussion; that
review state is stale after Batch 6. CK-KICK-012 remains active and this batch
did not complete the round.

### Batch 6 — review-finding resolutions (discussion-approved)

On 2026-08-11 Ben approved the CK-KICK-012 Batch 6 review-finding resolutions
in discussion. They are integrated in the canonical documents as Proposed
material only; they do not accept or silently replace the decision records.

- Status selection retains internal-failure trust-loss precedence, then
  configured resource-limit when completeness is lost, then the earliest fatal
  phase. Within the selected earliest fatal phase, invalid-source outranks
  unsupported when both are established; other ordinary statuses use their
  phase-specific mappings. The primary is the first diagnostic establishing
  the final status under this normative deterministic ordering. Reserved
  primary capacity preserves that minimal matching candidate despite ordinary
  truncation. If arena exhaustion changes the final status to resource-limit,
  the reserved resource/truncation diagnostic satisfies the final-status-
  primary rule.
- A mating Socket may be owned by any Part in the attached root's containment
  subtree. Resolution composes the module-root-to-Socket-owner containment
  transform with the mating Socket owner's local frame before alignment and
  inversion. The Attachment result is the attached root's sole resolved
  child-local containment placement relative to its host parent. Descendants
  inherit only through containment; Attachment is not a parallel transform
  inheritance path. A competing authored root-local placement compares with
  this same canonical value within tolerance, with authored and derived
  provenance preserved.
- A present attached root has exactly one incoming active Attachment; an absent
  optional module has none. The initial host Socket capacity is one active
  Attachment. Repeated endpoint pairs, host Socket reuse, zero incoming for a
  present attached root, and multiple incoming Attachments are separately
  invalid conditions.

These resolutions leave exact serialized fields and diagnostic codes, numeric
budgets and tolerances, canonical axes/units/rotation/scale/shear,
dependency-revision meaning, canonical bytes/hashing, and fixture contents
deferred. DR-0002 Revision 8, DR-0008 Revision 8, DR-0011 Revision 4, and
DR-0012 Revision 3 remain Proposed with Owner approval Pending and Review
Complete. Seven findings are pending Ben discussion and owner disposition; the
CK-KICK-012 Batch 5 review is stale historical evidence. CK-KICK-012 remains
active pending owner disposition.

## Round 8 — implementation platform (provisional)

### CK-KICK-013: Select the first implementation platform

State: active (discussion-approved Proposed platform direction integrated;
Proposed DR-0013 Revision 1 has Owner approval Pending and Review Complete;
findings are pending Ben discussion and owner disposition; not accepted or
implemented)

Prerequisites: the exploratory host boundary and a bounded CK-KICK-012
contract. CK-KICK-011 is not an automatic prerequisite.

Outcome:

- Use a stable Rust production semantic/compiler core in a Cargo workspace,
  with an engine-independent Rust compiler library, thin CLI, and replaceable
  geometry boundary. No initial daemon or service is proposed.
- Use an in-process Rust CPU dense-field evaluator/extractor for Stage 1. If
  measured required capability or performance is missing, evaluate an isolated
  C++ worker/backend first; use in-process C ABI/FFI only if that worker is
  proven insufficient. This is not a Rust-only-forever promise or an
  advanced-Rust-geometry maturity claim.
- Keep Python for disposable experiments, evidence/render tooling, and visual
  workbench tasks, not as a production compiler dependency. Target
  reproducible execution/workbench on Linux x86_64 under WSL or native Linux;
  preserve portability while deferring native Windows and host-engine targets.
- Have the compiler write ordinary versioned artifacts plus a manifest, with an
  independent visual workbench consuming filesystem artifacts. This does not
  settle final avatar-package serialization or compatibility.
- Require a reproducible benchmark and hardware profile for every performance
  claim. The language/build DR acceptance trigger remains unsatisfied; do not
  create implementation packages or activate compiler fixtures.

The Rust-first direction has complete current Double-review evidence; its
findings remain pending Ben discussion and owner disposition. Geometry
libraries, licensing, platform support, and any C++
worker/FFI boundary remain evidence-driven; they are not settled by this
proposal. No implementation package or compiler fixture is activated.

## Round 9 — Stage 1 generation proof (provisional)

### CK-KICK-014: Implement and audit the Stage 1 generation proof

State: provisional/queued (implementation prerequisite not yet met)

Prerequisite: accepted implementation/platform and surface decisions; the
CK-KICK-013 language/build acceptance trigger is still unsatisfied.

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
- the governance proposal has a reviewed human disposition;
- provisional product and architecture directions are preserved with their
  review state and do not masquerade as accepted contracts;
- the first proof and initial morphology family are bounded enough for an
  exploratory implementation slice;
- a bounded exploratory executable walking skeleton accepts minimal semantic
  input, produces a visible or inspectable output and diagnostics, and has a
  reproducible command; and
- implementation boundaries remain explicit about disposable discovery host
  versus production platform. Formal confirmatory registration and a production
  surface decision are optional follow-on gates, not prerequisites for starting
  prototype work.

The later embodiment and runtime items remain part of the programme. Explicit
owner dispositions remain required before a Proposed DR is treated as an
accepted production commitment, but they are not prerequisites for disposable
exploration. The next normal discussion is the walking-skeleton scope,
exploratory host boundary, and minimal semantic input/output contract. The
parked DR-0009/0010 findings are not a current discussion agenda.

# DR-0008: First digitigrade morphology and Stage 1 embodiment envelope

ID: DR-0008

Scope: Product, Specification and architecture

Status: Proposed

Revision: 5

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-09

Date decided: —

Discussion approval date: 2026-08-11

Revision history: Revisions 1–4 and their reviews remain preserved as
historical evidence. Revision 3 recorded Ben's CK-KICK-012 Batch 1
morphology/grammar selection and Revision 4 recorded its first review-
resolution batch. On 2026-08-11 Ben approved the CK-KICK-012 Batch 3
articulation and fixture-outcome resolutions recorded in Revision 5. This
discussion approval is not DR acceptance: this revision remains Proposed with
Owner approval Pending until a current-revision review and Ben's owner
disposition are recorded. Reviews of Revision 4 are stale for this revision.

Supersedes: —

Superseded by: —

## Context

The initial product boundary calls for stylized furry characters generated
without a handcrafted base mesh, while the first supported family and its
variation envelope remain unresolved. A bounded family and fixed fixture set
are needed for comparable surface and embodiment evidence. The semantic source
and lineage boundaries in DR-0002 and DR-0006 require the family to be
described through semantic modules rather than per-fixture output patches.

Stage 1 also needs enough linked embodiment information to preserve the path to
Stage 2 without claiming animation, contact, or deformation success.

The semantic grammar must be bounded enough for the first family while keeping
ownership distinct from other typed relationships. It must also leave room for
future graph relationships without implying support for arbitrary anatomy.

## Decision

### First morphology family

**Recommendation: Option 1 — a bounded stylized digitigrade furry biped.** The
family has these required semantic modules:

- torso and pelvis;
- head with a simplified muzzle;
- two arms;
- simplified hands or paws;
- two digitigrade legs; and
- simplified feet or paws.

Ears and tail are optional predefined modules addressed through named semantic
sockets. Their presence, type, and style are explicit module choices rather
than arbitrary attachment graphs.

Continuous variation is permitted in stature, torso width and depth,
head/muzzle scale, arm and leg length, foot size and angle, ear length, and
tail length and curvature. Exact ratios are deferred to evidence; this record
does not define numeric parameter ranges.

The following are explicitly invalid or deferred for this family: extra limbs,
wings, a quadruped stance, arbitrary joint counts or attachment graphs,
detailed fingers or toes, arbitrary anatomy, plantigrade bodies, and other
morphology families.

The fixed qualitative fixture set contains at least four substantially
different profiles, including:

- compact, broad, short-limbed, large-head;
- tall, narrow, long-legged;
- slender, long-limbed; and
- stocky, broad-chested.

At least one fixture contrasts optional-module presence, absence, or style.
All fixtures use the same grammar and generators. No fixture may require a
per-fixture mesh, topology, or rig correction.

The project may select experiment hypotheses and the profiles they are meant
to discriminate before exact fixtures are frozen. Before EXP-0001 executes or
its evidence is used, it must freeze stable fixture IDs, concrete source
inputs, discriminating parameters, seed/configuration, provenance, expected
outcome classification, and the expected primary diagnostic class/code for
every non-success fixture. Each fixture's expected outcome is exactly one of
valid-supported, semantically invalid, or well-formed-but-unsupported. This
proposal does not invent the exact values or fixture files. The freeze is a
prerequisite to execution and evidence, not to deciding what to test. Only
valid-supported fixtures count in the Stage 1 success population; semantically
invalid and well-formed-but-unsupported fixtures remain diagnostic evidence.

### Body grammar and relation boundary

The first body grammar is a bounded typed ownership tree for the proposed
digitigrade biped family. It covers the required modules and predefined optional
ear/tail socket modules above. It also admits typed non-ownership relations for
joints, sockets/attachments, capabilities, and regions. Ownership edges and
relations are distinct: a relation does not imply ownership, and ownership does
not replace the relation's type or semantics.

Ownership is the sole containment tree. Durable non-ownership concepts may be
reified and connected through multiple role-labelled relations. The later body
specification owns endpoint roles, cardinality, permissible cycles, frame
placement, and multi-part region membership; this is not a general arbitrary
hypergraph or solver representation. The first grammar nevertheless supports
only this bounded family and its declared relation kinds; arbitrary anatomy
and arbitrary user-defined graph kinds are unsupported. Invalid or unsupported
assemblies receive structured diagnostics. Units and coordinate basis must be
declared, and local frames and resolved transforms must be explicit.

The first digitigrade family requires minimum functional articulation/landmark
roles sufficient for Stage 2 lineage. The required functional order and
adjacency is: axial lineage root reference → pelvis → chest → neck → head;
each arm shoulder → elbow → wrist → terminal paw-base; and each digitigrade
leg hip → knee → one hock/ankle functional articulation → terminal paw-base.
When present, a tail has a tail-base role and may have further segments. Ears
require no articulation in this first envelope. Root is a reference role,
torso is an owned part, and chest is the upper-torso landmark. These arrows
express required functional order/adjacency, not serialized syntax. These are
semantic roles and frames, not a fixed bone hierarchy or count, joint limits,
solver, rig implementation, or anatomical-fidelity claim. Exact role
spelling/serialization and further chains remain spec detail.

This decision does not choose an exact permanent coordinate convention, numeric
ranges, surface primitives, schema or syntax technology, or a new morphology
family. Those choices remain deferred to their owning specification, evidence,
and decision work.

### Stage 1 embodiment boundary

**Recommendation: Option 2 — source-linked semantic intent and lineage.**
Stage 1 must emit semantic joint frames and semantic region intent/lineage
linked to the resolved semantic graph. Stage 1 does not have to generate a
usable bone hierarchy, bind weights/skinning, analytic collision proxies, or
actual contact artifacts. Stage 2 generates a usable skeleton, skin weights,
and collision proxies and proves one shared pose/control scenario. Stage 3
owns actual contact, deformation, and runtime claims.

Stage 1 makes no animation, contact, deformation, or real-time-performance
claim. Exact representations, technologies, budgets, and backends remain
deferred.

### Fixture success and validity rule

**Recommendation: Option 2 — every declared valid-supported fixture must pass.**
Every declared valid-supported fixture must meet every mandatory Stage 1
structural check and the recorded subjective visual floor for the Stage 1 gate.
A failed or inconclusive valid-supported fixture means the gate has not passed,
while remaining useful evidence that must stay visible. A non-success fixture
must produce its expected outcome and diagnostic and is not counted as a valid
pass fixture. The frozen fixture outcome taxonomy is valid-supported,
semantically invalid, or
well-formed-but-unsupported. Every semantically invalid or unsupported fixture
freezes its expected primary diagnostic class/code; both are diagnostic
evidence, not Stage 1 success population.

## Consequences

- Surface and semantic experiments use a fixed, varied target rather than a
  disguised single template.
- Required modules and named optional sockets provide a stable semantic scope
  while leaving later families and detailed anatomy open.
- Continuous variation can expose generator failures without turning each
  fixture into a bespoke asset.
- Stage 1 can preserve embodiment lineage and regions without bringing Stage 2
  animation or Stage 3 contact/deformation infrastructure into the first
  generation proof.
- Stage 1's mandatory embodiment outputs are semantic joint frames and
  semantic region intent/lineage; usable skeletons, skin weights, collision
  proxies, actual contact artifacts, and later claims are deferred to their
  owning stages.
- Fixture hypotheses can be chosen before exact freezing, but EXP-0001 cannot
  execute or contribute evidence until stable IDs, concrete inputs,
  discriminating parameters, seed/configuration, provenance, validity
  classification, expected outcome, and expected primary diagnostic class/code
  for every non-success fixture are frozen.
- Every declared valid fixture is part of the Stage 1 gate; failed and
  inconclusive fixtures remain visible and prevent continuation. Only
  valid-supported fixtures count toward Stage 1 success; semantically invalid
  and well-formed-but-unsupported fixtures are diagnostic evidence.
- Plantigrade, quadruped, winged, extra-limb, and arbitrary-anatomy support
  remain future decisions and must not be inferred from this family.

## Alternatives Considered

### Option 1: Bounded stylized digitigrade furry biped

This provides recognizable furry character structure, useful proportion
variation, and a manageable semantic module set for the first native proof.
**Recommendation: Option 1 — a bounded stylized digitigrade furry biped.**

### Option 2: Bounded plantigrade furry biped

This would simplify foot-ground assumptions and could be a useful later family,
but it does not test the selected digitigrade body plan and would broaden the
first morphology decision if both were supported.

### Option 3: Narrow near-human template

This could simplify rigging and shared poses, but risks proving a disguised
template rather than a procedural family with meaningful variation.

### Option 4: Multi-family grammar now

This could demonstrate broader ambition early, but would multiply invalid
assemblies, fixture obligations, and surface/semantic failure modes before the
first family is understood.

### Stage 1 embodiment alternatives

#### Option 1: Geometry and labels only

This would minimize Stage 1 output, but would leave semantic joint-frame and
region intent/lineage untested; Stage 2 would need to infer or recreate the
links from geometry and labels.

#### Option 2: Intent-only, source-linked semantic intent and lineage

This intent-only Stage 1 boundary preserves source-linked semantic joint frames
and region intent/lineage for later embodiment without requiring a usable
skeleton, skin weights, collision proxies, or contact artifacts in Stage 1.
**Recommendation: Option 2 — source-linked semantic intent and lineage.**

#### Option 3: Generated embodiment artifacts in Stage 1

This would additionally generate a usable skeleton, skin weights, collision
proxies, and potentially contact artifacts in Stage 1. It could show more of
the end vision in one pass, but would move Stage 2 ownership into the
generation gate and conflate lineage with embodiment and interaction risks.
It is not selected.

### Graph-relation alternatives

#### Option 1: Binary typed edges only

This is compact, but cannot represent a joint with two endpoint frames, a
socket with host and mating roles, or a region spanning several owned parts
without hidden conventions.

#### Option 2: Reified semantic relations with role-labelled participation

This preserves one containment tree while allowing independently identified
joints, attachments, sockets, and regions to connect to several participants.
It retains solver and geometry neutrality. **Recommendation: Option 2.**

#### Option 3: Unrestricted hypergraph

This is maximally general, but would admit structures outside the first
morphology envelope and move validity and traversal complexity into the first
contract without evidence.

### Articulation-lineage alternatives

#### Option 1: Opaque generator-owned articulation

This keeps the source smaller, but forces Stage 2 to invent articulation from
geometry and breaks the promised semantic lineage handoff.

#### Option 2: Minimum functional articulation and landmark roles

This supplies stable Stage 2 inputs without fixing a bone hierarchy, bone
count, limits, rigging technique, or anatomical-fidelity claim.
**Recommendation: Option 2.**

#### Option 3: Remove the Stage 1-to-Stage 2 lineage promise

This would make opaque modules coherent, but weakens the staged proof and
postpones the central shared-derivation question rather than testing it.

### Fixture-rule alternatives

#### Option 1: Partial-success continuation

The project could continue after only a subset of fixed valid fixtures passed,
reporting other fixtures as limitations. This would allow early progress but
would weaken the claim about the declared family and invite evidence-population
drift.

#### Option 2: All declared valid-supported fixtures must pass

Every declared valid-supported fixture meets every mandatory structural check
and the subjective visual floor; failed or inconclusive fixtures keep the gate
open. Semantically invalid and well-formed-but-unsupported fixtures fail their
frozen expected primary diagnostics without counting as valid passes.
**Recommendation: Option 2 — all declared valid-supported fixtures must pass.**

#### Option 3: Reclassify difficult fixtures after evaluation

The project could remove or reclassify a fixture after a failure or
inconclusive result. This would hide the variation the fixed set is intended
to test and make cross-stage evidence non-comparable. It is not selected.

## Adversarial Review Response

The Revision 1, Revision 2, and Revision 3 current-revision reviews
([authority](reviews/DR-0008-rev-03-review-01.md),
[second review](reviews/DR-0008-rev-03-review-02.md)), together with the
Revision 4 current-revision reviews
([authority](reviews/DR-0008-rev-04-review-01.md),
[morphology](reviews/DR-0008-rev-04-review-02.md)), are preserved as stale
historical evidence. On 2026-08-11 Ben approved the resulting CK-KICK-012
articulation and fixture-outcome resolutions for Revision 5. Review status for
this revision is Pending; no current-revision review has yet been run. Review
evidence records neither acceptance nor a clean review. Only Ben may accept or
reject this proposal.

## Implementation and Proof Obligations

- Define the family vocabulary, named sockets, module attachment semantics,
  ownership tree, reified relation concepts and role-labelled relations,
  invalid/unsupported assemblies, and deterministic variation inputs in the
  later body specifications.
- Specify the ordered axial, arm, leg, and optional-tail articulation roles,
  including root-reference, torso ownership, chest landmark, and the single
  hock/ankle functional articulation per digitigrade leg; preserve their
  semantic frames through Stage 1 lineage without implying a fixed rig,
  solver, bone count, or anatomical-fidelity claim.
- Define declared units and coordinate basis, explicit local frames and
  resolved transforms, and structured diagnostics without locking a permanent
  coordinate convention or exact numeric ranges here.
- Select hypotheses and intended discriminating profiles before exact freeze,
  then freeze stable fixture IDs, concrete source inputs, discriminating
  parameters, seed/configuration, provenance, one of valid-supported,
  semantically invalid, or well-formed-but-unsupported, and the expected
  primary diagnostic class/code for every non-success fixture before EXP-0001
  execution or evidence; this proposal does not create fixture files.
- Evaluate all fixed qualitative profiles through the same grammar and
  generators, recording bespoke correction attempts as failures rather than
  silently adding exceptions.
- Prove semantic lineage, joint frames, and region intent through Stage 1
  evidence; generate usable skeletons, skin weights, and collision proxies and
  evaluate the shared pose/control scenario in Stage 2; reserve actual contact
  and deformation/runtime claims for Stage 3.
- Defer exact ratios and numeric ranges, surface primitives and geometry method,
  schema/syntax technology, permanent coordinate convention, rigging technique,
  runtime backend, budgets, new morphology families, and compatibility rules to
  evidence and their own decisions.

## Canonical Design Links

- [Vision and scope](../product/vision-and-scope.md)
- [Product requirements](../product/requirements.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [Normative specification boundary](../../spec/README.md)
- [Architecture index](../architecture/README.md)
- [Open research questions](../research/open-questions.md)
- [Round 5 and later plan](../project/kickoff-plan.md)

## Reversibility and Revisit Triggers

Revisit the family if fixed-fixture evidence shows that the required modules
cannot produce coherent connected surfaces, semantic regions, or useful
variation without bespoke corrections. Revisit the envelope if continuous
variation repeatedly exceeds the evidence-supported grammar or if a deferred
family becomes necessary for the product target. Revisit Stage 1 hooks if they
cannot preserve lineage or provide useful inputs to Stage 2; do not expand them
into animation or interaction claims without a separate decision.

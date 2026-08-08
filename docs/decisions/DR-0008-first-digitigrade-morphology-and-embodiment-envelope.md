# DR-0008: First digitigrade morphology and Stage 1 embodiment envelope

ID: DR-0008

Scope: Product, Specification and architecture

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-09

Date decided: —

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

### Stage 1 embodiment boundary

**Recommendation: Option 2 — minimal linked embodiment hooks.** Stage 1 emits
semantic joint frames, basic bind/skinning metadata where practical, analytic
collision regions, semantic contact regions, and lineage linking those outputs
to the resolved semantic graph. The shared pose/control scenario belongs to
Stage 2; contact and deformation claims belong to Stage 3.

Stage 1 makes no attractive skinning, locomotion, IK, stretching, bulging, or
soft-body claim. Exact representations, technologies, budgets, and backends
remain deferred.

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

This would minimize Stage 1 output, but would leave semantic embodiment
lineage and the later rigging path untested.

#### Option 2: Minimal linked embodiment hooks

This preserves the minimum semantic and analytic links needed for later
embodiment without claiming a finished rig or interaction system.
**Recommendation: Option 2 — minimal linked embodiment hooks.**

#### Option 3: Complete rig, animation, contact, and deformation

This could show more of the end vision in one pass, but would conflate the
generation gate with later embodiment and runtime risks.

## Adversarial Review Response

No current-revision adversarial review has been completed. Review status is
Pending; only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the family vocabulary, named sockets, module attachment semantics,
  invalid assemblies, and deterministic variation inputs in the later body
  specifications.
- Create representative valid and invalid fixture inputs only when the
  relevant specification and implementation gates activate; this proposal does
  not create fixtures.
- Evaluate all fixed qualitative profiles through the same grammar and
  generators, recording bespoke correction attempts as failures rather than
  silently adding exceptions.
- Prove semantic lineage, joint frames, regions, and basic embodiment metadata
  through Stage 1 evidence; evaluate shared pose and skinning in Stage 2.
- Defer exact ratios, geometry method, rigging technique, runtime backend,
  budgets, and compatibility rules to evidence and their own decisions.

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

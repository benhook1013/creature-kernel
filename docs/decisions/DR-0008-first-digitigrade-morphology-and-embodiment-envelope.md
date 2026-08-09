# DR-0008: First digitigrade morphology and Stage 1 embodiment envelope

ID: DR-0008

Scope: Product, Specification and architecture

Status: Proposed

Revision: 3

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-09

Date decided: —

Revision history: Revision 1 was reviewed in Round 5 and Revision 2 was
reviewed in its current round; both remain preserved as historical evidence.
Revision 3 records Ben's settled CK-KICK-012 Batch 1 morphology/grammar
selection on 2026-08-09. The discussion selection is not DR acceptance: this
revision remains Proposed until a current-revision Double review and Ben's
owner disposition are recorded. Reviews of Revisions 1 and 2 are stale for
this revision.

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
inputs, discriminating parameters, seed/configuration, and provenance. This
proposal does not invent the exact values or fixture files. The freeze is a
prerequisite to execution and evidence, not to deciding what to test.

### Body grammar and relation boundary

The first body grammar is a bounded typed ownership tree for the proposed
digitigrade biped family. It covers the required modules and predefined optional
ear/tail socket modules above. It also admits typed relation edges for joints,
sockets/attachments, capabilities, and regions. Ownership edges and relation
edges are distinct: a relation does not imply ownership, and ownership does
not replace the relation's type or semantics.

The graph representation must not permanently require every relationship to be
a tree. The first grammar nevertheless supports only this bounded family and
its declared typed edge kinds; arbitrary anatomy and arbitrary user-defined
graph kinds are unsupported. Invalid or unsupported assemblies receive
structured diagnostics. Units and coordinate basis must be declared, and
local frames and resolved transforms must be explicit.

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

**Recommendation: Option 2 — every declared valid fixed fixture must pass.**
Every declared valid fixture must meet every mandatory Stage 1 structural
check and the recorded subjective visual floor for the Stage 1 gate. A failed
or inconclusive valid fixture means the gate has not passed, while remaining
useful evidence that must stay visible. An invalid fixture must fail with its
expected diagnostic and is not counted as a valid pass fixture.

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
  discriminating parameters, seed/configuration, and provenance are frozen.
- Every declared valid fixture is part of the Stage 1 gate; failed and
  inconclusive fixtures remain visible and prevent continuation, while invalid
  fixtures are diagnostic evidence rather than valid pass fixtures.
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

### Fixture-rule alternatives

#### Option 1: Partial-success continuation

The project could continue after only a subset of fixed valid fixtures passed,
reporting other fixtures as limitations. This would allow early progress but
would weaken the claim about the declared family and invite evidence-population
drift.

#### Option 2: All declared valid fixtures must pass

Every declared valid fixture meets every mandatory structural check and the
subjective visual floor; failed or inconclusive fixtures keep the gate open,
and invalid fixtures fail expected diagnostics without counting as valid
passes. **Recommendation: Option 2 — all declared valid fixtures must pass.**

#### Option 3: Reclassify difficult fixtures after evaluation

The project could remove or reclassify a fixture after a failure or
inconclusive result. This would hide the variation the fixed set is intended
to test and make cross-stage evidence non-comparable. It is not selected.

## Adversarial Review Response

[Round 5 fresh independent review](reviews/DR-0008-rev-01-review-01.md) and
[current-revision review](reviews/DR-0008-rev-02-review-01.md) are preserved as
stale historical evidence for Revisions 1 and 2. The Revision 1 review gave a
Revise recommendation at High confidence; the Revision 2 review gave an Accept
recommendation at High confidence after addressing its blockers. Neither
reviews Revision 3. The current-revision Double review is complete in the
[authority, identity, and compatibility pass](reviews/DR-0008-rev-03-review-01.md)
and the [morphology, graph, and graphics-system pass](reviews/DR-0008-rev-03-review-02.md).
The authority pass recommends Accept at Medium confidence subject to freezing
fixture validity and expected invalid diagnostics. The morphology/graph pass
recommends Revise at High confidence, finding unresolved reusable-module
identity, typed relation/frame representation, minimum articulation topology,
and invalid/unsupported result-boundary issues. These findings remain pending
Ben's disposition. Review completion records evidence, not a clean review or
acceptance. Only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the family vocabulary, named sockets, module attachment semantics,
  ownership tree, typed relation edges, invalid/unsupported assemblies, and
  deterministic variation inputs in the later body specifications.
- Define declared units and coordinate basis, explicit local frames and
  resolved transforms, and structured diagnostics without locking a permanent
  coordinate convention or exact numeric ranges here.
- Select hypotheses and intended discriminating profiles before exact freeze,
  then freeze stable fixture IDs, concrete source inputs, discriminating
  parameters, seed/configuration, and provenance before EXP-0001 execution or
  evidence; this proposal does not create fixture files.
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

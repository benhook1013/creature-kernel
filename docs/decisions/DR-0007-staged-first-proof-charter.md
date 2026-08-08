# DR-0007: Staged first-proof charter and claim boundaries

ID: DR-0007

Scope: Product

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-09

Date decided: —

Revision history: Revision 1 was reviewed in Round 5 and remains preserved as
historical evidence. Revision 2 applies Ben's settled resolutions to the three
Round 5 blockers: it makes Stage 1 embodiment outputs and deferrals explicit,
defines the all-valid-fixtures continuation gate, and requires fixture inputs
and provenance to be frozen before EXP-0001 execution or evidence. The
Revision 1 review is stale for this revision; a current-revision review is
pending. This proposal remains unaccepted.

Supersedes: —

Superseded by: —

## Context

The product baseline describes a generated creature that eventually combines
surface, semantics, embodiment, contact, deformation, and bounded runtime
behaviour. Treating all of those outcomes as one first proof would make it
difficult to identify which part of the premise succeeded or failed. The
product requirements also leave visual quality, morphology, performance, and
runtime thresholds open until evidence exists.

Round 5 therefore needs a staged proof charter. This is a proposed claim
boundary, not evidence that any stage has been implemented or passed.

## Decision

**Recommendation: Option 2 — explicit Stage 1 generation, Stage 2 embodiment,
and Stage 3 real-time interaction proofs.** Each stage has its own continuation
gate and explicit non-claims; success at one stage does not imply success at a
later stage.

### Stage 1 — generation proof

Stage 1 may continue only when every declared valid fixed fixture passes every
mandatory Stage 1 structural check and the recorded subjective visual floor.
The fixtures must be substantially different and compile from structured
source without bespoke per-character mesh or rig patches. A failed or
inconclusive valid fixture means the Stage 1 gate has not passed, while
remaining useful evidence that must stay visible in the record. An invalid
fixture must fail with its expected diagnostic and is not counted as a valid
pass fixture. The evidence should reproducibly include:

- a resolved semantic graph;
- a coherent connected surface;
- semantic regions;
- basic appearance;
- source-linked semantic joint frames and semantic region intent/lineage;
- structured diagnostics; and
- comparable captures and documented reproduction.

The mandatory Stage 1 embodiment output is source-linked semantic joint frames
and semantic region intent/lineage tied to the resolved semantic graph. Stage 1
does not have to generate a usable bone hierarchy, bind weights or skinning,
analytic collision proxies, or actual contact artifacts. Stage 1 makes no
animation, contact, deformation, or real-time-performance claim.

### Stage 2 — embodiment proof

Stage 2 should generate a usable skeleton, bind weights/skinning, and analytic
collision proxies, then demonstrate one shared pose/control scenario across
the fixed fixtures using the Stage 1 semantic frames and region intent. Stage 2
does not yet claim actual contact behaviour, deformation quality, or runtime
performance; actual contact artifacts and contact claims belong to Stage 3.

### Stage 3 — real-time interaction proof

Stage 3 should demonstrate semantic contact between two generated characters,
selected localized deformation or physical response, declared hardware and
performance evidence, and a useful fallback. Its performance claim is valid
only for the declared scenario and evidence; it does not establish an
unbounded runtime budget.

Across all stages, claims must identify what was tested and preserve explicit
not-tested claims. No stage implies later-stage success.

## Consequences

- Evidence can isolate generation, embodiment, and interaction failures.
- Stage 1 remains small enough to test the native generation premise without
  requiring animation or runtime infrastructure.
- Later stages inherit the fixed fixture set and semantic lineage rather than
  silently changing the proof population.
- Stage 2 and Stage 3 require additional implementation, fixtures, and
  experiments; their claims cannot be substituted with screenshots from an
  earlier stage.
- The Stage 1 gate is an all-valid-fixtures rule: a valid fixture that fails or
  is inconclusive prevents continuation, while an invalid fixture is expected
  to fail diagnostics and is excluded from the valid-fixture count.
- Fixture hypotheses may be selected before exact fixtures are frozen, but
  EXP-0001 execution and evidence require stable fixture IDs, concrete source
  inputs, discriminating parameters, seed/configuration, and provenance.
- Hardware profiles, performance targets, and exact quality thresholds remain
  deferred to evidence and later decisions.

## Alternatives Considered

### Option 1: One end-to-end first proof

This would show the full intended story in one prototype and might reveal
integration problems early. It was not selected because a failure would not
identify whether generation, embodiment, or runtime interaction caused the
result, and it would force later infrastructure into the first surface proof.

### Option 2: Explicit three proof stages

This separates the generation, embodiment, and real-time interaction gates
while preserving a continuous path between them. **Recommendation: Option 2 —
explicit Stage 1 generation, Stage 2 embodiment, and Stage 3 real-time
interaction proofs.**

### Option 3: Geometry-only proof with no explicit later gates

This would minimize the first prototype and keep implementation focused on
surface output. It was not selected because it would leave the embodiment and
real-time product claims without named continuation gates or disciplined
non-claims.

### Stage 1 embodiment alternatives

#### Option 1: Geometry-only output

Stage 1 would emit geometry, appearance, regions, and diagnostics but no
embodiment semantics. This has the smallest generation surface, but loses
source-linked joint-frame and region intent needed to carry semantic lineage
into Stage 2; later embodiment would have to infer or recreate those links.

#### Option 2: Intent-only, source-linked semantic intent and lineage

This intent-only Stage 1 output emits semantic joint frames and semantic region
intent/lineage linked to the resolved semantic graph. It defers a usable bone
hierarchy, bind weights/skinning, analytic collision proxies, and actual contact artifacts to
later stages. This preserves the path to Stage 2 while keeping generated
embodiment and interaction artifacts out of the first generation gate.
**Recommendation: Option 2 — source-linked semantic joint frames and semantic
region intent/lineage.**

#### Option 3: Generated embodiment artifacts in Stage 1

Stage 1 would additionally generate a usable skeleton, bind weights/skinning,
and collision proxies (and could be read as requiring contact artifacts).
This would test more of the embodiment pipeline earlier, but would move Stage 2
ownership into the generation gate and blur the boundary between lineage,
embodiment, and actual contact claims. It is not selected.

### Stage 1 fixture-gate alternatives

#### Option 1: Partial-success continuation

Stage 1 could continue after a selected subset of fixtures passed, with failed
or inconclusive fixtures reported as limitations. This would permit progress
despite family failures, but would make the continuation claim weaker than the
declared fixed population and could silently reward fixture selection.

#### Option 2: All declared valid fixtures must pass

Every declared valid fixed fixture must meet every mandatory structural check
and the recorded subjective visual floor. A failed or inconclusive valid
fixture keeps the gate open and remains evidence; an invalid fixture must
produce its expected diagnostic and is not counted as a valid pass fixture.
This makes the claimed population and failure semantics explicit.
**Recommendation: Option 2 — all declared valid fixtures must pass.**

#### Option 3: Exclude difficult fixtures after evaluation

A fixture could be removed or reclassified when it fails or is inconclusive.
This might simplify the first claim, but would make the evidence population
unstable and conceal exactly the variation the fixed set is intended to test.
It is not selected.

## Adversarial Review Response

[Round 5 fresh independent review](reviews/DR-0007-rev-01-review-01.md) is
Complete with a Revise recommendation at High confidence for Revision 1. It
is historical and stale for Revision 2. It identified three blocking issues:
contradictory Stage 1/Stage 2 embodiment ownership, an undefined effect of
fixture failure or inconclusive results on the Stage 1 continuation claim, and
qualitative fixture identities that were not fixed enough to preserve the
evidence population. Revision 2 records Ben's settled resolutions; current
review and Ben's owner disposition remain pending. Only Ben may accept or
reject this proposal.

## Implementation and Proof Obligations

- Select experiment hypotheses without requiring exact fixture freeze, then
  freeze stable fixture IDs, concrete source inputs, discriminating parameters,
  seed/configuration, and provenance before EXP-0001 execution or evidence.
- Define reproducible Stage 1 fixtures, source inputs, diagnostics, and
  comparable captures before claiming the Stage 1 gate; evaluate every declared
  valid fixture against every mandatory structural check and the visual floor.
- Record structural checks, semantic-region checks, and reproduction commands;
  retain subjective visual judgments separately from measured evidence.
- Define and test the shared Stage 2 pose/control scenario and its failure
  criteria after the Stage 1 boundary is established.
- Define the Stage 3 contact, localized-response, fallback, hardware, and
  performance evidence before making a real-time claim.
- Keep failed, inconclusive, and not-tested results visible in the relevant
  research or experiment records.

## Canonical Design Links

- [Vision and scope](../product/vision-and-scope.md)
- [Product requirements](../product/requirements.md)
- [First morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [Open research questions](../research/open-questions.md)
- [Project roadmap](../project/roadmap.md)
- [Round 5 and later plan](../project/kickoff-plan.md)

## Reversibility and Revisit Triggers

Revisit the stage boundaries if evidence shows that a gate cannot isolate a
meaningful product risk, that a required output belongs in an earlier stage,
or that the fixed fixture set hides a material failure. Revisit Stage 3's
claim when the declared hardware, interaction scenario, or fallback no longer
represents the downstream product target. Any revision must preserve the
distinction between tested and untested behaviour.

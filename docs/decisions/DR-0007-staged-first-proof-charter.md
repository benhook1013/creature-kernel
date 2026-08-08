# DR-0007: Staged first-proof charter and claim boundaries

ID: DR-0007

Scope: Product

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-09

Date decided: —

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

Stage 1 may continue when several substantially different fixed fixtures
compile from structured source without bespoke per-character mesh or rig
patches. The evidence should reproducibly include:

- a resolved semantic graph;
- a coherent connected surface;
- semantic regions;
- basic appearance;
- minimal linked embodiment metadata;
- structured diagnostics; and
- comparable captures and documented reproduction.

Stage 1 makes no animation, contact, deformation, or real-time-performance
claim. Its minimal embodiment metadata is a path-preserving hook, not a claim
of attractive skinning or a usable shared pose.

### Stage 2 — embodiment proof

Stage 2 should generate skeletons and skinning and demonstrate one shared
pose/control scenario across the fixed fixtures, with semantic joint and
contact regions. It does not yet claim contact behaviour, deformation quality,
or runtime performance.

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

## Adversarial Review Response

[Round 5 fresh independent review](reviews/DR-0007-rev-01-review-01.md) is
Complete with a Revise recommendation at High confidence. It identifies three
blocking issues: contradictory Stage 1/Stage 2 embodiment ownership, an
undefined effect of fixture failure or inconclusive results on the Stage 1
continuation claim, and qualitative fixture identities that are not yet fixed
enough to preserve the evidence population. Ben's owner disposition remains
pending; only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define reproducible Stage 1 fixtures, source inputs, diagnostics, and
  comparable captures before claiming the Stage 1 gate.
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

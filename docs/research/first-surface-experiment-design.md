# First surface experiment design

Status: Proposed research/evidence design

Origin: Assistant-authored from Ben's settled Recommendations 1–5 and the
linked Proposed decision records and research protocol below

Maintenance: Manual; no regeneration command

Authority: Research/evidence design only; it does not own product,
specification, architecture, fixture, or experiment-record contracts

Experiment registration: Not registered; EXP-0001 is not created by this
document

Evidence status: No evidence exists yet

## Purpose and authority

This document is a neutral design for the first surface-generation evidence
collection. It was authored from Ben's settled Recommendations 1–5 and is
bounded by the Proposed [DR-0007 staged first-proof charter](../decisions/DR-0007-staged-first-proof-charter.md),
[DR-0008 morphology envelope](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
[DR-0009 hybrid hypothesis](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md),
and [DR-0010 extraction and propagation policy](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md).
The [visual-quality evaluation protocol](visual-quality-evaluation.md) owns
the human visual-assessment method. Those documents remain Proposed or
research guidance; this design does not accept them, create a production
contract, or silently create evidence.

This is a research/evidence design, not an experiment record, registration,
fixture package, implementation plan, or normative specification. No host
stack, dependency, exact fixture value, grid size, or numerical threshold is
selected here. No implementation, fixture, capture, or result exists yet.

## Neutral dimensionless manifest

The proposed manifest is independent of the eventual production schema. It
describes semantic source intent and evidence identity in normalized,
dimensionless terms. Normalize each valid profile's total stature to
**height H = 1** for comparison. The manifest may later map to a concrete
source format, but that format is not chosen here.

### Stable profile identities

The following IDs are stable proposed evidence identities. Their exact source
values and inputs remain deferred to experiment registration.

| Stable ID | Intended discriminating axis |
| --- | --- |
| `compact_broad_short_large_head` | Compact stature, broad body, short limbs, and relatively large head |
| `tall_narrow_long_legged` | Tall stature/aspect with lower-leg emphasis and moderate thickness |
| `slender_long_limbed` | Low girth/thickness with long arm and leg proportions, without extreme stature as its main axis |
| `stocky_broad_chested` | Stocky stature with broad chest and substantial torso proportions |

The tall and slender profiles are deliberately orthogonal. `tall_narrow_long_legged`
tests stature/aspect and lower-leg emphasis while retaining moderate thickness;
`slender_long_limbed` tests low girth/thickness and long arm/leg proportions
without making extreme stature the primary axis. They must not collapse into
two names for one height-versus-thickness change.

The profile set remains a bounded stylized digitigrade furry biped family. It
uses the required torso/pelvis, simplified muzzle, two arms with simplified
hands or paws, and two digitigrade legs with simplified feet or paws. Ears and
tail remain optional named-socket modules. All profiles use the same grammar
and construction operations; a profile-specific correction is a recorded
failure, not a new manifest operation.

### Proposed landmarks and ratio categories

The registration should predeclare the landmarks and ratio categories needed
to distinguish the profiles and inspect named junctions/features. Proposed
categories include:

- total stature and aspect, with lower-leg emphasis distinguished from general
  height;
- torso width, depth, and girth/thickness;
- head and muzzle scale relative to torso;
- upper- and lower-limb lengths, including arm-to-leg and segment ratios;
- shoulder, hip, knee, ankle, muzzle, paw, foot, ear, and tail landmarks where
  the corresponding module exists;
- shoulder, hip, limb, muzzle, paw, foot, and other declared branch-junction
  regions; and
- optional named-socket presence, absence, or style contrast for at least one
  enabled or disabled ear/tail feature.

These are proposed categories, not exact values or pass thresholds. Exact
landmark coordinates, ratios, optional-module choices, and named
junction/feature criteria are deferred to registration and must be frozen
before execution or evidence is interpreted.

## Freeze gate before execution or evidence

Before EXP-0001 executes or any output is treated as evidence, the experiment
registration must freeze:

- the four stable profile IDs and their exact normalized values and source
  inputs;
- discriminating parameters, enabled optional modules, and expected
  landmarks/ratio inputs;
- deterministic seeds, configuration, compiler/build identity, provenance,
  and the exact host process;
- valid/invalid classification for every proposed fixture; and
- the expected diagnostic for each invalid fixture.

Selecting these hypotheses and profile identities can precede the freeze. A
profile may not be removed, reclassified after evaluation, or patched to make
the evidence population pass. Failed and inconclusive valid fixtures remain
part of the evidence and prevent the Stage 1 all-valid-fixtures gate from
passing; an invalid fixture is diagnostic evidence and is not counted as a
valid pass fixture.

## Five-branch comparison

The comparison is bounded nested ablation, not a full factorial sweep. Every
branch receives the same frozen semantic source intent, vocabulary, profile
identity, input mapping, common output interface, extraction policy,
diagnostics, capture settings, seed/configuration policy, parameter/tuning
budget, and implementation-effort reporting. Baselines receive the same
semantic feature vocabulary and source intent but realize them through their
own allowed construction rule.

| Branch | Construction rule for the comparison |
| --- | --- |
| Skeleton/swept-profile baseline | Semantic skeleton, explicit centerlines, swept profiles, and declared attachments |
| General implicit-field baseline | One general volumetric composition rule over the shared semantic inputs |
| Skeleton plus selected blending | Skeleton/swept-profile construction plus the selected implicit-blending operations |
| Skeleton plus reusable specialized generators | Skeleton/swept-profile construction plus reusable generators for the declared feature vocabulary |
| Full hybrid | Skeleton/swept-profile construction, selected implicit blending, and the same reusable specialized generators |

The registration must freeze the branch-operation matrix, allowed operations,
selected blend sites, generator set, parameter/tuning budgets,
implementation-effort budget, and common output fields. An internal
scalar-field storage choice does not change branch identity. Exact operations
and values are not selected by this design.

Before tuning, the registration freezes shared infrastructure and oracles,
branch/search contracts, deterministic initialization, adjustment unit,
stopping rule, maximum count, and the evaluation/search budget. Branches use
separate configurations or workspaces. The primary comparison uses identical
deterministic search and evaluation budgets; if human adjustment is permitted,
its order is preregistered and rotating or counterbalanced. Transfer of
branch-specific parameters, corrections, or defect fixes is prohibited during
primary evidence collection. Adjustments are global branch parameters only;
no per-fixture tuning or correction is permitted in the primary comparison.
Record unavoidable knowledge reuse, shared versus branch-specific effort, and
any shared fix that requires affected evidence to be rerun. Before primary
comparison, every required branch must pass
branch-neutral analytical readiness fixtures, cover every required operation
in its matrix, and disclose unresolved defects. An unready required branch
makes each affected comparison `Inconclusive`.

The paired per-fixture/site contrasts are:

| Contribution | Without the other contribution | With the other contribution |
| --- | --- | --- |
| Blending | `S+B` versus `S` | `Full` versus `S+G` |
| Generators | `S+G` versus `S` | `Full` versus `S+B` |

Here `S` is skeleton/swept-profile, `B` is selected blending, and `G` is the
reusable specialized-generator layer. For each criterion, preregister the
direction and per-criterion interaction contrasts. Independent credit for
blending or generators requires both relevant paired contrasts to support the
same direction. Support only with the other contribution present is
synergy-dependent; support only without it means the effect is suppressed or
antagonized by the other contribution. Opposing directions are antagonistic or
context-dependent under the registered rule. Otherwise use
ambiguous/disputed or combined-hybrid-only as applicable. Report interaction
as a diagnostic for attribution; it is not a scalar interaction score or a
full-factorial claim.

## Common sampling and convergence structure

All five branches use the common normalized field contract described in
[DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md):
coordinate system and units, sign convention, isovalue meaning, frozen
bounds/padding, interpolation, out-of-domain behaviour, orientation/gradient
convention, and deterministic postprocessing order. Per profile, the primary
comparison uses the same frozen bounds and three uniform grids: coarse,
nominal, and fine.

At nominal resolution, use a small deterministic set of sub-voxel phase
offsets. The exact offsets, grid sizes, and numerical thresholds are frozen at
registration. The design requires clipping checks, independent
continuous-field/isovalue clearance at all six domain faces, feature-relative
sampling checks, and convergence/stability measurements for components, named
junctions, gaps, thin features, and predeclared topology invariants. For each
valid initial closed creature exterior, the default expected invariant is one
watertight connected genus-zero component unless the fixture prospectively
declares another valid expectation. Shared or unavailable/indeterminate
evidence, including common-pipeline or oracle defects, unavailable mandatory
diagnostics, clipping that prevents a valid measurement, and sampling
non-convergence that cannot be attributed to a branch, is `Inconclusive` under
the shared precedence in DR-0009. Once apparatus and branch readiness pass, a
valid registered branch violation of a frozen clearance, convergence,
phase/topology, or feasibility criterion is a technology failure and
contributes to `Reject`; an indeterminate attribution remains `Inconclusive`.
No declared branch is silently dropped. Deviations from the common bounds,
grids, phases, or field contract are separate exploratory runs. Lewiner's
guarantee remains scoped to reconstruction from the sampled grid, not the
continuous field.

Run a repeated deterministic execution within the declared process, thread,
numeric, and platform scope. Record canonicalization, hashes, geometric
tolerances, and stage-level nondeterminism isolation. This design does not
claim bitwise cross-platform output.

## Evidence ledgers

Keep distinct ledgers with shared profile, branch, build, seed, and provenance
identities. The visual protocol describes the capture views and human review;
this design only establishes how those records join the other evidence.

### Structural ledger

Record mandatory fixture gates and machine/checklist results separately for
connectedness, boundaries/non-manifold cases, Euler characteristic or genus
where applicable, self-intersections, winding/orientation, signed volume,
normals versus field gradients, six-face continuous-field/isovalue clearance,
phase and component/junction/gap/thin-feature stability, expected topology
invariants, diagnostic completeness, and expected attachments. Mark
inapplicable, unavailable, failed, and inconclusive results explicitly;
unavailable or invalid required evidence is not an implicit pass.

### Semantic ledger

Record semantic lineage as a canonical non-negative distribution over durable
`(semantic_id, chart_id)` keys. Unit leaves provide raw mass; child inputs are
normalized before declared non-negative mappings or coefficients are applied;
duplicate keys coalesce before normalization. Require a finite positive total
before normalizing the complete distribution to one. Top-k values retain their
full-distribution normalized weights and are not renormalized; record residual
mass after selecting top-k. Hard or cutoff ties use deterministic ordering and
record ambiguity. Keep categorical ownership and chart validity as parallel
fields rather than interpolated scalar values; incompatible charts are not
silently blended. Record each contributor's local coordinate and validity,
missing-field masks, and chart-seam multiple-contributor or invalid/ambiguous
states. Independent closed-form fixtures or oracles cover nesting, duplicate
keys, operand scaling and order, coefficient order, ties, residual mass, and
incompatible charts without reusing the propagation implementation.

### Subjective visual ledger

Use the [visual-quality evaluation protocol](visual-quality-evaluation.md) for
consistent front, side, three-quarter, turntable, and targeted close-up review
where practical. Record reviewer, view/capture provenance, criterion,
rationale, disagreement, and uncertainty separately from structural and
semantic checks. The protocol's visual floor is a Stage 1 claim boundary, not a
numeric aesthetic score.

### Provenance and effort ledger

Record host process and stack, dependency versions and licenses, commands,
hardware when relevant, configuration, seed, artifacts/hashes, parameter and
tuning effort, implementation effort, complexity, and all correction attempts.
Large generated artifacts remain subject to the repository artifact-storage
policy. A correction that is specific to one profile is retained as a failure
or limitation, not hidden in a branch.

## Interpretation and retained failures

Apply the evidence-first comparative rule in [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
only after exact aggregation and threshold rules, named junction/feature
criteria, readiness fixtures, paired contrasts, and the assessment rule have
been frozen. Classify shared, unavailable, or indeterminate evidence as
`Inconclusive`; classify a valid mandatory branch violation as a technology
failure contributing to `Reject`; retain every declared branch and contrast.
With valid evidence, report all eligible passing baselines and their
non-dominated frontier rather than a scalar or one strongest baseline. The
mandatory visual floor is a separate gate; comparative visual evidence is a
declared frontier dimension. A frozen non-inferiority regression or a simpler
baseline matching the claimed result is `Reject`. Hybrid mandatory failure or
missing named improvement is `Reject`. If no baseline is eligible, the
comparative outcome is `Inconclusive`; if the hybrid passes, record only a
separate non-comparative `Feasibility demonstrated` annotation. Unresolved
nonmandatory trade-offs or comparative visual disagreement are
`Inconclusive`. `Support` requires valid evidence, an eligible frontier, all
gates, a named improvement, non-inferiority, no simpler match or dominance,
and no unresolved trade-off.

Retain raw failures, failed and inconclusive fixtures, invalid-fixture
diagnostics, disagreements, missing contributors, clipping, sampling
instability, and unsuccessful correction attempts. A result can support only
the bounded Stage 1 claim under this manifest and protocol; it cannot select a
production topology, dependency, runtime field, animation representation, or
backend.

## Deferred registration decisions

The next human decisions and experiment-registration work must choose the exact
host stack, dependency versions and licenses, concrete fixture values and
source inputs, enabled optional-module values, grid sizes, numerical
thresholds, canonicalization/hash details, and artifact-retention location.
This document intentionally does not choose any of them. Until those values
are frozen, there is no EXP-0001 evidence to interpret.

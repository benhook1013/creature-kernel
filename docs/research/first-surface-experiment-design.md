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
implementation-effort budget, and common output fields. An internal scalar-field storage
choice does not change branch identity. Exact operations and values are not
selected by this design.

## Common sampling and convergence structure

All five branches use the common normalized field contract described in
[DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md):
coordinate system and units, sign convention, isovalue meaning, frozen
bounds/padding, interpolation, out-of-domain behaviour, orientation/gradient
convention, and deterministic postprocessing order. Per profile, the primary
comparison uses the same frozen bounds and three uniform grids: coarse,
nominal, and fine.

The registration must define the exact grid sizes and numerical thresholds.
The design requires clipping checks, feature-relative sampling checks, and
convergence/stability measurements for components, named junctions, gaps, and
thin features. Deviations from the common bounds, grids, or field contract are
separate exploratory runs. Lewiner's guarantee remains scoped to reconstruction
from the sampled grid, not the continuous field.

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
normals versus field gradients, component/junction/gap/thin-feature stability,
diagnostic completeness, and expected attachments. Mark inapplicable,
unavailable, failed, and inconclusive results explicitly.

### Semantic ledger

Record resolved-graph lineage, raw and top-k contributors with normalized
weights, categorical ownership, each contributor's semantic ID and
local-chart identity/local coordinate/validity, missing-field masks, and
ambiguity diagnostics. Keep categorical IDs separate from scalar interpolation
and do not blend incompatible charts. Run independent analytical fixtures or
oracles for coverage, normalization, missing contributors, chart
reconstruction/validity, landmarks, and expected boundary ambiguity.

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

Apply the comparative rule in [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
only after exact aggregation and threshold rules, named junction/feature
criteria, and the assessment rule have been frozen. The hybrid is supported
only if every mandatory fixture gate passes, it is no worse than the strongest
passing baseline on mandatory structural/semantic checks, and it improves the
predeclared named junction/feature criteria. Reject it if a mandatory gate
fails or a simpler credible baseline achieves the same claimed result without
the named improvement. Mixed structural/subjective trade-offs, reviewer
disagreement, or inadequate evidence are inconclusive. Complexity, tuning, and
effort qualify the interpretation in every outcome.

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

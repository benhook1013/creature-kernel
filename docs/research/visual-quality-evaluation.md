# Visual-quality evaluation protocol

Status: Proposed research protocol

This protocol defines how to record visual-quality evidence for the bounded
first morphology proof. It is a research and evaluation method, not a product
contract and not evidence that the open questions are answered. Product stage
claims remain in [vision and scope](../product/vision-and-scope.md) and
[requirements](../product/requirements.md).

The neutral profile manifest and branch/evidence ledgers are described in the
[first surface experiment design](first-surface-experiment-design.md). This
protocol owns the human visual-assessment method and does not register EXP-0001
or provide evidence.

## Questions and scope

The protocol informs the following entries in the [open research question
registry](open-questions.md): RQ-001 through RQ-004; RQ-010 through RQ-014;
RQ-021 through RQ-024; RQ-030 through RQ-032; RQ-040 through RQ-045; and
RQ-072 and RQ-074. The open-question states remain unchanged. Stage 1 is
evaluated as a generation and lineage proof. Shared pose/animation belongs to
Stage 2, and contact/deformation and real-time interaction belong to Stage 3;
an assessment must not transfer a later-stage claim to an earlier stage.

## Planned model-assisted visual-appraisal checkpoint

Before the project relies on an AI or multimodal model for visual appraisal,
hold a recorded discussion with Ben and complete a current-at-the-time
research pass for RQ-004. This is a proposed research checkpoint, not present
evidence, a provider selection, or permission to weaken the human gate. The
discussion must first clarify what assistance is wanted: generic recognition or
categorisation is not the same capability as fine-grained spatial or geometry
defect detection, cross-view comparison and localisation, motion/deformation
review, consistency across repeated views, or iterative critique that is
specific and actionable enough to guide a revision. Treat claims about any
provider as time-sensitive; explicitly consider OpenAI, Google, xAI/Grok, and
other credible accessible providers available at the time, without assuming a
ranking or that a strong categorisation result implies reliable defect review.

If assistance remains worth testing, preregister a small blinded comparative
benchmark on Creature Kernel captures. Use repeated front/side/three-quarter
views and turntable or motion captures where relevant, with known injected or
labelled defects and clean controls. Mask provider/model and case identity
where practical, and compare models under documented prompts, image/video
limits, and tool access. Measure defect detection, spatial localisation,
explanation quality, actionable revision guidance, false positives, and
cross-view and repeat-run consistency. Also record cost, latency, privacy and
data retention terms, API/tooling reliability, version/configuration
provenance, and unhandled or refused cases. Separate measured results from
subjective reviewer judgment and from provider documentation or marketing
claims.

The checkpoint must end with an explicit role and safety decision: keep review
human-only; use a model only for triage or a second opinion; or permit a
strictly bounded reviewer role. Define confidence/uncertainty handling,
escalation to a human, and defect classes the model must not adjudicate. Until
a later evidence-backed decision changes this boundary, the human subjective
visual floor remains authoritative and model output cannot turn a failure into
a pass or replace human appraisal.

## Evaluation inputs and views

Evaluate the fixed body-profile set through the same generation operations,
configuration, and seed policy, using these stable proposed IDs:
`compact_broad_short_large_head`, `tall_narrow_long_legged`,
`slender_long_limbed`, and `stocky_broad_chested`. The tall profile tests
stature/aspect and lower-leg emphasis with moderate thickness; the slender
profile tests low girth/thickness and long arm/leg proportions without extreme
stature as its main axis. At least one profile must contrast optional-module
presence, absence, or style.
The project may select hypotheses and intended discriminating profiles before
exact fixtures are frozen. Before EXP-0001 execution or evidence, freeze stable
fixture IDs, concrete source inputs, discriminating parameters,
seed/configuration, and provenance. Do not add a fixture-specific corrective,
generator branch, or hand-authored patch to make one profile pass. Record the
fixture/profile identifier, source and generator provenance,
build/configuration identity, seed, view/capture settings, criterion, result,
and failure notes.

For the surface comparison, retain paired per-fixture/site visual contrasts for
each predeclared added operation under the same capture settings. Record the
literal conditional-effect pattern separately from the individual operation
contrasts; it must not assert independence, synergy, antagonism, or another
interaction claim, and it must not be folded into a new aesthetic score or an
unrecorded branch preference.

For each profile, retain consistent front, side, and three-quarter views, plus
a turntable when practical. Capture targeted closeups of shoulders, hips,
muzzle, paws, and other branch junctions that the profile includes. A second
perspective should be inspected before claiming that the subjective floor is
met where practical. Retain failures and inconclusive cases with the same
provenance; do not replace them with a successful rerun.

## Objective structural checks

Record machine- or checklist-based results separately from human visual
assessment. The checks should cover, as applicable to the claimed stage:

- output resolution and diagnostic completeness, including the configuration
  and interpretation needed to reproduce the check;
- repeatability from the same source, build/configuration identity, and seed;
- preservation and inspectability of semantic IDs and regions;
- a connected visible surface for the supported body plan;
- field-clearance status at all six domain faces, sub-voxel sampling-phase
  checks, and prospective component/topology invariants where the experiment
  has declared them;
- watertightness and non-manifold reporting, including explicit diagnostics for
  failures rather than an assumed pass;
- expected attachments and junctions, including required modules and enabled
  named-socket features;
- material regions and basic appearance inputs;
- source-linked semantic joint frames and semantic region intent/lineage. These
  checks do not establish a usable bone hierarchy, bind weights/skinning,
  analytic collision proxies, shared pose, actual contact, or deformation.

For semantic comparison records, preserve cross-operator contributor
distribution, top-k residual/discarded mass, deterministic ties, and chart
validity as distinct diagnostics; they are not visual-quality scores.

An objective check may be pass, fail, or inconclusive. The protocol does not
invent numeric aesthetic scores or convert a visual impression into a hidden
threshold.

## Stage 1 gate interpretation

Every declared valid fixed fixture must pass every mandatory Stage 1 structural
check and the recorded subjective visual floor for the Stage 1 gate. A failed
or inconclusive valid fixture means the gate has not passed, while remaining
useful evidence that must stay visible and linked to its provenance. An invalid
fixture must fail with its expected diagnostic and is not counted as a valid
pass fixture. This all-valid-fixtures rule does not prevent selecting
experiment hypotheses before exact fixtures are frozen, but exact freezing is
required before EXP-0001 execution or evidence.

## Subjective visual floor

Human reviewers assess whether the result reads as a coherent, intentional
stylized digitigrade anthropomorphic/animal-like biped in front, side, and three-quarter views. The assessment
considers:

- a legible silhouette and legible body modules;
- intentional shoulders, hips, muzzle, paws, and included branch junctions;
- coherent proportions, style, and colour across the body and its regions.

Low-detail and cartoon results are acceptable. A result fails the visual floor
when it presents conspicuous seams or detached parts, melted or collapsed
joints, or undifferentiated primitive blobs rather than an intentional
character. Human judgment is explicitly subjective: record the reviewer,
views, concise rationale, and disagreements or uncertainty, without inventing
a numeric aesthetic score or implying inter-reviewer precision that has not
been measured.

The subjective visual floor is a mandatory Stage 1 gate, not a comparative
visual score. It answers whether each valid fixture is an intentional,
coherent stylized character; it does not rank branches or establish a named
improvement. Comparative visual evidence is a separately declared frontier
dimension. For each paired fixture/site contrast, record the direction,
criterion, view provenance, rationale, reviewer disagreement, and uncertainty
without inventing a scalar or collapsing the record into an aesthetic score.
The comparative visual result must remain distinct from the floor result.

## Reviewer panel and adjudication

Each applicable comparative visual cell uses at least three independent
reviewers. Independence means independence from branch implementation and
tuning, not merely separate votes. Record each reviewer's eligibility and
independence assessment, and mask branch identity and randomize A/B order where
practical while keeping the capture settings and criterion fixed. Record every
individual vote and rationale before aggregation. A panel with fewer than three
eligible independent reviewers is `U` and exploratory, not a conclusive result.

Use the same generic `B`/`N`/`H`/`U` vocabulary as other criteria, with
modality-specific `N` meaning visual equivalence. Aggregate `B` when at least
two of three (or at least two-thirds of a larger registered panel) vote `B` and
no reviewer votes `H`; aggregate `H` when at least two of three (or at least
two-thirds) vote `H` and no reviewer votes `B`. Aggregate `N` when at least
two of three (or at least two-thirds) vote visual equivalence and no reviewer
votes `B` or `H`. Otherwise aggregate `U`. A not-applicable cell is
`NA`, separate from `U`, and excluded from applicable-cell coverage. The
comparative rubric and the visual-floor rubric are separate: floor votes record
whether each fixture clears the intentional-character gate and do not become a
comparative component vote.

For visual criteria in the component-attribution record, use the panel's
qualitative `B`/`N`/`H`/`U` adjudication: `B` is beneficial in the registered
direction, `H` is harmful or reversed, `N` is visual equivalence, and `U` is
unresolved, invalid, or unavailable evidence. This adjudication has no fake
statistical precision, practical-margin interval, or point-estimate claim.
The full per-fixture/site/criterion matrix is the component-attribution
result; optional coverage counts are descriptive only, with no collapsed
component outcome. Bundle outcome remains separate and grants no component
credit. An unresolved visual result remains `U`, not visual equivalence; `NA`
cells are excluded from applicable-cell coverage. A component `U` cell does not
by itself block bundle `Support`.

When comparative visual evidence is an applicable registered dimension for a
match or dominance determination, unresolved or disputed visual evidence that
could change that determination blocks a conclusive result and is
`Inconclusive`. This protocol contributes no scalar visual score; it records
views, rationale, disagreement, and uncertainty only.

Under the shared outcome precedence in DR-0009, a mandatory visual-floor
failure is a gate failure and contributes to `Reject` when the evidence is
valid; unavailable or indeterminate visual evidence is `Inconclusive` unless a
branch-specific terminal feasibility attribution already applies. Generic
evidence-unavailability wording cannot override that branch/failure
attribution. A valid frozen non-inferiority visual regression, or a simpler
eligible baseline
matching the overall claimed result under the registered multidimensional
rule, is `Reject`. Unresolved nonmandatory comparative visual disagreement is
`Inconclusive`, not an inferred pass or scalar compromise. Comparative bundle
`Support`/`Reject`/`Inconclusive` remains separate from component attribution.
The full per-fixture/site/criterion matrix is the sole component-attribution
result; missing applicable visual cells remain `U`, while not-applicable cells
are
`NA` and excluded from applicable-cell coverage. Optional coverage counts are
descriptive only. Bundle `Support` implies no independent component credit,
but a component `U` cell does not by itself block it. Comparative
`Support` requires an eligible frontier, all gates, a named improvement,
non-inferiority, no simpler match or dominance, and no unresolved trade-off.
If no baseline is eligible, the comparative outcome remains `Inconclusive`,
with a separate non-comparative `Feasibility demonstrated` annotation allowed
only when the hybrid otherwise passes.

## Stage 1 exclusions

The following are deferred or semantic-only in Stage 1 and must not be treated
as required visual-quality failures: face or mouth interiors; detailed eyes or
eyelids; teeth or tongue; fingers, toes, or claws; dense fur or hair;
clothing/cloth; contact or deformation; cinematic rendering; and
arbitrary anatomy. A simplified muzzle and hands/paws or feet/paws remain part
of the bounded family, while their detailed subfeatures are deferred.

## Evidence record and interpretation

An evaluation record should link the profile, views, turntable and closeups to
each objective criterion and subjective note. Summaries must distinguish
expectations, observed measurements/checks, human judgments, failures, and
inconclusive results. A Stage 1 continuation recommendation may use the full
record, but it cannot claim Stage 2 or Stage 3 success; any later claim requires
its own stage-specific evidence.

Record experiment lifecycle, evidence closure, and technology outcome as the
three fields defined in the [experiment workflow](../../experiments/README.md).
Only `finished` with `complete` evidence closure may calculate a technology
outcome or feasibility annotation. An experiment ending without closure is
`finished` or `abandoned` with `incomplete`/`none`, and `abandoned` is always
`incomplete`/`none`.

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
registry](open-questions.md): RQ-001, RQ-002, and RQ-003; RQ-010 through RQ-014;
RQ-021 through RQ-024; RQ-030 through RQ-032; RQ-040 through RQ-045; and
RQ-072 and RQ-074. The open-question states remain unchanged. Stage 1 is
evaluated as a generation and lineage proof. Shared pose/animation belongs to
Stage 2, and contact/deformation and real-time interaction belong to Stage 3;
an assessment must not transfer a later-stage claim to an earlier stage.

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
each predeclared added operation under the same capture settings. Report any
interaction separately from the individual operation contrasts; do not fold it
into a new aesthetic score or an unrecorded branch preference.

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
stylized furry biped in front, side, and three-quarter views. The assessment
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

When comparative visual evidence is an applicable registered dimension for a
match or dominance determination, unresolved or disputed visual evidence that
could change that determination blocks a conclusive result and is
`Inconclusive`. This protocol contributes no scalar visual score; it records
views, rationale, disagreement, and uncertainty only.

Under the shared outcome precedence in DR-0009, a mandatory visual-floor
failure is a gate failure and contributes to `Reject` when the evidence is
valid; unavailable or indeterminate visual evidence is `Inconclusive` unless a
branch-specific terminal feasibility attribution already applies. Generic
evidence-unavailability wording cannot override that terminal attribution. A
valid frozen non-inferiority visual regression, or a simpler eligible baseline
matching the overall claimed result under the registered multidimensional
rule, is `Reject`. Unresolved nonmandatory comparative visual disagreement is
`Inconclusive`, not an inferred pass or scalar compromise. Comparative bundle
`Support`/`Reject`/`Inconclusive` remains separate from per-component
attribution: missing visual ablation evidence makes the affected component
attribution `U`/`Inconclusive` but does not by itself prevent bundle `Support`,
and bundle `Support` implies no independent component credit. The
`combined-hybrid-only` tag remains a separate bundle annotation. Comparative
`Support` requires an eligible frontier, all gates, a named improvement,
non-inferiority, no simpler match or dominance, and no unresolved trade-off.
If no baseline is eligible, the comparative outcome remains `Inconclusive`,
with a separate non-comparative `Feasibility demonstrated` annotation allowed
only when the hybrid otherwise passes.

## Stage 1 exclusions

The following are deferred or semantic-only in Stage 1 and must not be treated
as required visual-quality failures: face or mouth interiors; detailed eyes or
eyelids; teeth or tongue; fingers, toes, or claws; dense fur or hair;
clothing/cloth; adult contact or deformation; cinematic rendering; and
arbitrary anatomy. A simplified muzzle and hands/paws or feet/paws remain part
of the bounded family, while their detailed subfeatures are deferred.

## Evidence record and interpretation

An evaluation record should link the profile, views, turntable and closeups to
each objective criterion and subjective note. Summaries must distinguish
expectations, observed measurements/checks, human judgments, failures, and
inconclusive results. A Stage 1 continuation recommendation may use the full
record, but it cannot claim Stage 2 or Stage 3 success; any later claim requires
its own stage-specific evidence.

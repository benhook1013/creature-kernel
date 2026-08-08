# Visual-quality evaluation protocol

Status: Proposed research protocol

This protocol defines how to record visual-quality evidence for the bounded
first morphology proof. It is a research and evaluation method, not a product
contract and not evidence that the open questions are answered. Product stage
claims remain in [vision and scope](../product/vision-and-scope.md) and
[requirements](../product/requirements.md).

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
configuration, and seed policy: compact/broad/short-limbed/large-head;
tall/narrow/long-legged; slender/long-limbed; and stocky/broad-chested. At
least one profile must contrast optional-module presence, absence, or style.
The project may select hypotheses and intended discriminating profiles before
exact fixtures are frozen. Before EXP-0001 execution or evidence, freeze stable
fixture IDs, concrete source inputs, discriminating parameters,
seed/configuration, and provenance. Do not add a fixture-specific corrective,
generator branch, or hand-authored patch to make one profile pass. Record the
fixture/profile identifier, source and generator provenance,
build/configuration identity, seed, view/capture settings, criterion, result,
and failure notes.

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
- watertightness and non-manifold reporting, including explicit diagnostics for
  failures rather than an assumed pass;
- expected attachments and junctions, including required modules and enabled
  named-socket features;
- material regions and basic appearance inputs;
- source-linked semantic joint frames and semantic region intent/lineage. These
  checks do not establish a usable bone hierarchy, bind weights/skinning,
  analytic collision proxies, shared pose, actual contact, or deformation.

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

# DR-0009: Hybrid surface-generation experiment hypothesis

ID: DR-0009

Scope: Architecture

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

Round 6 needs a falsifiable surface-generation hypothesis for the bounded
digitigrade fixture family in [DR-0008](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md).
The project needs to test semantic control, connected organic junctions, useful
variation, and specialized features without silently turning each fixture into
a handcrafted asset. This is a Stage 1 experiment choice, not a permanent
surface architecture, production dependency, or claim that any branch already
works.

The primary research supports several credible directions. *Implicit
Generalized Cylinders Using Profile Curves* describes implicit generalized
cylinders constructed from profile curves, establishing a relevant
skeleton/profile-radius family of representations ([source](https://doi.org/10.1016/j.cad.2004.09.012)).
*Implicit Surface Modeling Based on General Skeletons* establishes a general
skeleton-based implicit-surface approach ([source](https://www.jos.org.cn/josen/article/abstract/20000913)).
Those sources establish representation techniques, not their suitability for
Creature Kernel's fixtures or runtime.

*Subdivision Surfaces in Character Animation* studies subdivision surfaces in
the context of character animation ([source](https://doi.org/10.1145/280814.280826)).
The source establishes why smooth surface representation and deformation
topology are relevant to character work; applying that observation to this
project's Stage 1 topology question is an inference. The [OpenSubdiv
overview](https://graphics.pixar.com/opensubdiv/overview.html) documents an
open-source subdivision-surface library and its production-oriented scope. It
does not select OpenSubdiv as a project dependency or prove that a
patch-first branch meets the fixed fixtures.

The [OpenVDB Python
documentation](https://www.openvdb.org/documentation/doxygen/python.html),
[ParticlesToLevelSet attribute-transfer
documentation](https://www.openvdb.org/documentation/doxygen/classopenvdb_1_1v13__0_1_1tools_1_1ParticlesToLevelSet.html),
and [VolumeToMesh documentation](https://www.openvdb.org/documentation/doxygen/structopenvdb_1_1v12__1_1_1tools_1_1VolumeToMesh.html)
establish that a field-oriented workflow can expose scripting, attribute
transfer, and volume-to-mesh operations. That documents capability in one
library, not a production choice or evidence that its semantics, licensing,
performance, or outputs fit this project.

The working hypothesis is that semantic skeleton/radius structures can carry
the control needed for body parts and variation, implicit blending can improve
organic junctions where a direct structure is insufficient, and reusable
specialized generators can handle features whose geometry is not well served
by one universal operation. EXP-0001 must compare this hypothesis against
credible baselines so that it can be falsified. EXP-0001 is not registered or
created by this record.

## Decision

**Recommendation: Option 4 — a hybrid of semantic
skeleton/radius structures, implicit blending where useful, and reusable
specialized generators for muzzle, paws, ears, feet, and tail.** The branch is
the leading Stage 1 hypothesis only. It must use the same semantic source,
fixed fixture identities, diagnostics, and capture protocol across comparison
branches.

The semantic skeleton/radius structures provide explicit part and attachment
control. Implicit blending may be used at selected junctions or regions where
it tests the organic-junction hypothesis. Muzzle, paw, ear, foot, and tail
generators are reusable grammar capabilities: each is a parameterized module
defined by semantic type, sockets, fields, and diagnostics, and is available to
all fixtures that require it. A generator is not a hidden per-fixture mesh,
topology, or rig correction. Fixture-specific correction remains a recorded
failure, not a new exception in the branch.

The branch does not decide a permanent field representation, mesh topology,
animation-ready edge flow, runtime field representation, surface backend,
language, or library. Those remain open pending evidence and any later
decision record. It also does not claim that implicit generation must remain
live at runtime or that conventional derived meshes are forbidden.

The comparison branches are classified by construction rule rather than by
storage format: an implicit baseline uses one shared volumetric composition
rule without explicit swept-profile construction or feature-specific surface
generators; the skeleton/generalized-cylinder baseline uses explicit
centerlines and swept profiles without the hybrid's separately selected blend
and specialized-feature layers. Either branch may evaluate an implicit scalar
field internally. EXP-0001 must pin these operational boundaries so overlapping
mathematical representations do not collapse the comparison into three labels
for the same generator.

## Consequences

- Stage 1 can test semantic control and organic junction quality together while
  retaining baselines that can disprove the combined hypothesis.
- Specialized generators add grammar vocabulary and reusable capabilities;
  they do not license bespoke fixture patches or silently expand the supported
  morphology envelope.
- The hybrid branch has more moving parts and more diagnostic surface than a
  single representation. The experiment must therefore report which component
  produced each result and where a branch failed.
- A successful surface experiment would support only the stated Stage 1 claim
  under its fixtures and protocol. It would not settle production topology,
  animation deformation, runtime representation, backend, or performance.
- A failed or inconclusive hybrid result must remain visible and may support a
  different hypothesis, a narrower proof, or a revised decision; it must not be
  converted into an unrecorded implementation exception.

## Alternatives Considered

### Option 1: SDF/implicit-only

An implicit-only branch is credible because implicit fields naturally provide a
continuous surface description and can blend nearby contributions. The
general-skeleton and generalized-cylinder sources establish relevant implicit
families, while the field-oriented OpenVDB documentation shows that field
workflows can be scripted and extracted. These sources establish methods and
documented operations, not the project's required semantic control or visual
quality.

For this comparison, the branch uses one shared volumetric composition rule
without explicit swept-profile construction or feature-specific surface
generators. It is not the leading hypothesis because that common rule may make
explicit part ownership, local coordinates, thin/separate features, and
feature-specific controls harder to diagnose. Those are experiment risks, not
established failures; the implicit baseline is required so the hybrid claim
can be falsified against it.

### Option 2: Skeleton-radius/generalized-cylinder-only

This branch is credible because the generalized-cylinder and general-skeleton
sources directly describe semantic or profile-driven implicit surface
constructions. Explicit skeletons and radii offer a clear control model for
parts, proportions, and attachments and may preserve useful lineage.

For this comparison, explicit centerlines and swept profiles are the
construction rule, without the hybrid's separately selected blending and
feature-generator layers; an implicit scalar field may still be an internal
representation. It is not the leading hypothesis because a structure-only
method may expose limitations at organic branch junctions and at features such
as muzzle, paws, ears, feet, and tail. These are project hypotheses to test,
not conclusions from the sources. The branch remains a required baseline.

### Option 3: Parametric patches/subdivision-first

This branch is credible because subdivision surfaces are an established smooth
surface representation in character animation, and the OpenSubdiv overview
documents a library designed for subdivision workflows. A patch-first branch
could make surface continuity and animation-oriented topology explicit.

It is not the leading Stage 1 hypothesis because it risks requiring an
authored patch layout or base topology before the project has tested native
semantic generation. It may also shift the first proof toward topology and
deformation questions that DR-0007 deliberately places later. This is a scope
and proof-risk inference, not a claim that subdivision surfaces are unsuitable
for later production.

### Option 4: Hybrid semantic structures, implicit blending, and reusable
specialized generators

The hybrid branch is credible because it combines the explicit controls of
skeleton/radius constructions with field blending and module-specific controls
where those address different failure modes. The combined rationale is a
project hypothesis: it is selected to test whether semantic control and
organic-junction quality can coexist without fixture-specific patches. It is
preferred for the disposable experiment, not accepted as permanent
architecture. **Recommendation: Option 4.**

## Adversarial Review Response

Current-revision review: **Pending**. Ben requested two independent
adversarial reviews for these technically complex decisions; neither review
exists yet. No review finding is being treated as resolved, and this record
remains Proposed with Owner approval Pending.

## Implementation and Proof Obligations

- Design EXP-0001 to compare at least a generalized-cylinder/skeleton
  baseline, an implicit-field baseline, and the hybrid branch. Do not
  register or create EXP-0001 as part of this record.
- Define and pin the three branches by their allowed construction operations;
  do not treat an internal scalar-field storage choice as branch identity.
- Use the fixed DR-0008 fixture identities and the same semantic inputs,
  bounds/policy where applicable, diagnostics, captures, and structural checks
  for each branch. Record failed and inconclusive cases.
- Measure connectedness, semantic-region and local-field preservation,
  determinism, junction and feature failures, and extraction/topology
  characteristics separately from subjective visual assessment.
- Attribute every specialized module to a reusable grammar capability and
  record any fixture-specific correction as a failure. Do not add a bespoke
  patch to make a comparison pass.
- Record exact implementation versions, licenses, hardware, commands, and
  artifact-retention choices when the experiment is later designed. This DR
  does not choose OpenVDB, scikit-image, OpenSubdiv, or another production
  dependency.
- Keep animation-ready topology, runtime field representation, retopology,
  deformation, and backend questions open until the evidence supports a later
  decision.

## Canonical Design Links

- [First morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [Staged first-proof charter](DR-0007-staged-first-proof-charter.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [System architecture overview](../architecture/system-overview.md)
- [Normative specification boundary](../../spec/README.md)
- [Round 6 kickoff plan](../project/kickoff-plan.md)
- [Open research questions](../research/open-questions.md)

## Reversibility and Revisit Triggers

This is a disposable experiment hypothesis and can be replaced before
implementation without a migration. Revisit it if the baselines outperform the
hybrid on the declared Stage 1 evidence, if the hybrid requires
fixture-specific corrections, if semantic lineage cannot be preserved, or if the
fixture envelope exposes unsupported thin, separate, or junction features.
Regardless of experiment outcome, a permanent surface architecture, runtime
field representation, animation topology, and backend require their own
evidence and decision.

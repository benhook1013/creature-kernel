# DR-0010: Stage 1 surface extraction and semantic-field propagation

ID: DR-0010

Scope: Specification and architecture

Status: Proposed

Revision: 2

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-09

Date decided: —

Revision history: Revision 1 was reviewed in Round 6 by the [architecture and
proof-boundary review](reviews/DR-0010-rev-01-review-01.md) and the
[geometry, topology, and semantic-data review](reviews/DR-0010-rev-01-review-02.md).
Both reviews remain preserved as historical evidence and are stale for this
revision. Revision 2 applies Ben's settled resolutions: a common normalized
field contract and three-grid convergence controls, explicit semantic
contributor lineage and analytical oracles, and required topology,
orientation, volume, and determinism diagnostics. A current-revision review is
pending. This proposal remains unaccepted.

Supersedes: —

Superseded by: —

## Context

The Stage 1 surface experiment needs a reproducible extraction policy and a
way to preserve semantic information while a continuous field becomes an
ephemeral mesh. The policy must make branches comparable without pretending
that a sampled mesh is an animation-ready or production topology contract.

The original [Marching Cubes paper](https://www.cs.toronto.edu/~jacobson/seminar/lorenson-and-cline-1987.pdf)
establishes the classic cell-case approach for extracting an isosurface from a
sampled scalar field. The [scikit-image marching_cubes
documentation](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes)
documents a current implementation interface, including a Lewiner method and
parameters such as level, spacing, step size, degenerate-face handling, and
method selection. Those sources establish algorithmic and API capabilities;
they do not establish project-wide determinism, animation topology, or a
production dependency.

[Dual Contouring of Hermite Data](https://people.eecs.berkeley.edu/~jrs/meshpapers/JuLosassoSchaeferWarren.pdf)
establishes an adaptive contouring approach using Hermite data. That makes an
adaptive alternative technically credible, but does not prove its
comparability, semantic propagation, or suitability for this Stage 1 proof.
The [Subdivision Surfaces in Character Animation](https://doi.org/10.1145/280814.280826)
paper establishes the relevance of smooth, deformation-oriented surface
representation to character animation; applying that to a direct topology
alternative is a project inference, not evidence that a patch-first method is
ready now.

The [OpenVDB Python
documentation](https://www.openvdb.org/documentation/doxygen/python.html)
documents a Python interface to a sparse-volume toolkit. Its
[ParticlesToLevelSet attribute-transfer
documentation](https://www.openvdb.org/documentation/doxygen/classopenvdb_1_1v13__0_1_1tools_1_1ParticlesToLevelSet.html)
documents transfer of particle attributes into a level-set workflow, and its
[VolumeToMesh documentation](https://www.openvdb.org/documentation/doxygen/structopenvdb_1_1v12__1_1_1tools_1_1VolumeToMesh.html)
documents volume-to-mesh conversion. These establish examples of field
extraction and attribute transfer, not a selection of OpenVDB or any other
library as a production dependency.

## Decision

### Stage 1 extraction and sampling policy

**Recommendation: Option 2 — deterministic, pinned, uniform-grid Lewiner
Marching Cubes with common sampling and convergence controls.** Stage 1 uses a
common normalized field contract for every comparison branch. Before execution
the experiment must define, at minimum:

- coordinate system and units;
- scalar sign convention and the meaning of the isovalue;
- frozen per-fixture bounds and padding policy;
- grid interpolation model and out-of-domain behaviour;
- orientation and gradient convention; and
- deterministic postprocessing order, ordering, tie handling, and diagnostic
  behaviour.

For each fixture, every branch uses the same frozen bounds and three uniform
grids: coarse, nominal, and fine. Exact grid sizes are a later registration
choice. The design must check clipping and feature-relative sampling, and
measure convergence or stability for components, named junctions, gaps, and
thin features. Any branch or fixture that deviates from the common policy is a
separate exploratory run, not part of the primary comparison.

The pinned Lewiner guarantee is scoped to reconstruction from the sampled
grid. It does not guarantee topology or geometry of the underlying continuous
field, remove sampling artefacts, produce animation-ready edge flow, or
establish a production-quality meshing contract. Adaptive extraction,
retopology, deformation loops, UV topology, and topology continuity across
structural changes remain deferred.

### Semantic-field propagation policy

**Recommendation: Option 2 — preserve parallel semantic contributors and
diagnostics through field construction and extraction.** The extraction result
must retain links to the resolved semantic graph while keeping the following
semantics distinct from ephemeral mesh indices:

- raw contributors and a top-k contributor view, with normalized weights;
- categorical ownership as a separate value, never as an interpolated scalar;
- for every contributor, semantic ID, local-chart identity, local coordinate,
  and validity state; and
- missing-field masks and ambiguity diagnostics, including near-boundary and
  out-of-domain cases.

Contributor semantics must be defined per construction operator before the
experiment. The skeleton/swept-profile operator identifies its semantic
centerline, profile, and attachment contributors; the general implicit-field
operator identifies the source semantic contributions to its composition; the
selected-blending operator records its operand contributors and blend
weights; and a specialized generator identifies its semantic module, local
chart, and any module-level contributors. These are lineage descriptions, not
an instruction to choose a storage schema or to make incompatible charts
blendable. Categorical IDs must not be interpolated like scalar fields, and
incompatible local charts must not be blended; the result must instead retain
the ambiguity or invalidity diagnostic.

Independent analytical fixtures and oracles are required for coverage,
weight normalization, missing contributors, local-chart reconstruction and
validity, semantic landmarks, and expected boundary ambiguity. They are
branch-neutral checks on the propagation contract, not visual judgments.

The policy is compatible with documented field workflows that transfer
attributes into a level-set process, but those sources provide feasibility
evidence rather than a dependency decision. Exact storage layout, numeric
thresholds, interpolation details, and registration identifiers remain later
specification or experiment-registration work. Durable semantic identity and
build/artifact provenance stay separate from generated vertex, face, triangle,
LOD, or array indices, as required by
[DR-0006](DR-0006-durable-semantic-and-artifact-identity.md).

## Consequences

- The Stage 1 branches obtain a common, reproducible extraction baseline and
  comparable semantic diagnostics.
- A uniform grid may spend work in empty or high-detail regions and may miss
  information below its sampling resolution. Those limitations are accepted
  for the disposable proof and must be recorded.
- Three-grid convergence and feature-relative checks expose sampling and
  clipping limitations instead of presenting one resolution as continuous
  field truth. Deviations remain separate exploratory evidence.
- Contributor lineage, chart validity, analytical oracles, and explicit
  ambiguity diagnostics make semantic propagation inspectable without
  interpolating categorical data or incompatible charts.
- Required topology, orientation, volume, and normal-vs-gradient checks make
  structural failures visible; they do not turn mesh output into a production
  topology contract.
- Mesh indices remain ephemeral build outputs. Consumers must use durable
  semantic identity and separately recorded artifact/build provenance for
  cross-build references.
- The policy does not promise adaptive quality, animation-ready topology,
  stable topology under structural change, UVs, deformation, or runtime
  extraction. It also does not claim bitwise cross-platform output; process,
  thread, numeric, platform, canonicalization, and tolerance scope must be
  recorded for an experiment-level determinism claim. Those topics remain open
  for later evidence and decisions.

### Required diagnostics and determinism scope

The primary evidence ledger must include boundary and non-manifold reporting,
Euler characteristic or genus where applicable, self-intersection checks,
winding and orientation checks, signed-volume checks, and
normal-versus-field-gradient checks. A check that is not applicable must be marked as such with its
reason; an unavailable or ambiguous check is not an implicit pass.

Experiment registration must define process, thread, numeric, and platform
scope; mesh canonicalization and hashes; geometric tolerances; and how
nondeterminism is isolated at each stage. A repeated deterministic run is
required within that declared scope. The result may support scoped
repeatability, but it must not claim bitwise cross-platform output without
separate evidence.

## Alternatives Considered

### Extraction Option 1: Classic Marching Cubes

Classic Marching Cubes is credible because the original paper defines a
well-known sampled-cell isosurface extraction method and provides a simple
baseline against which later methods can be compared. It is useful as a
reference implementation or ablation branch.

It is not selected as the Stage 1 policy because this record needs the pinned
Lewiner implementation's documented method and explicit project controls for
ambiguity, deterministic postprocessing, and comparable configuration. The
classic paper alone does not provide those project-specific controls.

### Extraction Option 2: Deterministic pinned uniform-grid Lewiner Marching Cubes

This is credible because the scikit-image documentation exposes a Lewiner
method and controls for level, spacing, step size, degenerates, and method.
The project inference is that pinning the implementation, common normalized
field contract, three-grid policy, configuration, convergence checks, and
postprocessing provides a practical comparable Stage 1 baseline. It is
selected only for the disposable experiment.
**Recommendation: Option 2.**

### Extraction Option 3: Adaptive Dual Contouring

Dual Contouring is credible because the primary paper describes contouring
with Hermite data and adaptive spatial subdivision, which may represent detail
more efficiently and can support a different topology strategy.

It is deferred because adaptive cells, Hermite sampling, balancing, semantic
field transfer, and deterministic comparison add proof obligations before the
first surface evidence is understood. Deferral is not a claim that Dual
Contouring is unsuitable for production.

### Extraction Option 4: Patch-first/direct topology

Patch-first extraction is credible because direct topology and subdivision
representations can make continuity and deformation intent explicit; the
character-animation subdivision source establishes the relevance of that
concern. A patch-first branch could become appropriate when animation-ready
topology is the active proof target.

It is deferred because Stage 1 is testing native surface generation and
semantic propagation, not yet committing to a handcrafted patch layout or
animation topology. The project has not established the required patch
grammar or topology contract.

### Semantic propagation Option 1: Label after meshing

Post-mesh labels are credible as a minimal implementation and may suffice for
coarse visualization. They are not selected because labels assigned only
after extraction can lose the field-local context needed to diagnose boundary
ownership, blended junctions, and local coordinates, especially when a vertex
is near multiple semantic regions.

### Semantic propagation Option 2: Parallel fields sampled at vertices

This is credible because field workflows can carry more than an isosurface
scalar: the OpenVDB attribute-transfer documentation provides primary evidence
for transferring attributes into a level-set workflow. The project adds the
inference that raw and top-k contributors, normalized weights, categorical
ownership, local-chart identity and validity, analytical oracles, and explicit
ambiguity diagnostics are the most direct bounded way to test lineage in Stage
1. **Recommendation: Option 2.**

### Semantic propagation Option 3: Separate region meshes and stitch

Separate region meshes are credible because independently generated semantic
modules can be inspected and specialized, and stitching can make ownership
explicit. They are not selected because seams, duplicate boundaries, stitch
ordering, and field continuity would become additional first-proof variables;
the policy should first test shared-field propagation through one extraction
pass.

## Adversarial Review Response

The [architecture/proof-boundary review](reviews/DR-0010-rev-01-review-01.md)
is Complete with an Accept recommendation at Medium confidence and no
blocker; its nonblocking follow-ups are a cross-branch sampling-control rule
and branch-neutral semantic oracles. The [geometry/topology/semantic-data
review](reviews/DR-0010-rev-01-review-02.md) is Complete with a Revise
recommendation at High confidence. Both are preserved as historical Revision 1
reviews and are stale for this Revision 2. They identified the common field
contract, convergence controls, and semantic lineage beyond vertex sampling as
the material revision topics. Ben's settled recommendations are applied above.
Review of this material Revision 2 is pending, and Owner approval remains
Pending; no finding is silently treated as an acceptance of the decision.

## Implementation and Proof Obligations

- Define the normalized field contract, common frozen per-fixture bounds and
  padding, and the coarse/nominal/fine uniform grids before running the
  disposable experiment. Record the implementation version, isovalue,
  interpolation, out-of-domain behaviour, orientation/gradient convention,
  postprocessing order, tie rules, and diagnostic schema.
- Run clipping and feature-relative sampling checks and measure convergence or
  stability for components, junctions, gaps, and thin features. Keep any
  deviation as a separately labelled exploratory run.
- Define per-construction-operator contributor semantics and preserve raw and
  top-k contributors, normalized weights, categorical ownership, contributor
  IDs, chart identities, local coordinates, validity, missing masks, and
  ambiguity diagnostics. Do not interpolate categorical IDs or blend
  incompatible charts.
- Provide independent analytical fixtures and oracles for coverage,
  normalization, missing contributors, chart reconstruction/validity,
  landmarks, and expected boundary ambiguity.
- Record vertex/face counts, connectedness, degenerate or ambiguous cases,
  boundary/non-manifold status, Euler/genus where applicable,
  self-intersections, winding/orientation, signed volume, normals versus field
  gradients, semantic preservation, and deterministic repeatability.
- Define process, thread, numeric, and platform scope, canonicalization and
  hashes, geometric tolerances, and stage-level nondeterminism isolation in the
  experiment registration. Do not claim bitwise cross-platform output.
- Keep structural measurements separate from subjective visual assessment and
  from any later animation or runtime claim. Preserve durable semantic
  identity, resolved-graph lineage, and build/artifact provenance independently
  of ephemeral mesh indices.
- Record exact library versions, licenses, hardware, commands, and retained
  artifacts when implementation begins. This DR does not select OpenVDB,
  scikit-image, OpenSubdiv, or another production dependency or production
  topology.
- Revisit adaptive extraction, direct topology, retopology, deformation loops,
  UVs, and topology continuity only after Stage 1 evidence or a later proof
  makes those obligations active.

## Canonical Design Links

- [Hybrid surface-generation experiment hypothesis](DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
- [Staged first-proof charter](DR-0007-staged-first-proof-charter.md)
- [First morphology and Stage 1 embodiment envelope](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [System architecture overview](../architecture/system-overview.md)
- [Normative specification boundary](../../spec/README.md)
- [First surface experiment design](../research/first-surface-experiment-design.md)
- [Round 6 kickoff plan](../project/kickoff-plan.md)

## Reversibility and Revisit Triggers

The extraction and propagation policies are disposable Stage 1 controls and
can be replaced without a production migration. Revisit them if fixed-grid
sampling hides material features, repeated runs are not reproducible, semantic
fields cannot be propagated with useful diagnostics, or another extraction
method provides stronger evidence for the active proof. A later production
choice must separately evaluate adaptive extraction, retopology, deformation,
UVs, topology continuity, dependency portability, and runtime budgets.

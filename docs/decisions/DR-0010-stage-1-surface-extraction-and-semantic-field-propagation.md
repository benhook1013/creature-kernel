# DR-0010: Stage 1 surface extraction and semantic-field propagation

ID: DR-0010

Scope: Specification and architecture

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

### Stage 1 extraction policy

**Recommendation: Option 2 — deterministic, pinned, uniform-grid
Lewiner Marching Cubes.** Stage 1 should fix the sampled bounds, grid
resolution, isovalue, spacing convention, implementation version, and
postprocessing order for each comparison run. Inputs, configuration, compiler
version, and seed must be recorded. Postprocessing must use deterministic
ordering and tie handling, and diagnostics must expose invalid or ambiguous
samples rather than silently repairing them.

This policy is an evidence-control measure. Fixed sampling and a pinned
implementation make branch outputs comparable under the declared experiment;
they do not guarantee the topology of the underlying continuous field, remove
sampling artefacts, produce animation-ready edge flow, or establish a
production-quality meshing contract. Adaptive extraction, retopology,
deformation loops, UV topology, and topology continuity across structural
changes remain deferred.

### Semantic-field propagation policy

**Proposed policy: Option 2 — carry parallel semantic fields, part fields,
local coordinates, ownership/blend weights, and diagnostics through field
construction and extraction, then sample them at generated vertices with
deterministic tie rules.** The extraction result must retain links to the
resolved semantic graph and distinguish part ownership, blend weights, and
local coordinates from mesh indices. Ties, near-boundary ambiguity, missing
fields, and out-of-domain samples must be reported with stable diagnostics.

This policy is compatible with the documented OpenVDB example of transferring
particle attributes into a level-set workflow, but that example is supporting
evidence for feasibility rather than a dependency decision. The exact field
formats, interpolation rules, and ambiguity thresholds remain specification
work. Durable semantic identity and build/artifact provenance stay separate
from the generated vertex, face, triangle, LOD, or array indices, as required by
[DR-0006](DR-0006-durable-semantic-and-artifact-identity.md).

## Consequences

- The Stage 1 branches obtain a common, reproducible extraction baseline and
  comparable semantic diagnostics.
- A uniform grid may spend work in empty or high-detail regions and may miss
  information below its sampling resolution. Those limitations are accepted
  for the disposable proof and must be recorded.
- Propagated fields make semantic lineage and local-coordinate checks possible
  at generated vertices, but deterministic sampling cannot resolve ambiguous
  ownership without a declared rule and diagnostic.
- Mesh indices remain ephemeral build outputs. Consumers must use durable
  semantic identity and separately recorded artifact/build provenance for
  cross-build references.
- The policy does not promise adaptive quality, animation-ready topology,
  stable topology under structural change, UVs, deformation, or runtime
  extraction. Those topics remain open for later evidence and decisions.

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
The project inference is that pinning the implementation and fixing grid
policy, configuration, and postprocessing provides a practical comparable
Stage 1 baseline. It is selected only for the disposable experiment.
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
inference that parallel semantic fields with deterministic sampling and
ambiguity diagnostics are the most direct way to test lineage in Stage 1.
**Recommendation: Option 2.**

### Semantic propagation Option 3: Separate region meshes and stitch

Separate region meshes are credible because independently generated semantic
modules can be inspected and specialized, and stitching can make ownership
explicit. They are not selected because seams, duplicate boundaries, stitch
ordering, and field continuity would become additional first-proof variables;
the policy should first test shared-field propagation through one extraction
pass.

## Adversarial Review Response

Current-revision review: **Pending**. Ben requested two independent
adversarial reviews for these technically complex decisions; neither review
exists yet. No review finding is being treated as resolved, and this record
remains Proposed with Owner approval Pending.

## Implementation and Proof Obligations

- Define the fixed bounds, uniform-grid resolution, isovalue, spacing,
  implementation version, postprocessing order, tie rules, and diagnostic
  schema before running the disposable experiment.
- Compare extraction under the same field inputs and record vertex/face counts,
  connectedness, degenerate or ambiguous cases, semantic ownership and local
  coordinate preservation, and deterministic repeatability.
- Keep structural measurements separate from subjective visual assessment and
  from any later animation or runtime claim.
- Preserve durable semantic identity, resolved-graph lineage, and build/artifact
  provenance independently of ephemeral mesh indices.
- Record exact library versions, licenses, hardware, commands, and retained
  artifacts when implementation begins. This DR does not select OpenVDB,
  scikit-image, OpenSubdiv, or another production dependency.
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
- [Round 6 kickoff plan](../project/kickoff-plan.md)

## Reversibility and Revisit Triggers

The extraction and propagation policies are disposable Stage 1 controls and
can be replaced without a production migration. Revisit them if fixed-grid
sampling hides material features, repeated runs are not reproducible, semantic
fields cannot be propagated with useful diagnostics, or another extraction
method provides stronger evidence for the active proof. A later production
choice must separately evaluate adaptive extraction, retopology, deformation,
UVs, topology continuity, dependency portability, and runtime budgets.

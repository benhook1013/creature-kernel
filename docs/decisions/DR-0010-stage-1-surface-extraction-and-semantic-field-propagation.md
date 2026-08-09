# DR-0010: Stage 1 surface extraction and semantic-field propagation

ID: DR-0010

Scope: Specification and architecture

Status: Proposed

Revision: 5

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-09

Date decided: —

Revision history: Revision 1 was reviewed in Round 6 by the [architecture and
proof-boundary review](reviews/DR-0010-rev-01-review-01.md) and the
[geometry, topology, and semantic-data review](reviews/DR-0010-rev-01-review-02.md).
Both reviews remain preserved as historical evidence and are stale for this
revision. Revision 2 was reviewed by the [architecture/governance
review](reviews/DR-0010-rev-02-review-01.md) and the [geometry/semantics
review](reviews/DR-0010-rev-02-review-02.md); both reviews are preserved as
historical evidence and are stale for this revision. Revision 3 applied Ben's
settled resolutions to shared evidence precedence, phase and topology
controls, and cross-operator semantic contribution algebra. Revision 3 was
reviewed in Round 9 by the [architecture/proof/governance
review](reviews/DR-0010-rev-03-review-01.md) and [geometry/semantics/measurement
review](reviews/DR-0010-rev-03-review-02.md); both reviews are preserved as
historical evidence and are stale for this revision. Revision 4 applies Ben's
settled Round 9 resolutions to causal evidence classification and the nested
semantic contribution algebra. Revision 4 was reviewed by the
[architecture/proof/governance review](reviews/DR-0010-rev-04-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0010-rev-04-review-02.md);
both recommended `Revise` at High confidence. Revision 5 applies Ben's
settled Round 10 resolutions to finite branch-readiness termination, the raw
contribution measure and its representation-equivalence law, and the
cross-resolution phase/convergence envelope. The Revision 4 reviews remain
preserved as historical evidence and are stale for this revision. The current
[architecture/proof/governance review](reviews/DR-0010-rev-05-review-01.md) is
Complete with an Accept recommendation at High confidence and no DR-0010-
specific actionable objection in that lens. The current
[geometry/semantics/measurement review](reviews/DR-0010-rev-05-review-02.md)
is Complete with a Revise recommendation at High confidence and records the
two unresolved findings below. Revision 5 remains Proposed with Owner
approval Pending; Review Complete records evidence, not a clean review or
acceptance.

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
Marching Cubes with common sampling, phase, topology, and convergence
controls.** Stage 1 uses a
common normalized field contract for every comparison branch. Before execution
the experiment must define, at minimum:

- coordinate system and units;
- scalar sign convention and the meaning of the isovalue;
- frozen per-fixture bounds and padding policy;
- grid interpolation model and out-of-domain behaviour;
- orientation and gradient convention; and
- deterministic postprocessing order, ordering, tie handling, and diagnostic
  behaviour.

For each fixture, every branch uses the same frozen normalized domain,
per-fixture bounds and padding, nested or otherwise aligned grid origins, and
three uniform grids: coarse, nominal, and fine. Exact grid sizes and origins
are later registration choices. At every convergence resolution, phase
evaluation must use a nonempty phase subset shared with the other convergence
resolutions. Nominal resolution may add extra deterministic sub-voxel phases
for diagnostic coverage, but it may not replace the shared subset. Evaluate
convergence and stability for components, named junctions, gaps, thin
features, and predeclared topology invariants across the shared phase
envelope, not at zero phase alone. The exact domain, bounds, padding, origins,
grid sizes, phase sets, shared subset, envelope aggregation, and numerical
thresholds are frozen at experiment registration. Any branch or fixture that
deviates from the
common policy is a separate exploratory run, not part of the primary
comparison.

An independent continuous-field/isovalue clearance oracle must verify clearance
at all six domain faces. Clipping includes an isovalue intersection or a
continuous-field clearance violation at any face; the registration freezes the
clearance interpretation and threshold without this record selecting numeric
values. For every valid initial closed creature exterior, the default expected
topology invariant is one watertight connected genus-zero component. A fixture
may declare another valid component or genus expectation only prospectively in
its registration. Expected component and topology invariants must be recorded
before execution. The causal classification follows the shared precedence in
DR-0009. Before a branch-specific terminal condition, an independently
demonstrated shared apparatus or common-pipeline failure, an unavailable or
invalid mandatory oracle/evidence result, an unready branch that has not
exhausted its bounded remediation/implementation budget, or genuinely
indeterminate attribution makes the affected comparison `Inconclusive`; it is
not an implicit pass. The registration must freeze a finite
readiness-remediation/implementation budget and terminal rule for each branch.
If a branch exhausts its branch-specific budget without becoming ready or
producing comparable valid evidence, that is the branch's bounded feasibility
failure under DR-0009. It is not endless unreadiness, a universal-impossibility
claim, or permission to silently remove the branch; retain the branch and
affected contrasts with the DR-0009 consequence. Once apparatus and readiness
are valid, a registered measurement that violates frozen clearance,
convergence, phase/topology, feasibility/budget, or another mandatory criterion
is a valid branch technology failure, not unavailable evidence. That
technology outcome is governed by DR-0009.

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

Semantic lineage uses a canonical raw contribution measure; it represents
semantic lineage, not a physical force. Lineage distribution keys are durable
`(semantic_id, chart_id)` pairs wherever chart identity applies, with the
declared semantic contributor key used where it does not. A leaf emits unit
raw mass over its durable key. For an operator with child raw measures `mu_i`,
declared non-negative coefficients `a_i`, and declared non-negative transfer
mappings `T_i`, its raw output is `mu = sum_i a_i T_i(mu_i)`. No intermediate
child normalization occurs. Duplicate durable keys are coalesced in this raw
measure. Every raw value must be finite and non-negative, and the complete raw
measure must have a finite positive total. Normalize exactly once at the
observation/report boundary.

Representation equivalence means equality of the flattened durable-key raw
masses and path-transfer weights after the declared mappings are applied; it
does not mean merely having the same leaves under arbitrary binary averages.
The default unweighted associative union sums raw measures. Weighted operators
preserve their declared path coefficients. A local equal-weight binary average
is not automatically reassociation-equivalent: two nestings are equivalent
only when their flattened raw masses and path-transfer weights are equal. No
DAG or storage schema is required by this law. For unit leaves `A`, `B`, and
`C`, the naive normalized binary averages produce `(1/4, 1/4, 1/2)` for
`(A+B)+C` but `(1/2, 1/4, 1/4)` for `A+(B+C)`, whereas the canonical raw
unweighted union produces equal `(1/3, 1/3, 1/3)` after the one observation
normalization in either reassociation.

After observation normalization, derive the top-k view and residual mass,
hard-selection and cutoff results, and their tie/ambiguity diagnostics. Top-k
weights retain their full-distribution normalized values and are not
renormalized; residual mass is explicit. Hard-selection and cutoff ties use a
deterministic durable-key order and record ambiguity whenever the declared tie
condition is met. Categorical ownership and chart fields are parallel
post-normalization values, not interpolated scalars. Swept attachments and
specialized modules must each declare their raw transfer or aggregation rule;
incompatible charts must not be silently blended.

The skeleton/swept-profile operator identifies its semantic centerline,
profile, and attachment contributors; the general implicit-field operator
identifies the source semantic contributions to its composition; the
selected-blending operator records its operand contributors and blend weights;
and a specialized generator identifies its semantic module, local chart, and
any module-level contributors. Coefficients and transfer mappings are declared
against the corresponding durable operands or keys. These are lineage
descriptions, not an instruction to choose a storage schema or to make
incompatible charts blendable. Contributor local coordinates, validity,
missing-field masks, categorical ownership, and incompatible-chart state
remain parallel non-scalar values. At chart seams, retain multiple
contributors or an explicit invalid/ambiguous state.

Independent analytical oracles define expected distributions, tie outcomes,
discarded residual mass, chart-seam validity, and chart validity without
reusing the propagation implementation. Closed-form cases must include an
equivalent reassociation and a naive binary-average counterexample, plus
nesting, duplicate keys, operand scaling, operand order, coefficient order,
hard-selection and cutoff ties, residual mass, and incompatible charts. A
missing, non-finite, negative, or non-positive total, omitted contributor, or
unresolved chart state is a diagnostic, not a normalized pass.

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
- Three-grid convergence over a common nonempty phase subset, deterministic
  nominal extra phases, continuous face-clearance checks, and feature-relative
  checks expose sampling and clipping limitations instead of presenting one
  resolution or zero phase as continuous-field truth. Deviations remain
  separate exploratory evidence.
- Contributor lineage, shared contribution algebra, chart validity,
  independent analytical oracles, and explicit ambiguity/residual diagnostics
  make semantic propagation inspectable without interpolating categorical data
  or incompatible charts. Raw-measure flattening makes default unweighted union
  associative and preserves weighted path coefficients; it does not make local
  equal-weight binary averages reassociation-equivalent unless their flattened
  raw masses agree. Normalization occurs once at observation/report time, after
  which top-k, residual, hard-selection, cutoff ties, and parallel categorical
  or chart fields are derived.
- Required topology invariants, face-clearance, orientation, volume, and
  normal-vs-gradient checks make structural failures visible; they do not turn
  mesh output into a production topology contract.
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
normal-versus-field-gradient checks. A check that is not applicable must be
marked as such with its reason; an unavailable or ambiguous check is not an
implicit pass.

Experiment registration must define process, thread, numeric, and platform
scope; mesh canonicalization and hashes; geometric tolerances; how
nondeterminism is isolated at each stage; and a finite readiness-remediation/
implementation budget and terminal rule for each branch. A repeated
deterministic run is required within that declared scope. The result may
support scoped repeatability, but it must not claim bitwise cross-platform
output without separate evidence.

Evidence and readiness failures use the shared causal precedence in DR-0009.
An independently demonstrated shared apparatus or common-pipeline failure,
unavailable or invalid mandatory oracle/evidence, an unready branch that has
not exhausted its finite branch budget, or genuinely indeterminate attribution
makes the affected primary comparison `Inconclusive` before any technology
outcome. Exhaustion of a branch-specific readiness-remediation/implementation
budget without readiness is that branch's bounded feasibility failure under
DR-0009; it is not endless unreadiness or a universal-impossibility claim. The
branch and affected contrast remain in the record and are not silently
removed. Once apparatus and readiness are valid, a registered measurement that
violates frozen clearance, convergence, phase/topology, feasibility/budget, or
another mandatory criterion is a valid branch technology failure, not
unavailable evidence. That failure contributes to the technology outcome under
DR-0009.

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
1. The selected policy also requires a raw-measure nested contribution algebra
with unit leaves and one observation-boundary normalization. Its closed-form
independent oracle cases include equivalent reassociation and a naive
binary-average counterexample, so equality means equal flattened durable-key
masses and path-transfer weights rather than arbitrary reassociation of local
averages.
**Recommendation: Option 2.**

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

The Revision 3 [architecture/proof/governance review](reviews/DR-0010-rev-03-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0010-rev-03-review-02.md)
both recommended `Revise`, at High confidence. Ben's Revision 4 choices
resolve those findings by distinguishing independently demonstrated shared
apparatus/common-pipeline or unavailable/invalid mandatory evidence from valid
registered branch technology failures, and by defining representation-
invariant nested composition with deterministic coalescence, coefficient,
selection, cutoff, residual, and chart-state rules plus closed-form independent
oracles. The Revision 3 reviews remain preserved as historical evidence and
are stale for Revision 4.

The current [architecture/proof/governance review](reviews/DR-0010-rev-04-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0010-rev-04-review-02.md)
both reviewed Revision 4 and recommended `Revise`, at High confidence. They
identified unresolved finite branch-readiness disposition, the lack of a
nesting-invariant coefficient-composition law and reassociation oracle, and
the lack of a cross-resolution phase/convergence rule. Those Revision 4
reviews remain preserved as historical evidence and are stale for Revision 5.
Ben's settled Revision 5 resolutions define the finite branch budget and
terminal feasibility rule, the canonical raw-measure law and strict
representation equivalence, and the shared cross-resolution phase envelope.

The current [architecture/proof/governance review](reviews/DR-0010-rev-05-review-01.md)
is Complete with an Accept recommendation at High confidence and no
DR-0010-specific actionable objection in that lens. The current
[geometry/semantics/measurement review](reviews/DR-0010-rev-05-review-02.md)
is Complete with a Revise recommendation at High confidence. Its two
unresolved findings are exactly:

1. Transfer mappings are underconstrained for raw-measure flattening/path-
   weight oracles.
2. Phase coordinates, cross-resolution pairing/metrics, envelope aggregation,
   and nonmonotone convergence handling remain underdefined.

Revision 5 remains Proposed with Owner approval Pending and Review status
Complete; these findings remain unresolved pending Ben's disposition. Review
Complete records evidence, not a clean review or acceptance.

## Implementation and Proof Obligations

- Define the normalized field contract, common frozen normalized domain,
  per-fixture bounds and padding, nested or aligned coarse/nominal/fine grid
  origins, and the three uniform grids before running the disposable
  experiment. Record the implementation version, isovalue, interpolation,
  out-of-domain behaviour, orientation/gradient convention, postprocessing
  order, tie rules, and diagnostic schema. At every convergence resolution,
  use a nonempty phase subset shared across resolutions; nominal may add extra
  phases. Evaluate convergence/stability across that shared phase envelope,
  not zero-only. Exact domain, bounds, padding, origins, grid sizes, phase sets,
  envelope aggregation, and thresholds remain registration choices.
- Run clipping, independent six-face continuous-field/isovalue clearance, and
  feature-relative sampling checks; exercise the shared phase subset and any
  nominal extra phases; and measure convergence or stability for components,
  junctions, gaps, thin features, and the predeclared component/topology
  invariants. Keep any deviation as a separately labelled exploratory run.
  Freeze a finite readiness-remediation/implementation budget and terminal rule
  for each branch. Shared apparatus/oracle failure, unavailable or invalid
  mandatory evidence, an unready branch before its budget is exhausted, or
  indeterminate attribution is `Inconclusive` under DR-0009. Exhaustion of a
  branch-specific budget is instead a bounded feasibility failure under
  DR-0009; retain the branch and contrast, make no universal-impossibility
  claim, and do not silently remove it. Once apparatus and readiness are
  valid, a registered violation of a frozen mandatory criterion is a branch
  technology failure governed by DR-0009.
- Define the canonical raw contribution algebra over durable keys. Require
  unit raw leaf measures and, for every operator, declared non-negative
  coefficients and transfer mappings with raw output `mu = sum_i a_i
  T_i(mu_i)`. Do not normalize intermediate children. Coalesce duplicate keys
  in the raw measure; require every raw value to be finite and non-negative and
  the complete raw total to be finite and positive; normalize once at the
  observation/report boundary. Define representation equivalence as equal
  flattened durable-key raw masses and path-transfer weights, with default
  unweighted union summing measures and weighted operators preserving path
  coefficients. Do not require a DAG or storage schema. Preserve complete
  normalized weights, unrenormalized top-k weights, explicit residual mass,
  deterministic durable-key hard-selection and cutoff ties with ambiguity
  flags, categorical ownership and chart fields as parallel post-normalization
  values, contributor IDs, local coordinates, validity, missing masks, and
  chart-seam ambiguity/invalidity. Do not interpolate categorical IDs or blend
  incompatible charts.
- Provide independent analytical fixtures and oracles for coverage,
  distributions and normalization, missing contributors, tie results,
  residual mass, chart reconstruction/validity, landmarks, chart seams, and
  expected boundary ambiguity without reusing propagation implementation.
  Include closed-form cases for an equivalent reassociation and a naive
  binary-average counterexample, plus nesting, duplicate keys, operand scaling,
  operand order, coefficient order, hard/cutoff ties, residual mass, and
  incompatible charts.
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

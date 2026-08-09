# DR-0010: Stage 1 surface extraction and semantic-field propagation

ID: DR-0010

Scope: Specification and architecture

Status: Proposed

Revision: 8

Decision owner: Ben

Owner approval: Pending

Review status: Pending

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
preserved as historical evidence and are stale for this revision. Revision 6
applied only the derived outcome-contract alignment required by the then-
current DR-0009 ownership rules and was unreviewed. Revision 7 superseded that
alignment with Ben's approved DR-0009 Revision 7 choices and was itself
unreviewed. Revision 8 materially updates the inherited ledgers, visual
adjudication, and experiment lifecycle/closure/outcome vocabulary to align
with Ben's approved DR-0009 Revision 8 choices; it does not resolve either of
the two geometry/semantic findings carried forward below. The
[architecture/proof/governance review](reviews/DR-0010-rev-05-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0010-rev-05-review-02.md)
remain historical and stale. Revision 8 remains Proposed with Owner approval
Pending and Review status Pending; Revision 7 is superseded and unreviewed.
The two geometry/semantic findings below remain unresolved and require Ben's
next discussion followed by current-revision review.

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
DR-0009. Registration must freeze the universal identical `C` scaffold and
shared-repair ledger before branch work. Its finite operational admission test
requires all branches to receive the same interface, data, and access, with no
branch-specific construction logic or parameters. The immutable initial `C`
record freezes its base manifest ID, provenance, source, assets, known effort,
finite cap, and budget identity; unknown historic effort is unavailable, not
zero. The checkpoint and base manifest cannot move or mutate. A later repair
may enter finite `C` only when the same universal identical-interface/data/
access and no-branch-specific-construction-logic-or-parameters test still
passes. It becomes one append-only finite repair-log entry with a stable ID,
provenance/source/assets, known or unavailable historical effort, cap
consumption, and affected-evidence declaration. Every evidence item references
the base manifest ID plus the exact repair-log snapshot ID, including an
explicit empty snapshot before repairs; affected evidence is rerun after a
repair. No numeric cap, ID syntax, or storage format is selected here.
Pre-existing branch or subset prototypes are excluded from primary evidence.
Failure or exhaustion of `C` is the shared terminal, comparative
`Inconclusive`.

After the `C` checkpoint, every work item belongs exactly once to finite `C`
for a qualifying universal shared repair, one of the `I`, `S`, `B`, or `G`
capability ledgers, or to the branch-integration ledger.
`I` is the general implicit-field capability, `S` the skeleton/swept-profile
capability, `B` selected blending, and `G` reusable specialized generators.
Capability-ledger scope includes required-layer implementation, tuning, and
remediation; branch-attributed cost includes every required capability ledger
plus integration, while actual total cost counts each work item only once.
Full `C` effort is reported separately. Failures in `I`, `S`, `B`, or `G`
affect only consuming branches; integration failure affects its branch. A
shared apparatus, common-pipeline, or oracle failure makes the affected
comparison `Inconclusive`. A capability or branch issue while its registered
ledger budget remains is remediation state, not an outcome. Feasibility is
scoped to the immutable base `C` manifest ID plus exact repair-log snapshot ID
and the registered attributed branch budget ID. Exhaustion
without readiness or comparable valid evidence is the terminal registered
feasibility failure under DR-0009: a hybrid terminal failure is `Reject`, while
a baseline terminal failure is retained and excluded from the eligible
frontier. No branch is silently removed and no universal-impossibility claim
is made. Generic evidence-unavailability wording cannot override that
branch/failure attribution. Once apparatus and readiness are valid, a registered
measurement that violates frozen clearance, convergence, phase/topology, or
another mandatory criterion is a valid technology failure, not unavailable
evidence; its outcome is governed by DR-0009.

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

### Derived outcome and attribution alignment

The extraction and propagation records inherit DR-0009 Revision 8's outcome
ownership. The universal identical `C` scaffold/shared-repair ledger is
admitted before branch work through the operational test in the experiment
workflow: all branches have the same interface, data, and access, with no
branch-specific construction logic or parameters. Its immutable initial
record includes the base manifest ID, manifest/provenance, source, assets,
known effort, and finite cap; unknown historic effort is unavailable, not
zero. Failure or exhaustion of `C` is a shared terminal and makes the
comparative result `Inconclusive`. After the initial checkpoint, a later repair
may still enter finite `C` only when the same universal identical-interface/
data/access and no-branch-specific-construction-logic-or-parameters test
passes. The repair is one append-only finite repair-log entry with a stable ID,
provenance/source/assets, known or unavailable historical effort, cap
consumption, and affected-evidence declaration. Every evidence item references
the base manifest ID and exact repair-log snapshot ID, including an explicit
empty snapshot; affected evidence is rerun after a repair. Other capability and
effort work is
allocated exactly once to finite `I`, `S`, `B`, or `G` ledgers or the branch-
integration ledger. `I`/`S`/`B`/`G` failures affect only consuming branches;
integration affects its branch. Branch-attributed
cost includes all required capability layers and integration; actual total
cost counts each work item once, with full `C` effort reported separately.
Feasibility is scoped to the immutable base `C` manifest ID plus exact repair-
log snapshot ID and the registered attributed budget IDs.
Pre-existing branch or subset prototypes are excluded from primary evidence.

For each quantitative paired criterion, registration must freeze the effect
estimand, replication, adjudication, multiplicity treatment, practical margin
`±delta`, and valid uncertainty-interval and boundary rules. With effects
oriented in the registered beneficial direction, `B` requires the entire valid
interval to be above `+delta`, `H` requires it to be below `-delta`, `N`
is neutral equivalence requiring it to be wholly inside the neutral margin, and
`U` covers every other
case, including invalid or unavailable evidence. These states are not inferred
from a point estimate; an unresolved `U` result is not equivalence.
Visual criteria use the separate panel protocol in the visual-quality
evaluation document: a minimum of three independent reviewers, masking and
randomized presentation where practical, and recorded individual votes. The
comparative visual rubric uses modality-specific `N` for visual equivalence;
`NA` is separate from `U` and excluded from applicable-cell coverage. The full
per-fixture/site/criterion matrix is the component-attribution result; optional
coverage counts are descriptive only, and there is no collapsed categorical
component outcome. A conditional-effect pattern table is descriptive only and
must not assert independence, synergy, antagonism, or other interaction
claims. Bundle outcome remains separate and grants no component credit; a
component `U` cell does not by itself block bundle `Support`.

Experiment lifecycle, evidence closure, and technology outcome are recorded as
the three fields defined in the [experiment workflow](../../experiments/README.md).
Only `finished` with `complete` evidence closure may calculate a technology
outcome or feasibility annotation. `planned`/`running` remain `open`/`none`,
and an experiment ending without closure is `finished` or `abandoned` with
`incomplete`/`none`; `abandoned` is always `incomplete`/`none`.

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
nondeterminism is isolated at each stage; and the finite `C`/`I`/`S`/`B`/`G`
capability and branch-integration ledgers with their accounting and terminal
rules. The `C` admission test, manifest, provenance, source, assets, known
effort, cap, and budget ID are frozen before branch work; unknown historic
effort is unavailable, not zero. A repeated deterministic run is required
within that declared scope. The result may support scoped repeatability, but
it must not claim bitwise cross-platform output without separate evidence.

Evidence and readiness failures use the shared causal precedence in DR-0009.
An independently demonstrated shared apparatus, common-pipeline, or oracle
failure makes the affected primary comparison `Inconclusive`. Failure or
exhaustion of `C` is also a shared terminal with comparative `Inconclusive`.
An `I`, `S`, `B`, or
`G` capability failure affects only consuming branches, while a capability or
branch issue within its registered ledger budget is remediation state, not
generic evidence unavailability; integration failure affects its branch.
Exhaustion without readiness is the consuming branch's terminal feasibility
failure under DR-0009: a hybrid failure is `Reject`, while a baseline failure
is retained and excluded from the eligible frontier. Feasibility is scoped to
the immutable base `C` manifest ID plus exact repair-log snapshot ID and the
registered attributed budget IDs. Full `C` effort is
separate from actual-once and attributed branch costs.
Generic evidence-unavailability wording cannot override that branch/failure
attribution. The branch, capability, and affected contrast remain in the
record and are not silently removed; no universal-impossibility claim is made.
Once apparatus and readiness are valid, a registered measurement that violates
frozen clearance, convergence, phase/topology, or another mandatory criterion
is a valid branch technology failure, not unavailable evidence. That failure
contributes to the technology outcome under DR-0009.

Experiment lifecycle, evidence closure, and technology outcome are separate
fields. Use `planned | running | finished | abandoned`, `open | complete |
incomplete`, and `none | support | reject | inconclusive` as defined by the
[experiment workflow](../../experiments/README.md). Only `finished` with
`complete` closure may calculate an outcome or feasibility annotation; an
experiment ending without closure is `finished` or `abandoned` with
`incomplete`/`none`, and `abandoned` is always `incomplete`/`none`.

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

The [architecture/proof/governance review](reviews/DR-0010-rev-05-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0010-rev-05-review-02.md)
are preserved as historical Revision 5 evidence and are historical/stale for
Revision 8. Revision 6 was unreviewed and superseded by Revision 7; Revision 7
was itself unreviewed and is superseded by this material alignment. Revision 8
applies only the derived alignment to DR-0009's current outcome, budget,
attribution, visual-adjudication, and experiment lifecycle/closure/outcome
ownership; it does not resolve, narrow, choose options for, or conceal the two
carried findings. They remain exactly:

1. Transfer mappings are underconstrained for raw-measure flattening/path-
   weight oracles.
2. Phase coordinates, cross-resolution pairing/metrics, envelope aggregation,
   and nonmonotone convergence handling remain underdefined.

Revision 8 remains Proposed with Owner approval Pending and Review status
Pending. The findings await Ben's next discussion and current-revision review
after their resolution; no acceptance is implied.

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
  Admit finite `C` first through its operational test: all branches have the
  same interface, data, and access, with no branch-specific construction logic
  or parameters. Record its immutable base manifest ID, universal
  scaffold/shared-repair provenance, source, assets, known effort, finite cap,
  and budget ID; unknown historic effort is unavailable, not zero. A
  post-checkpoint repair may be assigned to finite `C` only when that same
  universal interface/data/access and no-branch-specific-construction-logic-
  or-parameters test passes. Record it as one append-only finite repair-log
  entry with a stable ID, provenance/source/assets, known or unavailable
  historical effort, cap consumption, and affected-evidence declaration. Every
  evidence item references the base manifest ID plus the exact repair-log
  snapshot ID, including an explicit empty snapshot; rerun affected evidence
  after a repair. Failure or exhaustion of `C`
  makes the comparative result `Inconclusive`. Freeze the `C` checkpoint before
  branch work and exclude pre-existing branch/subset prototypes from primary
  evidence. After the checkpoint, allocate each work item exactly once to
  finite `C` for a
  qualifying universal shared repair, to the finite `I`/`S`/`B`/`G` capability
  ledgers, or to the branch-integration ledger. Include all required capability
  layers and integration in branch-attributed cost,
  while actual total cost counts each work item once; report full `C` effort
  separately. `I`/`S`/`B`/`G` failure affects only consuming branches,
  integration failure affects its branch, and a shared apparatus,
  common-pipeline, or oracle failure makes the affected comparison
  `Inconclusive`; a capability or branch issue while its registered ledger
  budget remains is remediation state. Feasibility is scoped to the immutable
  base `C` manifest ID plus exact repair-log snapshot ID and the registered
  attributed budget IDs. Exhaustion without readiness is
  the terminal feasibility failure under DR-0009: retain the branch and
  contrast, apply `Reject` to a hybrid, and retain but exclude a baseline from
  the eligible frontier. Generic evidence-unavailability wording cannot
  override that branch/failure attribution; no universal-impossibility claim
  is made
  and no branch is silently removed. Once apparatus and readiness are valid, a
  registered violation of a frozen mandatory criterion is a branch technology
  failure governed by DR-0009.
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
- Apply the DR-0009 Revision 8 attribution contract: for quantitative criteria
  freeze estimand, replication, adjudication, multiplicity, practical margin
  `±delta`, valid uncertainty intervals, and boundaries; classify `B` only
  when the interval is wholly above `+delta`, `H` only when wholly below
  `-delta`, `N` only when wholly inside the margin, and `U` otherwise or when
evidence is invalid/unavailable. For visual criteria use the separate
minimum-three-reviewer panel with individual
  votes, masking/randomization where practical, and modality-specific `N` for
  visual equivalence; `NA` is separate from `U` and excluded from applicable-
  cell coverage. Aggregate `B`/`H` only at at least two of three with no
  opposite vote, aggregate visual `N` only at at least two of three with no
  `B`/`H`, and otherwise use `U`; fewer than three reviewers is `U` and
  exploratory. The full per-fixture/site/criterion matrix is the component-
  attribution result; optional coverage counts are descriptive only. Keep
  conditional effect patterns literal and descriptive, with no independence,
  synergy, antagonism, or interaction claims. Component `U` does not by itself
  block bundle `Support`; bundle outcome remains separate and grants no
  component credit.
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
- Keep experiment lifecycle, evidence closure, and technology outcome separate.
  Use the three fields from the [experiment workflow](../../experiments/README.md):
  only `finished` with `complete` closure calculates an outcome or feasibility
  annotation; `planned`/`running` remain `open`/`none`, and an experiment
  ending without closure is `finished` or `abandoned` with `incomplete`/`none`.
  `abandoned` is always `incomplete`/`none`.
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

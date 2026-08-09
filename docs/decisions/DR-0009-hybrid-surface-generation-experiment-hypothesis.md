# DR-0009: Hybrid surface-generation experiment hypothesis

ID: DR-0009

Scope: Architecture

Status: Proposed

Revision: 5

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-09

Date decided: —

Revision history: Revision 1 was reviewed in Round 6 by the [architecture and
proof-boundary review](reviews/DR-0009-rev-01-review-01.md) and the
[geometry, topology, and semantic-data review](reviews/DR-0009-rev-01-review-02.md).
Both reviews remain preserved as historical evidence and are stale for this
revision. Revision 2 was reviewed by the [architecture/governance
review](reviews/DR-0009-rev-02-review-01.md) and the [geometry/semantics
review](reviews/DR-0009-rev-02-review-02.md); both reviews are preserved as
historical evidence and are stale for this revision. Revision 3 applied Ben's
settled resolutions to the outcome/readiness precedence, fair tuning and
paired contrasts, and the eligible-baseline frontier. Revision 3 was reviewed
by the [architecture/proof/governance review](reviews/DR-0009-rev-03-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0009-rev-03-review-02.md);
both reviews are preserved as historical evidence and are stale for this
revision.
Revision 4 applies Ben's settled resolutions to causal failure attribution,
strict non-overlapping outcome precedence, comparative visual evidence,
bounded fairness and knowledge reuse, and interaction attribution. Revision 4
was reviewed by the [architecture/proof/governance review](reviews/DR-0009-rev-04-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0009-rev-04-review-02.md);
both recommended `Revise` at High confidence. Those reviews are preserved as
historical evidence and are stale for this revision. Revision 5 applies Ben's
settled Round 10 resolutions: a finite per-branch readiness-remediation and
implementation budget with a terminal feasibility-failure rule; branch-
sensitive baseline disposition; exclusive outcome predicates with complete
frontier dominance and simplicity/match rules; and an exact mutually
exclusive four-state interaction matrix. The current [architecture/proof/
governance review](reviews/DR-0009-rev-05-review-01.md) and [geometry/semantics/
measurement review](reviews/DR-0009-rev-05-review-02.md) are Complete and both
recommend `Revise` at High confidence. Their five unresolved findings are
recorded below. Revision 5 remains Proposed with Owner approval Pending;
Review Complete records evidence, not a clean review or acceptance.

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
credible baselines so that it can be falsified. The earlier reviews also showed
that a bundled branch needs an explicit comparison rule and bounded ablations
before an outcome can be interpreted. EXP-0001 is not registered or created by
this record.

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

### Evidence validity and comparative decision rule

**Recommendation: Option 2 — evidence validity/readiness first, then a
non-inferiority comparison with a predeclared named improvement.** Evidence
validity and branch readiness are evaluated before any technology outcome. A
comparison is affected, and therefore `Inconclusive`, when an independently
demonstrated shared-pipeline or apparatus failure occurs; a mandatory oracle
or evidence source is unavailable or invalid; or attribution is genuinely
indeterminate. A shared apparatus or oracle failure remains this affected-
comparison `Inconclusive` outcome even if attempts to repair it consume time
or effort. It is not converted into a branch feasibility failure, and the
affected fixture, contrast, or full comparison scope must be identified.

Before execution, registration must freeze a finite readiness-remediation and
implementation budget for each branch, including its accounting unit and
scope, starting point, permitted remediation, and terminal rule. This record
does not choose the budget amount, unit, host, implementation, or other
registration value. A branch that cannot reach readiness or produce
comparable valid evidence within its registered finite budget terminates as
`Feasibility failure under the registered implementation and budget`. This
terminal rule prevents endless unreadiness in a registered run. It is a
branch-specific outcome: a hybrid feasibility failure is `Reject`; a baseline
feasibility failure is retained in the record and excludes that baseline from
the eligible frontier. No declared branch is silently removed, and no branch
feasibility failure is a universal-impossibility claim. If baseline failures
leave no eligible baseline, a passing hybrid has only a separate
non-comparative `Feasibility demonstrated` annotation and the comparative
outcome is `Inconclusive`.

After shared apparatus/oracle validity and the branch terminal checks, a valid
registered measurement that violates a frozen mandatory clearance,
convergence, phase/topology, feasibility, budget, or other mandatory
criterion is that branch's mandatory technology failure. A hybrid mandatory
failure, including a missing named improvement, is `Reject`. A baseline-only
mandatory failure is retained and excludes that baseline from the eligible
frontier; it does not remove the declared branch from the experiment. A valid
measurement whose failure attribution remains genuinely indeterminate is
`Inconclusive`.

Mandatory visual quality is a separate Stage 1 visual-floor gate, not a
comparative score. Comparative visual quality is nevertheless an explicit,
predeclared frontier dimension, recorded separately from the visual floor and
from structural, semantic, named-feature, complexity, and effort dimensions.
No scalar score is fabricated. A baseline is eligible only if it is ready and
has complete valid evidence for every declared mandatory gate and comparison
dimension. The eligible passing baselines are all non-dominated baselines on
the predeclared structural/semantic, named-feature, comparative-visual,
complexity, and effort dimensions (the Pareto frontier), rather than one
"strongest" baseline. A baseline is dominated only when another eligible
passing baseline is no worse on every declared dimension and better on at
least one; exact dimension definitions and thresholds are frozen at
registration. Registration also freezes each dimension's applicability,
direction, aggregation and threshold rules, the Pareto dominance relation, a
simplicity partial order, and equivalence/match margins. These choices are
registered controls, not post-hoc judgements about which implementation looks
simple.

A conclusive match or dominance determination requires valid, resolved
evidence for every applicable registered dimension. Missing, invalid,
unavailable, ambiguous, or otherwise unresolved evidence that could affect
that determination makes the affected comparison `Inconclusive`; it cannot be
treated as a conclusive non-inferiority, match, or dominance result. A frontier
baseline conclusively dominates the hybrid when it is no worse on every
applicable dimension and better on at least one under the frozen relation. A
baseline conclusively matches the hybrid when all applicable dimensions are
resolved and every dimension is within its frozen equivalence margin. A
baseline is conclusively simpler only when the frozen simplicity partial order
places it strictly below the hybrid. Any frontier baseline that conclusively
dominates the hybrid causes `Reject`, regardless of whether it is simpler. A
conclusively simpler eligible baseline matching within the frozen equivalence
margins also causes `Reject`.

For outcome precedence, mandatory criteria are frozen pass/fail gates and
frozen non-inferiority bounds, including the mandatory visual floor. A
mandatory regression violates one of those criteria or bounds and has
precedence over all trade-off interpretations, so it is `Reject` for a valid
hybrid result. A nonmandatory regression is a valid worse result that does not
violate a mandatory gate or frozen non-inferiority bound. It may be recorded
as a resolved, predeclared trade-off; if the trade-off or its visual
interpretation remains unresolved, the result is `Inconclusive`. Comparative
visual disagreement is unresolved unless the registered visual protocol
resolves it. These definitions keep mandatory failure, branch feasibility
failure, nonmandatory trade-off, and invalid evidence distinct.

The following predicates are mutually exclusive. They are applied in row
order, and a later row is considered only when no earlier predicate is true.
Rows that require a conclusive match or dominance include the complete-
resolved-evidence condition above; unresolved evidence affecting that
relation therefore reaches the final `Inconclusive` row rather than both a
`Reject` and an `Inconclusive` row.

| Predicate, in precedence order | Primary outcome |
| --- | --- |
| Shared apparatus/common-pipeline failure, unavailable or invalid mandatory oracle/evidence, or genuinely indeterminate attribution affects the comparison | `Inconclusive` for the affected comparison |
| The hybrid reaches the branch terminal `Feasibility failure under the registered implementation and budget` | `Reject` |
| The hybrid has valid evidence and passes mandatory gates, but all declared baseline validity, mandatory, technology, and feasibility checks leave no eligible passing baseline | Comparative `Inconclusive`; only a separate non-comparative `Feasibility demonstrated` annotation may be recorded for the passing hybrid |
| The hybrid has valid evidence and violates a mandatory gate, has a mandatory regression, or lacks the named improvement | `Reject` |
| At least one eligible passing frontier baseline conclusively dominates the hybrid on every applicable registered dimension and is better on at least one | `Reject`, regardless of simplicity |
| No frontier baseline conclusively dominates the hybrid, and a conclusively simpler eligible baseline matches the hybrid within all frozen equivalence margins | `Reject` |
| At least one eligible passing frontier baseline exists; the hybrid passes all mandatory gates, shows the named improvement, meets frozen non-inferiority conditions against every frontier baseline, has no conclusive frontier dominance or simpler match, and has no unresolved declared trade-off | `Support` |
| At least one eligible passing baseline exists, but evidence affecting a conclusive dominance or match determination is unresolved, or a nonmandatory trade-off/comparative visual disagreement remains unresolved after the registered protocol | `Inconclusive` |

Baseline feasibility or technology failures can therefore remove a baseline
from eligibility without removing its record. If one or more eligible
baselines remain, the remaining predicates decide the comparison. An empty
frontier cannot produce comparative `Support`; a passing hybrid then receives
only the separate feasibility annotation described above. A hybrid terminal
failure or mandatory failure cannot be rescued by an empty frontier.
The Stage 1 all-valid-fixtures gate and the separate subjective visual-floor
method remain owned by
[DR-0007](DR-0007-staged-first-proof-charter.md) and the
[visual-quality protocol](../research/visual-quality-evaluation.md).

### Attribution and fairness contract

**Recommendation: Option 2 — five bounded branches with a branch-neutral
fairness and readiness contract.** EXP-0001 uses bounded nested ablation, not
a full factorial sweep. Every branch receives the
same frozen semantic source intent, shared semantic feature vocabulary,
fixture identity, input mapping, bounds and sampling policy, seed/configuration
policy, diagnostics, and common output interface. The experiment must freeze
a branch-operation matrix, allowed construction operations, parameter and
tuning budgets, finite per-branch readiness-remediation/implementation
budgets, and implementation-effort accounting before execution. Baselines
receive the same semantic feature vocabulary and source intent, while
realizing that intent through their own allowed construction rule. Any
remaining incompatibility or missing contributor is reported, not silently
removed from a baseline.

The proposed branch matrix is:

| Branch | Allowed construction operations | Deliberately absent operation |
| --- | --- | --- |
| Skeleton/swept-profile baseline | Semantic skeleton, explicit centerlines, swept profiles, and their declared attachment operations | Selected implicit blending and specialized surface generators |
| General implicit-field baseline | One general volumetric composition rule over the shared semantic inputs | Explicit swept-profile construction and specialized surface generators |
| Skeleton plus selected blending | Skeleton/swept-profile construction plus the preselected implicit blending operations | Specialized surface generators |
| Skeleton plus reusable specialized generators | Skeleton/swept-profile construction plus reusable generators for the declared feature vocabulary | Selected implicit blending |
| Full hybrid | Skeleton/swept-profile construction, selected implicit blending, and the same reusable specialized generators | None of the selected hybrid operations |

The matrix classifies branches by allowed construction operation, not by
whether an implementation stores an intermediate scalar field. A branch may
use an internal field when its construction rule permits it. Before branch
tuning, registration must freeze the shared infrastructure and oracles, branch
definitions and operation matrix, adjustable parameter domains, common
objective, deterministic initialization, stopping rule, and parameter,
evaluation, and implementation-effort budgets. It must also freeze the
output fields, exact selected blend sites, and generator operation set; those
values are deliberately not invented by this record. A reusable generator
remains a grammar capability, not a hidden per-fixture mesh, topology, or rig
correction. This bounded nested ablation supports attribution of the selected
blending and specialized-generator layers without claiming a full factorial
interaction analysis.

Each branch has a separate configuration and workspace. Branches use the same
deterministic search and evaluation budget; for human adjustment rounds, a
preregistered rotating or counterbalanced order may be used instead. The
registration must state which rule applies. Adjustments are global branch
parameters only: no fixture-specific tuning, post-hoc correction, or
per-fixture parameter is allowed in primary comparison. Branch-specific
parameters, corrections, and defect fixes must not be transferred between
branches during primary evidence collection. Shared-core fixes apply to every
affected branch and require rerunning all affected evidence. Unavoidable
knowledge reuse is logged, and shared versus branch-specific implementation,
tuning, and adjustment effort is reported and charged separately.

Before primary comparison, each required branch must pass branch-neutral
analytical readiness fixtures, exercise every required operation in its
declared matrix, and disclose unresolved implementation or fidelity defects.
The fixtures and oracles must be independent of branch-specific visual
success. A branch-specific readiness defect starts the branch's finite
registered readiness-remediation/implementation budget; if the branch still
cannot reach readiness or produce comparable valid evidence when that budget
is exhausted, the branch terminates as `Feasibility failure under the
registered implementation and budget`. A hybrid terminal failure is `Reject`;
a baseline terminal failure is retained and excluded from the frontier. A
shared apparatus, oracle, or common-pipeline defect remains affected-
comparison `Inconclusive` and is not charged as a branch terminal failure.
Missing operation coverage, an unresolved defect that affects a required
operation, or any other failed readiness condition is recorded with its scope
and budget accounting. Readiness does not establish a technology outcome, and
no branch is silently removed.

The following paired per-fixture/site contrasts are predeclared, with each
contrast evaluated using the same objective and global tuning rule:

| Contribution | Without the other contribution | With the other contribution |
| --- | --- | --- |
| Blending | `S+B` versus `S` (blending without generators) | `Full` versus `S+G` (blending with generators) |
| Generators | `S+G` versus `S` (generators without blending) | `Full` versus `S+B` (generators with blending) |

Here `S` is skeleton/swept-profile, `B` is selected blending, and `G` is the
reusable specialized-generator layer. Registration must define, for every
criterion, the beneficial direction and the acceptance rule for the paired
contrasts. For each component and criterion, classify the first state from the
contrast **without the other contribution** and the second state from the
contrast **with the other contribution**. Each state is exactly one of:

- `B` — beneficial in the registered direction;
- `N` — neutral, with no demonstrated directional effect;
- `H` — harmful or reversed against the registered direction; or
- `U` — unresolved because valid evidence or the direction is unavailable,
  invalid, ambiguous, or otherwise not resolved.

Any `U` state makes the interaction unresolved. The exact per-component
interaction matrix is:

| First state (without other); second state (with other) | `B` | `N` | `H` | `U` |
| --- | --- | --- | --- | --- |
| `B` | Independent beneficial | Suppressed to neutral | Reversed/antagonized | Unresolved |
| `N` | Synergy-dependent | No demonstrated effect | Harmful only with other | Unresolved |
| `H` | Interaction-dependent reversal | Harm neutralized | Consistently harmful | Unresolved |
| `U` | Unresolved | Unresolved | Unresolved | Unresolved |

Thus `B/B` is independent beneficial; `B/N` is suppressed to neutral;
`B/H` is reversed/antagonized; `N/B` is synergy-dependent; `N/N` has no
demonstrated effect; `N/H` is harmful only with the other contribution;
`H/B` is an interaction-dependent reversal; `H/N` has harm neutralized; and
`H/H` is consistently harmful. The matrix is mutually exclusive and is
reported per component and criterion. `combined-hybrid-only` is a separate
bundle-level tag when only the combined hybrid comparison supports the named
improvement; it is not a competing component label in this matrix. The matrix
is diagnostic, not a scalar interaction score or a full-factorial claim.

## Consequences

- Stage 1 can test semantic control and organic junction quality together while
  retaining baselines that can disprove the combined hypothesis.
- The evidence-first precedence makes support, rejection, and inconclusive
  outcomes inspectable before evidence exists; it does not turn a mixed
  trade-off into a fabricated scalar score or allow endless unreadiness. Shared
  apparatus/oracle failure remains affected-comparison `Inconclusive`; a
  branch-specific budget-exhausted readiness failure is a terminal feasibility
  failure with branch-sensitive consequences.
  An empty eligible-baseline frontier is comparative `Inconclusive`, even when
  a passing hybrid receives a separate feasibility annotation.
- The five branches expose the two selected hybrid contributions while keeping
  the comparison bounded. Finite readiness-remediation/implementation,
  complexity, tuning, and effort budgets remain part of the interpretation
  rather than hidden or unbounded costs.
- Specialized generators add grammar vocabulary and reusable capabilities;
  they do not license bespoke fixture patches or silently expand the supported
  morphology envelope.
- The hybrid branch has more moving parts and more diagnostic surface than a
  single representation. The experiment must therefore report which component
  produced each result and where a branch failed. The exact B/N/H/U matrix
  makes each paired interaction label mutually exclusive; `combined-hybrid-
  only` remains a separate bundle-level diagnostic tag. The matrix is not a
  scalar interaction score or a full-factorial claim.
- A successful surface experiment would support only the stated Stage 1 claim
  under its fixtures and protocol. It would not settle production topology,
  animation deformation, runtime representation, backend, or performance.
- A failed or inconclusive hybrid result must remain visible and may support a
  different hypothesis, a narrower proof, or a revised decision; it must not be
  converted into an unrecorded implementation exception. A hybrid feasibility
  failure is `Reject`; a baseline feasibility failure remains visible but
  excludes that baseline from the frontier, without a universal-impossibility
  claim or silent removal.

## Alternatives Considered

### Surface-construction alternatives

#### Option 1: SDF/implicit-only

An implicit-only branch is credible because implicit fields naturally provide a
continuous surface description and can blend nearby contributions. The
general-skeleton and generalized-cylinder sources establish relevant implicit
families, while the field-oriented OpenVDB documentation shows that field
workflows can be scripted and extracted. These sources establish methods and
documented operations, not the project's required semantic control or visual
quality.

For this comparison, the branch is the general implicit-field baseline in the
frozen matrix: one shared volumetric composition rule without explicit
swept-profile construction or feature-specific surface generators. It is not
the leading hypothesis because that common rule may make explicit part
ownership, local coordinates, thin/separate features, and feature-specific
controls harder to diagnose. Those are experiment risks, not established
failures; the baseline is required so the hybrid claim can be falsified against
it.

#### Option 2: Skeleton-radius/generalized-cylinder-only

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

#### Option 3: Parametric patches/subdivision-first

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

#### Option 4: Hybrid semantic structures, implicit blending, and reusable
specialized generators

The hybrid branch is credible because it combines the explicit controls of
skeleton/radius constructions with field blending and module-specific controls
where those address different failure modes. The combined rationale is a
project hypothesis: it is selected to test whether semantic control and
organic-junction quality can coexist without fixture-specific patches. It is
preferred for the disposable experiment, not accepted as permanent
architecture. **Recommendation: Option 4.**

### Comparative-decision and attribution alternatives

#### Option 1: Combined-bundle-only comparison

This option would compare the full hybrid only with simpler baselines and
interpret any difference as evidence for the bundle as a whole. It would be
cheaper to run and would avoid attributing a result to one component, but the
hybrid would still be carrying two selected contributions at once. The Round 6
reviews identified that confound as a blocker: without ablations, an observed
improvement could come from blending, specialized generators, their
interaction, or an unequal baseline budget. It was not selected because the
settled claim requires bounded component attribution and a fair common input
and output contract. A future experiment may deliberately make a bundle-only
claim, but it must not present it as attribution.

#### Option 2: Five-branch bounded nested ablation

This option adds the two one-layer branches to the two simpler baselines and
the full hybrid. It preserves a common semantic vocabulary and operation
budget, finite per-branch readiness-remediation/implementation budgets, and
operation matrix while directly testing each selected layer's incremental
contribution. A branch that cannot reach readiness or comparable evidence
within its registered budget terminates as a branch feasibility failure; it is
not left in an endless `Inconclusive` state. It does not test every possible
interaction or parameter combination, but it provides the bounded attribution
needed for this Stage 1 hypothesis.
**Recommendation: Option 2.**

#### Option 3: Full factorial sweep

A full factorial design could test every combination of construction layers,
blend choices, generators, parameter settings, and possibly feature modules.
That would expose interactions more completely, but it would multiply runs,
tuning opportunities, implementation burden, and multiple-comparison and
interpretation obligations before the first surface proof is understood. It
would also risk making the evidence depend on an unbounded search over
operation choices rather than the declared hypothesis. The reviewers' request
was for bounded ablations and a frozen operation matrix, not an exhaustive
factorial search. It was not selected for this experiment; a later study may
use a factorial design if a specific interaction question justifies its cost.

#### Readiness-terminal alternative: inconclusive-only unreadiness

An unready branch could remain `Inconclusive` indefinitely, or be abandoned
without a preregistered finite budget. That would preserve uncertainty but
would permit unreadiness to evade a terminal branch-sensitive outcome and
would make a registered run non-terminating. It is not selected. The selected
rule freezes a finite per-branch readiness-remediation/implementation budget;
branch exhaustion is `Feasibility failure under the registered implementation
and budget`, while independently demonstrated shared apparatus/oracle failure
remains affected-comparison `Inconclusive`.

#### Outcome-predicate alternative: partial frontier or overlapping rows

The experiment could compare one preferred baseline, treat only simpler
baselines as relevant, or permit unresolved dimensions to coexist with a
conclusive match/trade-off row. That would leave dominance incomplete and
make outcome rows overlap. It is not selected. Registration instead freezes
all applicable dimensions, their aggregation and thresholds, the Pareto
relation, a simplicity partial order, and match margins. Conclusive match and
dominance require resolved evidence across every applicable dimension; any
frontier baseline conclusively dominating the hybrid rejects regardless of
simplicity, and a simpler baseline conclusively matching within the margins
also rejects.

#### Interaction alternative: scalar or full-factorial interaction score

A scalar interaction score or an exhaustive factorial sweep could summarize
the bundle, but it would hide whether a component's effect is independent,
suppressed, synergistic, reversed, or neutralized and would add an unbounded
search. It is not selected. The paired contrasts instead use the exact,
mutually exclusive B/N/H/U matrix, while `combined-hybrid-only` is retained as
a separate bundle-level tag. The matrix is diagnostic and does not claim a
scalar or full-factorial result.

## Adversarial Review Response

The [architecture/proof-boundary review](reviews/DR-0009-rev-01-review-01.md)
and [geometry/topology/semantic-data review](reviews/DR-0009-rev-01-review-02.md)
are preserved as historical Revision 1 reviews and are stale for this
Revision 2. They recommended revision at High confidence, identifying the
comparative rule, component attribution, and fair branch contract as blockers.
Ben's settled recommendations are applied above.

The current [architecture/proof/governance review](reviews/DR-0009-rev-03-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0009-rev-03-review-02.md)
both reviewed Revision 3 and recommended `Revise`, at High confidence. Ben's
Revision 4 choices resolve their findings: causal classification now separates
shared apparatus/readiness failures from valid branch technology failures;
mandatory versus nonmandatory regression and strict outcome precedence are
defined; comparative visual quality is a frontier dimension separate from the
visual floor; fairness controls freeze infrastructure, order, workspaces,
budgets, and knowledge reuse; and interaction contrasts constrain independent
component credit. The empty-frontier case is comparative `Inconclusive`, with
only a separate non-comparative feasibility annotation available. These
Revision 3 reviews remain preserved as historical evidence and stale for
Revision 4.

The [architecture/proof/governance review](reviews/DR-0009-rev-04-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0009-rev-04-review-02.md)
reviewed Revision 4 and recommended `Revise`, at High confidence. They are
preserved as historical evidence and are stale for Revision 5. Their findings
are resolved in this proposal by freezing a finite per-branch
readiness-remediation/implementation budget and terminal rule; retaining
shared apparatus/oracle failure as affected-comparison `Inconclusive`; making
hybrid and baseline feasibility failures branch-sensitive; requiring
mutually exclusive outcome predicates; requiring complete resolved evidence
for conclusive match/dominance; disposing every frontier baseline's dominance
and every simpler baseline's match; and replacing overlapping interaction
labels with the exact B/N/H/U matrix plus a separate `combined-hybrid-only`
bundle tag.

The current [architecture/proof/governance review](reviews/DR-0009-rev-05-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0009-rev-05-review-02.md)
are Complete and both recommend `Revise` at High confidence. The five
unresolved findings are exactly:

1. The finite readiness budget begins too late, permitting unbounded
   pre-readiness branch implementation.
2. Bundle comparative `Support` can survive missing ablation evidence while
   affected component-attribution claims remain unresolved.
3. Branch-specific budget-exhausted evidence failure overlaps the shared-
   evidence `Inconclusive` predicate.
4. `N` versus `U` interaction inputs overlap because neutral is not
   demonstrated equivalence.
5. Cyclic dominance can leave eligible baselines but an empty Pareto frontier
   with no outcome.

Revision 5 remains Proposed with Owner approval Pending and is unaccepted.
Review Complete records evidence, not a clean review or acceptance; these
findings remain unresolved pending Ben's disposition. Revision 4 reviews
remain historical and stale.

## Implementation and Proof Obligations

- Design (but do not register or create) EXP-0001 to compare all five branches
  in the frozen operation matrix, with the same semantic source intent,
  feature vocabulary, fixture identities, input mapping, common output
  interface, diagnostics, and capture protocol.
- Freeze the comparative decision rule, named junction/feature criteria,
  eligible-frontier dimensions, branch operations, branch-neutral readiness
  fixtures, required-operation coverage, unresolved-defect disclosures,
  common objective, global initialization and tuning protocol, parameter/
  tuning budgets, finite per-branch readiness-remediation/implementation
  budgets, implementation-effort accounting, exact aggregation and threshold
  rules, and the terminal rule before execution or evidence interpretation.
  Report complexity, effort, and code/parameter/knowledge reuse alongside
  results. Do not allow an exhausted branch to remain indefinitely unready.
- Preserve the shared-failure distinction: an independently demonstrated
  shared apparatus/common-pipeline or unavailable/invalid mandatory oracle or
  evidence result remains affected-comparison `Inconclusive`; a
  branch-specific inability to reach readiness or comparable evidence within
  its finite budget is `Feasibility failure under the registered
  implementation and budget`. Apply `Reject` to a hybrid terminal failure;
  retain and exclude a baseline terminal failure; never make a universal-
  impossibility claim or silently remove a branch.
- Freeze the applicability, direction, aggregation, and thresholds of every
  registered comparison dimension; the Pareto dominance relation; the
  simplicity partial order; and equivalence/match margins. Require valid,
  resolved evidence across every applicable dimension before declaring any
  match or dominance. Treat unresolved evidence affecting that determination
  as `Inconclusive`; check every frontier baseline for conclusive dominance,
  regardless of simplicity, and every simpler eligible baseline for a
  conclusive match.
- Freeze shared infrastructure and mandatory oracles, branch definitions,
  operation matrices, adjustable parameter domains, initialization, stopping
  rule, and deterministic search/evaluation budget before branch tuning. Keep
  branch configurations and workspaces separate; use the same budget or a
  preregistered rotating/counterbalanced human-adjustment order. Prohibit
  transfer of branch-specific parameters, corrections, or defect fixes during
  primary evidence collection. Apply shared-core fixes to all affected
  branches and rerun affected evidence, while logging and separately charging
  unavoidable shared and branch-specific knowledge and effort.
- Keep fixture-specific corrections out of every branch. Record a correction
  attempt as a failure or limitation and retain it in the evidence ledger.
- Measure structural and semantic checks, named junction/feature outcomes,
  determinism, and extraction/topology characteristics separately from the
  subjective visual assessment. Keep the mandatory visual floor separate from
  comparative visual quality, which is a declared frontier dimension. Record
  all eligible passing baselines and their non-dominated frontier, mixed
  trade-offs, visual disagreement, common-pipeline failure, branch-specific
  mandatory failures, budget/readiness breaches, and inadequate evidence as
  required by the strict precedence table; do not force an outcome.
- Register the beneficial direction and paired interaction contrast for every
  criterion, assigning the first state to the contrast without the other
  contribution and the second state to the contrast with it. Use exactly the
  mutually exclusive B/N/H/U matrix: `B/B` independent beneficial, `B/N`
  suppressed to neutral, `B/H` reversed/antagonized, `N/B` synergy-dependent,
  `N/N` no demonstrated effect, `N/H` harmful only with other, `H/B`
  interaction-dependent reversal, `H/N` harm neutralized, `H/H` consistently
  harmful, and any `U` unresolved. Keep `combined-hybrid-only` as a separate
  bundle-level tag, not a component label. Keep interaction diagnostic rather
  than turning it into a scalar or a full-factorial claim.
- Use the normalized sampling, convergence, clipping, semantic-lineage, and
  topology/orientation controls proposed in DR-0010; this record does not
  replace that extraction policy.
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
- [First surface experiment design](../research/first-surface-experiment-design.md)
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

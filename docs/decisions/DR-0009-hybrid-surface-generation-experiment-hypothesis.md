# DR-0009: Hybrid surface-generation experiment hypothesis

ID: DR-0009

Scope: Architecture

Status: Proposed

Revision: 7

Decision owner: Ben

Owner approval: Pending

Review status: Pending

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
exclusive four-state interaction matrix. The Revision 5 [architecture/proof/
governance review](reviews/DR-0009-rev-05-review-01.md) and [geometry/semantics/
measurement review](reviews/DR-0009-rev-05-review-02.md) are Complete and both
recommend `Revise` at High confidence. Their five unresolved findings are
recorded below. Revision 5 remains Proposed with Owner approval Pending;
Review Complete records evidence, not a clean review or acceptance. Revision 6
applies Ben's settled Round 11 resolutions: a frozen common-scaffold
checkpoint followed by one cumulative per-branch
readiness-remediation/implementation budget;
separate bundle comparison and component attribution; mutually exclusive
sufficient-precision B/N/H/U regions; and preorder/acyclic controls for Pareto
frontiers. These are the four choices applied by this revision. The
[architecture/proof/governance review](reviews/DR-0009-rev-06-review-01.md) and
[experiment-design/measurement review](reviews/DR-0009-rev-06-review-02.md)
reviewed Revision 6; both are Complete and recommend `Revise` at High
confidence. Review Complete records evidence, not a clean review or
acceptance. The reviewers describe the prior Revision 5 findings as partly
resolved, but consolidate the remaining actionable issues into exactly these
five unresolved findings:

1. Scaffold provenance and allocation are underdefined for pre-existing,
   branch-favoring, dual-use, and subset-shared operation work, allowing budget
   bypass and inconsistent charging.
2. The interaction-matrix labels assert independence, synergy, and antagonism
   without a common-scale interaction estimand.
3. Criterion/site/fixture B/N/H/U states lack an exhaustive component-level
   aggregation rule.
4. B/N/H/U scientific regions still overlap (small precise directional effects
   can also be neutral-equivalent), visual precision needs a separate rule, and
   supporting “No effect” wording overclaims equivalence.
5. The outcome table lacks an explicit incomplete/abandoned-run disposition
   when not every branch has valid evidence or a terminal state.

Revision 7 applies Ben's settled Round 12 resolutions to all five findings:
layered provenance and effort ledgers; a descriptive conditional-effect matrix;
the complete matrix as the sole component-attribution result; disjoint
quantitative `B/N/H/U` and separate qualitative visual
`B/H/visually-equivalent/U` rules; and an explicit operational run status for
incomplete or abandoned execution. The Revision 6 reviews
remain preserved as historical/stale evidence linked above. Revision 7 is
unreviewed and unaccepted: it remains Proposed, has Owner approval Pending, and
has Review status Pending. EXP-0001 remains unregistered; this revision chooses
no registration values, thresholds, or tooling.

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
demonstrated shared apparatus/common-pipeline/mandatory-oracle failure occurs.
Such a failure remains affected-comparison
`Inconclusive` even if attempts to repair it consume time or effort; it is not
converted into a branch feasibility failure, and the affected fixture,
contrast, or full comparison scope must be identified. Generic missing,
invalid, or otherwise unavailable evidence is handled only after branch
terminal attribution, unless it is independently demonstrated to be this
shared failure.

Before execution, registration must freeze one cumulative readiness-
remediation/implementation budget for each branch and an authoritative
common-scaffold checkpoint. The pre-checkpoint common scaffold contains only
infrastructure and oracles required identically by every branch. Its
provenance, source state, admitted assets, and evidence of branch neutrality
are frozen at the checkpoint, which may not be moved after branch work begins.
Pre-existing branch-specific or subset-specific prototypes are excluded from
the primary comparison. They may be retained as clearly scoped
exploratory/reference evidence, but cannot support primary fairness, effort, or
feasibility claims.

After the checkpoint, every actual work item is assigned exactly once to one
finite `S`, `B`, or `G` capability ledger, or to one branch-specific integration
ledger. No work may be hidden or reclassified as scaffold. The registration
freezes admission and allocation rules, including the treatment of a capability
used by a subset of branches, and freezes each branch's budget, accounting unit
and scope, permitted remediation, checkpoint evidence, and terminal rule. Each
branch's attributed cumulative cost includes the full cost of every capability
ledger it requires plus its own integration ledger, and is checked against its
frozen branch budget. Project-total actual effort counts shared-layer work once;
branch cost views may attribute the same required layer to each consuming
branch, but do not represent that attribution as repeated project work. Actual
and attributed effort are reported separately. This record does not choose
numeric registration values or tooling.

Each branch's budget starts at the frozen checkpoint, before any counted
branch-specific capability, integration, tuning, or remediation work. A
readiness defect therefore consumes an already-running budget; it does not
start a new readiness clock. Exhaustion or failure of a capability ledger is a
branch-specific feasibility failure for every branch that consumes it, not a
universal shared-apparatus `Inconclusive` result. A branch-specific integration
ledger has the same branch-specific disposition. The consuming branches retain
their own terminal facts and attributed costs even when the capability's
actual work was performed once.

While a branch-specific defect remains within its cumulative budget, the
branch is in a remediation/readiness state, not a terminal final outcome. When
that budget is exhausted before the branch reaches readiness or produces
comparable valid evidence, the branch terminates as `Feasibility failure under
the registered implementation and budget`. Terminal attribution is made
before generic evidence-unavailability classification, so generic unavailable
evidence cannot override a branch-specific budget-exhaustion terminal. This
terminal rule prevents endless unreadiness in a registered run. It is a
branch-specific outcome: a hybrid feasibility failure is `Reject`; a baseline
feasibility failure is retained in the record and excludes that baseline from
the eligible frontier. No declared branch is silently removed, and no branch
feasibility failure is a universal-impossibility claim. If baseline failures
leave no eligible baseline, a passing hybrid has only a separate
non-comparative `Feasibility demonstrated` annotation and the comparative
outcome is `Inconclusive`—but only for a `Complete` run.

Run execution status is separate from technology outcome. `In progress` is an
operational status only. A run is `Complete` only when every required
comparison is closed by valid branch evidence, terminal branch states, or an
independently demonstrated registered shared comparison-terminal failure.
Only a `Complete` run calculates `Support`, `Reject`, or comparative
`Inconclusive`, or records a feasibility annotation. An `Incomplete` or
`Abandoned` run retains all partial evidence, provenance, consumed budgets, and
the stopping reason, including any existing branch terminal facts, but produces
no primary technology outcome or feasibility annotation. Existing branch
terminal facts do not by themselves make an incomplete run complete.

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
simplicity partial order, and equivalence/match margins. Each registered
dimension relation must be a preorder suitable for the comparison, and the
aggregate strict-dominance relation must be an acyclic strict partial order.
Incomparability is allowed; no scalarization is invented to force a total
order. A detected cycle, or an eligible set whose Pareto frontier is empty, is
a protocol/evidence failure and makes the affected comparison
`Inconclusive`. These choices are registered controls, not post-hoc judgements
about which implementation looks simple.

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
margins also causes `Reject`. A detected cycle or eligible-but-empty frontier
cannot be treated as a conclusive non-inferiority, match, or dominance result;
it follows the affected-comparison `Inconclusive` disposition above.

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

The following bundle predicates are mutually exclusive. They are applied in
row order, and a later row is considered only when no earlier predicate is
true. Independently demonstrated shared apparatus/common-pipeline or
mandatory-oracle failure is distinct from generic evidence unavailability.
Branch terminal attribution is evaluated before generic evidence
unavailability, so branch-specific budget exhaustion cannot be reclassified
as the generic `Inconclusive` row. Rows that require a conclusive match or
dominance include the complete-resolved-evidence condition above; unresolved
evidence affecting that relation therefore reaches the final `Inconclusive`
row rather than both a `Reject` and an `Inconclusive` row. These predicates are
evaluated only for a `Complete` run. The operational disposition for an
`Incomplete` or `Abandoned` run is included explicitly below and is not a
technology outcome.

| Predicate, in precedence order | Primary outcome |
| --- | --- |
| Run status is `Incomplete` or `Abandoned` because not every required comparison is closed | No primary technology outcome or feasibility annotation; retain partial evidence, provenance, consumed budgets, stopping reason, and existing branch terminal facts |
| An independently demonstrated shared apparatus/common-pipeline/mandatory-oracle failure affects the comparison | `Inconclusive` for the affected comparison |
| The hybrid reaches the branch terminal `Feasibility failure under the registered implementation and budget` | `Reject` |
| The hybrid has valid evidence and passes mandatory gates, but all declared baseline validity, mandatory, technology, and feasibility checks leave no eligible passing baseline | Comparative `Inconclusive`; only a separate non-comparative `Feasibility demonstrated` annotation may be recorded for the passing hybrid |
| The hybrid has valid evidence and violates a mandatory gate, has a mandatory regression, or lacks the named improvement | `Reject` |
| A registered dimension relation contains a detected cycle, or eligible passing baselines exist but the registered Pareto frontier is empty | `Inconclusive` for the affected comparison |
| At least one eligible passing frontier baseline conclusively dominates the hybrid on every applicable registered dimension and is better on at least one | `Reject`, regardless of simplicity |
| No frontier baseline conclusively dominates the hybrid, and a conclusively simpler eligible baseline matches the hybrid within all frozen equivalence margins | `Reject` |
| At least one eligible passing frontier baseline exists; the hybrid passes all mandatory gates, shows the named improvement, meets frozen non-inferiority conditions against every frontier baseline, has no conclusive frontier dominance or simpler match, and has no unresolved declared trade-off | `Support` |
| At least one eligible passing baseline exists, but generic evidence affecting a conclusive dominance or match determination, or attribution, is unresolved, or a nonmandatory trade-off/comparative visual disagreement remains unresolved after the registered protocol | `Inconclusive` |

Baseline feasibility or technology failures can therefore remove a baseline
from eligibility without removing its record. If one or more eligible
baselines remain, the remaining predicates decide the comparison. An empty
frontier with eligible baselines is a protocol/evidence failure and is
comparative `Inconclusive`; it cannot produce `Support`. A passing hybrid with
no eligible baseline receives only the separate feasibility annotation
described above. A hybrid terminal failure or mandatory failure cannot be
rescued by an empty frontier.
The Stage 1 all-valid-fixtures gate and the separate subjective visual-floor
method remain owned by
[DR-0007](DR-0007-staged-first-proof-charter.md) and the
[visual-quality protocol](../research/visual-quality-evaluation.md).

The table's `Support`/`Reject`/`Inconclusive` result is the primary
comparative outcome of the full hybrid bundle against the eligible baseline
frontier. It is separate from component attribution. For each selected
component (blending and reusable specialized generators), the complete
per-fixture/site/criterion conditional-effect matrix from the required paired
contrasts below is the component-attribution result. There is no collapsed
component-level `Supported`, `Not supported`, or `Harmful` category and no
unconstrained attribution aggregation. Optional coverage counts may be
reported only as preregistered descriptive information; they cannot become a
decisive scalar or a selective-credit rule. Bundle outcome remains separate
and never implies component credit. `combined-hybrid-only` remains a separate
bundle-level tag when the combined comparison supports the named improvement
without asserting why or assigning independent component credit.

### Attribution and fairness contract

**Recommendation: Option 2 — five bounded branches with a branch-neutral
fairness and readiness contract.** EXP-0001 uses bounded nested ablation, not
a full factorial sweep. Every branch receives the
same frozen semantic source intent, shared semantic feature vocabulary,
fixture identity, input mapping, bounds and sampling policy, seed/configuration
policy, diagnostics, and common output interface. The experiment must freeze
a branch-operation matrix, allowed construction operations, parameter and
tuning budgets, one cumulative per-branch readiness-remediation/implementation
budget, an authoritative common-scaffold checkpoint, and implementation-effort
accounting before execution. The accounting has separate provenance, actual-
effort, attributed-effort, capability, and branch-integration ledgers. Baselines
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

The checkpoint is a provenance boundary. Its common-scaffold ledger admits
only infrastructure and oracles required identically by every branch. The
registration freezes the scaffold's provenance, source state, admitted assets,
and evidence that each admitted item is branch-neutral. Pre-existing
branch-specific or subset-specific prototypes are excluded from the primary
comparison. They may be retained as clearly scoped exploratory/reference
evidence, but cannot support primary fairness, effort, or feasibility claims.

After the checkpoint, every actual work item is assigned exactly once to a
finite capability ledger or a branch-specific integration ledger. The finite
capability ledgers are `S` for skeleton/swept-profile capability, `B` for the
selected blending capability, and `G` for the reusable specialized-generator
capability. A capability ledger may be consumed by a subset of branches, but
it is not common scaffold and its consuming branch set and allocation rule are
frozen before execution. A branch-specific integration ledger records the
assembly, adaptation, and integration work unique to that branch. No work may
be hidden or reclassified as scaffold, and no work item may be charged to more
than one ledger. The registration freezes these admission and allocation rules
and the consuming branch set for each capability ledger.

Each branch's attributed cumulative cost includes the full cost of every
capability ledger it requires plus its own integration ledger, and is checked
against its frozen branch budget. Project-total actual effort counts work in a
shared capability ledger once. Branch cost views may attribute that same
required capability layer to each consuming branch for feasibility and branch
budget checks, but do not represent the attribution as repeated project work.
Actual and attributed effort are reported separately. Exhaustion or failure of
a capability ledger affects every consuming branch as a branch-specific
feasibility failure; it is not universal shared-apparatus `Inconclusive`.

The matrix classifies branches by allowed construction operation, not by
whether an implementation stores an intermediate scalar field. A branch may
use an internal field when its construction rule permits it. Before branch
tuning, registration must freeze the shared infrastructure and oracles, the
authoritative common-scaffold checkpoint, branch definitions and operation
matrix, adjustable parameter domains, common objective, deterministic
initialization, stopping rule, and parameter, evaluation, and implementation-
effort budgets and the provenance/effort ledger rules. It must also freeze the
output fields, exact selected blend sites, and generator operation set; those
values are deliberately not invented by this record. A reusable generator
remains a grammar capability, not a hidden per-fixture mesh, topology, or rig
correction. This bounded nested ablation supports attribution of the selected
blending and specialized-generator layers through the complete conditional-
effect matrix; it does not estimate interaction magnitude or claim a full
factorial result.

Each branch has a separate configuration and workspace. Branches use the same
deterministic search and evaluation budget; for human adjustment rounds, a
preregistered rotating or counterbalanced order may be used instead. The
registration must state which rule applies. Adjustments are global branch
parameters only: no fixture-specific tuning, post-hoc correction, or
per-fixture parameter is allowed in primary comparison. Branch-specific
parameters, corrections, and defect fixes must not be transferred between
branches during primary evidence collection. Shared-scaffold fixes apply to
every affected branch and require rerunning all affected evidence. Capability-
ledger fixes affect every consuming branch and are charged through each
consumer's attributed cost. Unavoidable knowledge reuse is logged, and shared
versus branch-specific implementation, tuning, and adjustment effort is
reported as actual and attributed effort separately.

Before primary comparison, each required branch must pass branch-neutral
analytical readiness fixtures, exercise every required operation in its
declared matrix, and disclose unresolved implementation or fidelity defects.
The fixtures and oracles must be independent of branch-specific visual
success. The common-scaffold checkpoint is frozen before any branch-specific
implementation, tuning, or remediation counted by the experiment. A branch's
one cumulative registered budget is already running at that checkpoint, so a
readiness defect consumes it rather than starting it. Every capability and
integration work item is allocated once under the ledgers above, and its full
required capability cost is included in each consuming branch's attributed
budget view. While budget remains,
the defect is a remediation/readiness state, not a terminal final outcome. If
the branch still cannot reach readiness or produce comparable valid evidence
when that cumulative budget is exhausted, the branch terminates as
`Feasibility failure under the registered implementation and budget`. A hybrid
terminal failure is `Reject`; a baseline terminal failure is retained and
excluded from the frontier. A capability-ledger or branch-integration failure
is branch-specific for every consuming branch. Only an independently
demonstrated shared apparatus, mandatory oracle, or common-pipeline defect
remains affected-comparison `Inconclusive` and is not charged as a branch
terminal failure. Generic evidence unavailability cannot override
branch-specific budget exhaustion.
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
contrasts. For each component, fixture, site, and criterion, classify the
first state from the contrast **without the other contribution** and the
second state from the contrast **with the other contribution**.

For each quantitative criterion, registration freezes the estimand, practical-
equivalence margin `±delta`, uncertainty interval and method, replication,
adjudication, multiplicity, validity requirements, and boundary handling. With
a valid uncertainty interval, `B` applies iff the full interval lies beyond
`+delta`; `H` applies iff the full interval lies below `-delta`; and `N`
applies iff the full interval is contained in `[-delta,+delta]`. `U` applies
otherwise or when evidence is invalid or unavailable. These rules are
mutually exclusive and exhaustive under the frozen boundary convention.

Subjective visual criteria use a separately preregistered qualitative
adjudication: resolved beneficial, resolved harmful, visually equivalent
within the frozen rubric, or `U` for disagreement, insufficient evidence,
invalid evidence, or unavailable evidence. This visual rule does not claim
statistical precision. Reports use “neutral equivalence within the frozen
margin/rubric”; they do not use “no effect” as a synonym for `N`.

The complete per-fixture/site/criterion conditional-effect matrix is a
descriptive pattern ledger, not an interaction estimand. Its literal cells
are:

| First state (without other); second state (with other) | `B` | `N` | `H` | `U` |
| --- | --- | --- | --- | --- |
| `B` | Beneficial both contexts | Beneficial without, neutral with | Beneficial without, harmful with | Unresolved |
| `N` | Neutral without, beneficial with | Neutral both | Neutral without, harmful with | Unresolved |
| `H` | Harmful without, beneficial with | Harmful without, neutral with | Harmful both | Unresolved |
| `U` | Unresolved | Unresolved | Unresolved | Unresolved |

Any `U` state is unresolved. The matrix records conditional-effect patterns
only; its sign patterns do not establish independence, synergy, antagonism,
suppression, reversal, or interaction magnitude. `combined-hybrid-only` is a
separate bundle-level tag when the combined comparison supports the named
improvement without component credit or a claim about why. It is not a
component matrix label.

## Consequences

- Stage 1 can test semantic control and organic junction quality together while
  retaining baselines that can disprove the combined hypothesis.
- The evidence-first precedence makes support, rejection, and inconclusive
  outcomes inspectable before evidence exists; it does not turn a mixed
  trade-off into a fabricated scalar score or allow endless unreadiness. The
  common-scaffold checkpoint and one cumulative per-branch budget make
  branch-specific implementation, tuning, and remediation finite from the
  start of counted branch work. Layered ledgers freeze provenance and allocate
  every post-checkpoint work item exactly once; capability-ledger failure is
  branch-specific for every consuming branch. Shared apparatus/common-pipeline
  or mandatory-oracle failure remains affected-comparison `Inconclusive`, and
  branch-specific budget exhaustion cannot be overridden by generic evidence
  unavailability. An empty eligible-baseline frontier is comparative
  `Inconclusive`, even when a passing hybrid receives a separate feasibility
  annotation in a `Complete` run. An `Incomplete` or `Abandoned` run produces
  no technology outcome or feasibility annotation.
- The five branches expose the two selected hybrid contributions while keeping
  the comparison bounded. The cumulative readiness-remediation/implementation,
  complexity, tuning, and effort budgets remain part of the interpretation
  rather than hidden or unbounded costs. Actual project effort and attributed
  branch effort are reported separately.
- Specialized generators add grammar vocabulary and reusable capabilities;
  they do not license bespoke fixture patches or silently expand the supported
  morphology envelope.
- The hybrid branch has more moving parts and more diagnostic surface than a
  single representation. The experiment must therefore report the primary
  bundle outcome separately from the complete per-fixture/site/criterion
  conditional-effect matrix for each component and show where a branch
  failed. There is no collapsed component outcome or unconstrained aggregation;
  optional coverage counts are descriptive only and cannot selectively credit
  a component. Bundle outcome never implies component credit. The literal
  B/N/H/U cells are mutually exclusive conditional-effect patterns, and
  `combined-hybrid-only` remains a separate bundle-level diagnostic tag. The
  matrix is not an interaction estimand or scalar interaction score.
- A successful surface experiment would support only the stated Stage 1 claim
  under its fixtures and protocol. It would not settle production topology,
  animation deformation, runtime representation, backend, or performance.
- A failed or inconclusive hybrid result must remain visible and may support a
  different hypothesis, a narrower proof, or a revised decision; it must not be
  converted into an unrecorded implementation exception. A hybrid feasibility
  failure is `Reject`; a baseline feasibility failure remains visible but
  excludes that baseline from the frontier, without a universal-impossibility
  claim or silent removal. Registered dimension preorders and an acyclic
  aggregate strict partial order preserve an interpretable frontier; a cycle
  or eligible-but-empty frontier is affected-comparison `Inconclusive`.

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
improvement could come from blending, specialized generators, their conditional
patterns, or an unequal baseline budget. It is not selected as the sole
record because the settled protocol keeps the complete conditional-effect
matrix separate from the primary bundle outcome. A bundle may still receive
comparative `Support` when its predicates pass, but it must carry
`combined-hybrid-only` rather than imply component credit or explain why the
bundle improved.

#### Option 2: Five-branch bounded nested ablation

This option adds the two one-layer branches to the two simpler baselines and
the full hybrid. It preserves a common semantic vocabulary and operation
budget, layered provenance and effort ledgers, a frozen common-scaffold
checkpoint, one cumulative per-branch readiness-remediation/implementation
budget, and an operation matrix while directly testing each selected layer's
incremental contribution. A branch that cannot reach readiness or comparable
evidence within its registered budget terminates as a branch feasibility
failure; it is not left in an endless `Inconclusive` state. The primary bundle
outcome and each component's complete conditional-effect matrix are reported
separately. It does not test every possible parameter combination, but it
provides the bounded attribution needed for this Stage 1 hypothesis.
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
rule freezes an authoritative common-scaffold checkpoint and one cumulative
per-branch readiness-remediation/implementation budget that is already running
before branch-specific implementation, tuning, or remediation counted by the
experiment. Branch exhaustion is `Feasibility failure under the registered
implementation and budget`, while independently demonstrated shared
apparatus/common-pipeline or mandatory-oracle failure remains affected-
comparison `Inconclusive`; generic evidence unavailability cannot override
the terminal attribution.

#### Outcome-predicate alternative: partial frontier or overlapping rows

The experiment could compare one preferred baseline, treat only simpler
baselines as relevant, or permit unresolved dimensions to coexist with a
conclusive match/trade-off row. That would leave dominance incomplete and
make outcome rows overlap. It is not selected. Registration instead freezes
all applicable dimensions, their aggregation and thresholds, the Pareto
relation, a simplicity partial order, and match margins. Each dimension
relation must be a suitable preorder and aggregate strict dominance an acyclic
strict partial order; incomparability remains allowed and no scalarization is
invented. Conclusive match and dominance require resolved evidence across
every applicable dimension; any frontier baseline conclusively dominating the
hybrid rejects regardless of simplicity, and a simpler baseline conclusively
matching within the margins also rejects. A detected cycle or eligible-but-
empty frontier is affected-comparison `Inconclusive`.

#### Conditional-effect alternative: scalar or full-factorial estimand

A common-scale interaction estimand or an exhaustive factorial sweep could
summarize more than the bounded contrasts, but it would add measurement,
multiple-comparison, and search obligations before the first surface proof is
understood. It is not selected. The paired contrasts instead use the exact,
mutually exclusive quantitative `B/N/H/U` and separate qualitative visual
`B/H/visually-equivalent/U` rules. Their complete per-fixture/site/criterion
matrix is a descriptive conditional-effect pattern ledger, not an interaction
estimand or scalar score. `combined-hybrid-only` is retained as a separate
bundle-level tag without claiming why the bundle improved.

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

The [architecture/proof/governance review](reviews/DR-0009-rev-05-review-01.md)
and [geometry/semantics/measurement review](reviews/DR-0009-rev-05-review-02.md)
reviewed Revision 5; both are Complete, recommend `Revise` at High confidence,
and are preserved as historical/stale evidence for Revision 6. Revision 6
applied Ben's four settled choices to those earlier findings: findings 1 and 3
by the common-scaffold checkpoint, one cumulative already-running per-branch
budget, and terminal attribution before generic evidence unavailability while
retaining independently demonstrated shared failure as affected-comparison
`Inconclusive`; finding 2 by separating bundle comparison from component
attribution; finding 4 by requiring sufficient-precision equivalence within the
frozen neutral margin for `N`; and finding 5 by requiring dimension preorders,
an acyclic aggregate strict partial order, and an affected-comparison
`Inconclusive` disposition for cycles or eligible-but-empty frontiers. Their
five findings were exactly:

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

The Revision 6 reviewers assess prior findings 3, 4, and 5 as resolved,
finding 2's boundary as resolved but its aggregation gap as remaining, and
finding 1 as incomplete because subset-shared allocation is still underdefined.
Their remaining overlap is consolidated into the five actionable findings
recorded above. Revision 7 addresses them as follows:

1. The layered provenance/effort-ledger contract restricts the pre-checkpoint
   scaffold to infrastructure and oracles required identically by every
   branch, freezes provenance, source state, admitted assets, and neutrality
   evidence, excludes branch-specific/subset-specific prototypes from primary
   claims, and allocates every post-checkpoint work item exactly once to an
   `S`, `B`, `G`, or branch-integration ledger. Full required capability costs
   are included in each consuming branch's attributed budget, while project
   actual effort counts shared work once and actual versus attributed effort
   are reported separately. Capability-ledger exhaustion is branch-specific
   feasibility failure for every consumer, not universal shared-apparatus
   `Inconclusive`.
2. The conditional-effect matrix uses literal descriptive cells (`B/B`
   beneficial both contexts; `B/N` beneficial without, neutral with; `B/H`
   beneficial without, harmful with; `N/B` neutral without, beneficial with;
   `N/N` neutral both; `N/H` neutral without, harmful with; `H/B` harmful
   without, beneficial with; `H/N` harmful without, neutral with; `H/H`
   harmful both; any `U` unresolved). It is a conditional-effect pattern
   ledger, not an interaction estimand, and does not assert independence,
   synergy, antagonism, suppression, reversal, or interaction magnitude.
3. The complete per-fixture/site/criterion matrix is the component-attribution
   result. A collapsed component outcome and unconstrained aggregation are
   removed. Optional coverage counts are descriptive only, preregistered, and
   cannot become a decisive scalar or selective-credit rule. Bundle outcome
   remains separate and never implies component credit.
4. Quantitative criteria freeze the estimand, `±delta` practical-equivalence
   margin, uncertainty interval/method, replication, adjudication,
   multiplicity, validity, and boundary handling. `B`, `H`, `N`, and `U` are
   mutually exclusive and exhaustive under the full-interval rules. Subjective
   visual criteria use a separate qualitative adjudication for beneficial,
   harmful, visual equivalence within the frozen rubric, or `U`; reports say
   “neutral equivalence within the frozen margin/rubric,” not “no effect.”
5. Operational run status is separate from technology outcome: only a
   `Complete` run with every required comparison closed by valid evidence,
   terminal branch states, or a registered shared comparison-terminal failure
   calculates `Support`, `Reject`, `Inconclusive`, or a feasibility annotation.
   `Incomplete` and `Abandoned` runs retain partial evidence, provenance,
   consumed budgets, stopping reason, and branch terminal facts but produce no
   primary technology outcome or feasibility annotation.

The [architecture/proof/governance review](reviews/DR-0009-rev-06-review-01.md)
and [experiment-design/measurement review](reviews/DR-0009-rev-06-review-02.md)
are Complete, recommend `Revise` at High confidence, and are preserved as
historical/stale evidence for Revision 7. Revision 7 is Proposed, has Owner
approval Pending, and has Review status Pending; it is unreviewed and
unaccepted. Review status Pending records that no current-revision review or
acceptance has occurred.

## Implementation and Proof Obligations

- Design (but do not register or create) EXP-0001 to compare all five branches
  in the frozen operation matrix, with the same semantic source intent,
  feature vocabulary, fixture identities, input mapping, common output
  interface, diagnostics, and capture protocol.
- Track execution status separately from technology outcome. `In progress` is
  operational only. Mark a run `Complete` only when every required comparison
  is closed by valid branch evidence, terminal branch states, or an
  independently demonstrated registered shared comparison-terminal failure.
  Only a `Complete` run may calculate `Support`, `Reject`, comparative
  `Inconclusive`, or a feasibility annotation. Preserve all partial evidence,
  provenance, consumed budgets, stopping reason, and existing branch terminal
  facts for `Incomplete` or `Abandoned` runs, but produce no primary technology
  outcome or feasibility annotation.
- Freeze the comparative decision rule, named junction/feature criteria,
  eligible-frontier dimensions, branch operations, branch-neutral readiness
  fixtures, required-operation coverage, unresolved-defect disclosures,
  common objective, global initialization and tuning protocol, parameter/
  tuning budgets, one cumulative per-branch readiness-remediation/
  implementation budget, an authoritative common-scaffold checkpoint,
  implementation-effort accounting, provenance and ledger allocation rules,
  exact aggregation and threshold rules, and the terminal rule before
  execution or evidence interpretation. Restrict the pre-checkpoint scaffold
  to infrastructure and oracles required identically by every branch; freeze
  its provenance, source state, admitted assets, and branch-neutrality
  evidence. Exclude pre-existing branch-specific and subset-specific
  prototypes from primary claims. After the checkpoint assign every actual
  work item exactly once to an `S`, `B`, `G`, or branch-specific integration
  ledger. Include each required capability ledger's full cost plus the branch
  integration ledger in that branch's cumulative attributed budget; count
  shared capability work once in project actual effort and report actual and
  attributed effort separately. The cumulative budget starts at the frozen
  checkpoint, before any counted branch-specific capability, integration,
  tuning, or remediation. Do not allow an exhausted branch or capability
  ledger to remain indefinitely unready.
- Preserve the shared-failure distinction: an independently demonstrated
  shared apparatus/common-pipeline or mandatory-oracle failure remains
  affected-comparison `Inconclusive`; a branch-specific inability to reach
  readiness or comparable evidence within its cumulative budget is
  `Feasibility failure under the registered implementation and budget`. A
  capability-ledger or branch-integration failure has that branch-specific
  disposition for every consuming branch. A branch-specific defect while
  budget remains is a remediation/readiness state, not a terminal final
  outcome. Attribute branch terminal failure before generic evidence
  unavailability, so the latter cannot override exhaustion. Apply `Reject` to
  a hybrid terminal failure; retain and exclude a baseline terminal failure;
  never make a universal-impossibility claim or silently remove a branch.
- Freeze the applicability, direction, aggregation, and thresholds of every
  registered comparison dimension; the Pareto dominance relation; the
  simplicity partial order; and equivalence/match margins. Require valid,
  resolved evidence across every applicable dimension before declaring any
  match or dominance. Treat unresolved evidence affecting that determination
  as `Inconclusive`; check every frontier baseline for conclusive dominance,
  regardless of simplicity, and every simpler eligible baseline for a
  conclusive match. Require registered dimension relations to be suitable
  preorders and aggregate strict dominance to be an acyclic strict partial
  order; allow incomparability without scalarization. Treat a detected cycle
  or eligible-but-empty frontier as affected-comparison `Inconclusive`.
- Freeze shared infrastructure and mandatory oracles, branch definitions,
  operation matrices, adjustable parameter domains, initialization, stopping
  rule, and deterministic search/evaluation budget before branch tuning. Keep
  branch configurations and workspaces separate; use the same budget or a
  preregistered rotating/counterbalanced human-adjustment order. Prohibit
  transfer of branch-specific parameters, corrections, or defect fixes during
  primary evidence collection. Apply common-scaffold fixes to all affected
  branches and rerun affected evidence. Apply capability-ledger fixes to every
  consuming branch and charge them through each consumer's attributed cost;
  log unavoidable shared and branch-specific knowledge and effort as actual
  and attributed effort separately.
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
- For every quantitative criterion, preregister the estimand, practical-
  equivalence margin `±delta`, uncertainty interval and method, replication,
  adjudication, multiplicity, validity, and boundary handling. Assign `B`
  only when the full valid interval lies beyond `+delta`, `H` only when it lies
  below `-delta`, `N` only when it is contained in `[-delta,+delta]`, and `U`
  otherwise or when evidence is invalid or unavailable. Keep these states
  mutually exclusive and exhaustive. For subjective visual criteria, use a
  separate qualitative adjudication for resolved beneficial, harmful, visually
  equivalent within the frozen rubric, or `U` for disagreement, insufficiency,
  invalidity, or unavailability; do not claim statistical precision. Use
  “neutral equivalence within the frozen margin/rubric,” never “no effect.”
- Report the primary bundle comparative outcome separately from the complete
  per-fixture/site/criterion conditional-effect matrix for each component.
  That complete matrix is the component-attribution result; do not create a
  collapsed component outcome or unconstrained aggregation. Optional coverage
  counts are descriptive only, preregistered, and cannot become a decisive
  scalar or selective-credit rule. Bundle outcome never implies component
  credit; retain `combined-hybrid-only` as a separate bundle tag.
- Register the beneficial direction and paired conditional-effect contrast for
  every criterion, assigning the first state to the contrast without the other
  contribution and the second state to the contrast with it. Use the literal
  descriptive matrix: `B/B` beneficial both contexts; `B/N` beneficial without,
  neutral with; `B/H` beneficial without, harmful with; `N/B` neutral without,
  beneficial with; `N/N` neutral both; `N/H` neutral without, harmful with;
  `H/B` harmful without, beneficial with; `H/N` harmful without, neutral with;
  `H/H` harmful both; and any `U` unresolved. The matrix is a conditional-
  effect pattern ledger, not an interaction estimand, and does not establish
  independence, synergy, antagonism, suppression, reversal, or interaction
  magnitude. Keep `combined-hybrid-only` as a separate bundle-level tag, not a
  component label or explanation.
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

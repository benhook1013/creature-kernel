# DR-0009: Hybrid surface-generation experiment hypothesis

ID: DR-0009

Scope: Architecture

Status: Proposed

Revision: 8

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
resolved, but record the following five Revision 6 unresolved findings as
historical review evidence:

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

Revision 7 applied Ben's settled Round 12 resolutions to all five findings:
layered provenance and effort ledgers; a descriptive conditional-effect matrix;
the complete matrix as the sole component-attribution result; disjoint
quantitative `B/N/H/U` and separate qualitative visual
`B/H/visually-equivalent/U` rules; and an explicit operational run status for
incomplete or abandoned execution. The Revision 6 reviews remain preserved as
historical/stale evidence linked above. The [architecture/proof/governance
review](reviews/DR-0009-rev-07-review-01.md) and
[experiment-design/measurement review](reviews/DR-0009-rev-07-review-02.md)
reviewed Revision 7; both are Complete and recommend `Revise` at High
confidence. Review Complete records evidence, not a clean review or
acceptance. The current review consolidates exactly these five unresolved
actionable findings:

1. Accounting taxonomy/scaffold scope remains incomplete: the general implicit
   baseline and post-checkpoint universal repairs lack finite ledgers, while
   scaffold neutrality/benefit/effort and feasibility-annotation scope are
   underdefined.
2. Visual evidence and matrix schema are incomplete: reviewer independence,
   presentation, and adjudication are underconstrained; visual equivalence
   has no explicit neutral mapping; absent/inapplicable cells lack `NA`.
3. `combined-hybrid-only` has contradictory, non-testable definitions.
4. New run-execution terms conflict with the canonical experiment lifecycle
   vocabulary.
5. Generic unresolved `attribution` is ambiguous between branch/failure
   attribution and component-matrix `U`.

Revision 7 remained Proposed, had Owner approval Pending, and had Review status
Complete. Its two reviews remain preserved historical evidence and are stale for
Revision 8. Revision 8 applies Ben's five settled resolutions to the Revision 7
findings: a closed `C`/`I`/`S`/`B`/`G` plus per-branch integration accounting
taxonomy with finite ledgers and operational scaffold admission; one generic
`B/N/H/U` matrix with modality-specific quantitative and comparative-visual
rules, preregistered applicability, separate `NA`, and a three-reviewer visual
panel; removal of the former `combined-hybrid-only` tag from current language;
orthogonal lifecycle, evidence-closure, and technology-outcome fields; and
explicit `branch/failure attribution` in the outcome table, with component
matrix `U` cells remaining visible evidence that do not by themselves block a
bundle `Support` result. The Revision 7 reviews are linked above, remain stale,
and their five findings plus exact resolutions are recorded in the adversarial
review response below. Revision 8 is unreviewed and unaccepted: it remains
Proposed with Owner approval Pending and Review status Pending. EXP-0001
remains unregistered; this revision chooses no stack, numeric fixture/grid,
artifact, registration, threshold, or tooling values.

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
comparison is affected, and therefore `inconclusive`, when an independently
demonstrated shared apparatus/common-pipeline/mandatory-oracle failure occurs.
Such a failure remains affected-comparison
`inconclusive` even if attempts to repair it consume time or effort; it is not
converted into a branch feasibility failure, and the affected fixture,
contrast, or full comparison scope must be identified. Generic missing,
invalid, or otherwise unavailable evidence is handled only after branch
terminal attribution, unless it is independently demonstrated to be this
shared failure.

Before execution, registration must freeze one cumulative readiness-
remediation/implementation budget for each branch and an authoritative
common-scaffold checkpoint. The actual-work accounting taxonomy is closed:
exactly one finite `C` ledger for the universal common scaffold and shared
repairs, one `I` ledger for general implicit-baseline capability, one `S`
ledger for skeleton/swept-profile capability, one `B` ledger for blending, one
`G` ledger for specialized generators, and one integration ledger for each
branch. No other actual-work ledger or unassigned work category is permitted.

An initial scaffold item may enter `C` only when it is required by every
branch, exposes the same interface/data/access to every branch, has no branch-
construction-specific implementation or parameters, and is admitted before
branch construction work begins. This is an operational neutrality test, not
a claim of equal benefit to every branch. Registration freezes the immutable
base C scaffold manifest, provenance, source state, admitted assets, known
effort, cap, consumers (all branches), branch attribution, exhaustion rule,
and disposition. `C` is finite. A universal repair made after the checkpoint
may enter C only when it passes the same universal-need, identical-interface/
data/access, and no-branch-construction-specific-implementation-or-parameters
conditions; the initial timing condition does not apply to a repair. It becomes
an append-only C repair-log entry, consumes the finite C cap, applies to every
affected branch, and requires rerunning affected evidence. Pre-existing
branch-specific or subset-specific prototypes are excluded from the primary
comparison. They may be retained as clearly scoped exploratory/reference
evidence, but cannot support primary fairness, effort, or feasibility claims.

Every actual work item belongs exactly once to `C`, `I`, `S`, `B`, `G`, or the
single integration ledger of its branch. `I` is consumed only by the general
implicit baseline; `S`, `B`, and `G` have the consumers declared in the branch
matrix below. The registration freezes each ledger's consumers, manifest and
provenance, source state and admitted assets, known effort, cap, attribution,
exhaustion rule, and disposition, as well as each branch's budget, accounting
unit and scope, permitted remediation, checkpoint evidence, and terminal rule.
No work may be hidden, charged twice, or reclassified after admission. Unknown
historical effort is recorded explicitly as unavailable, never as zero.

Project actual effort counts each work item once, including the full actual C
effort. Branch attributed cost views report the required C attribution and the
required `I`/`S`/`B`/`G` capability and branch-integration costs separately; a
repeated branch attribution is not repeated project work. Each branch's
incremental attributed budget starts from the immutable base C scaffold
manifest and the exact repair-log snapshot, then includes the
post-checkpoint capability and integration work required by that branch. The
feasibility annotation, when permitted, is scoped exactly to incremental
feasibility from that base-plus-snapshot state under the attributed branch
budget ID. Full C effort is reported separately from that annotation and
budget; it is never silently omitted. This record does not choose numeric
registration values or tooling.

Each branch's budget is already running at the frozen checkpoint, before any
counted branch-specific capability, integration, tuning, or remediation work.
A readiness defect therefore consumes that budget rather than starting a new
readiness clock. Exhaustion or failure of `I`, `S`, `B`, or `G` affects every
consuming branch as a branch-specific feasibility failure; exhaustion or
failure of a branch integration ledger has that same branch-specific
disposition. Exhaustion or failure of the registered finite `C` ledger is a
shared comparison-terminal failure and therefore `inconclusive` for every
affected comparative scope. The consuming branches retain their terminal facts
and attributed costs even when capability work was performed once.

While a branch-specific defect remains within its cumulative budget, the
branch is in a remediation/readiness state, not a terminal final outcome. When
that budget is exhausted before the branch reaches readiness or produces
comparable valid evidence, the branch terminates as `Feasibility failure under
the registered implementation and budget`. Terminal attribution is made
before generic evidence-unavailability classification, so generic unavailable
evidence cannot override a branch-specific budget-exhaustion terminal. This
terminal rule prevents endless unreadiness in a registered run. It is a
branch-specific outcome: a hybrid feasibility failure is `reject`; a baseline
feasibility failure is retained in the record and excludes that baseline from
the eligible frontier. No declared branch is silently removed, and no branch
feasibility failure is a universal-impossibility claim. If baseline failures
leave no eligible baseline, a passing hybrid has only a separate
non-comparative `Feasibility demonstrated` annotation and the comparative
outcome is `inconclusive`—but only when evidence closure is `complete`.

Experiment lifecycle, evidence closure, and technology outcome are orthogonal
fields. The lifecycle is exactly `planned`, `running`, `finished`, or
`abandoned`; evidence closure is exactly `open`, `complete`, or `incomplete`;
and technology outcome is exactly `none`, `support`, `reject`, or
`inconclusive`. `planned` and `running` require `open` and `none`. A
`finished` run with `complete` closure may calculate the technology outcome or
the feasibility annotation. Execution that ends without closure is recorded as
`finished` or `abandoned` with `incomplete` closure and `none` outcome;
`abandoned` must always be `incomplete`/`none`. Only `complete` closure
calculates an outcome or feasibility annotation. `inconclusive` is a
technology outcome, never a lifecycle state. Partial evidence, provenance,
consumed budgets, branch terminal facts, and the stopping reason are retained
for every `incomplete` or `abandoned` execution.

After shared apparatus/oracle validity and the branch terminal checks, a valid
registered measurement that violates a frozen mandatory clearance,
convergence, phase/topology, feasibility, budget, or other mandatory
criterion is that branch's mandatory technology failure. A hybrid mandatory
failure, including a missing named improvement, is `reject`. A baseline-only
mandatory failure is retained and excludes that baseline from the eligible
frontier; it does not remove the declared branch from the experiment. A valid
measurement whose branch/failure attribution remains genuinely indeterminate is
`inconclusive`.

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
`inconclusive`. These choices are registered controls, not post-hoc judgements
about which implementation looks simple.

A conclusive match or dominance determination requires valid, resolved
evidence for every applicable registered dimension. Missing, invalid,
unavailable, ambiguous, or otherwise unresolved evidence that could affect
that determination makes the affected comparison `inconclusive`; it cannot be
treated as a conclusive non-inferiority, match, or dominance result. A frontier
baseline conclusively dominates the hybrid when it is no worse on every
applicable dimension and better on at least one under the frozen relation. A
baseline conclusively matches the hybrid when all applicable dimensions are
resolved and every dimension is within its frozen equivalence margin. A
baseline is conclusively simpler only when the frozen simplicity partial order
places it strictly below the hybrid. Any frontier baseline that conclusively
dominates the hybrid causes `reject`, regardless of whether it is simpler. A
conclusively simpler eligible baseline matching within the frozen equivalence
margins also causes `reject`. A detected cycle or eligible-but-empty frontier
cannot be treated as a conclusive non-inferiority, match, or dominance result;
it follows the affected-comparison `inconclusive` disposition above.

For outcome precedence, mandatory criteria are frozen pass/fail gates and
frozen non-inferiority bounds, including the mandatory visual floor. A
mandatory regression violates one of those criteria or bounds and has
precedence over all trade-off interpretations, so it is `reject` for a valid
hybrid result. A nonmandatory regression is a valid worse result that does not
violate a mandatory gate or frozen non-inferiority bound. It may be recorded
as a resolved, predeclared trade-off; if the trade-off or its visual
interpretation remains unresolved, the result is `inconclusive`. Comparative
visual disagreement is unresolved unless the registered visual protocol
resolves it. These definitions keep mandatory failure, branch feasibility
failure, nonmandatory trade-off, and invalid evidence distinct.

The following bundle predicates are mutually exclusive. They are applied in
row order, and a later row is considered only when no earlier predicate is
true. Independently demonstrated shared apparatus/common-pipeline or
mandatory-oracle failure is distinct from generic evidence unavailability.
Branch terminal attribution is evaluated before generic evidence
unavailability, so branch-specific budget exhaustion cannot be reclassified
as the generic `inconclusive` row. Rows that require a conclusive match or
dominance include the complete-resolved-evidence condition above; unresolved
evidence affecting that relation therefore reaches the final `inconclusive`
row rather than both a `reject` and an `inconclusive` row. These predicates are
evaluated only when the lifecycle is `finished` and evidence closure is
`complete`. `planned`/`running` open evidence has technology outcome `none`; an
execution that ends with `incomplete` closure retains its operational record
and has technology outcome `none`, as specified above.

| Predicate, in precedence order | Primary outcome |
| --- | --- |
| Lifecycle is `finished` or `abandoned` with `incomplete` evidence closure because not every required comparison is closed | Technology outcome `none`; retain partial evidence, provenance, consumed budgets, stopping reason, and existing branch terminal facts |
| An independently demonstrated shared apparatus/common-pipeline/mandatory-oracle failure affects the comparison | `inconclusive` for the affected comparison |
| The hybrid reaches the branch terminal `Feasibility failure under the registered implementation and budget` | `reject` |
| The hybrid has valid evidence and passes mandatory gates, but all declared baseline validity, mandatory, technology, and feasibility checks leave no eligible passing baseline | Comparative `inconclusive`; only a separate non-comparative `Feasibility demonstrated` annotation may be recorded for the passing hybrid |
| The hybrid has valid evidence and violates a mandatory gate, has a mandatory regression, or lacks the named improvement | `reject` |
| A registered dimension relation contains a detected cycle, or eligible passing baselines exist but the registered Pareto frontier is empty | `inconclusive` for the affected comparison |
| At least one eligible passing frontier baseline conclusively dominates the hybrid on every applicable registered dimension and is better on at least one | `reject`, regardless of simplicity |
| No frontier baseline conclusively dominates the hybrid, and a conclusively simpler eligible baseline matches the hybrid within all frozen equivalence margins | `reject` |
| At least one eligible passing frontier baseline exists; the hybrid passes all mandatory gates, shows the named improvement, meets frozen non-inferiority conditions against every frontier baseline, has no conclusive frontier dominance or simpler match, and has no unresolved declared trade-off | `support` |
| At least one eligible passing baseline exists, but generic evidence affecting a conclusive dominance or match determination, or branch/failure attribution, is unresolved, or a nonmandatory trade-off/comparative visual disagreement remains unresolved after the registered protocol | `inconclusive` |

Baseline feasibility or technology failures can therefore remove a baseline
from eligibility without removing its record. If one or more eligible
baselines remain, the remaining predicates decide the comparison. An empty
frontier with eligible baselines is a protocol/evidence failure and is
comparative `inconclusive`; it cannot produce `support`. A passing hybrid with
no eligible baseline receives only the separate feasibility annotation
described above. A hybrid terminal failure or mandatory failure cannot be
rescued by an empty frontier.
The Stage 1 all-valid-fixtures gate and the separate subjective visual-floor
method remain owned by
[DR-0007](DR-0007-staged-first-proof-charter.md) and the
[visual-quality protocol](../research/visual-quality-evaluation.md).

The table's `support`/`reject`/`inconclusive` result is the primary
comparative outcome of the full hybrid bundle against the eligible baseline
frontier. It is separate from component attribution. For each selected
component (blending and reusable specialized generators), the complete
per-fixture/site/criterion conditional-effect matrix from the required paired
contrasts below is the component-attribution result. There is no collapsed
component-level `Supported`, `Not supported`, or `Harmful` category, no
component completeness threshold for bundle outcome, and no unconstrained
attribution aggregation. Optional coverage counts may be reported only as
preregistered descriptive information; they cannot become a decisive scalar or
a selective-credit rule. Component-matrix `U` cells remain visible evidence
and do not by themselves block bundle `support`; bundle outcome remains
separate and never implies component credit.

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

Under this proposed matrix, `C` is consumed by every branch, `I` only by the
general implicit-field baseline, `S` by the skeleton baseline and the three
skeleton-derived branches, `B` by the blending branch and full hybrid,
and `G` by the generators branch and full hybrid. Each branch has exactly one
integration ledger. These consumer sets are part of the registration and are
frozen before execution; this record does not invent their caps, effort units,
or numeric budget values.

The checkpoint is the immutable initial C scaffold manifest and provenance
boundary. Its common-scaffold ledger admits only work required by every branch
with the same interface/data/access, no branch-construction-specific
implementation or parameters, and admission before branch construction work.
This establishes operational neutrality, not equal benefit. Registration
freezes the base manifest ID, provenance, source state, admitted assets, known
effort, finite C cap, consumers, attribution, exhaustion, and disposition; the
checkpoint and base manifest never move or mutate. C may also record a
post-checkpoint repair only through an append-only, finite repair log. A repair
must pass the same universal identical-interface/data/access and
no-branch-specific-construction-logic-or-parameters test, receives a stable
repair-entry ID, records provenance/source/assets and known effort (or
unavailable historical effort), consumes the frozen C cap exactly once, and
declares affected evidence for rerun. Each evidence item or run snapshot
references both the immutable base manifest ID and the exact repair-log
snapshot ID, including an explicit empty snapshot before any repair; affected
evidence is not current until rerun against the new snapshot. The repair log is
append-only and finite, and each snapshot ID identifies an immutable log
prefix; no numeric cap, ID syntax, or storage format is selected here.
Pre-existing
branch-specific or subset-specific prototypes are excluded from the primary
comparison. They may be retained as clearly scoped exploratory/reference
evidence, but cannot support primary fairness, effort, or feasibility claims.

Across the run, every actual work item is assigned exactly once to the closed
taxonomy: `C`, `I` (general implicit baseline), `S` (skeleton/swept-profile),
`B` (blending), `G` (specialized generators), or one integration ledger for
the branch that performs the integration. `I` is consumed only by the general
implicit baseline; the consuming branches for `S`, `B`, and `G` are fixed by
the matrix. The registration freezes every ledger's consumers,
manifest/provenance, source state, admitted assets, known effort, cap,
attribution, exhaustion, and disposition. No work may be hidden, charged to
more than one ledger, or reclassified as scaffold.

Project actual effort counts each item once. Branch attributed cost views show
the required capability and integration costs and the C attribution
separately; repeated branch attribution is not repeated project work. The
incremental branch budget is tied to the immutable base C manifest ID, the
exact C repair-log snapshot ID, and the attributed branch budget ID. The
feasibility annotation is limited to incremental feasibility from that
base-plus-snapshot state under that budget. Full C effort is reported
separately, with unknown historical effort recorded as unavailable, never
zero. Exhaustion or failure of `I`, `S`, `B`, or `G` affects consuming branches
as feasibility; integration exhaustion affects its branch; C exhaustion or
failure is a registered shared comparison-terminal failure and is affected-
comparison `inconclusive`.

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
terminal failure is `reject`; a baseline terminal failure is retained and
excluded from the frontier. A capability-ledger or branch-integration failure
is branch-specific for every consuming branch. Only an independently
demonstrated shared apparatus, mandatory oracle, or common-pipeline defect
remains affected-comparison `inconclusive` and is not charged as a branch
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

Before execution, registration lists candidate cells and their applicability
for every component, fixture, site, criterion, and paired contrast. An
inapplicable cell is `NA`, recorded with a reason, and excluded from applicable-
cell evidence coverage and denominators. `NA` is distinct from `U`, which is
an unresolved applicable cell. All applicable modalities use one generic
matrix vocabulary: `B` beneficial, `N` neutral-equivalent, `H` harmful, and
`U` unresolved. The evidence rule for `N` is modality-specific.

For each quantitative criterion, registration freezes the estimand, practical-
equivalence margin `±delta`, uncertainty interval and method, replication,
adjudication, multiplicity, validity requirements, and boundary handling. With
a valid uncertainty interval, `B` applies iff the full interval lies beyond
`+delta`; `H` applies iff the full interval lies below `-delta`; and `N`
applies iff the full interval is contained in `[-delta,+delta]`. `U` applies
otherwise or when evidence is invalid or unavailable. These rules are
mutually exclusive and exhaustive under the frozen boundary convention.

Comparative visual evidence uses a panel of at least three eligible,
independent reviewers who are independent of branch implementation and
tuning. Branch presentation is masked and randomized where practical; the
registration records each reviewer's eligibility/independence, individual
`B/N/H/U` vote, presentation/masking provenance, and any exclusions. The
comparative visual rubric is distinct from the mandatory visual-floor rubric.
A visual `B` or `H` requires at least `2/3` same-state agreement among the
eligible panel and no opposite-direction vote. Visual `N` means visually
equivalent under the registered comparative rubric and requires at least `2/3`
equivalence votes with no `B` or `H` vote. If fewer than three eligible
independent reviewers are available, the comparative visual cell is `U` and
exploratory, not conclusive. Any other vote pattern is `U`. Reports use
“neutral equivalence within the frozen margin/rubric”; they do not use “no
effect” as a synonym for `N`.

The complete per-fixture/site/criterion conditional-effect matrix is a
descriptive pattern ledger, not an interaction estimand. Its literal cells
are:

| First state (without other); second state (with other) | `B` | `N` | `H` | `U` |
| --- | --- | --- | --- | --- |
| `B` | Beneficial both contexts | Beneficial without, neutral with | Beneficial without, harmful with | Unresolved |
| `N` | Neutral without, beneficial with | Neutral both | Neutral without, harmful with | Unresolved |
| `H` | Harmful without, beneficial with | Harmful without, neutral with | Harmful both | Unresolved |
| `U` | Unresolved | Unresolved | Unresolved | Unresolved |

Any `U` state is unresolved and any `NA` state remains outside applicable-cell
coverage and denominators. The matrix records conditional-effect patterns
only; its sign patterns do not establish independence, synergy, antagonism,
suppression, reversal, or interaction magnitude. It is not a component score
or a bundle-outcome predicate.

## Consequences

- Stage 1 can test semantic control and organic junction quality together while
  retaining baselines that can disprove the combined hypothesis.
- The evidence-first precedence makes support, rejection, and inconclusive
  outcomes inspectable before evidence exists; it does not turn a mixed
  trade-off into a fabricated scalar score or allow endless unreadiness. The
  common-scaffold checkpoint and one cumulative per-branch budget make
  branch-specific implementation, tuning, and remediation finite from the
  start of counted branch work. The closed C/I/S/B/G and per-branch
  integration ledgers freeze provenance and allocate every work item exactly
  once; C failure is a shared comparison-terminal failure, while I/S/B/G and
  integration failures are branch-specific for their consumers. Shared
  apparatus/common-pipeline or mandatory-oracle failure remains affected-
  comparison `inconclusive`, and branch-specific budget exhaustion cannot be
  overridden by generic evidence unavailability. An empty eligible-baseline
  frontier is comparative `inconclusive`, even when a passing hybrid receives a
  separate feasibility annotation under `finished`/`complete` closure. A
  `finished` or `abandoned` execution with `incomplete` closure retains its
  evidence and has technology outcome `none`.
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
  failed. There is no collapsed component outcome, component completeness
  threshold, or unconstrained aggregation; optional coverage counts are
  descriptive only and cannot selectively credit a component. Component `U`
  cells remain visible evidence and do not by themselves block bundle
  `support`. Bundle outcome never implies component credit. The literal
  B/N/H/U cells are mutually exclusive conditional-effect patterns, and the
  matrix is not an interaction estimand or scalar interaction score.
- A successful surface experiment would support only the stated Stage 1 claim
  under its fixtures and protocol. It would not settle production topology,
  animation deformation, runtime representation, backend, or performance.
- A failed or inconclusive hybrid result must remain visible and may support a
  different hypothesis, a narrower proof, or a revised decision; it must not be
  converted into an unrecorded implementation exception. A hybrid feasibility
  failure is `reject`; a baseline feasibility failure remains visible but
  excludes that baseline from the frontier, without a universal-impossibility
  claim or silent removal. Registered dimension preorders and an acyclic
  aggregate strict partial order preserve an interpretable frontier; a cycle
  or eligible-but-empty frontier is affected-comparison `inconclusive`.

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
comparative `support` when its predicates pass, but that result never implies
component credit or explains why the bundle improved.

#### Option 2: Five-branch bounded nested ablation

This option adds the two one-layer branches to the two simpler baselines and
the full hybrid. It preserves a common semantic vocabulary and operation
budget, layered provenance and effort ledgers, a frozen common-scaffold
checkpoint, one cumulative per-branch readiness-remediation/implementation
budget, and an operation matrix while directly testing each selected layer's
incremental contribution. A branch that cannot reach readiness or comparable
evidence within its registered budget terminates as a branch feasibility
failure; it is not left in an endless `inconclusive` state. The primary bundle
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

An unready branch could remain `inconclusive` indefinitely, or be abandoned
without a preregistered finite budget. That would preserve uncertainty but
would permit unreadiness to evade a terminal branch-sensitive outcome and
would make a registered run non-terminating. It is not selected. The selected
rule freezes an authoritative common-scaffold checkpoint and one cumulative
per-branch readiness-remediation/implementation budget that is already running
before branch-specific implementation, tuning, or remediation counted by the
experiment. Branch exhaustion is `Feasibility failure under the registered
implementation and budget`, while independently demonstrated shared
apparatus/common-pipeline or mandatory-oracle failure remains affected-
comparison `inconclusive`; generic evidence unavailability cannot override
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
empty frontier is affected-comparison `inconclusive`.

#### Conditional-effect alternative: scalar or full-factorial estimand

A common-scale interaction estimand or an exhaustive factorial sweep could
summarize more than the bounded contrasts, but it would add measurement,
multiple-comparison, and search obligations before the first surface proof is
understood. It is not selected. The paired contrasts instead use one exact,
mutually exclusive `B/N/H/U` vocabulary; quantitative `N` uses the uncertainty
interval inside the margin, while visual `N` means equivalence under the
comparative rubric. Their complete per-fixture/site/criterion matrix is a
descriptive conditional-effect pattern ledger, not an interaction estimand or
scalar score.

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
historical/stale evidence for Revision 7. The [Revision 7
architecture/proof/governance review](reviews/DR-0009-rev-07-review-01.md) and
[experiment-design/measurement review](reviews/DR-0009-rev-07-review-02.md)
are Complete, recommend `Revise` at High confidence, and are preserved as
historical/stale evidence for Revision 8. Review Complete is evidence, not a
clean review or acceptance. Their five consolidated findings and the exact
Revision 8 resolutions are:

1. **Accounting taxonomy/scaffold scope remained incomplete.** Revision 8
   closes the actual-work taxonomy at `C` (universal common scaffold/shared
   repairs), `I` (general implicit baseline), `S` (skeleton/swept-profile),
   `B` (blending), `G` (specialized generators), and one integration ledger per
   branch. Every work item belongs exactly once. The registration freezes each
   ledger's consumers, immutable base manifest ID, manifest/provenance, source
   state, admitted assets, known effort, finite cap, attribution, exhaustion,
   and disposition. C admission requires universal need, the same
   interface/data/access, no branch-construction-specific
   implementation/parameters, and admission before branch work. C is finite,
   and post-checkpoint universal repairs use an append-only finite repair log:
   each qualifying repair has a stable entry ID, provenance/source/assets,
   known or unavailable historical effort, cap consumption, and affected
   evidence declaration. Evidence references the immutable base manifest ID
   plus the exact repair-log snapshot ID (including an explicit empty snapshot);
   affected evidence is rerun after a repair. C exhaustion/failure is a
   registered shared comparison-terminal failure; I/S/B/G and integration
   exhaustion is branch feasibility. Project actual effort is counted once,
   branch attributed costs are reported, full C effort is separate, and
   unknown historical effort is unavailable rather than zero. A feasibility
   annotation is limited to the base manifest ID plus repair-log snapshot ID
   under the attributed branch budget ID.

2. **Visual evidence and matrix schema were incomplete.** Revision 8 uses one
   generic `B/N/H/U` vocabulary with modality-specific rules: quantitative
   `N` requires the uncertainty interval inside the registered margin, while
   visual `N` means visual equivalence under the comparative rubric. Candidate
   cells and applicability are preregistered; `NA` is separate, reasoned, and
   excluded from applicable-cell coverage and denominators. Comparative visual
   evidence uses at least three eligible independent reviewers independent of
   branch implementation/tuning, masking/randomization where practical,
   recorded individual votes and provenance, and a rubric distinct from the
   mandatory visual floor. The deterministic `2/3` same-state/no-opposite vote
   rules and the fewer-than-three `U`/exploratory disposition are stated above.

3. **The former `combined-hybrid-only` tag had contradictory, non-testable
   definitions.** Revision 8 removes that tag entirely from current
   proposal/decision/proof language. The primary bundle outcome and the
   component conditional-effect matrix remain separate, with no component
   completeness threshold and no inferred component credit. The term is
   retained only here and in historical descriptions of the older reviews and
   revisions to explain its removal.

4. **Run-execution terms conflicted with the canonical lifecycle vocabulary.**
   Revision 8 uses orthogonal fields consistently: lifecycle `planned`,
   `running`, `finished`, `abandoned`; evidence closure `open`, `complete`,
   `incomplete`; and technology outcome `none`, `support`, `reject`,
   `inconclusive`. planned/running imply open/none; only finished/complete
   may calculate an outcome or feasibility annotation; ended execution without
   closure is finished or abandoned with incomplete/none; and abandoned must
   be incomplete/none. `inconclusive` is not a lifecycle state.

5. **Generic unresolved `attribution` was ambiguous.** Revision 8 names the
   outcome-table condition `branch/failure attribution`. Component-matrix `U`
   cells remain visible evidence and do not by themselves block bundle
   `support`; there is no component completeness threshold.

Revision 8 is unreviewed and unaccepted. It remains Proposed with Owner
approval Pending and Review status Pending. EXP-0001 remains unregistered.

## Implementation and Proof Obligations

- Design (but do not register or create) EXP-0001 to compare all five branches
  in the frozen operation matrix, with the same semantic source intent,
  feature vocabulary, fixture identities, input mapping, common output
  interface, diagnostics, and capture protocol.
- Track three orthogonal fields: lifecycle `planned`/`running`/`finished`/
  `abandoned`, evidence closure `open`/`complete`/`incomplete`, and technology
  outcome `none`/`support`/`reject`/`inconclusive`. planned and running require
  open/none. Only finished/complete may calculate an outcome or feasibility
  annotation. Ended execution without closure is finished or abandoned with
  incomplete/none, and abandoned must be incomplete/none. Preserve partial
  evidence, provenance, consumed budgets, stopping reason, and branch terminal
  facts for every incomplete or abandoned execution; they produce no primary
  technology outcome or feasibility annotation.
- Freeze the comparative decision rule, named junction/feature criteria,
  eligible-frontier dimensions, branch operations, branch-neutral readiness
  fixtures, required-operation coverage, unresolved-defect disclosures,
  common objective, global initialization and tuning protocol, parameter/
  tuning budgets, one cumulative per-branch readiness-remediation/
  implementation budget, and the authoritative common-scaffold checkpoint
  before execution or evidence interpretation. Use the closed actual-work
  taxonomy exactly: finite `C` for universal common scaffold/shared repairs,
  `I` for general implicit baseline, `S` for skeleton/swept-profile, `B` for
  blending, `G` for specialized generators, and one integration ledger per
  branch. C admission requires universal need, the same interface/data/access,
  no branch-construction-specific implementation/parameters, and admission
  before branch work. After the checkpoint, a later repair may enter finite C
  only when the same universal identical-interface/data/access and
  no-branch-specific-construction-logic-or-parameters test still passes. The
  immutable base manifest stays fixed; the qualifying repair is an append-only
  finite repair-log entry with a stable ID, provenance/source/assets, known or
  unavailable historical effort, cap consumption, and affected-evidence
  declaration. Each evidence item references the base manifest ID plus its
  exact repair-log snapshot ID, including an explicit empty snapshot, and
  affected evidence is rerun after a repair. Freeze each ledger's consumers,
  manifest/provenance, source state, admitted assets, known effort, cap,
  attribution, exhaustion, and disposition. C remains finite after checkpoint
  repairs and affected evidence is rerun. Exclude pre-existing branch-specific
  and subset-specific prototypes from primary claims. Assign every work item
  exactly once; count project actual effort once, report branch attributed
  costs, and report full C effort separately. The cumulative branch budget
  starts at the frozen C checkpoint and the feasibility annotation is only
  incremental feasibility from the base manifest ID plus repair-log snapshot ID
  under the attributed branch budget ID.
  Do not allow an exhausted ledger to remain indefinitely unready.
- Preserve the shared-failure distinction: an independently demonstrated
  shared apparatus/common-pipeline or mandatory-oracle failure remains
  affected-comparison `inconclusive`; C exhaustion/failure is the same
  registered shared comparison-terminal disposition. A branch-specific
  inability to reach readiness or comparable evidence within its cumulative
  budget, or exhaustion/failure of I/S/B/G or branch integration, is
  `Feasibility failure under the registered implementation and budget`. A
  branch-specific defect while budget remains is a remediation/readiness state,
  not a terminal final outcome. Attribute branch terminal failure before
  generic evidence unavailability, so the latter cannot override exhaustion.
  Apply `reject` to a hybrid terminal failure; retain and exclude a baseline
  terminal failure; never make a universal-impossibility claim or silently
  remove a branch.
- Freeze the applicability, direction, aggregation, and thresholds of every
  registered comparison dimension; the Pareto dominance relation; the
  simplicity partial order; and equivalence/match margins. Require valid,
  resolved evidence across every applicable dimension before declaring any
  match or dominance. Treat unresolved evidence affecting that determination
  as `inconclusive`; check every frontier baseline for conclusive dominance,
  regardless of simplicity, and every simpler eligible baseline for a
  conclusive match. Require registered dimension relations to be suitable
  preorders and aggregate strict dominance to be an acyclic strict partial
  order; allow incomparability without scalarization. Treat a detected cycle
  or eligible-but-empty frontier as affected-comparison `inconclusive`.
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
  comparative visual quality, which is a declared frontier dimension. Use at
  least three eligible independent comparative visual reviewers independent of
  implementation/tuning; mask/randomize presentation where practical and
  record individual votes and provenance. Use a comparative rubric distinct
  from the mandatory visual-floor rubric. Record all eligible passing baselines
  and their non-dominated frontier, mixed trade-offs, visual disagreement,
  common-pipeline failure, branch-specific mandatory failures,
  budget/readiness breaches, and inadequate evidence as required by the strict
  precedence table; do not force an outcome.
- For every candidate cell, preregister applicability; record inapplicable
  cells as `NA` with a reason and exclude them from applicable-cell coverage
  and denominators. Use one generic `B/N/H/U` vocabulary. For quantitative
  criteria, preregister the estimand, practical-equivalence margin `±delta`,
  uncertainty interval and method, replication, adjudication, multiplicity,
  validity, and boundary handling; assign `B` only when the full valid interval
  lies beyond `+delta`, `H` only when it lies below `-delta`, `N` only when it
  is contained in `[-delta,+delta]`, and `U` otherwise or when evidence is
  invalid or unavailable. For visual criteria, `N` means visually equivalent
  under the comparative rubric; `B`/`H` require at least `2/3` same-state
  votes and no opposite-direction vote, `N` requires at least `2/3`
  equivalence votes and no `B`/`H` vote, and fewer than three eligible
  independent reviewers makes the cell `U`/exploratory rather than conclusive.
  Keep states mutually exclusive and exhaustive for applicable cells; use
  “neutral equivalence within the frozen margin/rubric,” never “no effect.”
- Report the primary bundle comparative outcome separately from the complete
  per-fixture/site/criterion conditional-effect matrix for each component.
  That complete matrix is the component-attribution result; do not create a
  collapsed component outcome, component completeness threshold, or
  unconstrained aggregation. Optional coverage counts are descriptive only,
  preregistered, and cannot become a decisive scalar or selective-credit rule.
  Component-matrix `U` cells remain visible evidence and do not by themselves
  block bundle `support`; bundle outcome never implies component credit.
- Register the beneficial direction and paired conditional-effect contrast for
  every criterion, assigning the first state to the contrast without the other
  contribution and the second state to the contrast with it. Use the literal
  descriptive matrix: `B/B` beneficial both contexts; `B/N` beneficial without,
  neutral with; `B/H` beneficial without, harmful with; `N/B` neutral without,
  beneficial with; `N/N` neutral both; `N/H` neutral without, harmful with;
  `H/B` harmful without, beneficial with; `H/N` harmful without, neutral with;
  `H/H` harmful both; and any `U` unresolved. Record `NA` separately for
  inapplicable candidate cells with a reason. The matrix is a conditional-
  effect pattern ledger, not an interaction estimand, and does not establish
  independence, synergy, antagonism, suppression, reversal, or interaction
  magnitude. It is not a component score or bundle-outcome predicate.
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

# Architecture documentation

Status: Provisional architecture baseline

This directory owns Creature Kernel's target technical boundaries, data flow,
invariants, and component responsibilities. Normative serialized formats and
semantic vocabularies belong in [`spec/`](../../spec/).

## Documents

- [System overview](system-overview.md)
- [Execution model](execution-model.md)
- [Component responsibilities](component-responsibilities.md)
- [Repository structure](repository-structure.md)
- [Decision records](../decisions/README.md)

## Architectural authority

- Product requirements define the outcomes architecture must satisfy.
- Specifications define the contracts architecture consumes and produces.
- Architecture defines target responsibilities and invariants.
- Decision records explain consequential choices and identify canonical documents
  to update.
- Research and experiments provide evidence but are not automatically normative.
- Implementation may lag architecture; project tracking must report that gap.

Architecture documents must label unresolved areas rather than presenting a
plausible proposal as an accepted contract. The current content is a proposed,
assistant-synthesized target pending review; it is not an accepted architecture
baseline.

The Round 2 product-boundary proposal in
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md)
keeps Creature Kernel's initial target engine-independent and downstream of a
real-time game integration. Related Proposed source, operation, and identity
boundaries are recorded in [DR-0002 Revision 2](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md),
and [DR-0006 Revision 1](../decisions/DR-0006-durable-semantic-and-artifact-identity.md).
Those records do not settle physical formats or identity syntax. The related
Proposed compile/runtime boundary is recorded in
[DR-0003 Revision 2](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)
and described in the execution model; exact interface schemas, compatibility,
budgets, and runtime mutation details remain open.

Round 13 records the current Proposed Stage 1 experiment hypotheses in
[DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
and [DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md).
DR-0009 Revision 8 applies the universal identical `C` scaffold/shared-repair
admission test, an immutable base `C` scaffold manifest plus a finite append-
only repair log and immutable snapshots, finite `C`/`I`/`S`/`B`/`G` and branch-
integration ledgers,
literal conditional-effect patterns, the full per-fixture/site/criterion
matrix as the sole component attribution, generic quantitative `B/N/H/U` and
modality-specific visual `N` with separate `NA`, branch/failure attribution,
and the three-field experiment lifecycle/closure/outcome vocabulary. DR-0010
Revision 8 carries this derived outcome/budget, branch/failure/component-matrix
attribution, visual-adjudication, and experiment lifecycle/closure/outcome
alignment and leaves exactly its two
geometry/semantic findings unresolved. A component `U` cell does not by itself
block bundle `Support`; failure or exhaustion of `C` is
a shared comparative `Inconclusive` terminal. Evidence identifies the
immutable base manifest and exact repair-log snapshot (including the explicit
empty snapshot before repairs); affected evidence is rerun after a repair.
Actual-once work, attributed branch cost, and base-plus-snapshot-scoped
feasibility remain distinct. DR-0009 remains
Proposed with Owner approval Pending and Review status Complete. Its two
Revision 8 Double-review artifacts recommend `Revise` at High confidence;
Review Complete records evidence, not a clean review or acceptance. Five
unresolved groups remain for Ben's discussion before Revision 9: repair
epochs/adaptive admission, C accounting and workflow records, independent
deterministic visual-floor adjudication, causal branch/failure attribution,
and bundle closure versus component `U`. Its Revision 7
reviews are historical/stale. DR-0010 remains Proposed with Owner approval Pending and
Review status Pending; its Revision 5 reviews are historical/stale and
Revision 7 was unreviewed and superseded. The
[first surface experiment design](../research/first-surface-experiment-design.md)
remains a neutral Proposed, manually maintained evidence plan; it does not
register EXP-0001 or create evidence. These materials guide falsifiable
evidence only; none settles permanent surface architecture, animation-ready
topology, runtime field representation, implementation language, or a geometry
backend.

## Current maturity

The architecture is pre-implementation. Component names describe provisional
responsibility boundaries, not approved packages, processes, repositories, or
technologies.

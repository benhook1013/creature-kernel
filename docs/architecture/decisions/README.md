# Architecture decision process

Status: Active process proposal

This directory records consequential decisions and their rationale. ADRs do not
replace canonical product, specification, or architecture documents. An accepted
ADR must identify and update the contracts it affects.

## When an ADR is required

Use an ADR when a choice materially affects one or more of:

- public or serialized contracts;
- semantic compatibility or migration;
- component and dependency boundaries;
- runtime performance architecture;
- geometry, animation, collision, or solver strategy;
- determinism, reproducibility, or networking;
- portability or host-engine coupling;
- security, licensing, or a difficult-to-replace dependency;
- large artifact storage or release compatibility;
- a previously accepted decision.

Small reversible implementation details do not require ADRs unless they become
contractual or repeatedly disputed.

## States

- `Candidate`: named in the registry but not yet a concrete proposal.
- `Proposed`: a complete proposal exists and can be challenged.
- `Under Review`: adversarial review is active for the current revision.
- `Accepted`: the human decision owner approved the reviewed revision.
- `Rejected`: considered and intentionally not selected.
- `Superseded`: replaced by a later accepted ADR.
- `Withdrawn`: proposal removed before a decision.

## Revision and review rule

Every proposal has an integer revision. A material change to the decision,
constraints, alternatives, or consequences increments the revision. Reviews name
the exact revision they assessed. An older review does not satisfy the acceptance
requirement for a newer revision.

An ADR may become `Accepted` only when:

1. An adversarial review covers its current revision.
2. Material objections have an explicit response.
3. Required experiments are complete or explicitly deferred with risk recorded.
4. Canonical design links and proof obligations are identified.
5. The decision owner explicitly approves it.

A human waiver may replace a missing review or proof obligation, but the ADR must
record the waiver, reason, and accepted risk.

Record explicit acceptance as `Owner approval: Approved by <Decision owner>` in
the ADR metadata. Until then use `Owner approval: Pending`. When `Review status`
is `Waived`, record non-placeholder `Waiver reason` and `Accepted risk` lines in
the adversarial-review response. A waived review is not implicit owner approval.

The validator checks metadata, registry agreement, review revision and links,
owner approval, and waiver fields. Human review remains responsible for judging
whether objections were answered adequately and whether experiment deferrals or
accepted risks are reasonable.

## Workflow

1. Add a candidate to [the registry](registry.md).
2. Copy [the ADR template](adr-template.md) and write a concrete proposal.
3. Set status to `Proposed`, review status to `Pending`, and revision to `1`.
4. Set the ADR to `Under Review` when review begins and request a review using
   the [adversarial review template](reviews/adversarial-review-template.md).
5. Record the proposal response and revise when necessary.
6. Obtain evidence through an experiment when claims remain uncertain.
7. The human decision owner accepts, rejects, withdraws, requests another
   revision, or leaves the ADR proposed with a named blocker.
8. Record explicit owner approval when accepting the ADR.
9. Update canonical documents and track implementation/proof obligations.

## Independence

When practical, the adversarial reviewer should use a fresh context, separate
agent/model, or external domain expert rather than the reasoning context that
authored the proposal. The review recommends; it does not decide.

## Naming

- ADR: `ADR-NNNN-short-title.md`
- Review: `ADR-NNNN-rev-RR-review-NN.md`

Numbers are never reused.

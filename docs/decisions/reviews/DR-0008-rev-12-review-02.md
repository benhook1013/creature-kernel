# Adversarial review: DR-0008 revision 12

Target DR: DR-0008

Target revision: 12

Review status: Complete

Execution state: Complete

Batch context: R3 resolver-boundary current-revision Double review

Review lens: Activation, evidence, compatibility, and reversibility

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; evidence only; no
authorship or edits

Date: 2026-08-18

Recommendation: Revise

Confidence: High

Reviewed commit: `e1ead72`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

The R3 direction is coherent, but the activation boundary does not yet carry
enough immutable evidence to prove the authored-conflict comparison profile,
its successor experiment lineage, or the morphology classification boundary.

## Findings

### R3-02-01 — Authored-conflict profile binding is not mechanically complete (High)

The activation payload can currently prove the expected-snapshot comparison-
profile binding, but not exactly one separately bound authored-conflict profile,
its constants, and its binding to the resolver/build request. Missing, extra, or
mismatched bindings therefore lack an explicit fail-closed activation rule.

Recommended disposition: define a separate content-bound authored-conflict
profile identity and definition, require cardinality exactly one, bind it to the
resolver/build request, and reject activation for missing, additional, or
mismatched bindings.

### R3-02-02 — Successor experiment is not admission-lineage bound (High)

The successor experiment is required narratively, but the current admission
shape does not prevent post-hoc selection of candidate rules or results. The
completed EXP-0002 attempt-001 has `profile_binding: null` and cannot satisfy
the R3 gate.

Recommended disposition: preregister candidate profile/rules/budgets/margin and
corpus roles, bind immutable result identities into the R3 admission, and
require a new candidate/evaluation after any failed or inconclusive result.

### R3-02-03 — Morphology classification boundary needs explicit fixtures (Medium)

The activation fixture set does not yet prove representative out-of-envelope
rejection, and DR-0008 uses ambiguous “invalid or deferred” wording. The
existing taxonomy already implies the distinction: a recognized first-family
invariant contradiction is `invalid-source`; a well-formed recognized
outside-family morphology is `unsupported`; malformed/schema errors follow
body-document rules.

Recommended disposition: clarify that taxonomy in the canonical wording and
add representative valid, invalid, and unsupported boundary fixtures. This is
technical alignment, not a new product choice.

## Blocking Objections

The three findings above are unresolved blockers to claiming the R3 activation
boundary is ready; they are recommendations for Ben's disposition, not fixes
made by this review.

## Non-blocking Risks

No additional non-blocking risk was recorded by this pass.

## Conditions for Acceptance

Resolve or explicitly disposition the three findings above before accepting the
direction or activating R3.

## Review Limitations

This was an evidence-only document review. No implementation, experiment,
fixture execution, or tests were performed by this pass.

## Documents Consulted

- DR-0008 Revision 12 and its linked current decision records
- Aligned product, architecture, body-document, body-graph, numeric-profile,
  fixture/admission, and project-status documents
- EXP-0002 attempt-001 results, including its null profile binding
- The prior Revision 11 review artifacts as stale history only

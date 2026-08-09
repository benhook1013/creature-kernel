# Adversarial review: DR-0009 revision 6

Target DR: DR-0009

Target revision: 6

Review status: Complete

Reviewer: Fresh gpt-5.6-sol experiment-design/measurement reviewer

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-09

Recommendation: Revise

Confidence: High

Reviewed commit: 0f26240658c1bd1f75e0d2dd92420fbd3243932d

## Executive Assessment

Revision 6 remains unjustified for acceptance because four high-severity
experiment-design and measurement gaps remain.

Prior-finding assessment: terminal/shared disjoint, bundle/component split, and
partial-order frontier fixed; budget and B/N/U only partially resolved; carried
DR-0010 issues not re-reported.

## Blocking Objections

### 1. High — Pre-checkpoint work can bypass branch budget

**Evidence:** DR-0009 lines 169-179, 339-345, 351-369; first-surface design
lines 138-153.

**Reason:** Pre-existing prototypes, branch-favoring shared infrastructure,
and dual-use work lack admission/allocation; nearly complete hybrid could
arrive pre-checkpoint while baseline pays full cost.

**Resolution:** Freeze scaffold provenance/allocation; genuinely neutral common
work benefits affected branches equivalently; charge or explicitly exclude
pre-checkpoint branch-specific/dual-use work; scope feasibility claim to
declared pre-existing assets.

### 2. High — Matrix labels assert interactions not established, and component aggregation is unconstrained

**Evidence:** DR-0009 lines 295-307, 385-436, 761-783.

**Reason:** B/B can hide large positive/negative interaction magnitude; mixed
fixture/site/criterion states permit selection.

**Resolution:** Rename cells as descriptive conditional-effect patterns or
preregister common-scale interaction estimand with equivalence/uncertainty;
define aggregation including U, mixed signs, fixtures, sites, criteria.

### 3. High — B/N/H/U meanings overlap despite arbitrary precedence

**Evidence:** DR-0009 lines 393-415, 768-780; design lines 173-180; visual
protocol lines 111-129.

**Reason:** A precise small positive interval may show direction and fall within
neutral margin; visual criteria lack measured inter-reviewer precision.

**Resolution:** Disjoint practical-effect regions: B/H beyond positive/negative
practical boundary, N uncertainty contained inside equivalence bounds, U
otherwise; freeze estimand, uncertainty, replication/adjudication,
multiplicity; separate qualitative visual rule if needed.

### 4. High — Outcome table is not total for unfinished/unavailable hybrid with no eligible baseline

**Evidence:** DR-0009 lines 181-205, 259-280.

**Reason:** No-baseline row requires valid passing hybrid; generic-unresolved row
requires eligible baseline, so an abandoned run with budget remaining has no
disposition.

**Resolution:** Interpret outcome only when every branch has valid evidence or
terminal state; add explicit incomplete/abandoned-run disposition that cannot
yield Support/Reject/feasibility annotation.

## Non-blocking Risks

None beyond the blocking objections.

## Conditions for Acceptance

Freeze scaffold provenance/allocation and account for or explicitly exclude
pre-checkpoint branch-specific and dual-use work, with feasibility claims scoped
to declared pre-existing assets. Rename interaction cells or preregister a
common-scale interaction estimand and define aggregation. Make B/N/H/U regions
disjoint and freeze the estimand, uncertainty, replication/adjudication, and
multiplicity rules. Add an incomplete/abandoned-run disposition that cannot
yield Support, Reject, or a feasibility annotation.

## Review Limitations

This was a fresh conceptual experiment-design/measurement review of the
reviewed commit. No implementation, registrations, fixtures, captures,
benchmarks, or threshold measurements were available.

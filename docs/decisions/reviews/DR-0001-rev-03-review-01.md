# Adversarial review: DR-0001 revision 3

Target DR: DR-0001

Target revision: 3

Review status: Complete

Reviewer: Fresh gpt-5.6-sol medium subagent

Independence: Fresh context; separate agent/model instance; no authorship or edits

Date: 2026-08-08

Reviewed commit: 69ba00256e60a0870d94467e2d722ac439bf1d35

Recommendation: Revise

Confidence: High

## Canonical Review Bundle

- [DR-0001 Revision 3](../DR-0001-documentation-authority-and-review-process.md)
- [DR-0001 Revision 2 review](DR-0001-rev-02-review-01.md)
- [Documentation authority and navigation](../../README.md)
- [Decision record process](../README.md)
- [Decision record registry](../registry.md)
- [Decision record template](../decision-record-template.md)
- [Decision review process](README.md)
- [Adversarial review template](adversarial-review-template.md)
- [Fresh-reread preamble](fresh-reread-preamble.md)
- [Contributor instructions](../../../AGENTS.md)
- [Project README](../../../README.md)
- [Developer workflow index](../../developer-workflows/README.md)
- [AI delegation and review workflow](../../developer-workflows/ai-delegation-and-review.md)
- [Kickoff plan](../../project/kickoff-plan.md)
- [Project status](../../project/status.md)
- [Repository evolution](../../project/repository-evolution.md)
- [Product documentation index](../../product/README.md)
- [Architecture documentation index](../../architecture/README.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0003](../DR-0003-real-time-first-compiled-avatar-boundary.md)
- [DR-0004](../DR-0004-external-automation-through-cli-and-api.md)
- [Documentation validator](../../../dev-tools/validation/validate_docs.py)
- Validator unit tests (`dev-tools/validation/tests/test_validate_docs.py`, later removed)
- [Documentation workflow](../../../.github/workflows/documentation.yml)

## Sources Actually Read

- [DR-0001 Revision 3](../DR-0001-documentation-authority-and-review-process.md)
- [DR-0001 Revision 2 review](DR-0001-rev-02-review-01.md)
- [Documentation authority and navigation](../../README.md)
- [Decision record process](../README.md)
- [Decision record registry](../registry.md)
- [Decision record template](../decision-record-template.md)
- [Decision review process](README.md)
- [Adversarial review template](adversarial-review-template.md)
- [Fresh-reread preamble](fresh-reread-preamble.md)
- [Contributor instructions](../../../AGENTS.md)
- [Project README](../../../README.md)
- [Developer workflow index](../../developer-workflows/README.md)
- [AI delegation and review workflow](../../developer-workflows/ai-delegation-and-review.md)
- [Kickoff plan](../../project/kickoff-plan.md)
- [Project status](../../project/status.md)
- [Repository evolution](../../project/repository-evolution.md)
- [Product documentation index](../../product/README.md)
- [Architecture documentation index](../../architecture/README.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0003](../DR-0003-real-time-first-compiled-avatar-boundary.md)
- [DR-0004](../DR-0004-external-automation-through-cli-and-api.md)
- [Documentation validator](../../../dev-tools/validation/validate_docs.py)
- Validator unit tests (`dev-tools/validation/tests/test_validate_docs.py`, later removed)
- [Documentation workflow](../../../.github/workflows/documentation.yml)

## Executive Assessment

Revision 3 improves proposal and status visibility and adds review-evidence and
structured-response rules with corresponding test targets. It is not ready for
acceptance. Two material contradictions remain and require Revision 4 followed
by a fresh current-revision review.

## Strongest Case Against

A lighter canonical-owner map, simple decision log, and risk-triggered human
review could avoid bootstrap self-authorization, mutable exact-revision links,
fixed rounds, and provider-specific routing. The richer process is justified
only if authority boundaries and evidence identity are unambiguous; otherwise
the extra structure may create confidence without durable proof.

## Hidden Assumptions

- The trial safety authorization is understood to cover every binding technical
  constraint in the root contributor guidance.
- A mutable decision-record path plus revision metadata preserves the exact
  content a reviewer assessed.
- Git history can independently reconstruct the reviewed content when a path
  later changes.
- Overlapping discussion, research, and review rounds remain clear to every
  contributor.
- Named model SKUs remain available and stable enough for the routing policy.

## Failure Modes and Edge Cases

- Stable semantic-ID and engine-independent-core mandates in AGENTS.md are
  treated as binding before DR-0002 or DR-0003 is accepted.
- The Revision 2 review link resolves the newer DR-0001 file, making historical
  evidence appear to target Revision 3.
- The validator passes a review whose mutable path exists but whose reviewed
  content, commit, or digest no longer matches the claimed revision.
- Overlapping rounds cause a reviewer and the main thread to act on different
  proposal revisions or canonical bundles.
- Model availability changes leave the named review route unavailable.

## Alternatives and Steelman

The unified high-threshold DR system remains defensible for this project size.
It keeps authority scopes and cross-cutting rationale in one place and can
remain lightweight if its trial boundary and evidence identity are explicit.

Exact-revision evidence could use immutable revision files, a reviewed commit or
tree identity, or a content digest. Each option preserves stronger historical
identity than a mutable path alone, while an immutable snapshot convention may
cost more repository space and a digest requires careful canonicalization.

## Performance and Scalability

No pre-acceptance benchmark is required. Later rounds should measure elapsed
latency, reviewer and main-thread effort, revision count, bypass attempts, and
post-review decision changes. These measurements can show whether round delay,
evidence capture, or routing creates disproportionate process cost.

## Portability, Lock-in, and Reversibility

The Markdown authority model and local validation remain portable. Model-routing
duplication is a nonblocking, revisitable maintenance risk. A rollback path
exists in the bootstrap rule, but the scope of what may bind contributors and
the identity of reviewed evidence must be fixed before acceptance.

## Licensing, Security, and Supply Chain

There is no licensing or security blocker in the proposed governance structure.
GitHub Actions and hosted models are operational dependencies only; their
availability and permissions still require eventual fallback and operational
review. This review offers no legal opinion.

## Evidence Gaps

- Define the exact scope of the human authorization that permits bootstrap
  controls to bind contributors.
- Establish durable identity for reviewed content beyond a mutable path and
  revision field.
- Add a negative mismatch test proving that changed content cannot satisfy an
  exact-revision review claim.
- Gather later empirical evidence about process latency and review overhead.

## Blocking Objections

### Bootstrap authorization is narrower than binding contributor guidance

Severity: blocking

Why it blocks acceptance: DR-0001 permits trial controls solely for authority
separation, proposal labels, review evidence, repository safety, and explicit
human ownership. However, AGENTS.md mandates stable semantic IDs and separation
of the engine-independent core from host-engine adapters. Those are substantive
technical constraints associated with unaccepted DR-0002 or DR-0003 material,
not only the authorized safety kernel.

Documents involved: DR-0001, AGENTS.md, the project README, and DR-0002 and
DR-0003-related architecture/product guidance.

Evidence needed: An explicit determination of the bootstrap authorization scope
and a status audit of which contributor instructions are trial-only versus
accepted contracts.

Suggested fix: Revision 4 should either explicitly broaden the human
authorization to cover these provisional technical constraints or downgrade or
remove the substantive mandates while keeping the safety kernel binding. The
choice must preserve DR-0002 and DR-0003 as Proposed.

### Exact-revision evidence is mutable

Severity: blocking

Why it blocks acceptance: Review links point to a mutable DR filename. The
Revision 2 review link now resolves the Revision 3 content, and the validator
and tests do not bind the review to a commit, blob, digest, or immutable
snapshot. Presence of a path therefore cannot prove the content actually
reviewed.

Documents involved: DR-0001, the Revision 2 review artifact, review templates,
the documentation validator, validator unit tests, and the documentation
workflow.

Evidence needed: A durable identity convention and a negative mismatch test
showing that a changed path or content cannot satisfy a claimed exact-revision
review.

Suggested fix: Revision 4 should choose an immutable reviewed-commit, content
digest, or revision-snapshot convention; update the process and mechanical
checks accordingly; and migrate historical review references without rewriting
their conclusions.

## Non-blocking Risks

- The round boundary remains somewhat imprecise when research and review
  overlap.
- “When practical” independence leaves judgment to the main thread, but this is
  acceptable for the current trial.
- Model routing and cost should be revisited when availability or process
  measurements change.

## Conditions for Acceptance

- Resolve both blockers in Revision 4 without accepting DR-0002–0004.
- Obtain a fresh review of the exact Revision 4 and affected canonical bundle.
- Record structured responses to that review and obtain Ben's explicit
  disposition only afterward.

## Review Limitations

This was a read-only review of the exact clean assigned commit and 24-file
corpus. It did not execute validation, inspect additional Git history, access
the network or CI, or inspect external material or review state. The review
recommends `Revise` only; it does not decide acceptance and does not make a
legal or product/architecture determination.

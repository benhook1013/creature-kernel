# Adversarial review: DR-0008 revision 13

Target DR: DR-0008

Target revision: 13

Review status: Complete

Execution state: Complete

Batch context: R3 morphology-boundary taxonomy Double review

Review lens: Taxonomy, compatibility, and fixture-boundary correctness

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; evidence only; no
authorship or edits

Date: 2026-08-18

Recommendation: Revise

Confidence: High

Reviewed commit: `117544a`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

The bounded morphology direction is sound, but the canonical taxonomy did not
yet identify a machine-observable request profile or deterministic distinction
between unsupported requests and contradictions within the supported profile.
Its outside-envelope and arbitrary-graph fixture wording was also ambiguous.

## Findings

### R3-03-01 — Outside-envelope wording conflicts with unsupported mapping (Medium)

DR-0008 still described extra limbs, quadrupeds, and related structures as
“invalid or deferred” while later paragraphs mapped recognized outside-envelope
requests to `unsupported`.

Recommended disposition: state that the envelope is deferred for future support;
an explicit well-formed request is `unsupported`, while a source claiming the
supported profile and violating its invariants is `invalid-source`.

### R3-03-02 — Morphology request identity and classification order are not observable (High)

The normalized source had no required source-level morphology/grammar request
profile identity, and no deterministic order distinguished a supported-profile
contradiction from an unsupported morphology request.

Recommended disposition: add one R3-gated top-level profile identity for the
assembled source, separate from `semantic_numeric`, and classify it after
admission/dependency/resource checks: missing or malformed is invalid; a
recognized supported profile runs its invariants; a well-formed unknown or
unsupported profile is unsupported without those invariants.

### R3-03-03 — Boundary fixtures are underspecified (Medium)

“Arbitrary/unbounded attachment graph” and “or equivalent” could accidentally
exercise cycles, dangling endpoints, capacity errors, or resource limits rather
than morphology support. That would make the expected unsupported result
ambiguous.

Recommended disposition: define five representative roles—supported valid,
supported contradiction, quadruped, extra-limb, and explicit freeform topology—
and require the latter three to be finite, schema-valid, duplicate-free,
acyclic, resource-admitted, and free of endpoint/capacity defects.

## Blocking Objections

The three findings above block claiming an unambiguous R3 morphology taxonomy;
they are recommendations for technical disposition, not fixes made by this
review.

## Non-blocking Risks

Exact profile field spelling, IDs, schema revision, diagnostic codes, and
fixture files remain intentionally gated and must be selected before activation.

## Conditions for Acceptance

Resolve or explicitly disposition the three findings above before accepting the
direction or activating R3.

## Review Limitations

This was an evidence-only document review. No implementation, experiment,
fixture execution, or tests were performed by this pass.

## Documents Consulted

- DR-0008 Revision 13 and its linked current decision records
- The canonical body-document, body-graph, fixture-manifest, numeric-profile,
  architecture, and project-status documents
- The Revision 12 review artifacts as stale history only

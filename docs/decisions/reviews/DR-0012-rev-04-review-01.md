# Adversarial review: DR-0012 revision 4

Target DR: DR-0012

Target revision: 4

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 7 current-revision double review

Review lens: Contract, schema, determinism, and authority boundaries

Reviewer: Fresh gpt-5.6-sol contract/schema/determinism/authority reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 88004388f9537a37617ae248bdaad4625e6f3f03

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 4 provides a useful bootstrap, phase, diagnostic, and resource-boundary
proposal. Three linked contract gaps remain material: status/completeness is
not total for all dependency and diagnostic combinations, Socket capacity is
ambiguous across roles, and typed Attachment inversion has no total transform
admissibility rule.

## Blocking Objections

1. **High — Status and completeness remain non-total for competing outcomes.**

   **Failure scenario:** A dependency can be unavailable or unverifiable and
   produce `dependency-failure`, or complete content can be malformed or
   unsupported, but the mixed same-phase precedence is unspecified. Independent
   checks may continue or stop without a normative rule. Processing completeness
   for an ordinary invalid/unsupported fatal result is ambiguous, and CK-PROD-
   033's diagnostic charging/resource wording can conflict with the ordinary
   diagnostic-truncation exception. Equivalent inputs can yield divergent
   envelopes.

   **Recommended resolution:** Publish a total phase/status/completeness matrix
   covering dependency acquisition/content overlap, continuation policy, normal
   fatal outcomes, diagnostic truncation, and resource-limit breaches; align the
   product requirement and canonical mirrors.

2. **Medium — Socket capacity is ambiguous across host and mating roles.**

   **Failure scenario:** Host and mating reuse by distinct Attachments are
   separately rejected, but one Socket used once in each role is not classified.
   Nested attached roots make global versus role-local capacity observable and
   can change the normalized graph and diagnostic.

   **Recommended resolution:** Define global or role-scoped capacity, nested
   provenance, and deterministic cross-role diagnostics or allowed semantics.

3. **High — Attachment placement is not total over the deferred transform
   domain.**

   **Failure scenario:** The Attachment equation requires an inverse, but a
   source-authored basis may be singular or degenerate. Canonical numeric and
   tolerance details are deferred without an admissibility invariant or status
   mapping, leaving resolver implementations to diverge.

   **Recommended resolution:** Specify transform admissibility, numeric
   tolerance, provenance, and deterministic outcome/diagnostic mapping for
   non-invertible inputs before claiming complete resolution semantics.

## Non-blocking Risks

1. **Medium — Exact schema and fixtures do not by themselves activate the
   semantic resolver.**

   Canonical axes/units, rotation, scale/shear, numeric representation, and
   tolerances remain needed for semantic normalization and snapshot publication.
   Parser/bootstrap acceptance should be distinguished from those later
   semantic stages. This is a staged activation obligation, not a requirement
   to make every representation detail part of this revision.

## Conditions for Acceptance

Close the total operation matrix, cross-role Socket policy, and Attachment
inverse domain. Define the staged parser/bootstrap versus semantic
normalization/snapshot boundary and freeze the exact frame/numeric fixtures
needed before resolver activation.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
schema, parser/resolver, fixtures, fuzz/property tests, numerical benchmarks,
or specialist security audit were available.

## Documents Consulted

- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [CK-PROD-033](../../product/requirements.md)
- Decision-record review process and CK-KICK-012 Batch 7 review brief

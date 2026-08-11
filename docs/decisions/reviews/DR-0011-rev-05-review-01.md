# Adversarial review: DR-0011 revision 5

Target DR: DR-0011

Target revision: 5

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

Revision 5 provides a useful typed vocabulary and explicit Attachment frame
composition. Two linked semantic contracts remain material: Socket capacity
across host and mating roles is not closed, and the Attachment inverse has no
total admissibility or status rule for degenerate source transforms.

## Blocking Objections

1. **Medium — Socket capacity is ambiguous across host and mating roles.**

   **Failure scenario:** Host and mating Socket reuse is rejected by distinct
   active Attachments in their respective roles, but the same Socket used once
   in each role is not classified. Nested module ownership makes global versus
   per-role capacity observable, allowing divergent normalized graphs and
   diagnostics.

   **Recommended resolution:** Specify global or role-scoped capacity, nested
   provenance, and deterministic cross-role diagnostics or permitted semantics.

2. **High — Attachment placement is not total over the deferred transform
   domain.**

   **Failure scenario:** The typed frame equation requires an inverse, while
   canonical axes, scale/shear policy, and numeric tolerances remain deferred.
   A singular or degenerate source basis can have no inverse and currently has
   no deterministic semantic-invalid or other outcome mapping.

   **Recommended resolution:** Define the backend-neutral transform
   admissibility invariant, numeric tolerance, provenance, and status/diagnostic
   mapping before consumers rely on the canonical placement.

## Non-blocking Risks

No additional DR-0011-specific status issue was identified: operation status
and completeness are linked to DR-0002/DR-0012. The exact canonical numeric
representation, axes, units, and tolerance remain deferred implementation/spec
detail, but they are activation obligations for a deterministic frame resolver.

## Conditions for Acceptance

Close cross-role Socket capacity and the inverse-domain contract, then provide
fixtures for nested/cross-role Socket use, singular or degenerate transforms,
and provenance-preserving frame conversion. Keep runtime pose and derived
world/reference frames distinct from authored local frames.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
schema, resolver, frame fixtures, geometry captures, numeric benchmarks, or
specialist numerical audit were available.

## Documents Consulted

- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 7 review brief

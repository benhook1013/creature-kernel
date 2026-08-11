# Adversarial review: DR-0012 revision 4

Target DR: DR-0012

Target revision: 4

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 7 current-revision double review

Review lens: Platform, build, geometry, reversibility, and host-integration boundaries

Reviewer: Fresh gpt-5.6-sol platform/build/geometry/reversibility/host-integration reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 88004388f9537a37617ae248bdaad4625e6f3f03

This artifact records review evidence and recommendations only. It accepts no
product, specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 4 establishes a credible exact-contract and ordered-resolution
direction. Three issues remain: ordinary fatal processing completeness is
ambiguous, module-root presence is not independently observable when its
Attachment is missing, and exact schema/fixtures are insufficient to activate a
deterministic semantic resolver without a staged numeric/frame contract.

## Blocking Objections

1. **High — Processing completeness is ambiguous for normal fatal outcomes.**

   **Failure scenario:** Invalid JSON or an unsupported family/revision stops
   downstream work, but the record does not state whether processing is complete
   relative to applicable work or incomplete relative to the full phase graph.
   Clients can disagree about the completeness of the same authoritative
   failure result.

   **Recommended resolution:** Define applicable-work semantics and a
   status/phase/completeness matrix for admission, parse, dependency,
   normalization, snapshot publication, and intentionally blocked phases.

2. **High — A present attached module root is not independently observable when
   its required Attachment is missing.**

   **Failure scenario:** Since `Module` is not a graph concept, Attachment
   cardinality alone cannot distinguish a present root with zero incoming
   Attachments from an absent optional module or an undeclared root. This makes
   normalized output, provenance, and diagnostics backend-dependent.

   **Recommended resolution:** Add a backend-neutral normalized module-root
   declaration with explicit presence/optionality and source provenance, then
   validate zero/one/multiple Attachment cases against it.

## Non-blocking Risks

1. **Medium — Exact schema and fixtures do not by themselves activate the
   resolver.**

   Canonical axes/units, rotation representation, scale/shear policy, numeric
   representation, and tolerances remain necessary for semantic normalization
   and snapshot publication. Parser/bootstrap should be a separately identified
   stage from semantic normalization and publication. This is an activation and
   evidence obligation, appropriately deferred from the exact parser syntax.

No additional independent DR-0012 issue was identified from this platform and
geometry lens beyond the linked Socket-role, transform-domain, and DR-0013
activation/publication concerns.

## Conditions for Acceptance

Close applicable-work completeness and normalized module-root observability.
Before semantic resolver activation, define the staged bootstrap versus
normalization/publication boundary and freeze the canonical frame/numeric
contract and fixtures needed for deterministic results.

## Review Limitations

This was a fresh conceptual review of the exact commit. No implementation,
schema, resolver, geometry backend, host integration, fixture corpus,
benchmarks, or portability evidence was available.

## Documents Consulted

- [DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- [DR-0002](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0011](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0013](../DR-0013-first-production-implementation-platform-and-geometry-boundary.md)
- Decision-record review process and CK-KICK-012 Batch 7 review brief

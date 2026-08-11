# Adversarial review: DR-0002 revision 6

Target DR: DR-0002

Target revision: 6

Review status: Complete

Execution state: Complete

Batch context: CK-KICK-012 Batch 4 current-revision double review

Review lens: Contract, schema, and hostile-input/security boundaries

Reviewer: Fresh gpt-5.6-sol contract/schema/security reviewer

Reasoning effort: Medium

Independence: Fresh context; separate agent instance; no authorship or edits

Date: 2026-08-11

Recommendation: Revise

Confidence: High

Reviewed commit: 7dba9346c91c59ff99f10b94630690bf732d6b28

This artifact records review evidence only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 6 has a coherent authoritative source-set and resolved-snapshot
boundary, but the envelope and its cross-record admission contract are not yet
executable enough to guarantee deterministic outcomes. The missing algebra,
recognition order, and resource enforcement are primarily owned by
[DR-0012](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
but are required to make the DR-0002 envelope promise complete.

## Prior-blocker closure

The prior classification, articulation, and measurement blockers are closed by
the Batch 4 resolutions in Revision 6. This review does not reopen them.

## Blocking Objections

1. **High — The authoritative envelope lacks a complete outcome/status
   algebra and precedence.**

   **Failure scenario:** The record names one envelope and ordered diagnostics,
   but does not define mappings or precedence for parser, schema, contract,
   dependency, resource, semantic, or unsupported failures; primary
   diagnostic selection; multi-fault accumulation; or diagnostic truncation.
   Consumers can therefore disagree about the envelope status or the
   diagnostic that explains it, including when an earlier phase and a later
   phase both fail. The three-way Stage 1 fixture taxonomy must remain distinct
   from parser/resource/dependency fixture outcomes.

   **Recommended resolution:** Define the complete status/category algebra,
   phase precedence, primary-diagnostic rule, deterministic multi-fault order,
   and bounded diagnostic behavior in DR-0012 while preserving this envelope
   as the sole status authority.

2. **High — Contract recognition and schema bootstrap order is unresolved.**

   **Failure scenario:** A resolver can choose different behavior for a
   missing, malformed, duplicate, unknown-family, or unsupported-revision
   discriminator because the minimum discriminator grammar, duplicate-key
   admission, contract-identity extraction, and schema selection order are not
   fixed. This makes the source-set admission boundary and unsupported outcome
   non-deterministic.

   **Recommended resolution:** Specify the sequence as minimum discriminator
   grammar, strict JSON/duplicate admission, contract identity extraction and
   validation, schema selection, then revision-schema validation, with explicit
   outcomes for each recognition failure.

3. **Medium — Resource limits lack minimum enforcement semantics.**

   **Failure scenario:** DR-0002 delegates resource limits to DR-0012, but a
   profile can still promise hostile-input safety without stating when byte
   decoding/tokenization, number-token validation, nesting/member accounting,
   dependency or expansion charging, and diagnostic/memory exhaustion are
   charged and reported. The same source can then consume unbounded work or
   produce different outcomes across implementations.

   **Recommended resolution:** Define minimum enforcement points and a bounded
   resource diagnostic/outcome; concrete numeric values may remain profile
   detail and must be recorded with results.

4. **Medium — Secondary architecture wording is stale against the selected
   boundary.**

   The architecture references still contain open-format/schema wording and
   one-socket Attachment wording, while the selected contracts are strict JSON
   with Draft 2020-12 structural validation and host/mating Socket roles.
   Align those secondary references with the canonical records so the
   source-set and graph boundary is not contradicted by navigation material.

## Non-blocking Risks

The review records these later obligations without treating them as resolved:
exact JSON dialect/vocabulary, UTF-8/BOM/Unicode/numeric fixtures; extension
details; canonical frames and tolerances; exact dependency-revision meaning;
the cross-DR fixture matrix; hostile-input fuzz/fixture evidence; and a JSON
parser/schema security specialist pass.

## Conditions for Acceptance

Resolve the envelope algebra and recognition/resource dependencies above,
align the secondary architecture wording, and preserve the distinction between
Stage 1 semantic outcomes and parser/resource/dependency outcomes. Ben's owner
disposition and the required current-revision review evidence remain governed
by the repository process.

## Review Limitations

Fresh, read-only conceptual review of the exact commit. No resolver, parser,
schema, fixture, fuzz, benchmark, validation, or specialist security evidence
was available.

## Documents Consulted

- [DR-0002 Revision 6](../DR-0002-declarative-body-document-source-of-truth.md)
- [DR-0008 Revision 6](../DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)
- [DR-0011 Revision 2](../DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)
- [DR-0012 Revision 1](../DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
- Decision-record review process and CK-KICK-012 Batch 4 resolutions

# Adversarial review: DR-0012 revision 11

Target DR: DR-0012

Target revision: 11

Review status: Complete

Execution state: Complete

Coverage: Complete

Batch context: CK-KICK-012/013 Batch 13 current-revision Double review

Review lens: Diagnostics/bootstrap, readiness security, build reproducibility,
adapter algebra/tier, status/reversibility/proportionality

Reviewer: Fresh gpt-5.6-sol

Reasoning effort: Medium

Independence: Fresh context; separate independent pass; no authorship or edits

Date: 2026-08-13

Recommendation: Revise

Confidence: High

Reviewed commit: `8c38c501eb1262a1b85af0b8605220625601772f`

This artifact records evidence and recommendations only. It accepts no product,
specification, architecture, or decision-record proposal.

## Executive Assessment

Revision 11 gives bootstrap diagnostics a sole owner and keeps implementation
binding separate from fixture payloads. The parser/bootstrap and later
Readiness transaction still need filesystem-safe closure, bit-exact numeric
normalization, and an explicit status distinction for malformed versus
unsupported adapter profiles.

## Blocking Objections

1. **High — P1 (cross-linked to DR-0006/DR-0013):** The implementation binding
   has no mechanically enforceable symlink/special-file/ancestor no-follow
   profile. A source path can escape the reviewed tree or change between stat
   and read. Require repository-root anchoring, regular-file-only entries and
   ancestors, no-follow stat/open consistency, and a symlink-escape fixture.
2. **Medium — P2 (cross-linked to DR-0011):** Normalization, sign, adapter, or
   narrowing can recreate `-0` after source lexical normalization, changing
   canonical values and digest bytes. Require `+0` canonicalization after every
   produced zero and before comparison/serialization, with raw-bit fixtures.
3. **Medium — P3 (cross-linked to DR-0013/diagnostics):** A recognized malformed
   adapter scale/profile has no explicit result classification. Distinguish
   malformed profile/request, unknown unsupported revision, and trusted
   conversion failure (`output-failure` where owned), and fixture `s=0`,
   negative/nonfinite, unknown revision, and conversion-failure cases.

## Non-blocking Risks

The bootstrap registry/profile remains conceptual until exact code and field
fixtures are admitted. No parser, resolver, adapter, or readiness gate is
activated by this review.

## Conditions for Acceptance

Coordinate P1 with the implementation-binding and platform owners, add P2's
bit-level canonicalization rule, and make P3's status algebra explicit in the
operation/diagnostic owners. Preserve the bootstrap fallback and the separate
fixture and implementation content scopes.

## Review Limitations

No parser, bootstrap registry, readiness preflight, filesystem harness,
adapter implementation, or diagnostic fixture corpus was available. This pass
does not choose status code spellings, profile IDs, target precision, or a
no-follow API.

## Documents Consulted

- DR-0012 Revision 11 and linked current DRs
- Body-document, body-graph, diagnostics, fixture-manifest, build-operation,
  canonical-data, and numeric-frame specifications
- Architecture, product, project status, registry, repository-evolution, and
  Batch 12 review artifacts

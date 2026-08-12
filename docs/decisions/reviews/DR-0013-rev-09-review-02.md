# Adversarial review: DR-0013 revision 9

Target DR: DR-0013

Target revision: 9

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

Revision 9 improves the post-Readiness-3 adapter algebra and preserves a
separate implementation binding. The proposed platform still lacks the
filesystem trust rules, bit-level zero normalization, and explicit adapter
profile/status algebra needed for reproducible, fail-closed activation.

## Blocking Objections

1. **High — P1:** The implementation binding does not define symlink,
   special-file, or ancestor no-follow rules and does not require stat/open
   consistency. A repository source symlink can point to mutable or
   out-of-tree content while the binding appears unchanged. Require
   repository-root-anchored regular files, reject symlinks/special files in
   entries and ancestors, use no-follow reads, and add a symlink-escape
   fixture.
2. **Medium — P2 (cross-linked to DR-0011/DR-0006):** Quaternion normalization,
   sign selection, adapter operations, or narrowing can recreate `-0` after
   lexical normalization and alter canonical tuple bits/digests. Canonicalize
   every produced zero to `+0` after those operations and before tuple/
   serialization; add bit-level fixtures.
3. **Medium — P3 (cross-linked to diagnostics/build-operation):** A recognized
   malformed adapter scale/profile value has no explicit status. Distinguish
   malformed profile/request from unknown unsupported profile revision and
   trusted conversion failure (`output-failure` where applicable), with
   fixtures for zero, negative, nonfinite, unknown revision, and conversion
   failure.

## Non-blocking Risks

The storage/output-only tier is appropriately narrower than runtime
conformance, but each claimed runtime capability still needs its own probe,
fixture, and reversible successor transaction. No adapter is activated here.

## Conditions for Acceptance

Add the no-follow binding profile and escape fixture, define post-operation `+0`
canonicalization, and make malformed/unsupported/conversion outcomes explicit
in the operation and diagnostic contracts. Preserve the two adapter tiers and
the separate implementation/fixture payload scopes.

## Review Limitations

No implementation-binding preflight, hostile filesystem test, adapter runtime,
diagnostic registry fixture, FTZ/DAZ probe, or benchmark was available. This
pass does not select status code spellings, target precision, or a runtime
conformance claim.

## Documents Consulted

- DR-0013 Revision 9 and linked current decision records
- Numeric-frame, body-document, body-graph, canonical-data, diagnostics,
  fixture-manifest, and build-operation specifications
- Architecture, product, project status, registry, repository-evolution, and
  Batch 12 review artifacts

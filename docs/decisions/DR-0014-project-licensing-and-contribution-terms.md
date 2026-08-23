# DR-0014: Project licensing and contribution terms

ID: DR-0014

Scope: Governance

Status: Accepted

Revision: 2

Decision owner: Ben

Owner approval: Approved by Ben

Review status: Complete

Date proposed: 2026-08-23

Date decided: 2026-08-23

Supersedes: —

Superseded by: —

## Context

Creature Kernel is preparing a repository that may be copied, distributed, and
contributed to. It needs a clear default for project-authored tracked material,
package metadata, and inbound contributions before those activities expand.
Without an explicit project choice, the repository would leave its intended
permissive/open terms and contribution terms ambiguous.

Ben selected the direction recorded here in discussion on 2026-08-23 and,
after the exact Revision 2 review, accepted this record on 2026-08-23. This
record describes project governance and is not legal advice.

## Decision

The accepted project direction selected by Ben is MIT OR Apache-2.0: permissive
and open, with recipients able to use either license. The repository will carry
the canonical full texts in [`LICENSE-MIT`](../../LICENSE-MIT) and
[`LICENSE-APACHE`](../../LICENSE-APACHE), with the collective notice:

```text
Copyright (c) 2026 Creature Kernel contributors
```

The project license applies by default to all project-authored tracked
repository material, including source, documentation, tests, fixtures, examples,
scripts, and metadata. Third-party material, separately licensed repository
assets, and their notices or terms are not relicensed by this decision.

Contributions intentionally submitted for inclusion in Creature Kernel are
accepted under the same MIT OR Apache-2.0 dual terms. No CLA or separate
contributor agreement is required. This contribution policy concerns work
submitted to this project and does not claim ownership or licensing control over
contributors' unrelated work.

### Generated-output boundary

The project license applies to project-authored repository material and does not
by itself impose a license on independently generated outputs. Input rights,
third-party material, and outputs incorporating separately licensed repository
assets remain subject to their own rights and terms. Generated-output ownership,
licensing, and distribution policy are a separate future decision and are not
settled by this record.

This decision does not create a public security contact, NOTICE file, contributor
agreement, trademark policy, release process, or third-party attribution
inventory. It does not make a claim over material that the project did not
author or have the right to license.

## Consequences

- Repository readers can identify the intended license expression from the
  root license files. Cargo package metadata should mirror that expression
  once the exact-bound historical experiment closure permits those manifest
  bytes to change safely.
- Contributors receive a clear inbound contribution term without a CLA, while
  the project must continue to distinguish its own material from third-party
  material and separately licensed assets.
- The dual expression preserves permissive/open reuse and offers a choice of
  the two selected license texts, with the notices and conditions in those
  texts remaining relevant to reuse.
- Independently generated outputs are not automatically assigned a project
  license by this decision, so future workflows must keep input, third-party,
  repository-asset, and output rights distinct.
- The repository does not gain a general relicensing, trademark, release,
  security-contact, or attribution-inventory process from this patch.

## Alternatives Considered

### MIT-only

MIT-only would be short and familiar and would preserve broad permissive reuse.
It was not selected because Ben chose the dual MIT OR Apache-2.0 expression and
the repository should expose that choice consistently in its license files and,
when the frozen manifest binding can be transitioned safely, package metadata.

### Apache-2.0-only

Apache-2.0-only would provide one explicit permissive license text and its
associated terms. It was not selected because the chosen direction retains MIT
as an equally available option for recipients.

### No project-wide choice yet

Leaving the repository unlicensed or deferring the choice would avoid an
immediate policy commitment. It was not selected because it would leave copying,
distribution, and contribution expectations unclear.

### A copyleft, source-available, or custom license

A stronger reciprocity or project-specific license could impose different
conditions or preserve more control. It was not selected because the settled
direction is permissive/open and does not call for those additional conditions.

### A CLA or separate contribution agreement

A CLA could introduce a separate contribution grant or future relicensing
mechanism. It was not selected because Ben explicitly chose contributions under
the same dual terms with no CLA.

## Adversarial Review Response

The exact [Revision 1 review](reviews/DR-0014-rev-01-review-01.md) found two blocking objections: incomplete license
metadata coverage for tracked standalone packages and an incomplete account of
reversibility. Revision 2 resolves those blockers by adding the selected
license expression to both standalone package manifests and clarifying the
limits on changing terms and contributor-owned work below. The exact
[Revision 2 review](reviews/DR-0014-rev-02-review-01.md) recommends `Accept` at
High confidence with no blockers. Ben accepted Revision 2 on 2026-08-23;
Review status is Complete and Owner approval is Approved by Ben.

Post-review integration found that adding the package metadata changes the
exact root, core, and standalone candidate manifest bytes retained by the
parked Phase 3 freeze-manifest test closure. Required CI then fails closed with
`current content mismatch for Cargo.toml`. The metadata edits are therefore
deferred rather than resealing or weakening historical experiment evidence.
This implementation constraint does not change the accepted project license,
contribution terms, or generated-output boundary, and it does not reactivate
Phase 3. The Revision 2 review's Cargo-metadata observation describes the
reviewed pre-integration candidate, not the final manifest state.

Recommended adversarial level: Single — this is a cross-cutting governance and
distribution choice with contribution and generated-output boundaries, while
the selected implementation is a bounded documentation patch with package
metadata explicitly deferred.

## Implementation and Proof Obligations

- Keep the canonical MIT and Apache-2.0 full texts intact and include the
  selected collective notice without paraphrasing the legal text.
- Keep all package records unpublished. Add and verify
  `license = "MIT OR Apache-2.0"` for the two workspace members and both tracked
  standalone packages only after a governed transition allows the exact-bound
  root, core, and standalone candidate manifest bytes to change without
  rewriting historical evidence. Until then the canonical root license files
  carry the project terms.
- Keep README and CONTRIBUTING guidance consistent with the project-authored,
  third-party, contribution, and generated-output boundaries in this record.
- Run `python3 dev-tools/validation/validate_docs.py`, `git diff --check`, and
  the full required CI checks. When the deferred metadata step activates, also
  run `cargo metadata --no-deps --format-version 1` for the root workspace and
  each standalone manifest; inspect all four resulting package records to
  confirm they expose `MIT OR Apache-2.0` and remain unpublished.
- Preserve the exact-Revision-2 adversarial review and owner acceptance with
  the accepted record.

## Canonical Design Links

- [`LICENSE-MIT`](../../LICENSE-MIT) and
  [`LICENSE-APACHE`](../../LICENSE-APACHE) own the full license texts.
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) owns the contributor-facing
  summary.
- [`README.md`](../../README.md) provides the public-facing licensing summary.
- The future package-metadata carriers are [`Cargo.toml`](../../Cargo.toml),
  [`creature-kernel-core/Cargo.toml`](../../crates/creature-kernel-core/Cargo.toml),
  [`creature-kernel-cli/Cargo.toml`](../../crates/creature-kernel-cli/Cargo.toml),
  [`EXP-0002 candidate/Cargo.toml`](../../experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml),
  and
  [`EXP-0002 authored-conflict candidate/Cargo.toml`](../../experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml)
  once the exact-bound closure transition is governed and implemented; they do
  not carry the expression in the current candidate.

## Reversibility and Revisit Triggers

Future versions may adopt changed terms only where the project has sufficient
rights to do so. Permissions already granted for distributed versions under
their applicable license cannot simply be withdrawn. Without a CLA,
contributor-owned work cannot be unilaterally relicensed under unrelated future
terms absent sufficient rights or consent. This is governance language, not
legal advice or a new relicensing process. Revisit this decision if the project
adopts a different distribution model, needs a copyleft/source-available/custom
term, changes how third-party or separately licensed assets are included,
establishes a generated-output workflow that needs an explicit policy, or
encounters a contribution requirement that the current dual terms and no-CLA
policy do not cover. Also revisit the deferred Cargo metadata when the Phase 3
manifest-byte binding is retired or deliberately transitioned. Any revision
must preserve this reasoning and record the changed license, contribution, or
scope boundary.

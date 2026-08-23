# Adversarial review: DR-0014 revision 1

Target DR: DR-0014

Target revision: 1

Review status: Complete

Reviewer: gpt-5.6-sol medium (fresh independent pass)

Independence: Fresh context; independently reviewed the exact current on-disk
Revision 1 patch and did not author or modify the proposal or implementation
files

Date: 2026-08-23

Recommendation: Revise

Confidence: High

## Executive Assessment

Revision 1 selects a conventional and internally coherent `MIT OR
Apache-2.0` direction, scopes it to project-authored tracked material, excludes
third-party and separately licensed material, and avoids claiming that the
project license automatically controls independently generated outputs. The
full Apache-2.0 text is byte-identical to both the installed canonical copy and
the Apache Software Foundation text after the separate collective notice; the
MIT text preserves the SPDX wording after substituting the collective notice,
with line wrapping as the only difference. The two root-workspace packages
both report `MIT OR Apache-2.0` and remain non-publishable.

The direction is reasonable, but Revision 1 is not ready for acceptance. Two
high-value consistency defects remain: two tracked standalone Cargo packages
have no license metadata, and the reversibility section does not acknowledge
the durable effect of already granted licenses or the limits created by
contributor-owned work under a no-CLA policy.

## Blocking Objections

1. **Package-metadata coverage is incomplete.** The implementation obligation
   checks only the root workspace and its two member crates. Direct metadata
   inspection of
   `experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml` and
   `experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml`
   reports `license: null` for both tracked standalone packages, although each
   has `publish = false`. This conflicts with the Context's repository-wide
   package-metadata goal and the Consequences claim that package consumers can
   identify the intended expression from Cargo metadata. Either add the same
   license expression to every current project-authored Cargo package, or
   narrow and justify the metadata claim and proof obligation as applying only
   to root-workspace packages while stating how standalone packages communicate
   their terms.

2. **The reversibility account is materially incomplete.** Saying only that a
   new DR revision can revise the decision can be read as broader reversibility
   than this licensing choice provides. The record should distinguish changing
   terms for future project versions from withdrawing permissions already
   granted for distributed versions, and should acknowledge that the no-CLA
   contribution model does not by itself give the project unilateral authority
   to relicense contributor-owned work under unrelated future terms. This is
   important decision-owner information and should be explicit before
   acceptance.

## Non-blocking Risks

No additional high-value objection was found. The collective notice is
consistent across both license files; README and CONTRIBUTING use the same
dual expression and no-CLA wording; the generated-output language is cautious
rather than an unsupported ownership claim; and no project NOTICE, trademark
policy, public security contact, release commitment, vendored tree, submodule,
or separate project license was found in the inspected current context.
Future third-party additions will still require case-specific notice and term
handling, as Revision 1 already anticipates.

## Conditions for Acceptance

Resolve both blocking objections in the proposal and implementation, preserve
the canonical license texts and project/third-party/generated-output
boundaries, then rerun documentation validation, metadata inspection for the
root workspace and both standalone packages, and `git diff --check`. A material
change to the decision or its consequences should follow the repository's
revision rule and receive review for the resulting current revision.

## Follow-ups

- Have the decision owner choose whether all tracked standalone Cargo packages
  carry explicit `MIT OR Apache-2.0` metadata or whether the DR deliberately
  limits its metadata guarantee to workspace packages.
- Add an accurate prior-release and contributor-rights qualification to the
  reversibility section without expanding into a general relicensing process.
- Before owner disposition, ensure the new license, contribution, decision,
  and review files are included in the intended tracked patch and retain the
  recorded third-party exclusions.

## Review Limitations

This is a technical and governance consistency review, not legal advice, and
the reviewer is not acting as legal counsel. It did not establish ownership of
individual repository files, contributor authority, patent coverage,
jurisdiction-specific enforceability, or the rights status of future inputs or
outputs. The target was the exact uncommitted current on-disk Revision 1 patch;
several licensing files were untracked, so no immutable commit identity was
available. Dependency source trees were not vendored or audited; the review
checked repository scope boundaries and current metadata, not every upstream
dependency license obligation.

## Documents Consulted

- `AGENTS.md`, the documentation authority and required product/architecture/
  status context, the decision process, registry row, and adversarial-review
  template
- DR-0014 Revision 1, `LICENSE-MIT`, `LICENSE-APACHE`, `CONTRIBUTING.md`, and
  the README licensing section
- Root workspace and all four tracked Cargo package manifests, root and
  standalone `cargo metadata` output, tracked-file names, and focused current
  licensing/third-party policy context
- Installed `/usr/share/common-licenses/Apache-2.0`, the Apache Software
  Foundation's published Apache-2.0 text, and SPDX's published MIT text

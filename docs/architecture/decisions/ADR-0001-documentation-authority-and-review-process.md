# ADR-0001: Documentation authority and adversarial review process

ID: ADR-0001

Status: Proposed

Revision: 1

Decision owner: Ben

Owner approval: Pending

Review status: Pending

Date proposed: 2026-08-05

Date decided: —

Supersedes: —

Superseded by: —

## Context

Creature Kernel begins with many consequential graphics, geometry, physics, and
runtime choices outside the project owner's established expertise. A previous
project introduced ADR structure and validation after a large design corpus
already existed, making reconstruction expensive and ambiguous.

The project needs early separation between product outcomes, normative formats,
architecture, rationale, research evidence, implementation status, and proof.
It also needs durable adversarial reviews instead of relying on ephemeral chat.

## Decision

Adopt the authority model in `docs/README.md`, the ADR lifecycle in this
directory, revision-specific adversarial reviews, and lightweight validation.

The human project owner remains the decision owner. Reviewers recommend but do
not decide. Accepted ADRs must identify canonical contracts and proof obligations.

Future repository areas are activated through a repository-evolution ledger
rather than empty implementation scaffolding.

## Consequences

- Consequential decisions become challengeable before implementation hardens.
- Rejected reasoning and accepted risk remain durable.
- Contributors must classify information and maintain links between decisions
  and canonical contracts.
- Some documentation and validation work occurs before code.
- The process can become bureaucratic if trivial implementation details are
  incorrectly escalated to ADRs.

## Alternatives Considered

### Informal Markdown and chat only

Lowest immediate effort, but rationale, objections, and decision state become
difficult to recover or validate.

### Full mature-project governance immediately

Would add machine-validated provenance, complete capability allocation, and
reconciliation machinery. It provides strong controls but is disproportionate
before implementation exists.

### ADRs without separate adversarial reviews

Preserves rationale but makes it easy for proposal authors to review their own
assumptions superficially.

## Adversarial Review Response

Pending review of revision 1.

## Implementation and Proof Obligations

- Maintain authority indexes, registry, templates, and status vocabulary.
- Validate required documents, ADR metadata, headings, registry membership, and
  local links.
- Add revision-aware review validation before accepting the first ADR.
- Review whether the process is producing useful challenge after several decisions.

## Canonical Design Links

- [Documentation authority](../../README.md)
- [ADR process](README.md)
- [Repository evolution](../../project/repository-evolution.md)
- [Contributor instructions](../../../AGENTS.md)

## Reversibility and Revisit Triggers

The process is documentation and tooling, so it is reversible. Revisit if ADR
overhead delays small decisions, reviewers cannot distinguish canonical owners,
validation becomes costly, or important choices still bypass review.

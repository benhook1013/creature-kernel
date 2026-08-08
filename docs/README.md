# Documentation authority and navigation

Status: Active

This index defines where Creature Kernel information belongs and which sources
are authoritative. The repository deliberately separates intent, contracts,
rationale, evidence, and status.

## Reading order

1. [Project overview](../README.md)
2. [Vision and scope](product/vision-and-scope.md)
3. [Requirements](product/requirements.md)
4. [Architecture index](architecture/README.md)
5. [Current project status](project/status.md)
6. Any relevant specifications, ADRs, research questions, experiments, and
   [developer workflows](developer-workflows/README.md)

The [foundation record](FOUNDATION.md) preserves the founding conversation. It is
historical context rather than the canonical owner of current contracts.

## Authority map

```text
Product outcomes and user workflows
                |
                v
Normative specifications and semantics
                |
                v
Target architecture and invariants
          |                 |
          | ADR rationale   | research and experiment evidence
          v                 v
Implementation and verification status
                |
                v
Code, tests, fixtures, benchmarks, and runtime proof
```

| Area | Owns | Does not own |
| --- | --- | --- |
| `docs/product/` | Outcomes, scope, users, observable requirements | Algorithms and component layout |
| `spec/` | Formats, semantics, identifiers, versioning, compatibility | Product priority or implementation status |
| `docs/architecture/` | Target boundaries, data flow, invariants, responsibilities | Historical rationale or proof status |
| `docs/architecture/decisions/` | Consequential decision rationale | The current contract by itself |
| `docs/research/` | Open questions, hypotheses, references | Accepted target state |
| `experiments/` | Reproducible evidence and limitations | Product or architecture authority |
| `docs/developer-workflows/` | Conditional contributor and review procedures | Product or technical contracts |
| `docs/project/` | Roadmap, current status, repository evolution | Product or technical contracts |
| Code and proof | What exists and what has been demonstrated | Intended behaviour not yet implemented |

## Conflict rule

If two documents appear to define the same contract differently, stop and fix
the canonical owner. Secondary documents should link to the owner and describe
only their local consequence.

An ADR must update or identify the canonical documents affected by an accepted
decision. An experiment can justify an ADR but cannot silently change a contract.

## Status language

Use precise status words:

- **Decision:** `Candidate`, `Proposed`, `Under Review`, `Accepted`, `Rejected`,
  `Superseded`, or `Withdrawn`.
- **Repository evolution:** `active`, `planned`, `triggered`, `deferred`,
  `not-applicable`, or `retired`.
- **Implementation:** `implemented`, `partial`, `not-implemented`,
  `design-unresolved`, or `not-applicable`.
- **Verification:** `proven`, `audited`, `unverified`, `drift-found`, or
  `not-applicable`.
- **Experiment:** `planned`, `running`, `complete`, `inconclusive`, or `abandoned`.

Do not use `done` where implementation and verification need separate answers.

## Generated and binary material

Generated documentation must name its authoritative source and regeneration
command. Large binary artifacts require an explicit storage decision; ordinary
Git history is not the default home for simulation caches or rendered datasets.

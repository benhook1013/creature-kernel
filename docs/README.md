# Documentation authority and navigation

Status: Operational under Accepted DR-0001 Revision 5

This index defines where Creature Kernel information belongs and which sources
are authoritative. The repository deliberately separates intent, contracts,
rationale, evidence, and status.

## Reading order

1. [Project overview](../README.md)
2. [Vision and scope](product/vision-and-scope.md)
3. [Requirements](product/requirements.md)
4. [Architecture index](architecture/README.md)
5. [Current project status](project/status.md)
6. Any relevant specifications, decision records, research questions, experiments, and
   [developer workflows](developer-workflows/README.md)

The [foundation record](FOUNDATION.md) preserves the founding conversation. It is
historical context rather than the canonical owner of current contracts. This
authority map and its process operate under Accepted DR-0001 Revision 5. That
acceptance applies to governance only; linked product, specification, and
architecture proposals remain provisional and require Ben's disposition.

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
          | Decision rationale | research and experiment evidence
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
| `docs/decisions/` | Consequential decision rationale across Governance, Product, Specification, and Architecture | The current contract by itself |
| `docs/research/` | Open questions, hypotheses, references | Accepted target state |
| `experiments/` | Reproducible evidence and limitations | Product or architecture authority |
| `docs/developer-workflows/` | Conditional contributor and review procedures | Product or technical contracts |
| `docs/project/` | Roadmap, current status, repository evolution | Product or technical contracts |
| Code and proof | What exists and what has been demonstrated | Intended behaviour not yet implemented |

## Navigation ownership

Every durable Markdown document must be listed from exactly one owning-area
index. Cross-links may be many; they do not transfer ownership. Numbered
decision records are indexed by the [decision registry](decisions/registry.md),
and review artifacts are indexed by the target DR's adversarial-review response.
This is an ownership and indexing rule, not a ban on cross-links.

## Conflict rule

If two documents appear to define the same contract differently, stop and fix
the canonical owner. Secondary documents should link to the owner and describe
only their local consequence.

A decision record must update or identify the canonical documents affected by an
accepted decision. An experiment can justify a decision record but cannot
silently change a contract.

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
- **Experiment lifecycle:** `planned`, `running`, `finished`, or `abandoned`.
- **Evidence closure:** `open`, `complete`, or `incomplete`.
- **Technology outcome:** `none`, `support`, `reject`, or `inconclusive`.

Experiment workflow uses these three independent fields. `planned` and
`running` experiments have `open` evidence closure and `none` technology
outcome. A `finished` experiment may calculate `support`, `reject`, or
`inconclusive` only when evidence closure is `complete`; an experiment that
ends without closure is `finished` or `abandoned` with `incomplete` closure
and `none` outcome. An `abandoned` experiment always has `incomplete` closure
and `none` outcome. Only `complete` evidence closure permits a technology
outcome or feasibility annotation.

The first-surface experiment workflow also closes actual work through finite
`C`, `I`, `S`, `B`, `G`, and branch-integration ledgers. `C` is the universal
scaffold and shared-repair ledger: before branch work, its admission test
requires every branch to receive the same interface, data, and access, with
no branch-specific construction logic or parameters. Registration freezes an
immutable base scaffold manifest and ID, provenance, source, assets, known
effort, finite cap, and budget identity; the checkpoint and base manifest do
not move or mutate. A qualifying post-checkpoint repair is one append-only
finite repair-log entry with a stable ID, provenance/source/assets, known or
unavailable historical effort, cap consumption, and affected-evidence
declaration. Each evidence item references the base manifest ID plus the exact
repair-log snapshot ID, including an explicit empty snapshot before repairs;
affected evidence is rerun after a repair. No numeric cap, ID syntax, or
storage format is selected here. Unknown historic effort is unavailable, not
zero. Failure or exhaustion of `C` is a shared terminal and makes the
comparative result `inconclusive`. `I`, `S`, `B`, and `G` failures affect only
consuming branches; integration failures affect their branch. Full `C` effort
is reported separately from actual-once work and attributed branch cost, and
feasibility is scoped to the base manifest ID, exact repair-log snapshot ID,
and registered attributed branch budget ID. Outcome wording uses branch/failure
attribution; component matrix
`U` cells remain visible and do not by themselves block bundle `Support`. See
the [experiment workflow](../experiments/README.md) for the recording
procedure.

Do not use `done` where implementation and verification need separate answers.

## Generated and binary material

Generated documentation must name its authoritative source and regeneration
command. Large binary artifacts require an explicit storage decision; ordinary
Git history is not the default home for simulation caches or rendered datasets.

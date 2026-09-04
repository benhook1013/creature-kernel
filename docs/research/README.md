# Research documentation

Status: Active

Creature Kernel contains graphics and physics questions that cannot be resolved
credibly through architecture prose alone. This area owns open questions,
hypotheses, references, and research context.

## Documents

- [Open questions](open-questions.md)
- [First host runtime evaluation](first-host-runtime-evaluation.md) — the
  2026-08-25 official-source comparison of Godot 4.7.2, Unity 6.3 LTS, Unreal
  Engine 5.8, and Bevy 0.19, plus a 2026-09-04 follow-up covering the completed
  bounded Godot trial and Bevy's remote-control, community AI, and physics
  ecosystem. No permanent host is selected; RQ-062 remains open.
- [Reference index](references.md)
- [Provisional morphology-knowledge inventory and pilot dossiers](morphology-knowledge-inventory-and-pilot-dossiers.md) — research-only
  inventory and exactly two selected anatomy pilots for the five-profile
  checkpoint.
- [Visual-quality evaluation protocol](visual-quality-evaluation.md)
- [First surface experiment design](first-surface-experiment-design.md) — a
  Proposed, neutral evidence design; EXP-0001 is not registered and no
  evidence exists yet.
- [Programmatic root-complex surface investigation](programmatic-root-complex-surface-investigation.md) — a
  Ben-authorized, experiment-local, pre-Readiness-4 candidate plan; it is
  non-normative and does not activate DR-0009/0010 or replace DR-0013 Stage 1
  proof.
- [Numeric and frame profile experiment design](numeric-frame-profile-experiment.md) —
  planned and unregistered evidence for numeric admission, exact dyadic/ULP
  boundaries, deterministic normalization and offline half-chord derivation,
  typed comparisons, claim identity/order, future adapter scale/tier probes,
  and error budgets; no results or evidence exist.
- [Experiment workflow](../../experiments/README.md)

## Authority rule

Research documents are intentionally non-normative. A paper, prototype, or
experiment can support or challenge a proposal but does not change product,
specification, or architecture contracts automatically.

Research-question lifecycle is distinct from experiment lifecycle. Use the
question labels above for questions; use the three experiment fields and
constraints in the [experiment workflow](../../experiments/README.md) for
registered runs. Do not use a question state such as `Answered for current
scope` as an experiment outcome, or an experiment state as a question state.

## Question lifecycle

Use:

- `Open`: unresolved and relevant.
- `Experiment planned`: a registered experiment targets the question.
- `Partially answered`: evidence narrows the space without closing it.
- `Answered for current scope`: sufficient for a bounded decision.
- `Deferred`: not currently worth investigating.
- `Invalidated`: the question relied on a rejected assumption.

Closing a question should link the evidence and any resulting decision record.

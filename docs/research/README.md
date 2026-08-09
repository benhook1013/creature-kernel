# Research documentation

Status: Active

Creature Kernel contains graphics and physics questions that cannot be resolved
credibly through architecture prose alone. This area owns open questions,
hypotheses, references, and research context.

## Documents

- [Open questions](open-questions.md)
- [Reference index](references.md)
- [Visual-quality evaluation protocol](visual-quality-evaluation.md)
- [First surface experiment design](first-surface-experiment-design.md) — a
  Proposed, neutral evidence design; EXP-0001 is not registered and no
  evidence exists yet.
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

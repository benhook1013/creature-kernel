# Experiments

Status: Active workflow; no experiments registered

Experiments provide reproducible evidence for research questions and decisions.
They do not become product or architecture contracts automatically. Research
question lifecycle is separate: a question may be `Open`, `Experiment
planned`, `Partially answered`, `Answered for current scope`, `Deferred`, or
`Invalidated`; those labels do not replace experiment fields below.

## Canonical experiment fields

Every experiment records three independent fields:

- **Experiment lifecycle:** `planned | running | finished | abandoned`.
- **Evidence closure:** `open | complete | incomplete`.
- **Technology outcome:** `none | support | reject | inconclusive`.

Use these constraints:

- `planned` and `running` require `open` evidence closure and `none`
  technology outcome.
- `finished` with `complete` evidence closure may record `support`, `reject`,
  or `inconclusive` and may carry a feasibility annotation.
- An experiment that ends without closure is `finished` or `abandoned` with
  `incomplete` evidence closure and `none` technology outcome.
- `abandoned` always has `incomplete` evidence closure and `none` technology
  outcome.
- Only `complete` evidence closure permits a technology outcome or feasibility
  annotation.

`none` means that no technology outcome is calculated. Outcome wording records
branch or failure attribution; a component `U` cell does not by itself block a
bundle `support` outcome. `NA` is a separate not-applicable cell state, not
`U`, and is excluded from applicable-cell coverage.

## Actual-work ledgers

Closed actual work is recorded exactly once in finite `C`, `I`, `S`, `B`, `G`,
or branch-integration ledgers. `C` is the universal scaffold/shared-repair
ledger and its pre-branch operational admission test requires all branches to
have the same interface, data, and access, with no branch-specific
construction logic or parameters. Registration freezes an immutable base
scaffold manifest and ID, provenance, source, assets, known effort, finite cap,
and budget identity. The checkpoint and base manifest do not move or mutate.
After the checkpoint, a qualifying universal repair is one append-only finite
repair-log entry with a stable entry ID, provenance/source/assets, known effort
or unavailable historical effort, cap consumption, and affected-evidence
declaration. Each evidence item references the base manifest ID plus the exact
repair-log snapshot ID, including an explicit empty snapshot before repairs;
affected evidence is rerun after a repair. No numeric cap, ID syntax, or
storage format is selected by this workflow. Unknown historic effort is
unavailable, not zero. Failure or exhaustion of `C` is a shared terminal and
makes the comparative result `inconclusive`; failures in `I`, `S`, `B`, or `G`
affect only their consuming branches, while integration failure affects its
branch. Record full `C` effort separately from actual-once total work and
attributed branch cost. Feasibility annotations are scoped to the immutable
base manifest ID, exact repair-log snapshot ID, and registered attributed
branch budget ID.

Register ledger IDs, scope, caps, and terminal rules before branch work. Keep
branch-attributed cost as the sum of required capability ledgers plus branch
integration, while actual total work counts each item once. Do not silently
remove a branch or convert unavailable historic effort into zero.

## Registration

Use a stable directory name:

```text
experiments/EXP-NNNN-short-title/
├── README.md
├── inputs/              # small committed inputs when appropriate
├── scripts/             # reproduction and analysis
└── results/             # small textual summaries; large artifacts external
```

Copy [the experiment template](experiment-template.md). Add a future registry
when the first experiment is created.

## Required properties

- Target research question IDs.
- A falsifiable or decision-relevant hypothesis.
- Explicit inputs, versions, configuration, and random seeds.
- Hardware and software environment when performance is involved.
- Metrics and thresholds selected before results where practical.
- Reproduction commands.
- Raw result location and retention policy.
- Limitations, failed runs, and negative evidence.
- Decision impact stated as a recommendation, not an automatic contract change.

## Artifact policy

Large meshes, caches, videos, captures, and datasets must not be committed until
an artifact-storage DR is accepted. Store small text, scripts, fixtures, hashes,
and manifests in Git so external artifacts remain attributable.

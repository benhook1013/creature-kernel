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

`none` means that no technology outcome is calculated. Specific activated
protocols may define additional outcome or attribution states, but the generic
workflow does not prescribe comparative ledgers or adjudication machinery.
Link the activated protocol from the experiment record when those rules are
needed.

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

Exploratory prototypes may use this workflow without registering a confirmatory
experiment. They should label observations and limitations clearly and must not
claim formal comparative support or reject under the parked surface protocol.

## Artifact policy

Large meshes, caches, videos, captures, and datasets must not be committed until
an artifact-storage DR is accepted. Store small text, scripts, fixtures, hashes,
and manifests in Git so external artifacts remain attributable.

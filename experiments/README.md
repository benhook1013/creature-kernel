# Experiments

Status: Active workflow; EXP-0002 remains planned with open evidence closure
and technology outcome `none`; its phase-one attempt-001 evidence is complete
and passed, while broader experiment obligations remain open.

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

Copy [the experiment template](experiment-template.md). Keep the registry
below current as experiments are created.

## Registered experiments

- [EXP-0002 numeric/frame profile](EXP-0002-numeric-frame-profile/README.md) —
  registered four-operation phase-one exact-artifact persistent-conformance
  package; one persistent candidate is specified to receive the frozen
  development, held-out, and adversarial roles in order. Its 49 exact frozen
  case adjudications and runner classifications for 26 registered named case
  groups, manifest identities, bounded runner, synthetic checks, and one-shot
  receipt wrapper are implemented and frozen. Attempt-001 passed all 49 cases
  and 26 registered relations at source commit
  `d88f5eca3ad3c0c0cb00dcf7dd012471be979305`; see the package's
  [human-readable results summary](EXP-0002-numeric-frame-profile/RESULTS.md).
  Overall experiment remains planned, evidence closure open, and technology
  outcome `none` because broader obligations remain.
  The [authored-conflict successor preregistration](EXP-0002-numeric-frame-profile/phase2-authored-conflict/README.md)
  is a separate draft-only, non-executing preflight package.

The phase-one claim is limited to 49 exact frozen case adjudications plus
runner classifications for 26 registered named case groups, including
represented boundary/resource/error/environment observations. Only
`lexical-equivalence`, `signed-zero-canonicalization`, and `environment-repeat`
have explicit cross-case checks; the other groupings organize member-case
outcomes. Held-out is non-tuning, not blind or process-isolated. This package
cannot establish role isolation, fresh-process behavior, order independence,
repeatability, broad generalization, profile selection, a production-domain
claim, or a technology outcome. See the
[package README](EXP-0002-numeric-frame-profile/README.md) for the
preregistered identity, resource budgets, and classification rules.

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

The disposable exploratory current-form surface preview, when present at
`experiments/current-form-surface-preview/`, is an unregistered current-source
bridge for a human visual appraisal. It is not `EXP-0001`, does not register an
experiment, and cannot activate Readiness 3/4, Stage 1, DR-0009/0010, a
production geometry backend or seam, or any rigging, animation, collision,
deformation, or runtime claim.

The [programmatic root-complex surface trial](programmatic-root-complex-surface/README.md)
is an unregistered exploratory pre-Readiness-4 trial from the Active runway.
It is not `EXP-0001` and does not calculate formal support or reject. Its
candidate-local frozen contract, neutral-first visual checkpoint, and
experiment-local launcher are not product, Stage 1, production, or formal
surface-comparison authority.

The [owned root assembly successor](owned-root-assembly-successor/README.md)
is the unregistered exploratory successor targeting open `RQ-002`, `RQ-012`,
`RQ-020`, and `RQ-021`. It is not `EXP-0001`; its candidate-local design
contract is frozen and SHA-256-bound, and its bounded implementation phase is
active at `correction_round=0`. It cannot establish a formal technology
outcome, production surface contract, or Stage 1 result.

## Artifact policy

Large meshes, caches, videos, captures, and datasets must not be committed until
an artifact-storage DR is accepted. Store small text, scripts, fixtures, hashes,
and manifests in Git so external artifacts remain attributable.

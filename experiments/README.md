# Experiments

Status: Active workflow; no experiments registered

Experiments provide reproducible evidence for research questions and decisions.
They do not become product or architecture contracts automatically.

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
an artifact-storage ADR is accepted. Store small text, scripts, fixtures, hashes,
and manifests in Git so external artifacts remain attributable.

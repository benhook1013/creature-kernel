# EXP-0002 successor: authored-conflict preregistration

This is the smallest non-executing successor slice for the R3 authored-root
versus Attachment-derived placement comparison. It validates a strict draft
manifest and prints a deterministic preflight plan; it does not run a
candidate, inspect the frozen phase-one corpora, select numeric constants, or
create a result or receipt.

The draft preserves the mechanics already decided for this successor:

- one separately content-bound authored-conflict comparison profile;
- development, held-out, then adversarial corpus roles, with held-out
  non-tuning;
- a new candidate/evaluation identity after failure or inconclusive evidence;
- explicit `agree`, `conflict`, and `skipped` outcomes alongside
  `incomplete` and `unsupported` classifications;
- fail-closed identity mismatch and no successful snapshot after an admitted
  conflict; and
- five representative morphology-boundary fixture roles, whose concrete source
  files remain gated.

The exact profile ID and constants, validation margin and formula, concrete
candidate and corpora, result/receipt identities, morphology request schema,
and resolver/build activation bindings remain unbound. This package therefore
cannot activate Readiness 3.

The standalone [phase-2 candidate](candidate/README.md) provides the bounded
JSONL transport and inspectable observations over the merged provisional
bridge. The provisional candidate retains and projects typed causes plus
equation inputs and steps, but the profile, corpus, result, receipt, resolver,
and R3 activation bindings remain absent and non-authoritative; those missing
bindings still block authoritative corpus/profile freezing.

## Safe preflight

From the repository root:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/preregister.py \
  --manifest experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/preregistration.json \
  --preflight-only
```

The default invocation is also non-executing. `--execute` is rejected rather
than being a dormant execution switch. The plan hashes only the three declared
canonical design references; it does not read phase-one JSONL corpora. Reference
paths reject symlink components and are checked for local replacement while
streaming. This is controlled-local change detection, not a claim of safety
against an adversarial filesystem.

## Development diagnostic run

The authored development corpus has a lean, non-authoritative adjudicator and
runner. Build the candidate explicitly, then pass its executable as an argv
input; the runner does not build, discover, or invoke a shell command:

```bash
cargo build --manifest-path experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml --locked --offline
PYTHONPATH=experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts \
  python3 experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/run_development.py \
  --candidate experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/target/debug/exp-0002-r3-authored-conflict-candidate
```

The command emits one bounded JSON diagnostic report to stdout for exactly 16
cases × 3 development profiles. It is marked `non_authoritative: true`,
`profile_selection: none`, and `r3_activation: inactive`; it is not an
experiment result, evidence, receipt, snapshot, admission, resolver output,
or activation artifact. A nonzero exit indicates a mismatch, incomplete
adjudication, candidate/transport failure, or report failure.

Focused checks:

```bash
python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts \
  -p 'test*.py'
python3 -m py_compile \
  experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/*.py
```

# EXP-0002 successor: authored-conflict development package

PR #65 (merged at `9bcf2172d0433d35d2d96e6841a83890899d11e9`) adds the
development-only phase-two authored-conflict runner for the R3 authored-root
versus Attachment-derived placement comparison. It includes the exact
unselected strict/micro/stress development sweep, a 16-case authored-conflict
development corpus, bounded JSONL transport, and a 16-case × 3-profile (48
request) adjudicator/runner with CI. The actual run passed all 48 requests:
18 `agree`, 15 `conflict`, 12 `skipped`, and 3 `rejected`; its report was under
128 KiB. This run selects no profile, supplies no held-out or adversarial
evidence, and does not activate Readiness 3.

The run is insufficient to choose strict, micro, or stress. Its discriminating
cases are synthetic scalar ladders plus two tiny direct socket-rotation
thresholds; it lacks realistic composed transforms, unit/basis conversion,
descendant paths, and independent equation-output verification. A separate
development-only extension now covers that gap: one deterministic three-Part
descendant-tail variant and six realistic-transform/oracle cases. Its exact
corpus identity and values are frozen in its own package; no profile is
selected.

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

The separate [development extension](corpora/development-extension/README.md)
executes those six cases against the same three profiles (18 requests). Its
cases combine centimetre units, a left-handed signed basis, a three-Part
descendant tail path, and non-identity half-turn rotations. An independent
exact-rational oracle checks the complete placement witness, not only the
classification. The candidate run passed 18/18 requests: 9 `agree` and 9
`conflict`. Hands-on trial and adversarial review found and covered
quaternion-sign canonicalization, source-derived document-identity, and
report-algebra defects. This remains non-authoritative development evidence:
it selects no profile and does not activate Readiness 3.

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

Repeatable candidate arguments use `--candidate-arg VALUE`; for an option-like
value, use the unambiguous form `--candidate-arg=--foo`. The candidate path and
arguments are passed as an argv sequence, never as a shell string.

The command emits one bounded JSON diagnostic report to stdout for exactly 16
cases × 3 development profiles. It is marked `non_authoritative: true`,
`profile_selection: none`, and `r3_activation: inactive`; it is not an
experiment result, evidence, receipt, snapshot, admission, resolver output,
or activation artifact. A nonzero exit indicates a mismatch, incomplete
adjudication, candidate/transport failure, or report failure.

This is controlled-local diagnostic execution, not an OS process sandbox. The
explicit candidate is trusted and must not daemonize, call `setsid`, change
session, or intentionally leave descendant processes. Ordinary group-contained
hangs or children and terminal integrity are bounded and detected by the
transport; OS-level containment of hostile or escaping descendants is out of
scope. No cgroup or job-object machinery is provided.

Focused checks:

```bash
python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts \
  -p 'test*.py'
python3 -m py_compile \
  experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/scripts/*.py
```

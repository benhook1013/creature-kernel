# EXP-0002 phase-one runner

This directory contains the standard-library Python runner for the frozen,
unrun phase-one corpus package. It is research tooling, not a production CLI
or profile selector.

`run_adapter.py` is the entrypoint. `runner_schema.py` loads the exact
manifest/corpus schema and performs hash, byte, ordering, relation,
disjointness, and preflight checks. `runner_oracle.py` independently computes
the exact decimal and scalar/translation Fraction/dyadic expectations.
`runner_transport.py` provides deadline-bounded JSONL subprocess I/O with
stdout/stderr caps, one-response enforcement, trailing-output rejection, and
safe cleanup. `runner_common.py` contains strict JSON and protocol helpers.

The manifest preregisters the stable evaluation binding
`ck.exp-0002.phase1-persistent-conformance-v1`. Phase one uses exactly one
persistent candidate process and sends development, held-out, then adversarial
cases. Held-out is non-tuning evidence, not blind or process-isolated; the
environment observations are conditioned on workload position. The claim is
limited to 49 exact frozen case adjudications plus runner classifications for
26 registered named case groups. Only `lexical-equivalence`,
`signed-zero-canonicalization`, and `environment-repeat` have explicit
cross-case checks; the other groupings organize member-case outcomes. It makes
no fresh-process, order-independence, repeatability, generalization, profile,
production-domain, or technology claim. The existing A/R tolerance entries
are bound as experiment inputs only; no profile is selected.
The environment-repeat relation is labelled as a workload-position-conditioned
capability observation, not a repeatability or order-independence claim.

The preregistration identity object is:

```text
candidate_artifacts = stream-hashed-before-and-after-execution
runner_modules = stream-hashed-before-and-after-execution
filesystem_assumption = controlled-local-no-adversarial-mid-run-replace-and-restore
candidate_build_context = observational-not-provenance
```

The identity-artifact read budget is 268435456 bytes (256 MiB). This is a
pragmatic controlled-local pre/post content-and-stat stability check, not proof
against an adversarial replace-and-restore during execution; the binary hash
remains the artifact identity. Result files retain the binding,
profile-null/technology-`none` state, manifest and corpus hashes, candidate
command/artifact hashes, runner bundle and configured budgets, plus available
toolchain and source identity. A dirty Git tree is recorded explicitly rather
than preventing a local run. Candidate build context is observational, not
provenance. Exact expected mismatches are completed-but-failed conformance
evidence; environment failure/unsupported and candidate unsupported are
inconclusive capability evidence only when no failure exists; transport,
nonzero-exit, and response-integrity failures are incomplete. A completed
execution remains `run_status: complete`; any exact failure takes evidence
precedence over inconclusive/unsupported while counts retain both. No result
can select or reject a production profile.
The runner Python toolchain is separate from candidate build context. Where
available, candidate context hashes `rust-toolchain.toml`, `Cargo.toml`, and
the workspace `Cargo.lock`, and retains bounded `rustc -Vv`/`cargo -V` output
plus selected build variables. This context does not prove how the candidate
binary was built; the candidate artifact hash is the binary identity.

## One-shot execution and receipt wrapper

`run_phase1_once.py` is a thin orchestration/provenance wrapper around the
existing runner. It is not a second numeric runner and is not evidence by
itself. Its default, help, and `--preflight-only` paths cannot run the
authoritative corpus. `--preflight-only` prints the safe plan, creates no
attempt, and invokes no corpus runner. An authoritative execution requires all
three of `--execute`, `--acknowledge RUN-EXP-0002-PHASE1`, and a new
`--attempt-id` such as `attempt-001` (or a later unused ID).

The wrapper fixes the execution target to `x86_64-unknown-linux-gnu` and the
Cargo dev/debug profile, and uses `--locked --offline`. It records the exact
clean source commit; clean means tracked, staged, and fully covered non-ignored
untracked files are clean. Its synthetic gate runs the runner unit tests,
runner-module compilation, and candidate `cargo test`; the candidate build
must then pass before the one authoritative run. Each attempt is written under:

```text
experiments/EXP-0002-numeric-frame-profile/results/phase1/<full-commit>/<attempt-id>/{result.json,receipt.json}
```

The attempt directory is exclusive and an existing attempt is never
overwritten. A completed authoritative attempt has both `result.json` and
`receipt.json`; a pre-run gate failure may preserve a receipt without a result.
The wrapper does not retry automatically. The receipt records the build and
run commands, target/profile/toolchain, an allowlisted environment, relevant
hashes, exit codes, failure stage, and cross-checks.
`result.json` remains the complete evidence record; the receipt is a compact
execution/provenance record, not a replacement for it. Offline integrity
checks inspect the recorded artifacts and do not rerun the corpus.

Completed failed or inconclusive evidence is retained. A fix or rerun requires
a new source commit and attempt ID and never overwrites an earlier attempt.
The wrapper bounds each validation, build, and authoritative-run command to
180 seconds, version observations to 5 seconds, subprocess stdout/stderr to
65,536 bytes, result JSON to 4 MiB, candidate artifact reads to 256 MiB, and
the receipt to 1 MiB.

Run synthetic checks from the repository root:

```bash
python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/scripts \
  -p 'test*.py'
python3 -m py_compile experiments/EXP-0002-numeric-frame-profile/scripts/*.py
```

The safe preflight command is:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/scripts/run_phase1_once.py --preflight-only
```

For reference, the exact execution command is:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/scripts/run_phase1_once.py \
  --execute --acknowledge RUN-EXP-0002-PHASE1 --attempt-id attempt-001
```

This command performs the one authoritative corpus run after all gates pass;
it is not a wrapper-PR test command. Use it only for an explicitly authorized
run with a clean source commit and an unused attempt ID.

The underlying `run_adapter.py` CLI accepts a candidate command after `--`:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/scripts/run_adapter.py \
  --manifest experiments/EXP-0002-numeric-frame-profile/corpora/manifest.json \
  --output <new-result.json> -- <candidate command and arguments>
```

The candidate receives only the protocol ID, an opaque `wire_request_id`,
operation, and input. Runner-only case IDs, relations, expected values, and
oracle data are not projected. The output path is exclusive-create only and
must not alias an input or candidate executable. No command here has been run
against the frozen corpora.

The runner does not select a profile or produce an experiment outcome. It does
not implement quaternion, transform, basis, claim, snapshot, geometry, or R3
activation evidence.

# EXP-0002: Numeric/frame profile phase-one package

Experiment ID: EXP-0002

Experiment lifecycle: planned

Evidence closure: open

Technology outcome: none

Research question: the numeric/frame profile question described in the
[research design](../../docs/research/numeric-frame-profile-experiment.md).

Related specification: [proposed numeric/frame profile](../../spec/numeric-frame-profile/README.md).

## Status and phase-one boundary

This is a frozen-input, frozen-tooling phase-one package with one completed
attempt. Attempt `attempt-001` ran at source commit
`d88f5eca3ad3c0c0cb00dcf7dd012471be979305`; its result and receipt are indexed
in the [human-readable results summary](RESULTS.md). The exact candidate,
runner, manifest, and three JSONL corpora are identified by their recorded
package/build and content identities. `profile_binding` remains `null` and
`technology_result` remains `none`; the result does not select a profile,
activate Readiness 3, or make a product/technology decision.

The attempt completed with `run_status: complete` and `evidence_status: passed`:
development 10/10, held-out 13/13, adversarial 26/26, 49/49 cases
overall, and 26/26 registered relations. The overall EXP-0002 lifecycle
remains `planned`, evidence closure remains `open`, and technology outcome
remains `none` because broader experiment obligations remain.

Phase one is the named exact-artifact persistent-conformance evaluation
`ck.exp-0002.phase1-persistent-conformance-v1`. One persistent candidate
process receives the development corpus, then the
held-out corpus, then the adversarial corpus, in that order. Held-out means
non-tuning: it is not blind to the operator, process-isolated from development,
or a fresh-process test. Environment observations are therefore conditioned on
the workload position at which they are collected. This topology does not
support claims about role isolation, fresh-process behavior, order
independence, repeatability, broad generalization, profile selection, or a
technology outcome.

The phase-one claim is limited to 49 exact frozen case adjudications plus
runner classifications for 26 registered named case groups, including the
represented boundary, resource, error, and environment observations. Only
`lexical-equivalence`, `signed-zero-canonicalization`, and
`environment-repeat` have explicit cross-case checks; the other groupings
organize member-case outcomes. It is not a production-domain, portability,
runtime, or general numeric/frame profile claim.

The current executable surface covers four operations:

- decimal admission;
- scalar comparison;
- translation comparison; and
- same-process, read-only environment attestation.

Quaternion operations remain unsupported. Later normalization, transform and
basis conversion, composition/inversion, claim identity/all-pairs,
authored/snapshot comparison, and adapter-tier obligations remain outside this
phase.

## Phase-three semantic-band conformance preregistration

The separate [phase-three conformance package](phase3-semantic-band-conformance/README.md)
is Proposed, non-authoritative, and execution-disabled. It tests one candidate
(`ck.provisional-r3-authored-conflict.semantic-band-1`) against one provisional
semantic profile over one standalone authored-versus-Attachment-derived rigid
transform. The declared bands analytically derive the candidate; this phase
does not select tolerances or compare profiles. Strict, micro, and stress remain
historical analytical negative comparisons and are not executed.
Its canonical thresholds are exact dyadic A and exact `2H` from the fixed bits;
`5e-5 m` and `5e-6` are nominal shorthand, and no angular claim is made.

The plan has 40 deterministic scored held-out cases across five families, plus
8 explicit development cases and 12 non-scored controls. The exact
constructions are now materialized as `development-unfrozen` in the
[generator](phase3-semantic-band-conformance/scripts/generate_phase3.py),
[focused test](phase3-semantic-band-conformance/scripts/test_generate_phase3.py),
three [corpora](phase3-semantic-band-conformance/corpora/), [recipe and
artifact manifests](phase3-semantic-band-conformance/manifests/), and
[sqrt vectors](phase3-semantic-band-conformance/sqrt-vectors.json). The
regeneration/check commands and current hashes are recorded in the phase-three
package and machine preregistration. It requires certified case-specific
discrepancy intervals, an independent oracle and witness, two WSL repeatability
attempts, one native consistency attempt, and two current Double review gates
before execution. Outcomes are only supported, failed, or inconclusive
conformance with failed-evidence precedence. Gate A is complete/passed for
this exact development-unfrozen materialization; its current Double review is
recorded in [Review 01](phase3-semantic-band-conformance/reviews/gate-a-review-01-closure-integrity.md)
and [Review 02](phase3-semantic-band-conformance/reviews/gate-a-review-02-numeric-claims.md).
This does not by itself close Gate B. The current v3 successor freeze is
materialized from execution-tool/materialization snapshot
`762b04b8db3397cb1885d94236ad5d47cb321830` under schema
`ck.exp-0002.phase3.freeze-manifest-3`, with manifest SHA-256
`faafe7680fcc3509a245dde6759396a1391e02c40891128ca44d007726adef85`.
It binds the experiment-wide closure tool, exact runtime contract, fixed
binary cap, exact slot reservation, and runtime/platform observations. The v2
freeze and its `Revise` reviews remain historical. The consolidated 296-test
suite passed before new E `762b04b8db3397cb1885d94236ad5d47cb321830`. No
candidate/exact attempt or native dispatch has been executed. The later commit
containing the exact v3 bytes still requires fresh current-revision Gate B
Double review, followed by execution-disabled admission and artifact-custody
preparation. An exact-attempt authorization is created separately only after
Ben explicitly authorizes execution. No loss ranking,
production binding, profile-value validation, product-quality claim, or
Readiness 3 activation follows.

The materialized ledger distinguishes `construction_target` (the exact recipe
magnitude used to construct a case) from source-derived `I_truth` (the metric
computed from the serialized source and its exact numeric lexemes). Current
materialization contains `I_truth` only: translation truth is exact; rotation
truth is a certified interval around the normalized q/-q-equivalent full chord,
not an exact singleton. `I_candidate` and `I_error` are mandatory future
scorer/adjudication outputs after candidate witness data exists; their caps are
preregistered obligations, not current artifacts. Records retain complete
authored and derived contribution lists, exact kappa metadata, and derived
canonical/source quaternions, including non-identity derived rotations.
Request IDs are unique across development, held-out, and controls;
normalized request-content uniqueness is checked across the development/held-out
roles, with controls separately partitioned for their typed and preflight
behavior.

The latest generator correction uses exact-rational dot/norm-squared rotation
truth with 256-bit integer-`isqrt` directed enclosures; decimal text is only
the final outward endpoint encoding. The certified interval radius and error
upper endpoint are capped at `1e-10` full chord. Source-derived admission
recomputes all 60 serialized records and finds 53 admitted, 4 typed controls,
and 3 out-of-domain controls; it certifies `kappa_q <= 2`, records the four
exact zero-quaternion typed locations, and exercises fail-closed negative
component, sum, quaternion, path, conditioning, and negative-relative gates.

The unchanged candidate is prebound at base commit
`f4125342211a1d1436ae48b685ec2342700f39c4`, before the Phase 3 package existed
in that tree. The complete 47-file candidate/core/build closure (including
protocol README, candidate `Cargo.lock`, and the compile-time embedded
`spec/body-document/schema/ck-body-document-v1.schema.json`) has path-set
SHA-256
`10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc` and
content SHA-256
`21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2`; base
tree and current-disk recomputation match. The schema is a compiled include
input. It is frozen from Gate A through exact attempts: any change requires a
new candidate identity and unseen scored material, or exact-public-corpus
adjudication. FE/MXCSR stays external and runner/oracle/scorer code cannot
change candidate source.

The durable candidate prebinding checker and focused test are development
tools, not generated corpus outputs or execution evidence. The checker is
17,745 bytes with SHA-256
`d21c122ecf5256b7e83402ba2a5a150807a1cfc64eef5e8df2002d86b1058c8b`; its
focused nine-test file is 5,389 bytes with SHA-256
`063206d1e9ecf4a5c2770061cca80e3492dc4bd3d34df56963c380690902d566`.
They run with:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/check_candidate_prebinding.py
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_candidate_prebinding.py
```

The checker follows production literal `include!`, `include_str!`, and
`include_bytes!` references recursively, rejects dynamic or unbound targets,
checks selected file types, modes, raw content, and relevant Cargo build/config
inputs, and does not sweep ignored target/cache artifacts. Git's textual mode
`100644` is parsed as OCTAL integer `33188` before big-endian u32 framing.

## Preregistered phase-one budgets

These are concrete runner/candidate resource budgets already implemented for
this exact evaluation. They are experimental inputs, not selected production
profile constants:

| Resource | Budget |
| --- | ---: |
| Candidate frame/request bytes | 16,384 bytes |
| Opaque wire request ID | 256 UTF-8 bytes |
| Candidate stdout | 65,536 bytes |
| Candidate stderr | 65,536 bytes |
| Per-request I/O deadline | 2.0 seconds |
| Shutdown deadline | 2.0 seconds |
| Trailing-output quiet window | 0.02 seconds |
| Cases per corpus | 128 |
| Cases across the package | 256 |
| Relations | 256 |
| Exact decimal-oracle work | 4,096 digits |
| Identity artifact read | 268,435,456 bytes (256 MiB) |

The manifest's `experimental_tolerances` entries are likewise phase-one input
cases. They do not bind a production profile or become selected A/R constants
from this package.

## Candidate boundary and identity

The candidate is a JSONL downstream consumer of `creature-kernel-core` with the
`provisional-r3-numeric-candidate` feature. Each request contains only its
protocol identifier, an opaque request identifier, an operation, and the
required input. Candidate responses contain observations or errors only.
Expected values, oracle values, profile bindings, corpus role, tags, and
relation/partner metadata remain runner-side and are never sent to the
candidate. Corpus records retain stable opaque `wire_request_id` values; these
are the only request IDs projected to the candidate and are distinct from
runner-side case IDs.

The preregistration identity object records:

```text
candidate_artifacts = stream-hashed-before-and-after-execution
runner_modules = stream-hashed-before-and-after-execution
filesystem_assumption = controlled-local-no-adversarial-mid-run-replace-and-restore
candidate_build_context = observational-not-provenance
```

The maximum identity artifact read is 268435456 bytes (256 MiB). This is a
pragmatic controlled-local pre/post content-and-stat stability check, not proof
against an adversarial replace-and-restore during execution; the binary hash
remains the artifact identity. Candidate build context is observational, not
provenance.

The environment/provider module is research-only and currently targets
x86_64 GNU/Linux. It performs read-only same-process inspection of C/x87
`fegetround` and MXCSR rounding-control (RC), FTZ, and DAZ bits, retaining raw
MXCSR plus decoded RC evidence. It performs no subnormal arithmetic probe or
dynamic subnormal-output claim and fails closed on any failed or unavailable
inspection. Other targets are unsupported by this adapter; this is not a
portability or production capability claim.

## One-shot execution and receipt wrapper

The committed phase-one one-shot wrapper, `scripts/run_phase1_once.py`, is
orchestration and provenance only. It is not a second numeric runner and is not
evidence itself. Its default, help, and `--preflight-only` paths cannot run the
authoritative corpus. `--preflight-only` prints the safe plan, creates no
attempt, and invokes no corpus runner. An authoritative execution requires all
three of `--execute`, `--acknowledge RUN-EXP-0002-PHASE1`, and a new
`--attempt-id` such as `attempt-001` (or a later unused ID).

The wrapper fixes the target to `x86_64-unknown-linux-gnu`, uses the Cargo
dev/debug profile with `--locked --offline`, and records the exact clean source
commit; clean means tracked, staged, and fully covered non-ignored untracked
files are clean. Its synthetic gate runs the runner unit tests, runner-module
compilation, and candidate `cargo test`; the candidate build must then pass
before the one authoritative run. Attempts use the exclusive layout
`experiments/EXP-0002-numeric-frame-profile/results/phase1/<full-commit>/<attempt-id>/{result.json,receipt.json}`.
An existing attempt is never overwritten. A completed authoritative attempt
has both files; a pre-run gate failure may preserve a receipt without a result.
There is no automatic retry.

`receipt.json` records the build/run commands, target/profile/toolchain,
allowlisted environment, hashes, exit codes, failure stage, and cross-checks.
The full evidence remains in `result.json`; the receipt does not become a
second result. Offline integrity checks do not rerun the corpus. Completed
failed or inconclusive evidence is preserved, and any fix or rerun uses a new
source commit and attempt ID without overwriting an earlier attempt.
The wrapper bounds each validation, build, and authoritative-run command to
180 seconds, version observations to 5 seconds, subprocess stdout/stderr to
65,536 bytes, result JSON to 4 MiB, candidate artifact reads to 256 MiB, and
the receipt to 1 MiB.

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

## Classification and result accounting

For this phase, interpretation is fixed before an evaluation:

- an exact mismatch against a frozen case, or against a relation with an
  explicit cross-case check, is failed conformance evidence;
- an environment `failed` or `unsupported` observation, and a candidate
  `unsupported` result, are inconclusive capability evidence only when no
  failure exists;
- transport failure, nonzero exit, missing/extra response, trailing output, or
  response-integrity failure is incomplete evidence; and
- no classification selects or rejects a profile, and no technology outcome is
  calculated.

A completed execution remains `run_status: complete`. Any exact failure takes
evidence precedence over inconclusive or unsupported results, while the case
and group counts retain both. This mixed aggregation does not turn the
phase-one evidence into profile selection or rejection.

If a candidate is changed after observing a frozen-role result, that change is
a new candidate evaluation with a new exact-artifact identity. Its result must
not overwrite or be described as the original held-out result.

## Package and checks

The standard-library Python runner loads the exact corpus schema, verifies
direct-child files, hashes, byte counts, family/order/relation metadata, and
candidate-projection disjointness. It independently recomputes the decimal
and scalar/translation Fraction/dyadic oracle during preflight and retains it
in result output. The subprocess transport bounds deadlines and stdout/stderr,
requires one response per request, rejects trailing output, and treats
transport or nonzero-exit failures as incomplete. Result output uses exclusive
creation and cannot overwrite or alias an input.

Run the synthetic runner checks from the repository root with:

```bash
python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/scripts \
  -p 'test*.py'
python3 -m py_compile experiments/EXP-0002-numeric-frame-profile/scripts/*.py
```

The runner CLI shape is:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/scripts/run_adapter.py \
  --manifest experiments/EXP-0002-numeric-frame-profile/corpora/manifest.json \
  --output <new-result.json> -- <candidate command and arguments>
```

The output path must be new and must not alias the manifest, corpus, or
candidate executable. Do not point this command at the frozen corpora until
the experiment is explicitly authorized.

## What this does not prove

This package is not an experiment result and does not select numeric constants
or a production profile. It does not prove quaternion normalization or
comparison, transform/basis behavior, claim identity/order, authored or
snapshot conformance, runtime geometry, portability, repeatability, or
Readiness 3/R3 activation. Failures, inconclusive results, unsupported
targets, and out-of-domain cases remain visible in any later result; this
package alone is not evidence that any proposed profile is suitable.

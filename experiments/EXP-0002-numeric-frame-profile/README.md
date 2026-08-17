# EXP-0002: Numeric/frame profile phase-one package

Experiment ID: EXP-0002

Experiment lifecycle: planned

Evidence closure: open

Technology outcome: none

Research question: the numeric/frame profile question described in the
[research design](../../docs/research/numeric-frame-profile-experiment.md).

Related specification: [proposed numeric/frame profile](../../spec/numeric-frame-profile/README.md).

## Status and phase-one boundary

This is a frozen-input, frozen-tooling, unrun phase-one package. The exact
candidate, runner, manifest, and three JSONL corpora are identified by their
recorded package/build and content identities. No candidate or corpus
evaluation has been run. `profile_binding` remains `null` and
`technology_result` remains `none`; there is no result, profile selection,
Readiness 3 activation, or product/technology decision.

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

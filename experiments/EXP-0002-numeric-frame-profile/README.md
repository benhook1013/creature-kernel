# EXP-0002: Numeric/frame profile preparatory slice

Experiment ID: EXP-0002

Experiment lifecycle: planned

Evidence closure: open

Technology outcome: none

Research question: the numeric/frame profile question described in the
[research design](../../docs/research/numeric-frame-profile-experiment.md).

Related specification: [proposed numeric/frame profile](../../spec/numeric-frame-profile/README.md).

## Status and scope

This is a frozen-input, unrun phase-one package. The development, held-out, and
adversarial JSONL corpora and their manifest hashes are frozen on disk, but no
candidate or corpus has been evaluated. There are no results, profile claims,
technology outcomes, R3 activation, production profile selection, or
runtime/geometry claims.

The current executable phase covers four operation families:

- decimal admission;
- scalar comparison;
- translation comparison;
- same-process environment attestation.

Quaternion operations remain explicitly unsupported. Later normalization,
transform/basis, composition/inversion, claim identity/all-pairs,
authored/snapshot, and adapter-tier obligations remain outside this package.

## Adapter boundary

The candidate is a JSONL downstream consumer of `creature-kernel-core` with the
`provisional-r3-numeric-candidate` feature. Each request is independent and
contains only its protocol identifier, an opaque request identifier, an
operation, and the required input. Candidate responses contain observations or
errors only. Expected values, oracle values, profile bindings, corpus role,
tags, and relation/partner metadata remain runner-side and are never sent to
the candidate. Corpus records retain stable opaque `wire_request_id` values;
these are the only request IDs projected to the candidate, and are distinct
from runner-side case IDs.

The environment/provider module is research-only and currently targets
x86_64 GNU/Linux. It performs read-only same-process inspection of C/x87
`fegetround` and MXCSR rounding-control (RC), FTZ, and DAZ bits, retaining raw
MXCSR plus decoded RC evidence. It performs no subnormal arithmetic probe or
dynamic subnormal-output claim and fails closed on any failed or unavailable
inspection. It never repairs the environment. Other targets are unsupported by
this adapter; this is not a portability or production capability claim.

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
snapshot conformance, runtime geometry, or Readiness-3/R3 activation. An
environment failure or unsupported observation remains retained capability
evidence and is not a technology pass/fail result.

Failures, inconclusive results, unsupported targets, and out-of-domain cases
remain visible in any later result; this package alone is not evidence that any
proposed profile is suitable.

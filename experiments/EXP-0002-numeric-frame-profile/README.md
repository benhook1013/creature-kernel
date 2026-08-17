# EXP-0002: Numeric/frame profile preparatory slice

Experiment ID: EXP-0002

Experiment lifecycle: planned

Evidence closure: open

Technology outcome: none

Research question: the numeric/frame profile question described in the
[research design](../../docs/research/numeric-frame-profile-experiment.md).

Related specification: [proposed numeric/frame profile](../../spec/numeric-frame-profile/README.md).

## Status and scope

This is a registered, preparatory protocol/adapter slice. It has not run a
development, held-out, or adversarial corpus. The protocol, corpora, profiles,
and results are not frozen. There are no results, profile claims, technology
outcomes, R3 activation, production profile selection, or runtime/geometry
claims.

The first executable phase targets five operation families:

- decimal admission;
- scalar comparison;
- translation comparison;
- quaternion normalization; and
- quaternion comparison.

Current executable coverage is smaller: the candidate binary exercises decimal,
scalar, translation, and same-process environment-attestation operations. The
research-only environment module also has provider tests; quaternion operations
remain explicitly unsupported by the candidate binary. Later transform/basis,
composition/inversion, claim identity/all-pairs, authored/snapshot, and adapter
tier obligations remain part of the eventual experiment.

## Adapter boundary

The candidate is a JSONL downstream consumer of `creature-kernel-core` with the
`provisional-r3-numeric-candidate` feature. Each request is independent and
contains only its protocol identifier, an opaque request identifier, an
operation, and the required input. Candidate responses contain observations or
errors only. Expected values, oracle values, profile bindings, corpus role,
tags, and relation/partner metadata remain runner-side and are never sent to
the candidate.

The environment/provider module is research-only and currently targets
x86_64 GNU/Linux. It performs read-only same-process inspection of C/x87
`fegetround` and MXCSR rounding-control (RC), FTZ, and DAZ bits, retaining raw
MXCSR plus decoded RC evidence. It performs no subnormal arithmetic probe or
dynamic subnormal-output claim and fails closed on any failed or unavailable
inspection. It never repairs the environment. Other targets are unsupported by
this adapter; this is not a portability or production capability claim.

## Reproduction commands

From the repository root, the current synthetic adapter checks are:

```bash
cargo build --manifest-path experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml --offline
cargo test --manifest-path experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml --offline
cargo run --manifest-path experiments/EXP-0002-numeric-frame-profile/candidate/Cargo.toml --offline < request.jsonl > response.jsonl
```

The run command is for synthetic requests only at this stage; it must not be
pointed at a future frozen corpus until the protocol, corpus hashes, oracle,
runner, and profile bindings have been reviewed and locked.

## Deferred freeze work

The following remain open before an evaluated run:

- freeze disjoint development, held-out, and adversarial JSONL corpora and
  their manifest hashes;
- implement and independently validate the decimal, dyadic, normalization,
  quaternion, and later transform/claim oracle paths;
- implement the runner's deterministic ordering, sanitized candidate
  projection, comparison adjudication, and result schema;
- bind candidate profiles, domains, budgets, conditioning rules, and expected
  classifications without moving or tuning cases after observation;
- define the exact request-byte and line-resource cap before any corpus run;
- bind toolchain/compiler/code-generation identity and independent square-root
  vectors before enabling quaternion support; and
- add quaternion, transform, basis, claim identity, and authored/snapshot
  fixtures only when their executable interfaces exist.

Failures, inconclusive results, unsupported targets, and out-of-domain cases
must remain visible. This preparatory record is not evidence that any proposed
profile is suitable.

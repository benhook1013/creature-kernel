# Numeric and frame profile experiment design

Status: Proposed planned evidence design; no experiment is registered and no
results exist.

## Question

What finite numeric range, quaternion normalization/near-zero policy, and
separate absolute-plus-relative tolerances are stable enough for the proposed
semantic numeric/frame profile? The target comparisons are translation,
angular rotation, quaternion equivalence, transform-composition residuals, and
authored-value conflict versus expected-snapshot comparison.

This design makes no geometry, performance, visual-quality, or runtime claim.
It selects no package and does not activate a schema or resolver.

## Planned protocol

Run only after the relevant Rust/JSON shell prerequisites exist; until then,
this document is design only. Use the intended Rust/JSON stack, a fixed source
decimal corpus, and reproducible seeds. The corpus must include signed zero,
extreme finite values, excessive precision, subnormal/underflow cases,
non-finite injection, zero/near-zero/non-normalized quaternions, and `q`/`-q`
pairs. Include creature-scale transforms across a useful magnitude range,
repeated composition/inversion chains at several lengths, and attachment
composition cases.

Repeat on WSL x86_64 and perform one native-Linux smoke run. Record hardware,
OS/filesystem context, toolchain, source/profile identifiers, seed, and command.
For each case retain raw parsed bits, canonical values, errors,
classifications, and comparison outcomes. Do not choose thresholds before
observing the corpus; distinguish observed behaviour from the eventual
recommendation and leave inconclusive cases recorded as such.

## Acceptance criteria for evidence

- Repeated runs classify the same inputs identically.
- Ordinary intended values are not rejected.
- Malformed and non-finite cases reject deterministically.
- Proposed tolerances are the smallest stable values observed, with an
  explicit safety margin and reasoning for each comparison type.
- Platform differences and inconclusive results are recorded rather than
  silently averaged away.

## Activation boundary

The later experiment implementation and results belong under `experiments/`
after the semantic shell, relevant profiles, and fixture admission prerequisites
are activated. Results may support or challenge DR/spec proposals but cannot
change them automatically.

# Numeric and frame profile experiment design

Status: Proposed evidence design; EXP-0002 remains planned, with open evidence
closure and no technology outcome. Phase-one attempt-001 is complete and
passed; the [human-readable evidence summary](../../experiments/EXP-0002-numeric-frame-profile/RESULTS.md)
links the immutable result and receipt. No profile selection or R3 activation
exists.

## Question

What finite numeric domain, quaternion normalization and near-zero policy,
conditioning bound, and typed comparison budgets are suitable for the proposed
semantic numeric/frame profile? The target comparisons are translation,
angular rotation, quaternion equivalence, transform-composition residuals, and
authored-value conflict versus expected-snapshot comparison. Batch 13 adds
exact dyadic comparator arithmetic, deterministic normalization/square-root
fixtures, stable claim identity, and the future adapter's scale/tier boundary
to the evidence obligations.

This design makes no geometry, performance, visual-quality, runtime, or
cross-platform claim. It selects no package, constant, schema, resolver, or
adapter and does not activate a readiness gate.

The implemented phase-one candidate/request-response package covers four
current operations: decimal admission, scalar comparison, translation
comparison, and read-only environment attestation. Quaternion operations
remain unsupported pending their required oracle and provider inputs. The
development, held-out, and adversarial corpora plus manifest identities are
frozen for phase one, and attempt-001 evaluated those frozen inputs. This is not
the whole eventual experiment: transform and basis conversion,
composition/inversion, claim identity and all-pairs evaluation,
authored-versus-snapshot comparison, and the later adapter tier remain
separate obligations below.

The environment attestation is a read-only inspection of C/x87
`fegetround` plus MXCSR rounding-control (RC), FTZ, and DAZ bits. It records
the raw MXCSR and decoded RC evidence and performs no subnormal arithmetic
probe or dynamic subnormal-output claim.

## Protocol status and preregistration boundary

EXP-0002 remains planned with open evidence closure and no technology outcome.
The phase-one package is frozen and implemented, and attempt-001 is complete;
its four-operation request/response shape, opaque wire request IDs, three
corpus files, manifest identities, bounded runner/oracle/transport, and
synthetic checks are fixed on disk. This design remains Proposed and is not a
complete frozen protocol for the broader experiment. Before any broader
evaluation, the remaining protocol must still preregister, independently of
observed outcomes:

- intended translation magnitude and component ranges, including the intended
  finite-value and decimal-admission domain;
- the quaternion component/norm domain, non-near-zero region, normalization
  policy, and the q/-q equivalence domain;
- the maximum composition and inversion-chain length and the transform classes
  admitted for evaluation;
- a condition-estimate definition and a declared maximum conditioning bound;
- separate semantic error budgets for translation, angular rotation,
  quaternion equivalence, composition residual, authored-claim conflict, and
  expected-snapshot comparison; and
- a predeclared validation margin and the rule for classifying a result as
  pass, reject, or inconclusive;
- an exact request-byte and line-resource cap, including malformed-input
  handling, before any corpus run; and
- toolchain/compiler/code-generation identity fields plus independent
  square-root vectors before quaternion support is evaluated.

The experiment must not derive tolerances from observed pass/fail minima in the
same corpus used to justify them. The exact error formula and validation-margin
constant remain open protocol decisions here; this document intentionally does
not freeze an arbitrary numeric value. In a later profile-bound evaluation, a
failure rejects the proposed profile or leaves it inconclusive; it never widens
a budget after observing a failure. A phase-one mismatch is candidate/artifact
conformance evidence only and never selects or rejects a profile.

For phase one, the binding is the named exact-artifact persistent-conformance
evaluation `ck.exp-0002.phase1-persistent-conformance-v1`. Exactly one
persistent candidate process receives development, then held-out, then
adversarial. Held-out is non-tuning, not blind or process-isolated from
development, and environment checkpoints are interpreted at their workload
position in that persistent process. The phase-one claim is limited to 49
exact frozen case adjudications plus runner classifications for 26 registered
named case groups, including represented boundary/resource/error/environment
observations. Only `lexical-equivalence`, `signed-zero-canonicalization`, and
`environment-repeat` have explicit cross-case checks; the other groupings
organize member-case outcomes. It does not support inference about role isolation,
fresh-process behavior, order independence, repeatability, broad
generalization, profile selection, or technology outcome. `profile_binding`
remains `null` and `technology_result` remains `none`.

Attempt-001 completed at source commit
`d88f5eca3ad3c0c0cb00dcf7dd012471be979305`, with 49/49 cases and 26/26
registered relations passed. The wrapper receipt reports one runner invocation,
exit `0`, and no failure; the raw result and receipt are linked from the
[phase-one results summary](../../experiments/EXP-0002-numeric-frame-profile/RESULTS.md).
The result is evidence for this identified candidate and runner only; it does
not establish a production profile, Readiness 3, portability, repeatability,
generalization, or the later quaternion/transform/adapter obligations.

## R3 successor admission lineage

The later authored-conflict evaluation is a distinct successor protocol, not a
promotion of phase one. Before held-out or adversarial execution it must freeze
the candidate profile/rules/constants, semantic budgets, validation margin and
formula, and the corpus identities and roles. Its admission record binds the
immutable protocol, candidate, corpus, result, and receipt identities, plus
the activation closure's separately bound resolver/source implementation
closure and a resolver binding plus complete build request that reference the
exact authored-conflict profile. The profile definition/content identity is a
separate activation input. Mismatch across these inputs fails closed. The
generic resolver implementation need not itself reference the exact profile. A
failed or inconclusive evaluation creates a new
candidate/evaluation identity and cannot mutate or widen the prior candidate.
Attempt-001 is explicitly ineligible because its `profile_binding` is `null`.
This record selects no exact profile ID, constant, fixture file, or activation
record, and its result cannot itself grant R3 activation.

The concrete phase-one budgets already implemented are experimental inputs, not
selected profile constants: frame 16,384 bytes; wire request ID 256 UTF-8
bytes; stdout and stderr 65,536 bytes each; I/O 2.0 seconds; shutdown 2.0
seconds; trailing quiet 0.02 seconds; at most 128 cases per corpus, 256 total
cases, and 256 relations; 4,096 decimal-oracle work digits; and a maximum
identity artifact read of 268435456 bytes (256 MiB). The manifest's current A/R
entries are experimental inputs and do not bind a production profile. Exact
mismatch against a case, or against a relation with an explicit cross-case
check, is failed conformance evidence. Environment failed or unsupported and
candidate unsupported are inconclusive capability evidence only when no failure
exists. Transport, nonzero-exit, or response-integrity failure is incomplete
evidence; none selects or rejects a profile. A completed execution remains
`run_status: complete`; any exact failure takes evidence precedence over
inconclusive/unsupported, while counts retain both. A fix after observing a
frozen-role result creates a new candidate evaluation and must not overwrite or
be called the original held-out result.

The phase-one preregistration identity object is exactly:

```text
candidate_artifacts = stream-hashed-before-and-after-execution
runner_modules = stream-hashed-before-and-after-execution
filesystem_assumption = controlled-local-no-adversarial-mid-run-replace-and-restore
candidate_build_context = observational-not-provenance
```

This is a pragmatic controlled-local pre/post content-and-stat stability check,
not proof against an adversarial replace-and-restore during execution. The
binary hash remains the artifact identity; candidate build context is
observational, not provenance.

## Canonical evaluation rules

The evaluated implementation must use a fixed, preregistered operation order
for parsing, canonicalization, normalization, composition, inversion, and
comparison. The initial canonical direction is round-to-nearest, ties-to-even,
with no reassociation, implicit fused-multiply-add contraction, flush-to-zero
(FTZ), or denormals-are-zero (DAZ). Any compiler or hardware mode that cannot
be held to that profile is a separate classification, not a silent alternate
run. Decimal admission verifies the already-fixed boundary: strict JSON rejects
non-finite syntax and typed/API non-finite injection is rejected; overflow to
infinity and any nonzero exact rational that rounds to signed zero are
rejected; finite nonzero subnormals and precision within the lexical/resource
bound are accepted; and lexical `-0` normalizes to semantic `+0`. Only intended
ranges, near-zero and conditioning thresholds, tolerance constants, semantic
budgets/margins, and profile IDs remain experiment/evidence-gated.

Scalar and translation comparisons must be verified mathematically, not by a
rounded equivalent expression: decode finite binary64 values as signed integer
significands times powers of two, then perform bounded dyadic/integer
subtraction, multiplication, addition, and inclusive comparison. The corpus
must include exact ties, one-ULP below/at/above each bound, opposite-sign
values, cancellation, and finite-domain edge cases. Quaternion comparison
normalizes through exact maximum-absolute scaling, fixed `xyzw` division,
left-to-right square accumulation, correctly rounded binary64 square root, and
fixed division. Runtime comparison then uses exact `sum((qa_i-s qb_i)^2) <=
(2H)^2`, with no `asin`, `sin`, norm, or runtime square root. `H` must be
derived offline from a declared independent high-precision oracle/generator
revision as the greatest binary64 value no greater than exact `sin(theta/4)`;
retain theta/H exact bits and derivation metadata.

The evaluated implementation must preserve raw source text and parsed bits,
canonical values, oracle values and uncertainty, comparison inputs and
outcomes, condition estimates, seeds, profile IDs, compiler/toolchain and
optimization settings, FMA/FTZ/DAZ settings, hardware/OS details, and final
classification. Human-readable explanations are evidence metadata, not
comparison identity.

## Oracles and corpora

The decimal-admission oracle is exact rational arithmetic over the source
decimal token, with analytic cases used whenever an exact formula is available.
Scalar and translation comparator cases use a rational/dyadic oracle that
retains the exact subtraction and bound comparison. Generic normalization and
transform chains additionally use a disposable, independent oracle at
materially higher precision. The higher-precision oracle must be independent of
the implementation under test and must retain its uncertainty or a justified
exact/analytic result. The offline H generator is a separately versioned,
independent high-precision oracle/generator; its theta/H bits, downward
quantization proof, and generator revision are retained. No oracle result is
silently rounded into a target budget without recording that uncertainty.
Quaternion support remains deferred until the toolchain/code-generation
identity is bound and independent square-root vectors are available.

Freeze three distinct corpora before the evaluated run:

1. a development corpus used only to debug the harness and protocol;
2. a held-out corpus not used to tune formulas, budgets, or classifications;
3. an adversarial corpus designed to probe boundaries and failure modes.

All three corpora must include, as applicable, midpoint and tie cases, signed
zero, subnormal and underflow cases, overflow, cancellation, excessive decimal
precision, non-finite injection, zero and near-zero quaternions, q/-q pairs,
long composition/inversion chains, ill-conditioned transforms, basis
conversion, and claim-order permutations. Add normalization/square-root
fixtures across the bounded initial platforms, direct common-frame versus
residual/asymmetry and order reversal, duplicate/collision claim identity,
deterministic sorted pair ordering, and smallest value-tuple selection. The
evaluated run must not move a
case between corpora after seeing a result.

The corpus also freezes representative intended-domain translations,
rotations, attachment compositions, and authored/snapshot comparisons. Values
outside the preregistered domain are rejected or marked out-of-domain; they are
not used to widen ranges or tolerances.

## Metamorphic and semantic checks

In addition to oracle comparisons, the run must check the following relations
where their preconditions hold:

- canonicalization is idempotent;
- q and -q produce equivalent canonical rotations and comparison outcomes;
- equivalent decimal lexical forms produce the same admitted value and bits;
- identity and inverse operations round-trip within the applicable profile;
- selected composition orders agree where the semantic operation declares them
  equivalent, while non-commuting order remains distinct;
- claim satisfiability is invariant under permutation of claim input order; and
- basis conversion followed by the inverse conversion round-trips within its
  declared profile.

The claim corpus must additionally prove that same ID plus the same normalized
value evaluates once while retaining every occurrence, whereas same ID plus a
different value is an invalid-source collision. Pair validity is unordered but
the first failing pair is selected from sorted claim IDs. Representative
selection uses the lexicographically smallest declared value tuple, with claim
ID only as an exact-tuple tie-break, and uses an exact total order after `-0`
normalization. Claim IDs must be generated only from the structured canonical
target/kind/source-namespace/semantic-address and explicit authored claim key;
raw JSON pointers and traversal/allocation/thread/time/generated IDs are
diagnostic-only or prohibited.

The proposed normative comparator direction is to normalize same-target claims
into one canonical local-to-parent frame, compare translations directly and
rotations by q/-q, and evaluate every applicable unordered claim pair rather
than using order-dependent folding. It must record boundary and tie
classifications and identify non-transitive or order-sensitive outcomes as
reject or inconclusive, never as a tolerance success. A composition residual
is measured only as a separately named diagnostic/snapshot check.

Record a condition estimate for every normalization, inversion, composition,
and basis-conversion case. A case exceeding the preregistered conditioning
bound is rejected or marked out-of-intended-domain, with its reason retained;
the comparison budget is not widened to accommodate it.

The future-adapter corpus is a separate post-Readiness-3 transaction. It must
cover a signed permutation `C` and finite positive engine-units/metre scale
`s`, with `sC` for vector lengths, `s` for scalar dimensions/radii/extents,
`C` for directions and normalized normals, and `D H D^-1` for rigid transforms
where `D = diag(sC, 1)`. The
default storage/output tier makes no runtime arithmetic claim; an optional
runtime-conformance tier adds probes and fixtures. Both tiers preregister
target precision, narrowing, domain, overflow/underflow/subnormal policy, and
translation/angular budgets. Include `s=1` and nonunit known-magnitude cases,
direction/no-scale cases, reflection, composition/inverse, quaternion sign,
round-trip, and overflow/underflow/subnormal fixtures. A binary32 subnormal
runtime claim requires an FTZ/DAZ probe; otherwise the required capability is
unsupported. These cases remain evidence only and do not activate an adapter.

## Platform and reproducibility boundary

The initial bounded evidence target is WSL x86_64 plus native Linux smoke on
the same declared protocol and corpus. Record the exact compiler/toolchain,
optimization profile, target, hardware, operating-system and filesystem
context, seeds, and command. A materially different architecture and toolchain
are required before making a broader cross-platform reproducibility claim; the
initial target must not be described as broad platform support. Any observed
platform difference remains a classified result and is not averaged away.

## Evidence accounting

For each case retain the source token/text, raw parsed bits, canonical bits,
oracle result and uncertainty, condition estimate, comparison result, error
components, classification, and any metamorphic-check outcome. Retain the
complete corpus manifests and content identities, seed/configuration, profile
IDs, compiler/toolchain/optimization/FMA/FTZ/DAZ settings, hardware/OS
metadata, and reproduction command. Record failures, inconclusive results,
out-of-domain cases, and harness failures separately from supported results.

The evidence may support or challenge the proposed numeric/frame and
comparison profiles. It cannot promote a proposal, accept a decision record,
activate a schema/resolver/adapter, or claim a technology outcome by itself.

## Acceptance criteria for evidence

- Repeated runs under the same declared profile classify the same inputs
  identically.
- Ordinary values inside the preregistered intended domain are not rejected
  without a retained oracle, conditioning, or implementation-failure reason.
- Decimal boundary cases agree with the exact rational or analytic oracle and
  explicitly classify overflow, underflow, subnormal, and non-finite cases.
- Exact dyadic scalar predicates agree with the rational oracle at inclusive
  ULP boundaries, and the offline H derivation retains a downward-quantization
  proof and exact theta/H bits.
- The held-out and adversarial corpora are evaluated without post-hoc budget,
  range, corpus, or formula changes.
- Every accepted comparison is within its preregistered semantic budget and
  validation margin, with condition estimates within the intended bound.
- Metamorphic checks and all-pairs claim evaluation are order-independent where
  the semantic relation requires it.
- Platform/toolchain differences, oracle uncertainty, failures, and
  inconclusive or out-of-domain cases are retained rather than silently
  averaged away.
- Adapter tier, scale, precision, and read-only FE/x87 plus MXCSR RC/FTZ/DAZ
  inspection results are retained as separate evidence; they cannot be
  promoted to a runtime capability claim by this experiment.

## Activation boundary

Evaluation tooling and results belong under `experiments/` after the semantic
shell, relevant profiles, and fixture-admission prerequisites exist. Results
may support or challenge DR/spec proposals but cannot change them
automatically. This design does not itself select a profile, calculate a
technology outcome, activate readiness, or establish implementation support;
attempt-001 evidence is recorded separately under `experiments/`. Any
Readiness implementation binding remains a separate scoped content-identity
transaction from the fixture payload and expected snapshots.

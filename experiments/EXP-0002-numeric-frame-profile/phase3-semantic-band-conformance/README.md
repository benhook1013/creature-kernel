# EXP-0002 phase three: semantic-band conformance preregistration

Status: Proposed, non-authoritative, execution not permitted

This package tests one candidate implementation against one provisional
semantic profile. It does not select tolerances or compare profiles. The
declared semantic bands analytically derive the candidate's constants; the
outcome is `supported`, `failed`, or `inconclusive` conformance evidence over
the bounded transform domain.

Ben authorization is still required before any exact attempt or dispatch.
Neither this authorization nor a future conformance result is technical
validation of the numeric values, permanent product truth, a production
binding, a product-quality claim, or Readiness 3 authorization.

## Boundary and candidate

The operation is one standalone source and one authored-versus-Attachment-
derived rigid transform. It covers translation, quaternion rotation,
source-basis/unit conversion, and the bounded composition/equation witness.
It excludes module or aggregate resolution, namespace merge/remap, snapshots,
geometry, rendering, rigging, animation, physics, runtime output, and R3
activation.

The only candidate planned for any future execution is:

`ck.provisional-r3-authored-conflict.semantic-band-1`

with `A = 0x3f0a36e2eb1c432d` (`5.0000000000000002e-05 m`), `R =
0x0000000000000000` (`0.0`), and `H = 0x3ec4f8b588e368f1`
(`2.5000000000000002e-06`). `A` is absolute translation tolerance, `R` is
relative translation tolerance, and `H` is quaternion half-chord tolerance.
The canonical semantic thresholds are the exact dyadic value identified by A
and exact `2H` (`0x3ed4f8b588e368f1`) in full-chord units. The shorter `5e-5`
and `5e-6` spellings below are nominal human-readable shorthand. This phase
uses q/-q full-chord semantics and makes no angular interpretation or claim.
The phase-two strict, micro, and stress profiles remain historical analytical
negative comparisons; they are not executed here and do not rank or reject
this candidate.

## Provisional bands and certified decisions

Translation bands are: nominal clear agreement at most `5e-5 m`, material floor
`2e-4 m`, conflict-certain minimum `2.3e-4 m`, and gross conflict minimum
`2e-3 m`. Rotation uses nominal full q/-q-equivalent quaternion chord: `5e-6`,
`2e-5`, `2.3e-5`, and `2e-3`, respectively. The `2.3/2.0 = 1.15` ratio is
the declared 15% semantic conflict guard (for both translation and rotation);
it is not a post-result adjustment.

The separate fixed 10% validation margin is a decision-threshold separation
for non-boundary scored cases. If `T` is the applicable candidate threshold
(`A + R * scale` for translation, `2H` in full-chord terms for rotation), an
agree case must have certified upper bound `<= 0.9*T`; a conflict case must
have certified lower bound `>= max(1.1*T, conflict-certain minimum)`. Inclusive
threshold cases belong only to deterministic development/comparator controls
and require singleton/exact oracle intervals.

The protocol defines three certified interval objects, but current materialization
contains source-derived `I_truth` only: translation truth is exact, while
rotation truth is a certified interval enclosing
`min(||qa-qb||_2, ||qa+qb||_2)` after normalization. `I_candidate` and `I_error`
are mandatory future scorer/adjudication outputs after candidate witness data
exists. `I_candidate` is computed from the candidate-reported binary64 witness;
`I_error`, derived from both, encloses absolute candidate-versus-ideal metric
error. Their caps remain preregistered obligations: interval radius and upper
error endpoint are at most `1e-10 m` for translation or `1e-10` full chord for
rotation. Neither future output is a current materialized artifact.

Preflight enumerates `0.9T`, `T`, `1.1T`, and the conflict-certain floor and
admits a scored case only when `I_truth` is wholly inside its declared class
and outside the threshold margin. Future `I_candidate` straddling `T`, or any
overly wide/unresolved current `I_truth` or future `I_candidate`/`I_error`
interval, is incomplete/inconclusive. A fully certified
candidate status inconsistent with the expected class is failed. Exact
threshold comparator controls use singleton exact intervals. No post-result
widening is allowed.

## Deterministic case plan

There is no randomness or seed. The held-out ledger has 40 scored cases:
five families, each with two cases in each metric/class cell (translation
agree, rotation agree, translation conflict, rotation conflict). Agree strata
are `0.50*T` and `0.85*T`; conflict strata are `1.05*conflict-certain-min`
and `1.05*gross-conflict-min`.

The exact ledger and request constructions are now materialized as
`development-unfrozen`, not pending and not frozen. The [deterministic
generator](scripts/generate_phase3.py) and [focused structural test](scripts/test_generate_phase3.py)
produce the [development corpus](corpora/development.jsonl), [held-out
corpus](corpora/held-out.jsonl), [controls corpus](corpora/controls.jsonl),
[recipe manifest](manifests/recipe-manifest.json), [artifact
manifest](manifests/artifact-manifest.json), and [12-vector sqrt
fixtures](sqrt-vectors.json). Regenerate or check the materialization only
with:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/generate_phase3.py
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/generate_phase3.py --check
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_generate_phase3.py
```

Each materialized ledger record separates `construction_target` from
`source_truth`: the former is the exact magnitude requested by the recipe
before serialization, while the latter is source-derived from the serialized
source and its exact numeric lexemes. Current materialization contains `I_truth`
only: translation truth may be exact; rotation truth is a certified interval
enclosing the normalized q/-q-equivalent full chord, not an exact singleton.
`I_candidate` and `I_error` are mandatory future scorer/adjudication outputs
after candidate witness data exists, not current artifacts; their caps remain
preregistered obligations. Rotation intervals use exact rational
dot-products and norm-squared values, then 256-bit integer-`isqrt` directed
rational bounds for every square root; decimal text is only the final outward
endpoint encoding. The current `I_truth` interval radius and mandatory future
`I_error` upper endpoint are both capped at `1e-10` full chord; `I_error` is not
a current artifact. The construction metadata retains the full
authored and Attachment-derived contribution lists, exact authored/derived and
pair kappa values, and derived canonical/source quaternions. Non-identity
derived rotations are intentionally present in the non-identity, conversion,
and other applicable family records.

The closed held-out ledger uses deterministic IDs of the form
`phase3/{family}/{metric}/{class}/{stratum}/{ordinal}`. Axis, sign, scale, and
chain assignments are table/formula-driven by the current recipe manifest.
The generator rejects duplicate IDs or invalid constructions and never
replaces or tunes a case. Request IDs are unique across all three materialized
roles. The generator also rejects duplicate normalized request content across
the development and held-out roles after removing `request_id`; controls are
separately partitioned because their typed/preflight behavior is distinct.
The eight explicit development cases cover the exact
translation threshold, near-threshold rotation (the exact singleton remains a
direct comparator unit-test obligation), q/-q sign equivalence, conversion,
four-edge composition, the Attachment equation, identity zero/zero, and
`kappa=999999`. The 40 held-out cases are the closed five-family Cartesian
product described above. The 12 controls are four gray cases strictly inside
the band, four dispatched typed zero-quaternion controls, three runner
preflight out-of-domain controls with `dispatch_to_candidate:false`, and one
dispatched negative-relative control. Preflight cases remain runner
adjudications and are not candidate wire requests. Gray-band cases are
observation-only. Candidate-local admission controls require their
preregistered typed skipped zero-quaternion observation and cause. The three
runner-preflight controls require an out-of-domain adjudication without
candidate dispatch; the negative-relative control requires its typed candidate
rejection. A wrong completed typed result is failed; missing or uncertain
evidence is inconclusive. Malformed transport remains unit tests.

Current generated candidate records reuse the existing phase-two
[request/envelope contract](../phase2-authored-conflict/candidate/README.md):
protocol `ck.exp-0002.r3-authored-conflict-candidate-request-1`, operation
`observe-authored-conflict`, `resource_profile: ordinary`, the existing
`gate/arithmetic/sqrt/environment` providers, and the canonical body-document
JSON source string. This phase adds no wire protocol.

### Source-derived domain admission

Admission is recomputed from every serialized source, retaining exact numeric
lexemes; it does not trust construction metadata. The 60 records partition
exactly into 53 `admitted`, 4 `typed-control`, and 3 `out-of-domain` records,
with all 40 scored held-out records admitted. Admitted records pass the
component (`<=16 m` and quaternion absolute component `<=1`), contribution
sum (`<=64 m`), source quaternion norm (`[0.5,2]`), four-edge path, exact
rational translation `kappa_pair <= 1e6`, and certified quaternion
`kappa_q <= 2` gates. `kappa_q` is the maximum of `1/sqrt(sum(q_i^2))`
over every source quaternion, certified using directed integer-`isqrt`
enclosures.

The four typed controls retain exact zero-quaternion locations: the tail-root
part placement (`main`, anchors `[tail]`), the host tail-mount socket
interface (`main`, anchors `[]`), the tail attachment offset (`main`, anchors
`[tail]`), and the mating tail-mount socket interface (`main`, anchors
`[tail]`). Each requires the typed `skipped` / `zero-quaternion` observation;
these are candidate-local admission controls, not resolver `invalid-source`
semantics. The three out-of-domain controls remain runner preflight
adjudications (`dispatch_to_candidate:false`). Negative fail-closed tests cover
translation component >16, contribution sum >64, quaternion component >1,
quaternion norm <0.5, path length >4, and `kappa_pair > 1e6`; a separate
dispatched negative-relative tolerance control requires the typed
`invalid-tolerance` rejection with `negative` `translation-relative` cause.
These tests are construction/audit checks, not execution evidence.

### Pre-disclosure candidate-source binding

The unchanged candidate semantics are prebound at base Git commit
`f4125342211a1d1436ae48b685ec2342700f39c4`, whose tree has no Phase 3 package.
The candidate history is `5bae100` (candidate added), `71c9a73` (Attachment
evidence), `a1bdc14` (typed causes), `b695d8a` (session integrity), and
`acd512f` (lint contract), all ancestors of that base commit.

The complete 47-file closure selects every tracked regular file under the
phase-two candidate directory, every tracked file under
`crates/creature-kernel-core/**`, root `Cargo.toml`, and `rust-toolchain.toml`,
then recursively adds every literal production `include!`, `include_str!`, and
`include_bytes!` target. This includes the compile-time embedded
`spec/body-document/schema/ck-body-document-v1.schema.json`, which is a
compiled include input. The candidate README is included as non-compiled
protocol/build documentation; the candidate `Cargo.lock` is the external
dependency-resolution input. Root `Cargo.lock` is excluded because the
candidate has its own standalone manifest and lockfile. No relevant candidate
or core `build.rs`, nor `.cargo/config` or `.cargo/config.toml` on the
candidate-to-repository ancestor path, exists in the base tree. Ignored
target/cache artifacts are not swept.

The reproducible closure algorithm is `ck.phase3-candidate-source-build-closure.v1`:
normalize repository-relative UTF-8 paths to `/`-separated paths without
leading `./`/`/`, empty, `.` or `..` components; sort raw UTF-8 path bytes;
parse Git's six-digit textual mode `100644` as OCTAL integer `33188`, then
encode that integer as big-endian u32. The
path-set stream is `ck.phase3-candidate-source-build-path-set.v1` plus NUL,
then for each sorted entry a big-endian u32 path-byte length, path bytes, and
big-endian u32 mode. The content stream uses the same entry fields, followed
by a big-endian u64 raw-byte length and exact bytes. SHA-256 is taken over each
stream without decoding, newline normalization, JSON, or Git-object hashing.
At the base commit and on the current disk independently: path-set count `47`,
path-set SHA-256
`10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc`, content
SHA-256 `21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2`,
and total raw bytes `1,494,337`.

From this Gate A materialization through every exact attempt, the bound
candidate source/build closure is frozen and immutable. Any change invalidates
the public-corpus bounded-domain claim and requires a new candidate identity
plus unseen scored material, or an explicit narrowing to exact-public-corpus
adjudication. Runner, oracle, and scorer implementations may be separate but
may not change the candidate closure. FE/MXCSR observation remains external;
no candidate modification is needed.

The current generated identities are: generator 47,539 bytes,
`a96ac78f3a59b268becfdc2e814b4422973bf4198b048bb9823db3072e00e90f`; focused
test 33,943 bytes,
`2dc9e9164a5ae820d6b170a28a1d5889e17e795d5d87c235bb5c3c75bb78a263`;
development 147,358 bytes,
`26401712d12545ba38df110a28232ae211c4991c89d8c635bb1b77ccd7dd9e20`;
held-out 753,548 bytes,
`86606497543e642c1995b5ff22081f0c2ba24a6c4ad5bb68a1cf74899fd7c49b`;
controls 219,560 bytes,
`9abba94abab5b0b8384bc90ae58c9b11c2bfa0f998ef259e94d06dd8c5acc7b7`;
recipe manifest 1,163,082 bytes,
`a81c6511335c9cb63fa432e633e7a5bd3a262df0f8ae2036a54cff9ae94ab638`;
artifact manifest 799 bytes,
`ec28e222b0a4af6de23b24c4ae8f9aa4263a7a8f548f6cd1002ef62e37bda6db`; and
sqrt vectors 1,946 bytes,
`20668c89c7a213a73b73494540bf612ac2b253d81e255c686ad78255869e7953`.

The durable candidate prebinding checker and focused test are development
tools, not generated corpus outputs or execution evidence. The checker is
17,745 bytes with SHA-256
`d21c122ecf5256b7e83402ba2a5a150807a1cfc64eef5e8df2002d86b1058c8b`; the
focused nine-test file is 5,389 bytes with SHA-256
`063206d1e9ecf4a5c2770061cca80e3492dc4bd3d34df56963c380690902d566`.
Run them with:

```bash
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/check_candidate_prebinding.py
python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_candidate_prebinding.py
```

The checker follows production literal `include!`, `include_str!`, and
`include_bytes!` references recursively, rejects dynamic or unbound targets,
checks selected regular-file types, modes, raw content, and relevant Cargo
build/config inputs, and does not sweep ignored target/cache artifacts.

## Gate B build/freeze preparation (development only)

The evidence and read-only Gate B preflight contracts now use the canonical
phase identifier `exp-0002-phase3-semantic-band-conformance-001`, matching this
preregistration. The earlier phase-ID mismatch is corrected; this is identity
plumbing, not experiment evidence.

The new `scripts/phase3_build_receipt.py` captures a build-only receipt from an
already-built candidate artifact. It binds the source closure, normalized
vendored dependency closure, sanitized exact build invocation, pinned
toolchain, and binary identity. It never starts the candidate, feeds it input,
or dispatches an attempt. Its focused checks are in
`scripts/test_phase3_build_receipt.py`.

The new `scripts/phase3_freeze_manifest.py` deterministically generates and
checks the concrete freeze inputs, with a narrow finalization path that binds
exactly one durable WSL receipt and one durable native receipt. Until both
receipt files exist and validate, the execution-package freeze remains
pre-freeze and the binary slots remain unbound. Its focused boundary checks are
in `scripts/test_phase3_freeze_manifest.py`. The current v4 successor freeze is
materialized from execution-tool/materialization snapshot
`48bd077d659a0d2fe6d672a33438b2ac3c85f126` under schema
`ck.exp-0002.phase3.freeze-manifest-4`, with manifest SHA-256
`092399ed48818b4e6bcf75db12fd6c022fdcbd70d60866eb9f4ddedf48864c72`.
It binds the experiment-wide closure tool, fixed binary cap, exact slot
reservation, runtime/platform observations, and the exact Python runtime
contract required by the exact-attempt entrypoint. The v4 successor binds
CPython `3.13.15` for both selectors and
the canonical isolated invocation
`python3.13 -I scripts/phase3_exact_attempt_launcher.py --launch-record <launch-record>`.
The launcher loads sibling modules by explicit file path, authenticates the
freeze/runtime/argv contract, reads one bounded canonical launch record and
its referenced records as exact bytes, and only then calls
`phase3_exact_attempt.run_exact_attempt`; its focused tests never execute a
candidate. The v2 freeze and its `Revise` reviews remain historical. The consolidated 296-test
suite passed before new E `762b04b8db3397cb1885d94236ad5d47cb321830`; the
older 267-test pass before historical v2 execution-tool commit
`9dca58a84072582db34045b8eac98d6e86d3d5ae` remains historical. No candidate
or exact experiment attempt has run and no native dispatch has occurred. The
v4 successor remains execution-disabled: the current materialization requires
fresh current-revision Gate B Double review, followed by
execution-disabled admission and artifact-custody preparation. An exact-
attempt authorization is created separately only after Ben explicitly
authorizes execution.

`development-unfrozen` remains the explicit state of the generated
corpus/request materialization. It is not a statement that the separately
bound execution package is unfrozen: once the canonical manifest has both
validated receipts, its execution-package freeze state is `frozen`. The
preregistration's pending-freeze fields are immutable Gate-A snapshot state;
the canonical freeze manifest supersedes those fields only for execution-
package freeze state. The preregistration is not rewritten by finalization or
preflight.

The manual `.github/workflows/phase3-gate-b-native-build.yml` workflow accepts
only a full 40-character commit SHA, runs on Ubuntu 24.04, recomputes the
candidate closure, performs the sanitized locked build, captures the build-only
receipt, and uploads a transfer-only bundle. It does not run the candidate,
perform an exact attempt, or dispatch the native experiment. The next internal
steps are the final current-revision Gate B Double reviews and their
admission/custody records. The committed receipts and v4 freeze artifact remain
build-only and execution-disabled; explicit Ben authorization for any
exact attempt or native dispatch follows those gates.

## Synthetic validation plumbing (development only)

The Phase 3 Python modules are implementation plumbing for exercising the
scoring boundary without running the experiment. The oracle, scorer, runner,
and receipt modules are pure in-memory Python: they do not open a candidate,
invoke Rust or a subprocess, use a path/executable, or create an attempt. The
read-only materialized-package adapter is the one package-reading boundary;
its result and receipt schemas remain deliberately non-evidence schemas. This
section describes the current implementation behavior; it does not add a wire
protocol, freeze the package, or alter the preregistered execution plan.

The modules and their in-memory entrypoints are:

- `phase3_common.py` provides strict UTF-8/JSON parsing with duplicate-member
  and non-finite rejection, bounded decimal admission, canonical JSON, exact
  `Fraction` conversion, rational intervals, directed integer-`isqrt` square
  root bounds, and binary64 bit conversion.
- `phase3_materialized_adapter.py` exposes the read-only
  `load_materialized_cases(package_root)` and
  `run_materialized(package_root, transcript)` entrypoints. The adapter
  validates the current closed materialization: the expected corpus,
  manifest, sqrt-vector, and `preregistration.json` layout; Proposed/planned,
  open, `technology_outcome: none`, execution-disabled preregistration; the
  `development-unfrozen`/`not_evidence`/`not_frozen` materialization flags and
  all preregistered artifact identities; the local generator's declared size
  and SHA-256 identity; the artifact manifest's schema, generator path, artifact
  paths, sizes, and SHA-256 values; the recipe manifest's 60
  ordered cases, five held-out families and strata, the fixed fixture
  declaration/hash and generated-source identities, threshold bits, request-ID
  formula, dispatch roles, typed expectations, and negative-relative control;
  and the 12-vector certified sqrt fixture. It
  then checks every request's existing protocol/operation/profile/providers,
  placeholder request ID and ordinal, source size/UTF-8 JSON/hash linkage, and
  exact binary64 tolerance bits. Files are bounded and read fail-closed: paths
  must be regular mode-0644 single-link files with no symlink components, and
  descriptor identity/size is checked before, during, and after reading;
  package, manifest, partition, preregistration, source, line/frame, request-ID,
  and numeric-token limits are enforced.
- The adapter projects exactly 8 development, 40 held-out, and 12 control
  records. Development and controls are observation-only (including the three
  `dispatch_to_candidate: false` preflight controls); held-out cases are the
  only internally scored role. `load_materialized_cases` deliberately omits
  recipe case IDs, construction metadata, `construction_target`, `source_truth`,
  and expected classes, keeping held-out cases opaque to callers. During
  `run_materialized`, expected held-out classes are retained only in the
  adapter's private handoff, and the materialized
  `p3-{attempt_id}-{global_ordinal:03d}` IDs are mapped internally to
  `synthetic/phase3/NNN`; a response must first echo its exact materialized ID
  before that echo is rewritten at the private boundary. Transcript keys are
  interpreted as materialized IDs only. Unknown keys, including an unpaired
  synthetic ID, are mapped to collision-free internal extra IDs for runner
  accounting and restored in the returned entries.
- `phase3_oracle.py` exposes `evaluate_source(source_text, metric)` and
  `verify_sqrt_vectors(vectors)`. The oracle consumes only serialized source
  text (or an in-memory vector sequence), independently maps basis/unit data,
  composes the Attachment equation, recomputes domain gates and typed
  zero-quaternion locations, and returns source-derived `I_truth` plus the
  expected nested witness. It does not import the materializer or read its
  generated records when the source is admitted; typed and out-of-domain
  results retain their corresponding bounded status instead.
- `phase3_scorer.py` exposes `score_response(request, oracle_result,
  response, expected_class=..., observation_only=...)`. It scores the actual
  Phase 2 response shape, not a simplified synthetic response invented for
  these tests.
- `phase3_runner.py` exposes `run_synthetic(cases, transcript)` (also
  exported as `run`). It accepts only a closed list of synthetic request-shaped
  dictionaries and an in-memory request-ID-to-response-bytes transcript, then
  calls the oracle and scorer. `dispatch_to_candidate: false` is a preflight
  decision only: its keyed response is not parsed or inspected, although an
  unconsumed transcript key is still reported as an extra response.
- `phase3_receipt.py` exposes `build_receipt(result)` (also exported as
  `synthetic_validation_receipt` and `receipt_bytes`). It rechecks the closed
  result/count/status algebra and emits a deterministic synthetic receipt.

The exact nested response scoring performed by `phase3_scorer.py` is:

1. For response bytes, enforce the 64 KiB frame limit and strict JSON; then
   enforce the closed top-level envelope, the existing response protocol ID,
   and an exact echoed `request_id`. An `observed` response must contain
   `observations` and no top-level `error` or `cause`. A typed non-`observed`
   response is supported only when its expected status and every expected
   stable cause field match the request; otherwise it is failed when
   contradictory or inconclusive when the candidate did not provide the
   expected typed response.
2. For an observed admitted response, require `observations.root` to equal
   the oracle source identity, tolerance fields to equal the request's exact
   binary64 bit encodings, and providers to equal the request selections with
   the expected unattested wrappers. Require exactly one complete root member
   with the expected identity/role and exactly one target Attachment whose
   provenance addresses, offset, and root-to-mating-owner path match the
   oracle.
3. Require the nested Attachment equation to contain the source-matching
   host/mating socket locals, every source-matching root-to-mating-owner part
   local, and exactly these five ordered operations and outputs:
   `attachment-containment`, `attachment-mating-socket`,
   `attachment-host-offset`, `attachment-inverse`, and
   `attachment-equation`. The reported authored root-local transform must
   match the oracle, and the reported derived root-local transform must equal
   the final equation output.
4. Compute `I_candidate` from the reported binary64 authored/derived root
   transforms: translation is the exact max component difference; rotation is
   the certified q/-q-equivalent full-chord interval. Combine it with the
   source-derived `I_truth` to compute `I_error`. Translation's threshold is
   `translation_absolute + translation_relative * translation_scale`; rotation's
   threshold is `2 * rotation_half_chord`. Candidate interval upper `<=`
   threshold is `agree`, lower `>` threshold is `conflict`, and a straddling
   interval is incomplete/inconclusive. A non-straddling class must agree with
   the nested `Attachment.outcome` and any expected class.
5. A candidate interval radius, error interval radius, or error upper endpoint
  above `1e-10` is incomplete/inconclusive. Otherwise an ordinary scored
  response is `supported`. A successfully adjudicated `observation_only` case,
  including a typed or out-of-domain control, is recorded as `observation`
  instead. Typed zero-quaternion controls require the exact
   typed skip code, `rotation` component, `zero-quaternion` cause, and oracle
   location. Malformed or missing evidence is inconclusive; a complete but
   contradictory witness is failed.

The runner applies this per-case result with deterministic aggregate
precedence: any `failed` entry makes the run `failed`; absent failures, any
`inconclusive` entry makes it `inconclusive`; observation-only entries cannot
support an aggregate by themselves. It counts preflight cases, dispatched
synthetic cases, observations, and extra responses, and never turns those
counts into experiment evidence. The receipt fixes `evidence_eligible: false`,
`technology_result: none`, null profile/freeze/authorization bindings,
`r3_activation: inactive`, empty tool identities, and zero candidate
process/request/response counts.

The pure in-memory bounds are 64 KiB per JSON frame/response, 24 KiB per
source, 256 UTF-8 bytes per request ID, at most 64 cases and 64 transcript
frames, and at most 4 MiB of transcript bytes. Numeric tokens are bounded to
256 bytes, 192 significant digits, and exponent/adjusted-exponent magnitude
2048; certified square-root bounds use 256-bit integer scaling and outward
interval endpoints use 96 decimal places. Stable cause strings are bounded
to 256 UTF-8 bytes and cause indices to one million. These are bounded test
inputs, not candidate process, filesystem, corpus, or experiment-attempt
execution.

Run the two focused modules directly from the repository root:

```bash
PYTHONWARNINGS=error python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_phase3_oracle_scorer.py
PYTHONWARNINGS=error python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_phase3_runner_receipt.py
```

They exercise only in-memory synthetic fixtures. They do not run
`generate_phase3.py`, `check_candidate_prebinding.py`, a candidate binary, a
Rust build, or an experiment process/attempt. The adapter test additionally
reads and copies the materialized package into temporary directories to test
its validation and file-safety boundary. The existing CI discovery command
now includes it through the `test_phase3_*.py` glob:

```bash
PYTHONWARNINGS=error python3 -m unittest discover \
  -s experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts \
  -p 'test_phase3_*.py' -v
```

All of these paths are development-only, never start a candidate/Rust
process, create an experiment attempt, or produce experiment evidence.

## Domain and transport contract

Canonical translation components and each contribution are at most `16 m` in
absolute value, with contribution infinity norms summing to at most `64 m`.
Quaternion components are finite and at most `1` in absolute value; source
quaternion norm is in `[0.5, 2]`, q/-q are equivalent, and near-zero input is
excluded. A path has at most four containment/composition edges per endpoint,
plus the single Attachment equation inverse/composition sequence.

After exact basis/unit/sign/inverse decomposition, each translation path has
ordered canonical-metre contributions `c_i`. Compute exactly rational
`S = sum(||c_i||_inf)` and `D = ||sum(c_i)||_inf`: `kappa_t = 1` when
`S = D = 0`, infinity when `D = 0 < S`, otherwise `S/D`. Then
`kappa_pair = max(kappa_t_authored, kappa_t_derived)`, with scored cases at
most `1e6`. Nonzero exact cancellation is admitted only as an analytic control
with the same certified interval cap; otherwise it is out of domain.

Quaternion conditioning is certified at high precision as
`kappa_q = max(1/||q_source||_2)` across source quaternions. It is at most 2
under the 0.5 norm floor. Chain limits and certified end-to-end intervals bound
accumulation; this is not an angular condition claim.

Inherited phase-two resource limits are frozen for this phase: 64 KiB JSONL
frame/response, 24 KiB source, 256 UTF-8-byte request ID, 64 records per
process, stdout cap equal to frame cap times records, 64 KiB stderr, 2 s I/O,
2 s shutdown, and a 0.02 s trailing-output quiet window. Strict UTF-8/JSON,
duplicate/nonfinite rejection, and oversize-drain/recovery remain required.
Before quaternion corpus execution, an independent sqrt/oracle self-check
must pass 12 vectors: four exact squares, four non-square certified brackets,
two scale metamorphics, and two domain-endpoint vectors.

Each request includes an opaque `request_id` of at most 256 UTF-8 bytes. IDs
are unique within an attempt and follow a frozen attempt/ordinal formula;
responses must echo the exact ID once. Missing, extra, colliding, mismatched,
trailing, or unaccounted responses fail closed as incomplete evidence. The
candidate receives protocol, operation, source, and tolerance tuple, so no
blindness is claimed: process length and tolerances can be inferred. Direct
role, family, truth, expected outcome, semantic-band, and scoring labels remain
withheld.

## Execution and evidence accounting

Each attempt uses one candidate and three fresh candidate processes: development
(8 case adjudications and 8 wire requests), held-out (40 and 40), and controls
(12 case adjudications and 9 wire requests), for 60 case adjudications and 57
candidate wire requests. The three control preflight cases are retained runner
adjudications and are not sent to the candidate. The preregistered plan is two
independent WSL2 x86_64 attempts for repeatability and one full native Ubuntu
24.04 x86_64 consistency attempt: 180 case adjudications, 171 candidate wire
requests, and nine fresh candidate processes total. Native evidence is bounded
consistency evidence, not broad portability. No automatic retry is allowed.

After a future pre-execution freeze, every attempt will use the same ordered
case, source, and tolerance bytes; request IDs are the only planned byte
substitution. The current materialized inputs remain development-unfrozen.
Cross-attempt comparison normalizes only those IDs and preregistered
environment/attempt metadata. WSL
repeats require exact equality of statuses, classifications, witness binary64
bits, certified interval endpoints, and retained semantic output; a fully
evidenced difference is failed determinism. Native requires the same semantic
equality; a fully evidenced mismatch is failed bounded consistency, while a
missing or uncomparable platform record is inconclusive.

For every process retain launch identity, exact argv/cwd/environment,
pre/post candidate-binary hash, pre/post FE/MXCSR state, request/response
counts and hashes, lifecycle/exit, clean shutdown, and missing/extra/trailing
output observations. Compare WSL attempts and native evidence separately.
Freeze expected platform selectors and retain CPU model/features,
architecture, kernel and WSL version where applicable, OS image/release,
filesystem type/mount context, workflow runner/image identity, toolchain, and
compiler. Selector mismatch is inconclusive unless it also proves a fully
evidenced semantic mismatch already classified failed.

Before execution, a freeze manifest must bind all outcome-affecting inputs:
protocol/profile, deterministic ledger/corpora, generator, oracle and sqrt
vectors, scorer, result/receipt schemas and writers, attempt-index schema,
writer and canonicalization, normalized path/mode/byte dependency closure,
exact build/run commands and flags/tool versions, candidate source/binary, and
runner/workflow definitions. Per-attempt
observations are created only at execution. Result and receipt are exclusive
post-execution outputs. The separate immutable attempt index binds the freeze-
manifest identity, unique attempt ID, platform/ordinal, exact Ben authorization
reference, result hash, and receipt hash. It hashes canonical envelope bytes
excluding its own hash. Nothing is overwritten or repaired in place.

## Proposed result, receipt, and Gate B preflight plumbing

The package now contains execution-incapable, in-memory Proposed contracts for
the future exact-attempt result, derived receipt, and immutable attempt index.
`scripts/phase3_evidence_contract.py` accepts only already-observed values and
returns canonical bytes; it does not launch a candidate, inspect a process,
read a package, or write a file. The result contract retains exact request and
response bytes and hashes, scorer/oracle context, process/platform/FE/MXCSR,
binary and transport observations, incomplete observations, and the derived
status. It enforces the preregistered 60 adjudications (8 development, 40
held-out, 12 controls), 57 dispatched requests and 3 preflight cases, three
ordered role processes (8/40/9 requests), and the normal 40 held-out
supported/20 observation status matrix for a complete correct synthetic
fixture. Status is derived with failed taking precedence over inconclusive;
observation-only entries cannot support a run by themselves.

Candidate wire bytes remain the exact seven-field request contract and are
separate from the hidden scorer context. Future candidate witness details are
retained as evidence data rather than inferred from summary labels. Receipts
must validate against the complete result bytes and bind their result hash;
the attempt index binds the result and receipt hashes and hashes its canonical
envelope while excluding only its own self-hash field. Domain-framed request
and response transport hashes, closed cross-bindings, and bounded partial
retention are contract checks, not execution evidence.

`scripts/phase3_gate_b_preflight.py` is a separate read-only non-evidence
preflight. It validates the materialized package and current Phase 3 tool
identities, then consumes the canonical freeze manifest through the existing
freeze/build-receipt validators. That binds and reports the manifest self-hash,
candidate source commit, runtime/provenance tool identities, exact WSL/native
receipt identities, binary slots, and execution-disabled readiness state. It
fails closed on canonical-manifest drift or tamper, missing or extra receipts,
and receipt/build mismatches. It does not create or rewrite a freeze manifest,
authorize an attempt, execute anything, create evidence, or pass Gate B. The
remaining blockers are the current-revision Double review of the frozen
concrete package and Ben's exact-attempt/native authorization. No R3 activation
or product/architecture decision follows from these validators.

Focused checks for this slice are:

```bash
PYTHONWARNINGS=error python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_phase3_evidence_contract.py
PYTHONWARNINGS=error python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_phase3_gate_b_preflight.py
PYTHONWARNINGS=error python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_phase3_exact_attempt_launcher.py
PYTHONWARNINGS=error python3 experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/test_phase3_freeze_manifest.py
```

These tests use only bounded in-memory or package-validation fixtures. They do
not run a candidate, Rust, Cargo, shell command, or experiment attempt.

## Gates and outcome

Gate A is complete/passed for this exact development-unfrozen materialization.
The fresh current-version Double review is recorded in [Review 01](reviews/gate-a-review-01-closure-integrity.md)
and [Review 02](reviews/gate-a-review-02-numeric-claims.md); prior issue-finding
reviews remain stale historical working evidence. The v4 successor execution
package is now frozen under the manifest identity above, but final current-
revision Gate B Double reviews and admission/custody/authorization records
remain pending. No exact attempt or native dispatch has been executed. Ben's
authorization will be requested only after those gates, and does not imply
profile selection, production binding, or R3 authorization.

Only the following conformance outcomes are allowed:

- `failed` takes precedence when at least one fully evidenced admissible
  classification, witness, typed control, deterministic semantic output,
  repeatability, or bounded-consistency assertion is false, even if other
  evidence is incomplete;
- otherwise `inconclusive` applies to incomplete transport/process/identity/
  environment/oracle evidence, wide or threshold-straddling intervals, or a
  platform comparison unable to support the claim; and
- otherwise `supported` requires complete evidence and every mandatory
  assertion to pass.

This package makes no 10:1 loss/ranking claim, does not validate the profile
values, and cannot bind production semantics, activate R3, or make a visual or
product-quality claim.

# Numeric and frame profile

Status: Proposed canonical specification; exact activation constants remain
experiment-gated

This Batch 12 update is Proposed and does not resolve C1 canonical collection
ordering/tie handling, C3 immutable Readiness 2/3 implementation binding, or
C4 diagnostic-domain/bootstrap compatibility. Those findings remain open in
the current decision records; no numeric, resolver, fixture, or adapter gate
activates from this document.

This document owns the semantic coordinate basis, Readiness 2 rigid-transform
carrier, Readiness 3 numeric validity/canonicalization boundary, and typed
comparison-profile shape. The [body-document contract](../body-document/README.md)
owns source admission and the [body-graph contract](../body-graph/README.md)
owns graph meaning and frame ownership. This profile does not select an engine
matrix layout, bone format, IK representation, deformation solver, or runtime
pose storage.

## Canonical semantic basis

The initial semantic basis is:

- right-handed coordinates;
- metres as the canonical length unit;
- `+Y` as creature-up; and
- `+Z` as creature-forward.

Directions are named semantic directions, not engine-specific axis strings.
Source documents declare their own basis and are normalized into this basis
with conversion provenance. An adapter may use another storage or display
convention, but it must identify the conversion at the boundary.

Transforms are conceptually column-vector, local-to-parent transforms. For a
local point `p_local`,

`p_parent = rotate(q, p_local) + t`.

For a composition `A <- B <- C`, the rightmost transform is applied first.
This is a semantic convention; storage order, matrix packing, and API naming
remain implementation choices as long as they preserve it.

## Readiness 2 carrier

Readiness 2 freezes only the structural rigid-transform carrier:

```text
translation: array of exactly 3 scalar values
rotation:    array of exactly 4 scalar values in explicit x, y, z, w order
```

Scale and shear fields are not part of this carrier. A transform with an
additional scale/shear member, the wrong array length, or a different rotation
component order is malformed for this profile. This structural rule does not
yet select exact scalar encoding, admissible ranges, normalization tolerances,
or comparison constants.

## Readiness 3 numeric semantics

Readiness 3 freezes the following admission and semantic rules. Exact
conditioning thresholds, normalization bounds, and comparison tolerances are
profile data and remain activation-gated; an implementation must not invent
them.

### JSON decimal admission

After strict JSON syntax, token, and resource checks, a JSON number token is
interpreted as an exact signed decimal rational. The conversion to binary64 is
directly correctly rounded using round-to-nearest, ties-to-even. It must not
use a host floating-point intermediate, locale rules, an ambient rounding mode,
or implementation-dependent wider/narrower precision. Exact rational parsing
and conversion are charged against the lexical/resource profile before any
unbounded materialization.

The result is admitted when it is finite, except that a nonzero exact rational
that rounds to either signed zero is rejected. Finite nonzero subnormals are
valid; canonical operations must not enable flush-to-zero (FTZ) or denormals-
are-zero (DAZ). Overflow to infinity is rejected. Precision is accepted for as
long as the token remains within the declared lexical/resource bound; there is
no arbitrary semantic digit cutoff. A lexical negative zero is accepted when
its exact rational is zero, then normalized to `+0` in semantic and canonical
values. The raw source representation retains the original bytes.

These rules make ordinary inexact values such as decimal `0.1` deterministic
without treating their decimal spelling as an exact binary64 value. Alternate
decimal spellings that denote the same rational may therefore normalize to the
same binary64 value while remaining distinct raw source bytes.

### Quaternion validity

Quaternion components are finite binary64 values and the quaternion is not zero
or otherwise within the profile's forbidden near-zero region. `q` and `-q`
represent the same rotation. Normalization is permitted only within the
versioned experiment-set drift bound. Canonical quaternion sign is chosen by
the first nonzero component in the order `w`, `x`, `y`, `z` being positive; if
all components are zero or within the forbidden region, the transform is
malformed. Malformed, non-finite, non-normalizable, or out-of-range values are
rejected.

## Typed comparison profiles

Comparison is typed rather than governed by one global epsilon. Exact discrete
values—including addresses, collection membership, enums, profile IDs,
provenance, diagnostics, schema/revision identifiers, and operation outcomes—
remain exact.

For a scalar and for each translation component, a pair `a`, `b` passes when

`|a - b| <= A + R * max(|a|, |b|)`

where `A` and `R` are finite, nonnegative entries selected by the comparison
profile. The comparison is inclusive.
The implementation must evaluate this predicate with stable checked
arithmetic, avoiding overflow, underflow, cancellation, and ambient floating-
point modes; a finite binary64 result cannot be accepted or rejected merely
because an unchecked intermediate overflowed. Translation vectors use the
componentwise L-infinity rule: every component must pass its named translation
entry. Stable evaluation obtains a same-sign difference by ordered magnitudes,
an opposite-sign difference by a checked magnitude sum, and evaluates the
right-hand bound in a checked scaled representation (or an equivalent
monotonic comparison). Mathematical overflow of an intermediate therefore
cannot silently turn the predicate into a pass or fail.

Quaternion comparison first normalizes both quaternions under the selected
normalization rule. Let `d = dot(qa, qb)`, choose `s = +1` when `d >= 0` and
`s = -1` otherwise (the `d == 0` tie therefore chooses `+1`), and compute the
stable half-chord in the fixed order

`h = 0.5 * ||qa - s qb||2`.

Then compute `theta = 4 * asin(clamp(h, 0, 1))` and accept exactly when
`theta <=` the named angular tolerance. Dot, subtraction, and norm components
use the carrier order `x,y,z,w` with left-to-right checked accumulation;
normalization uses the same order. The principal mathematical `asin` is
evaluated under the profile's deterministic binary64 elementary-function rule.
The dot product, signed subtraction, norm, clamp, and `asin` evaluation order
is fixed by this sequence; no alternative q-sign tie or approximate identity
test is permitted.

For transforms, form the residual `E = B * inverse(A)` using the selected
semantic composition convention. Compare the residual translation and rotation
through their named scalar/component and quaternion/angular comparison entries;
the residual is not compared by an unnamed approximate-identity shortcut.

For competing authoritative claims with the same normalized target (owner
address, property role, and frame/context), compare every unordered pair. All
pairs must pass; there is no transitive clustering, first-winner rule,
approximate identity, or deduplication rule. Any failing pair produces a
deterministic `invalid-source` conflict, with no successful snapshot. The
normalized binary64 representative tuple is value-type-specific: scalar
`(value)`; translation/vector `(x,y,z)` in declared semantic component order;
quaternion `(x,y,z,w)` after normalization and q/-q/sign canonicalization; and
rigid transform `(tx,ty,tz,qx,qy,qz,qw)`. Any later numeric type must define its
tuple in this profile before use. Lexicographic comparison uses an exact total
order over normalized finite binary64 values, with `-0` already normalized;
stable claim identity breaks ties only when tuples are identical. Retain
provenance for every claim. This representative selection is local to a claim
target and does not define canonical ordering for unrelated unordered
collections. Adding a passing claim can change the representative and hence a
snapshot; the comparison profile or fixture successor governs that change.

The authored-conflict and expected-snapshot profiles remain distinct, and
their constants are experiment-gated. Comparison profiles identify the
numeric/frame revision, scalar/transform rules, every tolerance entry, and
whether a comparison is exact or semantic. A missing or unsupported required
profile revision is unsupported and must not fall back to a global default.
Expected graph snapshots record their comparison-profile identity and
exact-or-semantic rule in the [fixture-manifest contract](../fixture-manifest/README.md).

## Required boundary fixtures

The Readiness 3 successor fixture set must bind and exercise ordinary inexact
decimal `0.1`, exact values, halfway/ties-to-even values, the maximum-finite
boundary and overflow, the smallest subnormal and nonzero underflow-to-zero,
excessive precision at the lexical/resource bound, lexical signed zero, and
alternate decimal spellings. In-bound precision must be admitted; a token
exceeding the declared lexical/resource bound exercises `resource-limit`, not
an arbitrary semantic digit cutoff. Fixtures must distinguish raw source bytes
from normalized `+0` and normalized binary64 values and must bind the separate
authored-conflict and expected-snapshot comparison profiles. Exact profile
identifiers, constants, expected bytes, and expected digests remain
activation-gated and are owned by the fixture-manifest admission transaction.

## Future adapter conformance

An adapter is a separate boundary after Readiness 3; this profile selects no
engine. It must declare an explicit signed-permutation orthogonal map `C` for
the three semantic axes (`C` has entries in `{-1, 0, +1}` and
`C^T C = I`). The adapter must document named-direction mapping, handedness
and any reflection, and map vectors and translations as `v' = C v` in the
declared unit basis. For a core rotation matrix `R`, it must map
`R' = C R C^-1`; for a homogeneous rigid transform `H`, it must map
`H' = diag(C, 1) H diag(C^-1, 1)`. Quaternion conversion must be performed
through that matrix mapping or a proven equivalent, preserving q/-q
equivalence and the declared quaternion convention.

Conformance must exercise named directions, reflections/handedness,
composition, inverse, quaternion sign equivalence, and core-to-adapter-to-core
round trips. A separate target-precision profile governs correctly rounded
narrowing, finite overflow, subnormal preservation, nonzero-to-zero underflow,
angular and translation budgets, and any target numeric limits. It must fail
closed for overflow or disallowed underflow and must not saturate, clamp, or
depend on an ambient numeric mode. The core snapshot remains binary64; target
precision is an adapter/output concern. Adapter activation is a separate
post-Readiness-3 transaction with its own fixtures and profile binding.

## Activation boundary

Readiness 2 may admit the structural carrier only as part of the exact schema
and fixture transaction. Readiness 3 is a separate successor transaction that
admits this profile's canonical basis/numeric rules, expected graph snapshots,
comparison profiles, and their resolver binding. Until those transactions are
admitted, the rules above are Proposed and no resolver or numeric fixture is
activated.

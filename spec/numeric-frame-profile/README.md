# Numeric and frame profile

Status: Proposed canonical specification; exact activation constants remain
experiment-gated

This Batch 13 update is Proposed. It records the approved comparator, claim
identity, and future-adapter directions while preserving the separate
canonical-collection, Readiness 2/3 binding, and diagnostic/bootstrap owners.
No numeric, resolver, fixture, or adapter gate activates from this document.

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
represent the same rotation. The deterministic normalization path scales by
the exact maximum absolute component, divides the fixed `x,y,z,w` components
by that scale, accumulates squares strictly left-to-right without
reassociation or FMA contraction, uses correctly rounded binary64 square root,
then performs fixed division. It validates finite, nonzero, and profile bounds
at each required boundary. The canonical sign is chosen by the first nonzero
component in the order `w`, `x`, `y`, `z` being positive. If all components are
zero or within the forbidden region, the transform is malformed. Malformed,
non-finite, non-normalizable, or out-of-range values are rejected. The profile
requires round-to-nearest, ties-to-even, with FTZ/DAZ and ambient rounding
controls disabled; a required correctly rounded square root that is unavailable
is unsupported. Near-zero and drift thresholds remain evidence-gated.

## Typed comparison profiles

Comparison is typed rather than governed by one global epsilon. Exact discrete
values—including addresses, collection membership, enums, profile IDs,
provenance, diagnostics, schema/revision identifiers, and operation outcomes—
remain exact.

For a scalar and for each translation component, a pair `a`, `b` passes when

`|a - b| <= A + R * max(|a|, |b|)`

where `A` and `R` are finite, nonnegative entries selected by the comparison
profile. The comparison is inclusive. Mathematically, each finite binary64 is
decoded as a signed integer significand times a power of two. The implementation
must perform the subtraction, multiplication, addition, and comparison as
exact bounded dyadic/integer operations (with explicit bounds for any required
temporary), with no rounded intermediate and no equivalent-monotonic freedom.
An input or intermediate outside the declared finite domain is rejected or
unsupported according to the profile; it cannot silently become a pass or
fail through overflow, underflow, cancellation, or an ambient floating-point
mode. Translation vectors use the componentwise L-infinity rule: every
component must pass its named translation entry.

Quaternion comparison first normalizes both quaternions under the deterministic
path above. Let `d = dot(qa, qb)`, choose `s = +1` when `d >= 0` and
`s = -1` otherwise (the `d == 0` tie therefore chooses `+1`). Set
`di = qa_i - s qb_i` in fixed `x,y,z,w` order and accept exactly when the
dyadic sum `sum(di^2) <= (2H)^2`, where `H` is the profile's finite binary64
angular half-chord bound. The dot, subtraction, square, sum, and comparison
are exact dyadic/integer operations; no runtime `asin`, `sin`, norm, or square
root is used by comparison. `H` is derived offline from an independent
high-precision oracle/generator revision and is the greatest binary64 value
no greater than the exact `sin(theta/4)` for the declared angular threshold.
The profile stores the exact theta/H bits and derivation metadata. No
alternative q-sign tie or approximate-identity test is permitted.

For same-target claims, normalize every value into the identical canonical
local-to-parent frame and compare translations directly componentwise and
rotations by the q/-q predicate above. The comparison is invariant under
claim order and does not form a residual. A residual may be retained as a
separately named composition diagnostic or snapshot check with its own profile
semantics; it is not the same-target validity predicate.

For competing authoritative claims with the same normalized target (owner
address, property role, and frame/context), compare every unordered pair. All
pairs must pass; there is no transitive clustering, first-winner rule,
approximate identity, or deduplication rule. Any failing pair produces a
deterministic `invalid-source` conflict, with no successful snapshot. Group
claims by their stable structured claim ID first: same ID with the same
normalized value is evaluated once while retaining every occurrence and its
provenance; same ID with a different normalized value is an invalid-source
collision. Evaluate valid pairs in lexicographic claim-ID order and report the
first failing sorted pair; pair validity itself is unordered.

The normalized binary64 representative tuple is value-type-specific: scalar
`(value)`; translation/vector `(x,y,z)` in declared semantic component order;
quaternion `(x,y,z,w)` after normalization and q/-q/sign canonicalization; and
rigid transform `(tx,ty,tz,qx,qy,qz,qw)`. Any later numeric type must define its
tuple in this profile before use. Lexicographic comparison uses exact total
order over normalized finite binary64 values (`-0` is already `+0`), defined by
the mathematical value or an equivalent sign-aware bit key; claim ID breaks a
tie only when the entire value tuple is exactly equal. Preserve all provenance,
including unselected claims. The representative rule is local to a claim
target and does not define canonical ordering for unrelated unordered
collections.

Stable claim identity is structured from the canonical target, claim kind,
source document/namespace identity, stable authored semantic record/property
address, and an explicit authored claim key when multiple intentional claims
are allowed. It never uses a raw JSON pointer, array/traversal/allocation
order, thread, time, or generated identifier. A raw pointer may remain
diagnostic provenance only. Local claim-ID/multiplicity is separate from the
generic canonical collection key; graph concept collections use their own
structured address and owner-role/claim collection key.

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
from normalized `+0` and normalized binary64 values; verify exact dyadic scalar
predicates against a rational oracle and inclusive ULP boundaries; bind the
same-target common-frame/order-reversal, duplicate/collision, sorted-pair,
and smallest-tuple claim-ID fixtures; and bind the separate authored-conflict
and expected-snapshot comparison profiles. Exact profile identifiers,
constants, expected bytes, and expected digests remain activation-gated and
are owned by the fixture-manifest admission transaction.

## Future adapter conformance

An adapter is a separate boundary after Readiness 3; this profile selects no
engine. It must declare an explicit signed-permutation orthogonal map `C` for
the three semantic axes (`C` has entries in `{-1, 0, +1}` and `C^T C = I`) and a
finite positive scale `s` in engine-units per metre. Vector length quantities
(points, translations, and displacements) map as `s C v`; scalar length
quantities (dimensions, radii, and extents) map as `s v`. Directions and
normalized normals map as `C v` with no scale. For a core
rotation matrix `R`, it maps `R' = C R C^-1`; for a homogeneous rigid transform
`H`, with `D = diag(sC, 1)`, it maps `H' = D H D^-1` and uses `D^-1` for the
reverse direction. Quaternion conversion must use that matrix conjugation or a
proven equivalent, preserving q/-q equivalence and the declared quaternion
convention. Raw covector semantics may be deferred until a contract needs
them; normalized normals are not covectors and receive no scale.

There are two proposed conformance tiers. The default tier covers storage and
output conversion only and makes no runtime arithmetic claim. An optional
runtime-conformance tier adds runtime probes and fixtures. Both tiers declare
target precision, domain and narrowing rules, finite overflow/underflow and
subnormal policy, and translation/angular budgets. Binary32 may exclude values
whose correctness depends on subnormals; a subnormal runtime claim requires an
FTZ/DAZ probe, otherwise the required capability is unsupported. Overflow or
disallowed underflow fails closed; conversion never saturates, clamps, or uses
an ambient numeric mode. Fixtures cover known magnitude (`s=1` and nonunit),
directions/no-scale, transform conjugation, composition/inverse/reflection/q,
round trips, and overflow/underflow/subnormal cases. The core snapshot remains
binary64. Adapter activation is a separate post-Readiness-3 transaction with
its own fixtures and profile binding.

## Activation boundary

Readiness 2 may admit the structural carrier only as part of the exact schema
and fixture transaction. Readiness 3 is a separate successor transaction that
admits this profile's canonical basis/numeric rules, expected graph snapshots,
comparison profiles, and their resolver binding. Until those transactions are
admitted, the rules above are Proposed and no resolver or numeric fixture is
activated.

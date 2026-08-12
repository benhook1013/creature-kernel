# Numeric and frame profile

Status: Proposed canonical specification; exact activation constants remain
experiment-gated

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

Readiness 3 freezes the following semantic rules, with exact thresholds and
tolerances admitted only after a reproducible numerical experiment:

- semantic scalar values are finite IEEE-754 binary64 values;
- values that cannot be represented as finite binary64 under the active profile
  are rejected, rather than rounded silently into a different semantic value;
- negative zero is normalized to positive zero in the semantic and canonical
  model;
- quaternion components are finite and the quaternion is not zero or otherwise
  within the profile's forbidden near-zero region;
- `q` and `-q` represent the same rotation;
- normalization is permitted only within the future experiment-set drift bound;
- canonical quaternion sign is chosen by the first nonzero component in the
  order `w`, `x`, `y`, `z` being positive; if all components are zero or within
  the forbidden region, the transform is malformed; and
- malformed, non-finite, non-normalizable, or out-of-range values are rejected.

No unselected epsilon, conditioning constant, or tolerance may be invented by
an implementation. The experiment must record hardware/profile, inputs,
reproduction command, measured drift, and limitations before the values become
an activation prerequisite.

## Typed comparison profiles

Comparison is typed rather than governed by one global epsilon.

Exact comparison applies to discrete values: addresses, collection membership,
enums, profile IDs, provenance, diagnostics, schema/revision identifiers, and
operation outcomes. Numeric comparison uses an absolute-plus-relative form,
with separate versioned entries for at least translation, angular rotation,
quaternion equivalence, and transform-composition residuals. The authored-
conflict profile and expected-snapshot profile are distinct: an authored
conflict may use a domain tolerance to decide invalidity, while a fixture
snapshot may use a separately named tolerance to compare a resolved result.

Comparison profiles identify the numeric/frame profile revision, scalar and
transform rules, each tolerance entry, and whether a comparison is exact or
semantic. They are data, not prose. A missing or unsupported required profile
revision is unsupported; it must not fall back to a global default.

Expected graph snapshots record their comparison-profile identity and exact or
semantic comparison rule in the [fixture-manifest contract](../fixture-manifest/README.md).

## Activation boundary

Readiness 2 may admit the structural carrier only as part of the exact schema
and fixture transaction. Readiness 3 is a separate successor transaction that
admits this profile's canonical basis/numeric rules, expected graph snapshots,
comparison profiles, and their resolver binding. Until those transactions are
admitted, the rules above are Proposed and no resolver or numeric fixture is
activated.

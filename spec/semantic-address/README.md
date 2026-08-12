# Semantic-address profile

Status: Proposed canonical specification; no resolver or schema is activated

This document is the canonical owner of the machine representation and
comparison rules for durable semantic addresses. The [body-graph contract](../body-graph/README.md)
owns which records need an address and the [body-document contract](../body-document/README.md)
owns source admission. This profile does not define filesystem paths, display
names, mesh identity, or artifact identity.

## Address representation

An address is one typed object with exactly these conceptual members:

```json
{
  "namespace": "core",
  "anchors": ["body", "left_arm"],
  "kind": "part",
  "role": "forearm"
}
```

`namespace` identifies the owning source namespace. `anchors` is an ordered,
outer-to-inner sequence of authored module-instance or structural anchors; it
may be empty for a top-level record. `kind` identifies the identity-bearing
concept. `role` is the role-local key within that kind and anchor context.
Member order is not semantic. The future exact encoding must reject missing,
duplicate, or extra members in this core object rather than silently ignoring
them.

The current closed `kind` vocabulary is:

`part`, `joint`, `socket`, `attachment`, `region`, `capability`, and `field`.

An authored module-instance declaration has a stable declaration address, but
it is source-scope identity rather than an additional embodied `kind` in this
closed vocabulary. Landmark, anchor, dimension, and frame records are owned
records addressed by their owner and role; they do not introduce new address
kinds. Unsupported kinds are rejected as unsupported rather than treated as
opaque identity.

## Lexical profile

`namespace`, every `anchors` member, and `role` use the same exact lexical
profile: one ASCII lowercase letter followed by zero or more ASCII lowercase
letters, decimal digits, or underscores (`[a-z][a-z0-9_]*`). Length bounds are
owned by the active resource profile and are not hidden in this syntax rule.
`kind` uses the closed lowercase vocabulary above. There is no case folding,
Unicode normalization, locale behaviour, delimiter escaping, filesystem
interpretation, or implicit index.

Display labels, authored prose, and Unicode names are separate metadata. They
may explain an address to a human but never participate in address equality,
reference resolution, ordering, or identity digests. An address component is
not a path segment and must not be used as one without a separate safe-path
mapping.

## Equality and references

Two addresses are structurally equal exactly when their four typed members are
equal after the profile's ASCII lexical validation and their `anchors` arrays
have the same length and element-by-element order. Object-member order is
ignored; array order is significant. No display label, source-document order,
mesh position, or generated array index can make unequal addresses equal.

References use the same object representation and structural equality. A
reference either resolves to one address in the admitted source set or emits a
deterministic missing/ambiguous/unsupported diagnostic under the owning
operation contract. Namespace ownership and authored collision-free remapping
are handled by the body-graph/source contracts; remapping must cover every
contributed address from the colliding namespace and may not silently rewrite
only the conflicting record.

The address profile is revisioned. A change to member meaning, lexical rules,
closed kinds, anchor ordering, or equality changes the profile identity and
invalidates the affected compatibility claims. Structural editing may create
new addresses, but it never changes an existing address's meaning in place.

## Resource and activation boundary

The active resource profile bounds the number of anchors and the lengths of all
lexical components. Implementations must enforce those bounds before accepting
an address into a graph or using it for unbounded lookup work. Malformed
lexical content is source-invalid; an otherwise valid address exceeding an
active resource bound is resource-limited.

This profile becomes implementation-relevant only when its exact schema,
resource profile, and fixture cases are admitted through the
[fixture-manifest contract](../fixture-manifest/README.md). Representative
cases must cover empty and nested anchors, malformed lexical values, unknown
kinds, object-member reordering, array-order inequality, duplicate addresses,
and namespace collision/remapping. No schema or parser is activated here.

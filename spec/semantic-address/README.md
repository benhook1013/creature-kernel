# Semantic-address profile

Status: Proposed canonical specification; CK-KICK-012 Batch 13/14 discussion-
approved identity cross-link; no resolver or schema is activated

Current Batch 13/14 material is recorded in DR-0006 Revision 12, DR-0011 Revision
15, DR-0012 Revision 14, and DR-0013 Revision 12; each remains Proposed with
Owner approval Pending and Review Pending. This profile remains a Proposed
identity input and does not activate a parser, resolver, schema, or fixture.

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

When this address is used as the owner-declared canonical key for an unordered
collection, its typed total order compares components in exactly this
precedence: `namespace` by the restricted profile's normalized
Unicode-scalar lexical order (the current machine profile is an ASCII subset),
ordered `anchors` lexicographically with prefix before extension, `kind` by
its frozen rank table, then `role` by that same identifier order. The current
address-kind rank table is frozen in the existing vocabulary order: `part` 0,
`joint` 1, `socket` 2, `attachment` 3, `region` 4, `capability` 5, and
`field` 6. A missing or malformed address fails closed; a collision is
rejected when the owning collection is semantically unique. Repeated records
must use the owning contract's explicit occurrence, claim, context, or
multiset identity rather than source order or array index. Canonical-data owns
the generic keyed-collection algorithm and each collection's multiplicity rule;
this profile owns address structure, lexical validity, equality, and this
address ordering. The comparator shape and activation gate are frozen here;
changing the address-kind vocabulary or rank table requires a profile successor.

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

## Conceptual claim-id-1

Authored measurement and transform claims use versioned conceptual
`claim-id-1`, a structured tuple of `(canonical_target, claim_kind,
source_document_namespace, authored_record_address, typed_property_role,
explicit_claim_key_or_absent)`. `canonical_target` is the normalized semantic
target; `claim_kind` is a closed, typed kind; source-document/namespace
identity is typed and normalized. The authored record address and typed
property role are durable and stable across parser traversal and object-member
order; the explicit claim key is present only for schema-permitted intentional
repeated claims. The tuple has the wire-independent component order and
conceptual comparator defined below. An unordered pair is
canonically `(min_id, max_id)`.

The selected claim-ID comparator is wire-independent. Its component precedence
is exactly the existing six-field order:
`canonical_target`, `claim_kind`, `source_document_namespace`,
`authored_record_address`, `typed_property_role`, and
`explicit_claim_key_or_absent`. The target uses the owning structured
semantic-address order above. Closed claim kinds and typed property roles use
profile-defined semantic tag ranks, not serialized enum spelling. Typed source
document/namespace identities and each semantic-address segment use the same
restricted normalized identifier Unicode-scalar lexical order; structured
address tuples and anchor sequences use prefix-before-extension. The claim-key
sum type orders absent before present, and present keys use that identifier
order. The claim-kind and typed-property-role rank tables are mandatory,
versioned activation inputs. Each table must be complete and injective over its
admitted closed set; missing, duplicate, or unknown kind, role, or rank entries
fail activation. An activated schema must bijectively map wire values to these
conceptual types/ranks and may not infer order from wire spelling. The
claim-ID comparator is fully total only for an activated profile containing
both tables; this proposal freezes its shape and gate, not later rank values.
No canonical claim ordering, digest, or resolver activation may occur before
both tables exist.

Same-ID occurrences with the same normalized value are evaluated once while
all occurrence/provenance records remain. Same-ID occurrences with different
normalized values are an invalid-source identity collision. Different IDs are
evaluated as all unordered pairs in this total order; the first failing pair
is the deterministic conflict representative, and the lexicographically
smallest value tuple is selected only after every pair passes. Exact wire field
spellings remain deferred to schema activation. A raw JSON pointer is
diagnostic provenance only: an activated source schema must provide the stable
record address, typed property role, and multiplicity key required by this
profile.

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

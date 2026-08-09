# CK-KICK-010 walking skeleton

This is an unregistered, disposable exploratory host for CK-KICK-010. It is
not `EXP-0001`, a formal experiment registration, a production architecture,
or a durable body-document/body-graph contract. The host is intentionally
small enough to replace after the exploratory seam is understood.

## Scope

The temporary JSON fixtures describe a rooted typed ownership tree. The
stdlib-only resolver validates the envelope, required module labels, unique
source labels, side metadata, finite transforms and parameters, supported
primitive kinds, parent/socket references, reachability, and cycles. It then
returns a serializable graph containing each node's parent-local transform,
explicit resolved world 4x4 transform, named sockets, and capsule/ellipsoid
primitive data.

The valid fixture contains torso, pelvis, head, muzzle, paired arms and hand
paws, paired digitigrade thigh/shin-hock/foot-paw chains, and an asymmetric
optional left ear attached through a declared head socket. The invalid fixture
has the same required shape except that `right_shin` is absent. Its resolver
result is exactly one `MISSING_REQUIRED_MODULE` validation diagnostic and no
graph; the missing-module check runs before parent/socket cascade validation.

No fields, NumPy geometry, marching cubes, meshing, attribution, artifact
publication, or CLI are implemented here. The scientific dependencies are
declared for the later disposable host stages, while this resolver and its
tests use only the Python standard library.

## Environment and commands

The intended interpreter is Python >= 3.10 (the local baseline is Python
3.10.12). From this directory, install the disposable host dependencies with:

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
```

Run the focused resolver tests with:

```bash
python3 -m unittest tests/test_resolver.py
```

## Temporary coordinates and rotations

All distances are metres in a right-handed frame with `+Y` up, `+Z`
creature-forward, and `-X` creature-right. JSON rotations use unit
quaternions in `[x, y, z, w]` order. Matrices use the conventional row-major
4x4 representation for column-vector transforms. A root's world transform is
its local transform. For every other node the resolver composes:

```text
world = parent_world * parent_socket_local * node_local
```

This coordinate and rotation convention is spike-only. Labels are deterministic
for identical input under the same `spike_revision`; they are not durable
cross-revision semantic IDs.

## Future disposable seams

The next bounded host stages may consume the graph through these replaceable
seams: analytic capsule/ellipsoid field evaluation, deterministic composition,
surface extraction, mesh validation, source-linked debug-region attribution,
and artifact writing. Scientific-library types should remain inside those
adapters rather than entering the temporary graph interface. A future CLI may
consume `ValidationResult`, `Diagnostic`, and `ResolvedGraph.to_dict()` without
parsing diagnostic prose; its command spelling is intentionally left to the
CLI worker.


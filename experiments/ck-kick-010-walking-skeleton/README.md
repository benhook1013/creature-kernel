# CK-KICK-010 walking skeleton

This directory contains the implemented, unregistered CK-KICK-010 disposable
exploratory host. It is not `EXP-0001`, a Stage 1 proof, a production
selection, or a durable body-document/body-graph contract. Its outputs are
evidence about this bounded spike only and must not be used as performance,
runtime, or production claims.

## Isolated environment

From the repository root, create an environment for this disposable host and
install its pinned dependencies:

```bash
python3 -m venv /tmp/ck-kick-010-venv
. /tmp/ck-kick-010-venv/bin/activate
cd experiments/ck-kick-010-walking-skeleton
python -m pip install -r requirements.txt -r requirements-dev.txt
```

The host uses the existing stdlib resolver, NumPy/scikit-image field and
marching-cubes adapters, trimesh structural checks, and project-owned artifact
and export seams. Scientific-library objects do not enter the resolved graph
or artifact contracts.

The temporary coordinates are metres in a right-handed frame with `+Y` up,
`+Z` creature-forward, and `-X` creature-right. JSON rotations use unit
quaternions in `[x, y, z, w]` order and the resolver emits row-major world
transforms. Child transforms resolve as
`parent_world * parent_socket_local * node_local`. The identity export retains
this basis and verifies the asymmetric `left_ear` landmark on positive X.

## Headless build

The output parent must already exist. The target itself must not exist; there
is no overwrite option. Defaults are `GeometryConfig` values of 128 samples
per axis, 0.10 metres of padding, and smooth-min `k=0.10`. The three values
may be overridden for a reversible debug run.

```bash
mkdir -p /tmp/ck-kick-010-outputs
python -m ck_spike build \
  --input fixtures/valid.json \
  --output /tmp/ck-kick-010-outputs/valid \
  --samples-per-axis 32
```

The command prints exactly one canonical JSON result. Exit `0` means a valid
build and publishes exactly:

```text
manifest.json
resolved_graph.json
mesh.ply
semantic_regions.json
diagnostics.json
```

`mesh.ply` is deterministic ASCII PLY 1.0 with vertices, outward vertex
normals, and triangular faces in artifact-local order. The semantic-region
sidecar contains one winner-only source-node label per PLY vertex and makes no
durable-identity or weight claim. The manifest records non-self artifact
hashes, exact geometry/grid/mesh metadata, source/build identity, coordinate
convention, identity export transform, and the asymmetric `left_ear`
landmark check.

The intentionally invalid fixture is validated before geometry:

```bash
python -m ck_spike build \
  --input fixtures/invalid-missing-right-shin.json \
  --output /tmp/ck-kick-010-outputs/invalid \
  --samples-per-axis 32
```

Exit `2` publishes only `diagnostics.json` and `manifest.json`; the primary
diagnostic is `MISSING_REQUIRED_MODULE`, and no graph, mesh, or region output
is present. Field/mesh failures exit `3` without a final target. Artifact,
publication, and unexpected failures exit `4` without overwriting an existing
target. The output parent is not created by the command.

## Tests and exact rerun comparison

Run the focused end-to-end and seam tests with:

```bash
python -m pytest -q
```

To compare two valid runs byte-for-byte, use two new targets:

```bash
mkdir -p /tmp/ck-kick-010-outputs
python -m ck_spike build --input fixtures/valid.json \
  --output /tmp/ck-kick-010-outputs/run-a --samples-per-axis 16
python -m ck_spike build --input fixtures/valid.json \
  --output /tmp/ck-kick-010-outputs/run-b --samples-per-axis 16
for name in diagnostics.json manifest.json mesh.ply resolved_graph.json semantic_regions.json; do
  cmp -- /tmp/ck-kick-010-outputs/run-a/$name /tmp/ck-kick-010-outputs/run-b/$name
done
sha256sum /tmp/ck-kick-010-outputs/run-a/*
sha256sum /tmp/ck-kick-010-outputs/run-b/*
```

The observed byte equality is same-environment evidence for this disposable
implementation. It does not establish cross-platform bit identity, Stage 1
success, performance limits, runtime behavior, or production suitability.

# Disposable current-form surface preview

This is an exploratory visual workbench for the exact four-variant
`creature-kernel.provisional-form-preview.v4` envelope. It converts the
temporary integer descriptors into analytic ellipsoid, capsule, and
linear-radius tapered-segment fields, folds them in stable full-AddressKey
order, and extracts a bounded continuous surface on a fixed uniform grid.

It is not a production geometry system, SDF contract, collision system,
animation topology, rig, skin, runtime, Readiness 3/4 proof, or DR-0009/0010
evidence. Winner labels are debug attribution only. Generated bundles belong
in `/tmp` and must not be committed.

## Run

Create an isolated environment outside the repository and install the small
experiment-local dependency set:

```bash
python3 -m venv /tmp/ck-current-form-surface-venv
. /tmp/ck-current-form-surface-venv/bin/activate
python -m pip install -r experiments/current-form-surface-preview/requirements.txt
```

The input must be a successful v4 inspection envelope. The output directory
must not already exist, and its parent must already exist:

```bash
mkdir -p /tmp/ck-current-form-surface
python experiments/current-form-surface-preview/generate_surface_preview.py \
  --input /tmp/form-v4.json \
  --output /tmp/ck-current-form-surface/run-a \
  --samples-per-axis 72
```

The successful bundle contains exactly the manifest and four sets of PLY,
semantic-winner sidecar, metrics JSON, and neutral composite PNG. The PNG has
fixed front, side, and three-quarter panels. Repeating the same input and
configuration on the same host produces byte-identical outputs; no timestamps
or temporary paths are embedded. The output contains no committed artifact
policy exception: keep it ephemeral under `/tmp`.

Focused tests:

```bash
python -m unittest discover -s experiments/current-form-surface-preview/tests
```

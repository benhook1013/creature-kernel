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

The compiler-owned middle seam is a private regional guide representation
derived separately for each of the four validated variants. It carries stable
source AddressKey ownership and provenance, the fixed prototype axes and
parent topology, axial pelvis/girdle and chest/waist controls, craniofacial
and neck transitions, per-segment limb centerlines and thickness profiles
with explicit joint-narrowing values, paw/forefoot controls, and tail
centerline/taper controls. These guides are internal derivation data: they
are neither semantic nodes nor a serialized contract, and they contain no
marching-cubes grid, mesh topology, SDF encoding, or renderer operation.
Their controls are backend-neutral only at this prototype level; path
primitive intent is retained so this disposable analytic-field adapter can
preserve capsule versus tapered-segment meaning. The adapter emits the
temporary fields and applies joint narrowing to joint collars, so this seam
may intentionally alter limb and joint-collar preview geometry while preserving source identity,
bundle layout, and recipe accounting.

The renderer expands each source descriptor into a bounded, deterministic
role recipe where useful. The current fixture convention supplies shared
chest/waist/hip masses, a broader axial trunk transition, cranium and muzzle,
a parent-surface neck/collar, source-owned shoulder masses plus limb root and
joint collars, tapered hip-to-thigh transitions, digitigrade lower-leg shaping,
paw/foot masses, and a smoothly rooted straight tail with a full midsection and
short blunt distal taper. Recipe components are fields,
not semantic nodes: every generated component keeps its source descriptor as
owner and the semantic sidecar emits only source AddressKeys. Limb and root
bridges are anchored on the parent analytic-field boundary in the existing
axis-aligned fixture convention; arbitrary orientation is not claimed. Recipe
expansion therefore fails closed unless the envelope contains the exact 18-Part
stylized-biped role/parent layout with a mirrored left/right body, +Y as up,
+Z as foot/muzzle forward, and -Z as the straight-tail direction. The expected
ellipsoid centres, capsule endpoints, and tapered-tail endpoints must also
remain bound to their source reference points. This is a deliberate preview
restriction, not a local-frame or general morphology contract.

The manifest metrics report both source descriptor count and actual generated
field count, including the field-memory bound used for allocation. This is
resource accounting for the disposable preview only, not a runtime budget or
future compiler contract.

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

One generator invocation emits all four fixed variant subdirectories; do not
run it separately per variant.

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

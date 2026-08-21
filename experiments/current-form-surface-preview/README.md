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
parent topology, ordered pelvic-girdle/waist/chest-girdle stations with short
station transitions, compact shoulder and hip root controls at limb roots,
craniofacial and neck transitions, piecewise tapered limb sections with
endpoint-owned elbow/knee/hock stations, private source-derived digitigrade
foot-chain controls, and tail
centerline/taper controls. These guides are internal derivation data: they
are neither semantic nodes nor a serialized contract, and they contain no
marching-cubes grid, mesh topology, SDF encoding, or renderer operation.
Their controls are backend-neutral only at this prototype level; path
primitive intent is retained so this disposable analytic-field adapter can
preserve capsule versus tapered-segment meaning. The adapter emits each named
piecewise section and joint station as source-owned fields while preserving
source identity, bundle layout, and recipe accounting.

The renderer expands each source descriptor into a bounded, deterministic
role recipe where useful. The current fixture convention supplies ordered
pelvic/chest girdle and narrow-waist masses joined by two short tapered station
bridges, cranium and muzzle, a parent-surface neck/collar, source-owned
compact shoulder and hip root controls plus embedded limb root bridges, tapered hip-to-thigh
transitions, piecewise limb profiles, endpoint joint stations, simple
two-stage hand paws, source-derived digitigrade foot chains from the existing
hock through a tapered metatarsal, planted paw pad, and forward toe box, and
a smoothly rooted straight tail with a full midsection and short blunt distal
taper. Recipe components are fields,
not semantic nodes: every generated component keeps its source descriptor as
owner and the semantic sidecar emits only source AddressKeys. Limb and root
bridges are anchored on the torso cage boundary for torso-owned roots, or the
parent analytic-field boundary for other attachments, in the existing
axis-aligned fixture convention; arbitrary orientation is not claimed. Recipe
expansion therefore fails closed unless the envelope contains the exact 18-Part
stylized-biped role/parent layout with a mirrored left/right body, +Y as up,
+Z as foot/muzzle forward, and -Z as the straight-tail direction. The expected
ellipsoid centres, capsule endpoints, and tapered-tail endpoints must also
remain bound to their source reference points. This is a deliberate preview
restriction, not a local-frame or general morphology contract.

The skin adapter embeds torso-owned root and hip connectors toward the child by
their support radius. Their guide-side boundary anchors remain visible in the
regional sidecar, while the compiled field uses the embedded centreline; the
separate shoulder/hip mass controls remain diagnostic and are not emitted as
additional skin fields.

The manifest metrics report both source descriptor count and actual generated
field count, including the field-memory bound used for allocation. This is
resource accounting for the disposable preview only, not a runtime budget or
future compiler contract.

The disposable v2 generator writes one private `regional-guide.json` and one
`guide-skin-composite.png` for each variant, alongside the retained
`surface.ply`, `semantic.json`, and `metrics.json` artifacts. The regional
guide sidecar is a sanitized, source-owned debug projection of `_HybridGuide`:
it carries only source AddressKeys, compiled recipe counts, projection
names/bases, one shared world-space render bound, fixed canvas/layout metadata,
and finite regional controls. Its v4 `torso_cage` controls compile into the
successor's private frame-aware ordered profile sweep: they retain
pelvis/torso owner AddressKeys, fixed guide axes/orientation, seven ordered
elliptical cross-sections from
pelvis through the shoulder ribcage, and six connections between adjacent
sections. The guide renderer draws these sections as rings/contours in the
front, side, and three-quarter x-ray panels. The older ordered axial
`stations` (`pelvic-girdle`, `waist`, `chest-girdle`) and `transitions`
(`pelvis-waist`, `waist-chest`) remain only as a clearly marked
`compatibility-diagnostic-not-rendered` sidecar view; they are not rendered and
are not the skin-driving controls. Limb controls expose
named tapered sections, consumed profile radii, source-owned root/hip bridges,
named endpoint joint stations, and exact parent anchors for hand/foot
attachments. Forearm controls have no elbow station, avoiding duplicate joint
ownership. Foot controls expose the existing source-owned hock, a tapered
metatarsal, planted paw-pad and forward toe-box masses, plus a guide-only
contact datum. Shoulder controls retain bilateral anterior/posterior support
curves for x-ray inspection, but mark them `guide-only`; only the
upper-arm-owned deltoid sweep remains skin-driving in this disposable
analytic adapter. The sidecar and manifest therefore report the exact
compiled recipe inventory separately from the richer private guide controls;
hands retain a simple paw mass and attachment. It is not a semantic or runtime
contract and contains no
descriptor input records or synthetic semantic IDs. The composite places guide and compiled
skin panels adjacent for each of front, side, and three-quarter projections.
Guide and skin panels use exactly the same projection framing, while one shared
render bound is used for all four variants so geometry differences remain
directly comparable. Mesh extraction retains each variant's own field bounds
and grid spacing; the shared render bound does not define sampling.

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
semantic-winner sidecar, metrics JSON, regional-guide JSON, and guide/skin
composite PNG. Repeating the same input and configuration on the same host
produces byte-identical outputs; no timestamps or temporary paths are
embedded. The output contains no committed artifact policy exception: keep it
ephemeral under `/tmp`.

## Disposable successor consumer

The separate successor consumer is a disposable exploratory proof. Its current
bounded slice replaces only the torso and shoulder surface construction; it
explicitly bridges the baseline fields for the head, neck, limbs, paws, and
tail. It is neither a permanent backend selection nor the active human visual
checkpoint. The [active runway](../../docs/project/status.md#active-runway)
defines the baseline-versus-successor browser comparison that must be reached
before human appraisal.

After creating and activating the experiment virtual environment described
above, the workflow has two steps:

```bash
cargo run -p creature-kernel-cli -- inspect-provisional-form \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  > /tmp/form-v4.json

mkdir -p /tmp/ck-successor-surface
python experiments/current-form-surface-preview/generate_successor_surface_preview.py \
  --input /tmp/form-v4.json \
  --output /tmp/ck-successor-surface/run-a \
  --samples-per-axis 48
```

Use `--samples-per-axis 48` for this bounded slice. Lower values within the
accepted argument range may still validly fail mesh-connectedness validation;
successful generation is not guaranteed at every in-range sampling value.

A successful run writes `successor-surface-manifest.json` plus four variant
directories. Each variant directory contains exactly `surface.ply`,
`metrics.json`, and `successor.json`. This slice does not yet produce PNGs or
publish a visual-gallery session.

Focused tests:

```bash
python -m unittest discover -s experiments/current-form-surface-preview/tests
```

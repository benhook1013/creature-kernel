# Disposable current-form surface preview

This is an exploratory visual workbench for the exact four-variant
`creature-kernel.provisional-form-preview.v8` envelope. It converts the
source-authored dimension-backed integer descriptors into analytic ellipsoid, capsule, and
linear-radius tapered-segment fields, folds them in stable full-AddressKey
order, and extracts a bounded continuous surface on a fixed uniform grid.

It is not a production geometry system, SDF contract, collision system,
animation topology, rig, skin, runtime, Readiness 3/4 proof, or DR-0009/0010
evidence. Winner labels are debug attribution only. Generated bundles belong
in `/tmp` and must not be committed.

The compiler-owned middle seam is a private regional-guide v7 representation
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
regional sidecar, while the compiled field uses the embedded centreline. The
successor shoulder consumer separately uses the authored shoulder peak/axilla
controls and frame axes described below; the bilateral support curves remain
guide-only.

The manifest metrics report both source descriptor count and actual generated
field count, including the field-memory bound used for allocation. This is
resource accounting for the disposable preview only, not a runtime budget or
future compiler contract.

The disposable v2 generator writes one private `regional-guide.json` and one
`guide-skin-composite.png` for each variant, alongside the retained
`surface.ply`, `semantic.json`, and `metrics.json` artifacts. The regional
guide v7 sidecar is a sanitized, source-owned debug projection of `_HybridGuide`:
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
contact datum. Shoulder controls retain authored peak/axilla anchors, vertical
and depth radii, and frame axes. The successor consumes them as exactly two
ordered, deterministic, frame-aware five-section lateral profile sweeps, one
per side: `torso-interior`, `torso-boundary`, `authored-shoulder`,
`upper-arm-socket`, and `upper-arm-midpoint`. The first two sections are
torso-owned; the authored shoulder, socket, and midpoint sections are matching
`upper_arm`-owned, with the last two overlapping the existing upper-arm sweep.
A shoulder-specific finite-span evaluator rejects malformed frames and axes
and keeps representative remote points away from accidental zero crossings.
The bilateral support curves remain `guide-only`; no arm root bridge or distal
deltoid field is emitted. The sidecar and manifest therefore report the exact
compiled recipe inventory separately from the richer private guide controls;
hands retain a simple paw mass and attachment. It is not a semantic or runtime
contract and contains no
descriptor input records or synthetic semantic IDs. The composite places guide and compiled
skin panels adjacent for each of front, side, and three-quarter projections.
Guide and skin panels use exactly the same projection framing, while one shared
render bound is used for all four variants so geometry differences remain
directly comparable. Mesh extraction retains each variant's own field bounds
and grid spacing; the shared render bound does not define sampling.

The successor keeps these concerns independent: the manifest generator's
`padding` is the successor mesh sampling padding (default `0.50`), while its
`capture_padding` is sourced from the baseline generator default and frames
the shared guide/skin captures (currently `0.75`). This preserves the
successor's known-good mesh grid while keeping default baseline and successor
capture frames exactly comparable.

## Run

Use the repository-owned launcher for every experiment Python command. It
selects the already-created interpreter from
`CK_CURRENT_FORM_SURFACE_PYTHON`, or by default from the native-Linux XDG
cache (`$XDG_CACHE_HOME/creature-kernel/current-form-surface-venv/bin/python`
or `$HOME/.cache/creature-kernel/current-form-surface-venv/bin/python`). It
checks the pinned dependencies and imports before each command, and replaces
inherited Windows `TMPDIR`/`TEMP`/`TMP` values with a verified native-Linux
temporary root. `CK_CURRENT_FORM_SURFACE_TMPDIR` may select an existing,
writable native-Linux directory explicitly. The launcher does not create an
environment or install packages.

Create the isolated environment once, outside the repository, and install the
small experiment-local dependency set explicitly:

```bash
surface_preview_launcher=experiments/current-form-surface-preview/surface_preview_launcher.sh
surface_preview_venv_root="${XDG_CACHE_HOME:-$HOME/.cache}/creature-kernel/current-form-surface-venv"
mkdir -p "$(dirname "$surface_preview_venv_root")"
python3 -m venv "$surface_preview_venv_root"
surface_preview_python="$surface_preview_venv_root/bin/python"
"$surface_preview_python" -m pip install -r experiments/current-form-surface-preview/requirements.txt
```

For a disposable `/tmp` environment, set
`CK_CURRENT_FORM_SURFACE_PYTHON=/tmp/ck-current-form-surface-venv/bin/python`
when invoking the launcher.

The input must be a successful v8 inspection envelope. The output directory
must not already exist, and its parent must already exist:

```bash
mkdir -p /tmp/ck-current-form-surface
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_surface_preview.py \
  --input /tmp/form-v8.json \
  --output /tmp/ck-current-form-surface/run-a \
  --samples-per-axis 72
```

One generator invocation emits all four fixed variant subdirectories; do not
run it separately per variant.

The direct successor applies the same baseline raw-input bound,
`surface_preview.MAX_INPUT_BYTES` (currently 4 MiB). Inputs at or below the
inclusive bound continue to normal UTF-8/JSON validation; an oversized input
fails with `input exceeds bounded size` before output staging or mesh work.

The successful bundle contains exactly the manifest and four sets of PLY,
semantic-winner sidecar, metrics JSON, regional-guide JSON, and guide/skin
composite PNG. Repeating the same input and configuration on the same host
produces byte-identical outputs; no timestamps or temporary paths are
embedded. The output contains no committed artifact policy exception: keep it
ephemeral under `/tmp`.

## Disposable successor consumer

The separate successor consumer is a disposable exploratory proof. Its current
bounded slice replaces the torso, shoulders, head, neck, four bilateral
limb-chain consumers, bilateral hand/foot consumers, and tail. The head/neck
consumer uses source-authored head/neck profile controls projected through the
regional guide. It retains exact source AddressKey ownership and provenance
for all eight ordered profile sections and seven connections across all four
variants. The projection preserves branched route lineage: a vertical
neck/cranium route from `neck-collar` through `cranium-crown`, and a forward
muzzle route from `cranium-mid` through `muzzle-tip`; centres, radii, endpoints,
thicknesses, and fixed axes come from each private guide. The successor
hand/foot boundary consumes
ordered hand attachment/paw sweeps and shin-to-foot digitigrade chains,
including guide-owned hock, metatarsal, pad, and toe controls. The successor
tail boundary consumes six source-owned tail elements (root source,
attachment, collar mass, tip source, extension, and cap); baseline fields
remain an explicit bridge only for two thigh root connectors and two hip
transitions. The two arm root bridges are replaced by the authored shoulder
sweeps above; no baseline tail, paw, or foot component remains. The shared
tail source/extension endpoint retains its independently authored profiles;
this experiment does not claim that the resulting tail silhouette or visual
quality has been observed or accepted.
It is neither a permanent backend selection nor the active human
visual checkpoint. The [active runway](../../docs/project/status.md#active-runway)
defines the baseline-versus-successor browser comparison that must be reached
before human appraisal.

The shoulder slice is an authored, disposable consumer intended to test
frame-aware profile continuity and bounded field behavior around the torso and
upper-arm join. It does not establish anatomical realism, production topology,
general morphology support, or the quality of the final visual result; those
remain unproven until the named visual checkpoint is reviewed.

After creating and activating the experiment virtual environment described
above, the workflow has two steps:

```bash
cargo run -p creature-kernel-cli -- inspect-provisional-form \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  > /tmp/form-v8.json

mkdir -p /tmp/ck-successor-surface
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_successor_surface_preview.py \
  --input /tmp/form-v8.json \
  --output /tmp/ck-successor-surface/run-a \
  --samples-per-axis 56
```

Use `--samples-per-axis 56` for this experiment preview. The lean fixture
aliases into disconnected sampled components at 48, so 56 is the documented
preview resolution. This does not solve production topology or minimum-feature
robustness; lower values within the accepted argument range may still validly
fail mesh-connectedness validation, and successful generation is not guaranteed
at every in-range sampling value.

A successful v5 run writes `successor-surface-manifest.json` plus exactly four
variant directories. Each variant directory contains exactly
`surface.ply`, `metrics.json`, `successor.json`, and one
`guide-skin-composite.png`. The PNG is a deterministic RGB capture at the
baseline-compatible `1800 × 570` canvas. It contains the exact six-panel order
`front-guide`, `front-skin`, `side-guide`, `side-skin`,
`three-quarter-guide`, `three-quarter-skin`: each projection has adjacent guide
and skin panels using the same projection frame, and all four variants use one
shared world-space render bound computed from the canonical baseline field
sets. The manifest and successor sidecars expose the profile identity, canvas,
layout, projections, and shared bounds alongside the four-artifact inventory.
The manifest generator configuration reports both independent padding values:
`padding` controls successor mesh sampling and `capture_padding` controls the
baseline-compatible shared capture frame.
Each manifest variant record and its `successor.json` sidecar also carries
`source_variant_sha256`, the 64-character lowercase SHA-256 digest of the
exact canonical raw producer variant object (`_canonical(raw_variant)`). This
is a deterministic source-record binding, not an artifact hash; the two
locations must agree for each variant, and distinct producer variants have
distinct digests.

The generator alone writes this disposable bundle; it does not publish a
visual-gallery session. The active
[`publish_surface_preview.py`](../../dev-tools/visual-review/README.md#disposable-baseline-versus-successor-surface-checkpoint)
workflow runs the current producer and both generators, validates the bundles,
and publishes the baseline-versus-successor captures through the visual-review
gallery.

Focused tests:

```bash
"$surface_preview_launcher" -m unittest discover -s experiments/current-form-surface-preview/tests
```

The same interface runs publishers and other Python entrypoints, for example:

```bash
"$surface_preview_launcher" dev-tools/visual-review/publish_surface_preview.py --help
```

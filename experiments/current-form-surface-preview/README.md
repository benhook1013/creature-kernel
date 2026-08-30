# Disposable current-form surface preview

This is an exploratory visual workbench for the exact four-variant
`creature-kernel.provisional-form-preview.v11` envelope. It converts the
source-authored dimension-backed integer descriptors into analytic ellipsoid, capsule, and
linear-radius tapered-segment fields, folds them in stable full-AddressKey
order, and extracts a bounded continuous surface on a fixed uniform grid.

It is not a production geometry system, SDF contract, collision system,
animation topology, rig, skin, runtime, Readiness 3/4 proof, or DR-0009/0010
evidence. Winner labels are debug attribution only. Generated bundles belong
in `/tmp` and must not be committed.

The integrated candidate is producer v11 with `authored_foot_profile` v1:
153 authored dimensions, 43 authored landmarks, and 16 authored frames. The
current diagnostic target is baseline preview format v3, regional guide v11,
and successor preview v9. Producer v11 and `authored_foot_profile` v1 remain
the source identities. The current successor region/profile identity is
`successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-profile-sweeps-v15`
after adding full-volume hand stations and source-control-preserving muzzle
composition.
The exact foot route is `hock -> metatarsal midpoint -> pad ->
pad-toe midpoint -> toe`: the hock is shin-owned, the other four stations are
foot-owned, and the route carries full lateral/up/forward radii, outer caps,
four spans, and exact producer/guide/successor lineage and cross-binding.
The final publication context cap is 12 KiB only for the exact subject-context
carrier; ordinary strings remain capped at 8192 characters. Existing
immutable sessions retain the format and captures with which they were
published. This diagnostic is published as a new immutable checkpoint; it
does not rewrite an older session.

The compiler-owned middle seam is a private regional-guide v11 representation
derived separately for each of the four validated variants. It carries stable
source AddressKey ownership and provenance, the fixed prototype axes and
parent topology, ordered pelvic-girdle/waist/chest-girdle stations with short
station transitions, compact shoulder and hip root controls at limb roots,
craniofacial and neck transitions, exact projected bilateral five-station
authored arm and leg profiles with anisotropic elbow/knee/hock compatibility
masses, piecewise tapered limb sections with endpoint-owned elbow/knee/hock
stations, private source-derived digitigrade
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
successor arm consumer separately uses the authored arm profile and shared
upper-arm-owned elbow seam described below. No successor arm root bridge or old
underarm support is emitted.

The manifest metrics report both source descriptor count and actual generated
field count, including the field-memory bound used for allocation. This is
resource accounting for the disposable preview only, not a runtime budget or
future compiler contract.

The disposable v3 generator writes one private `regional-guide.json` and one
`guide-skin-composite.png` for each variant, alongside the retained
`surface.ply`, `semantic.json`, and `metrics.json` artifacts. The regional
guide v11 sidecar is a sanitized, source-owned debug projection of `_HybridGuide`:
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
attachments. The authored arm profile is projected into exactly five ordered
stations per side: `upper-arm-start`, `upper-arm-midpoint`, `elbow`,
`forearm-midpoint`, and `forearm-distal`. The elbow is one shared
upper-arm-owned seam; the guide also carries its authored anisotropic
compatibility mass, while the forearm owns the distal station. No per-variant
station tuning is introduced. Foot controls expose the exact five-station route
`hock -> metatarsal midpoint -> pad -> pad-toe midpoint -> toe`: the hock is
inherited from the shin-owned authored leg profile, while the remaining four
stations are foot-owned. The route carries full lateral/up/forward radii, outer
caps, four spans, and exact producer/guide/successor lineage and cross-binding.
The guide also retains a contact datum. Shoulder controls retain authored peak/axilla anchors, vertical
and depth radii, and frame axes. The successor consumes them as exactly two
ordered, deterministic, frame-aware five-section lateral profile sweeps, one
per side: `torso-interior`, `torso-boundary`, `authored-shoulder`,
`upper-arm-socket`, and `upper-arm-midpoint`. The first two sections are
torso-owned; the remaining sections are matching `upper_arm`-owned controls.
A shoulder-specific finite-span evaluator rejects malformed frames and axes
and keeps representative remote points away from accidental zero crossings.
The current producer also carries bilateral `authored_leg_profile` v1:
five ordered stations per side (`thigh-start`, `thigh-midpoint`, `knee`,
`shin-midpoint`, `hock-endpoint`), owned `thigh/thigh/thigh/shin/shin`, and
30 source-authored lateral/up/forward radii with shared variant factors. The
guide projects those exact stations and exposes anisotropic
`leg-profile-segment` fields with lateral/up/forward radii at each endpoint.
The successor separately consumes the authored arm profile as four routes
(left/right upper arm and left/right forearm) and the authored leg profile as
two bilateral five-station routes. Each route consumes all three authored
lateral/up/forward radii; the shared elbow seam is exact and upper-arm-owned.
Arm, leg, and foot span profiles sample their transverse radii with the same
bounded shape-preserving interpolation used by the torso, retaining every
authored station exactly without inventing intermediate extrema.
The bilateral support curves remain
`guide-only`; no successor arm root bridge or distal deltoid field is emitted,
and no per-variant station tuning is used. The sidecar and manifest report the
exact compiled recipe inventory separately from the richer private guide
controls. The hands retain a simple paw mass and attachment. It is not a
semantic or runtime contract and contains no descriptor input records or
synthetic semantic IDs.

The three-layer diagnostic keeps the compatibility filename
`guide-skin-composite.png`, but each image is now `1800 × 1500` RGB with columns
`front`, `side`, and `three-quarter`, and rows `CONTROL GUIDE` (derived
controls, not evaluated geometry), `CONSUMED FIELDS` (the exact component
level-0 surfaces before smooth union, evaluator-backed, with debug colours),
and `FINAL SKIN` (the neutral smooth-union result). Guide-only controls may
appear in row 1, `CONTROL GUIDE`, without affecting rows 2 or 3. The consumed
row is made from the actual `Field`/`_Component` operands; recipe names and
colours are diagnostic implementation identities only, not semantic nodes,
materials, or hard seams, and not accepted DR-0010 evidence. All rows use the
same projection framing and shared render bound for direct comparison across
the four variants. Mesh extraction retains each variant's own field bounds
and grid spacing; the shared render bound does not define sampling.

The successor keeps these concerns independent: the manifest generator's
`padding` is the successor mesh sampling padding (default `0.50`), while its
`capture_padding` is sourced from the baseline generator default and frames
the shared three-layer captures (currently `0.75`). This preserves the
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

The input must be a successful v11 inspection envelope. The output directory
must not already exist, and its parent must already exist:

```bash
mkdir -p /tmp/ck-current-form-surface
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_surface_preview.py \
  --input /tmp/form-v11.json \
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
hand/foot boundary consumes ordered hand attachment/paw sweeps and shin-to-foot
digitigrade chains. Each hand-paw station retains the shared outward route plus
its source-derived outward/up/forward volume, while the foot chain retains the
shin-owned hock seam and foot-owned metatarsal, pad, and toe controls. The
successor
tail boundary consumes six source-owned tail elements (root source,
attachment, collar mass, tip source, extension, and cap); baseline fields
remain an explicit bridge only for two thigh root connectors and two hip
transitions. The successor v9 region
`successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-profile-sweeps-v15`
uses four authored arm-profile routes plus two authored leg-profile routes.
The authored leg routes retain the thigh-owned knee and shin-owned hock, and
each foot route is exactly `hock -> metatarsal midpoint -> pad -> pad-toe midpoint
-> toe`, with the hock shin-owned and all other stations foot-owned. The two arm
root bridges and old underarm supports are absent; the shared upper-arm-owned
elbow seam consumes all three authored radii. Exactly four temporary
thigh-root/hip bridges remain: one root bridge and one hip transition per
side. No duplicate legacy leg mass is retained, and there is no per-side or
per-variant station tuning. No baseline tail, paw, or foot component remains. The shared
tail source/extension endpoint retains its independently authored profiles;
this experiment does not claim that the resulting tail silhouette or visual
quality has been observed or accepted.
It is neither a permanent backend selection nor an acceptance decision. The
published form gallery is historical PR #113 evidence. Ben's 2026-08-24
appraisal of immutable checkpoint
`authored-form-expressivity-exact-field-components-checkpoint-v2` successor v9
accepts only that source-authored controls and procedural field routes cover
the required regions and produce a connected whole-body surface. Its neck is
visibly occluded or lost, its torso and pelvis read as rounded rectangular/
blocky, and the overall body is not convincing realistic or anatomical skin;
visual region readability remains failed or inconclusive. These are
limitations of this disposable candidate, not canonical geometry
prescriptions. Publication machinery is not acceptance.

The shared-pose structural embodiment gallery below has completed its named
human checkpoint: it was appraised "looks good" and merged through PR #114.
No further cosmetic repair is planned. It remains a disposable companion
consumer of this preview's generated surfaces, not a production architecture
claim. Its four-profile candidate set and semantic pose payload are frozen
before evidence; the current display variants are not automatic substitutes.
It uses generated, not illustrative, neutral/posed surface, skeleton/bone,
weight/influence, and collision-proxy artifacts with source/build/scenario
lineage. See `docs/project/status.md` for the current named human checkpoint
and active runway.

The experiment-local `structural_profile_candidates.json` freezes four source
candidate IDs used by the completed gallery:
`compact_broad_short_limb_large_head`, `tall_narrow_long_legged`,
`slender_long_limb`, and `stocky_broad_chested`. Generate their compact canonical
BodyDocuments through one shared data-driven transform:

```bash
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py --check
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py \
  --output-dir /tmp/ck-structural-profile-sources
```

The transform changes exact integer Part placements and source-authored
permille form dimensions, retains the stable unit neck-to-head reference edge,
preserves normalized route controls and identity rotations, and keeps all four
tail modules present while varying tail length and taper. It fails closed on
incomplete targets, overlapping or uncovered dimension groups, broken
bilateral/alignment/Attachment invariants, unsafe values, or non-atomic output.
These are candidate source fixtures and lineage evidence, not public morphology
limits or a production parameter system.

The authored arm slice is a disposable consumer intended to test frame-aware
profile continuity and bounded field behavior around the torso, upper-arm, and
elbow join. It does not establish anatomical realism, production topology,
general morphology support, or the quality of the final visual result. It is
historical surface evidence and is not the structural embodiment checkpoint.

After creating and activating the experiment virtual environment described
above, the workflow has two steps:

```bash
cargo run -p creature-kernel-cli -- inspect-provisional-form \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  > /tmp/form-v11.json

mkdir -p /tmp/ck-successor-surface
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_successor_surface_preview.py \
  --input /tmp/form-v11.json \
  --output /tmp/ck-successor-surface/run-a \
  --samples-per-axis 56
```

Use `--samples-per-axis 56` for this experiment preview. The lean fixture
aliases into disconnected sampled components at 48, so 56 is the documented
preview resolution. This does not solve production topology or minimum-feature
robustness; lower values within the accepted argument range may still validly
fail mesh-connectedness validation, and successful generation is not guaranteed
at every in-range sampling value.

A successful v9 run writes `successor-surface-manifest.json` plus exactly four
variant directories. Each variant directory contains exactly
`surface.ply`, source-owned winner `semantic.json`, `metrics.json`,
`successor.json`, and one
`guide-skin-composite.png`. The PNG is a deterministic RGB capture at the
baseline-compatible `1800 × 1500` canvas. Its three columns are `front`,
`side`, and `three-quarter`; its rows are `CONTROL GUIDE`, `CONSUMED FIELDS`,
and `FINAL SKIN` as described above. Publication metadata records
`panels_per_view: 3`. The manifest and successor sidecars expose the profile
identity, canvas, layout, projections, and shared bounds alongside the
five-artifact inventory. The semantic sidecar uses the same source-only
AddressKey winner boundary as the baseline and carries no synthetic rig or
bone semantics. It binds the exact ordered `surface.ply` bytes and exact raw
producer variant by SHA-256; its label count is bounded by and must equal the
validated PLY vertex count.
The manifest generator configuration reports both independent padding values:
`padding` controls successor mesh sampling and `capture_padding` controls the
baseline-compatible shared capture frame.

The first structural-embodiment bridge slice consumes one successful
`inspect-structure` result, its matching provisional-form result, the complete
successor bundle, a separately named candidate source profile, and one neutral
surface variant:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  > /tmp/structure.json

"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_embodiment_bridge.py \
  --inspect-structure /tmp/structure.json \
  --inspect-provisional-form /tmp/form-v11.json \
  --surface-bundle /tmp/ck-successor-surface/run-a \
  --candidate-profile-id authored_baseline_v0 \
  --surface-variant-id neutral-v0 \
  --output /tmp/ck-structural-bridge/run-a
```

Use a native Linux output parent because the bridge publishes with Linux
atomic no-replace directory semantics. The candidate artifact derives a rooted
bone hierarchy, complete semantic-Joint mapping, bounded normalized weights,
and collision capsules from a deterministic nearest-eligible-bone surface
partition. It also records any source Part that won no final-surface vertices;
that absence remains evidence rather than being filled with invented semantic
ownership. Its synthetic root starts at the exactly reproducible complete
neutral-surface centroid and ends at the source root Part reference, with a
deterministic farthest-vertex fallback for a coincident centroid. This first
slice emits no pose or posed surface. It is a direct
prerequisite to, not a substitute for, the shared-pose structural embodiment
gallery.

The completed gallery was built only after all four frozen profiles had
successful neutral bridge bundles and matching hash-bound structure and
neutral-surface inputs:

```bash
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_embodiment_gallery.py \
  --bridge-root /tmp/ck-structural-gallery-inputs/bridges \
  --neutral-ply-root /tmp/ck-structural-gallery-inputs/neutral-surfaces \
  --structure-root /tmp/ck-structural-gallery-inputs/structures \
  --source-manifest /tmp/ck-structural-profile-sources/manifest.json \
  --output /tmp/ck-structural-embodiment-gallery
```

Each input root must contain exactly the four frozen candidate IDs; structure
files use `<profile-id>.json`. The required generated source manifest binds
each profile to its generated source document and is copied into the gallery
inventory. The consumer rejects non-identity source Joint frames instead of
inventing unrecorded frame semantics. It applies the one
checked-in deterministic pose without IK or contact, performs classic linear
blend skinning, transforms the generated collision capsules, and publishes one
scale-consistent `1800 x 2500` PNG per profile. Every PNG uses the same global
world bound and has front, side, and three-quarter columns over five rows. The
side column is an exact orthographic projection. Skeleton rows are explicit
x-ray overlays drawn without skin depth occlusion, so internal and far-side
bones remain visible for inhabitation review; their visibility does not imply
an oblique camera. The five rows are neutral skin plus skeleton, posed skin plus
skeleton, dominant-bone/max-weight evidence, neutral skin plus proxies, and
posed skin plus proxies. The root
manifest inventories the pose and every per-profile neutral/posed surface,
skeleton, weight, proxy, metric, and gallery artifact. These remain disposable
candidate-scoped evidence, not runtime rig, solver, anatomy, or topology
contracts.

After generation, validate and publish only the four profile PNGs into one
immutable visual-review group:

```bash
"$surface_preview_launcher" dev-tools/visual-review/publish_structural_embodiment.py \
  --root /home/ben/.cache/creature-kernel/visual-reviews \
  --gallery /tmp/ck-structural-embodiment-gallery
```

The default session is available at
`http://localhost:8765/review/shared-pose-structural-embodiment-gallery` when
the existing visual-review service is running. The publisher revalidates the
complete 39-artifact/40-file candidate gallery, reproduces the frozen generated
sources, parses and checks the structural and posed evidence, and
deterministically re-renders each PNG from that evidence and the shared world
bound before copying only the four ordered PNGs required for appraisal. It
never replaces an existing session.

## Structural gallery evidence probe

`structural_gallery_evidence_probe.py` is disposable pre-proposal evidence. It
projects non-rendered structural evidence from an already-validated completed
gallery into immutable, hashable experiment records. It consumes a completed
gallery directory, not a review session, and delegates exact validation of the
complete source gallery to
`dev-tools/visual-review/publish_structural_embodiment.py`. Rendered gallery
PNGs, canvas data, and display metadata are deliberately outside the projection;
original `inspect-structure` bytes and per-vertex semantic labels are
unavailable. An expected invalid-gallery rejection returns no view, while
validator-load and unexpected runtime failures surface.

The probe is not a runtime package, bundle, durable schema, or adapter input
and makes no contact, deformation, physical-response, engine, or R3 claim. It
has no CLI; its import entrypoint is
`project_structural_gallery_evidence(gallery: Path)` (also exported as
`load_structural_gallery_evidence`). For a developer import/smoke check, run
the canonical experiment test command with the focused test filename:

```bash
experiments/current-form-surface-preview/test.sh \
  test_structural_gallery_evidence_probe.py
```

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

Tests:

```bash
experiments/current-form-surface-preview/test.sh
```

Pass one `test*` filename or `test*` discovery pattern to run a focused file
subset. During active implementation, pass a second `test*` method pattern to
filter that file further without triggering its mesh-heavy tests. Selectors
must begin with `test`; filename selectors must not contain `/`. The wrapper
resolves its own repository paths and always delegates
interpreter selection, pinned dependency validation, and native temporary-root
setup to `surface_preview_launcher.sh`; it never falls back to bare
`python3`. The launcher remains the entrypoint for publishers and other Python
commands, for example:

```bash
"$surface_preview_launcher" dev-tools/visual-review/publish_surface_preview.py --help
```

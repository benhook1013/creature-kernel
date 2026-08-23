# Local visual-review gallery

This is disposable developer/evidence tooling for comparing rendered image
options. It is deliberately a small Python 3.10+ standard-library program: it
does not install packages, fetch JavaScript, bind remotely, render images, or
make product/experiment decisions.

## Commands

Create an empty reviews root, then publish a rich manifest:

```bash
mkdir -p /tmp/creature-reviews
python3 dev-tools/visual-review/publish.py \
  --root /tmp/creature-reviews \
  --manifest /path/to/review-manifest.json
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-reviews --port 0
```

For read-only review from another device on the local network, opt in
explicitly to the wildcard listener:

```bash
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-reviews --port 0 --lan-read-only
```

`--lan-read-only` makes the review pages, static files, assets, and read APIs
readable to any device that can reach the selected port. Response `POST` writes
are disabled entirely in this mode, including requests with localhost-looking
Host/Origin headers or a valid token. To save a response, use the default
loopback-only mode. Replace the printed `0.0.0.0` with this host's LAN IP when
opening the gallery from another device. The Python server only binds the
listener; OS, WSL, container, and firewall forwarding are outside its scope
and may still be required for another device to connect. Do not enable this
mode on an untrusted network.

For a structural-only review, build the checked-in CLI and publish the
checked-in biped example through the bounded wrapper:

```bash
cargo build -p creature-kernel-cli
mkdir -p /tmp/creature-structure-reviews
python3 dev-tools/visual-review/publish_structure.py \
  --root /tmp/creature-structure-reviews \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --id stylized-biped-structure \
  --title "Stylized biped structural inspection"
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-structure-reviews --port 0
```

The wrapper runs the local `target/debug/creature-kernel` executable without a
shell, bounds its output and runtime, validates the inspection envelope, and
then uses the same immutable session publisher as image reviews. A valid
`invalid-source` inspection remains reviewable with its diagnostics. This is
a structural, source-preserving review: it renders no geometry and makes no
runtime or resolver-contract claim. Use `--creature-kernel PATH` when the CLI
is built elsewhere.

For prepared-source developer inspection, regenerate the same localhost
structure session with the additional bounded numeric preparation inventory:

```bash
cargo build -p creature-kernel-cli
mkdir -p /tmp/creature-prepared-source-reviews
python3 dev-tools/visual-review/publish_prepared_source.py \
  --root /tmp/creature-prepared-source-reviews \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --id stylized-biped-prepared-source \
  --title "Stylized biped prepared source"
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-prepared-source-reviews --port 0
```

`publish_prepared_source.py` invokes
`creature-kernel inspect-prepared-source --input PATH` without a shell, bounds
the child output and runtime, validates the
`creature-kernel.provisional-source-preparation-inspection.v1` envelope, and
publishes it as the existing immutable `structure` session kind. Its `graph`
is rendered by the existing structure viewer; `prepared` adds only basis,
counts, and numeric-value inspection data; and `preview`, when available,
directly consumes the restricted exact reference placements. The browser
renders a deliberately crude semantic point/line proof: Part markers,
containment links, Joint endpoint links, attachment-root distinction, semantic
labels, and deterministic SVG front (x/y), side (z/y), and top (x/z) views.
Joint frame transforms are not interpreted. This is spatial scaffolding only,
not geometry/mesh/surface/volume/anatomical quality, rigging, pose/animation,
IK, deformation, physics, general transforms, resolver activation, or runtime
evidence. It supplied the first genuine human-appraisable visual checkpoint;
Ben confirmed on 2026-08-15 that the diagrams were decodable and spatially
accurate for the intended straight tail. Generated sessions live under `/tmp`, are disposable, and are not
committed.

For the bounded filled-form appraisal candidate, build the CLI and publish the
four fixed profile variants from the same exact source placements:

```bash
cargo build -p creature-kernel-cli
mkdir -p /tmp/creature-provisional-form-reviews
python3 dev-tools/visual-review/publish_provisional_form.py \
  --root /tmp/creature-provisional-form-reviews \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  --creature-kernel target/debug/creature-kernel \
  --id stylized-biped-form \
  --title "Stylized biped filled-form appraisal"
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-provisional-form-reviews --port 0
```

`publish_provisional_form.py` invokes `creature-kernel
inspect-provisional-form --input PATH` shell-free, with a 10-second timeout,
256 KiB stdout bound, and 64 KiB stderr bound. It accepts only a complete,
diagnostic-free `creature-kernel.provisional-form-preview.v1`, `.v2`, `.v3`,
`.v4`, `.v5`, `.v6`, `.v7`, `.v8`, or `.v9` success envelope,
the exact four variant IDs/order, known Part addresses and provenance, bounded
integer points, supported ellipsoid/capsule/tapered-segment shapes, and the
positive reference scale. Failed CLI outcomes and malformed payloads are not
published. The resulting immutable `provisional-form` session contains the
validated payload only and no assets or external dependencies.

The CLI currently emits the provisional v9 contract. As in v2/v3, limb
capsules are owned by their current Part: `upper_arm` spans its reference point
to its direct `forearm` child, `forearm` to `hand`, `thigh` to `shin`, and
`shin` to `foot`. V4 introduced `neck` as a narrow axial capsule
from the neck reference to its direct `head` child, overlapping only the upper
torso and head rather than behaving like a torso-length spine. The tapered tail
remains parent-to-current Part. Historical v5 retains that geometry while
carrying only the source-authored dimension inventory and each descriptor's
original consumed dimension roles; its `upper_arm` capsule role is
`["form_radius"]`. Historical v6 retained the same display geometry while adding
source-authored shoulder landmarks and identity control frames. Its upper-arm
role inventory is `["form_radius", "form_shoulder_depth_radius"]`; only
`form_radius` supplies the capsule radius, while the depth control remains a
consumed authored control for later region-aware consumers. The server retains
strict read support for immutable v1-v5 sessions under their original
role/endpoint contracts. These are provisional display-volume rules, not a
generated skeleton, anatomical socket, or general junction contract.

Current v9 carries the source-owned `authored_torso_profile` and
`authored_head_neck_profile`. The torso profile contains seven ordered axial
sections, explicit pelvis/torso identity frames and landmarks,
lateral/anterior/posterior radius references, provenance, and variant-scaled
profile factors. The head/neck profile contains eight ordered sections and
seven connections, with head/neck identity frames and landmarks,
lateral/up/forward radius references, provenance, and variant-scaled profile
factors. It also carries a bilateral five-station `authored_arm_profile`
v1; the guide projects those exact arm stations and carries authored anisotropic
elbow compatibility masses. These profiles are producer-consumer bindings, not
new runtime or semantic contracts.

The read-only browser page renders each variant in front (x/y), side (z/y),
and top (x/z) filled SVG panels with shared bounds, physical display radii
derived from the reference scale, deterministic depth ordering, semantic role
colors, hover/focus labels, and an expanded inspection view with a persistent
part legend. Hovering or focusing a legend entry highlights the exact semantic
part in all three projections. It is overlapping display primitives with a straight
tail—not a continuous surface or mesh—and makes no claims of surface
continuity, anatomical correctness, mesh/topology, rigging, animation/IK,
deformation, physics, runtime behaviour, or Readiness 3. Keep generated
sessions under `/tmp`; do not commit them.

The server revalidates each stored `review.json` before serving it; the
browser's checks are a rendering guard, not the authoritative publication
contract.

By default the server binds only to `127.0.0.1` and prints one localhost URL
after the socket is bound; port `0` asks the operating system to choose an
available port. Stop it with Ctrl-C. Most publishers expect the reviews root
to already exist; `publish_surface_preview.py` creates its final root when its
parent exists. Each session ID is a one-time directory name: publishing
refuses to overwrite an existing session.

## Windows browser/CDP fallback

Use the T3 collaborative preview first for browser navigation, inspection,
interaction, screenshots, and recordings. If it is unavailable and a Windows
Chrome/CDP fallback is required, send a readable PowerShell script through the
stdin-only launcher:

```bash
dev-tools/visual-review/powershell-stdin.sh <<'POWERSHELL'
$ErrorActionPreference = 'Stop'
Invoke-RestMethod -Uri 'http://127.0.0.1:9222/json/version' |
  ConvertTo-Json -Depth 4
POWERSHELL
```

The launcher accepts no arguments and invokes `powershell.exe` with exactly
`-NoProfile -NonInteractive -File -`; stdin is forwarded unchanged. Do not use
`-EncodedCommand`, Base64, or another obfuscated payload. Opaque automation can
be blocked or misclassified and then surface as a misleading launch error.
Keeping the script readable preserves inspection and diagnosis.

## Rich manifest v1

The source manifest is authoritative and is not copied into a session. Its
shape is:

```json
{
  "schema_version": 1,
  "id": "surface-options-2026-08-09",
  "title": "Surface options",
  "description": "Optional description",
  "instructions": "Choose one option in each single-choice group.",
  "subject_context": {
    "authored_summary": {
      "text": "One left-ear node is present; no right-ear node is present.",
      "unknowns": ["Lighting is not yet final"]
    },
    "descriptor_snapshot": {"profile": "compact"},
    "provenance": {"build": "debug-42", "renderer": "preview"}
  },
  "groups": [
    {
      "id": "surface",
      "title": "Surface",
      "description": "Compare the rendered surface.",
      "selection_mode": "single",
      "items": [
        {
          "id": "warm",
          "title": "Warm surface",
          "source": "renders/warm-surface.png",
          "description": "Optional item description",
          "metadata": {"seed": 12, "renderer": "debug"}
        }
      ]
    }
  ]
}
```

`description`, `instructions`, item `description`, and `metadata` are
optional. IDs are unique safe slugs (`a-z`, `0-9`, `_`, `-`, beginning with a
lowercase letter or number); IDs are unique across the complete manifest.
`selection_mode` is `single`, `multiple`, or `none`. `source` is either an
absolute local path or a path relative to the source manifest; path traversal,
backslashes, symlinks, directories, and non-regular files are rejected. The
initial supported image types are PNG, JPEG (`.jpg`/`.jpeg`), WebP, and GIF.
SVG, HTML, and all other files are rejected.

`subject_context` is optional and, when present, must contain at least one of
these fields (unknown fields are rejected):

- `authored_summary`: an object with required non-empty `text` and optional
  `unknowns`, an array of non-empty strings. This is supplied interpretation;
  the gallery does not verify its truth.
- `descriptor_snapshot`: a JSON object containing a resolved/generated
  descriptor snapshot, copied or derived from structured source data. The
  gallery preserves and displays it but does not verify it.
- `provenance`: a JSON object describing build/render lineage. The gallery
  preserves and displays it but does not verify it.

The `What you're looking at` panel displays these fields before instructions,
including unknowns explicitly. Structured sections are rendered as compact
JSON. Context strings and manifest material are treated as text, never HTML.

The server and publisher require POSIX descriptor-relative filesystem
primitives (`O_NOFOLLOW`, directory descriptors, and directory-relative
atomic rename). They fail closed with a startup/operation error on platforms
without those primitives.

This is single-user localhost tooling, not a security boundary between local
processes running as the same operating-system user. Treat the reviews root,
manifest, and source images as private and stable while publishing or serving;
concurrent same-user replacement or mutation is outside the supported threat
model. The no-follow, path, origin, token, and file-type checks protect the
ordinary local workflow and accidental misuse. They do not make the gallery a
multi-user or adversary-resistant file service.

The publisher validates the full manifest before creating the session. It
copies each image to `SESSION/assets/<item-id>.<source-extension>` and writes
normalized `SESSION/review.json`; normalized items contain the relative
`image` field instead of `source`. A canonical JSON summary is printed on
success. A failed invocation cleans only its own staging/session files.

## Disposable baseline-versus-successor surface checkpoint

`publish_surface_preview.py` is a bounded adapter for the current experiment
surface consumers. It runs the current v9 provisional-form producer once, runs the
baseline and successor Python generators against that same producer output,
validates both bundles, and publishes four ordered baseline/successor image
pairs (eight guide/skin composite PNGs) through the ordinary image gallery.
This supplied the prior successor visual checkpoint and remains reusable
plumbing and baseline evidence for the [active runway](../../docs/project/status.md#active-runway),
not the current named checkpoint or a production/acceptance gate.

The current successor is v6 with region id
`successor-torso-shoulder-head-neck-arm-limb-extremity-tail-profile-sweeps-v10`.
It contains four authored arm-profile routes (left/right upper arm and
left/right forearm) plus two leg sweeps. The shared elbow seam is exact and
upper-arm-owned; all three authored lateral/up/forward radii are consumed.
There is no successor arm root bridge or old underarm support, and station
tuning does not vary per variant.

Run it from the isolated environment prepared by
`experiments/current-form-surface-preview/README.md`, or an equivalent
environment containing that experiment's pinned requirements.

```bash
cargo build -p creature-kernel-cli
mkdir -p /tmp/creature-surface-reviews
python3 dev-tools/visual-review/publish_surface_preview.py \
  --root /tmp/creature-surface-reviews \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  --creature-kernel target/debug/creature-kernel \
  --generator experiments/current-form-surface-preview/generate_surface_preview.py \
  --successor-generator experiments/current-form-surface-preview/generate_successor_surface_preview.py
```

For galleries that should survive WSL restarts, use a persistent Linux-side
root such as `/home/ben/.cache/creature-kernel/visual-reviews`. The publisher
creates that final directory when its parent exists. Serve it for LAN review
with the existing read-only command:

Transient generator work is allocated beside the selected review root so WSL
Windows TEMP/TMP does not redirect it to DrvFS; callers must still choose a
POSIX filesystem supporting the required operations.

```bash
python3 dev-tools/visual-review/serve.py \
  --root /home/ben/.cache/creature-kernel/visual-reviews \
  --port 8765 --lan-read-only
```

`--generator` selects the baseline consumer and `--successor-generator` selects
the separate successor consumer. Both default to the current experiment
scripts when omitted. A successful publication contains exactly four groups in
canonical variant order, each with baseline first and successor second, for
eight copied images. Every pair uses the same source provenance and shared
front, side, and three-quarter framing (`1800 × 570`, RGB), so the appraisal
can focus on the consumer boundary rather than capture differences.

The published `review.json` also retains the exact canonical current producer
envelope bytes
actually consumed by both generators in
`subject_context.descriptor_snapshot`. That payload is deterministically
XZ-compressed and Base64-encoded to stay within the bounded review-context
carrier, with its original UTF-8 encoding, byte count, and SHA-256 recorded
alongside it. `producer_envelope_sha256` binds the exact consumed producer
file; each published image's `source_sha256` carries that same digest.
The fields use the version-neutral `producer_envelope_*` prefix. Decoding the
field must reproduce the exact current-format bytes and therefore the complete
authored-dimension/landmark/frame/descriptor-role mapping. The original validated body
document remains identified by its UTF-8 encoding, byte count, and SHA-256
without duplicating its bytes. This is self-contained current-format lineage evidence, not
an image asset, a new body-document contract, or a claim that the disposable
consumers are production geometry.

For each pair, appraise whether the successor reads as a more coherent
stylized digitigrade biped overall: recognizable cranium/muzzle/neck,
shoulder/torso/pelvis structure, connected limbs and joints, digitigrade legs,
paws, and tail; less like blended primitives; and with the four variants still
meaningfully different. The gallery records the comparison only; it does not
record acceptance.

The baseline v2 generator bundle is fail-closed: its manifest must identify the
current v9 source, contain the four canonical v9 variants, and inventory exactly one PLY,
semantic sidecar, metrics JSON, regional-guide JSON, and guide/skin composite PNG
per variant. Every inventory path is relative, regular, non-symlinked, hash- and
size-checked. The regional-guide v8 sidecar is checked as a bounded finite
source-owned projection with the generator's exact skin-driving ordered torso
cage sections, pelvis/torso ownership, axes/orientation, and section
connections. Its older axial station and transition controls are accepted only
as explicitly marked compatibility diagnostics and are not rendered. The
producer v9 authored torso profile is checked as an exact seven-section
ordered index: every section binds its pelvis/torso owner identity frame,
axial landmark, lateral/anterior/posterior source dimensions and values,
provenance, and variant scaling factors. The guide repeats that source lineage
and the successor repeats it in its consumed profile-sweep controls. The
producer v9 authored head/neck profile is checked as an exact eight-section,
seven-connection ordered index. Each section binds its head/neck owner identity
frame, landmark, lateral/up/forward source dimensions and values, provenance,
and variant scaling factors; the guide and successor retain that exact source
lineage. The successor head/neck consumer uses source-authored head/neck
profile controls projected through the regional guide, retaining exact source
ownership/provenance and branched neck/cranium plus muzzle route lineage across
all four variants. Baseline
and successor pairing uses a canonical per-variant binding of source identity,
reference scale, variant/profile ids, producer-variant digest, descriptor owners,
capture framing, and torso lineage; it never pairs by list position alone.
The successor v6 sidecar and v10 region claims are checked against the guide and
metrics, including the current rounded-superellipse axial profile operation.
The retained producer envelope remains the exact consumed evidence, and every
successor PLY is parsed and checked for finite values, valid indices, one
connected component, and watertight topology. Any profile, provenance, identity,
lineage, metrics, framing, or inventory mismatch is rejected before a review
directory is created.
The sidecar also checks piecewise named limb sections and endpoint-owned
elbow/knee/hock stations, hand attachments and foot hock sources,
explicit shoulder/hip girdle masses, source-derived digitigrade foot chains
from hock through tapered metatarsal to planted paw-pad and toe-box, a
guide-only contact datum, positive dimensions,
allowed path primitives, expected source roles, and shared-bound containment;
its shoulder and arm sidecar binds the exact v9 identity frames, peak/axilla landmarks,
and variant-scaled depth controls to the producer. It distinguishes those
guide-derived controls and guide-only anterior/posterior support curves from
the baseline's two skin-driving deltoid sweeps; the successor arm routes
contain no root bridge or old underarm support. Its compiled recipe counts,
shared bounds, projections, canvas, and panel layout must match the manifest.
Stale support-field claims are rejected rather than silently accepted. Composite
PNG IHDR and inventory metadata are bound to the fixed 1800x570 RGB canvas. The
bundle's source/provenance and descriptor AddressKeys are bound to the parsed v9
producer result. The producer has a 10-second bound and the local extraction/
render subprocess has a finite 120-second bound. Unlisted files or directories,
malformed inventory or guide/provenance, partial variants, and generator or
producer timeouts prevent any review session from being created. The successor
v6 bundle is independently fail-closed: it must contain exactly four variants
with one PLY, metrics JSON, successor-consumer sidecar, and composite PNG per
variant. Its source identity, shared canvas/projections/layout/bounds, sidecar
identity, torso/shoulder/head-neck/limb/extremity/tail claims, temporary bridge,
metrics, inventory hashes, and regular-file set are checked against the
baseline boundary. Only the eight composite PNGs are copied to the gallery;
guide JSON, PLYs, sidecars, metrics, and temporary work directories remain
disposable.

This is a disposable current-source visual bridge. It does not activate Stage
1, Readiness 3, production geometry, runtime behaviour, or decision-record
evidence, and it has not yet been appraised or accepted. Keep generated bundles
and sessions under `/tmp`; they are not repository artifacts.

## HTTP routes and response format

Open `/` for a dynamic session index, then `/review/<id>` for a review. The
browser uses these same-origin routes:

- `GET /api/sessions` lists valid sessions and concise invalid-session errors.
- `GET /api/reviews/<id>` returns the normalized review and current response.
- `GET /api/reviews/<id>/assets/<asset>` serves only manifest-referenced images.
- `GET /api/reviews/<id>/response` reads the current response.
- `POST /api/reviews/<id>/response` atomically replaces only that session's
  `response.json`.

The POST body is JSON with `schema_version`, `review_id`, `selections`,
`group_notes`, and `overall_note`. Selections are arrays of item IDs keyed by
group ID; the server validates IDs and selection cardinality against the
manifest. The server adds `saved_at` as a UTC timestamp. Repeated saves are
intentional updates to the one current response. Requests are limited to 64
KiB and require the per-process token embedded in the same-origin review page,
plus localhost `Host` and `Origin` headers. No CORS, upload, delete, or
arbitrary-file/HTML endpoint is provided.

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
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --creature-kernel target/debug/creature-kernel \
  --id stylized-biped-form \
  --title "Stylized biped filled-form appraisal"
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-provisional-form-reviews --port 0
```

`publish_provisional_form.py` invokes `creature-kernel
inspect-provisional-form --input PATH` shell-free, with a 10-second timeout,
256 KiB stdout bound, and 64 KiB stderr bound. It accepts only a complete,
diagnostic-free `creature-kernel.provisional-form-preview.v1`, `.v2`, `.v3`, or
`.v4` success envelope,
the exact four variant IDs/order, known Part addresses and provenance, bounded
integer points, supported ellipsoid/capsule/tapered-segment shapes, and the
positive reference scale. Failed CLI outcomes and malformed payloads are not
published. The resulting immutable `provisional-form` session contains the
validated payload only and no assets or external dependencies.

The CLI currently emits the provisional v4 contract. As in v2/v3, limb
capsules are owned by their current Part: `upper_arm` spans its reference point
to its direct `forearm` child, `forearm` to `hand`, `thigh` to `shin`, and
`shin` to `foot`. V4 additionally represents `neck` as a narrow axial capsule
from the neck reference to its direct `head` child, overlapping only the upper
torso and head rather than behaving like a torso-length spine. The tapered tail
remains parent-to-current Part. The server retains strict read support for
immutable v1-v3 sessions under their original role/endpoint contracts. These
are provisional display-volume rules, not a generated skeleton, anatomical
socket, or general junction contract.

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

By default the server binds only to `127.0.0.1` and prints one localhost URL
after the socket is bound; port `0` asks the operating system to choose an
available port. Stop it with Ctrl-C. The reviews root must already exist, and
each session ID is a one-time directory name: publishing refuses to overwrite
an existing session.

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
  "id": "fur-options-2026-08-09",
  "title": "Fur options",
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
      "id": "coat",
      "title": "Coat",
      "description": "Compare the silhouette and surface.",
      "selection_mode": "single",
      "items": [
        {
          "id": "warm",
          "title": "Warm coat",
          "source": "renders/warm.png",
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

## Disposable surface-preview bridge

`publish_surface_preview.py` is a bounded adapter for the current experiment
surface generator. It runs the Rust v4 provisional-form producer, then runs an
experiment-local Python generator with explicit `--input` and `--output`
arguments, and publishes only the four guide/skin composite PNGs through the
ordinary image gallery:

Run it from the isolated environment prepared by
`experiments/current-form-surface-preview/README.md`, or an equivalent
environment containing that experiment's pinned requirements.

```bash
cargo build -p creature-kernel-cli
mkdir -p /tmp/creature-surface-reviews
python3 dev-tools/visual-review/publish_surface_preview.py \
  --root /tmp/creature-surface-reviews \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --creature-kernel target/debug/creature-kernel \
  --generator experiments/current-form-surface-preview/generate_surface_preview.py
```

The v2 generator bundle is fail-closed: its manifest must identify the v4 source,
contain the four canonical v4 variants in order, and inventory exactly one PLY,
semantic sidecar, metrics JSON, regional-guide JSON, and guide/skin composite PNG
per variant. Every inventory path is relative, regular, non-symlinked, hash- and
size-checked. The regional-guide v2 sidecar is checked as a bounded finite
source-owned projection with the generator's exact ordered axial station and
transition controls, explicit shoulder/hip girdle masses, positive dimensions,
allowed path primitives, expected source roles, and shared-bound containment;
its compiled recipe counts, shared bounds, projections, canvas, and panel layout
must match the manifest. Composite
PNG IHDR and inventory metadata are bound to the fixed 1800x570 RGB canvas. The
bundle's source/provenance and descriptor AddressKeys are bound to the parsed v4
producer result. The producer has a 10-second bound and the local extraction/
render subprocess has a finite 120-second bound. Unlisted files or directories,
malformed inventory or guide/provenance, partial variants, and generator or
producer timeouts prevent any review session from being created. Only the four
composite PNGs are copied to the gallery; guide JSON, PLYs, sidecars, metrics,
and temporary work directories remain disposable.

This is a disposable current-source visual bridge. It does not activate Stage
1, Readiness 3, production geometry, runtime behaviour, or decision-record
evidence. Keep generated bundles and sessions under `/tmp`; they are not
repository artifacts.

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

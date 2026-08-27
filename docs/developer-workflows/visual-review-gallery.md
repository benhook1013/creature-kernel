# Local visual-review gallery

Status: Implemented developer workflow; focused tests and local/browser smoke
verified

This workflow applies when an agent or developer needs browser-based,
side-by-side appraisal of generated images. The gallery is reusable local
developer/evidence presentation plumbing. It does not define Creature Kernel
product behaviour, architecture, visual-evidence semantics, or an experiment
protocol.

## Authority boundary

The gallery presents image options and records a person's selections and
notes. It is not Creature Kernel product UI, a renderer, a visual scoring or
adjudication system, formal experiment registration, or automatic acceptance.
The [visual-quality evaluation protocol](../research/visual-quality-evaluation.md)
owns visual-assessment and evidence meaning. The
[experiment workflow](../../experiments/README.md) owns registration and
artifact-retention requirements. Human selections and notes remain subjective
observations unless a later, provenance-complete evidence record explicitly
adopts them under the applicable protocol.

## Structural inspection review

The same local gallery can present the CLI's provisional, source-preserving
structural projection for the authored example. From the repository root:

```bash
cargo build -p creature-kernel-cli
mkdir -p /tmp/creature-reviews
python3 dev-tools/visual-review/publish_structure.py \
  --root /tmp/creature-reviews \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --creature-kernel target/debug/creature-kernel
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-reviews --port 0
```

Open the printed localhost URL and select the structural session. Its browser
view exposes collection counts, explicit Part containment, directed Joints,
module/Socket/Attachment composition, Regions and Capabilities, diagnostics,
and the closed raw JSON. This view is source inspection only. It does not
generate or prove geometry, a resolved snapshot, a rig, animation, physics, or
runtime behaviour; a successful status does not establish any of those claims.

Publishing creates a local immutable session under the review root. Keep the
root and session under `/tmp` (or another disposable local directory) and do
not commit generated sessions. The existing image-manifest publish and review
workflow remains supported; image sessions and structural sessions are separate
review kinds. The helper and browser details remain in the
[visual-review tool README](../../dev-tools/visual-review/README.md).

## Prepared-source inspection

The prepared-source developer instrumentation is invoked with
`inspect-prepared-source --input PATH`. It retains the structural projection
and adds the declared basis, prepared counts, and numeric debug rows for one
admitted source. For a browser session, run
`publish_prepared_source.py` followed by `serve.py` in a disposable local root;
the [visual-review tool README](../../dev-tools/visual-review/README.md) owns
the exact commands, bounds, and session behavior. This remains source
inspection only—not a creature visualization or retained-human checkpoint—and
does not activate resolver, snapshot, geometry, runtime, or Readiness 3
behavior.

## Filled-form appraisal candidate

The developer-only filled-form candidate is published with the bounded
`publish_provisional_form.py` adapter:

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

The adapter runs `inspect-provisional-form --input PATH` without a shell,
limits the child to 10 seconds, 256 KiB stdout, and 64 KiB stderr, and
publishes only a complete successful `provisional-form` payload. The browser
shows neutral, wider/softer, narrower/readable, and selected depth-forward
variants derived from the same exact placements. Every variant has shared
scale/bounds front x/y, side z/y, and top x/z panels containing overlapping
filled primitives and the straight tail.

This is a developer visual-appraisal candidate, not product geometry. It does
not claim surface continuity, anatomical correctness, mesh/topology,
rigging, animation/IK, deformation, physics, runtime behavior, or Readiness 3.
Generated sessions remain under `/tmp` and are not committed.

## Disposable continuous-surface preview bridge

The disposable bridge can place the current experiment generator's four
composite PNG panels in the same image gallery:

Run it from the isolated environment prepared by
`experiments/current-form-surface-preview/README.md`, or an equivalent
environment containing that experiment's pinned requirements.

```bash
surface_preview_launcher=experiments/current-form-surface-preview/surface_preview_launcher.sh
"$surface_preview_launcher" dev-tools/visual-review/publish_surface_preview.py \
  --root /tmp/creature-surface-reviews \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --creature-kernel target/debug/creature-kernel \
  --generator experiments/current-form-surface-preview/generate_surface_preview.py
```

The command first requires the Rust producer to emit the canonical v4
provisional-form envelope, then invokes the experiment-local generator in a
shell-free, time- and output-bounded subprocess. The generator must provide a
strict manifest with the four canonical v4 profiles, and for each profile a
PLY, semantic sidecar, metrics file, and exactly one neutral PNG composite
containing front, side, and three-quarter views. The bridge verifies safe
paths, regular non-symlinked files, hashes, byte counts, PNG dimensions and
view metadata before publishing. Only the four PNGs enter the immutable
gallery session; the other files remain temporary.

The producer is bounded to 10 seconds and the local extraction/render
subprocess to a finite 120 seconds, allowing four bounded 72^3 previews without
turning a failed experiment into an unbounded wait.

This is a current-source disposable visual bridge, not an activation of Stage
1, Readiness 3, production geometry, runtime behaviour, or DR evidence. The
gallery presents what the generator produced; it does not decide whether the
surface is good or accept an architecture. Keep generator work, bundles, and
sessions under `/tmp` and do not commit them.

## Workflow

1. Prepare a review manifest for the images to compare. Use stable option IDs,
   truthful titles and descriptions, and provenance metadata appropriate to the
   use: for example fixture/profile, source and build identity, seed and
   configuration, capture settings, and the criterion being appraised. Retain
   failure and inconclusive options when the applicable protocol requires them.
   Do not invent a numeric aesthetic score. An optional `subject_context` may
   carry an authored summary of the concrete resolved entity, a
   resolved/generated descriptor snapshot, and build/render provenance. The
   authored summary must describe that resolved entity rather than source-schema
   optionality or runtime randomness. The gallery preserves and displays this
   context but does not verify its truth. The manifest shape and supported
   image/path rules are defined in the
   [visual-review tool README](../../dev-tools/visual-review/README.md).
2. Publish the manifest into an existing disposable reviews root. For example:

   ```bash
   mkdir -p /tmp/creature-reviews
   python3 dev-tools/visual-review/publish.py \
     --root /tmp/creature-reviews \
     --manifest /path/to/review-manifest.json
   ```

   Publishing validates the complete manifest, creates a one-time session, and
   copies only the supported manifest-referenced images into that session.
3. Run the loopback server, normally asking the operating system for an
   available port:

   ```bash
   python3 dev-tools/visual-review/serve.py \
     --root /tmp/creature-reviews --port 0
   ```

   Open or share the printed `http://127.0.0.1:<port>/` (localhost) URL with
   the browser or local reviewer conducting the appraisal. Use the session's
   review page for the side-by-side comparison.
   For a read-only review from another device on the local network, explicitly
   use the LAN mode:

   ```bash
   python3 dev-tools/visual-review/serve.py \
     --root /tmp/creature-reviews --port 0 --lan-read-only
   ```

   This binds to `0.0.0.0` and makes review contents readable to devices that
   can reach the port. Response writes are disabled entirely in this mode,
   including requests with spoofed localhost `Host`/`Origin` headers or a valid
   token; use the default loopback mode when a response must be saved. Replace
   the printed `0.0.0.0` with this host's LAN IP for the second device. OS/WSL/
   container/firewall forwarding is outside the Python server and may still be
   required for a second device to connect. Use this only on a trusted local
   network.
4. After saving the review, read the session's `response.json` (or the
   response API described in the tool README) and preserve the selections,
   notes, and timestamp as observations. Interpret them under the applicable
   visual-assessment or experiment protocol; the gallery does not decide a
   result or accept a stage.
5. Stop the server with `Ctrl-C` when the review is complete. Keep the server
   and review root local to the task.

## Retention and evidence

Generated images, session copies, and response files are ephemeral outside Git
by default. Large captures remain prohibited from Git without an accepted
artifact-storage decision. If observations become durable evidence, record the
raw artifact location and retention policy, along with enough provenance to
reproduce or audit the appraisal, and follow the applicable experiment and
visual-assessment authority. A gallery session by itself does not register an
experiment or create visual evidence.

## Security and operation boundary

The server binds to loopback by default and is intended for one local process
and reviewer. The explicit `--lan-read-only` mode is for LAN GET/read access
only: it exposes review contents to devices able to reach the port while
disabling response writes entirely. Use the default loopback mode to save a
response. Do not use it on an untrusted network or as an authenticated
multi-user service. OS,
WSL, container, and firewall forwarding are outside the Python server and may
still be required. Use only images published by the manifest; do not add
external assets, CDNs, uploads, or arbitrary file endpoints. The review page
carries the per-process server token needed for response writes in the default
loopback mode, and the server validates the response path and request origin.
These controls support local appraisal; they do not turn the utility into an
authenticated or remotely deployable service. Secure filesystem operations require
POSIX/openat/no-follow support; unsupported platforms fail closed. Treat the
review root, manifest, and source images as private and stable for the
invocation. Correctness under concurrent replacement by another process
running as the same operating-system user is outside this local tool's threat
model.

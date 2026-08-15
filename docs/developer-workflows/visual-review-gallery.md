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

## Prepared-source review

The prepared-source candidate is invoked with
`inspect-prepared-source --input PATH`. It retains the structural projection
and adds the declared basis, prepared counts, and numeric debug rows for one
admitted source. For a browser session, run
`publish_prepared_source.py` followed by `serve.py` in a disposable local root;
the [visual-review tool README](../../dev-tools/visual-review/README.md) owns
the exact commands, bounds, and session behavior. This remains source
inspection only and does not activate resolver, snapshot, geometry, runtime,
or Readiness 3 behavior.

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

The server binds to loopback only and is intended for one local process and
reviewer. Do not expose it remotely or use it as an untrusted multi-user
service. Use only images published by the manifest; do not add external assets,
CDNs, uploads, or arbitrary file endpoints. The review page carries the
per-process server token needed for response writes, and the server validates
the response path and request origin. These controls support local appraisal;
they do not turn the utility into an authenticated or remotely deployable
service. Secure filesystem operations require POSIX/openat/no-follow support;
unsupported platforms fail closed. Treat the review root, manifest, and source
images as private and stable for the invocation. Correctness under concurrent
replacement by another process running as the same operating-system user is
outside this local tool's threat model.

# Authored examples

These examples are small, human-readable body documents for exercising the
admitted source shape and the provisional structural inspection command. They
are authored fixtures, not generated meshes or resolver snapshots.

## Stylized digitigrade biped

[`body-documents/stylized-digitigrade-biped.json`](body-documents/stylized-digitigrade-biped.json)
contains one bounded Stage-1-like creature: a pelvis-rooted torso, neck and
head chain; left and right arm chains ending in hands; left and right
digitigrade leg chains ending in feet; four semantic regions; and locomotion,
reach, and tail-motion capability subjects. A present tail module is attached
to the pelvis through host/mating Sockets and an Attachment. Its two Parts have
separate base and segment Joints.

The document demonstrates that these typed records can form one connected,
structurally inspectable source projection. On the current CLI it reports
`status: success` with 1 module, 18 Parts, 17 Joints, 2 Sockets, 1 Attachment,
4 Regions, and 3 Capabilities.

It does not prove geometry, numeric normalization, canonical frame semantics,
rigging, animation, runtime behaviour, or visual quality. The identity
transforms and simple placements are deliberately provisional. A document can
pass parser/schema admission and still fail the stronger structural inspection
checks (for example, with a disconnected Part or non-immediate Joint child).

Run it from the repository root:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

For the local browser structural review, use the built CLI and a disposable
`/tmp` review root:

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

The generated session is local and immutable and should not be committed. The
browser view is a provisional, source-preserving structural inspection—not
geometry, a resolved snapshot, rig, animation, physics, or runtime proof.
The existing image-review workflow remains available; see the [developer
workflow](../docs/developer-workflows/visual-review-gallery.md) for details.

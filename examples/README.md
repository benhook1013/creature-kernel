# Authored examples

These examples are small, human-readable body documents for exercising the
admitted source shape, the provisional structural inspection command, and the
prepared-source developer inspection. They are authored fixtures, not
generated meshes or resolver snapshots.

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
rotations and simple Part/Attachment placements are deliberately provisional.
A document can pass parser/schema admission and still fail the stronger
structural inspection checks (for example, with a disconnected Part or
non-immediate Joint child).

The current exact-placement foundation exercises this example in a deliberately
restricted domain: canonical metres, right-handed axes, identity rotations, and
exact integer translations for the Part placements plus Attachment host/mating
Socket frames and offsets it consumes. Part `placement.translation` values are
local to their declared containment parent. Unrelated Joint and named-frame
transforms are not validated or resolved by this operation. The example was
corrected from world-looking authored values to those parent-local deltas while
retaining the intended derived reference positions (for example, the head at
`[0, 3, 0]` and the tail tip at `[0, 0, -2]`). Its Attachment also agrees
exactly with the authored tail-root delta. This remains placement evidence
only; it is not general transform resolution, geometry, or a rendered creature.

Run it from the repository root:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

The unchanged `inspect-structure` command is structural-only. The prepared
source inspection adds the declared basis, prepared counts, and numeric debug
rows (stable semantic locations, display values, and binary64 bits) for this
single admitted source:

```bash
cargo run -p creature-kernel-cli -- inspect-prepared-source \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

This projection does not resolve or snapshot, canonicalize, apply basis/unit
values, interpret quaternions, expand dependencies/modules, or produce
geometry, rigging, animation, physics, or runtime output; it does not activate
Readiness 3.

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

To review the candidate primitive spatial preview in the browser, build the
CLI and run the existing `publish_prepared_source.py` followed by `serve.py`
against a disposable local root. The publisher invokes
`inspect-prepared-source --input PATH`; the browser then renders the exact
placement result as deterministic front (x/y), side (z/y), and top (x/z) SVG
scaffolding with semantic Part markers and links. Use the [visual-review tool
README](../dev-tools/visual-review/README.md) for the exact command flow and
interpretation. This is a crude point/line visual checkpoint, not geometry,
mesh, rigging, animation, physics, or runtime evidence; generated sessions are
disposable and must not be committed.

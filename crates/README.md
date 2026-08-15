# Crates

This directory contains the members of the Cargo workspace. See each crate's
manifest for package metadata. Readiness 2 remains active for the admitted
body-document parser/bootstrap and its schema, manifest, and fixtures. The
workspace also contains provisional structural address/index and validation
code plus the `inspect-structure` command in the
[`creature-kernel-cli`](creature-kernel-cli/) binary. This preparatory slice is
source-preserving inspection, not a finalized resolved snapshot or Readiness 3
activation; geometry and runtime implementation remain absent. The standalone
`creature_kernel_core::numeric` module validates strict JSON-number syntax,
performs pinned Rust 1.97.1 direct correctly-rounded binary64 final conversion,
and remains preparatory with typed overflow/nonzero-underflow failures, finite
subnormal support, lexical-zero `+0`, and focused boundary tests. It is not
wired into body-document admission, does not alter the admitted Readiness 2
identity, and does not activate Readiness 3. The standalone
`creature_kernel_core::frame` module is likewise preparatory: it provides a
normalized-binary64 structural transform carrier, exact signed-axis
source-basis mapping, and symbolic length-unit ratios, without unit scaling,
quaternion/transform algebra or comparison, source integration, resolver, or
snapshot behavior. The public
`creature_kernel_core::source_preparation::prepare_single_source` API accepts
raw source bytes plus a sealed `ResourceProfile`; it performs whole-document
admission, structural validation, basis preparation, and numeric preparation.
Its complete semantic numeric maps cover part/joint/socket/attachment
transforms, landmark positions, dimensions, and named frames, keyed by stable
semantic addresses or owner/role keys. The graph retains admitted source
records and source context as semantic provenance, but raw lexical
spelling/provenance is not recovered. The internal `frame_preparation` adapter
cannot bypass record-level admission. This preparation does not apply
basis/unit values or quaternion semantics, expand dependencies/modules,
produce claims/snapshots or serialization, or activate a resolver or Readiness
3. Normative source meaning
remains owned by [`spec/body-document`](../spec/body-document/README.md),
with the admitted schema at
[`ck-body-document-v1.schema.json`](../spec/body-document/schema/ck-body-document-v1.schema.json).

The core also has a deliberately restricted exact reference-placement
foundation over one prepared source. It requires canonical metres and a
right-handed basis (`+Y` up, `+Z` forward), identity rotations, and bounded
translations that remain exact integers in the binary64 carrier for the Part
placements plus Attachment host/mating Socket frames and offsets it consumes.
It composes parent-local Part deltas through explicit containment and checks
authored attached-root placement against the exact Attachment equation.
Unrelated Joint and named-frame transforms are not validated or resolved by
this operation. The CLI's prepared-source inspection directly consumes these
placements for a candidate deterministic spatial preview; the existing
browser session draws only crude semantic point/line scaffolding (Part
markers, containment and Joint endpoint links, attachment-root distinction,
and front/side/top SVG views). This is not general basis/unit/quaternion
transform math, geometry/mesh/surface/volume/anatomical quality, rigging,
pose/animation, IK, deformation, physics, resolver activation, or runtime
evidence.

The CLI also exposes the separate provisional developer-instrumentation
`inspect-prepared-source --input <path>` inspection. Unlike unchanged
`inspect-structure`, it adds the declared basis, prepared counts, and numeric
debug rows with stable semantic addresses or owner/role locations, display
values, and binary64 bits for one admitted source. It remains only a graph
projection: no resolver/snapshot, canonical serialization, basis/unit
application, quaternion semantics, dependency/module expansion, geometry,
rigging, animation, physics, runtime, or Readiness 3 activation. The local
browser flow uses `publish_prepared_source.py` followed by `serve.py`; see the
[visual-review tool README](../dev-tools/visual-review/README.md).

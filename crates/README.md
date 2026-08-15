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

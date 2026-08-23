# Creature Kernel

Creature Kernel is an engine-independent procedural creature compiler and
future embodiment runtime research prototype. It explores how one
authoritative semantic body definition can support generation, inspection, and
later runtime representations without making arbitrary creature or character
support a present-day claim.

## Current demonstrated boundary

The current demonstrated boundary is a bounded stylized digitigrade
anthropomorphic/animal-like biped with a torso/pelvis, head and simplified
muzzle, paired arms with simplified hands or paws, paired digitigrade legs
with simplified feet or paws, and optional named ear and tail modules. The
checked-in body document can be admitted and inspected structurally, prepared
into a source-preserving numeric/debug projection, and used to produce four
fixed display-only provisional filled-form variants.

These are preparatory developer-facing capabilities in an exploratory
prototype. They do not establish arbitrary morphology or model support, a
production compiler contract, production geometry, or a runtime avatar.

The longer-term generic direction is to derive geometry, rigging, collision,
materials, deformation data, and runtime adapters from shared semantic
lineage. Those are future capabilities, not capabilities of the current
prototype.

## Explicit non-capabilities today

- No arbitrary creature, character, anatomy, quadruped, wing, extra-limb, or
  detailed-digit support.
- No production mesh or surface-generation backend, final topology, or
  authored-mesh conformance path.
- No usable skeleton, skin weights, animation, IK, collision, contact,
  deformation, physics, or real-time runtime implementation.
- No standalone renderer, editor, game engine, service, or embedded AI
  assistant.

## Architecture direction

```text
semantic body document
        -> admission, preparation, and validation
        -> resolved semantic body graph
        -> specialized geometry, rig, collision, and appearance representations
        -> embodiment runtime and host-engine adapters
```

The semantic source is intended to remain authoritative; generated mesh
topology and runtime artifacts are derived representations. The graph,
geometry, rigging, collision, and runtime stages are proposed or gated beyond
the current provisional CLI and inspection slices.

## Quick start

The repository uses the Rust toolchain declared in
[`rust-toolchain.toml`](rust-toolchain.toml). From the repository root:

```bash
cargo test --workspace --all-targets
```

Inspect the checked-in examples with the three current provisional CLI
entrypoints:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped.json

cargo run -p creature-kernel-cli -- inspect-prepared-source \
  --input examples/body-documents/stylized-digitigrade-biped.json

cargo run -p creature-kernel-cli -- inspect-provisional-form \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json
```

`inspect-structure` emits a source-preserving structural debug projection;
`inspect-prepared-source` exposes bounded preparation data; and
`inspect-provisional-form` emits four fixed display-only filled-form variants.
The provisional-form entrypoint uses the checked-in authored-form input because
it consumes the current source-authored form controls.
All three accept `--input -` for stdin and emit structured JSON. They are
provisional inspection operations, not a general compile or runtime API.

For pinned-toolchain checks, prepared-source inspection, and local browser
workflows, see [`DEVELOPER_SETUP.md`](DEVELOPER_SETUP.md).

## Repository map

- [`crates/creature-kernel-core/`](crates/creature-kernel-core/) — semantic,
  admission, and preparation foundations.
- [`crates/creature-kernel-cli/`](crates/creature-kernel-cli/) — the thin
  provisional CLI adapter.
- [`examples/body-documents/`](examples/body-documents/) — checked-in semantic
  body inputs, including the current biped example.
- [`spec/`](spec/) — proposed normative document, graph, numeric, and related
  contract areas.
- [`docs/product/`](docs/product/), [`docs/architecture/`](docs/architecture/),
  [`docs/research/`](docs/research/), and [`docs/project/`](docs/project/) —
  intended outcomes, boundaries, evidence questions, and status.
- [`experiments/`](experiments/) — disposable, reproducible exploratory work.
- [`dev-tools/visual-review/`](dev-tools/visual-review/) — local inspection
  and gallery tooling for provisional artifacts.

## Licensing and contributions

Project-authored tracked repository material is available under either the MIT
License or Apache License, Version 2.0, at your option. See
[`LICENSE-MIT`](LICENSE-MIT) and [`LICENSE-APACHE`](LICENSE-APACHE). Contributions
are accepted under the same dual terms; no CLA is required.

The project license applies to project-authored repository material and does
not by itself impose a license on independently generated outputs. Input
rights, third-party material, and outputs incorporating separately licensed
repository assets remain subject to their own rights and terms.

## Further reading

- [Documentation map](docs/README.md)
- [Vision and scope](docs/product/vision-and-scope.md)
- [Requirements](docs/product/requirements.md)
- [Architecture](docs/architecture/README.md)
- [Body-document specification](spec/body-document/README.md)
- [Numeric and frame profile](spec/numeric-frame-profile/README.md)
- [Research questions](docs/research/open-questions.md)
- [Current project status](docs/project/status.md)

Most product, architecture, and specification material remains Proposed or
gated. The [decision registry](docs/decisions/registry.md) records rationale
and review state; [the founding record](docs/FOUNDATION.md) is historical
context rather than current authority.

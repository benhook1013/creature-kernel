# Creature Kernel

Creature Kernel is an exploratory platform for generating programmable
creatures from semantic body definitions instead of starting with a
hand-authored mesh. It is aimed at making varied, physically meaningful
characters easier to construct, inspect, and eventually use in real-time
experiences.

The initial focus is stylized furry characters. The longer-term idea is that a
single body definition can provide the shared lineage for geometry, rigging,
collision, materials, deformation, and runtime capabilities—while specialized
representations remain free to do their own jobs.

## Where the project is now

This is an exploratory executable prototype, not a finished game or engine.
The Rust workspace contains the emerging semantic/compiler core and a thin
CLI. Disposable Python experiments and a local browser gallery currently make
the generated structures and surface hypotheses visible. The project does not
yet provide production-ready animation, IK, physics, soft-body deformation,
arbitrary creature support, or a game runtime.

The current work is testing an important boundary: can the same semantic body
and generated private guides drive different surface-generation approaches?
The old ellipsoid/capsule preview remains as a comparison baseline while a
successor surface experiment explores more coherent continuous forms. Neither
preview is a permanent geometry backend.

See [current project status](docs/project/status.md) for the active runway and
the exact checkpoint currently being pursued.

## The intended direction

```text
semantic body document
        -> deterministic preparation and validation
        -> private guides and derived representations
        -> geometry, rigging, collision, appearance, and runtime adapters
        -> an engine or real-time interactive experience
```

The source of truth is intended to be the semantic body, not generated mesh
topology. Humans, scripts, and external AI agents should eventually be able to
use the same deterministic CLI/API operations to create, inspect, validate,
and revise bodies. The core does not require an embedded AI assistant.

This is deliberately staged. The first proof is a bounded stylized
digitigrade furry-biped family generated through shared operations. Broader
morphologies, authored-mesh conformance, richer appearance, usable rigs,
contact, deformation, and runtime interaction are later capabilities—not
claims made by the current prototype.

## What exists now

- A Rust/Cargo workspace for the semantic and compiler foundation.
- A strict, proposed body-document and body-graph direction with a checked-in
  stylized digitigrade biped example.
- Provisional source admission, structural inspection, numeric preparation, and
  placement scaffolding.
- A thin CLI for inspecting the authored structural and prepared-source views.
- Four fixed body-profile variants used to test shared generation operations.
- Disposable Python surface-preview experiments and deterministic visual
  artifacts for comparing baseline and successor hypotheses.
- A small local visual-review gallery for inspecting JSON, diagrams, and image
  comparisons in a browser.

These pieces are evidence and working foundations. They are not yet a
production compiler contract, final mesh pipeline, or runtime avatar system.

## Quick start

The repository uses the Rust toolchain declared in
[`rust-toolchain.toml`](rust-toolchain.toml). With Rust installed, run the
workspace tests from the repository root:

```bash
cargo test --workspace --all-targets
```

Inspect the checked-in semantic example:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

For the full setup, pinned-toolchain checks, prepared-source inspection, and
local browser sessions, see [`DEVELOPER_SETUP.md`](DEVELOPER_SETUP.md).

## Find your way around

- [Documentation map and reading order](docs/README.md) — where each kind of
  project information belongs.
- [Vision and scope](docs/product/vision-and-scope.md) — intended outcomes,
  boundaries, and staged success shape.
- [Requirements](docs/product/requirements.md) — proposed product
  requirements and first-proof limits.
- [Architecture](docs/architecture/README.md) — target boundaries and
  responsibilities.
- [Body-document specification](spec/body-document/README.md) — the proposed
  source-document direction.
- [Body-graph specification](spec/body-graph/README.md) — the proposed
  semantic graph direction.
- [Decision registry](docs/decisions/registry.md) — rationale for consequential
  choices; these records do not replace canonical contracts.
- [Research questions](docs/research/open-questions.md) — unresolved
  hypotheses and investigations.
- [Experiments](experiments/README.md) — reproducible exploratory evidence.
- [Visual-review tooling](dev-tools/visual-review/README.md) — disposable
  local browser/gallery workflows.
- [Current status](docs/project/status.md) — active work, checkpoint, and
  implementation state.

## Project boundaries

Creature Kernel is intended to be an engine-independent compiler and
embodiment runtime, not a replacement for a general-purpose game engine. A
real-time game is the first downstream proof and integration target.

The initial reference path is native programmatic generation without requiring
a handcrafted base mesh. Later support for externally supplied meshes must not
be ruled out by the semantic contracts. The first proof intentionally excludes
arbitrary anatomy, quadrupeds, extra limbs, detailed digits, full-resolution
soft-body simulation, dynamic topology every frame, and a built-in language
model.

## Contributing and validation

Read the [documentation authority map](docs/README.md) and
[`AGENTS.md`](AGENTS.md) before making consequential changes. Keep generated
meshes, captures, caches, and other disposable artifacts outside the repository
unless an explicit storage decision exists.

For documentation changes, run:

```bash
python3 dev-tools/validation/validate_docs.py
git diff --check
```

The project is still deciding which technical approaches deserve promotion
from experiments into durable contracts. Treat proposed documents and visual
previews as clearly labelled working material, and use
[`docs/project/status.md`](docs/project/status.md) to distinguish current
implementation from future direction.

## Historical context

[`docs/FOUNDATION.md`](docs/FOUNDATION.md) preserves the founding conversation.
It is useful context, but current product, specification, architecture, and
status documents are the authoritative sources for present work.

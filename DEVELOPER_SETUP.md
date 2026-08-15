# Developer setup

Creature Kernel's first reproducible Rust reference target is
`x86_64-unknown-linux-gnu`, using the WSL2 reference environment with the
repository under `/home`. The ordinary development profile is the default
Cargo development profile and is used for local checks.

The repository pins the ordinary Rust toolchain in `rust-toolchain.toml` to
Rust `1.97.1`. The reference toolchain reports:

```text
rustc 1.97.1 (8bab26f4f 2026-07-14)
binary: rustc
commit-hash: 8bab26f4f68e0e26f0bb7960be334d5b520ea452
commit-date: 2026-07-14
host: x86_64-unknown-linux-gnu
release: 1.97.1
LLVM version: 22.1.6
```

Install `rustup` using the official instructions at <https://rustup.rs/>, then
install the repository-pinned toolchain and components from the repository
root:

```bash
rustup toolchain install
rustup show active-toolchain
```

Run the bounded local checks from the repository root:

```bash
python3 dev-tools/readiness-evidence/evidence.py --fetch-locked .
python3 dev-tools/fixture-preflight/preflight.py \
  . fixtures/body-documents/readiness-2/manifest.v1.json
python3 dev-tools/readiness-evidence/evidence.py .
python3 dev-tools/readiness-evidence/evidence.py --run-bound-checks .
cargo fmt --all --check
cargo test --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
```

The provisional structural inspection command accepts one admitted body
document and emits a source-preserving structural projection:

```bash
cargo run -p creature-kernel-cli -- inspect-structure --input <path>
```

For the checked-in authored example, run:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

The current example is expected to return `status: success` at the
`structural-validation` stage. It reports 1 module, 18 Parts, 17 Joints, 2
Sockets, 1 Attachment, 4 Regions, and 3 Capabilities. Parser/schema admission
is only the first gate: an admitted fixture can still fail stronger structural
inspection with `invalid-source` diagnostics.

`inspect-structure` remains the structural-only command. To inspect the
prepared-source developer instrumentation for one admitted source, run:

```bash
cargo run -p creature-kernel-cli -- inspect-prepared-source \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

This retains the structural graph projection and adds the declared basis,
prepared counts, and numeric debug rows. Rows include stable semantic
addresses or owner/role locations, a display value, and binary64 bits. The
projection is not a resolver or snapshot and does not perform canonical
serialization, basis/unit application, quaternion semantics, dependency or
module expansion, geometry, rigging, animation, physics, or runtime work; it
does not activate Readiness 3.

To publish that inspection as a local structural-review session, build the CLI,
create a disposable `/tmp` review root, then publish and serve it:

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

Open the printed localhost URL. The browser view exposes collection counts,
explicit Part containment, directed Joints, module/Socket/Attachment
composition, Regions and Capabilities, diagnostics, and the raw JSON. This is
provisional source-preserving structural inspection only: it proves none of
geometry, a resolved snapshot, rigging, animation, physics, or runtime
behaviour. Generated sessions are local and immutable; do not commit them.
The existing image-review workflow remains supported. Detailed workflow and
tool behaviour live in the [visual-review workflow](docs/developer-workflows/visual-review-gallery.md)
and [tool README](dev-tools/visual-review/README.md).

To publish the prepared-source projection instead, use the same local server
flow with `publish_prepared_source.py` followed by `serve.py`, using a
disposable `/tmp` review root. The authoritative launch commands, bounds, and
session behavior are in the [tool README](dev-tools/visual-review/README.md).

```bash
mkdir -p /tmp/creature-prepared-source-reviews
python3 dev-tools/visual-review/publish_prepared_source.py \
  --root /tmp/creature-prepared-source-reviews \
  --input examples/body-documents/stylized-digitigrade-biped.json \
  --creature-kernel target/debug/creature-kernel
python3 dev-tools/visual-review/serve.py \
  --root /tmp/creature-prepared-source-reviews --port 0
```

Open the printed localhost URL and stop the server with Ctrl-C. Sessions under
`/tmp` are disposable and must not be committed.

The evidence runner rejects legacy/current Cargo config files in the checkout,
its Cargo lookup ancestors, and the selected Cargo home. It removes ambient
Cargo/Rust/compiler/profile flags and wrappers, sets the pinned toolchain, and
runs exactly these locked/offline commands for `x86_64-unknown-linux-gnu`:

```text
cargo test -p creature-kernel-core --all-targets --target x86_64-unknown-linux-gnu --locked --offline
cargo clippy -p creature-kernel-core --all-targets --target x86_64-unknown-linux-gnu --locked --offline -- -D warnings
```

The generator's Cargo metadata uses the same sanitized environment and target
filter, and fails closed unless the workspace exposes exactly the explicit core
library and CLI binary targets. The active Readiness 2 record remains the
immutable exact identity at its recorded merge commit. Running the evidence
generator on a later evolving worktree recomputes a new implementation hash
when a bound entrypoint such as `lib.rs` changes; a mismatch does not rewrite
the historical admission and cannot serve as Readiness 2 or Readiness 3
activation evidence. The current structural preparation is outside the
admitted Readiness 2 implementation identity and requires a future successor
transaction before any Readiness 3 activation claim.

This is checkout-independent evidence with an offline lockfile and normalized
paths, not full machine/container reproducibility. Cargo's registry cache,
host kernel, CPU/toolchain installation, filesystem, and native tool behavior
remain external evidence and are not vendored or claimed identical.

These checks provide shell evidence only. They are not performance evidence
or portability evidence.

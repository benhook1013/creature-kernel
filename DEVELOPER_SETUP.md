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
```

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
library and CLI binary targets. The focused preflight and evidence generator
inspect only the Proposed Readiness 2 candidate; neither admits the manifest
nor activates Readiness 2.

This is checkout-independent evidence with an offline lockfile and normalized
paths, not full machine/container reproducibility. Cargo's registry cache,
host kernel, CPU/toolchain installation, filesystem, and native tool behavior
remain external evidence and are not vendored or claimed identical.

These checks provide shell evidence only. They are not performance evidence
or portability evidence.

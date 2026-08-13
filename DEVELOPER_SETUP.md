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

Run the reproducible local checks from the repository root:

```bash
cargo fetch --locked
python3 dev-tools/fixture-preflight/preflight.py \
  . fixtures/body-documents/readiness-2/manifest.v1.json
python3 dev-tools/readiness-evidence/evidence.py .
cargo fmt --all --check
cargo test --workspace --all-targets --locked --offline
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
```

Fetch dependencies before using the local `--offline` reference checks; those
checks intentionally fail rather than consulting the network. The focused
preflight and evidence generator inspect only the Proposed Readiness 2
candidate; neither admits the manifest nor activates Readiness 2. CI fetches
dependencies with `--locked` before generating evidence and running Rust
checks.

These checks provide shell evidence only. They are not performance evidence
or portability evidence.

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
cargo fmt --all --check
cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
```

These checks provide shell evidence only. They are not performance evidence
or portability evidence.

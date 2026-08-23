# Contributing

Before making a change, read [`AGENTS.md`](AGENTS.md) and the documentation
authority map in [`docs/README.md`](docs/README.md), then follow the relevant
product, specification, architecture, and project-status documents.

For basic validation, run:

```bash
python3 dev-tools/validation/validate_docs.py
git diff --check
cargo test --workspace --all-targets
```

Contributions intentionally submitted for inclusion in Creature Kernel are
accepted under the same MIT OR Apache-2.0 dual terms. No contributor license
agreement (CLA) is required. This concerns contributions submitted to this
project; it does not claim ownership or licensing control over contributors'
unrelated work.

# Repository structure

Status: Provisional conceptual layout

This document describes the intended information architecture. It is not an
exact manifest. `docs/project/repository-evolution.md` controls when planned
areas become active.

```text
creature-kernel/
├── .github/workflows/       # repository validation when active
├── docs/
│   ├── product/             # outcomes, requirements, users
│   ├── architecture/        # target boundaries and invariants
│   ├── decisions/           # consequential rationale across authority scopes
│   ├── research/            # open questions and references
│   ├── developer-workflows/ # conditional contributor procedures
│   └── project/             # status, roadmap, repository evolution
├── spec/                    # normative formats and semantics (proposed body-document/body-graph contracts)
│   ├── body-document/       # authored source encoding and admission contract
│   └── body-graph/          # resolved semantic graph contract
├── Cargo.toml               # planned Rust workspace; not active
├── crates/                   # planned engine-independent core/compiler/CLI areas
├── experiments/             # reproducible research evidence
├── fixtures/                # small stable proof inputs
├── benchmarks/              # reproducible performance scenarios
├── dev-tools/validation/    # repository and contract validation
├── AGENTS.md                # always-on contributor authority
└── README.md                # project orientation
```

Implementation directories and the Cargo workspace are intentionally absent
until the language/build decision and its activation trigger are accepted.

## Activation rule

Create a new area when it owns a current contract, workflow, template, fixture,
or executable responsibility. Keep prospective areas in the repository-evolution
ledger instead of creating empty placeholders.

## Large artifacts

Generated meshes, simulation caches, videos, dense captures, and datasets must
not enter normal Git history until storage, licensing, retention, and
reproducibility rules are accepted. Small fixtures necessary for tests may be
committed with documented provenance.

## Future implementation shape

The CK-KICK-013 Proposed platform direction is a Cargo workspace with a stable
Rust engine-independent semantic/compiler core, thin CLI, replaceable geometry
boundary, and later adapters. It does not include an initial daemon/service.
The exact crate layout, geometry backend, isolated C++ worker boundary, and
adapter strategy remain evidence-driven and unresolved. These planned paths do
not activate packages; the language/build acceptance trigger must be met first.

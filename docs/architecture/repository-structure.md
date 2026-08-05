# Repository structure

Status: Active conceptual layout

This document describes the intended information architecture. It is not an
exact manifest. `docs/project/repository-evolution.md` controls when planned
areas become active.

```text
creature-kernel/
├── .github/workflows/       # repository validation when active
├── docs/
│   ├── product/             # outcomes, requirements, users
│   ├── architecture/        # target boundaries and ADRs
│   ├── research/            # open questions and references
│   └── project/             # status, roadmap, repository evolution
├── spec/                    # normative formats and semantics
├── experiments/             # reproducible research evidence
├── fixtures/                # small stable proof inputs
├── benchmarks/              # reproducible performance scenarios
├── dev-tools/validation/    # repository and contract validation
├── AGENTS.md                # always-on contributor authority
└── README.md                # project orientation
```

Implementation directories are intentionally absent until language, package,
and component decisions are accepted.

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

A monorepo with an engine-independent core, compiler, runtime, CLI, validation,
and adapters is the current expectation. The language, build system, exact
package layout, and adapter strategy remain unresolved and require ADRs.

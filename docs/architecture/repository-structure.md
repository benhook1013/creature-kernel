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
├── spec/                    # normative formats and semantics (Proposed contracts)
│   ├── body-document/       # authored source encoding and admission contract
│   ├── body-graph/          # resolved semantic graph contract
│   ├── fixture-manifest/    # conceptual fixture admission authority
│   ├── build-operation/      # Proposed public build/output contract
│   ├── semantic-address/     # proposed typed machine address profile
│   ├── canonical-data/       # proposed canonical bytes and digest domains
│   ├── numeric-frame-profile/# proposed numeric/frame comparison profile
│   └── diagnostics/          # proposed diagnostic registry/profile
├── Cargo.toml               # planned Rust workspace; not active
├── crates/                   # planned engine-independent core/compiler/CLI areas
├── experiments/             # reproducible research evidence
├── fixtures/                # small stable proof inputs (admitted later)
├── benchmarks/              # reproducible performance scenarios
├── dev-tools/validation/    # repository and contract validation
├── AGENTS.md                # always-on contributor authority
└── README.md                # project orientation
```

The fixture-manifest family is an active Proposed authority, but it remains
conceptual: no manifest schema, parser, or fixture corpus is created here. Its
manifest payload is admitted by a separate readiness/decision record that
binds reviewed content identities; there is no custom active-pointer ledger.
Implementation directories and the Cargo workspace are intentionally absent
until DR-0013 is accepted. The four readiness stages are: acceptance activates
only the empty Cargo workspace/compiler/library/CLI shell; a versioned,
preflighted fixture manifest, its listed files, exact JSON Schema, and
parser/bootstrap activate together in one review-branch transaction; canonical
numeric/frame rules plus frozen expected graph outputs activate semantic
resolver/in-memory snapshot handoff; and a working resolver plus provisional
geometry profile and project-owned seam activate exploratory Stage 1 geometry.
While the relevant DRs remain Proposed, no implementation packages, schema,
manifest payload, or compiler-consumed fixtures are activated. Readiness 2
requires one Ben-approved immutable manifest/fixture/schema/parser transaction;
unlisted fixtures never activate independently.

The Batch 11 focused profiles and Batch 12 numeric evidence direction remain
Proposed specification areas. Their activation order is numeric/frame
semantics, semantic addresses, canonical bytes/digests, diagnostics, exact
schema/manifest, Readiness 2, then the separate Readiness 3
snapshot/comparison transaction. The planned numeric experiment is
unregistered and has no results or evidence; it must preregister domains,
semantic budgets, independent oracles, frozen corpora, conditioning, and
compiler-mode controls before execution. These directories may own current
contracts, but documentation alone activates no implementation package or
fixture corpus.

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
Rust engine-independent semantic/compiler core, thin CLI, project-owned
versioned backend-neutral GeometryRequest/GeometryResult seam, and later
adapters. It does not include an initial daemon/service. The exact crate
layout, geometry backend, isolated C++ worker boundary, artifact serialization,
and adapter strategy remain evidence-driven and unresolved. These planned paths
do not activate packages; DR-0013 acceptance activates only the empty shell,
while exact schema and admitted fixtures/contracts gate Stage 1 parser/resolver
implementation.

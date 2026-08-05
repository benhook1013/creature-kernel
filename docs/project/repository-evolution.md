# Repository evolution ledger

Status: Active

This ledger records which structural capabilities exist now and which activate
only after concrete triggers. It prevents empty scaffolding from being mistaken
for approved design.

States: `active`, `planned`, `triggered`, `deferred`, `not-applicable`, `retired`.

| Capability | Horizon | State | Activation trigger | Destination | Validation |
| --- | --- | --- | --- | --- | --- |
| Documentation authority | Now | active | Foundation phase | `docs/README.md` | Required-path and link checks |
| Product baseline | Now | active | Foundation phase | `docs/product/` | Required-path and link checks |
| Architecture baseline | Now | active | Foundation phase | `docs/architecture/` | Required-path and link checks |
| ADR registry and reviews | Now | active | Before first technical choice | `docs/architecture/decisions/` | ADR metadata and registry checks |
| Research question registry | Now | active | Before first experiment | `docs/research/` | Stable-ID checks later |
| Experiment workflow | Now | active | Before first prototype | `experiments/` | Template and evidence checks later |
| Specification authority | Now | active | Before first format proposal | `spec/` | Index and link checks |
| Fixture policy | Now | active | Before first executable test | `fixtures/` | Provenance rules |
| Benchmark policy | Now | active | Before first performance claim | `benchmarks/` | Hardware and command requirements |
| Documentation CI | Now | active | Governance scaffold | `.github/workflows/documentation.yml` | GitHub Actions |
| Body-document schema | Next | planned | First body parser proposal | `spec/body-document/` | Schema fixtures |
| Semantic body-graph spec | Next | planned | First resolver proposal | `spec/body-graph/` | Graph fixtures |
| Implementation packages | Next | planned | Language/build ADR accepted | Toolchain-specific | Unit and integration tests |
| Generation fixtures | Next | planned | First compiler prototype | `fixtures/body-documents/` | Deterministic output checks |
| Geometry experiments | Next | planned | Surface ADR enters review | `experiments/` | Experiment-specific metrics |
| Runtime benchmarks | Next | planned | First executable runtime | `benchmarks/runtime/` | Reference hardware profiles |
| Developer setup | Next | planned | Toolchain selected | `DEVELOPER_SETUP.md` | Fresh-environment check |
| Contribution guide | Next | planned | External collaborator or public repo | `CONTRIBUTING.md` | Contributor dry run |
| License | Next | planned | Before external contribution/distribution | Root license file | Legal review as appropriate |
| Host-engine adapter docs | Next | planned | First adapter ADR accepted | Architecture and implementation area | Adapter smoke tests |
| Implementation/proof tracker | Next | planned | First meaningful code/design gap | `docs/project/implementation-tracking/` | Anchor checks |
| External mesh conformance | Later | deferred | Native generation and semantics proved | Future component | Import fixtures |
| Operations and recovery | Later | deferred | Persistent service or distributed build exists | `docs/operations/` | Runbook exercises |
| User guides | Later | deferred | User-facing workflow stabilizes | `docs/user-guides/` | Workflow tests |
| Release and compatibility automation | Later | deferred | First distributable version | `.github/` and release tooling | Release proof |
| Advanced governance provenance | Later | deferred | Simple registry cannot answer ownership/review | Future validation | Demonstrated need |

## Change rule

Changing a state or trigger updates this ledger. Activating a consequential new
contract area may require an ADR. Removing or retiring an area must preserve any
historical decisions or evidence it owns.

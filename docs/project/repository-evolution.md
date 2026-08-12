# Repository evolution ledger

Status: Operational under Accepted DR-0001 Revision 5

This ledger records which structural capabilities exist now and which activate
only after concrete triggers. It prevents empty scaffolding from being mistaken
for approved design. Its active entries mean the structure exists or is used
under the accepted DR-0001 Revision 5 governance process; they do not accept
any product, specification, or architecture proposal.

States: `active`, `planned`, `triggered`, `deferred`, `not-applicable`, `retired`.

CK-KICK-012 and CK-KICK-013 remain active Proposed work after discussion-
approved F1–F7 and Batch 8/9/10/11/12/13 resolutions. DR-0002 Revision 11 and
DR-0008 Revision 11 remain Proposed with Owner approval Pending and Review
Complete. DR-0006 Revision 9, DR-0011 Revision 12, DR-0012 Revision 11, and
DR-0013 Revision 9 remain Proposed with Owner approval Pending and Review
Pending after the material Batch 13 change; prior review evidence is stale for
the revised records. Ben approved the Batch 13 resolution directions as
Proposed material. No implementation or readiness gate activates.
See
the [current review state](status.md#current-review-and-future-activation-obligations)
for review lenses, recommendations, and findings. Earlier review evidence is
stale after these revisions. CK-KICK-014 remains provisional/queued and does not activate
implementation packages or compiler fixtures.

The focused diagnostic owner remains Proposed with nine initial domains and a
tiny mandatory bootstrap registry/profile; exact codes and fields are fixture-
gated. This ledger records no activation from that direction.

| Capability | Horizon | State | Activation trigger | Destination | Validation |
| --- | --- | --- | --- | --- | --- |
| Documentation authority | Now | active | Foundation phase | `docs/README.md` | Required-path and link checks |
| Product proposal area | Now | active | Foundation phase | `docs/product/` | Required-path and link checks |
| Architecture proposal area | Now | active | Foundation phase | `docs/architecture/` | Required-path and link checks |
| Decision record registry and reviews | Now | active | Before first consequential choice | `docs/decisions/` | DR metadata, Scope, and registry checks |
| Research question registry | Now | active | Before first experiment | `docs/research/` | Stable-ID checks later |
| Visual-quality evaluation protocol | Now | active | Round 5 visual-quality work | `docs/research/visual-quality-evaluation.md` | Protocol and evidence-link checks |
| Experiment workflow | Now | active | Before first prototype | `experiments/` | Template and evidence checks later |
| Specification authority | Now | active | Before first format proposal | `spec/` | Index and link checks |
| Fixture policy | Now | active | Before first executable test | `fixtures/` | Provenance rules |
| Benchmark policy | Now | active | Before first performance claim | `benchmarks/` | Hardware and command requirements |
| Documentation CI | Now | active | Governance scaffold | `.github/workflows/documentation.yml` | GitHub Actions |
| AI delegation and review | Now | active | Before first delegated design review | `docs/developer-workflows/` | Required-path and link checks |
| Local visual-review gallery | Now | active | First need for human appraisal of generated CK-KICK-010 output | `dev-tools/visual-review/` | Focused tests + local HTTP/browser smoke |
| Body-document specification | Next | active | First body parser proposal exists in the CK-KICK-012 Batch 4 Proposed contract | `spec/body-document/` | Schema-level contract fixtures when activated |
| Semantic body-graph spec | Next | active | First resolver proposal exists in the CK-KICK-012 Batch 4 Proposed contract | `spec/body-graph/` | Graph and cross-DR contract fixtures when activated |
| Fixture-manifest specification | Next | active | Batch 10 creates the canonical Proposed fixture-manifest/admission owner; implementation remains gated by Readiness 2 | `spec/fixture-manifest/` | Immutable reviewed-tree/payload binding, preflight, append-only successor, and admission-link checks |
| Build-operation specification | Next | active | Proposed public build/output contract exists as the canonical owner; implementation remains gated by DR-0013 readiness | `spec/build-operation/` | Contract, link, and ownership checks |
| Implementation packages | Next | planned | Stage 1: DR-0013 accepted, activating only the empty Cargo shell; Stage 2: exact JSON Schema plus a versioned/admitted manifest, all referenced fixture files, and parser/bootstrap activate together in one review-branch transaction after Ben admission; Batch 12/13's numeric/frame evidence, claim identity, and the semantic-address, canonical-data, and diagnostic profiles precede exact schema/manifest admission; Readiness 2 admits parser/bootstrap and its corpus; the distinct Readiness 3 transaction then activates the resolver/snapshot boundary; Stage 4: working resolver plus provisional geometry profile and project-owned seam activate exploratory Stage 1 geometry | Planned Cargo workspace (`Cargo.toml`, `crates/`) | Stage-specific shell, parser/bootstrap, resolver/snapshot, and exploratory-proof evidence |
| Readiness 3 resolver/snapshot transaction | Next | planned | A distinct Ben-approved successor transaction contains the successor manifest, expected snapshots, comparison profile/rule, resolver implementation or exact implementation binding, and unchanged content-identity preflight; only that explicit ledger activation triggers the Readiness 3 resolver/snapshot boundary; no gate activates while the records remain Proposed | `docs/decisions/DR-0013-first-production-implementation-platform-and-geometry-boundary.md` and admitted fixture manifest | Successor content binding, approval, comparison metadata, resolver binding, and in-memory snapshot handoff |
| Generation fixtures | Next | planned | Stage 2 only: a separate Ben-approved readiness/decision record names the reviewed source commit reference, manifest path/digest, SHA-256 payload digest, exact ordered path/mode/content set containing only the manifest and declared schema, fixtures, and snapshots, and the versioned external path-set framing/profile (exact identifier remains readiness-gated); readiness/approval/successor records, mutable pointers, self-reference, and Git commit identity are excluded; rerun on the merged target compares those content identities even when the merge commit changes; append-only successors and unlisted fixtures do not activate independently | `fixtures/body-documents/` | Immutable binding, manifest/listed-source agreement, and deterministic output checks |
| Geometry exploration | Next | planned | Stage 4 only: working resolver plus provisional geometry profile and project-owned GeometryRequest/GeometryResult seam; CK-KICK-014 is exploratory and does not require accepting/reactivating parked DR-0009/0010 | `experiments/` under an activated proof | Bounded exploratory evidence; generated bundles remain ephemeral/unretained and do not select production geometry |
| Confirmatory multi-branch surface comparison | Later | deferred | At least two runnable candidate surface implementations and an intended comparative outcome for production architecture, or Ben explicitly reactivates DR-0009/0010 | `experiments/` under an activated protocol | Activated-protocol evidence and review |
| Runtime benchmarks | Next | planned | First executable runtime | `benchmarks/runtime/` | Reference hardware profiles |
| Developer setup | Next | planned | Toolchain selected | `DEVELOPER_SETUP.md` | Fresh-environment check |
| Contribution guide | Next | planned | External collaborator or public repo | `CONTRIBUTING.md` | Contributor dry run |
| License | Next | planned | Before external contribution/distribution | Root license file | Legal review as appropriate |
| Host-engine adapter docs | Next | planned | First adapter DR accepted; post-Readiness-3 transaction defines signed permutation/positive scale, storage/output-only or runtime-conformance tier, and precision/subnormal probes | Architecture and implementation area | Adapter smoke tests and FTZ/DAZ capability evidence |
| Implementation/proof tracker | Next | planned | First meaningful code/design gap | `docs/project/implementation-tracking/` | Anchor checks |
| External mesh conformance | Later | deferred | Native generation and semantics proved | Future component | Import fixtures |
| Operations and recovery | Later | deferred | Persistent service or distributed build exists | `docs/operations/` | Runbook exercises |
| User guides | Later | deferred | User-facing workflow stabilizes | `docs/user-guides/` | Workflow tests |
| Release and compatibility automation | Later | deferred | First distributable version | `.github/` and release tooling | Release proof |
| Advanced governance provenance | Later | deferred | Simple registry cannot answer ownership/review | Future validation | Demonstrated need |

## Change rule

Changing a state or trigger updates this ledger. Activating a consequential new
contract area may require a DR. Existing top-level policy READMEs do not
activate planned subdirectories or documents; planned destinations remain
uncreated until their activation trigger and state are met. Removing or
retiring an area must preserve any historical decisions or evidence it owns.

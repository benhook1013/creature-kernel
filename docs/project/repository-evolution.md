# Repository evolution ledger

Status: Operational under Accepted DR-0001 Revision 5

This ledger records which structural capabilities exist now and which activate
only after concrete triggers. It prevents empty scaffolding from being mistaken
for approved design. Its active entries mean the structure exists or is used
under the accepted DR-0001 Revision 5 governance process; they do not accept
any product, specification, or architecture proposal.

States: `active`, `planned`, `triggered`, `deferred`, `not-applicable`, `retired`.

CK-KICK-012 remains active work after discussion-approved F1–F7 and
Batch 8/9/10/11/12/13 resolutions. CK-KICK-013 Readiness 1 is active after
Ben accepted DR-0013 Revision 12 on 2026-08-13; later platform and
implementation gates remain separately bounded. Accepted DR-0001
Revision 5 remains the operative governance baseline while DR-0001 Revision 6
is Proposed transition guidance with Ben's workflow direction approved and
current review complete; formal acceptance remains pending Ben's disposition.
DR-0002 Revision 11, DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012
Revision 14 are Accepted with Owner approval Approved by Ben on 2026-08-17.
DR-0008 Revision 11 remains Proposed with Owner approval Pending and Review
Complete. DR-0013 Revision 12 is Accepted with Owner approval Approved by Ben.
All four semantic-foundation records have Review status Complete. DR-0002
Revision 11's current review targeted exact commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`; the current Double reviews for
DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14 targeted
exact commit `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The reviews of the earlier
predecessor revisions at commit
`763cff22d10f6491a05a28312a25250704543dcf` are stale exact-target evidence;
G1/G2 were fixed mechanically, T1–T3 were resolved
in the successors, and T4 remains unselected and deferred, requiring Ben's
retained-human disposition before adapter profile/schema activation; it does not
block the empty first Rust slice. The immediate-predecessor review at exact
commit `9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in the current revisions. The 9c governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. The review artifacts remain preserved evidence.
Readiness 1 is triggered/active for the empty Cargo workspace, compiler/core-
library shell, and thin CLI shell. The exact schema, manifest, nine fixtures,
Rust parser/bootstrap, and Python preflight are active as the Readiness 2
transaction after merged commit `766992ab089687e9b1496574e8ffa721388d96f3`
(PR #6) and the successful post-merge identity recomputation recorded in the
[admission record](readiness-2-admission.md). This is a bounded activation and
does not activate Readiness 3 or any still-Proposed DR.
See
the [current review state](status.md#current-review-and-future-activation-obligations)
for review lenses, recommendations, and findings. Earlier review evidence is
stale after these revisions. CK-KICK-014 remains provisional/queued and does not activate
implementation packages or compiler fixtures.

The focused diagnostic owner remains Proposed with nine initial domains and a
tiny mandatory bootstrap registry/profile. The candidate `ck.diagnostic.r2`
codes are documented and used by the admitted parser/preflight transaction;
this ledger does not accept the diagnostic owner or activate Readiness 3.

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
| Fixture-manifest specification | Next | active | Batch 10 creates the canonical Proposed fixture-manifest/admission owner; the exact Readiness 2 manifest and listed corpus are admitted by the recorded post-merge recomputation | `spec/fixture-manifest/` | Immutable reviewed-tree/payload binding, preflight, append-only successor, and admission-link checks |
| Build-operation specification | Next | active | Proposed public build/output contract exists as the canonical owner; implementation remains gated by DR-0013 readiness | `spec/build-operation/` | Contract, link, and ownership checks |
| Implementation packages | Now | active | Readiness 1 is active after DR-0013 Revision 12 acceptance for the Cargo workspace, compiler/core library shell, and thin CLI shell. Readiness 2 is active after PR #6 merge commit `766992ab089687e9b1496574e8ffa721388d96f3` and successful fresh-archive identity recomputation for the exact schema, versioned manifest, nine fixtures, parser/bootstrap, and preflight. The distinct Readiness 3 transaction then activates the resolver/snapshot boundary; geometry remains gated by a working resolver plus provisional profile and seam | Cargo workspace (`Cargo.toml`, `crates/`) plus [`schema`](../../spec/body-document/schema/ck-body-document-v1.schema.json), [`manifest`](../../fixtures/body-documents/readiness-2/manifest.v1.json), [`preflight`](../../dev-tools/fixture-preflight/preflight.py), and admitted parser/bootstrap | Readiness 1 shell evidence; Readiness 2 preflight, content identities, and sanitized bound checks; later resolver/snapshot and exploratory-proof evidence |
| Readiness 3 resolver/snapshot transaction | Next | planned | A distinct Ben-approved successor transaction contains the successor manifest, expected snapshots, comparison profile/rule, resolver implementation or exact implementation binding, and unchanged content-identity preflight; only that explicit ledger activation triggers the Readiness 3 resolver/snapshot boundary; acceptance of the four semantic-foundation records alone does not activate the gate | `docs/decisions/DR-0013-first-production-implementation-platform-and-geometry-boundary.md` and admitted fixture manifest | Successor content binding, approval, comparison metadata, resolver binding, and in-memory snapshot handoff |
| Generation fixtures | Next | planned | Stage 2 only: a separate Ben-approved readiness/decision record names the reviewed source commit reference, manifest path/digest, SHA-256 payload digest, exact ordered path/mode/content set containing only the manifest and declared schema, fixtures, and snapshots, and the versioned external path-set framing/profile (exact identifier remains readiness-gated); readiness/approval/successor records, mutable pointers, self-reference, and Git commit identity are excluded; rerun on the merged target compares those content identities even when the merge commit changes; append-only successors and unlisted fixtures do not activate independently | `fixtures/body-documents/` | Immutable binding, manifest/listed-source agreement, and deterministic output checks |
| Geometry exploration | Next | planned | Stage 4 only: working resolver plus provisional geometry profile and project-owned GeometryRequest/GeometryResult seam; CK-KICK-014 is exploratory and does not require accepting/reactivating parked DR-0009/0010 | `experiments/` under an activated proof | Bounded exploratory evidence; generated bundles remain ephemeral/unretained and do not select production geometry |
| Confirmatory multi-branch surface comparison | Later | deferred | At least two runnable candidate surface implementations and an intended comparative outcome for production architecture, or Ben explicitly reactivates DR-0009/0010 | `experiments/` under an activated protocol | Activated-protocol evidence and review |
| Runtime benchmarks | Next | planned | First executable runtime | `benchmarks/runtime/` | Reference hardware profiles |
| Developer setup | Now | active | DR-0013 Readiness 1 / first production toolchain selected | `DEVELOPER_SETUP.md` | Fresh-environment check |
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

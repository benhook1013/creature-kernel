# Project status

Status date: 2026-08-12

## Phase

Exploratory executable prototype and semantic-contract integration. The
foundation governance and the product, specification, and architecture
proposals remain provisional; current work is integrating the CK-KICK-012 Batch
8/9/10 and CK-KICK-013 readiness/publication revisions while keeping implementation gated rather than
returning to confirmatory surface research.

## Current activation state

The Stage 1 confirmatory surface protocol is parked and non-blocking:

- [DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  remains `Proposed`, Owner approval `Pending`, Review `Complete`. Its two
  current Double-review artifacts recommend `Revise` at High confidence. All
  five findings and review artifacts are preserved; no Revision 9 or further
  finding discussion is active.
- [DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  remains `Proposed`, Owner approval `Pending`, Review `Pending`. Exactly two
  geometry/semantic findings remain preserved. No acceptance is implied.
- The [first surface experiment design](../research/first-surface-experiment-design.md)
  is also deferred, with no active prerequisite. `EXP-0001` is not
  registered and no confirmatory evidence exists.

Reactivate this material only when at least two runnable candidate surface
implementations exist and the project intends to use a comparative outcome to
justify or select production architecture, or when Ben explicitly reactivates
it. Exploratory prototypes may proceed before then, but their observations
cannot claim formal DR-0009/0010 support or reject. This section is the
canonical owner of the current activation state; the detailed DRs and reviews
remain unchanged.

Ben approved the following deferred planning direction on 2026-08-09 for any
future activation. It is recorded here without accepting or revising either DR:

- A repair after evidence starts would create a new immutable comparison epoch,
  admitted prospectively and independently, with a full primary rerun.
- Registration would define enforceable `C` accounting and extend the
  confirmatory record/template.
- The mandatory visual floor would use at least three
  implementation/tuning-independent deterministic panel adjudicators.
- Outcome-changing failure attribution would use a preregistered diagnostic
  tree and independent verification.
- Bundle-outcome closure and component-attribution completion would remain
  separate, with explicit causes for `U`.

## Current outcome

The foundation scaffold and governance process are integrated. DR-0001 Revision
5 is Accepted by Ben after its Complete clean review; that acceptance applies
only to the Governance DR. DR-0002 through DR-0013 remain Proposed with their
review and owner-disposition history preserved. Ben's CK-KICK-012 Batch 5,
Batch 6, F1–F7, Batch 8, Batch 9, and Batch 10 resolutions are discussion-approved and integrated
as Proposed canonical product/specification/architecture/project material. Earlier
review evidence is stale after the current revisions. The current six-record
set is DR-0002 Revision 11, DR-0006 Revision 6, DR-0008 Revision 11, DR-0011
Revision 8, DR-0012 Revision 7, and DR-0013 Revision 5. DR-0002 and DR-0008
remain Proposed with Owner approval Pending and Review Complete; the four
Batch 10-revised records remain Proposed with Owner approval Pending and Review
Pending. The completed Batch 9 Double
review targeted commit `6cf17270fda2827756c24a8d0fb301bef358f98f`.
The Batch 9 review evidence is stale for the four revised records and is not
acceptance. No implementation or readiness gate activates. The current mixed
review state and next discussion are recorded below.

CK-KICK-013 is active with its discussion-approved Rust-first platform
proposal integrated as Proposed material, not accepted or implemented.
Proposed DR-0013 Revision 5 has Owner approval Pending and Review Pending after
Batch 10. The
completed Batch 9 Double review targeted commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`; its evidence is stale for the revised
record and is not acceptance. No implementation or readiness gate activates.
Readiness is four staged gates: accepted DR-0013 activates only the empty Cargo
shell; a versioned, preflighted fixture manifest, its listed files, exact JSON
Schema, and parser/bootstrap activate together in one review-branch transaction;
canonical numeric/frame rules plus frozen expected graph outputs activate
semantic resolver/in-memory snapshot handoff; and a working
resolver plus provisional geometry profile and project-owned seam activates
exploratory Stage 1 geometry. The proposal includes a stable
Rust semantic/compiler core, thin CLI, versioned project-owned
backend-neutral GeometryRequest/GeometryResult seam, one authoritative build
envelope across geometry and publication, immutable build-scoped sibling
staging, manifest-last atomic no-replace publication, identity/path/hash/size
validation, and rejection of symlinked, unlisted, incomplete, mixed-build, or
stale bundles. The [Proposed build-operation contract](../../spec/build-operation/README.md)
owns candidate-to-committed artifact identity, deterministic output-root
targeting, idempotent publication, post-collision identity/lineage/hash
inspection, target conflict, and lineage-checked inspection. `output-failure`
covers trusted derived-output/publication
failure; every invocation has a unique attempt identity, while deterministic
build-request identity exists once the complete outcome-affecting request is
established; artifact identity exists only after successful publication, and
artifact inspection is a separate read operation. Future workers require protocol/version
negotiation, bounded resources/time, crash/timeout/resource mapping, output
validation, and compiler survival. Python remains for disposable experiments,
evidence/render tooling, and visual workbench tasks, not as a production
compiler dependency. Build requests include all outcome-affecting source/
dependency, compiler/toolchain, contract/schema/profile, configuration/seed,
backend-capability/protocol, and target-platform inputs; attempt identity is
unique for tracing only. Candidate identity derives from deterministic request,
artifact role, and identity-rule revision. Canonical serialization/hash is
required before activation. The initial filesystem profile is tested local WSL
`/home` only, excluding `/mnt/c`, network, removable, and unspecified
filesystems; process-crash-safe namespace publication is required without a
sudden-power-loss claim. Producer/output trust is distinct from
coordinator/reporter/publisher trust, and worker trust loss cannot be
rehabilitated by validation. The [fixture-manifest specification](../../spec/fixture-manifest/README.md)
owns immutable reviewed-tree/payload binding, append-only admissions, and the
Readiness 2/3 conceptual corpus. The first reference path is WSL2 x86_64 GNU;
native-Linux portability smoke follows later. Exact
rust-toolchain.toml, Cargo.lock, target/profile/rustc -Vv/reference metadata,
and lightweight license/unsafe/native/portability/security dependency review
are required without Git pinning or audit bureaucracy. Final serialization,
compatibility, and geometry backend remain deferred.

No accepted production surface architecture, geometry backend, numeric budget,
exact fixture, schema, runtime field, topology, or package compatibility is
selected. CK-KICK-010's approved grid, field, bundle, determinism, and
structural-gate values are debug-only spike inputs and do not change that
boundary.

## Current review and future activation obligations

The prior Double-review findings and ten artifacts are preserved in the
[decision registry](../decisions/registry.md) as stale historical evidence.
The completed Batch 9 Double review examined the exact target commit
`6cf17270fda2827756c24a8d0fb301bef358f` in two Sol medium passes: Review 01
used the contract/schema/determinism/security lens; Review 02 used the
platform/failure/reversibility/publication lens.

Recommendations (Review 01 / Review 02) are: DR-0002 — Accept High / Accept
Medium; DR-0006 — Revise High / Revise High; DR-0008 — Accept High / Accept High;
DR-0011 — Accept High / Accept High; DR-0012 — Accept High / Accept Medium; and
DR-0013 — Revise High / Revise High. These are review recommendations only, not
Ben acceptance. Review Complete is evidence, not a clean review or acceptance.

The consolidated Batch 9 findings are now discussion-resolved by Batch 10 and
remain preserved as stale historical review history:

- C1 — High — stable request/attempt/candidate/committed identity, retry, and
  concurrent publication (DR-0006/0013).
- C2 — High — filesystem profile, crash durability, and TOCTOU/tamper-safe
  inspection (DR-0013).
- C3 — High — worker-output versus coordinator/reporter/publisher trust
  (DR-0013).
- C4 — High — immutable external binding and supersession/rollback for
  Readiness 2 admission (DR-0013).
- C5 — Medium — closed artifact-inspection non-success status algebra
  (DR-0013).

Batch 10 integrated the approved resolutions as Proposed canonical material:
separate request/attempt/candidate identities and deterministic retry/collision
rules; the initial WSL `/home` filesystem profile and process-crash-safe
namespace publication boundary; separate inspection statuses and shared
completeness/diagnostic conventions; producer/output versus
coordinator/reporter/publisher trust; immutable fixture-manifest reviewed-tree
and activation-payload binding with append-only successor/deactivation rules;
and the conceptual body-document shape, typed collections, basis/frame/profile,
and omission/default rules. These changes make DR-0006 Revision 6, DR-0011
Revision 8, DR-0012 Revision 7, and DR-0013 Revision 5 current and Review
Pending. DR-0002 Revision 11 and DR-0008 Revision 11 are unchanged and remain
Review Complete. No current-revision adversarial review has been supplied by
this documentation pass; owner approval remains Pending.

The immediate next action is current-revision review and owner disposition for
the four revised records; do not silently accept them. No implementation/
readiness gate activates while the records remain Proposed. Earlier Batch 8/9
and other review artifacts remain preserved as stale historical evidence.
Do not activate packages, schemas, fixtures, parser/resolver, or geometry work
while disposition remains pending.

Two nonblocking obligations apply to later activation: before an isolated
worker activates, define containment, process-tree, output/log/handle/network/
protocol/cleanup/status bounds appropriate to its threat model; before making
evidence-bearing portability or performance claims, freeze the lightweight
exact build/reference environment and dependency source/feature inputs, with
native smoke preceding native portability claims.

On 2026-08-09 Ben settled CK-KICK-012 Batch 1 in discussion. On 2026-08-11
he approved seven Batch 1 resolutions: one unique owner per source namespace
with authored deterministic collision-free remapping for collisions; one
operation-result envelope for every phase and diagnostic, with an optional
validated snapshot only for valid-supported success; required functional
articulation roles; frozen fixture outcomes and primary diagnostics; typed
vocabulary; explicit measurement ownership and conflict diagnostics; and
declared source frames normalized to a revisioned canonical basis with
provenance. He also discussion-approved the Batch 4 encoding, resolution,
compatibility, resource, and fixture resolutions, the six Batch 5 blocker
resolutions, and the Batch 6 status/primary, descendant Socket, and
Attachment-cardinality resolutions, and the Batch 8/9 completeness, module,
transform, readiness, and build/publication resolutions. These discussion approvals do not accept
or silently replace the DRs. The canonical documents now state explicit Part
containment, descendant Socket Attachment placement, canonical resolved frame
records, the closed operation/bootstrap/status/resource contract, the
in-memory snapshot handoff, the build-operation owner, and the resolved
diagnostic/cardinality rules. Earlier review evidence is stale after these
revisions. The Batch 8/9/10 resolutions are discussion-approved Proposed changes,
not acceptance or a clean review.
The cross-cutting proposal is [DR-0012: initial
body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The [Proposed body-document contract](../../spec/body-document/README.md),
[Proposed body-graph contract](../../spec/body-graph/README.md),
[Proposed fixture-manifest contract](../../spec/fixture-manifest/README.md),
and [Proposed build-operation contract](../../spec/build-operation/README.md)
are now active canonical specification areas. No implementation package, machine schema,
numeric limit, exact fixture, canonical basis, or geometry backend is selected;
the Rust/Cargo platform remains a Proposed CK-KICK-013 direction only.
The meaning and enforcement details of an exact dependency revision remain a
nonblocking obligation before external authored dependencies activate.

## Current round and work state

- Rounds 0–5 are integrated history: governance, product boundary, semantic
  source/identity/operation proposals, compile/runtime boundary, first-proof
  charter, morphology envelope, and provisional visual criteria.
- CK-KICK-008 surface research is integrated as parked confirmatory guidance;
  it is not a blocker and does not require another review round now.
- CK-KICK-009 is complete for the disposable exploratory geometry host:
  Python with NumPy, scikit-image marching cubes, and trimesh, all retained as
  replaceable discovery adapters rather than production selections.
- CK-KICK-010 is implemented with bounded local evidence recorded in
  [`experiments/ck-kick-010-walking-skeleton/RESULTS.md`](../../experiments/ck-kick-010-walking-skeleton/RESULTS.md);
  its selected Single independent implementation review is complete with five
  substantive findings and a trailing-whitespace finding dispositioned in that
  record, not clean. Its provisional inputs and observations do not create a
  schema, DR, Stage 1 result, or production contract, and the evidence record
  does not register `EXP-0001`.
- The reusable local visual-review gallery is implemented at
  [`dev-tools/visual-review/`](../../dev-tools/visual-review/); current
  verification is complete for the implementation. `py_compile`, all 14
  focused unit/integration tests, `git diff --check`, local HTTP smoke for the
  session API and PNG serving, and Ben's real Chromium localhost browser smoke
  passed. One fresh Luna xhigh independent implementation review found three
  filesystem race defects (source replacement during publish, incomplete
  failure cleanup, and parent-directory redirection for assets/responses). A
  follow-up hardening attempt was rejected as disproportionate after growing
  the local utility by roughly 1,100 implementation/test lines while still not
  closing same-user replacement races. Those races are now explicitly outside
  the stable, private, single-user localhost threat model; the existing
  no-follow, path, origin, token, file-type, staging, and atomic-response checks
  remain. T3 product-native browser automation was unavailable; Ben
  subsequently confirmed the revised `subject_context` panel was working in
  his real Chromium browser.
  This remains presentation plumbing only and does not alter the CK-KICK-010
  conclusion or claim visual evidence or Stage 1.
- CK-KICK-011 follows useful exploratory evidence. A formal comparative
  surface decision is optional and risk-driven, not automatic.
- CK-KICK-012 is active with Batches 1, 4, 5, 6, F1–F3, Batch 8, Batch 9, and
  Batch 10 integrated as Proposed documentation; its parser/resolver and
  fixture-admission proposals activate the four specification families, while implementation packages and compiler-
  consumed fixtures remain unactivated. The current six-record set is DR-0002
  Revision 11, DR-0006 Revision 6, DR-0008 Revision 11, DR-0011 Revision 8,
  DR-0012 Revision 7, and DR-0013 Revision 5. DR-0002/0008 remain Proposed with
  Owner approval Pending and Review Complete; the four revised records remain
  Proposed with Owner approval Pending and Review Pending. The completed Batch 9
  Double review targeted `6cf17270fda2827756c24a8d0fb301bef358f98f` and is
  stale for the revised records; it is evidence, not acceptance.
  See [Current review and future activation obligations](#current-review-and-future-activation-obligations).
  It does not
  depend on CK-KICK-011.
- CK-KICK-013 is active with its Rust-first/Cargo platform proposal integrated
  as Proposed but not accepted or implemented. DR-0013 Revision 5 has Owner
  approval Pending and Review Pending; the completed Batch 9 Double review
  targeted `6cf17270fda2827756c24a8d0fb301bef358f98f` and is stale for the
  revised record. Its four readiness stages gate
  shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry respectively. The disposable Python
  discovery host remains distinct from the proposed production platform.

## Active work

- The selected Single independent implementation review of CK-KICK-010 and
  its evidence boundary is complete; findings and dispositions are recorded in
  `RESULTS.md`. Main consolidated validation passed after the corrections; no
  second review or review-until-clean pass was run. This does not reopen
  DR-0009/0010.
- Keep CK-KICK-012's active semantic, fixture-admission, and compatibility work
  bounded and obtain current-revision review and owner disposition for the
  Batch 10-revised proposals; do not activate
  parser/resolver packages or compiler fixtures until the four readiness stages'
  prerequisites are met. The active Proposed body-document, body-graph, and
  build-operation documents do not activate implementation packages.
- Keep CK-KICK-013's Rust-first platform direction Proposed and unimplemented;
  obtain owner disposition before DR-0013 acceptance. Acceptance alone would
  activate only the empty Cargo shell; schema/manifest, numeric/frame/output,
  and resolver/seam prerequisites gate later stages. Any performance claim must
  have reproducible benchmark and hardware-profile evidence.
- Preserve the accepted governance process and all historical decision/review
  evidence without reopening the parked confirmatory protocol.

## Proposed decisions and review state

The [decision registry](../decisions/registry.md) is the index for exact DR
metadata. Current non-governance proposals include:

- [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
  source set and resolved body graph — Revision 11, Proposed, Owner approval
  Pending, Review Complete; recommendation Accept High / Accept Medium.
- [DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md),
  compiled avatar and bounded real-time execution — Revision 2, Proposed,
  Review Complete, owner disposition pending.
- [DR-0004](../decisions/DR-0004-external-automation-through-cli-and-api.md),
  shared domain operations — Revision 2, Proposed, Review Complete, owner
  disposition pending.
- [DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md),
  initial product boundary — Revision 1, Proposed, Review Complete, owner
  disposition pending.
- [DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
  semantic and artifact identity — Revision 6, Proposed, Owner approval
  Pending, Review Pending after Batch 10; prior recommendation is stale.
- [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md) and
  [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
  first-proof and morphology boundaries — DR-0007 remains Proposed with its
  current review; DR-0008 Revision 11 is Proposed, Owner approval Pending,
  Review Complete; recommendation Accept High / Accept High.
- [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
  semantic vocabulary, measurements, and coordinate frames — Revision 8,
  Proposed, Owner approval Pending, Review Pending after Batch 10; prior
  recommendation is stale.
- [DR-0012](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
  initial body-document encoding, resolution, and compatibility — Revision 7,
  Proposed, Owner approval Pending, Review Pending after Batch 10; prior
  recommendation is stale.
- DR-0013, Rust-first production semantic/compiler platform — Revision 5,
  Proposed, Owner approval Pending, Review Pending after Batch 10; prior
  recommendation is stale; proposal integrated but not accepted or implemented.
- [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  and [DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  are parked as described in [Current activation state](#current-activation-state).

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Operational structure under Accepted DR-0001 Revision 5 |
| Decision-record and review workflow | partial | unverified | Governance accepted; technical/product proposals remain provisional |
| Research/experiment workflow | partial | unverified | Lightweight template exists; no experiment registered |
| Body specification | partial | unverified | Proposed body-document, body-graph, build-operation, and fixture-manifest contracts include Batch 10 discussion-approved updates; DR-0002/0008 remain Revision 11 Review Complete, while DR-0006 Revision 6, DR-0011 Revision 8, DR-0012 Revision 7, and DR-0013 Revision 5 remain Proposed with Owner approval Pending and Review Pending; no accepted format or implementation |
| Build-operation contract | partial | unverified | Proposed canonical public build/output owner exists; serialization, implementation, and artifact store remain unactivated |
| Production implementation platform | not-implemented | not-applicable | CK-KICK-013/DR-0013 Revision 5 is Proposed with Owner approval Pending and Review Pending after Batch 10; prior review evidence is stale and not acceptance. Readiness 1–4 gate shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry; no packages activated |
| Creature compiler | partial | unverified | Disposable CK-KICK-010 walking skeleton implemented; this is not a production compiler |
| CK-KICK-010 walking skeleton | implemented | audited | Valid/invalid local evidence and the selected Single independent review are complete; five substantive findings plus whitespace were dispositioned in RESULTS, not clean; this is not a production compiler |
| Local visual-review gallery | implemented | audited | Focused tests and local HTTP/browser smoke passed; subject_context is presentation-only; no visual-evidence or Stage 1 claim |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

- Obtain current-revision adversarial review and Ben's owner disposition for
  the four Batch 10-revised proposals while retaining Proposed status. Do not
  silently accept them or activate packages, schemas, fixtures, parser/resolver,
  or geometry work meanwhile.
- Keep the DR-0013 acceptance trigger unsatisfied while it remains Proposed;
  if accepted, activate only the Cargo/compiler shell. Do not activate Stage 1
  parser/resolver implementation until exact schema and admitted fixtures/
  contracts are available, and do not create packages while it is Proposed.
- Leave DR-0009/0010 parked unless the activation trigger occurs or Ben
  explicitly reactivates them.

## Explicitly not started

- Implementation packages.
- Large asset or dataset storage.
- External mesh conformance.
- Production distribution, operations, or release automation.

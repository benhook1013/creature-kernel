# Project status

Status date: 2026-08-12

## Phase

Exploratory executable prototype and semantic-contract integration. The
foundation governance and the product, specification, and architecture
proposals remain provisional; current work is integrating the CK-KICK-012 Batch
8/9 and CK-KICK-013 readiness/publication revisions while keeping implementation gated rather than
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
Batch 6, F1–F7, Batch 8, and Batch 9 resolutions are discussion-approved and integrated
as Proposed canonical product/specification/architecture material. Earlier
review evidence is stale after the current revisions. The current six-record
set is DR-0002 Revision 11, DR-0006 Revision 5, DR-0008 Revision 11, DR-0011
Revision 7, DR-0012 Revision 6, and DR-0013 Revision 4. All six remain Proposed
with Owner approval Pending and Review Pending. The prior current Double review
is stale historical evidence against commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`; its seven consolidated findings
were resolved by Batch 9 discussion and are not awaiting discussion. A fresh
current-revision Double review of all six records is required before owner
disposition. These resolutions are not acceptance or implementation.

CK-KICK-013 is active with its discussion-approved Rust-first platform
proposal integrated as Proposed material, not accepted or implemented.
Proposed DR-0013 Revision 4 has Owner approval Pending and Review Pending. The
prior current Double review is stale historical evidence against commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`; its seven findings were resolved by
Batch 9 discussion and are not awaiting discussion. A fresh current-revision
Double review is required before owner disposition.
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
targeting, idempotent publication, target conflict, and lineage-checked
inspection. `output-failure` covers trusted derived-output/publication
failure; build identity always exists, artifact identity only after successful
publication, and artifact inspection is a separate read operation. Future workers require protocol/version
negotiation, bounded resources/time, crash/timeout/resource mapping, output
validation, and compiler survival. Python remains for disposable experiments,
evidence/render tooling, and visual workbench tasks, not as a production
compiler dependency. The first reference path is WSL2 x86_64 GNU;
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
Ben's discussion-approved Batch 8 and Batch 9 resolutions materially revised
the six proposals. The prior current Double review is stale historical
evidence against commit `b19adf76aad7d672c0871bd38fc34739f3f4ac39`. Its seven
consolidated findings were resolved by Batch 9 discussion and are preserved
below as historical evidence; none is awaiting discussion. A fresh
current-revision Double review of all six records is required before owner
disposition. The addressed findings were:

- C1 — resolver snapshot finalization/status mapping.
- C2 — canonical build/artifact specification owner.
- C3 — candidate/committed artifact identity plus target, collision, retry, and
  inspection lifecycle.
- C4 — absent-module root identity/referenceability.
- C5 — Readiness 2 manifest admission/contract.
- C6 — CK-KICK-014 exploratory-surface prerequisite conflict.
- C7 — build/worker/publication outcome matrix and trusted failure-bundle
  boundary.

Review completion in the stale artifact means evidence existed only; no finding
was auto-fixed, no DR was accepted, and no implementation activated. Batch 9 is
discussion-approved Proposed material, not a clean review or acceptance. The
next step is the fresh exact-target Double review, followed by owner
disposition; no implementation activates.
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
revisions. The Batch 8/9 resolutions are discussion-approved Proposed changes,
not acceptance or a clean review.
The cross-cutting proposal is [DR-0012: initial
body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The [Proposed body-document contract](../../spec/body-document/README.md),
[Proposed body-graph contract](../../spec/body-graph/README.md), and
[Proposed build-operation contract](../../spec/build-operation/README.md) are
now active canonical specification areas. No implementation package, machine schema,
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
- CK-KICK-012 is active with Batches 1, 4, 5, 6, F1–F3, Batch 8, and Batch 9 integrated
  as Proposed documentation; its parser and resolver proposals activate the
  two specification families, while implementation packages and compiler-
  consumed fixtures remain unactivated. The current six-record set is DR-0002
  Revision 11, DR-0006 Revision 5, DR-0008 Revision 11, DR-0011 Revision 7,
  DR-0012 Revision 6, and DR-0013 Revision 4, all Proposed with Owner approval
  Pending and Review Pending. The prior current Double review is stale
  historical evidence; its seven findings were resolved by Batch 9 discussion
  and are not awaiting discussion. A fresh exact-target Double review of all
  six records is required before owner disposition. Earlier review evidence is
  stale. It does not
  depend on CK-KICK-011.
- CK-KICK-013 is active with its Rust-first/Cargo platform proposal integrated
  as Proposed but not accepted or implemented. DR-0013 Revision 4 has Owner
  approval Pending and Review Pending; the prior seven findings are stale
  historical evidence resolved by Batch 9 discussion and are not awaiting
  discussion. A fresh exact-target Double review is required before owner
  disposition. Earlier review evidence is stale. Its four readiness stages gate
  shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry respectively. The disposable Python
  discovery host remains distinct from the proposed production platform.

## Active work

- The selected Single independent implementation review of CK-KICK-010 and
  its evidence boundary is complete; findings and dispositions are recorded in
  `RESULTS.md`. Main consolidated validation passed after the corrections; no
  second review or review-until-clean pass was run. This does not reopen
  DR-0009/0010.
- Keep CK-KICK-012's active semantic and compatibility work bounded and obtain
  owner disposition for the Batch 9-revised proposals; do not activate
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
  Pending, Review Pending; the prior seven findings are stale historical
  evidence resolved by Batch 9 discussion, and a fresh Double review is required.
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
  semantic and artifact identity — Revision 5, Proposed, Owner approval
  Pending, Review Pending; a fresh Double review is required.
- [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md) and
  [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
  first-proof and morphology boundaries — DR-0007 remains Proposed with its
  current review; DR-0008 Revision 11 is Proposed, Owner approval Pending,
  Review Pending; the prior seven findings are stale historical evidence
  resolved by Batch 9 discussion, and a fresh Double review is required.
- [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
  semantic vocabulary, measurements, and coordinate frames — Revision 7,
  Proposed, Owner approval Pending, Review Pending; the prior seven findings
  are stale historical evidence resolved by Batch 9 discussion, and a fresh
  Double review is required.
- [DR-0012](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
  initial body-document encoding, resolution, and compatibility — Revision 6,
  Proposed, Owner approval Pending, Review Pending; the prior seven findings
  are stale historical evidence resolved by Batch 9 discussion, and a fresh
  Double review is required.
- DR-0013, Rust-first production semantic/compiler platform — Revision 4,
  Proposed, Owner approval Pending, Review Pending; the prior seven findings
  are stale historical evidence resolved by Batch 9 discussion, and a fresh
  Double review is required; proposal integrated but not accepted or
  implemented.
- [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  and [DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  are parked as described in [Current activation state](#current-activation-state).

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Operational structure under Accepted DR-0001 Revision 5 |
| Decision-record and review workflow | partial | unverified | Governance accepted; technical/product proposals remain provisional |
| Research/experiment workflow | partial | unverified | Lightweight template exists; no experiment registered |
| Body specification | partial | unverified | Proposed body-document, body-graph, and build-operation contracts include Batch 8/9 discussion-approved updates; DR-0002 Revision 11, DR-0006 Revision 5, DR-0008 Revision 11, DR-0011 Revision 7, DR-0012 Revision 6, and DR-0013 Revision 4 remain Proposed with Owner approval Pending and Review Pending; prior review findings are stale historical evidence resolved by Batch 9 discussion; no accepted format or implementation |
| Build-operation contract | partial | unverified | Proposed canonical public build/output owner exists; serialization, implementation, and artifact store remain unactivated |
| Production implementation platform | not-implemented | not-applicable | CK-KICK-013/DR-0013 Revision 4 is Proposed with Owner approval Pending and Review Pending; prior review findings are stale historical evidence resolved by Batch 9 discussion. A fresh Double review is required before owner disposition. Readiness 1–4 gate shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry; no packages activated |
| Creature compiler | partial | unverified | Disposable CK-KICK-010 walking skeleton implemented; this is not a production compiler |
| CK-KICK-010 walking skeleton | implemented | audited | Valid/invalid local evidence and the selected Single independent review are complete; five substantive findings plus whitespace were dispositioned in RESULTS, not clean; this is not a production compiler |
| Local visual-review gallery | implemented | audited | Focused tests and local HTTP/browser smoke passed; subject_context is presentation-only; no visual-evidence or Stage 1 claim |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

- Obtain a fresh exact-target Double review of all six Batch 9-revised
  proposals, then obtain owner disposition while retaining Proposed status. Do
  not activate packages, schemas, fixtures, parser/resolver, or geometry work
  meanwhile.
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

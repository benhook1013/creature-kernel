# Project status

Status date: 2026-08-11

## Phase

Exploratory executable prototype and semantic-contract integration. The
foundation governance and the product, specification, and architecture
proposals remain provisional; current work is integrating the CK-KICK-012 F1–F3
and CK-KICK-013 F4–F7 revisions while keeping implementation gated rather than
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
Batch 6, and F1–F7 resolutions are discussion-approved and integrated as
Proposed canonical product/specification/architecture material. The prior
CK-KICK-012 Batch 5 review at commit `a282dbabffd83afa4e62577086934d00f98e12c7`
and Batch 6 review at `c64b1b...` are stale historical evidence. DR-0002
Revision 9, DR-0008 Revision 9, DR-0011 Revision 5, and DR-0012 Revision 4
remain Proposed with Owner approval Pending and current Review Pending; DR-0013
is Revision 2 with the same Proposed/Pending/Pending state. A fresh current
Double review is pending for all five. The seven resolutions are discussion-
approved, not accepted or implemented; no current review is clean.

CK-KICK-013 is active with its discussion-approved Rust-first platform
proposal integrated as Proposed material, not accepted or implemented.
Proposed DR-0013 Revision 2 has Owner approval Pending and current Review
Pending; its prior `c64b1b...` review is stale and a fresh current Double review
is pending. Acceptance of DR-0013 alone triggers the Cargo workspace and empty
compiler/library/CLI shell boundary; exact schema and admitted fixtures still
gate Stage 1 parser/resolver implementation. The proposal includes a stable
Rust semantic/compiler core, thin CLI, versioned project-owned
backend-neutral GeometryRequest/GeometryResult seam, immutable build-scoped
sibling staging, manifest-last atomic no-replace publication, identity/path/
hash/size validation, and rejection of symlinked, unlisted, incomplete,
mixed-build, or stale bundles. Future workers require protocol/version
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
Attachment-cardinality resolutions. These discussion approvals do not accept
or silently replace the DRs. The canonical documents now state explicit Part
containment, descendant Socket Attachment placement, canonical resolved frame
records, the closed operation/bootstrap/status/resource contract, and the
resolved diagnostic/cardinality rules. The prior Batch 6 review is stale
historical evidence after the F1–F7 revisions; a fresh current Double review is
pending for the revised records. The seven resolutions are discussion-approved
Proposed changes, not acceptance or a clean review.
DR-0006 remains Proposed with its current revision's review evidence and owner
disposition state. The cross-cutting proposal is [DR-0012: initial
body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The [Proposed body-document contract](../../spec/body-document/README.md) and
[Proposed body-graph contract](../../spec/body-graph/README.md) are now active
canonical specification areas. No implementation package, machine schema,
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
- CK-KICK-012 is active with Batches 1, 4, 5, 6, and F1–F3 integrated as
  Proposed documentation; its parser and resolver proposals activate the two
  specification families, while implementation packages and compiler-consumed
  fixtures remain unactivated. DR-0002/0008/0011/0012 are at Revisions 9/9/5/4
  with Owner approval Pending and current Review Pending. The prior Double
  review is stale historical evidence; a fresh current Double review is
  pending. It does not depend on CK-KICK-011.
- CK-KICK-013 is active with its Rust-first/Cargo platform proposal integrated
  as Proposed but not accepted or implemented. DR-0013 Revision 2 has Owner
  approval Pending and current Review Pending; its prior Double review is stale
  and a fresh current Double review is pending. The disposable Python
  discovery host remains distinct from the proposed production platform.

## Active work

- The selected Single independent implementation review of CK-KICK-010 and
  its evidence boundary is complete; findings and dispositions are recorded in
  `RESULTS.md`. Main consolidated validation passed after the corrections; no
  second review or review-until-clean pass was run. This does not reopen
  DR-0009/0010.
- Keep CK-KICK-012's active semantic and compatibility work bounded; it must not
  promote the disposable host into a production platform or contract. Obtain
  owner disposition after the fresh current Double review of the discussion-
  approved F1–F3 revisions, then proceed to exact field/numeric/frame/fixture
  work as appropriate. The active Proposed body-document/body-graph documents
  do not activate implementation packages or compiler fixtures.
- Keep CK-KICK-013's Rust-first platform direction Proposed and unimplemented
  while its fresh current Double review is pending; obtain owner disposition
  before DR-0013 acceptance. Acceptance alone would activate only the empty
  Cargo shell, while exact schema and admitted fixtures still gate Stage 1
  parser/resolver implementation. Any performance claim must have reproducible
  benchmark and hardware-profile evidence.
- Preserve the accepted governance process and all historical decision/review
  evidence without reopening the parked confirmatory protocol.

## Proposed decisions and review state

The [decision registry](../decisions/registry.md) is the index for exact DR
metadata. Current non-governance proposals include:

- [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
  source set and resolved body graph — Revision 9, Proposed, Owner approval
  Pending, current Review Pending; prior Double review stale, fresh current
  Double review pending.
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
  semantic and artifact identity — Revision 4, Proposed, Owner approval
  Pending, Review Complete, owner disposition pending.
- [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md) and
  [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
  first-proof and morphology boundaries — DR-0007 remains Proposed with its
  current review; DR-0008 Revision 9 is Proposed, Owner approval Pending,
  current Review Pending; prior Double review stale, fresh current Double
  review pending.
- [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
  semantic vocabulary, measurements, and coordinate frames — Revision 5,
  Proposed, Owner approval Pending, current Review Pending; prior Double review
  stale, fresh current Double review pending.
- [DR-0012](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
  initial body-document encoding, resolution, and compatibility — Revision 4,
  Proposed, Owner approval Pending, current Review Pending; prior Double review
  stale, fresh current Double review pending.
- DR-0013, Rust-first production semantic/compiler platform — Revision 2,
  Proposed, Owner approval Pending, current Review Pending; prior Double review
  stale, fresh current Double review pending; proposal integrated but not
  accepted or implemented.
- [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  and [DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  are parked as described in [Current activation state](#current-activation-state).

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Operational structure under Accepted DR-0001 Revision 5 |
| Decision-record and review workflow | partial | unverified | Governance accepted; technical/product proposals remain provisional |
| Research/experiment workflow | partial | unverified | Lightweight template exists; no experiment registered |
| Body specification | partial | unverified | Proposed body-document and body-graph contracts include F1–F3 discussion-approved updates; DR-0002/0008/0011/0012 remain Proposed at Revisions 9/9/5/4 with Owner approval Pending and current Review Pending; prior Double review stale and fresh current Double review pending; no accepted format or implementation |
| Production implementation platform | not-implemented | not-applicable | CK-KICK-013/DR-0013 Revision 2 is Proposed with Owner approval Pending and current Review Pending; prior Double review stale and fresh current Double review pending. DR-0013 acceptance alone activates the empty Cargo shell; exact schema/admitted fixtures still gate Stage 1 parser/resolver work; no packages activated |
| Creature compiler | partial | unverified | Disposable CK-KICK-010 walking skeleton implemented; this is not a production compiler |
| CK-KICK-010 walking skeleton | implemented | audited | Valid/invalid local evidence and the selected Single independent review are complete; five substantive findings plus whitespace were dispositioned in RESULTS, not clean; this is not a production compiler |
| Local visual-review gallery | implemented | audited | Focused tests and local HTTP/browser smoke passed; subject_context is presentation-only; no visual-evidence or Stage 1 claim |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

- Obtain Ben's owner disposition after the fresh current Double review of the
  discussion-approved F1–F7 revisions; retain Proposed status until then. Only
  afterward do exact field/numeric/frame/fixture work or Stage 1 planning.
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

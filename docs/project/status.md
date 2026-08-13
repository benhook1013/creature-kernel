# Project status

Status date: 2026-08-13

## Phase

Exploratory executable prototype and semantic-contract integration. The
foundation governance and the product, specification, and architecture
proposals remain provisional; current work is integrating the CK-KICK-012 Batch
8/9/10/11/12/13 and CK-KICK-013 readiness/publication revisions while keeping implementation gated rather than
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

The foundation scaffold and governance process are integrated. Accepted DR-0001
Revision 5 remains the operative governance baseline while DR-0001 Revision 6
is Proposed transition guidance: Ben approved its workflow direction, but
its current review is Complete and formal acceptance remains pending Ben's
disposition. DR-0002 through
DR-0013 remain Proposed with their review and owner-disposition history
preserved. Ben's CK-KICK-012 Batch 5, Batch 6, F1–F7, Batch 8, Batch 9, Batch
10, Batch 11, Batch 12, and Batch 13 resolutions are discussion-approved and
integrated as Proposed canonical product/specification/architecture/project
material. The current six-record set is DR-0002 Revision 11, DR-0006 Revision
12, DR-0008 Revision 11, DR-0011 Revision 15, DR-0012 Revision 14, and DR-0013
Revision 12. DR-0002 and DR-0008 remain Proposed with Owner approval Pending
and Review Complete. DR-0006, DR-0011, DR-0012, and DR-0013 remain Proposed
with Owner approval Pending and Review Complete after the current Double review
at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The original Batch 13 review at exact commit
`8c38c501eb1262a1b85af0b8605220625601772f` produced D1–D3/P1–P3, which were
dispositioned in DR-0006/0011/0012/0013 Revisions 10/13/12/10. The earlier-
predecessor review at exact commit `763cff22d10f6491a05a28312a25250704543dcf`
produced G1/G2 and T1–T4; its artifacts are stale for these successors. G1/G2
were fixed mechanically, T1–T3 were resolved, and T4 remains unselected and
deferred, requiring Ben's retained-human disposition before adapter profile/
schema activation; it does not block the empty first Rust slice. The
immediate-predecessor review at exact commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in these revisions. The 9c governance pass corrected two mechanical
history-label issues and its technical pass found no findings / Ready for PR at
High confidence. Review Complete is evidence only. No acceptance, schema,
fixture, parser/resolver, adapter, Cargo package, readiness, experiment, or
implementation activates. The current review state and next action are
recorded below.

CK-KICK-013 is active with its discussion-approved Rust-first platform
proposal integrated as Proposed material, not accepted or implemented.
Proposed DR-0013 Revision 12 has Owner approval Pending and Review Complete after
the current Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The original 8c38c501 Batch 13
review produced D/P findings later dispositioned in Revision 10. The earlier
predecessor 763cff22 review produced G1/G2 and T1–T4; G1/G2 were fixed
mechanically, T1–T3 were resolved, and T4 remains unselected and deferred,
requiring Ben's retained-human disposition before adapter profile/schema
activation; it does not block the empty first Rust slice.
The immediate-predecessor 9b96d18 review is stale; its findings were corrected
in the current revisions. The 9c technical pass found no findings / Ready for
PR at High confidence. Review Complete is evidence only. This
is not acceptance, and no schema, fixture, parser/resolver,
adapter, Cargo package, readiness, experiment, or implementation activates.
The review at exact target commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` found stale historical/current
labels, an omitted retained-human checkpoint for T4, an incomplete comparator
precedence/rank gate, product-level sqrt/norm ambiguity, and a stray DR-0006
word. These findings were corrected in current successor revisions
12/15/14/12; that review is stale for the successors. T4 remains
unselected and requires Ben's retained-human disposition before adapter
profile/schema activation; it does not block the empty first Rust slice.
The proposed activation order is numeric/frame semantics, semantic addresses,
canonical data/digests, diagnostics, exact schema/manifest, Readiness 2, and a
distinct Readiness 3 successor transaction. No gate activates while the DRs
remain Proposed. Readiness 1 would be acceptance-only: accepted DR-0013 activates
only the empty Cargo shell; a versioned, preflighted fixture manifest, its listed
files, exact JSON Schema, and parser/bootstrap activate together in one
review-branch transaction; the distinct Readiness 3 transaction then activates
canonical numeric/frame rules plus frozen expected graph outputs and semantic
resolver/in-memory snapshot handoff; and a working
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
boundary. Batch 13 additionally keeps future adapters separate: signed
permutation `C` plus finite positive scale `s`, storage/output-only default or
optional runtime-conformance tier, explicit target precision/domain narrowing,
and FTZ/DAZ/subnormal probes. This is Proposed planning material only.

## Current review and future activation obligations

Batch 11, Batch 12, and Batch 13 are discussion-approved as Proposed material. Their
focused contract owners cover typed semantic addresses, canonical bytes/digest
domains, numeric/frame comparison semantics, and a small diagnostic registry.
Exact numeric bounds remain evidence-dependent; the planned
[numeric/frame profile experiment](../research/numeric-frame-profile-experiment.md)
is unregistered and has no results or evidence. Its Proposed protocol now
requires preregistered intended domains, separate semantic error budgets,
correctly rounded decimal-admission rules, fixed operation order and compiler
floating-point controls, rational/ULP boundaries, deterministic
normalization/square-root fixtures, offline H derivation, structured claim
identity/order fixtures, exact/higher-precision independent oracles, frozen
development/held-out/adversarial corpora, metamorphic and all-pairs checks,
condition estimates, and a validation margin whose formula/constant remain
open. The normative common-frame comparator, exact dyadic arithmetic,
normalization/sign direction, claim-ID, and sorted-pair direction are fixed
Proposed material; constants, ranges, margins/error formula, and deterministic
evaluation bindings remain open. Future adapter evidence covers signed
permutation/scale (vector lengths `sC`, scalar lengths `s`), storage/output and runtime tiers, precision/domain
narrowing, and FTZ/DAZ/subnormal probes. Activation order is numeric/frame,
address, canonical data, diagnostics, exact schema/manifest, Readiness 2, then
a distinct Readiness 3 expected-snapshot/comparison transaction. No gate or
implementation package activates from this status entry.

Diagnostic compatibility remains Proposed: nine initial domains are
source-admission, dependency, semantic-identity, graph-structure,
frame-numeric, resource, execution-trust, publication, and inspection, with
one tiny mandatory bootstrap registry/profile for unknown registry/profile
negotiation. Exact codes and serialized fields remain fixture-gated.
Readiness implementation binding remains a separate scoped content-identity
input from the fixture payload and expected snapshots; no binding is active.

The original Batch 13 Double review examined exact target commit
`8c38c501eb1262a1b85af0b8605220625601772f` and produced D1–D3/P1–P3; those
were dispositioned in the immediate successor revisions 10/13/12/10. The
earlier-predecessor review examined exact target commit
`763cff22d10f6491a05a28312a25250704543dcf` and produced G1/G2 and T1–T4; its
artifacts are stale for the current revisions. G1/G2 were fixed mechanically,
T1–T3 were resolved, and T4 remains unselected and deferred, requiring Ben's
retained-human disposition before adapter profile/schema activation; it does not
block the empty first Rust slice. The immediate-predecessor review examined
exact target `9b96d18b115126ef09e54ad8c6f21749d5559ff6`; its findings were
corrected in the current revisions. The current review examined exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`: its governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. Review Complete is evidence only; all four
records remain Proposed with Owner approval Pending. No acceptance, schema,
fixture, parser/resolver, adapter,
Cargo package, readiness, experiment, or implementation activates.

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

Batch 10 integrated its approved resolutions as stale Proposed historical
material, and Batch 11 integrated the approved machine-contract resolutions as
current Proposed material:
separate request/attempt/candidate identities and deterministic retry/collision
rules; the initial WSL `/home` filesystem profile and process-crash-safe
namespace publication boundary; separate inspection statuses and shared
completeness/diagnostic conventions; producer/output versus
coordinator/reporter/publisher trust; immutable fixture-manifest reviewed-tree
and activation-payload binding with append-only successor/deactivation rules;
and the conceptual body-document shape, typed collections, basis/frame/profile,
and omission/default rules. Batch 11 adds the typed semantic-address,
numeric/frame, canonical-data, and diagnostic profiles; Batch 12/13 improves
the numeric evidence protocol and makes DR-0006 Revision 12, DR-0011 Revision
15, DR-0012 Revision 14, and DR-0013 Revision 12 current. These records remain
Proposed with Owner approval Pending and Review Complete after the current
Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. Prior Batch 13 review evidence is stale for
these revisions; G1/G2 were fixed mechanically, T1–T3 were resolved, and T4
remains unselected and deferred, requiring Ben's retained-human disposition
before adapter profile/schema activation; it does not block the empty first Rust
slice. All records remain Proposed, and no
schema, fixture, parser/resolver, adapter, Cargo package, readiness,
experiment, or implementation activates.
DR-0002 Revision 11 and DR-0008 Revision 11 are unchanged and remain Review
Complete. Owner approval remains Pending.

The immediate next action is fresh review of the current resolution revisions.
The main thread will autonomously resolve technical correctness findings or
record evidence-dependent triggers under the DR-0001 Revision 6 transition
direction; only a retained-human product, architecture-boundary, material
trade-off, or external-impact finding returns to Ben. No proposal is silently
accepted.
No implementation/readiness gate activates while the records remain Proposed.
Earlier Batch 8/9 and other
review artifacts remain preserved as stale historical evidence.
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
transform, readiness, and build/publication resolutions, followed by the
Batch 11 machine-contract resolutions. These discussion approvals do not accept
or silently replace the DRs. The canonical documents now state explicit Part
containment, descendant Socket Attachment placement, canonical resolved frame
records, the closed operation/bootstrap/status/resource contract, the
in-memory snapshot handoff, the build-operation owner, and the resolved
diagnostic/cardinality rules. Earlier review evidence is stale after these
revisions. The Batch 8/9/10/11 resolutions are discussion-approved Proposed changes,
not acceptance or a clean review.
The cross-cutting proposal is [DR-0012: initial
body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
The [Proposed body-document contract](../../spec/body-document/README.md),
[Proposed body-graph contract](../../spec/body-graph/README.md),
[Proposed fixture-manifest contract](../../spec/fixture-manifest/README.md),
and [Proposed build-operation contract](../../spec/build-operation/README.md)
are now active canonical specification areas. No implementation package, machine schema,
numeric limit, exact fixture, or geometry backend is selected; the Batch 11
canonical basis and machine profiles remain Proposed and activation-gated;
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
- CK-KICK-012 is active with Batches 1, 4, 5, 6, F1–F3, Batch 8, Batch 9, Batch
  10, Batch 11, Batch 12, and Batch 13 integrated as Proposed documentation; its parser/resolver and
  fixture-admission proposals establish the four Proposed specification families, while implementation packages and compiler-
  consumed fixtures remain unactivated. The current six-record set is DR-0002
  Revision 11, DR-0006 Revision 12, DR-0008 Revision 11, DR-0011 Revision 15,
  DR-0012 Revision 14, and DR-0013 Revision 12. DR-0002/0008 remain Proposed
  with Owner approval Pending and Review Complete; DR-0006 and the three
  materially revised records remain Proposed with Owner approval Pending and
  Review Complete after the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. Prior Batch
  13 review evidence is stale historical evidence; G1/G2 were fixed
  mechanically, T1–T3 were resolved, and T4 remains unselected and deferred,
  requiring Ben's retained-human disposition before adapter profile/schema
  activation; it does not block the empty first Rust slice. The immediate-predecessor 9b96d18 review is stale; its findings were corrected. The 9c governance pass corrected two mechanical history-label issues and its technical pass found no findings / Ready for PR at High confidence.
  The completed Batch 9 Double review targeted
  `6cf17270fda2827756c24a8d0fb301bef358f` and is stale for the revised records;
  it is evidence, not acceptance.
  See [Current review and future activation obligations](#current-review-and-future-activation-obligations).
  It does not
  depend on CK-KICK-011.
- CK-KICK-013 is active with its Rust-first/Cargo platform proposal integrated
  as Proposed but not accepted or implemented. DR-0013 Revision 12 has Owner
  approval Pending and Review Complete after the current Double review at exact
  target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior Batch 13 review evidence is stale historical evidence, G1/G2 were
  fixed mechanically, T1–T3 were resolved, and T4 remains unselected and
  deferred, requiring Ben's retained-human disposition before adapter
  profile/schema activation; it does not block the empty first Rust slice. The immediate-predecessor 9b96d18 review is stale; its findings were corrected. Its four readiness stages gate
  shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry respectively. The disposable Python
  discovery host remains distinct from the proposed production platform.

## Active work

- The selected Single independent implementation review of CK-KICK-010 and
  its evidence boundary is complete; findings and dispositions are recorded in
  `RESULTS.md`. Main consolidated validation passed after the corrections; no
  second review or review-until-clean pass was run. This does not reopen
  DR-0009/0010.
- Keep CK-KICK-012's active semantic, fixture-admission, numeric, claim-identity,
  adapter, and compatibility work bounded and retain the current 9c Review
  Complete evidence after the immediate-predecessor technical resolutions; do
  not activate parser/resolver packages or compiler fixtures until the four
  readiness stages' prerequisites are met. The active Proposed body-document,
  body-graph, and build-operation documents do not activate implementation
  packages.
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
  semantic and artifact identity — Revision 12, Proposed, Owner approval
  Pending, Review Complete after the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior Batch 13 review evidence is
  stale historical evidence.
- [DR-0007](../decisions/DR-0007-staged-first-proof-charter.md) and
  [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
  first-proof and morphology boundaries — DR-0007 remains Proposed with its
  current review; DR-0008 Revision 11 is Proposed, Owner approval Pending,
  Review Complete; recommendation Accept High / Accept High.
- [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
  semantic vocabulary, measurements, and coordinate frames — Revision 15,
  Proposed, Owner approval Pending, Review Complete after the current Double
  review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior
  Batch 13 review evidence is stale historical evidence.
- [DR-0012](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md),
  initial body-document encoding, resolution, and compatibility — Revision 14,
  Proposed, Owner approval Pending, Review Complete after the current Double
  review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior
  Batch 13 review evidence is stale historical evidence.
- DR-0013, Rust-first production semantic/compiler platform — Revision 12,
  Proposed, Owner approval Pending, Review Complete after the current Double
  review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; proposal
  integrated but not accepted or implemented.
- [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  and [DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  are parked as described in [Current activation state](#current-activation-state).

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Operational structure under Accepted DR-0001 Revision 5 |
| Decision-record and review workflow | partial | unverified | Governance accepted; technical/product proposals remain provisional |
| Research/experiment workflow | partial | unverified | Lightweight template exists; no experiment registered |
| Body specification | partial | unverified | Proposed body-document, body-graph, build-operation, fixture-manifest, and Batch 11/12/13 focused profiles include discussion-approved updates; DR-0002/0008 remain Revision 11 Review Complete, while DR-0006 Revision 12, DR-0011 Revision 15, DR-0012 Revision 14, and DR-0013 Revision 12 are Proposed with Owner approval Pending and Review Complete at 9c evidence; no format or implementation is accepted |
| Build-operation contract | partial | unverified | Proposed canonical public build/output owner exists; serialization, implementation, and artifact store remain unactivated |
| Production implementation platform | not-implemented | not-applicable | CK-KICK-013/DR-0013 Revision 12 is Proposed with Owner approval Pending and Review Complete at 9c evidence; numeric/frame, address, canonical-data, diagnostics, schema/manifest, Readiness 2, distinct Readiness 3, adapter, and exploratory geometry remain gated; no packages activated |
| Creature compiler | partial | unverified | Disposable CK-KICK-010 walking skeleton implemented; this is not a production compiler |
| CK-KICK-010 walking skeleton | implemented | audited | Valid/invalid local evidence and the selected Single independent review are complete; five substantive findings plus whitespace were dispositioned in RESULTS, not clean; this is not a production compiler |
| Local visual-review gallery | implemented | audited | Focused tests and local HTTP/browser smoke passed; subject_context is presentation-only; no visual-evidence or Stage 1 claim |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

- Record the completed 9c current review and its mechanical history-label
  dispositions. The main thread may autonomously disposition technical findings;
  only
  retained-human product, architecture-boundary, material-trade-off, or
  external-impact findings return to Ben. Retain Proposed status and do not
  activate packages, schemas, fixtures, parser/resolver, or geometry work
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

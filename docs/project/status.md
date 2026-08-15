# Project status

Status date: 2026-08-15

## Phase

Exploratory executable prototype and semantic-contract integration. The
foundation governance and the product, specification, and architecture
proposals remain provisional; current work is integrating the CK-KICK-012 Batch
8/9/10/11/12/13 and CK-KICK-013 readiness/publication revisions while keeping later implementation gated rather than
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

## Current Readiness 2

DR-0013 Readiness 1 remains active. The exact `creature-kernel.body` r1 schema,
`creature-kernel.fixture-manifest` r1 manifest, nine listed fixtures, Rust
parser/bootstrap, and Python preflight are now the Active Readiness 2
parser/bootstrap/schema/manifest/fixture transaction. The preflight checks
internal consistency and emits `ck.path-set.raw.v1`, while the evidence
generator separately binds implementation, admission support, resolved Cargo
dependencies/features, and the build request. The
[Readiness 2 admission record](readiness-2-admission.md) records the exact
post-merge recomputation from merged commit
`766992ab089687e9b1496574e8ffa721388d96f3` (PR #6): every bound identity and
policy matched, and the sanitized runner passed 26 core parser/bootstrap tests
plus target-explicit locked/offline clippy with warnings denied. No Proposed
owning DR is accepted by this activation.
That admission record pins the reviewed source commit, merged commit, and
evidence identities.
Its owner approval is Approved by Ben on 2026-08-13, and its review status is
Waived: the agreed Double adversarial review completed, consolidated validation
passes, and Ben instructed “do it” in response to “approve and waive,” with no
repeat current-candidate review loop. Readiness 2 is current and active; this
does not activate the distinct Readiness 3 resolver/snapshot transaction.

## Current implementation status

Readiness 2 remains active for the admitted schema, manifest, fixtures,
parser/bootstrap, and preflight. The workspace now also contains a provisional
structural address/index and validator plus the `inspect-structure` CLI command
as preparatory implementation over admitted documents. This source-preserving
inspection projection is not a finalized resolved snapshot and does not activate
Readiness 3; resolver, canonical/numeric/frame, geometry, and runtime work remain
gated or absent. The active Readiness 2 admission remains the immutable exact
identity at its recorded merge commit; current structural preparation is outside
that admitted implementation identity and requires a future successor
transaction before any Readiness 3 activation claim.

This implementation batch adds a meaningful authored stylized digitigrade-biped
example that passes provisional structural inspection
(1 module, 18 Parts, 17 Joints, 2 Sockets, 1 Attachment, 4 Regions, 3
Capabilities). The CLI now provides structured help and deterministic success
summary counts. Local visual-review tooling now supports immutable read-only
structure sessions alongside legacy image reviews, exposing containment, joints,
composition, regions, capabilities, diagnostics, raw JSON, and an explicit
no-geometry/no-runtime boundary. Hands-on trials found no blockers; native T3
preview was unavailable, while bounded headless Chromium succeeded. These
preparatory results do not constitute Readiness 3 admission or activation:
they do not activate resolver/numeric semantics, geometry, rigging, animation,
physics, or runtime.

The current implementation now provides provisional developer instrumentation:
`inspect-prepared-source --input <path>` plus its bounded
`publish_prepared_source.py`/localhost-server flow. It preserves the admitted
single-source graph projection and adds the declared basis, prepared counts,
and numeric debug rows with binary64 bits and stable semantic locations. Ben's
2026-08-15 appraisal found that the prepared-source projection adds
developer-visible preparation data but no meaningful creature visualization;
the new spatial candidate was locally validated and appraised successfully on
2026-08-15. He does not want
routine implementation details presented for approval. It remains preparatory
only: it does not
resolve dependencies or produce a snapshot or canonical serialization, apply
basis/unit values, interpret quaternions, expand dependencies/modules, produce
geometry, rigging, animation, physics, or runtime output, or activate Readiness
3. PR #14 may be merged as preparatory tooling after its normal checks pass.
This is not blanket merge authority outside the named runway and does not waive
real user-visible or direction-setting decisions.

PR #9, “Add inspectable biped structure workflow,” is merged at commit
`565c32bd35215e23d737fb333604382d3e6958ab`. PR #10, “Add preparatory exact
decimal conversion,” is merged at commit
`fcd071365a9789c81944b2e7e0572f7e21f0d672`. The standalone
`creature_kernel_core::numeric` module is preparatory code only: it
checks strict JSON-number grammar, uses pinned Rust 1.97.1 direct correctly-
rounded binary64 final conversion, returns typed overflow/nonzero-underflow
failures, admits finite subnormals, normalizes lexical zero to `+0`, and has
focused boundary tests. Caller-enforced token/resource limits remain outside
this module. It is not wired into body-document admission, does not alter the
admitted Readiness 2 identity, and does not activate numeric semantics or
Readiness 3. The standalone `creature_kernel_core::frame` module is likewise
preparatory: it provides a normalized-binary64 structural transform carrier,
an exact signed-axis source-basis map, and symbolic length-unit ratios. It does
not apply unit scaling, validate or normalize quaternions, perform transform
algebra or comparison, integrate source documents, resolve graphs, publish
snapshots, or change the active Readiness 2 identity; it does not activate
Readiness 3. The public `creature_kernel_core::source_preparation::prepare_single_source`
operation accepts raw source bytes plus a sealed `ResourceProfile`, performs
whole-document admission, structural validation, basis preparation, and
numeric preparation for one source. Its complete semantic numeric maps cover
part/joint/socket/attachment transforms, landmark positions, dimensions, and
named frames under stable address or owner/role keys; the retained graph source
records and context provide semantic provenance. Raw lexical spelling and
provenance are not recovered. Internal `frame_preparation` helpers cannot
bypass record-level admission. This preparation does not apply basis/unit
values or quaternion semantics, expand dependencies/modules, produce claims,
snapshots, or serialization, or activate a resolver or Readiness 3.
This intentionally retires the provisional public record-level
`frame_preparation` API in favor of the admitted whole-source boundary.

The current implementation also provides a crate-private source-set preparation
projection: it prepares each member independently, retains exact raw bytes and
retained structural source metadata, builds a deterministic `(document,
namespace)` member table, and sorts declared edges deterministically. It does
not perform declaration matching, resolver statuses, cross-source merge,
snapshot, digest, or Readiness 3 activation; it remains preparatory and does
not accept or revise a Proposed decision record.

The current implementation also provides a deliberately restricted exact
reference-placement foundation over one prepared source. It accepts only
canonical metres in the right-handed basis (`+Y` up, `+Z` forward), identity
rotations, and translations that are exact bounded integers in the binary64
carrier for Part placements plus Attachment host/mating Socket frames and
offsets. It composes parent-local Part deltas through containment and checks
exact Attachment agreement between the authored attached-root delta and the
derived equation result. Unrelated Joint and named-frame transforms are not
validated or resolved by this operation. This is not general basis/unit/
quaternion transform math, resolver activation, geometry or surface generation,
or a user-facing rendered creature. The stylized example was corrected from
world-looking authored values to contract-compliant parent-local deltas while
retaining the intended derived reference positions.

Candidate locally validated and appraised by Ben on 2026-08-15: a directly
consuming primitive spatial preview
uses this exact placement result through the existing
`inspect-prepared-source`/`publish_prepared_source.py`/localhost-server flow.
The browser is limited to deterministic semantic point/line scaffolding with
Part markers, containment links, Joint endpoint links, attachment-root
distinction, labels, and front (x/y), side (z/y), and top (x/z) SVG views;
Joint frame transforms are not interpreted. It supplied the first genuine
human-appraisable visual checkpoint; Ben confirmed that its diagrams were
decodable and spatially accurate for the intended straight tail. This remains outside
the Readiness 3 activation boundary and does not claim geometry, mesh, surface,
volume, anatomical quality, rigging, pose/animation, IK, deformation, physics,
general transforms, resolver activation, or runtime evidence.

Ben's 2026-08-15 direction authorizes an autonomous runway of small, internal,
reversible preparatory PRs from this merged checkpoint toward a complete
Readiness 3 successor candidate. Routine numeric/frame, provenance, resolver,
snapshot, diagnostic, fixture, and test implementation may merge after its
required focused checks and risk-scaled review. Stop before merging the
transaction that claims Readiness 3 activation and ask Ben for its required
explicit approval; also stop earlier if work reaches a genuinely useful
rendered-form appraisal or another retained-human boundary. Preparatory merges
do not accept a Proposed DR, freeze activation-gated constants, or activate
Readiness 3.

The first runway slice adds a crate-private, fail-closed exact-dyadic arithmetic
foundation for later typed comparisons. It decodes admitted finite binary64
values without floating-point arithmetic, canonicalizes representation, and
provides checked fixed-shape ordering, addition, subtraction, multiplication,
squaring, and four-term summation under a conservative implementation safety
cap. It supplies no tolerance, profile, claim, resolver, or activation
semantics.

The next runway slice adds a crate-private typed scalar/translation predicate
over that foundation. Callers must supply finite nonnegative absolute and
relative entries explicitly; evaluation follows the specified inclusive exact
dyadic formula and checks all translation components in fixed order. It still
selects no profile identity or tolerance values and has no quaternion, claim,
resolver, diagnostic-status, or activation behavior.

The following runway slice adds crate-private deterministic quaternion
normalization and q/-q sign-canonicalization plumbing. Its fixed binary64
operation sequence and validation hooks are implemented, but normal builds can
construct only an unavailable square-root/environment capability. Provider
execution remains test-only against independently frozen result bits until a
future attested floating-environment boundary and activation-gated profile
constants exist. This slice therefore cannot silently normalize production
source or activate quaternion semantics.

The next runway slice adds the exact canonical-tuple quaternion comparison
predicate over already normalized private carriers. It uses exact dyadic dot
sign selection (`0` chooses positive), fixed four-component squared distance,
and an inclusive explicit `(2H)^2` bound. It chooses no `H`, profile identity,
fallback, or angular interpretation, and the sealed normalizer still prevents
normal-build production use.

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
disposition. DR-0002 through DR-0012 remain Proposed with their review and
owner-disposition history preserved; DR-0013 Revision 12 is Accepted with
Owner approval Approved by Ben and Date decided 2026-08-13. Ben's CK-KICK-012 Batch 5, Batch 6, F1–F7, Batch 8, Batch 9, Batch
10, Batch 11, Batch 12, and Batch 13 product/specification/architecture/project
material remains Proposed where owned by the other records; DR-0013's accepted
platform boundary is recorded below. The current six-record set is DR-0002
Revision 11, DR-0006 Revision 12, DR-0008 Revision 11, DR-0011 Revision 15,
DR-0012 Revision 14, and DR-0013 Revision 12. DR-0002 and DR-0008 remain Proposed with Owner approval Pending
and Review Complete. DR-0006, DR-0011, and DR-0012 remain Proposed with Owner
approval Pending and Review Complete after the current Double review
at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The original Batch 13 review at exact commit
`8c38c501eb1262a1b85af0b8605220625601772f` produced D1–D3/P1–P3, which were
dispositioned in DR-0006/0011/0012/0013 Revisions 10/13/12/10. The earlier-
predecessor review at exact commit `763cff22d10f6491a05a28312a25250704543dcf`
produced G1/G2 and T1–T4; its artifacts are stale for these successors. G1/G2
were fixed mechanically, T1–T3 were resolved, and T4 remains unselected and
deferred, requiring Ben's retained-human disposition before adapter profile/
schema activation; it does not block the current Rust implementation slice. The
immediate-predecessor review at exact commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in these revisions. The 9c governance pass corrected two mechanical
history-label issues and its technical pass found no findings / Ready for PR at
High confidence. The review artifacts remain preserved evidence. DR-0013 is
accepted and Readiness 1 is triggered/active for the Cargo workspace, compiler/
core library shell, and thin CLI shell. The provisional structural address/
index, validator, and inspection command are preparatory implementation. The
exact schema, manifest,
nine fixtures, parser/bootstrap, and preflight are the active Readiness 2
transaction after the recorded merge and post-merge identity recomputation;
the later resolver, adapter, experiment, and geometry gates remain inactive.
The current review state and later activation obligations
are recorded below.

CK-KICK-013 is active with its accepted Rust-first platform boundary and
Readiness 1 shell trigger. DR-0013 Revision 12 has Owner approval Approved by Ben,
Date decided 2026-08-13, and Review Complete after
the current Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. The original 8c38c501 Batch 13
review produced D/P findings later dispositioned in Revision 10. The earlier
predecessor 763cff22 review produced G1/G2 and T1–T4; G1/G2 were fixed
mechanically, T1–T3 were resolved, and T4 remains unselected and deferred,
requiring Ben's retained-human disposition before adapter profile/schema
activation; it does not block the current Rust implementation slice.
The immediate-predecessor 9b96d18 review is stale; its findings were corrected
in the current revisions. The 9c technical pass found no findings / Ready for
PR at High confidence. Review Complete remains preserved evidence; it does not
replace Ben's acceptance. Readiness 1 is triggered/active for the Cargo
workspace, compiler/core library shell, and thin CLI shell. The provisional
structural address/index, validator, and inspection command remain preparatory.
The exact
schema, manifest, nine fixtures, parser/bootstrap, and preflight are the active
Readiness 2 transaction under the admission record; the distinct Readiness 3
resolver/snapshot transaction is not active.
The review at exact target commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` found stale historical/current
labels, an omitted retained-human checkpoint for T4, an incomplete comparator
precedence/rank gate, product-level sqrt/norm ambiguity, and a stray DR-0006
word. These findings were corrected in current successor revisions
12/15/14/12; that review is stale for the successors. T4 remains
unselected and requires Ben's retained-human disposition before adapter
profile/schema activation; it does not block the current Rust implementation
slice.
The later activation order remains numeric/frame semantics, semantic addresses,
canonical data/digests, diagnostics, and then a distinct Readiness 3 successor
transaction. Those later gates remain inactive until their Proposed contracts
and explicit prerequisites are admitted.
Readiness 1 is now active: accepted DR-0013 activates the Cargo workspace,
compiler/core library shell, and thin CLI shell; the provisional structural
address/index, validator, and inspection command are preparatory only; a
versioned, preflighted fixture manifest, its listed
files, exact JSON Schema, and parser/bootstrap are now active together under
the Readiness 2 admission; the distinct Readiness 3 transaction then activates
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
narrowing, and FTZ/DAZ/subnormal probes. The remaining activation order is
numeric/frame, address, canonical data, diagnostics, and then a distinct
Readiness 3 expected-snapshot/comparison transaction. No later gate or
implementation package beyond the admitted Readiness 2 transaction activates
from this status entry.

Diagnostic compatibility remains Proposed: nine initial domains are
source-admission, dependency, semantic-identity, graph-structure,
frame-numeric, resource, execution-trust, publication, and inspection, with
one tiny mandatory bootstrap registry/profile for unknown registry/profile
negotiation. The exact `ck.diagnostic.r2` candidate codes are documented and
used by the admitted parser/preflight transaction, but the focused diagnostic
owner remains Proposed and no later diagnostic contract is accepted by this
activation. Readiness implementation binding remains a separate scoped
content-identity input from the fixture payload and expected snapshots; the
Readiness 2 binding is active while any Readiness 3 binding remains gated.

The original Batch 13 Double review examined exact target commit
`8c38c501eb1262a1b85af0b8605220625601772f` and produced D1–D3/P1–P3; those
were dispositioned in the immediate successor revisions 10/13/12/10. The
earlier-predecessor review examined exact target commit
`763cff22d10f6491a05a28312a25250704543dcf` and produced G1/G2 and T1–T4; its
artifacts are stale for the current revisions. G1/G2 were fixed mechanically,
T1–T3 were resolved, and T4 remains unselected and deferred, requiring Ben's
retained-human disposition before adapter profile/schema activation; it does not
block the current preparatory Rust slices. The immediate-predecessor review examined
exact target `9b96d18b115126ef09e54ad8c6f21749d5559ff6`; its findings were
corrected in the current revisions. The current review examined exact target
`9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`: its governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. The review artifacts remain preserved evidence;
DR-0002, DR-0006, DR-0008, DR-0011, and DR-0012 remain Proposed with Owner
approval Pending. DR-0013 Revision 12 is Accepted with Owner approval Approved by Ben.
Readiness 1 is triggered/active for the Cargo workspace, compiler/core library
shell, and thin CLI shell. The exact schema, manifest, nine fixtures,
parser/bootstrap, and preflight are the active Readiness 2 transaction after
the merged-commit identity recomputation; the later resolver, adapter,
experiment, and geometry gates are inactive.

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
15, DR-0012 Revision 14, and DR-0013 Revision 12 current. DR-0006, DR-0011,
and DR-0012 remain Proposed with Owner approval Pending and Review Complete after the current
Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. Prior Batch 13 review evidence is stale for
these revisions; G1/G2 were fixed mechanically, T1–T3 were resolved, and T4
remains unselected and deferred, requiring Ben's retained-human disposition
before adapter profile/schema activation; it does not block the current Rust
implementation slice. DR-0013 Readiness 1 is triggered/active for the Cargo workspace,
compiler/core library shell, and thin CLI shell. The exact schema, manifest,
nine fixtures, parser/bootstrap, and preflight are the active Readiness 2
transaction under the admission record; the distinct Readiness 3
resolver/snapshot transaction is not active.
DR-0002 Revision 11 and DR-0008 Revision 11 are unchanged and remain Review
Complete. Owner approval remains Pending.

The immediate next action is bounded source preparation and provenance
traversal over admitted records, grounded in the active parser/bootstrap and
admitted schema/manifest/fixture transaction. Readiness 1 and Readiness 2
remain active while Readiness 3 and later transactions remain gated. The
prepared-source command is developer-facing preparatory inspection, not a
human-visible creature result or retained-human checkpoint. PR #14 may merge
as preparatory tooling after its normal checks pass. The next retained-human
checkpoint is an actual rendered creature or primitive spatial preview, or a
genuine direction-setting decision.
The main thread will autonomously resolve technical correctness findings or
record evidence-dependent triggers under the DR-0001 Revision 6 transition
direction; only a retained-human product, architecture-boundary, material
trade-off, or external-impact finding returns to Ben. No proposal is silently
accepted. No later implementation/readiness gate activates while its owning
records remain Proposed.
Earlier Batch 8/9 and other
review artifacts remain preserved as stale historical evidence.
Do not activate the Readiness 3 resolver, adapters, or geometry work while
their successor admission, content-identity, and other prerequisites remain
pending.

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
the accepted Rust/Cargo platform remains bounded to the active Readiness 1
workspace/compiler-core/thin-CLI shell boundary; the provisional structural
slice does not activate Readiness 3.
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
  fixture-admission proposals establish the four Proposed specification families. The exact Readiness 2
  schema, manifest, nine fixtures, Rust parser/bootstrap, and Python preflight
  are active under the Readiness 2 admission record; later resolver behavior and
  compiler-consumed Readiness 3 fixtures remain unactivated. The separate
  Readiness 1 Cargo shell is active. The current six-record set is DR-0002
  Revision 11, DR-0006 Revision 12, DR-0008 Revision 11, DR-0011 Revision 15,
  DR-0012 Revision 14, and DR-0013 Revision 12. DR-0002/0008 remain Proposed
  with Owner approval Pending and Review Complete; DR-0006, DR-0011, and
  DR-0012 remain Proposed with Owner approval Pending and Review Complete after
  the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. Prior Batch
  13 review evidence is stale historical evidence; G1/G2 were fixed
  mechanically, T1–T3 were resolved, and T4 remains unselected and deferred,
  requiring Ben's retained-human disposition before adapter profile/schema
  activation; it does not block the current preparatory Rust slices. The immediate-predecessor 9b96d18 review is stale; its findings were corrected. The 9c governance pass corrected two mechanical history-label issues and its technical pass found no findings / Ready for PR at High confidence.
  The completed Batch 9 Double review targeted
  `6cf17270fda2827756c24a8d0fb301bef358f` and is stale for the revised records;
  it is evidence, not acceptance.
  See [Current review and future activation obligations](#current-review-and-future-activation-obligations).
  It does not
  depend on CK-KICK-011.
- CK-KICK-013 is active with its accepted Rust-first/Cargo platform boundary
  and Readiness 1 shell trigger. DR-0013 Revision 12 has Owner approval
  Approved by Ben and Review Complete after the current Double review at exact
  target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; prior Batch 13 review evidence is stale historical evidence, G1/G2 were
  fixed mechanically, T1–T3 were resolved, and T4 remains unselected and
deferred, requiring Ben's retained-human disposition before adapter
profile/schema activation; it does not block the current Rust implementation
slice. Readiness 1 is triggered/active for the Cargo workspace, compiler/core
library shell, and thin CLI shell; the provisional structural address/index,
validator, and inspection command remain preparatory. The immediate-predecessor
9b96d18 review is stale; its findings were corrected. Its later readiness stages gate
  shell, parser/bootstrap+fixtures, semantic resolver/in-memory snapshot, and exploratory geometry respectively. The disposable Python
  discovery host remains distinct from the accepted production platform.

## Active work

- The selected Single independent implementation review of CK-KICK-010 and
  its evidence boundary is complete; findings and dispositions are recorded in
  `RESULTS.md`. Main consolidated validation passed after the corrections; no
  second review or review-until-clean pass was run. This does not reopen
  DR-0009/0010.
- Keep CK-KICK-012's active semantic, fixture-admission, numeric, claim-identity,
  adapter, and compatibility work bounded and retain the current 9c Review
  Complete evidence after the immediate-predecessor technical resolutions. The
  Readiness 2 parser/bootstrap and admitted schema/manifest/fixture transaction
  are active; the Proposed body-graph, build-operation, numeric/frame, and
  compatibility documents do not activate Readiness 3 or later packages.
- Keep CK-KICK-013's implemented Readiness 1 boundary at the Cargo workspace,
  compiler/core library shell, and thin CLI shell, with the admitted Readiness 2
  parser/bootstrap transaction active alongside it. The provisional structural
  address/index, validator, and `inspect-structure` command are preparatory and
  do not activate Readiness 3. Advance bounded source preparation, including
  document-wide resolver preparation/provenance traversal. The
  `inspect-prepared-source` command and its bounded browser flow are
  developer-facing preparatory inspection, not a human-visible creature result
  or retained-human checkpoint. PR #14 may merge as preparatory tooling after
  its normal checks pass. The public single-source
  preparation operation and internal numeric/frame-preparation helpers stay
  preparatory, with no record-level admission bypass. Numeric/frame/output,
  adapter, and geometry prerequisites gate later stages. Any performance claim must have
  reproducible benchmark and hardware-profile evidence.
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
  Accepted, Owner approval Approved by Ben, Date decided 2026-08-13, Review Complete
  after the current Double review at exact target
  `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`; Readiness 1 is triggered/active.
- [DR-0009](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
  and [DR-0010](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
  are parked as described in [Current activation state](#current-activation-state).

## Implementation status

| Capability | Implementation | Verification | Notes |
| --- | --- | --- | --- |
| Documentation authority | partial | unverified | Operational structure under Accepted DR-0001 Revision 5 |
| Decision-record and review workflow | partial | unverified | Governance accepted; technical/product proposals remain provisional |
| Research/experiment workflow | partial | unverified | Lightweight template exists; no experiment registered |
| Body specification | partial | unverified | Proposed body-document, body-graph, build-operation, fixture-manifest, and Batch 11/12/13 focused profiles include discussion-approved updates; the Readiness 2 schema, manifest, nine fixtures, parser/bootstrap, and preflight are active under the admission record, while DR-0002/0008 remain Revision 11 Review Complete, DR-0006 Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14 remain Proposed with Owner approval Pending |
| Build-operation contract | partial | unverified | Proposed canonical public build/output owner exists; serialization, implementation, and artifact store remain unactivated |
| Production implementation platform | partial | proven | CK-KICK-013/DR-0013 Revision 12 is Accepted with Owner approval Approved by Ben; the Readiness 1 Cargo workspace, compiler/core library shell, and thin CLI shell pass pinned-toolchain checks. Readiness 2's exact schema, manifest, nine fixtures, parser/bootstrap, and preflight are active after merged commit `766992ab089687e9b1496574e8ffa721388d96f3` / PR #6 and successful post-merge identity recomputation. PR #9, the inspectable biped structure workflow, is merged at `565c32bd35215e23d737fb333604382d3e6958ab`; its structural index/validator/inspection remain preparatory. The public single-source preparation operation and internal numeric/frame-preparation helpers remain preparatory; helpers cannot bypass body-document admission, and distinct Readiness 3, adapter, and exploratory geometry remain gated |
| Creature compiler | partial | unverified | Disposable CK-KICK-010 walking skeleton implemented; this is not a production compiler |
| CK-KICK-010 walking skeleton | implemented | audited | Valid/invalid local evidence and the selected Single independent review are complete; five substantive findings plus whitespace were dispositioned in RESULTS, not clean; this is not a production compiler |
| Local visual-review gallery | implemented | audited | Focused tests and local HTTP/browser smoke passed; subject_context is presentation-only; no visual-evidence or Stage 1 claim |
| Runtime avatar | not-implemented | not-applicable | No runtime adapter selected |

## Immediate next actions

Ben authorized an autonomous runway on 2026-08-15 for small, internal,
reversible preparation PRs. PR #14 is eligible to merge as preparatory tooling
after its normal checks pass. The main thread may merge clean internal bridge
and document-wide preparation/provenance slices along the named runway, but
this is not blanket authority outside it and does not waive real user-visible
or direction-setting decisions. The next retained-human checkpoint is an
actual rendered creature or primitive spatial preview, or a genuine
direction-setting decision. Earlier permission to merge a specific PR does not
authorize merging later PRs outside this recorded runway.

- Use the active Readiness 2 parser/bootstrap and admitted schema, manifest, and
  fixture transaction as the implementation foundation; take bounded
  document-wide resolver preparation/provenance traversal and successor
  evidence. Keep adapters, geometry, and later packages gated.
- Keep Readiness 1 limited to the Cargo workspace, compiler/core library shell,
  and thin CLI shell. Keep the provisional structural address/index, validator,
  and `inspect-structure` command outside the formal Readiness 3 activation
  boundary; Readiness 2 remains active within its recorded
  parser/bootstrap/schema/manifest/fixture boundary.
- Leave DR-0009/0010 parked unless the activation trigger occurs or Ben
  explicitly reactivates them.

## Explicitly not started

- Later implementation packages beyond the active Readiness 2
  parser/bootstrap/schema/manifest/fixture transaction.
- Large asset or dataset storage.
- External mesh conformance.
- Production distribution, operations, or release automation.

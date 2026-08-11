# Decision record registry

Status: Operational under Accepted DR-0001 Revision 5

| ID | Title | Scope | Status | Revision | Review | Decision owner |
| --- | --- | --- | --- | --- | --- | --- |
| [DR-0001](DR-0001-documentation-authority-and-review-process.md) | Documentation authority and decision-record process | Governance | Accepted | 5 | Complete | Ben |
| [DR-0002](DR-0002-declarative-body-document-source-of-truth.md) | Authoritative semantic source set and resolved body graph | Specification and architecture | Proposed | 9 | Complete | Ben |
| [DR-0003](DR-0003-real-time-first-compiled-avatar-boundary.md) | Compiled avatar and bounded real-time execution | Product and architecture | Proposed | 2 | Complete | Ben |
| [DR-0004](DR-0004-external-automation-through-cli-and-api.md) | Shared deterministic domain operations for external automation | Product and architecture | Proposed | 2 | Complete | Ben |
| [DR-0005](DR-0005-initial-product-boundary-and-reference-workflow.md) | Initial product boundary and reference workflow | Product and architecture | Proposed | 1 | Complete | Ben |
| [DR-0006](DR-0006-durable-semantic-and-artifact-identity.md) | Durable semantic and artifact/build identity | Specification and architecture | Proposed | 4 | Complete | Ben |
| [DR-0007](DR-0007-staged-first-proof-charter.md) | Staged first-proof charter and claim boundaries | Product | Proposed | 2 | Complete | Ben |
| [DR-0008](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md) | First digitigrade morphology and Stage 1 embodiment envelope | Product, Specification and architecture | Proposed | 9 | Complete | Ben |
| [DR-0009](DR-0009-hybrid-surface-generation-experiment-hypothesis.md) | Hybrid surface-generation experiment hypothesis | Architecture | Proposed | 8 | Complete | Ben |
| [DR-0010](DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md) | Stage 1 surface extraction and semantic-field propagation | Specification and architecture | Proposed | 8 | Pending | Ben |
| [DR-0011](DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md) | Minimal semantic vocabulary, measurements, and frames | Specification and architecture | Proposed | 5 | Complete | Ben |
| [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md) | Initial body-document encoding, resolution, and compatibility | Specification and architecture | Proposed | 4 | Complete | Ben |
| [DR-0013](DR-0013-first-production-implementation-platform-and-geometry-boundary.md) | First production implementation platform and geometry boundary | Architecture | Proposed | 2 | Complete | Ben |

DR-0001 Revision 5 is `Accepted` after Ben's approval and its Complete clean
review; that disposition applies only to this Governance DR. DR-0002 through
DR-0013 remain `Proposed` technical or product material unless their rows state
otherwise. DR-0009 Revision 8 remains `Proposed` with owner approval `Pending`
and review `Complete`; both current-review artifacts recommend `Revise` at
High confidence. DR-0010 Revision 8 remains `Proposed` with owner approval
`Pending` and review `Pending`; exactly two geometry/semantic findings are
preserved. Review evidence records neither acceptance nor a clean review.

Ben settled CK-KICK-012 Batch 1 selections on 2026-08-09 and approved the seven
Batch 3 decisions in discussion on 2026-08-11. On 2026-08-11 he also approved
the Batch 4 resolutions recorded in DR-0002 Revision 6, DR-0008 Revision 6,
DR-0011 Revision 2, and new DR-0012 Revision 1. He then approved the Batch 5
blocker-resolution selections recorded in DR-0002 Revision 7, DR-0008
Revision 7, DR-0011 Revision 3, and DR-0012 Revision 2, followed by the Batch 6
review-finding resolutions now recorded in DR-0002 Revision 9, DR-0008
Revision 9, DR-0011 Revision 5, DR-0012 Revision 4, and DR-0013 Revision 2.
Those discussion approvals are distinct from later DR acceptance. All five
current revisions remain Proposed with owner approval Pending and Review
Complete. The current-revision Double review of each record examined target
commit `88004388f9537a37617ae248bdaad4625e6f3f03`; both independent passes
recommend Revise at High confidence. Review Complete records evidence, not a
clean review or acceptance. The exact-revision Batch 5 Double review at commit
`a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical evidence; its
three findings motivated and are resolved in the Batch 6 proposal text. The
exact-revision Batch 6 Double review at commit
`c64b1b98948304d631eecea6a354c9e42c89c510` is also stale historical evidence
after these proposal revisions; its ten artifacts remain preserved evidence,
not a clean review and not acceptance. The ten current-review artifacts are
linked from each DR's adversarial-review response below. Their selected status/primary-diagnostic,
containment, Attachment/frame, hostile-input, platform, geometry-seam,
artifact, worker, and reproducibility rules are split across the owning
records. Exact field spellings, diagnostic codes, numeric
thresholds/tolerances, canonical axes/units/rotation/scale/shear, canonical
bytes/hashing, dependency-revision semantics, and fixture evidence remain
later obligations. DR-0013's platform and geometry choices do not activate
implementation packages or a permanent later backend while it remains
Proposed.
DR-0006 Revision 4 remains unchanged, Proposed with owner approval Pending and
Review Complete. Exact dependency-revision meaning, exact source fields,
diagnostic codes, concrete resource values, canonical axes/units/rotation/
scale/shear, canonical bytes, and the cross-DR fixture matrix remain later
obligations. Review Complete records evidence, not acceptance or a clean review;
CK-KICK-012 remains active.

DR-0009 Revision 8 and DR-0010 Revision 8 are plan-state `deferred` (parked)
and non-blocking. No Revision 9, further review, owner disposition, or finding
discussion is active. Reactivate them only when at least two runnable candidate
surface implementations exist and a comparative outcome is intended to justify
or select production architecture, or when Ben explicitly reactivates them.
Until then, exploratory prototypes may record observations but may not claim
formal DR-0009/0010 support or reject. The detailed records, review artifacts,
and first-surface design remain preserved. The [project status](../project/status.md)
is the canonical owner of this current activation state.

## CK-KICK-012 Batch 6 prior Double review (stale after proposal revisions)

The prior exact-revision Double review examined target commit
`c64b1b98948304d631eecea6a354c9e42c89c510`. It was Complete evidence for
DR-0002 Revision 8, DR-0008 Revision 8, DR-0011 Revision 4, DR-0012 Revision 3,
and DR-0013 Revision 1; after the approved revisions it is stale historical
evidence. Both independent passes for every record recommended **Revise**.
Recommendations were **High** confidence except DR-0012 review 02, which was
**Medium** confidence. The ten preserved review artifacts are linked here:
[DR-0002 review 01](reviews/DR-0002-rev-08-review-01.md), [DR-0002 review 02](reviews/DR-0002-rev-08-review-02.md),
[DR-0008 review 01](reviews/DR-0008-rev-08-review-01.md), [DR-0008 review 02](reviews/DR-0008-rev-08-review-02.md),
[DR-0011 review 01](reviews/DR-0011-rev-04-review-01.md), [DR-0011 review 02](reviews/DR-0011-rev-04-review-02.md),
[DR-0012 review 01](reviews/DR-0012-rev-03-review-01.md), [DR-0012 review 02](reviews/DR-0012-rev-03-review-02.md),
[DR-0013 review 01](reviews/DR-0013-rev-01-review-01.md), and [DR-0013 review 02](reviews/DR-0013-rev-01-review-02.md).
These artifacts and the seven findings below are stale historical evidence,
not acceptance or a clean review. Ben approved the seven resolutions in
discussion on 2026-08-11 and they are recorded in the five new proposed
revisions above. The current-revision Double review is Complete evidence with
five findings pending Ben discussion and owner disposition; prior reviews
remain stale historical evidence.

The seven consolidated discussion findings are:

1. **F1 — High — total status algebra and completeness (resolution recorded).**
   Global internal trust loss dominates; a configured resource breach is
   resource-limit only when it prevents required processing/trusted completion;
   otherwise the earliest unable phase determines status. Complete acquisition
   is required before invalid-source, parse/semantic invalid-source outranks
   unsupported, dependency outcomes are mapped, and processing/diagnostic
   completeness are independently observable.
2. **F2 — High — typed Attachment transform (resolution recorded).**
   `T_A←B`, H/R/M, `S_h`/`S_m`, `O_(S_h←S_m)`, and the conceptual host-local
   equation are now defined; matrix and serialization details remain deferred.
3. **F3 — High overall (one reviewer Medium) — mating Socket capacity and
   reuse (resolution recorded).** Each present mating Socket has capacity one;
   reuse by distinct active Attachments, including distinct hosts or nested
   roots, is invalid with a distinct deterministic diagnostic concept.
4. **F4 — High — activation trigger (resolution recorded).** Acceptance of
   DR-0013 alone triggers the Cargo workspace and empty/compiler shell boundary;
   exact schema and admitted fixtures/contracts still gate Stage 1 parser/resolver work.
5. **F5 — High — replaceable geometry seam (resolution recorded).** A
   project-owned versioned GeometryRequest/GeometryResult conceptual seam is
   backend-neutral, carries bounded metadata/diagnostics/outputs and lineage,
   and does not establish a permanent surface/backend or DR-0009/0010 evidence.
6. **F6 — High — artifact/workbench and worker boundary (resolution recorded).**
   Immutable sibling staging, manifest-last atomic no-replace publication,
   identity/path/hash/size validation, incomplete/mixed/stale rejection, and
   future worker negotiation, bounded failure mapping, output validation, and
   compiler survival are required; detailed serialization remains deferred.
7. **F7 — Medium — reproducible Rust/platform baseline (resolution recorded).**
   Exact rust-toolchain.toml, committed Cargo.lock, target/profile/rustc/reference
   metadata, one WSL2/native-Linux x86_64 GNU path first, later portability
   smoke, lightweight dependency review, and broadened isolation/security/
   portability/licensing triggers are required without heavyweight process.

Affected records are DR-0002: F1–F3; DR-0008: F2–F3; DR-0011: F2–F3;
DR-0012: F1–F3; and DR-0013: F4–F7. These are discussion-approved proposal
resolutions, not owner acceptance; current-revision review is Complete and its
findings remain pending Ben discussion and owner disposition.

## CK-KICK-012/013 current Double review (Complete evidence; owner disposition pending)

The current-revision Double review examined target commit
`88004388f9537a37617ae248bdaad4625e6f3f03`. Both independent passes for each
of DR-0002, DR-0008, DR-0011, DR-0012, and DR-0013 recommend **Revise** at
**High** confidence. Review Complete means that evidence exists; it does not
mean the review was clean or that any DR is accepted. The findings below await
Ben discussion and owner disposition. The prior `c64b1b...` reviews remain
stale historical evidence.

1. **High — operation status/completeness remains non-total.** Mixed
   dependency-phase outcomes lack a tie-break; independent-check continuation
   and early-stop behaviour is undefined; processing completeness for normal
   fatal outcomes is ambiguous; and CK-PROD-033 conflicts with the ordinary
   diagnostic-truncation exception.
2. **High — module/Socket cardinality is not fully observable.** Total-vs-
   per-role cross-role Socket reuse is undefined, and a present module root
   requiring Attachment is not independently declared when the Attachment is
   missing.
3. **Medium overall but contract-blocking — Attachment inversion.** A current
   invertible/non-degenerate transform invariant and deterministic source-failure
   mapping are missing.
4. **High — implementation activation remains circular/underspecified.**
   Distinguish the Cargo shell; parser/bootstrap with an exact schema and frozen
   admitted fixture manifest; semantic resolver/snapshot numeric-frame
   prerequisites; and geometry/Stage 1 proof. Accepted or parked surface work
   must not circularly gate semantic implementation.
5. **High — compiler/geometry/worker/publication outcome authority is
   incomplete.** A publication failure cannot publish its own complete failure
   bundle. Define authoritative envelope layering, optional artifact identity,
   no-final-bundle publication failure, and normalized backend/worker outcomes.

These are pending decision-bearing findings, not additional current proposal
fixes. Before isolated worker activation, define containment, process-tree,
output/log/handle/network/protocol/cleanup/status bounds appropriate to the
threat model. Before evidence-bearing portability or performance claims, freeze
the lightweight exact build/reference environment and dependency source/feature
inputs; native smoke precedes native portability claims.

## Candidate decisions

Remaining candidates do not yet have reserved DR numbers. The first production
platform proposal is recorded in DR-0013; its later geometry backend remains
conditional and unaccepted.

| Candidate | Trigger for proposal |
| --- | --- |
| Production surface and topology architecture | After surface evidence and before a production commitment |
| Later geometry backend or worker boundary | If reproducible measurements or a required capability expose a credible gap in the proposed first in-process Rust geometry proof; evaluate an isolated C++ worker/backend first |
| First runtime engine and adapter boundary | Before a runtime integration proof |
| Avatar package serialization | Before persisting compiled avatars |
| Determinism and replay level | Before defining runtime state contracts |
| Artifact storage | Before committing or publishing large generated assets |
| Project licence | Before accepting external contributions or distribution |

# Decision record registry

Status: Operational under Accepted DR-0001 Revision 5

| ID | Title | Scope | Status | Revision | Review | Decision owner |
| --- | --- | --- | --- | --- | --- | --- |
| [DR-0001](DR-0001-documentation-authority-and-review-process.md) | Documentation authority and decision-record process | Governance | Accepted | 5 | Complete | Ben |
| [DR-0002](DR-0002-declarative-body-document-source-of-truth.md) | Authoritative semantic source set and resolved body graph | Specification and architecture | Proposed | 8 | Complete | Ben |
| [DR-0003](DR-0003-real-time-first-compiled-avatar-boundary.md) | Compiled avatar and bounded real-time execution | Product and architecture | Proposed | 2 | Complete | Ben |
| [DR-0004](DR-0004-external-automation-through-cli-and-api.md) | Shared deterministic domain operations for external automation | Product and architecture | Proposed | 2 | Complete | Ben |
| [DR-0005](DR-0005-initial-product-boundary-and-reference-workflow.md) | Initial product boundary and reference workflow | Product and architecture | Proposed | 1 | Complete | Ben |
| [DR-0006](DR-0006-durable-semantic-and-artifact-identity.md) | Durable semantic and artifact/build identity | Specification and architecture | Proposed | 4 | Complete | Ben |
| [DR-0007](DR-0007-staged-first-proof-charter.md) | Staged first-proof charter and claim boundaries | Product | Proposed | 2 | Complete | Ben |
| [DR-0008](DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md) | First digitigrade morphology and Stage 1 embodiment envelope | Product, Specification and architecture | Proposed | 8 | Complete | Ben |
| [DR-0009](DR-0009-hybrid-surface-generation-experiment-hypothesis.md) | Hybrid surface-generation experiment hypothesis | Architecture | Proposed | 8 | Complete | Ben |
| [DR-0010](DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md) | Stage 1 surface extraction and semantic-field propagation | Specification and architecture | Proposed | 8 | Pending | Ben |
| [DR-0011](DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md) | Minimal semantic vocabulary, measurements, and frames | Specification and architecture | Proposed | 4 | Complete | Ben |
| [DR-0012](DR-0012-initial-body-document-encoding-resolution-and-compatibility.md) | Initial body-document encoding, resolution, and compatibility | Specification and architecture | Proposed | 3 | Complete | Ben |
| [DR-0013](DR-0013-first-production-implementation-platform-and-geometry-boundary.md) | First production implementation platform and geometry boundary | Architecture | Proposed | 1 | Complete | Ben |

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
review-finding resolutions recorded in DR-0002 Revision 8, DR-0008 Revision 8,
DR-0011 Revision 4, and DR-0012 Revision 3. Those discussion approvals are
distinct from later DR acceptance. The four CK-KICK-012 current revisions
remain Proposed with owner approval Pending and Review Complete. The exact-
revision Batch 5 Double review at commit
`a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical evidence; its
three findings motivated and are resolved in the Batch 6 proposal text. The
current-revision Double review examined commit
`c64b1b98948304d631eecea6a354c9e42c89c510` and is complete evidence, not clean
and not acceptance. Their selected status/primary-diagnostic, containment, Attachment/frame, and
hostile-input rules are split across the owning records. Exact field spellings,
diagnostic codes, numeric thresholds/tolerances, canonical
axes/units/rotation/scale/shear, canonical bytes/hashing, dependency-revision
semantics, and fixture evidence remain later obligations. DR-0013 is likewise
Proposed with owner approval Pending and Review Complete; its platform and
geometry choices do not activate implementation packages or a permanent later
backend.
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

## CK-KICK-012 Batch 6 current Double review

The current-revision Double review examined exact target commit
`c64b1b98948304d631eecea6a354c9e42c89c510`. Review status is Complete for
DR-0002 Revision 8, DR-0008 Revision 8, DR-0011 Revision 4, DR-0012 Revision 3,
and DR-0013 Revision 1. Both independent passes for every record recommend
**Revise**. Recommendations are **High** confidence except DR-0012 review 02,
which is **Medium** confidence. The ten expected review artifacts are linked
here: [DR-0002 review 01](reviews/DR-0002-rev-08-review-01.md), [DR-0002 review 02](reviews/DR-0002-rev-08-review-02.md),
[DR-0008 review 01](reviews/DR-0008-rev-08-review-01.md), [DR-0008 review 02](reviews/DR-0008-rev-08-review-02.md),
[DR-0011 review 01](reviews/DR-0011-rev-04-review-01.md), [DR-0011 review 02](reviews/DR-0011-rev-04-review-02.md),
[DR-0012 review 01](reviews/DR-0012-rev-03-review-01.md), [DR-0012 review 02](reviews/DR-0012-rev-03-review-02.md),
[DR-0013 review 01](reviews/DR-0013-rev-01-review-01.md), and [DR-0013 review 02](reviews/DR-0013-rev-01-review-02.md).
These artifacts and the seven findings below are evidence pending Ben
discussion and owner disposition, not acceptance or a clean review. Prior
reviews remain stale historical evidence.

The seven consolidated discussion findings are:

1. **F1 — High — non-total status algebra and completeness.** Status algebra,
   completeness, and truncation remain non-total across phase 1 invalid-source
   versus input-failure, ordinary truncation versus resource-limit, and
   independent processing/diagnostic completeness.
2. **F2 — High — Attachment transform meaning.** Attachment needs typed
   from-to transform meanings, offset basis and order, and a conceptual
   host-local equation.
3. **F3 — High overall (one reviewer Medium) — active mating Socket reuse.**
   Active mating Socket reuse/capacity is unclassified for distinct hosts and
   nested roots.
4. **F4 — High — circular activation trigger.** DR-0013's activation trigger
   is circular and unnamed.
5. **F5 — High — replaceable geometry seam.** The seam lacks a backend-neutral
   request/result/diagnostic/lineage/capability and anti-leakage minimum; it
   must not become a permanent surface or implicitly create DR-0009/0010
   evidence.
6. **F6 — High — artifact/workbench and worker failure boundary.** The future
   artifact/workbench and worker boundary needs coherent atomic/manifest-last
   publication, identity/integrity/path/resource validation, and crash,
   timeout, and output handling.
7. **F7 — Medium — reproducible Rust/platform baseline.** The reproducible
   Rust/platform/dependency baseline is incomplete: toolchain/lock/MSRV-target/
   reference environment, license/security/unsafe-native policy, and isolation
   trigger scope remain unspecified.

Affected records are DR-0002: F1–F3; DR-0008: F2–F3; DR-0011: F2–F3;
DR-0012: F1–F3; and DR-0013: F4–F7. No finding is resolved by this metadata
recording.

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

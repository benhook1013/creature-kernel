# Product documentation

Status: Proposed product authority

This directory owns Creature Kernel's intended outcomes, scope, users, and
externally observable requirements. It must not embed implementation choices
unless the choice itself is a product constraint.

## Documents

- [Vision and scope](vision-and-scope.md)
- [Requirements](requirements.md)
- [Users and workflows](users-and-workflows.md)
- Batch 11/12 focused contract owners: [semantic-address](../../spec/semantic-address/README.md),
  [canonical-data](../../spec/canonical-data/README.md),
  [numeric-frame-profile](../../spec/numeric-frame-profile/README.md), and
  [diagnostics](../../spec/diagnostics/README.md).

Product documents outrank architecture when defining what the project is trying
to accomplish. Architecture determines how to satisfy those outcomes and must
surface conflicts rather than quietly weakening them. The current product
content is a proposed, assistant-synthesized baseline pending governance and
product review; it is not an accepted project contract.

The four Round 2 initial-boundary choices are recorded in
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md):
engine-independent compiler/runtime identity, the developer/researcher-first
workflow, stylized creature and demanding interaction/deformation stress cases
with general mechanisms, and native generation before external-mesh
conformance. They remain
proposals recorded under DR-0005.

DR-0005 preserves the proposal's original motivation and review context. The
product documents in this directory own the current neutral public-facing
framing; the decision record does not override them.

The accepted semantic-foundation directions are recorded in
[DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
and [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
Related Proposed product boundaries are recorded in
[DR-0004 Revision 2](../decisions/DR-0004-external-automation-through-cli-and-api.md)
and [DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md).
The canonical specification owners are the [body-document](../../spec/body-document/README.md),
[body-graph](../../spec/body-graph/README.md), [build-operation](../../spec/build-operation/README.md),
and [fixture-manifest](../../spec/fixture-manifest/README.md) contracts.

Prior CK-KICK-012 revisions and review artifacts remain preserved as historical
evidence. Ben's Batch 5, Batch 8, Batch 9, Batch 10, Batch 11, Batch 12, and
Batch 13 resolutions are discussion-approved and incorporated here as Proposed
product outcomes only. Accepted DR-0001 Revision 5 remains the operative
governance baseline while DR-0001 Revision 6 is Proposed transition guidance
with Ben's workflow direction approved and current review complete; formal
acceptance remains pending Ben's disposition. DR-0002 Revision 11, DR-0006
Revision 12, DR-0011 Revision 15, and DR-0012 Revision 14 are accepted
semantic-foundation directions with Owner approval Approved by Ben and Review
Complete, decided 2026-08-17; their concrete product, specification, profile,
and activation consequences remain Proposed or gated. DR-0013 Revision 12 is Accepted,
with Owner approval Approved by Ben and Review Complete at that exact target,
decided 2026-08-13. The reviews of the earlier
predecessor revisions at commit `763cff22d10f6491a05a28312a25250704543dcf`
are stale exact-target evidence; the immediate-predecessor review at exact
commit `9b96d18b115126ef09e54ad8c6f21749d5559ff6` is also stale, with its
findings corrected in these revisions. The 9c governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. Review Complete is evidence only;
G1/G2 were fixed mechanically, T1–T3 were resolved in the successors, and
T4 remains unselected and deferred, requiring Ben's retained-human disposition
before adapter profile/schema activation; it does not block the empty first Rust
slice. Review evidence is not acceptance. DR-0013's accepted platform boundary
does not accept these Proposed product contracts. Readiness 1 remains active
for the Cargo workspace, empty `creature-kernel-core` library shell, and thin
`creature-kernel` CLI shell. Readiness 2 is also active for the admitted exact body
and manifest schemas, manifest, nine fixtures, Rust parser/bootstrap,
and Python preflight/evidence. No Readiness 3 resolver, numeric semantic
activation, adapter, experiment, or Readiness 3 geometry implementation exists.
Recommendations and the next discussion are summarized in the [current review
state](../project/status.md#current-review-and-future-activation-obligations).
The cross-cutting semantic-foundation direction is [DR-0012:
initial body-document encoding, resolution, and compatibility](../decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).
This documentation records intended product outcomes; exact syntax details,
machine schema, exact numeric bounds, and implementation mechanisms remain
deferred to their owning specifications and architecture work. Batch 13 keeps
the typed machine-address, canonical-data, and diagnostic owners separate and
proposes: direct same-target comparison in one canonical local-to-parent frame;
exact dyadic scalar predicates; deterministic normalization and precomputed
half-chord bounds with no runtime transcendental comparison; structured stable
claim IDs, sorted pair evaluation, and smallest-tuple selection; and a graph
collection key distinct from local claim multiplicity. The unregistered
experiment must verify rational/ULP boundaries, offline H derivation, bounded
platform normalization fixtures, and order/identity fixtures. Future adapters
use signed permutation `C` plus positive scale `s` (vector lengths use `sC`,
scalar lengths use `s`), with storage/output-only
and optional runtime-conformance tiers, explicit precision/domain narrowing,
and FTZ/DAZ/subnormal probes. Diagnostic compatibility remains a separate
Proposed owner with nine domains—source-admission, dependency, semantic-
identity, graph-structure, frame-numeric, resource, execution-trust,
publication, and inspection—and one mandatory tiny bootstrap registry/profile;
exact codes/fields remain fixture-gated. Concrete diagnostic/profile IDs,
constants, resolver, and adapter bindings remain Proposed or gated; the
admitted Readiness 2 transaction does not activate Readiness 3.
Readiness implementation binding remains a separate scoped content-identity
transaction from the fixture payload and expected snapshots; no implementation
binding is implied here.

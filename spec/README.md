# Normative specifications

Status: Active Proposed authority boundary; the body-document, body-graph,
build-operation, and fixture-manifest contracts include discussion-approved
CK-KICK-012 Batch 10 material, but no format is accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

The current semantic proposal set is represented by [DR-0002](../docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
Their prior revisions and reviews remain preserved as historical evidence.
DR-0002 Revision 11 and DR-0008 Revision 11 remain Proposed with Owner approval
Pending and Review Complete. DR-0006 Revision 7, DR-0011 Revision 9, DR-0012
Revision 8, and DR-0013 Revision 6 remain Proposed with Owner approval Pending
and Review Pending after Batch 10. The Batch 9 review evidence targeted commit
`6cf17270fda2827756c24a8d0fb301bef358f98f` and is stale for the materially
revised records; Review Complete is evidence, not acceptance. No
implementation or readiness gate activates. See the [current review
state](../docs/project/status.md#current-review-and-future-activation-obligations)
for the mixed review state and findings.
The cross-cutting proposal is
[DR-0012: initial body-document encoding, resolution, and compatibility](../docs/decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).

## Proposed specification families

- [Body-document contract](body-document/README.md): the initial strict UTF-8
  JSON source encoding, ordered bootstrap and exact contract recognition,
  closed operation statuses and precedence, bounded deterministic diagnostics,
  and streaming/token-aware finite resource rules. It does not choose
  serialized field names or provide a machine schema file.
- [Resolved body-graph contract](body-graph/README.md): typed concepts,
  durable semantic identity, explicit Part containment and transform
  inheritance, directed joints with owner-specific frame records,
  contextual host/mating Socket Attachment placement, provenance, Stage 1
  invariants, and successful in-memory snapshot handoff conditions.
- [Fixture-manifest and admission contract](fixture-manifest/README.md): the
  conceptual fixture-suite payload, external readiness/decision binding,
  preflight, successor/rollback, manifest field groups, and readiness corpus
  admission boundary. It does not activate a schema, parser, or fixture file.
- [Build-operation and derived-output contract](build-operation/README.md):
  the Proposed public build envelope, in-memory snapshot handoff boundary,
  candidate-to-committed artifact identity lifecycle, deterministic target and
  collision rules, publication/inspection expectations, worker trust boundary,
  filesystem profile, and separate artifact inspection. It does not define
  final serialization.

These proposed contracts apply a finite implementation profile. Its approved
resource-limit categories are source and aggregate bytes, string
lengths/counts, nesting depth, object/array members, graph entities/relations,
ownership depth, module/reference expansion, extension count/payload, numeric
admissibility, diagnostics, and aggregate work/memory. Exact profile values and
accounting remain unselected.

- Authoritative semantic source set (the sole authored authority; initially
  potentially one human-readable document) with exactly versioned references
  to every outcome-affecting external authored dependency.
- One authoritative operation-result envelope for all phases and diagnostics:
  loading, syntax/schema/contract, dependencies, resources, semantic
  resolution, and invariants. A validated, inspectable, reproducible, per-build
  resolved semantic graph snapshot is required for successful `resolve` and may
  be omitted only when an operation contract such as `validate` permits it;
  persisted snapshot diagnostics are a derived subset.
  Semantically invalid and well-formed-but-unsupported partial graphs are
  non-compilable, non-contractual debug data. The proposed source/resolved
  split is detailed in the [body-document](body-document/README.md) and
  [body-graph](body-graph/README.md) contracts.
  The first public build operation extends this envelope with the trusted
  derived-output/publication status `output-failure`; geometry and publication
  do not create competing status channels.
- Durable semantic identities through structured addresses (source namespace,
  authored module-instance anchors, concept kind, and role-local key), and
  separate artifact/build identity and provenance. Each source namespace has
  one unique owner in a resolved source set; collisions require an authored,
  deterministic, collision-free remapping across every contributed semantic
  address, with no implicit shared ownership. Exact address serialization and
  lifecycle/remap rules remain open.
- Capabilities, regions, attachments, joints, and material/deformation metadata.
- A proposed supported-morphology and validity envelope for the bounded first
  digitigrade biped family. Its identity-bearing concepts are exactly Part,
  Joint, Socket, Attachment, Region, Capability, and Field. Module is authored
  reusable scope; landmark, anchor, dimension, and frame are typed owner+role
  records. Joint has one proximal and one distal Part; Socket is Part-owned;
  Attachment connects one host and one mating Socket without implying
  articulation. The normalized model declares a stable module-instance
  declaration address plus module/root-role/anchor-provenance,
  presence/optionality, and Attachment requirement without adding an eighth
  graph concept; an absent declaration emits no Part or relation target and is
  distinct from a present-but-unattached root. Every Socket
  has total active capacity one across host and mating roles, so cross-role
  reuse is invalid. Every embodied Part has exactly one explicit containment path
  to the root, including an optional module root; containment supplies
  transform inheritance and is checked independently from relation cycles.
  Stage 1 required Joints connect containment parents to immediate children.
  Attachment placement uses the typed host/mating transform equation in the
  body-graph contract; every transform entering composition is finite,
  non-degenerate, and invertible under the declared profile. A source violation
  is invalid-source and an implementation failure on an admissible transform
  is internal-failure. Readiness 2 fixes the structural rigid-transform carrier
  as exactly three translation components plus four explicit `xyzw` quaternion
  components, with no scale or shear fields; exact matrix/layout serialization,
  canonical numeric semantics, conditioning, and tolerances remain deferred to
  resolver activation. Competing authored placement must agree
  within a later-defined tolerance. The pelvis Part owns the root-reference frame. The axial chain
  is pelvis → spine Joint → torso/chest Part → neck-base Joint → neck Part →
  head-base Joint → head Part. Arm and leg chains use the required typed Joints
  and Parts and end in terminal paw-base landmark/Socket roles. Ear/tail modules
  use Attachment; movable tails also use a Joint. These are not
  bone/solver/rig/anatomy-fidelity requirements. Part-to-Part ownership is the
  sole structural body-containment tree; declarative ownership of other
  concepts and records does not create structural body edges.
  Arbitrary anatomy/user-defined graph kinds are unsupported in the first
  family. The resolver returns a deterministic result envelope: only valid,
  supported input produces a compilable validated snapshot.
- Declared units, handedness, up, and forward; normalization to a
  contract-revision canonical internal basis with conversion provenance; and
  distinct Part-local/reference, Joint proximal/distal, Socket-intrinsic,
  derived resolved world/reference, and runtime-pose frames. Attachment
  host/mating roles are contextual endpoints, not Socket frame roles.
  Transforms own placement, typed dimensions own size/extents,
  anchors/landmarks retain authored or derived provenance, ratios are derived
  only, and conflicting constraints diagnose. Readiness 2 requires a rigid
  carrier with three translation and four explicit `xyzw` quaternion
  components and no scale/shear fields; canonical numeric meaning and
  tolerances remain deferred to Readiness 3. Exact serialized fields and
  machine-schema contents remain deferred;
  strict JSON and JSON Schema Draft 2020-12 are the selected Proposed initial
  encoding and structural-validation technologies.
- A proposed fixture-profile contract describing stable profile identity,
  concrete source inputs, discriminating parameters, seed/configuration,
  provenance, shared-generation expectations, validity/diagnostic status, the
  frozen expected outcome of valid-supported, semantically invalid, or
  well-formed-but-unsupported, plus the primary diagnostic class/code for every
  non-success fixture. Fixture-manifest admission is owned by the
  [fixture-manifest contract](fixture-manifest/README.md), which binds a
  manifest payload to separately recorded reviewed content identities and Ben
  approval, and excludes unlisted fixtures. Only valid-supported fixtures count toward the Stage 1
  gate. Exact fixture definitions must be frozen if the deferred EXP-0001
  protocol is activated before its execution or evidence; selecting hypotheses
  may precede that freeze.
- The [first surface experiment design](../docs/research/first-surface-experiment-design.md)
  is parked, non-blocking confirmatory research. It is not a normative schema,
  does not register EXP-0001, and does not provide evidence until its activation
  trigger is met.
- A proposed staged embodiment contract describing Stage 1 source-linked
  semantic joint frames and semantic region intent/lineage, and the later
  ownership of usable skeletons, skin weights, collision proxies, contact, and
  deformation claims.
- A deferred sampled-field and semantic-lineage direction may later be informed
  by [DR-0010 Revision 8](../docs/decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md).
  Its detailed confirmatory sampling, convergence, and semantic-field rules
  remain in that parked decision record and are not current specification
  requirements. No storage layout or serialization format is selected.
- Runtime avatar package.
- Interaction and quality negotiation.
- Shared domain-operation and diagnostic contracts (eventually).
- Final artifact serialization and artifact inspection details not otherwise
  owned by the [build-operation contract](build-operation/README.md).

The body-document and body-graph contracts own semantic source admission and
resolved graph meaning. The build-operation contract owns the public derived
output and publication boundary; it does not move semantic identity out of
[DR-0006](../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md)
or make filesystem artifacts authored authority.

## Specification obligations

Every accepted format must define:

- purpose and authority;
- normative vocabulary;
- required and optional fields;
- validation and error behaviour;
- ordering and determinism where relevant;
- versioning, compatibility, and migration;
- unknown-field and extension behaviour;
- security and resource limits for untrusted input;
- representative valid and invalid fixtures;
- a machine-readable schema when practical.

Strict JSON and JSON Schema Draft 2020-12 are the Proposed initial encoding and
structural-validation technologies. No exact serialized field vocabulary,
machine-readable schema file, canonical byte representation, canonical hash
serialization, or accepted format exists yet. Canonical serialization and
hashing remain required before identity/build or fixture-manifest activation.

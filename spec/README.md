# Normative specifications

Status: Active authority boundary; proposed body-document and body-graph
contracts are discussion-approved for CK-KICK-012 Batch 5, but no format is
accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

The current semantic proposal set is represented by [DR-0002](../docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
Their prior revisions have complete review evidence. Batch 5 blocker
resolutions are discussion-approved and are represented as Proposed canonical
material here. The current CK-KICK-012 Batch 5 Double review is Complete at
commit `a282dbabffd83afa4e62577086934d00f98e12c7`; DR-0002 Revision 7, DR-0008
Revision 7, DR-0011 Revision 3, and DR-0012 Revision 2 remain Proposed with
Owner approval Pending. Three consolidated findings are pending Ben discussion;
their prior reviews remain preserved as stale historical evidence. DR-0006
remains Proposed with its current revision's review evidence. The cross-cutting
proposal is [DR-0012: initial body-document
encoding, resolution, and compatibility](../docs/decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).

## Proposed specification families

- [Body-document contract](body-document/README.md): the initial strict UTF-8
  JSON source encoding, ordered bootstrap and exact contract recognition,
  closed operation statuses and precedence, bounded deterministic diagnostics,
  and streaming/token-aware finite resource rules. It does not choose
  serialized field names or provide a machine schema file.
- [Resolved body-graph contract](body-graph/README.md): typed concepts,
  durable semantic identity, explicit Part containment and transform
  inheritance, directed joints with canonical local frame records,
  host/mating Socket Attachment placement, provenance, Stage 1 invariants, and
  success-publication rules.

Both proposed contracts apply a finite implementation profile. Its approved
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
  resolved semantic graph snapshot is an optional success payload only for
  valid-supported input; persisted snapshot diagnostics are a derived subset.
  Semantically invalid and well-formed-but-unsupported partial graphs are
  non-compilable, non-contractual debug data. The proposed source/resolved
  split is detailed in the [body-document](body-document/README.md) and
  [body-graph](body-graph/README.md) contracts.
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
  articulation. Every embodied Part has exactly one explicit containment path
  to the root, including an optional module root; containment supplies
  transform inheritance and is checked independently from relation cycles.
  Stage 1 required Joints connect containment parents to immediate children.
  Attachment placement uses host/mating interface frames, optional offset, and
  inverse mating placement; competing authored placement must agree within a
  later-defined tolerance. The pelvis Part owns the root-reference frame. The axial chain
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
  distinct local/reference, joint, socket/mating, derived resolved
  world/reference, and runtime-pose frames. Transforms own placement, typed
  dimensions own size/extents, anchors/landmarks retain authored or derived
  provenance, ratios are derived only, and conflicting constraints diagnose.
  Exact canonical axes, units, rotation, scale, shear, ranges, surface
  primitives, serialized fields, and machine-schema contents remain deferred;
  strict JSON and JSON Schema Draft 2020-12 are the selected Proposed initial
  encoding and structural-validation technologies.
- A proposed fixture-profile contract describing stable profile identity,
  concrete source inputs, discriminating parameters, seed/configuration,
  provenance, shared-generation expectations, validity/diagnostic status, the
  frozen expected outcome of valid-supported, semantically invalid, or
  well-formed-but-unsupported, plus the primary diagnostic class/code for every
  non-success fixture, and
  the distinction between fixture evidence and product claims. Only
  valid-supported fixtures count toward the Stage 1 gate. Exact fixture
  definitions must be frozen if the deferred EXP-0001 protocol is activated
  before its execution or evidence; selecting hypotheses may precede that
  freeze.
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
- Artifact inspection and manifests.

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
machine-readable schema file, canonical byte representation, or accepted
format exists yet.

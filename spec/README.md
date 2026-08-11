# Normative specifications

Status: Active authority boundary; no formats accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

The current semantic proposal set is [DR-0002 Revision 5](../docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006 Revision 4](../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008 Revision 5](../docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011 Revision 1](../docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
All remain Proposed with Owner approval Pending and Review Pending until their
current revisions receive the required Double review.

## Planned specification families

- Authoritative semantic source set (the sole authored authority; initially
  potentially one human-readable document) with exactly versioned references
  to every outcome-affecting external authored dependency.
- One authoritative operation-result envelope for all phases and diagnostics:
  loading, syntax/schema/contract, dependencies, resources, semantic
  resolution, and invariants. A validated, inspectable, reproducible, per-build
  resolved semantic graph snapshot is an optional success payload only for
  valid-supported input; persisted snapshot diagnostics are a derived subset.
  Semantically invalid and well-formed-but-unsupported partial graphs are
  non-compilable, non-contractual debug data.
- Durable semantic identities through structured addresses (source namespace,
  authored module-instance anchors, concept kind, and role-local key), and
  separate artifact/build identity and provenance. Each source namespace has
  one unique owner in a resolved source set; collisions require an authored,
  deterministic, collision-free remapping across every contributed semantic
  address, with no implicit shared ownership. Exact address serialization and
  lifecycle/remap rules remain open.
- Capabilities, regions, attachments, joints, and material/deformation metadata.
- A planned supported-morphology and validity envelope for the bounded first
  digitigrade biped family, including its typed ownership tree and vocabulary:
  Part (structural/owned), Joint (articulation relation/frames, not bone or
  solver), Socket (host interface frame), Attachment (module-to-socket mapping,
  not automatically a joint), Region (overlapping spatial designation, never
  ownership), Capability (queryable affordance, not implementation), and Field
  (spatial semantic intent/channel with lineage, representation-neutral). The
  required articulation is root reference → pelvis → chest → neck → head;
  arms shoulder → elbow → wrist → terminal paw-base; legs hip → knee → one
  hock/ankle articulation → terminal paw-base; and a present tail has a
  tail-base with later segments optional. Ears require none. These are not
  bone/solver/rig/anatomy-fidelity requirements. Ownership is the sole
  containment tree; non-ownership concepts may be reified through
  role-labelled relations.
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
  primitives, and schema or syntax technology remain deferred.
- A planned fixture-profile contract describing stable profile identity,
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
- A planned staged embodiment contract describing Stage 1 source-linked
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

No concrete schema or serialization technology is selected yet.

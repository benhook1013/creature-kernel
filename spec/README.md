# Normative specifications

Status: Active Proposed authority boundary; the body-document, body-graph,
build-operation, and fixture-manifest contracts include CK-KICK-012 Batch 13
discussion-approved material, but no format is accepted

This directory will own machine-facing semantics and serialized contracts. It is
separate from architecture so an implementation can change without silently
changing the meaning of persisted bodies or avatar packages.

The current semantic proposal set is represented by [DR-0002](../docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
Their prior revisions and reviews remain preserved as historical evidence.
DR-0002 Revision 11 and DR-0008 Revision 11 remain Proposed with Owner approval
Pending and Review Complete. Current material is recorded in DR-0006 Revision
12, DR-0011 Revision 15, and DR-0012 Revision 14; these remain Proposed with
Owner approval Pending and Review Complete after the current Double review at
exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. DR-0013 Revision 12 is
Accepted, with Owner approval Approved by Ben and Review Complete at that exact target,
decided 2026-08-13. Accepted DR-0001 Revision 5 remains the operative governance
baseline while DR-0001 Revision 6 is Proposed transition guidance with Ben's
workflow direction approved and current review complete; formal acceptance
remains pending Ben's disposition. The reviews of the earlier predecessor
revisions at commit `763cff22d10f6491a05a28312a25250704543dcf` are stale
exact-target evidence; G1/G2 were fixed mechanically, T1–T3 were resolved in
the successors, and T4 remains unselected and deferred, requiring Ben's
retained-human disposition before adapter profile/schema activation; it does not
block the empty first Rust slice. The immediate-predecessor review at exact
commit `9b96d18b115126ef09e54ad8c6f21749d5559ff6` is stale; its findings were
corrected in the current revisions. The 9c governance pass corrected two
mechanical history-label issues and its technical pass found no findings /
Ready for PR at High confidence. Review Complete is evidence only. Readiness 1
remains active in the repository. The exact schema, manifest, nine fixtures,
Rust parser/bootstrap, and Python preflight now exist as a Proposed Readiness 2
branch candidate, but are not admitted or active. See the [current review
state](../docs/project/status.md#current-review-and-future-activation-obligations)
for the current findings.
The cross-cutting proposal is
[DR-0012: initial body-document encoding, resolution, and compatibility](../docs/decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md).

## Proposed specification families

- [Body-document contract](body-document/README.md): the initial strict UTF-8
  JSON source encoding, ordered bootstrap and exact contract recognition,
  closed operation statuses and precedence, bounded deterministic diagnostics,
  and streaming/token-aware finite resource rules. Its Proposed Readiness 2
  candidate is the exact [Draft 2020-12 schema](body-document/schema/ck-body-document-v1.schema.json)
  for `creature-kernel.body` revision 1; it is not admitted or active.
- [Resolved body-graph contract](body-graph/README.md): typed concepts,
  durable semantic identity, explicit Part containment and transform
  inheritance, directed joints with owner-specific frame records,
  contextual host/mating Socket Attachment placement, provenance, Stage 1
  invariants, and successful in-memory snapshot handoff conditions.
- [Semantic-address profile](semantic-address/README.md): the exact structured
  address representation, lexical profile, closed identity kinds, structural
  equality, and reference semantics.
- [Numeric and frame profile](numeric-frame-profile/README.md): the canonical
  semantic basis, Readiness 2 rigid-transform carrier, exact JSON decimal to
  binary64 admission, quaternion and transform comparison algorithms, typed
  comparison-profile boundary, and the future adapter conformance obligation.
- [Canonical data and digest profile](canonical-data/README.md): canonical
  JSON normalization/serialization, owner-declared typed total keys and
  uniqueness/multiplicity rules for unordered collections, SHA-256 domain
  framing, and deterministic identity projections that consume normalized
  binary64 values.
- [Diagnostic registry and profile](diagnostics/README.md): sole owner of
  registry definitions, nine diagnostic domains, stable classes, occurrences,
  bootstrap compatibility, selection profiles, ordering, and compatibility;
  resource profiles remain separate operational inputs. The exact ten-code
  `ck.diagnostic.r2` candidate is documented there and remains Proposed until
  the whole Readiness 2 transaction is admitted.
- [Fixture-manifest and admission contract](fixture-manifest/README.md): the
  fixture-suite payload, separate external fixture and implementation
  bindings, preflight, successor/rollback, manifest field groups, numeric
  boundary and comparison fixture profile bindings, and readiness corpus
  admission boundary. Its Proposed Readiness 2 candidate is the exact
  manifest/schema/preflight plus nine files linked there; it is not admitted.
- [Build-operation and derived-output contract](build-operation/README.md):
  the Proposed public build envelope, in-memory snapshot handoff boundary,
  candidate-to-committed artifact identity lifecycle, deterministic target and
  collision rules, publication/inspection expectations, worker trust boundary,
  future adapter/output failure context without selecting an engine,
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
  lifecycle/remap rules are owned by the [semantic-address profile](semantic-address/README.md).
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
  components, with no scale or shear fields; the [numeric and frame
  profile](numeric-frame-profile/README.md) owns canonical numeric semantics,
  conditioning, and tolerances, while storage layout remains implementation-
  independent. Competing authored placement must agree
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
  components and no scale/shear fields. The [numeric and frame
  profile](numeric-frame-profile/README.md) owns canonical numeric meaning,
  tolerances, and comparison profiles; exact machine-schema contents remain
  readiness-gated;
  strict JSON and JSON Schema Draft 2020-12 are the selected Proposed initial
  encoding and structural-validation technologies.
- JSON decimal admission is exact-rational after strict syntax/token resource
  checks, then direct correctly rounded binary64 round-to-nearest,
  ties-to-even. Host float intermediates, locale, ambient rounding/precision,
  FTZ/DAZ, silent overflow, and arbitrary semantic digit cutoffs are not
  permitted; finite nonzero subnormals are admitted, nonzero-to-zero underflow
  and infinity overflow are rejected, lexical negative zero normalizes to
  `+0`, and raw source bytes remain unchanged. The numeric/frame profile owns
  these rules; body-document owns their source admission/status consequences.
- Exact discrete comparison remains exact. Same-target claims first normalize
  into one shared canonical local-to-parent frame; translations compare
  directly componentwise, and rotations use normalized q/-q equivalence with
  exact dyadic `sum((qa_i-s*qb_i)^2) <= (2H)^2` against an offline-admitted
  finite-binary64 `H`, with no runtime transcendental, norm, or square-root
  operation in comparison. Scalar and translation bounds use exact dyadic
  arithmetic at inclusive boundaries. `B * inverse(A)` is only a separately
  named composition/diagnostic profile, never same-target equality. Structured
  claim IDs retain occurrences/provenance, reject same-ID value collisions,
  evaluate all unordered pairs in sorted-ID order, and select the
  lexicographically smallest normalized tuple, with claim ID only for exact
  tuple ties. Authored-conflict and expected-snapshot profiles remain separate
  and their constants are experiment-gated.
- Every semantically unordered collection/projection must declare an
  owner-typed total canonical key and explicit uniqueness or multiplicity rule.
  The key is derived, not serialized solely for sorting; missing keys and
  uniqueness collisions fail closed, while legitimate repetitions retain
  explicit multiset/count/occurrence/claim identity. No source order, array
  index, traversal/allocation order, object serialization, canonical bytes, or
  raw bytes may be used as fallback. The canonical-data profile owns the
  generic algorithm and key inventory, including semantic addresses, module
  declarations, owner-role records, fixture IDs/paths, implementation-binding
  paths, dependencies, diagnostics, and future build arrays.
- Future adapters must declare an explicit signed-permutation orthogonal basis
  map and prove named directions, reflections/handedness, vector/translation
  mapping, rotation and homogeneous-transform conjugation, q conversion,
  composition, inverse, q/-q, and round trips. A separate target-precision
  profile governs correctly rounded narrowing, subnormals, nonzero-to-zero
  underflow, overflow, and angular/translation budgets without saturation,
  clamping, or ambient mode; core snapshots remain binary64 and no engine is
  selected.
- A proposed fixture-profile contract describing stable profile identity,
  concrete source inputs, discriminating parameters, seed/configuration,
  provenance, shared-generation expectations, validity/diagnostic status, the
  frozen expected outcome of valid-supported, semantically invalid, or
  well-formed-but-unsupported, plus the primary diagnostic class/code for every
  non-success fixture. Fixture-manifest admission is owned by the
  [fixture-manifest contract](fixture-manifest/README.md), which binds a
  manifest payload to separately recorded reviewed content identities and a
  separate implementation binding for any code-activating readiness gate.
  The implementation binding is a versioned domain-separated SHA-256 over an
  explicit ordered normalized safe-relative-path/mode/raw-content set; its
  binding record is outside the set, with no whole-repository or commit-
  equality identity. Post-merge and pre-ledger recomputation mismatch blocks
  activation and requires a successor. It includes relevant source, manifests,
  scripts/inputs, Cargo.lock, rust-toolchain, and applicable path dependencies;
  host/rustc/hardware evidence is recorded but not equality-bound unless a
  claim says so. Only valid-supported fixtures count toward the Stage 1
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

Diagnostic registry definitions, exactly nine domains, stable classes,
occurrence identity/multiplicity, selection profiles, ordering, and
compatibility belong solely to the diagnostic profile. Its tiny unnegotiated
bootstrap registry/profile always supports unknown required registry/profile
negotiation: top-level `unsupported`, deterministic bootstrap primary,
bootstrap effective IDs, bounded opaque requested IDs with `required=true`,
never unknown-profile emission or silent downgrade, and no extra phase. The
body-document contract owns status/precedence; build-operation owns output/status
mapping. Resource profiles are separate operational inputs.

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
structural-validation technologies. The semantic-address, numeric/frame,
canonical-data, and diagnostic profiles are Proposed and activation-gated; they
do not activate a schema, parser, resolver, or fixture corpus by themselves.

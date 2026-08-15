# Creature Kernel

Creature Kernel is an early research and engineering project for a programmable
creature-generation and embodiment platform.

The intended system begins with an authoritative semantic source set rather
than a handcrafted mesh. It resolves that source set through one operation
result envelope into a connected body, then derives surface geometry, skeleton,
skinning, collision representation, deformation metadata, materials, and
runtime interaction capabilities.

```text
Authoritative semantic source set
    -> operation result envelope
    -> optional per-build resolved semantic body graph snapshot (success only)
    -> volumes and attachment rules
    -> prepared assets plus selected semantic runtime data
    -> bounded pose, contact, deformation, and regional solvers
    -> interactive creature runtime
```

The initial creative focus is stylized furry characters. The architecture is
not intended to hard-code one species, one skeleton, or one rendering style.

## Proposed project principles

These principles remain proposed, provisional, assistant-synthesized project
direction under the accepted DR-0001 Revision 5 governance process. They are
not accepted product or architecture contracts. The source-set proposal is
[DR-0002](docs/decisions/DR-0002-declarative-body-document-source-of-truth.md),
the semantic/artifact identity proposal is
[DR-0006](docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md),
the semantic vocabulary, measurements, and frames proposal is
[DR-0011](docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md),
the real-time boundary proposal is
[DR-0003 Revision 2](docs/decisions/DR-0003-real-time-first-compiled-avatar-boundary.md),
and the CLI/API proposal is
[DR-0004 Revision 2](docs/decisions/DR-0004-external-automation-through-cli-and-api.md).
The initial product boundary and reference workflow are proposed in
[DR-0005](docs/decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).
The CK-KICK-012 Batch 4 encoding/resolution and Batch 5 blocker-resolution work
is represented by the
Proposed [body-document contract](spec/body-document/README.md) and
[body-graph contract](spec/body-graph/README.md), with the
[DR-0012: initial body-document encoding, resolution, and compatibility](docs/decisions/DR-0012-initial-body-document-encoding-resolution-and-compatibility.md)
now recorded for the integration batch. Batch 5 blocker resolutions are
discussion-approved and are reflected in the canonical specifications as
Proposed material. Accepted DR-0001 Revision 5 remains the operative governance
baseline while DR-0001 Revision 6 is Proposed transition guidance: Ben approved
its workflow direction and the current review is complete; formal acceptance
remains pending Ben's disposition. DR-0006/0011/0012 remain Proposed at Revisions
12/15/14 with Owner approval Pending and Review Complete after the current
Double review at exact target `9c0aa51d9b0307153e1e61100d8b0c18ea0bef3a`. DR-0013 Revision 12 is Accepted,
with Owner approval Approved by Ben and Review Complete at that exact target, decided
2026-08-13.
The earlier-predecessor review at commit `763cff22d10f6491a05a28312a25250704543dcf`
is stale exact-target evidence. The immediate-predecessor review at commit
`9b96d18b115126ef09e54ad8c6f21749d5559ff6` is also stale; its findings were
corrected in these revisions. The 9c governance pass found and corrected two
mechanical history-label issues; its technical pass found no findings / Ready
for PR at High confidence. Review Complete is evidence only. In the earlier
predecessor review, G1/G2 were fixed mechanically and T1–T3 were resolved in
the successors. T4 remains unselected and deferred pending Ben's retained-
human disposition before adapter profile/schema activation; it does not block
the current Rust implementation slice. Readiness 2 remains active for the
admitted schema, manifest, fixtures, parser/bootstrap, and preflight. The
workspace now also contains a provisional structural address/index and
validator plus the `inspect-structure` CLI command as preparation over those
admitted documents. The public
`creature_kernel_core::source_preparation::prepare_single_source` API is the
next bounded source boundary: it accepts raw bytes and a sealed
`ResourceProfile`, then performs admission, structural validation, basis
preparation, and numeric preparation for one source. This is not a finalized
resolved snapshot or Readiness 3 activation; geometry and runtime
implementation remain absent.

- Durable authored intent lives in an authoritative semantic source set. Every
  operation reports through one authoritative result envelope; the resolved
  graph and generated outputs remain derived, and a validated snapshot is
  optional and exists only for valid-supported success
  ([DR-0002](docs/decisions/DR-0002-declarative-body-document-source-of-truth.md)).
- Durable semantic identity is separate from artifact/build identity and
  provenance; generated topology indices are ephemeral
  ([DR-0006](docs/decisions/DR-0006-durable-semantic-and-artifact-identity.md)).
- Specialized representations and solvers share the resolved semantic graph as
  lineage; this does not require one mesh, topology, or universal solver.
- Body parts are composable generators with typed structural ownership. Part,
  Joint, Socket, Attachment, Region, Capability, and Field are the
  identity-bearing embodied concepts. A Module is an authored reusable scope
  that instantiates them, not an embodied graph concept; landmark, anchor,
  dimension, and frame are typed owned records addressed by owner and role.
  Every embodied Part, including an optional module root, has exactly one
  explicit containment path to the embodied root; relations do not create or
  repair containment, and containment supplies reference-transform inheritance.
  Containment and relation cycles are validated independently. Required Stage 1
  Joints connect structural parent Parts to immediate children. Joints are
  directed relations with one proximal and one distal Part endpoint and
  resolved canonical frame records in each Part-local basis; sockets are
  Part-owned interfaces with owning-Part frame records. An Attachment joins
  one host Socket to one mating Socket, derives module-root placement from the
  host Part/frame, both Socket frames, an optional offset, and the inverse
  mating frame, and does not imply articulation. Initially an attached root has
  one incoming Attachment and its host/mating ownership must agree with
  containment.
- The pelvis Part owns the root-reference frame. The first typed axial
  articulation is pelvis → spine Joint → torso/chest Part → neck-base Joint →
  neck Part → head-base Joint → head Part. Arm and leg chains similarly use
  explicit Joints between Parts and end at terminal paw-base landmark/Socket
  roles. Ear/tail modules use Attachment, while a movable tail also uses a
  separate Joint. These are semantic roles, not a bone, solver, rig, or
  anatomy-fidelity claim
  ([DR-0008](docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md)).
- Measurements keep transforms as reference-frame placement, typed dimensions
  as size/extents, and anchors/landmarks as stable authored or derived values;
  ratios are derived. Claims compare after normalization by owner address,
  property role, and frame/context; authored claims and explicit invariants
  must be jointly satisfiable, while derived/defaulted values never override
  authored values. Conflicts produce a deterministic semantic-invalid
  diagnostic and no success snapshot. Sources declare units, handedness, up,
  and forward; conversion to a contract-revision canonical basis records
  provenance. Exact axes, units, rotation, scale, and shear remain deferred
  ([DR-0011](docs/decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md)).
- CLI/API, future GUI, tests, scripts, and external AI agents are adapters over
  one deterministic domain-operation model
  ([DR-0004](docs/decisions/DR-0004-external-automation-through-cli-and-api.md)).
- The core application does not depend on an embedded AI assistant.
- A real-time game is the primary downstream experience. Expensive invariant
  generation happens outside the frame loop; hybrid compiled avatars expose
  bounded runtime representations and fallbacks
  ([DR-0003](docs/decisions/DR-0003-real-time-first-compiled-avatar-boundary.md)).
- Specialized animation, contact, and deformation solvers cooperate through a
  shared representation; no single solver is expected to solve everything.
- Capability levels and fallbacks should let characters participate even when
  they do not support the highest simulation quality.
- The initial product is an engine-independent procedural creature compiler and
  embodiment runtime, not a game, editor, or general-purpose engine. A
  real-time game is the first downstream proof and integration target.
- The earliest workflow is the project developer or researcher using structured
  source, CLI/API operations, diagnostics, and reproducible evidence. Technical
  artists and game developers remain important downstream review and integration
  users.
- Stylized furry characters are the initial domain. Adult interactions are
  motivating difficult contact and deformation stress cases, while reusable
  body, contact, and solver mechanisms remain general.
- Native programmatic generation without a handcrafted base mesh is the first
  reference path. External authored-mesh conformance is a later path that early
  contracts must not foreclose.
- The initial body-document adapter is strict UTF-8 JSON: one document,
  duplicate-key rejection, no comments/includes/evaluation, exact semantic
  contract-family and revision recognition, and structural validation with the
  proposed JSON Schema Draft 2020-12 vocabulary. Unknown core members fail;
  unsupported required extensions fail as unsupported, while optional
  extensions remain opaque and have no core semantic effect. Explicit
  migration produces a new source, and semantic contract identity remains
  separate from compiler/build/configuration/seed/dependency/artifact identity.
  Bootstrap requires byte/UTF-8 admission, strict duplicate-detecting parse,
  top-level object and exactly one family/revision discriminator, recognition
  before revision-schema selection, then revision-specific validation. Exact
  field names, machine schema, canonical bytes, and hashing remain deferred.
  Every operation exposes one of the closed statuses success, input-failure,
  invalid-source, unsupported, dependency-failure, resource-limit, or
  internal-failure with deterministic precedence and bounded diagnostics.

## Repository navigation

- [Documentation authority and reading order](docs/README.md)
- [Developer setup](DEVELOPER_SETUP.md)
- [Product vision and scope](docs/product/vision-and-scope.md)
- [Proposed body-document contract](spec/body-document/README.md)
- [Proposed body-graph contract](spec/body-graph/README.md)
- [Architecture](docs/architecture/README.md)
- [Decision record registry](docs/decisions/registry.md)
- [Open research questions](docs/research/open-questions.md)
- [Current project status](docs/project/status.md)
- [Authored examples](examples/README.md)

## Status

The project is in an exploratory executable-prototype and semantic-contract
integration phase. The accepted first production platform is Rust-first and
engine-independent; Readiness 2 remains active for the admitted schema,
manifest, fixtures, parser/bootstrap, and preflight. A provisional structural
address/index and validator plus the `inspect-structure` CLI command now exist
as preparatory implementation. They do not constitute a finalized resolved
snapshot or Readiness 3 activation. Rust `1.97.1` is the pinned first
production toolchain; geometry and runtime implementation remain absent. The
standalone `creature_kernel_core::numeric` module is preparatory only: it validates strict
JSON-number grammar, performs the pinned direct correctly-rounded binary64
conversion, reports typed overflow/nonzero-underflow failures, admits finite
subnormals, and normalizes lexical zero to `+0`; it is not wired into
body-document admission or Readiness 3. The standalone
`creature_kernel_core::frame` module is likewise preparatory: it provides a
normalized-binary64 structural transform carrier, exact signed-axis
source-basis mapping, and symbolic length-unit ratios. The internal
`frame_preparation` adapter is used only by
`source_preparation::prepare_single_source`; it is not a public record-level
admission bypass. The source projection exposes complete semantic numeric
maps for part/joint/socket/attachment transforms, landmark positions,
dimensions, and named frames, keyed by stable semantic addresses or
owner/role keys. Its graph retains admitted source records, basis/profile, and
contract context as semantic provenance; raw lexical spelling/provenance is
not recovered. Preparation does not apply basis/unit values or quaternion
semantics, expand dependencies/modules, produce claims/snapshots or
serialization, or activate a resolver or Readiness 3. See
[developer setup](DEVELOPER_SETUP.md) and [current project
status](docs/project/status.md) for the live round, review, and owner-
disposition state.

To inspect the authored structural example:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

The command is a provisional source-preserving inspection, not a resolver or
geometry build. Parser/schema admission can succeed while stronger structural
inspection still reports `invalid-source`; see [authored examples](examples/README.md).

`inspect-structure` is unchanged: it reports only the source-preserving
structural graph projection and structural diagnostics. The prepared-source
inspection is a separate provisional developer-instrumentation command:

```bash
cargo run -p creature-kernel-cli -- inspect-prepared-source \
  --input examples/body-documents/stylized-digitigrade-biped.json
```

For one admitted source, `inspect-prepared-source` emits that same graph plus
the declared source basis, prepared collection counts, and numeric debug rows
with stable semantic addresses or owner/role locations, display values, and
binary64 bits. It is an admitted single-source projection only: it does not
resolve dependencies or make a snapshot, perform canonical serialization,
apply basis or unit values, interpret quaternions, expand dependencies or
modules, or produce geometry, rigging, animation, physics, or runtime output.
It does not activate Readiness 3. Preparation failures emit bounded
diagnostics without a partial prepared payload.

For a local browser view of that projection, see the concise
[structural-review workflow](docs/developer-workflows/visual-review-gallery.md).
For a browser session, build the CLI, then run
`publish_prepared_source.py` followed by `serve.py` against a disposable local
root. The authoritative commands, bounds, and session behavior are in the
[visual-review tool README](dev-tools/visual-review/README.md); the existing
image-review gallery remains supported.

See [docs/FOUNDATION.md](docs/FOUNDATION.md) for the historical
conversation-derived record. Current contracts are owned by the documentation
areas linked above.

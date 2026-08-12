# System architecture overview

Status: Provisional conceptual baseline

## System purpose

Creature Kernel is proposed as an engine-independent procedural creature
compiler and embodiment runtime. It resolves an authoritative semantic source
set into one operation-result envelope and, for valid-supported success, an
optional per-build semantic body-graph snapshot, then derives specialized
representations for an embodied runtime avatar. It provides bounded systems for
animation, contact, deformation, and engine integration. It is not initially a
game, editor, or general-purpose engine; a real-time game is the first
downstream proof and integration target. This boundary remains Proposed under
[DR-0005](../decisions/DR-0005-initial-product-boundary-and-reference-workflow.md).
The current semantic boundaries are Proposed under [DR-0002](../decisions/DR-0002-declarative-body-document-source-of-truth.md),
[DR-0006](../decisions/DR-0006-durable-semantic-and-artifact-identity.md),
[DR-0008](../decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md),
and [DR-0011](../decisions/DR-0011-minimal-semantic-vocabulary-measurements-and-frames.md).
CK-KICK-012 Batch 6/7/8/9/10/11/12 resolutions are discussion-approved and represented
here as Proposed architecture consequences. DR-0002 Revision 11 and DR-0008
Revision 11 remain Proposed with Owner approval Pending and Review Complete.
DR-0006 Revision 8 remains Proposed with Owner approval Pending and Review
Complete; unresolved C1/C3/C4 contract findings remain. DR-0011 Revision 11,
DR-0012 Revision 10, and DR-0013 Revision 8 remain Proposed with Owner
approval Pending and Review Complete after the Batch 12 Double review of
commit `730a2f77840cc0caa1f838c30dac4ff20f985e69`; both independent passes
recommend Revise at High confidence, with unresolved A1–A4 and E1–E5 findings.
The Batch 11 review artifacts are stale only for those three materially revised
records. The fresh Batch 11 Double
review targeted commit `053dba58fd344ed636420e0974cf617862fe265f`; both
independent passes recommended Revise at High confidence at that historical
revision. The completed Batch 9 Double review targeted commit
`6cf17270fda2827756c24a8d0fb301bef358f98f`; its evidence is stale for the
revised records and is not acceptance. No implementation or readiness gate
activates. See the
[current review state](../project/status.md#current-review-and-future-activation-obligations)
for review lenses, recommendations, and findings. Earlier review evidence is
stale after these revisions; see the [decision registry](../decisions/registry.md).
The CK-KICK-012 Batch 5 review at commit
`a282dbabffd83afa4e62577086934d00f98e12c7` is stale historical evidence. No
acceptance or clean review is implied.

```text
Human, script, test, or external AI
              |
              v
   Operation adapters (CLI/API/GUI)
              |
              v
   Shared domain operations
              |
              v
 Authoritative semantic source set
              |
              v
 Operation result envelope
              |
              v
 Optional valid-supported resolved semantic body graph
              |
              v
      Specialized compilers
   +----------+----------+-----------+
   |          |          |           |
   v          v          v           v
Body graph  Surface   Skeleton   Collision and
and fields   mesh     and skin   deformation data
   +----------+----------+-----------+
              |
              v
   Hybrid runtime avatar package
              |
              v
       Embodiment runtime
              |
              v
        Host-engine adapter
```

## Principal representations

### Authoritative semantic source set

The proposed authored inputs that preserve durable semantic intent. Initially
this may be one human-readable document; future explicit semantic override
layers may also be authored inputs. Every outcome-affecting external authored
asset is an exactly versioned dependency of the source set; an external mesh is
authored input but not semantic truth. The source set alone is authored
authority. The initial adapter is proposed strict UTF-8 JSON with JSON Schema
Draft 2020-12 structural validation; the complete admission and compatibility
boundary is owned by the [body-document contract](../../spec/body-document/README.md).

### Operation result envelope and resolved semantic body graph snapshot

Every phase and diagnostic belongs to one authoritative operation-result
envelope with a closed status, completeness indication, deterministic bounded
diagnostics, and a validated per-build snapshot whenever the operation contract
requires one; successful `resolve` requires the in-memory snapshot. The
body-document contract owns bootstrap order, status precedence, diagnostic
retention/order, and hostile-input resource guards. The graph contract owns
resolved semantic structure. Resolver phase 8 is snapshot finalization/handoff,
not filesystem serialization. Mesh, rig, runtime, and other artifacts remain
further derived outputs. See the
[body-document contract](../../spec/body-document/README.md) and
[body-graph contract](../../spec/body-graph/README.md), and the
[build-operation contract](../../spec/build-operation/README.md); exact field
spellings, diagnostic codes, and activation constants remain gated by the
Proposed focused profiles.

### Proposed production platform and artifact/workbench boundary

CK-KICK-013 is a discussion-approved platform proposal, not an accepted
implementation decision. Proposed DR-0013 Revision 8 has Owner approval Pending
and Review Complete after the Batch 12 Double review of commit
`730a2f77840cc0caa1f838c30dac4ff20f985e69`, with unresolved findings carried forward
from Batch 11. The Batch 11 review evidence is stale for this materially
revised record; the fresh Batch 11 Double review targeted
commit `053dba58fd344ed636420e0974cf617862fe265f`; both independent passes recommend Revise at High confidence. The completed Batch 9 Double review targeted
commit `6cf17270fda2827756c24a8d0fb301bef358f98f`; its evidence is stale for
the revised record and is not acceptance. No implementation or readiness gate
activates. See the [current review
state](../project/status.md#current-review-and-future-activation-obligations)
for recommendations and findings. The four
readiness stages are: acceptance activates only the
empty Cargo shell; numeric/frame, semantic-address, canonical-data, and
diagnostic profiles precede exact schema/manifest admission; the exact schema,
versioned preflighted fixture manifest, listed files, and parser/bootstrap must
be admitted together in one Readiness 2 review-branch transaction; a distinct
Readiness 3 successor transaction with frozen expected graph outputs activates
semantic resolution and in-memory snapshot handoff; and a working resolver plus provisional geometry profile and
project-owned seam activates exploratory Stage 1 geometry. Its target is a stable Rust
production semantic/compiler core in a Cargo workspace, an engine-independent
compiler library, a thin CLI, and a versioned project-owned backend-neutral
GeometryRequest/GeometryResult seam, with no initial daemon or service. Stage 1
uses an in-process Rust CPU dense-field evaluator/extractor. If measured
capability/performance or a justified isolation, security, portability, or
licensing need exposes a gap, evaluate an isolated C++ worker/backend first;
use in-process C ABI/FFI only if that worker is proven insufficient. This
leaves room for a backend change and makes no advanced-Rust-geometry maturity
claim.

Python remains the disposable host for experiments, evidence/render tooling,
and visual workbench tasks; it is not a production compiler dependency. The
first reference path is WSL2 x86_64 GNU, with a
later native-Linux portability smoke. Record `rust-toolchain.toml`,
`Cargo.lock`, target/profile, `rustc -Vv`, and reference metadata; review each
dependency's license, unsafe/native code, and portability/security relevance
without Git pinning or heavyweight audit bureaucracy. The
[build-operation contract](../../spec/build-operation/README.md) owns the
public envelope for complete success outputs, candidate-to-committed
artifact identity, explicit-output-root target derivation, idempotent
publication, target conflicts, no-replace failure, and lineage-checked
inspection. Failed operations initially return the authoritative envelope and
persist no diagnostics-only failure bundle. The architecture consumes that Proposed boundary and does not
select final serialization or compatibility.
The seam does not select a permanent surface/backend or create DR-0009/0010
evidence. Future workers negotiate protocol/version, obey bounded time/resources, map
crash/timeout/resource outcomes, validate outputs, and leave the compiler
surviving failure. Canonical bytes are proposed as restricted canonical JSON
with domain-separated SHA-256 digests; exact numeric and address rules remain
evidence-dependent. Performance claims require a reproducible benchmark and
hardware profile.

Batch 10's initial filesystem profile supports only tested local WSL Linux under
`/home`; `/mnt/c`, network, removable, and unspecified filesystems remain out
of profile. Same-filesystem sibling staging, capability probing, atomic
no-replace, immutable committed outputs, cooperating builders, and
post-collision inspection provide process-crash-safe namespace publication,
without a sudden-power-loss durability claim. A profile-defined unambiguous
safe-ASCII candidate path mapping is an activation prerequisite. Malicious or
privileged concurrent mutation is outside scope, but inspection must verify a
complete artifact or reject it.

Build requests contain all outcome-affecting source/dependency,
compiler/toolchain, contract/schema/profile, configuration/seed,
backend-capability/protocol, and target-platform inputs. Attempt identity is
unique for tracing only; candidate identity derives from the deterministic
request, artifact role, and identity-rule revision. The [fixture-manifest
contract](../../spec/fixture-manifest/README.md) owns the manifest payload and
separate readiness/decision content-identity admission. Inspection is a separate
read operation with closed statuses;
producer/output trust is distinct from coordinator/reporter/publisher trust,
and lost worker trust cannot be rehabilitated by validation.

Batch 11 and Batch 12 propose typed restricted-ASCII machine addresses with
separate Unicode display names; a right-handed metre semantic basis (+Y up,
+Z creature-forward); finite binary64 values with correctly rounded decimal
admission and canonical quaternion treatment; fixed-order operations with no
reassociation, implicit FMA contraction, FTZ, or DAZ; deterministic typed
all-pairs comparison profiles; and a small versioned diagnostic registry.
Readiness 3 is a separate transaction for expected graph snapshots and
comparison rules, after those prerequisites and the canonical-data profile are
available. The planned numeric experiment preregisters intended domains,
separate semantic error budgets, exact/higher-precision oracles, frozen
development/held-out/adversarial corpora, condition estimates, and metamorphic
checks. Comparator shapes/formulas and normalization/sign direction are fixed
Proposed material; constants, ranges, validation-margin/error formula, and
deterministic evaluation implementation/binding remain open. Adapter
conformance remains deferred until adapter activation. These are Proposed
architecture consequences, not activated implementation work.

### First body grammar boundary

The first grammar is a bounded typed Part-containment tree for the proposed
digitigrade biped family plus the seven typed concepts and relation semantics
owned by the [body-graph contract](../../spec/body-graph/README.md). Its
architectural boundary is explicit: every embodied Part has one containment
path, containment supplies transform inheritance, relations cannot repair
containment, and containment and relation cycles are checked independently.
Absent optional module declarations retain a stable authored declaration
address and non-embodied root-role/template reference, emit no Part, reserve no
Part identity, and cannot be relation targets; a later present root derives its
Part identity from the module-instance anchor and root role. This is not an
additional embodied graph concept.
Required Stage 1 Joints connect structural parents to immediate children.
Attachment composition derives the attached root's sole child-local containment
placement from the host Socket, optional typed offset, and the mating Socket frame
after composing the attached-root-to-Socket-owner containment transform;
descendants inherit only through containment and the no-implied-Joint rule is
preserved. Each Socket has total active capacity one across host and mating
roles, so same-role and cross-role reuse are invalid conditions with
deterministic diagnostic treatment. Every transform entering Attachment composition is finite,
non-degenerate, and invertible under the declared profile; a source violation
is `invalid-source`, while an implementation failure on an admissible transform
is `internal-failure`. Exact representation, conditioning, and tolerance are
deferred to resolver activation.
Resolved Joint and Socket frame records are canonical semantic handoff data,
not rig or runtime data. The architecture consumes these rules and does not
restate serialized spellings or numeric conventions; see the canonical graph
contract for the minimum axial/limb chain, provenance, and invariants.

### Simulation representation

Skeletons, joint limits, analytic collision, signed-distance fields, deformation
cages, regional simulation meshes, mass properties, and semantic contact regions.

### Visible representation

Renderable surface geometry, normals, material attributes, LODs, attachments,
and bindings to the simulation representation.

### Runtime avatar package

A derived, bounded hybrid package containing conventional prepared mesh, LOD,
rig, collision, material, and deformation assets plus selected semantic fields,
cages, signed-distance data, and regional simulation data required by a runtime
adapter. It is not a promise of fully live implicit generation or
semantics-free conventional assets. Artifact/build identity and provenance
distinguish generated packages from durable semantic identity. Exact
serialization, compatibility, and streaming behaviour remain undecided.

### Stage 1 surface experiment hypotheses

The Stage 1 surface proposals are deliberately narrower than this conceptual
runtime architecture. The [first surface experiment design](../research/first-surface-experiment-design.md)
and linked [DR-0009 Revision 8](../decisions/DR-0009-hybrid-surface-generation-experiment-hypothesis.md)
and [DR-0010 Revision 8](../decisions/DR-0010-stage-1-surface-extraction-and-semantic-field-propagation.md)
are parked, Proposed confirmatory-research material. Their detailed records and
reviews are preserved, but no Revision 9, owner disposition, or additional
review is active. They become relevant only when at least two runnable candidate
surface implementations exist and a comparative outcome is intended to justify
production architecture, or when Ben explicitly reactivates them. Exploratory
prototypes may proceed before then, but their observations cannot claim formal
DR-0009/0010 support or reject. Permanent surface and topology architecture,
runtime field representation, animation-ready edge flow, retopology, and
backend choice remain unresolved.

## Architectural principles

### One source relationship

Geometry, rigging, collision, materials, deformation, packaging, and runtime
representations must derive from the same resolved semantic graph or explicitly
identify a linked authored input. This shared lineage does not require one mesh,
topology, geometry field, or universal solver.

### Semantic stability

Durable behaviour targets parts, regions, joints, attachments, local frames, and
capabilities through structured semantic addresses composed of source
namespace, authored module-instance anchors, concept kind, and role-local key.
Each source namespace has one unique owner in a resolved source set. Namespace
collisions require an authored, deterministic, collision-free remapping across
every contributed semantic address; implicit shared namespace ownership is not
allowed. Addresses are not derived from incidental path,
ordering, geometry, artifact identity, topology, or content hash. Artifact/build
identity and provenance remain separate; generated topology indices are
ephemeral through topology changes. Exact serialized address syntax and
clone/rename/split/merge/replacement lifecycle and remap rules remain deferred.

Only valid-supported input produces an optional compilable validated graph
snapshot; semantically invalid and well-formed-but-unsupported input are
distinct outcomes in the result envelope, with any rejected partial graph
explicitly non-compilable and non-contractual debug information.

Transforms own reference-frame placement, typed dimensions own size/extents,
and anchors/landmarks retain authored or derived provenance. Ratios are derived
only; conflicting constraints diagnose rather than silently choosing a winner.
The contract distinguishes Part local/reference, Joint proximal/distal, Socket
intrinsic interface, Attachment host/mating endpoint context, derived resolved
world/reference, and runtime-pose frames. Readiness 2 uses a rigid transform
carrier with exactly three translation components and four explicit `xyzw`
quaternion components, with no scale/shear fields; Readiness 3 freezes the
numeric basis, normalization, conditioning, and tolerance semantics.

### Deterministic core

Resolution and compilation should be reproducible from authored inputs, compiler
version, configuration, and seed. Query, mutation, resolution/compilation,
validation, diagnostics, and artifact inspection use one deterministic domain
operation model. Nondeterministic stages must be isolated and reported.

The resolver uses the ordered phases and closed result-status rules in the
[body-document contract](../../spec/body-document/README.md). Complete
acquisition is required before invalid-source. Fatal phases block dependent
work while independent diagnostics in a reached phase may accumulate; the
envelope retains reached diagnostics. Internal trust loss precedes a
qualifying resource-limit, which precedes the earliest applicable phase unable
to produce its required output. In a mixed dependency phase,
dependency-failure precedes invalid-source and then unsupported; parse and
semantic phases use invalid-source before unsupported. All mandatory independent
checks capable of changing status or primary run unless resource/trust
interruption prevents them. Processing is complete when all applicable work
establishing/trusting the selected outcome ran; blocked phases are inapplicable.
Diagnostic completeness means all applicable profile-required diagnostics were
retained; ordinary truncation is not resource-limit when processing/trust
continue, and optional checks cannot change status or primary. The primary is
the first diagnostic establishing the final status under that ordering. The architecture requires deterministic work and
bounded diagnostics but leaves profile values and accounting detail to the
canonical specification. Semantic equivalence and identity remain separate
from source ordering, compiler/build/configuration/seed, dependency, artifact,
and incidental topology identities.

### Engine-independent contracts

The proposed semantic model and runtime package concepts should not depend on one
host engine. Adapters translate those concepts into engine-specific systems;
the detailed package and interface contracts remain open under Proposed
[DR-0003](../decisions/DR-0003-real-time-first-compiled-avatar-boundary.md).

### Compile/runtime separation

Expensive invariant generation is outside the frame loop. The runtime performs
bounded live pose, contact, parameterized deformation, and activated regional
solver work against the hybrid package. Compatible parameter changes may update
in place; topology, body-plan, and major structural changes require
recompilation and validation. The initial preview workflow may block while it
reloads a valid replacement in the same session, while a failed replacement
retains the old validated avatar.

### Specialized solvers

Animation, IK, collision, balance, cage deformation, cloth, and volumetric
simulation remain specialized layers coordinated through explicit data and
ownership. No universal solver is assumed.

### Bounded quality

Runtime work must be budgeted by capability, region, distance, interaction, and
hardware. Advanced systems require lower-cost fallbacks.

### Evidence before commitment

Uncertain geometry, animation, physics, and performance choices should advance
through research questions, experiments, adversarial review, and decision
records.

## System boundary

Creature Kernel initially owns (proposed boundary):

- authored semantic-source parsing and validation;
- semantic body resolution;
- native procedural creature compilation;
- avatar packaging and diagnostics;
- runtime semantic capabilities and interaction coordination;
- shared domain operations and CLI/API adapters;
- host-engine adapter contracts.

It does not initially own:

- a complete renderer or general-purpose editor;
- game logic unrelated to creature embodiment;
- online accounts, commerce, or SaaS infrastructure;
- a language model;
- cinematic-quality simulation as a mandatory runtime dependency.

## Major unresolved choices

- Exact body-document fields, schema contents, and later source-set layering.
- Permanent surface and topology generation strategy (the Stage 1 hypotheses in
  DR-0009 and DR-0010 do not resolve it).
- Production implementation platform is proposed as Rust/Cargo under
  CK-KICK-013; geometry libraries/backend and any C++ worker boundary remain
  evidence-driven and unresolved.
- Exact morphology ranges and generator set for the selected first family.
- Skinning and joint-correction approach.
- Runtime engine and adapter interface.
- Collision and deformable-body backends.
- Avatar-package serialization and versioning.
- Performance envelope and reference hardware.
- Capability-tier labels, finite quality budgets, and fallback thresholds.
- Future asynchronous package-swap state and compatibility rules.
- Bit-exact simulation, network, and replay determinism requirements.
- Artifact storage and reproducibility strategy.

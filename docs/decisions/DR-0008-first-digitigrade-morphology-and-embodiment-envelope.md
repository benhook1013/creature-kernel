# DR-0008: First digitigrade morphology and Stage 1 embodiment envelope

ID: DR-0008

Scope: Product, Specification and architecture

Status: Proposed

Revision: 10

Decision owner: Ben

Owner approval: Pending

Review status: Complete

Date proposed: 2026-08-09

Date decided: —

Discussion approval date: 2026-08-12

Revision history: Revisions 1–7 and their reviews remain preserved as
historical evidence. Revision 3 recorded Ben's CK-KICK-012 Batch 1
morphology/grammar selection, Revision 4 recorded its first review-resolution
batch, Revision 5 recorded the Batch 3 fixture-outcome resolution, and
Revision 6 recorded the Batch 4 typed articulation/composition selection. On
2026-08-11 Ben approved the CK-KICK-012 Batch 5 blocker-resolution selections
recorded in Revision 7: explicit containment, Attachment placement and
validity, canonical Joint and Socket frame records, and the linked operation
outcome/bootstrap/resource rules. The exact-revision CK-KICK-012 Batch 5
Double review of Revision 7 is stale historical evidence. Its three findings
motivated the CK-KICK-012 Batch 6 resolutions recorded in Revision 8. The exact
Revision 8 Double review at commit
`c64b1b98948304d631eecea6a354c9e42c89c510` then identified F2–F3 for this
record. Ben approved those finding resolutions in discussion on 2026-08-11;
Revision 9 then resolved the typed descendant-owned Attachment composition and
mating-Socket cardinality consequences, while DR-0002, DR-0011, and DR-0012
carried linked graph, vocabulary, and status details. Revision 10 records
Ben's 2026-08-12 discussion approval of five Recommendation 1 resolutions:
the total status/completeness rule, normalized module-instance declaration and
global Socket capacity, Attachment transform admissibility, the four readiness
gates, and the authoritative build/publication outcome. This discussion
approval is not DR acceptance. Revision 10 remains Proposed with Owner approval
Pending and Review status Complete. The current-revision Double review examined target
commit `88004388f9537a37617ae248bdaad4625e6f3f03` in [review 01](reviews/DR-0008-rev-09-review-01.md)
and [review 02](reviews/DR-0008-rev-09-review-02.md); both independent passes
recommend **Revise** at **High** confidence. The prior Review Complete state
records evidence, not a clean review or acceptance. Those Revision 9 artifacts
are now stale historical evidence after this proposal change and a fresh current
Double review is required. The Revision 8 and earlier reviews remain stale
historical evidence.

Supersedes: —

Superseded by: —

## Context

The initial product boundary calls for stylized furry characters generated
without a handcrafted base mesh, while the first supported family and its
variation envelope remain unresolved. A bounded family and fixed fixture set
are needed for comparable surface and embodiment evidence. The semantic source
and lineage boundaries in DR-0002 and DR-0006 require the family to be
described through semantic modules rather than per-fixture output patches.

Stage 1 also needs enough linked embodiment information to preserve the path to
Stage 2 without claiming animation, contact, or deformation success.

The semantic grammar must be bounded enough for the first family while keeping
ownership distinct from other typed relationships. It must also leave room for
future graph relationships without implying support for arbitrary anatomy.

## Decision

### First morphology family

**Recommendation: Option 1 — a bounded stylized digitigrade furry biped.** The
family has these required semantic modules:

- torso and pelvis;
- head with a simplified muzzle;
- two arms;
- simplified hands or paws;
- two digitigrade legs; and
- simplified feet or paws.

Ears and tail are optional predefined modules addressed through named semantic
sockets. Their presence, type, and style are explicit module choices rather
than arbitrary attachment graphs.

Continuous variation is permitted in stature, torso width and depth,
head/muzzle scale, arm and leg length, foot size and angle, ear length, and
tail length and curvature. Exact ratios are deferred to evidence; this record
does not define numeric parameter ranges.

The following are explicitly invalid or deferred for this family: extra limbs,
wings, a quadruped stance, arbitrary joint counts or attachment graphs,
detailed fingers or toes, arbitrary anatomy, plantigrade bodies, and other
morphology families.

The fixed qualitative fixture set contains at least four substantially
different profiles, including:

- compact, broad, short-limbed, large-head;
- tall, narrow, long-legged;
- slender, long-limbed; and
- stocky, broad-chested.

At least one fixture contrasts optional-module presence, absence, or style.
All fixtures use the same grammar and generators. No fixture may require a
per-fixture mesh, topology, or rig correction.

The project may select experiment hypotheses and the profiles they are meant
to discriminate before exact fixtures are frozen. Before EXP-0001 executes or
its evidence is used, it must freeze stable fixture IDs, concrete source
inputs, discriminating parameters, seed/configuration, provenance, expected
outcome classification, and the expected primary diagnostic class/code for
every non-success fixture. Each fixture's expected outcome is exactly one of
valid-supported, semantically invalid, or well-formed-but-unsupported. This
proposal does not invent the exact values or fixture files. The freeze is a
prerequisite to execution and evidence, not to deciding what to test. Only
valid-supported fixtures count in the Stage 1 success population; semantically
invalid and well-formed-but-unsupported fixtures remain diagnostic evidence.
This three-way taxonomy applies only after a fixture is admitted, recognized,
and classified as a candidate for the Stage 1 semantic contract. Admission or
loading failures, strict parse/schema/discriminator failures, dependency
failures, configured resource limits, and internal/compiler-invariant failures
are separate operation outcomes under DR-0012 and must not be relabelled as
one of these three semantic fixture classes.

### Body grammar and relation boundary

The first body grammar is a bounded typed ownership tree for the proposed
digitigrade biped family. It covers the required modules and predefined optional
ear/tail socket modules above. It also admits typed non-ownership relations for
joints, sockets/attachments, capabilities, and regions. Ownership edges and
relations are distinct: a relation does not imply ownership, and ownership does
not replace the relation's type or semantics.

The normalized model declares each instantiated module through a
backend-neutral module-instance declaration owned by the graph boundary in
DR-0002. The declaration identifies the module, its root Part, an
instance-anchor/provenance, presence and optionality, and whether Attachment
composition is required; it is not an eighth identity-bearing graph concept.
Optional absence is distinct from a present-but-unattached module before
Attachment cardinality checking. A present Attachment-required root with zero
incoming active Attachments is deterministically invalid. Nested module
instances use distinct Socket instances and preserve containment/provenance.

Part-to-Part ownership is the sole structural body-containment tree. Every
embodied Part, including an optional module Part, has exactly one containment
path to the embodied root. Joint, Attachment, Region, and other relations
cannot create or repair that path. Containment owns reference-transform
inheritance; containment reachability and cycles are validated separately from
typed-relation cycles. For this bounded Stage 1 axial/limb grammar, required
Joint edges connect a structural parent Part to its immediate child Part.
Declarative ownership of other concepts and typed records scopes identity and
lifecycle without adding structural body edges. Durable non-structural
concepts may be reified and connected through multiple role-labelled
relations. The selected Joint, Socket, and Attachment endpoint roles,
placement, and cardinalities are defined below and in DR-0011. This is not a
general arbitrary hypergraph or solver representation. The first grammar
nevertheless supports only this bounded family and its declared relation
kinds; arbitrary anatomy and arbitrary user-defined graph kinds are
unsupported. Invalid or unsupported assemblies receive structured
diagnostics. Units and coordinate basis must be declared, and local frames and
resolved transforms must be explicit. All embodied Parts must remain
connected. A present attached module root has exactly one incoming active
Attachment, an absent optional module has none, and each Socket has total active
capacity one across host and mating roles. A Socket used by two active
Attachments in any role combination, including one host use plus one mating
use, is invalid. Repeated endpoint pairs, host reuse, mating reuse, and
cross-role reuse are distinct diagnostic concepts or map to an explicit
deterministic diagnostic; zero incoming Attachments for a present attached
module root and multiple incoming Attachments remain distinct invalid
conditions.

The first digitigrade family requires the following typed functional
articulation and landmark roles for Stage 1 lineage. A root-reference frame is
owned by the pelvis Part. The directed axial chain is:

- pelvis Part → spine Joint → torso/chest Part → neck-base Joint → neck Part →
  head-base Joint → head Part;
- shoulder Joint (torso Part → upper-arm Part) → elbow Joint (upper-arm Part →
  forearm Part) → wrist Joint (forearm Part → hand/paw Part), with a terminal
  paw-base landmark or Socket; and
- hip Joint (pelvis Part → thigh Part) → knee Joint (thigh Part → lower-leg
  Part) → one hock/ankle Joint (lower-leg Part → foot/paw Part), with a
  terminal paw-base landmark or Socket.

Each named articulation is a directed Joint with exactly one proximal Part and
one distal Part. Its resolved representation canonically owns proximal-frame
and distal-frame typed records, each expressed in the corresponding Part's
local basis, with source-reference provenance retained; the record is not a
bone, solver constraint, limit, rig, or runtime representation. A terminal
landmark or Socket is a typed record/interface owned by its named Part; it is
not an additional implicit Joint. A Socket owns exactly one interface frame in
its owning Part basis. Source references may supply these records, but the
resolved graph materializes the canonical owned records.

Optional ear and tail module composition uses an Attachment between a host
Socket and a mating Socket. The mating Socket may be owned by any Part in the
attached module-root containment subtree. For the typed transform contract,
`T_A←B` maps coordinates expressed in B into A. Let H be the host Part, R the
attached subtree root Part, M the mating Socket owner Part, and `S_h` and `S_m`
the host and mating Socket frames. Let `O_(S_h←S_m)` map mating-Socket
coordinates into host-Socket coordinates; identity makes the frames
coincident. The conceptual host-local equation is:

`T_H←R = T_H←S_h · O_(S_h←S_m) · (T_R←M · T_M←S_m)^−1`

Composition is understood in the stated coordinate bases and order, with the
rightmost transform applied first. Matrix layout and serialization remain
deferred. An optional authored Attachment offset, if admitted, is part of the
host/mating alignment transform `O` in that typed basis; exact field spelling
and tolerance remain deferred. The Attachment-derived result is the attached
root's sole resolved child-local containment placement relative to its host
parent. Descendants inherit only through containment; Attachment adds no
parallel transform-inheritance path. If authored root-local placement
independently controls the same degrees of freedom, it must agree with this
same canonical derived child-local value within the later contract tolerance or
the document is semantically invalid. Provenance for all source frames,
containment transforms, offset, and composition steps remains. Every transform
entering Attachment composition must be finite, non-degenerate, and invertible
under the declared transform profile. A source-caused violation is semantic
`invalid-source` with a deterministic diagnostic and preserved provenance;
implementation failure on an admissible transform is `internal-failure`. Exact
representation, allowed scale/shear, conditioning threshold, comparison
tolerances, and matrix storage remain resolver-activation prerequisites or
deferred specification details. A present attached module root requires exactly
one active incoming Attachment, while an absent optional module has none. Each
Socket has total active capacity one across host and mating roles; using a
Socket in two active Attachments in any combination, including one host use and
one mating use, is invalid. Repeated endpoint pairs, host reuse, mating reuse,
cross-role reuse, zero incoming Attachments, multiple incoming Attachments,
invalid or detached endpoints, containment disagreement, and Attachment cycles
are invalid, with distinct deterministic diagnostic concepts or an explicit
mapping. The attached host Part and module-root child must also agree with
separately declared containment. An Attachment never implies a Joint; a
movable tail requires a separate Joint, while ears require no articulation in
this first envelope. These arrows express required functional
order/adjacency, not serialized syntax. Exact role spelling and serialization
remain spec detail.

This decision does not choose an exact permanent coordinate convention, numeric
ranges, surface primitives, the detailed source fields/schema, or a new
morphology family. The initial JSON encoding and structural-schema technology
are selected by DR-0012; their exact source fields and schema remain deferred
to that specification work.

### Stage 1 embodiment boundary

**Recommendation: Option 2 — source-linked semantic intent and lineage.**
Stage 1 must emit semantic joint frames and semantic region intent/lineage
linked to the resolved semantic graph. Stage 1 does not have to generate a
usable bone hierarchy, bind weights/skinning, analytic collision proxies, or
actual contact artifacts. Stage 2 generates a usable skeleton, skin weights,
and collision proxies and proves one shared pose/control scenario. Stage 3
owns actual contact, deformation, and runtime claims.

Stage 1 makes no animation, contact, deformation, or real-time-performance
claim. Exact representations, technologies, budgets, and backends remain
deferred.

### Fixture success and validity rule

**Recommendation: Option 2 — every declared valid-supported fixture must pass.**
Every declared valid-supported fixture must meet every mandatory Stage 1
structural check and the recorded subjective visual floor for the Stage 1 gate.
A failed or inconclusive valid-supported fixture means the gate has not passed,
while remaining useful evidence that must stay visible. A non-success fixture
must produce its expected outcome and diagnostic and is not counted as a valid
pass fixture. The frozen fixture outcome taxonomy is valid-supported,
semantically invalid, or
well-formed-but-unsupported. Every semantically invalid or unsupported fixture
freezes its expected primary diagnostic class/code; both are diagnostic
evidence, not Stage 1 success population.

## Consequences

- Surface and semantic experiments use a fixed, varied target rather than a
  disguised single template.
- Required modules and named optional sockets provide a stable semantic scope
  while leaving later families and detailed anatomy open.
- Required articulation is now typed and directed: each Joint has exactly one
  proximal and one distal Part, and the resolved graph owns endpoint-frame
  records in the corresponding Part local bases with provenance. Terminal
  paw-base landmarks or Sockets do not create hidden joints.
- Optional ear/tail composition uses Socket-to-Socket Attachment; a movable
  tail requires a separate Joint, preserving the distinction between
  composition and articulation.
- Every embodied Part has one explicit root containment path, including
  optional module Parts; relations cannot repair containment, and containment
  alone owns reference-transform inheritance. Stage 1 required Joint edges
  connect structural parents to immediate children.
- Attachment placement permits a mating Socket owned by any Part in the
  attached module-root containment subtree. The module-root-to-Socket-owner
  containment transform is composed with the owner-local Socket frame before
  inversion/alignment; the result is the root's sole resolved child-local
  containment placement. Descendants inherit only through containment, and no
  parallel Attachment transform path exists. Competing authored root-local
  placement compares with that same canonical value and retains provenance.
  A normalized module-instance declaration makes module presence, optionality,
  root Part, instance anchor, and Attachment-required state observable without
  creating another graph concept. A present module root has exactly one
  incoming Attachment, an absent optional module has none, and each Socket has
  total active capacity one across host and mating roles. Repeated endpoint
  pairs, host reuse, mating reuse, cross-role reuse, zero incoming, multiple
  incoming, detached, cyclic, or containment-disagreeing composition is
  invalid; diagnostics remain deterministic and distinct or explicitly mapped.
  Every Attachment transform is finite, non-degenerate, and invertible under
  the declared profile; source violations are semantic `invalid-source` with
  preserved provenance, while implementation failure on admissible transforms
  is `internal-failure`.
- Continuous variation can expose generator failures without turning each
  fixture into a bespoke asset.
- Stage 1 can preserve embodiment lineage and regions without bringing Stage 2
  animation or Stage 3 contact/deformation infrastructure into the first
  generation proof.
- Stage 1's mandatory embodiment outputs are semantic joint frames and
  semantic region intent/lineage; usable skeletons, skin weights, collision
  proxies, actual contact artifacts, and later claims are deferred to their
  owning stages.
- Fixture hypotheses can be chosen before exact freezing, but EXP-0001 cannot
  execute or contribute evidence until stable IDs, concrete inputs,
  discriminating parameters, seed/configuration, provenance, validity
  classification, expected outcome, and expected primary diagnostic class/code
  for every non-success fixture are frozen.
- Every declared valid fixture is part of the Stage 1 gate; failed and
  inconclusive fixtures remain visible and prevent continuation. Only
  valid-supported fixtures count toward Stage 1 success; semantically invalid
  and well-formed-but-unsupported fixtures are diagnostic evidence.
- The three-way Stage 1 taxonomy does not absorb admission, parser/schema,
  dependency, configured resource-limit, or internal/compiler-invariant
  operation failures; those use the closed DR-0012 status set.
- Plantigrade, quadruped, winged, extra-limb, and arbitrary-anatomy support
  remain future decisions and must not be inferred from this family.

## Alternatives Considered

### Option 1: Bounded stylized digitigrade furry biped

This provides recognizable furry character structure, useful proportion
variation, and a manageable semantic module set for the first native proof.
**Recommendation: Option 1 — a bounded stylized digitigrade furry biped.**

### Option 2: Bounded plantigrade furry biped

This would simplify foot-ground assumptions and could be a useful later family,
but it does not test the selected digitigrade body plan and would broaden the
first morphology decision if both were supported.

### Option 3: Narrow near-human template

This could simplify rigging and shared poses, but risks proving a disguised
template rather than a procedural family with meaningful variation.

### Option 4: Multi-family grammar now

This could demonstrate broader ambition early, but would multiply invalid
assemblies, fixture obligations, and surface/semantic failure modes before the
first family is understood.

### Stage 1 embodiment alternatives

#### Option 1: Geometry and labels only

This would minimize Stage 1 output, but would leave semantic joint-frame and
region intent/lineage untested; Stage 2 would need to infer or recreate the
links from geometry and labels.

#### Option 2: Intent-only, source-linked semantic intent and lineage

This intent-only Stage 1 boundary preserves source-linked semantic joint frames
and region intent/lineage for later embodiment without requiring a usable
skeleton, skin weights, collision proxies, or contact artifacts in Stage 1.
**Recommendation: Option 2 — source-linked semantic intent and lineage.**

#### Option 3: Generated embodiment artifacts in Stage 1

This would additionally generate a usable skeleton, skin weights, collision
proxies, and potentially contact artifacts in Stage 1. It could show more of
the end vision in one pass, but would move Stage 2 ownership into the
generation gate and conflate lineage with embodiment and interaction risks.
It is not selected.

### Graph-relation alternatives

#### Option 1: Binary typed edges only

This is compact, but cannot represent a joint with two endpoint frames, a
socket with host and mating roles, or a region spanning several owned parts
without hidden conventions.

#### Option 2: Reified semantic relations with role-labelled participation

This preserves one containment tree while allowing independently identified
joints, attachments, sockets, and regions to connect to several participants.
It retains solver and geometry neutrality. **Recommendation: Option 2.**

#### Option 3: Unrestricted hypergraph

This is maximally general, but would admit structures outside the first
morphology envelope and move validity and traversal complexity into the first
contract without evidence.

#### Option 4: Derive containment from typed relations

This would let a Joint or Attachment make an otherwise disconnected Part
reachable, but would make transform inheritance and root validity depend on
relation traversal order and relation kind. It is rejected: Part containment is
explicit, sole structural ownership; relation cycles and containment cycles
are checked independently.

### Articulation-lineage alternatives

#### Option 1: Opaque generator-owned articulation

This keeps the source smaller, but forces Stage 2 to invent articulation from
geometry and breaks the promised semantic lineage handoff.

#### Option 2: Minimum functional articulation and landmark roles

This supplies stable Stage 2 inputs without fixing a bone hierarchy, bone
count, limits, rigging technique, or anatomical-fidelity claim.
**Recommendation: Option 2.**

The selected roles are typed Joint and Part concepts rather than labels whose
meaning a resolver must infer. A directed proximal-to-distal endpoint rule
gives graphics and semantic consumers the same cardinality and frame handoff.
Treating a Socket-to-Socket Attachment as articulation, or treating a terminal
paw-base landmark/Socket as an implicit Joint, would reintroduce the ambiguity
that this bounded lineage is intended to remove; those alternatives are not
selected.

The resolved Joint owns one proximal-frame and one distal-frame record in the
corresponding Part local bases, and a Socket owns one interface frame in its
owning Part basis. Leaving those records as ambiguous source references would
allow graphics and runtime consumers to choose different owners or bases; that
alternative is rejected. Source references remain provenance, not competing
resolved records.

For Attachment composition, deriving placement only from an authored module
transform would permit it to disagree with host/mating Socket frames; deriving
it only from sockets would discard an explicit offset. The selected
host/frame + host Socket + optional offset + inverse mating Socket composition
retains both forms and rejects disagreement within the later-defined
tolerance. An Attachment is composition, never an implicit Joint.

The mating Socket need not be root-owned: a descendant-owned Socket is resolved
by composing the module-root-to-owner containment transform with the owner's
local Socket frame before inversion/alignment. The resulting root child-local
placement is the sole containment placement, so descendants inherit only via
containment. Reusing a host Socket, repeating an endpoint pair, omitting the
incoming Attachment for a present module root, or adding a second incoming
Attachment is rejected rather than left to traversal order.

#### Option 3: Remove the Stage 1-to-Stage 2 lineage promise

This would make opaque modules coherent, but weakens the staged proof and
postpones the central shared-derivation question rather than testing it.

### Fixture-rule alternatives

#### Option 1: Partial-success continuation

The project could continue after only a subset of fixed valid fixtures passed,
reporting other fixtures as limitations. This would allow early progress but
would weaken the claim about the declared family and invite evidence-population
drift.

#### Option 2: All declared valid-supported fixtures must pass

Every declared valid-supported fixture meets every mandatory structural check
and the subjective visual floor; failed or inconclusive fixtures keep the gate
open. Semantically invalid and well-formed-but-unsupported fixtures fail their
frozen expected primary diagnostics without counting as valid passes.
**Recommendation: Option 2 — all declared valid-supported fixtures must pass.**

#### Option 3: Reclassify difficult fixtures after evaluation

The project could remove or reclassify a fixture after a failure or
inconclusive result. This would hide the variation the fixed set is intended
to test and make cross-stage evidence non-comparable. It is not selected.

## Adversarial Review Response

The Revision 1, Revision 2, and Revision 3 reviews
([authority](reviews/DR-0008-rev-03-review-01.md),
[second review](reviews/DR-0008-rev-03-review-02.md)), the Revision 4 reviews
([authority](reviews/DR-0008-rev-04-review-01.md),
[morphology](reviews/DR-0008-rev-04-review-02.md)), and the Revision 5 reviews
([contract](reviews/DR-0008-rev-05-review-01.md),
[graphics-system](reviews/DR-0008-rev-05-review-02.md)) remain preserved as
stale historical evidence.

The Revision 6 Double review is preserved as stale evidence at commit
`7dba9346c91c59ff99f10b94630690bf732d6b28`, with both independent passes
recommending **Revise** at **High** confidence. The exact-revision CK-KICK-012 Batch 5
Double review examined Revision 7 at commit
`a282dbabffd83afa4e62577086934d00f98e12c7`: the independent
[contract/schema/security pass](reviews/DR-0008-rev-07-review-01.md) recommended
**Revise** at **High** confidence, and the independent
[semantic-graph/graphics/runtime pass](reviews/DR-0008-rev-07-review-02.md) also
recommended **Revise** at **High** confidence.

The three Batch 5 findings in those exact-revision reviews motivated the
current CK-KICK-012 Batch 6 proposal text and are resolved across the current
records. This revision resolves the typed descendant-owned mating Socket
composition and exact Attachment cardinality; DR-0002 owns the source-set and
graph boundary, DR-0011 owns the linked typed Socket/frame vocabulary, and
DR-0012 owns linked status/bootstrap/resource details. Ben approved these F2–F3
resolutions in discussion on 2026-08-11. The exact Revision 8 Double review at
commit `c64b1b98948304d631eecea6a354c9e42c89c510` is stale historical evidence,
not a clean review or acceptance. Its independent [review 01](reviews/DR-0008-rev-08-review-01.md)
and [review 02](reviews/DR-0008-rev-08-review-02.md) both recommended **Revise**
at **High** confidence. The current Revision 9 Double review examined target
commit `88004388f9537a37617ae248bdaad4625e6f3f03`; [review 01](reviews/DR-0008-rev-09-review-01.md)
and [review 02](reviews/DR-0008-rev-09-review-02.md) both recommended **Revise**
at **High** confidence. Those ten artifacts and their five findings are now
stale historical evidence after the Revision 10 proposal change. Their
findings are dispositioned for the next review as follows: (1) total
status/completeness is owned by DR-0002/DR-0012 and cross-linked here; (2)
module-root observability and global cross-role Socket capacity are revised
here and in the normalized graph/vocabulary records; (3) Attachment transform
admissibility and source-versus-implementation mapping are revised here and
in DR-0002/DR-0011; (4) the four technical readiness gates are owned by
DR-0013; and (5) authoritative build/publication outcome and `output-failure`
are owned by DR-0013. The latter two are cross-links, not additional DR-0008
decisions. The fresh current Double review is complete at target commit
`b19adf76aad7d672c0871bd38fc34739f3f4ac39`: [review 01](reviews/DR-0008-rev-10-review-01.md)
recommended **Revise** at **Medium** confidence and [review 02](reviews/DR-0008-rev-10-review-02.md)
records **Ready for owner disposition** at **High** confidence with no
DR-0008-specific blocker. Applicable consolidated finding is C4; C1–C3 and
C5–C7 remain cross-cutting evidence owned by the linked records, chiefly
DR-0002/DR-0012/DR-0013. All seven consolidated current findings await Ben's
discussion and owner disposition; review completion is evidence, not a
clean review or acceptance. The three-way Stage 1
fixture taxonomy remains limited to admitted recognized semantic fixtures;
exact fixture files and expected codes, field spellings, tolerance,
canonical axes/units/rotation/scale/shear, conditioning, and fixture evidence
remain deferred. Owner approval remains Pending and Status remains Proposed;
Review status is Complete.
Only Ben may accept or reject this proposal.

## Implementation and Proof Obligations

- Define the family vocabulary, named sockets, module attachment semantics,
  ownership tree, reified relation concepts and role-labelled relations,
  invalid/unsupported assemblies, and deterministic variation inputs in the
  later body specifications.
- Specify the typed, directed axial, arm, leg, and optional-tail articulation
  roles, including the pelvis-owned root-reference frame, Part endpoints,
  proximal/distal cardinality, canonical owned endpoint-frame records in Part
  local bases with provenance, terminal paw-base landmark/Socket roles,
  Socket-to-Socket Attachment composition, and the single hock/ankle Joint per
  digitigrade leg. Preserve their semantic frames through Stage 1 lineage
  without implying a fixed rig, solver, bone count, limits, or
  anatomical-fidelity claim.
- Prove the explicit containment tree separately from typed relations: every
  embodied Part has one root path, containment owns reference-transform
  inheritance, required Stage 1 Joint edges join structural parents to
  immediate children, and attached module roots agree with separately declared
  host/child containment. Validate the normalized module-instance declaration
  (module, root Part, instance anchor/provenance, presence/optionality, and
  Attachment-required state) without adding an identity-bearing graph concept.
  Prove exactly one incoming active Attachment for each present module root,
  none for an absent optional module, and total active Socket capacity one
  across host and mating roles; distinguish repeated endpoint pairs, host
  reuse, mating reuse, cross-role reuse, zero incoming, and multiple incoming
  cases with deterministic diagnostics or explicit mapping. Nested modules
  require distinct Socket instances.
- Define and test Attachment placement using `T_A←B` (coordinates expressed in
  B mapped into A), H/R/M and `S_h`/`S_m` as the typed Part/frame names, and
  `T_H←R = T_H←S_h · O_(S_h←S_m) · (T_R←M · T_M←S_m)^−1`, where O maps
  mating-Socket coordinates into host-Socket coordinates. Verify that the
  result is the root's sole child-local containment placement, descendants
  inherit only via containment, authored root-local placement is compared to
  that same canonical value within tolerance, and provenance for all
  inputs/composition remains. Every transform entering composition must be
  finite, non-degenerate, and invertible under the declared profile; source
  violations map to semantic `invalid-source` with deterministic
  diagnostic/provenance, while failure on an admissible transform maps to
  `internal-failure`. Exact representation, scale/shear, conditioning,
  comparison tolerance, matrix layout, and serialization remain
  resolver-activation prerequisites or deferred specification details.
  Include invalid endpoints, detached/multiply attached roots, and Attachment
  cycles.
- Define declared units and coordinate basis, explicit local frames and
  resolved transforms, and structured diagnostics without locking a permanent
  coordinate convention or exact numeric ranges here.
- Select hypotheses and intended discriminating profiles before exact freeze,
  then freeze stable fixture IDs, concrete source inputs, discriminating
  parameters, seed/configuration, provenance, one of valid-supported,
  semantically invalid, or well-formed-but-unsupported, and the expected
  primary diagnostic class/code for every non-success fixture before EXP-0001
  execution or evidence; this proposal does not create fixture files.
- Evaluate all fixed qualitative profiles through the same grammar and
  generators, recording bespoke correction attempts as failures rather than
  silently adding exceptions.
- Prove semantic lineage, joint frames, and region intent through Stage 1
  evidence; generate usable skeletons, skin weights, and collision proxies and
  evaluate the shared pose/control scenario in Stage 2; reserve actual contact
  and deformation/runtime claims for Stage 3.
- Freeze the cross-DR fixture matrix covering durable identities, typed
  articulation endpoints, measurement/frame cases, expected outcomes, and
  diagnostics before treating implementation evidence as proof.
- Defer exact ratios and numeric ranges, surface primitives and geometry method,
  detailed source fields/schema, permanent coordinate convention, rigging
  technique, runtime backend, budgets, new morphology families, and future
  compatibility refinements to evidence and their own decisions. The initial
  encoding, compatibility recognition, and structural-schema technology are
  owned by DR-0012.

## Canonical Design Links

- [Vision and scope](../product/vision-and-scope.md)
- [Product requirements](../product/requirements.md)
- [Authoritative semantic source set](DR-0002-declarative-body-document-source-of-truth.md)
- [Durable semantic and artifact/build identity](DR-0006-durable-semantic-and-artifact-identity.md)
- [Normative specification boundary](../../spec/README.md)
- [Architecture index](../architecture/README.md)
- [Open research questions](../research/open-questions.md)
- [Round 5 and later plan](../project/kickoff-plan.md)

## Reversibility and Revisit Triggers

Revisit the family if fixed-fixture evidence shows that the required modules
cannot produce coherent connected surfaces, semantic regions, or useful
variation without bespoke corrections. Revisit the envelope if continuous
variation repeatedly exceeds the evidence-supported grammar or if a deferred
family becomes necessary for the product target. Revisit Stage 1 hooks if they
cannot preserve lineage or provide useful inputs to Stage 2; do not expand them
into animation or interaction claims without a separate decision.

# Provisional morphology-knowledge inventory and pilot dossiers

Status: Provisional research input

This record is retained research context only from the prior anatomy-focused
work after the bounded Godot feasibility checkpoint was dispositioned. It is
deliberately small: a source-backed inventory of functional coverage and
exactly two pilot dossiers. It does not authorize or prepare current
implementation; the [Active runway](../project/status.md#active-runway) is the
sole source for the current stop state and any continuation. It is not a
schema, roadmap, architecture, supported-morphology promise, or executable
truth.

## Evidence posture

### Source-backed observations

The following open references are used for broad orientation only:

- [Jones et al., mammalian thoracolumbar regionalization](https://pmc.ncbi.nlm.nih.gov/articles/PMC6240174/)
  supports treating the axial chain as regionally differentiated rather than
  as one uniform rod.
- [Lewis et al., human pelvis structure and function during gait](https://pmc.ncbi.nlm.nih.gov/articles/PMC5545133/)
  supports keeping pelvic structure and locomotor function visible when
  considering the trunk-to-limb transition.
- [Stark et al., a 3D musculoskeletal model of the dog](https://pmc.ncbi.nlm.nih.gov/articles/PMC8166944/)
  supports distinguishing connected masses, attachments, and articulated
  segments in a locomotor body model.
- [Chi and Roth, scaling and mechanics of carnivoran footpads](https://pmc.ncbi.nlm.nih.gov/articles/PMC2894873/)
  supports footpad/contact geometry, stiffness, and load mechanics in
  digitigrade locomotion as body size changes.
- [Barr, *Superquadrics and Angle-Preserving Transformations*](https://authors.library.caltech.edu/records/rtr62-f2882)
  supports a compact parametric vocabulary for oriented, rounded, non-circular
  masses and useful transformations.

These sources support broad regionalization, mass/attachment distinction,
gait/load relationship, digitigrade chain reasoning, and a compact parametric
mass vocabulary. They do not prescribe this project's hybrid biped, its
ratios, its geometry algorithm, or its future contracts. The existing
[procedural-surface references](references.md) remain available for surface
method questions; they do not supply anatomy facts here.

### Historical implementation observation and procedural inference

The bounded successor-v9 artifact
`authored-form-expressivity-exact-field-components-checkpoint-v2` and Ben's
scoped appraisal are recorded in [project status](../project/status.md) as
historical prior-candidate evidence. That artifact shows that its stations
and controls covered the required body regions while the resulting skin still
lost the neck and read as blocky through the torso and pelvis. The provisional
implementation inference from that exact prior candidate was that mass
hierarchy, non-uniform section progression, and overly uniform or global
blending warranted investigation. This is not a source-backed anatomy claim
or proof that no further controls will be needed.

The following are procedural inferences for the two dossiers, not normative
geometry rules:

- Prefer main masses with deliberate orientation and non-circular profiles
  over a collection of spherical blobs.
- Route sections along curved anatomical paths where the assembly bends; do
  not assume every segment is a straight centerline.
- Control transition envelopes locally so shoulder, hip, neck, waist, axilla,
  and groin boundaries can remain legible.
- Preserve deliberate constrictions and negative spaces instead of allowing a
  global blend to fill them.
- Vary correlated per-profile relationships—mass widths, section progression,
  limb lengths, joint placement, and contact dimensions—rather than applying
  isotropic scale to one base body.

## Functional morphology-knowledge inventory

This is research coverage, not a data model or a required object hierarchy.
Optionality is part of the questions to cover: distinguish the required body
core from optional modules without deciding how either is represented.

| Coverage area | Minimum implementation-facing attention |
| --- | --- |
| Axial chain | Regional progression through torso, neck, and head; preserve readable changes in section and orientation. |
| Head, cranium, muzzle, and jaw | Keep the head mass distinct from the torso and retain a simplified muzzle/jaw read. |
| Neck | Test visibility, narrowing, and connectedness between head and thorax. |
| Thorax/ribcage | Treat the chest as a broad mass with deliberate orientation and a distinct shoulder-facing surface. |
| Abdominal/lumbar bridge | Preserve a non-uniform bridge and a possible waist rather than a single bean-like trunk. |
| Pelvis | Keep a distinct load-bearing/root mass with readable continuation into each hip. |
| Shoulder and hip transitions | Inspect attachment roots and negative spaces; avoid beads, melted roots, and inflated junctions. |
| Upper- and lower-limb chains and joints | Preserve differentiated segment lengths, bends, taper, and joint placement. |
| Simplified hand/foot paws and placement planes | Keep a terminal paw mass and a deliberate static placement plane; detailed digits and runtime contact are out of scope. |
| Optional ears and tail/root | Check presence, absence, and simple style variation as optional modules; do not expand the pilot count. |

## Frozen profiles and expectations

These five names are frozen for comparative anatomy inspection in this lane;
they do not freeze numeric ratios or activate support:

- `standard_neutral_reference`: neutral reference read; proportions and
  transitions should remain clear without a deliberately extreme build.
- `compact_broad_short_limb_large_head`: broad, compressed body read; short
  limbs and a large head must not collapse the neck or turn the torso into a
  rounded rectangle.
- `tall_narrow_long_legged`: narrow, elongated body read; long legs must keep
  articulated joints and deliberate static placement rather than becoming
  hoses.
- `slender_long_limb`: slender, long-limbed read; correlated taper and joint
  spacing must remain visible without a fragile chain of beads.
- `stocky_broad_chested`: heavy, broad-chested read; chest, pelvis, and hip
  roots must stay distinct instead of becoming one inflated mass.

Across all five, expect readable neck/head separation, intentional torso and
pelvis masses, shoulder/hip transitions, tapered limbs, and simplified muzzle
and paws/feet. Differences must be morphological relationships, not only
uniform scale.

## Selected pilot dossiers

Exactly two dossiers are selected. Each is a bounded research input for the
five-profile anatomy checkpoint, not a contract or an acceptance test.

### 1. Axial and upper-root assembly

**Scope.** A linked assembly of neck, ribcage, abdominal/lumbar bridge, and
pelvis as distinct masses. Include enough of the shoulder and axilla transition
to test whether the neck remains visible and whether the upper roots remain
connected without a swollen branch junction.

**Question.** Can the current controls produce a coherent axial hierarchy with
non-uniform section progression and preserved neck, waist, and axilla space?

**Procedure.** Inspect front, side, and three-quarter views for mass order,
curved section routes, local transition envelopes, and the negative spaces
around the neck and shoulder roots. Exercise each frozen profile through the
same operations. Record where a local change repairs a transition and where a
global blend changes unrelated regions.

**Expected evidence.** The head should not appear planted on the torso; the
neck should remain a visible connector; ribcage, abdominal bridge, and pelvis
should read as related but distinct; and shoulder/axilla transitions should
not erase the intended constriction.

### 2. Pelvic-to-planted-hind-paw assembly

**Scope.** A connected hind-limb chain of pelvis, hip, thigh, knee, shin, hock,
metatarsal, pad, simplified toe terminal, and static placement plane. Keep the
chain simplified and stylized, while retaining the digitigrade bend and a
readable planted terminal surface. Detailed toes, load behaviour, runtime
contact, and deformation are excluded.

**Question.** Can the pelvis-to-paw chain express correlated proportions,
joint bends, taper, and a deliberate planted silhouette without degenerating
into a hose with spherical joints or a club-shaped paw?

**Procedure.** Exercise the same chain across all five frozen profiles. Inspect
side and three-quarter views for hip-root separation, knee/hock placement,
metatarsal continuation, paw orientation, and consistency against the static
placement plane. Check that changing leg length or body build does not
isotropically enlarge every segment or erase the bend sequence.

**Expected evidence.** Pelvis and hip should remain identifiable; thigh, knee,
shin, hock, and metatarsal should read as a connected articulated progression;
the simplified paw terminal should align with a deliberate static placement
plane; and profile differences should alter relationships rather than only
scale.

## Failure signatures to retain

Treat these as observations to record against the candidate under inspection,
not as anatomy prescriptions:

- lost neck or head planted on torso;
- rounded-rectangle or bean-like torso or pelvis;
- shoulder or hip beads, or melted roots;
- hose-like limbs;
- joint beads;
- spherical or club-like paws;
- ring seams;
- success in only one view;
- five profiles differing only by uniform scale.

## Scope boundary

The lane covers simplified stylized anatomy for implementation-facing
inspection. It excludes detailed muscle, hands, face, tissue, species
taxonomy, and claims of executable anatomical truth. Any future geometry,
schema, supported-family, or architecture decision must be made by its
canonical owner and supported by appropriate evidence; this document does not
make that decision.

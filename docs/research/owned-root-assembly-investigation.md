# Owned root assembly investigation

Status: Frozen candidate implementation phase; Ben-authorized bounded
investigation; experiment-local and non-normative

This is the settled successor plan after the terminal seven-ring candidate in
the [programmatic root-complex investigation](programmatic-root-complex-surface-investigation.md).
It does not define product behaviour, a production surface contract, canonical
Regions or Sockets, a permanent topology, or a backend. It cannot satisfy or
replace the DR-0013 Stage 1 proof. DR-0009 and DR-0010 remain parked.

## Canonical metre repair evidence and boundary

The active authored input has been rebaselined to the repaired canonical metre
source. `examples/body-documents/stylized-digitigrade-biped-authored-form.json`
is 56,984 bytes with SHA-256
`82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14`. All 153
canonical dimensions are metres. Non-dimension transforms and landmarks are
unchanged. The provisional display adapter derives retained descriptor-local
integer `*_permille` fields explicitly; those fields are not authored dimension
units. Profile factors remain separate integer-permille display/profile inputs;
active generated-profile output applies them with exact decimal arithmetic,
quantizes to the nearest millimetre using ties-to-even, and emits canonical
metres.

The active candidate-table binding is
`experiments/current-form-surface-preview/structural_profile_candidates.json`
with SHA-256
`a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640`. This
paragraph records only the source/hash metadata rebaseline: standard-neutral
geometry was expected, and is now proven, to remain unchanged. Historical
source and evidence remain untouched. The successor-neutral implementation is
complete; exact-five activation and its later human checkpoint remain active.

## Research-question mapping

This unregistered exploratory experiment targets four canonical questions:

- `RQ-002`: whether the result reads as an intentional stylized creature
  character rather than an articulated blob;
- `RQ-012`: whether semantic fields, local coordinates, and part identity can
  remain explicit through construction and evaluation;
- `RQ-020`: whether an owned multi-chart welded surface is useful evidence for
  the still-open initial-surface representation choice; and
- `RQ-021`: whether the method can produce useful shoulder, hip, and branch
  junctions without a base mesh.

All four questions remain `Open` in the canonical [open-questions
registry](open-questions.md). This plan and any resulting evidence do not
change their lifecycle automatically.

## Question and bounded outcome

Can a single welded standard-neutral root surface make anatomical ownership
visible enough that the neck, shoulder/axilla, pelvis, and hip/thigh-root
transitions read as one intentionally constructed simplified humanoid form?

The candidate is successful only if fixed front, side, and three-quarter views
show all of these cues:

- a clear neck stem emerging from the thorax;
- shoulders departing below the neck rather than forming a superior shelf;
- readable axillary hollows and arm ports;
- a pelvis that wraps over each hip/thigh root; and
- thighs descending from beneath the pelvis rather than appearing as external
  bulbs.

These are bounded visual criteria for this investigation, not a product anatomy
promise. Structural metrics can reject a broken artifact, but they cannot
accept anatomical readability; direct main-thread vision remains authoritative.

## Settled candidate

Build one welded subdivision cage for the ribcage, neck root,
abdomen/lumbar bridge, pelvis, bilateral shoulder/axilla roots, and bilateral
hip roots. This candidate uses exactly eight named, nonempty experiment-local
domain interiors while retaining a hard cap of no more than eight:

1. thorax;
2. neck root;
3. abdomen/lumbar bridge;
4. pelvis;
5. left shoulder/axilla root;
6. right shoulder/axilla root;
7. left hip root; and
8. right hip root.

The candidate has five open ports: neck, left arm, right arm, left thigh, and
right thigh. Freeze one profile-independent topology with at most 128 controls
and 120 base quads, two subdivision levels, oriented port boundaries, and
declared interface cardinality before rendering. Use existing authored
`neck_upper` and `upper_abdomen` controls. The exact topology, chart degrees,
port orientations, extraordinary placement and valence, continuity tolerances,
normal/fold bounds, and subdivision support are frozen in the required design
contract before coordinates or images are judged.

Each domain owns its interior faces and controls. Each declared junction is the
single construction owner of its shared boundary and records all incident
domains; the boundary is represented once, with no overlapping skins that
merely happen to coincide. Domains, charts, ports, and junctions are ephemeral
experiment records, not canonical anatomy IDs.
The frozen design must enumerate every base face and control owner, every
junction adjacency and its incident domains, and every domain's nonempty
interior. It rejects any domain interior that crosses a required neck,
shoulder/axilla, abdomen/thorax, abdomen/pelvis, or pelvis/hip anatomical
boundary instead of representing that boundary through a declared junction.

## Three distinct layers

Keep these responsibilities separate and test them separately:

1. **Construction ownership** assigns every base face, interior control, and
   shared junction boundary to exactly one domain or declared junction.
2. **Semantic causality** carries authored addresses and roles through derived
   parameters, bindings, and subdivision stencils to the generated controls
   and evaluated vertices.
3. **Evaluated-surface lineage** records the domain/chart contributors and
   local coordinates of the actual evaluated surface, including legitimate
   multi-domain junction contribution.

Every output control and evaluated vertex must be owned or have a declared
junction/contributor record. A categorical ownership-colour view may help a
human inspect lineage, but colour must never stand in for causality,
ownership, or geometry evidence. Direct skin and ownership diagnostics must
render the same evaluated surface; there is no hidden second skin or
render-only correction.

## Required design contract

The required sole freeze artifact for the candidate design is
`experiments/owned-root-assembly-successor/design-contract.md`. Its exact raw
bytes are frozen and SHA-256-bound at
`3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490`, recorded
by the existing
`experiments/owned-root-assembly-successor/design-contract.sha256` sidecar,
which records that matching contract SHA-256. The implementation README records
two completed independent FREEZE reviews. The builder must require that
identity and reject a missing file or any mismatch before admitting inputs or
producing output. This paragraph originally described the pre-implementation
state; the bounded standard-neutral implementation is now complete at
`correction_round=0`, with its authoritative evidence and remaining work
recorded in the experiment README and `docs/project/status.md`. This research
record remains experiment-local, non-authoritative evidence and direction
context.

The frozen design contract covers every item in the preflight below and sets
finite caps for total junction count and interface cardinality; chart, formula,
and dependency counts; candidate special cases; and non-test implementation
and test LOC. This plan intentionally does not invent those numeric values.

## Frozen preflight and evidence gates

Before geometry rendering, freeze the standard-neutral inputs, oriented
interface curves and cardinality, patch layout and degree, port orientation,
extraordinary placement/valence, positional continuity, evaluated normal/fold
bounds, declared subdivision rule/support, causality matrix, and locality
perturbations. The candidate-specific anatomy measurements replace the old
misleading port-span gates:

- neck exposure and neck-stem emergence;
- shoulder descent below the neck;
- axillary concavity;
- pelvic wrap over each hip root; and
- downward thigh-root orientation.

The implementation must then prove, on the same evaluated surface:

- no unowned controls or faces and no duplicate hidden surface;
- every declared geometry-driving input has a downstream binding;
- each must-affect baseline-versus-perturbed run moves actual in-target
  evaluated vertex coordinates by at least its frozen scale-relative minimum,
  and the final mesh bytes serialize those changed coordinates;
- off-target evaluated coordinates remain within their frozen locality bound;
- metadata, provenance, dependency, or manifest movement without the required
  evaluated-coordinate and final-mesh movement fails the must-affect gate;
- shared boundaries are welded with bounded positional and normal/fold
  behaviour;
- ports, manifold topology, winding, degeneracy, clearances, and bounded
  self-intersection checks pass at the cage and both subdivision levels; and
- fresh-process output is byte-identical under the pinned launcher and two
  hash seeds.

The structural checks are necessary gates and evidence, not an aggregate visual
score. The fixed neutral views are inspected by the main thread before any
profile expansion.

## Execution order and stop rule

The work proceeds in this order; items 1 through 5 are complete and item 6 is
active:

1. audit the terminal candidate's utilities for representation-independent
   reuse;
2. verify the frozen, SHA-256-bound design contract and its successor-neutral
   topology, interfaces, dependencies, finite complexity caps, tolerances, and
   evidence views;
3. implement the bounded owned-domain/junction cage and the three-layer
   records;
4. run ownership, causality, locality, topology, geometry, determinism, and
   same-surface rendering checks;
5. inspect the fixed standard-neutral views in the main thread; and
6. only if neutral credibility passes, apply the unchanged candidate to the
   exact-five profile order and complete the required evidence.

The exact-five order is `standard_neutral_reference`,
`compact_broad_short_limb_large_head`, `tall_narrow_long_legged`,
`slender_long_limb`, and `stocky_broad_chested`. This order is an evidence
fixture, not a supported morphology promise.

Allow the initial implementation plus at most two shared correction rounds.
If the visual cues remain unclear, a gate fails, ownership is ambiguous, or a
correction requires a profile branch, hidden surface, render offset, solver,
global remeshing, or unclear junction ownership, reject this candidate. Do not
fall back automatically to another representation; a different representation
requires a newly recorded runway and human authorization.

The named human checkpoint is Ben's appraisal of the exact-five owned-root
assembly, using fixed front, side, and three-quarter final-surface renders,
only after the standard neutral passes the unchanged internal gates and the
exact-five evidence is generated. No internal metric, model review, or
standard-neutral result substitutes for that checkpoint.

## Reuse, exclusions, and authority

Reuse only representation-independent utilities after a focused audit and
independent tests. Archive or reimplement the seven-ring topology, ring and
branch formulas, correction macros, candidate IDs and thresholds, and
anatomy-specific tests by default. Do not transplant its ownership model just
because its mesh checks passed.

This plan excludes distal anatomy, tail work, exact-five generation before
neutral credibility, gallery work before viable evidence, rigging, weights,
shared pose, deformation, simulation, packaging, Godot or other engine work,
production dependencies, and activation of parked decision records. Generated
meshes, captures, caches, and other large binaries remain outside Git under the
existing artifact policy. The implementation, if authorized by this runway,
stays under `experiments/`; this research record remains evidence and
direction context only.

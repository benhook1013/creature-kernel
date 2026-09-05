# Owned-root assembly successor: candidate design contract

Status: Candidate freeze contract v2; experiment-local and non-normative

Experiment lifecycle: `planned`
Evidence closure: `open`
Technology outcome: `none`

This document is a second freeze candidate for one standard-neutral,
Alternative C owned-root assembly. It is not a product contract, canonical
anatomy specification, production geometry backend, supported morphology
promise, runtime skeleton, Stage 1 result, or human acceptance. It does not
activate DR-0009, DR-0010, or DR-0013. The contract has no self-referential
hash. The sidecar and final digest anchors are deliberately absent until this
candidate has passed fresh independent review.

The target is one welded surface for thorax, neck root, abdomen/lumbar bridge,
pelvis, bilateral shoulder/axilla roots, and bilateral hip roots. It excludes
the head, hands, feet, distal limbs, tail, posing, rigging, weights,
deformation, simulation, engine integration, packaging, and exact-five profile
expansion until this candidate clears its neutral gates.

## 1. Evidence status, authority, and stop rule

The preliminary disposable technical evidence passed all 39 implemented
harness gates for each of seeds 17 and 29. It is **not** a completed-contract
pass: it did not exercise the completed charts, all new anatomy gates,
structural floors, corrected tolerance `T`, corrected shared-index policy, or
human acceptance. It also did not produce the contract-bound 47-file output
inventory below. Harness invocation bugs consumed zero geometry-correction
rounds. The evidence is historical provenance, not an oracle or acceptance of
this candidate.

The current disposable evidence identities are:

```text
corrected runner:       5093de56ca1ecbacb1b59f9b6a95ca96808279d528ff7d5d7f01ae99c17a81e0
bundle manifest:         8ce3f556c1b51f0145cdca1b581474ee780b6d0d0ed146bc281ce205682083e2
threshold contract:      efd7b3d6cf94bca75c1ae93f0a7ddeb08be39f5a0f66484a05b0ea859da1a75c
two-level smoke report:  763d285ebc88aa577d02f9e7ef9b56f0203bd809d4794f6e6eb73291596cec36
seed-17 report:          370c4272e30678b4e07bbdd0bbf4501762813388737911f388fa0086a7c4db74
seed-29 report:          f88bc67c8db34b25a2b8c914bf1eb3540c48c0e147f21642153d5ab1f4e7e39
stable manifest:         f9c5422541911da2a0c5af901c18302f06ee31ee14307ea4416a2d9849bffd6a
coordinate manifest:     6c653300922f64454332a0c8888779d9fd90f1933edd35ccd110f738599ae974
gate manifest:           f8b406b0749ac94fd92cba7875adac294c85b298c68dcc12ed3e0f1537d0804d
causality manifest:      6885cf7ae4bb1eb05ca29c5dc92f358020ab36f3636470542a74fa9f3a9a817b
render manifest:          00288e0b1f7f7f5b298cc447c25f9c7b657f47f5b58fd5bbe436650b799311ba
level-2 PLY:             b092fbca5e62735743290f260fd94b5d9b8db5924ec25f9a7ae49e35d9572250
direct PNG:              066f0682135603fb3f250ffde73a0c8c39bcdffb6433eca441768267fd80490f
lineage PNG:             4f1ddafe67a8dee9eaf97f35e9b3095aba8cc1b71c8c690fc4b8966a164424cc
```

An exact geometry audit of the level-2 PLY identified above enumerated 17,832
triangle pairs with exactly one shared vertex. The exact cone-feasibility
classifier frozen in section 7 classified all 17,832 as point-only. The
rejected incomplete finite-axis certificate falsely rejected 258 of those
pairs: 246 were ordinary noncoplanar incident-fan cases and 12 were
near-coplanar; the exact audit found zero genuine overlaps. This is local
pre-freeze audit evidence about those exact PLY bytes, not completed
implementation evidence and not a claim that the future checker passes.

The pre-freeze quantitative hip-correction evidence is recorded against the
prospective `lambda_x=1.00` and lower-pelvis-z dependency. Pelvic lateral
ratios are `L0=1.5625`, `L1=1.339629214789240`, and
`L2=1.068201586498584`; the minimum thigh co-normal values are
`L0=0.8038497998`, `L1=0.8038497998`, and `L2=0.8027381422`. All unchanged
structural, continuity, anatomy, intersection, causality, locality, and
determinism gates pass these derived values. This is pre-freeze derived gate
evidence, not a result of a completed executable contract, and no gate is
loosened by it.

The unchanged standard-neutral axillary samples have topology-ordered
`turn_depth` values from `0.151710 m` through `0.165612 m` and
`path_stretch` values from `1.898909` through `2.338761`; both ranges pass the
section-8 bounds. The prior finite-chord predicate was invalid for valid
level-1 and level-2 topology-ordered hollows, not evidence of a geometry
failure. These ranges are scoped pre-freeze audit evidence, not completed
implementation evidence or premature exact-five evidence.

The historical bundle used an earlier tolerance literal and different output
names. It is not silently rewritten. The future builder MUST use the corrected
`T` below, the exact output names below, and rerun all evidence against this
contract. The future build MUST reject before source admission and before
creating output when contract identity, source identity, profile identity,
runtime identity, package allowlist, or any closed input rule fails.

Authority is separated as follows: `AGENTS.md` and applicable workflows govern
operation; `docs/research/owned-root-assembly-investigation.md` owns the
Ben-authorized experiment direction; this file owns this candidate's exact
topology, formulas, gates, artifacts, and finite budgets; code and evidence can
demonstrate or falsify it but cannot alter it.

The prospective initial freeze is `correction_round=0`. This present
pre-freeze candidate therefore records `correction_round=0` and the exactly
empty ledger `correction_ledger=[]`; no contract has frozen or built yet.
Resolving review findings before that first freeze does not consume a geometry
correction round. After the initial neutral build, at most two shared
correction rounds are available. The exact mutable formula-block registry is:

```text
formula.axial.j1.edge      section 4.2 executable E/u expression and d,n tunables
formula.axial.j1.interior  section 4.2 executable virtual-C/E/u expression and d,n tunables
formula.axial.station      section 4.2 executable midpoint/E/u expression and d,n tunables
formula.neck.stem          section 4.3 executable E/u expression and n tunable
formula.shoulder.left      section 4.4 executable inner/outer/depth/center/E expressions
formula.shoulder.right     section 4.4 executable inner/outer/depth/center/E expressions
formula.hip.left           section 4.5 executable B_s/D/M_x/H_c/H_s/J_x/J_f/J_b/J_s expressions
formula.hip.right          section 4.5 executable B_s/D/M_x/H_c/H_s/J_x/J_f/J_b/J_s expressions
```

The exact named candidate tunables inside those blocks are
`axial.j1_d=2.5`, `axial.station_d=1.5`, `axial.n=2.6`,
`neck.lateral_multiplier=2.0`, `neck.n=2.2`,
`shoulder.inner_base_depth_factor=0.75`,
`shoulder.outer_vertical_factor=0.5`, `shoulder.n=2.2`,
`hip.kappa_s=0.70`, `hip.lambda_x=1.00`, `hip.lambda_y=0.25`, and
`hip.lambda_z=0.20`. A permitted correction's substantive change is limited
to an executable expression or named tunable in this registry and its
mechanically derived section-4.6 dependency records; the mandatory
round/ledger update and later derived identity anchors are mechanical
consequences, not an expanded correction scope. A shared helper correction
names every formula ID whose coordinates or derivatives it changes.

The station-row assignments, side/index dispatch, source selectors, aliases,
prepared values, source/profile identities and hashes, and every
standard-neutral trial/source-derived literal printed in sections 2 and 4.5
are immutable inputs, not formula tunables. A correction cannot change them or
topology, IDs, construction ownership, ports, subdivision, source admission,
the renderer, artifacts, gates, thresholds, scope, or any allowlist.

Each permitted correction edits this contract, increments `correction_round`
by exactly one to 1 or 2, and appends exactly one record to
`correction_ledger`. A ledger record is a closed object with exactly these
keys and types:

```text
round: integer, exactly the new correction_round
prior_contract_sha256: lowercase 64-hex string
trigger_evidence: nonempty array of file_record, sorted by role_path
changes: nonempty array sorted by (formula_id,symbol), each exactly
         {formula_id: string, symbol: string,
          prior_literal_or_formula: string, corrected_literal_or_formula: string}
applicability: exactly {bilateral: boolean,
                        domains: sorted nonempty unique domain_id array}
invalidation: exactly "all older implementation and evidence is invalidated"
```

`file_record` is defined in section 10. A bilateral formula correction MUST be
one shared correction applied to both sides and name both domains in
`applicability`; no implementation-only or one-sided tuning is permitted.
Every corrected contract requires two fresh, independent reviews of its exact
bytes. Only after both reviews resolve to a freeze recommendation may the new
sidecar, the two independent code literals, and the README anchor be
materialized for the new SHA. Implementation validation and all seed-local and
pair evidence then rerun from scratch; older output cannot be carried forward.
A third correction or any change outside this boundary rejects the candidate
and requires a new runway. Render-only offsets, hidden/duplicate skin, profile
branches, a solver, remeshing, or threshold relaxation likewise reject it.

## 2. Source and prepared input

### 2.1 Immutable source inputs and fixed paths

The fixed repository-relative inputs are:

```text
contract:     experiments/owned-root-assembly-successor/design-contract.md
sidecar:      experiments/owned-root-assembly-successor/design-contract.sha256
source:       examples/body-documents/stylized-digitigrade-biped-authored-form.json
profile_table: experiments/current-form-surface-preview/structural_profile_candidates.json
```

At this candidate state the contract is the only one of these four files
changed by this documentation pass; the source and profile files are existing
immutable inputs, and the future sidecar is not yet created. The source and
profile identities currently bound to the evidence are:

```text
source bytes: 56984
source sha256: 82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14
profile bytes: 29970
profile sha256: a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640
```

The exact source basis is `length_unit=metre`, `handedness=right`, `up=+y`,
and `forward=+z`. Every admitted dimension is a canonical binary64 metre; no
`/1000` conversion is allowed. Non-dimension transforms and landmarks remain
unchanged by the metre repair. Source or profile byte drift rejects the build.

The profile table is admitted only to select and validate the named profile.
The selected profile is exactly `standard_neutral_reference`; every numeric
field in its closed `dimension_scales` object MUST be exactly `1000`, and those
values MUST drive no geometry, formula, threshold, topology, or renderer
choice. Profile identity and the excluded optional-module state are
non-geometric. No profile branch is admitted in this neutral build.

### 2.2 Closed prepared schema

The prepared schema ID is `owned-root-assembly-successor-prepared.v1`. Its
UTF-8 JSON object MUST contain exactly these top-level keys and no others:

```text
schema, contract, source, profile_selection, basis, parts, stations,
shoulders, hips, provenance
```

The exact nested shapes are:

`vector3` is the reusable runtime numeric type: an array of exactly three
finite IEEE-754 binary64 values in x,y,z order. At runtime every field declared
`binary64` MUST have exact Python type `float` and be finite; `bool` and `int`
are not runtime binary64 values. Either signed-zero float is admitted in
memory. Section 10.1 freezes its distinct schema-aware wire encoding and
decoding rules. This is a type alias only and adds no schema member.

```text
schema: string, exactly owned-root-assembly-successor-prepared.v1
contract: {path: string, sha256: lowercase 64-hex string}
source: {path: string, sha256: lowercase 64-hex string}
profile_selection: {
  profile_id: string,
  profile_table_path: string,
  profile_table_sha256: lowercase 64-hex string,
  dimensions: object with exactly the selected profile's closed
              dimension_scales key set, binary64 values, every value 1000
}
basis: {
  length_unit: exactly "metre", handedness: exactly "right",
  up: exactly "+y", forward: exactly "+z"
}
```

`parts` is an array of exactly seven objects, in the address order below.
Each object contains exactly `address` and `placement`. `address` is the
normalized four-item array `[namespace, anchors, kind, role]`; `anchors` is an
array of strings. `placement` is exactly
`{translation: vector3,
rotation_xyzw: [binary64,binary64,binary64,binary64]}`. The rotation MUST be
the runtime float tuple `(+0.0,+0.0,+0.0,1.0)`, whose section-10.1 canonical
wire array is exactly `[0,0,0,1.0]`; scale and shear fields are forbidden. A
nonidentity rotation is rejected before any world sum. A missing, unknown,
duplicate, or extra part rejects:

```text
["main",[],"part","pelvis"]
["main",[],"part","torso"]
["main",[],"part","neck"]
["main",["left"],"part","upper_arm"]
["main",["right"],"part","upper_arm"]
["main",["left"],"part","thigh"]
["main",["right"],"part","thigh"]
```

`stations` is an object with exactly the nine station keys listed in section
2.3. Each value is exactly `{owner: address_tuple, prefix: string,
C: vector3, rL: binary64, rA: binary64, rP: binary64}`.
`shoulders` has exactly `left` and `right`; each value is exactly
`{axilla: vector3, peak: vector3, arm_origin: vector3, start_lateral:
binary64, start_up: binary64, start_forward: binary64, shoulder_depth:
binary64}`. `hips` has exactly `left` and `right`; each value is exactly
`{P_s: vector3, r_x: binary64, r_y: binary64, r_z: binary64}`.
`provenance` is exactly `{source_files: array of exactly 2 objects}`. Each
source-file object is exactly `{path, sha256, bytes}`. No provenance records,
required-control aliases, non-geometric object, or other provenance member is
admitted. Unknown keys, empty provenance, or a source-file count other than
two reject.

The immutable raw source JSON has its own section-2.1 admission path and is
not a contract-owned canonical artifact. After selecting a raw source numeric
value, prepared-input construction MUST explicitly convert it to finite Python
`float` before assigning it to a `binary64` field. The section-10.1 rejection
of nonzero integer tokens in contract-owned binary64 fields does not reject an
otherwise admitted integer spelling in the raw source.

No prepared object may contain finished vertices, faces, edges, connectivity,
perimeters, point clouds, fields, masks, silhouettes, corrective offsets,
serialized prior output, or anything trivially reindexed into the candidate
cage. A derived scalar is admitted only when named below and bound to a source
selector. These rules prevent a skin or hidden geometry layer from bypassing
the owned root.

### 2.3 Exact semantic selectors and aliases

Before selecting any row, normalize its source address or owner with this
closed admission function:

```text
normalize_source_address(raw):
  require raw is an object with exactly the keys
          {namespace, anchors, kind, role}
  require namespace, kind, and role are nonempty strings
  require anchors is an array of strings, with no other element type
  return [namespace, anchors, kind, role]
```

The function rejects a missing key, an extra key, a wrong type, an empty
string, or a non-string anchor. It returns a new normalized JSON array and
never a source object or tuple. `A(role,side)` returns exactly that array:

```text
A(role, side=None) = normalize_source_address({
  "namespace": "main",
  "anchors": [] if side is None else [side],
  "kind": "part",
  "role": role
})
```

Every source selector first normalizes each candidate row's `address` or
`owner`, then compares normalized arrays for equality. This applies to
`part(A)`, `landmark(A,role)`, `dimension(A,role)`, selected landmark frame
owners, prepared addresses, `source_binding_record.source_addresses`, and all
containment and address sorting. Raw object member order, source-row identity,
or a host tuple representation never participates in equality or sorting.
`address_tuple` elsewhere in this contract means this normalized JSON array.

The source selectors are unique and fail closed. `part(A)` is the unique
`body.parts` row with address `A`; `landmark(A,r)` is the unique
`body.landmarks` row whose owner is `A` and role is `r`; and `dimension(A,r)` is
the unique `body.dimensions` row whose owner is `A` and role is `r`. Missing or
duplicate matches reject. Every dimension is finite, positive, and parsed
directly as binary64 metres.

World translations and landmarks are:

```text
W(pelvis)          = part(A("pelvis")).placement.translation
W(torso)           = W(pelvis) + part(A("torso")).placement.translation
W(neck)            = W(torso)  + part(A("neck")).placement.translation
W(upper_arm,side)  = W(torso)  + part(A("upper_arm",side)).placement.translation
W(thigh,side)      = W(pelvis) + part(A("thigh",side)).placement.translation
L(A,role)          = W(A) + landmark(A,role).position
```

`W(A)` means the world translation of the unique admitted part at address
`A`, using the exact containment-chain recurrence above; no other transform
composition is implied.

The nine exact station mappings are:

| station | owner | prefix |
| --- | --- | --- |
| `lower_pelvis` | `A("pelvis")` | `form_torso_profile_lower_pelvis` |
| `upper_pelvis` | `A("pelvis")` | `form_torso_profile_upper_pelvis` |
| `lower_abdomen` | `A("torso")` | `form_torso_profile_lower_abdomen` |
| `waist_abdomen` | `A("torso")` | `form_torso_profile_waist_abdomen` |
| `upper_abdomen` | `A("torso")` | `form_torso_profile_upper_abdomen` |
| `lower_ribcage` | `A("torso")` | `form_torso_profile_lower_ribcage` |
| `upper_ribcage_shoulder` | `A("torso")` | `form_torso_profile_upper_ribcage_shoulder` |
| `neck_collar` | `A("neck")` | `form_head_neck_profile_neck_collar` |
| `neck_upper` | `A("neck")` | `form_head_neck_profile_neck_upper` |

`upper_abdomen` and `neck_upper` are mandatory ordinary stations, not aliases
or optional controls, and each has its ordinary `C` and radius
`source_binding_record`s. For every selected landmark, frame admission is
closed as follows: pelvis and torso station landmarks require
`frame.role="form_torso_profile_control"`; neck station landmarks require
`frame.role="form_head_neck_profile_control"`; upper-arm `form_axilla` and
`form_shoulder_peak` landmarks require `frame.role="form_shoulder_control"`;
and thigh `form_leg_profile_thigh_start` landmarks require
`frame.role="form_leg_profile_control"`. The selected frame owner MUST
normalize to the landmark owner. A missing frame, an additional matching
frame, or a different frame role or owner rejects. Dimension rows have no
invented or inferred frame.

For each non-neck station, `C=L(owner,prefix)`, `rL=dimension(owner,
prefix+"_lateral_radius")`, `rA=dimension(owner,prefix+"_anterior_radius")`,
and `rP=dimension(owner,prefix+"_posterior_radius")`. For each neck station,
`C` and `rL` use the same rules while `rA=rP=dimension(owner,
prefix+"_forward_radius")`; the authored `*_up_radius` values remain
non-geometric.

For each side, the exact shoulder aliases are:

```text
axilla         = L(A("upper_arm",side), "form_axilla")
peak           = L(A("upper_arm",side), "form_shoulder_peak")
arm_origin     = W(upper_arm,side)
start_lateral  = dimension(A("upper_arm",side),
                           "form_arm_profile_upper_arm_start_lateral_radius")
start_up       = dimension(A("upper_arm",side),
                           "form_arm_profile_upper_arm_start_up_radius")
start_forward  = dimension(A("upper_arm",side),
                           "form_arm_profile_upper_arm_start_forward_radius")
shoulder_depth = dimension(A("upper_arm",side), "form_shoulder_depth_radius")
```

The exact hip aliases are:

```text
P_s = L(A("thigh",side), "form_leg_profile_thigh_start")
r_x = dimension(A("thigh",side),
                "form_leg_profile_thigh_start_lateral_radius")
r_y = dimension(A("thigh",side),
                "form_leg_profile_thigh_start_up_radius")
r_z = dimension(A("thigh",side),
                "form_leg_profile_thigh_start_forward_radius")
L_x = stations.lower_pelvis.C.x
L_y = stations.lower_pelvis.C.y
L_z = stations.lower_pelvis.C.z
R_x = stations.lower_pelvis.rL
R_f = stations.lower_pelvis.rA
R_b = stations.lower_pelvis.rP
```

`hip.origin`, `form_extent_y`, profile identity, basis labels, and excluded
module state are non-geometric source concepts and are not prepared fields.
The closed prepared component universe is the exact 92 scalar components in
section 2.4. The existing `<=96` complexity ceiling remains a cap, not
permission to admit an additional key.

### 2.4 Closed geometry-component bindings

The geometry-driving prepared-component universe contains exactly 92 canonical
component IDs and no others:

```text
stations.<station>.C.x, stations.<station>.C.y, stations.<station>.C.z,
stations.<station>.rL, stations.<station>.rA, stations.<station>.rP
  for station in the exact nine-station table order                  9*6 = 54

shoulders.<side>.axilla.{x,y,z}, shoulders.<side>.peak.{x,y,z},
shoulders.<side>.arm_origin.{x,y,z},
shoulders.<side>.start_lateral, shoulders.<side>.start_up,
shoulders.<side>.start_forward, shoulders.<side>.shoulder_depth
  for side in left,right                                            2*13 = 26

hips.<side>.P_s.{x,y,z}, hips.<side>.r_x,
hips.<side>.r_y, hips.<side>.r_z
  for side in left,right                                             2*6 = 12
                                                                    total = 92
```

Brace notation in this listing expands to separate dotted IDs. The nine
station names and their order are exactly those in section 2.3. Every
component has exactly one nonempty `source_binding_record`:

```text
{prepared_component: string,
 derivation_id: one of "source.dimension-value.v1",
                       "source.world-placement-axis-sum.v1",
                       "source.world-landmark-axis-sum.v1",
 source_addresses: nonempty sorted unique array of address_tuple,
 source_pointers: nonempty sorted unique array of canonical JSON-pointer string}
```

Arrays `body.parts`, `body.landmarks`, and `body.dimensions` are addressed by
their zero-based indices in the exact admitted raw source bytes. The decimal
index token is `0` or an unsigned base-10 integer without a leading zero. A
canonical pointer is an RFC 6901 pointer with `~` encoded as `~0`, `/` as
`~1`, no URI escaping, and no trailing slash. Let `p(A)`, `l(A,role)`, and
`d(A,role)` be the exact unique raw-array indices selected by `part`,
`landmark`, and `dimension` in section 2.3. Missing or duplicate selection
rejects before a pointer is emitted. Axis indices are exactly `x=0`, `y=1`,
and `z=2`. The pointer constructors are:

```text
placement_pointer(A,axis) =
  "/body/parts/" + decimal(p(A)) + "/placement/translation/" + axis_index
landmark_pointer(A,role,axis) =
  "/body/landmarks/" + decimal(l(A,role)) + "/position/" + axis_index
dimension_pointer(A,role) =
  "/body/dimensions/" + decimal(d(A,role)) + "/value"
```

The fixed containment chains, in summation order, are:

```text
pelvis:          [A("pelvis")]
torso:           [A("pelvis"), A("torso")]
neck:            [A("pelvis"), A("torso"), A("neck")]
upper_arm,side:  [A("pelvis"), A("torso"), A("upper_arm",side)]
thigh,side:      [A("pelvis"), A("thigh",side)]
```

For each station `C.axis`, use derivation
`source.world-landmark-axis-sum.v1`; its pointers are the same-axis placement
pointers for the station owner's complete containment chain followed by
`landmark_pointer(owner,prefix,axis)`. Shoulder `axilla.axis` and `peak.axis`
use the upper-arm chain followed by the corresponding landmark pointer. Hip
`P_s.axis` uses the thigh chain followed by the thigh-start landmark pointer.
For each shoulder `arm_origin.axis`, use
`source.world-placement-axis-sum.v1` and exactly the same-axis placement
pointers for the upper-arm chain, with no landmark pointer.

Every station radius, shoulder scalar, and hip radius uses
`source.dimension-value.v1` and exactly its unique section-2.3 dimension
pointer. `source_addresses` is the sorted unique set of every part address
whose placement, landmark, or dimension row contributes to those pointers:
the complete containment-chain address set for a world sum and exactly the
dimension owner's address for a scalar. Address tuples sort by their canonical
section-10.1 JSON bytes; pointers sort by UTF-8 bytes. Pointer arrays preserve
no summation order--the `derivation_id`, fixed chain above, and axis-specific
formula define that order.

Both input-manifest and causality-manifest contain the same 92 records, unique
by `prepared_component`, sorted by that string's UTF-8 bytes. Empty,
duplicate, missing, extra, differently derived, or pointer/address-inconsistent
records reject. Source/profile identities, exact indices, selectors, aliases,
and all 92 bindings are immutable across correction rounds.

### 2.5 Scalar arithmetic and historical input

Every scalar primitive uses binary64 round-to-nearest, ties-to-even after each
primitive operation, with no fused multiply-add. For noninteger `p`,
`sp(x,p)` computes `m=math.pow(abs(x),p)` using exactly CPython 3.10.12 under the identical
frozen runtime fingerprint, returns `+0.0` when `m==0.0`, otherwise returns
`m` when `x>=0.0` and `fl(-m)` when `x<0.0`. This is a same-runtime
determinism rule, not a universal libm claim. `lerp(a,b,t)=(1-t)*a+t*b` uses
the explicit primitive order in section 7. Signed powers MUST use `sp`; a zero
sign MUST never become negative zero by accident.

The verified standalone evidence inventory and its bundled copy were each
52,282 bytes and byte-identical. Their mutable temporary paths are historical
provenance only. The historical level-0/1/2 coordinate hashes were:

```text
level 0: add98870612d897648fd5db7fdb96939b943e844bfa97588772c418943ce45be
level 1: 4ff42e85144c287343687d91acdabc35c4e328ab0bfeca75d085428b43c654d9
level 2: d15bbd8bb7cab281417a85aec0e3371302448f7cbad89a9dae5a7ec537e4af33
```

Those hashes are historical disposable evidence, not a completed-contract
result. The contract-bound build may change them when scalar operation order,
three PLY serialization, or the shared-index policy is corrected.

## 3. Fixed topology and ownership catalog

### 3.1 Cells, domains, and counts

The surface is the boundary of 58 selected unit cubical cells in an integer
lattice. A cell is `(domain_id,i,j,k)` with `k in {0,1}`. The exact closed
`domain_id` set and domain order are:

```text
domain.pelvis, domain.abdomen, domain.thorax, domain.neck,
domain.left_shoulder, domain.right_shoulder, domain.left_hip, domain.right_hip
```

These eight strings are the only domain IDs. Short anatomical names remain
ordinary prose or source-role names only; no short alias is admitted in a
contract-owned serialized owner, contributor, incident-domain, or palette
field. Cells sort lexicographically within each domain in the order above.

The complete selected-cell inventory is:

```text
domain.pelvis:         (0,0,0) (0,0,1) (1,0,0) (1,0,1) (2,0,0) (2,0,1) (3,0,0) (3,0,1) (4,0,0) (4,0,1)
domain.abdomen:        (1,1,0) (1,1,1) (1,2,0) (1,2,1) (2,1,0) (2,1,1) (2,2,0) (2,2,1) (3,1,0) (3,1,1) (3,2,0) (3,2,1)
domain.thorax:         (1,3,0) (1,3,1) (1,4,0) (1,4,1) (1,5,0) (1,5,1) (2,3,0) (2,3,1) (2,4,0) (2,4,1) (2,5,0) (2,5,1) (3,3,0) (3,3,1) (3,4,0) (3,4,1) (3,5,0) (3,5,1)
domain.neck:           (2,6,0) (2,6,1)
domain.left_shoulder:  (0,4,0) (0,4,1) (0,5,0) (0,5,1)
domain.right_shoulder: (4,4,0) (4,4,1) (4,5,0) (4,5,1)
domain.left_hip:       (0,-1,0) (0,-1,1) (1,-1,0) (1,-1,1)
domain.right_hip:      (3,-1,0) (3,-1,1) (4,-1,0) (4,-1,1)
```

Each selected cell contributes six outward-wound unit faces. Faces used by two
selected cells are internal and omitted. Remove the five named port-cap face
sets:

```text
neck: 2 faces       left_arm: 4 faces       right_arm: 4 faces
left_thigh: 4 faces right_thigh: 4 faces
```

The un-capped exterior has 122 faces. The retained welded surface MUST have:

```text
controls=120, quads=104, edges=227, boundary_edges=38,
boundary_components=5, connected_components=1, Euler_characteristic=-3,
non_manifold_edges=0, directed_orientation_conflicts=0
```

All eight domains MUST be nonempty. Every retained base quad is one bilinear
`(1,1)` patch with four distinct control IDs in its listed outward-wound
cycle. A shared junction is represented once by indexed controls, not by
coincident duplicate surfaces.

The explicit `q000` through `q103` sequence printed in section 3.3 is the sole
level-0 face-order authority. Recomputing retained exterior faces from the
selected cells MUST produce a bijection to that catalog, and every recomputed
face MUST match its printed canonical owner and exact four-control cycle in
place; cyclic rotation and reversal are both forbidden. There is no secondary
coordinate, direction, cell, or implementation-native face sort. A use count
above two fails closed. A retained control with one incident face domain is
owned by that canonical domain ID. A control with two incident face domains
MUST match one of the seven junctions; three or more domains, no matching
junction, or no owner fails closed.

### 3.2 Control catalog

IDs are assigned by lexicographic lattice coordinate `(i,j,k)`. The following
is the complete control/owner catalog; `c000` is first and `c119` is last:

```text
c000@(0,-1,0):domain.left_hip       c001@(0,-1,1):domain.left_hip       c002@(0,-1,2):domain.left_hip
c003@(0,0,0):junction.pelvis__left_hip c004@(0,0,1):junction.pelvis__left_hip c005@(0,0,2):junction.pelvis__left_hip
c006@(0,1,0):domain.pelvis          c007@(0,1,1):domain.pelvis          c008@(0,1,2):domain.pelvis
c009@(0,4,0):domain.left_shoulder   c010@(0,4,1):domain.left_shoulder   c011@(0,4,2):domain.left_shoulder
c012@(0,5,0):domain.left_shoulder   c013@(0,5,2):domain.left_shoulder   c014@(0,6,0):domain.left_shoulder
c015@(0,6,1):domain.left_shoulder   c016@(0,6,2):domain.left_shoulder
c017@(1,-1,0):domain.left_hip       c018@(1,-1,2):domain.left_hip
c019@(1,0,0):junction.pelvis__left_hip c020@(1,0,2):junction.pelvis__left_hip
c021@(1,1,0):junction.pelvis__abdomen c022@(1,1,1):junction.pelvis__abdomen c023@(1,1,2):junction.pelvis__abdomen
c024@(1,2,0):domain.abdomen         c025@(1,2,1):domain.abdomen         c026@(1,2,2):domain.abdomen
c027@(1,3,0):junction.abdomen__thorax c028@(1,3,1):junction.abdomen__thorax c029@(1,3,2):junction.abdomen__thorax
c030@(1,4,0):junction.thorax__left_shoulder c031@(1,4,1):junction.thorax__left_shoulder c032@(1,4,2):junction.thorax__left_shoulder
c033@(1,5,0):junction.thorax__left_shoulder c034@(1,5,2):junction.thorax__left_shoulder
c035@(1,6,0):junction.thorax__left_shoulder c036@(1,6,1):junction.thorax__left_shoulder c037@(1,6,2):junction.thorax__left_shoulder
c038@(2,-1,0):domain.left_hip       c039@(2,-1,1):domain.left_hip       c040@(2,-1,2):domain.left_hip
c041@(2,0,0):junction.pelvis__left_hip c042@(2,0,1):junction.pelvis__left_hip c043@(2,0,2):junction.pelvis__left_hip
c044@(2,1,0):junction.pelvis__abdomen c045@(2,1,2):junction.pelvis__abdomen
c046@(2,2,0):domain.abdomen          c047@(2,2,2):domain.abdomen
c048@(2,3,0):junction.abdomen__thorax c049@(2,3,2):junction.abdomen__thorax
c050@(2,4,0):domain.thorax           c051@(2,4,2):domain.thorax
c052@(2,5,0):domain.thorax           c053@(2,5,2):domain.thorax
c054@(2,6,0):junction.thorax__neck  c055@(2,6,1):junction.thorax__neck  c056@(2,6,2):junction.thorax__neck
c057@(2,7,0):domain.neck             c058@(2,7,1):domain.neck             c059@(2,7,2):domain.neck
c060@(3,-1,0):domain.right_hip      c061@(3,-1,1):domain.right_hip      c062@(3,-1,2):domain.right_hip
c063@(3,0,0):junction.pelvis__right_hip c064@(3,0,1):junction.pelvis__right_hip c065@(3,0,2):junction.pelvis__right_hip
c066@(3,1,0):junction.pelvis__abdomen c067@(3,1,2):junction.pelvis__abdomen
c068@(3,2,0):domain.abdomen          c069@(3,2,2):domain.abdomen
c070@(3,3,0):junction.abdomen__thorax c071@(3,3,2):junction.abdomen__thorax
c072@(3,4,0):domain.thorax           c073@(3,4,2):domain.thorax
c074@(3,5,0):domain.thorax           c075@(3,5,2):domain.thorax
c076@(3,6,0):junction.thorax__neck   c077@(3,6,1):junction.thorax__neck   c078@(3,6,2):junction.thorax__neck
c079@(3,7,0):domain.neck             c080@(3,7,1):domain.neck             c081@(3,7,2):domain.neck
c082@(4,-1,0):domain.right_hip       c083@(4,-1,2):domain.right_hip
c084@(4,0,0):junction.pelvis__right_hip c085@(4,0,2):junction.pelvis__right_hip
c086@(4,1,0):junction.pelvis__abdomen c087@(4,1,1):junction.pelvis__abdomen c088@(4,1,2):junction.pelvis__abdomen
c089@(4,2,0):domain.abdomen          c090@(4,2,1):domain.abdomen          c091@(4,2,2):domain.abdomen
c092@(4,3,0):junction.abdomen__thorax c093@(4,3,1):junction.abdomen__thorax c094@(4,3,2):junction.abdomen__thorax
c095@(4,4,0):junction.thorax__right_shoulder c096@(4,4,1):junction.thorax__right_shoulder c097@(4,4,2):junction.thorax__right_shoulder
c098@(4,5,0):junction.thorax__right_shoulder c099@(4,5,2):junction.thorax__right_shoulder
c100@(4,6,0):junction.thorax__right_shoulder c101@(4,6,1):junction.thorax__right_shoulder c102@(4,6,2):junction.thorax__right_shoulder
c103@(5,-1,0):domain.right_hip       c104@(5,-1,1):domain.right_hip       c105@(5,-1,2):domain.right_hip
c106@(5,0,0):junction.pelvis__right_hip c107@(5,0,1):junction.pelvis__right_hip c108@(5,0,2):junction.pelvis__right_hip
c109@(5,1,0):domain.pelvis            c110@(5,1,1):domain.pelvis            c111@(5,1,2):domain.pelvis
c112@(5,4,0):domain.right_shoulder     c113@(5,4,1):domain.right_shoulder     c114@(5,4,2):domain.right_shoulder
c115@(5,5,0):domain.right_shoulder     c116@(5,5,2):domain.right_shoulder
c117@(5,6,0):domain.right_shoulder     c118@(5,6,1):domain.right_shoulder c119@(5,6,2):domain.right_shoulder
```

### 3.3 Face catalog

The complete retained face catalog is:

```text
q000 domain.left_hip [c000,c001,c004,c003]       q001 domain.left_hip [c000,c003,c019,c017]
q002 domain.left_hip [c001,c002,c005,c004]       q003 domain.left_hip [c002,c018,c020,c005]
q004 domain.pelvis [c003,c004,c007,c006]         q005 domain.pelvis [c003,c006,c021,c019]
q006 domain.pelvis [c004,c005,c008,c007]         q007 domain.pelvis [c005,c020,c023,c008]
q008 domain.pelvis [c006,c007,c022,c021]         q009 domain.pelvis [c007,c008,c023,c022]
q010 domain.left_shoulder [c009,c012,c033,c030]  q011 domain.left_shoulder [c009,c030,c031,c010]
q012 domain.left_shoulder [c010,c031,c032,c011]  q013 domain.left_shoulder [c011,c032,c034,c013]
q014 domain.left_shoulder [c012,c014,c035,c033]  q015 domain.left_shoulder [c013,c034,c037,c016]
q016 domain.left_shoulder [c014,c015,c036,c035]  q017 domain.left_shoulder [c015,c016,c037,c036]
q018 domain.left_hip [c017,c019,c041,c038]       q019 domain.left_hip [c018,c040,c043,c020]
q020 domain.pelvis [c019,c021,c044,c041]         q021 domain.pelvis [c020,c043,c045,c023]
q022 domain.abdomen [c021,c022,c025,c024]        q023 domain.abdomen [c021,c024,c046,c044]
q024 domain.abdomen [c022,c023,c026,c025]        q025 domain.abdomen [c023,c045,c047,c026]
q026 domain.abdomen [c024,c025,c028,c027]        q027 domain.abdomen [c024,c027,c048,c046]
q028 domain.abdomen [c025,c026,c029,c028]        q029 domain.abdomen [c026,c047,c049,c029]
q030 domain.thorax [c027,c028,c031,c030]         q031 domain.thorax [c027,c030,c050,c048]
q032 domain.thorax [c028,c029,c032,c031]         q033 domain.thorax [c029,c049,c051,c032]
q034 domain.thorax [c030,c033,c052,c050]         q035 domain.thorax [c032,c051,c053,c034]
q036 domain.thorax [c033,c035,c054,c052]         q037 domain.thorax [c034,c053,c056,c037]
q038 domain.thorax [c035,c036,c055,c054]         q039 domain.thorax [c036,c037,c056,c055]
q040 domain.left_hip [c038,c041,c042,c039]       q041 domain.left_hip [c039,c042,c043,c040]
q042 domain.pelvis [c041,c044,c066,c063]         q043 domain.pelvis [c041,c063,c064,c042]
q044 domain.pelvis [c042,c064,c065,c043]         q045 domain.pelvis [c043,c065,c067,c045]
q046 domain.abdomen [c044,c046,c068,c066]        q047 domain.abdomen [c045,c067,c069,c047]
q048 domain.abdomen [c046,c048,c070,c068]        q049 domain.abdomen [c047,c069,c071,c049]
q050 domain.thorax [c048,c050,c072,c070]         q051 domain.thorax [c049,c071,c073,c051]
q052 domain.thorax [c050,c052,c074,c072]         q053 domain.thorax [c051,c073,c075,c053]
q054 domain.thorax [c052,c054,c076,c074]         q055 domain.thorax [c053,c075,c078,c056]
q056 domain.neck [c054,c055,c058,c057]           q057 domain.neck [c054,c057,c079,c076]
q058 domain.neck [c055,c056,c059,c058]           q059 domain.neck [c056,c078,c081,c059]
q060 domain.right_hip [c060,c061,c064,c063]      q061 domain.right_hip [c060,c063,c084,c082]
q062 domain.right_hip [c061,c062,c065,c064]      q063 domain.right_hip [c062,c083,c085,c065]
q064 domain.pelvis [c063,c066,c086,c084]         q065 domain.pelvis [c065,c085,c088,c067]
q066 domain.abdomen [c066,c068,c089,c086]        q067 domain.abdomen [c067,c088,c091,c069]
q068 domain.abdomen [c068,c070,c092,c089]        q069 domain.abdomen [c069,c091,c094,c071]
q070 domain.thorax [c070,c072,c095,c092]         q071 domain.thorax [c071,c094,c097,c073]
q072 domain.thorax [c072,c074,c098,c095]         q073 domain.thorax [c073,c097,c099,c075]
q074 domain.thorax [c074,c076,c100,c098]         q075 domain.thorax [c075,c099,c102,c078]
q076 domain.thorax [c076,c077,c101,c100]         q077 domain.neck [c076,c079,c080,c077]
q078 domain.thorax [c077,c078,c102,c101]         q079 domain.neck [c077,c080,c081,c078]
q080 domain.right_hip [c082,c084,c106,c103]      q081 domain.right_hip [c083,c105,c108,c085]
q082 domain.pelvis [c084,c086,c109,c106]         q083 domain.pelvis [c085,c108,c111,c088]
q084 domain.pelvis [c086,c087,c110,c109]         q085 domain.abdomen [c086,c089,c090,c087]
q086 domain.pelvis [c087,c088,c111,c110]         q087 domain.abdomen [c087,c090,c091,c088]
q088 domain.abdomen [c089,c092,c093,c090]        q089 domain.abdomen [c090,c093,c094,c091]
q090 domain.thorax [c092,c095,c096,c093]         q091 domain.thorax [c093,c096,c097,c094]
q092 domain.right_shoulder [c095,c098,c115,c112] q093 domain.right_shoulder [c095,c112,c113,c096]
q094 domain.right_shoulder [c096,c113,c114,c097] q095 domain.right_shoulder [c097,c114,c116,c099]
q096 domain.right_shoulder [c098,c100,c117,c115] q097 domain.right_shoulder [c099,c116,c119,c102]
q098 domain.right_shoulder [c100,c101,c118,c117] q099 domain.right_shoulder [c101,c102,c119,c118]
q100 domain.right_hip [c103,c106,c107,c104]      q101 domain.right_hip [c104,c107,c108,c105]
q102 domain.pelvis [c106,c109,c110,c107]         q103 domain.pelvis [c107,c110,c111,c108]
```

### 3.4 Junction and port catalog

There are exactly seven two-domain junctions. Junction IDs use the fixed
domain order. Each line freezes its canonical incident-domain pair and control
trace. Storage starts at the lexicographically least lattice endpoint, then
takes the lexicographically lesser neighbor first. This is a storage order,
not an outward-direction claim:

```text
junction.pelvis__left_hip [domain.pelvis,domain.left_hip]: [c003,c004,c005,c020,c043,c042,c041,c019]
junction.pelvis__abdomen [domain.pelvis,domain.abdomen]: [c021,c022,c023,c045,c067,c088,c087,c086,c066,c044]
junction.abdomen__thorax [domain.abdomen,domain.thorax]: [c027,c028,c029,c049,c071,c094,c093,c092,c070,c048]
junction.thorax__left_shoulder [domain.thorax,domain.left_shoulder]: [c030,c031,c032,c034,c037,c036,c035,c033]
junction.thorax__neck [domain.thorax,domain.neck]: [c054,c055,c056,c078,c077,c076]
junction.pelvis__right_hip [domain.pelvis,domain.right_hip]: [c063,c064,c065,c085,c108,c107,c106,c084]
junction.thorax__right_shoulder [domain.thorax,domain.right_shoulder]: [c095,c096,c097,c099,c102,c101,c100,c098]
```

The five open ports, their canonical construction-owner domains, declared
outward directions, and exact loops are:

```text
port.neck owner=domain.neck outward=+Y loop=[c057,c079,c080,c081,c059,c058] length=6
port.left_arm owner=domain.left_shoulder outward=-X loop=[c009,c012,c014,c015,c016,c013,c011,c010] length=8
port.right_arm owner=domain.right_shoulder outward=+X loop=[c112,c113,c114,c116,c119,c118,c117,c115] length=8
port.left_thigh owner=domain.left_hip outward=-Y loop=[c000,c001,c002,c018,c040,c039,c038,c017] length=8
port.right_thigh owner=domain.right_hip outward=-Y loop=[c060,c061,c062,c083,c105,c104,c103,c082] length=8
```

`junction_id` means exactly one of the seven IDs above. `construction_owner`
means exactly one of the eight section-3.1 `domain_id` values or one of those
seven `junction_id` values, as allowed by the owning catalog; no other string
is admitted. Every contract-owned serialized owner, face domain,
`contributor_domains`, and `incident_domains` value uses these canonical IDs.
A port owner is always the one canonical domain printed above and is never a
junction or a short alias.

Port direction MUST be proven by the loop-area and induced co-normal gates in
section 7, never by a label alone. Exactly 20 interior controls are extraordinary:

```text
valence 3: c006,c008,c109,c111
valence 5: c021,c023,c030,c032,c041,c043,c054,c056,c063,c065,c076,c078,
           c086,c088,c095,c097
```

No C1 or G1 claim is made at extraordinary controls or open ports.

## 4. Formula dispatch and source-derived coordinates

### 4.1 Exact disjoint dispatch

The dispatch is over the 120 retained control keys, never over an unretained
Cartesian lattice. Test each key in this order and reject a key that matches
zero or more than one rule:

```text
1. if j in {6,7} and i in {2,3}:
     family=neck; formula_id=formula.neck.stem
2. else if j in {4,5,6} and i in {0,1,4,5}:
     family=shoulder; side=left iff i in {0,1}, right iff i in {4,5}
     formula_id=formula.shoulder.<side>
3. else if j in {-1,0}:
     family=hip; side=left iff i in {0,1,2}, right iff i in {3,4,5}
     formula_id=formula.hip.<side>
4. else:
     family=axial; j=1 edge iff i in {0,5}
     j=1 interior iff i in {1,2,3,4}
     formula_id=formula.axial.j1.edge, formula.axial.j1.interior,
                or formula.axial.station for j>=2
```

There is no axial j=0 or axial j=6 rule. The only axial rows are:

```text
j=1 edge:      6 controls
j=1 interior: 10 controls
j=2:          10 controls
j=3:          10 controls
j=4:           4 controls
j=5:           4 controls
total:        44 controls
```

The family totals are neck 12, shoulder 32, hip 32, and axial 44. Each
control MUST have exactly one record with exactly these fields:

```text
control_id, lattice_key, formula_id, construction_owner,
index_parameters, geometry_dependencies, coordinate
```

`construction_owner` is the exact section-3.4 canonical owner for that
control and has no short alias. `coordinate` and every binary64 member of
`index_parameters` obey the section-2.2 runtime and section-10.1 wire rule.
geometry_dependencies contains prepared component keys only when the analytic
coordinate derivative for that record is nonzero. The contract hash and
formula ID bind formulas, constants, preconditions, and intermediate values;
they MUST NOT be redundantly or variably serialized into a formula record.
`coordinate` is the final finite base-control `vector3` before subdivision. The
closed dependency universe has exactly the 92 possible prepared-component IDs
defined in section 2.4, of which no more than 96 were allowed by the original
cap, and each record has at most 12 dependencies. A dependency list is sorted
and duplicate-free.

`index_parameters` is a closed object selected by formula family:

```text
axial:   {i: integer, j: integer, k: integer,
          u: binary64, q: binary64, d: binary64, n: binary64,
          station_selector: string}
neck:    {i: integer, j: integer, k: integer,
          u: binary64, q: binary64, n: binary64,
          station_selector: string}
shoulder:{i: integer, j: integer, k: integer, side: "left"|"right",
          a: binary64, v: binary64, q: binary64, sign: integer -1|+1}
hip:     {i: integer, j: integer, k: integer, side: "left"|"right",
          u: binary64, q: binary64}
```

The values are exactly those produced by sections 4.2 through 4.5 after every
stated binary64 rounding. Axial `station_selector` is exactly
`upper_pelvis`, `virtual.upper_pelvis_y__lower_abdomen`, `waist_abdomen`,
`upper_abdomen`, `lower_ribcage`, or
`virtual.lower_ribcage__upper_ribcage_shoulder` according to the frozen row
mapping. Neck `station_selector` is exactly `neck_collar` or `neck_upper`.
No other key, selector spelling, or family-specific payload is admitted.

### 4.2 Axial family

Define E componentwise with the binary64 operation rules in section 7:

```text
E(C,u,q,rL,rA,rP,n) =
  (fl(C.x + fl(rL * sp(u,2/n))),
   C.y,
   fl(C.z + fl((rA if q>=0 else rP) * sp(q,2/n))))
```

For axial records, `q=k-1`, `n=2.6`, and `u=fl((i-2.5)/d)`. Use `d=2.5` for
both j=1 cases and `d=1.5` for j>=2. Station selection is exact:

```text
j=1 edge:     upper_pelvis
j=1 interior: virtual station:
                 C.x=lower_abdomen.C.x
                 C.y=fl((upper_pelvis.C.y+lower_abdomen.C.y)/2)
                 C.z=lower_abdomen.C.z
                 all radii=lower_abdomen radii
j=2:           waist_abdomen
j=3:           upper_abdomen
j=4:           lower_ribcage
j=5:           componentwise midpoint of lower_ribcage and
               upper_ribcage_shoulder, each operation rounded
```

The j=1 edge record uses only upper-pelvis center and radii. The j=1 interior
record uses only lower-abdomen center and radii plus upper-pelvis center y. It
MUST NOT use unused upper-pelvis radii or center x/z.

### 4.3 Neck family

For `j=6` use `neck_collar`; for `j=7` use `neck_upper`:

```text
E(station.C, 2*(i-2.5), k-1,
  station.rL, station.rA, station.rP, 2.2)
```

Both neck depth values come from the authored `*_forward_radius` role. The
authored neck `*_up_radius` values, including the trial values 0.38 and 0.32,
are non-geometric and MUST NOT affect coordinates.

### 4.4 Shoulder family

For the left side use `i in {0,1}`, `a=1-i`, `sign=-1`; for the right use
`i in {4,5}`, `a=i-4`, `sign=+1`. Let `v=(j-4)/2` and `q=k-1`:

```text
inner = lerp(axilla, peak, v)
joint = arm_origin
outer = joint + (sign*start_lateral, (2*v-1)*start_up*0.5, 0)
inner_depth = 0.75*start_forward if v=0 else shoulder_depth
depth = (1-a)*inner_depth + a*start_forward
center = lerp(inner, outer, a)
point = E(center, 0, q, 0, depth, depth, 2.2)
```

The family does not imply that distal arms are in scope. Its exact
zero-coefficient-aware dependency rules are in section 4.6; a record MUST NOT
declare every family input as a dependency merely because the family names it.

### 4.5 Hip family

#### 4.5.1 Mutable executable formula block

For left use `u=i-1`; for right use `u=i-4`; in both cases `q=k-1`.

```text
kappa_s=0.70       lambda_x=1.00
lambda_y=0.25      lambda_z=0.20

B_s(u,q) = P_s + (u*r_x, 0, q*r_z)

D   = L_y - P_s.y
M_x = R_x - abs(P_s.x - L_x)
H_c = r_y + lambda_y*(D-r_y)
H_s = kappa_s*H_c
J_x = r_x + lambda_x*(M_x-r_x)
J_f = r_z + lambda_z*(R_f-r_z)
J_b = r_z + lambda_z*(R_b-r_z)
J_0z = lerp(P_s.z, L_z, lambda_z)
Q_z = fl(J_f*q) if q>=0 else fl(J_b*q)

J_s(u,q) = (P_s.x + u*J_x,
            P_s.y + H_s + (H_c-H_s)*(1-u*u),
            fl(J_0z + Q_z))
```

The port row depends only on `P_s`, `r_x`, and `r_z`. The junction row
depends only on `P_s`, `r_x`, `r_y`, `r_z`, lower-pelvis center x/y/z,
lower-pelvis lateral/anterior/posterior radii, and the four named constants.
It MUST NOT consume `hip.origin`, `form_extent_y`, profile identity, or a
basis value as a coordinate input.

#### 4.5.2 Immutable source-derived trial records

The standard-neutral trial source records are:

```text
lower_pelvis           C=(0,-0.45,0) rL=1.50 rA=0.85 rP=0.60
upper_pelvis           C=(0,-0.20,0) rL=1.35 rA=0.78 rP=0.56
lower_abdomen          C=(0, 0.25,0) rL=1.125 rA=0.68 rP=0.54
waist_abdomen          C=(0, 0.50,0) rL=0.875 rA=0.50 rP=0.40
upper_abdomen          C=(0, 0.80,0) rL=1.225 rA=0.725 rP=0.56
lower_ribcage          C=(0, 1.05,0) rL=1.45 rA=0.875 rP=0.675
upper_ribcage_shoulder C=(0, 1.95,0) rL=1.50 rA=0.90  rP=0.70
neck_collar            C=(0, 2.15,0) rL=0.42  rA=0.40  rP=0.40
neck_upper             C=(0, 2.55,0) rL=0.34  rA=0.33  rP=0.33
```

The trial hip values are `P_s=(-1,-1,0)/(1,-1,0)`, `r_x=0.32`, `r_y=0.28`,
`r_z=0.30`. The shoulder values are arm origins `(-1,2,0)/(1,2,0)`, axillae
`(-1.1,1.7,0)/(1.1,1.7,0)`, peaks `(-1.1,2.15,0)/(1.1,2.15,0)`, start
radii `(0.35,0.30,0.32)`, and `shoulder_depth=0.35`.

### 4.6 Exhaustive derivative dependency rules

The builder MUST publish the exact dependency list for every one of the 120
records. The following rules are exhaustive. A component is absent when its
coefficient is zero at the exact discrete index; no blanket family dependency
is allowed. For the hip-junction exception below, the frozen
`lambda_x=1.00` value is in force. `direct station E` applies to axial j=1
edge, axial j=2 through 4, and neck rows; j=1 interior and j=5 use their
explicit expansions below:

```text
direct station E(C,u,q,rL,rA,rP,n):
  always stations.<station_selector>.C.x,
         stations.<station_selector>.C.y,
         stations.<station_selector>.C.z
  include stations.<station_selector>.rL iff u != 0
  include stations.<station_selector>.rA iff q > 0
  include stations.<station_selector>.rP iff q < 0

axial j=1 interior:
  always stations.lower_abdomen.C.x, stations.lower_abdomen.C.y,
         stations.lower_abdomen.C.z, stations.upper_pelvis.C.y
  include stations.lower_abdomen.rL iff u != 0
  include stations.lower_abdomen.rA iff q > 0
  include stations.lower_abdomen.rP iff q < 0

axial j=5 virtual midpoint:
  always stations.lower_ribcage.C.x,
         stations.lower_ribcage.C.y,
         stations.lower_ribcage.C.z,
         stations.upper_ribcage_shoulder.C.x,
         stations.upper_ribcage_shoulder.C.y,
         stations.upper_ribcage_shoulder.C.z
  include stations.lower_ribcage.rL and
          stations.upper_ribcage_shoulder.rL iff u != 0
  include stations.lower_ribcage.rA and
          stations.upper_ribcage_shoulder.rA iff q > 0
  include stations.lower_ribcage.rP and
          stations.upper_ribcage_shoulder.rP iff q < 0

shoulder, a=0 (inner):
  include shoulders.<side>.axilla.{x,y,z} iff v < 1
  include shoulders.<side>.peak.{x,y,z} iff v > 0
  include shoulders.<side>.start_forward iff q != 0 and v = 0
  include shoulders.<side>.shoulder_depth iff q != 0 and v > 0

shoulder, a=1 (outer):
  always shoulders.<side>.arm_origin.{x,y,z},
         shoulders.<side>.start_lateral
  include shoulders.<side>.start_up iff v != 0.5
  include shoulders.<side>.start_forward iff q != 0

hip port, j=-1:
  always hips.<side>.P_s.{x,y,z}
  include hips.<side>.r_x iff u != 0
  include hips.<side>.r_z iff q != 0

hip junction, j=0:
  always hips.<side>.P_s.y, hips.<side>.P_s.z, hips.<side>.r_y,
         stations.lower_pelvis.C.y, stations.lower_pelvis.C.z
  include hips.<side>.P_s.x except when the complete x derivative cancels:
    side=left and u=-1, or side=right and u=+1
  include stations.lower_pelvis.rL, stations.lower_pelvis.C.x iff u != 0
  include hips.<side>.r_z, stations.lower_pelvis.rA iff q > 0
  include hips.<side>.r_z, stations.lower_pelvis.rP iff q < 0
```

Every j=5 virtual center or radius has exactly two nonzero `0.5`
source-component coefficients, one for `lower_ribcage` and one for
`upper_ribcage_shoulder`, before the usual `u`/`q` zero-coefficient rules for
radii are applied. No virtual center/radius or `station_selector` string may
appear in `geometry_dependencies`; only the canonical 92 section-2.4 IDs may
appear. Source placement components that fan out to several prepared
aliases are counted once as prepared component keys. This ledger is the sole
source of causality claims; metadata, labels, or observed movement cannot add
dependencies.

## 5. Ownership, charts, and junction continuity

Construction ownership, semantic causality, and evaluated-surface lineage are
three separate layers:

1. construction owns every domain interior, junction, control, and face;
2. semantic causality binds authored roles through derived values, formulas,
   and subdivision support; and
3. evaluated lineage records actual base-control contributors, source
   dependencies, domain/chart contributors, and face lineage.

Every control and face MUST have exactly one construction owner. Every
evaluated element MUST have lineage. A lineage colour or legend is a
diagnostic only and cannot prove causality. Direct and lineage renders MUST
consume the same evaluated arrays; lineage MUST NOT add, hide, or move skin.

### 5.1 Chart contract

There is one base chart per retained face: `chart.q000` through
`chart.q103`. For each face cycle `(U0,U1,U2,U3)`, its UVs are exactly:

```text
(U0,(0,0)), (U1,(1,0)), (U2,(1,1)), (U3,(0,1))
```

The chart owner is the face's canonical `domain_id`. Child corner order is
fixed by:

```text
M01=(U0+U1)/2  M12=(U1+U2)/2
M23=(U2+U3)/2  M30=(U3+U0)/2
C=(U0+U1+U2+U3)/4
s0=[U0,M01,C,M30]
s1=[U1,M12,C,M01]
s2=[U2,M23,C,M12]
s3=[U3,M30,C,M23]
```

Apply this rule recursively with exact reduced dyadic UVs. Child `sI` is
the child at parent corner `I`. IDs are:

```text
level 0 vertex: c000 through c119
level 1 vertex: vertex.L1.v0000 through vertex.L1.v0450
level 2 vertex: vertex.L2.v0000 through vertex.L2.v1736
level 0 face: q000 through q103
level 1 face: face.L1.q0000 through face.L1.q0415
level 2 face: face.L2.q0000 through face.L2.q1663
level 0 chart: chart.qNNN
level 1 chart: chart.qNNN/L1.sI
level 2 chart: chart.qNNN/L2.sI.sJ
```

Level-0 vertex and face IDs are exactly the section-3 catalog IDs. At each
derived level, vertex numbering resets to zero and follows the already-frozen
numeric vertex order in section 6. Derived face numbering likewise resets to
zero and follows the frozen child-emission order. `NNN` is exactly three ASCII
decimal digits, `MMMM` is exactly four ASCII decimal digits, and `I` and `J`
are each one ASCII digit in `0..3`; a transition level is one ASCII digit in
`0..2`. All literal punctuation, case, prefixes, and zero padding are exactly
as printed above; no alternative spelling, padding, alias, or
implementation-native identifier is admitted.

For base face `qNNN`, interpret `NNN` as its zero-based numeric face index.
Its level-1 child at corner `I` has numeric face index `4*NNN+I`, exact face ID
`face.L1.qMMMM`, and chart ID `chart.qNNN/L1.sI`. Its level-2 child at corner
`J` of that level-1 child has numeric face index `16*NNN+4*I+J`, exact face ID
`face.L2.qMMMM`, and chart ID `chart.qNNN/L2.sI.sJ`. `MMMM` is the four-digit
zero-padded spelling of the calculated index. This mapping is the executable
relation between child chart ancestry and numeric face IDs.

For each interior edge at a level, use the undirected key
`(lower_endpoint_id,higher_endpoint_id)`, where lower and higher mean numeric
vertex order at that level, never implementation string comparison. Its exact
`min(endpoint_id)` and `max(endpoint_id)` notation anywhere in edge or
transition processing means these same lower and higher numeric-order
endpoints, not lexical minimum or maximum. The exact
ASCII transition ID is the concatenation
`"transition/L" + decimal(level) + "/e" + lower_endpoint_id + "-" +
higher_endpoint_id`, using the exact endpoint spellings frozen above, with no
escaping, whitespace, padding change, or alternative separator. The source
chart is the lower numeric incident-face index at that level, and the
destination chart the higher; chart-string comparison is forbidden. In each
face, edge slot `r` is the directed pair
`face[r]->face[(r+1)%4]`; the destination slot MUST have reverse endpoint
order. Store source/destination chart, edge slots, endpoint IDs in ascending
numeric vertex order, `t_destination=1-t_source`, and `junction_id`.
Same-domain transitions use `junction_id=null`; a cross-domain transition
stores exactly one catalog junction ID and both incident domains in catalog
order.

At every level, each evaluated face has exactly one chart and base-face ancestor.
`chart_records` are authoritative face lineage: at level 0,
`base_face_id=face_id`; each child inherits its parent's `base_face_id` and
the construction-owner domain of that base face. No additional surface or
file lineage is permitted. Construction ownership, causal lineage,
contributor domains, and face/chart lineage remain distinct records and
claims.
Each evaluated vertex stores all incident `(chart_id,u,v)` records, sorted by
chart ID and then reduced dyadic `u,v`. Derived vertex IDs and numeric
order are the subdivision order in section 6. Child face IDs are emitted in
parent-face order and then parent corner order `0,1,2,3`.

The exact chart/transition counts are:

```text
                 level 0  level 1  level 2  total
charts               104      416     1664   2184
interior transitions  189      794     3252   4235
maximum chart samples/vertex: 5 at every level
```

### 5.2 Junction traces

For every junction, traces MUST be derived independently from each incident
domain's face/chart incidence. The two derived directions MUST be opposite.
Pair samples by exact dyadic transverse tags and require equal tags and IDs
before comparing coordinates. A junction residual MUST be at most `T` per
coordinate at levels 0, 1, and 2. Stored control order is never used as a
substitute for independently derived incidence traces.

The exhaustive junction map and transverse-tag rule are:

```text
junction.pelvis__left_hip          drop j; tag (i,k)
junction.pelvis__abdomen           drop j; tag (i,k)
junction.abdomen__thorax           drop j; tag (i,k)
junction.thorax__left_shoulder     drop i; tag (j,k)
junction.thorax__neck              drop j; tag (i,k)
junction.pelvis__right_hip         drop j; tag (i,k)
junction.thorax__right_shoulder    drop i; tag (j,k)
```

Initial tags are the indicated components of the exact section-3 lattice keys.
Subdivision propagates them as reduced dyadic values. Inherited boundary
vertices retain their tag; each inserted edge sample receives the exact
rational midpoint of its endpoint tags. The two incident canonical-domain
traces MUST be derived independently and produce equal tag/vertex sets in
opposite cyclic directions. Missing, duplicate, unequal, or differently
directed sets fail closed.

### 5.3 Executable ownership and lineage counts

The `unowned_elements` and `overowned_elements` invalid-count gates are
computed independently at every level from a closed, disjoint element
universe. Its keys are all expected vertices in that level's numeric order,
all expected faces in numeric face order, all topology-derived undirected
edges keyed by their lower and higher numeric vertex indices, and exactly one
boundary slot for each of the five catalog port IDs. At a conforming level its
cardinality is therefore:

```text
level 0: 120 vertices/controls + 104 faces + 227 edges + 5 boundary slots = 456
level 1: 451 vertices          + 416 faces + 870 edges + 5 boundary slots = 1742
level 2: 1737 vertices         + 1664 faces + 3404 edges + 5 boundary slots = 6810
```

The level-0 vertex keys are also the base-control keys, so a control is not
counted a second time. The level-0 face keys likewise represent the base
faces. This tagged union is the sole counting universe; an element can
contribute at most one to one of the two invalid counts at a level.
Any output identifier outside the exact section-5.1 level set is a hard
identifier/catalog failure and is never admitted as an alternate universe
element.

Base controls and base faces each require exactly one catalog-valid
construction-owner record. A base-control owner is either its exact catalog
domain or its exact catalog junction, including that junction's complete
incident-domain set. A base-face owner is its exact section-3 face-catalog
domain. A level-0 vertex/control element has both this construction-owner
obligation and the evaluated-vertex lineage obligation below; a derived vertex
has the lineage obligation only. For a level-0 face, the unique
chart/base-face ancestry record MUST exist and agree with that catalog owner.
Every level-1 or level-2 face MUST
have exactly one chart record whose section-5.1 numeric face ID, unique
base-face ancestor, and inherited construction-owner domain agree. That one
ancestry path is the evaluated face's construction ownership; contributor
lineage does not create another face owner.

Each topology-derived edge has exactly one derived classification record:

```text
one incident face:       boundary edge in exactly one propagated catalog port loop
two same-domain faces:   interior edge belonging to that one domain
two cross-domain faces:  edge in exactly one catalog junction and in that
                         junction's independently derived level trace
```

The three cases are mutually exclusive and are derived from face incidence,
face ancestry owners, propagated port loops, the junction catalog, and the two
independent junction traces rather than from a serialized edge-owner label.
Any other incidence or zero or multiple matching classifications is invalid.
For each boundary slot, its classification records are the actual one-face
boundary components whose canonically rotated, orientation-preserving numeric
vertex cycle exactly equals that propagated catalog port loop. Canonical
rotation starts at the cycle's lowest numeric vertex and does not reverse the
derived orientation. Requiring exactly one record in every port slot, together
with requiring every one-face edge to have exactly one port classification,
makes the actual boundary components and catalog ports bijective: a missing
port, duplicate component, unmatched component, or multiply matched component
cannot pass.

Every evaluated vertex requires exactly one `vertex_record` under its exact
section-5.1 ID. Its incident chart samples, base-control contributors,
geometry-dependency union, and contributor domains MUST be nonempty, complete,
and equal to the independently recomputed section-6 lineage. Multiple entries
inside the one catalog-order-unique `contributor_domains` array are valid
multi-domain evaluated lineage and never count as construction
over-ownership.

For each required obligation above, classify its candidate-record multiset as
`zero` when it is absent or its sole record is not catalog-valid, complete, and
equal to the independently derived value; `one` only when exactly one such
record exists and is valid; or `multiple` whenever more than one candidate
record exists, regardless of their contents. An element is counted once in
`overowned_elements` if any of its obligations is `multiple`; otherwise it is
counted once in `unowned_elements` if any obligation is `zero`; otherwise it
is valid. This precedence makes zero-versus-multiple handling deterministic
and prevents a face, edge, boundary slot, or vertex/control output from being
double-counted across the two aggregate invalid-count gates.

## 6. Subdivision, lineage, and finite formula ledger

Exactly two open-boundary Catmull–Clark levels are evaluated. The rules are:

```text
face point       = ordered mean of four face vertices in face-cycle order
boundary edge    = ordered midpoint of endpoint IDs
interior edge    = ordered sum of two endpoints and two face points, divided by 4
boundary vertex  = ordered (6*P + neighbor_1 + neighbor_2) / 8
interior vertex  = ordered (F + 2*R + (n-3)*P) / n
face emission    = (vertex, next-edge-point, face-point, previous-edge-point)
```

Boundary vertices MUST have exactly two boundary neighbours. Boundary loops
expand as `(vertex,next-edge-point)` while retaining orientation. No alternative
boundary rule, smoothing kernel, remesher, solver, optimizer, or post-build
correction is permitted.

```text
level 0: vertices=120, edges=227, quads=104, triangles=208, boundary_edges=38
level 1: vertices=451, edges=870, quads=416, triangles=832, boundary_edges=76
level 2: vertices=1737, edges=3404, quads=1664, triangles=3328, boundary_edges=152
```

The recurrence is `V'=V+E+Q`, `E'=2E+4Q`, `Q'=4Q`, `B'=2B`.

All displayed means and sums are componentwise. Every multiplication,
addition, subtraction, division, and square root is rounded binary64 after
the primitive, with no fused multiply-add. Face points use parent face order;
incident faces use ascending numeric face order; incident edges use ascending
numeric endpoint-index pairs. Numeric vertex order at each new level is:
updated parent vertices in parent order, edge points in sorted undirected-edge
order, then face points in parent-face order. Child faces are emitted in
parent-face order and corner order 0,1,2,3. Boundary-neighbor order is the
ascending numeric boundary-neighbor ID.

For an interior vertex P with n incident faces, F is the ordered componentwise
mean of its incident face points in ascending numeric face order. R is the ordered
componentwise mean of the endpoint midpoints of its incident edges in ascending
undirected-edge order. The interior update operation order is:

```text
t0 = fl(2*R)
t1 = fl(F+t0)
t2 = fl((n-3)*P)
P' = fl(fl(t1+t2)/n)
```

For a boundary vertex with ascending boundary neighbours N0 and N1:

```text
t0 = fl(6*P)
t1 = fl(t0+N0)
t2 = fl(t1+N1)
P' = fl(t2/8)
```

For an edge with endpoint IDs `e0<e1` in numeric vertex order, the boundary point is
`fl(fl(P0+P1)/2)`. An interior edge MUST have exactly two incident face
points `F0,F1` in ascending numeric face order and is evaluated componentwise in
this exact order:

```text
t0 = fl(P0+P1)
t1 = fl(t0+F0)
t2 = fl(t1+F1)
E' = fl(t2/4)
```

Thus the rule is exactly `(P0+P1+F0+F1)/4`; it is not the mean of an endpoint
midpoint and two face points divided by three. Every required incidence count
is checked before the update; absent or extra incidence is a hard failure.

Lineage MUST be deterministic. At level 0, each vertex's
`base_control_contributors` is the singleton containing its own control ID.
Each subdivision stencil propagates the sorted union of the contributing
records below. For every resulting vertex, `geometry_dependency_union` is
recomputed as the sorted unique union of the `geometry_dependencies` of its
contributing base controls, and `contributor_domains` is the catalog-order
unique domain union: a domain-owned base control contributes its singleton
domain, while a junction-owned base control contributes every domain in that
junction's catalog incident-domain list. The builder MUST recompute all three
serialized lineage values and reject any mismatch.

```text
boundary vertex = itself union two boundary neighbours
interior vertex = incident edge endpoints and incident face corners
edge point      = endpoints and all incident-face contributors
face point      = all four corner contributors
dependency      = union of dependencies of contributing base controls
face lineage    = parent face lineage repeated for four children, retaining
                  the parent's base_face_id and base-face construction owner
```

All lists use their declared order: base-control contributors and dependency
unions are sorted unique lists, while contributor domains use catalog-order
uniqueness. Level-2 hard ceilings are `<=20` base-control contributors,
`<=54` dependency-union keys, and `<=5` contributor domains per vertex.

The nine and only nine special-case IDs are:

```text
formula.axial.j1.edge
formula.axial.j1.interior
formula.neck.stem
formula.shoulder.left
formula.shoulder.right
formula.hip.left
formula.hip.right
topology.open-port-cap
topology.shared-junction
```

Their executable meanings are closed: the two axial IDs select the exact j=1
edge/interior formulas in section 4; the neck, shoulder, and hip IDs select
the listed domain formula records; topology.open-port-cap is the sole
operation that removes the five named cap face sets; and
topology.shared-junction is the sole operation that welds the seven catalog
junction traces and validates their two-domain ownership. These IDs are
ledger labels for these exact operations, not extension points. No unnamed
special case, macro, runtime fallback, or new topology decision is permitted.
Topology decision sites are capped at three: selected-cell admission,
port-cap removal, and owner/junction validation. A future implementation
publishes the IDs on every affected record and rejects any ID outside this
registry.

## 7. Corrected numeric tolerance, structural gates, and intersections

The fixed scale and roundoff tolerance are:

```text
S       = 0x1.c666666666666p+1 = 3.55 m
epsilon = 0x1.0000000000000p-52
T       = fl(fl(64*epsilon)*S)
        = 0x1.c666666666666p-45
        = 5.044853423896711e-14 m
```

The primitive operation order is closed:

```text
add3(a,b,c) = fl(fl(a+b)+c)
lerp(a,b,t):
  t0=fl(1-t); t1=fl(t0*a); t2=fl(t*b); result=fl(t1+t2)
dot(a,b) =
  fl(fl(fl(a.x*b.x)+fl(a.y*b.y))+fl(a.z*b.z))
cross(a,b) =
  (fl(fl(a.y*b.z)-fl(a.z*b.y)),
   fl(fl(a.z*b.x)-fl(a.x*b.z)),
   fl(fl(a.x*b.y)-fl(a.y*b.x)))
norm(v) = correctly-rounded binary64 sqrt(dot(v,v))
normalize(v) = v/norm(v); zero or non-finite norm rejects
```

All ordered sums start at +0.0 and use the stated order. No FMA is permitted.
For quad `(a,b,c,d)`, use triangles `(a,b,c)` and `(a,c,d)`:

```text
N0 = cross(b-a,c-a)
N1 = cross(c-a,d-a)
triangle_area_0 = fl(0.5*norm(N0))
triangle_area_1 = fl(0.5*norm(N1))
quad_area = fl(triangle_area_0+triangle_area_1)
full_quad_normal = normalize(N0+N1)
edge_length(a,b) = norm(b-a)
```

For an ordered loop p[0..n-1], centroid is the ordered componentwise sum
divided by n; area vector is the ordered sum of
`cross(p[i]-centroid,p[(i+1)%n]-centroid)` multiplied by 0.5; and planarity
residual is the maximum absolute dot product with the normalized area vector.
Zero or non-finite normals reject.

`fl` means binary64 round-to-nearest, ties-to-even. The preliminary evidence
used a different literal; that literal is historical and MUST NOT be reused.

The intersection constants are:

```text
I0 = 0x1.b7cdfd9d7bdbbp-34  # 1e-10, zero-shared AABB/SAT only
D  = 0x1.0000000000000p-46  # 64*epsilon, normalized degeneracy floor
```

Structural floors MUST be enforced rather than checked merely for positivity:

```text
                         level 0       level 1       level 2
minimum edge length       >=0.10 m      >=0.04 m      >=0.02 m
minimum triangle area     >=0.010 m2    >=0.002 m2    >=0.0005 m2
minimum quad area         >=0.010 m2    >=0.002 m2    >=0.0005 m2
```

At every level all values, normals, areas, and metrics MUST be finite. The
surface MUST be connected, orientable, outward-wound, non-manifold-free, and
free of accidental holes other than the five declared ports. Duplicate
controls, duplicate faces, degenerate faces, zero-length edges, unowned or
over-owned elements, and failed caps are hard failures.

`outward_wound` is the exact topological predicate: every level-0 face cycle
equals its section-3.3 printed cycle without rotation or reversal; every
two-face edge occurs in opposite directed order in its incident cycles; and
every one-face edge has the direction induced by its exact section-3.4 port
loop. At levels 1 and 2 every child cycle is the section-5.1 frozen emission
cycle from an outward-wound parent and every shared edge remains oppositely
directed. This predicate makes no subjective claim that a geometric normal
points away from a body centre.

The independent triangle checker MUST reject before geometry output if a level
has more than 4096 triangles. Its production broad-phase candidate cap and the
matching generated threshold are both exactly `1000000`; the cap applies
separately at each level and is not caller-configurable.
Normalize the complete mesh once:

```text
lo=componentwise mesh minimum
extent=componentwise(maximum-lo)
scale=norm(extent); reject unless finite and scale>0
p_normalized=(p-lo)/scale
D=0x1.0000000000000p-46
reject repeated IDs, non-finite coordinates, or normalized normal length <=D
```

The conservative shared-index intersection policy processes unordered triangle
pairs `(i,j)` with i<j:

```text
shared=3: duplicate triangle, hard failure
shared=2: require exactly two incidences of that edge with opposite direction;
          exclude from non-adjacent intersection testing; winding and folds remain
shared=1: always run the exact cone-feasibility classifier below
shared=0: run narrow phase only when AABBs are not disjoint
```

For zero-shared AABBs and every SAT projection interval, use exactly this one
reusable binary64 interval-disjoint predicate. Its inputs are the
already-computed binary64 interval extrema:

```text
interval_disjoint(lower_A, upper_A, lower_B, upper_B):
    cut_B = fl(lower_B - I0)
    cut_A = fl(lower_A - I0)
    disjoint = (upper_A < cut_B) or (upper_B < cut_A)
```

Evaluate both subtractions in the printed order under binary64
round-to-nearest, ties-to-even. The predicate result is `disjoint`; do not
rewrite it as `fl(lower_B-upper_A)>I0`, use a gap magnitude, reassociate it, or
apply the tolerance twice. A zero-shared AABB is disjoint when this predicate
is true on any axis. Contact or equality is not disjoint and remains a hit.

For each level, `broad_phase_candidate_count` is exactly the cardinality of
the unique unordered pairs of triangulated face records with `shared=0` for
which `interval_disjoint` is false on every normalized-AABB axis. Shared-one
pairs go
directly to the exact cone classifier and are not counted; shared-two and
shared-three pairs are also excluded. An acceleration structure is admitted
only if its deduplicated set equals the exhaustive `(i,j)` reference set with
`i<j`. The production candidate-enumeration helper visits that reference order
and fails immediately when it would emit candidate `1000001`, before narrow
phase.

The same production helper takes an explicit positive integer cap internally.
Every non-fixture caller MUST pass the exact production constant `1000000`.
Only the closed section-7 fixture harness may inject another cap; no CLI,
environment, prepared input, recipe, manifest, or implementation setting can
change it. `pair_policy_complete` is true exactly when every unordered pair
belongs to one and only one shared-count class, every shared-zero AABB survivor
receives SAT, every shared-one pair receives the exact classifier, every
shared-two pair passes the opposite-edge incidence rule, and no shared-three
pair exists.

The zero-shared SAT axis order is triangle A normal, triangle B normal, the
nine `cross(edge_A[i],edge_B[j])` axes with i outer then j, the three
`cross(normal_A,edge_A[i])` axes, and the three corresponding B axes. Edges
are `(p1-p0,p2-p1,p0-p2)`. Skip an axis with norm <=D; normalize every
other axis. On every admitted axis, apply `interval_disjoint` identically to
the two projected intervals; a pair is disjoint only when the predicate is
true on one such axis. Contact or equality remains a hit.

For exactly one shared vertex `s`, let `A0,A1` and `B0,B1` be the nonshared
vertices of triangles A and B in their triangle order. Work from every
already-normalized finite binary64 coordinate as its exact represented dyadic
value. Decode each coordinate with the semantics of CPython
`float.as_integer_ratio()`: the result is the unique reduced integer pair
`(numerator,denominator)` having the exact binary64 value and a positive
power-of-two denominator. Canonicalize either signed zero to rational `0/1`.
Rational addition, subtraction, multiplication, and division use
arbitrary-precision integers, reduce numerator and denominator by their gcd
after every operation, keep the denominator positive, and reject division by
zero. These exact predicates are explicitly exempt from the ordinary `fl`
operation semantics above.

Form the exact rational vectors, component by component, using rational
subtraction rather than binary64 subtraction or unit normalization:

```text
X0 = A0-s
X1 = A1-s
X2 = s-B0
X3 = s-B1
```

Any zero ray `Xi` is a hard checker failure. The existing repeated-control,
triangle-area, normalized-normal, and other structural checks remain required
and continue to reject degenerate triangles before this classifier; they are
not replaced or weakened here.

The pair is a **hit** if and only if exact rational values
`lambda0..lambda3` exist such that:

```text
lambda_i >= 0 for every i
lambda0+lambda1+lambda2+lambda3 = 1
lambda0*X0+lambda1*X1+lambda2*X2+lambda3*X3 = (0,0,0)
lambda0+lambda1 > 0
lambda2+lambda3 > 0
```

If no such values exist, the pair is point-only. Determine feasibility by the
following closed active-set procedure. Enumerate all subsets of
`{0,1,2,3}` first by sizes 2, 3, and 4 and then by lexicographic index order.
For each subset, solve the exact augmented system whose column for index `i`
is `(Xi.x,Xi.y,Xi.z,1)` and whose right-hand side is `(0,0,0,1)`. Row-reduce
with arbitrary-precision rational arithmetic: process unknown columns from
left to right; for each, choose the lowest currently available row with a
nonzero entry as pivot, swap it into the next pivot row, divide that row by
the pivot, and eliminate the unknown from every other row. Skip the subset if
an unknown column has no pivot, or if a coefficient-zero row has a nonzero
right-hand side. Otherwise the full-column-rank system has one solution; set
lambdas for omitted indices to zero and test all nonnegativity and both strict
side-sum conditions exactly. Stop at the first satisfying subset and classify
the pair as a hit. If all subsets fail, classify it as point-only.

The ordered inventory contains exactly
`C(4,2)+C(4,3)+C(4,4)=6+4+1=11` candidate subsets. Because evaluation stops
at the first satisfying subset, each shared-one pair evaluates at most 11
subset attempts. Carathéodory's theorem makes the inventory complete: any
feasible convex combination in three dimensions has a representation with at
most four active points, while the two strict side sums and nonzero rays rule
out a one-point witness. `I0`, `D`, and any former projection tolerance `R`
do not decide the final shared-one Boolean classification. The classifier's
Boolean result MUST be invariant under swapping triangles A and B and under
independently swapping the two A rays or the two B rays.

The production intersection fixture catalog is closed at exactly 105
executions. Every coordinate literal below is an exact binary64 hexadecimal
value, with these aliases:

```text
P0 =  0x0.0p+0
N0 = -0x0.0p+0
ONE = 0x1.0000000000000p+0
HALF = 0x1.0000000000000p-1
D50 = 0x1.0000000000000p-50
MIN_SUBNORMAL = 0x0.0000000000001p-1022
D = 0x1.0000000000000p-46
I0 = 0x1.b7cdfd9d7bdbbp-34
```

Unless a row overrides it, a shared-one base uses exact indexed triangles
`A=[(v0,s),(v1,A0),(v2,A1)]` and
`B=[(v0,s),(v3,B0),(v4,B1)]`, so the shared-index cardinality is one, with:

```text
s  = (P0,P0,P0)
A0 = (ONE,P0,P0)
A1 = (P0,ONE,P0)
```

The exact transform used by fixture rows is componentwise and ordered:

```text
transform(p,scale,t).axis:
  q0 = fl(scale*p.axis)
  q1 = fl(q0+t.axis)
  result = q1
```

The eleven shared-one bases, in stable table order, are:

| base fixture ID | exact override or construction | expected | required coverage |
| --- | --- | --- | --- |
| `shared1.offset-d50-point-only` | `B0=(ONE,P0,D50)`, `B1=(P0,ONE,D50)` | `point-only` | rejected finite-axis counterexample; near-coplanar point-only |
| `shared1.coplanar-duplicate-hit` | `B0=(ONE,P0,P0)`, `B1=(P0,ONE,P0)` | `hit` | `d=0`; ray/ray overlap; duplicate geometric rays; antipodal signed `Xi`; positive-zero representation |
| `shared1.offset-positive-minsub-point-only` | `B0=(ONE,P0,MIN_SUBNORMAL)`, `B1=(P0,ONE,MIN_SUBNORMAL)` | `point-only` | positive one-ULP side |
| `shared1.offset-negative-minsub-point-only` | `B0=(ONE,P0,-MIN_SUBNORMAL)`, `B1=(P0,ONE,-MIN_SUBNORMAL)` | `point-only` | negative one-ULP side |
| `shared1.coplanar-disjoint-fans` | `B0=(-ONE,P0,P0)`, `B1=(P0,-ONE,P0)` | `point-only` | coplanar disjoint fans; antipodal geometric rays; duplicate signed `Xi` |
| `shared1.ray-cone-hit` | `B0=(ONE,ONE,P0)`, `B1=(P0,P0,ONE)` | `hit` | one B ray strictly inside the A cone |
| `shared1.near-coplanar-full-rank-hit` | `B0=(ONE,P0,D50)`, `B1=(P0,ONE,-D50)` | `hit` | full-column-rank witness `lambda=(1/4,1/4,1/4,1/4)` |
| `shared1.transformed-point-only` | transform every point of `shared1.offset-d50-point-only` with `scale=0x1.0000000000000p+3`, `t=(0x1.0000000000000p+2,-0x1.0000000000000p+1,ONE)` | `point-only` | exactly representable translation and positive scale |
| `shared1.transformed-hit` | apply that same transform to `shared1.near-coplanar-full-rank-hit` | `hit` | exactly representable translation and positive scale |
| `shared1.negative-zero-hit` | start from `shared1.coplanar-duplicate-hit` and replace every zero-valued coordinate component with the exact `N0` bit pattern without arithmetic | `hit` | negative-zero representation; every decoded zero becomes `0/1` |
| `shared1.level2-ply-point-only` | exact PLY records and coordinates below | `point-only` | representative ordinary noncoplanar incident fan |

The positive-zero and negative-zero rows exhaust the two zero bit patterns for
every zero occurrence. Mixed masks add no distinct predicate case because the
exact rational decoder canonicalizes every component independently.

The level-2 PLY base uses `A=[(3,s),(1321,A0),(462,A1)]` and
`B=[(3,s),(1329,B0),(463,B1)]` from zero-based triangle pair `(1,65)` in PLY
SHA-256 `b092fbca5e62735743290f260fd94b5d9b8db5924ec25f9a7ae49e35d9572250`.
After section-7 mesh normalization its coordinates are exactly:

```text
s  = p3    = (0x1.8b59f7e4bf4dfp-7,0x1.0a35e0636f7c1p-4,0x1.264d28c7c3da4p-4)
A0 = p1321 = (0x1.37918e2798bb6p-8,0x1.61bcdab8dcc06p-4,0x1.43c9e5ce2aeb6p-4)
A1 = p462  = (0x1.7bc42ac7f04b0p-7,0x1.6cae8c4686bb2p-4,0x1.0be935f6a339ep-4)
B0 = p1329 = (0x1.7888e87a16156p-6,0x1.7eec0987f75cdp-4,0x1.d5d88ce274e30p-5)
B1 = p463  = (0x1.8b59f7e4bf4dfp-6,0x1.18982604f83a1p-4,0x1.07df2315527a3p-4)
```

Each base expands into exactly eight executions with suffixes in this order:

```text
p000, p001, p010, p011, p100, p101, p110, p111
```

For suffix `pABC`, apply bits left-to-right: if `A=1`, swap the complete
triangle A and B records; if `B=1`, swap the two nonshared records in the
resulting triangle A; if `C=1`, swap the two nonshared records in the resulting
triangle B. The shared record remains first in each triangle. Coordinates and
vertex IDs do not change. Every variant has ID `<base-fixture-id>.<suffix>`
and MUST produce its base result. Execution order is base-table order then the
suffix order above. Thus this matrix contributes exactly `11*8=88`
executions and tests all eight required swap combinations for every base.

The remaining seventeen fixtures, in stable table order, are:

| fixture ID | exact records or construction | expected result and stage |
| --- | --- | --- |
| `shared0.clear-hit-origin` | `A=[(0,(-ONE,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,ONE,P0))]`; `B=[(3,(P0,-ONE,P0)),(4,(HALF,HALF,P0)),(5,(-HALF,HALF,P0))]` | `hit` in zero-shared SAT narrow phase |
| `shared0.clear-hit-translated` | transform the preceding fixture with `scale=ONE`, `t=(0x1.0000000000000p+2,-0x1.0000000000000p+1,ONE)` | `hit` |
| `shared0.sub-I0-contact-origin` | `A=[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,ONE,P0))]`; B has IDs `3,4,5`, the same x/y values, and every z=`0x1.0000000000000p-34` | `hit` under `I0` although geometrically separated |
| `shared0.sub-I0-contact-translated` | transform the preceding fixture with `scale=ONE`, `t=(0x1.0000000000000p+2,-0x1.0000000000000p+1,ONE)` | `hit` under `I0` |
| `shared0.aabb-disjoint` | `A=[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,ONE,P0))]`; `B=[(3,(P0,P0,ONE)),(4,(ONE,P0,ONE)),(5,(P0,ONE,ONE))]` | `disjoint` at AABB stage |
| `shared0.sat-disjoint` | `A=[(0,(P0,P0,P0)),(1,(0x1.0000000000000p+1,P0,P0)),(2,(P0,0x1.0000000000000p+1,P0))]`; `B=[(3,(0x1.0000000000000p+1,0x1.0000000000000p+1,P0)),(4,(0x1.0000000000000p+1,0x1.8000000000000p+0,P0)),(5,(0x1.8000000000000p+0,0x1.0000000000000p+1,P0))]` | AABBs overlap; `disjoint` at SAT axis |
| `shared0.extreme-small-hit` | transform `shared0.clear-hit-origin` with `scale=0x1.0000000000000p-500`, `t=(P0,P0,P0)` | `hit` after normalization |
| `shared0.extreme-large-hit` | transform `shared0.clear-hit-origin` with `scale=0x1.0000000000000p+500`, `t=(P0,P0,P0)` | `hit` after normalization |
| `normal.boundary-D-reject` | one triangle `[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,D,P0))]` | hard failure at normalized-normal admission because norm `<=D` |
| `normal.successor-D-accept` | one triangle `[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,0x1.0000000000000p-45,P0))]` | normal admission passes; there are zero unordered pairs |
| `shared2.opposite-edge-valid` | `A=[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,ONE,P0))]`; `B=[(1,(ONE,P0,P0)),(0,(P0,P0,P0)),(3,(P0,-ONE,P0))]` | `excluded-adjacent`; opposite directed shared edge |
| `shared2.same-direction-reject` | `A=[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,ONE,P0))]`; `B=[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(3,(P0,-ONE,P0))]` | hard failure at shared-two incidence/direction check |
| `shared3.duplicate-triangle-reject` | two triangle records both equal `[(0,(P0,P0,P0)),(1,(ONE,P0,P0)),(2,(P0,ONE,P0))]` | hard failure at duplicate-triangle policy |
| `triangle-cap.boundary-4096` | for `r=0..4095`, IDs are `[3r,3r+1,3r+2]`; let binary64 `x=float(4*r)`, then coordinates are `(x,P0,P0)`, `(fl(x+ONE),P0,P0)`, `(x,ONE,P0)` | triangle cap admitted; no AABB candidates or hits |
| `triangle-cap.successor-4097` | preceding generator for `r=0..4096` | hard failure before normalization at triangle count 4097 |
| `candidate-cap.boundary-injected-3` | production helper with fixture-local cap 3 over the three exact triangles below | enumeration succeeds with exactly three candidates; narrow phase reports hits |
| `candidate-cap.successor-injected-3` | production helper with fixture-local cap 3 over the four exact triangles below | hard failure on the fourth candidate, before narrow phase |

For each candidate-cap row, triangle `r` has distinct IDs
`[3r,3r+1,3r+2]` and identical valid geometry:

```text
T_r = [(3r,(P0,P0,P0)),
       (3r+1,(ONE,P0,P0)),
       (3r+2,(P0,ONE,P0))]
boundary row:  r=0..2
successor row: r=0..3
```

All inter-triangle pairs have `shared=0` and surviving identical AABBs. The
boundary row therefore yields exactly `C(3,2)=3` candidates. For the successor
row the first four candidates in reference order are `(0,1)`, `(0,2)`,
`(0,3)`, and `(1,2)`; the injected cap of 3 MUST fail on `(1,2)`. Both rows
also assert, without adding an execution, that the production constant equals
integer `1000000` and that the three exact threshold records
`threshold.intersection.L0.broad_phase_candidate_count`,
`threshold.intersection.L1.broad_phase_candidate_count`, and
`threshold.intersection.L2.broad_phase_candidate_count` each have relation
`le`, upper bound integer `1000000`, and no lower bound. A million-pair
materialized fixture is forbidden.

The closed execution arithmetic is exactly:

```text
11 shared-one bases * 8 permutations = 88 executions
17 general fixture rows                    17 executions
total                                     105 executions
```

The 88 shared-one executions invoke the exact production shared-one classifier
with their coordinates treated as the already-normalized values its interface
requires. Each general row enters the production checker or named production
helper at the stage its construction specifies and follows production logic to
its frozen terminal result. Only the two candidate-cap rows use the
fixture-local helper cap. No fixture writes or publishes an artifact. The
complete 17,832-pair PLY audit remains bounded
pre-freeze evidence from section 1, not a committed mesh fixture, admitted
implementation input, output role, or completed-contract regression. The
artifact policy and closed 47-role inventory remain unchanged.

For every port and every level, let the ordered loop points be `p_i`, centroid
`c`, declared outward direction `d_port`, and
`A=0.5*sum(cross(p_i-c,p_(i+1)-c))`. The port loop MUST satisfy:

```text
-normalize(A) dot d_port >=0.99
planarity residual <=T
||A||/S^2 >=0.0001
```

Loop equality permits orientation-preserving cyclic rotation only; reversal
MUST fail. For each port boundary edge, calculate the full area-weighted
normal `nF` of its adjacent outward-wound quad, the outward-wound boundary
tangent `t`, and `cF=normalize(cross(t,nF))`. Require
`cF dot d_port >=0.80` at levels 0, 1, and 2. This induced co-normal gate is
independent of the loop-area gate and cannot be replaced by a label or colour.

At every cross-domain shared edge, compare the full area-weighted normals of
the incident quads using the smaller angle in degrees. Reject at or above:

```text
base: 90 degrees       level 1: 60 degrees       level 2: 30 degrees
```

The fold measure uses exactly CPython 3.10.12 `math.acos` under the identical frozen
runtime fingerprint. With
`pi=0x1.921fb54442d18p+1`, compute exactly:

```text
c  = clamp(dot(n0,n1),-1,+1)
a  = math.acos(c)
t0 = fl(a*180.0)
degrees = fl(t0/pi)
```

The normals are the full area-weighted quad normals from the primitive above,
and the smaller angle in degrees is reported. No reassociation is permitted;
the determinism claim is same-runtime only.

## 8. Candidate-specific anatomy gates

All measures below use the same evaluated surface at levels 0, 1, and 2.
Trace-to-trace measures use exact dyadic tag pairing; the shoulder-surface gate
uses its explicitly defined face-incidence set. A missing or ambiguous selector
fails closed. These are mechanical readability guards, not a visual-quality
score.

```text
neck exposure:             min >=0.05 m at levels 0,1,2
shoulder-surface descent:  min >=0.05 m at levels 0,1,2
arm-port descent:          supporting min >=0.05 m at levels 0,1,2
axillary turn depth:       min >=0.05 m at levels 0,1,2
axillary path stretch:     max <=2.5 at levels 0,1,2
axillary inboard recess:   inferior tags min >=0.05 m at levels 0,1,2
axillary downward recess:  inferior tags min >=0.05 m at levels 0,1,2
pelvic vertical wrap:      min >=0.05 m at levels 0,1,2
pelvic lateral ratio:      min >=1.05 at levels 0,1,2
front depth wrap:          min >=0.005 m at levels 0,1,2
back depth wrap:           min >=0.005 m at levels 0,1,2
downward thigh root:       the vertical-wrap scalar plus port direction -Y
```

The exact measures are:

- **Neck:** `delta_y=port.y-junction.y`; the neck port MUST be above the
  thorax-neck junction by `delta_y>=0.05 m` at every level.
- **Shoulder surface:** for each side and level, form the unique set of all
  evaluated vertices incident to evaluated faces whose base-face ancestor's
  construction owner is that side's shoulder domain. Require
  `max(shoulder_surface.y) <= min(neck_port.y)-0.05 m`. Face ancestry and
  chart incidence select this set; domain labels attached to vertices and
  spatial or visual bounding boxes are forbidden substitutes.
- **Arm-port support:** independently derive the side's evaluated arm-port
  loop and require `max(arm_port.y) <= min(neck_port.y)-0.05 m`. This
  supporting gate does not satisfy or replace shoulder-surface descent.
- **Axillary turn depth and path stretch:** arm/shoulder tags are `(j,k)`
  after dropping `i`. At each level and for every exact reduced dyadic depth
  tag `k`, derive three unique samples independently from face/chart
  incidence: `U` is the upper shoulder-junction sample at `j=6`, `A` is the
  same side's shoulder-junction axilla sample at `j=4`, and `O` is the
  inferior arm-port sample at `j=4`. Each trace MUST independently yield the
  complete reduced dyadic tag set over `0<=k<=2` for that level, and the three
  sets MUST be equal before pairing. The topology fixes the ordered trace
  `U -> A -> O`; no finite-chord projection chooses or reorders a sample. In
  the x-y plane, compute in the section-7 binary64 primitive order:

  ```text
  r = A-U
  s = O-A
  c = O-U
  lr = norm((r.x,r.y,0))
  ls = norm((s.x,s.y,0))
  lc = norm((c.x,c.y,0))
  path = fl(lr+ls)
  cross_z = fl(fl(c.x*r.y)-fl(c.y*r.x))
  oriented_cross = cross_z for left, fl(-cross_z) for right
  turn_depth = fl(oriented_cross/path)
  path_stretch = fl(path/lc)
  ```

  The production predicate uses this exact failure order for every U/A/O
  sample:

  ```text
  1. require U, A, and O finite
  2. compute r, s, c, lr, ls, and lc in the printed operation order
  3. require lr finite and lr>0
  4. require ls finite and ls>0
  5. require lc finite and lc>0
  6. compute path=fl(lr+ls); require path finite and path>0
  7. compute cross_z, oriented_cross, turn_depth, and path_stretch;
     require all four finite
  8. require turn_depth>=0x1.999999999999ap-5 m
  9. require path_stretch<=0x1.4000000000000p+1
  ```

  No division may occur before steps 3 through 6 have passed. Empty,
  duplicate, or ambiguous sample sets fail closed before this predicate.
  Signed turn depth verifies that the topology-ordered trace turns toward the
  axillary hollow; the scale-free path-stretch ceiling rejects unbounded
  hooked or sagging detours that could otherwise pass turn depth. These two
  mechanical guards remain insufficient to establish visual quality, so the
  fixed-view visual appraisal remains necessary. Both gates are independent
  of the following two supporting recess gates.

  The closed principal constants, all exact binary64 values, are:

  ```text
  level = 2
  k = {numerator:3,denominator:4}
  U0 = (-0x1.0866666666667p+0,0x1.1333333333333p+1,-0x1.699999999999ap-4)
  A0 = (-0x1.289999999999ap+0,0x1.9533333333334p+0,-0x1.2f28f5c28f5c4p-4)
  O0 = (-0x1.599999999999ap+0,0x1.d99999999999ap+0,-0x1.47ae147ae147bp-4)
  principal_turn_depth = 0x1.4016a28cc89afp-3 = 0.15629317276132101 m
  principal_path_stretch = 0x1.0ab0f3d101d06p+1 = 2.0835251589338695
  historical_old_t = 0x1.1a1d8e870c54fp+0 = 1.1020135001857232
  ```

  `historical_old_t` is provenance for the former fixture name
  `old-t>1-valid-hollow` and is exactly the rejected historical x-y-plane
  finite-chord projection
  `dot((A0-U0)_xy,(O0-U0)_xy)/dot((O0-U0)_xy,(O0-U0)_xy)`, where `_xy`
  means the two-component vector containing only x and y. It is not an
  admitted predicate, threshold, or gate.

  The seven U/A/O production-predicate executions, in exact order, are:

  | fixture ID | side and exact U/A/O construction | exact derived result | expected |
  | --- | --- | --- | --- |
  | `axillary.principal-left-pass` | left; `(U,A,O)=(U0,A0,O0)` | principal values above | pass |
  | `axillary.principal-right-mirror-pass` | right; negate only each x component of `U0,A0,O0` | identical principal values | pass |
  | `axillary.wrong-sign-left` | left; `(U,A,O)=(O0,A0,U0)` | `turn_depth=-0x1.4016a28cc89afp-3`; `path_stretch=0x1.0ab0f3d101d06p+1` | fail at step 8 only |
  | `axillary.U-equals-A` | left; `(U,A,O)=(U0,U0,O0)` | `lr=0x0.0p+0` | hard failure at step 3 |
  | `axillary.A-equals-O` | left; `(U,A,O)=(U0,O0,O0)` | `lr=0x1.bf1092ac1a7f1p-2`; `ls=0x0.0p+0` | hard failure at step 4 |
  | `axillary.U-equals-O` | left; `(U,A,O)=(U0,A0,U0)` | `lr=ls=0x1.29747f9d3ab49p-1`; `lc=0x0.0p+0` | hard failure at step 5 |
  | `axillary.long-sag-left` | left; `U=(0x0.0p+0,0x1.0000000000000p+0,0x0.0p+0)`, `A=(0x0.0p+0,-0x1.4000000000000p+3,0x0.0p+0)`, `O=(-0x1.0000000000000p+0,0x0.0p+0,0x0.0p+0)` | `turn_depth=0x1.0b8e161fdc225p-1`; `path_stretch=0x1.dc4de77c38e3cp+3` | pass step 8; fail step 9 |

  The other six executions are direct finite-scalar comparator fixtures, not
  U/A/O reachability tests. Their exact IDs, values, and outcomes are:

  ```text
  axillary.scalar.turn-depth-predecessor  0x1.9999999999999p-5  fail step 8
  axillary.scalar.turn-depth-boundary     0x1.999999999999ap-5  pass step 8
  axillary.scalar.turn-depth-successor    0x1.999999999999bp-5  pass step 8
  axillary.scalar.path-stretch-predecessor 0x1.3ffffffffffffp+1 pass step 9
  axillary.scalar.path-stretch-boundary    0x1.4000000000000p+1 pass step 9
  axillary.scalar.path-stretch-successor   0x1.4000000000001p+1 fail step 9
  ```

  The axillary fixture suite is exactly the seven table rows followed by those
  six scalar rows: `2 principal/mirror + 1 wrong-sign + 3 degeneracy + 1
  long-sag + 6 scalar = 13` executions. Every case invokes the applicable
  production predicate and emits no artifact.
- **Axillary supporting recesses:** the inferior
  set is exactly every reduced dyadic tag with `4<=j<=5`, including both
  endpoints and every midpoint generated at levels 1 and 2. Derive the
  shoulder-junction and arm-port samples independently from face/chart
  incidence. On the left require `junction.x-arm_port.x >=0.05 m`; on the
  right require `arm_port.x-junction.x >=0.05 m`. Require
  `arm_port.y-junction.y >=0.05 m` for every inferior tag on both sides.
  No endpoint or maximum-only substitute is permitted.
- **Pelvis:** thigh and pelvis/hip tags are `(i,k)` after dropping `j` and
  are paired by identical reduced dyadic tags. For each side,
  `vertical_wrap=junction.y-port.y`; require its minimum to be at least
  0.05 m at every level. For each tag with nonzero denominator,
  `lateral_ratio=abs(junction.x-P_s.x)/abs(port.x-P_s.x)` and require the
  minimum to be at least 1.05; at least one such tag is required. A zero
  denominator is reported as omitted and cannot satisfy the gate. Front tags
  are exactly `k>1`, with `front_wrap=junction.z-port.z`; back tags are
  exactly `k<1`, with `back_wrap=port.z-junction.z`. Tags with `k=1` are
  excluded from both depth sets and remain in vertical wrap.
- **Thigh:** downward thigh root is the same `vertical_wrap` scalar already
  required above, reported under this compatibility label together with the
  independently required `-Y` port orientation. It is not a second gate or
  a weaker level-0/1 alternative.

The following clearances MUST be at least `0.05 m` at every level:

```text
neck          min(spanX,spanZ)
axilla side   min(spanY,spanZ)
groin         minX(right hip junction)-maxX(left hip junction)
medial thigh  minX(right thigh port)-maxX(left thigh port)
```

For any named sample set `S`, `spanX(S)`, `spanY(S)`, and `spanZ(S)` are
respectively `max(p.x)-min(p.x)`, `max(p.y)-min(p.y)`, and
`max(p.z)-min(p.z)` over all and only the exact tag-paired samples selected
for that feature at that level. `minX` and `maxX` use the same closed sample
sets. An empty or ambiguous sample set fails closed; no visual bounding box
or unpaired endpoint may substitute. In the clearance list, `S` is the neck
port loop for `neck`, the corresponding arm-port loop for `axilla side`, and
the corresponding paired hip-junction or thigh-port samples for `groin` or
`medial thigh` respectively.

Every selector in this section is reconstructed from retained face incidence,
base-face ancestry, chart incidence, exact port/junction catalogs, and reduced
dyadic tags. A stored semantic label, lineage colour, render-space feature,
axis-aligned bounding box, or threshold-selected coordinate subset MUST NOT be
used as a selector or as a substitute for the prescribed incidence proof.

The disposable trial observed approximately 0.6394 m, 0.3 m, 0.8394 m, and
1.36 m for its corresponding clearances, but those values are historical
observations and not threshold substitutions. Positive gates do not claim a complete humanoid;
the main thread's fixed-view inspection remains authoritative for readable
thorax, abdomen, pelvis, neck, shoulder, axilla, and thigh-root form.

### 8.1 Exhaustive gate-manifest inventory

The gate manifest is generated from the following closed templates; it is not
assembled opportunistically by checks that happen to run. Template axes use
these exact ordered sets:

```text
levels = [0,1,2]
sides = [left,right]
junctions = [junction.pelvis__left_hip,junction.pelvis__abdomen,
             junction.abdomen__thorax,junction.thorax__left_shoulder,
             junction.thorax__neck,junction.pelvis__right_hip,
             junction.thorax__right_shoulder]
ports = [port.neck,port.left_arm,port.right_arm,
         port.left_thigh,port.right_thigh]
junction_base_samples = [8,10,10,8,6,8,8]
port_base_samples = [6,8,8,8,8]
bilateral_anatomy = [shoulder_surface_descent,arm_port_descent,
                     axillary_turn_depth,axillary_path_stretch,
                     axillary_inboard_recess,axillary_downward_recess,
                     pelvic_vertical_wrap,pelvic_lateral_ratio,
                     front_depth_wrap,back_depth_wrap]
clearances = [neck,left_axilla,right_axilla,groin,medial_thigh]
```

Substitution preserves the printed axis order only while generating records;
each finished group is sorted by `gate_id` UTF-8 bytes. `nJ` and `nP` below
are the matching base-sample entries. `V_L,E_L,Q_L,Tri_L,B_L` are the exact
level counts in section 6. `cardinality(selector)` means the number of unique
samples produced by the exact incidence/chart selector before measuring; an
empty, duplicated, non-finite, or ambiguous selected set fails and cannot be
aggregated.

| target group | gate ID template and Cartesian-product axes | exact sample selector and sample count | aggregation and threshold |
| --- | --- | --- | --- |
| structural | `structural.catalog.{metric}` for the 15 catalog metrics below | one computed scalar; `1` | `min=max=value`; catalog relation/value below |
| structural | `structural.catalog_boolean.{metric}` for the 13 booleans below | one complete predicate; `1` | `min=max=1`; `eq 1` |
| structural | `structural.L{L}.count.{metric}` for `levels x [vertices,edges,quads,triangles,boundary_edges]` | one computed count; `1` | `min=max=count`; `eq` section-6 count |
| structural | `structural.L{L}.surface_boolean.{metric}` for `levels x [connected,orientable,outward_wound,boundary_components_match_ports]` | one complete per-level predicate; `1` | `min=max=1`; `eq 1` |
| structural | `structural.L{L}.finite.{metric}` for `levels x [coordinates,quad_normals,triangle_areas,quad_areas]` | respectively all scalar coordinate components, normal components, triangle areas, or quad areas; `3*V_L`, `3*Q_L`, `2*Q_L`, or `Q_L` | require every member finite, then `min=max=1`; `eq 1` |
| structural | `structural.L{L}.floor.{metric}` for `levels x [edge_length,triangle_area,quad_area]` | all `E_L`, `2*Q_L`, or `Q_L` values; same number | observed minimum and maximum; `ge` the matching section-7 floor |
| structural | `structural.L{L}.invalid_count.{metric}` for `levels x` the nine invalid metrics below | one complete count; `1` | `min=max=count`; `eq 0` |
| structural | `structural.L{L}.chart.{metric}` for `levels x [charts,interior_transitions,maximum_samples_per_vertex]` | one complete count/maximum; `1` | `min=max=value`; `eq` section-5.1 value |
| structural | `structural.L2.lineage_cap.{metric}` for `[base_control_contributors,dependency_union_keys,contributor_domains]` | one value per level-2 vertex; `1737` | observed maximum; respectively `le 20`, `le 54`, `le 5` |
| structural | `structural.subdivision.{metric}` for the seven subdivision predicates below | one complete predicate; `1` | `min=max=1`; `eq 1` |
| continuity | `continuity.{junction}.L{L}.{metric}` for `junctions x levels x [tag_identity,opposite_trace_direction,coordinate_residual,fold_angle]` | complete paired traces for the junction; respectively `1`, `1`, `3*nJ*2^L`, `nJ*2^L` | first two `eq 1`; residual observed maximum `le T`; fold observed maximum `lt 90`, `lt 60`, or `lt 30` degrees for L0/L1/L2 |
| continuity | `continuity.{port}.L{L}.{metric}` for `ports x levels x [orientation,planarity,area_ratio,co_normal]` | exact evaluated port loop; respectively `1`, `nP*2^L`, `1`, `nP*2^L` | orientation scalar `ge 0.99`; planarity observed maximum `le T`; area scalar `ge 0.0001`; co-normal observed minimum `ge 0.80` |
| anatomy | `anatomy.neck_exposure.L{L}` for `levels` | all exact paired neck-junction/port tags; `6*2^L` | observed minimum; `ge 0.05 m` |
| anatomy | `anatomy.{metric}.{side}.L{L}` for `bilateral_anatomy x sides x levels` | selector/count rules below | observed minimum or maximum and relation specified below |
| anatomy | `anatomy.clearance.{name}.L{L}` for `clearances x levels` | one scalar from the named exact sample sets; `1` | `min=max=value`; `ge 0.05 m` |
| intersection | `intersection.L{L}.{metric}` for `levels x [triangle_count,broad_phase_candidate_count,intersection_hit_count,pair_policy_complete]` | one complete count or predicate; `1` | triangle count `eq Tri_L`; candidate count `le 1000000`; hit count `eq 0`; predicate `eq 1` |

The 15 catalog metrics and values are exactly:

```text
selected_cells=58, un_capped_faces=122, domains=8, junctions=7, ports=5,
controls=120, base_quads=104, base_edges=227, base_boundary_edges=38,
boundary_components=5, connected_components=1, euler_characteristic=-3,
extraordinary_controls=20, special_case_ids=9, topology_decision_sites=3
```

All use `eq` except `topology_decision_sites`, which uses `le 3` and records
the observed value 3. Their units are `count` except Euler characteristic,
whose unit is `dimensionless`. The 13 catalog booleans are exactly
`all_domains_nonempty`, `selected_cell_inventory_exact`,
`control_catalog_exact`, `face_catalog_exact`, `junction_catalog_exact`,
`port_catalog_exact`, `special_case_catalog_exact`,
`base_face_controls_distinct`, `base_edge_use_within_two`,
`construction_ownership_complete`, `port_caps_exactly_removed`,
`axillary_fixture_suite_complete`, and
`intersection_fixture_suite_complete`.

`intersection_fixture_suite_complete` equals 1 if and only if the seed builder
independently executes the exact 105 section-7 cases in their frozen order
through the production predicates and every case produces its frozen result.
`axillary_fixture_suite_complete` equals 1 if and only if the seed builder
independently executes the exact 13 section-8 cases in their frozen order
through the applicable production U/A/O or scalar predicate and every result
matches. Omission, duplication, substitution, a non-production predicate, a
wrong order or count, an unexpected result, an artifact emission, or reuse of
a unit-test result makes the corresponding Boolean 0. The managed tests in
section 11 independently execute the same 105 and 13 cases and do not trust
these manifest Booleans or reuse either seed builder's result. Both seed-local
fixture self-checks each contribute exactly one structural gate result, run
inside the existing `geometry-gates` timing and stage, and add no artifact or
output role.

The nine per-level invalid metrics are exactly `duplicate_vertex_ids`,
`duplicate_face_ids`, `degenerate_faces`, `zero_length_edges`,
`non_manifold_edges`, `orientation_conflicts`, `unowned_elements`,
`overowned_elements`, and `accidental_boundary_components`. The seven
subdivision predicates are exactly `recurrence_exact`, `incidence_complete`,
`boundary_neighbors_exact`, `face_emission_exact`, `lineage_complete`,
`chart_complete`, and `transition_complete`.

For bilateral anatomy, sample counts and thresholds are closed as follows:

| metric | exact selector and sample count at level L | threshold |
| --- | --- | --- |
| `shoulder_surface_descent` | each unique vertex in the section-8 side shoulder-surface set; `cardinality(selector)` | `ge 0.05 m` for `min(neck-port y)-vertex.y` |
| `arm_port_descent` | each vertex in that side's evaluated arm-port loop; `8*2^L` | `ge 0.05 m` for `min(neck-port y)-vertex.y` |
| `axillary_turn_depth` | every reduced depth tag `k`; `2*2^L+1`, hence 3/5/9 at L0/L1/L2 | observed minimum; `ge 0.05 m` for `turn_depth` |
| `axillary_path_stretch` | the same independently reconstructed and paired depth-tag set; `2*2^L+1`, hence 3/5/9 at L0/L1/L2 | observed maximum; `le 2.5 dimensionless` for `path_stretch` |
| `axillary_inboard_recess` | every shoulder-trace perimeter tag with `4<=j<=5`; `4*2^L+1` | `ge 0.05 m` |
| `axillary_downward_recess` | the same independently selected perimeter-tag set; `4*2^L+1` | `ge 0.05 m` |
| `pelvic_vertical_wrap` | every paired hip-junction/thigh-port perimeter tag; `8*2^L` | `ge 0.05 m` |
| `pelvic_lateral_ratio` | those perimeter tags whose exact denominator is nonzero; `cardinality(selector after exact-zero exclusion)`, required positive | `ge 1.05 dimensionless` |
| `front_depth_wrap` | perimeter tags with `k>1`; `4*2^L-1` | `ge 0.005 m` |
| `back_depth_wrap` | perimeter tags with `k<1`; `4*2^L-1` | `ge 0.005 m` |

The closed bilateral-anatomy inventory therefore contains exactly 10 metrics.
`axillary_turn_depth` and `axillary_path_stretch` each generate exactly
`2 sides * 3 levels = 6` aggregate gate results over their respective
3/5/9-sample level sets.

The downward-thigh compatibility label creates no gate result. The port
orientation and pelvic-vertical-wrap results already provide its two exact
facts. Every sample selector above is reconstructed independently from
face/chart incidence as required by sections 5 and 8; labels, colours, or
bounding boxes cannot supply samples.

Generated-threshold units are closed: predicates and finite checks use `boolean`;
integer inventories, topology/count results, chart/lineage counts, and
intersection counts use `count`; coordinate residual, planarity, edge length,
and linear anatomy/clearance measures use `m`; triangle and quad areas use
`m2`; fold angles use `degree`; and Euler characteristic, area ratio,
orientation dot, co-normal dot, and pelvic lateral ratio use `dimensionless`.
Axillary path stretch also uses `dimensionless`. No other unit string is
generated. The separately fixed report threshold
`gate.boolean-pass` retains its section-10.2 unit `dimensionless`.

For every generated `gate_id`, generate exactly one `threshold_record` with
`threshold_id="threshold." + gate_id`; its relation, bound(s), and unit are
the values in the tables above. No two gate results share that generated
threshold ID. The only additional threshold is `gate.boolean-pass`, used by
the six run-report gates in section 10.2. Consequently the gate manifest has
exactly 356 generated gate thresholds plus that one report threshold: 357
threshold records, with no unused or missing record.

Before aggregation, every raw numeric sample MUST be finite. A boolean or
single count has `sample_count=1` and equal integer observed
minimum/maximum. A
multi-sample minimum, maximum, ratio, residual, area, or distance has the
exact selector cardinality as `sample_count` and stores the true minimum and
maximum of all raw samples, regardless of which bound decides the gate. No
summary may hide a failing member. Successful arrays equal the generated
inventories exactly, with no extra, empty, or omitted record. The arithmetic
is:

```text
structural   = 15+13+(3*5)+(3*4)+(3*4)+(3*3)+(3*9)+(3*3)+3+7 = 122
continuity   = 7*3*4 + 5*3*4                           = 144
anatomy      = 3 + 10*2*3 + 5*3                        = 78
intersection = 3*4                                      = 12
total gate results                                      = 356
```

## 9. Causality, must-affect, and locality

The exact 33 source-derived must-affect parameter IDs are:

```text
left.r_y, right.r_y, lower_pelvis.L_y, lower_pelvis.C_z,
left.r_x, right.r_x, lower_pelvis.R_x,
left.r_z, right.r_z, lower_pelvis.R_f, lower_pelvis.R_b,
left.thigh_start_x, left.thigh_start_y, left.thigh_start_z,
right.thigh_start_x, right.thigh_start_y, right.thigh_start_z,
neck_collar.C_y, neck_collar.rL, neck_upper.C_y, neck_upper.rL,
left.axilla_x, left.axilla_y, right.axilla_x, right.axilla_y,
left.peak_y, right.peak_y,
left.start_lateral, right.start_lateral,
left.start_up, right.start_up,
left.shoulder_depth, right.shoulder_depth
```

Their exact prepared-component selectors are:

```text
left.r_y                  -> hips.left.r_y
right.r_y                 -> hips.right.r_y
lower_pelvis.L_y          -> stations.lower_pelvis.C.y
lower_pelvis.C_z          -> stations.lower_pelvis.C.z
left.r_x                  -> hips.left.r_x
right.r_x                 -> hips.right.r_x
lower_pelvis.R_x          -> stations.lower_pelvis.rL
left.r_z                  -> hips.left.r_z
right.r_z                 -> hips.right.r_z
lower_pelvis.R_f          -> stations.lower_pelvis.rA
lower_pelvis.R_b          -> stations.lower_pelvis.rP
left.thigh_start_x        -> hips.left.P_s.x
left.thigh_start_y        -> hips.left.P_s.y
left.thigh_start_z        -> hips.left.P_s.z
right.thigh_start_x       -> hips.right.P_s.x
right.thigh_start_y       -> hips.right.P_s.y
right.thigh_start_z       -> hips.right.P_s.z
neck_collar.C_y           -> stations.neck_collar.C.y
neck_collar.rL            -> stations.neck_collar.rL
neck_upper.C_y            -> stations.neck_upper.C.y
neck_upper.rL             -> stations.neck_upper.rL
left.axilla_x             -> shoulders.left.axilla.x
left.axilla_y             -> shoulders.left.axilla.y
right.axilla_x            -> shoulders.right.axilla.x
right.axilla_y            -> shoulders.right.axilla.y
left.peak_y               -> shoulders.left.peak.y
right.peak_y              -> shoulders.right.peak.y
left.start_lateral        -> shoulders.left.start_lateral
right.start_lateral       -> shoulders.right.start_lateral
left.start_up             -> shoulders.left.start_up
right.start_up            -> shoulders.right.start_up
left.shoulder_depth       -> shoulders.left.shoulder_depth
right.shoulder_depth      -> shoulders.right.shoulder_depth
```

For each ID independently, copy the validated prepared input, add exactly
binary64 `+0.01 m` to that one selected scalar, and change no other prepared
component. This is a one-sided positive perturbation; no negative or central
difference run is admitted. A selector that resolves to zero, multiple, or a
different component fails before geometry. Analytic nonzero derivative support
MUST be derived from the frozen
formulas and propagated through the fixed subdivision stencils; it MUST NOT be
inferred from metadata, lineage labels, or observed movement. Zero-coefficient
contributors are reported separately and excluded from predicted support.

Causality support is defined only over the numeric level-2 vertex indices
`0..1736`. For index `i`, calculate the vector
`delta_i=perturbed_coordinate_i-baseline_coordinate_i` componentwise and
`movement_i=norm(delta_i)` in the section-7 primitive order. The predicted
support is the sorted unique set of indices whose exact analytic derivative
with respect to the selected prepared component is nonzero after propagation
through both fixed subdivision stencils. The observed support is the sorted
unique set of indices for which `movement_i>T`. The two sets MUST be equal;
equivalently every predicted member moves by more than `T` and every other
level-2 vertex moves by at most `T`.

At `lambda_x=1.00`, the exact level-2 predicted support for the
`hips.left.P_s.x` and `hips.right.P_s.x` perturbations is expected to contain
436 vertices per side. This is a dependency/support expectation only; the
fresh predicted and observed support sets and hashes remain mandatory.

Each support set is hashed over this exact byte domain:

```text
ASCII bytes "CKSUPPORTv1"
one NUL byte
one unsigned byte with value 2
little-endian uint32 count
count little-endian uint32 numeric vertex indices in ascending order
no trailing byte
```

The count is at most 1737; every index is in range and strictly greater than
its predecessor. Empty predicted or observed support fails the perturbation
gate even though the byte grammar can represent count zero. Support bytes are
hash domains only and are not additional output files.

For every parameter, the builder MUST prove:

```text
support is nonempty
predicted and observed level-2 support sets and their hashes agree
max movement over predicted support >= M_min, where
M_min=fl(binary64(2.5e-4)*S)=0x1.d14e3bcd35a85p-11 m
final serialized mesh bytes differ from baseline
topology, IDs, formulas, ownership, and lineage are unchanged
all level-2 vertices outside predicted support move by at most T
```

Any admitted geometry-driving source role without a downstream consumer,
metadata movement without the required coordinate movement, or lineage
without a causal source binding fails closed. Forbidden inputs include profile
identity, finished geometry, connectivity, perimeters, point clouds, fields,
masks, corrective offsets, prior serialized output, and out-of-scope module
state.

## 10. Artifact, schema, serialization, and rendering contract

### 10.1 Canonical bytes and reusable records

Canonical JSON bytes are produced only by exactly CPython 3.10.12 under the
frozen runtime fingerprint. Parse with a rejecting `object_pairs_hook` and
reject duplicate object keys before normalization. Canonical processing is
schema-aware: first recognize the exact closed object shape and field grammar.
Every map key MUST be a string and every value MUST be the declared JSON
string, boolean, null, array, map, integer, finite number, or binary64 type.
Type dispatch tests `bool` before `int`, so booleans never satisfy an integer
or numeric field.

At runtime a field declared `binary64` contains only a finite Python `float`.
The encoder emits either signed binary64 zero as the single JSON integer token
`0`; every other binary64 float retains the exact CPython encoding below. It
preserves integers only in fields whose grammar admits integers and preserves
nonzero finite floats in fields whose grammar admits them. Then encode exactly:

```python
json.dumps(value, sort_keys=True, separators=(",", ":"),
           ensure_ascii=False, allow_nan=False).encode("utf-8")
```

The result has no BOM and no trailing LF. During schema-aware decoding of any
contract-owned canonical artifact, after duplicate-key rejection and closed
shape/key recognition but before binary64 type validation or numeric use, a
value in a `binary64` field is admitted only when it is a finite Python
`float`, or when its exact Python type is `int` and its value is exactly zero.
That sole integer-zero case is immediately coerced to binary64 `+0.0`; every
other integer token in a binary64 field rejects. A decoded `-0.0` or `0.0`
float is valid in memory but re-encodes as `0`, so either noncanonical wire
spelling fails the mandatory byte-for-byte re-encoding check.

The builder and comparator MUST canonical re-encode every decoded prepared
input, manifest, report, receipt, and nested record and require byte equality
with the original artifact before checking hashes, references, identities,
semantic relations, or cross-seed equality. Semantic checks use the coerced
runtime object; SHA-256 and stable byte comparison use the original bytes
after this canonicality proof. Parsing and reserializing bytes does not itself
replace or redefine the hashing operation.
Hashes are SHA-256 over exact bytes and lowercase hexadecimal. Coordinate hash
bytes are row-major triples `x,y,z` as IEEE-754 little-endian binary64 in
numeric vertex order. Triangle-index hash bytes are row-major signed
little-endian int64 indices in `(a,b,c),(a,c,d)` order. These byte strings have
no header or delimiter. A manifest hash covers the exact manifest bytes and is
referred to only by a later node in the DAG.

Every object grammar in this section is closed: listed keys are all required
and no other key is allowed. `hex64` means a lowercase 64-hex string;
`finite_number` means a non-boolean integer or finite binary64 float;
`role_path` means a nonempty canonical slash-separated role with no absolute
root, empty component, `.` component, or `..` component; `address_tuple` is
the normalized four-item JSON array defined in section 2.3; `runtime_string`
means a string whose UTF-8 encoding is at most 128 bytes;
`runtime_string-or-null` means null or `runtime_string`; `locale_string` means
a string whose UTF-8 encoding is at most 512 bytes; and `distribution_name`
means a canonical lowercase distribution name whose UTF-8 encoding is at most
128 bytes. `domain_id`, `junction_id`, and `construction_owner` are the exact
closed canonical types in sections 3.1 and 3.4; `junction_id-or-null` admits
only null or one of those seven junction IDs. Reusable records are:

```text
file_record = {role_path: role_path, bytes: nonnegative integer, sha256: hex64}
manifest_ref = {role_path: role_path, bytes: nonnegative integer,
                sha256: hex64, schema: string}
source_binding_record = {
  prepared_component: string,
  derivation_id: one of "source.dimension-value.v1",
                        "source.world-placement-axis-sum.v1",
                        "source.world-landmark-axis-sum.v1",
  source_addresses: sorted nonempty unique array of address_tuple,
  source_pointers: sorted nonempty unique array of canonical JSON-pointer strings
}
threshold_record = {threshold_id: string,
                    relation: one of "eq","ge","gt","le","lt","range",
                    lower: finite_number-or-null,
                    upper: finite_number-or-null,
                    unit: string}
gate_result = {gate_id: string, outcome: exactly "pass",
               sample_count: positive integer,
               observed_min: finite_number,
               observed_max: finite_number,
               threshold_id: string}
level_count_record = {level: integer 0..2, vertices: positive integer,
                      edges: positive integer, quads: positive integer,
                      triangles: positive integer,
                      boundary_edges: positive integer}
timing_record = {phase: string, seconds: finite nonnegative binary64}
```

Threshold arrays sort by `threshold_id`; gate-result arrays sort by `gate_id`;
file and manifest arrays sort by `role_path`; source bindings sort by
`prepared_component`; level counts and coordinate/index hash arrays sort by
`level`; every named-value array sorts by `name`; and string arrays sort by
UTF-8 bytes unless a different order is explicitly stated. A `gate_result` can occur
in a sealed successful bundle only with `outcome="pass"`, a matching declared
threshold, finite observed values where the measure is numeric, and values
that satisfy the relation. An `eq` record has equal non-null bounds; `ge` and
`gt` have only `lower`; `le` and `lt` have only `upper`; and `range` has both
with `lower<=upper`. Boolean and count bounds and observations are integers;
measured geometry, ratio, residual, angle, and timing values are binary64.
Boolean checks use observed minimum and maximum 1 against an `eq` threshold
of 1. A failed, skipped, unknown, or warning value is
not part of this algebra and cannot be serialized into a successful bundle.
Warnings remain run-local diagnostics and cannot replace a gate.

The exact runtime record grammar is:

```text
runtime_fingerprint = {
  schema: exactly "owned-root-assembly-successor-runtime.v2",
  python: {
    implementation: exactly "CPython", version: exactly "3.10.12",
    build: runtime_string, compiler: runtime_string, cache_tag: exactly "cpython-310",
    abiflags: runtime_string, soabi: runtime_string
  },
  platform: {
    system: exactly "Linux", release: runtime_string, version: runtime_string,
    machine: runtime_string, pointer_bits: positive integer,
    byteorder: one of "little","big", libc_name: runtime_string,
    libc_version: runtime_string
  },
  locale: {active: locale_string, preferred_encoding: locale_string},
  managed_launcher: file_record,
  requirements: file_record,
  direct_distributions: array of exactly three distribution_record in the
                         exact declared order,
  resolved_distributions: sorted array of exactly nine distribution_record,
  builtin_modules: array of exactly two builtin_module_record in order math,zlib
}
distribution_record = {name: distribution_name, version: runtime_string}
builtin_module_record = {
  module_name: one of "math","zlib", __file__: exactly null,
  find_spec_origin: exactly "built-in",
  compile_version: runtime_string-or-null, runtime_version: runtime_string-or-null
}
```

The direct records are exactly
`{name:"numpy",version:"2.2.6"}`,
`{name:"scikit-image",version:"0.25.2"}`, and
`{name:"pillow",version:"11.1.0"}` in that order. The resolved records are
exactly `imageio 2.37.4`, `lazy-loader 0.5`, `networkx 3.4.2`,
`numpy 2.2.6`, `packaging 26.3`, `pillow 11.1.0`, `scikit-image 0.25.2`,
`scipy 1.15.3`, and `tifffile 2025.5.10`, sorted by canonical lowercase name.
The math record requires `__file__` to be absent/`None` and
`find_spec(...).origin` to be exactly `"built-in"`; its compile and runtime
versions are null. The zlib record has the same `__file__` and origin proof,
with `compile_version` exactly `zlib.ZLIB_VERSION` and `runtime_version`
exactly `zlib.ZLIB_RUNTIME_VERSION`. Every general runtime string, distribution
name, and distribution version is at most 128 UTF-8 bytes. `locale.active` and
`locale.preferred_encoding` are each at most 512 UTF-8 bytes. The runtime
fingerprint SHA is SHA-256 of these canonical runtime-v2 JSON bytes.

### 10.2 Recipe, prepared input, manifests, and reports

The normalized recipe object has schema ID
`owned-root-assembly-successor-recipe.v1` and exactly these keys:

```text
schema, contract_role, contract_sha256, sidecar_role, source, profile_table,
profile_id, correction_round, topology_id, formula_ids, subdivision_levels,
special_case_ids, gate_set_id, renderer_id, artifact_roles, implementation_files,
runtime_fingerprint_sha256
```

`contract_role` and `sidecar_role` are the fixed roles in section 2.1;
`source` and `profile_table` are `file_record`; `profile_id` is
`standard_neutral_reference`; `correction_round` is the contract value;
`topology_id` is exactly `owned-root-58-cell-120-control-104-quad.v1`;
`formula_ids` is the sorted array of the eight dispatch formula IDs in section
4.1, including `formula.axial.station`; `special_case_ids` is the sorted array
of exactly the nine closed IDs in section 6;
`subdivision_levels` is integer 2; `gate_set_id` is exactly
`owned-root-neutral-gates.v1`; `renderer_id` is exactly
`owned-root-raster-pillow-11.1.0.v1`; `artifact_roles` is the sorted 47-role
inventory below; `implementation_files` is the sorted fifteen `file_record`
array from section 12; and `runtime_fingerprint_sha256` is `hex64`.
That hash covers the complete expanded section-10.1 runtime-v2 object. Both
input and stable manifests store that full object; a matching hash without
matching canonical runtime-v2 bytes is insufficient.
`recipe_id` is SHA-256 of this object's canonical JSON bytes. The recipe has
no `recipe_id`, seed, invocation, host path, output hash, manifest hash,
timestamp, or temporary path, so it has no hash cycle. It is reconstructed,
not published as a seventh manifest.

`prepared-input.json` is the exact closed nested object in section 2.2 encoded
by section 10.1. Its arrays retain the declared address order; provenance
source files sort by path.

The six manifest filenames and schema IDs are exactly:

```text
input-manifest.json: owned-root-assembly-successor-input-manifest.v1
coordinate-manifest.json: owned-root-assembly-successor-coordinate-manifest.v1
gate-manifest.json: owned-root-assembly-successor-gate-manifest.v1
causality-manifest.json: owned-root-assembly-successor-causality-manifest.v1
render-manifest.json: owned-root-assembly-successor-render-manifest.v1
stable-manifest.json: owned-root-assembly-successor-stable-manifest.v1
```

Their exact nested grammars are:

```text
input-manifest = {
  schema, contract_sha256: hex64, source: file_record,
  profile_table: file_record,
  profile_id: exactly "standard_neutral_reference",
  prepared_input: file_record,
  source_bindings: sorted array of exactly 92 source_binding_record,
  runtime: runtime_fingerprint,
  implementation_files: sorted array of exactly 15 file_record,
  recipe_id: hex64
}
coordinate-manifest = {
  schema, contract_sha256: hex64, input_manifest: manifest_ref,
  counts: array of exactly three level_count_record,
  coordinate_hashes: array of exactly three
      {level: integer 0..2, bytes: positive integer, sha256: hex64},
  triangle_index_hashes: array of exactly three
      {level: integer 0..2, bytes: positive integer, sha256: hex64},
  surface_artifacts: sorted array of exactly three file_record
}
gate-manifest = {
  schema, contract_sha256: hex64, coordinate_manifest: manifest_ref,
  thresholds: sorted array of exactly 357 threshold_record,
  structural: sorted array of exactly 122 gate_result,
  continuity: sorted array of exactly 144 gate_result,
  anatomy: sorted array of exactly 78 gate_result,
  intersection: sorted array of exactly 12 gate_result
}
causality-manifest = {
  schema, contract_sha256: hex64, input_manifest: manifest_ref,
  formula_records: array of exactly 120 formula_record sorted by control_id,
  source_bindings: sorted array of exactly 92 source_binding_record,
  charts: chart_summary,
  perturbations: array of exactly 33 perturbation_record sorted by parameter_id
}
formula_record = {
  control_id: section-3 exact cNNN control ID,
  lattice_key: array of exactly three integers,
  formula_id: string, construction_owner: construction_owner,
  index_parameters: closed family-dispatched object from section 4.1,
  geometry_dependencies: sorted unique string array,
  coordinate: vector3
}
dyadic = {numerator: integer, denominator: positive power-of-two integer}
         reduced to lowest terms, with zero exactly {numerator:0,denominator:1}
chart_summary = {
  level_counts: array of exactly three
      {level: integer 0..2, charts: positive integer,
       interior_transitions: nonnegative integer,
       maximum_samples_per_vertex: positive integer},
  chart_records: array of exactly 2184 sorted by chart_id, with elements
      {chart_id: section-5.1 exact chart ID, level: integer 0..2,
       face_id: section-5.1 exact level-specific face ID,
       base_face_id: section-3 exact qNNN base-face ID,
       construction_owner: domain_id,
       corners: array in face-cycle order of exactly four
           {vertex_id: section-5.1 exact level-specific vertex ID,
            u: dyadic, v: dyadic}},
  transition_records: array sorted by transition_id of exactly 4235
      {transition_id: section-5.1 exact transition ID, level: integer 0..2,
       source_chart: section-5.1 exact chart ID,
       destination_chart: section-5.1 exact chart ID,
       source_edge_slot: integer 0..3, destination_edge_slot: integer 0..3,
       endpoint_ids: array in ascending numeric vertex order at that level of
                     exactly two section-5.1 vertex IDs,
       t_destination_rule: exactly "1-t_source",
       junction_id: junction_id-or-null,
       incident_domains: array in section-3.1 catalog order with exactly one
                         domain_id when junction_id is null, otherwise exactly
                         the paired two domain_ids for that junction},
  vertex_records: array of exactly 2308 sorted by (level,numeric vertex order)
      {level: integer 0..2,
       vertex_id: section-5.1 exact level-specific vertex ID,
       samples: nonempty array sorted by (chart_id,u,v), with elements
           {chart_id: section-5.1 exact chart ID, u: dyadic, v: dyadic},
       base_control_contributors: sorted unique array of section-3 cNNN control IDs,
                                  maximum 20,
       geometry_dependency_union: sorted unique array of prepared component
                                  IDs, maximum 54,
       contributor_domains: unique domain_id array in section-3.1 catalog
                            order, maximum 5}
}
perturbation_record = {
  parameter_id: string, prepared_component: string,
  delta_m: exactly binary64 0.01,
  support_level: exactly integer 2,
  predicted_support_count: positive integer <=1737,
  observed_support_count: positive integer <=1737,
  predicted_support_sha256: hex64, observed_support_sha256: hex64,
  maximum_movement_m: positive finite binary64,
  artifact: file_record
}
render-manifest = {
  schema, contract_sha256: hex64, coordinate_manifest: manifest_ref,
  render_config: render_config_record,
  visibility: {level: exactly 2, triangle_count: exactly 3328,
               triangle_index_sha256: hex64,
               rule: exactly "larger-depth-then-lower-triangle-index"},
  artifacts: sorted array of exactly two file_record
}
stable-manifest = {
  schema, contract_sha256: hex64, recipe_id: hex64,
  runtime: runtime_fingerprint,
  implementation_files: sorted array of exactly 15 file_record,
  input_manifest: manifest_ref, coordinate_manifest: manifest_ref,
  gate_manifest: manifest_ref, causality_manifest: manifest_ref,
  render_manifest: manifest_ref,
  artifact_hashes: sorted array of exactly five file_record
}
```

Each manifest's `schema` is exactly the ID paired with its filename above.
Every `vector3` and every field declared `binary64` anywhere in these
manifests, their nested records, prepared input, run reports, the managed-test
receipt, and the comparison report uses the section-10.1 schema-aware runtime,
wire-zero, decode-coercion, and canonical re-encoding rule.
Every manifest reference uses that filename as `role_path` and its paired
schema ID. Input source/profile roles are the fixed section-2 paths and its
prepared role is `prepared-input.json`; coordinate surface roles are the three
named surface PLYs; perturbation artifacts use the exact parameter-to-filename
mapping in section 10.3; render artifacts are `direct.png` and `lineage.png`;
and stable artifact roles are exactly those three surface PLYs plus those two
PNGs. A role/schema mismatch rejects even when hash bytes happen to match.

The `formula_record` fields are exactly those required by section 4.1.
`artifact_hashes` contains only the three surface PLYs and two PNGs; prepared
input, perturbations, and implementation files are already bound by the input
or causality nodes. Stable manifests contain no absolute/temporary path,
timestamp, seed, invocation, display state, or value that differs across the
two fresh seed processes.

The managed-test receipt is a transient canonical JSON object with schema ID
`owned-root-assembly-successor-managed-test-receipt.v1`. It is staged outside
both seed bundles and has this exact closed grammar:

```text
managed_test_receipt = {
  schema: exactly "owned-root-assembly-successor-managed-test-receipt.v1",
  outcome: exactly "success",
  literal_invocation: {
    environment: exactly ["PYTHONHASHSEED=0"],
    argv: exactly
      ["experiments/owned-root-assembly-successor/build_owned_root.py",
       "--internal-managed-tests", "--receipt",
       <absolute host path to the staging managed-test-receipt.json>]
  },
  contract_sha256: hex64,
  runtime_fingerprint_sha256: hex64,
  implementation_files: sorted array of exactly 15 file_record,
  executed_test_ids: sorted nonempty unique string array,
  required_test_ids: exactly
      ["test_mesh_correctness.ProductionIntersectionFixtureTests.test_contract_fixture_matrix",
       "test_owned_root_surface.ProductionAxillaryFixtureTests.test_contract_fixture_matrix"],
  results: {tests_run: positive integer, failures: exactly 0,
            errors: exactly 0, skipped: exactly 0,
            expected_failures: exactly 0,
            unexpected_successes: exactly 0}
}
```

Both required IDs MUST occur exactly once in `executed_test_ids`. The internal
test mode snapshots the contract record, complete runtime-v2 bytes and hash,
and exact fifteen implementation `file_record`s before discovery; after all
tests it reconstructs them and requires byte-identical equality before it may
write this success receipt. `tests_run` MUST equal the cardinality of
`executed_test_ids`; zero tests, an unlisted duplicate ID, any nonzero result
count, or failure to execute exactly the 105 intersection and 13 axillary
production-fixture cases rejects without a receipt. The comparator validates
the receipt against its own current identity and both seed bundles, embeds the
validated object in the comparison report, and removes the transient staging
file before publication. The receipt is not a seed artifact, stable role, or
comparison output.

The run-local `report.json` schema ID is
`owned-root-assembly-successor-run-report.v1` and its exact grammar is:

```text
{
  schema, outcome: exactly "success", seed: one of 17,29,
  literal_invocation: {environment: array of exactly one string
                       "PYTHONHASHSEED=<seed>", argv: nonempty string array},
  output_path: absolute host path, staging_path: absolute host path,
  python_executable_path: absolute host path,
  started_utc: UTC string `YYYY-MM-DDTHH:MM:SS.ffffffZ`,
  finished_utc: UTC string `YYYY-MM-DDTHH:MM:SS.ffffffZ`,
  timings: array of exactly seven timing_record in order
           identity, prepared-input, catalogs, geometry-gates,
           causality, serialization, total-before-seal,
  runtime_fingerprint_sha256: hex64,
  stable_manifest: manifest_ref,
  gates: array of exactly six gate_result sorted by gate_id
}
```

Only this run-local report and the managed-test receipt, including its embedded
comparison-report copy, may contain literal executable, output, staging, or
temporary host paths. Its `report.sha256` is exactly one LF-terminated line
`<64 lowercase hexadecimal report SHA-256><two spaces>report.json<LF>`.
Neither file participates in stable identity or cross-seed byte comparison.
The six report `gate_id` values are exactly `seed.1.identity`,
`seed.2.prepared-input`, `seed.3.catalogs`, `seed.4.geometry-gates`,
`seed.5.causality`, and `seed.6.serialization`; each has sample count 1,
observed minimum and maximum 1, and threshold ID `gate.boolean-pass`, whose
fixed record is `{threshold_id:"gate.boolean-pass",relation:"eq",lower:1,
upper:1,unit:"dimensionless"}` and MUST be present in the gate-manifest
threshold array.
`literal_invocation.argv` is exactly the three private-builder argument strings
in order: `experiments/owned-root-assembly-successor/build_owned_root.py`,
`--output`, and that seed's absolute staging output path. It records the
private builder invocation, never the public shell launcher command;
normalization or shell-joined reconstruction is forbidden.

The final `comparison-report.json` schema ID is
`owned-root-assembly-successor-comparison-report.v1` and its exact grammar is:

```text
{
  schema, outcome: exactly "success",
  comparator: file_record,
  runtime_fingerprint_sha256: hex64,
  managed_test_receipt: managed_test_receipt,
  seed_bundles: array in seed order 17,29 of exactly
      {seed: integer, role_path: one of "seed-17","seed-29",
       stable_manifest: manifest_ref, report: file_record,
       report_sidecar: file_record},
  stable_comparisons: sorted array of exactly 45 file_record,
  excluded_run_local_roles: exactly ["report.json","report.sha256"]
}
```

Each stable comparison record contains the one byte count and SHA shared by
the two byte-identical files at that role. `comparator` is the bound
implementation `file_record` for `compare_two_seed_outputs.py`; this binds
comparator identity into completed pair evidence. The companion
`comparison-report.sha256` is exactly one LF-terminated line
`<64 lowercase hexadecimal comparison-report SHA-256><two spaces>comparison-report.json<LF>`.
In the first seed-bundle record `seed=17`, `role_path="seed-17"`, and the three
nested roles are `seed-17/stable-manifest.json`, `seed-17/report.json`, and
`seed-17/report.sha256`; the second record is the exact seed-29 analogue.
The comparator's role is exactly
`experiments/owned-root-assembly-successor/compare_two_seed_outputs.py`.
`managed_test_receipt` is the exact validated, schema-aware decoded receipt
object from the transient staging file; it is embedded before that file is
removed and introduces no additional comparison-directory role.

### 10.3 Closed inventory and acyclic hash graph

The exact successful per-seed inventory is 47 files: 3 surface PLYs, 33
perturbation PLYs, 2 PNGs, 6 manifests, 1 prepared input, 1 run report, and 1
run-report sidecar. Relative to a seed output root, the complete role inventory
is:

```text
surface-level-0.ply, surface-level-1.ply, surface-level-2.ply
perturb-left-r_y.ply, perturb-right-r_y.ply
perturb-lower_pelvis-L_y.ply, perturb-left-r_x.ply
perturb-lower_pelvis-C_z.ply,
perturb-right-r_x.ply, perturb-lower_pelvis-R_x.ply
perturb-left-r_z.ply, perturb-right-r_z.ply
perturb-lower_pelvis-R_f.ply, perturb-lower_pelvis-R_b.ply
perturb-left-thigh_start_x.ply, perturb-left-thigh_start_y.ply
perturb-left-thigh_start_z.ply, perturb-right-thigh_start_x.ply
perturb-right-thigh_start_y.ply, perturb-right-thigh_start_z.ply
perturb-neck_collar-C_y.ply, perturb-neck_collar-rL.ply
perturb-neck_upper-C_y.ply, perturb-neck_upper-rL.ply
perturb-left-axilla_x.ply, perturb-left-axilla_y.ply
perturb-right-axilla_x.ply, perturb-right-axilla_y.ply
perturb-left-peak_y.ply, perturb-right-peak_y.ply
perturb-left-start_lateral.ply, perturb-right-start_lateral.ply
perturb-left-start_up.ply, perturb-right-start_up.ply
perturb-left-shoulder_depth.ply, perturb-right-shoulder_depth.ply
direct.png, lineage.png
input-manifest.json, coordinate-manifest.json, gate-manifest.json
causality-manifest.json, render-manifest.json, stable-manifest.json
prepared-input.json, report.json, report.sha256
```

The cross-seed stable comparison set is exactly the 45 roles above after
excluding `report.json` and `report.sha256`. The exact one-way hash adjacency
list is:

```text
recipe -> contract, source, profile table, runtime fingerprint,
          15 implementation files, fixed topology/formula/gate/renderer/
          artifact-role configuration
input-manifest -> recipe_id, prepared-input, contract, source, profile table,
                  runtime fingerprint, 15 implementation files
coordinate-manifest -> input-manifest, coordinate/index byte strings,
                       3 surface PLYs
gate-manifest -> coordinate-manifest, thresholds, gate results
causality-manifest -> input-manifest, formula/source/chart records,
                      33 perturbation PLYs
render-manifest -> coordinate-manifest, renderer/visibility record, 2 PNGs
stable-manifest -> input, coordinate, gate, causality, render manifests,
                   recipe_id, runtime fingerprint, 15 implementation files,
                   3 surface PLYs, 2 PNGs
comparison-report -> validated embedded managed-test receipt, 2 closed seed
                     bundles, their 45 stable role comparisons, bound
                     comparator identity and common runtime fingerprint
```

No node hashes itself or an ancestor. A stable manifest never hashes itself,
a report, or a sidecar. The comparison report is outside both seed DAGs and is
created only after both sealed bundles exist.

### 10.4 PLY bytes

PLY serialization is ASCII 1.0 with LF, declared double coordinates, quads,
deterministic ordering, and one terminal LF. For each finite coordinate,
normalize either signed zero to integer zero, call exactly CPython 3.10.12
`format(value,'.17g')`, and canonicalize scientific notation, if present, as
`<mantissa>e<sign><absolute exponent in base-10 with no leading zeroes>` where
`sign` is exactly `+` or `-`; the mantissa is otherwise unchanged. Non-finite
values reject. Integer indices use ordinary unsigned base-10 spelling with no
leading zero except `0`. The exact header grammar is:

```text
ply
format ascii 1.0
element vertex N
property double x
property double y
property double z
element face Q
property list uchar int vertex_indices
end_header
```

The header substitutes decimal `N` and `Q`. Vertex rows follow section-6
numeric vertex order and face rows follow numeric face order; the section-5.1
IDs determine those orders but are not serialized into PLY. Each vertex row is
three canonical coordinate spellings separated by one ASCII space. Each face row is
`4 i0 i1 i2 i3`. Rows are separated by LF, with no comment, BOM, blank row, or
trailing byte after the terminal LF. The three baseline names and all 33
level-2 perturbation names are exactly the PLY roles in section 10.3. Each
perturbation PLY comes from its own fresh baseline-versus-`+0.01 m` build.

### 10.5 Exact renderer bytes

Rendering uses Pillow 11.1.0 and the level-2 arrays. Each PNG is RGB 512x1536,
made from three 512x512 panels in order front, side, 45deg. Panel-local row
`r` is written to canvas row `r`, `512+r`, or `1024+r` respectively, with the
same column. The camera vectors
are literal binary64 values:

```text
front: right=(1,0,0), up=(0,1,0), depth=(0,0,1)
side:  right=(0,0,1), up=(0,1,0), depth=(1,0,0)
45deg: right=(0.7071067811865476,0,-0.7071067811865475),
       up=(0,1,0),
       depth=(0.7071067811865475,0,0.7071067811865476)
```

With larger depth winning, the front panel exposes the anatomical `+Z`
surface from a camera on the `+Z` side looking toward `-Z`; the side panel
exposes the anatomical `+X` surface; and the 45-degree panel exposes the
front-right `(+X,+Z)` surface from that quadrant. These are the existing
gallery conventions, not interchangeable camera signs.

Let `m=fl(fl(lo+hi)/2)` componentwise for the common object-space AABB. For every
vertex and each camera, calculate `r=p-m`, then `u=dot(r,right)`,
`v=dot(r,up)`, and `z=dot(r,depth)` in section-7 order. Let `extent` be the
maximum of `abs(u)` and `abs(v)` over every projected vertex in all three
views; non-finite or nonpositive extent rejects. Compute the one common scale
as `scale=fl(232.0/extent)`. Panel coordinates are exactly
`x=fl(256.0+fl(scale*u))` and `y=fl(256.0-fl(scale*v))`; this is the required
Y inversion and leaves 24 pixels from the drawable boundary at coordinate 24
or 488. Pixel `(row,column)` has center `(column+0.5,row+0.5)` for rows and
columns 0 through 511.

Quads use triangles `(a,b,c)` then `(a,c,d)` in quad order; triangle indices
therefore ascend from 0 through 3327. For projected triangle vertices
`A=(ax,ay)`, `B=(bx,by)`, `C=(cx,cy)` and pixel center `P=(px,py)`, evaluate:

```text
d0  = fl(by-cy); d1=fl(ax-cx); d2=fl(cx-bx); d3=fl(ay-cy)
den = fl(fl(d0*d1)+fl(d2*d3))
if den is non-finite: reject rendering
if abs(den)<=1e-15: mark degenerate and stop this triangle
n0a = fl(by-cy); n0b=fl(px-cx); n0c=fl(cx-bx); n0d=fl(py-cy)
n0  = fl(fl(n0a*n0b)+fl(n0c*n0d)); w0=fl(n0/den)
n1a = fl(cy-ay); n1b=fl(px-cx); n1c=fl(ax-cx); n1d=fl(py-cy)
n1  = fl(fl(n1a*n1b)+fl(n1c*n1d)); w1=fl(n1/den)
w2  = fl(fl(1.0-w0)-w1)
depth = fl(fl(fl(w0*za)+fl(w1*zb))+fl(w2*zc))
```

After the explicit denominator test, any non-finite intermediate rejects.
A degenerate triangle draws no pixel. Otherwise the sample is included exactly when
`w0>=-1e-12`, `w1>=-1e-12`, and `w2>=-1e-12`; there is no backface culling.
Visit panels in declared order, rows top-to-bottom, columns left-to-right, and
triangles by ascending index. Each pixel starts with `has_sample=false` and no
owner; no non-finite depth sentinel is used. A sample replaces an empty pixel,
or a populated pixel when its depth is greater, or when depth is bitwise equal
and its triangle index is lower. Processing in ascending index means an equal
later sample is retained behind the earlier one. Direct and lineage rendering use identical projected triangles,
inclusion, depth, and visibility arrays.

Raster bytes use background `(247,247,247)` and direct surface
`(188,198,210)`. A lineage triangle uses exactly its base-face ancestor's
construction-owner domain palette entry; junction contributor multiplicity
never changes face colour:

```text
domain.pelvis=(214,83,83)       domain.abdomen=(226,157,68)
domain.thorax=(93,150,213)      domain.neck=(153,102,204)
domain.left_shoulder=(81,168,115)   domain.right_shoulder=(81,168,115)
domain.left_hip=(221,112,166)       domain.right_hip=(221,112,166)
```

There is no shading, lighting, label, outline, anti-aliasing, alpha, or
culling. Create each final canvas with
`Image.new("RGB",(512,1536),(247,247,247))`, copy panel rows into it in the
declared scan order, and call
`image.save(path,format="PNG",compress_level=9,optimize=False)` with no PNG
info, ICC profile, EXIF, DPI, timestamp, text, or other metadata argument.
Same-runtime reproduction is scoped to the frozen Pillow/runtime fingerprint.
The two images differ only in triangle RGB selection; lineage MUST NOT add,
hide, move, or imply an internal surface.

`render_config_record` is the closed canonical JSON projection of every
literal and vector in this subsection with exactly these keys:

```text
width, height, panel_width, panel_height, panel_order, padding,
background_rgb, direct_rgb, domain_palette, cameras, common_scale_rule,
pixel_center_rule, barycentric_tolerance, degenerate_tolerance,
depth_rule, tie_rule, quad_split, shading, lighting, labels, outlines,
anti_aliasing, alpha, culling, pillow_version, png_compress_level,
png_optimize, png_metadata
```

The exact values are `width=512`, `height=1536`, `panel_width=512`,
`panel_height=512`, `panel_order=["front","side","45deg"]`, `padding=24`, the
RGB arrays and eight-key palette above, and a three-record `cameras` array in
panel order whose records are exactly `{name,right,up,depth}` with the literal
vectors above. `common_scale_rule` is exactly
`aabb-midpoint-all-views-extent-232.v1`; `pixel_center_rule` is exactly
`column-plus-0.5-row-plus-0.5-y-down.v1`; `barycentric_tolerance=-1e-12`;
`degenerate_tolerance=1e-15`; `depth_rule="larger-depth-wins"`;
`tie_rule="lower-triangle-index-wins"`; and
`quad_split=[[0,1,2],[0,2,3]]`. All seven feature flags are `false`;
`pillow_version="11.1.0"`; `png_compress_level=9`; `png_optimize=false`; and
`png_metadata` is exactly the empty object. Maps have no other keys.

## 11. Paths, launcher, and reproducibility

The four fixed orchestration/private-executable and sidecar paths are exactly
(the contract, source, and profile paths are fixed inputs in section 2, not
entries in this list):

```text
experiments/owned-root-assembly-successor/owned_root_launcher.sh
experiments/owned-root-assembly-successor/build_owned_root.py
experiments/owned-root-assembly-successor/compare_two_seed_outputs.py
experiments/owned-root-assembly-successor/design-contract.sha256
```

`owned_root_launcher.sh` is the only public execution entrypoint. From the
repository root its one exact invocation form is:

```bash
PYTHONHASHSEED=0 experiments/owned-root-assembly-successor/owned_root_launcher.sh --output ABSENT_PATH
```

`ABSENT_PATH` MUST be an absolute fresh absent path. The launcher accepts
exactly `--output PATH`, requires literal `PYTHONHASHSEED=0`, and rejects every
other argument, environment hash seed, existing output target, missing fixed
file identity, or static identity mismatch before source admission or staging.
Contract, sidecar, source, profile, runtime, implementation allowlist, builder,
and comparator paths are fixed here rather than caller-selectable.

After static admission the public launcher selects, but does not create, a
fresh private sibling staging-root path on the output filesystem. It invokes
these private managed commands in order through the repository-owned
current-form launcher:

```bash
PYTHONHASHSEED=0 experiments/current-form-surface-preview/surface_preview_launcher.sh \
  experiments/owned-root-assembly-successor/build_owned_root.py \
  --internal-managed-tests \
  --receipt "$STAGING/managed-test-receipt.json"

PYTHONHASHSEED=17 experiments/current-form-surface-preview/surface_preview_launcher.sh \
  experiments/owned-root-assembly-successor/build_owned_root.py \
  --output "$STAGING/seed-17"

PYTHONHASHSEED=29 experiments/current-form-surface-preview/surface_preview_launcher.sh \
  experiments/owned-root-assembly-successor/build_owned_root.py \
  --output "$STAGING/seed-29"

PYTHONHASHSEED=0 experiments/current-form-surface-preview/surface_preview_launcher.sh \
  experiments/owned-root-assembly-successor/compare_two_seed_outputs.py \
  "$STAGING/seed-17" "$STAGING/seed-29" \
  --test-receipt "$STAGING/managed-test-receipt.json" \
  --output "$STAGING/comparison"
```

`$STAGING` denotes the launcher's absolute invocation-owned staging path; it
is not a caller input. Before creating `$STAGING`, the first private test mode
rechecks every fixed file identity, constructs and admits the complete runtime
identity, and admits no source geometry. It discovers `test_*.py` under
`experiments/owned-root-assembly-successor/tests` with `unittest`
programmatically and produces only the section-10.2 receipt after satisfying
its exact identities, result counts, required test IDs, 105 intersection
cases, and 13 axillary cases. Only then may it create `$STAGING` and atomically
stage the receipt. Managed tests MUST NOT invoke the public
`owned_root_launcher.sh`; they invoke production functions and, where needed,
the private builder modes directly, so orchestration cannot recurse.

After the comparator succeeds and the transient receipt is removed, the
public launcher requires the closed staging root:

```text
seed-17/     exactly 47 files
seed-29/     exactly 47 files
comparison/ exactly comparison-report.json and comparison-report.sha256
```

It then atomically publishes that complete three-directory outer root at
`ABSENT_PATH` with a no-replace rename. There is no standalone public unit-test,
seed-builder, or comparator command and no alternate multi-command evidence
sequence.

The sidecar is exactly one LF-terminated line:

```text
<64 lowercase hexadecimal contract SHA-256><two spaces>experiments/owned-root-assembly-successor/design-contract.md<LF>
```

The two spaces and the exact repository-relative path are required; no BOM,
extra line, or alternate path is accepted. After fresh review, the final
contract SHA is materialized as an independent literal named
EXPECTED_CONTRACT_SHA256 in both owned_root_launcher.sh and build_owned_root.py.
Both literals MUST equal the SHA of the exact contract bytes and MUST be
checked independently of the sidecar. During this pre-build candidate pass
the literal and sidecar are intentionally absent; an empty, placeholder, or
caller-supplied identity MUST fail before source admission. The README anchor
for the final contract SHA is likewise intentionally absent and may be added
only after fresh review; this candidate does not create or update it.

The launcher MUST use the repository-pinned current-form-surface environment,
record the complete runtime-v2 identity, and validate the runtime-v2 grammar and
all runtime string, locale string, and canonical runtime JSON size caps before
source admission. Each private seed builder independently rechecks all fixed
identities and runs section-13 groups 1 through 6 before atomically sealing its
closed 47-file staging bundle. A sealed seed bundle is diagnostic input to the
comparison, not completed experiment evidence. Failure of tests, either
builder, comparison, receipt removal, closed-root validation, or publication
emits nothing at `ABSENT_PATH`; cleanup is limited to invocation-owned staging.
Large meshes, PNGs, caches, captures, and datasets remain outside Git under the
artifact policy.

Bare system Python and ambient package imports are forbidden. The private
comparator requires literal `PYTHONHASHSEED=0` and accepts exactly, in order,
the seed-17 bundle path, the seed-29 bundle path,
`--test-receipt RECEIPT_PATH`, and `--output COMPARISON_PATH`. Both option
paths MUST be absolute staging paths, the receipt MUST be the one just produced
by this orchestration, and the comparison path MUST be fresh and absent.

The comparator and public launcher perform these six ordered stages:

1. **Structure and receipt admission:** require both exact closed 47-file seed
   inventories, regular-file and size rules, report-sidecar lexical grammars,
   and the canonical transient managed-test receipt at the exact staging path.
2. **Identity:** require contract, sidecar, both code literals, source,
   profile, recipe, all 15 implementation records, the current runtime, both
   seed runtime records, and every receipt identity and result count to agree.
3. **Stable DAG and gates:** validate each manifest in
   `input -> coordinate -> gate -> causality -> render -> stable` dependency
   order, including schemas, canonical bytes, references, hashes, exact gate
   inventories, all 357 thresholds, and successful gate algebra. This does not
   independently rerun the six seed-local groups or pre-validate their
   run-report stage records, which belong to stage 5.
4. **Stable comparison:** compare exactly the 45 stable roles in ascending
   UTF-8 role order and require byte identity.
5. **Reports and sidecars:** process seed 17 and then seed 29; validate each
   run-local report completely, including its six stage-result records and
   stable-manifest reference, and then validate its report sidecar. Reports
   remain excluded from stable comparison.
6. **Pair and outer publication:** embed the validated managed-test receipt,
   construct and atomically seal the exact two-file comparison directory,
   remove the transient staging receipt, then let the public launcher validate
   and atomically publish the exact three-directory outer root.

Each seed builder and the comparator independently constructs the complete
section-10.1 runtime-v2 fingerprint after its runtime admission checks. During
stage 2 the comparator requires its own canonical fingerprint bytes and hash,
the seed-17 runtime object, and the seed-29 runtime object to be identical;
the comparison report records that one common hash.

Only boundaries between these six stages define failure precedence. Within a
failed stage the implementation may aggregate diagnostics and sort them by
UTF-8 identifier for reproducibility, but the contract chooses no primary
failure and no intra-stage diagnostic order is evidence semantics. Any failed
stage exits 1 and stage 6 publishes neither the comparison directory nor outer
root; success exits 0. Those are the only specified exit codes. Only the
successfully published outer root, containing the two sealed seed bundles and
two-file comparison directory, is completed technical evidence.

The pinned requirements path is
`experiments/current-form-surface-preview/requirements.txt`, whose complete
package set is exactly `numpy==2.2.6`, `scikit-image==0.25.2`, and
`Pillow==11.1.0`. The managed launcher is the fixed
`experiments/current-form-surface-preview/surface_preview_launcher.sh` file
record. Any other external shell helper is an operational prerequisite only:
if it is absent or fails, launch stops before source admission, and it is not
part of stable identity.

The runtime-v2 fields have these exact meanings. The managed launcher and
requirements are raw regular-file `file_record`s at their fixed role paths.
`python` is read from the running interpreter and requires
`platform.python_implementation() == "CPython"`,
`platform.python_version() == "3.10.12"`, `platform.python_build()` joined by
one ASCII space for `build`, `platform.python_compiler()` for `compiler`,
`sys.implementation.cache_tag == "cpython-310"`, `sys.abiflags` for
`abiflags`, and `sysconfig.get_config_var("SOABI")` for `soabi`. Each value
is a `runtime_string`; missing or mismatched values reject.
No Python executable bytes, path, role, or hash are admitted.

`platform` uses the exact strings from `platform.system()`,
`platform.release()`, `platform.version()`, and `platform.machine()`, exactly
`Linux` for `system`, `8*struct.calcsize("P")` for `pointer_bits`,
`sys.byteorder` for `byteorder`, and the two `runtime_string` values from
`platform.libc_ver()` for `libc_name` and `libc_version`. `locale.active` is
`locale.setlocale(locale.LC_ALL,None)` and `locale.preferred_encoding` is
`locale.getpreferredencoding(False)`; both are recorded as `locale_string`
values, each with its separate 512-byte cap. The builder changes neither and
does not freeze a current locale literal.

Canonical distribution naming lowercases ASCII and replaces each maximal run
of `-`, `_`, or `.` with one `-`; any other name byte rejects. Direct records
are obtained from the fixed requirements and must be exactly the three
lowercase records in the grammar. Resolved records are obtained by exact
metadata version lookup for the nine names in the grammar and must match the
exact sorted name/version list. No distribution-file attestation, installation
tree enumeration, module-file record, or native-file attestation is performed
or serialized.

The builder imports `math` and `zlib` and independently checks that each
module's `__file__` is absent or `None` and that
`importlib.util.find_spec(module_name).origin == "built-in"`. The ordered
`builtin_modules` records use null `compile_version` and `runtime_version` for
math. The zlib record uses the exact strings `zlib.ZLIB_VERSION` and
`zlib.ZLIB_RUNTIME_VERSION` for those two fields. No standard-library file
record is admitted.

Every seed builder and the comparator independently constructs the complete
runtime-v2 object, canonicalizes its JSON bytes, and hashes those bytes. The
only runtime claim is byte identity across two fresh hash-seed processes when
the recorded CPython build, platform, dependency versions, managed launch
source, contract, source, and implementation are the same. This does not
claim hermetic recreation, wheel/native equivalence across separate installs,
or adversarial supply-chain integrity. Runtime JSON bytes and its hash are
full manifest inputs; host paths, timestamps, temporary paths, and external
shell-helper state remain run-local or operational only.


The four paths at the start of this section are fixed candidate identity,
public-orchestration, or private-executable roles; they are not by themselves
an implementation-file allowlist.
Exactly three of them -- `owned_root_launcher.sh`, `build_owned_root.py`, and
`compare_two_seed_outputs.py` -- are also members of the exhaustive fifteen-
file implementation package in section 12. The sidecar is not implementation.
The contract, sidecar, source, profile table, current-form launcher, and
requirements file are the exhaustive fixed admitted identity inputs outside
that fifteen-file package. This intentional three-path overlap is the complete
reconciliation of the lists and authorizes no other source file. Future
implementation files may be absent in this pre-build state, but before a build
the launcher and builder independently require all fifteen implementation
files, reject symlinks, special files, or any additional implementation
source, and bind each canonical role, raw byte count, and SHA-256 into the
input manifest and stable identity.
This complete identity and allowlist check occurs before source admission or
creation of staging or output.

## 12. Complexity and source budgets

These are hard caps, not permissions to fill them:

```text
domains: exactly 8, cap <=8, all nonempty
junctions: exactly 7, cap <=7
open ports: exactly 5, cap <=5
base controls: cap <=128, candidate exact 120
base quads: cap <=120, candidate exact 104
subdivision levels: exactly 2
unique geometry dependencies: exactly 92 used
dependencies per formula record: <=12
lineage contributors per vertex: <=20
dependency union per vertex: <=54
contributor domains per vertex: <=5
special-case IDs: exactly 9, with no unnamed case
topology decision sites: <=3
triangles per intersection run: <=4096
broad-phase candidates: <=1,000,000
active-set candidate subsets per shared-one pair: exactly 11 (6+4+1)
active-set evaluated attempts per shared-one pair: <=11
exact PNG pixels: 786432 per PNG, exactly 2 PNGs, <=2 MiB each
surface PLY files: exactly 3, <=2 MiB each
perturbation PLY files: exactly 33, <=2 MiB each
causality manifest: <=8 MiB
every other JSON artifact: <=2 MiB
non-test physical LOC: <=3400
test physical LOC: <=2600
```

The following resource caps are fixed, with no wall-clock or RSS gate:

```text
requirements file: <=64 KiB
managed launcher: <=4,000,000 bytes
runtime JSON: <=64 KiB
runtime and distribution strings other than the two locale fields: <=128 UTF-8 bytes
locale.active and locale.preferred_encoding: <=512 UTF-8 bytes each
resolved distributions: exactly 9
repository implementation input files: <=4,000,000 bytes each
published output artifacts: <=256 MiB each
```

The runtime/distribution string caps, the separate locale caps, and the
canonical runtime JSON cap are checked before source admission and do not
authorize an omitted runtime-v2 field or distribution record. The exact-nine
resolved distribution set and the exact two built-in module records remain
mandatory.

The implementation allowlist is exact and missing, additional, non-regular,
or byte-drifted implementation source files fail closed before source
admission. Every path has one `file_record` in both the input-manifest and
stable-manifest:

```text
experiments/owned-root-assembly-successor/build_owned_root.py
experiments/owned-root-assembly-successor/prepared_projection.py
experiments/owned-root-assembly-successor/owned_root_surface.py
experiments/owned-root-assembly-successor/mesh_correctness.py
experiments/owned-root-assembly-successor/render_export.py
experiments/owned-root-assembly-successor/owned_root_launcher.sh
experiments/owned-root-assembly-successor/compare_two_seed_outputs.py
experiments/owned-root-assembly-successor/artifact_serialization.py
experiments/owned-root-assembly-successor/anatomy_gates.py
experiments/owned-root-assembly-successor/chart_lineage.py
experiments/owned-root-assembly-successor/tests/test_build_owned_root.py
experiments/owned-root-assembly-successor/tests/test_prepared_projection.py
experiments/owned-root-assembly-successor/tests/test_owned_root_surface.py
experiments/owned-root-assembly-successor/tests/test_mesh_correctness.py
experiments/owned-root-assembly-successor/tests/test_render_export.py
```

The first ten paths are production files and the final five are test files;
this single 15-path list is the exhaustive package allowlist. Package-local
implementation source means every recursively discovered regular `.py` or
`.sh` file under `experiments/owned-root-assembly-successor`; the discovered
set MUST equal this list, and no differently suffixed package-local file may be
executed or imported. Documentation and the future SHA sidecar are identity
inputs, not implementation source.

The implementation files are measured from the package root and test files
from its `tests/` directory with GNU `wc -l`:

```bash
wc -l -- experiments/owned-root-assembly-successor/build_owned_root.py experiments/owned-root-assembly-successor/prepared_projection.py experiments/owned-root-assembly-successor/owned_root_surface.py experiments/owned-root-assembly-successor/mesh_correctness.py experiments/owned-root-assembly-successor/render_export.py experiments/owned-root-assembly-successor/owned_root_launcher.sh experiments/owned-root-assembly-successor/compare_two_seed_outputs.py experiments/owned-root-assembly-successor/artifact_serialization.py experiments/owned-root-assembly-successor/anatomy_gates.py experiments/owned-root-assembly-successor/chart_lineage.py
wc -l -- experiments/owned-root-assembly-successor/tests/test_build_owned_root.py experiments/owned-root-assembly-successor/tests/test_prepared_projection.py experiments/owned-root-assembly-successor/tests/test_owned_root_surface.py experiments/owned-root-assembly-successor/tests/test_mesh_correctness.py experiments/owned-root-assembly-successor/tests/test_render_export.py
```

The sums of the first and second commands MUST remain within their respective
caps. The nine special-case IDs, exact allowlists, chart counts, and topology
catalog are closed sets; compressing code or omitting tests does not authorize
removing a required check.

## 13. Seed-local gate and pair-publication order

Before sealing one seed bundle, the per-seed builder MUST verify these six
groups in order:

1. contract/sidecar, all fixed input and runtime identities, the exact
   implementation allowlist, and recipe identity;
2. exact prepared schema, source bindings, metre behavior, neutral profile,
   provenance cardinality, and non-geometric exclusions;
3. topology, ownership, junction, port, chart, transition, and special-case
   catalogs and the eleven static catalog Boolean checks;
4. inside the existing `geometry-gates` timing, execute
   `structural.catalog_boolean.axillary_fixture_suite_complete` and then
   `structural.catalog_boolean.intersection_fixture_suite_complete` in
   ascending UTF-8 gate-ID order, independently running the exact 13-case
   axillary catalog and exact 105-execution intersection catalog through their
   production predicates; then verify finite coordinates, structural floors,
   subdivision, lineage, continuity, winding, folds, clearances, anatomy
   selectors/gates, and intersection policy;
5. analytic causality for all 33 must-affect parameters, perturbation movement,
   serialized difference, and locality; and
6. canonical manifests/PLYs, same-surface direct/lineage rendering, closed
   47-role inventory, resource/LOC caps, and run-report sidecar.

The two fixture-suite Booleans are structural gate results despite executing
in group 4 rather than the static-catalog work in group 3. They reuse the
existing `geometry-gates` timing record, create no timing or gate stage, and
emit no artifact. The public launcher's mandatory internal managed tests in
section 11 precede both private seed builders and do not replace either
builder's independent group-4 self-check.

The builder MUST publish no partial result after any failed group and MUST NOT
invoke or require the comparator: its own bundle cannot be compared before it
exists. After the two independently seeded private builders atomically seal
their staging bundles, the public orchestration invokes the private comparator
and completes section 11's ordered publication. The pair is incomplete
diagnostic material until the exact outer root is atomically published. The
direct and lineage diagnostics are two colourings of the same final evaluated
surface. No label, manifest, internal model review, or one seed's success can
replace the corresponding geometry, byte comparison, or later visual evidence.

## 14. Neutral-only lock and future activation boundary

This section is explicitly neutral-only. Passing every neutral technical gate,
plus a recorded main-thread inspection that finds the fixed neutral cues
credible, makes this candidate eligible for a separately SHA-256-bound
`exact-five-activation-contract.md`; it does not activate exact-five and does
not authorize exact-five output, gallery work, or a human checkpoint by itself.
The canonical prohibition on exact-five work before credible neutral remains
in force.

The future additive activation contract may define only base-neutral
identity/evidence, the ordered five profile IDs, exact profile projection,
invocation/identity, and publication/comparison. It MUST freeze the 92-
component profile mapping, decimal factor and ties-to-even millimetre
projection, identity rotations and local landmarks, profile-placement parsing,
dual source/profile pointers, and fail-closed rule uniqueness. Geometry sees
numbers only and never a profile ID.

That additive contract MUST NOT alter topology, formulas, tunables, thresholds,
gates, subdivision, ownership, causality, or renderer. It has its own exact
allowlist, hashes, and literals, and its additive freeze consumes zero
geometry corrections from this contract. The exact-five output cardinality is
intentionally undefined until that activation contract exists. If activated,
its profile order is exactly:

```text
standard_neutral_reference
compact_broad_short_limb_large_head
tall_narrow_long_legged
slender_long_limb
stocky_broad_chested
```

## 15. Exclusions and disposition

The prior seven-ring topology, projection, formulas, macros, candidate IDs,
thresholds, loops, and anatomy-specific tests are hard-excluded from this
candidate. Only separately audited representation-independent generic
utilities may be reused. No seven-ring branch, fallback, hidden surface,
global remesh, solver, or render correction may enter this implementation.

This contract freezes a reproducible candidate design; it does not claim that
the candidate is implemented or good. The preliminary evidence remains
incomplete as stated in section 1. If the initial build plus two permitted shared
corrections still fails a frozen gate or the fixed visual cues, the candidate
is rejected or inconclusive and archived. Do not tune indefinitely, run
exact-five early, add distal anatomy or a tail, or silently switch
representations. A different representation requires a newly recorded runway
and human authorization.

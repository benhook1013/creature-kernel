# Owned root assembly successor exact-five activation contract

Status: Proposed additive experiment-local execution contract; freeze-pending;
implementation not claimed

Authority: this document is permitted only by section 14 of the frozen
`design-contract.md` and the experiment README. It is not product,
specification, architecture, Stage 1, production, or technology acceptance.

## 1. Scope, authority, and fail-closed rule

This contract proposes only the exact-five numeric expansion of the completed
owned-root standard-neutral experiment. It defines selection, projection,
execution, comparison, and publication around the existing neutral geometry
representation. It does not change that representation.

This draft and its sidecar identify the exact candidate bytes submitted for
review. They do not record acceptance or a completed freeze. The authoritative
geometry contract remains
`experiments/owned-root-assembly-successor/design-contract.md`, exactly 173184
bytes at SHA-256
`3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490`.
Every topology, formula, tunable, threshold, gate, subdivision stencil,
ownership rule, causality rule, PLY encoding, and renderer rule is incorporated
unchanged. `correction_round` remains `0`. If accepted, this additive freeze
consumes zero geometry corrections.

Any missing, duplicate, unknown, additional, reordered, byte-drifted,
noncanonical, non-finite, ambiguously selected, or differently derived input,
record, component, gate, artifact, or implementation role rejects before
publication. A failed run publishes nothing. There is no warning, skipped
profile, fallback profile, partial success, best-effort output, or caller
override.

The following are forbidden: profile-specific corrections; profile-aware
topology, formulas, tunables, thresholds, gates, subdivision, ownership,
causality, or rendering; a second or hidden surface; a new prepared or geometry
representation; post-generation coordinate edits; remeshing; solving;
optimization; render-only correction; distal anatomy; tail work; optional
module expansion; and any production claim. Profile labels, IDs, source
pointers, profile pointers, provenance, and branch decisions MUST NOT enter
surface logic.

## 2. Exact identities and ordered profiles

The fixed input records are:

```text
activation contract:
  experiments/owned-root-assembly-successor/exact-five-activation-contract.md
activation sidecar:
  experiments/owned-root-assembly-successor/exact-five-activation-contract.sha256
design contract:
  experiments/owned-root-assembly-successor/design-contract.md
  bytes 173184
  sha256 3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490
authored source:
  examples/body-documents/stylized-digitigrade-biped-authored-form.json
  bytes 56984
  sha256 82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14
profile table:
  experiments/current-form-surface-preview/structural_profile_candidates.json
  bytes 29970
  sha256 a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640
profile transform source:
  experiments/current-form-surface-preview/generate_structural_profile_sources.py
neutral projection source:
  experiments/owned-root-assembly-successor/prepared_projection.py
neutral builder source:
  experiments/owned-root-assembly-successor/build_owned_root.py
```

The exact existing semantics-bearing dependencies admitted from the post-seam
evidence are:

```text
experiments/owned-root-assembly-successor/anatomy_gates.py
  bytes 25674 sha256 0c4b5f7812141a4cd7c7107655e578044355dfef5dbda6574bbb63bc359a2ff4
experiments/owned-root-assembly-successor/artifact_serialization.py
  bytes 27977 sha256 3837928e4b987c65fd773e540f7db502f5d9a0b4c5940b95c923953754fdf7d4
experiments/owned-root-assembly-successor/build_owned_root.py
  bytes 78268 sha256 713cbf967bf2e0e233bae0c3506199fdc9a6ed71418edbd8dbf9b75beeee4045
experiments/owned-root-assembly-successor/chart_lineage.py
  bytes 18263 sha256 01fdd09e8e0bb6d31851f0c7af711d90b313e36a012dbe3d71415a0468c31efc
experiments/owned-root-assembly-successor/mesh_correctness.py
  bytes 51035 sha256 4104b70e70e958a469125d1fff544e20fee44b784bf7915d8e724e63d4f39db1
experiments/owned-root-assembly-successor/owned_root_surface.py
  bytes 58732 sha256 c982d889fee30e2efea881b5725170740bc8afa2a883aa3dc4623941cd3e2a22
experiments/owned-root-assembly-successor/prepared_projection.py
  bytes 39646 sha256 58637097a350332db40368a027347ec395192880aa6ba4782c7d523e5b288190
experiments/owned-root-assembly-successor/render_export.py
  bytes 15933 sha256 bc251ea3f3f3cb1aa5ea66bfc4f79a82f86191e76bacb9a3c4f58e64883c4780
experiments/current-form-surface-preview/generate_structural_profile_sources.py
  bytes 54437 sha256 009be817cd2ec2db663b668fb5c9bdfa7296936283322e59d7a145e3d3cfec62
experiments/current-form-surface-preview/structural_atomic_publish.py
  bytes 10489 sha256 5e648b3a1a3519afdf0fc1f2f1ecfe6fe7f1c58130f71fd2c8ee4317e2f282b5
experiments/current-form-surface-preview/surface_preview_launcher.sh
  bytes 6582 sha256 3e18da2d361029a16558757d9727150d54c4d691b35c6a2a21b5b51cb7785190
experiments/current-form-surface-preview/requirements.txt
  bytes 49 sha256 69a3ce10b1f993d7913f02ca187eabb8d367abf214662ffa2132feacbdeedbec
```

The first eight records are the existing neutral runtime semantics used by the
activation. The profile generator and its direct local import own the admitted
profile-transform semantics. The launcher and requirements own the managed
runtime. Missing, additional, changed, or substituted records reject before
source admission. The post-seam stable-manifest identity additionally binds
the complete existing fifteen-file neutral implementation and test package;
this additive contract does not restate or weaken that closed identity.

The four new additive files in section 9 are an exact allowlist. Because they
do not yet exist, this Proposed contract does not prehash them. At execution
each is admitted as a regular `file_record`; the exact sorted four-record array
is included in every profile-seed evidence file and final evidence. The
additive implementation MUST independently bind the exact activation-contract
SHA-256 in its public launcher and runner, in addition to validating the
sidecar. It MUST bind every fixed record above before source admission. The
sidecar grammar is section 12.

The sole admitted profile order is:

```text
0 standard_neutral_reference
1 compact_broad_short_limb_large_head
2 tall_narrow_long_legged
3 slender_long_limb
4 stocky_broad_chested
```

The profile table MUST have exactly its existing five rows in this order. Each
row MUST have exactly `dimension_scales`, `id`, `label`, and
`part_placements`; IDs and labels MUST be nonempty and unique. Transform
signatures, defined as the sorted complete placement map paired with the sorted
complete scale map, MUST be pairwise distinct. Selection is by one exact ID
match after the complete table has passed admission. Zero or multiple matches,
an unknown requested ID, index-only selection, label selection, reordered
rows, duplicate IDs or labels, or a transform-signature collision rejects.
The launcher itself requests no profile; it always executes all five in the
fixed order.

The post-seam neutral baseline identity is:

```text
comparison-report.json:
  bytes 24640
  sha256 fe450e9047275c517de297f50b9ed7881c969fd2c315e9714334dcb8d9e68f2a
comparison-report.sha256:
  bytes 89
  sha256 27d4941acc57c9a800c2ee76205dd349f401f900d6ed0ee01b3d07925df85dac
stable-manifest.json sha256, identically in seed 17 and seed 29:
  1b4aaed96671a55ae65dc163fd80db45288daf1b9dc9c91745bf19e414fa7ffa
direct.png sha256:
  b98d9cf219cad3c60ce43921fc86be7817529fd93448386860738b60110075ed
lineage.png sha256:
  19a006f8f237857d94821894016364dcc446caece3358e9c6da0794a75bf74d2
runtime fingerprint sha256:
  c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085
```

The baseline path is a caller-supplied locator, never identity or stable
evidence. The public launcher requires `--baseline-root BASELINE_ROOT`, where
`BASELINE_ROOT` is an existing canonical absolute directory disjoint from the
output and every invocation staging path. Any identity-equivalent relocation
is admitted; any content drift rejects through the complete checks below. The
retained reports correctly preserve their original staging paths, so the
current path-bound `build_owned_root.validate_seed_bundle` and
`compare_two_seed_outputs.outer_publication_inventory` APIs MUST NOT be called
on this relocated publication and their private helpers MUST NOT be imported.

Instead, the launcher performs one exact activation-local, path-neutral byte
admission before creating profile staging, and the publisher independently
repeats it before creating public staging after all ten profile bundles exist.
Using stable,
no-follow reads, reject symlinks, external hardlinks, special nodes, unexpected
or empty directories, size-cap violations, or anything except the exact outer
directories `seed-17`, `seed-29`, and `comparison`. Require exactly 47 unique
canonical roles from `build_owned_root.ARTIFACT_ROLES` in each seed and exactly
`comparison-report.json` plus its sidecar in `comparison`, for 96 files total.
The exact 45 stable roles are that 47-role tuple minus only `report.json` and
`report.sha256`, sorted by UTF-8 bytes.

The comparison report bytes and sidecar MUST match the fixed hash above and
the existing closed comparison-report schema. Require outcome `success`; the
fixed runtime fingerprint; the exact comparator implementation record; exact
excluded roles `report.json` and `report.sha256`; seed bundles in order 17 then
29; and exactly 45 sorted, unique stable comparison records. Every stable
record MUST match the byte count and SHA-256 of the same current role in both
seed directories. Each seed-bundle record for its report, report sidecar, and
stable manifest MUST match the current file with its exact prefixed role; each
report sidecar MUST hash its report; and both stable manifests MUST have the
fixed identical hash above.

Decode and validate the embedded neutral managed-test receipt path-neutrally:
the exact existing closed schema, contract/runtime/15-file implementation
identities, required-test IDs, exactly 134 executed passing tests, and all six
failure/skip counters zero. Validate each report as canonical closed JSON with
the correct seed, success outcome, runtime hash, stable-manifest reference,
phase order, and six all-pass gates. Historical path fields remain provenance:
require their own internal agreement, canonical absoluteness, correct seed
basename and staging relationship, but never equality to the relocated root.
After its fixed hash matches, validate each stable manifest as canonical closed
JSON with the design-contract identity, recipe, runtime, 15-file identity, and
five exact manifest references. Re-admit the complete 96-file baseline after
all payload comparisons and copies to close the read window.

This proves narrowly that every retained byte is identical to the exact bytes
certified by the fixed pre-rename comparison report; it is not a general or
fresh semantic validator for arbitrary neutral output. A matching headline
hash without the complete admission above is insufficient.

Standard-neutral regression equality covers exactly these 38
implementation-independent payload roles and no others: the three baseline
surface PLYs, all 33 perturbation PLYs, `direct.png`, and `lineage.png`.
Manifests, prepared input, reports, sidecars, receipts, recipes, and other
records that bind implementation files are explicitly excluded. Each of the
38 exact records is taken from the admitted post-seam comparison report and
must match both baseline seeds. This contract does not claim that an
exact-five implementation or run exists.

## 3. Closed profile-table admission

The active transform rules are the exact data and selector semantics of the
frozen profile table and the active-five mode of
`generate_structural_profile_sources.py`. The table has exactly the five rows
above, exactly the existing 37 positive integer `dimension_scales` keys per
row, and exactly the existing 18 typed `part_placements` keys per row. Every
scale is an integer in `1..10000`; every placement is exactly three integers,
each in `-1000000000..1000000000`. The table's `dimension_groups`,
`placement_targets`, `preserved_controls`, `reference_edges`, and
`rotation_policy` objects are closed and are admitted exactly as implemented
by that source. No caller may supply a replacement transform table.

Every source dimension MUST match exactly one dimension group, and every group
MUST match at least one source dimension. Every source part MUST match exactly
one placement target, and every profile's placement map MUST cover every and
only those targets. Typed address keys use exactly
`namespace|kind|comma-separated-anchors|role`; malformed or unknown addresses
reject. Source part, landmark, frame, and dimension selection uses the unique
normalized-address rules of design-contract sections 2.2 through 2.4.

All source rotations in parts, frames, joints, sockets, and attachments MUST
be the authored identity rotation `[0,0,0,1]` and MUST be copied unchanged.
All landmark positions, frame transforms, joint frames, socket frames, and
attachment offsets MUST be copied unchanged. Part placements are replaced
only by the selected row's complete placement map. Attachment equations,
containment, the declared reference edge, bilateral neutral-pose symmetry,
axial centerline, and shoulder-root/neck-base alignment MUST pass after
replacement. Tail data is validated only because it is in the frozen table;
it is excluded before the 92-component projection and MUST NOT be constructed,
tested as geometry, rendered, or published by this activation.

For `standard_neutral_reference`, every scale MUST equal `1000` and every
placement vector MUST equal its authored-source vector. Any difference rejects.

## 4. Exact decimal projection into 92 numbers

### 4.1 Numeric rule

For each selected source dimension decimal token `v` in metres and its unique
selected integer-permille scale `s`, parse `v` as an exact finite positive
decimal, not binary64. Compute with sufficient decimal precision to make the
following multiplication exact:

```text
scaled_millimetres = Decimal(v) * Decimal(s)
q = scaled_millimetres rounded to an integer with ROUND_HALF_EVEN
projected_metres_decimal = q / Decimal(1000)
```

Thus a discarded fractional millimetre less than `0.5` rounds down, greater
than `0.5` rounds up, and exactly `0.5` rounds to the even integer millimetre.
There is no preliminary binary64 conversion, `/1000` source reinterpretation,
double rounding, truncation, stochastic rounding, or profile exception.
Convert the final exact decimal metre value to finite Python `float` only after
quantization. It MUST round-trip through `Decimal(str(float_value))` to the
exact projected decimal; otherwise reject. Positive source dimensions that
quantize to zero, overflow, or become non-finite reject.

Selected placement vectors are exact integer metres from the profile row.
Convert each used placement coordinate directly to finite Python `float`.
Local landmark coordinates remain the unchanged authored finite binary64
metres. World sums use the exact containment chains and binary64 primitive
order in design-contract section 2.3. No placement value is scaled by a
dimension factor.

The standard-neutral row executes this same rule. Its resulting 92-number
carrier MUST produce the exact 38 payload roles named in section 2
byte-identically to both admitted post-seam baseline seed bundles.
Implementation-bearing manifests are not compared. Failure is a seam
regression and rejects the entire exact-five publication.

No profile-local prepared semantic object, prepared-input artifact, or second
prepared schema exists in this activation. The runner validates the fixed
source and complete profile table, selects one exact row, applies the admitted
profile transform to an invocation-local copy, and projects that validated
copy directly into the existing `GeometryComponents` carrier while producing
the evidence records below. The profile-local copy is neither passed across
the geometry seam nor serialized. This direct projector is activation-local
selection/projection logic, not a new geometry or prepared representation.

### 4.2 Component order and mapping

The existing `GeometryComponents` carrier and its exact 92-ID family inventory
are unchanged:

```text
stations.<station>.C.x, .C.y, .C.z, .rL, .rA, .rP
  for lower_pelvis, upper_pelvis, lower_abdomen, waist_abdomen,
      upper_abdomen, lower_ribcage, upper_ribcage_shoulder,
      neck_collar, neck_upper                                  54
shoulders.<side>.axilla.x, .y, .z, peak.x, .y, .z,
  arm_origin.x, .y, .z, start_lateral, start_up,
  start_forward, shoulder_depth
  for left, right                                             26
hips.<side>.P_s.x, .y, .z, r_x, r_y, r_z
  for left, right                                             12
                                                            total 92
```

The displayed family order above is descriptive, not positional. The sole
carrier order is the frozen implementation's exact
`GEOMETRY_COMPONENT_IDS`: form the complete 92-ID inventory above and sort it
globally by UTF-8 bytes. Thus all `hips.*` IDs precede all `shoulders.*` IDs,
which precede all `stations.*` IDs. Projection, `projected_values`, carrier
bytes, binding records, and component-index causality selectors MUST all use
that one global order; no family-local or table-display order is permitted.

Projection first creates a profile-local copy of the admitted source by the
rules above, then executes the existing unique selectors and aliases. The
closed mapping from the 92 components to profile data is:

| component family | profile placement input | dimension-scale group |
| --- | --- | --- |
| pelvis/torso station `C` | complete owner containment chain | none; local landmark unchanged |
| pelvis/torso station `rL` | none | `body_profile_lateral` |
| pelvis/torso station `rA`,`rP` | none | `body_profile_depth` |
| neck station `C` | pelvis, torso, neck chain | none; local landmark unchanged |
| neck station `rL` | none | `neck_profile_lateral` |
| neck station `rA`,`rP` | none | `neck_profile_forward` |
| shoulder `axilla`,`peak` | pelvis, torso, selected upper-arm chain | none; local landmarks unchanged |
| shoulder `arm_origin` | pelvis, torso, selected upper-arm chain | none |
| shoulder `start_lateral` | none | `arm_profile_lateral` |
| shoulder `start_up` | none | `arm_profile_up` |
| shoulder `start_forward` | none | `arm_profile_forward` |
| shoulder `shoulder_depth` | none | `arm_shoulder` |
| hip `P_s` | pelvis and selected thigh chain | none; local landmark unchanged |
| hip `r_x` | none | `leg_profile_lateral` |
| hip `r_y` | none | `leg_profile_up` |
| hip `r_z` | none | `leg_profile_forward` |

Every one of the 92 projected components has exactly one closed
`projection_binding_record`:

```text
{
  prepared_component: one exact GeometryComponents ID,
  derivation_id: one of
    "profile.dimension-permille-half-even-mm.v1",
    "profile.world-placement-axis-sum.v1",
    "profile.world-landmark-axis-sum.v1",
  source_addresses: nonempty sorted unique address_tuple array,
  source_pointers: nonempty sorted unique canonical RFC-6901 pointer array,
  profile_pointers: nonempty sorted unique canonical RFC-6901 pointer array
}
```

The source pointers are exactly the design-contract section-2.4 pointers. For
a scaled dimension, `profile_pointers` contains exactly
`/profiles/<profile-index>/dimension_scales/<group>`. For a world placement
sum it contains the matching pointer for every placement in the fixed chain:
`/profiles/<profile-index>/part_placements/<escaped-address-key>/<axis-index>`.
For a world landmark sum, `profile_pointers` contains exactly those placement
pointers. The source landmark pointer remains in `source_pointers`; no profile
landmark pointer is invented. A dimension record retains its source dimension
pointer and adds its one scale pointer. RFC-6901 escaping is `~` to `~0` and `/` to `~1`; profile
indices and axis indices use unsigned base-10 without leading zeroes. Arrays
sort by UTF-8 bytes. Empty, duplicate, missing, extra, differently grouped, or
pointer-inconsistent bindings reject.

The projected value crosses the geometry seam as only
`GeometryComponents(tuple_of_92_finite_binary64_values)`. Geometry MUST consume
only that existing 92-number geometry carrier. It MUST never receive or read
the authored JSON, generated profile JSON, profile table, prepared semantic
object, profile ID, index, label, pointer, provenance, or selection result.
The surface API accepts that carrier and nothing profile-shaped. Static and
managed tests MUST prove that those forbidden objects cannot be passed to or
observed by `owned_root_surface.py`, anatomy gates, mesh checks, subdivision,
causality, PLY serialization, or rendering. Dispatch on a projected numeric
value to infer a profile is equally forbidden.

## 5. Unchanged geometry and per-profile gates

For each profile and each seed, construction executes the design contract
without alteration: exact topology ID
`owned-root-58-cell-120-control-104-quad.v1`; 120 controls; 104 base quads;
the same eight nonempty domains, seven junctions, five ports, eight formula
IDs, nine special-case IDs, two subdivision levels, ownership and chart
catalogs, thresholds, and renderer ID
`owned-root-raster-pillow-11.1.0.v1`. Level counts remain exactly:

```text
level 0: 120 vertices, 227 edges, 104 quads, 208 triangles, 38 boundary edges
level 1: 451 vertices, 870 edges, 416 quads, 832 triangles, 76 boundary edges
level 2: 1737 vertices, 3404 edges, 1664 quads, 3328 triangles, 152 boundary edges
```

Every profile independently runs the six ordered seed-local groups in design
contract section 13. Every exact gate and threshold inventory remains closed:
122 structural, 144 continuity, 78 anatomy, and 12 intersection gate results,
with 357 threshold records. Every result MUST pass its unchanged threshold.
No profile aggregate, average, ranking, exception, relaxed threshold, or
visual judgment can replace one failed gate.

Randomness is forbidden. Nevertheless, every profile MUST execute in two
fresh processes, once with literal `PYTHONHASHSEED=17` and once with literal
`PYTHONHASHSEED=29`. Missing, ambient, `0`, or any other seed rejects. The two
seeds are a hash-order determinism challenge only and MUST NOT be consumed as
random or geometry input. For each profile, every stable value and ephemeral
artifact byte sequence MUST be identical across seeds, including the ordered
92 values, projection bindings, three surface PLYs, 33
perturbation PLYs, gate data, causality data, and two PNGs. Run-local paths,
timestamps, and timings are excluded from equality but remain validated.

## 6. Exact 33 copied-component causality gates

For every profile under both seeds, independently execute all 33 existing
must-affect parameters in this exact order and with these exact selectors:

```text
left.r_y -> hips.left.r_y
right.r_y -> hips.right.r_y
lower_pelvis.L_y -> stations.lower_pelvis.C.y
lower_pelvis.C_z -> stations.lower_pelvis.C.z
left.r_x -> hips.left.r_x
right.r_x -> hips.right.r_x
lower_pelvis.R_x -> stations.lower_pelvis.rL
left.r_z -> hips.left.r_z
right.r_z -> hips.right.r_z
lower_pelvis.R_f -> stations.lower_pelvis.rA
lower_pelvis.R_b -> stations.lower_pelvis.rP
left.thigh_start_x -> hips.left.P_s.x
left.thigh_start_y -> hips.left.P_s.y
left.thigh_start_z -> hips.left.P_s.z
right.thigh_start_x -> hips.right.P_s.x
right.thigh_start_y -> hips.right.P_s.y
right.thigh_start_z -> hips.right.P_s.z
neck_collar.C_y -> stations.neck_collar.C.y
neck_collar.rL -> stations.neck_collar.rL
neck_upper.C_y -> stations.neck_upper.C.y
neck_upper.rL -> stations.neck_upper.rL
left.axilla_x -> shoulders.left.axilla.x
left.axilla_y -> shoulders.left.axilla.y
right.axilla_x -> shoulders.right.axilla.x
right.axilla_y -> shoulders.right.axilla.y
left.peak_y -> shoulders.left.peak.y
right.peak_y -> shoulders.right.peak.y
left.start_lateral -> shoulders.left.start_lateral
right.start_lateral -> shoulders.right.start_lateral
left.start_up -> shoulders.left.start_up
right.start_up -> shoulders.right.start_up
left.shoulder_depth -> shoulders.left.shoulder_depth
right.shoulder_depth -> shoulders.right.shoulder_depth
```

Each perturbation copies that profile's validated 92-value tuple, adds exactly
binary64 `+0.01 m` (`float.fromhex("0x1.47ae147ae147bp-7")`) to the one selected
component, proves by exact tuple restoration that no other component changed,
wraps the copied tuple in a fresh identity-free `GeometryComponents` carrier,
and builds a fresh level-2 surface. The perturbation does not modify the source
or profile table and does not re-run profile projection with a changed scale.

For every perturbation, all design-contract section-9 obligations remain
exact: nonempty analytic predicted support; predicted and observed support
sets and `CKSUPPORTv1` hashes equal; maximum movement at least
`0x1.d14e3bcd35a85p-11 m`; off-support movement at most the unchanged `T`;
436 supported vertices for each thigh-start-x case; unchanged topology, IDs,
formulas, ownership, lineage, and quads; and level-2 PLY bytes different from
that profile's baseline. Every perturbation PLY is ephemeral, capped at 2 MiB,
hashed into stable evidence, compared across seeds, and removed before final
publication. There are exactly `5 * 2 * 33 = 330` perturbation executions and
no committed perturbation binary.

## 7. Activation-local bundle and evidence schemas

All JSON uses the design-contract section-10.1 canonical JSON and binary64
rules: closed schema before use, duplicate-key rejection, schema-aware zero
coercion, exact canonical re-encoding, no BOM, and no trailing LF. Hashes are
lowercase SHA-256 of exact raw bytes. `file_record`, `manifest_ref`,
`gate_result`, `threshold_record`, and `timing_record` retain their existing
meanings.

### 7.0 Additive managed-test receipt

Before any profile build, `exact_five_runner.py` executes its private
`--internal-managed-tests --receipt ABSENT_CANONICAL_PATH` mode under literal
`PYTHONHASHSEED=0`. The receipt is canonical JSON with schema
`owned-root-assembly-successor-exact-five-managed-test-receipt.v1` and exactly:

```text
{
  schema, outcome: exactly "success",
  invocation: {
    environment: exactly ["PYTHONHASHSEED=0"],
    implementation_role: exactly
      "experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py",
    mode: exactly "managed-tests"
  },
  activation_contract: file_record,
  design_contract: file_record,
  existing_dependencies: exact sorted 12-file dependency array from section 2,
  additive_implementation_files: exact sorted four-file file_record array,
  runtime: exact design-contract runtime_fingerprint,
  runtime_fingerprint_sha256: hex64,
  executed_test_ids: sorted nonempty unique string array,
  required_test_ids: exact sorted array listed below,
  results: {
    tests_run: exactly the executed_test_ids count,
    failures: 0, errors: 0, skipped: 0,
    expected_failures: 0, unexpected_successes: 0
  }
}
```

The exact required IDs are:

```text
test_exact_five_activation.ExactFiveActivationTests.test_all_33_selectors_copy_one_component
test_exact_five_activation.ExactFiveActivationTests.test_atomic_failure_has_no_partial_publication
test_exact_five_activation.ExactFiveActivationTests.test_decimal_half_even_boundaries
test_exact_five_activation.ExactFiveActivationTests.test_final_evidence_schema_and_19_file_closure
test_exact_five_activation.ExactFiveActivationTests.test_geometry_receives_only_components
test_exact_five_activation.ExactFiveActivationTests.test_neutral_projection_preserves_38_payloads
test_exact_five_activation.ExactFiveActivationTests.test_profile_seed_bundle_schema_and_closure
test_exact_five_activation.ExactFiveActivationTests.test_profile_table_closed_and_exact_order
test_exact_five_activation.ExactFiveActivationTests.test_profile_table_rejects_duplicate_keys_and_signatures
test_exact_five_activation.ExactFiveActivationTests.test_projection_has_exact_92_bindings
test_exact_five_activation.ExactFiveActivationTests.test_seed_dispatch_is_exact
test_exact_five_activation.ExactFiveActivationTests.test_static_identity_and_allowlist
```

Every required ID occurs exactly once in `executed_test_ids`; additional
discovered IDs are allowed only when they are also recorded, unique, and pass.
The runner compares all fixed and implementation identities before and after
test execution. Any changed identity, missing required ID, nonzero result,
skip, expected failure, unexpected success, malformed receipt, or receipt
path that already exists rejects before any profile output is created.
The launcher validates and retains the exact canonical receipt bytes. The
publisher independently reads the unchanged invocation-owned file, validates
the same closed object and identities, embeds the complete decoded object and
its raw-byte SHA-256 in final evidence, and never rewrites the receipt.

### 7.1 Exact 42-file profile/seed bundle

Each of the ten profile/seed executions seals exactly 42 files:

```text
surface-level-0.ply
surface-level-1.ply
surface-level-2.ply
the exact 33 perturb-<parameter>.ply roles from section 6, replacing every
  "." in the parameter ID with "-" and changing no underscore
direct.png
lineage.png
profile-seed-evidence.json
profile-seed-evidence.sha256
run-report.json
run-report.sha256
```

The first 38 roles are the payload set. The stable cross-seed set is exactly
those 38 payloads plus `profile-seed-evidence.json` and
`profile-seed-evidence.sha256`, for 40 roles. `run-report.json` and
`run-report.sha256` are the only excluded run-local roles. The evidence has no
seed, path, timestamp, timing, or temporary value, so its bytes and sidecar
MUST match across seeds.

`profile-seed-evidence.json` has schema
`owned-root-assembly-successor-profile-seed-evidence.v1` and exactly:

```text
{
  schema, outcome: exactly "success",
  activation_contract: file_record,
  design_contract: file_record,
  source: file_record,
  profile_table: file_record,
  existing_dependencies: exact sorted 12-file dependency array listed in
                         section 2,
  additive_implementation_files: exact sorted four-file file_record array,
  runtime: exact design-contract runtime_fingerprint,
  runtime_fingerprint_sha256: hex64,
  profile_id, profile_index,
  selection: {profile_pointer, profile_row_sha256,
              dimension_scales_sha256, part_placements_sha256},
  projected_values: array of exactly 92 projected_value_record in
                    GeometryComponents order,
  projected_carrier: {bytes, sha256} for the canonical 92-value array,
  projection_bindings: array of exactly 92 projection_binding_record sorted
                       by prepared_component,
  levels: array in level order 0,1,2 of exactly {
    level, counts: level_count_record,
    coordinate_bytes, coordinate_sha256,
    triangle_index_bytes, triangle_index_sha256,
    ply: file_record
  },
  thresholds: sorted array of exactly 357 threshold_record,
  gates: {
    structural: sorted 122 gate_result array,
    continuity: sorted 144 gate_result array,
    anatomy: sorted 78 gate_result array,
    intersection: sorted 12 gate_result array
  },
  causality: sorted array of exactly 33 causality_evidence records,
  renders: {
    renderer_id,
    render_config: exact render_export.render_config_record object,
    render_config_sha256,
    visibility: exact render_export.visibility_record object,
    visibility_sha256,
    direct: file_record, lineage: file_record,
    same_surface_positions_sha256, same_surface_triangles_sha256
  },
  payloads: sorted array of exactly 38 file_record,
  invariants: {
    topology_equal_to_neutral: exactly true,
    formulas_equal_to_neutral: exactly true,
    tunables_equal_to_neutral: exactly true,
    thresholds_equal_to_neutral: exactly true,
    gate_inventory_equal_to_neutral: exactly true,
    subdivision_equal_to_neutral: exactly true,
    ownership_equal_to_neutral: exactly true,
    causality_rules_equal_to_neutral: exactly true,
    renderer_equal_to_neutral: exactly true
  }
}
```

A `projected_value_record` is exactly
`{prepared_component,value:binary64,source_pointers,profile_pointers}` and MUST
agree with its binding. `projected_carrier` is exactly the byte count and
SHA-256 of canonical JSON encoding of the array of the 92 `value` fields in
`GeometryComponents` order. The runner computes it from the carrier; the
publisher reconstructs those bytes from `projected_values`, validates the
record, and therefore compares the exact carrier across seeds through the
already-stable evidence file. It is not a file record and adds no bundle role.
A selection hash always means SHA-256 of canonical JSON bytes: the complete
selected profile row for `profile_row_sha256`, its complete
`dimension_scales` object for `dimension_scales_sha256`, and its complete
`part_placements` object for `part_placements_sha256`. The publisher locates
the row again by the exact profile ID and index in the admitted fixed table,
recreates all three preimages, and requires all three hashes.
`profile_pointer` MUST equal `/profiles/<profile_index>` with the index written
as unsigned base-10 without leading zeroes, and resolving that pointer in the
admitted table MUST produce that same selected complete row.

`render_config_sha256` is SHA-256 of canonical JSON bytes of the adjacent
complete `render_config` object; the publisher validates that object through
`render_export.validate_render_config` and recreates the hash.
`visibility_sha256` is SHA-256 of canonical JSON bytes of the adjacent complete
`visibility` object returned by `render_export.visibility_record`; the
publisher requires its exact closed keys and recreates the hash.
`same_surface_positions_sha256` MUST equal the level-2 `coordinate_sha256`.
`same_surface_triangles_sha256` MUST equal both the level-2
`triangle_index_sha256` and `visibility.triangle_index_sha256`. The runner MUST
obtain `direct`, `lineage`, and the one shared visibility value from exactly
one `render_export.render_pair_bytes(level_2_mesh)` call; separately rebuilding
either image or its visibility is forbidden. These relations bind both image
records to one admitted level-2 surface without embedding the raster buffer.

A `causality_evidence` record is exactly the existing
design-contract perturbation record, including its payload `file_record`.
The three level records expose all PLY, coordinate, and triangle-index hashes.
The evidence exposes every projection/source pointer, all 92 values, all gate
results, all 33 causality records, render identities, and the complete payload
inventory without embedding binary bytes.

The profile/seed `run-report.json` has schema
`owned-root-assembly-successor-profile-seed-run-report.v1`. It contains exactly
the profile ID and index, seed 17 or 29, literal private invocation, output and
staging paths, interpreter path, UTC start/finish values, the seven ordered
phase timings `identity`, `selection-projection`, `catalogs`,
`geometry-gates`, `causality`, `serialization`, and `total-before-seal`,
runtime fingerprint hash, a `manifest_ref` to
`profile-seed-evidence.json`, and the six existing all-pass seed gate results.
Its sidecar uses section 12. The report MUST NOT be referenced by evidence.

### 7.2 Cross-seed and post-seam comparison

For each profile, the publisher compares the two closed 42-file bundles and
requires byte equality of exactly the 40 stable roles. It validates both run
reports and sidecars separately and excludes them from equality. A comparison
record is exactly `{role_path,bytes,sha256}` and records the one common byte
count and hash after both seed files have been proven equal.

For standard neutral only, the publisher additionally compares exactly the 38
payload records against the same roles in seed 17 and seed 29 of the admitted
post-seam baseline. Every byte count and hash MUST agree. It never compares the
activation evidence, sidecars, reports, or any neutral manifest.

### 7.3 Final exact-five evidence and run report

`exact-five-evidence.json` has schema
`owned-root-assembly-successor-exact-five-evidence.v1` and exactly:

```text
{
  schema, outcome: exactly "success",
  activation_contract: file_record,
  design_contract: file_record,
  source: file_record,
  profile_table: file_record,
  existing_dependencies: exact sorted 12-file dependency array listed in
                         section 2,
  additive_implementation_files: exact sorted four-file file_record array,
  managed_tests: {
    receipt_sha256: SHA-256 of the exact canonical receipt bytes,
    receipt: complete decoded section-7.0 managed-test receipt object
  },
  neutral_baseline: {
    comparison_report: file_record,
    stable_manifest_sha256: hex64,
    runtime_fingerprint_sha256: hex64,
    payload_comparisons: sorted array of exactly 38 comparison_record
  },
  runtime: exact design-contract runtime_fingerprint,
  runtime_fingerprint_sha256: hex64,
  profile_order: exact five-ID array,
  profiles: array in profile order of exactly five {
    profile_id, profile_index,
    evidence: complete decoded profile-seed-evidence object,
    stable_cross_seed_comparisons: sorted array of exactly 40 comparison_record,
    neutral_payload_comparisons: exactly 38 comparison_record for profile 0,
                                 exactly empty for profiles 1..4
  },
  payloads: sorted array of exactly 15 public file_record
}
```

The final evidence contains only backward references to the 15 already sealed
public payloads and the already completed managed-test receipt. It does not
contain a record for itself, its sidecar, the final run report, or the report
sidecar. `managed_tests.receipt_sha256` MUST match the canonical bytes of its
embedded complete receipt object before the temporary receipt is removed. The
embedded profile evidence preserves all
projection pointers, 92 values, three-level hashes, gate results, causality
records with ephemeral perturbation PLY hashes, render identities, and
comparisons after the profile/seed bundles are removed. Its
managed-test receipt does not claim publication or passage of the section-11
gate; the launcher establishes those after the final rename.

The final `run-report.json` has schema
`owned-root-assembly-successor-exact-five-run-report.v1` and exactly:

```text
{
  schema, outcome: exactly "success",
  literal_invocation: {environment: exactly ["PYTHONHASHSEED=0"],
                       argv: exact public argv array},
  output_path, staging_path, python_executable_path: canonical absolute paths,
  neutral_baseline_path: exactly the caller-supplied canonical BASELINE_ROOT,
  started_utc, finished_utc: fixed-format UTC strings,
  timings: ordered nonnegative timing_record array for identity, managed-tests,
           launcher-baseline-admission, profile-seed-builds,
           publisher-baseline-admission, comparison, pre-report-closure,
           total-before-seal,
  activation_contract_sha256, design_contract_sha256,
  runtime_fingerprint_sha256: hex64,
  evidence: manifest_ref for exact-five-evidence.json,
  evidence_sidecar: file_record for exact-five-evidence.sha256,
  payloads: sorted array of exactly 15 file_record,
  profile_seed_runs: array in profile order and seed order of exactly ten {
      profile_id, seed, outcome:"success", evidence_sha256:hex64},
  gates: array in exact ID order of exactly 21 all-pass Boolean gate_result
         records
}
```

Before invoking the publisher, the launcher creates one canonical closed
`owned-root-assembly-successor-exact-five-launcher-context.v1` temporary record
containing exactly the public `literal_invocation`, `output_path`,
`neutral_baseline_path`, and the first four timing records in the order
`identity`, `managed-tests`, `launcher-baseline-admission`, and
`profile-seed-builds`. The publisher admits that record and copies those exact
values into the final report. It independently measures the next three phases.
`total-before-seal` is exactly the arithmetic sum, in binary64 list order, of
the preceding seven timing seconds; it is not an inferred wall-clock interval.

The final report is created only after the evidence sidecar exists and the
publisher has re-admitted the exact 17-file pre-report closure: 15 payloads,
evidence, and evidence sidecar. The `publisher-baseline-admission` timing and gate record
only the publisher's independent admission performed before public staging;
the launcher's earlier pre-profile admission is reported only by the distinct
`launcher-baseline-admission` timing copied from the launcher-context record
and does not satisfy or replace the publisher's gate. The
`pre-report-closure` timing and gate record only that 17-file admission. The
report contains no record for itself or its own sidecar. After writing the
report and sidecar, the publisher re-admits the exact 19-file staging closure;
that necessarily later fact is not asserted inside the report. The launcher
then independently repeats the 19-file admission. Run-local values occur only
in reports.
The 21 gate IDs, in exact order, are:

```text
exact-five.run.01.identity
exact-five.run.02.managed-tests
exact-five.run.03.publisher-baseline-admission
exact-five.run.04.profile.standard_neutral_reference.seed-17
exact-five.run.05.profile.standard_neutral_reference.seed-29
exact-five.run.06.profile.compact_broad_short_limb_large_head.seed-17
exact-five.run.07.profile.compact_broad_short_limb_large_head.seed-29
exact-five.run.08.profile.tall_narrow_long_legged.seed-17
exact-five.run.09.profile.tall_narrow_long_legged.seed-29
exact-five.run.10.profile.slender_long_limb.seed-17
exact-five.run.11.profile.slender_long_limb.seed-29
exact-five.run.12.profile.stocky_broad_chested.seed-17
exact-five.run.13.profile.stocky_broad_chested.seed-29
exact-five.run.14.profile.standard_neutral_reference.cross-seed
exact-five.run.15.profile.compact_broad_short_limb_large_head.cross-seed
exact-five.run.16.profile.tall_narrow_long_legged.cross-seed
exact-five.run.17.profile.slender_long_limb.cross-seed
exact-five.run.18.profile.stocky_broad_chested.cross-seed
exact-five.run.19.standard-neutral-payload-equality
exact-five.run.20.evidence-graph
exact-five.run.21.pre-report-closure
```

Each observes integer 1 against `gate.boolean-pass`. None claims that the
later launcher-owned rename has already occurred.

## 8. Exact public inventory and acyclic publication graph

The publisher's successful staging root contains exactly 19 regular files and
no symlinks, hardlinks, sockets, devices, FIFOs, empty directories, or
additional entries:

```text
standard_neutral_reference/surface-level-2.ply
standard_neutral_reference/direct.png
standard_neutral_reference/lineage.png
compact_broad_short_limb_large_head/surface-level-2.ply
compact_broad_short_limb_large_head/direct.png
compact_broad_short_limb_large_head/lineage.png
tall_narrow_long_legged/surface-level-2.ply
tall_narrow_long_legged/direct.png
tall_narrow_long_legged/lineage.png
slender_long_limb/surface-level-2.ply
slender_long_limb/direct.png
slender_long_limb/lineage.png
stocky_broad_chested/surface-level-2.ply
stocky_broad_chested/direct.png
stocky_broad_chested/lineage.png
exact-five-evidence.json
exact-five-evidence.sha256
run-report.json
run-report.sha256
```

The one-way final hash graph is exact:

```text
managed-test receipt + 15 payloads -> exact-five-evidence.json
exact-five-evidence.json -> exact-five-evidence.sha256
launcher context + 15 payloads + evidence + evidence sidecar -> run-report.json
run-report.json -> run-report.sha256
```

No node hashes itself or a descendant. The launcher re-admits the exact graph
and 19-file closure after the publisher seals staging. PLY and PNG bytes remain
unchanged from design-contract sections 10.4 and 10.5. Each PNG is one
metadata-free 512x1536 RGB image containing front, side, and 45-degree panels
in that order; direct and lineage images use identical level-2 positions,
triangles, visibility, and camera calculation.

All 15 payloads remain external/local under the repository artifact policy and
MUST NOT be committed by this activation. The ten 42-file profile/seed
bundles, levels 0 and 1, 330 perturbation PLYs, managed-test receipt, and
launcher-context record are invocation-owned ephemeral material. They remain until the final evidence and
report are sealed, then the launcher removes only its exact staging inputs
before publication. A cleanup or closed-inventory failure rejects publication.

## 9. Entrypoints and ordered execution

The future sibling implementation package is exactly
`experiments/owned-root-assembly-successor-exact-five/`; placing executable
files under the neutral package is forbidden because that package has its own
closed 15-file implementation allowlist. The exact additive allowlist is:

```text
experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh
experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py
experiments/owned-root-assembly-successor-exact-five/exact_five_publisher.py
experiments/owned-root-assembly-successor-exact-five/tests/test_exact_five_activation.py
```

This is the complete sibling package source inventory. A gallery adapter is a
later, separate implementation and is not admitted, predeclared, or counted by
this contract.

The only public command, from repository root, is:

```bash
PYTHONHASHSEED=0 experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh --baseline-root BASELINE_ROOT --output ABSENT_PATH
```

`BASELINE_ROOT` MUST be the existing canonical absolute directory described in
section 2. `ABSENT_PATH` MUST be a canonical absolute path without empty, `.`
or `..` components. It and every invocation-owned sibling staging path MUST be
absent and disjoint from `BASELINE_ROOT`. The launcher accepts exactly those
four arguments in that order, requires literal seed `0`, treats the baseline
path only as a locator, binds all identities and the exact four-file allowlist
before source admission, and creates no output on failure.

The launcher uses the existing pinned
`surface_preview_launcher.sh` and requirements/runtime-v2 environment. In an
invocation-owned absent staging root it performs, in order:

1. Invoke `exact_five_runner.py --internal-managed-tests --receipt
   <staging-receipt-path>` under `PYTHONHASHSEED=0`; require the exact
   section-7.0 canonical success receipt and no skipped, expected-failure, or
   unexpected-success result.
2. Fully admit `BASELINE_ROOT` and record the
   `launcher-baseline-admission` timing.
3. For each profile in exact order, invoke `exact_five_runner.py --profile
   <exact-id> --output <staging-profile-seed-path>` first with
   `PYTHONHASHSEED=17`, then with `PYTHONHASHSEED=29`.
4. Seal the exact launcher-context record defined in section 7.3, then invoke
   `exact_five_publisher.py` under `PYTHONHASHSEED=0` with exactly
   `BASELINE_ROOT`, ten sealed sibling bundle paths in fixed profile/seed
   order, the managed-test receipt, the launcher-context record, and one absent
   staging-publication path. These are private fixed-shape arguments, not a
   public interface.
5. The publisher re-admits every bundle, validates all schemas and gates,
   performs every cross-seed and neutral-baseline comparison, creates and seals
   the exact 19-file staging tree, and re-admits that sealed tree. It returns
   success without deleting inputs or publishing the final path.
6. The launcher independently re-admits the sealed staging tree, removes only
   its exact invocation-owned ephemeral bundle, receipt, and launcher-context
   paths, verifies that cleanup did not alter the sealed tree, performs the sole
   final no-replace rename to `ABSENT_PATH`, and returns success only when that
   rename succeeds.

The runner owns profile-table admission, unique selection, decimal projection,
the identity-free 92-number handoff, unchanged geometry execution, all gates,
and sealing one closed ephemeral 42-file bundle. Its private managed-test mode
accepts only literal seed 0 and the exact section-7.0 arguments. Its private
profile-build mode accepts only one of the five exact IDs and only seed 17 or
29. It cannot publish public evidence or invoke the publisher. The publisher
cannot construct geometry, project a
profile, rerun a failed gate, rewrite a bundle, or choose a preferred seed; it
only admits, compares, summarizes, seals, and re-admits the staging
publication. It cannot rename to the public target or clean staging. The
launcher alone owns final cleanup and publication. All three independently
bind the contract, fixed sources, implementation files, and runtime.

The managed tests MUST include closed-table rejection, duplicate-key
rejection, unique profile/source selection, all 92 binding/pointer mappings,
decimal half-even boundary cases, neutral projection equality, identity-only
geometry API shape, both exact seeds for all profiles, all 33 copied-component
selectors, evidence schema/cardinalities, exact 19-file closure, sidecar
grammar, an identity-equivalent relocated-baseline success case, baseline
content-drift rejection, and atomic no-partial-output failure tests. Tests do
not replace any runtime gate.

## 10. Resource and cardinality caps

These are hard maxima, not implementation targets:

```text
profiles: exactly 5
hash-seed processes: exactly 2 per profile, values 17 and 29
ephemeral seed bundles: exactly 10, each exactly 42 files
stable cross-seed roles per profile: exactly 40
payload roles per profile/seed: exactly 38
geometry components: exactly 92 per profile
projection bindings: exactly 92 per profile
geometry gate results: exactly 356 per profile per seed
threshold records: exactly 357 per profile per seed
causality perturbations: exactly 33 per profile per seed
perturbation executions: exactly 330
published files: exactly 19
published level-2 PLYs: exactly 5, <=2 MiB each
published PNGs: exactly 10, 786432 pixels and <=2 MiB each
ephemeral surface or perturbation PLY: <=2 MiB each
exact-five-evidence.json: <=16 MiB
run-report.json: <=2 MiB
each sidecar: <=256 bytes
each staging evidence file or receipt: <=16 MiB
complete staging root: <=512 MiB
complete published root: <=32 MiB
runtime JSON: <=64 KiB
launcher-context record: <=64 KiB
each additive implementation file: <=4 MiB
additive non-test physical LOC: <=1600
additive test physical LOC: <=1200
```

Physical LOC is measured with GNU `wc -l` over the exact allowlist, separating
the first three files from the test file. Existing neutral implementation LOC
is not charged again and MUST remain byte-identical to its admitted post-seam
identity throughout an invocation. There is no wall-clock or RSS pass gate.

## 11. Technical-to-visual gate

The exact technical-to-visual gate passes only after the publisher has sealed
and re-admitted one exact 19-file staging root and the launcher has atomically
published that unchanged root, with all of the following true: fixed
identities match; managed tests pass; all five profiles pass every unchanged
technical gate under both seeds; all 33 causality gates pass for every
profile/seed; all 40-role cross-seed comparisons are byte-equal; standard neutral is
byte-equal to all 38 payload roles in both admitted post-seam baseline seed
bundles; the public evidence is complete and canonical; and the direct and
lineage renders are proven to use the same evaluated surface.

Only then may a gallery present the five profiles in section-2 order, standard
neutral first. For each profile it MUST show the published direct final skin
and same-surface lineage diagnostic, preserving the fixed front, side, and
three-quarter panels. It may not crop away a panel, substitute a mesh, add an
x-ray structure, relight, smooth, recolour the direct skin, or regenerate an
image. The exact files and hashes presented MUST be those in
`exact-five-evidence.json`.

The resulting checkpoint is Ben's retained visual judgment of the exact
artifact set: whether the neck, shoulder/axilla, pelvic-wrap, and downward
thigh-root cues remain credible across all five profiles and whether this
representation is worth extending. Internal metrics, model reviews, technical
gate success, or one convincing profile do not substitute for that judgment.
No merge, product promise, architecture acceptance, distal anatomy, tail work,
or further representation work follows without Ben's explicit direction.

## 12. Sidecars and disposition

Every sidecar is one ASCII, LF-terminated `sha256sum` line with exactly two
spaces:

```text
<64 lowercase hex><two spaces><repository-relative-or-local-role><LF>
```

The repository sidecar role is exactly
`experiments/owned-root-assembly-successor/exact-five-activation-contract.md`.
Each ephemeral bundle sidecar names exactly `profile-seed-evidence.json` or
`run-report.json`. Final sidecars name exactly `exact-five-evidence.json` and
`run-report.json`. No BOM, extra line, absolute path, or alternate spelling is
admitted.

This Proposed document defines an implementation-ready, freeze-pending
activation protocol. It does not
claim that the sibling implementation, post-seam exact-five evidence, gallery,
or human acceptance exists. Any need to change neutral geometry, introduce a
profile-specific rule, exceed a cap, alter the 19-file inventory, or weaken a
gate rejects this activation and returns to the main thread for a new recorded
decision.

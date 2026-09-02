# Disposable current-form surface preview

This is an exploratory visual workbench documenting the historical, closed
four-variant
`creature-kernel.provisional-form-preview.v11` envelope. It converts the
source-authored canonical metre-valued dimensions into analytic ellipsoid,
capsule, and linear-radius tapered-segment fields, folds them in stable full-
AddressKey order, and extracts a bounded continuous surface on a fixed uniform
grid. The source contains 153 canonical metre-valued dimensions. The
provisional display adapter explicitly derives retained descriptor-local integer
`*_permille` fields for its display controls; those fields are not authored
dimension units. Profile factors are separate integer-permille inputs applied at
the display/profile boundary. Active generated-profile output applies those
factors with exact decimal arithmetic, quantizes to the nearest millimetre
using ties-to-even, and emits canonical metres.

It is not a production geometry system, SDF contract, collision system,
animation topology, rig, skin, runtime, Readiness 3/4 proof, or DR-0009/0010
evidence. Winner labels are debug attribution only. Generated bundles belong
in `/tmp` and must not be committed.

The four-variant v9 path below is historical closed-candidate reproduction. It
is distinct from the later regional candidate's exact-five attempts, which
failed before rendering or publication. Fresh candidate generation or
publication requires a new Ben-authorized runway; historical reproduction
remains available through the documented commands.

The historical integrated candidate is producer v11 with
`authored_foot_profile` v1:
153 authored dimensions, 43 authored landmarks, and 16 authored frames. The
historical diagnostic target is baseline preview format v3, regional guide
v11, and successor preview v9. Producer v11 and `authored_foot_profile` v1 remain
the source identities. The historical successor region/profile identity is
`successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-hip-root-sweeps-v16`.
This v16 hip-root successor derives one four-station pelvis-to-thigh
socket/cup/tangent-blend route per side from the lower-pelvis cage and authored
thigh-root controls. It consumes the complete baseline field inventory and
retains zero temporary bridge fields.
The exact foot route is `hock -> metatarsal midpoint -> pad ->
pad-toe midpoint -> toe`: the hock is shin-owned, the other four stations are
foot-owned, and the route carries full lateral/up/forward radii, outer caps,
four spans, and exact producer/guide/successor lineage and cross-binding.
The final publication context cap is 12 KiB only for the exact subject-context
carrier; ordinary strings remain capped at 8192 characters. Existing
immutable sessions retain the format and captures with which they were
published. This diagnostic was published as an immutable historical session;
it does not create a current checkpoint or rewrite an older session.

The compiler-owned middle seam is a private regional-guide v11 representation
derived separately for each of the four validated variants. It carries stable
source AddressKey ownership and provenance, the fixed prototype axes and
parent topology, ordered pelvic-girdle/waist/chest-girdle stations with short
station transitions, compact shoulder and hip root controls at limb roots,
craniofacial and neck transitions, exact projected bilateral five-station
authored arm and leg profiles with anisotropic elbow/knee/hock compatibility
masses, piecewise tapered limb sections with endpoint-owned elbow/knee/hock
stations, private source-derived digitigrade
foot-chain controls, and tail
centerline/taper controls. These guides are internal derivation data: they
are neither semantic nodes nor a serialized contract, and they contain no
marching-cubes grid, mesh topology, SDF encoding, or renderer operation.
Their controls are backend-neutral only at this prototype level; path
primitive intent is retained so this disposable analytic-field adapter can
preserve capsule versus tapered-segment meaning. The adapter emits each named
piecewise section and joint station as source-owned fields while preserving
source identity, bundle layout, and recipe accounting.

The renderer expands each source descriptor into a bounded, deterministic
role recipe where useful. The current fixture convention supplies ordered
pelvic/chest girdle and narrow-waist masses joined by two short tapered station
bridges, cranium and muzzle, a parent-surface neck/collar, source-owned
compact shoulder and hip root controls plus embedded limb root connectors, tapered hip-to-thigh
transitions, piecewise limb profiles, endpoint joint stations, simple
two-stage hand paws, source-derived digitigrade foot chains from the existing
hock through a tapered metatarsal, planted paw pad, and forward toe box, and
a smoothly rooted straight tail with a full midsection and short blunt distal
taper. Recipe components are fields,
not semantic nodes: every generated component keeps its source descriptor as
owner and the semantic sidecar emits only source AddressKeys. Limb and root
connectors are anchored on the torso cage boundary for torso-owned roots, or the
parent analytic-field boundary for other attachments, in the existing
axis-aligned fixture convention; arbitrary orientation is not claimed. Recipe
expansion therefore fails closed unless the envelope contains the exact 18-Part
stylized-biped role/parent layout with a mirrored left/right body, +Y as up,
+Z as foot/muzzle forward, and -Z as the straight-tail direction. The expected
ellipsoid centres, capsule endpoints, and tapered-tail endpoints must also
remain bound to their source reference points. This is a deliberate preview
restriction, not a local-frame or general morphology contract.

The skin adapter embeds torso-owned root and hip connectors toward the child by
their support radius. Their guide-side boundary anchors remain visible in the
regional sidecar, while the compiled field uses the embedded centreline. The
successor arm consumer separately uses the authored arm profile and shared
upper-arm-owned elbow seam described below. No successor arm root bridge or old
underarm support is emitted.

For the fixed axis-aligned prototype, a connector endpoint on a principal axis
of its selected torso ellipse receives a deterministic analytic disk-containment
certificate. The certificate evaluates the ellipse quadratic at both disk
endpoints and at any in-range interior vertex. A general-point endpoint retains
the conservative homothetic certificate as fallback; failure to certify remains
fail-closed. A nonzero-lateral endpoint must also have
`support < lateral_forward_length`, even when its one-support-radius disk is analytically
contained, so embedding cannot reverse the ordered boundary-to-child path.
The zero-lateral pure-axial path remains available. On the corrected HEAD,
generated `standard_neutral_reference`, `compact_broad_short_limb_large_head`,
and `stocky_broad_chested` profiles compile, while the deliberately tall and
slender lean-thigh profiles are rejected at their thigh root connector when
that bounded ordering/containment proof cannot pass. This is candidate-local
correctness evidence, not a new morphology support promise.

The immutable historical sessions and captures documented below remain
historical evidence. Their reproduction commands are qualified by their
recorded source/configuration/implementation hashes; they do not claim exact
reproduction from this corrected, currently uncommitted HEAD, and generated
outputs remain disposable under `/tmp`.

The manifest metrics report both source descriptor count and actual generated
field count, including the field-memory bound used for allocation. This is
resource accounting for the disposable preview only, not a runtime budget or
future compiler contract.

The disposable v3 generator writes one private `regional-guide.json` and one
`guide-skin-composite.png` for each variant, alongside the retained
`surface.ply`, `semantic.json`, and `metrics.json` artifacts. The regional
guide v11 sidecar is a sanitized, source-owned debug projection of `_HybridGuide`:
it carries only source AddressKeys, compiled recipe counts, projection
names/bases, one shared world-space render bound, fixed canvas/layout metadata,
and finite regional controls. Its v4 `torso_cage` controls compile into the
successor's private frame-aware ordered profile sweep: they retain
pelvis/torso owner AddressKeys, fixed guide axes/orientation, seven ordered
elliptical cross-sections from
pelvis through the shoulder ribcage, and six connections between adjacent
sections. The guide renderer draws these sections as rings/contours in the
front, side, and three-quarter x-ray panels. The older ordered axial
`stations` (`pelvic-girdle`, `waist`, `chest-girdle`) and `transitions`
(`pelvis-waist`, `waist-chest`) remain only as a clearly marked
`compatibility-diagnostic-not-rendered` sidecar view; they are not rendered and
are not the skin-driving controls. Limb controls expose
named tapered sections, consumed profile radii, source-owned root/hip connectors,
named endpoint joint stations, and exact parent anchors for hand/foot
attachments. The authored arm profile is projected into exactly five ordered
stations per side: `upper-arm-start`, `upper-arm-midpoint`, `elbow`,
`forearm-midpoint`, and `forearm-distal`. The elbow is one shared
upper-arm-owned seam; the guide also carries its authored anisotropic
compatibility mass, while the forearm owns the distal station. No per-variant
station tuning is introduced. Foot controls expose the exact five-station route
`hock -> metatarsal midpoint -> pad -> pad-toe midpoint -> toe`: the hock is
inherited from the shin-owned authored leg profile, while the remaining four
stations are foot-owned. The route carries full lateral/up/forward radii, outer
caps, four spans, and exact producer/guide/successor lineage and cross-binding.
The guide also retains a contact datum. Shoulder controls retain authored peak/axilla anchors, vertical
and depth radii, and frame axes. The successor consumes them as exactly two
ordered, deterministic, frame-aware five-section lateral profile sweeps, one
per side: `torso-interior`, `torso-boundary`, `authored-shoulder`,
`upper-arm-socket`, and `upper-arm-midpoint`. The first two sections are
torso-owned; the remaining sections are matching `upper_arm`-owned controls.
A shoulder-specific finite-span evaluator rejects malformed frames and axes
and keeps representative remote points away from accidental zero crossings.
The current producer also carries bilateral `authored_leg_profile` v1:
five ordered stations per side (`thigh-start`, `thigh-midpoint`, `knee`,
`shin-midpoint`, `hock-endpoint`), owned `thigh/thigh/thigh/shin/shin`, and
30 source-authored lateral/up/forward radii with shared variant factors. The
guide projects those exact stations and exposes anisotropic
`leg-profile-segment` fields with lateral/up/forward radii at each endpoint.
The successor separately consumes the authored arm profile as four routes
(left/right upper arm and left/right forearm) and the authored leg profile as
two bilateral five-station routes. Each route consumes all three authored
lateral/up/forward radii; the shared elbow seam is exact and upper-arm-owned.
Arm, leg, and foot span profiles sample their transverse radii with the same
bounded shape-preserving interpolation used by the torso, retaining every
authored station exactly without inventing intermediate extrema.
The bilateral support curves remain
`guide-only`; no successor arm root bridge or distal deltoid field is emitted,
and no per-variant station tuning is used. The sidecar and manifest report the
exact compiled recipe inventory separately from the richer private guide
controls. The hands retain a simple paw mass and attachment. It is not a
semantic or runtime contract and contains no descriptor input records or
synthetic semantic IDs.

The three-layer diagnostic keeps the compatibility filename
`guide-skin-composite.png`, but each image is now `1800 × 1500` RGB with columns
`front`, `side`, and `three-quarter`, and rows `CONTROL GUIDE` (derived
controls, not evaluated geometry), `CONSUMED FIELDS` (the exact component
level-0 surfaces before smooth union, evaluator-backed, with debug colours),
and `FINAL SKIN` (the neutral smooth-union result). Guide-only controls may
appear in row 1, `CONTROL GUIDE`, without affecting rows 2 or 3. The consumed
row is made from the actual `Field`/`_Component` operands; recipe names and
colours are diagnostic implementation identities only, not semantic nodes,
materials, or hard seams, and not accepted DR-0010 evidence. All rows use the
same projection framing and shared render bound for direct comparison across
the four variants. Mesh extraction retains each variant's own field bounds
and grid spacing; the shared render bound does not define sampling.

The successor keeps these concerns independent: the manifest generator's
`padding` is the successor mesh sampling padding (default `0.50`), while its
`capture_padding` is sourced from the baseline generator default and frames
the shared three-layer captures (currently `0.75`). This preserves the
successor's known-good mesh grid while keeping default baseline and successor
capture frames exactly comparable.

## Candidate disposition and history

This section preserves the path from the earlier exact-five smooth-union
candidate through the completed bounded regional hypothesis. It records
candidate-scoped evidence and disposition; it does not replace the project
status, roadmap, or any proposed surface contract.

### Observation

The earlier exact-five smooth-union path proved useful technical plumbing: the
source-authored controls could be compiled into deterministic analytic fields,
composed into a connected whole-body surface, and carried through source
ownership, provenance, semantic sidecars, metrics, reproducible publication,
and visual review without a handcrafted base mesh. That is evidence about this
disposable route and its infrastructure, not a form-quality pass.

The exact displayed baseline for this history is the immutable local session
`successor-stylized-anatomy-five-profile-checkpoint-v1`, published on
2026-08-31 NZST. Its review descriptor SHA-256 is
`a17055186b832c0a1b5e306699572ea9ebddbb3d8678f9b8938392d04e6d65d4`, its
source-manifest SHA-256 is
`77c2763c771d18f67ee179a915044bd7b435425c0a4bd8d390ffbbc441a416c6`, and its
implementation SHA-256 is
`3181ab86c50f2df24dcca0a6e3f7fbe5e3502a7a0a4afaa1d5ecaa3bdffec45d`. The
associated branch head is
`68eadfb6a801e052ddc1102e82d976eac78ba1ce`. Captures remain local and
uncommitted under the artifact policy. This is a candidate-evidence
disposition, not a code revert.

Ben's scoped 2026-09-01 appraisal of that immutable displayed checkpoint
observed a lost or occluded neck, rounded rectangular/blocky torso and pelvis,
and an overall surface that was not convincing anatomy. The same candidate's
lower body read as external thigh bulbs rather than hip/leg roots seated inside
the pelvis, with an upside-down-bell lower torso. These observations are scoped
to that displayed candidate and revision.

### Disposition

The exact-five smooth-union candidate is rejected as visual evidence, frozen,
and retained as the failed baseline. It is not deleted, and its result is not
generalized into proof that implicit methods cannot work. Further local tuning
stopped because the observed torso/pelvis massing and hip-root relationship
were representation-level shortcomings for this candidate; additional
artifact-specific polishing would not provide a useful bounded answer and
would risk an open-ended tuning loop. This disposition makes no production
backend or architecture decision and does not activate the formal comparison.

### Retained evidence

The reusable remainder is the source inspection and authored-profile lineage,
regional-guide and semantic ownership/provenance plumbing, deterministic field
generation and extraction, metrics and hash-bound artifacts, and the disposable
publisher/visual-review workflow. The failed candidate's connected-surface and
cross-variant generation evidence remains available as context and regression
evidence. Its displayed anatomy judgments remain evidence about that exact
candidate, not durable geometry prescriptions.

### Executed initial alternative attempt

The `artifact-cache/...` prefix below is a logical local-cache identifier, not
a repository path or a literal universal filesystem path.

The initial `standard_neutral_reference` alternative attempt is now retained in
the durable local cache
`artifact-cache/creature-kernel/neutral-alternative-attempts/2026-09-01-a/`.
Its actual capture is
`artifact-cache/creature-kernel/neutral-alternative-attempts/2026-09-01-a/standard_neutral_reference.png`,
its identity record is
`artifact-cache/creature-kernel/neutral-alternative-attempts/2026-09-01-a/identity.json`,
and its retained mesh is
`artifact-cache/creature-kernel/neutral-alternative-attempts/2026-09-01-a/surface.ply`.
The identity record captures source/configuration/output hashes, including
PNG SHA-256
`86c2888d7415c0a9be69f359244c0e968a90cf19c10e216392bdd0e4270380e4`. This
exploratory one-off was generated from an uncommitted implementation state
that was not itself hash-bound or preserved. It is therefore retained
observational evidence, not exactly reproducible implementation evidence. It
is an `1800 × 1500` RGB fixed front/side/three-quarter 3×3 sheet using 56
samples, padding `0.5`, and default `smooth_k`. The mesh reported watertight,
one component, 3,850 vertices, and 7,696 faces; final review found unresolved
bounds, provenance, identity, and test defects, so technical triage is not
passed.

The main thread inspected this actual image and the retained rejected-v9 image.
Two fresh independent model-vision critiques inspected the actual image:
`gpt-5.6-luna` `xhigh` anatomy/silhouette and `gpt-5.6-luna` `high`
surface/mesh. They shared observations of a bulbous nearly spherical pelvis,
weak or pinched/jagged hip-to-thigh continuity, a short barrel-like torso,
hard regional seams, and faceting. The anatomy lens also noted abrupt narrow
neck/shoulder integration. The surface lens noted a possible pointed
side/tail termination, uncertain at 56 samples. The critiques are advisory
only and cannot establish topology, semantics, or deformation; faceting may be
capture sampling or shading. No visual acceptance or implementation
completion is claimed.

A `gpt-5.6-sol` medium read-only synthesis identified likely
support-as-geometry inflation and recommended support as a locality mask, a C1
gate, and source-derived axial caps/neck root. This is advisory implementation
input, not a new architecture or product decision. The initial attempt was
retained, followed by the single shared correction/republication sequence below.
No profile-specific corrections were applied.

### Completed corrected neutral and failed exact-five expansion

Attempt B remains retained at
`artifact-cache/creature-kernel/neutral-alternative-attempts/2026-09-01-b/`
as the hash-bound intermediate generated before final correctness fixes. The
authoritative final corrected neutral is C at
`artifact-cache/creature-kernel/neutral-alternative-attempts/2026-09-01-c/`.
This is the same shared correction after final correctness fixes, not a second
aesthetic correction. C's `standard_neutral_reference.png` has
SHA-256
`8ed4ccb8e4928e1de228b6e49c2c2c00f4afd59b793b923bf7906aaf71b2d5e0`, its
`surface.ply` has SHA-256
`d6b509b8452d8bd4aa41cb89d59815a3a0cc726383fa6c011d776c9b4e52632c`, and its
`identity.json` file has SHA-256
`3472d7cb48d9bd2a06dbd71e951d5a37fd18eac260bb88d39f5dbec4993c95ea`.
The identity record's `identity_sha256` is
`b99b180fffc153d5c24bdc175673cc1c307f6d16bc3d74cca19e3361c05055ec`, and its
`implementation_sha256` is
`1cbfa10a5e6019103b419c69d13b800b1247202e7389e094a91fea9725ea3e2d`.
C used 80 samples per axis, padding `0.5`, and `smooth_k` `0.1`; it has one
connected component, is watertight, and contains 7,770 vertices and 15,536
faces.

The main thread inspected C at original resolution. It materially removed the
giant spherical pelvis and reduced faceting/blobiness versus A, but still read
as a barrel or rounded-rectangle torso over a skirt or bell pelvis, with weak
hip seating, a collar or peg neck, and rod-like limbs. At checkpoint scale it
looked essentially the same as B; no second aesthetic correction was made.
Two independent model-vision passes split:
surface/integration judged the neutral sufficient to generate the five
profiles, while anatomy/silhouette judged it still a failed simplified
anatomy representation. Human authority was preserved by attempting the
exact-five expansion with the unchanged candidate and applying no further
tuning.

The exact-five publication ID
`successor-regional-anatomy-five-profile-checkpoint-v1` was attempted once
after B and again after final correctness fixes and C. Both attempts failed
before rendering/publication because `slender_long_limb` had six connected
components. No target directory was installed, and no exact-five human
checkpoint exists. The candidate is closed as failed under the
one-shared-correction stop rule. Stage 2 and Stage 3 remain inactive. No
autonomous next candidate or tuning is authorized; Ben must authorize a new
Stage 1 direction.

### Final regional-candidate disposition (PR #123)

[PR #123](https://github.com/benhook1013/creature-kernel/pull/123) is
**CLOSED, not merged**. Its pushed head was
`36ab72610d99a56a962cffbf8eda6b63d3a4034f`; latest pushed CI was green, but
the latest substantive hosted review had eight actionable findings. The
overlay archival commit is
`17ba5eaf39157f875931c287b3712367349e9299`, with tree
`4f1d5c81b8d77b28944676acc7679cabb0cdc06e` and parent exactly the pushed
head. It is unreviewed and unaccepted. The annotated remote tag is
`archive/regional-surface-candidate-2026-09-03` (tag object
`abc6b39eba32d73859b9396debc8858d7140db94`, peeled commit
`17ba5ea`).

The latest reviewed local gallery
`regional-surface-wip-wrist-36ab72610d99` remains in the artifact cache.
Its `review.json` SHA-256 is
`902ec0b0a5323094a3857cfec515a99aac60107c9182b60deeeaf2d12081e2d0`.
The five PNG hashes, in profile order, are: standard
`845017852e5b5299773b1b140eaf2a2b37edc5fc75fb8f0302af1655693a7e6c`, compact
`8c44e61cb8f675147cd8ea23c5fe5eb174332e4c7192bd2e415738156b6e96dd`, tall
`39570b2ee24af8df03a3585b8cfdb5aeca5c6d9fe37789538d968a0378e1f060`, slender
`bf222b0528786871a1cb66efd09aa2fbd23d3ade1b997a97a5c83b38b2ed3533`, and
stocky `8c98c1314c7b8220826fef7d02f96ee7ff89ad24f7794a4795a6b4dd37f98797`.

The scoped visual failure was blocky or bell-shaped torso/pelvis massing,
external/diagonal thigh bulbs rather than thighs seated as roots inside the
pelvis, and unconvincing neck/shoulder and other transitions. This is scoped
to this candidate and does not generalize to all implicit methods. The visual
service has been returned to main; the old worktree and local/remote branch
were removed only after tag verification. This closes the regional candidate;
the new programmatic investigation is separately bounded research, not a
reopening of PR #123.

Reproduction requires checking out the archive tag and using the archived
experiment launcher; the active branch does not retain the regional publisher:

```bash
surface_preview_launcher=experiments/current-form-surface-preview/surface_preview_launcher.sh
source_parent="$(mktemp -d /tmp/ck-regional-archive-source-XXXXXX)"
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py \
  --output-dir "$source_parent/sources"
"$surface_preview_launcher" dev-tools/visual-review/publish_regional_surface_gallery.py \
  --root "${XDG_CACHE_HOME:-$HOME/.cache}/creature-kernel/visual-reviews" \
  --source-manifest "$source_parent/sources/manifest.json" \
  --creature-kernel target/debug/creature-kernel \
  --id replace-with-a-fresh-regional-archive-id \
  --mesh-samples 56 --mesh-padding 0.2
```

The archived checkout, pinned experiment environment, and built
`target/debug/creature-kernel` are prerequisites. Use a fresh publication ID;
the immutable publisher will not replace the retained reviewed session.

### Next hypothesis (superseded)

The approved regional pivot recorded in the 2026-09-01 active runway was a
neutral-first, landmark-driven regional candidate: explicit ribcage,
abdominal-bridge, and pelvis regions; swept anisotropic limbs; specialized
shoulder and hip roots; controlled local blending; and, where needed, regional
lofted or patched surfaces. It was triaged through the neutral reference,
followed by one shared correction/republication and the exact-five publication
attempts recorded above with the unchanged candidate. No per-profile or
per-fixture fixes were part of this hypothesis. The hypothesis is closed by the
failed exact-five expansion above; there is no autonomous continuation until a
new human-authorized Stage 1 direction is recorded.

The visual pass was reserved for the exact-five human anatomy checkpoint, with
`standard_neutral_reference` first. That checkpoint was never created because
both exact-five attempts failed before rendering or publication. The formal
five-branch comparison remains parked.

Before Stage 2 begins, the separate representation gate requires human visual
acceptance, coherent watertight output, preserved semantic regions and
ownership, and repeatability across all five profiles. If those prerequisites
pass and a new runway activates Stage 2, an early continuation check follows a
provisional rig and weights exercise and tests topology/correspondence through
one representative bend/binding scenario. Neither gate activates the formal
comparison.

## Run

Use the repository-owned launcher for every experiment Python command. It
selects the already-created interpreter from
`CK_CURRENT_FORM_SURFACE_PYTHON`, or by default from the native-Linux XDG
cache (`$XDG_CACHE_HOME/creature-kernel/current-form-surface-venv/bin/python`
or `$HOME/.cache/creature-kernel/current-form-surface-venv/bin/python`). It
checks the pinned dependencies and imports before each command, and replaces
inherited Windows `TMPDIR`/`TEMP`/`TMP` values with a verified native-Linux
temporary root. `CK_CURRENT_FORM_SURFACE_TMPDIR` may select an existing,
writable native-Linux directory explicitly. The launcher does not create an
environment or install packages.

The one-purpose hash-bound neutral rerender helper is
`dev-tools/visual-review/rerender_neutral_alternative.py`. Run it through the
managed pinned environment to inspect only the first profile of an exact-five
source manifest and atomically install the three-file neutral output:

```bash
surface_preview_launcher=experiments/current-form-surface-preview/surface_preview_launcher.sh
source_parent="$(mktemp -d /tmp/ck-neutral-source-XXXXXX)"
source_dir="$source_parent/generated"
fresh_id=replace-with-a-fresh-neutral-attempt-id
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py \
  --output-dir "$source_dir"
"$surface_preview_launcher" dev-tools/visual-review/rerender_neutral_alternative.py \
  --output-parent "${XDG_CACHE_HOME:-$HOME/.cache}/creature-kernel/neutral-alternative-attempts" \
  --id "$fresh_id" \
  --source-manifest "$source_dir/manifest.json" \
  --creature-kernel target/debug/creature-kernel \
  --samples-per-axis 80 --padding 0.5 --smooth-k 0.1
```

The helper is one-purpose: it inspects only the first profile and atomically
installs exactly `surface.ply`, `standard_neutral_reference.png`, and
`identity.json`; it does not publish the exact-five group. Its `identity.json`
binds implementation, configuration, lineage, and output hashes. The bounded
fingerprint/identity route limits pinned runtime
requirements to 64 KiB, imported module files to 32 MiB each and 128 files,
repository implementation inputs to 4,000,000 bytes each, and the pinned
executable to 256,000,000 bytes and output artifacts to 256 MiB each. The
runtime fingerprint covers the pinned requirements, interpreter, and imported
package-module files only; it does not capture all ambient process, OS, loader,
native-library, filesystem, or machine state.

Create the isolated environment once, outside the repository, and install the
small experiment-local dependency set explicitly:

```bash
surface_preview_launcher=experiments/current-form-surface-preview/surface_preview_launcher.sh
surface_preview_venv_root="${XDG_CACHE_HOME:-$HOME/.cache}/creature-kernel/current-form-surface-venv"
mkdir -p "$(dirname "$surface_preview_venv_root")"
python3 -m venv "$surface_preview_venv_root"
surface_preview_python="$surface_preview_venv_root/bin/python"
"$surface_preview_python" -m pip install -r experiments/current-form-surface-preview/requirements.txt
```

For a disposable `/tmp` environment, set
`CK_CURRENT_FORM_SURFACE_PYTHON=/tmp/ck-current-form-surface-venv/bin/python`
when invoking the launcher.

The input must be a successful v11 inspection envelope. The output directory
must not already exist, and its parent must already exist:

```bash
mkdir -p /tmp/ck-current-form-surface
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_surface_preview.py \
  --input /tmp/form-v11.json \
  --output /tmp/ck-current-form-surface/run-a \
  --samples-per-axis 72
```

One generator invocation emits all four fixed variant subdirectories; do not
run it separately per variant.

The direct successor applies the same baseline raw-input bound,
`surface_preview.MAX_INPUT_BYTES` (currently 4 MiB). Inputs at or below the
inclusive bound continue to normal UTF-8/JSON validation; an oversized input
fails with `input exceeds bounded size` before output staging or mesh work.

The successful bundle contains exactly the manifest and four sets of PLY,
semantic-winner sidecar, metrics JSON, regional-guide JSON, and guide/skin
composite PNG. Repeating the same input and configuration on the same host
produces byte-identical outputs; no timestamps or temporary paths are
embedded. The output contains no committed artifact policy exception: keep it
ephemeral under `/tmp`.

## Disposable successor consumer

The separate successor consumer is a disposable exploratory proof. Its current
bounded slice replaces the torso, shoulders, head, neck, four bilateral
limb-chain consumers, bilateral hand/foot consumers, and tail. The head/neck
consumer uses source-authored head/neck profile controls projected through the
regional guide. It retains exact source AddressKey ownership and provenance
for all eight ordered profile sections and seven connections across all four
variants. The projection preserves branched route lineage: a vertical
neck/cranium route from `neck-collar` through `cranium-crown`, and a forward
muzzle route from `cranium-mid` through `muzzle-tip`; centres, radii, endpoints,
thicknesses, and fixed axes come from each private guide. The successor
hand/foot boundary consumes ordered hand attachment/paw sweeps and shin-to-foot
digitigrade chains. Each hand-paw station retains the shared outward route plus
its source-derived outward/up/forward volume, while the foot chain retains the
shin-owned hock seam and foot-owned metatarsal, pad, and toe controls. The
successor
tail boundary consumes six source-owned tail elements (root source,
attachment, collar mass, tip source, extension, and cap). The successor v9
region
`successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-hip-root-sweeps-v16`
uses four authored arm-profile routes plus two authored leg-profile routes.
The authored leg routes retain the thigh-owned knee and shin-owned hock, and
each foot route is exactly `hock -> metatarsal midpoint -> pad -> pad-toe midpoint
-> toe`, with the hock shin-owned and all other stations foot-owned. The
successor consumes every baseline field through its successor or derived
hip-root components; `temporary_bridge` is disabled with no consumer, regions,
retained recipes, or fields. The two arm root bridges and old underarm
supports are absent; the shared upper-arm-owned elbow seam consumes all three
authored radii. No duplicate legacy leg mass is retained, and there is no
per-side or per-variant station tuning. No baseline tail, paw, or foot
component remains. The shared tail source/extension endpoint retains its
independently authored profiles;
this experiment does not claim that the resulting tail silhouette or visual
quality has been observed or accepted.
It is neither a permanent backend selection nor an acceptance decision. The
published form gallery is historical PR #113 evidence. Ben's 2026-08-24
appraisal of immutable checkpoint
`authored-form-expressivity-exact-field-components-checkpoint-v2` successor v9
accepts only that source-authored controls and procedural field routes cover
the required regions and produce a connected whole-body surface. Its neck is
visibly occluded or lost, its torso and pelvis read as rounded rectangular/
blocky, and the overall body is not convincing realistic or anatomical skin;
visual region readability remains failed or inconclusive. These are
limitations of this disposable candidate, not canonical geometry
prescriptions. Publication machinery is not acceptance.

The shared-pose structural embodiment gallery below has completed its named
human checkpoint: it was appraised "looks good" and merged through PR #114.
No further cosmetic repair is planned. It remains a disposable companion
consumer of this preview's generated surfaces, not a production architecture
claim. Its four-profile candidate set and semantic pose payload are frozen
before evidence; the current display variants are not automatic substitutes.
It uses generated, not illustrative, neutral/posed surface, skeleton/bone,
weight/influence, and collision-proxy artifacts with source/build/scenario
lineage. See `docs/project/status.md` for the current stop state and continuation
authority.

The experiment-local `structural_profile_candidates.json` retains five ordered
source candidate IDs for the closed regional candidate reproduction, with the
standard neutral reference first:
`standard_neutral_reference`, `compact_broad_short_limb_large_head`,
`tall_narrow_long_legged`, `slender_long_limb`, and `stocky_broad_chested`.
Its active repaired-source binding is SHA-256
`82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14`, and the
candidate-table bytes are bound by SHA-256
`a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640`.
Generate their compact canonical
BodyDocuments through one shared data-driven transform:

```bash
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py --check
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py \
  --output-dir /tmp/ck-structural-profile-sources
```

The transform changes exact integer Part placements and canonical metre-valued
source dimensions by applying its integer-permille profile factors with exact
decimal arithmetic. Active generated-profile output quantizes each generated
dimension to the nearest millimetre using ties-to-even and emits canonical
metres; it does not reinterpret authored dimensions as permille. It retains the
stable unit neck-to-head reference edge, preserves normalized route controls and
identity rotations, and keeps one tail module present in each of the five
generated profiles while varying tail length and taper. It fails closed on
incomplete targets, overlapping or uncovered dimension groups, broken
bilateral/alignment/Attachment invariants, unsafe values, or non-atomic output.
These are candidate source fixtures and lineage evidence, not public morphology
limits or a production parameter system. This repair rebaselines active metadata
hashes only; standard-neutral geometry is expected unchanged, and the historical
source/evidence and its recorded outcome remain untouched.

The five-profile source-generation command above is a historical
closed-candidate reproduction command, not active runway work. The completed
shared-pose structural gallery is historical v1 and must retain its independent
origin/main lineage.
Reproduce its source inputs only with the explicit archived mode, which verifies
the immutable fixture bytes under
`historical/structural-embodiment-v1/`:

```bash
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_profile_sources.py \
  --generation-mode historical-structural-embodiment-v1 \
  --output-dir /tmp/ck-structural-profile-sources-historical
```

The historical mode is not selected from a profile count or ID list; it rejects
the closed regional five-profile table and any other candidate/source bytes.

The authored arm slice is a disposable consumer intended to test frame-aware
profile continuity and bounded field behavior around the torso, upper-arm, and
elbow join. It does not establish anatomical realism, production topology,
general morphology support, or the quality of the final visual result. It is
historical surface evidence and is not the structural embodiment checkpoint.

After creating and activating the experiment virtual environment described
above, the historical four-variant v9 reproduction workflow has two steps:

```bash
cargo run -p creature-kernel-cli -- inspect-provisional-form \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  > /tmp/form-v11.json

mkdir -p /tmp/ck-successor-surface
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_successor_surface_preview.py \
  --input /tmp/form-v11.json \
  --output /tmp/ck-successor-surface/run-a \
  --samples-per-axis 56
```

Use `--samples-per-axis 56` for this experiment preview. The lean fixture
aliases into disconnected sampled components at 48, so 56 is the documented
preview resolution. This does not solve production topology or minimum-feature
robustness; lower values within the accepted argument range may still validly
fail mesh-connectedness validation, and successful generation is not guaranteed
at every in-range sampling value.

A successful historical v9 reproduction writes
`successor-surface-manifest.json` plus exactly four
variant directories. Each variant directory contains exactly
`surface.ply`, source-owned winner `semantic.json`, `metrics.json`,
`successor.json`, and one
`guide-skin-composite.png`. The PNG is a deterministic RGB capture at the
baseline-compatible `1800 × 1500` canvas. Its three columns are `front`,
`side`, and `three-quarter`; its rows are `CONTROL GUIDE`, `CONSUMED FIELDS`,
and `FINAL SKIN` as described above. Publication metadata records
`panels_per_view: 3`. The manifest and successor sidecars expose the profile
identity, canvas, layout, projections, and shared bounds alongside the
five-artifact inventory. The semantic sidecar uses the same source-only
AddressKey winner boundary as the baseline and carries no synthetic rig or
bone semantics. It binds the exact ordered `surface.ply` bytes and exact raw
producer variant by SHA-256; its label count is bounded by and must equal the
validated PLY vertex count.
The manifest generator configuration reports both independent padding values:
`padding` controls successor mesh sampling and `capture_padding` controls the
baseline-compatible shared capture frame.

This four-variant v9 behavior is separate from the later regional five-profile
candidate; that candidate's exact-five publication attempts failed before
rendering or publication. Fresh candidate generation or publication requires a
new Ben-authorized runway, while historical reproduction remains permitted.

The first structural-embodiment bridge slice consumes one successful
`inspect-structure` result, its matching provisional-form result, the complete
successor bundle, a separately named candidate source profile, and one neutral
surface variant:

```bash
cargo run -p creature-kernel-cli -- inspect-structure \
  --input examples/body-documents/stylized-digitigrade-biped-authored-form.json \
  > /tmp/structure.json

"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_embodiment_bridge.py \
  --inspect-structure /tmp/structure.json \
  --inspect-provisional-form /tmp/form-v11.json \
  --surface-bundle /tmp/ck-successor-surface/run-a \
  --candidate-profile-id authored_baseline_v0 \
  --surface-variant-id neutral-v0 \
  --output /tmp/ck-structural-bridge/run-a
```

Use a native Linux output parent because the bridge publishes with Linux
atomic no-replace directory semantics. The candidate artifact derives a rooted
bone hierarchy, complete semantic-Joint mapping, bounded normalized weights,
and collision capsules from a deterministic nearest-eligible-bone surface
partition. It also records any source Part that won no final-surface vertices;
that absence remains evidence rather than being filled with invented semantic
ownership. Its synthetic root starts at the exactly reproducible complete
neutral-surface centroid and ends at the source root Part reference, with a
deterministic farthest-vertex fallback for a coincident centroid. This first
slice emits no pose or posed surface. It is a direct
prerequisite to, not a substitute for, the shared-pose structural embodiment
gallery.

The completed gallery was built only after all four frozen profiles had
successful neutral bridge bundles and matching hash-bound structure and
neutral-surface inputs:

```bash
"$surface_preview_launcher" experiments/current-form-surface-preview/generate_structural_embodiment_gallery.py \
  --bridge-root /tmp/ck-structural-gallery-inputs/bridges \
  --neutral-ply-root /tmp/ck-structural-gallery-inputs/neutral-surfaces \
  --structure-root /tmp/ck-structural-gallery-inputs/structures \
  --source-manifest /tmp/ck-structural-profile-sources-historical/manifest.json \
  --output /tmp/ck-structural-embodiment-gallery
```

Each input root must contain exactly the four frozen candidate IDs; structure
files use `<profile-id>.json`. The required generated source manifest binds
each profile to its generated source document and is copied into the gallery
inventory. The consumer rejects non-identity source Joint frames instead of
inventing unrecorded frame semantics. It applies the one
checked-in deterministic pose without IK or contact, performs classic linear
blend skinning, transforms the generated collision capsules, and publishes one
scale-consistent `1800 x 2500` PNG per profile. Every PNG uses the same global
world bound and has front, side, and three-quarter columns over five rows. The
side column is an exact orthographic projection. Skeleton rows are explicit
x-ray overlays drawn without skin depth occlusion, so internal and far-side
bones remain visible for inhabitation review; their visibility does not imply
an oblique camera. The five rows are neutral skin plus skeleton, posed skin plus
skeleton, dominant-bone/max-weight evidence, neutral skin plus proxies, and
posed skin plus proxies. The root
manifest inventories the pose and every per-profile neutral/posed surface,
skeleton, weight, proxy, metric, and gallery artifact. These remain disposable
candidate-scoped evidence, not runtime rig, solver, anatomy, or topology
contracts.

After generation, validate and publish only the four profile PNGs into one
immutable visual-review group:

```bash
"$surface_preview_launcher" dev-tools/visual-review/publish_structural_embodiment.py \
  --root "${XDG_CACHE_HOME:-$HOME/.cache}/creature-kernel/visual-reviews" \
  --gallery /tmp/ck-structural-embodiment-gallery
```

The default session is available at
`http://localhost:8765/review/shared-pose-structural-embodiment-gallery` when
the existing visual-review service is running. The publisher revalidates the
complete 39-artifact/40-file candidate gallery, reproduces the frozen generated
sources, parses and checks the structural and posed evidence, and
deterministically re-renders each PNG from that evidence and the shared world
bound before copying only the four ordered PNGs required for appraisal. It
never replaces an existing session.

## Structural gallery evidence probe

`structural_gallery_evidence_probe.py` is disposable pre-proposal evidence. It
projects non-rendered structural evidence from an already-validated completed
gallery into immutable, hashable experiment records. It consumes a completed
gallery directory, not a review session, and delegates exact validation of the
complete source gallery to
`dev-tools/visual-review/publish_structural_embodiment.py`. Rendered gallery
PNGs, canvas data, and display metadata are deliberately outside the projection;
original `inspect-structure` bytes and per-vertex semantic labels are
unavailable. An expected invalid-gallery rejection returns no view, while
validator-load and unexpected runtime failures surface.

The probe is not a runtime package, bundle, durable schema, or adapter input
and makes no contact, deformation, physical-response, engine, or R3 claim. It
has no CLI; its import entrypoint is
`project_structural_gallery_evidence(gallery: Path)` (also exported as
`load_structural_gallery_evidence`). For a developer import/smoke check, run
the canonical experiment test command with the focused test filename:

```bash
experiments/current-form-surface-preview/test.sh \
  test_structural_gallery_evidence_probe.py
```

Each manifest variant record and its `successor.json` sidecar also carries
`source_variant_sha256`, the 64-character lowercase SHA-256 digest of the
exact canonical raw producer variant object (`_canonical(raw_variant)`). This
is a deterministic source-record binding, not an artifact hash; the two
locations must agree for each variant, and distinct producer variants have
distinct digests.

The generator alone writes this disposable bundle; it does not publish a
visual-gallery session. The active
[`publish_surface_preview.py`](../../dev-tools/visual-review/README.md#disposable-baseline-versus-successor-surface-checkpoint)
workflow runs the current producer and both generators, validates the bundles,
and publishes the baseline-versus-successor captures through the visual-review
gallery.

Tests:

```bash
experiments/current-form-surface-preview/test.sh
```

Pass one `test*` filename or `test*` discovery pattern to run a focused file
subset. During active implementation, pass a second `test*` method pattern to
filter that file further without triggering its mesh-heavy tests. Selectors
must begin with `test`; filename selectors must not contain `/`. The wrapper
resolves its own repository paths and always delegates
interpreter selection, pinned dependency validation, and native temporary-root
setup to `surface_preview_launcher.sh`; it never falls back to bare
`python3`. The launcher remains the entrypoint for publishers and other Python
commands, for example:

```bash
"$surface_preview_launcher" dev-tools/visual-review/publish_surface_preview.py --help
```

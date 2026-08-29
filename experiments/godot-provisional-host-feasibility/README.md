# Godot 4.7.2 provisional structural host probes

Status: disposable approved-host evidence only

This directory contains a pinned Godot 4.7.2 launcher and three fail-closed
structural host probes that load two distinct profiles from an already
completed and validated structural-embodiment gallery. The neutral host-load
smoke and posed cross-check are headless structural probes: the neutral one
hash-checks all six projected profile artifacts, parses the neutral mesh,
skeleton, weights, and neutral proxies, then instantiates one neutral
`ArrayMesh` and one `StaticBody3D` with capsule collision shapes per profile;
the posed one also parses the posed mesh and posed proxies, independently
recomputes the published posed vertices and normals and posed proxy endpoints
from the published skin matrices plus weights at a fixed `2e-5` position/proxy
tolerance, and instantiates the corresponding posed mesh and collision shapes.
The skeletal pose smoke is the actual binding probe: it constructs a real
`Skeleton3D` hierarchy and `Skin` with exactly 18 bones and bind poses, attaches
the weighted `ArrayMesh` through `MeshInstance3D`, applies the shared pose
recipe, bakes neutral and posed host mesh evidence, and compares that evidence
plus 18 posed proxy nodes to the published artifacts. Its host normal evidence
uses a documented `3e-4` tolerance for Godot's host mesh normal encoding.
All three probes record deterministic host-local evidence in isolated
temporary Godot projects and remove those projects afterward. The skeletal
probe's semantic-contact mode is a bounded experiment-local contact path: its
fixed canonical command addresses actuator avatar 0's right wrist and response
avatar 1's left wrist, and freshly validates the exact selected posed-capsule
lineage plus CK, carrier, semantic-pose, and CK-projection identities before
launch and report publication. The disposable project explicitly pins Jolt
Physics. It moves an `AnimatableBody3D` actuator through bounded
approach/contact/release/exit phases against a `RigidBody3D` response body and
records runtime-derived contact and solver-response evidence. Its optional
deformation mode adds a smooth open forearm sleeve, drives a fixed localized
falloff from the retained contact sample, validates exact release recovery,
and emits static replay captures of the runtime mesh read-back states.

This is not a package, adapter, Readiness 3 result, realistic tissue result,
benchmark, or checkpoint claim. The contact path proves only bounded
experiment-local semantic contact and physical response: its report validates
the exact logical tick trace, contact samples and attribution, nonzero solver
impulse, snapshot-derived normal velocity/displacement, and clean exit. Its
runtime configuration is `AnimatableBody3D` actuator plus `RigidBody3D`
response initialized once with mass 1, gravity 0, locked rotation, sleep
disabled, and one shape; after setup the probe drives only the actuator. It
makes no claim about visual quality, package/adapter/R3/performance, permanent
Godot/Jolt selection, or the human checkpoint. The skeletal smoke's binding claim is
host-local only; its pose command mode remains disposable semantic-selector
injection and read-back evidence, and its no-contact paths remain unchanged
predecessor paths.
The deformation mode proves only slight open-edge surface deformation and
exact recovery. Its rigid capsule remains undeformed. The completed
experiment-local render/collision read-back coherence slice pairs the runtime
`ArrayMesh` and `CollisionShape3D` read-back in one response-body-local frame,
with the existing static replay linkage. Its schema is
`creature-kernel.disposable-godot-render-collision-coherence.v1` and its frame
is `response_body_local_selected_capsule_side`. It records `neutral`,
`contact_onset`, `peak`, and `recovery` at ticks 0, 26, 26, and 64; onset and
peak are legitimately the same first/strongest sample. The successful run
reported selected rigid-capsule endpoint and radius drift of exactly zero;
validation permits only the declared numeric tolerance, so exact zero is not a
general enforced invariant. The selected-capsule source binding cross-validates
semantic identity, radius, and central-segment length against the posed proxy.
Runtime body-local placement and orientation come from `CollisionShape3D`
read-back; this evidence does not claim that they are independently
common-frame-derived from the source proxy endpoints. Neutral and recovery
maximum absolute side clearance is `5.9605e-08`; peak inward penetration is
`0.00328758359`, peak outward clearance is `5.9605e-08`, and outside-falloff
penetration is `2.9802e-08`. Python independently reconstructs runtime capsule
endpoints from the capsule transform/height/radius and recomputes vertex
clearances and metrics. This remains narrow experiment-local evidence, not live
contact rendering, deformed collision, realistic tissue, production topology,
performance, package/adapter/R3 evidence, or permanent Godot/Jolt selection.
The static captures remain replay linkage rather than live contact rendering.
Normal failures remove newly written captures and the success report is
published last. An abrupt process termination can still leave orphan captures
without a report, so the two-part output assumes a stable, non-adversarial
same-user parent directory; consumers must not treat captures without the
matching success report as evidence.

## Provisioning

Provisioning is explicit and manual. No script in this directory downloads,
extracts, installs, upgrades, or locates Godot through the system. An operator
must obtain this exact official Linux x86_64 asset and place the executable at
the default path, or provide an absolute path to another exact, independently
verified copy with CK_GODOT_4_7_2_BINARY. The default path is:

    ${XDG_CACHE_HOME:-$HOME/.cache}/creature-kernel/godot/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64

When XDG_CACHE_HOME is unset or empty, HOME must be non-empty and absolute;
when XDG_CACHE_HOME is selected, it must be absolute. The wrapper fails closed
if the selected cache/home root is invalid. An explicit binary override still
has to be absolute.

- Official release page: <https://godotengine.org/download/archive/4.7.2-stable/>
- Official Linux x86_64 archive URL:
  <https://github.com/godotengine/godot/releases/download/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64.zip>
- Archive SHA-256:
  cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4
- Expected executable size: 146414384 bytes
- Expected executable SHA-256:
  8d106cbe6144c2dc7e881d61d2429c1a8a76e6b22ef48bd5e48dcf934953f71e
- Expected --version output:
  4.7.2.stable.official.ed1daf0bf

The wrapper rejects relative paths, missing paths, non-regular files,
non-executable files, symlinks and symlink path components, a digest mismatch,
and any other version output. It exits before handing control to Godot when a
preflight check fails. The version preflight itself uses `--headless`, as do
the integration-suite availability probes, so repeated validation does not
create transient WSLg windows.

## Use

The wrapper forwards every argument after preflight and preserves Godot's exit
status:

    experiments/godot-provisional-host-feasibility/launch_godot_4_7_2.sh \
      --headless --path /absolute/path/to/a/future/project

An explicit absolute-path override is available for another exact copy:

    CK_GODOT_4_7_2_BINARY=/absolute/path/to/Godot_v4.7.2-stable_linux.x86_64 \
      experiments/godot-provisional-host-feasibility/launch_godot_4_7_2.sh \
      --headless

TEMP and TMP are deliberately inherited unchanged. The wrapper neither
translates Windows-style values nor invents replacement directories; the
caller chooses the appropriate WSL or native-Linux temporary environment, and
the direct exec preserves it for Godot.

Run the neutral two-profile host-load smoke against an absolute completed
gallery path:

    experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_structural_gallery_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --report /absolute/path/to/neutral-report.json

Run the posed two-profile cross-check against the same kind of completed
gallery:

    experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_posed_structural_crosscheck.py \
      --gallery /absolute/path/to/completed-gallery \
      --report /absolute/path/to/posed-report.json

Run the actual two-profile `Skeleton3D`/`Skin` pose-binding probe against the
same kind of completed gallery. It uses the pinned Godot renderer with the
active X11 display and `gl_compatibility`; Godot's `--headless` dummy renderer
does not provide valid skeleton RIDs for this probe. The probe produces no
intentional visual output and makes no rendering-quality claim, but WSLg may
briefly show a Godot window while the real renderer starts. It therefore fails
closed unless an operator explicitly opts into an attended visible run:

    CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --report /absolute/path/to/skeletal-pose-report.json

To exercise the next engine-neutral-shaped serialized input boundary, first
build a disposable carrier from two freshly validated profiles. The serialized
carrier contains no Godot version, coordinate mapping, host translation, or
adapter field. This experiment-local builder still reuses the existing
structural gallery preflight, so the result does not prove a general package
producer or consumer. Its instance IDs are local to this experiment; its schema
and hashes are evidence bookkeeping, not a runtime package format, committed
artifact identity, adapter contract, or compatibility promise:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
        experiments/godot-provisional-host-feasibility/disposable_avatar_carrier.py \
        --gallery /absolute/path/to/completed-gallery \
        --profile-id compact_broad_short_limb_large_head \
        --profile-id tall_narrow_long_legged \
        --instance-id avatar-left \
        --instance-id avatar-right \
        --output /absolute/path/to/disposable-avatar-carrier.json

Pass that canonical carrier back through the skeletal probe with `--carrier`.
The carrier selects the authoritative ordered profile and experiment-instance
identities. Omit `--profile-id`, or repeat it exactly twice in the same order as
the carrier. The runner revalidates the carrier and gallery before launch,
passes the carrier-derived payload plus one ordered record per avatar to Godot.
Each record contains the carrier-backed `instance_id`, `profile_id`, and
`candidate_profile_sha256`. Godot binds each record to one actual runtime root
using deterministic safe naming and runtime-readable root metadata. The report
retains the aggregate carrier SHA-256, byte count, schema, boundary, and
instance order, and adds `carrier_avatar_bindings` with one root-metadata
read-back record per avatar. Python rejects missing, duplicate, reordered,
swapped, mismatched, or aggregate-only binding evidence before publication.
Carrier and gallery validation then repeat before publishing success. The earlier
no-carrier route remains available as predecessor evidence and does not emit
carrier avatar bindings.

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      xvfb-run -a env CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --report /absolute/path/to/skeletal-pose-report.json

Build the separate canonical semantic-pose command from that carrier and the
exact gallery shared-pose source:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
        experiments/godot-provisional-host-feasibility/disposable_semantic_pose_command.py \
        build \
        --gallery /absolute/path/to/completed-gallery \
        --carrier /absolute/path/to/disposable-avatar-carrier.json \
        --output /absolute/path/to/disposable-semantic-pose-command.json

Validate the command independently before consumption:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
        experiments/godot-provisional-host-feasibility/disposable_semantic_pose_command.py \
        validate \
        --gallery /absolute/path/to/completed-gallery \
        --carrier /absolute/path/to/disposable-avatar-carrier.json \
        --command /absolute/path/to/disposable-semantic-pose-command.json

Consume it by adding `--command` to the carrier-backed skeletal probe:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      xvfb-run -a env CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --command /absolute/path/to/disposable-semantic-pose-command.json \
      --report /absolute/path/to/semantic-pose-report.json

The command is experiment-local and canonical newline-terminated JSON. It
contains the command/schema boundary, exact shared-pose format/ID/SHA/version,
the ordered two-entry carrier target list, and exactly 18 ordered semantic rules
using the existing kind/role/anchor selectors and source `xyzw` rotations. Its
identity-frame evidence declares column vectors, `xyzw`, `C = I`, and `s = 1`
with `evidence_only=true` and `runtime_conformance=false`. It contains no node
names, bone indices, clips, or durable adapter/package schema. Python validates
the command and carrier before launch and again after Godot returns; any target,
	selector, source, frame, payload, or identity change prevents report
publication. Godot receives the injected semantic payload and does not load the
shared-pose file in command mode. Its command evidence is derived from runtime
root metadata plus each `Skeleton3D` bone's semantic metadata and observed local
rotation, with measured command error and complete local/global/`Skin` matrix
counts; it is not an echoed selector list. The no-command and carrier-only paths
remain unchanged predecessor paths.

Build the fixed canonical semantic-contact command from the same carrier and
the validated semantic-pose command:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
        experiments/godot-provisional-host-feasibility/disposable_semantic_contact_command.py \
        build \
        --gallery /absolute/path/to/completed-gallery \
        --carrier /absolute/path/to/disposable-avatar-carrier.json \
        --pose-command /absolute/path/to/disposable-semantic-pose-command.json \
        --output /absolute/path/to/disposable-semantic-contact-command.json

Validate the contact command independently against the fresh gallery, carrier,
and semantic-pose lineage:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
        experiments/godot-provisional-host-feasibility/disposable_semantic_contact_command.py \
        validate \
        --gallery /absolute/path/to/completed-gallery \
        --carrier /absolute/path/to/disposable-avatar-carrier.json \
        --pose-command /absolute/path/to/disposable-semantic-pose-command.json \
        --command /absolute/path/to/disposable-semantic-contact-command.json

Consume it through the carrier-, pose-, and CK-projection-backed skeletal probe:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      xvfb-run -a env CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --command /absolute/path/to/disposable-semantic-pose-command.json \
      --projection /absolute/path/to/disposable-ck-rust-projection.json \
      --ck-cli /absolute/path/to/target/debug/creature-kernel \
      --contact-command /absolute/path/to/disposable-semantic-contact-command.json \
      --report /absolute/path/to/semantic-deformation-report.json \
      --deformation-captures /absolute/path/to/not-yet-existing-deformation-captures

Publish the screened static replay captures for human comparison:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      dev-tools/visual-review/publish_godot_deformation.py \
      --root /absolute/path/to/existing-review-root \
      --report /absolute/path/to/semantic-deformation-report.json \
      --captures /absolute/path/to/deformation-captures

Contact mode requires the explicit Rust CLI and validated CK projection in
addition to the carrier and semantic-pose command. It does not alter the
experiment-local command, package, adapter, or engine-selection boundaries.

Run the new opt-in paired runtime evaluation, which launches the same validated
contact setup once with CPU deformation and once with rigid contact only:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      xvfb-run -a env CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --command /absolute/path/to/disposable-semantic-pose-command.json \
      --projection /absolute/path/to/disposable-ck-rust-projection.json \
      --ck-cli /absolute/path/to/target/debug/creature-kernel \
      --contact-command /absolute/path/to/disposable-semantic-contact-command.json \
      --report /absolute/path/to/runtime-evaluation-report.json \
      --deformation-captures /absolute/path/to/not-yet-existing-runtime-evaluation-captures \
      --runtime-evaluation

This mode requires an attended X11 renderer and fixes both launches to
`--resolution 512x512`, `--display-driver x11`, and
`--rendering-method gl_compatibility`. The corrected final evidence is one
bounded paired run in Godot 4.7.2 on Ubuntu 22.04.5 under WSL2, with a 12th Gen
Intel Core i7-12700KF, Jolt Physics at 60 Hz, and
`max_steps_per_frame` 8. The actual display was X11 at 512x512 using
`gl_compatibility`/`opengl3`. The adapter reported D3D12 (NVIDIA GeForce RTX
4070), vendor Microsoft, Mesa/OpenGL 4.2
(`4.2 (Core Profile) Mesa 23.2.1-1ubuntu3.1~22.04.4`), and an empty optional
`driver-info` list. The paired report binds launcher identity alongside
project, script, executable, and validated input identities.

The trial-local screens are a 60 Hz physics loop with a 20,000 us frame
(physics-interval) screen and a 2,000 us CPU deformation-core screen;
percentiles use nearest-rank p95. CPU deformation core (not mesh-only) covered
39 samples at p95 `1075us`, maximum `1461us`, and zero above `2000us`.
CPU-mode physics covered 64 samples at p95 `21489us`, maximum `25119us`, and
eight above `20000us`. Rigid physics covered 64 samples at p95 `20062us`,
maximum `23196us`, and four above `20000us`; rigid deformation is N/A.

The CPU deformation core includes validation, transforms, falloff or
interpolation, normal preparation, and `ArrayMesh` mutation. It excludes
experiment-only readback, state, and coherence validation, which remain
retained in the evidence-inclusive wall timing. Embedded per-mode semantic
evidence now audits capabilities: CPU mode has semantic contact, physical
response, deformation, and captures; rigid mode has semantic contact and
physical response only. Rigid-contact-only is a separately exercised,
lower-fidelity mode, not automatic failover; it preserves contact/physical
response and omits deformation/captures, with no visual equivalence claimed.
A successful report denotes valid execution; `within_screen` carries the
screen outcome. The CPU core screen passed, while the frame screen did not.
Two pre-correction runs exposed a mesh-only attribution error; their CPU values
`653us` and `633us` are superseded and must not be treated as full deformation
evidence. Godot allocator snapshots only were `107940927` current /
`110380697` maximum bytes for CPU and `98272523` current / `105477587` maximum
bytes for rigid; process RSS and GPU memory were not measured. This is one
bounded run, not a broad benchmark, product/runtime budget, or permanent
Godot/Jolt engine choice.

Build a disposable CK/Rust-backed projection from the same carrier and gallery
with the workspace CLI. The CLI path is mandatory and must be an absolute,
native WSL/Linux path to an executable regular non-symlink file; wrappers,
relative paths, symlinks, and Windows-style paths are rejected:

    cargo build -p creature-kernel-cli

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/disposable_ck_projection.py \
      build \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --output /absolute/path/to/disposable-ck-rust-projection.json \
      --cli /absolute/path/to/target/debug/creature-kernel

Validate that projection afresh against the carrier, gallery, and the same
native CLI executable:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/disposable_ck_projection.py \
      validate \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --projection /absolute/path/to/disposable-ck-rust-projection.json \
      --cli /absolute/path/to/target/debug/creature-kernel

The builder makes one ordered CLI call containing the two explicit
instance/source pairs for `inspect-runtime-input`. It records one compact
per-avatar runtime-input summary alongside the source and artifact lineage,
and binds the executable SHA-256, byte count, operation, and format. It checks
the Rust output envelope, exact instance IDs, source identity, prepared basis,
and bounded prepared/structural count maps before compacting the evidence. The
builder rechecks the carrier, gallery sources, and executable after inspection;
validation also requires an exact fresh rebuild. Publication is canonical JSON
and does not overwrite an existing output.

The skeletal runner accepts the projection only with its paired explicit
`--ck-cli /absolute/path/to/target/debug/creature-kernel` input. It performs the
same fresh projection validation before launch and again before publishing a
success report; supplying either argument without the other fails closed.

This provisional projection is transport and evidence bookkeeping
for this experiment only
(`creature-kernel.disposable-ck-rust-projection.v2`, boundary
`experiment_local_ck_projection_evidence_only`). It does not generate geometry
or define a durable CK package, artifact/build identity, adapter, host contract,
compatibility promise, Readiness 3 activation, or engine selection.

## Disposable CK directory payload

The current uncommitted package slice adds a disposable directory payload for
the same two ordered avatars. Its manifest is
`creature-kernel.disposable-ck-directory-payload.v1` with an
`experiment_local_directory_payload_evidence_only` boundary. The exact tree
contains `manifest.json`, exactly two source documents
(`avatars/0/source.json` and `avatars/1/source.json`), and seven load-time files
per avatar: `metrics.json`, `neutral.ply`, `posed.ply`, `skeleton.json`,
`weights.json`, `proxies-neutral.json`, and `proxies-posed.json`. These fixtures
require `source.dependencies` to be exactly `[]`; that is a fixture precondition
for copying source bytes, not a general dependency-closure result.

Build freshly validates the gallery, carrier, projection, and explicit native
Rust CLI, copies the exact bytes, revalidates the inputs after copying, and
publishes the manifest last. Offline package validation requires none of those
source inputs: it checks canonical manifest bytes, the exact directory
inventory, safe relative paths, regular non-symlink files, byte counts, and
SHA-256 identities. The package-only validator therefore remains an integrity
check for this disposable payload, not a package or wire contract.

Build the payload through the documented launcher:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/disposable_ck_package.py \
      build \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --projection /absolute/path/to/disposable-ck-rust-projection.json \
      --output /absolute/path/to/disposable-ck-package \
      --cli /absolute/path/to/target/debug/creature-kernel

Validate only the copied payload, without the gallery, carrier, projection, or
CLI being available:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/disposable_ck_package.py \
      validate \
      --package /absolute/path/to/disposable-ck-package

Run the package-backed skeletal/contact/deformation probe with the pinned
visible-Godot launcher:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      xvfb-run -a env CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --carrier /absolute/path/to/disposable-avatar-carrier.json \
      --command /absolute/path/to/disposable-semantic-pose-command.json \
      --projection /absolute/path/to/disposable-ck-rust-projection.json \
      --ck-cli /absolute/path/to/target/debug/creature-kernel \
      --contact-command /absolute/path/to/disposable-semantic-contact-command.json \
      --package /absolute/path/to/disposable-ck-package \
      --report /absolute/path/to/package-runtime-report.json \
      --deformation-captures /absolute/path/to/not-yet-existing-package-captures

In package mode, the runner sends Godot the package root and manifest plus the
existing validated carrier, CK projection, injected semantic-pose payload, and
optional semantic-contact inputs; it does not send a gallery path to Godot.
Godot reads both avatars from package bytes, constructs their runtime objects,
and emits `validated_ck_package` evidence that Python validates against the
package and fresh predecessor lineage. Non-package paths remain gallery-backed
and unchanged. The real pinned visible-Godot package integration test exists,
but remains pending an attended opt-in run.

This is no stable package or wire format, adapter contract, Readiness 3 result,
or engine choice. It also makes no general dependency-closure claim and does
not activate a runtime package, adapter, or host contract.

On a Linux or WSL host with `xvfb-run` available, use a virtual display to
exercise the same real-renderer path without opening a window. Set the existing
native temporary-root override so inherited Windows `TEMP`/`TMP` warnings do
not contaminate the command's JSON stdout:

    CK_CURRENT_FORM_SURFACE_TMPDIR=/tmp \
      xvfb-run -a env CK_ALLOW_VISIBLE_GODOT=1 \
      experiments/current-form-surface-preview/surface_preview_launcher.sh \
      experiments/godot-provisional-host-feasibility/run_skeletal_pose_smoke.py \
      --gallery /absolute/path/to/completed-gallery \
      --report /absolute/path/to/skeletal-pose-report.json

For Python tests and probes, use the canonical test wrapper. It delegates
interpreter selection, pinned dependency validation, and native temporary-root
setup to the current-form surface-preview launcher, while preserving
`CK_GODOT_STRUCTURAL_GALLERY` for the tests:

    experiments/godot-provisional-host-feasibility/test.sh

Pass one local `test*.py` filename or discovery pattern for a focused run. The
selector must begin with `test` and cannot contain `/`:

    experiments/godot-provisional-host-feasibility/test.sh \
      test_structural_gallery_smoke.py

Run the focused skeletal binding suite with:

    experiments/godot-provisional-host-feasibility/test.sh \
      test_skeletal_pose_smoke.py

The default profiles are `compact_broad_short_limb_large_head` and
`tall_narrow_long_legged`. Repeat `--profile-id` exactly twice to select a
different distinct pair from the frozen four-profile gallery.

Python first invokes the existing exact gallery validator and immutable
non-rendered evidence projection. The Python probes use the neutral runner's safe
temporary, atomic-publication, and postflight-revalidation infrastructure: it
copies the minimal project and selected GDScript into a temporary directory,
isolates home/XDG/temporary roots, rejects Godot error or resource-leak
diagnostics, and cross-checks the returned report against validator-backed
evidence before atomically writing canonical JSON. The reported CK XYZ to
Godot XYZ identity mapping and fixed profile translations are disposable
host-local choices, not a durable adapter contract. The carrier root names and
metadata are likewise experiment-only runtime read-back evidence.

## Checks

Run the focused automated tests from the repository root:

    bash experiments/godot-provisional-host-feasibility/test_launcher.sh
    experiments/godot-provisional-host-feasibility/test.sh

The launcher tests create disposable fake executables and launcher copies in a
temporary directory; they never alter the production digest. The neutral
26-test suite covers fixture-independent selection, rejection, diagnostics,
safe publication, and postflight behavior. The posed 18-test suite additionally
covers all six projected artifacts, independent posed vertex/normal/proxy
recomputation, deterministic repeated reports, and direct-mutation rejection.
Seven wrapper tests cover managed-environment routing and selector safety.
The disposable carrier suite contains 15 tests covering exact shape,
deterministic canonical publication, strict bounded loading, both frozen profile
pairs, instance identity, tampering and mixed-lineage rejection, and payload
reconstruction, including deterministic symlink-swap read and publication
regressions. The `test_skeletal_pose_smoke.py` focused result contains 68 tests
with 16 expected display skips, covering both frozen profile pairs, complete
`Skeleton3D`/`Skin` binding evidence, malformed and
tampered inputs and reports, deterministic reruns, carrier load-through with
one-to-one runtime-root read-back, real-process rejection of noncanonical
carrier identity, command-mode semantic injection/read-back, no pose-file
fallback after injection, repository/cache cleanliness, and bounded semantic
contact command consumption and report validation. The 12-test
semantic command suite covers
deterministic canonical bytes for both frozen profile pairs, strict field,
rotation, quaternion precision, and frame validation, lineage mismatch, and
safe publication. The neutral and posed
suites run their real Godot paths when the completed-gallery fixture and exact
pinned binary are available.
The nine-test semantic contact command suite covers fixed participant mapping,
fresh predecessor lineage, canonical publication, strict field validation,
tampering and mutation rejection, and command identity. Focused real contact
integration passed in 182.453s; the focused no-display file has 16 expected display
skips when its attended renderer path is unavailable.
The 19-test disposable CK projection suite covers exact producer and transport
identity, private CLI/source snapshot binding, bounded subprocess output, fresh
source/carrier/gallery/executable revalidation, deterministic publication,
mutation rejection, and both frozen
profile pairs against the native Rust CLI.
The main consolidated Godot experiment suite contains 197 tests with 31
expected skips. The real pinned visible-Godot package integration test exists,
but remains pending an attended opt-in run. The named human Godot feasibility
checkpoint is not yet reached.
Skeletal-pose integration additionally requires
an active X11 display and `CK_ALLOW_VISIBLE_GODOT=1` to mark an attended run;
otherwise those visible integration cases are skipped. All Godot probe suites
verify that no repository `.godot` cache directory is created.

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
temporary Godot projects and remove those projects afterward.

This is not a package, adapter, Readiness 3 result, semantic-contact result,
deformation result, physical-response result, benchmark, or checkpoint claim.
It makes no claim about a permanent Godot engine selection or about the wider
feasibility trial. The skeletal smoke's binding claim is host-local only; none
of the probes claims animation, semantic pose injection, physics stepping,
contact, deformation, render output, adapter/package/R3/performance/checkpoint
evidence, or visual review.

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
host-local choices, not a durable adapter contract.

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
The skeletal pose suite contains 14 tests covering both frozen profile pairs,
complete `Skeleton3D`/`Skin` binding evidence, malformed and tampered inputs,
deterministic reruns, and repository/cache cleanliness. The neutral and posed
suites run their real Godot paths when the completed-gallery fixture and exact
pinned binary are available. Skeletal-pose integration additionally requires
an active X11 display and `CK_ALLOW_VISIBLE_GODOT=1` to mark an attended run;
otherwise those visible integration cases are skipped. All Godot probe suites
verify that no repository `.godot` cache directory is created.

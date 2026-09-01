#!/usr/bin/env python3
"""Rerender one hash-bound standard-neutral alternative candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn


VISUAL_REVIEW_ROOT = Path(__file__).resolve().parent
if str(VISUAL_REVIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(VISUAL_REVIEW_ROOT))

import common  # noqa: E402
import publish as publication_helpers  # noqa: E402
import publish_provisional_form as inspection_helpers  # noqa: E402
import publish_successor_anatomy_gallery as exact_five_publisher  # noqa: E402
from common import ValidationError, canonical_json  # noqa: E402

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2] / "experiments" / "current-form-surface-preview"
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import successor_surface_preview as successor  # noqa: E402


class NeutralAlternativeRerenderError(RuntimeError):
    """A bounded, fail-closed neutral rerender failure."""


OUTPUT_FORMAT = "creature-kernel.disposable-neutral-alternative-rerender.v1"
STANDARD_NEUTRAL_PROFILE_ID = "standard_neutral_reference"
OUTPUT_PNG_NAME = f"{STANDARD_NEUTRAL_PROFILE_ID}.png"
OUTPUT_PLY_NAME = "surface.ply"
OUTPUT_IDENTITY_NAME = "identity.json"
EXPECTED_OUTPUTS = frozenset({OUTPUT_PLY_NAME, OUTPUT_PNG_NAME, OUTPUT_IDENTITY_NAME})
EXPECTED_CANVAS = {"width": 1800, "height": 1500, "mode": "RGB"}
EXPECTED_VIEWS = ("front", "side", "three-quarter")
IMPLEMENTATION_SOURCE_MAX_BYTES = 4_000_000
ARTIFACT_MAX_BYTES = 256 * 1024 * 1024
RUNTIME_REQUIREMENTS_MAX_BYTES = 64 * 1024
RUNTIME_MODULE_FILE_MAX_BYTES = 32 * 1024 * 1024
RUNTIME_MODULE_FILE_MAX_COUNT = 128
RUNTIME_IMPORT_NAMES = {
    "numpy": "numpy",
    "scikit-image": "skimage",
    "Pillow": "PIL",
}
RUNTIME_MODULE_SUFFIXES = {".py", ".pyc", ".so", ".pyd", ".dll", ".dylib"}


def _fail(message: str) -> NoReturn:
    raise NeutralAlternativeRerenderError(message)


def _validate_sampling(samples: int, padding: float, smooth_k: float) -> None:
    if (
        type(samples) is not int
        or samples < successor.ALTERNATIVE_MIN_SAMPLES
        or samples > successor.MAX_SAMPLES
        or samples**3 > successor.MAX_VOXELS
    ):
        _fail(
            "samples-per-axis must be between "
            f"{successor.ALTERNATIVE_MIN_SAMPLES} and {successor.MAX_SAMPLES} "
            "for the neutral alternative"
        )
    if not math.isfinite(float(padding)) or padding < 0.0:
        _fail("padding must be finite and non-negative")
    if not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("smooth-k must be finite and positive")


def _validate_source_manifest(
    source_manifest: Path,
) -> tuple[
    dict[str, Any],
    bytes,
    list[tuple[dict[str, Any], common.SourceReference, dict[str, Any], bytes]],
]:
    """Use the exact-five publisher's source admission contract."""

    try:
        manifest, manifest_bytes, records = exact_five_publisher._validate_source_manifest(source_manifest)
    except exact_five_publisher.SuccessorAnatomyGalleryError as exc:
        _fail(str(exc))
    if len(exact_five_publisher.PROFILE_IDS) != 5 or len(records) != 5:
        _fail("source manifest must validate as the exact five-profile contract")
    if records[0][0].get("id") != STANDARD_NEUTRAL_PROFILE_ID:
        _fail("source manifest first profile must be standard_neutral_reference")
    return manifest, manifest_bytes, records


def _inspect_profile(
    profile: dict[str, Any],
    source_ref: common.SourceReference,
    source_bytes: bytes,
    executable: Path,
    temporary_root: Path,
    expected_namespace: str,
) -> Any:
    """Delegate exactly one profile inspection to the existing bounded helper."""

    try:
        return exact_five_publisher._inspect_profile(
            profile,
            source_ref,
            source_bytes,
            executable,
            temporary_root,
            expected_namespace,
        )
    except exact_five_publisher.SuccessorAnatomyGalleryError as exc:
        _fail(str(exc))


def _file_identity(path: Path, maximum: int, where: str, *, repository_path: bool) -> dict[str, Any]:
    try:
        return exact_five_publisher._file_identity(
            path,
            maximum,
            where,
            repository_path=repository_path,
        )
    except exact_five_publisher.SuccessorAnatomyGalleryError as exc:
        _fail(str(exc))


def _runtime_identity(requirements_path: Path) -> dict[str, Any]:
    """Validate the pinned experiment environment and record a bounded fingerprint.

    This is deliberately a narrow evidence fingerprint: it covers the pinned
    requirement versions, the interpreter, and file hashes for currently
    imported modules belonging to those packages. It does not capture all
    ambient process, OS, loader, native-library, filesystem, or machine state.
    """

    try:
        requirements_bytes = requirements_path.read_bytes()
    except OSError as exc:
        _fail(f"could not read pinned runtime requirements: {exc}")
    if len(requirements_bytes) > RUNTIME_REQUIREMENTS_MAX_BYTES:
        _fail("pinned runtime requirements exceed the bounded size")

    requirements: list[tuple[str, str, str, str]] = []
    seen_distributions: set[str] = set()
    try:
        requirement_lines = requirements_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        _fail(f"pinned runtime requirements are not UTF-8: {exc}")
    for line_number, raw_line in enumerate(requirement_lines, start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.count("==") != 1:
            _fail(f"pinned runtime requirements line {line_number} must use name==version")
        distribution, expected_version = (part.strip() for part in line.split("==", 1))
        normalized_distribution = distribution.lower().replace("_", "-")
        if not distribution or not expected_version:
            _fail(f"pinned runtime requirements line {line_number} is incomplete")
        if normalized_distribution in seen_distributions:
            _fail(f"pinned runtime requirements contain duplicate distribution {distribution}")
        seen_distributions.add(normalized_distribution)
        import_name = RUNTIME_IMPORT_NAMES.get(distribution, distribution.replace("-", "_"))
        try:
            installed_version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            _fail(f"pinned runtime requirement {distribution}=={expected_version} is not installed: {exc}")
        if installed_version != expected_version:
            _fail(
                f"pinned runtime requirement {distribution}=={expected_version} is installed as {installed_version}"
            )
        try:
            importlib.import_module(import_name)
        except Exception as exc:
            _fail(f"pinned runtime import {import_name!r} failed for {distribution}: {exc}")
        requirements.append((distribution, expected_version, installed_version, import_name))

    module_paths: dict[str, set[str]] = {}
    for _distribution, _expected_version, _installed_version, import_name in requirements:
        module = sys.modules.get(import_name)
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str) or not module_file:
            _fail(f"pinned runtime import {import_name!r} has no file-backed module")
        for loaded_name, loaded_module in sys.modules.items():
            if loaded_name != import_name and not loaded_name.startswith(f"{import_name}."):
                continue
            loaded_file = getattr(loaded_module, "__file__", None)
            if not isinstance(loaded_file, str) or not loaded_file:
                continue
            loaded_path = Path(loaded_file)
            if loaded_path.suffix.lower() in RUNTIME_MODULE_SUFFIXES:
                module_paths.setdefault(str(loaded_path), set()).add(loaded_name)

    if len(module_paths) > RUNTIME_MODULE_FILE_MAX_COUNT:
        _fail(
            "pinned runtime imported-module fingerprint exceeds the bounded file count "
            f"({RUNTIME_MODULE_FILE_MAX_COUNT})"
        )
    module_files: list[dict[str, Any]] = []
    for module_path_text in sorted(module_paths):
        module_path = Path(module_path_text)
        file_identity = _file_identity(
            module_path,
            RUNTIME_MODULE_FILE_MAX_BYTES,
            f"pinned runtime module file {module_path}",
            repository_path=False,
        )
        module_files.append(
            {
                "modules": sorted(module_paths[module_path_text]),
                "path": module_path_text,
                "bytes": file_identity["bytes"],
                "sha256": file_identity["sha256"],
            }
        )

    return {
        "fingerprint_scope": (
            "bounded pinned-requirements/interpreter/imported-module fingerprint; "
            "does not capture all ambient process, OS, loader, native-library, filesystem, or machine state"
        ),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "version_info": list(sys.version_info[:5]),
        },
        "requirements_sha256": hashlib.sha256(requirements_bytes).hexdigest(),
        "requirements": [
            {
                "distribution": distribution,
                "required_version": expected_version,
                "installed_version": installed_version,
                "import": import_name,
            }
            for distribution, expected_version, installed_version, import_name in requirements
        ],
        "module_files": module_files,
        "limits": {
            "max_requirements_bytes": RUNTIME_REQUIREMENTS_MAX_BYTES,
            "max_module_file_bytes": RUNTIME_MODULE_FILE_MAX_BYTES,
            "max_module_files": RUNTIME_MODULE_FILE_MAX_COUNT,
        },
    }


def _implementation_identity(executable: Path) -> dict[str, Any]:
    """Hash every implementation input that can change this rerender."""

    files = {
        "rerender_helper": _file_identity(
            Path(__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "neutral rerender helper",
            repository_path=True,
        ),
        "exact_five_publisher": _file_identity(
            Path(exact_five_publisher.__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "exact-five publisher",
            repository_path=True,
        ),
        "successor": _file_identity(
            Path(successor.__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "successor implementation",
            repository_path=True,
        ),
        "renderer": _file_identity(
            Path(successor._baseline.__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "successor renderer",
            repository_path=True,
        ),
        "profile_source_generator": _file_identity(
            exact_five_publisher._profile_source_path(),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "profile-source generator",
            repository_path=True,
        ),
        "common_safety_helper": _file_identity(
            Path(common.__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "visual-review common safety helper",
            repository_path=True,
        ),
        "publication_helper": _file_identity(
            Path(publication_helpers.__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "visual-review publication helper",
            repository_path=True,
        ),
        "inspection_helper": _file_identity(
            Path(inspection_helpers.__file__),
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "provisional-form inspection helper",
            repository_path=True,
        ),
        "launcher": _file_identity(
            EXPERIMENT_ROOT / "surface_preview_launcher.sh",
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "surface-preview launcher",
            repository_path=True,
        ),
        "requirements": _file_identity(
            EXPERIMENT_ROOT / "requirements.txt",
            IMPLEMENTATION_SOURCE_MAX_BYTES,
            "surface-preview requirements",
            repository_path=True,
        ),
        "pinned_executable": _file_identity(
            executable,
            exact_five_publisher.PRODUCER_EXECUTABLE_MAX_BYTES,
            "pinned creature-kernel executable",
            repository_path=False,
        ),
    }
    runtime = _runtime_identity(EXPERIMENT_ROOT / "requirements.txt")
    if runtime["requirements_sha256"] != files["requirements"]["sha256"]:
        _fail("pinned runtime requirements changed while building implementation identity")
    return {
        "files": files,
        "runtime": runtime,
        "identity_sha256": hashlib.sha256(
            successor._canonical({"files": files, "runtime": runtime})
        ).hexdigest(),
    }


def _output_file_identity(path: Path, where: str) -> dict[str, Any]:
    identity = _file_identity(path, ARTIFACT_MAX_BYTES, where, repository_path=False)
    if identity["bytes"] <= 0:
        _fail(f"{where} must not be empty")
    return identity


def _refuse_existing_destination(parent_fd: int, output_id: str) -> None:
    try:
        info = os.stat(output_id, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        _fail(f"could not inspect output destination {output_id}: {exc}")
    if stat.S_ISLNK(info.st_mode):
        _fail(f"refusing existing destination symlink: {output_id}")
    _fail(f"refusing to overwrite existing destination: {output_id}")


def _remove_staging(parent_fd: int, staging_name: str, staging_fd: int, staging_identity: tuple[int, int]) -> None:
    """Remove only files created in this invocation's staging directory."""

    for name in EXPECTED_OUTPUTS:
        try:
            os.unlink(name, dir_fd=staging_fd)
        except FileNotFoundError:
            pass
        except OSError:
            pass
    try:
        info = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        if (info.st_dev, info.st_ino) == staging_identity and stat.S_ISDIR(info.st_mode):
            os.rmdir(staging_name, dir_fd=parent_fd)
    except OSError:
        pass


def _copy_private_file(
    source_path: Path,
    staging_fd: int,
    name: str,
    expected: dict[str, Any],
    where: str,
) -> None:
    """Copy one private output into staging and verify the copy by descriptors."""

    source_fd = -1
    output_fd = -1
    output_identity: tuple[int, int] | None = None
    completed = False
    try:
        source_fd = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW)
        source_info = os.fstat(source_fd)
        if not stat.S_ISREG(source_info.st_mode):
            _fail(f"{where} is not a regular file")
        if source_info.st_size > ARTIFACT_MAX_BYTES:
            _fail(f"{where} exceeds the bounded size")
        output_fd = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o644,
            dir_fd=staging_fd,
        )
        output_info = os.fstat(output_fd)
        if not stat.S_ISREG(output_info.st_mode):
            _fail(f"staged {name} is not a regular file")
        output_identity = (output_info.st_dev, output_info.st_ino)

        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(source_fd, min(1024 * 1024, ARTIFACT_MAX_BYTES - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > ARTIFACT_MAX_BYTES:
                _fail(f"{where} exceeds the bounded size")
            digest.update(chunk)
            written = 0
            while written < len(chunk):
                written += os.write(output_fd, chunk[written:])
        final_source_info = os.fstat(source_fd)
        if (
            (final_source_info.st_dev, final_source_info.st_ino, final_source_info.st_size)
            != (source_info.st_dev, source_info.st_ino, size)
        ):
            _fail(f"{where} changed while being copied")
        observed = {"bytes": size, "sha256": digest.hexdigest()}
        if observed != {"bytes": expected["bytes"], "sha256": expected["sha256"]}:
            _fail(f"{where} failed copy digest/size verification")
        os.fchmod(output_fd, 0o644)
        os.fsync(output_fd)
        final_output_info = os.fstat(output_fd)
        if (
            (final_output_info.st_dev, final_output_info.st_ino, final_output_info.st_size)
            != (output_info.st_dev, output_info.st_ino, size)
        ):
            _fail(f"staged {name} changed while being copied")
        completed = True
    except NeutralAlternativeRerenderError:
        raise
    except OSError as exc:
        _fail(f"could not stage {name}: {exc}")
    finally:
        if source_fd >= 0:
            try:
                os.close(source_fd)
            except OSError:
                pass
        if output_fd >= 0:
            try:
                os.close(output_fd)
            except OSError:
                pass
        if not completed and output_identity is not None:
            try:
                current = os.stat(name, dir_fd=staging_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == output_identity:
                    os.unlink(name, dir_fd=staging_fd)
            except OSError:
                pass


def _fd_file_identity(staging_fd: int, name: str, where: str) -> dict[str, Any]:
    """Hash one staged regular file through its open descriptor."""

    fd = -1
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=staging_fd)
        initial = os.fstat(fd)
        if stat.S_ISLNK(initial.st_mode) or not stat.S_ISREG(initial.st_mode):
            _fail(f"{where} is not a regular file")
        if initial.st_size > ARTIFACT_MAX_BYTES:
            _fail(f"{where} exceeds the bounded size")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, ARTIFACT_MAX_BYTES - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > ARTIFACT_MAX_BYTES:
                _fail(f"{where} exceeds the bounded size")
            digest.update(chunk)
        final = os.fstat(fd)
        if (final.st_dev, final.st_ino, final.st_size) != (initial.st_dev, initial.st_ino, size):
            _fail(f"{where} changed while being verified")
        return {"bytes": size, "sha256": digest.hexdigest()}
    except NeutralAlternativeRerenderError:
        raise
    except OSError as exc:
        _fail(f"could not verify {where}: {exc}")
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


def _validate_staging_inventory(
    staging_fd: int,
    staging_identity: tuple[int, int],
    expected_identities: dict[str, dict[str, Any]],
) -> None:
    """Verify the open staging directory and every staged file immediately before rename."""

    try:
        initial = os.fstat(staging_fd)
        entries = os.listdir(staging_fd)
    except OSError as exc:
        _fail(f"could not inspect neutral rerender staging: {exc}")
    if not stat.S_ISDIR(initial.st_mode) or (initial.st_dev, initial.st_ino) != staging_identity:
        _fail("neutral rerender staging directory changed before publication")
    if set(entries) != EXPECTED_OUTPUTS or set(expected_identities) != EXPECTED_OUTPUTS:
        _fail("neutral rerender staging inventory is not exactly surface.ply, standard_neutral_reference.png, identity.json")
    for name in sorted(entries):
        observed = _fd_file_identity(staging_fd, name, f"neutral rerender staging entry {name}")
        expected = expected_identities[name]
        if observed != {"bytes": expected["bytes"], "sha256": expected["sha256"]}:
            _fail(f"neutral rerender staging entry {name} failed final digest/size verification")
    final = os.fstat(staging_fd)
    if not stat.S_ISDIR(final.st_mode) or (final.st_dev, final.st_ino) != staging_identity:
        _fail("neutral rerender staging directory changed during final verification")


def rerender_neutral_alternative(
    output_parent: Path,
    output_id: str,
    source_manifest: Path,
    *,
    creature_kernel: Path | None = None,
    samples: int = successor.DEFAULT_SAMPLES,
    padding: float = successor.DEFAULT_PADDING,
    smooth_k: float = successor.DEFAULT_SMOOTH_K,
) -> dict[str, Any]:
    """Build and atomically retain only the first exact-five neutral profile."""

    _validate_sampling(samples, padding, smooth_k)
    try:
        output_id = common.validate_id(output_id, "output id")
    except ValidationError as exc:
        _fail(str(exc))

    output_parent = Path(output_parent).absolute()
    common.require_secure_fs_support()
    try:
        parent_fd = publication_helpers._open_directory(None, output_parent, "output parent")
    except ValidationError as exc:
        _fail(str(exc))

    staging_name: str | None = None
    staging_fd: int | None = None
    staging_identity: tuple[int, int] | None = None
    installed = False
    try:
        _refuse_existing_destination(parent_fd, output_id)
        try:
            manifest, manifest_bytes, records = _validate_source_manifest(source_manifest)
        except NeutralAlternativeRerenderError:
            raise
        except (ValidationError, OSError) as exc:
            _fail(f"could not validate source manifest: {exc}")

        try:
            executable_reference = exact_five_publisher._validate_executable(
                creature_kernel or inspection_helpers.default_creature_kernel()
            )
        except exact_five_publisher.SuccessorAnatomyGalleryError as exc:
            _fail(str(exc))

        with tempfile.TemporaryDirectory(prefix="ck-neutral-alternative-") as temporary:
            temporary_root = Path(temporary)
            try:
                temporary_info = temporary_root.stat()
            except OSError as exc:
                _fail(f"could not inspect private neutral rerender temporary directory: {exc}")
            if not stat.S_ISDIR(temporary_info.st_mode) or stat.S_IMODE(temporary_info.st_mode) != 0o700:
                _fail("neutral rerender temporary directory must be private mode 0700")
            try:
                executable = exact_five_publisher._pin_executable(executable_reference, temporary_root)
            except (
                exact_five_publisher.SuccessorAnatomyGalleryError,
                publication_helpers.PublishError,
            ) as exc:
                _fail(f"could not pin creature-kernel executable: {exc}")
            implementation = _implementation_identity(executable)

            profile, source_ref, _source_value, source_bytes = records[0]
            inspected = _inspect_profile(
                profile,
                source_ref,
                source_bytes,
                executable,
                temporary_root,
                manifest["source"]["base_namespace"],
            )
            if inspected.profile_id != STANDARD_NEUTRAL_PROFILE_ID:
                _fail("inspected profile is not standard_neutral_reference")

            try:
                baseline_capture_bound, prepared = exact_five_publisher._shared_capture_bound([inspected])
            except exact_five_publisher.SuccessorAnatomyGalleryError as exc:
                _fail(str(exc))
            if len(prepared) != 1 or prepared[0][0] is not inspected:
                _fail("neutral capture preparation did not contain exactly the inspected profile")
            guide = prepared[0][1]

            try:
                mesh = successor.build_neutral_alternative_variant(
                    inspected.form,
                    inspected.descriptors,
                    samples=samples,
                    padding=padding,
                    smooth_k=smooth_k,
                )
            except (
                successor.SuccessorPreviewError,
                successor._baseline.PreviewError,
                AttributeError,
                IndexError,
                OSError,
                OverflowError,
                ValueError,
                TypeError,
                KeyError,
            ) as exc:
                _fail(f"standard_neutral_reference successor surface build failed: {exc}")

            try:
                capture_bound = exact_five_publisher._capture_bound_with_components(
                    baseline_capture_bound,
                    [(inspected, guide, mesh)],
                )
                exact_five_publisher.successor._baseline._validate_hybrid_guide(guide, capture_bound)
            except exact_five_publisher.SuccessorAnatomyGalleryError as exc:
                _fail(str(exc))
            except (successor._baseline.PreviewError, ValueError, TypeError, KeyError) as exc:
                _fail(f"standard_neutral_reference cannot use the corrected capture bound: {exc}")

            private_surface_path = temporary_root / OUTPUT_PLY_NAME
            private_png_path = temporary_root / OUTPUT_PNG_NAME
            private_identity_path = temporary_root / OUTPUT_IDENTITY_NAME
            try:
                successor._write_ply(private_surface_path, mesh)
                capture = {
                    "canvas": dict(EXPECTED_CANVAS),
                    "views": list(EXPECTED_VIEWS),
                    "panels_per_view": 3,
                    "global_capture_bound": exact_five_publisher._bound_json(capture_bound),
                    "layout": successor._baseline._layout_json(),
                    "projections": successor._baseline._projection_json(),
                }
                successor._baseline._render(
                    private_png_path,
                    mesh.vertices,
                    mesh.faces,
                    STANDARD_NEUTRAL_PROFILE_ID,
                    guide=guide,
                    bounds=capture_bound,
                    render_components=mesh.render_components,
                )
                surface_identity = _output_file_identity(private_surface_path, "neutral rerender surface.ply")
                image_identity = exact_five_publisher._image_identity(
                    private_png_path,
                    inspected,
                    capture,
                    implementation,
                )
                try:
                    metrics = json.loads(successor._canonical(mesh.metrics))
                except (TypeError, ValueError, OverflowError) as exc:
                    _fail(f"neutral rerender mesh metrics are not canonical JSON: {exc}")

                source_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
                source_manifest_source = manifest["source"]
                output_identities = {
                    OUTPUT_PLY_NAME: surface_identity,
                    OUTPUT_PNG_NAME: {
                        "bytes": image_identity["bytes"],
                        "sha256": image_identity["sha256"],
                    },
                }
                identity = {
                    "format": OUTPUT_FORMAT,
                    "schema_version": 1,
                    "output_id": output_id,
                    "profile_id": STANDARD_NEUTRAL_PROFILE_ID,
                    "source_manifest_sha256": source_manifest_sha256,
                    "candidate_sha256": source_manifest_source["candidate_sha256"],
                    "base_source_sha256": source_manifest_source["source_sha256"],
                    "source_document_sha256": inspected.source_sha256,
                    "producer_envelope_sha256": inspected.producer_envelope_sha256,
                    "neutral_variant_id": successor.ALTERNATIVE_NEUTRAL_PROFILE_ID,
                    "neutral_variant_sha256": inspected.producer_variant_sha256,
                    "samples_per_axis": samples,
                    "padding": padding,
                    "smooth_k": smooth_k,
                    "source_manifest": {
                        "format": manifest["format"],
                        "sha256": source_manifest_sha256,
                        "candidate_sha256": source_manifest_source["candidate_sha256"],
                        "base_source_sha256": source_manifest_source["source_sha256"],
                        "profile_ids": list(exact_five_publisher.PROFILE_IDS),
                        "selected_profile_id": STANDARD_NEUTRAL_PROFILE_ID,
                    },
                    "source_document": {
                        "document": inspected.source_document,
                        "namespace": inspected.source_namespace,
                        "sha256": inspected.source_sha256,
                    },
                    "producer": {
                        "format": common.PROVISIONAL_FORM_V11_FORMAT,
                        "operation": common.PROVISIONAL_FORM_OPERATION,
                        "source_document": inspected.source_document,
                        "source_namespace": inspected.source_namespace,
                        "envelope_sha256": inspected.producer_envelope_sha256,
                        "variant_id": successor.ALTERNATIVE_NEUTRAL_PROFILE_ID,
                        "variant_sha256": inspected.producer_variant_sha256,
                    },
                    "successor": {
                        "format": successor.ALTERNATIVE_FORMAT,
                        "consumer_id": successor.ALTERNATIVE_CONSUMER_ID,
                        "region_id": successor.ALTERNATIVE_REGION_ID,
                        "config": {
                            "samples_per_axis": samples,
                            "padding": padding,
                            "smooth_k": smooth_k,
                            "capture_padding": successor.DEFAULT_CAPTURE_PADDING,
                        },
                        "implementation_sha256": implementation["identity_sha256"],
                    },
                    "capture": capture,
                    "metrics": metrics,
                    "outputs": output_identities,
                    "surface_sha256": surface_identity["sha256"],
                    "surface_bytes": surface_identity["bytes"],
                    "png_sha256": image_identity["sha256"],
                    "png_bytes": image_identity["bytes"],
                    "implementation": implementation,
                }
                identity["identity_sha256"] = hashlib.sha256(
                    successor._canonical(identity)
                ).hexdigest()
                private_identity_path.write_text(canonical_json(identity), encoding="utf-8", newline="\n")
                identity_file_identity = _output_file_identity(
                    private_identity_path,
                    "neutral rerender identity.json",
                )
                staged_identities = {
                    OUTPUT_PLY_NAME: {
                        "bytes": surface_identity["bytes"],
                        "sha256": surface_identity["sha256"],
                    },
                    OUTPUT_PNG_NAME: {
                        "bytes": image_identity["bytes"],
                        "sha256": image_identity["sha256"],
                    },
                    OUTPUT_IDENTITY_NAME: {
                        "bytes": identity_file_identity["bytes"],
                        "sha256": identity_file_identity["sha256"],
                    },
                }
                staging_name, staging_fd = publication_helpers._create_staging(parent_fd, output_id)
                staging_identity_info = os.fstat(staging_fd)
                staging_identity = (staging_identity_info.st_dev, staging_identity_info.st_ino)
                for name, private_path in (
                    (OUTPUT_PLY_NAME, private_surface_path),
                    (OUTPUT_PNG_NAME, private_png_path),
                    (OUTPUT_IDENTITY_NAME, private_identity_path),
                ):
                    _copy_private_file(
                        private_path,
                        staging_fd,
                        name,
                        staged_identities[name],
                        f"neutral rerender {name}",
                    )
                os.fchmod(staging_fd, 0o755)
                os.fsync(staging_fd)
                _validate_staging_inventory(staging_fd, staging_identity, staged_identities)
                try:
                    publication_helpers._rename_noreplace(
                        parent_fd,
                        staging_name,
                        parent_fd,
                        output_id,
                    )
                except FileExistsError as exc:
                    _fail(f"refusing to overwrite existing destination: {output_id}")
                installed = True
            except NeutralAlternativeRerenderError:
                raise
            except (
                exact_five_publisher.SuccessorAnatomyGalleryError,
                publication_helpers.PublishError,
                successor.SuccessorPreviewError,
                successor._baseline.PreviewError,
                OSError,
                OverflowError,
                ValueError,
                TypeError,
                KeyError,
            ) as exc:
                _fail(str(exc))
    finally:
        if staging_fd is not None:
            if not installed and staging_name is not None and staging_identity is not None:
                _remove_staging(parent_fd, staging_name, staging_fd, staging_identity)
            publication_helpers._close_fd(staging_fd)
        publication_helpers._close_fd(parent_fd)

    output_path = output_parent / output_id
    return {
        "format": OUTPUT_FORMAT,
        "status": "success",
        "id": output_id,
        "output": str(output_path),
        "files": sorted(EXPECTED_OUTPUTS),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-parent", required=True, type=Path, help="existing native-Linux output parent")
    parser.add_argument("--id", dest="output_id", required=True, help="fresh output directory id")
    parser.add_argument("--source-manifest", required=True, type=Path, help="exact-five structural source manifest")
    parser.add_argument("--creature-kernel", type=Path, default=None, help="creature-kernel executable")
    parser.add_argument(
        "--samples-per-axis",
        type=int,
        default=successor.DEFAULT_SAMPLES,
        help=f"alternative sampling resolution ({successor.ALTERNATIVE_MIN_SAMPLES}-{successor.MAX_SAMPLES})",
    )
    parser.add_argument("--padding", type=float, default=successor.DEFAULT_PADDING)
    parser.add_argument("--smooth-k", type=float, default=successor.DEFAULT_SMOOTH_K)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = rerender_neutral_alternative(
            args.output_parent,
            args.output_id,
            args.source_manifest,
            creature_kernel=args.creature_kernel,
            samples=args.samples_per_axis,
            padding=args.padding,
            smooth_k=args.smooth_k,
        )
    except (
        NeutralAlternativeRerenderError,
        exact_five_publisher.SuccessorAnatomyGalleryError,
        publication_helpers.PublishError,
        ValidationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"rerender-neutral-alternative failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

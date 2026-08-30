#!/usr/bin/env python3
"""Publish one disposable four-profile successor-surface anatomy appraisal."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np


VISUAL_REVIEW_ROOT = Path(__file__).resolve().parent
if str(VISUAL_REVIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(VISUAL_REVIEW_ROOT))

import common  # noqa: E402
from common import ValidationError, canonical_json  # noqa: E402
from publish import PublishError, publish_session  # noqa: E402
from publish_provisional_form import (  # noqa: E402
    ORDINARY_SOURCE_BYTES,
    ProvisionalFormPublishError,
    _copy_input_reference,
    _parse_inspection,
    _run_inspection,
    default_creature_kernel,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2] / "experiments" / "current-form-surface-preview"
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import generate_structural_profile_sources as profile_source_generator  # noqa: E402
import successor_surface_preview as successor  # noqa: E402


class SuccessorAnatomyGalleryError(RuntimeError):
    """A bounded, fail-closed successor anatomy-gallery error."""


SOURCE_MANIFEST_FORMAT = "creature-kernel.disposable-structural-profile-source-manifest.v1"
PROFILE_IDS = (
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
NEUTRAL_VARIANT_ID = "neutral-v0"
REVIEW_ID = "successor-surface-anatomy-appraisal"
TITLE = "Disposable successor-surface anatomy appraisal"
DESCRIPTION = (
    "Disposable successor-surface anatomy appraisal for four ordered source profiles; "
    "not structural, pose, or skeleton evidence and not acceptance."
)
INSTRUCTIONS = (
    "Compare the four ordered neutral successor-surface composites for gross anatomy, "
    "silhouette, connected regions, and profile differentiation. This is a disposable "
    "successor-surface anatomy appraisal only; it is not structural, pose, skeleton, "
    "or acceptance evidence, and this gallery records no acceptance decision."
)
EXPECTED_CANVAS = {"width": 1800, "height": 1500, "mode": "RGB"}
EXPECTED_VIEWS = ("front", "side", "three-quarter")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMPLEMENTATION_SOURCE_MAX_BYTES = 4_000_000
PRODUCER_EXECUTABLE_MAX_BYTES = 256_000_000
MIN_GALLERY_SAMPLES = successor.DEFAULT_SAMPLES


@dataclass(frozen=True)
class _ProfileInput:
    profile_id: str
    source_document: str
    source_namespace: str
    source_sha256: str
    form: Any
    descriptors: tuple[Any, ...]
    producer_envelope_sha256: str
    producer_variant_sha256: str


def _fail(message: str) -> None:
    raise SuccessorAnatomyGalleryError(message)


def _hash(value: Any, where: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        _fail(f"{where} must be a lowercase SHA-256 digest")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{where} must be a non-empty string")
    return value


def _read_reference_bytes(reference: common.SourceReference, maximum: int, where: str) -> bytes:
    try:
        with common.open_source_reference(reference, where) as stream:
            size = os.fstat(stream.fileno()).st_size
            if size > maximum:
                _fail(f"{where} exceeds the bounded size")
            data = stream.read(maximum + 1)
    except SuccessorAnatomyGalleryError:
        raise
    except (OSError, ValidationError) as exc:
        _fail(f"{where} cannot be read safely: {exc}")
    if len(data) > maximum:
        _fail(f"{where} exceeds the bounded size")
    return data


def _resolve_file(path: Path, where: str) -> common.SourceReference:
    try:
        absolute = Path(path).absolute()
        return common._resolve_file_reference(str(absolute), absolute, where)
    except (OSError, ValidationError, ValueError) as exc:
        _fail(str(exc))


def _file_identity(path: Path, maximum: int, where: str, *, repository_path: bool) -> dict[str, Any]:
    reference = _resolve_file(path, where)
    try:
        with common.open_source_reference(reference, where) as stream:
            initial_size = os.fstat(stream.fileno()).st_size
            if initial_size > maximum:
                _fail(f"{where} exceeds the bounded size")
            digest = hashlib.sha256()
            size = 0
            while chunk := stream.read(min(1024 * 1024, maximum - size + 1)):
                size += len(chunk)
                if size > maximum:
                    _fail(f"{where} exceeds the bounded size")
                digest.update(chunk)
    except SuccessorAnatomyGalleryError:
        raise
    except (OSError, ValidationError) as exc:
        _fail(f"{where} cannot be read safely: {exc}")
    identity: dict[str, Any] = {
        "bytes": size,
        "sha256": digest.hexdigest(),
    }
    if repository_path:
        repository_root = VISUAL_REVIEW_ROOT.parents[1]
        try:
            identity["repository_path"] = reference.path.relative_to(repository_root).as_posix()
        except ValueError:
            _fail(f"{where} is outside the repository")
    return identity


def _pin_executable(reference: common.SourceReference, temporary_root: Path) -> Path:
    """Copy the validated executable to a private immutable execution path."""

    destination = temporary_root / "creature-kernel"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    source_digest = hashlib.sha256()
    source_bytes = 0
    fd = -1
    try:
        with common.open_source_reference(reference, "creature-kernel executable") as source:
            source_info = os.fstat(source.fileno())
            if not stat.S_ISREG(source_info.st_mode):
                _fail("creature-kernel executable is not a regular file")
            if source_info.st_size > PRODUCER_EXECUTABLE_MAX_BYTES:
                _fail("creature-kernel executable exceeds the bounded size")
            fd = os.open(destination, flags, 0o700)
            with os.fdopen(fd, "wb") as output:
                fd = -1
                while True:
                    chunk = source.read(min(1024 * 1024, PRODUCER_EXECUTABLE_MAX_BYTES - source_bytes + 1))
                    if not chunk:
                        break
                    source_bytes += len(chunk)
                    if source_bytes > PRODUCER_EXECUTABLE_MAX_BYTES:
                        _fail("creature-kernel executable exceeds the bounded size")
                    source_digest.update(chunk)
                    output.write(chunk)
                if os.fstat(source.fileno()).st_size != source_bytes:
                    _fail("creature-kernel executable changed while being pinned")
                os.fchmod(output.fileno(), 0o700)
                output.flush()
                os.fsync(output.fileno())
    except SuccessorAnatomyGalleryError:
        if fd >= 0:
            os.close(fd)
        try:
            destination.unlink()
        except OSError:
            pass
        raise
    except (OSError, ValidationError) as exc:
        if fd >= 0:
            os.close(fd)
        try:
            destination.unlink()
        except OSError:
            pass
        _fail(f"could not pin creature-kernel executable: {exc}")

    pinned_reference = _resolve_file(destination, "pinned creature-kernel executable")
    pinned_digest = hashlib.sha256()
    pinned_bytes = 0
    try:
        with common.open_source_reference(pinned_reference, "pinned creature-kernel executable") as pinned:
            pinned_info = os.fstat(pinned.fileno())
            if stat.S_IMODE(pinned_info.st_mode) != 0o700:
                _fail("pinned creature-kernel executable does not have mode 0700")
            if pinned_info.st_size > PRODUCER_EXECUTABLE_MAX_BYTES:
                _fail("pinned creature-kernel executable exceeds the bounded size")
            while chunk := pinned.read(1024 * 1024):
                pinned_bytes += len(chunk)
                if pinned_bytes > PRODUCER_EXECUTABLE_MAX_BYTES:
                    _fail("pinned creature-kernel executable exceeds the bounded size")
                pinned_digest.update(chunk)
    except SuccessorAnatomyGalleryError:
        raise
    except (OSError, ValidationError) as exc:
        _fail(f"could not verify pinned creature-kernel executable: {exc}")
    if pinned_bytes != source_bytes or pinned_digest.digest() != source_digest.digest():
        _fail("pinned creature-kernel executable failed digest/size verification")
    return pinned_reference.path


def _implementation_identity(executable: Path) -> dict[str, Any]:
    files = {
        "adapter": _file_identity(
            Path(__file__), IMPLEMENTATION_SOURCE_MAX_BYTES, "anatomy-gallery adapter source", repository_path=True
        ),
        "successor": _file_identity(
            Path(successor.__file__), IMPLEMENTATION_SOURCE_MAX_BYTES, "successor implementation source", repository_path=True
        ),
        "renderer": _file_identity(
            Path(successor._baseline.__file__), IMPLEMENTATION_SOURCE_MAX_BYTES, "successor renderer source", repository_path=True
        ),
        "producer_executable": _file_identity(
            executable, PRODUCER_EXECUTABLE_MAX_BYTES, "creature-kernel executable", repository_path=False
        ),
    }
    return {
        "files": files,
        "identity_sha256": hashlib.sha256(successor._canonical(files)).hexdigest(),
    }


def _decode_json(data: bytes, where: str) -> Any:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{where} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        profile_source_generator._finite(value, where)
        return value
    except SuccessorAnatomyGalleryError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
        TypeError,
        profile_source_generator.ProfileGenerationError,
    ) as exc:
        _fail(f"{where} is not finite UTF-8 JSON: {exc}")


def _require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    return value


def _require_fields(value: dict[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unknown " + ", ".join(extra))
        _fail(f"{where} has invalid fields ({'; '.join(detail)})")


def _read_canonical_json(reference: common.SourceReference, where: str, *, source: bool = False) -> tuple[Any, bytes]:
    data = _read_reference_bytes(reference, profile_source_generator.MAX_JSON_BYTES, where)
    value = _decode_json(data, where)
    try:
        expected = (
            profile_source_generator.canonical_source_bytes(value)
            if source
            else profile_source_generator.canonical_bytes(value)
        )
    except profile_source_generator.ProfileGenerationError as exc:
        _fail(f"{where} is not canonical generated JSON: {exc}")
    if data != expected:
        _fail(f"{where} is not the canonical generated JSON")
    return value, data


def _validate_source_manifest(manifest_path: Path) -> tuple[dict[str, Any], bytes, list[tuple[dict[str, Any], common.SourceReference, dict[str, Any], bytes]]]:
    manifest_ref = _resolve_file(manifest_path, "source manifest")
    if manifest_ref.path.name != "manifest.json":
        _fail("source manifest must be named manifest.json")
    manifest, manifest_bytes = _read_canonical_json(manifest_ref, "source manifest")
    manifest_obj = _require_object(manifest, "source manifest")
    _require_fields(
        manifest_obj,
        {"candidate_format", "format", "profiles", "source"},
        "source manifest",
    )
    if manifest_obj["format"] != SOURCE_MANIFEST_FORMAT:
        _fail(f"source manifest format must be {SOURCE_MANIFEST_FORMAT}")
    if manifest_obj["candidate_format"] != profile_source_generator.FORMAT:
        _fail("source manifest candidate format is invalid")

    source = _require_object(manifest_obj["source"], "source manifest.source")
    _require_fields(source, {"base_document", "base_namespace", "candidate_sha256", "source_sha256"}, "source manifest.source")
    base_document = _text(source["base_document"], "source manifest.source.base_document")
    base_namespace = _text(source["base_namespace"], "source manifest.source.base_namespace")
    candidate_sha256 = _hash(source["candidate_sha256"], "source manifest.source.candidate_sha256")
    base_source_sha256 = _hash(source["source_sha256"], "source manifest.source.source_sha256")

    # The manifest's two upstream identities are checked against the current
    # frozen generator inputs. This is the smallest independent tamper check
    # for a manifest that is otherwise self-authenticating only by content.
    candidate_ref = _resolve_file(profile_source_generator.DEFAULT_CANDIDATE, "checked-in candidate")
    candidate_bytes = _read_reference_bytes(candidate_ref, profile_source_generator.MAX_JSON_BYTES, "checked-in candidate")
    if hashlib.sha256(candidate_bytes).hexdigest() != candidate_sha256:
        _fail("source manifest candidate hash does not match the checked-in candidate table")
    base_source_ref = _resolve_file(profile_source_generator.DEFAULT_SOURCE, "checked-in base source")
    base_source_bytes = _read_reference_bytes(
        base_source_ref, profile_source_generator.MAX_JSON_BYTES, "checked-in base source"
    )
    base_source = _decode_json(base_source_bytes, "checked-in base source")
    if hashlib.sha256(base_source_bytes).hexdigest() != base_source_sha256:
        _fail("source manifest base-source hash does not match the checked-in base source")
    base_source_obj = _require_object(base_source, "checked-in base source")
    base_source_identity = _require_object(base_source_obj.get("source"), "checked-in base source.source")
    if (
        base_source_identity.get("document") != base_document
        or base_source_identity.get("namespace") != base_namespace
    ):
        _fail("source manifest base-source identity does not match the checked-in base source")

    profiles = manifest_obj["profiles"]
    if not isinstance(profiles, list) or len(profiles) != len(PROFILE_IDS):
        _fail("source manifest must contain exactly four profiles")
    if [item.get("id") if isinstance(item, dict) else None for item in profiles] != list(PROFILE_IDS):
        _fail("source manifest profiles are not in the exact required order")

    expected_entries = {"manifest.json", *(f"{profile_id}.json" for profile_id in PROFILE_IDS)}
    try:
        common._reject_symlink_components(manifest_ref.path.parent, "source manifest directory")
        directory_info = manifest_ref.path.parent.lstat()
        entries = list(manifest_ref.path.parent.iterdir())
    except (OSError, ValidationError) as exc:
        _fail(f"source manifest directory cannot be inspected safely: {exc}")
    if not stat.S_ISDIR(directory_info.st_mode):
        _fail("source manifest parent is not a directory")
    if {entry.name for entry in entries} != expected_entries:
        _fail("source manifest directory contains unlisted or missing files")
    for entry in entries:
        try:
            info = entry.lstat()
        except OSError as exc:
            _fail(f"source manifest directory entry cannot be inspected: {exc}")
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            _fail(f"source manifest directory contains an unsafe entry: {entry.name}")

    loaded: list[tuple[dict[str, Any], common.SourceReference, dict[str, Any], bytes]] = []
    for index, raw_profile in enumerate(profiles):
        where = f"source manifest.profiles[{index}]"
        profile = _require_object(raw_profile, where)
        _require_fields(profile, {"bytes", "document", "file", "id", "sha256", "tail_signature"}, where)
        profile_id = profile["id"]
        if profile_id != PROFILE_IDS[index]:
            _fail(f"{where}.id is not in the exact required order")
        expected_document = f"{base_document}__{profile_source_generator.SOURCE_DOCUMENT_SUFFIX}__{profile_id}"
        if profile["document"] != expected_document:
            _fail(f"{where}.document does not bind its profile id")
        file_name = f"{profile_id}.json"
        if not isinstance(profile["file"], str) or profile["file"] != file_name or PurePosixPath(profile["file"]).parts != (file_name,):
            _fail(f"{where}.file is not the canonical profile path")
        byte_count = profile["bytes"]
        if type(byte_count) is not int or byte_count < 0:
            _fail(f"{where}.bytes must be a non-negative integer")
        if byte_count > ORDINARY_SOURCE_BYTES:
            _fail(f"{where}.bytes exceeds the inspect-provisional-form source bound")
        expected_hash = _hash(profile["sha256"], f"{where}.sha256")
        tail_signature = profile["tail_signature"]
        if (
            not isinstance(tail_signature, list)
            or len(tail_signature) != 5
            or any(type(value) is not int for value in tail_signature)
        ):
            _fail(f"{where}.tail_signature is invalid")
        source_ref = _resolve_file(manifest_ref.path.parent / file_name, f"{where}.file")
        source_value, source_bytes = _read_canonical_json(source_ref, f"{where}.file", source=True)
        if len(source_bytes) != byte_count or hashlib.sha256(source_bytes).hexdigest() != expected_hash:
            _fail(f"{where}.file does not match its manifest integrity metadata")
        source_object = _require_object(source_value, f"{where}.file")
        source_identity = _require_object(source_object.get("source"), f"{where}.file.source")
        if source_identity.get("document") != profile["document"] or source_identity.get("namespace") != base_namespace:
            _fail(f"{where}.file source identity does not match its profile record")
        try:
            tail_signature = list(profile_source_generator._tail_signature(source_object))
        except (
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            profile_source_generator.ProfileGenerationError,
        ) as exc:
            _fail(f"{where}.file has an invalid generated source shape: {exc}")
        if profile["tail_signature"] != tail_signature:
            _fail(f"{where}.tail_signature does not match its source document")
        loaded.append((profile, source_ref, source_value, source_bytes))
    return manifest_obj, manifest_bytes, loaded


def _validate_executable(executable: Path) -> common.SourceReference:
    reference = _resolve_file(executable, "creature-kernel executable")
    try:
        if not os.access(reference.path, os.X_OK):
            _fail("creature-kernel executable is not executable")
    except OSError as exc:
        _fail(f"could not inspect creature-kernel executable: {exc}")
    return reference


def _inspect_profile(
    profile: dict[str, Any],
    source_ref: common.SourceReference,
    source_bytes: bytes,
    executable: Path,
    temporary_root: Path,
    expected_namespace: str,
) -> _ProfileInput:
    profile_id = profile["id"]
    input_copy = temporary_root / f"{profile_id}.json"
    try:
        _copy_input_reference(source_ref, input_copy)
        copied = input_copy.read_bytes()
    except (OSError, ProvisionalFormPublishError, ValidationError) as exc:
        _fail(f"could not prepare {profile_id} for independent inspection: {exc}")
    if copied != source_bytes:
        _fail(f"{profile_id} source changed while preparing inspection")
    try:
        stdout, stderr, returncode = _run_inspection(
            [str(executable), "inspect-provisional-form", "--input", str(input_copy)]
        )
    except ProvisionalFormPublishError as exc:
        _fail(f"{profile_id} inspect-provisional-form failed: {exc}")
    if returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()[:240]
        _fail(f"{profile_id} inspect-provisional-form exited with status {returncode}{': ' + detail if detail else ''}")
    try:
        payload = _parse_inspection(stdout)
    except ProvisionalFormPublishError as exc:
        _fail(f"{profile_id} inspect-provisional-form failed: {exc}")
    if payload.get("format") != common.PROVISIONAL_FORM_V11_FORMAT:
        _fail(f"{profile_id} inspect-provisional-form did not produce the current v11 envelope")
    try:
        form = successor._baseline.validate_envelope(payload)
    except (successor.SuccessorPreviewError, ValueError, TypeError, KeyError) as exc:
        _fail(f"{profile_id} producer envelope is not a successor-compatible v11 form: {exc}")
    if form.source.get("document") != profile["document"]:
        _fail(f"{profile_id} producer source document does not match the source manifest")
    if form.source.get("namespace") != expected_namespace:
        _fail(f"{profile_id} producer source namespace does not match the source manifest")
    neutral = [item for item in form.variants if item[0] == NEUTRAL_VARIANT_ID]
    if len(neutral) != 1:
        _fail(f"{profile_id} producer envelope does not contain exactly one neutral-v0 variant")
    _, descriptors, raw_variant = neutral[0]
    if raw_variant.get("profile_id") != NEUTRAL_VARIANT_ID:
        _fail(f"{profile_id} neutral-v0 producer profile identity is invalid")
    producer_envelope_sha256 = hashlib.sha256(successor._canonical(payload)).hexdigest()
    producer_variant_sha256 = hashlib.sha256(successor._canonical(raw_variant)).hexdigest()
    return _ProfileInput(
        profile_id=profile_id,
        source_document=profile["document"],
        source_namespace=expected_namespace,
        source_sha256=profile["sha256"],
        form=form,
        descriptors=descriptors,
        producer_envelope_sha256=producer_envelope_sha256,
        producer_variant_sha256=producer_variant_sha256,
    )


def _shared_capture_bound(profiles: list[_ProfileInput]) -> tuple[Any, tuple[Any, ...]]:
    baseline = successor._baseline
    if tuple(baseline.CANVAS) != (EXPECTED_CANVAS["width"], EXPECTED_CANVAS["height"]):
        _fail("existing renderer canvas no longer has the fixed 1800x1500 format")
    if tuple(item.get("name") for item in baseline._projection_json()) != EXPECTED_VIEWS:
        _fail("existing renderer projections no longer have the fixed front/side/three-quarter order")
    if successor.DEFAULT_CAPTURE_PADDING != baseline.DEFAULT_PADDING:
        _fail("successor capture padding is no longer baseline-compatible")
    prepared: list[tuple[_ProfileInput, Any, tuple[Any, ...]]] = []
    for profile in profiles:
        try:
            guide = baseline._derive_hybrid_guides(profile.form, profile.descriptors)
            baseline._validate_hybrid_guide(guide)
            fields = baseline._compile_hybrid_guide(guide)
        except (baseline.PreviewError, successor.SuccessorPreviewError, ValueError, TypeError, KeyError) as exc:
            _fail(f"{profile.profile_id} could not prepare its successor capture guide: {exc}")
        prepared.append((profile, guide, fields))
    try:
        bounds = baseline._shared_render_bounds(
            tuple(fields for _, _, fields in prepared), successor.DEFAULT_CAPTURE_PADDING
        )
        for _, guide, _ in prepared:
            baseline._validate_hybrid_guide(guide, bounds)
    except (baseline.PreviewError, ValueError, TypeError) as exc:
        _fail(f"could not derive one shared capture bound: {exc}")
    return bounds, tuple(prepared)


def _validated_bound(value: Any, where: str) -> tuple[np.ndarray, np.ndarray]:
    try:
        lower, upper = value
        lower_array = np.asarray(lower, dtype=np.float64)
        upper_array = np.asarray(upper, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} is not a valid three-dimensional bound: {exc}")
    if (
        lower_array.shape != (3,)
        or upper_array.shape != (3,)
        or not np.all(np.isfinite(lower_array))
        or not np.all(np.isfinite(upper_array))
        or np.any(upper_array <= lower_array)
    ):
        _fail(f"{where} is not finite and ordered")
    return lower_array, upper_array


def _capture_bound_with_components(
    baseline_bound: Any,
    built: list[tuple[_ProfileInput, Any, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    """Extend the baseline frame to contain every built render component."""

    lower, upper = _validated_bound(baseline_bound, "baseline shared capture bound")
    component_bounds: list[tuple[str, np.ndarray, np.ndarray]] = []
    for profile, _guide, mesh in built:
        components = getattr(mesh, "render_components", None)
        if type(components) is not tuple or not components:
            _fail(f"{profile.profile_id} successor render components are missing or malformed")
        for index, component in enumerate(components):
            if not hasattr(component, "bounds"):
                _fail(f"{profile.profile_id} render component {index} is missing bounds")
            component_lower, component_upper = _validated_bound(
                component.bounds,
                f"{profile.profile_id} render component {index} bounds",
            )
            component_bounds.append((f"{profile.profile_id} render component {index}", component_lower, component_upper))

    for _where, component_lower, component_upper in component_bounds:
        lower = np.minimum(lower, component_lower)
        upper = np.maximum(upper, component_upper)
    lower, upper = _validated_bound((lower, upper), "corrected shared capture bound")
    for where, component_lower, component_upper in component_bounds:
        if np.any(component_lower < lower) or np.any(component_upper > upper):
            _fail(f"{where} is not contained by the corrected shared capture bound")
    return lower, upper


def _bound_json(bounds: tuple[Any, Any]) -> dict[str, list[float]]:
    lower, upper = _validated_bound(bounds, "shared capture bound")
    result = {
        "min": [float(value) for value in lower],
        "max": [float(value) for value in upper],
    }
    return result


def _image_identity(
    path: Path,
    profile: _ProfileInput,
    capture: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    try:
        info = path.lstat()
        data = path.read_bytes()
    except OSError as exc:
        _fail(f"{profile.profile_id} successor composite cannot be read: {exc}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail(f"{profile.profile_id} successor composite is not a regular file")
    try:
        with successor._baseline.Image.open(path) as image:
            image.load()
            if image.size != (EXPECTED_CANVAS["width"], EXPECTED_CANVAS["height"]) or image.mode != EXPECTED_CANVAS["mode"]:
                _fail(f"{profile.profile_id} successor composite is not the fixed RGB 1800x1500 capture")
    except SuccessorAnatomyGalleryError:
        raise
    except Exception as exc:
        _fail(f"{profile.profile_id} successor composite is not a readable PNG: {exc}")
    identity = {
        "profile_id": profile.profile_id,
        "source_document_sha256": profile.source_sha256,
        "producer_envelope_sha256": profile.producer_envelope_sha256,
        "producer_variant_sha256": profile.producer_variant_sha256,
        "successor_format": successor.FORMAT,
        "consumer_id": successor.CONSUMER_ID,
        "successor_region_id": successor.SUCCESSOR_REGION_ID,
        "implementation_sha256": implementation["identity_sha256"],
        "capture": capture,
    }
    identity_sha256 = hashlib.sha256(successor._canonical(identity)).hexdigest()
    return {
        "kind": "successor-skin-composite-png",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "identity_sha256": identity_sha256,
    }


def _build_review_manifest(
    profiles: list[_ProfileInput],
    source_manifest: dict[str, Any],
    source_manifest_sha256: str,
    implementation: dict[str, Any],
    temporary_root: Path,
    *,
    samples: int,
    padding: float,
    smooth_k: float,
    review_id: str,
    title: str,
) -> tuple[Path, dict[str, dict[str, int | str]]]:
    if type(samples) is not int or samples < MIN_GALLERY_SAMPLES or samples > successor.MAX_SAMPLES:
        _fail(f"samples-per-axis must be between {MIN_GALLERY_SAMPLES} and {successor.MAX_SAMPLES} for this four-profile gallery")
    if not math.isfinite(float(padding)) or padding < 0.0 or not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("successor sampling configuration is invalid")
    baseline_capture_bound, prepared = _shared_capture_bound(profiles)
    built: list[tuple[_ProfileInput, Any, Any]] = []
    for profile, guide, _ in prepared:
        try:
            mesh = successor.build_variant(
                profile.form,
                profile.descriptors,
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
            _fail(f"{profile.profile_id} successor surface build failed: {exc}")
        built.append((profile, guide, mesh))
    capture_bound = _capture_bound_with_components(baseline_capture_bound, built)
    for profile, guide, _mesh in built:
        try:
            successor._baseline._validate_hybrid_guide(guide, capture_bound)
        except (successor._baseline.PreviewError, ValueError, TypeError, KeyError) as exc:
            _fail(f"{profile.profile_id} cannot use the corrected shared capture bound: {exc}")
    capture_bound_json = _bound_json(capture_bound)
    capture = {
        "canvas": dict(EXPECTED_CANVAS),
        "views": list(EXPECTED_VIEWS),
        "global_capture_bound": capture_bound_json,
    }
    images: list[dict[str, Any]] = []
    expected_sources: dict[str, dict[str, int | str]] = {}
    for profile, guide, mesh in built:
        try:
            png = temporary_root / f"{profile.profile_id}.png"
            successor._baseline._render(
                png,
                mesh.vertices,
                mesh.faces,
                profile.profile_id,
                guide=guide,
                bounds=capture_bound,
                render_components=mesh.render_components,
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
            _fail(f"{profile.profile_id} successor surface/capture failed: {exc}")
        item_capture = {
            **capture,
            "successor_config": {
                "samples_per_axis": samples,
                "padding": padding,
                "smooth_k": smooth_k,
                "capture_padding": successor.DEFAULT_CAPTURE_PADDING,
            },
        }
        output_identity = _image_identity(png, profile, item_capture, implementation)
        expected_sources[profile.profile_id] = {
            "bytes": output_identity["bytes"],
            "sha256": output_identity["sha256"],
        }
        item_metadata = {
            "profile_id": profile.profile_id,
            "source_binding": {
                "document": profile.source_document,
                "namespace": profile.source_namespace,
                "profile_id": profile.profile_id,
                "mode": "identifier-only; v11 does not prove the exact source bytes consumed",
            },
            "source_hashes": {
                "source_document_sha256": profile.source_sha256,
                "producer_envelope_sha256": profile.producer_envelope_sha256,
                "producer_variant_sha256": profile.producer_variant_sha256,
            },
            "source_manifest_sha256": source_manifest_sha256,
            "producer": {
                "format": common.PROVISIONAL_FORM_V11_FORMAT,
                "operation": common.PROVISIONAL_FORM_OPERATION,
                "source_binding": {
                    "document": profile.source_document,
                    "namespace": profile.source_namespace,
                    "profile_id": profile.profile_id,
                    "mode": "identifier-only",
                },
                "variant_id": NEUTRAL_VARIANT_ID,
                "profile_id": NEUTRAL_VARIANT_ID,
                "envelope_sha256": profile.producer_envelope_sha256,
                "variant_sha256": profile.producer_variant_sha256,
            },
            "successor": {
                "format": successor.FORMAT,
                "consumer_id": successor.CONSUMER_ID,
                "region_id": successor.SUCCESSOR_REGION_ID,
                "config": item_capture["successor_config"],
                "implementation_sha256": implementation["identity_sha256"],
            },
            "capture": capture,
            "output_identity": output_identity,
        }
        images.append({
            "id": profile.profile_id,
            "title": profile.profile_id,
            "source": str(png),
            "description": "Neutral successor-skin composite with fixed front, side, and three-quarter views.",
            "metadata": item_metadata,
        })

    if [item["id"] for item in images] != list(PROFILE_IDS):
        _fail("successor anatomy image items are not in the exact profile order")
    if len({item["metadata"]["source_hashes"]["source_document_sha256"] for item in images}) != len(PROFILE_IDS):
        _fail("successor anatomy items reuse a producer source-document lineage")
    if len({item["metadata"]["producer"]["envelope_sha256"] for item in images}) != len(PROFILE_IDS):
        _fail("successor anatomy items reuse a producer envelope lineage")
    if len({item["metadata"]["producer"]["variant_sha256"] for item in images}) != len(PROFILE_IDS):
        _fail("successor anatomy items reuse a producer variant lineage")
    if len({item["metadata"]["output_identity"]["sha256"] for item in images}) != len(PROFILE_IDS):
        _fail("successor anatomy items reuse one rendered asset")

    descriptor_snapshot = {
        "adapter_format": "creature-kernel.disposable-successor-anatomy-gallery.v1",
        "source_manifest": {
            "format": source_manifest["format"],
            "sha256": source_manifest_sha256,
            "candidate_sha256": source_manifest["source"]["candidate_sha256"],
            "base_source_sha256": source_manifest["source"]["source_sha256"],
            "profile_ids": list(PROFILE_IDS),
        },
        "producer": {
            "format": common.PROVISIONAL_FORM_V11_FORMAT,
            "operation": common.PROVISIONAL_FORM_OPERATION,
            "selected_variant": NEUTRAL_VARIANT_ID,
            "source_binding": [item["metadata"]["producer"]["source_binding"] for item in images],
            "source_binding_mode": "identifier-only; v11 does not prove the exact source bytes consumed",
            "exact_source_document_sha256_by_profile": [
                item["metadata"]["source_hashes"]["source_document_sha256"] for item in images
            ],
            "envelope_sha256_by_profile": [item["metadata"]["producer"]["envelope_sha256"] for item in images],
            "variant_sha256_by_profile": [item["metadata"]["producer"]["variant_sha256"] for item in images],
        },
        "successor": {
            "format": successor.FORMAT,
            "consumer_id": successor.CONSUMER_ID,
            "region_id": successor.SUCCESSOR_REGION_ID,
            "config": {
                "samples_per_axis": samples,
                "padding": padding,
                "smooth_k": smooth_k,
                "capture_padding": successor.DEFAULT_CAPTURE_PADDING,
            },
        },
        "implementation": implementation,
        "capture": capture,
        "output_identity_sha256_by_profile": [item["metadata"]["output_identity"]["identity_sha256"] for item in images],
    }
    review = {
        "schema_version": 1,
        "id": review_id,
        "title": title,
        "description": DESCRIPTION,
        "instructions": INSTRUCTIONS,
        "subject_context": {"descriptor_snapshot": descriptor_snapshot},
        "kind": "image",
        "groups": [{
            "id": "successor-anatomy",
            "title": "Four ordered source profiles",
            "selection_mode": "none",
            "items": images,
        }],
    }
    manifest_path = temporary_root / "review-manifest.json"
    try:
        manifest_path.write_text(canonical_json(review), encoding="utf-8", newline="\n")
    except OSError as exc:
        _fail(f"could not write temporary review manifest: {exc}")
    return manifest_path, expected_sources


def publish_successor_anatomy_gallery(
    reviews_root: Path,
    source_manifest: Path,
    *,
    creature_kernel: Path | None = None,
    samples: int = successor.DEFAULT_SAMPLES,
    padding: float = successor.DEFAULT_PADDING,
    smooth_k: float = successor.DEFAULT_SMOOTH_K,
    review_id: str = REVIEW_ID,
    title: str = TITLE,
) -> dict[str, Any]:
    try:
        review_id = common.validate_id(review_id, "review id")
    except ValidationError as exc:
        _fail(str(exc))
    if title != TITLE:
        _fail("review title is fixed so the anatomy-only appraisal boundary remains explicit")
    manifest, manifest_bytes, records = _validate_source_manifest(source_manifest)
    executable_reference = _validate_executable(creature_kernel or default_creature_kernel())
    source_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    with tempfile.TemporaryDirectory(prefix="ck-successor-anatomy-gallery-") as temporary:
        temporary_root = Path(temporary)
        executable = _pin_executable(executable_reference, temporary_root)
        implementation = _implementation_identity(executable)
        profiles = [
            _inspect_profile(
                profile,
                source_ref,
                source_bytes,
                executable,
                temporary_root,
                manifest["source"]["base_namespace"],
            )
            for profile, source_ref, _source_value, source_bytes in records
        ]
        if [profile.profile_id for profile in profiles] != list(PROFILE_IDS):
            _fail("inspected profiles are not in the exact required order")
        if len({profile.source_sha256 for profile in profiles}) != len(PROFILE_IDS):
            _fail("profile source documents are not distinct")
        review_manifest, expected_sources = _build_review_manifest(
            profiles,
            manifest,
            source_manifest_sha256,
            implementation,
            temporary_root,
            samples=samples,
            padding=padding,
            smooth_k=smooth_k,
            review_id=review_id,
            title=title,
        )
        try:
            summary = publish_session(
                reviews_root,
                review_manifest,
                expected_sources=expected_sources,
            )
        except (ValidationError, PublishError, OSError) as exc:
            _fail(f"could not publish successor anatomy review: {exc}")
    return {**summary, "kind": "successor-anatomy-gallery", "profiles": len(PROFILE_IDS), "images": len(PROFILE_IDS)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing or creatable visual-review root")
    parser.add_argument("--source-manifest", required=True, type=Path, help="manifest.json from generate_structural_profile_sources.py")
    parser.add_argument("--creature-kernel", type=Path, default=None, help="creature-kernel executable (default: repository target/debug/creature-kernel)")
    parser.add_argument(
        "--samples-per-axis",
        type=int,
        default=successor.DEFAULT_SAMPLES,
        help=f"sampling resolution ({MIN_GALLERY_SAMPLES}-{successor.MAX_SAMPLES}; default: {successor.DEFAULT_SAMPLES})",
    )
    parser.add_argument("--padding", type=float, default=successor.DEFAULT_PADDING)
    parser.add_argument("--smooth-k", type=float, default=successor.DEFAULT_SMOOTH_K)
    parser.add_argument("--id", dest="review_id", default=REVIEW_ID)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_successor_anatomy_gallery(
            args.root,
            args.source_manifest,
            creature_kernel=args.creature_kernel,
            samples=args.samples_per_axis,
            padding=args.padding,
            smooth_k=args.smooth_k,
            review_id=args.review_id,
        )
    except (SuccessorAnatomyGalleryError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-successor-anatomy-gallery failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

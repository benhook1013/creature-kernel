"""Shared validation and filesystem helpers for the local visual-review tool.

The review tool intentionally keeps its on-disk format small and boring.  This
module is used by both the publisher and the HTTP server so that a session
accepted by one is the same session understood by the other.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_JSON_BYTES = 4 * 1024 * 1024
# Structural inspection output is intentionally bounded independently of the
# session JSON limit.  This is large enough for the current source-preserving
# graph projection while preventing a manifest from turning the gallery into
# an unbounded JSON transport.
MAX_STRUCTURE_JSON_BYTES = 256 * 1024
MAX_STRING = 8192
# Subject-context carriers may use the larger exact-carrier budget; ordinary
# metadata strings and objects remain bounded by MAX_STRING.
MAX_CONTEXT_JSON = 12 * 1024
STRUCTURE_FORMAT = "creature-kernel.provisional-structural-inspection.v1"
PREPARED_SOURCE_FORMAT = "creature-kernel.provisional-source-preparation-inspection.v1"
PREPARED_SOURCE_OPERATION = "inspect-prepared-source"
PREPARED_SOURCE_STAGE = "source-preparation"
PROVISIONAL_FORM_LEGACY_FORMAT = "creature-kernel.provisional-form-preview.v1"
PROVISIONAL_FORM_V2_FORMAT = "creature-kernel.provisional-form-preview.v2"
PROVISIONAL_FORM_V3_FORMAT = "creature-kernel.provisional-form-preview.v3"
# Retained so previously published records remain readable.  V5 through v8 are
# explicit historical producer contracts; v11 is the current publication
# contract.  Keep the current alias separate from the historical v7 contract so
# changing the current producer cannot change v7's shape or capsule semantics.
PROVISIONAL_FORM_HISTORICAL_V4_FORMAT = "creature-kernel.provisional-form-preview.v4"
PROVISIONAL_FORM_HISTORICAL_V5_FORMAT = "creature-kernel.provisional-form-preview.v5"
PROVISIONAL_FORM_HISTORICAL_V6_FORMAT = "creature-kernel.provisional-form-preview.v6"
PROVISIONAL_FORM_V6_FORMAT = PROVISIONAL_FORM_HISTORICAL_V6_FORMAT
PROVISIONAL_FORM_V7_FORMAT = "creature-kernel.provisional-form-preview.v7"
PROVISIONAL_FORM_V8_FORMAT = "creature-kernel.provisional-form-preview.v8"
PROVISIONAL_FORM_V9_FORMAT = "creature-kernel.provisional-form-preview.v9"
PROVISIONAL_FORM_V10_FORMAT = "creature-kernel.provisional-form-preview.v10"
PROVISIONAL_FORM_V11_FORMAT = "creature-kernel.provisional-form-preview.v11"
PROVISIONAL_FORM_FORMAT = PROVISIONAL_FORM_V11_FORMAT
PROVISIONAL_FORM_TORSO_PROFILE_FORMAT = (
    "creature-kernel.provisional-form-torso-profile.v1"
)
PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT = (
    "creature-kernel.provisional-form-head-neck-profile.v1"
)
PROVISIONAL_FORM_ARM_PROFILE_FORMAT = "creature-kernel.provisional-form-arm-profile.v1"
PROVISIONAL_FORM_LEG_PROFILE_FORMAT = "creature-kernel.provisional-form-leg-profile.v1"
PROVISIONAL_FORM_FOOT_PROFILE_FORMAT = "creature-kernel.provisional-form-foot-profile.v1"
PROVISIONAL_FORM_CORRECTED_FORMATS = {
    PROVISIONAL_FORM_V2_FORMAT,
    PROVISIONAL_FORM_V3_FORMAT,
    PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
    PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
    PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
    PROVISIONAL_FORM_V7_FORMAT,
    PROVISIONAL_FORM_V8_FORMAT,
    PROVISIONAL_FORM_V9_FORMAT,
    PROVISIONAL_FORM_V10_FORMAT,
    PROVISIONAL_FORM_V11_FORMAT,
}
PROVISIONAL_FORM_FORMATS = {
    PROVISIONAL_FORM_LEGACY_FORMAT,
    *PROVISIONAL_FORM_CORRECTED_FORMATS,
}
PROVISIONAL_FORM_OPERATION = "inspect-provisional-form"
PROVISIONAL_FORM_STAGE = "provisional-form"
PROVISIONAL_FORM_VARIANT_IDS = (
    "neutral-v0",
    "broad-soft-v0",
    "lean-readable-v0",
    "depth-forward-v0",
)
PROVISIONAL_FORM_PROVENANCE = "profile-derived-display"
PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE = "source-authored"
PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE = "source-authored"
PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE = "form_shoulder_control"
PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES = (
    "form_shoulder_peak",
    "form_axilla",
)
PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE = "form_torso_profile_control"
PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES = (
    "lower-pelvis",
    "upper-pelvis",
    "lower-abdomen",
    "waist-abdomen",
    "upper-abdomen",
    "lower-ribcage",
    "upper-ribcage-shoulder",
)
PROVISIONAL_FORM_TORSO_PROFILE_OWNER_ROLES = (
    "pelvis",
    "pelvis",
    "torso",
    "torso",
    "torso",
    "torso",
    "torso",
)
PROVISIONAL_FORM_TORSO_PROFILE_RADIUS_AXES = (
    ("lateral", "lateral_radius"),
    ("anterior", "anterior_radius"),
    ("posterior", "posterior_radius"),
)
PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE = "form_head_neck_profile_control"
PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES = (
    "neck-collar",
    "neck-upper",
    "head-base",
    "cranium-mid",
    "cranium-crown",
    "muzzle-root",
    "muzzle-mid",
    "muzzle-tip",
)
PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES = (
    "neck",
    "neck",
    "head",
    "head",
    "head",
    "head",
    "head",
    "head",
)
PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES = (
    ("lateral", "lateral_radius"),
    ("up", "up_radius"),
    ("forward", "forward_radius"),
)
PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES = ("left", "right")
PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES = (
    "upper-arm-start",
    "upper-arm-midpoint",
    "elbow",
    "forearm-midpoint",
    "forearm-distal",
)
PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES = (
    "upper_arm",
    "upper_arm",
    "upper_arm",
    "forearm",
    "forearm",
)
PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES = (
    ("lateral", "lateral_radius"),
    ("up", "up_radius"),
    ("forward", "forward_radius"),
)
PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE = "form_arm_profile_control"
PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES = ("left", "right")
PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES = (
    "thigh-start",
    "thigh-midpoint",
    "knee",
    "shin-midpoint",
    "hock-endpoint",
)
PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES = (
    "thigh",
    "thigh",
    "thigh",
    "shin",
    "shin",
)
PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES = (
    ("lateral", "lateral_radius"),
    ("up", "up_radius"),
    ("forward", "forward_radius"),
)
PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE = "form_leg_profile_control"
PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES = ("left", "right")
PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES = ("pad", "toe")
PROVISIONAL_FORM_FOOT_PROFILE_OWNER_ROLES = ("foot", "foot")
PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES = (
    ("lateral", "lateral_radius"),
    ("up", "up_radius"),
    ("forward", "forward_radius"),
)
PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE = "form_foot_profile_control"
PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX = 4
PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN = -1.0
PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX = 0.0
PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN = 0.0
PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX = 1.0
PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS = (
    ("neck-collar-to-neck-upper", 0, 1, "vertical-neck-cranium"),
    ("neck-upper-to-head-base", 1, 2, "vertical-neck-cranium"),
    ("head-base-to-cranium-mid", 2, 3, "vertical-neck-cranium"),
    ("cranium-mid-to-cranium-crown", 3, 4, "vertical-neck-cranium"),
    ("cranium-mid-to-muzzle-root", 3, 5, "forward-muzzle"),
    ("muzzle-root-to-muzzle-mid", 5, 6, "forward-muzzle"),
    ("muzzle-mid-to-muzzle-tip", 6, 7, "forward-muzzle"),
)
PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND = 1.0
PROVISIONAL_FORM_LEG_PROFILE_Y_MIN = -PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND
PROVISIONAL_FORM_LEG_PROFILE_Y_MAX = 0.0
PROVISIONAL_FORM_SHAPE_BASIS = (
    "source-authored-dimensions-plus-fixed-display-factor"
)
PROVISIONAL_FORM_RESOURCE_PROFILE = "ck.resource.body.r2"
PROVISIONAL_FORM_SHAPES = {"ellipsoid", "capsule", "tapered-segment"}
PROVISIONAL_FORM_ROLE_SHAPES = {
    "pelvis": "ellipsoid",
    "torso": "ellipsoid",
    "neck": "ellipsoid",
    "head": "ellipsoid",
    "hand": "ellipsoid",
    "foot": "ellipsoid",
    "upper_arm": "capsule",
    "forearm": "capsule",
    "thigh": "capsule",
    "shin": "capsule",
    "tail_root": "tapered-segment",
    "tail_tip": "tapered-segment",
}
# Corrected capsules are display volumes for a body *segment*, so their distal
# endpoint is the direct semantic child anchor. Keep the role relationship
# explicit: inferring a segment from an arbitrary child would make a branching
# body silently choose the wrong part.
PROVISIONAL_FORM_CAPSULE_CHILD_ROLES = {
    "upper_arm": "forearm",
    "forearm": "hand",
    "thigh": "shin",
    "shin": "foot",
}
PROVISIONAL_FORM_V4_CAPSULE_CHILD_ROLES = {
    **PROVISIONAL_FORM_CAPSULE_CHILD_ROLES,
    "neck": "head",
}
# These sets are intentionally explicit.  V8 currently emits the same neck
# capsule projection as v7, but the v7 historical contract must not acquire or
# lose semantics merely because PROVISIONAL_FORM_FORMAT advances.
PROVISIONAL_FORM_V7_NECK_CAPSULE_FORMATS = {
    PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
    PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
    PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
    PROVISIONAL_FORM_V7_FORMAT,
}
PROVISIONAL_FORM_V8_NECK_CAPSULE_FORMATS = {PROVISIONAL_FORM_V8_FORMAT}
PROVISIONAL_FORM_V9_NECK_CAPSULE_FORMATS = {PROVISIONAL_FORM_V9_FORMAT}
PROVISIONAL_FORM_V10_NECK_CAPSULE_FORMATS = {PROVISIONAL_FORM_V10_FORMAT}
PROVISIONAL_FORM_V11_NECK_CAPSULE_FORMATS = {PROVISIONAL_FORM_V11_FORMAT}
PROVISIONAL_FORM_V7_CAPSULE_CHILD_ROLES = PROVISIONAL_FORM_V4_CAPSULE_CHILD_ROLES
PROVISIONAL_FORM_V8_CAPSULE_CHILD_ROLES = {
    **PROVISIONAL_FORM_CAPSULE_CHILD_ROLES,
    "neck": "head",
}
PROVISIONAL_FORM_V10_CAPSULE_CHILD_ROLES = PROVISIONAL_FORM_V8_CAPSULE_CHILD_ROLES
PROVISIONAL_FORM_V11_CAPSULE_CHILD_ROLES = PROVISIONAL_FORM_V8_CAPSULE_CHILD_ROLES
PROVISIONAL_FORM_MAX_DESCRIPTORS = 64
PROVISIONAL_FORM_MAX_PERMILLE = 5000
EXACT_PLACEMENT_PREVIEW_FORMAT = (
    "creature-kernel.provisional-exact-placement-preview.v1"
)
EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE = "ck.preview.exact-placement-unavailable"
EXACT_PLACEMENT_PREVIEW_SOURCES = {
    "authored-root",
    "authored-containment",
    "authored-attachment",
}
SIGNED_I64_MIN = -(1 << 63)
SIGNED_I64_MAX = (1 << 63) - 1
PROVISIONAL_FORM_MAX_SQUARED_LENGTH = 3 * SIGNED_I64_MAX * SIGNED_I64_MAX
ADDRESS_COMPONENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ADDRESS_COMPONENT_MAX_BYTES = 16_384
ADDRESS_MAX_ANCHORS = 4_096
PREVIEW_ADDRESS_FIELDS = {"namespace", "anchors", "kind", "role"}
PreviewAddressKey = tuple[str, tuple[str, ...], str, str]
# Short aliases mirror STRUCTURE_FORMAT for callers that handle the two
# structure-session projection formats generically.
PREPARED_FORMAT = PREPARED_SOURCE_FORMAT
PREPARED_OPERATION = PREPARED_SOURCE_OPERATION
PREPARED_STAGE = PREPARED_SOURCE_STAGE
STRUCTURE_STATUSES = {
    "success",
    "invalid-source",
    "unsupported",
    "resource-limit",
    "internal-failure",
    "input-failure",
    "usage-error",
}
_HAS_DIR_FD_OPEN = os.open in getattr(os, "supports_dir_fd", set())
_HAS_DIR_FD_MKDIR = os.mkdir in getattr(os, "supports_dir_fd", set())
_HAS_DIR_FD_RENAME = os.rename in getattr(os, "supports_dir_fd", set())
_HAS_DIR_FD_UNLINK = os.unlink in getattr(os, "supports_dir_fd", set())
_HAS_DIR_FD_RMDIR = os.rmdir in getattr(os, "supports_dir_fd", set())


class ValidationError(ValueError):
    """A concise user-facing validation error."""


@dataclass(frozen=True)
class SourceReference:
    """A validated source path plus the identity observed during validation."""

    path: Path
    device: int
    inode: int


def require_secure_fs_support() -> None:
    """Fail closed when the descriptor-relative security primitives are absent."""

    required = (
        hasattr(os, "O_NOFOLLOW"),
        hasattr(os, "O_DIRECTORY"),
        _HAS_DIR_FD_OPEN,
        _HAS_DIR_FD_MKDIR,
        _HAS_DIR_FD_RENAME,
        _HAS_DIR_FD_UNLINK,
        _HAS_DIR_FD_RMDIR,
    )
    if os.name != "posix" or not all(required):
        raise ValidationError(
            "secure visual-review filesystem access requires POSIX openat/no-follow support"
        )


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON number {value}")


def read_json(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> Any:
    """Read one UTF-8 JSON object while bounding the amount read."""

    try:
        if path.is_symlink():
            raise ValidationError(f"symlink is not allowed: {path.name}")
        size = path.stat().st_size
        if size > max_bytes:
            raise ValidationError(f"JSON file is larger than {max_bytes} bytes")
        raw = path.read_bytes()
    except ValidationError:
        raise
    except (OSError, ValueError) as exc:
        raise ValidationError(f"cannot read {path.name}: {exc}") from exc
    try:
        return json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValidationError(f"invalid JSON in {path.name}: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{where} must be an object")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{where} must be an array")
    return value


def _string(value: Any, where: str, *, max_len: int = MAX_STRING) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{where} must be a non-empty string")
    if len(value) > max_len:
        raise ValidationError(f"{where} is too long")
    return value


def _optional_string(obj: dict[str, Any], key: str, where: str) -> str | None:
    if key not in obj or obj[key] is None:
        return None
    return _string(obj[key], f"{where}.{key}")


def validate_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValidationError(
            f"{where} must be a safe slug (lowercase letters, numbers, '_' or '-')"
        )
    return value


def _check_fields(obj: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ValidationError(f"{where} has unknown field(s): {', '.join(unknown)}")


def _metadata(value: Any, where: str, *, max_len: int = MAX_STRING) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{where} must be an object")
    # JSON data is retained as metadata and displayed with textContent by the
    # client.  Reject non-finite numbers and excessively deep/large values in
    # practical cases without imposing a domain-specific metadata vocabulary.
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{where} is not JSON-compatible: {exc}") from exc
    if len(encoded.encode("utf-8")) > max_len:
        raise ValidationError(f"{where} is too large")
    return value


def _subject_context(value: Any, where: str) -> dict[str, Any]:
    context = _object(value, where)
    _check_fields(context, {"authored_summary", "descriptor_snapshot", "provenance"}, where)
    if not context:
        raise ValidationError(f"{where} must contain at least one field")
    result: dict[str, Any] = {}
    if "authored_summary" in context:
        summary = _object(context["authored_summary"], f"{where}.authored_summary")
        _check_fields(summary, {"text", "unknowns"}, f"{where}.authored_summary")
        out_summary: dict[str, Any] = {
            "text": _string(summary.get("text"), f"{where}.authored_summary.text")
        }
        if "unknowns" in summary:
            unknowns = _array(summary["unknowns"], f"{where}.authored_summary.unknowns")
            out_summary["unknowns"] = [
                _string(item, f"{where}.authored_summary.unknowns[{index}]")
                for index, item in enumerate(unknowns)
            ]
        result["authored_summary"] = out_summary
    for key in ("descriptor_snapshot", "provenance"):
        if key in context:
            result[key] = _metadata(
                context[key],
                f"{where}.{key}",
                max_len=MAX_CONTEXT_JSON if key == "descriptor_snapshot" else MAX_STRING,
            )
    try:
        encoded = json.dumps(result, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{where} is not JSON-compatible: {exc}") from exc
    if len(encoded.encode("utf-8")) > MAX_CONTEXT_JSON:
        raise ValidationError(f"{where} is too large")
    return result


def _check_no_traversal(raw: str, where: str) -> None:
    if "\x00" in raw or "\\" in raw:
        raise ValidationError(f"{where} contains an invalid path character")
    # Reject traversal lexically, including it in an absolute path.  This is
    # intentionally stricter than resolving and checking a prefix.
    if ".." in Path(raw).parts:
        raise ValidationError(f"{where} contains traversal")


def _reject_symlink_components(path: Path, where: str) -> None:
    current = path
    while True:
        try:
            if current.is_symlink():
                raise ValidationError(f"{where} may not use symlinks")
        except OSError as exc:
            raise ValidationError(f"cannot inspect {where}: {exc}") from exc
        parent = current.parent
        if parent == current:
            break
        current = parent


def resolve_source_reference(source: str, manifest_path: Path, where: str) -> SourceReference:
    """Resolve a manifest source, refusing traversal, symlinks and non-files."""

    _check_no_traversal(source, where)
    raw = Path(source)
    candidate = raw if raw.is_absolute() else manifest_path.parent / raw
    _reject_symlink_components(candidate, where)
    try:
        info = candidate.stat()
    except OSError as exc:
        raise ValidationError(f"{where} does not exist or cannot be read") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ValidationError(f"{where} must refer to a regular file")
    extension = candidate.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f"{where} has unsupported image type; use PNG, JPEG, WebP or GIF"
        )
    return SourceReference(candidate, info.st_dev, info.st_ino)


def resolve_source(source: str, manifest_path: Path, where: str) -> Path:
    """Compatibility wrapper returning only the validated source path."""

    return resolve_source_reference(source, manifest_path, where).path


def open_source_reference(source: SourceReference, where: str) -> Any:
    """Open the validated source without following a replacement symlink."""

    if not hasattr(os, "O_NOFOLLOW"):
        raise ValidationError("secure source publication requires no-follow support")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = None
    try:
        fd = os.open(source.path, flags)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != (source.device, source.inode):
            os.close(fd)
            fd = None
            raise ValidationError(f"{where} changed while publishing")
        stream = os.fdopen(fd, "rb")
        fd = None
        return stream
    except ValidationError:
        if fd is not None:
            os.close(fd)
        raise
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise ValidationError(f"{where} is unavailable or changed while publishing") from exc


def read_source_json(source: SourceReference, where: str, *, max_bytes: int) -> Any:
    """Read bounded JSON through the already-validated source descriptor."""

    with open_source_reference(source, where) as stream:
        try:
            size = os.fstat(stream.fileno()).st_size
            if size > max_bytes:
                raise ValidationError(f"{where} is larger than {max_bytes} bytes")
            raw = stream.read(max_bytes + 1)
        except ValidationError:
            raise
        except OSError as exc:
            raise ValidationError(f"cannot read {where}: {exc}") from exc
    if len(raw) > max_bytes:
        raise ValidationError(f"{where} is larger than {max_bytes} bytes")
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValidationError(f"invalid JSON in {where}: {exc}") from exc


def _resolve_file_reference(source: str, manifest_path: Path, where: str) -> SourceReference:
    """Resolve a bounded local JSON source using image-source safety checks."""

    _check_no_traversal(source, where)
    raw = Path(source)
    candidate = raw if raw.is_absolute() else manifest_path.parent / raw
    _reject_symlink_components(candidate, where)
    try:
        info = candidate.stat()
    except OSError as exc:
        raise ValidationError(f"{where} does not exist or cannot be read") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ValidationError(f"{where} must refer to a regular file")
    return SourceReference(candidate, info.st_dev, info.st_ino)


def _validate_structure_envelope(value: Any, where: str) -> dict[str, Any]:
    """Check the provisional inspection envelope without validating its graph."""

    obj = _object(value, where)
    required = {
        "format",
        "operation",
        "stage",
        "status",
        "processing_complete",
        "diagnostics_complete",
        "diagnostics",
    }
    missing = sorted(required - set(obj))
    if missing:
        raise ValidationError(f"{where} is missing required field(s): {', '.join(missing)}")
    format_name = _string(obj["format"], f"{where}.format", max_len=256)
    if format_name != STRUCTURE_FORMAT:
        raise ValidationError(f"{where}.format must be {STRUCTURE_FORMAT}")
    if obj["operation"] != "inspect-structure":
        raise ValidationError(f"{where}.operation must be inspect-structure")
    _string(obj["stage"], f"{where}.stage", max_len=128)
    status = _string(obj["status"], f"{where}.status", max_len=128)
    if status not in STRUCTURE_STATUSES:
        raise ValidationError(f"{where}.status is not a supported inspection status")
    for key in ("processing_complete", "diagnostics_complete"):
        if not isinstance(obj[key], bool):
            raise ValidationError(f"{where}.{key} must be a boolean")
    diagnostics = _array(obj["diagnostics"], f"{where}.diagnostics")
    if status == "success":
        if not obj["processing_complete"] or not obj["diagnostics_complete"]:
            raise ValidationError(f"{where}.success must be complete")
        if not isinstance(obj.get("graph"), dict):
            raise ValidationError(f"{where}.graph must be an object for success")
        if diagnostics:
            raise ValidationError(f"{where}.diagnostics must be empty for success")
    else:
        if not obj["processing_complete"] and not obj["diagnostics_complete"]:
            raise ValidationError(
                f"{where} cannot report incomplete processing and incomplete diagnostics together"
            )
        if "graph" in obj:
            raise ValidationError(f"{where}.graph is only valid for success")
        if not diagnostics:
            raise ValidationError(f"{where}.diagnostics must not be empty for a non-success status")
    for index, diagnostic in enumerate(diagnostics):
        diagnostic_obj = _object(diagnostic, f"{where}.diagnostics[{index}]")
        if not diagnostic_obj:
            raise ValidationError(f"{where}.diagnostics[{index}] must not be empty")
    return obj


def _preview_address(value: Any, where: str, kind: str) -> PreviewAddressKey:
    address = _object(value, where)
    _check_fields(address, PREVIEW_ADDRESS_FIELDS, where)
    if set(address) != PREVIEW_ADDRESS_FIELDS:
        missing = sorted(PREVIEW_ADDRESS_FIELDS - set(address))
        raise ValidationError(f"{where} is missing field(s): {', '.join(missing)}")
    namespace = address.get("namespace")
    role = address.get("role")
    anchors = address.get("anchors")
    if type(namespace) is not str or not ADDRESS_COMPONENT_RE.fullmatch(namespace):
        raise ValidationError(f"{where}.namespace is not a restricted identifier")
    if type(role) is not str or not ADDRESS_COMPONENT_RE.fullmatch(role):
        raise ValidationError(f"{where}.role is not a restricted identifier")
    if len(namespace.encode("ascii", "strict")) > ADDRESS_COMPONENT_MAX_BYTES:
        raise ValidationError(f"{where}.namespace exceeds the identifier length bound")
    if len(role.encode("ascii", "strict")) > ADDRESS_COMPONENT_MAX_BYTES:
        raise ValidationError(f"{where}.role exceeds the identifier length bound")
    if not isinstance(anchors, list):
        raise ValidationError(f"{where}.anchors must be an array")
    if len(anchors) > ADDRESS_MAX_ANCHORS:
        raise ValidationError(f"{where}.anchors exceeds the resource bound")
    normalized_anchors: list[str] = []
    for index, anchor in enumerate(anchors):
        if type(anchor) is not str or not ADDRESS_COMPONENT_RE.fullmatch(anchor):
            raise ValidationError(f"{where}.anchors[{index}] is not a restricted identifier")
        if len(anchor.encode("ascii", "strict")) > ADDRESS_COMPONENT_MAX_BYTES:
            raise ValidationError(
                f"{where}.anchors[{index}] exceeds the identifier length bound"
            )
        normalized_anchors.append(anchor)
    if address.get("kind") != kind:
        raise ValidationError(f"{where}.kind must be {kind}")
    return (namespace, tuple(normalized_anchors), kind, role)


def _preview_graph_addresses(
    graph: dict[str, Any], collection: str, kind: str, where: str
) -> dict[PreviewAddressKey, dict[str, Any]]:
    addresses: dict[PreviewAddressKey, dict[str, Any]] = {}
    for index, value in enumerate(graph[collection]):
        item = _object(value, f"{where}.graph.{collection}[{index}]")
        key = _preview_address(
            item.get("address"),
            f"{where}.graph.{collection}[{index}].address",
            kind,
        )
        if key in addresses:
            raise ValidationError(f"{where}.graph.{collection} contains duplicate addresses")
        addresses[key] = item
    return addresses


def _preview_part_reference(
    value: Any, where: str, part_addresses: set[PreviewAddressKey]
) -> PreviewAddressKey:
    key = _preview_address(value, where, "part")
    if key not in part_addresses:
        raise ValidationError(f"{where} does not reference a graph Part")
    return key


def _preview_translation(value: Any, where: str) -> None:
    translation = _array(value, where)
    if len(translation) != 3:
        raise ValidationError(f"{where} must be an array of 3 integers")
    for component in translation:
        if type(component) is not int or not SIGNED_I64_MIN <= component <= SIGNED_I64_MAX:
            raise ValidationError(
                f"{where} components must be signed i64 integers exactly representable as binary64"
            )
        try:
            exactly_representable = int(float(component)) == component
        except (OverflowError, ValueError):
            exactly_representable = False
        if not exactly_representable:
            raise ValidationError(
                f"{where} components must be signed i64 integers exactly representable as binary64"
            )


def _preview_attachment_required_roots(
    graph: dict[str, Any], part_addresses: set[PreviewAddressKey], where: str
) -> set[PreviewAddressKey]:
    modules = graph.get("modules", [])
    if not isinstance(modules, list):
        raise ValidationError(f"{where}.graph.modules must be an array")
    roots: set[PreviewAddressKey] = set()
    for index, value in enumerate(modules):
        module_where = f"{where}.graph.modules[{index}]"
        module = _object(value, module_where)
        presence = module.get("presence")
        if presence not in {"absent", "present"}:
            raise ValidationError(f"{module_where}.presence must be absent or present")
        attachment_required = module.get("attachment_required")
        if type(attachment_required) is not bool:
            raise ValidationError(f"{module_where}.attachment_required must be a boolean")
        root = module.get("root")
        if presence == "absent":
            if root is not None:
                raise ValidationError(f"{module_where}.root must be null for an absent module")
            continue
        if root is None:
            raise ValidationError(f"{module_where}.root is required for a present module")
        root_key = _preview_part_reference(root, f"{module_where}.root", part_addresses)
        if attachment_required and root_key in roots:
            raise ValidationError(f"{where}.graph.modules contains duplicate attachment roots")
        if attachment_required:
            roots.add(root_key)
    return roots


def _validate_exact_placement_preview(
    value: Any,
    where: str,
    graph: dict[str, Any],
    prepared_basis: dict[str, Any] | None = None,
) -> None:
    preview = _object(value, where)
    format_name = _string(preview.get("format"), f"{where}.format", max_len=256)
    if format_name != EXACT_PLACEMENT_PREVIEW_FORMAT:
        raise ValidationError(f"{where}.format must be {EXACT_PLACEMENT_PREVIEW_FORMAT}")
    status = _string(preview.get("status"), f"{where}.status", max_len=128)

    try:
        encoded = json.dumps(preview, allow_nan=False, ensure_ascii=False)
        encoded_bytes = encoded.encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValidationError(f"{where} is not JSON-compatible: {exc}") from exc
    if len(encoded_bytes) > MAX_STRUCTURE_JSON_BYTES:
        raise ValidationError(f"{where} is too large")

    if status == "unavailable":
        _check_fields(preview, {"format", "status", "diagnostic"}, where)
        diagnostic = _object(preview.get("diagnostic"), f"{where}.diagnostic")
        _check_fields(diagnostic, {"code", "message"}, f"{where}.diagnostic")
        if diagnostic.get("code") != EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE:
            raise ValidationError(
                f"{where}.diagnostic.code must be {EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE}"
            )
        _string(diagnostic.get("message"), f"{where}.diagnostic.message")
        return
    if status != "available":
        raise ValidationError(f"{where}.status must be available or unavailable")

    _check_fields(
        preview,
        {
            "format",
            "status",
            "basis",
            "parts",
            "containment_edges",
            "joint_edges",
            "attachments",
        },
        where,
    )
    basis = _object(preview.get("basis"), f"{where}.basis")
    _check_fields(
        basis,
        {"length_unit", "handedness", "up", "forward", "source_for_canonical"},
        f"{where}.basis",
    )
    if prepared_basis is not None and basis != prepared_basis:
        raise ValidationError(f"{where}.basis does not match prepared.basis")
    if (
        basis.get("length_unit") != "metre"
        or basis.get("handedness") != "right"
        or basis.get("up") != "+y"
        or basis.get("forward") != "+z"
        or basis.get("source_for_canonical") != ["+x", "+y", "+z"]
    ):
        raise ValidationError(f"{where}.basis is not the closed prepared basis")

    part_records = _preview_graph_addresses(graph, "parts", "part", where)
    joint_records = _preview_graph_addresses(graph, "joints", "joint", where)
    socket_records = _preview_graph_addresses(graph, "sockets", "socket", where)
    attachment_records = _preview_graph_addresses(graph, "attachments", "attachment", where)
    part_addresses = set(part_records)
    joint_addresses = set(joint_records)
    socket_addresses = set(socket_records)
    attachment_addresses = set(attachment_records)
    attachment_roots = _preview_attachment_required_roots(graph, part_addresses, where)

    graph_parents: dict[PreviewAddressKey, PreviewAddressKey | None] = {}
    root_addresses: set[PreviewAddressKey] = set()
    for address, part_record in part_records.items():
        containment_where = f"{where}.graph.parts[{address!r}].containment"
        containment = _object(part_record.get("containment"), containment_where)
        _check_fields(containment, {"root", "parent"}, containment_where)
        if set(containment) == {"root"}:
            if containment["root"] is not True:
                raise ValidationError(f"{containment_where}.root must be true")
            graph_parents[address] = None
            root_addresses.add(address)
        elif set(containment) == {"parent"}:
            parent = _preview_part_reference(
                containment["parent"], f"{containment_where}.parent", part_addresses
            )
            if parent == address:
                raise ValidationError(f"{containment_where}.parent cannot self-reference")
            graph_parents[address] = parent
        else:
            raise ValidationError(
                f"{containment_where} must contain exactly root or parent"
            )
    if len(root_addresses) != 1:
        raise ValidationError(f"{where}.graph.parts must contain exactly one root")
    structural_root = next(iter(root_addresses))

    parts = _array(preview.get("parts"), f"{where}.parts")
    if len(parts) != len(graph["parts"]):
        raise ValidationError(f"{where}.parts count does not match graph.parts")
    seen_parts: set[PreviewAddressKey] = set()
    for index, value in enumerate(parts):
        part_where = f"{where}.parts[{index}]"
        part = _object(value, part_where)
        _check_fields(part, {"address", "position", "parent", "placement_source"}, part_where)
        address = _preview_part_reference(part.get("address"), f"{part_where}.address", part_addresses)
        if address in seen_parts:
            raise ValidationError(f"{where}.parts contains duplicate addresses")
        seen_parts.add(address)
        _preview_translation(part.get("position"), f"{part_where}.position")
        parent = part.get("parent")
        parent_key = None
        if parent is not None:
            parent_key = _preview_part_reference(parent, f"{part_where}.parent", part_addresses)
        if parent_key != graph_parents[address]:
            raise ValidationError(f"{part_where}.parent does not match graph containment")
        source = _string(part.get("placement_source"), f"{part_where}.placement_source")
        if source not in EXACT_PLACEMENT_PREVIEW_SOURCES:
            raise ValidationError(f"{part_where}.placement_source is not supported")
        expected_source = (
            "authored-root"
            if address == structural_root
            else "authored-attachment"
            if address in attachment_roots
            else "authored-containment"
        )
        if source != expected_source:
            raise ValidationError(f"{part_where}.placement_source does not match provenance")
    if seen_parts != part_addresses:
        raise ValidationError(f"{where}.parts addresses do not match graph.parts")

    containment_edges = _array(preview.get("containment_edges"), f"{where}.containment_edges")
    expected_containment = {
        (parent, child)
        for child, parent in graph_parents.items()
        if parent is not None
    }
    if len(containment_edges) != len(expected_containment):
        raise ValidationError(f"{where}.containment_edges count must equal parts minus one")
    seen_containment: set[tuple[PreviewAddressKey, PreviewAddressKey]] = set()
    for index, value in enumerate(containment_edges):
        edge_where = f"{where}.containment_edges[{index}]"
        edge = _object(value, edge_where)
        _check_fields(edge, {"parent", "child"}, edge_where)
        parent = _preview_part_reference(edge.get("parent"), f"{edge_where}.parent", part_addresses)
        child = _preview_part_reference(edge.get("child"), f"{edge_where}.child", part_addresses)
        if parent == child:
            raise ValidationError(f"{edge_where} cannot be a self edge")
        identity = (parent, child)
        if identity in seen_containment:
            raise ValidationError(f"{where}.containment_edges contains duplicates")
        seen_containment.add(identity)
    if seen_containment != expected_containment:
        raise ValidationError(f"{where}.containment_edges do not match graph containment")

    joint_edges = _array(preview.get("joint_edges"), f"{where}.joint_edges")
    if len(joint_edges) != len(graph["joints"]):
        raise ValidationError(f"{where}.joint_edges count does not match graph.joints")
    seen_joints: set[PreviewAddressKey] = set()
    for index, value in enumerate(joint_edges):
        edge_where = f"{where}.joint_edges[{index}]"
        edge = _object(value, edge_where)
        _check_fields(edge, {"joint", "proximal", "distal"}, edge_where)
        joint = _preview_address(edge.get("joint"), f"{edge_where}.joint", "joint")
        if joint not in joint_addresses:
            raise ValidationError(f"{edge_where}.joint does not reference a graph Joint")
        if joint in seen_joints:
            raise ValidationError(f"{where}.joint_edges contains duplicate joints")
        seen_joints.add(joint)
        proximal = _preview_part_reference(
            edge.get("proximal"), f"{edge_where}.proximal", part_addresses
        )
        distal = _preview_part_reference(
            edge.get("distal"), f"{edge_where}.distal", part_addresses
        )
        graph_joint = joint_records[joint]
        graph_proximal = _preview_part_reference(
            graph_joint.get("proximal"), f"{edge_where}.graph.proximal", part_addresses
        )
        graph_distal = _preview_part_reference(
            graph_joint.get("distal"), f"{edge_where}.graph.distal", part_addresses
        )
        if (proximal, distal) != (graph_proximal, graph_distal):
            raise ValidationError(f"{edge_where} endpoints do not match graph Joint")
    if seen_joints != joint_addresses:
        raise ValidationError(f"{where}.joint_edges identities do not match graph.joints")

    attachments = _array(preview.get("attachments"), f"{where}.attachments")
    if len(attachments) != len(graph["attachments"]):
        raise ValidationError(f"{where}.attachments count does not match graph.attachments")
    seen_attachments: set[PreviewAddressKey] = set()
    seen_attachment_roots: set[PreviewAddressKey] = set()
    for index, value in enumerate(attachments):
        attachment_where = f"{where}.attachments[{index}]"
        attachment = _object(value, attachment_where)
        _check_fields(
            attachment,
            {
                "attachment",
                "root",
                "host_socket",
                "mating_socket",
                "offset",
                "authored_root_local",
                "derived_root_local",
            },
            attachment_where,
        )
        identity = _preview_address(
            attachment.get("attachment"), f"{attachment_where}.attachment", "attachment"
        )
        if identity not in attachment_addresses:
            raise ValidationError(
                f"{attachment_where}.attachment does not reference a graph Attachment"
            )
        if identity in seen_attachments:
            raise ValidationError(f"{where}.attachments contains duplicate attachments")
        seen_attachments.add(identity)
        root = _preview_part_reference(
            attachment.get("root"), f"{attachment_where}.root", part_addresses
        )
        if root not in attachment_roots:
            raise ValidationError(
                f"{attachment_where}.root is not a present attachment-required module root"
            )
        if root in seen_attachment_roots:
            raise ValidationError(f"{where}.attachments contains duplicate roots")
        seen_attachment_roots.add(root)
        graph_attachment = attachment_records[identity]
        for key in ("host_socket", "mating_socket"):
            socket = _preview_address(attachment.get(key), f"{attachment_where}.{key}", "socket")
            if socket not in socket_addresses:
                raise ValidationError(f"{attachment_where}.{key} does not reference a graph Socket")
        graph_socket_fields = {"host_socket": "host", "mating_socket": "mating"}
        for preview_field, graph_field in graph_socket_fields.items():
            graph_socket = _preview_address(
                graph_attachment.get(graph_field),
                f"{attachment_where}.graph.{graph_field}",
                "socket",
            )
            if _preview_address(
                attachment.get(preview_field), f"{attachment_where}.{preview_field}", "socket"
            ) != graph_socket:
                raise ValidationError(
                    f"{attachment_where}.{preview_field} does not match graph Attachment"
                )
        for key in ("offset", "authored_root_local", "derived_root_local"):
            _preview_translation(attachment.get(key), f"{attachment_where}.{key}")
    if seen_attachments != attachment_addresses:
        raise ValidationError(f"{where}.attachments identities do not match graph.attachments")
    if seen_attachment_roots != attachment_roots:
        raise ValidationError(f"{where}.attachments roots do not match required module roots")


def _validate_prepared_source_envelope(value: Any, where: str) -> dict[str, Any]:
    """Validate the source-preparation projection used by the structure viewer.

    The graph deliberately uses the existing structural projection contract;
    only the additional prepared inventory is checked here.  Keeping this
    validation at the publication boundary prevents a malformed producer from
    being copied into an otherwise immutable review session.
    """

    obj = _object(value, where)
    required = {
        "format",
        "operation",
        "stage",
        "status",
        "processing_complete",
        "diagnostics_complete",
        "diagnostics",
    }
    missing = sorted(required - set(obj))
    if missing:
        raise ValidationError(f"{where} is missing required field(s): {', '.join(missing)}")
    if _string(obj["format"], f"{where}.format", max_len=256) != PREPARED_SOURCE_FORMAT:
        raise ValidationError(f"{where}.format must be {PREPARED_SOURCE_FORMAT}")
    if obj["operation"] != PREPARED_SOURCE_OPERATION:
        raise ValidationError(f"{where}.operation must be {PREPARED_SOURCE_OPERATION}")
    stage = _string(obj["stage"], f"{where}.stage", max_len=128)
    if stage not in {"admission", PREPARED_SOURCE_STAGE, "input", "usage"}:
        raise ValidationError(
            f"{where}.stage must be admission or {PREPARED_SOURCE_STAGE}"
        )
    status = _string(obj["status"], f"{where}.status", max_len=128)
    if status not in STRUCTURE_STATUSES:
        raise ValidationError(f"{where}.status is not a supported inspection status")
    allowed_stages = {
        "success": {PREPARED_SOURCE_STAGE},
        "input-failure": {"input"},
        "usage-error": {"usage"},
        "invalid-source": {"admission", PREPARED_SOURCE_STAGE},
        "unsupported": {"admission"},
        "resource-limit": {"admission"},
        "internal-failure": {"admission", PREPARED_SOURCE_STAGE},
    }
    if stage not in allowed_stages[status]:
        expected = ", ".join(sorted(allowed_stages[status]))
        raise ValidationError(f"{where}.stage is invalid for status {status}; expected {expected}")
    for key in ("processing_complete", "diagnostics_complete"):
        if not isinstance(obj[key], bool):
            raise ValidationError(f"{where}.{key} must be a boolean")
    diagnostics = _array(obj["diagnostics"], f"{where}.diagnostics")
    for index, diagnostic in enumerate(diagnostics):
        diagnostic_obj = _object(diagnostic, f"{where}.diagnostics[{index}]")
        if not diagnostic_obj:
            raise ValidationError(f"{where}.diagnostics[{index}] must not be empty")
    if status == "success":
        if not obj["processing_complete"] or not obj["diagnostics_complete"]:
            raise ValidationError(f"{where}.success must be complete")
        if diagnostics:
            raise ValidationError(f"{where}.diagnostics must be empty for success")
        if not isinstance(obj.get("graph"), dict):
            raise ValidationError(f"{where}.graph must be an object for success")
        graph = obj["graph"]
        graph_collections = {
            "parts", "joints", "sockets", "attachments", "landmarks", "dimensions", "frames"
        }
        graph_lengths: dict[str, int] = {}
        for collection in sorted(graph_collections):
            values = graph.get(collection)
            if not isinstance(values, list):
                raise ValidationError(f"{where}.graph.{collection} must be an array")
            graph_lengths[collection] = len(values)
        prepared = _object(obj.get("prepared"), f"{where}.prepared")
        _check_fields(prepared, {"basis", "counts", "numeric_values"}, f"{where}.prepared")
        basis = _object(prepared.get("basis"), f"{where}.prepared.basis")
        _check_fields(
            basis,
            {"length_unit", "handedness", "up", "forward", "source_for_canonical"},
            f"{where}.prepared.basis",
        )
        for key in ("length_unit", "handedness", "up", "forward"):
            _string(basis.get(key), f"{where}.prepared.basis.{key}", max_len=128)
        source_for_canonical = basis["source_for_canonical"]
        if (
            not isinstance(source_for_canonical, list)
            or len(source_for_canonical) != 3
            or any(
                not isinstance(axis, str) or not axis.strip()
                for axis in source_for_canonical
            )
        ):
            raise ValidationError(
                f"{where}.prepared.basis.source_for_canonical must be an array of 3 strings"
            )
        counts = _object(prepared.get("counts"), f"{where}.prepared.counts")
        expected_counts = {
            "parts", "joints", "sockets", "attachments", "landmarks", "dimensions", "frames"
        }
        _check_fields(counts, expected_counts, f"{where}.prepared.counts")
        missing_counts = sorted(expected_counts - set(counts))
        if missing_counts:
            raise ValidationError(
                f"{where}.prepared.counts is missing field(s): {', '.join(missing_counts)}"
            )
        for key, count in counts.items():
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValidationError(f"{where}.prepared.counts.{key} must be a non-negative integer")
            if count != graph_lengths[key]:
                raise ValidationError(
                    f"{where}.prepared.counts.{key} does not match graph.{key} length"
                )
        numeric_values = prepared.get("numeric_values")
        if not isinstance(numeric_values, list):
            raise ValidationError(f"{where}.prepared.numeric_values must be an array")
        try:
            encoded = json.dumps(numeric_values, allow_nan=False, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{where}.prepared.numeric_values is not JSON-compatible: {exc}") from exc
        if len(encoded) > MAX_STRUCTURE_JSON_BYTES:
            raise ValidationError(f"{where}.prepared.numeric_values is too large")
        rows: list[Any] = numeric_values
        expected_rows = {
            "parts": graph_lengths["parts"] * 7,
            "joints": graph_lengths["joints"] * 14,
            "sockets": graph_lengths["sockets"] * 7,
            "attachments": graph_lengths["attachments"] * 7,
            "landmarks": graph_lengths["landmarks"] * 3,
            "dimensions": graph_lengths["dimensions"],
            "frames": graph_lengths["frames"] * 7,
        }
        rows_by_group = {group: 0 for group in expected_rows}
        for index, row in enumerate(rows):
            row_where = f"{where}.prepared.numeric_values[{index}]"
            row_obj = _object(row, row_where)
            if not _string(row_obj.get("group"), f"{row_where}.group", max_len=128):
                raise ValidationError(f"{row_where}.group is required")
            group = row_obj["group"]
            if group not in expected_rows:
                raise ValidationError(f"{row_where}.group is not a supported collection")
            rows_by_group[group] += 1
            location = next(
                (row_obj.get(key) for key in (
                    "semantic_key", "semanticKey", "address", "owner_role", "ownerRole", "location", "key"
                ) if row_obj.get(key) is not None),
                None,
            )
            if location is None:
                raise ValidationError(f"{row_where} has no semantic location")
            for aliases, label in (
                (("field",), "field"),
                (("component",), "component"),
                (("display_value", "displayValue", "value"), "display value"),
                (("binary64_bits", "binary64Bits", "bits"), "binary64 bits"),
            ):
                if not any(row_obj.get(alias) is not None for alias in aliases):
                    raise ValidationError(f"{row_where} has no {label}")
            bits = next(
                row_obj[alias]
                for alias in ("binary64_bits", "binary64Bits", "bits")
                if row_obj.get(alias) is not None
            )
            if not isinstance(bits, str) or re.fullmatch(r"[0-9a-f]{16}", bits) is None:
                raise ValidationError(
                    f"{row_where} binary64 bits must be 16 lowercase hexadecimal digits"
                )
        for group, expected in expected_rows.items():
            if rows_by_group[group] != expected:
                raise ValidationError(
                    f"{where}.prepared.numeric_values {group} rows do not match expected cardinality"
                )
        if "preview" in obj:
            _validate_exact_placement_preview(
                obj["preview"], f"{where}.preview", graph, prepared["basis"]
            )
    else:
        if not obj["processing_complete"] and not obj["diagnostics_complete"]:
            raise ValidationError(
                f"{where} cannot report incomplete processing and incomplete diagnostics together"
            )
        if "graph" in obj or "prepared" in obj:
            raise ValidationError(f"{where}.graph and prepared are only valid for success")
        if "preview" in obj:
            raise ValidationError(f"{where}.preview is only valid for success")
        if not diagnostics:
            raise ValidationError(f"{where}.diagnostics must not be empty for a non-success status")
        primary = obj.get("primary_diagnostic")
        if not isinstance(primary, dict) or not primary:
            raise ValidationError(f"{where}.primary_diagnostic must be a non-empty object")
        if not any(primary == diagnostic for diagnostic in diagnostics):
            raise ValidationError(f"{where}.primary_diagnostic must be present in diagnostics")
    return obj


def _form_i64_vector(value: Any, where: str) -> list[int]:
    # Keep the filled-form adapter on exactly the same integer carrier domain
    # as the existing exact-placement preview, including binary64 fidelity.
    _preview_translation(value, where)
    return list(value)


def _form_permille(value: Any, where: str) -> int:
    if type(value) is not int or not 0 < value <= PROVISIONAL_FORM_MAX_PERMILLE:
        raise ValidationError(
            f"{where} must be a positive integer permille no greater than "
            f"{PROVISIONAL_FORM_MAX_PERMILLE}"
        )
    return value


def _form_address(value: Any, where: str) -> tuple[str, tuple[str, ...], str, str]:
    try:
        return _preview_address(value, where, "part")
    except (UnicodeEncodeError, TypeError) as exc:
        raise ValidationError(f"{where} is not a valid Part address") from exc


def _form_role_shape(format_name: str, role: str) -> str | None:
    if (
        format_name in PROVISIONAL_FORM_V7_NECK_CAPSULE_FORMATS
        or format_name in PROVISIONAL_FORM_V8_NECK_CAPSULE_FORMATS
        or format_name in PROVISIONAL_FORM_V9_NECK_CAPSULE_FORMATS
        or format_name in PROVISIONAL_FORM_V10_NECK_CAPSULE_FORMATS
        or format_name in PROVISIONAL_FORM_V11_NECK_CAPSULE_FORMATS
    ) and role == "neck":
        return "capsule"
    return PROVISIONAL_FORM_ROLE_SHAPES.get(role)


def _form_capsule_child_roles(format_name: str) -> dict[str, str]:
    if format_name in PROVISIONAL_FORM_V7_NECK_CAPSULE_FORMATS:
        return PROVISIONAL_FORM_V7_CAPSULE_CHILD_ROLES
    if format_name in PROVISIONAL_FORM_V8_NECK_CAPSULE_FORMATS:
        return PROVISIONAL_FORM_V8_CAPSULE_CHILD_ROLES
    if format_name in PROVISIONAL_FORM_V9_NECK_CAPSULE_FORMATS:
        return PROVISIONAL_FORM_V8_CAPSULE_CHILD_ROLES
    if format_name in PROVISIONAL_FORM_V10_NECK_CAPSULE_FORMATS:
        return PROVISIONAL_FORM_V10_CAPSULE_CHILD_ROLES
    if format_name in PROVISIONAL_FORM_V11_NECK_CAPSULE_FORMATS:
        return PROVISIONAL_FORM_V11_CAPSULE_CHILD_ROLES
    return PROVISIONAL_FORM_CAPSULE_CHILD_ROLES


def _form_display_factors(
    profile_id: str, role: str, shape_name: str
) -> tuple[int, ...]:
    """Return the fixed Rust display factors for one shape control set."""

    if shape_name == "ellipsoid":
        if profile_id == "neutral-v0":
            return (1_000, 1_000, 1_000)
        if profile_id == "broad-soft-v0":
            if role in {"pelvis", "torso", "head"}:
                return (1_200, 1_000, 1_150)
            if role in {"hand", "foot"}:
                return (1_150, 1_000, 1_150)
            return (1_000, 1_000, 1_000)
        if profile_id == "lean-readable-v0":
            return (800, 1_000, 800)
        if profile_id == "depth-forward-v0":
            if role in {"torso", "head", "foot"}:
                return (1_000, 1_000, 1_300)
            return (1_000, 1_000, 1_000)
    elif shape_name in {"capsule", "tapered-segment"}:
        if profile_id == "broad-soft-v0":
            factor = 1_150
        elif profile_id == "lean-readable-v0":
            factor = 800
        else:
            factor = 1_000
        return (factor,) * (1 if shape_name == "capsule" else 2)
    raise ValidationError(
        f"unsupported display factor combination: {profile_id}/{role}/{shape_name}"
    )


def _form_scaled_display_value(value: int, factor: int, where: str) -> int:
    """Apply the Rust fixed-factor integer operation and its result bound."""

    scaled = value * factor // 1_000
    if not 0 < scaled <= PROVISIONAL_FORM_MAX_PERMILLE:
        raise ValidationError(
            f"{where} fixed display factor produces invalid permille {scaled}"
        )
    return scaled


def _form_finite_vector(value: Any, where: str, length: int) -> list[int | float]:
    values = _array(value, where)
    if len(values) != length:
        raise ValidationError(f"{where} must contain exactly {length} components")
    normalized: list[int | float] = []
    for index, component in enumerate(values):
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise ValidationError(f"{where}[{index}] must be a finite number")
        if not math.isfinite(component):
            raise ValidationError(f"{where}[{index}] must be a finite number")
        normalized.append(component)
    return normalized


def _form_control_provenance(value: Any, where: str, document: str, namespace: str) -> None:
    provenance = _object(value, where)
    _check_fields(provenance, {"source", "document", "namespace"}, where)
    if (
        provenance.get("source") != PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE
        or provenance.get("document") != document
        or provenance.get("namespace") != namespace
    ):
        raise ValidationError(f"{where} is not source-authored")


def _provisional_form_upper_arm_owner(namespace: str, side: str) -> tuple[str, tuple[str, ...], str, str]:
    return _provisional_form_arm_owner(namespace, side, "upper_arm")


def _provisional_form_arm_owner(
    namespace: str, side: str, role: str
) -> tuple[str, tuple[str, ...], str, str]:
    return (namespace, (side,), "part", role)


def _provisional_form_foot_owner(namespace: str, side: str) -> tuple[str, tuple[str, ...], str, str]:
    return _provisional_form_arm_owner(namespace, side, "foot")


def _validate_v6_authored_controls(
    obj: dict[str, Any], where: str, *, document: str, namespace: str
) -> None:
    """Validate the closed source-authored shoulder-control inventory."""

    expected_owners = {
        _provisional_form_upper_arm_owner(namespace, side)
        for side in ("left", "right")
    }
    expected_frame_keys = {
        (owner, PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE)
        for owner in expected_owners
    }
    frames = _array(obj.get("authored_frames"), f"{where}.authored_frames")
    if len(frames) != len(expected_frame_keys):
        raise ValidationError(
            f"{where}.authored_frames must contain exactly two shoulder control frames"
        )
    frame_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    for index, raw_frame in enumerate(frames):
        frame_where = f"{where}.authored_frames[{index}]"
        frame = _object(raw_frame, frame_where)
        _check_fields(frame, {"owner", "role", "transform", "provenance"}, frame_where)
        owner = _form_address(frame.get("owner"), f"{frame_where}.owner")
        role = _string(frame.get("role"), f"{frame_where}.role", max_len=256)
        key = (owner, role)
        frame_keys.append(key)
        if key not in expected_frame_keys:
            raise ValidationError(
                f"{frame_where} must be the left/right upper_arm {PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE}"
            )
        _form_control_provenance(
            frame.get("provenance"), f"{frame_where}.provenance", document, namespace
        )
        transform = _object(frame.get("transform"), f"{frame_where}.transform")
        _check_fields(transform, {"translation", "rotation_xyzw"}, f"{frame_where}.transform")
        translation = _form_finite_vector(
            transform.get("translation"), f"{frame_where}.transform.translation", 3
        )
        rotation = _form_finite_vector(
            transform.get("rotation_xyzw"), f"{frame_where}.transform.rotation_xyzw", 4
        )
        if translation != [0, 0, 0] or rotation != [0, 0, 0, 1]:
            raise ValidationError(
                f"{frame_where} must use the identity rigid transform"
            )
    if len(set(frame_keys)) != len(frame_keys):
        raise ValidationError(f"{where}.authored_frames contains duplicate owner/role keys")
    if set(frame_keys) != expected_frame_keys:
        raise ValidationError(
            f"{where}.authored_frames must contain exactly one frame per left/right upper_arm"
        )
    if frame_keys != sorted(frame_keys):
        raise ValidationError(f"{where}.authored_frames must use stable owner/role order")

    expected_landmark_keys = {
        (owner, role)
        for owner in expected_owners
        for role in PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES
    }
    landmarks = _array(obj.get("authored_landmarks"), f"{where}.authored_landmarks")
    if len(landmarks) != len(expected_landmark_keys):
        raise ValidationError(
            f"{where}.authored_landmarks must contain exactly four shoulder landmarks"
        )
    landmark_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    for index, raw_landmark in enumerate(landmarks):
        landmark_where = f"{where}.authored_landmarks[{index}]"
        landmark = _object(raw_landmark, landmark_where)
        _check_fields(
            landmark,
            {"owner", "role", "frame", "position", "provenance"},
            landmark_where,
        )
        owner = _form_address(landmark.get("owner"), f"{landmark_where}.owner")
        role = _string(landmark.get("role"), f"{landmark_where}.role", max_len=256)
        key = (owner, role)
        landmark_keys.append(key)
        if key not in expected_landmark_keys:
            raise ValidationError(
                f"{landmark_where} must be form_shoulder_peak or form_axilla on a left/right upper_arm"
            )
        frame = _object(landmark.get("frame"), f"{landmark_where}.frame")
        _check_fields(frame, {"owner", "role"}, f"{landmark_where}.frame")
        frame_owner = _form_address(frame.get("owner"), f"{landmark_where}.frame.owner")
        frame_role = _string(frame.get("role"), f"{landmark_where}.frame.role", max_len=256)
        if frame_owner != owner or frame_role != PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE:
            raise ValidationError(
                f"{landmark_where}.frame must reference its same-owner {PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE}"
            )
        position = _form_finite_vector(landmark.get("position"), f"{landmark_where}.position", 3)
        if any(abs(component) > PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND for component in position):
            raise ValidationError(
                f"{landmark_where}.position components must be within +/-{PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND}"
            )
        _form_control_provenance(
            landmark.get("provenance"), f"{landmark_where}.provenance", document, namespace
        )
    if len(set(landmark_keys)) != len(landmark_keys):
        raise ValidationError(f"{where}.authored_landmarks contains duplicate owner/role keys")
    if set(landmark_keys) != expected_landmark_keys:
        raise ValidationError(
            f"{where}.authored_landmarks must contain exactly peak and axilla per upper_arm"
        )
    if landmark_keys != sorted(landmark_keys):
        raise ValidationError(f"{where}.authored_landmarks must use stable owner/role order")


def _provisional_form_torso_owner(
    namespace: str, role: str
) -> tuple[str, tuple[str, ...], str, str]:
    return (namespace, (), "part", role)


def _provisional_form_index(value: Any, length: int, where: str) -> int:
    if type(value) is not int or not 0 <= value < length:
        raise ValidationError(f"{where} must be an in-range integer index")
    return value


def _validate_v7_authored_torso_profile(
    obj: dict[str, Any],
    where: str,
    *,
    document: str,
    namespace: str,
    authored_dimension_values: dict[
        tuple[tuple[str, tuple[str, ...], str, str], str], int
    ],
    include_v8_controls: bool = False,
    include_v9_controls: bool = False,
    include_v10_controls: bool = False,
    include_v11_controls: bool = False,
) -> tuple[
    set[tuple[tuple[str, tuple[str, ...], str, str], str]],
    list[dict[str, Any]],
]:
    """Validate the closed v7 torso-profile index and its canonical records."""

    profile_where = f"{where}.authored_torso_profile"
    profile = _object(obj.get("authored_torso_profile"), profile_where)
    _check_fields(profile, {"format", "provenance", "sections"}, profile_where)
    if profile.get("format") != PROVISIONAL_FORM_TORSO_PROFILE_FORMAT:
        raise ValidationError(
            f"{profile_where}.format must be {PROVISIONAL_FORM_TORSO_PROFILE_FORMAT}"
        )
    _form_control_provenance(
        profile.get("provenance"),
        f"{profile_where}.provenance",
        document,
        namespace,
    )

    frames = _array(obj.get("authored_frames"), f"{where}.authored_frames")
    shoulder_frames = [
        item
        for item in frames
        if isinstance(item, dict) and item.get("role") == PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE
    ]
    landmarks = _array(obj.get("authored_landmarks"), f"{where}.authored_landmarks")
    shoulder_landmarks = [
        item
        for item in landmarks
        if isinstance(item, dict) and item.get("role") in PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES
    ]
    # Preserve the exact v6 shoulder contract inside v7.  The complete-array
    # checks below still reject unknown, missing, or duplicate torso records.
    _validate_v6_authored_controls(
        {"authored_frames": shoulder_frames, "authored_landmarks": shoulder_landmarks},
        where,
        document=document,
        namespace=namespace,
    )

    torso_owners = {
        _provisional_form_torso_owner(namespace, role)
        for role in {"pelvis", "torso"}
    }
    expected_frame_keys = {
        (owner, PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE)
        for owner in {
            _provisional_form_upper_arm_owner(namespace, side)
            for side in ("left", "right")
        }
    }
    expected_frame_keys.update(
        (owner, PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE)
        for owner in torso_owners
    )
    if include_v8_controls:
        expected_frame_keys.update(
            (
                _provisional_form_head_neck_owner(namespace, role),
                PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
            )
            for role in ("neck", "head")
        )
    if include_v9_controls:
        expected_frame_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, role),
                PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE,
            )
            for side in PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES
            for role in {"upper_arm", "forearm"}
        )
    if include_v10_controls:
        expected_frame_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, role),
                PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE,
            )
            for side in PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES
            for role in {"thigh", "shin"}
        )
    if include_v11_controls:
        expected_frame_keys.update(
            (
                _provisional_form_foot_owner(namespace, side),
                PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE,
            )
            for side in PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES
        )
    contract_label = "v11" if include_v11_controls else "v10" if include_v10_controls else "v9" if include_v9_controls else "v8" if include_v8_controls else "v7"
    expected_frame_count = 16 if include_v11_controls else 14 if include_v10_controls else 10 if include_v9_controls else 6 if include_v8_controls else 4
    if len(frames) != len(expected_frame_keys):
        raise ValidationError(
            f"{where}.authored_frames must contain exactly {expected_frame_count} {contract_label} control frames"
        )
    frame_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    seen_frame_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    for index, raw_frame in enumerate(frames):
        frame_where = f"{where}.authored_frames[{index}]"
        frame = _object(raw_frame, frame_where)
        _check_fields(frame, {"owner", "role", "transform", "provenance"}, frame_where)
        owner = _form_address(frame.get("owner"), f"{frame_where}.owner")
        role = _string(frame.get("role"), f"{frame_where}.role", max_len=256)
        key = (owner, role)
        frame_keys.append(key)
        if key in seen_frame_keys:
            raise ValidationError(f"{where}.authored_frames contains duplicate owner/role keys")
        if key not in expected_frame_keys:
            raise ValidationError(f"{frame_where} is not a {contract_label} control frame")
        _form_control_provenance(
            frame.get("provenance"), f"{frame_where}.provenance", document, namespace
        )
        transform = _object(frame.get("transform"), f"{frame_where}.transform")
        _check_fields(transform, {"translation", "rotation_xyzw"}, f"{frame_where}.transform")
        translation = _form_finite_vector(
            transform.get("translation"), f"{frame_where}.transform.translation", 3
        )
        rotation = _form_finite_vector(
            transform.get("rotation_xyzw"), f"{frame_where}.transform.rotation_xyzw", 4
        )
        if translation != [0, 0, 0] or rotation != [0, 0, 0, 1]:
            raise ValidationError(f"{frame_where} must use the identity rigid transform")
        seen_frame_keys.add(key)
    if set(frame_keys) != expected_frame_keys:
        raise ValidationError(
            f"{where}.authored_frames must contain the exact {contract_label} control inventory"
        )
    if frame_keys != sorted(frame_keys):
        raise ValidationError(f"{where}.authored_frames must use stable owner/role order")

    expected_landmark_keys = {
        (owner, role)
        for owner in {
            _provisional_form_upper_arm_owner(namespace, side)
            for side in ("left", "right")
        }
        for role in PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES
    }
    expected_landmark_keys.update(
        (
            _provisional_form_torso_owner(namespace, owner_role),
            f"form_torso_profile_{section_name.replace('-', '_')}",
        )
        for section_name, owner_role in zip(
            PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES,
            PROVISIONAL_FORM_TORSO_PROFILE_OWNER_ROLES,
        )
    )
    if include_v8_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_head_neck_owner(namespace, owner_role),
                f"form_head_neck_profile_{section_name.replace('-', '_')}",
            )
            for section_name, owner_role in zip(
                PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES,
            )
        )
    if include_v9_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, owner_role),
                f"form_arm_profile_{section_name.replace('-', '_')}",
            )
            for side in PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES
            for section_name, owner_role in zip(
                PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES,
            )
        )
    if include_v10_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, owner_role),
                f"form_leg_profile_{section_name.replace('-', '_')}",
            )
            for side in PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES
            for section_name, owner_role in zip(
                PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES,
            )
        )
    if include_v11_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_foot_owner(namespace, side),
                f"form_foot_profile_{section_name}",
            )
            for side in PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES
            for section_name in PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES
        )
    expected_landmark_count = 43 if include_v11_controls else 39 if include_v10_controls else 29 if include_v9_controls else 19 if include_v8_controls else 11
    if len(landmarks) != len(expected_landmark_keys):
        raise ValidationError(
            f"{where}.authored_landmarks must contain exactly {expected_landmark_count} {contract_label} control landmarks"
        )
    landmark_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    landmark_positions: list[list[int | float]] = []
    seen_landmark_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    for index, raw_landmark in enumerate(landmarks):
        landmark_where = f"{where}.authored_landmarks[{index}]"
        landmark = _object(raw_landmark, landmark_where)
        _check_fields(
            landmark,
            {"owner", "role", "frame", "position", "provenance"},
            landmark_where,
        )
        owner = _form_address(landmark.get("owner"), f"{landmark_where}.owner")
        role = _string(landmark.get("role"), f"{landmark_where}.role", max_len=256)
        key = (owner, role)
        landmark_keys.append(key)
        if key in seen_landmark_keys:
            raise ValidationError(f"{where}.authored_landmarks contains duplicate owner/role keys")
        if key not in expected_landmark_keys:
            raise ValidationError(f"{landmark_where} is not a v7 torso or shoulder landmark")
        _form_control_provenance(
            landmark.get("provenance"), f"{landmark_where}.provenance", document, namespace
        )
        frame = _object(landmark.get("frame"), f"{landmark_where}.frame")
        _check_fields(frame, {"owner", "role"}, f"{landmark_where}.frame")
        frame_owner = _form_address(frame.get("owner"), f"{landmark_where}.frame.owner")
        frame_role = _string(frame.get("role"), f"{landmark_where}.frame.role", max_len=256)
        expected_frame_role = (
            PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE
            if include_v11_controls and role.startswith("form_foot_profile_")
            else PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE
            if include_v9_controls and role.startswith("form_arm_profile_")
            else PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
            if include_v10_controls and role.startswith("form_leg_profile_")
            else PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE
            if owner[3] == "upper_arm"
            else PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE
            if include_v8_controls and owner[3] in {"neck", "head"}
            else PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE
        )
        if frame_owner != owner or frame_role != expected_frame_role:
            raise ValidationError(f"{landmark_where}.frame must reference its same-owner control frame")
        if (frame_owner, frame_role) not in seen_frame_keys:
            raise ValidationError(f"{landmark_where}.frame references an unlisted authored frame")
        position = _form_finite_vector(landmark.get("position"), f"{landmark_where}.position", 3)
        if any(abs(component) > PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND for component in position):
            raise ValidationError(
                f"{landmark_where}.position components must be within +/-{PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND}"
            )
        if owner[3] in {"pelvis", "torso"} and (position[0] != 0 or position[2] != 0):
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,0] point")
        if include_v8_controls and owner[3] in {"neck", "head"} and position[0] != 0:
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,z] point")
        if include_v9_controls and role.startswith("form_arm_profile_") and (
            owner[3] not in {"upper_arm", "forearm"} or position[0] != 0 or position[2] != 0
        ):
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,0] point")
        if include_v10_controls and role.startswith("form_leg_profile_") and (
            owner[3] not in {"thigh", "shin"} or position[0] != 0 or position[2] != 0
        ):
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,0] point")
        if include_v10_controls and role.startswith("form_leg_profile_") and not (
            PROVISIONAL_FORM_LEG_PROFILE_Y_MIN <= position[1] <= PROVISIONAL_FORM_LEG_PROFILE_Y_MAX
        ):
            raise ValidationError(
                f"{landmark_where}.position y must be in inclusive "
                f"[{PROVISIONAL_FORM_LEG_PROFILE_Y_MIN}, {PROVISIONAL_FORM_LEG_PROFILE_Y_MAX}]"
            )
        if include_v11_controls and role.startswith("form_foot_profile_") and (
            owner[3] != "foot"
            or position[0] != 0
            or not PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN <= position[1] <= PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX
            or not PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN <= position[2] <= PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX
        ):
            raise ValidationError(
                f"{landmark_where}.position must be [0,y,z] with y in inclusive "
                f"[{PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN}, {PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX}] "
                f"and z in inclusive [{PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN}, {PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX}]"
            )
        landmark_positions.append(position)
        seen_landmark_keys.add(key)
    if set(landmark_keys) != expected_landmark_keys:
        raise ValidationError(
            f"{where}.authored_landmarks must contain the exact {contract_label} control inventory"
        )
    if landmark_keys != sorted(landmark_keys):
        raise ValidationError(f"{where}.authored_landmarks must use stable owner/role order")

    dimension_records: list[
        tuple[tuple[str, tuple[str, ...], str, str], str, int]
    ] = []
    for index, raw_dimension in enumerate(
        _array(obj.get("authored_dimensions"), f"{where}.authored_dimensions")
    ):
        dimension_where = f"{where}.authored_dimensions[{index}]"
        dimension = _object(raw_dimension, dimension_where)
        owner = _form_address(dimension.get("owner"), f"{dimension_where}.owner")
        role = _string(dimension.get("role"), f"{dimension_where}.role", max_len=256)
        dimension_records.append(
            (owner, role, authored_dimension_values[(owner, role)])
        )

    sections = _array(profile.get("sections"), f"{profile_where}.sections")
    if len(sections) != len(PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES):
        raise ValidationError(f"{profile_where}.sections must contain exactly seven sections")
    consumed_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    section_y: list[float | int] = []
    source_sections: list[dict[str, Any]] = []
    for index, (raw_section, expected_name, expected_owner_role) in enumerate(
        zip(
            sections,
            PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES,
            PROVISIONAL_FORM_TORSO_PROFILE_OWNER_ROLES,
        )
    ):
        section_where = f"{profile_where}.sections[{index}]"
        section = _object(raw_section, section_where)
        _check_fields(
            section,
            {
                "name",
                "frame_index",
                "landmark_index",
                "dimension_indices",
                "provenance",
                "section_index",
            },
            section_where,
        )
        if section.get("name") != expected_name:
            raise ValidationError(f"{section_where}.name is not in the required stable order")
        if type(section.get("section_index")) is not int or section["section_index"] != index:
            raise ValidationError(f"{section_where}.section_index must equal its stable array index")
        _form_control_provenance(
            section.get("provenance"),
            f"{section_where}.provenance",
            document,
            namespace,
        )
        expected_owner = _provisional_form_torso_owner(namespace, expected_owner_role)
        frame_index = _provisional_form_index(
            section.get("frame_index"), len(frame_keys), f"{section_where}.frame_index"
        )
        if frame_keys[frame_index] != (
            expected_owner,
            PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE,
        ):
            raise ValidationError(
                f"{section_where}.frame_index does not resolve to its identity owner torso control frame"
            )

        section_key = expected_name.replace("-", "_")
        expected_landmark_role = f"form_torso_profile_{section_key}"
        landmark_index = _provisional_form_index(
            section.get("landmark_index"),
            len(landmark_keys),
            f"{section_where}.landmark_index",
        )
        if landmark_keys[landmark_index] != (expected_owner, expected_landmark_role):
            raise ValidationError(
                f"{section_where}.landmark_index does not resolve to the canonical section landmark"
            )
        position = landmark_positions[landmark_index]
        section_y.append(position[1])

        dimension_indices = _object(
            section.get("dimension_indices"), f"{section_where}.dimension_indices"
        )
        _check_fields(
            dimension_indices,
            {"lateral", "anterior", "posterior"},
            f"{section_where}.dimension_indices",
        )
        radii: dict[str, int] = {}
        for axis, role_suffix in PROVISIONAL_FORM_TORSO_PROFILE_RADIUS_AXES:
            dimension_index = _provisional_form_index(
                dimension_indices.get(axis),
                len(dimension_records),
                f"{section_where}.dimension_indices.{axis}",
            )
            expected_role = f"form_torso_profile_{section_key}_{role_suffix}"
            owner, role, value_permille = dimension_records[dimension_index]
            if (owner, role) != (expected_owner, expected_role):
                raise ValidationError(
                    f"{section_where}.dimension_indices.{axis} does not resolve to {expected_role}"
                )
            key = (owner, role)
            consumed_dimension_keys.add(key)
            radii[axis] = value_permille
        source_sections.append(
            {
                "name": expected_name,
                "owner_role": expected_owner_role,
                "position": position,
                "radii": radii,
            }
        )
    if any(section_y[index] >= section_y[index + 1] for index in range(len(section_y) - 1)):
        raise ValidationError(f"{profile_where}.sections landmarks must have strictly increasing y")
    return consumed_dimension_keys, source_sections


def _provisional_form_torso_profile_factors(
    profile_id: str, owner_role: str
) -> tuple[int, int]:
    """Return the fixed lateral and depth factors used by the Rust producer."""

    if profile_id == "neutral-v0":
        return (1_000, 1_000)
    if profile_id == "broad-soft-v0" and owner_role in {"pelvis", "torso"}:
        return (1_200, 1_150)
    if profile_id == "lean-readable-v0":
        return (800, 800)
    if profile_id == "depth-forward-v0" and owner_role == "torso":
        return (1_000, 1_300)
    return (1_000, 1_000)


def _validate_v7_variant_torso_profile(
    value: Any,
    where: str,
    *,
    profile_id: str,
    document: str,
    namespace: str,
    source_sections: list[dict[str, Any]],
) -> None:
    profile = _object(value, where)
    _check_fields(profile, {"format", "source", "provenance", "sections"}, where)
    if profile.get("format") != PROVISIONAL_FORM_TORSO_PROFILE_FORMAT:
        raise ValidationError(
            f"{where}.format must be {PROVISIONAL_FORM_TORSO_PROFILE_FORMAT}"
        )
    if profile.get("source") != "authored_torso_profile":
        raise ValidationError(f"{where}.source must be authored_torso_profile")
    _form_control_provenance(
        profile.get("provenance"), f"{where}.provenance", document, namespace
    )
    sections = _array(profile.get("sections"), f"{where}.sections")
    if len(sections) != len(source_sections):
        raise ValidationError(f"{where}.sections must contain exactly seven sections")
    for index, (raw_section, source_section) in enumerate(zip(sections, source_sections)):
        section_where = f"{where}.sections[{index}]"
        section = _object(raw_section, section_where)
        _check_fields(
            section,
            {
                "source_section_index",
                "name",
                "position",
                "lateral_radius_permille",
                "anterior_radius_permille",
                "posterior_radius_permille",
                "scaling",
                "provenance",
            },
            section_where,
        )
        if (
            type(section.get("source_section_index")) is not int
            or section["source_section_index"] != index
        ):
            raise ValidationError(
                f"{section_where}.source_section_index must equal its stable source index"
            )
        if section.get("name") != source_section["name"]:
            raise ValidationError(f"{section_where}.name does not match its source section")
        position = _form_finite_vector(
            section.get("position"), f"{section_where}.position", 3
        )
        if position != source_section["position"]:
            raise ValidationError(f"{section_where}.position must equal its source landmark")
        lateral_factor, depth_factor = _provisional_form_torso_profile_factors(
            profile_id, source_section["owner_role"]
        )
        expected_factors = {
            "lateral_factor_permille": lateral_factor,
            "anterior_factor_permille": depth_factor,
            "posterior_factor_permille": depth_factor,
        }
        scaling = _object(section.get("scaling"), f"{section_where}.scaling")
        _check_fields(scaling, set(expected_factors), f"{section_where}.scaling")
        for field, expected_factor in expected_factors.items():
            actual_factor = _form_permille(
                scaling.get(field), f"{section_where}.scaling.{field}"
            )
            if actual_factor != expected_factor:
                raise ValidationError(
                    f"{section_where}.scaling.{field} does not match the fixed variant factor"
                )
        factor_by_axis = {
            "lateral": lateral_factor,
            "anterior": depth_factor,
            "posterior": depth_factor,
        }
        for axis, _role_suffix in PROVISIONAL_FORM_TORSO_PROFILE_RADIUS_AXES:
            field = f"{axis}_radius_permille"
            actual_radius = _form_permille(
                section.get(field), f"{section_where}.{field}"
            )
            expected_radius = _form_scaled_display_value(
                source_section["radii"][axis],
                factor_by_axis[axis],
                f"{section_where}.{field}",
            )
            if actual_radius != expected_radius:
                raise ValidationError(
                    f"{section_where}.{field} does not match its indexed source radius and fixed factor"
                )
        _form_control_provenance(
            section.get("provenance"),
            f"{section_where}.provenance",
            document,
            namespace,
        )


def _provisional_form_head_neck_owner(
    namespace: str, role: str
) -> tuple[str, tuple[str, ...], str, str]:
    return (namespace, (), "part", role)


def _validate_v8_authored_head_neck_profile(
    obj: dict[str, Any],
    where: str,
    *,
    document: str,
    namespace: str,
    authored_dimension_values: dict[
        tuple[tuple[str, tuple[str, ...], str, str], str], int
    ],
    include_v9_controls: bool = False,
    include_v10_controls: bool = False,
    include_v11_controls: bool = False,
) -> tuple[
    set[tuple[tuple[str, tuple[str, ...], str, str], str]],
    list[dict[str, Any]],
]:
    """Validate v8's complete control inventory and head/neck profile index."""

    frames = _array(obj.get("authored_frames"), f"{where}.authored_frames")
    expected_frame_keys = {
        (
            _provisional_form_upper_arm_owner(namespace, side),
            PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE,
        )
        for side in ("left", "right")
    }
    expected_frame_keys.update(
        (
            _provisional_form_torso_owner(namespace, role),
            PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE,
        )
        for role in ("pelvis", "torso")
    )
    expected_frame_keys.update(
        (
            _provisional_form_head_neck_owner(namespace, role),
            PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
        )
        for role in ("neck", "head")
    )
    if include_v9_controls:
        expected_frame_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, role),
                PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE,
            )
            for side in PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES
            for role in {"upper_arm", "forearm"}
        )
    if include_v10_controls:
        expected_frame_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, role),
                PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE,
            )
            for side in PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES
            for role in {"thigh", "shin"}
        )
    if include_v11_controls:
        expected_frame_keys.update(
            (
                _provisional_form_foot_owner(namespace, side),
                PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE,
            )
            for side in PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES
        )
    contract_label = "v11" if include_v11_controls else "v10" if include_v10_controls else "v9" if include_v9_controls else "v8"
    if len(frames) != len(expected_frame_keys):
        expected_frame_count = 16 if include_v11_controls else 14 if include_v10_controls else 10 if include_v9_controls else 6
        raise ValidationError(
            f"{where}.authored_frames must contain exactly {expected_frame_count} {contract_label} control frames"
        )
    frame_keys: list[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = []
    seen_frame_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    for index, raw_frame in enumerate(frames):
        frame_where = f"{where}.authored_frames[{index}]"
        frame = _object(raw_frame, frame_where)
        _check_fields(frame, {"owner", "role", "transform", "provenance"}, frame_where)
        owner = _form_address(frame.get("owner"), f"{frame_where}.owner")
        role = _string(frame.get("role"), f"{frame_where}.role", max_len=256)
        key = (owner, role)
        frame_keys.append(key)
        if key in seen_frame_keys:
            raise ValidationError(f"{where}.authored_frames contains duplicate owner/role keys")
        if key not in expected_frame_keys:
            raise ValidationError(f"{frame_where} is not a {contract_label} control frame")
        _form_control_provenance(
            frame.get("provenance"), f"{frame_where}.provenance", document, namespace
        )
        transform = _object(frame.get("transform"), f"{frame_where}.transform")
        _check_fields(transform, {"translation", "rotation_xyzw"}, f"{frame_where}.transform")
        translation = _form_finite_vector(
            transform.get("translation"), f"{frame_where}.transform.translation", 3
        )
        rotation = _form_finite_vector(
            transform.get("rotation_xyzw"), f"{frame_where}.transform.rotation_xyzw", 4
        )
        if translation != [0, 0, 0] or rotation != [0, 0, 0, 1]:
            raise ValidationError(f"{frame_where} must use the identity rigid transform")
        seen_frame_keys.add(key)
    if set(frame_keys) != expected_frame_keys:
        raise ValidationError(f"{where}.authored_frames must contain the exact {contract_label} control inventory")
    if frame_keys != sorted(frame_keys):
        raise ValidationError(f"{where}.authored_frames must use stable owner/role order")

    landmarks = _array(obj.get("authored_landmarks"), f"{where}.authored_landmarks")
    expected_landmark_keys = {
        (
            _provisional_form_upper_arm_owner(namespace, side),
            role,
        )
        for side in ("left", "right")
        for role in PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES
    }
    expected_landmark_keys.update(
        (
            _provisional_form_torso_owner(namespace, owner_role),
            f"form_torso_profile_{section_name.replace('-', '_')}",
        )
        for section_name, owner_role in zip(
            PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES,
            PROVISIONAL_FORM_TORSO_PROFILE_OWNER_ROLES,
        )
    )
    expected_landmark_keys.update(
        (
            _provisional_form_head_neck_owner(namespace, owner_role),
            f"form_head_neck_profile_{section_name.replace('-', '_')}",
        )
        for section_name, owner_role in zip(
            PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES,
            PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES,
        )
    )
    if include_v9_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, owner_role),
                f"form_arm_profile_{section_name.replace('-', '_')}",
            )
            for side in PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES
            for section_name, owner_role in zip(
                PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES,
            )
        )
    if include_v10_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_arm_owner(namespace, side, owner_role),
                f"form_leg_profile_{section_name.replace('-', '_')}",
            )
            for side in PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES
            for section_name, owner_role in zip(
                PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES,
            )
        )
    if include_v11_controls:
        expected_landmark_keys.update(
            (
                _provisional_form_foot_owner(namespace, side),
                f"form_foot_profile_{section_name}",
            )
            for side in PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES
            for section_name in PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES
        )
    expected_landmark_count = 43 if include_v11_controls else 39 if include_v10_controls else 29 if include_v9_controls else 19
    if len(landmarks) != len(expected_landmark_keys):
        raise ValidationError(
            f"{where}.authored_landmarks must contain exactly {expected_landmark_count} {contract_label} control landmarks"
        )
    landmark_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    seen_landmark_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    for index, raw_landmark in enumerate(landmarks):
        landmark_where = f"{where}.authored_landmarks[{index}]"
        landmark = _object(raw_landmark, landmark_where)
        _check_fields(
            landmark,
            {"owner", "role", "frame", "position", "provenance"},
            landmark_where,
        )
        owner = _form_address(landmark.get("owner"), f"{landmark_where}.owner")
        role = _string(landmark.get("role"), f"{landmark_where}.role", max_len=256)
        key = (owner, role)
        landmark_keys.append(key)
        if key in seen_landmark_keys:
            raise ValidationError(f"{where}.authored_landmarks contains duplicate owner/role keys")
        if key not in expected_landmark_keys:
            raise ValidationError(f"{landmark_where} is not a {contract_label} control landmark")
        _form_control_provenance(
            landmark.get("provenance"), f"{landmark_where}.provenance", document, namespace
        )
        frame = _object(landmark.get("frame"), f"{landmark_where}.frame")
        _check_fields(frame, {"owner", "role"}, f"{landmark_where}.frame")
        frame_owner = _form_address(frame.get("owner"), f"{landmark_where}.frame.owner")
        if include_v11_controls and role.startswith("form_foot_profile_"):
            expected_frame_role = PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE
        elif include_v9_controls and role.startswith("form_arm_profile_"):
            expected_frame_role = PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE
        elif include_v10_controls and role.startswith("form_leg_profile_"):
            expected_frame_role = PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
        elif owner[3] in {"pelvis", "torso"}:
            expected_frame_role = PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE
        elif owner[3] in {"neck", "head"}:
            expected_frame_role = PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE
        else:
            expected_frame_role = PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE
        if frame_owner != owner or frame.get("role") != expected_frame_role:
            raise ValidationError(f"{landmark_where}.frame must reference its same-owner control frame")
        if (frame_owner, expected_frame_role) not in seen_frame_keys:
            raise ValidationError(f"{landmark_where}.frame references an unlisted authored frame")
        position = _form_finite_vector(landmark.get("position"), f"{landmark_where}.position", 3)
        if any(abs(component) > PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND for component in position):
            raise ValidationError(
                f"{landmark_where}.position components must be within +/-{PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND}"
            )
        if owner[3] in {"pelvis", "torso"} and (position[0] != 0 or position[2] != 0):
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,0] point")
        if owner[3] in {"neck", "head"} and position[0] != 0:
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,z] point")
        if include_v9_controls and role.startswith("form_arm_profile_") and (
            owner[3] not in {"upper_arm", "forearm"} or position[0] != 0 or position[2] != 0
        ):
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,0] point")
        if include_v10_controls and role.startswith("form_leg_profile_") and (
            owner[3] not in {"thigh", "shin"} or position[0] != 0 or position[2] != 0
        ):
            raise ValidationError(f"{landmark_where}.position must be an axial [0,y,0] point")
        if include_v10_controls and role.startswith("form_leg_profile_") and not (
            PROVISIONAL_FORM_LEG_PROFILE_Y_MIN <= position[1] <= PROVISIONAL_FORM_LEG_PROFILE_Y_MAX
        ):
            raise ValidationError(
                f"{landmark_where}.position y must be in inclusive "
                f"[{PROVISIONAL_FORM_LEG_PROFILE_Y_MIN}, {PROVISIONAL_FORM_LEG_PROFILE_Y_MAX}]"
            )
        if include_v11_controls and role.startswith("form_foot_profile_") and (
            owner[3] != "foot"
            or position[0] != 0
            or not PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN <= position[1] <= PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX
            or not PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN <= position[2] <= PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX
        ):
            raise ValidationError(
                f"{landmark_where}.position must be [0,y,z] with y in inclusive "
                f"[{PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN}, {PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX}] "
                f"and z in inclusive [{PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN}, {PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX}]"
            )
        seen_landmark_keys.add(key)
    if set(landmark_keys) != expected_landmark_keys:
        raise ValidationError(f"{where}.authored_landmarks must contain the exact {contract_label} control inventory")
    if landmark_keys != sorted(landmark_keys):
        raise ValidationError(f"{where}.authored_landmarks must use stable owner/role order")

    dimensions = _array(obj.get("authored_dimensions"), f"{where}.authored_dimensions")
    dimension_records: list[
        tuple[tuple[str, tuple[str, ...], str, str], str, int]
    ] = []
    for index, raw_dimension in enumerate(dimensions):
        dimension_where = f"{where}.authored_dimensions[{index}]"
        dimension = _object(raw_dimension, dimension_where)
        owner = _form_address(dimension.get("owner"), f"{dimension_where}.owner")
        role = _string(dimension.get("role"), f"{dimension_where}.role", max_len=256)
        dimension_records.append((owner, role, authored_dimension_values[(owner, role)]))

    profile_where = f"{where}.authored_head_neck_profile"
    profile = _object(obj.get("authored_head_neck_profile"), profile_where)
    _check_fields(profile, {"format", "provenance", "sections", "connections"}, profile_where)
    if profile.get("format") != PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT:
        raise ValidationError(
            f"{profile_where}.format must be {PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT}"
        )
    _form_control_provenance(
        profile.get("provenance"), f"{profile_where}.provenance", document, namespace
    )
    connections = _array(profile.get("connections"), f"{profile_where}.connections")
    if len(connections) != len(PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS):
        raise ValidationError(f"{profile_where}.connections must contain exactly seven records")
    for index, (raw_connection, expected) in enumerate(
        zip(connections, PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS)
    ):
        connection_where = f"{profile_where}.connections[{index}]"
        connection = _object(raw_connection, connection_where)
        _check_fields(
            connection,
            {"name", "from_section_index", "to_section_index", "route"},
            connection_where,
        )
        if (
            connection.get("name"),
            connection.get("from_section_index"),
            connection.get("to_section_index"),
            connection.get("route"),
        ) != expected:
            raise ValidationError(f"{connection_where} does not match the exact v8 connection route")

    sections = _array(profile.get("sections"), f"{profile_where}.sections")
    if len(sections) != len(PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES):
        raise ValidationError(f"{profile_where}.sections must contain exactly eight sections")
    consumed_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    route_values: list[list[float | int]] = [[], [], []]
    source_sections: list[dict[str, Any]] = []
    for index, (raw_section, expected_name, expected_owner_role) in enumerate(
        zip(
            sections,
            PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES,
            PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES,
        )
    ):
        section_where = f"{profile_where}.sections[{index}]"
        section = _object(raw_section, section_where)
        _check_fields(
            section,
            {
                "name",
                "frame_index",
                "landmark_index",
                "dimension_indices",
                "provenance",
                "section_index",
            },
            section_where,
        )
        if section.get("name") != expected_name:
            raise ValidationError(f"{section_where}.name is not in the required stable order")
        if type(section.get("section_index")) is not int or section["section_index"] != index:
            raise ValidationError(f"{section_where}.section_index must equal its stable array index")
        _form_control_provenance(
            section.get("provenance"), f"{section_where}.provenance", document, namespace
        )
        owner = _provisional_form_head_neck_owner(namespace, expected_owner_role)
        frame_index = _provisional_form_index(
            section.get("frame_index"), len(frame_keys), f"{section_where}.frame_index"
        )
        if frame_keys[frame_index] != (
            owner,
            PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
        ):
            raise ValidationError(
                f"{section_where}.frame_index does not resolve to its identity owner head/neck control frame"
            )
        section_key = expected_name.replace("-", "_")
        expected_landmark_role = f"form_head_neck_profile_{section_key}"
        landmark_index = _provisional_form_index(
            section.get("landmark_index"), len(landmark_keys), f"{section_where}.landmark_index"
        )
        if landmark_keys[landmark_index] != (owner, expected_landmark_role):
            raise ValidationError(
                f"{section_where}.landmark_index does not resolve to the canonical section landmark"
            )
        position = _form_finite_vector(
            landmarks[landmark_index]["position"],
            f"{section_where}.landmark.position",
            3,
        )
        if index <= 1:
            route_values[0].append(position[1])
        if 2 <= index <= 4:
            route_values[1].append(position[1])
        if index == 3 or index >= 5:
            route_values[2].append(position[2])

        dimension_indices = _object(
            section.get("dimension_indices"), f"{section_where}.dimension_indices"
        )
        _check_fields(
            dimension_indices,
            {axis for axis, _role_suffix in PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES},
            f"{section_where}.dimension_indices",
        )
        radii: dict[str, int] = {}
        for axis, role_suffix in PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES:
            dimension_index = _provisional_form_index(
                dimension_indices.get(axis),
                len(dimension_records),
                f"{section_where}.dimension_indices.{axis}",
            )
            expected_role = f"form_head_neck_profile_{section_key}_{role_suffix}"
            owner_at_index, role_at_index, value_permille = dimension_records[dimension_index]
            if (owner_at_index, role_at_index) != (owner, expected_role):
                raise ValidationError(
                    f"{section_where}.dimension_indices.{axis} does not resolve to {expected_role}"
                )
            key = (owner_at_index, role_at_index)
            consumed_dimension_keys.add(key)
            radii[axis] = value_permille
        source_sections.append(
            {
                "name": expected_name,
                "owner_role": expected_owner_role,
                "position": position,
                "radii": radii,
            }
        )
    for route_index, values in enumerate(route_values):
        if any(values[index] >= values[index + 1] for index in range(len(values) - 1)):
            axis = "z" if route_index == 2 else "y"
            raise ValidationError(
                f"{profile_where}.sections landmarks must have strictly increasing {axis}"
            )
    return consumed_dimension_keys, source_sections


def _provisional_form_head_neck_profile_factors(
    profile_id: str, owner_role: str
) -> tuple[int, int, int]:
    if owner_role == "head":
        if profile_id == "neutral-v0":
            return (1_000, 1_000, 1_000)
        if profile_id == "broad-soft-v0":
            return (1_200, 1_000, 1_150)
        if profile_id == "lean-readable-v0":
            return (800, 1_000, 800)
        if profile_id == "depth-forward-v0":
            return (1_000, 1_000, 1_300)
        return (1_000, 1_000, 1_000)
    factor = 1_150 if profile_id == "broad-soft-v0" else 800 if profile_id == "lean-readable-v0" else 1_000
    return (factor, factor, factor)


def _validate_v8_variant_head_neck_profile(
    value: Any,
    where: str,
    *,
    profile_id: str,
    document: str,
    namespace: str,
    source_sections: list[dict[str, Any]],
) -> None:
    profile = _object(value, where)
    _check_fields(profile, {"format", "source", "provenance", "sections", "connections"}, where)
    if profile.get("format") != PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT:
        raise ValidationError(f"{where}.format must be {PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT}")
    if profile.get("source") != "authored_head_neck_profile":
        raise ValidationError(f"{where}.source must be authored_head_neck_profile")
    _form_control_provenance(profile.get("provenance"), f"{where}.provenance", document, namespace)
    connections = _array(profile.get("connections"), f"{where}.connections")
    if len(connections) != len(PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS):
        raise ValidationError(f"{where}.connections must contain exactly seven records")
    for index, (raw_connection, expected) in enumerate(
        zip(connections, PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS)
    ):
        connection_where = f"{where}.connections[{index}]"
        connection = _object(raw_connection, connection_where)
        _check_fields(connection, {"name", "from_section_index", "to_section_index", "route"}, connection_where)
        if (
            connection.get("name"),
            connection.get("from_section_index"),
            connection.get("to_section_index"),
            connection.get("route"),
        ) != expected:
            raise ValidationError(f"{connection_where} does not match the exact v8 connection route")
    sections = _array(profile.get("sections"), f"{where}.sections")
    if len(sections) != len(source_sections):
        raise ValidationError(f"{where}.sections must contain exactly eight sections")
    for index, (raw_section, source_section) in enumerate(zip(sections, source_sections)):
        section_where = f"{where}.sections[{index}]"
        section = _object(raw_section, section_where)
        _check_fields(
            section,
            {
                "source_section_index",
                "name",
                "position",
                "lateral_radius_permille",
                "up_radius_permille",
                "forward_radius_permille",
                "scaling",
                "provenance",
            },
            section_where,
        )
        if type(section.get("source_section_index")) is not int or section["source_section_index"] != index:
            raise ValidationError(f"{section_where}.source_section_index must equal its stable source index")
        if section.get("name") != source_section["name"]:
            raise ValidationError(f"{section_where}.name does not match its source section")
        position = _form_finite_vector(section.get("position"), f"{section_where}.position", 3)
        if position != source_section["position"]:
            raise ValidationError(f"{section_where}.position must equal its indexed source landmark")
        lateral_factor, up_factor, forward_factor = _provisional_form_head_neck_profile_factors(
            profile_id, source_section["owner_role"]
        )
        expected_scaling = {
            "lateral_factor_permille": lateral_factor,
            "up_factor_permille": up_factor,
            "forward_factor_permille": forward_factor,
        }
        scaling = _object(section.get("scaling"), f"{section_where}.scaling")
        _check_fields(scaling, set(expected_scaling), f"{section_where}.scaling")
        for field, expected_factor in expected_scaling.items():
            if _form_permille(scaling.get(field), f"{section_where}.scaling.{field}") != expected_factor:
                raise ValidationError(f"{section_where}.scaling.{field} does not match the fixed variant factor")
        for axis, factor in zip(
            ("lateral", "up", "forward"),
            (lateral_factor, up_factor, forward_factor),
        ):
            field = f"{axis}_radius_permille"
            expected_radius = _form_scaled_display_value(
                source_section["radii"][axis], factor, f"{section_where}.{field}"
            )
            if _form_permille(section.get(field), f"{section_where}.{field}") != expected_radius:
                raise ValidationError(
                    f"{section_where}.{field} does not match its indexed source radius and fixed factor"
                )
        _form_control_provenance(section.get("provenance"), f"{section_where}.provenance", document, namespace)


def _provisional_form_arm_profile_factors(profile_id: str) -> tuple[int, int, int]:
    if profile_id == "broad-soft-v0":
        return (1_150, 1_000, 1_150)
    if profile_id == "lean-readable-v0":
        return (800, 1_000, 800)
    if profile_id == "depth-forward-v0":
        return (1_000, 1_000, 1_300)
    return (1_000, 1_000, 1_000)


def _validate_v9_authored_arm_profile(
    obj: dict[str, Any],
    where: str,
    *,
    document: str,
    namespace: str,
    authored_dimension_values: dict[
        tuple[tuple[str, tuple[str, ...], str, str], str], int
    ],
) -> tuple[
    set[tuple[tuple[str, tuple[str, ...], str, str], str]],
    list[dict[str, Any]],
]:
    """Validate v9's closed bilateral source profile and exact indexed lineage."""

    frames = _array(obj.get("authored_frames"), f"{where}.authored_frames")
    frame_keys = [
        (
            _form_address(frame.get("owner"), f"{where}.authored_frames[{index}].owner"),
            _string(frame.get("role"), f"{where}.authored_frames[{index}].role", max_len=256),
        )
        for index, frame in enumerate(frames)
    ]
    landmarks = _array(obj.get("authored_landmarks"), f"{where}.authored_landmarks")
    landmark_keys = [
        (
            _form_address(landmark.get("owner"), f"{where}.authored_landmarks[{index}].owner"),
            _string(landmark.get("role"), f"{where}.authored_landmarks[{index}].role", max_len=256),
        )
        for index, landmark in enumerate(landmarks)
    ]
    dimensions = _array(obj.get("authored_dimensions"), f"{where}.authored_dimensions")
    dimension_records = [
        (
            _form_address(dimension.get("owner"), f"{where}.authored_dimensions[{index}].owner"),
            _string(dimension.get("role"), f"{where}.authored_dimensions[{index}].role", max_len=256),
            authored_dimension_values[
                (
                    _form_address(dimension.get("owner"), f"{where}.authored_dimensions[{index}].owner"),
                    _string(dimension.get("role"), f"{where}.authored_dimensions[{index}].role", max_len=256),
                )
            ],
        )
        for index, dimension in enumerate(dimensions)
    ]

    profile_where = f"{where}.authored_arm_profile"
    profile = _object(obj.get("authored_arm_profile"), profile_where)
    _check_fields(profile, {"format", "provenance", "sides"}, profile_where)
    if profile.get("format") != PROVISIONAL_FORM_ARM_PROFILE_FORMAT:
        raise ValidationError(
            f"{profile_where}.format must be {PROVISIONAL_FORM_ARM_PROFILE_FORMAT}"
        )
    _form_control_provenance(
        profile.get("provenance"), f"{profile_where}.provenance", document, namespace
    )
    sides = _array(profile.get("sides"), f"{profile_where}.sides")
    if len(sides) != len(PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES):
        raise ValidationError(
            f"{profile_where}.sides must contain exactly two sides in left/right order"
        )

    consumed_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    source_sides: list[dict[str, Any]] = []
    axis_indices = {"lateral": 0, "up": 1, "forward": 2}
    for side_index, (raw_side, expected_side) in enumerate(
        zip(sides, PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES)
    ):
        side_where = f"{profile_where}.sides[{side_index}]"
        side = _object(raw_side, side_where)
        _check_fields(side, {"side", "sections"}, side_where)
        if side.get("side") != expected_side:
            raise ValidationError(f"{side_where}.side must be {expected_side}")
        sections = _array(side.get("sections"), f"{side_where}.sections")
        if len(sections) != len(PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES):
            raise ValidationError(f"{side_where}.sections must contain exactly five sections")
        source_sections: list[dict[str, Any]] = []
        for section_index, (raw_section, expected_name, owner_role) in enumerate(
            zip(
                sections,
                PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES,
            )
        ):
            section_where = f"{side_where}.sections[{section_index}]"
            section = _object(raw_section, section_where)
            _check_fields(
                section,
                {
                    "name",
                    "frame_index",
                    "landmark_index",
                    "dimension_indices",
                    "provenance",
                    "section_index",
                },
                section_where,
            )
            if section.get("name") != expected_name:
                raise ValidationError(f"{section_where}.name is not in the required stable order")
            if type(section.get("section_index")) is not int or section["section_index"] != section_index:
                raise ValidationError(f"{section_where}.section_index must equal its stable array index")
            _form_control_provenance(
                section.get("provenance"), f"{section_where}.provenance", document, namespace
            )
            owner = _provisional_form_arm_owner(namespace, expected_side, owner_role)
            frame_index = _provisional_form_index(
                section.get("frame_index"), len(frame_keys), f"{section_where}.frame_index"
            )
            if frame_keys[frame_index] != (owner, PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE):
                raise ValidationError(
                    f"{section_where}.frame_index does not resolve to its identity owner arm profile control frame"
                )
            section_key = expected_name.replace("-", "_")
            expected_landmark_role = f"form_arm_profile_{section_key}"
            landmark_index = _provisional_form_index(
                section.get("landmark_index"), len(landmark_keys), f"{section_where}.landmark_index"
            )
            if landmark_keys[landmark_index] != (owner, expected_landmark_role):
                raise ValidationError(
                    f"{section_where}.landmark_index does not resolve to the canonical arm profile landmark"
                )
            position = _form_finite_vector(
                landmarks[landmark_index].get("position"),
                f"{section_where}.landmark.position",
                3,
            )
            if (
                position[0] != 0
                or position[2] != 0
                or any(abs(component) > PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND for component in position)
            ):
                raise ValidationError(f"{section_where}.landmark.position must be an axial [0,y,0] point")
            dimension_indices = _object(
                section.get("dimension_indices"), f"{section_where}.dimension_indices"
            )
            _check_fields(
                dimension_indices,
                {axis for axis, _role_suffix in PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES},
                f"{section_where}.dimension_indices",
            )
            radii: dict[str, int] = {}
            for axis, role_suffix in PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES:
                dimension_index = _provisional_form_index(
                    dimension_indices.get(axis),
                    len(dimension_records),
                    f"{section_where}.dimension_indices.{axis}",
                )
                expected_role = f"form_arm_profile_{section_key}_{role_suffix}"
                owner_at_index, role_at_index, value_permille = dimension_records[dimension_index]
                if (owner_at_index, role_at_index) != (owner, expected_role):
                    raise ValidationError(
                        f"{section_where}.dimension_indices.{axis} does not resolve to {expected_role}"
                    )
                for factor in (
                    _provisional_form_arm_profile_factors(profile_id)
                    for profile_id in PROVISIONAL_FORM_VARIANT_IDS
                ):
                    _form_scaled_display_value(
                        value_permille,
                        factor[axis_indices[axis]],
                        f"{section_where}.dimension_indices.{axis}",
                    )
                key = (owner_at_index, role_at_index)
                consumed_dimension_keys.add(key)
                radii[axis] = value_permille
            source_sections.append(
                {
                    "name": expected_name,
                    "owner_role": owner_role,
                    "position": position,
                    "radii": radii,
                }
            )
        source_sides.append({"side": expected_side, "sections": source_sections})
    return consumed_dimension_keys, source_sides


def _validate_v9_variant_arm_profile(
    value: Any,
    where: str,
    *,
    profile_id: str,
    document: str,
    namespace: str,
    source_sides: list[dict[str, Any]],
) -> None:
    profile = _object(value, where)
    _check_fields(profile, {"format", "source", "provenance", "sides"}, where)
    if profile.get("format") != PROVISIONAL_FORM_ARM_PROFILE_FORMAT:
        raise ValidationError(f"{where}.format must be {PROVISIONAL_FORM_ARM_PROFILE_FORMAT}")
    if profile.get("source") != "authored_arm_profile":
        raise ValidationError(f"{where}.source must be authored_arm_profile")
    _form_control_provenance(profile.get("provenance"), f"{where}.provenance", document, namespace)
    sides = _array(profile.get("sides"), f"{where}.sides")
    if len(sides) != len(source_sides):
        raise ValidationError(f"{where}.sides must contain exactly two source-indexed sides")
    factors = _provisional_form_arm_profile_factors(profile_id)
    for side_index, (raw_side, source_side) in enumerate(zip(sides, source_sides)):
        side_where = f"{where}.sides[{side_index}]"
        side = _object(raw_side, side_where)
        _check_fields(side, {"side", "sections"}, side_where)
        if side.get("side") != source_side["side"]:
            raise ValidationError(f"{side_where}.side does not match its indexed source side")
        sections = _array(side.get("sections"), f"{side_where}.sections")
        if len(sections) != len(source_side["sections"]):
            raise ValidationError(f"{side_where}.sections must contain exactly five source-indexed sections")
        for section_index, (raw_section, source_section) in enumerate(
            zip(sections, source_side["sections"])
        ):
            section_where = f"{side_where}.sections[{section_index}]"
            section = _object(raw_section, section_where)
            _check_fields(
                section,
                {
                    "source_section_index",
                    "name",
                    "position",
                    "lateral_radius_permille",
                    "up_radius_permille",
                    "forward_radius_permille",
                    "scaling",
                    "provenance",
                },
                section_where,
            )
            if type(section.get("source_section_index")) is not int or section["source_section_index"] != section_index:
                raise ValidationError(f"{section_where}.source_section_index must equal its stable source index")
            if section.get("name") != source_section["name"]:
                raise ValidationError(f"{section_where}.name does not match its indexed source section")
            position = _form_finite_vector(section.get("position"), f"{section_where}.position", 3)
            if position != source_section["position"]:
                raise ValidationError(f"{section_where}.position must equal its indexed source landmark")
            expected_scaling = {
                "lateral_factor_permille": factors[0],
                "up_factor_permille": factors[1],
                "forward_factor_permille": factors[2],
            }
            scaling = _object(section.get("scaling"), f"{section_where}.scaling")
            _check_fields(scaling, set(expected_scaling), f"{section_where}.scaling")
            for field, expected_factor in expected_scaling.items():
                if _form_permille(scaling.get(field), f"{section_where}.scaling.{field}") != expected_factor:
                    raise ValidationError(f"{section_where}.scaling.{field} does not match the fixed variant factor")
            for axis, _role_suffix in PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES:
                field = f"{axis}_radius_permille"
                expected_radius = _form_scaled_display_value(
                    source_section["radii"][axis],
                    factors[{"lateral": 0, "up": 1, "forward": 2}[axis]],
                    f"{section_where}.{field}",
                )
                if _form_permille(section.get(field), f"{section_where}.{field}") != expected_radius:
                    raise ValidationError(
                        f"{section_where}.{field} does not match its indexed source radius and fixed factor"
                    )
            _form_control_provenance(section.get("provenance"), f"{section_where}.provenance", document, namespace)


def _provisional_form_leg_profile_factors(profile_id: str) -> tuple[int, int, int]:
    return _provisional_form_arm_profile_factors(profile_id)


def _validate_v10_authored_leg_profile(
    obj: dict[str, Any],
    where: str,
    *,
    document: str,
    namespace: str,
    authored_dimension_values: dict[
        tuple[tuple[str, tuple[str, ...], str, str], str], int
    ],
) -> tuple[
    set[tuple[tuple[str, tuple[str, ...], str, str], str]],
    list[dict[str, Any]],
]:
    """Validate v10's closed bilateral leg profile and exact indexed lineage."""

    frames = _array(obj.get("authored_frames"), f"{where}.authored_frames")
    landmarks = _array(obj.get("authored_landmarks"), f"{where}.authored_landmarks")
    dimensions = _array(obj.get("authored_dimensions"), f"{where}.authored_dimensions")
    leg_frame_count = sum(
        isinstance(frame, dict) and frame.get("role") == PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
        for frame in frames
    )
    leg_landmark_count = sum(
        isinstance(landmark, dict) and str(landmark.get("role", "")).startswith("form_leg_profile_")
        for landmark in landmarks
    )
    if leg_frame_count != 4 or leg_landmark_count != 10:
        raise ValidationError(
            f"{where} must contain exactly four leg profile frames and ten leg profile landmarks"
        )

    frame_keys = [
        (
            _form_address(frame.get("owner"), f"{where}.authored_frames[{index}].owner"),
            _string(frame.get("role"), f"{where}.authored_frames[{index}].role", max_len=256),
        )
        for index, frame in enumerate(frames)
    ]
    landmark_keys = [
        (
            _form_address(landmark.get("owner"), f"{where}.authored_landmarks[{index}].owner"),
            _string(landmark.get("role"), f"{where}.authored_landmarks[{index}].role", max_len=256),
        )
        for index, landmark in enumerate(landmarks)
    ]
    dimension_records = [
        (
            _form_address(dimension.get("owner"), f"{where}.authored_dimensions[{index}].owner"),
            _string(dimension.get("role"), f"{where}.authored_dimensions[{index}].role", max_len=256),
            authored_dimension_values[
                (
                    _form_address(dimension.get("owner"), f"{where}.authored_dimensions[{index}].owner"),
                    _string(dimension.get("role"), f"{where}.authored_dimensions[{index}].role", max_len=256),
                )
            ],
        )
        for index, dimension in enumerate(dimensions)
    ]

    profile_where = f"{where}.authored_leg_profile"
    profile = _object(obj.get("authored_leg_profile"), profile_where)
    _check_fields(profile, {"format", "provenance", "sides"}, profile_where)
    if profile.get("format") != PROVISIONAL_FORM_LEG_PROFILE_FORMAT:
        raise ValidationError(
            f"{profile_where}.format must be {PROVISIONAL_FORM_LEG_PROFILE_FORMAT}"
        )
    _form_control_provenance(
        profile.get("provenance"), f"{profile_where}.provenance", document, namespace
    )
    sides = _array(profile.get("sides"), f"{profile_where}.sides")
    if len(sides) != len(PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES):
        raise ValidationError(
            f"{profile_where}.sides must contain exactly two sides in left/right order"
        )

    expected_leg_dimension_keys = {
        (
            _provisional_form_arm_owner(namespace, side, owner_role),
            f"form_leg_profile_{section_name.replace('-', '_')}_{role_suffix}",
        )
        for side in PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES
        for section_name, owner_role in zip(
            PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES,
            PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES,
        )
        for _axis, role_suffix in PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES
    }
    actual_leg_dimension_keys = {
        key for key in authored_dimension_values if key[1].startswith("form_leg_profile_")
    }
    if actual_leg_dimension_keys != expected_leg_dimension_keys:
        raise ValidationError(
            f"{where}.authored_dimensions must contain exactly thirty leg profile radius dimensions"
        )

    consumed_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    source_sides: list[dict[str, Any]] = []
    axis_indices = {"lateral": 0, "up": 1, "forward": 2}
    for side_index, (raw_side, expected_side) in enumerate(
        zip(sides, PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES)
    ):
        side_where = f"{profile_where}.sides[{side_index}]"
        side = _object(raw_side, side_where)
        _check_fields(side, {"side", "sections"}, side_where)
        if side.get("side") != expected_side:
            raise ValidationError(f"{side_where}.side must be {expected_side}")
        sections = _array(side.get("sections"), f"{side_where}.sections")
        if len(sections) != len(PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES):
            raise ValidationError(f"{side_where}.sections must contain exactly five sections")
        source_sections: list[dict[str, Any]] = []
        previous_owner: tuple[str, tuple[str, ...], str, str] | None = None
        previous_y: int | float | None = None
        for section_index, (raw_section, expected_name, owner_role) in enumerate(
            zip(
                sections,
                PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES,
                PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES,
            )
        ):
            section_where = f"{side_where}.sections[{section_index}]"
            section = _object(raw_section, section_where)
            _check_fields(
                section,
                {
                    "name",
                    "frame_index",
                    "landmark_index",
                    "dimension_indices",
                    "provenance",
                    "section_index",
                },
                section_where,
            )
            if section.get("name") != expected_name:
                raise ValidationError(f"{section_where}.name is not in the required stable order")
            if type(section.get("section_index")) is not int or section["section_index"] != section_index:
                raise ValidationError(f"{section_where}.section_index must equal its stable array index")
            _form_control_provenance(
                section.get("provenance"), f"{section_where}.provenance", document, namespace
            )
            owner = _provisional_form_arm_owner(namespace, expected_side, owner_role)
            frame_index = _provisional_form_index(
                section.get("frame_index"), len(frame_keys), f"{section_where}.frame_index"
            )
            if frame_keys[frame_index] != (owner, PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE):
                raise ValidationError(
                    f"{section_where}.frame_index does not resolve to its identity owner leg profile control frame"
                )
            section_key = expected_name.replace("-", "_")
            expected_landmark_role = f"form_leg_profile_{section_key}"
            landmark_index = _provisional_form_index(
                section.get("landmark_index"), len(landmark_keys), f"{section_where}.landmark_index"
            )
            if landmark_keys[landmark_index] != (owner, expected_landmark_role):
                raise ValidationError(
                    f"{section_where}.landmark_index does not resolve to the canonical leg profile landmark"
                )
            position = _form_finite_vector(
                landmarks[landmark_index].get("position"),
                f"{section_where}.landmark.position",
                3,
            )
            if (
                position[0] != 0
                or position[2] != 0
                or any(abs(component) > PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND for component in position)
            ):
                raise ValidationError(f"{section_where}.landmark.position must be an axial [0,y,0] point")
            if not (
                PROVISIONAL_FORM_LEG_PROFILE_Y_MIN
                <= position[1]
                <= PROVISIONAL_FORM_LEG_PROFILE_Y_MAX
            ):
                raise ValidationError(
                    f"{section_where}.landmark.position y must be in inclusive "
                    f"[{PROVISIONAL_FORM_LEG_PROFILE_Y_MIN}, {PROVISIONAL_FORM_LEG_PROFILE_Y_MAX}]"
                )
            if previous_owner == owner and previous_y is not None and position[1] >= previous_y:
                raise ValidationError(
                    f"{section_where}.landmark.position must be strictly ordered toward the distal end within each Part frame"
                )
            previous_owner = owner
            previous_y = position[1]
            dimension_indices = _object(
                section.get("dimension_indices"), f"{section_where}.dimension_indices"
            )
            _check_fields(
                dimension_indices,
                {axis for axis, _role_suffix in PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES},
                f"{section_where}.dimension_indices",
            )
            radii: dict[str, int] = {}
            for axis, role_suffix in PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES:
                dimension_index = _provisional_form_index(
                    dimension_indices.get(axis),
                    len(dimension_records),
                    f"{section_where}.dimension_indices.{axis}",
                )
                expected_role = f"form_leg_profile_{section_key}_{role_suffix}"
                owner_at_index, role_at_index, value_permille = dimension_records[dimension_index]
                if (owner_at_index, role_at_index) != (owner, expected_role):
                    raise ValidationError(
                        f"{section_where}.dimension_indices.{axis} does not resolve to {expected_role}"
                    )
                for profile_id in PROVISIONAL_FORM_VARIANT_IDS:
                    _form_scaled_display_value(
                        value_permille,
                        _provisional_form_leg_profile_factors(profile_id)[axis_indices[axis]],
                        f"{section_where}.dimension_indices.{axis}",
                    )
                key = (owner_at_index, role_at_index)
                consumed_dimension_keys.add(key)
                radii[axis] = value_permille
            source_sections.append(
                {
                    "name": expected_name,
                    "owner_role": owner_role,
                    "position": position,
                    "radii": radii,
                }
            )
        source_sides.append({"side": expected_side, "sections": source_sections})
    return consumed_dimension_keys, source_sides


def _validate_v10_variant_leg_profile(
    value: Any,
    where: str,
    *,
    profile_id: str,
    document: str,
    namespace: str,
    source_sides: list[dict[str, Any]],
) -> None:
    profile = _object(value, where)
    _check_fields(profile, {"format", "source", "provenance", "sides"}, where)
    if profile.get("format") != PROVISIONAL_FORM_LEG_PROFILE_FORMAT:
        raise ValidationError(f"{where}.format must be {PROVISIONAL_FORM_LEG_PROFILE_FORMAT}")
    if profile.get("source") != "authored_leg_profile":
        raise ValidationError(f"{where}.source must be authored_leg_profile")
    _form_control_provenance(profile.get("provenance"), f"{where}.provenance", document, namespace)
    sides = _array(profile.get("sides"), f"{where}.sides")
    if len(sides) != len(source_sides):
        raise ValidationError(f"{where}.sides must contain exactly two source-indexed sides")
    factors = _provisional_form_leg_profile_factors(profile_id)
    for side_index, (raw_side, source_side) in enumerate(zip(sides, source_sides)):
        side_where = f"{where}.sides[{side_index}]"
        side = _object(raw_side, side_where)
        _check_fields(side, {"side", "sections"}, side_where)
        if side.get("side") != source_side["side"]:
            raise ValidationError(f"{side_where}.side does not match its indexed source side")
        sections = _array(side.get("sections"), f"{side_where}.sections")
        if len(sections) != len(source_side["sections"]):
            raise ValidationError(f"{side_where}.sections must contain exactly five source-indexed sections")
        for section_index, (raw_section, source_section) in enumerate(
            zip(sections, source_side["sections"])
        ):
            section_where = f"{side_where}.sections[{section_index}]"
            section = _object(raw_section, section_where)
            _check_fields(
                section,
                {
                    "source_section_index",
                    "name",
                    "position",
                    "lateral_radius_permille",
                    "up_radius_permille",
                    "forward_radius_permille",
                    "scaling",
                    "provenance",
                },
                section_where,
            )
            if type(section.get("source_section_index")) is not int or section["source_section_index"] != section_index:
                raise ValidationError(f"{section_where}.source_section_index must equal its stable source index")
            if section.get("name") != source_section["name"]:
                raise ValidationError(f"{section_where}.name does not match its indexed source section")
            position = _form_finite_vector(section.get("position"), f"{section_where}.position", 3)
            if position != source_section["position"]:
                raise ValidationError(f"{section_where}.position must equal its indexed source landmark")
            expected_scaling = {
                "lateral_factor_permille": factors[0],
                "up_factor_permille": factors[1],
                "forward_factor_permille": factors[2],
            }
            scaling = _object(section.get("scaling"), f"{section_where}.scaling")
            _check_fields(scaling, set(expected_scaling), f"{section_where}.scaling")
            for field, expected_factor in expected_scaling.items():
                if _form_permille(scaling.get(field), f"{section_where}.scaling.{field}") != expected_factor:
                    raise ValidationError(f"{section_where}.scaling.{field} does not match the fixed variant factor")
            for axis, _role_suffix in PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES:
                field = f"{axis}_radius_permille"
                expected_radius = _form_scaled_display_value(
                    source_section["radii"][axis],
                    factors[{"lateral": 0, "up": 1, "forward": 2}[axis]],
                    f"{section_where}.{field}",
                )
                if _form_permille(section.get(field), f"{section_where}.{field}") != expected_radius:
                    raise ValidationError(
                        f"{section_where}.{field} does not match its indexed source radius and fixed factor"
                    )
            _form_control_provenance(section.get("provenance"), f"{section_where}.provenance", document, namespace)


def _provisional_form_foot_profile_factors(profile_id: str) -> tuple[int, int, int]:
    if profile_id == "broad-soft-v0":
        return (1_150, 1_000, 1_150)
    if profile_id == "lean-readable-v0":
        return (800, 1_000, 800)
    if profile_id == "depth-forward-v0":
        return (1_000, 1_000, 1_300)
    return (1_000, 1_000, 1_000)


def _validate_v11_authored_foot_profile(
    obj: dict[str, Any],
    where: str,
    *,
    document: str,
    namespace: str,
    authored_dimension_values: dict[
        tuple[tuple[str, tuple[str, ...], str, str], str], int
    ],
    leg_profile_sides: list[dict[str, Any]],
    reference_length: float,
) -> tuple[
    set[tuple[tuple[str, tuple[str, ...], str, str], str]],
    list[dict[str, Any]],
]:
    profile_where = f"{where}.authored_foot_profile"
    profile = _object(obj.get("authored_foot_profile"), profile_where)
    _check_fields(profile, {"format", "provenance", "sides"}, profile_where)
    if profile.get("format") != PROVISIONAL_FORM_FOOT_PROFILE_FORMAT:
        raise ValidationError(f"{profile_where}.format must be {PROVISIONAL_FORM_FOOT_PROFILE_FORMAT}")
    _form_control_provenance(profile.get("provenance"), f"{profile_where}.provenance", document, namespace)

    frames = _array(obj.get("authored_frames"), f"{where}.authored_frames")
    landmarks = _array(obj.get("authored_landmarks"), f"{where}.authored_landmarks")
    dimensions = _array(obj.get("authored_dimensions"), f"{where}.authored_dimensions")
    frame_keys = [
        (
            _form_address(frame.get("owner"), f"{where}.authored_frames[{index}].owner"),
            _string(frame.get("role"), f"{where}.authored_frames[{index}].role", max_len=256),
        )
        for index, frame in enumerate(frames)
    ]
    landmark_keys = [
        (
            _form_address(landmark.get("owner"), f"{where}.authored_landmarks[{index}].owner"),
            _string(landmark.get("role"), f"{where}.authored_landmarks[{index}].role", max_len=256),
        )
        for index, landmark in enumerate(landmarks)
    ]
    dimension_records = [
        (
            _form_address(dimension.get("owner"), f"{where}.authored_dimensions[{index}].owner"),
            _string(dimension.get("role"), f"{where}.authored_dimensions[{index}].role", max_len=256),
            authored_dimension_values[
                (
                    _form_address(dimension.get("owner"), f"{where}.authored_dimensions[{index}].owner"),
                    _string(dimension.get("role"), f"{where}.authored_dimensions[{index}].role", max_len=256),
                )
            ],
        )
        for index, dimension in enumerate(dimensions)
    ]
    expected_dimension_keys = {
        (
            _provisional_form_foot_owner(namespace, side),
            f"form_foot_profile_{section_name}_{role_suffix}",
        )
        for side in PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES
        for section_name in PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES
        for _axis, role_suffix in PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES
    }
    actual_dimension_keys = {
        (owner, role)
        for owner, role, _value in dimension_records
        if role.startswith("form_foot_profile_")
    }
    if actual_dimension_keys != expected_dimension_keys:
        raise ValidationError(f"{where}.authored_dimensions must contain exactly twelve foot profile radius dimensions")
    for owner, role, value in dimension_records:
        if role.startswith("form_foot_profile_"):
            if owner[3] != "foot" or not 0 < value <= PROVISIONAL_FORM_MAX_PERMILLE:
                raise ValidationError(f"{where}.authored_dimensions contains an invalid foot profile dimension")
            for profile_id in PROVISIONAL_FORM_VARIANT_IDS:
                _form_scaled_display_value(value, _provisional_form_foot_profile_factors(profile_id)[0], f"{where}.authored_dimensions.{role}")

    sides = _array(profile.get("sides"), f"{profile_where}.sides")
    if len(sides) != len(PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES):
        raise ValidationError(f"{profile_where}.sides must contain exactly two sides in left/right order")
    consumed_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    source_sides: list[dict[str, Any]] = []
    axis_indices = {"lateral": 0, "up": 1, "forward": 2}
    for side_index, (raw_side, expected_side) in enumerate(zip(sides, PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES)):
        side_where = f"{profile_where}.sides[{side_index}]"
        side = _object(raw_side, side_where)
        _check_fields(side, {"side", "hock_binding", "sections"}, side_where)
        if side.get("side") != expected_side:
            raise ValidationError(f"{side_where}.side must be {expected_side}")
        hock_where = f"{side_where}.hock_binding"
        hock = _object(side.get("hock_binding"), hock_where)
        _check_fields(hock, {"source_profile", "side_index", "section_index"}, hock_where)
        if (
            hock.get("source_profile") != "authored_leg_profile"
            or hock.get("side_index") != side_index
            or hock.get("section_index") != PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX
        ):
            raise ValidationError(f"{hock_where} must bind the same-side authored leg hock endpoint")
        if side_index >= len(leg_profile_sides):
            raise ValidationError(f"{hock_where}.side_index is out of range")
        leg_side = leg_profile_sides[side_index]
        if leg_side.get("side") != expected_side or len(leg_side.get("sections", [])) <= PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX:
            raise ValidationError(f"{hock_where} does not resolve to the same authored leg side")
        leg_hock = leg_side["sections"][PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX]
        if leg_hock.get("name") != "hock-endpoint" or leg_hock.get("owner_role") != "shin":
            raise ValidationError(f"{hock_where} does not resolve to authored shin hock-endpoint")

        sections = _array(side.get("sections"), f"{side_where}.sections")
        if len(sections) != len(PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES):
            raise ValidationError(f"{side_where}.sections must contain exactly two sections")
        source_sections: list[dict[str, Any]] = []
        previous_z: int | float | None = None
        for section_index, (raw_section, expected_name) in enumerate(zip(sections, PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES)):
            section_where = f"{side_where}.sections[{section_index}]"
            section = _object(raw_section, section_where)
            _check_fields(section, {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}, section_where)
            if section.get("name") != expected_name or section.get("section_index") != section_index:
                raise ValidationError(f"{section_where} is not in the required pad/toe order")
            _form_control_provenance(section.get("provenance"), f"{section_where}.provenance", document, namespace)
            owner = _provisional_form_foot_owner(namespace, expected_side)
            frame_index = _provisional_form_index(section.get("frame_index"), len(frame_keys), f"{section_where}.frame_index")
            if frame_keys[frame_index] != (owner, PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE):
                raise ValidationError(f"{section_where}.frame_index does not resolve to its same-owner identity foot control frame")
            landmark_index = _provisional_form_index(section.get("landmark_index"), len(landmark_keys), f"{section_where}.landmark_index")
            expected_landmark_role = f"form_foot_profile_{expected_name}"
            if landmark_keys[landmark_index] != (owner, expected_landmark_role):
                raise ValidationError(f"{section_where}.landmark_index does not resolve to its canonical foot landmark")
            position = _form_finite_vector(landmarks[landmark_index].get("position"), f"{section_where}.landmark.position", 3)
            if (
                position[0] != 0
                or not PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN <= position[1] <= PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX
                or not PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN <= position[2] <= PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX
                or any(abs(component) > PROVISIONAL_FORM_CONTROL_COORDINATE_BOUND for component in position)
            ):
                raise ValidationError(f"{section_where}.landmark.position is outside the foot profile bounds")
            if previous_z is not None and position[2] <= previous_z:
                raise ValidationError(f"{section_where}.landmark.position must use strict +z order")
            previous_z = position[2]
            dimension_indices = _object(section.get("dimension_indices"), f"{section_where}.dimension_indices")
            _check_fields(dimension_indices, {axis for axis, _role_suffix in PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES}, f"{section_where}.dimension_indices")
            radii: dict[str, int] = {}
            for axis, role_suffix in PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES:
                dimension_index = _provisional_form_index(dimension_indices.get(axis), len(dimension_records), f"{section_where}.dimension_indices.{axis}")
                owner_at_index, role_at_index, value_permille = dimension_records[dimension_index]
                expected_role = f"form_foot_profile_{expected_name}_{role_suffix}"
                if (owner_at_index, role_at_index) != (owner, expected_role):
                    raise ValidationError(f"{section_where}.dimension_indices.{axis} does not resolve to {expected_role}")
                for profile_id in PROVISIONAL_FORM_VARIANT_IDS:
                    _form_scaled_display_value(value_permille, _provisional_form_foot_profile_factors(profile_id)[axis_indices[axis]], f"{section_where}.dimension_indices.{axis}")
                consumed_dimension_keys.add((owner_at_index, role_at_index))
                radii[axis] = value_permille
            source_sections.append({"name": expected_name, "position": position, "radii": radii})
        pad, toe = source_sections
        pad_contact = pad["position"][1] / reference_length - pad["radii"]["up"] / 1000.0
        toe_contact = toe["position"][1] / reference_length - toe["radii"]["up"] / 1000.0
        if not math.isfinite(pad_contact) or not math.isfinite(toe_contact) or abs(pad_contact - toe_contact) > 1e-12:
            raise ValidationError(f"{side_where} pad and toe must share an equal contact datum")
        forward_gap = (toe["position"][2] - pad["position"][2]) / reference_length
        forward_overlap = (pad["radii"]["forward"] + toe["radii"]["forward"]) / 1000.0
        lateral_overlap = (pad["radii"]["lateral"] + toe["radii"]["lateral"]) / 1000.0
        if not forward_gap < forward_overlap or not lateral_overlap > 0:
            raise ValidationError(f"{side_where} foot sections must overlap forward and laterally")
        source_sides.append({"side": expected_side, "hock_binding": dict(hock), "sections": source_sections})
    return consumed_dimension_keys, source_sides


def _validate_v11_variant_foot_profile(
    value: Any,
    where: str,
    *,
    profile_id: str,
    document: str,
    namespace: str,
    source_sides: list[dict[str, Any]],
) -> None:
    profile = _object(value, where)
    _check_fields(profile, {"format", "source", "provenance", "sides"}, where)
    if profile.get("format") != PROVISIONAL_FORM_FOOT_PROFILE_FORMAT or profile.get("source") != "authored_foot_profile":
        raise ValidationError(f"{where} format/source is invalid")
    _form_control_provenance(profile.get("provenance"), f"{where}.provenance", document, namespace)
    sides = _array(profile.get("sides"), f"{where}.sides")
    if len(sides) != len(source_sides):
        raise ValidationError(f"{where}.sides must contain exactly two source-indexed sides")
    factors = _provisional_form_foot_profile_factors(profile_id)
    for side_index, (raw_side, source_side) in enumerate(zip(sides, source_sides)):
        side_where = f"{where}.sides[{side_index}]"
        side = _object(raw_side, side_where)
        _check_fields(side, {"side", "hock_binding", "sections"}, side_where)
        if side.get("side") != source_side["side"] or side.get("hock_binding") != source_side["hock_binding"]:
            raise ValidationError(f"{side_where} does not preserve its indexed source side and hock binding")
        sections = _array(side.get("sections"), f"{side_where}.sections")
        if len(sections) != len(source_side["sections"]):
            raise ValidationError(f"{side_where}.sections must contain exactly two source-indexed sections")
        for section_index, (raw_section, source_section) in enumerate(zip(sections, source_side["sections"])):
            section_where = f"{side_where}.sections[{section_index}]"
            section = _object(raw_section, section_where)
            _check_fields(section, {"source_section_index", "name", "position", "lateral_radius_permille", "up_radius_permille", "forward_radius_permille", "scaling", "provenance"}, section_where)
            if section.get("source_section_index") != section_index or section.get("name") != source_section["name"]:
                raise ValidationError(f"{section_where} does not preserve its source section index/name")
            position = _form_finite_vector(section.get("position"), f"{section_where}.position", 3)
            if position != source_section["position"]:
                raise ValidationError(f"{section_where}.position must equal its indexed source landmark")
            scaling = _object(section.get("scaling"), f"{section_where}.scaling")
            expected_scaling = {"lateral_factor_permille": factors[0], "up_factor_permille": factors[1], "forward_factor_permille": factors[2]}
            _check_fields(scaling, set(expected_scaling), f"{section_where}.scaling")
            for field, expected_factor in expected_scaling.items():
                if _form_permille(scaling.get(field), f"{section_where}.scaling.{field}") != expected_factor:
                    raise ValidationError(f"{section_where}.{field} does not match its fixed factor")
            for axis, _role_suffix in PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES:
                field = f"{axis}_radius_permille"
                expected_radius = _form_scaled_display_value(source_section["radii"][axis], factors[{"lateral": 0, "up": 1, "forward": 2}[axis]], f"{section_where}.{field}")
                if _form_permille(section.get(field), f"{section_where}.{field}") != expected_radius:
                    raise ValidationError(f"{section_where}.{field} does not match its indexed source radius and fixed factor")
            _form_control_provenance(section.get("provenance"), f"{section_where}.provenance", document, namespace)


def _validate_provisional_form_envelope(value: Any, where: str) -> dict[str, Any]:
    """Validate the successful filled-form CLI envelope before immutable copy."""

    obj = _object(value, where)
    _check_fields(
        obj,
        {
            "format",
            "operation",
            "status",
            "stage",
            "processing_complete",
            "diagnostics_complete",
            "diagnostics",
            "source",
            "reference_scale",
            "authored_dimensions",
            "authored_landmarks",
            "authored_frames",
            "authored_torso_profile",
            "authored_head_neck_profile",
            "authored_arm_profile",
            "authored_leg_profile",
            "authored_foot_profile",
            "variants",
            "limitations",
        },
        where,
    )
    format_name = _string(obj.get("format"), f"{where}.format", max_len=256)
    if format_name not in PROVISIONAL_FORM_FORMATS:
        raise ValidationError(
            f"{where}.format must be {PROVISIONAL_FORM_LEGACY_FORMAT}, "
            f"{PROVISIONAL_FORM_V2_FORMAT}, {PROVISIONAL_FORM_V3_FORMAT}, "
            f"{PROVISIONAL_FORM_HISTORICAL_V4_FORMAT}, "
            f"{PROVISIONAL_FORM_HISTORICAL_V5_FORMAT}, "
            f"{PROVISIONAL_FORM_HISTORICAL_V6_FORMAT}, {PROVISIONAL_FORM_V7_FORMAT}, "
            f"{PROVISIONAL_FORM_V8_FORMAT}, {PROVISIONAL_FORM_V9_FORMAT}, "
            f"{PROVISIONAL_FORM_V10_FORMAT}, or {PROVISIONAL_FORM_V11_FORMAT}"
        )
    is_v5 = format_name == PROVISIONAL_FORM_HISTORICAL_V5_FORMAT
    is_v6 = format_name == PROVISIONAL_FORM_HISTORICAL_V6_FORMAT
    is_v7 = format_name == PROVISIONAL_FORM_V7_FORMAT
    is_v8 = format_name == PROVISIONAL_FORM_V8_FORMAT
    is_v9 = format_name == PROVISIONAL_FORM_V9_FORMAT
    is_v10 = format_name == PROVISIONAL_FORM_V10_FORMAT
    is_v11 = format_name == PROVISIONAL_FORM_V11_FORMAT
    has_shoulder_controls = is_v6 or is_v7 or is_v8 or is_v9 or is_v10 or is_v11
    has_authored_dimensions = is_v5 or has_shoulder_controls
    dimension_contract = "v5, v6, v7, v8, v9, v10, or v11" if is_v11 else "v5, v6, v7, v8, v9, or v10" if is_v10 else "v5, v6, v7, v8, or v9" if is_v9 else "v5, v6, v7, or v8" if is_v8 else "v5, v6, or v7"
    control_contract = "v6, v7, v8, v9, v10, or v11" if is_v11 else "v6, v7, v8, v9, or v10" if is_v10 else "v6, v7, v8, or v9" if is_v9 else "v6, v7, or v8" if is_v8 else "v6 or v7"
    if has_authored_dimensions and "authored_dimensions" not in obj:
        raise ValidationError(f"{where}.authored_dimensions is required for {dimension_contract}")
    if not has_authored_dimensions and "authored_dimensions" in obj:
        raise ValidationError(
            f"{where}.authored_dimensions is only valid for {dimension_contract}"
        )
    for control_key in ("authored_landmarks", "authored_frames"):
        if has_shoulder_controls and control_key not in obj:
            raise ValidationError(f"{where}.{control_key} is required for {control_contract}")
        if not has_shoulder_controls and control_key in obj:
            raise ValidationError(f"{where}.{control_key} is only valid for {control_contract}")
    if is_v7 or is_v8 or is_v9 or is_v10 or is_v11:
        if "authored_torso_profile" not in obj:
            raise ValidationError(f"{where}.authored_torso_profile is required for v7 through v11")
    elif "authored_torso_profile" in obj:
        raise ValidationError(f"{where}.authored_torso_profile is only valid for v7 through v11")
    if is_v8 or is_v9 or is_v10 or is_v11:
        if "authored_head_neck_profile" not in obj:
            raise ValidationError(f"{where}.authored_head_neck_profile is required for v8 through v11")
    elif "authored_head_neck_profile" in obj:
        raise ValidationError(f"{where}.authored_head_neck_profile is only valid for v8 through v11")
    if is_v9 or is_v10 or is_v11:
        if "authored_arm_profile" not in obj:
            raise ValidationError(f"{where}.authored_arm_profile is required for v9 through v11")
    elif "authored_arm_profile" in obj:
        raise ValidationError(f"{where}.authored_arm_profile is only valid for v9 through v11")
    if is_v10 or is_v11:
        if "authored_leg_profile" not in obj:
            raise ValidationError(f"{where}.authored_leg_profile is required for v10 or v11")
    elif "authored_leg_profile" in obj:
        raise ValidationError(f"{where}.authored_leg_profile is only valid for v10 or v11")
    if is_v11:
        if "authored_foot_profile" not in obj:
            raise ValidationError(f"{where}.authored_foot_profile is required for v11")
    elif "authored_foot_profile" in obj:
        raise ValidationError(f"{where}.authored_foot_profile is only valid for v11")
    if is_v8 or is_v9 or is_v10 or is_v11:
        expected_envelope_fields = {
            "format",
            "operation",
            "status",
            "stage",
            "processing_complete",
            "diagnostics_complete",
            "diagnostics",
            "source",
            "reference_scale",
            "authored_dimensions",
            "authored_landmarks",
            "authored_frames",
            "authored_torso_profile",
            "authored_head_neck_profile",
            *( {"authored_arm_profile"} if is_v9 or is_v10 or is_v11 else set() ),
            *( {"authored_leg_profile"} if is_v10 or is_v11 else set() ),
            *( {"authored_foot_profile"} if is_v11 else set() ),
            "variants",
            "limitations",
        }
        missing = sorted(expected_envelope_fields - set(obj))
        if missing:
            raise ValidationError(
                f"{where} is missing required {'v11' if is_v11 else 'v10' if is_v10 else 'v9' if is_v9 else 'v8'} field(s): {', '.join(missing)}"
            )
    if obj.get("operation") != PROVISIONAL_FORM_OPERATION:
        raise ValidationError(f"{where}.operation must be {PROVISIONAL_FORM_OPERATION}")
    if obj.get("status") != "success":
        raise ValidationError(f"{where}.status must be success for publication")
    if obj.get("stage") != PROVISIONAL_FORM_STAGE:
        raise ValidationError(f"{where}.stage must be {PROVISIONAL_FORM_STAGE}")
    if obj.get("processing_complete") is not True or obj.get("diagnostics_complete") is not True:
        raise ValidationError(f"{where}.success must report complete processing and diagnostics")
    diagnostics = _array(obj.get("diagnostics"), f"{where}.diagnostics")
    if diagnostics:
        raise ValidationError(f"{where}.diagnostics must be empty for success")
    limitations = _string(obj.get("limitations"), f"{where}.limitations", max_len=MAX_STRING)
    if "Readiness" not in limitations or "geometry" not in limitations:
        raise ValidationError(f"{where}.limitations must state the provisional boundary")

    source = _object(obj.get("source"), f"{where}.source")
    _check_fields(source, {"document", "namespace", "resource_profile_id"}, f"{where}.source")
    document = _string(source.get("document"), f"{where}.source.document", max_len=MAX_STRING)
    namespace = _string(source.get("namespace"), f"{where}.source.namespace", max_len=MAX_STRING)
    resource_profile_id = source.get("resource_profile_id")
    if resource_profile_id != PROVISIONAL_FORM_RESOURCE_PROFILE:
        raise ValidationError(
            f"{where}.source.resource_profile_id must be {PROVISIONAL_FORM_RESOURCE_PROFILE}"
        )

    authored_dimension_keys: set[tuple[tuple[str, tuple[str, ...], str, str], str]] = set()
    authored_dimension_values: dict[
        tuple[tuple[str, tuple[str, ...], str, str], str], int
    ] = {}
    if has_authored_dimensions:
        authored_dimensions = _array(
            obj.get("authored_dimensions"), f"{where}.authored_dimensions"
        )
        if not authored_dimensions:
            raise ValidationError(f"{where}.authored_dimensions must not be empty")
        ordered_dimension_keys: list[
            tuple[tuple[str, tuple[str, ...], str, str], str]
        ] = []
        for dimension_index, raw_dimension in enumerate(authored_dimensions):
            dimension_where = f"{where}.authored_dimensions[{dimension_index}]"
            dimension = _object(raw_dimension, dimension_where)
            _check_fields(
                dimension,
                {"owner", "role", "value_permille", "provenance"},
                dimension_where,
            )
            owner = _form_address(dimension.get("owner"), f"{dimension_where}.owner")
            if owner[0] != namespace:
                raise ValidationError(f"{dimension_where}.owner does not match source namespace")
            role = _string(dimension.get("role"), f"{dimension_where}.role", max_len=256)
            value_permille = _form_permille(
                dimension.get("value_permille"), f"{dimension_where}.value_permille"
            )
            provenance = _object(
                dimension.get("provenance"), f"{dimension_where}.provenance"
            )
            _check_fields(
                provenance,
                {"source", "document", "namespace"},
                f"{dimension_where}.provenance",
            )
            if (
                provenance.get("source") != PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE
                or provenance.get("document") != document
                or provenance.get("namespace") != namespace
            ):
                raise ValidationError(f"{dimension_where}.provenance is invalid")
            key = (owner, role)
            ordered_dimension_keys.append(key)
            authored_dimension_keys.add(key)
            authored_dimension_values[key] = value_permille
        if len(authored_dimension_keys) != len(ordered_dimension_keys):
            raise ValidationError(f"{where}.authored_dimensions contains duplicate owner/role keys")
        if ordered_dimension_keys != sorted(ordered_dimension_keys):
            raise ValidationError(f"{where}.authored_dimensions must use stable owner/role order")
        if is_v10 and len(authored_dimensions) != 141:
            raise ValidationError(f"{where}.authored_dimensions must contain exactly 141 dimensions for v10")
        if is_v11 and len(authored_dimensions) != 153:
            raise ValidationError(f"{where}.authored_dimensions must contain exactly 153 dimensions for v11")

    scale = _object(obj.get("reference_scale"), f"{where}.reference_scale")
    _check_fields(
        scale,
        {"parent", "child", "axis_delta", "squared_length", "source"},
        f"{where}.reference_scale",
    )
    parent_key = _form_address(scale.get("parent"), f"{where}.reference_scale.parent")
    child_key = _form_address(scale.get("child"), f"{where}.reference_scale.child")
    if parent_key[0] != namespace or child_key[0] != namespace:
        raise ValidationError(f"{where}.reference_scale addresses do not match source namespace")
    if parent_key == child_key:
        raise ValidationError(f"{where}.reference_scale parent and child must differ")
    axis_delta = _form_i64_vector(scale.get("axis_delta"), f"{where}.reference_scale.axis_delta")
    squared_length = scale.get("squared_length")
    if (
        type(squared_length) is not int
        or not 0 < squared_length <= PROVISIONAL_FORM_MAX_SQUARED_LENGTH
        or squared_length != sum(component * component for component in axis_delta)
    ):
        raise ValidationError(f"{where}.reference_scale.squared_length is invalid")
    if scale.get("source") != "exact-containment-edge":
        raise ValidationError(
            f"{where}.reference_scale.source must be exact-containment-edge"
        )
    reference_length = math.sqrt(float(squared_length))
    if not math.isfinite(reference_length) or reference_length <= 0:
        raise ValidationError(f"{where}.reference_scale length is invalid")

    profile_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set()
    torso_profile_sections: list[dict[str, Any]] = []
    head_neck_profile_sections: list[dict[str, Any]] = []
    arm_profile_sides: list[dict[str, Any]] = []
    leg_profile_sides: list[dict[str, Any]] = []
    if is_v6:
        _validate_v6_authored_controls(
            obj, where, document=document, namespace=namespace
        )
    elif is_v7:
        profile_dimension_keys, torso_profile_sections = _validate_v7_authored_torso_profile(
            obj,
            where,
            document=document,
            namespace=namespace,
            authored_dimension_values=authored_dimension_values,
        )
    elif is_v8 or is_v9 or is_v10 or is_v11:
        torso_keys, torso_profile_sections = _validate_v7_authored_torso_profile(
            obj,
            where,
            document=document,
            namespace=namespace,
            authored_dimension_values=authored_dimension_values,
            include_v8_controls=True,
            include_v9_controls=is_v9 or is_v10 or is_v11,
            include_v10_controls=is_v10 or is_v11,
            include_v11_controls=is_v11,
        )
        profile_dimension_keys.update(torso_keys)
        head_keys, head_neck_profile_sections = _validate_v8_authored_head_neck_profile(
            obj,
            where,
            document=document,
            namespace=namespace,
            authored_dimension_values=authored_dimension_values,
            include_v9_controls=is_v9 or is_v10 or is_v11,
            include_v10_controls=is_v10 or is_v11,
            include_v11_controls=is_v11,
        )
        profile_dimension_keys.update(head_keys)
        if is_v9 or is_v10 or is_v11:
            arm_keys, arm_profile_sides = _validate_v9_authored_arm_profile(
                obj,
                where,
                document=document,
                namespace=namespace,
                authored_dimension_values=authored_dimension_values,
            )
            profile_dimension_keys.update(arm_keys)
        if is_v10 or is_v11:
            leg_keys, leg_profile_sides = _validate_v10_authored_leg_profile(
                obj,
                where,
                document=document,
                namespace=namespace,
                authored_dimension_values=authored_dimension_values,
            )
            profile_dimension_keys.update(leg_keys)
        if is_v11:
            foot_keys, foot_profile_sides = _validate_v11_authored_foot_profile(
                obj,
                where,
                document=document,
                namespace=namespace,
                authored_dimension_values=authored_dimension_values,
                leg_profile_sides=leg_profile_sides,
                reference_length=reference_length,
            )
            profile_dimension_keys.update(foot_keys)

    variants = _array(obj.get("variants"), f"{where}.variants")
    if len(variants) != len(PROVISIONAL_FORM_VARIANT_IDS):
        raise ValidationError(f"{where}.variants must contain exactly four variants")
    canonical: list[tuple[Any, ...]] | None = None
    consumed_dimension_keys: set[
        tuple[tuple[str, tuple[str, ...], str, str], str]
    ] = set(profile_dimension_keys)
    for index, raw_variant in enumerate(variants):
        variant_where = f"{where}.variants[{index}]"
        variant = _object(raw_variant, variant_where)
        _check_fields(
            variant,
            {
                "id",
                "profile_id",
                "provenance",
                "descriptors",
                *( {"torso_profile"} if is_v7 or is_v8 or is_v9 or is_v10 or is_v11 else set() ),
                *( {"head_neck_profile"} if is_v8 or is_v9 or is_v10 or is_v11 else set() ),
                *( {"arm_profile"} if is_v9 or is_v10 or is_v11 else set() ),
                *( {"leg_profile"} if is_v10 or is_v11 else set() ),
                *( {"foot_profile"} if is_v11 else set() ),
            },
            variant_where,
        )
        expected_id = PROVISIONAL_FORM_VARIANT_IDS[index]
        if variant.get("id") != expected_id or variant.get("profile_id") != expected_id:
            raise ValidationError(f"{variant_where} must be {expected_id} in fixed order")
        provenance = _object(variant.get("provenance"), f"{variant_where}.provenance")
        _check_fields(
            provenance,
            {"source", "resource_profile_id", "shape_basis"}
            if has_authored_dimensions
            else {"source", "resource_profile_id"},
            f"{variant_where}.provenance",
        )
        if provenance.get("source") != PROVISIONAL_FORM_PROVENANCE:
            raise ValidationError(f"{variant_where}.provenance.source is not known")
        if provenance.get("resource_profile_id") != resource_profile_id:
            raise ValidationError(f"{variant_where}.provenance profile does not match source")
        if has_authored_dimensions and provenance.get("shape_basis") != PROVISIONAL_FORM_SHAPE_BASIS:
            raise ValidationError(f"{variant_where}.provenance.shape_basis is invalid")
        if is_v7 or is_v8 or is_v9 or is_v10 or is_v11:
            _validate_v7_variant_torso_profile(
                variant.get("torso_profile"),
                f"{variant_where}.torso_profile",
                profile_id=expected_id,
                document=document,
                namespace=namespace,
                source_sections=torso_profile_sections,
            )
        if is_v8 or is_v9 or is_v10 or is_v11:
            _validate_v8_variant_head_neck_profile(
                variant.get("head_neck_profile"),
                f"{variant_where}.head_neck_profile",
                profile_id=expected_id,
                document=document,
                namespace=namespace,
                source_sections=head_neck_profile_sections,
            )
        if is_v9 or is_v10 or is_v11:
            _validate_v9_variant_arm_profile(
                variant.get("arm_profile"),
                f"{variant_where}.arm_profile",
                profile_id=expected_id,
                document=document,
                namespace=namespace,
                source_sides=arm_profile_sides,
            )
        if is_v10 or is_v11:
            _validate_v10_variant_leg_profile(
                variant.get("leg_profile"),
                f"{variant_where}.leg_profile",
                profile_id=expected_id,
                document=document,
                namespace=namespace,
                source_sides=leg_profile_sides,
            )
        if is_v11:
            _validate_v11_variant_foot_profile(
                variant.get("foot_profile"),
                f"{variant_where}.foot_profile",
                profile_id=expected_id,
                document=document,
                namespace=namespace,
                source_sides=foot_profile_sides,
            )
        descriptors = _array(variant.get("descriptors"), f"{variant_where}.descriptors")
        if not descriptors or len(descriptors) > PROVISIONAL_FORM_MAX_DESCRIPTORS:
            raise ValidationError(
                f"{variant_where}.descriptors must contain 1..{PROVISIONAL_FORM_MAX_DESCRIPTORS} items"
            )
        descriptor_keys: list[tuple[Any, ...]] = []
        address_map: dict[tuple[str, tuple[str, ...], str, str], tuple[list[int], dict[str, Any]]] = {}
        for descriptor_index, raw_descriptor in enumerate(descriptors):
            descriptor_where = f"{variant_where}.descriptors[{descriptor_index}]"
            descriptor = _object(raw_descriptor, descriptor_where)
            _check_fields(
                descriptor,
                {
                    "descriptor_kind",
                    "address",
                    "parent",
                    "placement_source",
                    "reference_point",
                    "profile_id",
                    "source",
                    "provenance",
                    "shape",
                    "dimension_roles",
                },
                descriptor_where,
            )
            if not has_authored_dimensions and "dimension_roles" in descriptor:
                raise ValidationError(
                    f"{descriptor_where}.dimension_roles is only valid for v5, v6, v7, or v8"
                )
            if descriptor.get("descriptor_kind") != "display-only-form-descriptor":
                raise ValidationError(f"{descriptor_where}.descriptor_kind is not supported")
            address = _form_address(descriptor.get("address"), f"{descriptor_where}.address")
            if address[0] != namespace:
                raise ValidationError(f"{descriptor_where}.address does not match source namespace")
            if address in address_map:
                raise ValidationError(f"{variant_where}.descriptors contains duplicate addresses")
            parent_value = descriptor.get("parent")
            parent = None if parent_value is None else _form_address(parent_value, f"{descriptor_where}.parent")
            if parent is not None and parent[0] != namespace:
                raise ValidationError(f"{descriptor_where}.parent does not match source namespace")
            if parent == address:
                raise ValidationError(f"{descriptor_where}.parent cannot self-reference")
            reference_point = _form_i64_vector(
                descriptor.get("reference_point"), f"{descriptor_where}.reference_point"
            )
            if descriptor.get("profile_id") != expected_id or descriptor.get("source") != PROVISIONAL_FORM_PROVENANCE:
                raise ValidationError(f"{descriptor_where} provenance does not match its variant")
            descriptor_provenance = _object(
                descriptor.get("provenance"), f"{descriptor_where}.provenance"
            )
            _check_fields(
                descriptor_provenance,
                {"source", "resource_profile_id", "shape_basis"}
                if has_authored_dimensions
                else {"source", "resource_profile_id"},
                f"{descriptor_where}.provenance",
            )
            if (
                descriptor_provenance.get("source") != PROVISIONAL_FORM_PROVENANCE
                or descriptor_provenance.get("resource_profile_id") != resource_profile_id
                or (
                    has_authored_dimensions
                    and descriptor_provenance.get("shape_basis")
                    != PROVISIONAL_FORM_SHAPE_BASIS
                )
            ):
                raise ValidationError(f"{descriptor_where}.provenance is not known")
            placement_source = descriptor.get("placement_source")
            if placement_source not in {"authored-root", "authored-containment", "authored-attachment"}:
                raise ValidationError(f"{descriptor_where}.placement_source is not supported")
            shape = _object(descriptor.get("shape"), f"{descriptor_where}.shape")
            shape_name = shape.get("name")
            expected_shape = _form_role_shape(format_name, address[3])
            if expected_shape is None:
                raise ValidationError(f"{descriptor_where}.address.role is not supported")
            if shape_name != expected_shape:
                raise ValidationError(
                    f"{descriptor_where}.shape.name must be {expected_shape} for role {address[3]}"
                )
            if shape_name == "ellipsoid":
                _check_fields(shape, {"name", "center", "axis_extents_permille"}, f"{descriptor_where}.shape")
                center = _form_i64_vector(shape.get("center"), f"{descriptor_where}.shape.center")
                if center != reference_point:
                    raise ValidationError(f"{descriptor_where}.shape.center must equal reference_point")
                extents = _array(shape.get("axis_extents_permille"), f"{descriptor_where}.shape.axis_extents_permille")
                if len(extents) != 3:
                    raise ValidationError(f"{descriptor_where}.shape.axis_extents_permille must contain 3 values")
                for extent_index, extent in enumerate(extents):
                    _form_permille(extent, f"{descriptor_where}.shape.axis_extents_permille[{extent_index}]")
            elif shape_name == "capsule":
                _check_fields(shape, {"name", "from", "to", "radius_permille"}, f"{descriptor_where}.shape")
                from_point = _form_i64_vector(shape.get("from"), f"{descriptor_where}.shape.from")
                to_point = _form_i64_vector(shape.get("to"), f"{descriptor_where}.shape.to")
                _form_permille(shape.get("radius_permille"), f"{descriptor_where}.shape.radius_permille")
                if (
                    parent is None
                    or from_point == to_point
                    or (
                        format_name == PROVISIONAL_FORM_LEGACY_FORMAT
                        and to_point != reference_point
                    )
                ):
                    raise ValidationError(f"{descriptor_where}.shape capsule endpoints are invalid")
            else:
                _check_fields(shape, {"name", "from", "to", "start_radius_permille", "end_radius_permille"}, f"{descriptor_where}.shape")
                from_point = _form_i64_vector(shape.get("from"), f"{descriptor_where}.shape.from")
                to_point = _form_i64_vector(shape.get("to"), f"{descriptor_where}.shape.to")
                _form_permille(shape.get("start_radius_permille"), f"{descriptor_where}.shape.start_radius_permille")
                _form_permille(shape.get("end_radius_permille"), f"{descriptor_where}.shape.end_radius_permille")
                if parent is None or from_point == to_point or to_point != reference_point:
                    raise ValidationError(f"{descriptor_where}.shape tapered endpoints are invalid")
            dimension_roles: tuple[str, ...] = ()
            if has_authored_dimensions:
                raw_dimension_roles = _array(
                    descriptor.get("dimension_roles"),
                    f"{descriptor_where}.dimension_roles",
                )
                expected_dimension_roles = {
                    "ellipsoid": (
                        "form_extent_x",
                        "form_extent_y",
                        "form_extent_z",
                    ),
                    "capsule": (
                        ("form_radius", "form_shoulder_depth_radius")
                        if has_shoulder_controls and address[3] == "upper_arm"
                        else ("form_radius",)
                    ),
                    "tapered-segment": ("form_start_radius", "form_end_radius"),
                }[shape_name]
                if tuple(raw_dimension_roles) != expected_dimension_roles:
                    raise ValidationError(
                        f"{descriptor_where}.dimension_roles do not match its shape"
                    )
                if any(
                    (address, role) not in authored_dimension_keys
                    for role in raw_dimension_roles
                ):
                    raise ValidationError(
                        f"{descriptor_where}.dimension_roles do not identify source controls"
                    )
                dimension_roles = tuple(raw_dimension_roles)
                consumed_dimension_keys.update(
                    (address, role) for role in dimension_roles
                )
                factors = _form_display_factors(expected_id, address[3], shape_name)
                if shape_name == "ellipsoid":
                    controls = tuple(shape["axis_extents_permille"])
                elif shape_name == "capsule":
                    controls = (shape["radius_permille"],)
                else:
                    controls = (
                        shape["start_radius_permille"],
                        shape["end_radius_permille"],
                    )
                # v6 retains shoulder depth as a consumed authored control,
                # but the current capsule display shape has one radius.  Only
                # form_radius is a capsule-radius numeric control; the depth
                # control must not be silently treated as a second radius.
                numeric_roles = (
                    ("form_radius",)
                    if has_shoulder_controls and shape_name == "capsule" and address[3] == "upper_arm"
                    else dimension_roles
                )
                numeric_factors = (
                    (_form_display_factors(expected_id, address[3], shape_name)[0],)
                    if numeric_roles != dimension_roles
                    else factors
                )
                expected_controls = tuple(
                    _form_scaled_display_value(
                        authored_dimension_values[(address, role)],
                        factor,
                        f"{descriptor_where}.shape.{role}",
                    )
                    for role, factor in zip(numeric_roles, numeric_factors)
                )
                if controls != expected_controls:
                    raise ValidationError(
                        f"{descriptor_where}.shape numeric controls do not match "
                        "source-authored dimensions after the fixed display factor"
                    )
            descriptor_keys.append(address)
            address_map[address] = (
                reference_point,
                {
                    "parent": parent,
                    "placement_source": placement_source,
                    "shape": shape,
                    "shape_name": shape_name,
                    "dimension_roles": dimension_roles,
                    },
            )
        if has_shoulder_controls:
            expected_upper_arm_owners = {
                _provisional_form_upper_arm_owner(namespace, side)
                for side in ("left", "right")
            }
            if not expected_upper_arm_owners <= set(address_map):
                raise ValidationError(
                    f"{variant_where}.descriptors must contain matching left/right upper_arm owners"
                )
        if descriptor_keys != sorted(descriptor_keys):
            raise ValidationError(f"{variant_where}.descriptors must use stable AddressKey order")
        roots = [
            address
            for address, (_, details) in address_map.items()
            if details["placement_source"] == "authored-root"
        ]
        if len(roots) != 1:
            raise ValidationError(f"{variant_where}.descriptors must contain exactly one root")

        # Validate limb segment ownership before walking ordinary parent
        # invariants.  This keeps a missing distal child diagnostic about the
        # capsule contract, rather than being obscured by a later orphan check
        # on a different descriptor.
        if format_name in PROVISIONAL_FORM_CORRECTED_FORMATS:
            capsule_child_roles = _form_capsule_child_roles(format_name)
            for address, (reference_point, details) in address_map.items():
                if details["shape_name"] != "capsule":
                    continue
                expected_child_role = capsule_child_roles[address[3]]
                direct_children = [
                    child
                    for child, (_, child_details) in address_map.items()
                    if child_details["parent"] == address and child[3] == expected_child_role
                ]
                if not direct_children:
                    raise ValidationError(
                        f"{variant_where} capsule {address[3]} is missing its direct {expected_child_role} child"
                    )
                if len(direct_children) != 1:
                    raise ValidationError(
                        f"{variant_where} capsule {address[3]} has ambiguous direct {expected_child_role} children"
                    )
                capsule = details["shape"]
                if capsule["from"] != reference_point:
                    raise ValidationError(
                        f"{variant_where} capsule {address[3]} start does not match its reference point"
                    )
                child_point = address_map[direct_children[0]][0]
                if capsule["to"] != child_point:
                    raise ValidationError(
                        f"{variant_where} capsule {address[3]} end does not match its direct {expected_child_role} child point"
                    )

        for address, (reference_point, details) in address_map.items():
            parent = details["parent"]
            if details["placement_source"] == "authored-root" and parent is not None:
                raise ValidationError(f"{variant_where} root descriptor has a parent")
            if details["placement_source"] != "authored-root" and parent is None:
                raise ValidationError(f"{variant_where} non-root descriptor has no parent")
            if parent is not None and parent not in address_map:
                raise ValidationError(f"{variant_where} descriptor parent is missing")
            if parent is not None:
                shape = details["shape"]
                if (
                    shape["name"] == "tapered-segment"
                    or (
                        format_name == PROVISIONAL_FORM_LEGACY_FORMAT
                        and shape["name"] == "capsule"
                    )
                ) and shape["from"] != address_map[parent][0]:
                    raise ValidationError(f"{variant_where} segment start does not match parent point")
            lineage: set[tuple[str, tuple[str, ...], str, str]] = set()
            current = address
            while current in address_map:
                if current in lineage:
                    raise ValidationError(f"{variant_where}.descriptors contain a parent cycle")
                lineage.add(current)
                next_parent = address_map[current][1]["parent"]
                if next_parent is None:
                    break
                current = next_parent
        if canonical is None:
            canonical = [
                (
                    key,
                    address_map[key][0],
                    address_map[key][1]["parent"],
                    address_map[key][1]["placement_source"],
                    next(item["shape"]["name"] for item in descriptors if _form_address(item["address"], "descriptor.address") == key),
                    address_map[key][1]["dimension_roles"],
                )
                for key in descriptor_keys
            ]
        else:
            current = [
                (
                    key,
                    address_map[key][0],
                    address_map[key][1]["parent"],
                    address_map[key][1]["placement_source"],
                    next(item["shape"]["name"] for item in descriptors if _form_address(item["address"], "descriptor.address") == key),
                    address_map[key][1]["dimension_roles"],
                )
                for key in descriptor_keys
            ]
            if current != canonical:
                raise ValidationError(f"{variant_where}.descriptors do not preserve exact placements and shape kinds")
    if canonical is None:
        raise ValidationError(f"{where}.variants did not contain descriptors")
    if has_authored_dimensions and consumed_dimension_keys != authored_dimension_keys:
        raise ValidationError(
            f"{where}.authored_dimensions must equal the complete descriptor-consumed control set"
        )
    canonical_points = {entry[0]: entry[1] for entry in canonical}
    canonical_parents = {entry[0]: entry[2] for entry in canonical}
    if parent_key not in canonical_points or child_key not in canonical_points:
        raise ValidationError(f"{where}.reference_scale must name descriptor addresses")
    candidates: list[tuple[int, tuple[str, tuple[str, ...], str, str], tuple[str, tuple[str, ...], str, str], list[int]]] = []
    for child, parent in canonical_parents.items():
        if parent is None:
            continue
        delta = [canonical_points[child][component] - canonical_points[parent][component] for component in range(3)]
        if any(component < SIGNED_I64_MIN or component > SIGNED_I64_MAX for component in delta):
            raise ValidationError(f"{where} descriptor edge exceeds the signed i64 domain")
        squared = sum(component * component for component in delta)
        if squared:
            candidates.append((squared, child, parent, delta))
    if not candidates:
        raise ValidationError(f"{where}.reference_scale has no nonzero descriptor edge")
    selected = min(candidates, key=lambda candidate: (candidate[0], candidate[1]))
    if (squared_length, child_key, parent_key, axis_delta) != (
        selected[0], selected[1], selected[2], selected[3]
    ):
        raise ValidationError(f"{where}.reference_scale does not match the selected descriptor edge")
    return obj


def _validate_review_structure_envelope(value: Any, where: str) -> dict[str, Any]:
    """Validate either supported structure-viewer projection format."""

    obj = _object(value, where)
    format_name = obj.get("format")
    if format_name == PREPARED_SOURCE_FORMAT:
        return _validate_prepared_source_envelope(obj, where)
    return _validate_structure_envelope(obj, where)


def _normalize_image_groups(
    groups: Any,
    manifest_path: Path,
    *,
    reserved_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, SourceReference]]:
    groups = _array(groups, "manifest.groups")
    if not groups:
        raise ValidationError("manifest.groups must not be empty")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set(reserved_ids or ())
    sources: dict[str, SourceReference] = {}
    for group_number, raw_group in enumerate(groups):
        where = f"manifest.groups[{group_number}]"
        group = _object(raw_group, where)
        _check_fields(group, {"id", "title", "description", "selection_mode", "items"}, where)
        group_id = validate_id(group.get("id"), f"{where}.id")
        if group_id in seen_ids:
            raise ValidationError(f"duplicate id: {group_id}")
        seen_ids.add(group_id)
        group_title = _string(group.get("title"), f"{where}.title", max_len=512)
        mode = group.get("selection_mode")
        if mode not in {"single", "multiple", "none"}:
            raise ValidationError(f"{where}.selection_mode must be single, multiple or none")
        items = _array(group.get("items"), f"{where}.items")
        if not items:
            raise ValidationError(f"{where}.items must not be empty")
        out_group: dict[str, Any] = {
            "id": group_id,
            "title": group_title,
            "selection_mode": mode,
            "items": [],
        }
        description = _optional_string(group, "description", where)
        if description is not None:
            out_group["description"] = description
        for item_number, raw_item in enumerate(items):
            item_where = f"{where}.items[{item_number}]"
            item = _object(raw_item, item_where)
            _check_fields(item, {"id", "title", "source", "description", "metadata"}, item_where)
            item_id = validate_id(item.get("id"), f"{item_where}.id")
            if item_id in seen_ids:
                raise ValidationError(f"duplicate id: {item_id}")
            seen_ids.add(item_id)
            item_title = _string(item.get("title"), f"{item_where}.title", max_len=512)
            source_value = _string(item.get("source"), f"{item_where}.source", max_len=4096)
            source_ref = resolve_source_reference(source_value, manifest_path, f"{item_where}.source")
            image_name = f"assets/{item_id}{source_ref.path.suffix.lower()}"
            out_item: dict[str, Any] = {"id": item_id, "title": item_title, "image": image_name}
            description = _optional_string(item, "description", item_where)
            if description is not None:
                out_item["description"] = description
            if "metadata" in item:
                out_item["metadata"] = _metadata(item["metadata"], f"{item_where}.metadata")
            out_group["items"].append(out_item)
            sources[item_id] = source_ref
        normalized.append(out_group)
    return normalized, sources


def _base_manifest(data: Any, manifest_path: Path) -> tuple[dict[str, Any], dict[str, SourceReference]]:
    obj = _object(data, "manifest")
    _check_fields(
        obj,
        {
            "schema_version",
            "id",
            "title",
            "description",
            "instructions",
            "subject_context",
            "kind",
            "groups",
            "structure_source",
            "provisional_form_source",
        },
        "manifest",
    )
    if obj.get("schema_version") != SCHEMA_VERSION or isinstance(
        obj.get("schema_version"), bool
    ):
        raise ValidationError("manifest.schema_version must be 1")
    review_id = validate_id(obj.get("id"), "manifest.id")
    title = _string(obj.get("title"), "manifest.title", max_len=512)
    kind = obj.get("kind", "image")
    if kind not in {"image", "structure", "provisional-form"}:
        raise ValidationError("manifest.kind must be image, structure or provisional-form")

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": review_id,
        "title": title,
        "kind": kind,
        "groups": [],
    }
    for key in ("description", "instructions"):
        value = _optional_string(obj, key, "manifest")
        if value is not None:
            result[key] = value
    if "subject_context" in obj:
        result["subject_context"] = _subject_context(obj["subject_context"], "manifest.subject_context")

    if kind == "structure":
        if "provisional_form_source" in obj:
            raise ValidationError(
                "manifest.provisional_form_source is only valid for provisional-form reviews"
            )
        if "structure_source" not in obj:
            raise ValidationError("manifest.structure_source is required for structure reviews")
        structure_source = _string(obj["structure_source"], "manifest.structure_source", max_len=4096)
        structure_ref = _resolve_file_reference(structure_source, manifest_path, "manifest.structure_source")
        structure = read_source_json(
            structure_ref,
            "manifest.structure_source",
            max_bytes=MAX_STRUCTURE_JSON_BYTES,
        )
        result["structure"] = _validate_review_structure_envelope(structure, "structure_source")
        # A structure review may carry optional image groups, but unlike an
        # image review it does not need any.
        if "groups" in obj:
            if not isinstance(obj["groups"], list):
                raise ValidationError("manifest.groups must be an array")
            if obj["groups"]:
                result["groups"], sources = _normalize_image_groups(
                    obj["groups"], manifest_path, reserved_ids={review_id}
                )
            else:
                sources = {}
        else:
            sources = {}
    elif kind == "provisional-form":
        if "provisional_form_source" not in obj:
            raise ValidationError(
                "manifest.provisional_form_source is required for provisional-form reviews"
            )
        if "structure_source" in obj:
            raise ValidationError(
                "manifest.structure_source is not valid for provisional-form reviews"
            )
        form_source = _string(
            obj["provisional_form_source"],
            "manifest.provisional_form_source",
            max_len=4096,
        )
        form_ref = _resolve_file_reference(
            form_source, manifest_path, "manifest.provisional_form_source"
        )
        form = read_source_json(
            form_ref,
            "manifest.provisional_form_source",
            max_bytes=MAX_STRUCTURE_JSON_BYTES,
        )
        result["provisional_form"] = _validate_provisional_form_envelope(
            form, "manifest.provisional_form_source"
        )
        if "groups" in obj and obj["groups"] not in ([], None):
            raise ValidationError("manifest.groups must be empty for provisional-form reviews")
        sources = {}
    else:
        if "structure_source" in obj:
            raise ValidationError("manifest.structure_source is only valid for structure reviews")
        if "provisional_form_source" in obj:
            raise ValidationError(
                "manifest.provisional_form_source is only valid for provisional-form reviews"
            )
        result["groups"], sources = _normalize_image_groups(
            obj.get("groups"), manifest_path, reserved_ids={review_id}
        )
    return result, sources


def normalize_rich_manifest(data: Any, manifest_path: Path) -> tuple[dict[str, Any], dict[str, SourceReference]]:
    """Validate a source manifest and return normalized review data and sources."""

    return _base_manifest(data, manifest_path)


def read_rich_manifest(manifest_path: Path) -> tuple[dict[str, Any], dict[str, SourceReference]]:
    if manifest_path.is_symlink():
        raise ValidationError("source manifest may not be a symlink")
    return normalize_rich_manifest(read_json(manifest_path), manifest_path)


def _validate_image_reference(image: Any, item_id: str, where: str) -> str:
    if not isinstance(image, str) or "\\" in image or "\x00" in image:
        raise ValidationError(f"{where}.image is invalid")
    parts = Path(image).parts
    if len(parts) != 2 or parts[0] != "assets" or parts[1].startswith("."):
        raise ValidationError(f"{where}.image must be a relative assets path")
    if parts[1].rsplit(".", 1)[0] != item_id:
        raise ValidationError(f"{where}.image does not match item id")
    if Path(image).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError(f"{where}.image has unsupported image type")
    return image


def validate_normalized_review(
    data: Any,
    session_dir: Path,
    *,
    check_assets: bool = True,
) -> dict[str, Any]:
    """Validate a session review.json and its referenced files."""

    obj = _object(data, "review")
    _check_fields(
        obj,
        {
            "schema_version",
            "id",
            "title",
            "description",
            "instructions",
            "subject_context",
            "kind",
            "groups",
            "structure",
            "provisional_form",
        },
        "review",
    )
    if obj.get("schema_version") != SCHEMA_VERSION or isinstance(obj.get("schema_version"), bool):
        raise ValidationError("review.schema_version must be 1")
    review_id = validate_id(obj.get("id"), "review.id")
    title = _string(obj.get("title"), "review.title", max_len=512)
    kind = obj.get("kind", "image")
    if kind not in {"image", "structure", "provisional-form"}:
        raise ValidationError("review.kind must be image, structure or provisional-form")
    if "structure" in obj:
        if kind != "structure":
            raise ValidationError("review.structure is only valid for structure reviews")
        if "provisional_form" in obj:
            raise ValidationError("review.provisional_form is only valid for provisional-form reviews")
        structure = _validate_review_structure_envelope(obj["structure"], "review.structure")
    elif kind == "structure":
        raise ValidationError("review.structure is required for structure reviews")
    elif "provisional_form" in obj:
        if kind != "provisional-form":
            raise ValidationError("review.provisional_form is only valid for provisional-form reviews")
        structure = None
        provisional_form = _validate_provisional_form_envelope(
            obj["provisional_form"], "review.provisional_form"
        )
    elif kind == "provisional-form":
        raise ValidationError("review.provisional_form is required for provisional-form reviews")
    else:
        structure = None
        provisional_form = None
    groups_value = obj.get("groups")
    groups = _array(groups_value, "review.groups")
    if kind == "image" and not groups:
        raise ValidationError("review.groups must not be empty")
    if kind == "provisional-form" and groups:
        raise ValidationError("review.groups must be empty for provisional-form reviews")
    result: dict[str, Any] = {
        "schema_version": 1,
        "id": review_id,
        "title": title,
        "kind": kind,
        "groups": [],
    }
    if structure is not None:
        result["structure"] = structure
    if kind == "provisional-form":
        result["provisional_form"] = provisional_form
    for key in ("description", "instructions"):
        value = _optional_string(obj, key, "review")
        if value is not None:
            result[key] = value
    if "subject_context" in obj:
        result["subject_context"] = _subject_context(obj["subject_context"], "review.subject_context")
    seen: set[str] = {review_id}
    images: set[str] = set()
    for group_number, raw_group in enumerate(groups):
        where = f"review.groups[{group_number}]"
        group = _object(raw_group, where)
        _check_fields(group, {"id", "title", "description", "selection_mode", "items"}, where)
        group_id = validate_id(group.get("id"), f"{where}.id")
        if group_id in seen:
            raise ValidationError(f"duplicate id: {group_id}")
        seen.add(group_id)
        group_title = _string(group.get("title"), f"{where}.title", max_len=512)
        mode = group.get("selection_mode")
        if mode not in {"single", "multiple", "none"}:
            raise ValidationError(f"{where}.selection_mode is invalid")
        items = _array(group.get("items"), f"{where}.items")
        if not items:
            raise ValidationError(f"{where}.items must not be empty")
        out_group: dict[str, Any] = {
            "id": group_id,
            "title": group_title,
            "selection_mode": mode,
            "items": [],
        }
        description = _optional_string(group, "description", where)
        if description is not None:
            out_group["description"] = description
        for item_number, raw_item in enumerate(items):
            item_where = f"{where}.items[{item_number}]"
            item = _object(raw_item, item_where)
            _check_fields(item, {"id", "title", "image", "description", "metadata"}, item_where)
            item_id = validate_id(item.get("id"), f"{item_where}.id")
            if item_id in seen:
                raise ValidationError(f"duplicate id: {item_id}")
            seen.add(item_id)
            item_title = _string(item.get("title"), f"{item_where}.title", max_len=512)
            image = _validate_image_reference(item.get("image"), item_id, item_where)
            if image in images:
                raise ValidationError(f"duplicate image: {image}")
            images.add(image)
            if check_assets:
                image_path = session_dir / Path(image)
                _reject_symlink_components(image_path, f"{item_where}.image")
                try:
                    info = image_path.stat()
                except OSError as exc:
                    raise ValidationError(f"missing image asset: {image}") from exc
                if not stat.S_ISREG(info.st_mode):
                    raise ValidationError(f"image asset is not a regular file: {image}")
            out_item: dict[str, Any] = {"id": item_id, "title": item_title, "image": image}
            description = _optional_string(item, "description", item_where)
            if description is not None:
                out_item["description"] = description
            if "metadata" in item:
                out_item["metadata"] = _metadata(item["metadata"], f"{item_where}.metadata")
            out_group["items"].append(out_item)
        result["groups"].append(out_group)
    return result


def load_session(root: Path, review_id: str) -> tuple[Path, dict[str, Any]]:
    validate_id(review_id, "review id")
    session = root / review_id
    if session.is_symlink() or not session.is_dir():
        raise ValidationError("review session does not exist")
    review_path = session / "review.json"
    if review_path.is_symlink() or not review_path.is_file():
        raise ValidationError("session has no valid review.json")
    data = validate_normalized_review(read_json(review_path), session)
    if data["id"] != review_id:
        raise ValidationError("session directory and review id differ")
    return session, data


def iter_sessions(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    valid_with_order: list[tuple[int, dict[str, Any]]] = []
    errors: list[dict[str, str]] = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        return [], [{"id": "reviews-root", "error": f"cannot list reviews root: {exc}"}]
    for entry in entries:
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        if entry.is_symlink():
            errors.append({"id": entry.name, "error": "session symlinks are not allowed"})
            continue
        try:
            session, review = load_session(root, entry.name)
            published_mtime_ns = (session / "review.json").stat().st_mtime_ns
            published_seconds, published_remainder_ns = divmod(
                published_mtime_ns,
                1_000_000_000,
            )
            published_at = datetime.fromtimestamp(
                published_seconds,
                timezone.utc,
            ).replace(
                microsecond=published_remainder_ns // 1_000,
            ).isoformat(timespec="microseconds").replace("+00:00", "Z")
        except (OverflowError, ValueError) as exc:
            errors.append({
                "id": entry.name,
                "error": f"invalid review.json publication timestamp: {exc}",
            })
        except (OSError, ValidationError) as exc:
            errors.append({"id": entry.name, "error": str(exc)})
        else:
            summary = {
                "id": review["id"],
                "title": review["title"],
                "kind": review.get("kind", "image"),
                "published_at": published_at,
                **({"description": review["description"]} if "description" in review else {}),
            }
            valid_with_order.append((published_mtime_ns, summary))
    valid_with_order.sort(key=lambda item: (-item[0], item[1]["id"]))
    valid = [summary for _, summary in valid_with_order]
    return valid, errors


def validate_response_payload(value: Any, review: dict[str, Any]) -> dict[str, Any]:
    obj = _object(value, "response")
    _check_fields(obj, {"schema_version", "review_id", "selections", "group_notes", "overall_note"}, "response")
    if obj.get("schema_version") != SCHEMA_VERSION or isinstance(obj.get("schema_version"), bool):
        raise ValidationError("response.schema_version must be 1")
    if obj.get("review_id") != review["id"]:
        raise ValidationError("response.review_id does not match the review")
    selections = _object(obj.get("selections"), "response.selections")
    group_notes = _object(obj.get("group_notes"), "response.group_notes")
    known_groups = {group["id"]: group for group in review["groups"]}
    if set(selections) - set(known_groups):
        raise ValidationError("response.selections contains an unknown group")
    if set(group_notes) - set(known_groups):
        raise ValidationError("response.group_notes contains an unknown group")
    normalized_selections: dict[str, list[str]] = {}
    normalized_notes: dict[str, str] = {}
    for group_id, group in known_groups.items():
        selected = selections.get(group_id, [])
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            raise ValidationError(f"selection for {group_id} must be an array of item ids")
        item_ids = {item["id"] for item in group["items"]}
        if len(selected) != len(set(selected)) or any(item not in item_ids for item in selected):
            raise ValidationError(f"selection for {group_id} contains an invalid item")
        if group["selection_mode"] == "single" and len(selected) > 1:
            raise ValidationError(f"selection for {group_id} allows only one item")
        if group["selection_mode"] == "none" and selected:
            raise ValidationError(f"selection is disabled for {group_id}")
        normalized_selections[group_id] = selected
        note = group_notes.get(group_id, "")
        if not isinstance(note, str) or len(note) > MAX_STRING:
            raise ValidationError(f"note for {group_id} must be a string")
        normalized_notes[group_id] = note
    overall = obj.get("overall_note", "")
    if not isinstance(overall, str) or len(overall) > MAX_STRING:
        raise ValidationError("response.overall_note must be a string")
    return {
        "schema_version": 1,
        "review_id": review["id"],
        "selections": normalized_selections,
        "group_notes": normalized_notes,
        "overall_note": overall,
    }


def load_response(session: Path, review: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    path = session / "response.json"
    if not path.exists() and not path.is_symlink():
        return None, None
    try:
        if path.is_symlink() or not path.is_file():
            raise ValidationError("response.json is not a regular file")
        stored = read_json(path)
        if not isinstance(stored, dict):
            raise ValidationError("response must be an object")
        saved_at = stored.get("saved_at")
        # A timestamp is server-owned.  Preserve it only if it is a string; a
        # malformed old response is reported below rather than being rendered.
        if not isinstance(saved_at, str):
            raise ValidationError("response.saved_at is missing")
        value = validate_response_payload({key: stored[key] for key in stored if key != "saved_at"}, review)
        return {**value, "saved_at": saved_at}, None
    except ValidationError as exc:
        return None, str(exc)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def ensure_root(root: Path) -> Path:
    root = root.absolute()
    _reject_symlink_components(root, "reviews root")
    if not root.is_dir():
        raise ValidationError("reviews root must already exist as a directory")
    return root

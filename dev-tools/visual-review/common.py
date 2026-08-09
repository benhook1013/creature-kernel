"""Shared validation and filesystem helpers for the local visual-review tool.

The review tool intentionally keeps its on-disk format small and boring.  This
module is used by both the publisher and the HTTP server so that a session
accepted by one is the same session understood by the other.
"""

from __future__ import annotations

import json
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
MAX_STRING = 8192
MAX_CONTEXT_JSON = MAX_STRING
_HAS_DIR_FD_OPEN = os.open in getattr(os, "supports_dir_fd", set())
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
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
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


def _metadata(value: Any, where: str, *, max_len: int = MAX_CONTEXT_JSON) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{where} must be an object")
    # JSON data is retained as metadata and displayed with textContent by the
    # client.  Reject non-finite numbers and excessively deep/large values in
    # practical cases without imposing a domain-specific metadata vocabulary.
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{where} is not JSON-compatible: {exc}") from exc
    if len(encoded) > max_len:
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
            result[key] = _metadata(context[key], f"{where}.{key}")
    try:
        encoded = json.dumps(result, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{where} is not JSON-compatible: {exc}") from exc
    if len(encoded) > MAX_CONTEXT_JSON:
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


def _base_manifest(data: Any, manifest_path: Path) -> tuple[dict[str, Any], dict[str, SourceReference]]:
    obj = _object(data, "manifest")
    _check_fields(
        obj,
        {"schema_version", "id", "title", "description", "instructions", "subject_context", "groups"},
        "manifest",
    )
    if obj.get("schema_version") != SCHEMA_VERSION or isinstance(
        obj.get("schema_version"), bool
    ):
        raise ValidationError("manifest.schema_version must be 1")
    review_id = validate_id(obj.get("id"), "manifest.id")
    title = _string(obj.get("title"), "manifest.title", max_len=512)
    groups = _array(obj.get("groups"), "manifest.groups")
    if not groups:
        raise ValidationError("manifest.groups must not be empty")

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": review_id,
        "title": title,
        "groups": [],
    }
    for key in ("description", "instructions"):
        value = _optional_string(obj, key, "manifest")
        if value is not None:
            result[key] = value
    if "subject_context" in obj:
        result["subject_context"] = _subject_context(obj["subject_context"], "manifest.subject_context")

    seen_ids: set[str] = {review_id}
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
        result["groups"].append(out_group)
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
        {"schema_version", "id", "title", "description", "instructions", "subject_context", "groups"},
        "review",
    )
    if obj.get("schema_version") != SCHEMA_VERSION or isinstance(obj.get("schema_version"), bool):
        raise ValidationError("review.schema_version must be 1")
    review_id = validate_id(obj.get("id"), "review.id")
    title = _string(obj.get("title"), "review.title", max_len=512)
    groups = _array(obj.get("groups"), "review.groups")
    if not groups:
        raise ValidationError("review.groups must not be empty")
    result: dict[str, Any] = {"schema_version": 1, "id": review_id, "title": title, "groups": []}
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
    valid: list[dict[str, Any]] = []
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
            _, review = load_session(root, entry.name)
        except ValidationError as exc:
            errors.append({"id": entry.name, "error": str(exc)})
        else:
            valid.append({
                "id": review["id"],
                "title": review["title"],
                **({"description": review["description"]} if "description" in review else {}),
            })
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
    if root.is_symlink() or not root.is_dir():
        raise ValidationError("reviews root must already exist as a directory")
    return root

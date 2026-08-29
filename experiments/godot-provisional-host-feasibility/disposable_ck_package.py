#!/usr/bin/env python3
"""Build and validate a disposable directory payload for two CK avatars.

This is an experiment-local producer.  It copies the already validated
projection inputs into a deterministic directory so a later host probe need
not read the gallery.  The manifest identity is transport bookkeeping only;
this module does not define a CK package, adapter, resolver, or runtime
contract.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


sys.dont_write_bytecode = True


SCHEMA = "creature-kernel.disposable-ck-directory-payload.v1"
BOUNDARY = "experiment_local_directory_payload_evidence_only"
MANIFEST_FILE = "manifest.json"
AVATARS_DIRECTORY = "avatars"
SOURCE_FILE = "source.json"
METRICS_FILE = "metrics.json"

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_CONTENT_BYTES = 128 * 1024 * 1024
MAX_JSON_NODES = 200_000
MAX_JSON_DEPTH = 96
MAX_STRING_LENGTH = 65_536
MAX_TREE_ENTRIES = 256

MANIFEST_BODY_KEYS = ("schema", "boundary", "projection_identity", "avatars")
MANIFEST_KEYS = ("schema", "boundary", "manifest_identity", "projection_identity", "avatars")
MANIFEST_IDENTITY_KEYS = ("scope", "sha256", "bytes")
MANIFEST_IDENTITY_SCOPE = "canonical_transport_manifest_body_only_not_provenance"
AVATAR_KEYS = (
    "ordinal",
    "instance_id",
    "profile_id",
    "candidate_profile_sha256",
    "runtime_input_inspection",
    "source",
    "artifacts",
    "metrics",
)
SOURCE_KEYS = ("path", "sha256", "bytes", "document", "namespace")
FILE_KEYS = ("path", "sha256", "bytes")

HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
FORBIDDEN_FIELD_TOKENS = {
    "adapter",
    "godot",
    "host",
    "package",
    "readiness",
    "resolver",
    "snapshot",
    "wire",
}


class PackageError(ValueError):
    """A bounded, fail-closed payload validation or publication failure."""


def _load_projection_module():
    try:
        import disposable_ck_projection as module  # type: ignore
    except ImportError:  # pragma: no cover - package import path
        from . import disposable_ck_projection as module  # type: ignore
    return module


def _canonical_json(value: object) -> bytes:
    try:
        return (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise PackageError("manifest cannot be encoded as canonical finite JSON") from exc


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _finite_json(value: object, where: str = "manifest", *, depth: int = 0, state: list[int] | None = None) -> None:
    if state is None:
        state = [0]
    state[0] += 1
    if state[0] > MAX_JSON_NODES:
        raise PackageError(f"{where} exceeds the bounded JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise PackageError(f"{where} exceeds the bounded JSON depth")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PackageError(f"{where} contains a non-finite number")
    elif isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 10**15:
            raise PackageError(f"{where} contains an unbounded integer")
    elif isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise PackageError(f"{where} contains an overlong string")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite_json(item, f"{where}[{index}]", depth=depth + 1, state=state)
    elif isinstance(value, dict):
        if len(value) > 2048:
            raise PackageError(f"{where} contains an oversized object")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_LENGTH:
                raise PackageError(f"{where} contains an invalid object key")
            _finite_json(item, f"{where}.{key}", depth=depth + 1, state=state)
    elif value is not None and not isinstance(value, bool):
        raise PackageError(f"{where} contains an unsupported JSON value")


def _exact_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def _absolute_path(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise PackageError(f"{label} must be an absolute path: {path}")
    return path


def _reject_symlink_components(path: Path, label: str) -> None:
    absolute = path if path.is_absolute() else Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        except OSError as exc:
            raise PackageError(f"could not inspect {label} path components: {path}") from exc
        if stat.S_ISLNK(mode):
            raise PackageError(f"{label} or one of its path components is a symlink: {path}")


def _regular_directory(path: Path, label: str) -> os.stat_result:
    _reject_symlink_components(path, label)
    try:
        info = path.lstat()
    except OSError as exc:
        raise PackageError(f"{label} is unavailable: {path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise PackageError(f"{label} must be a regular non-symlink directory: {path}")
    return info


def _read_regular_file(carrier_module: object, path: Path, maximum: int, label: str) -> bytes:
    try:
        return carrier_module._read_regular_file(path, maximum, label)  # type: ignore[attr-defined]
    except PackageError:
        raise
    except Exception as exc:
        raise PackageError(f"{label} could not be read safely: {type(exc).__name__}: {exc}") from exc


def _object(value: object, label: str, keys: tuple[str, ...]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise PackageError(f"{label} has unexpected or missing fields")
    return value


def _string(value: object, label: str) -> str:
    if type(value) is not str or not value or len(value) > MAX_STRING_LENGTH:
        raise PackageError(f"{label} must be a bounded non-empty string")
    return value


def _integer(value: object, label: str, *, maximum: int = MAX_FILE_BYTES) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise PackageError(f"{label} must be a bounded non-negative integer")
    return value


def _hash(value: object, label: str) -> str:
    value = _string(value, label)
    if HASH_PATTERN.fullmatch(value) is None:
        raise PackageError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _safe_relative(value: object, label: str) -> str:
    value = _string(value, label)
    if value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", value) or "\\" in value or "\x00" in value:
        raise PackageError(f"{label} must be a safe relative POSIX path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or str(parsed) != value or any(part in {"", ".", ".."} for part in parsed.parts):
        raise PackageError(f"{label} must be a safe relative POSIX path")
    return value


def _reject_forbidden_fields(value: object, where: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if any(normalized == token or normalized.startswith(token + "_") for token in FORBIDDEN_FIELD_TOKENS):
                raise PackageError(f"{where} contains a forbidden field: {key}")
            _reject_forbidden_fields(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_fields(item, f"{where}[{index}]")


def _reject_absolute_strings(value: object, where: str = "manifest") -> None:
    if isinstance(value, str):
        if value.startswith(("/", "\\", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value):
            raise PackageError(f"{where} contains an absolute path")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_absolute_strings(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_absolute_strings(item, f"{where}[{index}]")


def _artifact_names(projection_module: object, carrier_module: object) -> tuple[str, ...]:
    try:
        names = tuple(projection_module._artifact_names(carrier_module))  # type: ignore[attr-defined]
    except Exception as exc:
        raise PackageError("existing projection did not expose its exact six-artifact contract") from exc
    if len(names) != 6 or any(type(name) is not str for name in names):
        raise PackageError("existing projection artifact contract is not exactly six names")
    return names


def _validate_file_record(value: object, label: str) -> dict[str, object]:
    record = _object(value, label, FILE_KEYS)
    _safe_relative(record["path"], f"{label}.path")
    _hash(record["sha256"], f"{label}.sha256")
    _integer(record["bytes"], f"{label}.bytes")
    return record


def _validate_manifest_body(value: object, projection_module: object, carrier_module: object) -> dict[str, object]:
    body = _object(value, "manifest body", MANIFEST_BODY_KEYS)
    if body["schema"] != SCHEMA or body["boundary"] != BOUNDARY:
        raise PackageError("manifest schema or experiment boundary is invalid")
    projection_identity = _object(body["projection_identity"], "projection_identity", ("scope", "sha256", "bytes"))
    if projection_identity["scope"] != projection_module.PROJECTION_IDENTITY_SCOPE:  # type: ignore[attr-defined]
        raise PackageError("projection_identity does not identify the existing transport-only projection")
    _hash(projection_identity["sha256"], "projection_identity.sha256")
    _integer(projection_identity["bytes"], "projection_identity.bytes", maximum=projection_module.MAX_PROJECTION_BYTES)  # type: ignore[attr-defined]

    avatars = body["avatars"]
    if not isinstance(avatars, list) or len(avatars) != 2:
        raise PackageError("manifest must contain exactly two ordered avatars")
    artifact_names = _artifact_names(projection_module, carrier_module)
    total = 0
    for index, raw in enumerate(avatars):
        avatar = _object(raw, f"avatars[{index}]", AVATAR_KEYS)
        if avatar["ordinal"] != index:
            raise PackageError(f"avatars[{index}].ordinal does not bind the fixed ordered slot")
        _integer(avatar["ordinal"], f"avatars[{index}].ordinal", maximum=1)
        _string(avatar["instance_id"], f"avatars[{index}].instance_id")
        if carrier_module.INSTANCE_ID_PATTERN.fullmatch(avatar["instance_id"]) is None:  # type: ignore[attr-defined]
            raise PackageError(f"avatars[{index}].instance_id is not a safe carrier instance identity")
        _string(avatar["profile_id"], f"avatars[{index}].profile_id")
        _hash(avatar["candidate_profile_sha256"], f"avatars[{index}].candidate_profile_sha256")
        try:
            projection_module._validate_runtime_input_evidence(  # type: ignore[attr-defined]
                avatar["runtime_input_inspection"], f"avatars[{index}].runtime_input_inspection"
            )
        except PackageError:
            raise
        except Exception as exc:
            raise PackageError(f"avatars[{index}].runtime_input_inspection is not valid projection evidence") from exc

        source = _object(avatar["source"], f"avatars[{index}].source", SOURCE_KEYS)
        expected_source_path = f"{AVATARS_DIRECTORY}/{index}/{SOURCE_FILE}"
        if _safe_relative(source["path"], f"avatars[{index}].source.path") != expected_source_path:
            raise PackageError(f"avatars[{index}].source.path is not the fixed payload path")
        _hash(source["sha256"], f"avatars[{index}].source.sha256")
        source_bytes = _integer(source["bytes"], f"avatars[{index}].source.bytes")
        total += source_bytes
        _string(source["document"], f"avatars[{index}].source.document")
        _string(source["namespace"], f"avatars[{index}].source.namespace")

        artifacts = avatar["artifacts"]
        if not isinstance(artifacts, list) or len(artifacts) != 6:
            raise PackageError(f"avatars[{index}].artifacts must contain exactly six ordered files")
        for artifact_index, artifact_name in enumerate(artifact_names):
            record = _validate_file_record(artifacts[artifact_index], f"avatars[{index}].artifacts[{artifact_index}]")
            expected_path = f"{AVATARS_DIRECTORY}/{index}/{artifact_name}"
            if record["path"] != expected_path:
                raise PackageError(f"avatars[{index}].artifacts[{artifact_index}] is not the fixed ordered file")
            total += record["bytes"]  # type: ignore[operator]

        metrics = _validate_file_record(avatar["metrics"], f"avatars[{index}].metrics")
        if metrics["path"] != f"{AVATARS_DIRECTORY}/{index}/{METRICS_FILE}":
            raise PackageError(f"avatars[{index}].metrics.path is not the fixed payload path")
        total += metrics["bytes"]  # type: ignore[operator]
    if len({avatar["instance_id"] for avatar in avatars}) != 2:
        raise PackageError("manifest instance identities must be distinct")
    if len({avatar["profile_id"] for avatar in avatars}) != 2:
        raise PackageError("manifest profile identities must be distinct")
    if total > MAX_CONTENT_BYTES:
        raise PackageError(f"manifest content exceeds the bounded total of {MAX_CONTENT_BYTES} bytes")
    _finite_json(body)
    _reject_forbidden_fields(body)
    _reject_absolute_strings(body)
    return body


def _transport_identity(body: dict[str, object]) -> dict[str, object]:
    canonical = _canonical_json(body)
    return {
        "scope": MANIFEST_IDENTITY_SCOPE,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "bytes": len(canonical),
    }


def identify_manifest(value: object, *, projection_module: object | None = None, carrier_module: object | None = None) -> dict[str, object]:
    """Attach only the disposable transport identity to a validated body."""
    projection_module = projection_module or _load_projection_module()
    carrier_module = carrier_module or projection_module._load_carrier_module()  # type: ignore[attr-defined]
    if not isinstance(value, dict) or set(value) not in (set(MANIFEST_BODY_KEYS), set(MANIFEST_KEYS)):
        raise PackageError("manifest to identify has unexpected or missing fields")
    body = {key: value[key] for key in MANIFEST_BODY_KEYS}
    _validate_manifest_body(body, projection_module, carrier_module)
    return {**body, "manifest_identity": _transport_identity(body)}


def _validate_manifest_shape(value: object, projection_module: object | None = None, carrier_module: object | None = None) -> dict[str, object]:
    projection_module = projection_module or _load_projection_module()
    carrier_module = carrier_module or projection_module._load_carrier_module()  # type: ignore[attr-defined]
    root = _object(value, "manifest", MANIFEST_KEYS)
    body = {key: root[key] for key in MANIFEST_BODY_KEYS}
    _validate_manifest_body(body, projection_module, carrier_module)
    identity = _object(root["manifest_identity"], "manifest_identity", MANIFEST_IDENTITY_KEYS)
    if identity["scope"] != MANIFEST_IDENTITY_SCOPE:
        raise PackageError("manifest_identity does not declare its transport-only scope")
    _hash(identity["sha256"], "manifest_identity.sha256")
    _integer(identity["bytes"], "manifest_identity.bytes", maximum=MAX_MANIFEST_BYTES)
    if not _exact_equal(identity, _transport_identity(body)):
        raise PackageError("manifest_identity does not match the canonical transport body")
    encoded = _canonical_json(root)
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise PackageError(f"manifest exceeds the bounded size of {MAX_MANIFEST_BYTES} bytes")
    return root


def _parse_json_bytes(data: bytes, label: str) -> object:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise PackageError(f"{label} is not valid finite UTF-8 JSON") from exc
    _finite_json(value, label)
    return value


def _package_root(path: Path, *, must_exist: bool) -> Path:
    path = _absolute_path(path, "package path")
    _reject_symlink_components(path, "package path")
    if not must_exist:
        try:
            path.lstat()
        except FileNotFoundError:
            return path
        except OSError as exc:
            raise PackageError(f"could not inspect package destination: {path}") from exc
        raise PackageError(f"package destination already exists: {path}")
    _regular_directory(path, "package path")
    return path


def _scan_package(root: Path) -> tuple[set[str], set[str]]:
    _regular_directory(root, "package root")
    files: set[str] = set()
    directories: set[str] = set()
    entry_count = 0

    def walk(directory: Path, relative: str) -> None:
        nonlocal entry_count
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise PackageError(f"could not scan package directory: {directory}") from exc
        for entry in entries:
            entry_count += 1
            if entry_count > MAX_TREE_ENTRIES:
                raise PackageError(f"package tree exceeds the bounded entry count of {MAX_TREE_ENTRIES}")
            child_relative = entry.name if not relative else f"{relative}/{entry.name}"
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise PackageError(f"could not inspect package entry: {child_relative}") from exc
            if stat.S_ISLNK(info.st_mode):
                raise PackageError(f"package entry is a symlink: {child_relative}")
            if stat.S_ISDIR(info.st_mode):
                directories.add(child_relative)
                walk(Path(entry.path), child_relative)
            elif stat.S_ISREG(info.st_mode):
                files.add(child_relative)
            else:
                raise PackageError(f"package entry is not a regular file or directory: {child_relative}")

    walk(root, "")
    return files, directories


def _expected_inventory(artifact_names: tuple[str, ...]) -> tuple[set[str], set[str]]:
    files = {MANIFEST_FILE}
    directories = {AVATARS_DIRECTORY}
    for index in range(2):
        prefix = f"{AVATARS_DIRECTORY}/{index}"
        directories.add(prefix)
        files.add(f"{prefix}/{SOURCE_FILE}")
        files.update(f"{prefix}/{name}" for name in artifact_names)
        files.add(f"{prefix}/{METRICS_FILE}")
    return files, directories


def _manifest_file_records(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(manifest["avatars"]):  # type: ignore[index]
        avatar = raw  # type: ignore[assignment]
        candidates = [avatar["source"], *avatar["artifacts"], avatar["metrics"]]  # type: ignore[index]
        for item in candidates:
            record = item  # type: ignore[assignment]
            path = record["path"]  # type: ignore[index]
            if path in records:
                raise PackageError(f"manifest contains a duplicate file path: {path}")
            records[path] = record  # type: ignore[assignment]
    return records


def _verify_manifest_files(
    root: Path,
    manifest: dict[str, object],
    projection_module: object,
    carrier_module: object,
) -> None:
    records = _manifest_file_records(manifest)
    total = 0
    for relative, record in records.items():
        data = _read_regular_file(carrier_module, root / relative, MAX_FILE_BYTES, f"package file {relative}")
        actual_hash = hashlib.sha256(data).hexdigest()
        if len(data) != record["bytes"] or actual_hash != record["sha256"]:  # type: ignore[operator]
            raise PackageError(f"package file hash or byte count mismatch: {relative}")
        if relative.endswith(f"/{SOURCE_FILE}"):
            avatar_index = relative.split("/")[1]
            source = manifest["avatars"][int(avatar_index)]["source"]  # type: ignore[index]
            _validate_copied_source_dependencies(
                data,
                relative,
                projection_module=projection_module,
                expected_document=source["document"],  # type: ignore[index]
                expected_namespace=source["namespace"],  # type: ignore[index]
            )
        elif relative.endswith(f"/{METRICS_FILE}"):
            avatar_index = relative.split("/")[1]
            avatar = manifest["avatars"][int(avatar_index)]  # type: ignore[index]
            _validate_copied_metrics(data, relative, avatar["profile_id"])  # type: ignore[index]
        elif relative.endswith(("/skeleton.json", "/weights.json", "/proxies-neutral.json", "/proxies-posed.json")):
            avatar_index = relative.split("/")[1]
            avatar = manifest["avatars"][int(avatar_index)]  # type: ignore[index]
            _validate_profile_bearing_artifact(data, relative, avatar["profile_id"])  # type: ignore[index]
        total += len(data)
    if total > MAX_CONTENT_BYTES:
        raise PackageError(f"package content exceeds the bounded total of {MAX_CONTENT_BYTES} bytes")


def load_manifest(path: Path) -> dict[str, object]:
    """Load, inventory-check, and hash-check one disposable payload."""
    projection_module = _load_projection_module()
    carrier_module = projection_module._load_carrier_module()  # type: ignore[attr-defined]
    root = _package_root(path, must_exist=True)
    files, directories = _scan_package(root)
    expected_files, expected_directories = _expected_inventory(_artifact_names(projection_module, carrier_module))
    if files != expected_files or directories != expected_directories:
        raise PackageError("package tree does not contain the exact expected files and directories")
    data = _read_regular_file(carrier_module, root / MANIFEST_FILE, MAX_MANIFEST_BYTES, "package manifest")
    value = _parse_json_bytes(data, "package manifest")
    manifest = _validate_manifest_shape(value, projection_module, carrier_module)
    if data != _canonical_json(manifest):
        raise PackageError("package manifest is not canonical newline-terminated JSON")
    _verify_manifest_files(root, manifest, projection_module, carrier_module)
    return manifest


def _fresh_projection(
    gallery: Path,
    carrier_path: Path,
    projection_path: Path,
    cli_path: Path | None,
    label: str,
) -> tuple[object, object, object]:
    gallery = _absolute_path(gallery, "gallery path")
    carrier_path = _absolute_path(carrier_path, "carrier path")
    projection_path = _absolute_path(projection_path, "projection path")
    if cli_path is None:
        raise PackageError("an explicit absolute Rust CLI path is required")
    cli_path = _absolute_path(cli_path, "Rust CLI path")
    projection_module = _load_projection_module()
    carrier_module = projection_module._load_carrier_module()  # type: ignore[attr-defined]
    try:
        projection = projection_module.validate_projection(  # type: ignore[attr-defined]
            projection_path, gallery, carrier_path, cli_path=cli_path
        )
    except Exception as exc:
        raise PackageError(f"{label} projection/carrier/gallery validation failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(projection, dict):
        raise PackageError(f"{label} projection validator did not return an object")
    return projection_module, carrier_module, projection


def _gallery_file(carrier_module: object, gallery: Path, relative: str, label: str) -> bytes:
    _safe_relative(relative, f"{label}.path")
    return _read_regular_file(carrier_module, gallery / relative, MAX_FILE_BYTES, label)


def _collect_payload_files(
    projection_module: object,
    carrier_module: object,
    projection: dict[str, object],
    gallery: Path,
) -> tuple[dict[str, bytes], dict[str, object]]:
    avatars = projection.get("avatars")
    if not isinstance(avatars, list) or len(avatars) != 2:
        raise PackageError("validated projection must contain exactly two ordered avatars")
    artifact_names = _artifact_names(projection_module, carrier_module)
    files: dict[str, bytes] = {}
    manifest_avatars: list[dict[str, object]] = []
    total = 0
    for index, raw in enumerate(avatars):
        if not isinstance(raw, dict):
            raise PackageError(f"validated projection avatar {index} is not an object")
        profile_id = raw.get("profile_id")
        if type(profile_id) is not str:
            raise PackageError(f"validated projection avatar {index} has no exact profile identity")
        source = raw.get("source")
        if not isinstance(source, dict) or set(source) != set(projection_module.SOURCE_KEYS):  # type: ignore[attr-defined]
            raise PackageError(f"validated projection avatar {index} has an invalid source record")
        source_relative = source["path"]
        source_data = _gallery_file(carrier_module, gallery, source_relative, f"source {profile_id}")  # type: ignore[arg-type]
        if len(source_data) != source["bytes"] or hashlib.sha256(source_data).hexdigest() != source["sha256"]:  # type: ignore[operator]
            raise PackageError(f"source {profile_id} changed or disagrees with projection identity")
        package_source_path = f"{AVATARS_DIRECTORY}/{index}/{SOURCE_FILE}"
        files[package_source_path] = source_data
        source_record = {
            "path": package_source_path,
            "sha256": hashlib.sha256(source_data).hexdigest(),
            "bytes": len(source_data),
            "document": source["document"],
            "namespace": source["namespace"],
        }
        total += len(source_data)

        artifacts = raw.get("artifacts")
        if not isinstance(artifacts, list) or len(artifacts) != 6:
            raise PackageError(f"validated projection avatar {index} has an invalid artifact list")
        package_artifacts: list[dict[str, object]] = []
        for artifact_index, artifact_name in enumerate(artifact_names):
            artifact = artifacts[artifact_index]
            if not isinstance(artifact, dict) or set(artifact) != set(projection_module.ARTIFACT_KEYS):  # type: ignore[attr-defined]
                raise PackageError(f"validated projection avatar {index} artifact {artifact_index} is invalid")
            gallery_relative = artifact["path"]
            data = _gallery_file(carrier_module, gallery, gallery_relative, f"artifact {gallery_relative}")  # type: ignore[arg-type]
            if len(data) != artifact["bytes"] or hashlib.sha256(data).hexdigest() != artifact["sha256"]:  # type: ignore[operator]
                raise PackageError(f"artifact {gallery_relative} changed or disagrees with projection identity")
            package_relative = f"{AVATARS_DIRECTORY}/{index}/{artifact_name}"
            files[package_relative] = data
            package_artifacts.append({"path": package_relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            total += len(data)

        metrics_relative = f"{profile_id}/{METRICS_FILE}"
        metrics_data = _gallery_file(carrier_module, gallery, metrics_relative, f"metrics {profile_id}")
        metrics_value = _parse_json_bytes(metrics_data, f"metrics {profile_id}")
        if not _exact_equal(metrics_value, raw.get("metrics")):
            raise PackageError(f"metrics {profile_id} changed or disagrees with projection evidence")
        package_metrics_path = f"{AVATARS_DIRECTORY}/{index}/{METRICS_FILE}"
        files[package_metrics_path] = metrics_data
        package_metrics = {"path": package_metrics_path, "sha256": hashlib.sha256(metrics_data).hexdigest(), "bytes": len(metrics_data)}
        total += len(metrics_data)
        if total > MAX_CONTENT_BYTES:
            raise PackageError(f"copied payload exceeds the bounded total of {MAX_CONTENT_BYTES} bytes")

        manifest_avatars.append(
            {
                "ordinal": index,
                "instance_id": raw.get("instance_id"),
                "profile_id": profile_id,
                "candidate_profile_sha256": raw.get("candidate_profile_sha256"),
                "runtime_input_inspection": deepcopy(raw.get("runtime_input_inspection")),
                "source": source_record,
                "artifacts": package_artifacts,
                "metrics": package_metrics,
            }
        )
    body = {
        "schema": SCHEMA,
        "boundary": BOUNDARY,
        "projection_identity": deepcopy(projection.get("projection_identity")),
        "avatars": manifest_avatars,
    }
    _validate_manifest_body(body, projection_module, carrier_module)
    return files, body


def _manifest_from_projection(
    projection_module: object,
    carrier_module: object,
    projection: dict[str, object],
    gallery: Path,
) -> tuple[dict[str, bytes], dict[str, object]]:
    files, body = _collect_payload_files(projection_module, carrier_module, projection, gallery)
    manifest = {**body, "manifest_identity": _transport_identity(body)}
    _validate_manifest_shape(manifest, projection_module, carrier_module)
    if len(_canonical_json(manifest)) > MAX_MANIFEST_BYTES:
        raise PackageError(f"manifest exceeds the bounded size of {MAX_MANIFEST_BYTES} bytes")
    return files, manifest


def _directory_open_flags(carrier_module: object) -> int:
    try:
        return carrier_module._directory_open_flags()  # type: ignore[attr-defined]
    except Exception as exc:
        raise PackageError("existing carrier did not expose its no-follow directory opener") from exc


def _open_directory_descriptor(path: Path, label: str) -> int:
    projection_module = _load_projection_module()
    carrier_module = projection_module._load_carrier_module()  # type: ignore[attr-defined]
    try:
        return carrier_module._open_directory_descriptor(path, label)  # type: ignore[attr-defined]
    except PackageError:
        raise
    except Exception as exc:
        raise PackageError(f"could not open {label} without following symlinks: {path}") from exc


def _open_directory_at(parent_fd: int, name: str, path: Path, label: str) -> int:
    directory_fd: int | None = None
    try:
        carrier_module = _load_projection_module()._load_carrier_module()  # type: ignore[attr-defined]
        directory_fd = os.open(name, _directory_open_flags(carrier_module), dir_fd=parent_fd)
        info = os.fstat(directory_fd)
        if not stat.S_ISDIR(info.st_mode):
            raise PackageError(f"{label} must be a regular non-symlink directory: {path}")
        return directory_fd
    except PackageError:
        if directory_fd is not None:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        raise
    except (OSError, NotImplementedError, TypeError) as exc:
        if directory_fd is not None:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        raise PackageError(f"could not open {label}: {path}") from exc


def _directory_identity(path: Path, label: str, *, parent_fd: int | None = None) -> tuple[int, int]:
    path = Path(path)
    absolute = path if path.is_absolute() else Path(os.path.abspath(path))
    owns_parent_fd = parent_fd is None
    if owns_parent_fd:
        parent_fd = _open_directory_descriptor(absolute.parent, f"{label} parent")
    directory_fd: int | None = None
    try:
        directory_fd = _open_directory_at(parent_fd, absolute.name, absolute, label)
        info = os.fstat(directory_fd)
        if not stat.S_ISDIR(info.st_mode):
            raise PackageError(f"{label} must be a regular non-symlink directory: {path}")
        return info.st_dev, info.st_ino
    except OSError as exc:
        raise PackageError(f"could not inspect {label}: {path}") from exc
    finally:
        if directory_fd is not None:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        if owns_parent_fd:
            try:
                os.close(parent_fd)
            except OSError:
                pass


def _create_destination(path: Path) -> tuple[Path, tuple[int, int]]:
    path = _package_root(path, must_exist=False)
    _regular_directory(path.parent, "package output parent")
    parent_fd: int | None = None
    identity: tuple[int, int] | None = None
    try:
        parent_fd = _open_directory_descriptor(path.parent, "package output parent")
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise PackageError(f"package destination already exists: {path}") from exc
        except (OSError, NotImplementedError, TypeError) as exc:
            raise PackageError(f"could not create package destination: {path}") from exc

        try:
            # Capture the created directory identity through the already
            # anchored parent descriptor before the diagnostic lstat.  If
            # lstat is interrupted after mkdir, cleanup can still be attempted
            # against this bounded identity.
            identity = _directory_identity(path, "new package destination", parent_fd=parent_fd)
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise PackageError(f"new package destination must be a regular non-symlink directory: {path}")
            if (info.st_dev, info.st_ino) != identity:
                raise PackageError(f"new package destination changed while being inspected: {path}")
            return path, identity
        except Exception as exc:
            if identity is not None:
                _cleanup_created_destination(path, identity)
            if isinstance(exc, PackageError):
                raise
            raise PackageError(f"could not inspect new package destination: {path}") from exc
    finally:
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except OSError:
                pass


def _make_layout(root: Path) -> None:
    root = Path(root)
    absolute = root if root.is_absolute() else Path(os.path.abspath(root))
    root_fd = _open_directory_descriptor(absolute, "package root")
    avatars_fd: int | None = None
    try:
        try:
            os.mkdir(AVATARS_DIRECTORY, mode=0o700, dir_fd=root_fd)
        except FileExistsError as exc:
            raise PackageError(f"package layout path already exists: {AVATARS_DIRECTORY}") from exc
        except (OSError, NotImplementedError, TypeError) as exc:
            raise PackageError(f"could not create package layout path: {AVATARS_DIRECTORY}") from exc

        avatars_fd = _open_directory_at(
            root_fd,
            AVATARS_DIRECTORY,
            absolute / AVATARS_DIRECTORY,
            f"package layout directory {AVATARS_DIRECTORY}",
        )
        for index in range(2):
            relative = f"{AVATARS_DIRECTORY}/{index}"
            name = str(index)
            try:
                os.mkdir(name, mode=0o700, dir_fd=avatars_fd)
            except FileExistsError as exc:
                raise PackageError(f"package layout path already exists: {relative}") from exc
            except (OSError, NotImplementedError, TypeError) as exc:
                raise PackageError(f"could not create package layout path: {relative}") from exc
    finally:
        if avatars_fd is not None:
            try:
                os.close(avatars_fd)
            except OSError:
                pass
        try:
            os.close(root_fd)
        except OSError:
            pass


def _write_new_file(path: Path, data: bytes, label: str) -> None:
    path = Path(path)
    absolute = path if path.is_absolute() else Path(os.path.abspath(path))
    parent_fd = _open_directory_descriptor(absolute.parent, f"{label} parent")
    fd: int | None = None
    try:
        fd = os.open(
            absolute.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=parent_fd,
        )
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("package file write made no progress")
            view = view[written:]
        os.fsync(fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size != len(data):
            raise PackageError(f"{label} is incomplete after writing")
    except PackageError:
        raise
    except OSError as exc:
        raise PackageError(f"could not write {label}: {path}") from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.close(parent_fd)
        except OSError:
            pass


def _verify_copied_files(root: Path, files: dict[str, bytes], *, include_manifest: bool) -> None:
    expected_files = set(files)
    if include_manifest:
        expected_files.add(MANIFEST_FILE)
    actual_files, actual_directories = _scan_package(root)
    expected_directories = {AVATARS_DIRECTORY, f"{AVATARS_DIRECTORY}/0", f"{AVATARS_DIRECTORY}/1"}
    if actual_files != expected_files or actual_directories != expected_directories:
        raise PackageError("copied package tree does not contain the exact expected inventory")
    carrier_module = _load_projection_module()._load_carrier_module()  # type: ignore[attr-defined]
    for relative, expected in files.items():
        actual = _read_regular_file(carrier_module, root / relative, MAX_FILE_BYTES, f"copied file {relative}")
        if actual != expected or hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest():
            raise PackageError(f"copied file bytes differ from the validated source: {relative}")


def _validate_copied_source_dependencies(
    data: bytes,
    label: str,
    *,
    projection_module: object | None = None,
    expected_document: object | None = None,
    expected_namespace: object | None = None,
) -> None:
    parsed = _parse_json_bytes(data, f"copied source {label}")
    source = parsed.get("source") if isinstance(parsed, dict) else None
    projection_module = projection_module or _load_projection_module()
    try:
        source = projection_module._validate_source_identity(source, f"copied source {label}.source")  # type: ignore[attr-defined]
    except Exception as exc:
        raise PackageError(f"copied source {label} does not have the exact canonical source shape") from exc
    if not _exact_equal(source["dependencies"], []):
        raise PackageError(
            f"copied source {label} must contain a source object with source.dependencies exactly []; "
            "this experiment-local payload copies each source file without a dependency closure"
        )
    if (expected_document is None) != (expected_namespace is None):
        raise PackageError(f"copied source {label} has incomplete manifest source identity")
    if expected_document is not None and (
        source["document"] != expected_document or source["namespace"] != expected_namespace
    ):
        raise PackageError(f"copied source {label} document/namespace does not match manifest source metadata")


def _validate_copied_metrics(data: bytes, label: str, expected_profile_id: object) -> None:
    metrics = _parse_json_bytes(data, f"package metrics {label}")
    if not isinstance(metrics, dict) or metrics.get("profile_id") != expected_profile_id:
        raise PackageError(f"package metrics {label} profile identity does not match its manifest avatar")


def _validate_profile_bearing_artifact(data: bytes, label: str, expected_profile_id: object) -> None:
    artifact = _parse_json_bytes(data, f"package artifact {label}")
    if not isinstance(artifact, dict) or artifact.get("profile_id") != expected_profile_id:
        raise PackageError(f"package artifact {label} profile identity does not match its manifest avatar")


def _remove_tree_contents(directory_fd: int) -> bool:
    """Remove only entries that remain at their observed identities."""
    complete = True
    try:
        directory_flags = _directory_open_flags(_load_projection_module()._load_carrier_module())  # type: ignore[attr-defined]
    except PackageError:
        return False
    try:
        entries = os.scandir(f"/proc/self/fd/{directory_fd}")
    except OSError:
        return False
    with entries:
        for entry in entries:
            name = entry.name
            try:
                observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            except OSError:
                complete = False
                continue
            if stat.S_ISDIR(observed.st_mode):
                try:
                    child_fd = os.open(name, directory_flags, dir_fd=directory_fd)
                except OSError:
                    complete = False
                    continue
                try:
                    child_info = os.fstat(child_fd)
                    if not os.path.samestat(observed, child_info) or not _remove_tree_contents(child_fd):
                        complete = False
                        continue
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if not os.path.samestat(child_info, current):
                        complete = False
                        continue
                    os.rmdir(name, dir_fd=directory_fd)
                except (FileNotFoundError, NotADirectoryError, OSError):
                    complete = False
                finally:
                    try:
                        os.close(child_fd)
                    except OSError:
                        pass
                continue
            if not stat.S_ISREG(observed.st_mode):
                # Never remove a symlink or another replacement type.
                complete = False
                continue
            try:
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError:
                complete = False
                continue
            if not os.path.samestat(observed, current):
                complete = False
                continue
            try:
                os.unlink(name, dir_fd=directory_fd)
            except OSError:
                complete = False
    return complete


def _remove_tree(path: Path) -> None:
    """Remove contents through an anchored no-follow directory descriptor."""
    directory_fd = _open_directory_descriptor(path, "cleanup directory")
    try:
        _remove_tree_contents(directory_fd)
    finally:
        try:
            os.close(directory_fd)
        except OSError:
            pass


def _cleanup_created_destination(path: Path, identity: tuple[int, int]) -> None:
    parent_fd: int | None = None
    directory_fd: int | None = None
    try:
        parent_fd = _open_directory_descriptor(path.parent, "package cleanup parent")
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(current.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or (current.st_dev, current.st_ino) != identity
        ):
            return
        directory_fd = os.open(
            path.name,
            _directory_open_flags(_load_projection_module()._load_carrier_module()),  # type: ignore[attr-defined]
            dir_fd=parent_fd,
        )
        opened = os.fstat(directory_fd)
        if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != identity:
            return
        if not _remove_tree_contents(directory_fd):
            return
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != identity or not stat.S_ISDIR(current.st_mode):
            return
        os.rmdir(path.name, dir_fd=parent_fd)
    except (OSError, PackageError):
        return
    finally:
        if directory_fd is not None:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except OSError:
                pass


def build_package(
    gallery: Path,
    carrier_path: Path,
    projection_path: Path,
    output_path: Path,
    *,
    cli_path: Path | None = None,
) -> dict[str, object]:
    """Freshly validate inputs, copy the bounded payload, and publish its manifest."""
    output_path = _absolute_path(output_path, "package output path")
    projection_module, carrier_module, initial_projection = _fresh_projection(
        gallery, carrier_path, projection_path, cli_path, "initial"
    )
    files, manifest = _manifest_from_projection(projection_module, carrier_module, initial_projection, Path(gallery))
    destination: Path | None = None
    destination_identity: tuple[int, int] | None = None
    try:
        destination, destination_identity = _create_destination(output_path)
        _make_layout(destination)
        source_records = {
            relative: record
            for relative, record in _manifest_file_records(manifest).items()
            if relative.endswith(f"/{SOURCE_FILE}")
        }
        for relative in sorted(files):
            _write_new_file(destination / relative, files[relative], f"package file {relative}")
            if relative.endswith(f"/{SOURCE_FILE}"):
                source = source_records[relative]
                _validate_copied_source_dependencies(
                    files[relative],
                    relative,
                    projection_module=projection_module,
                    expected_document=source["document"],
                    expected_namespace=source["namespace"],
                )
        _verify_copied_files(destination, files, include_manifest=False)

        post_projection_module, post_carrier_module, post_projection = _fresh_projection(
            gallery, carrier_path, projection_path, cli_path, "post-copy"
        )
        if not _exact_equal(initial_projection, post_projection):
            raise PackageError("source gallery or projection changed after payload copying")
        post_files, post_manifest = _manifest_from_projection(
            post_projection_module, post_carrier_module, post_projection, Path(gallery)
        )
        if files != post_files or not _exact_equal(manifest, post_manifest):
            raise PackageError("source gallery content changed after payload copying")
        _verify_copied_files(destination, files, include_manifest=False)
        manifest_bytes = _canonical_json(manifest)
        _write_new_file(destination / MANIFEST_FILE, manifest_bytes, "package manifest")
        loaded = load_manifest(destination)
        if not _exact_equal(loaded, manifest):
            raise PackageError("published package manifest changed during publication")
        return manifest
    except PackageError:
        if destination is not None and destination_identity is not None:
            _cleanup_created_destination(destination, destination_identity)
        raise
    except Exception as exc:
        if destination is not None and destination_identity is not None:
            _cleanup_created_destination(destination, destination_identity)
        raise PackageError(f"disposable CK payload build failed: {type(exc).__name__}: {exc}") from exc


def validate_package(
    package_path: Path,
) -> dict[str, object]:
    """Validate the payload without requiring its source gallery or producer."""
    stored = load_manifest(package_path)
    return stored


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--gallery", type=Path, required=True)
    build.add_argument("--carrier", type=Path, required=True)
    build.add_argument("--projection", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--cli", type=Path, required=True, help="absolute native creature-kernel executable")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--package", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "build":
            manifest = build_package(
                args.gallery, args.carrier, args.projection, args.output, cli_path=args.cli
            )
        else:
            manifest = validate_package(args.package)
    except PackageError as exc:
        print(f"package-error: {exc}", file=sys.stderr)
        return 2
    print(_canonical_json(manifest).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

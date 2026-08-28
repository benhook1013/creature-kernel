#!/usr/bin/env python3
"""Build and validate the disposable engine-neutral avatar-input carrier."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any, Iterable


sys.dont_write_bytecode = True

try:  # Direct module execution puts this directory on sys.path.
    from run_structural_gallery_smoke import EXPECTED_GODOT_VERSION, preflight
except ImportError:  # pragma: no cover - package import path
    from .run_structural_gallery_smoke import EXPECTED_GODOT_VERSION, preflight


SCHEMA = "creature-kernel.disposable-engine-neutral-avatar-input.v1"
BOUNDARY = "experiment_input_only_no_runtime_package_or_adapter_contract"
POSE_FILE = "structural_embodiment_shared_pose.json"
INSTANCE_ID_PATTERN = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")

# The carrier is metadata plus validator-backed projections, not the gallery
# artifact bytes.  Keep a finite transport budget even though normal carriers
# are much smaller.
MAX_CARRIER_BYTES = 4 * 1024 * 1024
MAX_JSON_NODES = 200_000
MAX_JSON_DEPTH = 96
MAX_STRING_LENGTH = 65_536
MAX_POSE_BYTES = 16 * 1024 * 1024

SOURCE_GALLERY_KEYS = ("projection_contract", "manifest_sha256", "manifest_bytes", "boundary")
SHARED_POSE_KEYS = ("path", "pose_id", "sha256", "bytes")
INSTANCE_KEYS = (
    "instance_id",
    "profile_id",
    "label",
    "candidate_profile_sha256",
    "artifacts",
    "metrics",
)
PROFILE_KEYS = ("profile_id", "label", "candidate_profile_sha256", "artifacts", "metrics")
CARRIER_KEYS = ("schema", "boundary", "source_gallery", "shared_pose", "instances")


class CarrierError(ValueError):
    """A bounded, fail-closed carrier validation or publication failure."""


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CarrierError("carrier cannot be encoded as canonical finite JSON") from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _finite_json(value: Any, where: str = "carrier", *, depth: int = 0, state: list[int] | None = None) -> None:
    if state is None:
        state = [0]
    state[0] += 1
    if state[0] > MAX_JSON_NODES:
        raise CarrierError(f"{where} exceeds the bounded JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise CarrierError(f"{where} exceeds the bounded JSON depth")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CarrierError(f"{where} contains a non-finite number")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 10**15:
            raise CarrierError(f"{where} contains an unbounded integer")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise CarrierError(f"{where} contains an overlong string")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_json(item, f"{where}[{index}]", depth=depth + 1, state=state)
        return
    if isinstance(value, dict):
        if len(value) > 2048:
            raise CarrierError(f"{where} contains an oversized object")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_LENGTH:
                raise CarrierError(f"{where} contains an invalid object key")
            _finite_json(item, f"{where}.{key}", depth=depth + 1, state=state)
        return
    if value is not None and not isinstance(value, bool):
        raise CarrierError(f"{where} contains an unsupported JSON value")


def _exact_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int/float coercions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def _absolute_path(path: Path, label: str) -> Path:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_absolute():
        raise CarrierError(f"{label} must be an absolute path: {path}")
    return path


def _reject_symlink_components(path: Path, label: str) -> None:
    """Reject symlinks in an absolute lexical path, including the leaf."""
    absolute = path if path.is_absolute() else Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        except OSError as exc:
            raise CarrierError(f"could not inspect {label} path components") from exc
        if stat.S_ISLNK(mode):
            raise CarrierError(f"{label} or one of its path components is a symlink: {path}")


def _regular_file(path: Path, label: str) -> os.stat_result:
    _reject_symlink_components(path, label)
    try:
        info = path.lstat()
    except OSError as exc:
        raise CarrierError(f"{label} is unavailable: {path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise CarrierError(f"{label} must be a regular non-symlink file: {path}")
    return info


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )


def _read_open_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)


def _verify_directory_fd(directory_fd: int, path: Path, label: str) -> None:
    try:
        info = os.fstat(directory_fd)
    except OSError as exc:
        raise CarrierError(f"could not inspect {label} descriptor: {path}") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CarrierError(f"{label} must be a regular directory: {path}")


def _open_directory_descriptor(path: Path, label: str) -> int:
    """Open an absolute directory path and retain its descriptor as the anchor."""
    path = _absolute_path(path, label)
    _reject_symlink_components(path, label)
    directory_fd: int | None = None
    try:
        directory_fd = os.open(path.anchor, _directory_open_flags())
        _verify_directory_fd(directory_fd, Path(path.anchor), label)
        for component in path.parts[1:]:
            next_fd = os.open(component, _directory_open_flags(), dir_fd=directory_fd)
            try:
                _verify_directory_fd(next_fd, path, label)
            except CarrierError:
                try:
                    os.close(next_fd)
                except OSError:
                    pass
                raise
            previous_fd = directory_fd
            directory_fd = next_fd
            os.close(previous_fd)
        return directory_fd
    except CarrierError:
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
        raise CarrierError(f"could not open {label}: {path}") from exc


def _read_bounded_descriptor(
    file_fd: int,
    maximum: int,
    label: str,
    path: Path,
    size_error: str | None = None,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        try:
            chunk = os.read(file_fd, min(64 * 1024, maximum - total + 1))
        except OSError as exc:
            raise CarrierError(f"could not read {label}: {path}") from exc
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise CarrierError(size_error or f"{label} exceeds the bounded size of {maximum} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _read_regular_file(path: Path, maximum: int, label: str, *, size_error: str | None = None) -> bytes:
    path = _absolute_path(path, f"{label} path")
    expected_info = _regular_file(path, label)
    directory_fd = _open_directory_descriptor(path.parent, f"{label} parent directory")
    file_fd: int | None = None
    try:
        try:
            file_fd = os.open(path.name, _read_open_flags(), dir_fd=directory_fd)
        except (OSError, NotImplementedError, TypeError) as exc:
            raise CarrierError(f"could not open {label}: {path}") from exc
        try:
            try:
                actual_info = os.fstat(file_fd)
            except OSError as exc:
                raise CarrierError(f"could not inspect {label} descriptor: {path}") from exc
            if not stat.S_ISREG(actual_info.st_mode):
                raise CarrierError(f"{label} must be a regular non-symlink file: {path}")
            if (actual_info.st_dev, actual_info.st_ino) != (expected_info.st_dev, expected_info.st_ino):
                raise CarrierError(f"{label} changed while it was being opened: {path}")
            if actual_info.st_size > maximum:
                raise CarrierError(size_error or f"{label} exceeds the bounded size of {maximum} bytes")
            return _read_bounded_descriptor(file_fd, maximum, label, path, size_error)
        finally:
            try:
                os.close(file_fd)
            finally:
                file_fd = None
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass
        try:
            os.close(directory_fd)
        except OSError:
            pass


def _read_carrier_bytes(path: Path) -> bytes:
    return _read_regular_file(
        path,
        MAX_CARRIER_BYTES,
        "carrier path",
        size_error=f"carrier path exceeds the bounded input size of {MAX_CARRIER_BYTES} bytes",
    )


def load_carrier(path: Path) -> dict:
    """Load one absolute-path carrier file at the strict canonical-JSON syntax boundary.

    Semantic carrier and lineage checks remain owned by ``validate_carrier``.
    """
    data = _read_carrier_bytes(path)
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise CarrierError(f"carrier is not valid finite UTF-8 JSON: {path}") from exc
    _finite_json(value)
    if not isinstance(value, dict):
        raise CarrierError("carrier JSON must be an object")
    if data != _canonical_json(value):
        raise CarrierError("carrier JSON is not canonical newline-terminated JSON")
    return value


def _pair(values: Iterable[str], label: str) -> tuple[str, str]:
    if isinstance(values, (str, bytes)):
        raise CarrierError(f"{label} must contain exactly two values")
    try:
        selected = tuple(values)
    except (TypeError, ValueError) as exc:
        raise CarrierError(f"{label} must contain exactly two values") from exc
    if len(selected) != 2:
        raise CarrierError(f"exactly two {label} are required")
    if any(type(value) is not str for value in selected):
        raise CarrierError(f"{label} must be exact strings")
    return selected  # type: ignore[return-value]


def _validate_instance_ids(instance_ids: Iterable[str]) -> tuple[str, str]:
    selected = _pair(instance_ids, "instance IDs")
    for instance_id in selected:
        if INSTANCE_ID_PATTERN.fullmatch(instance_id) is None:
            raise CarrierError(
                "instance IDs must match restricted lowercase ASCII [a-z][a-z0-9-]{0,63}: "
                f"{instance_id!r}"
            )
    if selected[0] == selected[1]:
        raise CarrierError(f"duplicate experiment instance identity rejected: {selected[0]}")
    return selected


def _read_validated_pose(gallery: Path, pose_sha256: str) -> int:
    pose_path = gallery / POSE_FILE
    data = _read_regular_file(pose_path, MAX_POSE_BYTES, "shared pose")
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if actual_sha256 != pose_sha256:
        raise CarrierError("shared pose SHA-256 disagrees with the validator-backed payload")
    return len(data)


def _validated_payload(gallery: Path, profile_ids: tuple[str, str]) -> dict[str, Any]:
    try:
        _, payload = preflight(gallery, profile_ids)
    except CarrierError:
        raise
    except Exception as exc:
        raise CarrierError(f"structural gallery preflight failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CarrierError("structural gallery preflight did not return a payload object")
    return payload


def _carrier_from_payload(
    gallery: Path,
    payload: dict[str, Any],
    instance_ids: tuple[str, str],
) -> dict[str, Any]:
    required_payload_keys = {
        "projection_contract",
        "manifest_sha256",
        "manifest_bytes",
        "godot_version",
        "profile_ids",
        "pose_id",
        "pose_sha256",
        "boundary",
        "profiles",
    }
    if set(payload) != required_payload_keys:
        raise CarrierError("validator-backed payload has unexpected or missing fields")
    if payload.get("godot_version") != EXPECTED_GODOT_VERSION:
        raise CarrierError("validator-backed payload has an unexpected Godot version")
    profile_ids = _pair(payload.get("profile_ids", ()), "profile IDs in the validated payload")
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != 2:
        raise CarrierError("validator-backed payload does not contain exactly two profiles")
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict) or set(profile) != set(PROFILE_KEYS):
            raise CarrierError(f"validated profile {index} has unexpected or missing fields")
        if profile.get("profile_id") != profile_ids[index]:
            raise CarrierError("validated profile IDs are not ordered consistently")
    pose_sha256 = payload.get("pose_sha256")
    if type(pose_sha256) is not str:
        raise CarrierError("validator-backed pose SHA-256 is not an exact string")
    pose_bytes = _read_validated_pose(gallery, pose_sha256)
    source_gallery = {
        "projection_contract": payload["projection_contract"],
        "manifest_sha256": payload["manifest_sha256"],
        "manifest_bytes": payload["manifest_bytes"],
        "boundary": payload["boundary"],
    }
    shared_pose = {
        "path": POSE_FILE,
        "pose_id": payload["pose_id"],
        "sha256": pose_sha256,
        "bytes": pose_bytes,
    }
    instances = []
    for instance_id, profile in zip(instance_ids, profiles):
        instances.append(
            {
                "instance_id": instance_id,
                "profile_id": profile["profile_id"],
                "label": profile["label"],
                "candidate_profile_sha256": profile["candidate_profile_sha256"],
                "artifacts": profile["artifacts"],
                "metrics": profile["metrics"],
            }
        )
    return {
        "schema": SCHEMA,
        "boundary": BOUNDARY,
        "source_gallery": source_gallery,
        "shared_pose": shared_pose,
        "instances": instances,
    }


def build_carrier(gallery: Path, profile_ids, instance_ids) -> dict:
    """Build the canonical carrier from one fresh validator-backed preflight."""
    selected_profiles = _pair(profile_ids, "profile IDs")
    selected_instances = _validate_instance_ids(instance_ids)
    gallery = _absolute_path(gallery, "gallery path")
    payload = _validated_payload(gallery, selected_profiles)
    return _carrier_from_payload(gallery, payload, selected_instances)


def _extract_selection(carrier: Any) -> tuple[tuple[str, str], tuple[str, str]]:
    if not isinstance(carrier, dict):
        raise CarrierError("carrier must be a JSON object")
    instances = carrier.get("instances")
    if not isinstance(instances, list) or len(instances) != 2:
        raise CarrierError("carrier must contain exactly two ordered instances")
    profile_ids: list[str] = []
    instance_ids: list[str] = []
    for index, instance in enumerate(instances):
        if not isinstance(instance, dict):
            raise CarrierError(f"carrier instance {index} must be an object")
        profile_id = instance.get("profile_id")
        instance_id = instance.get("instance_id")
        if type(profile_id) is not str or type(instance_id) is not str:
            raise CarrierError(f"carrier instance {index} must expose exact profile and instance IDs")
        profile_ids.append(profile_id)
        instance_ids.append(instance_id)
    return _pair(profile_ids, "profile IDs in carrier"), _validate_instance_ids(instance_ids)


def _godot_payload_from_carrier(carrier: dict[str, Any]) -> dict[str, Any]:
    source_gallery = carrier["source_gallery"]
    shared_pose = carrier["shared_pose"]
    instances = carrier["instances"]
    return {
        "projection_contract": source_gallery["projection_contract"],
        "manifest_sha256": source_gallery["manifest_sha256"],
        "manifest_bytes": source_gallery["manifest_bytes"],
        "godot_version": EXPECTED_GODOT_VERSION,
        "profile_ids": [instance["profile_id"] for instance in instances],
        "pose_id": shared_pose["pose_id"],
        "pose_sha256": shared_pose["sha256"],
        "boundary": source_gallery["boundary"],
        "profiles": [
            {key: instance[key] for key in PROFILE_KEYS}
            for instance in instances
        ],
    }


def validate_carrier(carrier: Any, gallery: Path) -> tuple[dict, tuple[str, str], tuple[str, str]]:
    """Rebuild and compare a carrier, then reconstruct the existing Godot payload."""
    profile_ids, instance_ids = _extract_selection(carrier)
    gallery = _absolute_path(gallery, "gallery path")
    payload = _validated_payload(gallery, profile_ids)
    expected = _carrier_from_payload(gallery, payload, instance_ids)
    if not _exact_equal(carrier, expected):
        raise CarrierError("carrier does not exactly match the fresh validator-backed projection")
    return _godot_payload_from_carrier(carrier), profile_ids, instance_ids


def _publication_destination(path: Path) -> tuple[Path, tuple[int, int]]:
    path = _absolute_path(path, "carrier output path")
    _reject_symlink_components(path, "carrier output path")
    try:
        parent_info = path.parent.lstat()
    except OSError as exc:
        raise CarrierError(f"could not inspect carrier output parent: {path.parent}") from exc
    if stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode):
        raise CarrierError(f"carrier output parent is not a regular directory: {path.parent}")
    return path, (parent_info.st_dev, parent_info.st_ino)


def write_carrier(path: Path, carrier: dict) -> None:
    """Publish canonical JSON bytes through an anchored, no-overwrite directory.

    This is the publication boundary; ``validate_carrier`` remains the semantic
    authority for carrier contents and lineage.
    """
    if not isinstance(carrier, dict):
        raise CarrierError("carrier to write must be a JSON object")
    _finite_json(carrier)
    data = _canonical_json(carrier)
    if len(data) > MAX_CARRIER_BYTES:
        raise CarrierError(f"carrier exceeds the bounded size of {MAX_CARRIER_BYTES} bytes")
    destination, expected_parent_identity = _publication_destination(path)
    directory_fd: int | None = None
    temporary_fd: int | None = None
    temporary_name: str | None = None
    try:
        directory_fd = _open_directory_descriptor(destination.parent, "carrier output parent directory")
        opened_parent = os.fstat(directory_fd)
        if (opened_parent.st_dev, opened_parent.st_ino) != expected_parent_identity:
            raise CarrierError(
                f"carrier output parent changed while it was being opened: {destination.parent}"
            )
        for _ in range(128):
            candidate = f".ck-carrier-{secrets.token_hex(16)}.tmp"
            try:
                temporary_fd = os.open(
                    candidate,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=directory_fd,
                )
            except FileExistsError:
                continue
            except (OSError, NotImplementedError, TypeError) as exc:
                raise CarrierError(f"could not create a temporary carrier in: {destination.parent}") from exc
            temporary_name = candidate
            break
        if temporary_fd is None or temporary_name is None:
            raise CarrierError(f"could not allocate a temporary carrier in: {destination.parent}")
        try:
            view = memoryview(data)
            while view:
                written = os.write(temporary_fd, view)
                if written <= 0:
                    raise OSError("temporary carrier write made no progress")
                view = view[written:]
            os.fsync(temporary_fd)
        finally:
            os.close(temporary_fd)
            temporary_fd = None
        # A hard-link create is atomic and fails with EEXIST, unlike replace().
        os.link(
            temporary_name,
            destination.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        os.unlink(temporary_name, dir_fd=directory_fd)
        temporary_name = None
        os.fsync(directory_fd)
    except CarrierError:
        raise
    except (OSError, NotImplementedError, TypeError) as exc:
        raise CarrierError(f"canonical carrier could not be published without overwrite: {destination}") from exc
    finally:
        if temporary_fd is not None:
            try:
                os.close(temporary_fd)
            except OSError:
                pass
        if temporary_name is not None and directory_fd is not None:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
            except OSError:
                pass
        if directory_fd is not None:
            try:
                os.close(directory_fd)
            except OSError:
                pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", required=True, type=Path, help="absolute completed structural gallery directory")
    parser.add_argument("--profile-id", action="append", required=True, dest="profile_ids", help="repeat exactly twice")
    parser.add_argument("--instance-id", action="append", required=True, dest="instance_ids", help="repeat exactly twice")
    parser.add_argument("--output", required=True, type=Path, help="absolute carrier output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        carrier = build_carrier(args.gallery, args.profile_ids, args.instance_ids)
        write_carrier(args.output, carrier)
    except CarrierError as exc:
        print(f"disposable avatar carrier failed: {exc}", file=sys.stderr)
        return 2
    print(_canonical_json(carrier).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Closed artifact serialization, stable inventory, and publication."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import math
import os
import re
import secrets
import stat
import struct
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

CONTRACT_ROLE = "experiments/owned-root-assembly-successor/design-contract.md"
RENAME_NOREPLACE = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_PATH = getattr(os, "O_PATH", os.O_RDONLY)
_STAT_FIELDS = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                "st_size", "st_mtime_ns", "st_ctime_ns", "st_rdev", "st_blksize", "st_blocks")
_PUBLISHED_STAT_FIELDS = tuple(field for field in _STAT_FIELDS if field != "st_ctime_ns")
class ArtifactSerializationError(ValueError): pass
def _stat_key(info: os.stat_result, fields=_STAT_FIELDS) -> tuple[object, ...]:
    """Return stable stat fields; atime is omitted because reads may update it."""
    return tuple(getattr(info, field, None) for field in fields)
def _same_stat(left: os.stat_result, right: os.stat_result) -> bool: return _stat_key(left) == _stat_key(right)
def _require_same_stat(expected: os.stat_result, observed: os.stat_result, message: str) -> None:
    if not _same_stat(expected, observed): raise ArtifactSerializationError(message)
def _same_published_state(left: os.stat_result, right: os.stat_result) -> bool:
    return os.path.samestat(left, right) and _stat_key(left, _PUBLISHED_STAT_FIELDS) == _stat_key(right, _PUBLISHED_STAT_FIELDS)
def _require_regular(info: os.stat_result, label: str) -> None:
    if not stat.S_ISREG(info.st_mode): raise ArtifactSerializationError(f"{label} is not a regular file")
    if info.st_nlink > 1: raise ArtifactSerializationError(f"{label} has external hardlinks")
def _require_publishable(info: os.stat_result, label: str) -> None:
    if stat.S_ISLNK(info.st_mode): raise ArtifactSerializationError(f"{label} must not be a symlink")
    if stat.S_ISDIR(info.st_mode): return
    if not stat.S_ISREG(info.st_mode): raise ArtifactSerializationError(f"{label} must be a regular file or directory")
    if info.st_nlink > 1: raise ArtifactSerializationError(f"{label} has external hardlinks")
def validate_role_path(value: object, *, label: str = "role_path") -> str:
    if not isinstance(value, str) or not value or "\x00" in value: raise ArtifactSerializationError(f"{label} must be a canonical relative path")
    if value.startswith("/") or "\\" in value: raise ArtifactSerializationError(f"{label} must be a canonical relative path")
    if any(not part or part in {".", ".."} for part in value.split("/")): raise ArtifactSerializationError(f"{label} contains an invalid component")
    return value
def _canonical(value: Any, path: str = "$") -> Any:
    if type(value) is float:
        if not math.isfinite(value): raise ArtifactSerializationError(f"non-finite number at {path}")
        return 0 if value == 0.0 else value
    if value is None or isinstance(value, (str, bool, int)): return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value): raise ArtifactSerializationError(f"invalid object key at {path}")
        return {key: _canonical(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [_canonical(item, f"{path}[{i}]") for i, item in enumerate(value)]
    raise ArtifactSerializationError(f"non-JSON value at {path}")
def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        if isinstance(exc, ArtifactSerializationError): raise
        raise ArtifactSerializationError("value cannot be canonically encoded") from exc
def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result: raise ArtifactSerializationError(f"duplicate object key: {key}")
        result[key] = value
    return result
def _reject_constant(value: str) -> None: raise ArtifactSerializationError(f"non-finite JSON constant: {value}")
def decode_canonical_json(data: bytes | bytearray | memoryview | str) -> Any:
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, ArtifactSerializationError): raise
        raise ArtifactSerializationError("invalid JSON artifact") from exc
    if canonical_json_bytes(value) != raw: raise ArtifactSerializationError("JSON artifact is not canonical")
    return value
def coerce_binary64(value: object, *, label: str = "binary64") -> float:
    if type(value) is float and math.isfinite(value): return value
    if type(value) is int and value == 0: return 0.0
    raise ArtifactSerializationError(f"{label} is not a finite binary64 float or zero integer")
def sha256_bytes(data: bytes | bytearray | memoryview) -> str:
    if not isinstance(data, (bytes, bytearray, memoryview)): raise ArtifactSerializationError("hash input must be bytes-like")
    return hashlib.sha256(bytes(data)).hexdigest()
def _path(path: str | os.PathLike[str]) -> Path:
    try:
        value = os.fspath(path)
        return Path(os.path.abspath(os.fsdecode(value) if isinstance(value, bytes) else value))
    except (TypeError, ValueError) as exc:
        raise ArtifactSerializationError("path must be a filesystem path") from exc
def _component(value: str, label: str) -> str:
    if (not isinstance(value, str) or not value or value in {".", ".."} or "/" in value
            or "\\" in value or "\x00" in value): raise ArtifactSerializationError(f"{label} is not a safe path component")
    return value
def _open_directory(path: str | os.PathLike[str]) -> int:
    absolute = _path(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | _NOFOLLOW | _CLOEXEC
    descriptor = os.open(absolute.anchor, flags)
    try:
        for part in absolute.parts[1:]:
            child = os.open(_component(part, "directory component"), flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode): raise ArtifactSerializationError("directory is not a directory")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise
def _read_stable_once(fd: int, initial: os.stat_result, max_bytes: int | None) -> bytes:
    _require_same_stat(initial, os.fstat(fd), "regular file changed before repeated read")
    chunks, offset = [], 0
    while True:
        _require_same_stat(initial, os.fstat(fd), "regular file changed between chunks")
        chunk = os.pread(fd, 1024 * 1024, offset)
        _require_same_stat(initial, os.fstat(fd), "regular file changed between chunks")
        if not chunk: break
        offset += len(chunk)
        if max_bytes is not None and offset > max_bytes: raise ArtifactSerializationError("regular file exceeds size cap")
        chunks.append(chunk)
    return b"".join(chunks)
def _read_stable_fd(fd: int, max_bytes: int | None) -> tuple[bytes, os.stat_result]:
    initial = os.fstat(fd)
    _require_regular(initial, "opened file")
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 0 or initial.st_size > max_bytes): raise ArtifactSerializationError("regular file exceeds size cap")
    readings = [_read_stable_once(fd, initial, max_bytes) for _ in range(2)]
    final = os.fstat(fd)
    _require_same_stat(initial, final, "regular file changed while reading")
    if final.st_size != len(readings[1]) or readings[0] != readings[1]: raise ArtifactSerializationError("regular file changed while reading")
    return readings[1], final
def _read_stable_with_identity(parent_fd: int, name: str,
                               max_bytes: int | None) -> tuple[bytes, os.stat_result]:
    try:
        fd = os.open(_component(name, "file name"), os.O_RDONLY | _NOFOLLOW | _CLOEXEC,
                     dir_fd=parent_fd)
    except OSError as exc:
        raise ArtifactSerializationError("cannot open regular file") from exc
    try:
        return _read_stable_fd(fd, max_bytes)
    except OSError as exc:
        raise ArtifactSerializationError("regular file cannot be read stably") from exc
    finally:
        os.close(fd)
def _read_stable(parent_fd: int, name: str, max_bytes: int | None) -> bytes:
    return _read_stable_with_identity(parent_fd, name, max_bytes)[0]
def read_regular_file(path: str | os.PathLike[str], *, max_bytes: int | None = None) -> bytes:
    absolute = _path(path)
    parent_fd = _open_directory(absolute.parent)
    try:
        data, opened = _read_stable_with_identity(parent_fd, absolute.name, max_bytes)
        try:
            named = os.stat(absolute.name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise ArtifactSerializationError("requested file path changed while reading") from exc
        if not _same_stat(opened, named): raise ArtifactSerializationError("requested file path changed while reading")
        return data
    finally:
        os.close(parent_fd)
def regular_file_record(path: str | os.PathLike[str], role_path: str | None = None,
                        *, max_bytes: int | None = None) -> dict[str, Any]:
    absolute = _path(path)
    role = absolute.name if role_path is None else validate_role_path(role_path)
    data = read_regular_file(absolute, max_bytes=max_bytes)
    return {"role_path": role, "bytes": len(data), "sha256": sha256_bytes(data)}
def _hash_rows(rows: Iterable[Iterable[object]], coordinates: bool) -> bytes:
    result = bytearray()
    for row_index, row in enumerate(rows):
        values = tuple(row)
        if len(values) != 3:
            raise ArtifactSerializationError(
                f"coordinate row {row_index} is not a vector3"
                if coordinates else f"triangle row {row_index} is invalid"
            )
        for axis, value in zip("xyz", values):
            valid = (type(value) is float and math.isfinite(value) if coordinates
                     else type(value) is int and -(1 << 63) <= value < (1 << 63))
            if not valid:
                raise ArtifactSerializationError(
                    f"coordinate {row_index}.{axis} is not binary64"
                    if coordinates else f"triangle row {row_index} is invalid"
                )
        result.extend(struct.pack("<ddd" if coordinates else "<qqq", *values))
    return bytes(result)
def coordinate_hash_bytes(coordinates: Iterable[Iterable[object]]) -> bytes:
    return _hash_rows(coordinates, True)
def triangle_index_hash_bytes(triangles: Iterable[Iterable[object]]) -> bytes:
    return _hash_rows(triangles, False)
def contract_sidecar_bytes(contract_sha256: str) -> bytes:
    if not isinstance(contract_sha256, str) or SHA256_RE.fullmatch(contract_sha256) is None: raise ArtifactSerializationError("contract SHA-256 must be lowercase 64-hex")
    return f"{contract_sha256}  {CONTRACT_ROLE}\n".encode("ascii")
def validate_contract_sidecar(data: bytes | bytearray | memoryview,
                              expected_sha256: str) -> None:
    if bytes(data) != contract_sidecar_bytes(expected_sha256): raise ArtifactSerializationError("contract sidecar is not the exact required line")
def _closed_inventory_fd(root_fd: int, expected: tuple[str, ...],
                         max_file_bytes: int | None) -> tuple[tuple[dict[str, Any], ...], tuple[Any, ...]]:
    expected_dirs = set()
    for role in expected:
        while "/" in role:
            role = role.rsplit("/", 1)[0]
            expected_dirs.add(role)
    first = _inventory_snapshot(root_fd, expected_dirs, max_file_bytes)
    second = _inventory_snapshot(root_fd, expected_dirs, max_file_bytes)
    files = tuple(sorted((role for role, value in first.items() if value[1] is not None), key=lambda value: value.encode("utf-8")))
    if first != second or files != expected: raise ArtifactSerializationError("closed inventory changed or does not match")
    identities = tuple(sorted(((role, value[0]) for role, value in first.items() if role), key=lambda row: row[0].encode("utf-8")))
    return tuple(first[role][1] for role in expected), identities
def closed_inventory(root: str | os.PathLike[str], roles: Iterable[str], *,
                     max_file_bytes: int | None = None) -> tuple[dict[str, Any], ...]:
    values = tuple(validate_role_path(role) for role in roles)
    if len(set(values)) != len(values): raise ArtifactSerializationError("closed inventory contains duplicate roles")
    if max_file_bytes is not None and (type(max_file_bytes) is not int or max_file_bytes < 0): raise ArtifactSerializationError("max_file_bytes must be a nonnegative integer")
    expected = tuple(sorted(values, key=lambda value: value.encode("utf-8")))
    root_fd = _open_directory(root)
    try:
        return _closed_inventory_fd(root_fd, expected, max_file_bytes)[0]
    finally:
        os.close(root_fd)
def _inventory_snapshot(root_fd: int, expected_dirs: set[str], max_bytes: int | None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    try:
        for relative, directories, _files, directory_fd in os.fwalk(".", topdown=True, follow_symlinks=False, dir_fd=root_fd):
            prefix = "" if relative == "." else relative.removeprefix("./")
            before = os.fstat(directory_fd)
            if prefix in snapshot and snapshot[prefix][0] != _stat_key(before): raise ArtifactSerializationError("inventory child directory changed while opening")
            snapshot.setdefault(prefix, (_stat_key(before), None))
            names = sorted(os.listdir(directory_fd), key=lambda value: value.encode("utf-8"))
            child_directories = []
            for name in names:
                _component(name, "inventory entry")
                role = f"{prefix}/{name}" if prefix else name
                entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISLNK(entry.st_mode): raise ArtifactSerializationError(f"inventory contains a symlink: {role}")
                if stat.S_ISDIR(entry.st_mode):
                    if role not in expected_dirs: raise ArtifactSerializationError(f"inventory contains an unexpected directory: {role}")
                    snapshot[role] = (_stat_key(entry), None)
                    child_directories.append((name, role, entry))
                elif stat.S_ISREG(entry.st_mode):
                    _require_regular(entry, f"inventory file {role}")
                    data, opened = _read_stable_with_identity(directory_fd, name, max_bytes)
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if not _same_stat(entry, opened) or not _same_stat(opened, current) or current.st_size != len(data): raise ArtifactSerializationError("inventory file was replaced while reading")
                    snapshot[role] = (_stat_key(current), {"role_path": validate_role_path(role), "bytes": len(data), "sha256": sha256_bytes(data)})
                else: raise ArtifactSerializationError(f"inventory contains a non-regular entry: {role}")
            for name, _role, expected_entry in child_directories:
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if not _same_stat(expected_entry, current): raise ArtifactSerializationError("inventory child entry changed during traversal")
            directories[:] = [name for name in directories if (f"{prefix}/{name}" if prefix else name) in expected_dirs]
            after = sorted(os.listdir(directory_fd), key=lambda value: value.encode("utf-8"))
            if names != after or not _same_stat(before, os.fstat(directory_fd)): raise ArtifactSerializationError("inventory directory changed during traversal")
    except (OSError, UnicodeError) as exc:
        raise ArtifactSerializationError("inventory traversal failed") from exc
    return snapshot
def _freeze_inventory(records: Iterable[Mapping[str, Any]]) -> tuple[tuple[str, int, str], ...]:
    try:
        values = tuple(records)
        if any(not isinstance(record, Mapping) or set(record) != {"role_path", "bytes", "sha256"} for record in values): raise ArtifactSerializationError("expected inventory must contain closed file_records")
        frozen = tuple((validate_role_path(record["role_path"]), record["bytes"], record["sha256"])
                       for record in values)
    except (KeyError, TypeError, UnicodeError, ValueError) as exc:
        if isinstance(exc, ArtifactSerializationError): raise
        raise ArtifactSerializationError("expected inventory must contain closed file_records") from exc
    if any(type(size) is not int or size < 0 or not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None for _role, size, digest in frozen): raise ArtifactSerializationError("expected inventory contains an invalid file_record")
    ordered = tuple(sorted(frozen, key=lambda row: row[0].encode("utf-8")))
    if frozen != ordered or len({role for role, _size, _digest in frozen}) != len(frozen): raise ArtifactSerializationError("expected inventory must be uniquely ordered by role_path")
    return frozen
def _inventory_verifier(fd: int, expected: tuple[tuple[str, int, str], ...], max_bytes: int):
    root, roles, baseline = os.fstat(fd), tuple(row[0] for row in expected), None
    def verify() -> None:
        nonlocal baseline
        if stat.S_ISDIR(root.st_mode):
            records, identities = _closed_inventory_fd(fd, roles, max_bytes)
        else:
            if len(expected) != 1: raise ArtifactSerializationError("regular-file publication requires exactly one file_record")
            try: data, identity = _read_stable_fd(fd, max_bytes)
            except OSError as exc: raise ArtifactSerializationError("publication inventory cannot be read stably") from exc
            records = ({"role_path": roles[0], "bytes": len(data), "sha256": sha256_bytes(data)},)
            identities = ((roles[0], _stat_key(identity, _PUBLISHED_STAT_FIELDS)),)
        if _freeze_inventory(records) != expected: raise ArtifactSerializationError("publication inventory does not match expected records")
        if baseline is None: baseline = identities
        elif identities != baseline: raise ArtifactSerializationError("publication inventory file identities changed")
    return verify
def _rename_no_replace(parent_fd: int, source: str, destination: str) -> None:
    if os.name != "posix": raise ArtifactSerializationError("atomic no-replace publication requires Linux/WSL")
    function = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if function is None: raise ArtifactSerializationError("renameat2 is unavailable")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    result = function(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), RENAME_NOREPLACE)
    if result == 0: return
    error = ctypes.get_errno()
    if error == errno.EEXIST: raise FileExistsError(destination)
    raise ArtifactSerializationError(f"atomic no-replace rename failed: {os.strerror(error)}")
def _verify_canonical_publication(parent_fd: int, parent_path: Path, destination: str, expected: os.stat_result) -> None:
    try: current_parent = os.stat(parent_path, follow_symlinks=False); current_target = os.stat(parent_path / destination, follow_symlinks=False)
    except OSError as exc: raise ArtifactSerializationError("requested publication pathname changed") from exc
    if not os.path.samestat(os.fstat(parent_fd), current_parent) or not _same_published_state(expected, current_target): raise ArtifactSerializationError("published entry is not bound to requested pathname")
def _move_to_rollback_quarantine(parent_fd: int, name: str) -> str:
    """Atomically preserve the entry currently at name under a fresh sibling name."""
    for _ in range(32):
        quarantine = f".rollback-{os.getpid()}-{secrets.token_hex(8)}"
        try:
            _rename_no_replace(parent_fd, name, quarantine)
            return quarantine
        except FileExistsError: continue
    raise ArtifactSerializationError("unable to allocate publication rollback quarantine")
def _rollback_publication(parent_fd: int, source: str, destination: str, expected_fd: int) -> bool:
    """Restore the expected inode or quarantine a replacement; never delete either."""
    quarantine = _move_to_rollback_quarantine(parent_fd, destination)
    moved = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
    if not os.path.samestat(os.fstat(expected_fd), moved): return False
    try:
        _rename_no_replace(parent_fd, quarantine, source)
    except FileExistsError as exc:
        raise ArtifactSerializationError(
            "staging name was occupied; published entry remains in rollback quarantine"
        ) from exc
    restored = os.stat(source, dir_fd=parent_fd, follow_symlinks=False)
    if not os.path.samestat(os.fstat(expected_fd), restored): raise ArtifactSerializationError("rolled-back staging entry was replaced")
    return True
def _require_absent(parent_fd: int, name: str, error_name: str) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(error_name)

def _publish_at(parent_fd: int, parent_path: Path, source: str, destination: str, expected: os.stat_result, expected_fd: int, verify=None) -> None:
    _require_same_stat(expected, os.fstat(expected_fd), "pinned staging entry changed before publication")
    current = os.stat(source, dir_fd=parent_fd, follow_symlinks=False)
    _require_publishable(current, "staging entry")
    if not _same_stat(expected, current):
        raise ArtifactSerializationError("staging entry changed before publication")
    if verify is not None: verify()
    _require_absent(parent_fd, destination, destination)
    renamed = False
    try:
        _rename_no_replace(parent_fd, source, destination)
        renamed = True; _verify_canonical_publication(parent_fd, parent_path, destination, expected)
        installed = os.stat(destination, dir_fd=parent_fd, follow_symlinks=False)
        _require_publishable(installed, "published entry")
        if not _same_published_state(expected, installed):
            raise ArtifactSerializationError("published entry identity changed")
        os.fsync(parent_fd)
        if verify is not None: verify()
        verified = os.stat(destination, dir_fd=parent_fd, follow_symlinks=False)
        if not os.path.samestat(expected, verified) or not _same_published_state(expected, verified): raise ArtifactSerializationError("published entry changed after fsync")
        _require_publishable(verified, "published entry"); _verify_canonical_publication(parent_fd, parent_path, destination, expected)
    except Exception as publication_failure:
        if renamed:
            _handle_publication_failure(
                parent_fd, source, destination, expected_fd, publication_failure
            )
        raise
def _handle_publication_failure(parent_fd: int, source: str, destination: str, expected_fd: int, failure: Exception) -> None:
    try:
        rolled_back = _rollback_publication(parent_fd, source, destination, expected_fd)
    except Exception as rollback_failure:
        raise ArtifactSerializationError(
            "publication failed and exact atomic rollback did not complete; "
            f"original failure: {failure}"
        ) from rollback_failure
    if not rolled_back:
        raise ArtifactSerializationError(
            "publication failed after destination replacement; the unrelated entry was quarantined"
        ) from failure

def publish_no_replace(staging: str | os.PathLike[str], destination: str | os.PathLike[str], expected_inventory: Iterable[Mapping[str, Any]], *, max_file_bytes: int) -> Path:
    """Publish a sibling only if its pinned files still match prior closed inventory records."""
    expected = _freeze_inventory(expected_inventory)
    if type(max_file_bytes) is not int or max_file_bytes < 0: raise ArtifactSerializationError("max_file_bytes must be a nonnegative integer")
    stage, target = _path(staging), _path(destination)
    if stage.parent != target.parent or stage.name == target.name: raise ArtifactSerializationError("staging and destination must be distinct siblings")
    _component(stage.name, "staging name")
    _component(target.name, "destination name")
    parent_fd = _open_directory(stage.parent)
    source_fd = inventory_fd = -1
    try:
        source_fd = os.open(stage.name, _PATH | _NOFOLLOW | _CLOEXEC, dir_fd=parent_fd)
        source = os.fstat(source_fd)
        _require_publishable(source, "staging entry")
        inventory_fd = os.open(stage.name, os.O_RDONLY | os.O_NONBLOCK | _NOFOLLOW | _CLOEXEC, dir_fd=parent_fd)
        _require_same_stat(source, os.fstat(inventory_fd), "staging entry changed before inventory binding")
        _publish_at(parent_fd, stage.parent, stage.name, target.name, source, source_fd,
                    _inventory_verifier(inventory_fd, expected, max_file_bytes))
    finally:
        if inventory_fd >= 0:
            os.close(inventory_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(parent_fd)
    return target
def _temporary_file(parent_fd: int, target_name: str) -> tuple[int, str]:
    for _ in range(32):
        name = f".{target_name}.stage-{os.getpid()}-{secrets.token_hex(8)}"
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | _CLOEXEC, 0o600, dir_fd=parent_fd)
            return fd, name
        except FileExistsError:
            continue
    raise ArtifactSerializationError("unable to create a unique temporary artifact")
def write_bytes_no_replace(path: str | os.PathLike[str], data: bytes) -> Path:
    if not isinstance(data, bytes): raise ArtifactSerializationError("atomic payload must be bytes")
    target = _path(path)
    _component(target.name, "destination name")
    parent_fd = _open_directory(target.parent)
    descriptor = -1
    try:
        _require_absent(parent_fd, target.name, str(target))
        descriptor, temporary_name = _temporary_file(parent_fd, target.name)
        identity = os.fstat(descriptor)
        _require_regular(identity, "temporary artifact")
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0: raise ArtifactSerializationError("temporary artifact write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        identity = os.fstat(descriptor)
        _require_regular(identity, "temporary artifact")
        _publish_at(parent_fd, target.parent, temporary_name, target.name, identity, descriptor)
        os.close(descriptor)
        descriptor = -1
        return target
    except Exception:
        if descriptor >= 0: os.close(descriptor)
        # Conditional unlink by pathname is not available. Retaining the
        # staging entry is safer than deleting an adversarial replacement.
        raise
    finally:
        os.close(parent_fd)
def write_canonical_json_no_replace(path: str | os.PathLike[str], value: Any) -> Path:
    return write_bytes_no_replace(path, canonical_json_bytes(value))
def write_contract_sidecar_no_replace(path: str | os.PathLike[str],
                                      contract_sha256: str) -> Path:
    return write_bytes_no_replace(path, contract_sidecar_bytes(contract_sha256))

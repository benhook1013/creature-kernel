"""Immutable publication and reading of one exact Phase 3 attempt.

This module is deliberately execution-incapable.  It accepts already-built
canonical result, receipt, and attempt-index bytes, validates the three
objects through :mod:`phase3_evidence_contract`, and publishes them as one
closed, no-replace filesystem object.  It does not launch a candidate, create
an evidence record, or repair partial output.

The publication directory is intentionally not a temporary staging area.  A
failed publication remains in place as diagnostic state and can never be
silently completed or replaced by a later call.  A reader only accepts the
closed three-file layout after descriptor-bound metadata and byte/hash checks.

Mode ``0444``/``0555`` is an immutable-publication convention, not protection
against a hostile process with the same UID (or root), which can chmod and
replace entries after this module returns.  Mutations reflected in the
verifier's repeated reads or final retained-descriptor/path observations are
detected.  This is an observed-overlap boundary, not external custody against
a malicious peer that can act after an individual final observation or after
the verifier returns.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import phase3_evidence_contract as contract


RESULT_NAME = "result.json"
RECEIPT_NAME = "receipt.json"
INDEX_NAME = "attempt-index.json"
FILE_NAMES = (RESULT_NAME, RECEIPT_NAME, INDEX_NAME)
FILE_MODES = 0o444
DIRECTORY_MODE = 0o555
MAX_PARENT_PATH_BYTES = 4096
MAX_COMPONENT_BYTES = 255
MAX_ATTEMPT_ID_BYTES = contract.MAX_ID_BYTES
ATTEMPT_RE = contract.ATTEMPT_RE


class PublicationError(ValueError):
    """Stable, typed fail-closed publication/reader error."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", " ")[:300]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


@dataclass(frozen=True)
class FileIdentity:
    """Identity returned for one immutable published file."""

    path: Path
    bytes: int
    sha256: str
    mode: int


@dataclass(frozen=True)
class PublishedAttempt:
    """The validated, closed filesystem identity of one exact attempt."""

    attempt_id: str
    directory: Path
    files: Mapping[str, FileIdentity]

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", MappingProxyType(dict(self.files)))

    @property
    def result(self) -> FileIdentity:
        return self.files[RESULT_NAME]

    @property
    def receipt(self) -> FileIdentity:
        return self.files[RECEIPT_NAME]

    @property
    def attempt_index(self) -> FileIdentity:
        return self.files[INDEX_NAME]


def _fail(code: str, detail: str) -> None:
    raise PublicationError(code, detail)


def _close(fd: int) -> None:
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            pass


def _path(value: Path | str, label: str) -> Path:
    if not isinstance(value, (Path, str)):
        _fail("path", f"{label} must be a pathlib.Path or string")
    path = Path(value)
    if not path.is_absolute():
        _fail("path", f"{label} must be absolute")
    try:
        encoded = os.fsencode(str(path))
    except UnicodeEncodeError as error:
        raise PublicationError("path", f"{label} is not representable by the filesystem") from error
    if len(encoded) > MAX_PARENT_PATH_BYTES or "\x00" in str(path):
        _fail("path", f"{label} exceeds the bounded path limit")
    # Do not normalize or resolve: retaining the caller's components lets the
    # descriptor walk reject traversal and symlink substitutions explicitly.
    if any(part in {"", ".", ".."} or "\x00" in part or "\\" in part for part in path.parts[1:]):
        _fail("path", f"{label} has an unsafe component")
    if len(path.parts) < 2:
        _fail("path", f"{label} must not be the filesystem root")
    for part in path.parts[1:]:
        if len(os.fsencode(part)) > MAX_COMPONENT_BYTES:
            _fail("path", f"{label} has an oversized component")
    return path


def _attempt_id(value: object) -> str:
    if type(value) is not str or not value or len(value.encode("utf-8", errors="replace")) > MAX_ATTEMPT_ID_BYTES:
        _fail("attempt-id", "attempt ID is not bounded")
    if ATTEMPT_RE.fullmatch(value) is None or value in {"attempt-id", "attempt-000"}:
        _fail("attempt-id", "attempt ID is invalid or a placeholder")
    return value


def _open_directory(path: Path, label: str) -> int:
    """Open every component from the root with O_NOFOLLOW."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(os.sep, flags)
    except OSError as error:
        raise PublicationError("unavailable", f"{label}: {error}") from error
    try:
        for component in path.parts[1:]:
            next_fd = -1
            try:
                next_fd = os.open(component, flags, dir_fd=fd)
                previous_fd, fd, next_fd = fd, next_fd, -1
                _close(previous_fd)
            finally:
                _close(next_fd)
        st = os.fstat(fd)
        if not stat.S_ISDIR(st.st_mode):
            _fail("path-type", f"{label} is not a directory")
        return fd
    except PublicationError:
        _close(fd)
        raise
    except OSError as error:
        _close(fd)
        raise PublicationError("unavailable", f"{label}: {error}") from error


def _contract_bytes(result_bytes: bytes, receipt_bytes: bytes, index_bytes: bytes) -> tuple[str, bytes, bytes, bytes]:
    if type(result_bytes) is not bytes or type(receipt_bytes) is not bytes or type(index_bytes) is not bytes:
        _fail("contract", "all publication inputs must be exact bytes")
    try:
        result = contract.validate_result(result_bytes)
        contract.validate_receipt(receipt_bytes, result_bytes)
        contract.validate_attempt_index(index_bytes, result_bytes, receipt_bytes)
    except contract.EvidenceContractError as error:
        raise PublicationError("contract", str(error)) from error
    attempt_id = _attempt_id(result["attempt"]["attempt_id"])
    return attempt_id, result_bytes, receipt_bytes, index_bytes


def _stat_regular(fd: int, label: str, *, mode: int | None = None, size: int | None = None) -> os.stat_result:
    try:
        st = os.fstat(fd)
    except OSError as error:
        raise PublicationError("unavailable", f"{label}: {error}") from error
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        _fail("path-type", f"{label} is not a single-link regular file")
    if mode is not None and stat.S_IMODE(st.st_mode) != mode:
        _fail("mode", f"{label} does not have mode {mode:o}")
    if size is not None and st.st_size != size:
        _fail("race", f"{label} size changed")
    return st


def _metadata(st: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def _read_descriptor(fd: int, limit: int, label: str) -> bytes:
    """Read one descriptor from offset zero with a hard byte bound."""
    try:
        os.lseek(fd, 0, os.SEEK_SET)
    except OSError as error:
        raise PublicationError("unavailable", f"{label}: {error}") from error
    chunks: list[bytes] = []
    total = 0
    while True:
        try:
            chunk = os.read(fd, min(1024 * 1024, limit - total + 1))
        except OSError as error:
            raise PublicationError("unavailable", f"{label}: {error}") from error
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            _fail("size", f"{label} exceeds its bound")
        chunks.append(chunk)
    return b"".join(chunks)


def _write_file(directory_fd: int, name: str, raw: bytes, label: str) -> FileIdentity:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = -1
    try:
        fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
        offset = 0
        while offset < len(raw):
            try:
                written = os.write(fd, raw[offset:])
            except OSError as error:
                raise PublicationError("write", f"{label}: {error}") from error
            if written <= 0:
                _fail("write", f"{label} made no progress")
            offset += written
        os.fsync(fd)
        os.fchmod(fd, FILE_MODES)
        os.fsync(fd)
        writer_before = _stat_regular(fd, label, mode=FILE_MODES, size=len(raw))
        try:
            path_before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as error:
            raise PublicationError("race", f"{label}: {error}") from error
        if _metadata(writer_before) != _metadata(path_before):
            _fail("race", f"{label} changed while publishing")
        read_fd = -1
        try:
            read_fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
            reader_before = _stat_regular(read_fd, label, mode=FILE_MODES, size=len(raw))
            if _metadata(writer_before) != _metadata(reader_before):
                _fail("race", f"{label} reopened a different file")
            persisted = _read_descriptor(read_fd, len(raw), f"{label} persisted readback")
            reader_after = _stat_regular(read_fd, label, mode=FILE_MODES, size=len(raw))
            writer_after = _stat_regular(fd, label, mode=FILE_MODES, size=len(raw))
            path_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if not (_metadata(writer_before) == _metadata(reader_before) == _metadata(reader_after) == _metadata(writer_after) == _metadata(path_after)):
                _fail("race", f"{label} changed during persisted readback")
            persisted_sha = hashlib.sha256(persisted).hexdigest()
            if persisted != raw or persisted_sha != hashlib.sha256(raw).hexdigest():
                _fail("persisted-bytes", f"{label} persisted bytes differ from caller bytes")
            return FileIdentity(Path(name), len(persisted), persisted_sha, stat.S_IMODE(reader_after.st_mode))
        finally:
            _close(read_fd)
    except PublicationError:
        raise
    except FileExistsError as error:
        raise PublicationError("collision", f"{label} already exists") from error
    except OSError as error:
        raise PublicationError("unavailable", f"{label}: {error}") from error
    finally:
        _close(fd)


def _validate_dir_name(directory_fd: int, name: str, label: str, expected_mode: int) -> tuple[int, os.stat_result]:
    fd = -1
    try:
        path_st = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISDIR(path_st.st_mode) or stat.S_IMODE(path_st.st_mode) != expected_mode:
            _fail("directory", f"{label} has wrong type or mode")
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
        opened = os.fstat(fd)
        if _metadata(path_st) != _metadata(opened):
            _fail("race", f"{label} changed while opening")
        return fd, opened
    except PublicationError:
        _close(fd)
        raise
    except OSError as error:
        _close(fd)
        raise PublicationError("unavailable", f"{label}: {error}") from error


def publish_attempt(parent_root: Path | str, result_bytes: bytes, receipt_bytes: bytes, index_bytes: bytes) -> PublishedAttempt:
    """Publish one validated attempt beneath an existing absolute directory.

    The attempt directory is created exclusively.  Any error after that
    creation leaves the directory and any files already written untouched.
    """
    root = _path(parent_root, "parent_root")
    attempt_id, result_bytes, receipt_bytes, index_bytes = _contract_bytes(result_bytes, receipt_bytes, index_bytes)
    parent_fd = _open_directory(root, "parent_root")
    directory_fd = -1
    try:
        try:
            os.mkdir(attempt_id, 0o700, dir_fd=parent_fd)
        except FileExistsError as error:
            raise PublicationError("collision", f"attempt directory {attempt_id} already exists") from error
        except OSError as error:
            raise PublicationError("mkdir", f"attempt directory {attempt_id}: {error}") from error
        # The directory is writable only during this one publication call.
        directory_fd, _ = _validate_dir_name(parent_fd, attempt_id, "attempt directory", 0o700)
        _write_file(directory_fd, RESULT_NAME, result_bytes, RESULT_NAME)
        _write_file(directory_fd, RECEIPT_NAME, receipt_bytes, RECEIPT_NAME)
        _write_file(directory_fd, INDEX_NAME, index_bytes, INDEX_NAME)
        os.fchmod(directory_fd, DIRECTORY_MODE)
        os.fsync(directory_fd)
        os.fsync(parent_fd)
        # Verify the completed closure through one retained-descriptor snapshot.
        # Earlier per-file readbacks prove each individual write; this shared
        # verifier also catches mutation of an earlier member while a later
        # member is being observed.
        _, identities = _verify_closure(
            directory_fd,
            attempt_id,
            expected={RESULT_NAME: result_bytes, RECEIPT_NAME: receipt_bytes, INDEX_NAME: index_bytes},
        )
        final_dir_fd, _ = _validate_dir_name(parent_fd, attempt_id, "attempt directory", DIRECTORY_MODE)
        _close(final_dir_fd)
        directory = root / attempt_id
        identities = {name: FileIdentity(directory / name, item.bytes, item.sha256, item.mode) for name, item in identities.items()}
        return PublishedAttempt(attempt_id, directory, identities)
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("publication", str(error)) from error
    finally:
        _close(directory_fd)
        _close(parent_fd)


def _bounded_layout(directory_fd: int) -> tuple[str, ...]:
    """Read at most four names; the fourth is already a closed-layout error."""
    names: list[str] = []
    try:
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) == 4:
                    break
    except OSError as error:
        raise PublicationError("unavailable", f"attempt directory listing: {error}") from error
    if len(names) != len(FILE_NAMES) or set(names) != set(FILE_NAMES):
        _fail("file-layout", "attempt directory is not exactly the closed three-file layout")
    return tuple(names)


def _verify_closure(
    directory_fd: int,
    attempt_id: str,
    *,
    expected: Mapping[str, bytes] | None = None,
) -> tuple[dict[str, bytes], dict[str, FileIdentity]]:
    """Verify one retained-descriptor three-file closure observation."""
    limits = {
        RESULT_NAME: contract.MAX_RESULT_BYTES,
        RECEIPT_NAME: contract.MAX_RECEIPT_BYTES,
        INDEX_NAME: contract.MAX_INDEX_BYTES,
    }
    if expected is not None and (type(expected) is not dict or set(expected) != set(FILE_NAMES) or any(type(value) is not bytes for value in expected.values())):
        _fail("expected-closure", "expected closure is not the exact three-file byte mapping")
    _bounded_layout(directory_fd)
    descriptors: dict[str, int] = {}
    initial: dict[str, os.stat_result] = {}
    observations: dict[str, bytes] = {}
    identities: dict[str, FileIdentity] = {}
    try:
        # Open and bind all three names before reading any member.  Retaining
        # every descriptor makes a later restat meaningful even if a name is
        # replaced while another member is being read.
        for name in FILE_NAMES:
            path_st = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(path_st.st_mode) or path_st.st_nlink != 1 or stat.S_IMODE(path_st.st_mode) != FILE_MODES:
                _fail("file-layout", f"{name} is not a 0444 single-link regular file")
            if path_st.st_size > limits[name]:
                _fail("size", f"{name} exceeds its bound")
            fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
            descriptors[name] = fd
            opened = _stat_regular(fd, name, mode=FILE_MODES)
            if _metadata(path_st) != _metadata(opened):
                _fail("race", f"{name} changed while opening the closure")
            initial[name] = opened

        for name in FILE_NAMES:
            fd = descriptors[name]
            first = _read_descriptor(fd, limits[name], f"{name} first read")
            middle = _stat_regular(fd, name, mode=FILE_MODES, size=len(first))
            middle_path = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if _metadata(initial[name]) != _metadata(middle) or _metadata(middle) != _metadata(middle_path):
                _fail("race", f"{name} changed during first closure read")
            second = _read_descriptor(fd, limits[name], f"{name} second read")
            second_stat = _stat_regular(fd, name, mode=FILE_MODES, size=len(second))
            second_path = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if _metadata(initial[name]) != _metadata(second_stat) or _metadata(second_stat) != _metadata(second_path):
                _fail("race", f"{name} changed during second closure read")
            first_sha = hashlib.sha256(first).hexdigest()
            second_sha = hashlib.sha256(second).hexdigest()
            if first != second or first_sha != second_sha:
                _fail("content-race", f"{name} differs across bounded reads")
            observations[name] = first
            identities[name] = FileIdentity(Path(name), len(first), first_sha, stat.S_IMODE(second_stat.st_mode))

        _bounded_layout(directory_fd)
        # All descriptors remain open through this final all-member restat.
        # mtime/ctime are retained in _metadata, closing the same-size mutation
        # gap that inode/mode/link/size checks alone would leave.
        for name in FILE_NAMES:
            final_fd = _stat_regular(descriptors[name], name, mode=FILE_MODES, size=len(observations[name]))
            final_path = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if _metadata(initial[name]) != _metadata(final_fd) or _metadata(final_fd) != _metadata(final_path):
                _fail("race", f"{name} changed before closure validation")

        actual_id, _, _, _ = _contract_bytes(
            observations[RESULT_NAME], observations[RECEIPT_NAME], observations[INDEX_NAME]
        )
        if actual_id != attempt_id:
            _fail("attempt-mismatch", "result attempt ID differs from directory name")
        if expected is not None and any(observations[name] != expected[name] for name in FILE_NAMES):
            _fail("persisted-closure", "completed attempt bytes differ from caller bytes")
        return observations, identities
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("unavailable", f"closure verification: {error}") from error
    finally:
        for fd in descriptors.values():
            _close(fd)


def read_attempt(parent_root: Path | str, attempt_id: str) -> PublishedAttempt:
    """Read and validate a closed immutable attempt directory."""
    root = _path(parent_root, "parent_root")
    attempt_id = _attempt_id(attempt_id)
    parent_fd = _open_directory(root, "parent_root")
    directory_fd = -1
    try:
        directory_fd, directory_before = _validate_dir_name(parent_fd, attempt_id, "attempt directory", DIRECTORY_MODE)
        _, verified_identities = _verify_closure(directory_fd, attempt_id)
        # Check the directory after all reads, closing the TOCTOU window around
        # a replacement or chmod by another process.
        final = os.fstat(directory_fd)
        named = os.stat(attempt_id, dir_fd=parent_fd, follow_symlinks=False)
        if not (_metadata(directory_before) == _metadata(final) == _metadata(named)) or stat.S_IMODE(final.st_mode) != DIRECTORY_MODE:
            _fail("race", "attempt directory changed while reading")
        directory = root / attempt_id
        identities = {name: FileIdentity(directory / name, item.bytes, item.sha256, item.mode) for name, item in verified_identities.items()}
        return PublishedAttempt(attempt_id, directory, identities)
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("unavailable", f"attempt read: {error}") from error
    finally:
        _close(directory_fd)
        _close(parent_fd)


# Small aliases for callers that prefer noun/verb names.
publish = publish_attempt
read_published_attempt = read_attempt


__all__ = [
    "RESULT_NAME", "RECEIPT_NAME", "INDEX_NAME", "FILE_NAMES", "FILE_MODES", "DIRECTORY_MODE",
    "PublicationError", "FileIdentity", "PublishedAttempt", "publish_attempt", "publish", "read_attempt",
    "read_published_attempt",
]

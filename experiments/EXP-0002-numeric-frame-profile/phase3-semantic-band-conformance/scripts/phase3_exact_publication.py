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
the verifier returns.  ``reserve_experiment_slot`` additionally leaves a
durable marker in one package-owned namespace before attempt work begins.  It
provides exactly-once cooperative accounting for the frozen manifest hash,
platform selector, and ordinal; tokens and markers are deliberately not
described as unforgeable security capabilities or hostile cross-process locks.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
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
PUBLICATION_TRUST_BOUNDARY = "cooperating-same-process-local-posix-v1"
EXPERIMENT_SLOT_SCHEMA = "ck.exp-0002.phase3.experiment-slot-reservation-1"
EXPERIMENT_SLOT_NAMESPACE = Path(__file__).resolve().parents[1] / "results" / "exact-slot-reservations"
EXPERIMENT_SLOT_SELECTORS = {
    "wsl2-x86_64": frozenset({0, 1}),
    "ubuntu-24.04-x86_64": frozenset({2}),
}


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


_RESERVATION_TOKEN = object()


@dataclass(frozen=True)
class _IssuedReservation:
    """Immutable facts captured when the cooperative handle is issued."""

    parent_root: Path
    attempt_id: str
    parent_initial: os.stat_result
    directory_initial: os.stat_result


class AttemptReservation:
    """One-shot cooperative handle for an empty prelaunch attempt directory.

    The private token detects accidental construction through the public API;
    it is not an unforgeable capability against arbitrary Python code in the
    same process.  A per-handle lock makes publish/close atomic among
    cooperating same-process threads.
    """

    __slots__ = (
        "_token", "_issued", "_parent_fd", "_directory_fd", "_lock", "_state", "_slot_binding",
    )

    def __init__(
        self,
        *,
        parent_root: Path,
        attempt_id: str,
        parent_fd: int,
        directory_fd: int,
        parent_initial: os.stat_result,
        directory_initial: os.stat_result,
        _token: object,
    ) -> None:
        if _token is not _RESERVATION_TOKEN:
            _fail("reservation", "attempt reservation was not issued by this module")
        self._token = _token
        self._issued = _IssuedReservation(parent_root, attempt_id, parent_initial, directory_initial)
        self._parent_fd = parent_fd
        self._directory_fd = directory_fd
        self._lock = threading.RLock()
        self._state = "issued"
        self._slot_binding = None

    @property
    def parent_root(self) -> Path:
        return self._issued.parent_root

    @property
    def attempt_id(self) -> str:
        return self._issued.attempt_id

    @property
    def directory(self) -> Path:
        return self._issued.parent_root / self._issued.attempt_id

    @property
    def experiment_slot(self) -> Mapping[str, object] | None:
        binding = self._slot_binding
        return None if binding is None else MappingProxyType(dict(binding))

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._state == "closed"

    def close(self) -> None:
        with self._lock:
            # A re-entrant callback in the publishing thread must not close
            # descriptors out from under its own active publication.  Other
            # threads block on the lock until publication has consumed them.
            if self._state in {"publishing", "closed"}:
                return
            self._close_locked()

    def _close_locked(self) -> None:
        parent_fd, directory_fd = self._parent_fd, self._directory_fd
        self._parent_fd = -1
        self._directory_fd = -1
        self._state = "closed"
        _close(directory_fd)
        _close(parent_fd)


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


def _slot_binding(
    successor_manifest_sha256: object,
    platform_selector: object,
    ordinal: object,
    attempt_id: object,
) -> dict[str, object]:
    if type(successor_manifest_sha256) is not str or len(successor_manifest_sha256) != 64 or any(c not in "0123456789abcdef" for c in successor_manifest_sha256):
        _fail("slot-key", "successor manifest hash is not lowercase SHA-256")
    if type(platform_selector) is not str or platform_selector not in EXPERIMENT_SLOT_SELECTORS:
        _fail("slot-key", "platform selector is not preregistered")
    if type(ordinal) is not int or isinstance(ordinal, bool) or ordinal not in EXPERIMENT_SLOT_SELECTORS[platform_selector]:
        _fail("slot-key", "ordinal is not allowed for the selected platform")
    return {
        "successor_manifest_sha256": successor_manifest_sha256,
        "platform_selector": platform_selector,
        "ordinal": ordinal,
        "attempt_id": _attempt_id(attempt_id),
    }


def _slot_canonical(value: Mapping[str, object]) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise PublicationError("slot-record", "slot reservation is not canonical JSON") from error


def _slot_paths(binding: Mapping[str, object], namespace: Path) -> tuple[Path, Path]:
    digest = str(binding["successor_manifest_sha256"])
    selector = str(binding["platform_selector"])
    ordinal = str(binding["ordinal"])
    directory = namespace / digest / selector
    return directory, directory / f"ordinal-{ordinal}.json"


def _reserve_slot_marker(binding: Mapping[str, object]) -> None:
    """Persist the experiment-wide consumed slot before attempt work begins."""
    namespace = _path(EXPERIMENT_SLOT_NAMESPACE, "experiment slot namespace")
    directory, marker = _slot_paths(binding, namespace)
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        raw = _slot_canonical({"schema": EXPERIMENT_SLOT_SCHEMA, **dict(binding)})
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o600)
        try:
            offset = 0
            while offset < len(raw):
                written = os.write(fd, raw[offset:])
                if written <= 0:
                    _fail("slot-write", "slot marker made no progress")
                offset += written
            os.fsync(fd)
            os.fchmod(fd, 0o600)
            os.fsync(fd)
        finally:
            _close(fd)
        _fsync_path(directory)
        _fsync_path(namespace)
    except FileExistsError as error:
        raise PublicationError("slot-consumed", "experiment slot is already bound to an attempt") from error
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("slot-reservation", f"cannot consume experiment slot: {error}") from error


def _fsync_path(path: Path) -> None:
    fd = -1
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) if path.is_dir() else os.O_RDONLY)
        os.fsync(fd)
    except OSError as error:
        raise PublicationError("slot-reservation", f"cannot fsync slot namespace: {error}") from error
    finally:
        _close(fd)


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


def _open_dir_name(directory_fd: int, name: str, label: str) -> tuple[int, os.stat_result]:
    fd = -1
    try:
        path_st = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISDIR(path_st.st_mode):
            _fail("directory", f"{label} has wrong type")
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


def _validate_dir_name(directory_fd: int, name: str, label: str, expected_mode: int) -> tuple[int, os.stat_result]:
    fd = -1
    try:
        fd, opened = _open_dir_name(directory_fd, name, label)
        if stat.S_IMODE(opened.st_mode) != expected_mode:
            _fail("directory", f"{label} has wrong mode")
        return fd, opened
    except PublicationError:
        _close(fd)
        raise


def _parent_identity(st: os.stat_result) -> tuple[int, int, int]:
    return st.st_dev, st.st_ino, st.st_mode


def _empty_directory(directory_fd: int) -> None:
    """Reject after observing at most one directory member."""
    try:
        with os.scandir(directory_fd) as entries:
            for _ in entries:
                _fail("reservation-not-empty", "reserved attempt directory is not empty")
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("unavailable", f"reserved attempt directory listing: {error}") from error


def _reserve_attempt_for_test(parent_root: Path | str, attempt_id: str) -> AttemptReservation:
    """Test-only local reservation helper; it is not experiment-wide.

    The empty ``0700`` directory is the durable consumed marker.  Closing the
    returned reservation, process failure, or a later publication failure
    never removes it and a second reservation of the same ID fails closed.
    This is local to the explicitly supplied root; it is not global replay
    prevention across independent roots.
    """
    root = _path(parent_root, "parent_root")
    attempt_id = _attempt_id(attempt_id)
    parent_fd = _open_directory(root, "parent_root")
    directory_fd = -1
    try:
        try:
            os.mkdir(attempt_id, 0o700, dir_fd=parent_fd)
        except FileExistsError as error:
            raise PublicationError("collision", f"attempt directory {attempt_id} already exists") from error
        except OSError as error:
            raise PublicationError("mkdir", f"attempt directory {attempt_id}: {error}") from error
        # POSIX mkdir does not return a descriptor.  Within the supported
        # cooperating local boundary, immediately capture the dirfd-anchored
        # identity, normalize umask effects without following symlinks, then
        # require that the same object is opened.  This detects replacements
        # overlapping these observations.  A hostile same-UID process that
        # replaces the name before the first stat remains outside the stated
        # trust boundary; this is not claimed as a global capability lock.
        created = os.stat(attempt_id, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(created.st_mode):
            _fail("race", "created attempt path is no longer a directory")
        os.chmod(attempt_id, 0o700, dir_fd=parent_fd, follow_symlinks=False)
        normalized = os.stat(attempt_id, dir_fd=parent_fd, follow_symlinks=False)
        if (created.st_dev, created.st_ino) != (normalized.st_dev, normalized.st_ino):
            _fail("race", "attempt directory changed between mkdir and mode normalization")
        directory_fd, opened = _validate_dir_name(parent_fd, attempt_id, "attempt directory", 0o700)
        if (created.st_dev, created.st_ino) != (opened.st_dev, opened.st_ino):
            _fail("race", "attempt directory changed between mkdir and descriptor binding")
        os.fchmod(directory_fd, 0o700)
        os.fsync(directory_fd)
        directory_initial = os.fstat(directory_fd)
        directory_named = os.stat(attempt_id, dir_fd=parent_fd, follow_symlinks=False)
        if _metadata(directory_initial) != _metadata(directory_named):
            _fail("race", "attempt directory changed while setting reservation mode")
        _empty_directory(directory_fd)
        os.fsync(parent_fd)
        parent_initial = os.fstat(parent_fd)
        reservation = AttemptReservation(
            parent_root=root,
            attempt_id=attempt_id,
            parent_fd=parent_fd,
            directory_fd=directory_fd,
            parent_initial=parent_initial,
            directory_initial=directory_initial,
            _token=_RESERVATION_TOKEN,
        )
        parent_fd = -1
        directory_fd = -1
        return reservation
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("reservation", str(error)) from error
    finally:
        _close(directory_fd)
        _close(parent_fd)


def reserve_experiment_slot(
    parent_root: Path | str,
    successor_manifest_sha256: str,
    platform_selector: str,
    ordinal: int,
    attempt_id: str,
) -> AttemptReservation:
    """Consume one experiment-wide slot and return a publication reservation.

    The slot marker is rooted at the package-owned ``EXPERIMENT_SLOT_NAMESPACE``;
    ``parent_root`` is only the immutable publication directory for the returned
    handle.  Consequently two callers cannot evade exactly-once accounting by
    selecting different output roots.  The marker is written first, so every
    failed or abandoned reservation remains consumed.  This is cooperative
    local trust, not a hostile-process or cross-machine lock.
    """
    binding = _slot_binding(successor_manifest_sha256, platform_selector, ordinal, attempt_id)
    _reserve_slot_marker(binding)
    try:
        reservation = _reserve_attempt_for_test(parent_root, str(binding["attempt_id"]))
    except Exception:
        # Deliberately retain the marker: a consumed slot cannot be retried
        # after an output-root failure or a process interruption.
        raise
    reservation._slot_binding = dict(binding)
    return reservation


def _require_reservation(value: object) -> AttemptReservation:
    if type(value) is not AttemptReservation or getattr(value, "_token", None) is not _RESERVATION_TOKEN:
        _fail("reservation", "reservation was not issued by this module or has the wrong type")
    return value


def _claim_reservation(value: object) -> AttemptReservation:
    """Atomically claim a handle and hold its lock through publish/close."""
    reservation = _require_reservation(value)
    reservation._lock.acquire()
    if reservation._state != "issued" or reservation._parent_fd < 0 or reservation._directory_fd < 0:
        reservation._lock.release()
        _fail("reservation-closed", "reservation is already closed, consumed, or being published")
    reservation._state = "publishing"
    return reservation


def _finish_reservation(reservation: AttemptReservation) -> None:
    """Consume a claimed handle while its same-process lock remains held."""
    try:
        reservation._close_locked()
    finally:
        reservation._lock.release()


def _verify_reservation(reservation: AttemptReservation) -> None:
    try:
        parent_now = os.fstat(reservation._parent_fd)
        directory_now = os.fstat(reservation._directory_fd)
    except OSError as error:
        raise PublicationError("reservation-unavailable", str(error)) from error
    if _parent_identity(parent_now) != _parent_identity(reservation._issued.parent_initial):
        _fail("reservation-root", "held parent directory identity changed")
    if _metadata(directory_now) != _metadata(reservation._issued.directory_initial) or stat.S_IMODE(directory_now.st_mode) != 0o700:
        _fail("reservation-directory", "held attempt directory changed before publication")

    reopened_root = -1
    reopened_directory = -1
    try:
        reopened_root = _open_directory(reservation.parent_root, "reservation parent_root")
        if _parent_identity(os.fstat(reopened_root)) != _parent_identity(parent_now):
            _fail("reservation-root", "parent_root path no longer names the held directory")
        reopened_directory, named = _validate_dir_name(
            reservation._parent_fd, reservation.attempt_id, "reserved attempt directory", 0o700
        )
        if _metadata(named) != _metadata(reservation._issued.directory_initial) or _metadata(os.fstat(reopened_directory)) != _metadata(directory_now):
            _fail("reservation-directory", "attempt path no longer names the held reservation")
        _empty_directory(reservation._directory_fd)
        _empty_directory(reopened_directory)
    finally:
        _close(reopened_directory)
        _close(reopened_root)


def _verify_experiment_slot(reservation: AttemptReservation, result_bytes: bytes) -> None:
    binding = getattr(reservation, "_slot_binding", None)
    if binding is None:
        return
    try:
        result = contract.validate_result(result_bytes)
    except contract.EvidenceContractError as error:
        raise PublicationError("contract", str(error)) from error
    attempt = result.get("attempt")
    if not isinstance(attempt, Mapping):
        _fail("slot-binding", "result attempt metadata is unavailable")
    expected = {
        "successor_manifest_sha256": attempt.get("freeze_manifest_sha256"),
        "platform_selector": attempt.get("platform_selector"),
        "ordinal": attempt.get("ordinal"),
        "attempt_id": attempt.get("attempt_id"),
    }
    if expected != binding:
        _fail("slot-binding", "result attempt metadata differs from the consumed experiment slot")


def _verify_final_named_paths(reservation: AttemptReservation) -> None:
    """Rebind both public names to the retained descriptors before return."""
    try:
        parent_now = os.fstat(reservation._parent_fd)
        directory_now = os.fstat(reservation._directory_fd)
    except OSError as error:
        raise PublicationError("reservation-unavailable", str(error)) from error
    if _parent_identity(parent_now) != _parent_identity(reservation._issued.parent_initial):
        _fail("reservation-root", "held parent directory identity changed during publication")
    if not stat.S_ISDIR(directory_now.st_mode) or stat.S_IMODE(directory_now.st_mode) != DIRECTORY_MODE:
        _fail("reservation-directory", "held attempt directory is not a closed publication directory")

    reopened_root = -1
    reopened_directory = -1
    try:
        reopened_root = _open_directory(reservation.parent_root, "final reservation parent_root")
        if _parent_identity(os.fstat(reopened_root)) != _parent_identity(parent_now):
            _fail("reservation-root", "parent_root path no longer names the held directory at publication return")
        reopened_directory, named = _validate_dir_name(
            reopened_root, reservation.attempt_id, "final attempt directory", DIRECTORY_MODE
        )
        if _metadata(named) != _metadata(directory_now) or _metadata(os.fstat(reopened_directory)) != _metadata(directory_now):
            _fail("reservation-directory", "attempt path no longer names the held directory at publication return")
    finally:
        _close(reopened_directory)
        _close(reopened_root)


def publish_reserved_attempt(
    reservation: AttemptReservation,
    result_bytes: bytes,
    receipt_bytes: bytes,
    index_bytes: bytes,
) -> PublishedAttempt:
    """Consume one reservation and publish its already-built evidence bytes."""
    reservation = _claim_reservation(reservation)
    try:
        attempt_id, result_bytes, receipt_bytes, index_bytes = _contract_bytes(result_bytes, receipt_bytes, index_bytes)
        if attempt_id != reservation.attempt_id:
            _fail("attempt-mismatch", "evidence attempt ID differs from the prelaunch reservation")
        _verify_experiment_slot(reservation, result_bytes)
        _verify_reservation(reservation)
        directory_fd = reservation._directory_fd
        parent_fd = reservation._parent_fd
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
        directory = reservation.directory
        identities = {name: FileIdentity(directory / name, item.bytes, item.sha256, item.mode) for name, item in identities.items()}
        published = PublishedAttempt(attempt_id, directory, identities)
        _verify_final_named_paths(reservation)
        return published
    except PublicationError:
        raise
    except OSError as error:
        raise PublicationError("publication", str(error)) from error
    finally:
        _finish_reservation(reservation)


def _publish_attempt_for_test(parent_root: Path | str, result_bytes: bytes, receipt_bytes: bytes, index_bytes: bytes) -> PublishedAttempt:
    """Test-only local publication helper; it is not experiment-wide."""
    attempt_id, result_bytes, receipt_bytes, index_bytes = _contract_bytes(result_bytes, receipt_bytes, index_bytes)
    reservation = _reserve_attempt_for_test(parent_root, attempt_id)
    return publish_reserved_attempt(reservation, result_bytes, receipt_bytes, index_bytes)


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


# Small reader alias for callers that prefer a noun name.
read_published_attempt = read_attempt


__all__ = [
    "RESULT_NAME", "RECEIPT_NAME", "INDEX_NAME", "FILE_NAMES", "FILE_MODES", "DIRECTORY_MODE",
    "PUBLICATION_TRUST_BOUNDARY", "EXPERIMENT_SLOT_SCHEMA", "EXPERIMENT_SLOT_NAMESPACE", "EXPERIMENT_SLOT_SELECTORS",
    "PublicationError", "FileIdentity", "PublishedAttempt", "AttemptReservation", "reserve_experiment_slot",
    "publish_reserved_attempt", "read_attempt", "read_published_attempt",
]

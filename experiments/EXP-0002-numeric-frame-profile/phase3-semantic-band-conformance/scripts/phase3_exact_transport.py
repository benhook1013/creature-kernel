"""Fail-closed Linux x86_64 exact candidate transport.

The launcher accepts an already-open, caller-verified executable descriptor.
It never turns a caller path into an executable path and never invokes a
shell, wrapper, or retry.  The child self-traces, stops before ``execve`` and
is resumed only after the parent has seen the post-exec ptrace trap, verified
descriptor identity through ``/proc/<pid>/exe`` and the retained descriptor,
and observed the actual x87/MXCSR register image.

This is bounded transport plumbing, not an experiment runner.  It owns one
process/session, preserves caller request bytes (adding only a missing LF),
retains exact frame/output bytes and hashes, and kills/reaps on every failure.
"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import fcntl
import resource
import selectors
import signal
import stat
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import phase3_exact_fp_observer as fp
from phase3_common import (
    FRAME_BYTES,
    IO_DEADLINE_SECONDS,
    MAX_SESSION_RECORDS,
    SESSION_STDOUT_CAP,
    STDERR_TOTAL_CAP,
    SHUTDOWN_DEADLINE_SECONDS,
    TRAILING_OUTPUT_QUIET_SECONDS,
)


STDOUT_TOTAL_CAP = SESSION_STDOUT_CAP
MAX_SESSION_FRAMES = MAX_SESSION_RECORDS
MAX_EXECUTABLE_BYTES = 64 * 1024 * 1024
MAX_DEADLINE_SECONDS = 60.0
MAX_REQUEST_ID_BYTES = 256
MAX_ARGV0_BYTES = 256
MAX_ENV_ITEMS = 128
MAX_ENV_NAME_BYTES = 256
MAX_ENV_VALUE_BYTES = 4096
MAX_ENV_TOTAL_BYTES = 64 * 1024
# Linux memfd sealing constants (fcntl.h); use numeric fallbacks for Python
# versions whose fcntl module does not expose them.
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_MEMFD_SEALS = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE
# A terminal wait is still nonblocking with respect to candidate I/O, but the
# kernel may publish pipe EOF and the waitable exit state on adjacent scheduler
# ticks.  A one-microsecond probe can repeatedly miss that transition and
# leave an already-zombie tracee unreaped.  Keep one bounded owner of wait4()
# while giving it a short publication window.
TERMINAL_POLL_SECONDS = 0.01
CHILD_EXEC_FD = 198
CHILD_ERROR_FD = 199


class ExactTransportError(ValueError):
    """Stable transport/lifecycle failure with retained partial evidence."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


@dataclass(frozen=True)
class ExactTransportLimits:
    frame_bytes: int = FRAME_BYTES
    stdout_total_bytes: int = STDOUT_TOTAL_CAP
    stderr_total_bytes: int = STDERR_TOTAL_CAP
    max_frames: int = MAX_SESSION_FRAMES
    io_deadline_seconds: float = IO_DEADLINE_SECONDS
    shutdown_deadline_seconds: float = SHUTDOWN_DEADLINE_SECONDS
    trailing_output_quiet_seconds: float = TRAILING_OUTPUT_QUIET_SECONDS

    def __post_init__(self) -> None:
        for name in ("frame_bytes", "stdout_total_bytes", "stderr_total_bytes", "max_frames"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.frame_bytes > FRAME_BYTES:
            raise ValueError(f"frame_bytes cannot exceed frozen {FRAME_BYTES}-byte cap")
        if self.stdout_total_bytes > STDOUT_TOTAL_CAP:
            raise ValueError(f"stdout_total_bytes cannot exceed frozen {STDOUT_TOTAL_CAP}-byte cap")
        if self.stderr_total_bytes > STDERR_TOTAL_CAP:
            raise ValueError(f"stderr_total_bytes cannot exceed frozen {STDERR_TOTAL_CAP}-byte cap")
        if self.max_frames > MAX_SESSION_FRAMES:
            raise ValueError(f"max_frames cannot exceed frozen {MAX_SESSION_FRAMES}-frame cap")
        for name in ("io_deadline_seconds", "shutdown_deadline_seconds", "trailing_output_quiet_seconds"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be a finite number")
            if name == "trailing_output_quiet_seconds":
                if value <= 0 or value > MAX_DEADLINE_SECONDS:
                    raise ValueError(f"{name} must be positive and bounded")
            elif value <= 0 or value > MAX_DEADLINE_SECONDS:
                raise ValueError(f"{name} must be positive and bounded")


@dataclass(frozen=True)
class DescriptorIdentity:
    device: int
    inode: int
    mode: int
    size: int
    nlink: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "DescriptorIdentity":
        return cls(
            device=int(value.st_dev),
            inode=int(value.st_ino),
            mode=int(value.st_mode),
            size=int(value.st_size),
            nlink=int(value.st_nlink),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "size": self.size,
            "nlink": self.nlink,
        }


@dataclass(frozen=True)
class ContentObservation:
    size: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {"size": self.size, "sha256": self.sha256}


@dataclass(frozen=True)
class LaunchResult:
    status: str
    code: str
    detail: str
    pid: int | None
    observation: fp.FPStateObservation | None
    descriptor_pre: DescriptorIdentity | None
    descriptor_post_exe: DescriptorIdentity | None
    descriptor_post_fd: DescriptorIdentity | None
    cwd_pre: DescriptorIdentity | None = None
    cwd_post: DescriptorIdentity | None = None
    content_initial: ContentObservation | None = None
    content_pre_fork: ContentObservation | None = None
    content_post_exec: ContentObservation | None = None
    startup_error: bytes = b""
    seals_initial: int | None = None
    seals_pre_fork: int | None = None
    seals_post_exec: int | None = None

    @property
    def observed(self) -> bool:
        return self.status == "observed" and self.observation is not None and self.observation.usable

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
            "pid": self.pid,
            "observation": None if self.observation is None else self.observation.to_dict(),
            "descriptor_pre": None if self.descriptor_pre is None else self.descriptor_pre.to_dict(),
            "descriptor_post_exe": None if self.descriptor_post_exe is None else self.descriptor_post_exe.to_dict(),
            "descriptor_post_fd": None if self.descriptor_post_fd is None else self.descriptor_post_fd.to_dict(),
            "cwd_pre": None if self.cwd_pre is None else self.cwd_pre.to_dict(),
            "cwd_post": None if self.cwd_post is None else self.cwd_post.to_dict(),
            "content_initial": None if self.content_initial is None else self.content_initial.to_dict(),
            "content_pre_fork": None if self.content_pre_fork is None else self.content_pre_fork.to_dict(),
            "content_post_exec": None if self.content_post_exec is None else self.content_post_exec.to_dict(),
            "seals_initial": self.seals_initial,
            "seals_pre_fork": self.seals_pre_fork,
            "seals_post_exec": self.seals_post_exec,
            "startup_error": self.startup_error.decode("utf-8", errors="replace"),
        }


@dataclass(frozen=True)
class ExactTransportResult:
    status: str
    code: str | None
    detail: str | None
    launch: LaunchResult
    final_observation: fp.FPStateObservation | None
    returncode: int | None
    exit_code: int | None
    term_signal: int | None
    requests: tuple[bytes, ...]
    responses: tuple[bytes, ...]
    stdout: bytes
    stderr: bytes
    trailing_stdout: bytes
    request_sha256: tuple[str, ...]
    response_sha256: tuple[str, ...]
    stdout_sha256: str
    stderr_sha256: str
    request_count: int
    response_count: int
    process_group_id: int | None
    reaped: bool
    killed: bool
    clean_shutdown: bool
    partial: bool
    attempt_count: int = 1
    rusage: Mapping[str, Any] | None = None
    startup_error: bytes = b""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
            "launch": self.launch.to_dict(),
            "final_observation": None if self.final_observation is None else self.final_observation.to_dict(),
            "returncode": self.returncode,
            "exit_code": self.exit_code,
            "term_signal": self.term_signal,
            "request_count": self.request_count,
            "response_count": self.response_count,
            "request_sha256": list(self.request_sha256),
            "response_sha256": list(self.response_sha256),
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "trailing_stdout_sha256": hashlib.sha256(self.trailing_stdout).hexdigest(),
            "process_group_id": self.process_group_id,
            "reaped": self.reaped,
            "killed": self.killed,
            "clean_shutdown": self.clean_shutdown,
            "partial": self.partial,
            "attempt_count": self.attempt_count,
            "rusage": None if self.rusage is None else dict(self.rusage),
            "startup_error": self.startup_error.decode("utf-8", errors="replace"),
        }


def _strict_object(frame: bytes, label: str) -> dict[str, Any]:
    try:
        text = frame.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ExactTransportError("malformed-" + label, f"{label} is not UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, TypeError, ValueError) as error:
        raise ExactTransportError("malformed-" + label, f"{label} is not one strict JSON object") from error
    if not isinstance(value, dict):
        raise ExactTransportError("malformed-" + label, f"{label} is not a JSON object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _validate_request_id(value: Any, code_prefix: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExactTransportError(code_prefix, "request_id must be a non-empty string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ExactTransportError(f"{code_prefix}-utf8", "request_id must be UTF-8 encodable") from error
    if len(encoded) > MAX_REQUEST_ID_BYTES:
        raise ExactTransportError(
            f"{code_prefix}-too-large",
            f"request_id exceeds {MAX_REQUEST_ID_BYTES} UTF-8 bytes",
        )
    return value


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_environment(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("environment must be a mapping of exact strings")
    if len(value) > MAX_ENV_ITEMS:
        raise ValueError(f"environment cannot contain more than {MAX_ENV_ITEMS} entries")
    result: dict[str, str] = {}
    total_bytes = 0
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ValueError("environment keys and values must be strings")
        if not key or "=" in key or "\x00" in key or "\x00" in item:
            raise ValueError("environment contains an empty, '=' or NUL member")
        # Reject surrogate/non-UTF-8 strings before forking, instead of
        # allowing os.execve to apply an implicit filesystem encoding.
        try:
            key_bytes = key.encode("utf-8")
            item_bytes = item.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("environment contains a non-UTF-8 string") from error
        if len(key_bytes) > MAX_ENV_NAME_BYTES:
            raise ValueError(f"environment name exceeds {MAX_ENV_NAME_BYTES} UTF-8 bytes")
        if len(item_bytes) > MAX_ENV_VALUE_BYTES:
            raise ValueError(f"environment value exceeds {MAX_ENV_VALUE_BYTES} UTF-8 bytes")
        total_bytes += len(key_bytes) + 1 + len(item_bytes) + 1
        if total_bytes > MAX_ENV_TOTAL_BYTES:
            raise ValueError(f"environment exceeds {MAX_ENV_TOTAL_BYTES} aggregate UTF-8 bytes")
        result[key] = item
    return result


def _validate_argv0(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("argv0 must be one non-empty NUL-free string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("argv0 must be UTF-8 encodable") from error
    if len(encoded) > MAX_ARGV0_BYTES:
        raise ValueError(f"argv0 exceeds {MAX_ARGV0_BYTES} UTF-8 bytes")
    return value


def _validate_cwd(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or not os.path.isabs(value):
        raise ValueError("cwd must be one absolute NUL-free path")
    value.encode("utf-8")
    return value


def _descriptor_seals(fd: int) -> int:
    try:
        seals = int(fcntl.fcntl(fd, F_GET_SEALS))
    except OSError as error:
        raise ExactTransportError("descriptor-not-sealed", "executable descriptor is not a readable Linux sealed memfd") from error
    if seals & REQUIRED_MEMFD_SEALS != REQUIRED_MEMFD_SEALS:
        raise ExactTransportError(
            "descriptor-not-sealed",
            "executable descriptor lacks F_SEAL_WRITE, F_SEAL_GROW, F_SEAL_SHRINK, and F_SEAL_SEAL",
        )
    return seals


def _descriptor_identity(fd: int) -> DescriptorIdentity:
    try:
        value = os.fstat(fd)
    except OSError as error:
        raise ExactTransportError("descriptor-unavailable", str(error)) from error
    if not stat.S_ISREG(value.st_mode):
        raise ExactTransportError("descriptor-not-regular", "executable descriptor is not a regular file")
    if not value.st_mode & 0o111:
        raise ExactTransportError("descriptor-not-executable", "executable descriptor has no execute bit")
    _descriptor_seals(fd)
    return DescriptorIdentity.from_stat(value)


def _directory_identity(fd: int) -> DescriptorIdentity:
    try:
        value = os.fstat(fd)
    except OSError as error:
        raise ExactTransportError("cwd-descriptor-unavailable", str(error)) from error
    if not stat.S_ISDIR(value.st_mode):
        raise ExactTransportError("cwd-not-directory", "cwd descriptor is not a directory")
    if value.st_nlink < 1:
        raise ExactTransportError("cwd-unlinked", "cwd directory has no link")
    identity = DescriptorIdentity.from_stat(value)
    # Directory size and link count legitimately change when unrelated
    # children are created. Device/inode/type/mode identify the retained cwd
    # object; content custody belongs to the executable regular file only.
    return DescriptorIdentity(identity.device, identity.inode, identity.mode, 0, 0)


def _validate_expected_content(expected_bytes: bytes | None, expected_sha256: str | None) -> tuple[bytes, str]:
    if not isinstance(expected_bytes, bytes):
        raise ExactTransportError("expected-content-required", "expected executable bytes are required")
    if len(expected_bytes) > MAX_EXECUTABLE_BYTES:
        raise ExactTransportError("expected-content-too-large", "expected executable exceeds the bounded content cap")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(char not in "0123456789abcdef" for char in expected_sha256):
        raise ExactTransportError("expected-hash-required", "expected executable SHA-256 must be lowercase hexadecimal")
    actual = _hash(expected_bytes)
    if actual != expected_sha256:
        raise ExactTransportError("expected-hash-mismatch", "expected bytes do not match expected SHA-256")
    return expected_bytes, expected_sha256


def _read_fd_content(fd: int) -> ContentObservation:
    """Hash an already-open read-only regular file without changing its offset."""

    try:
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        value = os.fstat(fd)
    except OSError as error:
        raise ExactTransportError("descriptor-read", str(error)) from error
    if flags & os.O_ACCMODE != os.O_RDONLY:
        raise ExactTransportError("descriptor-not-readonly", "executable descriptor must be opened O_RDONLY")
    if not stat.S_ISREG(value.st_mode):
        raise ExactTransportError("descriptor-not-regular", "executable descriptor is not a regular file")
    size = int(value.st_size)
    if size < 0 or size > MAX_EXECUTABLE_BYTES:
        raise ExactTransportError("descriptor-size", "executable descriptor exceeds the bounded content cap")
    digest = hashlib.sha256()
    offset = 0
    while offset < size:
        try:
            chunk = os.pread(fd, min(1024 * 1024, size - offset), offset)
        except OSError as error:
            raise ExactTransportError("descriptor-read", str(error)) from error
        if not chunk:
            raise ExactTransportError("descriptor-short-read", "executable descriptor ended before its bounded size")
        digest.update(chunk)
        offset += len(chunk)
    try:
        after = os.fstat(fd)
    except OSError as error:
        raise ExactTransportError("descriptor-read", str(error)) from error
    if DescriptorIdentity.from_stat(value) != DescriptorIdentity.from_stat(after):
        raise ExactTransportError("descriptor-content-race", "executable descriptor identity changed during hash")
    return ContentObservation(size=size, sha256=digest.hexdigest())


def _status_to_exit(status: int) -> tuple[int | None, int | None, int | None]:
    if os.WIFEXITED(status):
        code = os.WEXITSTATUS(status)
        return code, code, None
    if os.WIFSIGNALED(status):
        signum = os.WTERMSIG(status)
        return -signum, None, signum
    return None, None, None


def _allocate_transport_pipes(pipe_flags: int) -> tuple[int, int, int, int, int, int, int, int]:
    """Allocate and configure the four transport pipes as one bounded unit."""

    pairs: list[tuple[int, int]] = []
    opened: list[int] = []
    try:
        for _ in range(4):
            pair = os.pipe2(pipe_flags)
            pairs.append(pair)
            opened.extend(pair)
        for fd in (pairs[0][1], pairs[1][0], pairs[2][0], pairs[3][0]):
            os.set_blocking(fd, False)
        return (
            pairs[0][0], pairs[0][1], pairs[1][0], pairs[1][1],
            pairs[2][0], pairs[2][1], pairs[3][0], pairs[3][1],
        )
    except BaseException:
        for fd in opened:
            try:
                os.close(fd)
            except OSError:
                pass
        raise


def _rusage_dict(value: resource.struct_rusage | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "user_seconds": value.ru_utime,
        "system_seconds": value.ru_stime,
        "max_rss": value.ru_maxrss,
        "minor_faults": value.ru_minflt,
        "major_faults": value.ru_majflt,
        "involuntary_context_switches": value.ru_nivcsw,
        "voluntary_context_switches": value.ru_nvcsw,
    }


class ExactCandidateSession:
    """One traced candidate process and one bounded framed session.

    ``auto_launch`` is useful for tests and integration that need to mutate or
    revalidate the caller descriptor between construction and launch.  There
    is exactly one launch attempt; this class never retries.
    """

    def __init__(
        self,
        executable_fd: int,
        argv0: str,
        env: Mapping[str, str],
        cwd: str | int | None,
        expected_bytes: bytes | None = None,
        expected_sha256: str | None = None,
        frames: Sequence[bytes] | None = None,
        limits: ExactTransportLimits | None = None,
        *,
        expected_fp: fp.FPExpectation | Mapping[str, Any] | None = None,
        cwd_fd: int | None = None,
        expected_executable_bytes: bytes | None = None,
        expected_executable_sha256: str | None = None,
        auto_launch: bool = True,
    ) -> None:
        if not fp.is_supported_platform():
            raise ExactTransportError("unsupported-platform", "exact candidate transport requires Linux x86_64")
        if not isinstance(executable_fd, int) or isinstance(executable_fd, bool) or executable_fd < 0:
            raise ValueError("executable_fd must be a nonnegative open descriptor")
        self.executable_fd = executable_fd
        self.argv0 = _validate_argv0(argv0)
        self.env = _validate_environment(env)
        if expected_bytes is None:
            expected_bytes = expected_executable_bytes
        elif expected_executable_bytes is not None and expected_bytes != expected_executable_bytes:
            raise ExactTransportError("expected-content-ambiguous", "two different expected executable byte values were supplied")
        if expected_sha256 is None:
            expected_sha256 = expected_executable_sha256
        elif expected_executable_sha256 is not None and expected_sha256 != expected_executable_sha256:
            raise ExactTransportError("expected-hash-ambiguous", "two different expected executable hashes were supplied")
        self.expected_bytes, self.expected_sha256 = _validate_expected_content(expected_bytes, expected_sha256)
        self._cwd_fd_owned = False
        if cwd_fd is not None:
            if cwd is not None:
                raise ExactTransportError("cwd-descriptor-ambiguous", "supply either cwd path or cwd_fd, not both")
            if not isinstance(cwd_fd, int) or isinstance(cwd_fd, bool) or cwd_fd < 0:
                raise ExactTransportError("cwd-descriptor", "cwd_fd must be an open directory descriptor")
            self.cwd_fd = os.dup(cwd_fd)
            self._cwd_fd_owned = True
            self.cwd = None
        elif isinstance(cwd, int):
            self.cwd_fd = os.dup(cwd)
            self._cwd_fd_owned = True
            self.cwd = None
        elif isinstance(cwd, str):
            self.cwd = _validate_cwd(cwd)
            try:
                self.cwd_fd = os.open(self.cwd, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            except OSError as error:
                raise ExactTransportError("cwd-open", str(error)) from error
            self._cwd_fd_owned = True
        else:
            raise ExactTransportError("cwd-required", "cwd path or verified directory descriptor is required")
        try:
            self.cwd_pre = _directory_identity(self.cwd_fd)
        except BaseException:
            self._close_owned_cwd()
            raise
        try:
            self.limits = limits if limits is not None else ExactTransportLimits()
            if not isinstance(self.limits, ExactTransportLimits):
                raise TypeError("limits must be ExactTransportLimits")
        except BaseException:
            self._close_owned_cwd()
            raise
        try:
            if frames is None:
                self.frames: tuple[bytes, ...] = ()
            else:
                if not isinstance(frames, Sequence) or isinstance(frames, (str, bytes, bytearray)):
                    raise TypeError("frames must be a sequence of bytes")
                self.frames = tuple(self._prepare_frame(item, check_limit=True) for item in frames)
                if len(self.frames) > self.limits.max_frames:
                    raise ValueError("frames exceed the one-session frame limit")
        except BaseException:
            self._close_owned_cwd()
            raise
        try:
            if expected_fp is None:
                self.expected_fp = fp.FPExpectation()
            elif isinstance(expected_fp, fp.FPExpectation):
                self.expected_fp = expected_fp
            else:
                self.expected_fp = fp.FPExpectation.from_mapping(expected_fp)
        except BaseException:
            self._close_owned_cwd()
            raise
        try:
            self.descriptor_pre = _descriptor_identity(executable_fd)
            self.seals_initial = _descriptor_seals(executable_fd)
            self.content_initial = _read_fd_content(executable_fd)
        except BaseException:
            self._close_owned_cwd()
            raise
        if self.content_initial.size != len(self.expected_bytes) or self.content_initial.sha256 != self.expected_sha256:
            self._close_owned_cwd()
            raise ExactTransportError("descriptor-content-mismatch", "open executable bytes differ from expected custody bytes")
        self.descriptor_post_exe: DescriptorIdentity | None = None
        self.descriptor_post_fd: DescriptorIdentity | None = None
        self.content_pre_fork: ContentObservation | None = None
        self.content_post_exec: ContentObservation | None = None
        self.seals_pre_fork: int | None = None
        self.seals_post_exec: int | None = None
        self.cwd_post: DescriptorIdentity | None = None
        self.launch_result: LaunchResult | None = None
        self.pid: int | None = None
        self.process_group_id: int | None = None
        self._stdin_fd: int | None = None
        self._stdout_fd: int | None = None
        self._stderr_fd: int | None = None
        self._error_fd: int | None = None
        self._selector: selectors.BaseSelector | None = None
        self._stdout_buffer = bytearray()
        self._stderr = bytearray()
        self._stdout = bytearray()
        self._requests: list[bytes] = []
        self._responses: list[bytes] = []
        self._final_observation: fp.FPStateObservation | None = None
        self._final_inconclusive = False
        self._final_mismatch = False
        self._final_exit_stop_seen = False
        self._stdout_eof = False
        self._stderr_eof = False
        self._stdin_closed = False
        self._closed = False
        self._failure: ExactTransportError | None = None
        self._returncode: int | None = None
        self._exit_code: int | None = None
        self._term_signal: int | None = None
        self._rusage: Mapping[str, Any] | None = None
        self._wait_status_seen = False
        self._killed = False
        self._reaped = False
        self._clean_shutdown = False
        self._startup_error = b""
        self.attempt_count = 0
        if auto_launch:
            try:
                self.launch()
            except BaseException:
                self._close_owned_cwd()
                raise

    @classmethod
    def open(cls, *args: Any, **kwargs: Any) -> "ExactCandidateSession":
        return cls(*args, **kwargs)

    @property
    def failure(self) -> ExactTransportError | None:
        return self._failure

    @property
    def stdout(self) -> bytes:
        return bytes(self._stdout)

    @property
    def stderr(self) -> bytes:
        return bytes(self._stderr)

    @property
    def responses(self) -> tuple[bytes, ...]:
        return tuple(self._responses)

    @property
    def requests(self) -> tuple[bytes, ...]:
        return tuple(self._requests)

    @property
    def launch_observation(self) -> fp.FPStateObservation | None:
        return None if self.launch_result is None else self.launch_result.observation

    def _close_owned_cwd(self) -> None:
        if not getattr(self, "_cwd_fd_owned", False):
            return
        fd = getattr(self, "cwd_fd", None)
        self._cwd_fd_owned = False
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    def _drain_startup_error(self) -> None:
        fd = self._error_fd
        if fd is None:
            return
        while len(self._startup_error) < 4096:
            try:
                chunk = os.read(fd, 4096 - len(self._startup_error))
            except BlockingIOError:
                return
            except OSError:
                return
            if not chunk:
                return
            self._startup_error += chunk

    def _close_parent_fds(self) -> None:
        self._close_stdin()
        if self._selector is not None:
            try:
                self._selector.close()
            except Exception:
                pass
            self._selector = None
        for fd_name in ("_stdout_fd", "_stderr_fd", "_error_fd"):
            fd = getattr(self, fd_name, None)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_name, None)

    def _prepare_frame(self, frame: bytes, *, check_limit: bool) -> bytes:
        if not isinstance(frame, bytes):
            raise ExactTransportError("request-frame", "request frame must be bytes")
        if not frame.endswith(b"\n"):
            frame = frame + b"\n"
        if check_limit and len(frame) > self.limits.frame_bytes:
            raise ExactTransportError("request-frame-too-large", f"request frame exceeds {FRAME_BYTES} bytes")
        return frame

    def _launch_failure(self, status: str, code: str, detail: str, observation: fp.FPStateObservation | None = None) -> LaunchResult:
        self._record_failure(code, detail)
        if self.pid is None:
            # No child was created, so the lifecycle is terminal without a
            # reap obligation (and is represented as already settled).
            self._reaped = True
        self._abort_and_reap()
        self.launch_result = LaunchResult(
            status, code, detail, self.pid, observation, self.descriptor_pre,
            self.descriptor_post_exe, self.descriptor_post_fd, self.cwd_pre,
            self.cwd_post, self.content_initial, self.content_pre_fork,
            self.content_post_exec, self._startup_error, self.seals_initial,
            self.seals_pre_fork, self.seals_post_exec,
        )
        return self.launch_result

    def launch(self) -> LaunchResult:
        if self.launch_result is not None:
            return self.launch_result
        self.attempt_count += 1
        if self.attempt_count != 1:
            return self._launch_failure("failed", "retry-forbidden", "exact transport permits one launch only")
        try:
            current = _descriptor_identity(self.executable_fd)
        except ExactTransportError as error:
            return self._launch_failure("failed", "descriptor-substitution", error.detail)
        if current != self.descriptor_pre:
            return self._launch_failure("failed", "descriptor-substitution", "descriptor identity changed before launch")
        try:
            self.seals_pre_fork = _descriptor_seals(self.executable_fd)
        except ExactTransportError as error:
            return self._launch_failure("failed", "descriptor-not-sealed", error.detail)
        if self.seals_pre_fork != self.seals_initial:
            return self._launch_failure("failed", "descriptor-seals-mismatch", "executable sealing changed before fork")
        try:
            self.content_pre_fork = _read_fd_content(self.executable_fd)
        except ExactTransportError as error:
            return self._launch_failure("failed", error.code, error.detail)
        if self.content_pre_fork.size != len(self.expected_bytes) or self.content_pre_fork.sha256 != self.expected_sha256:
            return self._launch_failure("failed", "descriptor-content-mismatch", "executable content changed before fork")
        try:
            cwd_now = _directory_identity(self.cwd_fd)
        except ExactTransportError as error:
            return self._launch_failure("failed", error.code, error.detail)
        if cwd_now != self.cwd_pre:
            return self._launch_failure("failed", "cwd-identity-mismatch", "cwd directory identity changed before fork")
        pipe_flags = getattr(os, "O_CLOEXEC", 0)
        try:
            stdin_r, stdin_w, stdout_r, stdout_w, stderr_r, stderr_w, error_r, error_w = _allocate_transport_pipes(pipe_flags)
        except OSError as error:
            return self._launch_failure("inconclusive", "launch-failed", str(error))
        try:
            pid = os.fork()
        except OSError as error:
            for fd in (stdin_r, stdin_w, stdout_r, stdout_w, stderr_r, stderr_w, error_r, error_w):
                try:
                    os.close(fd)
                except OSError:
                    pass
            return self._launch_failure("failed", "fork-failed", str(error))
        if pid == 0:
            self._child_exec(stdin_r, stdin_w, stdout_r, stdout_w, stderr_r, stderr_w, error_r, error_w, self.cwd_fd)
            os._exit(127)
        self.pid = pid
        # Do not call getpgid immediately after fork: before the child reaches
        # its setsid() the PID still belongs to the caller's process group.
        # Recording that group and later killpg()'ing it could kill the
        # launcher itself.  The child is required to stop after setsid(), at
        # which point we obtain and verify the private PID group.
        self.process_group_id = None
        for fd in (stdin_r, stdout_w, stderr_w, error_w):
            try:
                os.close(fd)
            except OSError:
                pass
        self._stdin_fd, self._stdout_fd, self._stderr_fd, self._error_fd = stdin_w, stdout_r, stderr_r, error_r
        self._selector = selectors.DefaultSelector()
        self._selector.register(stdout_r, selectors.EVENT_READ, "stdout")
        self._selector.register(stderr_r, selectors.EVENT_READ, "stderr")
        try:
            initial = self._wait_for_status(time.monotonic() + self.limits.io_deadline_seconds)
            if initial is None or not os.WIFSTOPPED(initial) or os.WSTOPSIG(initial) != signal.SIGSTOP:
                return self._launch_failure("inconclusive", "tracee-start-stop-missing", "child did not reach its self-trace stop")
            try:
                self.process_group_id = os.getpgid(pid)
            except OSError as error:
                return self._launch_failure("inconclusive", "process-group", str(error))
            if self.process_group_id != pid:
                return self._launch_failure("failed", "process-group", "child did not create a private process group")
            fp.ptrace_set_options(pid)
            fp.ptrace_continue(pid)
            post_exec = self._wait_for_status(time.monotonic() + self.limits.io_deadline_seconds)
            if post_exec is None:
                return self._launch_failure("inconclusive", "exec-stop-missing", "post-exec ptrace stop was not observed")
            stop = fp.parse_wait_status(pid, post_exec)
            if not stop.is_exec_stop:
                return self._launch_failure(
                    "failed", "unexpected-ptrace-stop",
                    "tracee did not stop at the expected PTRACE_EVENT_EXEC trap",
                )
            self.descriptor_post_exe = self._stat_proc_descriptor("exe")
            self.descriptor_post_fd = self._stat_proc_descriptor(f"fd/{CHILD_EXEC_FD}")
            self.seals_post_exec = self._stat_proc_descriptor_seals(f"fd/{CHILD_EXEC_FD}")
            self.cwd_post = self._stat_proc_directory("cwd")
            self.content_post_exec = _read_fd_content(self.executable_fd)
            if self.descriptor_post_exe != self.descriptor_pre or self.descriptor_post_fd != self.descriptor_pre:
                return self._launch_failure("failed", "descriptor-identity-mismatch", "post-exec descriptor identity differs from prelaunch identity")
            if self.seals_post_exec != self.seals_initial:
                return self._launch_failure("failed", "descriptor-seals-mismatch", "post-exec descriptor seals differ from prelaunch seals")
            if self.cwd_post != self.cwd_pre:
                return self._launch_failure("failed", "cwd-identity-mismatch", "post-exec cwd identity differs from prelaunch identity")
            if self.content_post_exec.size != len(self.expected_bytes) or self.content_post_exec.sha256 != self.expected_sha256:
                return self._launch_failure("failed", "descriptor-content-race", "executable content changed before post-exec observation")
            observation = fp.observe_initial_fp_state(pid, expected=self.expected_fp)
            if observation.status != "observed":
                return self._launch_failure(observation.status, observation.code, observation.detail, observation)
            fp.ptrace_continue(pid)
            self.launch_result = LaunchResult(
                "observed", "observed", "post-exec FP state, descriptor content, cwd, and identity observed",
                pid, observation, self.descriptor_pre, self.descriptor_post_exe,
                self.descriptor_post_fd, self.cwd_pre, self.cwd_post,
                self.content_initial, self.content_pre_fork, self.content_post_exec,
                self._startup_error, self.seals_initial, self.seals_pre_fork,
                self.seals_post_exec,
            )
            return self.launch_result
        except fp.FPObserverError as error:
            return self._launch_failure("inconclusive", error.code, error.detail)
        except (OSError, ExactTransportError) as error:
            code = error.code if isinstance(error, ExactTransportError) else "launch-failed"
            detail = error.detail if isinstance(error, ExactTransportError) else str(error)
            return self._launch_failure("inconclusive", code, detail)

    def _child_exec(
        self,
        stdin_r: int,
        stdin_w: int,
        stdout_r: int,
        stdout_w: int,
        stderr_r: int,
        stderr_w: int,
        error_r: int,
        error_w: int,
        cwd_fd: int,
    ) -> None:
        """Child-only setup.  Every failure is reported then exits; no shell."""

        try:
            os.setsid()
            os.dup2(self.executable_fd, CHILD_EXEC_FD, inheritable=True)
            os.dup2(stdin_r, 0, inheritable=True)
            os.dup2(stdout_w, 1, inheritable=True)
            os.dup2(stderr_w, 2, inheritable=True)
            os.dup2(error_w, CHILD_ERROR_FD, inheritable=False)
            os.fchdir(cwd_fd)
            fp.ptrace_traceme()
            os.kill(os.getpid(), signal.SIGSTOP)
            # Close both ends of every parent-created pipe in the child.  In
            # particular, retaining stdin_w would keep the child's own stdin
            # pipe writable and make EOF/trailing-output shutdown impossible.
            for fd in (stdin_r, stdin_w, stdout_r, stdout_w, stderr_r, stderr_w, error_r, error_w, cwd_fd, self.executable_fd):
                if fd not in {0, 1, 2, CHILD_EXEC_FD, CHILD_ERROR_FD}:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            os.execve(CHILD_EXEC_FD, [self.argv0], self.env)
        except BaseException as error:
            detail = f"{type(error).__name__}: {error}".encode("utf-8", errors="replace")[:1024]
            try:
                os.write(CHILD_ERROR_FD, detail)
            except OSError:
                pass
            os._exit(127)

    def _stat_proc_descriptor(self, relative: str) -> DescriptorIdentity:
        if self.pid is None:
            raise ExactTransportError("pid-unavailable", "tracee PID is unavailable")
        path = f"/proc/{self.pid}/{relative}"
        try:
            value = os.stat(path)
        except OSError as error:
            raise ExactTransportError("descriptor-observation-unavailable", str(error)) from error
        return DescriptorIdentity.from_stat(value)

    def _stat_proc_descriptor_seals(self, relative: str) -> int:
        if self.pid is None:
            raise ExactTransportError("pid-unavailable", "tracee PID is unavailable")
        path = f"/proc/{self.pid}/{relative}"
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        except OSError as error:
            raise ExactTransportError("descriptor-seals-unavailable", str(error)) from error
        try:
            return _descriptor_seals(fd)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _stat_proc_directory(self, relative: str) -> DescriptorIdentity:
        value = self._stat_proc_descriptor(relative)
        return DescriptorIdentity(value.device, value.inode, value.mode, 0, 0)

    def _wait_for_status(self, deadline: float) -> int | None:
        if self.pid is None:
            return None
        while time.monotonic() < deadline:
            try:
                waited, status, usage = os.wait4(self.pid, os.WUNTRACED | os.WNOHANG)
            except ChildProcessError:
                self._reaped = True
                return None
            except OSError as error:
                if error.errno == errno.EINTR:
                    continue
                raise
            if waited:
                self._wait_status_seen = True
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    self._returncode, self._exit_code, self._term_signal = _status_to_exit(status)
                    self._rusage = _rusage_dict(usage)
                    self._reaped = True
                return status
            time.sleep(min(0.001, max(0.0, deadline - time.monotonic())))
        return None

    def _read_fd(self, fd: int, kind: str) -> None:
        while True:
            try:
                chunk = os.read(fd, 8192)
            except BlockingIOError:
                return
            except OSError as error:
                raise ExactTransportError(f"{kind}-read", str(error)) from error
            if not chunk:
                if kind == "stdout":
                    self._stdout_eof = True
                else:
                    self._stderr_eof = True
                if self._selector is not None:
                    try:
                        self._selector.unregister(fd)
                    except (KeyError, OSError):
                        pass
                return
            if kind == "stdout":
                if len(self._stdout) + len(chunk) > self.limits.stdout_total_bytes:
                    raise ExactTransportError("stdout-cap", "candidate aggregate stdout cap exceeded")
                self._stdout.extend(chunk)
                self._stdout_buffer.extend(chunk)
                newline = self._stdout_buffer.find(b"\n")
                if newline < 0 and len(self._stdout_buffer) > self.limits.frame_bytes:
                    raise ExactTransportError("response-frame-too-large", f"candidate frame exceeds {FRAME_BYTES} bytes")
                if newline >= 0 and newline + 1 > self.limits.frame_bytes:
                    raise ExactTransportError("response-frame-too-large", f"candidate frame exceeds {FRAME_BYTES} bytes")
            else:
                if len(self._stderr) + len(chunk) > self.limits.stderr_total_bytes:
                    raise ExactTransportError("stderr-cap", "candidate aggregate stderr cap exceeded")
                self._stderr.extend(chunk)

    def _pump(self, deadline: float, pending: bytearray | None = None) -> None:
        if self._selector is None:
            raise ExactTransportError("selector-unavailable", "transport selector is unavailable")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ExactTransportError("io-timeout", "candidate I/O deadline exceeded")
        if pending and self._stdin_fd is not None and not self._stdin_closed:
            try:
                self._selector.register(self._stdin_fd, selectors.EVENT_WRITE, "stdin")
            except KeyError:
                pass
            except OSError as error:
                raise ExactTransportError("stdin-register", str(error)) from error
        for key, _ in self._selector.select(min(remaining, 0.05)):
            if key.data == "stdout":
                self._read_fd(self._stdout_fd, "stdout")  # type: ignore[arg-type]
            elif key.data == "stderr":
                self._read_fd(self._stderr_fd, "stderr")  # type: ignore[arg-type]
            elif key.data == "stdin" and pending is not None and self._stdin_fd is not None:
                try:
                    written = os.write(self._stdin_fd, pending)
                except BlockingIOError:
                    written = 0
                except BrokenPipeError as error:
                    raise ExactTransportError("stdin-write", "candidate closed stdin") from error
                except OSError as error:
                    raise ExactTransportError("stdin-write", str(error)) from error
                if written:
                    del pending[:written]
                if not pending:
                    try:
                        self._selector.unregister(self._stdin_fd)
                    except (KeyError, OSError):
                        pass

    def _observe_final_fp_state(self) -> ExactTransportError | None:
        if self._final_observation is not None:
            return None
        if self.pid is None or self.launch_result is None or not self.launch_result.observed:
            self._final_inconclusive = True
            return ExactTransportError("final-fp-observation-unavailable", "initial FP observation was not usable")
        observation = fp.observe_initial_fp_state(self.pid, expected=self.expected_fp)
        self._final_observation = observation
        if observation.status != "observed":
            if observation.status == "failed":
                self._final_mismatch = True
                return ExactTransportError("final-fp-state-mismatch", observation.detail)
            self._final_inconclusive = True
            return ExactTransportError("final-fp-observation-unavailable", observation.detail)
        initial = self.launch_result.observation
        if initial is None or not initial.usable:
            self._final_inconclusive = True
            return ExactTransportError("final-fp-observation-unavailable", "initial FP observation was not usable")
        drift: list[str] = []
        for field in (
            "x87_rounding_mode", "mxcsr_rounding_mode", "ftz", "daz",
            "x87_control_word", "mxcsr", "x87_exception_masks", "mxcsr_exception_masks",
        ):
            if getattr(self.expected_fp, field) is None:
                continue
            before = getattr(initial, field)
            after = getattr(observation, field)
            if before != after:
                drift.append(f"{field} changed from {before!r} to {after!r}")
        if drift:
            self._final_mismatch = True
            return ExactTransportError("final-fp-state-drift", "; ".join(drift))
        return None

    def _handle_ptrace_stop(self, status: int) -> None:
        if self.pid is None or not os.WIFSTOPPED(status):
            return
        stop = fp.parse_wait_status(self.pid, status)
        if stop.signal == signal.SIGTRAP and stop.event == fp.PTRACE_EVENT_EXIT:
            if self._final_exit_stop_seen:
                self._continue_terminal_stop_for_abort(status, record_error=False)
                raise ExactTransportError("duplicate-final-fp-observation", "tracee produced more than one PTRACE_EVENT_EXIT stop")
            self._final_exit_stop_seen = True
            problem = self._observe_final_fp_state()
            try:
                fp.ptrace_continue(self.pid, 0)
            except fp.FPObserverError as error:
                raise ExactTransportError(error.code, error.detail) from error
            if problem is not None:
                self._record_failure(problem.code, problem.detail)
            return
        if stop.signal == signal.SIGCHLD and stop.event == 0:
            try:
                fp.ptrace_continue(self.pid, 0)
            except fp.FPObserverError as error:
                raise ExactTransportError(error.code, error.detail) from error
            return
        raise ExactTransportError(
            "unexpected-ptrace-stop",
            f"tracee stopped with signal {stop.signal} and event {stop.event} after launch",
        )

    def _continue_terminal_stop_for_abort(self, status: int, *, record_error: bool = True) -> None:
        """Release an already-terminal ptrace stop during bounded cleanup."""

        if self.pid is None or not os.WIFSTOPPED(status):
            return
        stop = fp.parse_wait_status(self.pid, status)
        if stop.signal != signal.SIGTRAP or stop.event != fp.PTRACE_EVENT_EXIT:
            return
        try:
            fp.ptrace_continue(self.pid, 0)
        except fp.FPObserverError as error:
            # Cleanup must retain the original failure, but this diagnostic
            # still participates in the bounded lifecycle result if it was
            # the only failure observed.
            if record_error:
                self._record_failure(error.code, error.detail)

    def _poll_terminal(self, *, wait_seconds: float = 0.000001) -> None:
        """Consume a terminal wait status without blocking on pipe progress."""

        if self.pid is None or self._reaped:
            return
        status = self._wait_for_status(time.monotonic() + max(0.0, wait_seconds))
        if status is not None and os.WIFSTOPPED(status):
            self._handle_ptrace_stop(status)

    def _abort_and_reap(self) -> None:
        if self.pid is None:
            self._drain_startup_error()
            self._close_parent_fds()
            self._close_owned_cwd()
            return
        self._kill_process_group()
        deadline = time.monotonic() + min(self.limits.shutdown_deadline_seconds, 1.0)
        while not self._reaped and time.monotonic() < deadline:
            status = self._wait_for_status(deadline)
            if status is not None and self._reaped:
                break
            if status is not None and os.WIFSTOPPED(status):
                try:
                    self._handle_ptrace_stop(status)
                except ExactTransportError as error:
                    self._record_failure(error.code, error.detail)
                    self._continue_terminal_stop_for_abort(status)
                    self._kill_process_group()
            time.sleep(0.001)
        if not self._reaped:
            # A traced child that did not report a terminal status is not
            # allowed to survive a failed exact attempt, but the reaper must
            # not block indefinitely waiting for a kernel lifecycle event.
            # Preserve ``reaped=False`` if bounded polling cannot observe it.
            kill_deadline = time.monotonic() + min(self.limits.shutdown_deadline_seconds, 1.0)
            self._kill_process_group()
            while not self._reaped and time.monotonic() < kill_deadline:
                status = self._wait_for_status(kill_deadline)
                if status is not None and self._reaped:
                    break
                if status is not None and os.WIFSTOPPED(status):
                    try:
                        self._handle_ptrace_stop(status)
                    except ExactTransportError as error:
                        self._record_failure(error.code, error.detail)
                        self._continue_terminal_stop_for_abort(status)
                        self._kill_process_group()
                time.sleep(0.001)
        self._drain_startup_error()
        self._close_parent_fds()
        self._close_owned_cwd()

    def _kill_process_group(self) -> None:
        # A group ID is safe to signal only after the post-setsid stop check;
        # retaining the pid equality guard also protects early fork failures.
        if self.process_group_id is not None and self.process_group_id == self.pid:
            try:
                os.killpg(self.process_group_id, signal.SIGKILL)
                self._killed = True
            except ProcessLookupError:
                pass
            except OSError:
                pass
        if self.pid is not None and not self._reaped:
            try:
                os.kill(self.pid, signal.SIGKILL)
                self._killed = True
            except OSError:
                pass

    def _record_failure(self, code: str, detail: str) -> None:
        if self._failure is None:
            self._failure = ExactTransportError(code, detail)

    def _response_request_id(self, response: bytes) -> str:
        value = _strict_object(response.rstrip(b"\n"), "response")
        return _validate_request_id(value.get("request_id"), "response-request-id")

    def _request_id(self, frame: bytes) -> str:
        value = _strict_object(frame.rstrip(b"\n"), "request")
        return _validate_request_id(value.get("request_id"), "request-id")

    def request_frame(self, frame: bytes, request_id: str | None = None) -> bytes:
        """Send one exact frame and return one exact correlated response frame."""

        if self.launch_result is None:
            self.launch()
        if self._closed:
            raise ExactTransportError("session-closed", "candidate session is closed")
        if self._failure is not None:
            raise self._failure
        if self.launch_result is None or not self.launch_result.observed:
            raise ExactTransportError("candidate-not-observed", "candidate was not admitted after external FP observation")
        if len(self._requests) >= self.limits.max_frames:
            self._record_failure("request-limit", "one-session frame limit exceeded")
            self._abort_and_reap()
            raise self._failure  # type: ignore[misc]
        try:
            wire = self._prepare_frame(frame, check_limit=True)
            body_id = self._request_id(wire)
            if request_id is None:
                expected_id = body_id
            else:
                expected_id = _validate_request_id(request_id, "request-id")
                if expected_id != body_id:
                    raise ExactTransportError("request-id-mismatch", "explicit request_id differs from the request body ID")
        except ExactTransportError as error:
            self._record_failure(error.code, error.detail)
            self._abort_and_reap()
            raise
        if self._stdout_buffer:
            self._record_failure("trailing-output", "candidate emitted output before the next request")
            self._abort_and_reap()
            raise self._failure  # type: ignore[misc]
        self._requests.append(wire)
        pending = bytearray(wire)
        deadline = time.monotonic() + self.limits.io_deadline_seconds
        try:
            while pending:
                self._pump(deadline, pending)
                self._poll_terminal(wait_seconds=TERMINAL_POLL_SECONDS)
                if self._reaped and not self._stdout_buffer:
                    # Exit and pipe publication are separate kernel events;
                    # drain once after observing exit so queued response bytes
                    # retain precedence over the early-exit classification.
                    if time.monotonic() < deadline:
                        self._pump(deadline)
                    if not self._stdout_buffer:
                        raise ExactTransportError("candidate-exited", "candidate exited before response")
            while b"\n" not in self._stdout_buffer:
                self._pump(deadline)
                self._poll_terminal(wait_seconds=TERMINAL_POLL_SECONDS)
                if self._reaped and b"\n" not in self._stdout_buffer:
                    if time.monotonic() < deadline:
                        self._pump(deadline)
                    if b"\n" not in self._stdout_buffer:
                        raise ExactTransportError("candidate-exited", "candidate exited before response")
            newline = self._stdout_buffer.index(b"\n") + 1
            response = bytes(self._stdout_buffer[:newline])
            del self._stdout_buffer[:newline]
            self._responses.append(response)
            actual_id = self._response_request_id(response)
            if actual_id != expected_id:
                raise ExactTransportError("response-request-id-mismatch", "response request_id differs from request")
            quiet_deadline = min(deadline, time.monotonic() + self.limits.trailing_output_quiet_seconds)
            while time.monotonic() < quiet_deadline:
                self._pump(quiet_deadline)
                if self._stdout_buffer:
                    raise ExactTransportError("extra-output", "candidate emitted an extra or trailing frame")
                if self._reaped and self._stdout_eof:
                    break
            return response
        except ExactTransportError as error:
            self._record_failure(error.code, error.detail)
            self._abort_and_reap()
            raise

    request = request_frame

    def run(self, frames: Sequence[bytes] | None = None) -> ExactTransportResult:
        """Run the supplied ordered frames once and return retained results."""

        try:
            if frames is None:
                selected = self.frames
            elif isinstance(frames, (str, bytes, bytearray)) or not isinstance(frames, Sequence):
                raise ExactTransportError("frames-sequence", "run frames must be a sequence of bytes")
            else:
                selected = tuple(self._prepare_frame(item, check_limit=True) for item in frames)
            if not selected:
                raise ExactTransportError("frames-empty", "run requires at least one request frame")
            if len(selected) > self.limits.max_frames:
                raise ExactTransportError("request-limit", "run frames exceed the one-session frame limit")
        except ExactTransportError as error:
            self._record_failure(error.code, error.detail)
            self._abort_and_reap()
            return self.close()
        try:
            for frame in selected:
                self.request_frame(frame)
        except ExactTransportError:
            pass
        return self.close()

    def _close_stdin(self) -> None:
        if self._stdin_closed:
            return
        self._stdin_closed = True
        if self._stdin_fd is None:
            return
        if self._selector is not None:
            try:
                self._selector.unregister(self._stdin_fd)
            except (KeyError, OSError):
                pass
        try:
            os.close(self._stdin_fd)
        except OSError:
            pass

    def close(self) -> ExactTransportResult:
        if self._closed:
            return self._result()
        self._closed = True
        if self.pid is not None and self._failure is None:
            self._close_stdin()
            deadline = time.monotonic() + self.limits.shutdown_deadline_seconds
            try:
                while not self._reaped and time.monotonic() < deadline:
                    self._pump(deadline)
                    self._poll_terminal(wait_seconds=TERMINAL_POLL_SECONDS)
                while (not self._stdout_eof or not self._stderr_eof) and time.monotonic() < deadline:
                    self._pump(deadline)
                    self._poll_terminal(wait_seconds=TERMINAL_POLL_SECONDS)
                if self._reaped and (not self._stdout_eof or not self._stderr_eof):
                    # A terminal wait can win the race with pipe HUP delivery.
                    # Once the child is already a zombie, allow one short,
                    # bounded drain window for the kernel to publish EOF; no
                    # candidate work can continue in this window.
                    drain_deadline = min(deadline + 0.25, time.monotonic() + 0.25)
                    while (not self._stdout_eof or not self._stderr_eof) and time.monotonic() < drain_deadline:
                        self._pump(drain_deadline)
                        self._poll_terminal(wait_seconds=TERMINAL_POLL_SECONDS)
                if not self._reaped or not self._stdout_eof or not self._stderr_eof:
                    raise ExactTransportError("shutdown-timeout", "candidate shutdown deadline exceeded")
                if self._stdout_buffer:
                    raise ExactTransportError("trailing-output", "candidate emitted trailing stdout")
                if self._returncode not in (None, 0):
                    raise ExactTransportError("candidate-exit", f"candidate exited with status {self._returncode}")
                # A clean terminal lifecycle is not sufficient evidence for
                # support: exactly one exit-stop xstate observation must have
                # been retained while the tracee was stopped.  If the exit
                # event was unavailable/missed, retain the clean reap and
                # bytes but classify the session as inconclusive.
                if self._final_observation is None:
                    self._final_inconclusive = True
                    self._record_failure(
                        "final-fp-observation-unavailable",
                        "normal exit completed without a PTRACE_EVENT_EXIT FP observation",
                    )
                    self._clean_shutdown = True
                elif self._final_observation.status != "observed":
                    if self._final_observation.status == "failed":
                        self._final_mismatch = True
                        self._record_failure("final-fp-state-mismatch", self._final_observation.detail)
                    else:
                        self._final_inconclusive = True
                        self._record_failure(
                            "final-fp-observation-unavailable", self._final_observation.detail,
                        )
                        self._clean_shutdown = True
                elif self._failure is None:
                    self._clean_shutdown = True
            except ExactTransportError as error:
                self._record_failure(error.code, error.detail)
                self._abort_and_reap()
        elif self._failure is not None:
            self._abort_and_reap()
        if (
            self._final_inconclusive
            and self._failure is not None
            and self._failure.code == "final-fp-observation-unavailable"
            and self._reaped
            and self._stdout_eof
            and self._stderr_eof
            and not self._stdout_buffer
            and self._returncode == 0
        ):
            # Final evidence can be discovered during request-time quiet
            # polling, before close() enters its normal branch.  Preserve the
            # clean process/pipe lifecycle even though support is inconclusive.
            self._clean_shutdown = True
        self._drain_startup_error()
        self._close_parent_fds()
        self._close_owned_cwd()
        return self._result()

    def _result(self) -> ExactTransportResult:
        launch = self.launch_result or LaunchResult(
            "inconclusive", "not-launched", "candidate was not launched", self.pid,
            None, getattr(self, "descriptor_pre", None), self.descriptor_post_exe,
            self.descriptor_post_fd, getattr(self, "cwd_pre", None), self.cwd_post,
            getattr(self, "content_initial", None), self.content_pre_fork,
            self.content_post_exec, self._startup_error,
            getattr(self, "seals_initial", None), getattr(self, "seals_pre_fork", None),
            getattr(self, "seals_post_exec", None),
        )
        if self._final_inconclusive and self._failure is not None and self._failure.code == "final-fp-observation-unavailable":
            status = "inconclusive"
        elif launch.status == "inconclusive" and self._failure is not None and self._failure.code == launch.code:
            status = "inconclusive"
        elif self._failure is not None:
            status = "failed"
        else:
            status = "supported" if self._clean_shutdown else launch.status
        return ExactTransportResult(
            status=status,
            code=None if self._failure is None else self._failure.code,
            detail=None if self._failure is None else self._failure.detail,
            launch=launch,
            final_observation=self._final_observation,
            returncode=self._returncode,
            exit_code=self._exit_code,
            term_signal=self._term_signal,
            requests=tuple(self._requests),
            responses=tuple(self._responses),
            stdout=bytes(self._stdout),
            stderr=bytes(self._stderr),
            trailing_stdout=bytes(self._stdout_buffer),
            request_sha256=tuple(_hash(item) for item in self._requests),
            response_sha256=tuple(_hash(item) for item in self._responses),
            stdout_sha256=_hash(bytes(self._stdout)),
            stderr_sha256=_hash(bytes(self._stderr)),
            request_count=len(self._requests),
            response_count=len(self._responses),
            process_group_id=self.process_group_id,
            reaped=self._reaped,
            killed=self._killed,
            clean_shutdown=self._clean_shutdown,
            partial=(len(self._responses) < len(self._requests)) or bool(self._stdout_buffer),
            attempt_count=self.attempt_count,
            rusage=self._rusage,
            startup_error=self._startup_error,
        )

    def __enter__(self) -> "ExactCandidateSession":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        result = self.close()
        if exc_type is None and result.status == "failed":
            raise ExactTransportError(result.code or "session-failed", result.detail or "exact session failed")
        return False


# Descriptive aliases for callers that prefer the transport-oriented name.
BoundedExactTransport = ExactCandidateSession
ExactTransportSession = ExactCandidateSession


__all__ = [
    "BoundedExactTransport", "CHILD_EXEC_FD", "ContentObservation", "DescriptorIdentity", "ExactCandidateSession",
    "ExactTransportError", "ExactTransportLimits", "ExactTransportResult", "ExactTransportSession",
    "F_ADD_SEALS", "F_SEAL_GROW", "F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_WRITE",
    "FRAME_BYTES", "IO_DEADLINE_SECONDS", "MAX_REQUEST_ID_BYTES", "MAX_SESSION_FRAMES",
    "REQUIRED_MEMFD_SEALS", "STDERR_TOTAL_CAP", "STDOUT_TOTAL_CAP", "TRAILING_OUTPUT_QUIET_SECONDS",
]

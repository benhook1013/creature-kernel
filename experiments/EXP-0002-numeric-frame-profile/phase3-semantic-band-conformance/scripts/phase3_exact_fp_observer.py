"""External initial floating-point-state observation for the Phase 3 launcher.

This module deliberately contains no candidate-specific code.  On Linux
x86_64 the tracer reads the stopped tracee's x86 XSAVE image through
``PTRACE_GETREGSET`` and ``NT_X86_XSTATE``.  The legacy FXSAVE portion of that
image has the x87 control word at byte 0 and MXCSR at byte 24.  Those offsets
are the Linux x86_64 ptrace register ABI (``ptrace(2)`` and
``include/uapi/linux/elf.h``); the FXSAVE layout is also specified by Intel's
Software Developer's Manual, Vol. 1, ``FXSAVE``.

No value returned by this module should be used as evidence unless ``status``
is ``"observed"`` and the caller has checked the expected-state policy.  A
tracee must already be stopped by ptrace when :func:`observe_fp_state` is
called.  The helper does not resume it; this makes a failed observation
fail-closed at the launcher boundary.
"""

from __future__ import annotations

import ctypes
import errno
import os
import platform
import signal
import sys
from dataclasses import dataclass
from typing import Any, Mapping


PTRACE_TRACEME = 0
PTRACE_CONT = 7
PTRACE_SETOPTIONS = 0x4200
PTRACE_GETREGSET = 0x4204
PTRACE_O_TRACEEXEC = 1 << 4
PTRACE_O_EXITKILL = 1 << 20
PTRACE_EVENT_EXEC = 4
NT_X86_XSTATE = 0x202
MAX_XSTATE_BYTES = 64 * 1024
X87_CONTROL_WORD_OFFSET = 0
MXCSR_OFFSET = 24
MIN_XSTATE_BYTES = MXCSR_OFFSET + 4

_ROUNDING_NAMES = {
    0: "nearest",
    1: "downward",
    2: "upward",
    3: "toward-zero",
}


class FPObserverError(RuntimeError):
    """A low-level observer error with a stable machine-facing code."""

    def __init__(self, code: str, detail: str, err: int | None = None) -> None:
        self.code = code
        self.detail = detail
        self.errno = err
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class FPExpectation:
    """The externally supplied initial-state admission policy.

    ``None`` fields are intentionally unconstrained.  The Phase 3 default
    checks only the controls that are part of the proposed numeric profile:
    nearest rounding, no FTZ, and no DAZ.  A caller may additionally bind raw
    control words or exception masks when its platform profile requires it.
    """

    x87_rounding_mode: str | None = "nearest"
    mxcsr_rounding_mode: str | None = "nearest"
    ftz: bool | None = False
    daz: bool | None = False
    x87_control_word: int | None = None
    mxcsr: int | None = None
    x87_exception_masks: int | None = None
    mxcsr_exception_masks: int | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("x87_rounding_mode", self.x87_rounding_mode),
            ("mxcsr_rounding_mode", self.mxcsr_rounding_mode),
        ):
            if value is not None and value not in _ROUNDING_NAMES.values():
                raise ValueError(f"{label} is not a supported rounding-mode name")
        for label, value, maximum in (
            ("x87_control_word", self.x87_control_word, 0xFFFF),
            ("mxcsr", self.mxcsr, 0xFFFFFFFF),
            ("x87_exception_masks", self.x87_exception_masks, 0x3F),
            ("mxcsr_exception_masks", self.mxcsr_exception_masks, 0x3F),
        ):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > maximum):
                raise ValueError(f"{label} is outside its unsigned register range")
        for label, value in (("ftz", self.ftz), ("daz", self.daz)):
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{label} must be bool or None")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FPExpectation":
        if not isinstance(value, Mapping):
            raise TypeError("FP expectation must be a mapping or FPExpectation")
        allowed = {
            "x87_rounding_mode", "mxcsr_rounding_mode", "fe_rounding",
            "ftz", "daz", "x87_control_word", "mxcsr",
            "x87_exception_masks", "mxcsr_exception_masks",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown FP expectation fields: {sorted(unknown)!r}")
        mode = value.get("fe_rounding")
        x87_mode = value.get("x87_rounding_mode", mode)
        mxcsr_mode = value.get("mxcsr_rounding_mode", mode)
        return cls(
            x87_rounding_mode=x87_mode,
            mxcsr_rounding_mode=mxcsr_mode,
            ftz=value.get("ftz", False),
            daz=value.get("daz", False),
            x87_control_word=value.get("x87_control_word"),
            mxcsr=value.get("mxcsr"),
            x87_exception_masks=value.get("x87_exception_masks"),
            mxcsr_exception_masks=value.get("mxcsr_exception_masks"),
        )


@dataclass(frozen=True)
class FPStateObservation:
    """Bounded raw/decoded register observation.

    ``status`` is one of ``observed``, ``failed`` (a concrete mismatch), or
    ``inconclusive`` (the register interface was unavailable or malformed).
    ``raw_xstate`` is retained only for a successful bounded read.
    """

    status: str
    code: str
    detail: str
    pid: int
    raw_xstate: bytes = b""
    x87_control_word: int | None = None
    mxcsr: int | None = None
    x87_rounding_mode: str | None = None
    mxcsr_rounding_mode: str | None = None
    x87_exception_masks: int | None = None
    mxcsr_exception_masks: int | None = None
    x87_flags: int | None = None
    mxcsr_flags: int | None = None
    ftz: bool | None = None
    daz: bool | None = None
    stopped: bool = True
    expected: FPExpectation | None = None

    def __post_init__(self) -> None:
        if self.status not in {"observed", "failed", "inconclusive"}:
            raise ValueError("invalid FP observation status")

    @property
    def usable(self) -> bool:
        return self.status == "observed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
            "pid": self.pid,
            "raw_xstate_hex": self.raw_xstate.hex(),
            "x87_control_word": None if self.x87_control_word is None else f"0x{self.x87_control_word:04x}",
            "mxcsr": None if self.mxcsr is None else f"0x{self.mxcsr:08x}",
            "x87_rounding_mode": self.x87_rounding_mode,
            "mxcsr_rounding_mode": self.mxcsr_rounding_mode,
            "x87_exception_masks": self.x87_exception_masks,
            "mxcsr_exception_masks": self.mxcsr_exception_masks,
            "x87_flags": self.x87_flags,
            "mxcsr_flags": self.mxcsr_flags,
            "ftz": self.ftz,
            "daz": self.daz,
            "stopped": self.stopped,
        }


@dataclass(frozen=True)
class PtraceStop:
    pid: int
    status: int
    signal: int
    event: int
    exit_code: int | None = None
    term_signal: int | None = None

    @property
    def is_exec_stop(self) -> bool:
        return signal.SIGTRAP == self.signal and self.event == PTRACE_EVENT_EXEC


def is_supported_platform() -> bool:
    """Return whether this exact register ABI is available."""

    return sys.platform.startswith("linux") and platform.machine().lower() in {"x86_64", "amd64"}


def _libc() -> ctypes.CDLL:
    if not is_supported_platform():
        raise FPObserverError("unsupported-platform", "initial FP observation requires Linux x86_64")
    try:
        return ctypes.CDLL(None, use_errno=True)
    except OSError as error:
        raise FPObserverError("ptrace-unavailable", str(error), getattr(error, "errno", None)) from error


def _ptrace(request: int, pid: int, address: int = 0, data: Any = None) -> int:
    libc = _libc()
    function = libc.ptrace
    # ``pid_t`` is a C int on Linux; ctypes has no c_pid_t alias.
    function.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
    function.restype = ctypes.c_long
    address_arg = ctypes.c_void_p(address)
    if data is None:
        data_arg = ctypes.c_void_p(0)
    elif isinstance(data, int):
        data_arg = ctypes.c_void_p(data)
    else:
        data_arg = ctypes.cast(data, ctypes.c_void_p)
    ctypes.set_errno(0)
    result = int(function(request, pid, address_arg, data_arg))
    if result == -1:
        err = ctypes.get_errno()
        raise FPObserverError("ptrace-failed", os.strerror(err), err)
    return result


def ptrace_traceme() -> None:
    """Mark the calling child for its parent and fail rather than continue."""

    _ptrace(PTRACE_TRACEME, 0)


def ptrace_set_options(pid: int, options: int = PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL) -> None:
    _ptrace(PTRACE_SETOPTIONS, pid, 0, options)


def ptrace_continue(pid: int, delivery_signal: int = 0) -> None:
    if delivery_signal < 0 or delivery_signal > signal.NSIG:
        raise ValueError("invalid signal for ptrace continue")
    _ptrace(PTRACE_CONT, pid, 0, delivery_signal)


def _decode_xstate(raw: bytes, pid: int, expected: FPExpectation | None) -> FPStateObservation:
    if len(raw) < MIN_XSTATE_BYTES:
        return FPStateObservation("inconclusive", "malformed-xstate", "kernel returned too few xstate bytes", pid, expected=expected)
    x87 = int.from_bytes(raw[X87_CONTROL_WORD_OFFSET:X87_CONTROL_WORD_OFFSET + 2], "little")
    mxcsr = int.from_bytes(raw[MXCSR_OFFSET:MXCSR_OFFSET + 4], "little")
    x87_rc = (x87 >> 10) & 0x3
    mxcsr_rc = (mxcsr >> 13) & 0x3
    fields = {
        "x87_control_word": x87,
        "mxcsr": mxcsr,
        "x87_rounding_mode": _ROUNDING_NAMES.get(x87_rc),
        "mxcsr_rounding_mode": _ROUNDING_NAMES.get(mxcsr_rc),
        "x87_exception_masks": x87 & 0x3F,
        "mxcsr_exception_masks": (mxcsr >> 7) & 0x3F,
        "x87_flags": None,
        "mxcsr_flags": mxcsr & 0x3F,
        "ftz": bool(mxcsr & (1 << 15)),
        "daz": bool(mxcsr & (1 << 6)),
    }
    if expected is not None:
        mismatch: list[str] = []
        for key in (
            "x87_rounding_mode", "mxcsr_rounding_mode", "ftz", "daz",
            "x87_control_word", "mxcsr", "x87_exception_masks", "mxcsr_exception_masks",
        ):
            wanted = getattr(expected, key)
            if wanted is not None and fields[key] != wanted:
                mismatch.append(f"{key} expected {wanted!r}, observed {fields[key]!r}")
        status = "failed" if mismatch else "observed"
        code = "fp-state-mismatch" if mismatch else "observed"
        detail = "; ".join(mismatch) if mismatch else "initial x87/MXCSR state matched the admission policy"
    else:
        status, code, detail = "observed", "observed", "initial x87/MXCSR state read"
    return FPStateObservation(
        status=status,
        code=code,
        detail=detail,
        pid=pid,
        raw_xstate=bytes(raw),
        expected=expected,
        **fields,
    )


def observe_fp_state(pid: int, *, expected: FPExpectation | Mapping[str, Any] | None = None) -> FPStateObservation:
    """Read a stopped tracee's x87 control word and MXCSR.

    The tracee remains stopped regardless of the return status.  Callers must
    explicitly resume only an ``observed`` result after all launch identity
    checks have passed.
    """

    if not is_supported_platform():
        return FPStateObservation("inconclusive", "unsupported-platform", "initial FP observation requires Linux x86_64", int(pid), stopped=False)
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        pid_value = pid if isinstance(pid, int) and not isinstance(pid, bool) else -1
        return FPStateObservation("inconclusive", "invalid-pid", "tracee PID must be positive", pid_value, stopped=False)
    try:
        policy = None if expected is None else (expected if isinstance(expected, FPExpectation) else FPExpectation.from_mapping(expected))
    except (TypeError, ValueError) as error:
        return FPStateObservation("inconclusive", "invalid-expectation", str(error), pid)
    buffer = ctypes.create_string_buffer(MAX_XSTATE_BYTES)
    iov = _IOVec(ctypes.cast(buffer, ctypes.c_void_p), MAX_XSTATE_BYTES)
    try:
        _ptrace(PTRACE_GETREGSET, pid, NT_X86_XSTATE, ctypes.byref(iov))
    except FPObserverError as error:
        return FPStateObservation("inconclusive", "register-read-unavailable", error.detail, pid, expected=policy)
    length = int(iov.iov_len)
    if length < MIN_XSTATE_BYTES or length > MAX_XSTATE_BYTES:
        return FPStateObservation("inconclusive", "malformed-xstate", f"kernel returned invalid xstate length {length}", pid, expected=policy)
    return _decode_xstate(buffer.raw[:length], pid, policy)


class _IOVec(ctypes.Structure):
    _fields_ = [("iov_base", ctypes.c_void_p), ("iov_len", ctypes.c_size_t)]


def observe_initial_fp_state(pid: int, *, expected: FPExpectation | Mapping[str, Any] | None = None) -> FPStateObservation:
    """Named alias used by the exact transport's post-exec admission step."""

    return observe_fp_state(pid, expected=expected)


def parse_wait_status(pid: int, status: int) -> PtraceStop:
    if os.WIFSTOPPED(status):
        return PtraceStop(pid, status, os.WSTOPSIG(status), status >> 16)
    if os.WIFEXITED(status):
        return PtraceStop(pid, status, 0, 0, exit_code=os.WEXITSTATUS(status))
    if os.WIFSIGNALED(status):
        return PtraceStop(pid, status, 0, 0, term_signal=os.WTERMSIG(status))
    return PtraceStop(pid, status, 0, 0)


__all__ = [
    "FPExpectation", "FPObserverError", "FPStateObservation", "MAX_XSTATE_BYTES",
    "MIN_XSTATE_BYTES", "NT_X86_XSTATE", "PTRACE_EVENT_EXEC", "PTRACE_O_EXITKILL",
    "PTRACE_O_TRACEEXEC", "PtraceStop", "is_supported_platform", "observe_fp_state",
    "observe_initial_fp_state", "parse_wait_status", "ptrace_continue", "ptrace_set_options",
    "ptrace_traceme",
]

"""Bounded subprocess/JSONL transport for the non-authoritative phase-two runner."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from phase2_common import (
    FRAME_BYTES,
    IO_DEADLINE_SECONDS,
    REQUEST_PROTOCOL_ID,
    SHUTDOWN_DEADLINE_SECONDS,
    STDERR_TOTAL_CAP,
    STDOUT_TOTAL_CAP,
    TRAILING_OUTPUT_QUIET_SECONDS,
    Phase2ProtocolError,
    frame_json,
    validate_request_frame,
    validate_response_frame,
)


class Phase2TransportError(Phase2ProtocolError):
    """A subprocess, pipe, deadline, or output-boundary failure."""


@dataclass(frozen=True)
class CloseResult:
    returncode: int | None
    trailing_stdout: bytes
    stderr: bytes
    failure: str | None


class BoundedSubprocessSession:
    """One persistent candidate process with bounded concurrent pipe drains."""

    def __init__(
        self,
        command: Sequence[str],
        cwd: str | None = None,
        *,
        io_deadline_seconds: float = IO_DEADLINE_SECONDS,
        shutdown_deadline_seconds: float = SHUTDOWN_DEADLINE_SECONDS,
        trailing_output_quiet_seconds: float = TRAILING_OUTPUT_QUIET_SECONDS,
        stdout_cap: int = STDOUT_TOTAL_CAP,
        stderr_cap: int = STDERR_TOTAL_CAP,
    ) -> None:
        if not command:
            raise Phase2TransportError("spawn-command", "candidate command is empty")
        if io_deadline_seconds <= 0 or shutdown_deadline_seconds <= 0:
            raise Phase2TransportError("deadline-config", "subprocess deadlines must be positive")
        if trailing_output_quiet_seconds < 0:
            raise Phase2TransportError("deadline-config", "trailing-output window must be nonnegative")
        if stdout_cap <= 0 or stderr_cap <= 0:
            raise Phase2TransportError("cap-config", "subprocess output caps must be positive")
        self.command = list(command)
        self.io_deadline_seconds = io_deadline_seconds
        self.shutdown_deadline_seconds = shutdown_deadline_seconds
        self.trailing_output_quiet_seconds = trailing_output_quiet_seconds
        self.stdout_cap = stdout_cap
        self.stderr_cap = stderr_cap
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                start_new_session=True,
                bufsize=0,
            )
        except OSError as error:
            raise Phase2TransportError("spawn-failed", str(error)) from error
        self.process_group_id: int | None = None
        try:
            self.process_group_id = os.getpgid(self.process.pid)
        except OSError as error:
            self._kill_process_group()
            raise Phase2TransportError("process-group", str(error)) from error
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            self._kill_process_group()
            raise Phase2TransportError("pipe-unavailable", "candidate pipes are unavailable")

        self.stdin_fd = self.process.stdin.fileno()
        self.stdout_fd = self.process.stdout.fileno()
        self.stderr_fd = self.process.stderr.fileno()
        for fd in (self.stdin_fd, self.stdout_fd, self.stderr_fd):
            os.set_blocking(fd, False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.stdout_fd, selectors.EVENT_READ, "stdout")
        self.selector.register(self.stderr_fd, selectors.EVENT_READ, "stderr")
        self.stdin_registered = False
        self.stdin_closed = False
        self.stdout_buffer = bytearray()
        self.stderr_buffer = bytearray()
        self.stdout_total = 0
        self.stderr_total = 0
        self.stdout_eof = False
        self.stderr_eof = False
        self.closed = False
        self.failure: str | None = None

    def _error(self, code: str, detail: str) -> Phase2TransportError:
        return Phase2TransportError(code, detail)

    def _kill_process_group(self) -> None:
        group_id = self.process_group_id
        if group_id is not None:
            try:
                os.killpg(group_id, signal.SIGKILL)
                return
            except ProcessLookupError:
                return
            except OSError:
                pass
        if self.process.poll() is None:
            try:
                self.process.kill()
            except OSError:
                pass

    def _unregister(self, fd: int) -> None:
        try:
            self.selector.unregister(fd)
        except (KeyError, OSError):
            pass

    def _read_fd(self, fd: int, kind: str) -> None:
        while True:
            try:
                chunk = os.read(fd, 8192)
            except BlockingIOError:
                return
            except OSError as error:
                raise self._error(f"{kind}-read", str(error)) from error
            if not chunk:
                if kind == "stdout":
                    self.stdout_eof = True
                else:
                    self.stderr_eof = True
                self._unregister(fd)
                return
            if kind == "stdout":
                self.stdout_total += len(chunk)
                if self.stdout_total > self.stdout_cap:
                    raise self._error("stdout-cap", "candidate stdout cap exceeded")
                self.stdout_buffer.extend(chunk)
                first_newline = self.stdout_buffer.find(b"\n")
                if first_newline < 0 and len(self.stdout_buffer) > FRAME_BYTES:
                    raise self._error("response-frame-too-large", "candidate response frame exceeds 64 KiB")
                if first_newline >= 0 and first_newline + 1 > FRAME_BYTES:
                    raise self._error("response-frame-too-large", "candidate response frame exceeds 64 KiB")
            else:
                self.stderr_total += len(chunk)
                if self.stderr_total > self.stderr_cap:
                    raise self._error("stderr-cap", "candidate stderr cap exceeded")
                self.stderr_buffer.extend(chunk)

    def _pump(self, deadline: float, write_data: bytearray | None = None) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise self._error("io-timeout", "candidate I/O deadline exceeded")
        if write_data and not self.stdin_closed and not self.stdin_registered:
            try:
                self.selector.register(self.stdin_fd, selectors.EVENT_WRITE, "stdin")
                self.stdin_registered = True
            except (KeyError, OSError) as error:
                raise self._error("stdin-register", str(error)) from error
        events = self.selector.select(min(remaining, 0.05))
        for key, _ in events:
            if key.data == "stdout":
                self._read_fd(self.stdout_fd, "stdout")
            elif key.data == "stderr":
                self._read_fd(self.stderr_fd, "stderr")
            elif key.data == "stdin" and write_data:
                try:
                    written = os.write(self.stdin_fd, write_data)
                except BlockingIOError:
                    written = 0
                except OSError as error:
                    raise self._error("stdin-write", str(error)) from error
                if written:
                    del write_data[:written]
                if not write_data:
                    self._unregister(self.stdin_fd)
                    self.stdin_registered = False

    def _check_process_alive(self, *, response_required: bool = True) -> None:
        returncode = self.process.poll()
        if response_required and returncode is not None and b"\n" not in self.stdout_buffer:
            raise self._error("candidate-exited", f"candidate exited before response ({returncode})")

    def _abort(self, error: Phase2ProtocolError) -> None:
        if self.failure is None:
            self.failure = str(error)
        self._kill_process_group()

    def request(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Send one request and return its opaque, transport-validated response."""
        if not isinstance(request, Mapping):
            raise self._error("request-not-object", "request must be a JSON object")
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise self._error("request-id", "request_id must be a non-empty string")
        if request.get("protocol_id") != REQUEST_PROTOCOL_ID:
            raise self._error("request-protocol", "request protocol ID differs")
        frame = frame_json(request)
        try:
            response_frame = self.request_frame(frame)
            return validate_response_frame(response_frame, request_id)
        except Phase2ProtocolError as error:
            self._abort(error)
            raise

    def request_frame(self, frame: bytes) -> bytes:
        """Exchange one already-framed JSONL record, preserving response bytes."""
        if self.closed:
            raise self._error("session-closed", "candidate session is closed")
        if self.failure is not None:
            raise self._error("session-failed", self.failure)
        if not isinstance(frame, bytes) or not frame.endswith(b"\n"):
            raise self._error("request-frame", "request frame must be bytes ending in LF")
        if len(frame) > FRAME_BYTES:
            raise self._error("request-frame-too-large", "request frame exceeds 64 KiB")
        validate_request_frame(frame)
        if self.stdout_buffer:
            error = self._error("trailing-output", "candidate emitted output before the next request")
            self._abort(error)
            raise error
        pending = bytearray(frame)
        deadline = time.monotonic() + self.io_deadline_seconds
        try:
            while pending:
                self._check_process_alive(response_required=False)
                self._pump(deadline, pending)
            while b"\n" not in self.stdout_buffer:
                self._check_process_alive()
                self._pump(deadline)
            newline = self.stdout_buffer.index(b"\n") + 1
            response = bytes(self.stdout_buffer[:newline])
            del self.stdout_buffer[:newline]
            quiet_deadline = min(deadline, time.monotonic() + self.trailing_output_quiet_seconds)
            while time.monotonic() < quiet_deadline:
                self._pump(quiet_deadline)
                if self.stdout_buffer:
                    raise self._error("extra-output", "candidate emitted more than one response")
                if self.process.poll() is not None and self.stdout_eof:
                    break
            return response
        except Phase2TransportError as error:
            self._abort(error)
            raise

    def _close_stdin(self) -> None:
        if self.stdin_closed:
            return
        self.stdin_closed = True
        self._unregister(self.stdin_fd)
        self.stdin_registered = False
        try:
            os.close(self.stdin_fd)
        except OSError:
            pass

    def close(self) -> CloseResult:
        if self.closed:
            return CloseResult(
                self.process.poll(),
                bytes(self.stdout_buffer),
                bytes(self.stderr_buffer),
                self.failure,
            )
        self.closed = True
        try:
            self._close_stdin()
            deadline = time.monotonic() + self.shutdown_deadline_seconds
            while self.process.poll() is None or not self.stdout_eof or not self.stderr_eof:
                self._pump(deadline)
                if time.monotonic() >= deadline:
                    raise self._error("shutdown-timeout", "candidate shutdown deadline exceeded")
        except Phase2TransportError as error:
            self._abort(error)
            drain_deadline = time.monotonic() + min(0.5, self.shutdown_deadline_seconds)
            while not self.stdout_eof or not self.stderr_eof:
                if time.monotonic() >= drain_deadline:
                    break
                try:
                    self._pump(drain_deadline)
                except Phase2TransportError:
                    break
        finally:
            if self.process.poll() is None or not self.stdout_eof or not self.stderr_eof:
                self._kill_process_group()
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
            try:
                self.selector.close()
            except Exception:
                pass
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except OSError:
                    pass
        return CloseResult(
            self.process.returncode,
            bytes(self.stdout_buffer),
            bytes(self.stderr_buffer),
            self.failure,
        )

    def __enter__(self) -> "BoundedSubprocessSession":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

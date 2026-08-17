"""Deadline-bounded, cap-bounded JSONL subprocess transport."""

from __future__ import annotations

import hashlib
import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Sequence

from runner_common import FRAME_BYTES, PREREGISTERED_LIMITS, ProtocolError, frame_json

IO_DEADLINE_SECONDS = PREREGISTERED_LIMITS["io_deadline_seconds"]
SHUTDOWN_DEADLINE_SECONDS = PREREGISTERED_LIMITS["shutdown_deadline_seconds"]
TRAILING_OUTPUT_QUIET_SECONDS = PREREGISTERED_LIMITS["trailing_output_quiet_seconds"]
STDOUT_TOTAL_CAP = PREREGISTERED_LIMITS["stdout_total_bytes"]
STDERR_TOTAL_CAP = PREREGISTERED_LIMITS["stderr_total_bytes"]


class TransportError(ProtocolError):
    """Candidate process, pipe, deadline, or output framing failure."""


@dataclass(frozen=True)
class CloseResult:
    returncode: int | None
    trailing_stdout: bytes
    stderr: bytes
    failure: str | None


class BoundedSubprocessSession:
    """One persistent JSONL candidate session with bounded concurrent drains."""

    def __init__(
        self,
        command: Sequence[str],
        cwd: str | None = None,
        deadline_seconds: float = IO_DEADLINE_SECONDS,
    ) -> None:
        self.command = list(command)
        self.deadline_seconds = deadline_seconds
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            raise TransportError(f"candidate spawn failed: {error}") from error
        try:
            self.process_group_id: int | None = os.getpgid(self.process.pid)
        except OSError as error:
            try:
                self.process.kill()
            except OSError:
                pass
            raise TransportError(f"candidate process group unavailable: {error}") from error
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            self._kill_process_group()
            raise TransportError("candidate pipes are unavailable")
        self.stdin_fd = self.process.stdin.fileno()
        self.stdout_fd = self.process.stdout.fileno()
        self.stderr_fd = self.process.stderr.fileno()
        for fd in (self.stdin_fd, self.stdout_fd, self.stderr_fd):
            os.set_blocking(fd, False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.stdout_fd, selectors.EVENT_READ, "stdout")
        self.selector.register(self.stderr_fd, selectors.EVENT_READ, "stderr")
        self.stdout_buffer = bytearray()
        self.stderr_buffer = bytearray()
        self.stdout_total = 0
        self.stderr_total = 0
        self.stdout_eof = False
        self.stderr_eof = False
        self.closed = False
        self.failure: str | None = None

    @property
    def stderr_sha256(self) -> str:
        return hashlib.sha256(self.stderr_buffer).hexdigest()

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

    def _read_fd(self, fd: int, kind: str) -> None:
        while True:
            try:
                chunk = os.read(fd, 8192)
            except BlockingIOError:
                return
            except OSError as error:
                raise TransportError(f"candidate {kind} read failed: {error}") from error
            if not chunk:
                if kind == "stdout":
                    self.stdout_eof = True
                else:
                    self.stderr_eof = True
                try:
                    self.selector.unregister(fd)
                except KeyError:
                    pass
                return
            if kind == "stdout":
                self.stdout_total += len(chunk)
                if self.stdout_total > STDOUT_TOTAL_CAP:
                    raise TransportError("candidate stdout total cap exceeded")
                self.stdout_buffer.extend(chunk)
                if b"\n" not in self.stdout_buffer and len(self.stdout_buffer) > FRAME_BYTES:
                    raise TransportError("candidate response frame exceeds byte limit")
            else:
                self.stderr_total += len(chunk)
                if self.stderr_total > STDERR_TOTAL_CAP:
                    raise TransportError("candidate stderr total cap exceeded")
                self.stderr_buffer.extend(chunk)

    def _pump(self, deadline: float, write_data: bytearray | None = None) -> int:
        if time.monotonic() >= deadline:
            raise TransportError("candidate I/O deadline exceeded")
        if write_data is not None and write_data:
            try:
                try:
                    self.selector.register(self.stdin_fd, selectors.EVENT_WRITE, "stdin")
                except KeyError:
                    self.selector.modify(self.stdin_fd, selectors.EVENT_WRITE, "stdin")
            except OSError as error:
                raise TransportError(f"candidate stdin descriptor is unavailable: {error}") from error
        timeout = max(0.0, min(deadline - time.monotonic(), 0.05))
        events = self.selector.select(timeout)
        for key, _ in events:
            if key.data == "stdout":
                self._read_fd(self.stdout_fd, "stdout")
            elif key.data == "stderr":
                self._read_fd(self.stderr_fd, "stderr")
            elif key.data == "stdin" and write_data is not None and write_data:
                try:
                    written = os.write(self.stdin_fd, write_data)
                except BlockingIOError:
                    written = 0
                except OSError as error:
                    raise TransportError(f"candidate stdin write failed: {error}") from error
                if written:
                    del write_data[:written]
                if not write_data:
                    try:
                        self.selector.unregister(self.stdin_fd)
                    except KeyError:
                        pass
        return len(events)

    def _check_process_alive(self) -> None:
        returncode = self.process.poll()
        if returncode is not None and not self.stdout_buffer:
            raise TransportError(f"candidate exited before response with status {returncode}")

    def request(self, request: dict[str, object]) -> bytes:
        return self.request_frame(frame_json(request))

    def request_frame(self, frame: bytes) -> bytes:
        if self.closed:
            raise TransportError("candidate session is closed")
        if self.stdout_buffer:
            raise TransportError("candidate emitted trailing output before the next request")
        frame = bytearray(frame)
        if len(frame) > FRAME_BYTES:
            raise TransportError("candidate request frame exceeds byte limit")
        deadline = time.monotonic() + self.deadline_seconds
        while frame:
            self._check_process_alive()
            self._pump(deadline, frame)
        while b"\n" not in self.stdout_buffer:
            self._check_process_alive()
            self._pump(deadline)
        newline = self.stdout_buffer.index(b"\n") + 1
        if newline > FRAME_BYTES:
            raise TransportError("candidate response frame exceeds byte limit")
        response = bytes(self.stdout_buffer[:newline])
        del self.stdout_buffer[:newline]
        quiet_deadline = min(deadline, time.monotonic() + TRAILING_OUTPUT_QUIET_SECONDS)
        while time.monotonic() < quiet_deadline:
            self._pump(quiet_deadline)
            if self.stdout_buffer:
                raise TransportError("candidate emitted more than one response for one request")
            if self.process.poll() is not None and self.stdout_eof:
                break
        return response

    def close(self) -> CloseResult:
        if self.closed:
            return CloseResult(self.process.poll(), bytes(self.stdout_buffer), bytes(self.stderr_buffer), self.failure)
        self.closed = True
        try:
            try:
                os.close(self.stdin_fd)
            except OSError:
                pass
            deadline = time.monotonic() + SHUTDOWN_DEADLINE_SECONDS
            while self.process.poll() is None or not self.stdout_eof or not self.stderr_eof:
                if time.monotonic() >= deadline:
                    raise TransportError("candidate shutdown deadline exceeded")
                self._pump(deadline)
        except TransportError as error:
            self.failure = str(error)
            self._kill_process_group()
            drain_deadline = time.monotonic() + 0.5
            while not self.stdout_eof or not self.stderr_eof:
                if time.monotonic() >= drain_deadline:
                    break
                try:
                    self._pump(drain_deadline)
                except TransportError:
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
                except Exception:
                    pass
        return CloseResult(self.process.returncode, bytes(self.stdout_buffer), bytes(self.stderr_buffer), self.failure)

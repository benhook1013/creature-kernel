from __future__ import annotations

import os
import signal
import sys
import time
import unittest
from unittest import mock

import phase3_exact_fp_observer as observer


class FPObserverTests(unittest.TestCase):
    def test_platform_gate_is_linux_x86_64_in_this_runner(self) -> None:
        self.assertTrue(observer.is_supported_platform())

    def test_real_stopped_tracee_observation_decodes_x87_and_mxcsr(self) -> None:
        if not observer.is_supported_platform():
            self.skipTest("Linux x86_64 only")
        pid = os.fork()
        if pid == 0:
            try:
                observer.ptrace_traceme()
                os.kill(os.getpid(), signal.SIGSTOP)
                os._exit(0)
            except BaseException:
                os._exit(127)
        try:
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                waited, status = os.waitpid(pid, os.WUNTRACED | os.WNOHANG)
                if waited:
                    break
                time.sleep(0.001)
            self.assertTrue(os.WIFSTOPPED(status))
            value = observer.observe_initial_fp_state(pid)
            self.assertEqual(value.status, "observed")
            self.assertEqual(value.x87_rounding_mode, "nearest")
            self.assertEqual(value.mxcsr_rounding_mode, "nearest")
            self.assertFalse(value.ftz)
            self.assertFalse(value.daz)
            self.assertEqual(value.x87_control_word, 0x037F)
            # The stopped pre-exec Python image may carry non-semantic MXCSR
            # precision/reserved bits; the admission fields are rounding,
            # FTZ, and DAZ.  The transport's post-exec ELF check is exact.
            self.assertEqual(value.mxcsr & (0x3 << 13), 0)
            self.assertGreaterEqual(len(value.raw_xstate), observer.MIN_XSTATE_BYTES)
        finally:
            try:
                observer.ptrace_continue(pid)
            except Exception:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

    def test_wrong_expected_state_is_failed_and_never_admitted(self) -> None:
        if not observer.is_supported_platform():
            self.skipTest("Linux x86_64 only")
        pid = os.fork()
        if pid == 0:
            try:
                observer.ptrace_traceme()
                os.kill(os.getpid(), signal.SIGSTOP)
                os._exit(0)
            except BaseException:
                os._exit(127)
        try:
            waited, status = os.waitpid(pid, os.WUNTRACED)
            self.assertEqual(waited, pid)
            value = observer.observe_fp_state(pid, expected=observer.FPExpectation(x87_rounding_mode="downward"))
            self.assertEqual(value.status, "failed")
            self.assertEqual(value.code, "fp-state-mismatch")
            self.assertFalse(value.usable)
        finally:
            try:
                observer.ptrace_continue(pid)
            except Exception:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

    def test_invalid_pid_is_typed_inconclusive(self) -> None:
        value = observer.observe_fp_state(-1)
        self.assertEqual(value.status, "inconclusive")
        self.assertEqual(value.code, "invalid-pid")

    def test_unavailable_register_read_is_typed_inconclusive(self) -> None:
        with mock.patch.object(observer, "_ptrace", side_effect=observer.FPObserverError("ptrace-failed", "denied", 1)):
            value = observer.observe_fp_state(1234)
        self.assertEqual(value.status, "inconclusive")
        self.assertEqual(value.code, "register-read-unavailable")

    def test_malformed_xstate_is_typed_inconclusive(self) -> None:
        def shorten(_request: int, _pid: int, _address: int, data: object) -> int:
            data._obj.iov_len = 1  # type: ignore[attr-defined]
            return 0

        with mock.patch.object(observer, "_ptrace", side_effect=shorten):
            value = observer.observe_fp_state(42)
        self.assertEqual(value.status, "inconclusive")
        self.assertEqual(value.code, "malformed-xstate")


if __name__ == "__main__":
    unittest.main()

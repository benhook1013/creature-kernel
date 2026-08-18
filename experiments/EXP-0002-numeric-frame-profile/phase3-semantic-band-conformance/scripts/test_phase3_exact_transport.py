from __future__ import annotations

import os
import fcntl
import hashlib
import json
import signal
import tempfile
import unittest
from dataclasses import replace
from unittest import mock
from pathlib import Path

import phase3_exact_fp_observer as observer
from phase3_exact_transport import (
    FRAME_BYTES,
    ExactCandidateSession,
    ExactTransportError,
    ExactTransportLimits,
    F_ADD_SEALS,
    REQUIRED_MEMFD_SEALS,
)


CAT = "/bin/cat"
SHELL = "phase3-fixture"

FIXTURE_SOURCE = b'''#!/bin/bash
mode=${CK_EXACT_FIXTURE_MODE:-normal}
IFS= read -r request || exit 0
case "$mode" in
  normal) printf '%s\\n' "$request" ;;
  malformed) printf 'not-json\\n' ; exit 0 ;;
  extra) printf '%s\\n{"request_id":"extra"}\\n' "$request" ; exit 0 ;;
  trailing) printf '%s\\n' "$request"; sleep 0.05; printf 'trailing\\n' ;;
  stderr) head -c 4096 /dev/zero >&2; sleep 1 ;;
  stdout) head -c 70000 /dev/zero ;;
  sleep) sleep 1 ;;
  exit7) exit 7 ;;
  signal) printf '%s\\n' "$request"; kill -TERM $$ ;;
  partial) printf '{"request_id":"x"' ; exit 0 ;;
esac
'''


class ExactTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ck-phase3-fixture-")
        self.fixture_path = Path(self.temporary.name) / "fixture.sh"
        self.fixture_path.write_bytes(FIXTURE_SOURCE)
        self.fixture_path.chmod(0o500)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture_bytes(self, path: str) -> bytes:
        return Path("/bin/bash").read_bytes() if path == SHELL else Path(path).read_bytes()

    def fd_bytes(self, payload: bytes, label: str = "phase3-fixture", mode: int = 0o500) -> int:
        flags = getattr(os, "MFD_CLOEXEC", 0x0001) | getattr(os, "MFD_ALLOW_SEALING", 0x0002)
        descriptor = os.memfd_create(label, flags)
        try:
            offset = 0
            while offset < len(payload):
                offset += os.write(descriptor, payload[offset:])
            os.fchmod(descriptor, mode)
            fcntl.fcntl(descriptor, F_ADD_SEALS, REQUIRED_MEMFD_SEALS)
            readonly = os.open(f"/proc/self/fd/{descriptor}", os.O_RDONLY | os.O_CLOEXEC)
            os.close(descriptor)
            os.lseek(readonly, 0, os.SEEK_SET)
            return readonly
        except BaseException:
            os.close(descriptor)
            raise

    def fd(self, path: str = CAT) -> int:
        return self.fd_bytes(self.fixture_bytes(path), Path(path).name)

    def session(self, path: str = CAT, *, limits: ExactTransportLimits | None = None, env: dict[str, str] | None = None, **kwargs: object) -> ExactCandidateSession:
        expected = self.fixture_bytes(path)
        launch_env = {} if env is None else dict(env)
        if path == SHELL:
            launch_env.setdefault("BASH_ENV", str(self.fixture_path))
        return ExactCandidateSession(
            self.fd(path),
            Path(path).name,
            launch_env,
            "/tmp",
            expected,
            hashlib.sha256(expected).hexdigest(),
            limits=limits or ExactTransportLimits(io_deadline_seconds=2.0, shutdown_deadline_seconds=2.0),
            **kwargs,
        )

    def test_descriptor_exec_and_floating_point_observation_precede_transport(self) -> None:
        session = self.session()
        try:
            self.assertTrue(session.launch_result is not None and session.launch_result.observed)
            self.assertEqual(session.launch_result.seals_initial, REQUIRED_MEMFD_SEALS)
            self.assertEqual(session.launch_result.seals_pre_fork, REQUIRED_MEMFD_SEALS)
            self.assertEqual(session.launch_result.seals_post_exec, REQUIRED_MEMFD_SEALS)
            self.assertEqual(session.launch_observation.x87_rounding_mode, "nearest")  # type: ignore[union-attr]
            self.assertEqual(session.launch_observation.mxcsr, 0x1F80)  # type: ignore[union-attr]
            self.assertEqual(session.request_frame(b'{"request_id":"one"}'), b'{"request_id":"one"}\n')
            self.assertEqual(session.requests, (b'{"request_id":"one"}\n',))
        finally:
            result = session.close()
            os.close(session.executable_fd)
        self.assertEqual(result.status, "supported")
        self.assertTrue(result.reaped)
        self.assertIsNotNone(result.final_observation)
        self.assertEqual(result.final_observation.status, "observed")
        self.assertEqual(result.final_observation.x87_rounding_mode, "nearest")
        self.assertEqual(result.final_observation.mxcsr_rounding_mode, "nearest")
        self.assertEqual(result.to_dict()["final_observation"]["status"], "observed")
        self.assertFalse(result.killed)
        self.assertEqual(result.attempt_count, 1)
        self.assertEqual(result.request_count, result.response_count)

    def test_request_bytes_are_preserved_and_only_missing_lf_is_added(self) -> None:
        session = self.session()
        try:
            raw = b'{"request_id":"preserve","payload":"\\u00e9"}'
            session.request_frame(raw)
            self.assertEqual(session.requests[0], raw + b"\n")
            self.assertEqual(session.request_frame(b'{"request_id":"already"}\n'), b'{"request_id":"already"}\n')
        finally:
            result = session.close()
            os.close(session.executable_fd)
        self.assertEqual(result.status, "supported")

    def test_materialized_shaped_20k_request_is_admitted_under_frozen_64k_frame_cap(self) -> None:
        session = self.session()
        try:
            raw = b'{"request_id":"large","source":"' + (b"x" * 20_000) + b'"}'
            response = session.request_frame(raw)
            self.assertEqual(response, raw + b"\n")
            result = session.close()
        finally:
            try:
                os.close(session.executable_fd)
            except OSError:
                pass
        self.assertEqual(result.status, "supported")
        self.assertEqual(len(result.requests[0]), len(raw) + 1)

    def test_wrong_fp_policy_fails_closed_before_any_request(self) -> None:
        session = self.session(expected_fp=observer.FPExpectation(x87_rounding_mode="downward"))
        try:
            self.assertEqual(session.launch_result.status, "failed")
            self.assertEqual(session.launch_result.code, "fp-state-mismatch")
            with self.assertRaisesRegex(ExactTransportError, "fp-state-mismatch"):
                session.request_frame(b'{"request_id":"not-sent"}')
            result = session.close()
        finally:
            try:
                os.close(session.executable_fd)
            except OSError:
                pass
        self.assertEqual(result.status, "failed")
        self.assertTrue(result.reaped)
        self.assertEqual(result.request_count, 0)

    def test_request_id_is_utf8_bounded_and_explicit_value_must_match_body(self) -> None:
        session = self.session()
        try:
            with self.assertRaisesRegex(ExactTransportError, "request-id-mismatch"):
                session.request_frame(b'{"request_id":"body"}', request_id="explicit")
            result = session.close()
        finally:
            os.close(session.executable_fd)
        self.assertEqual(result.code, "request-id-mismatch")
        self.assertEqual(result.request_count, 0)

        for request_id, expected_code in (
            ("x" * 257, "request-id-too-large"),
            ("\ud800", "request-id-utf8"),
        ):
            session = self.session()
            try:
                body = json.dumps({"request_id": request_id}, ensure_ascii=True).encode("utf-8")
                with self.assertRaisesRegex(ExactTransportError, expected_code):
                    session.request_frame(body)
                result = session.close()
            finally:
                os.close(session.executable_fd)
            self.assertEqual(result.code, expected_code)

    def test_final_fp_state_drift_is_failed_and_retained(self) -> None:
        session = self.session(auto_launch=False)
        original = observer.observe_initial_fp_state
        calls = 0

        def drift(pid: int, *, expected: object = None) -> object:
            nonlocal calls
            value = original(pid, expected=expected)  # type: ignore[arg-type]
            calls += 1
            if calls == 2:
                return replace(value, mxcsr=value.mxcsr ^ (0x1 << 13), mxcsr_rounding_mode="downward", code="observed")  # type: ignore[union-attr]
            return value

        try:
            with mock.patch.object(observer, "observe_initial_fp_state", side_effect=drift):
                self.assertTrue(session.launch_result is None)
                self.assertTrue(session.launch().observed)
                session.request_frame(b'{"request_id":"drift"}')
                result = session.close()
        finally:
            os.close(session.executable_fd)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.code, "final-fp-state-drift")
        self.assertIsNotNone(result.final_observation)
        self.assertEqual(result.final_observation.status, "observed")

    def test_unavailable_final_fp_state_is_inconclusive_and_retained(self) -> None:
        session = self.session(auto_launch=False)
        original = observer.observe_initial_fp_state
        calls = 0

        def unavailable(pid: int, *, expected: object = None) -> object:
            nonlocal calls
            calls += 1
            if calls == 2:
                return observer.FPStateObservation(
                    "inconclusive", "register-read-unavailable", "test final register read unavailable", pid,
                )
            return original(pid, expected=expected)  # type: ignore[arg-type]

        try:
            with mock.patch.object(observer, "observe_initial_fp_state", side_effect=unavailable):
                self.assertTrue(session.launch().observed)
                session.request_frame(b'{"request_id":"final-unavailable"}')
                result = session.close()
        finally:
            os.close(session.executable_fd)
        self.assertEqual(result.status, "inconclusive")
        self.assertEqual(result.code, "final-fp-observation-unavailable")
        self.assertTrue(result.reaped)
        self.assertIsNotNone(result.final_observation)
        self.assertEqual(result.final_observation.status, "inconclusive")

    def test_missing_exit_event_is_inconclusive_with_clean_reap(self) -> None:
        session = self.session(auto_launch=False)
        original_set_options = observer.ptrace_set_options

        def without_exit_event(pid: int) -> None:
            original_set_options(pid, options=observer.PTRACE_O_TRACEEXEC | observer.PTRACE_O_EXITKILL)

        try:
            with mock.patch.object(observer, "ptrace_set_options", side_effect=without_exit_event):
                self.assertTrue(session.launch().observed)
                session.request_frame(b'{"request_id":"missing-exit-event"}')
                result = session.close()
        finally:
            os.close(session.executable_fd)
        self.assertEqual(result.status, "inconclusive")
        self.assertEqual(result.code, "final-fp-observation-unavailable")
        self.assertTrue(result.reaped)
        self.assertTrue(result.clean_shutdown)
        self.assertIsNone(result.final_observation)

    def test_duplicate_or_wrong_ptrace_exit_stop_fails_closed(self) -> None:
        session = self.session(auto_launch=False)
        stopped_exit = (signal.SIGTRAP << 8) | 0x7F | (observer.PTRACE_EVENT_EXIT << 16)
        stopped_other = (signal.SIGTRAP << 8) | 0x7F | (5 << 16)
        try:
            self.assertTrue(session.launch().observed)
            session._final_exit_stop_seen = True
            with self.assertRaisesRegex(ExactTransportError, "duplicate-final-fp-observation"):
                session._handle_ptrace_stop(stopped_exit)
            session._final_exit_stop_seen = False
            with self.assertRaisesRegex(ExactTransportError, "unexpected-ptrace-stop"):
                session._handle_ptrace_stop(stopped_other)
            session._record_failure("unexpected-ptrace-stop", "synthetic stop")
            result = session.close()
        finally:
            os.close(session.executable_fd)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.code, "unexpected-ptrace-stop")
        self.assertTrue(result.reaped)

    def test_duplicate_real_exit_stop_cleanup_reaps(self) -> None:
        session = self.session(SHELL, env={"CK_EXACT_FIXTURE_MODE": "exit7"})
        try:
            self.assertTrue(session.launch().observed)
            # Synthetic reviewer condition: the real exit event is now a
            # duplicate from the transport state machine's perspective.
            session._final_exit_stop_seen = True
            with self.assertRaisesRegex(ExactTransportError, "duplicate-final-fp-observation"):
                session.request_frame(b'{"request_id":"duplicate-real"}')
            result = session.close()
        finally:
            os.close(session.executable_fd)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.code, "duplicate-final-fp-observation")
        self.assertTrue(result.reaped)

    def test_cwd_path_and_descriptor_are_not_ambiguous(self) -> None:
        descriptor = self.fd()
        cwd_fd = os.open("/tmp", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        expected = self.fixture_bytes(CAT)
        try:
            with self.assertRaisesRegex(ExactTransportError, "cwd-descriptor-ambiguous"):
                ExactCandidateSession(
                    descriptor, "cat", {}, "/tmp", expected,
                    hashlib.sha256(expected).hexdigest(), cwd_fd=cwd_fd,
                )
        finally:
            os.close(descriptor)
            os.close(cwd_fd)

    def test_argv_and_environment_bounds_fail_before_launch(self) -> None:
        expected = self.fixture_bytes(CAT)
        cases = (
            {"argv0": "a" * 257},
            {"env": {"k" * 257: "v"}},
            {"env": {"k": "v" * 4097}},
            {"env": {str(index): "v" for index in range(129)}},
        )
        for kwargs in cases:
            descriptor = self.fd()
            try:
                with self.assertRaises((TypeError, ValueError)):
                    ExactCandidateSession(
                        descriptor, "cat", {}, "/tmp", expected,
                        hashlib.sha256(expected).hexdigest(), **kwargs,
                    )
            finally:
                os.close(descriptor)

    def test_constructor_validation_closes_acquired_cwd_descriptor(self) -> None:
        baseline = len(os.listdir("/proc/self/fd"))
        expected = self.fixture_bytes(CAT)
        descriptor = self.fd()
        try:
            with self.assertRaises((TypeError, ValueError)):
                ExactCandidateSession(
                    descriptor, "cat", {}, "/tmp", expected,
                    hashlib.sha256(expected).hexdigest(), frames=[object()],
                )
        finally:
            os.close(descriptor)
        self.assertLessEqual(len(os.listdir("/proc/self/fd")), baseline + 1)

    def shell_failure(self, command: bytes, *, limits: ExactTransportLimits | None = None, request_id: str = "x") -> tuple[ExactCandidateSession, object]:
        if b"not-json" in command:
            mode = "malformed"
        elif b'"extra"' in command:
            mode = "extra"
        elif b"4096" in command:
            mode = "stderr"
        elif b"70000" in command:
            mode = "stdout"
        elif b"exit 7" in command:
            mode = "exit7"
        elif b"sleep 1" in command:
            mode = "sleep"
        else:
            mode = "normal"
        session = self.session(SHELL, limits=limits, env={"CK_EXACT_FIXTURE_MODE": mode})
        try:
            with self.assertRaises(ExactTransportError):
                body = json.dumps({"request_id": request_id}, separators=(",", ":")).encode()
                session.request_frame(body, request_id=request_id)
        finally:
            result = session.close()
            try:
                os.close(session.executable_fd)
            except OSError:
                pass
        return session, result

    def test_malformed_response_is_retained_and_reaped(self) -> None:
        session, result = self.shell_failure(b"printf 'not-json\\n'; exit 0")
        self.assertEqual(result.code, "malformed-response")
        self.assertEqual(result.responses, (b"not-json\n",))
        self.assertTrue(result.reaped)

    def test_extra_frame_is_rejected(self) -> None:
        session, result = self.shell_failure(b"printf '{\"request_id\":\"x\"}\\n{\"request_id\":\"extra\"}\\n'; exit 0")
        self.assertEqual(result.code, "extra-output")
        self.assertEqual(result.response_count, 1)
        self.assertTrue(result.partial)
        self.assertTrue(result.reaped)

    def test_trailing_output_after_quiet_window_is_failed(self) -> None:
        session = self.session(SHELL, env={"CK_EXACT_FIXTURE_MODE": "trailing"}, limits=ExactTransportLimits(io_deadline_seconds=0.8, shutdown_deadline_seconds=0.8, trailing_output_quiet_seconds=0.01))
        try:
            response = session.request_frame(b'{"request_id":"x"}', request_id="x")
            self.assertEqual(response, b'{"request_id":"x"}\n')
            result = session.close()
        finally:
            try:
                os.close(session.executable_fd)
            except OSError:
                pass
        self.assertEqual(result.code, "trailing-output")
        self.assertTrue(result.reaped)

    def test_stderr_and_aggregate_output_limits_kill_and_reap(self) -> None:
        stderr_session, stderr_result = self.shell_failure(
            b"head -c 4096 /dev/zero >&2; sleep 1",
            limits=ExactTransportLimits(stderr_total_bytes=1024, io_deadline_seconds=0.3, shutdown_deadline_seconds=0.3),
        )
        self.assertEqual(stderr_result.code, "stderr-cap")
        self.assertTrue(stderr_result.killed and stderr_result.reaped)
        stdout_session, stdout_result = self.shell_failure(
            b"head -c 70000 /dev/zero",
            limits=ExactTransportLimits(io_deadline_seconds=0.3, shutdown_deadline_seconds=0.3),
        )
        self.assertEqual(stdout_result.code, "response-frame-too-large")
        self.assertTrue(stdout_result.killed and stdout_result.reaped)

    def test_deadline_early_exit_and_signal_are_typed(self) -> None:
        _, timeout_result = self.shell_failure(
            b"sleep 1",
            limits=ExactTransportLimits(io_deadline_seconds=0.05, shutdown_deadline_seconds=0.1),
        )
        self.assertEqual(timeout_result.code, "io-timeout")
        self.assertTrue(timeout_result.killed and timeout_result.reaped)
        _, exit_result = self.shell_failure(b"exit 7")
        self.assertEqual(exit_result.code, "candidate-exited")
        self.assertEqual(exit_result.exit_code, 7)
        self.assertTrue(exit_result.reaped)
        signal_session = self.session(SHELL, env={"CK_EXACT_FIXTURE_MODE": "signal"})
        try:
            with self.assertRaisesRegex(ExactTransportError, "unexpected-ptrace-stop"):
                signal_session.request_frame(b'{"request_id":"x"}', request_id="x")
            signal_result = signal_session.close()
        finally:
            try:
                os.close(signal_session.executable_fd)
            except OSError:
                pass
        self.assertEqual(signal_result.code, "unexpected-ptrace-stop")
        self.assertTrue(signal_result.reaped)

    def test_partial_observation_is_not_fabricated(self) -> None:
        session = self.session(SHELL, env={"CK_EXACT_FIXTURE_MODE": "partial"})
        try:
            with self.assertRaises(ExactTransportError):
                session.request_frame(b'{"request_id":"x"}', request_id="x")
            result = session.close()
        finally:
            try:
                os.close(session.executable_fd)
            except OSError:
                pass
        self.assertEqual(result.response_count, 0)
        self.assertTrue(result.partial)
        self.assertIn(b'{"request_id":"x"', result.stdout)

    def test_descriptor_substitution_is_rejected_and_no_retry_occurs(self) -> None:
        expected = self.fixture_bytes(CAT)
        descriptor = self.fd_bytes(expected, "substitution-original")
        session = ExactCandidateSession(descriptor, "fixture", {}, "/tmp", expected, hashlib.sha256(expected).hexdigest(), auto_launch=False)
        os.close(descriptor)
        replacement = self.fd_bytes(expected, "substitution-replacement")
        try:
            result_launch = session.launch()
            self.assertEqual(result_launch.code, "descriptor-substitution")
            self.assertEqual(session.attempt_count, 1)
            self.assertIs(session.launch(), result_launch)
            result = session.close()
        finally:
            os.close(replacement)
        self.assertEqual(result.status, "failed")
        self.assertTrue(result.reaped)

    def test_expected_content_hash_and_readonly_access_are_required(self) -> None:
        expected = self.fixture_bytes(CAT)
        wrong_hash_fd = self.fd_bytes(expected, "wrong-hash")
        with self.assertRaisesRegex(ExactTransportError, "expected-hash-mismatch"):
            ExactCandidateSession(wrong_hash_fd, "cat", {}, "/tmp", expected, "0" * 64)
        os.close(wrong_hash_fd)
        readonly_fd = self.fd_bytes(expected, "write-access", mode=0o700)
        descriptor = os.open(f"/proc/self/fd/{readonly_fd}", os.O_WRONLY | os.O_CLOEXEC)
        os.close(readonly_fd)
        try:
            with self.assertRaisesRegex(ExactTransportError, "descriptor-not-readonly"):
                ExactCandidateSession(descriptor, "cat", {}, "/tmp", expected, hashlib.sha256(expected).hexdigest())
        finally:
            os.close(descriptor)

    def test_unsealed_or_mutable_executable_is_rejected_before_fork(self) -> None:
        expected = self.fixture_bytes(CAT)
        descriptor = os.memfd_create("unsealed", getattr(os, "MFD_CLOEXEC", 0x0001))
        try:
            os.write(descriptor, expected)
            os.fchmod(descriptor, 0o500)
            with self.assertRaisesRegex(ExactTransportError, "descriptor-not-sealed"):
                ExactCandidateSession(descriptor, "cat", {}, "/tmp", expected, hashlib.sha256(expected).hexdigest())
        finally:
            os.close(descriptor)

    def test_invalid_run_inputs_return_typed_failure_not_supported_zero(self) -> None:
        for invalid in ("not-a-sequence", [], [b"not-json"]):
            with self.subTest(invalid=repr(invalid)):
                session = self.session()
                try:
                    result = session.run(invalid)  # type: ignore[arg-type]
                    try:
                        os.close(session.executable_fd)
                    except OSError:
                        pass
                except Exception:
                    try:
                        session.close()
                    finally:
                        os.close(session.executable_fd)
                    raise
                self.assertEqual(result.status, "failed")
                self.assertNotEqual(result.code, None)

    def test_twenty_clean_sessions_are_reaped_without_shutdown_timeout(self) -> None:
        for ordinal in range(20):
            session = self.session()
            try:
                session.request_frame((f'{{"request_id":"clean-{ordinal}"}}').encode("ascii"))
                result = session.close()
            finally:
                os.close(session.executable_fd)
            self.assertEqual(result.status, "supported", result.detail)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(result.reaped)
            self.assertNotEqual(result.code, "shutdown-timeout")

    def test_repeated_failure_sessions_do_not_accumulate_parent_fds(self) -> None:
        baseline = len(os.listdir("/proc/self/fd"))
        expected = self.fixture_bytes(SHELL)
        expected_hash = hashlib.sha256(expected).hexdigest()
        for _ in range(8):
            descriptor = self.fd_bytes(expected, "failure-fixture")
            session = ExactCandidateSession(
                descriptor, "fixture", {"CK_EXACT_FIXTURE_MODE": "sleep"}, "/tmp", expected, expected_hash,
                limits=ExactTransportLimits(io_deadline_seconds=0.05, shutdown_deadline_seconds=0.1),
            )
            try:
                result = session.run([b'{"request_id":"x"}'])
            finally:
                os.close(descriptor)
            self.assertEqual(result.status, "failed")
            self.assertTrue(result.reaped)
        self.assertLessEqual(len(os.listdir("/proc/self/fd")), baseline + 2)

    def test_unresolved_reap_remains_bounded_and_truthful(self) -> None:
        session = self.session(limits=ExactTransportLimits(io_deadline_seconds=0.05, shutdown_deadline_seconds=0.001))
        session._record_failure("forced-test-failure", "exercise bounded reaping")
        try:
            with mock.patch.object(session, "_wait_for_status", return_value=None):
                result = session.close()
            self.assertFalse(result.reaped)
            self.assertEqual(result.code, "forced-test-failure")
        finally:
            if session.pid is not None and not result.reaped:
                try:
                    os.kill(session.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    os.waitpid(session.pid, 0)
                except ChildProcessError:
                    pass

    def test_no_shell_wrapper_or_environment_injection_surface(self) -> None:
        with self.assertRaises((TypeError, ValueError)):
            self.session(argv0=["cat"])  # type: ignore[arg-type]
        with self.assertRaises((TypeError, ValueError)):
            self.session(env={"BAD=KEY": "value"})
        session = self.session()
        try:
            # cat receives the exact bytes and no shell expands metacharacters.
            raw = b'{"request_id":"literal","value":"$(touch /tmp/nope)"}'
            self.assertEqual(session.request_frame(raw), raw + b"\n")
        finally:
            result = session.close()
            os.close(session.executable_fd)
        self.assertEqual(result.status, "supported")

    def test_frame_limit_and_no_retry_after_failure(self) -> None:
        session = self.session()
        try:
            with self.assertRaises(ExactTransportError):
                session.request_frame(b"{" + b"x" * FRAME_BYTES)
            first = session.close()
            second = session.close()
        finally:
            try:
                os.close(session.executable_fd)
            except OSError:
                pass
        self.assertEqual(first, second)
        self.assertTrue(first.reaped)
        self.assertEqual(first.attempt_count, 1)


if __name__ == "__main__":
    unittest.main()

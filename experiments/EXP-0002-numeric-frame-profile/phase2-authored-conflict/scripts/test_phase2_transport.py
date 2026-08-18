from __future__ import annotations

import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase2_common import (
    FRAME_BYTES,
    MAX_SOURCE_BYTES,
    MAX_REQUEST_ID_BYTES,
    MAX_SESSION_RECORDS,
    REQUEST_PROTOCOL_ID,
    Phase2ProtocolError,
)
from phase2_transport import BoundedSubprocessSession, Phase2TransportError


SCRIPT = textwrap.dedent(
    r'''
    import json
    import os
    import sys
    import time

    mode = sys.argv[1]
    response_protocol = "ck.exp-0002.r3-authored-conflict-candidate-response-1"

    def response(request_id, status="observed"):
        return json.dumps({
            "protocol_id": response_protocol,
            "request_id": request_id,
            "status": status,
        }, separators=(",", ":")) + "\n"

    def padded_response(request_id):
        return json.dumps({
            "protocol_id": response_protocol,
            "request_id": request_id,
            "status": "observed",
            "padding": "x" * 2048,
        }, separators=(",", ":")) + "\n"

    if mode == "no-response":
        time.sleep(10)
    elif mode == "stderr":
        sys.stderr.write("x" * (%d + 1))
        sys.stderr.flush()
        time.sleep(10)
    elif mode == "inherited-pipe":
        child = os.fork()
        if child == 0:
            time.sleep(10)
            os._exit(0)
        os._exit(0)
    elif mode == "crash-after-response":
        for line in sys.stdin:
            request = json.loads(line)
            sys.stdout.write(response(request["request_id"]))
            sys.stdout.flush()
            os._exit(7)
    elif mode == "trailing-at-close":
        for line in sys.stdin:
            request = json.loads(line)
            sys.stdout.write(response(request["request_id"]))
            sys.stdout.flush()
            time.sleep(0.05)
            sys.stdout.write("trailing-output\n")
            sys.stdout.flush()
            for _ in sys.stdin:
                pass
    else:
        for line in sys.stdin:
            request = json.loads(line)
            request_id = request["request_id"]
            if mode == "malformed":
                sys.stdout.write("{not-json}\n")
            elif mode == "non-object":
                sys.stdout.write("[]\n")
            elif mode == "duplicate":
                sys.stdout.write(
                    '{{"protocol_id":"{}","request_id":"{}","status":"observed","request_id":"{}"}}\n'
                    .format(response_protocol, request_id, request_id)
                )
            elif mode == "wrong-protocol":
                sys.stdout.write(response(request_id).replace(response_protocol, "wrong-protocol"))
            elif mode == "oversized":
                sys.stdout.write("x" * (%d + 1) + "\n")
            elif mode == "extra-output":
                sys.stdout.write(response(request_id))
                sys.stdout.write(response(request_id))
            elif mode == "large-repeated":
                sys.stdout.write(padded_response(request_id))
            else:
                sys.stdout.write(response(request_id))
            sys.stdout.flush()
    '''
) % (FRAME_BYTES, FRAME_BYTES)


class Phase2TransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ck-phase2-transport-")
        self.script = Path(self.temporary.name) / "candidate.py"
        self.script.write_text(SCRIPT, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def session(self, mode: str, **kwargs: object) -> BoundedSubprocessSession:
        return BoundedSubprocessSession(
            [sys.executable, "-u", str(self.script), mode],
            **kwargs,
        )

    @staticmethod
    def request(request_id: str = "request-1", **extra: object) -> dict[str, object]:
        request: dict[str, object] = {
            "protocol_id": REQUEST_PROTOCOL_ID,
            "request_id": request_id,
            "operation": "observe-authored-conflict",
            "source": "{}",
        }
        request.update(extra)
        return request

    def test_real_subprocess_supports_repeated_records_and_clean_close(self) -> None:
        session = self.session("normal")
        try:
            first = session.request(self.request("request-1"))
            second = session.request(self.request("request-2"))
            self.assertEqual(first["request_id"], "request-1")
            self.assertEqual(second["request_id"], "request-2")
        finally:
            result = session.close()
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(result.failure)
        self.assertEqual(result.trailing_stdout, b"")

    def test_repeated_legal_output_can_exceed_one_frame_cumulatively(self) -> None:
        session = self.session("large-repeated")
        try:
            for index in range(40):
                response = session.request(self.request(f"request-{index}"))
                self.assertEqual(response["status"], "observed")
            self.assertGreater(session.stdout_total, FRAME_BYTES)
        finally:
            result = session.close()
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(result.failure)

    def test_session_record_limit_rejects_the_65th_request(self) -> None:
        session = self.session("normal")
        try:
            for index in range(MAX_SESSION_RECORDS):
                session.request(self.request(f"request-{index}"))
            with self.assertRaisesRegex(Phase2TransportError, "request-limit"):
                session.request(self.request("request-65"))
        finally:
            result = session.close()
        self.assertIn("request-limit", result.failure or "")

    def test_duplicate_json_response_is_rejected(self) -> None:
        session = self.session("duplicate")
        try:
            with self.assertRaisesRegex(Phase2ProtocolError, "duplicate-key"):
                session.request(self.request())
        finally:
            result = session.close()
        self.assertIn("duplicate-key", result.failure or "")

    def test_non_object_and_protocol_anomaly_are_rejected(self) -> None:
        for mode, code in (("non-object", "response-not-object"), ("wrong-protocol", "protocol-mismatch")):
            with self.subTest(mode=mode):
                session = self.session(mode)
                try:
                    with self.assertRaisesRegex(Phase2ProtocolError, code):
                        session.request(self.request())
                finally:
                    session.close()

    def test_oversized_response_is_rejected(self) -> None:
        session = self.session("oversized")
        try:
            with self.assertRaises(Phase2TransportError) as raised:
                session.request(self.request())
        finally:
            session.close()
        self.assertIn(raised.exception.code, {"stdout-cap", "response-frame-too-large"})

    def test_stderr_cap_is_enforced_while_waiting_for_response(self) -> None:
        session = self.session("stderr", io_deadline_seconds=0.5)
        try:
            with self.assertRaisesRegex(Phase2TransportError, "stderr-cap"):
                session.request(self.request())
        finally:
            session.close()

    def test_no_response_hits_wall_deadline_and_terminates(self) -> None:
        session = self.session("no-response", io_deadline_seconds=0.15, shutdown_deadline_seconds=0.15)
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(Phase2TransportError, "io-timeout"):
                session.request(self.request())
        finally:
            result = session.close()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertIn("io-timeout", result.failure or "")

    def test_close_classifies_nonzero_exit_after_valid_response(self) -> None:
        session = self.session("crash-after-response")
        self.assertEqual(session.request(self.request())["status"], "observed")
        result = session.close()
        self.assertEqual(result.returncode, 7)
        self.assertIn("candidate-exit", result.failure or "")

    def test_close_classifies_trailing_stdout_after_response(self) -> None:
        session = self.session("trailing-at-close")
        self.assertEqual(session.request(self.request())["status"], "observed")
        result = session.close()
        self.assertIn("trailing-output", result.failure or "")

    def test_unreaped_state_is_a_terminal_failure(self) -> None:
        session = self.session("normal")
        try:
            session.process.returncode = None
            session._classify_terminal_failure()
            self.assertIn("candidate-not-reaped", session.failure or "")
        finally:
            result = session.close()
        self.assertIn("candidate-not-reaped", result.failure or "")

    def test_context_manager_raises_close_integrity_failure(self) -> None:
        with self.assertRaisesRegex(Phase2TransportError, "session-integrity"):
            with self.session("crash-after-response") as session:
                session.request(self.request())

    def test_context_manager_preserves_active_exception_while_closing(self) -> None:
        with self.assertRaises(ValueError):
            with self.session("no-response", shutdown_deadline_seconds=0.1):
                raise ValueError("caller failure")

    def test_delayed_inherited_pipe_is_terminated_as_a_process_group(self) -> None:
        session = self.session("inherited-pipe", shutdown_deadline_seconds=0.1)
        started = time.monotonic()
        result = session.close()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertIn("shutdown-timeout", result.failure or "")

    def test_extra_response_is_rejected(self) -> None:
        session = self.session("extra-output")
        try:
            with self.assertRaisesRegex(Phase2TransportError, "extra-output"):
                session.request(self.request())
        finally:
            session.close()

    def test_source_material_bound_before_spawn_exchange(self) -> None:
        session = self.session("normal")
        try:
            with self.assertRaisesRegex(Phase2ProtocolError, "source-too-large"):
                session.request(self.request(source="x" * (MAX_SOURCE_BYTES + 1)))
        finally:
            result = session.close()
        self.assertIsNone(result.failure)

    def test_request_id_uses_shared_utf8_byte_bound(self) -> None:
        accepted_id = "é" * (MAX_REQUEST_ID_BYTES // len("é".encode("utf-8")))
        rejected_id = "é" * ((MAX_REQUEST_ID_BYTES // len("é".encode("utf-8"))) + 1)
        self.assertEqual(len(accepted_id.encode("utf-8")), MAX_REQUEST_ID_BYTES)
        self.assertGreater(len(rejected_id.encode("utf-8")), MAX_REQUEST_ID_BYTES)
        session = self.session("normal")
        try:
            response = session.request(self.request(accepted_id))
            self.assertEqual(response["request_id"], accepted_id)
            with self.assertRaisesRegex(Phase2ProtocolError, "request-id-too-large"):
                session.request(self.request(rejected_id))
        finally:
            result = session.close()
        self.assertIsNone(result.failure)

    def test_request_id_encoding_failure_has_stable_code(self) -> None:
        session = self.session("normal")
        try:
            with self.assertRaisesRegex(Phase2ProtocolError, "request-id-encoding"):
                session.request(self.request("\ud800"))
        finally:
            result = session.close()
        self.assertIsNone(result.failure)

    def test_request_frame_bound_is_enforced(self) -> None:
        session = self.session("normal")
        try:
            with self.assertRaisesRegex(Phase2TransportError, "request-frame-too-large"):
                session.request_frame(b"x" * (FRAME_BYTES + 1) + b"\n")
        finally:
            result = session.close()
        self.assertIsNone(result.failure)

    def test_close_is_idempotent_after_normal_exit(self) -> None:
        session = self.session("normal")
        session.request(self.request())
        first = session.close()
        second = session.close()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

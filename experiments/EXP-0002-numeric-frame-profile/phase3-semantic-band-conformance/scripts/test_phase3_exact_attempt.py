"""Focused synthetic tests for the exact-attempt orchestration boundary.

No package corpus, candidate executable, subprocess, or real publication is
used here.  Every execution-capable dependency is replaced with a bounded
in-memory fake.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import phase3_exact_attempt as M


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


RUNTIME_PATHS = tuple(M.evidence_contract.TOOL_ORDER)
EXACT_PATHS = tuple(M.authority.REQUIRED_EXACT_RUNTIME_TOOLS)
PROVENANCE_PATHS = (
    "scripts/generate_phase3.py",
    "scripts/check_candidate_prebinding.py",
    "scripts/phase3_build_receipt.py",
    "scripts/phase3_freeze_manifest.py",
)
ALL_PATHS = (*RUNTIME_PATHS, *EXACT_PATHS, *PROVENANCE_PATHS)
TOOLS = [{"path": path, "bytes": index + 1, "sha256": f"{index + 1:064x}"} for index, path in enumerate(ALL_PATHS)]
CANDIDATE_COMMIT = "c" * 40
EXECUTION_COMMIT = "e" * 40
FROZEN_BINARY = {"bytes": 100_944_288, "mode": 0o100755, "sha256": "f" * 64}
EMPTY_STREAM = {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}
LIFECYCLE = {
    "state": "exited", "exit_code": 0, "term_signal": None,
    "reaped": True, "killed": False, "partial": False,
    "clean_shutdown": True, "startup_error": "", "rusage": None,
}
EMPTY_OUTPUT = {
    "missing": [], "extra": [], "trailing": [],
    "stdout": EMPTY_STREAM, "stderr": EMPTY_STREAM,
}


def _freeze_value() -> bytes:
    def entry(tool: dict[str, object]) -> dict[str, object]:
        return {"path": tool["path"], "mode": 0o644, "bytes": tool["bytes"], "sha256": tool["sha256"]}
    by_path = {item["path"]: item for item in TOOLS}
    return _canonical({
        "manifest_sha256": "a" * 64,
        "candidate_source_commit": CANDIDATE_COMMIT,
        "execution_tool_source_commit": EXECUTION_COMMIT,
        "runtime_tool_identities": [entry(by_path[path]) for path in RUNTIME_PATHS],
        "exact_runtime_tool_identities": [entry(by_path[path]) for path in EXACT_PATHS],
        "provenance_tool_identities": [entry(by_path[path]) for path in PROVENANCE_PATHS],
        "binaries": {
            "wsl2-x86_64": {"status": "bound", "binary_identity": FROZEN_BINARY},
            "ubuntu-24.04-x86_64": {"status": "bound", "binary_identity": {"bytes": 100_945_304, "mode": 0o100755, "sha256": "e" * 64}},
        },
    })


def _platform_value(selector: str = "wsl2-x86_64") -> dict[str, object]:
    def location(name: str) -> dict[str, object]:
        return {"path": f"/home/test/{name}", "kind": "directory", "device": 1, "inode": 10, "mode": 0o40700, "size": 0, "nlink": 1, "filesystem": "ext4", "mount": "/home"}
    return {
        "selector": selector,
        "cpu_model": "synthetic-cpu",
        "cpu_features": ["synthetic-feature"],
        "architecture": "x86_64",
        "kernel_or_wsl": "synthetic-kernel",
        "os_release": "synthetic-os",
        "filesystem": "synthetic-fs",
        "mount_context": "synthetic-mount",
        "workflow_runner": "synthetic-runner",
        "workflow_image": "synthetic-image",
        "toolchain": "synthetic-toolchain",
        "compiler": "synthetic-compiler",
        "locations": {"package": location("package"), "output": location("output"), "work": location("work"), "custody": location("custody"), "roles": {role: location(role) for role in M.ROLE_ORDER}},
        "runtime": {"implementation": "CPython", "version": "3.13.0", "executable": "/home/test/python", "python_version": "3.13.0", "platform": "linux-x86_64", "libc": "glibc 2.39"},
        "build_receipt": {"source": "frozen-build-receipt", "selector": selector, "receipt_sha256": "1" * 64, "receipt_self_hash": "2" * 64, "platform_role": "wsl" if selector == "wsl2-x86_64" else "native", "runner_os": "synthetic-runner", "image_os": "synthetic-image", "image_version": "1", "toolchain": "synthetic-toolchain", "compiler": "synthetic-compiler"},
    }


@dataclass(frozen=True)
class Request:
    request_id: str
    request_bytes: bytes


class Cohort:
    def __init__(self, role: str, count: int) -> None:
        self.role = role
        self.requests = tuple(Request(f"p3-attempt-001-{ordinal:03d}", f"request-{ordinal}".encode()) for ordinal in range(count))

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(item.request_id for item in self.requests)

    @property
    def request_bytes(self) -> tuple[bytes, ...]:
        return tuple(item.request_bytes for item in self.requests)


class Prepared:
    attempt_id = "attempt-001"

    def __init__(self) -> None:
        self.transport = tuple(Cohort(role, M.ROLE_REQUEST_COUNTS[role]) for role in M.ROLE_ORDER)


class Verified:
    candidate_fd = 17
    candidate_bytes = FROZEN_BINARY["bytes"]
    candidate_sha256 = "f" * 64

    def __init__(self, on_close=None) -> None:
        self._on_close = on_close

    def close(self) -> None:
        if self._on_close is not None:
            self._on_close()


class Reservation:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.attempt_id = "attempt-001"
        self.experiment_slot = {
            "successor_manifest_sha256": "a" * 64,
            "platform_selector": "wsl2-x86_64",
            "ordinal": 0,
            "attempt_id": "attempt-001",
        }
        self.closed = False
        self.marker_exists = True

    def close(self) -> None:
        self.events.append("reservation-close")
        self.closed = True


class Session:
    def __init__(self, role: str, events: list[str], fail: bool) -> None:
        self.role = role
        self.events = events
        self.fail = fail
        self.runs = 0
        self.closed = False
        self.close_calls = 0

    def run(self) -> dict[str, object]:
        self.runs += 1
        self.events.append(f"run-{self.role}")
        if self.fail:
            raise RuntimeError("synthetic process failure")
        return {
            "status": "inconclusive",
            "code": "synthetic",
            "detail": "synthetic transport result",
            "requests": tuple(f"request-{index}".encode() for index in range(M.ROLE_REQUEST_COUNTS[self.role])),
            "responses": tuple(b"response" for _ in range(M.ROLE_REQUEST_COUNTS[self.role])),
            "lifecycle": {"state": "exited", "exit_code": 0, "term_signal": None, "reaped": True, "killed": False, "partial": False, "clean_shutdown": True, "startup_error": "", "rusage": None},
            "output": {"missing": [], "extra": [], "trailing": [], "stdout": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}, "stderr": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}},
            "fe_mxcsr": None,
        }

    def close(self) -> None:
        self.close_calls += 1
        self.closed = True


class OrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events: list[str] = []
        self.sessions: list[Session] = []
        self.cwd_fds: list[int] = []
        self.verified_closed = 0
        self.reservation = Reservation(self.events)
        self.freeze = _freeze_value()
        self.admission = _canonical({"record": "admission"})
        self.authorization = _canonical({"record": "authorization"})
        self.custody = _canonical({"custody_record_sha256": "c" * 64})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def deps(self, *, fail_first: bool = True, fail_result: bool = False) -> M._ExactAttemptDependencies:
        def preflight(*args: object) -> dict[str, object]:
            self.events.append("preflight")
            def full_entry(item: dict[str, object]) -> dict[str, object]:
                return {**item, "mode": 0o644}
            by_path = {item["path"]: item for item in TOOLS}
            execution_package = {
                "manifest_sha256": "a" * 64,
                "candidate_source_commit": CANDIDATE_COMMIT,
                "execution_tool_source_commit": EXECUTION_COMMIT,
                "source_snapshot_validation": {
                    "status": "passed",
                    "checker": "phase3_freeze_manifest.check_manifest",
                    "ancestry_algorithm": "git merge-base --is-ancestor",
                    "candidate_source_commit": CANDIDATE_COMMIT,
                    "execution_tool_source_commit": EXECUTION_COMMIT,
                    "candidate_is_ancestor_of_execution_tools": True,
                    "current_execution_tools_match_execution_tool_commit": True,
                    "current_execution_tool_identity_count": len(TOOLS),
                },
                "runtime_tool_identities": [full_entry(by_path[path]) for path in RUNTIME_PATHS],
                "exact_runtime_tool_identities": [full_entry(by_path[path]) for path in EXACT_PATHS],
                "provenance_tool_identities": [full_entry(by_path[path]) for path in PROVENANCE_PATHS],
            }
            return {"schema": M.gate_b_preflight.SCHEMA, "execution_permitted": False, "execution_package": execution_package, "tool_identities": TOOLS}

        def admission(*args: object, **kwargs: object) -> dict[str, object]:
            self.events.append("admission")
            return {"freeze_manifest_sha256": "a" * 64, "execution_permitted": False}

        def custody(*args: object, **kwargs: object) -> Verified:
            self.events.append("custody")
            return Verified(lambda: setattr(self, "verified_closed", self.verified_closed + 1))

        def validate_custody_record(*args: object, **kwargs: object) -> dict[str, object]:
            self.events.append("custody-static")
            return {"custody_record_sha256": "c" * 64, "candidate": dict(FROZEN_BINARY)}

        def authorization(*args: object, **kwargs: object) -> dict[str, object]:
            self.events.append("authorization")
            return {"attempt_id": "attempt-001", "platform_selector": "wsl2-x86_64", "ordinal": 0, "authorization_reference": "BEN-AUTH-001", "execution_permitted": True, "automatic_retry": False}

        def prepare(*args: object, **kwargs: object) -> Prepared:
            self.events.append("prepare")
            return Prepared()

        def reserve(*args: object, **kwargs: object) -> Reservation:
            self.assertEqual(len(args), 5)
            self.assertEqual(args[1:], ("a" * 64, "wsl2-x86_64", 0, "attempt-001"))
            self.assertEqual(kwargs, {})
            self.events.append("reserve")
            return self.reservation

        def factory(**kwargs: object) -> Session:
            self.assertEqual(set(kwargs), {"executable_fd", "argv0", "env", "cwd", "cwd_fd", "expected_bytes", "expected_sha256", "frames", "expected_fp", "auto_launch"})
            self.assertIs(kwargs["auto_launch"], False)
            self.assertIsNone(kwargs["cwd"])
            self.assertIsInstance(kwargs["cwd_fd"], int)
            self.cwd_fds.append(kwargs["cwd_fd"])
            self.assertEqual(kwargs["argv0"], M.CANDIDATE_ARGV0)
            self.assertEqual(kwargs["env"], dict(M.CANDIDATE_ENVIRONMENT))
            self.assertNotIn("candidate_path", kwargs)
            self.assertNotIn("retry", kwargs)
            self.assertNotIn("process_count", kwargs)
            self.events.append(f"factory-{len(self.sessions)}")
            session = Session(M.ROLE_ORDER[len(self.sessions)], self.events, fail=fail_first and not self.sessions)
            self.sessions.append(session)
            return session

        def adjudicate(*args: object, **kwargs: object) -> object:
            self.events.append("adjudicate")
            self.assertIs(kwargs.get("allow_incomplete"), True)

            class Run:
                def evidence_contract_inputs(inner_self) -> dict[str, object]:
                    return {"adjudications": [{"ordinal": index} for index in range(60)]}

            return Run()

        def build_result(*args: object, **kwargs: object) -> bytes:
            self.events.append("build-result")
            if fail_result:
                raise RuntimeError("synthetic post-reservation failure")
            return b"result"

        return M._ExactAttemptDependencies(
            preflight=preflight,
            prepare=prepare,
            validate_admission=admission,
            validate_authorization=authorization,
            validate_custody_record=validate_custody_record,
            verify_custody=custody,
            reserve_attempt=reserve,
            transport_factory=factory,
            adjudicate=adjudicate,
            build_result=build_result,
            build_receipt=lambda result: b"receipt",
            build_attempt_index=lambda result, receipt, attempt: b"index",
            publish_reserved_attempt=lambda reservation, result, receipt, index: (self.events.append("publish") or "published"),
            platform_probe=lambda selector, **kwargs: _platform_value(selector),
        )

    def invoke(self, deps: M._ExactAttemptDependencies) -> M.ExactAttemptRun:
        return M._run_exact_attempt_for_tests(
            self.root / "package",
            "attempt-001",
            platform_selector="wsl2-x86_64",
            ordinal=0,
            freeze_manifest=self.freeze,
            admission_record=self.admission,
            authorization_record=self.authorization,
            custody_record=self.custody,
            review_root=self.root / "reviews",
            candidate_identity={"closure": "fixture"},
            tool_identities=TOOLS,
            output_root=self.root / "output",
            work_root=self.root / "work",
            dependencies=deps,
        )

    def test_prechecks_and_reservation_precede_all_candidate_processes(self) -> None:
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda *args, **kwargs: None), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(self.deps())
        self.assertEqual(self.events[:8], ["preflight", "admission", "custody-static", "authorization", "prepare", "reserve", "custody", "factory-0"])
        self.assertEqual([item.role for item in result.prepared.transport], list(M.ROLE_ORDER))
        self.assertEqual([session.runs for session in self.sessions], [1, 1, 1])
        self.assertEqual(self.events.count("factory-0"), 1)
        self.assertEqual(self.events.count("factory-1"), 1)
        self.assertEqual(self.events.count("factory-2"), 1)
        self.assertEqual(self.events.count("adjudicate"), 1)
        self.assertEqual(self.events[-2:], ["publish", "reservation-close"])
        self.assertTrue(all(session.closed for session in self.sessions))
        for fd in self.cwd_fds:
            with self.assertRaises(OSError):
                __import__("os").fstat(fd)

    def test_production_custody_validator_projection_need_not_repeat_raw_self_hash(self) -> None:
        base = self.deps(fail_first=False)

        def production_validator(
            raw_or_record: bytes | dict[str, object], *, expected_manifest: bytes,
            expected_manifest_sha256: str | None = None, expected_manifest_hash: str | None = None,
            now: object | None = None,
        ) -> dict[str, object]:
            self.assertIsInstance(raw_or_record, bytes)
            self.assertIsInstance(expected_manifest, bytes)
            self.assertEqual(expected_manifest_sha256, "a" * 64)
            self.assertIsNone(expected_manifest_hash)
            self.assertIsNone(now)
            return {
                "selector": "wsl2-x86_64", "role": "wsl", "source_commit": CANDIDATE_COMMIT,
                "receipt": {}, "candidate": dict(FROZEN_BINARY), "transfer": {}, "manifest": {}, "binding": {},
            }

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "validate_custody_record": production_validator})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(deps)
        self.assertEqual(len(result.process_observations), 3)
        self.assertIn("publish", self.events)

    def test_attempt_work_is_absent_until_after_reservation(self) -> None:
        base = self.deps(fail_first=False)
        attempt_path = self.root / "work" / "attempt-001"
        checks: list[tuple[str, bool]] = []

        def preflight(*args: object, **kwargs: object) -> dict[str, object]:
            checks.append(("preflight", attempt_path.exists()))
            return base.preflight(*args, **kwargs)

        def authorization(*args: object, **kwargs: object) -> dict[str, object]:
            checks.append(("authorization", attempt_path.exists()))
            return base.validate_authorization(*args, **kwargs)

        def prepare(*args: object, **kwargs: object) -> Prepared:
            checks.append(("prepare", attempt_path.exists()))
            return Prepared()

        def reserve(*args: object, **kwargs: object) -> Reservation:
            checks.append(("reserve", attempt_path.exists()))
            return base.reserve_attempt(*args, **kwargs)

        deps = M._ExactAttemptDependencies(**{
            **base.__dict__, "preflight": preflight, "validate_authorization": authorization,
            "prepare": prepare, "reserve_attempt": reserve,
        })
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            self.invoke(deps)
        self.assertEqual(checks, [("preflight", False), ("authorization", False), ("prepare", False), ("reserve", False)])
        self.assertTrue(attempt_path.exists())

    def test_post_reservation_work_failure_consumes_marker(self) -> None:
        deps = self.deps()
        with mock.patch.object(M, "_prepare_work_locations", side_effect=M.ExactAttemptError("work", "synthetic work failure")), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertTrue(self.reservation.closed)
        self.assertTrue(self.reservation.marker_exists)
        self.assertNotIn("factory-0", self.events)

    def test_failed_first_role_does_not_retry_or_skip_later_roles(self) -> None:
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda *args, **kwargs: None), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(self.deps())
        self.assertEqual([session.role for session in self.sessions], list(M.ROLE_ORDER))
        self.assertEqual([session.runs for session in self.sessions], [1, 1, 1])
        self.assertEqual(len(result.process_observations), 3)

    def test_production_shaped_self_closing_sessions_are_not_closed_twice(self) -> None:
        base = self.deps(fail_first=False)

        class ProductionSession(Session):
            def __init__(inner_self, role: str) -> None:
                super().__init__(role, self.events, False)
                inner_self._closed = False

            def run(inner_self) -> dict[str, object]:
                result = super().run()
                inner_self.close()
                return result

            def close(inner_self) -> None:
                inner_self.close_calls += 1
                inner_self._closed = True
                inner_self.closed = True

        def factory(**kwargs: object) -> ProductionSession:
            del kwargs
            session = ProductionSession(M.ROLE_ORDER[len(self.sessions)])
            self.sessions.append(session)
            return session

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "transport_factory": factory})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            self.invoke(deps)
        self.assertEqual([session.close_calls for session in self.sessions], [1, 1, 1])
        self.assertTrue(all(getattr(session, "_closed") is True for session in self.sessions))

    def test_alternate_non_self_closing_sessions_are_closed_once(self) -> None:
        base = self.deps(fail_first=False)

        class AlternateSession(Session):
            def __init__(inner_self, role: str) -> None:
                super().__init__(role, self.events, False)
                inner_self._closed = False

            def close(inner_self) -> None:
                inner_self.close_calls += 1
                inner_self._closed = True
                inner_self.closed = True

        def factory(**kwargs: object) -> AlternateSession:
            del kwargs
            session = AlternateSession(M.ROLE_ORDER[len(self.sessions)])
            self.sessions.append(session)
            return session

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "transport_factory": factory})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            self.invoke(deps)
        self.assertEqual([session.close_calls for session in self.sessions], [1, 1, 1])

    def test_session_without_callable_close_is_rejected_before_run(self) -> None:
        base = self.deps(fail_first=False)
        made: list[object] = []

        class NoClose:
            def __init__(inner_self, role: str) -> None:
                inner_self.role = role
                inner_self.runs = 0

            def run(inner_self) -> dict[str, object]:
                inner_self.runs += 1
                raise AssertionError("invalid session must not run")

        def factory(**kwargs: object) -> NoClose:
            del kwargs
            session = NoClose(M.ROLE_ORDER[len(made)])
            made.append(session)
            return session

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "transport_factory": factory})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(deps)
        self.assertEqual([session.runs for session in made], [0, 0, 0])
        self.assertEqual([item["outcome"]["status"] for item in result.process_observations], ["inconclusive"] * 3)

    def test_one_sided_content_hash_mismatch_is_visible_and_failed(self) -> None:
        content = {"size": 4, "sha256": "b" * 64}
        requests = tuple(f"request-{index}".encode() for index in range(8))
        ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
        for field in ("content_initial", "content_pre_fork", "content_post_exec"):
            with self.subTest(field=field):
                result = {
                    "status": "supported", "requests": requests, "responses": (),
                    "launch": {"identity": "launch", field: content},
                    "output": EMPTY_OUTPUT,
                    "lifecycle": LIFECYCLE,
                }
                process = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "a" * 64, None)
                self.assertIsNone(process["candidate_binary"])
                self.assertEqual(process["execution_identity"][field], content)
                self.assertEqual(process["outcome"]["status"], "failed")
                self.assertIn(f"{field}-custody-mismatch", process["outcome"]["detail"])

    def test_all_null_execution_identity_becomes_missing_incomplete_field(self) -> None:
        requests = tuple(f"request-{index}".encode() for index in range(8))
        ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
        launch = {key: None for key in M.EXECUTION_IDENTITY_KEYS}
        result = {
            "status": "inconclusive", "requests": requests, "responses": (),
            "launch": launch, "output": EMPTY_OUTPUT,
            "lifecycle": LIFECYCLE,
        }
        process = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "a" * 64, None)
        self.assertIsNone(process["execution_identity"])
        self.assertIn("execution_identity", process["missing"])
        M.evidence_contract._process(process, 0, "wsl2-x86_64")

    def test_post_reservation_failure_consumes_marker_without_reuse(self) -> None:
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda *args, **kwargs: None), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(self.deps(fail_result=True))
        self.assertTrue(self.reservation.closed)
        self.assertTrue(self.reservation.marker_exists)
        self.assertIn("reservation-close", self.events)
        self.assertNotIn("publish", self.events)

    def test_invalid_reservation_is_rejected_before_factory(self) -> None:
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "reserve_attempt": lambda *args, **kwargs: None})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("factory-0", self.events)
        self.assertEqual(self.verified_closed, 0)

    def test_wrong_id_reservation_is_rejected_before_factory(self) -> None:
        invalid = Reservation(self.events)
        invalid.attempt_id = "attempt-wrong"
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "reserve_attempt": lambda *args, **kwargs: invalid})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("factory-0", self.events)
        self.assertTrue(invalid.closed)

    def test_alternate_experiment_slot_is_rejected_before_factory(self) -> None:
        invalid = Reservation(self.events)
        invalid.experiment_slot = {
            **invalid.experiment_slot,
            "ordinal": 1,
        }
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "reserve_attempt": lambda *args, **kwargs: invalid})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("factory-0", self.events)
        self.assertTrue(invalid.closed)

    def test_missing_experiment_slot_is_rejected_before_factory(self) -> None:
        invalid = Reservation(self.events)
        invalid.experiment_slot = None
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "reserve_attempt": lambda *args, **kwargs: invalid})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("factory-0", self.events)
        self.assertTrue(invalid.closed)

    def test_closed_reservation_is_rejected_before_factory(self) -> None:
        invalid = Reservation(self.events)
        invalid.closed = True
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "reserve_attempt": lambda *args, **kwargs: invalid})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("factory-0", self.events)

    def test_malformed_reservation_is_rejected_before_factory(self) -> None:
        class Malformed:
            attempt_id = "attempt-001"
            closed = False

        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "reserve_attempt": lambda *args, **kwargs: Malformed()})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("factory-0", self.events)

    def test_exact_attempt_metadata_and_fixed_transport_inputs(self) -> None:
        captured: dict[str, object] = {}
        deps = self.deps(fail_first=False)
        original_result = deps.build_result

        def capture(attempt: object, adjudications: object, processes: object, tools: object) -> bytes:
            captured.update({"attempt": attempt, "adjudications": adjudications, "processes": processes, "tools": tools})
            return original_result(attempt, adjudications, processes, tools)

        deps = M._ExactAttemptDependencies(**{**deps.__dict__, "build_result": capture})
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda *args, **kwargs: None), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            self.invoke(deps)
        self.assertEqual(captured["tools"], TOOLS[: len(RUNTIME_PATHS)])
        self.assertEqual(len(captured["adjudications"]), 60)
        self.assertEqual(captured["attempt"], {
            "freeze_manifest_sha256": "a" * 64,
            "attempt_id": "attempt-001",
            "platform_selector": "wsl2-x86_64",
            "ordinal": 0,
            "authorization_reference": "BEN-AUTH-001",
            "gate_b_admission_sha256": hashlib.sha256(self.admission).hexdigest(),
            "authorization_record_sha256": hashlib.sha256(self.authorization).hexdigest(),
            "custody_record_sha256": "c" * 64,
        })

    def test_malformed_or_partial_authoritative_records_fail_before_reservation(self) -> None:
        deps = self.deps()
        malformed = self.freeze[:-2] + b"x\n"
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda *args, **kwargs: None), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            self.freeze = malformed
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_unpatched_manifest_only_authority_interface_is_used(self) -> None:
        calls: list[object] = []
        deps = self.deps(fail_first=False)
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda manifest: calls.append(manifest)), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            self.invoke(deps)
        self.assertEqual(len(calls), 1)

    def test_factory_failure_has_absent_transport_and_exact_missing_fields(self) -> None:
        def factory(**kwargs: object) -> object:
            raise RuntimeError("factory did not launch")
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "transport_factory": factory})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(deps)
        for process in result.process_observations:
            self.assertIsNone(process["transport"]["requests"])
            self.assertIsNone(process["transport"]["responses"])
            self.assertIn("transport.requests", process["missing"])
            self.assertIn("transport.responses", process["missing"])

    def test_actual_short_request_prefix_is_retained(self) -> None:
        base = self.deps(fail_first=False)

        class ShortSession(Session):
            def run(inner_self) -> dict[str, object]:
                inner_self.events.append("run-short")
                return {
                    "status": "inconclusive",
                    "code": "short",
                    "detail": "one admitted request",
                    "requests": (b"request-0",),
                    "responses": (),
                    "lifecycle": LIFECYCLE,
                    "output": EMPTY_OUTPUT,
                }

        def factory(**kwargs: object) -> object:
            role = M.ROLE_ORDER[len(self.sessions)]
            session = ShortSession(role, self.events, False) if not self.sessions else Session(role, self.events, False)
            self.sessions.append(session)
            return session
        deps = M._ExactAttemptDependencies(**{**base.__dict__, "transport_factory": factory})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(deps)
        first = result.process_observations[0]
        self.assertEqual(first["transport"]["requests"]["count"], 1)
        self.assertEqual(first["transport"]["responses"]["count"], 0)
        self.assertIn("p3-attempt-001-000", first["output"]["missing"])

    def test_malformed_response_is_retained_as_output_and_published(self) -> None:
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            result = self.invoke(self.deps(fail_first=False))
        self.assertEqual(len(result.process_observations), 3)
        self.assertTrue(any("malformed-response" in process["output"]["extra"] for process in result.process_observations if process["output"] is not None))
        self.assertIn("publish", self.events)

    def test_missing_final_fp_is_incomplete_without_pre_substitution(self) -> None:
        fe = {
            "x87_control_word": "0x037f", "mxcsr": "0x00001f80",
            "x87_rounding_mode": "nearest", "mxcsr_rounding_mode": "nearest",
            "x87_exception_masks": 63, "mxcsr_exception_masks": 63,
            "x87_flags": 0, "mxcsr_flags": 0, "ftz": False, "daz": False,
        }
        requests = (b"request-0",) * 8
        ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
        result = {
            "status": "supported", "requests": requests, "responses": (),
            "launch": {"identity": "launch", "observation": fe},
            "lifecycle": LIFECYCLE,
            "output": EMPTY_OUTPUT,
            "final_observation": None,
        }
        process = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "f" * 64, None)
        self.assertEqual(process["variant"], "incomplete-v1")
        self.assertIsNone(process["fe_mxcsr"])
        self.assertIn("fe-pre-observed-final-missing", process["outcome"]["detail"])
        self.assertEqual(process["outcome"]["status"], "inconclusive")

    def test_execution_identity_is_retained_and_cwd_mismatch_fails(self) -> None:
        descriptor = {"device": 1, "inode": 2, "mode": 0o755, "size": 0, "nlink": 1}
        content = {"size": 4, "sha256": "a" * 64}
        identity_launch = {
            "identity": "launch", "observation": None,
            "descriptor_pre": descriptor, "descriptor_post_exe": descriptor,
            "descriptor_post_fd": descriptor, "cwd_pre": descriptor, "cwd_post": descriptor,
            "content_initial": content, "content_pre_fork": content, "content_post_exec": content,
            "seals_initial": 1, "seals_pre_fork": 1, "seals_post_exec": 1,
        }
        requests = tuple(f"request-{index}".encode() for index in range(8))
        ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
        result = {"status": "supported", "requests": requests, "responses": (), "launch": identity_launch, "output": EMPTY_OUTPUT, "lifecycle": LIFECYCLE, "candidate_binary": {"sha256_pre": "a" * 64, "sha256_post": "a" * 64}}
        process = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "a" * 64, descriptor)
        self.assertEqual(process["execution_identity"]["cwd_pre"], descriptor)
        self.assertEqual(process["execution_identity"]["content_post_exec"], content)
        self.assertEqual(process["outcome"]["status"], "inconclusive")
        mismatched = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "a" * 64, {**descriptor, "inode": 99})
        self.assertEqual(mismatched["outcome"]["status"], "failed")
        self.assertIn("cwd_pre-mismatch", mismatched["outcome"]["detail"])

    def test_prepared_real_stat_identity_matches_transport_normalization(self) -> None:
        role_dir = self.root / "real-role"
        role_dir.mkdir()
        fd, prepared = M._open_anchored_directory(role_dir, "real role")
        try:
            raw = os.fstat(fd)
            normalized = M.transport._directory_identity(fd).to_dict()
            self.assertEqual(prepared, normalized)
            self.assertEqual(prepared["size"], 0)
            self.assertEqual(prepared["nlink"], 0)
            self.assertTrue(raw.st_size >= 0)
            self.assertTrue(raw.st_nlink >= 1)

            requests = tuple(f"request-{index}".encode() for index in range(8))
            ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
            result = {
                "status": "supported", "requests": requests, "responses": (),
                "launch": {"identity": "launch", "cwd_pre": normalized, "cwd_post": normalized},
                "output": EMPTY_OUTPUT,
                "lifecycle": LIFECYCLE,
                "candidate_binary": {"sha256_pre": "a" * 64, "sha256_post": "a" * 64},
            }
            process = M._process_observation("development", role_dir, requests, ids, None, result, _platform_value(), "a" * 64, prepared)
            self.assertNotIn("cwd_pre-mismatch", process["outcome"]["detail"])
            self.assertNotIn("cwd_post-mismatch", process["outcome"]["detail"])
            mismatched = M._process_observation(
                "development", role_dir, requests, ids, None, result, _platform_value(), "a" * 64,
                {**prepared, "inode": prepared["inode"] + 1},
            )
            self.assertEqual(mismatched["outcome"]["status"], "failed")
            self.assertIn("cwd_pre-mismatch", mismatched["outcome"]["detail"])
        finally:
            os.close(fd)

    def test_wrong_stable_candidate_hash_is_visible_and_failed(self) -> None:
        descriptor = {"device": 1, "inode": 2, "mode": 0o755, "size": 0, "nlink": 1}
        content = {"size": 4, "sha256": "b" * 64}
        launch = {"identity": "launch", "content_initial": content, "content_post_exec": content}
        requests = tuple(f"request-{index}".encode() for index in range(8))
        ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
        result = {"status": "supported", "requests": requests, "responses": (), "launch": launch, "output": {"missing": [], "extra": [], "trailing": []}}
        process = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "a" * 64, descriptor)
        self.assertEqual(process["candidate_binary"], {"sha256_pre": "b" * 64, "sha256_post": "b" * 64})
        self.assertEqual(process["outcome"]["status"], "failed")
        self.assertIn("candidate-binary-custody-mismatch", process["outcome"]["detail"])

    def test_malformed_metadata_salvages_independent_observations(self) -> None:
        fe = {
            "x87_control_word": "0x037f", "mxcsr": "0x00001f80",
            "x87_rounding_mode": "nearest", "mxcsr_rounding_mode": "nearest",
            "x87_exception_masks": 63, "mxcsr_exception_masks": 63,
            "x87_flags": 0, "mxcsr_flags": 0, "ftz": False, "daz": False,
        }
        requests = tuple(f"request-{index}".encode() for index in range(8))
        ids = tuple(f"p3-attempt-001-{index:03d}" for index in range(8))
        result = {
            "status": "supported", "requests": requests, "responses": (),
            "launch": {
                "identity": "launch",
                "observation": fe,
                "content_initial": {"sha256": "a" * 64},
                "content_post_exec": {"sha256": "a" * 64},
            },
            "final_observation": fe,
            "candidate_binary": {"sha256_pre": "bad", "sha256_post": "bad"},
            "fe_mxcsr": "malformed-fe-field",
            "lifecycle": LIFECYCLE,
            "output": EMPTY_OUTPUT,
        }
        process = M._process_observation("development", self.root, requests, ids, None, result, _platform_value(), "a" * 64, None)
        self.assertEqual(process["variant"], "incomplete-v1")
        self.assertEqual(process["candidate_binary"], {"sha256_pre": "a" * 64, "sha256_post": "a" * 64})
        self.assertEqual(process["fe_mxcsr"]["pre"], fe)
        self.assertEqual(process["lifecycle"], result["lifecycle"])
        self.assertEqual(process["platform"], _platform_value())
        self.assertIsNotNone(process["output"])
        self.assertIn("invalid-fe-metadata", process["outcome"]["detail"])

    def test_platform_mismatch_happens_before_reservation(self) -> None:
        deps = M._ExactAttemptDependencies(**{
            **self.deps().__dict__,
            "platform_probe": lambda selector, **kwargs: {"selector": "ubuntu-24.04-x86_64"},
        })
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_public_aliases_have_no_dependency_substitution_surface(self) -> None:
        import inspect
        for alias in (M.run_exact_attempt, M.execute_exact_attempt, M.orchestrate_exact_attempt, M.run, M.execute, M.exact_attempt):
            self.assertNotIn("dependencies", inspect.signature(alias).parameters)
            with self.assertRaises(TypeError):
                alias("package", "attempt", platform_selector="wsl2-x86_64", ordinal=0,
                      freeze_manifest=b"", admission_record=b"",
                      authorization_record=b"", custody_record=b"", review_root="reviews",
                      candidate_identity={}, tool_identities=[], output_root="output", work_root="work",
                      dependencies=self.deps())

    def test_production_reservation_dependency_is_experiment_slot_api(self) -> None:
        self.assertIs(M._ExactAttemptDependencies().reserve_attempt, M.publication.reserve_experiment_slot)

    def test_v3_freeze_is_blocked_without_authenticated_runtime_contract(self) -> None:
        with self.assertRaises(M.ExactAttemptError) as error:
            M._validate_frozen_runtime_contract(json.loads(self.freeze), "wsl2-x86_64")
        self.assertEqual(error.exception.code, "runtime-contract")

    def test_runtime_contract_requires_three_ascii_numeric_version_components(self) -> None:
        freeze = json.loads(self.freeze)
        freeze[M.PYTHON_RUNTIME_CONTRACT_FIELD] = {
            "schema": M.PYTHON_RUNTIME_CONTRACT_SCHEMA,
            "platforms": {
                selector: {
                    "selector": selector,
                    "implementation": "cpython",
                    "version": "3.12.x" if selector == "wsl2-x86_64" else "3.12.4",
                    "invocation": ["python3"],
                    "module_loading": "PYTHONPATH=package/scripts",
                    "entrypoint": "python3 -m phase3_exact_attempt",
                }
                for selector in M.PLATFORM_ORDINALS
            },
        }
        with self.assertRaises(M.ExactAttemptError) as error:
            M._validate_frozen_runtime_contract(freeze, "wsl2-x86_64")
        self.assertEqual(error.exception.code, "runtime-contract")

    def test_selected_frozen_binary_sizes_and_cap_are_checked_before_reservation(self) -> None:
        self.assertEqual(M.MAX_EXECUTABLE_BYTES, M.transport.MAX_EXECUTABLE_BYTES)
        self.assertEqual(M.MAX_EXECUTABLE_BYTES, M.evidence_contract.MAX_EXECUTABLE_BYTES)
        freeze = json.loads(_freeze_value())
        for selector, size, digest in (
            ("wsl2-x86_64", 100_944_288, "f" * 64),
            ("ubuntu-24.04-x86_64", 100_945_304, "e" * 64),
        ):
            selected = M._validate_selected_binary_compatibility(
                freeze, selector, {"candidate": {"bytes": size, "mode": 0o100755, "sha256": digest}},
            )
            self.assertEqual(selected, {"bytes": size, "mode": 0o100755, "sha256": digest})
        freeze["binaries"]["wsl2-x86_64"]["binary_identity"]["bytes"] = 100_945_305
        with self.assertRaises(M.ExactAttemptError):
            M._validate_selected_binary_compatibility(
                freeze, "wsl2-x86_64", {"candidate": {"bytes": 100_945_305, "mode": 0o100755, "sha256": "f" * 64}},
            )

    def test_lifecycle_accepts_only_finite_nonnegative_rusage(self) -> None:
        keys = (
            "user_seconds", "system_seconds", "max_rss", "minor_faults",
            "major_faults", "involuntary_context_switches", "voluntary_context_switches",
        )
        usage = {key: float(index) + 0.5 for index, key in enumerate(keys)}
        lifecycle = M._valid_lifecycle({**LIFECYCLE, "rusage": usage})
        self.assertIsNotNone(lifecycle)
        self.assertEqual(lifecycle["rusage"], usage)  # type: ignore[index]
        for key, bad in (
            ("user_seconds", math.nan),
            ("system_seconds", math.inf),
            ("max_rss", -1),
            ("minor_faults", "not-a-number"),
            ("major_faults", True),
        ):
            malformed = {**usage, key: bad}
            self.assertIsNone(M._valid_lifecycle({**LIFECYCLE, "rusage": malformed}))
        missing = dict(usage)
        del missing["major_faults"]
        self.assertIsNone(M._valid_lifecycle({**LIFECYCLE, "rusage": missing}))
        extra = {**usage, "unexpected": 1}
        self.assertIsNone(M._valid_lifecycle({**LIFECYCLE, "rusage": extra}))

    def test_static_candidate_mismatch_is_rejected_before_reservation(self) -> None:
        base = self.deps()

        def mismatched_static_custody(*args: object, **kwargs: object) -> dict[str, object]:
            value = base.validate_custody_record(*args, **kwargs)
            value["candidate"] = {**value["candidate"], "bytes": 100_945_304, "sha256": "e" * 64}
            return value

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "validate_custody_record": mismatched_static_custody})
        with self.assertRaises(M.ExactAttemptError):
            self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_missing_runtime_platform_facts_are_rejected_before_reservation(self) -> None:
        base = self.deps()

        def missing_runtime(selector: str, **kwargs: object) -> dict[str, object]:
            value = _platform_value(selector)
            value["runtime"] = None
            return value

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "platform_probe": missing_runtime})
        with self.assertRaises(M.ExactAttemptError):
            self.invoke(deps)
        self.assertNotIn("reserve", self.events)
        self.assertEqual(self.verified_closed, 0)

    def test_platform_missing_key_fails_before_factory(self) -> None:
        missing = _platform_value()
        del missing["compiler"]
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "platform_probe": lambda selector, **kwargs: missing})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)
        self.assertNotIn("factory-0", self.events)

    def test_platform_extra_key_fails_before_factory(self) -> None:
        extra = {**_platform_value(), "unregistered": "value"}
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "platform_probe": lambda selector, **kwargs: extra})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)
        self.assertNotIn("factory-0", self.events)

    def test_preflight_report_requires_current_full_tool_closure(self) -> None:
        base = self.deps()

        def missing_tools(*args: object, **kwargs: object) -> dict[str, object]:
            report = base.preflight(*args, **kwargs)
            report.pop("tool_identities", None)
            return report

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "preflight": missing_tools})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_preflight_report_collection_mismatch_fails_closed(self) -> None:
        base = self.deps()

        def mismatched(*args: object, **kwargs: object) -> dict[str, object]:
            report = base.preflight(*args, **kwargs)
            report["execution_package"]["runtime_tool_identities"] = []
            return report

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "preflight": mismatched})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_preflight_source_snapshot_attestation_is_required(self) -> None:
        base = self.deps()

        def missing_attestation(*args: object, **kwargs: object) -> dict[str, object]:
            report = base.preflight(*args, **kwargs)
            report["execution_package"].pop("source_snapshot_validation", None)
            return report

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "preflight": missing_attestation})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_preflight_source_snapshot_attestation_mismatch_fails_closed(self) -> None:
        base = self.deps()

        def mismatched_attestation(*args: object, **kwargs: object) -> dict[str, object]:
            report = base.preflight(*args, **kwargs)
            report["execution_package"]["source_snapshot_validation"]["current_execution_tool_identity_count"] = len(TOOLS) - 1
            return report

        deps = M._ExactAttemptDependencies(**{**base.__dict__, "preflight": mismatched_attestation})
        with mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(deps)
        self.assertNotIn("reserve", self.events)

    def test_entrypoint_has_no_implicit_launch_controls(self) -> None:
        import inspect
        parameters = inspect.signature(M.run_exact_attempt).parameters
        self.assertNotIn("candidate_path", parameters)
        self.assertNotIn("argv", parameters)
        self.assertNotIn("retry", parameters)
        self.assertNotIn("process_count", parameters)

    def test_bad_cohort_closes_custody_before_reservation(self) -> None:
        class BadPrepared:
            transport = (Cohort("development", M.ROLE_REQUEST_COUNTS["development"]),)
        deps = M._ExactAttemptDependencies(**{**self.deps().__dict__, "prepare": lambda *args, **kwargs: BadPrepared()})
        with self.assertRaises(M.ExactAttemptError):
            self.invoke(deps)
        self.assertNotIn("reserve", self.events)
        self.assertEqual(self.verified_closed, 0)

        self.events.clear()
        self.freeze = _canonical({"manifest_sha256": "a" * 64})
        with mock.patch.object(M.authority, "validate_required_exact_runtime_tools", lambda *args, **kwargs: None), mock.patch.object(M, "_read_candidate_descriptor", return_value=b"candidate"):
            with self.assertRaises(M.ExactAttemptError):
                self.invoke(M._ExactAttemptDependencies(**{**deps.__dict__, "preflight": lambda *args: {"execution_permitted": False}, "build_result": deps.build_result}))
        self.assertNotIn("reserve", self.events)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Focused synthetic tests for the EXP-0002 frozen-corpus runner."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_adapter as runner  # noqa: E402
from runner_common import (  # noqa: E402
    EVALUATION_BINDING,
    FRAME_BYTES,
    MAX_CASES_PER_CORPUS,
    MAX_WIRE_REQUEST_ID_BYTES,
    PROTOCOL_ID,
    PREREGISTERED_LIMITS,
    ProtocolError,
    TECHNOLOGY_RESULT,
    parse_bits,
    parse_json_bytes,
    frame_json,
)
from runner_oracle import oracle_case  # noqa: E402
from runner_schema import STABLE_ERROR_CODES, load_manifest, validate_case  # noqa: E402
from runner_transport import (  # noqa: E402
    STDERR_TOTAL_CAP,
    STDOUT_TOTAL_CAP,
    BoundedSubprocessSession,
    CloseResult,
    TransportError,
)


SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER = SCRIPT_DIR / "run_adapter.py"
_CANDIDATE_TEMPS: list[tempfile.TemporaryDirectory[str]] = []


def _response_script(body: str) -> Path:
    temporary = tempfile.TemporaryDirectory(prefix="ck2-candidate-")
    _CANDIDATE_TEMPS.append(temporary)
    path = Path(temporary.name) / "candidate.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def tearDownModule() -> None:
    for temporary in _CANDIDATE_TEMPS:
        temporary.cleanup()


def _record(case_id: str, wire_id: str, operation: str, input_value: dict[str, object], expected: dict[str, object], *, request_raw: str | None = None) -> dict[str, object]:
    record: dict[str, object] = {
        "case_id": case_id,
        "wire_request_id": wire_id,
        "family": operation,
        "operation": operation,
        "expected": expected,
        "relations": [],
    }
    if request_raw is None:
        record["input"] = input_value
    else:
        record["request_raw"] = request_raw
    return record


def _write_package(root: Path, records: dict[str, list[dict[str, object]]], relations: list[dict[str, object]] | None = None, *, full_claims: bool = False) -> Path:
    records = {role: list(values) for role, values in records.items()}
    relation_values = [dict(value) for value in (relations or [])]
    if full_claims:
        if len(relation_values) > 26:
            raise ValueError("full synthetic claim fixture cannot exceed 26 relations")
        relation_ids = {str(relation["id"]) for relation in relation_values}
        if len(relation_ids) != len(relation_values):
            raise ValueError("full synthetic claim fixture requires unique relation IDs")
        all_records = records["development"] + records["held-out"] + records["adversarial"]
        if len(all_records) > 49:
            raise ValueError("full synthetic claim fixture cannot exceed 49 cases")
        for index in range(49 - len(all_records)):
            filler = _decimal_record()
            filler["case_id"] = f"synthetic_case_{index:02d}"
            filler["wire_request_id"] = f"synthetic_wire_{index:032x}"
            records["development"].append(filler)
        all_records = records["development"] + records["held-out"] + records["adversarial"]
        filler_relation_count = 26 - len(relation_values)
        synthetic_relation_index = 0
        for index in range(filler_relation_count):
            relation_id = f"synthetic-relation-{synthetic_relation_index:02d}"
            while relation_id in relation_ids:
                synthetic_relation_index += 1
                relation_id = f"synthetic-relation-{synthetic_relation_index:02d}"
            synthetic_relation_index += 1
            relation_ids.add(relation_id)
            member = all_records[index % len(all_records)]
            relation_values.append({"id": relation_id, "cases": [str(member["case_id"])], "meaning": "synthetic full-claim fixture"})
            member["relations"] = list(member["relations"]) + [relation_id]
        relation_ids = [str(relation["id"]) for relation in relation_values]
        for index, record in enumerate(all_records):
            if not record["relations"]:
                relation_id = relation_ids[index % len(relation_ids)]
                record["relations"] = [relation_id]
                next(relation for relation in relation_values if relation["id"] == relation_id)["cases"].append(str(record["case_id"]))
    manifest: dict[str, object] = {
        "manifest_version": "ck.r3.numeric-corpus-manifest-1",
        "experiment_id": "EXP-0002",
        "lifecycle": "frozen-inputs-unrun",
        "evaluation_binding": EVALUATION_BINDING,
        "preregistration": {
            "identity": {
                "candidate_artifacts": "stream-hashed-before-and-after-execution",
                "runner_modules": "stream-hashed-before-and-after-execution",
                "filesystem_assumption": "controlled-local-no-adversarial-mid-run-replace-and-restore",
                "candidate_build_context": "observational-not-provenance",
            },
            "topology": {
                "candidate_processes": 1,
                "persistent_process": True,
                "corpus_sequence": ["development", "held-out", "adversarial"],
                "held_out_role": "non-tuning-not-blind-or-process-isolated",
                "environment_observations": "workload-position-conditioned",
                "fresh_process_claim": False,
                "order_independence_claim": False,
                "repeatability_claim": False,
                "generalization_claim": False,
                "profile_claim": False,
                "technology_claim": False,
            },
            "claim_domain": {
                "kind": "exact-artifact-agreement",
                "case_count": 49,
                "relation_count": 26,
                "scope": "49 exact frozen case adjudications plus runner classifications for 26 registered named case groups; only relation IDs with explicit cross-case checks make the narrower predicate; other groupings organize member-case outcomes",
                "production_domain_claim": False,
            },
            "limits": dict(PREREGISTERED_LIMITS),
            "tolerance_bindings": ["exp-zero", "exp-ulp52-absolute", "exp-minsub-absolute", "exp-ulp52-relative", "exp-pre-ulp52-relative"],
            "classification": {
                "exact_expected_mismatch": "completed-failed-conformance-evidence",
                "environment_failed_or_unsupported": "inconclusive-capability-evidence",
                "candidate_unsupported": "inconclusive-capability-evidence",
                "transport_nonzero_or_response_integrity": "incomplete",
                "profile_selection": "none",
                "technology_result": TECHNOLOGY_RESULT,
            },
        },
        "candidate_request_protocol": "ck.r3.numeric-candidate-request-1",
        "candidate_response_protocol": "ck.r3.numeric-candidate-response-1",
        "operations": ["decimal-admission", "scalar-comparison", "translation-comparison", "environment-attestation"],
        "corpus_order": ["development.jsonl", "held-out.jsonl", "adversarial.jsonl"],
        "experimental_tolerances": {
            "exp-zero": {"absolute_bits": "0x0000000000000000", "relative_bits": "0x0000000000000000", "role": "synthetic"},
            "exp-ulp52-absolute": {"absolute_bits": "0x3cb0000000000000", "relative_bits": "0x0000000000000000", "role": "synthetic"},
            "exp-minsub-absolute": {"absolute_bits": "0x0000000000000001", "relative_bits": "0x0000000000000000", "role": "synthetic"},
            "exp-ulp52-relative": {"absolute_bits": "0x0000000000000000", "relative_bits": "0x3cb0000000000000", "role": "synthetic"},
            "exp-pre-ulp52-relative": {"absolute_bits": "0x0000000000000000", "relative_bits": "0x3caffffffffffffe", "role": "synthetic"},
        },
        "record_shape": {
            "required": ["case_id", "wire_request_id", "family", "operation", "expected", "relations"],
            "request_member": "exactly one of input or request_raw",
            "candidate_projection": {
                "valid": {
                    "protocol_id": "ck.r3.numeric-candidate-request-1",
                    "request_id": "wire_request_id",
                    "operation": "operation",
                    "input": "input",
                },
                "raw": "request_raw",
            },
            "runner_only": ["case_id", "wire_request_id", "family", "expected", "relations"],
        },
        "result_shape": {
            "required": ["protocol_id", "status"],
            "optional": ["request_id", "observations", "error"],
            "transport_statuses": ["observed", "rejected", "resource-limit", "unsupported", "error"],
            "candidate_adjudication": "none",
        },
        "error_codes": {code: code for code in STABLE_ERROR_CODES},
        "corpora": [],
        "relations": relation_values,
        "disjointness": {
            "case_ids": "unique across all roles",
            "record_bytes": "no complete JSONL line is shared across roles",
            "candidate_request_bytes": "opaque wire IDs make projections distinct",
        },
        "run_state": {
            "corpus_run": "not-run",
            "candidate_evaluation": "not performed",
            "profile_binding": None,
            "technology_result": TECHNOLOGY_RESULT,
        },
    }
    for order, role in enumerate(("development", "held-out", "adversarial"), 1):
        path = root / f"{role}.jsonl"
        payload = b"".join(json.dumps(record, separators=(",", ":")).encode() + b"\n" for record in records[role])
        path.write_bytes(payload)
        family_counts: dict[str, int] = {}
        for record in records[role]:
            family = str(record["family"])
            family_counts[family] = family_counts.get(family, 0) + 1
        manifest["corpora"].append(
            {
                "order": order,
                "role": role,
                "path": path.name,
                "count": len(records[role]),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "family_counts": family_counts,
                "case_ids": [record["case_id"] for record in records[role]],
            }
        )
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _scalar_input() -> dict[str, object]:
    return {
        "absolute_bits": "0x0000000000000000",
        "relative_bits": "0x0000000000000000",
        "left_bits": "0x3ff0000000000000",
        "right_bits": "0x3ff0000000000000",
    }


def _decimal_record() -> dict[str, object]:
    return _record(
        "case_decimal",
        "wire_91d4c6b7e8a2035f",
        "decimal-admission",
        {"token": "0.1", "max_token_bytes": "512", "max_significant_digits": "128", "max_exponent_abs": "10000"},
        {"status": "observed", "observations": {"bits": "0x3fb999999999999a"}},
    )


class RunnerTests(unittest.TestCase):
    def test_strict_json_and_stable_error_codes(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_json_bytes(b'{"a":1,"a":2}')
        with self.assertRaises(ProtocolError):
            parse_json_bytes(b'{"a":{"b":1,"b":2}}')
        with self.assertRaises(ProtocolError):
            parse_json_bytes(b'{"a":NaN}')
        with self.assertRaises(ProtocolError):
            parse_bits("0x7ff0000000000000", "bits")
        self.assertIsNone(runner._candidate_error_code("invalid JSON number token"))
        self.assertEqual(runner._candidate_error_code("invalid-json-number"), "invalid-json-number")

    def test_response_status_member_algebra_rejects_ambiguous_shapes(self) -> None:
        base = {"protocol_id": runner.RESPONSE_PROTOCOL_ID, "status": "unsupported"}
        with self.assertRaises(ProtocolError):
            runner._validate_response_shape(dict(base, observations={}))
        with self.assertRaises(ProtocolError):
            runner._validate_response_shape({"protocol_id": runner.RESPONSE_PROTOCOL_ID, "status": "error"})
        with self.assertRaises(ProtocolError):
            runner._validate_response_shape({"protocol_id": runner.RESPONSE_PROTOCOL_ID, "status": "observed"})
        self.assertEqual(runner._validate_response_shape(base)["status"], "unsupported")

    def test_decimal_and_dyadic_oracles_are_exact_and_bounded(self) -> None:
        _, expected, work = oracle_case("decimal-admission", {"token": "1.00000000000000011102230246251565404236316680908203125", "max_token_bytes": "512", "max_significant_digits": "400", "max_exponent_abs": "10000"})
        self.assertEqual(expected["observations"]["bits"], "0x3ff0000000000000")
        self.assertGreater(work, 0)
        _, expected, _ = oracle_case("decimal-admission", {"token": "2.4703282292062326e-324", "max_token_bytes": "512", "max_significant_digits": "400", "max_exponent_abs": "10000"})
        self.assertEqual(expected["error_code"], "nonzero-underflow-to-zero")
        scalar = _scalar_input()
        scalar["right_bits"] = "0x3ff0000000000001"
        oracle, expected, _ = oracle_case("scalar-comparison", scalar)
        self.assertFalse(oracle["predicate"])
        self.assertFalse(expected["observations"]["predicate"])

    def test_case_projection_is_sanitized_and_raw_duplicate_is_runner_owned(self) -> None:
        record = _decimal_record()
        _, request_bytes, _ = validate_case(record)
        request = parse_json_bytes(request_bytes)
        self.assertEqual(set(request), {"protocol_id", "request_id", "operation", "input"})
        self.assertNotIn("expected", request)
        raw_id = "wire_44a0d91c6e7f2385"
        raw = '{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"' + raw_id + '","operation":"decimal-admission","operation":"decimal-admission","input":{}}'
        malformed = _record("case_raw", raw_id, "decimal-admission", {}, {"status": "error", "error_code": "malformed-request"}, request_raw=raw)
        _, projected, info = validate_case(malformed)
        self.assertEqual(projected, raw.encode() + b"\n")
        self.assertIsNone(info["request_id"])

    def test_wire_request_id_boundary_and_runner_identity_cap(self) -> None:
        boundary_id = "é" * (MAX_WIRE_REQUEST_ID_BYTES // 2)
        boundary = _decimal_record()
        boundary["wire_request_id"] = boundary_id
        _, request_bytes, _ = validate_case(boundary)
        self.assertEqual(parse_json_bytes(request_bytes)["request_id"], boundary_id)

        oversized = dict(boundary, wire_request_id=boundary_id + "a")
        with self.assertRaises(ProtocolError):
            validate_case(oversized)

        wrong_protocol_raw = json.dumps(
            {"protocol_id": "wrong-protocol", "request_id": boundary_id, "operation": "decimal-admission", "input": {}},
            separators=(",", ":"),
            ensure_ascii=False,
        )
        raw_boundary = _record("case_raw_boundary", boundary_id, "decimal-admission", {}, {"status": "error", "error_code": "malformed-request"}, request_raw=wrong_protocol_raw)
        validate_case(raw_boundary)
        raw_oversized_id = boundary_id + "a"
        raw_oversized = _record(
            "case_raw_oversized",
            raw_oversized_id,
            "decimal-admission",
            {},
            {"status": "error", "error_code": "malformed-request"},
            request_raw=json.dumps({"protocol_id": "wrong-protocol", "request_id": raw_oversized_id, "operation": "decimal-admission", "input": {}}, separators=(",", ":"), ensure_ascii=False),
        )
        with self.assertRaises(ProtocolError):
            validate_case(raw_oversized)

        identity = runner._runner_identity()
        self.assertEqual(identity["caps"]["wire_request_id_bytes"], MAX_WIRE_REQUEST_ID_BYTES)
        self.assertEqual(len(identity["bundle_sha256"]), 64)
        self.assertEqual(identity["budgets"]["max_identity_artifact_bytes"], 268_435_456)

    def test_stream_identity_is_capped_and_detects_changed_after_capture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-identity-") as temp:
            path = Path(temp) / "artifact"
            path.write_bytes(b"abcd")
            with patch.dict(runner.PREREGISTERED_LIMITS, {"max_identity_artifact_bytes": 3}):
                with self.assertRaises(ProtocolError):
                    runner._stream_file_identity(path)
            with patch.dict(runner.PREREGISTERED_LIMITS, {"max_identity_artifact_bytes": 32}):
                before = runner._stream_file_identity(path)
                path.write_bytes(b"changed")
                observed, failures = runner._recheck_bound_files([before])
            self.assertTrue(observed)
            self.assertTrue(failures)

    def test_path_spelled_candidate_launches_resolved_executable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-path-candidate-") as temp:
            root = Path(temp)
            first_dir = root / "first"
            second_dir = root / "second"
            first_dir.mkdir()
            second_dir.mkdir()
            for directory, marker in ((first_dir, "first"), (second_dir, "second")):
                candidate = directory / "phase-candidate"
                candidate.write_text(f"#!{sys.executable}\nimport sys\nfor _line in sys.stdin:\n    print({marker!r}, flush=True)\n", encoding="utf-8")
                candidate.chmod(0o755)
            with patch.dict(os.environ, {"PATH": str(first_dir)}):
                execution_command, executable, _digest, _artifacts = runner._resolve_candidate_executable(["phase-candidate", "--flag"])
            self.assertEqual(executable, (first_dir / "phase-candidate").resolve())
            self.assertEqual(execution_command, [str(executable), "--flag"])
            with patch.dict(os.environ, {"PATH": str(second_dir)}):
                session = BoundedSubprocessSession(execution_command)
                try:
                    response = session.request({"protocol_id": PROTOCOL_ID, "request_id": "x", "operation": "scalar-comparison", "input": {}})
                finally:
                    session.close()
            self.assertIn(b"first", response)

    def test_environment_control_algebra_and_inconclusive_shape(self) -> None:
        base = {"target": "x86_64-unknown-linux-gnu", "status": "passed", "rounding_mode": 0, "mxcsr": "0x00001f80", "mxcsr_rounding_mode": 0, "ftz_enabled": False, "daz_enabled": False, "failure_classification": "none", "scope": "single-threaded-jsonl-loop"}
        self.assertEqual(runner._validate_environment_observation(base), "passed")
        unsupported = dict(base, target="unsupported-target", status="unsupported", rounding_mode=None, mxcsr=None, mxcsr_rounding_mode=None, ftz_enabled=None, daz_enabled=None, failure_classification="unsupported-target")
        self.assertEqual(runner._validate_environment_observation(unsupported), "unsupported")
        failed = dict(base, status="failed", failure_classification="ftz-enabled", mxcsr="0x00009f80", ftz_enabled=True)
        self.assertEqual(runner._validate_environment_observation(failed), "failed")
        failed_daz = dict(base, status="failed", failure_classification="daz-enabled", mxcsr="0x00001fc0", daz_enabled=True)
        self.assertEqual(runner._validate_environment_observation(failed_daz), "failed")
        failed_rounding = dict(base, status="failed", failure_classification="wrong-rounding-mode", rounding_mode=1)
        self.assertEqual(runner._validate_environment_observation(failed_rounding), "failed")
        unavailable = dict(base, status="failed", failure_classification="rounding-mode-unavailable", rounding_mode=-1)
        self.assertEqual(runner._validate_environment_observation(unavailable), "failed")
        with self.assertRaises(ProtocolError):
            runner._validate_environment_observation(dict(unsupported, ftz_enabled=False))
        with self.assertRaises(ProtocolError):
            runner._validate_environment_observation(dict(failed, failure_classification="daz-enabled"))
        with self.assertRaises(ProtocolError):
            runner._validate_environment_observation(dict(base, status=[]))
        with self.assertRaises(ProtocolError):
            runner._validate_environment_observation(dict(base, failure_classification={}))
        with self.assertRaises(ProtocolError):
            runner._validate_environment_observation(dict(base, target="synthetic"))
        with self.assertRaises(ProtocolError):
            runner._validate_environment_observation(dict(unsupported, target="unsupported"))
        raw = frame_json({"protocol_id": runner.RESPONSE_PROTOCOL_ID, "request_id": "wire-1", "status": "observed", "observations": failed})
        classification, _, failure = runner.adjudicate_response("environment-attestation", "wire-1", {"status": "observed"}, raw)
        self.assertEqual(classification, "inconclusive")
        self.assertIn("failed", failure)

    def test_environment_repeat_ignores_sticky_mxcsr_bits(self) -> None:
        first_observation = {"target": "x86_64-unknown-linux-gnu", "status": "passed", "rounding_mode": 0, "mxcsr": "0x00001f80", "mxcsr_rounding_mode": 0, "ftz_enabled": False, "daz_enabled": False, "failure_classification": "none", "scope": "single-threaded-jsonl-loop"}
        second_observation = dict(first_observation, mxcsr="0x00001f81")
        self.assertEqual(runner._validate_environment_observation(first_observation), "passed")
        self.assertEqual(runner._validate_environment_observation(second_observation), "passed")
        first = {"candidate": {"response": {"observations": first_observation}}, "classification": "pass"}
        second = {"candidate": {"response": {"observations": second_observation}}, "classification": "pass"}
        result = runner._relation_classification({"a": first, "b": second}, {"id": "environment-repeat", "cases": ["a", "b"], "meaning": "synthetic"})
        self.assertEqual(result["classification"], "pass")
        self.assertEqual(result["claim_type"], "workload-position-conditioned-capability-observation")

    def test_primary_transport_failure_survives_cleanup_evidence(self) -> None:
        case = _decimal_record()
        info = {"request_id": case["wire_request_id"], "oracle": {}}

        class FailingSession:
            def __init__(self, primary: str) -> None:
                self.primary = primary

            def request_frame(self, _request: bytes) -> bytes:
                raise TransportError(self.primary)

        for primary, cleanup in (
            ("candidate I/O deadline exceeded", "candidate shutdown deadline exceeded"),
            ("candidate response frame exceeds byte limit", "candidate emitted delayed output"),
        ):
            with self.subTest(primary=primary):
                result = runner.run_cases(
                    {"development": [case], "held-out": [], "adversarial": []},
                    {"case_decimal": info},
                    {},
                    FailingSession(primary),
                    {"synthetic": True},
                )
                self.assertEqual(result["failure"], primary)
                runner._apply_close_result(
                    result,
                    CloseResult(0, b"late\n", b"", cleanup),
                )
                self.assertEqual(result["failure"], primary)
                self.assertEqual(result["candidate"]["cleanup"]["failure"], cleanup)
                self.assertGreater(result["candidate"]["cleanup"]["trailing_stdout_bytes"], 0)

    def test_completed_aggregation_fail_outranks_unsupported(self) -> None:
        first = _decimal_record()
        first["case_id"] = "case_fail"
        second = _decimal_record()
        second["case_id"] = "case_unsupported"
        _, _, first_info = validate_case(first)
        _, _, second_info = validate_case(second)
        first_response = frame_json({"protocol_id": runner.RESPONSE_PROTOCOL_ID, "request_id": first["wire_request_id"], "status": "observed", "observations": {"bits": "0x3ff0000000000000"}})
        second_response = frame_json({"protocol_id": runner.RESPONSE_PROTOCOL_ID, "request_id": second["wire_request_id"], "status": "unsupported"})

        class Session:
            def __init__(self) -> None:
                self.responses = [first_response, second_response]

            def request_frame(self, _request: bytes) -> bytes:
                return self.responses.pop(0)

        result = runner.run_cases(
            {"development": [first, second], "held-out": [], "adversarial": []},
            {first["case_id"]: first_info, second["case_id"]: second_info},
            {},
            Session(),
            {"synthetic": True},
        )
        self.assertEqual(result["run_status"], "complete")
        self.assertEqual(result["evidence_status"], "failed")
        self.assertEqual(result["summary"]["fail"], 1)
        self.assertEqual(result["summary"]["unsupported"], 1)

    def test_malformed_response_is_incomplete(self) -> None:
        case = _decimal_record()
        _, _, info = validate_case(case)
        malformed = frame_json({"protocol_id": runner.RESPONSE_PROTOCOL_ID, "request_id": case["wire_request_id"], "status": "unsupported", "observations": {}})

        class Session:
            def request_frame(self, _request: bytes) -> bytes:
                return malformed

        result = runner.run_cases(
            {"development": [case], "held-out": [], "adversarial": []},
            {case["case_id"]: info},
            {},
            Session(),
            {"synthetic": True},
        )
        self.assertEqual(result["run_status"], "incomplete")
        self.assertEqual(result["evidence_status"], "incomplete")
        self.assertEqual(result["summary"]["incomplete"], 1)

    def test_relation_fail_outranks_inconclusive(self) -> None:
        records = {
            "fail": {"classification": "fail", "candidate": {"response": {} }},
            "inconclusive": {"classification": "inconclusive", "candidate": {"response": {} }},
        }
        relation = runner._relation_classification(records, {"id": "synthetic", "cases": ["fail", "inconclusive"], "meaning": "synthetic"})
        self.assertEqual(relation["classification"], "fail")
        self.assertEqual(relation["claim_type"], "registered-case-group")

    def test_transport_timeout_and_oversize_frame_or_total_are_visible(self) -> None:
        timeout_script = _response_script("""
            import time
            for _line in __import__('sys').stdin:
                time.sleep(0.2)
        """)
        session = BoundedSubprocessSession([sys.executable, str(timeout_script)], deadline_seconds=0.05)
        try:
            with self.assertRaisesRegex(TransportError, "deadline"):
                session.request({"protocol_id": PROTOCOL_ID, "request_id": "x", "operation": "scalar-comparison", "input": {}})
        finally:
            session.close()

        frame_script = _response_script(f"""
            import sys
            for _line in sys.stdin:
                sys.stdout.write('x' * {FRAME_BYTES} + '\\n')
                sys.stdout.flush()
        """)
        session = BoundedSubprocessSession([sys.executable, str(frame_script)])
        try:
            with self.assertRaisesRegex(TransportError, "frame"):
                session.request({"protocol_id": PROTOCOL_ID, "request_id": "x", "operation": "scalar-comparison", "input": {}})
        finally:
            session.close()

        total_script = _response_script(f"""
            import sys
            for _line in sys.stdin:
                sys.stdout.write(('x' * 1023 + '\\n') * {STDOUT_TOTAL_CAP // 1024 + 4})
                sys.stdout.flush()
        """)
        session = BoundedSubprocessSession([sys.executable, str(total_script)])
        try:
            with self.assertRaisesRegex(TransportError, "total cap"):
                deadline = time.monotonic() + 2.0
                write_data = bytearray(frame_json({"protocol_id": PROTOCOL_ID, "request_id": "x", "operation": "scalar-comparison", "input": {}}))
                while write_data:
                    session._pump(deadline, write_data)
                while True:
                    session._pump(deadline)
        finally:
            session.close()

    @unittest.skipUnless(hasattr(os, "fork"), "requires POSIX process groups")
    def test_delayed_final_trailing_output_is_retained_after_leader_exit(self) -> None:
        script = _response_script("""
            import json, os, sys, time
            for line in sys.stdin:
                request = json.loads(line)
                print(json.dumps({"protocol_id":"ck.r3.numeric-candidate-response-1", "request_id":request["request_id"], "status":"observed", "observations":{"predicate":True}}), flush=True)
                child = os.fork()
                if child == 0:
                    time.sleep(0.1)
                    print(json.dumps({"late":True}), flush=True)
                    os._exit(0)
                raise SystemExit(0)
        """)
        session = BoundedSubprocessSession([sys.executable, str(script)])
        try:
            session.request({"protocol_id": PROTOCOL_ID, "request_id": "x", "operation": "scalar-comparison", "input": {}})
        finally:
            closed = session.close()
        self.assertIn(b'"late": true', closed.trailing_stdout)
        result = {"run_status": "complete", "candidate": {}}
        runner._apply_close_result(result, closed)
        self.assertEqual(result["run_status"], "incomplete")
        self.assertIn("trailing stdout", result["candidate"]["cleanup"]["failure"])

    def test_cli_nonzero_exit_and_identity_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-runner-") as temp:
            root = Path(temp)
            manifest = _write_package(root, {"development": [_decimal_record()], "held-out": [], "adversarial": []}, full_claims=True)
            candidate = _response_script("""
                import json, sys
                for line in sys.stdin:
                    request = json.loads(line)
                    print(json.dumps({"protocol_id":"ck.r3.numeric-candidate-response-1", "request_id":request["request_id"], "status":"observed", "observations":{"bits":"0x3fb999999999999a"}}), flush=True)
                    raise SystemExit(3)
            """)
            output = root / "result.json"
            completed = subprocess.run([sys.executable, str(RUNNER), "--manifest", str(manifest), "--output", str(output), "--", sys.executable, str(candidate)], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["run_status"], "incomplete")
            self.assertEqual(result["candidate"]["returncode"], 3)
            self.assertEqual(set(result["runner"]["module_sha256"]), {"run_adapter.py", "runner_common.py", "runner_oracle.py", "runner_schema.py", "runner_transport.py"})
            self.assertEqual(len(result["runner"]["bundle_sha256"]), 64)
            self.assertEqual(result["runner"]["caps"]["frame_bytes"], FRAME_BYTES)
            self.assertEqual(result["runner"]["caps"]["wire_request_id_bytes"], MAX_WIRE_REQUEST_ID_BYTES)
            self.assertIn("io", result["runner"]["deadlines_seconds"])
            self.assertEqual(result["evaluation_binding"], EVALUATION_BINDING)
            self.assertIsNone(result["profile_binding"])
            self.assertEqual(result["technology_result"], TECHNOLOGY_RESULT)
            self.assertEqual(result["result_identity"]["evaluation_binding"], EVALUATION_BINDING)
            self.assertEqual(result["result_identity"]["configured_budgets"], dict(PREREGISTERED_LIMITS))
            self.assertIn("build_identity", result["result_identity"])
            self.assertEqual(result["result_identity"]["identity"]["stability"], "verified")
            self.assertEqual(result["result_identity"]["identity"]["contract"]["candidate_build_context"], "observational-not-provenance")
            self.assertEqual(result["candidate"]["execution_command"][0], str(Path(sys.executable).resolve()))
            self.assertEqual(result["result_identity"]["candidate_execution_command"], result["candidate"]["execution_command"])
            artifacts = result["candidate"]["command_artifacts"]
            self.assertEqual({item["path"] for item in artifacts}, {str(Path(sys.executable).resolve()), str(candidate.resolve())})

    def test_manifest_hash_and_case_cap_use_bounded_corpus_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-bounded-manifest-") as temp:
            root = Path(temp)
            manifest = _write_package(root, {"development": [_decimal_record()], "held-out": [], "adversarial": []}, full_claims=True)
            _, _, metadata = load_manifest(manifest)
            self.assertEqual(metadata["manifest_sha256"], hashlib.sha256(manifest.read_bytes()).hexdigest())
            development = root / "development.jsonl"
            self.assertEqual(metadata["corpora"][0]["sha256"], hashlib.sha256(development.read_bytes()).hexdigest())
            mismatched = json.loads(manifest.read_text(encoding="utf-8"))
            mismatched["preregistration"]["claim_domain"]["case_count"] = 48
            mismatched_path = root / "mismatched.json"
            mismatched_path.write_text(json.dumps(mismatched), encoding="utf-8")
            with self.assertRaisesRegex(ProtocolError, "claim domain"):
                load_manifest(mismatched_path)

            too_many: list[dict[str, object]] = []
            for index in range(MAX_CASES_PER_CORPUS + 1):
                record = _decimal_record()
                record["case_id"] = f"case_{index:03d}"
                record["wire_request_id"] = f"wire_{index:032x}"
                too_many.append(record)
            too_many_root = root / "too-many"
            too_many_root.mkdir()
            oversized_manifest = _write_package(too_many_root, {"development": too_many, "held-out": [], "adversarial": []})
            with self.assertRaisesRegex(ProtocolError, "case-count bound"):
                load_manifest(oversized_manifest)

    def test_full_claim_fixture_relation_collision_is_finite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-relation-collision-") as temp:
            root = Path(temp)
            record = _decimal_record()
            record["case_id"] = "collision_base"
            record["relations"] = ["synthetic-relation-00", "synthetic-relation-01"]
            relations = [
                {"id": "synthetic-relation-00", "cases": ["collision_base"], "meaning": "synthetic collision fixture"},
                {"id": "synthetic-relation-01", "cases": ["collision_base"], "meaning": "synthetic collision fixture"},
            ]
            manifest = _write_package(root, {"development": [record], "held-out": [], "adversarial": []}, relations, full_claims=True)
            _, corpora, metadata = load_manifest(manifest)
            self.assertEqual(sum(len(values) for values in corpora.values()), 49)
            self.assertEqual(len(metadata["relations"]), 26)

    def test_completed_semantic_fail_is_nonzero_and_explicit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-semantic-fail-") as temp:
            root = Path(temp)
            manifest = _write_package(root, {"development": [_decimal_record()], "held-out": [], "adversarial": []}, full_claims=True)
            candidate = _response_script("""
                import json, sys
                for line in sys.stdin:
                    request = json.loads(line)
                    print(json.dumps({"protocol_id":"ck.r3.numeric-candidate-response-1", "request_id":request["request_id"], "status":"observed", "observations":{"bits":"0x3ff0000000000000"}}), flush=True)
            """)
            output = root / "result.json"
            completed = subprocess.run([sys.executable, str(RUNNER), "--manifest", str(manifest), "--output", str(output), "--", sys.executable, str(candidate)], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["run_status"], "complete")
            self.assertEqual(result["evidence_status"], "failed")
            self.assertEqual(result["summary"]["fail"], 49)
            self.assertIsNone(result["failure"])

    def test_nonempty_relation_is_retained_and_classified_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-relation-") as temp:
            root = Path(temp)
            first = _decimal_record()
            first["case_id"] = "case_first"
            first["relations"] = ["lexical-equivalence"]
            second = _record(
                "case_second",
                "wire_0c5a8d3f7b129e46",
                "decimal-admission",
                {"token": "1e-1", "max_token_bytes": "512", "max_significant_digits": "128", "max_exponent_abs": "10000"},
                {"status": "observed", "observations": {"bits": "0x3fb999999999999a"}},
            )
            second["relations"] = ["lexical-equivalence"]
            manifest = _write_package(
                root,
                {"development": [first, second], "held-out": [], "adversarial": []},
                [{"id": "lexical-equivalence", "cases": ["case_first", "case_second"], "meaning": "equivalent decimal spellings"}],
                full_claims=True,
            )
            candidate = _response_script("""
                import json, sys
                for line in sys.stdin:
                    request = json.loads(line)
                    print(json.dumps({"protocol_id":"ck.r3.numeric-candidate-response-1", "request_id":request["request_id"], "status":"observed", "observations":{"bits":"0x3fb999999999999a"}}), flush=True)
            """)
            output = root / "result.json"
            completed = subprocess.run([sys.executable, str(RUNNER), "--manifest", str(manifest), "--output", str(output), "--", sys.executable, str(candidate)], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["relations"][0]["id"], "lexical-equivalence")
            self.assertEqual(result["relations"][0]["classification"], "pass")

    def test_raw_request_end_to_end_and_candidate_projection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck2-raw-") as temp:
            root = Path(temp)
            wire_id = "wire_44a0d91c6e7f2385"
            raw = '{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"' + wire_id + '","operation":"decimal-admission","operation":"decimal-admission","input":{}}'
            record = _record("case_raw", wire_id, "decimal-admission", {}, {"status": "error", "error_code": "malformed-request"}, request_raw=raw)
            manifest = _write_package(root, {"development": [], "held-out": [], "adversarial": [record]}, full_claims=True)
            candidate = _response_script("""
                import json, sys
                for line in sys.stdin:
                    if line.count('"operation"') == 2:
                        print(json.dumps({"protocol_id":"ck.r3.numeric-candidate-response-1", "status":"error", "error":"malformed-request"}), flush=True)
                    else:
                        request = json.loads(line)
                        print(json.dumps({"protocol_id":"ck.r3.numeric-candidate-response-1", "request_id":request["request_id"], "status":"observed", "observations":{"bits":"0x3fb999999999999a"}}), flush=True)
            """)
            output = root / "result.json"
            completed = subprocess.run([sys.executable, str(RUNNER), "--manifest", str(manifest), "--output", str(output), "--", sys.executable, str(candidate)], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["summary"]["pass"], 49)
            self.assertIsNone(result["corpora"][2]["cases"][0]["request_id"])


if __name__ == "__main__":
    unittest.main()

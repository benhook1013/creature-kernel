"""Bounded tests for the execution-incapable Phase 3 evidence contract."""

from __future__ import annotations

import base64
import hashlib
import json
import stat
import unittest

import phase3_evidence_contract as contract
import phase3_oracle as oracle
import phase3_scorer as scorer
import test_phase3_oracle_scorer as fixture
from phase3_common import FRAME_BYTES, canonical_json


def _attempt() -> dict[str, object]:
    return {
        "freeze_manifest_sha256": "a" * 64,
        "attempt_id": "attempt-001",
        "platform_selector": "wsl2-x86_64",
        "ordinal": 0,
        "authorization_reference": "BEN-AUTH-2026-08-19-001",
        "gate_b_admission_sha256": "c" * 64,
        "authorization_record_sha256": "d" * 64,
        "custody_record_sha256": "e" * 64,
    }


def _tools() -> list[dict[str, object]]:
    names = (
        "phase3_common", "phase3_oracle", "phase3_scorer", "phase3_runner",
        "phase3_receipt", "phase3_materialized_adapter", "phase3_evidence_contract",
        "phase3_gate_b_preflight",
    )
    return [{"path": f"scripts/{name}.py", "bytes": 1, "sha256": "b" * 64} for name in names]


def _execution_identity(*, partial: bool = False) -> dict[str, object]:
    candidate = {"device": 1, "inode": 100, "mode": stat.S_IFREG | 0o555, "size": 123, "nlink": 0}
    cwd = {"device": 1, "inode": 200, "mode": stat.S_IFDIR | 0o700, "size": 4096, "nlink": 2}
    content = {"size": 123, "sha256": "e" * 64}
    if partial:
        return {
            "descriptor_pre": dict(candidate), "descriptor_post_exe": None, "descriptor_post_fd": None,
            "cwd_pre": None, "cwd_post": None,
            "content_initial": dict(content), "content_pre_fork": None, "content_post_exec": None,
            "seals_initial": 15, "seals_pre_fork": None, "seals_post_exec": None,
        }
    return {
        "descriptor_pre": dict(candidate), "descriptor_post_exe": dict(candidate), "descriptor_post_fd": dict(candidate),
        "cwd_pre": dict(cwd), "cwd_post": dict(cwd),
        "content_initial": dict(content), "content_pre_fork": dict(content), "content_post_exec": dict(content),
        "seals_initial": 15, "seals_pre_fork": 15, "seals_post_exec": 15,
    }


def _wire(value: object) -> dict[str, object]:
    raw = json.dumps({key: value[key] for key in contract.REQUEST_WIRE_KEYS}, separators=(",", ":")).encode()
    return {"bytes_b64": base64.b64encode(raw).decode(), "sha256": hashlib.sha256(raw).hexdigest()}


def _evidence(ordinal: int, request_id: str, *, status: str, classification: str, dispatched: bool = True) -> dict[str, object]:
    if not dispatched:
        payload = {"variant": "runner-preflight-v1", "runner": {"reason": "out-of-domain numeric admission", "domain_status": "out-of-domain"}, "classification": "out-of-domain", "cause": None}
    else:
        request = fixture.request(request_id)
        if 52 <= ordinal <= 55:
            request["source"] = fixture.source_text(root_q=[0, 0, 0, 0])
        if ordinal == 59:
            request.update({"expected_response_status": "rejected", "expected_cause": {"code": "ck.provisional-r3-authored-conflict.numeric-comparison.invalid-profile", "failure": "negative", "field": "translation-relative", "index": 3}})
            request["tolerances"]["translation_relative"] = -1
        truth = oracle.evaluate_source(request["source"], request["metric"])
        if 52 <= ordinal <= 55:
            response = fixture.skipped_response(request, truth)
        elif ordinal == 59:
            response = json.dumps({"protocol_id": "ck.exp-0002.r3-authored-conflict-candidate-response-1", "request_id": request_id, "status": "rejected", "error": "ck.provisional-r3-authored-conflict.invalid-tolerance", "cause": request["expected_cause"]}, separators=(",", ":")).encode()
        else:
            response = fixture.wire_response(request, truth, outcome=classification)
        context = {"metric": request["metric"], "observation_only": status == "observation", "expected_class": classification if 8 <= ordinal < 48 else None, "expected_response_status": "rejected" if ordinal == 59 else None, "expected_cause": request.get("expected_cause")}
        scorer_request = dict(request)
        scorer_request.pop("metric")
        scorer_request.update({key: value for key, value in context.items() if key in {"metric", "expected_response_status", "expected_cause"} and value is not None})
        scorer_request["metric"] = context["metric"]
        score = scorer.score_response(scorer_request, truth, response, expected_class=context["expected_class"], observation_only=context["observation_only"])
        payload = {"variant": "dispatched-candidate-v1", "request": _wire(request), "response": {"bytes_b64": base64.b64encode(response).decode(), "sha256": hashlib.sha256(response).hexdigest()}, "scorer_context": context, "oracle_result": truth, "scorer_result": score}
    evidence = {"schema": contract.EVIDENCE_SCHEMA, "payload": payload}
    return {"ordinal": ordinal, "request_id": request_id, "role": "development" if ordinal < 8 else "held-out" if ordinal < 48 else "controls", "dispatch_to_candidate": dispatched, "status": status, "classification": classification, "evidence": evidence, "evidence_sha256": hashlib.sha256(canonical_json(evidence)).hexdigest()}


def _adjudications(attempt_id: str = "attempt-001") -> list[dict[str, object]]:
    result = []
    for ordinal in range(60):
        request_id = f"p3-{attempt_id}-{ordinal:03d}"
        if 56 <= ordinal <= 58:
            item = _evidence(ordinal, request_id, status="observation", classification="out-of-domain", dispatched=False)
        elif 52 <= ordinal <= 55:
            item = _evidence(ordinal, request_id, status="observation", classification="skipped")
        elif ordinal == 59:
            item = _evidence(ordinal, request_id, status="observation", classification="rejected")
        elif ordinal < 8 or 48 <= ordinal <= 51:
            item = _evidence(ordinal, request_id, status="observation", classification="agree")
        else:
            item = _evidence(ordinal, request_id, status="supported", classification="agree")
        result.append(item)
    return result


def _make_dispatched_incomplete(adjudications: list[dict[str, object]], ordinal: int) -> None:
    item = adjudications[ordinal]
    complete = item["evidence"]["payload"]
    item["status"] = "inconclusive"
    item["classification"] = "incomplete"
    item["evidence"] = {
        "schema": contract.EVIDENCE_SCHEMA,
        "payload": {
            "variant": "dispatched-incomplete-v1",
            "request": complete["request"],
            "response": None,
            "scorer_context": complete["scorer_context"],
            "reason": "response unavailable",
            "cause": {"code": "missing-response", "detail": "candidate response was not observed"},
        },
    }
    item["evidence_sha256"] = hashlib.sha256(canonical_json(item["evidence"])).hexdigest()


def _process(role: str, count: int, adjudications: list[dict[str, object]], *, incomplete: bool = False) -> dict[str, object]:
    requests = []
    responses = []
    for item in adjudications:
        if item["role"] != role or not item["dispatch_to_candidate"]:
            continue
        payload = item["evidence"]["payload"]
        requests.append(base64.b64decode(payload["request"]["bytes_b64"]))
        if payload.get("response") is not None:
            responses.append(base64.b64decode(payload["response"]["bytes_b64"]))
    def pair(frames: list[bytes], domain: bytes) -> dict[str, object]:
        return {"count": len(frames), "sha256": contract._framed_hash(frames, domain)}
    if incomplete:
        return {
            "variant": "incomplete-v1", "role": role, "candidate_request_count": count,
            "platform": None, "launch": None,
            "candidate_binary": {"sha256_pre": "e" * 64, "sha256_post": "e" * 64},
            "execution_identity": _execution_identity(partial=True),
            "fe_mxcsr": None, "transport": {"requests": pair(requests, contract.REQUEST_FRAME_DOMAIN), "responses": pair(responses, contract.RESPONSE_FRAME_DOMAIN)},
            "lifecycle": None, "output": None, "missing": ["platform", "launch", "fe_mxcsr", "lifecycle", "output"],
            "outcome": {"status": "inconclusive", "code": "startup-observation-incomplete", "detail": "test fixture intentionally omits process observations"},
        }
    return {
        "variant": "complete-v1", "role": role, "candidate_request_count": count,
        "platform": {"selector": "wsl2-x86_64", "cpu_model": "test-cpu", "cpu_features": ["sse2"], "architecture": "x86_64", "kernel_or_wsl": "test-kernel", "os_release": "test-os", "filesystem": "ext4", "mount_context": "/work", "workflow_runner": "local-test", "workflow_image": "test-image", "toolchain": "rust-test", "compiler": "rustc-test"},
        "launch": {"identity": f"launch-{role}", "argv": ["candidate", "--role", role], "cwd": "/work/candidate", "environment": {"CK_ROLE": role}},
        "candidate_binary": {"sha256_pre": "e" * 64, "sha256_post": "e" * 64},
        "execution_identity": _execution_identity(),
        "fe_mxcsr": {"pre": {"x87_control_word": "0x037f", "mxcsr": "0x00001f80", "x87_rounding_mode": "nearest", "mxcsr_rounding_mode": "nearest", "x87_exception_masks": 63, "mxcsr_exception_masks": 63, "x87_flags": None, "mxcsr_flags": 0, "ftz": False, "daz": False}, "post": {"x87_control_word": "0x037f", "mxcsr": "0x00001f80", "x87_rounding_mode": "nearest", "mxcsr_rounding_mode": "nearest", "x87_exception_masks": 63, "mxcsr_exception_masks": 63, "x87_flags": None, "mxcsr_flags": 0, "ftz": False, "daz": False}},
        "transport": {"requests": pair(requests, contract.REQUEST_FRAME_DOMAIN), "responses": pair(responses, contract.RESPONSE_FRAME_DOMAIN)},
        "lifecycle": {"state": "exited", "exit_code": 0, "clean_shutdown": True}, "output": {"missing": [], "extra": [], "trailing": []},
        "outcome": {"status": "supported", "code": None, "detail": None},
    }


def _result(*, incomplete_process: bool = False, adjudications: list[dict[str, object]] | None = None) -> bytes:
    adjudications = adjudications or _adjudications()
    processes = [_process("development", 8, adjudications, incomplete=incomplete_process), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
    return contract.build_result(_attempt(), adjudications, processes, _tools())


class EvidenceContractTests(unittest.TestCase):
    def test_result_receipt_index_are_deterministic_and_bound(self) -> None:
        result = _result()
        self.assertEqual(result, _result())
        value = contract.validate_result(result)
        self.assertEqual(value["counts"], {"cases": 60, "development": 8, "held-out": 40, "controls": 12, "dispatched": 57, "preflight": 3, "supported": 40, "failed": 0, "inconclusive": 0, "observation": 20})
        self.assertNotIn("frames_b64", value["process_observations"][0]["transport"]["requests"])
        receipt = contract.build_receipt(result)
        self.assertEqual(receipt, contract.build_receipt(result))
        self.assertEqual(contract.validate_receipt(receipt, result)["result_sha256"], hashlib.sha256(result).hexdigest())
        index = contract.build_attempt_index(result, receipt)
        self.assertEqual(index, contract.build_attempt_index(result, receipt))
        self.assertEqual(contract.validate_attempt_index(index, result, receipt)["envelope_sha256"], json.loads(index)["envelope_sha256"])
        attempt = value["attempt"]
        self.assertEqual(attempt["gate_b_admission_sha256"], "c" * 64)
        self.assertEqual(attempt["authorization_record_sha256"], "d" * 64)
        self.assertEqual(attempt["custody_record_sha256"], "e" * 64)
        self.assertEqual(contract.validate_receipt(receipt, result)["attempt"], attempt)
        self.assertEqual(contract.validate_attempt_index(index, result, receipt)["attempt"], attempt)

    def test_ordinal_role_dispatch_and_status_layout_is_closed(self) -> None:
        swapped = _adjudications(); swapped[8]["role"] = "development"
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=swapped)
        swapped = _adjudications(); swapped[59]["dispatch_to_candidate"] = False; swapped[59]["classification"] = "out-of-domain"
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=swapped)
        swapped = _adjudications(); swapped[0]["status"] = "supported"
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=swapped)

    def test_observations_are_neutral_and_only_heldout_can_support(self) -> None:
        result = json.loads(_result())
        self.assertEqual(result["status"], "supported")
        self.assertEqual(sum(item["status"] == "supported" for item in result["adjudications"]), 40)
        observations = _adjudications()
        for index in range(8, 48):
            observations[index]["status"] = "observation"
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=observations)

    def test_scorer_binding_rejects_shallow_or_tampered_witness(self) -> None:
        shallow = _adjudications(); shallow[8]["evidence"]["payload"]["response"]["bytes_b64"] = base64.b64encode(b"x").decode(); shallow[8]["evidence"]["payload"]["response"]["sha256"] = hashlib.sha256(b"x").hexdigest(); shallow[8]["evidence_sha256"] = hashlib.sha256(canonical_json(shallow[8]["evidence"])).hexdigest()
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=shallow)
        tampered = _adjudications(); tampered[8]["evidence"]["payload"]["scorer_result"]["classification"] = "conflict"; tampered[8]["evidence_sha256"] = hashlib.sha256(canonical_json(tampered[8]["evidence"])).hexdigest()
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=tampered)

    def test_candidate_wire_is_exactly_seven_fields_and_context_is_separate(self) -> None:
        item = _adjudications()[8]
        wire = json.loads(base64.b64decode(item["evidence"]["payload"]["request"]["bytes_b64"]))
        self.assertEqual(set(wire), set(contract.REQUEST_WIRE_KEYS))
        self.assertEqual(set(item["evidence"]["payload"]["scorer_context"]), set(contract.SCORER_CONTEXT_KEYS))
        leaked = _adjudications()
        request = json.loads(base64.b64decode(leaked[8]["evidence"]["payload"]["request"]["bytes_b64"]))
        request["metric"] = "translation"
        raw = json.dumps(request, separators=(",", ":")).encode()
        leaked[8]["evidence"]["payload"]["request"] = {"bytes_b64": base64.b64encode(raw).decode(), "sha256": hashlib.sha256(raw).hexdigest()}
        leaked[8]["evidence_sha256"] = hashlib.sha256(canonical_json(leaked[8]["evidence"])).hexdigest()
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=leaked)
        context = _adjudications()
        context[8]["evidence"]["payload"]["scorer_context"]["expected_class"] = "conflict"
        context[8]["evidence_sha256"] = hashlib.sha256(canonical_json(context[8]["evidence"])).hexdigest()
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=context)

    def test_legal_response_frame_near_inherited_limit_is_bounded(self) -> None:
        adjudications = _adjudications()
        item = adjudications[8]
        payload = item["evidence"]["payload"]
        raw = base64.b64decode(payload["response"]["bytes_b64"])
        padded = raw.rstrip(b"\n") + b" " * (FRAME_BYTES - len(raw.rstrip(b"\n")) - 1) + b"\n"
        payload["response"] = {"bytes_b64": base64.b64encode(padded).decode(), "sha256": hashlib.sha256(padded).hexdigest()}
        item["evidence_sha256"] = hashlib.sha256(contract._canonical(item["evidence"], "test evidence", contract.MAX_EVIDENCE_BYTES)).hexdigest()
        result = _result(adjudications=adjudications)
        self.assertEqual(json.loads(result)["status"], "supported")

    def test_status_precedence_process_incomplete_and_drift(self) -> None:
        incomplete = json.loads(_result(incomplete_process=True))
        self.assertEqual(incomplete["status"], "inconclusive")
        drift = _adjudications(); result = json.loads(_result(adjudications=drift)); del result
        processes = [_process("development", 8, drift), _process("held-out", 40, drift), _process("controls", 9, drift)]
        processes[0]["candidate_binary"]["sha256_post"] = "d" * 64
        self.assertEqual(json.loads(contract.build_result(_attempt(), drift, processes, _tools()))["status"], "failed")

    def test_fp_status_flags_may_drift_but_controls_may_not(self) -> None:
        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        post = processes[0]["fe_mxcsr"]["post"]
        post["mxcsr"] = "0x00001f81"
        post["mxcsr_flags"] = 1
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "supported")
        post["x87_control_word"] = "0x077f"
        post["x87_rounding_mode"] = "downward"
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "failed")

    def test_execution_identity_complete_partial_and_closed_schema(self) -> None:
        complete = json.loads(_result())
        identity = complete["process_observations"][0]["execution_identity"]
        self.assertEqual(identity["descriptor_pre"], identity["descriptor_post_exe"])
        self.assertEqual(identity["content_initial"]["sha256"], "e" * 64)

        partial = json.loads(_result(incomplete_process=True))
        partial_identity = partial["process_observations"][0]["execution_identity"]
        self.assertIsNotNone(partial_identity["descriptor_pre"])
        self.assertIsNone(partial_identity["descriptor_post_exe"])
        self.assertEqual(partial["status"], "inconclusive")

        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications, incomplete=True), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        processes[0]["execution_identity"] = None
        processes[0]["missing"].append("execution_identity")
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "inconclusive")

        processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        processes[0]["execution_identity"]["unexpected"] = True
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())

    def test_execution_identity_mismatch_derives_failed_with_global_precedence(self) -> None:
        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications, incomplete=True), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        processes[2]["execution_identity"]["descriptor_post_exe"]["inode"] = 101
        value = json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))
        self.assertEqual(value["status"], "failed")

        processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        processes[0]["execution_identity"]["content_post_exec"]["sha256"] = "f" * 64
        value = json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))
        self.assertEqual(value["status"], "failed")

    def test_execution_identity_requires_exact_memfd_seals(self) -> None:
        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        self.assertEqual(processes[0]["execution_identity"]["seals_initial"], contract.REQUIRED_MEMFD_SEALS)
        for key in ("seals_initial", "seals_pre_fork", "seals_post_exec"):
            processes[0]["execution_identity"][key] = 0
        value = json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))
        self.assertEqual(value["status"], "failed")

        processes = [_process("development", 8, adjudications, incomplete=True), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        processes[0]["execution_identity"]["seals_initial"] = 1
        value = json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))
        self.assertEqual(value["status"], "failed")

    def test_process_outcome_retains_failure_and_inconclusive_precedence(self) -> None:
        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        processes[0]["outcome"] = {"status": "failed", "code": "exec-failed", "detail": "candidate launch failed"}
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "failed")
        processes[0]["outcome"] = {"status": "inconclusive", "code": "observation-missing", "detail": "post-exec observation unavailable"}
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "inconclusive")
        processes[0]["outcome"] = {"status": "supported", "code": "not-allowed", "detail": "not allowed"}
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())

    def test_incomplete_adjudication_cannot_mask_later_process_failures(self) -> None:
        def fail_binary(process: dict[str, object]) -> None:
            process["candidate_binary"]["sha256_post"] = "f" * 64

        def fail_fp(process: dict[str, object]) -> None:
            post = process["fe_mxcsr"]["post"]
            post["x87_control_word"] = "0x077f"
            post["x87_rounding_mode"] = "downward"

        def fail_lifecycle(process: dict[str, object]) -> None:
            process["lifecycle"] = {"state": "failed", "exit_code": 1, "clean_shutdown": False}

        def fail_outcome(process: dict[str, object]) -> None:
            process["outcome"] = {"status": "failed", "code": "transport-failed", "detail": "candidate transport failed"}

        for name, mutation in (
            ("binary", fail_binary), ("fp", fail_fp),
            ("lifecycle", fail_lifecycle), ("outcome", fail_outcome),
        ):
            with self.subTest(failure=name):
                adjudications = _adjudications()
                _make_dispatched_incomplete(adjudications, 8)
                processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
                mutation(processes[2])
                value = json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))
                self.assertEqual(value["status"], "failed")

    def test_incomplete_transport_and_failure_precedence_is_order_independent(self) -> None:
        def retain_prefix(process: dict[str, object], adjudications: list[dict[str, object]], role: str) -> None:
            frames = []
            for item in adjudications:
                if item["role"] == role and item["dispatch_to_candidate"]:
                    frames.append(base64.b64decode(item["evidence"]["payload"]["request"]["bytes_b64"]))
            process["transport"] = {
                "requests": {"count": 1, "sha256": contract._framed_hash(frames[:1], contract.REQUEST_FRAME_DOMAIN)},
                "responses": {"count": 0, "sha256": contract._framed_hash([], contract.RESPONSE_FRAME_DOMAIN)},
            }

        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications, incomplete=True), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        retain_prefix(processes[0], adjudications, "development")
        processes[2]["outcome"] = {"status": "failed", "code": "late-failure", "detail": "later controls process failed"}
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "failed")

        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications, incomplete=True)]
        processes[0]["candidate_binary"]["sha256_post"] = "f" * 64
        retain_prefix(processes[2], adjudications, "controls")
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "failed")

    def test_incomplete_transport_accepts_only_observed_prefixes(self) -> None:
        adjudications = _adjudications()
        processes = [_process("development", 8, adjudications, incomplete=True), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        requests = []
        responses = []
        for item in adjudications[:8]:
            payload = item["evidence"]["payload"]
            requests.append(base64.b64decode(payload["request"]["bytes_b64"]))
            responses.append(base64.b64decode(payload["response"]["bytes_b64"]))
        processes[0]["transport"] = {
            "requests": {"count": 2, "sha256": contract._framed_hash(requests[:2], contract.REQUEST_FRAME_DOMAIN)},
            "responses": {"count": 1, "sha256": contract._framed_hash(responses[:1], contract.RESPONSE_FRAME_DOMAIN)},
        }
        self.assertEqual(json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))["status"], "inconclusive")
        processes[0]["transport"]["requests"]["sha256"] = "f" * 64
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())
        processes[0]["transport"] = {"requests": None, "responses": None}
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())

    def test_prelaunch_failure_explicitly_marks_unobserved_transport(self) -> None:
        adjudications = _adjudications()
        process = _process("development", 8, adjudications, incomplete=True)
        process["transport"] = {"requests": None, "responses": None}
        process["missing"].extend(["transport.requests", "transport.responses"])
        process["outcome"] = {"status": "failed", "code": "candidate-launch-failed", "detail": "candidate never reached transport"}
        processes = [process, _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        value = json.loads(contract.build_result(_attempt(), adjudications, processes, _tools()))
        self.assertEqual(value["status"], "failed")
        retained = value["process_observations"][0]
        self.assertIsNone(retained["transport"]["requests"])
        self.assertIsNone(retained["transport"]["responses"])

    def test_incomplete_missing_markers_must_match_observations(self) -> None:
        adjudications = _adjudications()
        process = _process("development", 8, adjudications, incomplete=True)
        process["missing"].append("transport.requests")
        processes = [process, _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())

        process = _process("development", 8, adjudications, incomplete=True)
        process["transport"]["requests"] = None
        processes = [process, _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())

        process = _process("development", 8, adjudications, incomplete=True)
        process["missing"].remove("platform")
        processes = [process, _process("held-out", 40, adjudications), _process("controls", 9, adjudications)]
        with self.assertRaises(contract.EvidenceContractError):
            contract.build_result(_attempt(), adjudications, processes, _tools())

    def test_dispatched_incomplete_retains_request_and_missing_or_malformed_response(self) -> None:
        for response in (None, {"bytes_b64": base64.b64encode(b"not-json").decode(), "sha256": hashlib.sha256(b"not-json").hexdigest()}):
            adjudications = _adjudications()
            item = adjudications[8]
            complete = item["evidence"]["payload"]
            item["status"] = "inconclusive"
            item["classification"] = "incomplete"
            item["evidence"] = {"schema": contract.EVIDENCE_SCHEMA, "payload": {"variant": "dispatched-incomplete-v1", "request": complete["request"], "response": response, "scorer_context": complete["scorer_context"], "reason": "response unavailable or malformed", "cause": {"code": "missing-response", "detail": "observed frame could not be scored"}}}
            item["evidence_sha256"] = hashlib.sha256(canonical_json(item["evidence"])).hexdigest()
            result = contract.build_result(_attempt(), adjudications, [_process("development", 8, adjudications), _process("held-out", 40, adjudications), _process("controls", 9, adjudications)], _tools())
            self.assertEqual(json.loads(result)["status"], "inconclusive")

    def test_tamper_unbound_and_transport_hash_fail_closed(self) -> None:
        result = _result(); receipt = contract.build_receipt(result); index = contract.build_attempt_index(result, receipt)
        with self.assertRaises(contract.EvidenceContractError): contract.validate_receipt(receipt)
        with self.assertRaises(contract.EvidenceContractError): contract.validate_attempt_index(index)
        for raw, validator, args in ((result, contract.validate_result, ()), (receipt, contract.validate_receipt, (result,)), (index, contract.validate_attempt_index, (result, receipt))):
            tampered = bytearray(raw); tampered[-2] = ord("x") if tampered[-2] != ord("x") else ord("y")
            with self.assertRaises(contract.EvidenceContractError): validator(bytes(tampered), *args)
        bad = _adjudications(); bad[8]["evidence"]["payload"]["response"]["bytes_b64"] = base64.b64encode(b"bad").decode(); bad[8]["evidence"]["payload"]["response"]["sha256"] = hashlib.sha256(b"bad").hexdigest(); bad[8]["evidence_sha256"] = hashlib.sha256(canonical_json(bad[8]["evidence"])).hexdigest()
        with self.assertRaises(contract.EvidenceContractError): _result(adjudications=bad)


if __name__ == "__main__":
    unittest.main()

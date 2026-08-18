"""Focused, execution-incapable tests for experiment-wide closure."""

from __future__ import annotations

import hashlib
import json
import stat
import unittest
from unittest import mock

import phase3_experiment_closure as closure
import phase3_evidence_contract as evidence
import test_phase3_evidence_contract as evidence_fixture


FREEZE_HASH = "f" * 64
EXECUTION_SOURCE_COMMIT = "a" * 40
REVIEWED_COMMIT = "b" * 40


def _self_hashed(value: dict[str, object], field: str, domain: bytes, *, strip_newline: bool) -> bytes:
    value[field] = None
    unsigned = closure._canonical(value)
    material = unsigned[:-1] if strip_newline else unsigned
    value[field] = hashlib.sha256(domain + material).hexdigest()
    return closure._canonical(value)


def _custody(ordinal: int, selector: str) -> bytes:
    return _self_hashed({
        "schema": "ck.exp-0002.phase3.gate-b-exact-artifact-custody-1",
        "experiment_id": "EXP-0002",
        "phase_id": closure.PHASE_ID,
        "candidate_profile_id": closure.CANDIDATE_PROFILE_ID,
        "successor_manifest_sha256": FREEZE_HASH,
        "platform": {"selector": selector, "role": "wsl" if selector.startswith("wsl") else "native"},
        "candidate_source_commit": "a" * 40,
        "receipt": {"path": "build-receipt.json", "mode": stat.S_IFREG | 0o644, "bytes": 1, "sha256": "1" * 64, "self_hash": "2" * 64},
        "candidate": {"path": "candidate", "mode": stat.S_IFREG | 0o755, "bytes": 1, "sha256": "3" * 64},
        "transfer": {},
        "policy": {"custody": "declared", "candidate_execution": "prohibited", "experiment_dispatch": "prohibited", "causal_build_attestation": False},
        "custody_record_sha256": None,
    }, "custody_record_sha256", b"ck.exp-0002.phase3.gate-b-exact-artifact-custody.v1\0", strip_newline=False)


def _admission(*, execution_source: str = EXECUTION_SOURCE_COMMIT, reviewed_commit: str = REVIEWED_COMMIT) -> bytes:
    return _self_hashed({
        "schema": "ck.exp-0002.phase3.gate-b-admission-1",
        "experiment_id": "EXP-0002",
        "phase_id": closure.PHASE_ID,
        "candidate_profile_id": closure.CANDIDATE_PROFILE_ID,
        "freeze_manifest_sha256": FREEZE_HASH,
        "execution_tool_source_commit": execution_source,
        "reviewed_commit": reviewed_commit,
        "reviews": [{"status": "passed", "disposition": "Clean", "findings": []}, {"status": "passed", "disposition": "Clean", "findings": []}],
        "status": "passed",
        "execution_permitted": False,
        "admission_record_sha256": None,
    }, "admission_record_sha256", b"ck.exp-0002.phase3.gate-b-admission.v1\0", strip_newline=True)


def _authorization(ordinal: int, selector: str, attempt_id: str, admission_raw: bytes, custody_raw: bytes) -> bytes:
    custody = json.loads(custody_raw)
    return _self_hashed({
        "schema": "ck.exp-0002.phase3.exact-attempt-human-authorization-1",
        "experiment_id": "EXP-0002",
        "phase_id": closure.PHASE_ID,
        "candidate_profile_id": closure.CANDIDATE_PROFILE_ID,
        "admission_record_sha256": hashlib.sha256(admission_raw).hexdigest(),
        "freeze_manifest_sha256": FREEZE_HASH,
        "custody_record_sha256": custody["custody_record_sha256"],
        "attempt_id": attempt_id,
        "platform_selector": selector,
        "ordinal": ordinal,
        "authorization_reference": f"SYNTHETIC-AUTH-{ordinal}",
        "scope": "exact-attempt",
        "execution_permitted": True,
        "automatic_retry": False,
        "authorization_record_sha256": None,
    }, "authorization_record_sha256", b"ck.exp-0002.phase3.exact-attempt-human-authorization.v1\0", strip_newline=True)


def _different_supported_evidence(attempt_id: str) -> dict[str, object]:
    ordinal = 8
    request_id = f"p3-{attempt_id}-{ordinal:03d}"
    request = evidence_fixture.fixture.request(request_id, absolute=3)
    request["source"] = evidence_fixture.fixture.source_text(root_t=[1, 0, 0])
    truth = evidence_fixture.oracle.evaluate_source(request["source"], request["metric"])
    response = evidence_fixture.fixture.wire_response(
        request, truth,
        authored=evidence_fixture.fixture.transform(1),
        derived=evidence_fixture.fixture.transform(0),
        final_output=evidence_fixture.fixture.transform(0),
        outcome="agree",
    )
    context = {"metric": request["metric"], "observation_only": False, "expected_class": "agree", "expected_response_status": None, "expected_cause": None}
    score = evidence_fixture.scorer.score_response(request, truth, response, expected_class="agree", observation_only=False)
    payload = {
        "variant": "dispatched-candidate-v1", "request": evidence_fixture._wire(request),
        "response": {"bytes_b64": evidence_fixture.base64.b64encode(response).decode(), "sha256": hashlib.sha256(response).hexdigest()},
        "scorer_context": context, "oracle_result": truth, "scorer_result": score,
    }
    wrapped = {"schema": evidence.EVIDENCE_SCHEMA, "payload": payload}
    return {"ordinal": ordinal, "request_id": request_id, "role": "held-out", "dispatch_to_candidate": True, "status": "supported", "classification": "agree", "evidence": wrapped, "evidence_sha256": hashlib.sha256(evidence_fixture.canonical_json(wrapped)).hexdigest()}


def _attempt_record(ordinal: int, *, result_status: str = "supported", process_tag: str = "same", semantic_disagreement: bool = False, admission_kwargs: dict[str, str] | None = None) -> dict[str, object]:
    selector = closure.EXPECTED_SELECTORS[ordinal]
    attempt_id = f"attempt-synthetic-{ordinal}"
    attempt = {
        "freeze_manifest_sha256": FREEZE_HASH,
        "attempt_id": attempt_id,
        "platform_selector": selector,
        "ordinal": ordinal,
        "authorization_reference": f"SYNTHETIC-AUTH-{ordinal}",
        "gate_b_admission_sha256": "0" * 64,
        "authorization_record_sha256": "0" * 64,
        "custody_record_sha256": "0" * 64,
    }
    adjudications = evidence_fixture._adjudications(attempt_id)
    if semantic_disagreement:
        adjudications[8] = _different_supported_evidence(attempt_id)
    processes = [
        evidence_fixture._process("development", 8, adjudications),
        evidence_fixture._process("held-out", 40, adjudications),
        evidence_fixture._process("controls", 9, adjudications),
    ]
    for process in processes:
        process["platform"]["selector"] = selector
        if process_tag != "same":
            process["platform"]["cpu_model"] = f"{process_tag}-cpu"
            process["launch"]["identity"] = f"{process_tag}-{process['role']}"
            for descriptor in ("descriptor_pre", "descriptor_post_exe", "descriptor_post_fd"):
                process["execution_identity"][descriptor]["inode"] += 1
            process["lifecycle"]["rusage"] = {"user_seconds": 1.0, "system_seconds": 0.0, "max_rss": 1, "minor_faults": 0, "major_faults": 0, "involuntary_context_switches": 0, "voluntary_context_switches": 0}
    if result_status == "failed":
        processes[0]["outcome"] = {"status": "failed", "code": "synthetic-failure", "detail": "bounded synthetic failure"}
    elif result_status == "inconclusive":
        processes[0] = evidence_fixture._process("development", 8, adjudications, incomplete=True)
    result = evidence.build_result(attempt, adjudications, processes, evidence_fixture._tools())
    result_value = json.loads(result)
    attempt = result_value["attempt"]
    admission_raw = _admission(**(admission_kwargs or {}))
    custody_raw = _custody(ordinal, selector)
    authorization_raw = _authorization(ordinal, selector, attempt_id, admission_raw, custody_raw)
    attempt["gate_b_admission_sha256"] = hashlib.sha256(admission_raw).hexdigest()
    attempt["authorization_record_sha256"] = hashlib.sha256(authorization_raw).hexdigest()
    attempt["custody_record_sha256"] = json.loads(custody_raw)["custody_record_sha256"]
    result = evidence.build_result(attempt, adjudications, processes, evidence_fixture._tools())
    receipt = evidence.build_receipt(result)
    index = evidence.build_attempt_index(result, receipt)
    return {"ordinal": ordinal, "freeze_manifest": b"synthetic-freeze\n", "admission": admission_raw, "authorization": authorization_raw, "custody": custody_raw, "result": result, "receipt": receipt, "index": index}


def _freeze() -> dict[str, object]:
    return {"schema": "ck.exp-0002.phase3.freeze-manifest-3", "manifest_sha256": FREEZE_HASH, "execution_permitted": False, "execution_tool_source_commit": EXECUTION_SOURCE_COMMIT}


class ExperimentClosureTests(unittest.TestCase):
    def test_empty_or_partial_closure_is_inconclusive_and_never_supported(self) -> None:
        raw = closure.build_experiment_closure([])
        value = closure.validate_experiment_closure(raw)
        self.assertEqual(value["status"], "inconclusive")
        self.assertNotEqual(value["status"], "supported")
        self.assertEqual([item["ordinal"] for item in value["attempts"]], [0, 1, 2])
        self.assertTrue(all(item["attempt_status"] is None for item in value["attempts"]))

    def test_duplicate_and_extra_ordinals_fail_closed(self) -> None:
        for records, code in (([{"ordinal": 0}, {"ordinal": 0}], "duplicate"), ([{"ordinal": 9}], "ordinal")):
            with self.subTest(code=code), self.assertRaises(closure.ExperimentClosureError) as error:
                closure.build_experiment_closure(records)
            self.assertEqual(error.exception.code, code)

    def test_closure_self_hash_is_not_resealable_without_recomputation(self) -> None:
        raw = closure.build_experiment_closure([])
        value = json.loads(raw)
        value["status"] = "supported"
        forged = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(closure.ExperimentClosureError) as error:
            closure.validate_experiment_closure(forged)
        self.assertEqual(error.exception.code, "closure-self-hash")

    def test_authenticated_supported_triplet_ignores_runtime_observation_drift(self) -> None:
        records = [_attempt_record(index, process_tag=f"platform-{index}") for index in range(3)]
        with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()):
            value = closure.validate_experiment_closure(closure.build_experiment_closure(records, allow_missing=False))
        self.assertEqual(value["status"], "supported")
        self.assertTrue(value["comparison"]["semantic_equality"])

    def test_supported_semantic_disagreement_fails(self) -> None:
        records = [_attempt_record(index, semantic_disagreement=index == 2) for index in range(3)]
        with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()):
            value = json.loads(closure.build_experiment_closure(records, allow_missing=False))
        self.assertEqual(value["status"], "failed")
        self.assertEqual(value["reason"], "semantic-output-mismatch")

    def test_failed_and_inconclusive_attempts_have_global_precedence_without_semantic_mismatch(self) -> None:
        failed = [_attempt_record(index, result_status="failed", process_tag=f"failed-{index}") for index in range(3)]
        with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()):
            value = json.loads(closure.build_experiment_closure(failed, allow_missing=False))
        self.assertEqual(value["status"], "failed")
        self.assertEqual(value["reason"], "attempt-failed")

        inconclusive = [_attempt_record(index, result_status="inconclusive", process_tag=f"partial-{index}") for index in range(3)]
        with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()):
            value = json.loads(closure.build_experiment_closure(inconclusive, allow_missing=False))
        self.assertEqual(value["status"], "inconclusive")
        self.assertEqual(value["reason"], "incomplete-attempt-closure")

    def test_freeze_and_custody_cross_bindings_are_authenticated(self) -> None:
        record = _attempt_record(0)
        tampered_custody = json.loads(record["custody"])
        tampered_custody["candidate"]["bytes"] = 2
        record["custody"] = closure._canonical(tampered_custody)
        records = [record, _attempt_record(1), _attempt_record(2)]
        with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()), self.assertRaises(closure.ExperimentClosureError) as error:
            closure.build_experiment_closure(records, allow_missing=False)
        self.assertEqual(error.exception.code, "record-hash")

        record = _attempt_record(0)
        result_value = json.loads(record["result"])
        result_value["attempt"]["freeze_manifest_sha256"] = "0" * 64
        record["result"] = evidence.build_result(result_value)
        record["receipt"] = evidence.build_receipt(record["result"])
        record["index"] = evidence.build_attempt_index(record["result"], record["receipt"])
        records = [record, _attempt_record(1), _attempt_record(2)]
        with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()), self.assertRaises(closure.ExperimentClosureError) as error:
            closure.build_experiment_closure(records, allow_missing=False)
        self.assertEqual(error.exception.code, "result-binding")

    def test_admission_commit_bindings_follow_frozen_source_and_distinct_review_target(self) -> None:
        cases = (
            {"execution_source": "c" * 40},
            {"execution_source": "not-a-commit"},
            {"reviewed_commit": EXECUTION_SOURCE_COMMIT},
            {"reviewed_commit": "not-a-commit"},
        )
        for admission_kwargs in cases:
            with self.subTest(admission_kwargs=admission_kwargs):
                records = [_attempt_record(index, admission_kwargs=admission_kwargs) for index in range(3)]
                with mock.patch.object(closure, "_validate_freeze", return_value=_freeze()), self.assertRaises(closure.ExperimentClosureError) as error:
                    closure.build_experiment_closure(records, allow_missing=False)
                self.assertEqual(error.exception.code, "admission-binding")


if __name__ == "__main__":
    unittest.main()

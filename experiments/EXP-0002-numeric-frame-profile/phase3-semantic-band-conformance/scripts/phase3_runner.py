"""Closed, in-memory, synthetic-only Phase 3 runner."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

import phase3_oracle as oracle
import phase3_scorer as scorer
from phase3_common import (
    FRAME_BYTES, MAX_REQUEST_ID_BYTES, MAX_SESSION_RECORDS, MAX_SOURCE_BYTES,
    REQUEST_PROTOCOL_ID, Phase3Error, as_fraction,
)

MAX_TRANSCRIPT_BYTES = FRAME_BYTES * MAX_SESSION_RECORDS
CASE_REQUIRED = frozenset({"protocol_id", "request_id", "operation", "resource_profile", "source", "tolerances", "providers", "metric"})
CASE_OPTIONAL = frozenset({"dispatch_to_candidate", "expected_class", "expected_classification", "observation_only", "synthetic_case_id", "expected_response_status", "expected_cause", "translation_scale"})
TOLERANCE_KEYS = frozenset({"translation_absolute", "translation_relative", "rotation_half_chord"})
PROVIDER_KEYS = frozenset({"gate", "arithmetic", "sqrt", "environment"})
EXPLICIT_FORBIDDEN = frozenset({
    "execution_permitted", "candidate_argv", "candidate_path", "candidate_binary", "candidate_executable",
    "command", "shell", "cwd", "env", "environment_variables", "profile", "profile_binding",
    "freeze", "freeze_manifest", "freeze_manifest_identity", "authorization", "authorization_reference",
    "r3", "r3_active", "r3_activation", "execute", "acknowledge",
})


class RunnerError(Phase3Error):
    pass


def _fail(code: str, detail: str) -> None:
    raise RunnerError(code, detail)


def _plain_json_value(value: Any, label: str) -> None:
    if callable(value):
        _fail("negative-capability", f"{label} is callable")
    if isinstance(value, float) and not math.isfinite(value):
        _fail("case-shape", f"{label} is non-finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _plain_json_value(item, f"{label}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("case-shape", f"{label} has a non-string key")
            if key in EXPLICIT_FORBIDDEN:
                _fail("negative-capability", f"{label}.{key} is forbidden")
            _plain_json_value(item, f"{label}.{key}")
        return
    _fail("negative-capability", f"{label} contains unsupported {type(value).__name__}")


def _case_list(cases: Any) -> list[dict[str, Any]]:
    if type(cases) is not list:
        _fail("cases", "cases must be a plain list")
    if len(cases) > MAX_SESSION_RECORDS:
        _fail("case-count", "synthetic case count exceeds 64")
    result = []
    for index, case in enumerate(cases):
        if type(case) is not dict:
            _fail("case-shape", f"case[{index}] must be a plain object")
        _plain_json_value(case, f"case[{index}]")
        keys = set(case)
        forbidden = keys & EXPLICIT_FORBIDDEN
        if forbidden:
            _fail("negative-capability", f"case[{index}] contains {sorted(forbidden)[0]}")
        if not CASE_REQUIRED <= keys or keys - CASE_REQUIRED - CASE_OPTIONAL:
            _fail("case-shape", f"case[{index}] violates the closed synthetic schema")
        if case["protocol_id"] != REQUEST_PROTOCOL_ID or case["operation"] != "observe-authored-conflict" or case["resource_profile"] != "ordinary":
            _fail("case-contract", f"case[{index}] candidate request contract differs")
        request_id = case["request_id"]
        if not isinstance(request_id, str) or not request_id or len(request_id.encode("utf-8")) > MAX_REQUEST_ID_BYTES:
            _fail("request-id", f"case[{index}] request_id is invalid")
        if not (request_id.startswith("synthetic-") or request_id.startswith("synthetic/")):
            _fail("non-synthetic-id", f"case[{index}] request_id is not synthetic")
        if not isinstance(case["source"], str) or len(case["source"].encode("utf-8")) > MAX_SOURCE_BYTES:
            _fail("source", f"case[{index}] source is invalid or oversized")
        if type(case["tolerances"]) is not dict or set(case["tolerances"]) != TOLERANCE_KEYS:
            _fail("case-shape", f"case[{index}].tolerances violates its closed schema")
        try:
            for field in TOLERANCE_KEYS:
                as_fraction(case["tolerances"][field], f"case[{index}].tolerances.{field}")
        except Phase3Error as error:
            _fail("case-shape", f"case[{index}] tolerance is invalid: {error.code}")
        if type(case["providers"]) is not dict or set(case["providers"]) != PROVIDER_KEYS:
            _fail("case-shape", f"case[{index}].providers violates its closed schema")
        providers = case["providers"]
        if providers["gate"] not in {"allow", "reject"} or providers["arithmetic"] not in {"native", "unavailable"} or providers["sqrt"] not in {"native", "unavailable"} or providers["environment"] != "unattested-no-probe-v1":
            _fail("case-contract", f"case[{index}] provider selection is invalid")
        if case["metric"] not in {"translation", "rotation"}:
            _fail("case-contract", f"case[{index}] metric is invalid")
        if "dispatch_to_candidate" in case and not isinstance(case["dispatch_to_candidate"], bool):
            _fail("case-shape", f"case[{index}].dispatch_to_candidate must be boolean")
        if "observation_only" in case and not isinstance(case["observation_only"], bool):
            _fail("case-shape", f"case[{index}].observation_only must be boolean")
        expected_class = case.get("expected_class", case.get("expected_classification"))
        if expected_class is not None and expected_class not in {"agree", "conflict", "skipped", "rejected"}:
            _fail("case-shape", f"case[{index}] expected classification is invalid")
        if "expected_class" in case and "expected_classification" in case:
            _fail("case-shape", f"case[{index}] has duplicate expected classification fields")
        if "expected_response_status" in case:
            if case["expected_response_status"] not in {"rejected", "unsupported", "error", "resource-limit"} or "expected_cause" not in case:
                _fail("case-shape", f"case[{index}] expected response metadata is incomplete")
            try:
                scorer.stable_cause(case["expected_cause"], f"case[{index}].expected_cause")
            except Phase3Error as error:
                _fail("case-shape", f"case[{index}] expected cause is invalid: {error.code}")
        elif "expected_cause" in case:
            _fail("case-shape", f"case[{index}] expected_cause lacks expected_response_status")
        if "synthetic_case_id" in case and (not isinstance(case["synthetic_case_id"], str) or not case["synthetic_case_id"] or len(case["synthetic_case_id"].encode("utf-8")) > MAX_REQUEST_ID_BYTES):
            _fail("case-shape", f"case[{index}] synthetic_case_id is invalid")
        if "translation_scale" in case:
            try:
                if as_fraction(case["translation_scale"], f"case[{index}].translation_scale") < 0:
                    _fail("case-shape", f"case[{index}] translation_scale is negative")
            except Phase3Error as error:
                _fail("case-shape", f"case[{index}] translation_scale is invalid: {error.code}")
        result.append(case)
    ids = [item["request_id"] for item in result]
    if len(ids) != len(set(ids)):
        _fail("duplicate-request-id", "synthetic request IDs must be unique")
    return result


def _transcript(value: Any) -> dict[str, bytes]:
    if type(value) is not dict:
        _fail("transcript", "transcript must be a plain mapping")
    if len(value) > MAX_SESSION_RECORDS:
        _fail("transcript-count", "transcript exceeds 64 records")
    total = 0
    result: dict[str, bytes] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or type(raw) is not bytes:
            _fail("transcript-shape", "transcript must map string IDs to bytes")
        if len(raw) > FRAME_BYTES:
            # Retain the frame for per-case adjudication, while still applying
            # the bounded aggregate accounting before any parse.
            pass
        total += len(raw)
        if total > MAX_TRANSCRIPT_BYTES:
            _fail("transcript-total-bytes", "transcript exceeds 4 MiB")
        result[key] = raw
    return result


def _overall(counts: Mapping[str, int]) -> str:
    if counts["failed"]:
        return "failed"
    if counts["inconclusive"]:
        return "inconclusive"
    if counts["observation"] and not counts["supported"]:
        return "inconclusive"
    return "supported"


def run_synthetic(cases: Any, transcript: Any) -> dict[str, Any]:
    case_list = _case_list(cases)
    frames = _transcript(transcript)
    entries: list[dict[str, Any]] = []
    used: set[str] = set()
    synthetic_dispatches = 0
    preflight_count = 0
    for case in case_list:
        request_id = case["request_id"]
        dispatch = case.get("dispatch_to_candidate", True)
        try:
            truth = oracle.evaluate_source(case["source"], case["metric"])
        except Phase3Error as error:
            entries.append({"request_id": request_id, "status": "inconclusive", "classification": "incomplete", "preflight": True, "cause": {"code": f"oracle:{error.code}"}})
            preflight_count += 1
            continue
        if not dispatch or truth["status"] == "out-of-domain":
            # Deliberately do not index, parse, or otherwise inspect a keyed
            # transcript frame for preflight-only adjudication.
            preflight_count += 1
            preflight_status = "inconclusive"
            if truth["status"] == "out-of-domain":
                preflight_status = "observation" if case.get("observation_only", False) else "supported"
            entries.append({"request_id": request_id, "status": preflight_status, "classification": truth["status"], "preflight": True, "cause": {"code": "out-of-domain" if truth["status"] == "out-of-domain" else "dispatch-disabled"}})
            continue
        synthetic_dispatches += 1
        if request_id not in frames:
            entries.append({"request_id": request_id, "status": "inconclusive", "classification": "incomplete", "preflight": False, "cause": {"code": "missing-response"}})
            continue
        used.add(request_id)
        raw = frames[request_id]
        result = scorer.score_response(case, truth, raw, expected_class=case.get("expected_class", case.get("expected_classification")), observation_only=case.get("observation_only", False))
        result.update({"request_id": request_id, "preflight": False})
        entries.append(result)
    extras = sorted(set(frames) - used)
    for request_id in extras:
        entries.append({"request_id": request_id, "status": "inconclusive", "classification": "incomplete", "preflight": True, "cause": {"code": "extra-response"}})
    counts = {name: sum(1 for item in entries if item["status"] == name) for name in ("supported", "failed", "inconclusive", "observation")}
    counts.update({"cases": len(case_list), "entries": len(entries), "extra_responses": len(extras)})
    return {
        "schema": "ck.exp-0002.phase3.synthetic-run-result-2",
        "mode": "synthetic-validation",
        "evidence_eligible": False,
        "technology_result": "none",
        "profile_binding": None,
        "freeze_manifest_identity": None,
        "authorization_reference": None,
        "r3_activation": "inactive",
        "status": _overall(counts),
        "synthetic_dispatches": synthetic_dispatches,
        "preflight_count": preflight_count,
        "tool_identities": [],
        "counts": counts,
        "entries": entries,
    }


run = run_synthetic
__all__ = ["RunnerError", "run_synthetic", "run"]

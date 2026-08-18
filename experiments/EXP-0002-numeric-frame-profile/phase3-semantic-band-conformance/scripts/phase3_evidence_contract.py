"""Execution-incapable Phase 3 result, receipt, and attempt-index contract.

This module is deliberately a writer for *already observed* values.  It does
not know how to launch a candidate, inspect a process, or read a package.  The
only bytes it creates are canonical in-memory JSON bytes.  The witness shape
is intentionally still Proposed: each adjudication retains a bounded
canonical evidence object and its digest, rather than pretending that the
future exact witness schema has already been frozen.
"""

from __future__ import annotations

import hashlib
import base64
import json
import math
import os
import re
import struct
from pathlib import Path
from typing import Any, Mapping

import phase3_oracle as oracle
import phase3_scorer as scorer
from phase3_common import FRAME_BYTES, REQUEST_PROTOCOL_ID, RESPONSE_PROTOCOL_ID, canonical_json, parse_json


RESULT_SCHEMA = "ck.exp-0002.phase3.exact-attempt-result-1"
RECEIPT_SCHEMA = "ck.exp-0002.phase3.exact-attempt-receipt-1"
ATTEMPT_INDEX_SCHEMA = "ck.exp-0002.phase3.immutable-attempt-index-1"
EVIDENCE_SCHEMA = "ck.exp-0002.phase3.evidence-proposed-1"
EXPERIMENT_ID = "EXP-0002"
PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"

MAX_RESULT_BYTES = 16 * 1024 * 1024
MAX_RECEIPT_BYTES = 256 * 1024
MAX_INDEX_BYTES = 64 * 1024
MAX_STRING_BYTES = 128 * 1024
MAX_ID_BYTES = 256
MAX_EVIDENCE_BYTES = 512 * 1024
MAX_ARRAY_ITEMS = 256
MAX_OBJECT_MEMBERS = 128
MAX_NESTING = 16
MAX_PROCESS_OBSERVATIONS = 3
MAX_ADJUDICATIONS = 60
MAX_TOOLS = 32
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ATTEMPT_RE = re.compile(r"^attempt-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
TOOL_ORDER = (
    "scripts/phase3_common.py", "scripts/phase3_oracle.py", "scripts/phase3_scorer.py",
    "scripts/phase3_runner.py", "scripts/phase3_receipt.py",
    "scripts/phase3_materialized_adapter.py", "scripts/phase3_evidence_contract.py",
    "scripts/phase3_gate_b_preflight.py",
)

ROLE_COUNTS = {"development": 8, "held-out": 40, "controls": 12}
PROCESS_REQUEST_COUNTS = {"development": 8, "held-out": 40, "controls": 9}
PLATFORM_SELECTORS = frozenset({
    "wsl2-x86_64", "ubuntu-24.04-x86_64", "WSL2 x86_64 GNU/Linux", "Ubuntu 24.04 x86_64",
})
STATUSES = frozenset({"supported", "failed", "inconclusive", "observation"})
CLASSIFICATIONS = frozenset({
    "agree", "conflict", "skipped", "rejected", "out-of-domain",
    "incomplete", "observation", "supported", "failed", "inconclusive",
    "witness-mismatch", "classification-mismatch", "expected-class-mismatch",
    "straddling", "interval-cap", "candidate-not-observed", "malformed",
})

RESULT_KEYS = frozenset({
    "schema", "evidence_schema", "binding", "attempt", "tool_identities", "adjudications",
    "process_observations", "counts", "status",
})
ATTEMPT_KEYS = frozenset({
    "freeze_manifest_sha256", "attempt_id", "platform_selector", "ordinal",
    "authorization_reference",
})
ADJUDICATION_KEYS = frozenset({
    "ordinal", "request_id", "role", "dispatch_to_candidate", "status",
    "classification", "evidence", "evidence_sha256",
})
EVIDENCE_KEYS = frozenset({"schema", "payload"})
DISPATCHED_EVIDENCE_KEYS = frozenset({
    "variant", "response", "request", "scorer_context", "oracle_result", "scorer_result",
})
PREFLIGHT_EVIDENCE_KEYS = frozenset({"variant", "runner", "classification", "cause"})
INCOMPLETE_DISPATCHED_EVIDENCE_KEYS = frozenset({"variant", "request", "response", "scorer_context", "reason", "cause"})
INCOMPLETE_PREFLIGHT_EVIDENCE_KEYS = frozenset({"variant", "reason", "cause"})
RESPONSE_KEYS = frozenset({"bytes_b64", "sha256"})
REQUEST_KEYS = frozenset({"bytes_b64", "sha256"})
REQUEST_WIRE_KEYS = frozenset({
    "protocol_id", "request_id", "operation", "resource_profile", "source",
    "tolerances", "providers", })
SCORER_CONTEXT_KEYS = frozenset({
    "metric", "observation_only", "expected_class", "expected_response_status", "expected_cause",
})
CAUSE_KEYS = frozenset({"code", "detail"})
RUNNER_KEYS = frozenset({"reason", "domain_status"})
PLATFORM_KEYS = frozenset({
    "selector", "cpu_model", "cpu_features", "architecture", "kernel_or_wsl",
    "os_release", "filesystem", "mount_context", "workflow_runner", "workflow_image",
    "toolchain", "compiler",
})
FE_STATE_KEYS = frozenset({"fe_rounding", "mxcsr", "ftz", "daz"})
PROCESS_KEYS = frozenset({
    "variant", "role", "candidate_request_count", "platform", "launch", "candidate_binary",
    "fe_mxcsr", "transport", "lifecycle", "output",
})
INCOMPLETE_PROCESS_KEYS = frozenset({
    "variant", "role", "candidate_request_count", "platform", "launch", "candidate_binary",
    "fe_mxcsr", "transport", "lifecycle", "output", "missing",
})
LAUNCH_KEYS = frozenset({"identity", "argv", "cwd", "environment"})
HASH_PAIR_KEYS = frozenset({"count", "sha256"})
CANDIDATE_HASH_KEYS = frozenset({"sha256_pre", "sha256_post"})
FE_KEYS = frozenset({"pre", "post"})
LIFECYCLE_KEYS = frozenset({"state", "exit_code", "clean_shutdown"})
OUTPUT_KEYS = frozenset({"missing", "extra", "trailing"})
TRANSPORT_KEYS = frozenset({"requests", "responses"})
COUNTS_KEYS = frozenset({
    "cases", "development", "held-out", "controls", "dispatched", "preflight",
    "supported", "failed", "inconclusive", "observation",
})
RECEIPT_KEYS = frozenset({
    "schema", "evidence_schema", "binding", "result_sha256", "attempt", "tool_identities",
    "processes", "counts", "status",
})
RECEIPT_PROCESS_KEYS = frozenset({
    "variant", "role", "candidate_request_count", "request_count", "request_sha256",
    "response_count", "response_sha256", "candidate_sha256_pre",
    "candidate_sha256_post",
})
RECEIPT_INCOMPLETE_PROCESS_KEYS = frozenset({"variant", "role", "candidate_request_count", "partial_observation"})

REQUEST_FRAME_DOMAIN = b"ck.exp-0002.phase3.request-frames.v1\0"
RESPONSE_FRAME_DOMAIN = b"ck.exp-0002.phase3.response-frames.v1\0"
INDEX_KEYS = frozenset({
    "schema", "evidence_schema", "binding", "attempt", "result_sha256", "receipt_sha256",
    "envelope_sha256",
})


class EvidenceContractError(ValueError):
    """Stable bounded contract error."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", " ")[:256]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str) -> None:
    raise EvidenceContractError(code, detail)


def _plain(value: Any, label: str, depth: int = 0, *, reject_evidence_names: bool = False) -> None:
    """Reject Python container/type tricks before any JSON canonicalization."""
    if depth > MAX_NESTING:
        _fail("nesting-limit", f"{label} exceeds {MAX_NESTING} levels")
    if callable(value):
        _fail("non-plain-value", f"{label} is callable")
    if isinstance(value, (Path, os.PathLike)):
        _fail("non-plain-value", f"{label} is a path/container value")
    if type(value) is float:
        if not math.isfinite(value):
            _fail("nonfinite", f"{label} is non-finite")
        return
    if value is None or type(value) in (bool, int, str):
        if type(value) is int and value.bit_length() > 640:
            _fail("integer-limit", f"{label} exceeds bounded integer width")
        if type(value) is str:
            try:
                size = len(value.encode("utf-8"))
            except UnicodeEncodeError as error:
                raise EvidenceContractError("invalid-utf8", f"{label} is not UTF-8") from error
            if size > MAX_STRING_BYTES:
                _fail("string-limit", f"{label} exceeds {MAX_STRING_BYTES} bytes")
        return
    if type(value) is list:
        if len(value) > MAX_ARRAY_ITEMS:
            _fail("array-limit", f"{label} exceeds {MAX_ARRAY_ITEMS} items")
        for index, item in enumerate(value):
            _plain(item, f"{label}[{index}]", depth + 1, reject_evidence_names=reject_evidence_names)
        return
    if type(value) is dict:
        if len(value) > MAX_OBJECT_MEMBERS:
            _fail("object-limit", f"{label} exceeds {MAX_OBJECT_MEMBERS} members")
        for key, item in value.items():
            if type(key) is not str:
                _fail("non-plain-value", f"{label} has a non-string key")
            if reject_evidence_names and key in {"synthetic", "non_evidence", "evidence_eligible", "runner_only"}:
                _fail("evidence-field", f"{label}.{key} cannot masquerade as evidence")
            _plain(item, f"{label}.{key}", depth + 1, reject_evidence_names=reject_evidence_names)
        return
    _fail("non-plain-value", f"{label} has unsupported type {type(value).__name__}")


def _exact(value: Any, keys: frozenset[str] | set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        _fail("closed-schema", f"{label} has unexpected or missing members")
    return value


def _string(value: Any, label: str, *, max_bytes: int = MAX_STRING_BYTES, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value):
        _fail("string", f"{label} must be a non-empty string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise EvidenceContractError("invalid-utf8", f"{label} is not UTF-8") from error
    if size > max_bytes:
        _fail("string-limit", f"{label} exceeds {max_bytes} bytes")
    return value


def _bounded_int(value: Any, label: str, maximum: int = 1_000_000) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        _fail("integer", f"{label} is not a bounded non-negative integer")
    return value


def _sha(value: Any, label: str) -> str:
    value = _string(value, label, max_bytes=64)
    if SHA256_RE.fullmatch(value) is None:
        _fail("sha256", f"{label} is not lowercase SHA-256")
    return value


def _canonical(value: Any, label: str, limit: int) -> bytes:
    _plain(value, label)
    try:
        raw = canonical_json(value, limit=limit)
    except Exception as error:
        _fail("canonical-json", f"{label} is not canonical JSON")
        raise AssertionError from error
    return raw


def _decode(raw: bytes, label: str, limit: int) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("bytes", f"{label} must be bytes")
    if len(raw) > limit:
        _fail("byte-limit", f"{label} exceeds {limit} bytes")
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                _fail("duplicate-json-member", f"duplicate {label} member {key}")
            out[key] = value
        return out
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=lambda token: _fail("nonfinite", token))
    except EvidenceContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError, TypeError) as error:
        raise EvidenceContractError("malformed-json", f"{label} is malformed") from error
    _plain(value, label)
    if type(value) is not dict:
        _fail("object", f"{label} must be an object")
    expected = _canonical(value, label, limit)
    if raw != expected:
        _fail("noncanonical", f"{label} is not canonical JSON bytes")
    return value


def _attempt(value: Any, label: str = "attempt") -> dict[str, Any]:
    obj = _exact(value, ATTEMPT_KEYS, label)
    _sha(obj["freeze_manifest_sha256"], f"{label}.freeze_manifest_sha256")
    attempt_id = _string(obj["attempt_id"], f"{label}.attempt_id", max_bytes=MAX_ID_BYTES)
    if ATTEMPT_RE.fullmatch(attempt_id) is None or attempt_id in {"attempt-id", "attempt-000"}:
        _fail("attempt-id", f"{label}.attempt_id is a placeholder or invalid")
    platform_selector = _string(obj["platform_selector"], f"{label}.platform_selector", max_bytes=MAX_ID_BYTES)
    if platform_selector not in PLATFORM_SELECTORS:
        _fail("platform-selector", f"{label}.platform_selector is not preregistered")
    ordinal = obj["ordinal"]
    if type(ordinal) is not int or not 0 <= ordinal <= 1_000_000:
        _fail("ordinal", f"{label}.ordinal is invalid")
    authorization = _string(obj["authorization_reference"], f"{label}.authorization_reference", max_bytes=MAX_ID_BYTES)
    if authorization.lower() in {"ben", "authorization", "required", "placeholder", "pending"}:
        _fail("authorization-reference", f"{label}.authorization_reference is a placeholder")
    return obj


def _binding(value: Any, label: str = "binding") -> dict[str, str]:
    obj = _exact(value, frozenset({"experiment_id", "phase_id", "candidate_profile_id"}), label)
    if obj != {"experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID, "candidate_profile_id": CANDIDATE_PROFILE_ID}:
        _fail("binding", f"{label} does not identify the preregistered experiment/profile")
    for key, item in obj.items():
        _string(item, f"{label}.{key}")
    return obj


def _tools(value: Any, label: str = "tool_identities") -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != 8:
        _fail("tool-identities", f"{label} must contain the eight Phase 3 tool identities")
    output: list[dict[str, Any]] = []
    paths: set[str] = set()
    for index, item in enumerate(value):
        obj = _exact(item, frozenset({"path", "bytes", "sha256"}), f"{label}[{index}]")
        path = _string(obj["path"], f"{label}[{index}].path", max_bytes=512)
        if path.startswith(("/", "\\")) or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")):
            _fail("tool-path", f"{label}[{index}].path is not a safe relative identity")
        if path in paths:
            _fail("duplicate-tool", f"duplicate tool identity {path}")
        paths.add(path)
        _bounded_int(obj["bytes"], f"{label}[{index}].bytes", 4 * 1024 * 1024)
        _sha(obj["sha256"], f"{label}[{index}].sha256")
        output.append(obj)
    # This is the preregistered owner order, which remains stable even though
    # ``phase3_evidence_contract`` sorts before ``phase3_materialized_adapter``
    # lexically.  Stable owner order makes cross-object identity comparison
    # unambiguous without inventing a filesystem scan.
    paths_in_order = [item["path"] for item in output]
    if paths_in_order != list(TOOL_ORDER):
        _fail("tool-order", f"{label} must exactly follow TOOL_ORDER")
    return output


def _cause(value: Any, label: str, *, required: bool = False) -> dict[str, str] | None:
    if value is None:
        if required:
            _fail("evidence-cause", f"{label} is required")
        return None
    obj = _exact(value, CAUSE_KEYS, label)
    _string(obj["code"], f"{label}.code", max_bytes=256)
    _string(obj["detail"], f"{label}.detail", max_bytes=512)
    return obj


def _b64_bytes(value: Any, label: str, limit: int) -> bytes:
    text = _string(value, label, max_bytes=((limit + 2) // 3) * 4 + 4)
    try:
        raw = base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as error:
        raise EvidenceContractError("evidence-bytes", f"{label} is invalid base64") from error
    if len(raw) > limit:
        _fail("byte-limit", f"{label} decodes beyond {limit} bytes")
    return raw


def _wire_request(value: Any, label: str, outer_request_id: str) -> dict[str, Any]:
    wrapper = _exact(value, REQUEST_KEYS, label)
    raw = _b64_bytes(wrapper["bytes_b64"], f"{label}.bytes_b64", FRAME_BYTES)
    _sha(wrapper["sha256"], f"{label}.sha256")
    if wrapper["sha256"] != hashlib.sha256(raw).hexdigest():
        _fail("evidence-hash", f"{label} bytes/hash differ")
    try:
        request = parse_json(raw, label=f"{label} wire")
    except Exception as error:
        raise EvidenceContractError("request-json", f"{label} is not a strict protocol request") from error
    if type(request) is not dict:
        _fail("request-schema", f"{label} wire request must be an object")
    if set(request) != REQUEST_WIRE_KEYS:
        _fail("request-schema", f"{label} wire request has unexpected or missing fields")
    if request.get("protocol_id") != REQUEST_PROTOCOL_ID or request.get("request_id") != outer_request_id:
        _fail("evidence-request-link", f"{label} protocol/request identity differs")
    if request.get("operation") != "observe-authored-conflict" or request.get("resource_profile") != "ordinary":
        _fail("request-contract", f"{label} wire request contract differs")
    if type(request.get("source")) is not str or len(request["source"].encode("utf-8")) > 24 * 1024:
        _fail("request-source", f"{label} source is missing or oversized")
    if type(request.get("tolerances")) is not dict or set(request["tolerances"]) != {"translation_absolute", "translation_relative", "rotation_half_chord"}:
        _fail("request-tolerances", f"{label} tolerances are not closed")
    if type(request.get("providers")) is not dict or set(request["providers"]) != {"gate", "arithmetic", "sqrt", "environment"}:
        _fail("request-providers", f"{label} providers are not closed")
    return request


def _context_cause(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if type(value) is not dict or not {"code", "failure", "field"} <= set(value) or set(value) - {"code", "failure", "field", "index"}:
        _fail("scorer-context", f"{label} is not a closed expected-cause object")
    _string(value["code"], f"{label}.code", max_bytes=256)
    _string(value["failure"], f"{label}.failure", max_bytes=256)
    _string(value["field"], f"{label}.field", max_bytes=256)
    if "index" in value:
        _bounded_int(value["index"], f"{label}.index", 1_000_000)
    return value


def _scorer_context(value: Any, label: str, ordinal: int) -> dict[str, Any]:
    obj = _exact(value, SCORER_CONTEXT_KEYS, label)
    metric = obj["metric"]
    if metric not in {"translation", "rotation"}:
        _fail("scorer-context", f"{label}.metric is invalid")
    expected_observation = ordinal < 8 or ordinal >= 48
    if type(obj["observation_only"]) is not bool or obj["observation_only"] != expected_observation:
        _fail("scorer-context", f"{label}.observation_only differs from the ordinal contract")
    expected_class = obj["expected_class"]
    if 8 <= ordinal < 48:
        if expected_class not in {"agree", "conflict"}:
            _fail("scorer-context", f"{label}.expected_class is required for held-out cases")
    elif expected_class is not None:
        _fail("scorer-context", f"{label}.expected_class must be null outside held-out cases")
    expected_status = obj["expected_response_status"]
    expected_cause = _context_cause(obj["expected_cause"], f"{label}.expected_cause")
    if ordinal == 59:
        if expected_status != "rejected" or expected_cause is None:
            _fail("scorer-context", f"{label} negative-relative control requires rejection context")
    elif expected_status is not None or expected_cause is not None:
        _fail("scorer-context", f"{label} response rejection context is out of ordinal scope")
    return obj


def _wire_response(value: Any, label: str, outer_request_id: str) -> bytes:
    wrapper = _exact(value, RESPONSE_KEYS, label)
    raw = _b64_bytes(wrapper["bytes_b64"], f"{label}.bytes_b64", FRAME_BYTES)
    if not raw:
        _fail("evidence-bytes", f"{label} response is empty")
    _sha(wrapper["sha256"], f"{label}.sha256")
    if wrapper["sha256"] != hashlib.sha256(raw).hexdigest():
        _fail("evidence-hash", f"{label} bytes/hash differ")
    try:
        parsed = parse_json(raw, label=f"{label} wire")
    except Exception as error:
        raise EvidenceContractError("response-json", f"{label} is not a strict protocol response") from error
    if type(parsed) is not dict or parsed.get("protocol_id") != RESPONSE_PROTOCOL_ID or parsed.get("request_id") != outer_request_id:
        _fail("evidence-protocol", f"{label} protocol/request identity differs")
    return raw


def _raw_response(value: Any, label: str, outer_request_id: str) -> bytes:
    """Retain an observed response frame without requiring it to parse."""
    wrapper = _exact(value, RESPONSE_KEYS, label)
    raw = _b64_bytes(wrapper["bytes_b64"], f"{label}.bytes_b64", FRAME_BYTES)
    if not raw:
        _fail("evidence-bytes", f"{label} response is empty")
    _sha(wrapper["sha256"], f"{label}.sha256")
    if wrapper["sha256"] != hashlib.sha256(raw).hexdigest():
        _fail("evidence-hash", f"{label} bytes/hash differ")
    return raw


def _complete_dispatched(payload: Any, label: str, outer_classification: str, outer_status: str, outer_request_id: str, ordinal: int) -> None:
    obj = _exact(payload, DISPATCHED_EVIDENCE_KEYS, label)
    if obj["variant"] != "dispatched-candidate-v1":
        _fail("evidence-variant", f"{label}.variant is not dispatched-candidate-v1")
    request = _wire_request(obj["request"], f"{label}.request", outer_request_id)
    context = _scorer_context(obj["scorer_context"], f"{label}.scorer_context", ordinal)
    scorer_request = dict(request)
    scorer_request["metric"] = context["metric"]
    if context["expected_response_status"] is not None:
        scorer_request["expected_response_status"] = context["expected_response_status"]
        scorer_request["expected_cause"] = context["expected_cause"]
    response_bytes = _wire_response(obj["response"], f"{label}.response", outer_request_id)
    try:
        oracle_result = oracle.evaluate_source(request["source"], context["metric"])
    except Exception as error:
        raise EvidenceContractError("oracle-result", f"{label} source cannot be evaluated") from error
    _plain(obj["oracle_result"], f"{label}.oracle_result")
    if obj["oracle_result"] != oracle_result:
        _fail("oracle-mismatch", f"{label} retained oracle result differs")
    try:
        scored = scorer.score_response(
            scorer_request, oracle_result, response_bytes,
            expected_class=context["expected_class"], observation_only=context["observation_only"],
        )
    except Exception as error:
        raise EvidenceContractError("scorer-result", f"{label} response cannot be scored") from error
    _plain(obj["scorer_result"], f"{label}.scorer_result")
    if obj["scorer_result"] != scored:
        _fail("scorer-mismatch", f"{label} retained scorer result differs")
    if scored.get("status") != outer_status or scored.get("classification") != outer_classification:
        _fail("evidence-classification", f"{label} scorer result contradicts adjudication")
    if scored.get("status") in {"failed", "inconclusive"} and not isinstance(scored.get("cause"), dict):
        _fail("evidence-cause", f"{label} non-supporting score requires a cause")
    if ordinal in {52, 53, 54, 55} and outer_classification != "skipped":
        _fail("classification-order", f"{label} typed controls must classify skipped")
    if ordinal == 59 and outer_classification != "rejected":
        _fail("classification-order", f"{label} negative-relative control must classify rejected")


def _incomplete_dispatched(payload: Any, label: str, outer_request_id: str, ordinal: int) -> None:
    obj = _exact(payload, INCOMPLETE_DISPATCHED_EVIDENCE_KEYS, label)
    if obj["variant"] != "dispatched-incomplete-v1":
        _fail("evidence-variant", f"{label}.variant is not dispatched-incomplete-v1")
    _wire_request(obj["request"], f"{label}.request", outer_request_id)
    _scorer_context(obj["scorer_context"], f"{label}.scorer_context", ordinal)
    if obj["response"] is not None:
        _raw_response(obj["response"], f"{label}.response", outer_request_id)
    _string(obj["reason"], f"{label}.reason", max_bytes=256)
    _cause(obj["cause"], f"{label}.cause", required=True)


def _evidence(value: Any, label: str, *, dispatched: bool, status: str, classification: str, request_id: str, ordinal: int) -> tuple[dict[str, Any], str]:
    # Normalize once, then apply exactly one plain-value traversal.  The
    # wrapper is a Proposed schema marker; its variants are closed below.
    if type(value) is dict and set(value) == EVIDENCE_KEYS and value.get("schema") == EVIDENCE_SCHEMA:
        evidence = value
    else:
        evidence = {"schema": EVIDENCE_SCHEMA, "payload": value}
    _exact(evidence, EVIDENCE_KEYS, label)
    _plain(evidence, label, reject_evidence_names=True)
    if evidence["schema"] != EVIDENCE_SCHEMA or type(evidence["payload"]) is not dict:
        _fail("evidence-schema", f"{label} must be a Proposed object payload")
    payload = evidence["payload"]
    variant = payload.get("variant")
    if status == "inconclusive":
        if dispatched:
            if classification != "incomplete":
                _fail("evidence-classification", f"{label} incomplete classification contradicts dispatch")
            _incomplete_dispatched(payload, label, request_id, ordinal)
        else:
            if set(payload) != INCOMPLETE_PREFLIGHT_EVIDENCE_KEYS or variant != "runner-preflight-incomplete-v1":
                _fail("evidence-incomplete", f"{label} inconclusive evidence must be a closed incomplete variant")
            if classification != "out-of-domain":
                _fail("evidence-classification", f"{label} incomplete classification contradicts dispatch")
            _string(payload["reason"], f"{label}.reason", max_bytes=256)
            _cause(payload["cause"], f"{label}.cause", required=True)
    elif dispatched:
        _complete_dispatched(payload, label, classification, status, request_id, ordinal)
    else:
        obj = _exact(payload, PREFLIGHT_EVIDENCE_KEYS, label)
        if obj["variant"] != "runner-preflight-v1":
            _fail("evidence-variant", f"{label}.variant is not runner-preflight-v1")
        runner = _exact(obj["runner"], RUNNER_KEYS, f"{label}.runner")
        _string(runner["reason"], f"{label}.runner.reason", max_bytes=256)
        _string(runner["domain_status"], f"{label}.runner.domain_status", max_bytes=128)
        if obj["classification"] != classification or classification != "out-of-domain":
            _fail("evidence-classification", f"{label} preflight classification contradicts out-of-domain")
        _cause(obj["cause"], f"{label}.cause", required=status == "failed")
    raw = _canonical(evidence, label, MAX_EVIDENCE_BYTES)
    return evidence, hashlib.sha256(raw).hexdigest()


def _adjudication(value: Any, index: int, attempt_id: str) -> dict[str, Any]:
    obj = _exact(value, ADJUDICATION_KEYS, f"adjudication[{index}]")
    ordinal = obj["ordinal"]
    if ordinal != index:
        _fail("adjudication-order", f"adjudication[{index}] ordinal differs")
    expected_id = f"p3-{attempt_id}-{index:03d}"
    if obj["request_id"] != expected_id:
        _fail("request-id", f"adjudication[{index}] request ID differs")
    _string(obj["request_id"], f"adjudication[{index}].request_id", max_bytes=MAX_ID_BYTES)
    expected_role = "development" if index < 8 else "held-out" if index < 48 else "controls"
    role = obj["role"]
    if role != expected_role:
        _fail("role-order", f"adjudication[{index}] role differs from preregistered ordinal layout")
    if type(obj["dispatch_to_candidate"]) is not bool:
        _fail("dispatch", f"adjudication[{index}] dispatch flag is invalid")
    expected_dispatch = index not in {56, 57, 58}
    if obj["dispatch_to_candidate"] != expected_dispatch:
        _fail("dispatch-role", f"adjudication[{index}] dispatch flag differs from preregistered layout")
    if obj["status"] not in STATUSES:
        _fail("status", f"adjudication[{index}] status is invalid")
    if obj["status"] == "supported" and not 8 <= index < 48:
        _fail("status-classification", f"only held-out adjudications may be supported ({index})")
    if obj["status"] == "observation" and 8 <= index < 48:
        _fail("status-classification", f"held-out adjudication {index} cannot be observation-only")
    if obj["classification"] not in CLASSIFICATIONS:
        _fail("classification", f"adjudication[{index}] classification is invalid")
    expected_classifications = {"skipped"} if 52 <= index <= 55 else {"rejected"} if index == 59 else {"out-of-domain"} if 56 <= index <= 58 else {"agree", "conflict"}
    if obj["status"] in {"supported", "observation"} and obj["classification"] not in expected_classifications:
        _fail("classification-order", f"adjudication[{index}] classification differs from preregistered role")
    evidence, evidence_sha = _evidence(
        obj["evidence"], f"adjudication[{index}].evidence",
        dispatched=obj["dispatch_to_candidate"], status=obj["status"], classification=obj["classification"], request_id=obj["request_id"], ordinal=index,
    )
    if obj["evidence_sha256"] != evidence_sha:
        _fail("evidence-hash", f"adjudication[{index}] evidence SHA differs")
    normalized = dict(obj)
    normalized["evidence"] = evidence
    return normalized


def _framed_hash(frames: list[bytes], domain: bytes) -> str:
    body = bytearray(domain)
    for frame in frames:
        body.extend(struct.pack(">Q", len(frame)))
        body.extend(frame)
    return hashlib.sha256(bytes(body)).hexdigest()


def _hash_pair(value: Any, label: str, domain: bytes) -> dict[str, Any]:
    obj = _exact(value, HASH_PAIR_KEYS, label)
    _bounded_int(obj["count"], f"{label}.count", MAX_ADJUDICATIONS)
    _sha(obj["sha256"], f"{label}.sha256")
    return obj


def _platform(value: Any, label: str, selector: str) -> dict[str, Any]:
    obj = _exact(value, PLATFORM_KEYS, label)
    if obj["selector"] != selector or selector not in PLATFORM_SELECTORS:
        _fail("platform-selector", f"{label}.selector differs from the attempt selector")
    for key in PLATFORM_KEYS - {"cpu_features"}:
        _string(obj[key], f"{label}.{key}", max_bytes=1024)
    features = obj["cpu_features"]
    if type(features) is not list or not features or len(features) > 128:
        _fail("platform-features", f"{label}.cpu_features is empty or oversized")
    for index, feature in enumerate(features):
        _string(feature, f"{label}.cpu_features[{index}]", max_bytes=256)
    return obj


def _fe_state(value: Any, label: str) -> dict[str, Any]:
    obj = _exact(value, FE_STATE_KEYS, label)
    _string(obj["fe_rounding"], f"{label}.fe_rounding", max_bytes=128)
    _string(obj["mxcsr"], f"{label}.mxcsr", max_bytes=64)
    if type(obj["ftz"]) is not bool or type(obj["daz"]) is not bool:
        _fail("fe-mxcsr", f"{label}.ftz/daz must be boolean")
    return obj


def _process(value: Any, index: int, selector: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("process-schema", f"process observation {index} is not an object")
    if value.get("variant") == "incomplete-v1":
        obj = _exact(value, INCOMPLETE_PROCESS_KEYS, f"process_observations[{index}]")
        if obj["role"] not in ROLE_COUNTS:
            _fail("process-role", f"process observation {index} role is invalid")
        _bounded_int(obj["candidate_request_count"], f"process[{index}].candidate_request_count", MAX_ADJUDICATIONS)
        if obj["candidate_request_count"] != PROCESS_REQUEST_COUNTS[obj["role"]]:
            _fail("process-count", f"process observation {obj['role']} request count differs")
        if obj["platform"] is not None:
            _platform(obj["platform"], f"process[{index}].platform", selector)
        if obj["launch"] is not None:
            launch = _exact(obj["launch"], LAUNCH_KEYS, f"process[{index}].launch")
            _string(launch["identity"], f"process[{index}].launch.identity")
            if type(launch["argv"]) is not list or not 1 <= len(launch["argv"]) <= 64:
                _fail("launch-argv", f"process[{index}].launch.argv is invalid")
            for n, item in enumerate(launch["argv"]):
                _string(item, f"process[{index}].launch.argv[{n}]", max_bytes=1024)
            _string(launch["cwd"], f"process[{index}].launch.cwd", max_bytes=2048)
            if type(launch["environment"]) is not dict:
                _fail("launch-environment", f"process[{index}].launch.environment is not an object")
            for key, item in launch["environment"].items():
                _string(key, f"process[{index}].launch.environment key", max_bytes=256)
                if item is not None:
                    _string(item, f"process[{index}].launch.environment.{key}", max_bytes=2048, nonempty=False)
        if obj["candidate_binary"] is not None:
            binary = _exact(obj["candidate_binary"], CANDIDATE_HASH_KEYS, f"process[{index}].candidate_binary")
            _sha(binary["sha256_pre"], f"process[{index}].candidate_binary.sha256_pre")
            _sha(binary["sha256_post"], f"process[{index}].candidate_binary.sha256_post")
        if obj["fe_mxcsr"] is not None:
            fe = _exact(obj["fe_mxcsr"], FE_KEYS, f"process[{index}].fe_mxcsr")
            for key in FE_KEYS:
                _fe_state(fe[key], f"process[{index}].fe_mxcsr.{key}")
        transport = _exact(obj["transport"], TRANSPORT_KEYS, f"process[{index}].transport")
        for key, domain in (("requests", REQUEST_FRAME_DOMAIN), ("responses", RESPONSE_FRAME_DOMAIN)):
            if transport[key] is not None:
                _hash_pair(transport[key], f"process[{index}].transport.{key}", domain)
        if obj["lifecycle"] is not None:
            lifecycle = _exact(obj["lifecycle"], LIFECYCLE_KEYS, f"process[{index}].lifecycle")
            if lifecycle["state"] not in {"exited", "terminated", "failed"} or type(lifecycle["exit_code"]) is not int or not -128 <= lifecycle["exit_code"] <= 255 or type(lifecycle["clean_shutdown"]) is not bool:
                _fail("lifecycle", f"process[{index}] lifecycle observation is invalid")
        if obj["output"] is not None:
            output = _exact(obj["output"], OUTPUT_KEYS, f"process[{index}].output")
            for key in OUTPUT_KEYS:
                if type(output[key]) is not list or len(output[key]) > MAX_ADJUDICATIONS:
                    _fail("output-observation", f"process[{index}].output.{key} is invalid")
                for n, item in enumerate(output[key]):
                    _string(item, f"process[{index}].output.{key}[{n}]", max_bytes=MAX_ID_BYTES)
        if type(obj["missing"]) is not list or not obj["missing"] or len(obj["missing"]) > 32:
            _fail("process-missing", f"process[{index}].missing must retain bounded unavailable fields")
        for n, item in enumerate(obj["missing"]):
            _string(item, f"process[{index}].missing[{n}]", max_bytes=128)
        return obj
    obj = _exact(value, PROCESS_KEYS, f"process_observations[{index}]")
    if obj["variant"] != "complete-v1":
        _fail("process-variant", f"process observation {index} variant is invalid")
    role = obj["role"]
    if role not in ROLE_COUNTS:
        _fail("process-role", f"process observation {index} role is invalid")
    _bounded_int(obj["candidate_request_count"], f"process[{index}].candidate_request_count", MAX_ADJUDICATIONS)
    if obj["candidate_request_count"] != PROCESS_REQUEST_COUNTS[role]:
        _fail("process-count", f"process observation {role} request count differs")
    _platform(obj["platform"], f"process[{index}].platform", selector)
    launch = _exact(obj["launch"], LAUNCH_KEYS, f"process[{index}].launch")
    _string(launch["identity"], f"process[{index}].launch.identity")
    if type(launch["argv"]) is not list or not 1 <= len(launch["argv"]) <= 64:
        _fail("launch-argv", f"process[{index}].launch.argv is invalid")
    for n, item in enumerate(launch["argv"]):
        _string(item, f"process[{index}].launch.argv[{n}]", max_bytes=1024)
    _string(launch["cwd"], f"process[{index}].launch.cwd", max_bytes=2048)
    if type(launch["environment"]) is not dict or not launch["environment"]:
        _fail("launch-environment", f"process[{index}].launch.environment is not an object")
    for key, item in launch["environment"].items():
        _string(key, f"process[{index}].launch.environment key", max_bytes=256)
        if item is not None:
            _string(item, f"process[{index}].launch.environment.{key}", max_bytes=2048, nonempty=False)
    binary = _exact(obj["candidate_binary"], CANDIDATE_HASH_KEYS, f"process[{index}].candidate_binary")
    _sha(binary["sha256_pre"], f"process[{index}].candidate_binary.sha256_pre")
    _sha(binary["sha256_post"], f"process[{index}].candidate_binary.sha256_post")
    fe = _exact(obj["fe_mxcsr"], FE_KEYS, f"process[{index}].fe_mxcsr")
    for key in FE_KEYS:
        _fe_state(fe[key], f"process[{index}].fe_mxcsr.{key}")
    transport = _exact(obj["transport"], TRANSPORT_KEYS, f"process[{index}].transport")
    requests = _hash_pair(transport["requests"], f"process[{index}].transport.requests", REQUEST_FRAME_DOMAIN)
    responses = _hash_pair(transport["responses"], f"process[{index}].transport.responses", RESPONSE_FRAME_DOMAIN)
    if requests["count"] != obj["candidate_request_count"] or responses["count"] > requests["count"]:
        _fail("transport-count", f"process[{index}] request/response counts are outside the observed candidate bounds")
    lifecycle = _exact(obj["lifecycle"], LIFECYCLE_KEYS, f"process[{index}].lifecycle")
    if lifecycle["state"] not in {"exited", "terminated", "failed"}:
        _fail("lifecycle", f"process[{index}] lifecycle state is invalid")
    if type(lifecycle["exit_code"]) is not int or not -128 <= lifecycle["exit_code"] <= 255:
        _fail("exit-code", f"process[{index}] exit code is invalid")
    if type(lifecycle["clean_shutdown"]) is not bool:
        _fail("clean-shutdown", f"process[{index}] clean_shutdown is invalid")
    output = _exact(obj["output"], OUTPUT_KEYS, f"process[{index}].output")
    for key in OUTPUT_KEYS:
        if type(output[key]) is not list or len(output[key]) > MAX_ADJUDICATIONS:
            _fail("output-observation", f"process[{index}].output.{key} is invalid")
        for n, item in enumerate(output[key]):
            _string(item, f"process[{index}].output.{key}[{n}]", max_bytes=MAX_ID_BYTES)
    return obj


def _counts(adjudications: list[dict[str, Any]]) -> dict[str, int]:
    role_counts = {role: sum(item["role"] == role for item in adjudications) for role in ROLE_COUNTS}
    preflight = sum(not item["dispatch_to_candidate"] for item in adjudications)
    status_counts = {status: sum(item["status"] == status for item in adjudications) for status in STATUSES}
    return {
        "cases": len(adjudications),
        "development": role_counts["development"],
        "held-out": role_counts["held-out"],
        "controls": role_counts["controls"],
        "dispatched": len(adjudications) - preflight,
        "preflight": preflight,
        "supported": status_counts["supported"],
        "failed": status_counts["failed"],
        "inconclusive": status_counts["inconclusive"],
        "observation": status_counts["observation"],
    }


def _wire_frames(adjudications: list[dict[str, Any]]) -> dict[str, tuple[list[bytes], list[bytes]]]:
    output = {role: ([], []) for role in ROLE_COUNTS}
    for item in adjudications:
        if not item["dispatch_to_candidate"]:
            continue
        payload = item["evidence"]["payload"]
        if payload.get("variant") not in {"dispatched-candidate-v1", "dispatched-incomplete-v1"}:
            continue
        request = _b64_bytes(payload["request"]["bytes_b64"], "adjudication request", FRAME_BYTES)
        response = None if payload.get("response") is None else _b64_bytes(payload["response"]["bytes_b64"], "adjudication response", FRAME_BYTES)
        output[item["role"]][0].append(request)
        if response is not None:
            output[item["role"]][1].append(response)
    return output


def _process_health(processes: list[dict[str, Any]]) -> str:
    """Return the aggregate process disposition without accepting drift."""
    if any(item.get("variant") == "incomplete-v1" for item in processes):
        for item in processes:
            if item.get("variant") != "incomplete-v1":
                continue
            binary = item.get("candidate_binary")
            if binary is not None and binary["sha256_pre"] != binary["sha256_post"]:
                return "failed"
            fe = item.get("fe_mxcsr")
            if fe is not None and fe["pre"] != fe["post"]:
                return "failed"
            lifecycle = item.get("lifecycle")
            if lifecycle is not None and (lifecycle["state"] != "exited" or lifecycle["exit_code"] != 0 or not lifecycle["clean_shutdown"]):
                return "failed"
        return "inconclusive"
    for item in processes:
        if item["candidate_binary"]["sha256_pre"] != item["candidate_binary"]["sha256_post"]:
            return "failed"
        if item["transport"]["responses"]["count"] != item["transport"]["requests"]["count"]:
            return "inconclusive"
        fe = item["fe_mxcsr"]
        if fe["pre"] != fe["post"]:
            return "failed"
        if item["lifecycle"]["state"] != "exited" or item["lifecycle"]["exit_code"] != 0 or not item["lifecycle"]["clean_shutdown"]:
            return "failed"
        if any(item["output"][key] for key in OUTPUT_KEYS):
            return "inconclusive"
    return "supported"


def _validate_result_obj(result: Any) -> dict[str, Any]:
    _plain(result, "result")
    obj = _exact(result, RESULT_KEYS, "result")
    if obj["schema"] != RESULT_SCHEMA or obj["evidence_schema"] != EVIDENCE_SCHEMA:
        _fail("schema", "result schema differs")
    _binding(obj["binding"])
    attempt = _attempt(obj["attempt"])
    tools = _tools(obj["tool_identities"])
    if type(obj["adjudications"]) is not list or len(obj["adjudications"]) != MAX_ADJUDICATIONS:
        _fail("adjudication-count", "result must contain exactly 60 adjudications")
    adjudications = [_adjudication(item, index, attempt["attempt_id"]) for index, item in enumerate(obj["adjudications"])]
    counts = _counts(adjudications)
    if counts["development"] != 8 or counts["held-out"] != 40 or counts["controls"] != 12:
        _fail("role-count", "result role counts differ from 8/40/12")
    if counts["dispatched"] != 57 or counts["preflight"] != 3:
        _fail("dispatch-count", "result dispatch counts differ from 57/3")
    if [item["ordinal"] for item in adjudications if not item["dispatch_to_candidate"]] != [56, 57, 58]:
        _fail("dispatch-role", "only the three preregistered control ordinals may be preflight-only")
    if type(obj["process_observations"]) is not list or len(obj["process_observations"]) != 3:
        _fail("process-count", "result must contain exactly 3 process observations")
    processes = [_process(item, index, attempt["platform_selector"]) for index, item in enumerate(obj["process_observations"])]
    process_roles = [item["role"] for item in processes]
    if process_roles != ["development", "held-out", "controls"]:
        _fail("process-role", "process observations must be development/held-out/controls")
    frames_by_role = _wire_frames(adjudications)
    for process in processes:
        if process.get("variant") == "incomplete-v1":
            requests, responses = frames_by_role[process["role"]]
            transport = process["transport"]
            if transport["requests"] is None and requests:
                _fail("transport-derived", f"incomplete process {process['role']} omits available request transport")
            if transport["responses"] is None and responses:
                _fail("transport-derived", f"incomplete process {process['role']} omits available response transport")
            if transport["requests"] is not None and (transport["requests"]["count"] != len(requests) or transport["requests"]["sha256"] != _framed_hash(requests, REQUEST_FRAME_DOMAIN)):
                _fail("transport-derived", f"incomplete process {process['role']} request transport is not derived from adjudications")
            if transport["responses"] is not None and (transport["responses"]["count"] != len(responses) or transport["responses"]["sha256"] != _framed_hash(responses, RESPONSE_FRAME_DOMAIN)):
                _fail("transport-derived", f"incomplete process {process['role']} response transport is not derived from adjudications")
            continue
        requests, responses = frames_by_role[process["role"]]
        retained_requests = process["transport"]["requests"]
        retained_responses = process["transport"]["responses"]
        if retained_requests["count"] != len(requests) or retained_requests["sha256"] != _framed_hash(requests, REQUEST_FRAME_DOMAIN):
            _fail("transport-derived", f"process {process['role']} request transport is not derived from adjudications")
        if retained_responses["count"] != len(responses) or retained_responses["sha256"] != _framed_hash(responses, RESPONSE_FRAME_DOMAIN):
            _fail("transport-derived", f"process {process['role']} response transport is not derived from adjudications")
    if type(obj["counts"]) is not dict or set(obj["counts"]) != COUNTS_KEYS:
        _fail("counts-schema", "result counts violate closed schema")
    if any(obj["counts"][key] != counts[key] for key in COUNTS_KEYS):
        _fail("counts-algebra", "result counts are not derived from adjudications")
    process_status = _process_health(processes)
    expected_status = "failed" if counts["failed"] or process_status == "failed" else "inconclusive" if counts["inconclusive"] or process_status == "inconclusive" else None
    if expected_status is None:
        heldout_good = all(item["status"] == "supported" for item in adjudications[8:48])
        expected_status = "supported" if heldout_good else "inconclusive"
    if obj["status"] != expected_status:
        _fail("status-precedence", "result status violates failed/inconclusive/supported precedence")
    return obj


def validate_result(result_bytes: bytes) -> dict[str, Any]:
    """Validate canonical result bytes and return their in-memory object."""
    return _validate_result_obj(_decode(result_bytes, "result", MAX_RESULT_BYTES))


def _make_result(attempt: Mapping[str, Any], adjudications: Any, process_observations: Any, tool_identities: Any) -> bytes:
    if type(attempt) is not dict or type(adjudications) is not list or type(process_observations) is not list:
        _fail("writer-input", "result writer requires plain attempt, adjudication, and process values")
    attempt_obj = _attempt(attempt)
    validated_adjudications = [_adjudication(item, index, attempt_obj["attempt_id"]) for index, item in enumerate(adjudications)]
    validated_processes = [_process(item, index, attempt_obj["platform_selector"]) for index, item in enumerate(process_observations)]
    result = {
        "schema": RESULT_SCHEMA,
        "evidence_schema": EVIDENCE_SCHEMA,
        "binding": {"experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID, "candidate_profile_id": CANDIDATE_PROFILE_ID},
        "attempt": attempt_obj,
        "tool_identities": tool_identities,
        "adjudications": validated_adjudications,
        "process_observations": validated_processes,
        "counts": _counts(validated_adjudications),
        "status": "inconclusive",
    }
    # Validate once to derive the status, then emit exactly the validated object.
    result["status"] = _derived_status(result)
    raw = _canonical(result, "result", MAX_RESULT_BYTES)
    _validate_result_obj(result)
    return raw


def _derived_status(result: Mapping[str, Any]) -> str:
    adjudications = result["adjudications"]
    if any(item["status"] == "failed" for item in adjudications):
        return "failed"
    if any(item["status"] == "inconclusive" for item in adjudications):
        return "inconclusive"
    process_status = _process_health(result["process_observations"])
    if process_status == "failed":
        return "failed"
    if process_status == "inconclusive":
        return "inconclusive"
    heldout_good = all(item["status"] == "supported" for item in adjudications[8:48])
    return "supported" if heldout_good else "inconclusive"


def build_result(
    attempt: Mapping[str, Any] | None = None,
    adjudications: list[Mapping[str, Any]] | None = None,
    process_observations: list[Mapping[str, Any]] | None = None,
    tool_identities: list[Mapping[str, Any]] | None = None,
    **fields: Any,
) -> bytes:
    """Build canonical exact-attempt result bytes from already-observed values.

    A fully formed result mapping may be supplied as ``attempt`` for callers
    that stage a record before writing; ordinary callers pass the four named
    components.  No clock, random ID, process, filesystem, or network input is
    consulted.
    """
    if attempt is not None and type(attempt) is dict and set(attempt) == RESULT_KEYS:
        obj = dict(attempt)
        obj["status"] = _derived_status(obj)
        raw = _canonical(obj, "result", MAX_RESULT_BYTES)
        _validate_result_obj(obj)
        return raw
    if attempt is None:
        attempt = fields.pop("attempt_metadata", fields.pop("attempt", None))
    if adjudications is None:
        adjudications = fields.pop("adjudications", None)
    if process_observations is None:
        process_observations = fields.pop("processes", fields.pop("process_observations", None))
    if tool_identities is None:
        tool_identities = fields.pop("tool_identities", None)
    if fields:
        _fail("writer-input", "result writer received unexpected fields")
    return _make_result(attempt, adjudications, process_observations, tool_identities)


def _receipt_obj(result_bytes: bytes) -> dict[str, Any]:
    result = validate_result(result_bytes)
    result_sha = hashlib.sha256(result_bytes).hexdigest()
    processes = []
    for process in result["process_observations"]:
        if process.get("variant") == "incomplete-v1":
            processes.append({
                "variant": "incomplete-v1", "role": process["role"],
                "candidate_request_count": process["candidate_request_count"],
                "partial_observation": process,
            })
            continue
        processes.append({
            "variant": "complete-v1",
            "role": process["role"],
            "candidate_request_count": process["candidate_request_count"],
            "request_count": process["transport"]["requests"]["count"],
            "request_sha256": process["transport"]["requests"]["sha256"],
            "response_count": process["transport"]["responses"]["count"],
            "response_sha256": process["transport"]["responses"]["sha256"],
            "candidate_sha256_pre": process["candidate_binary"]["sha256_pre"],
            "candidate_sha256_post": process["candidate_binary"]["sha256_post"],
        })
    return {
        "schema": RECEIPT_SCHEMA,
        "evidence_schema": EVIDENCE_SCHEMA,
        "binding": result["binding"],
        "result_sha256": result_sha,
        "attempt": result["attempt"],
        "tool_identities": result["tool_identities"],
        "processes": processes,
        "counts": result["counts"],
        "status": result["status"],
    }


def build_receipt(result_bytes: bytes) -> bytes:
    """Derive a deterministic closed receipt from validated result bytes."""
    obj = _receipt_obj(result_bytes)
    raw = _canonical(obj, "receipt", MAX_RECEIPT_BYTES)
    validate_receipt(raw, result_bytes)
    return raw


def validate_receipt(receipt_bytes: bytes, result_bytes: bytes | None = None) -> dict[str, Any]:
    if type(result_bytes) is not bytes:
        _fail("unbound-receipt", "receipt validation requires referenced result bytes")
    obj = _decode(receipt_bytes, "receipt", MAX_RECEIPT_BYTES)
    _exact(obj, RECEIPT_KEYS, "receipt")
    if obj["schema"] != RECEIPT_SCHEMA or obj["evidence_schema"] != EVIDENCE_SCHEMA:
        _fail("schema", "receipt schema differs")
    _binding(obj["binding"], "receipt.binding")
    _sha(obj["result_sha256"], "receipt.result_sha256")
    _attempt(obj["attempt"], "receipt.attempt")
    _tools(obj["tool_identities"], "receipt.tool_identities")
    if type(obj["counts"]) is not dict or set(obj["counts"]) != COUNTS_KEYS:
        _fail("counts-schema", "receipt counts violate closed schema")
    for key in COUNTS_KEYS:
        _bounded_int(obj["counts"][key], f"receipt.counts.{key}", MAX_ADJUDICATIONS)
    expected_fixed = {"cases": 60, "development": 8, "held-out": 40, "controls": 12, "dispatched": 57, "preflight": 3}
    if any(obj["counts"][key] != value for key, value in expected_fixed.items()):
        _fail("counts-algebra", "receipt does not retain the exact 60/57/3 and 8/40/12 accounting")
    if obj["counts"]["supported"] + obj["counts"]["failed"] + obj["counts"]["inconclusive"] + obj["counts"]["observation"] != 60:
        _fail("counts-algebra", "receipt status counts do not sum to 60")
    if obj["status"] not in STATUSES - {"observation"}:
        _fail("status", "receipt status is invalid")
    if type(obj["processes"]) is not list or len(obj["processes"]) != 3:
        _fail("process-count", "receipt process identities are incomplete")
    roles = []
    for index, process in enumerate(obj["processes"]):
        if type(process) is not dict:
            _fail("process-schema", f"receipt.processes[{index}] is not an object")
        if process.get("variant") == "incomplete-v1":
            _exact(process, RECEIPT_INCOMPLETE_PROCESS_KEYS, f"receipt.processes[{index}]")
        else:
            _exact(process, RECEIPT_PROCESS_KEYS, f"receipt.processes[{index}]")
        role = process["role"]
        if role not in ROLE_COUNTS or role in roles:
            _fail("process-role", "receipt process roles are invalid")
        roles.append(role)
        _bounded_int(process["candidate_request_count"], "candidate_request_count", MAX_ADJUDICATIONS)
        if process["candidate_request_count"] != PROCESS_REQUEST_COUNTS[role]:
            _fail("process-count", f"receipt process {role} request count differs")
        if process["variant"] == "incomplete-v1":
            if type(process["partial_observation"]) is not dict:
                _fail("process-schema", "receipt incomplete process lacks partial observation")
            continue
        if process["variant"] != "complete-v1":
            _fail("process-variant", "receipt process variant is invalid")
        _bounded_int(process["request_count"], "request_count", MAX_ADJUDICATIONS)
        _bounded_int(process["response_count"], "response_count", MAX_ADJUDICATIONS)
        _sha(process["request_sha256"], "request_sha256")
        _sha(process["response_sha256"], "response_sha256")
        _sha(process["candidate_sha256_pre"], "candidate_sha256_pre")
        _sha(process["candidate_sha256_post"], "candidate_sha256_post")
        if process["candidate_request_count"] != process["request_count"] or process["response_count"] > process["request_count"]:
            _fail("transport-count", "receipt process counts differ")
    if roles != ["development", "held-out", "controls"]:
        _fail("process-role", "receipt process roles are not ordered")
    _sha_expected = hashlib.sha256(result_bytes).hexdigest()
    if obj["result_sha256"] != _sha_expected:
        _fail("result-hash", "receipt does not bind supplied result bytes")
    expected = _receipt_obj(result_bytes)
    if obj != expected:
        _fail("receipt-mismatch", "receipt does not derive from supplied result")
    return obj


def build_attempt_index(result_bytes: bytes, receipt_bytes: bytes, attempt: Mapping[str, Any] | None = None) -> bytes:
    """Build the in-memory immutable index envelope without write semantics."""
    result = validate_result(result_bytes)
    receipt = validate_receipt(receipt_bytes, result_bytes)
    result_attempt = result["attempt"]
    if attempt is None:
        attempt_obj = dict(result_attempt)
    else:
        if type(attempt) is not dict:
            _fail("index-input", "attempt metadata must be a plain object")
        attempt_obj = dict(attempt)
    _attempt(attempt_obj, "index.attempt")
    if attempt_obj != result_attempt or attempt_obj != receipt["attempt"]:
        _fail("attempt-mismatch", "index metadata differs from result/receipt")
    envelope = {
        "schema": ATTEMPT_INDEX_SCHEMA,
        "evidence_schema": EVIDENCE_SCHEMA,
        "binding": result["binding"],
        "attempt": attempt_obj,
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
    }
    envelope_sha = hashlib.sha256(_canonical(envelope, "attempt-index envelope", MAX_INDEX_BYTES)).hexdigest()
    envelope["envelope_sha256"] = envelope_sha
    raw = _canonical(envelope, "attempt-index", MAX_INDEX_BYTES)
    validate_attempt_index(raw, result_bytes, receipt_bytes)
    return raw


def validate_attempt_index(index_bytes: bytes, result_bytes: bytes | None = None, receipt_bytes: bytes | None = None) -> dict[str, Any]:
    if type(result_bytes) is not bytes or type(receipt_bytes) is not bytes:
        _fail("unbound-index", "attempt-index validation requires referenced result and receipt bytes")
    obj = _decode(index_bytes, "attempt-index", MAX_INDEX_BYTES)
    _exact(obj, INDEX_KEYS, "attempt-index")
    if obj["schema"] != ATTEMPT_INDEX_SCHEMA or obj["evidence_schema"] != EVIDENCE_SCHEMA:
        _fail("schema", "attempt-index schema differs")
    _binding(obj["binding"], "index.binding")
    _attempt(obj["attempt"], "index.attempt")
    result_sha = _sha(obj["result_sha256"], "index.result_sha256")
    receipt_sha = _sha(obj["receipt_sha256"], "index.receipt_sha256")
    expected_envelope = dict(obj)
    del expected_envelope["envelope_sha256"]
    expected_sha = hashlib.sha256(_canonical(expected_envelope, "attempt-index envelope", MAX_INDEX_BYTES)).hexdigest()
    if obj["envelope_sha256"] != expected_sha:
        _fail("index-self-hash", "attempt-index envelope SHA differs")
    if result_sha != hashlib.sha256(result_bytes).hexdigest():
        _fail("result-hash", "attempt-index result hash differs")
    result = validate_result(result_bytes)
    if result["binding"] != obj["binding"]:
        _fail("binding", "attempt-index binding differs from result")
    if result["attempt"] != obj["attempt"]:
        _fail("attempt-mismatch", "attempt-index attempt differs from result")
    if receipt_sha != hashlib.sha256(receipt_bytes).hexdigest():
        _fail("receipt-hash", "attempt-index receipt hash differs")
    receipt = validate_receipt(receipt_bytes, result_bytes)
    if receipt["binding"] != obj["binding"]:
        _fail("binding", "attempt-index binding differs from receipt")
    if receipt["attempt"] != obj["attempt"]:
        _fail("attempt-mismatch", "attempt-index attempt differs from receipt")
    return obj


# Names used by callers at the result/receipt/index boundaries.
result_bytes = build_result
receipt_bytes = build_receipt
attempt_index_bytes = build_attempt_index
build_index = build_attempt_index
write_result = build_result
write_receipt = build_receipt
write_attempt_index = build_attempt_index

__all__ = [
    "RESULT_SCHEMA", "RECEIPT_SCHEMA", "ATTEMPT_INDEX_SCHEMA", "EVIDENCE_SCHEMA",
    "EXPERIMENT_ID", "PHASE_ID", "CANDIDATE_PROFILE_ID",
    "EvidenceContractError", "build_result", "validate_result", "build_receipt",
    "validate_receipt", "build_attempt_index", "build_index", "validate_attempt_index",
    "result_bytes", "receipt_bytes", "attempt_index_bytes", "write_result", "write_receipt", "write_attempt_index",
]

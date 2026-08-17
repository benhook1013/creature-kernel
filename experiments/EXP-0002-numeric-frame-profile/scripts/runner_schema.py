"""Authoritative frozen corpus/manifest loading and case validation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from runner_common import (
    CASE_REQUIRED_FIELDS,
    FRAME_BYTES,
    MAX_CASES_PER_CORPUS,
    MAX_RELATIONS,
    MAX_TOTAL_CASES,
    OPERATIONS,
    OPERATION_FIELDS,
    PROTOCOL_ID,
    RESPONSE_PROTOCOL_ID,
    ROLES,
    MAX_WIRE_REQUEST_ID_BYTES,
    EXPECTED_FIELDS,
    ProtocolError,
    forbidden_keys,
    frame_json,
    iter_bounded_frames,
    parse_json_bytes,
    read_bounded_bytes,
    parse_raw_request,
    require_exact_fields,
    require_object,
    require_sha256,
    require_string,
    require_string_list,
)
from runner_oracle import OracleBoundError, oracle_case

MANIFEST_FIELDS = {
    "manifest_version",
    "experiment_id",
    "lifecycle",
    "candidate_request_protocol",
    "candidate_response_protocol",
    "operations",
    "corpus_order",
    "experimental_tolerances",
    "record_shape",
    "result_shape",
    "error_codes",
    "corpora",
    "relations",
    "disjointness",
    "run_state",
}
CORPUS_FIELDS = {"order", "role", "path", "count", "bytes", "sha256", "family_counts", "case_ids"}
RELATION_FIELDS = {"id", "cases", "meaning"}
ENVIRONMENT_EXPECTED_FIELDS = {"kind", "required_fields", "status_enum", "mxcsr_rounding_mode", "scope", "absent_fields", "technology_result"}
ENVIRONMENT_REQUIRED_FIELDS = {"target", "status", "rounding_mode", "mxcsr", "mxcsr_rounding_mode", "ftz_enabled", "daz_enabled", "failure_classification", "scope"}
ENVIRONMENT_FAILURES = {"none", "unsupported-target", "rounding-mode-unavailable", "wrong-rounding-mode", "ftz-enabled", "daz-enabled"}
ENVIRONMENT_STATUSES = {"passed", "failed", "unsupported"}
WIRE_CASE_REQUIRED_FIELDS = CASE_REQUIRED_FIELDS | {"wire_request_id"}
STABLE_ERROR_CODES = {
    "malformed-request",
    "invalid-json-number",
    "non-finite-or-overflow",
    "nonzero-underflow-to-zero",
    "invalid-input",
    "token-bytes",
    "significant-digits",
    "exponent-magnitude",
}


def _case_expected_shape(expected: Any, operation: str) -> dict[str, Any]:
    expected = require_object(expected, "expected")
    if not set(expected) <= EXPECTED_FIELDS or "status" not in expected:
        raise ProtocolError("expected has unknown or missing fields")
    status = expected["status"]
    if status not in {"observed", "rejected", "resource-limit", "error"}:
        raise ProtocolError("expected status is not a closed transport classification")
    if status == "observed":
        if "error_code" in expected or "observations" not in expected:
            raise ProtocolError("observed expected result must contain observations only")
        observations = require_object(expected["observations"], "expected observations")
        if operation == "environment-attestation":
            require_exact_fields(observations, ENVIRONMENT_EXPECTED_FIELDS, "environment expected observations")
            if observations["kind"] != "environment-evidence" or observations["technology_result"] != "not-adjudicated":
                raise ProtocolError("environment expected result is not capability-only evidence")
            if set(observations["required_fields"]) != ENVIRONMENT_REQUIRED_FIELDS:
                raise ProtocolError("environment expected required field set differs")
            if set(observations["status_enum"]) != ENVIRONMENT_STATUSES:
                raise ProtocolError("environment expected status enum differs")
            if observations["scope"] != "single-threaded-jsonl-loop":
                raise ProtocolError("environment expected scope differs")
            if set(observations["absent_fields"]) != {"subnormal_add_bits", "subnormal_multiply_bits"}:
                raise ProtocolError("environment expected stale-field set differs")
        elif operation == "decimal-admission":
            require_exact_fields(observations, {"bits"}, "decimal expected observations")
        elif operation in {"scalar-comparison", "translation-comparison"}:
            require_exact_fields(observations, {"predicate"}, "comparison expected observations")
            if not isinstance(observations["predicate"], bool):
                raise ProtocolError("expected predicate is not boolean")
    else:
        if "observations" in expected or "error_code" not in expected:
            raise ProtocolError("non-observed expected result must contain one error_code")
        if not isinstance(expected["error_code"], str):
            raise ProtocolError("expected error_code is not a string")
        if expected["error_code"] not in STABLE_ERROR_CODES:
            raise ProtocolError("expected error_code is outside the closed stable code set")
    if "request_id" in expected and not isinstance(expected["request_id"], str):
        raise ProtocolError("expected request_id is not a string")
    return expected


def validate_case(case: Mapping[str, Any]) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    """Validate one authoritative record and recompute its independent oracle."""

    if set(case) - WIRE_CASE_REQUIRED_FIELDS - {"input", "request_raw"}:
        raise ProtocolError("case contains fields from an alternate corpus schema")
    if not WIRE_CASE_REQUIRED_FIELDS <= set(case) or ("input" in case) == ("request_raw" in case):
        raise ProtocolError("case must contain exactly one input/request_raw member")
    case_id = require_string(case["case_id"], "case_id")
    if not case_id or any(char.isspace() for char in case_id):
        raise ProtocolError("case_id must be opaque non-whitespace text")
    wire_request_id = require_string(case["wire_request_id"], "wire_request_id")
    if not wire_request_id or any(char.isspace() for char in wire_request_id):
        raise ProtocolError("wire_request_id must be opaque non-whitespace text")
    if len(wire_request_id.encode("utf-8")) > MAX_WIRE_REQUEST_ID_BYTES:
        raise ProtocolError("wire_request_id exceeds 256 UTF-8 bytes")
    operation = require_string(case["operation"], "operation")
    family = require_string(case["family"], "family")
    if operation not in OPERATIONS or family != operation:
        raise ProtocolError("case family/operation is not in the current phase")
    expected = _case_expected_shape(case["expected"], operation)
    relations = require_string_list(case["relations"], "relations")
    if len(relations) != len(set(relations)):
        raise ProtocolError("case contains duplicate relation IDs")
    if "input" in case:
        input_value = require_object(case["input"], "case input")
        forbidden_keys(input_value)
        if operation == "environment-attestation" and input_value != {}:
            raise ProtocolError("environment input must be empty")
        oracle, oracle_expected, work_digits = oracle_case(operation, input_value)
        if expected.get("status") != oracle_expected.get("status"):
            raise ProtocolError(f"expected status disagrees with exact oracle for {case_id}")
        if "error_code" in oracle_expected and expected.get("error_code") != oracle_expected["error_code"]:
            raise ProtocolError(f"expected error_code disagrees with exact oracle for {case_id}")
        if "observations" in oracle_expected and operation != "environment-attestation" and expected.get("observations") != oracle_expected["observations"]:
            raise ProtocolError(f"expected observations disagree with exact oracle for {case_id}")
        request = {"protocol_id": PROTOCOL_ID, "request_id": wire_request_id, "operation": operation, "input": input_value}
        request_bytes = frame_json(request)
        return dict(case), request_bytes, {"oracle": oracle, "expected": expected, "work_digits": work_digits, "request_id": wire_request_id}
    raw_text = case["request_raw"]
    if not isinstance(raw_text, str):
        raise ProtocolError("request_raw must be a string")
    raw_bytes = raw_text.encode("utf-8") + b"\n"
    if len(raw_bytes) > FRAME_BYTES:
        raise ProtocolError("request_raw exceeds frame limit")
    parsed = parse_raw_request(raw_text)
    if parsed is None:
        if expected.get("status") != "error" or expected.get("error_code") != "malformed-request":
            raise ProtocolError(f"malformed raw request has wrong expected result for {case_id}")
        if expected.get("request_id") is not None:
            raise ProtocolError(f"malformed raw request cannot retain request_id for {case_id}")
        request_id = None
    else:
        if set(parsed) != {"protocol_id", "request_id", "operation", "input"}:
            raise ProtocolError(f"raw request fields differ for {case_id}")
        request_id = parsed.get("request_id")
        if not isinstance(request_id, str) or request_id != wire_request_id:
            raise ProtocolError(f"raw request_id is invalid for {case_id}")
        if len(request_id.encode("utf-8")) > MAX_WIRE_REQUEST_ID_BYTES:
            raise ProtocolError(f"raw request_id exceeds 256 UTF-8 bytes for {case_id}")
        if parsed.get("protocol_id") != PROTOCOL_ID:
            if expected.get("error_code") != "malformed-request":
                raise ProtocolError(f"wrong-protocol raw request has wrong expected result for {case_id}")
        elif expected.get("error_code") not in {"invalid-input", "malformed-request"}:
            raise ProtocolError(f"valid raw request has unexpected expected result for {case_id}")
    if request_id is not None and request_id != wire_request_id:
        raise ProtocolError(f"expected/raw request_id differs for {case_id}")
    if expected.get("request_id") is not None and expected.get("request_id") != wire_request_id:
        raise ProtocolError(f"expected request_id differs for {case_id}")
    return dict(case), raw_bytes, {"oracle": {"classification": "not-applicable", "reason": expected.get("error_code", "malformed-request"), "owner": "runner-preflight-v1"}, "expected": expected, "work_digits": 0, "request_id": request_id}


def _load_jsonl(path: Path) -> tuple[str, int, list[dict[str, Any]], set[bytes], set[bytes], dict[str, dict[str, Any]], int]:
    digest = hashlib.sha256()
    byte_length = 0
    records: list[dict[str, Any]] = []
    request_bytes: set[bytes] = set()
    line_bytes: set[bytes] = set()
    metadata: dict[str, dict[str, Any]] = {}
    max_work_digits = 0
    with path.open("rb") as stream:
        for ordinal, raw in enumerate(iter_bounded_frames(stream), 1):
            if ordinal > MAX_CASES_PER_CORPUS:
                raise ProtocolError(f"{path} exceeds case-count bound")
            if raw in line_bytes:
                raise ProtocolError(f"duplicate complete line bytes in {path}: {ordinal}")
            line_bytes.add(raw)
            digest.update(raw)
            byte_length += len(raw)
            if raw in {b"\n", b"\r\n"}:
                raise ProtocolError(f"blank JSONL record at {path}:{ordinal}")
            record = require_object(parse_json_bytes(raw), f"case {ordinal}")
            validated, projected, info = validate_case(record)
            case_id = validated["case_id"]
            if projected in request_bytes:
                raise ProtocolError(f"duplicate candidate projection in {path}: {case_id}")
            request_bytes.add(projected)
            records.append(validated)
            metadata[case_id] = info
            max_work_digits = max(max_work_digits, info["work_digits"])
    return digest.hexdigest(), byte_length, records, request_bytes, line_bytes, metadata, max_work_digits


def _regular_direct_child(manifest_path: Path, relative: str, role: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.name != relative or candidate.parent != Path("."):
        raise ProtocolError(f"{role} corpus path must be a direct child")
    path = manifest_path.parent / candidate
    if path.is_symlink() or not path.is_file():
        raise ProtocolError(f"{role} corpus path is not a regular non-symlink file")
    return path


def load_manifest(path: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ProtocolError("manifest must be a regular non-symlink file")
    manifest_bytes = read_bounded_bytes(path)
    manifest = require_object(parse_json_bytes(manifest_bytes), "manifest")
    require_exact_fields(manifest, MANIFEST_FIELDS, "manifest")
    if manifest["manifest_version"] != "ck.r3.numeric-corpus-manifest-1" or manifest["experiment_id"] != "EXP-0002" or manifest["lifecycle"] != "frozen-inputs-unrun":
        raise ProtocolError("manifest identity/lifecycle mismatch")
    if manifest["candidate_request_protocol"] != PROTOCOL_ID or manifest["candidate_response_protocol"] != RESPONSE_PROTOCOL_ID:
        raise ProtocolError("manifest protocol mismatch")
    if tuple(manifest["operations"]) != ("decimal-admission", "scalar-comparison", "translation-comparison", "environment-attestation"):
        raise ProtocolError("manifest operation ordering differs")
    if set(manifest["operations"]) != OPERATIONS or tuple(manifest["corpus_order"]) != tuple(f"{role}.jsonl" for role in ROLES):
        raise ProtocolError("manifest operation or corpus order differs")
    if set(manifest["error_codes"]) != STABLE_ERROR_CODES:
        raise ProtocolError("manifest stable error-code set differs")
    record_shape = require_object(manifest["record_shape"], "record_shape")
    require_exact_fields(record_shape, {"required", "request_member", "candidate_projection", "runner_only"}, "record_shape")
    if record_shape["required"] != ["case_id", "wire_request_id", "family", "operation", "expected", "relations"] or record_shape["request_member"] != "exactly one of input or request_raw" or record_shape["runner_only"] != ["case_id", "wire_request_id", "family", "expected", "relations"]:
        raise ProtocolError("manifest record shape differs")
    projection = require_object(record_shape["candidate_projection"], "candidate_projection")
    require_exact_fields(projection, {"valid", "raw"}, "candidate_projection")
    if projection["raw"] != "request_raw" or projection["valid"] != {"protocol_id": PROTOCOL_ID, "request_id": "wire_request_id", "operation": "operation", "input": "input"}:
        raise ProtocolError("manifest candidate projection differs")
    result_shape = require_object(manifest["result_shape"], "result_shape")
    require_exact_fields(result_shape, {"required", "optional", "transport_statuses", "candidate_adjudication"}, "result_shape")
    if result_shape["required"] != ["protocol_id", "status"] or result_shape["optional"] != ["request_id", "observations", "error"] or result_shape["transport_statuses"] != ["observed", "rejected", "resource-limit", "unsupported", "error"] or result_shape["candidate_adjudication"] != "none":
        raise ProtocolError("manifest result shape differs")
    run_state = require_object(manifest["run_state"], "run_state")
    require_exact_fields(run_state, {"corpus_run", "candidate_evaluation", "profile_binding", "technology_result"}, "run_state")
    if run_state.get("profile_binding", "not-null") is not None or run_state.get("corpus_run") != "not-run" or run_state.get("candidate_evaluation") != "not performed" or run_state.get("technology_result") is not None:
        raise ProtocolError("manifest is not an unrun profile-null package")
    corpora = manifest["corpora"]
    if not isinstance(corpora, list) or len(corpora) != len(ROLES):
        raise ProtocolError("manifest must contain exactly three corpora")
    loaded: dict[str, list[dict[str, Any]]] = {}
    case_info: dict[str, dict[str, Any]] = {}
    all_request_bytes: set[bytes] = set()
    all_line_bytes: set[bytes] = set()
    metadata_corpora: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    total = 0
    max_work_digits = 0
    for expected_order, entry_value in enumerate(corpora, 1):
        entry = require_object(entry_value, "corpus manifest entry")
        require_exact_fields(entry, CORPUS_FIELDS, "corpus manifest entry")
        role = require_string(entry["role"], "corpus role")
        if role != ROLES[expected_order - 1] or entry["order"] != expected_order or role in loaded:
            raise ProtocolError("manifest corpus roles/order differ")
        corpus_path = _regular_direct_child(path, require_string(entry["path"], "corpus path"), role)
        digest, byte_length, records, request_bytes, line_bytes, infos, work_digits = _load_jsonl(corpus_path)
        if digest != require_sha256(entry["sha256"], f"{role} sha256") or byte_length != entry["bytes"] or len(records) != entry["count"]:
            raise ProtocolError(f"corpus hash/bytes/count mismatch for {role}")
        if [record["case_id"] for record in records] != entry["case_ids"]:
            raise ProtocolError(f"corpus case order mismatch for {role}")
        if {record["family"] for record in records} - OPERATIONS or {record["operation"] for record in records} - set(manifest["operations"]):
            raise ProtocolError(f"corpus operation mismatch for {role}")
        counts: dict[str, int] = {}
        for record in records:
            counts[record["family"]] = counts.get(record["family"], 0) + 1
            case_id = record["case_id"]
            if case_id in seen_ids:
                raise ProtocolError(f"duplicate case ID across corpora: {case_id}")
            seen_ids.add(case_id)
            if case_id not in infos:
                raise ProtocolError("internal case metadata loss")
            case_info[case_id] = infos[case_id]
        if counts != entry["family_counts"]:
            raise ProtocolError(f"family matrix mismatch for {role}")
        if all_request_bytes & request_bytes:
            raise ProtocolError(f"candidate projection bytes overlap roles at {role}")
        all_request_bytes |= request_bytes
        if all_line_bytes & line_bytes:
            raise ProtocolError(f"corpus line bytes overlap roles at {role}")
        all_line_bytes |= line_bytes
        loaded[role] = records
        total += len(records)
        max_work_digits = max(max_work_digits, work_digits)
        metadata_corpora.append({"role": role, "path": entry["path"], "sha256": digest, "bytes": byte_length, "count": len(records), "case_ids": [record["case_id"] for record in records]})
    if total > MAX_TOTAL_CASES or tuple(loaded) != ROLES:
        raise ProtocolError("corpus total/order bound failed")
    relations = manifest["relations"]
    if not isinstance(relations, list) or len(relations) > MAX_RELATIONS:
        raise ProtocolError("manifest relations exceed bound")
    relation_metadata: dict[str, dict[str, Any]] = {}
    memberships: dict[str, set[str]] = {case_id: set(record["relations"]) for case_id, record in ((case["case_id"], case) for role in ROLES for case in loaded[role])}
    for relation_value in relations:
        relation = require_object(relation_value, "relation")
        require_exact_fields(relation, RELATION_FIELDS, "relation")
        relation_id = require_string(relation["id"], "relation id")
        if relation_id in relation_metadata:
            raise ProtocolError("duplicate relation ID")
        case_ids = require_string_list(relation["cases"], "relation cases")
        if not case_ids or any(case_id not in seen_ids for case_id in case_ids):
            raise ProtocolError("relation references an unknown case")
        if any(relation_id not in memberships[case_id] for case_id in case_ids):
            raise ProtocolError(f"relation membership is not bidirectional: {relation_id}")
        relation_metadata[relation_id] = {"id": relation_id, "cases": case_ids, "meaning": require_string(relation["meaning"], "relation meaning")}
    for case_id, ids in memberships.items():
        if any(relation_id not in relation_metadata for relation_id in ids):
            raise ProtocolError(f"case references an unknown relation: {case_id}")
        if any(case_id not in relation_metadata[relation_id]["cases"] for relation_id in ids):
            raise ProtocolError(f"case relation membership is not bidirectional: {case_id}")
    if max_work_digits > 4_096:
        raise OracleBoundError(f"frozen corpus needs {max_work_digits} exact decimal work digits")
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    return manifest, loaded, {"manifest_sha256": manifest_sha, "corpora": metadata_corpora, "relations": relation_metadata, "case_info": case_info, "oracle_bound": {"max_decimal_materialization_digits": max_work_digits, "bound": 4_096, "proof": "preflight exact admitted-token scan"}}


def output_path_safe(output: Path, forbidden: list[Path]) -> Path:
    """Reject overwrite, aliases, and unusable output parents before execution."""

    if not output.parent.exists() or not output.parent.is_dir():
        raise ProtocolError("output parent must be an existing directory")
    if os.path.lexists(output):
        raise ProtocolError("output path already exists; refusing overwrite")
    resolved = output.parent.resolve() / output.name
    for path in forbidden:
        if resolved == path.resolve():
            raise ProtocolError("output path aliases an input or candidate executable")
    return output

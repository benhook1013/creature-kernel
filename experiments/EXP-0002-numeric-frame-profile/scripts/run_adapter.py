#!/usr/bin/env python3
"""Bounded, research-only runner for the frozen EXP-0002 phase-1 package."""

from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from runner_common import (
    CASE_CLASSIFICATIONS,
    EXPONENT_MASK,
    FRAME_BYTES,
    MAX_CASES_PER_CORPUS,
    MAX_RELATIONS,
    MAX_TOTAL_CASES,
    MAX_WIRE_REQUEST_ID_BYTES,
    OPERATIONS,
    PROTOCOL_ID,
    RESPONSE_FIELDS,
    RESPONSE_PROTOCOL_ID,
    RESULT_STATUSES,
    ROLES,
    ProtocolError,
    canonical_json_bytes,
    forbidden_keys,
    frame_json,
    parse_json_bytes,
    require_exact_fields,
    require_object,
)
from runner_oracle import MAX_ORACLE_DECIMAL_DIGITS, OracleBoundError, oracle_case
from runner_schema import (
    ENVIRONMENT_FAILURES,
    ENVIRONMENT_REQUIRED_FIELDS,
    ENVIRONMENT_STATUSES,
    load_manifest,
    output_path_safe,
    STABLE_ERROR_CODES,
)
from runner_transport import (
    STDERR_TOTAL_CAP,
    STDOUT_TOTAL_CAP,
    TRAILING_OUTPUT_QUIET_SECONDS,
    IO_DEADLINE_SECONDS,
    SHUTDOWN_DEADLINE_SECONDS,
    BoundedSubprocessSession,
    CloseResult,
    TransportError,
)

ERROR_CODE_MAP = {code: code for code in STABLE_ERROR_CODES}
ENVIRONMENT_FAILURE_CLASSIFICATIONS = {
    "none",
    "unsupported-target",
    "rounding-mode-unavailable",
    "wrong-rounding-mode",
    "ftz-enabled",
    "daz-enabled",
}
RUNNER_MODULES = (
    "run_adapter.py",
    "runner_common.py",
    "runner_oracle.py",
    "runner_schema.py",
    "runner_transport.py",
)


def sanitize_request(operation: str, input_value: Mapping[str, Any], request_id: str) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise ProtocolError("unsupported operation")
    request = {"protocol_id": PROTOCOL_ID, "request_id": request_id, "operation": operation, "input": input_value}
    frame_json(request)
    return request


def _candidate_error_code(error: Any) -> str | None:
    return ERROR_CODE_MAP.get(error) if isinstance(error, str) else None


def _validate_response_shape(value: Any) -> dict[str, Any]:
    response = require_object(value, "candidate response")
    if not set(response) <= RESPONSE_FIELDS or "protocol_id" not in response or "status" not in response:
        raise ProtocolError("candidate response fields differ")
    if not isinstance(response["protocol_id"], str) or not isinstance(response["status"], str):
        raise ProtocolError("candidate response protocol/status types are invalid")
    if response["status"] not in RESULT_STATUSES:
        raise ProtocolError("candidate response status is outside the closed transport set")
    if "request_id" in response and not isinstance(response["request_id"], str):
        raise ProtocolError("candidate response request_id is invalid")
    if "observations" in response and not isinstance(response["observations"], dict):
        raise ProtocolError("candidate observations must be an object")
    if "error" in response and not isinstance(response["error"], str):
        raise ProtocolError("candidate error must be a string")
    forbidden_keys(response, "response")
    if response["status"] == "observed" and "error" in response:
        raise ProtocolError("observed response contains an error")
    return response


def _validate_environment_observation(observations: Mapping[str, Any]) -> str:
    require_exact_fields(observations, ENVIRONMENT_REQUIRED_FIELDS, "environment observation")
    if not isinstance(observations["target"], str) or not isinstance(observations["scope"], str):
        raise ProtocolError("environment target/scope types are invalid")
    status = observations["status"]
    failure = observations["failure_classification"]
    if not isinstance(status, str) or not isinstance(failure, str):
        raise ProtocolError("environment status/failure classification types are invalid")
    if status not in ENVIRONMENT_STATUSES or failure not in ENVIRONMENT_FAILURE_CLASSIFICATIONS:
        raise ProtocolError("environment status/failure classification is not closed")
    if observations["scope"] != "single-threaded-jsonl-loop":
        raise ProtocolError("environment scope differs")
    control_fields = ("rounding_mode", "mxcsr", "mxcsr_rounding_mode", "ftz_enabled", "daz_enabled")
    if status == "unsupported":
        if observations["target"] != "unsupported-target" or failure != "unsupported-target" or any(observations[key] is not None for key in control_fields):
            raise ProtocolError("unsupported environment observation must null all controls")
        return status

    if observations["target"] != "x86_64-unknown-linux-gnu":
        raise ProtocolError("supported environment target differs")
    if any(observations[key] is None for key in control_fields):
        raise ProtocolError("supported environment observation lacks required controls")
    for key in ("rounding_mode", "mxcsr_rounding_mode"):
        value = observations[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ProtocolError(f"environment {key} type is invalid")
    if not 0 <= observations["mxcsr_rounding_mode"] <= 3:
        raise ProtocolError("environment MXCSR rounding mode is out of range")
    if not isinstance(observations["ftz_enabled"], bool) or not isinstance(observations["daz_enabled"], bool):
        raise ProtocolError("environment FTZ/DAZ types are invalid")
    mxcsr = observations["mxcsr"]
    if not isinstance(mxcsr, str) or len(mxcsr) != 10 or not mxcsr.startswith("0x"):
        raise ProtocolError("environment MXCSR format is invalid")
    try:
        raw = int(mxcsr[2:], 16)
    except ValueError as error:
        raise ProtocolError("environment MXCSR is not hexadecimal") from error
    if raw > (1 << 32) - 1 or observations["mxcsr_rounding_mode"] != ((raw >> 13) & 3):
        raise ProtocolError("environment MXCSR rounding evidence disagrees")
    if observations["ftz_enabled"] != bool(raw & (1 << 15)) or observations["daz_enabled"] != bool(raw & (1 << 6)):
        raise ProtocolError("environment MXCSR FTZ/DAZ evidence disagrees")

    rounding_mode = observations["rounding_mode"]
    if rounding_mode < 0:
        expected_failure = "rounding-mode-unavailable"
    elif rounding_mode != 0 or observations["mxcsr_rounding_mode"] != 0:
        expected_failure = "wrong-rounding-mode"
    elif observations["ftz_enabled"]:
        expected_failure = "ftz-enabled"
    elif observations["daz_enabled"]:
        expected_failure = "daz-enabled"
    else:
        expected_failure = None
    if status == "passed":
        if failure != "none" or expected_failure is not None:
            raise ProtocolError("passed environment observation is not round-to-nearest without FTZ/DAZ")
    elif status == "failed":
        if expected_failure is None or failure != expected_failure:
            raise ProtocolError("failed environment observation does not report its first failed control")
    return status


def adjudicate_response(operation: str, request_id: str | None, expected: Mapping[str, Any], raw_response: bytes) -> tuple[str, dict[str, Any], str | None]:
    response = _validate_response_shape(parse_json_bytes(raw_response))
    if response["protocol_id"] != RESPONSE_PROTOCOL_ID:
        raise ProtocolError("candidate response protocol mismatch")
    if response.get("request_id") != request_id:
        raise ProtocolError("candidate response correlation mismatch")
    status = response["status"]
    if status == "unsupported":
        return "unsupported", response, response.get("error")
    if status == "observed":
        observations = response.get("observations")
        if not isinstance(observations, dict):
            raise ProtocolError("observed response is missing observations")
        if operation == "environment-attestation":
            environment_status = _validate_environment_observation(observations)
            if expected.get("status") != "observed":
                return "fail", response, "environment transport status disagrees"
            if environment_status != "passed":
                return "inconclusive", response, f"environment capability status: {environment_status}"
            return "pass", response, None
        if operation == "decimal-admission":
            require_exact_fields(observations, {"bits"}, "decimal observations")
            bits = observations["bits"]
            try:
                finite = isinstance(bits, str) and len(bits) == 18 and bits.startswith("0x") and not (int(bits[2:], 16) & EXPONENT_MASK == EXPONENT_MASK)
            except ValueError:
                finite = False
            if not finite:
                raise ProtocolError("decimal response bits are invalid")
        elif operation in {"scalar-comparison", "translation-comparison"}:
            require_exact_fields(observations, {"predicate"}, "comparison observations")
            if not isinstance(observations["predicate"], bool):
                raise ProtocolError("comparison predicate is invalid")
        if expected.get("status") != "observed" or expected.get("observations") != observations:
            return "fail", response, "candidate observations disagree with expected result"
        return "pass", response, None
    if "observations" in response:
        raise ProtocolError("non-observed response contains observations")
    actual_code = _candidate_error_code(response.get("error"))
    if expected.get("status") != status or expected.get("error_code") != actual_code:
        return "fail", response, f"candidate error code mismatch: {actual_code!r}"
    return "pass", response, None


def _relation_classification(case_records: Mapping[str, dict[str, Any]], relation: Mapping[str, Any]) -> dict[str, Any]:
    case_ids = relation["cases"]
    missing = [case_id for case_id in case_ids if case_id not in case_records]
    if missing:
        return {"id": relation["id"], "meaning": relation["meaning"], "case_ids": case_ids, "classification": "incomplete", "reason": "member case was not processed", "missing": missing}
    members = [case_records[case_id] for case_id in case_ids]
    classifications = {record["classification"] for record in members}
    if "incomplete" in classifications:
        classification = "incomplete"
    elif "unsupported" in classifications or "inconclusive" in classifications:
        classification = "inconclusive"
    elif "fail" in classifications:
        classification = "fail"
    else:
        classification = "pass"
    if classification == "pass" and relation["id"] in {"lexical-equivalence", "signed-zero-canonicalization", "maximum-finite"}:
        bits = [record["candidate"].get("response", {}).get("observations", {}).get("bits") for record in members]
        if not bits or any(value != bits[0] for value in bits):
            classification = "fail"
    if classification == "pass" and relation["id"] == "environment-repeat":
        controls = []
        for record in members:
            observation = record["candidate"].get("response", {}).get("observations", {})
            controls.append(tuple(observation.get(key) for key in ("rounding_mode", "mxcsr_rounding_mode", "ftz_enabled", "daz_enabled")))
        if any(value != controls[0] for value in controls):
            classification = "fail"
    return {"id": relation["id"], "meaning": relation["meaning"], "case_ids": case_ids, "classification": classification}


def run_cases(corpora: Mapping[str, Sequence[Mapping[str, Any]]], case_info: Mapping[str, Mapping[str, Any]], relations: Mapping[str, Mapping[str, Any]], session: Any, candidate_identity: Mapping[str, Any]) -> dict[str, Any]:
    all_records: dict[str, dict[str, Any]] = {}
    counts = {classification: 0 for classification in sorted(CASE_CLASSIFICATIONS)}
    ordinal = 0
    stopped: str | None = None
    for role in ("development", "held-out", "adversarial"):
        for case in corpora.get(role, []):
            ordinal += 1
            case_id = case["case_id"]
            info = case_info[case_id]
            request_id = info.get("request_id")
            request_bytes = case["request_raw"].encode("utf-8") + b"\n" if "request_raw" in case else frame_json(sanitize_request(case["operation"], case["input"], request_id or case_id))
            raw_response = b""
            response: dict[str, Any] | None = None
            try:
                raw_response = session.request_frame(request_bytes) if hasattr(session, "request_frame") else session.request(sanitize_request(case["operation"], case.get("input", {}), request_id or case_id))
                classification, response, failure = adjudicate_response(case["operation"], request_id, case["expected"], raw_response)
            except (ProtocolError, TransportError) as error:
                classification = "incomplete"
                failure = str(error)
                stopped = str(error)
            counts[classification] += 1
            all_records[case_id] = {
                "case_id": case_id,
                "ordinal": ordinal,
                "role": role,
                "family": case["family"],
                "operation": case["operation"],
                "request_id": request_id,
                "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                "oracle": info["oracle"],
                "expected": case["expected"],
                "candidate": {"response_raw_sha256": hashlib.sha256(raw_response).hexdigest(), "response": response},
                "relations": case["relations"],
                "classification": classification,
                "failure": failure,
            }
            if stopped is not None:
                break
        if stopped is not None:
            break
    relation_results = [_relation_classification(all_records, relation) for relation in relations.values()]
    if stopped is not None:
        run_status = "incomplete"
        evidence_status = "incomplete"
    elif counts["inconclusive"] or counts["unsupported"]:
        run_status = "inconclusive"
        evidence_status = "inconclusive"
    elif counts["fail"]:
        # `run_status` describes whether the bounded execution completed;
        # semantic evidence quality is reported separately.
        run_status = "complete"
        evidence_status = "failed"
    else:
        run_status = "complete"
        evidence_status = "passed"
    return {
        "schema": "ck.exp-0002.numeric-corpus-result-1",
        "experiment_id": "EXP-0002",
        "run_status": run_status,
        "evidence_status": evidence_status,
        "classification_vocabulary": sorted(CASE_CLASSIFICATIONS),
        "protocol_revision": PROTOCOL_ID,
        "candidate": dict(candidate_identity),
        "corpora": [{"role": role, "planned_case_count": len(corpora.get(role, [])), "processed_case_count": sum(case["case_id"] in all_records for case in corpora.get(role, [])), "cases": [all_records[case["case_id"]] for case in corpora.get(role, []) if case["case_id"] in all_records]} for role in ("development", "held-out", "adversarial")],
        "relations": relation_results,
        "summary": counts,
        "failure": stopped,
    }


def _resolve_candidate_executable(command: Sequence[str]) -> tuple[Path, str, list[dict[str, Any]]]:
    if not command:
        raise ProtocolError("candidate command is required after --")
    executable = Path(command[0]) if ("/" in command[0] or "\\" in command[0]) else Path(shutil.which(command[0]) or "")
    if not executable:
        raise ProtocolError("candidate executable could not be resolved")
    executable = executable.resolve(strict=True)
    if not executable.is_file():
        raise ProtocolError("candidate executable is not a regular file")
    artifacts: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for index, argument in enumerate(command):
        candidate = Path(argument)
        if index == 0:
            artifact = executable.resolve()
        elif not candidate.is_file():
            continue
        else:
            artifact = candidate.resolve()
        if artifact in seen_paths:
            continue
        seen_paths.add(artifact)
        try:
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        except OSError as error:
            raise ProtocolError(f"candidate artifact is unreadable: {artifact}") from error
        artifacts.append({"argument_index": index, "argument": argument, "path": str(artifact), "sha256": digest})
    executable_digest = next(item["sha256"] for item in artifacts if item["argument_index"] == 0)
    return executable, executable_digest, artifacts


def _apply_close_result(result: dict[str, Any], close: CloseResult) -> None:
    cleanup: dict[str, Any] = {
        "returncode": close.returncode,
        "stderr_bytes": len(close.stderr),
        "stderr_sha256": hashlib.sha256(close.stderr).hexdigest(),
        "trailing_stdout_bytes": len(close.trailing_stdout),
        "trailing_stdout_sha256": hashlib.sha256(close.trailing_stdout).hexdigest(),
        "failure": None,
    }
    result["candidate"]["cleanup"] = cleanup
    # Retain the legacy direct fields while making cleanup ownership explicit.
    result["candidate"]["returncode"] = close.returncode
    result["candidate"]["stderr_bytes"] = cleanup["stderr_bytes"]
    result["candidate"]["stderr_sha256"] = cleanup["stderr_sha256"]
    result["candidate"]["trailing_stdout_bytes"] = cleanup["trailing_stdout_bytes"]
    if close.failure:
        result["run_status"] = "incomplete"
        result["evidence_status"] = "incomplete"
        cleanup["failure"] = close.failure
    elif close.returncode != 0:
        result["run_status"] = "incomplete"
        result["evidence_status"] = "incomplete"
        cleanup["failure"] = f"candidate exited with status {close.returncode}"
    elif close.trailing_stdout:
        result["run_status"] = "incomplete"
        result["evidence_status"] = "incomplete"
        cleanup["failure"] = "candidate emitted trailing stdout after the final response"


def _runner_identity() -> dict[str, Any]:
    script_dir = Path(__file__).resolve().parent
    module_sha256: dict[str, str] = {}
    for module in RUNNER_MODULES:
        path = script_dir / module
        try:
            module_sha256[module] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise ProtocolError(f"runner module is unreadable: {module}") from error
    caps = {
        "frame_bytes": FRAME_BYTES,
        "stdout_total_bytes": STDOUT_TOTAL_CAP,
        "stderr_total_bytes": STDERR_TOTAL_CAP,
        "max_cases_per_corpus": MAX_CASES_PER_CORPUS,
        "max_total_cases": MAX_TOTAL_CASES,
        "max_relations": MAX_RELATIONS,
        "max_oracle_decimal_digits": MAX_ORACLE_DECIMAL_DIGITS,
        "wire_request_id_bytes": MAX_WIRE_REQUEST_ID_BYTES,
    }
    deadlines = {
        "io": IO_DEADLINE_SECONDS,
        "shutdown": SHUTDOWN_DEADLINE_SECONDS,
        "trailing_output_quiet": TRAILING_OUTPUT_QUIET_SECONDS,
    }
    bundle = canonical_json_bytes({"module_sha256": module_sha256, "caps": caps, "deadlines_seconds": deadlines})
    return {
        "script_sha256": module_sha256["run_adapter.py"],
        "module_sha256": module_sha256,
        "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "caps": caps,
        "deadlines_seconds": deadlines,
    }


def _write_new_output(path: Path, result: Mapping[str, Any]) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(canonical_json_bytes(result) + b"\n")
    except FileExistsError as error:
        raise ProtocolError("output path appeared during run; refusing overwrite") from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("candidate", nargs=argparse.REMAINDER, help="candidate command after --")
    args = parser.parse_args(argv)
    command = list(args.candidate)
    if command and command[0] == "--":
        command.pop(0)
    try:
        executable, executable_sha256, command_artifacts = _resolve_candidate_executable(command)
        manifest, corpora, metadata = load_manifest(args.manifest)
        del manifest
        forbidden = [args.manifest.resolve()] + [args.manifest.parent / entry["path"] for entry in metadata["corpora"]] + [executable]
        output_path_safe(args.output, forbidden)
        candidate_identity = {"command": command, "command_artifacts": command_artifacts, "executable": str(executable), "executable_sha256": executable_sha256, "feature": "provisional-r3-numeric-candidate", "profile_id": None}
        runner_identity = _runner_identity()
        session = BoundedSubprocessSession(command, cwd=str(Path.cwd()))
        try:
            result = run_cases(corpora, metadata["case_info"], metadata["relations"], session, candidate_identity)
        finally:
            close_result = session.close()
        _apply_close_result(result, close_result)
        result["manifest"] = {"sha256": metadata["manifest_sha256"], "corpora": metadata["corpora"], "oracle_bound": metadata["oracle_bound"]}
        result["runner"] = runner_identity
        _write_new_output(args.output, result)
        return 0 if result["run_status"] == "complete" and result["evidence_status"] == "passed" else 2
    except (ProtocolError, OracleBoundError, OSError) as error:
        print(f"EXP-0002 runner error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

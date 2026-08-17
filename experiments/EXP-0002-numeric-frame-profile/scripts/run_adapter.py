#!/usr/bin/env python3
"""Bounded, research-only runner for the frozen EXP-0002 phase-1 package."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import selectors
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from runner_common import (
    CASE_CLASSIFICATIONS,
    EVALUATION_BINDING,
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
    PREREGISTERED_LIMITS,
    TECHNOLOGY_RESULT,
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
    status = response["status"]
    if status == "observed":
        if "observations" not in response or "error" in response:
            raise ProtocolError("observed response must contain observations and no error")
    elif "observations" in response:
        raise ProtocolError("non-observed response contains observations")
    elif status in {"rejected", "resource-limit", "error"} and "error" not in response:
        raise ProtocolError("rejected/resource/error response must contain an error")
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
    if relation["id"] == "environment-repeat":
        claim_type = "workload-position-conditioned-capability-observation"
    elif relation["id"] in {"lexical-equivalence", "signed-zero-canonicalization"}:
        claim_type = "cross-case-bit-equivalence"
    else:
        claim_type = "registered-case-group"
    missing = [case_id for case_id in case_ids if case_id not in case_records]
    if missing:
        return {"id": relation["id"], "meaning": relation["meaning"], "claim_type": claim_type, "case_ids": case_ids, "classification": "incomplete", "reason": "member case was not processed", "missing": missing}
    members = [case_records[case_id] for case_id in case_ids]
    classifications = {record["classification"] for record in members}
    if "fail" in classifications:
        classification = "fail"
    elif "unsupported" in classifications or "inconclusive" in classifications:
        classification = "inconclusive"
    elif "incomplete" in classifications:
        classification = "incomplete"
    else:
        classification = "pass"
    if classification == "pass" and relation["id"] in {"lexical-equivalence", "signed-zero-canonicalization"}:
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
    return {"id": relation["id"], "meaning": relation["meaning"], "claim_type": claim_type, "case_ids": case_ids, "classification": classification}


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
                "environment_observation_position": ordinal if case["operation"] == "environment-attestation" else None,
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
    relation_counts = {classification: 0 for classification in sorted(CASE_CLASSIFICATIONS)}
    for relation in relation_results:
        relation_counts[relation["classification"]] += 1
    if stopped is not None or counts["incomplete"] or relation_counts["incomplete"]:
        run_status = "incomplete"
        evidence_status = "incomplete"
    else:
        run_status = "complete"
        if counts["fail"] or relation_counts["fail"]:
            evidence_status = "failed"
        elif counts["inconclusive"] or counts["unsupported"] or relation_counts["inconclusive"] or relation_counts["unsupported"]:
            evidence_status = "inconclusive"
        else:
            evidence_status = "passed"
    return {
        "schema": "ck.exp-0002.numeric-corpus-result-1",
        "experiment_id": "EXP-0002",
        "evaluation_binding": EVALUATION_BINDING,
        "profile_binding": None,
        "technology_result": TECHNOLOGY_RESULT,
        "run_status": run_status,
        "evidence_status": evidence_status,
        "classification_vocabulary": sorted(CASE_CLASSIFICATIONS),
        "protocol_revision": PROTOCOL_ID,
        "execution": {
            "candidate_processes": 1,
            "persistent_process": True,
            "corpus_sequence": ["development", "held-out", "adversarial"],
            "held_out_role": "non-tuning-not-blind-or-process-isolated",
            "environment_observations": "workload-position-conditioned",
        },
        "candidate": dict(candidate_identity),
        "corpora": [{"role": role, "planned_case_count": len(corpora.get(role, [])), "processed_case_count": sum(case["case_id"] in all_records for case in corpora.get(role, [])), "cases": [all_records[case["case_id"]] for case in corpora.get(role, []) if case["case_id"] in all_records]} for role in ("development", "held-out", "adversarial")],
        "relations": relation_results,
        "classification_contract": {
            "exact_expected_mismatch": "completed-failed-conformance-evidence",
            "environment_failed_or_unsupported": "inconclusive-capability-evidence",
            "candidate_unsupported": "inconclusive-capability-evidence",
            "transport_nonzero_or_response_integrity": "incomplete",
            "profile_selection": "none",
            "technology_result": TECHNOLOGY_RESULT,
        },
        "summary": counts,
        "relation_summary": relation_counts,
        "failure": stopped,
    }


def _stable_file_stat(path: Path) -> dict[str, int]:
    stat_result = path.stat(follow_symlinks=False)
    return {
        "device": int(stat_result.st_dev),
        "inode": int(stat_result.st_ino),
        "mode": int(stat_result.st_mode),
        "size": int(stat_result.st_size),
        "mtime_ns": int(stat_result.st_mtime_ns),
    }


def _stream_file_identity(path: Path) -> dict[str, Any]:
    """Hash one regular file with a bounded streaming read and stat snapshot."""

    cap = PREREGISTERED_LIMITS["max_identity_artifact_bytes"]
    resolved = path.resolve(strict=True)
    if resolved != path or path.is_symlink() or not path.is_file():
        raise ProtocolError(f"identity path is not a regular non-symlink file: {path}")
    before = _stable_file_stat(path)
    if before["size"] > cap:
        raise ProtocolError(f"identity file exceeds {cap}-byte cap: {path}")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(min(1024 * 1024, cap - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > cap:
                raise ProtocolError(f"identity file exceeds {cap}-byte cap: {path}")
            digest.update(chunk)
    after = _stable_file_stat(path)
    if before != after or total != after["size"]:
        raise ProtocolError(f"identity file changed while hashing: {path}")
    return {"path": str(path), "bytes": total, "stat": after, "sha256": digest.hexdigest()}


def _resolve_candidate_executable(command: Sequence[str]) -> tuple[list[str], Path, str, list[dict[str, Any]]]:
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
            identity = _stream_file_identity(artifact)
        except (OSError, ProtocolError) as error:
            raise ProtocolError(f"candidate artifact is unreadable: {artifact}") from error
        artifacts.append({"argument_index": index, "argument": argument, **identity})
    executable_digest = next(item["sha256"] for item in artifacts if item["argument_index"] == 0)
    execution_command = [str(executable), *command[1:]]
    return execution_command, executable, executable_digest, artifacts


def _source_identity() -> dict[str, Any]:
    """Capture available source identity without requiring a clean worktree."""

    unavailable = {"available": False, "reason": "git identity unavailable", "dirty": None, "untracked_covered": False}
    try:
        root_process = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(Path.cwd()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2.0,
            text=True,
        )
        commit_process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path.cwd()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2.0,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return unavailable
    if root_process.returncode != 0 or commit_process.returncode != 0:
        return unavailable
    try:
        tracked_process = subprocess.run(
            ["git", "diff", "--quiet"],
            cwd=str(Path.cwd()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2.0,
        )
        staged_process = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(Path.cwd()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2.0,
        )
        untracked_process = subprocess.Popen(
            ["git", "ls-files", "--others", "--exclude-standard", "--directory"],
            cwd=str(Path.cwd()),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        assert untracked_process.stdout is not None
        os.set_blocking(untracked_process.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(untracked_process.stdout, selectors.EVENT_READ)
        untracked_present = False
        deadline = time.monotonic() + 2.0
        while untracked_process.poll() is None and time.monotonic() < deadline:
            events = selector.select(max(0.0, min(0.05, deadline - time.monotonic())))
            if not events:
                continue
            if os.read(untracked_process.stdout.fileno(), 1):
                untracked_present = True
                break
        selector.close()
        if not untracked_present:
            try:
                untracked_present = bool(os.read(untracked_process.stdout.fileno(), 1))
            except BlockingIOError:
                pass
        terminated_for_bound = untracked_present or untracked_process.poll() is None
        if terminated_for_bound:
            try:
                os.killpg(os.getpgid(untracked_process.pid), signal.SIGKILL)
            except OSError:
                untracked_process.kill()
        untracked_process.wait(timeout=0.5)
    except (OSError, subprocess.SubprocessError):
        return unavailable
    if tracked_process.returncode not in (0, 1) or staged_process.returncode not in (0, 1) or (untracked_process.returncode not in (0, 1) and not terminated_for_bound):
        return unavailable
    return {
        "available": True,
        "git_root": root_process.stdout.strip(),
        "git_commit": commit_process.stdout.strip(),
        "dirty": tracked_process.returncode == 1 or staged_process.returncode == 1 or untracked_present,
        "tracked_dirty": tracked_process.returncode == 1,
        "staged_dirty": staged_process.returncode == 1,
        "untracked_dirty": untracked_present,
        "untracked_covered": True,
    }


def _bounded_file_identity(path: Path, cap_bytes: int = 1 << 20) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        return {"available": False, "path": str(path), "reason": "file unavailable"}
    try:
        with path.open("rb") as stream:
            payload = stream.read(cap_bytes + 1)
    except OSError as error:
        return {"available": False, "path": str(path), "reason": f"file unreadable: {error}"}
    if len(payload) > cap_bytes:
        return {"available": False, "path": str(path), "reason": "file exceeds identity cap", "cap_bytes": cap_bytes}
    return {"available": True, "path": str(path), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _bounded_command_observation(command: Sequence[str], cwd: Path, cap_bytes: int = 8 * 1024) -> dict[str, Any]:
    observation: dict[str, Any] = {"available": False, "command": list(command), "cap_bytes": cap_bytes}
    try:
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as error:
        observation["reason"] = f"command unavailable: {error}"
        return observation
    assert process.stdout is not None
    fd = process.stdout.fileno()
    os.set_blocking(fd, False)
    selector = selectors.DefaultSelector()
    selector.register(fd, selectors.EVENT_READ)
    output = bytearray()
    reason: str | None = None
    deadline = time.monotonic() + 2.0
    try:
        while True:
            if time.monotonic() >= deadline:
                reason = "command deadline exceeded"
                break
            events = selector.select(max(0.0, min(0.05, deadline - time.monotonic())))
            for _key, _mask in events:
                try:
                    chunk = os.read(fd, 8192)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(fd)
                    break
                output.extend(chunk)
                if len(output) > cap_bytes:
                    reason = "command output exceeds identity cap"
                    break
            if reason is not None or not selector.get_map():
                break
            if process.poll() is not None and not events:
                reason = "command closed output unexpectedly"
                break
    finally:
        selector.close()
        if reason is not None and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except OSError:
                process.kill()
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=0.5)
        process.stdout.close()
    if reason is not None:
        observation["reason"] = reason
        return observation
    if process.returncode != 0:
        observation["reason"] = f"command exited with status {process.returncode}"
        return observation
    try:
        observation["stdout"] = bytes(output).decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
        observation["reason"] = "command output is not UTF-8"
        return observation
    observation["available"] = True
    return observation


def _find_upward(start: Path, filename: str) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for parent in (current, *current.parents):
        candidate = parent / filename
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return None


def _candidate_build_context(executable: Path) -> dict[str, Any]:
    cargo_manifest = _find_upward(executable.parent, "Cargo.toml") or _find_upward(Path.cwd(), "Cargo.toml")
    workspace = cargo_manifest.parent if cargo_manifest is not None else Path.cwd()
    cargo_lock = _find_upward(workspace, "Cargo.lock")
    rust_toolchain = _find_upward(workspace, "rust-toolchain.toml")
    source_files = {
        "rust_toolchain_toml": _bounded_file_identity(rust_toolchain or workspace / "rust-toolchain.toml"),
        "candidate_cargo_toml": _bounded_file_identity(cargo_manifest or workspace / "Cargo.toml"),
        "workspace_cargo_lock": _bounded_file_identity(cargo_lock or workspace / "Cargo.lock"),
    }
    environment = {key: os.environ.get(key) for key in ("RUSTFLAGS", "CARGO_TARGET_DIR", "CARGO_BUILD_TARGET", "CARGO_INCREMENTAL")}
    return {
        "scope": "observed candidate build context",
        "provenance_claim": "context only; does not prove the candidate binary was built by this toolchain or source state",
        "workspace": str(workspace),
        "source_files": source_files,
        "rustc_version": _bounded_command_observation(["rustc", "-Vv"], workspace),
        "cargo_version": _bounded_command_observation(["cargo", "-V"], workspace),
        "build_environment": environment,
    }


def _build_identity(executable: Path) -> dict[str, Any]:
    return {
        "runner_toolchain": {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "compiler": platform.python_compiler(),
        },
        "candidate_build_context": _candidate_build_context(executable),
        "source": _source_identity(),
    }


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
        _mark_incomplete(result, close.failure)
        cleanup["failure"] = close.failure
    elif close.returncode != 0:
        failure = f"candidate exited with status {close.returncode}"
        _mark_incomplete(result, failure)
        cleanup["failure"] = failure
    elif close.trailing_stdout:
        failure = "candidate emitted trailing stdout after the final response"
        _mark_incomplete(result, failure)
        cleanup["failure"] = failure


def _runner_identity() -> dict[str, Any]:
    script_dir = Path(__file__).resolve().parent
    module_identity: dict[str, dict[str, Any]] = {}
    for module in RUNNER_MODULES:
        path = script_dir / module
        try:
            module_identity[module] = _stream_file_identity(path)
        except (OSError, ProtocolError) as error:
            raise ProtocolError(f"runner module is unreadable: {module}") from error
    module_sha256 = {module: identity["sha256"] for module, identity in module_identity.items()}
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
    budgets = dict(PREREGISTERED_LIMITS)
    bundle = canonical_json_bytes({"evaluation_binding": EVALUATION_BINDING, "module_sha256": module_sha256, "caps": caps, "deadlines_seconds": deadlines, "budgets": budgets})
    return {
        "evaluation_binding": EVALUATION_BINDING,
        "script_sha256": module_sha256["run_adapter.py"],
        "module_sha256": module_sha256,
        "module_identity": module_identity,
        "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "caps": caps,
        "deadlines_seconds": deadlines,
        "budgets": budgets,
    }


IDENTITY_CONTRACT = {
    "candidate_artifacts": "stream-hashed-before-and-after-execution",
    "runner_modules": "stream-hashed-before-and-after-execution",
    "filesystem_assumption": "controlled-local-no-adversarial-mid-run-replace-and-restore",
    "candidate_build_context": "observational-not-provenance",
}


def _recheck_bound_files(expected: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    observed: list[dict[str, Any]] = []
    failures: list[str] = []
    for item in expected:
        path = Path(str(item["path"]))
        try:
            current = _stream_file_identity(path)
        except (OSError, ProtocolError) as error:
            failures.append(f"{path}: {error}")
            continue
        observed.append(current)
        if any(current.get(key) != item.get(key) for key in ("path", "bytes", "stat", "sha256")):
            failures.append(f"{path}: path/content/stat identity changed")
    return observed, failures


def _identity_stability(candidate_artifacts: Sequence[Mapping[str, Any]], runner_modules: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    post_candidate, candidate_failures = _recheck_bound_files(candidate_artifacts)
    post_runner: dict[str, dict[str, Any]] = {}
    runner_failures: list[str] = []
    for module, expected in runner_modules.items():
        observed, failures = _recheck_bound_files([expected])
        if observed:
            post_runner[module] = observed[0]
        runner_failures.extend(f"runner module {module}: {failure}" for failure in failures)
    failures = [*candidate_failures, *runner_failures]
    return {
        "contract": dict(IDENTITY_CONTRACT),
        "pre_run": {"candidate_artifacts": [dict(item) for item in candidate_artifacts], "runner_modules": {module: dict(item) for module, item in runner_modules.items()}},
        "post_run": {"candidate_artifacts": post_candidate, "runner_modules": post_runner},
        "stability": "verified" if not failures else "failed",
        "failures": failures,
    }


def _mark_incomplete(result: dict[str, Any], reason: str) -> None:
    result["run_status"] = "incomplete"
    result["evidence_status"] = "incomplete"
    if result.get("failure") is None:
        result["failure"] = reason
    else:
        result.setdefault("additional_failures", []).append(reason)


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
        execution_command, executable, executable_sha256, command_artifacts = _resolve_candidate_executable(command)
        manifest, corpora, metadata = load_manifest(args.manifest)
        forbidden = [args.manifest.resolve()] + [args.manifest.parent / entry["path"] for entry in metadata["corpora"]] + [executable]
        output_path_safe(args.output, forbidden)
        candidate_identity = {"command": command, "execution_command": execution_command, "command_artifacts": command_artifacts, "executable": str(executable), "executable_sha256": executable_sha256, "feature": "provisional-r3-numeric-candidate", "evaluation_binding": EVALUATION_BINDING, "profile_binding": None, "profile_id": None, "build_identity": _build_identity(executable)}
        runner_identity = _runner_identity()
        session = BoundedSubprocessSession(execution_command, cwd=str(Path.cwd()))
        try:
            result = run_cases(corpora, metadata["case_info"], metadata["relations"], session, candidate_identity)
        finally:
            close_result = session.close()
        _apply_close_result(result, close_result)
        identity_evidence = _identity_stability(command_artifacts, runner_identity["module_identity"])
        if identity_evidence["stability"] != "verified":
            _mark_incomplete(result, "identity stability check failed")
        result["manifest"] = {"sha256": metadata["manifest_sha256"], "corpora": metadata["corpora"], "oracle_bound": metadata["oracle_bound"]}
        result["preregistration"] = metadata["preregistration"]
        result["runner"] = runner_identity
        result["result_identity"] = {
            "schema": "ck.exp-0002.result-identity-1",
            "evaluation_binding": EVALUATION_BINDING,
            "manifest_sha256": metadata["manifest_sha256"],
            "corpora": metadata["corpora"],
            "claim_domain": metadata["preregistration"]["claim_domain"],
            "tolerance_bindings": metadata["preregistration"]["tolerance_bindings"],
            "candidate_command": list(command),
            "candidate_execution_command": list(execution_command),
            "candidate_command_artifacts": command_artifacts,
            "runner_bundle_sha256": runner_identity["bundle_sha256"],
            "configured_budgets": runner_identity["budgets"],
            "build_identity": candidate_identity["build_identity"],
            "identity": identity_evidence,
            "profile_binding": None,
            "technology_result": TECHNOLOGY_RESULT,
        }
        _write_new_output(args.output, result)
        return 0 if result["run_status"] == "complete" and result["evidence_status"] == "passed" else 2
    except (ProtocolError, OracleBoundError, OSError) as error:
        print(f"EXP-0002 runner error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

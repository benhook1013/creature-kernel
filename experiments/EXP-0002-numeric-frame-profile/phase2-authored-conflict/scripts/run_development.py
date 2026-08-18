#!/usr/bin/env python3
"""Run the 16-case EXP-0002 development corpus against an explicit candidate.

This is a bounded diagnostic runner.  It evaluates all three development
candidate profiles but does not select a profile, create experiment evidence,
produce a receipt/result, resolve a source set, or activate Readiness 3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

import development_corpus as corpus
import profile_sweep
from phase2_adjudicator import AdjudicationError, classify_response, expectation_passes
from phase2_common import (
    MAX_REQUEST_ID_BYTES,
    REQUEST_PROTOCOL_ID,
    Phase2ProtocolError,
    frame_json,
    validate_response_frame,
)
from phase2_transport import BoundedSubprocessSession, Phase2TransportError


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = PACKAGE / "profiles" / "development-sweep.json"
DEFAULT_CORPUS = PACKAGE / "corpora" / "development" / "corpus.json"
REPORT_SCHEMA = "ck.exp-0002.r3-authored-conflict-development-diagnostic-1"
MAX_CANDIDATE_BYTES = 128 * 1024 * 1024
MAX_REPORT_BYTES = 128 * 1024
MAX_ARG_BYTES = 1024
MAX_ARGS = 16
EXPECTED_REQUESTS = 16 * 3


class DevelopmentRunError(ValueError):
    """Bounded input, candidate, report, or execution failure."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = _safe_detail(detail)
        super().__init__(f"{code}: {self.detail}")


def _safe_detail(value: object) -> str:
    text = str(value).replace("\x00", "?").replace("\n", " ").replace("\r", " ")
    return text[:256]


def _hash_file(path: Path, limit: int, label: str) -> tuple[str, int]:
    if path.is_symlink() or not path.is_file():
        raise DevelopmentRunError("file-type", f"{label} must be a regular non-symlink file")
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise DevelopmentRunError("symlink", f"{label} contains a symlink component")
        current = current.parent
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError as error:
        raise DevelopmentRunError("file-read", f"{label}: {error}") from error
    if len(raw) > limit:
        raise DevelopmentRunError("file-too-large", f"{label} exceeds {limit} bytes")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _candidate_identity(argv: Sequence[str]) -> tuple[list[str], Path, str, int, str]:
    if not argv or len(argv) > MAX_ARGS:
        raise DevelopmentRunError("candidate-argv", f"candidate argv must contain 1..{MAX_ARGS} entries")
    command = [str(value) for value in argv]
    for index, value in enumerate(command):
        if not value or len(value.encode("utf-8")) > MAX_ARG_BYTES:
            raise DevelopmentRunError("candidate-argv", f"candidate argv[{index}] is empty or oversized")
    raw_path = Path(command[0])
    path = raw_path if raw_path.is_absolute() else Path.cwd() / raw_path
    path = Path(os.path.abspath(path))
    digest, size = _hash_file(path, MAX_CANDIDATE_BYTES, "candidate executable")
    if not os.access(path, os.X_OK):
        raise DevelopmentRunError("candidate-executable", "candidate executable is not executable")
    command[0] = str(path)
    argv_bytes = json.dumps(command, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    argv_hash = hashlib.sha256(argv_bytes).hexdigest()
    return command, path, digest, size, argv_hash


def _bits_to_float(bits: str) -> float:
    integer = int(bits[2:], 16)
    return struct.unpack(">d", integer.to_bytes(8, "big"))[0]


def _profile_tolerances(candidate_id: str, override: Any, sweep: dict[str, Any] | None = None) -> dict[str, float]:
    if sweep is None:
        constants = profile_sweep.EXPECTED[candidate_id]
    else:
        candidates = {record["candidate_id"]: record for record in sweep["candidates"]}
        constants = candidates[candidate_id]["constants"]
    def bits(name: str) -> str:
        value = constants[name]
        return value["bits"] if isinstance(value, dict) else value[0]

    values = {
        "translation_absolute": _bits_to_float(bits("A")),
        "translation_relative": _bits_to_float(bits("R")),
        "rotation_half_chord": _bits_to_float(bits("H")),
    }
    if override is not None:
        if not isinstance(override, dict):
            raise DevelopmentRunError("tolerance-override", "corpus tolerance override is not an object")
        for field, value in override.items():
            if field not in values:
                raise DevelopmentRunError("tolerance-override", f"unknown override field {field}")
            if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                raise DevelopmentRunError("tolerance-override", f"invalid override value for {field}")
            try:
                converted = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise DevelopmentRunError("tolerance-override", f"invalid override value for {field}") from error
            if not math.isfinite(converted):
                raise DevelopmentRunError("tolerance-override", f"non-finite override value for {field}")
            values[field] = converted
    return values


def build_request(
    case: dict[str, Any],
    candidate_id: str,
    source: bytes,
    sweep: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one closed candidate request without selecting a profile."""
    request_id = f"dev-{case['case_id']}-{candidate_id}"
    if len(request_id.encode("utf-8")) > MAX_REQUEST_ID_BYTES:
        raise DevelopmentRunError("request-id", "deterministic request ID exceeds transport bound")
    try:
        source_text = source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DevelopmentRunError("source-utf8", "materialized source is not UTF-8") from error
    return {
        "protocol_id": REQUEST_PROTOCOL_ID,
        "request_id": request_id,
        "operation": "observe-authored-conflict",
        "resource_profile": "ordinary",
        "source": source_text,
        "tolerances": _profile_tolerances(candidate_id, case["tolerance_override"], sweep),
        "providers": dict(case["providers"]),
    }


def _entry(
    case: dict[str, Any],
    candidate_id: str,
    request_id: str,
    request_hash: str,
    response_hash: str | None,
    observed: str,
    observed_cause: dict[str, Any] | None,
    failure: str | None,
) -> dict[str, Any]:
    profile_id = profile_sweep.PROFILE_IDS[candidate_id]
    expected = case["expected"][profile_id]
    return {
        "case_id": case["case_id"],
        "candidate_id": candidate_id,
        "profile_id": profile_id,
        "request_id": request_id,
        "request_sha256": request_hash,
        "response_sha256": response_hash,
        "observed_classification": observed,
        "observed_cause": observed_cause,
        "expected_classification": expected["classification"],
        "expected_cause": expected["cause"],
        "pass": failure is None and expectation_passes(observed, observed_cause, expected),
        "failure": failure,
    }


def _report(
    entries: list[dict[str, Any]],
    input_hashes: dict[str, Any],
    failures: list[str],
    requests_sent: int,
) -> dict[str, Any]:
    classification_totals: dict[str, int] = {}
    for item in entries:
        classification = item["observed_classification"]
        classification_totals[classification] = classification_totals.get(classification, 0) + 1
    passed = sum(1 for item in entries if item["pass"])
    total = len(entries)
    failed = total - passed
    completed = sum(1 for item in entries if item["response_sha256"] is not None)
    return {
        "schema": REPORT_SCHEMA,
        "non_authoritative": True,
        "profile_selection": "none",
        "r3_activation": "inactive",
        "run_status": "pass" if total == EXPECTED_REQUESTS and failed == 0 and not failures else "fail",
        "inputs": input_hashes,
        "summary": {
            "planned": EXPECTED_REQUESTS,
            "entries": total,
            "requests_sent": requests_sent,
            "responses_received": completed,
            "passed": passed,
            "failed": failed,
            "classification_totals": classification_totals,
            "failures": failures,
        },
        "entries": entries,
    }


def _encode_report(report: dict[str, Any]) -> bytes:
    try:
        encoded = (json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise DevelopmentRunError("report-encode", "diagnostic report is not strict JSON") from error
    if len(encoded) > MAX_REPORT_BYTES:
        raise DevelopmentRunError("report-size", f"diagnostic report exceeds {MAX_REPORT_BYTES} bytes")
    return encoded


def run_development(
    candidate_argv: Sequence[str],
    *,
    sweep_path: Path | str = DEFAULT_SWEEP,
    corpus_path: Path | str = DEFAULT_CORPUS,
) -> dict[str, Any]:
    """Execute exactly 48 bounded requests and return a diagnostic report."""
    sweep_path = Path(sweep_path)
    corpus_path = Path(corpus_path)
    sweep = profile_sweep.load_profile_sweep(sweep_path)
    corpus_value = corpus.load_development_corpus(corpus_path)
    candidate_command, candidate_path, candidate_hash, candidate_size, argv_hash = _candidate_identity(candidate_argv)
    sweep_hash, sweep_size = _hash_file(sweep_path, profile_sweep.MAX_DEFINITION_BYTES, "sweep definition")
    corpus_hash, corpus_size = _hash_file(corpus_path, corpus.MAX_CORPUS_BYTES, "development corpus")
    input_hashes = {
        "sweep_definition_sha256": sweep_hash,
        "sweep_definition_bytes": sweep_size,
        "corpus_sha256": corpus_hash,
        "corpus_bytes": corpus_size,
        "candidate_executable_sha256": candidate_hash,
        "candidate_executable_bytes": candidate_size,
        "candidate_argv_sha256": argv_hash,
        "candidate_argv_count": len(candidate_command),
        "candidate_identity": "normalized argv sequence hash plus argv[0] executable bytes hash",
    }

    # The sweep loader has already checked these fields; retaining the explicit
    # assertion prevents a future caller from silently changing loop order.
    if sweep["selected_profile_id"] is not None or sweep["r3_activation"] != "inactive":
        raise DevelopmentRunError("activation-boundary", "sweep contains selection or activation")
    cases = corpus_value["cases"]
    if len(cases) != 16:
        raise DevelopmentRunError("case-count", "development run requires exactly 16 cases")

    entries: list[dict[str, Any]] = []
    failures: list[str] = []
    requests_sent = 0
    session_failed = False
    session_failure = ""
    session = BoundedSubprocessSession(candidate_command)
    close_result = None
    primary_error: Exception | None = None
    close_error: Exception | None = None
    try:
        for case in cases:
            source = corpus.materialize_case(case)
            for candidate_id in profile_sweep.CANDIDATE_IDS:
                request = build_request(case, candidate_id, source, sweep)
                try:
                    request_frame = frame_json(request)
                    request_hash = hashlib.sha256(request_frame).hexdigest()
                except Phase2ProtocolError as error:
                    failure = f"request:{error.code}"
                    failures.append(failure)
                    entries.append(_entry(case, candidate_id, request["request_id"], "", None, "incomplete", None, failure))
                    continue

                if session_failed:
                    failure = session_failure or "transport:session-failed"
                    entries.append(_entry(case, candidate_id, request["request_id"], request_hash, None, "incomplete", None, failure))
                    continue

                requests_sent += 1
                try:
                    response_frame = session.request_frame(request_frame)
                    response_hash = hashlib.sha256(response_frame).hexdigest()
                except Phase2TransportError as error:
                    failure = f"transport:{error.code}"
                    failures.append(failure)
                    session_failed = True
                    session_failure = failure
                    entries.append(_entry(case, candidate_id, request["request_id"], request_hash, None, "incomplete", None, failure))
                    continue

                try:
                    response = validate_response_frame(response_frame, request["request_id"])
                    observed, observed_cause = classify_response(response)
                    failure = None
                except (Phase2ProtocolError, AdjudicationError) as error:
                    observed, observed_cause = "incomplete", None
                    failure = f"response:{getattr(error, 'code', 'malformed')}"
                    failures.append(failure)
                entries.append(_entry(case, candidate_id, request["request_id"], request_hash, response_hash, observed, observed_cause, failure))
    except Exception as error:
        primary_error = error
    finally:
        try:
            close_result = session.close()
        except Exception as error:
            close_error = error
    if primary_error is not None:
        raise primary_error
    if close_error is not None:
        failures.append(f"transport:close:{_safe_detail(close_error)}")
    elif close_result is not None:
        if close_result.failure:
            failures.append(f"transport:{_safe_detail(close_result.failure)}")
        if close_result.returncode not in (0, None):
            failures.append(f"candidate-exit:{close_result.returncode}")
    # Preserve one occurrence per diagnostic code while retaining order.
    failures = list(dict.fromkeys(failures))
    report = _report(entries, input_hashes, failures, requests_sent)
    _encode_report(report)
    return report


def _error_report(error: Exception) -> dict[str, Any]:
    code = getattr(error, "code", "runner-error")
    detail = _safe_detail(error)
    return {
        "schema": REPORT_SCHEMA,
        "non_authoritative": True,
        "profile_selection": "none",
        "r3_activation": "inactive",
        "run_status": "fail",
        "inputs": {},
        "summary": {
            "planned": EXPECTED_REQUESTS,
            "entries": 0,
            "requests_sent": 0,
            "responses_received": 0,
            "passed": 0,
            "failed": 0,
            "classification_totals": {},
            "failures": [f"{code}:{detail}"],
        },
        "entries": [],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the non-authoritative EXP-0002 development diagnostic")
    parser.add_argument("--candidate", nargs="+", required=True, metavar="ARGV", help="candidate executable followed by explicit argv")
    parser.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args(argv)
    try:
        report = run_development(args.candidate, sweep_path=args.sweep, corpus_path=args.corpus)
    except Exception as error:  # keep CLI diagnostics bounded and body-free
        report = _error_report(error)
        encoded = _encode_report(report)
        sys.stdout.buffer.write(encoded)
        return 2
    sys.stdout.buffer.write(_encode_report(report))
    return 0 if report["run_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the separate six-case EXP-0002 development extension.

The extension is intentionally not folded into ``run_development.py``.  The
historical 16-case corpus and its 48-request report remain immutable evidence
of that earlier diagnostic.  This runner executes six new long-tail cases
against the same three development profiles (18 requests), and asks the
independent exact oracle to verify each complete response.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Any, Sequence

import development_extension_corpus as corpus
import development_extension_oracle as oracle
import profile_sweep
from phase2_common import MAX_REQUEST_ID_BYTES, REQUEST_PROTOCOL_ID, Phase2ProtocolError, frame_json, validate_response_frame
from phase2_transport import BoundedSubprocessSession, Phase2TransportError


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = PACKAGE / "profiles" / "development-sweep.json"
DEFAULT_CORPUS = PACKAGE / "corpora" / "development-extension" / "corpus.json"
REPORT_SCHEMA = "ck.exp-0002.r3-authored-conflict-development-extension-diagnostic-1"
REPORT_ID = "ck.exp-0002.r3-authored-conflict-development-extension-report-1"
MAX_CANDIDATE_BYTES = 128 * 1024 * 1024
MAX_REPORT_BYTES = 256 * 1024
MAX_ARG_BYTES = 1024
MAX_ARGS = 16
EXPECTED_CASES = 6
EXPECTED_REQUESTS = EXPECTED_CASES * len(profile_sweep.CANDIDATE_IDS)
EXPECTED_CLASSIFICATION_TOTALS = {"agree": 9, "conflict": 9}


class ExtensionRunError(ValueError):
    """Bounded input, identity, report, or execution failure."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", " ")[:256]
        super().__init__(f"{code}: {self.detail}")


def _hash_file(path: Path, limit: int, label: str) -> tuple[str, int]:
    if path.is_symlink() or not path.is_file():
        raise ExtensionRunError("file-type", f"{label} must be a regular non-symlink file")
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise ExtensionRunError("symlink", f"{label} contains a symlink component")
        current = current.parent
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ExtensionRunError("file-read", f"{label}: {error}") from error
    if len(raw) > limit:
        raise ExtensionRunError("file-too-large", f"{label} exceeds {limit} bytes")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _candidate_identity(argv: Sequence[str]) -> tuple[list[str], str, int, str]:
    if not argv or len(argv) > MAX_ARGS:
        raise ExtensionRunError("candidate-argv", f"candidate argv must contain 1..{MAX_ARGS} entries")
    command = [str(value) for value in argv]
    for index, value in enumerate(command):
        if not value or len(value.encode("utf-8")) > MAX_ARG_BYTES:
            raise ExtensionRunError("candidate-argv", f"candidate argv[{index}] is empty or oversized")
    raw_path = Path(command[0])
    path = Path(os.path.abspath(raw_path if raw_path.is_absolute() else Path.cwd() / raw_path))
    digest, size = _hash_file(path, MAX_CANDIDATE_BYTES, "candidate executable")
    if not os.access(path, os.X_OK):
        raise ExtensionRunError("candidate-executable", "candidate executable is not executable")
    command[0] = str(path)
    encoded = json.dumps(command, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return command, digest, size, hashlib.sha256(encoded).hexdigest()


def _bits_to_float(bits: str) -> float:
    try:
        integer = int(bits[2:], 16)
        value = struct.unpack(">d", integer.to_bytes(8, "big"))[0]
    except (ValueError, OverflowError):
        raise ExtensionRunError("sweep-bits", "invalid profile constant bits") from None
    if not math.isfinite(value):
        raise ExtensionRunError("sweep-bits", "profile constant is non-finite")
    return value


def _profile_tolerances(candidate_id: str, sweep: MappingLike) -> tuple[dict[str, float], dict[str, str]]:
    records = {record["candidate_id"]: record for record in sweep["candidates"]}
    constants = records[candidate_id]["constants"]
    fields = {"translation_absolute": "A", "translation_relative": "R", "rotation_half_chord": "H"}
    values: dict[str, float] = {}
    bits: dict[str, str] = {}
    for field, name in fields.items():
        constant = constants[name]
        bit_text = constant["bits"] if isinstance(constant, dict) else constant[0]
        bits[field] = bit_text
        values[field] = _bits_to_float(bit_text)
    return values, bits


MappingLike = dict[str, Any]


def build_request(case: MappingLike, candidate_id: str, source: bytes, sweep: MappingLike) -> tuple[dict[str, Any], dict[str, str]]:
    request_id = f"dev-ext-{case['case_id']}-{candidate_id}"
    if len(request_id.encode("utf-8")) > MAX_REQUEST_ID_BYTES:
        raise ExtensionRunError("request-id", "deterministic request ID exceeds transport bound")
    try:
        source_text = source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExtensionRunError("source-utf8", "materialized source is not UTF-8") from error
    tolerances, tolerance_bits = _profile_tolerances(candidate_id, sweep)
    return {
        "protocol_id": REQUEST_PROTOCOL_ID,
        "request_id": request_id,
        "operation": "observe-authored-conflict",
        "resource_profile": "ordinary",
        "source": source_text,
        "tolerances": tolerances,
        "providers": dict(case.get("providers", {"gate": "allow", "arithmetic": "native", "sqrt": "native", "environment": "unattested-no-probe-v1"})),
    }, tolerance_bits


def _entry(case: MappingLike, candidate_id: str, request_id: str, request_hash: str, response_hash: str | None, observed: str, expected: str, passed: bool, failure: str | None) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "candidate_id": candidate_id,
        "profile_id": profile_sweep.PROFILE_IDS[candidate_id],
        "request_id": request_id,
        "request_sha256": request_hash,
        "response_sha256": response_hash,
        "observed_classification": observed,
        "expected_classification": expected,
        "pass": passed,
        "failure": failure,
    }


def _report(entries: list[dict[str, Any]], inputs: dict[str, Any], failures: list[str], requests_sent: int) -> dict[str, Any]:
    totals: dict[str, int] = {}
    for item in entries:
        value = item["observed_classification"]
        totals[value] = totals.get(value, 0) + 1
    passed = sum(1 for item in entries if item["pass"])
    incomplete = sum(1 for item in entries if item["observed_classification"] == "incomplete")
    mismatches = sum(1 for item in entries if item["failure"] == "oracle:classification-mismatch")
    if len(entries) == EXPECTED_REQUESTS and passed == EXPECTED_REQUESTS and totals == EXPECTED_CLASSIFICATION_TOTALS and not failures:
        status = "pass"
    elif any(item["failure"] and item["failure"].startswith("oracle:") for item in entries):
        status = "fail"
    else:
        status = "inconclusive"
    return {
        "report_id": REPORT_ID,
        "schema": REPORT_SCHEMA,
        "non_authoritative": True,
        "profile_selection": "none",
        "r3_activation": "inactive",
        "run_status": status,
        "inputs": inputs,
        "summary": {
            "planned": EXPECTED_REQUESTS,
            "entries": len(entries),
            "requests_sent": requests_sent,
            "responses_received": sum(1 for item in entries if item["response_sha256"] is not None),
            "passed": passed,
            "failed": sum(1 for item in entries if not item["pass"]),
            "incomplete": incomplete,
            "expectation_mismatches": mismatches,
            "classification_totals": totals,
            "expected_classification_totals": EXPECTED_CLASSIFICATION_TOTALS,
            "failures": list(dict.fromkeys(failures)),
        },
        "entries": entries,
    }


def _encode(report: dict[str, Any]) -> bytes:
    try:
        raw = (json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ExtensionRunError("report-encode", "report is not strict JSON") from error
    if len(raw) > MAX_REPORT_BYTES:
        raise ExtensionRunError("report-size", "extension report exceeds bound")
    return raw


def run_development_extension(candidate_argv: Sequence[str], *, sweep_path: Path | str = DEFAULT_SWEEP, corpus_path: Path | str = DEFAULT_CORPUS) -> dict[str, Any]:
    sweep_path, corpus_path = Path(sweep_path), Path(corpus_path)
    sweep = profile_sweep.load_profile_sweep(sweep_path)
    extension = corpus.load_development_extension_corpus(corpus_path)
    cases = extension["cases"]
    if len(cases) != EXPECTED_CASES:
        raise ExtensionRunError("case-count", "extension requires exactly six cases")
    command, candidate_hash, candidate_size, argv_hash = _candidate_identity(candidate_argv)
    sweep_hash, sweep_size = _hash_file(sweep_path, profile_sweep.MAX_DEFINITION_BYTES, "sweep definition")
    corpus_hash, corpus_size = _hash_file(corpus_path, corpus.MAX_CORPUS_BYTES, "extension corpus")
    oracle_hash, oracle_size = _hash_file(Path(__file__).with_name("development_extension_oracle.py"), MAX_REPORT_BYTES, "oracle script")
    builder_hash, builder_size = _hash_file(Path(__file__).with_name("development_extension_corpus.py"), MAX_REPORT_BYTES, "corpus builder")
    inputs = {
        "extension_corpus_sha256": corpus_hash,
        "extension_corpus_bytes": corpus_size,
        "corpus_builder_sha256": builder_hash,
        "corpus_builder_bytes": builder_size,
        "oracle_sha256": oracle_hash,
        "oracle_bytes": oracle_size,
        "sweep_definition_sha256": sweep_hash,
        "sweep_definition_bytes": sweep_size,
        "candidate_executable_sha256": candidate_hash,
        "candidate_executable_bytes": candidate_size,
        "candidate_argv_sha256": argv_hash,
        "candidate_argv_count": len(command),
        "identity_basis": "extension corpus, builder, oracle, sweep, candidate bytes, and normalized argv",
    }
    entries: list[dict[str, Any]] = []
    failures: list[str] = []
    requests_sent = 0
    session_failed = False
    session_failure = ""
    session = BoundedSubprocessSession(command)
    close_result = None
    try:
        for case in cases:
            source = corpus.materialize_case(case)
            expected_map = case["expected"]
            for candidate_id in profile_sweep.CANDIDATE_IDS:
                profile_id = profile_sweep.PROFILE_IDS[candidate_id]
                expected = expected_map[profile_id]["classification"]
                request, tolerance_bits = build_request(case, candidate_id, source, sweep)
                request_hash = ""
                try:
                    request_frame = frame_json(request)
                    request_hash = hashlib.sha256(request_frame).hexdigest()
                except Phase2ProtocolError as error:
                    failure = f"inconclusive:request:{error.code}"
                    failures.append(failure)
                    entries.append(_entry(case, candidate_id, request["request_id"], request_hash, None, "incomplete", expected, False, failure))
                    continue
                if session_failed:
                    failure = session_failure or "inconclusive:transport:session-failed"
                    entries.append(_entry(case, candidate_id, request["request_id"], request_hash, None, "incomplete", expected, False, failure))
                    continue
                requests_sent += 1
                try:
                    response_frame = session.request_frame(request_frame)
                    response_hash = hashlib.sha256(response_frame).hexdigest()
                except Phase2TransportError as error:
                    failure = f"inconclusive:transport:{error.code}"
                    failures.append(failure)
                    session_failed, session_failure = True, failure
                    entries.append(_entry(case, candidate_id, request["request_id"], request_hash, None, "incomplete", expected, False, failure))
                    continue
                try:
                    response = validate_response_frame(response_frame, request["request_id"])
                    observed = oracle.verify_response(response, source, profile_id, tolerance_bits)
                    if observed != expected:
                        failure = "oracle:classification-mismatch"
                        failures.append(failure)
                        passed = False
                    else:
                        failure, passed = None, True
                except oracle.OracleIntegrityError as error:
                    observed, failure = "incomplete", f"inconclusive:oracle-integrity:{error.code}"
                    failures.append(failure)
                    passed = False
                except oracle.OracleError as error:
                    # The transport envelope was complete.  Any subsequent
                    # response shape, identity, witness, provider, or outcome
                    # disagreement is a candidate failure, not missing data.
                    observed, failure = "failed", f"oracle:{error.code}"
                    failures.append(failure)
                    passed = False
                except (Phase2ProtocolError, ValueError) as error:
                    code = getattr(error, "code", "malformed")
                    observed, failure, passed = "incomplete", f"inconclusive:response:{code}", False
                    failures.append(failure)
                entries.append(_entry(case, candidate_id, request["request_id"], request_hash, response_hash, observed, expected, passed, failure))
    finally:
        try:
            close_result = session.close()
        except Exception as error:
            failures.append(f"inconclusive:transport:close:{str(error)[:128]}")
    if close_result is not None:
        if close_result.failure:
            failures.append(f"inconclusive:transport:{str(close_result.failure).split(':', 1)[0]}")
        if close_result.returncode not in (0, None):
            failures.append(f"inconclusive:candidate-exit:{close_result.returncode}")
    report = _report(entries, inputs, failures, requests_sent)
    _encode(report)
    return report


def _error_report(error: Exception) -> dict[str, Any]:
    code = getattr(error, "code", "runner-error")
    return {
        "report_id": REPORT_ID,
        "schema": REPORT_SCHEMA,
        "non_authoritative": True,
        "profile_selection": "none",
        "r3_activation": "inactive",
        "run_status": "inconclusive",
        "inputs": {},
        "summary": {"planned": EXPECTED_REQUESTS, "entries": 0, "requests_sent": 0, "responses_received": 0, "passed": 0, "failed": 0, "incomplete": 0, "expectation_mismatches": 0, "classification_totals": {}, "expected_classification_totals": EXPECTED_CLASSIFICATION_TOTALS, "failures": [f"{code}:{str(error)[:256]}"],},
        "entries": [],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the non-authoritative EXP-0002 development extension")
    parser.add_argument("--candidate", required=True, metavar="PATH")
    parser.add_argument("--candidate-arg", action="append", default=[], metavar="VALUE")
    parser.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args(argv)
    try:
        report = run_development_extension([args.candidate, *args.candidate_arg], sweep_path=args.sweep, corpus_path=args.corpus)
    except Exception as error:
        report = _error_report(error)
        sys.stdout.buffer.write(_encode(report))
        return 2
    sys.stdout.buffer.write(_encode(report))
    return 0 if report["run_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Execution-incapable, experiment-wide Phase 3 closure adjudicator.

An exact attempt is evidence for one platform/ordinal only.  This module is
the sole consumer that may turn the three preregistered attempt results into
an experiment-level outcome.  It consumes exact record bytes, authenticates
their cross-bindings, and retains hashes rather than copying the evidence
records into a second mutable envelope.

The trust boundary is cooperative local record custody: hashes and canonical
record validators detect substitution and accidental replay, but do not claim
an untrusted process cannot rewrite a file after it was read.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import re
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence

import phase3_evidence_contract as evidence


SCHEMA = "ck.exp-0002.phase3.experiment-closure-1"
HASH_DOMAIN = b"ck.exp-0002.phase3.experiment-closure.v1\0"
PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
EXPERIMENT_ID = "EXP-0002"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"
EXPECTED_ORDINALS = (0, 1, 2)
EXPECTED_SELECTORS = {0: "wsl2-x86_64", 1: "wsl2-x86_64", 2: "ubuntu-24.04-x86_64"}
STATUSES = frozenset({"supported", "failed", "inconclusive"})
TERMINAL_SCHEMA = "ck.exp-0002.phase3.exact-attempt-terminal-failure-1"
TERMINAL_HASH_DOMAIN = b"ck.exp-0002.phase3.exact-attempt-terminal-failure.v1\0"
LEDGER_ID = "ck.exp-0002.phase3.experiment-slot-ledger.v1"
RESERVATION_SCHEMA = "ck.exp-0002.phase3.experiment-slot-reservation-1"
ATTEMPT_ID_RE = re.compile(r"^attempt-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
MAX_ATTEMPT_ID_BYTES = 256
MAX_RECORD_BYTES = 16 * 1024 * 1024
MAX_CLOSURE_BYTES = 512 * 1024
REQUEST_ID_MARKER = "<request-id>"


class ExperimentClosureError(ValueError):
    """Stable fail-closed error for closure authentication/adjudication."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", "")[:320]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str = "") -> None:
    raise ExperimentClosureError(code, detail)


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ExperimentClosureError("canonical-json", "value is not canonical JSON") from error


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _valid_sha(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _valid_commit(value: Any) -> bool:
    return type(value) is str and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _parse(raw: bytes, label: str, *, limit: int = MAX_RECORD_BYTES) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > limit or not raw.endswith(b"\n"):
        _fail("record", f"{label} is absent, oversized, or not LF terminated")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except ExperimentClosureError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise ExperimentClosureError("record", f"{label} is not strict JSON") from error
    if type(value) is not dict or _canonical(value) != raw:
        _fail("record", f"{label} is not a canonical object")
    return value


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            _fail("duplicate-json-key", key)
        result[key] = value
    return result


def _constant(token: str) -> None:
    _fail("nonfinite-json", token)


def _raw(value: Any, label: str) -> bytes:
    if type(value) is bytes:
        return value
    if type(value) is bytearray:
        _fail("record", f"{label} must be immutable bytes")
    _fail("record", f"{label} must be exact bytes")


def _record_field(record: Mapping[str, Any], *names: str) -> bytes | None:
    for name in names:
        if name in record:
            value = record[name]
            if value is None:
                return None
            return _raw(value, name)
    return None


def _self_hash(record: Mapping[str, Any], field: str, domain: bytes, *, strip_newline: bool = False) -> None:
    supplied = record.get(field)
    if not _valid_sha(supplied):
        _fail("record-hash", f"{field} is not a SHA-256")
    unsigned = dict(record)
    unsigned[field] = None
    raw = _canonical(unsigned)
    if strip_newline:
        raw = raw[:-1]
    if _sha(domain + raw) != supplied:
        _fail("record-hash", f"{field} does not authenticate its exact record")


def _freeze_module() -> Any:
    path = Path(__file__).with_name("phase3_freeze_manifest.py")
    spec = importlib.util.spec_from_file_location("phase3_experiment_closure_freeze", path)
    if spec is None or spec.loader is None:
        _fail("freeze", "freeze validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ExperimentClosureError("freeze", "freeze validator cannot be loaded") from error
    return module


def _validate_freeze(raw: bytes) -> dict[str, Any]:
    module = _freeze_module()
    try:
        value = module.validate_manifest(raw)
    except Exception as error:
        raise ExperimentClosureError("freeze", str(error)) from error
    current = getattr(module, "CURRENT_SCHEMA", getattr(module, "V3_SCHEMA", getattr(module, "SCHEMA", None)))
    if value.get("schema") != current:
        _fail("freeze-version", "closure requires the current immutable successor freeze")
    if value.get("execution_permitted") is not False:
        _fail("freeze-state", "freeze remains execution-disabled")
    if not _valid_sha(value.get("manifest_sha256")):
        _fail("freeze", "freeze self-hash is unavailable")
    return value


def _validate_bound_record(raw: bytes, label: str, *, freeze_hash: str, attempt: Mapping[str, Any], freeze_source_commit: str | None = None, expected_admission_hash: str | None = None, expected_custody_hash: str | None = None) -> dict[str, Any]:
    value = _parse(raw, label, limit=MAX_RECORD_BYTES)
    if value.get("experiment_id") != EXPERIMENT_ID or value.get("phase_id") != PHASE_ID or value.get("candidate_profile_id") != CANDIDATE_PROFILE_ID:
        _fail("record-binding", f"{label} has the wrong experiment identity")
    if label == "admission":
        if value.get("schema") != "ck.exp-0002.phase3.gate-b-admission-1":
            _fail("admission-schema", "admission schema is not the frozen contract")
        if value.get("freeze_manifest_sha256") != freeze_hash or value.get("execution_permitted") is not False or value.get("status") != "passed":
            _fail("admission-binding", "admission is not bound to the frozen execution-disabled package")
        required = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "freeze_manifest_sha256", "execution_tool_source_commit", "reviewed_commit", "reviews", "status", "execution_permitted", "admission_record_sha256"}
        if set(value) != required:
            _fail("admission-shape", "admission record is not the closed reviewed contract")
        execution_source = value.get("execution_tool_source_commit")
        reviewed_commit = value.get("reviewed_commit")
        if not _valid_commit(execution_source) or not _valid_commit(reviewed_commit):
            _fail("admission-binding", "admission commit identities are not full lowercase commit SHAs")
        if not _valid_commit(freeze_source_commit) or execution_source != freeze_source_commit:
            _fail("admission-binding", "admission execution source differs from the frozen execution source")
        if reviewed_commit == execution_source:
            _fail("admission-binding", "admission reviewed commit must be distinct from the execution source")
        reviews = value.get("reviews")
        if type(reviews) is not list or len(reviews) != 2:
            _fail("admission-reviews", "admission does not retain exactly two reviews")
        lenses: set[str] = set()
        reviewers: set[str] = set()
        paths: set[str] = set()
        for review in reviews:
            required_review = {"review_id", "reviewer", "lens", "path", "bytes", "sha256", "status", "disposition", "findings"}
            if not isinstance(review, Mapping) or set(review) != required_review or review.get("status") != "passed" or review.get("disposition") != "Clean" or review.get("findings") != []:
                _fail("admission-reviews", "admission review is not a passed Clean review")
            if not isinstance(review["reviewer"], str) or not review["reviewer"] or not isinstance(review["lens"], str) or not review["lens"] or not isinstance(review["path"], str) or not review["path"].endswith(".md") or not _valid_sha(review["sha256"]):
                _fail("admission-reviews", "admission review identity is incomplete")
            if type(review["bytes"]) is not int or review["bytes"] <= 0 or review["bytes"] > 256 * 1024:
                _fail("admission-reviews", "admission review byte bound is invalid")
            lenses.add(review["lens"]); reviewers.add(review["reviewer"]); paths.add(review["path"])
        if len(lenses) != 2 or len(reviewers) != 2 or len(paths) != 2:
            _fail("admission-reviews", "admission review identities are not independent")
        _self_hash(value, "admission_record_sha256", b"ck.exp-0002.phase3.gate-b-admission.v1\0", strip_newline=True)
    elif label == "authorization":
        if value.get("schema") != "ck.exp-0002.phase3.exact-attempt-human-authorization-1":
            _fail("authorization-schema", "authorization schema is not the frozen contract")
        if value.get("freeze_manifest_sha256") != freeze_hash or value.get("attempt_id") != attempt["attempt_id"] or value.get("platform_selector") != attempt["platform_selector"] or value.get("ordinal") != attempt["ordinal"]:
            _fail("authorization-binding", "authorization does not bind the exact attempt slot")
        if value.get("execution_permitted") is not True or value.get("automatic_retry") is not False:
            _fail("authorization-policy", "authorization is not the fixed one-attempt policy")
        required = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "admission_record_sha256", "freeze_manifest_sha256", "custody_record_sha256", "attempt_id", "platform_selector", "ordinal", "authorization_reference", "scope", "execution_permitted", "automatic_retry", "authorization_record_sha256"}
        if set(value) != required:
            _fail("authorization-shape", "authorization record is not closed")
        if expected_admission_hash is not None and value.get("admission_record_sha256") != expected_admission_hash:
            _fail("admission-binding", "authorization does not bind the exact admission bytes")
        if value.get("scope") != "exact-attempt" or value.get("ordinal") != attempt["ordinal"]:
            _fail("authorization-policy", "authorization scope or ordinal is not the fixed attempt policy")
        reference = value.get("authorization_reference")
        if not isinstance(reference, str) or not reference.strip() or reference.casefold().strip() in {"tbd", "todo", "pending", "placeholder", "none", "null", "n/a", "na"}:
            _fail("authorization-reference", "authorization reference is empty or a placeholder")
        if expected_custody_hash is not None and value.get("custody_record_sha256") != expected_custody_hash:
            _fail("custody-binding", "authorization custody hash differs")
        _self_hash(value, "authorization_record_sha256", b"ck.exp-0002.phase3.exact-attempt-human-authorization.v1\0", strip_newline=True)
    elif label == "custody":
        if value.get("schema") != "ck.exp-0002.phase3.gate-b-exact-artifact-custody-1":
            _fail("custody-schema", "custody schema is not the frozen contract")
        if value.get("successor_manifest_sha256") != freeze_hash:
            _fail("custody-binding", "custody is not bound to the exact successor freeze")
        required = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "successor_manifest_sha256", "platform", "candidate_source_commit", "receipt", "candidate", "transfer", "policy", "custody_record_sha256"}
        if set(value) != required:
            _fail("custody-shape", "custody record is not closed")
        platform = value.get("platform")
        if not isinstance(platform, Mapping) or platform.get("selector") != attempt["platform_selector"] or platform.get("role") not in {"wsl", "native"}:
            _fail("custody-binding", "custody platform differs from the attempt slot")
        transfer = value.get("transfer")
        if not isinstance(transfer, Mapping) or transfer.get("kind") not in {"invocation-owned-raw-bundle-tar", "github-actions-artifact-zip"}:
            _fail("custody-transfer", "custody transfer lineage is absent or unsupported")
        locator = transfer.get("locator")
        if not isinstance(locator, Mapping) or locator.get("kind") != "filesystem-path" or not isinstance(locator.get("value"), str) or not locator["value"].startswith("/"):
            _fail("custody-transfer", "custody transfer locator is not an absolute supplied path")
        if transfer["kind"] == "github-actions-artifact-zip":
            workflow = transfer.get("workflow")
            run = transfer.get("run")
            artifact = transfer.get("artifact")
            if not isinstance(workflow, Mapping) or not _valid_commit(workflow.get("commit")) or not _valid_sha(workflow.get("sha256")) or workflow.get("path") != ".github/workflows/phase3-gate-b-native-build.yml":
                _fail("custody-transfer", "GitHub workflow lineage is incomplete")
            if not isinstance(run, Mapping) or type(run.get("id")) is not int or type(run.get("attempt")) is not int:
                _fail("custody-transfer", "GitHub run lineage is incomplete")
            if not isinstance(artifact, Mapping) or type(artifact.get("id")) is not int or not isinstance(artifact.get("digest"), str):
                _fail("custody-transfer", "GitHub artifact lineage is incomplete")
        elif set(transfer) != {"kind", "locator", "bundle", "created_at", "expires_at", "retention_days"}:
            _fail("custody-transfer", "raw transfer lineage is not closed")
        receipt = value.get("receipt")
        if not isinstance(receipt, Mapping) or set(receipt) != {"path", "mode", "bytes", "sha256", "self_hash"} or receipt.get("path") != "build-receipt.json" or receipt.get("mode") != stat.S_IFREG | 0o644 or not _valid_sha(receipt.get("sha256")) or not _valid_sha(receipt.get("self_hash")):
            _fail("custody-receipt", "custody receipt identity is not closed")
        candidate = value.get("candidate")
        if not isinstance(candidate, Mapping) or set(candidate) != {"path", "mode", "bytes", "sha256"} or candidate.get("path") != "candidate" or candidate.get("mode") != stat.S_IFREG | 0o755 or not _valid_sha(candidate.get("sha256")):
            _fail("custody-candidate", "custody candidate identity is not closed")
        if value.get("policy") != {"custody": "declared", "candidate_execution": "prohibited", "experiment_dispatch": "prohibited", "causal_build_attestation": False}:
            _fail("custody-policy", "custody policy is not execution-prohibited")
        # Unlike admission and human-authorization records, the custody
        # contract authenticates its unsigned canonical JSON *including* the
        # terminating LF.  The value used by authorization/result binding is
        # this domain-separated field, never SHA-256(custody_raw).
        _self_hash(value, "custody_record_sha256", b"ck.exp-0002.phase3.gate-b-exact-artifact-custody.v1\0")
    else:
        _fail("record", f"unknown bound record {label}")
    return value


def _validate_terminal(raw: bytes, *, freeze_hash: str, ordinal: int) -> dict[str, Any]:
    value = _parse(raw, "terminal failure", limit=16 * 1024)
    required = {"schema", "ledger_id", "successor_manifest_sha256", "platform_selector", "ordinal", "attempt_id", "status", "code", "detail", "terminal_record_sha256"}
    if set(value) != required or value.get("schema") != TERMINAL_SCHEMA or value.get("ledger_id") != LEDGER_ID:
        _fail("terminal-schema", "terminal failure record is not the canonical ledger-bound contract")
    if value.get("successor_manifest_sha256") != freeze_hash or value.get("ordinal") != ordinal or EXPECTED_SELECTORS.get(ordinal) != value.get("platform_selector"):
        _fail("terminal-binding", "terminal failure record does not bind the expected slot")
    attempt_id = value.get("attempt_id")
    if (
        not isinstance(attempt_id, str)
        or not attempt_id
        or len(attempt_id.encode("utf-8", errors="replace")) > MAX_ATTEMPT_ID_BYTES
        or ATTEMPT_ID_RE.fullmatch(attempt_id) is None
        or attempt_id in {"attempt-id", "attempt-000"}
    ):
        _fail("terminal-binding", "terminal failure attempt ID is malformed")
    code = value.get("code")
    detail = value.get("detail")
    try:
        code_bytes = len(code.encode("utf-8")) if isinstance(code, str) else -1
        detail_bytes = len(detail.encode("utf-8")) if isinstance(detail, str) else -1
    except UnicodeEncodeError:
        code_bytes = detail_bytes = -1
    if (
        value.get("status") not in {"failed", "inconclusive"}
        or not isinstance(code, str) or not code or code_bytes > 128 or code_bytes < 0
        or not isinstance(detail, str) or not detail or detail_bytes > 1024 or detail_bytes < 0
    ):
        _fail("terminal-schema", "terminal failure disposition is malformed")
    unsigned = dict(value); unsigned["terminal_record_sha256"] = None
    # The publication ledger hashes the canonical object without its
    # terminating LF, matching the experiment's other authorization-style
    # self-hash conventions.
    if _sha(TERMINAL_HASH_DOMAIN + _canonical(unsigned)[:-1]) != value["terminal_record_sha256"]:
        _fail("terminal-hash", "terminal failure self-hash does not match")
    return value


def _validate_reservation_record(raw: bytes, *, freeze_hash: str, ordinal: int) -> dict[str, Any]:
    """Validate the exact retained bytes of the consumed slot marker."""
    value = _parse(raw, "experiment slot reservation", limit=16 * 1024)
    required = {"schema", "ledger_id", "successor_manifest_sha256", "platform_selector", "ordinal", "attempt_id"}
    if set(value) != required or value.get("schema") != RESERVATION_SCHEMA or value.get("ledger_id") != LEDGER_ID:
        _fail("reservation-schema", "reservation record is not the canonical ledger contract")
    if value.get("successor_manifest_sha256") != freeze_hash or value.get("ordinal") != ordinal or EXPECTED_SELECTORS.get(ordinal) != value.get("platform_selector"):
        _fail("reservation-binding", "reservation record does not bind the expected slot")
    if not isinstance(value.get("attempt_id"), str) or ATTEMPT_ID_RE.fullmatch(value["attempt_id"]) is None:
        _fail("reservation-binding", "reservation record attempt ID is malformed")
    return value


def _canonical_authority_and_custody(
    *, freeze_raw: bytes, admission_raw: bytes, custody_raw: bytes, freeze_hash: str,
) -> None:
    """Run the canonical authority/custody owners for a real frozen package.

    Synthetic fixtures intentionally use a minimal patched freeze owner; those
    are covered by the complete equivalent checks above.  A real v3 freeze
    carries the full binary/review/tool sections and therefore must pass the
    canonical repository-bound validators before closure can compare results.
    """
    if not isinstance(freeze_raw, bytes):
        return
    try:
        if not isinstance(_validate_freeze(freeze_raw).get("binaries"), Mapping):
            return
        base = Path(__file__).parent
        for name in ("phase3_exact_authority.py", "phase3_exact_custody.py"):
            path = base / name
            spec = importlib.util.spec_from_file_location(f"phase3_closure_owner_{name.replace('.', '_')}", path)
            if spec is None or spec.loader is None:
                _fail("owner-validator", f"canonical {name} cannot be loaded")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if name == "phase3_exact_authority.py":
                module.validate_gate_b_admission(
                    admission_raw,
                    freeze_manifest=freeze_raw,
                    review_root=base.parent / "reviews",
                )
            else:
                module.validate_custody_record(
                    custody_raw,
                    expected_manifest=freeze_raw,
                    expected_manifest_sha256=freeze_hash,
                )
    except ExperimentClosureError:
        raise
    except Exception as error:
        _fail("owner-validator", str(error))


def _normalize_wire(raw_b64: Any) -> tuple[Any, str] | None:
    if type(raw_b64) is not str:
        return None
    try:
        raw = base64.b64decode(raw_b64.encode("ascii"), validate=True)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or "request_id" not in value:
        return None
    value["request_id"] = REQUEST_ID_MARKER
    normalized = _canonical(value)
    return base64.b64encode(normalized).decode("ascii"), _sha(normalized)


def _semantic_adjudications(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize only request IDs; witness bits and semantic values stay exact."""
    normalized: list[dict[str, Any]] = []
    for item in result["adjudications"]:
        copy = json.loads(json.dumps(item))
        copy["request_id"] = REQUEST_ID_MARKER
        evidence_obj = copy.get("evidence")
        if isinstance(evidence_obj, dict):
            payload = evidence_obj.get("payload")
            if isinstance(payload, dict):
                for side in ("request", "response"):
                    wire = payload.get(side)
                    if isinstance(wire, dict) and "bytes_b64" in wire:
                        updated = _normalize_wire(wire["bytes_b64"])
                        if updated is not None:
                            wire["bytes_b64"], wire["sha256"] = updated
                evidence_obj["payload"] = payload
        copy["evidence_sha256"] = _sha(_canonical(copy["evidence"])) if isinstance(copy.get("evidence"), dict) else copy.get("evidence_sha256")
        normalized.append(copy)
    return normalized


def _semantic_projection(result: Mapping[str, Any]) -> dict[str, Any]:
    """Build the cross-attempt projection of comparable semantic results.

    Process/platform/lifecycle observations establish whether an individual
    attempt is admissible, but are not semantic outputs.  They intentionally
    do not participate here: descriptor identity, rusage, paths, launch
    environments, and platform facts differ legitimately between WSL and
    native runs.  The adjudications retain the exact classifications,
    witnesses, intervals, and semantic outputs; only request identifiers are
    normalized by ``_semantic_adjudications``.
    """
    return {
        "status": result["status"],
        "counts": json.loads(json.dumps(result["counts"])),
        "adjudications": _semantic_adjudications(result),
    }


def _attempt_semantics(result: Mapping[str, Any]) -> str:
    return _sha(HASH_DOMAIN + _canonical(_semantic_projection(result)))


def _attempt_metadata(result: Mapping[str, Any]) -> dict[str, Any]:
    attempt = result.get("attempt")
    if not isinstance(attempt, Mapping):
        _fail("result-binding", "result attempt metadata is missing")
    required = ("freeze_manifest_sha256", "attempt_id", "platform_selector", "ordinal", "authorization_reference", "gate_b_admission_sha256", "authorization_record_sha256", "custody_record_sha256")
    if any(key not in attempt for key in required):
        _fail("result-binding", "result attempt metadata is incomplete")
    selector = attempt["platform_selector"]
    ordinal = attempt["ordinal"]
    if EXPECTED_SELECTORS.get(ordinal) != selector:
        _fail("result-binding", "result platform/ordinal is not preregistered")
    return dict(attempt)


def _validate_attempt(record: Mapping[str, Any], ordinal: int, freeze: Mapping[str, Any]) -> dict[str, Any]:
    freeze_raw = _record_field(record, "freeze_manifest", "freeze_manifest_bytes", "freeze_bytes")
    admission_raw = _record_field(record, "admission", "admission_record", "admission_bytes")
    authorization_raw = _record_field(record, "authorization", "authorization_record", "authorization_bytes")
    custody_raw = _record_field(record, "custody", "custody_record", "custody_bytes")
    result_raw = _record_field(record, "result", "result_bytes")
    receipt_raw = _record_field(record, "receipt", "receipt_bytes")
    index_raw = _record_field(record, "index", "attempt_index", "index_bytes")
    terminal_raw = _record_field(record, "terminal", "terminal_failure", "terminal_bytes")
    reservation_raw = _record_field(record, "reservation", "reservation_record", "reservation_bytes", "slot_marker")
    required = (freeze_raw, admission_raw, authorization_raw, custody_raw, result_raw, receipt_raw, index_raw)
    if reservation_raw is None and any(item is not None for item in (*required, terminal_raw)):
        _fail("reservation-missing", "occupied slot evidence does not retain its canonical reservation record")
    if any(item is None for item in required):
        if freeze_raw is not None:
            supplied = _validate_freeze(freeze_raw)
            if supplied != freeze:
                _fail("freeze-binding", "partial attempt freeze differs from the closure freeze")
        reservation = _validate_reservation_record(reservation_raw, freeze_hash=freeze["manifest_sha256"], ordinal=ordinal) if reservation_raw is not None and freeze_raw is not None else None
        terminal = _validate_terminal(terminal_raw, freeze_hash=freeze["manifest_sha256"], ordinal=ordinal) if terminal_raw is not None and freeze_raw is not None else None
        if reservation is not None and terminal is not None and reservation["attempt_id"] != terminal["attempt_id"]:
            _fail("reservation-binding", "terminal failure attempt ID differs from the consumed reservation")
        names = ("freeze", "admission", "authorization", "custody", "result", "receipt", "index")
        missing = [name for name, item in zip(names, required) if item is None]
        if reservation is not None and terminal is None:
            # A durable consumed marker with no terminal record is an
            # abandoned reservation, never a merely missing optional field.
            missing.append("terminal")
        summary = {"ordinal": ordinal, "selector": EXPECTED_SELECTORS[ordinal], "attempt_status": terminal["status"] if terminal is not None else ("inconclusive" if reservation is not None else None), "missing": missing, "record_hashes": {name: None if item is None else _sha(item) for name, item in zip(names, required)}}
        if reservation is not None:
            summary["reservation_record_sha256"] = _sha(reservation_raw)
            summary["attempt_id"] = reservation["attempt_id"]
        if terminal is not None:
            summary["attempt_id"] = terminal["attempt_id"]
            summary["terminal_record_sha256"] = _sha(terminal_raw)
        return summary
    if terminal_raw is not None:
        _fail("terminal-extra", "a complete published attempt cannot also carry terminal failure evidence")
    supplied_freeze = _validate_freeze(freeze_raw)
    if supplied_freeze != freeze:
        _fail("freeze-binding", "attempt freeze bytes differ across slots")
    freeze_hash = freeze["manifest_sha256"]
    reservation = _validate_reservation_record(reservation_raw, freeze_hash=freeze_hash, ordinal=ordinal)
    result = evidence.validate_result(result_raw)
    attempt = _attempt_metadata(result)
    if attempt["ordinal"] != ordinal or attempt["freeze_manifest_sha256"] != freeze_hash:
        _fail("result-binding", "result does not bind the expected slot/freeze")
    if record.get("attempt_id") is not None and record.get("attempt_id") != attempt["attempt_id"]:
        _fail("attempt-binding", "caller slot metadata differs from result attempt ID")
    if record.get("platform_selector") is not None and record.get("platform_selector") != attempt["platform_selector"]:
        _fail("platform-binding", "caller slot metadata differs from result platform")
    if reservation["attempt_id"] != attempt["attempt_id"]:
        _fail("reservation-binding", "result attempt ID differs from the consumed reservation")
    _canonical_authority_and_custody(
        freeze_raw=freeze_raw,
        admission_raw=admission_raw,
        custody_raw=custody_raw,
        freeze_hash=freeze_hash,
    )
    admission_hash = _sha(admission_raw)
    admission = _validate_bound_record(admission_raw, "admission", freeze_hash=freeze_hash, attempt=attempt, freeze_source_commit=freeze.get("execution_tool_source_commit"))
    custody = _validate_bound_record(custody_raw, "custody", freeze_hash=freeze_hash, attempt=attempt)
    custody_hash = custody["custody_record_sha256"]
    authorization = _validate_bound_record(authorization_raw, "authorization", freeze_hash=freeze_hash, attempt=attempt, expected_admission_hash=admission_hash, expected_custody_hash=custody_hash)
    if authorization.get("authorization_reference") != attempt["authorization_reference"]:
        _fail("authorization-binding", "result authorization reference differs from the exact authorization record")
    if attempt["gate_b_admission_sha256"] != _sha(admission_raw) or attempt["authorization_record_sha256"] != _sha(authorization_raw) or attempt["custody_record_sha256"] != custody_hash:
        _fail("result-binding", "result does not retain the exact authority/custody hashes")
    receipt = evidence.validate_receipt(receipt_raw, result_raw)
    index = evidence.validate_attempt_index(index_raw, result_raw, receipt_raw)
    if receipt["attempt"] != attempt or index["attempt"] != attempt:
        _fail("record-binding", "receipt/index attempt metadata differs from result")
    attempt_status = result["status"]
    semantic_sha = _attempt_semantics(result)
    return {
        "ordinal": ordinal,
        "selector": attempt["platform_selector"],
        "attempt_id": attempt["attempt_id"],
        "attempt_status": attempt_status,
        "semantic_sha256": semantic_sha,
        "missing": [],
        "reservation_record_sha256": _sha(reservation_raw),
        "record_hashes": {name: _sha(raw) for name, raw in (("freeze", freeze_raw), ("admission", admission_raw), ("authorization", authorization_raw), ("custody", custody_raw), ("result", result_raw), ("receipt", receipt_raw), ("index", index_raw))},
        "result_sha256": _sha(result_raw),
        "receipt_sha256": _sha(receipt_raw),
        "index_sha256": _sha(index_raw),
        "_semantic": _semantic_adjudications(result),
    }


def _strip_private(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if not key.startswith("_")}


def build_experiment_closure(
    attempt_records: Sequence[Mapping[str, Any]] | None = None,
    *,
    attempts: Sequence[Mapping[str, Any]] | None = None,
    allow_missing: bool = True,
) -> bytes:
    """Authenticate ordinals 0/1/2 and emit the sole experiment outcome."""
    if attempt_records is None:
        attempt_records = attempts if attempts is not None else ()
    elif attempts is not None:
        _fail("attempts", "attempt records were supplied twice")
    if isinstance(attempt_records, Mapping):
        expanded: list[Mapping[str, Any]] = []
        for key, value in attempt_records.items():
            if not isinstance(value, Mapping):
                _fail("attempts", "ordinal mapping contains a non-object record")
            item = dict(value)
            item.setdefault("ordinal", key)
            expanded.append(item)
        attempt_records = expanded
    if not isinstance(attempt_records, Sequence) or isinstance(attempt_records, (str, bytes, bytearray)):
        _fail("attempts", "attempt records must be a sequence")
    by_ordinal: dict[int, Mapping[str, Any]] = {}
    for record in attempt_records:
        if not isinstance(record, Mapping):
            _fail("attempts", "attempt record is not an object")
        ordinal = record.get("ordinal")
        if type(ordinal) is not int or ordinal not in EXPECTED_ORDINALS:
            _fail("ordinal", "attempt record has an unexpected ordinal")
        if ordinal in by_ordinal:
            _fail("duplicate", f"ordinal {ordinal} appears more than once")
        by_ordinal[ordinal] = record
    extras = set(by_ordinal) - set(EXPECTED_ORDINALS)
    if extras:
        _fail("extra", "attempt records contain unexpected ordinals")
    freeze_raw = None
    for ordinal in EXPECTED_ORDINALS:
        if ordinal in by_ordinal:
            freeze_raw = _record_field(by_ordinal[ordinal], "freeze_manifest", "freeze_manifest_bytes", "freeze_bytes")
            if freeze_raw is not None:
                break
    if freeze_raw is None:
        missing_summaries = [{"ordinal": ordinal, "selector": EXPECTED_SELECTORS[ordinal], "attempt_status": None, "missing": ["freeze"], "record_hashes": {name: None for name in ("freeze", "admission", "authorization", "custody", "result", "receipt", "index")}} for ordinal in EXPECTED_ORDINALS]
        if not allow_missing:
            _fail("missing", "no frozen closure input is available")
        statuses = missing_summaries
        freeze_hash = None
    else:
        freeze = _validate_freeze(freeze_raw)
        freeze_hash = freeze["manifest_sha256"]
        statuses = [_validate_attempt(by_ordinal[ordinal], ordinal, freeze) if ordinal in by_ordinal else {"ordinal": ordinal, "selector": EXPECTED_SELECTORS[ordinal], "attempt_status": None, "missing": ["attempt"], "record_hashes": {name: None for name in ("freeze", "admission", "authorization", "custody", "result", "receipt", "index")}} for ordinal in EXPECTED_ORDINALS]
    if not allow_missing and any(item.get("missing") for item in statuses):
        _fail("missing", "experiment closure is missing one or more required attempt records")
    attempt_ids = [item.get("attempt_id") for item in statuses if isinstance(item.get("attempt_id"), str)]
    if len(attempt_ids) != len(set(attempt_ids)):
        _fail("duplicate-attempt-id", "closure contains the same attempt ID in more than one slot")
    complete = [item for item in statuses if not item.get("missing")]
    # Only complete, supported attempts are comparable semantic observations.
    # Failed or inconclusive attempts may retain different partial witnesses;
    # those differences must not be reclassified as semantic disagreement.
    comparable = [item for item in complete if item.get("attempt_status") == "supported"]
    semantic_mismatch = len({item.get("semantic_sha256") for item in comparable}) > 1
    if any(item.get("attempt_status") == "failed" for item in statuses):
        outcome = "failed"
        reason = "attempt-failed"
    elif semantic_mismatch:
        outcome = "failed"
        reason = "semantic-output-mismatch"
    elif len(complete) != len(EXPECTED_ORDINALS) or any(item.get("attempt_status") == "inconclusive" for item in statuses):
        outcome = "inconclusive"
        reason = "incomplete-attempt-closure"
    elif not all(item.get("attempt_status") == "supported" for item in statuses):
        outcome = "inconclusive"
        reason = "attempt-status-not-supported"
    else:
        outcome = "supported"
        reason = None
    body = {
        "schema": SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "candidate_profile_id": CANDIDATE_PROFILE_ID,
        "freeze_manifest_sha256": freeze_hash,
        "required_ordinals": list(EXPECTED_ORDINALS),
        "attempts": [_strip_private(item) for item in statuses],
        "normalization": {"request_ids": REQUEST_ID_MARKER, "only": ["request IDs"]},
        "comparison": {"semantic_equality": not semantic_mismatch, "status_precedence": ["failed", "inconclusive", "supported"], "witnesses": "exact status/classification/binary64 witness bits/interval endpoints/semantic output"},
        "status": outcome,
        "reason": reason,
        "closure_self_hash": None,
    }
    body["closure_self_hash"] = _sha(HASH_DOMAIN + _canonical(body))
    raw = _canonical(body)
    if len(raw) > MAX_CLOSURE_BYTES:
        _fail("size", "experiment closure exceeds its bound")
    return raw


def validate_experiment_closure(raw: bytes) -> dict[str, Any]:
    value = _parse(raw, "experiment closure", limit=MAX_CLOSURE_BYTES)
    required = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "freeze_manifest_sha256", "required_ordinals", "attempts", "normalization", "comparison", "status", "reason", "closure_self_hash"}
    if set(value) != required or value["schema"] != SCHEMA or value["experiment_id"] != EXPERIMENT_ID or value["phase_id"] != PHASE_ID or value["candidate_profile_id"] != CANDIDATE_PROFILE_ID:
        _fail("closure-schema", "experiment closure schema is not closed")
    if value["required_ordinals"] != list(EXPECTED_ORDINALS) or not _valid_sha(value["closure_self_hash"]):
        _fail("closure-schema", "required ordinals or self-hash is invalid")
    if value["freeze_manifest_sha256"] is not None and not _valid_sha(value["freeze_manifest_sha256"]):
        _fail("closure-schema", "closure freeze hash is invalid")
    expected_normalization = {"request_ids": REQUEST_ID_MARKER, "only": ["request IDs"]}
    normalization = value.get("normalization")
    if normalization != expected_normalization:
        _fail("closure-schema", "closure normalization declaration is not exact")
    comparison = value.get("comparison")
    if not isinstance(comparison, Mapping) or set(comparison) != {"semantic_equality", "status_precedence", "witnesses"} or comparison.get("status_precedence") != ["failed", "inconclusive", "supported"] or comparison.get("witnesses") != "exact status/classification/binary64 witness bits/interval endpoints/semantic output":
        _fail("closure-schema", "closure comparison declaration is not exact")
    unsigned = dict(value)
    unsigned["closure_self_hash"] = None
    if _sha(HASH_DOMAIN + _canonical(unsigned)) != value["closure_self_hash"]:
        _fail("closure-self-hash", "experiment closure self-hash does not match")
    if value["status"] not in STATUSES:
        _fail("closure-status", "experiment closure status is invalid")
    attempts = value["attempts"]
    if type(attempts) is not list or [item.get("ordinal") for item in attempts if isinstance(item, Mapping)] != list(EXPECTED_ORDINALS):
        _fail("closure-attempts", "closure does not contain ordinals 0, 1, 2 exactly once")
    for index, item in enumerate(attempts):
        if not isinstance(item, Mapping):
            _fail("closure-attempts", f"attempt summary {index} is not an object")
        allowed = {"ordinal", "selector", "attempt_id", "attempt_status", "semantic_sha256", "missing", "record_hashes", "result_sha256", "receipt_sha256", "index_sha256", "terminal_record_sha256", "reservation_record_sha256"}
        required_summary = {"ordinal", "selector", "attempt_status", "missing", "record_hashes"}
        if set(item) - allowed or not required_summary <= set(item) or set(item.get("record_hashes", {})) != {"freeze", "admission", "authorization", "custody", "result", "receipt", "index"}:
            _fail("closure-attempts", f"attempt summary {index} is not closed")
        if item.get("selector") != EXPECTED_SELECTORS.get(item.get("ordinal")) or item.get("attempt_status") not in STATUSES | {None}:
            _fail("closure-attempts", f"attempt summary {index} has invalid slot/status")
        missing = item.get("missing")
        if type(missing) is not list or any(type(name) is not str for name in missing):
            _fail("closure-attempts", f"attempt summary {index} missing list is invalid")
        if not missing and (type(item.get("attempt_id")) is not str or not _valid_sha(item.get("semantic_sha256"))):
            _fail("closure-attempts", f"attempt summary {index} is incomplete despite empty missing list")
        if item.get("terminal_record_sha256") is not None and not _valid_sha(item.get("terminal_record_sha256")):
            _fail("closure-attempts", f"attempt summary {index} terminal record hash is invalid")
        if item.get("reservation_record_sha256") is not None and not _valid_sha(item.get("reservation_record_sha256")):
            _fail("closure-attempts", f"attempt summary {index} reservation record hash is invalid")
        for name, digest in item["record_hashes"].items():
            if digest is not None and not _valid_sha(digest):
                _fail("closure-attempts", f"attempt summary {index}.{name} hash is invalid")
        for field, name in (("result_sha256", "result"), ("receipt_sha256", "receipt"), ("index_sha256", "index")):
            if field in item and item[field] != item["record_hashes"][name]:
                _fail("closure-attempts", f"attempt summary {index}.{field} is not retained exactly")
    complete = [item for item in attempts if not item["missing"]]
    comparable = [item for item in complete if item.get("attempt_status") == "supported"]
    mismatch = len({item.get("semantic_sha256") for item in comparable}) > 1
    if comparison["semantic_equality"] is not (not mismatch):
        _fail("closure-status", "closure semantic equality declaration is inconsistent")
    if any(item["attempt_status"] == "failed" for item in attempts):
        expected_status, expected_reason = "failed", "attempt-failed"
    elif mismatch:
        expected_status, expected_reason = "failed", "semantic-output-mismatch"
    elif len(complete) != len(EXPECTED_ORDINALS) or any(item["attempt_status"] == "inconclusive" for item in attempts):
        expected_status, expected_reason = "inconclusive", "incomplete-attempt-closure"
    elif not all(item["attempt_status"] == "supported" for item in attempts):
        expected_status, expected_reason = "inconclusive", "attempt-status-not-supported"
    else:
        expected_status, expected_reason = "supported", None
    if value["status"] != expected_status or value["reason"] != expected_reason:
        _fail("closure-status", "closure status does not follow global failed/inconclusive precedence")
    return value


adjudicate_experiment = build_experiment_closure
close_experiment = build_experiment_closure
build_closure = build_experiment_closure


__all__ = ["SCHEMA", "HASH_DOMAIN", "EXPECTED_ORDINALS", "EXPECTED_SELECTORS", "ExperimentClosureError", "build_experiment_closure", "adjudicate_experiment", "close_experiment", "build_closure", "validate_experiment_closure"]

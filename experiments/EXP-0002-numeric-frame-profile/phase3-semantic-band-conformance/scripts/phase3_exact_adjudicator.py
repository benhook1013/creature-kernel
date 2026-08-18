"""Exact Phase 3 corpus preparation and response adjudication.

This module is the execution-boundary-free part of the future Phase 3
attempt.  It validates the materialized package through
``phase3_materialized_adapter``, retains the committed JSONL request bytes,
and substitutes only the frozen request-id token for one bounded attempt.
There is deliberately no candidate, process, socket, subprocess, or network
handle here.

The transport-facing view contains only ordered request IDs and bytes.  The
private case ledger retains recipe metadata (including held-out labels) and is
consulted only after response correlation, immediately before the independent
oracle and scorer are called.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import phase3_materialized_adapter as adapter
import phase3_oracle as oracle
import phase3_scorer as scorer
from phase3_common import (
    FRAME_BYTES,
    MAX_REQUEST_ID_BYTES,
    MAX_SOURCE_BYTES,
    Phase3Error,
    ProtocolError,
    parse_json,
    validate_response_frame,
)


EXACT_SCHEMA = "ck.exp-0002.phase3.exact-adjudication-inputs-1"
EVIDENCE_SCHEMA = "ck.exp-0002.phase3.evidence-proposed-1"
REQUEST_ID_FORMULA = "p3-{attempt_id}-{global_ordinal:03d}"
PLACEHOLDER_ATTEMPT_ID = "{attempt_id}"
EXPECTED_TOTAL_CASES = 60
EXPECTED_DISPATCHED_REQUESTS = 57
EXPECTED_PREFLIGHT_CASES = 3
# Correlation needs at most one extra record beyond the exact wire count to
# preserve duplicate/unknown/extra diagnostics, and must never materialize an
# arbitrary or non-terminating response iterable.
MAX_RESPONSE_ENTRIES = EXPECTED_DISPATCHED_REQUESTS + 1
ROLE_COUNTS = {"development": 8, "held-out": 40, "controls": 12}
ROLE_REQUEST_COUNTS = {"development": 8, "held-out": 40, "controls": 9}
PARTITION_PATHS = {
    "development": "corpora/development.jsonl",
    "held-out": "corpora/held-out.jsonl",
    "controls": "corpora/controls.jsonl",
}
PREREGISTRATION_PATH = "preregistration.json"
GENERATOR_PATH = "scripts/generate_phase3.py"
MAX_PACKAGE_PATH_BYTES = 512
MAX_ATTEMPT_ID_BYTES = 128
ATTEMPT_RE = re.compile(r"^attempt-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
REQUEST_KEYS = frozenset({
    "operation", "protocol_id", "providers", "request_id", "resource_profile",
    "source", "tolerances",
})
PREFLIGHT_REASON_TO_ORACLE_REASON = {
    "translation-component-domain": "canonical_translation_components",
    "path-edge-domain": "path_edges",
    "conditioning-domain": "translation_kappa_pair",
}


class ExactAdjudicatorError(Phase3Error):
    """A bounded, stable error from exact preparation or adjudication."""


def _fail(code: str, detail: str) -> None:
    raise ExactAdjudicatorError(code, detail)


def _expect(condition: bool, code: str, detail: str) -> None:
    if not condition:
        _fail(code, detail)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class _PackageSnapshot:
    """One secure, manifest-bound package byte snapshot."""

    files: Mapping[str, bytes]
    declarations: Mapping[str, Mapping[str, Any]]
    artifact_manifest: Mapping[str, Any]


def _bounded_text(value: Any, label: str, maximum: int) -> str:
    if type(value) is not str or not value:
        _fail("wrong-type", f"{label} must be a non-empty string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ExactAdjudicatorError("invalid-utf8", f"{label} is not UTF-8") from error
    _expect(size <= maximum, "resource-limit", f"{label} exceeds {maximum} UTF-8 bytes")
    return value


def derive_request_id(attempt_id: str, ordinal: int) -> str:
    """Return the preregistered per-attempt request ID for one ordinal."""
    attempt_id = _bounded_text(attempt_id, "attempt_id", MAX_ATTEMPT_ID_BYTES)
    _expect(ATTEMPT_RE.fullmatch(attempt_id) is not None, "attempt-id", "attempt_id violates the bounded attempt-ID form")
    _expect(type(ordinal) is int and not isinstance(ordinal, bool), "ordinal", "ordinal must be an integer")
    _expect(0 <= ordinal < EXPECTED_TOTAL_CASES, "ordinal", "ordinal is outside the exact 000..059 corpus")
    result = f"p3-{attempt_id}-{ordinal:03d}"
    _expect(len(result.encode("utf-8")) <= MAX_REQUEST_ID_BYTES, "request-id", "derived request ID exceeds 256 UTF-8 bytes")
    return result


def placeholder_request_id(ordinal: int) -> str:
    """Return the exact frozen request-id token in a materialized JSONL row."""
    _expect(type(ordinal) is int and 0 <= ordinal < EXPECTED_TOTAL_CASES, "ordinal", "ordinal is outside the exact corpus")
    return f"p3-{PLACEHOLDER_ATTEMPT_ID}-{ordinal:03d}"


@dataclass(frozen=True)
class ByteSubstitutionProof:
    """Proof that a request changed only its frozen request-id token."""

    ordinal: int
    placeholder: bytes
    replacement: bytes
    original_sha256: str
    prepared_sha256: str
    original_bytes: int
    prepared_bytes: int
    original_changed_start: int
    original_changed_end: int
    prepared_changed_start: int
    prepared_changed_end: int
    changed_byte_count: int

    @property
    def only_request_id_changed(self) -> bool:
        # The fixed ``p3-`` prefix and ``-NNN`` ordinal suffix are shared by
        # both IDs.  The actual byte delta is the bounded attempt token inside
        # that frozen request-id field.
        old_token = self.placeholder[len(b"p3-"):-len(b"-000")]
        new_token = self.replacement[len(b"p3-"):-len(b"-000")]
        return (
            self.changed_byte_count == len(old_token) + len(new_token)
            and self.original_changed_end - self.original_changed_start == len(old_token)
            and self.prepared_changed_end - self.prepared_changed_start == len(new_token)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "placeholder_sha256": _sha256(self.placeholder),
            "replacement_sha256": _sha256(self.replacement),
            "original_sha256": self.original_sha256,
            "prepared_sha256": self.prepared_sha256,
            "original_bytes": self.original_bytes,
            "prepared_bytes": self.prepared_bytes,
            "original_changed_start": self.original_changed_start,
            "original_changed_end": self.original_changed_end,
            "prepared_changed_start": self.prepared_changed_start,
            "prepared_changed_end": self.prepared_changed_end,
            "changed_byte_count": self.changed_byte_count,
            "only_request_id_changed": self.only_request_id_changed,
        }


def substitute_request_id(raw: bytes, *, attempt_id: str, ordinal: int) -> tuple[bytes, ByteSubstitutionProof]:
    """Substitute the one frozen ID token without parsing or reserializing.

    The returned proof compares common prefix/suffix bytes and verifies that
    the changed old/new spans are exactly the placeholder and derived ID.  A
    repeated/missing token is rejected instead of guessing which occurrence
    is the request ID.
    """
    _expect(type(raw) is bytes, "request-bytes", "request bytes must be bytes")
    _expect(0 < len(raw) <= FRAME_BYTES, "frame-size", f"request frame is empty or exceeds {FRAME_BYTES} bytes")
    old = placeholder_request_id(ordinal).encode("ascii")
    new = derive_request_id(attempt_id, ordinal).encode("ascii")
    _expect(raw.count(old) == 1, "request-id-token", "request does not contain exactly one frozen request-id token")
    start = raw.index(old)
    prepared = raw[:start] + new + raw[start + len(old):]
    _expect(len(prepared) <= FRAME_BYTES, "frame-size", f"prepared request exceeds {FRAME_BYTES} bytes")

    prefix = 0
    while prefix < len(raw) and prefix < len(prepared) and raw[prefix] == prepared[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(raw) - prefix
        and suffix < len(prepared) - prefix
        and raw[len(raw) - 1 - suffix] == prepared[len(prepared) - 1 - suffix]
    ):
        suffix += 1
    old_end = len(raw) - suffix
    new_end = len(prepared) - suffix
    old_token = old[len(b"p3-"):-len(b"-000")]
    new_token = new[len(b"p3-"):-len(b"-000")]
    _expect(raw[prefix:old_end] == old_token, "request-byte-drift", "original changed span is not the frozen request-id attempt token")
    _expect(prepared[prefix:new_end] == new_token, "request-byte-drift", "prepared changed span is not the derived request-id attempt token")
    _expect(raw[:prefix] == prepared[:prefix] and raw[old_end:] == prepared[new_end:], "request-byte-drift", "bytes outside request ID changed")
    proof = ByteSubstitutionProof(
        ordinal=ordinal,
        placeholder=old,
        replacement=new,
        original_sha256=_sha256(raw),
        prepared_sha256=_sha256(prepared),
        original_bytes=len(raw),
        prepared_bytes=len(prepared),
        original_changed_start=prefix,
        original_changed_end=old_end,
        prepared_changed_start=prefix,
        prepared_changed_end=new_end,
        changed_byte_count=(old_end - prefix) + (new_end - prefix),
    )
    _expect(proof.only_request_id_changed, "request-byte-drift", "byte-level request-id substitution proof failed")
    return prepared, proof


@dataclass(frozen=True)
class TransportRequest:
    """One transport-visible request; no recipe or expected-label fields."""

    ordinal: int
    request_id: str
    request_bytes: bytes
    request_sha256: str
    substitution: ByteSubstitutionProof

    @property
    def wire_bytes(self) -> bytes:
        return self.request_bytes

    @property
    def raw_bytes(self) -> bytes:
        return self.request_bytes

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "request_id": self.request_id,
            "request_bytes": self.request_bytes,
            "request_sha256": self.request_sha256,
        }


@dataclass(frozen=True)
class TransportCohort:
    """Ordered wire requests for one candidate process."""

    role: str
    requests: tuple[TransportRequest, ...]

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(item.request_id for item in self.requests)

    @property
    def request_bytes(self) -> tuple[bytes, ...]:
        return tuple(item.request_bytes for item in self.requests)


@dataclass(frozen=True)
class _CasePlan:
    """Private post-response ledger; never exposed through transport views."""

    ordinal: int
    role: str
    case_id: str
    metric: str
    dispatch_to_candidate: bool
    observation_only: bool
    expected_class: str | None
    expected_response_status: str | None
    expected_cause: Mapping[str, Any] | None
    recipe_expectation: str | Mapping[str, Any] | None
    typed_expectation: Mapping[str, Any] | None
    source: str
    request_object: Mapping[str, Any]
    request_template: bytes
    transport_request: TransportRequest | None
    domain_expectation: str


@dataclass(frozen=True)
class PreparedAttempt:
    """Prepared exact inputs and private post-response ledger."""

    attempt_id: str
    package_root: str
    cohorts: tuple[TransportCohort, ...]
    _cases: tuple[_CasePlan, ...]

    @property
    def total_cases(self) -> int:
        return len(self._cases)

    @property
    def dispatched_count(self) -> int:
        return sum(case.dispatch_to_candidate for case in self._cases)

    @property
    def preflight_count(self) -> int:
        return sum(not case.dispatch_to_candidate for case in self._cases)

    @property
    def transport(self) -> tuple[TransportCohort, ...]:
        """Return the only view intended for a future transport wrapper."""
        return self.cohorts

    @property
    def request_bytes(self) -> tuple[bytes, ...]:
        return tuple(item.request_bytes for cohort in self.cohorts for item in cohort.requests)

    @property
    def request_ids(self) -> tuple[str, ...]:
        return tuple(item.request_id for cohort in self.cohorts for item in cohort.requests)

    def substitution_proofs(self) -> tuple[ByteSubstitutionProof, ...]:
        return tuple(item.substitution for cohort in self.cohorts for item in cohort.requests)


@dataclass(frozen=True)
class ResponseRecord:
    request_id: str
    response_bytes: bytes


@dataclass(frozen=True)
class CaseAdjudication:
    """Typed per-case post-response adjudication."""

    ordinal: int
    request_id: str
    role: str
    dispatch_to_candidate: bool
    status: str
    classification: str
    oracle_result: Mapping[str, Any] | None
    scorer_result: Mapping[str, Any] | None
    request_bytes: bytes | None
    response_bytes: bytes | None
    cause: Mapping[str, Any] | None
    evidence: Mapping[str, Any]

    def as_evidence_contract_adjudication(self, attempt_id: str) -> dict[str, Any]:
        """Return the closed adjudication shape consumed by evidence_contract."""
        _expect(self.request_id == derive_request_id(attempt_id, self.ordinal), "request-id", "adjudication attempt ID differs")
        evidence = dict(self.evidence)
        evidence_raw = _canonical_evidence(evidence)
        return {
            "ordinal": self.ordinal,
            "request_id": self.request_id,
            "role": self.role,
            "dispatch_to_candidate": self.dispatch_to_candidate,
            "status": self.status,
            "classification": self.classification,
            "evidence": evidence,
            "evidence_sha256": _sha256(evidence_raw),
        }


@dataclass(frozen=True)
class AdjudicationRun:
    """Ordered typed adjudications plus evidence-contract aggregate inputs."""

    prepared: PreparedAttempt
    adjudications: tuple[CaseAdjudication, ...]
    status: str
    counts: Mapping[str, int]

    def evidence_contract_inputs(self) -> dict[str, Any]:
        return {
            "adjudications": [item.as_evidence_contract_adjudication(self.prepared.attempt_id) for item in self.adjudications],
            "counts": dict(self.counts),
        }

    def build_result_inputs(
        self,
        attempt: Mapping[str, Any],
        process_observations: Sequence[Mapping[str, Any]],
        *,
        tool_identities: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Return arguments suitable for ``phase3_evidence_contract.build_result``."""
        return {
            # Attempt identity/authorization is deliberately caller-owned;
            # preparation never invents an authorization or freeze binding.
            "attempt": dict(attempt),
            "adjudications": self.evidence_contract_inputs()["adjudications"],
            "process_observations": list(process_observations),
            "tool_identities": list(tool_identities),
        }


def _canonical_evidence(value: Mapping[str, Any]) -> bytes:
    try:
        raw = (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ExactAdjudicatorError("evidence-json", "evidence cannot be encoded as strict JSON") from error
    _expect(len(raw) <= 512 * 1024, "resource-limit", "evidence exceeds the bounded evidence limit")
    return raw


def _b64_frame(raw: bytes) -> dict[str, str]:
    _expect(type(raw) is bytes and 0 < len(raw) <= FRAME_BYTES, "frame-size", "wire frame is empty or oversized")
    return {"bytes_b64": base64.b64encode(raw).decode("ascii"), "sha256": _sha256(raw)}


def _strict_recipe(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ExactAdjudicatorError("recipe-read", "recipe manifest snapshot cannot be parsed") from error
    _expect(type(value) is dict and type(value.get("cases")) is list and len(value["cases"]) == EXPECTED_TOTAL_CASES, "recipe-count", "recipe manifest does not contain exactly 60 cases")
    return value


def _raw_partition_lines(raw: bytes, role: str) -> list[bytes]:
    relative = PARTITION_PATHS[role]
    _expect(len(raw) <= adapter.MAX_PARTITION_BYTES, "resource-limit", f"{relative} exceeds the partition bound")
    _expect(raw.endswith(b"\n"), "line-ending", f"{relative} is not LF terminated")
    lines = raw.split(b"\n")
    if raw.endswith(b"\n"):
        lines.pop()
    _expect(len(lines) == ROLE_COUNTS[role], "partition-count", f"{relative} count differs from the exact cohort")
    for index, line in enumerate(lines):
        _expect(bool(line), "blank-line", f"{relative} line {index + 1} is blank")
        _expect(not line.endswith(b"\r"), "line-ending", f"{relative} line {index + 1} is not LF terminated")
        _expect(len(line) + 1 <= FRAME_BYTES, "frame-size", f"{relative} line {index + 1} exceeds {FRAME_BYTES} bytes")
    return [line + b"\n" for line in lines]


def _secure_snapshot(root: Path, baseline: _PackageSnapshot | None = None) -> _PackageSnapshot:
    """Read package bytes through adapter's bounded descriptor path.

    The first call establishes the preregistration/artifact identities.  A
    later call is checked against that exact byte snapshot and those original
    declarations, so a mutation after adapter validation cannot silently
    replace a request field or recipe label.
    """
    try:
        adapter._check_layout(root)
        prereg_raw = adapter._regular_bytes(root / PREREGISTRATION_PATH, PREREGISTRATION_PATH, adapter.MAX_PREREG_BYTES)
        if baseline is not None:
            _expect(prereg_raw == baseline.files[PREREGISTRATION_PATH], "package-race", "preregistration changed between secure reads")
            declarations = baseline.declarations
        else:
            declarations = adapter._validate_preregistration(prereg_raw)
        generator = adapter._read_and_validate_generator(root, declarations[GENERATOR_PATH])
        artifact_manifest, artifact_raw = adapter._read_and_validate_artifacts(root, declarations)
    except (adapter.MaterializedAdapterError, Phase3Error, OSError, TypeError, ValueError) as error:
        raise ExactAdjudicatorError("package-snapshot", getattr(error, "code", "package snapshot is invalid")) from error
    files = {
        PREREGISTRATION_PATH: prereg_raw,
        GENERATOR_PATH: generator,
        **artifact_raw,
    }
    if baseline is not None:
        _expect(set(files) == set(baseline.files), "package-race", "package snapshot file set changed")
        for path, raw in files.items():
            _expect(raw == baseline.files[path], "package-race", f"{path} changed after adapter validation")
        _expect(artifact_manifest == baseline.artifact_manifest, "package-race", "artifact manifest changed after adapter validation")
    return _PackageSnapshot(files, declarations, artifact_manifest)


def _request_object(raw: bytes, ordinal: int, expected_id: str) -> dict[str, Any]:
    try:
        value = parse_json(raw, label=f"request[{ordinal}]")
    except (ProtocolError, Phase3Error) as error:
        raise ExactAdjudicatorError("request-json", f"request[{ordinal}] is malformed") from error
    _expect(type(value) is dict and set(value) == REQUEST_KEYS, "request-shape", f"request[{ordinal}] violates the seven-field wire contract")
    _expect(value.get("request_id") == expected_id, "request-id", f"request[{ordinal}] ID differs from derived attempt ID")
    _expect(type(value.get("source")) is str and len(value["source"].encode("utf-8")) <= MAX_SOURCE_BYTES, "source", f"request[{ordinal}] source is invalid")
    return value


def prepare_exact_attempt(package_root: str | Path, attempt_id: str) -> PreparedAttempt:
    """Validate a package and prepare its exact ordered 57-request wire set."""
    attempt_id = _bounded_text(attempt_id, "attempt_id", MAX_ATTEMPT_ID_BYTES)
    _expect(ATTEMPT_RE.fullmatch(attempt_id) is not None, "attempt-id", "attempt_id violates the bounded attempt-ID form")
    root = Path(package_root)
    try:
        root = Path(adapter._absolute_path(root))
    except (TypeError, ValueError, OSError) as error:
        raise ExactAdjudicatorError("package-path", "package root is invalid") from error
    _expect(len(str(root).encode("utf-8")) <= MAX_PACKAGE_PATH_BYTES, "resource-limit", "package root path is oversized")

    # Establish one secure, manifest-bound snapshot before validation.  The
    # existing adapter remains the canonical semantic/package validator; the
    # second snapshot below closes the read-after-validation race.
    try:
        initial_snapshot = _secure_snapshot(root)
        opaque_cases = adapter.load_materialized_cases(root)
    except ExactAdjudicatorError:
        raise
    except (adapter.MaterializedAdapterError, Phase3Error) as error:
        raise ExactAdjudicatorError("package-validation", getattr(error, "code", "invalid-package")) from error
    final_snapshot = _secure_snapshot(root, initial_snapshot)
    _expect(len(opaque_cases) == EXPECTED_TOTAL_CASES, "package-count", "validated package does not contain 60 cases")
    recipe = _strict_recipe(final_snapshot.files["manifests/recipe-manifest.json"])

    case_plans: list[_CasePlan] = []
    cohorts: list[TransportCohort] = []
    offset = 0
    for role in ("development", "held-out", "controls"):
        raw_lines = _raw_partition_lines(final_snapshot.files[PARTITION_PATHS[role]], role)
        transport: list[TransportRequest] = []
        for line_index, raw_template in enumerate(raw_lines):
            ordinal = offset + line_index
            recipe_case = recipe["cases"][ordinal]
            expected_id = derive_request_id(attempt_id, ordinal)
            prepared_raw, proof = substitute_request_id(raw_template, attempt_id=attempt_id, ordinal=ordinal)
            request_object = _request_object(prepared_raw, ordinal, expected_id)
            opaque = opaque_cases[ordinal]
            _expect(request_object["source"] == opaque["source"], "request-source", f"request[{ordinal}] differs from validated adapter source")
            _expect(recipe_case["metric"] in {"translation", "rotation"}, "metric", f"recipe case {ordinal} metric is invalid")
            dispatch = bool(recipe_case["dispatch_to_candidate"])
            request = TransportRequest(ordinal, expected_id, prepared_raw, _sha256(prepared_raw), proof) if dispatch else None
            if request is not None:
                transport.append(request)
            expected_class = recipe_case["expected_class"] if role == "held-out" else None
            typed = recipe_case.get("typed_expectation")
            typed_metadata = typed if type(typed) is dict else None
            if typed is not None and typed_metadata is None:
                _expect(type(typed) is str, "typed-expectation", f"recipe case {ordinal} typed expectation is not a bounded label")
                _expect(len(typed.encode("utf-8")) <= 256, "typed-expectation", f"recipe case {ordinal} typed expectation label is oversized")
            if ordinal in range(52, 56) or ordinal == 59:
                _expect(typed_metadata is not None, "typed-expectation", f"recipe case {ordinal} typed expectation is missing")
            if typed_metadata is not None:
                if ordinal in range(52, 56):
                    _expect(set(typed_metadata) == {"cause", "classification", "status"}, "typed-expectation", f"recipe case {ordinal} typed expectation is not closed")
                    _expect(typed_metadata["status"] == "observed" and typed_metadata["classification"] == "skipped", "typed-expectation", f"recipe case {ordinal} typed expectation differs")
                elif ordinal in range(56, 59):
                    _expect(set(typed_metadata) == {"reason", "status"}, "typed-expectation", f"recipe case {ordinal} preflight expectation is not closed")
                    _expect(typed_metadata["status"] == "out-of-domain", "typed-expectation", f"recipe case {ordinal} preflight expectation differs")
                elif ordinal == 59:
                    _expect(set(typed_metadata) == {"cause", "error", "status"}, "typed-expectation", "negative-relative typed expectation is not closed")
                    _expect(typed_metadata["status"] == "rejected", "typed-expectation", "negative-relative typed expectation differs")
                else:
                    _fail("typed-expectation", f"unexpected typed expectation at recipe case {ordinal}")
            expected_status = typed_metadata.get("status") if ordinal == 59 and typed_metadata is not None else None
            expected_cause = typed_metadata.get("cause") if ordinal == 59 and typed_metadata is not None else None
            case_plans.append(_CasePlan(
                ordinal=ordinal,
                role=role,
                case_id=recipe_case["case_id"],
                metric=recipe_case["metric"],
                dispatch_to_candidate=dispatch,
                observation_only=ordinal < 8 or ordinal >= 48,
                expected_class=expected_class,
                expected_response_status=expected_status,
                expected_cause=expected_cause,
                recipe_expectation=typed,
                typed_expectation=None if typed_metadata is None else dict(typed_metadata),
                source=request_object["source"],
                request_object=request_object,
                request_template=raw_template,
                transport_request=request,
                domain_expectation=recipe_case["domain_expectation"],
            ))
        cohorts.append(TransportCohort(role, tuple(transport)))
        offset += len(raw_lines)

    _expect(len(case_plans) == EXPECTED_TOTAL_CASES, "case-count", "prepared case count differs from 60")
    _expect(sum(case.dispatch_to_candidate for case in case_plans) == EXPECTED_DISPATCHED_REQUESTS, "dispatch-count", "prepared dispatch count differs from 57")
    _expect(sum(not case.dispatch_to_candidate for case in case_plans) == EXPECTED_PREFLIGHT_CASES, "preflight-count", "prepared preflight count differs from 3")
    _expect([cohort.role for cohort in cohorts] == ["development", "held-out", "controls"], "cohort-order", "cohort order drifted")
    _expect([len(cohort.requests) for cohort in cohorts] == [8, 40, 9], "cohort-count", "wire cohort counts differ from 8/40/9")
    return PreparedAttempt(str(attempt_id), str(root), tuple(cohorts), tuple(case_plans))


def load_exact_corpus(package_root: str | Path, attempt_id: str = "attempt-001") -> PreparedAttempt:
    """Compatibility alias emphasizing that preparation is read-only."""
    return prepare_exact_attempt(package_root, attempt_id)


def _response_entries(responses: Any) -> list[ResponseRecord]:
    if responses is None:
        return []
    if isinstance(responses, Mapping):
        try:
            iterator = iter(responses)
        except (TypeError, ValueError, RuntimeError) as error:
            raise ExactAdjudicatorError("response-shape", "responses mapping cannot be enumerated") from error

        def mapping_entries() -> Any:
            for request_id in iterator:
                yield request_id, responses[request_id]

        source = mapping_entries()
    elif isinstance(responses, (str, bytes, bytearray)):
        _fail("response-shape", "responses must be an ordered collection, not one frame")
    else:
        try:
            source = iter(responses)
        except (TypeError, ValueError, RuntimeError) as error:
            raise ExactAdjudicatorError("response-shape", "responses cannot be enumerated") from error
    entries: list[Any] = []
    for _ in range(MAX_RESPONSE_ENTRIES):
        try:
            entries.append(next(source))
        except StopIteration:
            break
        except (TypeError, ValueError, RuntimeError) as error:
            raise ExactAdjudicatorError("response-shape", "responses cannot be enumerated") from error
    result: list[ResponseRecord] = []
    for index, item in enumerate(entries):
        if isinstance(item, ResponseRecord):
            result.append(item)
            continue
        if isinstance(item, tuple) and len(item) == 2:
            request_id, raw = item
            _bounded_text(request_id, f"response[{index}].request_id", MAX_REQUEST_ID_BYTES)
            _expect(type(raw) is bytes, "response-shape", f"response[{index}] bytes are not bytes")
            result.append(ResponseRecord(request_id, raw))
            continue
        if type(item) is bytes:
            try:
                parsed = parse_json(item, label=f"response[{index}]")
            except (ProtocolError, Phase3Error) as error:
                raise ExactAdjudicatorError("response-malformed", f"response[{index}] is malformed") from error
            _expect(type(parsed) is dict and type(parsed.get("request_id")) is str, "response-malformed", f"response[{index}] has no response request ID")
            result.append(ResponseRecord(parsed["request_id"], item))
            continue
        _fail("response-shape", f"response[{index}] is not a response record")
    return result


def correlate_responses(prepared: PreparedAttempt, responses: Any, *, allow_incomplete: bool = False) -> tuple[dict[int, bytes | None], dict[int, str]]:
    """Correlate exactly one response per dispatched request.

    Returns ordinal-keyed response bytes and ordinal-keyed missing reasons.
    Unknown, duplicate, malformed, extra, and order-drift records always fail.
    Missing records fail by default; ``allow_incomplete=True`` retains them as
    explicit incomplete observations for evidence construction.
    """
    records = _response_entries(responses)
    expected = [item for cohort in prepared.cohorts for item in cohort.requests]
    expected_by_id = {item.request_id: item for item in expected}
    seen: set[str] = set()
    observed: dict[int, bytes | None] = {}
    observed_ordinals: list[int] = []
    for index, record in enumerate(records):
        request_id = record.request_id
        if request_id not in expected_by_id:
            _fail("response-unknown-id", f"response[{index}] has an unknown or preflight request ID")
        if request_id in seen:
            _fail("response-duplicate-id", f"response[{index}] duplicates {request_id}")
        seen.add(request_id)
        expected_request = expected_by_id[request_id]
        _expect(type(record.response_bytes) is bytes, "response-shape", f"response[{index}] bytes are not bytes")
        _expect(0 < len(record.response_bytes) <= FRAME_BYTES, "response-size", f"response[{index}] is empty or oversized")
        try:
            validate_response_frame(record.response_bytes, request_id)
        except (ProtocolError, Phase3Error) as error:
            raise ExactAdjudicatorError("response-malformed", f"response[{index}] failed protocol validation") from error
        observed[expected_request.ordinal] = record.response_bytes
        observed_ordinals.append(expected_request.ordinal)
    expected_ordinals = [item.ordinal for item in expected]
    if observed_ordinals != sorted(observed_ordinals):
        _fail("response-order", "response records are not in the fixed global dispatch order")
    missing = [item.ordinal for item in expected if item.request_id not in seen]
    if missing and not allow_incomplete:
        _fail("response-missing", f"missing responses for {len(missing)} dispatched requests")
    missing_reasons = {ordinal: "missing-response" for ordinal in missing}
    for ordinal in expected_ordinals:
        observed.setdefault(ordinal, None)
    return observed, missing_reasons


def _scorer_request(case: _CasePlan) -> dict[str, Any]:
    value = dict(case.request_object)
    value["metric"] = case.metric
    if case.expected_response_status is not None:
        value["expected_response_status"] = case.expected_response_status
        value["expected_cause"] = dict(case.expected_cause or {})
    return value


def _validate_typed_success(case: _CasePlan, response_raw: bytes, score: Mapping[str, Any]) -> None:
    """Check recipe typed metadata on already-successful scorer output.

    The scorer remains the owner of zero-quaternion and top-level rejection
    semantics.  This is a narrow postcondition check over the recipe's typed
    expectation, so a completed contradictory response remains the scorer's
    existing ``failed`` result while incomplete evidence remains
    ``inconclusive``.
    """
    typed = case.typed_expectation
    if typed is None or score.get("status") not in {"supported", "observation"}:
        return
    try:
        response = parse_json(response_raw, label=f"typed response[{case.ordinal}]")
    except (ProtocolError, Phase3Error) as error:
        raise ExactAdjudicatorError("typed-response", f"typed response[{case.ordinal}] cannot be parsed") from error
    _expect(type(response) is dict, "typed-response", f"typed response[{case.ordinal}] is not an object")
    _expect(response.get("status") == typed["status"], "typed-expectation", f"typed response[{case.ordinal}] status contradicts the recipe")
    expected_class = typed.get("classification")
    if expected_class is not None:
        _expect(score.get("classification") == expected_class, "typed-expectation", f"typed response[{case.ordinal}] classification contradicts the recipe")
    expected_cause = typed.get("cause")
    if expected_cause is not None:
        _expect(score.get("cause") == expected_cause, "typed-expectation", f"typed response[{case.ordinal}] cause contradicts the recipe")


def _evidence_for(case: _CasePlan, status: str, classification: str, oracle_result: Mapping[str, Any] | None, score: Mapping[str, Any] | None, request_raw: bytes | None, response_raw: bytes | None, cause: Mapping[str, Any] | None, *, incomplete: bool = False) -> dict[str, Any]:
    context = {
        "metric": case.metric,
        "observation_only": case.observation_only,
        "expected_class": case.expected_class,
        "expected_response_status": case.expected_response_status,
        "expected_cause": None if case.expected_cause is None else dict(case.expected_cause),
    }
    if not case.dispatch_to_candidate:
        if incomplete:
            payload = {
                "variant": "runner-preflight-incomplete-v1",
                "reason": "oracle-incomplete",
                "cause": {"code": "oracle-incomplete", "detail": str((cause or {}).get("detail", "oracle unavailable"))[:256]},
            }
        else:
            domain = (oracle_result or {}).get("domain", {})
            payload = {
                "variant": "runner-preflight-v1",
                "runner": {"reason": str(domain.get("reason") or "out-of-domain"), "domain_status": str((oracle_result or {}).get("status", "out-of-domain"))},
                "classification": classification,
                "cause": None if cause is None else {"code": str(cause.get("code", "preflight")), "detail": str(cause.get("detail", ""))[:512]},
            }
        return {"schema": EVIDENCE_SCHEMA, "payload": payload}
    request_wrapper = None if request_raw is None else _b64_frame(request_raw)
    if incomplete:
        payload = {
            "variant": "dispatched-incomplete-v1",
            "request": request_wrapper,
            "response": None if response_raw is None else _b64_frame(response_raw),
            "scorer_context": context,
            "reason": "missing-response" if response_raw is None else "incomplete-adjudication",
            "cause": {"code": str((cause or {}).get("code", "incomplete")), "detail": str((cause or {}).get("detail", "response evidence incomplete"))[:512]},
        }
    else:
        _expect(request_wrapper is not None and response_raw is not None and oracle_result is not None and score is not None, "evidence-input", "complete dispatched evidence is missing a required value")
        payload = {
            "variant": "dispatched-candidate-v1",
            "response": _b64_frame(response_raw),
            "request": request_wrapper,
            "scorer_context": context,
            "oracle_result": oracle_result,
            "scorer_result": score,
        }
    return {"schema": EVIDENCE_SCHEMA, "payload": payload}


def adjudicate_exact(prepared: PreparedAttempt, responses: Any = None, *, allow_incomplete: bool = False) -> AdjudicationRun:
    """Correlate and adjudicate one exact prepared attempt.

    Held-out labels are read from the private case ledger only after response
    correlation, then passed to the independent exact oracle/scorer.  No
    candidate-visible request is parsed and reserialized during preparation.
    """
    if type(prepared) is not PreparedAttempt:
        _fail("prepared-input", "adjudicate_exact requires a PreparedAttempt")
    correlated, missing = correlate_responses(prepared, responses, allow_incomplete=allow_incomplete)
    output: list[CaseAdjudication] = []
    for case in prepared._cases:
        request_raw = case.transport_request.request_bytes if case.transport_request is not None else None
        response_raw = correlated.get(case.ordinal)
        if not case.dispatch_to_candidate:
            try:
                truth = oracle.evaluate_source(case.source, case.metric)
                classification = "out-of-domain" if truth.get("status") == "out-of-domain" else "incomplete"
                # Preflight is an observation-only runner adjudication.  It
                # must not elevate a non-dispatched control to candidate
                # support (the evidence contract reserves ``supported`` for
                # held-out candidate results).
                status = "observation" if classification == "out-of-domain" else "inconclusive"
                cause = None if classification == "out-of-domain" else {"code": "preflight-domain", "detail": "runner preflight did not admit this case"}
                typed = case.typed_expectation
                expected_reason = PREFLIGHT_REASON_TO_ORACLE_REASON.get(str(typed.get("reason"))) if typed is not None else None
                if typed is not None and (truth.get("status") != typed.get("status") or truth.get("domain", {}).get("reason") != expected_reason):
                    status = "failed"
                    cause = {"code": "typed-control-mismatch", "detail": "runner preflight differs from typed expectation"}
                evidence = _evidence_for(case, status, classification, truth, None, None, None, cause)
                output.append(CaseAdjudication(case.ordinal, derive_request_id(prepared.attempt_id, case.ordinal), case.role, False, status, classification, truth, None, None, None, cause, evidence))
            except (oracle.OracleError, Phase3Error, TypeError, ValueError) as error:
                cause = {"code": "oracle-incomplete", "detail": str(error)[:256]}
                evidence = _evidence_for(case, "inconclusive", "out-of-domain", None, None, None, None, cause, incomplete=True)
                output.append(CaseAdjudication(case.ordinal, derive_request_id(prepared.attempt_id, case.ordinal), case.role, False, "inconclusive", "out-of-domain", None, None, None, None, cause, evidence))
            continue
        if response_raw is None:
            cause = {"code": missing.get(case.ordinal, "missing-response"), "detail": "one dispatched response was not retained"}
            evidence = _evidence_for(case, "inconclusive", "incomplete", None, None, request_raw, None, cause, incomplete=True)
            output.append(CaseAdjudication(case.ordinal, derive_request_id(prepared.attempt_id, case.ordinal), case.role, True, "inconclusive", "incomplete", None, None, request_raw, None, cause, evidence))
            continue
        try:
            truth = oracle.evaluate_source(case.source, case.metric)
        except (oracle.OracleError, Phase3Error, TypeError, ValueError) as error:
            cause = {"code": "oracle-incomplete", "detail": str(error)[:256]}
            evidence = _evidence_for(case, "inconclusive", "incomplete", None, None, request_raw, response_raw, cause, incomplete=True)
            output.append(CaseAdjudication(case.ordinal, derive_request_id(prepared.attempt_id, case.ordinal), case.role, True, "inconclusive", "incomplete", None, None, request_raw, response_raw, cause, evidence))
            continue
        score = scorer.score_response(
            _scorer_request(case), truth, response_raw,
            expected_class=case.expected_class,
            observation_only=case.observation_only,
        )
        _validate_typed_success(case, response_raw, score)
        status = str(score.get("status", "inconclusive"))
        classification = str(score.get("classification", "incomplete"))
        cause_value = score.get("cause") if isinstance(score.get("cause"), Mapping) else None
        evidence = _evidence_for(case, status, classification, truth, score, request_raw, response_raw, cause_value, incomplete=False)
        output.append(CaseAdjudication(case.ordinal, derive_request_id(prepared.attempt_id, case.ordinal), case.role, True, status, classification, truth, score, request_raw, response_raw, cause_value, evidence))

    _expect(len(output) == EXPECTED_TOTAL_CASES, "adjudication-count", "adjudication output does not contain 60 cases")
    counts = {
        "cases": len(output),
        "development": sum(item.role == "development" for item in output),
        "held-out": sum(item.role == "held-out" for item in output),
        "controls": sum(item.role == "controls" for item in output),
        "dispatched": sum(item.dispatch_to_candidate for item in output),
        "preflight": sum(not item.dispatch_to_candidate for item in output),
        "supported": sum(item.status == "supported" for item in output),
        "failed": sum(item.status == "failed" for item in output),
        "inconclusive": sum(item.status == "inconclusive" for item in output),
        "observation": sum(item.status == "observation" for item in output),
    }
    status = "failed" if counts["failed"] else "inconclusive" if counts["inconclusive"] else "supported" if all(item.status == "supported" for item in output[8:48]) else "inconclusive"
    return AdjudicationRun(prepared, tuple(output), status, counts)


def adjudicate(prepared: PreparedAttempt, responses: Any = None, *, allow_incomplete: bool = False) -> AdjudicationRun:
    return adjudicate_exact(prepared, responses, allow_incomplete=allow_incomplete)


prepare = prepare_exact_attempt
prepare_exact_requests = prepare_exact_attempt
adjudicate_attempt = adjudicate_exact
substitute_request_bytes = substitute_request_id


__all__ = [
    "EXACT_SCHEMA", "REQUEST_ID_FORMULA", "EXPECTED_TOTAL_CASES", "EXPECTED_DISPATCHED_REQUESTS", "EXPECTED_PREFLIGHT_CASES",
    "ROLE_COUNTS", "ROLE_REQUEST_COUNTS", "ExactAdjudicatorError", "ByteSubstitutionProof", "TransportRequest", "TransportCohort",
    "PreparedAttempt", "ResponseRecord", "CaseAdjudication", "AdjudicationRun", "derive_request_id", "placeholder_request_id",
    "substitute_request_id", "substitute_request_bytes", "prepare_exact_attempt", "prepare", "prepare_exact_requests", "load_exact_corpus",
    "correlate_responses", "adjudicate_exact", "adjudicate_attempt", "adjudicate",
]

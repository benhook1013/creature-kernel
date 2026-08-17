"""Shared bounded JSON, bit-string, and protocol helpers for EXP-0002."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Mapping

FRAME_BYTES = 16_384
MAX_WIRE_REQUEST_ID_BYTES = 256
MAX_CASES_PER_CORPUS = 128
MAX_TOTAL_CASES = 256
MAX_RELATIONS = 256
EVALUATION_BINDING = "ck.exp-0002.phase1-persistent-conformance-v1"
TECHNOLOGY_RESULT = "none"
PROTOCOL_ID = "ck.r3.numeric-candidate-request-1"
RESPONSE_PROTOCOL_ID = "ck.r3.numeric-candidate-response-1"
ROLES = ("development", "held-out", "adversarial")
PREREGISTERED_LIMITS = {
    "frame_bytes": FRAME_BYTES,
    "wire_request_id_bytes": MAX_WIRE_REQUEST_ID_BYTES,
    "stdout_total_bytes": 64 * 1024,
    "stderr_total_bytes": 64 * 1024,
    "io_deadline_seconds": 2.0,
    "shutdown_deadline_seconds": 2.0,
    "trailing_output_quiet_seconds": 0.02,
    "max_cases_per_corpus": MAX_CASES_PER_CORPUS,
    "max_total_cases": MAX_TOTAL_CASES,
    "max_relations": MAX_RELATIONS,
    "max_oracle_decimal_digits": 4096,
    "max_identity_artifact_bytes": 268_435_456,
}
OPERATIONS = {
    "decimal-admission",
    "scalar-comparison",
    "translation-comparison",
    "environment-attestation",
}
OPERATION_FIELDS = {
    "decimal-admission": {
        "token",
        "max_token_bytes",
        "max_significant_digits",
        "max_exponent_abs",
    },
    "scalar-comparison": {
        "absolute_bits",
        "relative_bits",
        "left_bits",
        "right_bits",
    },
    "translation-comparison": {
        "absolute_bits",
        "relative_bits",
        "left_bits",
        "right_bits",
    },
    "environment-attestation": set(),
}
REQUEST_FIELDS = {"protocol_id", "request_id", "operation", "input"}
RESPONSE_FIELDS = {"protocol_id", "request_id", "status", "observations", "error"}
EXPECTED_FIELDS = {"status", "observations", "error_code", "request_id"}
CASE_REQUIRED_FIELDS = {"case_id", "family", "operation", "expected", "relations"}
RESULT_STATUSES = {"observed", "rejected", "resource-limit", "unsupported", "error"}
CASE_CLASSIFICATIONS = {"pass", "fail", "inconclusive", "unsupported", "incomplete"}
FORBIDDEN_LEAK_KEYS = {
    "expected",
    "oracle",
    "profile",
    "profile_id",
    "corpus_role",
    "tags",
    "relation",
    "relations",
    "partner",
    "relation_ids",
}
DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
BITS_RE = re.compile(r"0x[0-9a-fA-F]{16}\Z")
UNSIGNED_RE = re.compile(r"[0-9]+\Z")
UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1
SIGN_MASK = 1 << 63
EXPONENT_MASK = 0x7FF << 52
FRACTION_MASK = (1 << 52) - 1


class ProtocolError(ValueError):
    """Malformed, unsafe, or internally inconsistent runner data."""


class OracleBoundError(ValueError):
    """An exact oracle input exceeded the deliberately bounded work budget."""


def _duplicate_rejector(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ProtocolError(f"non-finite JSON constant: {value}")


def parse_json_bytes(raw: bytes) -> Any:
    """Parse one bounded strict JSON value."""

    if len(raw) > FRAME_BYTES:
        raise ProtocolError("JSON frame exceeds byte limit")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ProtocolError("JSON frame is not UTF-8") from error
    if text.startswith("\ufeff"):
        raise ProtocolError("UTF-8 BOM is not permitted")
    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_rejector,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ProtocolError, TypeError) as error:
        if isinstance(error, ProtocolError):
            raise
        raise ProtocolError("malformed JSON frame") from error


def read_bounded_bytes(path: Path) -> bytes:
    """Read one bounded manifest/file payload with a cap-plus-one probe."""

    with path.open("rb") as stream:
        data = stream.read(FRAME_BYTES + 1)
    if len(data) > FRAME_BYTES:
        raise ProtocolError(f"{path} exceeds byte limit")
    return data


def parse_raw_request(text: str) -> dict[str, Any] | None:
    """Parse a corpus raw request while retaining duplicate-member cases."""

    if not isinstance(text, str) or not text or "\n" in text or "\r" in text:
        raise ProtocolError("request_raw must be one JSON line")
    if len(text.encode("utf-8")) + 1 > FRAME_BYTES:
        raise ProtocolError("request_raw exceeds frame limit")
    try:
        decoder = json.JSONDecoder(object_pairs_hook=_duplicate_rejector, parse_constant=_reject_constant)
        value, end = decoder.raw_decode(text)
    except (json.JSONDecodeError, ProtocolError, TypeError):
        return None
    if text[end:].strip():
        return None
    return value if isinstance(value, dict) else None


def require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError(f"{name} must be an object")
    return value


def require_exact_fields(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    actual = set(value)
    if actual != fields:
        raise ProtocolError(
            f"{name} fields differ; missing={sorted(fields - actual)}, extra={sorted(actual - fields)}"
        )


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ProtocolError(f"{name} must be a string")
    return value


def require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ProtocolError(f"{name} must be a string list")
    return list(value)


def require_sha256(value: Any, name: str) -> str:
    value = require_string(value, name)
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ProtocolError(f"{name} must be lowercase SHA-256")
    return value


def forbidden_keys(value: Any, path: str = "input") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_LEAK_KEYS:
                raise ProtocolError(f"forbidden candidate field at {path}.{key}")
            forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            forbidden_keys(child, f"{path}[{index}]")


def iter_bounded_frames(stream: BinaryIO) -> Iterable[bytes]:
    """Yield LF-delimited frames without accumulating an oversized line."""

    while True:
        first = stream.readline(FRAME_BYTES + 1)
        if not first:
            return
        if len(first) > FRAME_BYTES:
            while first and not first.endswith(b"\n"):
                first = stream.readline(FRAME_BYTES + 1)
            raise ProtocolError("JSONL frame exceeds byte limit")
        yield first


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def frame_json(value: Any) -> bytes:
    frame = canonical_json_bytes(value) + b"\n"
    if len(frame) > FRAME_BYTES:
        raise ProtocolError("candidate request or result exceeds frame limit")
    return frame


def parse_unsigned_string(value: Any, name: str, maximum: int) -> int:
    value = require_string(value, name)
    if not UNSIGNED_RE.fullmatch(value):
        raise ProtocolError(f"{name} must be an unsigned decimal string")
    parsed = int(value, 10)
    if parsed > maximum:
        raise ProtocolError(f"{name} exceeds bounded integer range")
    return parsed


def binary64_fraction(bits: int) -> Fraction:
    exponent_field = (bits >> 52) & 0x7FF
    fraction = bits & FRACTION_MASK
    negative = bool(bits & SIGN_MASK)
    if exponent_field == 0:
        if fraction == 0:
            return Fraction(0)
        significand = fraction
        exponent = -1074
    else:
        significand = (1 << 52) | fraction
        exponent = exponent_field - 1023 - 52
    result = Fraction(significand << exponent, 1) if exponent >= 0 else Fraction(significand, 1 << -exponent)
    return -result if negative else result


def parse_bits(value: Any, name: str) -> tuple[int, Fraction]:
    value = require_string(value, name)
    if not BITS_RE.fullmatch(value):
        raise ProtocolError(f"{name} must be 0x plus 16 hexadecimal digits")
    bits = int(value[2:], 16)
    if bits & EXPONENT_MASK == EXPONENT_MASK:
        raise ProtocolError(f"{name} is non-finite")
    if bits & ~SIGN_MASK == 0:
        bits = 0
    return bits, binary64_fraction(bits)


def bits_string(bits: int) -> str:
    return f"0x{bits:016x}"

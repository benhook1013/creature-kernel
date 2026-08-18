"""Shared bounded JSONL transport primitives for the phase-two candidate."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


FRAME_BYTES = 64 * 1024
MAX_SOURCE_BYTES = 24 * 1024
MAX_SESSION_RECORDS = 64
SESSION_STDOUT_CAP = FRAME_BYTES * MAX_SESSION_RECORDS
STDOUT_TOTAL_CAP = SESSION_STDOUT_CAP
STDERR_TOTAL_CAP = 64 * 1024
IO_DEADLINE_SECONDS = 2.0
SHUTDOWN_DEADLINE_SECONDS = 2.0
TRAILING_OUTPUT_QUIET_SECONDS = 0.02
REQUEST_PROTOCOL_ID = "ck.exp-0002.r3-authored-conflict-candidate-request-1"
RESPONSE_PROTOCOL_ID = "ck.exp-0002.r3-authored-conflict-candidate-response-1"


class Phase2ProtocolError(ValueError):
    """A stable malformed-frame or protocol-boundary failure."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _duplicate_rejector(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Phase2ProtocolError("duplicate-key", f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise Phase2ProtocolError("nonfinite-json", f"non-finite JSON constant: {token}")


def parse_json_frame(raw: bytes) -> Any:
    """Parse one strict UTF-8 JSON frame, including at most one JSON record."""
    if len(raw) > FRAME_BYTES:
        raise Phase2ProtocolError("frame-too-large", "JSON frame exceeds 64 KiB")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise Phase2ProtocolError("invalid-utf8", "JSON frame is not UTF-8") from error
    if text.startswith("\ufeff"):
        raise Phase2ProtocolError("utf8-bom", "UTF-8 BOM is not permitted")
    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_rejector,
            parse_constant=_reject_constant,
        )
    except Phase2ProtocolError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise Phase2ProtocolError("malformed-json", "JSON frame is malformed") from error


def frame_json(value: Mapping[str, Any]) -> bytes:
    """Serialize one request object as one bounded UTF-8 JSONL frame."""
    if not isinstance(value, Mapping):
        raise Phase2ProtocolError("request-not-object", "request must be a JSON object")
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise Phase2ProtocolError("request-not-json", "request is not strict JSON") from error
    if len(encoded) > FRAME_BYTES:
        raise Phase2ProtocolError("request-frame-too-large", "request frame exceeds 64 KiB")
    if "source" in value:
        source = value["source"]
        if not isinstance(source, str):
            raise Phase2ProtocolError("source-not-string", "source material must be a string")
        if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise Phase2ProtocolError("source-too-large", "source material exceeds 24 KiB")
    return encoded


def validate_request_frame(raw: bytes) -> dict[str, Any]:
    """Validate the transport-owned request object and source-material cap."""
    value = parse_json_frame(raw)
    if not isinstance(value, dict):
        raise Phase2ProtocolError("request-not-object", "candidate request must be an object")
    if "source" in value:
        source = value["source"]
        if not isinstance(source, str):
            raise Phase2ProtocolError("source-not-string", "source material must be a string")
        if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise Phase2ProtocolError("source-too-large", "source material exceeds 24 KiB")
    return value


def validate_response_frame(raw: bytes, request_id: str) -> dict[str, Any]:
    """Validate only the transport-owned response envelope.

    Observation fields are intentionally left opaque for the future runner.
    """
    value = parse_json_frame(raw)
    if not isinstance(value, dict):
        raise Phase2ProtocolError("response-not-object", "candidate response must be an object")
    if value.get("protocol_id") != RESPONSE_PROTOCOL_ID:
        raise Phase2ProtocolError("protocol-mismatch", "candidate response protocol ID differs")
    response_id = value.get("request_id")
    if not isinstance(response_id, str):
        raise Phase2ProtocolError("response-request-id", "candidate response request_id is missing or not a string")
    if response_id != request_id:
        raise Phase2ProtocolError("response-request-id-mismatch", "candidate response request_id differs")
    if not isinstance(value.get("status"), str) or not value["status"]:
        raise Phase2ProtocolError("response-status", "candidate response status is missing or empty")
    return value

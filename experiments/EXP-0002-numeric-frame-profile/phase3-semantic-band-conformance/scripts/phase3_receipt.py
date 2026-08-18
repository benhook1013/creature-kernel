"""Validated deterministic receipt for a synthetic-only Phase 3 result."""

from __future__ import annotations

from typing import Any, Mapping

from phase3_common import MAX_SESSION_RECORDS, ProtocolError, canonical_json

RECEIPT_SCHEMA = "ck.exp-0002.phase3.synthetic-validation-receipt-2"
RESULT_SCHEMA = "ck.exp-0002.phase3.synthetic-run-result-2"
RESULT_KEYS = frozenset({"schema", "mode", "evidence_eligible", "technology_result", "profile_binding", "freeze_manifest_identity", "authorization_reference", "r3_activation", "status", "synthetic_dispatches", "preflight_count", "tool_identities", "counts", "entries"})
COUNT_KEYS = frozenset({"cases", "entries", "supported", "failed", "inconclusive", "observation", "extra_responses"})


def _integer(value: Any, label: str, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ProtocolError("receipt-count", f"{label} is not a bounded nonnegative integer")
    return value


def _validate_result(result: Mapping[str, Any]) -> dict[str, int]:
    if type(result) is not dict or set(result) != RESULT_KEYS:
        raise ProtocolError("receipt-input", "synthetic result violates its closed schema")
    fixed = {
        "schema": RESULT_SCHEMA,
        "mode": "synthetic-validation",
        "evidence_eligible": False,
        "technology_result": "none",
        "profile_binding": None,
        "freeze_manifest_identity": None,
        "authorization_reference": None,
        "r3_activation": "inactive",
    }
    if any(result.get(key) != value for key, value in fixed.items()):
        raise ProtocolError("receipt-input", "synthetic result has an evidence-capable binding")
    # This slice accepts no path, executable, file, or external-tool input, so
    # the only truthful identity set is empty.  A future execution wrapper has
    # a different receipt and must bind its tools there.
    if result.get("tool_identities") != []:
        raise ProtocolError("receipt-input", "pure in-memory validation has no external tool identities")
    if type(result.get("entries")) is not list:
        raise ProtocolError("receipt-input", "synthetic entries must be a list")
    raw_counts = result.get("counts")
    if type(raw_counts) is not dict or set(raw_counts) != COUNT_KEYS:
        raise ProtocolError("receipt-input", "synthetic counts violate their closed schema")
    counts = {key: _integer(raw_counts[key], f"counts.{key}") for key in COUNT_KEYS}
    dispatches = _integer(result.get("synthetic_dispatches"), "synthetic_dispatches", MAX_SESSION_RECORDS)
    preflight = _integer(result.get("preflight_count"), "preflight_count", MAX_SESSION_RECORDS)
    if (
        counts["cases"] > MAX_SESSION_RECORDS
        or counts["extra_responses"] > MAX_SESSION_RECORDS
        or counts["entries"] > 2 * MAX_SESSION_RECORDS
        or counts["entries"] != len(result["entries"])
        or counts["entries"] != counts["cases"] + counts["extra_responses"]
    ):
        raise ProtocolError("receipt-algebra", "case/entry bounds are inconsistent")
    if counts["supported"] + counts["failed"] + counts["inconclusive"] + counts["observation"] != counts["entries"]:
        raise ProtocolError("receipt-algebra", "status counts do not sum to entries")
    if dispatches + preflight != counts["cases"]:
        raise ProtocolError("receipt-algebra", "dispatch/preflight/extra algebra is inconsistent")
    expected_status = (
        "failed" if counts["failed"]
        else "inconclusive" if counts["inconclusive"] or (counts["observation"] and not counts["supported"])
        else "supported"
    )
    if result.get("status") != expected_status:
        raise ProtocolError("receipt-algebra", "aggregate status violates precedence")
    actual = {name: 0 for name in ("supported", "failed", "inconclusive", "observation")}
    for entry in result["entries"]:
        if type(entry) is not dict or entry.get("status") not in actual:
            raise ProtocolError("receipt-entry", "synthetic entry status is invalid")
        actual[entry["status"]] += 1
    if any(actual[key] != counts[key] for key in actual):
        raise ProtocolError("receipt-algebra", "entry statuses differ from counts")
    return counts


def build_receipt(result: Mapping[str, Any]) -> bytes:
    counts = _validate_result(result)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "mode": "synthetic-validation",
        "evidence_eligible": False,
        "profile_binding": None,
        "freeze_manifest_identity": None,
        "authorization_reference": None,
        "r3_activation": "inactive",
        "technology_result": "none",
        "status": result["status"],
        "candidate_counts": {"processes": 0, "requests": 0, "responses": 0},
        "tool_identities": [],
        "synthetic": {
            "cases": counts["cases"],
            "entries": counts["entries"],
            "supported": counts["supported"],
            "failed": counts["failed"],
            "inconclusive": counts["inconclusive"],
            "observation": counts["observation"],
            "extra_responses": counts["extra_responses"],
            "dispatches": result["synthetic_dispatches"],
            "preflight": result["preflight_count"],
        },
    }
    return canonical_json(receipt)


synthetic_validation_receipt = build_receipt
receipt_bytes = build_receipt
__all__ = ["RECEIPT_SCHEMA", "build_receipt", "synthetic_validation_receipt", "receipt_bytes"]

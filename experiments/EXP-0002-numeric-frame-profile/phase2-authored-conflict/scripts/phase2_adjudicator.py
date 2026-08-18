#!/usr/bin/env python3
"""Closed response adjudication for the non-authoritative development run.

Only the stable fields needed by the authored corpus are interpreted.  Human
display details, equation traces, locations, and other diagnostic payload are
not part of classification or expectation matching.
"""

from __future__ import annotations

from typing import Any, Mapping


MAX_ERROR_DETAIL = 256
STABLE_CAUSE_FIELDS = frozenset(
    {"code", "failure", "operation", "stage", "index", "field", "component"}
)
IGNORED_CAUSE_FIELDS = frozenset(
    {"location", "member", "values_member", "role", "values_role", "address", "context"}
)
KNOWN_CAUSE_FIELDS = STABLE_CAUSE_FIELDS | IGNORED_CAUSE_FIELDS


class AdjudicationError(ValueError):
    """A response is malformed for the fields this adjudicator consumes."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail[:MAX_ERROR_DETAIL]
        super().__init__(f"{code}: {self.detail}")


def _fail(code: str, detail: str) -> None:
    raise AdjudicationError(code, detail)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("wrong-type", f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("wrong-type", f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("wrong-type", f"{label} must be a non-empty string")
    return value


def _stable_value(value: Any, label: str) -> Any:
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    _fail("cause-shape", f"{label} is not a stable scalar")


def stable_cause(cause: Any, label: str = "cause") -> dict[str, Any]:
    """Validate a typed cause and return only stable matching fields."""
    value = _object(cause, label)
    unknown = set(value) - KNOWN_CAUSE_FIELDS
    if unknown:
        _fail("cause-fields", f"{label} contains unknown fields")
    if "code" not in value or not isinstance(value["code"], str) or not value["code"]:
        _fail("cause-shape", f"{label}.code is required")
    result: dict[str, Any] = {}
    for key in STABLE_CAUSE_FIELDS:
        if key in value:
            result[key] = _stable_value(value[key], f"{label}.{key}")
    return result


def _cause_signature(cause: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(cause.items()))


def cause_matches(observed: Any, expected: Any) -> bool:
    """Match stable expected fields as an exact subset of observed fields."""
    if expected is None:
        return observed is None
    if observed is None:
        return False
    try:
        observed_stable = stable_cause(observed)
        expected_stable = stable_cause(expected, "expected cause")
    except AdjudicationError:
        return False
    return all(observed_stable.get(key) == value for key, value in expected_stable.items())


def _member_skip(member: Mapping[str, Any], index: int) -> dict[str, Any]:
    skip = _object(member.get("skip"), f"members[{index}].skip")
    if not isinstance(skip.get("code"), str) or not skip["code"]:
        _fail("skip-shape", f"members[{index}].skip.code is required")
    if "detail" in skip and not isinstance(skip["detail"], str):
        _fail("skip-shape", f"members[{index}].skip.detail must be a string")
    return stable_cause(skip.get("cause"), f"members[{index}].skip.cause")


def _attachment(attachment: Any, member_index: int, attachment_index: int) -> tuple[str, dict[str, Any] | None]:
    value = _object(attachment, f"members[{member_index}].attachments[{attachment_index}]")
    outcome = _string(value.get("outcome"), "attachment.outcome")
    if outcome in {"agree", "conflict"}:
        return outcome, None
    if outcome != "skipped":
        _fail("attachment-outcome", f"unsupported attachment outcome {outcome}")
    if not isinstance(value.get("component"), str) or not value["component"]:
        _fail("attachment-shape", "skipped attachment component is required")
    if not isinstance(value.get("code"), str) or not value["code"]:
        _fail("attachment-shape", "skipped attachment code is required")
    if "detail" in value and not isinstance(value["detail"], str):
        _fail("attachment-shape", "attachment detail must be a string")
    cause = stable_cause(value.get("cause"), "attachment.cause")
    cause.setdefault("component", value["component"])
    return outcome, cause


def classify_observations(observations: Any) -> tuple[str, dict[str, Any] | None]:
    """Apply the closed observed-outcome algebra to one observation object."""
    value = _object(observations, "observations")
    required = {"root", "members", "tolerances", "providers"}
    if not required <= set(value):
        _fail("observations-fields", "observations is missing an adjudicated field")
    _object(value["root"], "observations.root")
    _object(value["tolerances"], "observations.tolerances")
    _object(value["providers"], "observations.providers")
    if "detail" in value and not isinstance(value["detail"], str):
        _fail("observations-fields", "observations.detail must be a string")
    members = _array(value["members"], "observations.members")
    if not members:
        _fail("missing-evidence", "observations.members is empty")

    compared_count = 0
    conflict = False
    skip_causes: list[dict[str, Any]] = []
    for member_index, raw_member in enumerate(members):
        member = _object(raw_member, f"members[{member_index}]")
        outcome = _string(member.get("outcome"), f"members[{member_index}].outcome")
        attachments = _array(member.get("attachments"), f"members[{member_index}].attachments")
        if outcome == "compared":
            if not attachments:
                _fail("missing-evidence", f"members[{member_index}] has no compared attachments")
            for attachment_index, attachment in enumerate(attachments):
                attachment_outcome, cause = _attachment(attachment, member_index, attachment_index)
                if attachment_outcome == "agree":
                    compared_count += 1
                elif attachment_outcome == "conflict":
                    compared_count += 1
                    conflict = True
                else:
                    skip_causes.append(cause or {})
        elif outcome == "skipped":
            if attachments:
                _fail("skip-shape", f"members[{member_index}] has attachments while skipped")
            skip_causes.append(_member_skip(member, member_index))
        else:
            _fail("member-outcome", f"unsupported member outcome {outcome}")

    if conflict and skip_causes:
        return "incomplete", None
    if conflict:
        return "conflict", None
    if skip_causes:
        signatures = {_cause_signature(cause) for cause in skip_causes}
        if len(signatures) != 1:
            return "incomplete", None
        return "skipped", skip_causes[0]
    if compared_count == 0:
        return "incomplete", None
    return "agree", None


def classify_response(response: Any) -> tuple[str, dict[str, Any] | None]:
    """Validate and classify the candidate response fields consumed here."""
    value = _object(response, "response")
    if not isinstance(value.get("protocol_id"), str) or not value["protocol_id"]:
        _fail("response-envelope", "response.protocol_id is required")
    if not isinstance(value.get("request_id"), str) or not value["request_id"]:
        _fail("response-envelope", "response.request_id is required")
    status = _string(value.get("status"), "response.status")
    if status == "observed":
        if "observations" not in value or "error" in value or "cause" in value:
            _fail("response-envelope", "observed response has an invalid envelope")
        return classify_observations(value["observations"])
    if status in {"rejected", "unsupported"}:
        if not isinstance(value.get("error"), str) or not value["error"]:
            _fail("response-error", f"{status} response.error is required")
        if "observations" in value:
            _fail("response-envelope", f"{status} response must not include observations")
        cause = stable_cause(value["cause"]) if "cause" in value else None
        return status, cause
    _fail("response-status", f"status {status} is not adjudicable")
    return "incomplete", None


def expectation_passes(
    observed_classification: str,
    observed_cause: dict[str, Any] | None,
    expected: Mapping[str, Any],
) -> bool:
    expected_classification = expected.get("classification")
    if observed_classification != expected_classification:
        return False
    return cause_matches(observed_cause, expected.get("cause"))

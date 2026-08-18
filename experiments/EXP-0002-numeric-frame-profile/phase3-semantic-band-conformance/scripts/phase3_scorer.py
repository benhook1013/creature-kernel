"""Strict scoring of the frozen nested Phase 2 candidate response."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence

from phase3_common import (
    FRAME_BYTES, MAX_REQUEST_ID_BYTES, RESPONSE_PROTOCOL_ID, Phase3Error,
    ProtocolError, RationalInterval, as_fraction, bits_to_float,
    directed_sqrt_bounds, fraction_to_binary64_bits, parse_json,
)

INTERVAL_CAP = Fraction(1, 10**10)
FRAME_VALUE_QUATERNION_CODE = "ck.provisional-r3-authored-conflict.frame-value.quaternion"
MAX_CAUSE_STRING_BYTES = 256
MAX_CAUSE_INDEX = 1_000_000
CAUSE_STRING_FIELDS = frozenset({"code", "failure", "operation", "stage", "field", "component"})
CAUSE_DIAGNOSTIC_FIELDS = frozenset({"location", "member", "values_member", "role", "values_role", "address", "context"})


class ScoringError(Phase3Error):
    pass


def _fail(code: str, detail: str) -> None:
    raise ScoringError(code, detail)


def _obj(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("wrong-type", f"{label} must be an object")
    return value


def _arr(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("wrong-type", f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("wrong-type", f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_CAUSE_STRING_BYTES:
        _fail("size", f"{label} is oversized")
    return value


def _exact_keys(value: Mapping[str, Any], required: set[str], optional: set[str], label: str) -> None:
    keys = set(value)
    if not required <= keys or keys - required - optional:
        _fail("closed-shape", f"{label} has missing or unknown fields")


def stable_cause(value: Any, label: str = "cause") -> dict[str, Any]:
    cause = _obj(value, label)
    allowed = CAUSE_STRING_FIELDS | CAUSE_DIAGNOSTIC_FIELDS | {"index"}
    if "code" not in cause or set(cause) - allowed:
        _fail("cause-shape", f"{label} has missing or unknown fields")
    result: dict[str, Any] = {}
    for key, item in cause.items():
        if key in CAUSE_STRING_FIELDS:
            result[key] = _string(item, f"{label}.{key}")
        elif key == "index":
            if isinstance(item, bool):
                _fail("cause-shape", f"{label}.index is invalid")
            if isinstance(item, Decimal):
                if not item.is_finite() or item != item.to_integral_value():
                    _fail("cause-shape", f"{label}.index is invalid")
                item = int(item)
            if not isinstance(item, int) or not 0 <= item <= MAX_CAUSE_INDEX:
                _fail("cause-shape", f"{label}.index is invalid")
            result[key] = int(item)
        else:
            result[key] = item
    return result


def _address(value: Any, label: str) -> dict[str, Any]:
    address = _obj(value, label)
    _exact_keys(address, {"namespace", "anchors", "kind", "role"}, set(), label)
    _string(address["namespace"], f"{label}.namespace")
    anchors = _arr(address["anchors"], f"{label}.anchors")
    if any(not isinstance(item, str) for item in anchors):
        _fail("address-shape", f"{label}.anchors must contain strings")
    _string(address["kind"], f"{label}.kind")
    _string(address["role"], f"{label}.role")
    return address


def _identity(value: Any, label: str) -> dict[str, str]:
    identity = _obj(value, label)
    _exact_keys(identity, {"document", "namespace"}, set(), label)
    return {"document": _string(identity["document"], f"{label}.document"), "namespace": _string(identity["namespace"], f"{label}.namespace")}


def _location(value: Any, label: str) -> dict[str, Any]:
    location = _obj(value, label)
    _exact_keys(location, {"member", "role", "slot"}, set(), label)
    _identity(location["member"], f"{label}.member")
    _string(location["role"], f"{label}.role")
    slot = _obj(location["slot"], f"{label}.slot")
    if not {"kind", "component"} <= set(slot) or set(slot) - {"kind", "component", "address", "owner_role"}:
        _fail("location-shape", f"{label}.slot has missing or unknown fields")
    _string(slot["kind"], f"{label}.slot.kind")
    _string(slot["component"], f"{label}.slot.component")
    if "address" in slot:
        _address(slot["address"], f"{label}.slot.address")
    return location


def _bits(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _fail("binary64", f"{label} must be a bits string")
    bits_to_float(value)
    return value


def _transform(value: Any, label: str) -> dict[str, list[str]]:
    transform = _obj(value, label)
    _exact_keys(transform, {"translation", "rotation_xyzw"}, set(), label)
    translation = _arr(transform["translation"], f"{label}.translation")
    rotation = _arr(transform["rotation_xyzw"], f"{label}.rotation_xyzw")
    if len(translation) != 3 or len(rotation) != 4:
        _fail("transform-shape", f"{label} has wrong component count")
    return {
        "translation": [_bits(item, f"{label}.translation") for item in translation],
        "rotation_xyzw": [_bits(item, f"{label}.rotation_xyzw") for item in rotation],
    }


def _rotation_interval(left: Sequence[Fraction], right: Sequence[Fraction]) -> RationalInterval:
    left_norm = sum(item * item for item in left)
    right_norm = sum(item * item for item in right)
    if left_norm == 0 or right_norm == 0:
        _fail("binary64-witness", "quaternion is zero")
    product_lower, product_upper = directed_sqrt_bounds(left_norm * right_norm)
    dot = abs(sum(a * b for a, b in zip(left, right)))
    ratio_lower = dot / product_upper if dot else Fraction(0)
    ratio_upper = dot / product_lower if dot else Fraction(0)
    square_lower = max(Fraction(0), Fraction(2) - 2 * ratio_upper)
    square_upper = max(Fraction(0), Fraction(2) - 2 * ratio_lower)
    return RationalInterval(directed_sqrt_bounds(square_lower)[0], directed_sqrt_bounds(square_upper)[1])


def _analytic_transform_matches(reported: Any, analytic: Any, label: str) -> bool:
    actual = _transform(reported, label)
    expected = _obj(analytic, f"{label}.oracle")
    translation = expected.get("translation_exact")
    rotation = expected.get("rotation_raw_exact")
    if not isinstance(translation, list) or len(translation) != 3 or not isinstance(rotation, list) or len(rotation) != 4:
        _fail("oracle-integrity", f"{label} oracle transform is incomplete")
    def exact_fraction(text: Any) -> Fraction:
        if isinstance(text, str) and text.count("/") == 1:
            numerator, denominator = text.split("/", 1)
            if len(numerator) > 256 or len(denominator) > 256 or not numerator.lstrip("-").isdigit() or not denominator.isdigit() or int(denominator) == 0:
                _fail("oracle-integrity", f"{label} has invalid exact fraction")
            return Fraction(int(numerator), int(denominator))
        return as_fraction(text)

    t_error = max(abs(Fraction.from_float(bits_to_float(bits)) - exact_fraction(exact)) for bits, exact in zip(actual["translation"], translation))
    q_actual = [Fraction.from_float(bits_to_float(bits)) for bits in actual["rotation_xyzw"]]
    q_ideal = [exact_fraction(exact) for exact in rotation]
    return t_error <= INTERVAL_CAP and _rotation_interval(q_actual, q_ideal).upper <= INTERVAL_CAP


def _expected_tolerance_bits(request: Mapping[str, Any]) -> dict[str, str]:
    tolerances = _obj(request.get("tolerances"), "request.tolerances")
    _exact_keys(tolerances, {"translation_absolute", "translation_relative", "rotation_half_chord"}, set(), "request.tolerances")
    return {key: fraction_to_binary64_bits(as_fraction(tolerances[key], key), key) for key in ("translation_absolute", "translation_relative", "rotation_half_chord")}


def _validate_observation_header(request: Mapping[str, Any], truth: Mapping[str, Any], observations: Mapping[str, Any]) -> list[Any]:
    _exact_keys(observations, {"root", "members", "tolerances", "providers"}, {"detail"}, "observations")
    if _identity(observations["root"], "observations.root") != truth.get("source_identity"):
        _fail("witness-mismatch", "observations.root differs from source")
    if observations["tolerances"] != _expected_tolerance_bits(request):
        _fail("witness-mismatch", "observed tolerance bits differ from request")
    providers = _obj(request.get("providers"), "request.providers")
    expected_providers = {
        "gate": {"selection": providers.get("gate"), "attestation": "unattested"},
        "arithmetic": {"selection": providers.get("arithmetic"), "attestation": "unattested"},
        "sqrt": {"selection": providers.get("sqrt"), "attestation": "unattested"},
        "environment": providers.get("environment"),
    }
    if observations["providers"] != expected_providers:
        _fail("witness-mismatch", "observed providers differ from request")
    return _arr(observations["members"], "observations.members")


def _root_member(members: Sequence[Any], identity: Mapping[str, Any]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    complete = 0
    for index, raw in enumerate(members):
        member = _obj(raw, f"members[{index}]")
        required = {"identity", "role", "outcome", "attachments"}
        if not required <= set(member):
            _fail("missing-evidence", f"members[{index}] is structurally incomplete")
        parsed_identity = _identity(member["identity"], f"members[{index}].identity")
        role = _string(member["role"], f"members[{index}].role")
        outcome = _string(member["outcome"], f"members[{index}].outcome")
        _arr(member["attachments"], f"members[{index}].attachments")
        # ``skip`` on a complete compared member is contradictory evidence,
        # not an incomplete wire shape; the typed-control adjudicator reports
        # the semantic outcome mismatch below.
        allowed = required | {"skip"}
        if set(member) - allowed:
            _fail("closed-shape", f"members[{index}] has unknown fields")
        complete += 1
        if role == "root" and parsed_identity == identity:
            matches.append(member)
    if len(matches) > 1:
        _fail("witness-mismatch", "duplicate source root members")
    if not matches and complete:
        _fail("witness-mismatch", "complete member evidence has the wrong source root")
    if not matches:
        _fail("missing-evidence", "expected exactly one source root member")
    return matches[0]


def _provenance_matches(value: Any, expected: Mapping[str, Any]) -> bool:
    provenance = _obj(value, "attachment.provenance")
    required = {"attachment", "root", "host_socket", "mating_socket", "host_owner", "mating_owner", "offset", "root_to_mating_owner_path"}
    _exact_keys(provenance, required, set(), "attachment.provenance")
    for field in required - {"offset", "root_to_mating_owner_path"}:
        _address(provenance[field], f"attachment.provenance.{field}")
        if provenance[field] != expected.get(field):
            return False
    if not _analytic_transform_matches(provenance["offset"], expected.get("offset"), "attachment.provenance.offset"):
        return False
    path = _arr(provenance["root_to_mating_owner_path"], "attachment.provenance.root_to_mating_owner_path")
    for index, address in enumerate(path):
        _address(address, f"attachment.provenance.path[{index}]")
    expected_path = expected.get("root_to_mating_owner_path")
    return expected_path is None or path == expected_path


def _validate_equation(value: Any, expected: Mapping[str, Any], expected_provenance: Mapping[str, Any]) -> dict[str, list[str]]:
    equation = _obj(value, "attachment.equation")
    _exact_keys(equation, {"host_socket_local", "mating_socket_local", "root_to_mating_owner_part_locals", "equation_steps"}, set(), "attachment.equation")
    if not _analytic_transform_matches(equation["host_socket_local"], expected.get("host_socket_local"), "equation.host_socket_local") or not _analytic_transform_matches(equation["mating_socket_local"], expected.get("mating_socket_local"), "equation.mating_socket_local"):
        _fail("witness-mismatch", "equation socket input differs from source")
    locals_ = _arr(equation["root_to_mating_owner_part_locals"], "equation.part_locals")
    expected_path = expected_provenance.get("root_to_mating_owner_path", [])
    expected_locals = expected.get("root_to_mating_owner_part_locals", [])
    if len(locals_) != len(expected_path):
        _fail("witness-mismatch", "equation part-local path length differs")
    for index, item in enumerate(locals_):
        local = _obj(item, f"equation.part_locals[{index}]")
        _exact_keys(local, {"address", "local"}, set(), f"equation.part_locals[{index}]")
        _address(local["address"], f"equation.part_locals[{index}].address")
        if local["address"] != expected_path[index]:
            _fail("witness-mismatch", "equation part-local address differs")
        if not _analytic_transform_matches(local["local"], expected_locals[index].get("local"), f"equation.part_locals[{index}].local"):
            _fail("witness-mismatch", "equation part-local differs from source")
    steps = _arr(equation["equation_steps"], "equation.equation_steps")
    operations = ["attachment-containment", "attachment-mating-socket", "attachment-host-offset", "attachment-inverse", "attachment-equation"]
    if len(steps) != len(operations):
        _fail("witness-mismatch", "equation step count differs")
    final_output: dict[str, list[str]] | None = None
    for index, (step, operation) in enumerate(zip(steps, operations)):
        item = _obj(step, f"equation.steps[{index}]")
        _exact_keys(item, {"operation", "output"}, set(), f"equation.steps[{index}]")
        if item["operation"] != operation:
            _fail("witness-mismatch", "equation operation differs")
        if not _analytic_transform_matches(item["output"], expected["equation_steps"][index].get("output"), f"equation.steps[{index}].output"):
            _fail("witness-mismatch", "equation step output differs from oracle")
        if index == len(operations) - 1:
            final_output = _transform(item["output"], f"equation.steps[{index}].output")
    if final_output is None:
        _fail("missing-evidence", "equation has no final output")
    return final_output


def _candidate_interval(metric: str, authored: Mapping[str, Any], derived: Mapping[str, Any]) -> RationalInterval:
    left = _transform(authored, "attachment.authored_root_local")
    right = _transform(derived, "attachment.derived_root_local")
    if metric == "translation":
        values = [abs(Fraction.from_float(bits_to_float(a)) - Fraction.from_float(bits_to_float(b))) for a, b in zip(left["translation"], right["translation"])]
        return RationalInterval(max(values), max(values))
    aq = tuple(Fraction.from_float(bits_to_float(item)) for item in left["rotation_xyzw"])
    bq = tuple(Fraction.from_float(bits_to_float(item)) for item in right["rotation_xyzw"])
    return _rotation_interval(aq, bq)


def _truth_interval(truth: Mapping[str, Any]) -> RationalInterval:
    value = _obj(truth.get("I_truth"), "I_truth")
    return RationalInterval(as_fraction(value.get("lower"), "I_truth.lower"), as_fraction(value.get("upper"), "I_truth.upper"))


def _error_interval(truth: RationalInterval, candidate: RationalInterval) -> RationalInterval:
    lower = candidate.lower - truth.upper if truth.upper < candidate.lower else truth.lower - candidate.upper if candidate.upper < truth.lower else Fraction(0)
    upper = max(abs(a - b) for a in (truth.lower, truth.upper) for b in (candidate.lower, candidate.upper))
    return RationalInterval(lower, upper)


def _threshold(request: Mapping[str, Any], metric: str) -> Fraction:
    tolerances = _obj(request.get("tolerances"), "request.tolerances")
    if metric == "translation":
        absolute = as_fraction(tolerances.get("translation_absolute"), "translation_absolute")
        relative = as_fraction(tolerances.get("translation_relative"), "translation_relative")
        if absolute < 0 or relative < 0:
            _fail("invalid-tolerance", "translation tolerance is negative")
        scale = as_fraction(request.get("translation_scale", 1), "translation_scale")
        return absolute + relative * scale
    half = as_fraction(tolerances.get("rotation_half_chord"), "rotation_half_chord")
    if half < 0:
        _fail("invalid-tolerance", "rotation tolerance is negative")
    return 2 * half


def _candidate_class(interval: RationalInterval, threshold: Fraction) -> str:
    if interval.upper <= threshold:
        return "agree"
    if interval.lower > threshold:
        return "conflict"
    return "straddling"


def classify_candidate_interval(interval: RationalInterval, threshold: Fraction) -> str:
    """Expose the inclusive comparator for direct certified-boundary tests."""
    return _candidate_class(interval, threshold)


def _target_attachment(member: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    attachments = _arr(member.get("attachments"), "member.attachments")
    matches: list[dict[str, Any]] = []
    complete = 0
    required = {"provenance", "equation", "authored_root_local", "derived_root_local", "outcome"}
    allowed = required | {"component", "code", "detail", "cause"}
    for index, attachment in enumerate(attachments):
        item = _obj(attachment, f"member.attachments[{index}]")
        if not required <= set(item):
            _fail("missing-evidence", f"member.attachments[{index}] is structurally incomplete")
        if set(item) - allowed:
            _fail("closed-shape", f"member.attachments[{index}] has unknown fields")
        complete += 1
        if _provenance_matches(item["provenance"], expected):
            matches.append(item)
    if len(matches) > 1:
        _fail("witness-mismatch", "duplicate complete target attachments")
    if not matches and complete:
        _fail("witness-mismatch", "complete attachment evidence has the wrong provenance")
    if not matches:
        _fail("missing-evidence", "expected exactly one target attachment")
    return matches[0]


def _failure_result(error: Exception) -> dict[str, Any]:
    code = getattr(error, "code", "malformed-response")
    if code == "witness-mismatch":
        return {"status": "failed", "classification": "witness-mismatch", "cause": {"code": code, "detail": str(error)[:256]}}
    return {"status": "inconclusive", "classification": "incomplete", "cause": {"code": code, "detail": str(error)[:256]}}


def _typed_control(request: Mapping[str, Any], truth: Mapping[str, Any], observations: Mapping[str, Any]) -> dict[str, Any]:
    try:
        members = _validate_observation_header(request, truth, observations)
        member = _root_member(members, truth["source_identity"])
    except ScoringError as error:
        return _failure_result(error)
    cause: dict[str, Any] | None = None
    complete_wrong: str | None = None
    outcome = member.get("outcome")
    if outcome == "skipped":
        if member.get("attachments") != []:
            complete_wrong = "skipped-member-attachments"
        skip = member.get("skip")
        if isinstance(skip, Mapping):
            if skip.get("code") != FRAME_VALUE_QUATERNION_CODE:
                complete_wrong = "skip-code"
            if "cause" in skip:
                cause = stable_cause(skip["cause"], "member.skip.cause")
    elif outcome == "compared":
        if "skip" in member:
            return {"status": "failed", "classification": "skipped", "cause": {"code": "typed-control-mismatch", "failure": "compared-member-skip-contradiction"}}
        if member.get("attachments") == []:
            return {"status": "failed", "classification": "skipped", "cause": {"code": "typed-control-mismatch", "failure": "member-outcome"}}
        try:
            attachment = _target_attachment(member, truth["provenance"])
        except ScoringError as error:
            return _failure_result(error)
        if attachment.get("outcome") != "skipped":
            complete_wrong = "attachment-outcome"
        elif isinstance(attachment.get("cause"), Mapping):
            cause = stable_cause(attachment["cause"], "attachment.cause")
            if attachment.get("code") != FRAME_VALUE_QUATERNION_CODE:
                complete_wrong = "skip-code"
            if attachment.get("component") != "rotation" or cause.get("component") != "rotation":
                complete_wrong = "skip-component"
    else:
        complete_wrong = "member-outcome"
    if complete_wrong:
        return {"status": "failed", "classification": "skipped", "cause": {"code": "typed-control-mismatch", "failure": complete_wrong}}
    if cause is None:
        return {"status": "inconclusive", "classification": "incomplete", "cause": {"code": "missing-evidence"}}
    if cause.get("code") != FRAME_VALUE_QUATERNION_CODE or cause.get("failure") != "zero-quaternion":
        return {"status": "failed", "classification": "skipped", "cause": {"code": "typed-control-mismatch", "failure": "cause"}}
    if "location" not in cause:
        return {"status": "inconclusive", "classification": "incomplete", "cause": {"code": "missing-location"}}
    try:
        observed_location = _location(cause["location"], "cause.location")
    except ScoringError as error:
        return _failure_result(error)
    expected_locations = truth.get("domain", {}).get("zero_quaternion_locations", [])
    if len(expected_locations) != 1 or observed_location != expected_locations[0]:
        return {"status": "failed", "classification": "skipped", "cause": {"code": "typed-control-mismatch", "failure": "location"}}
    return {"status": "supported", "classification": "skipped", "cause": cause}


def score_response(request: Mapping[str, Any], oracle_result: Mapping[str, Any], response: bytes | Mapping[str, Any], *, expected_class: str | None = None, observation_only: bool = False) -> dict[str, Any]:
    """Score one actual-protocol response; malformed evidence is inconclusive."""
    try:
        if isinstance(response, bytes):
            if len(response) > FRAME_BYTES:
                raise ProtocolError("response-too-large", "response exceeds 64 KiB")
            value = _obj(parse_json(response, label="response"), "response")
        elif isinstance(response, Mapping):
            value = dict(response)
        else:
            _fail("response-type", "response must be bytes or object")
        _exact_keys(value, {"protocol_id", "request_id", "status"}, {"observations", "error", "detail", "cause"}, "response")
        if value["protocol_id"] != RESPONSE_PROTOCOL_ID:
            _fail("protocol-mismatch", "response protocol differs")
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or value["request_id"] != request_id:
            _fail("response-request-id-mismatch", "response request_id differs")
        if len(request_id.encode("utf-8")) > MAX_REQUEST_ID_BYTES:
            _fail("response-request-id", "request_id is oversized")
        status = _string(value["status"], "response.status")
        if status != "observed":
            expected_status = request.get("expected_response_status")
            if expected_status == status and isinstance(value.get("cause"), Mapping):
                observed = stable_cause(value["cause"], "response.cause")
                expected_cause = request.get("expected_cause")
                normalized_expected = stable_cause(expected_cause, "request.expected_cause") if isinstance(expected_cause, Mapping) else None
                if normalized_expected is not None and all(observed.get(key) == item for key, item in normalized_expected.items()):
                    return {"status": "supported", "classification": status, "cause": observed}
                return {"status": "failed", "classification": status, "cause": {"code": "typed-control-mismatch", "failure": "top-level-cause"}}
            return {"status": "inconclusive", "classification": "incomplete", "cause": {"code": "candidate-not-observed"}}
        if "observations" not in value or "error" in value or "cause" in value:
            _fail("response-envelope", "observed response has invalid envelope")
        observations = _obj(value["observations"], "observations")
        if oracle_result.get("status") == "typed-control":
            typed_result = _typed_control(request, oracle_result, observations)
            if observation_only and typed_result.get("status") == "supported":
                typed_result = {**typed_result, "status": "observation"}
            return typed_result
        if oracle_result.get("status") != "admitted":
            return {"status": "observation" if observation_only else "supported", "classification": "out-of-domain", "cause": {"code": "preflight-only"}}
        members = _validate_observation_header(request, oracle_result, observations)
        member = _root_member(members, oracle_result["source_identity"])
        if member.get("outcome") != "compared":
            return {"status": "failed", "classification": "skipped", "cause": {"code": "unexpected-member-outcome"}}
        attachment = _target_attachment(member, oracle_result["provenance"])
        final_output = _validate_equation(attachment["equation"], oracle_result["equation"], oracle_result["provenance"])
        if not _analytic_transform_matches(attachment["authored_root_local"], oracle_result["authored_root_local"], "attachment.authored_root_local"):
            _fail("witness-mismatch", "authored root transform differs from source")
        if _transform(attachment["derived_root_local"], "attachment.derived_root_local") != final_output:
            _fail("witness-mismatch", "derived root transform differs from final equation output")
        candidate = _candidate_interval(str(oracle_result["metric"]), attachment["authored_root_local"], attachment["derived_root_local"])
        truth = _truth_interval(oracle_result)
        error = _error_interval(truth, candidate)
        threshold = _threshold(request, str(oracle_result["metric"]))
        candidate_class = _candidate_class(candidate, threshold)
        reported = attachment.get("outcome")
        if reported not in {"agree", "conflict"}:
            return {"status": "failed", "classification": candidate_class, "I_candidate": candidate.as_dict(), "I_error": error.as_dict(), "cause": {"code": "attachment-outcome"}}
        if candidate_class != "straddling" and reported != candidate_class:
            return {"status": "failed", "classification": candidate_class, "I_candidate": candidate.as_dict(), "I_error": error.as_dict(), "cause": {"code": "classification-mismatch"}}
        if expected_class is not None and candidate_class != "straddling" and candidate_class != expected_class:
            return {"status": "failed", "classification": candidate_class, "I_candidate": candidate.as_dict(), "I_error": error.as_dict(), "cause": {"code": "expected-class-mismatch"}}
        if candidate_class == "straddling":
            return {"status": "inconclusive", "classification": "incomplete", "I_candidate": candidate.as_dict(), "I_error": error.as_dict(), "cause": {"code": "candidate-threshold-straddle"}}
        if candidate.radius > INTERVAL_CAP or error.radius > INTERVAL_CAP or error.upper > INTERVAL_CAP:
            return {"status": "inconclusive", "classification": "incomplete", "I_candidate": candidate.as_dict(), "I_error": error.as_dict(), "cause": {"code": "interval-cap"}}
        if observation_only:
            return {"status": "observation", "classification": candidate_class, "I_candidate": candidate.as_dict(), "I_error": error.as_dict()}
        return {"status": "supported", "classification": candidate_class, "I_candidate": candidate.as_dict(), "I_error": error.as_dict()}
    except (ScoringError, ProtocolError, ValueError) as error:
        return _failure_result(error)


score = score_response
score_synthetic_response = score_response
__all__ = ["ScoringError", "score_response", "score_synthetic_response", "score", "stable_cause", "classify_candidate_interval"]

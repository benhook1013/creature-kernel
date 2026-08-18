#!/usr/bin/env python3
"""Independent exact oracle for the EXP-0002 development extension.

The historical development runner deliberately adjudicates only the stable
classification algebra.  This module is intentionally separate: it checks the
long-tail fixture's complete placement witness.  Source decimals are parsed
as :class:`~fractions.Fraction` values, basis conversion and unit scaling are
performed without binary floating point, and the expected binary64 output is
then compared with the candidate's bit strings.

This is a development experiment, not an activation or profile-selection
authority.  A malformed/incomplete response is represented by the runner as
``inconclusive``; a complete response whose witness differs from this oracle
is a failure.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence


class OracleError(ValueError):
    """The candidate response or source cannot satisfy the closed oracle."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = str(detail)[:256]
        super().__init__(f"{code}: {self.detail}")


class OracleIntegrityError(OracleError):
    """The authored source cannot be evaluated by this bounded oracle."""


def _fail(code: str, detail: str) -> None:
    raise OracleError(code, detail)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("wrong-type", f"{label} must be an object")
    return value


def _array(value: Any, label: str, length: int | None = None) -> list[Any]:
    if not isinstance(value, list):
        _fail("wrong-type", f"{label} must be an array")
    if length is not None and len(value) != length:
        _fail("length", f"{label} must contain {length} entries")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("wrong-type", f"{label} must be a non-empty string")
    return value


def _fraction(value: Any, label: str) -> Fraction:
    """Parse JSON numbers or decimal strings exactly.

    Corpus material is deliberately JSON and therefore normally supplies
    integer/decimal values.  Reject binary-only non-finite values rather than
    silently approximating them.
    """
    if isinstance(value, bool):
        _fail("number", f"{label} is boolean")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            _fail("number", f"{label} is not finite")
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("number", f"{label} is not finite")
        # A caller that parsed ordinary JSON with the stdlib has already lost
        # decimal spelling.  from_float still makes that loss explicit and
        # deterministic; the extension's authored values are dyadic.
        return Fraction.from_float(value)
    if isinstance(value, str):
        try:
            parsed = Decimal(value)
        except Exception as error:  # Decimal raises several subclasses.
            _fail("number", f"{label} is not a decimal: {error}")
        if not parsed.is_finite():
            _fail("number", f"{label} is not finite")
        return Fraction(parsed)
    _fail("number", f"{label} is not numeric")
    raise AssertionError


def _bits(value: Fraction, label: str) -> str:
    """Return exact round-to-nearest/even IEEE-754 binary64 bits."""
    if value == 0:
        return "0x0000000000000000"
    sign = 1 if value < 0 else 0
    value = abs(value)
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if exponent >= 0 and Fraction(1 << exponent) > value:
        exponent -= 1
    elif exponent < 0 and Fraction(1, 1 << -exponent) > value:
        exponent -= 1

    def round_even(numerator: int, denominator: int) -> int:
        quotient, remainder = divmod(numerator, denominator)
        if remainder * 2 > denominator or (remainder * 2 == denominator and quotient % 2):
            quotient += 1
        return quotient

    if exponent < -1022:
        significand = round_even((value * (1 << 1074)).numerator, (value * (1 << 1074)).denominator)
        if significand == 0:
            return f"0x{sign << 63:016x}"
        if significand >= 1 << 52:
            return f"0x{(sign << 63) | (1 << 52):016x}"
        return f"0x{(sign << 63) | significand:016x}"
    scale = 52 - exponent
    scaled = value * (1 << scale) if scale >= 0 else value / (1 << -scale)
    significand = round_even(scaled.numerator, scaled.denominator)
    if significand == 1 << 53:
        significand >>= 1
        exponent += 1
    if exponent > 1023:
        _fail("binary64", f"{label} rounded to infinity")
    bits = (sign << 63) | ((exponent + 1023) << 52) | (significand - (1 << 52))
    return f"0x{bits:016x}"


def _fraction_sqrt(value: Fraction, label: str) -> Fraction:
    if value < 0:
        _fail("quaternion", f"{label} norm is negative")
    numerator_root = math.isqrt(value.numerator)
    denominator_root = math.isqrt(value.denominator)
    if numerator_root * numerator_root != value.numerator or denominator_root * denominator_root != value.denominator:
        _fail("quaternion", f"{label} norm is not an exact rational square")
    return Fraction(numerator_root, denominator_root)


def _signed_axis(axis: Any, label: str) -> tuple[int, int]:
    value = _string(axis, label)
    if len(value) != 2 or value[0] not in "+-" or value[1] not in "xyz":
        _fail("basis", f"{label} is not a signed axis")
    return "xyz".index(value[1]), 1 if value[0] == "+" else -1


def _basis_map(source: Mapping[str, Any]) -> tuple[tuple[int, int], ...]:
    basis = _object(source.get("basis"), "basis")
    _, up_sign = _signed_axis(basis.get("up"), "basis.up")
    up_index, _ = _signed_axis(basis.get("up"), "basis.up")
    forward_index, forward_sign = _signed_axis(basis.get("forward"), "basis.forward")
    if up_index == forward_index:
        _fail("basis", "basis up and forward are collinear")
    # Cross(up, forward), represented as a signed Cartesian axis.
    cross = {
        (0, 1): (2, up_sign * forward_sign),
        (1, 2): (0, up_sign * forward_sign),
        (2, 0): (1, up_sign * forward_sign),
        (1, 0): (2, -up_sign * forward_sign),
        (2, 1): (0, -up_sign * forward_sign),
        (0, 2): (1, -up_sign * forward_sign),
    }[(up_index, forward_index)]
    handedness = _string(basis.get("handedness"), "basis.handedness")
    right = (cross[0], cross[1] if handedness == "right" else -cross[1])
    if handedness not in {"right", "left"}:
        _fail("basis", "basis.handedness is unsupported")
    return (right, (up_index, up_sign), (forward_index, forward_sign))


_UNIT_METRES: dict[str, Fraction] = {
    "metre": Fraction(1),
    "centimetre": Fraction(1, 100),
    "millimetre": Fraction(1, 1000),
}


def _map_vec(values: Sequence[Any], basis_map: tuple[tuple[int, int], ...], unit: Fraction, label: str) -> tuple[Fraction, Fraction, Fraction]:
    raw = [_fraction(value, f"{label}[{index}]") for index, value in enumerate(_array(list(values), label, 3))]
    return tuple(raw[index] * sign * unit for index, sign in basis_map)  # type: ignore[return-value]


def _map_quat(values: Sequence[Any], basis_map: tuple[tuple[int, int], ...], label: str) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    raw = [_fraction(value, f"{label}[{index}]") for index, value in enumerate(_array(list(values), label, 4))]
    vector = [raw[index] * sign for index, sign in basis_map]
    # Quaternion vector components are axial: det(C) * C.
    permutation = [item[0] for item in basis_map]
    inversions = sum(permutation[i] > permutation[j] for i in range(3) for j in range(i + 1, 3))
    determinant = (-1 if inversions % 2 else 1) * math.prod(item[1] for item in basis_map)
    vector = [component * determinant for component in vector]
    q = tuple(vector + [raw[3]])
    norm_sq = sum(component * component for component in q)
    if norm_sq == 0:
        _fail("quaternion", f"{label} is zero")
    norm = _fraction_sqrt(norm_sq, label)
    return _canonical_quat(tuple(component / norm for component in q))


Transform = tuple[tuple[Fraction, Fraction, Fraction], tuple[Fraction, Fraction, Fraction, Fraction]]


def _canonical_quat(q: Sequence[Fraction]) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    """Select the core's unique quaternion representative.

    Components are carried as ``xyzw``, but sign selection examines
    ``w,x,y,z``.  Fractions have only one zero representation, so serialization
    through :func:`_bits` also guarantees canonical ``+0`` output bits.
    """
    result = tuple(q)
    sign_component = next((result[index] for index in (3, 0, 1, 2) if result[index] != 0), None)
    if sign_component is not None and sign_component < 0:
        result = tuple(-component for component in result)
    return result  # type: ignore[return-value]


def _quat_mul(left: Sequence[Fraction], right: Sequence[Fraction]) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    x1, y1, z1, w1 = left
    x2, y2, z2, w2 = right
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    )


def _quat_conjugate(q: Sequence[Fraction]) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    return (-q[0], -q[1], -q[2], q[3])  # type: ignore[return-value]


def _rotate(q: Sequence[Fraction], vector: Sequence[Fraction]) -> tuple[Fraction, Fraction, Fraction]:
    point = (vector[0], vector[1], vector[2], Fraction(0))
    result = _quat_mul(_quat_mul(q, point), _quat_conjugate(q))
    return result[0], result[1], result[2]


def _compose(left: Transform, right: Transform) -> Transform:
    translation = tuple(left[0][index] + _rotate(left[1], right[0])[index] for index in range(3))
    return translation, _canonical_quat(_quat_mul(left[1], right[1]))


def _inverse(value: Transform) -> Transform:
    q = _canonical_quat(_quat_conjugate(value[1]))
    return tuple(-component for component in _rotate(q, value[0])), q  # type: ignore[return-value]


def _transform(value: Mapping[str, Any], basis_map: tuple[tuple[int, int], ...], unit: Fraction, label: str) -> Transform:
    return (
        _map_vec(value.get("translation"), basis_map, unit, f"{label}.translation"),
        _map_quat(value.get("rotation_xyzw"), basis_map, f"{label}.rotation_xyzw"),
    )


def _address(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    result = _object(value, label)
    for field in ("namespace", "anchors", "kind", "role"):
        if field not in result:
            _fail("address", f"{label}.{field} is missing")
    _string(result["namespace"], f"{label}.namespace")
    _array(result["anchors"], f"{label}.anchors")
    _string(result["kind"], f"{label}.kind")
    _string(result["role"], f"{label}.role")
    return result


def _part(source: Mapping[str, Any], role: str, anchors: list[str]) -> Mapping[str, Any]:
    parts = _array(_object(source.get("body"), "body").get("parts"), "body.parts")
    matches = [part for part in parts if isinstance(part, dict) and part.get("address", {}).get("role") == role and part.get("address", {}).get("anchors") == anchors]
    if len(matches) != 1:
        _fail("source-shape", f"expected one {role} part with anchors {anchors}")
    return _object(matches[0], f"part.{role}")


def _socket(source: Mapping[str, Any], anchors: list[str]) -> Mapping[str, Any]:
    sockets = _array(_object(source.get("body"), "body").get("sockets"), "body.sockets")
    matches = [socket for socket in sockets if isinstance(socket, dict) and socket.get("address", {}).get("anchors") == anchors]
    if len(matches) != 1:
        _fail("source-shape", f"expected one socket with anchors {anchors}")
    return _object(matches[0], "socket")


def _source_document(source: bytes | str) -> dict[str, Any]:
    if isinstance(source, bytes):
        try:
            document = json.loads(source.decode("utf-8"), parse_float=Decimal, parse_int=int)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            _fail("source-json", str(error))
    else:
        try:
            document = json.loads(source, parse_float=Decimal, parse_int=int)
        except json.JSONDecodeError as error:
            _fail("source-json", str(error))
    return _object(document, "source")


def source_member_identity(source: bytes | str) -> dict[str, str]:
    """Return the root member identity authored in the materialized source."""
    document = _source_document(source)
    identity = _object(document.get("source"), "source.source")
    return {
        "document": _string(identity.get("document"), "source.source.document"),
        "namespace": _string(identity.get("namespace"), "source.source.namespace"),
    }


def expected_witness(source: bytes | str) -> dict[str, Any]:
    """Build the exact long-tail witness expected from one materialized case."""
    document = _source_document(source)
    basis = _object(document.get("basis"), "basis")
    unit_name = _string(basis.get("length_unit"), "basis.length_unit")
    if unit_name not in _UNIT_METRES:
        _fail("unit", f"unsupported extension unit {unit_name}")
    basis_map = _basis_map(document)
    unit = _UNIT_METRES[unit_name]

    root = _part(document, "tail_root", ["tail"])
    tip = _part(document, "tail_tip", ["tail"])
    end = _part(document, "tail_end", ["tail", "end"])
    host = _socket(document, [])
    mating = _socket(document, ["tail"])
    attachments = _array(_object(document.get("body"), "body").get("attachments"), "body.attachments")
    if len(attachments) != 1:
        _fail("source-shape", "extension requires exactly one attachment")
    attachment = _object(attachments[0], "attachment")
    offset = _transform(attachment.get("offset"), basis_map, unit, "attachment.offset")
    root_local = _transform(root.get("placement"), basis_map, unit, "tail_root.placement")
    tip_local = _transform(tip.get("placement"), basis_map, unit, "tail_tip.placement")
    end_local = _transform(end.get("placement"), basis_map, unit, "tail_end.placement")
    host_local = _transform(host.get("interface_frame"), basis_map, unit, "host.interface_frame")
    mating_local = _transform(mating.get("interface_frame"), basis_map, unit, "mating.interface_frame")

    folded = _compose(tip_local, end_local)
    root_to_mating = _compose(folded, mating_local)
    host_plus_offset = _compose(host_local, offset)
    inverse_mating = _inverse(root_to_mating)
    derived = _compose(host_plus_offset, inverse_mating)

    def transform_value(value: Transform) -> dict[str, list[str]]:
        return {
            "translation": [_bits(component, "transform.translation") for component in value[0]],
            "rotation_xyzw": [_bits(component, "transform.rotation") for component in value[1]],
        }

    def addr(value: Mapping[str, Any], label: str) -> dict[str, Any]:
        return _address(value.get("address", value), label)

    path = [addr(root, "tail_root.address"), addr(tip, "tail_tip.address"), addr(end, "tail_end.address")]
    part_locals = [
        {"address": path[1], "local": transform_value(tip_local)},
        {"address": path[2], "local": transform_value(end_local)},
    ]
    attachment_address = addr(attachment, "attachment.address")
    host_address = addr(host, "host.address")
    mating_address = addr(mating, "mating.address")
    host_owner = _address(host.get("owner"), "host.owner")
    mating_owner = _address(mating.get("owner"), "mating.owner")
    provenance = {
        "attachment": attachment_address,
        "root": path[0],
        "host_socket": host_address,
        "mating_socket": mating_address,
        "host_owner": host_owner,
        "mating_owner": mating_owner,
        "offset": transform_value(offset),
        "root_to_mating_owner_path": path,
    }
    equation = {
        "host_socket_local": transform_value(host_local),
        "mating_socket_local": transform_value(mating_local),
        "root_to_mating_owner_part_locals": part_locals,
        "equation_steps": [
            {"operation": "attachment-containment", "output": transform_value(folded)},
            {"operation": "attachment-mating-socket", "output": transform_value(root_to_mating)},
            {"operation": "attachment-host-offset", "output": transform_value(host_plus_offset)},
            {"operation": "attachment-inverse", "output": transform_value(inverse_mating)},
            {"operation": "attachment-equation", "output": transform_value(derived)},
        ],
    }
    return {
        "provenance": provenance,
        "equation": equation,
        "authored_root_local": transform_value(root_local),
        "derived_root_local": transform_value(derived),
    }


def _deep_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        _fail("witness-mismatch", label)


def verify_response(response: Mapping[str, Any], source: bytes | str, profile_id: str, tolerance_bits: Mapping[str, str]) -> str:
    """Verify the closed observed response and return its classification.

    The returned classification is deliberately only ``agree`` or ``conflict``
    for this extension.  ``skipped``, ``unsupported`` and ``rejected`` are
    incomplete evidence and therefore raise ``OracleError``.
    """
    value = _object(response, "response")
    if value.get("status") != "observed":
        _fail("response-status", "extension requires an observed response")
    observations = _object(value.get("observations"), "observations")
    try:
        expected_member_identity = source_member_identity(source)
        witness = expected_witness(source)
    except OracleError as error:
        raise OracleIntegrityError(error.code, error.detail) from error
    _deep_equal(observations.get("root"), expected_member_identity, "root identity")
    _deep_equal(observations.get("tolerances"), dict(tolerance_bits), "tolerances")
    providers = _object(observations.get("providers"), "observations.providers")
    expected_providers = {
        "gate": {"selection": "allow", "attestation": "unattested"},
        "arithmetic": {"selection": "native", "attestation": "unattested"},
        "sqrt": {"selection": "native", "attestation": "unattested"},
        "environment": "unattested-no-probe-v1",
    }
    _deep_equal(providers, expected_providers, "providers")
    members = _array(observations.get("members"), "observations.members")
    if len(members) != 1:
        _fail("witness-shape", "extension requires exactly one root member")
    member = _object(members[0], "members[0]")
    _deep_equal(member.get("identity"), expected_member_identity, "member identity")
    _deep_equal(member.get("role"), "root", "member role")
    _deep_equal(member.get("outcome"), "compared", "member outcome")
    attachments = _array(member.get("attachments"), "members[0].attachments")
    if len(attachments) != 1:
        _fail("witness-shape", "extension requires exactly one attachment")
    attachment = _object(attachments[0], "attachment")
    for field in ("provenance", "equation", "authored_root_local", "derived_root_local"):
        _deep_equal(attachment.get(field), witness[field], field)
    outcome = attachment.get("outcome")
    if outcome not in {"agree", "conflict"}:
        _fail("attachment-outcome", "extension requires an agree or conflict attachment outcome")
    _string(profile_id, "profile_id")
    return outcome

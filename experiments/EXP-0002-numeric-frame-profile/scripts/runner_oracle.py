"""Independent exact decimal and dyadic oracle for the frozen phase-1 cases."""

from __future__ import annotations

import re
import sys
from fractions import Fraction
from typing import Any, Mapping

from runner_common import (
    DECIMAL_RE,
    EXPONENT_MASK,
    MAX_CASES_PER_CORPUS,
    OPERATION_FIELDS,
    OracleBoundError,
    PREREGISTERED_LIMITS,
    ProtocolError,
    SIGN_MASK,
    UINT32_MAX,
    UINT64_MAX,
    bits_string,
    parse_bits,
    parse_unsigned_string,
    require_exact_fields,
    require_string,
)

# This is an oracle work bound, not a corpus input limit.  Preflight computes
# the maximum admitted decimal materialization need and retains that proof.
MAX_ORACLE_DECIMAL_DIGITS = PREREGISTERED_LIMITS["max_oracle_decimal_digits"]

ERR_INVALID_JSON_NUMBER = "invalid-json-number"
ERR_OVERFLOW = "non-finite-or-overflow"
ERR_UNDERFLOW = "nonzero-underflow-to-zero"


def _round_even(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    twice = remainder * 2
    if twice > denominator or (twice == denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2_fraction(numerator: int, denominator: int) -> int:
    estimate = numerator.bit_length() - denominator.bit_length()
    if estimate >= 0:
        if numerator < denominator << estimate:
            estimate -= 1
    elif numerator << -estimate < denominator:
        estimate -= 1
    return estimate


def _round_scaled(numerator: int, denominator: int, scale: int) -> int:
    if scale >= 0:
        return _round_even(numerator << scale, denominator)
    return _round_even(numerator, denominator << -scale)


def round_fraction_to_binary64(value: Fraction) -> int | None:
    """Return nearest-even finite binary64 bits, or None for overflow/zero."""

    if value == 0:
        return 0
    negative = value < 0
    numerator = abs(value.numerator)
    denominator = value.denominator
    exponent = _floor_log2_fraction(numerator, denominator)
    if exponent < -1022:
        significand = _round_scaled(numerator, denominator, 1074)
        if significand == 0:
            return None
        if significand >= 1 << 52:
            exponent_field = 1
            fraction = significand - (1 << 52)
        else:
            exponent_field = 0
            fraction = significand
    else:
        significand = _round_scaled(numerator, denominator, 52 - exponent)
        if significand >= 1 << 53:
            significand >>= 1
            exponent += 1
        if exponent > 1023:
            return None
        exponent_field = exponent + 1023
        fraction = significand - (1 << 52)
    result = (exponent_field << 52) | fraction
    return result | SIGN_MASK if negative else result


def _decimal_profile(token: str) -> tuple[int, int, int, bool]:
    if not DECIMAL_RE.fullmatch(token):
        raise ProtocolError(ERR_INVALID_JSON_NUMBER)
    unsigned = token[1:] if token.startswith("-") else token
    parts = re.split(r"[eE]", unsigned, maxsplit=1)
    mantissa = parts[0]
    exponent_text = parts[1] if len(parts) == 2 else ""
    integer, _, fraction = mantissa.partition(".")
    digits = integer + fraction
    nonzero_seen = False
    significant_digits = 0
    for char in digits:
        if char != "0":
            nonzero_seen = True
        if nonzero_seen:
            significant_digits += 1
    if significant_digits == 0:
        significant_digits = 1
    exponent = 0
    exponent_abs = 0
    if exponent_text:
        exponent_sign = 1
        if exponent_text[0] in "+-":
            exponent_sign = -1 if exponent_text[0] == "-" else 1
            exponent_text = exponent_text[1:]
        for char in exponent_text:
            exponent_abs = min(UINT64_MAX, exponent_abs * 10 + int(char))
        exponent = exponent_sign * exponent_abs
    return significant_digits, exponent_abs, exponent, all(char == "0" for char in digits)


def decimal_fraction(token: str, exponent: int) -> Fraction:
    unsigned = token[1:] if token.startswith("-") else token
    mantissa = re.split(r"[eE]", unsigned, maxsplit=1)[0]
    integer, _, fraction = mantissa.partition(".")
    digits = integer + fraction
    numerator = int(digits, 10)
    scale = exponent - len(fraction)
    value = Fraction(numerator * 10**scale, 1) if scale >= 0 else Fraction(numerator, 10**-scale)
    return -value if token.startswith("-") else value


def fraction_record(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _decimal_case(input_value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    require_exact_fields(input_value, OPERATION_FIELDS["decimal-admission"], "decimal input")
    token = require_string(input_value["token"], "token")
    max_token = parse_unsigned_string(input_value["max_token_bytes"], "max_token_bytes", sys.maxsize)
    max_digits = parse_unsigned_string(input_value["max_significant_digits"], "max_significant_digits", sys.maxsize)
    max_exponent = parse_unsigned_string(input_value["max_exponent_abs"], "max_exponent_abs", UINT32_MAX)
    if max_token == 0 or max_digits == 0:
        return {"classification": "invalid-input", "owner": "runner-exact-decimal-v1"}, {"status": "error", "error_code": "invalid-input"}, 0
    token_bytes = len(token.encode("utf-8"))
    if token_bytes > max_token:
        return {"classification": "resource-limit", "limit": "token-bytes", "owner": "runner-exact-decimal-v1"}, {"status": "resource-limit", "error_code": "token-bytes"}, 0
    try:
        significant, exponent_abs, exponent, zero = _decimal_profile(token)
    except ProtocolError:
        return {"classification": "invalid-json-number", "owner": "runner-exact-decimal-v1"}, {"status": "rejected", "error_code": ERR_INVALID_JSON_NUMBER}, 0
    if significant > max_digits:
        return {"classification": "resource-limit", "limit": "significant-digits", "owner": "runner-exact-decimal-v1"}, {"status": "resource-limit", "error_code": "significant-digits"}, 0
    if exponent_abs > max_exponent:
        return {"classification": "resource-limit", "limit": "exponent-magnitude", "owner": "runner-exact-decimal-v1"}, {"status": "resource-limit", "error_code": "exponent-magnitude"}, 0
    if zero:
        value = Fraction(0)
        work_digits = 0
    else:
        unsigned = token[1:] if token.startswith("-") else token
        mantissa = re.split(r"[eE]", unsigned, maxsplit=1)[0]
        _, _, fraction_digits = mantissa.partition(".")
        integer_digits = mantissa.replace(".", "").lstrip("0")
        scale = exponent - len(fraction_digits)
        work_digits = len(integer_digits) + abs(scale)
        if work_digits > MAX_ORACLE_DECIMAL_DIGITS:
            raise OracleBoundError(f"decimal materialization requires {work_digits} digits")
        value = decimal_fraction(token, exponent)
    bits = round_fraction_to_binary64(value)
    if bits is None:
        if abs(value) <= Fraction(1, 1 << 1075):
            return {"classification": "nonzero-underflow", "rational": fraction_record(value), "owner": "runner-exact-decimal-v1"}, {"status": "rejected", "error_code": ERR_UNDERFLOW}, work_digits
        return {"classification": "non-finite-or-overflow", "rational": fraction_record(value), "owner": "runner-exact-decimal-v1"}, {"status": "rejected", "error_code": ERR_OVERFLOW}, work_digits
    return {"classification": "admitted", "bits": bits_string(bits), "rational": fraction_record(value), "rounding": "nearest-even", "owner": "runner-exact-decimal-v1"}, {"status": "observed", "observations": {"bits": bits_string(bits)}}, work_digits


def _comparison_case(operation: str, input_value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    require_exact_fields(input_value, OPERATION_FIELDS[operation], f"{operation} input")
    _, absolute = parse_bits(input_value["absolute_bits"], "absolute_bits")
    _, relative = parse_bits(input_value["relative_bits"], "relative_bits")
    if operation == "scalar-comparison":
        values = [(parse_bits(input_value["left_bits"], "left_bits")[1], parse_bits(input_value["right_bits"], "right_bits")[1])]
    else:
        left = input_value["left_bits"]
        right = input_value["right_bits"]
        if not isinstance(left, list) or not isinstance(right, list) or len(left) != 3 or len(right) != 3:
            raise ProtocolError("translation vectors must be arrays of three components")
        values = [(parse_bits(a, f"left_bits[{i}]")[1], parse_bits(b, f"right_bits[{i}]")[1]) for i, (a, b) in enumerate(zip(left, right))]
    differences: list[Fraction] = []
    bounds: list[Fraction] = []
    predicates: list[bool] = []
    for left_value, right_value in values:
        difference = abs(left_value - right_value)
        bound = absolute + relative * max(abs(left_value), abs(right_value))
        differences.append(difference)
        bounds.append(bound)
        predicates.append(difference <= bound)
    predicate = all(predicates)
    oracle = {"classification": "predicate", "predicate": predicate, "absolute": fraction_record(absolute), "relative": fraction_record(relative), "differences": [fraction_record(value) for value in differences], "bounds": [fraction_record(value) for value in bounds], "uncertainty": "exact", "owner": "runner-exact-dyadic-v1"}
    return oracle, {"status": "observed", "observations": {"predicate": predicate}}


def oracle_case(operation: str, input_value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    if operation == "decimal-admission":
        return _decimal_case(input_value)
    if operation in {"scalar-comparison", "translation-comparison"}:
        oracle, expected = _comparison_case(operation, input_value)
        return oracle, expected, 0
    if operation == "environment-attestation":
        require_exact_fields(input_value, set(), "environment input")
        return {"classification": "evidence-only", "owner": "candidate-environment-observation-v1", "uncertainty": "not-applicable"}, {"status": "observed"}, 0
    raise ProtocolError(f"unsupported operation: {operation}")

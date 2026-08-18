"""Pure, bounded primitives shared by the synthetic Phase 3 pipeline.

This module intentionally has no knowledge of the candidate, corpus files, or
the repository.  It is safe to import from small in-memory tests and keeps the
wire limits inherited from Phase 2 in one place.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Mapping


FRAME_BYTES = 64 * 1024
MAX_SOURCE_BYTES = 24 * 1024
MAX_REQUEST_ID_BYTES = 256
MAX_SESSION_RECORDS = 64
SESSION_STDOUT_CAP = FRAME_BYTES * MAX_SESSION_RECORDS
STDOUT_TOTAL_CAP = SESSION_STDOUT_CAP
STDERR_TOTAL_CAP = 64 * 1024
IO_DEADLINE_SECONDS = 2.0
SHUTDOWN_DEADLINE_SECONDS = 2.0
TRAILING_OUTPUT_QUIET_SECONDS = 0.02
REQUEST_PROTOCOL_ID = "ck.exp-0002.r3-authored-conflict-candidate-request-1"
RESPONSE_PROTOCOL_ID = "ck.exp-0002.r3-authored-conflict-candidate-response-1"
SQRT_PRECISION_BITS = 256
INTERVAL_DECIMAL_PLACES = 96
MAX_RESPONSE_BYTES = FRAME_BYTES
MAX_NUMERIC_TOKEN_BYTES = 256
MAX_NUMERIC_SIGNIFICANT_DIGITS = 192
MAX_NUMERIC_EXPONENT_ABS = 2048


class Phase3Error(ValueError):
    """A stable error from a bounded synthetic operation."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", " ")[:256]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


class ProtocolError(Phase3Error):
    pass


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ProtocolError("duplicate-key", f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _constant(token: str) -> None:
    raise ProtocolError("nonfinite-json", f"non-finite JSON constant: {token}")


def bounded_decimal(token: str) -> Decimal:
    """Admit a finite JSON numeric token before any large integer expansion."""
    if not isinstance(token, str) or len(token.encode("ascii", errors="ignore")) != len(token):
        raise ProtocolError("numeric-token", "numeric token is not bounded ASCII")
    if len(token) > MAX_NUMERIC_TOKEN_BYTES:
        raise ProtocolError("numeric-token-too-large", "numeric token exceeds 256 bytes")
    try:
        value = Decimal(token)
    except InvalidOperation as error:
        raise ProtocolError("numeric-token", "numeric token is invalid") from error
    if not value.is_finite():
        raise ProtocolError("nonfinite-json", "numeric token is non-finite")
    sign, digits, exponent = value.as_tuple()
    del sign
    significant = len(digits)
    adjusted = value.adjusted() if value != 0 else 0
    if significant > MAX_NUMERIC_SIGNIFICANT_DIGITS:
        raise ProtocolError("numeric-significand-too-large", "numeric token has too many significant digits")
    if abs(exponent) > MAX_NUMERIC_EXPONENT_ABS or abs(adjusted) > MAX_NUMERIC_EXPONENT_ABS:
        raise ProtocolError("numeric-exponent-too-large", "numeric token exponent exceeds bound")
    return value


def parse_json(raw: bytes | str, *, label: str = "JSON") -> Any:
    """Parse strict UTF-8 JSON while retaining decimal source lexemes."""
    if isinstance(raw, bytes):
        if len(raw) > FRAME_BYTES:
            raise ProtocolError("frame-too-large", f"{label} exceeds {FRAME_BYTES} bytes")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ProtocolError("invalid-utf8", f"{label} is not UTF-8") from error
    elif isinstance(raw, str):
        text = raw
        if len(text.encode("utf-8")) > FRAME_BYTES:
            raise ProtocolError("frame-too-large", f"{label} exceeds {FRAME_BYTES} bytes")
    else:
        raise ProtocolError("wrong-type", f"{label} must be bytes or string")
    if text.startswith("\ufeff"):
        raise ProtocolError("utf8-bom", f"{label} has a BOM")
    try:
        return json.loads(
            text,
            parse_int=bounded_decimal,
            parse_float=bounded_decimal,
            parse_constant=_constant,
            object_pairs_hook=_pairs,
        )
    except ProtocolError:
        raise
    except (json.JSONDecodeError, InvalidOperation, RecursionError, TypeError, ValueError) as error:
        raise ProtocolError("malformed-json", f"{label} is malformed") from error


def parse_json_frame(raw: bytes) -> Any:
    return parse_json(raw, label="JSON frame")


def canonical_json(value: Any, *, limit: int = FRAME_BYTES) -> bytes:
    try:
        raw = (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ProtocolError("not-json", "value cannot be encoded as strict JSON") from error
    if len(raw) > limit:
        raise ProtocolError("frame-too-large", f"canonical JSON exceeds {limit} bytes")
    return raw


def _request_id(value: Mapping[str, Any]) -> str:
    request_id = value.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise ProtocolError("request-id", "request_id must be a non-empty string")
    try:
        size = len(request_id.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ProtocolError("request-id-encoding", "request_id is not valid UTF-8") from error
    if size > MAX_REQUEST_ID_BYTES:
        raise ProtocolError("request-id-too-large", "request_id exceeds 256 UTF-8 bytes")
    return request_id


def validate_request_frame(raw: bytes) -> dict[str, Any]:
    value = parse_json_frame(raw)
    if not isinstance(value, dict):
        raise ProtocolError("request-not-object", "request must be an object")
    _request_id(value)
    source = value.get("source")
    if source is not None:
        if not isinstance(source, str):
            raise ProtocolError("source-not-string", "source must be a string")
        if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise ProtocolError("source-too-large", "source exceeds 24 KiB")
    return value


def validate_response_frame(raw: bytes, request_id: str) -> dict[str, Any]:
    value = parse_json_frame(raw)
    if not isinstance(value, dict):
        raise ProtocolError("response-not-object", "response must be an object")
    if value.get("protocol_id") != RESPONSE_PROTOCOL_ID:
        raise ProtocolError("protocol-mismatch", "response protocol_id differs")
    if value.get("request_id") != request_id:
        raise ProtocolError("response-request-id-mismatch", "response request_id differs")
    if not isinstance(value.get("status"), str) or not value["status"]:
        raise ProtocolError("response-status", "response status is missing")
    return value


def as_fraction(value: Any, label: str = "value") -> Fraction:
    """Convert a finite exact decimal/integer token to a rational."""
    if isinstance(value, bool):
        raise Phase3Error("number", f"{label} is boolean")
    if isinstance(value, Fraction):
        if value.numerator.bit_length() > 8192 or value.denominator.bit_length() > 8192:
            raise Phase3Error("numeric-token-too-large", f"{label} rational exceeds bound")
        return value
    if isinstance(value, Decimal):
        try:
            checked = bounded_decimal(str(value))
        except ProtocolError as error:
            raise Phase3Error(error.code, f"{label}: {error.detail}") from error
        return Fraction(checked)
    if isinstance(value, int):
        if value.bit_length() > 640:
            raise Phase3Error("numeric-significand-too-large", f"{label} integer exceeds bound")
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise Phase3Error("nonfinite", f"{label} is non-finite")
        return Fraction.from_float(value)
    if isinstance(value, str):
        try:
            decimal = bounded_decimal(value)
        except ProtocolError as error:
            raise Phase3Error(error.code, f"{label}: {error.detail}") from error
        return Fraction(decimal)
    raise Phase3Error("number", f"{label} is not numeric")


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _floor_fraction(value: Fraction, denominator: int) -> int:
    return value.numerator * denominator // value.denominator


def _ceil_fraction(value: Fraction, denominator: int) -> int:
    return -((-value.numerator * denominator) // value.denominator)


def decimal_outward(value: Fraction, direction: str, places: int = INTERVAL_DECIMAL_PLACES) -> str:
    if value < 0 or direction not in {"lower", "upper"}:
        raise Phase3Error("interval", "outward endpoint requires nonnegative value and direction")
    scale = 10**places
    integer = _floor_fraction(value, scale) if direction == "lower" else _ceil_fraction(value, scale)
    whole, remainder = divmod(integer, scale)
    if remainder == 0:
        return str(whole)
    return f"{whole}.{remainder:0{places}d}".rstrip("0")


@dataclass(frozen=True)
class RationalInterval:
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if self.lower < 0 or self.upper < self.lower:
            raise Phase3Error("interval", "invalid interval bounds")

    @property
    def width(self) -> Fraction:
        return self.upper - self.lower

    @property
    def radius(self) -> Fraction:
        return self.width / 2

    @property
    def singleton(self) -> bool:
        return self.lower == self.upper

    def contains(self, value: Fraction) -> bool:
        return self.lower <= value <= self.upper

    def straddles(self, value: Fraction) -> bool:
        return self.lower < value < self.upper

    def as_dict(self, *, quantity: str | None = None, method: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "lower": decimal_outward(self.lower, "lower"),
            "upper": decimal_outward(self.upper, "upper"),
            "lower_exact": fraction_text(self.lower),
            "upper_exact": fraction_text(self.upper),
            "certified": True,
            "radius_upper": decimal_outward(self.radius, "upper"),
        }
        if quantity is not None:
            result["quantity"] = quantity
        if method is not None:
            result["method"] = method
        return result


def directed_sqrt_bounds(value: Fraction, precision_bits: int = SQRT_PRECISION_BITS) -> tuple[Fraction, Fraction]:
    """Bound sqrt(value) using integer arithmetic only."""
    if value < 0:
        raise Phase3Error("sqrt-negative", "square-root radicand is negative")
    if value == 0:
        return Fraction(0), Fraction(0)
    nroot = math.isqrt(value.numerator)
    droot = math.isqrt(value.denominator)
    if nroot * nroot == value.numerator and droot * droot == value.denominator:
        exact = Fraction(nroot, droot)
        return exact, exact
    scale = 1 << precision_bits
    floor_scaled = math.isqrt((value.numerator * scale * scale) // value.denominator)
    lower = Fraction(floor_scaled, scale)
    upper = Fraction(floor_scaled + 1, scale)
    if lower * lower > value or upper * upper < value:
        raise Phase3Error("sqrt-enclosure", "integer-isqrt enclosure failed")
    return lower, upper


def bits_to_float(bits: str) -> float:
    if not isinstance(bits, str) or len(bits) != 18 or not bits.startswith("0x"):
        raise Phase3Error("binary64", "bits must be 0x followed by 16 hex digits")
    try:
        integer = int(bits[2:], 16)
    except ValueError as error:
        raise Phase3Error("binary64", "invalid binary64 hex") from error
    value = struct.unpack(">d", integer.to_bytes(8, "big"))[0]
    if not math.isfinite(value):
        raise Phase3Error("binary64-nonfinite", "binary64 witness must be finite")
    return value


def float_to_bits(value: float) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise Phase3Error("binary64", "value must be finite")
    return f"0x{struct.unpack('>Q', struct.pack('>d', float(value)))[0]:016x}"


def fraction_to_binary64_bits(value: Fraction, label: str = "value") -> str:
    """Round an exact rational to binary64 using host-independent integer math."""
    if value == 0:
        return "0x0000000000000000"
    sign = 1 if value < 0 else 0
    magnitude = abs(value)
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if exponent >= 0 and Fraction(1 << exponent) > magnitude:
        exponent -= 1
    elif exponent < 0 and Fraction(1, 1 << -exponent) > magnitude:
        exponent -= 1

    def round_even(numerator: int, denominator: int) -> int:
        quotient, remainder = divmod(numerator, denominator)
        twice = remainder * 2
        if twice > denominator or (twice == denominator and quotient & 1):
            quotient += 1
        return quotient

    if exponent < -1022:
        scaled = magnitude * (1 << 1074)
        significand = round_even(scaled.numerator, scaled.denominator)
        if significand == 0:
            return f"0x{sign << 63:016x}"
        if significand >= 1 << 52:
            return f"0x{(sign << 63) | (1 << 52):016x}"
        return f"0x{(sign << 63) | significand:016x}"
    scale = 52 - exponent
    scaled = magnitude * (1 << scale) if scale >= 0 else magnitude / (1 << -scale)
    significand = round_even(scaled.numerator, scaled.denominator)
    if significand == 1 << 53:
        significand >>= 1
        exponent += 1
    if exponent > 1023:
        raise Phase3Error("binary64-overflow", f"{label} rounds to infinity")
    bits = (sign << 63) | ((exponent + 1023) << 52) | (significand - (1 << 52))
    return f"0x{bits:016x}"


def interval_from_decimal(value: Mapping[str, Any], label: str = "interval") -> RationalInterval:
    if not isinstance(value, Mapping):
        raise Phase3Error("interval", f"{label} must be an object")
    lower = as_fraction(value.get("lower"), f"{label}.lower")
    upper = as_fraction(value.get("upper"), f"{label}.upper")
    return RationalInterval(lower, upper)

#!/usr/bin/env python3
"""Deterministic six-case development extension for EXP-0002.

This is deliberately a separate corpus and materializer.  It does not import
or modify the 16-case development corpus.  The only per-case source change is
the lexical token used for the ``tail_root`` x translation; all graph, basis,
and transform changes belong to the named built-in variant.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

PACKAGE = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE.parents[2]
CORPUS_PATH = PACKAGE / "corpora" / "development-extension" / "corpus.json"
BASE_FIXTURE = "examples/body-documents/stylized-digitigrade-biped.json"
BASE_SHA256 = "49937955d25538bc9546689427022ce71776192834ec829b8dc005bb4518a66f"
PARENT_CORPUS_ID = "ck.exp-0002.r3-authored-conflict-development-corpus-1"
SCHEMA = "ck.exp-0002.r3-authored-conflict-development-extension-corpus-1"
CORPUS_ID = SCHEMA
CORPUS_ROLE = "development"
SWEEP_ID = "ck.exp-0002.r3-authored-conflict-sweep-1"
SWEEP_PATH = "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/profiles/development-sweep.json"
SWEEP_SHA256 = "b4e124988cff891c66166ee95024be1a8d6c545ddded1415c428cc681c03b173"
VARIANT_ID = "descendant-tail-end-v1"
MATERIALIZATION_FORMAT = "json-development-extension-generated-v1"
CASE_IDS = (
    "strict-boundary",
    "strict-successor",
    "micro-boundary",
    "micro-successor",
    "stress-boundary",
    "stress-successor",
)
PROFILE_IDS = {
    "strict": "ck.provisional-r3-authored-conflict.dev.strict-1",
    "micro": "ck.provisional-r3-authored-conflict.dev.micro-1",
    "stress": "ck.provisional-r3-authored-conflict.dev.stress-1",
}
PROFILE_BITS = {
    "strict": {"A": "0x3cf0000000000000", "R": "0x3d10000000000000", "H": "0x3d10000000000000"},
    "micro": {"A": "0x3eb0000000000000", "R": "0x3d70000000000000", "H": "0x3eb0000000000000"},
    "stress": {"A": "0x3f50000000000000", "R": "0x3df0000000000000", "H": "0x3f30000000000000"},
}
MAX_CORPUS_BYTES = 96 * 1024
MAX_SOURCE_BYTES = 24 * 1024
MAX_RESOURCE_BYTES = 24 * 1024
MAX_CASES = 6
MIN_CASES = 6


class CorpusValidationError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")


class RawNumber(str):
    """A validated finite decimal token retained verbatim by the encoder."""


def _fail(code: str, detail: str) -> None:
    raise CorpusValidationError(code, detail)


def _bits_fraction(bits: str) -> Fraction:
    value = int(bits[2:], 16)
    sign = -1 if value >> 63 else 1
    exponent = (value >> 52) & 0x7FF
    fraction = value & ((1 << 52) - 1)
    if exponent == 0x7FF:
        _fail("nonfinite", f"bits {bits} is non-finite")
    if exponent == 0:
        significand, power = fraction, -1074
    else:
        significand, power = (1 << 52) | fraction, exponent - 1023 - 52
    return sign * Fraction(significand) * (Fraction(2) ** power)


def _round_even(q: int, r: int, denominator: int) -> int:
    if r * 2 < denominator or (r * 2 == denominator and q % 2 == 0):
        return q
    return q + 1


def exact_rn_even_bits(value: Fraction) -> int:
    """Independent exact rational round-to-nearest/even binary64 conversion."""
    if value == 0:
        return 0
    sign = 1 if value < 0 else 0
    value = abs(value)
    # Find floor(log2(value)) without a floating-point intermediate.
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if exponent >= 0 and Fraction(1 << exponent) > value:
        exponent -= 1
    elif exponent < 0 and Fraction(1, 1 << -exponent) > value:
        exponent -= 1
    if exponent < -1022:
        scaled = value * (1 << 1074)
        q, r = divmod(scaled.numerator, scaled.denominator)
        significand = _round_even(q, r, scaled.denominator)
        if significand == 0:
            return sign << 63
        if significand >= 1 << 52:
            return (sign << 63) | (1 << 52)
        return (sign << 63) | significand
    scale = 52 - exponent
    scaled = value * (1 << scale) if scale >= 0 else value / (1 << -scale)
    q, r = divmod(scaled.numerator, scaled.denominator)
    significand = _round_even(q, r, scaled.denominator)
    if significand == 1 << 53:
        significand >>= 1
        exponent += 1
    if exponent > 1023:
        _fail("overflow", "exact conversion overflows finite binary64")
    return (sign << 63) | ((exponent + 1023) << 52) | (significand - (1 << 52))


def _bits_float(bits: int) -> float:
    return struct.unpack(">d", bits.to_bytes(8, "big"))[0]


def _bits_text(bits: int) -> str:
    return f"0x{bits:016x}"


def _decimal_token(value: Fraction) -> str:
    """Render a finite decimal expansion exactly, without float conversion."""
    sign = "-" if value < 0 else ""
    value = abs(value)
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        _fail("decimal-construction", "source token denominator is not finite decimal")
    places = max(twos, fives)
    numerator = value.numerator * (2 ** (places - twos)) * (5 ** (places - fives))
    digits = str(numerator)
    if places == 0:
        return sign + digits
    if len(digits) <= places:
        digits = "0" * (places + 1 - len(digits)) + digits
    result = digits[:-places] + "." + digits[-places:]
    result = result.rstrip("0").rstrip(".")
    return sign + (result or "0")


def _fraction_number(token: str) -> Fraction:
    try:
        parsed = Decimal(token)
    except Exception as exc:  # pragma: no cover - guarded corpus data
        _fail("decimal-token", f"invalid token {token!r}: {exc}")
    if not parsed.is_finite():
        _fail("decimal-token", "token must be finite")
    return Fraction(parsed)


def _qmul(a: tuple[Fraction, ...], b: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    )


def _qinv(q: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    return (-q[0], -q[1], -q[2], q[3])


def _qrot(q: tuple[Fraction, ...], v: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    return _qmul(_qmul(q, (*v, Fraction(0))), _qinv(q))[:3]


def _compose(a: tuple[tuple[Fraction, ...], tuple[Fraction, ...]], b: tuple[tuple[Fraction, ...], tuple[Fraction, ...]]):
    return (tuple(x + y for x, y in zip(_qrot(a[1], b[0]), a[0])), _qmul(a[1], b[1]))


def _source_translation(values: tuple[Fraction, Fraction, Fraction]) -> tuple[Fraction, ...]:
    # Fixed variant basis: C maps source [-Y,+Z,+X] to canonical [X,Y,Z].
    return (-values[1] / 100, values[2] / 100, values[0] / 100)


QX = (Fraction(1), Fraction(0), Fraction(0), Fraction(0))
QY = (Fraction(0), Fraction(-1), Fraction(0), Fraction(0))
QZ = (Fraction(0), Fraction(0), Fraction(-1), Fraction(0))
FIXED_SOURCE = {
    "host_translation": (Fraction(50), Fraction(25, 2), Fraction(75, 2)),
    "mating_translation": (Fraction(25, 2), Fraction(25), Fraction(75, 2)),
    "offset_translation": (Fraction(25, 2), Fraction(25), Fraction(75, 2)),
    "tail_tip_translation": (Fraction(25, 2), Fraction(25), Fraction(75, 2)),
    "tail_end_translation": (Fraction(25), Fraction(25, 2), Fraction(75, 2)),
}


def derived_canonical_transform() -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    host = (_source_translation(FIXED_SOURCE["host_translation"]), QY)
    offset = (_source_translation(FIXED_SOURCE["offset_translation"]), QZ)
    tip = (_source_translation(FIXED_SOURCE["tail_tip_translation"]), QY)
    end = (_source_translation(FIXED_SOURCE["tail_end_translation"]), QZ)
    mating = (_source_translation(FIXED_SOURCE["mating_translation"]), QX)
    root_to_mating = _compose(_compose(tip, end), mating)
    inverse = (tuple(-x for x in _qrot(_qinv(root_to_mating[1]), root_to_mating[0])), _qinv(root_to_mating[1]))
    return _compose(_compose(host, offset), inverse)


DERIVED_TRANSLATION, DERIVED_ROTATION = derived_canonical_transform()
DERIVED_COMPONENT = DERIVED_TRANSLATION[2]
ROOT_FIXED_Y = -100 * DERIVED_TRANSLATION[0]
ROOT_FIXED_Z = 100 * DERIVED_TRANSLATION[1]


def _profile_fraction(candidate: str, field: str) -> Fraction:
    return _bits_fraction(PROFILE_BITS[candidate][field])


def boundary_fraction(candidate: str) -> Fraction:
    """Solve the positive-side inclusive predicate for authored ``a > d``."""
    a, r = _profile_fraction(candidate, "A"), _profile_fraction(candidate, "R")
    d = DERIVED_COMPONENT
    return d + (a + r * d) / (1 - r)


def boundary_bits(candidate: str) -> tuple[int, int]:
    target = boundary_fraction(candidate)
    bits = exact_rn_even_bits(target)
    target_bits_fraction = _bits_fraction(_bits_text(bits))
    while target_bits_fraction > target:
        bits -= 1
        target_bits_fraction = _bits_fraction(_bits_text(bits))
    while _bits_fraction(_bits_text(bits + 1)) <= target:
        bits += 1
    return bits, bits + 1


def source_token_for_bits(bits: int) -> str:
    token = _decimal_token(_bits_fraction(_bits_text(bits)) * 100)
    # Independent proof: exact source metres conversion rounds to target bits.
    if exact_rn_even_bits(_fraction_number(token) / 100) != bits:
        _fail("source-binding", "source token does not bind target binary64")
    return token


class _DuplicateKey(Exception):
    pass


def _parse_json(raw: bytes) -> dict[str, Any]:
    def pairs(items):
        out = {}
        for key, val in items:
            if key in out:
                raise _DuplicateKey(key)
            out[key] = val
        return out
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_float=Decimal, parse_int=int)
    except (_DuplicateKey, ValueError, UnicodeDecodeError) as exc:
        _fail("json", str(exc))
    if not isinstance(value, dict):
        _fail("json", "top-level value must be object")
    return value


def _canonical_json(value: Any) -> str:
    if isinstance(value, RawNumber):
        return str(value)
    if value is None: return "null"
    if value is True: return "true"
    if value is False: return "false"
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, int): return str(value)
    if isinstance(value, float): return json.dumps(value, allow_nan=False, separators=(",", ":"))
    if isinstance(value, str): return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    if isinstance(value, list): return "[" + ",".join(_canonical_json(v) for v in value) + "]"
    if isinstance(value, dict): return "{" + ",".join(_canonical_json(str(k)) + ":" + _canonical_json(value[k]) for k in sorted(value)) + "}"
    _fail("json-value", f"unsupported {type(value).__name__}")
    return ""


def _fixture_raw(repo_root: Path) -> tuple[bytes, dict[str, Any]]:
    path = repo_root / BASE_FIXTURE
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA256:
        _fail("fixture-hash", "base fixture hash changed")
    return raw, _parse_json(raw)


def _find(records: list[dict[str, Any]], role: str, anchors: list[str] | None = None) -> dict[str, Any]:
    for record in records:
        address = record.get("address", {})
        if address.get("role") == role and (anchors is None or address.get("anchors") == anchors):
            return record
    _fail("variant", f"missing {role} {anchors}")


def _variant_source(base: dict[str, Any], token: str) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result["basis"] = {"length_unit": "centimetre", "handedness": "left", "up": "+z", "forward": "+x"}
    body = result["body"]
    root = _find(body["parts"], "tail_root", ["tail"])
    tip = _find(body["parts"], "tail_tip", ["tail"])
    root["placement"] = {"translation": [RawNumber(token), RawNumber(_decimal_token(ROOT_FIXED_Y)), RawNumber(_decimal_token(ROOT_FIXED_Z))], "rotation_xyzw": [0, 1, 0, 0]}
    tip["placement"] = {"translation": [Decimal("12.5"), Decimal("25"), Decimal("37.5")], "rotation_xyzw": [0, 0, 1, 0]}
    end = {"address": {"namespace": "main", "anchors": ["tail", "end"], "kind": "part", "role": "tail_end"}, "containment": {"parent": {"namespace": "main", "anchors": ["tail"], "kind": "part", "role": "tail_tip"}}, "placement": {"translation": [Decimal("25"), Decimal("12.5"), Decimal("37.5")], "rotation_xyzw": [1, 0, 0, 0]}}
    body["parts"].append(end)
    body["joints"].append({"address": {"namespace": "main", "anchors": ["tail", "end"], "kind": "joint", "role": "tip_end"}, "proximal": {"namespace": "main", "anchors": ["tail"], "kind": "part", "role": "tail_tip"}, "distal": {"namespace": "main", "anchors": ["tail", "end"], "kind": "part", "role": "tail_end"}, "proximal_frame": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}, "distal_frame": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}})
    host = _find(body["sockets"], "tail_mount", [])
    mating = _find(body["sockets"], "tail_mount", ["tail"])
    host["interface_frame"] = {"translation": [Decimal("50"), Decimal("12.5"), Decimal("37.5")], "rotation_xyzw": [0, 0, 1, 0]}
    mating["owner"] = {"namespace": "main", "anchors": ["tail", "end"], "kind": "part", "role": "tail_end"}
    mating["interface_frame"] = {"translation": [Decimal("12.5"), Decimal("25"), Decimal("37.5")], "rotation_xyzw": [0, 1, 0, 0]}
    body["attachments"][0]["offset"] = {"translation": [Decimal("12.5"), Decimal("25"), Decimal("37.5")], "rotation_xyzw": [1, 0, 0, 0]}
    for region in body["regions"]:
        if region.get("address", {}).get("role") == "tail":
            region["parts"].append({"namespace": "main", "anchors": ["tail", "end"], "kind": "part", "role": "tail_end"})
    for capability in body["capabilities"]:
        if capability.get("address", {}).get("role") == "tail_motion":
            capability["subjects"].append({"namespace": "main", "anchors": ["tail", "end"], "kind": "part", "role": "tail_end"})
    return result


def materialize_case(case: Mapping[str, Any], repo_root: Path | str = REPO_ROOT) -> bytes:
    if case.get("variant_id") != VARIANT_ID:
        _fail("unknown-variant", str(case.get("variant_id")))
    token = case.get("source_token")
    if not isinstance(token, str) or _decimal_token(_fraction_number(token)) != token:
        _fail("source-token", "source_token must be its exact finite decimal spelling")
    _, base = _fixture_raw(Path(repo_root))
    output = (_canonical_json(_variant_source(base, token)) + "\n").encode("utf-8")
    if len(output) > MAX_SOURCE_BYTES:
        _fail("source-bytes", "materialized source exceeds bound")
    return output


def _expected_for_case(case_index: int) -> dict[str, str]:
    candidate = CASE_IDS[case_index].split("-")[0]
    direction = CASE_IDS[case_index].split("-")[1]
    bits = boundary_bits(candidate)[0 if direction == "boundary" else 1]
    authored = _bits_fraction(_bits_text(bits))
    result = {}
    for candidate_id in PROFILE_IDS:
        a, r = _profile_fraction(candidate_id, "A"), _profile_fraction(candidate_id, "R")
        d = DERIVED_COMPONENT
        result[PROFILE_IDS[candidate_id]] = "agree" if abs(authored - d) <= a + r * max(abs(authored), abs(d)) else "conflict"
    return result


def validate_corpus(corpus: Mapping[str, Any], repo_root: Path | str = REPO_ROOT) -> dict[str, Any]:
    required = {"schema", "corpus_id", "corpus_role", "parent_corpus_id", "sweep_id", "sweep_path", "sweep_sha256", "variant", "base_fixture", "materialization", "limits", "cases", "corpus_identity"}
    if set(corpus) != required:
        _fail("schema-fields", "extension corpus fields differ")
    if corpus["schema"] != SCHEMA or corpus["corpus_id"] != CORPUS_ID or corpus["corpus_role"] != CORPUS_ROLE or corpus["parent_corpus_id"] != PARENT_CORPUS_ID or corpus["sweep_id"] != SWEEP_ID or corpus["sweep_path"] != SWEEP_PATH or corpus["sweep_sha256"] != SWEEP_SHA256:
        _fail("identity", "extension identity differs")
    variant = corpus["variant"]
    if not isinstance(variant, dict) or variant.get("id") != VARIANT_ID or variant.get("operation") != "built-in-descendant-tail-end-v1":
        _fail("variant", "unknown or malformed variant")
    base = corpus["base_fixture"]
    if base != {"path": BASE_FIXTURE, "sha256": BASE_SHA256}:
        _fail("base-fixture", "base fixture identity differs")
    limits = corpus["limits"]
    if limits != {"max_cases": MAX_CASES, "source_bytes": MAX_SOURCE_BYTES, "resource_bytes": MAX_RESOURCE_BYTES}:
        _fail("limits", "resource bounds differ")
    if corpus["materialization"] != {"format": MATERIALIZATION_FORMAT, "hash": "sha256", "source_bytes": "materialized-source"}:
        _fail("materialization", "materialization declaration differs")
    cases = corpus["cases"]
    if not isinstance(cases, list) or len(cases) != 6 or tuple(c["case_id"] for c in cases) != CASE_IDS:
        _fail("case-order", "exact six case order is required")
    for index, case in enumerate(cases):
        if set(case) != {"case_id", "variant_id", "source_token", "target_bits", "boundary_fraction", "expected", "materialized_sha256", "source_bytes"}:
            _fail("case-fields", f"{CASE_IDS[index]} fields differ")
        if case["variant_id"] != VARIANT_ID:
            _fail("unknown-variant", case["case_id"])
        candidate = CASE_IDS[index].split("-")[0]
        direction = CASE_IDS[index].split("-")[1]
        bbits = boundary_bits(candidate)
        expected_bits = bbits[0 if direction == "boundary" else 1]
        if case["target_bits"] != _bits_text(expected_bits) or case["boundary_fraction"] != f"{boundary_fraction(candidate).numerator}/{boundary_fraction(candidate).denominator}":
            _fail("oracle", f"{case['case_id']} boundary binding differs")
        if case["source_token"] != source_token_for_bits(expected_bits):
            _fail("source-binding", case["case_id"])
        source = materialize_case(case, repo_root)
        if len(source) != case["source_bytes"] or len(source) > MAX_SOURCE_BYTES or hashlib.sha256(source).hexdigest() != case["materialized_sha256"]:
            _fail("materialized-hash", case["case_id"])
        if case["expected"] != {profile: {"classification": c, "cause": None} for profile, c in _expected_for_case(index).items()}:
            _fail("expectation", case["case_id"])
    identity = corpus["corpus_identity"]
    if not isinstance(identity, dict) or set(identity) != {"algorithm", "basis", "content_sha256"} or identity["algorithm"] != "sha256" or identity["basis"] != "canonical-json-without-corpus-identity":
        _fail("corpus-identity", "identity declaration differs")
    without = dict(corpus)
    without.pop("corpus_identity")
    expected_hash = hashlib.sha256((_canonical_json(without) + "\n").encode()).hexdigest()
    if identity["content_sha256"] != expected_hash:
        _fail("corpus-identity", "content digest mismatch")
    return dict(corpus)


def load_development_extension_corpus(path: Path | str = CORPUS_PATH, repo_root: Path | str = REPO_ROOT) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if len(raw) > MAX_CORPUS_BYTES:
        _fail("corpus-bytes", "corpus exceeds bound")
    return validate_corpus(_parse_json(raw), repo_root)


# Explicit aliases keep the extension convenient for focused consumers while
# retaining the role-specific name used by the corpus package.
load_corpus = load_development_extension_corpus
validate_extension_corpus = validate_corpus


if __name__ == "__main__":
    value = load_development_extension_corpus()
    print(f"valid development extension corpus: cases={len(value['cases'])}; variant={VARIANT_ID}")

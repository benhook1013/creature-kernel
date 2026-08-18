#!/usr/bin/env python3
"""Bounded, non-executing loader for the EXP-0002 development corpus.

The corpus is an authored input package only.  This module never selects a
profile, invokes the Rust candidate, or creates an evidence result.  It checks
closed JSON Pointer-like replacements, independently proves numeric oracle
claims, and materializes deterministic JSON source bytes for a later runner.
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

import profile_sweep


PACKAGE = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE.parents[2]
CORPUS_PATH = PACKAGE / "corpora" / "development" / "corpus.json"
SCHEMA = "ck.exp-0002.r3-authored-conflict-development-corpus-1"
CORPUS_ID = "ck.exp-0002.r3-authored-conflict-development-corpus-1"
CORPUS_ROLE = "development"
BASE_FIXTURE = "examples/body-documents/stylized-digitigrade-biped.json"
BASE_SHA256 = "49937955d25538bc9546689427022ce71776192834ec829b8dc005bb4518a66f"
MATERIALIZATION_FORMAT = "json-development-generated-v1"
MAX_CORPUS_BYTES = 96 * 1024
MAX_CASES = 16
MIN_CASES = 14
MAX_MUTATIONS = 8
MAX_POINTER_PARTS = 24
MAX_JSON_DEPTH = 24
# The candidate transport admits at most 24 KiB of decoded source bytes.
MAX_SOURCE_BYTES = 24 * 1024
MIN_ROTATION_MARGIN = Fraction(1, 10**24)
PROFILE_IDS = tuple(profile_sweep.PROFILE_IDS[candidate] for candidate in profile_sweep.CANDIDATE_IDS)
TOLERANCE_FIELDS = ("translation_absolute", "translation_relative", "rotation_half_chord")
PROVIDERS = ("gate", "arithmetic", "sqrt", "environment")
ENVIRONMENT = "unattested-no-probe-v1"
CASE_IDS = frozenset(
    {
        "baseline-equation-agree",
        "translation-strict-boundary",
        "translation-strict-nextafter",
        "translation-micro-boundary",
        "translation-micro-nextafter",
        "translation-stress-boundary",
        "translation-stress-nextafter",
        "translation-broad-conflict",
        "quaternion-sign-equivalence",
        "rotation-strict-vs-wide",
        "rotation-wide-vs-stress",
        "arithmetic-provider-unavailable",
        "gate-input-reject",
        "sqrt-provider-unavailable",
        "zero-quaternion-input",
        "negative-relative-override",
    }
)

PART_TAIL_ROOT_TRANSLATION_Z = "/body/parts/16/placement/translation/2"
HOST_SOCKET_TRANSLATION_Z = "/body/sockets/0/interface_frame/translation/2"
PART_TAIL_ROOT_ROTATION = "/body/parts/16/placement/rotation_xyzw"
HOST_SOCKET_ROTATION = "/body/sockets/0/interface_frame/rotation_xyzw"
PELVIS_ROTATION = "/body/parts/0/placement/rotation_xyzw"
POS_ZERO_BITS = "0x0000000000000000"
POS_ONE_BITS = "0x3ff0000000000000"
NEG_ONE_BITS = "0xbff0000000000000"
FRAME_VALUE_QUATERNION_CODE = "ck.provisional-r3-authored-conflict.frame-value.quaternion"
INVALID_PROFILE_CODE = "ck.provisional-r3-authored-conflict.numeric-comparison.invalid-profile"
NATIVE_PROVIDERS = {
    "gate": "allow",
    "arithmetic": "native",
    "sqrt": "native",
    "environment": ENVIRONMENT,
}


def _case_contract(
    family: str,
    expectation_basis: str,
    mutation: str,
    providers: Mapping[str, str],
    tolerance_override: Mapping[str, Any] | None,
    oracle_kind: str,
    expected_classification: str | None = None,
    expected_cause: Mapping[str, Any] | None = None,
    oracle_candidate_id: str | None = None,
    oracle_direction: str | None = None,
    oracle_z_bits: str | None = None,
    oracle_min_margin: Fraction | None = None,
) -> dict[str, Any]:
    return {
        "family": family,
        "expectation_basis": expectation_basis,
        "mutation": mutation,
        "providers": dict(providers),
        "tolerance_override": None if tolerance_override is None else dict(tolerance_override),
        "oracle_kind": oracle_kind,
        "oracle_candidate_id": oracle_candidate_id,
        "oracle_direction": oracle_direction,
        "oracle_z_bits": oracle_z_bits,
        "oracle_min_margin": oracle_min_margin,
        "expected_classification": expected_classification,
        "expected_cause": None if expected_cause is None else dict(expected_cause),
    }


CASE_CONTRACTS: dict[str, dict[str, Any]] = {
    "baseline-equation-agree": _case_contract(
        "baseline-equation", "independent-exact", "none", NATIVE_PROVIDERS, None, "none", "agree"
    ),
    "translation-strict-boundary": _case_contract(
        "translation-boundary", "independent-exact", "translation-boundary", NATIVE_PROVIDERS, None, "translation-boundary",
        oracle_candidate_id="strict", oracle_direction="at-or-below"
    ),
    "translation-strict-nextafter": _case_contract(
        "translation-boundary", "independent-exact", "translation-boundary", NATIVE_PROVIDERS, None, "translation-boundary",
        oracle_candidate_id="strict", oracle_direction="nextafter-above"
    ),
    "translation-micro-boundary": _case_contract(
        "translation-boundary", "independent-exact", "translation-boundary", NATIVE_PROVIDERS, None, "translation-boundary",
        oracle_candidate_id="micro", oracle_direction="at-or-below"
    ),
    "translation-micro-nextafter": _case_contract(
        "translation-boundary", "independent-exact", "translation-boundary", NATIVE_PROVIDERS, None, "translation-boundary",
        oracle_candidate_id="micro", oracle_direction="nextafter-above"
    ),
    "translation-stress-boundary": _case_contract(
        "translation-boundary", "independent-exact", "translation-boundary", NATIVE_PROVIDERS, None, "translation-boundary",
        oracle_candidate_id="stress", oracle_direction="at-or-below"
    ),
    "translation-stress-nextafter": _case_contract(
        "translation-boundary", "independent-exact", "translation-boundary", NATIVE_PROVIDERS, None, "translation-boundary",
        oracle_candidate_id="stress", oracle_direction="nextafter-above"
    ),
    "translation-broad-conflict": _case_contract(
        "translation-conflict", "independent-exact", "translation-broad", NATIVE_PROVIDERS, None, "none", "conflict"
    ),
    "quaternion-sign-equivalence": _case_contract(
        "rotation-sign-equivalence", "independent-exact", "quaternion-sign", NATIVE_PROVIDERS, None, "none", "agree"
    ),
    "rotation-strict-vs-wide": _case_contract(
        "rotation-margin", "independent-conservative", "rotation-margin", NATIVE_PROVIDERS, None, "rotation-margin",
        oracle_z_bits="0x3e70000000000000", oracle_min_margin=Fraction(1, 10**24)
    ),
    "rotation-wide-vs-stress": _case_contract(
        "rotation-margin", "independent-conservative", "rotation-margin", NATIVE_PROVIDERS, None, "rotation-margin",
        oracle_z_bits="0x3f1a36e2eb1c432d", oracle_min_margin=Fraction(1, 10**24)
    ),
    "arithmetic-provider-unavailable": _case_contract(
        "typed-provider-failure",
        "contract-order",
        "none",
        {**NATIVE_PROVIDERS, "arithmetic": "unavailable"},
        None,
        "none",
        "skipped",
        {
            "code": FRAME_VALUE_QUATERNION_CODE,
            "failure": "provider-unavailable",
            "operation": "div",
            "stage": "scaled-component",
            "index": 0,
        },
    ),
    "gate-input-reject": _case_contract(
        "typed-provider-failure",
        "contract-order",
        "none",
        {**NATIVE_PROVIDERS, "gate": "reject"},
        None,
        "none",
        "skipped",
        {"code": FRAME_VALUE_QUATERNION_CODE, "failure": "gate-rejected", "stage": "input"},
    ),
    "sqrt-provider-unavailable": _case_contract(
        "typed-provider-failure",
        "contract-order",
        "none",
        {**NATIVE_PROVIDERS, "sqrt": "unavailable"},
        None,
        "none",
        "skipped",
        {"code": FRAME_VALUE_QUATERNION_CODE, "failure": "sqrt-unavailable"},
    ),
    "zero-quaternion-input": _case_contract(
        "typed-input-failure",
        "contract-order",
        "zero-quaternion",
        NATIVE_PROVIDERS,
        None,
        "none",
        "skipped",
        {"code": FRAME_VALUE_QUATERNION_CODE, "failure": "zero-quaternion"},
    ),
    "negative-relative-override": _case_contract(
        "top-level-tolerance-rejection",
        "contract-order",
        "none",
        NATIVE_PROVIDERS,
        {"translation_relative": -1},
        "none",
        "rejected",
        {"code": INVALID_PROFILE_CODE, "failure": "negative", "field": "translation-relative"},
    ),
}


class CorpusValidationError(ValueError):
    """A stable, machine-readable corpus definition failure."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _DuplicateKey(Exception):
    pass


def _fail(code: str, detail: str) -> None:
    raise CorpusValidationError(code, detail)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("wrong-type", f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("wrong-type", f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _fail("wrong-type", f"{label} must be a string")
    if not value:
        _fail("empty-value", f"{label} must not be empty")
    return value


def _exact_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing:
        _fail("missing-field", f"{label}: {','.join(missing)}")
    if extra:
        _fail("extra-field", f"{label}: {','.join(extra)}")


def _walk(value: Any, depth: int = 0, label: str = "corpus") -> None:
    if depth > MAX_JSON_DEPTH:
        _fail("json-depth", f"{label} exceeds depth {MAX_JSON_DEPTH}")
    if isinstance(value, float) and not math.isfinite(value):
        _fail("nonfinite-value", f"{label} is not finite")
    if isinstance(value, Decimal) and not value.is_finite():
        _fail("nonfinite-value", f"{label} is not finite")
    if isinstance(value, dict):
        for key, child in value.items():
            _walk(child, depth + 1, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, depth + 1, f"{label}[{index}]")


def _parse(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("invalid-utf8", str(exc))

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _DuplicateKey(key)
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except _DuplicateKey as exc:
        _fail("duplicate-key", f"duplicate object member {exc}")
    except (ValueError, json.JSONDecodeError, RecursionError) as exc:
        _fail("invalid-json", str(exc))
    _walk(value)
    return _object(value, "corpus")


def _read_regular(path: Path, limit: int, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        _fail("file-type", f"{label} must be a regular non-symlink file")
    # Check every existing component to avoid accepting a symlinked directory.
    current = path
    while current != current.parent:
        if current.is_symlink():
            _fail("symlink", f"{label} contains a symlink component")
        current = current.parent
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError as exc:
        _fail("file-read", f"{label}: {exc}")
    if len(raw) > limit:
        _fail("file-too-large", f"{label} exceeds {limit} bytes")
    return raw


def _number(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal, float)):
        _fail("wrong-type", f"{label} must be a JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        _fail("nonfinite-value", f"{label} is not finite")
    if isinstance(value, Decimal) and not value.is_finite():
        _fail("nonfinite-value", f"{label} is not finite")


def _number_fraction(value: Any, label: str) -> Fraction:
    _number(value, label)
    if isinstance(value, Decimal):
        return Fraction(value)
    if isinstance(value, int):
        return Fraction(value)
    return Fraction.from_float(value)


def _bits_float(bits: str, label: str) -> float:
    if len(bits) != 18 or not bits.startswith("0x") or any(c not in "0123456789abcdef" for c in bits[2:]):
        _fail("bits-format", f"{label} must be 0x plus 16 lowercase hexadecimal digits")
    integer = int(bits[2:], 16)
    if integer >> 63:
        _fail("negative-value", f"{label} has its sign bit set")
    if (integer >> 52) & 0x7FF == 0x7FF:
        _fail("nonfinite-value", f"{label} is NaN or infinity")
    try:
        return struct.unpack(">d", integer.to_bytes(8, "big"))[0]
    except (OverflowError, struct.error) as exc:
        _fail("bits-format", f"{label} is not a binary64 value: {exc}")
    raise AssertionError("unreachable")


def _float_bits(value: float) -> str:
    return "0x" + struct.pack(">d", value).hex()


def _pointer(path: str, label: str) -> list[str]:
    if not path.startswith("/") or path == "/":
        _fail("pointer-format", f"{label} must be a non-root JSON Pointer")
    parts = path[1:].split("/")
    if len(parts) > MAX_POINTER_PARTS:
        _fail("pointer-depth", f"{label} exceeds {MAX_POINTER_PARTS} path parts")
    decoded: list[str] = []
    for part in parts:
        i = 0
        out = ""
        while i < len(part):
            if part[i] == "~":
                if i + 1 >= len(part) or part[i + 1] not in "01":
                    _fail("pointer-escape", f"{label} has an invalid escape")
                out += "~" if part[i + 1] == "0" else "/"
                i += 2
            else:
                out += part[i]
                i += 1
        if out in ("", ".", ".."):
            _fail("pointer-part", f"{label} contains an unsafe path part")
        decoded.append(out)
    return decoded


def _same_json_type(old: Any, new: Any) -> bool:
    if isinstance(old, bool) or isinstance(new, bool):
        return isinstance(old, bool) and isinstance(new, bool)
    if isinstance(old, (int, Decimal, float)) and isinstance(new, (int, Decimal, float)):
        return True
    return type(old) is type(new)


def _locate(root: Any, parts: list[str], label: str) -> tuple[Any, str]:
    current = root
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                _fail("missing-path", f"{label} does not exist")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or (part.startswith("0") and part != "0") or int(part) >= len(current):
                _fail("missing-path", f"{label} does not exist")
            current = current[int(part)]
        else:
            _fail("path-through-scalar", f"{label} traverses a scalar")
    return current, parts[-1]


def _replace(root: Any, path: str, value: Any, label: str) -> None:
    parts = _pointer(path, label)
    parent, key = _locate(root, parts, label)
    if isinstance(parent, dict):
        if key not in parent:
            _fail("missing-path", f"{label} does not exist")
        if not _same_json_type(parent[key], value):
            _fail("replacement-type", f"{label} changes the JSON value type")
        parent[key] = copy.deepcopy(value)
        return
    if isinstance(parent, list):
        if not key.isdigit() or (key.startswith("0") and key != "0") or int(key) >= len(parent):
            _fail("missing-path", f"{label} does not exist")
        index = int(key)
        if not _same_json_type(parent[index], value):
            _fail("replacement-type", f"{label} changes the JSON value type")
        parent[index] = copy.deepcopy(value)
        return
    _fail("path-through-scalar", f"{label} parent is a scalar")


def _lookup(root: Any, path: str, label: str) -> Any:
    """Read one already-materialized value through the closed pointer rules."""
    current = root
    for part in _pointer(path, label):
        if isinstance(current, dict):
            if part not in current:
                _fail("missing-path", f"{label} does not exist")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or (part.startswith("0") and part != "0") or int(part) >= len(current):
                _fail("missing-path", f"{label} does not exist")
            current = current[int(part)]
        else:
            _fail("path-through-scalar", f"{label} traverses a scalar")
    return current


def _json_value_equal(left: Any, right: Any, label: str) -> bool:
    """Compare JSON-shaped contract values, with numeric values by exact value."""
    left_is_number = isinstance(left, (int, Decimal, float)) and not isinstance(left, bool)
    right_is_number = isinstance(right, (int, Decimal, float)) and not isinstance(right, bool)
    if left_is_number or right_is_number:
        if not left_is_number or not right_is_number:
            return False
        return _number_fraction(left, label) == _number_fraction(right, label)
    if isinstance(left, list) or isinstance(right, list):
        if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
            return False
        return all(_json_value_equal(a, b, label) for a, b in zip(left, right))
    if isinstance(left, dict) or isinstance(right, dict):
        if not isinstance(left, dict) or not isinstance(right, dict) or set(left) != set(right):
            return False
        return all(_json_value_equal(left[key], right[key], label) for key in left)
    return type(left) is type(right) and left == right


def _number_bits(value: Any, label: str) -> str:
    _number(value, label)
    try:
        binary = float(value)
    except (OverflowError, ValueError) as exc:
        _fail("mutation-value", f"{label} cannot be converted to binary64: {exc}")
    if not math.isfinite(binary):
        _fail("mutation-value", f"{label} is not finite binary64")
    return _float_bits(binary)


def _assert_number_bits(value: Any, expected_bits: str, label: str) -> None:
    actual_bits = _number_bits(value, label)
    if actual_bits != expected_bits:
        _fail("mutation-contract", f"{label} has bits {actual_bits}, expected {expected_bits}")


def _assert_vector_bits(value: Any, expected_bits: tuple[str, ...], label: str) -> None:
    vector = _array(value, label)
    if len(vector) != len(expected_bits):
        _fail("mutation-contract", f"{label} must contain {len(expected_bits)} components")
    for index, (component, bits) in enumerate(zip(vector, expected_bits)):
        _assert_number_bits(component, bits, f"{label}[{index}]")


def _canonical_json(value: Any) -> str:
    """Encode the materialized source while retaining Decimal numeric lexemes."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Decimal):
        if not value.is_finite():
            _fail("nonfinite-value", "materialized Decimal is not finite")
        return str(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("nonfinite-value", "materialized float is not finite")
        return json.dumps(value, allow_nan=False, separators=(",", ":"))
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json(child) for child in value) + "]"
    if isinstance(value, dict):
        members = []
        for key in sorted(value):
            members.append(_canonical_json(str(key)) + ":" + _canonical_json(value[key]))
        return "{" + ",".join(members) + "}"
    _fail("wrong-type", f"cannot encode {type(value).__name__}")
    return ""  # unreachable


def _fixture_for_case(case: Mapping[str, Any], repo_root: Path) -> tuple[Path, bytes, dict[str, Any]]:
    base = _object(case["base_fixture"], "case.base_fixture")
    path_text = _string(base["path"], "case.base_fixture.path")
    if Path(path_text).is_absolute() or any(part in ("", ".", "..") for part in Path(path_text).parts):
        _fail("fixture-path", "base fixture path must be a relative safe path")
    path = repo_root / path_text
    raw = _read_regular(path, MAX_SOURCE_BYTES, "base fixture")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != base["sha256"]:
        _fail("fixture-hash-mismatch", f"base fixture hash is {digest}, expected authored hash")
    source = _parse_source(raw)
    return path, raw, source


def _parse_source(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=lambda pairs: _source_pairs(pairs),
            parse_float=Decimal,
            parse_int=int,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except _DuplicateKey as exc:
        _fail("duplicate-key", f"base fixture contains duplicate member {exc}")
    except (ValueError, json.JSONDecodeError, RecursionError) as exc:
        _fail("fixture-json", str(exc))
    return _object(value, "base fixture")


def _source_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def materialize_case(case: Mapping[str, Any], repo_root: Path | str = REPO_ROOT) -> bytes:
    """Apply closed replacements and return deterministic development bytes."""
    _, _, source = _fixture_for_case(case, Path(repo_root))
    mutations = _array(case["mutations"], "case.mutations")
    result = copy.deepcopy(source)
    seen: set[str] = set()
    for index, mutation_raw in enumerate(mutations):
        mutation = _object(mutation_raw, f"case.mutations[{index}]")
        _exact_fields(mutation, {"op", "path", "value"}, f"case.mutations[{index}]")
        if mutation["op"] != "replace":
            _fail("mutation-op", f"case.mutations[{index}].op must be replace")
        path = _string(mutation["path"], f"case.mutations[{index}].path")
        if path in seen:
            _fail("duplicate-mutation", f"case mutates {path} more than once")
        seen.add(path)
        _replace(result, path, mutation["value"], f"case.mutations[{index}].path")
    output = (_canonical_json(result) + "\n").encode("utf-8")
    if len(output) > MAX_SOURCE_BYTES:
        _fail("materialized-too-large", f"materialized source exceeds {MAX_SOURCE_BYTES} bytes")
    return output


def _profile_constants(profile_id: str) -> tuple[Fraction, Fraction, Fraction]:
    candidate_id = next((c for c, value in profile_sweep.PROFILE_IDS.items() if value == profile_id), None)
    if candidate_id is None:
        _fail("profile-id", f"unknown profile ID {profile_id}")
    values = profile_sweep.EXPECTED[candidate_id]
    names = ("A", "R", "H")
    return tuple(Fraction.from_float(_bits_float(values[name][0], f"{candidate_id}.{name}")) for name in names)  # type: ignore[return-value]


def translation_boundary(candidate_id: str) -> Fraction:
    """Return the exact positive boundary A/(1-R) for one sweep candidate."""
    if candidate_id not in profile_sweep.CANDIDATE_IDS:
        _fail("candidate-id", f"unknown candidate {candidate_id}")
    values = profile_sweep.EXPECTED[candidate_id]
    a = Fraction.from_float(_bits_float(values["A"][0], f"{candidate_id}.A"))
    r = Fraction.from_float(_bits_float(values["R"][0], f"{candidate_id}.R"))
    return a / (1 - r)


def _boundary_float(candidate_id: str, direction: str) -> float:
    target = translation_boundary(candidate_id)
    value = float(target)
    if direction == "at-or-below":
        while Fraction.from_float(value) > target:
            value = math.nextafter(value, -math.inf)
        while Fraction.from_float(math.nextafter(value, math.inf)) <= target:
            value = math.nextafter(value, math.inf)
    elif direction == "nextafter-above":
        value = _boundary_float(candidate_id, "at-or-below")
        value = math.nextafter(value, math.inf)
        if Fraction.from_float(value) <= target:
            _fail("boundary-generation", f"nextafter did not exceed {candidate_id} boundary")
    else:
        _fail("boundary-direction", f"unsupported direction {direction}")
    return value


def _translation_agrees(delta: float, candidate_id: str) -> bool:
    values = profile_sweep.EXPECTED[candidate_id]
    a = Fraction.from_float(_bits_float(values["A"][0], f"{candidate_id}.A"))
    r = Fraction.from_float(_bits_float(values["R"][0], f"{candidate_id}.R"))
    d = Fraction.from_float(delta)
    return d <= a + r * d


def _rotation_agrees(z: Any, candidate_id: str) -> bool:
    """Exact Fraction predicate for q=(0,0,z,1) versus identity.

    For the normalized tuple, half-chord squared is
    ``(1 - 1/sqrt(1+z*z))/2``.  Squaring the positive inequality avoids a
    floating-point square root and is independent of candidate implementation.
    """
    z_fraction = _number_fraction(z, "rotation oracle z")
    values = profile_sweep.EXPECTED[candidate_id]
    h = Fraction.from_float(_bits_float(values["H"][0], f"{candidate_id}.H"))
    left = (1 - 2 * h * h) ** 2 * (1 + z_fraction * z_fraction)
    return left <= 1


def _rotation_margin(z: Any, candidate_id: str) -> Fraction:
    z_fraction = _number_fraction(z, "rotation oracle z")
    values = profile_sweep.EXPECTED[candidate_id]
    h = Fraction.from_float(_bits_float(values["H"][0], f"{candidate_id}.H"))
    return abs((1 - 2 * h * h) ** 2 * (1 + z_fraction * z_fraction) - 1)


def _expected_map(case: Mapping[str, Any], label: str) -> dict[str, dict[str, Any]]:
    expected = _object(case["expected"], f"{label}.expected")
    if set(expected) != set(PROFILE_IDS):
        _fail("profile-coverage", f"{label}.expected must cover exactly all sweep profile IDs")
    result: dict[str, dict[str, Any]] = {}
    for profile_id in PROFILE_IDS:
        entry = _object(expected[profile_id], f"{label}.expected[{profile_id}]")
        _exact_fields(entry, {"classification", "cause"}, f"{label}.expected[{profile_id}]")
        classification = _string(entry["classification"], f"{label}.classification")
        if classification not in {"agree", "conflict", "skipped", "rejected"}:
            _fail("classification", f"{label} has unsupported classification {classification}")
        if entry["cause"] is not None:
            cause = _object(entry["cause"], f"{label}.cause")
            if set(cause) - {"code", "failure", "operation", "stage", "index", "field"}:
                _fail("cause-fields", f"{label}.cause contains unstable or unknown fields")
            if "code" not in cause:
                _fail("cause-fields", f"{label}.cause.code is required")
            _string(cause["code"], f"{label}.cause.code")
            for field in ("failure", "operation", "stage", "field"):
                if field in cause:
                    _string(cause[field], f"{label}.cause.{field}")
            if "index" in cause and (isinstance(cause["index"], bool) or not isinstance(cause["index"], int)):
                _fail("cause-fields", f"{label}.cause.index must be an integer")
        result[profile_id] = entry
    return result


def _assert_expected_contract(
    expected: Mapping[str, Mapping[str, Any]],
    classification: str,
    cause: Mapping[str, Any] | None,
    label: str,
) -> None:
    for profile_id, entry in expected.items():
        if entry["classification"] != classification or not _json_value_equal(entry["cause"], cause, f"{label}.{profile_id}.cause"):
            _fail("expected-contract", f"{label}.{profile_id} does not match its frozen classification/cause")


def _assert_mutation_paths(case: Mapping[str, Any], paths: tuple[str, ...], label: str) -> list[dict[str, Any]]:
    mutations = _array(case["mutations"], f"{label}.mutations")
    actual_paths = tuple(mutation["path"] for mutation in mutations)
    if actual_paths != paths:
        _fail("mutation-contract", f"{label} mutation paths differ from the frozen case contract")
    return mutations  # materialize_case already validated each closed mutation shape


def _validate_case_contract(
    case: Mapping[str, Any],
    expected: Mapping[str, Mapping[str, Any]],
    oracle_kind: str,
    oracle_data: Mapping[str, Any],
    materialized_source: Mapping[str, Any],
) -> None:
    case_id = case["case_id"]
    contract = CASE_CONTRACTS.get(case_id)
    if contract is None:
        _fail("case-contract", f"{case_id} has no frozen development case contract")
    if case["family"] != contract["family"] or case["expectation_basis"] != contract["expectation_basis"]:
        _fail("case-contract", f"{case_id} family or expectation basis differs from its frozen case contract")
    if case["providers"] != contract["providers"]:
        _fail("case-contract", f"{case_id} provider declarations differ from its frozen case contract")
    if not _json_value_equal(case["tolerance_override"], contract["tolerance_override"], f"{case_id}.tolerance_override"):
        _fail("case-contract", f"{case_id} tolerance override differs from its frozen case contract")
    if oracle_kind != contract["oracle_kind"]:
        _fail("case-contract", f"{case_id} oracle kind differs from its frozen case contract")
    if contract["oracle_candidate_id"] is not None and oracle_data.get("candidate_id") != contract["oracle_candidate_id"]:
        _fail("oracle-contract", f"{case_id} oracle candidate differs from its frozen case contract")
    if contract["oracle_direction"] is not None and oracle_data.get("direction") != contract["oracle_direction"]:
        _fail("oracle-contract", f"{case_id} oracle direction differs from its frozen case contract")
    if contract["oracle_z_bits"] is not None:
        _assert_number_bits(oracle_data.get("z"), contract["oracle_z_bits"], f"{case_id}.oracle.data.z")
    if contract["oracle_min_margin"] is not None:
        _number(oracle_data.get("min_margin"), f"{case_id}.oracle.data.min_margin")
        if Fraction(oracle_data["min_margin"]) != contract["oracle_min_margin"]:
            _fail("oracle-contract", f"{case_id} rotation margin differs from its frozen case contract")

    expected_classification = contract["expected_classification"]
    if expected_classification is not None:
        _assert_expected_contract(expected, expected_classification, contract["expected_cause"], case_id)

    mutation_kind = contract["mutation"]
    if mutation_kind == "none":
        _assert_mutation_paths(case, (), case_id)
        return

    if mutation_kind == "translation-boundary":
        mutations = _assert_mutation_paths(
            case,
            (PART_TAIL_ROOT_TRANSLATION_Z, HOST_SOCKET_TRANSLATION_Z),
            case_id,
        )
        if oracle_data["component"] != "z":
            _fail("oracle-contract", f"{case_id} translation oracle component must be z")
        _assert_number_bits(mutations[0]["value"], POS_ZERO_BITS, f"{case_id}.mutations[0].value")
        _assert_number_bits(
            _lookup(materialized_source, PART_TAIL_ROOT_TRANSLATION_Z, f"{case_id}.part"),
            POS_ZERO_BITS,
            f"{case_id}.materialized.part",
        )
        value_bits = oracle_data["value_bits"]
        _bits_float(value_bits, f"{case_id}.oracle.data.value_bits")
        _assert_number_bits(mutations[1]["value"], value_bits, f"{case_id}.mutations[1].value")
        _assert_number_bits(
            _lookup(materialized_source, HOST_SOCKET_TRANSLATION_Z, f"{case_id}.socket"),
            value_bits,
            f"{case_id}.materialized.socket",
        )
        return

    if mutation_kind == "translation-broad":
        mutations = _assert_mutation_paths(
            case,
            (PART_TAIL_ROOT_TRANSLATION_Z, HOST_SOCKET_TRANSLATION_Z),
            case_id,
        )
        _assert_number_bits(mutations[0]["value"], POS_ZERO_BITS, f"{case_id}.mutations[0].value")
        _assert_number_bits(mutations[1]["value"], POS_ONE_BITS, f"{case_id}.mutations[1].value")
        _assert_number_bits(_lookup(materialized_source, PART_TAIL_ROOT_TRANSLATION_Z, f"{case_id}.part"), POS_ZERO_BITS, f"{case_id}.materialized.part")
        _assert_number_bits(_lookup(materialized_source, HOST_SOCKET_TRANSLATION_Z, f"{case_id}.socket"), POS_ONE_BITS, f"{case_id}.materialized.socket")
        return

    if mutation_kind == "quaternion-sign":
        mutations = _assert_mutation_paths(case, (PART_TAIL_ROOT_ROTATION,), case_id)
        expected_bits = (POS_ZERO_BITS, POS_ZERO_BITS, POS_ZERO_BITS, NEG_ONE_BITS)
        _assert_vector_bits(mutations[0]["value"], expected_bits, f"{case_id}.mutations[0].value")
        _assert_vector_bits(_lookup(materialized_source, PART_TAIL_ROOT_ROTATION, f"{case_id}.rotation"), expected_bits, f"{case_id}.materialized.rotation")
        return

    if mutation_kind == "rotation-margin":
        mutations = _assert_mutation_paths(case, (HOST_SOCKET_ROTATION,), case_id)
        if oracle_data["component"] != "rotation":
            _fail("oracle-contract", f"{case_id} rotation oracle component must be rotation")
        if not _json_value_equal(mutations[0]["value"][2], oracle_data["z"], f"{case_id}.rotation.z"):
            _fail("mutation-contract", f"{case_id} mutation z differs from the rotation oracle z")
        z_bits = _number_bits(oracle_data["z"], f"{case_id}.oracle.data.z")
        expected_bits = (POS_ZERO_BITS, POS_ZERO_BITS, z_bits, POS_ONE_BITS)
        _assert_vector_bits(mutations[0]["value"], expected_bits, f"{case_id}.mutations[0].value")
        _assert_vector_bits(_lookup(materialized_source, HOST_SOCKET_ROTATION, f"{case_id}.rotation"), expected_bits, f"{case_id}.materialized.rotation")
        return

    if mutation_kind == "zero-quaternion":
        mutations = _assert_mutation_paths(case, (PELVIS_ROTATION,), case_id)
        expected_bits = (POS_ZERO_BITS, POS_ZERO_BITS, POS_ZERO_BITS, POS_ZERO_BITS)
        _assert_vector_bits(mutations[0]["value"], expected_bits, f"{case_id}.mutations[0].value")
        _assert_vector_bits(_lookup(materialized_source, PELVIS_ROTATION, f"{case_id}.rotation"), expected_bits, f"{case_id}.materialized.rotation")
        return

    _fail("case-contract", f"{case_id} has unsupported frozen mutation contract {mutation_kind}")


def _validate_case(case_raw: Any, index: int, repo_root: Path) -> dict[str, Any]:
    case = _object(case_raw, f"cases[{index}]")
    _exact_fields(
        case,
        {"case_id", "family", "base_fixture", "mutations", "providers", "tolerance_override", "expected", "expectation_basis", "oracle", "materialized_sha256"},
        f"cases[{index}]",
    )
    case_id = _string(case["case_id"], f"cases[{index}].case_id")
    family = _string(case["family"], f"cases[{index}].family")
    base = _object(case["base_fixture"], f"cases[{index}].base_fixture")
    _exact_fields(base, {"path", "sha256"}, f"cases[{index}].base_fixture")
    if base["path"] != BASE_FIXTURE or base["sha256"] != BASE_SHA256:
        _fail("fixture-identity", f"{case_id} must bind the committed stylized fixture identity")
    mutations = _array(case["mutations"], f"cases[{index}].mutations")
    if len(mutations) > MAX_MUTATIONS:
        _fail("mutation-limit", f"{case_id} exceeds {MAX_MUTATIONS} mutations")
    providers = _object(case["providers"], f"cases[{index}].providers")
    _exact_fields(providers, set(PROVIDERS), f"cases[{index}].providers")
    for key in PROVIDERS:
        _string(providers[key], f"{case_id}.providers.{key}")
    if providers["gate"] not in {"allow", "reject"}:
        _fail("provider-selection", f"{case_id} has an unsupported gate provider")
    if providers["arithmetic"] not in {"native", "unavailable"}:
        _fail("provider-selection", f"{case_id} has an unsupported arithmetic provider")
    if providers["sqrt"] not in {"native", "unavailable"}:
        _fail("provider-selection", f"{case_id} has an unsupported sqrt provider")
    if providers["environment"] != ENVIRONMENT:
        _fail("environment", f"{case_id} has an unsupported environment declaration")
    override = case["tolerance_override"]
    if override is not None:
        override = _object(override, f"{case_id}.tolerance_override")
        if not set(override) <= set(TOLERANCE_FIELDS) or not override:
            _fail("tolerance-override", f"{case_id} has invalid tolerance override fields")
        for key, value in override.items():
            _number(value, f"{case_id}.tolerance_override.{key}")
    basis = _string(case["expectation_basis"], f"{case_id}.expectation_basis")
    if basis not in {"independent-exact", "independent-conservative", "contract-order"}:
        _fail("expectation-basis", f"{case_id} has unsupported expectation basis")
    expected = _expected_map(case, case_id)
    oracle = _object(case["oracle"], f"{case_id}.oracle")
    _exact_fields(oracle, {"kind", "data"}, f"{case_id}.oracle")
    kind = _string(oracle["kind"], f"{case_id}.oracle.kind")
    data = _object(oracle["data"], f"{case_id}.oracle.data")

    # Materialization validates paths, replacement types, duplicate paths, and
    # the fixture hash before any case can be accepted.
    materialized = materialize_case(case, repo_root)
    digest = hashlib.sha256(materialized).hexdigest()
    if digest != case["materialized_sha256"]:
        _fail("materialized-hash-mismatch", f"{case_id} materializes to {digest}, not the authored hash")
    materialized_source = _parse_source(materialized)

    if kind == "translation-boundary":
        _exact_fields(data, {"candidate_id", "direction", "component", "boundary_fraction", "value_bits"}, f"{case_id}.oracle.data")
        candidate_id = _string(data["candidate_id"], f"{case_id}.oracle.data.candidate_id")
        direction = _string(data["direction"], f"{case_id}.oracle.data.direction")
        if candidate_id not in profile_sweep.CANDIDATE_IDS or direction not in {"at-or-below", "nextafter-above"}:
            _fail("translation-oracle", f"{case_id} has invalid boundary identity")
        target = translation_boundary(candidate_id)
        if data["boundary_fraction"] != f"{target.numerator}/{target.denominator}":
            _fail("boundary-fraction", f"{case_id} does not record exact A/(1-R)")
        value = _bits_float(_string(data["value_bits"], f"{case_id}.oracle.data.value_bits"), f"{case_id}.value_bits")
        actual = Fraction.from_float(value)
        if direction == "at-or-below" and not (actual <= target < Fraction.from_float(math.nextafter(value, math.inf))):
            _fail("boundary-bit-proof", f"{case_id} is not the greatest binary64 value at or below the exact boundary")
        if direction == "nextafter-above" and not (Fraction.from_float(math.nextafter(value, -math.inf)) <= target < actual):
            _fail("boundary-bit-proof", f"{case_id} is not the immediate binary64 value above the exact boundary")
        for profile_id, entry in expected.items():
            want = "agree" if _translation_agrees(value, next(c for c, p in profile_sweep.PROFILE_IDS.items() if p == profile_id)) else "conflict"
            if entry["classification"] != want or entry["cause"] is not None:
                _fail("oracle-expectation", f"{case_id} has incorrect independent translation expectation")
    elif kind == "rotation-margin":
        _exact_fields(data, {"component", "z", "min_margin"}, f"{case_id}.oracle.data")
        z = data["z"]
        _number(z, f"{case_id}.oracle.data.z")
        margin_floor = Fraction(data["min_margin"]) if isinstance(data["min_margin"], int) else Fraction(Decimal(str(data["min_margin"])))
        if margin_floor < MIN_ROTATION_MARGIN:
            _fail("rotation-margin", f"{case_id} declares too small a conservative margin")
        for candidate_id in profile_sweep.CANDIDATE_IDS:
            if _rotation_margin(z, candidate_id) < margin_floor:
                _fail("rotation-margin", f"{case_id} is too close to {candidate_id} threshold")
            profile_id = profile_sweep.PROFILE_IDS[candidate_id]
            want = "agree" if _rotation_agrees(z, candidate_id) else "conflict"
            if expected[profile_id]["classification"] != want or expected[profile_id]["cause"] is not None:
                _fail("oracle-expectation", f"{case_id} has incorrect independent rotation expectation")
    elif kind == "none":
        _exact_fields(data, set(), f"{case_id}.oracle.data")
    else:
        _fail("oracle-kind", f"{case_id} has unsupported oracle kind {kind}")
    _validate_case_contract(case, expected, kind, data, materialized_source)
    return case


def validate_corpus(value: Any, repo_root: Path | str = REPO_ROOT) -> dict[str, Any]:
    corpus = _object(value, "corpus")
    if set(CASE_CONTRACTS) != CASE_IDS:
        _fail("case-contract", "frozen case contracts do not cover the closed case set")
    _exact_fields(corpus, {"schema", "corpus_id", "corpus_role", "sweep_id", "materialization", "cases"}, "corpus")
    if corpus["schema"] != SCHEMA or corpus["corpus_id"] != CORPUS_ID:
        _fail("identity-mismatch", "corpus schema or identity differs")
    if corpus["corpus_role"] != CORPUS_ROLE:
        _fail("role-mismatch", "corpus role must be development")
    if corpus["sweep_id"] != profile_sweep.SWEEP_ID:
        _fail("sweep-mismatch", "corpus must reference the unselected development sweep")
    materialization = _object(corpus["materialization"], "corpus.materialization")
    _exact_fields(materialization, {"format", "source_bytes", "hash"}, "corpus.materialization")
    if materialization["format"] != MATERIALIZATION_FORMAT or materialization["source_bytes"] != "development-generated" or materialization["hash"] != "sha256":
        _fail("materialization-format", "materialization declaration differs")
    cases = _array(corpus["cases"], "corpus.cases")
    if not MIN_CASES <= len(cases) <= MAX_CASES:
        _fail("case-count", f"corpus must contain {MIN_CASES}..{MAX_CASES} cases")
    seen: set[str] = set()
    checked: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        checked_case = _validate_case(case, index, Path(repo_root))
        if checked_case["case_id"] in seen:
            _fail("duplicate-case", f"duplicate case ID {checked_case['case_id']}")
        seen.add(checked_case["case_id"])
        checked.append(checked_case)
    if seen != CASE_IDS:
        _fail("case-set", "development corpus case IDs differ from the frozen bounded set")
    corpus["cases"] = checked
    return corpus


def load_development_corpus(path: Path | str = CORPUS_PATH, repo_root: Path | str = REPO_ROOT) -> dict[str, Any]:
    raw = _read_regular(Path(path), MAX_CORPUS_BYTES, "development corpus")
    return validate_corpus(_parse(raw), repo_root)


if __name__ == "__main__":
    load_development_corpus()
    print(f"valid development corpus: cases={len(load_development_corpus()['cases'])}; profile-selection=none")

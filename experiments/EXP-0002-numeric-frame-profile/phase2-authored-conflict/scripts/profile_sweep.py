#!/usr/bin/env python3
"""Bounded loader for the non-activating EXP-0002 development sweep.

The file is an authored, closed definition.  This module validates it without
selecting a profile, applying defaults, repairing values, or binding a digest.
The later runner can use :func:`load_profile_sweep` as its input boundary.
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping


DEFINITION_PATH = Path(__file__).resolve().parents[1] / "profiles" / "development-sweep.json"
SCHEMA = "ck.exp-0002.r3-authored-conflict-development-sweep-1"
SWEEP_ID = "ck.exp-0002.r3-authored-conflict-sweep-1"
DEFINITION_ID = "ck.exp-0002.r3-authored-conflict-development-sweep-definition-1"
TARGET = "authored-root-local-vs-attachment-derived"
COMPARISON_MODE = "semantic-exact-dyadic-tolerance"
CANDIDATE_IDS = ("strict", "micro", "stress")
CONSTANT_NAMES = ("A", "R", "H")
PROFILE_IDS = {
    "strict": "ck.provisional-r3-authored-conflict.dev.strict-1",
    "micro": "ck.provisional-r3-authored-conflict.dev.micro-1",
    "stress": "ck.provisional-r3-authored-conflict.dev.stress-1",
}
MAX_DEFINITION_BYTES = 16 * 1024
MAX_CANDIDATE_RECORDS = 3
# Named aliases make the boundary explicit to future runner consumers.
MAX_FILE_BYTES = MAX_DEFINITION_BYTES
MAX_RECORDS = MAX_CANDIDATE_RECORDS
MAX_JSON_DEPTH = 12

EXPECTED = {
    "strict": {
        "A": ("0x3cf0000000000000", "3.552713678800501e-15"),
        "R": ("0x3d10000000000000", "1.4210854715202004e-14"),
        "H": ("0x3d10000000000000", "1.4210854715202004e-14"),
    },
    "micro": {
        "A": ("0x3eb0000000000000", "9.5367431640625e-07"),
        "R": ("0x3d70000000000000", "9.094947017729282e-13"),
        "H": ("0x3eb0000000000000", "9.5367431640625e-07"),
    },
    "stress": {
        "A": ("0x3f50000000000000", "0.0009765625"),
        "R": ("0x3df0000000000000", "2.3283064365386963e-10"),
        "H": ("0x3f30000000000000", "0.000244140625"),
    },
}


class SweepValidationError(ValueError):
    """A stable, machine-readable definition failure."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _DuplicateKey(Exception):
    pass


def _fail(code: str, detail: str) -> None:
    raise SweepValidationError(code, detail)


def _exact_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        _fail("missing-field", f"{label}: {','.join(missing)}")
    if extra:
        _fail("extra-field", f"{label}: {','.join(extra)}")


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("wrong-type", f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _fail("wrong-type", f"{label} must be a string")
    return value


def _walk(value: Any, depth: int = 0, label: str = "definition") -> None:
    if depth > MAX_JSON_DEPTH:
        _fail("json-depth", f"{label} exceeds depth {MAX_JSON_DEPTH}")
    if isinstance(value, float) and not math.isfinite(value):
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
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except _DuplicateKey as exc:
        _fail("duplicate-key", f"duplicate object member {exc}")
    except (ValueError, json.JSONDecodeError, RecursionError) as exc:
        _fail("invalid-json", str(exc))
    _walk(value)
    return _object(value, "definition")


def _bits_to_float(bits: str, label: str) -> float:
    if len(bits) != 18 or not bits.startswith("0x") or any(c not in "0123456789abcdef" for c in bits[2:]):
        _fail("bits-format", f"{label} must be 0x plus 16 lowercase hexadecimal digits")
    integer = int(bits[2:], 16)
    if integer >> 63:
        _fail("negative-value", f"{label} has its sign bit set")
    if (integer >> 52) & 0x7FF == 0x7FF:
        _fail("nonfinite-value", f"{label} is NaN or infinity")
    return struct.unpack(">d", integer.to_bytes(8, "big"))[0]


def _float_bits(value: float) -> str:
    return "0x" + struct.pack(">d", value).hex()


def _validate_constant(value: Any, candidate_id: str, name: str) -> None:
    label = f"candidates[{candidate_id}].constants.{name}"
    constant = _object(value, label)
    _exact_fields(constant, {"bits", "decimal"}, label)
    bits = _string(constant["bits"], f"{label}.bits")
    decimal = _string(constant["decimal"], f"{label}.decimal")
    if decimal.startswith("-"):
        _fail("negative-value", f"{label}.decimal is negative")
    binary = _bits_to_float(bits, f"{label}.bits")
    try:
        parsed = float(decimal)
    except (OverflowError, ValueError) as exc:
        _fail("decimal-format", f"{label}.decimal is not a finite decimal: {exc}")
    if not math.isfinite(parsed):
        _fail("nonfinite-value", f"{label}.decimal is not finite")
    if parsed < 0:
        _fail("negative-value", f"{label}.decimal is negative")
    if _float_bits(parsed) != bits:
        _fail("bits-decimal-mismatch", f"{label}.bits and decimal disagree")
    expected_bits, expected_decimal = EXPECTED[candidate_id][name]
    if bits != expected_bits or decimal != expected_decimal:
        _fail("candidate-value-mismatch", f"{label} differs from the frozen sweep constant")
    if not math.isfinite(binary):  # defensive: the bit-level check is authoritative
        _fail("nonfinite-value", f"{label}.bits is not finite")


def validate_definition(value: Any) -> dict[str, Any]:
    """Validate a parsed definition and return the same object, without repair."""
    definition = _object(value, "definition")
    _exact_fields(
        definition,
        {
            "schema",
            "sweep_id",
            "definition_id",
            "profile_role",
            "authored_conflict_target",
            "semantic_comparison_mode",
            "selected_profile_id",
            "r3_activation",
            "candidates",
        },
        "definition",
    )
    if definition["schema"] != SCHEMA:
        _fail("schema-mismatch", "definition.schema is not the supported schema")
    if definition["sweep_id"] != SWEEP_ID:
        _fail("identity-mismatch", "definition.sweep_id is not the supported sweep")
    if definition["definition_id"] != DEFINITION_ID:
        _fail("identity-mismatch", "definition.definition_id is not the development sweep definition")
    if definition["profile_role"] != "development-sweep-constants":
        _fail("role-mismatch", "definition.profile_role must identify development constants")
    if definition["authored_conflict_target"] != TARGET:
        _fail("target-mismatch", "authored-conflict target differs")
    if definition["semantic_comparison_mode"] != COMPARISON_MODE:
        _fail("comparison-mode-mismatch", "semantic comparison mode differs")
    if definition["selected_profile_id"] is not None:
        _fail("selection-present", "selected_profile_id must remain null")
    if definition["r3_activation"] != "inactive":
        _fail("activation-present", "R3 activation must remain inactive")

    candidates = definition["candidates"]
    if not isinstance(candidates, list):
        _fail("wrong-type", "definition.candidates must be an array")
    if len(candidates) > MAX_CANDIDATE_RECORDS:
        _fail("record-limit", f"definition.candidates exceeds {MAX_CANDIDATE_RECORDS} records")
    if len(candidates) != len(CANDIDATE_IDS):
        _fail("candidate-count", "definition.candidates must contain exactly three records")
    ids: list[str] = []
    for index, raw_candidate in enumerate(candidates):
        candidate = _object(raw_candidate, f"candidates[{index}]")
        _exact_fields(candidate, {"candidate_id", "profile_id", "constants"}, f"candidates[{index}]")
        candidate_id = _string(candidate["candidate_id"], f"candidates[{index}].candidate_id")
        ids.append(candidate_id)
        if candidate_id != CANDIDATE_IDS[index]:
            _fail("candidate-order", "candidate IDs must be ordered strict, micro, stress")
        profile_id = _string(candidate["profile_id"], f"candidates[{index}].profile_id")
        if profile_id != PROFILE_IDS[candidate_id]:
            _fail("profile-id-mismatch", f"profile ID for {candidate_id} differs from the frozen candidate identity")
        constants = _object(candidate["constants"], f"candidates[{index}].constants")
        _exact_fields(constants, set(CONSTANT_NAMES), f"candidates[{index}].constants")
        for name in CONSTANT_NAMES:
            _validate_constant(constants[name], candidate_id, name)
    if tuple(ids) != CANDIDATE_IDS:
        _fail("candidate-set", "candidate IDs must be exactly strict, micro, stress")
    return definition


def load_profile_sweep(path: Path | str = DEFINITION_PATH) -> dict[str, Any]:
    """Read and validate one bounded development sweep definition."""
    definition_path = Path(path)
    try:
        if definition_path.is_symlink() or not definition_path.is_file():
            _fail("file-type", "definition must be a regular non-symlink file")
        with definition_path.open("rb") as handle:
            raw = handle.read(MAX_DEFINITION_BYTES + 1)
    except SweepValidationError:
        raise
    except OSError as exc:
        _fail("file-read", str(exc))
    if not raw:
        _fail("file-empty", "definition is empty")
    if len(raw) > MAX_DEFINITION_BYTES:
        _fail("file-too-large", f"definition exceeds {MAX_DEFINITION_BYTES} bytes")
    return validate_definition(_parse(raw))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="validate the EXP-0002 development sweep")
    parser.add_argument("path", nargs="?", type=Path, default=DEFINITION_PATH)
    args = parser.parse_args()
    load_profile_sweep(args.path)
    print("valid development sweep: selected_profile_id=null; r3_activation=inactive")

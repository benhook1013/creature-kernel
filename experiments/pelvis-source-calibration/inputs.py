"""Prepare the one frozen pelvis source-calibration input set.

This module is intentionally stdlib-only.  It reads the predecessor's frozen
``inputs.json`` and the parent-owned protocol, then emits concrete generator
cases.  It never imports or calls geometry code.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
FROZEN_ROOT = Path("/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot")
FROZEN_OLD_INPUTS = FROZEN_ROOT / "source/experiments/pelvis-thigh-transition/inputs.json"
PROTOCOL_PATH = HERE / "protocol.json"
OLD_CASE_COUNT = 5
NORMALIZATION_REASON = "frame/unit normalization"
ANATOMICAL_REASON = "anatomical estimate"
SCHEMA = "creature-kernel.pelvis-source-calibration-inputs.v1"


class InputError(ValueError):
    """Raised when the frozen source or protocol cannot be admitted."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_json(path: Path) -> tuple[Any, bytes]:
    if path.is_symlink() or not path.is_file():
        raise InputError(f"required regular file is unavailable: {path}")
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise InputError(f"invalid finite UTF-8 JSON: {path}") from exc
    return value, raw


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise InputError(f"{label} must be finite")
    return number


def _canonical(path: str | os.PathLike[str], label: str) -> Path:
    result = Path(path)
    if not result.is_absolute() or os.path.normpath(str(result)) != str(result):
        raise InputError(f"{label} must be an absolute canonical path")
    return result


def _load_source() -> tuple[dict[str, Any], bytes, str]:
    value, raw = _strict_json(FROZEN_OLD_INPUTS)
    if not isinstance(value, dict) or not isinstance(value.get("cases"), list):
        raise InputError("frozen predecessor inputs must contain a cases list")
    if len(value["cases"]) < OLD_CASE_COUNT:
        raise InputError("frozen predecessor inputs do not contain five controls")
    controls = value["cases"][:OLD_CASE_COUNT]
    expected = (
        "standard_neutral_reference",
        "compact_broad_short_limb_large_head",
        "tall_narrow_long_legged",
        "slender_long_limb",
        "stocky_broad_chested",
    )
    actual = tuple(case.get("id") for case in controls if isinstance(case, dict))
    if actual != expected:
        raise InputError(f"frozen control order differs: {actual!r}")
    for case in controls:
        if not isinstance(case, dict) or not isinstance(case.get("components"), dict):
            raise InputError("frozen controls must be complete predecessor case dictionaries")
        if not isinstance(case.get("attachments"), dict):
            raise InputError("frozen controls must contain attachments")
    return value, raw, _sha256(raw)


def _load_protocol() -> tuple[dict[str, Any], bytes, str]:
    value, raw = _strict_json(PROTOCOL_PATH)
    if not isinstance(value, dict) or value.get("version") != "pelvis-source-calibration.single-set.v1":
        raise InputError("protocol version is not the declared single-set calibration protocol")
    if value.get("historical_controls") != OLD_CASE_COUNT:
        raise InputError("protocol historical control count is not five")
    budget = value.get("budget")
    if budget != {"calibration_sets": 1, "input_refinements": 0, "geometry_changes": 0}:
        raise InputError("protocol budget is not the one-set/no-change budget")
    transform = value.get("base_transform")
    if not isinstance(transform, dict) or set(transform) != {"scale", "translation", "reason"}:
        raise InputError("protocol base_transform shape is not admitted")
    scale = _finite(transform["scale"], "protocol base_transform.scale")
    translation = transform["translation"]
    if scale <= 0.0 or not isinstance(translation, list) or len(translation) != 3:
        raise InputError("protocol base_transform values are invalid")
    [_finite(item, "protocol base_transform.translation") for item in translation]
    cases = value.get("cases")
    if not isinstance(cases, list) or len(cases) != 2:
        raise InputError("protocol must declare exactly two calibration cases")
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise InputError("protocol calibration case is malformed")
        for key in ("stations", "hip_radii", "attachments", "reference_landmarks"):
            if key not in case:
                raise InputError(f"protocol case {case.get('id')} lacks {key}")
    return value, raw, _sha256(raw)


def _coordinate_component(key: str) -> int | None:
    axis = key.rsplit(".", 1)[-1]
    return {"x": 0, "y": 1, "z": 2}.get(axis)


def _affine_value(value: Any, axis: int | None, scale: float, translation: list[float]) -> float:
    number = _finite(value, "source component")
    return number * scale + (translation[axis] if axis is not None else 0.0)


def _affine_components(source: Mapping[str, Any], scale: float, translation: list[float], reason_detail: str) -> tuple[dict[str, float], list[dict[str, Any]]]:
    result: dict[str, float] = {}
    ledger: list[dict[str, Any]] = []
    for key, value in source.items():
        if not isinstance(key, str):
            raise InputError("component IDs must be strings")
        axis = _coordinate_component(key)
        old = _finite(value, f"components.{key}")
        new = _affine_value(value, axis, scale, translation)
        result[key] = float(new)
        if new != old:
            ledger.append({
                "path": f"/components/{key}",
                "old": old,
                "new": float(new),
                "reason": NORMALIZATION_REASON,
                "reason_detail": reason_detail,
                "protocol_reason_pointer": "/base_transform/reason",
            })
    return result, ledger


def _affine_attachments(source: Mapping[str, Any], scale: float, translation: list[float], reason_detail: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result: dict[str, Any] = {}
    ledger: list[dict[str, Any]] = []
    for side, side_value in source.items():
        if not isinstance(side_value, Mapping):
            raise InputError(f"attachments.{side} must be a mapping")
        result[side] = {}
        for name, point in side_value.items():
            if not isinstance(point, list) or len(point) != 3:
                raise InputError(f"attachments.{side}.{name} must be a three-vector")
            new_point = []
            for axis, value in enumerate(point):
                old = _finite(value, f"attachments.{side}.{name}[{axis}]")
                new = old * scale + translation[axis]
                new_point.append(float(new))
                if new != old:
                    ledger.append({
                        "path": f"/attachments/{side}/{name}/{axis}",
                        "old": old,
                        "new": float(new),
                        "reason": NORMALIZATION_REASON,
                        "reason_detail": reason_detail,
                        "protocol_reason_pointer": "/base_transform/reason",
                    })
            result[side][name] = new_point
    return result, ledger


def _record(ledger: list[dict[str, Any]], path: str, old: Any, new: Any, reason: str, *, reason_detail: str | None = None, protocol_reason_pointer: str | None = None) -> None:
    old_value = deepcopy(old)
    new_value = deepcopy(new)
    if old_value != new_value:
        entry = {"path": path, "old": old_value, "new": new_value, "reason": reason}
        if reason_detail is not None:
            entry["reason_detail"] = reason_detail
        if protocol_reason_pointer is not None:
            entry["protocol_reason_pointer"] = protocol_reason_pointer
        ledger.append(entry)


def _set_component(components: dict[str, float], ledger: list[dict[str, Any]], key: str, value: Any, *, reason_detail: str, protocol_reason_pointer: str) -> None:
    if key not in components:
        raise InputError(f"protocol override refers to unknown component: {key}")
    old = components[key]
    components[key] = float(_finite(value, key))
    _record(ledger, f"/components/{key}", old, components[key], ANATOMICAL_REASON, reason_detail=reason_detail, protocol_reason_pointer=protocol_reason_pointer)


def _apply_protocol_case(neutral: Mapping[str, Any], protocol_case: Mapping[str, Any], protocol_index: int, source_sha256: str, protocol_sha256: str, transform: Mapping[str, Any]) -> dict[str, Any]:
    scale = _finite(transform["scale"], "base transform scale")
    translation = [float(_finite(item, "base transform translation")) for item in transform["translation"]]
    components, ledger = _affine_components(neutral["components"], scale, translation, str(transform["reason"]))
    attachments, attachment_ledger = _affine_attachments(neutral["attachments"], scale, translation, str(transform["reason"]))
    ledger.extend(attachment_ledger)

    stations = protocol_case["stations"]
    if not isinstance(stations, Mapping):
        raise InputError(f"protocol stations malformed: {protocol_case.get('id')}")
    station_reason = str(protocol_case["station_reason"])
    station_reason_pointer = f"/cases/{protocol_index}/station_reason"
    for station_name, station in stations.items():
        if not isinstance(station, Mapping) or set(station) != {"centre", "radii"}:
            raise InputError(f"protocol station malformed: {station_name}")
        centre = station["centre"]
        radii = station["radii"]
        if not isinstance(centre, list) or len(centre) != 3 or not isinstance(radii, list) or len(radii) != 3:
            raise InputError(f"protocol station vectors malformed: {station_name}")
        for axis, name in enumerate(("x", "y", "z")):
            _set_component(components, ledger, f"stations.{station_name}.C.{name}", centre[axis], reason_detail=station_reason, protocol_reason_pointer=station_reason_pointer)
        for name, value in zip(("rL", "rA", "rP"), radii):
            _set_component(components, ledger, f"stations.{station_name}.{name}", value, reason_detail=station_reason, protocol_reason_pointer=station_reason_pointer)

    protocol_attachments = protocol_case["attachments"]
    if not isinstance(protocol_attachments, Mapping) or set(protocol_attachments) != {"left", "right"}:
        raise InputError("protocol attachments must contain left and right")
    hip_radii = protocol_case["hip_radii"]
    if not isinstance(hip_radii, list) or len(hip_radii) != 3:
        raise InputError("protocol hip_radii must be a three-vector")
    hip_radii_reason = str(protocol_case["hip_radii_reason"])
    hip_radii_reason_pointer = f"/cases/{protocol_index}/hip_radii_reason"
    attachment_reason = str(protocol_case["attachment_reason"])
    attachment_reason_pointer = f"/cases/{protocol_index}/attachment_reason"
    for side in ("left", "right"):
        side_data = protocol_attachments[side]
        if not isinstance(side_data, Mapping) or set(side_data) != {"centre", "knee"}:
            raise InputError(f"protocol attachments.{side} is malformed")
        for name in ("centre", "knee"):
            point = side_data[name]
            if not isinstance(point, list) or len(point) != 3:
                raise InputError(f"protocol attachments.{side}.{name} is not a three-vector")
            for axis, value in enumerate(point):
                old = attachments[side][name][axis]
                new = float(_finite(value, f"protocol attachments.{side}.{name}[{axis}]"))
                attachments[side][name][axis] = new
                _record(ledger, f"/attachments/{side}/{name}/{axis}", old, new, ANATOMICAL_REASON, reason_detail=attachment_reason, protocol_reason_pointer=attachment_reason_pointer)
        for axis, name in enumerate(("x", "y", "z")):
            _set_component(components, ledger, f"hips.{side}.P_s.{name}", side_data["centre"][axis], reason_detail=attachment_reason, protocol_reason_pointer=attachment_reason_pointer)
        for name, value in zip(("r_x", "r_y", "r_z"), hip_radii):
            _set_component(components, ledger, f"hips.{side}.{name}", value, reason_detail=hip_radii_reason, protocol_reason_pointer=hip_radii_reason_pointer)

    case_id = protocol_case["id"]
    return {
        "id": case_id,
        "role": protocol_case["role"],
        "components": components,
        "attachments": attachments,
        "provenance": {
            "source": {"path": "frozen old inputs.json", "sha256": source_sha256},
            "base_case": "standard_neutral_reference",
            "base_transform": {
                "scale": scale,
                "translation": translation,
                "reason": transform["reason"],
            },
            "protocol_case_id": case_id,
            "change_ledger": ledger,
            "protocol_sha256": protocol_sha256,
            "reference_landmarks_excluded": True,
            "claim": "single declared calibration input; no geometry or topology variation",
        },
    }


def build_document() -> dict[str, Any]:
    """Return the concrete seven-case document without constructing geometry."""
    source, _source_raw, source_sha256 = _load_source()
    protocol, _protocol_raw, protocol_sha256 = _load_protocol()
    controls = deepcopy(source["cases"][:OLD_CASE_COUNT])
    neutral = controls[0]
    transform = protocol["base_transform"]
    new_cases = [
        _apply_protocol_case(neutral, case, index, source_sha256, protocol_sha256, transform)
        for index, case in enumerate(protocol["cases"])
    ]
    cases = [*controls, *new_cases]
    component_ids = list(source.get("component_ids", []))
    if not component_ids or set(neutral["components"]) != set(component_ids):
        raise InputError("frozen neutral component inventory is inconsistent")
    for case in new_cases:
        if set(case["components"]) != set(component_ids):
            raise InputError(f"calibration case component inventory differs: {case['id']}")
        if "reference_landmarks" in case or "joint_left" in json.dumps(case, sort_keys=True):
            raise InputError(f"reference-only landmark leaked into generator case: {case['id']}")
    return {
        "schema": SCHEMA,
        "source": {
            "path": str(FROZEN_OLD_INPUTS),
            "sha256": source_sha256,
            "historical_case_count": OLD_CASE_COUNT,
        },
        "protocol": {
            "path": "experiments/pelvis-source-calibration/protocol.json",
            "sha256": protocol_sha256,
        },
        "component_ids": component_ids,
        "case_ids": [case["id"] for case in cases],
        "historical_controls": [case["id"] for case in controls],
        "calibration_cases": [case["id"] for case in new_cases],
        "display_normalization": {
            "scale": float(transform["scale"]),
            "translation": [float(item) for item in transform["translation"]],
            "reason": transform["reason"],
            "applies_to": "historical display copies only; saved/evaluated meshes remain native generator output",
        },
        "cases": cases,
        "immutability": "one concrete seven-case set; no input refinement or geometry tuning",
    }


def json_bytes(document: Mapping[str, Any]) -> bytes:
    try:
        return (json.dumps(document, sort_keys=True, indent=2, separators=(",", ": "), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputError("concrete inputs are not finite deterministic JSON") from exc


def prepare(output: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Generate the concrete document and optionally write it to an absent path."""
    document = build_document()
    if output is None:
        return document
    path = _canonical(output, "inputs output")
    if path.exists() or path.is_symlink():
        raise InputError(f"refusing to replace existing concrete inputs: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(document))
    return document


prepare_inputs = build_document


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare frozen pelvis calibration inputs")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare(args.output)
    station_reason = str(protocol_case["station_reason"])
    station_reason_pointer = f"/cases/{protocol_index}/station_reason"
    hip_radii_reason = str(protocol_case["hip_radii_reason"])
    hip_radii_reason_pointer = f"/cases/{protocol_index}/hip_radii_reason"
    attachment_reason = str(protocol_case["attachment_reason"])
    attachment_reason_pointer = f"/cases/{protocol_index}/attachment_reason"

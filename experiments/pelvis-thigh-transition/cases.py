"""Numeric pelvis/thigh transition cases; geometry is deliberately out of scope."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXACT_PACKAGE = ROOT / "experiments/owned-root-assembly-successor-exact-five"
if str(EXACT_PACKAGE) not in sys.path:
    sys.path.insert(0, str(EXACT_PACKAGE))

import exact_five_runner as exact_five


SOURCE_ROLE = "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json"
SOURCE_PATH = ROOT / SOURCE_ROLE
PROFILE_PATH = ROOT / PROFILE_ROLE
SOURCE_SHA256 = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
PROFILE_SHA256 = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
PROFILE_IDS = (
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
HUMAN_ID = "ordinary_human_reference"
PERTURBATION_IDS = (
    "neutral_pelvis_width_plus_10pct",
    "neutral_left_spacing_minus_005",
    "neutral_left_direction_tilt_5deg",
    "neutral_left_front_offset_plus_005",
    "neutral_left_asymmetric_xz_and_radius",
    "neutral_invalid_close_thick",
)


def _load_json(path: Path) -> dict[str, Any]:
    expected = {SOURCE_PATH: SOURCE_SHA256, PROFILE_PATH: PROFILE_SHA256}.get(path)
    raw = path.read_bytes()
    if expected is None or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"fixed input SHA-256 mismatch before loading: {path}")
    return exact_five.profiles.load_json(path, path.name)


def _address_key(address: dict[str, Any]) -> str:
    return f"{address['namespace']}|{address['kind']}|{'|'.join(address['anchors'])}|{address['role']}"


def _source_indexes(source: dict[str, Any]) -> dict[str, dict[str, int]]:
    body = source["body"]
    parts = {_address_key(row["address"]): index for index, row in enumerate(body["parts"])}
    landmarks = {
        (row["owner"]["anchors"][0] if row["owner"]["anchors"] else "", row["owner"]["role"], row["role"]): index
        for index, row in enumerate(body["landmarks"])
    }
    frames = {
        (_address_key(row["owner"]), row["role"]): index
        for index, row in enumerate(body["frames"])
    }
    joints = {
        (_address_key(row["address"]), row["address"]["anchors"][0] if row["address"]["anchors"] else ""): index
        for index, row in enumerate(body["joints"])
    }
    return {"parts": parts, "landmarks": landmarks, "frames": frames, "joints": joints}


def _validate_identity_thigh_inputs(source: dict[str, Any]) -> None:
    indexes = _source_indexes(source)
    for side in ("left", "right"):
        part_key = _part_key(side)
        part = source["body"]["parts"][indexes["parts"][part_key]]
        if part["placement"]["rotation_xyzw"] != [0, 0, 0, 1]:
            raise ValueError(f"{part_key} placement rotation is not identity")
        frame = source["body"]["frames"][indexes["frames"][(part_key, "form_leg_profile_control")]]
        transform = frame["transform"]
        if transform["translation"] != [0, 0, 0] or transform["rotation_xyzw"] != [0, 0, 0, 1]:
            raise ValueError(f"{part_key} control frame is not identity")


def _part_key(side: str) -> str:
    return f"main|part|{side}|thigh"


def _part_world_translation(source: dict[str, Any], row: dict[str, Any], key: str) -> list[float]:
    parts = {_address_key(item["address"]): item for item in source["body"]["parts"]}

    def resolve(current: str, trail: set[str]) -> list[float]:
        if current in trail:
            raise ValueError("part containment cycle")
        placement = row["part_placements"][current]
        parent = parts[current]["containment"].get("parent")
        if parent is None:
            return [float(value) for value in placement]
        parent_key = _address_key(parent)
        parent_world = resolve(parent_key, trail | {current})
        return [parent_world[index] + float(placement[index]) for index in range(3)]

    return resolve(key, set())


def _part_chain_keys(source: dict[str, Any], key: str) -> list[str]:
    parts = {_address_key(item["address"]): item for item in source["body"]["parts"]}
    parent = parts[key]["containment"].get("parent")
    return [_address_key(parent), *[key]] if parent is not None else [key]


def _pointer_values(prefix: str) -> list[str]:
    return [f"{prefix}/{axis}" for axis in range(3)]


def _attachment_provenance(source: dict[str, Any], row: dict[str, Any], profile_index: int, side: str) -> dict[str, Any]:
    indexes = _source_indexes(source)
    part_key = _part_key(side)
    part_index = indexes["parts"][part_key]
    thigh_start_key = (side, "thigh", "form_leg_profile_thigh_start")
    knee_key = (side, "thigh", "form_leg_profile_knee")
    thigh_start_index = indexes["landmarks"][thigh_start_key]
    knee_index = indexes["landmarks"][knee_key]
    frame_index = indexes["frames"][(part_key, "form_leg_profile_control")]
    hip_joint_index = indexes["joints"][(f"main|joint|{side}|hip", side)]
    hip_joint = source["body"]["joints"][hip_joint_index]
    frame_transform = source["body"]["frames"][frame_index]["transform"]
    start_prefix = f"/body/landmarks/{thigh_start_index}/position"
    knee_prefix = f"/body/landmarks/{knee_index}/position"
    chain_keys = _part_chain_keys(source, part_key)
    source_part_pointers = [_pointer_values(f"/body/parts/{indexes['parts'][chain_key]}/placement/translation") for chain_key in chain_keys]
    profile_part_pointers = [_pointer_values(f"/profiles/{profile_index}/part_placements/{chain_key}") for chain_key in chain_keys]
    return {
        "frame": {
            "source_pointers": [f"/body/frames/{frame_index}/transform"],
            "translation": frame_transform["translation"],
            "rotation_xyzw": frame_transform["rotation_xyzw"],
            "interpretation": "identity frame admitted; no rig or joint resolution",
        },
        "centre": {
            "derivation": "profile.world-part-plus-thigh-start.v1",
            "source_pointers": [pointer for group in source_part_pointers for pointer in group] + _pointer_values(start_prefix),
            "profile_pointers": [pointer for group in profile_part_pointers for pointer in group],
        },
        "knee": {
            "derivation": "profile.world-part-plus-source-knee.v1",
            "source_pointers": [pointer for group in source_part_pointers for pointer in group] + _pointer_values(knee_prefix),
            "profile_pointers": [pointer for group in profile_part_pointers for pointer in group],
        },
        "joint_hint": {
            "source_pointer": f"/body/joints/{hip_joint_index}",
            "proximal_frame": hip_joint["proximal_frame"],
            "distal_frame": hip_joint["distal_frame"],
            "interpretation": "source hint retained for provenance; not interpreted as a solved skeleton",
        },
    }


def _profile_case(profile_id: str, source: dict[str, Any], table: dict[str, Any]) -> dict[str, Any]:
    projection = exact_five.project_profile(profile_id, source, table)
    ids = tuple(exact_five.surface.GEOMETRY_COMPONENT_IDS)
    components = {component: float(value) for component, value in zip(ids, projection["carrier"].values)}
    profile_index = projection["profile_index"]
    row = table["profiles"][profile_index]
    attachments = {}
    bindings = {}
    for side in ("left", "right"):
        world_part = _part_world_translation(source, row, _part_key(side))
        indexes = _source_indexes(source)
        start_index = indexes["landmarks"][(side, "thigh", "form_leg_profile_thigh_start")]
        knee_index = indexes["landmarks"][(side, "thigh", "form_leg_profile_knee")]
        start = source["body"]["landmarks"][start_index]["position"]
        knee = source["body"]["landmarks"][knee_index]["position"]
        attachments[side] = {
            "centre": [world_part[index] + float(start[index]) for index in range(3)],
            "knee": [world_part[index] + float(knee[index]) for index in range(3)],
        }
        bindings[side] = _attachment_provenance(source, row, profile_index, side)
    return {
        "id": profile_id,
        "role": "exactfive_unchanged_profileprojection",
        "components": components,
        "attachments": attachments,
        "provenance": {
            "source": {"path": SOURCE_ROLE, "sha256": SOURCE_SHA256},
            "profile": {"path": PROFILE_ROLE, "sha256": PROFILE_SHA256, "profile_id": profile_id, "profile_index": profile_index},
            "bindings": bindings,
            "claim": "unchanged exact-five profile projection; no geometry executed",
        },
    }


def _set_station(components: dict[str, float], station: str, centre: list[float], radii: tuple[float, float, float]) -> None:
    station = f"stations.{station}"
    for axis, value in zip(("x", "y", "z"), centre):
        components[f"{station}.C.{axis}"] = float(value)
    for name, value in zip(("rL", "rA", "rP"), radii):
        components[f"{station}.{name}"] = float(value)


def _set_hip(components: dict[str, float], side: str, centre: list[float], radii: tuple[float, float, float]) -> None:
    prefix = f"hips.{side}.P_s"
    components[f"{prefix}.x"], components[f"{prefix}.y"], components[f"{prefix}.z"] = map(float, centre)
    components[f"hips.{side}.r_x"], components[f"hips.{side}.r_y"], components[f"hips.{side}.r_z"] = map(float, radii)


def _human_case(neutral: dict[str, Any]) -> dict[str, Any]:
    components = {key: float(value) * 0.16 for key, value in neutral["components"].items()}
    hips = {"left": [-0.105, -0.16, 0.0], "right": [0.105, -0.16, 0.0]}
    knees = {"left": [-0.105, -0.59, 0.0], "right": [0.105, -0.59, 0.0]}
    for side in ("left", "right"):
        _set_hip(components, side, hips[side], (0.085, 0.085, 0.090))
    _set_station(components, "lower_pelvis", [0.0, -0.072, 0.0], (0.180, 0.105, 0.120))
    _set_station(components, "upper_pelvis", [0.0, -0.032, 0.0], (0.160, 0.100, 0.105))
    _set_station(components, "lower_abdomen", [0.0, 0.040, 0.0], (0.135, 0.090, 0.090))
    _set_station(components, "waist_abdomen", [0.0, 0.080, 0.0], (0.120, 0.080, 0.075))
    return {
        "id": HUMAN_ID,
        "role": "executable_cross_family_challenge",
        "components": components,
        "attachments": {side: {"centre": hips[side], "knee": knees[side]} for side in ("left", "right")},
        "provenance": {
            "source": {"path": SOURCE_ROLE, "sha256": SOURCE_SHA256},
            "profile": {"path": PROFILE_ROLE, "sha256": PROFILE_SHA256, "base_case": "standard_neutral_reference", "uniform_scale": 0.16},
            "bindings": {side: {"centre": {"derivation": "inputs.json.case-override.v1", "source_pointers": [f"/cases/5/attachments/{side}/centre"], "profile_pointers": []}, "knee": {"derivation": "inputs.json.case-override.v1", "source_pointers": [f"/cases/5/attachments/{side}/knee"], "profile_pointers": []}} for side in ("left", "right")},
            "authoritative_input_path": "experiments/pelvis-thigh-transition/inputs.json",
            "override_authority": "literal /cases/5/attachments/* pointers and numeric component overrides in this file; source/profile are only uniformly scaled base context",
            "frame": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0], "interpretation": "identity local pelvis frame; no rig or joint resolution"},
            "claim": "synthetic adult coarse pelvic proportions; not anatomical measured truth or a whole-body fixture",
        },
    }


def _copy_neutral(neutral: dict[str, Any], case_id: str, expected_change: dict[str, Any]) -> dict[str, Any]:
    return {"id": case_id, "role": "predeclared_neutral_perturbation", "components": copy.deepcopy(neutral["components"]), "attachments": copy.deepcopy(neutral["attachments"]), "provenance": {"source": {"path": SOURCE_ROLE, "sha256": SOURCE_SHA256}, "profile": {"path": PROFILE_ROLE, "sha256": PROFILE_SHA256, "base_case": "standard_neutral_reference"}, "bindings": copy.deepcopy(neutral["provenance"]["bindings"]), "expected_change": expected_change, "claim": "numeric perturbation declaration only; no geometry executed"}}


def _perturbations(neutral: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    width = _copy_neutral(neutral, PERTURBATION_IDS[0], {"direction": "pelvic lower/upper lateral radii increase"})
    width["components"]["stations.lower_pelvis.rL"] *= 1.10
    width["components"]["stations.upper_pelvis.rL"] *= 1.10
    cases.append(width)

    spacing = _copy_neutral(neutral, PERTURBATION_IDS[1], {"direction": "left hip, knee and thigh start translate -x by 0.05"})
    spacing["components"]["hips.left.P_s.x"] -= 0.05
    for point in spacing["attachments"]["left"].values():
        point[0] -= 0.05
    cases.append(spacing)

    direction = _copy_neutral(neutral, PERTURBATION_IDS[2], {"direction": "left thigh direction tilts 5 degrees inward"})
    h = direction["attachments"]["left"]["centre"]
    original_knee = neutral["attachments"]["left"]["knee"]
    original_leg_length = math.sqrt(sum((original_knee[index] - h[index]) ** 2 for index in range(3)))
    direction["attachments"]["left"]["knee"] = [
        h[0] + 0.0871557427 * original_leg_length,
        h[1] - 0.9961946981 * original_leg_length,
        h[2],
    ]
    direction["provenance"]["expected_change"]["original_leg_length"] = original_leg_length
    cases.append(direction)

    front = _copy_neutral(neutral, PERTURBATION_IDS[3], {"direction": "left hip, knee and thigh start translate +z by 0.05"})
    front["components"]["hips.left.P_s.z"] += 0.05
    for point in front["attachments"]["left"].values():
        point[2] += 0.05
    cases.append(front)

    asymmetric = _copy_neutral(neutral, PERTURBATION_IDS[4], {"direction": "left x spacing -0.05, z offset +0.05, left lateral start radius +5%"})
    asymmetric["components"]["hips.left.P_s.x"] -= 0.05
    asymmetric["components"]["hips.left.P_s.z"] += 0.05
    asymmetric["components"]["hips.left.r_x"] *= 1.05
    for point in asymmetric["attachments"]["left"].values():
        point[0] -= 0.05
        point[2] += 0.05
    cases.append(asymmetric)

    invalid = _copy_neutral(neutral, PERTURBATION_IDS[5], {"direction": "deliberately incompatible medial overlap; expected rejection"})
    invalid["components"]["hips.left.P_s.x"] = -0.2
    invalid["components"]["hips.right.P_s.x"] = 0.2
    invalid["components"]["hips.left.r_x"] = 0.35
    invalid["components"]["hips.right.r_x"] = 0.35
    for side, x in (("left", -0.2), ("right", 0.2)):
        invalid["attachments"][side]["centre"][0] = x
        invalid["attachments"][side]["knee"][0] = x
    cases.append(invalid)
    return cases


def _validate_case(case: dict[str, Any], ids: tuple[str, ...]) -> None:
    if set(case) != {"id", "role", "components", "attachments", "provenance"}:
        raise ValueError(f"case shape mismatch: {case.get('id')}")
    if tuple(case["components"]) != ids or any(type(value) is not float or not math.isfinite(value) for value in case["components"].values()):
        raise ValueError(f"component carrier mismatch: {case['id']}")
    for side in ("left", "right"):
        for name in ("centre", "knee"):
            point = case["attachments"][side][name]
            if type(point) is not list or len(point) != 3 or any(type(value) is not float or not math.isfinite(value) for value in point):
                raise ValueError(f"attachment mismatch: {case['id']} {side} {name}")


def load_cases() -> list[dict[str, Any]]:
    """Return concrete carriers and attachment inputs without constructing geometry."""
    source = _load_json(SOURCE_PATH)
    table = _load_json(PROFILE_PATH)
    _validate_identity_thigh_inputs(source)
    profile_cases = [_profile_case(profile_id, source, table) for profile_id in PROFILE_IDS]
    human = _human_case(profile_cases[0])
    cases = [*profile_cases, human, *_perturbations(profile_cases[0])]
    ids = tuple(exact_five.surface.GEOMETRY_COMPONENT_IDS)
    for case in cases:
        _validate_case(case, ids)
    return cases


def _document(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "creature-kernel.pelvis-thigh-transition-inputs.v1",
        "source": {"path": SOURCE_ROLE, "sha256": SOURCE_SHA256},
        "profile_table": {"path": PROFILE_ROLE, "sha256": PROFILE_SHA256},
        "component_ids": list(exact_five.surface.GEOMETRY_COMPONENT_IDS),
        "mandatory_case_ids": [*PROFILE_IDS, HUMAN_ID],
        "perturbation_case_ids": list(PERTURBATION_IDS),
        "cases": cases,
        "immutability": "mandatory fixtures and perturbations are fixed once this file is written",
    }


def _bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, separators=(",", ": ")) + "\n").encode("utf-8")


def _path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute() or path != Path(*path.parts) or path != path.resolve(strict=False):
        raise ValueError("path must be absolute and canonical")
    return path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] not in {"--write-inputs", "--check-inputs"}:
        raise SystemExit("usage: cases.py --write-inputs ABSENT_PATH | --check-inputs PATH")
    path = _path(argv[1])
    expected = _bytes(_document(load_cases()))
    if argv[0] == "--write-inputs":
        if path.exists() or path.is_symlink():
            raise ValueError(f"refusing to replace existing input file: {path}")
        path.write_bytes(expected)
        return 0
    actual = path.read_bytes()
    if actual != expected:
        raise ValueError("inputs.json does not match current concrete case generation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("surface_preview", ROOT / "surface_preview.py")
assert SPEC and SPEC.loader
surface_preview = importlib.util.module_from_spec(SPEC)
sys.modules["surface_preview"] = surface_preview
SPEC.loader.exec_module(surface_preview)


def address(role: str, anchors: list[str] | None = None) -> dict[str, object]:
    return {"namespace": "main", "anchors": anchors or [], "kind": "part", "role": role}


def fixed_display_factors(profile_id: str, role: str, shape_name: str) -> tuple[int, ...]:
    if shape_name == "ellipsoid":
        if profile_id == "neutral-v0":
            return (1_000, 1_000, 1_000)
        if profile_id == "broad-soft-v0":
            if role in {"pelvis", "torso", "head"}:
                return (1_200, 1_000, 1_150)
            if role in {"hand", "foot"}:
                return (1_150, 1_000, 1_150)
            return (1_000, 1_000, 1_000)
        if profile_id == "lean-readable-v0":
            return (800, 1_000, 800)
        if profile_id == "depth-forward-v0":
            if role in {"torso", "head", "foot"}:
                return (1_000, 1_000, 1_300)
            return (1_000, 1_000, 1_000)
    if shape_name == "capsule":
        return ((1_150 if profile_id == "broad-soft-v0" else 800 if profile_id == "lean-readable-v0" else 1_000),)
    if shape_name == "tapered-segment":
        factor = 1_150 if profile_id == "broad-soft-v0" else 800 if profile_id == "lean-readable-v0" else 1_000
        return (factor, factor)
    raise AssertionError(f"unsupported fixture shape {shape_name!r}")


def apply_fixed_display_factors(item: dict[str, object], profile_id: str) -> None:
    shape = item["shape"]
    role = item["address"]["role"]
    factors = fixed_display_factors(profile_id, role, shape["name"])
    if shape["name"] == "ellipsoid":
        shape["axis_extents_permille"] = [
            value * factor // 1_000
            for value, factor in zip(shape["axis_extents_permille"], factors)
        ]
    elif shape["name"] == "capsule":
        shape["radius_permille"] = shape["radius_permille"] * factors[0] // 1_000
    else:
        shape["start_radius_permille"] = shape["start_radius_permille"] * factors[0] // 1_000
        shape["end_radius_permille"] = shape["end_radius_permille"] * factors[1] // 1_000


def make_payload() -> dict[str, object]:
    dimension_roles = {
        "ellipsoid": ["form_extent_x", "form_extent_y", "form_extent_z"],
        "capsule": ["form_radius"],
        "tapered-segment": ["form_start_radius", "form_end_radius"],
    }

    def descriptor(role: str, point: list[int], parent: dict[str, object] | None, shape: dict[str, object], anchors: list[str] | None = None) -> dict[str, object]:
        roles = ["form_radius", "form_shoulder_depth_radius"] if role == "upper_arm" else dimension_roles[shape["name"]]
        return {"descriptor_kind": "display-only-form-descriptor", "address": address(role, anchors), "parent": parent, "placement_source": "authored-root" if parent is None else "authored-containment", "reference_point": point, "dimension_roles": roles, "profile_id": "neutral-v0", "source": "profile-derived-display", "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2", "shape_basis": "source-authored-dimensions-plus-fixed-display-factor"}, "shape": shape}
    pelvis = address("pelvis")
    descriptors = [
        descriptor("pelvis", [0, 0, 0], None, {"name": "ellipsoid", "center": [0, 0, 0], "axis_extents_permille": [1700, 1200, 900]}),
        descriptor("torso", [0, 1, 0], pelvis, {"name": "ellipsoid", "center": [0, 1, 0], "axis_extents_permille": [1650, 1200, 900]}),
        descriptor("neck", [0, 2, 0], address("torso"), {"name": "capsule", "from": [0, 2, 0], "to": [0, 3, 0], "radius_permille": 350}),
        descriptor("head", [0, 3, 0], address("neck"), {"name": "ellipsoid", "center": [0, 3, 0], "axis_extents_permille": [1000, 600, 900]}),
        descriptor("upper_arm", [-1, 2, 0], address("torso"), {"name": "capsule", "from": [-1, 2, 0], "to": [-2, 2, 0], "radius_permille": 220}, ["left"]),
        descriptor("forearm", [-2, 2, 0], address("upper_arm", ["left"]), {"name": "capsule", "from": [-2, 2, 0], "to": [-3, 2, 0], "radius_permille": 190}, ["left"]),
        descriptor("hand", [-3, 2, 0], address("forearm", ["left"]), {"name": "ellipsoid", "center": [-3, 2, 0], "axis_extents_permille": [450, 400, 350]}, ["left"]),
        descriptor("upper_arm", [1, 2, 0], address("torso"), {"name": "capsule", "from": [1, 2, 0], "to": [2, 2, 0], "radius_permille": 220}, ["right"]),
        descriptor("forearm", [2, 2, 0], address("upper_arm", ["right"]), {"name": "capsule", "from": [2, 2, 0], "to": [3, 2, 0], "radius_permille": 190}, ["right"]),
        descriptor("hand", [3, 2, 0], address("forearm", ["right"]), {"name": "ellipsoid", "center": [3, 2, 0], "axis_extents_permille": [450, 400, 350]}, ["right"]),
        descriptor("thigh", [-1, -1, 0], pelvis, {"name": "capsule", "from": [-1, -1, 0], "to": [-1, -2, 0], "radius_permille": 280}, ["left"]),
        descriptor("shin", [-1, -2, 0], address("thigh", ["left"]), {"name": "capsule", "from": [-1, -2, 0], "to": [-1, -3, 1], "radius_permille": 220}, ["left"]),
        descriptor("foot", [-1, -3, 1], address("shin", ["left"]), {"name": "ellipsoid", "center": [-1, -3, 1], "axis_extents_permille": [500, 350, 700]}, ["left"]),
        descriptor("thigh", [1, -1, 0], pelvis, {"name": "capsule", "from": [1, -1, 0], "to": [1, -2, 0], "radius_permille": 280}, ["right"]),
        descriptor("shin", [1, -2, 0], address("thigh", ["right"]), {"name": "capsule", "from": [1, -2, 0], "to": [1, -3, 1], "radius_permille": 220}, ["right"]),
        descriptor("foot", [1, -3, 1], address("shin", ["right"]), {"name": "ellipsoid", "center": [1, -3, 1], "axis_extents_permille": [500, 350, 700]}, ["right"]),
        descriptor("tail_root", [0, 0, -1], pelvis, {"name": "tapered-segment", "from": [0, 0, 0], "to": [0, 0, -1], "start_radius_permille": 300, "end_radius_permille": 220}, ["tail"]),
        descriptor("tail_tip", [0, 0, -2], address("tail_root", ["tail"]), {"name": "tapered-segment", "from": [0, 0, -1], "to": [0, 0, -2], "start_radius_permille": 220, "end_radius_permille": 40}, ["tail"]),
    ]
    descriptors.sort(key=lambda item: (item["address"]["namespace"], tuple(item["address"]["anchors"]), item["address"]["kind"], item["address"]["role"]))
    torso_specs = [
        ("lower-pelvis", "pelvis", -0.45, (1500, 850, 600)),
        ("upper-pelvis", "pelvis", -0.20, (1350, 780, 560)),
        ("lower-abdomen", "torso", 0.10, (1050, 620, 500)),
        ("waist-abdomen", "torso", 0.30, (900, 520, 420)),
        ("upper-abdomen", "torso", 0.50, (1125, 650, 500)),
        ("lower-ribcage", "torso", 0.75, (1400, 850, 650)),
        ("upper-ribcage-shoulder", "torso", 0.95, (1500, 900, 700)),
    ]
    head_neck_specs = [
        ("neck-collar", "neck", 0.15, 0.0, (420, 380, 400)),
        ("neck-upper", "neck", 0.55, 0.0, (340, 320, 330)),
        ("head-base", "head", -0.35, 0.0, (520, 400, 480)),
        ("cranium-mid", "head", 0.05, 0.0, (780, 560, 720)),
        ("cranium-crown", "head", 0.40, 0.0, (700, 520, 650)),
        ("muzzle-root", "head", -0.10, 0.25, (500, 360, 520)),
        ("muzzle-mid", "head", -0.12, 0.55, (430, 300, 500)),
        ("muzzle-tip", "head", -0.12, 0.80, (340, 240, 360)),
    ]
    arm_specs = [
        ("upper-arm-start", "upper_arm", 0.0, (350, 300, 320)),
        ("upper-arm-midpoint", "upper_arm", -0.5, (250, 240, 230)),
        ("elbow", "upper_arm", -1.0, (230, 220, 210)),
        ("forearm-midpoint", "forearm", -0.5, (210, 200, 190)),
        ("forearm-distal", "forearm", -1.0, (180, 170, 160)),
    ]
    leg_specs = [
        ("thigh-start", "thigh", 0.0, (320, 280, 300)),
        ("thigh-midpoint", "thigh", -0.5, (300, 260, 280)),
        ("knee", "thigh", -1.0, (240, 210, 225)),
        ("shin-midpoint", "shin", -0.5, (225, 195, 210)),
        ("hock-endpoint", "shin", -1.0, (185, 165, 175)),
    ]
    foot_specs = [
        ("pad", -0.2, 0.36, (320, 150, 300)),
        ("toe", -0.2, 0.72, (260, 150, 240)),
    ]
    authored_dimensions = []
    for item in descriptors:
        shape = item["shape"]
        if shape["name"] == "ellipsoid":
            values = shape["axis_extents_permille"]
        elif shape["name"] == "capsule":
            values = [shape["radius_permille"]]
        else:
            values = [shape["start_radius_permille"], shape["end_radius_permille"]]
        if item["address"]["role"] == "upper_arm":
            values = [shape["radius_permille"], 350]
        for role, value in zip(item["dimension_roles"], values):
            authored_dimensions.append({
                "owner": copy.deepcopy(item["address"]),
                "role": role,
                "value_permille": value,
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
    for name, owner_role, _, radii in torso_specs:
        owner = address(owner_role)
        underscore_name = name.replace("-", "_")
        for suffix, value in zip(surface_preview.TORSO_PROFILE_DIMENSION_SUFFIXES, radii):
            authored_dimensions.append({
                "owner": copy.deepcopy(owner),
                "role": surface_preview.TORSO_PROFILE_DIMENSION_PREFIX + underscore_name + "_" + suffix,
                "value_permille": value,
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
    for name, owner_role, _, _, radii in head_neck_specs:
        owner = address(owner_role)
        underscore_name = name.replace("-", "_")
        for suffix, value in zip(surface_preview.HEAD_NECK_PROFILE_DIMENSION_SUFFIXES, radii):
            authored_dimensions.append({
                "owner": copy.deepcopy(owner),
                "role": surface_preview.HEAD_NECK_PROFILE_DIMENSION_PREFIX + underscore_name + "_" + suffix,
                "value_permille": value,
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
    for side in ("left", "right"):
        for name, owner_role, _, radii in arm_specs:
            owner = address(owner_role, [side])
            underscore_name = name.replace("-", "_")
            for suffix, value in zip(surface_preview.ARM_PROFILE_DIMENSION_SUFFIXES, radii):
                authored_dimensions.append({
                    "owner": copy.deepcopy(owner),
                    "role": surface_preview.ARM_PROFILE_DIMENSION_PREFIX + underscore_name + "_" + suffix,
                    "value_permille": value,
                    "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
                })
        for name, owner_role, _, radii in leg_specs:
            owner = address(owner_role, [side])
            underscore_name = name.replace("-", "_")
            for suffix, value in zip(surface_preview.LEG_PROFILE_DIMENSION_SUFFIXES, radii):
                authored_dimensions.append({
                    "owner": copy.deepcopy(owner),
                    "role": surface_preview.LEG_PROFILE_DIMENSION_PREFIX + underscore_name + "_" + suffix,
                    "value_permille": value,
                    "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
                })
        for name, _, _, radii in foot_specs:
            owner = address("foot", [side])
            for suffix, value in zip(surface_preview.FOOT_PROFILE_DIMENSION_SUFFIXES, radii):
                authored_dimensions.append({
                    "owner": copy.deepcopy(owner),
                    "role": surface_preview.FOOT_PROFILE_DIMENSION_PREFIX + name + "_" + suffix,
                    "value_permille": value,
                    "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
                })
    authored_dimensions.sort(key=lambda item: (item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]))
    variants = []
    for variant_id in surface_preview.VARIANT_IDS:
        current = copy.deepcopy(descriptors)
        for item in current:
            item["profile_id"] = variant_id
            item["provenance"]["resource_profile_id"] = "ck.resource.body.r2"
            apply_fixed_display_factors(item, variant_id)
        torso_profile_sections = []
        for index, (name, owner_role, y, radii) in enumerate(torso_specs):
            lateral_factor, depth_factor = surface_preview._torso_profile_factors(variant_id, owner_role)
            torso_profile_sections.append({
                "source_section_index": index,
                "name": name,
                "position": [0.0, y, 0.0],
                "lateral_radius_permille": radii[0] * lateral_factor // 1_000,
                "anterior_radius_permille": radii[1] * depth_factor // 1_000,
                "posterior_radius_permille": radii[2] * depth_factor // 1_000,
                "scaling": {
                    "lateral_factor_permille": lateral_factor,
                    "anterior_factor_permille": depth_factor,
                    "posterior_factor_permille": depth_factor,
                },
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
        head_neck_profile_sections = []
        for index, (name, owner_role, y, z, radii) in enumerate(head_neck_specs):
            factors = surface_preview._head_neck_profile_factors(variant_id, owner_role)
            head_neck_profile_sections.append({
                "source_section_index": index,
                "name": name,
                "position": [0.0, y, z],
                "lateral_radius_permille": radii[0] * factors[0] // 1_000,
                "up_radius_permille": radii[1] * factors[1] // 1_000,
                "forward_radius_permille": radii[2] * factors[2] // 1_000,
                "scaling": {
                    "lateral_factor_permille": factors[0],
                    "up_factor_permille": factors[1],
                    "forward_factor_permille": factors[2],
                },
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
        arm_profile_sides = []
        for side in ("left", "right"):
            factors = surface_preview._arm_profile_factors(variant_id)
            arm_profile_sides.append({
                "side": side,
                "sections": [
                    {
                        "source_section_index": index,
                        "name": name,
                        "position": [0.0, y, 0.0],
                        "lateral_radius_permille": radii[0] * factors[0] // 1_000,
                        "up_radius_permille": radii[1] * factors[1] // 1_000,
                        "forward_radius_permille": radii[2] * factors[2] // 1_000,
                        "scaling": {
                            "lateral_factor_permille": factors[0],
                            "up_factor_permille": factors[1],
                            "forward_factor_permille": factors[2],
                        },
                        "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
                    }
                    for index, (name, _, y, radii) in enumerate(arm_specs)
                ],
            })
        leg_profile_sides = []
        for side in ("left", "right"):
            factors = surface_preview._arm_profile_factors(variant_id)
            leg_profile_sides.append({
                "side": side,
                "sections": [
                    {
                        "source_section_index": index,
                        "name": name,
                        "position": [0.0, y, 0.0],
                        "lateral_radius_permille": radii[0] * factors[0] // 1_000,
                        "up_radius_permille": radii[1] * factors[1] // 1_000,
                        "forward_radius_permille": radii[2] * factors[2] // 1_000,
                        "scaling": {
                            "lateral_factor_permille": factors[0],
                            "up_factor_permille": factors[1],
                            "forward_factor_permille": factors[2],
                        },
                        "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
                    }
                    for index, (name, _, y, radii) in enumerate(leg_specs)
                ],
            })
        foot_profile_sides = []
        for side_index, side in enumerate(("left", "right")):
            factors = surface_preview._foot_profile_factors(variant_id)
            foot_profile_sides.append({
                "side": side,
                "hock_binding": {
                    "source_profile": "authored_leg_profile",
                    "side_index": side_index,
                    "section_index": surface_preview.FOOT_PROFILE_HOCK_SECTION_INDEX,
                },
                "sections": [
                    {
                        "source_section_index": index,
                        "name": name,
                        "position": [0.0, y, z],
                        "lateral_radius_permille": radii[0] * factors[0] // 1_000,
                        "up_radius_permille": radii[1] * factors[1] // 1_000,
                        "forward_radius_permille": radii[2] * factors[2] // 1_000,
                        "scaling": {
                            "lateral_factor_permille": factors[0],
                            "up_factor_permille": factors[1],
                            "forward_factor_permille": factors[2],
                        },
                        "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
                    }
                    for index, (name, y, z, radii) in enumerate(foot_specs)
                ],
            })
        head_neck_connections = [
            {"name": name, "from_section_index": from_index, "to_section_index": to_index, "route": route}
            for name, from_index, to_index, route in surface_preview.HEAD_NECK_PROFILE_CONNECTIONS
        ]
        variants.append({"id": variant_id, "profile_id": variant_id, "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2", "shape_basis": "source-authored-dimensions-plus-fixed-display-factor"}, "descriptors": current, "torso_profile": {"format": surface_preview.AUTHORED_TORSO_PROFILE_FORMAT, "source": "authored_torso_profile", "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}, "sections": torso_profile_sections}, "head_neck_profile": {"format": surface_preview.AUTHORED_HEAD_NECK_PROFILE_FORMAT, "source": "authored_head_neck_profile", "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}, "sections": head_neck_profile_sections, "connections": head_neck_connections}, "arm_profile": {"format": surface_preview.AUTHORED_ARM_PROFILE_FORMAT, "source": "authored_arm_profile", "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}, "sides": arm_profile_sides}, "leg_profile": {"format": surface_preview.AUTHORED_LEG_PROFILE_FORMAT, "source": "authored_leg_profile", "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}, "sides": leg_profile_sides}, "foot_profile": {"format": surface_preview.AUTHORED_FOOT_PROFILE_FORMAT, "source": "authored_foot_profile", "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}, "sides": foot_profile_sides}})
    authored_landmarks = [
        {"owner": address("upper_arm", ["left"]), "role": "form_shoulder_peak", "frame": {"owner": address("upper_arm", ["left"]), "role": "form_shoulder_control"}, "position": [-0.1, 0.15, 0.0], "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}},
        {"owner": address("upper_arm", ["left"]), "role": "form_axilla", "frame": {"owner": address("upper_arm", ["left"]), "role": "form_shoulder_control"}, "position": [-0.1, -0.3, 0.0], "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}},
        {"owner": address("upper_arm", ["right"]), "role": "form_shoulder_peak", "frame": {"owner": address("upper_arm", ["right"]), "role": "form_shoulder_control"}, "position": [0.1, 0.15, 0.0], "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}},
        {"owner": address("upper_arm", ["right"]), "role": "form_axilla", "frame": {"owner": address("upper_arm", ["right"]), "role": "form_shoulder_control"}, "position": [0.1, -0.3, 0.0], "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}},
    ]
    for name, owner_role, y, _ in torso_specs:
        owner = address(owner_role)
        authored_landmarks.append({
            "owner": copy.deepcopy(owner),
            "role": surface_preview.TORSO_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"),
            "frame": {"owner": copy.deepcopy(owner), "role": surface_preview.TORSO_PROFILE_FRAME_ROLE},
            "position": [0.0, y, 0.0],
            "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
        })
    for name, owner_role, y, z, _ in head_neck_specs:
        owner = address(owner_role)
        authored_landmarks.append({
            "owner": copy.deepcopy(owner),
            "role": surface_preview.HEAD_NECK_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"),
            "frame": {"owner": copy.deepcopy(owner), "role": surface_preview.HEAD_NECK_PROFILE_FRAME_ROLE},
            "position": [0.0, y, z],
            "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
        })
    for side in ("left", "right"):
        for name, owner_role, y, _ in arm_specs:
            owner = address(owner_role, [side])
            authored_landmarks.append({
                "owner": copy.deepcopy(owner),
                "role": surface_preview.ARM_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"),
                "frame": {"owner": copy.deepcopy(owner), "role": surface_preview.ARM_PROFILE_CONTROL_FRAME_ROLE},
                "position": [0.0, y, 0.0],
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
        for name, owner_role, y, _ in leg_specs:
            owner = address(owner_role, [side])
            authored_landmarks.append({
                "owner": copy.deepcopy(owner),
                "role": surface_preview.LEG_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"),
                "frame": {"owner": copy.deepcopy(owner), "role": surface_preview.LEG_PROFILE_CONTROL_FRAME_ROLE},
                "position": [0.0, y, 0.0],
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
        for name, y, z, _ in foot_specs:
            owner = address("foot", [side])
            authored_landmarks.append({
                "owner": copy.deepcopy(owner),
                "role": surface_preview.FOOT_PROFILE_LANDMARK_PREFIX + name,
                "frame": {"owner": copy.deepcopy(owner), "role": surface_preview.FOOT_PROFILE_CONTROL_FRAME_ROLE},
                "position": [0.0, y, z],
                "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
            })
    authored_landmarks.sort(key=lambda item: (item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]))
    authored_frames = [
        {"owner": address(role), "role": surface_preview.HEAD_NECK_PROFILE_FRAME_ROLE, "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}, "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}}
        for role in ("head", "neck")
    ] + [
        {"owner": address(role), "role": surface_preview.TORSO_PROFILE_FRAME_ROLE, "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}, "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}}
        for role in ("pelvis", "torso")
    ] + [
        {"owner": address("upper_arm", [side]), "role": "form_shoulder_control", "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}, "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}}
        for side in ("left", "right")
    ] + [
        {"owner": address(owner_role, [side]), "role": surface_preview.ARM_PROFILE_CONTROL_FRAME_ROLE, "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}, "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}}
        for side in ("left", "right")
        for owner_role in ("forearm", "upper_arm")
    ] + [
        {"owner": address(owner_role, [side]), "role": surface_preview.LEG_PROFILE_CONTROL_FRAME_ROLE, "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}, "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}}
        for side in ("left", "right")
        for owner_role in ("shin", "thigh")
    ] + [
        {"owner": address("foot", [side]), "role": surface_preview.FOOT_PROFILE_CONTROL_FRAME_ROLE, "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}, "provenance": {"source": "source-authored", "document": "test", "namespace": "main"}}
        for side in ("left", "right")
    ]
    authored_frames.sort(key=lambda item: (item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]))
    source_provenance = {"source": "source-authored", "document": "test", "namespace": "main"}
    frame_indices = {
        (item["owner"]["role"], tuple(item["owner"]["anchors"]), item["role"]): index
        for index, item in enumerate(authored_frames)
    }
    landmark_indices = {
        (item["owner"]["role"], tuple(item["owner"]["anchors"]), item["role"]): index
        for index, item in enumerate(authored_landmarks)
    }
    dimension_indices = {
        (item["owner"]["role"], tuple(item["owner"]["anchors"]), item["role"]): index
        for index, item in enumerate(authored_dimensions)
    }
    authored_torso_profile = {
        "format": surface_preview.AUTHORED_TORSO_PROFILE_FORMAT,
        "provenance": copy.deepcopy(source_provenance),
        "sections": [
            {
                "name": name,
                "frame_index": frame_indices[(owner_role, (), surface_preview.TORSO_PROFILE_FRAME_ROLE)],
                "landmark_index": landmark_indices[(owner_role, (), surface_preview.TORSO_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))],
                "dimension_indices": {
                    suffix.split("_")[0]: dimension_indices[(owner_role, (), surface_preview.TORSO_PROFILE_DIMENSION_PREFIX + name.replace("-", "_") + "_" + suffix)]
                    for suffix in surface_preview.TORSO_PROFILE_DIMENSION_SUFFIXES
                },
                "provenance": copy.deepcopy(source_provenance),
                "section_index": index,
            }
            for index, (name, owner_role, _, _) in enumerate(torso_specs)
        ],
    }
    authored_head_neck_profile = {
        "format": surface_preview.AUTHORED_HEAD_NECK_PROFILE_FORMAT,
        "provenance": copy.deepcopy(source_provenance),
        "sections": [
            {
                "name": name,
                "frame_index": frame_indices[(owner_role, (), surface_preview.HEAD_NECK_PROFILE_FRAME_ROLE)],
                "landmark_index": landmark_indices[(owner_role, (), surface_preview.HEAD_NECK_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))],
                "dimension_indices": {
                    suffix.split("_")[0]: dimension_indices[(owner_role, (), surface_preview.HEAD_NECK_PROFILE_DIMENSION_PREFIX + name.replace("-", "_") + "_" + suffix)]
                    for suffix in surface_preview.HEAD_NECK_PROFILE_DIMENSION_SUFFIXES
                },
                "provenance": copy.deepcopy(source_provenance),
                "section_index": index,
            }
            for index, (name, owner_role, _, _, _) in enumerate(head_neck_specs)
        ],
        "connections": [
            {"name": name, "from_section_index": from_index, "to_section_index": to_index, "route": route}
            for name, from_index, to_index, route in surface_preview.HEAD_NECK_PROFILE_CONNECTIONS
        ],
    }
    authored_arm_profile = {
        "format": surface_preview.AUTHORED_ARM_PROFILE_FORMAT,
        "provenance": copy.deepcopy(source_provenance),
        "sides": [
            {
                "side": side,
                "sections": [
                    {
                        "name": name,
                        "frame_index": frame_indices[(owner_role, (side,), surface_preview.ARM_PROFILE_CONTROL_FRAME_ROLE)],
                        "landmark_index": landmark_indices[(owner_role, (side,), surface_preview.ARM_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))],
                        "dimension_indices": {
                            suffix.split("_")[0]: dimension_indices[(owner_role, (side,), surface_preview.ARM_PROFILE_DIMENSION_PREFIX + name.replace("-", "_") + "_" + suffix)]
                            for suffix in surface_preview.ARM_PROFILE_DIMENSION_SUFFIXES
                        },
                        "provenance": copy.deepcopy(source_provenance),
                        "section_index": index,
                    }
                    for index, (name, owner_role, _, _) in enumerate(arm_specs)
                ],
            }
            for side in ("left", "right")
        ],
    }
    authored_leg_profile = {
        "format": surface_preview.AUTHORED_LEG_PROFILE_FORMAT,
        "provenance": copy.deepcopy(source_provenance),
        "sides": [
            {
                "side": side,
                "sections": [
                    {
                        "name": name,
                        "frame_index": frame_indices[(owner_role, (side,), surface_preview.LEG_PROFILE_CONTROL_FRAME_ROLE)],
                        "landmark_index": landmark_indices[(owner_role, (side,), surface_preview.LEG_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))],
                        "dimension_indices": {
                            suffix.split("_")[0]: dimension_indices[(owner_role, (side,), surface_preview.LEG_PROFILE_DIMENSION_PREFIX + name.replace("-", "_") + "_" + suffix)]
                            for suffix in surface_preview.LEG_PROFILE_DIMENSION_SUFFIXES
                        },
                        "provenance": copy.deepcopy(source_provenance),
                        "section_index": index,
                    }
                    for index, (name, owner_role, _, _) in enumerate(leg_specs)
                ],
            }
            for side in ("left", "right")
        ],
    }
    authored_foot_profile = {
        "format": surface_preview.AUTHORED_FOOT_PROFILE_FORMAT,
        "provenance": copy.deepcopy(source_provenance),
        "sides": [
            {
                "side": side,
                "hock_binding": {
                    "source_profile": "authored_leg_profile",
                    "side_index": side_index,
                    "section_index": surface_preview.FOOT_PROFILE_HOCK_SECTION_INDEX,
                },
                "sections": [
                    {
                        "name": name,
                        "frame_index": frame_indices[("foot", (side,), surface_preview.FOOT_PROFILE_CONTROL_FRAME_ROLE)],
                        "landmark_index": landmark_indices[("foot", (side,), surface_preview.FOOT_PROFILE_LANDMARK_PREFIX + name)],
                        "dimension_indices": {
                            suffix.split("_")[0]: dimension_indices[("foot", (side,), surface_preview.FOOT_PROFILE_DIMENSION_PREFIX + name + "_" + suffix)]
                            for suffix in surface_preview.FOOT_PROFILE_DIMENSION_SUFFIXES
                        },
                        "provenance": copy.deepcopy(source_provenance),
                        "section_index": index,
                    }
                    for index, (name, _, _, _) in enumerate(foot_specs)
                ],
            }
            for side_index, side in enumerate(("left", "right"))
        ],
    }
    payload = {"format": surface_preview.SOURCE_FORMAT, "operation": "inspect-provisional-form", "status": "success", "stage": "provisional-form", "processing_complete": True, "diagnostics_complete": True, "diagnostics": [], "source": {"document": "test", "namespace": "main", "resource_profile_id": "ck.resource.body.r2"}, "reference_scale": {"parent": address("neck"), "child": address("head"), "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}, "authored_dimensions": authored_dimensions, "authored_landmarks": authored_landmarks, "authored_frames": authored_frames, "authored_torso_profile": authored_torso_profile, "authored_head_neck_profile": authored_head_neck_profile, "authored_arm_profile": authored_arm_profile, "authored_leg_profile": authored_leg_profile, "authored_foot_profile": authored_foot_profile, "variants": variants, "limitations": "Provisional display-only geometry descriptors; source-authored dimensions, shoulder controls, authored_torso_profile v1, authored_head_neck_profile v1, authored_arm_profile v1, authored_leg_profile v1, and authored_foot_profile v1 use bounded source-authored controls and fixed display factors; no production geometry or Readiness 3."}
    return payload


def make_varied_payload() -> dict[str, object]:
    return make_payload()


class SurfacePreviewTests(unittest.TestCase):
    def test_validation_preserves_four_variants_and_full_keys(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual([x[0] for x in form.variants], list(surface_preview.VARIANT_IDS))
        self.assertIn(("main", ("left",), "part", "hand"), {x.key for x in form.variants[0][1]})
        self.assertEqual(len(form.authored_dimensions), 153)
        self.assertEqual(len(form.authored_landmarks), 43)
        self.assertEqual(len(form.authored_frames), 16)
        self.assertEqual(
            form.authored_dimensions,
            tuple(sorted(form.authored_dimensions, key=lambda item: (item[0], item[1]))),
        )
        for _, descriptors, _ in form.variants:
            self.assertTrue(all(descriptor.dimension_roles for descriptor in descriptors))

    def test_validation_fails_closed_for_missing_or_invalid_authored_controls(self) -> None:
        payload = make_payload()
        payload["authored_dimensions"] = []
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview.validate_envelope(payload)

    def test_authored_arm_profile_projects_all_ten_stations_and_thirty_radii_with_lineage(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual(
            tuple(side.side for side in form.authored_arm_profile.sides),
            surface_preview.ARM_PROFILE_SIDE_NAMES,
        )
        self.assertEqual(
            tuple(section.name for section in form.authored_arm_profile.sides[0].sections),
            surface_preview.ARM_PROFILE_SECTION_NAMES,
        )
        radius_count = 0
        for variant_index, (variant_id, descriptors, _) in enumerate(form.variants):
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            projected = form.variant_arm_profiles[variant_index]
            by_key = {descriptor.key: descriptor for descriptor in descriptors}
            for authored_side, projected_side, guide_side in zip(
                form.authored_arm_profile.sides,
                projected.sides,
                guide.arm_profile.sides,
            ):
                self.assertEqual(guide_side.side, authored_side.side)
                self.assertEqual(
                    tuple(section.name for section in guide_side.sections),
                    surface_preview.ARM_PROFILE_SECTION_NAMES,
                )
                for authored, variant_section, station in zip(
                    authored_side.sections,
                    projected_side.sections,
                    guide_side.sections,
                ):
                    owner = by_key[authored.owner]
                    source = surface_preview._source_shape(owner, form.reference_scale)
                    fraction = -variant_section.position[1]
                    expected_center = tuple(
                        float(source["from"][axis] + fraction * (source["to"][axis] - source["from"][axis]))
                        for axis in range(3)
                    )
                    self.assertIs(station.owner, owner)
                    self.assertEqual(station.section_index, authored.section_index)
                    self.assertEqual(station.source_section_index, variant_section.source_section_index)
                    self.assertEqual(station.frame_index, authored.frame_index)
                    self.assertEqual(station.landmark_index, authored.landmark_index)
                    self.assertEqual(station.landmark.role, authored.landmark.role)
                    self.assertEqual(station.frame.role, surface_preview.ARM_PROFILE_CONTROL_FRAME_ROLE)
                    self.assertEqual(station.center, expected_center)
                    factors = surface_preview._arm_profile_factors(variant_id)
                    controls = (authored.lateral, authored.up, authored.forward)
                    projected_radii = (
                        variant_section.lateral_radius_permille,
                        variant_section.up_radius_permille,
                        variant_section.forward_radius_permille,
                    )
                    for lineage, control, factor, projected_radius in zip(
                        (station.lateral_lineage, station.up_lineage, station.forward_lineage),
                        controls,
                        factors,
                        projected_radii,
                    ):
                        self.assertEqual(lineage.base, control.value_permille)
                        self.assertEqual(lineage.factor, factor)
                        self.assertEqual(lineage.scaled, projected_radius)
                        self.assertEqual(lineage.reference, (owner.key, control.role))
                        self.assertEqual(lineage.reference_index, control.source_index)
                        self.assertEqual(lineage.provenance, control.provenance)
                        self.assertEqual(lineage.consumed_section, authored.name)
                        if variant_index == 0:
                            radius_count += 1
        self.assertEqual(radius_count, 30)

    def test_authored_arm_profile_preserves_route_ownership_seam_and_attachment_boundary(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        fields = surface_preview._compile_hybrid_guide(guide)
        expected_owners = ("upper_arm", "upper_arm", "upper_arm", "forearm", "forearm")
        for side in guide.arm_profile.sides:
            self.assertEqual(tuple(section.name for section in side.sections), surface_preview.ARM_PROFILE_SECTION_NAMES)
            self.assertEqual(tuple(section.owner.key[3] for section in side.sections), expected_owners)
            upper_arm = next(item for item in guide.limb_guides if item.owner.key[1:] == ((side.side,), "part", "upper_arm"))
            forearm = next(item for item in guide.limb_guides if item.owner.key[1:] == ((side.side,), "part", "forearm"))
            self.assertEqual(side.sections[0].center, upper_arm.sections[0].centerline[0])
            self.assertEqual(side.sections[2].center, upper_arm.sections[-1].centerline[1])
            expected_forearm_midpoint = tuple(
                float(forearm.sections[0].centerline[0][axis] + 0.5 * (
                    forearm.sections[-1].centerline[1][axis] - forearm.sections[0].centerline[0][axis]
                ))
                for axis in range(3)
            )
            self.assertEqual(side.sections[3].center, expected_forearm_midpoint)
            self.assertEqual(side.sections[2].owner, upper_arm.owner)
            self.assertNotEqual(side.sections[2].owner, forearm.owner)
            self.assertEqual(side.sections[2].lateral_lineage.consumed_section, "elbow")
        elbow_fields = [item for item in fields if item.recipe == "elbow"]
        self.assertEqual(len(elbow_fields), 2)
        self.assertEqual({item.owner.key[3] for item in elbow_fields}, {"upper_arm"})
        self.assertTrue(all(item.shape["name"] == "arm-profile-segment" for item in fields if item.recipe in {
            "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal",
        }))

    def test_authored_arm_profile_source_perturbation_is_local_to_one_station_and_side(self) -> None:
        baseline_form = surface_preview.validate_envelope(make_payload())
        baseline_guide = surface_preview._derive_hybrid_guides(baseline_form, baseline_form.variants[0][1])
        baseline_fields = surface_preview._compile_hybrid_guide(baseline_guide)
        payload = make_payload()
        elbow_forward_role = surface_preview.ARM_PROFILE_DIMENSION_PREFIX + "elbow_forward_radius"
        elbow_dimension = next(
            item for item in payload["authored_dimensions"]
            if item["owner"]["anchors"] == ["left"] and item["owner"]["role"] == "upper_arm" and item["role"] == elbow_forward_role
        )
        elbow_dimension["value_permille"] += 11
        for variant in payload["variants"]:
            factor = surface_preview._arm_profile_factors(variant["id"])[2]
            section = next(item for item in variant["arm_profile"]["sides"][0]["sections"] if item["name"] == "elbow")
            section["forward_radius_permille"] = elbow_dimension["value_permille"] * factor // 1_000
        changed_form = surface_preview.validate_envelope(payload)
        changed_guide = surface_preview._derive_hybrid_guides(changed_form, changed_form.variants[0][1])
        changed_fields = surface_preview._compile_hybrid_guide(changed_guide)
        baseline_sides = {side.side: side for side in baseline_guide.arm_profile.sides}
        changed_sides = {side.side: side for side in changed_guide.arm_profile.sides}
        for name in surface_preview.ARM_PROFILE_SECTION_NAMES:
            before = baseline_sides["right"].sections[surface_preview.ARM_PROFILE_SECTION_NAMES.index(name)]
            after = changed_sides["right"].sections[surface_preview.ARM_PROFILE_SECTION_NAMES.index(name)]
            self.assertEqual(before.center, after.center)
            self.assertEqual(before.radii, after.radii)
        for index, name in enumerate(surface_preview.ARM_PROFILE_SECTION_NAMES):
            before = baseline_sides["left"].sections[index]
            after = changed_sides["left"].sections[index]
            if name == "elbow":
                self.assertNotEqual(before.radii, after.radii)
                self.assertEqual(before.radii[:2], after.radii[:2])
            else:
                self.assertEqual(before.radii, after.radii)
        self.assertEqual(
            baseline_sides["left"].sections[0].center,
            changed_sides["left"].sections[0].center,
        )
        for before, after in zip(baseline_guide.shoulder_frame.sides, changed_guide.shoulder_frame.sides):
            self.assertEqual(
                surface_preview._curve_json("anterior-support", before.anterior_support.owner, before.anterior_support),
                surface_preview._curve_json("anterior-support", after.anterior_support.owner, after.anterior_support),
            )
            self.assertEqual(
                surface_preview._curve_json("posterior-return", before.posterior_return.owner, before.posterior_return),
                surface_preview._curve_json("posterior-return", after.posterior_return.owner, after.posterior_return),
            )
            self.assertEqual(
                surface_preview._curve_json("deltoid-sweep", before.deltoid_sweep.owner, before.deltoid_sweep),
                surface_preview._curve_json("deltoid-sweep", after.deltoid_sweep.owner, after.deltoid_sweep),
            )
        baseline_arm_fields = {
            (item.owner.key, item.recipe): item.shape
            for item in baseline_fields
            if item.owner.key[1] == ("left",) and item.recipe in {"upper_arm-joint", "elbow"}
        }
        changed_arm_fields = {
            (item.owner.key, item.recipe): item.shape
            for item in changed_fields
            if item.owner.key[1] == ("left",) and item.recipe in {"upper_arm-joint", "elbow"}
        }
        self.assertFalse(np.array_equal(
            baseline_arm_fields[(baseline_sides["left"].sections[1].owner.key, "upper_arm-joint")]["radii1"],
            changed_arm_fields[(baseline_sides["left"].sections[1].owner.key, "upper_arm-joint")]["radii1"],
        ))
        np.testing.assert_array_equal(
            baseline_arm_fields[(baseline_sides["left"].sections[1].owner.key, "upper_arm-joint")]["radii0"],
            changed_arm_fields[(baseline_sides["left"].sections[1].owner.key, "upper_arm-joint")]["radii0"],
        )

    def test_authored_arm_profile_keeps_legacy_underarm_support_curves_guide_only(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        fields = surface_preview._compile_hybrid_guide(guide)
        bounds = surface_preview._shared_render_bounds((fields,), 0.5)
        regional = surface_preview._regional_guide_json("neutral-v0", guide, bounds, compiled_fields=fields)
        shoulder = regional["controls"]["shoulder_frame"]
        curves = [curve for side in shoulder["sides"] for curve in side["curves"]]
        self.assertEqual(
            {curve["name"] for curve in curves if curve["consumption"] == "guide-only"},
            {"anterior-support", "posterior-return"},
        )
        self.assertTrue(all(curve["consumption"] == "guide-only" for curve in curves if curve["name"] != "deltoid-sweep"))
        self.assertEqual(
            [field.recipe for field in fields if field.recipe.startswith("shoulder-")],
            [],
        )
        self.assertEqual(
            regional["controls"]["arm_profile"]["status"],
            "skin-driving arm profile; legacy shoulder supports remain guide-only",
        )

    def test_authored_arm_profile_rejects_malformed_indices_order_ownership_scaling_and_radii(self) -> None:
        cases: list[dict[str, object]] = []
        payload = make_payload()
        payload["authored_arm_profile"]["sides"][0]["sections"][2]["section_index"] = 1
        cases.append(payload)
        payload = make_payload()
        payload["authored_arm_profile"]["sides"][0]["sections"][1]["dimension_indices"]["forward"] = payload["authored_arm_profile"]["sides"][0]["sections"][1]["dimension_indices"]["lateral"]
        cases.append(payload)
        payload = make_payload()
        payload["authored_arm_profile"]["sides"] = list(reversed(payload["authored_arm_profile"]["sides"]))
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["arm_profile"]["sides"][0]["sections"][2]["forward_radius_permille"] += 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["arm_profile"]["sides"][0]["sections"][2]["source_section_index"] = 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["arm_profile"]["sides"][0]["sections"][2]["scaling"]["lateral_factor_permille"] += 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["arm_profile"]["sides"][0]["sections"][2]["position"][0] = 0.01
        cases.append(payload)
        payload = make_payload()
        landmark_index = payload["authored_arm_profile"]["sides"][0]["sections"][2]["landmark_index"]
        payload["authored_landmarks"][landmark_index]["position"][1] = -0.5
        cases.append(payload)
        for index, malformed in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(surface_preview.PreviewError):
                surface_preview.validate_envelope(malformed)

    def test_authored_leg_profile_projects_all_ten_stations_and_thirty_radii_with_lineage(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual(tuple(side.side for side in form.authored_leg_profile.sides), surface_preview.LEG_PROFILE_SIDE_NAMES)
        self.assertEqual(tuple(section.name for section in form.authored_leg_profile.sides[0].sections), surface_preview.LEG_PROFILE_SECTION_NAMES)
        radius_count = 0
        for variant_index, (variant_id, descriptors, _) in enumerate(form.variants):
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            projected = form.variant_leg_profiles[variant_index]
            by_key = {descriptor.key: descriptor for descriptor in descriptors}
            for authored_side, projected_side, guide_side in zip(form.authored_leg_profile.sides, projected.sides, guide.leg_profile.sides):
                self.assertEqual(guide_side.side, authored_side.side)
                self.assertEqual(tuple(section.name for section in guide_side.sections), surface_preview.LEG_PROFILE_SECTION_NAMES)
                for authored, variant_section, station in zip(authored_side.sections, projected_side.sections, guide_side.sections):
                    owner = by_key[authored.owner]
                    source = surface_preview._source_shape(owner, form.reference_scale)
                    fraction = -variant_section.position[1]
                    expected_center = tuple(float(source["from"][axis] + fraction * (source["to"][axis] - source["from"][axis])) for axis in range(3))
                    self.assertIs(station.owner, owner)
                    self.assertEqual(station.center, expected_center)
                    self.assertEqual(station.frame.role, surface_preview.LEG_PROFILE_CONTROL_FRAME_ROLE)
                    self.assertEqual(station.profile_provenance, form.authored_leg_profile.provenance)
                    self.assertEqual(station.variant_provenance, variant_section.provenance)
                    factors = surface_preview._arm_profile_factors(variant_id)
                    for lineage, control, factor, projected_radius in zip(
                        (station.lateral_lineage, station.up_lineage, station.forward_lineage),
                        (authored.lateral, authored.up, authored.forward),
                        factors,
                        (variant_section.lateral_radius_permille, variant_section.up_radius_permille, variant_section.forward_radius_permille),
                    ):
                        self.assertEqual(lineage.base, control.value_permille)
                        self.assertEqual(lineage.factor, factor)
                        self.assertEqual(lineage.scaled, projected_radius)
                        self.assertEqual(lineage.reference, (owner.key, control.role))
                        self.assertEqual(lineage.reference_index, control.source_index)
                        self.assertEqual(lineage.provenance, control.provenance)
                        if variant_index == 0:
                            radius_count += 1
        self.assertEqual(radius_count, 30)

    def test_authored_leg_profile_preserves_route_ownership_seam_hock_and_full_radius_fields(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        fields = surface_preview._compile_hybrid_guide(guide)
        expected_owners = ("thigh", "thigh", "thigh", "shin", "shin")
        for side in guide.leg_profile.sides:
            self.assertEqual(tuple(section.owner.key[3] for section in side.sections), expected_owners)
            thigh = next(item for item in guide.limb_guides if item.owner.key[1:] == ((side.side,), "part", "thigh"))
            shin = next(item for item in guide.limb_guides if item.owner.key[1:] == ((side.side,), "part", "shin"))
            self.assertEqual(side.sections[0].center, thigh.sections[0].centerline[0])
            self.assertEqual(side.sections[1].center, thigh.sections[0].centerline[1])
            self.assertEqual(side.sections[2].center, thigh.sections[1].centerline[1])
            self.assertEqual(side.sections[2].center, shin.sections[0].centerline[0])
            self.assertEqual(side.sections[3].center, shin.sections[0].centerline[1])
            self.assertEqual(side.sections[4].center, shin.sections[1].centerline[1])
            self.assertEqual(thigh.joint.center, side.sections[2].center)
            self.assertEqual(shin.joint.center, side.sections[4].center)
        route_fields = [item for item in fields if item.recipe in {"thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint"}]
        self.assertEqual(len(route_fields), 8)
        self.assertTrue(all(item.shape["name"] == "leg-profile-segment" for item in route_fields))
        self.assertTrue(all(len(item.shape["radii0"]) == 3 and len(item.shape["radii1"]) == 3 for item in route_fields))
        self.assertEqual({item.owner.key[3] for item in fields if item.recipe == "knee"}, {"thigh"})
        self.assertEqual({item.owner.key[3] for item in fields if item.recipe == "hock"}, {"shin"})

    def test_authored_leg_profile_rejects_malformed_closure_owner_order_seam_radius_and_provenance(self) -> None:
        cases: list[dict[str, object]] = []
        payload = make_payload()
        payload["authored_leg_profile"]["sides"][0]["sections"][2]["section_index"] = 1
        cases.append(payload)
        payload = make_payload()
        payload["authored_leg_profile"]["sides"][0]["sections"][1]["dimension_indices"]["forward"] = payload["authored_leg_profile"]["sides"][0]["sections"][1]["dimension_indices"]["lateral"]
        cases.append(payload)
        payload = make_payload()
        payload["authored_leg_profile"]["sides"] = list(reversed(payload["authored_leg_profile"]["sides"]))
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["leg_profile"]["sides"][0]["sections"][2]["forward_radius_permille"] += 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["leg_profile"]["sides"][0]["sections"][2]["source_section_index"] = 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["leg_profile"]["sides"][0]["sections"][2]["scaling"]["lateral_factor_permille"] += 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["leg_profile"]["sides"][0]["sections"][2]["position"][0] = 0.01
        cases.append(payload)
        payload = make_payload()
        knee_index = payload["authored_leg_profile"]["sides"][0]["sections"][2]["landmark_index"]
        payload["authored_landmarks"][knee_index]["position"][1] = -0.5
        cases.append(payload)
        payload = make_payload()
        for section_index, y in enumerate((0.75, 0.25, -0.25)):
            landmark_index = payload["authored_leg_profile"]["sides"][0]["sections"][section_index]["landmark_index"]
            payload["authored_landmarks"][landmark_index]["position"][1] = y
        cases.append(payload)
        payload = make_payload()
        payload["authored_leg_profile"]["sides"][0]["sections"][2]["provenance"]["source"] = "tampered"
        cases.append(payload)
        for index, malformed in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(surface_preview.PreviewError):
                surface_preview.validate_envelope(malformed)

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        side = guide.leg_profile.left
        broken_station = dataclasses.replace(side.sections[2], center=(side.sections[2].center[0], side.sections[2].center[1] + 0.1, side.sections[2].center[2]))
        broken_side = dataclasses.replace(side, sections=(*side.sections[:2], broken_station, *side.sections[3:]))
        broken_profile = dataclasses.replace(guide.leg_profile, sides=(broken_side, guide.leg_profile.right))
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._compile_hybrid_guide(dataclasses.replace(guide, leg_profile=broken_profile))

    def test_authored_leg_profile_radius_perturbation_is_local_to_one_station_and_side(self) -> None:
        baseline_form = surface_preview.validate_envelope(make_payload())
        baseline_guide = surface_preview._derive_hybrid_guides(baseline_form, baseline_form.variants[0][1])
        baseline_fields = surface_preview._compile_hybrid_guide(baseline_guide)
        payload = make_payload()
        role = surface_preview.LEG_PROFILE_DIMENSION_PREFIX + "knee_forward_radius"
        dimension = next(item for item in payload["authored_dimensions"] if item["owner"]["anchors"] == ["left"] and item["owner"]["role"] == "thigh" and item["role"] == role)
        dimension["value_permille"] += 13
        for variant in payload["variants"]:
            factor = surface_preview._arm_profile_factors(variant["id"])[2]
            section = next(item for item in variant["leg_profile"]["sides"][0]["sections"] if item["name"] == "knee")
            section["forward_radius_permille"] = dimension["value_permille"] * factor // 1_000
        changed_form = surface_preview.validate_envelope(payload)
        changed_guide = surface_preview._derive_hybrid_guides(changed_form, changed_form.variants[0][1])
        changed_fields = surface_preview._compile_hybrid_guide(changed_guide)
        baseline_sides = {side.side: side for side in baseline_guide.leg_profile.sides}
        changed_sides = {side.side: side for side in changed_guide.leg_profile.sides}
        for side_name in ("left", "right"):
            for index, name in enumerate(surface_preview.LEG_PROFILE_SECTION_NAMES):
                before = baseline_sides[side_name].sections[index]
                after = changed_sides[side_name].sections[index]
                if side_name == "left" and name == "knee":
                    self.assertNotEqual(before.radii, after.radii)
                    self.assertEqual(before.radii[:2], after.radii[:2])
                else:
                    self.assertEqual(before.radii, after.radii)
                self.assertEqual(before.center, after.center)
        def field_map(fields: tuple[surface_preview.Field, ...]) -> dict[tuple[tuple[str, tuple[str, ...], str, str], str], surface_preview.Field]:
            return {(item.owner.key, item.recipe): item for item in fields}
        before = field_map(baseline_fields)
        after = field_map(changed_fields)
        self.assertNotEqual(before[(('main', ('left',), 'part', 'thigh'), "thigh-joint")].shape["radii1"].tolist(), after[(('main', ('left',), 'part', 'thigh'), "thigh-joint")].shape["radii1"].tolist())
        self.assertNotEqual(before[(('main', ('left',), 'part', 'shin'), "shin-pre-joint")].shape["radii0"].tolist(), after[(('main', ('left',), 'part', 'shin'), "shin-pre-joint")].shape["radii0"].tolist())
        self.assertEqual(before[(('main', ('right',), 'part', 'thigh'), "thigh-joint")].shape["radii1"].tolist(), after[(('main', ('right',), 'part', 'thigh'), "thigh-joint")].shape["radii1"].tolist())
        self.assertEqual(before[(('main', ('left',), 'part', 'shin'), "hock")].shape["radii"].tolist(), after[(('main', ('left',), 'part', 'shin'), "hock")].shape["radii"].tolist())

    def test_authored_leg_profile_regional_controls_are_observable_deterministic_and_keep_foot_bridge(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        fields = surface_preview._compile_hybrid_guide(guide)
        bounds = surface_preview._shared_render_bounds((fields,), 0.5)
        first = surface_preview._regional_guide_json("neutral-v0", guide, bounds, compiled_fields=fields)
        second = surface_preview._regional_guide_json("neutral-v0", guide, bounds, compiled_fields=fields)
        self.assertEqual(first, second)
        self.assertEqual(first["format"], surface_preview.REGIONAL_GUIDE_FORMAT)
        self.assertEqual(first["counts"]["leg_profile_sides"], 2)
        self.assertEqual(first["counts"]["leg_profile_sections"], 10)
        controls = first["controls"]["leg_profile"]
        self.assertEqual(controls["format"], surface_preview.AUTHORED_LEG_PROFILE_FORMAT)
        self.assertEqual(controls["route_topology"]["owner_roles"], list(surface_preview.LEG_PROFILE_OWNER_ROLES))
        self.assertEqual(controls["route_topology"]["seam"], {"name": "knee", "index": 2, "owner_role": "thigh"})
        self.assertEqual(controls["route_topology"]["endpoint"], {"name": "hock-endpoint", "index": 4, "owner_role": "shin"})
        self.assertEqual(sum(len(side["sections"]) for side in controls["sides"]), 10)
        self.assertTrue(all(set(section["lineage"]) == {"lateral", "up", "forward"} for side in controls["sides"] for section in side["sections"]))
        self.assertTrue(all(section["consumption"] == ("skin-driving; knee seam owned by thigh station" if section["name"] == "knee" else "skin-driving") for side in controls["sides"] for section in side["sections"]))
        for side in guide.leg_profile.sides:
            thigh = next(item for item in guide.limb_guides if item.owner.key[1:] == ((side.side,), "part", "thigh"))
            shin = next(item for item in guide.limb_guides if item.owner.key[1:] == ((side.side,), "part", "shin"))
            self.assertIsNotNone(thigh.root_centerline)
            self.assertIsNotNone(thigh.hip_centerline)
            foot = next(item for item in guide.paw_guides if item.owner.key[1:] == ((side.side,), "part", "foot"))
            self.assertIsNotNone(foot.foot_chain)
            assert foot.foot_chain is not None and shin.joint is not None
            self.assertEqual(foot.foot_chain.hock_anchor, side.sections[4].center)
            self.assertEqual(foot.foot_chain.hock_anchor, shin.joint.center)
            self.assertEqual(foot.foot_chain.metatarsal_centerline[0], foot.foot_chain.hock_anchor)

    def test_validation_fails_closed_for_malformed_shoulder_controls(self) -> None:
        cases: list[dict[str, object]] = []

        missing_landmark = make_payload()
        missing_landmark["authored_landmarks"].pop()
        cases.append(missing_landmark)

        duplicate_frame = make_payload()
        duplicate_frame["authored_frames"].append(
            copy.deepcopy(duplicate_frame["authored_frames"][0])
        )
        cases.append(duplicate_frame)

        wrong_owner = make_payload()
        wrong_owner["authored_landmarks"][0]["owner"]["role"] = "forearm"
        cases.append(wrong_owner)

        wrong_frame = make_payload()
        wrong_frame["authored_landmarks"][0]["frame"]["role"] = "wrong-frame"
        cases.append(wrong_frame)

        non_identity = make_payload()
        non_identity["authored_frames"][0]["transform"]["translation"][0] = 0.01
        cases.append(non_identity)

        out_of_bounds = make_payload()
        out_of_bounds["authored_landmarks"][0]["position"][0] = 1.01
        cases.append(out_of_bounds)

        non_finite = make_payload()
        non_finite["authored_landmarks"][0]["position"][0] = math.nan
        cases.append(non_finite)

        missing_depth = make_payload()
        missing_depth["authored_dimensions"] = [
            item
            for item in missing_depth["authored_dimensions"]
            if not (
                item["owner"]["role"] == "upper_arm"
                and item["owner"]["anchors"] == ["left"]
                and item["role"] == "form_shoulder_depth_radius"
            )
        ]
        cases.append(missing_depth)

        for index, payload in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(surface_preview.PreviewError):
                surface_preview.validate_envelope(payload)

    def test_authored_shoulder_controls_drive_variant_guides_exactly(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        expected_depth = {
            "neutral-v0": (1_000, 350, 0.350),
            "broad-soft-v0": (1_150, 402, 0.402),
            "lean-readable-v0": (800, 280, 0.280),
            "depth-forward-v0": (1_000, 350, 0.350),
        }
        for variant_id, descriptors, _ in form.variants:
            frame = surface_preview._derive_hybrid_guides(form, descriptors).shoulder_frame
            self.assertEqual(tuple(side.side for side in frame.sides), ("left", "right"))
            factor, scaled, radius = expected_depth[variant_id]
            for side in frame.sides:
                sign = -1.0 if side.side == "left" else 1.0
                self.assertEqual(side.authored_frame.translation, (0.0, 0.0, 0.0))
                self.assertEqual(side.authored_frame.rotation_xyzw, (0.0, 0.0, 0.0, 1.0))
                self.assertAlmostEqual(side.peak_anchor[0], 1.1 * sign)
                self.assertAlmostEqual(side.peak_anchor[1], 2.15)
                self.assertAlmostEqual(side.axilla_anchor[0], 1.1 * sign)
                self.assertAlmostEqual(side.axilla_anchor[1], 1.70)
                self.assertAlmostEqual(side.vertical_midpoint, 1.925)
                self.assertAlmostEqual(side.vertical_radius, 0.225)
                self.assertEqual(side.depth_value_permille, 350)
                self.assertEqual(side.depth_profile_factor, factor)
                self.assertEqual(side.depth_scaled_permille, scaled)
                self.assertAlmostEqual(side.depth_radius, radius)
                depth_control = surface_preview._shoulder_source_control_json(side)[
                    "depth_control"
                ]
                self.assertEqual(
                    depth_control["consumption"],
                    "guide-derived shoulder wrap depth; baseline field remains guide-only",
                )

        changed_payload = make_payload()
        for landmark in changed_payload["authored_landmarks"]:
            if landmark["role"] == "form_shoulder_peak":
                landmark["position"][1] = 0.25
        changed_form = surface_preview.validate_envelope(changed_payload)
        changed_frame = surface_preview._derive_hybrid_guides(
            changed_form, changed_form.variants[0][1]
        ).shoulder_frame
        self.assertTrue(all(math.isclose(side.peak_anchor[1], 2.25) for side in changed_frame.sides))
        self.assertTrue(all(math.isclose(side.vertical_radius, 0.275) for side in changed_frame.sides))
        for invalid in (0, -1, 1.5, 5001):
            payload = make_payload()
            payload["authored_dimensions"][0]["value_permille"] = invalid
            with self.assertRaises(surface_preview.PreviewError):
                surface_preview.validate_envelope(payload)
        payload = make_payload()
        payload["variants"][0]["descriptors"][0]["dimension_roles"] = ["unlisted"]
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview.validate_envelope(payload)
        payload = make_payload()
        payload["authored_dimensions"].append({
            "owner": copy.deepcopy(payload["authored_dimensions"][0]["owner"]),
            "role": "form_unconsumed",
            "value_permille": 100,
            "provenance": {"source": "source-authored", "document": "test", "namespace": "main"},
        })
        payload["authored_dimensions"].sort(
            key=lambda item: (
                item["owner"]["namespace"],
                tuple(item["owner"]["anchors"]),
                item["owner"]["kind"],
                item["owner"]["role"],
                item["role"],
            )
        )
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview.validate_envelope(payload)

    def test_validation_rejects_tampered_authored_dimension_with_unchanged_descriptors(self) -> None:
        payload = make_payload()
        payload["authored_dimensions"][0]["value_permille"] += 1
        with self.assertRaisesRegex(
            surface_preview.PreviewError,
            "shape numeric controls do not match source-authored dimensions",
        ):
            surface_preview.validate_envelope(payload)

    def test_validation_rejects_tampered_non_neutral_variant_shape_control(self) -> None:
        payload = make_payload()
        torso = next(
            item
            for item in payload["variants"][1]["descriptors"]
            if item["address"]["role"] == "torso"
        )
        torso["shape"]["axis_extents_permille"][0] += 1
        with self.assertRaisesRegex(
            surface_preview.PreviewError,
            "shape numeric controls do not match source-authored dimensions",
        ):
            surface_preview.validate_envelope(payload)

    def test_rejects_wrong_order_and_unknown_envelope_fields(self) -> None:
        payload = make_payload(); payload["variants"] = list(reversed(payload["variants"]))
        with self.assertRaises(surface_preview.PreviewError): surface_preview.validate_envelope(payload)
        payload = make_payload(); payload["extra"] = True
        with self.assertRaises(surface_preview.PreviewError): surface_preview.validate_envelope(payload)

    def test_private_hybrid_guides_are_stable_source_owned_and_backend_neutral(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        expected_keys = tuple(descriptor.key for descriptor in form.variants[0][1])
        topology_signatures = []
        geometry_signatures = []
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            topology_signatures.append(
                (
                    guide.topology.owner_keys,
                    guide.topology.parent_edges,
                    guide.topology.bilateral_pairs,
                )
            )
            regional_owners = (
                tuple(item.owner.key for item in guide.axial_guides)
                + (guide.head_guide.head_owner.key, guide.head_guide.neck_owner.key)
                + tuple(item.owner.key for item in guide.limb_guides)
                + tuple(item.owner.key for item in guide.paw_guides)
                + tuple(item.owner.key for item in guide.tail_guides)
            )
            self.assertEqual(set(regional_owners), set(expected_keys))
            self.assertEqual(guide.source_owners, descriptors)
            self.assertEqual(len(guide.axial_guides), 2)
            self.assertEqual(len(guide.limb_guides), 8)
            self.assertEqual(len(guide.paw_guides), 4)
            self.assertEqual(len(guide.tail_guides), 2)
            self.assertTrue(
                {"girdle_center", "chest_center", "waist_center"}
                <= {name for item in guide.axial_guides for name in vars(item) if name.endswith("_center")}
            )
            self.assertEqual(
                [station.name for axial in guide.axial_guides for station in axial.station_controls],
                ["pelvic-girdle", "waist", "chest-girdle"],
            )
            self.assertEqual(
                [transition.name for axial in guide.axial_guides for transition in axial.transition_controls],
                ["pelvis-waist", "waist-chest"],
            )
            station_radii = [station.radii for axial in guide.axial_guides for station in axial.station_controls]
            self.assertLess(station_radii[1][0], station_radii[0][0])
            self.assertLess(station_radii[1][2], station_radii[0][2])
            self.assertLess(station_radii[1][0], station_radii[2][0])
            self.assertLess(station_radii[1][2], station_radii[2][2])
            self.assertGreater(station_radii[1][0], station_radii[2][0] * 0.60)
            self.assertGreater(station_radii[1][2], station_radii[2][2] * 0.60)
            transitions = guide.axial_transitions
            self.assertGreaterEqual(transitions[0].thickness[1], station_radii[1][0] * 0.80)
            self.assertGreaterEqual(transitions[1].thickness[0], station_radii[1][0] * 0.80)
            stations = guide.axial_stations
            self.assertGreater(stations[0].center[1] + stations[0].radii[1], stations[1].center[1] - stations[1].radii[1])
            self.assertGreater(stations[1].center[1] + stations[1].radii[1], stations[2].center[1] - stations[2].radii[1])
            self.assertEqual(
                {guide.head_guide.head_owner.key, guide.head_guide.neck_owner.key},
                {item.key for item in descriptors if item.key[3] in {"head", "neck"}},
            )
            for item in guide.limb_guides:
                if item.joint is None:
                    continue
                if item.owner.key[3] == "upper_arm":
                    arm_side = next(side for side in guide.arm_profile.sides if side.side == item.owner.key[1][0])
                    self.assertEqual(item.joint.radii, arm_side.sections[2].radii)
                elif item.owner.key[3] in {"thigh", "shin"}:
                    leg_side = next(side for side in guide.leg_profile.sides if side.side == item.owner.key[1][0])
                    station_index = 2 if item.owner.key[3] == "thigh" else 4
                    self.assertEqual(item.joint.radii, leg_side.sections[station_index].radii)
                else:
                    self.assertLess(item.joint.radii[0], min(item.joint.adjacent_profiles))
            self.assertTrue(all(len(item.sections) == 2 and all(section.path_kind == "capsule" for section in item.sections) for item in guide.limb_guides))
            self.assertTrue(all(section.centerline[0] != section.centerline[1] for item in guide.limb_guides for section in item.sections))
            for limb in guide.limb_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in limb.profile_controls))
            for paw in guide.paw_guides:
                if paw.owner.key[3] == "hand":
                    assert paw.paw_radii is not None
                    self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in paw.paw_radii))
                else:
                    self.assertIsNone(paw.paw_radii)
                    assert paw.foot_chain is not None
                    self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in paw.foot_chain.pad_radii))
            for tail in guide.tail_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in (*tail.taper,)))
            geometry_signatures.append(
                (
                    guide.head_guide.cranium_radii,
                    tuple(item.profile_controls for item in guide.limb_guides),
                    tuple(item.taper for item in guide.tail_guides),
                )
            )
            fields = surface_preview._compile_hybrid_guide(guide)
            owners_by_key = {descriptor.key: descriptor for descriptor in descriptors}
            self.assertTrue({field.owner.key for field in fields} <= set(expected_keys))
            self.assertTrue(
                all(field.owner is owners_by_key[field.owner.key] for field in fields)
            )
            torso_field = next(item for item in fields if item.recipe == "torso-cage")
            self.assertEqual(
                {owner.key for owner in torso_field.shape["section_owners"]},
                {item.key for item in descriptors if item.key[3] in {"pelvis", "torso"}},
            )
        self.assertEqual(topology_signatures, [topology_signatures[0]] * 4)
        self.assertGreater(len(set(geometry_signatures)), 1)

    def test_private_guides_mirror_bilateral_centerlines_and_profiles(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        for left_key, right_key in guide.topology.bilateral_pairs:
            if left_key[3] in {"hand", "foot"}:
                left = next(item for item in guide.paw_guides if item.source_key == left_key)
                right = next(item for item in guide.paw_guides if item.source_key == right_key)
                if left_key[3] == "hand":
                    self.assertEqual(left.paw_radii, right.paw_radii)
                    assert left.paw_center is not None and right.paw_center is not None
                    self.assertAlmostEqual(left.paw_center[0], -right.paw_center[0])
                    self.assertEqual(left.paw_center[1:], right.paw_center[1:])
                else:
                    assert left.foot_chain is not None and right.foot_chain is not None
                    self.assertEqual(left.foot_chain.metatarsal_profile, right.foot_chain.metatarsal_profile)
                    self.assertEqual(left.foot_chain.pad_radii, right.foot_chain.pad_radii)
                    self.assertEqual(left.foot_chain.toe_radii, right.foot_chain.toe_radii)
            else:
                left = next(item for item in guide.limb_guides if item.source_key == left_key)
                right = next(item for item in guide.limb_guides if item.source_key == right_key)
                self.assertEqual(left.profile_controls, right.profile_controls)
                for left_section, right_section in zip(left.sections, right.sections):
                    self.assertEqual(left_section.name, right_section.name)
                    self.assertEqual(left_section.thickness, right_section.thickness)
                    for left_point, right_point in zip(left_section.centerline, right_section.centerline):
                        self.assertAlmostEqual(left_point[0], -right_point[0])
                        self.assertEqual(left_point[1:], right_point[1:])
                if left_key[3] == "upper_arm":
                    self.assertEqual(left.shoulder_radii, right.shoulder_radii)
                    self.assertAlmostEqual(left.shoulder_center[0], -right.shoulder_center[0])  # type: ignore[index]
                if left_key[3] == "thigh":
                    self.assertEqual(left.hip_radii, right.hip_radii)
                    self.assertAlmostEqual(left.hip_center[0], -right.hip_center[0])  # type: ignore[index]

    def test_private_shoulder_frame_is_bilateral_source_owned_and_input_derived(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        topology_signatures = []
        dimensions = []
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            frame = guide.shoulder_frame
            baseline_fields = surface_preview._compile_hybrid_guide(guide)
            changed_central = (frame.central_profile[0] * 1.17, frame.central_profile[1])
            changed_sides = tuple(
                dataclasses.replace(
                    side,
                    anterior_support=dataclasses.replace(
                        side.anterior_support,
                        profile=(changed_central[0], *side.anterior_support.profile[1:]),
                    ),
                )
                for side in frame.sides
            )
            changed_frame = dataclasses.replace(frame, central_profile=changed_central, sides=changed_sides)
            changed_fields = surface_preview._compile_hybrid_guide(dataclasses.replace(guide, shoulder_frame=changed_frame))

            self.assertEqual(
                tuple((item.owner.key, item.recipe) for item in baseline_fields),
                tuple((item.owner.key, item.recipe) for item in changed_fields),
            )
            self.assertNotIn("shoulder-left-anterior-support-0", {item.recipe for item in baseline_fields})
            self.assertNotIn("shoulder-left-anterior-support-0", {item.recipe for item in changed_fields})
            self.assertIs(frame.torso_owner, next(item for item in descriptors if item.key[3] == "torso"))
            self.assertIs(frame.neck_owner, next(item for item in descriptors if item.key[3] == "neck"))
            self.assertEqual(tuple(item.side for item in frame.sides), ("left", "right"))
            self.assertEqual(frame.source_keys[0], frame.torso_owner.key)
            self.assertEqual(frame.source_keys[1], frame.neck_owner.key)
            self.assertEqual(frame.source_keys[2:], tuple(item.owner.key for item in frame.sides))
            self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in frame.central_profile))
            for side in frame.sides:
                limb = next(item for item in guide.limb_guides if item.owner is side.owner)
                self.assertIs(side.owner, next(item for item in descriptors if item.key == side.owner.key))
                self.assertEqual(side.socket_anchor, limb.sections[0].centerline[0])
                self.assertEqual(side.shoulder_extremum, side.authored_peak_anchor)
                self.assertEqual(side.shoulder_extremum, side.peak_anchor)
                self.assertGreater(side.vertical_radius, 0.0)
                self.assertGreater(side.depth_radius, 0.0)
                self.assertGreater(side.span, 0.0)
                self.assertTrue(np.isfinite(side.slope))
                self.assertEqual(side.anterior_support.owner, frame.torso_owner)
                self.assertEqual(side.posterior_return.owner, frame.torso_owner)
                self.assertEqual(side.deltoid_sweep.owner, side.owner)
                for curve in (side.anterior_support, side.posterior_return):
                    self.assertEqual(len(curve.points), 4)
                    self.assertEqual(len(curve.points), len(curve.profile))
                    self.assertEqual(curve.points[0], frame.central_anchor)
                    self.assertEqual(curve.points[2], side.shoulder_extremum)
                    self.assertEqual(curve.points[3], side.socket_anchor)
                self.assertGreater(side.anterior_support.points[1][2], side.shoulder_extremum[2])
                self.assertLess(side.posterior_return.points[1][2], side.shoulder_extremum[2])
                self.assertEqual(len(side.deltoid_sweep.points), 3)
                self.assertEqual(side.deltoid_sweep.points[:2], (side.shoulder_extremum, side.socket_anchor))
                first = limb.sections[0]
                first_quarter = np.asarray(first.centerline[0]) + 0.25 * (np.asarray(first.centerline[1]) - np.asarray(first.centerline[0]))
                np.testing.assert_allclose(side.deltoid_sweep.points[2], first_quarter, rtol=0.0, atol=1.0e-12)
            left, right = frame.sides
            self.assertAlmostEqual(left.shoulder_extremum[0], -right.shoulder_extremum[0])
            self.assertEqual(left.shoulder_extremum[1:], right.shoulder_extremum[1:])
            self.assertAlmostEqual(left.socket_anchor[0], -right.socket_anchor[0])
            self.assertEqual(left.socket_anchor[1:], right.socket_anchor[1:])
            self.assertAlmostEqual(left.span, right.span)
            self.assertAlmostEqual(left.slope, right.slope)
            topology_signatures.append(
                tuple((item.side, item.owner.key, tuple(curve.name for curve in (item.anterior_support, item.posterior_return, item.deltoid_sweep))) for item in frame.sides)
            )
            dimensions.append(
                (frame.central_profile, tuple(item.span for item in frame.sides), tuple(item.anterior_support.profile[1] for item in frame.sides))
            )
        self.assertEqual(topology_signatures, [topology_signatures[0]] * 4)
        self.assertGreater(len(set(dimensions)), 1)

    def test_private_shoulder_frame_rejects_malformed_axes_owners_order_and_connections(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        frame = guide.shoulder_frame
        malformed_axes = dataclasses.replace(frame.axes, forward=(0.0, 1.0, 0.0))
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(dataclasses.replace(guide, shoulder_frame=dataclasses.replace(frame, axes=malformed_axes)))
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(dataclasses.replace(guide, shoulder_frame=dataclasses.replace(frame, sides=(frame.right, frame.left))))
        torso = next(item for item in form.variants[0][1] if item.key[3] == "torso")
        bad_owner = dataclasses.replace(frame.left, owner=torso)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(dataclasses.replace(guide, shoulder_frame=dataclasses.replace(frame, sides=(bad_owner, frame.right))))
        bad_points = frame.left.anterior_support.points[:2] + (frame.left.anterior_support.points[1],) + frame.left.anterior_support.points[3:]
        bad_curve = dataclasses.replace(frame.left.anterior_support, points=bad_points)
        bad_side = dataclasses.replace(frame.left, anterior_support=bad_curve)
        bad_guide = dataclasses.replace(guide, shoulder_frame=dataclasses.replace(frame, sides=(bad_side, frame.right)))
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(bad_guide)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._compile_hybrid_guide(bad_guide)

    def test_shoulder_frame_compiles_exact_ordered_source_owned_spans_for_all_variants(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        expected_support_recipes: list[str] = []
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            fields = surface_preview._compile_hybrid_guide(guide)
            frame = guide.shoulder_frame
            torso_supports = [
                item for item in fields
                if item.owner is frame.torso_owner and item.recipe.startswith("shoulder-")
            ]
            self.assertEqual([item.recipe for item in torso_supports], expected_support_recipes)
            self.assertTrue(all(item.owner is frame.torso_owner for item in torso_supports))
            for side in frame.sides:
                deltoids = [item for item in fields if item.owner is side.owner and item.recipe.startswith("deltoid-sweep-")]
                self.assertEqual([item.recipe for item in deltoids], ["deltoid-sweep-1"])
                field = deltoids[0]
                np.testing.assert_allclose(field.shape["from"], side.deltoid_sweep.points[1], rtol=0.0, atol=0.0)
                np.testing.assert_allclose(field.shape["to"], side.deltoid_sweep.points[2], rtol=0.0, atol=0.0)
                self.assertEqual(float(field.shape["r0"]), side.deltoid_sweep.profile[1])
                self.assertEqual(float(field.shape["r1"]), side.deltoid_sweep.profile[2])
            compiled_shoulder_fields = torso_supports + [
                item for item in fields
                if item.recipe == "deltoid-sweep-1" or (item.recipe == "root-bridge" and item.owner.key[3] == "upper_arm")
            ]
            geometry_signatures = [
                (
                    tuple(float(value) for value in item.shape["from"]),
                    tuple(float(value) for value in item.shape["to"]),
                    float(item.shape["r0"]),
                    float(item.shape["r1"]),
                )
                for item in compiled_shoulder_fields
            ]
            self.assertEqual(len(geometry_signatures), len(set(geometry_signatures)))
            self.assertEqual(len(fields), 52)
            self.assertNotIn("shoulder-mass", {item.recipe for item in fields})

    def test_limb_stations_are_endpoint_owned_and_feet_are_structured(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        guide = surface_preview._derive_hybrid_guides(form, descriptors)
        fields = surface_preview._compile_hybrid_guide(guide)
        by_role = {(item.key[1], item.key[3]): item for item in descriptors}
        expected_joints = {"upper_arm": "elbow", "thigh": "knee", "shin": "hock"}
        for limb in guide.limb_guides:
            role = limb.owner.key[3]
            self.assertEqual(len(limb.sections), 2)
            self.assertNotIn("limb-segment", [item.recipe for item in fields])
            if role == "forearm":
                self.assertIsNone(limb.joint)
                continue
            assert limb.joint is not None
            self.assertEqual(limb.joint.name, expected_joints[role])
            self.assertEqual(limb.joint.center, limb.sections[-1].centerline[1])
            np.testing.assert_allclose(limb.joint.center, surface_preview._source_shape(limb.owner, form.reference_scale)["to"])
            if role == "upper_arm":
                arm_side = next(side for side in guide.arm_profile.sides if side.side == limb.owner.key[1][0])
                self.assertEqual(limb.joint.radii, arm_side.sections[2].radii)
            elif role in {"thigh", "shin"}:
                leg_side = next(side for side in guide.leg_profile.sides if side.side == limb.owner.key[1][0])
                station_index = 2 if role == "thigh" else 4
                self.assertEqual(limb.joint.radii, leg_side.sections[station_index].radii)
            else:
                self.assertAlmostEqual(limb.joint.radii[0], 0.70 * min(limb.joint.adjacent_profiles), places=12)
                self.assertTrue(all(limb.joint.radii[0] < value for value in limb.joint.adjacent_profiles))
            adjacent_role = {"upper_arm": "forearm", "thigh": "shin", "shin": "foot"}[role]
            self.assertIn((limb.owner.key[1], adjacent_role), by_role)
            if adjacent_role in {"forearm", "shin"}:
                neighbor = next(item for item in guide.limb_guides if item.owner.key[1:] == (limb.owner.key[1], "part", adjacent_role))
                self.assertEqual(limb.joint.adjacent_profiles[0], limb.sections[-1].thickness[1])
                self.assertEqual(limb.joint.adjacent_profiles[1], neighbor.sections[0].thickness[0])
            self.assertEqual(
                [item.recipe for item in fields if item.owner is limb.owner and item.recipe in {"elbow", "knee", "hock"}],
                [expected_joints[role]],
            )
        for paw in guide.paw_guides:
            if paw.owner.key[3] == "foot":
                assert paw.foot_chain is not None
                chain = paw.foot_chain
                self.assertGreater(chain.metatarsal_centerline[1][2], chain.hock_anchor[2])
                self.assertLess(chain.metatarsal_centerline[1][1], chain.hock_anchor[1])
                self.assertGreater(chain.pad_center[2], chain.hock_anchor[2])
                self.assertGreater(chain.toe_center[2], chain.pad_center[2])
                self.assertGreater(chain.metatarsal_profile[0], chain.metatarsal_profile[1])
                metatarsal = next(item for item in fields if item.owner is paw.owner and item.recipe == "metatarsal")
                pad = next(item for item in fields if item.owner is paw.owner and item.recipe == "paw-pad")
                toe = next(item for item in fields if item.owner is paw.owner and item.recipe == "toe-box")
                shin = by_role[(paw.owner.key[1], "shin")]
                self.assertEqual(tuple(metatarsal.shape["from"]), tuple(surface_preview._source_shape(shin, form.reference_scale)["to"]))
                self.assertEqual(tuple(metatarsal.shape["from"]), chain.hock_anchor)
                self.assertEqual(tuple(metatarsal.shape["to"]), chain.pad_center)
                self.assertEqual(tuple(pad.shape["center"]), chain.pad_center)
                self.assertEqual(tuple(toe.shape["center"]), chain.toe_center)
                self.assertEqual([item.recipe for item in fields if item.owner is paw.owner], ["metatarsal", "paw-pad", "toe-box"])
            else:
                self.assertEqual([item.recipe for item in fields if item.owner is paw.owner], ["paw", "extremity-bridge"])

    def test_authored_foot_profile_is_bilateral_exact_and_contact_grounded(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        signatures = []
        self.assertFalse(hasattr(surface_preview, "_derive_foot_chain_profile"))
        for variant_index, (variant_id, descriptors, _) in enumerate(form.variants):
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            fields = surface_preview._compile_hybrid_guide(guide)
            projected_profile = form.variant_foot_profiles[variant_index]
            feet = tuple(item for item in guide.paw_guides if item.owner.key[3] == "foot")
            self.assertEqual(len(feet), 2)
            for foot in feet:
                self.assertIsNotNone(foot.foot_chain)
                chain = foot.foot_chain
                assert chain is not None
                shin = next(item for item in guide.limb_guides if item.owner.key == foot.owner.parent)
                assert shin.joint is not None
                side_index = 0 if foot.owner.key[1] == ("left",) else 1
                authored_side = form.authored_foot_profile.sides[side_index]
                projected_side = projected_profile.sides[side_index]
                guide_side = guide.foot_profile.sides[side_index]
                self.assertEqual(chain.profile, guide.foot_profile)
                self.assertEqual(guide_side.hock_binding, ("authored_leg_profile", side_index, surface_preview.FOOT_PROFILE_HOCK_SECTION_INDEX))
                self.assertEqual(tuple(float(value) for value in foot.owner.point), shin.joint.center)
                for authored, projected, station in zip(authored_side.sections, projected_side.sections, guide_side.sections):
                    expected_center = tuple(float(foot.owner.point[axis] + projected.position[axis] / form.reference_scale) for axis in range(3))
                    self.assertEqual(station.center, expected_center)
                    self.assertEqual(station.center, chain.pad_center if authored.name == "pad" else chain.toe_center)
                    self.assertEqual(station.radii, tuple(value / 1000.0 for value in (projected.lateral_radius_permille, projected.up_radius_permille, projected.forward_radius_permille)))
                    self.assertEqual(station.radii, chain.pad_radii if authored.name == "pad" else chain.toe_radii)
                    self.assertEqual(station.profile_provenance, form.authored_foot_profile.provenance)
                    self.assertEqual(station.variant_provenance, projected.provenance)
                    for lineage, control, factor, scaled in zip(
                        (station.lateral_lineage, station.up_lineage, station.forward_lineage),
                        (authored.lateral, authored.up, authored.forward),
                        surface_preview._foot_profile_factors(variant_id),
                        (projected.lateral_radius_permille, projected.up_radius_permille, projected.forward_radius_permille),
                    ):
                        self.assertEqual(lineage.base, control.value_permille)
                        self.assertEqual(lineage.factor, factor)
                        self.assertEqual(lineage.scaled, scaled)
                        self.assertEqual(lineage.reference, (foot.owner.key, control.role))
                        self.assertEqual(lineage.reference_index, control.source_index)
                        self.assertEqual(lineage.provenance, control.provenance)
                        self.assertEqual(lineage.consumed_section, authored.name)
                expected_metatarsal_profile = surface_preview._derive_foot_metatarsal_profile(
                    chain.hock_radii,
                    chain.pad_radii,
                    "test.foot_chain",
                )
                self.assertEqual(chain.metatarsal_profile, expected_metatarsal_profile)
                self.assertEqual(shin.joint.adjacent_profiles[1], expected_metatarsal_profile[0])
                self.assertEqual(chain.hock_anchor, shin.joint.center)
                self.assertEqual(chain.hock_radii, shin.joint.radii)
                self.assertEqual(chain.metatarsal_centerline[0], chain.hock_anchor)
                self.assertGreater(chain.metatarsal_centerline[1][2], chain.hock_anchor[2])
                self.assertLess(chain.metatarsal_centerline[1][1], chain.hock_anchor[1])
                self.assertGreater(chain.pad_center[2], chain.hock_anchor[2])
                self.assertGreater(chain.toe_center[2], chain.pad_center[2])
                self.assertGreater(chain.metatarsal_profile[0], chain.metatarsal_profile[1])
                self.assertTrue(all(value > 0.0 for value in chain.metatarsal_profile))
                hock_field = next(item for item in fields if item.owner is shin.owner and item.recipe == "hock")
                metatarsal_field = next(item for item in fields if item.owner is foot.owner and item.recipe == "metatarsal")
                np.testing.assert_array_equal(hock_field.shape["center"], chain.hock_anchor)
                np.testing.assert_array_equal(hock_field.shape["radii"], chain.hock_radii)
                self.assertEqual(float(shin.joint.adjacent_profiles[1]), float(metatarsal_field.shape["r0"]))
                self.assertEqual(float(chain.metatarsal_profile[0]), float(metatarsal_field.shape["r0"]))
                shared_anchor = np.asarray([chain.hock_anchor])
                self.assertLess(float(surface_preview._field(shared_anchor, hock_field)[0]), 0.0)
                self.assertLess(float(surface_preview._field(shared_anchor, metatarsal_field)[0]), 0.0)
                self.assertAlmostEqual(chain.contact_height, float(chain.pad_center[1] - chain.pad_radii[1]), places=12)
                self.assertAlmostEqual(chain.pad_center[1] - chain.pad_radii[1], chain.contact_height, places=12)
                self.assertAlmostEqual(chain.toe_center[1] - chain.toe_radii[1], chain.contact_height, places=12)
                signatures.append((chain.metatarsal_centerline, chain.metatarsal_profile, chain.pad_center, chain.toe_center))

            left, right = feet
            left_chain = left.foot_chain
            right_chain = right.foot_chain
            assert left_chain is not None and right_chain is not None
            self.assertEqual(left_chain.metatarsal_profile, right_chain.metatarsal_profile)
            self.assertEqual(left_chain.pad_radii, right_chain.pad_radii)
            self.assertEqual(left_chain.toe_radii, right_chain.toe_radii)
            for left_point, right_point in zip(left_chain.metatarsal_centerline, right_chain.metatarsal_centerline):
                self.assertAlmostEqual(left_point[0], -right_point[0])
                self.assertEqual(left_point[1:], right_point[1:])
            self.assertAlmostEqual(left_chain.pad_center[0], -right_chain.pad_center[0])
            self.assertEqual(left_chain.pad_center[1:], right_chain.pad_center[1:])
            self.assertAlmostEqual(left_chain.toe_center[0], -right_chain.toe_center[0])
            self.assertEqual(left_chain.toe_center[1:], right_chain.toe_center[1:])

        self.assertEqual(len(signatures), 8)
        first_descriptors = form.variants[0][1]
        first_a = surface_preview._derive_hybrid_guides(form, first_descriptors)
        first_b = surface_preview._derive_hybrid_guides(form, first_descriptors)
        self.assertEqual(
            [item.foot_chain for item in first_a.paw_guides],
            [item.foot_chain for item in first_b.paw_guides],
        )

    def test_legacy_foot_shape_does_not_drive_authored_profile_or_compiled_chain(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())

        def profile_signature(guide: object) -> tuple[object, ...]:
            profile = guide.foot_profile  # type: ignore[attr-defined]
            return tuple(
                (
                    side.side,
                    side.hock_binding,
                    tuple(
                        (
                            station.name,
                            station.section_index,
                            station.source_section_index,
                            station.frame_index,
                            station.landmark_index,
                            station.owner.key,
                            station.frame,
                            station.landmark,
                            station.center,
                            station.radii,
                            station.lateral_lineage,
                            station.up_lineage,
                            station.forward_lineage,
                            station.profile_provenance,
                            station.variant_provenance,
                        )
                        for station in side.sections
                    ),
                )
                for side in profile.sides
            )

        def chain_signature(guide: object) -> tuple[object, ...]:
            return tuple(
                (
                    paw.owner.key,
                    tuple(
                        (field.name, getattr(paw.foot_chain, field.name))
                        for field in dataclasses.fields(paw.foot_chain)
                        if field.name != "profile"
                    ),
                )
                for paw in guide.paw_guides  # type: ignore[attr-defined]
                if paw.foot_chain is not None
            )

        def field_signature(fields: tuple[surface_preview.Field, ...]) -> tuple[object, ...]:
            return tuple(
                (
                    field.owner.key,
                    field.recipe,
                    json.dumps(
                        field.shape,
                        sort_keys=True,
                        default=lambda value: value.tolist() if isinstance(value, np.ndarray) else value,
                    ),
                )
                for field in fields
                if field.owner.key[3] == "foot"
            )

        for _, descriptors, _ in form.variants:
            foot_descriptors = {item.key: item for item in descriptors if item.key[3] == "foot"}
            baseline_guide = surface_preview._derive_hybrid_guides(form, descriptors)
            baseline_fields = surface_preview._compile_hybrid_guide(baseline_guide)
            baseline_profile = profile_signature(baseline_guide)
            baseline_chain = chain_signature(baseline_guide)
            baseline_foot_fields = field_signature(baseline_fields)
            legacy_foot = foot_descriptors[sorted(foot_descriptors)[0]]
            original_extents = list(legacy_foot.shape["axis_extents_permille"])
            legacy_foot.shape["axis_extents_permille"] = [value + 137 for value in original_extents]
            try:
                changed_guide = surface_preview._derive_hybrid_guides(form, descriptors)
                changed_fields = surface_preview._compile_hybrid_guide(changed_guide)
            finally:
                legacy_foot.shape["axis_extents_permille"] = original_extents

            self.assertEqual(profile_signature(changed_guide), baseline_profile)
            self.assertEqual(chain_signature(changed_guide), baseline_chain)
            self.assertEqual(field_signature(changed_fields), baseline_foot_fields)
            changed_foot_paws = [paw for paw in changed_guide.paw_guides if paw.owner.key[3] == "foot"]
            self.assertEqual(len(changed_foot_paws), len(foot_descriptors))
            for station_side in changed_guide.foot_profile.sides:
                for station in station_side.sections:
                    expected_owner = foot_descriptors[(legacy_foot.key[0], (station_side.side,), "part", "foot")]
                    self.assertIs(station.owner, expected_owner)
            for paw in changed_foot_paws:
                self.assertIs(paw.owner, foot_descriptors[paw.owner.key])
            for field in changed_fields:
                if field.owner.key[3] == "foot":
                    self.assertIs(field.owner, foot_descriptors[field.owner.key])

    def test_authored_foot_profile_perturbation_is_local_to_one_pad_and_side(self) -> None:
        baseline_form = surface_preview.validate_envelope(make_payload())
        baseline_guide = surface_preview._derive_hybrid_guides(baseline_form, baseline_form.variants[0][1])
        baseline_fields = surface_preview._compile_hybrid_guide(baseline_guide)
        payload = make_payload()
        role = surface_preview.FOOT_PROFILE_DIMENSION_PREFIX + "pad_forward_radius"
        dimension = next(
            item
            for item in payload["authored_dimensions"]
            if item["owner"]["anchors"] == ["left"]
            and item["owner"]["role"] == "foot"
            and item["role"] == role
        )
        dimension["value_permille"] += 17
        for variant in payload["variants"]:
            factor = surface_preview._foot_profile_factors(variant["id"])[2]
            section = next(item for item in variant["foot_profile"]["sides"][0]["sections"] if item["name"] == "pad")
            section["forward_radius_permille"] = dimension["value_permille"] * factor // 1_000
        changed_form = surface_preview.validate_envelope(payload)
        changed_guide = surface_preview._derive_hybrid_guides(changed_form, changed_form.variants[0][1])
        changed_fields = surface_preview._compile_hybrid_guide(changed_guide)
        baseline_sides = {side.side: side for side in baseline_guide.foot_profile.sides}
        changed_sides = {side.side: side for side in changed_guide.foot_profile.sides}
        for side_name in ("left", "right"):
            for index, name in enumerate(surface_preview.FOOT_PROFILE_SECTION_NAMES):
                before = baseline_sides[side_name].sections[index]
                after = changed_sides[side_name].sections[index]
                if side_name == "left" and name == "pad":
                    self.assertEqual(before.radii[:2], after.radii[:2])
                    self.assertNotEqual(before.radii[2], after.radii[2])
                else:
                    self.assertEqual(before.radii, after.radii)
                self.assertEqual(before.center, after.center)
        def field_map(fields: tuple[surface_preview.Field, ...]) -> dict[tuple[object, str], surface_preview.Field]:
            return {(item.owner.key, item.recipe): item for item in fields if item.owner.key[3] == "foot"}
        before = field_map(baseline_fields)
        after = field_map(changed_fields)
        self.assertNotEqual(before[(('main', ('left',), 'part', 'foot'), "paw-pad")].shape["radii"].tolist(), after[(('main', ('left',), 'part', 'foot'), "paw-pad")].shape["radii"].tolist())
        def shape_signature(field: surface_preview.Field) -> str:
            return json.dumps(
                field.shape,
                sort_keys=True,
                default=lambda value: value.tolist() if isinstance(value, np.ndarray) else value,
            )
        for key in (
            (('main', ('right',), 'part', 'foot'), "paw-pad"),
            (('main', ('left',), 'part', 'foot'), "toe-box"),
            (('main', ('left',), 'part', 'foot'), "metatarsal"),
        ):
            self.assertEqual(shape_signature(before[key]), shape_signature(after[key]))
        for field in after.values():
            self.assertIs(field.owner, next(item for item in changed_form.variants[0][1] if item.key == field.owner.key))

    def test_digitigrade_foot_chain_rejects_bad_hock_contact_and_taper(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        foot = next(item for item in guide.paw_guides if item.owner.key[3] == "foot")
        chain = foot.foot_chain
        assert chain is not None

        malformed_cases = (
            dataclasses.replace(chain, hock_anchor=(chain.hock_anchor[0], chain.hock_anchor[1] + 0.1, chain.hock_anchor[2])),
            dataclasses.replace(chain, toe_center=(chain.toe_center[0], chain.toe_center[1] + 0.1, chain.toe_center[2])),
            dataclasses.replace(chain, toe_center=(chain.toe_center[0], chain.toe_center[1], chain.pad_center[2] + chain.pad_radii[2] + chain.toe_radii[2] + 0.01)),
            dataclasses.replace(chain, metatarsal_profile=(chain.metatarsal_profile[1], chain.metatarsal_profile[0])),
        )
        for malformed_chain in malformed_cases:
            malformed_paw = dataclasses.replace(foot, foot_chain=malformed_chain)
            malformed_paws = tuple(malformed_paw if item is foot else item for item in guide.paw_guides)
            with self.assertRaises(surface_preview.PreviewError):
                surface_preview._compile_hybrid_guide(dataclasses.replace(guide, paw_guides=malformed_paws))

    def test_private_guides_reject_malformed_profile_and_consume_piecewise_sections(self) -> None:
        import dataclasses

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        baseline = surface_preview._compile_hybrid_guide(guide)
        for limb in guide.limb_guides:
            if limb.owner.key[3] in {"upper_arm", "forearm", "thigh", "shin"}:
                continue
            baseline_field = next(item for item in baseline if item.owner is limb.owner and item.recipe.endswith("-pre-joint") or item.owner is limb.owner and item.recipe.endswith("-proximal"))
            first_section = limb.sections[0]
            changed_section = dataclasses.replace(first_section, thickness=(first_section.thickness[0] * 0.60, first_section.thickness[1] * 0.45))
            changed_limb = dataclasses.replace(limb, sections=(changed_section, limb.sections[1]))
            changed_guides = tuple(changed_limb if item is limb else item for item in guide.limb_guides)
            changed_frame = guide.shoulder_frame
            if limb.owner.key[3] == "upper_arm":
                changed_sides = []
                for side in changed_frame.sides:
                    if side.owner is not limb.owner:
                        changed_sides.append(side)
                        continue
                    anterior = dataclasses.replace(side.anterior_support, profile=(*side.anterior_support.profile[:-1], changed_section.thickness[0]))
                    posterior = dataclasses.replace(side.posterior_return, profile=(*side.posterior_return.profile[:-1], changed_section.thickness[0]))
                    deltoid = dataclasses.replace(side.deltoid_sweep, profile=(side.deltoid_sweep.profile[0], *changed_section.thickness))
                    changed_sides.append(dataclasses.replace(side, anterior_support=anterior, posterior_return=posterior, deltoid_sweep=deltoid))
                changed_frame = dataclasses.replace(changed_frame, sides=tuple(changed_sides))
            changed = surface_preview._compile_hybrid_guide(
                dataclasses.replace(guide, limb_guides=changed_guides, shoulder_frame=changed_frame)
            )
            changed_field = next(
                item for item in changed
                if item.owner is limb.owner and item.recipe.endswith("-pre-joint") or item.owner is limb.owner and item.recipe.endswith("-proximal")
            )
            self.assertLess(float(changed_field.shape["r0"]), float(baseline_field.shape["r0"]))
            self.assertLess(float(changed_field.shape["r1"]), float(baseline_field.shape["r1"]))
        for limb in guide.limb_guides:
            malformed_section = dataclasses.replace(limb.sections[0], thickness=(0.0, limb.sections[0].thickness[1]))
            malformed = dataclasses.replace(limb, sections=(malformed_section, limb.sections[1]))
            malformed_guides = tuple(malformed if item is limb else item for item in guide.limb_guides)
            with self.assertRaises(surface_preview.PreviewError):
                surface_preview._compile_hybrid_guide(
                    dataclasses.replace(guide, limb_guides=malformed_guides)
                )
        for limb in guide.limb_guides:
            malformed_section = dataclasses.replace(limb.sections[1], thickness=(limb.sections[1].thickness[0], 0.0))
            malformed = dataclasses.replace(limb, sections=(limb.sections[0], malformed_section))
            malformed_guides = tuple(malformed if item is limb else item for item in guide.limb_guides)
            with self.assertRaises(surface_preview.PreviewError):
                surface_preview._compile_hybrid_guide(
                    dataclasses.replace(guide, limb_guides=malformed_guides)
                )

    def test_private_torso_cage_has_shared_ordered_source_owned_sections(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        expected_names = (
            "lower-pelvis",
            "upper-pelvis",
            "lower-abdomen",
            "waist-abdomen",
            "upper-abdomen",
            "lower-ribcage",
            "upper-ribcage-shoulder",
        )
        topologies = []
        dimensions = []
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            cage = guide.torso_cage
            self.assertIsInstance(cage, surface_preview._TorsoCage)
            self.assertEqual(tuple(section.name for section in cage.sections), expected_names)
            self.assertEqual(cage.source_keys, (cage.pelvis_owner.key, cage.torso_owner.key))
            self.assertEqual(cage.pelvis_owner.key[3], "pelvis")
            self.assertEqual(cage.torso_owner.key[3], "torso")
            self.assertTrue(all(any(owner is descriptor for descriptor in descriptors) for owner in cage.source_owners))
            self.assertTrue(all(any(section.owner is owner for owner in cage.source_owners) for section in cage.sections))
            self.assertEqual(
                tuple(section.owner.key[3] for section in cage.sections),
                ("pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso"),
            )
            self.assertTrue(
                all(
                    np.isfinite(value)
                    for section in cage.sections
                    for value in section.center
                )
            )
            self.assertTrue(
                all(
                    np.isfinite(value) and value > 0.0
                    for section in cage.sections
                    for value in (
                        section.lateral_radius,
                        section.anterior_radius,
                        section.posterior_radius,
                        section.depth_radius,
                    )
                )
            )
            self.assertTrue(
                all(
                    cage.sections[index].center[1] < cage.sections[index + 1].center[1]
                    for index in range(len(cage.sections) - 1)
                )
            )
            lateral = np.asarray([section.lateral_radius for section in cage.sections])
            depth = np.asarray([section.depth_radius for section in cage.sections])
            self.assertEqual(
                tuple(section.lateral_lineage.base for section in cage.sections),
                (1500, 1350, 1050, 900, 1125, 1400, 1500),
            )
            self.assertEqual(
                tuple(section.anterior_lineage.base for section in cage.sections),
                (850, 780, 620, 520, 650, 850, 900),
            )
            self.assertEqual(
                tuple(section.posterior_lineage.base for section in cage.sections),
                (600, 560, 500, 420, 500, 650, 700),
            )
            self.assertTrue(np.all(lateral > 0.0))
            self.assertTrue(np.all(depth > 0.0))
            topologies.append(
                tuple((section.name, section.owner.key) for section in cage.sections)
            )
            dimensions.append(
                tuple((section.lateral_radius, section.depth_radius) for section in cage.sections)
            )
        self.assertEqual(topologies, [topologies[0]] * len(form.variants))
        self.assertGreater(len(set(dimensions)), 1)

    def test_authored_torso_profile_derives_exact_sections_and_lineage(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual(
            tuple(section.name for section in form.authored_torso_profile.sections),
            surface_preview.TORSO_PROFILE_SECTION_NAMES,
        )
        for variant_index, (variant_id, descriptors, _) in enumerate(form.variants):
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            profile = form.variant_torso_profiles[variant_index]
            by_key = {descriptor.key: descriptor for descriptor in descriptors}
            for index, (authored, projected, section) in enumerate(
                zip(form.authored_torso_profile.sections, profile.sections, guide.torso_cage.sections)
            ):
                owner = by_key[authored.owner]
                expected_center = tuple(
                    float(owner.point[axis] + projected.position[axis] / form.reference_scale)
                    for axis in range(3)
                )
                self.assertEqual(section.owner, owner)
                self.assertEqual(section.center, expected_center)
                expected_lateral, expected_depth = surface_preview._torso_profile_factors(variant_id, owner.key[3])
                self.assertEqual(section.lateral_lineage.base, authored.lateral.value_permille)
                self.assertEqual(section.lateral_lineage.factor, expected_lateral)
                self.assertEqual(section.lateral_lineage.scaled, projected.lateral_radius_permille)
                self.assertEqual(section.anterior_lineage.base, authored.anterior.value_permille)
                self.assertEqual(section.anterior_lineage.factor, expected_depth)
                self.assertEqual(section.anterior_lineage.scaled, projected.anterior_radius_permille)
                self.assertEqual(section.posterior_lineage.base, authored.posterior.value_permille)
                self.assertEqual(section.posterior_lineage.factor, expected_depth)
                self.assertEqual(section.posterior_lineage.scaled, projected.posterior_radius_permille)
                self.assertEqual(section.lateral_lineage.reference, (owner.key, authored.lateral.role))
                self.assertEqual(section.anterior_lineage.reference, (owner.key, authored.anterior.role))
                self.assertEqual(section.posterior_lineage.reference, (owner.key, authored.posterior.role))
                self.assertEqual(section.lateral_lineage.reference_index, authored.lateral.source_index)
                self.assertEqual(section.anterior_lineage.reference_index, authored.anterior.source_index)
                self.assertEqual(section.posterior_lineage.reference_index, authored.posterior.source_index)
                self.assertEqual(section.lateral_lineage.consumed_section, authored.name)
                self.assertEqual(section.anterior_lineage.consumed_section, authored.name)
                self.assertEqual(section.posterior_lineage.consumed_section, authored.name)
                self.assertAlmostEqual(
                    section.depth_radius,
                    0.5 * (section.anterior_radius + section.posterior_radius),
                )
                self.assertEqual(section.landmark.role, authored.landmark.role)
                self.assertEqual(section.frame.role, surface_preview.TORSO_PROFILE_FRAME_ROLE)

    def test_authored_torso_profile_factor_behavior_is_shared_and_asymmetric_depth_is_retained(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        for variant_index, (variant_id, descriptors, _) in enumerate(form.variants):
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            projected = form.variant_torso_profiles[variant_index]
            for authored, variant_section, guide_section in zip(
                form.authored_torso_profile.sections,
                projected.sections,
                guide.torso_cage.sections,
            ):
                lateral_factor, depth_factor = surface_preview._torso_profile_factors(variant_id, authored.owner[3])
                self.assertEqual(variant_section.lateral_factor, lateral_factor)
                self.assertEqual(variant_section.anterior_factor, depth_factor)
                self.assertEqual(variant_section.posterior_factor, depth_factor)
                self.assertEqual(guide_section.lateral_lineage.factor, lateral_factor)
                self.assertEqual(guide_section.anterior_lineage.factor, depth_factor)
                self.assertEqual(guide_section.posterior_lineage.factor, depth_factor)
                self.assertEqual(guide_section.anterior_lineage.factor, guide_section.posterior_lineage.factor)
        payload = make_payload()
        dimension = next(
            item
            for item in payload["authored_dimensions"]
            if item["role"] == surface_preview.TORSO_PROFILE_DIMENSION_PREFIX + "lower_abdomen_anterior_radius"
        )
        dimension["value_permille"] = 700
        for variant in payload["variants"]:
            section = variant["torso_profile"]["sections"][2]
            factor = section["scaling"]["anterior_factor_permille"]
            section["anterior_radius_permille"] = 700 * factor // 1_000
        form = surface_preview.validate_envelope(payload)
        neutral = surface_preview._derive_hybrid_guides(form, form.variants[0][1]).torso_cage.section("lower-abdomen")
        self.assertNotEqual(neutral.anterior_radius, neutral.posterior_radius)
        self.assertAlmostEqual(neutral.depth_radius, (neutral.anterior_radius + neutral.posterior_radius) / 2.0)

    def test_authored_torso_profile_source_perturbation_is_local(self) -> None:
        payload = make_payload()
        profile = payload["authored_torso_profile"]
        landmark_index = profile["sections"][3]["landmark_index"]
        payload["authored_landmarks"][landmark_index]["position"][1] = 0.34
        for variant in payload["variants"]:
            variant["torso_profile"]["sections"][3]["position"][1] = 0.34
        form = surface_preview.validate_envelope(payload)
        baseline = surface_preview._derive_hybrid_guides(form, form.variants[0][1]).torso_cage
        original = make_payload()
        original_form = surface_preview.validate_envelope(original)
        original_cage = surface_preview._derive_hybrid_guides(original_form, original_form.variants[0][1]).torso_cage
        for index, (before, after) in enumerate(zip(original_cage.sections, baseline.sections)):
            if index == 3:
                self.assertNotEqual(before.center, after.center)
            else:
                self.assertEqual(before.center, after.center)
                self.assertEqual(before.lateral_lineage, after.lateral_lineage)
                self.assertEqual(before.anterior_lineage, after.anterior_lineage)
                self.assertEqual(before.posterior_lineage, after.posterior_lineage)

    def test_authored_torso_profile_rejects_malformed_index_roles_and_scaling(self) -> None:
        cases: list[dict[str, object]] = []
        payload = make_payload()
        payload["authored_torso_profile"]["sections"][0]["section_index"] = 1
        cases.append(payload)
        payload = make_payload()
        payload["authored_torso_profile"]["sections"][0]["frame_index"] = 99
        cases.append(payload)
        payload = make_payload()
        payload["authored_torso_profile"]["sections"][0]["dimension_indices"]["posterior"] = payload["authored_torso_profile"]["sections"][0]["dimension_indices"]["anterior"]
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["torso_profile"]["sections"][2]["scaling"]["posterior_factor_permille"] += 1
        cases.append(payload)
        payload = make_payload()
        payload["authored_landmarks"][payload["authored_torso_profile"]["sections"][1]["landmark_index"]]["position"][0] = 0.1
        cases.append(payload)
        for malformed in cases:
            with self.subTest(malformed=malformed):
                with self.assertRaises(surface_preview.PreviewError):
                    surface_preview.validate_envelope(malformed)

    def test_authored_torso_profile_rejects_nonmonotone_route_at_envelope_admission(self) -> None:
        payload = make_payload()
        previous = next(
            item
            for item in payload["authored_landmarks"]
            if item["role"] == surface_preview.TORSO_PROFILE_LANDMARK_PREFIX + "waist_abdomen"
        )
        current = next(
            item
            for item in payload["authored_landmarks"]
            if item["role"] == surface_preview.TORSO_PROFILE_LANDMARK_PREFIX + "upper_abdomen"
        )
        current["position"][1] = previous["position"][1]
        with self.assertRaisesRegex(surface_preview.PreviewError, "strictly increasing"):
            surface_preview.validate_envelope(payload)

    def test_authored_head_neck_profile_projects_all_variants_with_exact_lineage(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual(
            tuple(section.name for section in form.authored_head_neck_profile.sections),
            surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES,
        )
        self.assertEqual(
            form.authored_head_neck_profile.connections,
            tuple(surface_preview.HeadNeckConnection(*value) for value in surface_preview.HEAD_NECK_PROFILE_CONNECTIONS),
        )
        for variant_index, (variant_id, descriptors, _) in enumerate(form.variants):
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            projected = form.variant_head_neck_profiles[variant_index]
            by_key = {descriptor.key: descriptor for descriptor in descriptors}
            for authored, variant_section, guide_section in zip(
                form.authored_head_neck_profile.sections,
                projected.sections,
                guide.head_guide.profile.sections,
            ):
                owner = by_key[authored.owner]
                self.assertIs(guide_section.owner, owner)
                self.assertEqual(guide_section.section_index, authored.section_index)
                self.assertEqual(guide_section.source_section_index, variant_section.source_section_index)
                self.assertEqual(
                    guide_section.center,
                    tuple(owner.point[axis] + variant_section.position[axis] / form.reference_scale for axis in range(3)),
                )
                factors = surface_preview._head_neck_profile_factors(variant_id, owner.key[3])
                for lineage, control, factor, projected_radius in zip(
                    (guide_section.lateral_lineage, guide_section.up_lineage, guide_section.forward_lineage),
                    (authored.lateral, authored.up, authored.forward),
                    factors,
                    (variant_section.lateral_radius_permille, variant_section.up_radius_permille, variant_section.forward_radius_permille),
                ):
                    self.assertEqual(lineage.base, control.value_permille)
                    self.assertEqual(lineage.factor, factor)
                    self.assertEqual(lineage.scaled, projected_radius)
                    self.assertEqual(lineage.reference, (owner.key, control.role))
                    self.assertEqual(lineage.reference_index, control.source_index)
                    self.assertEqual(lineage.provenance, control.provenance)
                self.assertTrue(all(value > 0.0 for value in guide_section.radii))

    def test_authored_head_neck_profile_rejects_malformed_index_edge_provenance_and_scaling(self) -> None:
        cases: list[dict[str, object]] = []
        payload = make_payload()
        payload["authored_head_neck_profile"]["sections"][0]["section_index"] = 1
        cases.append(payload)
        payload = make_payload()
        payload["authored_head_neck_profile"]["sections"][0]["frame_index"] = 99
        cases.append(payload)
        payload = make_payload()
        payload["authored_head_neck_profile"]["sections"][0]["dimension_indices"]["up"] = payload["authored_head_neck_profile"]["sections"][0]["dimension_indices"]["lateral"]
        cases.append(payload)
        payload = make_payload()
        payload["authored_head_neck_profile"]["connections"][1]["to_section_index"] = 7
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["head_neck_profile"]["connections"][0]["route"] = "wrong-route"
        cases.append(payload)
        payload = make_payload()
        payload["authored_head_neck_profile"]["provenance"]["document"] = "other-document"
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["head_neck_profile"]["provenance"]["namespace"] = "other"
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["head_neck_profile"]["sections"][3]["scaling"]["forward_factor_permille"] += 1
        cases.append(payload)
        payload = make_payload()
        payload["variants"][0]["head_neck_profile"]["sections"][6]["forward_radius_permille"] += 1
        cases.append(payload)
        for malformed in cases:
            with self.subTest(malformed=malformed):
                with self.assertRaises(surface_preview.PreviewError):
                    surface_preview.validate_envelope(malformed)

    def test_authored_head_neck_profile_rejects_nonmonotone_source_neck_cranium_and_muzzle_routes(self) -> None:
        route_cases = (
            ("neck-upper", "neck-collar", 1),
            ("cranium-crown", "cranium-mid", 1),
            ("muzzle-tip", "muzzle-mid", 2),
        )
        for current_name, previous_name, axis in route_cases:
            payload = make_payload()
            current = next(
                item
                for item in payload["authored_landmarks"]
                if item["role"] == surface_preview.HEAD_NECK_PROFILE_LANDMARK_PREFIX + current_name.replace("-", "_")
            )
            previous = next(
                item
                for item in payload["authored_landmarks"]
                if item["role"] == surface_preview.HEAD_NECK_PROFILE_LANDMARK_PREFIX + previous_name.replace("-", "_")
            )
            current["position"][axis] = previous["position"][axis]
            with self.subTest(route=current_name):
                with self.assertRaisesRegex(surface_preview.PreviewError, "strictly increasing"):
                    surface_preview.validate_envelope(payload)

    def test_authored_head_neck_profile_rejects_nonmonotone_variant_routes_at_variant_parser_boundary(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        route_cases = (
            ("neck-upper", "neck-collar", 1),
            ("cranium-crown", "cranium-mid", 1),
            ("muzzle-tip", "muzzle-mid", 2),
        )
        for current_name, previous_name, axis in route_cases:
            current_index = surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES.index(current_name)
            previous_index = surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES.index(previous_name)
            authored_sections = list(form.authored_head_neck_profile.sections)
            current = authored_sections[current_index]
            previous = authored_sections[previous_index]
            position = list(current.landmark.position)
            position[axis] = previous.landmark.position[axis]
            authored_sections[current_index] = dataclasses.replace(
                current,
                landmark=dataclasses.replace(current.landmark, position=tuple(position)),
            )
            malformed_authored = dataclasses.replace(
                form.authored_head_neck_profile,
                sections=tuple(authored_sections),
            )
            variant_profile = copy.deepcopy(form.raw["variants"][0]["head_neck_profile"])
            variant_profile["sections"][current_index]["position"] = position
            with self.subTest(route=current_name):
                with self.assertRaisesRegex(surface_preview.PreviewError, "strictly increasing"):
                    surface_preview._parse_variant_head_neck_profile(
                        variant_profile,
                        form.source,
                        malformed_authored,
                        surface_preview.VARIANT_IDS[0],
                    )

    def test_head_neck_guide_rejects_nonmonotone_neck_cranium_and_muzzle_routes(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        route_cases = (
            ("neck-upper", "neck-collar", 1),
            ("cranium-crown", "cranium-mid", 1),
            ("muzzle-tip", "muzzle-mid", 2),
        )
        for current_name, previous_name, axis in route_cases:
            sections = list(guide.head_guide.profile.sections)
            current_index = surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES.index(current_name)
            previous_index = surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES.index(previous_name)
            current = sections[current_index]
            previous = sections[previous_index]
            center = list(current.center)
            center[axis] = previous.center[axis]
            sections[current_index] = dataclasses.replace(current, center=tuple(center))
            profile = dataclasses.replace(guide.head_guide.profile, sections=tuple(sections))
            head = dataclasses.replace(guide.head_guide, profile=profile)
            with self.subTest(route=current_name):
                with self.assertRaisesRegex(surface_preview.PreviewError, "strictly increasing"):
                    surface_preview._validate_hybrid_guide(dataclasses.replace(guide, head_guide=head))

    def test_authored_head_neck_profile_perturbation_is_local_to_station_and_incident_paths(self) -> None:
        original_form = surface_preview.validate_envelope(make_payload())
        original = surface_preview._derive_hybrid_guides(original_form, original_form.variants[0][1])
        payload = make_payload()
        landmark = next(item for item in payload["authored_landmarks"] if item["role"] == "form_head_neck_profile_muzzle_mid")
        landmark["position"][2] = 0.60
        for variant in payload["variants"]:
            next(item for item in variant["head_neck_profile"]["sections"] if item["name"] == "muzzle-mid")["position"][2] = 0.60
        changed_form = surface_preview.validate_envelope(payload)
        changed = surface_preview._derive_hybrid_guides(changed_form, changed_form.variants[0][1])
        original_profile = {item.name: item for item in original.head_guide.profile.sections}
        changed_profile = {item.name: item for item in changed.head_guide.profile.sections}
        for name in surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES:
            if name == "muzzle-mid":
                self.assertNotEqual(original_profile[name].center, changed_profile[name].center)
            else:
                self.assertEqual(
                    surface_preview._head_neck_section_json(original_profile[name]),
                    surface_preview._head_neck_section_json(changed_profile[name]),
                )
        for before, after in zip(original.head_guide.profile.connections, changed.head_guide.profile.connections):
            incident = before.spec.from_section_index == 6 or before.spec.to_section_index == 6
            if incident:
                self.assertNotEqual(before.centerline, after.centerline)
            else:
                self.assertEqual(
                    surface_preview._head_neck_connection_json(before),
                    surface_preview._head_neck_connection_json(after),
                )
        self.assertNotEqual(original.head_guide.muzzle_center, changed.head_guide.muzzle_center)
        self.assertEqual(original.head_guide.cranium_center, changed.head_guide.cranium_center)
        self.assertEqual(original.head_guide.head_transition, changed.head_guide.head_transition)
        self.assertEqual(original.head_guide.neck_transition, changed.head_guide.neck_transition)
        self.assertEqual(original.head_guide.neck_collar_center, changed.head_guide.neck_collar_center)

    def test_authored_torso_profile_generation_is_deterministic_for_all_variants(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        first = []
        second = []
        for variant in form.variants:
            first.append(tuple(surface_preview._torso_section_json(section) for section in surface_preview._derive_hybrid_guides(form, variant[1]).torso_cage.sections))
        form_again = surface_preview.validate_envelope(make_payload())
        for variant in form_again.variants:
            second.append(tuple(surface_preview._torso_section_json(section) for section in surface_preview._derive_hybrid_guides(form_again, variant[1]).torso_cage.sections))
        self.assertEqual(first, second)

    def test_torso_cage_rejects_malformed_axes_and_owners(self) -> None:
        import dataclasses

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        malformed_axes = dataclasses.replace(
            guide.torso_cage.axes,
            lateral=(0.0, 1.0, 0.0),
        )
        malformed_cage = dataclasses.replace(guide.torso_cage, axes=malformed_axes)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(
                dataclasses.replace(guide, torso_cage=malformed_cage)
            )

        torso = next(item for item in form.variants[0][1] if item.key[3] == "torso")
        malformed_cage = dataclasses.replace(guide.torso_cage, pelvis_owner=torso)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(
                dataclasses.replace(guide, torso_cage=malformed_cage)
            )

        malformed_sections = tuple(
            dataclasses.replace(section, owner=torso)
            if index == 0
            else section
            for index, section in enumerate(guide.torso_cage.sections)
        )
        malformed_cage = dataclasses.replace(guide.torso_cage, sections=malformed_sections)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(
                dataclasses.replace(guide, torso_cage=malformed_cage)
            )

    def test_torso_cage_normalizes_disproportionate_radii_without_rejection(self) -> None:
        payload = make_payload()
        for dimension in payload["authored_dimensions"]:
            if dimension["role"] != "form_extent_y":
                continue
            owner_role = dimension["owner"]["role"]
            if owner_role == "pelvis":
                dimension["value_permille"] = 5000
            elif owner_role == "torso":
                dimension["value_permille"] = 2
        for variant in payload["variants"]:
            for item in variant["descriptors"]:
                role = item["address"]["role"]
                if role == "pelvis":
                    item["shape"]["axis_extents_permille"][1] = 5000
                elif role == "torso":
                    item["shape"]["axis_extents_permille"][1] = 2
        form = surface_preview.validate_envelope(payload)
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        surface_preview._validate_hybrid_guide(guide)
        sections = guide.torso_cage.sections
        self.assertTrue(
            all(
                np.isfinite(value)
                for section in sections
                for value in section.center
            )
        )
        self.assertTrue(all(sections[index].center[1] < sections[index + 1].center[1] for index in range(len(sections) - 1)))

    def test_generated_torso_junctions_are_on_symmetric_cage_boundary_for_all_variants(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            fields = surface_preview._compile_hybrid_guide(guide)
            torso_field = next(item for item in fields if item.recipe == "torso-cage")
            torso = next(item for item in descriptors if item.key[3] == "torso")
            pelvis = next(item for item in descriptors if item.key[3] == "pelvis")
            torso_center = surface_preview._source_shape(torso, form.reference_scale)["center"]
            pelvis_center = surface_preview._source_shape(pelvis, form.reference_scale)["center"]

            shoulder_guides = [item for item in guide.limb_guides if item.owner.key[3] == "upper_arm"]
            hip_guides = [item for item in guide.limb_guides if item.owner.key[3] == "thigh"]
            shoulder_points = np.asarray([item.root_centerline[0] for item in shoulder_guides])  # type: ignore[index]
            hip_points = np.asarray([item.hip_centerline[0] for item in hip_guides])  # type: ignore[index]
            neck_point = np.asarray([guide.head_guide.neck_transition[0]])
            for points in (shoulder_points, hip_points, neck_point):
                residual = surface_preview._field(points, torso_field)
                self.assertTrue(np.all(np.isfinite(residual)))
            if points is neck_point:
                self.assertLessEqual(float(residual[0]), 0.0)
            else:
                np.testing.assert_allclose(residual, 0.0, atol=1.0e-12)
            self.assertTrue(np.all(np.linalg.norm(shoulder_points - torso_center, axis=1) > 1.0e-9))
            self.assertTrue(np.all(np.linalg.norm(hip_points - pelvis_center, axis=1) > 1.0e-9))
            self.assertGreater(float(np.linalg.norm(neck_point[0] - torso_center)), 1.0e-9)

            np.testing.assert_allclose(shoulder_points[0, 1:], shoulder_points[1, 1:], atol=1.0e-12)
            self.assertAlmostEqual(float(shoulder_points[0, 0]), -float(shoulder_points[1, 0]), places=12)
            np.testing.assert_allclose(hip_points[0, 1:], hip_points[1, 1:], atol=1.0e-12)
            self.assertAlmostEqual(float(hip_points[0, 0]), -float(hip_points[1, 0]), places=12)

            torso_key = torso.key
            pelvis_key = pelvis.key
            self.assertEqual(surface_preview._field_owner_keys(shoulder_points, torso_field), (torso_key, torso_key))
            self.assertEqual(surface_preview._field_owner_keys(hip_points, torso_field), (pelvis_key, pelvis_key))
            self.assertEqual(surface_preview._field_owner_keys(neck_point, torso_field), (torso_key,))

    def test_embedded_branch_connectors_reduce_sampled_boundary_overshoot(self) -> None:
        form = surface_preview.validate_envelope(make_varied_payload())
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            fields = surface_preview._compile_hybrid_guide(guide)
            torso_field = next(item for item in fields if item.recipe == "torso-cage")
            for limb in guide.limb_guides:
                if limb.owner.key[3] not in {"upper_arm", "thigh"}:
                    continue
                paths = [("root-bridge", limb.root_centerline, limb.root_thickness)]
                if limb.hip_centerline is not None:
                    paths.append(("hip-transition", limb.hip_centerline, limb.hip_thickness))
                for recipe, semantic_path, semantic_profile in paths:
                    if semantic_path is None or semantic_profile is None:
                        continue
                    bridge = next(item for item in fields if item.owner is limb.owner and item.recipe == recipe)
                    semantic_anchor = np.asarray(semantic_path[0], dtype=np.float64)
                    target = np.asarray(semantic_path[1], dtype=np.float64)
                    support = float(bridge.shape["r0"])
                    compiled_start = bridge.shape["from"]

                    # Derive the branch-facing side from the cage boundary and
                    # its owning section, not from the child path's axial
                    # component. In the fixed fixture the child target is
                    # inward of this side; the connector moves toward it.
                    section = guide.torso_cage.lower_boundary if limb.owner.key[3] == "thigh" else guide.torso_cage.upper_boundary
                    side = semantic_anchor[[0, 2]] - np.asarray(section.center, dtype=np.float64)[[0, 2]]
                    side /= np.linalg.norm(side)
                    outward = np.asarray([side[0], 0.0, side[1]])
                    inward = -outward
                    np.testing.assert_allclose(compiled_start, semantic_anchor + inward * support, atol=1.0e-12)
                    self.assertGreater(float(np.linalg.norm(compiled_start - target)), 1.0e-9)

                    # Sample beyond the branch-facing cage side. The current
                    # support must have no measurable field outside the
                    # semantic boundary; the centreline itself must remain a
                    # negative, non-degenerate connection into the child.
                    distances = np.linspace(0.0, support * 1.5, 64)
                    samples = semantic_anchor[None, :] + distances[:, None] * outward[None, :]
                    values = surface_preview._field(samples, bridge)
                    outside = distances[values <= 1.0e-10]
                    observed_excess = float(np.max(outside)) if len(outside) else 0.0
                    self.assertLessEqual(observed_excess, 1.0e-10)
                    midpoint = (compiled_start + target) * 0.5
                    self.assertLess(float(surface_preview._field(np.asarray([midpoint]), bridge)[0]), 0.0)
                    self.assertAlmostEqual(float(surface_preview._field(np.asarray([semantic_anchor]), torso_field)[0]), 0.0, places=12)

    def test_torso_cage_dimensions_are_consumed_by_the_swept_field(self) -> None:
        import dataclasses

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        baseline = surface_preview._compile_hybrid_guide(guide)
        baseline_cage = next(item for item in baseline if item.recipe == "torso-cage")
        cage = guide.torso_cage
        lower_abdomen = cage.section("lower-abdomen")
        lower_abdomen_index = next(index for index, section in enumerate(cage.sections) if section is lower_abdomen)
        changed_section = dataclasses.replace(
            lower_abdomen,
            lateral_radius=lower_abdomen.lateral_radius * 0.75,
            anterior_radius=lower_abdomen.anterior_radius * 0.75,
            posterior_radius=lower_abdomen.posterior_radius * 0.75,
            depth_radius=lower_abdomen.depth_radius * 0.75,
        )
        changed_cage = dataclasses.replace(
            cage,
            sections=tuple(changed_section if index == lower_abdomen_index else section for index, section in enumerate(cage.sections)),
        )
        changed = surface_preview._compile_hybrid_guide(
            dataclasses.replace(guide, torso_cage=changed_cage)
        )
        changed_cage_field = next(item for item in changed if item.recipe == "torso-cage")
        self.assertLess(float(changed_cage_field.shape["lateral_radii"][lower_abdomen_index]), float(baseline_cage.shape["lateral_radii"][lower_abdomen_index]))
        self.assertLess(float(changed_cage_field.shape["depth_radii"][lower_abdomen_index]), float(baseline_cage.shape["depth_radii"][lower_abdomen_index]))

        # The shoulder/hip masses remain private guide diagnostics and are no
        # longer emitted as duplicate skin fields; the cage itself is the
        # only torso/pelvis field and connector controls consume its boundary.
        self.assertNotIn("hip-girdle", {item.recipe for item in baseline})
        self.assertNotIn("shoulder-mass", {item.recipe for item in baseline})

    def test_torso_cage_field_is_finite_elliptical_and_has_rounded_caps(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        field = next(item for item in surface_preview._compile_hybrid_guide(guide) if item.recipe == "torso-cage")
        shape = field.shape
        centres = shape["centers"]
        heights = shape["heights"]
        samples = np.asarray([
            [0.0, heights[0] - 0.75 * shape["cap_radii"][0], 0.0],
            [0.0, heights[0], 0.0],
            [shape["lateral_radii"][2], heights[2], 0.0],
            [0.0, heights[-1], 0.0],
            [0.0, heights[-1] + shape["cap_radii"][-1], 0.0],
        ])
        values = surface_preview._field(samples, field)
        self.assertTrue(np.all(np.isfinite(values)))
        self.assertLess(float(values[0]), 0.0)
        self.assertLess(float(values[1]), 0.0)
        self.assertAlmostEqual(float(values[2]), 0.0, places=12)
        self.assertLess(float(values[3]), 0.0)
        # The rounded cap evaluates at its zero boundary; tolerate the tiny
        # negative residual from floating-point square-root arithmetic.
        self.assertGreaterEqual(float(values[4]), -1.0e-12)
        for index, (centre, height, lateral, depth) in enumerate(zip(
            shape["centers"], shape["heights"], shape["lateral_radii"], shape["depth_radii"]
        )):
            section_points = np.asarray([
                centre,
                [centre[0] + lateral, height, centre[2]],
                [centre[0], height, centre[2] + depth],
            ])
            section_values = surface_preview._field(section_points, field)
            self.assertLess(float(section_values[0]), 0.0, index)
            np.testing.assert_allclose(section_values[1:], [0.0, 0.0], atol=1e-12)
        midpoint = (heights[:-1] + heights[1:]) * 0.5
        # The profile is clamped and monotone between ordered sections; no
        # interpolation control can exceed its adjacent source values.
        for index, y in enumerate(midpoint):
            point = np.asarray([[centres[index, 0], y, centres[index, 2]]])
            self.assertLess(float(surface_preview._field(point, field)[0]), 0.0)

    def test_monotone_cubic_torso_profile_is_exact_bounded_and_c1(self) -> None:
        x = np.asarray([0.0, 0.7, 2.0, 3.4, 5.0])
        radii = np.asarray([1.0, 1.8, 1.2, 1.55, 1.1])
        slopes = surface_preview._monotone_cubic_slopes(x, radii)
        dense = np.linspace(x[0], x[-1], 2001)
        sampled = surface_preview._monotone_cubic_sample(x, radii, slopes, dense)
        for index, value in enumerate(radii):
            self.assertEqual(float(surface_preview._monotone_cubic_sample(x, radii, slopes, x[index])), float(value))
        for index in range(len(x) - 1):
            interval = (dense >= x[index]) & (dense <= x[index + 1])
            self.assertTrue(np.all(sampled[interval] >= min(radii[index], radii[index + 1]) - 1.0e-12))
            self.assertTrue(np.all(sampled[interval] <= max(radii[index], radii[index + 1]) + 1.0e-12))
            self.assertTrue(np.all(sampled[interval] > 0.0))
        epsilon = 1.0e-5
        for coordinate in x[1:-1]:
            left = (surface_preview._monotone_cubic_sample(x, radii, slopes, coordinate) - surface_preview._monotone_cubic_sample(x, radii, slopes, coordinate - epsilon)) / epsilon
            right = (surface_preview._monotone_cubic_sample(x, radii, slopes, coordinate + epsilon) - surface_preview._monotone_cubic_sample(x, radii, slopes, coordinate)) / epsilon
            self.assertAlmostEqual(float(left), float(right), places=4)

    def test_monotone_cubic_matches_independent_hand_calculation(self) -> None:
        # x=[0,1,2,4], y=[0,1,2,5/2] gives secants [1,1,1/4].
        # The shape-preserving tangents are [1,1,3/7,0].  At t=1/2 in
        # [1,2] and [2,4], the Hermite values are 11/7 and 33/14.
        x = np.asarray([0.0, 1.0, 2.0, 4.0])
        values = np.asarray([0.0, 1.0, 2.0, 2.5])
        slopes = surface_preview._monotone_cubic_slopes(x, values)
        np.testing.assert_allclose(slopes, [1.0, 1.0, 3.0 / 7.0, 0.0], rtol=0.0, atol=1.0e-14)
        np.testing.assert_allclose(
            surface_preview._monotone_cubic_sample(x, values, slopes, np.asarray([0.5, 1.5, 3.0])),
            [0.5, 11.0 / 7.0, 33.0 / 14.0],
            rtol=0.0,
            atol=1.0e-14,
        )

    def test_monotone_cubic_rejects_nonfinite_derived_controls(self) -> None:
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._monotone_cubic_slopes(
                np.asarray([0.0, 1.0e-320, 2.0e-320]),
                np.asarray([0.0, 1.0, 2.0]),
            )
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._monotone_cubic_slopes(
                np.asarray([-1.0e308, 0.0, 1.0e308]),
                np.asarray([0.0, 1.0, 2.0]),
            )
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._monotone_cubic_sample(
                np.asarray([0.0, 1.0, 2.0]),
                np.asarray([0.0, 1.0, 2.0]),
                np.asarray([1.0, np.nan, 1.0]),
                0.5,
            )

    def test_torso_cage_sampling_uses_shared_smoothed_controls_for_field_and_anchors(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        for _, descriptors, _ in form.variants:
            guide = surface_preview._derive_hybrid_guides(form, descriptors)
            cage = guide.torso_cage
            shape = surface_preview._torso_cage_shape(cage)
            field = surface_preview.Field(guide.torso_cage.torso_owner, "torso-cage", shape)
            lower, upper = shape["heights"][[0, -1]]
            for axial in np.linspace(lower, upper, 11):
                center, lateral, depth = surface_preview._torso_cage_sample_controls(shape, axial)
                point = surface_preview._torso_cage_boundary_anchor(cage, float(axial), (1.0, 0.0, 0.35))
                np.testing.assert_allclose(center[1], axial, atol=1.0e-12)
                np.testing.assert_allclose(
                    ((point[0] - center[0]) / lateral) ** 2 + ((point[2] - center[2]) / depth) ** 2,
                    1.0,
                    atol=1.0e-12,
                )
                self.assertAlmostEqual(float(surface_preview._field(np.asarray([point]), field)[0]), 0.0, places=12)

    def test_torso_cage_attribution_switches_deterministically_between_source_owners(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        field = next(item for item in surface_preview._compile_hybrid_guide(guide) if item.recipe == "torso-cage")
        heights = field.shape["heights"]
        lower_midpoint = (heights[0] + heights[1]) * 0.5
        upper_midpoint = (heights[2] + heights[3]) * 0.5
        # Pick the representable sample immediately below the mathematical
        # midpoint; this avoids making the test depend on which side a binary
        # float happens to round the exact midpoint toward.
        tie = np.nextafter((heights[1] + heights[2]) * 0.5, heights[1])
        points = np.asarray([[0.0, lower_midpoint, 0.0], [0.0, upper_midpoint, 0.0], [0.0, tie, 0.0]])
        labels = surface_preview._field_owner_keys(points, field)
        self.assertEqual(labels[0][3], "pelvis")
        self.assertEqual(labels[1][3], "torso")
        self.assertEqual(labels[2][3], "pelvis")
        off_axis = np.asarray([
            [100.0, lower_midpoint, -100.0],
            [-100.0, upper_midpoint, 100.0],
            [250.0, tie, -250.0],
        ])
        self.assertEqual(surface_preview._field_owner_keys(off_axis, field), labels)

    def test_torso_cage_boundary_query_handles_interpolation_and_end_caps(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        cage = guide.torso_cage
        lower = cage.lower_boundary
        upper = cage.upper_boundary
        midpoint = (cage.section("lower-abdomen").center[1] + cage.section("waist-abdomen").center[1]) * 0.5
        point = surface_preview._torso_cage_boundary_anchor(cage, midpoint, (1.0, 0.0, 0.5))
        shape = surface_preview._torso_cage_shape(cage)
        sampled_center, sampled_lateral, sampled_depth = surface_preview._torso_cage_sample_controls(shape, midpoint)
        self.assertAlmostEqual(
            ((point[0] - sampled_center[0]) / sampled_lateral) ** 2
            + ((point[2] - sampled_center[2]) / sampled_depth) ** 2,
            1.0,
            places=12,
        )
        lower_point = surface_preview._torso_cage_boundary_anchor(cage, lower.center[1] - 10.0, (-1.0, 0.0, 0.0))
        upper_point = surface_preview._torso_cage_boundary_anchor(cage, upper.center[1] + 10.0, (0.0, 1.0, 0.0))
        self.assertAlmostEqual(float(lower_point[1]), float(lower.center[1]), places=12)
        self.assertAlmostEqual(float(upper_point[1]), float(upper.center[1] + min(upper.lateral_radius, upper.depth_radius)), places=12)
        self.assertAlmostEqual(float(surface_preview._field(np.asarray([point]), surface_preview.Field(guide.torso_cage.torso_owner, "torso-cage", surface_preview._torso_cage_shape(cage)))[0]), 0.0, places=12)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._torso_cage_boundary_anchor(cage, midpoint, (0.0, 0.0, 0.0))

    def test_role_recipes_anchor_limbs_and_expand_head_and_paw(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        fields = surface_preview._compound_fields(form, descriptors)
        source_keys = {descriptor.key for descriptor in descriptors}
        self.assertTrue(fields)
        self.assertTrue(all(field.owner.key in source_keys for field in fields))
        expected_recipes = {
            "torso-cage",
            "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
            "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal", "thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint",
            "elbow", "knee", "hock", "root-bridge", "hip-transition",
            "paw", "metatarsal", "paw-pad", "toe-box", "extremity-bridge", "tail-segment", "tail-tip-extension", "tail-tip-cap", "tail-root-bridge",
            "tail-root-collar",
        }
        expected_recipes.add("deltoid-sweep-1")
        self.assertEqual({field.recipe for field in fields}, expected_recipes)
        self.assertEqual(len(fields), 52)

        pelvis = next(item for item in descriptors if item.key[3] == "pelvis")
        torso = next(item for item in descriptors if item.key[3] == "torso")
        torso_field = next(item for item in fields if item.recipe == "torso-cage")
        self.assertIs(torso_field.owner, torso)
        self.assertEqual(
            tuple(owner.key[3] for owner in torso_field.shape["section_owners"]),
            ("pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso"),
        )
        self.assertTrue(any(owner is pelvis for owner in torso_field.shape["section_owners"]))
        self.assertNotIn("axial-trunk", {field.recipe for field in fields})

        upper_arm = next(item for item in descriptors if item.key[3] == "upper_arm")
        bridge = next(item for item in fields if item.owner is upper_arm and item.recipe == "root-bridge")
        torso = next(item for item in descriptors if item.key[3] == "torso")
        self.assertFalse((bridge.shape["from"] == torso.point).all(), "limb bridge must not start at torso centre")
        self.assertTrue((bridge.shape["to"] == surface_preview._source_shape(upper_arm, form.reference_scale)["from"]).all())
        upper_arm_shape = surface_preview._source_shape(upper_arm, form.reference_scale)
        upper_arm_radius = surface_preview._radius_from_shape(upper_arm_shape)
        guide = surface_preview._derive_hybrid_guides(form, descriptors)
        torso_cage = guide.torso_cage
        left_upper_arm = next(
            item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "upper_arm"
        )
        right_upper_arm = next(
            item for item in descriptors if item.key[1] == ("right",) and item.key[3] == "upper_arm"
        )
        self.assertEqual(
            [item.recipe for item in fields if item.owner is left_upper_arm],
            ["upper_arm-pre-joint", "upper_arm-joint", "root-bridge", "elbow", "deltoid-sweep-1"],
        )

        left_thigh = next(
            item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "thigh"
        )
        right_thigh = next(
            item for item in descriptors if item.key[1] == ("right",) and item.key[3] == "thigh"
        )
        left_hip = next(item for item in fields if item.owner is left_thigh and item.recipe == "hip-transition")
        right_hip = next(item for item in fields if item.owner is right_thigh and item.recipe == "hip-transition")
        left_thigh_shape = surface_preview._source_shape(left_thigh, form.reference_scale)
        thigh_radius = surface_preview._radius_from_shape(left_thigh_shape)
        left_hip_guide = next(item for item in surface_preview._derive_hybrid_guides(form, descriptors).limb_guides if item.owner is left_thigh)
        np.testing.assert_allclose(
            left_hip.shape["from"],
            surface_preview._embed_boundary_connector(left_hip_guide.hip_centerline, left_hip_guide.hip_thickness, "test")[0],  # type: ignore[arg-type]
        )
        np.testing.assert_allclose(
            left_hip.shape["to"],
            left_thigh_shape["from"] + 0.35 * (left_thigh_shape["to"] - left_thigh_shape["from"]),
        )
        self.assertAlmostEqual(float(left_hip.shape["r0"]), 0.78 * thigh_radius, places=12)
        self.assertAlmostEqual(float(left_hip.shape["r1"]), 0.66 * thigh_radius, places=12)
        self.assertIs(left_hip.owner, left_thigh)
        np.testing.assert_allclose(left_hip.shape["from"][[1, 2]], right_hip.shape["from"][[1, 2]])
        np.testing.assert_allclose(left_hip.shape["to"][[1, 2]], right_hip.shape["to"][[1, 2]])
        self.assertAlmostEqual(float(left_hip.shape["from"][0]), -float(right_hip.shape["from"][0]))
        self.assertAlmostEqual(float(left_hip.shape["to"][0]), -float(right_hip.shape["to"][0]))
        self.assertEqual(
            [item.recipe for item in fields if item.owner is left_thigh],
            ["thigh-pre-joint", "thigh-joint", "root-bridge", "hip-transition", "knee"],
        )
        neck = next(item for item in descriptors if item.key[3] == "neck")
        neck_field = next(item for item in fields if item.owner is neck and item.recipe == "tapered-neck")
        np.testing.assert_allclose(
            neck_field.shape["from"],
            guide.head_guide.profile.sections[0].center,
        )

        forearm = next(
            item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "forearm"
        )
        self.assertEqual(
            [item.recipe for item in fields if item.owner is forearm],
            ["forearm-proximal", "forearm-distal"],
        )

        torso_field = next(item for item in fields if item.owner is torso and item.recipe == "torso-cage")
        self.assertEqual(torso_field.shape["name"], "torso-cage")
        self.assertEqual(len(torso_field.shape["centers"]), 7)

        hand = next(item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "hand")
        paw = next(item for item in fields if item.owner is hand and item.recipe == "paw")
        source_hand = surface_preview._source_shape(hand, form.reference_scale)
        self.assertGreater(float(paw.shape["radii"][2]), float(source_hand["radii"][2]))
        hand_bridge = next(item for item in fields if item.owner is hand and item.recipe == "extremity-bridge")
        forearm = next(item for item in descriptors if item.key == hand.parent)
        hand_anchor_value = surface_preview._field(hand_bridge.shape["from"].reshape(1, 3), forearm, form.reference_scale)[0]
        self.assertAlmostEqual(float(hand_anchor_value), 0.0, places=12)

        foot = next(item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "foot")
        foot_guide = next(item for item in surface_preview._derive_hybrid_guides(form, descriptors).paw_guides if item.owner is foot)
        assert foot_guide.foot_chain is not None
        chain = foot_guide.foot_chain
        metatarsal = next(item for item in fields if item.owner is foot and item.recipe == "metatarsal")
        foot_pad = next(item for item in fields if item.owner is foot and item.recipe == "paw-pad")
        foot_front = next(item for item in fields if item.owner is foot and item.recipe == "toe-box")
        np.testing.assert_allclose(metatarsal.shape["from"], chain.hock_anchor)
        np.testing.assert_allclose(metatarsal.shape["to"], chain.pad_center)
        np.testing.assert_allclose(metatarsal.shape["r0"], chain.metatarsal_profile[0])
        np.testing.assert_allclose(metatarsal.shape["r1"], chain.metatarsal_profile[1])
        np.testing.assert_allclose(foot_pad.shape["center"], chain.pad_center)
        np.testing.assert_allclose(foot_pad.shape["radii"], chain.pad_radii)
        np.testing.assert_allclose(foot_front.shape["center"], chain.toe_center)
        np.testing.assert_allclose(foot_front.shape["radii"], chain.toe_radii)
        self.assertEqual([item.recipe for item in fields if item.owner is foot], ["metatarsal", "paw-pad", "toe-box"])

        tail_root = next(item for item in descriptors if item.key[3] == "tail_root")
        tail_tip = next(item for item in descriptors if item.key[3] == "tail_tip")
        root_shape = surface_preview._source_shape(tail_root, form.reference_scale)
        tip_shape = surface_preview._source_shape(tail_tip, form.reference_scale)
        root_fields = [item for item in fields if item.owner is tail_root]
        tip_fields = [item for item in fields if item.owner is tail_tip]
        self.assertEqual(
            [item.recipe for item in root_fields],
            ["tail-segment", "tail-root-bridge", "tail-root-collar"],
        )
        self.assertEqual(
            [item.recipe for item in tip_fields],
            ["tail-segment", "tail-tip-extension", "tail-tip-cap"],
        )
        root_segment = root_fields[0]
        np.testing.assert_allclose(root_segment.shape["from"], root_shape["from"])
        np.testing.assert_allclose(root_segment.shape["to"], root_shape["to"])
        self.assertAlmostEqual(float(root_segment.shape["r0"]), 1.15 * float(root_shape["r0"]), places=12)
        self.assertAlmostEqual(float(root_segment.shape["r1"]), 1.35 * float(root_shape["r1"]), places=12)
        tip_segment, tip_extension, tip_cap = tip_fields
        np.testing.assert_allclose(tip_segment.shape["from"], tip_shape["from"])
        np.testing.assert_allclose(tip_segment.shape["to"], tip_shape["to"])
        self.assertAlmostEqual(float(tip_segment.shape["r0"]), 1.35 * float(tip_shape["r0"]), places=12)
        self.assertAlmostEqual(float(tip_segment.shape["r1"]), 0.90 * float(tip_shape["r0"]), places=12)
        np.testing.assert_allclose(tip_extension.shape["from"], tip_shape["to"])
        np.testing.assert_allclose(
            tip_extension.shape["to"],
            tip_shape["to"] + 0.50 * (tip_shape["to"] - tip_shape["from"]),
        )
        self.assertAlmostEqual(float(tip_extension.shape["r0"]), float(tip_segment.shape["r1"]), places=12)
        self.assertAlmostEqual(float(tip_extension.shape["r1"]), 0.55 * float(tip_shape["r0"]), places=12)
        np.testing.assert_allclose(tip_cap.shape["center"], tip_extension.shape["to"])
        np.testing.assert_allclose(tip_cap.shape["radii"], np.full(3, 0.70 * float(tip_shape["r0"])))
        root_bridge = next(item for item in root_fields if item.recipe == "tail-root-bridge")
        root_collar = next(item for item in root_fields if item.recipe == "tail-root-collar")
        np.testing.assert_allclose(
            root_bridge.shape["from"],
            surface_preview._parent_surface_anchor(pelvis, root_shape["to"], form.reference_scale),
        )
        np.testing.assert_allclose(root_bridge.shape["to"], root_shape["to"])
        np.testing.assert_allclose(root_collar.shape["center"], root_shape["to"])
        np.testing.assert_allclose(
            root_collar.shape["radii"],
            root_shape["r1"] * np.asarray([1.50, 1.50, 1.80]),
        )
        self.assertTrue(all(item.owner is tail_root for item in root_fields))
        self.assertTrue(all(item.owner is tail_tip for item in tip_fields))

    def test_authored_head_neck_profile_drives_compatibility_recipes_and_source_ownership(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        guide = surface_preview._derive_hybrid_guides(form, descriptors)
        fields = surface_preview._compile_hybrid_guide(guide)
        head = next(item for item in descriptors if item.key[3] == "head")
        neck = next(item for item in descriptors if item.key[3] == "neck")
        cranium = next(item for item in fields if item.owner is head and item.recipe == "cranium")
        muzzle = next(item for item in fields if item.owner is head and item.recipe == "muzzle")
        head_base = next(item for item in fields if item.owner is head and item.recipe == "head-base-bridge")
        tapered_neck = next(item for item in fields if item.owner is neck and item.recipe == "tapered-neck")
        collar = next(item for item in fields if item.owner is neck and item.recipe == "neck-collar")
        stations = {section.name: section for section in guide.head_guide.profile.sections}

        np.testing.assert_allclose(cranium.shape["center"], stations["cranium-mid"].center)
        np.testing.assert_allclose(cranium.shape["radii"], stations["cranium-mid"].radii)
        np.testing.assert_allclose(muzzle.shape["center"], stations["muzzle-mid"].center)
        np.testing.assert_allclose(muzzle.shape["radii"], stations["muzzle-mid"].radii)
        np.testing.assert_allclose(head_base.shape["from"], stations["neck-upper"].center)
        np.testing.assert_allclose(head_base.shape["to"], stations["head-base"].center)
        self.assertEqual(
            (head_base.shape["r0"], head_base.shape["r1"]),
            (min(stations["neck-upper"].radii), min(stations["head-base"].radii)),
        )
        np.testing.assert_allclose(tapered_neck.shape["from"], stations["neck-collar"].center)
        np.testing.assert_allclose(tapered_neck.shape["to"], stations["neck-upper"].center)
        self.assertEqual(
            (tapered_neck.shape["r0"], tapered_neck.shape["r1"]),
            (min(stations["neck-collar"].radii), min(stations["neck-upper"].radii)),
        )
        np.testing.assert_allclose(collar.shape["center"], stations["neck-collar"].center)
        np.testing.assert_allclose(collar.shape["radii"], stations["neck-collar"].radii)

        cranium_bottom = float(cranium.shape["center"][1] - cranium.shape["radii"][1])
        cranium_top = float(cranium.shape["center"][1] + cranium.shape["radii"][1])
        muzzle_bottom = float(muzzle.shape["center"][1] - muzzle.shape["radii"][1])
        muzzle_top = float(muzzle.shape["center"][1] + muzzle.shape["radii"][1])
        self.assertLess(muzzle_bottom, cranium_top)
        self.assertGreater(muzzle_top, cranium_bottom)
        self.assertEqual(len(fields), 52)
        source_keys = {descriptor.key for descriptor in descriptors}
        self.assertTrue(all(field.owner.key in source_keys for field in fields))
        self.assertEqual(len(guide.head_guide.profile.sections), 8)
        self.assertEqual(len(guide.head_guide.profile.connections), 7)

    def test_segment_parent_surface_anchor_uses_radius_and_fails_when_ambiguous(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        neck = next(item for item in descriptors if item.key[3] == "neck")
        head = next(item for item in descriptors if item.key[3] == "head")
        head_cap = surface_preview._parent_surface_anchor(neck, head.point, form.reference_scale)
        self.assertAlmostEqual(float(head_cap[0]), 0.0)
        self.assertAlmostEqual(float(head_cap[1]), 3.35)
        self.assertAlmostEqual(float(head_cap[2]), 0.0)
        side = surface_preview._parent_surface_anchor(neck, np.asarray([1.0, 2.5, 0.0]), form.reference_scale)
        self.assertAlmostEqual(float(side[0]), 0.35)
        self.assertAlmostEqual(float(side[1]), 2.5)
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._parent_surface_anchor(neck, np.asarray([0.0, 2.5, 0.0]), form.reference_scale)

        tail_root = next(item for item in descriptors if item.key[3] == "tail_root")
        tapered_side = surface_preview._parent_surface_anchor(tail_root, np.asarray([1.0, 0.0, -0.5]), form.reference_scale)
        self.assertAlmostEqual(float(tapered_side[0]), 0.26)
        self.assertAlmostEqual(float(tapered_side[2]), -0.5)

    def test_role_recipes_reject_nonconforming_axis_placement(self) -> None:
        payload = make_payload()
        for variant in payload["variants"]:
            upper_arm = next(
                item for item in variant["descriptors"]
                if item["address"]["anchors"] == ["left"] and item["address"]["role"] == "upper_arm"
            )
            upper_arm["reference_point"] = [0, 2, -1]
            upper_arm["shape"]["from"] = [0, 2, -1]
        form = surface_preview.validate_envelope(payload)
        with self.assertRaisesRegex(surface_preview.PreviewError, r"\+Y-up/\+Z-forward"):
            surface_preview._compound_fields(form, form.variants[0][1])

    def test_recipe_order_owner_labels_and_resource_accounting_are_deterministic(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        first = surface_preview._compound_fields(form, descriptors)
        second = surface_preview._compound_fields(form, descriptors)
        self.assertEqual([(field.owner.key, field.recipe) for field in first], [(field.owner.key, field.recipe) for field in second])
        self.assertEqual(
            [(field.owner.key[1], field.owner.key[3], field.recipe) for field in first],
            [
                ((), "head", "cranium"), ((), "head", "muzzle"), ((), "head", "head-base-bridge"),
                ((), "neck", "tapered-neck"), ((), "neck", "neck-collar"), ((), "torso", "torso-cage"),
                (("left",), "foot", "metatarsal"), (("left",), "foot", "paw-pad"), (("left",), "foot", "toe-box"),
                (("left",), "forearm", "forearm-proximal"), (("left",), "forearm", "forearm-distal"),
                (("left",), "hand", "paw"), (("left",), "hand", "extremity-bridge"),
                (("left",), "shin", "shin-pre-joint"), (("left",), "shin", "shin-joint"), (("left",), "shin", "hock"),
                (("left",), "thigh", "thigh-pre-joint"), (("left",), "thigh", "thigh-joint"),
                (("left",), "thigh", "root-bridge"), (("left",), "thigh", "hip-transition"),
                (("left",), "thigh", "knee"),
                (("left",), "upper_arm", "upper_arm-pre-joint"), (("left",), "upper_arm", "upper_arm-joint"),
                (("left",), "upper_arm", "root-bridge"), (("left",), "upper_arm", "elbow"),
                (("left",), "upper_arm", "deltoid-sweep-1"),
                (("right",), "foot", "metatarsal"), (("right",), "foot", "paw-pad"), (("right",), "foot", "toe-box"),
                (("right",), "forearm", "forearm-proximal"), (("right",), "forearm", "forearm-distal"),
                (("right",), "hand", "paw"), (("right",), "hand", "extremity-bridge"),
                (("right",), "shin", "shin-pre-joint"), (("right",), "shin", "shin-joint"), (("right",), "shin", "hock"),
                (("right",), "thigh", "thigh-pre-joint"), (("right",), "thigh", "thigh-joint"),
                (("right",), "thigh", "root-bridge"), (("right",), "thigh", "hip-transition"),
                (("right",), "thigh", "knee"),
                (("right",), "upper_arm", "upper_arm-pre-joint"), (("right",), "upper_arm", "upper_arm-joint"),
                (("right",), "upper_arm", "root-bridge"), (("right",), "upper_arm", "elbow"),
                (("right",), "upper_arm", "deltoid-sweep-1"),
                (("tail",), "tail_root", "tail-segment"), (("tail",), "tail_root", "tail-root-bridge"), (("tail",), "tail_root", "tail-root-collar"),
                (("tail",), "tail_tip", "tail-segment"), (("tail",), "tail_tip", "tail-tip-extension"), (("tail",), "tail_tip", "tail-tip-cap"),
            ],
        )
        recipe_signature = [(field.owner.key, field.recipe) for field in first]
        for _, variant_descriptors, _ in form.variants[1:]:
            self.assertEqual(recipe_signature, [(field.owner.key, field.recipe) for field in surface_preview._compound_fields(form, variant_descriptors)])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            input_path.write_bytes(surface_preview._canonical(make_payload()))
            output = root / "output"
            surface_preview.generate(input_path, output, samples=48, padding=0.5)
            manifest = json.loads((output / "surface-preview-manifest.json").read_text())
            metrics = manifest["variants"][0]["metrics"]
            self.assertEqual(metrics["source_descriptor_count"], 18)
            self.assertEqual(metrics["generated_field_count"], 52)
            self.assertEqual(metrics["field_memory_values"], metrics["generated_field_count"] * 48**3)
            source_keys = {json.dumps(descriptor.key, default=list) for descriptor in descriptors}
            winner_keys = {json.dumps(tuple((item["namespace"], tuple(item["anchors"]), item["kind"], item["role"])), default=list) for item in metrics["winner_addresses"]}
            self.assertTrue(winner_keys <= source_keys)

    def test_output_is_deterministic_and_has_exact_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); input_path = root / "input.json"; input_path.write_bytes(surface_preview._canonical(make_payload()))
            first = root / "first"; second = root / "second"
            surface_preview.generate(input_path, first, samples=48, padding=0.5)
            surface_preview.generate(input_path, second, samples=48, padding=0.5)
            first_files = sorted(x.relative_to(first).as_posix() for x in first.rglob("*") if x.is_file())
            self.assertEqual(len(first_files), 21)
            self.assertEqual(first_files, sorted(x.relative_to(second).as_posix() for x in second.rglob("*") if x.is_file()))
            for name in first_files:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
            manifest = json.loads((first / "surface-preview-manifest.json").read_text())
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["format"], "creature-kernel.disposable-surface-preview.v2")
            self.assertEqual(manifest["source_format"], surface_preview.SOURCE_FORMAT)
            self.assertEqual([x["id"] for x in manifest["variants"]], list(surface_preview.VARIANT_IDS))
            self.assertTrue(all(len(x["inventory"]) == 5 for x in manifest["variants"]))
            self.assertTrue(all(x["metrics"]["source_descriptor_count"] == 18 for x in manifest["variants"]))
            self.assertTrue(all(x["metrics"]["generated_field_count"] == 52 for x in manifest["variants"]))
            self.assertTrue(all(x["metrics"]["component_count"] == 1 and x["metrics"]["watertight"] for x in manifest["variants"]))
            self.assertEqual(
                sorted(path.name for path in (first / surface_preview.VARIANT_IDS[0]).iterdir()),
                ["guide-skin-composite.png", "metrics.json", "regional-guide.json", "semantic.json", "surface.ply"],
            )

    def test_v2_shared_frames_and_private_regional_controls_are_exact_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            input_path.write_bytes(surface_preview._canonical(make_varied_payload()))
            output = root / "output"
            manifest = surface_preview.generate(input_path, output, samples=48, padding=0.5)
            self.assertEqual([item["name"] for item in manifest["projections"]], ["front", "side", "three-quarter"])
            self.assertEqual(manifest["canvas"], {"width": 1800, "height": 570, "mode": "RGB"})
            self.assertEqual(manifest["layout"]["panel_order"], [
                "front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin",
            ])
            expected_bounds = manifest["shared_render_bounds"]
            grid_signatures = []
            guide_controls = []
            cage_topologies = []
            for variant in manifest["variants"]:
                grid_signatures.append((tuple(variant["grid"]["bounds_min"]), tuple(variant["grid"]["bounds_max"]), tuple(variant["grid"]["spacing"])))
                regional = json.loads((output / variant["id"] / "regional-guide.json").read_text())
                self.assertEqual(regional["variant"], variant["id"])
                self.assertEqual(regional["format"], surface_preview.REGIONAL_GUIDE_FORMAT)
                self.assertEqual(regional["shared_render_bounds"], expected_bounds)
                self.assertEqual(regional["counts"]["owners"], 18)
                self.assertEqual(regional["counts"]["axial_stations"], 3)
                self.assertEqual(regional["counts"]["axial_transitions"], 2)
                self.assertEqual(regional["counts"]["axial_core_masses"], 1)
                self.assertEqual(regional["counts"]["torso_cage_sections"], 7)
                self.assertEqual(regional["counts"]["torso_cage_connections"], 6)
                self.assertEqual(regional["counts"]["shoulder_frame_sides"], 2)
                self.assertEqual(regional["counts"]["shoulder_frame_curves"], 6)
                self.assertEqual(regional["counts"]["shoulder_frame_compiled_fields"], 2)
                self.assertEqual(regional["counts"]["arm_profile_sides"], 2)
                self.assertEqual(regional["counts"]["arm_profile_sections"], 10)
                self.assertEqual(regional["counts"]["leg_profile_sides"], 2)
                self.assertEqual(regional["counts"]["leg_profile_sections"], 10)
                self.assertEqual(regional["counts"]["head_neck_profile_sections"], 8)
                self.assertEqual(regional["counts"]["head_neck_profile_connections"], 7)
                self.assertEqual(regional["counts"]["compiled_fields"], 52)
                self.assertEqual(regional["counts"]["compiled_field_recipe_counts"], {
                    "upper_arm-pre-joint": 2, "upper_arm-joint": 2, "forearm-proximal": 2, "forearm-distal": 2,
                    "thigh-pre-joint": 2, "thigh-joint": 2, "shin-pre-joint": 2, "shin-joint": 2,
                    "elbow": 2, "knee": 2, "hock": 2, "paw": 2, "metatarsal": 2, "paw-pad": 2, "toe-box": 2,
                    "extremity-bridge": 2, "root-bridge": 4, "hip-transition": 2,
                    "tail-segment": 2, "cranium": 1,
                    "muzzle": 1, "head-base-bridge": 1, "tapered-neck": 1,
                    "neck-collar": 1, "torso-cage": 1,
                    "deltoid-sweep-1": 2,
                    "tail-root-bridge": 1, "tail-root-collar": 1,
                    "tail-tip-extension": 1, "tail-tip-cap": 1,
                })
                self.assertEqual([item["name"] for item in regional["projections"]], ["front", "side", "three-quarter"])
                self.assertEqual(regional["layout"], manifest["layout"])
                self.assertEqual(regional["canvas"], manifest["canvas"])
                self.assertTrue(regional["controls"]["axial"])
                self.assertTrue(regional["controls"]["torso_cage"])
                head = regional["controls"]["head"]
                self.assertEqual(head["profile_format"], surface_preview.AUTHORED_HEAD_NECK_PROFILE_FORMAT)
                self.assertEqual([item["name"] for item in head["sections"]], list(surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES))
                self.assertEqual(
                    [(item["name"], item["from_section_index"], item["to_section_index"], item["route"]) for item in head["connections"]],
                    list(surface_preview.HEAD_NECK_PROFILE_CONNECTIONS),
                )
                self.assertTrue(all({"lateral", "up", "forward"} <= set(item["lineage"]) for item in head["sections"]))
                self.assertTrue(all(all({"owner", "role", "index"} <= set(item["lineage"][axis]["reference"]) for axis in ("lateral", "up", "forward")) for item in head["sections"]))
                self.assertEqual(len(head["paths"]), 2)
                self.assertEqual(regional["controls"]["shoulder_frame"]["status"], "private shoulder frame; support curves guide-only; deltoid sweep skin-driving")
                shoulder_frame = regional["controls"]["shoulder_frame"]
                self.assertEqual([item["side"] for item in shoulder_frame["sides"]], ["left", "right"])
                self.assertEqual(set(shoulder_frame["owners"]), {"torso", "neck", "left_upper_arm", "right_upper_arm"})
                self.assertEqual(len(shoulder_frame["central"]["profile"]), 2)
                self.assertTrue(all(len(item["curves"]) == 3 for item in shoulder_frame["sides"]))
                self.assertTrue(all(len(curve["points"]) == len(curve["profile"]) for item in shoulder_frame["sides"] for curve in item["curves"]))
                self.assertTrue(all(curve["consumption"] == ("skin-driving" if curve["name"] == "deltoid-sweep" else "guide-only") for item in shoulder_frame["sides"] for curve in item["curves"]))
                self.assertTrue(regional["controls"]["limbs"])
                self.assertTrue(regional["controls"]["paws"])
                self.assertTrue(regional["controls"]["tails"])
                leg_profile = regional["controls"]["leg_profile"]
                self.assertEqual(leg_profile["format"], surface_preview.AUTHORED_LEG_PROFILE_FORMAT)
                self.assertEqual([item["side"] for item in leg_profile["sides"]], ["left", "right"])
                self.assertEqual(leg_profile["route_topology"]["section_names"], list(surface_preview.LEG_PROFILE_SECTION_NAMES))
                self.assertEqual(leg_profile["route_topology"]["owner_roles"], list(surface_preview.LEG_PROFILE_OWNER_ROLES))
                self.assertEqual(sum(len(item["sections"]) for item in leg_profile["sides"]), 10)
                self.assertTrue(all({"lateral", "up", "forward"} <= set(item["lineage"]) for side in leg_profile["sides"] for item in side["sections"]))
                axial = regional["controls"]["axial"]
                self.assertEqual(axial["status"], "compatibility-diagnostic-not-rendered")
                self.assertEqual([item["name"] for item in axial["stations"]], ["pelvic-girdle", "waist", "chest-girdle"])
                self.assertEqual([item["name"] for item in axial["transitions"]], ["pelvis-waist", "waist-chest"])
                self.assertEqual([item["owner"]["role"] for item in axial["stations"]], ["pelvis", "torso", "torso"])
                self.assertEqual([item["owner"]["role"] for item in axial["transitions"]], ["torso", "torso"])
                self.assertEqual(axial["core"]["mass"]["control"], "pelvic-core")
                self.assertEqual([item["recipe"] for item in axial["stations"]], ["hips", "waist", "chest"])
                self.assertEqual([item["recipe"] for item in axial["transitions"]], ["pelvis-waist-bridge", "waist-chest-bridge"])
                self.assertEqual(axial["transitions"][0]["path"]["path_kind"], "tapered-segment")
                self.assertLess(axial["stations"][1]["mass"]["radii"][0], axial["stations"][2]["mass"]["radii"][0])
                self.assertLess(axial["stations"][1]["mass"]["radii"][2], axial["stations"][2]["mass"]["radii"][2])
                cage = regional["controls"]["torso_cage"]
                self.assertEqual(cage["status"], "skin-driving torso controls")
                self.assertEqual([item["name"] for item in cage["sections"]], [
                    "lower-pelvis", "upper-pelvis", "lower-abdomen", "waist-abdomen", "upper-abdomen", "lower-ribcage", "upper-ribcage-shoulder",
                ])
                self.assertEqual([item["owner"]["role"] for item in cage["sections"]], ["pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso"])
                self.assertEqual(cage["axes"], {"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]})
                self.assertEqual(cage["connections"], [
                    {"from": "lower-pelvis", "to": "upper-pelvis"},
                    {"from": "upper-pelvis", "to": "lower-abdomen"},
                    {"from": "lower-abdomen", "to": "waist-abdomen"},
                    {"from": "waist-abdomen", "to": "upper-abdomen"},
                    {"from": "upper-abdomen", "to": "lower-ribcage"},
                    {"from": "lower-ribcage", "to": "upper-ribcage-shoulder"},
                ])
                cage_topologies.append((
                    tuple(item["name"] for item in cage["sections"]),
                    tuple(item["owner"]["role"] for item in cage["sections"]),
                    tuple((item["from"], item["to"]) for item in cage["connections"]),
                ))
                thigh = next(item for item in regional["controls"]["limbs"] if item["owner"]["role"] == "thigh")
                upper_arm = next(item for item in regional["controls"]["limbs"] if item["owner"]["role"] == "upper_arm")
                self.assertEqual({item["control"] for item in thigh["masses"]}, {"hip-girdle"})
                self.assertEqual({item["control"] for item in upper_arm["masses"]}, {"shoulder-girdle"})
                self.assertEqual([item["name"] for item in thigh["joints"]], ["knee"])
                self.assertEqual([item["name"] for item in upper_arm["joints"]], ["elbow"])
                forearm = next(item for item in regional["controls"]["limbs"] if item["owner"]["role"] == "forearm")
                self.assertEqual(forearm["joints"], [])
                self.assertEqual([item["name"] for item in forearm["anchors"]], ["forearm-distal-boundary"])
                self.assertEqual(forearm["anchors"][0]["kind"], "parent-surface-anchor")
                self.assertNotIn("centerline", upper_arm)
                self.assertNotIn("joint_narrowing", upper_arm)
                shin = next(item for item in regional["controls"]["limbs"] if item["owner"]["role"] == "shin")
                self.assertEqual([item["name"] for item in shin["anchors"]], ["hock-endpoint"])
                foot_control = next(item for item in regional["controls"]["paws"] if item["owner"]["role"] == "foot")
                self.assertEqual({item["control"] for item in foot_control["chain"]["masses"]}, {"paw-pad", "toe-box"})
                self.assertEqual(foot_control["chain"]["metatarsal"]["control"], "metatarsal")
                self.assertEqual(foot_control["chain"]["axes"], {"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]})
                hand_control = next(item for item in regional["controls"]["paws"] if item["owner"]["role"] == "hand")
                self.assertEqual(hand_control["attachment_source"]["owner"]["role"], "forearm")
                self.assertEqual(hand_control["attachment_source"]["anchor"], "forearm-distal-boundary")
                self.assertEqual(foot_control["hock_source"]["owner"]["role"], "shin")
                self.assertEqual(foot_control["hock_source"]["anchor"], "hock-endpoint")
                guide_controls.append(regional["controls"])

                def has_forbidden_key(value: object) -> bool:
                    if isinstance(value, dict):
                        return any(key in {"descriptor_kind", "shape"} or has_forbidden_key(item) for key, item in value.items())
                    if isinstance(value, list):
                        return any(has_forbidden_key(item) for item in value)
                    return False

                self.assertFalse(has_forbidden_key(regional))
                with Image.open(output / variant["id"] / "guide-skin-composite.png") as image:
                    self.assertEqual(image.size, (1800, 570))
            self.assertGreater(len(set(grid_signatures)), 1)
            self.assertEqual(len(set(cage_topologies)), 1)
            direct_form = surface_preview.validate_envelope(make_varied_payload())
            for variant_id, (_, descriptors, _) in zip(surface_preview.VARIANT_IDS, direct_form.variants):
                _, _, _, _, direct_metrics, direct_grid = surface_preview.build_variant(
                    direct_form, descriptors, 48, 0.5, surface_preview.DEFAULT_SMOOTH_K,
                )
                generated = next(item for item in manifest["variants"] if item["id"] == variant_id)
                self.assertEqual(generated["grid"], direct_grid)
                self.assertEqual(generated["metrics"], direct_metrics)
            self.assertNotEqual(guide_controls[0]["head"]["masses"], guide_controls[3]["head"]["masses"])

    def test_side_skin_projection_stays_inside_its_panel(self) -> None:
        # An intentionally asymmetric box makes a second side-basis
        # application obvious: the world X span is wide while side-screen X
        # is the narrow world Z span.  This is a lightweight renderer-level
        # regression rather than a mesh-extraction test.
        side_basis = np.asarray(next(item[1] for item in surface_preview.PROJECTIONS if item[0] == "side"), dtype=np.float64)
        side_box = next(item["box"] for item in surface_preview.PANEL_LAYOUT if item["id"] == "side-skin")
        bounds = (np.asarray([-3.0, -1.0, -0.5]), np.asarray([3.0, 1.0, 0.5]))
        frame = surface_preview._projection_frame(bounds, side_basis, side_box)
        vertices = np.asarray([
            [-3.0, -1.0, -0.5], [3.0, -1.0, -0.5], [3.0, 1.0, -0.5], [-3.0, 1.0, -0.5],
            [-3.0, -1.0, 0.5], [3.0, -1.0, 0.5], [3.0, 1.0, 0.5], [-3.0, 1.0, 0.5],
        ])
        faces = np.asarray([
            [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0],
        ], dtype=np.int64)
        image = Image.new("RGB", surface_preview.CANVAS, (0, 0, 0))
        surface_preview._draw_skin(ImageDraw.Draw(image), frame, vertices, faces)
        pixels = np.asarray(image)
        changed = np.any(pixels != 0, axis=2)
        self.assertTrue(np.any(changed))
        ys, xs = np.where(changed)
        x0, y0, x1, y1 = side_box
        self.assertGreaterEqual(int(xs.min()), x0)
        self.assertLess(int(xs.max()), x1)
        self.assertGreaterEqual(int(ys.min()), y0)
        self.assertLess(int(ys.max()), y1)

    def test_regional_sidecar_controls_match_compiled_recipe_geometry(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        _, descriptors, _ = form.variants[0]
        guide = surface_preview._derive_hybrid_guides(form, descriptors)
        fields = surface_preview._compile_hybrid_guide(guide)
        bounds = surface_preview._shared_render_bounds((fields,), 0.5)
        regional = surface_preview._regional_guide_json("neutral-v0", guide, bounds, compiled_fields=fields)
        axial = regional["controls"]["axial"]
        # The sidecar retains old axial controls only as an explicitly marked
        # compatibility diagnostic; the skin-driving controls are the cage.
        self.assertEqual(axial["status"], "compatibility-diagnostic-not-rendered")
        self.assertEqual([item["recipe"] for item in axial["stations"]], ["hips", "waist", "chest"])
        self.assertEqual([item["recipe"] for item in axial["transitions"]], ["pelvis-waist-bridge", "waist-chest-bridge"])
        torso_field = next(item for item in fields if item.recipe == "torso-cage")
        np.testing.assert_allclose(torso_field.shape["centers"], [section.center for section in guide.torso_cage.sections])
        np.testing.assert_allclose(torso_field.shape["lateral_radii"], [section.lateral_radius for section in guide.torso_cage.sections])
        np.testing.assert_allclose(torso_field.shape["depth_radii"], [section.depth_radius for section in guide.torso_cage.sections])
        cage = regional["controls"]["torso_cage"]
        self.assertEqual(cage["status"], "skin-driving torso controls")
        self.assertEqual([item["name"] for item in cage["sections"]], [section.name for section in guide.torso_cage.sections])
        np.testing.assert_allclose([item["center"] for item in cage["sections"]], [section.center for section in guide.torso_cage.sections])
        np.testing.assert_allclose([item["lateral_radius"] for item in cage["sections"]], [section.lateral_radius for section in guide.torso_cage.sections])
        np.testing.assert_allclose([item["depth_radius"] for item in cage["sections"]], [section.depth_radius for section in guide.torso_cage.sections])
        shoulder = regional["controls"]["shoulder_frame"]
        self.assertEqual(shoulder["central"]["owner"], surface_preview._address_json(guide.shoulder_frame.torso_owner.key))
        self.assertEqual(shoulder["central"]["anchor"], list(guide.shoulder_frame.central_anchor))
        for side_json, side in zip(shoulder["sides"], guide.shoulder_frame.sides):
            self.assertEqual(side_json["side"], side.side)
            self.assertEqual(side_json["span"], side.span)
            self.assertEqual(side_json["slope"], side.slope)
            for curve_json, curve in zip(side_json["curves"], (side.anterior_support, side.posterior_return, side.deltoid_sweep)):
                self.assertEqual(curve_json["name"], curve.name)
                self.assertEqual(curve_json["points"], [list(point) for point in curve.points])
                self.assertEqual(curve_json["profile"], list(curve.profile))
        for limb in regional["controls"]["limbs"]:
            for mass in limb["masses"]:
                recipe = {"shoulder-girdle": "shoulder-mass", "hip-girdle": "hip-girdle", "joint": "joint-collar"}[mass["control"]]
                self.assertNotIn(recipe, {item.recipe for item in fields})

    def test_invalid_private_guide_data_fails_closed(self) -> None:
        import dataclasses

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        bounds = surface_preview._shared_render_bounds((surface_preview._compile_hybrid_guide(guide),), 0.5)
        invalid = dataclasses.replace(guide, head_guide=dataclasses.replace(guide.head_guide, cranium_center=(float("nan"), 0.0, 0.0)))
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._regional_guide_json("neutral-v0", invalid, bounds)
        invalid = dataclasses.replace(guide, head_guide=dataclasses.replace(guide.head_guide, cranium_center=(bounds[1][0] + 1.0, 0.0, 0.0)))
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._regional_guide_json("neutral-v0", invalid, bounds)


if __name__ == "__main__":
    unittest.main()

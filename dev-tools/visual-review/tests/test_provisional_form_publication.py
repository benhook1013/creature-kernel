from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import common
serve = load_module("provisional_form_serve", "serve.py")
publisher = load_module("provisional_form_publisher", "publish_provisional_form.py")


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


def torso_profile_factors(profile_id: str, owner_role: str) -> tuple[int, int]:
    if profile_id == "neutral-v0":
        return (1_000, 1_000)
    if profile_id == "broad-soft-v0" and owner_role in {"pelvis", "torso"}:
        return (1_200, 1_150)
    if profile_id == "lean-readable-v0":
        return (800, 800)
    if profile_id == "depth-forward-v0" and owner_role == "torso":
        return (1_000, 1_300)
    return (1_000, 1_000)


class ProvisionalFormPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")
        address = {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"}
        self.payload = {
            "format": common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
            "operation": common.PROVISIONAL_FORM_OPERATION,
            "status": "success",
            "stage": common.PROVISIONAL_FORM_STAGE,
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "source": {"document": "fixture", "namespace": "main", "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE},
            "reference_scale": {"parent": {**address, "role": "pelvis"}, "child": {**address, "role": "torso"}, "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"},
            "authored_dimensions": [
                {"owner": {**address, "role": "pelvis"}, "role": "form_extent_x", "value_permille": 1000, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "pelvis"}, "role": "form_extent_y", "value_permille": 900, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "pelvis"}, "role": "form_extent_z", "value_permille": 800, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "torso"}, "role": "form_extent_x", "value_permille": 1000, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "torso"}, "role": "form_extent_y", "value_permille": 1000, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "torso"}, "role": "form_extent_z", "value_permille": 900, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
            ],
            "variants": [],
            "limitations": "Provisional display-only geometry descriptors; no production geometry or Readiness 3.",
        }
        self.payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_binary(self, body: str, name: str = "fake-kernel") -> Path:
        binary = self.directory / name
        binary.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
        binary.chmod(0o755)
        return binary

    def publish_with(self, binary: Path, **kwargs: object) -> Path:
        summary = publisher.publish_provisional_form(self.root, self.input, creature_kernel=binary, **kwargs)
        return Path(summary["session"])

    def capsule_payload(
        self, *, format_name: str = common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT
    ) -> dict[str, object]:
        """Build a small body chain under either versioned capsule contract."""

        def address(role: str, anchors: list[str] | None = None) -> dict[str, object]:
            return {"namespace": "main", "anchors": anchors or [], "kind": "part", "role": role}

        is_dimension_format = format_name in {
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
            common.PROVISIONAL_FORM_V7_FORMAT,
            common.PROVISIONAL_FORM_V8_FORMAT,
        }
        is_v6 = format_name in {
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
            common.PROVISIONAL_FORM_V7_FORMAT,
            common.PROVISIONAL_FORM_V8_FORMAT,
        }
        is_v7 = format_name == common.PROVISIONAL_FORM_V7_FORMAT
        is_v8 = format_name == common.PROVISIONAL_FORM_V8_FORMAT
        is_v9 = format_name == common.PROVISIONAL_FORM_V9_FORMAT

        if is_v9:
            payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V8_FORMAT)
            payload["format"] = common.PROVISIONAL_FORM_V9_FORMAT
            control_provenance = {
                "source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE,
                "document": "fixture",
                "namespace": "main",
            }
            arm_section_values = [
                ("upper-arm-start", "upper_arm", 0.0, (350, 300, 320)),
                ("upper-arm-midpoint", "upper_arm", -0.5, (250, 240, 230)),
                ("elbow", "upper_arm", -1.0, (230, 220, 210)),
                ("forearm-midpoint", "forearm", -0.5, (210, 200, 190)),
                ("forearm-distal", "forearm", -1.0, (180, 170, 160)),
            ]
            for side in ("left", "right"):
                for section_name, owner_role, y, radii in arm_section_values:
                    owner = address(owner_role, [side])
                    section_key = section_name.replace("-", "_")
                    for role_suffix, value in zip(
                        ("lateral_radius", "up_radius", "forward_radius"), radii
                    ):
                        payload["authored_dimensions"].append({
                            "owner": copy.deepcopy(owner),
                            "role": f"form_arm_profile_{section_key}_{role_suffix}",
                            "value_permille": value,
                            "provenance": copy.deepcopy(control_provenance),
                        })
                for section_name, owner_role, y, _radii in arm_section_values:
                    owner = address(owner_role, [side])
                    if not any(
                        frame["owner"] == owner
                        and frame["role"] == common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE
                        for frame in payload["authored_frames"]
                    ):
                        payload["authored_frames"].append({
                            "owner": copy.deepcopy(owner),
                            "role": common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE,
                            "transform": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]},
                            "provenance": copy.deepcopy(control_provenance),
                        })
                    payload["authored_landmarks"].append({
                        "owner": copy.deepcopy(owner),
                        "role": f"form_arm_profile_{section_name.replace('-', '_')}",
                        "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE},
                        "position": [0, y, 0],
                        "provenance": copy.deepcopy(control_provenance),
                    })
            sort_key = lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
                item["owner"]["kind"], item["owner"]["role"], item["role"],
            )
            payload["authored_dimensions"].sort(key=sort_key)
            payload["authored_frames"].sort(key=sort_key)
            payload["authored_landmarks"].sort(key=sort_key)

            def rebind_profile(profile_key: str, section_values: list[tuple[str, str, float, tuple[int, ...]]], axes: tuple[tuple[str, str], ...]) -> None:
                profile = payload[profile_key]
                for section, (section_name, owner_role, _position, _radii) in zip(profile["sections"], section_values):
                    owner = address(owner_role)
                    section_key = section_name.replace("-", "_")
                    frame_role = common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE if profile_key == "authored_torso_profile" else common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE
                    section["frame_index"] = next(
                        index for index, frame in enumerate(payload["authored_frames"])
                        if frame["owner"] == owner and frame["role"] == frame_role
                    )
                    landmark_prefix = "form_torso_profile" if profile_key == "authored_torso_profile" else "form_head_neck_profile"
                    section["landmark_index"] = next(
                        index for index, landmark in enumerate(payload["authored_landmarks"])
                        if landmark["owner"] == owner and landmark["role"] == f"{landmark_prefix}_{section_key}"
                    )
                    section["dimension_indices"] = {
                        axis: next(
                            index for index, dimension in enumerate(payload["authored_dimensions"])
                            if dimension["owner"] == owner
                            and dimension["role"] == f"{landmark_prefix}_{section_key}_{suffix}"
                        )
                        for axis, suffix in axes
                    }

            rebind_profile(
                "authored_torso_profile",
                [
                    (name, role, y, radii)
                    for name, role, y, radii in [
                        ("lower-pelvis", "pelvis", -0.55, (820, 760, 700)),
                        ("upper-pelvis", "pelvis", -0.35, (760, 700, 660)),
                        ("lower-abdomen", "torso", -0.10, (680, 620, 600)),
                        ("waist-abdomen", "torso", 0.05, (640, 580, 560)),
                        ("upper-abdomen", "torso", 0.20, (690, 630, 610)),
                        ("lower-ribcage", "torso", 0.38, (780, 720, 700)),
                        ("upper-ribcage-shoulder", "torso", 0.58, (860, 800, 780)),
                    ]
                ],
                (("lateral", "lateral_radius"), ("anterior", "anterior_radius"), ("posterior", "posterior_radius")),
            )
            rebind_profile(
                "authored_head_neck_profile",
                [
                    (name, role, y, (radii[0], radii[1], radii[2]))
                    for name, role, y, _z, radii in [
                        ("neck-collar", "neck", 0.60, 0.00, (420, 380, 360)),
                        ("neck-upper", "neck", 0.72, 0.00, (400, 360, 340)),
                        ("head-base", "head", 0.82, 0.00, (560, 520, 500)),
                        ("cranium-mid", "head", 0.88, 0.00, (620, 580, 560)),
                        ("cranium-crown", "head", 0.94, 0.00, (600, 560, 540)),
                        ("muzzle-root", "head", 0.94, 0.10, (430, 390, 400)),
                        ("muzzle-mid", "head", 0.94, 0.20, (390, 350, 360)),
                        ("muzzle-tip", "head", 0.94, 0.30, (300, 280, 300)),
                    ]
                ],
                (("lateral", "lateral_radius"), ("up", "up_radius"), ("forward", "forward_radius")),
            )
            payload["authored_arm_profile"] = {
                "format": common.PROVISIONAL_FORM_ARM_PROFILE_FORMAT,
                "provenance": copy.deepcopy(control_provenance),
                "sides": [
                    {
                        "side": side,
                        "sections": [
                            {
                                "name": section_name,
                                "frame_index": next(
                                    index for index, frame in enumerate(payload["authored_frames"])
                                    if frame["owner"] == address(owner_role, [side])
                                    and frame["role"] == common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE
                                ),
                                "landmark_index": next(
                                    index for index, landmark in enumerate(payload["authored_landmarks"])
                                    if landmark["owner"] == address(owner_role, [side])
                                    and landmark["role"] == f"form_arm_profile_{section_name.replace('-', '_')}"
                                ),
                                "dimension_indices": {
                                    axis: next(
                                        index for index, dimension in enumerate(payload["authored_dimensions"])
                                        if dimension["owner"] == address(owner_role, [side])
                                        and dimension["role"] == f"form_arm_profile_{section_name.replace('-', '_')}_{suffix}"
                                    )
                                    for axis, suffix in common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES
                                },
                                "provenance": copy.deepcopy(control_provenance),
                                "section_index": section_index,
                            }
                            for section_index, (section_name, owner_role, _y, _radii) in enumerate(arm_section_values)
                        ],
                    }
                    for side in ("left", "right")
                ],
            }
            arm_factors = {
                "neutral-v0": (1000, 1000, 1000),
                "broad-soft-v0": (1150, 1000, 1150),
                "lean-readable-v0": (800, 1000, 800),
                "depth-forward-v0": (1000, 1000, 1300),
            }
            for variant in payload["variants"]:
                factors = arm_factors[variant["id"]]
                variant["arm_profile"] = {
                    "format": common.PROVISIONAL_FORM_ARM_PROFILE_FORMAT,
                    "source": "authored_arm_profile",
                    "provenance": copy.deepcopy(control_provenance),
                    "sides": [
                        {
                            "side": side,
                            "sections": [
                                {
                                    "source_section_index": section_index,
                                    "name": section_name,
                                    "position": [0, y, 0],
                                    "lateral_radius_permille": radii[0] * factors[0] // 1000,
                                    "up_radius_permille": radii[1] * factors[1] // 1000,
                                    "forward_radius_permille": radii[2] * factors[2] // 1000,
                                    "scaling": {
                                        "lateral_factor_permille": factors[0],
                                        "up_factor_permille": factors[1],
                                        "forward_factor_permille": factors[2],
                                    },
                                    "provenance": copy.deepcopy(control_provenance),
                                }
                                for section_index, (section_name, _owner_role, y, radii) in enumerate(arm_section_values)
                            ],
                        }
                        for side in ("left", "right")
                    ],
                }
            return payload

        if format_name == common.PROVISIONAL_FORM_V10_FORMAT:
            payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V9_FORMAT)
            payload["format"] = common.PROVISIONAL_FORM_V10_FORMAT
            control_provenance = {
                "source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE,
                "document": "fixture",
                "namespace": "main",
            }
            leg_section_values = [
                ("thigh-start", "thigh", 0.0, (320, 280, 300)),
                ("thigh-midpoint", "thigh", -0.5, (300, 260, 280)),
                ("knee", "thigh", -1.0, (240, 210, 225)),
                ("shin-midpoint", "shin", -0.5, (225, 195, 210)),
                ("hock-endpoint", "shin", -1.0, (185, 165, 175)),
            ]
            for side in ("left", "right"):
                for section_name, owner_role, _y, radii in leg_section_values:
                    owner = address(owner_role, [side])
                    section_key = section_name.replace("-", "_")
                    for role_suffix, value in zip(
                        ("lateral_radius", "up_radius", "forward_radius"), radii
                    ):
                        payload["authored_dimensions"].append({
                            "owner": copy.deepcopy(owner),
                            "role": f"form_leg_profile_{section_key}_{role_suffix}",
                            "value_permille": value,
                            "provenance": copy.deepcopy(control_provenance),
                        })
                for _section_name, owner_role, _y, _radii in leg_section_values:
                    owner = address(owner_role, [side])
                    if not any(
                        frame["owner"] == owner
                        and frame["role"] == common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
                        for frame in payload["authored_frames"]
                    ):
                        payload["authored_frames"].append({
                            "owner": copy.deepcopy(owner),
                            "role": common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE,
                            "transform": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]},
                            "provenance": copy.deepcopy(control_provenance),
                        })
                for section_name, owner_role, y, _radii in leg_section_values:
                    owner = address(owner_role, [side])
                    payload["authored_landmarks"].append({
                        "owner": copy.deepcopy(owner),
                        "role": f"form_leg_profile_{section_name.replace('-', '_')}",
                        "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE},
                        "position": [0, y, 0],
                        "provenance": copy.deepcopy(control_provenance),
                    })
            sort_key = lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
                item["owner"]["kind"], item["owner"]["role"], item["role"],
            )
            payload["authored_dimensions"].sort(key=sort_key)
            payload["authored_frames"].sort(key=sort_key)
            payload["authored_landmarks"].sort(key=sort_key)

            def index_of(items: list[dict[str, object]], owner: dict[str, object], role: str) -> int:
                return next(
                    index for index, item in enumerate(items)
                    if item["owner"] == owner and item["role"] == role
                )

            def rebind_profile(
                profile_key: str,
                section_values: list[tuple[str, str, float, tuple[int, ...]]],
                prefix: str,
                frame_role: str,
                axes: tuple[tuple[str, str], ...],
            ) -> None:
                profile = payload[profile_key]
                for section, (section_name, owner_role, _position, _radii) in zip(profile["sections"], section_values):
                    owner = address(owner_role)
                    section_key = section_name.replace("-", "_")
                    section["frame_index"] = index_of(payload["authored_frames"], owner, frame_role)
                    section["landmark_index"] = index_of(
                        payload["authored_landmarks"], owner, f"{prefix}_{section_key}"
                    )
                    section["dimension_indices"] = {
                        axis: index_of(
                            payload["authored_dimensions"], owner, f"{prefix}_{section_key}_{suffix}"
                        )
                        for axis, suffix in axes
                    }

            torso_values = [
                ("lower-pelvis", "pelvis", -0.55, (820, 760, 700)),
                ("upper-pelvis", "pelvis", -0.35, (760, 700, 660)),
                ("lower-abdomen", "torso", -0.10, (680, 620, 600)),
                ("waist-abdomen", "torso", 0.05, (640, 580, 560)),
                ("upper-abdomen", "torso", 0.20, (690, 630, 610)),
                ("lower-ribcage", "torso", 0.38, (780, 720, 700)),
                ("upper-ribcage-shoulder", "torso", 0.58, (860, 800, 780)),
            ]
            head_values = [
                ("neck-collar", "neck", 0.60, (420, 380, 360)),
                ("neck-upper", "neck", 0.72, (400, 360, 340)),
                ("head-base", "head", 0.82, (560, 520, 500)),
                ("cranium-mid", "head", 0.88, (620, 580, 560)),
                ("cranium-crown", "head", 0.94, (600, 560, 540)),
                ("muzzle-root", "head", 0.94, (430, 390, 400)),
                ("muzzle-mid", "head", 0.94, (390, 350, 360)),
                ("muzzle-tip", "head", 0.94, (300, 280, 300)),
            ]
            rebind_profile(
                "authored_torso_profile", torso_values, "form_torso_profile",
                common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE,
                (("lateral", "lateral_radius"), ("anterior", "anterior_radius"), ("posterior", "posterior_radius")),
            )
            rebind_profile(
                "authored_head_neck_profile", head_values, "form_head_neck_profile",
                common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
                (("lateral", "lateral_radius"), ("up", "up_radius"), ("forward", "forward_radius")),
            )
            for side in payload["authored_arm_profile"]["sides"]:
                for section, (section_name, owner_role, _y, _radii) in zip(side["sections"], [
                    ("upper-arm-start", "upper_arm", 0.0, (350, 300, 320)),
                    ("upper-arm-midpoint", "upper_arm", -0.5, (250, 240, 230)),
                    ("elbow", "upper_arm", -1.0, (230, 220, 210)),
                    ("forearm-midpoint", "forearm", -0.5, (210, 200, 190)),
                    ("forearm-distal", "forearm", -1.0, (180, 170, 160)),
                ]):
                    owner = address(owner_role, [side["side"]])
                    section_key = section_name.replace("-", "_")
                    section["frame_index"] = index_of(payload["authored_frames"], owner, common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE)
                    section["landmark_index"] = index_of(payload["authored_landmarks"], owner, f"form_arm_profile_{section_key}")
                    section["dimension_indices"] = {
                        axis: index_of(payload["authored_dimensions"], owner, f"form_arm_profile_{section_key}_{suffix}")
                        for axis, suffix in common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES
                    }

            payload["authored_leg_profile"] = {
                "format": common.PROVISIONAL_FORM_LEG_PROFILE_FORMAT,
                "provenance": copy.deepcopy(control_provenance),
                "sides": [
                    {
                        "side": side,
                        "sections": [
                            {
                                "name": section_name,
                                "frame_index": index_of(payload["authored_frames"], address(owner_role, [side]), common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE),
                                "landmark_index": index_of(payload["authored_landmarks"], address(owner_role, [side]), f"form_leg_profile_{section_name.replace('-', '_')}"),
                                "dimension_indices": {
                                    axis: index_of(payload["authored_dimensions"], address(owner_role, [side]), f"form_leg_profile_{section_name.replace('-', '_')}_{suffix}")
                                    for axis, suffix in common.PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES
                                },
                                "provenance": copy.deepcopy(control_provenance),
                                "section_index": section_index,
                            }
                            for section_index, (section_name, owner_role, _y, _radii) in enumerate(leg_section_values)
                        ],
                    }
                    for side in ("left", "right")
                ],
            }
            leg_factors = {
                "neutral-v0": (1000, 1000, 1000),
                "broad-soft-v0": (1150, 1000, 1150),
                "lean-readable-v0": (800, 1000, 800),
                "depth-forward-v0": (1000, 1000, 1300),
            }
            for variant in payload["variants"]:
                factors = leg_factors[variant["id"]]
                variant["leg_profile"] = {
                    "format": common.PROVISIONAL_FORM_LEG_PROFILE_FORMAT,
                    "source": "authored_leg_profile",
                    "provenance": copy.deepcopy(control_provenance),
                    "sides": [
                        {
                            "side": side,
                            "sections": [
                                {
                                    "source_section_index": section_index,
                                    "name": section_name,
                                    "position": [0, y, 0],
                                    "lateral_radius_permille": radii[0] * factors[0] // 1000,
                                    "up_radius_permille": radii[1] * factors[1] // 1000,
                                    "forward_radius_permille": radii[2] * factors[2] // 1000,
                                    "scaling": {
                                        "lateral_factor_permille": factors[0],
                                        "up_factor_permille": factors[1],
                                        "forward_factor_permille": factors[2],
                                    },
                                    "provenance": copy.deepcopy(control_provenance),
                                }
                                for section_index, (section_name, _owner_role, y, radii) in enumerate(leg_section_values)
                            ],
                        }
                        for side in ("left", "right")
                    ],
                }
            return payload

        if format_name == common.PROVISIONAL_FORM_V11_FORMAT:
            payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V10_FORMAT)
            payload["format"] = common.PROVISIONAL_FORM_V11_FORMAT
            control_provenance = {
                "source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE,
                "document": "fixture",
                "namespace": "main",
            }
            foot_values = [
                ("pad", -0.2, 0.36, (320, 150, 300)),
                ("toe", -0.2, 0.72, (260, 150, 240)),
            ]

            for side in ("left", "right"):
                owner = address("foot", [side])
                for section_name, _y, _z, radii in foot_values:
                    for role_suffix, value in zip(
                        ("lateral_radius", "up_radius", "forward_radius"), radii
                    ):
                        payload["authored_dimensions"].append({
                            "owner": copy.deepcopy(owner),
                            "role": "form_foot_profile_" + section_name + "_" + role_suffix,
                            "value_permille": value,
                            "provenance": copy.deepcopy(control_provenance),
                        })
                payload["authored_frames"].append({
                    "owner": copy.deepcopy(owner),
                    "role": common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE,
                    "transform": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]},
                    "provenance": copy.deepcopy(control_provenance),
                })
                for section_name, y, z, _radii in foot_values:
                    payload["authored_landmarks"].append({
                        "owner": copy.deepcopy(owner),
                        "role": "form_foot_profile_" + section_name,
                        "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE},
                        "position": [0, y, z],
                        "provenance": copy.deepcopy(control_provenance),
                    })

            sort_key = lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
                item["owner"]["kind"], item["owner"]["role"], item["role"],
            )
            for key in ("authored_dimensions", "authored_frames", "authored_landmarks"):
                payload[key].sort(key=sort_key)

            def index_of(items: list[dict[str, object]], owner: dict[str, object], role: str) -> int:
                return next(
                    index for index, item in enumerate(items)
                    if item["owner"] == owner and item["role"] == role
                )

            def rebind(
                profile: dict[str, object],
                side: str | None,
                section_names: tuple[str, ...],
                owner_roles: tuple[str, ...],
                prefix: str,
                frame_role: str,
                axes: tuple[tuple[str, str], ...],
            ) -> None:
                for section, section_name, owner_role in zip(profile["sections"], section_names, owner_roles):
                    owner = address(owner_role, [] if side is None else [side])
                    section_key = section_name.replace("-", "_")
                    section["frame_index"] = index_of(payload["authored_frames"], owner, frame_role)
                    section["landmark_index"] = index_of(payload["authored_landmarks"], owner, prefix + "_" + section_key)
                    section["dimension_indices"] = {
                        axis: index_of(payload["authored_dimensions"], owner, prefix + "_" + section_key + "_" + suffix)
                        for axis, suffix in axes
                    }

            rebind(
                payload["authored_torso_profile"], None,
                common.PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES,
                common.PROVISIONAL_FORM_TORSO_PROFILE_OWNER_ROLES,
                "form_torso_profile", common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE,
                common.PROVISIONAL_FORM_TORSO_PROFILE_RADIUS_AXES,
            )
            rebind(
                payload["authored_head_neck_profile"], None,
                common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES,
                common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES,
                "form_head_neck_profile", common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
                common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES,
            )
            for side in ("left", "right"):
                rebind(
                    next(item for item in payload["authored_arm_profile"]["sides"] if item["side"] == side),
                    side, common.PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES,
                    common.PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES,
                    "form_arm_profile", common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE,
                    common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES,
                )
                rebind(
                    next(item for item in payload["authored_leg_profile"]["sides"] if item["side"] == side),
                    side, common.PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES,
                    common.PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES,
                    "form_leg_profile", common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE,
                    common.PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES,
                )

            foot_sides = []
            for side_index, side in enumerate(("left", "right")):
                owner = address("foot", [side])
                foot_sides.append({
                    "side": side,
                    "hock_binding": {
                        "source_profile": "authored_leg_profile",
                        "side_index": side_index,
                        "section_index": common.PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX,
                    },
                    "sections": [
                        {
                            "name": section_name,
                            "frame_index": index_of(payload["authored_frames"], owner, common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE),
                            "landmark_index": index_of(payload["authored_landmarks"], owner, "form_foot_profile_" + section_name),
                            "dimension_indices": {
                                axis: index_of(payload["authored_dimensions"], owner, "form_foot_profile_" + section_name + "_" + suffix)
                                for axis, suffix in common.PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES
                            },
                            "provenance": copy.deepcopy(control_provenance),
                            "section_index": section_index,
                        }
                        for section_index, (section_name, _y, _z, _radii) in enumerate(foot_values)
                    ],
                })
            payload["authored_foot_profile"] = {
                "format": common.PROVISIONAL_FORM_FOOT_PROFILE_FORMAT,
                "provenance": copy.deepcopy(control_provenance),
                "sides": foot_sides,
            }

            factors_by_variant = {
                "neutral-v0": (1000, 1000, 1000),
                "broad-soft-v0": (1150, 1000, 1150),
                "lean-readable-v0": (800, 1000, 800),
                "depth-forward-v0": (1000, 1000, 1300),
            }
            for variant in payload["variants"]:
                factors = factors_by_variant[variant["id"]]
                variant["foot_profile"] = {
                    "format": common.PROVISIONAL_FORM_FOOT_PROFILE_FORMAT,
                    "source": "authored_foot_profile",
                    "provenance": copy.deepcopy(control_provenance),
                    "sides": [
                        {
                            "side": side,
                            "hock_binding": copy.deepcopy(foot_sides[side_index]["hock_binding"]),
                            "sections": [
                                {
                                    "source_section_index": section_index,
                                    "name": section_name,
                                    "position": [0, y, z],
                                    "lateral_radius_permille": radii[0] * factors[0] // 1000,
                                    "up_radius_permille": radii[1] * factors[1] // 1000,
                                    "forward_radius_permille": radii[2] * factors[2] // 1000,
                                    "scaling": {
                                        "lateral_factor_permille": factors[0],
                                        "up_factor_permille": factors[1],
                                        "forward_factor_permille": factors[2],
                                    },
                                    "provenance": copy.deepcopy(control_provenance),
                                }
                                for section_index, (section_name, y, z, radii) in enumerate(foot_values)
                            ],
                        }
                        for side_index, side in enumerate(("left", "right"))
                    ],
                }
            return payload

        def descriptor(
            role: str,
            point: list[int],
            parent: dict[str, object] | None,
            shape: dict[str, object],
            anchors: list[str] | None = None,
        ) -> dict[str, object]:
            dimension_roles = {
                "ellipsoid": ["form_extent_x", "form_extent_y", "form_extent_z"],
                "capsule": (
                    ["form_radius", "form_shoulder_depth_radius"]
                    if is_v6 and role == "upper_arm"
                    else ["form_radius"]
                ),
                "tapered-segment": ["form_start_radius", "form_end_radius"],
            }[shape["name"]]
            owner = address(role, anchors)
            return {
                "descriptor_kind": "display-only-form-descriptor",
                "address": owner,
                "parent": parent,
                "placement_source": "authored-root" if parent is None else "authored-containment",
                "reference_point": point,
                "dimension_roles": dimension_roles,
                "profile_id": "neutral-v0",
                "source": common.PROVISIONAL_FORM_PROVENANCE,
                "provenance": {
                    "source": common.PROVISIONAL_FORM_PROVENANCE,
                    "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
                    "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS,
                },
                "shape": shape,
            }

        pelvis = address("pelvis")
        torso = address("torso")
        neck = address("neck")
        head = address("head")

        def part(role: str, side: str | None = None) -> dict[str, object]:
            return address(role, [] if side is None else [side])

        neck_shape = (
            {"name": "capsule", "from": [0, 2, 0], "to": [0, 3, 0], "radius_permille": 500}
            if format_name in {
                common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
                common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
                common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
                common.PROVISIONAL_FORM_V7_FORMAT,
                common.PROVISIONAL_FORM_V8_FORMAT,
            }
            else {"name": "ellipsoid", "center": [0, 2, 0], "axis_extents_permille": [650, 600, 600]}
        )
        descriptors = [
            descriptor("pelvis", [0, 0, 0], None, {"name": "ellipsoid", "center": [0, 0, 0], "axis_extents_permille": [1000, 900, 800]}),
            descriptor("torso", [0, 1, 0], pelvis, {"name": "ellipsoid", "center": [0, 1, 0], "axis_extents_permille": [1000, 1000, 900]}),
            descriptor("neck", [0, 2, 0], torso, neck_shape),
            descriptor("head", [0, 3, 0], neck, {"name": "ellipsoid", "center": [0, 3, 0], "axis_extents_permille": [1000, 1000, 900]}),
            descriptor("upper_arm", [-1, 2, 0], torso, {"name": "capsule", "from": [-1, 2, 0], "to": [-2, 2, 0], "radius_permille": 200}, ["left"]),
            descriptor("forearm", [-2, 2, 0], part("upper_arm", "left"), {"name": "capsule", "from": [-2, 2, 0], "to": [-3, 2, 0], "radius_permille": 180}, ["left"]),
            descriptor("hand", [-3, 2, 0], part("forearm", "left"), {"name": "ellipsoid", "center": [-3, 2, 0], "axis_extents_permille": [450, 400, 350]}, ["left"]),
            descriptor("upper_arm", [1, 2, 0], torso, {"name": "capsule", "from": [1, 2, 0], "to": [2, 2, 0], "radius_permille": 200}, ["right"]),
            descriptor("forearm", [2, 2, 0], part("upper_arm", "right"), {"name": "capsule", "from": [2, 2, 0], "to": [3, 2, 0], "radius_permille": 180}, ["right"]),
            descriptor("hand", [3, 2, 0], part("forearm", "right"), {"name": "ellipsoid", "center": [3, 2, 0], "axis_extents_permille": [450, 400, 350]}, ["right"]),
            descriptor("thigh", [-1, 0, 0], pelvis, {"name": "capsule", "from": [-1, 0, 0], "to": [-1, -1, 0], "radius_permille": 240}, ["left"]),
            descriptor("shin", [-1, -1, 0], part("thigh", "left"), {"name": "capsule", "from": [-1, -1, 0], "to": [-1, -2, 0], "radius_permille": 180}, ["left"]),
            descriptor("foot", [-1, -2, 0], part("shin", "left"), {"name": "ellipsoid", "center": [-1, -2, 0], "axis_extents_permille": [500, 350, 600]}, ["left"]),
            descriptor("thigh", [1, 0, 0], pelvis, {"name": "capsule", "from": [1, 0, 0], "to": [1, -1, 0], "radius_permille": 240}, ["right"]),
            descriptor("shin", [1, -1, 0], part("thigh", "right"), {"name": "capsule", "from": [1, -1, 0], "to": [1, -2, 0], "radius_permille": 180}, ["right"]),
            descriptor("foot", [1, -2, 0], part("shin", "right"), {"name": "ellipsoid", "center": [1, -2, 0], "axis_extents_permille": [500, 350, 600]}, ["right"]),
            descriptor("tail_root", [0, -1, 0], pelvis, {"name": "tapered-segment", "from": [0, 0, 0], "to": [0, -1, 0], "start_radius_permille": 220, "end_radius_permille": 180}, ["tail"]),
            descriptor("tail_tip", [0, -2, 0], part("tail_root", "tail"), {"name": "tapered-segment", "from": [0, -1, 0], "to": [0, -2, 0], "start_radius_permille": 180, "end_radius_permille": 120}, ["tail"]),
        ]
        descriptors.sort(key=lambda item: (
            item["address"]["namespace"], tuple(item["address"]["anchors"]),
            item["address"]["kind"], item["address"]["role"],
        ))
        if format_name == common.PROVISIONAL_FORM_LEGACY_FORMAT:
            for item in descriptors:
                if item["shape"]["name"] != "capsule" or item["parent"] is None:
                    continue
                parent = next(
                    candidate
                    for candidate in descriptors
                    if candidate["address"] == item["parent"]
                )
                item["shape"]["from"] = copy.deepcopy(parent["reference_point"])
                item["shape"]["to"] = copy.deepcopy(item["reference_point"])
        payload = copy.deepcopy(self.payload)
        payload["format"] = format_name
        payload["authored_dimensions"] = []
        for item in descriptors:
            shape = item["shape"]
            if shape["name"] == "ellipsoid":
                values = shape["axis_extents_permille"]
            elif shape["name"] == "capsule":
                values = [shape["radius_permille"]]
                if is_v6 and item["address"]["role"] == "upper_arm":
                    values.append(350)
            else:
                values = [shape["start_radius_permille"], shape["end_radius_permille"]]
            for role, value in zip(item["dimension_roles"], values):
                if role == "form_shoulder_depth_radius":
                    value = 350
                payload["authored_dimensions"].append({
                    "owner": copy.deepcopy(item["address"]),
                    "role": role,
                    "value_permille": value,
                    "provenance": {
                        "source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE,
                        "document": "fixture",
                        "namespace": "main",
                    },
                })
        payload["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        candidates = []
        for item in descriptors:
            parent = item["parent"]
            if parent is None:
                continue
            parent_item = next(candidate for candidate in descriptors if candidate["address"] == parent)
            delta = [item["reference_point"][index] - parent_item["reference_point"][index] for index in range(3)]
            squared = sum(component * component for component in delta)
            if squared:
                candidates.append((squared, item["address"], parent, delta))
        selected = min(candidates, key=lambda candidate: (candidate[0], (
            candidate[1]["namespace"], tuple(candidate[1]["anchors"]), candidate[1]["kind"], candidate[1]["role"]
        )))
        payload["reference_scale"] = {
            "parent": selected[2],
            "child": selected[1],
            "axis_delta": selected[3],
            "squared_length": selected[0],
            "source": "exact-containment-edge",
        }
        payload["variants"] = []
        for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS:
            variant_descriptors = copy.deepcopy(descriptors)
            for item in variant_descriptors:
                item["profile_id"] = variant_id
                if is_dimension_format:
                    apply_fixed_display_factors(item, variant_id)
            payload["variants"].append({
                "id": variant_id,
                "profile_id": variant_id,
                "provenance": {
                    "source": common.PROVISIONAL_FORM_PROVENANCE,
                    "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
                    "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS,
                },
                "descriptors": variant_descriptors,
            })
        if is_v7 or is_v8:
            torso_section_values = [
                ("lower-pelvis", "pelvis", -0.55, (820, 760, 700)),
                ("upper-pelvis", "pelvis", -0.35, (760, 700, 660)),
                ("lower-abdomen", "torso", -0.10, (680, 620, 600)),
                ("waist-abdomen", "torso", 0.05, (640, 580, 560)),
                ("upper-abdomen", "torso", 0.20, (690, 630, 610)),
                ("lower-ribcage", "torso", 0.38, (780, 720, 700)),
                ("upper-ribcage-shoulder", "torso", 0.58, (860, 800, 780)),
            ]
            control_provenance = {
                "source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE,
                "document": "fixture",
                "namespace": "main",
            }
            for section_name, owner_role, y, radii in torso_section_values:
                owner = address(owner_role)
                section_key = section_name.replace("-", "_")
                for role_suffix, value in zip(
                    ("lateral_radius", "anterior_radius", "posterior_radius"),
                    radii,
                ):
                    payload["authored_dimensions"].append({
                        "owner": copy.deepcopy(owner),
                        "role": f"form_torso_profile_{section_key}_{role_suffix}",
                        "value_permille": value,
                        "provenance": {
                            "source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE,
                            "document": "fixture",
                            "namespace": "main",
                        },
                    })
            payload["authored_dimensions"].sort(key=lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
                item["owner"]["kind"], item["owner"]["role"], item["role"],
            ))

        if is_v6:
            controls = []
            for side, x in (("left", -0.1), ("right", 0.1)):
                owner = address("upper_arm", [side])
                controls.extend([
                    {
                        "owner": copy.deepcopy(owner),
                        "role": "form_shoulder_peak",
                        "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE},
                        "position": [x, 0.15, 0],
                        "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": "fixture", "namespace": "main"},
                    },
                    {
                        "owner": copy.deepcopy(owner),
                        "role": "form_axilla",
                        "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE},
                        "position": [x, -0.3, 0],
                        "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": "fixture", "namespace": "main"},
                    },
                ])
            payload["authored_landmarks"] = sorted(controls, key=lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
            ))
            payload["authored_frames"] = sorted([
                {
                    "owner": {"namespace": "main", "anchors": [side], "kind": "part", "role": "upper_arm"},
                    "role": common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE,
                    "transform": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]},
                    "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": "fixture", "namespace": "main"},
                }
                for side in ("left", "right")
            ], key=lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
            ))
            if is_v7 or is_v8:
                torso_frame_owners = set()
                for section_name, owner_role, y, _radii in torso_section_values:
                    owner = address(owner_role)
                    if owner_role not in torso_frame_owners:
                        payload["authored_frames"].append({
                            "owner": copy.deepcopy(owner),
                            "role": common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE,
                            "transform": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]},
                            "provenance": copy.deepcopy(control_provenance),
                        })
                        torso_frame_owners.add(owner_role)
                    payload["authored_landmarks"].append({
                        "owner": copy.deepcopy(owner),
                        "role": f"form_torso_profile_{section_name.replace('-', '_')}",
                        "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE},
                        "position": [0, y, 0],
                        "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": "fixture", "namespace": "main"},
                    })
                payload["authored_frames"].sort(key=lambda item: (
                    item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
                ))
                payload["authored_landmarks"].sort(key=lambda item: (
                    item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
                ))
                payload["authored_torso_profile"] = {
                    "format": common.PROVISIONAL_FORM_TORSO_PROFILE_FORMAT,
                    "provenance": copy.deepcopy(control_provenance),
                    "sections": [
                        {
                            "name": section_name,
                            "frame_index": next(
                                index
                                for index, frame in enumerate(payload["authored_frames"])
                                if frame["owner"] == address(owner_role)
                                and frame["role"] == common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE
                            ),
                            "landmark_index": next(
                                index
                                for index, landmark in enumerate(payload["authored_landmarks"])
                                if landmark["owner"] == address(owner_role)
                                and landmark["role"]
                                == f"form_torso_profile_{section_name.replace('-', '_')}"
                            ),
                            "dimension_indices": {
                                axis: next(
                                    index
                                    for index, dimension in enumerate(payload["authored_dimensions"])
                                    if dimension["owner"] == address(owner_role)
                                    and dimension["role"]
                                    == f"form_torso_profile_{section_name.replace('-', '_')}_{role_suffix}"
                                )
                                for axis, role_suffix in (
                                    ("lateral", "lateral_radius"),
                                    ("anterior", "anterior_radius"),
                                    ("posterior", "posterior_radius"),
                                )
                            },
                            "provenance": copy.deepcopy(control_provenance),
                            "section_index": section_index,
                        }
                        for section_index, (
                            section_name,
                            owner_role,
                            _y,
                            _radii,
                        ) in enumerate(torso_section_values)
                    ],
                }
                for variant in payload["variants"]:
                    variant_sections = []
                    for section_index, (
                        section_name,
                        owner_role,
                        y,
                        radii,
                    ) in enumerate(torso_section_values):
                        lateral_factor, depth_factor = torso_profile_factors(
                            variant["id"], owner_role
                        )
                        variant_sections.append({
                            "source_section_index": section_index,
                            "name": section_name,
                            "position": [0, y, 0],
                            "lateral_radius_permille": radii[0] * lateral_factor // 1_000,
                            "anterior_radius_permille": radii[1] * depth_factor // 1_000,
                            "posterior_radius_permille": radii[2] * depth_factor // 1_000,
                            "scaling": {
                                "lateral_factor_permille": lateral_factor,
                                "anterior_factor_permille": depth_factor,
                                "posterior_factor_permille": depth_factor,
                            },
                            "provenance": copy.deepcopy(control_provenance),
                        })
                    variant["torso_profile"] = {
                        "format": common.PROVISIONAL_FORM_TORSO_PROFILE_FORMAT,
                        "source": "authored_torso_profile",
                        "provenance": copy.deepcopy(control_provenance),
                        "sections": variant_sections,
                    }
        if is_v8:
            head_neck_section_values = [
                ("neck-collar", "neck", 0.60, 0.00, (420, 380, 360)),
                ("neck-upper", "neck", 0.72, 0.00, (400, 360, 340)),
                ("head-base", "head", 0.82, 0.00, (560, 520, 500)),
                ("cranium-mid", "head", 0.88, 0.00, (620, 580, 560)),
                ("cranium-crown", "head", 0.94, 0.00, (600, 560, 540)),
                ("muzzle-root", "head", 0.94, 0.10, (430, 390, 400)),
                ("muzzle-mid", "head", 0.94, 0.20, (390, 350, 360)),
                ("muzzle-tip", "head", 0.94, 0.30, (300, 280, 300)),
            ]
            for section_name, owner_role, y, z, radii in head_neck_section_values:
                owner = address(owner_role)
                section_key = section_name.replace("-", "_")
                for role_suffix, value in zip(
                    ("lateral_radius", "up_radius", "forward_radius"), radii
                ):
                    payload["authored_dimensions"].append({
                        "owner": copy.deepcopy(owner),
                        "role": f"form_head_neck_profile_{section_key}_{role_suffix}",
                        "value_permille": value,
                        "provenance": copy.deepcopy(control_provenance),
                    })
            payload["authored_dimensions"].sort(key=lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
                item["owner"]["kind"], item["owner"]["role"], item["role"],
            ))
            head_neck_frame_owners = set()
            for section_name, owner_role, _y, _z, _radii in head_neck_section_values:
                owner = address(owner_role)
                if owner_role not in head_neck_frame_owners:
                    payload["authored_frames"].append({
                        "owner": copy.deepcopy(owner),
                        "role": common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
                        "transform": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]},
                        "provenance": copy.deepcopy(control_provenance),
                    })
                    head_neck_frame_owners.add(owner_role)
                payload["authored_landmarks"].append({
                    "owner": copy.deepcopy(owner),
                    "role": f"form_head_neck_profile_{section_name.replace('-', '_')}",
                    "frame": {"owner": copy.deepcopy(owner), "role": common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE},
                    "position": [0, _y, _z],
                    "provenance": copy.deepcopy(control_provenance),
                })
            payload["authored_frames"].sort(key=lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
            ))
            payload["authored_landmarks"].sort(key=lambda item: (
                item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
            ))
            payload["authored_head_neck_profile"] = {
                "format": common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT,
                "provenance": copy.deepcopy(control_provenance),
                "sections": [
                    {
                        "name": section_name,
                        "frame_index": next(
                            index for index, frame in enumerate(payload["authored_frames"])
                            if frame["owner"] == address(owner_role)
                            and frame["role"] == common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE
                        ),
                        "landmark_index": next(
                            index for index, landmark in enumerate(payload["authored_landmarks"])
                            if landmark["owner"] == address(owner_role)
                            and landmark["role"] == f"form_head_neck_profile_{section_name.replace('-', '_')}"
                        ),
                        "dimension_indices": {
                            axis: next(
                                index for index, dimension in enumerate(payload["authored_dimensions"])
                                if dimension["owner"] == address(owner_role)
                                and dimension["role"] == f"form_head_neck_profile_{section_name.replace('-', '_')}_{role_suffix}"
                            )
                            for axis, role_suffix in (
                                ("lateral", "lateral_radius"),
                                ("up", "up_radius"),
                                ("forward", "forward_radius"),
                            )
                        },
                        "provenance": copy.deepcopy(control_provenance),
                        "section_index": section_index,
                    }
                    for section_index, (section_name, owner_role, _y, _z, _radii)
                    in enumerate(head_neck_section_values)
                ],
                "connections": [
                    {
                        "name": name,
                        "from_section_index": from_index,
                        "to_section_index": to_index,
                        "route": route,
                    }
                    for name, from_index, to_index, route
                    in common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS
                ],
            }
            for variant in payload["variants"]:
                variant_sections = []
                for section_index, (section_name, owner_role, y, z, radii) in enumerate(head_neck_section_values):
                    factors = {
                        "lateral": 1000,
                        "up": 1000,
                        "forward": 1000,
                    }
                    if owner_role == "head":
                        if variant["id"] == "broad-soft-v0": factors = {"lateral": 1200, "up": 1000, "forward": 1150}
                        elif variant["id"] == "lean-readable-v0": factors = {"lateral": 800, "up": 1000, "forward": 800}
                        elif variant["id"] == "depth-forward-v0": factors = {"lateral": 1000, "up": 1000, "forward": 1300}
                    elif variant["id"] == "broad-soft-v0": factors = {"lateral": 1150, "up": 1150, "forward": 1150}
                    elif variant["id"] == "lean-readable-v0": factors = {"lateral": 800, "up": 800, "forward": 800}
                    variant_sections.append({
                        "source_section_index": section_index,
                        "name": section_name,
                        "position": [0, y, z],
                        "lateral_radius_permille": radii[0] * factors["lateral"] // 1000,
                        "up_radius_permille": radii[1] * factors["up"] // 1000,
                        "forward_radius_permille": radii[2] * factors["forward"] // 1000,
                        "scaling": {
                            "lateral_factor_permille": factors["lateral"],
                            "up_factor_permille": factors["up"],
                            "forward_factor_permille": factors["forward"],
                        },
                        "provenance": copy.deepcopy(control_provenance),
                    })
                variant["head_neck_profile"] = {
                    "format": common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT,
                    "source": "authored_head_neck_profile",
                    "provenance": copy.deepcopy(control_provenance),
                    "sections": variant_sections,
                    "connections": copy.deepcopy(payload["authored_head_neck_profile"]["connections"]),
                }
            # Head/neck controls are added after the torso section values above;
            # rebuild every torso binding against the final sorted inventories so
            # v8 indices refer to the emitted arrays rather than the intermediate
            # v7-shaped arrays.
            for section in payload["authored_torso_profile"]["sections"]:
                owner = address(
                    "pelvis" if section["name"] in {"lower-pelvis", "upper-pelvis"} else "torso"
                )
                section_key = section["name"].replace("-", "_")
                section["frame_index"] = next(
                    index for index, frame in enumerate(payload["authored_frames"])
                    if frame["owner"] == owner
                    and frame["role"] == common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE
                )
                section["landmark_index"] = next(
                    index for index, landmark in enumerate(payload["authored_landmarks"])
                    if landmark["owner"] == owner
                    and landmark["role"] == f"form_torso_profile_{section_key}"
                )
                section["dimension_indices"] = {
                    axis: next(
                        index for index, dimension in enumerate(payload["authored_dimensions"])
                        if dimension["owner"] == owner
                        and dimension["role"] == f"form_torso_profile_{section_key}_{role_suffix}"
                    )
                    for axis, role_suffix in (
                        ("lateral", "lateral_radius"),
                        ("anterior", "anterior_radius"),
                        ("posterior", "posterior_radius"),
                    )
                }
        if not is_v6:
            payload.pop("authored_landmarks", None)
            payload.pop("authored_frames", None)
        if not (is_v7 or is_v8):
            payload.pop("authored_torso_profile", None)
        if not is_v8:
            payload.pop("authored_head_neck_profile", None)
        if not is_dimension_format:
            payload.pop("authored_dimensions")
            for variant in payload["variants"]:
                variant["provenance"].pop("shape_basis")
                for item in variant["descriptors"]:
                    item.pop("dimension_roles")
                    item["provenance"].pop("shape_basis")
        return payload

    def test_success_publishes_distinct_immutable_form_session_and_route(self) -> None:
        self.assertEqual(self.payload["format"], common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT)
        binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n")
        session = self.publish_with(binary, review_id="form-review", title="Filled form")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["kind"], "provisional-form")
        self.assertEqual(review["provisional_form"], self.payload)
        self.assertEqual(list((session / "assets").iterdir()), [])
        self.payload["variants"][0]["descriptors"][0]["shape"]["center"][0] = 9
        stored_descriptors = json.loads((session / "review.json").read_text())["provisional_form"]["variants"][0]["descriptors"]
        stored_pelvis = next(
            descriptor for descriptor in stored_descriptors
            if descriptor["address"]["role"] == "pelvis" and not descriptor["address"]["anchors"]
        )
        self.assertEqual(stored_pelvis["shape"]["center"], [0, 0, 0])
        server = serve.create_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/reviews/form-review") as response:
                body = json.load(response)
            self.assertEqual(body["review"]["kind"], "provisional-form")
            self.assertEqual(len(body["review"]["provisional_form"]["variants"]), 4)
        finally:
            server.shutdown(); thread.join(); server.server_close()

    def test_v6_rejects_tampered_authored_dimension_with_unchanged_descriptors(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["authored_dimensions"][0]["value_permille"] += 1
        with self.assertRaisesRegex(
            common.ValidationError,
            "shape numeric controls do not match source-authored dimensions",
        ):
            common._validate_provisional_form_envelope(
                payload, "tampered authored dimension fixture"
            )

    def test_v6_rejects_tampered_non_neutral_variant_shape_control(self) -> None:
        payload = copy.deepcopy(self.payload)
        torso = next(
            descriptor
            for descriptor in payload["variants"][1]["descriptors"]
            if descriptor["address"]["role"] == "torso"
        )
        torso["shape"]["axis_extents_permille"][0] += 1
        with self.assertRaisesRegex(
            common.ValidationError,
            "shape numeric controls do not match source-authored dimensions",
        ):
            common._validate_provisional_form_envelope(
                payload, "tampered non-neutral variant fixture"
            )

    def test_v6_rejects_unconsumed_authored_dimension(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["authored_dimensions"].append({
            "owner": copy.deepcopy(payload["authored_dimensions"][0]["owner"]),
            "role": "form_unconsumed",
            "value_permille": 100,
            "provenance": {
                "source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE,
                "document": "fixture",
                "namespace": "main",
            },
        })
        payload["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        with self.assertRaisesRegex(
            common.ValidationError,
            "authored_dimensions must equal the complete descriptor-consumed control set",
        ):
            common._validate_provisional_form_envelope(payload, "extra v6 dimension fixture")

    def test_historical_v5_retains_only_its_original_dimension_contract(self) -> None:
        payload = self.capsule_payload(
            format_name=common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT
        )
        validated = common._validate_provisional_form_envelope(payload, "historical v5 fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT)
        for variant in validated["variants"]:
            for descriptor in variant["descriptors"]:
                if descriptor["address"]["role"] == "upper_arm":
                    self.assertEqual(descriptor["dimension_roles"], ["form_radius"])
        self.assertNotIn("authored_landmarks", validated)
        self.assertNotIn("authored_frames", validated)

    def test_v6_shoulder_control_inventory_fails_closed(self) -> None:
        cases = []

        missing = copy.deepcopy(self.payload)
        missing["authored_landmarks"].pop()
        cases.append(missing)

        duplicate = copy.deepcopy(self.payload)
        duplicate["authored_frames"].append(copy.deepcopy(duplicate["authored_frames"][0]))
        cases.append(duplicate)

        wrong_owner = copy.deepcopy(self.payload)
        wrong_owner["authored_landmarks"][0]["owner"]["role"] = "forearm"
        cases.append(wrong_owner)

        wrong_frame = copy.deepcopy(self.payload)
        wrong_frame["authored_landmarks"][0]["frame"]["role"] = "wrong_frame"
        cases.append(wrong_frame)

        nonidentity = copy.deepcopy(self.payload)
        nonidentity["authored_frames"][0]["transform"]["translation"][0] = 0.1
        cases.append(nonidentity)

        out_of_bound = copy.deepcopy(self.payload)
        out_of_bound["authored_landmarks"][0]["position"][0] = 1.01
        cases.append(out_of_bound)

        nonfinite = copy.deepcopy(self.payload)
        nonfinite["authored_landmarks"][0]["position"][0] = float("nan")
        cases.append(nonfinite)

        missing_descriptor = copy.deepcopy(self.payload)
        for variant in missing_descriptor["variants"]:
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if not (
                    descriptor["address"]["role"] == "upper_arm"
                    and descriptor["address"]["anchors"] == ["right"]
                )
            ]
        cases.append(missing_descriptor)

        for index, payload in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(common.ValidationError):
                    common._validate_provisional_form_envelope(
                        payload, f"malformed v6 control fixture {index}"
                    )

    def test_v7_torso_profile_is_a_closed_index_over_canonical_controls(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V7_FORMAT)
        validated = common._validate_provisional_form_envelope(payload, "v7 torso fixture")
        profile = validated["authored_torso_profile"]
        self.assertEqual(profile["format"], common.PROVISIONAL_FORM_TORSO_PROFILE_FORMAT)
        self.assertEqual(
            [section["name"] for section in profile["sections"]],
            list(common.PROVISIONAL_FORM_TORSO_PROFILE_SECTION_NAMES),
        )
        self.assertEqual(len(validated["authored_frames"]), 4)
        self.assertEqual(len(validated["authored_landmarks"]), 11)
        self.assertEqual(len(validated["authored_dimensions"]), 57)
        self.assertTrue(
            all(
                set(section)
                == {
                    "name",
                    "frame_index",
                    "landmark_index",
                    "dimension_indices",
                    "provenance",
                    "section_index",
                }
                for section in profile["sections"]
            )
        )
        for section_index, (section, owner_role) in enumerate(zip(
            profile["sections"], common.PROVISIONAL_FORM_TORSO_PROFILE_OWNER_ROLES
        )):
            self.assertEqual(section["section_index"], section_index)
            self.assertEqual(
                validated["authored_frames"][section["frame_index"]]["owner"]["role"],
                owner_role,
            )
            self.assertEqual(
                validated["authored_landmarks"][section["landmark_index"]]["role"],
                f"form_torso_profile_{section['name'].replace('-', '_')}",
            )
            for axis, suffix in (
                ("lateral", "lateral_radius"),
                ("anterior", "anterior_radius"),
                ("posterior", "posterior_radius"),
            ):
                dimension = validated["authored_dimensions"][
                    section["dimension_indices"][axis]
                ]
                self.assertEqual(
                    dimension["role"],
                    f"form_torso_profile_{section['name'].replace('-', '_')}_{suffix}",
                )
        self.assertTrue(all("torso_profile" in variant for variant in validated["variants"]))

        cases = []
        unknown_envelope_field = copy.deepcopy(payload)
        unknown_envelope_field["unexpected"] = True
        cases.append(unknown_envelope_field)

        wrong_profile_format = copy.deepcopy(payload)
        wrong_profile_format["authored_torso_profile"]["format"] = "wrong"
        cases.append(wrong_profile_format)

        wrong_profile_provenance = copy.deepcopy(payload)
        wrong_profile_provenance["authored_torso_profile"]["provenance"]["document"] = "wrong"
        cases.append(wrong_profile_provenance)

        wrong_section_order = copy.deepcopy(payload)
        wrong_section_order["authored_torso_profile"]["sections"][1]["name"] = "lower-pelvis"
        cases.append(wrong_section_order)

        wrong_section_index = copy.deepcopy(payload)
        wrong_section_index["authored_torso_profile"]["sections"][1]["section_index"] = 0
        cases.append(wrong_section_index)

        wrong_frame_reference = copy.deepcopy(payload)
        wrong_frame_reference["authored_torso_profile"]["sections"][0]["frame_index"] = 2
        cases.append(wrong_frame_reference)

        non_integer_frame_index = copy.deepcopy(payload)
        non_integer_frame_index["authored_torso_profile"]["sections"][0]["frame_index"] = True
        cases.append(non_integer_frame_index)

        wrong_landmark_reference = copy.deepcopy(payload)
        wrong_landmark_reference["authored_torso_profile"]["sections"][0]["landmark_index"] = 1
        cases.append(wrong_landmark_reference)

        non_identity_frame = copy.deepcopy(payload)
        non_identity_frame["authored_frames"][0]["transform"]["translation"][1] = 0.1
        cases.append(non_identity_frame)

        non_axial_landmark = copy.deepcopy(payload)
        non_axial_landmark["authored_landmarks"][0]["position"][2] = 0.1
        cases.append(non_axial_landmark)

        non_increasing_y = copy.deepcopy(payload)
        non_increasing_y["authored_landmarks"][1]["position"][1] = non_increasing_y["authored_landmarks"][0]["position"][1]
        cases.append(non_increasing_y)

        zero_radius = copy.deepcopy(payload)
        zero_radius["authored_dimensions"][0]["value_permille"] = 0
        cases.append(zero_radius)

        wrong_dimension_reference = copy.deepcopy(payload)
        wrong_dimension_reference["authored_torso_profile"]["sections"][0]["dimension_indices"]["lateral"] = 0
        cases.append(wrong_dimension_reference)

        unknown_source_field = copy.deepcopy(payload)
        unknown_source_field["authored_torso_profile"]["sections"][0]["radius"] = 1
        cases.append(unknown_source_field)

        wrong_variant_source_index = copy.deepcopy(payload)
        wrong_variant_source_index["variants"][0]["torso_profile"]["sections"][0]["source_section_index"] = 1
        cases.append(wrong_variant_source_index)

        changed_variant_position = copy.deepcopy(payload)
        changed_variant_position["variants"][0]["torso_profile"]["sections"][0]["position"][1] += 0.01
        cases.append(changed_variant_position)

        wrong_variant_factor = copy.deepcopy(payload)
        wrong_variant_factor["variants"][1]["torso_profile"]["sections"][0]["scaling"]["lateral_factor_permille"] = 1_199
        cases.append(wrong_variant_factor)

        wrong_scaled_radius = copy.deepcopy(payload)
        wrong_scaled_radius["variants"][3]["torso_profile"]["sections"][2]["anterior_radius_permille"] += 1
        cases.append(wrong_scaled_radius)

        wrong_variant_provenance = copy.deepcopy(payload)
        wrong_variant_provenance["variants"][0]["torso_profile"]["sections"][0]["provenance"]["namespace"] = "wrong"
        cases.append(wrong_variant_provenance)

        unknown_variant_field = copy.deepcopy(payload)
        unknown_variant_field["variants"][0]["torso_profile"]["extra"] = True
        cases.append(unknown_variant_field)

        for index, malformed in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(malformed, f"malformed v7 torso fixture {index}")

        for prior_format in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
        ):
            prior = self.capsule_payload(format_name=prior_format)
            prior["authored_torso_profile"] = copy.deepcopy(payload["authored_torso_profile"])
            with self.subTest(prior_format=prior_format), self.assertRaisesRegex(
                common.ValidationError, "authored_torso_profile is only valid for v7"
            ):
                common._validate_provisional_form_envelope(prior, f"v7 field on {prior_format}")
            prior_variant = self.capsule_payload(format_name=prior_format)
            prior_variant["variants"][0]["torso_profile"] = copy.deepcopy(
                payload["variants"][0]["torso_profile"]
            )
            with self.subTest(prior_variant_format=prior_format), self.assertRaisesRegex(
                common.ValidationError, "torso_profile"
            ):
                common._validate_provisional_form_envelope(
                    prior_variant, f"v7 variant field on {prior_format}"
                )

    def test_v7_torso_profile_rejects_composed_space_cross_owner_inversion(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V7_FORMAT)
        upper_pelvis = next(
            landmark
            for landmark in payload["authored_landmarks"]
            if landmark["role"] == "form_torso_profile_upper_pelvis"
        )
        upper_pelvis["position"][1] = 0.95
        for variant in payload["variants"]:
            variant["torso_profile"]["sections"][1]["position"][1] = 0.95
        with self.assertRaisesRegex(
            common.ValidationError,
            r"authored_torso_profile\.sections landmarks must have strictly increasing composed body-space y",
        ):
            common._validate_provisional_form_envelope(
                payload, "composed-space cross-owner torso route fixture"
            )

    def test_unknown_and_malformed_payloads_fail_closed(self) -> None:
        cases = [
            {"unknown": True},
            {"variants": list(reversed(self.payload["variants"]))},
            {"shape": {"name": "mesh"}},
            {"reference_scale": {"axis_delta": [0, 1, 0], "squared_length": 2}},
            {"point": [1.5, 0, 0]},
            {"permille": 0},
        ]
        for index, change in enumerate(cases):
            payload = copy.deepcopy(self.payload)
            if "unknown" in change:
                payload["unexpected"] = True
            elif "variants" in change:
                payload["variants"] = change["variants"]
            elif "shape" in change:
                payload["variants"][0]["descriptors"][0]["shape"] = {"name": "mesh"}
            elif "reference_scale" in change:
                payload["reference_scale"]["squared_length"] = 2
            elif "point" in change:
                payload["variants"][0]["descriptors"][0]["reference_point"] = [1.5, 0, 0]
            else:
                payload["variants"][0]["descriptors"][0]["shape"]["axis_extents_permille"][0] = 0
            binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(payload)) + ")\n", f"bad-{index}")
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id=f"bad-form-{index}")
            self.assertFalse((self.root / f"bad-form-{index}").exists())

    def test_v8_head_neck_profile_is_closed_indexed_ordered_and_source_provenant(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V8_FORMAT)
        validated = common._validate_provisional_form_envelope(payload, "v8 head/neck fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_V8_FORMAT)
        self.assertEqual(len(validated["authored_dimensions"]), 81)
        self.assertEqual(len(validated["authored_frames"]), 6)
        self.assertEqual(len(validated["authored_landmarks"]), 19)
        profile = validated["authored_head_neck_profile"]
        self.assertEqual(profile["format"], common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT)
        self.assertEqual(
            [section["name"] for section in profile["sections"]],
            list(common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES),
        )
        self.assertEqual(
            profile["connections"],
            [
                {
                    "name": name,
                    "from_section_index": from_index,
                    "to_section_index": to_index,
                    "route": route,
                }
                for name, from_index, to_index, route
                in common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS
            ],
        )
        for index, (section, owner_role) in enumerate(zip(
            profile["sections"], common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES
        )):
            self.assertEqual(section["section_index"], index)
            frame = validated["authored_frames"][section["frame_index"]]
            landmark = validated["authored_landmarks"][section["landmark_index"]]
            self.assertEqual(frame["owner"]["role"], owner_role)
            self.assertEqual(frame["role"], common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE)
            self.assertEqual(landmark["owner"], frame["owner"])
            self.assertEqual(
                landmark["role"],
                f"form_head_neck_profile_{section['name'].replace('-', '_')}",
            )
            self.assertEqual(landmark["frame"]["role"], common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE)
            self.assertEqual(landmark["position"][0], 0)
            for axis, suffix in common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES:
                dimension = validated["authored_dimensions"][section["dimension_indices"][axis]]
                self.assertEqual(
                    dimension["role"],
                    f"form_head_neck_profile_{section['name'].replace('-', '_')}_{suffix}",
                )
        for variant in validated["variants"]:
            self.assertIn("torso_profile", variant)
            self.assertIn("head_neck_profile", variant)
            self.assertEqual(
                variant["head_neck_profile"]["connections"],
                profile["connections"],
            )

        cases = []
        missing_head_profile = copy.deepcopy(payload)
        missing_head_profile.pop("authored_head_neck_profile")
        cases.append(missing_head_profile)
        missing_torso_profile = copy.deepcopy(payload)
        missing_torso_profile.pop("authored_torso_profile")
        cases.append(missing_torso_profile)
        unknown_envelope_field = copy.deepcopy(payload)
        unknown_envelope_field["unexpected"] = True
        cases.append(unknown_envelope_field)
        wrong_profile_format = copy.deepcopy(payload)
        wrong_profile_format["authored_head_neck_profile"]["format"] = "wrong"
        cases.append(wrong_profile_format)
        wrong_connection_route = copy.deepcopy(payload)
        wrong_connection_route["authored_head_neck_profile"]["connections"][0]["route"] = "wrong"
        cases.append(wrong_connection_route)
        wrong_section_order = copy.deepcopy(payload)
        wrong_section_order["authored_head_neck_profile"]["sections"][0]["name"] = "neck-upper"
        cases.append(wrong_section_order)
        wrong_section_index = copy.deepcopy(payload)
        wrong_section_index["authored_head_neck_profile"]["sections"][1]["section_index"] = 0
        cases.append(wrong_section_index)
        wrong_frame_index = copy.deepcopy(payload)
        wrong_frame_index["authored_head_neck_profile"]["sections"][0]["frame_index"] = 0
        cases.append(wrong_frame_index)
        wrong_landmark_index = copy.deepcopy(payload)
        wrong_landmark_index["authored_head_neck_profile"]["sections"][0]["landmark_index"] = 0
        cases.append(wrong_landmark_index)
        non_axial = copy.deepcopy(payload)
        non_axial["authored_landmarks"][non_axial["authored_head_neck_profile"]["sections"][0]["landmark_index"]]["position"][0] = 0.1
        cases.append(non_axial)
        non_increasing_neck_y = copy.deepcopy(payload)
        neck_sections = non_increasing_neck_y["authored_head_neck_profile"]["sections"]
        first_neck = neck_sections[0]["landmark_index"]
        second_neck = neck_sections[1]["landmark_index"]
        non_increasing_neck_y["authored_landmarks"][second_neck]["position"][1] = non_increasing_neck_y["authored_landmarks"][first_neck]["position"][1]
        cases.append(non_increasing_neck_y)
        muzzle_root_at_cranium_mid = copy.deepcopy(payload)
        muzzle_sections = muzzle_root_at_cranium_mid["authored_head_neck_profile"]["sections"]
        cranium_mid = muzzle_sections[3]["landmark_index"]
        muzzle_root = muzzle_sections[5]["landmark_index"]
        muzzle_root_at_cranium_mid["authored_landmarks"][muzzle_root]["position"][2] = muzzle_root_at_cranium_mid["authored_landmarks"][cranium_mid]["position"][2]
        cases.append(muzzle_root_at_cranium_mid)
        muzzle_root_before_cranium_mid = copy.deepcopy(payload)
        muzzle_sections = muzzle_root_before_cranium_mid["authored_head_neck_profile"]["sections"]
        cranium_mid = muzzle_sections[3]["landmark_index"]
        muzzle_root = muzzle_sections[5]["landmark_index"]
        muzzle_root_before_cranium_mid["authored_landmarks"][muzzle_root]["position"][2] = muzzle_root_before_cranium_mid["authored_landmarks"][cranium_mid]["position"][2] - 0.1
        cases.append(muzzle_root_before_cranium_mid)
        non_increasing_muzzle_z = copy.deepcopy(payload)
        muzzle_sections = non_increasing_muzzle_z["authored_head_neck_profile"]["sections"]
        first_muzzle = muzzle_sections[5]["landmark_index"]
        second_muzzle = muzzle_sections[6]["landmark_index"]
        non_increasing_muzzle_z["authored_landmarks"][second_muzzle]["position"][2] = non_increasing_muzzle_z["authored_landmarks"][first_muzzle]["position"][2]
        cases.append(non_increasing_muzzle_z)
        wrong_dimension_index = copy.deepcopy(payload)
        wrong_dimension_index["authored_head_neck_profile"]["sections"][0]["dimension_indices"]["up"] = 0
        cases.append(wrong_dimension_index)
        wrong_variant_position = copy.deepcopy(payload)
        wrong_variant_position["variants"][0]["head_neck_profile"]["sections"][0]["position"][1] += 0.01
        cases.append(wrong_variant_position)
        wrong_variant_factor = copy.deepcopy(payload)
        wrong_variant_factor["variants"][1]["head_neck_profile"]["sections"][2]["scaling"]["lateral_factor_permille"] = 1_201
        cases.append(wrong_variant_factor)
        wrong_scaled_radius = copy.deepcopy(payload)
        wrong_scaled_radius["variants"][3]["head_neck_profile"]["sections"][2]["forward_radius_permille"] += 1
        cases.append(wrong_scaled_radius)
        unknown_variant_field = copy.deepcopy(payload)
        unknown_variant_field["variants"][0]["head_neck_profile"]["extra"] = True
        cases.append(unknown_variant_field)
        for index, malformed in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(malformed, f"malformed v8 head/neck fixture {index}")

        for prior_format in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
            common.PROVISIONAL_FORM_V7_FORMAT,
        ):
            prior = self.capsule_payload(format_name=prior_format)
            prior["authored_head_neck_profile"] = copy.deepcopy(payload["authored_head_neck_profile"])
            with self.subTest(prior_format=prior_format), self.assertRaisesRegex(
                common.ValidationError, "authored_head_neck_profile is only valid for v8"
            ):
                common._validate_provisional_form_envelope(prior, f"v8 field on {prior_format}")
            prior_variant = self.capsule_payload(format_name=prior_format)
            prior_variant["variants"][0]["head_neck_profile"] = copy.deepcopy(
                payload["variants"][0]["head_neck_profile"]
            )
            with self.subTest(prior_variant_format=prior_format), self.assertRaisesRegex(
                common.ValidationError, "head_neck_profile"
            ):
                common._validate_provisional_form_envelope(
                    prior_variant, f"v8 variant field on {prior_format}"
                )

    def test_v9_arm_profile_is_closed_and_python_browser_parity_is_fail_closed(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V9_FORMAT)
        validated = common._validate_provisional_form_envelope(payload, "v9 arm fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_V9_FORMAT)
        self.assertEqual(len(validated["authored_dimensions"]), 111)
        self.assertEqual(len(validated["authored_frames"]), 10)
        self.assertEqual(len(validated["authored_landmarks"]), 29)
        profile = validated["authored_arm_profile"]
        self.assertEqual(profile["format"], common.PROVISIONAL_FORM_ARM_PROFILE_FORMAT)
        self.assertEqual(
            [side["side"] for side in profile["sides"]],
            list(common.PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES),
        )
        for side_index, side in enumerate(profile["sides"]):
            self.assertEqual(
                [section["name"] for section in side["sections"]],
                list(common.PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES),
            )
            for section_index, (section, owner_role) in enumerate(zip(
                side["sections"], common.PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES
            )):
                self.assertEqual(section["section_index"], section_index)
                frame = validated["authored_frames"][section["frame_index"]]
                landmark = validated["authored_landmarks"][section["landmark_index"]]
                self.assertEqual(frame["owner"]["anchors"], [side["side"]])
                self.assertEqual(frame["owner"]["role"], owner_role)
                self.assertEqual(frame["role"], common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE)
                self.assertEqual(landmark["owner"], frame["owner"])
                self.assertEqual(
                    landmark["role"],
                    f"form_arm_profile_{section['name'].replace('-', '_')}",
                )
                self.assertEqual(landmark["frame"]["role"], common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE)
                self.assertEqual(landmark["position"][0], 0)
                self.assertEqual(landmark["position"][2], 0)
                for axis, suffix in common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES:
                    dimension = validated["authored_dimensions"][section["dimension_indices"][axis]]
                    self.assertEqual(
                        dimension["role"],
                        f"form_arm_profile_{section['name'].replace('-', '_')}_{suffix}",
                    )
                    self.assertGreater(dimension["value_permille"], 0)
                    self.assertLessEqual(dimension["value_permille"], 5000)
        for variant in validated["variants"]:
            self.assertEqual(
                [side["side"] for side in variant["arm_profile"]["sides"]],
                list(common.PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES),
            )
            for side in variant["arm_profile"]["sides"]:
                for section_index, section in enumerate(side["sections"]):
                    self.assertEqual(section["source_section_index"], section_index)
                    for axis, _suffix in common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES:
                        self.assertGreater(section[f"{axis}_radius_permille"], 0)
                        self.assertLessEqual(section[f"{axis}_radius_permille"], 5000)
        self.assertEqual(self.browser_form_errors(payload), [])

        cases: list[tuple[str, dict[str, object]]] = []
        wrong_side = copy.deepcopy(payload)
        wrong_side["authored_arm_profile"]["sides"][0]["side"] = "right"
        cases.append(("wrong side order", wrong_side))
        wrong_section_order = copy.deepcopy(payload)
        wrong_section_order["authored_arm_profile"]["sides"][0]["sections"][0]["name"] = "elbow"
        cases.append(("wrong section order", wrong_section_order))
        wrong_section_index = copy.deepcopy(payload)
        wrong_section_index["authored_arm_profile"]["sides"][1]["sections"][1]["source_section_index"] = 0
        cases.append(("wrong source section index", wrong_section_index))
        wrong_frame_reference = copy.deepcopy(payload)
        wrong_frame_reference["authored_arm_profile"]["sides"][0]["sections"][0]["frame_index"] = 0
        cases.append(("wrong frame reference", wrong_frame_reference))
        wrong_landmark_reference = copy.deepcopy(payload)
        wrong_landmark_reference["authored_arm_profile"]["sides"][0]["sections"][0]["landmark_index"] = 0
        cases.append(("wrong landmark reference", wrong_landmark_reference))
        wrong_dimension_reference = copy.deepcopy(payload)
        wrong_dimension_reference["authored_arm_profile"]["sides"][0]["sections"][0]["dimension_indices"]["lateral"] = 0
        cases.append(("wrong dimension reference", wrong_dimension_reference))
        wrong_source_position = copy.deepcopy(payload)
        source_landmark_index = wrong_source_position["authored_arm_profile"]["sides"][0]["sections"][1]["landmark_index"]
        wrong_source_position["authored_landmarks"][source_landmark_index]["position"][0] = 0.1
        cases.append(("wrong source-local position", wrong_source_position))
        wrong_variant_position = copy.deepcopy(payload)
        wrong_variant_position["variants"][0]["arm_profile"]["sides"][0]["sections"][0]["position"][1] = 0.1
        cases.append(("wrong projected position", wrong_variant_position))
        wrong_source_radius = copy.deepcopy(payload)
        source_dimension_index = wrong_source_radius["authored_arm_profile"]["sides"][0]["sections"][0]["dimension_indices"]["lateral"]
        wrong_source_radius["authored_dimensions"][source_dimension_index]["value_permille"] = 0
        cases.append(("wrong source radius", wrong_source_radius))
        wrong_variant_radius = copy.deepcopy(payload)
        wrong_variant_radius["variants"][1]["arm_profile"]["sides"][0]["sections"][0]["lateral_radius_permille"] += 1
        cases.append(("wrong projected radius", wrong_variant_radius))
        wrong_scaling = copy.deepcopy(payload)
        wrong_scaling["variants"][2]["arm_profile"]["sides"][0]["sections"][0]["scaling"]["forward_factor_permille"] = 1
        cases.append(("wrong scaling", wrong_scaling))
        wrong_provenance = copy.deepcopy(payload)
        wrong_provenance["authored_arm_profile"]["provenance"]["document"] = "wrong"
        cases.append(("wrong source provenance", wrong_provenance))
        wrong_variant_provenance = copy.deepcopy(payload)
        wrong_variant_provenance["variants"][3]["arm_profile"]["sides"][1]["sections"][4]["provenance"]["namespace"] = "wrong"
        cases.append(("wrong variant provenance", wrong_variant_provenance))
        unknown_control = copy.deepcopy(payload)
        unknown_control["authored_arm_profile"]["sides"][0]["unexpected"] = True
        cases.append(("unlisted profile control", unknown_control))
        for label, malformed in cases:
            with self.subTest(common_case=label), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(malformed, f"malformed v9 arm fixture: {label}")
            with self.subTest(browser_case=label):
                self.assertTrue(self.browser_form_errors(malformed))

    def test_v10_leg_profile_is_closed_and_python_browser_parity_is_fail_closed(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V10_FORMAT)
        validated = common._validate_provisional_form_envelope(payload, "v10 leg fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_V10_FORMAT)
        self.assertEqual(len(validated["authored_dimensions"]), 141)
        self.assertEqual(len(validated["authored_frames"]), 14)
        self.assertEqual(len(validated["authored_landmarks"]), 39)
        profile = validated["authored_leg_profile"]
        self.assertEqual(profile["format"], common.PROVISIONAL_FORM_LEG_PROFILE_FORMAT)
        self.assertEqual(
            [side["side"] for side in profile["sides"]],
            list(common.PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES),
        )
        for side in profile["sides"]:
            self.assertEqual(
                [section["name"] for section in side["sections"]],
                list(common.PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES),
            )
            for section_index, (section, owner_role) in enumerate(zip(
                side["sections"], common.PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES
            )):
                self.assertEqual(section["section_index"], section_index)
                frame = validated["authored_frames"][section["frame_index"]]
                landmark = validated["authored_landmarks"][section["landmark_index"]]
                self.assertEqual(frame["owner"]["anchors"], [side["side"]])
                self.assertEqual(frame["owner"]["role"], owner_role)
                self.assertEqual(frame["role"], common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE)
                self.assertEqual(landmark["owner"], frame["owner"])
                self.assertEqual(
                    landmark["role"],
                    f"form_leg_profile_{section['name'].replace('-', '_')}",
                )
                self.assertEqual(landmark["frame"]["role"], common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE)
                self.assertEqual(landmark["position"][0], 0)
                self.assertEqual(landmark["position"][2], 0)
                for axis, suffix in common.PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES:
                    dimension = validated["authored_dimensions"][section["dimension_indices"][axis]]
                    self.assertEqual(
                        dimension["role"],
                        f"form_leg_profile_{section['name'].replace('-', '_')}_{suffix}",
                    )
                    self.assertGreater(dimension["value_permille"], 0)
                    self.assertLessEqual(dimension["value_permille"], 5000)
        self.assertEqual(self.browser_form_errors(payload), [])

        cases: list[tuple[str, dict[str, object]]] = []
        missing_profile = copy.deepcopy(payload)
        missing_profile.pop("authored_leg_profile")
        cases.append(("missing authored leg profile", missing_profile))
        renamed_variant_profile = copy.deepcopy(payload)
        renamed_variant_profile["variants"][0]["leg_profile_renamed"] = renamed_variant_profile["variants"][0].pop("leg_profile")
        cases.append(("renamed variant leg profile", renamed_variant_profile))
        wrong_profile_format = copy.deepcopy(payload)
        wrong_profile_format["authored_leg_profile"]["format"] = "wrong"
        cases.append(("wrong leg profile format", wrong_profile_format))
        duplicate_landmark = copy.deepcopy(payload)
        duplicate_landmark["authored_landmarks"][0]["role"] = duplicate_landmark["authored_landmarks"][1]["role"]
        cases.append(("duplicate leg landmark", duplicate_landmark))
        wrong_side = copy.deepcopy(payload)
        wrong_side["authored_leg_profile"]["sides"][0]["side"] = "right"
        cases.append(("wrong leg side", wrong_side))
        wrong_owner = copy.deepcopy(payload)
        wrong_owner["authored_leg_profile"]["sides"][0]["sections"][0]["frame_index"] = next(
            index for index, frame in enumerate(wrong_owner["authored_frames"])
            if frame["role"] == common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
            and frame["owner"]["anchors"] == ["left"]
            and frame["owner"]["role"] == "shin"
        )
        cases.append(("wrong leg owner", wrong_owner))
        cross_bound = copy.deepcopy(payload)
        cross_bound["authored_leg_profile"]["sides"][1]["sections"][4]["landmark_index"] = 0
        cases.append(("cross-bound leg landmark", cross_bound))
        wrong_position = copy.deepcopy(payload)
        source_landmark_index = wrong_position["authored_leg_profile"]["sides"][0]["sections"][0]["landmark_index"]
        wrong_position["authored_landmarks"][source_landmark_index]["position"][1] = 1.1
        cases.append(("out-of-bound leg position", wrong_position))
        wrong_distal_order = copy.deepcopy(payload)
        left_knee_source_index = wrong_distal_order["authored_leg_profile"]["sides"][0]["sections"][2]["landmark_index"]
        wrong_distal_order["authored_landmarks"][left_knee_source_index]["position"][1] = -0.25
        for variant in wrong_distal_order["variants"]:
            variant["leg_profile"]["sides"][0]["sections"][2]["position"][1] = -0.25
        cases.append(("left knee out of distal order", wrong_distal_order))
        positive_but_descending = copy.deepcopy(payload)
        for section_index, y in enumerate((0.75, 0.25, -0.25)):
            landmark_index = positive_but_descending["authored_leg_profile"]["sides"][0]["sections"][section_index]["landmark_index"]
            positive_but_descending["authored_landmarks"][landmark_index]["position"][1] = y
        cases.append(("positive but descending leg stations", positive_but_descending))
        wrong_source_radius = copy.deepcopy(payload)
        source_dimension_index = wrong_source_radius["authored_leg_profile"]["sides"][0]["sections"][0]["dimension_indices"]["lateral"]
        wrong_source_radius["authored_dimensions"][source_dimension_index]["value_permille"] = 0
        cases.append(("non-positive leg radius", wrong_source_radius))
        wrong_projected_radius = copy.deepcopy(payload)
        wrong_projected_radius["variants"][1]["leg_profile"]["sides"][0]["sections"][0]["lateral_radius_permille"] += 1
        cases.append(("wrong projected leg radius", wrong_projected_radius))
        wrong_scaling = copy.deepcopy(payload)
        wrong_scaling["variants"][2]["leg_profile"]["sides"][0]["sections"][0]["scaling"]["forward_factor_permille"] = 1
        cases.append(("wrong leg scaling", wrong_scaling))
        wrong_provenance = copy.deepcopy(payload)
        wrong_provenance["authored_leg_profile"]["provenance"]["document"] = "wrong"
        cases.append(("wrong leg provenance", wrong_provenance))
        unknown_control = copy.deepcopy(payload)
        unknown_control["authored_leg_profile"]["sides"][0]["sections"][0]["unexpected"] = True
        cases.append(("unknown leg control field", unknown_control))
        unknown_dimension = copy.deepcopy(payload)
        unknown_dimension["authored_dimensions"].append(copy.deepcopy(unknown_dimension["authored_dimensions"][-1]))
        unknown_dimension["authored_dimensions"][-1]["role"] = "form_leg_profile_unknown_radius"
        cases.append(("unknown leg dimension", unknown_dimension))
        for label, malformed in cases:
            with self.subTest(common_case=label), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(malformed, f"malformed v10 leg fixture: {label}")
            with self.subTest(browser_case=label):
                self.assertTrue(self.browser_form_errors(malformed))

    def test_v11_foot_profile_is_closed_and_python_browser_parity_is_fail_closed(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V11_FORMAT)
        validated = common._validate_provisional_form_envelope(payload, "v11 foot fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_V11_FORMAT)
        self.assertEqual(len(validated["authored_dimensions"]), 153)
        self.assertEqual(len(validated["authored_frames"]), 16)
        self.assertEqual(len(validated["authored_landmarks"]), 43)
        profile = validated["authored_foot_profile"]
        self.assertEqual(profile["format"], common.PROVISIONAL_FORM_FOOT_PROFILE_FORMAT)
        self.assertEqual(
            [side["side"] for side in profile["sides"]],
            list(common.PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES),
        )
        for side_index, side in enumerate(profile["sides"]):
            self.assertEqual(
                side["hock_binding"],
                {
                    "source_profile": "authored_leg_profile",
                    "side_index": side_index,
                    "section_index": common.PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX,
                },
            )
            self.assertEqual(
                [section["name"] for section in side["sections"]],
                list(common.PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES),
            )
            previous_z = None
            for section_index, section in enumerate(side["sections"]):
                self.assertEqual(section["section_index"], section_index)
                frame = validated["authored_frames"][section["frame_index"]]
                landmark = validated["authored_landmarks"][section["landmark_index"]]
                self.assertEqual(frame["owner"]["role"], "foot")
                self.assertEqual(frame["owner"]["anchors"], [side["side"]])
                self.assertEqual(frame["role"], common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE)
                self.assertEqual(landmark["owner"], frame["owner"])
                self.assertEqual(landmark["role"], "form_foot_profile_" + section["name"])
                self.assertEqual(landmark["frame"]["role"], common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE)
                self.assertEqual(landmark["position"][0], 0)
                self.assertGreaterEqual(landmark["position"][1], -1)
                self.assertLessEqual(landmark["position"][1], 0)
                self.assertGreaterEqual(landmark["position"][2], 0)
                self.assertLessEqual(landmark["position"][2], 1)
                if previous_z is not None:
                    self.assertGreater(landmark["position"][2], previous_z)
                previous_z = landmark["position"][2]
                for axis, suffix in common.PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES:
                    dimension = validated["authored_dimensions"][section["dimension_indices"][axis]]
                    self.assertEqual(
                        dimension["role"],
                        "form_foot_profile_" + section["name"] + "_" + suffix,
                    )
                    self.assertEqual(dimension["owner"], frame["owner"])
                    self.assertGreater(dimension["value_permille"], 0)
                    self.assertLessEqual(dimension["value_permille"], 5000)
        for variant in validated["variants"]:
            foot_variant = variant["foot_profile"]
            self.assertEqual(foot_variant["format"], common.PROVISIONAL_FORM_FOOT_PROFILE_FORMAT)
            self.assertEqual(foot_variant["source"], "authored_foot_profile")
            self.assertEqual(
                [side["side"] for side in foot_variant["sides"]],
                list(common.PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES),
            )
            for side in foot_variant["sides"]:
                for section_index, section in enumerate(side["sections"]):
                    self.assertEqual(section["source_section_index"], section_index)
                    self.assertEqual(section["position"][0], 0)
                    self.assertGreaterEqual(section["position"][1], -1)
                    self.assertLessEqual(section["position"][1], 0)
                    self.assertGreaterEqual(section["position"][2], 0)
                    self.assertLessEqual(section["position"][2], 1)
        self.assertEqual(self.browser_form_errors(payload), [])

        cases: list[tuple[str, dict[str, object]]] = []
        missing_profile = copy.deepcopy(payload)
        missing_profile.pop("authored_foot_profile")
        cases.append(("missing authored foot profile", missing_profile))
        extra_profile_field = copy.deepcopy(payload)
        extra_profile_field["authored_foot_profile"]["unexpected"] = True
        cases.append(("extra authored foot profile field", extra_profile_field))
        wrong_variant_field = copy.deepcopy(payload)
        wrong_variant_field["variants"][0]["foot_profile"]["unexpected"] = True
        cases.append(("extra variant foot profile field", wrong_variant_field))
        wrong_side = copy.deepcopy(payload)
        wrong_side["authored_foot_profile"]["sides"][0]["side"] = "right"
        cases.append(("wrong foot side order", wrong_side))
        wrong_hock_side = copy.deepcopy(payload)
        wrong_hock_side["authored_foot_profile"]["sides"][0]["hock_binding"]["side_index"] = 1
        cases.append(("wrong foot hock side binding", wrong_hock_side))
        wrong_hock_section = copy.deepcopy(payload)
        wrong_hock_section["authored_foot_profile"]["sides"][0]["hock_binding"]["section_index"] = 3
        cases.append(("wrong foot hock section binding", wrong_hock_section))
        wrong_section_order = copy.deepcopy(payload)
        wrong_section_order["authored_foot_profile"]["sides"][0]["sections"][0]["name"] = "toe"
        cases.append(("wrong foot section order", wrong_section_order))
        wrong_section_index = copy.deepcopy(payload)
        wrong_section_index["authored_foot_profile"]["sides"][1]["sections"][1]["section_index"] = 0
        cases.append(("wrong foot section index", wrong_section_index))
        wrong_frame_reference = copy.deepcopy(payload)
        wrong_frame_reference["authored_foot_profile"]["sides"][0]["sections"][0]["frame_index"] = 0
        cases.append(("cross-bound foot frame reference", wrong_frame_reference))
        wrong_landmark_reference = copy.deepcopy(payload)
        wrong_landmark_reference["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"] = 0
        cases.append(("cross-bound foot landmark reference", wrong_landmark_reference))
        wrong_dimension_reference = copy.deepcopy(payload)
        wrong_dimension_reference["authored_foot_profile"]["sides"][0]["sections"][0]["dimension_indices"]["lateral"] = 0
        cases.append(("cross-bound foot dimension reference", wrong_dimension_reference))
        wrong_owner = copy.deepcopy(payload)
        source_landmark_index = wrong_owner["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"]
        wrong_owner["authored_landmarks"][source_landmark_index]["owner"]["role"] = "shin"
        cases.append(("wrong foot owner", wrong_owner))
        wrong_frame_role = copy.deepcopy(payload)
        source_frame_index = wrong_frame_role["authored_foot_profile"]["sides"][0]["sections"][0]["frame_index"]
        wrong_frame_role["authored_frames"][source_frame_index]["role"] = common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
        cases.append(("wrong foot frame role", wrong_frame_role))
        wrong_provenance = copy.deepcopy(payload)
        wrong_provenance["authored_foot_profile"]["sides"][0]["sections"][0]["provenance"]["document"] = "wrong"
        cases.append(("wrong foot source provenance", wrong_provenance))
        nonfinite_position = copy.deepcopy(payload)
        source_landmark_index = nonfinite_position["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"]
        nonfinite_position["authored_landmarks"][source_landmark_index]["position"][2] = math.nan
        cases.append(("nonfinite foot position", nonfinite_position))
        out_of_range_y = copy.deepcopy(payload)
        source_landmark_index = out_of_range_y["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"]
        out_of_range_y["authored_landmarks"][source_landmark_index]["position"][1] = 0.1
        cases.append(("superficially ordered foot y outside bounds", out_of_range_y))
        out_of_range_z = copy.deepcopy(payload)
        source_landmark_index = out_of_range_z["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"]
        out_of_range_z["authored_landmarks"][source_landmark_index]["position"][2] = -0.2
        cases.append(("superficially ordered foot z outside bounds", out_of_range_z))
        reversed_z = copy.deepcopy(payload)
        pad_index = reversed_z["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"]
        toe_index = reversed_z["authored_foot_profile"]["sides"][0]["sections"][1]["landmark_index"]
        reversed_z["authored_landmarks"][pad_index]["position"][2] = 0.8
        reversed_z["authored_landmarks"][toe_index]["position"][2] = 0.7
        cases.append(("reversed foot z order", reversed_z))
        equal_contact = copy.deepcopy(payload)
        toe_index = equal_contact["authored_foot_profile"]["sides"][0]["sections"][1]["landmark_index"]
        equal_contact["authored_landmarks"][toe_index]["position"][1] = -0.21
        cases.append(("unequal foot contact datum", equal_contact))
        no_forward_overlap = copy.deepcopy(payload)
        pad_index = no_forward_overlap["authored_foot_profile"]["sides"][0]["sections"][0]["landmark_index"]
        toe_index = no_forward_overlap["authored_foot_profile"]["sides"][0]["sections"][1]["landmark_index"]
        no_forward_overlap["authored_landmarks"][pad_index]["position"][2] = 0.0
        no_forward_overlap["authored_landmarks"][toe_index]["position"][2] = 1.0
        cases.append(("foot forward gap", no_forward_overlap))
        wrong_radius = copy.deepcopy(payload)
        source_dimension_index = wrong_radius["authored_foot_profile"]["sides"][0]["sections"][0]["dimension_indices"]["lateral"]
        wrong_radius["authored_dimensions"][source_dimension_index]["value_permille"] = 5001
        cases.append(("foot radius out of bounds", wrong_radius))
        wrong_projected_radius = copy.deepcopy(payload)
        wrong_projected_radius["variants"][1]["foot_profile"]["sides"][0]["sections"][0]["lateral_radius_permille"] += 1
        cases.append(("wrong projected foot radius", wrong_projected_radius))
        wrong_scaling = copy.deepcopy(payload)
        wrong_scaling["variants"][2]["foot_profile"]["sides"][0]["sections"][0]["scaling"]["forward_factor_permille"] = 1
        cases.append(("wrong foot scaling", wrong_scaling))
        wrong_variant_provenance = copy.deepcopy(payload)
        wrong_variant_provenance["variants"][3]["foot_profile"]["sides"][1]["sections"][1]["provenance"]["namespace"] = "wrong"
        cases.append(("wrong foot variant provenance", wrong_variant_provenance))
        unknown_dimension = copy.deepcopy(payload)
        unknown_dimension["authored_dimensions"].append(copy.deepcopy(unknown_dimension["authored_dimensions"][-1]))
        unknown_dimension["authored_dimensions"][-1]["role"] = "form_foot_profile_unknown_radius"
        cases.append(("unknown foot dimension", unknown_dimension))
        for label, malformed in cases:
            with self.subTest(common_case=label), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(malformed, "malformed v11 foot fixture: " + label)
            with self.subTest(browser_case=label):
                self.assertTrue(self.browser_form_errors(malformed))

    def test_v2_through_v6_limb_capsules_use_their_direct_distal_child_anchor(self) -> None:
        for format_name in (
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
        ):
            with self.subTest(format_name=format_name):
                payload = self.capsule_payload(format_name=format_name)
                validated = common._validate_provisional_form_envelope(
                    payload, "capsule fixture"
                )
                self.assertEqual(validated["format"], format_name)

                old_parent_center = copy.deepcopy(payload)
                for descriptor in old_parent_center["variants"][0]["descriptors"]:
                    if descriptor["address"]["role"] == "upper_arm":
                        descriptor["shape"]["from"] = [0, 1, 0]
                        break
                with self.assertRaisesRegex(
                    common.ValidationError,
                    "start does not match its reference point",
                ):
                    common._validate_provisional_form_envelope(
                        old_parent_center, "old capsule fixture"
                    )

        payload = self.capsule_payload()

        missing_distal = copy.deepcopy(payload)
        for variant in missing_distal["variants"]:
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] != "forearm"
            ]
        with self.assertRaisesRegex(common.ValidationError, "missing its direct forearm child"):
            common._validate_provisional_form_envelope(missing_distal, "missing capsule fixture")

        ambiguous = self.capsule_payload()
        for variant in ambiguous["variants"]:
            descriptors = variant["descriptors"]
            forearm = next(item for item in descriptors if item["address"]["role"] == "forearm")
            duplicate_forearm = copy.deepcopy(forearm)
            duplicate_forearm["address"]["anchors"] = ["branch"]
            duplicate_forearm["reference_point"] = [-2, 3, 0]
            duplicate_forearm["shape"]["from"] = [-2, 3, 0]
            duplicate_forearm["shape"]["to"] = [-3, 3, 0]
            duplicate_hand = next(item for item in descriptors if item["address"]["role"] == "hand")
            duplicate_hand = copy.deepcopy(duplicate_hand)
            duplicate_hand["address"]["anchors"] = ["branch"]
            duplicate_hand["parent"] = duplicate_forearm["address"]
            duplicate_hand["reference_point"] = [-3, 3, 0]
            duplicate_hand["shape"]["center"] = [-3, 3, 0]
            descriptors.extend([duplicate_forearm, duplicate_hand])
            descriptors.sort(key=lambda item: (
                item["address"]["namespace"], tuple(item["address"]["anchors"]),
                item["address"]["kind"], item["address"]["role"],
            ))
        ambiguous["authored_dimensions"].extend([
            {
                "owner": {"namespace": "main", "anchors": ["branch"], "kind": "part", "role": "forearm"},
                "role": "form_radius",
                "value_permille": 180,
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"},
            },
            *[
                {
                    "owner": {"namespace": "main", "anchors": ["branch"], "kind": "part", "role": "hand"},
                    "role": role,
                    "value_permille": value,
                    "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"},
                }
                for role, value in (
                    ("form_extent_x", 450),
                    ("form_extent_y", 400),
                    ("form_extent_z", 350),
                )
            ],
        ])
        ambiguous["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        with self.assertRaisesRegex(common.ValidationError, "ambiguous direct forearm children"):
            common._validate_provisional_form_envelope(ambiguous, "ambiguous capsule fixture")

    def test_v6_neck_capsule_requires_exactly_one_direct_head_endpoint(self) -> None:
        payload = self.capsule_payload(format_name=common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT)
        validated = common._validate_provisional_form_envelope(payload, "v6 neck fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT)

        neck_ellipsoid = copy.deepcopy(payload)
        for descriptor in neck_ellipsoid["variants"][0]["descriptors"]:
            if descriptor["address"]["role"] == "neck":
                descriptor["shape"] = {
                    "name": "ellipsoid",
                    "center": descriptor["reference_point"],
                    "axis_extents_permille": [650, 600, 600],
                }
                break
        with self.assertRaisesRegex(
            common.ValidationError, "must be capsule for role neck"
        ):
            common._validate_provisional_form_envelope(
                neck_ellipsoid, "v6 ellipsoid neck fixture"
            )

        wrong_endpoint = copy.deepcopy(payload)
        for descriptor in wrong_endpoint["variants"][0]["descriptors"]:
            if descriptor["address"]["role"] == "neck":
                descriptor["shape"]["to"] = [0, 4, 0]
                break
        with self.assertRaisesRegex(
            common.ValidationError, "end does not match its direct head child point"
        ):
            common._validate_provisional_form_envelope(
                wrong_endpoint, "v6 wrong neck endpoint fixture"
            )

        missing_head = copy.deepcopy(payload)
        for variant in missing_head["variants"]:
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] != "head"
            ]
        with self.assertRaisesRegex(
            common.ValidationError, "missing its direct head child"
        ):
            common._validate_provisional_form_envelope(
                missing_head, "v6 missing head fixture"
            )

        ambiguous_head = copy.deepcopy(payload)
        for variant in ambiguous_head["variants"]:
            descriptors = variant["descriptors"]
            head = next(
                item for item in descriptors if item["address"]["role"] == "head"
            )
            extra_head = copy.deepcopy(head)
            extra_head["address"]["anchors"] = ["branch"]
            extra_head["reference_point"] = [0, 4, 0]
            extra_head["shape"]["center"] = [0, 4, 0]
            descriptors.append(extra_head)
            descriptors.sort(key=lambda item: (
                item["address"]["namespace"], tuple(item["address"]["anchors"]),
                item["address"]["kind"], item["address"]["role"],
            ))
        ambiguous_head["authored_dimensions"].extend([
            {
                "owner": {"namespace": "main", "anchors": ["branch"], "kind": "part", "role": "head"},
                "role": role,
                "value_permille": value,
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"},
            }
            for role, value in (
                ("form_extent_x", 1000),
                ("form_extent_y", 1000),
                ("form_extent_z", 900),
            )
        ])
        ambiguous_head["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        with self.assertRaisesRegex(
            common.ValidationError, "ambiguous direct head children"
        ):
            common._validate_provisional_form_envelope(
                ambiguous_head, "v6 ambiguous head fixture"
            )

        for prior_format in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
        ):
            prior = self.capsule_payload(format_name=prior_format)
            prior["format"] = common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT
            expected_message = (
                "authored_landmarks is required for v6"
                if prior_format == common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT
                else "authored_dimensions is required for v5, v6, or v7"
            )
            with self.subTest(prior_format=prior_format), self.assertRaisesRegex(
                common.ValidationError, expected_message
            ):
                common._validate_provisional_form_envelope(
                    prior, "prior payload mislabeled v6"
                )

    def test_v1_capsules_retain_legacy_parent_to_current_contract(self) -> None:
        legacy = self.capsule_payload(
            format_name=common.PROVISIONAL_FORM_LEGACY_FORMAT
        )
        common._validate_provisional_form_envelope(legacy, "legacy capsule fixture")

        normalized = common.validate_normalized_review(
            {
                "schema_version": 1,
                "id": "legacy-form",
                "title": "Legacy form",
                "kind": "provisional-form",
                "groups": [],
                "provisional_form": legacy,
            },
            self.directory,
            check_assets=False,
        )
        self.assertEqual(
            normalized["provisional_form"]["format"],
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
        )

        corrected_mislabeled_v1 = self.capsule_payload(
            format_name=common.PROVISIONAL_FORM_V2_FORMAT
        )
        corrected_mislabeled_v1["format"] = common.PROVISIONAL_FORM_LEGACY_FORMAT
        with self.assertRaisesRegex(common.ValidationError, "capsule endpoints are invalid"):
            common._validate_provisional_form_envelope(
                corrected_mislabeled_v1, "corrected payload mislabeled v1"
            )

        for corrected_format in (
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
        ):
            legacy_mislabeled_corrected = copy.deepcopy(legacy)
            legacy_mislabeled_corrected["format"] = corrected_format
            with self.subTest(corrected_format=corrected_format), self.assertRaisesRegex(
                common.ValidationError, "start does not match its reference point"
            ):
                common._validate_provisional_form_envelope(
                    legacy_mislabeled_corrected,
                    "legacy payload mislabeled corrected",
                )

    def test_nonzero_output_bound_timeout_and_collision_are_bounded(self) -> None:
        noisy = self.fake_binary(f"import sys\nsys.stdout.write('x' * {publisher.MAX_STDOUT_BYTES + 1})\n", "noisy")
        with self.assertRaises(publisher.ProvisionalFormPublishError):
            self.publish_with(noisy, review_id="noisy")
        slow = self.fake_binary("import time\ntime.sleep(30)\n", "slow")
        with patch.object(publisher, "INSPECTION_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, "timed out"):
                self.publish_with(slow, review_id="slow")
        failed = self.fake_binary("import sys\nsys.stderr.write('failed')\nsys.exit(9)\n", "failed")
        with self.assertRaises(publisher.ProvisionalFormPublishError):
            self.publish_with(failed, review_id="failed")
        valid = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n", "valid")
        self.publish_with(valid, review_id="collision")
        with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, "already exists"):
            self.publish_with(valid, review_id="collision")

    def test_payload_rejects_root_role_shape_scale_and_exact_integer_violations(self) -> None:
        cases = []
        root_violation = copy.deepcopy(self.payload)
        root_violation["variants"][0]["descriptors"][1]["placement_source"] = "authored-root"
        root_violation["variants"][0]["descriptors"][1]["parent"] = None
        cases.append(root_violation)
        unknown_role = copy.deepcopy(self.payload)
        unknown_role["variants"][0]["descriptors"][0]["address"]["role"] = "mystery"
        cases.append(unknown_role)
        role_shape = copy.deepcopy(self.payload)
        role_shape["variants"][0]["descriptors"][0]["shape"]["name"] = "capsule"
        cases.append(role_shape)
        drift = copy.deepcopy(self.payload)
        drift["variants"][1]["descriptors"][0]["shape"]["name"] = "capsule"
        cases.append(drift)
        binary64 = copy.deepcopy(self.payload)
        binary64["variants"][0]["descriptors"][0]["reference_point"][0] = (1 << 53) + 1
        cases.append(binary64)
        non_edge = copy.deepcopy(self.payload)
        head = copy.deepcopy(non_edge["variants"][0]["descriptors"][1])
        head["address"] = {**head["address"], "role": "head"}
        head["parent"] = {**head["parent"], "role": "torso"}
        head["reference_point"] = [0, 2, 0]
        head["shape"]["center"] = [0, 2, 0]
        for variant in non_edge["variants"]:
            variant_head = copy.deepcopy(head)
            variant_head["profile_id"] = variant["id"]
            variant_head["provenance"] = copy.deepcopy(variant["provenance"])
            variant["descriptors"] = [variant_head, variant["descriptors"][0], variant["descriptors"][1]]
        non_edge["reference_scale"] = {
            "parent": {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"},
            "child": {"namespace": "main", "anchors": [], "kind": "part", "role": "head"},
            "axis_delta": [0, 2, 0],
            "squared_length": 4,
            "source": "exact-containment-edge",
        }
        cases.append(non_edge)
        for index, payload in enumerate(cases):
            binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(payload)) + ")\n", f"semantic-{index}")
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id=f"semantic-{index}")

    def test_input_is_copied_from_validated_identity_before_cli(self) -> None:
        capture = self.directory / "captured-input.bin"
        binary = self.fake_binary(
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(capture)!r}).write_bytes(pathlib.Path(sys.argv[-1]).read_bytes())\n"
            "sys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n",
            "identity-kernel",
        )
        self.input.write_bytes(b'{"identity":"original"}')
        self.publish_with(binary, review_id="identity-copy")
        self.assertEqual(capture.read_bytes(), self.input.read_bytes())
        self.assertNotEqual(capture.read_bytes(), b"{}")

    def test_forked_descendant_is_killed_on_timeout(self) -> None:
        pid_path = self.directory / "descendant.pid"
        binary = self.fake_binary(
            "import pathlib, subprocess, sys, time\n"
            f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            f"pathlib.Path({str(pid_path)!r}).write_text(str(child.pid))\n"
            "time.sleep(30)\n",
            "fork-kernel",
        )
        # Leave enough startup time for the helper to fork and persist its PID;
        # the timeout still interrupts the deliberately long-running process.
        with patch.object(publisher, "INSPECTION_TIMEOUT_SECONDS", 1.0):
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id="forked-timeout")
        child_pid = int(pid_path.read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            self.fail("forked descendant survived bounded process-group cleanup")

    def test_output_caps_are_exactly_bounded_before_buffering(self) -> None:
        self.assertEqual(publisher.MAX_STDOUT_BYTES, 256 * 1024)
        self.assertEqual(publisher.MAX_STDERR_BYTES, 64 * 1024)
        for label, limit in (("stdout", publisher.MAX_STDOUT_BYTES), ("stderr", publisher.MAX_STDERR_BYTES)):
            binary = self.fake_binary(
                "import sys\n"
                + (f"sys.stdout.write('x' * {limit + 1})\n" if label == "stdout" else f"sys.stderr.write('x' * {limit + 1})\n"),
                f"bound-{label}",
            )
            with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, label):
                self.publish_with(binary, review_id=f"bound-{label}")

    def test_checked_in_browser_dispatch_is_anchor_aware_and_shared_scale(self) -> None:
        app = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function renderProvisionalForm", app)
        self.assertIn("provisionalFormPreviewSection(payload)", app)
        self.assertIn("payload.variants.forEach", app)
        self.assertIn("formBounds(payload)", app)
        self.assertIn("function formDescriptorQualifier", app)
        self.assertIn('anchors.indexOf("left")', app)
        self.assertIn('anchors.indexOf("right")', app)
        self.assertIn('return "#a78bfa"', app)
        self.assertIn('return "#f4a261"', app)
        self.assertIn('"Front · x / y"', app)
        self.assertIn('"Side · z / y"', app)
        self.assertIn('"Top · x / z"', app)
        self.assertIn('"creature-kernel.provisional-form-preview.v6"', app)
        self.assertIn('"creature-kernel.provisional-form-preview.v7"', app)
        self.assertIn('"creature-kernel.provisional-form-preview.v8"', app)
        self.assertIn('"creature-kernel.provisional-form-preview.v9"', app)
        self.assertIn('var isV6 = payload.format === PROVISIONAL_FORM_V6_FORMAT;', app)
        self.assertIn('var isV8 = payload.format === PROVISIONAL_FORM_V8_FORMAT;', app)
        self.assertIn('var isV9 = payload.format === PROVISIONAL_FORM_V9_FORMAT;', app)
        self.assertIn('v5 is an authored-dimension-only format', app)
        self.assertIn('function formV6ShoulderControls(payload)', app)
        self.assertIn('form_shoulder_control', app)
        self.assertIn('form_shoulder_peak', app)
        self.assertIn('form_axilla', app)
        self.assertIn('["form_radius", "form_shoulder_depth_radius"]', app)
        self.assertIn('shape.name === "capsule" ? shape.radius_permille', app)
        self.assertIn('form_head_neck_profile_control', app)
        self.assertIn('forward-muzzle', app)
        self.assertIn('form_arm_profile_control', app)
        self.assertIn('function formV9AuthoredArmProfile(payload)', app)
        self.assertIn('"creature-kernel.provisional-form-preview.v10"', app)
        self.assertIn('"creature-kernel.provisional-form-preview.v11"', app)
        self.assertIn('var isV11 = payload.format === PROVISIONAL_FORM_V11_FORMAT;', app)
        self.assertIn('form_leg_profile_control', app)
        self.assertIn('function formV10AuthoredLegProfile(payload)', app)
        self.assertIn('form_foot_profile_control', app)
        self.assertIn('function formV11AuthoredFootProfile(payload, legSourceSides)', app)

    def browser_form_errors(self, payload: dict[str, object]) -> list[str]:
        script = r'''
const fs = require("fs");
const vm = require("vm");
const appPath = process.argv[1];
let source = fs.readFileSync(appPath, "utf8");
const entrypoint = "  load();\n}());";
if (source.split(entrypoint).length !== 2) {
  throw new Error("unexpected browser app entrypoint");
}
source = source.replace(entrypoint, "  globalThis.__formValidation = formValidation;\n}());");
const context = {
  console,
  document: { getElementById: function () { return null; } },
  window: {}
};
vm.runInNewContext(source, context, { filename: appPath });
function reviveNonfinite(key, value) {
  if (value && value.__browser_nonfinite__ === "nan") { return NaN; }
  if (value && value.__browser_nonfinite__ === "infinity") { return Infinity; }
  if (value && value.__browser_nonfinite__ === "negative-infinity") { return -Infinity; }
  return value;
}
process.stdout.write(JSON.stringify(context.__formValidation(JSON.parse(fs.readFileSync(0, "utf8"), reviveNonfinite))));
'''
        def encode_nonfinite(value: object) -> object:
            if isinstance(value, float) and not math.isfinite(value):
                kind = "nan" if math.isnan(value) else "negative-infinity" if value < 0 else "infinity"
                return {"__browser_nonfinite__": kind}
            if isinstance(value, dict):
                return {key: encode_nonfinite(item) for key, item in value.items()}
            if isinstance(value, list):
                return [encode_nonfinite(item) for item in value]
            return value

        completed = subprocess.run(
            ["node", "-e", script, str(HERE / "static" / "app.js")],
            input=json.dumps(encode_nonfinite(payload)),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_browser_vm_enforces_versioned_authored_field_contract(self) -> None:
        authored_fields = ("authored_dimensions", "authored_frames", "authored_landmarks")
        for format_name in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
        ):
            with self.subTest(format_name=format_name):
                valid = self.capsule_payload(format_name=format_name)
                self.assertEqual(self.browser_form_errors(valid), [])
                for field in authored_fields:
                    malformed = copy.deepcopy(valid)
                    malformed[field] = []
                    with self.subTest(field=field):
                        self.assertTrue(self.browser_form_errors(malformed))

        valid_v5 = self.capsule_payload(
            format_name=common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT
        )
        self.assertEqual(self.browser_form_errors(valid_v5), [])
        for field in ("authored_frames", "authored_landmarks"):
            malformed = copy.deepcopy(valid_v5)
            malformed[field] = []
            with self.subTest(format_name="v5", field=field):
                self.assertTrue(self.browser_form_errors(malformed))

        valid_v6 = self.capsule_payload(format_name=common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT)
        self.assertEqual(self.browser_form_errors(valid_v6), [])
        for field in authored_fields:
            malformed = copy.deepcopy(valid_v6)
            malformed.pop(field)
            with self.subTest(format_name="v6", field=field):
                self.assertTrue(self.browser_form_errors(malformed))

    def test_browser_vm_enforces_v7_torso_profile_index_contract(self) -> None:
        valid_v7 = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V7_FORMAT)
        self.assertEqual(self.browser_form_errors(valid_v7), [])

        composed_inversion = copy.deepcopy(valid_v7)
        upper_pelvis = next(
            landmark
            for landmark in composed_inversion["authored_landmarks"]
            if landmark["role"] == "form_torso_profile_upper_pelvis"
        )
        upper_pelvis["position"][1] = 0.95
        for variant in composed_inversion["variants"]:
            variant["torso_profile"]["sections"][1]["position"][1] = 0.95
        self.assertEqual(
            self.browser_form_errors(composed_inversion),
            [
                "Authored torso sections landmarks must have strictly increasing composed body-space y."
            ] * len(composed_inversion["variants"]),
        )

        cases = []
        unknown_envelope_field = copy.deepcopy(valid_v7)
        unknown_envelope_field["unexpected"] = True
        cases.append(unknown_envelope_field)
        wrong_format = copy.deepcopy(valid_v7)
        wrong_format["authored_torso_profile"]["format"] = "wrong"
        cases.append(wrong_format)
        wrong_order = copy.deepcopy(valid_v7)
        wrong_order["authored_torso_profile"]["sections"][0]["name"] = "upper-pelvis"
        cases.append(wrong_order)
        wrong_frame = copy.deepcopy(valid_v7)
        wrong_frame["authored_torso_profile"]["sections"][0]["frame_index"] = 2
        cases.append(wrong_frame)
        non_integer_index = copy.deepcopy(valid_v7)
        non_integer_index["authored_torso_profile"]["sections"][0]["landmark_index"] = 0.5
        cases.append(non_integer_index)
        non_axial = copy.deepcopy(valid_v7)
        non_axial["authored_landmarks"][0]["position"][0] = 0.1
        cases.append(non_axial)
        non_increasing_owner_local_y = copy.deepcopy(valid_v7)
        lower_abdomen = next(
            landmark
            for landmark in non_increasing_owner_local_y["authored_landmarks"]
            if landmark["role"] == "form_torso_profile_lower_abdomen"
        )
        waist_abdomen = next(
            landmark
            for landmark in non_increasing_owner_local_y["authored_landmarks"]
            if landmark["role"] == "form_torso_profile_waist_abdomen"
        )
        waist_abdomen["position"][1] = lower_abdomen["position"][1]
        for variant in non_increasing_owner_local_y["variants"]:
            waist_section = next(
                section
                for section in variant["torso_profile"]["sections"]
                if section["name"] == "waist-abdomen"
            )
            waist_section["position"][1] = lower_abdomen["position"][1]
        cases.append(non_increasing_owner_local_y)
        missing_dimension = copy.deepcopy(valid_v7)
        missing_dimension["authored_torso_profile"]["sections"][0]["dimension_indices"]["lateral"] = 0
        cases.append(missing_dimension)
        unknown_section_field = copy.deepcopy(valid_v7)
        unknown_section_field["authored_torso_profile"]["sections"][0]["radius"] = 1
        cases.append(unknown_section_field)
        wrong_position = copy.deepcopy(valid_v7)
        wrong_position["variants"][0]["torso_profile"]["sections"][0]["position"][1] += 0.1
        cases.append(wrong_position)
        wrong_factor = copy.deepcopy(valid_v7)
        wrong_factor["variants"][1]["torso_profile"]["sections"][0]["scaling"]["posterior_factor_permille"] = 1_149
        cases.append(wrong_factor)
        wrong_scaled_radius = copy.deepcopy(valid_v7)
        wrong_scaled_radius["variants"][3]["torso_profile"]["sections"][2]["posterior_radius_permille"] += 1
        cases.append(wrong_scaled_radius)
        unknown_variant_field = copy.deepcopy(valid_v7)
        unknown_variant_field["variants"][0]["torso_profile"]["unexpected"] = True
        cases.append(unknown_variant_field)

        for index, malformed in enumerate(cases):
            with self.subTest(index=index):
                self.assertTrue(self.browser_form_errors(malformed))

        for prior_format in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
        ):
            prior = self.capsule_payload(format_name=prior_format)
            prior["authored_torso_profile"] = copy.deepcopy(valid_v7["authored_torso_profile"])
            with self.subTest(prior_format=prior_format):
                self.assertTrue(self.browser_form_errors(prior))
            prior_variant = self.capsule_payload(format_name=prior_format)
            prior_variant["variants"][0]["torso_profile"] = copy.deepcopy(
                valid_v7["variants"][0]["torso_profile"]
            )
            with self.subTest(prior_variant_format=prior_format):
                self.assertTrue(self.browser_form_errors(prior_variant))

    def test_browser_vm_rejects_composed_torso_inputs_before_order_check(self) -> None:
        valid_v7 = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V7_FORMAT)

        missing_torso_owner = copy.deepcopy(valid_v7)
        for variant in missing_torso_owner["variants"]:
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if not (
                    descriptor["address"]["role"] == "torso"
                    and descriptor["address"]["anchors"] == []
                )
            ]

        invalid_torso_owner = copy.deepcopy(valid_v7)
        for variant in invalid_torso_owner["variants"]:
            torso = next(
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] == "torso"
                and descriptor["address"]["anchors"] == []
            )
            torso["reference_point"][1] = float("nan")

        nonfinite_source_position = copy.deepcopy(valid_v7)
        source_landmark = next(
            landmark
            for landmark in nonfinite_source_position["authored_landmarks"]
            if landmark["role"] == "form_torso_profile_lower_abdomen"
        )
        source_landmark["position"][1] = float("nan")

        missing_torso_tree = copy.deepcopy(valid_v7)
        for variant in missing_torso_tree["variants"]:
            pelvis_address = next(
                descriptor["address"]
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] == "pelvis"
            )
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] != "torso"
            ]
            for descriptor in variant["descriptors"]:
                if (
                    descriptor.get("parent")
                    and descriptor["parent"]["role"] == "torso"
                ):
                    descriptor["parent"] = copy.deepcopy(pelvis_address)
        neck = next(
            descriptor
            for descriptor in missing_torso_tree["variants"][0]["descriptors"]
            if descriptor["address"]["role"] == "neck"
            and descriptor["address"]["anchors"] == []
        )
        head = next(
            descriptor
            for descriptor in missing_torso_tree["variants"][0]["descriptors"]
            if descriptor["address"]["role"] == "head"
            and descriptor["address"]["anchors"] == []
        )
        missing_torso_tree["reference_scale"] = {
            "parent": copy.deepcopy(neck["address"]),
            "child": copy.deepcopy(head["address"]),
            "axis_delta": [
                head["reference_point"][axis] - neck["reference_point"][axis]
                for axis in range(3)
            ],
            "squared_length": sum(
                (head["reference_point"][axis] - neck["reference_point"][axis]) ** 2
                for axis in range(3)
            ),
            "source": "exact-containment-edge",
        }

        cases = [
            (missing_torso_owner, "descriptor parent is missing"),
            (invalid_torso_owner, "reference_point must be a finite signed-i64 vector"),
            (nonfinite_source_position, "position must be finite and within +/-1.0"),
            (missing_torso_tree, "Authored torso sections owner has no validated body-space placement"),
        ]
        for payload, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                errors = self.browser_form_errors(payload)
                self.assertTrue(errors)
                self.assertTrue(
                    any(expected_error in error for error in errors),
                    errors,
                )

    def test_browser_vm_enforces_v8_head_neck_profile_index_contract(self) -> None:
        valid_v8 = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V8_FORMAT)
        self.assertEqual(self.browser_form_errors(valid_v8), [])

        cases = []
        unknown_envelope_field = copy.deepcopy(valid_v8)
        unknown_envelope_field["unexpected"] = True
        cases.append(unknown_envelope_field)
        missing_head_profile = copy.deepcopy(valid_v8)
        missing_head_profile.pop("authored_head_neck_profile")
        cases.append(missing_head_profile)
        wrong_profile_format = copy.deepcopy(valid_v8)
        wrong_profile_format["authored_head_neck_profile"]["format"] = "wrong"
        cases.append(wrong_profile_format)
        wrong_connection = copy.deepcopy(valid_v8)
        wrong_connection["authored_head_neck_profile"]["connections"][0]["route"] = "wrong"
        cases.append(wrong_connection)
        wrong_order = copy.deepcopy(valid_v8)
        wrong_order["authored_head_neck_profile"]["sections"][0]["name"] = "neck-upper"
        cases.append(wrong_order)
        wrong_section_index = copy.deepcopy(valid_v8)
        wrong_section_index["authored_head_neck_profile"]["sections"][1]["section_index"] = 0
        cases.append(wrong_section_index)
        wrong_frame_index = copy.deepcopy(valid_v8)
        wrong_frame_index["authored_head_neck_profile"]["sections"][0]["frame_index"] = 0
        cases.append(wrong_frame_index)
        non_integer_landmark_index = copy.deepcopy(valid_v8)
        non_integer_landmark_index["authored_head_neck_profile"]["sections"][0]["landmark_index"] = 0.5
        cases.append(non_integer_landmark_index)
        non_axial = copy.deepcopy(valid_v8)
        non_axial["authored_landmarks"][valid_v8["authored_head_neck_profile"]["sections"][0]["landmark_index"]]["position"][0] = 0.1
        cases.append(non_axial)
        non_increasing_neck_y = copy.deepcopy(valid_v8)
        neck_sections = non_increasing_neck_y["authored_head_neck_profile"]["sections"]
        first_neck = neck_sections[0]["landmark_index"]
        second_neck = neck_sections[1]["landmark_index"]
        non_increasing_neck_y["authored_landmarks"][second_neck]["position"][1] = non_increasing_neck_y["authored_landmarks"][first_neck]["position"][1]
        cases.append(non_increasing_neck_y)
        muzzle_root_at_cranium_mid = copy.deepcopy(valid_v8)
        muzzle_sections = muzzle_root_at_cranium_mid["authored_head_neck_profile"]["sections"]
        cranium_mid = muzzle_sections[3]["landmark_index"]
        muzzle_root = muzzle_sections[5]["landmark_index"]
        muzzle_root_at_cranium_mid["authored_landmarks"][muzzle_root]["position"][2] = muzzle_root_at_cranium_mid["authored_landmarks"][cranium_mid]["position"][2]
        cases.append(muzzle_root_at_cranium_mid)
        muzzle_root_before_cranium_mid = copy.deepcopy(valid_v8)
        muzzle_sections = muzzle_root_before_cranium_mid["authored_head_neck_profile"]["sections"]
        cranium_mid = muzzle_sections[3]["landmark_index"]
        muzzle_root = muzzle_sections[5]["landmark_index"]
        muzzle_root_before_cranium_mid["authored_landmarks"][muzzle_root]["position"][2] = muzzle_root_before_cranium_mid["authored_landmarks"][cranium_mid]["position"][2] - 0.1
        cases.append(muzzle_root_before_cranium_mid)
        non_increasing_muzzle_z = copy.deepcopy(valid_v8)
        muzzle_sections = non_increasing_muzzle_z["authored_head_neck_profile"]["sections"]
        first_muzzle = muzzle_sections[5]["landmark_index"]
        second_muzzle = muzzle_sections[6]["landmark_index"]
        non_increasing_muzzle_z["authored_landmarks"][second_muzzle]["position"][2] = non_increasing_muzzle_z["authored_landmarks"][first_muzzle]["position"][2]
        cases.append(non_increasing_muzzle_z)
        wrong_dimension_index = copy.deepcopy(valid_v8)
        wrong_dimension_index["authored_head_neck_profile"]["sections"][0]["dimension_indices"]["up"] = 0
        cases.append(wrong_dimension_index)
        wrong_variant_position = copy.deepcopy(valid_v8)
        wrong_variant_position["variants"][0]["head_neck_profile"]["sections"][0]["position"][1] += 0.01
        cases.append(wrong_variant_position)
        wrong_variant_factor = copy.deepcopy(valid_v8)
        wrong_variant_factor["variants"][1]["head_neck_profile"]["sections"][2]["scaling"]["lateral_factor_permille"] = 1_201
        cases.append(wrong_variant_factor)
        wrong_scaled_radius = copy.deepcopy(valid_v8)
        wrong_scaled_radius["variants"][3]["head_neck_profile"]["sections"][2]["forward_radius_permille"] += 1
        cases.append(wrong_scaled_radius)
        unknown_variant_field = copy.deepcopy(valid_v8)
        unknown_variant_field["variants"][0]["head_neck_profile"]["extra"] = True
        cases.append(unknown_variant_field)
        for index, malformed in enumerate(cases):
            with self.subTest(index=index):
                self.assertTrue(self.browser_form_errors(malformed))

        for prior_format in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V5_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V6_FORMAT,
            common.PROVISIONAL_FORM_V7_FORMAT,
        ):
            prior = self.capsule_payload(format_name=prior_format)
            prior["authored_head_neck_profile"] = copy.deepcopy(valid_v8["authored_head_neck_profile"])
            with self.subTest(prior_format=prior_format):
                self.assertTrue(self.browser_form_errors(prior))
            prior_variant = self.capsule_payload(format_name=prior_format)
            prior_variant["variants"][0]["head_neck_profile"] = copy.deepcopy(
                valid_v8["variants"][0]["head_neck_profile"]
            )
            with self.subTest(prior_variant_format=prior_format):
                self.assertTrue(self.browser_form_errors(prior_variant))

    def test_browser_vm_matches_common_for_v8_geometry_and_scale_invariants(self) -> None:
        valid_v8 = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V8_FORMAT)
        self.assertEqual(self.browser_form_errors(valid_v8), [])

        def descriptor(payload: dict[str, object], role: str, anchors: list[str] | None = None) -> dict[str, object]:
            return next(
                item
                for item in payload["variants"][0]["descriptors"]
                if item["address"]["role"] == role
                and item["address"]["anchors"] == (anchors or [])
            )

        cases: list[tuple[str, dict[str, object]]] = []
        zero_squared_length = copy.deepcopy(valid_v8)
        zero_squared_length["reference_scale"]["squared_length"] = 0
        cases.append(("zero squared length", zero_squared_length))

        invalid_squared_length = copy.deepcopy(valid_v8)
        invalid_squared_length["reference_scale"]["squared_length"] = 2
        cases.append(("mismatched squared length", invalid_squared_length))

        nonfinite_scale = copy.deepcopy(valid_v8)
        nonfinite_scale["reference_scale"]["axis_delta"][0] = float("nan")
        cases.append(("non-finite reference-scale coordinate", nonfinite_scale))

        zero_extent = copy.deepcopy(valid_v8)
        descriptor(zero_extent, "pelvis")["shape"]["axis_extents_permille"][0] = 0
        cases.append(("zero ellipsoid extent", zero_extent))

        nonfinite_coordinate = copy.deepcopy(valid_v8)
        descriptor(nonfinite_coordinate, "pelvis")["reference_point"][0] = float("nan")
        cases.append(("non-finite descriptor coordinate", nonfinite_coordinate))

        center_mismatch = copy.deepcopy(valid_v8)
        descriptor(center_mismatch, "pelvis")["shape"]["center"][0] = 1
        cases.append(("ellipsoid center/reference mismatch", center_mismatch))

        malformed_segment_endpoint = copy.deepcopy(valid_v8)
        upper_arm = descriptor(malformed_segment_endpoint, "upper_arm", ["left"])
        upper_arm["shape"]["to"] = copy.deepcopy(upper_arm["shape"]["from"])
        cases.append(("malformed segment endpoints", malformed_segment_endpoint))

        nonfinite_segment_endpoint = copy.deepcopy(valid_v8)
        descriptor(nonfinite_segment_endpoint, "upper_arm", ["left"])["shape"]["from"][0] = float("nan")
        cases.append(("non-finite segment endpoint", nonfinite_segment_endpoint))

        zero_segment_radius = copy.deepcopy(valid_v8)
        descriptor(zero_segment_radius, "upper_arm", ["left"])["shape"]["radius_permille"] = 0
        cases.append(("zero segment radius", zero_segment_radius))

        empty_limitations = copy.deepcopy(valid_v8)
        empty_limitations["limitations"] = ""
        cases.append(("empty limitations", empty_limitations))

        unsupported_limitations = copy.deepcopy(valid_v8)
        unsupported_limitations["limitations"] = "display-only preview"
        cases.append(("unsupported limitations", unsupported_limitations))

        for label, malformed in cases:
            with self.subTest(case=label), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(malformed, f"malformed v8 {label}")
            with self.subTest(browser_case=label):
                self.assertTrue(self.browser_form_errors(malformed))

    def test_browser_vm_matches_common_for_v8_cranium_mid_to_muzzle_root_route(self) -> None:
        valid_v8 = self.capsule_payload(format_name=common.PROVISIONAL_FORM_V8_FORMAT)
        self.assertEqual(self.browser_form_errors(valid_v8), [])

        for label, offset in (("equal", 0.0), ("before", -0.1)):
            malformed = copy.deepcopy(valid_v8)
            sections = malformed["authored_head_neck_profile"]["sections"]
            cranium_mid = sections[3]["landmark_index"]
            muzzle_root = sections[5]["landmark_index"]
            malformed["authored_landmarks"][muzzle_root]["position"][2] = (
                malformed["authored_landmarks"][cranium_mid]["position"][2] + offset
            )
            with self.subTest(common_case=label), self.assertRaises(common.ValidationError):
                common._validate_provisional_form_envelope(
                    malformed, f"muzzle-root {label} cranium-mid z"
                )
            with self.subTest(browser_case=label):
                self.assertTrue(self.browser_form_errors(malformed))

    def test_current_rust_producer_passes_python_and_browser_validators(self) -> None:
        repository = HERE.parents[1]
        completed = subprocess.run(
            [
                "cargo",
                "run",
                "--quiet",
                "--package",
                "creature-kernel-cli",
                "--bin",
                "creature-kernel",
                "--",
                "inspect-provisional-form",
                "--input",
                "examples/body-documents/stylized-digitigrade-biped-authored-form.json",
            ],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
        )
        produced = json.loads(completed.stdout)
        validated = common._validate_provisional_form_envelope(
            produced, "current Rust producer output"
        )
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_V11_FORMAT)
        self.assertIn("authored_torso_profile", produced)
        self.assertIn("authored_head_neck_profile", produced)
        self.assertIn("authored_arm_profile", produced)
        self.assertIn("authored_leg_profile", produced)
        self.assertIn("authored_foot_profile", produced)
        for variant in produced["variants"]:
            self.assertIn("torso_profile", variant)
            self.assertIn("head_neck_profile", variant)
            self.assertIn("arm_profile", variant)
            self.assertIn("leg_profile", variant)
            self.assertIn("foot_profile", variant)
        self.assertEqual(self.browser_form_errors(produced), [])


if __name__ == "__main__":
    unittest.main()

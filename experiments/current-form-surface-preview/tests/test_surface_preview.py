from __future__ import annotations

import copy
import importlib.util
import json
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


def make_payload() -> dict[str, object]:
    def descriptor(role: str, point: list[int], parent: dict[str, object] | None, shape: dict[str, object], anchors: list[str] | None = None) -> dict[str, object]:
        return {"descriptor_kind": "display-only-form-descriptor", "address": address(role, anchors), "parent": parent, "placement_source": "authored-root" if parent is None else "authored-containment", "reference_point": point, "profile_id": "neutral-v0", "source": "profile-derived-display", "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2"}, "shape": shape}
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
    variants = []
    for variant_id in surface_preview.VARIANT_IDS:
        current = copy.deepcopy(descriptors)
        for item in current:
            item["profile_id"] = variant_id
            item["provenance"]["resource_profile_id"] = "ck.resource.body.r2"
        variants.append({"id": variant_id, "profile_id": variant_id, "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2"}, "descriptors": current})
    payload = {"format": surface_preview.SOURCE_FORMAT, "operation": "inspect-provisional-form", "status": "success", "stage": "provisional-form", "processing_complete": True, "diagnostics_complete": True, "diagnostics": [], "source": {"document": "test", "namespace": "main", "resource_profile_id": "ck.resource.body.r2"}, "reference_scale": {"parent": address("neck"), "child": address("head"), "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}, "variants": variants, "limitations": "Provisional display-only geometry descriptors; no production geometry or Readiness 3."}
    return payload


def make_varied_payload() -> dict[str, object]:
    payload = make_payload()
    factors = (1.0, 1.08, 0.92, 1.16)
    for variant, factor in zip(payload["variants"], factors):
        for item in variant["descriptors"]:
            shape = item["shape"]
            if shape["name"] == "ellipsoid":
                shape["axis_extents_permille"] = [max(1, round(value * factor)) for value in shape["axis_extents_permille"]]
            elif shape["name"] == "capsule":
                shape["radius_permille"] = max(1, round(shape["radius_permille"] * factor))
            else:
                shape["start_radius_permille"] = max(1, round(shape["start_radius_permille"] * factor))
                shape["end_radius_permille"] = max(1, round(shape["end_radius_permille"] * factor))
    return payload


class SurfacePreviewTests(unittest.TestCase):
    def test_validation_preserves_four_variants_and_full_keys(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual([x[0] for x in form.variants], list(surface_preview.VARIANT_IDS))
        self.assertIn(("main", ("left",), "part", "hand"), {x.key for x in form.variants[0][1]})

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
                {guide.head_guide.head_owner.key, guide.head_guide.neck_owner.key},
                {item.key for item in descriptors if item.key[3] in {"head", "neck"}},
            )
            self.assertTrue(all(item.joint_narrowing[-1] < 1.0 for item in guide.limb_guides))
            self.assertTrue(all(item.path_kind == "capsule" for item in guide.limb_guides))
            self.assertTrue(all(item.centerline[0] != item.centerline[1] for item in guide.limb_guides))
            for limb in guide.limb_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in (*limb.thickness_profile, *limb.joint_narrowing)))
            for paw in guide.paw_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in (*paw.radii, *paw.paw_radii)))
            for tail in guide.tail_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in (*tail.taper,)))
            geometry_signatures.append(
                (
                    guide.head_guide.cranium_radii,
                    tuple(item.thickness_profile for item in guide.limb_guides),
                    tuple(item.taper for item in guide.tail_guides),
                )
            )
            fields = surface_preview._compile_hybrid_guide(guide)
            owners_by_key = {descriptor.key: descriptor for descriptor in descriptors}
            self.assertEqual({field.owner.key for field in fields}, set(expected_keys))
            self.assertTrue(
                all(field.owner is owners_by_key[field.owner.key] for field in fields)
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
                self.assertEqual(left.radii, right.radii)
                self.assertEqual(left.paw_radii, right.paw_radii)
                self.assertAlmostEqual(left.paw_center[0], -right.paw_center[0])
                self.assertEqual(left.paw_center[1:], right.paw_center[1:])
            else:
                left = next(item for item in guide.limb_guides if item.source_key == left_key)
                right = next(item for item in guide.limb_guides if item.source_key == right_key)
                self.assertEqual(left.thickness_profile, right.thickness_profile)
                self.assertEqual(left.joint_narrowing, right.joint_narrowing)
                for left_point, right_point in zip(left.centerline, right.centerline):
                    self.assertAlmostEqual(left_point[0], -right_point[0])
                    self.assertEqual(left_point[1:], right_point[1:])

    def test_private_guides_reject_malformed_profile_and_consume_narrowing(self) -> None:
        import dataclasses

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        baseline = surface_preview._compile_hybrid_guide(guide)
        for limb in guide.limb_guides:
            baseline_field = next(
                item for item in baseline
                if item.owner is limb.owner and item.recipe == "limb-segment"
            )
            changed_limb = dataclasses.replace(limb, joint_narrowing=(0.60, 0.45))
            changed_guides = tuple(changed_limb if item is limb else item for item in guide.limb_guides)
            changed = surface_preview._compile_hybrid_guide(
                dataclasses.replace(guide, limb_guides=changed_guides)
            )
            changed_field = next(
                item for item in changed
                if item.owner is limb.owner and item.recipe == "limb-segment"
            )
            self.assertLess(float(changed_field.shape["r0"]), float(baseline_field.shape["r0"]))
            self.assertLess(float(changed_field.shape["r1"]), float(baseline_field.shape["r1"]))
        for limb in guide.limb_guides:
            malformed = dataclasses.replace(limb, joint_narrowing=(0.0, 0.45))
            malformed_guides = tuple(malformed if item is limb else item for item in guide.limb_guides)
            with self.assertRaises(surface_preview.PreviewError):
                surface_preview._compile_hybrid_guide(
                    dataclasses.replace(guide, limb_guides=malformed_guides)
                )
        for limb in guide.limb_guides:
            malformed = dataclasses.replace(limb, joint_narrowing=(0.60, 1.1))
            malformed_guides = tuple(malformed if item is limb else item for item in guide.limb_guides)
            with self.assertRaises(surface_preview.PreviewError):
                surface_preview._compile_hybrid_guide(
                    dataclasses.replace(guide, limb_guides=malformed_guides)
                )

    def test_role_recipes_anchor_limbs_and_expand_head_and_paw(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        fields = surface_preview._compound_fields(form, descriptors)
        source_keys = {descriptor.key for descriptor in descriptors}
        self.assertTrue(fields)
        self.assertTrue(all(field.owner.key in source_keys for field in fields))
        expected_recipes = {
            "hips", "pelvic-core", "chest", "waist", "axial-trunk",
            "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
            "limb-segment", "root-bridge", "hip-transition", "shoulder-mass", "joint-collar", "digitigrade-lower-leg",
            "paw-mass", "foot-front", "extremity-bridge", "tail-segment", "tail-tip-extension", "tail-tip-cap", "tail-root-bridge",
            "tail-root-collar",
        }
        self.assertEqual({field.recipe for field in fields}, expected_recipes)
        self.assertEqual(len(fields), 50)

        pelvis = next(item for item in descriptors if item.key[3] == "pelvis")
        torso = next(item for item in descriptors if item.key[3] == "torso")
        trunk = next(item for item in fields if item.owner is torso and item.recipe == "axial-trunk")
        pelvis_shape = surface_preview._source_shape(pelvis, form.reference_scale)
        torso_shape = surface_preview._source_shape(torso, form.reference_scale)
        np.testing.assert_allclose(
            trunk.shape["from"],
            surface_preview._parent_surface_anchor(pelvis, torso.point, form.reference_scale),
        )
        np.testing.assert_allclose(
            trunk.shape["to"],
            torso_shape["center"] - np.asarray([0.0, 0.55 * torso_shape["radii"][1], 0.0]),
        )
        self.assertAlmostEqual(float(trunk.shape["r0"]), 0.70 * float(pelvis_shape["radii"][0]), places=12)
        self.assertAlmostEqual(float(trunk.shape["r1"]), 0.68 * float(torso_shape["radii"][0]), places=12)
        self.assertIs(trunk.owner, torso)

        upper_arm = next(item for item in descriptors if item.key[3] == "upper_arm")
        bridge = next(item for item in fields if item.owner is upper_arm and item.recipe == "root-bridge")
        torso = next(item for item in descriptors if item.key[3] == "torso")
        self.assertFalse((bridge.shape["from"] == torso.point).all(), "limb bridge must not start at torso centre")
        self.assertTrue((bridge.shape["to"] == surface_preview._source_shape(upper_arm, form.reference_scale)["from"]).all())
        shoulder = next(item for item in fields if item.owner is upper_arm and item.recipe == "shoulder-mass")
        upper_arm_shape = surface_preview._source_shape(upper_arm, form.reference_scale)
        upper_arm_radius = surface_preview._radius_from_shape(upper_arm_shape)
        np.testing.assert_allclose(
            shoulder.shape["center"],
            upper_arm_shape["from"] + np.asarray([0.0, -0.20 * upper_arm_radius, 0.0]),
        )
        np.testing.assert_allclose(
            shoulder.shape["radii"],
            upper_arm_radius * np.asarray([1.30, 1.55, 1.55]),
        )
        self.assertIs(shoulder.owner, upper_arm)
        left_upper_arm = next(
            item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "upper_arm"
        )
        right_upper_arm = next(
            item for item in descriptors if item.key[1] == ("right",) and item.key[3] == "upper_arm"
        )
        left_shoulder = next(item for item in fields if item.owner is left_upper_arm and item.recipe == "shoulder-mass")
        right_shoulder = next(item for item in fields if item.owner is right_upper_arm and item.recipe == "shoulder-mass")
        np.testing.assert_allclose(left_shoulder.shape["center"][[1, 2]], right_shoulder.shape["center"][[1, 2]])
        self.assertAlmostEqual(float(left_shoulder.shape["center"][0]), -float(right_shoulder.shape["center"][0]))
        self.assertEqual(
            [item.recipe for item in fields if item.owner is left_upper_arm],
            ["limb-segment", "root-bridge", "shoulder-mass", "joint-collar"],
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
        np.testing.assert_allclose(
            left_hip.shape["from"],
            surface_preview._parent_surface_anchor(pelvis, left_thigh_shape["from"], form.reference_scale),
        )
        np.testing.assert_allclose(
            left_hip.shape["to"],
            left_thigh_shape["from"] + 0.35 * (left_thigh_shape["to"] - left_thigh_shape["from"]),
        )
        self.assertAlmostEqual(float(left_hip.shape["r0"]), 1.25 * thigh_radius, places=12)
        self.assertAlmostEqual(float(left_hip.shape["r1"]), 1.15 * thigh_radius, places=12)
        self.assertIs(left_hip.owner, left_thigh)
        np.testing.assert_allclose(left_hip.shape["from"][[1, 2]], right_hip.shape["from"][[1, 2]])
        np.testing.assert_allclose(left_hip.shape["to"][[1, 2]], right_hip.shape["to"][[1, 2]])
        self.assertAlmostEqual(float(left_hip.shape["from"][0]), -float(right_hip.shape["from"][0]))
        self.assertAlmostEqual(float(left_hip.shape["to"][0]), -float(right_hip.shape["to"][0]))
        self.assertEqual(
            [item.recipe for item in fields if item.owner is left_thigh],
            ["limb-segment", "root-bridge", "hip-transition", "joint-collar"],
        )

        forearm = next(
            item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "forearm"
        )
        self.assertEqual(
            [item.recipe for item in fields if item.owner is forearm],
            ["limb-segment"],
        )

        torso_shape = surface_preview._source_shape(torso, form.reference_scale)
        chest = next(item for item in fields if item.owner is torso and item.recipe == "chest")
        np.testing.assert_allclose(
            chest.shape["radii"],
            torso_shape["radii"] * np.asarray([0.92, 0.70, 1.02]),
        )

        hand = next(item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "hand")
        paw = next(item for item in fields if item.owner is hand and item.recipe == "paw-mass")
        source_hand = surface_preview._source_shape(hand, form.reference_scale)
        self.assertGreater(float(paw.shape["radii"][2]), float(source_hand["radii"][2]))
        hand_bridge = next(item for item in fields if item.owner is hand and item.recipe == "extremity-bridge")
        forearm = next(item for item in descriptors if item.key == hand.parent)
        hand_anchor_value = surface_preview._field(hand_bridge.shape["from"].reshape(1, 3), forearm, form.reference_scale)[0]
        self.assertAlmostEqual(float(hand_anchor_value), 0.0, places=12)

        foot = next(item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "foot")
        foot_shape = surface_preview._source_shape(foot, form.reference_scale)
        foot_pad = next(item for item in fields if item.owner is foot and item.recipe == "paw-mass")
        foot_front = next(item for item in fields if item.owner is foot and item.recipe == "foot-front")
        np.testing.assert_allclose(
            foot_pad.shape["center"],
            foot_shape["center"] + np.asarray([0.0, -0.12 * foot_shape["radii"][1], -0.12 * foot_shape["radii"][2]]),
        )
        np.testing.assert_allclose(
            foot_pad.shape["radii"],
            foot_shape["radii"] * np.asarray([1.15, 0.62, 0.62]),
        )
        np.testing.assert_allclose(
            foot_front.shape["center"],
            foot_shape["center"] + np.asarray([0.0, -0.16 * foot_shape["radii"][1], 0.52 * foot_shape["radii"][2]]),
        )
        np.testing.assert_allclose(
            foot_front.shape["radii"],
            foot_shape["radii"] * np.asarray([1.18, 0.50, 0.50]),
        )
        foot_bridge = next(item for item in fields if item.owner is foot and item.recipe == "extremity-bridge")
        shin = next(item for item in descriptors if item.key == foot.parent)
        foot_anchor_value = surface_preview._field(foot_bridge.shape["from"].reshape(1, 3), shin, form.reference_scale)[0]
        self.assertAlmostEqual(float(foot_anchor_value), 0.0, places=12)

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

    def test_candidate_c_craniofacial_ratios_overlap_and_source_ownership(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        descriptors = form.variants[0][1]
        fields = surface_preview._compound_fields(form, descriptors)
        head = next(item for item in descriptors if item.key[3] == "head")
        neck = next(item for item in descriptors if item.key[3] == "neck")
        head_shape = surface_preview._source_shape(head, form.reference_scale)
        hx, hy, hz = head_shape["radii"]
        cranium = next(item for item in fields if item.owner is head and item.recipe == "cranium")
        muzzle = next(item for item in fields if item.owner is head and item.recipe == "muzzle")
        head_base = next(item for item in fields if item.owner is head and item.recipe == "head-base-bridge")
        tapered_neck = next(item for item in fields if item.owner is neck and item.recipe == "tapered-neck")

        np.testing.assert_allclose(cranium.shape["center"], head.point + np.asarray([0.0, 0.10 * hy, -0.04 * hz]))
        np.testing.assert_allclose(cranium.shape["radii"], np.asarray([0.85 * hx, 1.00 * hy, 0.85 * hz]))
        np.testing.assert_allclose(muzzle.shape["center"], head.point + np.asarray([0.0, -0.10 * hy, 0.62 * hz]))
        np.testing.assert_allclose(muzzle.shape["radii"], np.asarray([0.50 * hx, 0.48 * hy, 0.50 * hz]))
        self.assertAlmostEqual(
            float(head_base.shape["to"][1]),
            float(cranium.shape["center"][1] - 0.84 * cranium.shape["radii"][1]),
            places=12,
        )
        self.assertAlmostEqual(float(tapered_neck.shape["to"][1]), float(head.point[1] - 0.70 * hy), places=12)

        cranium_bottom = float(cranium.shape["center"][1] - cranium.shape["radii"][1])
        cranium_top = float(cranium.shape["center"][1] + cranium.shape["radii"][1])
        muzzle_bottom = float(muzzle.shape["center"][1] - muzzle.shape["radii"][1])
        muzzle_top = float(muzzle.shape["center"][1] + muzzle.shape["radii"][1])
        self.assertLess(muzzle_bottom, cranium_top)
        self.assertGreater(muzzle_top, cranium_bottom)
        self.assertEqual(len(fields), 50)
        source_keys = {descriptor.key for descriptor in descriptors}
        self.assertTrue(all(field.owner.key in source_keys for field in fields))

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
        recipe_signature = [(field.owner.key, field.recipe) for field in first]
        for _, variant_descriptors, _ in form.variants[1:]:
            self.assertEqual(recipe_signature, [(field.owner.key, field.recipe) for field in surface_preview._compound_fields(form, variant_descriptors)])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            input_path.write_bytes(surface_preview._canonical(make_payload()))
            output = root / "output"
            surface_preview.generate(input_path, output, samples=24, padding=0.5)
            manifest = json.loads((output / "surface-preview-manifest.json").read_text())
            metrics = manifest["variants"][0]["metrics"]
            self.assertEqual(metrics["source_descriptor_count"], 18)
            self.assertEqual(metrics["generated_field_count"], 50)
            self.assertEqual(metrics["field_memory_values"], metrics["generated_field_count"] * 24**3)
            source_keys = {json.dumps(field.owner.key, default=list) for field in first}
            winner_keys = {json.dumps(tuple((item["namespace"], tuple(item["anchors"]), item["kind"], item["role"])), default=list) for item in metrics["winner_addresses"]}
            self.assertTrue(winner_keys <= source_keys)

    def test_output_is_deterministic_and_has_exact_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); input_path = root / "input.json"; input_path.write_bytes(surface_preview._canonical(make_payload()))
            first = root / "first"; second = root / "second"
            surface_preview.generate(input_path, first, samples=24, padding=0.5)
            surface_preview.generate(input_path, second, samples=24, padding=0.5)
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
            self.assertTrue(all(x["metrics"]["generated_field_count"] == 50 for x in manifest["variants"]))
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
            manifest = surface_preview.generate(input_path, output, samples=32, padding=0.5)
            self.assertEqual([item["name"] for item in manifest["projections"]], ["front", "side", "three-quarter"])
            self.assertEqual(manifest["canvas"], {"width": 1800, "height": 570, "mode": "RGB"})
            self.assertEqual(manifest["layout"]["panel_order"], [
                "front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin",
            ])
            expected_bounds = manifest["shared_render_bounds"]
            grid_signatures = []
            guide_controls = []
            for variant in manifest["variants"]:
                grid_signatures.append((tuple(variant["grid"]["bounds_min"]), tuple(variant["grid"]["bounds_max"]), tuple(variant["grid"]["spacing"])))
                regional = json.loads((output / variant["id"] / "regional-guide.json").read_text())
                self.assertEqual(regional["variant"], variant["id"])
                self.assertEqual(regional["shared_render_bounds"], expected_bounds)
                self.assertEqual(regional["counts"], {"owners": 18, "axial": 2, "head": 1, "limbs": 8, "paws": 4, "tails": 2, "centerlines": 17})
                self.assertEqual([item["name"] for item in regional["projections"]], ["front", "side", "three-quarter"])
                self.assertEqual(regional["layout"], manifest["layout"])
                self.assertEqual(regional["canvas"], manifest["canvas"])
                self.assertTrue(regional["controls"]["axial"])
                self.assertTrue(regional["controls"]["limbs"])
                self.assertTrue(regional["controls"]["paws"])
                self.assertTrue(regional["controls"]["tails"])
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
            direct_form = surface_preview.validate_envelope(make_varied_payload())
            for variant_id, (_, descriptors, _) in zip(surface_preview.VARIANT_IDS, direct_form.variants):
                _, _, _, _, direct_metrics, direct_grid = surface_preview.build_variant(
                    direct_form, descriptors, 32, 0.5, surface_preview.DEFAULT_SMOOTH_K,
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

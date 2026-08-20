from __future__ import annotations

import copy
import dataclasses
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
            self.assertTrue(all(item.joint is None or item.joint.radii[0] < min(item.joint.adjacent_profiles) for item in guide.limb_guides))
            self.assertTrue(all(len(item.sections) == 2 and all(section.path_kind == "capsule" for section in item.sections) for item in guide.limb_guides))
            self.assertTrue(all(section.centerline[0] != section.centerline[1] for item in guide.limb_guides for section in item.sections))
            for limb in guide.limb_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in limb.profile_controls))
            for paw in guide.paw_guides:
                self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in paw.paw_radii))
                if paw.heel_radii is not None:
                    self.assertTrue(all(np.isfinite(value) and value > 0.0 for value in paw.heel_radii))
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
                self.assertEqual(left.paw_radii, right.paw_radii)
                self.assertEqual(left.heel_radii, right.heel_radii)
                self.assertAlmostEqual(left.paw_center[0], -right.paw_center[0])
                self.assertEqual(left.paw_center[1:], right.paw_center[1:])
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
            changed_frame = dataclasses.replace(frame, central_profile=(frame.central_profile[0] * 1.17, frame.central_profile[1] * 1.17))
            changed_fields = surface_preview._compile_hybrid_guide(dataclasses.replace(guide, shoulder_frame=changed_frame))

            def jsonable(value: object) -> object:
                if isinstance(value, np.ndarray):
                    return value.tolist()
                if isinstance(value, dict):
                    return {key: jsonable(item) for key, item in value.items()}
                if isinstance(value, (tuple, list)):
                    return [jsonable(item) for item in value]
                return value

            self.assertEqual(
                tuple((item.owner.key, item.recipe, jsonable(item.shape)) for item in baseline_fields),
                tuple((item.owner.key, item.recipe, jsonable(item.shape)) for item in changed_fields),
            )
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
                self.assertEqual(side.shoulder_extremum, limb.root_centerline[0])  # type: ignore[index]
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
        with self.assertRaises(surface_preview.PreviewError):
            surface_preview._validate_hybrid_guide(dataclasses.replace(guide, shoulder_frame=dataclasses.replace(frame, sides=(bad_side, frame.right))))

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
                assert paw.heel_center is not None and paw.heel_radii is not None
                assert paw.forefoot_center is not None and paw.forefoot_radii is not None
                self.assertGreater(paw.forefoot_center[2], paw.heel_center[2])
                self.assertGreater(paw.forefoot_radii[0], paw.heel_radii[0])
                self.assertLess(paw.forefoot_radii[1], paw.heel_radii[1])
                attachment = next(item for item in fields if item.owner is paw.owner and item.recipe == "extremity-bridge")
                shin = by_role[(paw.owner.key[1], "shin")]
                self.assertEqual(tuple(attachment.shape["from"]), tuple(surface_preview._source_shape(shin, form.reference_scale)["to"]))
                self.assertEqual(tuple(attachment.shape["to"]), paw.heel_center)
                self.assertEqual([item.recipe for item in fields if item.owner is paw.owner], ["heel", "forefoot", "extremity-bridge"])
            else:
                self.assertIsNone(paw.heel_center)
                self.assertEqual([item.recipe for item in fields if item.owner is paw.owner], ["paw", "extremity-bridge"])

    def test_private_guides_reject_malformed_profile_and_consume_piecewise_sections(self) -> None:
        import dataclasses

        form = surface_preview.validate_envelope(make_payload())
        guide = surface_preview._derive_hybrid_guides(form, form.variants[0][1])
        baseline = surface_preview._compile_hybrid_guide(guide)
        for limb in guide.limb_guides:
            baseline_field = next(item for item in baseline if item.owner is limb.owner and item.recipe.endswith("-pre-joint") or item.owner is limb.owner and item.recipe.endswith("-proximal"))
            first_section = limb.sections[0]
            changed_section = dataclasses.replace(first_section, thickness=(first_section.thickness[0] * 0.60, first_section.thickness[1] * 0.45))
            changed_limb = dataclasses.replace(limb, sections=(changed_section, limb.sections[1]))
            changed_guides = tuple(changed_limb if item is limb else item for item in guide.limb_guides)
            changed = surface_preview._compile_hybrid_guide(
                dataclasses.replace(guide, limb_guides=changed_guides)
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
                    for value in (section.lateral_radius, section.depth_radius)
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
            self.assertTrue(np.all((lateral[1:] / lateral[:-1] >= 0.80) & (lateral[1:] / lateral[:-1] <= 1.20)))
            self.assertTrue(np.all((depth[1:] / depth[:-1] >= 0.80) & (depth[1:] / depth[:-1] <= 1.20)))
            # The abdomen has a genuinely flat short waist band rather than
            # one sharp local minimum. Its neighbors still taper and widen.
            np.testing.assert_allclose(lateral[2:5], lateral[2])
            np.testing.assert_allclose(depth[2:5], depth[2])
            self.assertLess(float(lateral[2]), float(lateral[1]))
            self.assertGreater(float(lateral[5]), float(lateral[4]))
            self.assertLess(float(lateral[5] / lateral[4]), 1.12)
            topologies.append(
                tuple((section.name, section.owner.key) for section in cage.sections)
            )
            dimensions.append(
                tuple((section.lateral_radius, section.depth_radius) for section in cage.sections)
            )
        self.assertEqual(topologies, [topologies[0]] * len(form.variants))
        self.assertGreater(len(set(dimensions)), 1)

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
        for item in payload["variants"][0]["descriptors"]:
            role = item["address"]["role"]
            if role == "pelvis":
                item["shape"]["axis_extents_permille"] = [1700, 5000, 900]
            elif role == "torso":
                item["shape"]["axis_extents_permille"] = [1650, 2, 900]
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
            "paw", "heel", "forefoot", "extremity-bridge", "tail-segment", "tail-tip-extension", "tail-tip-cap", "tail-root-bridge",
            "tail-root-collar",
        }
        self.assertEqual({field.recipe for field in fields}, expected_recipes)
        self.assertEqual(len(fields), 50)

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
        torso_cage = surface_preview._derive_hybrid_guides(form, descriptors).torso_cage
        left_upper_arm = next(
            item for item in descriptors if item.key[1] == ("left",) and item.key[3] == "upper_arm"
        )
        right_upper_arm = next(
            item for item in descriptors if item.key[1] == ("right",) and item.key[3] == "upper_arm"
        )
        self.assertEqual(
            [item.recipe for item in fields if item.owner is left_upper_arm],
            ["upper_arm-pre-joint", "upper_arm-joint", "root-bridge", "elbow"],
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
            surface_preview._torso_cage_boundary_anchor(
                torso_cage,
                float(neck.point[1]),
                np.asarray(neck.point) - np.asarray(torso_cage.upper_boundary.center),
            ),
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
        foot_shape = surface_preview._source_shape(foot, form.reference_scale)
        foot_pad = next(item for item in fields if item.owner is foot and item.recipe == "heel")
        foot_front = next(item for item in fields if item.owner is foot and item.recipe == "forefoot")
        np.testing.assert_allclose(
            foot_pad.shape["center"],
            foot_shape["center"] + np.asarray([0.0, -0.08 * foot_shape["radii"][1], -0.20 * foot_shape["radii"][2]]),
        )
        np.testing.assert_allclose(
            foot_pad.shape["radii"],
            foot_shape["radii"] * np.asarray([1.02, 0.68, 0.78]),
        )
        np.testing.assert_allclose(
            foot_front.shape["center"],
            foot_shape["center"] + np.asarray([0.0, -0.18 * foot_shape["radii"][1], 0.38 * foot_shape["radii"][2]]),
        )
        np.testing.assert_allclose(
            foot_front.shape["radii"],
            foot_shape["radii"] * np.asarray([1.30, 0.42, 0.82]),
        )
        foot_bridge = next(item for item in fields if item.owner is foot and item.recipe == "extremity-bridge")
        shin = next(item for item in descriptors if item.key == foot.parent)
        np.testing.assert_allclose(foot_bridge.shape["from"], surface_preview._source_shape(shin, form.reference_scale)["to"])
        self.assertEqual(foot_bridge.shape["to"].tolist(), foot_pad.shape["center"].tolist())

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
        self.assertEqual(
            [(field.owner.key[1], field.owner.key[3], field.recipe) for field in first],
            [
                ((), "head", "cranium"), ((), "head", "muzzle"), ((), "head", "head-base-bridge"),
                ((), "neck", "tapered-neck"), ((), "neck", "neck-collar"), ((), "torso", "torso-cage"),
                (("left",), "foot", "heel"), (("left",), "foot", "forefoot"), (("left",), "foot", "extremity-bridge"),
                (("left",), "forearm", "forearm-proximal"), (("left",), "forearm", "forearm-distal"),
                (("left",), "hand", "paw"), (("left",), "hand", "extremity-bridge"),
                (("left",), "shin", "shin-pre-joint"), (("left",), "shin", "shin-joint"), (("left",), "shin", "hock"),
                (("left",), "thigh", "thigh-pre-joint"), (("left",), "thigh", "thigh-joint"),
                (("left",), "thigh", "root-bridge"), (("left",), "thigh", "hip-transition"),
                (("left",), "thigh", "knee"),
                (("left",), "upper_arm", "upper_arm-pre-joint"), (("left",), "upper_arm", "upper_arm-joint"),
                (("left",), "upper_arm", "root-bridge"), (("left",), "upper_arm", "elbow"),
                (("right",), "foot", "heel"), (("right",), "foot", "forefoot"), (("right",), "foot", "extremity-bridge"),
                (("right",), "forearm", "forearm-proximal"), (("right",), "forearm", "forearm-distal"),
                (("right",), "hand", "paw"), (("right",), "hand", "extremity-bridge"),
                (("right",), "shin", "shin-pre-joint"), (("right",), "shin", "shin-joint"), (("right",), "shin", "hock"),
                (("right",), "thigh", "thigh-pre-joint"), (("right",), "thigh", "thigh-joint"),
                (("right",), "thigh", "root-bridge"), (("right",), "thigh", "hip-transition"),
                (("right",), "thigh", "knee"),
                (("right",), "upper_arm", "upper_arm-pre-joint"), (("right",), "upper_arm", "upper_arm-joint"),
                (("right",), "upper_arm", "root-bridge"), (("right",), "upper_arm", "elbow"),
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
            self.assertEqual(metrics["generated_field_count"], 50)
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
                self.assertEqual(regional["counts"]["compiled_fields"], 50)
                self.assertEqual(regional["counts"]["compiled_field_recipe_counts"], {
                    "upper_arm-pre-joint": 2, "upper_arm-joint": 2, "forearm-proximal": 2, "forearm-distal": 2,
                    "thigh-pre-joint": 2, "thigh-joint": 2, "shin-pre-joint": 2, "shin-joint": 2,
                    "elbow": 2, "knee": 2, "hock": 2, "paw": 2, "heel": 2, "forefoot": 2,
                    "extremity-bridge": 4, "root-bridge": 4, "hip-transition": 2,
                    "tail-segment": 2, "cranium": 1,
                    "muzzle": 1, "head-base-bridge": 1, "tapered-neck": 1,
                    "neck-collar": 1, "torso-cage": 1,
                    "tail-root-bridge": 1, "tail-root-collar": 1,
                    "tail-tip-extension": 1, "tail-tip-cap": 1,
                })
                self.assertEqual([item["name"] for item in regional["projections"]], ["front", "side", "three-quarter"])
                self.assertEqual(regional["layout"], manifest["layout"])
                self.assertEqual(regional["canvas"], manifest["canvas"])
                self.assertTrue(regional["controls"]["axial"])
                self.assertTrue(regional["controls"]["torso_cage"])
                self.assertTrue(regional["controls"]["limbs"])
                self.assertTrue(regional["controls"]["paws"])
                self.assertTrue(regional["controls"]["tails"])
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
                self.assertEqual({item["control"] for item in next(item for item in regional["controls"]["paws"] if item["owner"]["role"] == "foot")["masses"]}, {"heel", "forefoot"})
                hand_control = next(item for item in regional["controls"]["paws"] if item["owner"]["role"] == "hand")
                self.assertEqual(hand_control["attachment_source"]["owner"]["role"], "forearm")
                self.assertEqual(hand_control["attachment_source"]["anchor"], "forearm-distal-boundary")
                foot_control = next(item for item in regional["controls"]["paws"] if item["owner"]["role"] == "foot")
                self.assertEqual(foot_control["attachment_source"]["owner"]["role"], "shin")
                self.assertEqual(foot_control["attachment_source"]["anchor"], "hock-endpoint")
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

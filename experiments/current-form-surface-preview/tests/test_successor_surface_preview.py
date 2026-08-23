from __future__ import annotations

import importlib.util
import hashlib
import json
import math
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SPEC = importlib.util.spec_from_file_location("successor_fixture", Path(__file__).with_name("test_surface_preview.py"))
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
fixture = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixture)
sys.path.insert(0, str(ROOT))
import surface_preview  # noqa: E402
import successor_surface_preview as successor  # noqa: E402


def _native_temporary_directory() -> tempfile.TemporaryDirectory:
    """Keep Linux publication tests on a filesystem with renameat2 support."""

    native_root = "/tmp" if sys.platform.startswith("linux") else None
    return tempfile.TemporaryDirectory(dir=native_root)


def _serialized_torso_section_controls(region: successor.SuccessorRegion) -> list[dict[str, object]]:
    """Give generator test doubles the same source-authored controls as real meshes."""

    return [
        {
            "name": section.name,
            "owner": surface_preview._address_json(section.owner.key),
            "center": [float(value) for value in section.center],
            "axial_position": float(section.axial_position if section.axial_position is not None else section.path_length),
            "lateral_radius": float(section.cardinal_radii[0]),
            "anterior_radius": float(section.cardinal_radii[1]),
            "posterior_radius": float(section.cardinal_radii[2]),
        }
        for section in region.loft.sections
    ]


class _TestOwner:
    def __init__(self, label: str) -> None:
        self.key = ("test", (label,), "part", label)


def _test_profile_sweep(transform: tuple[np.ndarray, np.ndarray] | None = None) -> successor._ProfileSweep:
    owners = (_TestOwner("lower"), _TestOwner("middle"), _TestOwner("upper"))
    centers = np.asarray(((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 2.0, 0.0)))
    tangent = np.asarray((0.0, 1.0, 0.0))
    first = np.asarray((1.0, 0.0, 0.0))
    second = np.asarray((0.0, 0.0, 1.0))
    if transform is not None:
        rotation, translation = transform
        centers = centers @ rotation.T + translation
        tangent = tangent @ rotation.T
        first = first @ rotation.T
        second = second @ rotation.T
    sections = tuple(
        successor._ProfileSection(
            name,
            owner,
            tuple(center),
            tuple(tangent),
            (tuple(first), tuple(second)),
            radii,
            float(index),
        )
        for index, (name, owner, center, radii) in enumerate(zip(
            ("lower", "middle", "upper"), owners, centers, ((1.0, 0.5), (0.8, 0.4), (0.6, 0.3))
        ))
    )
    caps = (
        successor._ProfileEndpointCap("start", sections[0].center, tuple(-value for value in sections[0].tangent), sections[0].transverse_axes, sections[0].transverse_radii, 0.5),
        successor._ProfileEndpointCap("end", sections[-1].center, sections[-1].tangent, sections[-1].transverse_axes, sections[-1].transverse_radii, 0.3),
    )
    return successor._ProfileSweep(sections, caps)


def _bent_test_profile_sweep() -> successor._ProfileSweep:
    owner = _TestOwner("bent")
    centers = ((-1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    expected_tangents = ((1.0, 0.0, 0.0), (2.0 ** -0.5, 2.0 ** -0.5, 0.0), (0.0, 1.0, 0.0))
    sections = tuple(
        successor._ProfileSection(
            name=f"bend-{index}", owner=owner, center=center, tangent=tangent,
            transverse_axes=(
                tuple(successor._frame_from_tangent(np.asarray(tangent), np.asarray((0.0, 0.0, 1.0)), np.asarray((0.0, 1.0, 0.0)), f"test-bend[{index}]")[1]),
                tuple(successor._frame_from_tangent(np.asarray(tangent), np.asarray((0.0, 0.0, 1.0)), np.asarray((0.0, 1.0, 0.0)), f"test-bend[{index}]")[2]),
            ),
            transverse_radii=(0.4, 0.4), path_length=float(index),
        )
        for index, (center, tangent) in enumerate(zip(centers, expected_tangents))
    )
    caps = (
        successor._ProfileEndpointCap("start", sections[0].center, tuple(-value for value in sections[0].tangent), sections[0].transverse_axes, sections[0].transverse_radii, 0.4),
        successor._ProfileEndpointCap("end", sections[-1].center, sections[-1].tangent, sections[-1].transverse_axes, sections[-1].transverse_radii, 0.4),
    )
    return successor._ProfileSweep(sections, caps)


def _test_torso_profile_sweep(transform: tuple[np.ndarray, np.ndarray] | None = None) -> successor._ProfileSweep:
    """Build a v7-shaped seven-section guide without fixture dependencies."""

    pelvis = _TestOwner("pelvis")
    torso = _TestOwner("torso")
    centers = np.asarray(tuple((0.0, float(index), 0.0) for index in range(7)), dtype=np.float64)
    axes = np.asarray(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), dtype=np.float64)
    if transform is not None:
        rotation, translation = transform
        centers = centers @ rotation.T + translation
        axes = axes @ rotation.T
    guide_axes = SimpleNamespace(
        lateral=tuple(axes[0]),
        up=tuple(axes[1]),
        forward=tuple(axes[2]),
    )
    cardinal_radii = (
        (1.00, 0.70, 0.95),
        (1.10, 0.78, 0.90),
        (1.25, 0.88, 1.00),
        (1.18, 0.96, 0.82),
        (1.30, 1.10, 0.86),
        (1.42, 1.16, 0.92),
        (1.34, 1.24, 0.88),
    )
    source_sections = tuple(
        SimpleNamespace(
            name=name,
            owner=pelvis if index < 2 else torso,
            center=tuple(centers[index]),
            lateral_radius=profile[0],
            anterior_radius=profile[1],
            posterior_radius=profile[2],
        )
        for index, (name, profile) in enumerate(zip(
            (
                "lower-pelvis", "upper-pelvis", "lower-abdomen", "waist-abdomen",
                "upper-abdomen", "lower-ribcage", "upper-ribcage-shoulder",
            ),
            cardinal_radii,
        ))
    )
    guide = SimpleNamespace(
        torso_cage=SimpleNamespace(
            sections=source_sections,
            axes=guide_axes,
            pelvis_owner=pelvis,
            torso_owner=torso,
        ),
        topology=SimpleNamespace(axes=guide_axes),
    )
    return successor._make_profile_sweep(guide)


def _rotated_between_sections_profile_sweep() -> successor._ProfileSweep:
    owner = _TestOwner("rotated-frame")
    angle = np.pi / 4.0
    left_axes = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    right_axes = ((float(np.cos(angle)), 0.0, float(np.sin(angle))), (-float(np.sin(angle)), 0.0, float(np.cos(angle))))
    sections = (
        successor._ProfileSection("left", owner, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), left_axes, (1.0, 0.8), 0.0),
        successor._ProfileSection("right", owner, (0.0, 1.0, 0.0), (0.0, 1.0, 0.0), right_axes, (1.0, 0.8), 1.0),
    )
    caps = (
        successor._ProfileEndpointCap("start", sections[0].center, (0.0, -1.0, 0.0), left_axes, sections[0].transverse_radii, 0.8),
        successor._ProfileEndpointCap("end", sections[-1].center, (0.0, 1.0, 0.0), right_axes, sections[-1].transverse_radii, 0.8),
    )
    return successor._ProfileSweep(sections, caps)


_HEAD_NECK_AXIS_INDEX = {"lateral": 0, "up": 1, "forward": 2}


def _mutate_head_neck_radius(
    guide: object,
    section_index: int,
    axis: str,
    factor: float = 1.37,
) -> object:
    """Make one otherwise-valid successor guide with derived connections."""

    profile = guide.head_guide.profile  # type: ignore[attr-defined]
    sections = list(profile.sections)
    source = sections[section_index]
    radii = list(source.radii)
    radii[_HEAD_NECK_AXIS_INDEX[axis]] *= factor
    sections[section_index] = replace(source, radii=tuple(radii))
    rebuilt_connections = []
    for connection in profile.connections:
        from_section = sections[connection.spec.from_section_index]
        to_section = sections[connection.spec.to_section_index]
        rebuilt_connections.append(replace(
            connection,
            from_section=from_section,
            to_section=to_section,
            centerline=(from_section.center, to_section.center),
            thickness=(min(from_section.radii), min(to_section.radii)),
        ))
    changed_profile = replace(profile, sections=tuple(sections), connections=tuple(rebuilt_connections))
    return replace(guide, head_guide=replace(guide.head_guide, profile=changed_profile))  # type: ignore[attr-defined]


def _head_neck_route_signature(
    route: successor._RegionalProfileSweep,
    source_profile: object,
    axes: object,
) -> np.ndarray:
    """Capture direct route-field, station-volume, and bound observables."""

    probes = []
    for section in route.sweep.sections:
        source = source_profile.sections[section.source_section_index]
        center = np.asarray(section.center, dtype=np.float64)
        probes.extend(
            center + 0.5 * source.radii[index] * np.asarray(getattr(axes, axis), dtype=np.float64)
            for axis, index in _HEAD_NECK_AXIS_INDEX.items()
        )
    points = np.asarray(probes, dtype=np.float64)
    station_values = np.concatenate(
        tuple(
            successor._profile_station_volume_field(
                points[index:index + 3],
                route.sweep.sections[index // 3],
            )
            for index in range(0, len(points), 3)
        )
    )
    route_values = successor._profile_sweep_field(points, route.sweep)
    lower, upper = successor._profile_sweep_bounds(route.sweep)
    return np.concatenate((route_values, station_values, lower, upper))


_ARM_AXIS_INDEX = {"lateral": 0, "up": 1, "forward": 2}


def _mutate_arm_profile_radius(
    guide: object,
    side_index: int,
    station_index: int,
    axis: str,
    factor: float = 1.37,
) -> object:
    """Make a guide-valid-for-the-successor arm radius perturbation."""

    profile = guide.arm_profile  # type: ignore[attr-defined]
    sides = list(profile.sides)
    side = sides[side_index]
    stations = list(side.sections)
    source = stations[station_index]
    lineage_name = ("lateral_lineage", "up_lineage", "forward_lineage")[_ARM_AXIS_INDEX[axis]]
    lineage = getattr(source, lineage_name)
    base = max(1, int(round(lineage.base * factor)))
    scaled = base * lineage.factor // 1000
    changed_lineage = replace(lineage, base=base, scaled=scaled)
    radii = list(source.radii)
    radii[_ARM_AXIS_INDEX[axis]] = scaled / 1000.0
    stations[station_index] = replace(
        source,
        radii=tuple(radii),
        **{lineage_name: changed_lineage},
    )
    sides[side_index] = replace(side, sections=tuple(stations))
    return replace(guide, arm_profile=replace(profile, sides=tuple(sides)))  # type: ignore[attr-defined]


def _arm_route_signature(routes: tuple[successor._LimbChainSweep, ...], guide: object) -> np.ndarray:
    """Capture route and full authored station-volume observables."""

    axes = guide.topology.axes  # type: ignore[attr-defined]
    guide_axes = tuple(np.asarray(getattr(axes, axis), dtype=np.float64) for axis in ("lateral", "up", "forward"))
    profile_sides = {side.side: side for side in guide.arm_profile.sides}  # type: ignore[attr-defined]
    probes = []
    station_values = []
    for route in routes:
        for station, section in zip(route.source_stations, route.sweep.sections):
            side_name = route.chain_name.split("-", 1)[0]
            baseline_station = profile_sides[side_name].sections[station.source_section_index]
            center = np.asarray(baseline_station.center, dtype=np.float64)
            probes.extend(
                center + 0.55 * float(baseline_station.radii[index]) * guide_axes[index]
                for index in range(3)
            )
            station_values.extend(
                successor._profile_station_volume_field(
                    np.asarray((point,), dtype=np.float64), section,
                )[0]
                for point in probes[-3:]
            )
    route_values = np.concatenate(tuple(successor._profile_sweep_field(np.asarray(probes), route.sweep) for route in routes))
    return np.concatenate((route_values, np.asarray(station_values, dtype=np.float64)))


class SuccessorTorsoProfileNumericalTests(unittest.TestCase):
    def test_torso_profile_hits_exact_cardinals_and_has_finite_outside_caps(self) -> None:
        sweep = _test_torso_profile_sweep()
        for section in sweep.sections:
            center = np.asarray(section.center, dtype=np.float64)
            lateral_axis, forward_axis = (np.asarray(axis, dtype=np.float64) for axis in section.transverse_axes)
            lateral, anterior, posterior = section.cardinal_radii
            cardinal_points = np.asarray((
                center + lateral * lateral_axis,
                center - lateral * lateral_axis,
                center + anterior * forward_axis,
                center - posterior * forward_axis,
            ))
            np.testing.assert_allclose(successor._loft_field(cardinal_points, sweep), 0.0, rtol=0.0, atol=1.0e-12)

        start, end = sweep.sections[0], sweep.sections[-1]
        outside = np.asarray((
            np.asarray(start.center) + 2.0 * sweep.endpoint_caps[0].axial_radius * np.asarray(sweep.endpoint_caps[0].outward_tangent),
            np.asarray(end.center) + 2.0 * sweep.endpoint_caps[1].axial_radius * np.asarray(sweep.endpoint_caps[1].outward_tangent),
            (0.0, 3.0, 12.0),
            (12.0, 3.0, 0.0),
        ), dtype=np.float64)
        values = successor._loft_field(outside, sweep)
        self.assertTrue(np.all(np.isfinite(values)))
        self.assertTrue(np.all(values > 0.0))

    def test_torso_profile_is_shape_preserving_asymmetric_and_non_elliptical(self) -> None:
        sweep = _test_torso_profile_sweep()
        path = np.asarray([section.path_length for section in sweep.sections], dtype=np.float64)
        controls = np.asarray([section.cardinal_radii for section in sweep.sections], dtype=np.float64)
        slopes = successor._shape_preserving_slopes(path, controls)
        for index in range(len(path) - 1):
            samples = np.linspace(path[index], path[index + 1], 17)
            interpolated = successor._shape_preserving_sample(path, controls, slopes, samples)
            lower = np.minimum(controls[index], controls[index + 1]) - 1.0e-12
            upper = np.maximum(controls[index], controls[index + 1]) + 1.0e-12
            self.assertTrue(np.all(interpolated >= lower))
            self.assertTrue(np.all(interpolated <= upper))

        section = sweep.sections[4]
        center = np.asarray(section.center, dtype=np.float64)
        lateral_axis, forward_axis = (np.asarray(axis, dtype=np.float64) for axis in section.transverse_axes)
        lateral, anterior, posterior = section.cardinal_radii
        front = successor._loft_field((center + 0.8 * anterior * forward_axis).reshape(1, 3), sweep)[0]
        back = successor._loft_field((center - 0.8 * anterior * forward_axis).reshape(1, 3), sweep)[0]
        self.assertNotAlmostEqual(float(front), float(back), places=10)

        rounded_point = center + 0.75 * lateral * lateral_axis + 0.75 * anterior * forward_axis
        rounded_value = float(successor._loft_field(rounded_point.reshape(1, 3), sweep)[0])
        ellipse_value = (math.sqrt(0.75**2 + 0.75**2) - 1.0) * min(lateral, anterior, posterior)
        self.assertLess(rounded_value, ellipse_value - 1.0e-3)

    def test_torso_profile_is_invariant_under_fixed_frame_rotation_and_translation(self) -> None:
        angle_x, angle_y = 0.31, -0.47
        rx = np.asarray(((1.0, 0.0, 0.0), (0.0, math.cos(angle_x), -math.sin(angle_x)), (0.0, math.sin(angle_x), math.cos(angle_x))))
        ry = np.asarray(((math.cos(angle_y), 0.0, math.sin(angle_y)), (0.0, 1.0, 0.0), (-math.sin(angle_y), 0.0, math.cos(angle_y))))
        rotation = ry @ rx
        translation = np.asarray((2.5, -1.25, 0.75), dtype=np.float64)
        original = _test_torso_profile_sweep()
        transformed = _test_torso_profile_sweep((rotation, translation))
        points = np.asarray(((0.2, 0.6, 0.1), (0.9, 2.5, -0.35), (-1.0, 4.4, 0.55), (0.1, 6.7, 0.0)))
        np.testing.assert_allclose(
            successor._loft_field(points @ rotation.T + translation, transformed),
            successor._loft_field(points, original),
            rtol=0.0,
            atol=1.0e-11,
        )


class SuccessorSurfacePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.form = surface_preview.validate_envelope(fixture.make_varied_payload())

    def test_successor_consumes_authored_five_section_shoulder_envelopes(self) -> None:
        expected_names = (
            "torso-interior", "torso-boundary", "authored-shoulder",
            "upper-arm-socket", "upper-arm-midpoint",
        )
        expected_depths = {
            "neutral-v0": (350, 1000, 0.350),
            "broad-soft-v0": (402, 1150, 0.402),
            "lean-readable-v0": (280, 800, 0.280),
            "depth-forward-v0": (350, 1000, 0.350),
        }
        for variant_id, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            self.assertEqual(region.consumer_id, successor.CONSUMER_ID)
            self.assertEqual(region.region_id, successor.SUCCESSOR_REGION_ID)
            self.assertEqual(tuple(item.recipe for item in region.shoulder_sweeps), (
                "left-shoulder-envelope", "right-shoulder-envelope",
            ))
            self.assertEqual(len(region.shoulder_sweeps), 2)
            upper_arms = {
                item.owner.key[1][0]: item
                for item in guide.limb_guides
                if item.owner.key[3] == "upper_arm"
            }
            arms = {item.chain_name: item for item in region.arm_sweeps}
            for shoulder, side in zip(region.shoulder_sweeps, guide.shoulder_frame.sides):
                sections = shoulder.sweep.sections
                self.assertEqual(shoulder.side, side.side)
                self.assertEqual(shoulder.sweep.names, expected_names)
                self.assertEqual(tuple(section.owner.key[3] for section in sections), (
                    "torso", "torso", "upper_arm", "upper_arm", "upper_arm",
                ))
                self.assertIs(sections[0].owner, guide.shoulder_frame.torso_owner)
                self.assertIs(sections[1].owner, guide.shoulder_frame.torso_owner)
                self.assertIs(sections[2].owner, side.owner)
                self.assertIs(sections[3].owner, side.owner)
                self.assertIs(sections[4].owner, side.owner)

                authored_center = 0.5 * (
                    np.asarray(side.peak_anchor, dtype=np.float64)
                    + np.asarray(side.axilla_anchor, dtype=np.float64)
                )
                np.testing.assert_allclose(sections[2].center, authored_center, rtol=0.0, atol=1.0e-12)
                self.assertEqual(
                    sections[2].transverse_radii,
                    (side.vertical_radius, side.depth_radius),
                )
                expected_depth, expected_factor, expected_radius = expected_depths[variant_id]
                self.assertEqual(side.depth_scaled_permille, expected_depth)
                self.assertEqual(side.depth_profile_factor, expected_factor)
                self.assertAlmostEqual(side.depth_radius, expected_radius, places=12)

                boundary_value = float(successor._loft_field(
                    np.asarray(sections[1].center, dtype=np.float64).reshape(1, 3),
                    region.loft,
                )[0])
                interior_value = float(successor._loft_field(
                    np.asarray(sections[0].center, dtype=np.float64).reshape(1, 3),
                    region.loft,
                )[0])
                self.assertLessEqual(abs(boundary_value), successor._SHOULDER_BOUNDARY_TOLERANCE)
                self.assertLess(interior_value, 0.0)

                upper = upper_arms[side.side]
                self.assertEqual(sections[3].center, upper.sections[0].centerline[0])
                self.assertEqual(sections[4].center, upper.sections[0].centerline[1])
                upper_sweep = arms[f"{side.side}-upper-arm-route"].sweep.sections
                for shoulder_section, arm_section in zip(sections[3:], upper_sweep[:2]):
                    np.testing.assert_array_equal(shoulder_section.center, arm_section.center)
                    self.assertLessEqual(
                        float(successor._profile_sweep_field(
                            np.asarray(arm_section.center).reshape(1, 3),
                            arms[f"{side.side}-upper-arm-route"].sweep,
                        )[0]),
                        0.0,
                    )
                for section in sections[3:]:
                    probe = np.asarray(section.center, dtype=np.float64).reshape(1, 3)
                    self.assertLessEqual(
                        float(successor._profile_sweep_field(probe, arms[f"{side.side}-upper-arm-route"].sweep)[0]),
                        0.0,
                    )

            self.assertEqual(len(region.bridge_fields), 4)
            self.assertEqual(sum(field.recipe == "root-bridge" for field in region.bridge_fields), 2)
            self.assertEqual(sum(field.recipe == "hip-transition" for field in region.bridge_fields), 2)
            self.assertEqual(
                {field.owner.key[3] for field in region.bridge_fields if field.recipe == "root-bridge"},
                {"thigh"},
            )
            self.assertFalse(any(field.recipe == "deltoid-sweep-1" for field in region.bridge_fields))
            self.assertFalse(any(
                field.recipe == "root-bridge" and field.owner.key[3] == "upper_arm"
                for field in region.bridge_fields
            ))
            self.assertFalse(any(
                component.recipe.startswith("successor-shoulder-")
                and "deltoid" in component.recipe
                for component in successor._make_components(region, successor.DEFAULT_SMOOTH_K)
            ))

    def test_shoulder_finite_span_evaluator_is_bounded_and_fail_closed(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        region = successor.compile_successor_region(guide)
        shoulder = region.shoulder_sweeps[0]
        remote_points = np.asarray((
            (8.0, 3.0, 0.0), (-8.0, 3.0, 0.0),
            (0.0, 8.0, 0.0), (0.0, -4.0, 0.0),
            (0.0, 3.0, 8.0), (0.0, 3.0, -8.0),
        ), dtype=np.float64)
        remote_values = successor._shoulder_sweep_field(remote_points, shoulder)
        self.assertTrue(np.all(np.isfinite(remote_values)))
        self.assertTrue(np.all(remote_values > 0.0))

        malformed_sections = list(shoulder.sweep.sections)
        malformed_sections[1] = replace(
            malformed_sections[1],
            center=malformed_sections[0].center,
        )
        malformed_sweep = replace(shoulder.sweep, sections=tuple(malformed_sections))
        cases = {
            "degenerate-section": replace(shoulder, sweep=malformed_sweep),
            "zero-preferred-frame": replace(
                shoulder,
                preferred_up=(0.0, 0.0, 0.0),
                preferred_forward=(0.0, 0.0, 0.0),
            ),
        }
        for name, malformed in cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._shoulder_sweep_field(remote_points, malformed)

    def test_shoulder_underarm_probe_remains_continuous_and_bounded(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            for shoulder, side in zip(region.shoulder_sweeps, guide.shoulder_frame.sides):
                authored = np.asarray(shoulder.sweep.sections[2].center, dtype=np.float64)
                socket = np.asarray(shoulder.sweep.sections[3].center, dtype=np.float64)
                underarm = np.asarray(side.axilla_anchor, dtype=np.float64)
                points = np.vstack((
                    np.linspace(authored, socket, 17),
                    underarm,
                    underarm + np.asarray(side.axes.forward, dtype=np.float64) * side.depth_radius,
                    underarm - np.asarray(side.axes.forward, dtype=np.float64) * side.depth_radius,
                ))
                values = successor._shoulder_sweep_field(points, shoulder)
                self.assertTrue(np.all(np.isfinite(values)))
                centerline_values = values[:17]
                flank_values = values[17:]
                self.assertTrue(np.all(centerline_values < 0.0))
                self.assertLess(float(np.max(centerline_values)), -1.0e-3)
                self.assertLess(float(np.max(np.abs(np.diff(centerline_values)))), 0.05)
                self.assertLess(
                    float(np.max(np.abs(flank_values))),
                    max(0.25, side.depth_radius),
                )

    def test_torso_profile_rebinds_five_section_shoulder_attachment_probes(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            self.assertEqual(region.loft.profile_operation, successor.TORSO_PROFILE_OPERATION)
            for section in region.loft.sections:
                center = np.asarray(section.center, dtype=np.float64)
                lateral_axis, forward_axis = (np.asarray(axis, dtype=np.float64) for axis in section.transverse_axes)
                lateral, anterior, posterior = section.cardinal_radii
                probes = np.asarray((
                    center + lateral * lateral_axis,
                    center - lateral * lateral_axis,
                    center + anterior * forward_axis,
                    center - posterior * forward_axis,
                ))
                probe_values = successor._loft_field(probes, region.loft)
                self.assertTrue(
                    np.all(probe_values <= successor._SHOULDER_BOUNDARY_TOLERANCE),
                    msg=f"torso station probes escaped the continuous sweep: {probe_values!r}",
                )

            for shoulder, side in zip(region.shoulder_sweeps, guide.shoulder_frame.sides):
                interior = np.asarray(shoulder.sweep.sections[0].center, dtype=np.float64)
                boundary = np.asarray(shoulder.sweep.sections[1].center, dtype=np.float64)
                self.assertLess(float(successor._loft_field(interior.reshape(1, 3), region.loft)[0]), 0.0)
                self.assertLessEqual(abs(float(successor._loft_field(boundary.reshape(1, 3), region.loft)[0])), successor._SHOULDER_BOUNDARY_TOLERANCE)
                self.assertIs(shoulder.sweep.sections[0].owner, guide.shoulder_frame.torso_owner)
                self.assertIs(shoulder.sweep.sections[1].owner, guide.shoulder_frame.torso_owner)
                upper_arm = next(item for item in region.arm_sweeps if item.chain_name == f"{side.side}-upper-arm-route")
                np.testing.assert_array_equal(shoulder.sweep.sections[3].center, upper_arm.sweep.sections[0].center)
                np.testing.assert_array_equal(shoulder.sweep.sections[4].center, upper_arm.sweep.sections[1].center)
                remote = np.asarray(((8.0, 3.0, 0.0), (-8.0, 3.0, 0.0), (0.0, 8.0, 0.0), (0.0, -4.0, 0.0)))
                remote_values = successor._shoulder_sweep_field(remote, shoulder)
                self.assertTrue(np.all(np.isfinite(remote_values)))
                self.assertTrue(np.all(remote_values > 0.0))

            center = np.asarray(region.loft.sections[3].center, dtype=np.float64)
            lateral_axis = np.asarray(region.loft.sections[3].transverse_axes[0], dtype=np.float64)
            probe = center + 0.6 * lateral_axis
            mirrored = center - 0.6 * lateral_axis
            np.testing.assert_allclose(
                successor._loft_field(np.asarray((probe, mirrored)), region.loft)[0],
                successor._loft_field(np.asarray((probe, mirrored)), region.loft)[1],
                rtol=0.0,
                atol=1.0e-12,
            )

    def test_extremity_sweeps_have_shared_order_topology_and_exact_caps(self) -> None:
        expected_order = (
            "left-hand-attachment", "left-hand-paw", "left-foot",
            "right-hand-attachment", "right-hand-paw", "right-foot",
        )
        expected_kinds = (
            "hand-attachment", "hand-paw", "foot-chain",
            "hand-attachment", "hand-paw", "foot-chain",
        )
        expected_names = {
            "hand-attachment": ("hand-attachment-start", "hand-attachment-end"),
            "hand-paw": ("hand-paw-base", "hand-paw-palm", "hand-paw-knuckle", "hand-paw-tip"),
            "foot-chain": ("hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe"),
        }
        expected_counts = {"hand-attachment": 2, "hand-paw": 4, "foot-chain": 5}
        expected_roles = {
            "hand-attachment": ("hand", "hand"),
            "hand-paw": ("hand", "hand", "hand", "hand"),
            "foot-chain": ("shin", "foot", "foot", "foot", "foot"),
        }
        topologies = []
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
            self.assertEqual(tuple(item.name for item in region.extremity_sweeps), expected_order)
            self.assertEqual(tuple(item.kind for item in region.extremity_sweeps), expected_kinds)
            for item in region.extremity_sweeps:
                self.assertEqual(item.section_names, expected_names[item.kind])
                self.assertEqual(item.sections_consumed, expected_counts[item.kind])
                self.assertEqual(
                    tuple(section.owner.key[3] for section in item.sweep.sections),
                    expected_roles[item.kind],
                )
                self.assertTrue(all(source_by_key.get(owner.key) is owner for owner in item.sweep.owners))
                self.assertEqual(len(item.sweep.endpoint_caps), 2)
                self.assertEqual(tuple(cap.side for cap in item.sweep.endpoint_caps), ("start", "end"))
                if item.kind == "foot-chain":
                    self.assertEqual(tuple(transition.section_index for transition in item.sweep.internal_transitions), (2,))
                    self.assertEqual(item.sweep.internal_transitions[0].owner.key[3], "foot")
                else:
                    self.assertEqual(item.sweep.internal_transitions, ())
            topologies.append(
                (
                    tuple(item.name for item in region.extremity_sweeps),
                    tuple(item.sections_consumed for item in region.extremity_sweeps),
                    tuple(len(item.sweep.internal_transitions) for item in region.extremity_sweeps),
                )
            )
        self.assertEqual(len(set(topologies)), 1)

    def test_every_authored_arm_station_and_radius_changes_a_route_observable(self) -> None:
        for variant_id, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            baseline = successor._make_arm_profile_sweeps(guide)
            baseline_by_name = {item.chain_name: item for item in baseline}
            for side_index, side in enumerate(guide.arm_profile.sides):
                for station_index, station in enumerate(side.sections):
                    affected = {
                        f"{side.side}-upper-arm-route" if station_index <= 2 else f"{side.side}-forearm-route"
                    }
                    if station_index == 2:
                        affected = {f"{side.side}-upper-arm-route", f"{side.side}-forearm-route"}
                    for axis in _ARM_AXIS_INDEX:
                        with self.subTest(variant=variant_id, station=station.name, axis=axis):
                            changed = successor._make_arm_profile_sweeps(
                                _mutate_arm_profile_radius(guide, side_index, station_index, axis)
                            )
                            changed_by_name = {item.chain_name: item for item in changed}
                            self.assertEqual(set(changed_by_name), set(baseline_by_name))
                            differences = {
                                name: float(np.max(np.abs(
                                    _arm_route_signature((changed_by_name[name],), guide)
                                    - _arm_route_signature((baseline_by_name[name],), guide)
                                )))
                                for name in affected
                            }
                            self.assertTrue(
                                any(value > 1.0e-8 for value in differences.values()),
                                msg=f"{station.name}.{axis} did not affect its authored route: {differences!r}",
                            )

    def test_arm_profile_perturbation_is_one_sided_and_routes_remain_shared(self) -> None:
        guide = surface_preview._derive_hybrid_guides(self.form, self.form.variants[0][1])
        baseline = successor._make_arm_profile_sweeps(guide)
        changed = successor._make_arm_profile_sweeps(_mutate_arm_profile_radius(guide, 0, 1, "forward"))
        baseline_right = tuple(item for item in baseline if item.chain_name.startswith("right-"))
        changed_right = tuple(item for item in changed if item.chain_name.startswith("right-"))
        np.testing.assert_array_equal(
            _arm_route_signature(changed_right, guide),
            _arm_route_signature(baseline_right, guide),
        )
        self.assertGreater(
            float(np.max(np.abs(
                _arm_route_signature(tuple(item for item in changed if item.chain_name.startswith("left-")), guide)
                - _arm_route_signature(tuple(item for item in baseline if item.chain_name.startswith("left-")), guide)
            ))),
            1.0e-8,
        )

    def test_malformed_arm_profile_guide_is_rejected_fail_closed(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        profile = guide.arm_profile
        left = profile.sides[0]
        malformed_station = replace(left.sections[2], name="renamed-elbow")
        malformed_side = replace(left, sections=left.sections[:2] + (malformed_station,) + left.sections[3:])
        wrong_axes = replace(profile, axes=replace(profile.axes, up=(0.0, 0.0, 1.0)))
        bad_lineage = replace(
            left.sections[1],
            forward_lineage=replace(left.sections[1].forward_lineage, reference_index=999),
        )
        bad_lineage_side = replace(left, sections=left.sections[:1] + (bad_lineage,) + left.sections[2:])
        cases = (
            replace(guide, arm_profile=replace(profile, sides=(malformed_side, profile.sides[1]))),
            replace(guide, arm_profile=wrong_axes),
            replace(guide, arm_profile=replace(profile, sides=(bad_lineage_side, profile.sides[1]))),
        )
        for invalid in cases:
            with self.assertRaises(successor.SuccessorPreviewError):
                successor._make_arm_profile_sweeps(invalid)

    def test_hand_sweeps_retain_exact_guide_controls_and_forearm_overlap(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            paws = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.paw_guides}
            arms = {item.chain_name: item for item in region.arm_sweeps}
            for item in region.hand_sweeps:
                side = item.side
                hand = paws[(side, "hand")]
                arm = arms[f"{side}-forearm-route"]
                self.assertEqual(hand.owner.parent, arm.sweep.sections[-1].owner.key)
                self.assertIs(item.sweep.sections[0].owner, hand.owner)
                if item.kind == "hand-attachment":
                    self.assertEqual(item.section_names, ("hand-attachment-start", "hand-attachment-end"))
                    np.testing.assert_array_equal(item.sweep.sections[0].center, hand.attachment_centerline[0])
                    np.testing.assert_array_equal(item.sweep.sections[-1].center, hand.attachment_centerline[1])
                    self.assertEqual(
                        tuple(section.transverse_radii for section in item.sweep.sections),
                        ((hand.attachment_radius, hand.attachment_radius),) * 2,
                    )
                else:
                    self.assertEqual(item.section_names, successor._HAND_PAW_SECTION_NAMES)
                    outward = np.asarray(hand.axes.lateral, dtype=np.float64) * (-1.0 if side == "left" else 1.0)
                    outward /= np.linalg.norm(outward)
                    for section, control in zip(item.sweep.sections, successor._HAND_PAW_PROFILE):
                        expected_center = np.asarray(hand.paw_center) + control[0] * hand.paw_radii[0] * outward
                        np.testing.assert_array_equal(section.center, expected_center)
                        self.assertEqual(
                            section.transverse_radii,
                            (hand.paw_radii[1] * control[1], hand.paw_radii[2] * control[2]),
                        )
                        np.testing.assert_array_equal(section.tangent, outward)
                        self.assertEqual(
                            section.transverse_axes,
                            (tuple(hand.axes.up), tuple(hand.axes.forward)),
                        )
                    paw_center = np.asarray(hand.paw_center).reshape(1, 3)
                    self.assertLess(float(successor._profile_sweep_field(paw_center, item.sweep)[0]), 0.0)
                forearm_end = np.asarray(arm.sweep.sections[-1].center).reshape(1, 3)
                self.assertLess(float(successor._profile_sweep_field(forearm_end, item.sweep)[0]), 0.0)

    def test_foot_sweeps_retain_exact_chain_controls_and_forward_contact_order(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            paws = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.paw_guides}
            legs = {item.chain_name: item for item in region.limb_sweeps}
            for item in region.foot_sweeps:
                side = item.side
                paw = paws[(side, "foot")]
                chain = paw.foot_chain
                leg = legs[f"{side}-leg"]
                sections = item.sweep.sections
                self.assertEqual(item.source_owners, (leg.sweep.sections[-1].owner, paw.owner))
                self.assertEqual(tuple(section.owner for section in sections), item.source_owners[:1] + (paw.owner,) * 4)
                self.assertEqual(sections[0].owner.key, leg.sweep.sections[-1].owner.key)
                np.testing.assert_array_equal(sections[0].center, chain.hock_anchor)
                np.testing.assert_array_equal(sections[0].center, chain.metatarsal_centerline[0])
                expected_centers = (
                    chain.hock_anchor,
                    tuple(0.5 * (np.asarray(chain.metatarsal_centerline[0]) + np.asarray(chain.metatarsal_centerline[1]))),
                    chain.pad_center,
                    tuple(0.5 * (np.asarray(chain.pad_center) + np.asarray(chain.toe_center))),
                    chain.toe_center,
                )
                expected_radii = (
                    tuple(chain.hock_radii[:2]),
                    (sum(chain.metatarsal_profile) * 0.5,) * 2,
                    tuple(chain.pad_radii[:2]),
                    tuple(0.5 * (np.asarray(chain.pad_radii[:2]) + np.asarray(chain.toe_radii[:2]))),
                    tuple(chain.toe_radii[:2]),
                )
                for section, center, radii in zip(sections, expected_centers, expected_radii):
                    np.testing.assert_array_equal(section.center, center)
                    self.assertEqual(section.transverse_radii, radii)
                self.assertGreater(sections[-1].center[2], sections[2].center[2])
                self.assertLess(chain.contact_height, sections[2].center[1])

    def test_extremity_tail_replacement_and_bridge_inventory_is_exact(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        region = successor.compile_successor_region(guide, baseline)
        self.assertEqual(len(baseline), 52)
        self.assertEqual(len(region.bridge_fields), 4)
        self.assertEqual(len(baseline) - len(region.bridge_fields), 48)
        self.assertEqual(len(region.replaced_baseline_recipes), 28)
        self.assertEqual(sum(field.recipe in region.replaced_baseline_recipes for field in baseline), 46)
        self.assertEqual(
            sum(field.recipe in successor._EXTREMITY_BASELINE_RECIPES for field in baseline),
            10,
        )
        self.assertEqual(
            {field.recipe for field in region.bridge_fields},
            {"root-bridge", "hip-transition"},
        )
        self.assertEqual(sum(field.recipe == "root-bridge" for field in region.bridge_fields), 2)
        self.assertEqual(sum(field.recipe == "hip-transition" for field in region.bridge_fields), 2)
        self.assertEqual(
            {field.owner.key[3] for field in region.bridge_fields if field.recipe == "root-bridge"},
            {"thigh"},
        )
        self.assertEqual(sum(field.recipe in successor._TAIL_BASELINE_RECIPES for field in baseline), 6)
        self.assertFalse(any(field.recipe in successor._TAIL_BASELINE_RECIPES for field in region.bridge_fields))
        self.assertNotIn("paw", {field.recipe for field in region.bridge_fields})
        self.assertNotIn("metatarsal", {field.recipe for field in region.bridge_fields})
        self.assertNotIn("paw-pad", {field.recipe for field in region.bridge_fields})
        self.assertNotIn("toe-box", {field.recipe for field in region.bridge_fields})
        self.assertFalse(
            {component.recipe for component in successor._make_components(region, successor.DEFAULT_SMOOTH_K)}
            & set(successor._EXTREMITY_BASELINE_RECIPES)
        )

    def test_tail_successor_elements_retain_exact_controls_joins_and_mass_bounds(self) -> None:
        expected_names = (
            "tail-root-source", "tail-root-attachment", "tail-root-collar",
            "tail-tip-source", "tail-tip-extension", "tail-tip-cap",
        )
        expected_kinds = (
            "source-centerline", "root-attachment", "root-collar-mass",
            "source-centerline", "tip-extension", "tip-cap-mass",
        )
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            root, tip = guide.tail_guides
            elements = region.tail_elements
            self.assertEqual(tuple(item.name for item in elements), expected_names)
            self.assertEqual(tuple(item.kind for item in elements), expected_kinds)
            self.assertEqual(tuple(item.owner.key[3] for item in elements), (
                "tail_root", "tail_root", "tail_root", "tail_tip", "tail_tip", "tail_tip",
            ))
            for item, owner in zip(elements[:3], (root.owner,) * 3):
                self.assertIs(item.owner, owner)
                self.assertTrue(all(section.owner is owner for section in item.sweep.sections))
            for item, owner in zip(elements[3:], (tip.owner,) * 3):
                self.assertIs(item.owner, owner)
                self.assertTrue(all(section.owner is owner for section in item.sweep.sections))

            for item, path, profile in (
                (elements[0], root.centerline, root.taper),
                (
                    elements[1],
                    (elements[1].sweep.sections[0].center, root.root_attachment_centerline[1]),
                    root.root_attachment_taper,
                ),
                (elements[3], tip.centerline, tip.taper),
                (elements[4], tip.extension_centerline, tip.extension_taper),
            ):
                self.assertIsNotNone(path)
                self.assertIsNotNone(profile)
                for section, expected_center, expected_radius in zip(item.sweep.sections, path, profile):  # type: ignore[union-attr]
                    np.testing.assert_array_equal(section.center, expected_center)
                    self.assertEqual(section.transverse_radii, (float(expected_radius),) * 2)

            for item, centre, radii, source in (
                (elements[2], root.root_collar_center, root.root_collar_radii, root),
                (elements[5], tip.cap_center, tip.cap_radii, tip),
            ):
                self.assertIsNotNone(centre)
                self.assertIsNotNone(radii)
                middle = item.sweep.sections[len(item.sweep.sections) // 2]
                np.testing.assert_array_equal(middle.center, centre)
                self.assertEqual(middle.transverse_radii, (float(radii[0]), float(radii[1])))  # type: ignore[index]
                axis = np.asarray(successor._tail_axis(source, "test tail"), dtype=np.float64)
                centre_vector = np.asarray(centre, dtype=np.float64)
                axial_radius = float(radii[2])  # type: ignore[index]
                for section in item.sweep.sections:
                    self.assertLessEqual(
                        abs(float(np.dot(np.asarray(section.center) - centre_vector, axis))),
                        axial_radius + 1.0e-7,
                    )
                for cap in item.sweep.endpoint_caps:
                    self.assertLessEqual(
                        abs(float(np.dot(np.asarray(cap.center) - centre_vector, axis))) + cap.axial_radius,
                        axial_radius + 1.0e-7,
                    )

            def assert_join(left: Any, right: Any) -> None:
                np.testing.assert_array_equal(left, right)

            assert_join(elements[1].sweep.sections[-1].center, elements[0].sweep.sections[-1].center)
            assert_join(elements[2].sweep.sections[1].center, elements[0].sweep.sections[-1].center)
            assert_join(elements[0].sweep.sections[-1].center, elements[3].sweep.sections[0].center)
            assert_join(elements[3].sweep.sections[-1].center, elements[4].sweep.sections[0].center)
            assert_join(elements[4].sweep.sections[-1].center, elements[5].sweep.sections[1].center)
            source_profile = elements[3].sweep.sections[-1].transverse_radii
            extension_profile = elements[4].sweep.sections[0].transverse_radii
            self.assertEqual(source_profile, (float(tip.taper[-1]),) * 2)
            self.assertEqual(extension_profile, (float(tip.extension_taper[0]),) * 2)  # type: ignore[index]

    def test_tail_successor_attachment_reanchors_to_loft_boundary_for_all_variants(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            root, tip = guide.tail_guides
            attachment = region.tail_elements[1].sweep
            start = np.asarray(attachment.sections[0].center, dtype=np.float64)
            old_start = np.asarray(root.root_attachment_centerline[0], dtype=np.float64)
            source_end = np.asarray(root.root_attachment_centerline[1], dtype=np.float64)

            self.assertLessEqual(
                abs(float(successor._loft_field(start.reshape(1, 3), region.loft)[0])),
                successor._SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE,
            )
            self.assertFalse(np.allclose(start, old_start, rtol=0.0, atol=1.0e-12))
            np.testing.assert_array_equal(attachment.sections[-1].center, source_end)
            self.assertEqual(
                tuple(section.transverse_radii for section in attachment.sections),
                tuple((float(value),) * 2 for value in root.root_attachment_taper),
            )
            self.assertEqual(
                region.tail_elements[3].sweep.sections[-1].transverse_radii,
                (float(tip.taper[-1]),) * 2,
            )
            self.assertEqual(
                region.tail_elements[4].sweep.sections[0].transverse_radii,
                (float(tip.extension_taper[0]),) * 2,
            )

    def test_tail_root_parent_must_be_the_canonical_pelvis_owner(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        root, tip = guide.tail_guides
        wrong_parent = guide.torso_cage.torso_owner.key
        wrong_root_owner = replace(root.owner, parent=wrong_parent)
        wrong_source_descriptors = tuple(
            wrong_root_owner if owner is root.owner else owner
            for owner in guide.source_descriptors
        )
        wrong_guide = replace(
            guide,
            source_descriptors=wrong_source_descriptors,
            tail_guides=(replace(root, owner=wrong_root_owner), tip),
        )
        with self.assertRaisesRegex(successor.SuccessorPreviewError, "canonical pelvis owner"):
            successor._make_tail_elements(wrong_guide)

    def test_tail_successor_components_consume_all_elements_with_source_attribution(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        region = successor.compile_successor_region(guide)
        components = successor._make_components(region, successor.DEFAULT_SMOOTH_K)
        by_recipe = {component.recipe: component for component in components}
        self.assertEqual(
            tuple(recipe for recipe in by_recipe if recipe.startswith("successor-tail-")),
            tuple(f"successor-{item.name}" for item in region.tail_elements),
        )
        for item in region.tail_elements:
            component = by_recipe[f"successor-{item.name}"]
            self.assertTrue(component.successor)
            self.assertIs(component.owner, item.owner)
            self.assertIsNotNone(component.attribution)
            points = np.asarray([section.center for section in item.sweep.sections], dtype=np.float64)
            self.assertTrue(np.all(component.evaluate(points) < 0.0))
            attributed = component.attribution(points)  # type: ignore[misc]
            self.assertEqual(tuple(address[3] for address in attributed), tuple(section.owner.key[3] for section in item.sweep.sections))
            self.assertTrue(all(address == item.owner.key for address in attributed))

    def test_tail_validation_rejects_inventory_axes_controls_joins_and_malformed_baseline(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        root, tip = guide.tail_guides

        wrong_tip_owner = replace(tip.owner, parent=guide.torso_cage.torso_owner.key)
        wrong_tip_descriptors = tuple(wrong_tip_owner if owner is tip.owner else owner for owner in guide.source_descriptors)
        wrong_tip_parent = replace(
            guide,
            source_descriptors=wrong_tip_descriptors,
            tail_guides=(root, replace(tip, owner=wrong_tip_owner)),
        )
        drifted_axes = replace(root.axes, forward=(0.0, 0.1, 1.0))
        guide_cases = {
            "missing-tail": replace(guide, tail_guides=(root,)),
            "duplicate-tail": replace(guide, tail_guides=(root, root)),
            "wrong-canonical-owner": replace(guide, tail_guides=(replace(root, owner=replace(root.owner)), tip)),
            "wrong-tip-parent": wrong_tip_parent,
            "axes-drift": replace(guide, tail_guides=(replace(root, axes=drifted_axes), tip)),
        }
        for name, invalid_guide in guide_cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._make_tail_elements(invalid_guide)

        valid_elements = successor._make_tail_elements(guide)

        def mutate_section(element_index: int, section_index: int, **changes: object) -> tuple[Any, ...]:
            elements = list(valid_elements)
            element = elements[element_index]
            sections = list(element.sweep.sections)
            sections[section_index] = replace(sections[section_index], **changes)
            elements[element_index] = replace(element, sweep=replace(element.sweep, sections=tuple(sections)))
            return tuple(elements)

        invalid_elements = {
            "path-drift": mutate_section(0, 1, center=(0.1, 0.0, -1.0)),
            "profile-drift": mutate_section(0, 1, transverse_radii=(0.31, 0.31)),
            "axes-drift": mutate_section(2, 0, tangent=(1.0, 0.0, 0.0)),
            "root-collar-center-drift": mutate_section(2, 1, center=(0.1, 0.0, -1.0)),
            "root-collar-radius-drift": mutate_section(2, 1, transverse_radii=(0.34, 0.33)),
            "root-source-attachment-join-drift": mutate_section(1, 1, center=(0.1, 0.0, -1.0)),
            "root-collar-source-join-drift": mutate_section(2, 1, center=(0.1, 0.0, -1.0)),
            "source-extension-join-drift": mutate_section(4, 0, center=(0.1, 0.0, -2.0)),
            "extension-cap-join-drift": mutate_section(5, 1, center=(0.1, 0.0, -2.5)),
        }
        for name, invalid_elements in invalid_elements.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._validate_tail_elements(guide, invalid_elements)

        tail_fields = tuple(field for field in baseline if field.recipe in successor._TAIL_BASELINE_RECIPES)
        malformed_baselines = {
            "missing-tail-field": tuple(field for field in baseline if field is not tail_fields[0]),
            "duplicate-tail-field": baseline + (tail_fields[0],),
            "wrong-canonical-owner": tuple(
                replace(field, owner=guide.head_guide.head_owner) if field is tail_fields[0] else field
                for field in baseline
            ),
        }
        for name, invalid_baseline in malformed_baselines.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._validate_tail_baseline_inventory(guide, invalid_baseline)

    def test_tail_rejection_coverage_targets_incomplete_anchor_and_baseline_shape_controls(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        root, tip = guide.tail_guides

        incomplete_cases = {
            "missing-root-attachment": replace(
                guide,
                tail_guides=(replace(root, root_attachment_centerline=None), tip),
            ),
            "missing-root-collar": replace(
                guide,
                tail_guides=(replace(root, root_collar_radii=None), tip),
            ),
            "missing-tip-extension": replace(
                guide,
                tail_guides=(root, replace(tip, extension_taper=None)),
            ),
            "missing-tip-cap": replace(
                guide,
                tail_guides=(root, replace(tip, cap_center=None)),
            ),
        }
        for name, invalid_guide in incomplete_cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._make_tail_elements(invalid_guide)

        drifted_start = tuple(value + (0.1 if axis == 1 else 0.0) for axis, value in enumerate(root.root_attachment_centerline[0]))
        drifted_root = replace(
            root,
            root_attachment_centerline=(drifted_start, root.root_attachment_centerline[1]),
        )
        with self.assertRaises(successor.SuccessorPreviewError):
            successor._make_tail_elements(replace(guide, tail_guides=(drifted_root, tip)))

        valid_region = successor.compile_successor_region(guide, baseline)
        attachment = valid_region.tail_elements[1]
        changed_sections = list(attachment.sweep.sections)
        changed_sections[0] = replace(
            changed_sections[0],
            center=tuple(value + (0.1 if axis == 1 else 0.0) for axis, value in enumerate(changed_sections[0].center)),
        )
        changed_elements = list(valid_region.tail_elements)
        changed_elements[1] = replace(
            attachment,
            sweep=replace(attachment.sweep, sections=tuple(changed_sections)),
        )
        with self.assertRaises(successor.SuccessorPreviewError):
            successor._validate_tail_elements(guide, tuple(changed_elements), valid_region.loft)

        tail_bridge = next(
            field for field in baseline
            if field.recipe == "tail-root-bridge" and field.owner is root.owner
        )
        malformed_baselines = {
            "baseline-tail-path": tuple(
                replace(
                    field,
                    shape={**field.shape, "to": tuple(value + (0.1 if axis == 2 else 0.0) for axis, value in enumerate(field.shape["to"]))},
                ) if field is tail_bridge else field
                for field in baseline
            ),
            "baseline-tail-profile": tuple(
                replace(field, shape={**field.shape, "r1": float(field.shape["r1"]) + 0.1})
                if field is tail_bridge else field
                for field in baseline
            ),
        }
        for name, invalid_baseline in malformed_baselines.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._validate_tail_baseline_inventory(guide, invalid_baseline)

    def test_extremity_components_consume_all_sweeps_with_dynamic_attribution(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            components = successor._make_components(region, successor.DEFAULT_SMOOTH_K)
            by_name = {component.recipe: component for component in components}
            for item in region.extremity_sweeps:
                component = by_name[f"successor-{item.name}"]
                self.assertTrue(component.successor)
                self.assertIs(component.owner, item.sweep.sections[0].owner)
                points = np.asarray([section.center for section in item.sweep.sections])
                self.assertTrue(np.all(component.evaluate(points) < 0.0))
                attributed = component.attribution(points)  # type: ignore[misc]
                self.assertEqual(tuple(owner[3] for owner in attributed), tuple(section.owner.key[3] for section in item.sweep.sections))

    def test_head_neck_routes_consume_exact_authored_topology_and_remain_reusable(self) -> None:
        expected_routes = {
            "vertical-neck-cranium": ((0, 1, 2, 3, 4), "up", ("lateral", "forward")),
            "forward-muzzle": ((3, 5, 6, 7), "forward", ("lateral", "up")),
        }
        topologies = []
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            self.assertIsInstance(region.head_neck_sweeps, tuple)
            self.assertIs(region.head_neck_profile, guide.head_guide.profile)
            self.assertEqual(tuple(item.recipe for item in region.head_neck_sweeps), tuple(expected_routes))
            for item in region.head_neck_sweeps:
                indices, tangent_axis, transverse_axes = expected_routes[item.recipe]
                self.assertEqual(item.sweep.profile_operation, successor._HEAD_NECK_PROFILE_OPERATION)
                self.assertEqual(tuple(section.source_section_index for section in item.sweep.sections), indices)
                self.assertEqual(item.sweep.names, tuple(surface_preview.HEAD_NECK_PROFILE_SECTION_NAMES[index] for index in indices))
                self.assertEqual(len(item.sweep.endpoint_caps), 2)
                self.assertEqual(item.sweep.internal_transitions, ())
                axis_index = {"lateral": 0, "up": 1, "forward": 2}
                for section, source_index in zip(item.sweep.sections, indices):
                    source = guide.head_guide.profile.sections[source_index]
                    self.assertIs(section.owner, source.owner)
                    self.assertEqual(section.center, source.center)
                    self.assertEqual(section.tangent_radius, source.radii[axis_index[tangent_axis]])
                    self.assertEqual(
                        section.transverse_radii,
                        tuple(source.radii[axis_index[axis]] for axis in transverse_axes),
                    )
                    np.testing.assert_array_equal(
                        successor._profile_sweep_field(np.asarray(section.center).reshape(1, 3), item.sweep) < 0.0,
                        np.asarray([True]),
                    )
                connection_indices = tuple(
                    connection.spec.name
                    for connection in guide.head_guide.profile.connections
                    if connection.spec.route == item.recipe
                )
                self.assertEqual(
                    [connection[0] for connection in surface_preview.HEAD_NECK_PROFILE_CONNECTIONS if connection[3] == item.recipe],
                    list(connection_indices),
                )
                for connection in guide.head_guide.profile.connections:
                    if connection.spec.route != item.recipe:
                        continue
                    samples = np.linspace(connection.centerline[0], connection.centerline[1], 9)
                    self.assertTrue(np.all(successor._profile_sweep_field(samples, item.sweep) < 0.0))
            metadata = successor._head_neck_metadata(region)
            self.assertEqual(metadata["operation"], successor._HEAD_NECK_PROFILE_OPERATION)
            self.assertEqual([route["name"] for route in metadata["route_topology"]], list(expected_routes))
            self.assertEqual(tuple(item.recipe for item in region.head_neck_sweeps), tuple(route["name"] for route in metadata["route_topology"]))
            self.assertEqual(metadata["sections_consumed"], 8)
            self.assertEqual(metadata["connections_consumed"], 7)
            topologies.append(tuple((item.recipe, item.sweep.names, item.sweep.profile_operation) for item in region.head_neck_sweeps))
        self.assertEqual(len(set(topologies)), 1)

    def test_head_neck_connections_are_exact_adjacent_route_spans_and_derived(self) -> None:
        expected_route_spans = []
        for route_name, section_indices, _, _ in successor._HEAD_NECK_ROUTE_TOPOLOGY:
            expected_route_spans.extend(
                (route_name, left, right)
                for left, right in zip(section_indices, section_indices[1:])
            )

        for variant_id, descriptors, _ in self.form.variants:
            with self.subTest(variant=variant_id):
                guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
                profile = guide.head_guide.profile
                region = successor.compile_successor_region(guide)
                observed_spans = tuple(
                    (connection.spec.route, connection.spec.from_section_index, connection.spec.to_section_index)
                    for connection in profile.connections
                )
                self.assertEqual(observed_spans, tuple(expected_route_spans))
                self.assertEqual(len(profile.connections), 7)

                routes = {item.recipe: item for item in region.head_neck_sweeps}
                for connection in profile.connections:
                    from_section = profile.sections[connection.spec.from_section_index]
                    to_section = profile.sections[connection.spec.to_section_index]
                    self.assertIs(connection.from_section, from_section)
                    self.assertIs(connection.to_section, to_section)
                    self.assertEqual(connection.centerline, (from_section.center, to_section.center))
                    self.assertEqual(connection.thickness, (min(from_section.radii), min(to_section.radii)))

                for route_name, _, _, _ in successor._HEAD_NECK_ROUTE_TOPOLOGY:
                    route = routes[route_name]
                    route_connections = tuple(
                        connection for connection in profile.connections
                        if connection.spec.route == route_name
                    )
                    self.assertEqual(len(route_connections), len(route.sweep.sections) - 1)
                    for connection, (left, right) in zip(
                        route_connections,
                        zip(route.sweep.sections, route.sweep.sections[1:]),
                    ):
                        self.assertEqual(connection.from_section, profile.sections[left.source_section_index])
                        self.assertEqual(connection.to_section, profile.sections[right.source_section_index])
                        self.assertEqual(connection.centerline, (left.center, right.center))

    def test_every_authored_head_neck_radius_changes_a_compiled_route_observable(self) -> None:
        for variant_id, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            profile = guide.head_guide.profile
            axes = guide.topology.axes
            baseline_routes = {item.recipe: item for item in successor._make_head_neck_sweeps(guide)}
            for section_index, source in enumerate(profile.sections):
                affected_routes = tuple(
                    (route_name, section_indices)
                    for route_name, section_indices, _, _ in successor._HEAD_NECK_ROUTE_TOPOLOGY
                    if section_index in section_indices
                )
                for axis in _HEAD_NECK_AXIS_INDEX:
                    with self.subTest(variant=variant_id, station=source.name, axis=axis):
                        changed_guide = _mutate_head_neck_radius(guide, section_index, axis)
                        changed_route_items = successor._make_head_neck_sweeps(changed_guide)
                        changed_routes = {item.recipe: item for item in changed_route_items}
                        self.assertEqual(set(changed_routes), set(baseline_routes))
                        differences = []
                        for route_name, _ in affected_routes:
                            differences.append(float(np.max(np.abs(
                                _head_neck_route_signature(changed_routes[route_name], profile, axes)
                                - _head_neck_route_signature(baseline_routes[route_name], profile, axes)
                            ))))
                        self.assertTrue(
                            any(difference > 1.0e-8 for difference in differences),
                            msg=f"{source.name}.{axis} did not affect its route observables: {differences!r}",
                        )

    def test_head_neck_invalid_guide_dimensions_fail_closed(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        profile = guide.head_guide.profile

        def with_profile(changed_profile: object) -> object:
            return replace(guide, head_guide=replace(guide.head_guide, profile=changed_profile))

        invalid_section = replace(profile.sections[6], radii=(float("nan"), 0.2, 0.2))
        invalid_sections = profile.sections[:6] + (invalid_section,) + profile.sections[7:]
        invalid_connection_spec = replace(profile.connections[0].spec, to_section_index=7)
        invalid_connection = replace(profile.connections[0], spec=invalid_connection_spec)
        invalid_centerline = replace(
            profile.connections[0],
            centerline=(profile.connections[0].centerline[0], tuple(value + 0.1 for value in profile.connections[0].centerline[1])),
        )
        invalid_lineage = replace(
            profile.sections[7],
            forward_lineage=replace(profile.sections[7].forward_lineage, reference_index=999),
        )
        invalid_axes = replace(profile, axes=replace(guide.topology.axes, up=(0.0, 0.0, 1.0)))
        cases = (
            ("radius", replace(profile, sections=invalid_sections)),
            ("section-index", replace(profile, sections=profile.sections[:2] + (replace(profile.sections[2], section_index=7),) + profile.sections[3:])),
            ("frame-index", replace(profile, sections=profile.sections[:2] + (replace(profile.sections[2], frame_index=99),) + profile.sections[3:])),
            ("landmark-index", replace(profile, sections=profile.sections[:2] + (replace(profile.sections[2], landmark_index=99),) + profile.sections[3:])),
            ("edge-index", replace(profile, connections=(invalid_connection,) + profile.connections[1:])),
            ("edge-centerline", replace(profile, connections=(invalid_centerline,) + profile.connections[1:])),
            ("lineage-index", replace(profile, sections=profile.sections[:7] + (invalid_lineage,))),
            ("axes", invalid_axes),
        )
        for name, invalid_profile in cases:
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._make_head_neck_sweeps(with_profile(invalid_profile))

    def test_authored_station_radius_and_position_are_skin_driving(self) -> None:
        """A valid terminal radius and crown position must change route fields."""

        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            profile = guide.head_guide.profile

            def mutate_profile(index: int, *, center_delta: tuple[float, float, float] | None = None, radii: tuple[float, float, float] | None = None) -> object:
                sections = list(profile.sections)
                source = sections[index]
                center = tuple(
                    float(source.center[axis] + (center_delta[axis] if center_delta is not None else 0.0))
                    for axis in range(3)
                )
                sections[index] = replace(source, center=center, radii=radii or source.radii)
                rebuilt_connections = []
                for connection in profile.connections:
                    from_section = sections[connection.spec.from_section_index]
                    to_section = sections[connection.spec.to_section_index]
                    rebuilt_connections.append(replace(
                        connection,
                        from_section=from_section,
                        to_section=to_section,
                        centerline=(from_section.center, to_section.center),
                        thickness=(min(from_section.radii), min(to_section.radii)),
                    ))
                changed_profile = replace(profile, sections=tuple(sections), connections=tuple(rebuilt_connections))
                return replace(guide, head_guide=replace(guide.head_guide, profile=changed_profile))

            original_routes = {item.recipe: item for item in successor._make_head_neck_sweeps(guide)}
            radius_change = tuple(profile.sections[7].radii[:2]) + (profile.sections[7].radii[2] * 0.35,)
            radius_guide = mutate_profile(7, radii=radius_change)
            successor._validate_authored_head_neck_guide(radius_guide)
            changed_radius_routes = {item.recipe: item for item in successor._make_head_neck_sweeps(radius_guide)}
            muzzle_tip = np.asarray(profile.sections[7].center, dtype=np.float64)
            forward = np.asarray(guide.topology.axes.forward, dtype=np.float64)
            radius_probe = (muzzle_tip + 0.75 * profile.sections[7].radii[2] * forward).reshape(1, 3)
            original_radius_value = successor._profile_sweep_field(radius_probe, original_routes["forward-muzzle"].sweep)
            changed_radius_value = successor._profile_sweep_field(radius_probe, changed_radius_routes["forward-muzzle"].sweep)
            self.assertGreater(float(np.max(np.abs(original_radius_value - changed_radius_value))), 1.0e-8)

            position_guide = mutate_profile(4, center_delta=(0.18, 0.0, 0.0))
            successor._validate_authored_head_neck_guide(position_guide)
            changed_position_routes = {item.recipe: item for item in successor._make_head_neck_sweeps(position_guide)}
            crown = np.asarray(profile.sections[4].center, dtype=np.float64)
            crown_probe = np.asarray((crown, crown + np.asarray((0.0, 0.0, 0.20)), crown + np.asarray((0.20, 0.0, 0.0))))
            original_position_value = successor._profile_sweep_field(crown_probe, original_routes["vertical-neck-cranium"].sweep)
            changed_position_value = successor._profile_sweep_field(crown_probe, changed_position_routes["vertical-neck-cranium"].sweep)
            self.assertGreater(float(np.max(np.abs(original_position_value - changed_position_value))), 1.0e-8)

    def test_head_neck_sweeps_are_consumed_by_components_and_composed_field(self) -> None:
        expected_recipes = {"vertical-neck-cranium", "forward-muzzle"}
        for variant_id, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            components = successor._make_components(region, 0.10)
            head_components = {
                component.recipe: component
                for component in components
                if component.recipe in {f"successor-{recipe}" for recipe in expected_recipes}
            }
            self.assertEqual(set(head_components), {f"successor-{recipe}" for recipe in expected_recipes})
            for item in region.head_neck_sweeps:
                component = head_components[f"successor-{item.recipe}"]
                self.assertIs(component.owner, item.owner)
                representative = np.asarray(item.sweep.sections[len(item.sweep.sections) // 2].center, dtype=np.float64).reshape(1, 3)
                own_value = successor._profile_sweep_field(representative, item.sweep)
                self.assertLess(float(own_value[0]), 0.0)
                np.testing.assert_allclose(component.evaluate(representative), own_value, rtol=0.0, atol=1.0e-12)

                if variant_id == "neutral-v0":
                    # One shared wiring proof is enough here: overlapping
                    # guide-derived forms can legitimately swallow a probe at
                    # another variant's section centre. All-four visibility is
                    # covered separately by the sampled winner-ownership
                    # regression, not by this pointwise subtraction.
                    without_item = replace(
                        region,
                        head_neck_sweeps=tuple(other for other in region.head_neck_sweeps if other is not item),
                    )
                    composed_value = float(successor._successor_region_field(representative, region, 0.10)[0])
                    without_value = float(successor._successor_region_field(representative, without_item, 0.10)[0])
                    self.assertGreater(abs(composed_value - without_value), 1.0e-8)

    def test_authored_arm_routes_have_exact_shared_five_station_profile_and_elbow_ownership(self) -> None:
        expected_order = (
            "left-upper-arm-route", "left-forearm-route", "right-upper-arm-route", "right-forearm-route",
            "left-leg", "right-leg",
        )
        expected_names = {
            "left-upper-arm-route": ("upper-arm-start", "upper-arm-midpoint", "elbow"),
            "left-forearm-route": ("elbow", "forearm-midpoint", "forearm-distal"),
            "right-upper-arm-route": ("upper-arm-start", "upper-arm-midpoint", "elbow"),
            "right-forearm-route": ("elbow", "forearm-midpoint", "forearm-distal"),
            "left-leg": ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
            "right-leg": ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
        }
        expected_roles = {
            "left-upper-arm-route": ("upper_arm", "upper_arm", "upper_arm"),
            "left-forearm-route": ("upper_arm", "forearm", "forearm"),
            "right-upper-arm-route": ("upper_arm", "upper_arm", "upper_arm"),
            "right-forearm-route": ("upper_arm", "forearm", "forearm"),
            "left-leg": ("thigh", "thigh", "thigh", "shin", "shin"),
            "right-leg": ("thigh", "thigh", "thigh", "shin", "shin"),
        }
        topologies = []
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            self.assertEqual(tuple(item.chain_name for item in region.limb_sweeps), expected_order)
            self.assertEqual(tuple(item.chain_name for item in region.arm_sweeps), expected_order[:4])
            topology = []
            for item in region.limb_sweeps:
                self.assertEqual(item.section_names, expected_names[item.chain_name])
                self.assertEqual(item.sections_consumed, len(expected_names[item.chain_name]))
                self.assertEqual(tuple(section.owner.key[3] for section in item.sweep.sections), expected_roles[item.chain_name])
                self.assertEqual(len(item.sweep.endpoint_caps), 2)
                self.assertEqual(tuple(cap.side for cap in item.sweep.endpoint_caps), ("start", "end"))
                if item.is_arm_profile_route:
                    self.assertEqual(item.sweep.profile_operation, successor._ARM_PROFILE_OPERATION)
                    self.assertEqual(len(item.source_stations), 3)
                    self.assertTrue(all(section.station_volume_radii is not None for section in item.sweep.sections))
                    self.assertEqual(
                        tuple(section.station_volume_radii for section in item.sweep.sections),
                        tuple(station.radii for station in item.source_stations),
                    )
                transition_indices = tuple(transition.section_index for transition in item.sweep.internal_transitions)
                self.assertEqual(len(transition_indices), len(set(transition_indices)))
                self.assertTrue(all(0 < index < item.sections_consumed - 1 for index in transition_indices))
                topology.append((item.chain_name, item.section_names, item.sections_consumed, transition_indices))
            for side in ("left", "right"):
                upper = next(item for item in region.arm_sweeps if item.chain_name == f"{side}-upper-arm-route")
                forearm = next(item for item in region.arm_sweeps if item.chain_name == f"{side}-forearm-route")
                guide_side = next(item for item in guide.arm_profile.sides if item.side == side)
                self.assertIs(upper.source_stations[-1], guide_side.sections[2])
                self.assertIs(forearm.source_stations[0], guide_side.sections[2])
                self.assertIs(upper.source_stations[-1].owner, guide_side.sections[2].owner)
                self.assertEqual(upper.source_stations[-1].owner.key[3], "upper_arm")
            topologies.append(tuple(topology))
        self.assertEqual(len(set(topologies)), 1)

    def test_bridge_inventory_retains_expected_four_thigh_and_hip_connectors(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        region = successor.compile_successor_region(guide, baseline)
        expected_bridge_recipes = {"root-bridge", "hip-transition"}
        self.assertEqual(len(region.bridge_fields), 4)
        self.assertEqual(len(baseline) - len(region.bridge_fields), 48)
        self.assertEqual({field.recipe for field in region.bridge_fields}, expected_bridge_recipes)
        self.assertNotIn("deltoid-sweep-1", {field.recipe for field in region.bridge_fields})
        self.assertFalse(any(
            field.recipe in {"anterior-support", "posterior-support", "upper-arm-root-bridge"}
            for field in region.bridge_fields
        ))
        self.assertFalse(any(
            component.recipe in {"successor-deltoid-sweep-1", "successor-anterior-support", "successor-posterior-support", "successor-upper-arm-root-bridge"}
            for component in successor._make_components(region, successor.DEFAULT_SMOOTH_K)
        ))
        self.assertEqual(len(region.replaced_baseline_recipes), 28)
        self.assertEqual(
            sum(field.recipe in region.replaced_baseline_recipes for field in baseline),
            46,
        )
        self.assertEqual(
            sum(field.recipe in successor._LIMB_CHAIN_BASELINE_RECIPES for field in baseline),
            22,
        )

        chains = {item.chain_name: item for item in region.leg_sweeps + region.arm_sweeps}
        inventory = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.limb_guides}
        for side in ("left", "right"):
            arm = chains[f"{side}-forearm-route"]
            leg = chains[f"{side}-leg"]
            self.assertFalse(any(
                field.recipe == "root-bridge" and field.owner is inventory[(side, "upper_arm")].owner
                for field in region.bridge_fields
            ))
            leg_root = next(field for field in region.bridge_fields if field.recipe == "root-bridge" and field.owner is inventory[(side, "thigh")].owner)
            np.testing.assert_allclose(leg_root.shape["to"], leg.sweep.sections[0].center, rtol=0.0, atol=1.0e-12)
            hip = next(field for field in region.bridge_fields if field.recipe == "hip-transition" and field.owner is inventory[(side, "thigh")].owner)
            self.assertTrue(np.all(np.isfinite(hip.shape["from"])))
            hand = next(item for item in region.hand_sweeps if item.side == side and item.kind == "hand-attachment")
            self.assertLessEqual(
                float(successor._profile_sweep_field(np.asarray(arm.sweep.sections[-1].center).reshape(1, 3), hand.sweep)[0]),
                0.0,
            )
            foot = next(item for item in region.foot_sweeps if item.side == side)
            np.testing.assert_allclose(foot.sweep.sections[0].center, leg.sweep.sections[-1].center, rtol=0.0, atol=1.0e-12)
            foot_guide = next(item for item in guide.paw_guides if item.owner.key[1] == (side,) and item.owner.key[3] == "foot")
            np.testing.assert_allclose(foot_guide.foot_chain.hock_anchor, foot.sweep.sections[0].center, rtol=0.0, atol=1.0e-12)

    def test_limb_components_consume_all_chains_with_dynamic_section_ownership(self) -> None:
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            components = successor._make_components(region, successor.DEFAULT_SMOOTH_K)
            by_recipe = {component.recipe: component for component in components}
            probes = []
            for chain in region.limb_sweeps:
                component = by_recipe[f"successor-{chain.chain_name}"]
                self.assertTrue(component.successor)
                self.assertIsNotNone(component.attribution)
                points = np.asarray([section.center for section in chain.sweep.sections], dtype=np.float64)
                self.assertTrue(np.all(component.evaluate(points) < 0.0))
                attributed = component.attribution(points)  # type: ignore[misc]
                self.assertEqual(tuple(item[3] for item in attributed), tuple(section.owner.key[3] for section in chain.sweep.sections))
                probes.extend(points)
            composed = successor._successor_region_field(np.asarray(probes), region, successor.DEFAULT_SMOOTH_K)
            self.assertTrue(np.all(np.isfinite(composed)))
            self.assertTrue(np.all(composed < 0.0))

    def test_invalid_limb_inventory_ownership_and_connectors_fail_closed(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        limbs = guide.limb_guides
        head_owner = guide.head_guide.head_owner
        cases = {
            "missing": replace(guide, limb_guides=limbs[:-1]),
            "duplicate": replace(guide, limb_guides=limbs + (limbs[0],)),
            "wrong-owner": replace(guide, limb_guides=(replace(limbs[0], owner=head_owner),) + limbs[1:]),
        }
        upper_index = next(index for index, limb in enumerate(limbs) if limb.owner.key[3] == "upper_arm")
        upper = limbs[upper_index]
        changed_section = replace(
            upper.sections[1],
            centerline=(upper.sections[1].centerline[0], tuple(value + 0.25 for value in upper.sections[1].centerline[1])),
        )
        changed_limbs = list(limbs)
        changed_limbs[upper_index] = replace(upper, sections=(upper.sections[0], changed_section))
        cases["connector-mismatch"] = replace(guide, limb_guides=tuple(changed_limbs))
        for name, invalid in cases.items():
            with self.subTest(name=name), self.assertRaises((successor.SuccessorPreviewError, surface_preview.PreviewError)):
                successor.compile_successor_region(invalid)

        baseline = surface_preview._compile_hybrid_guide(guide)
        wrong_field = tuple(
            replace(field, owner=head_owner) if field.recipe == "elbow" else field
            for field in baseline
        )
        with self.assertRaises(successor.SuccessorPreviewError):
            successor.compile_successor_region(guide, wrong_field)

    def test_extremity_validation_rejects_identity_parent_path_profile_inventory_and_controls(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        hand_index = next(index for index, paw in enumerate(guide.paw_guides) if paw.owner.key[1:] == (("left",), "part", "hand"))
        hand = guide.paw_guides[hand_index]

        cloned_paws = list(guide.paw_guides)
        cloned_paws[hand_index] = replace(hand, owner=replace(hand.owner))
        cloned_owner = replace(guide, paw_guides=tuple(cloned_paws))

        wrong_parent = replace(hand.owner, parent=guide.torso_cage.torso_owner.key)
        source_descriptors = tuple(wrong_parent if owner is hand.owner else owner for owner in guide.source_descriptors)
        parent_paws = tuple(replace(hand, owner=wrong_parent) if paw is hand else paw for paw in guide.paw_guides)
        wrong_parent_guide = replace(guide, source_descriptors=source_descriptors, paw_guides=parent_paws)

        drifted_attachment = replace(
            hand,
            attachment_centerline=(
                hand.attachment_centerline[0],
                tuple(value + 0.1 for value in hand.attachment_centerline[1]),
            ),
        )
        attachment_paws = list(guide.paw_guides)
        attachment_paws[hand_index] = drifted_attachment
        attachment_drift = replace(guide, paw_guides=tuple(attachment_paws))

        drifted_axes = replace(hand.axes, forward=(0.0, 0.1, 1.0))
        control_paws = list(guide.paw_guides)
        control_paws[hand_index] = replace(hand, axes=drifted_axes)
        control_drift = replace(guide, paw_guides=tuple(control_paws))

        def mutate_field(recipe: str, role: str, mutation: object) -> tuple[object, ...]:
            fields = list(baseline)
            index = next(
                index for index, field in enumerate(fields)
                if field.recipe == recipe and field.owner.key[1] == ("left",) and field.owner.key[3] == role
            )
            fields[index] = mutation(fields[index])  # type: ignore[operator]
            return tuple(fields)

        path_drift = mutate_field(
            "extremity-bridge", "hand",
            lambda field: replace(field, shape={**field.shape, "from": tuple(value + 0.1 for value in field.shape["from"])}),
        )
        profile_drift = mutate_field(
            "paw-pad", "foot",
            lambda field: replace(field, shape={**field.shape, "radii": tuple(value + 0.1 for value in field.shape["radii"])}),
        )
        missing_mirror = tuple(
            field for field in baseline
            if not (field.recipe == "paw" and field.owner.key[1] == ("left",))
        )
        duplicated_mirror = tuple(
            baseline[index]
            if field.recipe != "paw" or field.owner.key[1] != ("right",)
            else next(item for item in baseline if item.recipe == "paw" and item.owner.key[1] == ("left",))
            for index, field in enumerate(baseline)
        )
        cases = {
            "cloned-owner": (cloned_owner, baseline),
            "attachment-guide-drift": (attachment_drift, baseline),
            "attachment-path-drift": (guide, path_drift),
            "foot-profile-drift": (guide, profile_drift),
            "missing-mirrored-paw": (guide, missing_mirror),
            "duplicated-mirrored-paw": (guide, duplicated_mirror),
            "hand-control-drift": (control_drift, baseline),
        }
        for name, (invalid_guide, invalid_fields) in cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor.compile_successor_region(invalid_guide, invalid_fields)

        # Exercise the successor extremity parent check directly: the normal
        # compile path also validates the temporary baseline bridge first and
        # would reject this mutation before reaching the new consumer.
        wrong_parent_limbs = successor._make_limb_sweeps(wrong_parent_guide)
        with self.assertRaises(successor.SuccessorPreviewError):
            successor._make_extremity_sweeps(wrong_parent_guide, wrong_parent_limbs)

    def test_extremity_rejects_rotated_orthonormal_hand_frame(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        hand_index = next(index for index, paw in enumerate(guide.paw_guides) if paw.owner.key[1:] == (("left",), "part", "hand"))
        hand = guide.paw_guides[hand_index]
        angle = 0.37
        cosine, sine = math.cos(angle), math.sin(angle)
        rotated_axes = replace(
            hand.axes,
            lateral=(cosine, 0.0, sine),
            forward=(-sine, 0.0, cosine),
        )
        rotated_paws = list(guide.paw_guides)
        rotated_paws[hand_index] = replace(hand, axes=rotated_axes)
        rotated_guide = replace(guide, paw_guides=tuple(rotated_paws))

        with self.assertRaisesRegex(successor.SuccessorPreviewError, "hand guide axes"):
            successor.compile_successor_region(rotated_guide, baseline)

    def test_extremity_rejects_metatarsal_endpoint_drift_from_pad(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        foot_index = next(index for index, paw in enumerate(guide.paw_guides) if paw.owner.key[1:] == (("left",), "part", "foot"))
        foot = guide.paw_guides[foot_index]
        chain = foot.foot_chain
        drifted_end = tuple(value + (0.1 if axis == 0 else 0.0) for axis, value in enumerate(chain.metatarsal_centerline[1]))
        drifted_chain = replace(
            chain,
            metatarsal_centerline=(chain.metatarsal_centerline[0], drifted_end),
        )
        drifted_paws = list(guide.paw_guides)
        drifted_paws[foot_index] = replace(foot, foot_chain=drifted_chain)
        drifted_guide = replace(guide, paw_guides=tuple(drifted_paws))
        drifted_baseline = surface_preview._compile_hybrid_guide(drifted_guide)

        with self.assertRaisesRegex(successor.SuccessorPreviewError, "metatarsal must end at the pad exactly"):
            successor.compile_successor_region(drifted_guide, drifted_baseline)

    def test_limb_validation_rejects_identity_topology_inventory_and_bridge_drift(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        sweeps = successor._make_limb_sweeps(guide)
        upper_index = next(index for index, limb in enumerate(guide.limb_guides) if limb.owner.key[1:] == (("left",), "part", "upper_arm"))
        upper = guide.limb_guides[upper_index]

        def changed_limb(replacement: object) -> object:
            limbs = list(guide.limb_guides)
            limbs[upper_index] = replacement
            return replace(guide, limb_guides=tuple(limbs))

        cloned_upper = replace(upper.owner)
        bad_guides = {
            "cloned-limb-owner": changed_limb(replace(upper, owner=cloned_upper)),
            "wrong-section-name": changed_limb(replace(
                upper,
                sections=(replace(upper.sections[0], name="renamed"), upper.sections[1]),
            )),
            "section-gap": changed_limb(replace(
                upper,
                sections=(
                    upper.sections[0],
                    replace(
                        upper.sections[1],
                        centerline=(
                            tuple(value + 0.125 for value in upper.sections[1].centerline[0]),
                            upper.sections[1].centerline[1],
                        ),
                    ),
                ),
            )),
        }
        for name, invalid in bad_guides.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._limb_inventory(invalid)

        left_elbow = next(field for field in baseline if field.recipe == "elbow" and field.owner.key[1] == ("left",))
        right_elbow = next(field for field in baseline if field.recipe == "elbow" and field.owner.key[1] == ("right",))
        bad_field_sets = {
            "cloned-removed-owner": tuple(
                replace(field, owner=replace(field.owner)) if field is left_elbow else field
                for field in baseline
            ),
            "mirrored-field-duplicated": tuple(
                left_elbow if field is right_elbow else field
                for field in baseline
            ),
        }

        def mutate_shape(recipe: str, side: str, role: str, key: str, delta: float) -> tuple[object, ...]:
            result = []
            for field in baseline:
                if field.recipe == recipe and field.owner.key[1] == (side,) and field.owner.key[3] == role:
                    shape = dict(field.shape)
                    if key in {"from", "to"}:
                        changed = np.asarray(shape[key], dtype=np.float64).copy()
                        changed[0] += delta
                        shape[key] = changed
                    else:
                        shape[key] = float(shape[key]) + delta
                    field = replace(field, shape=shape)
                result.append(field)
            return tuple(result)

        bad_field_sets.update({
            "root-path": mutate_shape("root-bridge", "left", "upper_arm", "from", 0.125),
            "hip-profile": mutate_shape("hip-transition", "left", "thigh", "r1", 0.125),
            "metatarsal-path": mutate_shape("metatarsal", "left", "foot", "to", 0.125),
            "hand-attachment": mutate_shape("extremity-bridge", "left", "hand", "from", 0.125),
        })
        for name, invalid_fields in bad_field_sets.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._validate_limb_bridge_inventory(guide, invalid_fields, sweeps)

        hand_index = next(index for index, paw in enumerate(guide.paw_guides) if paw.owner.key[1:] == (("left",), "part", "hand"))
        hand = guide.paw_guides[hand_index]
        cloned_hand = replace(hand.owner)
        paws = list(guide.paw_guides)
        paws[hand_index] = replace(hand, owner=cloned_hand)
        with self.assertRaises(successor.SuccessorPreviewError):
            successor._validate_limb_bridge_inventory(replace(guide, paw_guides=tuple(paws)), baseline, sweeps)

        wrong_parent_hand = replace(hand.owner, parent=guide.torso_cage.torso_owner.key)
        parent_guide = replace(
            guide,
            source_descriptors=tuple(wrong_parent_hand if owner is hand.owner else owner for owner in guide.source_descriptors),
            paw_guides=tuple(replace(hand, owner=wrong_parent_hand) if paw is hand else paw for paw in guide.paw_guides),
        )
        parent_fields = tuple(
            replace(field, owner=wrong_parent_hand) if field.owner is hand.owner else field
            for field in baseline
        )
        with self.assertRaises(successor.SuccessorPreviewError):
            successor._validate_limb_bridge_inventory(parent_guide, parent_fields, sweeps)

    def test_baseline_recipe_signature_is_unchanged_and_successor_is_distinct(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        before = tuple((field.owner.key, field.recipe) for field in surface_preview._compile_hybrid_guide(guide))
        mesh = successor.build_variant(self.form, descriptors, padding=0.5)
        after = tuple((field.owner.key, field.recipe) for field in surface_preview._compile_hybrid_guide(guide))

        self.assertEqual(before, after)
        self.assertEqual(mesh.metrics["consumer_id"], successor.CONSUMER_ID)
        self.assertEqual(mesh.metrics["successor_region"]["torso_sections_consumed"], 7)
        self.assertTrue(mesh.metrics["temporary_bridge"]["enabled"])
        self.assertEqual(mesh.metrics["temporary_bridge"]["field_count"], 4)
        self.assertEqual(mesh.metrics["successor_region"]["replaced_baseline_field_count"], 48)
        self.assertNotEqual(mesh.metrics["consumer_id"], "creature-kernel.disposable-surface-preview.v2")
        self.assertEqual(len(mesh.vertices.shape), 2)
        self.assertEqual(mesh.vertices.shape[1], 3)
        self.assertEqual(mesh.faces.shape[1], 3)
        self.assertTrue(np.all(np.isfinite(mesh.vertices)))
        self.assertTrue(np.all(np.isfinite(mesh.normals)))
        self.assertTrue(mesh.metrics["watertight"])
        self.assertEqual(mesh.metrics["component_count"], 1)
        self.assertGreater(mesh.metrics["signed_volume"], 0.0)

    def test_successor_preserves_section_source_ownership_in_attribution(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        region = successor.compile_successor_region(guide)
        points = np.asarray([region.loft.centers[0], region.loft.centers[1], region.loft.centers[2], region.loft.centers[-1]])
        owner_roles = tuple(owner[3] for owner in successor._loft_owner_keys(points, region.loft))
        self.assertEqual(owner_roles, ("pelvis", "pelvis", "torso", "torso"))

        mesh = successor.build_variant(self.form, descriptors, padding=0.5)
        emitted = mesh.metrics["successor_region"]["torso_section_owner_keys"]
        self.assertEqual([item["role"] for item in emitted[:2]], ["pelvis", "pelvis"])
        self.assertEqual([item["role"] for item in emitted[2:]], ["torso"] * 5)
        winner_roles = {item["role"] for item in mesh.metrics["winner_addresses"]}
        self.assertIn("pelvis", winner_roles)
        self.assertIn("torso", winner_roles)

    def test_successor_rejects_missing_renamed_duplicate_or_wrong_owner_inventory(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        torso = guide.torso_cage.torso_owner
        left, right = guide.shoulder_frame.sides
        head = guide.head_guide.head_owner

        cases = {
            "missing-torso": tuple(field for field in baseline if field.recipe != "torso-cage"),
            "duplicate-torso": baseline + (next(field for field in baseline if field.recipe == "torso-cage"),),
            "wrong-torso-owner": tuple(
                replace(field, owner=head) if field.recipe == "torso-cage" else field for field in baseline
            ),
            "renamed-deltoid": tuple(
                replace(field, recipe="deltoid-sweep-2")
                if field.recipe == "deltoid-sweep-1" and field.owner is left.owner
                else field
                for field in baseline
            ),
            "duplicate-left-deltoid": tuple(
                field for field in baseline if not (field.recipe == "deltoid-sweep-1" and field.owner is right.owner)
            ) + (next(field for field in baseline if field.recipe == "deltoid-sweep-1" and field.owner is left.owner),),
            "wrong-deltoid-owner": tuple(
                replace(field, owner=torso)
                if field.recipe == "deltoid-sweep-1" and field.owner is left.owner
                else field
                for field in baseline
            ),
        }
        for name, mutated in cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor.compile_successor_region(guide, mutated)

    def test_all_variants_are_deterministic_and_remain_distinct(self) -> None:
        signatures = []
        for variant_id, descriptors, _ in self.form.variants:
            first = successor.build_variant(self.form, descriptors, padding=0.5)
            second = successor.build_variant(self.form, descriptors, padding=0.5)
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            self.assertEqual(
                tuple(item.recipe for item in first.representation.shoulder_sweeps),
                ("left-shoulder-envelope", "right-shoulder-envelope"),
            )
            self.assertEqual(
                tuple(item.sweep.names for item in first.representation.shoulder_sweeps),
                (
                    ("torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"),
                ) * 2,
            )
            self.assertEqual(first.metrics["grid"]["samples_per_axis"], 56)
            self.assertTrue(first.metrics["watertight"])
            self.assertEqual(first.metrics["component_count"], 1)
            self.assertTrue(first.metrics["finite_vertices"] and first.metrics["finite_normals"])
            self.assertGreater(first.metrics["signed_volume"], 0.0)
            limb_metrics = first.metrics["successor_region"]
            self.assertEqual(limb_metrics["regional_guide_format"], successor.REGIONAL_GUIDE_FORMAT)
            self.assertEqual(limb_metrics["torso_representation"], successor.TORSO_PROFILE_OPERATION)
            self.assertEqual(limb_metrics["torso_profile_exponent"], successor.TORSO_SUPERELLIPSE_EXPONENT)
            self.assertEqual(len(limb_metrics["torso_section_controls"]), 7)
            self.assertEqual(
                [item["owner"]["role"] for item in limb_metrics["torso_section_controls"]],
                ["pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso"],
            )
            self.assertEqual(limb_metrics["shoulder_representation"], "authored-five-section-frame-aware-profile-sweeps")
            self.assertEqual(limb_metrics["shoulder_sweeps_consumed"], 2)
            self.assertEqual(limb_metrics["shoulder_sweep_order"], ["left-shoulder-envelope", "right-shoulder-envelope"])
            self.assertEqual(limb_metrics["shoulder_sweep_section_counts"], [5, 5])
            self.assertEqual(limb_metrics["limb_sweeps_consumed"], 6)
            self.assertEqual(
                limb_metrics["limb_sweep_order"],
                ["left-upper-arm-route", "left-forearm-route", "right-upper-arm-route", "right-forearm-route", "left-leg", "right-leg"],
            )
            self.assertEqual(limb_metrics["limb_sweep_route_kinds"], ["arm-profile", "arm-profile", "arm-profile", "arm-profile", "limb", "limb"])
            self.assertEqual(limb_metrics["limb_sweep_station_counts"], [3, 3, 3, 3, 5, 5])
            self.assertEqual(limb_metrics["limb_sweep_endpoint_cap_counts"], [2, 2, 2, 2, 2, 2])
            self.assertEqual([len(owners) for owners in limb_metrics["limb_sweep_section_owner_keys"]], [3, 3, 3, 3, 5, 5])
            self.assertEqual(
                [
                    (owner["anchors"][0], owner["role"])
                    for owner in limb_metrics["limb_source_owner_keys"]
                ],
                [
                    ("left", "upper_arm"),
                    ("left", "upper_arm"), ("left", "forearm"),
                    ("right", "upper_arm"),
                    ("right", "upper_arm"), ("right", "forearm"),
                    ("left", "thigh"), ("left", "shin"),
                    ("right", "thigh"), ("right", "shin"),
                ],
            )
            self.assertEqual(limb_metrics["arm_profile"]["route_order"], ["left-upper-arm-route", "left-forearm-route", "right-upper-arm-route", "right-forearm-route"])
            self.assertEqual(limb_metrics["arm_profile"]["topology"], "two-routes-per-side-shared-upper-arm-elbow-seam")
            self.assertEqual(
                [len(item["sections"]) for item in limb_metrics["arm_profile"]["stations"]],
                [5, 5],
            )
            self.assertEqual(limb_metrics["extremity_sweeps_consumed"], 6)
            self.assertEqual(
                limb_metrics["extremity_sweep_order"],
                ["left-hand-attachment", "left-hand-paw", "left-foot", "right-hand-attachment", "right-hand-paw", "right-foot"],
            )
            self.assertEqual(
                limb_metrics["extremity_sweep_kinds"],
                ["hand-attachment", "hand-paw", "foot-chain", "hand-attachment", "hand-paw", "foot-chain"],
            )
            self.assertEqual(limb_metrics["extremity_sweep_station_counts"], [2, 4, 5, 2, 4, 5])
            self.assertEqual(limb_metrics["extremity_sweep_endpoint_cap_counts"], [2, 2, 2, 2, 2, 2])
            self.assertEqual(limb_metrics["extremity_sweep_internal_transition_counts"], [0, 0, 1, 0, 0, 1])
            self.assertEqual(limb_metrics["tail_elements_consumed"], 6)
            self.assertEqual(
                limb_metrics["tail_element_order"],
                ["tail-root-source", "tail-root-attachment", "tail-root-collar", "tail-tip-source", "tail-tip-extension", "tail-tip-cap"],
            )
            self.assertEqual(
                limb_metrics["tail_element_kinds"],
                ["source-centerline", "root-attachment", "root-collar-mass", "source-centerline", "tip-extension", "tip-cap-mass"],
            )
            self.assertEqual(limb_metrics["tail_element_section_counts"], [2, 2, 3, 2, 2, 3])
            self.assertEqual(limb_metrics["tail_element_endpoint_cap_counts"], [2, 2, 2, 2, 2, 2])
            self.assertEqual(limb_metrics["tail_element_internal_transition_counts"], [0, 0, 0, 0, 0, 0])
            self.assertEqual(limb_metrics["replaced_baseline_field_count"], 48)
            self.assertEqual(len(limb_metrics["replaced_baseline_recipes"]), 28)
            self.assertEqual(first.metrics["temporary_bridge"]["field_count"], 4)
            np.testing.assert_array_equal(first.vertices, second.vertices)
            np.testing.assert_array_equal(first.faces, second.faces)
            np.testing.assert_array_equal(first.normals, second.normals)
            self.assertEqual(first.metrics, second.metrics)
            self.assertEqual(first.metrics["successor_region"]["torso_section_names"][-1], "upper-ribcage-shoulder")
            head_neck_metrics = limb_metrics["head_neck"]
            self.assertEqual(head_neck_metrics["profile_format"], surface_preview.AUTHORED_HEAD_NECK_PROFILE_FORMAT)
            self.assertEqual(head_neck_metrics["operation"], successor._HEAD_NECK_PROFILE_OPERATION)
            self.assertEqual(head_neck_metrics["sections_consumed"], 8)
            self.assertEqual(head_neck_metrics["connections_consumed"], 7)
            self.assertEqual(
                [route["name"] for route in head_neck_metrics["route_topology"]],
                ["vertical-neck-cranium", "forward-muzzle"],
            )
            self.assertEqual(
                [item["section_index"] for item in head_neck_metrics["sections"]],
                list(range(8)),
            )
            signatures.append((first.vertices.shape, first.metrics["signed_volume"], tuple(first.metrics["grid"]["bounds_max"])))
        self.assertEqual(len(signatures), 4)
        self.assertGreater(len(set(signatures)), 1)

    def test_default_successor_capture_frame_matches_baseline_frame(self) -> None:
        canonical_fields = tuple(
            surface_preview._compile_hybrid_guide(
                surface_preview._derive_hybrid_guides(self.form, descriptors)
            )
            for _, descriptors, _ in self.form.variants
        )
        baseline_bounds = surface_preview._shared_render_bounds(
            canonical_fields, surface_preview.DEFAULT_PADDING
        )
        successor_bounds = surface_preview._shared_render_bounds(
            canonical_fields, successor.DEFAULT_CAPTURE_PADDING
        )
        self.assertEqual(successor.DEFAULT_CAPTURE_PADDING, surface_preview.DEFAULT_PADDING)
        np.testing.assert_array_equal(successor_bounds[0], baseline_bounds[0])
        np.testing.assert_array_equal(successor_bounds[1], baseline_bounds[1])

    def test_generator_emits_explicit_successor_and_bridge_metadata(self) -> None:
        with _native_temporary_directory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_bytes(surface_preview._canonical(fixture.make_varied_payload()))
            existing = root / "existing"
            existing.mkdir()
            sentinel = existing / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(successor.SuccessorPreviewError, "refusing to overwrite"):
                successor.generate(source, existing, padding=0.5)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            failed = root / "failed"
            before_failed_run = sorted(path.name for path in root.iterdir())
            with self.assertRaisesRegex(successor.SuccessorPreviewError, "sampling configuration"):
                successor.generate(source, failed, samples=19, padding=0.5)
            self.assertFalse(failed.exists())
            self.assertEqual(sorted(path.name for path in root.iterdir()), before_failed_run)
            first = root / "first"
            second = root / "second"
            first_manifest = successor.generate(source, first, padding=0.5)
            second_manifest = successor.generate(source, second, padding=0.5)
            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(
                [item["source_variant_sha256"] for item in first_manifest["variants"]],
                [item["source_variant_sha256"] for item in second_manifest["variants"]],
            )
            self.assertEqual(successor.FORMAT, "creature-kernel.disposable-successor-surface-preview.v6")
            self.assertEqual(first_manifest["format"], successor.FORMAT)
            self.assertEqual(first_manifest["consumer_id"], successor.CONSUMER_ID)
            self.assertEqual(first_manifest["generator"]["samples_per_axis"], 56)
            self.assertEqual(first_manifest["generator"]["padding"], 0.5)
            self.assertEqual(first_manifest["generator"]["capture_padding"], successor.DEFAULT_CAPTURE_PADDING)
            self.assertEqual([item["id"] for item in first_manifest["variants"]], list(surface_preview.VARIANT_IDS))
            self.assertEqual(len(first_manifest["variants"]), 4)
            self.assertEqual(
                sorted(path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()),
                sorted(
                    ["successor-surface-manifest.json"]
                    + [
                        f"{variant_id}/{name}"
                        for variant_id in surface_preview.VARIANT_IDS
                        for name in ("guide-skin-composite.png", "metrics.json", "successor.json", "surface.ply")
                    ]
                ),
            )
            self.assertEqual(
                sorted(path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()),
                sorted(path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()),
            )
            for first_path in first.rglob("*"):
                if first_path.is_file():
                    self.assertEqual(first_path.read_bytes(), (second / first_path.relative_to(first)).read_bytes())
            self.assertNotIn(str(first), (first / "successor-surface-manifest.json").read_text())
            canonical_fields = tuple(
                surface_preview._compile_hybrid_guide(
                    surface_preview._derive_hybrid_guides(self.form, descriptors)
                )
                for _, descriptors, _ in self.form.variants
            )
            expected_bounds = surface_preview._shared_render_bounds(
                canonical_fields, successor.DEFAULT_CAPTURE_PADDING
            )
            baseline_default_bounds = surface_preview._shared_render_bounds(
                canonical_fields, surface_preview.DEFAULT_PADDING
            )
            expected_bounds_json = {
                "min": [float(value) for value in expected_bounds[0]],
                "max": [float(value) for value in expected_bounds[1]],
            }
            self.assertEqual(expected_bounds_json, {
                "min": [float(value) for value in baseline_default_bounds[0]],
                "max": [float(value) for value in baseline_default_bounds[1]],
            })
            self.assertEqual(first_manifest["shared_render_bounds"], expected_bounds_json)
            self.assertEqual(first_manifest["canvas"], {"width": surface_preview.CANVAS[0], "height": surface_preview.CANVAS[1], "mode": "RGB"})
            self.assertEqual(first_manifest["projections"], surface_preview._projection_json())
            self.assertEqual(first_manifest["layout"], surface_preview._layout_json())
            self.assertEqual([item["name"] for item in first_manifest["projections"]], ["front", "side", "three-quarter"])
            self.assertEqual(first_manifest["layout"]["panel_order"], [
                "front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin",
            ])
            self.assertTrue(all(not Path(item["path"]).is_absolute() for variant in first_manifest["variants"] for item in variant["inventory"]))
            source_variant_hashes = {
                variant_id: hashlib.sha256(successor._canonical(raw_variant)).hexdigest()
                for variant_id, _, raw_variant in self.form.variants
            }
            self.assertEqual(len(source_variant_hashes), 4)
            self.assertEqual(len(set(source_variant_hashes.values())), 4)
            for digest in source_variant_hashes.values():
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
            expected_sampling_bounds = {}
            for variant_id, descriptors, _ in self.form.variants:
                guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
                fields = surface_preview._compile_hybrid_guide(guide)
                region = successor.compile_successor_region(guide, fields)
                expected_sampling_bounds[variant_id] = successor._combined_bounds(
                    successor._make_components(region, successor.DEFAULT_SMOOTH_K), successor.DEFAULT_PADDING
                )
            for variant in first_manifest["variants"]:
                self.assertEqual(variant["profile_id"], variant["id"])
                self.assertEqual(variant["source_variant_sha256"], source_variant_hashes[variant["id"]])
                variant_dir = first / variant["id"]
                self.assertEqual(
                    sorted(path.name for path in variant_dir.iterdir()),
                    ["guide-skin-composite.png", "metrics.json", "successor.json", "surface.ply"],
                )
                self.assertEqual(len(variant["inventory"]), 4)
                inventory_by_kind = {item["kind"]: item for item in variant["inventory"]}
                self.assertEqual(set(inventory_by_kind), {"ply", "metrics", "successor-consumer-sidecar", "guide-skin-composite-png"})
                png_inventory = inventory_by_kind["guide-skin-composite-png"]
                png_path = variant_dir / "guide-skin-composite.png"
                self.assertEqual(png_inventory["path"], f"{variant['id']}/guide-skin-composite.png")
                self.assertEqual(png_inventory["bytes"], png_path.stat().st_size)
                self.assertEqual(png_inventory["sha256"], hashlib.sha256(png_path.read_bytes()).hexdigest())
                self.assertEqual(png_inventory["width"], surface_preview.CANVAS[0])
                self.assertEqual(png_inventory["height"], surface_preview.CANVAS[1])
                self.assertEqual(png_inventory["views"], ["front", "side", "three-quarter"])
                self.assertEqual(png_inventory["panels_per_view"], 2)
                self.assertEqual(png_inventory["mode"], "RGB")
                with Image.open(png_path) as image:
                    self.assertEqual(image.size, surface_preview.CANVAS)
                    self.assertEqual(image.mode, "RGB")
                    image.verify()
                sidecar = json.loads((variant_dir / "successor.json").read_text())
                metrics_payload = json.loads((variant_dir / "metrics.json").read_text())
                sampling_lower, sampling_upper = expected_sampling_bounds[variant["id"]]
                self.assertEqual(
                    metrics_payload["grid"]["bounds_min"],
                    [float(value) for value in sampling_lower],
                )
                self.assertEqual(
                    metrics_payload["grid"]["bounds_max"],
                    [float(value) for value in sampling_upper],
                )
                self.assertEqual(sidecar["format"], successor.FORMAT)
                self.assertEqual(sidecar["variant_id"], variant["id"])
                self.assertEqual(sidecar["profile_id"], variant["profile_id"])
                self.assertEqual(sidecar["source_variant_sha256"], variant["source_variant_sha256"])
                self.assertEqual(sidecar["consumer_id"], successor.CONSUMER_ID)
                self.assertEqual(sidecar["capture"]["canvas"], first_manifest["canvas"])
                self.assertEqual(sidecar["capture"]["projections"], first_manifest["projections"])
                self.assertEqual(sidecar["capture"]["layout"], first_manifest["layout"])
                self.assertEqual(sidecar["capture"]["shared_render_bounds"], expected_bounds_json)
                self.assertEqual(sidecar["torso"]["representation"], successor.TORSO_PROFILE_OPERATION)
                self.assertEqual(sidecar["torso"]["regional_guide_format"], successor.REGIONAL_GUIDE_FORMAT)
                self.assertEqual(sidecar["torso"]["superellipse_exponent"], successor.TORSO_SUPERELLIPSE_EXPONENT)
                self.assertEqual(sidecar["torso"]["sections_consumed"], 7)
                self.assertEqual(len(sidecar["torso"]["section_controls"]), 7)
                self.assertEqual(
                    sidecar["shoulders"],
                    {
                        "representation": "authored-five-section-frame-aware-profile-sweeps",
                        "sweeps_consumed": 2,
                        "sweep_order": ["left-shoulder-envelope", "right-shoulder-envelope"],
                        "section_counts": [5, 5],
                        "section_names": [
                            ["torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"],
                            ["torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"],
                        ],
                    },
                )
                self.assertEqual(sidecar["head_neck"]["profile_format"], surface_preview.AUTHORED_HEAD_NECK_PROFILE_FORMAT)
                self.assertEqual(sidecar["head_neck"]["operation"], successor._HEAD_NECK_PROFILE_OPERATION)
                self.assertEqual(sidecar["head_neck"]["regional_guide_format"], successor.REGIONAL_GUIDE_FORMAT)
                self.assertEqual(sidecar["head_neck"]["sections_consumed"], 8)
                self.assertEqual(sidecar["head_neck"]["connections_consumed"], 7)
                self.assertEqual(
                    [item["section_index"] for item in sidecar["head_neck"]["sections"]],
                    list(range(8)),
                )
                self.assertEqual(
                    [item["name"] for item in sidecar["head_neck"]["route_topology"]],
                    ["vertical-neck-cranium", "forward-muzzle"],
                )
                self.assertEqual(
                    [item["section_indices"] for item in sidecar["head_neck"]["route_topology"]],
                    [[0, 1, 2, 3, 4], [3, 5, 6, 7]],
                )
                self.assertTrue(all(set(item["lineage"]) == {"lateral", "up", "forward"} for item in sidecar["head_neck"]["sections"]))
                self.assertEqual(sidecar["limbs"]["sweeps_consumed"], 6)
                self.assertEqual(sidecar["limbs"]["sweep_order"], ["left-upper-arm-route", "left-forearm-route", "right-upper-arm-route", "right-forearm-route", "left-leg", "right-leg"])
                self.assertEqual(sidecar["limbs"]["route_kinds"], ["arm-profile", "arm-profile", "arm-profile", "arm-profile", "limb", "limb"])
                self.assertEqual(sidecar["limbs"]["station_counts"], [3, 3, 3, 3, 5, 5])
                self.assertEqual(
                    sidecar["limbs"]["station_names"],
                    [
                        ["upper-arm-start", "upper-arm-midpoint", "elbow"],
                        ["elbow", "forearm-midpoint", "forearm-distal"],
                        ["upper-arm-start", "upper-arm-midpoint", "elbow"],
                        ["elbow", "forearm-midpoint", "forearm-distal"],
                        ["thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"],
                        ["thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"],
                    ],
                )
                self.assertEqual(sidecar["limbs"]["endpoint_cap_counts"], [2, 2, 2, 2, 2, 2])
                self.assertEqual(len(sidecar["limbs"]["section_owner_keys"]), 6)
                self.assertEqual([len(owners) for owners in sidecar["limbs"]["section_owner_keys"]], [3, 3, 3, 3, 5, 5])
                self.assertEqual(sidecar["limbs"]["arm_profile"]["format"], surface_preview.AUTHORED_ARM_PROFILE_FORMAT)
                self.assertEqual(sidecar["limbs"]["arm_profile"]["regional_guide_format"], successor.REGIONAL_GUIDE_FORMAT)
                self.assertEqual(sidecar["limbs"]["arm_profile"]["route_order"], ["left-upper-arm-route", "left-forearm-route", "right-upper-arm-route", "right-forearm-route"])
                self.assertEqual(sidecar["extremities"]["sweeps_consumed"], 6)
                self.assertEqual(
                    sidecar["extremities"]["sweep_order"],
                    ["left-hand-attachment", "left-hand-paw", "left-foot", "right-hand-attachment", "right-hand-paw", "right-foot"],
                )
                self.assertEqual(
                    sidecar["extremities"]["sweep_kinds"],
                    ["hand-attachment", "hand-paw", "foot-chain", "hand-attachment", "hand-paw", "foot-chain"],
                )
                self.assertEqual(sidecar["extremities"]["station_counts"], [2, 4, 5, 2, 4, 5])
                self.assertEqual(sidecar["extremities"]["endpoint_cap_counts"], [2, 2, 2, 2, 2, 2])
                self.assertEqual(sidecar["extremities"]["internal_transition_counts"], [0, 0, 1, 0, 0, 1])
                self.assertEqual(sidecar["tail"]["representation"], "shared-guide-derived-profile-sweep-elements")
                self.assertEqual(sidecar["tail"]["elements_consumed"], 6)
                self.assertEqual(
                    sidecar["tail"]["element_order"],
                    ["tail-root-source", "tail-root-attachment", "tail-root-collar", "tail-tip-source", "tail-tip-extension", "tail-tip-cap"],
                )
                self.assertEqual(
                    sidecar["tail"]["element_kinds"],
                    ["source-centerline", "root-attachment", "root-collar-mass", "source-centerline", "tip-extension", "tip-cap-mass"],
                )
                self.assertEqual(sidecar["tail"]["section_counts"], [2, 2, 3, 2, 2, 3])
                self.assertEqual(sidecar["tail"]["endpoint_cap_counts"], [2, 2, 2, 2, 2, 2])
                self.assertEqual(sidecar["tail"]["internal_transition_counts"], [0, 0, 0, 0, 0, 0])
                self.assertEqual(len(sidecar["replaced_baseline_recipes"]), 28)
                self.assertTrue(sidecar["temporary_bridge"]["enabled"])
                self.assertEqual(sidecar["temporary_bridge"]["field_count"], 4)

    def test_generator_rejects_oversized_input_before_parse_or_staging(self) -> None:
        with _native_temporary_directory() as directory:
            root = Path(directory)
            source = root / "oversized.json"
            source.write_bytes(b"not-json" + b"x" * surface_preview.MAX_INPUT_BYTES)
            output = root / "output"

            with mock.patch.object(successor.json, "loads", side_effect=AssertionError("JSON parse was reached")), mock.patch.object(
                successor, "build_variant", side_effect=AssertionError("mesh work was reached")
            ):
                with self.assertRaisesRegex(successor.SuccessorPreviewError, "^input exceeds bounded size$"):
                    successor.generate(source, output, padding=0.5)

            self.assertFalse(output.exists())
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["oversized.json"])

    def test_bounded_input_reader_accepts_the_exact_inclusive_limit(self) -> None:
        with _native_temporary_directory() as directory:
            source = Path(directory) / "exact-limit.json"
            source.write_bytes(b"x" * surface_preview.MAX_INPUT_BYTES)

            data = successor._read_bounded_input(source)

            self.assertEqual(len(data), surface_preview.MAX_INPUT_BYTES)

    def test_generator_rejects_unexpected_staged_entries_and_cleans(self) -> None:
        with _native_temporary_directory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_bytes(surface_preview._canonical(fixture.make_varied_payload()))

            def fake_build_variant(form, descriptors, **_kwargs):
                guide = surface_preview._derive_hybrid_guides(form, descriptors)
                fields = surface_preview._compile_hybrid_guide(guide)
                region = successor.compile_successor_region(guide, fields)
                metrics = {
                    "successor_region": {
                        "torso_section_controls": _serialized_torso_section_controls(region),
                        "tail_element_controls": [],
                        "tail_tip_shared_endpoint": {},
                    },
                    "temporary_bridge": {"enabled": True, "field_count": 4},
                }
                return successor.SuccessorMesh(
                    np.empty((0, 3), dtype=np.float64),
                    np.empty((0, 3), dtype=np.int64),
                    np.empty((0, 3), dtype=np.float64),
                    (),
                    metrics,
                    region,
                    {},
                )

            for entry_kind in ("extra", "symlink"):
                with self.subTest(entry_kind=entry_kind):
                    output = root / entry_kind

                    def fake_render(path, *args, **kwargs):
                        del args, kwargs
                        path.write_bytes(b"mock-png")
                        injected = path.parent / f"unexpected-{entry_kind}"
                        if entry_kind == "extra":
                            injected.write_bytes(b"unexpected")
                        else:
                            try:
                                injected.symlink_to(path.name)
                            except (OSError, NotImplementedError) as exc:
                                raise unittest.SkipTest(f"symlinks unavailable: {exc}") from exc

                    with mock.patch.object(successor, "build_variant", side_effect=fake_build_variant), mock.patch.object(
                        surface_preview, "_render", side_effect=fake_render
                    ):
                        with self.assertRaisesRegex(successor.SuccessorPreviewError, "staging bundle contains a symlink|explicit artifact inventory"):
                            successor.generate(source, output, padding=0.5)
                    self.assertFalse(output.exists())
                    self.assertEqual(sorted(path.name for path in root.iterdir()), ["input.json"])

    def test_generator_cleans_staging_after_render_failure(self) -> None:
        with _native_temporary_directory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_bytes(surface_preview._canonical(fixture.make_varied_payload()))
            output = root / "render-failure"

            def fake_build_variant(form, descriptors, **_kwargs):
                guide = surface_preview._derive_hybrid_guides(form, descriptors)
                fields = surface_preview._compile_hybrid_guide(guide)
                region = successor.compile_successor_region(guide, fields)
                metrics = {
                    "successor_region": {
                        "torso_section_controls": _serialized_torso_section_controls(region),
                        "tail_element_controls": [],
                        "tail_tip_shared_endpoint": {},
                    },
                    "temporary_bridge": {"enabled": True, "field_count": 4},
                }
                return successor.SuccessorMesh(
                    np.empty((0, 3), dtype=np.float64),
                    np.empty((0, 3), dtype=np.int64),
                    np.empty((0, 3), dtype=np.float64),
                    (),
                    metrics,
                    region,
                    {},
                )

            def failing_render(path, *args, **kwargs):
                del args, kwargs
                self.assertTrue((path.parent / "surface.ply").is_file())
                self.assertTrue((path.parent / "metrics.json").is_file())
                self.assertTrue((path.parent / "successor.json").is_file())
                path.write_bytes(b"partial-png")
                raise RuntimeError("injected render failure")

            with mock.patch.object(successor, "build_variant", side_effect=fake_build_variant), mock.patch.object(
                surface_preview, "_render", side_effect=failing_render
            ):
                with self.assertRaisesRegex(RuntimeError, "injected render failure"):
                    successor.generate(source, output, padding=0.5)
            self.assertFalse(output.exists())
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["input.json"])

    def test_rotated_profile_sweep_is_rigid_transform_invariant(self) -> None:
        angle = 0.63
        rotation_axis = np.asarray((1.0, 2.0, 3.0))
        rotation_axis /= np.linalg.norm(rotation_axis)
        skew = np.asarray(((0.0, -rotation_axis[2], rotation_axis[1]), (rotation_axis[2], 0.0, -rotation_axis[0]), (-rotation_axis[1], rotation_axis[0], 0.0)))
        rotation = np.eye(3) * np.cos(angle) + (1.0 - np.cos(angle)) * np.outer(rotation_axis, rotation_axis) + np.sin(angle) * skew
        translation = np.asarray((2.5, -1.25, 0.75))
        base = _test_profile_sweep()
        rotated = _test_profile_sweep((rotation, translation))
        self.assertFalse(np.allclose(rotated.sections[0].tangent, (0.0, 1.0, 0.0)))
        self.assertAlmostEqual(float(np.linalg.det(rotation)), 1.0, places=12)
        points = np.asarray(((0.0, 0.5, 0.0), (0.35, 1.4, 0.2), (0.0, 2.4, 0.0), (0.0, -0.6, 0.0), (1.5, 1.0, -0.8)))
        transformed_points = points @ rotation.T + translation
        np.testing.assert_allclose(successor._profile_sweep_field(points, base), successor._profile_sweep_field(transformed_points, rotated), rtol=0.0, atol=1.0e-12)
        rotated_lower, rotated_upper = successor._profile_sweep_bounds(rotated)
        transformed_controls = np.asarray([
            value
            for section in rotated.sections
            for value in (
                np.asarray(section.center) + section.transverse_radii[0] * np.asarray(section.transverse_axes[0]),
                np.asarray(section.center) - section.transverse_radii[1] * np.asarray(section.transverse_axes[1]),
            )
        ])
        self.assertTrue(np.all(transformed_controls >= rotated_lower - 1.0e-12))
        self.assertTrue(np.all(transformed_controls <= rotated_upper + 1.0e-12))

    def test_profile_frames_caps_bounds_and_owner_ties_are_deterministic(self) -> None:
        sweep = _test_profile_sweep()
        successor._validate_profile_sweep(sweep)
        for section in sweep.sections:
            tangent = np.asarray(section.tangent)
            first = np.asarray(section.transverse_axes[0])
            second = np.asarray(section.transverse_axes[1])
            np.testing.assert_allclose(np.linalg.norm((tangent, first, second), axis=1), (1.0, 1.0, 1.0), rtol=0.0, atol=1.0e-12)
            np.testing.assert_allclose((np.dot(tangent, first), np.dot(tangent, second), np.dot(first, second)), (0.0, 0.0, 0.0), rtol=0.0, atol=1.0e-12)
        midpoint = np.asarray(((0.0, 0.5, 0.0), (0.0, 1.5, 0.0)))
        self.assertEqual(successor._loft_owner_keys(midpoint, sweep)[0], sweep.owners[0].key)
        self.assertEqual(successor._loft_owner_keys(midpoint, sweep)[1], sweep.owners[1].key)
        endpoint = np.asarray(sweep.sections[0].center) + sweep.sections[0].transverse_radii[0] * np.asarray(sweep.sections[0].transverse_axes[0])
        self.assertAlmostEqual(float(successor._profile_sweep_field(endpoint.reshape(1, 3), sweep)[0]), 0.0, places=12)
        center = np.asarray(sweep.sections[0].center)
        outward = center - 0.5 * np.asarray(sweep.sections[0].tangent)
        self.assertAlmostEqual(float(successor._profile_sweep_field(outward.reshape(1, 3), sweep)[0]), 0.0, places=12)
        beyond = center - 0.6 * np.asarray(sweep.sections[0].tangent)
        self.assertGreater(float(successor._profile_sweep_field(beyond.reshape(1, 3), sweep)[0]), 0.0)
        internal_outside = np.asarray((0.0, 0.1, 0.0))
        self.assertTrue(np.isposinf(float(successor._profile_span_field(internal_outside.reshape(1, 3), sweep.sections[1], sweep.sections[2])[0])))
        self.assertTrue(np.isfinite(float(successor._profile_sweep_field(internal_outside.reshape(1, 3), sweep)[0])))
        lower, upper = successor._profile_sweep_bounds(sweep)
        controls = []
        for section in sweep.sections:
            controls.extend((
                np.asarray(section.center) + section.transverse_radii[0] * np.asarray(section.transverse_axes[0]),
                np.asarray(section.center) - section.transverse_radii[1] * np.asarray(section.transverse_axes[1]),
            ))
        controls.append(np.asarray(sweep.endpoint_caps[0].center) - sweep.endpoint_caps[0].axial_radius * np.asarray(sweep.endpoint_caps[0].outward_tangent))
        controls = np.asarray(controls)
        self.assertTrue(np.all(controls >= lower - 1.0e-12))
        self.assertTrue(np.all(controls <= upper + 1.0e-12))

    def test_profile_sweep_rejects_malformed_frames_spans_radii_and_caps(self) -> None:
        valid = _test_profile_sweep()
        cases = {
            "duplicate-path": replace(valid, _validated=False, sections=tuple(replace(item, path_length=0.0) if index == 1 else item for index, item in enumerate(valid.sections))),
            "degenerate-span": replace(valid, _validated=False, sections=tuple(replace(item, center=valid.sections[0].center) if index == 1 else item for index, item in enumerate(valid.sections))),
            "bad-frame": replace(valid, _validated=False, sections=(replace(valid.sections[0], tangent=(0.0, 2.0, 0.0)),) + valid.sections[1:]),
            "wrong-centerline-tangent": replace(valid, _validated=False, sections=(replace(valid.sections[0], tangent=(1.0, 0.0, 0.0)),) + valid.sections[1:]),
            "non-orthogonal-frame": replace(valid, _validated=False, sections=(replace(valid.sections[0], transverse_axes=((2.0 ** -0.5, 0.0, 2.0 ** -0.5), valid.sections[0].transverse_axes[1])),) + valid.sections[1:]),
            "bad-radii": replace(valid, _validated=False, sections=(replace(valid.sections[0], transverse_radii=(0.0, 0.5)),) + valid.sections[1:]),
            "bad-cap": replace(valid, _validated=False, endpoint_caps=(replace(valid.endpoint_caps[0], axial_radius=0.0), valid.endpoint_caps[1])),
        }
        for name, malformed in cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor._validate_profile_sweep(malformed)

    def test_bent_profile_has_one_bounded_joint_transition_without_wedge(self) -> None:
        bent = _bent_test_profile_sweep()
        straight = _test_profile_sweep()
        self.assertEqual(len(bent.internal_transitions), 1)
        self.assertEqual(bent.internal_transitions[0].section_index, 1)
        self.assertEqual(bent.internal_transitions[0].owner, bent.sections[1].owner)
        self.assertEqual(bent.internal_transitions[0].transverse_radii, bent.sections[1].transverse_radii)
        self.assertEqual(bent.internal_transitions[0].axial_radius, min(bent.sections[1].transverse_radii))
        self.assertEqual(straight.internal_transitions, ())

        reproduced = np.asarray((0.1, -0.1, 0.0))
        value = float(successor._profile_sweep_field(reproduced.reshape(1, 3), bent)[0])
        self.assertTrue(math.isfinite(value))
        self.assertLess(value, 0.0)
        across_joint = np.asarray(((-1.0e-7, -0.1, 0.0), (1.0e-7, -0.1, 0.0)))
        across_values = successor._profile_sweep_field(across_joint, bent)
        self.assertTrue(np.all(np.isfinite(across_values)))
        self.assertTrue(np.all(across_values < 0.0))

    def test_rotated_between_sections_bounds_use_conservative_elliptical_radius(self) -> None:
        sweep = _rotated_between_sections_profile_sweep()
        lower, upper = successor._profile_sweep_bounds(sweep)
        conservative_radius = math.hypot(1.0, 0.8)
        self.assertGreaterEqual(float(upper[0]), conservative_radius - 1.0e-12)
        self.assertLessEqual(float(lower[0]), -conservative_radius + 1.0e-12)

    def test_paired_transverse_frame_flip_interpolates_without_cancellation(self) -> None:
        base = _test_profile_sweep()
        last = base.sections[-1]
        flipped_last = replace(last, transverse_axes=tuple(tuple(-value for value in axis) for axis in last.transverse_axes))
        flipped_cap = replace(base.endpoint_caps[-1], transverse_axes=flipped_last.transverse_axes)
        flipped = successor._ProfileSweep(
            base.sections[:-1] + (flipped_last,),
            (base.endpoint_caps[0], flipped_cap),
        )
        points = np.asarray(((0.0, 1.5, 0.0), (0.35, 1.75, 0.2), (0.0, 2.4, 0.0)))
        base_values = successor._profile_sweep_field(points, base)
        flipped_values = successor._profile_sweep_field(points, flipped)
        self.assertTrue(np.all(np.isfinite(flipped_values)))
        np.testing.assert_allclose(flipped_values, base_values, rtol=0.0, atol=1.0e-12)

    def test_atomic_directory_collision_preserves_stage_and_target(self) -> None:
        with _native_temporary_directory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            stage.mkdir()
            target.mkdir()
            (stage / "staged.txt").write_text("stage", encoding="utf-8")
            (target / "existing.txt").write_text("target", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                successor._atomic_rename_noreplace(stage, target)
            self.assertEqual((stage / "staged.txt").read_text(encoding="utf-8"), "stage")
            self.assertEqual((target / "existing.txt").read_text(encoding="utf-8"), "target")


if __name__ == "__main__":
    unittest.main()

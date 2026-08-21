from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SPEC = importlib.util.spec_from_file_location("successor_fixture", Path(__file__).with_name("test_surface_preview.py"))
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
fixture = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixture)
sys.path.insert(0, str(ROOT))
import surface_preview  # noqa: E402
import successor_surface_preview as successor  # noqa: E402


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


class SuccessorSurfacePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.form = surface_preview.validate_envelope(fixture.make_varied_payload())

    def test_successor_consumes_ordered_cage_and_real_shoulder_inputs(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline_fields = surface_preview._compile_hybrid_guide(guide)
        region = successor.compile_successor_region(guide, baseline_fields)

        self.assertEqual(region.consumer_id, successor.CONSUMER_ID)
        self.assertEqual(region.region_id, successor.SUCCESSOR_REGION_ID)
        self.assertEqual(region.sections_consumed, 7)
        self.assertEqual(region.loft.internal_transitions, ())
        self.assertEqual(region.section_names, (
            "lower-pelvis", "upper-pelvis", "lower-abdomen", "waist-abdomen",
            "upper-abdomen", "lower-ribcage", "upper-ribcage-shoulder",
        ))
        self.assertEqual(region.shoulder_inputs_consumed, 16)
        self.assertEqual({span.curve_name for span in region.shoulder_spans}, {"anterior-support", "posterior-return", "deltoid-sweep"})
        self.assertEqual({span.side for span in region.shoulder_spans}, {"left", "right"})
        self.assertEqual(
            tuple(item.recipe for item in region.head_neck_sweeps),
            ("cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar"),
        )
        self.assertEqual(tuple(len(item.sweep.sections) for item in region.head_neck_sweeps), (5, 4, 2, 2, 3))
        self.assertNotIn("torso-cage", {field.recipe for field in region.bridge_fields})
        self.assertNotIn("deltoid-sweep-1", {field.recipe for field in region.bridge_fields})
        self.assertEqual(
            {field.recipe for field in region.bridge_fields} &
            {"cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar"},
            set(),
        )
        self.assertEqual(len(region.bridge_fields), len(baseline_fields) - 30)
        self.assertEqual(len(region.limb_sweeps), 4)

        # Changing an actual support profile changes the successor skin field;
        # the support is not merely emitted as an x-ray guide line.
        point = np.asarray(region.shoulder_spans[0].start, dtype=np.float64).reshape(1, 3)
        before = successor._successor_region_field(point, region, 0.10)
        changed = region.shoulder_spans[0].__class__(
            region.shoulder_spans[0].side,
            region.shoulder_spans[0].curve_name,
            region.shoulder_spans[0].span_index,
            region.shoulder_spans[0].owner,
            region.shoulder_spans[0].start,
            region.shoulder_spans[0].end,
            region.shoulder_spans[0].start_radius * 1.35,
            region.shoulder_spans[0].end_radius,
        )
        changed_region = region.__class__(
            region.consumer_id, region.region_id, region.loft,
            (changed,) + region.shoulder_spans[1:], region.bridge_fields,
            region.replaced_baseline_recipes, region.source_owners,
        )
        after = successor._successor_region_field(point, changed_region, 0.10)
        self.assertFalse(np.array_equal(before, after))

    def test_head_neck_sweeps_retain_guide_controls_and_shared_topology(self) -> None:
        topologies = []
        for variant_id, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            topologies.append((tuple(item.recipe for item in region.head_neck_sweeps), tuple(len(item.sweep.sections) for item in region.head_neck_sweeps)))
            head = guide.head_guide
            cranium, muzzle, head_transition, neck_transition, collar = region.head_neck_sweeps
            self.assertIs(cranium.owner, head.head_owner)
            self.assertIs(muzzle.owner, head.head_owner)
            self.assertIs(head_transition.owner, head.head_owner)
            self.assertIs(neck_transition.owner, head.neck_owner)
            self.assertIs(collar.owner, head.neck_owner)
            np.testing.assert_allclose(head_transition.sweep.sections[0].center, head.head_transition[0])
            np.testing.assert_allclose(head_transition.sweep.sections[-1].center, head.head_transition[1])
            np.testing.assert_allclose(neck_transition.sweep.sections[0].center, head.neck_transition[0])
            np.testing.assert_allclose(neck_transition.sweep.sections[-1].center, head.neck_transition[1])
            self.assertEqual(head_transition.sweep.sections[0].transverse_radii, (head.head_transition_thickness[0],) * 2)
            self.assertEqual(head_transition.sweep.sections[-1].transverse_radii, (head.head_transition_thickness[1],) * 2)
            self.assertEqual(neck_transition.sweep.sections[0].transverse_radii, (head.neck_transition_thickness[0],) * 2)
            self.assertEqual(neck_transition.sweep.sections[-1].transverse_radii, (head.neck_transition_thickness[1],) * 2)
            # The mass profiles are guide-derived and have more than one
            # station, rather than reproducing the baseline ellipsoids.
            self.assertNotEqual(tuple(cranium.sweep.sections[0].center), tuple(cranium.sweep.sections[-1].center))
            self.assertNotEqual(tuple(muzzle.sweep.sections[0].center), tuple(muzzle.sweep.sections[-1].center))
            muzzle_section = muzzle.sweep.sections[1]
            self.assertEqual(
                muzzle_section.transverse_radii,
                (head.muzzle_radii[0] * successor._MUZZLE_PROFILE[1][1], head.muzzle_radii[1] * successor._MUZZLE_PROFILE[1][2]),
            )
            muzzle_tangent = np.asarray(muzzle_section.tangent)
            muzzle_first, muzzle_second = (np.asarray(axis) for axis in muzzle_section.transverse_axes)
            np.testing.assert_allclose(muzzle_tangent, np.asarray(head.axes.forward), rtol=0.0, atol=1.0e-12)
            np.testing.assert_allclose(
                (np.linalg.norm(muzzle_tangent), np.linalg.norm(muzzle_first), np.linalg.norm(muzzle_second)),
                (1.0, 1.0, 1.0), rtol=0.0, atol=1.0e-12,
            )
            np.testing.assert_allclose(
                (np.dot(muzzle_tangent, muzzle_first), np.dot(muzzle_tangent, muzzle_second), np.dot(muzzle_first, muzzle_second)),
                (0.0, 0.0, 0.0), rtol=0.0, atol=1.0e-12,
            )
            self.assertAlmostEqual(abs(float(np.dot(muzzle_first, np.asarray(head.axes.lateral)))), 1.0, places=12)
            self.assertAlmostEqual(abs(float(np.dot(muzzle_second, np.asarray(head.axes.up)))), 1.0, places=12)
            self.assertLess(
                muzzle.sweep.sections[-1].transverse_radii[0],
                muzzle.sweep.sections[1].transverse_radii[0],
            )
            collar_section = collar.sweep.sections[1]
            self.assertEqual(
                collar_section.transverse_radii,
                (
                    head.neck_collar_radii[0] * successor._COLLAR_TRANSVERSE_SCALE * successor._COLLAR_PROFILE[1][1],
                    head.neck_collar_radii[2] * successor._COLLAR_TRANSVERSE_SCALE * successor._COLLAR_PROFILE[1][2],
                ),
            )
            source_keys = {descriptor.key for descriptor in guide.source_descriptors}
            self.assertTrue(all(item.owner.key in source_keys for item in region.head_neck_sweeps))
        self.assertEqual(len(set(topologies)), 1)

    def test_head_neck_invalid_guide_dimensions_fail_closed(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        invalid_head = replace(guide.head_guide, muzzle_radii=(float("nan"), 0.2, 0.2))
        invalid_guide = replace(guide, head_guide=invalid_head)
        with self.assertRaises(successor.SuccessorPreviewError):
            successor._make_head_neck_sweeps(invalid_guide)

    def test_head_neck_sweeps_are_consumed_by_components_and_composed_field(self) -> None:
        expected_recipes = {"cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar"}
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

    def test_limb_sweeps_have_shared_five_station_topology_and_proximal_joint_ownership(self) -> None:
        expected_order = ("left-arm", "left-leg", "right-arm", "right-leg")
        expected_names = {
            "left-arm": ("upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "forearm-distal"),
            "right-arm": ("upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "forearm-distal"),
            "left-leg": ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
            "right-leg": ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
        }
        expected_roles = {
            "left-arm": ("upper_arm", "upper_arm", "upper_arm", "forearm", "forearm"),
            "right-arm": ("upper_arm", "upper_arm", "upper_arm", "forearm", "forearm"),
            "left-leg": ("thigh", "thigh", "thigh", "shin", "shin"),
            "right-leg": ("thigh", "thigh", "thigh", "shin", "shin"),
        }
        topologies = []
        for _, descriptors, _ in self.form.variants:
            guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
            region = successor.compile_successor_region(guide)
            self.assertEqual(tuple(item.chain_name for item in region.limb_sweeps), expected_order)
            topology = []
            for item in region.limb_sweeps:
                self.assertEqual(item.section_names, expected_names[item.chain_name])
                self.assertEqual(item.sections_consumed, 5)
                self.assertEqual(tuple(section.owner.key[3] for section in item.sweep.sections), expected_roles[item.chain_name])
                self.assertIs(item.sweep.sections[2].owner, item.sweep.sections[1].owner)
                self.assertEqual(len(item.sweep.endpoint_caps), 2)
                self.assertEqual(tuple(cap.side for cap in item.sweep.endpoint_caps), ("start", "end"))
                transition_indices = tuple(transition.section_index for transition in item.sweep.internal_transitions)
                self.assertEqual(len(transition_indices), len(set(transition_indices)))
                self.assertTrue(all(0 < index < 4 for index in transition_indices))
                self.assertEqual(
                    len({tuple(transition.center) for transition in item.sweep.internal_transitions}),
                    len(item.sweep.internal_transitions),
                )
                self.assertTrue(all(
                    not np.allclose(cap.center, transition.center, rtol=0.0, atol=1.0e-12)
                    for cap in item.sweep.endpoint_caps
                    for transition in item.sweep.internal_transitions
                ))
                topology.append((item.chain_name, item.section_names, item.sections_consumed, transition_indices))
            topologies.append(tuple(topology))
        self.assertEqual(len(set(topologies)), 1)

    def test_limb_bridge_inventory_retains_expected_twenty_two_fields_and_connectors(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        region = successor.compile_successor_region(guide, baseline)
        expected_bridge_recipes = {
            "root-bridge", "hip-transition", "paw", "extremity-bridge", "metatarsal",
            "paw-pad", "toe-box", "tail-segment", "tail-tip-extension", "tail-tip-cap",
            "tail-root-bridge", "tail-root-collar",
        }
        self.assertEqual(len(region.bridge_fields), 22)
        self.assertEqual({field.recipe for field in region.bridge_fields}, expected_bridge_recipes)
        self.assertEqual(len(region.replaced_baseline_recipes), 18)
        self.assertEqual(
            sum(field.recipe in region.replaced_baseline_recipes for field in baseline),
            30,
        )
        self.assertEqual(
            sum(field.recipe in successor._LIMB_CHAIN_BASELINE_RECIPES for field in baseline),
            22,
        )

        chains = {item.chain_name: item for item in region.limb_sweeps}
        inventory = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.limb_guides}
        for side in ("left", "right"):
            arm = chains[f"{side}-arm"]
            leg = chains[f"{side}-leg"]
            arm_root = next(field for field in region.bridge_fields if field.recipe == "root-bridge" and field.owner is inventory[(side, "upper_arm")].owner)
            leg_root = next(field for field in region.bridge_fields if field.recipe == "root-bridge" and field.owner is inventory[(side, "thigh")].owner)
            np.testing.assert_allclose(arm_root.shape["to"], arm.sweep.sections[0].center, rtol=0.0, atol=1.0e-12)
            np.testing.assert_allclose(leg_root.shape["to"], leg.sweep.sections[0].center, rtol=0.0, atol=1.0e-12)
            hip = next(field for field in region.bridge_fields if field.recipe == "hip-transition" and field.owner is inventory[(side, "thigh")].owner)
            self.assertTrue(np.all(np.isfinite(hip.shape["from"])))
            hand = next(field for field in region.bridge_fields if field.recipe == "extremity-bridge" and field.owner.key[1] == (side,) and field.owner.key[3] == "hand")
            self.assertLessEqual(
                successor._point_to_segment_distance(arm.sweep.sections[-1].center, hand.shape["from"], hand.shape["to"]),
                max(arm.sweep.sections[-1].transverse_radii) + max(float(hand.shape["r0"]), float(hand.shape["r1"])) + successor._FRAME_TOLERANCE,
            )
            foot = next(field for field in region.bridge_fields if field.recipe == "metatarsal" and field.owner.key[1] == (side,) and field.owner.key[3] == "foot")
            np.testing.assert_allclose(foot.shape["from"], leg.sweep.sections[-1].center, rtol=0.0, atol=1.0e-12)
            foot_guide = next(item for item in guide.paw_guides if item.owner.key[1] == (side,) and item.owner.key[3] == "foot")
            np.testing.assert_allclose(foot_guide.foot_chain.hock_anchor, leg.sweep.sections[-1].center, rtol=0.0, atol=1.0e-12)

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
        self.assertGreater(mesh.metrics["temporary_bridge"]["field_count"], 0)
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
            self.assertEqual(first.metrics["grid"]["samples_per_axis"], 56)
            self.assertTrue(first.metrics["watertight"])
            self.assertEqual(first.metrics["component_count"], 1)
            self.assertTrue(first.metrics["finite_vertices"] and first.metrics["finite_normals"])
            self.assertGreater(first.metrics["signed_volume"], 0.0)
            limb_metrics = first.metrics["successor_region"]
            self.assertEqual(limb_metrics["limb_sweeps_consumed"], 4)
            self.assertEqual(limb_metrics["limb_sweep_order"], ["left-arm", "left-leg", "right-arm", "right-leg"])
            self.assertEqual(limb_metrics["limb_sweep_station_counts"], [5, 5, 5, 5])
            self.assertEqual(limb_metrics["limb_sweep_endpoint_cap_counts"], [2, 2, 2, 2])
            self.assertTrue(all(len(owners) == 5 for owners in limb_metrics["limb_sweep_section_owner_keys"]))
            np.testing.assert_array_equal(first.vertices, second.vertices)
            np.testing.assert_array_equal(first.faces, second.faces)
            np.testing.assert_array_equal(first.normals, second.normals)
            self.assertEqual(first.metrics, second.metrics)
            self.assertEqual(first.metrics["successor_region"]["torso_section_names"][-1], "upper-ribcage-shoulder")
            winner_keys = {
                (item["namespace"], tuple(item["anchors"]), item["kind"], item["role"])
                for item in first.metrics["winner_addresses"]
            }
            self.assertIn(first.representation.head_neck_sweeps[3].owner.key, winner_keys)
            signatures.append((first.vertices.shape, first.metrics["signed_volume"], tuple(first.metrics["grid"]["bounds_max"])))
        self.assertEqual(len(signatures), 4)
        self.assertGreater(len(set(signatures)), 1)

    def test_generator_emits_explicit_successor_and_bridge_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
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
            first = root / "first"
            second = root / "second"
            first_manifest = successor.generate(source, first, padding=0.5)
            second_manifest = successor.generate(source, second, padding=0.5)
            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(first_manifest["format"], successor.FORMAT)
            self.assertEqual(first_manifest["consumer_id"], successor.CONSUMER_ID)
            self.assertEqual(first_manifest["generator"]["samples_per_axis"], 56)
            self.assertEqual([item["id"] for item in first_manifest["variants"]], list(surface_preview.VARIANT_IDS))
            self.assertEqual(
                sorted(path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()),
                sorted(path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()),
            )
            for first_path in first.rglob("*"):
                if first_path.is_file():
                    self.assertEqual(first_path.read_bytes(), (second / first_path.relative_to(first)).read_bytes())
            for variant in first_manifest["variants"]:
                sidecar = json.loads((first / variant["id"] / "successor.json").read_text())
                self.assertEqual(sidecar["consumer_id"], successor.CONSUMER_ID)
                self.assertEqual(sidecar["torso"]["sections_consumed"], 7)
                self.assertEqual(sidecar["shoulders"]["inputs_consumed"], 16)
                self.assertEqual(sidecar["head_neck"]["sweeps_consumed"], 5)
                self.assertEqual(
                    sidecar["head_neck"]["sweep_order"],
                    ["cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar"],
                )
                self.assertEqual(
                    sidecar["head_neck"]["section_counts"],
                    [5, 4, 2, 2, 3],
                )
                self.assertEqual(sidecar["limbs"]["sweeps_consumed"], 4)
                self.assertEqual(sidecar["limbs"]["sweep_order"], ["left-arm", "left-leg", "right-arm", "right-leg"])
                self.assertEqual(sidecar["limbs"]["station_counts"], [5, 5, 5, 5])
                self.assertEqual(
                    sidecar["limbs"]["station_names"],
                    [
                        ["upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "forearm-distal"],
                        ["thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"],
                        ["upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "forearm-distal"],
                        ["thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"],
                    ],
                )
                self.assertEqual(sidecar["limbs"]["endpoint_cap_counts"], [2, 2, 2, 2])
                self.assertEqual(len(sidecar["limbs"]["section_owner_keys"]), 4)
                self.assertTrue(all(len(owners) == 5 for owners in sidecar["limbs"]["section_owner_keys"]))
                self.assertTrue(sidecar["temporary_bridge"]["enabled"])

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
        with tempfile.TemporaryDirectory() as directory:
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

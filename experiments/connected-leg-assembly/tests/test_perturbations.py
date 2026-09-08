import copy
import json
import math
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))
import perturbations  # noqa: E402


SIDES = ("left", "right")
SECTIONS = (
    "mid_thigh", "knee_pre_support", "knee", "knee_post_support",
    "calf", "ankle_approach", "ankle",
)
FRACTIONS = (0.70, 0.90, 1.0, 0.12, 0.35, 0.72, 1.0)


def add(*values):
    return tuple(sum(value[index] for value in values) for index in range(3))


def sub(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def scale(value, factor):
    return tuple(factor * item for item in value)


def dot(left, right):
    return sum(left[index] * right[index] for index in range(3))


def cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def unit(value):
    length = math.sqrt(dot(value, value))
    return scale(value, 1.0 / length)


def lerp(left, right, fraction):
    return add(scale(left, 1.0 - fraction), scale(right, fraction))


def frame(tangent):
    tangent = unit(tangent)
    x = unit(sub((1.0, 0.0, 0.0), scale(tangent, tangent[0])))
    up = scale(tangent, -1.0)
    return {"X": x, "U": up, "F": unit(cross(x, up))}


def rotate(point, pivot, axis, degrees):
    angle = math.radians(degrees)
    value = sub(point, pivot)
    parallel = scale(axis, dot(axis, value))
    return add(scale(value, math.cos(angle)),
               scale(cross(axis, value), math.sin(angle)),
               scale(parallel, 1.0 - math.cos(angle)), pivot)


def synthetic_inputs():
    def row(side):
        sign = -1.0 if side == "left" else 1.0
        return {
            "J": [sign * 0.56, 2.1, 0.0],
            "T": [sign * 0.5, 2.0, 0.0],
            "K": [sign * 0.5, 1.0, 0.0],
            "A": [sign * 0.5, 0.0, 0.0],
            "radii": {
                "knee": [0.20, 0.16, 0.18],
                "calf": [0.18, 0.14, 0.22],
                "ankle": [0.10, 0.09, 0.13],
            },
            "mid_thigh_factor": 0.85,
            "support_fraction": 0.10,
            "J_role": "synthetic independent pose input",
            "TK_source_role": "synthetic source points",
            "distal_design_status": "synthetic test geometry",
        }
    return {side: row(side) for side in SIDES}


def synthetic_root():
    vertices = []
    for side in SIDES:
        x_offset = -0.5 if side == "left" else 0.5
        exit_centre = (x_offset, 1.55, 0.0)
        for corner in range(8):
            angle = 2.0 * math.pi * corner / 8.0
            lateral = 0.20 * math.cos(angle)
            forward_radius = 0.11 if math.sin(angle) >= 0.0 else 0.17
            forward = forward_radius * math.sin(angle)
            vertices.append((exit_centre[0] + lateral,
                             exit_centre[1],
                             exit_centre[2] + forward))
    return {
        "vertices": vertices,
        "quads": [],
        "loops": {
            "port.left_thigh": list(range(0, 8)),
            "port.right_thigh": list(range(8, 16)),
        },
        "base_stencils": [[[index, 1.0]] for index in range(16)],
    }


class SyntheticConstruction:
    def __init__(self):
        self.build_inputs = []
        self.build_count = 0
        self.evaluate_count = 0

    def _mesh(self, root, inputs):
        vertices = [tuple(point) for point in root["vertices"]]
        metadata = {"chains": {}}
        loops = copy.deepcopy(root["loops"])
        for side in SIDES:
            row = inputs[side]
            T, K, A = (tuple(row[name]) for name in ("T", "K", "A"))
            incoming = unit(sub(K, T))
            outgoing = unit(sub(A, K))
            knee_tangent = unit(add(incoming, outgoing))
            frames = [frame(value) for value in
                      (incoming, incoming, knee_tangent, outgoing,
                       outgoing, outgoing, outgoing)]
            exit_centre = add(T, scale(sub(K, T), 0.45))
            root_loop = root["loops"][f"port.{side}_thigh"]
            template = []
            lat_radius = 0.0
            ant_radius = 0.0
            post_radius = 0.0
            projected = []
            incoming_frame = frames[0]
            for index in root_loop:
                delta = sub(tuple(root["vertices"][index]), exit_centre)
                lateral = dot(delta, incoming_frame["X"])
                forward = dot(delta, incoming_frame["F"])
                projected.append((lateral, forward))
                lat_radius = max(lat_radius, abs(lateral))
                ant_radius = max(ant_radius, forward)
                post_radius = max(post_radius, -forward)
            for lateral, forward in projected:
                template.append((lateral / lat_radius,
                                 forward / (ant_radius if forward >= 0 else post_radius)))
            exit_radii = (lat_radius, ant_radius, post_radius)
            mid_radii = scale(exit_radii, row["mid_thigh_factor"])
            supplied = {name: tuple(row["radii"][name])
                        for name in ("knee", "calf", "ankle")}
            centres = [
                lerp(T, K, FRACTIONS[0]), lerp(T, K, FRACTIONS[1]), K,
                lerp(K, A, FRACTIONS[3]), lerp(K, A, FRACTIONS[4]),
                lerp(K, A, FRACTIONS[5]), A,
            ]
            radii = []
            for name, fraction in zip(SECTIONS, FRACTIONS):
                if name in ("mid_thigh", "knee_pre_support", "knee") and fraction <= 0.70:
                    value = lerp(exit_radii, mid_radii, (fraction - 0.45) / 0.25)
                elif name in ("mid_thigh", "knee_pre_support", "knee"):
                    value = lerp(mid_radii, supplied["knee"], (fraction - 0.70) / 0.30)
                elif fraction <= 0.35:
                    value = lerp(supplied["knee"], supplied["calf"], fraction / 0.35)
                elif name == "ankle":
                    value = supplied["ankle"]
                else:
                    value = lerp(supplied["calf"], supplied["ankle"], (fraction - 0.35) / 0.65)
                radii.append(value)
            sections = []
            for name, centre, section_radii, section_frame in zip(
                    SECTIONS, centres, radii, frames):
                ring = []
                for lateral, forward in template:
                    depth = section_radii[1] if forward >= 0.0 else section_radii[2]
                    point = add(centre,
                                scale(section_frame["X"], lateral * section_radii[0]),
                                scale(section_frame["F"], forward * depth))
                    ring.append(len(vertices))
                    vertices.append(point)
                sections.append({"name": name, "indices": ring, "centre": list(centre)})
            metadata["chains"][side] = {
                "pose_only_J": list(row["J"]),
                "pose_only_J_usage": (
                    "recorded context; unused by rest construction"
                ),
                "role_metadata": {
                    "J_role": row["J_role"],
                    "TK_source_role": row["TK_source_role"],
                    "distal_design_status": row["distal_design_status"],
                },
                "sections": sections,
            }
            loops[f"port.{side}_ankle"] = list(sections[-1]["indices"])
        return {
            "vertices": [list(point) for point in vertices],
            "quads": [],
            "loops": loops,
            "base_stencils": [[[index, 1.0]] for index in range(len(vertices))],
            "metadata": metadata,
        }

    def build(self, root, inputs):
        self.build_count += 1
        self.build_inputs.append(copy.deepcopy(inputs))
        return self._mesh(root, inputs)

    def evaluate(self, mesh):
        self.evaluate_count += 1
        return [copy.deepcopy(mesh), copy.deepcopy(mesh)]


class SyntheticBinding:
    def __init__(self):
        self.bind_inputs = []
        self.bind_count = 0
        self.pose_count = 0

    def bind(self, base, rest, root, prior_binding, inputs):
        self.bind_count += 1
        self.bind_inputs.append(copy.deepcopy(inputs))
        weights = []
        for index in range(len(base["vertices"])):
            row = [1.0, 0.0, 0.0, 0.0, 0.0]
            for side, thigh, shank in (("left", 1, 2), ("right", 3, 4)):
                for station, section in enumerate(base["metadata"]["chains"][side]["sections"]):
                    if index in section["indices"]:
                        shank_weight = (0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 1.0)[station]
                        row[thigh] = 1.0 - shank_weight
                        row[shank] = shank_weight
                        row[0] = 0.0
            weights.append(row)
        # The synthetic L2 is an identity-stencil copy of L0.
        return {"evaluated_weights": copy.deepcopy(weights),
                "base_weights": copy.deepcopy(weights),
                "leg_inputs": copy.deepcopy(inputs)}

    def pose(self, rest_mesh, binding, angles):
        self.pose_count += 1
        output = copy.deepcopy(rest_mesh)
        inputs = binding["leg_inputs"]
        J = tuple(inputs["left"]["J"])
        K = tuple(inputs["left"]["K"])
        y_axis = unit(sub(J, K))
        axis = unit(sub((1.0, 0.0, 0.0), scale(y_axis, y_axis[0])))
        hip = angles["left"]["hip"]
        vertices = []
        for point, row in zip(rest_mesh["vertices"], binding["evaluated_weights"]):
            source = tuple(point)
            transformed = rotate(source, J, axis, -hip)
            left_weight = row[1] + row[2]
            vertices.append(list(add(scale(source, 1.0 - left_weight),
                                     scale(transformed, left_weight))))
        output["vertices"] = vertices
        return output


def synthetic_protocol():
    return {
        "checks": {"binding_and_pose": {"source_effect_response_max_abs_error": 1.0e-8}},
        "baseline_poses": [
            {"id": "Lhip15_knee0",
             "left": {"hip": 15, "knee": 0, "ankle": 0},
             "right": {"hip": 0, "knee": 0, "ankle": 0}},
        ],
        "input_perturbations": [
            {"id": "left_A_y_minus_0.02",
             "change": {"path": "cases[*].leg_inputs.left.A[1]",
                         "operation": "add", "value": -0.02}},
            {"id": "left_calf_posterior_radius_times_1.10",
             "change": {"path": "cases[*].leg_inputs.left.radii.calf[2]",
                         "operation": "multiply", "value": 1.10}},
            {"id": "left_J_y_plus_0.01_at_hip15",
             "change": {"path": "cases[*].leg_inputs.left.J[1]",
                         "operation": "add", "value": 0.01}},
        ],
    }


def posterior_metric_fixture(stable_l0=True, expanding_l2=True, *,
                             non_extremal_only=False,
                             direction_invalid=False):
    source_frame = {
        "F": (0.0, -0.32599068331940423, 0.9453729816262723),
    }
    template = (
        (-1.0, -9.130123557772671e-18),
        (-0.7071067811865475, -0.7071067811865475),
        (0.0, 0.0),
        (0.0, 1.0),
        (0.7071067811865475, 0.7071067811865475),
        (1.0, 0.0),
        (0.7071067811865475, -0.7071067811865475),
        (0.0, -1.0),
    )
    direction = scale(source_frame["F"], -1.0)
    seam_expected = scale(direction, 5.192757773483211e-20)
    stable_expected = scale(direction, 0.004596194077712563)
    zero = (0.0, 0.0, 0.0)
    invalid = scale(direction, -0.001) if direction_invalid else zero
    expected_l0 = [seam_expected, stable_expected, invalid] + [zero] * 6
    actual_l0 = [
        zero, stable_expected if stable_l0 else zero, invalid, *([zero] * 6)
    ]
    baseline_l0 = [
        (-0.155, -0.45649999999999996, -0.009999999999999998)
        for _ in range(9)
    ]
    centre = (0.0, 0.0, 0.0)
    baseline_l2 = [scale(direction, extent) for extent in (2.0, 1.0, 0.0, 10.0)]
    stencils = [[(0, 1.0)], [(1, 1.0)], [(2, 1.0)], [(8, 1.0)]]
    if non_extremal_only:
        expected_l2 = [zero, scale(direction, 0.5), zero, zero]
    else:
        expected_l2 = [scale(direction, 0.5), scale(direction, 0.25),
                       invalid, zero]
    actual_l2 = copy.deepcopy(expected_l2) if expanding_l2 else [zero] * 4
    return perturbations._calf_posterior_measurement(
        baseline_l0, actual_l0, expected_l0, list(range(8)), template,
        baseline_l2, stencils, actual_l2, expected_l2, source_frame,
        centre, 1.0e-8,
    )


class PerturbationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.root = synthetic_root()
        self.inputs = synthetic_inputs()
        self.construction = SyntheticConstruction()
        self.binding = SyntheticBinding()
        self.baseline_L0 = self.construction.build(self.root, self.inputs)
        self.baseline_L2 = copy.deepcopy(self.baseline_L0)
        self.baseline_binding = self.binding.bind(
            self.baseline_L0, self.baseline_L2, self.root, {}, self.inputs)
        self.construction.build_inputs.clear()
        self.construction.build_count = 0
        self.construction.evaluate_count = 0
        self.binding.bind_inputs.clear()
        self.binding.bind_count = 0

    def run_evidence(self, inputs=None):
        return perturbations.run_case(
            self.root, self.baseline_L2, {}, inputs or self.inputs,
            self.baseline_L0, self.baseline_L2, self.baseline_binding,
            synthetic_protocol(), self.construction, self.binding)

    @staticmethod
    def failure_summary(result):
        return [(item["id"], item["status"], {
            name: details for name, details in item["checks"].items()
            if not details.get("pass", False)
        }, item["exceptions"]) for item in result["perturbations"]]

    def test_all_three_are_single_pass_and_json_compatible(self):
        result = self.run_evidence()
        self.assertEqual(result["status"], "pass", self.failure_summary(result))
        self.assertEqual(result["declared_perturbation_ids"], [
            "left_A_y_minus_0.02",
            "left_calf_posterior_radius_times_1.10",
            "left_J_y_plus_0.01_at_hip15",
        ])
        self.assertTrue(all(item["status"] == "pass" for item in result["perturbations"]))
        json.dumps(result, allow_nan=False)
        self.assertEqual(self.construction.build_count, 3)
        self.assertEqual(self.construction.evaluate_count, 3)
        self.assertEqual(self.binding.bind_count, 3)
        self.assertEqual(self.binding.pose_count, 2)
        for sent in self.construction.build_inputs + self.binding.bind_inputs:
            self.assertEqual(set(sent), set(SIDES))
            self.assertIn("mid_thigh_factor", sent["left"])
            self.assertIn("support_fraction", sent["right"])

    def test_asymmetric_ankle_mean_is_not_gated_to_A(self):
        result = self.run_evidence()
        self.assertEqual(result["status"], "pass", self.failure_summary(result))
        record = result["perturbations"][0]
        expected = record["expected"]["ankle_expected_world_loop_mean"]
        A = self.inputs["left"]["A"]
        self.assertGreater(abs(expected[2] - A[2]), 1.0e-6)
        self.assertIn("l2_ankle_mean_matches_analytic_l0_mean", record["checks"])
        self.assertTrue(record["checks"]["l2_ankle_mean_matches_analytic_l0_mean"]["pass"])

    def test_calf_uses_signed_piecewise_stencil_expectation(self):
        result = self.run_evidence()
        self.assertEqual(result["status"], "pass", self.failure_summary(result))
        record = result["perturbations"][1]
        coefficients = record["expected"]["piecewise_calf_posterior_coefficients"]
        self.assertAlmostEqual(coefficients["knee_post_support"], 0.12 / 0.35)
        self.assertEqual(coefficients["calf"], 1.0)
        self.assertAlmostEqual(coefficients["ankle_approach"], 0.28 / 0.65)
        self.assertEqual(coefficients["ankle"], 0.0)
        self.assertTrue(record["checks"]["analytic_full_stencil_L2_response"]["pass"])
        self.assertTrue(record["checks"]["ankle_boundary_and_loop_mean_unchanged"]["pass"])
        metric = record["checks"]["signed_calf_posterior_expansion"]
        self.assertTrue(metric["support_envelope"]["actual_expansion_in_minus_localF"])
        self.assertGreater(metric["support_envelope"]["extent_difference_m"], 1.0e-8)
        self.assertEqual(
            metric["exact_planar_section"]["definition"],
            "the eight exact L0 calf-ring samples only",
        )
        self.assertTrue(record["checks"]["root_and_other_leg_unchanged"]["pass"])

    def test_anthro_seam_is_indeterminate_but_stable_zero_response_fails(self):
        seam = posterior_metric_fixture(stable_l0=True, expanding_l2=True)
        samples = seam["source_samples"]
        self.assertEqual(samples[0]["domain"], "posterior-indeterminate")
        self.assertEqual(samples[0]["response_status"], "indeterminate-bounded")
        self.assertLess(samples[0]["expected_signed_minus_localF"],
                        samples[0]["projected_ulp_bound"])
        self.assertEqual(samples[1]["domain"], "posterior-stable")
        self.assertTrue(samples[1]["pass"])
        self.assertTrue(seam["pass"], seam)

        stable_zero = posterior_metric_fixture(stable_l0=False, expanding_l2=True)
        stable_sample = stable_zero["source_samples"][1]
        self.assertEqual(stable_sample["domain"], "posterior-stable")
        self.assertEqual(stable_sample["response_status"], "failed-nonpositive")
        self.assertFalse(stable_zero["pass"], stable_zero)

    def test_l2_support_envelope_without_expansion_fails(self):
        metric = posterior_metric_fixture(stable_l0=True, expanding_l2=False)
        self.assertGreater(metric["support_envelope"]["l2_vertex_count"], 0)
        self.assertFalse(metric["support_envelope"]["actual_expansion_in_minus_localF"])
        self.assertFalse(metric["pass"], metric)

    def test_non_extremal_posterior_motion_does_not_count_as_envelope_growth(self):
        metric = posterior_metric_fixture(
            stable_l0=True, expanding_l2=True, non_extremal_only=True,
        )
        envelope = metric["support_envelope"]
        self.assertGreater(envelope["samples"][1]["actual_signed_minus_localF"], 0.0)
        self.assertEqual(envelope["baseline_extremum"]["l2_vertex_id"], 0)
        self.assertEqual(envelope["actual_extremum"]["l2_vertex_id"], 0)
        self.assertEqual(envelope["extent_difference_m"], 0.0)
        self.assertFalse(envelope["actual_expansion_in_minus_localF"])
        self.assertFalse(metric["pass"], metric)

    def test_direction_invalid_rows_are_retained_in_pass_reduction(self):
        metric = posterior_metric_fixture(
            stable_l0=True, expanding_l2=True, direction_invalid=True,
        )
        source_row = metric["source_samples"][2]
        support_row = next(
            row for row in metric["support_envelope"]["samples"]
            if row["l2_vertex_id"] == 2
        )
        self.assertEqual(source_row["domain"], "opposite-frame-response")
        self.assertEqual(support_row["domain"], "opposite-frame-response")
        self.assertFalse(source_row["pass"])
        self.assertFalse(support_row["pass"])
        self.assertFalse(metric["pass"], metric)

    def test_legacy_outer_factor_shape_is_unavailable_without_adaptation(self):
        legacy = copy.deepcopy(self.inputs)
        legacy["mid_thigh_factor"] = 0.85
        legacy["support_fraction"] = 0.10
        for side in SIDES:
            del legacy[side]["mid_thigh_factor"]
            del legacy[side]["support_fraction"]
        result = self.run_evidence(legacy)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.construction.build_count, 0)
        self.assertIn("left and right sides", result["exceptions"][0]["message"])

    def test_J_allows_only_intended_pose_metadata_and_rejects_shape_changes(self):
        result = self.run_evidence()
        self.assertEqual(result["status"], "pass", self.failure_summary(result))
        record = result["perturbations"][2]
        for level in ("L0", "L2"):
            self.assertTrue(
                record["checks"][
                    f"rest_{level}_shape_exactly_unchanged_except_pose_only_J"
                ]["pass"]
            )
            self.assertTrue(
                record["checks"][
                    f"rest_{level}_pose_only_J_matches_intended_source"
                ]["pass"]
            )
            self.assertTrue(
                record["checks"][
                    f"rest_{level}_only_declared_pose_only_J_metadata_changed"
                ]["pass"]
            )
        expected_J = [self.inputs["left"]["J"][0],
                      self.inputs["left"]["J"][1] + 0.01,
                      self.inputs["left"]["J"][2]]
        self.assertEqual(
            record["checks"]["rest_L0_pose_only_J_matches_intended_source"][
                "actual_pose_only_J"
            ],
            expected_J,
        )

        def candidate_with_expected_J():
            candidate = copy.deepcopy(self.baseline_L0)
            candidate["metadata"]["chains"]["left"]["pose_only_J"] = expected_J
            return candidate

        moved_vertex = candidate_with_expected_J()
        moved_vertex["vertices"][16][0] += 0.01
        self.assertFalse(
            perturbations._compare_rest_construction(
                self.baseline_L0, moved_vertex, "left", expected_J, "vertex"
            )["all_other_fields_equal"]
        )

        changed_stencil = candidate_with_expected_J()
        changed_stencil["base_stencils"][16][0][1] = 0.5
        self.assertFalse(
            perturbations._compare_rest_construction(
                self.baseline_L0, changed_stencil, "left", expected_J, "stencil"
            )["all_other_fields_equal"]
        )

        changed_topology = candidate_with_expected_J()
        changed_topology["loops"]["port.left_ankle"] = [16, 17, 18, 19,
                                                           20, 21, 22, 23]
        self.assertFalse(
            perturbations._compare_rest_construction(
                self.baseline_L0, changed_topology, "left", expected_J, "topology"
            )["all_other_fields_equal"]
        )


if __name__ == "__main__":
    unittest.main()

import copy
import importlib.util
import json
import math
import os
import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("connected_leg_checks", ROOT / "checks.py")
CHECKS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKS
SPEC.loader.exec_module(CHECKS)
BINDING_SPEC = importlib.util.spec_from_file_location("connected_leg_binding_for_checks", ROOT / "binding.py")
BINDING = importlib.util.module_from_spec(BINDING_SPEC)
sys.modules[BINDING_SPEC.name] = BINDING
BINDING_SPEC.loader.exec_module(BINDING)


def identity():
    return [[1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]


def protocol(prior_face_count=0):
    return {"checks": {
        "minimum_edge_over_scale": 1e-8,
        "minimum_triangle_area_over_scale_squared": 1e-10,
        "weight_partition_tolerance": 1e-9,
        "independent_lbs_tolerance": 1e-9,
        "identity_position_tolerance": 1e-9,
        "lower_edge_strain_ratio": [0.5, 2.0],
        "lower_triangle_area_ratio": [0.4, 2.5],
        "lower_normal_dot_min": 0.0,
        "prior_face_count": prior_face_count,
        "boundary_loop_names": ["neck", "arm.left", "arm.right", "ankle.left", "ankle.right"],
    }}


def leg_inputs():
    return {
        "left": {"J": [-0.1, 0.0, 0.0], "T": [-0.12, -0.05, 0.0],
                 "K": [-0.08, -0.4, 0.03], "A": [-0.08, -0.7, -0.08]},
        "right": {"J": [0.1, 0.0, 0.0], "T": [0.12, -0.05, 0.0],
                  "K": [0.08, -0.4, 0.03], "A": [0.08, -0.7, -0.08]},
    }


def binding_for(vertices, weights=None, inputs=None):
    inputs = copy.deepcopy(inputs if inputs is not None else leg_inputs())
    source_rows, points = CHECKS._source_joint_rows(inputs)
    joints = {name: {"rest_matrix": source_rows[name]["rest"],
                     "inverse_bind_matrix": source_rows[name]["inverse_bind"]}
              for name in CHECKS._JOINTS}
    frames = {}
    for side in ("left", "right"):
        thigh_rest = source_rows[f"{side}_hip"]["rest"]
        knee_rest = source_rows[f"{side}_knee"]["rest"]
        frames[side] = {
            **copy.deepcopy(points[side]),
            "thigh": {"rest_global": thigh_rest},
            "knee": {"rest_global": knee_rest,
                     "rest_local": CHECKS._mm(CHECKS._inverse(thigh_rest), knee_rest)},
        }
    return {
        "joint_order": list(BINDING._JOINT_ORDER),
        "weight_columns": list(BINDING._WEIGHT_COLUMNS),
        "joints": joints,
        "parents": {"pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
                     "right_hip": "pelvis", "right_knee": "right_hip"},
        "rest_frames": frames,
        "leg_inputs": inputs,
        "evaluated_weights": copy.deepcopy(
            weights if weights is not None else
            [[1.0, 0.0, 0.0, 0.0, 0.0] for _ in vertices]),
    }


def arm_source_binding(vertices):
    """Small 9-column binding fixture with near-horizontal +/-X arm bones."""
    inputs = leg_inputs()
    binding = binding_for(vertices, inputs=inputs)
    binding["joint_order"] = list(CHECKS._ARM_JOINTS)
    binding["weight_columns"] = list(CHECKS._ARM_WEIGHT_COLUMNS)
    binding["parents"] = {
        "pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
        "right_hip": "pelvis", "right_knee": "right_hip",
        "left_shoulder": "pelvis", "left_elbow": "left_shoulder",
        "right_shoulder": "pelvis", "right_elbow": "right_shoulder",
    }
    arm_points = {
        "left": {"J": [-0.2, 1.0, 0.0], "E": [-1.0, 1.0, 0.0],
                  "W": [-1.6, 1.0, 0.0]},
        "right": {"J": [0.2, 1.0, 0.0], "E": [1.0, 1.0, 0.0],
                   "W": [1.6, 1.0, 0.0]},
    }
    for side in ("left", "right"):
        shoulder = CHECKS._arm_source_frame(arm_points[side]["J"],
                                             arm_points[side]["E"],
                                             f"{side} shoulder")
        elbow = CHECKS._arm_source_frame(arm_points[side]["E"],
                                          arm_points[side]["W"],
                                          f"{side} elbow")
        binding["rest_frames"][side].update({
            "arm_source_points": copy.deepcopy(arm_points[side]),
            "shoulder": {"rest_global": shoulder},
            "elbow": {"rest_global": elbow,
                       "rest_local": CHECKS._mm(CHECKS._inverse(shoulder), elbow)},
        })
        binding["joints"][f"{side}_shoulder"] = {
            "rest_matrix": shoulder, "inverse_bind_matrix": CHECKS._inverse(shoulder),
        }
        binding["joints"][f"{side}_elbow"] = {
            "rest_matrix": elbow, "inverse_bind_matrix": CHECKS._inverse(elbow),
        }
    binding["evaluated_weights"] = [
        [1.0] + [0.0] * (len(CHECKS._ARM_WEIGHT_COLUMNS) - 1)
        for _ in vertices
    ]
    return binding


def arm_graph_fixture():
    """Synthetic root graph with the accepted 8/8/10 D0/D1/D2 regions."""
    root_count = 152
    root_quads = []
    append_quads = []
    arms = {}
    cursor = root_count
    for side_index, side in enumerate(("left", "right")):
        offset = side_index * 26
        d0 = list(range(offset, offset + 8))
        d1 = list(range(offset + 8, offset + 16))
        d2 = list(range(offset + 16, offset + 26))
        root_quads.extend([
            [d0[0], d0[1], d0[2], d0[3]], [d0[4], d0[5], d0[6], d0[7]],
            [d1[0], d1[1], d1[2], d1[3]], [d1[4], d1[5], d1[6], d1[7]],
            [d1[0], d1[1], d1[4], d1[5]],
        ])
        for start in (0, 2, 4, 6):
            root_quads.append([d0[start], d0[start + 1], d1[start + 1], d1[start]])
            root_quads.append([d1[start], d1[start + 1], d2[start + 1], d2[start]])
        root_quads.append([d1[0], d1[1], d2[8], d2[9]])

        collar = list(range(cursor, cursor + 8))
        cursor += 8
        section_indices = []
        for _ in CHECKS._ARM_SECTION_NAMES:
            section = list(range(cursor, cursor + 8))
            cursor += 8
            section_indices.append(section)
        cap = cursor
        cursor += 1
        for left, right in zip([collar] + section_indices[:-1], section_indices):
            for slot in range(8):
                next_slot = (slot + 1) % 8
                append_quads.append([left[slot], left[next_slot],
                                     right[next_slot], right[slot]])
        for slot in range(8):
            next_slot = (slot + 1) % 8
            append_quads.append([d0[slot], d0[next_slot],
                                 collar[next_slot], collar[slot]])
        arms[side] = {
            "J_source": f"shoulders.{side}.arm_origin",
            "J": [float(side_index), 1.0, 0.0],
            "E": [float(side_index) + 1.0, 1.0, 0.0],
            "W": [float(side_index) + 2.0, 1.0, 0.0],
            "source_port": {"name": f"port.{side}_arm", "indices": d0},
            "collar": {"indices": collar},
            "sections": [{"name": name, "indices": values}
                         for name, values in zip(CHECKS._ARM_SECTION_NAMES, section_indices)],
            "cap": {"vertex": cap},
            "new_vertex_indices": collar + [index for section in section_indices for index in section] + [cap],
        }
    vertices = [[float(index), 0.0, 0.0] for index in range(cursor)]
    quads = root_quads + append_quads
    base = {"vertices": vertices, "quads": quads,
            "metadata": {"root": {"vertex_count": root_count,
                                    "face_count": len(root_quads)},
                         "arms": arms}}
    return base, arms


def combined_arm_head_tail_graph_fixture():
    """Final adjacency has a tail replacement inside the original root range."""
    base, arms = arm_graph_fixture()
    old_root_faces = base["metadata"]["root"]["face_count"]
    d0 = list(range(52, 58))
    d1 = list(range(60, 66))
    d2 = list(range(70, 76))
    support = list(range(len(base["vertices"]), len(base["vertices"]) + 6))
    tail = list(range(support[-1] + 1, support[-1] + 5))
    base["vertices"].extend([[float(index), 0.0, 1.0] for index in support + tail])
    head_root = []
    head_support = []
    for slot in range(6):
        next_slot = (slot + 1) % 6
        head_root.extend((
            [d0[slot], d0[next_slot], d1[next_slot], d1[slot]],
            [d1[slot], d1[next_slot], d2[next_slot], d2[slot]],
        ))
        head_support.append([d0[slot], d0[next_slot], support[next_slot], support[slot]])
    prior_quads = (
        base["quads"][:old_root_faces] + head_root
        + base["quads"][old_root_faces:] + head_support
    )
    base["metadata"]["root"]["face_count"] = old_root_faces + len(head_root)
    base["metadata"]["head"] = {
        "neck_port_indices": d0,
        "binding_handoff": {"consumed_neck_port_indices": d0},
    }
    final_quads = copy.deepcopy(prior_quads)
    final_quads[old_root_faces] = [d0[0], d0[1], tail[0], tail[1]]
    final_quads.extend([
        [tail[0], tail[1], tail[2], tail[3]],
        [tail[1], tail[2], tail[3], support[0]],
    ])
    head = {"source_port": d0, "support": support}
    return base, arms, head, prior_quads, final_quads


def pose_mesh(vertices, owners):
    return {"vertices": copy.deepcopy(vertices), "quads": [[0, 1, 2, 3]],
            "face_owners": owners, "loops": {}}


def clean_adjacent_fixture():
    vertices = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
    rest = pose_mesh(vertices, ["leg.left"])
    posed = pose_mesh(vertices, ["leg.left"])
    inputs = leg_inputs()
    return rest, posed, binding_for(vertices, inputs=inputs), {
        "left": {"hip": 0.0, "knee": 0.0},
        "right": {"hip": 0.0, "knee": 0.0},
    }, protocol(), inputs


def crossing_fixture():
    vertices = [
        [-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0],
        [0.0, -1.0, -1.0], [0.0, 1.0, -1.0], [0.0, 1.0, 1.0], [0.0, -1.0, 1.0],
    ]
    rest = {"vertices": vertices, "quads": [[0, 1, 2, 3], [4, 5, 6, 7]],
            "face_owners": ["leg.left", "leg.right"], "loops": {}}
    posed = copy.deepcopy(rest)
    inputs = leg_inputs()
    binding = binding_for(vertices, inputs=inputs)
    return rest, posed, binding, {
        "left": {"hip": 0.0, "knee": 0.0},
        "right": {"hip": 0.0, "knee": 0.0},
    }, protocol(), inputs


class CheckMeshTests(unittest.TestCase):
    def test_reports_missing_five_port_boundary_contract(self):
        vertices = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
        mesh = {"vertices": vertices, "quads": [[0, 1, 2, 3]],
                "loops": {"neck": [0, 1, 2, 3]},
                "base_stencils": [[[index, 1.0]] for index in range(4)]}
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertTrue(report["checks"]["one_connected_component"])
        self.assertFalse(report["checks"]["exact_five_boundary_loops"])
        self.assertFalse(report["checks"]["declared_neck_two_arms_two_ankles"])

    def test_nonpositive_triangle_area_is_a_defect(self):
        mesh = {"vertices": [[0.0, 0.0, 0.0]] * 4, "quads": [[0, 1, 2, 3]],
                "loops": {}, "base_stencils": [[[index, 1.0]] for index in range(4)]}
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["triangle_minimum_area"])
        self.assertEqual(report["outcome"], "fail")

    def test_stencil_partition_uses_declared_numeric_tolerance(self):
        rows = [[[0, 1.0000000005]]]
        self.assertEqual(CHECKS._stencil_rows(rows, 1, 1, "stencils", 1e-9),
                         [[(0, 1.0000000005)]])

    def test_terminal_foot_metadata_accepts_three_retained_boundaries(self):
        report = CHECKS.check_mesh(terminal_foot_mesh(), protocol())
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["foot_metadata_contract"])
        self.assertTrue(report["checks"]["foot_closed_boundary_contract"])
        self.assertNotIn("exact_five_boundary_loops", report["checks"])

    def test_terminal_foot_missing_metadata_does_not_admit_three_boundaries(self):
        mesh = terminal_foot_mesh()
        del mesh["metadata"]["feet"]
        mesh["metadata"]["base_vertex_count"] = len(mesh["vertices"])
        mesh["metadata"]["base_control_owners"] = ["domain.root"] * len(mesh["vertices"])
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["exact_five_boundary_loops"])
        self.assertFalse(report["checks"]["declared_neck_two_arms_two_ankles"])

    def test_terminal_foot_missing_side_is_rejected(self):
        mesh = terminal_foot_mesh()
        del mesh["metadata"]["feet"]["left"]
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["foot_metadata_contract"])

    def test_terminal_foot_overlapping_assignment_is_rejected(self):
        mesh = terminal_foot_mesh()
        mesh["metadata"]["feet"]["right"]["new_vertex_indices"] = [30, 31]
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["foot_metadata_contract"])

    def test_terminal_foot_out_of_range_assignment_is_rejected(self):
        mesh = terminal_foot_mesh()
        mesh["metadata"]["feet"]["right"]["new_vertex_indices"] = [36]
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["foot_metadata_contract"])

    def test_terminal_foot_loop_mismatch_is_rejected(self):
        mesh = terminal_foot_mesh()
        mesh["loops"]["port.right_ankle"] = mesh["loops"].pop("port.right_arm")
        report = CHECKS.check_mesh(mesh, protocol())
        self.assertFalse(report["pass"])
        self.assertTrue(report["checks"]["foot_metadata_contract"])
        self.assertFalse(report["checks"]["foot_closed_boundary_contract"])


class CheckPoseTests(unittest.TestCase):
    def test_terminal_foot_pose_uses_broadphase_wrapper_and_complete_pair_scope(self):
        rest, posed, binding, angles, limits, inputs = clean_adjacent_fixture()
        rest["metadata"] = {"feet": {}}
        posed["metadata"] = {"feet": {}}
        calls = []

        class Broadphase:
            METHOD = "synthetic-broadphase"
            FROZEN_CORE_PATH = CHECKS._FROZEN_CORE

            @staticmethod
            def collision_report(vertices, triangles, *, include_classifications, block_size=1024):
                calls.append((vertices, triangles, include_classifications, block_size))
                pair_count = len(triangles) * (len(triangles) - 1) // 2
                return {
                    "available": True,
                    "pair_count": pair_count,
                    "pair_partition_complete": True,
                    "final_classification_partition_complete": True,
                    "hit_pairs_truncated": False,
                    "candidate_pairs_truncated": False,
                    "nontrivial_evidence_truncated": False,
                    "hit_pairs": [], "errors": [], "blocks": [{"block": 0}],
                    "narrowphase": "frozen-oracle",
                }

        with mock.patch.object(CHECKS, "_BROADPHASE", Broadphase()), \
                mock.patch.object(CHECKS, "_load_intersection_core",
                                  side_effect=AssertionError("legacy route used")):
            report = CHECKS.check_pose(rest, posed, binding, angles, limits, inputs)

        self.assertTrue(report["pass"], report)
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0][2])
        collision = report["metrics"]["collision"]
        self.assertEqual(collision["method"], "synthetic-broadphase")
        self.assertEqual(collision["narrowphase"], "frozen-oracle")
        self.assertEqual(collision["intersection_core_path"], str(CHECKS._FROZEN_CORE))
        self.assertEqual(len(collision["intersection_core_sha256"]), 64)
        self.assertTrue(collision["scope"]["complete_pair_accounting"])
        self.assertEqual(collision["covered_pair_count"], collision["expected_pair_count"])

    def test_terminal_foot_pose_maps_wrapper_hits_to_owned_faces(self):
        rest, posed, binding, angles, limits, inputs = clean_adjacent_fixture()
        rest["metadata"] = {"feet": {}}
        posed["metadata"] = {"feet": {}}
        extra = [[3.0, 0.0, 0.0], [4.0, 0.0, 0.0],
                 [4.0, 1.0, 0.0], [3.0, 1.0, 0.0]]
        for mesh in (rest, posed):
            mesh["vertices"] = mesh["vertices"] + extra
            mesh["quads"] = [[0, 1, 2, 3], [4, 5, 6, 7]]
            mesh["face_owners"] = ["leg.left", "leg.right"]
        binding = binding_for(rest["vertices"], inputs=inputs)

        class Broadphase:
            FROZEN_CORE_PATH = CHECKS._FROZEN_CORE
            METHOD = "synthetic-broadphase"

            @staticmethod
            def collision_report(_vertices, _triangles, *, include_classifications, block_size=1024):
                return {
                    "available": True, "pair_count": 6,
                    "pair_partition_complete": True,
                    "final_classification_partition_complete": True,
                    "hit_pairs_truncated": False,
                    "candidate_pairs_truncated": False,
                    "nontrivial_evidence_truncated": False,
                    "hit_pairs": [[0, 2]], "errors": [], "blocks": [],
                    "narrowphase": "frozen-oracle",
                }

        with mock.patch.object(CHECKS, "_BROADPHASE", Broadphase()):
            report = CHECKS.check_pose(rest, posed, binding, angles, limits, inputs)

        collision = report["metrics"]["collision"]
        self.assertEqual(collision["hit_face_pairs"][0]["faces"], [0, 1])
        self.assertFalse(report["checks"]["lower_collision_inventory"])

    def test_terminal_foot_pose_without_wrapper_is_unavailable_not_legacy(self):
        rest, posed, binding, angles, limits, inputs = clean_adjacent_fixture()
        rest["metadata"] = {"feet": {}}
        posed["metadata"] = {"feet": {}}
        with mock.patch.object(CHECKS, "_BROADPHASE", None), \
                mock.patch.object(CHECKS, "_load_broadphase", return_value=None), \
                mock.patch.object(CHECKS, "_load_intersection_core",
                                  side_effect=AssertionError("legacy route used")):
            report = CHECKS.check_pose(rest, posed, binding, angles, limits, inputs)

        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["collision_coverage_complete"])
        self.assertIn("collision_unavailable",
                      {row["code"] for row in report["errors"]})

    def test_clean_adjacent_fixture_passes_and_has_complete_collision_coverage(self):
        values = clean_adjacent_fixture()
        report = CHECKS.check_pose(*values)
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["identity_at_zero_angles"])
        self.assertTrue(report["checks"]["collision_coverage_complete"])
        self.assertEqual(report["metrics"]["collision"]["global_face_pair_count"], 0)

    def test_synthetic_positive_crossing_fixture_is_caught(self):
        values = crossing_fixture()
        report = CHECKS.check_pose(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["lower_collision_inventory"])
        self.assertGreaterEqual(len(report["metrics"]["collision"]["lower_hit_pairs"]), 1)

    def test_static_pose_with_nonzero_angle_fails_independent_lbs(self):
        rest, posed, binding, angles, limits, inputs = clean_adjacent_fixture()
        binding = copy.deepcopy(binding)
        binding["evaluated_weights"] = [[0.0, 1.0, 0.0, 0.0, 0.0] for _ in rest["vertices"]]
        angles = {"left": 15.0, "right": 0.0}
        report = CHECKS.check_pose(rest, posed, binding, angles, limits, inputs)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["independent_hierarchical_lbs"])

    def test_wrong_binding_frames_and_self_consistent_pose_fail_source_check(self):
        rest, _posed, _binding, angles, limits, immutable_inputs = clean_adjacent_fixture()
        wrong_inputs = copy.deepcopy(immutable_inputs)
        wrong_inputs["left"]["J"][1] += 0.1
        weights = [[0.0, 1.0, 0.0, 0.0, 0.0] for _ in rest["vertices"]]
        wrong_binding = binding_for(rest["vertices"], weights, wrong_inputs)
        angles = {"left": {"hip": 15.0, "knee": 0.0},
                  "right": {"hip": 0.0, "knee": 0.0}}
        wrong_pose = BINDING.pose(rest, wrong_binding, angles)
        report = CHECKS.check_pose(rest, wrong_pose, wrong_binding, angles, limits,
                                   immutable_inputs)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["binding_leg_inputs_match_immutable_inputs"])
        self.assertFalse(report["checks"]["binding_rest_sources_match_J_K_A"])

    def test_nonvertical_knee_uses_positive_rotation_after_parent_hip(self):
        rest, _posed, _binding, _angles, limits, inputs = clean_adjacent_fixture()
        weights = [[0.0, 0.0, 1.0, 0.0, 0.0] for _ in rest["vertices"]]
        binding = binding_for(rest["vertices"], weights, inputs)
        angles = {"left": {"hip": 20.0, "knee": 30.0},
                  "right": {"hip": 0.0, "knee": 0.0}}
        posed = BINDING.pose(rest, binding, angles)
        report = CHECKS.check_pose(rest, posed, binding, angles, limits, inputs)
        self.assertTrue(report["checks"]["independent_hierarchical_lbs"], report)

    def test_multiblock_pair_coverage_counts_cross_products_once(self):
        vertices = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                    [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
        quads = [(0, 1, 2, 3)] * 2050  # 4100 triangles: more than two default blocks.
        def stub(_vertices, triangles):
            pair_count = len(triangles) * (len(triangles) - 1) // 2
            return {"pair_count": pair_count,
                    "pair_policy_evidence": {"processed_pair_count": pair_count},
                    "pair_policy_complete": True, "candidate_pairs_truncated": False,
                    "hit_pairs_truncated": False, "hit_pairs": []}
        with mock.patch.object(CHECKS, "_load_intersection_core", return_value=stub):
            report = CHECKS._collision_report(
                vertices, quads, ["domain.left_leg"] * len(quads),
                set(range(len(quads))), set(),
            )
        self.assertTrue(report["coverage_complete"], report)
        self.assertEqual(report["covered_pair_count"], report["expected_pair_count"])

    def test_candidate_detail_truncation_does_not_hide_complete_hit_inventory(self):
        vertices = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                    [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
        def stub(_vertices, triangles):
            pair_count = len(triangles) * (len(triangles) - 1) // 2
            return {"pair_count": pair_count,
                    "pair_policy_evidence": {"processed_pair_count": pair_count},
                    "pair_policy_complete": True, "candidate_pairs_truncated": True,
                    "hit_pairs_truncated": False, "hit_pairs": []}
        with mock.patch.object(CHECKS, "_load_intersection_core", return_value=stub):
            report = CHECKS._collision_report(
                vertices, [(0, 1, 2, 3)], ["domain.left_leg"], {0}, set(),
            )
        self.assertTrue(report["coverage_complete"], report)
        self.assertTrue(report["available"], report)
        self.assertEqual(report["candidate_detail_truncated_calls"], [[0, 0]])

    def test_processed_pair_mismatch_is_unavailable_even_if_helper_claims_complete(self):
        vertices = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                    [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
        def stub(_vertices, triangles):
            pair_count = len(triangles) * (len(triangles) - 1) // 2
            return {"pair_count": pair_count,
                    "pair_policy_evidence": {"processed_pair_count": pair_count - 1},
                    "pair_policy_complete": True, "candidate_pairs_truncated": False,
                    "hit_pairs_truncated": False, "hit_pairs": []}
        with mock.patch.object(CHECKS, "_load_intersection_core", return_value=stub):
            report = CHECKS._collision_report(
                vertices, [(0, 1, 2, 3)], ["domain.left_leg"], {0}, set(),
            )
        self.assertFalse(report["coverage_complete"], report)
        self.assertFalse(report["available"], report)
        self.assertEqual(report["errors"][0]["code"], "incomplete_pair_policy")

    def test_captured_actual_pose_has_complete_lower_surface_collision_coverage(self):
        capture_value = os.environ.get("CONNECTED_LEG_CAPTURE_RUN")
        if not capture_value:
            self.skipTest("set CONNECTED_LEG_CAPTURE_RUN to exercise a captured full pose")
        capture = Path(capture_value)
        run_report = json.loads((capture / "run-report.json").read_text(encoding="utf-8"))
        inputs = json.loads((capture / "inputs.json").read_text(encoding="utf-8"))
        protocol_value = json.loads((capture / "protocol.json").read_text(encoding="utf-8"))
        case = run_report["cases"][0]
        case_inputs = next(row["leg_inputs"] for row in inputs["cases"] if row["id"] == case["id"])
        binding = json.loads((capture / "cases" / f"case-00-{case['id']}" / "binding.json").read_text(encoding="utf-8"))
        pose = case["poses"][0]
        report = CHECKS.check_pose(case["rest"], pose["mesh"], binding, pose["angles"],
                                   protocol_value, case_inputs)
        collision = report["metrics"]["collision"]
        triangle_count = len(case["rest"]["quads"]) * 2
        self.assertEqual(triangle_count, 7936)
        self.assertEqual(collision["covered_pair_count"], triangle_count * (triangle_count - 1) // 2)
        self.assertTrue(collision["coverage_complete"], collision)
        self.assertTrue(collision["available"], collision)
        self.assertTrue(report["checks"]["lower_collision_inventory"], report)
        self.assertNotIn("collision_unavailable", {row["code"] for row in report["errors"]})

    def test_nested_constructor_root_face_count_scales_to_l2(self):
        count = 2200
        parsed = {"value": {"metadata": {"level": 2, "root": {"face_count": 136}}},
                  "quads": [(0, 1, 2, 3)] * count,
                  "face_owners": ["domain.torso"] * 2176 + ["domain.left_leg"] * 24}
        lower, upper, start = CHECKS._lower_faces(parsed, {})
        self.assertEqual(start, 2176)
        self.assertEqual(lower, set(range(2176, count)))
        self.assertEqual(upper, set(range(2176)))

    def test_actual_protocol_and_binding_metadata_names_drive_pose_check(self):
        actual_protocol = json.loads((ROOT / "protocol.json").read_text(encoding="utf-8"))
        rest, posed, binding, angles, _limits, inputs = clean_adjacent_fixture()
        rest["metadata"] = {"level": 2, "root": {"face_count": 0}}
        posed["metadata"] = copy.deepcopy(rest["metadata"])
        self.assertEqual(tuple(binding["joint_order"]), tuple(BINDING._JOINT_ORDER))
        self.assertEqual(tuple(binding["weight_columns"]), tuple(BINDING._WEIGHT_COLUMNS))
        def stub(_vertices, triangles):
            pair_count = len(triangles) * (len(triangles) - 1) // 2
            return {"pair_count": pair_count,
                    "pair_policy_evidence": {"processed_pair_count": pair_count},
                    "pair_policy_complete": True, "candidate_pairs_truncated": False,
                    "hit_pairs_truncated": False, "hit_pairs": []}
        with mock.patch.object(CHECKS, "_load_intersection_core", return_value=stub):
            report = CHECKS.check_pose(rest, posed, binding, angles, actual_protocol, inputs)
        self.assertTrue(report["pass"], report)
        self.assertFalse(report["diagnostics"]["lower_normal_dot"]["gated"])
        self.assertEqual(CHECKS._limit(actual_protocol, ("weight_sum_max_abs_error",)), 1e-9)


class ArmCheckTests(unittest.TestCase):
    def test_arm_source_frame_handles_bones_near_both_x_axes(self):
        cases = {
            "left": ([-0.2, 1.0, 0.0], [-1.0, 1.0, 0.0]),
            "right": ([0.2, 1.0, 0.0], [1.0, 1.0, 0.0]),
        }
        for side, (origin, distal) in cases.items():
            frame = CHECKS._arm_source_frame(origin, distal, f"{side} arm")
            self.assertAlmostEqual(frame[2][2], 1.0)
            for column in range(3):
                self.assertAlmostEqual(
                    math.sqrt(sum(frame[row][column] ** 2 for row in range(3))), 1.0
                )

    def test_arm_endpoint_oracle_checks_settled_directions_for_both_sides(self):
        binding = arm_source_binding([[0.0, 0.0, 0.0]])
        zero = {side: {"shoulder_raise": 0.0, "shoulder_forward": 0.0,
                       "elbow": 0.0} for side in ("left", "right")}
        for side in ("left", "right"):
            for angle_name, point_name, component in (
                ("shoulder_raise", "E", 1),
                ("shoulder_forward", "E", 2),
                ("elbow", "W", 2),
            ):
                angles = copy.deepcopy(zero)
                angles[side][angle_name] = 10.0
                result = CHECKS._arm_endpoint_oracle(binding, angles)[side]
                self.assertGreater(result["posed"][point_name][component],
                                   result["rest"][point_name][component])

        report = CHECKS._report("synthetic-arm-endpoint-check")
        _order, posed_joints, _skins = CHECKS._expected_joint_poses(
            leg_inputs(), zero, binding
        )
        CHECKS._check_arm_endpoint_oracle(
            report, binding, zero, posed_joints, 1.0e-9
        )
        self.assertFalse(report["errors"], report)
        self.assertTrue(report["checks"]["arm_endpoint_parent_oracle"])

    def test_arm_expected_pose_uses_negative_elbow_rotation(self):
        binding = arm_source_binding([[0.0, 0.0, 0.0]])
        angles = {side: {"hip": 0.0, "knee": 0.0,
                         "shoulder_raise": 0.0, "shoulder_forward": 0.0,
                         "elbow": 20.0} for side in ("left", "right")}
        _order, posed, _skins = CHECKS._expected_joint_poses(
            leg_inputs(), angles, binding
        )
        oracle = CHECKS._arm_endpoint_oracle(binding, angles)
        for side in ("left", "right"):
            self.assertAlmostEqual(posed[f"{side}_elbow"][1][3],
                                   oracle[side]["posed"]["E"][1])
            self.assertGreater(oracle[side]["posed"]["W"][2],
                               oracle[side]["rest"]["W"][2])

    def test_arm_source_check_rejects_same_origin_wrong_joint_rotation(self):
        binding = arm_source_binding([[0.0, 0.0, 0.0]])
        wrong = copy.deepcopy(binding)
        wrong["joints"]["left_shoulder"]["rest_matrix"] = CHECKS._mm(
            wrong["joints"]["left_shoulder"]["rest_matrix"],
            [[-1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
             [0.0, 0.0, -1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
        )
        contract = {"source_points": {
            side: copy.deepcopy(binding["rest_frames"][side]["arm_source_points"])
            for side in ("left", "right")
        }}
        report = CHECKS._report("synthetic-arm-source-check")
        CHECKS._check_arm_source_frames(report, wrong, contract, 1e-9)
        self.assertFalse(report["checks"]["arm_source_J_E_W_frames"])
        self.assertIn("arm_source_frames",
                      {row["code"] for row in report["errors"]})

    def test_arm_graph_uses_exact_8_8_10_regions_and_harmonic_field(self):
        base, arms = arm_graph_fixture()
        fields, _blends, diagnostics = CHECKS._arm_graph_fields(
            base, base["quads"], arms
        )
        for side in ("left", "right"):
            details = diagnostics["per_side"][side]
            self.assertEqual((len(details["D0"]), len(details["D1"]),
                              len(details["D2"])), (8, 8, 10))
            self.assertTrue(all(math.isfinite(value)
                                for value in fields[side].values()),
                            (fields, diagnostics))

    def test_combined_head_arms_tail_use_prior_root_graph_and_final_adjacency(self):
        base, arms, head, prior_quads, final_quads = combined_arm_head_tail_graph_fixture()
        with self.assertRaisesRegex(ValueError, "root face references a non-root vertex"):
            CHECKS._arm_graph_fields(base, final_quads, arms)
        with self.assertRaisesRegex(ValueError, "root faces must reference only root vertices"):
            CHECKS._head_graph_field(base, final_quads, head)

        fields, _blends, diagnostics = CHECKS._arm_graph_fields(
            base, final_quads, arms, root_quads=prior_quads
        )
        head_values, _head_diagnostics = CHECKS._head_graph_field(
            base, final_quads, head, root_quads=prior_quads
        )
        self.assertEqual(set(fields), {"left", "right"})
        self.assertTrue(all(math.isfinite(value)
                            for values in fields.values()
                            for value in values.values()))
        self.assertEqual(set(head_values), set(head["source_port"] + list(range(60, 66))))
        self.assertEqual(set(diagnostics["per_side"]["left"]["D0"]),
                         set(arms["left"]["source_port"]["indices"]))

    def test_arm_binding_dispatch_finalizes_successful_specialized_report(self):
        vertices = [[float(index), 0.0, 0.0] for index in range(152)]
        mesh = {"vertices": vertices, "quads": [[0, 1, 2, 3]],
                "metadata": {"arms": {}}}

        def specialized(report, *_args):
            report["checks"]["specialized_complete"] = True
            return report

        with mock.patch.object(CHECKS, "_check_arm_binding",
                               side_effect=specialized):
            report = CHECKS.check_binding(
                mesh, mesh, {}, {"vertices": vertices,
                                 "quads": [[0, 1, 2, 3]]}, {}, {}, {}
            )
        self.assertTrue(report["pass"], report)

    def test_arm_metadata_contract_accepts_named_source_allocations(self):
        base, _arms = arm_graph_fixture()
        contract = CHECKS._arm_metadata_contract(base, len(base["vertices"]))
        self.assertTrue(contract["present"])
        self.assertEqual({side: len(indices)
                          for side, indices in contract["indices"].items()},
                         {"left": 89, "right": 89})

    def test_arm_pose_selects_complete_broadphase_route(self):
        rest, posed, binding, angles, limits, inputs = clean_adjacent_fixture()
        rest["metadata"] = {"arms": {"left": {}, "right": {}}}
        posed["metadata"] = copy.deepcopy(rest["metadata"])
        calls = []

        def broadphase(*_args, **_kwargs):
            calls.append(True)
            return {"available": True, "coverage_complete": True,
                    "lower_hit_pairs": []}

        with mock.patch.object(CHECKS, "_foot_collision_report",
                               side_effect=broadphase), \
                mock.patch.object(CHECKS, "_collision_report",
                                  side_effect=AssertionError("legacy route used")):
            report = CHECKS.check_pose(rest, posed, binding, angles, limits, inputs)

        self.assertEqual(len(calls), 1)
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["collision_coverage_complete"])


def binding_fixture():
    root_vertices = [[float(index), 0.0, 0.0] for index in range(152)]
    appended = [[float(index), -1.0, 0.0] for index in range(152, 264)]
    vertices = root_vertices + appended
    prior_root = {"vertices": copy.deepcopy(root_vertices), "quads": [[0, 1, 2, 3]]}
    inputs = leg_inputs()
    chains = {}
    cursor = 152
    for side in ("left", "right"):
        sections = []
        for order, name in enumerate(CHECKS._STATION_NAMES):
            ring = list(range(cursor, cursor + 8))
            cursor += 8
            sections.append({"name": name, "order": order, "indices": ring})
        chains[side] = {"sections": sections}
    base = {"vertices": copy.deepcopy(vertices), "quads": [[0, 1, 2, 3]],
            "metadata": {"chains": chains}}
    prior_rows = [[0.2, 0.3, 0.5] for _ in root_vertices]
    base_rows = [[0.2, 0.3, 0.0, 0.5, 0.0] for _ in root_vertices]
    for side, thigh, shank in (("left", 1, 2), ("right", 3, 4)):
        for station_index, section in enumerate(chains[side]["sections"]):
            shank_value = CHECKS._STATION_SHANK_WEIGHTS[station_index]
            for _index in section["indices"]:
                row = [0.0] * 5
                row[thigh], row[shank] = 1.0 - shank_value, shank_value
                base_rows.append(row)
    rest = {"vertices": copy.deepcopy(vertices), "quads": [[0, 1, 2, 3]],
            "base_stencils": [[[index, 1.0]] for index in range(264)]}
    binding = binding_for(vertices, base_rows, inputs)
    binding.update({"base_weights": base_rows,
                    "source_station_knee": list(CHECKS._STATION_SHANK_WEIGHTS),
                    "prior_column_map": [0, 1, 3]})
    prior_binding = {"base_weights": prior_rows}
    return base, rest, binding, prior_root, prior_binding, inputs, protocol()


def tail_metadata(new_indices, replacement_faces=(0, 1, 2)):
    host = [0, 1, 2, 3]
    phase = [[1, 1], [-1, 1], [-1, -1], [1, -1]]
    rings = [list(new_indices[:4]), list(new_indices[4:8])]
    corner_by_index = {
        index: corner
        for ring in rings
        for corner, index in enumerate(ring)
    }
    supports = {}
    for index in new_indices:
        corner = corner_by_index[index]
        supports[str(index)] = {
            "target_joint": "pelvis", "host_vertex_indices": host[:],
            "host_corner": corner, "source_phase": phase[corner],
            "convex_weights": [0.55 if slot == corner else 0.15 for slot in range(4)],
        }
    return {
        "owner": "domain.tail", "enabled": True,
        "source_host_identity": {"owner": "domain.pelvis", "face_index": 0,
                                  "vertex_indices": host[:]},
        "host": {"source_phase": copy.deepcopy(phase)},
        "source_phase": copy.deepcopy(phase), "ring_indices": rings,
        "station_fractions": [0.0, 1.0],
        "new_vertex_indices": list(new_indices),
        "face_replacement": {
            "original_face_index": 0, "original_quad": host[:],
            "replacement_face_indices": list(replacement_faces),
            "one_to_many": [[0, *replacement_faces]],
            "original_host_retained": False,
        },
        "transition_weights": {
            "collar_blend_strength": 0.5, "supports": supports,
        },
    }


def tail_binding_fixture():
    values = list(binding_fixture())
    base, rest, binding, prior_root, prior_binding, inputs, limits = values
    tail_indices = list(range(264, 272))
    base["vertices"].extend([[float(index), -2.0, 0.0] for index in tail_indices])
    base["quads"] = [
        [0, 1, 264, 265], [1, 2, 266, 265], [264, 265, 269, 268],
        [265, 266, 270, 269], [266, 267, 271, 270],
    ]
    base["metadata"].update({
        "base_vertex_count": 272,
        "base_control_owners": ["domain.root"] * 264 + ["domain.tail"] * 8,
        "root": {"vertex_count": 152, "face_count": 1},
        "index_mapping": {"root_face_mappings_excluding_tail_host": []},
        "tail": tail_metadata(tail_indices),
    })
    rest["vertices"].extend([[float(index), -2.0, 0.0] for index in tail_indices])
    rest["base_stencils"].extend([[[index, 1.0]] for index in tail_indices])
    base_rows = copy.deepcopy(binding["base_weights"])
    base_rows.extend([[0.6, 0.15, 0.0, 0.25, 0.0] for _ in range(4)])
    base_rows.extend([[1.0, 0.0, 0.0, 0.0, 0.0] for _ in range(4)])
    binding["base_weights"] = base_rows
    binding["evaluated_weights"] = copy.deepcopy(base_rows)
    binding["tail_vertex_indices"] = tail_indices[:]
    binding["tail_weighting"] = {
        "collar_blend_strength": 0.5, "distal_joint": "pelvis",
        "no_tail_joint": True,
        "vertices": {
            str(index): {
                "ring_fraction": 0.0 if index < 268 else 1.0,
                "pelvis_fraction": 0.5 if index < 268 else 1.0,
                "host_support_fraction": 0.5 if index < 268 else 0.0,
                "host_vertex_indices": [0, 1, 2, 3],
                "convex_weights": [0.55 if slot == index % 4 else 0.15 for slot in range(4)],
            }
            for index in tail_indices
        },
    }
    binding["metadata"] = {
        "tail_weighting_contract": {
            "host_face": 0, "host_vertex_indices": [0, 1, 2, 3],
            "kept_root_face_correspondence": [],
            "replacement_face_indices": [0, 1, 2],
            "collar_blend_strength": 0.5,
            "distal_target_joint": "pelvis", "tail_joint": "not_present",
        }
    }
    return base, rest, binding, prior_root, prior_binding, inputs, limits


def terminal_foot_mesh():
    """A small two-hole surface whose metadata exercises the foot contract."""
    width = height = 5
    vertices = [[float(x), float(y), 0.0]
                for y in range(height + 1) for x in range(width + 1)]
    omitted = {(1, 1), (3, 3)}
    quads = []
    for y in range(height):
        for x in range(width):
            if (x, y) not in omitted:
                lower = y * (width + 1) + x
                quads.append([lower, lower + 1, lower + width + 2, lower + width + 1])
    cycles = CHECKS._boundary_cycles(CHECKS._edge_incidence(quads))
    loops = {
        "port.neck": cycles[0],
        "port.left_arm": cycles[1],
        "port.right_arm": cycles[2],
    }
    owner_count = 28
    metadata = {
        "level": 0,
        "base_vertex_count": owner_count,
        "base_control_owners": ["domain.root"] * owner_count,
        "root": {"vertex_count": 4},
        "chains": {
            "left": {"new_vertex_indices": list(range(4, 16))},
            "right": {"new_vertex_indices": list(range(16, 28))},
        },
        "feet": {
            "left": {"new_vertex_indices": [28, 29, 30]},
            "right": {"new_vertex_indices": [31, 32, 33, 34, 35]},
        },
    }
    return {
        "vertices": vertices,
        "quads": quads,
        "loops": loops,
        "base_stencils": [[[index, 1.0]] for index in range(len(vertices))],
        "metadata": metadata,
    }


def terminal_foot_binding_fixture():
    values = list(binding_fixture())
    base, rest, binding, prior_root, prior_binding, inputs, limits = values
    base["vertices"].extend([[264.0, -1.0, 0.0], [265.0, -1.0, 0.0]])
    base_metadata = base["metadata"]
    base_metadata["base_vertex_count"] = 266
    base_metadata["base_control_owners"] = ["domain.root"] * 266
    base_metadata["root"] = {"vertex_count": 152}
    for side in ("left", "right"):
        base_metadata["chains"][side]["new_vertex_indices"] = [
            index for section in base_metadata["chains"][side]["sections"]
            for index in section["indices"]
        ]
    base_metadata["feet"] = {
        "left": {"new_vertex_indices": [264]},
        "right": {"new_vertex_indices": [265]},
    }
    rest["vertices"].extend([[264.0, -1.0, 0.0], [265.0, -1.0, 0.0]])
    rest["base_stencils"].extend([[[264, 1.0]], [[265, 1.0]]])
    binding["base_weights"].extend([
        [0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 1.0],
    ])
    binding["evaluated_weights"] = copy.deepcopy(binding["base_weights"])
    binding["foot_vertex_indices"] = {"left": [264], "right": [265]}
    binding["metadata"] = {
        "foot_vertex_indices": {"left": [264], "right": [265]},
    }
    return base, rest, binding, prior_root, prior_binding, inputs, limits


class CheckBindingTests(unittest.TestCase):
    def test_source_stations_prior_mapping_and_full_transfer_pass(self):
        report = CHECKS.check_binding(*binding_fixture())
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["declared_source_station_knee"])
        self.assertTrue(report["checks"]["original_root_152x3_mapped_to_five_columns"])
        self.assertTrue(report["checks"]["actual_l2_full_stencil_transfer"])

    def test_in_range_prior_weight_change_is_caught_by_mapping(self):
        values = list(binding_fixture())
        values[2] = copy.deepcopy(values[2])
        values[2]["base_weights"][0] = [0.21, 0.29, 0.0, 0.5, 0.0]
        values[2]["evaluated_weights"][0] = copy.deepcopy(values[2]["base_weights"][0])
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["original_root_152x3_mapped_to_five_columns"])

    def test_full_stencil_transfer_is_not_replaced_by_partition_check(self):
        values = list(binding_fixture())
        values[2] = copy.deepcopy(values[2])
        values[2]["evaluated_weights"][10] = [0.25, 0.25, 0.0, 0.5, 0.0]
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["actual_l2_full_stencil_transfer"])

    def test_consistently_mutated_station_base_and_l2_weights_still_fail(self):
        values = list(binding_fixture())
        values[2] = copy.deepcopy(values[2])
        values[2]["base_weights"][152] = [0.0, 0.75, 0.25, 0.0, 0.0]
        values[2]["evaluated_weights"][152] = [0.0, 0.75, 0.25, 0.0, 0.0]
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["constructor_station_base_weights"])
        self.assertFalse(report["checks"]["actual_l2_full_stencil_transfer"])

    def test_terminal_foot_metadata_and_shank_weights_pass(self):
        report = CHECKS.check_binding(*terminal_foot_binding_fixture())
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["terminal_foot_metadata_and_shank_weights"])
        self.assertTrue(report["checks"]["terminal_foot_full_l2_stencil_transfer"])

    def test_terminal_foot_full_l2_stencil_transfer_rejects_mutated_surface_weight(self):
        values = list(terminal_foot_binding_fixture())
        values[2] = copy.deepcopy(values[2])
        values[2]["evaluated_weights"][264] = [0.0, 0.0, 0.0, 0.0, 0.0]
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["terminal_foot_full_l2_stencil_transfer"])

    def test_tail_binding_checks_explicit_control_corner_supports_and_stencils(self):
        report = CHECKS.check_binding(*tail_binding_fixture())
        self.assertTrue(report["pass"], report)
        for name in (
            "tail_host_face_identity", "tail_kept_root_faces_exact",
            "tail_host_face_replaced", "tail_binding_control_explicit",
            "tail_corner_supports", "tail_l0_weight_formula",
            "tail_l2_full_stencil_transfer",
        ):
            self.assertTrue(report["checks"][name], (name, report))

    def test_tail_checker_uses_declared_ring_ordinal_for_non_multiple_prefix(self):
        tail_indices = list(range(265, 273))
        mesh = {
            "vertices": [[0.0, 0.0, 0.0] for _ in range(273)],
            "quads": [[0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3]],
            "metadata": {
                "root": {"vertex_count": 152, "face_count": 1},
                "base_vertex_count": 273,
                "index_mapping": {"root_face_mappings_excluding_tail_host": []},
                "tail": tail_metadata(tail_indices),
            },
        }
        contract = CHECKS._tail_metadata_contract(mesh, len(mesh["vertices"]))
        self.assertEqual(
            [contract["supports"][index]["host_corner"] for index in tail_indices],
            [0, 1, 2, 3, 0, 1, 2, 3],
        )

    def test_tail_checker_rejects_pelvis_only_constant_against_nonpelvis_host_support(self):
        values = list(tail_binding_fixture())
        original = values[2]["base_weights"][264]
        self.assertGreater(original[1], 0.0)
        self.assertGreater(original[3], 0.0)
        self.assertTrue(CHECKS.check_binding(*values)["checks"]["tail_l0_weight_formula"])

        values[2] = copy.deepcopy(values[2])
        values[2]["base_weights"][264] = [1.0, 0.0, 0.0, 0.0, 0.0]
        values[2]["evaluated_weights"][264] = [1.0, 0.0, 0.0, 0.0, 0.0]
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["tail_l0_weight_formula"])

    def test_tail_binding_rejects_uniform_centroid_support(self):
        values = list(tail_binding_fixture())
        values[0] = copy.deepcopy(values[0])
        values[0]["metadata"]["tail"]["transition_weights"]["supports"]["264"]["convex_weights"] = [0.25] * 4
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertTrue(report["errors"])

    def test_tail_binding_rejects_changed_kept_root_face(self):
        values = list(tail_binding_fixture())
        values[0] = copy.deepcopy(values[0])
        values[0]["metadata"]["index_mapping"]["root_face_mappings_excluding_tail_host"] = [[0, 0]]
        report = CHECKS.check_binding(*values)
        self.assertFalse(report["pass"])
        self.assertTrue(report["errors"])


class HeadCheckTests(unittest.TestCase):
    def head_metadata(self):
        port = list(range(6))
        support = list(range(152, 158))
        return {
            "metadata": {
                "head": {
                    "neck_source": "stations.neck_upper",
                    "neck_port_indices": port,
                    "stations": [{"name": "neck_support", "indices": support}],
                    "new_vertex_indices": support,
                    "binding_handoff": {
                        "joint": "neck_head",
                        "pivot_source": "stations.neck_collar.C",
                        "pivot": [0.0, 1.5, 0.0],
                        "consumed_neck_port_indices": port,
                        "neck_support_ring_indices": support,
                        "head_new_vertex_indices": support,
                    },
                }
            }
        }

    def head_binding(self):
        pivot = [0.0, 1.5, 0.0]
        rest = identity()
        rest[0][3], rest[1][3], rest[2][3] = pivot
        return {
            "rest_frames": {"head": {
                "J": pivot,
                "pivot_source": "stations.neck_collar.C",
                "rest_global": rest,
                "frame_source": CHECKS._HEAD_FRAME_SOURCE,
            }},
            "joints": {"neck": {
                "rest_matrix": rest,
                "inverse_bind_matrix": CHECKS._inverse(rest),
            }},
        }

    def test_head_handoff_consumes_exact_upper_port_but_uses_collar_pivot(self):
        contract = CHECKS._head_metadata_contract(self.head_metadata(), 158)
        self.assertEqual(contract["source_port"], list(range(6)))
        self.assertEqual(contract["consumed_neck_port_indices"], list(range(6)))
        self.assertEqual(contract["J"], (0.0, 1.5, 0.0))
        self.assertEqual(contract["pivot_source"], "stations.neck_collar.C")
        bad = self.head_metadata()
        bad["metadata"]["head"]["binding_handoff"]["consumed_neck_port_indices"] = list(range(1, 7))
        with self.assertRaises(ValueError):
            CHECKS._head_metadata_contract(bad, 158)

    def test_head_source_check_rejects_same_origin_wrong_rotation(self):
        report = CHECKS._report("head-test")
        contract = CHECKS._head_metadata_contract(self.head_metadata(), 158)
        binding = self.head_binding()
        self.assertEqual(CHECKS._head_source_frame_error(report, binding, contract, 1e-9), 0.0)
        wrong = copy.deepcopy(binding)
        wrong["joints"]["neck"]["rest_matrix"][0][0] = -1.0
        error = CHECKS._head_source_frame_error(report, wrong, contract, 1e-9)
        self.assertGreater(error, 1e-9)

    def test_head_endpoint_oracle_has_declared_positive_directions(self):
        binding = self.head_binding()
        yaw = CHECKS._head_endpoint_oracle(binding, {"head": {"yaw": 10.0, "nod": 0.0}})
        nod = CHECKS._head_endpoint_oracle(binding, {"head": {"yaw": 0.0, "nod": 10.0}})
        self.assertGreater(yaw["posed_forward_endpoint"][0], yaw["rest_forward_endpoint"][0])
        self.assertLess(nod["posed_forward_endpoint"][1], nod["rest_forward_endpoint"][1])

    def test_head_harmonic_identity_uses_positions_not_high_vertex_ids(self):
        d0 = list(range(50, 56))
        d1 = list(range(60, 66))
        d2 = list(range(70, 76))
        support = list(range(152, 158))
        root_quads = []
        support_quads = []
        for slot in range(6):
            next_slot = (slot + 1) % 6
            root_quads.extend((
                [d0[slot], d0[next_slot], d1[next_slot], d1[slot]],
                [d1[slot], d1[next_slot], d2[next_slot], d2[slot]],
            ))
            support_quads.append(
                [d0[slot], d0[next_slot], support[next_slot], support[slot]]
            )
        base = {
            "metadata": {"root": {"vertex_count": 152,
                                     "face_count": len(root_quads)}},
        }
        values, diagnostics = CHECKS._head_graph_field(
            base, root_quads + support_quads,
            {"source_port": d0, "support": support},
        )
        self.assertEqual(set(values), set(d0 + d1))
        self.assertTrue(all(math.isfinite(value) for value in values.values()))
        self.assertEqual(diagnostics["support"], support)

    def test_joint_rows_keeps_all_five_six_nine_ten_layouts_explicit(self):
        for order in (CHECKS._JOINTS, CHECKS._HEAD_JOINTS,
                      CHECKS._ARM_JOINTS, CHECKS._ARM_HEAD_JOINTS):
            binding = {"joint_order": list(order),
                       "joints": {name: {"rest_matrix": identity(),
                                          "inverse_bind_matrix": identity()}
                                  for name in order}}
            parents = {"pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
                       "right_hip": "pelvis", "right_knee": "right_hip"}
            if "neck" in order:
                parents["neck"] = "pelvis"
            for side in ("left", "right"):
                if f"{side}_shoulder" in order:
                    parents.update({f"{side}_shoulder": "pelvis",
                                    f"{side}_elbow": f"{side}_shoulder"})
            binding["parents"] = parents
            parsed, _rows, parsed_parents = CHECKS._joint_rows(binding)
            self.assertEqual(tuple(parsed), tuple(order))
            self.assertEqual(parsed_parents, parents)


def comparison_fixture():
    old_l0 = {"vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
              "quads": [[0, 1, 2, 3]]}
    new_l0 = {"vertices": old_l0["vertices"] + [[2.0, 0.0, 0.0], [3.0, 0.0, 0.0], [3.0, 1.0, 0.0], [2.0, 1.0, 0.0]],
              "quads": [[0, 1, 2, 3], [4, 5, 6, 7]]}
    old_l2 = {"vertices": old_l0["vertices"], "quads": [[0, 1, 2, 3]],
              "base_stencils": [[[0, 1.0]], [[1, 1.0]], [[2, 1.0]], [[3, 1.0]]],
              "loops": {"ankle.left": [2, 3, 0]}}
    new_l2 = {"vertices": [[2.0, 0.0, 0.0], [3.0, 0.0, 0.0], [2.0, 1.0, 0.0], [3.0, 1.0, 0.0],
                            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.01, 1.0, 0.0], [0.01, 1.0, 0.0]],
              "quads": [[4, 5, 6, 7], [0, 1, 2, 3]],
              "base_stencils": [[[4, 1.0]], [[5, 1.0]], [[6, 1.0]], [[7, 1.0]],
                                 [[0, 1.0]], [[1, 1.0]], [[4, 1.0]], [[5, 1.0]]],
              "loops": {"ankle.left": [6, 7, 4]}}
    return old_l0, new_l0, old_l2, new_l2


def tail_compare_fixture():
    root_vertices = [[float(index), 0.0, 0.0] for index in range(152)]
    root_vertices[:8] = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0],
                         [0.0, 1.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0],
                         [3.0, 1.0, 0.0], [2.0, 1.0, 0.0]]
    old_l0 = {
        "vertices": root_vertices,
        "quads": [[0, 1, 2, 3], [4, 5, 6, 7]],
    }
    new_l0 = {
        "vertices": old_l0["vertices"] + [[0.0, -0.1, 0.0], [1.0, -0.1, 0.0],
                                             [1.0, -0.2, 0.0], [0.0, -0.2, 0.0],
                                             [0.0, -0.3, 0.0], [1.0, -0.3, 0.0],
                                             [1.0, -0.4, 0.0], [0.0, -0.4, 0.0]],
        "quads": [[0, 1, 152, 153], [4, 5, 6, 7], [1, 2, 154, 153],
                  [152, 153, 155, 154]],
        "metadata": {
            "root": {"vertex_count": 152, "face_count": 2},
            "base_vertex_count": 160,
            "index_mapping": {
                "root_face_mappings_excluding_tail_host": [[1, 1]],
            },
            "tail": tail_metadata(list(range(152, 160)), [0, 1, 2, 3]),
        },
    }
    old_l2 = {
        "vertices": copy.deepcopy(old_l0["vertices"][:8]),
        "quads": [[0, 1, 2, 3], [4, 5, 6, 7]],
        "base_stencils": [[[index, 1.0]] for index in range(8)],
    }
    new_l2 = {
        "vertices": [[0.1, 0.0, 0.0], [1.1, 0.0, 0.0], [1.0, 1.0, 0.0],
                     [0.0, 1.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0],
                     [3.0, 1.0, 0.0], [2.0, 1.0, 0.0]],
        "quads": [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 2, 3], [4, 5, 6, 7]],
        "base_stencils": [[[8, 1.0]], [[9, 1.0]], [[2, 1.0]], [[3, 1.0]],
                           [[4, 1.0]], [[5, 1.0]], [[6, 1.0]], [[7, 1.0]]],
    }
    return old_l0, new_l0, old_l2, new_l2


def combined_tail_compare_fixture():
    """Local CC changes are declared at tail, arm, head, and foot seams."""
    root_vertices = [[float(index), 0.0, 0.0] for index in range(152)]
    tail_vertices = [[float(index), -1.0, 0.0] for index in range(152, 160)]
    old_l0 = {
        "vertices": root_vertices,
        "quads": [[0, 1, 2, 3], [4, 5, 6, 7]],
    }
    new_l0 = {
        "vertices": root_vertices + tail_vertices,
        "quads": [[0, 1, 152, 153], [4, 5, 6, 7],
                  [152, 153, 154, 155], [156, 157, 158, 159]],
        "metadata": {
            "base_vertex_count": 160,
            "root": {"vertex_count": 152, "face_count": 2},
            "index_mapping": {"root_face_mappings_excluding_tail_host": [[1, 1]]},
            "tail": tail_metadata(list(range(152, 160)), [0, 1, 2]),
            "arms": {
                "left": {"source_port": {"indices": [4]}},
                "right": {"source_port": {"indices": [7]}},
            },
            "head": {"binding_handoff": {"consumed_neck_port_indices": [5]}},
            "feet": {
                "left": {"ankle_source_loop": [6]},
                "right": {"ankle_source_loop": [6]},
            },
        },
    }
    old_l2 = {
        "vertices": copy.deepcopy(root_vertices[:8]),
        "quads": [[0, 1, 2, 3], [4, 5, 6, 7]],
        "base_stencils": [[[index, 1.0]] for index in range(8)],
    }
    new_l2 = {
        "vertices": copy.deepcopy(root_vertices[:8]),
        "quads": [[0, 1, 2, 3], [4, 5, 6, 7],
                  [0, 1, 2, 3], [4, 5, 6, 7]],
        "base_stencils": [
            [[0, 0.5], [152, 0.5]], [[1, 0.5], [153, 0.5]],
            [[2, 0.5], [154, 0.5]], [[3, 0.5], [155, 0.5]],
            [[4, 0.5], [152, 0.5]], [[5, 0.5], [153, 0.5]],
            [[6, 0.5], [154, 0.5]], [[7, 1.0]],
        ],
    }
    return old_l0, new_l0, old_l2, new_l2


class CompareRootTests(unittest.TestCase):
    def test_shifted_l2_vertex_indices_use_face_prefix_mapping(self):
        report = CHECKS.compare_root(*comparison_fixture())
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["l2_face_prefix_mapping_consistent"])
        self.assertEqual(report["metrics"]["changed_stencil_count"], 2)
        self.assertIsNotNone(report["metrics"]["changed_stencil_location_worst"])

    def test_original_l0_prefix_defect_is_reported(self):
        values = list(comparison_fixture())
        values[1] = copy.deepcopy(values[1])
        values[1]["vertices"][0][0] = 0.1
        report = CHECKS.compare_root(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["original_l0_vertex_prefix"])

    def test_tail_compare_replaces_only_declared_host_and_keeps_far_support(self):
        report = CHECKS.compare_root(*tail_compare_fixture())
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["tail_explicit_host_identity"])
        self.assertTrue(report["checks"]["tail_kept_root_faces_exact"])
        self.assertTrue(report["checks"]["tail_far_support_invariance"])
        self.assertTrue(report["checks"]["tail_near_attachment_changes_labelled"])

    def test_combined_appendage_local_stencils_are_labelled_without_hiding_far_rows(self):
        report = CHECKS.compare_root(*combined_tail_compare_fixture())
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["l2_face_prefix_mapping_consistent"])
        self.assertTrue(report["checks"]["same_full_stencil_unchanged_invariance"])
        self.assertTrue(report["checks"]["tail_near_attachment_changes_labelled"])
        sources = {
            source
            for row in report["metrics"]["changed_stencil_displacements"]
            for source in row.get("attachment_sources", [])
        }
        self.assertEqual(sources, {"arms", "feet", "head", "tail"})

    def test_tail_compare_rejects_far_support_displacement(self):
        values = list(tail_compare_fixture())
        values[3] = copy.deepcopy(values[3])
        values[3]["vertices"][4][0] += 0.25
        report = CHECKS.compare_root(*values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["tail_far_support_invariance"])

    def test_leg_root_ports_are_declared_from_prior_boundary_and_label_changes(self):
        prior_root = {
            "vertices": [[float(index), 0.0, 0.0] for index in range(12)],
            "quads": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]],
            "loops": {
                "port.left_thigh": [4, 5, 6, 7],
                "port.right_thigh": [8, 9, 10, 11],
            },
        }
        expanded = {
            "metadata": {
                "chains": {
                    "left": {"root_exit": [4, 5, 6, 7]},
                    "right": {"root_exit": [8, 9, 10, 11]},
                },
                "root": {"old_thigh_ports_closed": {
                    "left": [4, 5, 6, 7], "right": [8, 9, 10, 11],
                }},
            }
        }
        attachments = CHECKS._declared_attachment_vertices(
            expanded, {"host_vertices": [0, 1, 2, 3]}, prior_root)
        self.assertEqual(attachments["leg_left"], {4, 5, 6, 7})
        self.assertEqual(attachments["leg_right"], {8, 9, 10, 11})

    def test_leg_root_port_outside_prior_boundary_is_rejected(self):
        prior_root = {
            "vertices": [[float(index), 0.0, 0.0] for index in range(12)],
            "quads": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]],
            "loops": {
                "port.left_thigh": [4, 5, 6, 7],
                "port.right_thigh": [8, 9, 10, 11],
            },
        }
        expanded = {"metadata": {"chains": {
            "left": {"root_exit": [4, 5, 6, 0]},
            "right": {"root_exit": [8, 9, 10, 11]},
        }}}
        with self.assertRaises(ValueError):
            CHECKS._declared_attachment_vertices(
                expanded, {"host_vertices": [0, 1, 2, 3]}, prior_root)


if __name__ == "__main__":
    unittest.main()

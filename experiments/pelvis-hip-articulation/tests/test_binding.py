from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

import numpy as np


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_DIR))
import binding  # noqa: E402


def _mesh_fixture() -> tuple[dict, dict, dict, dict]:
    # Four quads make a connected boundary-edge graph.  The two unknowns on
    # each side have the hand-solvable system [[2,-1],[-1,3]].
    vertices = [
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0], [4.0, 0.0, 0.0], [5.0, 0.0, 0.0],
        [4.0, 1.0, 0.0], [4.0, 1.0, 0.0], [2.0, 0.0, 0.0],
    ]
    quads = [[0, 1, 2, 8], [0, 8, 3, 1],
             [4, 5, 6, 8], [4, 8, 7, 5]]
    transitions = {
        "left": {"socket": [0], "ringA": [1], "ringB": [2], "exit": [3]},
        "right": {"socket": [4], "ringA": [5], "ringB": [6], "exit": [7]},
    }
    base = {
        "schema": "synthetic-l0",
        "level": 0,
        "vertices": vertices,
        "quads": quads,
        "base_stencils": [[[index, 1.0]] for index in range(len(vertices))],
        "loops": {"port.left_thigh": [3], "port.right_thigh": [7]},
        "control_owners": [f"owner-{index}" for index in range(len(vertices))],
        "face_owners": ["face-owner"] * len(quads),
        "metadata": {"transition_indices": transitions},
    }
    rest_vertices = copy.deepcopy(vertices) + [[0.75, 0.0, 0.0]]
    rest = {
        "schema": "synthetic-l2",
        "level": 2,
        "vertices": rest_vertices,
        "quads": copy.deepcopy(quads),
        "base_stencils": copy.deepcopy(base["base_stencils"]) + [[[0, 0.25], [1, 0.75]]],
        "loops": {"port.left_thigh": [3], "port.right_thigh": [7]},
        "control_owners": [f"evaluated-owner-{index}" for index in range(len(rest_vertices))],
        "face_owners": ["evaluated-face-owner"] * len(quads),
        "metadata": {"transition_indices": copy.deepcopy(transitions)},
    }
    components = {f"component_{index:02d}": float(index) for index in range(92)}
    case = {
        "id": "synthetic-independent-joints",
        "components": components,
        "attachments": {
            "left": {"centre": [0.0, 1.0, 0.0], "knee": [0.0, -1.0, 0.0]},
            "right": {"centre": [11.0, 5.0, 0.0], "knee": [10.0, 4.0, 0.0]},
        },
    }
    landmarks = {"joint_left": [0.0, 0.0, 0.0],
                 "joint_right": [10.0, 5.0, 0.0]}
    return base, rest, case, landmarks


def _binding() -> tuple[dict, dict, dict, dict, dict]:
    base, rest, case, landmarks = _mesh_fixture()
    result = binding.bind(base, rest, case, landmarks)
    return result, base, rest, case, landmarks


class BindingTests(unittest.TestCase):
    def test_uniform_harmonic_weights_are_positive_and_partitioned(self) -> None:
        result, _base, _rest, case, _landmarks = _binding()
        weights = np.asarray(result["base_weights"])
        np.testing.assert_allclose(weights.sum(axis=1), 1.0, atol=1.0e-12)
        self.assertTrue(np.all(weights >= 0.0))
        self.assertTrue(np.all(weights[:2, :2] > 0.0))
        np.testing.assert_allclose(weights[0], [0.6, 0.4, 0.0])
        np.testing.assert_allclose(weights[1], [0.2, 0.8, 0.0])
        np.testing.assert_allclose(weights[2], [0.0, 1.0, 0.0])
        np.testing.assert_allclose(weights[6], [0.0, 0.0, 1.0])
        self.assertEqual(len(result["evaluated_weights"]), 10)
        self.assertEqual(len(case["components"]), 92)

    def test_stencil_propagation_and_full_strength_distal_ports(self) -> None:
        result, _base, rest, _case, _landmarks = _binding()
        evaluated = np.asarray(result["evaluated_weights"])
        base_weights = np.asarray(result["base_weights"])
        np.testing.assert_allclose(evaluated[9],
                                   0.25 * base_weights[0] + 0.75 * base_weights[1])
        self.assertEqual(result["metadata"]["l2_distal_port_loop_counts"],
                         {"port.left_thigh": 1, "port.right_thigh": 1})
        self.assertEqual(result["l0_anchor_indices"]["left"]["exit"], [3])
        self.assertEqual(rest["base_stencils"][9], [[0, 0.25], [1, 0.75]])

    def test_json_safe_and_rest_metadata_are_explicit(self) -> None:
        result, _base, rest, _case, _landmarks = _binding()
        json.dumps(result)
        posed = binding.pose(rest, result, {"left": 0.0, "right": 0.0})
        json.dumps(posed)
        self.assertEqual(posed["provenance"]["base_stencils"], "REST")
        self.assertFalse(posed["metadata"]["posed_cage_evaluation"])
        self.assertEqual(posed["quads"], rest["quads"])
        self.assertEqual(posed["loops"], rest["loops"])
        self.assertEqual(posed["control_owners"], rest["control_owners"])
        self.assertEqual(posed["face_owners"], rest["face_owners"])
        self.assertEqual(posed["base_stencils"], rest["base_stencils"])

    def test_hand_calculable_positive_90_degree_pivot_transform(self) -> None:
        result, _base, rest, _case, _landmarks = _binding()
        points = binding.joint_points(result, {"left": 90.0, "right": 0.0})
        left = points["left"]
        np.testing.assert_allclose(left["posed_J"], left["J"], atol=1.0e-12)
        np.testing.assert_allclose(left["T"], [0.0, 0.0, -1.0], atol=1.0e-12)
        np.testing.assert_allclose(left["K"], [0.0, 0.0, 1.0], atol=1.0e-12)
        np.testing.assert_allclose(left["posed_T"], [0.0, 0.0, -1.0], atol=1.0e-12)
        np.testing.assert_allclose(left["posed_K"], [0.0, 0.0, 1.0], atol=1.0e-12)
        np.testing.assert_allclose(left["skin_matrix"],
                                   [[1.0, 0.0, 0.0, 0.0],
                                    [0.0, 0.0, 1.0, 0.0],
                                    [0.0, -1.0, 0.0, 0.0],
                                    [0.0, 0.0, 0.0, 1.0]], atol=1.0e-12)
        posed = binding.pose(rest, result, {"left": 90.0, "right": 0.0})
        np.testing.assert_allclose(posed["vertices"][3], [0.0, 0.0, -1.0], atol=1.0e-12)

    def test_independent_joints_change_frames_not_topology_weights_or_rest(self) -> None:
        result, base, rest, case, landmarks = _binding()
        changed = copy.deepcopy(landmarks)
        changed["joint_left"] = [2.0, 3.0, 4.0]
        changed_result = binding.bind(base, rest, case, changed)
        self.assertEqual(changed_result["base_weights"], result["base_weights"])
        self.assertEqual(changed_result["evaluated_weights"], result["evaluated_weights"])
        self.assertNotEqual(changed_result["rest_frames"]["left"]["rest_matrix"],
                            result["rest_frames"]["left"]["rest_matrix"])
        self.assertEqual(rest["vertices"], _mesh_fixture()[1]["vertices"])
        posed = binding.pose(rest, changed_result, {"left": 0.0, "right": 0.0})
        self.assertEqual(posed["vertices"], rest["vertices"])

    def test_zero_angle_pose_is_identity(self) -> None:
        result, _base, rest, _case, _landmarks = _binding()
        posed = binding.pose(rest, result, {"left": 0, "right": 0})
        self.assertEqual(posed["vertices"], rest["vertices"])
        points = binding.joint_points(result, {"left": 0, "right": 0})
        for side in ("left", "right"):
            np.testing.assert_array_equal(points[side]["rest_matrix"],
                                          points[side]["posed_matrix"])
            np.testing.assert_array_equal(points[side]["skin_matrix"], np.eye(4))

    def test_wrong_indices_and_disconnected_graph_fail(self) -> None:
        base, rest, case, landmarks = _mesh_fixture()
        wrong = copy.deepcopy(base)
        wrong["metadata"]["transition_indices"]["left"]["socket"] = [99]
        with self.assertRaises(ValueError):
            binding.bind(wrong, rest, case, landmarks)

        disconnected = copy.deepcopy(base)
        disconnected["vertices"].append([20.0, 0.0, 0.0])
        disconnected["base_stencils"].append([[9, 1.0]])
        with self.assertRaises(ValueError):
            binding.bind(disconnected, rest, case, landmarks)

    def test_material_negative_weights_fail_without_clamping(self) -> None:
        base, rest, case, landmarks = _mesh_fixture()
        negative = copy.deepcopy(rest)
        negative["base_stencils"][9] = [[2, 2.0], [0, -1.0]]
        with self.assertRaises(ValueError):
            binding.bind(base, negative, case, landmarks)

        result, _base, rest, _case, _landmarks = _binding()
        tampered = copy.deepcopy(result)
        tampered["evaluated_weights"][9][0] = -0.01
        with self.assertRaises(ValueError):
            binding.pose(rest, tampered, {"left": 0.0, "right": 0.0})


if __name__ == "__main__":
    unittest.main()

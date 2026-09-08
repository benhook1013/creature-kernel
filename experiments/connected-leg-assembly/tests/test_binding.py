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
import arm_construction  # noqa: E402
import construction  # noqa: E402
import head_construction  # noqa: E402


ROOT_COUNT = 152
STATION_NAMES = ("mid_thigh", "knee_pre_support", "knee", "knee_post_support", "calf", "ankle_approach", "ankle")
INPUTS = json.loads((EXPERIMENT_DIR / "inputs.json").read_text(encoding="utf-8"))
ARM_INPUTS = json.loads((EXPERIMENT_DIR / "arm-inputs.json").read_text(encoding="utf-8"))
HEAD_INPUTS = json.loads((EXPERIMENT_DIR / "head-inputs.json").read_text(encoding="utf-8"))
ARM_CASE_IDS = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")


def _angles(left_hip=0.0, left_knee=0.0, right_hip=0.0, right_knee=0.0):
    return {
        "left": {"hip": left_hip, "knee": left_knee, "ankle": 0.0},
        "right": {"hip": right_hip, "knee": right_knee, "ankle": 0.0},
    }


def _arm_angles(left_hip=0.0, left_knee=0.0, right_hip=0.0, right_knee=0.0,
                left_raise=0.0, left_forward=0.0, left_elbow=0.0,
                right_raise=0.0, right_forward=0.0, right_elbow=0.0):
    return {
        "left": {"hip": left_hip, "knee": left_knee,
                  "shoulder_raise": left_raise,
                  "shoulder_forward": left_forward, "elbow": left_elbow},
        "right": {"hip": right_hip, "knee": right_knee,
                   "shoulder_raise": right_raise,
                   "shoulder_forward": right_forward, "elbow": right_elbow},
    }


def _head_angles(yaw=0.0, nod=0.0):
    return {
        "left": {"hip": 0.0, "knee": 0.0, "ankle": 0.0},
        "right": {"hip": 0.0, "knee": 0.0, "ankle": 0.0},
        "head": {"yaw": yaw, "nod": nod},
    }


def _fixture(nonzero_rest_shank: bool = False):
    root_vertices = [
        [float(index % 19) * 0.01, 1.0 + float(index // 19) * 0.01,
         float(index % 3) * 0.02]
        for index in range(ROOT_COUNT)
    ]
    root_quads = [[4 * index + slot for slot in range(4)]
                  for index in range(ROOT_COUNT // 4)]
    left_j = [-0.5, 1.0, 0.0]
    left_t = [-0.5, 0.9, 0.0]
    left_k = [-0.5, 0.0, 0.0]
    right_j = [0.5, 1.0, 0.0]
    right_t = [0.5, 0.9, 0.0]
    right_k = [0.5, 0.0, 0.0]
    left_a = [-0.5, -0.8, 0.4] if nonzero_rest_shank else [-0.5, -1.0, 0.0]
    right_a = [0.5, -0.8, -0.4] if nonzero_rest_shank else [0.5, -1.0, 0.0]
    legs = {
        "left": {"J": left_j, "T": left_t, "K": left_k, "A": left_a,
                  "mid_thigh_factor": 0.85, "support_fraction": 0.1},
        "right": {"J": right_j, "T": right_t, "K": right_k, "A": right_a,
                   "mid_thigh_factor": 0.85, "support_fraction": 0.1},
    }

    vertices = copy.deepcopy(root_vertices)
    rings = {"left": [], "right": []}
    for side, sign in (("left", -1.0), ("right", 1.0)):
        j, t, k, a = (np.asarray(legs[side][name], dtype=float)
                      for name in ("J", "T", "K", "A"))
        centres = (t + 0.70 * (k - t), t + 0.90 * (k - t), k,
                   k + 0.12 * (a - k), k + 0.35 * (a - k),
                   k + 0.72 * (a - k), a)
        for station_index, centre in enumerate(centres):
            ring = list(range(len(vertices), len(vertices) + 8))
            rings[side].append(ring)
            for corner in range(8):
                # The small ring is synthetic; its mean is the declared
                # station point and it uses metres/Y-up/Z-front coordinates.
                lateral = 0.02 if corner & 1 else -0.02
                depth = 0.015 if corner & 2 else -0.015
                vertical = 0.015 if corner & 4 else -0.015
                vertices.append((centre + [lateral * sign, vertical, depth]).tolist())

    all_quads = copy.deepcopy(root_quads)
    for side in ("left", "right"):
        for ring in rings[side]:
            all_quads.append(ring[:4])
    chains = {}
    for side in ("left", "right"):
        centres = (np.asarray(legs[side]["T"], dtype=float) +
                   0.70 * (np.asarray(legs[side]["K"], dtype=float) -
                           np.asarray(legs[side]["T"], dtype=float)),
                   np.asarray(legs[side]["T"], dtype=float) +
                   0.90 * (np.asarray(legs[side]["K"], dtype=float) -
                           np.asarray(legs[side]["T"], dtype=float)),
                   np.asarray(legs[side]["K"], dtype=float),
                   np.asarray(legs[side]["K"], dtype=float) +
                   0.12 * (np.asarray(legs[side]["A"], dtype=float) -
                           np.asarray(legs[side]["K"], dtype=float)),
                   np.asarray(legs[side]["K"], dtype=float) +
                   0.35 * (np.asarray(legs[side]["A"], dtype=float) -
                           np.asarray(legs[side]["K"], dtype=float)),
                   np.asarray(legs[side]["K"], dtype=float) +
                   0.72 * (np.asarray(legs[side]["A"], dtype=float) -
                           np.asarray(legs[side]["K"], dtype=float)),
                   np.asarray(legs[side]["A"], dtype=float))
        sections = [{"name": name, "path": "T_to_K" if index < 3 else "K_to_A",
                     "fraction": (0.70, 0.90, 1.0, 0.12, 0.35, 0.72, 1.0)[index],
                     "indices": copy.deepcopy(ring), "centre": centre.tolist(),
                     "order": index}
                    for index, (name, ring, centre) in enumerate(
                        zip(STATION_NAMES, rings[side], centres))]
        chains[side] = {
            "sections": sections,
            "ring_order": list(STATION_NAMES),
            "ring_indices_by_name": {section["name"]: copy.deepcopy(section["indices"])
                                      for section in sections},
            "new_vertex_indices": [index for ring in rings[side] for index in ring],
        }
    base = {
        "schema": "synthetic-connected-leg-l0",
        "level": 0,
        "vertices": vertices,
        "quads": all_quads,
        "metadata": {
            "root": {"vertex_count": ROOT_COUNT, "face_count": len(root_quads)},
            "index_mapping": {
                "root_vertex_old_to_new": [[index, index] for index in range(ROOT_COUNT)],
                "root_face_old_to_new": [[index, index] for index in range(len(root_quads))],
            },
            "chains": chains,
        },
    }
    rest = {
        "schema": "synthetic-connected-leg-l2",
        "level": 2,
        "vertices": copy.deepcopy(vertices),
        "quads": copy.deepcopy(all_quads),
        "base_stencils": [[[index, 1.0]] for index in range(len(vertices))],
        "metadata": {"source": "synthetic-rest"},
    }
    prior_root = {
        "schema": "synthetic-prior-root-l0",
        "level": 0,
        "vertices": copy.deepcopy(root_vertices),
        "quads": copy.deepcopy(root_quads),
    }
    prior_weights = []
    for index in range(ROOT_COUNT):
        if index % 3 == 0:
            prior_weights.append([0.6, 0.4, 0.0])
        elif index % 3 == 1:
            prior_weights.append([0.2, 0.0, 0.8])
        else:
            prior_weights.append([1.0, 0.0, 0.0])
    prior_binding = {
        "schema": "creature-kernel.pelvis-hip-articulation-binding.v1",
        "base_weights": prior_weights,
    }
    return base, rest, prior_root, prior_binding, legs


def _bound(nonzero_rest_shank: bool = False):
    values = _fixture(nonzero_rest_shank)
    return binding.bind(*values), values


def _foot_fixture():
    base, rest, prior_root, prior_binding, legs = _fixture()
    foot_points = {
        "left": [
            [-0.54, -1.10, -0.08], [-0.46, -1.10, -0.08],
            [-0.54, -1.10, 0.08], [-0.46, -1.10, 0.08],
            [-0.50, -1.12, 0.16],
        ],
        "right": [
            [0.46, -1.10, -0.08], [0.54, -1.10, -0.08],
            [0.46, -1.10, 0.08], [0.54, -1.10, 0.08],
            [0.50, -1.12, 0.16], [0.50, -1.14, 0.24],
        ],
    }
    foot_indices = {}
    for side in ("left", "right"):
        indices = []
        for point in foot_points[side]:
            indices.append(len(base["vertices"]))
            base["vertices"].append(list(point))
        foot_indices[side] = indices
    base["metadata"]["feet"] = {
        side: {"new_vertex_indices": copy.deepcopy(indices)}
        for side, indices in foot_indices.items()
    }
    for side, indices in foot_indices.items():
        base["quads"].extend([
            indices[:4], indices[1:5],
        ])
    rest["vertices"] = copy.deepcopy(base["vertices"])
    rest["quads"] = copy.deepcopy(base["quads"])
    rest["base_stencils"] = [
        [[index, 1.0]] for index in range(len(rest["vertices"]))
    ]
    mixed_index = foot_indices["left"][1]
    root_index = 0
    rest["base_stencils"][mixed_index] = [
        [root_index, 0.25], [mixed_index, 0.75],
    ]
    return base, rest, prior_root, prior_binding, legs


def _foot_bound():
    values = _foot_fixture()
    return binding.bind(*values), values


def _tail_fixture():
    base, rest, prior_root, prior_binding, legs = _fixture()
    host_face = 2
    host_vertices = copy.deepcopy(prior_root["quads"][host_face])
    source_phase = [[-1, -1], [-1, 1], [1, 1], [1, -1]]
    tail_indices = list(range(len(base["vertices"]), len(base["vertices"]) + 8))
    for point in (
        [0.0, 0.5, -0.05], [0.05, 0.5, -0.05],
        [0.05, 0.55, -0.05], [0.0, 0.55, -0.05],
        [0.0, 0.25, -0.15], [0.04, 0.25, -0.15],
        [0.04, 0.29, -0.15], [0.0, 0.29, -0.15],
    ):
        base["vertices"].append(point)
    ring0, ring1 = tail_indices[:4], tail_indices[4:]
    base["quads"][host_face] = [host_vertices[0], host_vertices[1], ring0[1], ring0[0]]
    base["quads"].extend([
        [host_vertices[1], host_vertices[2], ring0[2], ring0[1]],
        [host_vertices[2], host_vertices[3], ring0[3], ring0[2]],
        [host_vertices[3], host_vertices[0], ring0[0], ring0[3]],
        [ring0[0], ring0[1], ring1[1], ring1[0]],
        [ring0[1], ring0[2], ring1[2], ring1[1]],
        [ring0[2], ring0[3], ring1[3], ring1[2]],
        [ring0[3], ring0[0], ring1[0], ring1[3]],
        ring1,
    ])
    supports = {
        str(index): {
            "host_vertex_indices": copy.deepcopy(host_vertices),
            "host_corner": index % 4,
            "source_phase": copy.deepcopy(source_phase[index % 4]),
            "convex_weights": [
                0.55 if slot == index % 4 else 0.15
                for slot in range(4)
            ],
            "target_joint": "pelvis",
        }
        for index in tail_indices
    }
    kept_faces = [[index, index] for index in range(len(prior_root["quads"]))
                  if index != host_face]
    replacement_faces = [host_face, len(prior_root["quads"]),
                         len(prior_root["quads"]) + 1,
                         len(prior_root["quads"]) + 2]
    base["metadata"]["index_mapping"]["root_face_mappings_excluding_tail_host"] = kept_faces
    base["metadata"]["tail"] = {
        "enabled": True,
        "source_host_identity": {
            "face_index": host_face,
            "vertex_indices": copy.deepcopy(host_vertices),
            "owner": "domain.pelvis",
        },
        "face_replacement": {
            "original_face_index": host_face,
            "original_quad": copy.deepcopy(host_vertices),
            "replacement_face_indices": replacement_faces,
            "one_to_many": [[host_face, *replacement_faces]],
            "original_host_retained": False,
        },
        "ring_indices": [ring0, ring1],
        "station_fractions": [0.0, 1.0],
        "source_phase": source_phase,
        "host": {"source_phase": copy.deepcopy(source_phase)},
        "new_vertex_indices": tail_indices,
        "transition_weights": {
            "status": "implemented",
            "collar_blend_strength": 0.5,
            "future_target_joint": "pelvis",
            "supports": supports,
        },
    }
    rest["vertices"] = copy.deepcopy(base["vertices"])
    rest["quads"] = copy.deepcopy(base["quads"])
    rest["base_stencils"] = [
        [[index, 1.0]] for index in range(len(rest["vertices"]))
    ]
    return base, rest, prior_root, prior_binding, legs


def _tail_bound():
    values = _tail_fixture()
    return binding.bind(*values), values


def _actual_arm_cases():
    arm_rows = {row["case_id"]: row["sides"] for row in ARM_INPUTS["cases"]}
    cases = []
    for row in INPUTS["cases"]:
        if row["id"] not in ARM_CASE_IDS:
            continue
        root = json.loads(Path(row["root_mesh"]["path"]).read_text(encoding="utf-8"))
        source = json.loads(Path(row["original_case"]["path"]).read_text(encoding="utf-8"))
        prior_binding = json.loads(Path(row["prior_hip_binding"]["path"]).read_text(encoding="utf-8"))
        base = construction.build(root, row["leg_inputs"])
        arm_mesh = arm_construction.build(base, source, arm_rows[row["id"]])
        levels = arm_construction.evaluate(arm_mesh, levels=2)
        bound = binding.bind(arm_mesh, levels[2], root, prior_binding, row["leg_inputs"])
        cases.append((row["id"], root, arm_mesh, levels[2], prior_binding, bound))
    if tuple(case[0] for case in cases) != ARM_CASE_IDS:
        raise AssertionError("canonical arm cases were not loaded")
    return cases


def _actual_head_cases(with_arms=False):
    head_rows = {row["case_id"]: row["head"] for row in HEAD_INPUTS["cases"]}
    cases = []
    for row in INPUTS["cases"]:
        if row["id"] not in ARM_CASE_IDS:
            continue
        root = json.loads(Path(row["root_mesh"]["path"]).read_text(encoding="utf-8"))
        source = json.loads(Path(row["original_case"]["path"]).read_text(encoding="utf-8"))
        prior_binding = json.loads(Path(row["prior_hip_binding"]["path"]).read_text(encoding="utf-8"))
        base = construction.build(root, row["leg_inputs"])
        if with_arms:
            arm_rows = {item["case_id"]: item["sides"] for item in ARM_INPUTS["cases"]}
            base = arm_construction.build(base, source, arm_rows[row["id"]])
        head_mesh = head_construction.build(base, source, head_rows[row["id"]])
        levels = head_construction.evaluate(head_mesh, levels=2)
        bound = binding.bind(head_mesh, levels[2], root, prior_binding, row["leg_inputs"])
        cases.append((row["id"], root, source, head_mesh, levels[2], prior_binding, bound))
    if tuple(case[0] for case in cases) != ARM_CASE_IDS:
        raise AssertionError("canonical head cases were not loaded")
    return cases


class BindingTests(unittest.TestCase):
    def test_root_weight_preservation_and_five_column_mapping(self) -> None:
        bound, (_base, _rest, _prior_root, prior_binding, _legs) = _bound()
        prior = np.asarray(prior_binding["base_weights"])
        actual = np.asarray(bound["base_weights"][:ROOT_COUNT])
        expected = np.column_stack((prior[:, 0], prior[:, 1],
                                    np.zeros(ROOT_COUNT), prior[:, 2],
                                    np.zeros(ROOT_COUNT)))
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(bound["joint_order"],
                         ["pelvis", "left_hip", "left_knee",
                          "right_hip", "right_knee"])
        self.assertEqual(bound["weight_columns"],
                         ["pelvis", "left_thigh", "left_shank",
                          "right_thigh", "right_shank"])
        self.assertNotIn("foot_vertex_indices", bound)
        for side in ("left", "right"):
            actual_centres = bound["station_points"][side]
            sections = _base["metadata"]["chains"][side]["sections"]
            metadata_centres = [section["centre"] for section in sections]
            self.assertEqual(actual_centres, metadata_centres)

    def test_stencil_propagation_produces_all_five_columns(self) -> None:
        base, rest, prior_root, prior_binding, legs = _fixture()
        rest["base_stencils"][-1] = [[0, 0.25], [152, 0.75]]
        bound = binding.bind(base, rest, prior_root, prior_binding, legs)
        expected = (0.25 * np.asarray(bound["base_weights"][0]) +
                    0.75 * np.asarray(bound["base_weights"][152]))
        np.testing.assert_allclose(bound["evaluated_weights"][-1], expected)
        self.assertEqual(len(bound["evaluated_weights"][-1]), 5)
        json.dumps(bound)

    def test_hierarchy_records_nonzero_rest_shank_angle(self) -> None:
        bound, _values = _bound(nonzero_rest_shank=True)
        points = binding.joint_points(bound, _angles())
        left_local = np.asarray(points["left"]["knee"]["rest_local"])
        self.assertFalse(np.allclose(left_local[:3, :3], np.eye(3)))
        np.testing.assert_allclose(points["left"]["posed_K"],
                                   points["left"]["rest_K"])

    def test_rest_pose_is_identity_and_preserves_topology(self) -> None:
        bound, (_base, rest, _prior_root, _prior_binding, _legs) = _bound()
        posed = binding.pose(rest, bound, _angles())
        self.assertEqual(posed["vertices"], rest["vertices"])
        self.assertEqual(posed["quads"], rest["quads"])
        self.assertEqual(posed["base_stencils"], rest["base_stencils"])
        self.assertEqual(posed["metadata"]["representation"], "pose")
        self.assertFalse(posed["metadata"]["posed_cage_evaluation"])
        points = binding.joint_points(bound, _angles())
        for side in ("left", "right"):
            np.testing.assert_array_equal(points[side]["thigh"]["skin_matrix"], np.eye(4))
            np.testing.assert_array_equal(points[side]["knee"]["skin_matrix"], np.eye(4))

    def test_parent_hip_carries_knee_when_knee_angle_is_zero(self) -> None:
        bound, _values = _bound(nonzero_rest_shank=True)
        points = binding.joint_points(bound, _angles(left_hip=30.0))
        left = points["left"]
        np.testing.assert_allclose(left["posed_K_from_parent"],
                                   left["posed_K_from_knee"], atol=1.0e-10)
        np.testing.assert_allclose(left["posed_A"],
                                   (np.asarray(left["thigh"]["skin_matrix"]) @
                                    np.r_[left["rest_A"], 1.0])[:3],
                                   atol=1.0e-10)

    def test_positive_knee_angle_moves_ankle_back_in_negative_z(self) -> None:
        bound, _values = _bound()
        points = binding.joint_points(bound, _angles(left_knee=30.0))
        self.assertLess(points["left"]["posed_A"][2], 0.0)
        np.testing.assert_allclose(points["left"]["posed_K"],
                                   points["left"]["rest_K"], atol=1.0e-10)

    def test_mirrored_inputs_have_mirrored_pose_response(self) -> None:
        bound, _values = _bound()
        points = binding.joint_points(
            bound, _angles(left_hip=20.0, left_knee=25.0,
                           right_hip=20.0, right_knee=25.0)
        )
        left = np.asarray(points["left"]["posed_A"])
        right = np.asarray(points["right"]["posed_A"])
        np.testing.assert_allclose(left, [-right[0], right[1], right[2]], atol=1.0e-10)

    def test_invalid_inputs_are_rejected(self) -> None:
        base, rest, prior_root, prior_binding, legs = _fixture()
        wrong_root = copy.deepcopy(base)
        wrong_root["vertices"][0][0] += 1.0e-6
        with self.assertRaises(ValueError):
            binding.bind(wrong_root, rest, prior_root, prior_binding, legs)

        negative_prior = copy.deepcopy(prior_binding)
        negative_prior["base_weights"][0] = [-0.1, 1.1, 0.0]
        with self.assertRaises(ValueError):
            binding.bind(base, rest, prior_root, negative_prior, legs)

        missing_chain = copy.deepcopy(base)
        missing_chain["metadata"] = {}
        with self.assertRaises(ValueError):
            binding.bind(missing_chain, rest, prior_root, prior_binding, legs)

        degenerate_leg = copy.deepcopy(legs)
        degenerate_leg["left"]["J"] = copy.deepcopy(degenerate_leg["left"]["K"])
        with self.assertRaises(ValueError):
            binding.bind(base, rest, prior_root, prior_binding, degenerate_leg)

        bad_stencil = copy.deepcopy(rest)
        bad_stencil["base_stencils"][0] = [[0, 0.5]]
        with self.assertRaises(ValueError):
            binding.bind(base, bad_stencil, prior_root, prior_binding, legs)

        bound, _ = _bound()
        tampered = copy.deepcopy(bound)
        tampered["evaluated_weights"][0][0] = -0.1
        with self.assertRaises(ValueError):
            binding.pose(rest, tampered, _angles())

        nonzero_ankle = _angles()
        nonzero_ankle["left"]["ankle"] = 1.0
        with self.assertRaises(ValueError):
            binding.pose(rest, bound, nonzero_ankle)

    def test_weight_guard_recovers_baseline_roundoff_without_relaxing_real_bounds(self) -> None:
        one_ulp_over = np.nextafter(1.0, 2.0)
        binding._check_weight_bounds(
            np.asarray([[one_ulp_over, 0.0, 0.0]], dtype=float),
            "one_ulp",
        )
        with self.assertRaises(ValueError):
            binding._check_weight_bounds(
                np.asarray([[1.0 + 2.0 * binding._TOLERANCE, 0.0, 0.0]], dtype=float),
                "real_upper",
            )
        with self.assertRaises(ValueError):
            binding._check_weight_bounds(
                np.asarray([[-2.0 * binding._TOLERANCE, 1.0 + 2.0 * binding._TOLERANCE, 0.0]], dtype=float),
                "real_lower",
            )
        with self.assertRaises(ValueError):
            binding._check_weight_bounds(
                np.asarray([[0.5, 0.4, 0.0]], dtype=float),
                "partition",
            )

    def test_explicit_feet_use_semantic_indices_and_preserve_zero_pose(self) -> None:
        bound, (base, rest, _prior_root, _prior_binding, _legs) = _foot_bound()
        feet = base["metadata"]["feet"]
        for side in ("left", "right"):
            indices = feet[side]["new_vertex_indices"]
            self.assertEqual(bound["foot_vertex_indices"][side], indices)
            column = 2 if side == "left" else 4
            for index in indices:
                np.testing.assert_array_equal(
                    bound["base_weights"][index],
                    [0.0, 0.0, 1.0, 0.0, 0.0] if column == 2
                    else [0.0, 0.0, 0.0, 0.0, 1.0],
                )
        posed = binding.pose(rest, bound, _angles())
        self.assertEqual(posed["vertices"], rest["vertices"])
        self.assertEqual(posed["quads"], rest["quads"])
        self.assertEqual(posed["base_stencils"], rest["base_stencils"])

    def test_feet_follow_existing_hierarchical_hip_and_knee_without_ankle_joint(self) -> None:
        bound, (base, rest, _prior_root, _prior_binding, _legs) = _foot_bound()
        angles = _angles(left_hip=25.0, left_knee=30.0)
        posed = binding.pose(rest, bound, angles)
        points = binding.joint_points(bound, angles)
        left_index = base["metadata"]["feet"]["left"]["new_vertex_indices"][0]
        right_index = base["metadata"]["feet"]["right"]["new_vertex_indices"][0]
        knee_skin = np.asarray(points["left"]["knee"]["skin_matrix"])
        expected = (knee_skin @ np.r_[rest["vertices"][left_index], 1.0])[:3]
        np.testing.assert_allclose(posed["vertices"][left_index], expected)
        self.assertFalse(np.array_equal(posed["vertices"][left_index],
                                        rest["vertices"][left_index]))
        np.testing.assert_array_equal(posed["vertices"][right_index],
                                      rest["vertices"][right_index])
        self.assertNotIn("ankle", bound["joint_order"])

    def test_feet_partition_and_full_l2_stencil_transfer_preserve_existing_l0_weights(self) -> None:
        baseline, _baseline_values = _bound()
        bound, (base, rest, _prior_root, _prior_binding, _legs) = _foot_bound()
        baseline_count = len(baseline["base_weights"])
        np.testing.assert_array_equal(
            np.asarray(bound["base_weights"][:baseline_count]),
            np.asarray(baseline["base_weights"]),
        )
        base_weights = np.asarray(bound["base_weights"])
        evaluated = np.asarray(bound["evaluated_weights"])
        np.testing.assert_array_equal(base_weights.sum(axis=1), np.ones(len(base_weights)))
        np.testing.assert_allclose(evaluated.sum(axis=1), np.ones(len(evaluated)))
        mixed_index = base["metadata"]["feet"]["left"]["new_vertex_indices"][1]
        expected = (0.25 * np.asarray(bound["base_weights"][0]) +
                    0.75 * np.asarray(bound["base_weights"][mixed_index]))
        np.testing.assert_allclose(bound["evaluated_weights"][mixed_index], expected)
        self.assertEqual(len(rest["base_stencils"]), len(rest["vertices"]))

    def test_hostile_foot_metadata_is_rejected(self) -> None:
        base, rest, prior_root, prior_binding, legs = _foot_fixture()
        feet = base["metadata"]["feet"]
        hostile = {
            "duplicate_within_side": lambda value: value["left"]["new_vertex_indices"].__setitem__(
                1, value["left"]["new_vertex_indices"][0]),
            "overlap_between_sides": lambda value: value["right"]["new_vertex_indices"].__setitem__(
                0, value["left"]["new_vertex_indices"][0]),
            "root_vertex_overwrite": lambda value: value["left"]["new_vertex_indices"].__setitem__(0, 0),
            "leg_vertex_overwrite": lambda value: value["left"]["new_vertex_indices"].__setitem__(
                0, base["metadata"]["chains"]["left"]["sections"][0]["indices"][0]),
            "non_integer_id": lambda value: value["left"]["new_vertex_indices"].__setitem__(0, True),
            "incomplete_coverage": lambda value: value["right"]["new_vertex_indices"].pop(),
            "out_of_range_id": lambda value: value["right"]["new_vertex_indices"].__setitem__(
                0, len(base["vertices"])),
        }
        for name, mutate in hostile.items():
            with self.subTest(name=name):
                candidate = copy.deepcopy(base)
                mutate(candidate["metadata"]["feet"])
                with self.assertRaises(ValueError):
                    binding.bind(candidate, rest, prior_root, prior_binding, legs)

    def test_tail_transition_uses_declared_host_support_and_distal_pelvis(self) -> None:
        bound, (base, rest, _prior_root, _prior_binding, _legs) = _tail_bound()
        tail = base["metadata"]["tail"]
        self.assertEqual(bound["tail_vertex_indices"], tail["new_vertex_indices"])
        self.assertNotIn("tail", bound["joint_order"])
        weights = np.asarray(bound["base_weights"], dtype=float)
        self.assertTrue(np.allclose(weights.sum(axis=1), 1.0, atol=1.0e-12))
        for index in tail["ring_indices"][-1]:
            np.testing.assert_array_equal(weights[index], [1.0, 0.0, 0.0, 0.0, 0.0])
        host = tail["source_host_identity"]["vertex_indices"]
        expected_support = sum(
            coefficient * weights[index]
            for index, coefficient in zip(host, [0.55, 0.15, 0.15, 0.15])
        )
        collar = tail["ring_indices"][0][0]
        expected_collar = 0.5 * expected_support + 0.5 * np.asarray(
            [1.0, 0.0, 0.0, 0.0, 0.0]
        )
        np.testing.assert_allclose(weights[collar], expected_collar, atol=1.0e-12)
        evaluated = np.asarray(bound["evaluated_weights"], dtype=float)
        np.testing.assert_allclose(evaluated, weights, atol=1.0e-12)
        self.assertEqual(len(rest["base_stencils"]), len(rest["vertices"]))

    def test_tail_requires_explicit_collar_blend_strength(self) -> None:
        values = _tail_fixture()
        del values[0]["metadata"]["tail"]["transition_weights"]["collar_blend_strength"]
        with self.assertRaisesRegex(ValueError, "collar_blend_strength"):
            binding.bind(*values)

    def test_tail_uniform_centroid_support_is_rejected(self) -> None:
        values = _tail_fixture()
        support = values[0]["metadata"]["tail"]["transition_weights"]["supports"]["264"]
        support["convex_weights"] = [0.25, 0.25, 0.25, 0.25]
        with self.assertRaisesRegex(ValueError, "inset-corner rule"):
            binding.bind(*values)

    def test_tail_host_correspondence_is_explicit_and_hostile_mapping_is_rejected(self) -> None:
        mutations = {
            "wrong_kept_target": lambda candidate: candidate["metadata"]["index_mapping"]
            ["root_face_mappings_excluding_tail_host"].__setitem__(0, [0, 1]),
            "wrong_replacement_host": lambda candidate: candidate["metadata"]["tail"]
            ["face_replacement"].__setitem__("original_face_index", 3),
            "original_host_retained": lambda candidate: candidate["metadata"]["tail"]
            ["face_replacement"].__setitem__("original_host_retained", True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                values = list(_tail_fixture())
                mutate(values[0])
                with self.assertRaises(ValueError):
                    binding.bind(*values)

    def test_harmonic_root_graph_uses_supplied_original_faces(self) -> None:
        base, _rest, prior_root, _prior_binding, _legs = _fixture()
        base["metadata"]["root"]["face_count"] = 1
        modified_prefix = copy.deepcopy(base["quads"])
        modified_prefix[0] = [0, 1, 2, 4]
        graph, _metadata = binding._root_edge_graph(
            base, modified_prefix, {}, prior_root["quads"][:1],
        )
        self.assertIn(3, graph[0])
        self.assertNotIn(4, graph[0])


class ArmBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _actual_arm_cases()

    def test_actual_root_graph_has_semantic_free_and_seed_regions(self):
        for case_id, _root, arm_mesh, _rest, _prior, bound in self.cases:
            with self.subTest(case=case_id):
                influence = bound["metadata"]["arm_root_influence"]
                self.assertGreater(influence["thigh_neighbourhood_count"], 0)
                for side in ("left", "right"):
                    row = influence["per_side"][side]
                    self.assertEqual(row["D0_count"], 8)
                    self.assertEqual(row["D1_count"], 8)
                    self.assertEqual(row["free_count"], 16)
                    self.assertEqual(row["seed_count"], 10)
                    self.assertEqual(row["collar_anchor_value"], 1.0)
                    self.assertEqual(row["D2_anchor_value"], 0.0)
                    self.assertEqual(len(influence["connections"][side]), 8)
                    self.assertEqual(set(row["D0"]), set(arm_mesh["metadata"]["arms"][side]["source_port"]["indices"]))
                self.assertEqual(influence["bilateral_shared_D2"], [])

    def test_root_arm_field_preserves_old_ratios_and_is_nine_column(self):
        for case_id, _root, _arm_mesh, _rest, prior_binding, bound in self.cases:
            with self.subTest(case=case_id):
                self.assertEqual(bound["joint_order"], [
                    "pelvis", "left_hip", "left_knee", "right_hip", "right_knee",
                    "left_shoulder", "left_elbow", "right_shoulder", "right_elbow",
                ])
                self.assertEqual(bound["weight_columns"], [
                    "pelvis", "left_thigh", "left_shank", "right_thigh", "right_shank",
                    "left_upper_arm", "left_forearm", "right_upper_arm", "right_forearm",
                ])
                prior = np.asarray(prior_binding["base_weights"], dtype=float)
                actual = np.asarray(bound["base_weights"], dtype=float)
                influence = bound["metadata"]["arm_root_influence"]
                for side, upper_column in (("left", 5), ("right", 7)):
                    free = influence["fields"][side]
                    for index, value in free.items():
                        old = np.asarray([
                            prior[index, 0], prior[index, 1], 0.0,
                            prior[index, 2], 0.0,
                        ])
                        np.testing.assert_allclose(actual[index, :5], old * (1.0 - value), atol=1.0e-12)
                        self.assertAlmostEqual(actual[index, upper_column], value, places=12)
                        self.assertEqual(actual[index, 6 if side == "left" else 8], 0.0)
                non_arm = set(range(ROOT_COUNT)) - set(influence["fields"]["left"]) - set(influence["fields"]["right"])
                for index in non_arm:
                    np.testing.assert_array_equal(actual[index, 5:], np.zeros(4))
                np.testing.assert_allclose(actual.sum(axis=1), np.ones(len(actual)))

    def test_arm_appendage_blend_anchors_and_free_elbow_are_semantic(self):
        for case_id, _root, arm_mesh, _rest, _prior, bound in self.cases:
            with self.subTest(case=case_id):
                for side in ("left", "right"):
                    row = arm_mesh["metadata"]["arms"][side]
                    blends = {int(index): value for index, value in bound["arm_elbow_blend"][side].items()}
                    sections = {section["name"]: section["indices"] for section in row["sections"]}
                    for index in row["collar"]["indices"] + sections["upper_belly"] + sections["pre_elbow"]:
                        self.assertEqual(blends[index], 0.0)
                    for index in sections["post_elbow"] + sections["forearm_belly"] + sections["pre_wrist"] + sections["wrist"] + sections["palm"] + sections["knuckle"] + sections["terminal"] + [row["cap"]["vertex"]]:
                        self.assertEqual(blends[index], 1.0)
                    for index in sections["elbow"]:
                        self.assertGreater(blends[index], 0.0)
                        self.assertLess(blends[index], 1.0)
                    self.assertEqual(bound["metadata"]["arm_weighting"]["elbow"],
                                     "free arm-appendage harmonic blend")

    def test_source_bone_pivot_frames_and_zero_pose_identity(self):
        for case_id, _root, arm_mesh, rest, _prior, bound in self.cases:
            with self.subTest(case=case_id):
                posed = binding.pose(rest, bound, _arm_angles())
                self.assertEqual(posed["vertices"], rest["vertices"])
                self.assertEqual(posed["quads"], rest["quads"])
                self.assertEqual(posed["base_stencils"], rest["base_stencils"])
                for side in ("left", "right"):
                    source = arm_mesh["metadata"]["arms"][side]
                    frames = bound["rest_frames"][side]
                    shoulder = binding._arm_frame(source["J"], source["E"], f"{side} test shoulder")
                    elbow = binding._arm_frame(source["E"], source["W"], f"{side} test elbow")
                    np.testing.assert_array_equal(
                        frames["shoulder"]["rest_global"], shoulder["rest_global"])
                    np.testing.assert_array_equal(
                        frames["elbow"]["rest_global"], elbow["rest_global"])
                    self.assertEqual(
                        frames["arm_source_points"]["frame_source"],
                        "source J->E and E->W bones; not construction P->E/E->W sections",
                    )
                    self.assertEqual(
                        frames["arm_source_points"]["pose_rotation_order"],
                        "shoulder Rz(side_sign*shoulder_raise) @ Rx(-shoulder_forward); elbow Rx(-elbow)",
                    )

    def test_arm_frame_accepts_near_horizontal_bones_and_rejects_vertical_projection(self):
        for distal in ([1.0, -1.0e-12, 0.0], [-1.0, -1.0e-12, 0.0]):
            frame = binding._arm_frame([0.0, 0.0, 0.0], distal, "near-horizontal")
            rotation = np.asarray(frame["rotation"])
            np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1.0e-10)
            self.assertGreater(np.linalg.det(rotation), 0.0)
            self.assertGreaterEqual(rotation[2, 2], 0.0)
        with self.assertRaisesRegex(ValueError, "global \+Y projection"):
            binding._arm_frame([0.0, 0.0, 0.0], [0.0, -1.0, 0.0], "vertical")

    def test_unilateral_and_bilateral_modest_arm_poses_have_independent_endpoint_checks(self):
        for case_id, _root, _arm_mesh, rest, _prior, bound in self.cases:
            with self.subTest(case=case_id):
                unilateral = _arm_angles(left_raise=15.0, left_forward=10.0,
                                         left_elbow=25.0)
                points = binding.joint_points(bound, unilateral)
                for side in ("left", "right"):
                    side_points = points[side]
                    shoulder_skin = np.asarray(side_points["shoulder"]["skin_matrix"])
                    elbow_skin = np.asarray(side_points["elbow"]["skin_matrix"])
                    J = np.r_[side_points["rest_arm_J"], 1.0]
                    E = np.r_[side_points["rest_arm_E"], 1.0]
                    W = np.r_[side_points["rest_arm_W"], 1.0]
                    np.testing.assert_allclose(side_points["posed_arm_J"], (shoulder_skin @ J)[:3], atol=1.0e-10)
                    np.testing.assert_allclose(side_points["posed_arm_E"], (shoulder_skin @ E)[:3], atol=1.0e-10)
                    np.testing.assert_allclose(side_points["posed_arm_E"], (elbow_skin @ E)[:3], atol=1.0e-10)
                    np.testing.assert_allclose(side_points["posed_arm_W"], (elbow_skin @ W)[:3], atol=1.0e-10)
                self.assertFalse(np.allclose(points["left"]["posed_arm_W"], points["left"]["rest_arm_W"]))
                np.testing.assert_allclose(points["right"]["posed_arm_J"], points["right"]["rest_arm_J"], atol=1.0e-10)

                rest_points = binding.joint_points(bound, _arm_angles())
                raise_points = binding.joint_points(
                    bound, _arm_angles(left_raise=15.0, right_raise=15.0))
                forward_points = binding.joint_points(
                    bound, _arm_angles(left_forward=10.0, right_forward=10.0))
                elbow_points = binding.joint_points(
                    bound, _arm_angles(left_elbow=25.0, right_elbow=25.0))
                for side in ("left", "right"):
                    self.assertGreater(raise_points[side]["posed_arm_E"][1],
                                       rest_points[side]["rest_arm_E"][1])
                    self.assertGreater(forward_points[side]["posed_arm_E"][2],
                                       rest_points[side]["rest_arm_E"][2])
                    self.assertGreater(elbow_points[side]["posed_arm_W"][2],
                                       rest_points[side]["rest_arm_W"][2])
                bilateral = _arm_angles(left_raise=15.0, left_forward=10.0,
                                         left_elbow=25.0, right_raise=15.0,
                                         right_forward=10.0, right_elbow=25.0)
                mirrored = binding.joint_points(bound, bilateral)
                for name in ("posed_arm_J", "posed_arm_E", "posed_arm_W"):
                    left = np.asarray(mirrored["left"][name])
                    right = np.asarray(mirrored["right"][name])
                    np.testing.assert_allclose(left, [-right[0], right[1], right[2]], atol=1.0e-10)


class HeadBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _actual_head_cases()
        cls.arm_head_cases = _actual_head_cases(with_arms=True)

    def test_source_owned_neck_pivot_is_not_the_neck_upper_port(self):
        for case_id, _root, source, head_mesh, _rest, _prior, bound in self.cases:
            with self.subTest(case=case_id):
                metadata = head_mesh["metadata"]["head"]
                handoff = metadata["binding_handoff"]
                expected = [source["components"][f"stations.neck_collar.C.{axis}"]
                            for axis in "xyz"]
                upper = [source["components"][f"stations.neck_upper.C.{axis}"]
                         for axis in "xyz"]
                self.assertEqual(handoff["pivot_source"], "stations.neck_collar.C")
                self.assertEqual(bound["rest_frames"]["head"]["J"], expected)
                self.assertEqual(bound["rest_frames"]["head"]["pivot_source"],
                                 "stations.neck_collar.C")
                self.assertNotEqual(expected, upper)
                self.assertEqual(bound["metadata"]["head_weighting"]["neck_upper_port_is_pivot"],
                                 False)

    def test_head_six_column_partition_stencils_and_preserved_root_ratios(self):
        for case_id, _root, _source, head_mesh, rest, prior_binding, bound in self.cases:
            with self.subTest(case=case_id):
                self.assertEqual(bound["joint_order"], [
                    "pelvis", "left_hip", "left_knee", "right_hip", "right_knee", "neck",
                ])
                self.assertEqual(bound["weight_columns"], [
                    "pelvis", "left_thigh", "left_shank", "right_thigh", "right_shank", "neck",
                ])
                base_weights = np.asarray(bound["base_weights"], dtype=float)
                evaluated = np.asarray(bound["evaluated_weights"], dtype=float)
                np.testing.assert_allclose(base_weights.sum(axis=1), 1.0, atol=1.0e-12)
                np.testing.assert_allclose(evaluated.sum(axis=1), 1.0, atol=1.0e-12)
                self.assertEqual(len(evaluated), len(rest["vertices"]))
                self.assertEqual(len(rest["base_stencils"]), len(rest["vertices"]))
                head_indices = set(bound["head_vertex_indices"])
                neck_index = bound["weight_columns"].index("neck")
                for index in head_indices:
                    expected = np.zeros(6)
                    expected[neck_index] = 1.0
                    np.testing.assert_array_equal(base_weights[index], expected)

                prior = np.asarray(prior_binding["base_weights"], dtype=float)
                old = np.column_stack((prior[:, 0], prior[:, 1], np.zeros(152),
                                       prior[:, 2], np.zeros(152)))
                influence = bound["head_root_influence"]
                modified = set(influence["per_root"]["D0"]) | set(influence["per_root"]["D1"])
                for index in range(152):
                    if index in modified:
                        h = influence["field"][str(index)] if str(index) in influence["field"] else influence["field"][index]
                        np.testing.assert_allclose(base_weights[index, :5], old[index] * (1.0 - h), atol=1.0e-12)
                        self.assertAlmostEqual(base_weights[index, 5], h, places=12)
                    else:
                        np.testing.assert_array_equal(base_weights[index], np.r_[old[index], 0.0])

    def test_head_identity_yaw_nod_endpoint_directions_and_hierarchy(self):
        for case_id, _root, _source, _head_mesh, rest, _prior, bound in self.cases:
            with self.subTest(case=case_id):
                identity = binding.pose(rest, bound, _head_angles())
                self.assertEqual(identity["vertices"], rest["vertices"])
                self.assertEqual(identity["quads"], rest["quads"])
                self.assertEqual(identity["base_stencils"], rest["base_stencils"])
                self.assertEqual(bound["parents"]["neck"], "pelvis")
                self.assertIn("neck", bound["joints"])

                yaw = binding.joint_points(bound, _head_angles(yaw=10.0))["head"]
                self.assertGreater(yaw["posed_forward_direction"][0], 0.0)
                self.assertAlmostEqual(yaw["posed_forward_direction"][1], 0.0, places=12)
                nod = binding.joint_points(bound, _head_angles(nod=10.0))["head"]
                self.assertLess(nod["posed_forward_direction"][1], 0.0)
                self.assertAlmostEqual(nod["posed_forward_direction"][0], 0.0, places=12)
                self.assertEqual(yaw["pose_rotation_order"], "Ry(yaw) @ Rx(nod)")

    def test_head_transition_reports_no_shoulder_overlap_and_preserves_arm_layout(self):
        for case_id, _root, _source, head_mesh, rest, _prior, bound in self.arm_head_cases:
            with self.subTest(case=case_id):
                self.assertEqual(len(bound["joint_order"]), 10)
                self.assertEqual(bound["joint_order"][-1], "neck")
                self.assertEqual(bound["weight_columns"][-1], "neck")
                self.assertEqual(bound["head_root_influence"]["per_root"]["shoulder_overlap"], [])
                evaluated = np.asarray(bound["evaluated_weights"], dtype=float)
                self.assertEqual(len(evaluated), len(rest["vertices"]))
                np.testing.assert_allclose(evaluated.sum(axis=1), 1.0, atol=1.0e-12)
                neck_column = bound["weight_columns"].index("neck")
                for index in bound["head_vertex_indices"]:
                    # L2 boundary stencils may blend the connected root seam;
                    # the semantic L0 appendage allocation is the one-hot
                    # contract, while L2 must preserve complete partitioning.
                    self.assertEqual(bound["base_weights"][index][neck_column], 1.0)
                self.assertEqual(head_mesh["metadata"]["head"]["binding_handoff"]["joint"],
                                 "neck_head")

    def test_neck_handoff_rejects_missing_or_wrong_source_pivot(self):
        case_id, root, _source, head_mesh, rest, prior, _bound = self.cases[0]
        leg_inputs = next(row["leg_inputs"] for row in INPUTS["cases"]
                          if row["id"] == case_id)
        for replacement in (None, "stations.neck_upper.C"):
            candidate = copy.deepcopy(head_mesh)
            if replacement is None:
                del candidate["metadata"]["head"]["binding_handoff"]["pivot_source"]
            else:
                candidate["metadata"]["head"]["binding_handoff"]["pivot_source"] = replacement
            with self.assertRaises(ValueError):
                binding.bind(candidate, rest, root, prior, leg_inputs)


if __name__ == "__main__":
    unittest.main()

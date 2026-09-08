"""Focused tests for the explicit host-58 connected-tail adapter."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import construction  # noqa: E402
import tail_construction  # noqa: E402


INPUTS = json.loads((HERE / "inputs.json").read_text(encoding="utf-8"))
TAIL_INPUTS = json.loads((HERE / "tail-inputs.json").read_text(encoding="utf-8"))
TAIL_CASES = {row["case_id"]: row for row in TAIL_INPUTS["cases"]}
CASE_IDS = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")
HOST_FACE = 58
HOST_VERTICES = [41, 44, 66, 63]


def _actual_cases():
    result = []
    for row in INPUTS["cases"]:
        if row["id"] not in CASE_IDS:
            continue
        root = json.loads(Path(row["root_mesh"]["path"]).read_text(encoding="utf-8"))
        base = construction.build(root, row["leg_inputs"])
        controls = TAIL_CASES[row["id"]]
        output = tail_construction.build(base, controls)
        result.append((row["id"], base, output, controls))
    if tuple(row[0] for row in result) != CASE_IDS:
        raise AssertionError("canonical tail cases were not loaded")
    return result


class TailConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _actual_cases()

    def test_disabled_human_feature_returns_source_mesh_exactly(self):
        case_id, base, output, controls = self.cases[0]
        self.assertEqual(case_id, "calibrated_ordinary_human")
        self.assertFalse(controls["enabled"])
        self.assertEqual(output, base)
        self.assertNotIn("tail", output["metadata"])

    def test_pinned_host_is_derived_from_source_mesh_and_slot_is_replaced(self):
        case_id, base, output, _controls = self.cases[1]
        self.assertEqual(case_id, "calibrated_upright_anthropomorphic")
        tail = output["metadata"]["tail"]
        host = tail["host"]
        self.assertEqual(host["face_index"], HOST_FACE)
        self.assertEqual(host["original_quad"], HOST_VERTICES)
        self.assertEqual(host["owner"], "domain.pelvis")
        self.assertEqual(base["quads"][HOST_FACE], HOST_VERTICES)
        self.assertEqual(base["face_owners"][HOST_FACE], "domain.pelvis")
        np.testing.assert_array_equal(host["coordinates"],
                                      [base["vertices"][index] for index in HOST_VERTICES])
        self.assertEqual(output["quads"][HOST_FACE],
                         output["quads"][tail["annulus_face_indices"][0]])
        self.assertNotIn(HOST_VERTICES, output["quads"])
        points = np.asarray(host["coordinates"], dtype=float)
        raw_normal = np.cross(points[1] - points[0], points[2] - points[0])
        raw_normal += np.cross(points[2] - points[0], points[3] - points[0])
        expected_normal = raw_normal / np.linalg.norm(raw_normal)
        np.testing.assert_allclose(host["normal"], expected_normal, atol=1.0e-12)

    def test_non_host_faces_vertices_and_face_indices_remain_stable(self):
        _case_id, base, output, _controls = self.cases[1]
        base_face_count = len(base["quads"])
        tail = output["metadata"]["tail"]
        self.assertEqual(len(output["vertices"]), len(base["vertices"]) + 20)
        self.assertEqual(len(output["quads"]), base_face_count + 20)
        self.assertEqual(tail["annulus_face_indices"],
                         [HOST_FACE, base_face_count, base_face_count + 1,
                          base_face_count + 2])
        self.assertEqual(tail["tail_face_indices"],
                         list(range(base_face_count + 3, base_face_count + 19)))
        self.assertEqual(tail["cap_face_index"], base_face_count + 19)
        self.assertEqual(tail["new_face_indices"],
                         [HOST_FACE] + list(range(base_face_count, base_face_count + 20)))
        self.assertEqual(output["vertices"][:len(base["vertices"])], base["vertices"])
        self.assertEqual(output["control_owners"][:len(base["control_owners"])],
                         base["control_owners"])
        self.assertEqual(output["base_stencils"][:len(base["base_stencils"])],
                         base["base_stencils"])
        for index, face in enumerate(base["quads"]):
            if index != HOST_FACE:
                self.assertEqual(output["quads"][index], face)
                self.assertEqual(output["face_owners"][index], base["face_owners"][index])
        self.assertEqual(output["loops"], base["loops"])
        self.assertEqual(tail["face_replacement"]["original_host_retained"], False)
        self.assertEqual(tail["face_replacement"]["one_to_many"],
                         [[HOST_FACE, *tail["annulus_face_indices"]]])

    def test_inset_collar_source_phase_frames_and_cubic_stations_are_explicit(self):
        _case_id, base, output, controls = self.cases[1]
        tail = output["metadata"]["tail"]
        host = tail["host"]
        points = np.asarray(host["coordinates"], dtype=float)
        centre = np.mean(points, axis=0)
        inset = np.asarray(host["inset_corners"], dtype=float)
        np.testing.assert_allclose(inset, centre + 0.4 * (points - centre), atol=1.0e-12)
        collar = np.asarray(host["collar_vertices"], dtype=float)
        np.testing.assert_allclose(
            collar,
            inset + float(controls["collar_distance"]) * np.asarray(host["normal"]),
            atol=1.0e-12,
        )
        self.assertEqual(len(tail["host"]["source_phase"]), 4)
        self.assertEqual(len({tuple(phase) for phase in tail["host"]["source_phase"]}), 4)
        self.assertEqual(len(tail["ring_indices"]), 5)
        self.assertEqual(tail["station_fractions"], controls["station_fractions"])
        centreline = tail["centreline"]
        self.assertEqual(centreline["kind"], "cubic_bezier")
        self.assertEqual(len(centreline["control_points"]), 4)
        self.assertEqual(tail["ring_indices"][0], tail["new_vertex_indices"][:4])
        self.assertEqual(output["frames"], base["frames"])
        self.assertNotIn("tail", output["frames"])
        self.assertEqual(tail["host_normal"], host["normal"])
        self.assertEqual(tail["source_phase"], host["source_phase"])
        self.assertEqual(
            tail["frame_rule"],
            "project global +X onto each cubic tangent plane; V=X cross tangent",
        )
        for frame in tail["ring_frames"]:
            tangent = np.asarray(frame["tangent"], dtype=float)
            x_axis = np.asarray(frame["X"], dtype=float)
            v_axis = np.asarray(frame["V"], dtype=float)
            np.testing.assert_allclose(np.linalg.norm(tangent), 1.0, atol=1.0e-12)
            np.testing.assert_allclose(np.linalg.norm(x_axis), 1.0, atol=1.0e-12)
            np.testing.assert_allclose(np.linalg.norm(v_axis), 1.0, atol=1.0e-12)
            self.assertAlmostEqual(float(np.dot(x_axis, tangent)), 0.0, places=12)
            self.assertGreater(float(np.dot(np.cross(x_axis, tangent), v_axis)), 1.0 - 1.0e-12)
        expected_direction = np.asarray([0.0, -0.25, -1.0])
        expected_direction /= np.linalg.norm(expected_direction)
        np.testing.assert_allclose(tail["centreline"]["terminal_direction"],
                                   expected_direction, atol=1.0e-12)

    def test_connected_cap_and_binding_supports_match_inset_corner_derivation(self):
        _case_id, base, output, _controls = self.cases[1]
        tail = output["metadata"]["tail"]
        self.assertEqual(len(tail["tail_face_indices"]), 16)
        self.assertEqual(len(output["quads"][tail["cap_face_index"]]), 4)
        self.assertEqual(tail["transition_weights"]["status"],
                         "binding_declared_no_tail_joint")
        self.assertEqual(tail["transition_weights"]["collar_blend_strength"], 0.5)
        supports = tail["transition_weights"]["supports"]
        self.assertEqual(set(map(int, supports)), set(tail["new_vertex_indices"]))
        host_points = np.asarray([base["vertices"][index] for index in HOST_VERTICES],
                                 dtype=float)
        inset = np.asarray(tail["host"]["inset_corners"], dtype=float)
        for offset, index in enumerate(tail["new_vertex_indices"]):
            corner = offset % 4
            row = supports[str(index)]
            self.assertEqual(row["host_vertex_indices"], HOST_VERTICES)
            self.assertEqual(row["host_corner"], corner)
            self.assertEqual(row["source_phase"], tail["source_phase"][corner])
            self.assertEqual(row["convex_weights"],
                             [0.55 if slot == corner else 0.15 for slot in range(4)])
            np.testing.assert_allclose(
                np.asarray(row["convex_weights"]) @ host_points,
                inset[corner],
                atol=1.0e-12,
            )
            self.assertEqual(row["target_joint"], "pelvis")
            self.assertIn("q=.4*P_i+.6*C", row["support_rule"])
        self.assertEqual(output["metadata"]["base_control_owners"][:len(base["vertices"])],
                         base["metadata"]["base_control_owners"])

    def test_host_identity_and_candidate_controls_reject_drift(self):
        _case_id, base, _output, controls = self.cases[1]
        hostile = copy.deepcopy(controls)
        hostile["host_identity"]["vertex_indices"] = [41, 44, 63, 66]
        with self.assertRaises(tail_construction.TailConstructionError):
            tail_construction.build(base, hostile)
        hostile = copy.deepcopy(controls)
        hostile["host_identity"]["owner"] = "domain.root"
        with self.assertRaises(tail_construction.TailConstructionError):
            tail_construction.build(base, hostile)
        hostile = copy.deepcopy(controls)
        hostile["station_fractions"] = [0.0, 0.25, 0.25, 0.75, 1.0]
        with self.assertRaises(tail_construction.TailConstructionError):
            tail_construction.build(base, hostile)


if __name__ == "__main__":
    unittest.main()

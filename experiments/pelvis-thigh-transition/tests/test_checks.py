from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import checks


class CheckerTests(unittest.TestCase):
    def test_canonical_thigh_exits_selected_amid_five_ports(self):
        parsed = {"loops": {
            "port.neck": (0, 1, 2),
            "port.left_arm": (3, 4, 5),
            "port.right_arm": (6, 7, 8),
            "port.left_thigh": (9, 10, 11),
            "port.right_thigh": (12, 13, 14),
        }}
        self.assertEqual(checks._exit_loop_names({}, parsed),
                         ["port.left_thigh", "port.right_thigh"])
        del parsed["loops"]["port.right_thigh"]
        self.assertEqual(checks._exit_loop_names({}, parsed), [])

    def test_real_generic_intersection_module_loads_on_small_triangles(self):
        vertices = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                    (3.0, 0.0, 0.0), (4.0, 0.0, 0.0), (3.0, 1.0, 0.0),
                    (6.0, 0.0, 0.0), (7.0, 0.0, 0.0), (6.0, 1.0, 0.0),
                    (100.0, 100.0, 100.0))
        triangles = ((0, 1, 2), (3, 4, 5), (6, 7, 8))
        with patch.dict(sys.modules):
            sys.modules.pop("owned_root_generic_mesh_correctness", None)
            result = checks._intersection_report(vertices, triangles, (0, 1, 2), ("pelvis",) * 3)
            self.assertTrue(result["available"], result)
            self.assertIn("owned_root_generic_mesh_correctness", sys.modules)
        self.assertTrue(result["pair_policy_complete"], result)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["hit_pairs"], [])
        self.assertEqual(len(result["calls"]), 3)
        self.assertEqual(result["unreferenced_vertex_count"], 1)

    def test_ray_intersection_returns_positive_distance(self):
        vertices = ((2.0, -1.0, -1.0), (2.0, 1.0, -1.0), (2.0, 0.0, 1.0))
        distance = checks._ray_triangle((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), vertices, (0, 1, 2))
        self.assertEqual(distance, 2.0)
        self.assertEqual(checks._deduplicate_hits((2.0, 2.0 + 5.0e-7, 3.0), 1.0e-6), [2.0, 3.0])

    def test_directed_open_exit_loop_uses_negated_newell_normal_for_outward(self):
        case = self._case_with_direction((0.0, 0.0, -1.0))
        parsed = self._exit_parsed(wrong_plane=False)
        result = checks._exit_checks(case, parsed, checks._source_dimensions(case))
        self.assertAlmostEqual(result["loops"]["left_exit"]["outward_dot_direction"], 1.0)
        for value, expected in zip(result["loops"]["left_exit"]["plane_normal"], (0.0, 0.0, 1.0)):
            self.assertAlmostEqual(value, expected)
        for value, expected in zip(result["loops"]["left_exit"]["outward_normal"], (0.0, 0.0, -1.0)):
            self.assertAlmostEqual(value, expected)

    def test_invalid_mesh_is_a_json_diagnostic_not_an_exception(self):
        bad_mesh = {
            "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            "quads": ((0, 1, 2, 99),),
            "face_owners": ("pelvis",),
            "control_owners": ("pelvis", "pelvis", "pelvis"),
            "loops": {"only": (0, 1, 2)},
            "base_stencils": (),
            "frames": {},
        }
        report = checks.check_case(self._case(), [bad_mesh, bad_mesh, bad_mesh])
        json.dumps(report, allow_nan=False)
        self.assertFalse(report["technical"]["pass"])
        self.assertFalse(report["render"]["safe"])
        self.assertTrue(any(row["code"] == "invalid_mesh"
                            for row in report["technical"]["levels"][0]["errors"]))

    def test_lower_quad_triangle_normal_orientation_is_a_gate(self):
        parsed = {
            "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                         (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)),
            "quads": ((0, 1, 2, 3),),
            "face_owners": ("pelvis",),
        }
        result = checks._lower_quad_normal_checks(parsed)
        self.assertFalse(result["pass"])
        self.assertEqual(result["failure_count"], 1)
        self.assertLess(result["failures"][0]["normal_dot"], 0.0)

    def test_boundary_declaration_requires_five_loops(self):
        mesh = {
            "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
                         (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)),
            "quads": ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                      (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)),
            "face_owners": ("pelvis",) * 6,
            "control_owners": ("pelvis",) * 8,
            "loops": {"one": (0, 1, 2, 3)},
            "base_stencils": (),
            "frames": {},
        }
        level_report, _ = checks._mesh_structural_checks(0, mesh, None)
        self.assertFalse(level_report["pass"])
        self.assertTrue(any(row["code"] == "invalid_mesh" for row in level_report["errors"]))

    def test_negative_clearance_keeps_finite_mesh_renderable_but_fails_admission(self):
        mesh = self._small_mesh()
        case = self._case()
        case["attachments"]["left"]["centre"] = [-0.2, -1.0, 0.0]
        case["attachments"]["right"]["centre"] = [0.2, -1.0, 0.0]
        case["components"]["hips.left.r_x"] = 0.35
        case["components"]["hips.right.r_x"] = 0.35
        case["admission_failures"] = ["nominal_medial_clearance"]
        report = checks.check_case(case, [mesh, mesh, mesh])
        self.assertFalse(report["technical"]["pass"])
        self.assertTrue(report["render"]["safe"])
        self.assertFalse(report["admission"]["pass"])
        self.assertTrue(report["admission"]["failures"])

    def test_tilt_response_uses_actual_exit_plane_not_correct_frame_metadata(self):
        base_case = self._case_with_direction((0.0, 0.0, -1.0))
        case = dict(base_case)
        case["id"] = "neutral_left_direction_tilt_5deg"
        case["provenance"] = {"expected_change": {"direction": "left thigh direction tilts"}}
        base_levels = [self._exit_mesh(False)] * 3
        new_levels = [self._exit_mesh(True)] * 3
        result = checks.compare_perturbation(base_case, base_levels, case, new_levels)
        self.assertIn("direction_tilt_response", result["checks"], result)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["direction_tilt_response"]["pass"])

    def test_asymmetric_response_requires_actual_L2_radius_increase(self):
        base_case = self._case_with_direction((0.0, 0.0, -1.0))
        case = copy.deepcopy(base_case)
        case["id"] = "neutral_left_asymmetric_xz_and_radius"
        case["declared_response"] = "left asymmetric translation and radius"
        case["components"]["hips.left.r_x"] *= 1.05
        delta = (0.04, 0.0, 0.05)
        for key in ("centre", "knee"):
            case["attachments"]["left"][key] = checks._vec_add(case["attachments"]["left"][key], delta)
        base_mesh = self._exit_mesh(False)
        for factor, expected_pass in ((1.0, False), (1.05, True), (1.10, False)):
            with self.subTest(actual_radius_factor=factor):
                new_mesh = copy.deepcopy(base_mesh)
                new_mesh["vertices"] = tuple(
                    (x * factor + delta[0], y, z + delta[2]) if index < 4 else (x, y, z)
                    for index, (x, y, z) in enumerate(base_mesh["vertices"]))
                # L0/L1 and metadata cannot substitute for measured L2 response.
                with patch.object(checks, "check_case", side_effect=AssertionError("full check rerun")):
                    result = checks.compare_perturbation(
                        base_case, [base_mesh] * 3, case, [base_mesh, base_mesh, new_mesh])
                self.assertTrue(result["checks"]["exit_centroid_response"]["pass"], result)
                self.assertEqual(result["checks"]["asymmetric_lateral_span_response"]["pass"], expected_pass, result)
                self.assertEqual(result["pass"], expected_pass, result)
                json.dumps(result, allow_nan=False)

    def test_containment_rays_start_at_source_H_despite_wrong_output_H(self):
        case = self._case_with_direction((0.0, 0.0, -1.0))
        parsed = self._exit_parsed(False)
        for record in parsed["frames"].values():
            record["H"] = (100.0, 200.0, 300.0)
        info = checks._source_dimensions(case)
        with patch.object(checks, "_ray_triangle", return_value=None) as ray:
            result = checks._containment_checks(case, parsed, info)
        for side in ("left", "right"):
            self.assertEqual(result["rays"][side + ":summary"]["H"], info["H_by_side"][side])
            self.assertTrue(any(call.args[0] == info["H_by_side"][side] for call in ray.call_args_list))
        self.assertFalse(any(call.args[0] == (100.0, 200.0, 300.0) for call in ray.call_args_list))

    def test_truncated_upper_hits_fail_closed_for_lower_collision_inventory(self):
        diagnostic = Mock(return_value={"pair_policy_complete": True,
                                       "intersection_hit_count": 65,
                                       "hit_pairs": [(0, 1)], "hit_pairs_truncated": True})
        module = SimpleNamespace(intersection_diagnostics=diagnostic)
        spec = SimpleNamespace(name="owned_root_generic_mesh_correctness",
                               loader=SimpleNamespace(exec_module=lambda module: None))
        parsed = self._exit_parsed(False)
        parsed["face_owners"] = ["upper_arm"] * len(parsed["quads"])
        with patch.dict(sys.modules), \
                patch.object(checks.importlib.util, "spec_from_file_location", return_value=spec), \
                patch.object(checks.importlib.util, "module_from_spec", return_value=module):
            result = checks._level_intersection_and_geometry(2, parsed, checks._source_dimensions(self._case()))
        inventory = result["intersections"]
        self.assertEqual(diagnostic.call_count, 3)
        self.assertFalse(inventory["collision_inventory_complete"])
        self.assertFalse(inventory["pass"])
        self.assertFalse(result["nonadjacent_lower_intersections"]["pass"])
        self.assertEqual(inventory["lower_hit_pairs"], [])
        self.assertTrue(any(row["code"] == "incomplete_collision_inventory" for row in inventory["errors"]))

    @staticmethod
    def _case():
        return {
            "id": "synthetic",
            "attachments": {
                "left": {"centre": [-1.0, 0.0, 0.0], "knee": [-1.0, -1.0, 0.0]},
                "right": {"centre": [1.0, 0.0, 0.0], "knee": [1.0, -1.0, 0.0]},
            },
            "components": {
                "stations.lower_pelvis.rL": 1.0,
                "hips.left.r_x": 0.3, "hips.left.r_y": 0.3, "hips.left.r_z": 0.3,
                "hips.right.r_x": 0.3, "hips.right.r_y": 0.3, "hips.right.r_z": 0.3,
            },
        }

    @classmethod
    def _case_with_direction(cls, direction):
        case = cls._case()
        case["attachments"] = {
            "left": {"centre": [-1.0, 0.0, 0.0], "knee": [-1.0, 0.0, direction[2]]},
            "right": {"centre": [1.0, 0.0, 0.0], "knee": [1.0, 0.0, direction[2]]},
        }
        return case

    @staticmethod
    def _exit_parsed(wrong_plane):
        mesh = CheckerTests._exit_mesh(wrong_plane)
        level_report, parsed = checks._mesh_structural_checks(2, mesh, None)
        if parsed is None:
            raise AssertionError(level_report)
        return parsed

    @staticmethod
    def _exit_mesh(wrong_plane):
        left = ((-0.3, -0.3, -0.45), (0.3, -0.3, -0.45),
                (0.3, 0.3, -0.45), (-0.3, 0.3, -0.45))
        if wrong_plane:
            right = ((-0.3, -0.3, 0.0), (0.3, -0.3, 0.0),
                     (0.3, -0.3, 0.6), (-0.3, -0.3, 0.6))
        else:
            right = tuple((x + 2.0, y, z) for x, y, z in left)
        extras = (
            ((-0.2, -0.2, 0.2), (0.2, -0.2, 0.2), (0.2, 0.2, 0.2), (-0.2, 0.2, 0.2)),
            ((1.8, -0.2, 0.2), (2.2, -0.2, 0.2), (2.2, 0.2, 0.2), (1.8, 0.2, 0.2)),
            ((3.8, -0.2, 0.2), (4.2, -0.2, 0.2), (4.2, 0.2, 0.2), (3.8, 0.2, 0.2)),
        )
        vertices = left + right + tuple(point for group in extras for point in group)
        loops = {"left_exit": (0, 1, 2, 3), "right_exit": (4, 5, 6, 7),
                 "socket": (8, 9, 10, 11), "upper": (12, 13, 14, 15),
                 "lower": (16, 17, 18, 19)}
        quads = tuple(loops.values())
        frames = {
            "left": {"H": (0.0, 0.0, 0.0), "knee": (0.0, 0.0, -1.0), "length": 1.0,
                     "d": (0.0, 0.0, -1.0), "X": (1.0, 0.0, 0.0), "U": (0.0, 0.0, 1.0),
                     "F": (0.0, -1.0, 0.0), "exit": (0.0, 0.0, -0.45)},
            "right": {"H": (0.0, 0.0, 0.0), "knee": (0.0, 0.0, -1.0), "length": 1.0,
                      "d": (0.0, 0.0, -1.0), "X": (1.0, 0.0, 0.0), "U": (0.0, 0.0, 1.0),
                      "F": (0.0, -1.0, 0.0), "exit": (0.0, 0.0, -0.45)},
        }
        return {"vertices": vertices, "quads": quads, "face_owners": ("pelvis",) * 5,
                "control_owners": ("pelvis",) * 20, "loops": loops,
                "base_stencils": tuple(((index, 1.0),) for index in range(20)),
                "frames": frames}

    @staticmethod
    def _small_mesh():
        vertices = tuple(point for index in range(8)
                         for point in ((float(index), 0.0, 0.10 * index),
                                       (float(index), 1.0, 0.10 * index + 0.2)))
        quads = tuple((2 * index, 2 * index + 1, 2 * index + 3, 2 * index + 2)
                      for index in range(7))
        return {
            "vertices": vertices,
            "quads": quads,
            "face_owners": ("pelvis",) * len(quads),
            "control_owners": ("pelvis",) * len(vertices),
            "loops": {"a": (0, 1, 2), "b": (3, 4, 5), "c": (6, 7, 8),
                      "d": (9, 10, 11), "e": (12, 13, 14)},
            "base_stencils": tuple(((index, 1.0),) for index in range(len(vertices))),
            "frames": {},
        }


if __name__ == "__main__":
    unittest.main()

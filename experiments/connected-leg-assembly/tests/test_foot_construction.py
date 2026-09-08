"""Bounded tests for the connected coarse foot prerequisite."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

import construction  # noqa: E402
import foot_construction  # noqa: E402


INPUTS_PATH = EXPERIMENT_DIR / "inputs.json"
FOOT_INPUTS_PATH = EXPERIMENT_DIR / "foot-inputs.json"
EXPECTED_CASES = (
    "calibrated_ordinary_human",
    "calibrated_upright_anthropomorphic",
)
RETAINED_PORTS = {"port.neck", "port.left_arm", "port.right_arm"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_cases() -> list[tuple[str, dict, dict, dict, dict]]:
    document = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    foot_document = json.loads(FOOT_INPUTS_PATH.read_text(encoding="utf-8"))
    foot_rows = {row["case_id"]: row["sides"] for row in foot_document["cases"]}
    result = []
    for case in document["cases"]:
        case_id = case["id"]
        if case_id not in EXPECTED_CASES:
            continue
        root_ref = case["root_mesh"]
        root_path = Path(root_ref["path"])
        if _sha256(root_path) != root_ref["sha256"]:
            raise AssertionError(f"immutable root identity drifted: {root_path}")
        root = json.loads(root_path.read_text(encoding="utf-8"))
        leg_inputs = case["leg_inputs"]
        base = construction.build(root, leg_inputs)
        result.append((case_id, base, leg_inputs, foot_rows[case_id], root))
    if tuple(row[0] for row in result) != EXPECTED_CASES:
        raise AssertionError("the two canonical connected-leg cases were not loaded")
    return result


def _edge_uses(quads):
    uses = {}
    for face_index, face in enumerate(quads):
        for index, left in enumerate(face):
            right = face[(index + 1) % 4]
            edge = tuple(sorted((left, right)))
            uses.setdefault(edge, []).append((face_index, left, right))
    return uses


class FootConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _actual_cases()
        cls.outputs = []
        for case_id, base, leg_inputs, foot_inputs, _root in cls.cases:
            output = foot_construction.build(base, leg_inputs, foot_inputs)
            levels = foot_construction.evaluate(output, levels=2)
            cls.outputs.append((case_id, base, leg_inputs, foot_inputs, output, levels))

    def test_longitudinal_candidate_runs_both_actual_cases_and_evaluates(self):
        self.assertEqual(len(self.outputs), 2)
        for case_id, base, _leg_inputs, _foot_inputs, output, levels in self.outputs:
            with self.subTest(case=case_id):
                self.assertEqual(len(base["vertices"]), 264)
                self.assertEqual(len(base["quads"]), 248)
                self.assertEqual(len(output["vertices"]), 438)
                self.assertEqual(len(output["quads"]), 428)
                self.assertEqual([level["metadata"]["level"] for level in levels], [0, 1, 2])
                for parent, child in zip(levels, levels[1:]):
                    edge_count = len(_edge_uses(parent["quads"]))
                    self.assertEqual(len(child["vertices"]),
                                     len(parent["vertices"]) + edge_count + len(parent["quads"]))
                self.assertEqual(set(output["loops"]), RETAINED_PORTS)
                self.assertEqual(set(levels[2]["loops"]), RETAINED_PORTS)

    def test_closed_feet_are_manifold_wound_and_connected(self):
        for case_id, _base, _leg_inputs, _foot_inputs, output, _levels in self.outputs:
            with self.subTest(case=case_id):
                uses = _edge_uses(output["quads"])
                self.assertTrue(all(len(rows) in (1, 2) for rows in uses.values()))
                boundary = {edge for edge, rows in uses.items() if len(rows) == 1}
                declared = set()
                for loop in output["loops"].values():
                    for index, left in enumerate(loop):
                        declared.add(tuple(sorted((left, loop[(index + 1) % len(loop)]))))
                self.assertEqual(boundary, declared)
                self.assertTrue(all(len(rows) == 2 for edge, rows in uses.items()
                                    if any(index >= 264 for index in edge)))
                self.assertNotIn("port.left_ankle", output["loops"])
                self.assertNotIn("port.right_ankle", output["loops"])
                for side in ("left", "right"):
                    foot = output["metadata"]["feet"][side]
                    self.assertEqual(len(foot["new_vertex_indices"]), 87)
                    self.assertEqual(len(foot["new_face_indices"]), 90)
                    self.assertEqual(foot["winding"]["output_orientation"], 1)

    def test_source_anchors_and_longitudinal_grid_have_meaningful_positions(self):
        for case_id, _base, leg_inputs, foot_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    controls = foot_inputs[side]
                    x = leg_inputs[side]["A"][0]
                    anchors = foot["source_anchors"]
                    for name in ("H", "B", "T"):
                        self.assertEqual(anchors[name], [x, controls[name]["plantar_y"], controls[name]["z"]])
                    rows = foot["longitudinal_rows"]
                    self.assertEqual([row["name"] for row in rows], list(
                        foot_construction._LONGITUDINAL_ROW_NAMES
                    ))
                    self.assertEqual([row["z_formula"] for row in rows], list(
                        foot_construction._LONGITUDINAL_ROW_FORMULAS
                    ))
                    self.assertEqual([row["source_role"] for row in rows], list(
                        foot_construction._LONGITUDINAL_ROW_ROLES
                    ))
                    self.assertEqual(foot["lateral_fractions"], list(
                        foot_construction._LATERAL_FRACTIONS
                    ))
                    dorsal = foot["grid_indices"]["dorsal"]
                    plantar = foot["grid_indices"]["plantar"]
                    self.assertEqual(len(dorsal), 8)
                    self.assertEqual(len(plantar), 8)
                    self.assertIsNone(dorsal[2][2])
                    self.assertEqual(len(foot["ring_indices_by_name"]["dorsal_grid"]), 39)
                    self.assertEqual(len(foot["ring_indices_by_name"]["plantar_grid"]), 40)
                    self.assertEqual(len(foot["attachment_loop"]["hole"]), 8)
                    self.assertEqual(foot["attachment_loop"]["hole"],
                                     foot["ring_indices_by_name"]["ankle_hole"])
                    self.assertEqual(foot["attachment_loop"]["ankle"],
                                     foot["ankle_source_loop"])
                    self.assertEqual(
                        foot["correspondence"]["target_order"],
                        list(foot_construction._HOLE_BOUNDARY_NAMES),
                    )
                    self.assertGreater(foot["correspondence"]["score"],
                                       foot["correspondence"]["runner_up_score"])

    def test_longitudinal_rows_follow_declared_source_profiles(self):
        def source_dorsal(z, controls):
            H, B, T = (controls[name] for name in ("H", "B", "T"))
            if z <= B["z"]:
                left, right = H, B
            else:
                left, right = B, T
            fraction = (z - left["z"]) / (right["z"] - left["z"])
            left_y = left["plantar_y"] + left["dorsalthickness"]
            right_y = right["plantar_y"] + right["dorsalthickness"]
            return left_y + fraction * (right_y - left_y)

        def source_plantar(z, controls):
            H, B, T = (controls[name] for name in ("H", "B", "T"))
            if z <= B["z"]:
                left, right = H, B
            else:
                left, right = B, T
            fraction = (z - left["z"]) / (right["z"] - left["z"])
            return left["plantar_y"] + fraction * (right["plantar_y"] - left["plantar_y"])

        for case_id, _base, _leg_inputs, foot_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    controls = foot_inputs[side]
                    A = _leg_inputs[side]["A"]
                    rows = foot["longitudinal_rows"]
                    expected_z = [
                        controls["H"]["z"],
                        0.5 * (controls["H"]["z"] + A[2]),
                        A[2],
                        A[2] + 0.25 * (controls["B"]["z"] - A[2]),
                        A[2] + 0.625 * (controls["B"]["z"] - A[2]),
                        controls["B"]["z"],
                        0.5 * (controls["B"]["z"] + controls["T"]["z"]),
                        controls["T"]["z"],
                    ]
                    for row, z in zip(rows, expected_z):
                        self.assertAlmostEqual(row["z"], z)
                        if z <= controls["B"]["z"]:
                            u = (z - controls["H"]["z"]) / (controls["B"]["z"] - controls["H"]["z"])
                            expected_width = controls["H"]["halfwidth"] + u * u * (
                                controls["B"]["halfwidth"] - controls["H"]["halfwidth"]
                            )
                        else:
                            u = (z - controls["B"]["z"]) / (controls["T"]["z"] - controls["B"]["z"])
                            expected_width = controls["B"]["halfwidth"] + u * (
                                controls["T"]["halfwidth"] - controls["B"]["halfwidth"]
                            )
                        self.assertAlmostEqual(row["halfwidth"], expected_width)

                    for row_index, row_indices in enumerate(foot["grid_indices"]["dorsal"]):
                        for column, index in enumerate(row_indices):
                            if index is None:
                                continue
                            top = output["vertices"][index]
                            bottom = output["vertices"][foot["grid_indices"]["plantar"][row_index][column]]
                            self.assertAlmostEqual(top[1], source_dorsal(rows[row_index]["z"], controls))
                            self.assertAlmostEqual(bottom[1], source_plantar(rows[row_index]["z"], controls))
                            self.assertAlmostEqual(top[0], bottom[0])
                            self.assertAlmostEqual(top[2], bottom[2])

    def test_dorsal_hole_and_grid_face_ranges_are_conforming(self):
        for case_id, _base, _leg_inputs, _foot_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    self.assertEqual(len(foot["attachment_loop"]["hole"]), 8)
                    self.assertEqual(
                        foot["ring_order"],
                        ["dorsal_grid", "plantar_grid", "ankle_hole", "collar"],
                    )
                    ranges = foot["face_owner_ranges"]
                    self.assertEqual(len(ranges["dorsal_grid"]), 24)
                    self.assertEqual(len(ranges["plantar_grid"]), 28)
                    self.assertEqual(len(ranges["outer_perimeter"]), 22)
                    self.assertEqual(len(ranges["ankle_to_collar"]), 8)
                    self.assertEqual(len(ranges["collar_to_hole"]), 8)

    def test_source_profiles_reject_out_of_range_z(self):
        _case_id, _base, _leg_inputs, foot_inputs, _output, _levels = self.outputs[0]
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction._source_profile(
                foot_inputs["left"]["H"]["z"] - 1.0,
                foot_inputs["left"],
                "dorsal_y",
                "left",
            )
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction._source_profile(
                foot_inputs["left"]["T"]["z"] + 1.0,
                foot_inputs["left"],
                "plantar_y",
                "left",
            )

    def test_old_prefix_and_three_ports_are_preserved_exactly(self):
        for _case_id, base, _leg_inputs, _foot_inputs, output, _levels in self.outputs:
            self.assertEqual(output["vertices"][:264], base["vertices"])
            self.assertEqual(output["quads"][:248], base["quads"])
            self.assertEqual(output["face_owners"][:248], base["face_owners"])
            self.assertEqual(output["control_owners"][:264], base["control_owners"])
            for name in RETAINED_PORTS:
                self.assertEqual(output["loops"][name], base["loops"][name])
            self.assertNotIn("weights", output)
            self.assertNotIn("base_weights", output)

    def test_phase_resolution_does_not_assume_a0_is_d0(self):
        _case_id, base, leg_inputs, foot_inputs, _output, _levels = self.outputs[0]
        shifted = copy.deepcopy(base)
        side = "left"
        original = list(shifted["loops"]["port.left_ankle"])
        shifted_loop = original[3:] + original[:3]
        shifted["loops"]["port.left_ankle"] = shifted_loop
        shifted["metadata"]["chains"][side]["ankle_port"] = list(shifted_loop)
        for section in shifted["metadata"]["chains"][side]["sections"]:
            if section["name"] == "ankle":
                section["indices"] = list(shifted_loop)
        output = foot_construction.build(shifted, leg_inputs, foot_inputs)
        correspondence = output["metadata"]["feet"][side]["correspondence"]
        self.assertEqual(correspondence["target_to_ankle_indices"][0], original[0])
        self.assertNotEqual(shifted_loop[0], correspondence["target_to_ankle_indices"][0])

    def test_reversed_attached_loop_resolves_reverse_output_winding(self):
        _case_id, base, leg_inputs, foot_inputs, _output, _levels = self.outputs[0]
        reversed_base = copy.deepcopy(base)
        side = "right"
        original = list(reversed_base["loops"]["port.right_ankle"])
        reversed_loop = list(reversed(original))
        reversed_base["loops"]["port.right_ankle"] = reversed_loop
        reversed_base["metadata"]["chains"][side]["ankle_port"] = list(reversed_loop)
        for section in reversed_base["metadata"]["chains"][side]["sections"]:
            if section["name"] == "ankle":
                section["indices"] = list(reversed_loop)
        output = foot_construction.build(reversed_base, leg_inputs, foot_inputs)
        foot = output["metadata"]["feet"][side]
        self.assertEqual(foot["correspondence"]["direction"], -1)
        self.assertEqual(foot["winding"]["attached_ankle_loop"], -1)
        self.assertEqual(foot["winding"]["output_orientation"], 1)
        self.assertEqual(set(output["loops"]), RETAINED_PORTS)

    def test_invalid_foot_relationships_and_schema_fail_closed(self):
        _case_id, base, leg_inputs, foot_inputs, _output, _levels = self.outputs[0]
        bad = copy.deepcopy(foot_inputs)
        bad["left"]["B"]["z"] = leg_inputs["left"]["A"][2]
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction.build(base, leg_inputs, bad)

        bad = copy.deepcopy(foot_inputs)
        bad["right"]["B"]["halfwidth"] = 0.001
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction.build(base, leg_inputs, bad)

        bad = copy.deepcopy(foot_inputs)
        bad["left"]["unsupported"] = True
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction.build(base, leg_inputs, bad)

        bad_leg_inputs = copy.deepcopy(leg_inputs)
        bad_leg_inputs["left"]["unexpected"] = 1.0
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction.build(base, bad_leg_inputs, foot_inputs)

    def test_nonfinite_and_degenerate_foot_geometry_fail_closed(self):
        _case_id, base, leg_inputs, foot_inputs, _output, _levels = self.outputs[0]
        bad = copy.deepcopy(foot_inputs)
        bad["left"]["T"]["dorsalthickness"] = float("nan")
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction.build(base, leg_inputs, bad)

        bad = copy.deepcopy(foot_inputs)
        bad["right"]["T"]["z"] = bad["right"]["B"]["z"]
        with self.assertRaises(foot_construction.FootConstructionError):
            foot_construction.build(base, leg_inputs, bad)

    def test_frozen_core_catches_second_triangle_only_hit(self):
        vertices = [
            (0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 2.0, 0.0),
            (0.0, 2.0, 0.0), (0.2, 1.2, -1.0), (0.2, 1.5, 1.0),
            (0.8, 1.2, 0.0), (10.0, 10.0, 10.0),
        ]
        quads = [(0, 1, 2, 3), (4, 5, 6, 7)]
        with self.assertRaisesRegex(
                foot_construction.FootConstructionError,
                r"triangle hit \(1, 2\) maps to quad faces \(0, 1\)"):
            foot_construction._validate_intersections(vertices, quads, 1, [1], "left")

    def test_frozen_core_catches_one_shared_vertex_hit(self):
        vertices = [
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
            (10.0, 10.0, 10.0), (1.0, 1.0, 0.0), (0.0, 0.0, 1.0),
            (10.0, -10.0, 10.0),
        ]
        quads = [(0, 1, 2, 3), (0, 4, 5, 6)]
        with self.assertRaisesRegex(
                foot_construction.FootConstructionError,
                r"triangle hit \(0, 2\) maps to quad faces \(0, 1\)"):
            foot_construction._validate_intersections(vertices, quads, 1, [1], "left")

    def test_l2_stencils_remain_finite_and_partitioned(self):
        for case_id, _base, _leg_inputs, _foot_inputs, _output, levels in self.outputs:
            for level in levels:
                with self.subTest(case=case_id, level=level["metadata"]["level"]):
                    self.assertEqual(len(level["base_stencils"]), len(level["vertices"]))
                    for stencil in level["base_stencils"]:
                        total = sum(float(term[1]) for term in stencil)
                        self.assertTrue(math.isfinite(total))
                        self.assertAlmostEqual(total, 1.0, places=9)
                        self.assertTrue(all(term[0] >= 0 and term[1] >= -1.0e-10
                                            for term in stencil))


if __name__ == "__main__":
    unittest.main()

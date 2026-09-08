"""Focused FOOT-004 source/form candidate tests.

These tests are execution-owned by Raman.  They deliberately use only the
two canonical synthetic/calibrated experiment cases and the frozen generic
connected-leg evaluator; no body construction or pose is included.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

import construction  # noqa: E402
import foot_form_construction  # noqa: E402


INPUTS_PATH = EXPERIMENT_DIR / "inputs.json"
FORM_INPUTS_PATH = EXPERIMENT_DIR / "foot-form-inputs.json"
EXPECTED_CASES = (
    "calibrated_ordinary_human",
    "calibrated_upright_anthropomorphic",
)
RETAINED_PORTS = {"port.neck", "port.left_arm", "port.right_arm"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_cases() -> list[tuple[str, dict, dict, dict]]:
    document = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    form_document = json.loads(FORM_INPUTS_PATH.read_text(encoding="utf-8"))
    form_rows = {row["case_id"]: row for row in form_document["cases"]}
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
        if case_id not in form_rows:
            raise AssertionError(f"FOOT-004 inputs lack case {case_id}")
        base = construction.build(root, leg_inputs)
        result.append((case_id, base, leg_inputs, form_rows[case_id]))
    if tuple(row[0] for row in result) != EXPECTED_CASES:
        raise AssertionError("the two canonical connected-leg cases were not loaded")
    return result


def _edge_uses(quads):
    uses = {}
    for face_index, face in enumerate(quads):
        for index, left in enumerate(face):
            right = face[(index + 1) % len(face)]
            edge = tuple(sorted((left, right)))
            uses.setdefault(edge, []).append((face_index, left, right))
    return uses


class SourceFrameTests(unittest.TestCase):
    def test_source_frame_uses_attachment_x_not_leg_summary_x(self):
        """A mocked terminal frame may differ from the construction summary."""
        attachment_x = (0.6, 0.0, 0.8)
        source = foot_form_construction._source_frame(
            {"frames": {"left": {"X": [1.0, 0.0, 0.0]}}},
            "left",
            {"X": attachment_x},
        )
        self.assertEqual(source["X"], attachment_x)
        self.assertAlmostEqual(source["U"][1], 1.0)
        self.assertAlmostEqual(source["F"][2], 0.6)


class FootFormConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _actual_cases()
        cls.outputs = []
        for case_id, base, leg_inputs, form_inputs in cls.cases:
            output = foot_form_construction.build(base, leg_inputs, form_inputs)
            levels = foot_form_construction.evaluate(output, levels=2)
            cls.outputs.append((case_id, base, leg_inputs, form_inputs, output, levels))

    def test_candidate_preserves_prefix_counts_ports_and_evaluation(self):
        self.assertEqual(len(self.outputs), 2)
        for case_id, base, _leg_inputs, _form_inputs, output, levels in self.outputs:
            with self.subTest(case=case_id):
                self.assertEqual((len(base["vertices"]), len(base["quads"])), (264, 248))
                self.assertEqual((len(output["vertices"]), len(output["quads"])), (438, 428))
                self.assertEqual([level["metadata"]["level"] for level in levels], [0, 1, 2])
                self.assertEqual(set(output["loops"]), RETAINED_PORTS)
                self.assertEqual(set(levels[2]["loops"]), RETAINED_PORTS)
                self.assertEqual(output["vertices"][:264], base["vertices"])
                self.assertEqual(output["quads"][:248], base["quads"])

    def test_reused_grid_is_closed_and_metadata_is_explicit(self):
        for case_id, _base, _leg_inputs, _form_inputs, output, _levels in self.outputs:
            with self.subTest(case=case_id):
                uses = _edge_uses(output["quads"])
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
                    ranges = foot["face_owner_ranges"]
                    self.assertEqual(len(ranges["dorsal_grid"]), 24)
                    self.assertEqual(len(ranges["plantar_grid"]), 28)
                    self.assertEqual(len(ranges["outer_perimeter"]), 22)
                    self.assertEqual(len(ranges["ankle_to_collar"]), 8)
                    self.assertEqual(len(ranges["collar_to_hole"]), 8)

    def test_source_form_rows_frames_and_radii_are_lineaged(self):
        for case_id, _base, _leg_inputs, form_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    source_form = foot["source_form"]
                    self.assertEqual(source_form["case_id"], case_id)
                    self.assertEqual(source_form["local_controls"], form_inputs["sides"][side])
                    self.assertEqual(source_form["construction"], form_inputs["construction"])
                    self.assertEqual(source_form["reference_y_usage"],
                                     "contact-plane measurement only; no floor projection")
                    self.assertEqual(
                        [row["name"] for row in foot["longitudinal_rows"]],
                        list(foot_form_construction._ROW_NAMES),
                    )
                    self.assertEqual(
                        [row["formula"] for row in foot["longitudinal_rows"]],
                        list(foot_form_construction._ROW_FORMULAS),
                    )
                    self.assertEqual(foot["lateral_fractions"],
                                     list(foot_form_construction._LATERAL_FRACTIONS))
                    self.assertIsNone(foot["grid_indices"]["dorsal"][2][2])
                    self.assertEqual(len(foot["attachment_loop"]["ankle"]), 8)
                    self.assertEqual(foot["attachment_loop"]["ankle"],
                                     foot["ankle_source_loop"])
                    self.assertEqual(len(foot["attachment_loop"]["hole"]), 8)
                    self.assertEqual(
                        foot["correspondence"]["target_order"],
                        list(foot_form_construction._HOLE_BOUNDARY_NAMES),
                    )
                    self.assertEqual(set(foot["frames"]["source"]), {"X", "U", "F"})
                    self.assertIn("R is ankle-body surface centre and is not a joint",
                                  source_form["joint_rule"])

    def test_rounding_uses_distinct_local_normal_top_and_bottom(self):
        for case_id, _base, _leg_inputs, form_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    controls = form_inputs["sides"][side]
                    rows = foot["longitudinal_rows"]
                    for row_index, row in enumerate(rows):
                        top_index = foot["grid_indices"]["dorsal"][row_index][2]
                        bottom_index = foot["grid_indices"]["plantar"][row_index][2]
                        self.assertIsNotNone(top_index)
                        top = output["vertices"][top_index]
                        bottom = output["vertices"][bottom_index]
                        centre = row["centre"]
                        normal = row["normal"]
                        expected_top = [centre[axis] + row["rD"] * normal[axis]
                                        for axis in range(3)]
                        expected_bottom = [centre[axis] - row["rP"] * normal[axis]
                                           for axis in range(3)]
                        for actual, expected in zip(top, expected_top):
                            self.assertAlmostEqual(actual, expected)
                        for actual, expected in zip(bottom, expected_bottom):
                            self.assertAlmostEqual(actual, expected)
                        if row_index in (0, 2, 5, 6, 7):
                            name = ("H", "R", "M", "B", "T")[(0, 1, 5, 6, 7).index(row_index)]
                            self.assertEqual(row["rL"], controls[name]["rL"])
                            self.assertEqual(row["rD"], controls[name]["rD"])
                            self.assertEqual(row["rP"], controls[name]["rP"])

    def test_rejects_schema_frame_and_source_degeneracy(self):
        _case_id, base, leg_inputs, form_inputs, _output, _levels = self.outputs[0]
        bad = copy.deepcopy(form_inputs)
        bad["sides"]["left"]["M"]["local_z"] = bad["sides"]["left"]["R"]["local_z"]
        with self.assertRaises(foot_form_construction.FootFormConstructionError):
            foot_form_construction.build(base, leg_inputs, bad)

        bad = copy.deepcopy(form_inputs)
        bad["sides"]["right"]["B"]["rD"] = 0.0
        with self.assertRaises(foot_form_construction.FootFormConstructionError):
            foot_form_construction.build(base, leg_inputs, bad)

        bad = copy.deepcopy(form_inputs)
        bad["construction"]["cross_section_rounding"] = 1.0
        with self.assertRaises(foot_form_construction.FootFormConstructionError):
            foot_form_construction.build(base, leg_inputs, bad)

        bad = copy.deepcopy(form_inputs)
        bad["sides"]["left"]["unexpected"] = True
        with self.assertRaises(foot_form_construction.FootFormConstructionError):
            foot_form_construction.build(base, leg_inputs, bad)


if __name__ == "__main__":
    unittest.main()

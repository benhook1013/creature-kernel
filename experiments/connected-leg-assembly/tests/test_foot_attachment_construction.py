"""Focused FOOT-005 attachment-only tests.

Raman owns execution.  These tests are intentionally written before the
capture and must not be run as part of this implementation handoff.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

import construction  # noqa: E402
import foot_attachment_construction  # noqa: E402
import foot_form_construction  # noqa: E402


INPUTS_PATH = EXPERIMENT_DIR / "inputs.json"
FORM_INPUTS_PATH = EXPERIMENT_DIR / "foot-form-inputs.json"
ATTACHMENT_INPUTS_PATH = EXPERIMENT_DIR / "foot-attachment-inputs.json"
EXPECTED_CASES = (
    "calibrated_ordinary_human",
    "calibrated_upright_anthropomorphic",
)
RETAINED_PORTS = {"port.neck", "port.left_arm", "port.right_arm"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cases():
    document = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    form_document = json.loads(FORM_INPUTS_PATH.read_text(encoding="utf-8"))
    attachment_inputs = json.loads(ATTACHMENT_INPUTS_PATH.read_text(encoding="utf-8"))
    forms = {row["case_id"]: row for row in form_document["cases"]}
    rows = []
    for case in document["cases"]:
        if case["id"] not in EXPECTED_CASES:
            continue
        root_path = Path(case["root_mesh"]["path"])
        if _sha256(root_path) != case["root_mesh"]["sha256"]:
            raise AssertionError(f"immutable root identity drifted: {root_path}")
        rows.append((
            case["id"],
            construction.build(json.loads(root_path.read_text(encoding="utf-8")),
                               case["leg_inputs"]),
            case["leg_inputs"],
            forms[case["id"]],
        ))
    if tuple(row[0] for row in rows) != EXPECTED_CASES:
        raise AssertionError("the two canonical connected-leg cases were not loaded")
    return rows, attachment_inputs


class ConnectorSeamTests(unittest.TestCase):
    def test_default_builder_seam_preserves_old_collar_formula(self):
        base_vertices = [(float(index), 0.0, 0.0) for index in range(8)]
        hole_points = [(float(index), 10.0, 0.0) for index in range(8)]
        appended = []

        def append_vertex(point):
            appended.append(tuple(point))
            return 8 + len(appended) - 1

        result = foot_form_construction._default_connector_builder({
            "append_vertex": append_vertex,
            "semantic_ankle": list(range(8)),
            "hole_points": hole_points,
            "hole_indices": list(range(16, 24)),
            "orientation": 1,
            "base_vertices": base_vertices,
            "form": {"construction": {"collar_fraction": 0.20}},
        })
        self.assertIsNone(inspect.signature(foot_form_construction.build)
                          .parameters["connector_builder"].default)
        self.assertEqual(result["ring_order"], ["collar"])
        self.assertEqual(result["band_order"], ["ankle_to_collar", "collar_to_hole"])
        self.assertEqual(appended[0], (0.0, 2.0, 0.0))
        self.assertEqual(appended[-1], (7.0, 2.0, 0.0))

    def test_explicit_default_callback_matches_implicit_foot004_for_human(self):
        cases, _attachment_inputs = _cases()
        case_id, base, leg_inputs, form_inputs = cases[0]
        self.assertEqual(case_id, "calibrated_ordinary_human")
        implicit = foot_form_construction.build(base, leg_inputs, form_inputs)
        explicit = foot_form_construction.build(
            base, leg_inputs, form_inputs,
            connector_builder=foot_form_construction._default_connector_builder,
        )
        self.assertEqual(explicit, implicit)


class FootAttachmentConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.attachment_inputs = _cases()
        cls.outputs = []
        for case_id, base, leg_inputs, form_inputs in cls.cases:
            output = foot_attachment_construction.build(
                base, leg_inputs, form_inputs, cls.attachment_inputs
            )
            levels = foot_attachment_construction.evaluate(output, levels=2)
            cls.outputs.append((case_id, base, leg_inputs, form_inputs, output, levels))

    def test_counts_prefix_ports_and_evaluation(self):
        self.assertEqual(len(self.outputs), 2)
        for case_id, base, _leg_inputs, _form_inputs, output, levels in self.outputs:
            with self.subTest(case=case_id):
                self.assertEqual((len(base["vertices"]), len(base["quads"])), (264, 248))
                self.assertEqual((len(output["vertices"]), len(output["quads"])), (454, 428))
                self.assertEqual([level["metadata"]["level"] for level in levels], [0, 1, 2])
                self.assertEqual(set(output["loops"]), RETAINED_PORTS)
                self.assertEqual(output["vertices"][:264], base["vertices"])
                self.assertEqual(output["quads"][:248], base["quads"])

    def test_two_support_rings_replace_old_collar(self):
        for case_id, _base, _leg_inputs, _form_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    self.assertNotIn("collar", foot["attachment_loop"])
                    self.assertEqual(foot["ring_order"][-2:], ["support_s0", "support_s1"])
                    self.assertEqual(set(foot["attachment_loop"]) -
                                     {"ankle", "hole", "support_s0", "support_s1"}, set())
                    for name in ("ankle_to_s0", "s0_to_s1", "s1_to_hole"):
                        self.assertEqual(len(foot["face_owner_ranges"][name]), 8)
                    self.assertNotIn("ankle_to_collar", foot["face_owner_ranges"])
                    self.assertNotIn("collar_to_hole", foot["face_owner_ranges"])
                    self.assertEqual(len(foot["new_vertex_indices"]), 95)
                    self.assertEqual(len(foot["new_face_indices"]), 90)

    def test_endpoints_bulk_source_and_explicit_diagnostics_are_preserved(self):
        for case_id, base, _leg_inputs, form_inputs, output, _levels in self.outputs:
            for side in ("left", "right"):
                with self.subTest(case=case_id, side=side):
                    foot = output["metadata"]["feet"][side]
                    self.assertEqual(foot["attachment_loop"]["ankle"],
                                     foot["ankle_source_loop"])
                    self.assertEqual(len(foot["attachment_loop"]["hole"]), 8)
                    self.assertEqual(foot["source_form"]["local_controls"],
                                     form_inputs["sides"][side])
                    candidate = foot["attachment_candidate"]
                    self.assertEqual(len(candidate["diagnostics"]), 8)
                    self.assertIn("chord_dot_d_in", candidate["diagnostics"][0])
                    self.assertIn("chord_dot_c_out", candidate["diagnostics"][0])
                    self.assertIn("boundary_previous_direction", candidate["diagnostics"][0])
                    self.assertIn("boundary_next_direction", candidate["diagnostics"][0])
                    self.assertEqual(candidate["diagnostic_policy"].split(", ")[0],
                                     "chord/conormal/adjacent-direction dots are evidence only")
                    self.assertEqual(output["vertices"][:len(base["vertices"])],
                                     base["vertices"])

    def test_mirrored_cases_keep_shared_lengths_and_support_correspondence(self):
        for case_id, _base, _leg_inputs, _form_inputs, output, _levels in self.outputs:
            left = output["metadata"]["feet"]["left"]["attachment_candidate"]["diagnostics"]
            right = output["metadata"]["feet"]["right"]["attachment_candidate"]["diagnostics"]
            for left_row, right_row in zip(left, right):
                with self.subTest(case=case_id, sector=left_row["sector"]):
                    self.assertAlmostEqual(left_row["chord_length"], right_row["chord_length"])
                    self.assertAlmostEqual(left_row["l0"], right_row["l0"])
                    self.assertAlmostEqual(left_row["l1"], right_row["l1"])
                    self.assertEqual(left_row["name"], right_row["name"])


if __name__ == "__main__":
    unittest.main()

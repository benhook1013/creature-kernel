from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
import inputs  # noqa: E402
import runner  # noqa: E402


class CalibrationInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = inputs.build_document()
        cls.source = json.loads(inputs.FROZEN_OLD_INPUTS.read_text(encoding="utf-8"))
        cls.protocol = json.loads(inputs.PROTOCOL_PATH.read_text(encoding="utf-8"))

    def test_exactly_five_inherited_controls_then_two_protocol_cases(self):
        cases = self.document["cases"]
        self.assertEqual(len(cases), 7)
        self.assertEqual(cases[:5], self.source["cases"][:5])
        self.assertEqual(
            [case["id"] for case in cases],
            [
                "standard_neutral_reference",
                "compact_broad_short_limb_large_head",
                "tall_narrow_long_legged",
                "slender_long_limb",
                "stocky_broad_chested",
                "calibrated_ordinary_human",
                "calibrated_upright_anthropomorphic",
            ],
        )

    def test_protocol_overrides_are_concrete_and_affine_base_is_display_separate(self):
        neutral = self.source["cases"][0]
        for case, declared in zip(self.document["cases"][5:], self.protocol["cases"]):
            self.assertEqual(case["role"], declared["role"])
            self.assertEqual(case["components"]["shoulders.left.arm_origin.x"], -0.16)
            self.assertEqual(case["components"]["shoulders.left.arm_origin.y"], 0.48)
            self.assertAlmostEqual(case["components"]["shoulders.left.shoulder_depth"], 0.056)
            self.assertEqual(case["components"]["stations.lower_pelvis.C.y"], declared["stations"]["lower_pelvis"]["centre"][1])
            self.assertEqual(case["components"]["stations.lower_pelvis.rL"], declared["stations"]["lower_pelvis"]["radii"][0])
            self.assertEqual(case["components"]["hips.left.r_x"], declared["hip_radii"][0])
            self.assertEqual(case["attachments"]["right"]["knee"], declared["attachments"]["right"]["knee"])
            self.assertNotEqual(case["components"], neutral["components"])
        self.assertEqual(self.document["display_normalization"]["scale"], 0.16)
        self.assertEqual(self.document["display_normalization"]["translation"], [0.0, 0.16, 0.0])
        self.assertIn("saved/evaluated meshes remain native", self.document["display_normalization"]["applies_to"])

    def test_reference_landmarks_and_j_are_not_generator_fields(self):
        for case in self.document["cases"][5:]:
            self.assertNotIn("reference_landmarks", case)
            serialized = json.dumps(case, sort_keys=True)
            self.assertNotIn("joint_left", serialized)
            self.assertNotIn("joint_right", serialized)
            self.assertNotIn("\"J\"", serialized)

    def test_change_ledger_has_complete_reason_trace_for_each_change(self):
        allowed_reasons = {inputs.NORMALIZATION_REASON, inputs.ANATOMICAL_REASON}
        protocol_details = {
            reason
            for case in self.protocol["cases"]
            for reason in (case["station_reason"], case["hip_radii_reason"], case["attachment_reason"])
        }
        for case in self.document["cases"][5:]:
            ledger = case["provenance"]["change_ledger"]
            self.assertTrue(ledger)
            for entry in ledger:
                self.assertTrue({"path", "old", "new", "reason", "reason_detail", "protocol_reason_pointer"} <= set(entry))
                self.assertIn(entry["reason"], allowed_reasons)
                self.assertNotEqual(entry["old"], entry["new"])
                if entry["reason"] == inputs.NORMALIZATION_REASON:
                    self.assertEqual(entry["reason_detail"], self.protocol["base_transform"]["reason"])
                    self.assertEqual(entry["protocol_reason_pointer"], "/base_transform/reason")
                else:
                    self.assertIn(entry["reason_detail"], protocol_details)
                    self.assertTrue(entry["protocol_reason_pointer"].startswith("/cases/"))

            paths = {entry["path"] for entry in ledger}
            for key, old in self.source["cases"][0]["components"].items():
                axis = {"x": 0, "y": 1, "z": 2}.get(key.rsplit(".", 1)[-1])
                expected = float(old) * 0.16 + ([0.0, 0.16, 0.0][axis] if axis is not None else 0.0)
                if expected != float(old):
                    self.assertIn(f"/components/{key}", paths)

    def test_prepare_is_deterministic_and_refuses_replacement(self):
        first = inputs.json_bytes(inputs.build_document())
        second = inputs.json_bytes(inputs.build_document())
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "inputs.json"
            inputs.prepare(output)
            self.assertEqual(output.read_bytes(), first)
            with self.assertRaises(inputs.InputError):
                inputs.prepare(output)

    def test_frozen_construction_and_checks_import_without_build(self):
        runner.sys.dont_write_bytecode = True
        old_source = inputs.FROZEN_ROOT / "source/experiments/pelvis-thigh-transition"
        construction = runner._load_module(old_source / "construction.py", "test_frozen_construction_smoke")
        checks = runner._load_module(old_source / "checks.py", "test_frozen_checks_smoke")
        self.assertTrue(callable(construction.build))
        self.assertTrue(callable(construction.evaluate))
        self.assertTrue(callable(checks.check_case))

    @staticmethod
    def _two_tubes():
        vertices = []
        quads = []
        for centre_x in (-0.4, 0.4):
            base = len(vertices)
            for y in (-2.0, 0.0):
                vertices.extend([
                    [centre_x - 0.1, y, -0.1],
                    [centre_x + 0.1, y, -0.1],
                    [centre_x + 0.1, y, 0.1],
                    [centre_x - 0.1, y, 0.1],
                ])
            for offset in range(4):
                next_offset = (offset + 1) % 4
                quads.append([base + offset, base + next_offset, base + 4 + next_offset, base + 4 + offset])
        return vertices, quads

    def test_actual_section_diagnostics_transform_history_and_require_two_loops(self):
        runner.sys.dont_write_bytecode = True
        section = runner._load_module(ROOT / "section_diagnostic.py", "test_captured_section_integration")
        points, faces = self._two_tubes()
        display_points = runner._affine_points(points, 0.16, [0.0, 0.16, 0.0])
        case = {
            "id": "standard_neutral_reference",
            "attachments": {
                "left": {"centre": [-0.4, -1.0, 0.0], "knee": [-0.38, -0.5, 0.0]},
                "right": {"centre": [0.4, -1.0, 0.0], "knee": [0.38, -0.5, 0.0]},
            },
        }
        protocol = {
            "section_samples": 41,
            "section_y_limits": [-0.24, 0.16],
            "joint_to_thigh_segment_samples": [0.0, 0.25, 0.5, 0.75, 1.0],
            "thigh_axis_segment_samples": [0.0, 0.15, 0.3, 0.45],
            "historical_display_transform": {"scale": 0.16, "translation": [0.0, 0.16, 0.0]},
        }
        evidence = runner._diagnostics(section, display_points, faces, case, None, protocol, 0.16)
        first_point = evidence["_raw_point_evidence"][0]
        self.assertEqual(first_point["point"], [-0.064, 0.0, 0.0])
        self.assertNotEqual(first_point["result"]["status"], "OUT_OF_REPRESENTED_RANGE")
        middle = next(row for row in evidence["section_samples"] if abs(row["y"]) < 1.0e-12)
        self.assertTrue(middle["closed"])
        self.assertTrue(middle["usable"])
        self.assertEqual(middle["loop_count"], 2)
        self.assertTrue(evidence["observed_bifurcation_intervals"]["two_loop_ranges"])
        self.assertEqual(evidence["observed_bifurcation_intervals"]["one_to_two_boundary_brackets"], [])

    def test_overlay_set_contains_joint_landmarks_and_both_paths(self):
        case = self.document["cases"][5]
        protocol_case = self.protocol["cases"][0]
        overlays = runner._overlays(case, protocol_case, "native_calibration_frame", self.protocol)
        labels = {item["label"] for item in overlays}
        self.assertIn("J-T left", labels)
        self.assertIn("J-T right", labels)
        self.assertIn("T-K left", labels)
        self.assertIn("T-K right", labels)
        for label in ("J left", "crest left", "ASIS left", "PSIS left", "pubis", "trochanter left"):
            self.assertIn(label, labels)


if __name__ == "__main__":
    unittest.main()

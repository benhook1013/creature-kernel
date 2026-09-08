from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runner  # noqa: E402


IDENTITY = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


class FakeBinding:
    def bind(self, _base, _rest, _case, _refs):
        return {"evaluated_weights": [[1.0, 0.0, 0.0]], "method": "synthetic"}

    def pose(self, rest, _binding, _angles):
        return copy.deepcopy(rest)

    def joint_points(self, _binding, angles):
        def row():
            return {"J": [0.0, 0.0, 0.0], "T": [0.0, -1.0, 0.0],
                    "K": [0.0, -2.0, 0.0], "posed_J": [0.0, 0.0, 0.0],
                    "posed_T": [0.0, -1.0, 0.0], "posed_K": [0.0, -2.0, 0.0],
                    "posed_points": {"J": [0.0, 0.0, 0.0],
                                     "T": [0.0, -1.0, 0.0],
                                     "K": [0.0, -2.0, 0.0]},
                    "posed_matrix": IDENTITY, "skin_matrix": IDENTITY}
        return {"left": row(), "right": row(), "angles": angles}


class FakeChecks:
    def __init__(self, binding_pass=True):
        self.calls = []
        self.binding_calls = []
        self.binding_pass = binding_pass

    def check_binding(self, *args):
        self.binding_calls.append(args)
        return {"schema": "synthetic-binding-checks-v1", "pass": self.binding_pass,
                "metrics": {"synthetic": 1.0}, "errors": []}

    def check_pose(self, *_args):
        self.calls.append(_args)
        refs = _args[5]
        scale = 10.0 if refs.get("joint_left", [0.0, 0.0, 0.0])[1] > 0.0 else 1.0
        return {"schema": "synthetic-checks-v1", "pass": True,
                "checks": {"synthetic": True}, "metrics": {"scale": scale},
                "errors": []}


class FakeRender:
    def __init__(self):
        self.calls = []

    def render_views(self, _vertices, _quads, output_path, _title, _status,
                     _bounds, _overlays, *, underside, allow_crop):
        output_path = Path(output_path)
        self.calls.append((_vertices, _quads, output_path, _overlays, underside, allow_crop))
        output_path.write_bytes(b"png")
        diagnostic = output_path.with_name(output_path.stem + "-diagnostic.png")
        diagnostic.write_bytes(b"diagnostic")
        underside_path = None
        if underside:
            underside_path = output_path.with_name(output_path.stem + "-underside.png")
            underside_path.write_bytes(b"underside")
        return {"output_path": str(output_path),
                "diagnostic_path": str(diagnostic),
                "underside_path": str(underside_path) if underside_path else None}


def protocol_fixture():
    return {"views": {"bounds": [[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]]},
            "checks": {"pivot_counterfactual_response_over_L_min": 1.0},
            "pivot_counterfactual": {"J_left_delta": [0.0, 0.01, 0.0],
                                      "pose": {"left": 15.0, "right": 0.0}},
            "poses": [{"id": "rest", "left": 0.0, "right": 0.0},
                      {"id": "left_flex_15", "left": 15.0, "right": 0.0},
                      {"id": "left_flex_30", "left": 30.0, "right": 0.0},
                      {"id": "right_flex_15", "left": 0.0, "right": 15.0},
                      {"id": "both_flex_20", "left": 20.0, "right": 20.0}]}


class RunnerTests(unittest.TestCase):
    def test_capture_allowlist_is_exact_and_includes_integration(self):
        self.assertEqual(set(runner.CAPTURE_FILES), {
            "binding.py", "capture.py", "checks.py", "runner.py",
            "README.md", "protocol.json", "tests/test_binding.py",
            "tests/test_capture.py", "tests/test_checks.py",
            "tests/test_integration.py", "tests/test_runner.py",
        })

    def test_absent_output_is_a_sibling_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot"
            snapshot.mkdir()
            output = root / "output"
            self.assertEqual(runner._require_absent_output(output, snapshot), output)
            output.mkdir()
            with self.assertRaises(runner.RunnerError):
                runner._require_absent_output(output, snapshot)
            with self.assertRaises(runner.RunnerError):
                runner._require_absent_output(snapshot / "nested", snapshot)

    def test_dynamic_import_is_registered_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            module_path = Path(directory) / "module.py"
            module_path.write_text("VALUE = 7\n", encoding="utf-8")
            loaded = runner._load_module("synthetic_runner_module", module_path)
            self.assertIs(sys.modules["synthetic_runner_module"], loaded)
            self.assertEqual(loaded.VALUE, 7)

    def test_overlays_use_serialized_joint_schema_and_diagnostic_labels(self):
        points = FakeBinding().joint_points({}, {"left": 15.0, "right": 0.0})
        refs = {"crest_left": [0.0, 0.5, 0.0], "crest_right": [0.0, 0.5, 0.0],
                "asis_left": [0.0, 0.4, 0.1], "asis_right": [0.0, 0.4, 0.1],
                "psis_left": [0.0, 0.3, -0.1], "psis_right": [0.0, 0.3, -0.1],
                "trochanter_left": [0.0, -0.4, 0.0],
                "trochanter_right": [0.0, -0.4, 0.0],
                "pubic_symphysis": [0.0, -0.2, 0.0]}
        overlays = runner._overlays({"left": points["left"], "right": points["right"]}, refs)
        self.assertGreaterEqual(len(overlays), 11)
        self.assertTrue(all(set(item) == {"start", "end", "color", "label"}
                            for item in overlays))
        self.assertTrue(all(item["label"].startswith("diagnostic") for item in overlays))
        self.assertEqual(overlays[0]["start"], [0.0, 0.0, 0.0])

    def test_frozen_helper_import_smoke_does_not_execute_body(self):
        loaded = runner._load_module(
            "synthetic_runner_capture_smoke", ROOT / "capture.py")
        self.assertIs(sys.modules["synthetic_runner_capture_smoke"], loaded)
        self.assertTrue(hasattr(loaded, "prepare"))

    def test_pose_export_serializes_actual_joint_matrices(self):
        mesh = {"vertices": [[0.0, 0.0, 0.0]], "metadata": {}}
        points = {"left": {"posed_matrix": [[2.0] * 4] * 4},
                  "right": {"posed_matrix": IDENTITY}}
        exported = runner._pose_export(mesh, points, {"left": 15.0, "right": 0.0})
        self.assertEqual(exported["metadata"]["joints"]["left_hip"]["pose_matrix"],
                         points["left"]["posed_matrix"])
        self.assertEqual(exported["metadata"]["joints"]["pelvis"]["pose_matrix"], IDENTITY)
        self.assertEqual(mesh["metadata"], {})
        json.dumps(exported)

    def test_synthetic_orchestration_keeps_five_poses_and_counterfactual_separate(self):
        base = {"vertices": [[0.0, 0.0, 0.0]]}
        rest = {"vertices": [[0.0, 0.0, 0.0]], "quads": [], "metadata": {}}
        case = {"id": "calibrated_ordinary_human", "attachments": {}}
        refs = {"joint_left": [0.0, 0.0, 0.0], "joint_right": [0.0, 0.0, 0.0],
                "trochanter_left": [0.0, -0.4, 0.0],
                "trochanter_right": [0.0, -0.4, 0.0]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            summary = runner._run_case(
                "calibrated_ordinary_human", base, rest, case, refs,
                protocol_fixture(), output, FakeBinding(), FakeChecks(), FakeRender())
            self.assertEqual(len(summary["poses"]), 5)
            self.assertEqual({row["id"] for row in summary["poses"]},
                             {pose["id"] for pose in protocol_fixture()["poses"]})
            self.assertTrue(summary["counterfactual"]["diagnostic_only"])
            self.assertTrue(summary["binding_method_pass"])
            self.assertNotIn("counterfactual", {row["id"] for row in summary["poses"]})
            self.assertTrue(summary["rest_vertices_unchanged"])
            self.assertTrue((output / "cases/calibrated_ordinary_human/poses/rest/mesh.json").is_file())
            self.assertTrue((output / "cases/calibrated_ordinary_human/counterfactual/checks.json").is_file())

    def test_synthetic_orchestration_reads_back_mesh_binding_and_joints(self):
        base = {"vertices": [[0.0, 0.0, 0.0]]}
        rest = {"vertices": [[0.0, 0.0, 0.0]], "quads": [], "metadata": {}}
        case = {"id": "calibrated_ordinary_human", "attachments": {}}
        refs = {"joint_left": [0.0, 0.0, 0.0], "joint_right": [0.0, 0.0, 0.0],
                "trochanter_left": [0.0, -0.4, 0.0],
                "trochanter_right": [0.0, -0.4, 0.0]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            checks = FakeChecks()
            render = FakeRender()
            protocol = protocol_fixture()
            protocol["pivot_counterfactual"] = {
                "J_left_delta": [0.0, 0.02, 0.0],
                "pose": {"left": 17.0, "right": 3.0},
            }
            read_values = {}
            original_read_json = runner._read_json

            def read_json(path):
                value = original_read_json(path)
                read_values[Path(path)] = value[0]
                return value

            with mock.patch.object(runner, "_read_json", side_effect=read_json):
                runner._run_case(
                    "calibrated_ordinary_human", base, rest, case, refs,
                    protocol, output, FakeBinding(), checks, render)
            binding_path = output / "cases/calibrated_ordinary_human/binding.json"
            mesh_path = output / "cases/calibrated_ordinary_human/poses/rest/mesh.json"
            joints_path = output / "cases/calibrated_ordinary_human/poses/rest/joints.json"
            self.assertIs(checks.calls[0][1], read_values[mesh_path])
            self.assertIs(checks.calls[0][2], read_values[binding_path])
            self.assertIs(checks.binding_calls[0][2], read_values[binding_path])
            self.assertIn(joints_path, read_values)
            self.assertIs(render.calls[0][0], read_values[mesh_path]["vertices"])
            self.assertEqual(len(checks.calls), 6)
            counter_binding = output / "cases/calibrated_ordinary_human/counterfactual/binding.json"
            counter_mesh = output / "cases/calibrated_ordinary_human/counterfactual/mesh.json"
            counter_joints = output / "cases/calibrated_ordinary_human/counterfactual/joints.json"
            self.assertIn(counter_binding, read_values)
            self.assertIn(counter_mesh, read_values)
            self.assertIn(counter_joints, read_values)
            comparison = json.loads((counter_mesh.parent / "comparison.json").read_text(encoding="utf-8"))
            self.assertEqual(comparison["J_left_delta"], [0.0, 0.02, 0.0])
            self.assertEqual(comparison["counterfactual_pose"], {"left": 17.0, "right": 3.0})
            self.assertEqual(comparison["L"], 1.0)
            counter_joints_value = read_values[counter_joints]
            self.assertEqual(counter_joints_value["angles_degrees"], {"left": 17.0, "right": 3.0})

    def test_binding_numeric_failure_does_not_hide_pose_evidence(self):
        base = {"vertices": [[0.0, 0.0, 0.0]]}
        rest = {"vertices": [[0.0, 0.0, 0.0]], "quads": [], "metadata": {}}
        case = {"id": "calibrated_ordinary_human", "attachments": {}}
        refs = {"joint_left": [0.0, 0.0, 0.0], "joint_right": [0.0, 0.0, 0.0],
                "trochanter_left": [0.0, -0.4, 0.0],
                "trochanter_right": [0.0, -0.4, 0.0]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            checks = FakeChecks(binding_pass=False)
            render = FakeRender()
            summary = runner._run_case(
                "calibrated_ordinary_human", base, rest, case, refs,
                protocol_fixture(), output, FakeBinding(), checks, render)
            self.assertFalse(summary["binding_method_pass"])
            self.assertEqual(len(summary["poses"]), 5)
            self.assertEqual(len(render.calls), 5)
            self.assertTrue(all(row["technical_status"] == "TECHNICAL REJECTED"
                                for row in summary["poses"]))
            self.assertTrue((output / "cases/calibrated_ordinary_human/binding-checks.json").is_file())
            self.assertTrue((output / "cases/calibrated_ordinary_human/poses/left_flex_15/mesh.json").is_file())


if __name__ == "__main__":
    unittest.main()

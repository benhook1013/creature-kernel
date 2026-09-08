from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import capture  # noqa: E402


def identity(root: Path, construction: str = "x") -> dict[str, object]:
    return {"runtime": {"executable": "/frozen/runtime/bin/python"}, "manifest": {"construction": {"sha256": construction}}, "root": str(root)}


class CaptureTests(unittest.TestCase):
    def test_prepare_refuses_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            with self.assertRaises(capture.CaptureError):
                capture.prepare(str(output), ["capture.py"])

    def test_prepare_copy_and_verify_with_tiny_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "capture.py").write_text("capture", encoding="utf-8")
            (source / "tests").mkdir()
            (source / "tests/test_capture.py").write_text("tests", encoding="utf-8")
            calibration = root / "calibration"
            calibration.mkdir()
            (calibration / "prepare-report.json").write_text('{"status":"prepared"}', encoding="utf-8")
            (calibration / "source-manifest.json").write_text('{"schema":"creature-kernel.pelvis-source-calibration-captured-source.v1","files":[]}', encoding="utf-8")
            input_path = calibration / "input.json"
            input_path.write_text('{"tiny":true}\n', encoding="utf-8")
            frozen_runner = root / "runner.py"
            frozen_runner.write_text("# stdlib-only test placeholder\n", encoding="utf-8")
            entries = [("tiny", input_path, Path("inputs/tiny.json"), "rest_mesh")]
            dependency = identity(root, capture.CONSTRUCTION_SHA256)
            with mock.patch.object(capture, "HERE", source), mock.patch.object(capture, "INPUT_MAPPINGS", ()), mock.patch.object(capture, "CALIBRATION_SOURCE_MANIFEST", calibration / "source-manifest.json"), mock.patch.object(capture, "CALIBRATION_PREPARE_REPORT", calibration / "prepare-report.json"), mock.patch.object(capture, "FROZEN_CALIBRATION_RUNNER", frozen_runner), mock.patch.object(capture, "_calibration_inputs", return_value=entries), mock.patch.object(capture, "_load_frozen_dependency_identity", return_value=dependency):
                output = root / "output"
                manifest = capture.prepare(str(output), ["capture.py", "tests/test_capture.py"])
                self.assertFalse(manifest["geometry_executed"])
                self.assertEqual(capture.verify(str(output))["status"], "prepared")
                self.assertEqual(len(capture.artifact_manifest(str(output))["files"]), 4)

    def test_verify_detects_changed_rest_mesh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "inputs/case-05-calibrated_ordinary_human-rest-L0.json"
            target.parent.mkdir()
            target.write_text("original", encoding="utf-8")
            manifest = {"schema": "creature-kernel.pelvis-hip-articulation-capture.v1", "status": "prepared", "geometry_executed": False, "body_articulation_executed": False, "captured_source": {"before": [], "after": [], "copies": []}, "inputs": {"before": [], "after": [], "copies": [{"name": "case_05_rest_L0", "kind": "rest_mesh", "snapshot_path": "inputs/case-05-calibrated_ordinary_human-rest-L0.json", "bytes": 8, "sha256": hashlib.sha256(b"original").hexdigest()}]}, "frozen_dependency": {"before": {}, "after": {}, "construction_sha256": capture.CONSTRUCTION_SHA256}, "runtime_path": "/frozen/runtime/bin/python"}
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            target.write_text("changed", encoding="utf-8")
            with mock.patch.object(capture, "_load_frozen_dependency_identity", return_value={}):
                with self.assertRaises(capture.CaptureError):
                    capture.verify(str(root))

    def test_actual_frozen_dependency_identity_smoke_is_read_only(self) -> None:
        dependency = capture._load_frozen_dependency_identity()
        self.assertEqual(dependency["manifest"]["construction"]["sha256"], capture.CONSTRUCTION_SHA256)
        self.assertEqual(dependency["runtime"]["executable"], str(capture.FROZEN_DEPENDENCY_ROOT / "runtime/bin/python"))

    def test_actual_calibration_inputs_manifest_smoke_is_read_only(self) -> None:
        inputs = capture._calibration_inputs()
        self.assertEqual(len(inputs), 6)
        self.assertEqual(sum(kind == "rest_mesh" for _name, _source, _target, kind in inputs), 4)
        self.assertEqual({name for name, _source, _target, _kind in inputs}, {"case_05_rest_L0", "case_05_rest_L2", "case_06_rest_L0", "case_06_rest_L2", "calibration_protocol", "calibration_inputs"})


if __name__ == "__main__":
    unittest.main()

"""End-to-end tests for the CK-KICK-010 headless command."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import trimesh

from ck_spike.cli import main


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "valid.json"
INVALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "invalid-missing-right-shin.json"
EXPECTED_VALID = {
    "diagnostics.json",
    "manifest.json",
    "mesh.ply",
    "resolved_graph.json",
    "semantic_regions.json",
}
EXPECTED_INVALID = {"diagnostics.json", "manifest.json"}


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.parent = Path(self.temporary.name) / "outputs"
        self.parent.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, fixture: Path, target: Path, *extra: str):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "build",
                    "--input",
                    str(fixture),
                    "--output",
                    str(target),
                    "--samples-per-axis",
                    "12",
                    *extra,
                ]
            )
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        return code, json.loads(lines[0])

    @staticmethod
    def hashes(bundle: Path) -> dict[str, str]:
        return {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in bundle.iterdir()
            if path.is_file()
        }

    def test_valid_build_publishes_exact_bundle_and_manifest_hashes(self):
        target = self.parent / "valid"
        code, result = self.run_cli(VALID_FIXTURE, target)

        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(set(result["artifact_names"]), EXPECTED_VALID)
        self.assertEqual({path.name for path in target.iterdir()}, EXPECTED_VALID)

        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("manifest.json", manifest["artifacts"])
        self.assertEqual(
            manifest["artifacts"],
            {name: self.hashes(target)[name] for name in sorted(EXPECTED_VALID - {"manifest.json"})},
        )
        self.assertEqual(manifest["fixture_id"], "ck-kick-010-valid-biped")
        self.assertEqual(manifest["geometry_config"]["samples_per_axis"], 12)
        self.assertEqual(manifest["export"]["landmark_verification"]["label"], "left_ear")
        self.assertTrue(manifest["export"]["landmark_verification"]["pass"])
        self.assertGreater(manifest["export"]["landmark_verification"]["source_world_position"][0], 0)
        self.assertGreater(manifest["export"]["determinant"], 0)

        graph = json.loads((target / "resolved_graph.json").read_text(encoding="utf-8"))
        self.assertEqual(len(graph["nodes"]), 15)
        regions = json.loads((target / "semantic_regions.json").read_text(encoding="utf-8"))
        self.assertEqual(regions["mesh_vertex_indices"], "artifact-local")
        self.assertTrue(regions["mesh_vertex_indices_are_artifact_local"])
        self.assertEqual(len(regions["source_node_labels"]), manifest["metrics"]["vertex_count"])
        self.assertNotIn("weights", regions)

        mesh = trimesh.load(io.BytesIO((target / "mesh.ply").read_bytes()), file_type="ply", process=False)
        self.assertEqual(len(mesh.vertices), manifest["metrics"]["vertex_count"])
        self.assertEqual(len(mesh.faces), manifest["metrics"]["face_count"])
        self.assertTrue(mesh.is_watertight)
        header = (target / "mesh.ply").read_text(encoding="ascii").split("end_header\n", 1)[0]
        self.assertIn("property double x\n", header)
        self.assertIn("property double y\n", header)
        self.assertIn("property double z\n", header)
        self.assertIn("property double nx\n", header)
        self.assertIn("property double ny\n", header)
        self.assertIn("property double nz\n", header)
        self.assertNotIn("property float ", header)

    def test_invalid_build_publishes_diagnostics_only_with_primary_code(self):
        target = self.parent / "invalid"
        code, result = self.run_cli(INVALID_FIXTURE, target)

        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["diagnostic_codes"], ["MISSING_REQUIRED_MODULE"])
        self.assertEqual({path.name for path in target.iterdir()}, EXPECTED_INVALID)
        self.assertEqual(
            json.loads((target / "diagnostics.json").read_text(encoding="utf-8"))["diagnostics"][0]["code"],
            "MISSING_REQUIRED_MODULE",
        )
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "invalid")
        self.assertIsNone(manifest["grid"])
        self.assertIsNone(manifest["metrics"])

    def test_two_valid_runs_are_byte_identical(self):
        first = self.parent / "first"
        second = self.parent / "second"
        self.assertEqual(self.run_cli(VALID_FIXTURE, first)[0], 0)
        self.assertEqual(self.run_cli(VALID_FIXTURE, second)[0], 0)
        for name in sorted(EXPECTED_VALID):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

    def test_existing_target_is_refused_and_unchanged(self):
        target = self.parent / "existing"
        target.mkdir()
        marker = target / "keep"
        marker.write_bytes(b"do not overwrite")
        code, result = self.run_cli(VALID_FIXTURE, target)

        self.assertEqual(code, 4)
        self.assertEqual(result["diagnostic_codes"], ["OUTPUT_TARGET_EXISTS"])
        self.assertEqual(marker.read_bytes(), b"do not overwrite")
        self.assertEqual(sorted(path.name for path in target.iterdir()), ["keep"])

    def test_field_failure_is_machine_readable_and_publishes_no_target(self):
        target = self.parent / "field-failure"
        code, result = self.run_cli(VALID_FIXTURE, target, "--samples-per-axis", "3", "--padding", "0")

        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["diagnostic_codes"], ["FIELD_DOMAIN_FACE_NOT_POSITIVE"])
        self.assertFalse(target.exists())

    def test_module_entry_smoke(self):
        target = self.parent / "smoke"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ck_spike",
                "build",
                "--input",
                str(VALID_FIXTURE),
                "--output",
                str(target),
                "--samples-per-axis",
                "8",
            ],
            cwd=EXPERIMENT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        self.assertEqual(json.loads(completed.stdout)["status"], "valid")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()

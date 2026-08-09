"""Focused checks for the disposable CK-KICK-010 evidence helper."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TOOL = EXPERIMENT_ROOT / "tools" / "reproduce_evidence.py"


class EvidenceReproductionTests(unittest.TestCase):
    def run_tool(self, output_root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), "--output-root", str(output_root), *extra],
            cwd=EXPERIMENT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_success_reports_four_runs_inventories_hashes_and_equality(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "outputs"
            parent.mkdir()
            output_root = parent / "evidence"
            completed = self.run_tool(output_root, "--samples-per-axis", "8")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            summary = json.loads(completed.stdout)
            self.assertEqual(
                [run["name"] for run in summary["runs"]],
                ["valid-a", "valid-b", "invalid-a", "invalid-b"],
            )
            self.assertEqual(
                summary["runs"][0]["inventory"],
                [
                    "diagnostics.json",
                    "manifest.json",
                    "mesh.ply",
                    "resolved_graph.json",
                    "semantic_regions.json",
                ],
            )
            self.assertEqual(
                summary["runs"][2]["inventory"], ["diagnostics.json", "manifest.json"]
            )
            self.assertEqual(
                [run["exit_code"] for run in summary["runs"]], [0, 0, 2, 2]
            )
            self.assertTrue(summary["comparisons"]["valid"]["byte_equal"])
            self.assertTrue(summary["comparisons"]["invalid"]["byte_equal"])
            for run in summary["runs"]:
                self.assertEqual(set(run["sha256"]), set(run["inventory"]))

    def test_existing_output_root_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "outputs"
            parent.mkdir()
            output_root = parent / "existing"
            output_root.mkdir()
            marker = output_root / "keep.txt"
            marker.write_text("keep me", encoding="utf-8")

            completed = self.run_tool(output_root, "--samples-per-axis", "8")

            self.assertEqual(completed.returncode, 2)
            self.assertIn("output root already exists", completed.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep me")
            self.assertEqual(list(output_root.iterdir()), [marker])

    def test_missing_parent_is_refused_and_nothing_is_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "missing" / "evidence"

            completed = self.run_tool(output_root, "--samples-per-axis", "8")

            self.assertEqual(completed.returncode, 2)
            self.assertIn("output root parent does not exist", completed.stderr)
            self.assertFalse(output_root.exists())
            self.assertFalse(output_root.parent.exists())


if __name__ == "__main__":
    unittest.main()

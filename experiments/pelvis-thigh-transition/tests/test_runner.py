from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import runner


def _cube(offset: float = 0.0):
    vertices = (
        (-0.6, -0.4, -0.5 + offset), (0.6, -0.4, -0.5 + offset),
        (0.6, 0.4, -0.5 + offset), (-0.6, 0.4, -0.5 + offset),
        (-0.6, -0.4, 0.5 + offset), (0.6, -0.4, 0.5 + offset),
        (0.6, 0.4, 0.5 + offset), (-0.6, 0.4, 0.5 + offset),
    )
    quads = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7))
    return {
        "vertices": vertices, "quads": quads,
        "face_owners": ("synthetic",) * len(quads),
        "control_owners": ("synthetic",) * len(vertices),
        "loops": {"synthetic": (0, 1, 2, 3)},
        "base_stencils": tuple((((index, 1.0),),) for index in range(len(vertices))),
        "frames": {"synthetic": {"axis": (0.0, -1.0, 0.0)}},
        "metadata": {"synthetic": True},
    }


def _inputs(path: Path):
    cases = [
        {"id": "standard_neutral_reference", "role": "mandatory", "components": {"x": 0.0},
         "attachments": {"left": {"centre": [-0.2, 0.0, 0.0], "knee": [-0.2, -0.3, 0.0]},
                          "right": {"centre": [0.2, 0.0, 0.0], "knee": [0.2, -0.3, 0.0]}}},
        {"id": "ordinary_human_reference", "role": "mandatory", "components": {"x": 0.0},
         "attachments": {}},
        {"id": "neutral_pelvis_width", "role": "predeclared_neutral_perturbation", "components": {"x": 0.1},
         "attachments": {}},
        {"id": "neutral_invalid_close_thick", "role": "predeclared_neutral_perturbation", "components": {"x": 1.0},
         "attachments": {}},
    ]
    path.write_text(json.dumps({"perturbation_case_ids": [cases[2]["id"], cases[3]["id"]], "cases": cases}), encoding="utf-8")


class RunnerTests(unittest.TestCase):
    def test_depth12_gate_report_preserves_diagnostics_and_technical_outcome(self):
        # The barycentric scalars are at depth 12 (report root is depth 0).
        # Frame/ray/hit nesting previously exceeded the serialization limit 8.
        for passed in (True, False):
            with self.subTest(technical_pass=passed):
                report = {
                    "schema": "pelvis-thigh-transition/checks-v1",
                    "technical": {
                        "pass": passed,
                        "levels": [{"frames": {"left": {"containment": {
                            "rays": {"+X": {"hits": [{
                                "barycentric": [0.25, 0.25, 0.5],
                                "distance": 0.125,
                                "face_pair": [17, 42],
                                "pass": passed,
                            }]}}
                        }}}}],
                    },
                    "render": {"safe": True},
                }
                outcome, retained = runner._check_outcome(report)
                self.assertEqual(outcome, "technical_pass" if passed else "rejected")
                self.assertEqual(retained, report)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "case-report.json"
                    runner._write_json(path, retained)
                    self.assertEqual(json.loads(path.read_text(encoding="utf-8")), report)

    def test_bounded_serialization_rejects_depth65_after_accepting_depth64(self):
        value = {"pass": False}
        for _ in range(63):
            value = [value]
        self.assertEqual(runner._bounded(value), value)
        with self.assertRaisesRegex(runner.RunnerError, "nesting exceeds the bounded depth"):
            runner._bounded([value])

    def _mock_apis(self, check_outcome=None, comparison_pass=True):
        calls = []

        def build(components, attachments, diagnostic=False):
            calls.append(("build", components, attachments, diagnostic))
            return {"id": "synthetic"}

        def evaluate(built, levels=2):
            calls.append(("evaluate", built, levels))
            mesh = _cube()
            return [mesh, mesh, mesh]

        def check(case, levels):
            calls.append(("check", case, levels))
            if check_outcome is not None:
                return check_outcome
            return {"schema": "synthetic-checks-v1",
                    "outcome": "reject" if "invalid" in case["id"] else "pass",
                    "numeric": "synthetic"}

        def compare(base_case, base_levels, case, levels):
            calls.append(("compare", base_case, base_levels, case, levels))
            return {"schema": "synthetic-perturbation-v1", "pass": comparison_pass}

        construction = SimpleNamespace(build=build, evaluate=evaluate)
        checker = SimpleNamespace(check_case=check,
                                  compare_perturbation=compare)
        return patch.multiple(runner, construction=construction, checks=checker,
                              _validate_registered_inputs=lambda *_args: None), calls

    def test_mock_run_persists_unverified_final_and_complete_mesh_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            context, calls = self._mock_apis()
            with context:
                report = runner.run(inputs, output, attempt=0, workers=1)
            invalid = output / "cases" / "case-03-neutral_invalid_close_thick"
            self.assertEqual(report["case_count"], 4)
            self.assertEqual(report["outcome"], "pass")
            self.assertTrue((output / "inputs.json").is_file())
            self.assertTrue((output / "runner-source.py").is_file())
            self.assertTrue((output / "stable-manifest.json").is_file())
            mesh = json.loads((invalid / "mesh-level-2.json").read_text(encoding="utf-8"))
            for key in ("face_owners", "control_owners", "loops", "base_stencils", "frames", "metadata"):
                self.assertIn(key, mesh)
            self.assertTrue((invalid / "lowercrop-unverified.png").is_file())
            self.assertTrue((invalid / "lowercrop-unverified-underside.png").is_file())
            self.assertTrue((invalid / "lowercrop-final.png").is_file())
            self.assertTrue((invalid / "fullroot-final.png").is_file())
            self.assertTrue((invalid / "case-report-unverified.json").is_file())
            self.assertTrue((invalid / "case-report.json").is_file())
            self.assertEqual(report["cases"][3]["outcome"], "rejected")
            self.assertTrue(report["cases"][3]["expected_rejection_met"])
            self.assertEqual(calls[0][0:2], ("build", {"x": 0.0}))
            self.assertIs(calls[0][3], True)
            self.assertEqual(calls[1][0:3], ("evaluate", {"id": "synthetic"}, 2))

    def test_bounds_and_comparison_are_input_driven_and_manifest_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output_a, output_b = root / "inputs.json", root / "a", root / "b"
            _inputs(inputs)
            with self._mock_apis()[0]:
                first = runner.run(inputs, output_a, attempt=1, workers=1)
            with self._mock_apis()[0]:
                second = runner.run(inputs, output_b, attempt=1, workers=1)
            self.assertEqual(first["perturbation_comparisons"][0]["outcome"], "compared")
            self.assertEqual(first["cases"][0]["bounds"]["lowercrop"],
                             [[-2.4, -2.7, -1.3], [2.4, 1.0, 1.3]])
            self.assertTrue(first["cases"][1]["bounds"]["physical_scale"].startswith("human reference"))
            self.assertEqual((output_a / "stable-manifest.json").read_bytes(),
                             (output_b / "stable-manifest.json").read_bytes())

    def test_failed_valid_comparison_propagates_to_root_and_is_not_compared(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            with self._mock_apis(comparison_pass=False)[0]:
                report = runner.run(inputs, output, attempt=0, workers=1)
            self.assertEqual(report["outcome"], "failed")
            self.assertEqual(report["comparison_failure_count"], 2)
            self.assertEqual(report["perturbation_comparisons"][0]["outcome"], "failed")
            self.assertFalse(report["perturbation_comparisons"][0]["comparison_pass"])

    def test_missing_outcome_is_an_error_not_an_implicit_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            with self._mock_apis(check_outcome={"schema": "synthetic-checks-v1"})[0]:
                report = runner.run(inputs, output, attempt=0, workers=1)
            self.assertTrue(all(case["outcome"] == "error" for case in report["cases"]))
            self.assertEqual(report["outcome"], "failed")
            self.assertTrue(any(item["phase"] == "checks.check_case"
                                for item in report["cases"][0]["exceptions"]))

    def test_missing_checker_fails_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            construction = SimpleNamespace(build=lambda *_args, **_kwargs: {},
                                           evaluate=lambda *_args, **_kwargs: [])
            with patch.object(runner, "construction", construction), patch.object(runner, "checks", None), self.assertRaises(runner.RunnerError):
                runner.run(inputs, output, attempt=0, workers=1)
            self.assertFalse(output.exists())

    def test_missing_construction_or_build_fails_closed_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            checks = SimpleNamespace(check_case=lambda *_args: {},
                                     compare_perturbation=lambda *_args: {})
            for construction in (None, SimpleNamespace(evaluate=lambda *_args: [])):
                with self.subTest(construction=construction):
                    with patch.object(runner, "construction", construction), patch.object(runner, "checks", checks), self.assertRaises(runner.RunnerError):
                        runner.run(inputs, output, attempt=0, workers=1)
                    self.assertFalse(output.exists())

    def test_output_must_be_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            output.mkdir()
            with self._mock_apis()[0], self.assertRaises(runner.RunnerError):
                runner.run(inputs, output, attempt=0, workers=1)

    def test_modified_or_missing_registered_inputs_fail_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs.json", root / "run"
            _inputs(inputs)
            with self.assertRaises(runner.RunnerError):
                runner.run(inputs, output, attempt=0, workers=1)
            self.assertFalse(output.exists())
            inputs.unlink()
            with self.assertRaises(runner.RunnerError):
                runner.run(inputs, output, attempt=0, workers=1)
            self.assertFalse(output.exists())

    def test_cases_py_exact_document_check_is_required_after_digest(self):
        raw = b'{"registered":true}\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inputs.json"
            path.write_bytes(raw)
            fake_cases = SimpleNamespace(main=lambda argv: (_ for _ in ()).throw(ValueError("modified")))
            with patch.object(runner, "REGISTERED_INPUT_SHA256", hashlib.sha256(raw).hexdigest()), \
                    patch.object(runner, "cases", fake_cases), \
                    self.assertRaises(runner.RunnerError):
                runner._validate_registered_inputs(path, raw)


if __name__ == "__main__":
    unittest.main()

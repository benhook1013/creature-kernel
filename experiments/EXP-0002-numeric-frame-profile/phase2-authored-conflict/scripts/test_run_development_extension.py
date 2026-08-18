"""Focused non-executing tests for the extension runner contract."""

from __future__ import annotations

import unittest

import development_extension_corpus as corpus
import run_development_extension as runner
import profile_sweep


class DevelopmentExtensionRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.extension = corpus.load_development_extension_corpus()
        cls.sweep = profile_sweep.load_profile_sweep()

    def test_request_shape_and_identity_are_extension_specific(self) -> None:
        case = self.extension["cases"][0]
        request, tolerance_bits = runner.build_request(case, "strict", corpus.materialize_case(case), self.sweep)
        self.assertEqual(request["request_id"], "dev-ext-strict-boundary-strict")
        self.assertEqual(request["operation"], "observe-authored-conflict")
        self.assertEqual(set(tolerance_bits), {"translation_absolute", "translation_relative", "rotation_half_chord"})
        self.assertEqual(len(request["source"]), case["source_bytes"])

    def test_report_requires_exact_18_requests_and_nine_each(self) -> None:
        entries = []
        for case in self.extension["cases"]:
            for candidate_id in profile_sweep.CANDIDATE_IDS:
                expected = case["expected"][profile_sweep.PROFILE_IDS[candidate_id]]["classification"]
                entries.append(runner._entry(case, candidate_id, f"id-{len(entries)}", "req", "resp", expected, expected, True, None))
        report = runner._report(entries, {"extension_corpus_sha256": "x"}, [], 18)
        self.assertEqual(report["report_id"], runner.REPORT_ID)
        self.assertEqual(report["schema"], runner.REPORT_SCHEMA)
        self.assertEqual(report["run_status"], "pass")
        self.assertEqual(report["summary"]["planned"], 18)
        self.assertEqual(report["summary"]["classification_totals"], {"agree": 9, "conflict": 9})
        self.assertEqual(report["profile_selection"], "none")
        self.assertEqual(report["r3_activation"], "inactive")

    def test_incomplete_transport_cannot_pass(self) -> None:
        case = self.extension["cases"][0]
        entry = runner._entry(case, "strict", "id", "req", None, "incomplete", "agree", False, "inconclusive:transport:timeout")
        report = runner._report([entry], {}, ["inconclusive:transport:timeout"], 1)
        self.assertEqual(report["run_status"], "inconclusive")
        self.assertNotEqual(report["summary"]["passed"], 18)

    def test_complete_non_witness_oracle_error_is_failure(self) -> None:
        case = self.extension["cases"][0]
        entry = runner._entry(case, "strict", "id", "req", "resp", "failed", "agree", False, "oracle:wrong-type")
        report = runner._report([entry], {}, ["oracle:wrong-type"], 1)
        self.assertEqual(report["run_status"], "fail")

    def test_oracle_integrity_uncertainty_is_inconclusive(self) -> None:
        case = self.extension["cases"][0]
        entry = runner._entry(case, "strict", "id", "req", "resp", "incomplete", "agree", False, "inconclusive:oracle-integrity:quaternion")
        report = runner._report([entry], {}, ["inconclusive:oracle-integrity:quaternion"], 1)
        self.assertEqual(report["run_status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()

"""Focused tests for the independent development-extension oracle."""

from __future__ import annotations

import copy
import unittest

import development_extension_corpus as corpus
import development_extension_oracle as oracle
import profile_sweep


class DevelopmentExtensionOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.extension = corpus.load_development_extension_corpus()
        cls.sweep = profile_sweep.load_profile_sweep()

    def _response(self, case: dict, candidate_id: str, outcome: str) -> tuple[dict, bytes]:
        source = corpus.materialize_case(case)
        witness = oracle.expected_witness(source)
        record = {item["candidate_id"]: item for item in self.sweep["candidates"]}[candidate_id]
        tolerance_bits = {
            "translation_absolute": record["constants"]["A"]["bits"],
            "translation_relative": record["constants"]["R"]["bits"],
            "rotation_half_chord": record["constants"]["H"]["bits"],
        }
        identity = oracle.source_member_identity(source)
        attachment = copy.deepcopy(witness)
        attachment["outcome"] = outcome
        response = {
            "protocol_id": "ck.exp-0002.r3-authored-conflict-candidate-response-1",
            "request_id": f"test-{case['case_id']}-{candidate_id}",
            "status": "observed",
            "observations": {
                "root": identity,
                "members": [{
                    "identity": identity,
                    "role": "root",
                    "outcome": "compared",
                    "attachments": [attachment],
                }],
                "tolerances": tolerance_bits,
                "providers": {
                    "gate": {"selection": "allow", "attestation": "unattested"},
                    "arithmetic": {"selection": "native", "attestation": "unattested"},
                    "sqrt": {"selection": "native", "attestation": "unattested"},
                    "environment": "unattested-no-probe-v1",
                },
            },
        }
        return response, source

    def test_all_six_cases_have_a_five_step_long_tail_witness(self) -> None:
        self.assertEqual(len(self.extension["cases"]), 6)
        for case in self.extension["cases"]:
            witness = oracle.expected_witness(corpus.materialize_case(case))
            path = witness["provenance"]["root_to_mating_owner_path"]
            self.assertEqual([item["role"] for item in path], ["tail_root", "tail_tip", "tail_end"])
            self.assertEqual(len(witness["equation"]["equation_steps"]), 5)

    def test_frozen_sign_and_source_identity_regression(self) -> None:
        source = corpus.materialize_case(self.extension["cases"][0])
        witness = oracle.expected_witness(source)
        self.assertEqual(
            oracle.source_member_identity(source),
            {"document": "stylized_digitigrade_biped", "namespace": "main"},
        )
        rotations = [step["output"]["rotation_xyzw"] for step in witness["equation"]["equation_steps"]]
        positive_zero = "0x0000000000000000"
        self.assertEqual(rotations[0], ["0x3ff0000000000000", positive_zero, positive_zero, positive_zero])
        self.assertEqual(rotations[1], [positive_zero, positive_zero, positive_zero, "0x3ff0000000000000"])
        self.assertEqual(rotations[3], [positive_zero, positive_zero, positive_zero, "0x3ff0000000000000"])
        self.assertEqual(rotations[4], ["0x3ff0000000000000", positive_zero, positive_zero, positive_zero])

    def test_exact_witness_accepts_expected_case_outcomes(self) -> None:
        for case in self.extension["cases"]:
            candidate_id = case["case_id"].split("-", 1)[0]
            profile_id = profile_sweep.PROFILE_IDS[candidate_id]
            expected = case["expected"][profile_id]["classification"]
            response, source = self._response(case, candidate_id, expected)
            self.assertEqual(
                oracle.verify_response(response, source, profile_id, response["observations"]["tolerances"]),
                expected,
            )

    def test_wrong_witness_is_not_reduced_to_classification(self) -> None:
        case = self.extension["cases"][0]
        response, source = self._response(case, "strict", "agree")
        response["observations"]["members"][0]["attachments"][0]["equation"]["equation_steps"][0]["operation"] = "attachment-equation"
        with self.assertRaises(oracle.OracleError) as raised:
            oracle.verify_response(response, source, profile_sweep.PROFILE_IDS["strict"], response["observations"]["tolerances"])
        self.assertEqual(raised.exception.code, "witness-mismatch")

    def test_unsupported_response_is_a_candidate_response_error(self) -> None:
        case = self.extension[0] if isinstance(self.extension, list) else self.extension["cases"][0]
        response, source = self._response(case, "strict", "agree")
        response["status"] = "unsupported"
        response.pop("observations")
        with self.assertRaises(oracle.OracleError) as raised:
            oracle.verify_response(response, source, profile_sweep.PROFILE_IDS["strict"], {})
        self.assertEqual(raised.exception.code, "response-status")


if __name__ == "__main__":
    unittest.main()

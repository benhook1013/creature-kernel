"""Focused in-memory runner and synthetic receipt tests."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import phase3_oracle as oracle
import phase3_receipt as receipt
import phase3_runner as runner
from test_phase3_oracle_scorer import request, skipped_response, source_text, transform, wire_response


def case(request_id: str = "synthetic-1", **extra: object) -> dict[str, object]:
    value = request(request_id)
    value.update(extra)
    return value


class RunnerTests(unittest.TestCase):
    def test_actual_nested_response_and_gray_count_algebra(self) -> None:
        first = case("synthetic-1", expected_class="agree")
        truth = oracle.evaluate_source(first["source"], "translation")
        normal = wire_response(first, truth)
        gray = case("synthetic-gray", observation_only=True)
        gray_truth = oracle.evaluate_source(gray["source"], "translation")
        gray_response = wire_response(gray, gray_truth)
        result = runner.run_synthetic([first, gray], {"synthetic-1": normal, "synthetic-gray": gray_response})
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["counts"]["supported"], 1)
        self.assertEqual(result["counts"]["observation"], 1)
        self.assertEqual(sum(result["counts"][key] for key in ("supported", "failed", "inconclusive", "observation")), result["counts"]["entries"])

    def test_observation_only_cannot_support_aggregate(self) -> None:
        gray = case("synthetic-gray-only", observation_only=True)
        truth = oracle.evaluate_source(gray["source"], "translation")
        result = runner.run_synthetic([gray], {gray["request_id"]: wire_response(gray, truth)})
        self.assertEqual(result["counts"]["observation"], 1)
        self.assertEqual(result["counts"]["supported"], 0)
        self.assertEqual(result["status"], "inconclusive")
        decoded = json.loads(receipt.build_receipt(result))
        self.assertEqual(decoded["status"], "inconclusive")

    def test_typed_control_and_out_of_domain_observations_cannot_support(self) -> None:
        typed = case("synthetic-typed-observation", observation_only=True)
        typed["source"] = source_text(root_q=[0, 0, 0, 0])
        typed_truth = oracle.evaluate_source(typed["source"], "translation")
        outside = case("synthetic-domain-observation", observation_only=True)
        outside["source"] = source_text(descendants=[[0, 0, 0]] * 5)
        outside_truth = oracle.evaluate_source(outside["source"], "translation")
        self.assertEqual(outside_truth["status"], "out-of-domain")
        result = runner.run_synthetic([typed, outside], {typed["request_id"]: skipped_response(typed, typed_truth)})
        self.assertEqual([entry["status"] for entry in result["entries"]], ["observation", "observation"])
        self.assertEqual(result["counts"]["observation"], 2)
        self.assertEqual(result["status"], "inconclusive")

    def test_preflight_does_not_parse_keyed_response(self) -> None:
        value = case("synthetic-preflight", dispatch_to_candidate=False)
        result = runner.run_synthetic([value], {"synthetic-preflight": b'{"bad":NaN}'})
        self.assertEqual(result["preflight_count"], 1)
        self.assertEqual(result["entries"][0]["cause"]["code"], "dispatch-disabled")
        self.assertEqual(result["entries"][1]["cause"]["code"], "extra-response")

    def test_malformed_duplicate_nonfinite_and_oversized_are_per_case(self) -> None:
        cases = [case("synthetic-malformed"), case("synthetic-duplicate"), case("synthetic-nonfinite"), case("synthetic-oversized")]
        transcript = {
            "synthetic-malformed": b"{",
            "synthetic-duplicate": b'{"request_id":"synthetic-duplicate","request_id":"synthetic-duplicate"}',
            "synthetic-nonfinite": b'{"request_id":"synthetic-nonfinite","x":NaN}',
            "synthetic-oversized": b"x" * (64 * 1024 + 1),
        }
        result = runner.run_synthetic(cases, transcript)
        self.assertEqual(result["counts"]["inconclusive"], 4)
        self.assertEqual(result["status"], "inconclusive")

    def test_transcript_count_and_total_caps(self) -> None:
        with self.assertRaises(runner.RunnerError) as context:
            runner.run_synthetic([], {f"synthetic-{index}": b"" for index in range(65)})
        self.assertEqual(context.exception.code, "transcript-count")
        frames = {f"synthetic-{index}": b"x" * (64 * 1024 + 1) for index in range(64)}
        with self.assertRaises(runner.RunnerError) as context:
            runner.run_synthetic([], frames)
        self.assertEqual(context.exception.code, "transcript-total-bytes")

    def test_closed_schema_rejects_binding_names_and_container_bypasses(self) -> None:
        forbidden = ("execution_permitted", "candidate_argv", "candidate_path", "candidate_binary", "candidate_executable", "command", "shell", "cwd", "env", "profile", "profile_binding", "freeze", "freeze_manifest_identity", "authorization", "authorization_reference", "r3_activation")
        for name in forbidden:
            with self.subTest(name=name), self.assertRaises(runner.RunnerError) as context:
                runner.run_synthetic([case(**{name: "forbidden"})], {})
            self.assertEqual(context.exception.code, "negative-capability")
        for value in (("tuple",), {"set"}, Path("relative/path"), lambda: None):
            with self.subTest(kind=type(value).__name__), self.assertRaises(runner.RunnerError) as context:
                runner.run_synthetic([case(expected_cause=value)], {})
            self.assertEqual(context.exception.code, "negative-capability")

    def test_failed_precedes_inconclusive(self) -> None:
        failed_case = case("synthetic-fail", expected_class="agree")
        truth = oracle.evaluate_source(failed_case["source"], "translation")
        wrong = wire_response(failed_case, truth, authored=transform(0), derived=transform(10), outcome="agree")
        missing = case("synthetic-missing")
        result = runner.run_synthetic([failed_case, missing], {"synthetic-fail": wrong})
        self.assertEqual(result["counts"]["failed"], 1)
        self.assertEqual(result["counts"]["inconclusive"], 1)
        self.assertEqual(result["status"], "failed")


class ReceiptTests(unittest.TestCase):
    def test_receipt_binds_aggregate_but_cannot_resemble_evidence(self) -> None:
        value = case("synthetic-1", expected_class="agree")
        truth = oracle.evaluate_source(value["source"], "translation")
        result = runner.run_synthetic([value], {"synthetic-1": wire_response(value, truth)})
        first = receipt.build_receipt(result)
        self.assertEqual(first, receipt.build_receipt(result))
        decoded = json.loads(first)
        self.assertEqual(decoded["mode"], "synthetic-validation")
        self.assertFalse(decoded["evidence_eligible"])
        self.assertEqual(decoded["candidate_counts"], {"processes": 0, "requests": 0, "responses": 0})
        self.assertIsNone(decoded["profile_binding"])
        self.assertIsNone(decoded["freeze_manifest_identity"])
        self.assertIsNone(decoded["authorization_reference"])
        self.assertEqual(decoded["r3_activation"], "inactive")
        self.assertEqual(decoded["tool_identities"], [])

    def test_receipt_rejects_fabricated_counts_and_status(self) -> None:
        value = case("synthetic-1")
        result = runner.run_synthetic([value], {})
        for mutation in ("counts", "status", "binding"):
            bad = copy.deepcopy(result)
            if mutation == "counts":
                bad["counts"]["supported"] += 1
            elif mutation == "status":
                bad["status"] = "supported"
            else:
                bad["profile_binding"] = "fabricated"
            with self.subTest(mutation=mutation), self.assertRaises(Exception):
                receipt.build_receipt(bad)

    def test_receipt_rejects_entry_and_extra_response_bound_fabrication(self) -> None:
        base = runner.run_synthetic([], {})
        for entries in (129, 1000):
            bad = copy.deepcopy(base)
            bad["entries"] = [{"status": "inconclusive"} for _ in range(entries)]
            bad["counts"].update({"entries": entries, "inconclusive": entries, "extra_responses": entries})
            bad["status"] = "inconclusive"
            with self.subTest(entries=entries), self.assertRaises(Exception):
                receipt.build_receipt(bad)
        impossible = copy.deepcopy(base)
        impossible["entries"] = [{"status": "inconclusive"}]
        impossible["counts"].update({"entries": 1, "inconclusive": 1, "extra_responses": 0})
        impossible["status"] = "inconclusive"
        with self.assertRaises(Exception):
            receipt.build_receipt(impossible)


if __name__ == "__main__":
    unittest.main()

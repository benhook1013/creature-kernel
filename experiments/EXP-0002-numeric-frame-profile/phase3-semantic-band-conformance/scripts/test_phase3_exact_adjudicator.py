"""Focused tests for exact Phase 3 preparation and adjudication plumbing."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import phase3_evidence_contract as evidence_contract
import phase3_materialized_adapter as adapter
import phase3_exact_adjudicator as exact
import phase3_oracle as oracle
from phase3_common import RESPONSE_PROTOCOL_ID
from test_phase3_materialized_adapter import MaterializedAdapterTests
from test_phase3_oracle_scorer import skipped_response


PACKAGE = Path(__file__).resolve().parents[1]


class ExactAdjudicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._holder = tempfile.TemporaryDirectory()
        cls.package = Path(cls._holder.name) / "phase3"
        shutil.copytree(PACKAGE, cls.package, symlinks=True)
        freeze = cls.package / "manifests/freeze-manifest.json"
        if freeze.exists() and not freeze.is_symlink():
            freeze.chmod(0o644)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._holder.cleanup()

    def prepare(self) -> exact.PreparedAttempt:
        return exact.prepare_exact_attempt(self.package, "attempt-001")

    def copy_package(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        holder = tempfile.TemporaryDirectory()
        destination = Path(holder.name) / "phase3"
        shutil.copytree(PACKAGE, destination, symlinks=True)
        freeze = destination / "manifests/freeze-manifest.json"
        if freeze.exists() and not freeze.is_symlink():
            freeze.chmod(0o644)
        return holder, destination

    def response_for(self, prepared: exact.PreparedAttempt, ordinal: int) -> bytes:
        cases = adapter.load_materialized_cases(self.package)
        raw = MaterializedAdapterTests.response_for(cases[ordinal])
        raw, _ = exact.substitute_request_id(raw, attempt_id=prepared.attempt_id, ordinal=ordinal)
        return raw

    def test_substitution_proves_only_attempt_token_bytes_changed(self) -> None:
        raw = (self.package / "corpora/development.jsonl").read_bytes().splitlines(keepends=True)[0]
        prepared, proof = exact.substitute_request_id(raw, attempt_id="attempt-001", ordinal=0)
        self.assertTrue(proof.only_request_id_changed)
        self.assertEqual(raw[proof.original_changed_start:proof.original_changed_end], b"{attempt_id}")
        self.assertEqual(prepared[proof.prepared_changed_start:proof.prepared_changed_end], b"attempt-001")
        self.assertEqual(raw[:proof.original_changed_start], prepared[:proof.prepared_changed_start])
        self.assertEqual(raw[proof.original_changed_end:], prepared[proof.prepared_changed_end:])
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.substitute_request_id(raw.replace(b"{attempt_id}", b"{attempt_id}{attempt_id}"), attempt_id="attempt-001", ordinal=0)
        self.assertEqual(context.exception.code, "request-id-token")

    def test_three_ordered_cohorts_and_exact_wire_counts(self) -> None:
        prepared = self.prepare()
        self.assertEqual(prepared.total_cases, 60)
        self.assertEqual(prepared.dispatched_count, 57)
        self.assertEqual(prepared.preflight_count, 3)
        self.assertEqual([cohort.role for cohort in prepared.cohorts], ["development", "held-out", "controls"])
        self.assertEqual([len(cohort.requests) for cohort in prepared.cohorts], [8, 40, 9])
        self.assertEqual(prepared.request_ids[0], "p3-attempt-001-000")
        self.assertEqual(prepared.request_ids[-1], "p3-attempt-001-059")
        self.assertEqual([item.ordinal for item in prepared.cohorts[-1].requests], list(range(48, 56)) + [59])

    def test_transport_view_has_no_hidden_labels(self) -> None:
        prepared = self.prepare()
        for cohort in prepared.transport:
            for request in cohort.requests:
                self.assertEqual(set(request.as_dict()), {"ordinal", "request_id", "request_bytes", "request_sha256"})
                wire = request.request_bytes.decode("utf-8")
                self.assertNotIn("expected_class", wire)
                self.assertNotIn("case_id", wire)
                self.assertNotIn("held-out", wire)
        self.assertEqual(len(prepared.transport[1].requests), 40)

    def test_response_correlation_rejects_duplicate_missing_unknown_malformed_and_order_drift(self) -> None:
        prepared = self.prepare()
        first = self.response_for(prepared, 8)
        second = self.response_for(prepared, 9)
        first_id, second_id = prepared.request_ids[8], prepared.request_ids[9]
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, [(first_id, first)], allow_incomplete=False)
        self.assertEqual(context.exception.code, "response-missing")
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, [(first_id, first), (first_id, first)], allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-duplicate-id")
        unknown = second.replace(second_id.encode(), b"p3-attempt-001-999", 1)
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, [(second_id, unknown)], allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-malformed")
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, [("p3-attempt-001-999", unknown)], allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-unknown-id")
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, [(second_id, second), (first_id, first)], allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-order")
        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, [(first_id, b"{}")], allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-malformed")

    def test_response_iterables_have_a_hard_bounded_consumption_limit(self) -> None:
        prepared = self.prepare()

        def frame(request_id: str) -> bytes:
            return (json.dumps({
                "protocol_id": RESPONSE_PROTOCOL_ID,
                "request_id": request_id,
                "status": "observed",
            }, sort_keys=True, separators=(",", ":")) + "\n").encode()

        records = [(request_id, frame(request_id)) for request_id in prepared.request_ids]
        consumed = 0

        def exact_generator():
            nonlocal consumed
            for record in records:
                consumed += 1
                yield record

        observed, missing = exact.correlate_responses(prepared, exact_generator())
        self.assertEqual(consumed, exact.EXPECTED_DISPATCHED_REQUESTS)
        self.assertEqual(len(observed), exact.EXPECTED_DISPATCHED_REQUESTS)
        self.assertEqual(missing, {})

        consumed = 0

        def oversized_generator():
            nonlocal consumed
            for record in records:
                consumed += 1
                yield record
            consumed += 1
            yield prepared.request_ids[0], frame(prepared.request_ids[0])
            raise AssertionError("oversized response generator was consumed past the one extra record")

        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, oversized_generator(), allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-duplicate-id")
        self.assertEqual(consumed, exact.MAX_RESPONSE_ENTRIES)

        consumed = 0

        def infinite_like_generator():
            nonlocal consumed
            while True:
                consumed += 1
                yield prepared.request_ids[0], frame(prepared.request_ids[0])

        with self.assertRaises(exact.ExactAdjudicatorError) as context:
            exact.correlate_responses(prepared, infinite_like_generator(), allow_incomplete=True)
        self.assertEqual(context.exception.code, "response-duplicate-id")
        self.assertEqual(consumed, exact.MAX_RESPONSE_ENTRIES)

    def test_partial_adjudication_has_preflight_controls_and_evidence_contract_shapes(self) -> None:
        prepared = self.prepare()
        response = self.response_for(prepared, 8)
        run = exact.adjudicate_exact(prepared, [(prepared.request_ids[8], response)], allow_incomplete=True)
        self.assertEqual(run.counts, {
            "cases": 60, "development": 8, "held-out": 40, "controls": 12,
            "dispatched": 57, "preflight": 3, "supported": 1, "failed": 0,
            "inconclusive": 56, "observation": 3,
        })
        self.assertEqual(run.adjudications[8].status, "supported")
        self.assertEqual(run.adjudications[8].classification, "agree")
        for ordinal in (56, 57, 58):
            self.assertFalse(run.adjudications[ordinal].dispatch_to_candidate)
            self.assertEqual(run.adjudications[ordinal].classification, "out-of-domain")
            self.assertEqual(run.adjudications[ordinal].status, "observation")
        # Every retained adjudication is accepted by the existing result
        # contract's private per-case validator; no duplicate semantics live
        # in this module.
        for ordinal, item in enumerate(run.evidence_contract_inputs()["adjudications"]):
            evidence_contract._adjudication(item, ordinal, "attempt-001")

    def test_held_out_label_enters_only_post_response_context(self) -> None:
        prepared = self.prepare()
        response = self.response_for(prepared, 8)
        run = exact.adjudicate_exact(prepared, [(prepared.request_ids[8], response)], allow_incomplete=True)
        wire = prepared.cohorts[1].requests[0].request_bytes.decode("utf-8")
        self.assertNotIn('"agree"', wire)
        context = run.adjudications[8].evidence["payload"]["scorer_context"]
        self.assertEqual(context["expected_class"], "agree")
        self.assertEqual(run.adjudications[8].oracle_result["status"], "admitted")
        self.assertEqual(run.adjudications[8].scorer_result["classification"], "agree")

    def test_determinism_and_no_execution_handles(self) -> None:
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first.request_ids, second.request_ids)
        self.assertEqual(first.request_bytes, second.request_bytes)
        self.assertEqual(first.substitution_proofs(), second.substitution_proofs())
        source = Path(exact.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("socket", imports)
        self.assertNotIn("phase3_runner", imports)
        self.assertFalse(hasattr(first, "execute"))

    def test_post_validation_operation_and_held_out_metric_drift_fail_closed(self) -> None:
        for relative in ("corpora/held-out.jsonl", "manifests/recipe-manifest.json"):
            holder, package = self.copy_package()
            try:
                original = adapter.load_materialized_cases

                def mutate_after_validation(root: Path, *, _original=original, _relative=relative):
                    result = _original(root)
                    path = Path(root) / _relative
                    if _relative.startswith("corpora/"):
                        path.write_bytes(path.read_bytes().replace(
                            b'"operation":"observe-authored-conflict"', b'"operation":"drifted-operation"', 1))
                    else:
                        recipe = json.loads(path.read_text(encoding="utf-8"))
                        recipe["cases"][8]["metric"] = "rotation"
                        path.write_text(json.dumps(recipe, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
                    return result

                adapter.load_materialized_cases = mutate_after_validation
                with self.assertRaises(exact.ExactAdjudicatorError) as context:
                    exact.prepare_exact_attempt(package, "attempt-001")
                self.assertEqual(context.exception.code, "package-snapshot")
            finally:
                adapter.load_materialized_cases = original
                holder.cleanup()

    def test_post_validation_symlink_drift_fails_closed(self) -> None:
        holder, package = self.copy_package()
        path = package / "corpora/controls.jsonl"
        backup = package / "controls.saved"
        original = adapter.load_materialized_cases
        try:
            def mutate_after_validation(root: Path):
                result = original(root)
                source = Path(root) / "corpora/controls.jsonl"
                source.rename(backup)
                source.symlink_to(backup)
                return result

            adapter.load_materialized_cases = mutate_after_validation
            with self.assertRaises(exact.ExactAdjudicatorError) as context:
                exact.prepare_exact_attempt(package, "attempt-001")
            self.assertEqual(context.exception.code, "package-snapshot")
        finally:
            adapter.load_materialized_cases = original
            holder.cleanup()

    def test_post_validation_artifact_hash_drift_fails_closed(self) -> None:
        holder, package = self.copy_package()
        original = adapter.load_materialized_cases
        try:
            def mutate_after_validation(root: Path):
                result = original(root)
                path = Path(root) / "manifests/artifact-manifest.json"
                raw = path.read_bytes()
                old = b'"sha256":"9abba94abab5b0b8384bc90ae58c9b11c2bfa0f998ef259e94d06dd8c5acc7b7"'
                new = b'"sha256":"8abba94abab5b0b8384bc90ae58c9b11c2bfa0f998ef259e94d06dd8c5acc7b7"'
                self.assertEqual(raw.count(old), 1)
                path.write_bytes(raw.replace(old, new, 1))
                return result

            adapter.load_materialized_cases = mutate_after_validation
            with self.assertRaises(exact.ExactAdjudicatorError) as context:
                exact.prepare_exact_attempt(package, "attempt-001")
            self.assertEqual(context.exception.code, "package-snapshot")
        finally:
            adapter.load_materialized_cases = original
            holder.cleanup()

    def test_all_typed_controls_use_recipe_expectations_and_scorer_semantics(self) -> None:
        prepared = self.prepare()
        cases = adapter.load_materialized_cases(self.package)
        responses = []
        for ordinal in range(52, 56):
            truth = oracle.evaluate_source(cases[ordinal]["source"], cases[ordinal]["metric"])
            raw = skipped_response(cases[ordinal], truth)
            raw, _ = exact.substitute_request_id(raw, attempt_id="attempt-001", ordinal=ordinal)
            responses.append((prepared.request_ids[ordinal], raw))
        negative = prepared._cases[59]
        negative_id = negative.transport_request.request_id
        response = {
            "protocol_id": RESPONSE_PROTOCOL_ID,
            "request_id": negative_id,
            "status": "rejected",
            "error": negative.typed_expectation["error"],
            "cause": negative.typed_expectation["cause"],
        }
        responses.append((negative_id, (json.dumps(response, sort_keys=True, separators=(",", ":")) + "\n").encode()))
        run = exact.adjudicate_exact(prepared, responses, allow_incomplete=True)
        for ordinal in range(52, 56):
            self.assertEqual((run.adjudications[ordinal].status, run.adjudications[ordinal].classification), ("observation", "skipped"))
            self.assertEqual(run.adjudications[ordinal].cause, prepared._cases[ordinal].typed_expectation["cause"])
        self.assertEqual((run.adjudications[59].status, run.adjudications[59].classification), ("observation", "rejected"))
        for ordinal in [52, 53, 54, 55, 59]:
            evidence_contract._adjudication(run.evidence_contract_inputs()["adjudications"][ordinal], ordinal, "attempt-001")

        bad = json.loads(responses[0][1].decode())
        bad["observations"]["members"][0]["outcome"] = "compared"
        bad_raw = (json.dumps(bad, sort_keys=True, separators=(",", ":")) + "\n").encode()
        bad_run = exact.adjudicate_exact(prepared, [(prepared.request_ids[52], bad_raw)], allow_incomplete=True)
        self.assertEqual((bad_run.adjudications[52].status, bad_run.adjudications[52].classification), ("failed", "skipped"))


if __name__ == "__main__":
    unittest.main()

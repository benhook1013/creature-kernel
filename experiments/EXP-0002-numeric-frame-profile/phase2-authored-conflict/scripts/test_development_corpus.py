from __future__ import annotations

import copy
import hashlib
import unittest
from decimal import Decimal
from pathlib import Path

import development_corpus as corpus


def loaded() -> dict[str, object]:
    return corpus.load_development_corpus()


class DevelopmentCorpusTests(unittest.TestCase):
    def test_regular_file_read_is_capped_at_limit_plus_one(self) -> None:
        class ProbePath:
            parent = None

            def __init__(self) -> None:
                self.requested: int | None = None
                self.parent = self

            def is_symlink(self) -> bool:
                return False

            def is_file(self) -> bool:
                return True

            def open(self, mode: str) -> "ProbePath":
                self.assert_mode = mode
                return self

            def __enter__(self) -> "ProbePath":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, size: int) -> bytes:
                self.requested = size
                return b"x" * size

        probe = ProbePath()
        with self.assertRaisesRegex(corpus.CorpusValidationError, "file-too-large"):
            corpus._read_regular(probe, 31, "probe")
        self.assertEqual(probe.requested, 32)

    def test_source_bound_matches_candidate_transport(self) -> None:
        self.assertEqual(corpus.MAX_SOURCE_BYTES, 24 * 1024)
        for case in loaded()["cases"]:
            self.assertLessEqual(len(corpus.materialize_case(case)), 24 * 1024)

    def test_case_ids_and_profile_expectation_coverage_are_closed(self) -> None:
        value = loaded()
        cases = value["cases"]
        self.assertEqual(len(cases), 16)
        self.assertEqual(
            {case["case_id"] for case in cases},
            {
                "baseline-equation-agree",
                "translation-strict-boundary",
                "translation-strict-nextafter",
                "translation-micro-boundary",
                "translation-micro-nextafter",
                "translation-stress-boundary",
                "translation-stress-nextafter",
                "translation-broad-conflict",
                "quaternion-sign-equivalence",
                "rotation-strict-vs-wide",
                "rotation-wide-vs-stress",
                "arithmetic-provider-unavailable",
                "gate-input-reject",
                "sqrt-provider-unavailable",
                "zero-quaternion-input",
                "negative-relative-override",
            },
        )
        for case in cases:
            self.assertEqual(set(case["expected"]), set(corpus.PROFILE_IDS))
            for expectation in case["expected"].values():
                self.assertIn(expectation["classification"], {"agree", "conflict", "skipped", "rejected"})

    def test_materialization_is_deterministic_and_hash_bound(self) -> None:
        case = loaded()["cases"][1]
        first = corpus.materialize_case(case)
        second = corpus.materialize_case(case)
        self.assertEqual(first, second)
        self.assertEqual(hashlib.sha256(first).hexdigest(), case["materialized_sha256"])
        self.assertIn(b'"rotation_xyzw"', first)

    def test_missing_type_and_duplicate_mutations_fail_closed(self) -> None:
        case = copy.deepcopy(loaded()["cases"][0])
        case["mutations"] = [{"op": "replace", "path": "/body/no-such", "value": 1}]
        with self.assertRaisesRegex(corpus.CorpusValidationError, "missing-path"):
            corpus.materialize_case(case)

        case["mutations"] = [{"op": "replace", "path": "/body/parts/0", "value": 1}]
        with self.assertRaisesRegex(corpus.CorpusValidationError, "replacement-type"):
            corpus.materialize_case(case)

        case["mutations"] = [
            {"op": "replace", "path": "/body/parts/16/placement/translation/2", "value": 0},
            {"op": "replace", "path": "/body/parts/16/placement/translation/2", "value": 0},
        ]
        with self.assertRaisesRegex(corpus.CorpusValidationError, "duplicate-mutation"):
            corpus.materialize_case(case)

    def test_fixture_and_materialized_hash_mismatch_fail_closed(self) -> None:
        value = loaded()
        fixture_case = copy.deepcopy(value["cases"][0])
        fixture_case["base_fixture"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(corpus.CorpusValidationError, "fixture-identity"):
            corpus._validate_case(fixture_case, 0, corpus.REPO_ROOT)

        changed = copy.deepcopy(value["cases"][0])
        changed["materialized_sha256"] = "0" * 64
        with self.assertRaisesRegex(corpus.CorpusValidationError, "materialized-hash-mismatch"):
            corpus._validate_case(changed, 0, corpus.REPO_ROOT)

    def test_materialized_translation_value_is_bound_to_oracle_bits(self) -> None:
        value = copy.deepcopy(loaded())
        case = next(case for case in value["cases"] if case["case_id"] == "translation-strict-boundary")
        case["mutations"][1]["value"] = 999
        case["materialized_sha256"] = hashlib.sha256(corpus.materialize_case(case)).hexdigest()
        with self.assertRaisesRegex(corpus.CorpusValidationError, "mutation-contract"):
            corpus.validate_corpus(value)

    def test_translation_oracle_identity_and_rotation_value_are_closed(self) -> None:
        value = copy.deepcopy(loaded())
        translation = next(case for case in value["cases"] if case["case_id"] == "translation-strict-boundary")
        translation["oracle"]["data"]["candidate_id"] = "micro"
        with self.assertRaisesRegex(corpus.CorpusValidationError, "oracle-contract|boundary-fraction"):
            corpus.validate_corpus(value)

        value = copy.deepcopy(loaded())
        rotation = next(case for case in value["cases"] if case["case_id"] == "rotation-strict-vs-wide")
        rotation["oracle"]["data"]["z"] = Decimal("0.0001")
        with self.assertRaisesRegex(corpus.CorpusValidationError, "mutation-contract|oracle-contract|oracle-expectation"):
            corpus.validate_corpus(value)

    def test_non_oracle_expected_contract_is_closed(self) -> None:
        value = copy.deepcopy(loaded())
        case = next(case for case in value["cases"] if case["case_id"] == "arithmetic-provider-unavailable")
        for expectation in case["expected"].values():
            expectation["classification"] = "agree"
            expectation["cause"] = None
        with self.assertRaisesRegex(corpus.CorpusValidationError, "expected-contract"):
            corpus.validate_corpus(value)

    def test_malformed_oracle_bits_fail_with_stable_errors(self) -> None:
        for bits, error in (
            ("0x1234", "bits-format"),
            ("0x7ff0000000000000", "nonfinite-value"),
            ("0x8000000000000000", "negative-value"),
        ):
            with self.subTest(bits=bits):
                value = copy.deepcopy(loaded())
                case = next(case for case in value["cases"] if case["case_id"] == "translation-strict-boundary")
                case["oracle"]["data"]["value_bits"] = bits
                with self.assertRaisesRegex(corpus.CorpusValidationError, error):
                    corpus.validate_corpus(value)

    def test_exact_boundary_and_immediate_successor_bit_proof(self) -> None:
        for candidate_id in corpus.profile_sweep.CANDIDATE_IDS:
            boundary = corpus.translation_boundary(candidate_id)
            below = corpus._boundary_float(candidate_id, "at-or-below")
            above = corpus._boundary_float(candidate_id, "nextafter-above")
            self.assertLessEqual(corpus.Fraction.from_float(below), boundary)
            self.assertGreater(corpus.Fraction.from_float(above), boundary)
            self.assertEqual(above, corpus.math.nextafter(below, corpus.math.inf))
            self.assertTrue(corpus._translation_agrees(below, candidate_id))
            self.assertFalse(corpus._translation_agrees(above, candidate_id))

    def test_rotation_oracle_requires_and_uses_a_conservative_margin(self) -> None:
        value = loaded()
        first = next(case for case in value["cases"] if case["case_id"] == "rotation-strict-vs-wide")
        z = first["oracle"]["data"]["z"]
        self.assertGreaterEqual(corpus._rotation_margin(z, "strict"), corpus.MIN_ROTATION_MARGIN)
        self.assertFalse(corpus._rotation_agrees(z, "strict"))
        self.assertTrue(corpus._rotation_agrees(z, "micro"))
        changed = copy.deepcopy(value)
        changed_case = next(case for case in changed["cases"] if case["case_id"] == "rotation-strict-vs-wide")
        changed_case["oracle"]["data"]["min_margin"] = Decimal("1")
        with self.assertRaisesRegex(corpus.CorpusValidationError, "rotation-margin"):
            corpus.validate_corpus(changed)

    def test_negative_override_is_retained_as_top_level_rejection(self) -> None:
        case = next(case for case in loaded()["cases"] if case["case_id"] == "negative-relative-override")
        self.assertEqual(case["tolerance_override"], {"translation_relative": -1})
        for expectation in case["expected"].values():
            self.assertEqual(expectation["classification"], "rejected")
            self.assertEqual(expectation["cause"]["failure"], "negative")


if __name__ == "__main__":
    unittest.main()

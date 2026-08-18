#!/usr/bin/env python3
"""Focused proof tests for the additive development extension."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from fractions import Fraction
from pathlib import Path

import development_extension_corpus as corpus


class DevelopmentExtensionCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = corpus.load_development_extension_corpus()

    @staticmethod
    def _source(case):
        return corpus._parse_json(corpus.materialize_case(case))

    def test_schema_identity_variant_and_exact_order(self) -> None:
        self.assertEqual(self.value["schema"], corpus.SCHEMA)
        self.assertEqual(self.value["corpus_id"], corpus.CORPUS_ID)
        self.assertEqual(self.value["parent_corpus_id"], corpus.PARENT_CORPUS_ID)
        self.assertEqual(self.value["corpus_role"], "development")
        self.assertEqual(self.value["variant"]["id"], "descendant-tail-end-v1")
        self.assertEqual([case["case_id"] for case in self.value["cases"]], list(corpus.CASE_IDS))

    def test_deterministic_materialization_and_hashes(self) -> None:
        for case in self.value["cases"]:
            first = corpus.materialize_case(case)
            second = corpus.materialize_case(case)
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first).hexdigest(), case["materialized_sha256"])
            self.assertEqual(len(first), case["source_bytes"])
        identity = self.value["corpus_identity"]
        without_identity = dict(self.value)
        without_identity.pop("corpus_identity")
        canonical = (corpus._canonical_json(without_identity) + "\n").encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), identity["content_sha256"])

    def test_variant_has_19_part_descendant_chain_and_descendant_mating_owner(self) -> None:
        source = self._source(self.value["cases"][0])
        parts = source["body"]["parts"]
        self.assertEqual(len(parts), 19)
        by_role = {part["address"]["role"]: part for part in parts}
        self.assertEqual(by_role["tail_root"]["containment"]["parent"]["role"], "pelvis")
        self.assertEqual(by_role["tail_tip"]["containment"]["parent"]["role"], "tail_root")
        self.assertEqual(by_role["tail_end"]["containment"]["parent"]["role"], "tail_tip")
        self.assertEqual(by_role["tail_end"]["address"]["anchors"], ["tail", "end"])
        sockets = source["body"]["sockets"]
        mating = next(s for s in sockets if s["address"]["anchors"] == ["tail"])
        self.assertEqual(mating["owner"]["role"], "tail_end")
        self.assertEqual(mating["owner"]["anchors"], ["tail", "end"])
        self.assertEqual(len(source["body"]["joints"]), 18)

    def test_noncanonical_basis_and_fixed_transform_recipe(self) -> None:
        source = self._source(self.value["cases"][0])
        self.assertEqual(source["basis"], {"length_unit": "centimetre", "handedness": "left", "up": "+z", "forward": "+x"})
        body = source["body"]
        parts = {p["address"]["role"]: p for p in body["parts"]}
        sockets = body["sockets"]
        host = next(s for s in sockets if not s["address"]["anchors"])
        mating = next(s for s in sockets if s["address"]["anchors"] == ["tail"])
        attachment = body["attachments"][0]
        # Every fixed transform in the recipe is nonidentity; the root x is the
        # sole per-case source token and its rotation remains fixed.
        self.assertEqual([str(value) for value in parts["tail_root"]["placement"]["translation"][1:]], ["-50", "112.5"])
        self.assertEqual(parts["tail_root"]["placement"]["rotation_xyzw"], [0, 1, 0, 0])
        self.assertEqual([str(value) for value in parts["tail_tip"]["placement"]["translation"]], ["12.5", "25", "37.5"])
        self.assertEqual(parts["tail_tip"]["placement"]["rotation_xyzw"], [0, 0, 1, 0])
        self.assertEqual([str(value) for value in parts["tail_end"]["placement"]["translation"]], ["25", "12.5", "37.5"])
        self.assertEqual(parts["tail_end"]["placement"]["rotation_xyzw"], [1, 0, 0, 0])
        self.assertEqual([str(value) for value in host["interface_frame"]["translation"]], ["50", "12.5", "37.5"])
        self.assertEqual(host["interface_frame"]["rotation_xyzw"], [0, 0, 1, 0])
        self.assertEqual([str(value) for value in mating["interface_frame"]["translation"]], ["12.5", "25", "37.5"])
        self.assertEqual(mating["interface_frame"]["rotation_xyzw"], [0, 1, 0, 0])
        self.assertEqual([str(value) for value in attachment["offset"]["translation"]], ["12.5", "25", "37.5"])
        self.assertEqual(attachment["offset"]["rotation_xyzw"], [1, 0, 0, 0])

    def test_only_root_x_source_token_varies(self) -> None:
        sources = [self._source(case) for case in self.value["cases"]]
        roots = [next(p for p in source["body"]["parts"] if p["address"]["role"] == "tail_root") for source in sources]
        self.assertEqual(len({root["placement"]["translation"][0] for root in roots}), 6)
        for root in roots:
            root["placement"]["translation"][0] = "<varying-root-x>"
        self.assertTrue(all(source == sources[0] for source in sources[1:]))

    def test_exact_boundary_successor_source_binding_and_inequalities(self) -> None:
        totals = {"agree": 0, "conflict": 0}
        for index, case in enumerate(self.value["cases"]):
            candidate, direction = case["case_id"].split("-")
            target = corpus._bits_fraction(case["target_bits"])
            boundary = corpus.boundary_fraction(candidate)
            self.assertEqual(Fraction(case["boundary_fraction"]), boundary)
            if direction == "boundary":
                self.assertLessEqual(target, boundary)
                self.assertLess(boundary, corpus._bits_fraction(corpus._bits_text(int(case["target_bits"][2:], 16) + 1)))
            else:
                self.assertLess(boundary, target)
                self.assertLessEqual(corpus._bits_fraction(corpus._bits_text(int(case["target_bits"][2:], 16) - 1)), boundary)
            self.assertEqual(corpus.exact_rn_even_bits(corpus._fraction_number(case["source_token"]) / 100), int(case["target_bits"][2:], 16))
            for profile_id, expected in case["expected"].items():
                profile = next(key for key, value in corpus.PROFILE_IDS.items() if value == profile_id)
                a = corpus._profile_fraction(profile, "A")
                r = corpus._profile_fraction(profile, "R")
                actual = "agree" if abs(target - corpus.DERIVED_COMPONENT) <= a + r * max(abs(target), abs(corpus.DERIVED_COMPONENT)) else "conflict"
                self.assertEqual(expected["classification"], actual)
                self.assertIsNone(expected["cause"])
                totals[actual] += 1
        self.assertEqual(totals, {"agree": 9, "conflict": 9})

    def test_source_and_resource_limits(self) -> None:
        self.assertEqual(self.value["limits"]["source_bytes"], corpus.MAX_SOURCE_BYTES)
        self.assertEqual(self.value["limits"]["resource_bytes"], corpus.MAX_RESOURCE_BYTES)
        self.assertLessEqual(corpus.CORPUS_PATH.stat().st_size, corpus.MAX_CORPUS_BYTES)
        self.assertTrue(all(case["source_bytes"] <= corpus.MAX_SOURCE_BYTES for case in self.value["cases"]))

    def test_unknown_variant_rejected(self) -> None:
        case = copy.deepcopy(self.value["cases"][0])
        case["variant_id"] = "arbitrary-patch-language"
        with self.assertRaises(corpus.CorpusValidationError) as context:
            corpus.materialize_case(case)
        self.assertEqual(context.exception.code, "unknown-variant")

    def test_original_16_case_corpus_raw_hash_unchanged(self) -> None:
        old = corpus.PACKAGE / "corpora" / "development" / "corpus.json"
        self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(), "4a9f67949f1278ce4ab14a8e8c6cbf7503d8b688c084d2c6ee4a7bc70a819c28")


if __name__ == "__main__":
    unittest.main()

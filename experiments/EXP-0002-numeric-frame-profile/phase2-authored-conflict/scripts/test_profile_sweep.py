from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import profile_sweep


PACKAGE = Path(__file__).resolve().parents[1]
DEFINITION = PACKAGE / "profiles" / "development-sweep.json"


def fresh_definition() -> dict[str, object]:
    return json.loads(DEFINITION.read_text(encoding="utf-8"))


def write_definition(root: Path, value: object, name: str = "definition.json") -> Path:
    path = root / name
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
    return path


class ProfileSweepTests(unittest.TestCase):
    def test_valid_definition_has_exact_order_and_no_selection(self) -> None:
        definition = profile_sweep.load_profile_sweep(DEFINITION)
        self.assertEqual(definition["schema"], profile_sweep.SCHEMA)
        self.assertEqual(definition["sweep_id"], profile_sweep.SWEEP_ID)
        self.assertEqual(definition["definition_id"], profile_sweep.DEFINITION_ID)
        self.assertEqual(definition["selected_profile_id"], None)
        self.assertEqual(definition["r3_activation"], "inactive")
        self.assertEqual(
            [candidate["candidate_id"] for candidate in definition["candidates"]],
            ["strict", "micro", "stress"],
        )
        self.assertEqual(
            [candidate["profile_id"] for candidate in definition["candidates"]],
            [
                "ck.provisional-r3-authored-conflict.dev.strict-1",
                "ck.provisional-r3-authored-conflict.dev.micro-1",
                "ck.provisional-r3-authored-conflict.dev.stress-1",
            ],
        )

    def test_candidate_profile_identity_is_exact(self) -> None:
        definition = fresh_definition()
        definition["candidates"][1]["profile_id"] = "ck.provisional-r3-authored-conflict.dev.other-1"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "profile-id-mismatch"):
                profile_sweep.load_profile_sweep(write_definition(Path(temporary), definition))

    def test_object_member_order_is_not_semantic(self) -> None:
        definition = fresh_definition()

        def reverse_objects(value: object) -> object:
            if isinstance(value, dict):
                return {key: reverse_objects(child) for key, child in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse_objects(child) for child in value]
            return value

        with tempfile.TemporaryDirectory() as temporary:
            path = write_definition(Path(temporary), reverse_objects(definition), "reordered.json")
            self.assertEqual(profile_sweep.load_profile_sweep(path)["sweep_id"], profile_sweep.SWEEP_ID)

    def test_mutation_is_rejected_without_repair(self) -> None:
        definition = fresh_definition()
        definition["selected_profile_id"] = "strict"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "selection-present"):
                profile_sweep.load_profile_sweep(write_definition(Path(temporary), definition))

    def test_duplicate_key_is_rejected(self) -> None:
        raw = '{"schema":"%s","schema":"%s"}\n' % (profile_sweep.SCHEMA, profile_sweep.SCHEMA)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "duplicate-key"):
                profile_sweep.load_profile_sweep(path)

    def test_bit_decimal_mismatch_is_rejected(self) -> None:
        definition = fresh_definition()
        definition["candidates"][0]["constants"]["A"]["bits"] = "0x3cf0000000000001"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "bits-decimal-mismatch"):
                profile_sweep.load_profile_sweep(write_definition(Path(temporary), definition))

    def test_candidate_order_is_semantic_and_rejected(self) -> None:
        definition = fresh_definition()
        definition["candidates"] = [definition["candidates"][1], definition["candidates"][0], definition["candidates"][2]]
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "candidate-order"):
                profile_sweep.load_profile_sweep(write_definition(Path(temporary), definition))

    def test_extra_field_is_rejected(self) -> None:
        definition = fresh_definition()
        definition["candidates"][0]["unexpected"] = True
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "extra-field"):
                profile_sweep.load_profile_sweep(write_definition(Path(temporary), definition))

    def test_file_and_candidate_record_bounds_are_rejected(self) -> None:
        definition = fresh_definition()
        definition["candidates"].append(copy.deepcopy(definition["candidates"][0]))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "record-limit"):
                profile_sweep.load_profile_sweep(write_definition(Path(temporary), definition))

            oversized = Path(temporary) / "oversized.json"
            oversized.write_bytes(b" " * (profile_sweep.MAX_DEFINITION_BYTES + 1))
            with self.assertRaisesRegex(profile_sweep.SweepValidationError, "file-too-large"):
                profile_sweep.load_profile_sweep(oversized)


if __name__ == "__main__":
    unittest.main()

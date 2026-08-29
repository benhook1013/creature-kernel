from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
DEFAULTS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
ALTERNATE = ("slender_long_limb", "stocky_broad_chested")
SOURCE_POSE = Path(__file__).resolve().parents[1] / "current-form-surface-preview" / "structural_embodiment_shared_pose.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


neutral = load_module(
    "neutral_structural_gallery_smoke_for_semantic_pose_command_tests",
    EXPERIMENT / "run_structural_gallery_smoke.py",
)
sys.modules["run_structural_gallery_smoke"] = neutral
carrier = load_module("disposable_avatar_carrier_for_semantic_pose_command_tests", EXPERIMENT / "disposable_avatar_carrier.py")
command = load_module("disposable_semantic_pose_command_under_test", EXPERIMENT / "disposable_semantic_pose_command.py")


def _fixture(profile_ids: tuple[str, str] = DEFAULTS) -> dict:
    source = json.loads(SOURCE_POSE.read_text(encoding="utf-8"))
    return {
        "schema": command.SCHEMA,
        "boundary": command.BOUNDARY,
        "command_id": command.COMMAND_ID,
        "command_version": command.COMMAND_VERSION,
        "source_pose": {
            "format": source["format"],
            "pose_id": source["pose_id"],
            "sha256": hashlib.sha256(SOURCE_POSE.read_bytes()).hexdigest(),
            "version": source["version"],
        },
        "targets": [
            {"instance_id": "avatar-left", "profile_id": profile_ids[0], "candidate_profile_sha256": "a" * 64},
            {"instance_id": "avatar-right", "profile_id": profile_ids[1], "candidate_profile_sha256": "b" * 64},
        ],
        "rules": [
            {
                "kind": rule["kind"],
                "role": rule["role"],
                "anchors": rule["anchors"],
                "rotation_xyzw": rule["rotation_xyzw"],
            }
            for rule in source["rules"]
        ],
        "identity_frame": deepcopy(command.IDENTITY_FRAME),
    }


class DisposableSemanticPoseCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-disposable-semantic-pose-command-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_exact_shape_reuses_semantic_selectors_and_has_no_host_fields(self) -> None:
        value = _fixture()
        self.assertIs(command._validate_shape(value), value)
        self.assertEqual(tuple(value), command.COMMAND_KEYS)
        self.assertEqual(len(value["targets"]), 2)
        self.assertEqual(len(value["rules"]), command.RULE_COUNT)
        self.assertEqual(value["identity_frame"]["vectors"], "column")
        self.assertEqual(value["identity_frame"]["rotation_storage"], "xyzw")
        self.assertEqual(value["identity_frame"]["C"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        self.assertEqual(value["identity_frame"]["s"], 1.0)
        self.assertTrue(value["identity_frame"]["evidence_only"])
        self.assertFalse(value["identity_frame"]["runtime_conformance"])
        serialized = json.dumps(value, sort_keys=True).casefold()
        for forbidden in ("godot", "bone_index", "animation_clip", "node_name"):
            self.assertNotIn(forbidden, serialized)

    def test_selector_keys_are_structural_when_fields_contain_delimiters(self) -> None:
        value = _fixture()
        value["rules"][0].update({"kind": "joint|semantic", "role": "wrist", "anchors": ["right"]})
        value["rules"][1].update({"kind": "joint", "role": "semantic|wrist", "anchors": ["right"]})
        self.assertIs(command._validate_shape(value), value)

    def test_command_version_uses_value_equality_for_strict_ints(self) -> None:
        value = _fixture()
        with patch.object(command, "COMMAND_VERSION", 1000):
            value["command_version"] = int("1000")
            self.assertIsNot(value["command_version"], command.COMMAND_VERSION)
            self.assertIs(command._validate_shape(value), value)

    def test_canonical_bytes_and_load_are_deterministic_for_both_frozen_pairs(self) -> None:
        for profile_ids in (DEFAULTS, ALTERNATE):
            with self.subTest(profile_ids=profile_ids):
                first = _fixture(profile_ids)
                second = _fixture(profile_ids)
                first_bytes = command._canonical_json(first)
                second_bytes = command._canonical_json(second)
                self.assertEqual(first_bytes, second_bytes)
                first_path = self.root / f"{'-'.join(profile_ids)}-first.json"
                second_path = self.root / f"{'-'.join(profile_ids)}-second.json"
                first_path.write_bytes(first_bytes)
                second_path.write_bytes(second_bytes)
                self.assertEqual(command.load_command(first_path), command.load_command(second_path))
                self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_safe_atomic_command_publication_and_identity_are_deterministic(self) -> None:
        value = _fixture()
        first_path = self.root / "first.json"
        second_path = self.root / "second.json"
        command.write_command(first_path, value)
        command.write_command(second_path, value)
        self.assertEqual(first_path.read_bytes(), command._canonical_json(value))
        self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        self.assertEqual(command.command_identity(value), command.command_identity(command.load_command(first_path)))
        with self.assertRaises(command.CommandError):
            command.write_command(first_path, value)

    def test_shape_rejects_unknown_fields_non_strings_duplicate_selectors_bad_rotation_and_bad_frame(self) -> None:
        mutations = []
        extra = _fixture()
        extra["unexpected"] = False
        mutations.append(extra)
        non_string_target = _fixture()
        non_string_target["targets"][0]["profile_id"] = 1
        mutations.append(non_string_target)
        duplicate_target = _fixture()
        duplicate_target["targets"][1]["instance_id"] = duplicate_target["targets"][0]["instance_id"]
        mutations.append(duplicate_target)
        extra_rule = _fixture()
        extra_rule["rules"][0]["host_bone"] = "forbidden"
        mutations.append(extra_rule)
        duplicate_rule = _fixture()
        duplicate_rule["rules"][1]["kind"] = duplicate_rule["rules"][0]["kind"]
        duplicate_rule["rules"][1]["role"] = duplicate_rule["rules"][0]["role"]
        duplicate_rule["rules"][1]["anchors"] = duplicate_rule["rules"][0]["anchors"]
        mutations.append(duplicate_rule)
        non_unit = _fixture()
        non_unit["rules"][0]["rotation_xyzw"] = [0.0, 0.0, 0.0, 0.0]
        mutations.append(non_unit)
        non_finite = _fixture()
        non_finite["rules"][0]["rotation_xyzw"][0] = float("nan")
        mutations.append(non_finite)
        overflowing = _fixture()
        overflowing["rules"][0]["rotation_xyzw"][0] = 10**1000
        mutations.append(overflowing)
        bad_frame = _fixture()
        bad_frame["identity_frame"]["C"][0][1] = 1.0
        mutations.append(bad_frame)
        bad_scale = _fixture()
        bad_scale["identity_frame"]["s"] = 1
        mutations.append(bad_scale)
        oversized = _fixture()
        oversized["source_pose"]["pose_id"] = "x" * (command.MAX_IDENTIFIER_BYTES + 1)
        mutations.append(oversized)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(command.CommandError):
                command._validate_shape(value)
        for api in (command.command_identity, command.semantic_payload):
            with self.subTest(api=api.__name__), self.assertRaises(command.CommandError):
                api(oversized)

    def test_load_rejects_noncanonical_command_and_validate_rejects_mismatch(self) -> None:
        value = _fixture()
        noncanonical = self.root / "noncanonical.json"
        noncanonical.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(command.CommandError, "not canonical"):
            command.load_command(noncanonical)
        changed = deepcopy(value)
        changed["targets"][0]["profile_id"] = "wrong-profile"
        with (
            patch.object(command, "build_command", return_value=value),
            self.assertRaisesRegex(command.CommandError, "does not exactly match"),
        ):
            command.validate_command(changed, self.root, self.root / "carrier.json")

    def test_real_source_target_and_rule_lineage_mismatches_are_rejected(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"cached completed gallery unavailable: {GALLERY}")
        carrier_path = self.root / "lineage-carrier.json"
        carrier.write_carrier(
            carrier_path,
            carrier.build_carrier(GALLERY, DEFAULTS, ("lineage-left", "lineage-right")),
        )
        expected = command.build_command(GALLERY, carrier_path)
        mutations = []
        wrong_source = deepcopy(expected)
        wrong_source["source_pose"]["sha256"] = "0" * 64
        mutations.append(wrong_source)
        wrong_target = deepcopy(expected)
        wrong_target["targets"][0]["candidate_profile_sha256"] = "1" * 64
        mutations.append(wrong_target)
        reordered_targets = deepcopy(expected)
        reordered_targets["targets"].reverse()
        mutations.append(reordered_targets)
        reordered_rules = deepcopy(expected)
        reordered_rules["rules"][0], reordered_rules["rules"][1] = (
            reordered_rules["rules"][1],
            reordered_rules["rules"][0],
        )
        mutations.append(reordered_rules)
        changed_rotation = deepcopy(expected)
        changed_rotation["rules"][0]["rotation_xyzw"] = [
            1.0e-6,
            0.0,
            0.0,
            math.sqrt(1.0 - 1.0e-12),
        ]
        mutations.append(changed_rotation)
        with patch.object(command, "build_command", return_value=expected):
            for value in mutations:
                with self.subTest(value=value), self.assertRaisesRegex(command.CommandError, "does not exactly match"):
                    command.validate_command(value, GALLERY, carrier_path)

    def test_cli_build_and_validate_paths_use_canonical_command(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"cached completed gallery unavailable: {GALLERY}")
        for label, profile_ids in (("default", DEFAULTS), ("alternate", ALTERNATE)):
            with self.subTest(profile_ids=profile_ids):
                carrier_path = self.root / f"{label}-carrier.json"
                command_path = self.root / f"{label}-command.json"
                instance_ids = (f"{label}-left", f"{label}-right")
                carrier.write_carrier(
                    carrier_path,
                    carrier.build_carrier(GALLERY, profile_ids, instance_ids),
                )
                with patch.dict(os.environ, {"CK_CURRENT_FORM_SURFACE_TMPDIR": "/tmp"}), redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        command.main(
                            [
                                "build",
                                "--gallery",
                                str(GALLERY),
                                "--carrier",
                                str(carrier_path),
                                "--output",
                                str(command_path),
                            ]
                        ),
                        0,
                    )
                    self.assertEqual(
                        command.main(
                            [
                                "validate",
                                "--gallery",
                                str(GALLERY),
                                "--carrier",
                                str(carrier_path),
                                "--command",
                                str(command_path),
                            ]
                        ),
                        0,
                    )
                loaded = command.load_command(command_path)
                self.assertEqual(tuple(target["instance_id"] for target in loaded["targets"]), instance_ids)
                self.assertEqual(tuple(target["profile_id"] for target in loaded["targets"]), profile_ids)


def redirect_stdout(stream):
    return patch("sys.stdout", stream)


if __name__ == "__main__":
    unittest.main()

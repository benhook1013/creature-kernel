from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
DEFAULTS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
ALTERNATE = ("slender_long_limb", "stocky_broad_chested")
INSTANCE_IDS = ("avatar-one", "avatar-two")
POSE_BYTES = b'{"pose_id":"test-pose","rules":[]}\n'
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_module("run_structural_gallery_smoke_for_carrier_tests", EXPERIMENT / "run_structural_gallery_smoke.py")
sys.modules["run_structural_gallery_smoke"] = smoke
carrier = load_module("disposable_avatar_carrier_under_test", EXPERIMENT / "disposable_avatar_carrier.py")


def _payload(profile_ids: tuple[str, str], pose_sha256: str) -> dict:
    profiles = []
    for profile_id in profile_ids:
        artifacts = []
        for artifact_name in smoke.EXPECTED_ARTIFACT_NAMES:
            artifact_path = f"{profile_id}/{artifact_name}"
            artifacts.append(
                {
                    "path": artifact_path,
                    "sha256": hashlib.sha256(artifact_path.encode("ascii")).hexdigest(),
                    "bytes": len(artifact_path),
                }
            )
        profiles.append(
            {
                "profile_id": profile_id,
                "label": f"Fixture {profile_id}",
                "candidate_profile_sha256": hashlib.sha256(profile_id.encode("ascii")).hexdigest(),
                "artifacts": artifacts,
                "metrics": {
                    "format": "creature-kernel.disposable-structural-embodiment-gallery.v1",
                    "profile_id": profile_id,
                    "neutral_vertex_count": 3,
                    "posed_vertex_count": 3,
                    "face_count": 1,
                    "bone_count": 18,
                    "proxy_count": 18,
                    "neutral_bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
                    "posed_bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
                    "pose_rule_count": 18,
                    "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
                    "gallery_global_world_bound": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
                },
            }
        )
    return {
        "projection_contract": "test-projection-v1",
        "manifest_sha256": "c" * 64,
        "manifest_bytes": 123,
        "godot_version": carrier.EXPECTED_GODOT_VERSION,
        "profile_ids": list(profile_ids),
        "pose_id": "test-pose",
        "pose_sha256": pose_sha256,
        "boundary": "host_only_smoke",
        "profiles": profiles,
    }


class DisposableAvatarCarrierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-disposable-avatar-carrier-test-")
        self.root = Path(self.temp.name)
        self.gallery = self.root / "gallery"
        self.gallery.mkdir()
        (self.gallery / carrier.POSE_FILE).write_bytes(POSE_BYTES)
        self.pose_sha256 = hashlib.sha256(POSE_BYTES).hexdigest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_preflight(self, gallery: Path, profile_ids: tuple[str, str]) -> tuple[object, dict]:
        return object(), _payload(tuple(profile_ids), self.pose_sha256)

    def build(self, profile_ids=DEFAULTS, instance_ids=INSTANCE_IDS) -> dict:
        with patch.object(carrier, "preflight", side_effect=self.fake_preflight):
            return carrier.build_carrier(self.gallery, profile_ids, instance_ids)

    def validate(self, value: dict, profile_ids=DEFAULTS) -> tuple[dict, tuple[str, str], tuple[str, str]]:
        with patch.object(carrier, "preflight", side_effect=self.fake_preflight) as preflight:
            result = carrier.validate_carrier(value, self.gallery)
        self.assertEqual(preflight.call_count, 1)
        self.assertEqual(preflight.call_args.args[1], tuple(profile_ids))
        return result

    def test_build_shape_is_exact_and_contains_no_host_or_package_fields(self) -> None:
        value = self.build()
        self.assertEqual(tuple(value), carrier.CARRIER_KEYS)
        self.assertEqual(value["schema"], carrier.SCHEMA)
        self.assertEqual(value["boundary"], carrier.BOUNDARY)
        self.assertEqual(set(value["source_gallery"]), set(carrier.SOURCE_GALLERY_KEYS))
        self.assertEqual(value["shared_pose"], {
            "path": carrier.POSE_FILE,
            "pose_id": "test-pose",
            "sha256": self.pose_sha256,
            "bytes": len(POSE_BYTES),
        })
        self.assertEqual(len(value["instances"]), 2)
        for instance in value["instances"]:
            self.assertEqual(set(instance), set(carrier.INSTANCE_KEYS))
        forbidden = {"godot_version", "coordinate_mapping", "translation", "host_id", "package", "adapter"}
        self.assertTrue(forbidden.isdisjoint(value))

    def test_build_is_deterministic_and_both_frozen_pairs_are_supported(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        first_path = self.root / "first.json"
        second_path = self.root / "second.json"
        carrier.write_carrier(first_path, first)
        carrier.write_carrier(second_path, second)
        self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        for profile_ids in (DEFAULTS, ALTERNATE):
            with self.subTest(profile_ids=profile_ids):
                value = self.build(profile_ids, INSTANCE_IDS)
                self.assertEqual(tuple(item["profile_id"] for item in value["instances"]), profile_ids)

    def test_instance_identity_is_exact_lowercase_ascii_and_distinct(self) -> None:
        for bad in (("same", "same"), ("Avatar", "other"), ("with_under", "other"), ("", "other"), ("a" * 65, "other")):
            with self.subTest(instance_ids=bad):
                with self.assertRaises(carrier.CarrierError):
                    self.build(DEFAULTS, bad)

    def test_validate_rejects_missing_reordered_tampered_and_mixed_lineage_values(self) -> None:
        original = self.build()
        cases = {}

        missing = deepcopy(original)
        del missing["shared_pose"]["bytes"]
        cases["missing field"] = missing

        reordered = deepcopy(original)
        reordered["instances"][0]["artifacts"] = list(reversed(reordered["instances"][0]["artifacts"]))
        cases["reordered artifacts"] = reordered

        tampered = deepcopy(original)
        tampered["instances"][0]["metrics"]["face_count"] = 999
        cases["tampered metrics"] = tampered

        mixed = deepcopy(original)
        alternate_payload = _payload(ALTERNATE, self.pose_sha256)
        mixed["instances"][0]["candidate_profile_sha256"] = alternate_payload["profiles"][0]["candidate_profile_sha256"]
        mixed["instances"][0]["artifacts"] = alternate_payload["profiles"][0]["artifacts"]
        mixed["instances"][0]["metrics"] = alternate_payload["profiles"][0]["metrics"]
        cases["mixed lineage"] = mixed

        swapped_selection = deepcopy(original)
        swapped_selection["instances"][0]["profile_id"], swapped_selection["instances"][1]["profile_id"] = DEFAULTS[1], DEFAULTS[0]
        cases["reordered profile selection"] = swapped_selection

        extra = deepcopy(original)
        extra["unexpected"] = True
        cases["extra top-level key"] = extra

        for label, value in cases.items():
            with self.subTest(case=label):
                with self.assertRaisesRegex(carrier.CarrierError, "exactly match"):
                    self.validate(value)

    def test_absolute_and_traversal_artifact_paths_fail_by_exact_projection_mismatch(self) -> None:
        for path in ("/tmp/neutral.ply", "../neutral.ply", "profile/../../neutral.ply"):
            value = self.build()
            value["instances"][0]["artifacts"][0]["path"] = path
            with self.subTest(path=path):
                with self.assertRaisesRegex(carrier.CarrierError, "exactly match"):
                    self.validate(value)

    def test_validate_reconstructs_the_existing_godot_payload_and_only_adds_version(self) -> None:
        value = self.build()
        godot_payload, profile_ids, instance_ids = self.validate(value)
        expected = _payload(DEFAULTS, self.pose_sha256)
        self.assertEqual(godot_payload, expected)
        self.assertEqual(profile_ids, DEFAULTS)
        self.assertEqual(instance_ids, INSTANCE_IDS)
        self.assertEqual(set(godot_payload), set(expected))
        self.assertEqual(godot_payload["godot_version"], carrier.EXPECTED_GODOT_VERSION)
        self.assertNotIn("schema", godot_payload)
        self.assertNotIn("instances", godot_payload)

    def test_load_rejects_bounded_malformed_and_duplicate_json_inputs(self) -> None:
        cases = {
            "malformed utf8": b"\xff",
            "malformed json": b"{",
            "duplicate key": b'{"a":1,"a":2}',
            "nonfinite": b'{"a":NaN}',
            "nonobject": b"[]",
            "noncanonical": b'{ "a": 1 }\n',
            "deep": (b"[" * (carrier.MAX_JSON_DEPTH + 10)) + b"0" + (b"]" * (carrier.MAX_JSON_DEPTH + 10)),
        }
        for label, raw in cases.items():
            path = self.root / f"{label.replace(' ', '-')}.json"
            path.write_bytes(raw)
            with self.subTest(case=label):
                with self.assertRaises(carrier.CarrierError):
                    carrier.load_carrier(path)

        oversized = self.root / "oversized.json"
        oversized.write_bytes(b"0" * (carrier.MAX_CARRIER_BYTES + 1))
        with self.assertRaisesRegex(carrier.CarrierError, "bounded input size"):
            carrier.load_carrier(oversized)

    def test_load_and_write_are_canonical_and_write_does_not_overwrite(self) -> None:
        value = self.build()
        output = self.root / "carrier.json"
        carrier.write_carrier(output, value)
        expected_bytes = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self.assertEqual(output.read_bytes(), expected_bytes)
        self.assertEqual(carrier.load_carrier(output), value)
        sentinel = b"existing carrier\n"
        output.write_bytes(sentinel)
        with self.assertRaises(carrier.CarrierError):
            carrier.write_carrier(output, value)
        self.assertEqual(output.read_bytes(), sentinel)

    def test_load_and_write_reject_symlink_files_and_path_components(self) -> None:
        value = self.build()
        target = self.root / "target.json"
        target.write_bytes(b"{}")
        carrier_link = self.root / "carrier-link.json"
        carrier_link.symlink_to(target)
        with self.assertRaises(carrier.CarrierError):
            carrier.load_carrier(carrier_link)

        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        link_parent = self.root / "link-parent"
        link_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaises(carrier.CarrierError):
            carrier.write_carrier(link_parent / "carrier.json", value)

        relative = Path("relative-carrier.json")
        with self.assertRaises(carrier.CarrierError):
            carrier.write_carrier(relative, value)

    def test_load_does_not_follow_carrier_symlink_installed_after_parent_open(self) -> None:
        target = self.root / "carrier.json"
        replacement = self.root / "replacement.json"
        target.write_bytes(b'{"a":1}\n')
        replacement.write_bytes(b'{"a":2}\n')
        original_open = carrier._open_directory_descriptor

        def open_then_swap(path: Path, label: str) -> int:
            directory_fd = original_open(path, label)
            self.assertEqual(path, self.root)
            target.rename(self.root / "original-carrier.json")
            target.symlink_to(replacement)
            return directory_fd

        with patch.object(carrier, "_open_directory_descriptor", side_effect=open_then_swap):
            with self.assertRaises(carrier.CarrierError):
                carrier.load_carrier(target)

    def test_shared_pose_does_not_follow_symlink_installed_after_gallery_open(self) -> None:
        pose_path = self.gallery / carrier.POSE_FILE
        replacement = self.root / "replacement-pose.json"
        pose_path.write_bytes(b"original pose\n")
        replacement.write_bytes(POSE_BYTES)
        original_pose_sha256 = hashlib.sha256(b"original pose\n").hexdigest()
        original_open = carrier._open_directory_descriptor

        def open_then_swap(path: Path, label: str) -> int:
            directory_fd = original_open(path, label)
            self.assertEqual(path, self.gallery)
            pose_path.rename(self.gallery / "original-pose.json")
            pose_path.symlink_to(replacement)
            return directory_fd

        with patch.object(carrier, "_open_directory_descriptor", side_effect=open_then_swap):
            with self.assertRaises(carrier.CarrierError):
                carrier._read_validated_pose(self.gallery, original_pose_sha256)

    def test_publication_remains_in_open_directory_when_parent_becomes_symlink(self) -> None:
        value = self.build()
        parent = self.root / "publication"
        parent.mkdir()
        replacement = self.root / "replacement-target"
        replacement.mkdir()
        output = parent / "carrier.json"
        original_parent = self.root / "publication-original"
        original_open = carrier._open_directory_descriptor

        def open_then_swap(path: Path, label: str) -> int:
            directory_fd = original_open(path, label)
            self.assertEqual(path, parent)
            parent.rename(original_parent)
            parent.symlink_to(replacement, target_is_directory=True)
            return directory_fd

        with patch.object(carrier, "_open_directory_descriptor", side_effect=open_then_swap):
            carrier.write_carrier(output, value)

        self.assertTrue((original_parent / "carrier.json").is_file())
        self.assertFalse((replacement / "carrier.json").exists())
        self.assertTrue(parent.is_symlink())
        self.assertEqual(carrier.load_carrier(original_parent / "carrier.json"), value)

    def test_publication_rejects_regular_parent_replacement_before_open(self) -> None:
        value = self.build()
        parent = self.root / "publication"
        parent.mkdir()
        replacement = self.root / "replacement-target"
        replacement.mkdir()
        output = parent / "carrier.json"
        original_parent = self.root / "publication-original"
        original_open = carrier._open_directory_descriptor

        def swap_then_open(path: Path, label: str) -> int:
            self.assertEqual(path, parent)
            parent.rename(original_parent)
            replacement.rename(parent)
            return original_open(path, label)

        with patch.object(carrier, "_open_directory_descriptor", side_effect=swap_then_open):
            with self.assertRaisesRegex(carrier.CarrierError, "changed while it was being opened"):
                carrier.write_carrier(output, value)

        self.assertFalse((parent / "carrier.json").exists())
        self.assertFalse((original_parent / "carrier.json").exists())

    def test_cli_requires_exact_pairs_and_publishes_output(self) -> None:
        output = self.root / "cli-carrier.json"
        args = [
            "--gallery", str(self.gallery),
            "--profile-id", DEFAULTS[0],
            "--profile-id", DEFAULTS[1],
            "--instance-id", INSTANCE_IDS[0],
            "--instance-id", INSTANCE_IDS[1],
            "--output", str(output),
        ]
        with patch.object(carrier, "preflight", side_effect=self.fake_preflight):
            with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(carrier.main(args), 0)
        self.assertEqual(carrier.load_carrier(output), json.loads(stdout.getvalue()))

        too_few = self.root / "too-few.json"
        with patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(carrier.main([
                "--gallery", str(self.gallery),
                "--profile-id", DEFAULTS[0],
                "--instance-id", INSTANCE_IDS[0],
                "--instance-id", INSTANCE_IDS[1],
                "--output", str(too_few),
            ]), 2)
        self.assertFalse(too_few.exists())


class DisposableAvatarCarrierGalleryIntegrationTests(unittest.TestCase):
    def test_real_completed_gallery_supports_both_frozen_pairs(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"completed gallery unavailable: {GALLERY}")
        for profile_ids in (DEFAULTS, ALTERNATE):
            with self.subTest(profile_ids=profile_ids):
                value = carrier.build_carrier(GALLERY, profile_ids, INSTANCE_IDS)
                payload, returned_profiles, returned_instances = carrier.validate_carrier(value, GALLERY)
                self.assertEqual(tuple(payload["profile_ids"]), profile_ids)
                self.assertEqual(returned_profiles, profile_ids)
                self.assertEqual(returned_instances, INSTANCE_IDS)


if __name__ == "__main__":
    unittest.main()

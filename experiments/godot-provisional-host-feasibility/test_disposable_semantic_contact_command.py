from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
DEFAULTS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
ALTERNATE = ("slender_long_limb", "stocky_broad_chested")
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


neutral = load_module(
    "neutral_structural_gallery_smoke_for_semantic_contact_command_tests",
    EXPERIMENT / "run_structural_gallery_smoke.py",
)
sys.modules["run_structural_gallery_smoke"] = neutral
carrier = load_module("disposable_avatar_carrier_for_semantic_contact_command_tests", EXPERIMENT / "disposable_avatar_carrier.py")
pose = load_module("disposable_semantic_pose_command_for_semantic_contact_command_tests", EXPERIMENT / "disposable_semantic_pose_command.py")
contact = load_module(
    "disposable_semantic_contact_command_under_test",
    EXPERIMENT / "disposable_semantic_contact_command.py",
)


class DependencyFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.gallery = root / "gallery"
        self.gallery.mkdir()
        self.carrier_path = root / "carrier.json"
        self.pose_path = root / "pose.json"
        self.carrier_value = {
            "schema": "test-carrier",
            "boundary": "test-only",
            "instances": [
                {
                    "instance_id": "avatar-left",
                    "profile_id": "compact",
                    "candidate_profile_sha256": "a" * 64,
                },
                {
                    "instance_id": "avatar-right",
                    "profile_id": "tall",
                    "candidate_profile_sha256": "b" * 64,
                },
            ],
        }
        self.payload = {"payload": "validated"}
        self.profile_ids = ("compact", "tall")
        self.instance_ids = ("avatar-left", "avatar-right")
        self.pose_value = {"pose": "validated-pose"}
        self.pose_bytes = self._canonical(self.pose_value)
        self.pose_identity = {
            "sha256": hashlib.sha256(self.pose_bytes).hexdigest(),
            "byte_count_decimal": str(len(self.pose_bytes)),
            "schema": contact.POSE_SCHEMA,
            "boundary": contact.POSE_BOUNDARY,
            "command_id": contact.POSE_COMMAND_ID,
            "command_version": contact.POSE_COMMAND_VERSION,
        }
        self.carrier_path.write_bytes(carrier._canonical_json(self.carrier_value))
        self.pose_path.write_bytes(self.pose_bytes)
        self.pose_load_paths = []
        self.pose_validate_calls = []
        self.pose_identity_inputs = []

        def read_regular_file(path: Path, maximum: int, label: str, size_error: str | None = None) -> bytes:
            return carrier._read_regular_file(path, maximum, label, size_error=size_error)

        self.carrier_module = SimpleNamespace(
            INSTANCE_ID_PATTERN=re.compile(r"[a-z][a-z0-9-]{0,63}\Z"),
            load_carrier=lambda path: deepcopy(self.carrier_value),
            validate_carrier=lambda value, gallery: (
                deepcopy(self.payload),
                self.profile_ids,
                self.instance_ids,
            ),
            _read_carrier_bytes=lambda path: Path(path).read_bytes(),
            _read_regular_file=read_regular_file,
            _canonical_json=carrier._canonical_json,
            _unique_object=carrier._unique_object,
            _finite_json=carrier._finite_json,
            write_carrier=carrier.write_carrier,
        )

        def load_pose_command(path: Path) -> dict:
            self.pose_load_paths.append(Path(path))
            return deepcopy(self.pose_value)

        def validate_pose_command(value: object, gallery: Path, carrier_path: Path) -> object:
            self.pose_validate_calls.append((deepcopy(value), Path(gallery), Path(carrier_path)))
            return value

        def pose_command_identity(value: dict) -> dict:
            self.pose_identity_inputs.append(deepcopy(value))
            canonical = self._canonical(value)
            identity = deepcopy(self.pose_identity)
            identity["sha256"] = hashlib.sha256(canonical).hexdigest()
            identity["byte_count_decimal"] = str(len(canonical))
            return identity

        self.pose_module = SimpleNamespace(
            MAX_COMMAND_BYTES=256 * 1024,
            load_command=load_pose_command,
            validate_command=validate_pose_command,
            command_identity=pose_command_identity,
            _canonical_json=self._canonical,
        )

    @staticmethod
    def _canonical(value: object) -> bytes:
        return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

    def patches(self):
        return patch.object(contact, "_load_carrier_module", return_value=self.carrier_module), patch.object(
            contact, "_load_pose_command_module", return_value=self.pose_module
        )


class DisposableSemanticContactCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-disposable-semantic-contact-command-test-")
        self.root = Path(self.temp.name)
        self.deps = DependencyFixture(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self) -> dict:
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch:
            return contact.build_contact_command(
                self.deps.gallery,
                self.deps.carrier_path,
                self.deps.pose_path,
            )

    def test_build_has_exact_contract_and_exact_fixed_participants(self) -> None:
        value = self.build()
        self.assertEqual(tuple(value), contact.COMMAND_KEYS)
        self.assertEqual(value["schema"], "creature-kernel.disposable-semantic-contact-command.v1")
        self.assertEqual(value["boundary"], "experiment_local_contact_command_evidence_only_no_adapter_or_runtime_conformance")
        self.assertEqual(value["command_id"], "probe-single-semantic-contact")
        self.assertEqual(value["command_version"], 1)
        self.assertEqual(value["mapping_revision"], "joint-selector-to-posed-proxy-v1")
        self.assertEqual(value["targets"], [
            {"instance_id": "avatar-left", "profile_id": "compact", "candidate_profile_sha256": "a" * 64},
            {"instance_id": "avatar-right", "profile_id": "tall", "candidate_profile_sha256": "b" * 64},
        ])
        self.assertEqual(value["source_pose_command"], self.deps.pose_identity)
        self.assertEqual(value["participants"], contact.EXPECTED_PARTICIPANTS)
        self.assertEqual(value["interaction"], contact.EXPECTED_INTERACTION)
        forbidden_keys = {"godot", "host", "package", "adapter", "readiness", "node", "body_type", "distance", "ticks", "mass", "solver", "deformation", "performance"}
        self.assertTrue(forbidden_keys.isdisjoint(value))

    def test_build_is_deterministic_and_identity_uses_canonical_bytes(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(contact._canonical_json(first), contact._canonical_json(second))
        identity = contact.command_identity(first)
        self.assertEqual(identity["sha256"], hashlib.sha256(contact._canonical_json(first)).hexdigest())
        self.assertEqual(identity["byte_count_decimal"], str(len(contact._canonical_json(first))))
        self.assertEqual(identity["schema"], contact.SCHEMA)
        self.assertEqual(identity["command_id"], contact.COMMAND_ID)

    def test_validate_rebuilds_lineage_and_rejects_target_pose_and_mixed_lineage_changes(self) -> None:
        expected = self.build()
        mutations = []
        reordered = deepcopy(expected)
        reordered["targets"].reverse()
        mutations.append(("reordered targets", reordered))
        mixed = deepcopy(expected)
        mixed["targets"][0]["profile_id"] = expected["targets"][1]["profile_id"]
        mixed["targets"][0]["candidate_profile_sha256"] = expected["targets"][1]["candidate_profile_sha256"]
        mutations.append(("mixed target lineage", mixed))
        changed_pose = deepcopy(expected)
        changed_pose["source_pose_command"]["sha256"] = "e" * 64
        mutations.append(("pose identity tamper", changed_pose))
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch:
            contact.validate_contact_command(expected, self.deps.gallery, self.deps.carrier_path, self.deps.pose_path)
            for label, mutation in mutations:
                with self.subTest(case=label), self.assertRaisesRegex(contact.ContactCommandError, "does not exactly match"):
                    contact.validate_contact_command(
                        mutation,
                        self.deps.gallery,
                        self.deps.carrier_path,
                        self.deps.pose_path,
                    )

    def test_shape_rejects_paths_forbidden_fields_and_non_exact_participants(self) -> None:
        value = self.build()
        mutations = []
        extra = deepcopy(value)
        extra["host"] = "godot"
        mutations.append(extra)
        path_value = deepcopy(value)
        path_value["source_pose_command"]["boundary"] = "/tmp/host-package"
        mutations.append(path_value)
        drive_relative = deepcopy(value)
        drive_relative["targets"][0]["profile_id"] = "C:foo"
        mutations.append(drive_relative)
        nested_forbidden = deepcopy(value)
        nested_forbidden["interaction"]["solver"] = False
        mutations.append(nested_forbidden)
        wrong_participant = deepcopy(value)
        wrong_participant["participants"][0]["selector"]["anchors"] = ["left"]
        mutations.append(wrong_participant)
        wrong_command = deepcopy(value)
        wrong_command["command_id"] = "probe-other-contact"
        mutations.append(wrong_command)
        wrong_version = deepcopy(value)
        wrong_version["command_version"] = 2
        mutations.append(wrong_version)
        wrong_mapping = deepcopy(value)
        wrong_mapping["mapping_revision"] = "other-mapping"
        mutations.append(wrong_mapping)
        wrong_interaction = deepcopy(value)
        wrong_interaction["interaction"]["phase_order"] = ["approach", "contact", "exit"]
        mutations.append(wrong_interaction)
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(contact.ContactCommandError):
                carrier_patch, pose_patch = self.deps.patches()
                with carrier_patch, pose_patch:
                    contact._validate_shape(mutation)

        ordinary_identifier = deepcopy(value)
        ordinary_identifier["targets"][0]["profile_id"] = "host-adapter-profile"
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch:
            self.assertIs(contact._validate_shape(ordinary_identifier), ordinary_identifier)

    def test_load_is_bounded_canonical_and_rejects_duplicate_or_relative_input(self) -> None:
        value = self.build()
        output = self.root / "contact.json"
        output.write_bytes(contact._canonical_json(value))
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch:
            self.assertEqual(contact.load_contact_command(output), value)
            with self.assertRaises(contact.ContactCommandError):
                contact.load_contact_command(Path("relative-contact.json"))
        noncanonical = self.root / "noncanonical.json"
        noncanonical.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch, self.assertRaisesRegex(contact.ContactCommandError, "not canonical"):
            contact.load_contact_command(noncanonical)
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"schema":"x","schema":"y"}\n', encoding="utf-8")
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch, self.assertRaises(contact.ContactCommandError):
            contact.load_contact_command(duplicate)
        invalid_utf8 = self.root / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"\xff")
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch, self.assertRaises(contact.ContactCommandError):
            contact.load_contact_command(invalid_utf8)
        oversized = self.root / "oversized.json"
        oversized.write_bytes(b"0" * (contact.MAX_COMMAND_BYTES + 1))
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch, self.assertRaisesRegex(contact.ContactCommandError, "bounded input size"):
            contact.load_contact_command(oversized)

    def test_publication_does_not_overwrite_and_rejects_symlink_output(self) -> None:
        value = self.build()
        output = self.root / "published.json"
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch:
            contact.write_contact_command(output, value)
            expected_bytes = contact._canonical_json(value)
            self.assertEqual(output.read_bytes(), expected_bytes)
            with self.assertRaises(contact.ContactCommandError):
                contact.write_contact_command(output, value)
            self.assertEqual(output.read_bytes(), expected_bytes)
            target = self.root / "target.json"
            target.write_bytes(b"target\n")
            link = self.root / "link.json"
            link.symlink_to(target)
            with self.assertRaises(contact.ContactCommandError):
                contact.write_contact_command(link, value)

    def test_pre_and_postflight_reject_predecessor_change(self) -> None:
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch:
            initial = contact._validated_predecessors(self.deps.gallery, self.deps.carrier_path, self.deps.pose_path)
            changed = deepcopy(initial)
            changed["pose_identity"]["sha256"] = "f" * 64
            with patch.object(contact, "_validated_predecessors", side_effect=[initial, changed]), self.assertRaisesRegex(
                contact.ContactCommandError, "predecessor pose_identity changed"
            ):
                contact.build_contact_command(self.deps.gallery, self.deps.carrier_path, self.deps.pose_path)

    def test_cli_build_and_validate_use_the_explicit_pose_command_path(self) -> None:
        output = self.root / "cli-contact.json"
        carrier_patch, pose_patch = self.deps.patches()
        with carrier_patch, pose_patch, patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(contact.main([
                "build",
                "--gallery", str(self.deps.gallery),
                "--carrier", str(self.deps.carrier_path),
                "--pose-command", str(self.deps.pose_path),
                "--output", str(output),
            ]), 0)
            self.assertEqual(contact.main([
                "validate",
                "--gallery", str(self.deps.gallery),
                "--carrier", str(self.deps.carrier_path),
                "--pose-command", str(self.deps.pose_path),
                "--command", str(output),
            ]), 0)
        self.assertTrue(self.deps.pose_load_paths)
        self.assertTrue(all(path == self.deps.pose_path for path in self.deps.pose_load_paths))
        expected_validation = (self.deps.pose_value, self.deps.gallery, self.deps.carrier_path)
        self.assertTrue(self.deps.pose_validate_calls)
        self.assertTrue(all(call == expected_validation for call in self.deps.pose_validate_calls))
        self.assertTrue(self.deps.pose_identity_inputs)
        self.assertTrue(all(value == self.deps.pose_value for value in self.deps.pose_identity_inputs))
        self.assertEqual(contact.load_contact_command(output), self.build())

    def test_real_frozen_gallery_builds_and_freshly_validates_both_profile_pairs(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"frozen structural gallery unavailable: {GALLERY}")
        for label, profile_ids in (("default", DEFAULTS), ("alternate", ALTERNATE)):
            with self.subTest(profile_ids=profile_ids):
                instance_ids = (f"{label}-left", f"{label}-right")
                carrier_path = self.root / f"{label}-carrier.json"
                pose_path = self.root / f"{label}-pose.json"
                contact_path = self.root / f"{label}-contact.json"

                carrier_value = carrier.build_carrier(GALLERY, profile_ids, instance_ids)
                carrier.write_carrier(carrier_path, carrier_value)
                pose_value = pose.build_command(GALLERY, carrier_path)
                pose.write_command(pose_path, pose_value)
                contact_value = contact.build_contact_command(GALLERY, carrier_path, pose_path)
                contact.write_contact_command(contact_path, contact_value)
                loaded = contact.load_contact_command(contact_path)
                self.assertIs(
                    contact.validate_contact_command(loaded, GALLERY, carrier_path, pose_path),
                    loaded,
                )

                expected_targets = [
                    {key: instance[key] for key in contact.TARGET_KEYS}
                    for instance in carrier_value["instances"]
                ]
                self.assertEqual(loaded["targets"], expected_targets)
                self.assertEqual(tuple(target["profile_id"] for target in loaded["targets"]), profile_ids)
                self.assertEqual(tuple(target["instance_id"] for target in loaded["targets"]), instance_ids)
                self.assertEqual(loaded["source_pose_command"], pose.command_identity(pose_value))


if __name__ == "__main__":
    unittest.main()

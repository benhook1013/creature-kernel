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
PROFILE_IDS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
INSTANCE_IDS = ("avatar-left", "avatar-right")
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_module(
    "run_structural_gallery_smoke_for_package_tests",
    EXPERIMENT / "run_structural_gallery_smoke.py",
)
sys.modules["run_structural_gallery_smoke"] = smoke
carrier = load_module(
    "disposable_avatar_carrier_for_package_tests",
    EXPERIMENT / "disposable_avatar_carrier.py",
)
sys.modules["disposable_avatar_carrier"] = carrier
projection = load_module(
    "disposable_ck_projection_for_package_tests",
    EXPERIMENT / "disposable_ck_projection.py",
)
sys.modules["disposable_ck_projection"] = projection
package = load_module(
    "disposable_ck_package_under_test",
    EXPERIMENT / "disposable_ck_package.py",
)


def runtime_evidence(profile_id: str) -> dict[str, object]:
    return {
        "format": projection.RUST_FORMAT,
        "operation": projection.RUST_OPERATION,
        "stage": "runtime-input",
        "status": "success",
        "processing_complete": True,
        "diagnostics_complete": True,
        "diagnostics": [],
        "source": {"document": f"fixture.{profile_id}", "namespace": "fixture"},
        "prepared_basis": deepcopy(projection.EXPECTED_PREPARED_BASIS),
        "prepared_counts": {name: 0 for name in projection.PREPARED_COUNT_KEYS},
        "structural_counts": {name: 0 for name in projection.STRUCTURAL_COUNT_KEYS},
    }


class DisposableCKPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-disposable-package-test-")
        self.root = Path(self.temp.name)
        self.gallery = self.root / "gallery"
        (self.gallery / projection.SOURCE_DIR).mkdir(parents=True)
        self.projection_path = self.root / "projection.json"
        self.carrier_path = self.root / "carrier.json"
        self.cli_path = self.root / "creature-kernel"
        self.cli_path.write_bytes(b"fake native cli")
        self.cli_path.chmod(0o700)

        avatars = []
        for profile_id in PROFILE_IDS:
            source = {
                "source": {
                    "dependencies": [],
                    "document": f"fixture.{profile_id}",
                    "namespace": "fixture",
                }
            }
            source_bytes = (json.dumps(source, separators=(",", ":")) + "\n").encode("utf-8")
            (self.gallery / projection.SOURCE_DIR / f"{profile_id}.json").write_bytes(source_bytes)
            profile_directory = self.gallery / profile_id
            profile_directory.mkdir()
            artifact_records = []
            for artifact_name in smoke.EXPECTED_ARTIFACT_NAMES:
                if artifact_name in {"skeleton.json", "weights.json", "proxies-neutral.json", "proxies-posed.json"}:
                    data = package._canonical_json({"format": "fixture", "profile_id": profile_id})
                else:
                    data = f"{profile_id}:{artifact_name}".encode("ascii")
                (profile_directory / artifact_name).write_bytes(data)
                artifact_records.append(
                    {
                        "path": f"{profile_id}/{artifact_name}",
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                    }
                )
            metrics = {
                "format": "creature-kernel.disposable-structural-embodiment-metrics.v1",
                "profile_id": profile_id,
                "vertex_count": 3,
            }
            (profile_directory / package.METRICS_FILE).write_bytes(
                (json.dumps(metrics, separators=(",", ":")) + "\n").encode("utf-8")
            )
            avatars.append(
                {
                    "instance_id": INSTANCE_IDS[len(avatars)],
                    "profile_id": profile_id,
                    "label": f"Fixture {profile_id}",
                    "candidate_profile_sha256": hashlib.sha256(profile_id.encode("ascii")).hexdigest(),
                    "source": {
                        "path": f"sources/{profile_id}.json",
                        "sha256": hashlib.sha256(source_bytes).hexdigest(),
                        "bytes": len(source_bytes),
                        "document": source["source"]["document"],
                        "namespace": "fixture",
                    },
                    "runtime_input_inspection": runtime_evidence(profile_id),
                    "artifacts": artifact_records,
                    "metrics": metrics,
                }
            )
        projection_body = {
            "schema": projection.SCHEMA,
            "boundary": projection.BOUNDARY,
            "producer_identity": {
                "sha256": "a" * 64,
                "bytes": 15,
                "operation": projection.RUST_OPERATION,
                "format": projection.RUST_FORMAT,
            },
            "carrier_identity": {
                "schema": carrier.SCHEMA,
                "boundary": carrier.BOUNDARY,
                "sha256": "b" * 64,
                "bytes": 15,
                "instance_ids": list(INSTANCE_IDS),
            },
            "gallery_identity": {
                "projection_contract": "test-gallery-v1",
                "manifest_sha256": "c" * 64,
                "manifest_bytes": 123,
                "boundary": "test-gallery-boundary",
                "profile_ids": list(PROFILE_IDS),
            },
            "shared_pose": {
                "path": projection.POSE_FILE,
                "pose_id": "shared-test-pose",
                "sha256": "d" * 64,
                "bytes": 42,
            },
            "avatars": avatars,
        }
        self.projection_value = projection.identify_projection(projection_body, carrier_module=carrier)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _validated(self, value: dict[str, object] | None = None):
        return patch.object(
            projection,
            "validate_projection",
            return_value=deepcopy(value if value is not None else self.projection_value),
        )

    def build(self, output: Path | None = None, value: dict[str, object] | None = None) -> dict[str, object]:
        destination = output or self.root / "payload"
        with patch.object(package, "_load_projection_module", return_value=projection), self._validated(value):
            return package.build_package(
                self.gallery,
                self.carrier_path,
                self.projection_path,
                destination,
                cli_path=self.cli_path,
            )

    def test_deterministic_successful_structure_and_transport_only_manifest(self) -> None:
        first_path = self.root / "first-payload"
        second_path = self.root / "second-payload"
        first = self.build(first_path)
        second = self.build(second_path)
        self.assertEqual(first, second)
        self.assertEqual(first["manifest_identity"]["scope"], package.MANIFEST_IDENTITY_SCOPE)
        self.assertEqual(package.load_manifest(first_path), first)
        self.assertEqual(package.load_manifest(second_path), second)
        expected_files, expected_directories = package._expected_inventory(smoke.EXPECTED_ARTIFACT_NAMES)
        for path in (first_path, second_path):
            files, directories = package._scan_package(path)
            self.assertEqual(files, expected_files)
            self.assertEqual(directories, expected_directories)
            self.assertEqual((first_path / package.MANIFEST_FILE).read_bytes(), (second_path / package.MANIFEST_FILE).read_bytes())
            self.assertEqual((path / package.MANIFEST_FILE).read_bytes(), package._canonical_json(first))
        encoded = json.dumps(first, ensure_ascii=True, sort_keys=True, separators=(",", ":")).lower()
        for forbidden in ("godot", "host", "adapter", "resolver", "snapshot", "readiness"):
            self.assertNotIn(forbidden, encoded)
        self.assertNotIn("shared_pose", first)
        for index, avatar in enumerate(first["avatars"]):
            self.assertEqual(avatar["ordinal"], index)
            self.assertEqual(
                [record["path"] for record in avatar["artifacts"]],
                [f"avatars/{index}/{name}" for name in smoke.EXPECTED_ARTIFACT_NAMES],
            )
            self.assertEqual(avatar["source"]["path"], f"avatars/{index}/source.json")
            self.assertEqual(avatar["metrics"]["path"], f"avatars/{index}/metrics.json")

    def test_package_only_validation_survives_unavailable_inputs_and_cli(self) -> None:
        output = self.root / "payload"
        manifest = self.build(output)
        for path in (self.gallery, self.carrier_path, self.projection_path, self.cli_path):
            if path.is_dir():
                for child in sorted(path.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                path.rmdir()
            elif path.exists():
                path.unlink()
        with patch.object(projection, "validate_projection", side_effect=AssertionError("fresh inputs used")):
            self.assertEqual(package.validate_package(output), manifest)
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            self.assertEqual(package.main(["validate", "--package", str(output)]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), manifest)

    def test_offline_validation_rejects_rehashed_dependency_bearing_source(self) -> None:
        output = self.root / "dependency-payload"
        original = self.build(output)
        expected_files, expected_directories = package._expected_inventory(smoke.EXPECTED_ARTIFACT_NAMES)
        files, directories = package._scan_package(output)
        self.assertEqual(len(files), 17)
        self.assertEqual(files, expected_files)
        self.assertEqual(directories, expected_directories)

        source_record = original["avatars"][0]["source"]
        source_data = package._canonical_json(
            {
                "source": {
                    "dependencies": [
                        {
                            "content_sha256": "sha256:" + "f" * 64,
                            "document": "fixture.dependency",
                            "namespace": "fixture",
                        }
                    ],
                    "document": source_record["document"],
                    "namespace": source_record["namespace"],
                }
            }
        )
        (output / source_record["path"]).write_bytes(source_data)
        changed = deepcopy(original)
        changed_source = changed["avatars"][0]["source"]
        changed_source["sha256"] = hashlib.sha256(source_data).hexdigest()
        changed_source["bytes"] = len(source_data)
        changed = package.identify_manifest(changed, projection_module=projection, carrier_module=carrier)
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))

        files, directories = package._scan_package(output)
        self.assertEqual(len(files), 17)
        self.assertEqual(files, expected_files)
        self.assertEqual(directories, expected_directories)
        for validator in (package.load_manifest, package.validate_package):
            with self.subTest(validator=validator.__name__), self.assertRaisesRegex(
                package.PackageError, r"source\.dependencies exactly.*dependency closure"
            ):
                validator(output)

    def test_offline_validation_binds_source_and_profile_bearing_content(self) -> None:
        output = self.root / "identity-content-payload"
        original = self.build(output)

        source_record = original["avatars"][0]["source"]
        source_value = {"source": {"dependencies": [], "document": "wrong.document", "namespace": "fixture"}}
        source_data = package._canonical_json(source_value)
        (output / source_record["path"]).write_bytes(source_data)
        changed = deepcopy(original)
        changed_source = changed["avatars"][0]["source"]
        changed_source["sha256"] = hashlib.sha256(source_data).hexdigest()
        changed_source["bytes"] = len(source_data)
        changed = package.identify_manifest(changed, projection_module=projection, carrier_module=carrier)
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "document/namespace does not match"):
            package.validate_package(output)

        output = self.root / "source-shape-payload"
        original = self.build(output)
        source_record = original["avatars"][0]["source"]
        source_data = package._canonical_json(
            {
                "source": {
                    "dependencies": [],
                    "document": source_record["document"],
                    "namespace": source_record["namespace"],
                    "unexpected": "field",
                }
            }
        )
        (output / source_record["path"]).write_bytes(source_data)
        changed = deepcopy(original)
        changed_source = changed["avatars"][0]["source"]
        changed_source["sha256"] = hashlib.sha256(source_data).hexdigest()
        changed_source["bytes"] = len(source_data)
        changed = package.identify_manifest(changed, projection_module=projection, carrier_module=carrier)
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "exact canonical source shape"):
            package.validate_package(output)

        output = self.root / "profile-content-payload"
        original = self.build(output)
        artifact_path = output / original["avatars"][1]["artifacts"][2]["path"]
        artifact_data = package._canonical_json({"format": "fixture", "profile_id": "wrong-profile"})
        artifact_path.write_bytes(artifact_data)
        changed = deepcopy(original)
        artifact_record = changed["avatars"][1]["artifacts"][2]
        artifact_record["sha256"] = hashlib.sha256(artifact_data).hexdigest()
        artifact_record["bytes"] = len(artifact_data)
        changed = package.identify_manifest(changed, projection_module=projection, carrier_module=carrier)
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "artifact .* profile identity"):
            package.validate_package(output)

        output = self.root / "metrics-content-payload"
        original = self.build(output)
        metrics_path = output / original["avatars"][0]["metrics"]["path"]
        metrics_data = package._canonical_json(
            {"format": "creature-kernel.disposable-structural-embodiment-metrics.v1", "profile_id": "wrong-profile", "vertex_count": 3}
        )
        metrics_path.write_bytes(metrics_data)
        changed = deepcopy(original)
        metrics_record = changed["avatars"][0]["metrics"]
        metrics_record["sha256"] = hashlib.sha256(metrics_data).hexdigest()
        metrics_record["bytes"] = len(metrics_data)
        changed = package.identify_manifest(changed, projection_module=projection, carrier_module=carrier)
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "metrics .* profile identity"):
            package.validate_package(output)

    def test_missing_and_extra_entries_are_rejected(self) -> None:
        for kind in ("missing", "extra"):
            output = self.root / kind
            self.build(output)
            if kind == "missing":
                (output / "avatars/0/neutral.ply").unlink()
            else:
                (output / "avatars/0/extra.bin").write_bytes(b"extra")
            with self.subTest(kind=kind), self.assertRaisesRegex(package.PackageError, "exact expected"):
                package.validate_package(output)

    def test_symlink_entries_and_source_fail_closed(self) -> None:
        output = self.root / "symlink-payload"
        self.build(output)
        target = self.root / "target"
        target.write_bytes(b"target")
        payload_link = output / "avatars/0/neutral.ply"
        payload_link.unlink()
        payload_link.symlink_to(target)
        with self.assertRaisesRegex(package.PackageError, "symlink"):
            package.validate_package(output)

        source = self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json"
        source.unlink()
        source.symlink_to(target)
        failed_output = self.root / "source-symlink-payload"
        with self.assertRaises(package.PackageError):
            self.build(failed_output)
        self.assertFalse(failed_output.exists())

    def test_tampered_content_manifest_and_reordered_identities_are_rejected(self) -> None:
        output = self.root / "tampered-payload"
        self.build(output)
        (output / "avatars/1/weights.json").write_bytes(b"tampered")
        with self.assertRaisesRegex(package.PackageError, "hash or byte count"):
            package.validate_package(output)

        output = self.root / "tampered-manifest-payload"
        original = self.build(output)
        changed = deepcopy(original)
        changed["avatars"][0]["candidate_profile_sha256"] = "e" * 64
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "manifest_identity"):
            package.validate_package(output)

        output = self.root / "reordered-payload"
        original = self.build(output)
        changed = deepcopy(original)
        changed["avatars"] = list(reversed(changed["avatars"]))
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "ordinal|manifest_identity"):
            package.validate_package(output)

    def test_path_traversal_and_strict_manifest_inputs_are_rejected(self) -> None:
        output = self.root / "path-payload"
        original = self.build(output)
        changed = deepcopy(original)
        changed["avatars"][0]["source"]["path"] = "../outside/source.json"
        (output / package.MANIFEST_FILE).write_bytes(package._canonical_json(changed))
        with self.assertRaisesRegex(package.PackageError, "fixed payload path|safe relative"):
            package.validate_package(output)

        bad = self.root / "malformed-manifest-payload"
        valid = self.build(bad)
        expected_files, expected_directories = package._expected_inventory(smoke.EXPECTED_ARTIFACT_NAMES)
        files, directories = package._scan_package(bad)
        self.assertEqual(len(files), 17)
        self.assertEqual(files, expected_files)
        self.assertEqual(directories, expected_directories)
        valid_bytes = (bad / package.MANIFEST_FILE).read_bytes()
        for label, raw, message in (
            ("duplicate", b'{"schema":"duplicate",' + valid_bytes[1:], "not valid finite"),
            ("nonfinite", valid_bytes.replace(b'"schema":"creature-kernel.disposable-ck-directory-payload.v1"', b'"schema":NaN', 1), "not valid finite"),
            ("noncanonical", b" " + valid_bytes, "not canonical newline-terminated"),
        ):
            (bad / package.MANIFEST_FILE).write_bytes(raw)
            with self.subTest(label=label), self.assertRaisesRegex(package.PackageError, message):
                package.load_manifest(bad)

    def test_changed_source_after_copy_is_rejected_and_destination_is_cleaned(self) -> None:
        output = self.root / "changed-source-payload"
        original_write = package._write_new_file
        changed = False

        def write_then_change(path: Path, data: bytes, label: str) -> None:
            nonlocal changed
            original_write(path, data, label)
            if not changed and path.name == smoke.EXPECTED_ARTIFACT_NAMES[-1]:
                changed = True
                source = self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json"
                source.write_bytes(source.read_bytes() + b"changed")

        with patch.object(package, "_load_projection_module", return_value=projection), self._validated(), patch.object(
            package, "_write_new_file", side_effect=write_then_change
        ), self.assertRaisesRegex(package.PackageError, "changed"):
            package.build_package(
                self.gallery,
                self.carrier_path,
                self.projection_path,
                output,
                cli_path=self.cli_path,
            )
        self.assertFalse(output.exists())

    def test_dependency_bearing_source_is_rejected_and_destination_is_cleaned(self) -> None:
        output = self.root / "dependency-payload"
        changed = deepcopy(self.projection_value)
        source = changed["avatars"][0]["source"]
        source_data = package._canonical_json(
            {
                "source": {
                    "dependencies": [
                        {
                            "content_sha256": "sha256:" + "f" * 64,
                            "document": "fixture.dependency",
                            "namespace": "fixture",
                        }
                    ],
                    "document": source["document"],
                    "namespace": source["namespace"],
                }
            }
        )
        source_path = self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json"
        source_path.write_bytes(source_data)
        source["sha256"] = hashlib.sha256(source_data).hexdigest()
        source["bytes"] = len(source_data)

        with self.assertRaisesRegex(package.PackageError, r"source\.dependencies exactly.*dependency closure"):
            self.build(output, changed)
        self.assertFalse(output.exists())

    def test_no_overwrite_and_failure_cleanup(self) -> None:
        sentinel = self.root / "existing-payload"
        sentinel.mkdir()
        (sentinel / "sentinel").write_bytes(b"keep")
        with self.assertRaisesRegex(package.PackageError, "already exists"):
            self.build(sentinel)
        self.assertEqual((sentinel / "sentinel").read_bytes(), b"keep")

        output = self.root / "failed-payload"
        original_write = package._write_new_file
        writes = 0

        def fail_after_one(path: Path, data: bytes, label: str) -> None:
            nonlocal writes
            writes += 1
            original_write(path, data, label)
            if writes == 1:
                raise package.PackageError("intentional bounded write failure")

        with patch.object(package, "_load_projection_module", return_value=projection), self._validated(), patch.object(
            package, "_write_new_file", side_effect=fail_after_one
        ), self.assertRaisesRegex(package.PackageError, "intentional"):
            package.build_package(
                self.gallery,
                self.carrier_path,
                self.projection_path,
                output,
                cli_path=self.cli_path,
            )
        self.assertFalse(output.exists())

    def test_destination_lstat_failure_after_mkdir_is_cleaned(self) -> None:
        output = self.root / "lstat-failure-payload"
        captured = False
        lstat_failed = False
        original_identity = package._directory_identity
        original_lstat = Path.lstat

        def capture_identity(path: Path, label: str, *, parent_fd: int | None = None) -> tuple[int, int]:
            nonlocal captured
            identity = original_identity(path, label, parent_fd=parent_fd)
            captured = True
            return identity

        def fail_post_create_lstat(path: Path) -> os.stat_result:
            nonlocal lstat_failed
            if captured and path == output and not lstat_failed:
                lstat_failed = True
                raise OSError("simulated post-create lstat failure")
            return original_lstat(path)

        with patch.object(package, "_directory_identity", side_effect=capture_identity), patch.object(
            Path, "lstat", autospec=True, side_effect=fail_post_create_lstat
        ), self.assertRaisesRegex(package.PackageError, "could not inspect new package destination"):
            package._create_destination(output)
        self.assertTrue(captured)
        self.assertTrue(lstat_failed)
        self.assertFalse(output.exists())

    def test_create_destination_anchors_output_parent_before_mkdir(self) -> None:
        output_parent = self.root / "output-parent"
        output_parent.mkdir()
        owned_parent = self.root / "owned-output-parent"
        foreign = self.root / "foreign-output-parent"
        foreign.mkdir()
        sentinel = foreign / "must-survive"
        sentinel.write_bytes(b"external data")
        output = output_parent / "payload"
        swapped = False
        original_open = package._open_directory_descriptor

        def open_then_replace(path: Path, label: str) -> int:
            nonlocal swapped
            descriptor = original_open(path, label)
            if path == output_parent and not swapped:
                output_parent.rename(owned_parent)
                output_parent.symlink_to(foreign, target_is_directory=True)
                swapped = True
            return descriptor

        with patch.object(package, "_open_directory_descriptor", side_effect=open_then_replace), self.assertRaises(
            package.PackageError
        ):
            package._create_destination(output)

        self.assertTrue(swapped)
        self.assertTrue(output_parent.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"external data")
        self.assertFalse(foreign.joinpath("payload").exists())
        self.assertTrue(owned_parent.joinpath("payload").is_dir())

    def test_make_layout_anchors_root_before_layout_mkdir(self) -> None:
        root = self.root / "layout-root"
        root.mkdir()
        owned_root = self.root / "owned-layout-root"
        foreign = self.root / "foreign-layout-root"
        foreign.mkdir()
        sentinel = foreign / "must-survive"
        sentinel.write_bytes(b"external data")
        swapped = False
        original_open = package._open_directory_descriptor

        def open_then_replace(path: Path, label: str) -> int:
            nonlocal swapped
            descriptor = original_open(path, label)
            if path == root and not swapped:
                root.rename(owned_root)
                root.symlink_to(foreign, target_is_directory=True)
                swapped = True
            return descriptor

        with patch.object(package, "_open_directory_descriptor", side_effect=open_then_replace):
            package._make_layout(root)

        self.assertTrue(swapped)
        self.assertTrue(root.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"external data")
        self.assertFalse(foreign.joinpath(package.AVATARS_DIRECTORY).exists())
        self.assertTrue(owned_root.joinpath("avatars/0").is_dir())
        self.assertTrue(owned_root.joinpath("avatars/1").is_dir())

    def test_build_does_not_write_or_cleanup_through_replaced_avatar_parent(self) -> None:
        output = self.root / "raced-payload"
        avatar_parent = output / "avatars/0"
        owned_avatar_parent = self.root / "owned-avatar-0"
        foreign = self.root / "foreign-avatar-0"
        foreign.mkdir()
        sentinel = foreign / "must-survive"
        sentinel.write_bytes(b"external data")
        swapped = False
        original_open = package._open_directory_descriptor

        def open_then_replace(path: Path, label: str) -> int:
            nonlocal swapped
            descriptor = original_open(path, label)
            if path == avatar_parent and not swapped:
                avatar_parent.rename(owned_avatar_parent)
                avatar_parent.symlink_to(foreign, target_is_directory=True)
                swapped = True
            return descriptor

        with patch.object(package, "_load_projection_module", return_value=projection), self._validated(), patch.object(
            package, "_open_directory_descriptor", side_effect=open_then_replace
        ), self.assertRaises(package.PackageError):
            package.build_package(
                self.gallery,
                self.carrier_path,
                self.projection_path,
                output,
                cli_path=self.cli_path,
            )

        self.assertTrue(swapped)
        self.assertTrue(avatar_parent.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"external data")
        self.assertFalse(foreign.joinpath("metrics.json").exists())
        self.assertTrue(owned_avatar_parent.is_dir())

    def test_cleanup_abandons_replaced_destination_symlink(self) -> None:
        output = self.root / "replaced-payload"
        output.mkdir()
        foreign = self.root / "foreign"
        foreign.mkdir()
        sentinel = foreign / "must-survive"
        sentinel.write_bytes(b"external data")
        info = output.lstat()
        identity = (info.st_dev, info.st_ino)

        output.rmdir()
        output.symlink_to(foreign, target_is_directory=True)
        package._cleanup_created_destination(output, identity)

        self.assertTrue(output.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"external data")

    def test_cleanup_does_not_follow_nested_path_replaced_by_symlink(self) -> None:
        output = self.root / "raced-payload"
        output.mkdir()
        nested = output / "nested"
        nested.mkdir()
        foreign = self.root / "foreign-tree"
        foreign.mkdir()
        sentinel = foreign / "must-survive"
        sentinel.write_bytes(b"external data")
        info = output.lstat()
        identity = (info.st_dev, info.st_ino)
        real_scandir = os.scandir
        swapped = False

        def replace_before_root_scan(path):
            nonlocal swapped
            if not swapped and isinstance(path, str) and path.startswith("/proc/self/fd/"):
                if Path(os.path.realpath(path)) == output:
                    nested.rmdir()
                    nested.symlink_to(foreign, target_is_directory=True)
                    swapped = True
            return real_scandir(path)

        with patch.object(package.os, "scandir", side_effect=replace_before_root_scan):
            package._cleanup_created_destination(output, identity)

        self.assertTrue(swapped)
        self.assertTrue(nested.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"external data")
        self.assertTrue(output.is_dir())

    def test_build_and_validate_cli_boundaries(self) -> None:
        output = self.root / "cli-payload"
        stdout = io.StringIO()
        with patch.object(package, "_load_projection_module", return_value=projection), self._validated(), patch(
            "sys.stdout", stdout
        ):
            result = package.main(
                [
                    "build",
                    "--gallery",
                    str(self.gallery),
                    "--carrier",
                    str(self.carrier_path),
                    "--projection",
                    str(self.projection_path),
                    "--output",
                    str(output),
                    "--cli",
                    str(self.cli_path),
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), package.load_manifest(output))
        with self.assertRaises(SystemExit):
            package._parser().parse_args(["build", "--gallery", str(self.gallery)])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

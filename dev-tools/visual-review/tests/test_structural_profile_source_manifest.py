"""Focused tests for the reusable exact-five source-manifest validator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve()
REPOSITORY_ROOT = HERE.parents[3]
VISUAL_REVIEW_ROOT = HERE.parents[1]
EXPERIMENT_ROOT = REPOSITORY_ROOT / "experiments" / "current-form-surface-preview"
sys.path.insert(0, str(VISUAL_REVIEW_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

import generate_structural_profile_sources as profile_generator  # noqa: E402
import structural_profile_source_manifest as validator  # noqa: E402


PROFILE_IDS = list(profile_generator.ACTIVE_PROFILE_IDS)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class StructuralProfileSourceManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(
            prefix="ck-source-manifest-tests-",
            dir=tempfile.gettempdir(),
        )
        self.root = Path(self.temp.name)
        self.candidate = profile_generator.DEFAULT_CANDIDATE
        self.base_source = profile_generator.DEFAULT_SOURCE
        self.source_dir = self._make_bundle("sources")
        self.manifest_path = self.source_dir / "manifest.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _make_bundle(self, name: str) -> Path:
        output_dir = self.root / name
        profile_generator.write_sources(self.candidate, self.base_source, output_dir)
        return output_dir

    @staticmethod
    def _read_manifest(path: Path) -> dict[str, object]:
        return json.loads(path.read_bytes())

    @staticmethod
    def _write_manifest(path: Path, value: dict[str, object]) -> None:
        path.write_bytes(profile_generator.canonical_bytes(value))

    def _override_candidate_read(self, candidate_bytes: bytes):
        original_read = validator._read_regular_file

        def read(path: Path, maximum: int, where: str) -> tuple[Path, bytes]:
            if where == "checked-in candidate":
                return path, candidate_bytes
            return original_read(path, maximum, where)

        return patch.object(validator, "_read_regular_file", side_effect=read)

    def _override_generator(self, mutate):
        original_execute = validator._execute_generator_snapshot

        def execute(path: Path, source: bytes):
            generator = original_execute(path, source)
            mutate(generator)
            return generator

        return patch.object(validator, "_execute_generator_snapshot", side_effect=execute)

    def _assert_rejected(self, manifest_path: Path, message: str) -> None:
        with self.assertRaisesRegex(validator.StructuralProfileSourceManifestError, message):
            validator.validate_structural_profile_source_manifest(manifest_path)

    def test_import_does_not_mutate_sys_path(self) -> None:
        module_name = "structural_profile_manifest_import_path_test"
        original_path = sys.path.copy()
        unconfigured_path = [entry for entry in original_path if entry != str(EXPERIMENT_ROOT)]
        self.assertNotIn(str(EXPERIMENT_ROOT), unconfigured_path)

        try:
            with patch.object(sys, "path", unconfigured_path):
                _load_module(module_name, VISUAL_REVIEW_ROOT / "structural_profile_source_manifest.py")
                self.assertEqual(sys.path, unconfigured_path)
        finally:
            sys.modules.pop(module_name, None)

        self.assertEqual(sys.path, original_path)

    def test_validation_works_without_experiment_root_on_sys_path(self) -> None:
        original_path = sys.path.copy()
        unconfigured_path = [entry for entry in original_path if entry != str(EXPERIMENT_ROOT)]
        helper_before = sys.modules.get("structural_atomic_publish")

        with patch.object(sys, "path", unconfigured_path):
            path_before_validation = sys.path.copy()
            result = validator.validate_structural_profile_source_manifest(self.manifest_path)
            self.assertEqual(sys.path, path_before_validation)
            self.assertEqual(result.profile_ids, tuple(PROFILE_IDS))
            self.assertIs(sys.modules.get("structural_atomic_publish"), helper_before)

        self.assertEqual(sys.path, original_path)

    def test_generator_snapshot_restores_process_state_after_success_and_failure(self) -> None:
        generator_path = validator.EXPERIMENT_ROOT / "generate_structural_profile_sources.py"
        _, generator_bytes = validator._read_regular_file(
            generator_path,
            validator.MAX_GENERATOR_BYTES,
            "active profile generator",
        )
        original_path = sys.path.copy()
        unconfigured_path = [entry for entry in original_path if entry != str(EXPERIMENT_ROOT)]
        missing = object()
        helper_before = sys.modules.pop("structural_atomic_publish", missing)

        try:
            with patch.object(sys, "path", unconfigured_path):
                path_before_success = sys.path.copy()
                modules_before_success = sys.modules.copy()
                snapshot = validator._execute_generator_snapshot(generator_path, generator_bytes)
                self.assertIsInstance(
                    snapshot.structural_atomic_publish,
                    validator._UnavailableGeneratorDependency,
                )
                self.assertNotIn("structural_atomic_publish", sys.modules)
                self.assertEqual(sys.path, path_before_success)
                self.assertEqual(sys.modules, modules_before_success)

                failing_source = generator_bytes + b"\nstructural_atomic_publish.AtomicPublishError\n"
                path_before_failure = sys.path.copy()
                modules_before_failure = sys.modules.copy()
                with self.assertRaisesRegex(
                    validator.StructuralProfileSourceManifestError,
                    "active profile generator snapshot could not be executed",
                ):
                    validator._execute_generator_snapshot(generator_path, failing_source)
                self.assertNotIn("structural_atomic_publish", sys.modules)
                self.assertEqual(sys.path, path_before_failure)
                self.assertEqual(sys.modules, modules_before_failure)
        finally:
            if helper_before is missing:
                sys.modules.pop("structural_atomic_publish", None)
            else:
                sys.modules["structural_atomic_publish"] = helper_before

        self.assertEqual(sys.path, original_path)

    def test_valid_bundle_returns_ordered_immutable_records_and_lineage(self) -> None:
        result = validator.validate_structural_profile_source_manifest(self.manifest_path)
        manifest_value = self._read_manifest(self.manifest_path)

        self.assertEqual(result.profile_ids, tuple(PROFILE_IDS))
        self.assertEqual([source.id for source in result.sources], PROFILE_IDS)
        self.assertEqual(result.manifest.path, self.manifest_path.absolute())
        self.assertEqual(result.manifest.bytes, self.manifest_path.stat().st_size)
        self.assertEqual(
            result.manifest.sha256,
            hashlib.sha256(self.manifest_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(result.manifest.format, validator.SOURCE_MANIFEST_FORMAT)
        self.assertEqual(result.manifest.candidate_format, profile_generator.FORMAT)
        self.assertEqual(
            result.manifest.candidate_sha256,
            manifest_value["source"]["candidate_sha256"],  # type: ignore[index]
        )
        self.assertEqual(
            result.manifest.base_source_sha256,
            manifest_value["source"]["source_sha256"],  # type: ignore[index]
        )
        self.assertEqual(result.generator.mode, profile_generator.DEFAULT_GENERATION_MODE)
        self.assertEqual(result.generator.format, profile_generator.FORMAT)
        self.assertEqual(result.generator.source_document_suffix, profile_generator.SOURCE_DOCUMENT_SUFFIX)
        self.assertEqual(result.generator.profile_ids, tuple(PROFILE_IDS))
        self.assertEqual(result.generator.candidate_path, profile_generator.DEFAULT_CANDIDATE.absolute())
        self.assertEqual(result.generator.base_source_path, profile_generator.DEFAULT_SOURCE.absolute())
        self.assertEqual(
            result.generator.candidate_sha256,
            hashlib.sha256(profile_generator.DEFAULT_CANDIDATE.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            result.generator.base_source_sha256,
            hashlib.sha256(profile_generator.DEFAULT_SOURCE.read_bytes()).hexdigest(),
        )

        for profile_id, source in zip(PROFILE_IDS, result.sources, strict=True):
            record = next(item for item in manifest_value["profiles"] if item["id"] == profile_id)  # type: ignore[index]
            self.assertEqual(source.path, (self.source_dir / f"{profile_id}.json").absolute())
            self.assertEqual(source.document, record["document"])
            self.assertEqual(source.namespace, "main")
            self.assertEqual(source.bytes, record["bytes"])
            self.assertEqual(source.sha256, record["sha256"])
            self.assertEqual(source.tail_signature, tuple(record["tail_signature"]))
            self.assertEqual(source.provenance.document, source.document)
            self.assertEqual(source.provenance.namespace, source.namespace)
            self.assertEqual(source.provenance.dependencies, ())

        with self.assertRaises(FrozenInstanceError):
            result.profile_ids = ()  # type: ignore[misc]

    def test_validator_identity_uses_retained_executed_source_after_live_path_replacement(self) -> None:
        source_bytes = (VISUAL_REVIEW_ROOT / "structural_profile_source_manifest.py").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            live_path = Path(directory) / "structural_profile_source_manifest.py"
            live_path.write_bytes(source_bytes)
            snapshot_module = _load_module(
                "structural_profile_manifest_live_replacement_test",
                live_path,
            )
            live_path.write_bytes(b"raise RuntimeError('replacement must not be hashed')\n")
            identity = snapshot_module._implementation_source_identity()

        self.assertEqual(identity["id"], validator.VALIDATOR_IMPLEMENTATION_ID)
        self.assertEqual(identity["bytes"], len(source_bytes))
        self.assertEqual(identity["sha256"], hashlib.sha256(source_bytes).hexdigest())

    def test_profile_order_is_exact(self) -> None:
        manifest = self._read_manifest(self.manifest_path)
        profiles = manifest["profiles"]  # type: ignore[index]
        profiles[0], profiles[1] = profiles[1], profiles[0]  # type: ignore[index]
        self._write_manifest(self.manifest_path, manifest)
        self._assert_rejected(self.manifest_path, "exact required order")

    def test_document_bytes_and_hash_claims_are_checked(self) -> None:
        mutations = (
            ("document", "wrong_document", "document does not bind its profile id"),
            ("bytes", 1, "bytes does not match the canonical generated source"),
            ("sha256", "0" * 64, "sha256 does not match the canonical generated source"),
        )
        for field, replacement, message in mutations:
            with self.subTest(field=field):
                source_dir = self._make_bundle(f"mutated-{field}")
                manifest_path = source_dir / "manifest.json"
                manifest = self._read_manifest(manifest_path)
                manifest["profiles"][0][field] = replacement  # type: ignore[index]
                self._write_manifest(manifest_path, manifest)
                self._assert_rejected(manifest_path, message)

    def test_directory_inventory_rejects_extra_missing_symlink_and_unsafe_path(self) -> None:
        extra_dir = self._make_bundle("extra")
        (extra_dir / "unexpected.json").write_bytes(b"{}\n")
        self._assert_rejected(extra_dir / "manifest.json", "exact file set")

        missing_dir = self._make_bundle("missing")
        (missing_dir / f"{PROFILE_IDS[-1]}.json").unlink()
        self._assert_rejected(missing_dir / "manifest.json", "exact file set")

        symlink_dir = self._make_bundle("symlink")
        linked_target = self.root / "symlink-target.json"
        linked_source = symlink_dir / f"{PROFILE_IDS[0]}.json"
        linked_target.write_bytes(linked_source.read_bytes())
        linked_source.unlink()
        linked_source.symlink_to(linked_target)
        self._assert_rejected(symlink_dir / "manifest.json", "unsafe entry")

        path_dir = self._make_bundle("path")
        path_manifest = path_dir / "manifest.json"
        manifest = self._read_manifest(path_manifest)
        manifest["profiles"][0]["file"] = "../escape.json"  # type: ignore[index]
        self._write_manifest(path_manifest, manifest)
        self._assert_rejected(path_manifest, "canonical profile path")

    def test_final_directory_recheck_rejects_inventory_and_hash_mutation(self) -> None:
        original_scan = validator._scan_source_directory

        calls = 0

        def add_late_entry(
            root: Path,
            expected_entries: set[str],
            **kwargs: object,
        ):
            nonlocal calls
            calls += 1
            if calls == 2:
                (root / "late-entry.json").write_bytes(b"{}\n")
            return original_scan(root, expected_entries, **kwargs)

        with patch.object(validator, "_scan_source_directory", side_effect=add_late_entry):
            self._assert_rejected(self.manifest_path, "exact file set")
        self.assertEqual(calls, 2)

        hash_dir = self._make_bundle("late-hash-mutation")
        hash_manifest = hash_dir / "manifest.json"
        calls = 0

        def mutate_final_bytes(
            root: Path,
            expected_entries: set[str],
            **kwargs: object,
        ):
            nonlocal calls
            calls += 1
            if calls == 2:
                source = root / f"{PROFILE_IDS[0]}.json"
                source.write_bytes(source.read_bytes() + b" ")
            return original_scan(root, expected_entries, **kwargs)

        with patch.object(validator, "_scan_source_directory", side_effect=mutate_final_bytes):
            self._assert_rejected(hash_manifest, "entry changed during validation")
        self.assertEqual(calls, 2)

        swap_dir = self._make_bundle("late-directory-swap")
        swap_manifest = swap_dir / "manifest.json"
        calls = 0

        def swap_final_directory(
            root: Path,
            expected_entries: set[str],
            **kwargs: object,
        ):
            nonlocal calls
            calls += 1
            if calls == 2:
                original = root.with_name(root.name + "-original")
                root.rename(original)
                root.mkdir()
            return original_scan(root, expected_entries, **kwargs)

        with patch.object(validator, "_scan_source_directory", side_effect=swap_final_directory):
            self._assert_rejected(swap_manifest, "directory changed during validation")
        self.assertEqual(calls, 2)

    def test_manifest_candidate_and_base_hashes_bind_checked_in_inputs(self) -> None:
        candidate_hash_dir = self._make_bundle("wrong-candidate-hash")
        candidate_hash_manifest = candidate_hash_dir / "manifest.json"
        candidate_hash_value = self._read_manifest(candidate_hash_manifest)
        candidate_hash_value["source"]["candidate_sha256"] = "0" * 64  # type: ignore[index]
        self._write_manifest(candidate_hash_manifest, candidate_hash_value)
        self._assert_rejected(candidate_hash_manifest, "candidate hash does not match")

        base_hash_dir = self._make_bundle("wrong-base-hash")
        base_hash_manifest = base_hash_dir / "manifest.json"
        base_hash_value = self._read_manifest(base_hash_manifest)
        base_hash_value["source"]["source_sha256"] = "0" * 64  # type: ignore[index]
        self._write_manifest(base_hash_manifest, base_hash_value)
        self._assert_rejected(base_hash_manifest, "base-source hash does not match")

    def test_candidate_internal_base_hash_is_also_bound(self) -> None:
        candidate = json.loads(self.candidate.read_bytes())
        candidate["base_source"]["sha256"] = "0" * 64
        candidate_path = self.root / "candidate-with-wrong-base-hash.json"
        candidate_bytes = profile_generator.canonical_bytes(candidate)
        candidate_path.write_bytes(candidate_bytes)

        manifest = self._read_manifest(self.manifest_path)
        manifest["source"]["candidate_sha256"] = hashlib.sha256(candidate_bytes).hexdigest()  # type: ignore[index]
        self._write_manifest(self.manifest_path, manifest)
        with self._override_candidate_read(candidate_bytes):
            self._assert_rejected(self.manifest_path, "candidate base-source hash does not match")

    def test_candidate_base_source_path_must_match_default_source(self) -> None:
        canonical_path = profile_generator.DEFAULT_SOURCE.relative_to(REPOSITORY_ROOT).as_posix()
        replacements = (
            ("empty", ""),
            ("absolute", str(profile_generator.DEFAULT_SOURCE.absolute())),
            ("traversal", "../" + canonical_path),
            ("alternate", canonical_path.replace("/", "/./", 1)),
            ("mismatch", "examples/body-documents/other-source.json"),
        )
        for label, replacement in replacements:
            with self.subTest(path=label):
                source_dir = self._make_bundle(f"candidate-base-path-{label}")
                manifest_path = source_dir / "manifest.json"
                candidate = json.loads(self.candidate.read_bytes())
                candidate["base_source"]["path"] = replacement
                candidate_bytes = profile_generator.canonical_bytes(candidate)
                manifest = self._read_manifest(manifest_path)
                manifest["source"]["candidate_sha256"] = hashlib.sha256(candidate_bytes).hexdigest()  # type: ignore[index]
                self._write_manifest(manifest_path, manifest)
                with self._override_candidate_read(candidate_bytes):
                    self._assert_rejected(
                        manifest_path,
                        "candidate base-source path does not match the active generator default source",
                    )

    def test_active_generator_mode_and_format_are_bound(self) -> None:
        def historical_mode(generator) -> None:
            generator.DEFAULT_GENERATION_MODE = generator.HISTORICAL_GENERATION_MODE

        with self._override_generator(historical_mode):
            self._assert_rejected(self.manifest_path, "active profile generator mode")

        def drifted_format(generator) -> None:
            generator.FORMAT = "drifted-candidate-format"

        with self._override_generator(drifted_format):
            self._assert_rejected(self.manifest_path, "candidate format is not the active generator format")

    def test_regenerator_output_order_and_provenance_are_bound(self) -> None:
        def reversed_outputs(generator) -> None:
            original_generate = generator.generate_sources

            def reversed_sources(candidate: object, base_source: object, *, mode: str) -> list[dict[str, object]]:
                return list(reversed(original_generate(candidate, base_source, mode=mode)))

            generator.generate_sources = reversed_sources

        with self._override_generator(reversed_outputs):
            self._assert_rejected(self.manifest_path, r"regenerated source\[0\] source provenance")

    def test_generator_hash_and_executed_code_share_one_race_safe_snapshot(self) -> None:
        generator_path = validator.EXPERIMENT_ROOT / "generate_structural_profile_sources.py"
        original_read = validator._read_regular_file
        _, generator_a = original_read(
            generator_path,
            validator.MAX_GENERATOR_BYTES,
            "active profile generator",
        )
        marker = b'DEFAULT_GENERATION_MODE = "active-five-profile"'
        replacement = b'DEFAULT_GENERATION_MODE = "historical-structural-embodiment-v1"'
        self.assertIn(marker, generator_a)
        generator_b = generator_a.replace(marker, replacement, 1)

        def read(path: Path, maximum: int, where: str) -> tuple[Path, bytes]:
            if where == "active profile generator":
                return path, generator_b
            return original_read(path, maximum, where)

        with patch.object(validator, "_read_regular_file", side_effect=read):
            self._assert_rejected(self.manifest_path, "active profile generator mode")


if __name__ == "__main__":
    unittest.main()

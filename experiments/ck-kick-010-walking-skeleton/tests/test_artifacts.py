import hashlib
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ck_spike import artifacts
from ck_spike.diagnostics import Phase


class CanonicalArtifactTests(unittest.TestCase):
    def test_canonical_json_is_stable_utf8_and_has_one_newline(self):
        value = {"z": "é", "a": [1, True], "nested": {"b": 2, "a": 1}}
        expected = b'{"a":[1,true],"nested":{"a":1,"b":2},"z":"\xc3\xa9"}\n'
        self.assertEqual(artifacts.canonical_json_bytes(value), expected)
        self.assertEqual(artifacts.canonical_json_bytes(value), artifacts.canonical_json_bytes({"a": [1, True], "z": "é", "nested": {"a": 1, "b": 2}}))

    def test_canonical_json_rejects_nonfinite_values(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                artifacts.canonical_json_bytes({"value": value})

    def test_sha256_known_vector(self):
        data = b"abc"
        self.assertEqual(
            artifacts.sha256_bytes(data),
            hashlib.sha256(data).hexdigest(),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.bin"
            path.write_bytes(data)
            self.assertEqual(artifacts.sha256_file(path), hashlib.sha256(data).hexdigest())

    def test_sha256_file_rejects_symlinks_and_other_non_regular_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            regular = root / "regular"
            regular.write_bytes(b"outside")
            symlink = root / "symlink"
            symlink.symlink_to(regular)
            directory = root / "directory"
            directory.mkdir()

            for path in (symlink, directory):
                with self.subTest(path=path.name), self.assertRaises(ValueError):
                    artifacts.sha256_file(path)

            fifo = root / "fifo"
            if hasattr(os, "mkfifo"):
                os.mkfifo(fifo)
                with self.assertRaises(ValueError):
                    artifacts.sha256_file(fifo)

            socket_path = root / "socket"
            socket_file = None
            try:
                if hasattr(socket, "AF_UNIX"):
                    socket_file = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    socket_file.bind(str(socket_path))
                    with self.assertRaises(ValueError):
                        artifacts.sha256_file(socket_path)
            finally:
                if socket_file is not None:
                    socket_file.close()

    def test_manifest_hashes_supplied_files_without_self_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mesh.ply"
            path.write_bytes(b"mesh")
            manifest = artifacts.build_manifest(
                {"resolved_graph.json": b"graph", "mesh.ply": path}
            )
            self.assertEqual(
                manifest["artifacts"],
                {
                    "mesh.ply": artifacts.sha256_bytes(b"mesh"),
                    "resolved_graph.json": artifacts.sha256_bytes(b"graph"),
                },
            )
            self.assertNotIn("manifest.json", manifest["artifacts"])
            self.assertEqual(
                artifacts.manifest_bytes({"mesh.ply": b"mesh"}),
                artifacts.canonical_json_bytes(
                    artifacts.build_manifest({"mesh.ply": b"mesh"})
                ),
            )

    def test_build_identity_separates_input_environment_and_caller_identities(self):
        identity = artifacts.build_identity(
            spike_revision=1,
            seed=7,
            input_payload={"nodes": ["torso"]},
            config_payload={"resolution": 128},
            compiler_identity="compiler-rev",
            source_identity="source-rev",
            dependency_versions={"numpy": "1", "scikit-image": "2", "trimesh": "3"},
        )
        self.assertEqual(identity["compiler_identity"], "compiler-rev")
        self.assertEqual(identity["source_identity"], "source-rev")
        self.assertEqual(identity["seed"], 7)
        self.assertEqual(set(identity["dependencies"]), {"numpy", "scikit-image", "trimesh"})
        self.assertNotIn("artifact_hashes", identity)
        self.assertNotIn("source_node_labels", identity)
        json.loads(artifacts.canonical_json_bytes(identity))


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.parent = self.root / "outputs"
        self.parent.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _bundle():
        return artifacts.add_manifest(
            {
                "diagnostics.json": b'{"ok":true}\n',
                "resolved_graph.json": b'{"nodes":[]}\n',
            }
        )

    @staticmethod
    def _validator(staging):
        names = sorted(
            str(path.relative_to(staging)).replace(os.sep, "/")
            for path in staging.rglob("*")
            if path.is_file()
        )
        return names == ["diagnostics.json", "manifest.json", "resolved_graph.json"]

    def test_successful_publish_to_new_target(self):
        target = self.parent / "bundle"
        result = artifacts.publish_bundle(target, self._bundle(), self._validator)
        self.assertEqual(result.target, target.resolve())
        self.assertTrue(target.is_dir())
        self.assertEqual(set(result.artifact_names), set(self._bundle()))
        self.assertFalse(any(path.name.startswith(".bundle.staging-") for path in self.parent.iterdir()))

    def test_existing_file_directory_and_symlink_are_refused_unchanged(self):
        existing_file = self.parent / "file"
        existing_file.write_bytes(b"keep")
        existing_directory = self.parent / "directory"
        existing_directory.mkdir()
        (existing_directory / "keep").write_bytes(b"keep")
        existing_symlink = self.parent / "symlink"
        existing_symlink.symlink_to(existing_file)

        for target, expected in (
            (existing_file, b"keep"),
            (existing_directory, None),
            (existing_symlink, b"keep"),
        ):
            with self.assertRaises(artifacts.ArtifactPublicationError) as raised:
                artifacts.publish_bundle(target, self._bundle(), self._validator)
            self.assertEqual(raised.exception.diagnostics[0].phase, Phase.PUBLICATION)
            self.assertEqual(raised.exception.diagnostics[0].code, "OUTPUT_TARGET_EXISTS")
            if expected is not None:
                self.assertEqual(target.read_bytes(), expected)
        self.assertTrue((existing_directory / "keep").exists())
        self.assertTrue(existing_symlink.is_symlink())

    def test_root_home_repository_and_host_targets_are_refused(self):
        protected = {
            Path(os.path.abspath(os.sep)),
            Path.home(),
            self.root / "repository",
            self.root / "host",
        }
        for target in protected:
            target.mkdir(parents=True, exist_ok=True)
            kwargs = {}
            if target.name == "repository":
                kwargs["repository_root"] = target
            if target.name == "host":
                kwargs["disposable_host_root"] = target
            with self.assertRaises(artifacts.ArtifactPublicationError) as raised:
                artifacts.publish_bundle(target, self._bundle(), self._validator, **kwargs)
            self.assertEqual(raised.exception.diagnostics[0].code, "PROTECTED_OUTPUT_TARGET")

    def test_nonexistent_or_symlink_parent_is_refused(self):
        for target in (self.root / "missing" / "bundle", self.root / "linked" / "bundle"):
            if target.parent.name == "linked":
                target.parent.symlink_to(self.parent, target_is_directory=True)
            with self.assertRaises(artifacts.ArtifactPublicationError) as raised:
                artifacts.publish_bundle(target, self._bundle(), self._validator)
            self.assertEqual(raised.exception.diagnostics[0].code, "INVALID_OUTPUT_PARENT")

    def test_writer_or_validator_failure_cleans_only_invocation_staging(self):
        sibling = self.parent / "sibling"
        sibling.mkdir()
        (sibling / "keep").write_bytes(b"keep")

        def failing_writer(staging):
            (staging / "partial").write_bytes(b"partial")
            raise RuntimeError("writer failed")

        target = self.parent / "writer-failure"
        with self.assertRaises(artifacts.ArtifactPublicationError):
            artifacts.publish_bundle(target, failing_writer, self._validator)
        self.assertFalse(target.exists())
        self.assertEqual((sibling / "keep").read_bytes(), b"keep")
        self.assertEqual(list(self.parent.glob(".*.staging-*")), [])

        target = self.parent / "validator-failure"
        with self.assertRaises(artifacts.ArtifactPublicationError):
            artifacts.publish_bundle(target, self._bundle(), lambda _staging: False)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.parent.glob(".*.staging-*")), [])

    def test_non_regular_writer_entry_is_rejected_before_validator_or_publication(self):
        target = self.parent / "non-regular"
        external = self.parent / "external"
        external.write_bytes(b"must remain untouched")
        validator_called = False

        def writer(staging):
            (staging / "diagnostics.json").symlink_to(external)

        def validator(_staging):
            nonlocal validator_called
            validator_called = True
            return True

        with self.assertRaises(artifacts.ArtifactPublicationError) as raised:
            artifacts.publish_bundle(target, writer, validator)

        self.assertEqual(raised.exception.diagnostics[0].code, "BUNDLE_VALIDATION_FAILED")
        self.assertFalse(validator_called)
        self.assertFalse(target.exists())
        self.assertEqual(external.read_bytes(), b"must remain untouched")
        self.assertEqual(list(self.parent.glob(".*.staging-*")), [])

    def test_target_appearing_race_leaves_target_and_sibling_untouched(self):
        target = self.parent / "race"
        sibling = self.parent / "sibling"
        sibling.mkdir(exist_ok=True)
        (sibling / "keep").write_bytes(b"keep")

        def appears_during_publish(staging, destination):
            destination.mkdir()
            (destination / "preexisting").write_bytes(b"do not replace")
            raise FileExistsError("simulated race")

        with mock.patch.object(artifacts, "_atomic_rename_noreplace", appears_during_publish):
            with self.assertRaises(artifacts.ArtifactPublicationError) as raised:
                artifacts.publish_bundle(target, self._bundle(), self._validator)
        self.assertEqual(raised.exception.diagnostics[0].code, "OUTPUT_TARGET_APPEARED")
        self.assertEqual((target / "preexisting").read_bytes(), b"do not replace")
        self.assertEqual((sibling / "keep").read_bytes(), b"keep")
        self.assertEqual(list(self.parent.glob(".*.staging-*")), [])

    def test_diagnostics_only_shape_is_caller_validated_and_can_publish(self):
        target = self.parent / "invalid-fixture"
        bundle = artifacts.add_manifest({"diagnostics.json": b'{"ok":false}\n'})

        def diagnostics_only_validator(staging):
            return sorted(path.name for path in staging.iterdir()) == [
                "diagnostics.json",
                "manifest.json",
            ]

        result = artifacts.publish_bundle(target, bundle, diagnostics_only_validator)
        self.assertTrue(result.target.is_dir())
        self.assertFalse((target / "mesh.ply").exists())
        self.assertEqual(json.loads((target / "diagnostics.json").read_text()), {"ok": False})


if __name__ == "__main__":
    unittest.main()

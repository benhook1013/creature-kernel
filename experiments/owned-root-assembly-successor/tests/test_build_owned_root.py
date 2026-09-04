from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import artifact_serialization as artifacts  # noqa: E402


class CanonicalArtifactTests(unittest.TestCase):
    def test_canonical_json_is_compact_utf8_and_has_no_trailing_lf(self) -> None:
        value = {"z": "é", "a": [1, True], "nested": {"b": 2, "a": 1}}
        self.assertEqual(
            artifacts.canonical_json_bytes(value),
            b'{"a":[1,true],"nested":{"a":1,"b":2},"z":"\xc3\xa9"}',
        )

    def test_binary64_zeros_have_one_wire_spelling_and_nonfinite_values_fail(self) -> None:
        self.assertEqual(
            artifacts.canonical_json_bytes({"positive": 0.0, "negative": -0.0}),
            b'{"negative":0,"positive":0}',
        )
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.canonical_json_bytes({"value": value})

    def test_coordinate_and_triangle_hash_domains_are_exact(self) -> None:
        coordinates = ((1.0, -0.0, 2.5),)
        triangles = ((0, 1, 2), (-1, 4, 8))
        expected_coordinates = b"".join(
            value.to_bytes(8, "little", signed=False)
            for value in (0x3FF0000000000000, 0x8000000000000000, 0x4004000000000000)
        )
        self.assertEqual(artifacts.coordinate_hash_bytes(coordinates), expected_coordinates)
        expected_triangles = b"".join(
            int(value).to_bytes(8, "little", signed=True)
            for row in triangles
            for value in row
        )
        self.assertEqual(artifacts.triangle_index_hash_bytes(triangles), expected_triangles)
        self.assertEqual(
            artifacts.sha256_bytes(artifacts.coordinate_hash_bytes(coordinates)),
            hashlib.sha256(expected_coordinates).hexdigest(),
        )

    def test_canonical_decode_rejects_duplicates_and_noncanonical_bytes(self) -> None:
        with self.assertRaises(artifacts.ArtifactSerializationError):
            artifacts.decode_canonical_json(b'{"a":1,"a":2}')
        with self.assertRaises(artifacts.ArtifactSerializationError):
            artifacts.decode_canonical_json(b'{"a": 1}')
        self.assertEqual(artifacts.decode_canonical_json(b'{"a":0}'), {"a": 0})
        self.assertEqual(artifacts.coerce_binary64(0), 0.0)
        with self.assertRaises(artifacts.ArtifactSerializationError):
            artifacts.coerce_binary64(1)


class FileAdmissionTests(unittest.TestCase):
    def test_regular_file_record_hashes_exact_bytes_and_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload.bin"
            payload.write_bytes(b"payload")
            record = artifacts.regular_file_record(payload, "seed/payload.bin")
            self.assertEqual(record["bytes"], 7)
            self.assertEqual(record["sha256"], hashlib.sha256(b"payload").hexdigest())
            self.assertEqual(artifacts.regular_file_record(payload, "seed/payload.bin"), record)
            link = root / "link"
            link.symlink_to(payload)
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.regular_file_record(link, "seed/link")
            hardlink = root / "hardlink"
            os.link(payload, hardlink)
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.regular_file_record(payload, "seed/payload.bin")
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.validate_role_path("../payload.bin")
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.regular_file_record(payload, "")

    def test_sidecar_is_exact_one_lf_terminated_line(self) -> None:
        digest = hashlib.sha256(b"contract").hexdigest()
        expected = f"{digest}  {artifacts.CONTRACT_ROLE}\n".encode("ascii")
        self.assertEqual(artifacts.contract_sidecar_bytes(digest), expected)
        artifacts.validate_contract_sidecar(expected, digest)
        with self.assertRaises(artifacts.ArtifactSerializationError):
            artifacts.validate_contract_sidecar(expected + b"\n", digest)
        with self.assertRaises(TypeError):
            artifacts.contract_sidecar_bytes(digest, contract_role="alternate")
        with self.assertRaises(TypeError):
            artifacts.validate_contract_sidecar(
                expected, digest, contract_role="alternate"
            )
        with tempfile.TemporaryDirectory() as directory:
            sidecar = Path(directory) / "design-contract.sha256"
            self.assertEqual(
                artifacts.write_contract_sidecar_no_replace(sidecar, digest), sidecar
            )
            self.assertEqual(sidecar.read_bytes(), expected)
            with self.assertRaises(TypeError):
                artifacts.write_contract_sidecar_no_replace(
                    Path(directory) / "alternate.sha256",
                    digest,
                    contract_role="alternate",
                )

    def test_closed_inventory_requires_exact_regular_file_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_bytes(b"a")
            (root / "nested").mkdir()
            (root / "nested" / "b").write_bytes(b"b")
            records = artifacts.closed_inventory(root, ("a", "nested/b"))
            self.assertEqual(tuple(record["role_path"] for record in records), ("a", "nested/b"))
            (root / "extra").write_bytes(b"extra")
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.closed_inventory(root, ("a", "nested/b"))

    def test_closed_inventory_rejects_hardlinked_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            alias = root / "alias"
            payload.write_bytes(b"payload")
            os.link(payload, alias)
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.closed_inventory(root, ("payload",))

    def test_closed_inventory_rejects_unexpected_directory_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_bytes(b"a")
            (root / "empty").mkdir()
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.closed_inventory(root, ("a",))
            (root / "empty").rmdir()
            (root / "link").symlink_to(root / "a")
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.closed_inventory(root, ("a",))

    def test_closed_inventory_rejects_deterministic_insertion_and_removal(self) -> None:
        for operation in ("insert", "remove"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                payload = root / "payload"
                payload.write_bytes(b"payload")
                original_listdir = artifacts.os.listdir
                calls = 0

                def listdir(path):
                    nonlocal calls
                    names = original_listdir(path)
                    if isinstance(path, int) and calls == 0:
                        calls += 1
                        if operation == "insert":
                            (root / "inserted").write_bytes(b"race")
                        else:
                            payload.unlink()
                    return names

                with mock.patch.object(artifacts.os, "listdir", side_effect=listdir):
                    with self.assertRaises(artifacts.ArtifactSerializationError):
                        artifacts.closed_inventory(root, ("payload",))

    def test_closed_inventory_rejects_deterministic_same_name_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            payload.write_bytes(b"original")
            moved = root / "moved"
            original_pread = artifacts.os.pread
            replaced = False

            def pread(fd, count, offset):
                nonlocal replaced
                data = original_pread(fd, count, offset)
                if data and not replaced:
                    replaced = True
                    payload.rename(moved)
                    payload.write_bytes(b"replacement")
                return data

            with mock.patch.object(artifacts.os, "pread", side_effect=pread):
                with self.assertRaises(artifacts.ArtifactSerializationError):
                    artifacts.closed_inventory(root, ("payload",))

    def test_closed_inventory_rejects_expected_nested_directory_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            (nested / "payload").write_bytes(b"original")
            moved = root / "nested-moved"
            original_stat = artifacts.os.stat
            replaced = False

            def stat(path, *args, **kwargs):
                nonlocal replaced
                result = original_stat(path, *args, **kwargs)
                if path == "nested" and kwargs.get("dir_fd") is not None and not replaced:
                    replaced = True
                    nested.rename(moved)
                    nested.mkdir()
                    (nested / "payload").write_bytes(b"replacement")
                return result

            with mock.patch.object(artifacts.os, "stat", side_effect=stat):
                with self.assertRaises(artifacts.ArtifactSerializationError):
                    artifacts.closed_inventory(root, ("nested/payload",))

    def test_regular_file_read_rejects_real_same_size_pwrite_between_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory) / "payload"
            chunk_size = 1024 * 1024
            payload.write_bytes(b"a" * (chunk_size * 2))
            writer_fd = os.open(payload, os.O_WRONLY)
            original_pread = artifacts.os.pread
            mutated = False

            def pread(fd, count, offset):
                nonlocal mutated
                data = original_pread(fd, count, offset)
                if offset == 0 and data and not mutated:
                    mutated = True
                    self.assertEqual(os.pwrite(writer_fd, b"b", chunk_size), 1)
                return data

            try:
                with mock.patch.object(artifacts.os, "pread", side_effect=pread):
                    with self.assertRaises(artifacts.ArtifactSerializationError):
                        artifacts.read_regular_file(payload)
            finally:
                os.close(writer_fd)

    def test_regular_file_read_rechecks_requested_path_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            moved = root / "moved"
            payload.write_bytes(b"original")
            original_read = artifacts._read_stable_with_identity

            def read_then_replace(parent_fd, name, max_bytes):
                result = original_read(parent_fd, name, max_bytes)
                payload.rename(moved)
                payload.write_bytes(b"replacement")
                return result

            with mock.patch.object(artifacts, "_read_stable_with_identity",
                                   side_effect=read_then_replace):
                with self.assertRaises(artifacts.ArtifactSerializationError):
                    artifacts.read_regular_file(payload)

    def test_regular_file_read_rejects_deterministic_same_size_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory) / "payload"
            payload.write_bytes(b"original")
            original_pread = artifacts.os.pread
            mutated = False

            def pread(fd, count, offset):
                nonlocal mutated
                data = original_pread(fd, count, offset)
                if data and not mutated:
                    mutated = True
                    payload.write_bytes(b"mutated!")
                return data

            with mock.patch.object(artifacts.os, "pread", side_effect=pread):
                with self.assertRaises(artifacts.ArtifactSerializationError):
                    artifacts.read_regular_file(payload)


class PublicationTests(unittest.TestCase):
    def test_atomic_json_write_and_no_replace_preserve_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "artifact.json"
            artifacts.write_canonical_json_no_replace(target, {"ok": True})
            self.assertEqual(target.read_bytes(), b'{"ok":true}')
            with self.assertRaises(FileExistsError):
                artifacts.write_canonical_json_no_replace(target, {"ok": False})
            self.assertEqual(target.read_bytes(), b'{"ok":true}')
            self.assertEqual(
                [path.name for path in root.iterdir()],
                ["artifact.json"],
            )

    def test_directory_publication_is_atomic_and_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / ".bundle.stage"
            target = root / "bundle"
            stage.mkdir()
            (stage / "payload").write_bytes(b"new")
            self.assertEqual(artifacts.publish_no_replace(stage, target), target)
            self.assertEqual((target / "payload").read_bytes(), b"new")
            second = root / ".second.stage"
            second.mkdir()
            (second / "payload").write_bytes(b"replacement")
            with self.assertRaises(FileExistsError):
                artifacts.publish_no_replace(second, target)
            self.assertEqual((target / "payload").read_bytes(), b"new")

    def test_publication_rejects_hardlinked_staging_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            alias = root / "alias"
            target = root / "target"
            stage.write_bytes(b"staged")
            os.link(stage, alias)
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.publish_no_replace(stage, target)
            self.assertFalse(target.exists())
            self.assertEqual(stage.read_bytes(), b"staged")
            self.assertEqual(alias.read_bytes(), b"staged")

    def test_parent_fsync_failure_rolls_exact_file_back_to_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            stage.write_bytes(b"staged")

            def fail_fsync(_descriptor):
                raise OSError("injected parent fsync failure")

            with mock.patch.object(artifacts.os, "fsync", side_effect=fail_fsync):
                with self.assertRaisesRegex(OSError, "injected parent fsync failure"):
                    artifacts.publish_no_replace(stage, target)
            self.assertFalse(target.exists())
            self.assertEqual(stage.read_bytes(), b"staged")

    def test_published_hardlink_is_rejected_and_alias_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            alias = root / "alias"
            stage.write_bytes(b"staged")

            def hardlink_then_fail(_descriptor):
                os.link(target, alias)
                raise OSError("injected parent fsync failure")

            with mock.patch.object(artifacts.os, "fsync", side_effect=hardlink_then_fail):
                with self.assertRaisesRegex(OSError, "injected parent fsync failure"):
                    artifacts.publish_no_replace(stage, target)
            self.assertFalse(target.exists())
            self.assertEqual(stage.read_bytes(), b"staged")
            self.assertEqual(alias.read_bytes(), b"staged")

    def test_directory_fsync_failure_rolls_back_whole_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            stage.mkdir()
            (stage / "payload").write_bytes(b"staged")

            def fail_fsync(_descriptor):
                raise OSError("injected parent fsync failure")

            with mock.patch.object(artifacts.os, "fsync", side_effect=fail_fsync):
                with self.assertRaisesRegex(OSError, "injected parent fsync failure"):
                    artifacts.publish_no_replace(stage, target)
            self.assertFalse(target.exists())
            self.assertEqual((stage / "payload").read_bytes(), b"staged")

    def test_directory_mutation_is_rolled_back_without_recursive_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            stage.mkdir()
            (stage / "payload").write_bytes(b"staged")

            def mutate_then_fail(_descriptor):
                (target / "payload").write_bytes(b"mutated")
                (target / "added").write_bytes(b"preserved")
                raise OSError("injected parent fsync failure")

            with mock.patch.object(artifacts.os, "unlink",
                                   side_effect=AssertionError("must not unlink")):
                with mock.patch.object(artifacts.os, "rmdir",
                                       side_effect=AssertionError("must not rmdir")):
                    with mock.patch.object(artifacts.os, "fsync",
                                           side_effect=mutate_then_fail):
                        with self.assertRaisesRegex(
                                OSError, "injected parent fsync failure"):
                            artifacts.publish_no_replace(stage, target)
            self.assertFalse(target.exists())
            self.assertEqual((stage / "payload").read_bytes(), b"mutated")
            self.assertEqual((stage / "added").read_bytes(), b"preserved")

    def test_parent_fsync_failure_preserves_replaced_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            replacement = root / "replacement"
            stage.write_bytes(b"staged")
            replacement.write_bytes(b"unrelated")

            published_original = root / "published-original"
            original_rename = artifacts._rename_no_replace
            rename_calls = 0

            def fail_fsync(_descriptor):
                raise OSError("injected parent fsync failure")

            def replace_before_rollback(parent_fd, source, destination):
                nonlocal rename_calls
                rename_calls += 1
                if rename_calls == 2:
                    target.rename(published_original)
                    replacement.rename(target)
                original_rename(parent_fd, source, destination)

            with mock.patch.object(artifacts, "_rename_no_replace",
                                   side_effect=replace_before_rollback):
                with mock.patch.object(artifacts.os, "fsync", side_effect=fail_fsync):
                    with self.assertRaises(artifacts.ArtifactSerializationError):
                        artifacts.publish_no_replace(stage, target)
            self.assertEqual(target.read_bytes(), b"unrelated")
            self.assertEqual(published_original.read_bytes(), b"staged")
            self.assertFalse(any(path.name.startswith(".rollback-")
                                 for path in root.iterdir()))

    def test_parent_fsync_failure_preserves_replaced_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            stage.write_bytes(b"staged")

            def occupy_source_then_fail(_descriptor):
                stage.write_bytes(b"unrelated")
                raise OSError("injected parent fsync failure")

            with mock.patch.object(artifacts.os, "fsync",
                                   side_effect=occupy_source_then_fail):
                with self.assertRaises(artifacts.ArtifactSerializationError):
                    artifacts.publish_no_replace(stage, target)
            self.assertFalse(target.exists())
            self.assertEqual(stage.read_bytes(), b"unrelated")
            quarantined = [path for path in root.iterdir()
                           if path.name.startswith(".rollback-")]
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0].read_bytes(), b"staged")

    def test_failed_temporary_write_does_not_delete_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            original_temporary_file = artifacts._temporary_file
            temporary_path = None

            def capture_temporary(parent_fd, target_name):
                nonlocal temporary_path
                descriptor, name = original_temporary_file(parent_fd, target_name)
                temporary_path = root / name
                return descriptor, name

            def replace_temporary_then_fail(_descriptor):
                assert temporary_path is not None
                temporary_path.unlink()
                temporary_path.write_bytes(b"unrelated")
                raise OSError("injected temporary fsync failure")

            with mock.patch.object(artifacts, "_temporary_file",
                                   side_effect=capture_temporary):
                with mock.patch.object(artifacts.os, "fsync",
                                       side_effect=replace_temporary_then_fail):
                    with self.assertRaisesRegex(
                            OSError, "injected temporary fsync failure"):
                        artifacts.write_bytes_no_replace(target, b"staged")
            self.assertFalse(target.exists())
            self.assertIsNotNone(temporary_path)
            self.assertEqual(temporary_path.read_bytes(), b"unrelated")

    def test_source_to_symlink_race_fails_without_following_victim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            victim = root / "victim"
            stage.write_bytes(b"staged")
            victim.write_bytes(b"must remain")
            original_rename = artifacts._rename_no_replace
            replaced = False

            def replace_source_then_rename(parent_fd, source, destination):
                nonlocal replaced
                if not replaced:
                    replaced = True
                    os.unlink(source, dir_fd=parent_fd)
                    os.symlink(victim.name, source, dir_fd=parent_fd)
                original_rename(parent_fd, source, destination)

            with mock.patch.object(artifacts, "_rename_no_replace",
                                   side_effect=replace_source_then_rename):
                with self.assertRaises(artifacts.ArtifactSerializationError):
                    artifacts.publish_no_replace(stage, target)
            self.assertTrue(target.is_symlink())
            self.assertEqual(victim.read_bytes(), b"must remain")

    def test_write_temp_and_publish_stay_on_held_parent_after_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "parent"
            root.mkdir()
            moved = Path(directory) / "parent-moved"
            original_temporary_file = artifacts._temporary_file

            def replace_parent_then_create(parent_fd, target_name):
                root.rename(moved)
                root.mkdir()
                return original_temporary_file(parent_fd, target_name)

            with mock.patch.object(artifacts, "_temporary_file", side_effect=replace_parent_then_create):
                artifacts.write_bytes_no_replace(root / "artifact", b"held")
            self.assertEqual((moved / "artifact").read_bytes(), b"held")
            self.assertFalse((root / "artifact").exists())

    def test_post_publication_verification_stays_on_held_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "parent"
            root.mkdir()
            stage = root / "stage"
            stage.mkdir()
            (stage / "payload").write_bytes(b"held")
            target = root / "bundle"
            moved = Path(directory) / "parent-moved"
            original_rename = artifacts._rename_no_replace

            def rename_then_replace_parent(parent_fd, source, destination):
                original_rename(parent_fd, source, destination)
                root.rename(moved)
                root.mkdir()

            with mock.patch.object(artifacts, "_rename_no_replace", side_effect=rename_then_replace_parent):
                artifacts.publish_no_replace(stage, target)
            self.assertEqual((moved / "bundle" / "payload").read_bytes(), b"held")
            self.assertFalse((root / "bundle").exists())


if __name__ == "__main__":
    unittest.main()

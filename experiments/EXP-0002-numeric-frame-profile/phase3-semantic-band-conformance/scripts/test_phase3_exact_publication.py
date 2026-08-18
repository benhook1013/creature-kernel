"""Focused synthetic tests for the exact-attempt publication boundary."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import phase3_evidence_contract as contract
import test_phase3_evidence_contract as evidence_fixture


SCRIPT = Path(__file__).with_name("phase3_exact_publication.py")
SPEC = importlib.util.spec_from_file_location("phase3_exact_publication_test_subject", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def _blobs() -> tuple[bytes, bytes, bytes]:
    result = evidence_fixture._result()
    receipt = contract.build_receipt(result)
    index = contract.build_attempt_index(result, receipt)
    return result, receipt, index


class ExactPublicationTests(unittest.TestCase):
    def test_roundtrip_is_canonical_immutable_and_descriptor_checked(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            published = M.publish_attempt(root, result, receipt, index)
            self.assertEqual(published.attempt_id, "attempt-001")
            self.assertEqual(published.directory, root / "attempt-001")
            self.assertEqual(set(published.files), set(M.FILE_NAMES))
            with self.assertRaises(TypeError):
                published.files[M.RESULT_NAME] = published.result
            self.assertEqual(published.result.path, root / "attempt-001" / M.RESULT_NAME)
            self.assertEqual(stat.S_IMODE(os.stat(published.directory).st_mode), M.DIRECTORY_MODE)
            for name, raw in ((M.RESULT_NAME, result), (M.RECEIPT_NAME, receipt), (M.INDEX_NAME, index)):
                path = published.directory / name
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), M.FILE_MODES)
                self.assertEqual(path.stat().st_nlink, 1)
            read = M.read_attempt(root, "attempt-001")
            self.assertEqual(read.result.sha256, published.result.sha256)
            self.assertEqual(read.receipt.bytes, len(receipt))
            self.assertEqual(read.attempt_index.path, published.attempt_index.path)

    def test_contract_is_validated_before_filesystem_creation_and_cross_binding_fails(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            with self.assertRaises(M.PublicationError) as caught:
                M.publish_attempt(root, result, receipt[:-1] + b"x", index)
            self.assertEqual(caught.exception.code, "contract")
            self.assertEqual(list(root.iterdir()), [])
            other_adjudications = evidence_fixture._adjudications()
            other_attempt = evidence_fixture._attempt()
            other_attempt["ordinal"] = 1
            other_result = contract.build_result(
                other_attempt,
                other_adjudications,
                [
                    evidence_fixture._process("development", 8, other_adjudications),
                    evidence_fixture._process("held-out", 40, other_adjudications),
                    evidence_fixture._process("controls", 9, other_adjudications),
                ],
                evidence_fixture._tools(),
            )
            other_receipt = contract.build_receipt(other_result)
            with self.assertRaises(M.PublicationError):
                M.publish_attempt(root, result, other_receipt, index)
            self.assertEqual(list(root.iterdir()), [])

    def test_existing_attempt_is_exclusive_and_partial_output_is_retained(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            M.publish_attempt(root, result, receipt, index)
            with self.assertRaises(M.PublicationError) as caught:
                M.publish_attempt(root, result, receipt, index)
            self.assertEqual(caught.exception.code, "collision")
            partial_root = Path(directory) / "partial"
            partial_root.mkdir()
            original = M._write_file
            calls = 0

            def fail_after_result(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise M.PublicationError("synthetic", "second file failure")
                return original(*args, **kwargs)

            with mock.patch.object(M, "_write_file", side_effect=fail_after_result):
                with self.assertRaises(M.PublicationError):
                    M.publish_attempt(partial_root, result, receipt, index)
            partial = partial_root / "attempt-001"
            self.assertTrue(partial.is_dir())
            self.assertTrue((partial / M.RESULT_NAME).is_file())
            self.assertFalse((partial / M.RECEIPT_NAME).exists())
            self.assertFalse((partial / M.INDEX_NAME).exists())

    def test_publication_reopens_and_rejects_persisted_readback_mismatch(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            original = M._read_descriptor

            def corrupt_readback(fd, limit, label):
                raw = original(fd, limit, label)
                if label == "result.json persisted readback":
                    return raw[:-1] + (b"x" if raw[-1:] != b"x" else b"y")
                return raw

            with mock.patch.object(M, "_read_descriptor", side_effect=corrupt_readback):
                with self.assertRaises(M.PublicationError) as caught:
                    M.publish_attempt(root, result, receipt, index)
            self.assertEqual(caught.exception.code, "persisted-bytes")
            self.assertTrue((root / "attempt-001" / M.RESULT_NAME).is_file())
            self.assertFalse((root / "attempt-001" / M.RECEIPT_NAME).exists())

    def test_reader_rejects_bytes_that_differ_between_descriptor_reads(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            M.publish_attempt(root, result, receipt, index)
            original = M._read_descriptor

            def corrupt_second_read(fd, limit, label):
                raw = original(fd, limit, label)
                if label == "result.json second read":
                    return raw[:-1] + (b"x" if raw[-1:] != b"x" else b"y")
                return raw

            with mock.patch.object(M, "_read_descriptor", side_effect=corrupt_second_read):
                with self.assertRaises(M.PublicationError) as caught:
                    M.read_attempt(root, "attempt-001")
            self.assertEqual(caught.exception.code, "content-race")

    def test_reader_detects_earlier_member_mutation_while_later_member_is_read(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            published = M.publish_attempt(root, result, receipt, index)
            result_path = published.result.path
            original = M._read_descriptor
            mutated = False

            def mutate_result_during_receipt(fd, limit, label):
                nonlocal mutated
                if label == "receipt.json first read" and not mutated:
                    mutated = True
                    raw = result_path.read_bytes()
                    changed = (b"x" if raw[:1] != b"x" else b"y") + raw[1:]
                    os.chmod(result_path, 0o644)
                    result_path.write_bytes(changed)
                    os.chmod(result_path, M.FILE_MODES)
                return original(fd, limit, label)

            with mock.patch.object(M, "_read_descriptor", side_effect=mutate_result_during_receipt):
                with self.assertRaises(M.PublicationError) as caught:
                    M.read_attempt(root, "attempt-001")
            self.assertTrue(mutated)
            self.assertEqual(caught.exception.code, "race")

    def test_reader_reenumerates_the_closed_layout_after_file_reads(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            published = M.publish_attempt(root, result, receipt, index)
            original = M._bounded_layout
            calls = 0

            def mutate_after_first_enumeration(fd):
                nonlocal calls
                calls += 1
                names = original(fd)
                if calls == 1:
                    os.chmod(published.directory, 0o755)
                    (published.directory / "late-extra").write_bytes(b"diagnostic")
                    os.chmod(published.directory, M.DIRECTORY_MODE)
                return names

            with mock.patch.object(M, "_bounded_layout", side_effect=mutate_after_first_enumeration):
                with self.assertRaises(M.PublicationError) as caught:
                    M.read_attempt(root, "attempt-001")
            self.assertEqual(caught.exception.code, "file-layout")

    def test_directory_enumeration_stops_at_the_fourth_entry(self) -> None:
        yielded = 0

        class Entry:
            def __init__(self, name):
                self.name = name

        class Scan:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def __iter__(self):
                nonlocal yielded
                for index in range(100):
                    yielded += 1
                    yield Entry(f"entry-{index}")

        with mock.patch.object(M.os, "scandir", return_value=Scan()):
            with self.assertRaises(M.PublicationError) as caught:
                M._bounded_layout(123)
        self.assertEqual(caught.exception.code, "file-layout")
        self.assertEqual(yielded, 4)

    def test_directory_validator_closes_fd_when_post_open_fstat_fails(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            M.publish_attempt(root, result, receipt, index)
            parent_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                before = len(os.listdir("/proc/self/fd"))
                with mock.patch.object(M.os, "fstat", side_effect=OSError("synthetic fstat failure")):
                    with self.assertRaises(M.PublicationError):
                        M._validate_dir_name(parent_fd, "attempt-001", "attempt directory", M.DIRECTORY_MODE)
                after = len(os.listdir("/proc/self/fd"))
                self.assertEqual(after, before)
            finally:
                os.close(parent_fd)

    def _make_mutable(self, root: Path, name: str, action) -> None:
        result, receipt, index = _blobs()
        published = M.publish_attempt(root, result, receipt, index)
        os.chmod(published.directory, 0o755)
        action(published.directory / name)
        os.chmod(published.directory, M.DIRECTORY_MODE)
        with self.assertRaises(M.PublicationError):
            M.read_attempt(root, published.attempt_id)

    def test_reader_rejects_symlink_hardlink_extra_and_wrong_mode(self) -> None:
        for mutation in ("symlink", "hardlink", "extra", "mode"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "published"
                root.mkdir()
                if mutation == "symlink":
                    self._make_mutable(root, M.RESULT_NAME, lambda path: (path.unlink(), path.symlink_to("receipt.json")))
                elif mutation == "hardlink":
                    self._make_mutable(root, M.RESULT_NAME, lambda path: os.link(path, Path(directory) / "outside-hardlink"))
                elif mutation == "extra":
                    self._make_mutable(root, M.RESULT_NAME, lambda path: (path.parent / "unexpected").write_bytes(b"x"))
                else:
                    self._make_mutable(root, M.RESULT_NAME, lambda path: os.chmod(path, 0o644))

    def test_reader_rejects_directory_symlink_and_attempt_id_path_traversal(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            M.publish_attempt(root, result, receipt, index)
            outside = Path(directory) / "outside"
            outside.mkdir()
            (root / "attempt-002").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(M.PublicationError):
                M.read_attempt(root, "attempt-002")
            with self.assertRaises(M.PublicationError):
                M.read_attempt(root, "../attempt-001")

    def test_reader_rejects_missing_or_corrupt_closed_layout(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            published = M.publish_attempt(root, result, receipt, index)
            os.chmod(published.directory, 0o755)
            (published.directory / M.INDEX_NAME).unlink()
            os.chmod(published.directory, M.DIRECTORY_MODE)
            with self.assertRaises(M.PublicationError):
                M.read_attempt(root, "attempt-001")


if __name__ == "__main__":
    unittest.main()

"""Focused synthetic tests for the exact-attempt publication boundary."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import tempfile
import threading
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


_BLOB_CACHE: tuple[bytes, bytes, bytes] | None = None


def _blobs() -> tuple[bytes, bytes, bytes]:
    global _BLOB_CACHE
    if _BLOB_CACHE is None:
        result = evidence_fixture._result()
        receipt = contract.build_receipt(result)
        index = contract.build_attempt_index(result, receipt)
        _BLOB_CACHE = result, receipt, index
    return _BLOB_CACHE


class ExactPublicationTests(unittest.TestCase):
    def test_prelaunch_reservation_is_durable_exclusive_and_close_is_idempotent(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            reservation = M._reserve_attempt_for_test(root, "attempt-001")
            marker = root / "attempt-001"
            self.assertTrue(marker.is_dir())
            self.assertEqual(stat.S_IMODE(marker.stat().st_mode), 0o700)
            self.assertEqual(list(marker.iterdir()), [])
            with self.assertRaises(M.PublicationError) as caught:
                M._reserve_attempt_for_test(root, "attempt-001")
            self.assertEqual(caught.exception.code, "collision")
            reservation.close()
            reservation.close()
            self.assertTrue(reservation.closed)
            self.assertTrue(marker.is_dir())
            with self.assertRaises(M.PublicationError) as caught:
                M.publish_reserved_attempt(reservation, result, receipt, index)
            self.assertEqual(caught.exception.code, "reservation-closed")

    def test_experiment_slot_reservation_is_global_across_output_roots(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root_one = base / "published-one"; root_one.mkdir()
            root_two = base / "published-two"; root_two.mkdir()
            slot_namespace = base / "canonical-slots"
            with mock.patch.object(M, "EXPERIMENT_SLOT_NAMESPACE", slot_namespace):
                reservation = M.reserve_experiment_slot(root_one, "a" * 64, "wsl2-x86_64", 0, "attempt-001")
                with self.assertRaises(M.PublicationError) as caught:
                    M.reserve_experiment_slot(root_two, "a" * 64, "wsl2-x86_64", 0, "attempt-002")
                self.assertEqual(caught.exception.code, "slot-consumed")
                reservation.close()

    def test_experiment_slot_binding_is_checked_before_publication(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"; root.mkdir()
            with mock.patch.object(M, "EXPERIMENT_SLOT_NAMESPACE", Path(directory) / "canonical-slots"):
                reservation = M.reserve_experiment_slot(root, "a" * 64, "wsl2-x86_64", 0, "attempt-001")
                forged = json.loads(result.decode())
                forged["attempt"]["freeze_manifest_sha256"] = "b" * 64
                forged_result = contract._canonical(forged, "result", contract.MAX_RESULT_BYTES)
                forged_receipt = contract.build_receipt(forged_result)
                forged_index = contract.build_attempt_index(forged_result, forged_receipt)
                with self.assertRaises(M.PublicationError) as caught:
                    M.publish_reserved_attempt(reservation, forged_result, forged_receipt, forged_index)
                self.assertEqual(caught.exception.code, "slot-binding")
                self.assertTrue(reservation.closed)

    def test_consumed_slot_can_retain_one_terminal_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "published"; root.mkdir()
            with mock.patch.object(M, "EXPERIMENT_SLOT_NAMESPACE", base / "canonical-slots"):
                reservation = M.reserve_experiment_slot(root, "a" * 64, "wsl2-x86_64", 0, "attempt-terminal-001")
                terminal = M.write_terminal_failure(reservation, code="synthetic-failure", detail="bounded post-reservation failure")
            self.assertTrue(reservation.closed)
            self.assertEqual(terminal.name, M.TERMINAL_FAILURE_NAME)
            value = json.loads(terminal.read_bytes())
            self.assertEqual(value["schema"], M.TERMINAL_FAILURE_SCHEMA)
            self.assertEqual(value["ledger_id"], M.EXPERIMENT_SLOT_LEDGER_ID)
            with self.assertRaises(M.PublicationError):
                M.write_terminal_failure(reservation, code="second", detail="must not replace")

    def test_reservation_normalizes_umask_to_private_marker_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            previous = os.umask(0o777)
            try:
                reservation = M._reserve_attempt_for_test(root, "attempt-001")
            finally:
                os.umask(previous)
            try:
                self.assertEqual(stat.S_IMODE((root / "attempt-001").stat().st_mode), 0o700)
            finally:
                reservation.close()

    def test_reserved_publication_consumes_capability_and_double_publish_fails(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            reservation = M._reserve_attempt_for_test(root, "attempt-001")
            published = M.publish_reserved_attempt(reservation, result, receipt, index)
            self.assertTrue(reservation.closed)
            self.assertEqual(published.attempt_id, "attempt-001")
            with self.assertRaises(M.PublicationError) as caught:
                M.publish_reserved_attempt(reservation, result, receipt, index)
            self.assertEqual(caught.exception.code, "reservation-closed")

    def test_wrong_attempt_consumes_reservation_and_leaves_empty_marker(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            reservation = M._reserve_attempt_for_test(root, "attempt-002")
            with self.assertRaises(M.PublicationError) as caught:
                M.publish_reserved_attempt(reservation, result, receipt, index)
            self.assertEqual(caught.exception.code, "attempt-mismatch")
            self.assertTrue(reservation.closed)
            self.assertEqual(list((root / "attempt-002").iterdir()), [])
            with self.assertRaises(M.PublicationError):
                M._reserve_attempt_for_test(root, "attempt-002")

    def test_reservation_rejects_preexisting_partial_and_added_member(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            partial = root / "attempt-001"
            partial.mkdir(mode=0o700)
            (partial / "partial").write_bytes(b"diagnostic")
            with self.assertRaises(M.PublicationError) as caught:
                M._reserve_attempt_for_test(root, "attempt-001")
            self.assertEqual(caught.exception.code, "collision")

            fresh_root = Path(directory) / "fresh"
            fresh_root.mkdir()
            reservation = M._reserve_attempt_for_test(fresh_root, "attempt-001")
            (fresh_root / "attempt-001" / "unexpected").write_bytes(b"diagnostic")
            with self.assertRaises(M.PublicationError):
                M.publish_reserved_attempt(reservation, result, receipt, index)
            self.assertTrue((fresh_root / "attempt-001" / "unexpected").is_file())

    def test_reservation_rejects_renamed_replaced_and_unissued_objects(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "published"
            other_root = base / "other"
            root.mkdir()
            other_root.mkdir()

            renamed = M._reserve_attempt_for_test(root, "attempt-001")
            (root / "attempt-001").rename(root / "moved-attempt-001")
            (root / "attempt-001").mkdir(mode=0o700)
            with self.assertRaises(M.PublicationError):
                M.publish_reserved_attempt(renamed, result, receipt, index)

            cross_parent = base / "cross"
            cross_parent.mkdir()
            cross_root = M._reserve_attempt_for_test(cross_parent, "attempt-001")
            with self.assertRaises(AttributeError):
                cross_root._issued.parent_root = other_root
            cross_root.close()

            fabricated = object.__new__(M.AttemptReservation)
            with self.assertRaises(M.PublicationError) as caught:
                M.publish_reserved_attempt(fabricated, result, receipt, index)
            self.assertEqual(caught.exception.code, "reservation")

    def test_trust_boundary_is_cooperative_not_unforgeable(self) -> None:
        self.assertEqual(M.PUBLICATION_TRUST_BOUNDARY, "operator-enforced-single-dispatch-persistent-ledger-v1")
        self.assertIn("not an unforgeable capability", M.AttemptReservation.__doc__)

    def test_legacy_arbitrary_root_helpers_are_private_only(self) -> None:
        for name in ("reserve_attempt", "publish_attempt", "publish"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(M, name))

    def test_same_reservation_concurrent_publish_has_one_typed_loser(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            reservation = M._reserve_attempt_for_test(root, "attempt-001")
            entered = threading.Event()
            release = threading.Event()
            original = M._write_file
            first = True
            outcomes: list[str] = []
            outcomes_lock = threading.Lock()

            def block_first_write(*args, **kwargs):
                nonlocal first
                if first:
                    first = False
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError("synthetic publication gate timed out")
                return original(*args, **kwargs)

            def publish_worker() -> None:
                try:
                    M.publish_reserved_attempt(reservation, result, receipt, index)
                    outcome = "success"
                except M.PublicationError as error:
                    outcome = error.code
                with outcomes_lock:
                    outcomes.append(outcome)

            with mock.patch.object(M, "_write_file", side_effect=block_first_write):
                first_thread = threading.Thread(target=publish_worker)
                second_thread = threading.Thread(target=publish_worker)
                close_thread = threading.Thread(target=reservation.close)
                first_thread.start()
                self.assertTrue(entered.wait(5))
                second_thread.start()
                close_thread.start()
                release.set()
                first_thread.join(10)
                second_thread.join(10)
                close_thread.join(10)
            self.assertFalse(first_thread.is_alive())
            self.assertFalse(second_thread.is_alive())
            self.assertFalse(close_thread.is_alive())
            self.assertCountEqual(outcomes, ["success", "reservation-closed"])
            self.assertTrue(reservation.closed)
            self.assertTrue((root / "attempt-001" / M.INDEX_NAME).is_file())

    def test_publish_revalidates_named_root_and_attempt_before_return(self) -> None:
        result, receipt, index = _blobs()
        for replacement in ("attempt", "root"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                root = base / "published"
                root.mkdir()
                reservation = M._reserve_attempt_for_test(root, "attempt-001")
                original = M._verify_closure

                def replace_after_closure(*args, **kwargs):
                    verified = original(*args, **kwargs)
                    if replacement == "attempt":
                        (root / "attempt-001").rename(root / "moved-attempt-001")
                        (root / "attempt-001").mkdir()
                        os.chmod(root / "attempt-001", M.DIRECTORY_MODE)
                    else:
                        root.rename(base / "moved-root")
                        root.mkdir()
                    return verified

                with mock.patch.object(M, "_verify_closure", side_effect=replace_after_closure):
                    with self.assertRaises(M.PublicationError) as caught:
                        M.publish_reserved_attempt(reservation, result, receipt, index)
                self.assertIn(caught.exception.code, {"reservation-root", "reservation-directory"})
                self.assertTrue(reservation.closed)

    def test_reservation_detects_mkdir_to_open_name_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            original = M._open_dir_name
            replaced = False

            def replace_before_open(parent_fd, name, label):
                nonlocal replaced
                if name == "attempt-001" and not replaced:
                    replaced = True
                    (root / name).rename(root / "moved-attempt-001")
                    (root / name).mkdir(mode=0o700)
                return original(parent_fd, name, label)

            with mock.patch.object(M, "_open_dir_name", side_effect=replace_before_open):
                with self.assertRaises(M.PublicationError) as caught:
                    M._reserve_attempt_for_test(root, "attempt-001")
            self.assertTrue(replaced)
            self.assertEqual(caught.exception.code, "race")

    def test_roundtrip_is_canonical_immutable_and_descriptor_checked(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            published = M._publish_attempt_for_test(root, result, receipt, index)
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
                M._publish_attempt_for_test(root, result, receipt[:-1] + b"x", index)
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
                M._publish_attempt_for_test(root, result, other_receipt, index)
            self.assertEqual(list(root.iterdir()), [])

    def test_existing_attempt_is_exclusive_and_partial_output_is_retained(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            M._publish_attempt_for_test(root, result, receipt, index)
            with self.assertRaises(M.PublicationError) as caught:
                M._publish_attempt_for_test(root, result, receipt, index)
            self.assertEqual(caught.exception.code, "collision")
            partial_root = Path(directory) / "partial"
            partial_root.mkdir()
            # Use the public experiment reservation here so the failure path
            # exercises the same ledger-bound terminal evidence that closure
            # consumes.  The local helper intentionally has no slot binding.
            slot_namespace = Path(directory) / "canonical-slots"
            original = M._write_file
            calls = 0

            def fail_after_result(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise M.PublicationError("synthetic", "second file failure")
                return original(*args, **kwargs)

            with mock.patch.object(M, "EXPERIMENT_SLOT_NAMESPACE", slot_namespace), mock.patch.object(M, "_write_file", side_effect=fail_after_result):
                reservation = M.reserve_experiment_slot(partial_root, "a" * 64, "wsl2-x86_64", 0, "attempt-001")
                with self.assertRaises(M.PublicationError):
                    M.publish_reserved_attempt(reservation, result, receipt, index)
            partial = partial_root / "attempt-001"
            self.assertTrue(partial.is_dir())
            self.assertTrue((partial / M.RESULT_NAME).is_file())
            self.assertFalse((partial / M.RECEIPT_NAME).exists())
            self.assertFalse((partial / M.INDEX_NAME).exists())
            self.assertTrue((partial / M.TERMINAL_FAILURE_NAME).is_file())

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
                    M._publish_attempt_for_test(root, result, receipt, index)
            self.assertEqual(caught.exception.code, "persisted-bytes")
            self.assertTrue((root / "attempt-001" / M.RESULT_NAME).is_file())
            self.assertFalse((root / "attempt-001" / M.RECEIPT_NAME).exists())

    def test_reader_rejects_bytes_that_differ_between_descriptor_reads(self) -> None:
        result, receipt, index = _blobs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            M._publish_attempt_for_test(root, result, receipt, index)
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
            published = M._publish_attempt_for_test(root, result, receipt, index)
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
            published = M._publish_attempt_for_test(root, result, receipt, index)
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
            M._publish_attempt_for_test(root, result, receipt, index)
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
        published = M._publish_attempt_for_test(root, result, receipt, index)
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
            M._publish_attempt_for_test(root, result, receipt, index)
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
            published = M._publish_attempt_for_test(root, result, receipt, index)
            os.chmod(published.directory, 0o755)
            (published.directory / M.INDEX_NAME).unlink()
            os.chmod(published.directory, M.DIRECTORY_MODE)
            with self.assertRaises(M.PublicationError):
                M.read_attempt(root, "attempt-001")


if __name__ == "__main__":
    unittest.main()

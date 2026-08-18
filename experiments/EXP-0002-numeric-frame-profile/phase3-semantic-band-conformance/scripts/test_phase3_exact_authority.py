#!/usr/bin/env python3
"""Synthetic tests for execution-incapable Phase 3 authority records."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("phase3_exact_authority.py")
SPEC = importlib.util.spec_from_file_location("phase3_exact_authority_test_subject", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

PACKAGE = SCRIPT.parents[1]
FREEZE_PATH = PACKAGE / "manifests/freeze-manifest.json"
FREEZE_BYTES = FREEZE_PATH.read_bytes()
FREEZE = json.loads(FREEZE_BYTES)
FREEZE_SHA = FREEZE["manifest_sha256"]
SOURCE_COMMIT = FREEZE["candidate_source_commit"]


def _review(index: int, lens: str, reviewer: str, path: str) -> dict[str, object]:
    return {
        "review_id": f"gate-b-final-{index}",
        "reviewer": reviewer,
        "lens": lens,
        "path": path,
        "bytes": 0,
        "sha256": "0" * 64,
        "status": "passed",
        "disposition": "Clean",
        "findings": [],
    }


def _admission(review_root: Path) -> bytes:
    values = [
        _review(1, M.REQUIRED_REVIEW_LENSES[0], "reviewer-alpha", "gate-b-final-01.md"),
        _review(2, M.REQUIRED_REVIEW_LENSES[1], "reviewer-beta", "gate-b-final-02.md"),
    ]
    for item in values:
        data = (review_root / str(item["path"])).read_bytes()
        item["bytes"] = len(data)
        item["sha256"] = hashlib.sha256(data).hexdigest()
    return M.encode_gate_b_admission({
        "schema": M.ADMISSION_SCHEMA,
        "experiment_id": M.EXPERIMENT_ID,
        "phase_id": M.PHASE_ID,
        "candidate_profile_id": M.CANDIDATE_PROFILE_ID,
        "freeze_manifest_sha256": FREEZE_SHA,
        "execution_tool_source_commit": SOURCE_COMMIT,
        "reviewed_commit": SOURCE_COMMIT,
        "reviews": values,
        "status": "passed",
        "execution_permitted": False,
        "admission_record_sha256": None,
    })


class ExactAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)
        self.reviews = self.root / "reviews"
        self.reviews.mkdir()
        (self.reviews / "gate-b-final-01.md").write_bytes(b"# clean closure review\nResult: Clean\n")
        (self.reviews / "gate-b-final-02.md").write_bytes(b"# clean execution review\nResult: Clean\n")
        self.admission = _admission(self.reviews)

    def tearDown(self) -> None:
        self.holder.cleanup()

    def test_admission_roundtrip_authenticates_freeze_and_anchored_reviews(self) -> None:
        value = M.validate_gate_b_admission(self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews)
        self.assertEqual(value["freeze_manifest_sha256"], FREEZE_SHA)
        self.assertEqual(value["execution_tool_source_commit"], SOURCE_COMMIT)
        self.assertFalse(value["execution_permitted"])

    def test_admission_rejects_valid_pre_freeze_manifest(self) -> None:
        freeze_module = M._freeze_module()
        value = json.loads(FREEZE_BYTES)
        value["binaries"] = freeze_module._binary_slots({})
        value["readiness"] = freeze_module._readiness(value["binaries"])
        value["manifest_sha256"] = freeze_module._self_hash(value)
        pre_freeze = freeze_module._canonical(value)
        admission = json.loads(self.admission)
        admission["freeze_manifest_sha256"] = value["manifest_sha256"]
        admission = M.encode_gate_b_admission(admission)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(admission, freeze_manifest=pre_freeze, review_root=self.reviews)
        self.assertEqual(context.exception.code, "freeze-readiness")

    def test_admission_tamper_is_rejected_even_when_json_remains_parseable(self) -> None:
        value = json.loads(self.admission)
        value["status"] = "failed"
        tampered = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(tampered, freeze_manifest=FREEZE_BYTES, review_root=self.reviews)
        self.assertIn(context.exception.code, {"admission-status", "record-hash"})

    def test_admission_requires_distinct_review_identity_path_lens_and_reviewer(self) -> None:
        original = json.loads(self.admission)
        for field in ("review_id", "path", "lens", "reviewer"):
            value = json.loads(self.admission)
            value["reviews"][1][field] = value["reviews"][0][field]
            # Re-seal only the record so shape validation reaches the intended
            # duplicate field rather than stopping at the outer self-hash.
            with self.assertRaises(M.AuthorityError) as context:
                M.encode_gate_b_admission(value)
            self.assertIn(context.exception.code, {"review-identity", "review-lenses"})
        self.assertEqual(original["status"], "passed")

    def test_admission_rejects_nonclean_review_and_wrong_commit_or_manifest(self) -> None:
        value = json.loads(self.admission)
        value["reviews"][0]["findings"] = [{"finding": "problem"}]
        with self.assertRaises(M.AuthorityError) as context:
            M.encode_gate_b_admission(value)
        self.assertEqual(context.exception.code, "review-findings")

        value = json.loads(self.admission)
        value["execution_tool_source_commit"] = "a" * 40
        value["reviewed_commit"] = "a" * 40
        forged = M.encode_gate_b_admission(value)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(forged, freeze_manifest=FREEZE_BYTES, review_root=self.reviews)
        self.assertEqual(context.exception.code, "source-binding")

        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self.admission, freeze_manifest=FREEZE_BYTES[:-1] + b"x\n", review_root=self.reviews)
        self.assertEqual(context.exception.code, "freeze")

    def test_review_symlink_and_review_hash_drift_fail_closed(self) -> None:
        moved = self.reviews / "gate-b-final-02.md"
        moved.unlink()
        moved.symlink_to(self.root / "outside.md")
        (self.root / "outside.md").write_bytes(b"# clean execution review\nResult: Clean\n")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-file")

    def test_review_path_replacement_after_open_is_rejected(self) -> None:
        replacement = self.root / "replacement.md"
        replacement.write_bytes(b"different inode with same byte count!!\n")
        replacement_stat = replacement.stat()
        root_fd = M._open_root(self.reviews)
        try:
            with mock.patch.object(M.os, "stat", return_value=replacement_stat):
                with self.assertRaises(M.AuthorityError) as context:
                    M._read_review(root_fd, "gate-b-final-01.md")
            self.assertEqual(context.exception.code, "review-race")
        finally:
            M.os.close(root_fd)

    def test_exact_runtime_tool_hook_is_explicit_and_closed(self) -> None:
        current = M.validate_required_exact_runtime_tools(FREEZE)
        self.assertEqual(current["present"], ())
        self.assertEqual(current["missing"], M.REQUIRED_EXACT_RUNTIME_TOOLS)
        identities = [
            {"path": path, "mode": 0o644, "bytes": index + 1, "sha256": f"{index + 1:064x}"}
            for index, path in enumerate(M.REQUIRED_EXACT_RUNTIME_TOOLS)
        ]
        complete = M.validate_required_exact_runtime_tools({"runtime_tool_identities": identities}, require_complete=True)
        self.assertEqual(complete["present"], M.REQUIRED_EXACT_RUNTIME_TOOLS)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"runtime_tool_identities": identities + [dict(identities[0])]})
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"runtime_tool_identities": identities[:-1]})
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"runtime_tool_identities": identities[:-1]}, require_complete=True)
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"runtime_tool_identities": []}, require_complete=True)
        self.assertEqual(context.exception.code, "runtime-tool-closure")

    def _authorization(self, *, selector: str = "wsl2-x86_64", ordinal: int = 0, custody: str = "c" * 64, attempt: str = "attempt-001") -> bytes:
        return M.encode_authorization({
            "schema": M.AUTHORIZATION_SCHEMA,
            "experiment_id": M.EXPERIMENT_ID,
            "phase_id": M.PHASE_ID,
            "candidate_profile_id": M.CANDIDATE_PROFILE_ID,
            "admission_record_sha256": hashlib.sha256(self.admission).hexdigest(),
            "freeze_manifest_sha256": FREEZE_SHA,
            "custody_record_sha256": custody,
            "attempt_id": attempt,
            "platform_selector": selector,
            "ordinal": ordinal,
            "authorization_reference": "ben-approval-2026-08-19-001",
            "scope": "exact-attempt",
            "execution_permitted": True,
            "automatic_retry": False,
            "authorization_record_sha256": None,
        })

    def test_authorization_roundtrip_cross_binds_exact_admission_and_values(self) -> None:
        raw = self._authorization()
        value = M.validate_authorization(
            raw,
            admission_bytes=self.admission,
            freeze_manifest=FREEZE_BYTES,
            review_root=self.reviews,
            expected_custody_record_sha256="c" * 64,
            expected_attempt_id="attempt-001",
            expected_platform_selector="wsl2-x86_64",
            expected_ordinal=0,
            expected_authorization_reference="ben-approval-2026-08-19-001",
        )
        self.assertTrue(value["execution_permitted"])
        self.assertFalse(value["automatic_retry"])

    def test_authorization_platform_ordinal_matrix_and_mismatch(self) -> None:
        for selector, ordinals in M.PLATFORM_ORDINALS.items():
            for ordinal in ordinals:
                raw = self._authorization(selector=selector, ordinal=ordinal)
                value = M.validate_authorization(raw, admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector=selector, expected_ordinal=ordinal, expected_authorization_reference="ben-approval-2026-08-19-001")
                self.assertEqual(value["ordinal"], ordinal)
        with self.assertRaises(M.AuthorityError) as context:
            self._authorization(selector="ubuntu-24.04-x86_64", ordinal=0)
        self.assertEqual(context.exception.code, "ordinal")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_authorization(self._authorization(), admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="d" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0, expected_authorization_reference="ben-approval-2026-08-19-001")
        self.assertEqual(context.exception.code, "custody-binding")

    def test_authorization_rejects_placeholder_reference_retry_scope_and_admission_tamper(self) -> None:
        value = json.loads(self._authorization())
        for field, replacement in (("authorization_reference", "TBD"), ("automatic_retry", True), ("scope", "batch")):
            forged_value = dict(value)
            forged_value[field] = replacement
            with self.assertRaises(M.AuthorityError) as context:
                M.encode_authorization(forged_value)
            self.assertIn(context.exception.code, {"authorization-reference", "authorization-policy", "record-hash"})
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_authorization(self._authorization(), admission_bytes=self.admission + b" ", freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0, expected_authorization_reference="ben-approval-2026-08-19-001")
        self.assertIn(context.exception.code, {"record-size", "noncanonical", "freeze", "admission-binding"})

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self) -> None:
        duplicate = b'{"admission_record_sha256":null,"admission_record_sha256":null}\n'
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_authorization(duplicate, admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0, expected_authorization_reference="ben-approval-2026-08-19-001")
        self.assertEqual(context.exception.code, "duplicate-json-key")

    def test_expected_authorization_reference_is_required_and_exact(self) -> None:
        with self.assertRaises(TypeError):
            M.validate_authorization(self._authorization(), admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_authorization(self._authorization(), admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0, expected_authorization_reference="ben-approval-other")
        self.assertEqual(context.exception.code, "authorization-reference")


if __name__ == "__main__":
    unittest.main()

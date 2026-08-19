#!/usr/bin/env python3
"""Synthetic tests for execution-incapable Phase 3 authority records."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("phase3_exact_authority.py")
SPEC = importlib.util.spec_from_file_location("phase3_exact_authority_test_subject", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

FREEZE_SCRIPT = SCRIPT.with_name("phase3_freeze_manifest.py")
FREEZE_SPEC = importlib.util.spec_from_file_location("phase3_exact_authority_freeze_fixture", FREEZE_SCRIPT)
assert FREEZE_SPEC and FREEZE_SPEC.loader
F = importlib.util.module_from_spec(FREEZE_SPEC)
FREEZE_SPEC.loader.exec_module(F)

CANDIDATE_COMMIT = "c" * 40
EXECUTION_TOOL_SOURCE_COMMIT = "e" * 40
MATERIALIZATION_COMMIT = "b" * 40
FREEZE_SHA = "d" * 64


def _review_bytes(index: int, lens: str, *, reviewer: str | None = None, reviewed_commit: str = MATERIALIZATION_COMMIT, freeze_hash: str = FREEZE_SHA) -> bytes:
    if reviewer is None:
        reviewer = "reviewer-alpha" if index == 1 else "reviewer-beta"
    header = {
        "schema": M.REVIEW_HEADER_SCHEMA,
        "review_id": f"gate-b-final-{index}",
        "reviewer": reviewer,
        "status": "Complete",
        "disposition": "Clean",
        "lens": lens,
        "reviewed_commit": reviewed_commit,
        "freeze_manifest_sha256": freeze_hash,
        "findings": [],
    }
    return M.REVIEW_HEADER_PREFIX.encode("ascii") + M._canonical(header)[:-1] + b"\n# review body\n"


def _exact_tools() -> list[dict[str, object]]:
    return [
        {"path": path, "mode": 0o644, "bytes": index + 1, "sha256": f"{index + 1:064x}"}
        for index, path in enumerate(M.REQUIRED_EXACT_RUNTIME_TOOLS)
    ]


def _closure_tools() -> list[dict[str, object]]:
    return [
        {"path": path, "mode": 0o644, "bytes": 1, "sha256": "a" * 64}
        for path in M.EXPERIMENT_CLOSURE_TOOLS
    ]


FREEZE = {
    "schema": M.FREEZE_SCHEMA,
    "manifest_sha256": FREEZE_SHA,
    "candidate_source_commit": CANDIDATE_COMMIT,
    "execution_tool_source_commit": EXECUTION_TOOL_SOURCE_COMMIT,
    "materialization_commit": MATERIALIZATION_COMMIT,
    "predecessor_inherited_sha256": F.EXPECTED_INHERITED_V1_SHA256,
    "exact_runtime_tool_identities": _exact_tools(),
    "experiment_closure_schema": M.EXPERIMENT_CLOSURE_SCHEMA,
    "experiment_closure_tool_identities": _closure_tools(),
    "binding": {
        "experiment_id": M.EXPERIMENT_ID,
        "phase_id": M.PHASE_ID,
        "candidate_profile_id": M.CANDIDATE_PROFILE_ID,
    },
    "binaries": {
        "wsl2-x86_64": {"status": "bound"},
        "ubuntu-24.04-x86_64": {"status": "bound"},
    },
    "readiness": {
        "materialization_state": "frozen",
        "freeze_blockers": [],
        "execution_permitted": False,
    },
    "execution_permitted": False,
}
FREEZE_BYTES = M._canonical(FREEZE)


class _FreezeFixture:
    """Minimal canonical-owner substitute for consumer-focused v3 tests."""

    @staticmethod
    def validate_manifest(raw: bytes) -> dict[str, object]:
        value = json.loads(raw)
        if M._canonical(value) != raw:
            raise ValueError("fixture freeze is not canonical")
        return value

    @staticmethod
    def check_manifest(*, manifest_raw: bytes | None = None) -> dict[str, object]:
        return copy.deepcopy(FREEZE)


class _UncheckedExecutionFreezeFixture(_FreezeFixture):
    """Pure-valid fixture whose E snapshot has no repository-bound proof."""

    @staticmethod
    def check_manifest(*, manifest_raw: bytes | None = None) -> dict[str, object]:
        raise ValueError("execution commit is not a descendant/current snapshot")


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
        "execution_tool_source_commit": EXECUTION_TOOL_SOURCE_COMMIT,
        "reviewed_commit": MATERIALIZATION_COMMIT,
        "reviews": values,
        "status": "passed",
        "execution_permitted": False,
        "admission_record_sha256": None,
    })


class ExactAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.freeze_patch = mock.patch.object(M, "_freeze_module", return_value=_FreezeFixture)
        self.freeze_patch.start()
        # These legacy synthetic consumer tests exercise record and review
        # shape.  Git-bound review-target proof is covered by the dedicated
        # temporary-repository tests below.
        self.review_target_patch = mock.patch.object(M, "_validate_reviewed_target")
        self.review_target_patch.start()
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)
        self.reviews = self.root / "reviews"
        self.reviews.mkdir()
        (self.reviews / "gate-b-final-01.md").write_bytes(_review_bytes(1, M.REQUIRED_REVIEW_LENSES[0]))
        (self.reviews / "gate-b-final-02.md").write_bytes(_review_bytes(2, M.REQUIRED_REVIEW_LENSES[1]))
        self.admission = _admission(self.reviews)

    def tearDown(self) -> None:
        self.holder.cleanup()
        self.review_target_patch.stop()
        self.freeze_patch.stop()

    def test_admission_roundtrip_authenticates_freeze_and_anchored_reviews(self) -> None:
        with mock.patch.object(_FreezeFixture, "check_manifest", wraps=_FreezeFixture.check_manifest) as current_check:
            value = M.validate_gate_b_admission(self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews)
        current_check.assert_called_once_with(manifest_raw=FREEZE_BYTES)
        self.assertEqual(value["freeze_manifest_sha256"], FREEZE_SHA)
        self.assertEqual(value["execution_tool_source_commit"], EXECUTION_TOOL_SOURCE_COMMIT)
        self.assertEqual(value["reviewed_commit"], MATERIALIZATION_COMMIT)
        self.assertNotEqual(value["execution_tool_source_commit"], CANDIDATE_COMMIT)
        self.assertFalse(value["execution_permitted"])


    def test_admission_rejects_valid_pre_freeze_manifest(self) -> None:
        value = copy.deepcopy(FREEZE)
        value["readiness"]["materialization_state"] = "planned"
        value["manifest_sha256"] = "f" * 64
        pre_freeze = M._canonical(value)
        admission = json.loads(self.admission)
        admission["freeze_manifest_sha256"] = value["manifest_sha256"]
        admission = M.encode_gate_b_admission(admission)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(admission, freeze_manifest=pre_freeze, review_root=self.reviews)
        self.assertEqual(context.exception.code, "freeze-current")

    def test_pure_valid_unchecked_execution_snapshot_is_not_authority(self) -> None:
        with mock.patch.object(M, "_freeze_module", return_value=_UncheckedExecutionFreezeFixture):
            with self.assertRaises(M.AuthorityError) as context:
                M.validate_gate_b_admission(
                    self.admission,
                    freeze_manifest=FREEZE_BYTES,
                    review_root=self.reviews,
                )
        self.assertEqual(context.exception.code, "freeze-current")

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
        value["execution_tool_source_commit"] = CANDIDATE_COMMIT
        value["reviewed_commit"] = CANDIDATE_COMMIT
        forged = M.encode_gate_b_admission(value)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(forged, freeze_manifest=FREEZE_BYTES, review_root=self.reviews)
        self.assertEqual(context.exception.code, "source-binding")

        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self.admission, freeze_manifest=FREEZE_BYTES[:-1] + b"x\n", review_root=self.reviews)
        self.assertEqual(context.exception.code, "freeze")

    def test_admission_rejects_predecessor_freeze_even_if_owner_accepts_it(self) -> None:
        for schema in ("ck.exp-0002.phase3.freeze-manifest-1", M.LEGACY_FREEZE_SCHEMA):
            predecessor = copy.deepcopy(FREEZE)
            predecessor["schema"] = schema
            predecessor["manifest_sha256"] = "f" * 64
            admission = json.loads(self.admission)
            admission["freeze_manifest_sha256"] = predecessor["manifest_sha256"]
            with self.assertRaises(M.AuthorityError) as context:
                M.validate_gate_b_admission(M.encode_gate_b_admission(admission), freeze_manifest=M._canonical(predecessor), review_root=self.reviews)
            self.assertEqual(context.exception.code, "freeze-version")

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
        self.assertEqual(current["present"], M.REQUIRED_EXACT_RUNTIME_TOOLS)
        self.assertEqual(current["missing"], ())
        identities = _exact_tools()
        complete = M.validate_required_exact_runtime_tools({"exact_runtime_tool_identities": identities})
        self.assertEqual(complete["present"], M.REQUIRED_EXACT_RUNTIME_TOOLS)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"exact_runtime_tool_identities": identities + [dict(identities[0])]})
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"exact_runtime_tool_identities": identities[:-1]})
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"exact_runtime_tool_identities": []})
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"runtime_tool_identities": identities})
        self.assertEqual(context.exception.code, "runtime-tool-closure")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_required_exact_runtime_tools({"exact_runtime_tool_identities": identities + [{"path": "scripts/unexpected.py", "mode": 0o644, "bytes": 1, "sha256": "f" * 64}]})
        self.assertEqual(context.exception.code, "runtime-tool-closure")

    def test_v3_closure_tool_hook_is_explicit_and_closed(self) -> None:
        self.assertEqual(M.validate_experiment_closure_tool(FREEZE), M.EXPERIMENT_CLOSURE_TOOLS)
        for mutate in (
            lambda value: value.pop("experiment_closure_schema"),
            lambda value: value.__setitem__("experiment_closure_tool_identities", []),
            lambda value: value["experiment_closure_tool_identities"][0].__setitem__("path", "scripts/other.py"),
        ):
            value = copy.deepcopy(FREEZE)
            mutate(value)
            with self.assertRaises(M.AuthorityError) as context:
                M.validate_experiment_closure_tool(value)
            self.assertEqual(context.exception.code, "closure-tool-closure")

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
        )
        self.assertTrue(value["execution_permitted"])
        self.assertFalse(value["automatic_retry"])

    def test_authorization_platform_ordinal_matrix_and_mismatch(self) -> None:
        for selector, ordinals in M.PLATFORM_ORDINALS.items():
            for ordinal in ordinals:
                raw = self._authorization(selector=selector, ordinal=ordinal)
                value = M.validate_authorization(raw, admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector=selector, expected_ordinal=ordinal)
                self.assertEqual(value["ordinal"], ordinal)
        with self.assertRaises(M.AuthorityError) as context:
            self._authorization(selector="ubuntu-24.04-x86_64", ordinal=0)
        self.assertEqual(context.exception.code, "ordinal")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_authorization(self._authorization(), admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="d" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0)
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
            M.validate_authorization(self._authorization(), admission_bytes=self.admission + b" ", freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0)
        self.assertIn(context.exception.code, {"record-size", "noncanonical", "freeze", "admission-binding"})

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self) -> None:
        duplicate = b'{"admission_record_sha256":null,"admission_record_sha256":null}\n'
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_authorization(duplicate, admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0)
        self.assertEqual(context.exception.code, "duplicate-json-key")

    def test_authorization_reference_is_record_owned_not_caller_expected(self) -> None:
        value = M.validate_authorization(self._authorization(), admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0)
        self.assertEqual(value["authorization_reference"], "ben-approval-2026-08-19-001")
        with self.assertRaises(TypeError):
            M.validate_authorization(self._authorization(), admission_bytes=self.admission, freeze_manifest=FREEZE_BYTES, review_root=self.reviews, expected_custody_record_sha256="c" * 64, expected_attempt_id="attempt-001", expected_platform_selector="wsl2-x86_64", expected_ordinal=0, expected_authorization_reference="caller-forged")


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=5,
    )
    return result.stdout.decode("utf-8").strip()


class GitBoundAuthorityTests(unittest.TestCase):
    """Repository-bound proof tests for the later v3 review target."""

    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)
        self.reviews = self.root / "reviews"
        self.reviews.mkdir()
        (self.reviews / "gate-b-final-01.md").write_bytes(_review_bytes(1, M.REQUIRED_REVIEW_LENSES[0]))
        (self.reviews / "gate-b-final-02.md").write_bytes(_review_bytes(2, M.REQUIRED_REVIEW_LENSES[1]))
        self.freeze_patch: mock._patch | None = None

    def tearDown(self) -> None:
        if self.freeze_patch is not None:
            self.freeze_patch.stop()
        self.holder.cleanup()

    def _history(self, *, manifest_bytes: bytes | None = None, missing_manifest: bool = False, repo_name: str = "repo") -> tuple[dict[str, object], bytes, str, str, str, str, str]:
        repo = self.root / repo_name
        repo.mkdir()
        _git(repo, "init", "--quiet")
        _git(repo, "config", "user.email", "authority-tests@example.invalid")
        _git(repo, "config", "user.name", "Authority Tests")
        (repo / "history.txt").write_bytes(b"execution snapshot\n")
        _git(repo, "add", "history.txt")
        _git(repo, "commit", "--quiet", "-m", "execution snapshot")
        execution = _git(repo, "rev-parse", "HEAD")
        (repo / "history.txt").write_bytes(b"materialization snapshot\n")
        _git(repo, "add", "history.txt")
        _git(repo, "commit", "--quiet", "-m", "materialization snapshot")
        materialization = _git(repo, "rev-parse", "HEAD")

        manifest_path = repo / "frozen" / "freeze-manifest.json"
        manifest_path.parent.mkdir()
        self.reviews = repo / "reviews"
        self.reviews.mkdir()
        (self.reviews / "gate-b-final-01.md").write_bytes(b"# clean closure review\nResult: Clean\n")
        (self.reviews / "gate-b-final-02.md").write_bytes(b"# clean execution review\nResult: Clean\n")
        freeze = copy.deepcopy(FREEZE)
        freeze["execution_tool_source_commit"] = execution
        freeze["materialization_commit"] = materialization
        freeze_raw = M._canonical(freeze)
        if not missing_manifest:
            manifest_path.write_bytes(freeze_raw if manifest_bytes is None else manifest_bytes)
        (repo / "review-target.txt").write_bytes(b"review target\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "--quiet", "-m", "review target")
        reviewed = _git(repo, "rev-parse", "HEAD")
        # Review artifacts are committed after the target commit; their
        # header binds the already-known reviewed target without a hash cycle.
        (self.reviews / "gate-b-final-01.md").write_bytes(_review_bytes(1, M.REQUIRED_REVIEW_LENSES[0], reviewed_commit=reviewed))
        (self.reviews / "gate-b-final-02.md").write_bytes(_review_bytes(2, M.REQUIRED_REVIEW_LENSES[1], reviewed_commit=reviewed))
        _git(repo, "add", "reviews")
        _git(repo, "commit", "--quiet", "-m", "review evidence")
        (repo / "head.txt").write_bytes(b"current head\n")
        _git(repo, "add", "head.txt")
        _git(repo, "commit", "--quiet", "-m", "current head")
        current_head = _git(repo, "rev-parse", "HEAD")
        manifest_rel = manifest_path.relative_to(repo).as_posix()

        class DynamicFreeze:
            REPO = repo
            MANIFEST = manifest_path

            @staticmethod
            def validate_manifest(raw: bytes) -> dict[str, object]:
                value = json.loads(raw)
                if M._canonical(value) != raw:
                    raise ValueError("fixture freeze is not canonical")
                return value

            @staticmethod
            def check_manifest(*, manifest_raw: bytes | None = None) -> dict[str, object]:
                return copy.deepcopy(freeze)

        self.freeze_patch = mock.patch.object(M, "_freeze_module", return_value=DynamicFreeze)
        self.freeze_patch.start()
        return freeze, freeze_raw, execution, materialization, reviewed, current_head, manifest_rel

    def _admission(self, *, source: str, reviewed: str, freeze_hash: str = FREEZE_SHA) -> bytes:
        values = [
            _review(1, M.REQUIRED_REVIEW_LENSES[0], "reviewer-alpha", "gate-b-final-01.md"),
            _review(2, M.REQUIRED_REVIEW_LENSES[1], "reviewer-beta", "gate-b-final-02.md"),
        ]
        for item in values:
            data = (self.reviews / str(item["path"])).read_bytes()
            item["bytes"] = len(data)
            item["sha256"] = hashlib.sha256(data).hexdigest()
        return M.encode_gate_b_admission({
            "schema": M.ADMISSION_SCHEMA,
            "experiment_id": M.EXPERIMENT_ID,
            "phase_id": M.PHASE_ID,
            "candidate_profile_id": M.CANDIDATE_PROFILE_ID,
            "freeze_manifest_sha256": freeze_hash,
            "execution_tool_source_commit": source,
            "reviewed_commit": reviewed,
            "reviews": values,
            "status": "passed",
            "execution_permitted": False,
            "admission_record_sha256": None,
        })

    def test_later_review_target_contains_exact_freeze_and_is_admitted(self) -> None:
        freeze, freeze_raw, execution, materialization, reviewed, _current, manifest_rel = self._history()
        self.assertEqual(manifest_rel, "frozen/freeze-manifest.json")
        value = M.validate_gate_b_admission(
            self._admission(source=execution, reviewed=reviewed),
            freeze_manifest=freeze_raw,
            review_root=self.reviews,
        )
        self.assertEqual(value["execution_tool_source_commit"], execution)
        self.assertEqual(value["reviewed_commit"], reviewed)
        self.assertNotEqual(reviewed, materialization)

    def test_execution_and_materialization_targets_are_rejected(self) -> None:
        _freeze, freeze_raw, execution, materialization, _reviewed, _current, _path = self._history()
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=execution), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-target-ancestry")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=materialization), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "reviewed-commit")

    def test_unrelated_and_future_review_targets_are_rejected(self) -> None:
        _freeze, freeze_raw, execution, _materialization, reviewed, current_head, _path = self._history()
        repo = self.root / "repo"
        branch = _git(repo, "symbolic-ref", "--short", "HEAD")
        _git(repo, "checkout", "--quiet", "--orphan", "unrelated")
        (repo / "unrelated.txt").write_bytes(b"unrelated\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "--quiet", "-m", "unrelated")
        unrelated = _git(repo, "rev-parse", "HEAD")
        _git(repo, "checkout", "--quiet", branch)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=unrelated), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-target-ancestry")

        _git(repo, "checkout", "--quiet", "-b", "future", current_head)
        (repo / "future.txt").write_bytes(b"future\n")
        _git(repo, "add", "future.txt")
        _git(repo, "commit", "--quiet", "-m", "future")
        future = _git(repo, "rev-parse", "HEAD")
        _git(repo, "checkout", "--quiet", branch)
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=future), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-target-ancestry")
        self.assertNotEqual(reviewed, future)

    def test_different_and_missing_manifest_bytes_are_rejected(self) -> None:
        _freeze, freeze_raw, execution, _materialization, reviewed, _current, _path = self._history(manifest_bytes=b"different manifest bytes\n")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=reviewed), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-target-manifest")

        assert self.freeze_patch is not None
        self.freeze_patch.stop()
        self.freeze_patch = None
        _freeze, freeze_raw, execution, _materialization, reviewed, _current, _path = self._history(missing_manifest=True, repo_name="repo-missing")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=reviewed), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-target-git")

    def test_committed_arbitrary_review_markdown_is_not_admissible(self) -> None:
        _freeze, freeze_raw, execution, _materialization, reviewed, _current, _path = self._history()
        repo = self.root / "repo"
        (self.reviews / "gate-b-final-01.md").write_bytes(b"# arbitrary markdown\nResult: Clean\n")
        _git(repo, "add", "reviews")
        _git(repo, "commit", "--quiet", "-m", "forged review body")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=reviewed), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-header")

    def test_committed_review_with_mismatched_semantic_header_is_rejected(self) -> None:
        _freeze, freeze_raw, execution, _materialization, reviewed, _current, _path = self._history()
        repo = self.root / "repo"
        (self.reviews / "gate-b-final-01.md").write_bytes(_review_bytes(1, M.REQUIRED_REVIEW_LENSES[0], reviewed_commit="f" * 40))
        _git(repo, "add", "reviews")
        _git(repo, "commit", "--quiet", "-m", "mismatched review header")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=reviewed), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-header-binding")

    def test_committed_review_with_mismatched_reviewer_header_is_rejected(self) -> None:
        _freeze, freeze_raw, execution, _materialization, reviewed, _current, _path = self._history()
        (self.reviews / "gate-b-final-01.md").write_bytes(
            _review_bytes(1, M.REQUIRED_REVIEW_LENSES[0], reviewer="reviewer-forged", reviewed_commit=reviewed)
        )
        _git(self.reviews.parent, "add", "reviews")
        _git(self.reviews.parent, "commit", "--quiet", "-m", "mismatched reviewer header")
        with self.assertRaises(M.AuthorityError) as context:
            M.validate_gate_b_admission(self._admission(source=execution, reviewed=reviewed), freeze_manifest=freeze_raw, review_root=self.reviews)
        self.assertEqual(context.exception.code, "review-header-binding")

    def test_admission_encoding_does_not_run_git(self) -> None:
        record = self._admission(source=EXECUTION_TOOL_SOURCE_COMMIT, reviewed=MATERIALIZATION_COMMIT)
        with mock.patch.object(M.subprocess, "run", side_effect=AssertionError("encoding must not run Git")):
            self.assertTrue(M.encode_gate_b_admission(json.loads(record)))


class AuthorityFreezeLoaderTests(unittest.TestCase):
    def test_public_freeze_module_is_not_trusted(self) -> None:
        fake = mock.Mock()
        private_name = "phase3_exact_authority_freeze"
        previous = M.sys.modules.pop(private_name, None)
        try:
            with mock.patch.dict(M.sys.modules, {"phase3_freeze_manifest": fake}, clear=False):
                loaded = M._freeze_module()
            self.assertIsNot(loaded, fake)
            self.assertTrue(callable(loaded.validate_manifest))
            fake.validate_manifest.assert_not_called()
        finally:
            M.sys.modules.pop(private_name, None)
            if previous is not None:
                M.sys.modules[private_name] = previous

    def test_frozen_validator_identity_rejects_stale_source_bytes(self) -> None:
        raw = M._canonical({
            "provenance_tool_identities": [{
                "path": "scripts/phase3_freeze_manifest.py",
                "mode": 0o644,
                "bytes": Path(M.__file__).with_name("phase3_freeze_manifest.py").stat().st_size,
                "sha256": "0" * 64,
            }],
        })
        with self.assertRaises(M.AuthorityError):
            M._freeze_module(raw)


if __name__ == "__main__":
    unittest.main()

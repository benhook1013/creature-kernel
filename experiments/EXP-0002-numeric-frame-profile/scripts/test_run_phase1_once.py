#!/usr/bin/env python3
"""Synthetic tests for the fail-closed EXP-0002 one-shot wrapper.

Nothing in this module points at the frozen manifest/corpora or starts the
authoritative candidate.  The orchestration tests use a temporary git
repository, temporary candidate bytes, and a fake runner command.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_phase1_once as wrapper  # noqa: E402


def _git(cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=cwd, text=True, capture_output=True, check=True)


def _synthetic_git_repo() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory(prefix="exp0002-wrapper-git-")
    root = Path(temporary.name)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "synthetic@example.invalid")
    _git(root, "config", "user.name", "Synthetic Wrapper")
    (root / "tracked.txt").write_text("clean\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "--quiet", "-m", "synthetic")
    return temporary, root


def _metadata() -> dict[str, object]:
    case_ids = [f"case-{index:02d}" for index in range(49)]
    corpora: list[dict[str, object]] = []
    start = 0
    for role, count in (("development", 17), ("held-out", 16), ("adversarial", 16)):
        ids = case_ids[start : start + count]
        start += count
        corpora.append({"role": role, "path": f"{role}.jsonl", "sha256": f"{role}-sha", "bytes": count, "count": count, "case_ids": ids})
    relations = {f"relation-{index:02d}": {"id": f"relation-{index:02d}", "cases": [case_ids[index]], "meaning": "synthetic relation"} for index in range(26)}
    return {"manifest_sha256": "manifest-sha", "evaluation_binding": wrapper.EVALUATION_BINDING, "corpora": corpora, "relations": relations, "oracle_bound": {"bound": 4096}}


def _fake_paths(root: Path, manifest: Path, runner: Path, candidate: Path) -> dict[str, Path]:
    return {"root": root, "package": root, "manifest": manifest, "runner": runner, "candidate_manifest": root / "Cargo.toml", "target": root, "candidate": candidate}


def _synthetic_result(metadata: dict[str, object], candidate: Path, candidate_sha: str, commit: str, *, evidence_status: str = "passed") -> dict[str, object]:
    corpora = metadata["corpora"]
    assert isinstance(corpora, list)
    classification = {"passed": "pass", "failed": "fail", "inconclusive": "inconclusive"}[evidence_status]
    cases: list[dict[str, object]] = []
    for corpus in corpora:
        assert isinstance(corpus, dict)
        cases.extend({"case_id": case_id, "classification": classification} for case_id in corpus["case_ids"])
    candidate_text = str(candidate.resolve())
    artifact = {"argument_index": 0, "argument": candidate_text, "sha256": candidate_sha}
    identity = {
        "schema": "ck.exp-0002.result-identity-1",
        "evaluation_binding": wrapper.EVALUATION_BINDING,
        "manifest_sha256": metadata["manifest_sha256"],
        "candidate_command": [candidate_text],
        "candidate_execution_command": [candidate_text],
        "candidate_command_artifacts": [artifact],
        "runner_bundle_sha256": "runner-bundle",
        "configured_budgets": {},
        "identity": {
            "stability": "verified",
            "pre_run": {"candidate_artifacts": [{"sha256": candidate_sha}]},
            "post_run": {"candidate_artifacts": [{"sha256": candidate_sha}]},
        },
        "profile_binding": None,
        "technology_result": "none",
    }
    relations = [{"id": f"relation-{index:02d}", "meaning": "synthetic relation", "case_ids": [f"case-{index:02d}"], "classification": classification} for index in range(26)]
    summary = {key: 0 for key in ("fail", "inconclusive", "incomplete", "pass", "unsupported")}
    summary[classification] = 49
    relation_summary = {key: 0 for key in summary}
    relation_summary[classification] = 26
    return {
        "schema": wrapper.RESULT_SCHEMA,
        "experiment_id": "EXP-0002",
        "evaluation_binding": wrapper.EVALUATION_BINDING,
        "profile_binding": None,
        "technology_result": "none",
        "run_status": "complete",
        "evidence_status": evidence_status,
        "protocol_revision": "ck.r3.numeric-candidate-request-1",
        "execution": {
            "candidate_processes": 1,
            "persistent_process": True,
            "corpus_sequence": list(wrapper.ROLES),
            "held_out_role": "non-tuning-not-blind-or-process-isolated",
            "environment_observations": "workload-position-conditioned",
        },
        "manifest": {"sha256": metadata["manifest_sha256"], "corpora": corpora, "oracle_bound": metadata["oracle_bound"]},
        "corpora": [{"role": corpus["role"], "planned_case_count": corpus["count"], "processed_case_count": corpus["count"], "cases": cases[offset : offset + corpus["count"]]} for offset, corpus in ((0, corpora[0]), (17, corpora[1]), (33, corpora[2]))],
        "relations": relations,
        "summary": summary,
        "relation_summary": relation_summary,
        "candidate": {
            "command": [candidate_text],
            "execution_command": [candidate_text],
            "command_artifacts": [artifact],
            "executable": candidate_text,
            "executable_sha256": candidate_sha,
            "build_identity": {"source": {"git_commit": commit}},
        },
        "runner": {"evaluation_binding": wrapper.EVALUATION_BINDING, "bundle_sha256": "runner-bundle", "budgets": {}},
        "result_identity": identity,
    }


class WrapperUnitTests(unittest.TestCase):
    def test_plan_and_acknowledgement_are_fail_closed(self) -> None:
        self.assertEqual(wrapper.main(["--preflight-only"]), 0)
        self.assertEqual(wrapper.main(["--preflight-only", "--execute", "--acknowledge", "wrong", "--attempt-id", "attempt-001"]), 0)
        self.assertEqual(wrapper.main(["--attempt-id", "attempt-001"]), 2)
        self.assertEqual(wrapper.main(["--execute", "--attempt-id", "attempt-001", "--acknowledge", ""]), 2)
        self.assertEqual(wrapper.main(["--acknowledge", wrapper.ACKNOWLEDGEMENT, "--attempt-id", "attempt-001"]), 2)
        self.assertEqual(wrapper.main(["--acknowledge", "wrong", "--attempt-id", "attempt-001"]), 2)

    def test_attempt_id_and_no_overwrite(self) -> None:
        temporary, root = _synthetic_git_repo()
        self.addCleanup(temporary.cleanup)
        commit = wrapper.source_snapshot(root)["commit"]
        self.assertEqual(wrapper.attempt_path(root, commit, "attempt-001").name, "attempt-001")
        with self.assertRaises(wrapper.WrapperError):
            wrapper.validate_attempt_id("attempt-1")
        target = wrapper.attempt_path(root, commit, "attempt-001")
        target.mkdir(parents=True)
        with self.assertRaises(wrapper.WrapperError):
            wrapper._create_attempt(target)

    def test_redirected_or_looped_target_rejects_before_attempt_creation(self) -> None:
        for mode in ("redirect", "loop"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="exp0002-wrapper-path-") as name:
                root = Path(name)
                package = root / "experiments" / "EXP-0002-numeric-frame-profile"
                (package / "corpora").mkdir(parents=True)
                (package / "scripts").mkdir()
                candidate_dir = package / "candidate"
                candidate_dir.mkdir()
                manifest = package / "corpora" / "manifest.json"
                runner = package / "scripts" / "run_adapter.py"
                candidate_manifest = candidate_dir / "Cargo.toml"
                manifest.write_text("{}", encoding="utf-8")
                runner.write_text("# fake\n", encoding="utf-8")
                candidate_manifest.write_text("# fake\n", encoding="utf-8")
                target = candidate_dir / "target"
                if mode == "redirect":
                    outside = root / "outside"
                    outside.mkdir()
                    target.symlink_to(outside, target_is_directory=True)
                else:
                    target.symlink_to(target, target_is_directory=True)
                candidate = target / wrapper.CANDIDATE_TARGET / "debug" / wrapper.CANDIDATE_BINARY
                with patch.multiple(wrapper, REPOSITORY_ROOT=root, PACKAGE_DIR=package, MANIFEST=manifest, RUNNER=runner, CANDIDATE_MANIFEST=candidate_manifest, CANDIDATE_PATH=candidate):
                    self.assertEqual(wrapper.main(["--execute", "--acknowledge", wrapper.ACKNOWLEDGEMENT, "--attempt-id", "attempt-001"]), 2)
                self.assertFalse((root / "experiments" / "EXP-0002-numeric-frame-profile" / "results").exists())

    def test_absent_target_and_candidate_are_allowed_before_build(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-absent-target-") as name:
            root = Path(name)
            package = root / "experiments" / "EXP-0002-numeric-frame-profile"
            (package / "corpora").mkdir(parents=True)
            (package / "scripts").mkdir()
            candidate_dir = package / "candidate"
            candidate_dir.mkdir()
            manifest = package / "corpora" / "manifest.json"
            runner = package / "scripts" / "run_adapter.py"
            candidate_manifest = candidate_dir / "Cargo.toml"
            manifest.write_text("{}", encoding="utf-8")
            runner.write_text("# fake\n", encoding="utf-8")
            candidate_manifest.write_text("# fake\n", encoding="utf-8")
            target = candidate_dir / "target"
            candidate = target / wrapper.CANDIDATE_TARGET / "debug" / wrapper.CANDIDATE_BINARY
            with patch.multiple(wrapper, PACKAGE_DIR=package, MANIFEST=manifest, RUNNER=runner, CANDIDATE_MANIFEST=candidate_manifest, CANDIDATE_PATH=candidate):
                paths = wrapper._validate_fixed_paths(root)
            self.assertEqual(paths["target"], target.resolve())
            self.assertEqual(paths["candidate"], candidate.resolve())

    def test_receipt_publication_is_exclusive_and_no_final_partial_on_write_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-receipt-") as name:
            root = Path(name)
            receipt_path = root / "receipt.json"
            wrapper._write_receipt(receipt_path, {"schema": "synthetic"})
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["schema"], "synthetic")
            with self.assertRaises(wrapper.WrapperError):
                wrapper._write_receipt(receipt_path, {"schema": "replacement"})
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["schema"], "synthetic")
            failed_path = root / "failed-receipt.json"
            with patch.object(wrapper.os, "fsync", side_effect=OSError("synthetic fsync failure")), self.assertRaises(OSError):
                wrapper._write_receipt(failed_path, {"schema": "synthetic"})
            self.assertFalse(failed_path.exists())
            self.assertTrue(list(root.glob(".failed-receipt.json.partial-*")))

    def test_clean_tree_gate_covers_tracked_staged_and_untracked(self) -> None:
        temporary, root = _synthetic_git_repo()
        self.addCleanup(temporary.cleanup)
        self.assertTrue(wrapper.source_snapshot(root)["clean"])
        (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
        self.assertFalse(wrapper.source_snapshot(root)["tracked_clean"])
        _git(root, "checkout", "--", "tracked.txt")
        (root / "tracked.txt").write_text("staged\n", encoding="utf-8")
        _git(root, "add", "tracked.txt")
        self.assertFalse(wrapper.source_snapshot(root)["staged_clean"])
        _git(root, "reset", "--quiet", "HEAD", "--", "tracked.txt")
        (root / "new.txt").write_text("untracked\n", encoding="utf-8")
        self.assertFalse(wrapper.source_snapshot(root)["untracked_clean"])

    def test_git_probe_fails_closed_on_timeout_and_untracked_overflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-probe-") as name:
            root = Path(name)
            commit = wrapper.CommandResult(("git",), 0, b"a" * 40 + b"\n", b"")
            timeout = wrapper.CommandResult(("git",), None, b"", b"", timed_out=True)
            clean = wrapper.CommandResult(("git",), 0, b"", b"")
            for probe_root in (root, Path.cwd()):
                with patch.object(wrapper, "_run_command", side_effect=[commit, timeout, clean, clean]):
                    snapshot = wrapper.source_snapshot(probe_root)
                self.assertFalse(snapshot["clean"])
                self.assertFalse(snapshot["untracked_covered"])
                overflow = wrapper.CommandResult(("git",), 0, b"x", b"", output_bound_exceeded=True)
                with patch.object(wrapper, "_run_command", side_effect=[commit, clean, clean, overflow]):
                    snapshot = wrapper.source_snapshot(probe_root)
                self.assertFalse(snapshot["clean"])
                self.assertFalse(snapshot["untracked_covered"])

    def test_fixed_commands_and_environment(self) -> None:
        self.assertIn("--target", wrapper._build_command())
        self.assertIn(wrapper.CANDIDATE_TARGET, wrapper._build_command())
        self.assertEqual(wrapper._build_command()[-2:], ["--locked", "--offline"])
        env = wrapper._build_environment()
        self.assertEqual(env["CARGO_BUILD_TARGET"], wrapper.CANDIDATE_TARGET)
        self.assertEqual(Path(env["CARGO_TARGET_DIR"]).resolve(), (wrapper.PACKAGE_DIR / "candidate" / "target").resolve())

    def test_result_crosschecks_reject_identity_or_case_drift(self) -> None:
        metadata = _metadata()
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-result-") as name:
            candidate = Path(name) / "candidate"
            candidate.write_bytes(b"candidate")
            candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            result_path = Path(name) / "result.json"
            result = _synthetic_result(metadata, candidate, candidate_sha, "a" * 40)
            result_path.write_text(json.dumps(result), encoding="utf-8")
            verified = wrapper.validate_result(result_path, manifest_metadata=metadata, candidate_path=candidate, candidate_sha256=candidate_sha, source={"commit": "a" * 40, "clean": True, "untracked_covered": True})
            self.assertEqual(verified["status"], "verified")
            with self.assertRaises(wrapper.WrapperError):
                wrapper.validate_result(result_path, manifest_metadata=metadata, candidate_path=candidate, candidate_sha256=candidate_sha, source={"commit": "a" * 40, "clean": True, "untracked_covered": True}, runner_exit_code=2)
            candidate.write_bytes(b"drift")
            with self.assertRaises(wrapper.WrapperError):
                wrapper.validate_result(result_path, manifest_metadata=metadata, candidate_path=candidate, candidate_sha256=candidate_sha, source={"commit": "a" * 40, "clean": True, "untracked_covered": True})
            candidate.write_bytes(b"candidate")
            result["manifest"]["sha256"] = "wrong"  # type: ignore[index]
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(wrapper.WrapperError):
                wrapper.validate_result(result_path, manifest_metadata=metadata, candidate_path=candidate, candidate_sha256=candidate_sha, source={"commit": "a" * 40, "clean": True, "untracked_covered": True})

    def test_result_counters_and_evidence_status_cannot_contradict_records(self) -> None:
        metadata = _metadata()
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-counter-") as name:
            candidate = Path(name) / "candidate"
            candidate.write_bytes(b"candidate")
            candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            result_path = Path(name) / "result.json"
            result = _synthetic_result(metadata, candidate, candidate_sha, "a" * 40, evidence_status="failed")
            result["summary"]["pass"] = 48  # type: ignore[index]
            result["summary"]["fail"] = 1  # type: ignore[index]
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(wrapper.WrapperError):
                wrapper.validate_result(result_path, manifest_metadata=metadata, candidate_path=candidate, candidate_sha256=candidate_sha, source={"commit": "a" * 40, "clean": True, "untracked_covered": True}, runner_exit_code=2)
            result = _synthetic_result(metadata, candidate, candidate_sha, "a" * 40, evidence_status="passed")
            result["evidence_status"] = "failed"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(wrapper.WrapperError):
                wrapper.validate_result(result_path, manifest_metadata=metadata, candidate_path=candidate, candidate_sha256=candidate_sha, source={"commit": "a" * 40, "clean": True, "untracked_covered": True}, runner_exit_code=2)

    def test_bounded_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-output-") as name:
            script = Path(name) / "output.py"
            script.write_text("import sys; sys.stdout.write('x' * 10000)\n", encoding="utf-8")
            result = wrapper._run_command([sys.executable, str(script)], cwd=Path(name), timeout=5.0, output_cap=128)
            self.assertTrue(result.output_bound_exceeded)
            self.assertLessEqual(len(result.stdout), 128)

    def test_candidate_artifact_cap_handles_sparse_72_mib_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-artifact-") as name:
            candidate = Path(name) / "candidate"
            with candidate.open("wb") as stream:
                stream.truncate(72 * 1024 * 1024)
            self.assertEqual(len(wrapper._file_sha256(candidate, cap=wrapper.MAX_ARTIFACT_BYTES)), 64)
            with self.assertRaises(wrapper.WrapperError):
                wrapper._file_sha256(candidate, cap=1 * 1024 * 1024)

    def test_post_validation_source_mutation_stops_before_build(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exp0002-wrapper-mutation-") as name:
            root = Path(name)
            candidate = root / "candidate"
            candidate.write_bytes(b"candidate")
            manifest = root / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            metadata = _metadata()
            commit = "d" * 40
            snapshots = iter((
                {"commit": commit, "clean": True, "tracked_clean": True, "staged_clean": True, "untracked_clean": True, "untracked_covered": True},
                {"commit": commit, "clean": False, "tracked_clean": False, "staged_clean": True, "untracked_clean": True, "untracked_covered": True},
            ))
            commands: list[tuple[str, ...]] = []

            def fake_command(argv: list[str] | tuple[str, ...], **kwargs: object) -> wrapper.CommandResult:
                command = tuple(str(value) for value in argv)
                commands.append(command)
                return wrapper.CommandResult(command, 0, b"ok\n", b"")

            with patch.multiple(wrapper, REPOSITORY_ROOT=root, PACKAGE_DIR=root, MANIFEST=manifest, CANDIDATE_MANIFEST=root / "Cargo.toml", CANDIDATE_PATH=candidate, _validate_fixed_paths=lambda _root: _fake_paths(root, manifest, root / "run_adapter.py", candidate), source_snapshot=lambda _root: next(snapshots), load_manifest=lambda _path: ({}, {}, metadata)), patch.object(wrapper, "_run_command", side_effect=fake_command), patch.object(wrapper, "_run_version_observations", return_value=[]):
                self.assertEqual(wrapper.main(["--execute", "--acknowledge", wrapper.ACKNOWLEDGEMENT, "--attempt-id", "attempt-001"]), 2)
            self.assertFalse(any(command and command[0] == "cargo" and "build" in command for command in commands))

    def test_receipt_preserved_for_validation_failure(self) -> None:
        temporary, root = _synthetic_git_repo()
        self.addCleanup(temporary.cleanup)
        with patch.object(wrapper, "REPOSITORY_ROOT", root), patch.object(wrapper, "_validate_fixed_paths", return_value=_fake_paths(root, root / "manifest.json", root / "run_adapter.py", root / "candidate")), patch.object(wrapper, "source_snapshot", return_value={"commit": "a" * 40, "clean": True, "tracked_clean": True, "staged_clean": True, "untracked_clean": True, "untracked_covered": True}), patch.object(wrapper, "load_manifest", side_effect=wrapper.WrapperError("synthetic validation")):
            self.assertEqual(wrapper.main(["--execute", "--acknowledge", wrapper.ACKNOWLEDGEMENT, "--attempt-id", "attempt-001"]), 2)
        receipt = root / "experiments" / "EXP-0002-numeric-frame-profile" / "results" / "phase1" / ("a" * 40) / "attempt-001" / "receipt.json"
        self.assertTrue(receipt.is_file())
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload["failure"]["stage"], "validation")
        self.assertEqual(payload["runner"]["invocations"], 0)

    def test_successful_fake_runner_accepts_failed_and_inconclusive_evidence(self) -> None:
        for evidence_status, runner_exit in (("failed", 2), ("inconclusive", 2)):
            with self.subTest(evidence_status=evidence_status), tempfile.TemporaryDirectory(prefix="exp0002-wrapper-flow-") as name:
                root = Path(name)
                candidate = root / "candidate"
                candidate.write_bytes(b"candidate")
                manifest = root / "manifest.json"
                manifest.write_text("{}", encoding="utf-8")
                runner_script = root / "run_adapter.py"
                runner_script.write_text("# fake\n", encoding="utf-8")
                metadata = _metadata()
                commit = "b" * 40
                candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
                runner_calls = [0]

                def fake_command(argv: list[str] | tuple[str, ...], **kwargs: object) -> wrapper.CommandResult:
                    argv_tuple = tuple(str(value) for value in argv)
                    if "--output" in argv_tuple:
                        runner_calls[0] += 1
                        output = Path(argv_tuple[argv_tuple.index("--output") + 1])
                        output.write_text(json.dumps(_synthetic_result(metadata, candidate, candidate_sha, commit, evidence_status=evidence_status)), encoding="utf-8")
                        return wrapper.CommandResult(argv_tuple, runner_exit, b"", b"")
                    if argv_tuple and argv_tuple[0] in {"rustc", "cargo"} and "-V" in argv_tuple:
                        return wrapper.CommandResult(argv_tuple, 0, b"version\n", b"")
                    if argv_tuple and argv_tuple[0] == "cargo" and "build" in argv_tuple:
                        return wrapper.CommandResult(argv_tuple, 0, b"", b"")
                    return wrapper.CommandResult(argv_tuple, 0, b"ok\n", b"")

                with patch.multiple(wrapper, REPOSITORY_ROOT=root, PACKAGE_DIR=root, MANIFEST=manifest, RUNNER=runner_script, CANDIDATE_MANIFEST=root / "Cargo.toml", CANDIDATE_PATH=candidate, _validate_fixed_paths=lambda _root: _fake_paths(root, manifest, runner_script, candidate), source_snapshot=lambda _root: {"commit": commit, "clean": True, "tracked_clean": True, "staged_clean": True, "untracked_clean": True, "untracked_covered": True}, load_manifest=lambda _path: ({}, {}, metadata)), patch.object(wrapper, "_run_command", side_effect=fake_command), patch.object(wrapper, "_run_version_observations", return_value=[]):
                    self.assertEqual(wrapper.main(["--execute", "--acknowledge", wrapper.ACKNOWLEDGEMENT, "--attempt-id", "attempt-001"]), 0)
                receipt = root / "experiments" / "EXP-0002-numeric-frame-profile" / "results" / "phase1" / commit / "attempt-001" / "receipt.json"
                payload = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertIsNone(payload["failure"])
                self.assertEqual(runner_calls[0], 1)
                self.assertEqual(payload["executable"]["sha256_after_run"], candidate_sha)
                self.assertEqual(payload["result"]["evidence_status"], evidence_status)
                self.assertEqual(payload["runner"]["exit_code"], runner_exit)

    def test_receipt_preserved_for_build_runner_and_integrity_failures(self) -> None:
        for failure_kind in ("build", "runner", "integrity"):
            with self.subTest(failure_kind=failure_kind), tempfile.TemporaryDirectory(prefix="exp0002-wrapper-failure-") as name:
                root = Path(name)
                candidate = root / "candidate"
                candidate.write_bytes(b"candidate")
                manifest = root / "manifest.json"
                manifest.write_text("{}", encoding="utf-8")
                runner_script = root / "run_adapter.py"
                runner_script.write_text("# fake\n", encoding="utf-8")
                metadata = _metadata()
                commit = "c" * 40
                candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()

                def fake_command(argv: list[str] | tuple[str, ...], **kwargs: object) -> wrapper.CommandResult:
                    argv_tuple = tuple(str(value) for value in argv)
                    if argv_tuple and argv_tuple[0] == "cargo" and "build" in argv_tuple:
                        return wrapper.CommandResult(argv_tuple, 9 if failure_kind == "build" else 0, b"", b"build failed\n" if failure_kind == "build" else b"")
                    if "--output" in argv_tuple:
                        if failure_kind == "runner":
                            return wrapper.CommandResult(argv_tuple, 9, b"", b"runner failed\n")
                        if failure_kind == "integrity":
                            output = Path(argv_tuple[argv_tuple.index("--output") + 1])
                            output.write_text("{}\n", encoding="utf-8")
                        return wrapper.CommandResult(argv_tuple, 0, b"", b"")
                    return wrapper.CommandResult(argv_tuple, 0, b"ok\n", b"")

                with patch.multiple(wrapper, REPOSITORY_ROOT=root, PACKAGE_DIR=root, MANIFEST=manifest, RUNNER=runner_script, CANDIDATE_MANIFEST=root / "Cargo.toml", CANDIDATE_PATH=candidate, _validate_fixed_paths=lambda _root: _fake_paths(root, manifest, runner_script, candidate), source_snapshot=lambda _root: {"commit": commit, "clean": True, "tracked_clean": True, "staged_clean": True, "untracked_clean": True, "untracked_covered": True}, load_manifest=lambda _path: ({}, {}, metadata)), patch.object(wrapper, "_run_command", side_effect=fake_command), patch.object(wrapper, "_run_version_observations", return_value=[]):
                    self.assertEqual(wrapper.main(["--execute", "--acknowledge", wrapper.ACKNOWLEDGEMENT, "--attempt-id", "attempt-001"]), 2)
                receipt = root / "experiments" / "EXP-0002-numeric-frame-profile" / "results" / "phase1" / commit / "attempt-001" / "receipt.json"
                payload = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual(payload["failure"]["stage"], failure_kind)
                self.assertEqual(payload["attempt"]["source_commit"], commit)


if __name__ == "__main__":
    unittest.main()

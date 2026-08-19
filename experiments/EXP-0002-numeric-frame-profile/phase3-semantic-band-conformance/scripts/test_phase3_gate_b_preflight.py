"""Read-only Gate B preflight tests over the current package and temp copies."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import phase3_gate_b_preflight as preflight
import phase3_freeze_manifest as freeze


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_V1_COMMIT = "553d51bd55dd837b01b950d063d288369f61e56d"
MANIFEST_REPOSITORY_PATH = "experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/manifests/freeze-manifest.json"


def _v1_fixture() -> bytes:
    """Read the immutable v1 predecessor, never the current package file."""
    result = subprocess.run(
        ["git", "-C", str(freeze.REPO), "show", f"{HISTORICAL_V1_COMMIT}:{MANIFEST_REPOSITORY_PATH}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 or not result.stdout.endswith(b"\n"):
        raise AssertionError("historical v1 manifest fixture unavailable")
    return result.stdout


def _candidate() -> dict[str, object]:
    return {
        "algorithm": preflight.EXPECTED_ALGORITHM,
        "count": preflight.EXPECTED_CANDIDATE_COUNT,
        "path_set_sha256": preflight.EXPECTED_PATH_SHA256,
        "content_sha256": preflight.EXPECTED_CONTENT_SHA256,
        "total_raw_bytes": preflight.EXPECTED_CANDIDATE_BYTES,
    }


def _tools(root: Path, paths: tuple[str, ...] = preflight.TOOL_PATHS) -> list[dict[str, object]]:
    return [{"path": path, "bytes": (root / path).stat().st_size, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()} for path in paths]


def _frozen_package(root: Path) -> Path:
    """Create a synthetic v2 package without touching Git or executing artifacts."""
    root.mkdir(parents=True, exist_ok=True)
    package = root / "package"
    shutil.copytree(ROOT, package)
    manifest_path = package / freeze.MANIFEST_REL

    def committed(_repo: Path, _commit: str, paths: tuple[str, ...]) -> list[dict]:
        return freeze._tool_identities(package, paths)

    with (
        patch.object(freeze, "_validate_candidate_commit_snapshot"),
        patch.object(freeze, "_validate_candidate_build_snapshot"),
        patch.object(freeze, "_assert_descendant_commit"),
        patch.object(freeze, "_execution_tool_identities_from_commit", side_effect=committed),
    ):
        successor = freeze.build_successor_manifest(
            _v1_fixture(),
            execution_tool_source_commit="e" * 40,
            package=package,
        )
    manifest_path.write_bytes((json.dumps(successor, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())
    manifest_path.chmod(0o644)
    return package


class GateBPreflightTests(unittest.TestCase):
    def test_fresh_freeze_module_receives_preflight_git_executable_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "a" / "b" / "c" / "d" / "package"
            scripts = root / "scripts"
            scripts.mkdir(parents=True)
            source = Path(freeze.__file__).read_bytes()
            validator = scripts / "phase3_freeze_manifest.py"
            validator.write_bytes(source)
            validator.chmod(0o644)
            manifest = json.dumps({
                "provenance_tool_identities": [{
                    "path": preflight.FREEZE_SCRIPT_PATH,
                    "mode": 0o644,
                    "bytes": len(source),
                    "sha256": hashlib.sha256(source).hexdigest(),
                }],
            }, sort_keys=True, separators=(",", ":"))
            with patch.object(preflight, "GIT_EXECUTABLE", "/tmp/preflight-git"):
                loaded = preflight._load_freeze_module(root, (manifest + "\n").encode())
            self.assertEqual(loaded.GIT_EXECUTABLE, "/tmp/preflight-git")

    def test_freeze_validator_replacement_after_identity_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            validator = scripts / "phase3_freeze_manifest.py"
            original = b"original validator bytes\n"
            validator.write_bytes(original)
            manifest = json.dumps({
                "provenance_tool_identities": [{
                    "path": preflight.FREEZE_SCRIPT_PATH,
                    "mode": 0o644,
                    "bytes": len(original),
                    "sha256": hashlib.sha256(original).hexdigest(),
                }],
            }, sort_keys=True, separators=(",", ":"))
            validator.write_bytes(b"replacement validator bytes\n")
            with self.assertRaises(preflight.GateBPreflightError):
                preflight._load_freeze_module(root, (manifest + "\n").encode())

    def test_regular_bytes_closes_parent_after_post_read_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool.py"
            path.write_bytes(b"tool\n")
            real_open = preflight.os.open
            real_close = preflight.os.close
            real_stat = preflight.os.stat
            opened: list[int] = []
            closed: list[int] = []
            stat_calls = 0

            def tracked_open(*args, **kwargs):
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            def tracked_close(descriptor: int) -> None:
                closed.append(descriptor)
                real_close(descriptor)

            def fail_recheck(*args, **kwargs):
                nonlocal stat_calls
                stat_calls += 1
                if stat_calls == 1:
                    return real_stat(*args, **kwargs)
                raise OSError("forced post-read race")

            with patch.object(preflight.os, "open", side_effect=tracked_open), patch.object(preflight.os, "close", side_effect=tracked_close), patch.object(preflight.os, "stat", side_effect=fail_recheck):
                with self.assertRaises(preflight.GateBPreflightError) as error:
                    preflight._regular_bytes(path, "tool.py")
            self.assertEqual(error.exception.code, "tool-race")
            self.assertEqual(set(opened), set(closed))

    def test_current_package_is_read_only_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = _frozen_package(Path(directory))
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                report = preflight.build_gate_b_preflight(package, _candidate(), _tools(package))
            self.assertEqual(report["schema"], preflight.SCHEMA)
            self.assertFalse(report["gate_b_ready"])
            self.assertFalse(report["readiness"])
            self.assertFalse(report["review"])
            self.assertFalse(report["execution_permitted"])
            self.assertFalse(report["authorization_accepted"])
            self.assertFalse(report["evidence"])
            self.assertEqual(report["technology_outcome"], "none")
            self.assertEqual(report["r3_activation"], "inactive")
            self.assertEqual(report["accounting"]["case_adjudications"], 60)
            self.assertEqual(report["accounting"]["candidate_wire_requests"], 57)
            self.assertEqual(report["accounting"]["runner_preflight_adjudications"], 3)
            self.assertEqual(next(check for check in report["checks"] if check["name"] == "expected-prebound-candidate-identity")["status"], "passed")
            self.assertEqual(report["execution_package"]["freeze_state"], "frozen")
            self.assertEqual(report["execution_package"]["manifest_sha256"], json.loads((package / freeze.MANIFEST_REL).read_text())["manifest_sha256"])
            self.assertEqual(report["execution_package"]["predecessor_manifest_sha256"], freeze.EXPECTED_V1_MANIFEST_SHA256)
            self.assertEqual(report["execution_package"]["candidate_source_commit"], "647eab5297adca1998764904cce98eca154738e4")
            self.assertEqual(report["execution_package"]["execution_tool_source_commit"], "e" * 40)
            snapshot = report["execution_package"]["source_snapshot_validation"]
            self.assertEqual(snapshot["status"], "passed")
            self.assertEqual(snapshot["ancestry_algorithm"], "git merge-base --is-ancestor")
            self.assertTrue(snapshot["candidate_is_ancestor_of_execution_tools"])
            self.assertTrue(snapshot["current_execution_tools_match_execution_tool_commit"])
            self.assertEqual(snapshot["current_execution_tool_identity_count"], 19)
            self.assertEqual(len(report["execution_package"]["runtime_tool_identities"]), len(freeze.RUNTIME_TOOLS))
            self.assertEqual(len(report["execution_package"]["exact_runtime_tool_identities"]), len(freeze.LEGACY_EXACT_RUNTIME_TOOLS))
            self.assertEqual(set(report["execution_package"]["binary_slots"]), set(freeze.SELECTORS))
            self.assertEqual(len(report["execution_package"]["provenance_tool_identities"]), len(freeze.PROVENANCE_TOOLS))
            self.assertEqual(len(report["tool_identities"]), 19)
            self.assertIn("preregistration pending-freeze fields are immutable Gate-A snapshot state", report["execution_package"]["note"])
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                first = preflight.build_gate_b_preflight_bytes(package, _candidate(), _tools(package))
                second = preflight.build_gate_b_preflight_bytes(package, _candidate(), _tools(package))
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())

    def test_historical_v1_package_is_not_current_preflight_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(ROOT, package)
            (package / freeze.MANIFEST_REL).write_bytes(_v1_fixture())
            (package / freeze.MANIFEST_REL).chmod(0o644)
            with patch.object(preflight, "_load_freeze_module", return_value=freeze):
                with self.assertRaises(preflight.GateBPreflightError) as error:
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))
            self.assertEqual(error.exception.code, "freeze-manifest")

    def test_checked_in_v4_package_remains_inspectable_but_is_not_v5_exact_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(ROOT, package)
            manifest = json.loads((package / freeze.MANIFEST_REL).read_text(encoding="utf-8"))
            for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
                for identity in manifest[field]:
                    raw = (package / identity["path"]).read_bytes()
                    identity["bytes"] = len(raw)
                    identity["sha256"] = hashlib.sha256(raw).hexdigest()
            with (
                patch.object(preflight, "_load_freeze_module", return_value=freeze),
                patch.object(freeze, "check_manifest", return_value=manifest),
            ):
                report = preflight.build_gate_b_preflight(package, _candidate(), _tools(package, preflight.V4_TOOL_PATHS))
            self.assertEqual(report["execution_package"]["freeze_state"], "frozen")
            self.assertEqual(report["execution_package"]["freeze_schema"], freeze.V4_SCHEMA)
            self.assertEqual(report["exact_runtime_closure"]["status"], "missing")
            self.assertIn("v5 freeze successor required by exact execution consumers", report["missing_gate_b_items"])

    def test_candidate_tool_tamper_and_forbidden_fields(self) -> None:
        bad_candidate = _candidate()
        bad_candidate["content_sha256"] = "0" * 64
        with self.assertRaises(preflight.GateBPreflightError):
            preflight.build_gate_b_preflight(ROOT, bad_candidate, _tools(ROOT))
        bad_tools = _tools(ROOT)
        bad_tools[-1] = dict(bad_tools[-1])
        bad_tools[-1]["bytes"] = int(bad_tools[-1]["bytes"]) + 1
        with self.assertRaises(preflight.GateBPreflightError):
            preflight.build_gate_b_preflight(ROOT, _candidate(), bad_tools)
        for forbidden in ("command", "shell", "environment", "acknowledgement", "path_to_run", "execution_permitted"):
            candidate = _candidate()
            candidate[forbidden] = "forbidden"
            with self.subTest(forbidden=forbidden), self.assertRaises(preflight.GateBPreflightError):
                preflight.build_gate_b_preflight(ROOT, candidate, _tools(ROOT))
        with self.assertRaises(preflight.GateBPreflightError):
            preflight.build_gate_b_preflight(ROOT, _candidate(), {"scripts/phase3_common.py": {"bytes": 1, "sha256": "a" * 64, "command": "cargo"}})

    def test_temp_copy_read_path_does_not_execute_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = _frozen_package(Path(temporary))
            before = sorted((path.relative_to(target).as_posix(), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()) for path in target.rglob("*") if path.is_file())
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                report = preflight.build_gate_b_preflight(target, _candidate(), _tools(target))
            after = sorted((path.relative_to(target).as_posix(), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()) for path in target.rglob("*") if path.is_file())
            self.assertFalse(report["execution_permitted"])
            self.assertEqual(before, after)

    def test_manifest_tamper_and_receipt_set_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = _frozen_package(Path(temporary))
            manifest_path = package / freeze.MANIFEST_REL
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["candidate_source_commit"] = "a" * 40
            manifest["manifest_sha256"] = freeze._self_hash(manifest)
            manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))

            # Restore the finalized package, then add an unlisted receipt.
            package = _frozen_package(Path(temporary) / "restored")
            (package / freeze.RECEIPT_DIR_REL / "extra.json").write_text("{}\n", encoding="utf-8")
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))

            package = _frozen_package(Path(temporary) / "tampered")
            receipt = package / freeze.RECEIPT_PATHS["wsl2-x86_64"]
            receipt.write_bytes(receipt.read_bytes() + b"\n")
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))

            package = _frozen_package(Path(temporary) / "missing")
            (package / freeze.RECEIPT_PATHS["ubuntu-24.04-x86_64"]).unlink()
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_resolve_source_commit", return_value="f" * 40), patch.object(freeze, "_validate_candidate_build_snapshot"), patch.object(freeze, "_validate_execution_commit_snapshot"), patch.object(freeze, "_validate_current_candidate_build_inputs"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))


if __name__ == "__main__":
    unittest.main()

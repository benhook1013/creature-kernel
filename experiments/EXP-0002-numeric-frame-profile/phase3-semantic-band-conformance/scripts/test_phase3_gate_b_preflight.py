"""Read-only Gate B preflight tests over the current package and temp copies."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import phase3_gate_b_preflight as preflight
import phase3_freeze_manifest as freeze


ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> dict[str, object]:
    return {
        "algorithm": preflight.EXPECTED_ALGORITHM,
        "count": preflight.EXPECTED_CANDIDATE_COUNT,
        "path_set_sha256": preflight.EXPECTED_PATH_SHA256,
        "content_sha256": preflight.EXPECTED_CONTENT_SHA256,
        "total_raw_bytes": preflight.EXPECTED_CANDIDATE_BYTES,
    }


def _tools(root: Path) -> list[dict[str, object]]:
    return [{"path": path, "bytes": (root / path).stat().st_size, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()} for path in preflight.TOOL_PATHS]


def _frozen_package(root: Path) -> Path:
    """Create a finalized package using the current scripts without touching Git artifacts."""
    root.mkdir(parents=True, exist_ok=True)
    package = root / "package"
    shutil.copytree(ROOT, package)
    manifest_path = package / freeze.MANIFEST_REL
    old_manifest = json.loads((ROOT / freeze.MANIFEST_REL).read_text(encoding="utf-8"))
    baseline = freeze.generate_manifest(package=package, source_commit=old_manifest["candidate_source_commit"])
    manifest_path.write_bytes((json.dumps(baseline, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())
    manifest_path.chmod(0o644)
    with patch.object(freeze, "_validate_candidate_commit_snapshot"):
        freeze.finalize_from_receipts(manifest_path, [package / freeze.RECEIPT_PATHS["wsl2-x86_64"], package / freeze.RECEIPT_PATHS["ubuntu-24.04-x86_64"]], package=package)
    return package


class GateBPreflightTests(unittest.TestCase):
    def test_current_package_is_read_only_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = _frozen_package(Path(directory))
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
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
            self.assertEqual(report["execution_package"]["candidate_source_commit"], "647eab5297adca1998764904cce98eca154738e4")
            self.assertEqual(set(report["execution_package"]["binary_slots"]), set(freeze.SELECTORS))
            self.assertEqual(len(report["execution_package"]["provenance_tool_identities"]), len(freeze.PROVENANCE_TOOLS))
            self.assertIn("preregistration pending-freeze fields are immutable Gate-A snapshot state", report["execution_package"]["note"])
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
                first = preflight.build_gate_b_preflight_bytes(package, _candidate(), _tools(package))
                second = preflight.build_gate_b_preflight_bytes(package, _candidate(), _tools(package))
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())

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
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
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
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))

            # Restore the finalized package, then add an unlisted receipt.
            package = _frozen_package(Path(temporary) / "restored")
            (package / freeze.RECEIPT_DIR_REL / "extra.json").write_text("{}\n", encoding="utf-8")
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))

            package = _frozen_package(Path(temporary) / "tampered")
            receipt = package / freeze.RECEIPT_PATHS["wsl2-x86_64"]
            receipt.write_bytes(receipt.read_bytes() + b"\n")
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))

            package = _frozen_package(Path(temporary) / "missing")
            (package / freeze.RECEIPT_PATHS["ubuntu-24.04-x86_64"]).unlink()
            with patch.object(preflight, "_load_freeze_module", return_value=freeze), patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(preflight.GateBPreflightError):
                    preflight.build_gate_b_preflight(package, _candidate(), _tools(package))


if __name__ == "__main__":
    unittest.main()

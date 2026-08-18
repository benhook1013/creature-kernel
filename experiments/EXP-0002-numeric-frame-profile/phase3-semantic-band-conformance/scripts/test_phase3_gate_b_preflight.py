"""Read-only Gate B preflight tests over the current package and temp copies."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import phase3_gate_b_preflight as preflight


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


class GateBPreflightTests(unittest.TestCase):
    def test_current_package_is_read_only_not_ready(self) -> None:
        report = preflight.build_gate_b_preflight(ROOT, _candidate(), _tools(ROOT))
        self.assertEqual(report["schema"], preflight.SCHEMA)
        self.assertFalse(report["gate_b_ready"])
        self.assertFalse(report["execution_permitted"])
        self.assertFalse(report["authorization_accepted"])
        self.assertFalse(report["evidence"])
        self.assertEqual(report["technology_outcome"], "none")
        self.assertEqual(report["r3_activation"], "inactive")
        self.assertEqual(report["accounting"]["case_adjudications"], 60)
        self.assertEqual(report["accounting"]["candidate_wire_requests"], 57)
        self.assertEqual(report["accounting"]["runner_preflight_adjudications"], 3)
        self.assertEqual(next(check for check in report["checks"] if check["name"] == "expected-prebound-candidate-identity")["status"], "passed")
        self.assertTrue(any("current-disk candidate closure" in item for item in report["missing_gate_b_items"]))
        first = preflight.build_gate_b_preflight_bytes(ROOT, _candidate(), _tools(ROOT))
        second = preflight.build_gate_b_preflight_bytes(ROOT, _candidate(), _tools(ROOT))
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
            target = Path(temporary) / "package"
            import shutil
            shutil.copytree(ROOT, target)
            before = sorted((path.relative_to(target).as_posix(), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()) for path in target.rglob("*") if path.is_file())
            report = preflight.build_gate_b_preflight(target, _candidate(), _tools(target))
            after = sorted((path.relative_to(target).as_posix(), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()) for path in target.rglob("*") if path.is_file())
            self.assertFalse(report["execution_permitted"])
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

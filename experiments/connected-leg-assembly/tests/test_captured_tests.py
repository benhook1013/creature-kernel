"""Focused mocked tests for the capture-before-test entrypoint."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import captured_tests  # noqa: E402


class CapturedTestsEntrypointTests(unittest.TestCase):
    def _fixture(self, root: Path, *, returncode: int = 0):
        snapshot = root / "snapshot"
        captured = snapshot / "arbitrary-layout" / "selected_case.py"
        managed = root / "managed-python"
        managed.write_text("runtime", encoding="utf-8")
        managed.chmod(0o755)
        logical = "tests/selected_case.py"
        manifest = {
            "source": {"files": [{
                "path": logical,
                "snapshot_path": str(captured),
            }]},
            "runtime": {"executable": str(managed)},
            "limitations": ["existing capture limitation"],
        }
        events = []

        fake_runner = mock.Mock()
        fake_runner.CAPTURE_FILES = ("runner.py", "root_source.py", "hip_source.py")

        def prepare(path, file_names):
            events.append("prepare")
            self.assertEqual(Path(path), snapshot)
            self.assertIn("captured_tests.py", file_names)
            self.assertIn(logical, file_names)
            captured.parent.mkdir(parents=True)
            captured.write_text("import unittest\nunittest.main()\n", encoding="utf-8")
            (snapshot / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            return manifest

        def verify(_path):
            events.append("verify")
            return manifest

        def invoke(command, **kwargs):
            events.append("test")
            return subprocess.CompletedProcess(command, returncode, "selected stdout", "selected stderr")

        fake_runner.prepare.side_effect = prepare
        fake_runner.verify.side_effect = verify
        return snapshot, logical, fake_runner, invoke, events

    def test_uses_manifest_path_and_verifies_before_and_after_selected_test(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, logical, fake_runner, invoke, events = self._fixture(Path(directory))
            report = captured_tests.run_captured_tests(
                snapshot, logical,
                ["ChosenTests.test_one"],
                runner_module=fake_runner, process_run=invoke)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(events, ["prepare", "verify", "test", "verify"])
        self.assertIn("arbitrary-layout/selected_case.py", report["captured_test_path"])
        self.assertEqual(report["selected_tests"], ["ChosenTests.test_one"])
        self.assertEqual(report["preverify"], "passed")
        self.assertEqual(report["postverify"], "passed")

    def test_nonzero_selected_test_is_failed_but_snapshot_is_postverified(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, logical, fake_runner, invoke, events = self._fixture(
                Path(directory), returncode=1)
            report = captured_tests.run_captured_tests(
                snapshot, logical,
                runner_module=fake_runner, process_run=invoke)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["test"]["returncode"], 1)
        self.assertEqual(events[-1], "verify")
        self.assertEqual(report["postverify"], "passed")

    def test_postverify_failure_overrides_successful_test(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot, logical, fake_runner, invoke, events = self._fixture(Path(directory))
            original_verify = fake_runner.verify.side_effect
            calls = 0

            def verify(path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    events.append("verify")
                    raise ValueError("captured drift")
                return original_verify(path)

            fake_runner.verify.side_effect = verify
            report = captured_tests.run_captured_tests(
                snapshot, logical,
                runner_module=fake_runner, process_run=invoke)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["postverify"], "failed")
        self.assertEqual(report["postverify_error"]["message"], "captured drift")

    def test_manifest_venv_symlink_is_retained_as_invocation_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, logical, fake_runner, _invoke, events = self._fixture(root)
            target = root / "system-python"
            target.write_text("runtime target", encoding="utf-8")
            target.chmod(0o755)
            recorded = root / "venv" / "bin" / "python"
            recorded.parent.mkdir(parents=True)
            recorded.symlink_to(target)
            manifest = fake_runner.prepare.side_effect(snapshot, [
                *fake_runner.CAPTURE_FILES, "captured_tests.py", logical])
            manifest["runtime"]["executable"] = str(recorded)
            fake_runner.prepare.side_effect = lambda _path, file_names: manifest
            fake_runner.verify.side_effect = lambda _path: manifest
            invoked = []

            def invoke(command, **_kwargs):
                invoked.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")

            report = captured_tests.run_captured_tests(
                snapshot, logical,
                runner_module=fake_runner, process_run=invoke)
            self.assertTrue(recorded.is_symlink())
            self.assertNotEqual(recorded, recorded.resolve())
            self.assertEqual(report["managed_python"], str(recorded))
            self.assertEqual(invoked[0][0], str(recorded))

    def test_rejects_unsafe_paths_and_selector_flags_before_capture(self):
        fake_runner = mock.Mock()
        with self.assertRaises(captured_tests.CapturedTestError):
            captured_tests.run_captured_tests("/tmp/unused", "../test.py",
                                              runner_module=fake_runner)
        with self.assertRaises(captured_tests.CapturedTestError):
            captured_tests.run_captured_tests("/tmp/unused", "tests/test.py",
                                              ["-k"], runner_module=fake_runner)
        fake_runner.prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()

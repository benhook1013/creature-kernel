from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


WRAPPER = Path(__file__).resolve().parents[1] / "test.sh"


class SurfacePreviewTestWrapperTests(unittest.TestCase):
    def run_wrapper(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], bool]:
        with tempfile.TemporaryDirectory(prefix="surface-preview-test-wrapper-", dir="/tmp") as directory:
            root = Path(directory)
            marker = root / "python-invoked"
            python_shim = root / "python-shim"
            python_shim.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" > \"$CK_SURFACE_PREVIEW_TEST_WRAPPER_MARKER\"\n"
                "exit 97\n",
                encoding="utf-8",
            )
            python_shim.chmod(0o755)
            environment = os.environ.copy()
            environment["CK_CURRENT_FORM_SURFACE_PYTHON"] = str(python_shim)
            environment["CK_SURFACE_PREVIEW_TEST_WRAPPER_MARKER"] = str(marker)
            result = subprocess.run(
                [str(WRAPPER), *arguments],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            return result, marker.exists()

    def test_rejects_slash_empty_and_invalid_selectors_before_unittest(self) -> None:
        selectors = ("testfoo/bar.py", "test/foo.py", "", "not_a_test.py")
        for selector in selectors:
            with self.subTest(selector=selector):
                result, python_invoked = self.run_wrapper(selector)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(python_invoked, result.stderr)
                self.assertIn("must begin with 'test' and must not contain '/'", result.stderr)
                self.assertNotIn("Ran ", result.stdout + result.stderr)

    def test_rejects_excess_arguments_before_unittest(self) -> None:
        result, python_invoked = self.run_wrapper("test_surface_preview.py", "test_one", "extra")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(python_invoked, result.stderr)
        self.assertIn("provide at most one test filename pattern and one test method pattern", result.stderr)
        self.assertNotIn("Ran ", result.stdout + result.stderr)

    def test_rejects_selector_that_matches_no_test_files(self) -> None:
        result, python_invoked = self.run_wrapper("test_does_not_exist.py")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(python_invoked, result.stderr)
        self.assertIn("matched no test files", result.stderr)

    def test_default_and_wildcard_selectors_reach_the_pinned_launcher(self) -> None:
        for arguments in ((), ("test*.py",)):
            with self.subTest(arguments=arguments):
                result, python_invoked = self.run_wrapper(*arguments)
                self.assertEqual(result.returncode, 97)
                self.assertTrue(python_invoked)

    def test_help_succeeds_from_non_root_directory(self) -> None:
        result, python_invoked = self.run_wrapper("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(python_invoked, result.stderr)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("test*.py pattern", result.stdout)

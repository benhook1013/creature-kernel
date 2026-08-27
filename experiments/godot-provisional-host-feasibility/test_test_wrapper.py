from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


WRAPPER = Path(__file__).resolve().parent / "test.sh"


class GodotTestWrapperTests(unittest.TestCase):
    def run_wrapper(
        self, *arguments: str, gallery: str = "/tmp/ck-gallery-preserved"
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        directory = tempfile.TemporaryDirectory(prefix="godot-test-wrapper-", dir="/tmp")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        arguments_path = root / "arguments"
        gallery_path = root / "gallery"
        python_shim = root / "python-shim"
        python_shim.write_text(
            "#!/bin/sh\n"
            "if [ \"${1-}\" = \"-\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            f"printf '%s\\0' \"$@\" > {shlex.quote(str(arguments_path))}\n"
            f"printf '%s\\n' \"${{CK_GODOT_STRUCTURAL_GALLERY-__UNSET__}}\" > {shlex.quote(str(gallery_path))}\n"
            "exit 97\n",
            encoding="utf-8",
        )
        python_shim.chmod(0o755)
        environment = os.environ.copy()
        environment["CK_CURRENT_FORM_SURFACE_PYTHON"] = str(python_shim)
        environment["CK_GODOT_STRUCTURAL_GALLERY"] = gallery
        result = subprocess.run(
            [str(WRAPPER), *arguments],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, arguments_path, gallery_path

    @staticmethod
    def read_arguments(path: Path) -> list[str]:
        return [argument.decode("utf-8") for argument in path.read_bytes().split(b"\0")[:-1]]

    def test_default_suite_reaches_pinned_launcher_and_preserves_gallery(self) -> None:
        result, arguments_path, gallery_path = self.run_wrapper()
        self.assertEqual(result.returncode, 97, result.stderr)
        self.assertEqual(
            self.read_arguments(arguments_path),
            [
                "-m",
                "unittest",
                "discover",
                "-s",
                str(WRAPPER.parent),
                "-p",
                "test*.py",
            ],
        )
        self.assertEqual(gallery_path.read_text(encoding="utf-8"), "/tmp/ck-gallery-preserved\n")

    def test_local_filename_pattern_is_forwarded_without_path_components(self) -> None:
        result, arguments_path, gallery_path = self.run_wrapper(
            "test_structural_gallery_smoke.py", gallery="/tmp/another-gallery"
        )
        self.assertEqual(result.returncode, 97, result.stderr)
        self.assertEqual(self.read_arguments(arguments_path)[-2:], ["-p", "test_structural_gallery_smoke.py"])
        self.assertEqual(gallery_path.read_text(encoding="utf-8"), "/tmp/another-gallery\n")

    def test_rejects_path_traversal_slashes_and_non_test_selectors_before_launcher(self) -> None:
        selectors = ("../test.py", "testfoo/bar.py", "test/../test.py", "", "not_a_test.py")
        for selector in selectors:
            with self.subTest(selector=selector):
                result, arguments_path, gallery_path = self.run_wrapper(selector)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(arguments_path.exists(), result.stderr)
                self.assertFalse(gallery_path.exists(), result.stderr)
                self.assertIn("must begin with 'test' and must not contain '/'", result.stderr)
                self.assertNotIn("Ran ", result.stdout + result.stderr)

    def test_rejects_excess_arguments_before_launcher(self) -> None:
        result, arguments_path, gallery_path = self.run_wrapper(
            "test_structural_gallery_smoke.py", "extra"
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(arguments_path.exists(), result.stderr)
        self.assertFalse(gallery_path.exists(), result.stderr)
        self.assertIn("provide at most one", result.stderr)

    def test_rejects_selector_that_matches_no_test_files(self) -> None:
        result, arguments_path, gallery_path = self.run_wrapper("test_does_not_exist.py")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(arguments_path.exists(), result.stderr)
        self.assertFalse(gallery_path.exists(), result.stderr)
        self.assertIn("matched no test files", result.stderr)

    def test_help_succeeds_without_invoking_launcher(self) -> None:
        result, arguments_path, gallery_path = self.run_wrapper("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(arguments_path.exists(), result.stderr)
        self.assertFalse(gallery_path.exists(), result.stderr)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("test*.py pattern", result.stdout)
        self.assertIn("test_structural_gallery_smoke.py)", result.stdout)

    def test_missing_or_non_executable_launcher_uses_fail_closed_error_path(self) -> None:
        for launcher_state in ("missing", "non-executable"):
            with self.subTest(launcher_state=launcher_state):
                directory = tempfile.TemporaryDirectory(prefix="godot-test-wrapper-launcher-")
                self.addCleanup(directory.cleanup)
                root = Path(directory.name)
                repository = root / "repo"
                test_dir = repository / "experiments" / "godot-provisional-host-feasibility"
                test_dir.mkdir(parents=True)
                wrapper = test_dir / "test.sh"
                wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
                wrapper.chmod(0o755)
                (test_dir / "test_placeholder.py").write_text("", encoding="utf-8")
                launcher = repository / "experiments" / "current-form-surface-preview" / "surface_preview_launcher.sh"
                launcher.parent.mkdir(parents=True)
                if launcher_state == "non-executable":
                    launcher.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
                    launcher.chmod(0o644)

                result = subprocess.run(
                    [str(wrapper), "test_placeholder.py"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("pinned current-form launcher is missing or not executable", result.stderr)
                self.assertIn("Usage:", result.stderr)
                self.assertIn("test_structural_gallery_smoke.py)", result.stderr)

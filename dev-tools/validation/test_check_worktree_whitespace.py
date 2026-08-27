#!/usr/bin/env python3

import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPOSITORY_ROOT / "dev-tools" / "validation" / "check_worktree_whitespace.sh"


class WorktreeWhitespaceCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Whitespace Test")
        self.git("config", "user.email", "whitespace-test@example.invalid")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repo,
            check=check,
            capture_output=True,
            text=True,
        )

    def commit_file(self, relative_path: str, contents: str) -> None:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        self.git("add", "--", relative_path)
        self.git("commit", "-q", "-m", "initial")

    def run_wrapper(self, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(WRAPPER)],
            cwd=cwd or self.repo,
            capture_output=True,
            text=True,
        )

    def test_clean_tracked_staged_and_untracked_files(self) -> None:
        self.commit_file("tracked.txt", "clean tracked content\n")

        staged = self.repo / "staged.txt"
        staged.write_text("clean staged content\n", encoding="utf-8")
        self.git("add", "--", "staged.txt")

        untracked = self.repo / "directory with spaces" / "--clean\nfile.txt"
        untracked.parent.mkdir()
        untracked.write_text("clean untracked content\n", encoding="utf-8")

        result = self.run_wrapper(self.repo / "directory with spaces")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_trailing_whitespace_in_tracked_unstaged_change_fails(self) -> None:
        self.commit_file("tracked.txt", "clean\n")
        (self.repo / "tracked.txt").write_text("trailing spaces   \n", encoding="utf-8")

        result = self.run_wrapper()

        self.assertNotEqual(result.returncode, 0)
        diagnostics = result.stdout + result.stderr
        self.assertIn("tracked.txt", diagnostics)
        self.assertIn("trailing whitespace", diagnostics)

    def test_space_before_tab_in_staged_change_fails(self) -> None:
        self.commit_file("staged.txt", "clean\n")
        (self.repo / "staged.txt").write_text(" \tindented\n", encoding="utf-8")
        self.git("add", "--", "staged.txt")

        result = self.run_wrapper()

        self.assertNotEqual(result.returncode, 0)
        diagnostics = result.stdout + result.stderr
        self.assertIn("staged.txt", diagnostics)
        self.assertIn("space before tab", diagnostics)

    def test_blank_line_at_eof_in_untracked_spaced_path_fails(self) -> None:
        self.commit_file("tracked.txt", "clean\n")
        untracked = self.repo / "untracked path with spaces.txt"
        untracked.write_text("content\n\n", encoding="utf-8")
        nested = self.repo / "nested"
        nested.mkdir()

        result = self.run_wrapper(nested)

        self.assertNotEqual(result.returncode, 0)
        diagnostics = result.stdout + result.stderr
        self.assertIn("untracked path with spaces.txt", diagnostics)
        self.assertIn("blank line at EOF", diagnostics)

    def test_ignored_files_are_not_checked(self) -> None:
        self.commit_file("tracked.txt", "clean\n")
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        self.git("add", "--", ".gitignore")
        self.git("commit", "-q", "-m", "ignore test")
        (self.repo / "ignored.txt").write_text("ignored   \n\n", encoding="utf-8")

        result = self.run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_untracked_file_is_clean(self) -> None:
        self.commit_file("tracked.txt", "clean\n")
        (self.repo / "empty.txt").touch()

        result = self.run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_does_not_change_index_or_worktree(self) -> None:
        self.commit_file("tracked.txt", "clean\n")
        (self.repo / "tracked.txt").write_text("unstaged clean\n", encoding="utf-8")
        staged = self.repo / "staged.txt"
        staged.write_text("staged clean\n", encoding="utf-8")
        self.git("add", "--", "staged.txt")
        untracked = self.repo / "untracked file.txt"
        untracked.write_text("untracked clean\n", encoding="utf-8")
        before_status = self.git("status", "--porcelain=v1", "-z").stdout
        before_index = self.git("diff", "--cached", "--raw", "-z").stdout
        before_contents = {
            path: path.read_bytes()
            for path in (self.repo / "tracked.txt", staged, untracked)
        }

        result = self.run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("status", "--porcelain=v1", "-z").stdout, before_status)
        self.assertEqual(self.git("diff", "--cached", "--raw", "-z").stdout, before_index)
        self.assertEqual(
            {path: path.read_bytes() for path in before_contents},
            before_contents,
        )


if __name__ == "__main__":
    unittest.main()

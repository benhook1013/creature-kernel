#!/usr/bin/env python3
"""Focused, non-executing tests for candidate prebinding closure checks."""

from __future__ import annotations

import importlib.util
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_candidate_prebinding.py")
SPEC = importlib.util.spec_from_file_location("candidate_prebinding", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CandidatePrebindingTests(unittest.TestCase):
    def test_git_mode_is_octal(self) -> None:
        self.assertEqual(MODULE.parse_git_mode("100644"), 33188)

    def test_schema_include_is_selected_and_expected_identity_is_fixed(self) -> None:
        entries = MODULE.select_base_entries()
        self.assertIn(MODULE.SCHEMA_PATH, {entry.path for entry in entries})
        expected = MODULE.Identity(
            47,
            1_494_337,
            "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc",
            "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2",
        )
        self.assertEqual(MODULE.identity(entries), expected)
        base, current = MODULE.check()
        self.assertEqual(base, expected)
        self.assertEqual(current, expected)

    def test_dynamic_include_is_rejected(self) -> None:
        with self.assertRaises(MODULE.CheckError):
            MODULE._include_targets('const P: &str = "x"; const B: &str = include_str!(P);', "src/lib.rs")

    def test_include_macro_and_recursive_rust_include_are_selected(self) -> None:
        root = MODULE.Entry("src/root.rs", 33188, b'include!("child.rs");')
        child = MODULE.Entry("src/child.rs", 33188, b'include!("nested.rs"); include_str!("data.txt");')
        nested = MODULE.Entry("src/nested.rs", 33188, b"fn nested() {}\n")
        data = MODULE.Entry("src/data.txt", 33188, b"payload\n")
        entries = {root.path: root}
        blobs = {entry.path: entry for entry in (root, child, nested, data)}
        with mock.patch.object(MODULE, "_all_blob_entries", return_value=(blobs, set(blobs))):
            MODULE._add_literal_include_targets(Path("."), "unused", entries)
        self.assertEqual(set(entries), set(blobs))

    def test_include_escape_is_rejected(self) -> None:
        with self.assertRaises(MODULE.CheckError):
            MODULE._include_targets('const B: &str = include_str!("../../outside");', "src/lib.rs")

    def test_duplicate_and_invalid_paths_are_rejected(self) -> None:
        entry = MODULE.Entry("src/lib.rs", 33188, b"x")
        with self.assertRaises(MODULE.CheckError):
            MODULE.identity([entry, entry])
        for path in ("", "./src/lib.rs", "src//lib.rs", "src/../lib.rs", "/src/lib.rs"):
            with self.assertRaises(MODULE.CheckError):
                MODULE.normalize_repo_path(path)

    def test_new_build_inputs_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            candidate = repo / MODULE.CANDIDATE_DIR
            candidate.mkdir(parents=True)
            (candidate / "build.rs").write_text("fn main() {}\n")
            (repo / ".cargo").mkdir()
            (repo / ".cargo/config.toml").write_text("[build]\n")
            (repo / "unrelated").mkdir()
            (repo / "unrelated/build.rs").write_text("fn main() {}\n")
            self.assertEqual(
                MODULE._new_build_inputs(repo, set()),
                [".cargo/config.toml", f"{MODULE.CANDIDATE_DIR}/build.rs"],
            )

    def test_unrelated_git_symlink_does_not_abort_tree_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "regular").write_bytes(b"x")
            (repo / "unrelated-link").symlink_to("regular")
            subprocess.run(["git", "add", "regular", "unrelated-link"], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
                cwd=repo,
                check=True,
            )
            blobs, paths = MODULE._all_blob_entries(repo, "HEAD")
            self.assertIn("regular", blobs)
            self.assertIn("unrelated-link", paths)
            self.assertNotIn("unrelated-link", blobs)

    def test_current_path_guards_reject_missing_symlink_and_non_regular(self) -> None:
        entry = MODULE.Entry("src/file", stat.S_IFREG | 0o644, b"x")
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "src").mkdir()
            (repo / "src/file").write_bytes(b"x")
            self.assertEqual(MODULE._safe_current_entry(repo, entry), entry)
            (repo / "src/file").unlink()
            (repo / "src/file").symlink_to("../missing")
            with self.assertRaises(MODULE.CheckError):
                MODULE._safe_current_entry(repo, entry)
            (repo / "src/file").unlink()
            (repo / "src/file").mkdir()
            with self.assertRaises(MODULE.CheckError):
                MODULE._safe_current_entry(repo, entry)


if __name__ == "__main__":
    unittest.main()

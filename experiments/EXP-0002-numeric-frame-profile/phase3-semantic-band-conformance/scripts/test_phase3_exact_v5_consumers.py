"""Exact consumer gates reject the immutable v4 predecessor."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import phase3_exact_attempt_launcher as launcher
import phase3_exact_attempt as attempt
import phase3_exact_authority as authority
import phase3_exact_custody as custody
from test_phase3_exact_attempt_launcher import _freeze


REPO = Path(__file__).resolve().parents[4]
V4_COMMIT = "369175137fc42f6cd99d32468ed4a6f10a0d6d59"
MANIFEST = "experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/manifests/freeze-manifest.json"


def _v4() -> bytes:
    result = subprocess.run(["git", "-C", str(REPO), "show", f"{V4_COMMIT}:{MANIFEST}"], check=False, stdout=subprocess.PIPE)
    if result.returncode:
        raise AssertionError("historical v4 fixture unavailable")
    return result.stdout


class ExactV5ConsumerTests(unittest.TestCase):
    def test_launcher_rejects_v4_before_loading_phase3_tools(self) -> None:
        with self.assertRaises(launcher.LauncherError) as error:
            launcher._validate_sibling_identities(_v4(), Path("/tmp"))
        self.assertIn(error.exception.code, {"freeze", "freeze-version"})

    def test_authority_rejects_v4(self) -> None:
        with self.assertRaises(authority.AuthorityError) as error:
            authority._validate_freeze(_v4())
        self.assertIn(error.exception.code, {"freeze", "freeze-version"})

    def test_custody_rejects_v4(self) -> None:
        with self.assertRaises(custody.CustodyError) as error:
            custody._parse_manifest(_v4())
        self.assertEqual(error.exception.code, "manifest-version")

    def test_v5_runtime_cross_binding_rejects_altered_absolute_interpreter_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            freeze = _freeze(Path(directory))
            selected = freeze["exact_python_runtime_contract"]["platforms"]["wsl2-x86_64"]
            selected["interpreter_identity"]["path"] = "/tmp/other-python"
            with self.assertRaises(attempt.ExactAttemptError) as error:
                attempt._validate_frozen_runtime_contract(freeze, "wsl2-x86_64")
            self.assertEqual(error.exception.code, "runtime-contract")

    def test_v5_runtime_cross_binding_rejects_altered_absolute_git_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            freeze = _freeze(Path(directory))
            selected = freeze["exact_python_runtime_contract"]["platforms"]["wsl2-x86_64"]
            selected["external_tools"]["git"]["path"] = "/tmp/other-git"
            with self.assertRaises(launcher.LauncherError) as error:
                probe = SimpleNamespace(
                    prepare_runtime_import_closure=lambda raw: {"prepared": True},
                    validate_current_attestation=lambda raw, **kwargs: {
                        "selector": "wsl2-x86_64",
                        "interpreter": selected["interpreter"],
                        "invocation": selected["invocation"],
                        "attestation_sha256": selected["attestation_identity"]["attestation_sha256"],
                    },
                )
                with patch.object(launcher, "_LOAD_ROOT", Path(directory)), patch.object(launcher, "_RETAINED_SIBLING_BYTES", {"scripts/phase3_python_runtime_probe.py": b"probe"}), patch.object(launcher, "_load_sibling_module", return_value=probe), patch.object(launcher.sys, "implementation", SimpleNamespace(name="cpython")), patch.object(launcher.sys, "version_info", SimpleNamespace(major=3, minor=13, micro=15)), patch.object(launcher.sys, "flags", SimpleNamespace(isolated=1)):
                    launcher._runtime_preflight(
                            freeze,
                            "wsl2-x86_64",
                            ["--launch-record", "/tmp/launch.json"],
                            [selected["interpreter"], "-I", launcher.SCRIPT_RELATIVE_PATH, "--launch-record", "/tmp/launch.json"],
                        )
            self.assertIn(error.exception.code, {"external-tool", "record-read"})

    def test_v5_runtime_provenance_tool_count_is_derived_and_closure_is_separate(self) -> None:
        def identity(path: str, number: int) -> dict[str, object]:
            return {"path": path, "mode": 0o644, "bytes": number, "sha256": f"{number:064x}"}

        freeze = {
            "schema": launcher.FREEZE_SCHEMA,
            "runtime_tool_identities": [identity(f"scripts/runtime-{index}.py", index + 1) for index in range(8)],
            "exact_runtime_tool_identities": [identity(f"scripts/exact-{index}.py", index + 9) for index in range(8)],
            "provenance_tool_identities": [identity(f"scripts/provenance-{index}.py", index + 17) for index in range(5)],
            "experiment_closure_tool_identities": [identity("scripts/phase3_experiment_closure.py", 22)],
        }
        self.assertEqual(len(launcher._raw_tool_identities(freeze)), 21)
        self.assertEqual(len(launcher._tool_identities(freeze)), 21)
        freeze["provenance_tool_identities"].pop()
        with self.assertRaises(launcher.LauncherError) as error:
            launcher._raw_tool_identities(freeze)
        self.assertEqual(error.exception.code, "tool-closure")


if __name__ == "__main__":
    unittest.main()

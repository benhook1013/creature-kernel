"""Non-executing tests for the exact-attempt launcher boundary."""

from __future__ import annotations

import json
from contextlib import contextmanager, ExitStack
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import phase3_exact_attempt_launcher as M


@contextmanager
def _chdir(path: Path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _freeze() -> dict[str, object]:
    invocation = list(M.PYTHON_INVOCATION)

    def identities(prefix: str, count: int) -> list[dict[str, object]]:
        return [{"path": f"scripts/{prefix}{index}.py", "mode": 0o644, "bytes": index + 1, "sha256": f"{index + 1:064x}"} for index in range(count)]

    return {
        "schema": M.FREEZE_SCHEMA,
        "exact_python_runtime_contract": {
            "schema": M.PYTHON_RUNTIME_CONTRACT_SCHEMA,
            "platforms": {
                selector: {
                    "selector": selector,
                    "implementation": "CPython",
                    "version": M.PYTHON_VERSION,
                    "invocation": invocation,
                    "module_loading": M.PYTHON_MODULE_LOADING,
                    "entrypoint": M.PYTHON_ENTRYPOINT,
                }
                for selector in M.SELECTORS
            },
        },
        "candidate_closure": {
            "algorithm": "ck.phase3-candidate-source-build-closure.v1",
            "count": 47,
            "path_set_sha256": "a" * 64,
            "content_sha256": "b" * 64,
            "total_raw_bytes": 1494337,
        },
        "runtime_tool_identities": identities("runtime-", 8),
        "exact_runtime_tool_identities": identities("exact-", 8),
        "provenance_tool_identities": identities("provenance-", 4),
    }


class LauncherTests(unittest.TestCase):
    def _setup(self, *, launch_value: dict[str, object] | None = None) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object], bytes]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "reviews").mkdir()
        freeze = _freeze()
        freeze_raw = _canonical(freeze)
        if launch_value is None:
            launch_value = {
                "schema": M.LAUNCH_RECORD_SCHEMA,
                "package_root": ".",
                "attempt_id": "attempt-001",
                "platform_selector": "wsl2-x86_64",
                "ordinal": 0,
                "freeze_manifest_path": "freeze.json",
                "admission_record_path": "admission.json",
                "authorization_record_path": "authorization.json",
                "custody_record_path": "custody.json",
                "review_root": "reviews",
                "output_root": str(root / "output"),
                "work_root": str(root / "work"),
            }
        (root / "launch.json").write_bytes(_canonical(launch_value))
        (root / "freeze.json").write_bytes(freeze_raw)
        for name in ("admission.json", "authorization.json", "custody.json"):
            (root / name).write_bytes(_canonical({"record": name}))
        return temporary, root, launch_value, freeze_raw

    def _runtime(self, root: Path, *, isolated: int = 1, version: tuple[int, int, int] = (3, 13, 15), orig: list[str] | None = None):
        if orig is None:
            orig = ["/opt/python3.13", "-I", M.SCRIPT_RELATIVE_PATH, "--launch-record", "launch.json"]
        return patch.object(M.sys, "implementation", SimpleNamespace(name="cpython")), patch.object(M.sys, "version_info", SimpleNamespace(major=version[0], minor=version[1], micro=version[2])), patch.object(M.sys, "flags", SimpleNamespace(isolated=isolated)), patch.object(M.sys, "orig_argv", orig)

    def test_help_does_not_load_or_execute(self) -> None:
        with patch.object(M, "_invoke_exact_attempt") as invoke, patch.object(M, "_load_sibling_module", side_effect=AssertionError("help loaded a module")):
            self.assertEqual(M.main(["--help"]), 0)
        invoke.assert_not_called()

    def test_malformed_duplicate_oversized_and_unsafe_records_fail_before_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_bytes(b'{"schema":"x","schema":"y"}\n')
            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b"a" * M.MAX_RECORD_BYTES + b"}\n")
            for path in (duplicate, oversized):
                with self.subTest(path=path.name), patch.object(M, "_invoke_exact_attempt") as invoke:
                    with self.assertRaises(M.LauncherError):
                        M.main(["--launch-record", str(path)])
                    invoke.assert_not_called()

            temporary, _, launch, _ = self._setup()
            try:
                launch["freeze_manifest_path"] = "../freeze.json"
                path = root / "unsafe.json"
                path.write_bytes(_canonical(launch))
                with patch.object(M, "_invoke_exact_attempt") as invoke, self.assertRaises(M.LauncherError):
                    M.main(["--launch-record", str(path)])
                invoke.assert_not_called()
            finally:
                temporary.cleanup()

    def test_runtime_version_isolation_and_argv_fail_before_call(self) -> None:
        temporary, root, _, _ = self._setup()
        try:
            cases = {
                "version": {"version": (3, 13, 14)},
                "no-isolated": {"isolated": 0},
                "argv": {"orig": ["/opt/python3.13", "-I", M.SCRIPT_RELATIVE_PATH, "--launch-record", "other.json"]},
            }
            for label, options in cases.items():
                with self.subTest(label=label), patch.object(M, "_validate_freeze", return_value=_freeze()), patch.object(M, "_invoke_exact_attempt") as invoke:
                    with ExitStack() as stack:
                        stack.enter_context(_chdir(root))
                        for context in self._runtime(root, **options):
                            stack.enter_context(context)
                        with self.assertRaises(M.LauncherError):
                            M.main(["--launch-record", "launch.json"])
                    invoke.assert_not_called()
        finally:
            temporary.cleanup()

    def test_valid_synthetic_launch_calls_private_seam_once_with_exact_bytes_and_paths(self) -> None:
        temporary, root, _, freeze_raw = self._setup()
        try:
            observed: list[dict[str, object]] = []

            def invoke(**inputs: object) -> None:
                observed.append(inputs)

            with patch.object(M, "_validate_freeze", return_value=_freeze()), patch.object(M, "_invoke_exact_attempt", side_effect=invoke) as seam:
                with ExitStack() as stack:
                    stack.enter_context(_chdir(root))
                    for context in self._runtime(root):
                        stack.enter_context(context)
                    self.assertEqual(M.main(["--launch-record", "launch.json"]), 0)
            seam.assert_called_once()
            self.assertEqual(len(observed), 1)
            inputs = observed[0]
            self.assertEqual(inputs["freeze_manifest"], freeze_raw)
            self.assertEqual(inputs["admission_record"], (root / "admission.json").read_bytes())
            self.assertEqual(inputs["authorization_record"], (root / "authorization.json").read_bytes())
            self.assertEqual(inputs["custody_record"], (root / "custody.json").read_bytes())
            self.assertEqual(inputs["package_root"], root)
            self.assertEqual(inputs["review_root"], root / "reviews")
            self.assertEqual(inputs["attempt_id"], "attempt-001")
        finally:
            temporary.cleanup()

    def test_isolated_production_sibling_load_reaches_patched_attempt_without_candidate_work(self) -> None:
        """Exercise the real sibling import graph while keeping the attempt inert."""
        module_names = {
            "phase3_common", "phase3_oracle", "phase3_scorer", "phase3_runner",
            "phase3_materialized_adapter", "phase3_evidence_contract", "phase3_exact_fp_observer",
            "phase3_exact_transport", "phase3_exact_adjudicator", "phase3_gate_b_preflight",
            "phase3_build_receipt", "phase3_freeze_manifest", "phase3_exact_authority",
            "phase3_exact_custody", "phase3_exact_publication", "phase3_exact_attempt",
        }
        saved = {name: __import__("sys").modules.get(name) for name in module_names}
        for name in module_names:
            __import__("sys").modules.pop(name, None)
        ambient = __import__("types").ModuleType("phase3_exact_attempt")
        ambient.run_exact_attempt = lambda **_: (_ for _ in ()).throw(AssertionError("ambient attempt module was consumed"))
        __import__("sys").modules["phase3_exact_attempt"] = ambient
        observed: list[dict[str, object]] = []
        real_loader = M._load_sibling_module

        def loader(filename: str, module_name: str, **kwargs: object):
            module = real_loader(filename, module_name, **kwargs)
            if filename == "phase3_exact_attempt.py":
                module.run_exact_attempt = lambda **inputs: observed.append(inputs)
            return module

        try:
            with patch.object(M, "_load_sibling_module", side_effect=loader):
                M._invoke_exact_attempt(package_root=Path("/tmp/package"), attempt_id="attempt-001")
            self.assertEqual(len(observed), 1)
            self.assertEqual(observed[0]["attempt_id"], "attempt-001")
            self.assertIn("phase3_exact_attempt", __import__("sys").modules)
        finally:
            for name, module in saved.items():
                if module is None:
                    __import__("sys").modules.pop(name, None)
                else:
                    __import__("sys").modules[name] = module


if __name__ == "__main__":
    unittest.main()

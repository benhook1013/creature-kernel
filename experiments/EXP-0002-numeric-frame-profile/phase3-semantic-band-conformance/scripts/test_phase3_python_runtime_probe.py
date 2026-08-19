"""Synthetic, non-provisioning tests for the Phase 3 runtime attestation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import phase3_freeze_manifest as freeze
import phase3_python_runtime_probe as probe


def _identity(path: Path) -> dict:
    return probe._identity(path)


def _record(root: Path, selector: str = "wsl2-x86_64", *, interpreter_bytes: bytes = b"python-3.13.15") -> bytes:
    interpreter = root / "opt" / "python3.13"
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_bytes(interpreter_bytes)
    interpreter.chmod(0o755)
    stdlib = root / "opt" / "stdlib.py"
    native = root / "opt" / "_runtime.so"
    stdlib.write_bytes(b"stdlib fixture")
    native.write_bytes(b"native fixture")
    for path in (stdlib, native):
        path.chmod(0o644)
    files = sorted((_identity(stdlib), _identity(native)), key=lambda item: item["path"])
    unsigned = {
        "schema": probe.SCHEMA,
        "selector": selector,
        "implementation": "CPython",
        "version": "3.13.15",
        "interpreter": interpreter.as_posix(),
        "interpreter_identity": _identity(interpreter),
        "invocation": [interpreter.as_posix(), "-I", "scripts/phase3_exact_attempt_launcher.py", "--launch-record", "<launch-record>"],
        "module_loading": probe.MODULE_LOADING,
        "entrypoint": probe.ENTRYPOINT,
        "runtime_roots": [str((root / "opt").as_posix())],
        "files": files,
        "imported_modules": [{"name": "fixture_native", "kind": "extension", "origin": _identity(native), "cached": None}],
        "loader_dependencies": [_identity(native)],
        "sys_path": [],
        "environment_policy": {
            "mode": "sanitized-env-i", "ambient": "excluded", "observed_keys": [],
            "values": {"PATH": "<bound-tool-path>", "HOME": "<sanitized-home>", "XDG_CONFIG_HOME": "<sanitized-xdg-config>", "XDG_CACHE_HOME": "<sanitized-xdg-cache>", "PYTHONPATH": "<forbidden>", "PYTHONHOME": "<forbidden>", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "LANG": "C", "LC_ALL": "C"},
        },
        "canonicalization": {"encoding": "UTF-8", "json": "RFC 8259-compatible strict JSON", "sort_keys": True, "separators": [",", ":"], "ensure_ascii": True, "trailing_newline": True, "self_hash_domain": probe.HASH_DOMAIN.decode("ascii").rstrip("\0"), "self_hash_excludes": ["attestation_sha256"]},
    }
    unsigned["attestation_sha256"] = hashlib.sha256(probe.HASH_DOMAIN + probe.canonical(unsigned)).hexdigest()
    return probe.canonical(unsigned)


class PythonRuntimeProbeTests(unittest.TestCase):
    def _require_runtime(self, raw: bytes, state: tuple[list[dict], list[dict]]) -> None:
        value = json.loads(raw)
        with (
            patch.object(probe.sys, "executable", value["interpreter"]),
            patch.object(probe.sys, "implementation", types.SimpleNamespace(name="cpython")),
            patch.object(probe.sys, "version_info", (3, 13, 15)),
            patch.object(probe.sys, "path", list(value["sys_path"])),
            patch.object(probe, "_environment_policy", return_value=value["environment_policy"]),
            patch.object(probe, "_runtime_state", return_value=state),
        ):
            probe.validate_current_attestation(raw, expected_selector=value["selector"], require_current_runtime=True)

    def test_fixture_record_is_deterministic_and_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = _record(Path(directory))
            value = probe.validate_current_attestation(raw, expected_selector="wsl2-x86_64")
            self.assertEqual(value["attestation_sha256"], hashlib.sha256(probe.HASH_DOMAIN + probe.canonical({key: value[key] for key in value if key != "attestation_sha256"})).hexdigest())
            self.assertEqual(probe.attestation_identity(raw, path=probe.ATTESTATION_PATHS["wsl2-x86_64"])["sha256"], hashlib.sha256(raw).hexdigest())

    def test_altered_path_home_xdg_do_not_enter_attestation_policy(self) -> None:
        with patch.dict("os.environ", {"PATH": "/altered", "HOME": "/altered-home", "XDG_CONFIG_HOME": "/altered-config", "XDG_CACHE_HOME": "/altered-cache"}, clear=False):
            first = probe._environment_policy()
        with patch.dict("os.environ", {"PATH": "/other", "HOME": "/other-home", "XDG_CONFIG_HOME": "/other-config", "XDG_CACHE_HOME": "/other-cache"}, clear=False):
            second = probe._environment_policy()
        self.assertEqual(first, second)

    def test_same_version_different_interpreter_bytes_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = probe.validate_attestation(_record(root / "first"))
            second = probe.validate_attestation(_record(root / "second", interpreter_bytes=b"different-python"))
            self.assertEqual(first["version"], second["version"])
        self.assertNotEqual(first["interpreter_identity"]["sha256"], second["interpreter_identity"]["sha256"])

    def test_static_frozen_script_import_graph_is_covered_without_importing_siblings(self) -> None:
        root = Path(__file__).parent
        stdlib: set[str] = set()
        other: set[str] = set()
        for relative in probe.FROZEN_PHASE3_SCRIPT_FILES:
            found_stdlib, found_other = probe._static_imports((root.parent / relative).read_bytes(), relative)
            stdlib.update(found_stdlib)
            other.update(found_other)
        self.assertTrue(stdlib <= set(probe.FROZEN_PHASE3_STDLIB_MODULES))
        authenticated = set(freeze.RUNTIME_TOOLS) | set(freeze.EXACT_RUNTIME_TOOLS)
        runtime_loaded_provenance = {
            "scripts/phase3_build_receipt.py",
            "scripts/phase3_freeze_manifest.py",
            "scripts/check_candidate_prebinding.py",
            freeze.RUNTIME_PROBE_PATH,
        }
        self.assertEqual(set(probe.FROZEN_PHASE3_SCRIPT_FILES), authenticated | runtime_loaded_provenance)
        launcher_tree = probe.ast.parse((root / "phase3_exact_attempt_launcher.py").read_bytes())
        launcher_loaded: set[str] = set()
        for node in probe.ast.walk(launcher_tree):
            if not isinstance(node, probe.ast.For) or not isinstance(node.target, probe.ast.Name) or node.target.id != "filename":
                continue
            if not isinstance(node.iter, (probe.ast.Tuple, probe.ast.List)):
                continue
            values = [item.value for item in node.iter.elts if isinstance(item, probe.ast.Constant) and isinstance(item.value, str)]
            if values and all(value.endswith(".py") for value in values):
                launcher_loaded.update(f"scripts/{value}" for value in values)
        self.assertTrue(launcher_loaded)
        self.assertTrue(launcher_loaded <= set(probe.FROZEN_PHASE3_SCRIPT_FILES))
        self.assertIn("ctypes", stdlib)
        self.assertIn("ast", stdlib)
        self.assertIn("importlib", stdlib)
        self.assertIn("tomllib", stdlib)
        self.assertIn("phase3_common", {item.split(".", 1)[0] for item in other})

    def test_prepare_runtime_import_closure_is_fixed_and_native_ready(self) -> None:
        prepared = probe.prepare_runtime_import_closure()
        expected = set(probe.FROZEN_PHASE3_STDLIB_MODULES)
        if tuple(probe.sys.version_info[:2]) < (3, 11):
            expected.remove("tomllib")
            self.assertNotIn("tomllib", prepared)
        else:
            self.assertIn("tomllib", prepared)
        self.assertEqual(set(prepared), expected)
        self.assertEqual(len(prepared), len(expected))
        self.assertIn("ctypes", prepared)
        self.assertIn("_ctypes", prepared)

    def test_target_runtime_does_not_silently_skip_tomllib(self) -> None:
        if tuple(probe.sys.version_info[:2]) >= (3, 11):
            self.skipTest("host already provides target-required tomllib")
        with patch.object(probe.sys, "version_info", (3, 13, 15)):
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.prepare_runtime_import_closure()
        self.assertEqual(error.exception.code, "import-closure")

    def test_observed_cached_bytecode_is_bound_and_tamper_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = json.loads(_record(root))
            source = root / "opt" / "cached_source.py"
            cached = root / "opt" / "cached_source.pyc"
            source.write_bytes(b"source")
            cached.write_bytes(b"bytecode")
            source.chmod(0o644)
            cached.chmod(0o644)
            source_identity = _identity(source)
            cached_identity = _identity(cached)
            raw["files"].extend((source_identity, cached_identity))
            raw["files"].sort(key=lambda item: item["path"])
            raw["imported_modules"] = [{"name": "cached_source", "kind": "source", "origin": source_identity, "cached": cached_identity}, *raw["imported_modules"]]
            raw["imported_modules"].sort(key=lambda item: item["name"])
            raw["attestation_sha256"] = hashlib.sha256(probe.HASH_DOMAIN + probe.canonical({key: raw[key] for key in raw if key != "attestation_sha256"})).hexdigest()
            checked = probe.validate_current_attestation(probe.canonical(raw))
            self.assertEqual(checked["imported_modules"][0]["cached"]["sha256"], cached_identity["sha256"])
            cached.write_bytes(b"tampered-bytecode")
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.validate_current_attestation(probe.canonical(raw))
            self.assertEqual(error.exception.code, "file-drift")

    def test_post_capture_module_dependency_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = _record(root)
            value = json.loads(raw)
            extra = root / "opt" / "extra.py"
            extra.write_bytes(b"extra")
            extra.chmod(0o644)
            modules = list(value["imported_modules"])
            modules.append({"name": "late_dependency", "kind": "source", "origin": _identity(extra), "cached": None})
            with self.assertRaises(probe.RuntimeProbeError) as error:
                self._require_runtime(raw, (modules, value["loader_dependencies"]))
            self.assertEqual(error.exception.code, "module-closure")

    def test_post_capture_native_loader_dependency_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = _record(root)
            value = json.loads(raw)
            extra = root / "opt" / "late.so"
            extra.write_bytes(b"late-native")
            extra.chmod(0o644)
            loaders = list(value["loader_dependencies"])
            loaders.append(_identity(extra))
            loaders.sort(key=lambda item: item["path"])
            with self.assertRaises(probe.RuntimeProbeError) as error:
                self._require_runtime(raw, (value["imported_modules"], loaders))
            self.assertEqual(error.exception.code, "loader-closure")

    def test_descriptor_walk_rejects_symlink_parent_and_final_component(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_bytes(b"target")
            target.chmod(0o644)
            (root / "parent-link").symlink_to(root, target_is_directory=True)
            (root / "final-link").symlink_to(target)
            with self.assertRaises(probe.RuntimeProbeError) as parent_error:
                probe._identity(root / "parent-link" / "target")
            with self.assertRaises(probe.RuntimeProbeError) as final_error:
                probe._identity(root / "final-link")
            self.assertEqual(parent_error.exception.code, "symlink")
            self.assertEqual(final_error.exception.code, "symlink")

    def test_descriptor_read_race_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stable.py"
            path.write_bytes(b"stable")
            path.chmod(0o644)
            with patch.object(probe, "_stat_signature", side_effect=[(1,), (2,)]):
                with self.assertRaises(probe.RuntimeProbeError) as error:
                    probe._identity(path)
            self.assertEqual(error.exception.code, "file-race")

    def test_group_world_writable_mode_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.py"
            path.write_bytes(b"unsafe")
            path.chmod(0o777)
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe._identity(path)
            self.assertEqual(error.exception.code, "file-mode")

    def test_stdlib_or_native_tamper_and_missing_file_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = _record(root)
            native = root / "opt" / "_runtime.so"
            native.write_bytes(b"tampered")
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.validate_current_attestation(raw, check_files=True)
            self.assertEqual(error.exception.code, "file-drift")
            native.unlink()
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.validate_current_attestation(raw, check_files=True)
            self.assertIn(error.exception.code, {"missing-file", "file-drift"})

    def test_absolute_path_and_selector_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = json.loads(_record(root))
            value["interpreter"] = "python3.13"
            value["attestation_sha256"] = hashlib.sha256(probe.HASH_DOMAIN + probe.canonical({key: value[key] for key in value if key != "attestation_sha256"})).hexdigest()
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.validate_attestation(probe.canonical(value))
            self.assertEqual(error.exception.code, "path")
            value = json.loads(_record(root))
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.validate_current_attestation(probe.canonical(value), expected_selector="ubuntu-24.04-x86_64", check_files=False)
            self.assertEqual(error.exception.code, "selector")

    def test_duplicate_modules_loaders_and_sys_path_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = json.loads(_record(root))
            for field, mutate in (
                ("imported_modules", lambda value: value["imported_modules"].append(dict(value["imported_modules"][0]))),
                ("loader_dependencies", lambda value: value["loader_dependencies"].append(dict(value["loader_dependencies"][0]))),
                ("sys_path", lambda value: value.__setitem__("sys_path", ["/z", "/z"])),
            ):
                value = json.loads(json.dumps(base))
                mutate(value)
                value["attestation_sha256"] = hashlib.sha256(probe.HASH_DOMAIN + probe.canonical({key: value[key] for key in value if key != "attestation_sha256"})).hexdigest()
                with self.assertRaises(probe.RuntimeProbeError) as error:
                    probe.validate_attestation(probe.canonical(value))
                self.assertEqual(error.exception.code, "attestation-shape", field)

    def test_aggregate_runtime_bound_is_applied_across_closure_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = json.loads(_record(Path(directory)))
            template = dict(value["files"][0])
            value["files"] = [dict(template, path=f"/synthetic/runtime-{index}.py") for index in range(9)]
            for item in value["files"]:
                item["bytes"] = probe.MAX_FILE_BYTES
            value["attestation_sha256"] = hashlib.sha256(probe.HASH_DOMAIN + probe.canonical({key: value[key] for key in value if key != "attestation_sha256"})).hexdigest()
            with self.assertRaises(probe.RuntimeProbeError) as error:
                probe.validate_attestation(probe.canonical(value))
            self.assertEqual(error.exception.code, "runtime-bound")


if __name__ == "__main__":
    unittest.main()

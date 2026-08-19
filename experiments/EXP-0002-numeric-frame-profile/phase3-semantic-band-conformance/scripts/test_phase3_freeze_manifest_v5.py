"""Focused v5 freeze tests using synthetic runtime sidecars only.

These tests do not provision CPython, build Cargo artifacts, or perform an
experiment attempt.  Git ancestry is patched only at the successor seam; the
writer and CLI paths still materialize the canonical manifest bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import phase3_freeze_manifest as freeze
import phase3_python_runtime_probe as probe


V4_COMMIT = "369175137fc42f6cd99d32468ed4a6f10a0d6d59"
MANIFEST_PATH = "experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/manifests/freeze-manifest.json"


def _v4_fixture() -> bytes:
    result = subprocess.run(
        ["git", "-C", str(freeze.REPO), "show", f"{V4_COMMIT}:{MANIFEST_PATH}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise AssertionError("historical v4 fixture unavailable")
    return result.stdout


def _identity(path: Path) -> dict[str, object]:
    info = path.stat()
    return {
        "path": path.as_posix(),
        "mode": stat.S_IMODE(info.st_mode),
        "bytes": info.st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "uid": info.st_uid,
        "gid": info.st_gid,
        "nlink": info.st_nlink,
    }


def _record(root: Path, selector: str, *, interpreter_bytes: bytes = b"python-3.13.15") -> bytes:
    interpreter = root / "opt" / "python3.13"
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_bytes(interpreter_bytes)
    interpreter.chmod(0o755)
    stdlib = root / "opt" / "stdlib.py"
    native = root / "opt" / "_runtime.so"
    stdlib.write_bytes(b"stdlib fixture")
    native.write_bytes(b"native fixture")
    stdlib.chmod(0o644)
    native.chmod(0o644)
    files = sorted((_identity(stdlib), _identity(native)), key=lambda item: str(item["path"]).encode("utf-8"))
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
        "runtime_roots": [(root / "opt").as_posix()],
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


def _attestation_identity(raw: bytes, relative: str, *, attestation_sha256: str | None = None) -> dict[str, object]:
    value = probe.validate_attestation(raw) if attestation_sha256 is None else None
    return {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "attestation_sha256": value["attestation_sha256"] if value is not None else attestation_sha256,
    }


def _contract(root: Path) -> dict:
    """Materialize two synthetic sidecars and return contract-2 mapping."""
    attestations = {}
    for selector in freeze.SELECTORS:
        raw = _record(root / selector, selector=selector)
        relative = freeze.RUNTIME_ATTESTATION_PATHS[selector]
        path = root / "package" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        record = probe.validate_attestation(raw)
        git_path = Path("/usr/bin/git")
        git_bytes = git_path.read_bytes()
        attestations[selector] = {
            "selector": selector,
            "implementation": "CPython",
            "version": "3.13.15",
            "interpreter": record["interpreter"],
            "interpreter_identity": record["interpreter_identity"],
            "invocation": record["invocation"],
            "module_loading": probe.MODULE_LOADING,
            "entrypoint": probe.ENTRYPOINT,
            "attestation_identity": _attestation_identity(raw, relative),
            "external_tools": {
                "git": {
                    "path": git_path.as_posix(),
                    "mode": stat.S_IMODE(git_path.stat().st_mode),
                    "bytes": len(git_bytes),
                    "sha256": hashlib.sha256(git_bytes).hexdigest(),
                }
            },
        }
    return {"schema": freeze.PYTHON_RUNTIME_CONTRACT_V2_SCHEMA, "platforms": attestations}


def _successor(package: Path, root: Path, *, contract: dict | None = None) -> dict:
    predecessor_raw = _v4_fixture()
    predecessor = freeze.validate_manifest(predecessor_raw)
    if contract is None:
        contract = _contract(root)

    def committed(_repo: Path, commit: str, paths: tuple[str, ...]) -> list[dict]:
        if commit == predecessor["execution_tool_source_commit"]:
            for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities", "experiment_closure_tool_identities"):
                if [item["path"] for item in predecessor[field]] == list(paths):
                    return predecessor[field]
        return freeze._tool_identities(package, paths)

    with (
        patch.object(freeze, "_validate_candidate_build_snapshot"),
        patch.object(freeze, "_validate_execution_commit_snapshot"),
        patch.object(freeze, "_assert_descendant_commit"),
        patch.object(freeze, "_execution_tool_identities_from_commit", side_effect=committed),
    ):
        return freeze.build_v5_successor_manifest(
            predecessor_raw,
            execution_tool_source_commit="f" * 40,
            materialization_commit="e" * 40,
            runtime_contract=contract,
            package=package,
        )


class FreezeManifestV5Tests(unittest.TestCase):
    def test_freeze_git_calls_use_absolute_seam_and_closed_reproducible_environment(self) -> None:
        with patch.object(freeze.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "a" * 40
            freeze._git_head(freeze.REPO)
            command = run.call_args.args[0]
            environment = run.call_args.kwargs["env"]
        self.assertEqual(command[0], freeze.GIT_EXECUTABLE)
        self.assertTrue(Path(command[0]).is_absolute())
        self.assertEqual(environment, freeze.GIT_ENV)
        self.assertEqual(environment["LANG"], "C")
        self.assertEqual(environment["LC_ALL"], "C")
        self.assertEqual(environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(environment["GIT_CONFIG_SYSTEM"], "/dev/null")
        self.assertEqual(environment["HOME"], "/nonexistent")
        self.assertEqual(environment["XDG_CONFIG_HOME"], "/nonexistent")
        self.assertEqual(environment["XDG_CACHE_HOME"], "/nonexistent")
        self.assertEqual(environment["GIT_OPTIONAL_LOCKS"], "0")

    def test_candidate_validation_binds_fresh_checker_to_freeze_git_seam(self) -> None:
        observed: dict[str, object] = {}

        class Checker:
            BASE_COMMIT = "a" * 40

            def check(self, _repo: Path, _commit: str) -> None:
                observed["executable"] = self.GIT_EXECUTABLE
                observed["environment"] = self.GIT_ENV

            def select_base_entries(self, _repo: Path, _commit: str) -> list[object]:
                return []

        checker = Checker()
        with patch.object(freeze, "GIT_EXECUTABLE", "/tmp/authenticated-git"):
            loaded, entries = None, None
            with patch.object(freeze, "_load_module", return_value=checker):
                loaded, entries = freeze._candidate_entries(Path("/repo"), Path("/package"))
        self.assertIs(loaded, checker)
        self.assertEqual(entries, [])
        self.assertEqual(observed["executable"], "/tmp/authenticated-git")
        self.assertEqual(observed["environment"], freeze.GIT_ENV)

    def test_receipt_and_its_prebinding_child_receive_freeze_git_seam(self) -> None:
        relative = "scripts/phase3_build_receipt.py"
        manifest = {"provenance_tool_identities": [freeze._file_identity(freeze.PACKAGE, relative)]}
        with patch.object(freeze, "GIT_EXECUTABLE", "/tmp/authenticated-git"):
            receipt = freeze._receipt_module(freeze.PACKAGE, manifest)
            checker = receipt._load_prebinding()
        self.assertEqual(receipt.GIT_EXECUTABLE, "/tmp/authenticated-git")
        self.assertEqual(receipt.GIT_ENV, freeze.GIT_ENV)
        self.assertEqual(checker.GIT_EXECUTABLE, "/tmp/authenticated-git")
        self.assertEqual(checker.GIT_ENV, freeze.GIT_ENV)

    def test_v1_through_v4_bytes_remain_valid_and_current_v4_check_is_execution_disabled(self) -> None:
        historical_v1 = subprocess.run(
            ["git", "-C", str(freeze.REPO), "show", f"553d51bd55dd837b01b950d063d288369f61e56d:{MANIFEST_PATH}"],
            check=False,
            stdout=subprocess.PIPE,
        ).stdout
        historical_v2 = subprocess.run(
            ["git", "-C", str(freeze.REPO), "show", f"cc1531c2e8efe40f8a4896d11b10973147c5636b:{MANIFEST_PATH}"],
            check=False,
            stdout=subprocess.PIPE,
        ).stdout
        historical_v3 = subprocess.run(
            ["git", "-C", str(freeze.REPO), "show", f"e4725412712dab25221949809e7247af9484a4f0:{MANIFEST_PATH}"],
            check=False,
            stdout=subprocess.PIPE,
        ).stdout
        for expected, raw in zip((freeze.V1_SCHEMA, freeze.V2_SCHEMA, freeze.V3_SCHEMA, freeze.V4_SCHEMA), (historical_v1, historical_v2, historical_v3, _v4_fixture())):
            with self.subTest(schema=expected):
                value = freeze.validate_manifest(raw)
                self.assertEqual(value["schema"], expected)
                self.assertEqual(value["manifest_sha256"], freeze._self_hash(value))

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            # The v4 manifest authenticates the v4 receipt validator bytes.
            # Keep this historical check on that exact source after the
            # current validator gains the v5 Git seam.
            historical_receipt = subprocess.run(
                [freeze.GIT_EXECUTABLE, "-C", str(freeze.REPO), "show", f"{V4_COMMIT}:experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/scripts/phase3_build_receipt.py"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=freeze.GIT_ENV,
            )
            self.assertEqual(historical_receipt.returncode, 0)
            (package / "scripts/phase3_build_receipt.py").write_bytes(historical_receipt.stdout)
            manifest_path = package / freeze.MANIFEST_REL
            manifest_path.write_bytes(_v4_fixture())
            manifest_path.chmod(0o644)
            v4 = freeze.validate_manifest(_v4_fixture())

            def identities(_package: Path, paths: tuple[str, ...]) -> list[dict]:
                if paths == freeze.EXPERIMENT_CLOSURE_TOOLS:
                    return v4["experiment_closure_tool_identities"]
                return freeze._tool_identities(_package, paths)

            with (
                patch.object(freeze, "_resolve_source_commit", return_value="a" * 40),
                patch.object(freeze, "_validate_candidate_build_snapshot"),
                patch.object(freeze, "_validate_execution_commit_snapshot"),
                patch.object(freeze, "_validate_current_candidate_build_inputs"),
                patch.object(freeze, "_assert_descendant_commit"),
                patch.object(freeze, "_tool_identities", side_effect=identities),
            ):
                checked = freeze.check_manifest(package=package, path=manifest_path)
            self.assertEqual(checked["schema"], freeze.V4_SCHEMA)
            self.assertFalse(checked["execution_permitted"])

    def test_v5_success_cross_binds_sidecar_bytes_without_reading_absolute_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package"
            shutil.copytree(freeze.PACKAGE, package)
            contract = _contract(root)
            # Leave only sidecar bytes.  Their attested absolute roots and
            # runtime files are deliberately absent from this build host.
            shutil.rmtree(root / "wsl2-x86_64")
            shutil.rmtree(root / "ubuntu-24.04-x86_64")
            successor = _successor(package, root, contract=contract)
        self.assertEqual(successor["schema"], freeze.V5_SCHEMA)
        self.assertEqual(successor["manifest_sha256"], freeze._self_hash(successor))
        self.assertEqual(len(successor["runtime_tool_identities"]), 8)
        self.assertEqual(len(successor["exact_runtime_tool_identities"]), 8)
        self.assertEqual(len(successor["provenance_tool_identities"]), 5)
        self.assertEqual(len(successor["experiment_closure_tool_identities"]), 1)
        self.assertEqual(freeze.validate_manifest(freeze._canonical(successor)), successor)

    def test_v5_rejects_missing_sidecar_and_raw_sidecar_tamper(self) -> None:
        for mutation in ("missing", "raw-tamper"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package = root / "package"
                shutil.copytree(freeze.PACKAGE, package)
                contract = _contract(root)
                sidecar = package / freeze.RUNTIME_ATTESTATION_PATHS["ubuntu-24.04-x86_64"]
                if mutation == "missing":
                    sidecar.unlink()
                else:
                    sidecar.write_bytes(sidecar.read_bytes() + b" ")
                with self.subTest(mutation=mutation), self.assertRaises(freeze.FreezeManifestError) as error:
                    _successor(package, root, contract=contract)
                self.assertEqual(error.exception.code, "runtime-attestation")

    def test_v5_rejects_attestation_self_hash_and_selector_mismatch(self) -> None:
        for mutation in ("self-hash", "selector"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package = root / "package"
                shutil.copytree(freeze.PACKAGE, package)
                contract = _contract(root)
                selector = "wsl2-x86_64"
                sidecar = package / freeze.RUNTIME_ATTESTATION_PATHS[selector]
                value = json.loads(sidecar.read_text(encoding="utf-8"))
                if mutation == "self-hash":
                    value["attestation_sha256"] = "0" * 64
                    expected_hash = value["attestation_sha256"]
                else:
                    value["selector"] = "ubuntu-24.04-x86_64"
                    unsigned = {key: value[key] for key in value if key != "attestation_sha256"}
                    expected_hash = hashlib.sha256(probe.HASH_DOMAIN + probe.canonical(unsigned)).hexdigest()
                    value["attestation_sha256"] = expected_hash
                raw = probe.canonical(value)
                sidecar.write_bytes(raw)
                contract["platforms"][selector]["attestation_identity"] = _attestation_identity(raw, freeze.RUNTIME_ATTESTATION_PATHS[selector], attestation_sha256=expected_hash)
                with self.subTest(mutation=mutation), self.assertRaises(freeze.FreezeManifestError) as error:
                    _successor(package, root, contract=contract)
                self.assertEqual(error.exception.code, "runtime-attestation")

    def test_v5_rejects_full_interpreter_identity_mismatch_and_same_version_different_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package"
            shutil.copytree(freeze.PACKAGE, package)
            contract = _contract(root)
            selector = "wsl2-x86_64"
            original = contract["platforms"][selector]["interpreter_identity"]
            forged = dict(original)
            forged["sha256"] = "0" * 64
            contract["platforms"][selector]["interpreter_identity"] = forged
            with self.assertRaises(freeze.FreezeManifestError) as error:
                _successor(package, root, contract=contract)
            self.assertEqual(error.exception.code, "runtime-attestation")

            # The version remains 3.13.15, but this is a different executable
            # identity.  The sidecar still records the original executable,
            # so path/version-only binding would incorrectly accept it.
            second_root = root / "second"
            second_raw = _record(second_root, selector=selector, interpreter_bytes=b"different-python-3.13.15")
            second_value = probe.validate_attestation(second_raw)
            contract = _contract(root)
            contract["platforms"][selector]["interpreter"] = second_value["interpreter"]
            contract["platforms"][selector]["interpreter_identity"] = second_value["interpreter_identity"]
            contract["platforms"][selector]["invocation"] = second_value["invocation"]
            with self.assertRaises(freeze.FreezeManifestError) as error:
                _successor(package, root, contract=contract)
            self.assertEqual(error.exception.code, "runtime-attestation")

    def test_v5_writer_and_cli_materialize_canonical_successor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package"
            shutil.copytree(freeze.PACKAGE, package)
            manifest_path = package / freeze.MANIFEST_REL
            manifest_path.write_bytes(_v4_fixture())
            manifest_path.chmod(0o644)
            contract = _contract(root)
            contract_path = root / "runtime-contract.json"
            contract_path.write_bytes(freeze._canonical(contract))
            predecessor = freeze.validate_manifest(_v4_fixture())

            def committed(_repo: Path, commit: str, paths: tuple[str, ...]) -> list[dict]:
                if commit == predecessor["execution_tool_source_commit"]:
                    for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities", "experiment_closure_tool_identities"):
                        if [item["path"] for item in predecessor[field]] == list(paths):
                            return predecessor[field]
                return freeze._tool_identities(package, paths)

            with (
                patch.object(freeze, "_validate_candidate_build_snapshot"),
                patch.object(freeze, "_validate_execution_commit_snapshot"),
                patch.object(freeze, "_assert_descendant_commit"),
                patch.object(freeze, "_execution_tool_identities_from_commit", side_effect=committed),
            ):
                result = freeze.main([
                    "--repo", str(freeze.REPO), "--package", str(package), "--manifest", str(manifest_path),
                    "--successor-v5", "f" * 40, "e" * 40, str(contract_path),
                ])
            self.assertEqual(result, 0)
            written = freeze.validate_manifest(manifest_path.read_bytes())
            self.assertEqual(written["schema"], freeze.V5_SCHEMA)
            self.assertEqual(written["manifest_sha256"], freeze._self_hash(written))

    def test_v5_rejects_non_exact_v4_predecessor(self) -> None:
        with self.assertRaises(freeze.FreezeManifestError) as error:
            freeze.build_v5_successor_manifest(
                _v4_fixture().replace(b"freeze-manifest-4", b"freeze-manifest-3"),
                execution_tool_source_commit="f" * 40,
                materialization_commit="e" * 40,
                runtime_contract={},
            )
        self.assertIn(error.exception.code, {"manifest-shape", "predecessor-manifest"})

    def test_v5_extra_file_policy_allows_only_the_two_canonical_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package"
            shutil.copytree(freeze.PACKAGE, package)
            _contract(root)
            self.assertEqual(freeze._package_extra_files(package), sorted(freeze.RUNTIME_ATTESTATION_PATHS.values()))
            self.assertEqual(freeze._package_extra_files(package, allow_v5_runtime_attestations=True), [])
            extra = package / "manifests" / "runtime-attestations" / "extra.json"
            extra.write_bytes(b"{}\n")
            self.assertIn(extra.relative_to(package).as_posix(), freeze._package_extra_files(package, allow_v5_runtime_attestations=True))


if __name__ == "__main__":
    unittest.main()

"""Focused non-executing tests for the Phase 3 freeze manifest."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import phase3_build_receipt as build_receipt
import phase3_freeze_manifest as freeze


BUNDLE_FILES = ("candidate", "build-receipt.json", "build-metadata.json", "cargo-metadata.json")
HISTORICAL_V1_COMMIT = "553d51bd55dd837b01b950d063d288369f61e56d"
HISTORICAL_V2_COMMIT = "cc1531c2e8efe40f8a4896d11b10973147c5636b"
HISTORICAL_V3_COMMIT = "e4725412712dab25221949809e7247af9484a4f0"
MANIFEST_REPOSITORY_PATH = "experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance/manifests/freeze-manifest.json"


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _historical_manifest_bytes(commit: str) -> bytes:
    """Read a pinned historical manifest, never the package's current successor."""
    result = subprocess.run(
        ["git", "-C", str(freeze.REPO), "show", f"{commit}:{MANIFEST_REPOSITORY_PATH}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 or not result.stdout.endswith(b"\n"):
        raise AssertionError(f"historical manifest fixture unavailable: {commit}")
    return result.stdout


def _v1_fixture() -> bytes:
    return _historical_manifest_bytes(HISTORICAL_V1_COMMIT)


def _v2_fixture() -> bytes:
    return _historical_manifest_bytes(HISTORICAL_V2_COMMIT)


def _v3_fixture() -> bytes:
    return _historical_manifest_bytes(HISTORICAL_V3_COMMIT)


def _copy_package(root: Path) -> tuple[Path, Path]:
    package = root / "phase3-package"
    shutil.copytree(freeze.PACKAGE, package)
    receipts = package / freeze.RECEIPT_DIR_REL
    if receipts.exists():
        shutil.rmtree(receipts)
    receipts.mkdir(parents=True)
    manifest_path = package / freeze.MANIFEST_REL
    manifest_path.write_bytes(_canonical(freeze.generate_manifest(package=package)))
    manifest_path.chmod(0o644)
    return package, manifest_path


def _receipt_raw(manifest: dict, role: str, *, source_commit: str | None = None, dependency_suffix: str = "b", dependency_raw_suffix: str = "c", dependency_bytes: int = 1) -> bytes:
    if source_commit is None:
        source_commit = manifest["candidate_source_commit"]
    selector = "wsl2-x86_64" if role == "wsl" else "ubuntu-24.04-x86_64"
    target_dir = "/tmp/ck-phase3-test-target-" + role
    artifact = manifest["build"]["recipe"]["artifact_build"]
    build = {
        "platform_role": role,
        "platform_observation": {"stability": "observed-for-this-build-only", "runner_os": "Linux", "runner_arch": "X64", "image_os": "Ubuntu", "image_version": "fixture", "kernel": "Linux fixture", "sanitized_environment_keys": sorted(freeze.ENV_POLICY["variables"])},
        "target": freeze.TARGET,
        "profile": "dev",
        "argv": ["cargo", "+1.97.1", "build", "--manifest-path", freeze.CANDIDATE_MANIFEST_REL, "--target", freeze.TARGET, "--target-dir", target_dir, "--locked", "--offline"],
        "cwd": ".",
        "env_policy": freeze.ENV_POLICY,
        "toolchain": {"rust_toolchain": "1.97.1", "rustc": "rustc 1.97.1 (fixture)\ncommit-hash: 8bab26f4f68e0e26f0bb7960be334d5b520ea452\nhost: x86_64-unknown-linux-gnu\nLLVM version: 22.1.6", "cargo": "cargo 1.97.1 (fixture)\ncommit-hash: c980f4866141969fab6254a680546a277789d6f0\nhost: x86_64-unknown-linux-gnu", "python": "Python 3.10 (fixture)"},
        "cargo_lock": {key: manifest["build"]["dependencies"]["cargo_lock"][key] for key in ("path", "sha256", "bytes")},
        "dependency_closure": {"schema": "ck.exp-0002.phase3.gate-b-cargo-metadata-1", "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1", "sha256": dependency_suffix * 64, "raw_sha256": dependency_raw_suffix * 64, "bytes": dependency_bytes, "packages": 2, "nodes": 2},
        "vendor_closure": {"role_path": f"phase3-gate-b-{role}-vendor", "algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1", "files": 1, "bytes": 1, "path_sha256": "d" * 64, "content_sha256": "e" * 64},
        "cargo_config": {"role_path": f"phase3-gate-b-{role}-cargo-config", "algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1", "sha256": "a" * 64, "bytes": 1},
        "binary_role_path": artifact["binary_role_path_pattern"].format(platform_role=role, target=freeze.TARGET),
    }
    closure = manifest["candidate_closure"]
    binary_path = build["binary_role_path"]
    return build_receipt.build_receipt(
        source_commit=source_commit,
        source_closure={"algorithm": closure["algorithm"], "base_commit": closure["base_commit"], "files": closure["count"], "bytes": closure["total_raw_bytes"], "path_sha256": closure["path_set_sha256"], "content_sha256": closure["content_sha256"]},
        build=build,
        binary={"role": "phase3-candidate", "path": binary_path, "sha256": "f" * 64, "bytes": 17, "mode": "0755", "elf": {"class": "ELF64", "data": "little-endian", "machine": "x86_64", "type": "ET_DYN", "osabi": 0, "entry_point": "0x0000000000000000"}},
    )


def _portable_checksum_paths(raw: str) -> list[str]:
    paths: list[str] = []
    for line in raw.splitlines():
        try:
            digest, path = line.split("  ", 1)
        except ValueError as error:
            raise ValueError("checksum manifest line is malformed") from error
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checksum manifest digest is malformed")
        if not path or path.startswith("/") or "/" in path or path in paths:
            raise ValueError("checksum manifest path is not a unique basename")
        paths.append(path)
    return paths


def _successor(package: Path, execution_commit: str = "e" * 40) -> dict:
    predecessor_raw = _v1_fixture()

    def committed(_repo: Path, _commit: str, paths: tuple[str, ...]) -> list[dict]:
        return freeze._tool_identities(package, paths)

    with (
        patch.object(freeze, "_validate_candidate_commit_snapshot"),
        patch.object(freeze, "_validate_candidate_build_snapshot"),
        patch.object(freeze, "_assert_descendant_commit"),
        patch.object(freeze, "_execution_tool_identities_from_commit", side_effect=committed),
    ):
        return freeze.build_successor_manifest(
            predecessor_raw,
            execution_tool_source_commit=execution_commit,
            package=package,
        )


def _v3_successor(package: Path, execution_commit: str = "a" * 40, materialization_commit: str = "b" * 40) -> dict:
    # The package copy contains the current v3 successor.  A v3 builder must
    # be tested against the immutable historical v2 predecessor instead of
    # accidentally feeding it its own successor.
    predecessor_raw = _v2_fixture()
    predecessor = freeze.validate_manifest(predecessor_raw)

    def committed(_repo: Path, _commit: str, paths: tuple[str, ...]) -> list[dict]:
        if _commit == freeze.EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT:
            for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
                if [item["path"] for item in predecessor[field]] == list(paths):
                    return predecessor[field]
        return freeze._tool_identities(package, paths)

    with (
        patch.object(freeze, "_validate_candidate_build_snapshot"),
        patch.object(freeze, "_validate_execution_commit_snapshot"),
        patch.object(freeze, "_assert_descendant_commit"),
        patch.object(freeze, "_execution_tool_identities_from_commit", side_effect=committed),
    ):
        return freeze.build_v3_successor_manifest(
            predecessor_raw,
            execution_tool_source_commit=execution_commit,
            materialization_commit=materialization_commit,
            package=package,
        )


def _runtime_contract(native_python_version: str = "3.13.15") -> dict:
    """Synthetic future-workflow fixture; no host runtime is consulted."""
    return {
        "schema": freeze.PYTHON_RUNTIME_CONTRACT_SCHEMA,
        "platforms": {
            selector: {
                "selector": selector,
                "implementation": "CPython",
                "version": freeze.PYTHON_RUNTIME_VERSION,
                "invocation": list(freeze.PYTHON_RUNTIME_INVOCATION),
                "module_loading": freeze.PYTHON_RUNTIME_MODULE_LOADING,
                "entrypoint": freeze.PYTHON_RUNTIME_ENTRYPOINT,
            }
            for selector in freeze.SELECTORS
        },
    }


def _v4_successor(package: Path, execution_commit: str = "c" * 40, materialization_commit: str = "d" * 40, runtime_contract: dict | None = None) -> dict:
    predecessor_raw = _v3_fixture()
    predecessor = freeze.validate_manifest(predecessor_raw)

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
        return freeze.build_v4_successor_manifest(
            predecessor_raw,
            execution_tool_source_commit=execution_commit,
            materialization_commit=materialization_commit,
            runtime_contract=_runtime_contract() if runtime_contract is None else runtime_contract,
            package=package,
        )


def _unbound_historical_manifest() -> dict:
    # Keep low-level atomic-write tests on the immutable v1 shape.  The
    # package's checked-in manifest is the current v2 successor and must not
    # be used as a predecessor fixture.
    value = freeze.validate_manifest(_v1_fixture())
    value["binaries"] = freeze._binary_slots()
    value["readiness"] = freeze._readiness(value["binaries"])
    return freeze._seal(value)


class FreezeManifestTests(unittest.TestCase):
    def test_v3_successor_preserves_exact_v1_v2_history_and_closure_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            successor = _v3_successor(package)
        self.assertEqual(successor["schema"], freeze.V3_SCHEMA)
        self.assertEqual(successor["predecessor_manifest_sha256"], freeze.EXPECTED_V2_MANIFEST_SHA256)
        self.assertEqual(successor["predecessor_v1_manifest_sha256"], freeze.EXPECTED_V1_MANIFEST_SHA256)
        self.assertEqual(successor["previous_execution_tool_source_commit"], freeze.EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT)
        self.assertEqual(successor["experiment_closure_schema"], "ck.exp-0002.phase3.experiment-closure-1")
        self.assertEqual(freeze.validate_manifest(_canonical(successor)), successor)

    def test_v3_requires_exact_v2_predecessor_and_distinct_materialization(self) -> None:
        with self.assertRaises(freeze.FreezeManifestError) as error:
            freeze.build_v3_successor_manifest(b"{}\n", execution_tool_source_commit="a" * 40, materialization_commit="b" * 40)
        self.assertEqual(error.exception.code, "manifest-shape")
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                _v3_successor(package, materialization_commit=freeze.EXPECTED_V2_MATERIALIZATION_COMMIT)
        self.assertEqual(error.exception.code, "materialization-commit")

    def test_v4_successor_preserves_v3_history_and_binds_both_python_runtimes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            successor = _v4_successor(package)
        self.assertEqual(successor["schema"], freeze.V4_SCHEMA)
        self.assertEqual(successor["predecessor_manifest_sha256"], freeze.EXPECTED_V3_MANIFEST_SHA256)
        self.assertEqual(successor["predecessor_v1_manifest_sha256"], freeze.EXPECTED_V1_MANIFEST_SHA256)
        self.assertEqual(successor["predecessor_v2_manifest_sha256"], freeze.EXPECTED_V2_MANIFEST_SHA256)
        self.assertEqual(successor["predecessor_v2_inherited_sha256"], freeze.EXPECTED_INHERITED_V1_SHA256)
        self.assertEqual(successor["predecessor_v2_execution_tool_source_commit"], freeze.EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT)
        self.assertEqual(successor["predecessor_v2_materialization_commit"], freeze.EXPECTED_V2_MATERIALIZATION_COMMIT)
        self.assertEqual(successor["previous_execution_tool_source_commit"], freeze.EXPECTED_V3_EXECUTION_TOOL_SOURCE_COMMIT)
        self.assertEqual(successor["old_materialization_commit"], freeze.EXPECTED_V3_MATERIALIZATION_COMMIT)
        contract = successor["exact_python_runtime_contract"]
        self.assertEqual(contract["schema"], freeze.PYTHON_RUNTIME_CONTRACT_SCHEMA)
        self.assertEqual(set(contract["platforms"]), set(freeze.SELECTORS))
        self.assertEqual(contract["platforms"]["wsl2-x86_64"]["version"], "3.13.15")
        self.assertEqual(contract["platforms"]["ubuntu-24.04-x86_64"]["version"], "3.13.15")
        self.assertEqual(freeze.validate_manifest(_canonical(successor)), successor)

    def test_v4_requires_an_authoritative_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.build_v4_successor_manifest(
                    _v3_fixture(),
                    execution_tool_source_commit="c" * 40,
                    materialization_commit="d" * 40,
                    package=package,
                )
        self.assertEqual(error.exception.code, "runtime-contract")

    def test_v4_rejects_non_exact_v3_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.build_v4_successor_manifest(
                    _v2_fixture(),
                    execution_tool_source_commit="c" * 40,
                    materialization_commit="d" * 40,
                    runtime_contract=_runtime_contract(),
                    package=package,
                )
        self.assertEqual(error.exception.code, "predecessor-manifest")

    def test_v4_runtime_selector_version_invocation_and_entrypoint_tamper_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            successor = _v4_successor(package)
        mutations = {
            "selector": lambda value: value["exact_python_runtime_contract"]["platforms"]["wsl2-x86_64"].__setitem__("selector", "ubuntu-24.04-x86_64"),
            "version": lambda value: value["exact_python_runtime_contract"]["platforms"]["ubuntu-24.04-x86_64"].__setitem__("version", "3.13"),
            "invocation": lambda value: value["exact_python_runtime_contract"]["platforms"]["wsl2-x86_64"].__setitem__("invocation", ["python3", "-m", "phase3_exact_attempt"]),
            "module_loading": lambda value: value["exact_python_runtime_contract"]["platforms"]["wsl2-x86_64"].__setitem__("module_loading", "ambient-import"),
            "entrypoint": lambda value: value["exact_python_runtime_contract"]["platforms"]["wsl2-x86_64"].__setitem__("entrypoint", "phase3_exact_attempt.run"),
        }
        for label, mutate in mutations.items():
            forged = json.loads(_canonical(successor))
            mutate(forged)
            forged["manifest_sha256"] = freeze._self_hash(forged)
            with self.subTest(label=label), self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.validate_manifest(_canonical(forged))
            self.assertEqual(error.exception.code, "manifest-shape")

    def test_historical_v1_bytes_remain_valid_and_current_check_requires_v2(self) -> None:
        raw = _v1_fixture()
        historical = freeze.validate_manifest(raw)
        self.assertEqual(historical["schema"], freeze.V1_SCHEMA)
        self.assertEqual(historical["manifest_sha256"], freeze._self_hash(historical))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            path.write_bytes(raw)
            path.chmod(0o644)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.check_manifest(path=path)
        self.assertEqual(error.exception.code, "current-schema")
        self.assertEqual(freeze.validate_manifest(_v2_fixture())["schema"], freeze.V2_SCHEMA)

    def test_successor_preserves_v1_facts_and_binds_disjoint_tool_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            predecessor = freeze.validate_manifest(_v1_fixture())
            successor = _successor(package)
        self.assertEqual(successor["schema"], freeze.SCHEMA)
        self.assertEqual(successor["predecessor_manifest_sha256"], predecessor["manifest_sha256"])
        self.assertEqual(successor["candidate_source_commit"], freeze.EXPECTED_CANDIDATE_SOURCE_COMMIT)
        self.assertEqual(successor["execution_tool_source_commit"], "e" * 40)
        self.assertEqual(successor["predecessor_inherited_sha256"], freeze.EXPECTED_INHERITED_V1_SHA256)
        self.assertEqual(freeze._inherited_v1_hash(predecessor), freeze.EXPECTED_INHERITED_V1_SHA256)
        for field in freeze.INHERITED_SUCCESSOR_FIELDS:
            self.assertEqual(successor[field], predecessor[field], field)
        self.assertEqual([item["path"] for item in successor["runtime_tool_identities"]], list(freeze.RUNTIME_TOOLS))
        self.assertEqual([item["path"] for item in successor["exact_runtime_tool_identities"]], list(freeze.LEGACY_EXACT_RUNTIME_TOOLS))
        self.assertEqual([item["path"] for item in successor["provenance_tool_identities"]], list(freeze.PROVENANCE_TOOLS))
        paths = [item["path"] for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities") for item in successor[field]]
        self.assertEqual(len(paths), 19)
        self.assertEqual(len(set(paths)), 19)
        self.assertEqual(freeze.validate_manifest(_canonical(successor)), successor)

    def test_pure_successor_rejects_resealed_inherited_fact_substitutions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            successor = _successor(package)
        mutations = {
            "candidate-closure": lambda value: value["candidate_closure"]["entries"][0].__setitem__("sha256", "0" * 64),
            "raw-input": lambda value: value["raw_inputs"][0].__setitem__("sha256", "0" * 64),
            "binary": lambda value: value["binaries"]["wsl2-x86_64"]["binary_identity"].__setitem__("sha256", "0" * 64),
            "receipt": lambda value: value["binaries"]["wsl2-x86_64"].__setitem__("receipt_sha256", "0" * 64),
        }
        for label, mutate in mutations.items():
            forged = json.loads(_canonical(successor))
            mutate(forged)
            forged["manifest_sha256"] = freeze._self_hash(forged)
            with self.subTest(label=label), self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.validate_manifest(_canonical(forged))
            self.assertEqual(error.exception.code, "manifest-shape")

    def test_successor_rejects_a_validly_resealed_v1_substitute(self) -> None:
        predecessor = freeze.validate_manifest(_v1_fixture())
        forged = json.loads(_canonical(predecessor))
        forged["runtime_tool_identities"][0]["sha256"] = "0" * 64
        forged["manifest_sha256"] = freeze._self_hash(forged)
        self.assertEqual(freeze.validate_manifest(_canonical(forged)), forged)
        with self.assertRaises(freeze.FreezeManifestError) as error:
            freeze.build_successor_manifest(
                _canonical(forged),
                execution_tool_source_commit="e" * 40,
            )
        self.assertEqual(error.exception.code, "predecessor-manifest")

    def test_execution_tool_commit_must_descend_from_candidate_commit(self) -> None:
        with patch.object(freeze.subprocess, "run") as run:
            run.return_value.returncode = 0
            freeze._assert_descendant_commit(freeze.REPO, "a" * 40, "b" * 40)
            run.return_value.returncode = 1
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze._assert_descendant_commit(freeze.REPO, "a" * 40, "b" * 40)
        self.assertEqual(error.exception.code, "execution-tool-commit")

    def test_successor_tool_contract_is_closed_and_current_check_cross_binds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            successor = _successor(package)
            manifest_path = package / freeze.MANIFEST_REL
            manifest_path.write_bytes(_canonical(successor))
            manifest_path.chmod(0o644)
            with (
                patch.object(freeze, "_resolve_source_commit", return_value="f" * 40),
                patch.object(freeze, "_validate_candidate_build_snapshot"),
                patch.object(freeze, "_validate_execution_commit_snapshot"),
                patch.object(freeze, "_validate_current_candidate_build_inputs"),
            ):
                self.assertEqual(freeze.check_manifest(package=package, path=manifest_path), successor)
            forged = json.loads(_canonical(successor))
            forged["exact_runtime_tool_identities"][0]["path"] = "scripts/not-closed.py"
            forged["manifest_sha256"] = freeze._self_hash(forged)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.validate_manifest(_canonical(forged))
            self.assertEqual(error.exception.code, "manifest-shape")

    def test_successor_writer_replaces_exact_v1_once_and_refuses_v2_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            manifest_path = package / freeze.MANIFEST_REL
            manifest_path.write_bytes(_v1_fixture())
            manifest_path.chmod(0o644)

            def committed(_repo: Path, _commit: str, paths: tuple[str, ...]) -> list[dict]:
                return freeze._tool_identities(package, paths)

            with (
                patch.object(freeze, "_validate_candidate_commit_snapshot"),
                patch.object(freeze, "_validate_candidate_build_snapshot"),
                patch.object(freeze, "_assert_descendant_commit"),
                patch.object(freeze, "_execution_tool_identities_from_commit", side_effect=committed),
            ):
                written = freeze.write_successor_manifest(manifest_path, "e" * 40, package=package)
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.write_successor_manifest(manifest_path, "e" * 40, package=package)
            self.assertEqual(error.exception.code, "manifest-finalized")
            self.assertEqual(freeze.validate_manifest(manifest_path.read_bytes()), written)

    def test_successor_exchange_detects_and_restores_last_moment_destination_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            manifest_path = package / freeze.MANIFEST_REL
            manifest_path.write_bytes(_v1_fixture())
            manifest_path.chmod(0o644)
            predecessor_snapshot = freeze._read_manifest_snapshot(manifest_path)
            successor = _successor(package)
            decoy = b'{"decoy":true}\n'
            exchange = freeze._rename_exchange
            calls = 0

            def replace_then_exchange(first: Path, second: Path) -> None:
                nonlocal calls
                if calls == 0:
                    decoy_path = second.parent / "last-moment-decoy.json"
                    decoy_path.write_bytes(decoy)
                    decoy_path.chmod(0o644)
                    os.replace(decoy_path, second)
                calls += 1
                exchange(first, second)

            with patch.object(freeze, "_rename_exchange", side_effect=replace_then_exchange):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze._atomic_write_manifest(
                        successor,
                        manifest_path,
                        expected_destination_snapshot=predecessor_snapshot,
                    )
            self.assertEqual(error.exception.code, "manifest-write")
            self.assertEqual(calls, 2)
            self.assertEqual(manifest_path.read_bytes(), decoy)
            self.assertEqual(list(manifest_path.parent.glob(f".{manifest_path.name}.*.tmp")), [])

    def test_initial_creation_never_replaces_a_last_moment_entry(self) -> None:
        manifest = _unbound_historical_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            decoy = b'{"appeared":true}\n'
            rename_noreplace = freeze._rename_noreplace

            def appear_then_publish(first: Path, second: Path) -> None:
                second.write_bytes(decoy)
                second.chmod(0o644)
                rename_noreplace(first, second)

            with patch.object(freeze, "_rename_noreplace", side_effect=appear_then_publish):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze._atomic_write_manifest(manifest, path)
            self.assertEqual(error.exception.code, "manifest-write")
            self.assertEqual(path.read_bytes(), decoy)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_unbound_exchange_detects_and_restores_last_moment_destination_replacement(self) -> None:
        manifest = _unbound_historical_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            path.write_bytes(_canonical(manifest))
            path.chmod(0o644)
            decoy = b'{"replacement":true}\n'
            exchange = freeze._rename_exchange
            calls = 0

            def replace_then_exchange(first: Path, second: Path) -> None:
                nonlocal calls
                if calls == 0:
                    decoy_path = second.parent / "unbound-decoy.json"
                    decoy_path.write_bytes(decoy)
                    decoy_path.chmod(0o644)
                    os.replace(decoy_path, second)
                calls += 1
                exchange(first, second)

            with patch.object(freeze, "_rename_exchange", side_effect=replace_then_exchange):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze._atomic_write_manifest(manifest, path)
            self.assertEqual(error.exception.code, "manifest-write")
            self.assertEqual(calls, 2)
            self.assertEqual(path.read_bytes(), decoy)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_finalization_rejects_a_valid_snapshot_substitution_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            path = package / freeze.MANIFEST_REL
            baseline = _unbound_historical_manifest()
            path.write_bytes(_canonical(baseline))
            path.chmod(0o644)
            decoy = json.loads(_canonical(baseline))
            decoy["raw_inputs"][0]["sha256"] = "0" * 64
            decoy["manifest_sha256"] = freeze._self_hash(decoy)
            decoy_raw = _canonical(decoy)

            def generated(
                _repo: Path = freeze.REPO,
                _package: Path = package,
                *,
                binaries: dict | None = None,
                source_commit: str | None = None,
            ) -> dict:
                value = json.loads(_canonical(baseline))
                value["candidate_source_commit"] = source_commit
                value["binaries"] = freeze._binary_slots(binaries)
                value["readiness"] = freeze._readiness(value["binaries"])
                return freeze._seal(value)

            atomic_write = freeze._atomic_write_manifest

            def substitute_then_publish(value: dict, destination: Path, **kwargs: object) -> None:
                decoy_path = destination.parent / "finalize-decoy.json"
                decoy_path.write_bytes(decoy_raw)
                decoy_path.chmod(0o644)
                os.replace(decoy_path, destination)
                atomic_write(value, destination, **kwargs)

            receipts = [
                package / freeze.RECEIPT_PATHS["wsl2-x86_64"],
                package / freeze.RECEIPT_PATHS["ubuntu-24.04-x86_64"],
            ]
            with (
                patch.object(freeze, "_resolve_source_commit", return_value="f" * 40),
                patch.object(freeze, "_validate_candidate_commit_snapshot"),
                patch.object(freeze, "generate_manifest", side_effect=generated),
                patch.object(freeze, "_atomic_write_manifest", side_effect=substitute_then_publish),
            ):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.finalize_from_receipts(path, receipts, package=package)
            self.assertEqual(error.exception.code, "manifest-write")
            self.assertEqual(path.read_bytes(), decoy_raw)

    def test_initial_creation_reports_success_when_visible_entry_directory_sync_is_unavailable(self) -> None:
        manifest = _unbound_historical_manifest()
        for failure in ("directory-open", "directory-fsync"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "freeze-manifest.json"
                with patch.object(
                    freeze,
                    "_fsync_directory",
                    side_effect=freeze.FreezeManifestError("manifest-write", failure),
                ):
                    freeze._atomic_write_manifest(manifest, path)
                self.assertEqual(path.read_bytes(), _canonical(manifest))
                self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_replacement_directory_sync_failure_restores_exact_old_manifest(self) -> None:
        old = _unbound_historical_manifest()
        new = json.loads(_canonical(old))
        new["raw_inputs"][0]["sha256"] = "0" * 64
        new["manifest_sha256"] = freeze._self_hash(new)
        for failure in ("directory-open", "directory-fsync"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "freeze-manifest.json"
                old_raw = _canonical(old)
                path.write_bytes(old_raw)
                path.chmod(0o644)
                with patch.object(
                    freeze,
                    "_fsync_directory",
                    side_effect=[freeze.FreezeManifestError("manifest-write", failure), None],
                ):
                    with self.assertRaises(freeze.FreezeManifestError) as error:
                        freeze._atomic_write_manifest(new, path)
                self.assertEqual(error.exception.code, "manifest-write")
                self.assertEqual(path.read_bytes(), old_raw)
                self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_generation_is_deterministic_and_unbound_is_truthful(self) -> None:
        first = freeze.generate_manifest()
        second = freeze.generate_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["manifest_sha256"], freeze._self_hash(first))
        self.assertTrue(freeze._valid_commit(first["candidate_source_commit"]))
        self.assertEqual(first["binding"]["phase_id"], freeze.PHASE_ID)
        self.assertEqual(first["candidate_closure"]["count"], 47)
        self.assertEqual(first["candidate_closure"]["total_raw_bytes"], 1_494_337)
        self.assertEqual(len(first["candidate_closure"]["entries"]), 47)
        self.assertEqual(len(first["runtime_tool_identities"]), 8)
        self.assertEqual(len(first["provenance_tool_identities"]), 4)
        self.assertEqual([item["path"] for item in first["provenance_tool_identities"]], list(freeze.PROVENANCE_TOOLS))
        self.assertEqual(set(first["binaries"]), set(freeze.SELECTORS))
        self.assertTrue(all(slot["status"] == "unbound" for slot in first["binaries"].values()))
        self.assertNotIn("gate_b_ready", first["readiness"])
        self.assertNotIn("gate_b_review_status", first["readiness"])
        self.assertIn("freeze_blockers", first["readiness"])
        self.assertFalse(first["readiness"]["execution_permitted"])

    def test_candidate_path_identity_is_independently_recomputed(self) -> None:
        manifest = freeze.generate_manifest()
        path_stream = bytearray(b"ck.phase3-candidate-source-build-path-set.v1\0")
        content_stream = bytearray(b"ck.phase3-candidate-source-build-content.v1\0")
        for item in manifest["candidate_closure"]["entries"]:
            raw = (freeze.REPO / item["path"]).read_bytes()
            self.assertEqual(item["bytes"], len(raw))
            self.assertEqual(item["sha256"], hashlib.sha256(raw).hexdigest())
            encoded = item["path"].encode()
            path_stream += struct.pack(">I", len(encoded)) + encoded + struct.pack(">I", item["mode"])
            content_stream += struct.pack(">I", len(encoded)) + encoded + struct.pack(">I", item["mode"]) + struct.pack(">Q", len(raw)) + raw
        self.assertEqual(hashlib.sha256(path_stream).hexdigest(), manifest["candidate_closure"]["path_set_sha256"])
        self.assertEqual(hashlib.sha256(content_stream).hexdigest(), manifest["candidate_closure"]["content_sha256"])

    def test_check_rejects_self_hash_and_validly_sealed_drift(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            path.write_bytes(_canonical(manifest))
            tampered = dict(manifest)
            tampered["manifest_sha256"] = "0" * 64
            path.write_bytes(_canonical(tampered))
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.check_historical_manifest(path=path)
            self.assertEqual(error.exception.code, "manifest-self-hash")
            tampered = json.loads(_canonical(manifest))
            tampered["raw_inputs"][0]["sha256"] = "0" * 64
            tampered["manifest_sha256"] = freeze._self_hash(tampered)
            path.write_bytes(_canonical(tampered))
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.check_historical_manifest(path=path)
            self.assertIn(error.exception.code, {"manifest-drift", "source-commit"})

    def test_check_rejects_source_commit_mismatch(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            tampered = dict(manifest)
            tampered["candidate_source_commit"] = "a" * 40
            tampered["manifest_sha256"] = freeze._self_hash(tampered)
            path.write_bytes(_canonical(tampered))
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.check_historical_manifest(path=path)
            self.assertEqual(error.exception.code, "source-commit")

    def test_candidate_commit_blob_drift_is_rejected(self) -> None:
        identity = freeze._file_identity(freeze.REPO, "rust-toolchain.toml")
        freeze._assert_git_identity(freeze.REPO, freeze._git_head(freeze.REPO), "rust-toolchain.toml", identity)
        tampered = dict(identity, sha256="0" * 64)
        with self.assertRaises(freeze.FreezeManifestError) as error:
            freeze._assert_git_identity(freeze.REPO, freeze._git_head(freeze.REPO), "rust-toolchain.toml", tampered)
        self.assertEqual(error.exception.code, "source-commit")

    def test_later_freeze_head_does_not_replace_candidate_commit(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            path.write_bytes(_canonical(manifest))
            with patch.object(freeze, "_validate_candidate_commit_snapshot"), patch.object(freeze, "_git_head", return_value="b" * 40):
                self.assertEqual(freeze.check_historical_manifest(path=path)["candidate_source_commit"], manifest["candidate_source_commit"])

    def test_workflow_identity_is_bound_and_drift_is_rejected(self) -> None:
        manifest = freeze.generate_manifest()
        workflow = manifest["repository_inputs"]["native_build_workflow"]
        self.assertEqual(workflow["path"], freeze.WORKFLOW_REL)
        self.assertEqual(workflow["runner_label"], "ubuntu-24.04")
        self.assertTrue(workflow["pinned_action_refs"])
        self.assertTrue(all("@" in reference and freeze.ACTION_SHA_RE.fullmatch(reference.rsplit("@", 1)[1]) for reference in workflow["pinned_action_refs"]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            tampered = json.loads(_canonical(manifest))
            tampered["repository_inputs"]["native_build_workflow"]["identity"]["sha256"] = "0" * 64
            tampered["manifest_sha256"] = freeze._self_hash(tampered)
            path.write_bytes(_canonical(tampered))
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.check_historical_manifest(path=path)
            self.assertIn(error.exception.code, {"manifest-drift", "source-commit"})

    def test_pure_validator_rejects_resealed_arbitrary_contract_sections(self) -> None:
        manifest = freeze.generate_manifest()
        for field in ("protocol", "platform", "build", "candidate_closure"):
            forged = json.loads(_canonical(manifest))
            forged[field] = {"forged": True}
            forged["manifest_sha256"] = freeze._self_hash(forged)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.validate_manifest(_canonical(forged))
            self.assertEqual(error.exception.code, "manifest-shape")

    def test_native_workflow_bootstraps_rustup_before_prebinding(self) -> None:
        workflow = (freeze.REPO / freeze.WORKFLOW_REL).read_text(encoding="utf-8")
        configure = workflow.index("      - name: Configure isolated build directories")
        install = workflow.index("      - name: Install pinned Rust toolchain and target")
        prebinding = workflow.index("      - name: Recompute Gate-A candidate source closure")
        self.assertLess(configure, install)
        self.assertLess(install, prebinding)
        install_step = workflow[install:prebinding]
        self.assertIn(
            "rustup toolchain install 1.97.1 --profile minimal --no-self-update",
            install_step,
        )
        self.assertIn('CARGO_HOME="$RUNNER_TEMP/ck-phase3-cargo-home"', install_step)
        self.assertIn('RUSTUP_HOME="$RUNNER_TEMP/ck-phase3-rustup-home"', install_step)
        self.assertIn('test ! -e "$path"', workflow[configure:install])
        build = workflow[workflow.index("      - name: Build candidate in fresh explicit target directory") :]
        self.assertIn(
            'env -i PATH="$PATH" HOME="$CK_ISOLATED_HOME" CARGO_HOME="$CARGO_HOME" '
            'RUSTUP_HOME="$RUSTUP_HOME" CARGO_NET_OFFLINE=true '
            'CARGO_TARGET_DIR="$CK_TARGET_DIR" TMPDIR="$RUNNER_TEMP"',
            build,
        )

    def test_native_bundle_checksums_are_portable_closed_and_self_verified(self) -> None:
        workflow = (freeze.REPO / freeze.WORKFLOW_REL).read_text(encoding="utf-8")
        assemble = workflow[workflow.index("      - name: Assemble transfer-only build bundle") : workflow.index("      - name: Upload transfer-only build bundle")]
        checksum_command = next(line.strip() for line in assemble.splitlines() if line.strip().startswith("sha256sum candidate "))
        self.assertEqual(
            checksum_command,
            "sha256sum candidate build-receipt.json build-metadata.json cargo-metadata.json > SHA256SUMS",
        )
        self.assertIn('cd "$bundle"', assemble)
        self.assertIn("sha256sum -c SHA256SUMS", assemble)
        self.assertNotIn('sha256sum "$bundle"/*', assemble)
        self.assertIn("candidate build-receipt.json build-metadata.json cargo-metadata.json SHA256SUMS", assemble)

        digest = "0123456789abcdef" * 4
        portable = "\n".join(f"{digest}  {path}" for path in BUNDLE_FILES) + "\n"
        self.assertEqual(_portable_checksum_paths(portable), list(BUNDLE_FILES))
        for path in ("/home/runner/work/_temp/candidate", "nested/candidate"):
            with self.assertRaises(ValueError):
                _portable_checksum_paths(f"{digest}  {path}\n")

    def test_check_rejects_extra_materialized_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package"
            shutil.copytree(freeze.PACKAGE, package)
            manifest_path = package / freeze.MANIFEST_REL
            manifest_path.write_bytes(_canonical(freeze.generate_manifest(package=package)))
            manifest_path.chmod(0o644)
            (package / "corpora" / "unexpected.jsonl").write_text("{}\n", encoding="utf-8")
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.check_historical_manifest(package=package, path=manifest_path)
            self.assertEqual(error.exception.code, "extra-input")

    def test_two_durable_receipts_bind_binaries_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package, manifest_path = _copy_package(Path(directory))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            receipts: list[Path] = []
            for role in ("wsl", "native"):
                receipt_path = package / freeze.RECEIPT_DIR_REL / f"{role}.json"
                receipt_path.write_bytes(_receipt_raw(manifest, role, dependency_raw_suffix="c" if role == "wsl" else "d", dependency_bytes=1 if role == "wsl" else 2))
                receipts.append(receipt_path)
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                finalized = freeze.finalize_from_receipts(manifest_path, receipts, package=package)
            self.assertTrue(all(slot["status"] == "bound" for slot in finalized["binaries"].values()))
            self.assertEqual(finalized["readiness"]["materialization_state"], "frozen")
            self.assertIn("gate_b_review_requirement", finalized["readiness"])
            self.assertFalse(finalized["execution_permitted"])
            self.assertNotIn("artifact_ref", finalized["binaries"]["wsl2-x86_64"])
            self.assertEqual(finalized["binaries"]["wsl2-x86_64"]["receipt_path"], "manifests/build-receipts/wsl.json")
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                self.assertEqual(freeze.check_historical_manifest(package=package, path=manifest_path)["manifest_sha256"], finalized["manifest_sha256"])
            original = manifest_path.read_bytes()
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.write_manifest(finalized, manifest_path)
            self.assertEqual(error.exception.code, "manifest-finalized")
            self.assertEqual(manifest_path.read_bytes(), original)
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.finalize_from_receipts(manifest_path, receipts, package=package)
            self.assertEqual(error.exception.code, "build-receipt")
            self.assertEqual(manifest_path.read_bytes(), original)
            receipt_path = package / freeze.RECEIPT_DIR_REL / "wsl.json"
            receipt_path.write_bytes(receipt_path.read_bytes() + b"\n")
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.check_historical_manifest(package=package, path=manifest_path)
            self.assertIn(error.exception.code, {"receipt-drift", "build-receipt"})

    def test_receipt_directory_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package, manifest_path = _copy_package(Path(directory))
            (package / freeze.RECEIPT_DIR_REL / "extra.json").write_text("{}\n", encoding="utf-8")
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.check_historical_manifest(package=package, path=manifest_path)
            self.assertEqual(error.exception.code, "extra-input")

    def test_mixed_binary_slots_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package, manifest_path = _copy_package(Path(directory))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            receipts = []
            for role in ("wsl", "native"):
                receipt_path = package / freeze.RECEIPT_DIR_REL / f"{role}.json"
                receipt_path.write_bytes(_receipt_raw(manifest, role))
                receipts.append(receipt_path)
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                finalized = freeze.finalize_from_receipts(manifest_path, receipts, package=package)
            finalized["binaries"]["wsl2-x86_64"] = {"status": "unbound", "receipt_path": None, "receipt_bytes": None, "receipt_sha256": None, "receipt_self_hash": None, "binary_identity": None}
            finalized["manifest_sha256"] = freeze._self_hash(finalized)
            manifest_path.write_bytes(_canonical(finalized))
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.check_historical_manifest(package=package, path=manifest_path)
            self.assertEqual(error.exception.code, "binary-binding")

    def test_receipts_must_be_same_commit_and_full_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package, manifest_path = _copy_package(Path(directory))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            wsl = package / freeze.RECEIPT_DIR_REL / "wsl.json"
            native = package / freeze.RECEIPT_DIR_REL / "native.json"
            wsl.write_bytes(_receipt_raw(manifest, "wsl"))
            native.write_bytes(_receipt_raw(manifest, "native", source_commit="c" * 40))
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.finalize_from_receipts(manifest_path, [wsl, native], package=package)
            self.assertEqual(error.exception.code, "source-commit")

    def test_receipt_outside_tracked_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, manifest_path = _copy_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            outside = root / "wsl.json"
            outside.write_bytes(_receipt_raw(manifest, "wsl"))
            inside = package / freeze.RECEIPT_DIR_REL / "native.json"
            inside.write_bytes(_receipt_raw(manifest, "native"))
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.finalize_from_receipts(manifest_path, [outside, inside], package=package)
            self.assertEqual(error.exception.code, "build-receipt-path")

    def test_receipt_sidecar_must_have_exactly_one_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, _ = _copy_package(root)
            receipt = package / freeze.RECEIPT_PATHS["wsl2-x86_64"]
            receipt.write_text("{}\n", encoding="utf-8")
            (root / "receipt-hardlink.json").hardlink_to(receipt)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze._receipt_path(package, receipt)
            self.assertEqual(error.exception.code, "build-receipt-path")

    def test_nested_receipt_recursion_is_bounded(self) -> None:
        class RecursiveReceiptModule:
            @staticmethod
            def validate_receipt(_raw: bytes) -> dict:
                raise RecursionError("synthetic nested receipt")

        with tempfile.TemporaryDirectory() as directory:
            package, _ = _copy_package(Path(directory))
            receipt = package / freeze.RECEIPT_PATHS["wsl2-x86_64"]
            receipt.write_text("{}\n", encoding="utf-8")
            with patch.object(freeze, "_receipt_module", return_value=RecursiveReceiptModule()):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze._load_build_receipt(receipt, package, {}, {})
            self.assertEqual(error.exception.code, "build-receipt")

    def test_receipt_validator_identity_rejects_stale_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package, _ = _copy_package(Path(directory))
            source = package / "scripts" / "phase3_build_receipt.py"
            with self.assertRaises(freeze.FreezeManifestError):
                freeze._receipt_module(package, {
                    "provenance_tool_identities": [{
                        "path": "scripts/phase3_build_receipt.py",
                        "mode": 0o644,
                        "bytes": source.stat().st_size,
                        "sha256": "0" * 64,
                    }],
                })

    def test_manifest_write_is_atomic_and_leaves_no_temporary_file(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "nested" / "freeze-manifest.json"
            freeze.write_manifest(manifest, path)
            self.assertEqual(path.read_bytes(), _canonical(manifest))
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_manifest_write_rejects_resealed_arbitrary_overwrite(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "freeze-manifest.json"
            freeze.write_manifest(manifest, path)
            original = path.read_bytes()
            malformed = json.loads(_canonical(manifest))
            malformed["attempts"] = "caller-controlled replacement"
            malformed["manifest_sha256"] = freeze._self_hash(malformed)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.write_manifest(malformed, path)
            self.assertEqual(error.exception.code, "manifest-drift")
            self.assertEqual(path.read_bytes(), original)

    def test_manifest_check_rejects_nonregular_symlink_hardlink_and_wrong_mode(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "freeze-manifest.json"
            path.write_bytes(_canonical(manifest))
            path.chmod(0o644)
            invalid_paths: list[Path] = []

            wrong_mode = root / "wrong-mode.json"
            wrong_mode.write_bytes(path.read_bytes())
            wrong_mode.chmod(0o600)
            invalid_paths.append(wrong_mode)

            hardlink = root / "hardlink.json"
            hardlink.hardlink_to(path)
            invalid_paths.append(hardlink)

            symlink = root / "symlink.json"
            symlink.symlink_to(path)
            invalid_paths.append(symlink)

            directory_path = root / "directory.json"
            directory_path.mkdir()
            invalid_paths.append(directory_path)

            for invalid in invalid_paths:
                with self.subTest(path=invalid.name), self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze._load_manifest(invalid)
                self.assertEqual(error.exception.code, "manifest-file")

    def test_atomic_writer_materializes_mode_before_replace_and_rejects_bad_destination(self) -> None:
        manifest = freeze.generate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "freeze-manifest.json"
            path.write_bytes(_canonical(manifest))
            path.chmod(0o600)
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze._atomic_write_manifest(manifest, path)
            self.assertEqual(error.exception.code, "manifest-write")

            path.unlink()
            freeze._atomic_write_manifest(manifest, path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()

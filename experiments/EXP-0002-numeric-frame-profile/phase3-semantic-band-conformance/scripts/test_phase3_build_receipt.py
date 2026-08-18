#!/usr/bin/env python3
"""Focused tests for the non-executing Gate-B build receipt boundary."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("phase3_build_receipt.py")
SPEC = importlib.util.spec_from_file_location("phase3_build_receipt_test_subject", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


COMMIT = "a" * 40
CLOSURE = {
    "algorithm": "ck.phase3-candidate-source-build-closure.v1",
    "base_commit": "f4125342211a1d1436ae48b685ec2342700f39c4",
    "files": 47,
    "bytes": 1_494_337,
    "path_sha256": "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc",
    "content_sha256": "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2",
}


def _metadata(path: Path) -> Path:
    package_id = f"path+file://{path}/{MODULE.CANDIDATE_MANIFEST}#{MODULE.CANDIDATE_PACKAGE_NAME}@{MODULE.CANDIDATE_PACKAGE_VERSION}"
    serde_id = "registry+https://github.com/rust-lang/crates.io-index#serde@1.0.0"
    cargo_metadata = {
        "version": 1,
        "workspace_root": str(path / MODULE.CANDIDATE_MANIFEST.removesuffix("/Cargo.toml")),
        "packages": [
            {"id": package_id, "name": MODULE.CANDIDATE_PACKAGE_NAME, "version": MODULE.CANDIDATE_PACKAGE_VERSION, "source": None, "checksum": None, "manifest_path": str(path / MODULE.CANDIDATE_MANIFEST)},
            {"id": serde_id, "name": "serde", "version": "1.0.0", "source": MODULE.REGISTRY_SOURCE, "checksum": "a" * 64, "manifest_path": str(path / "registry" / "serde" / "Cargo.toml")},
        ],
        "workspace_members": [package_id],
        "workspace_default_members": [package_id],
        "resolve": {"root": package_id, "nodes": [{"id": package_id, "dependencies": [serde_id]}, {"id": serde_id, "dependencies": []}]},
    }
    dependency_path = path / "cargo-metadata.json"
    dependency_path.write_text(json.dumps(cargo_metadata), encoding="utf-8")
    lock_path = path / MODULE.CANDIDATE_LOCK
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("# synthetic locked dependency closure\n", encoding="utf-8")
    vendor_path = path / "vendor"
    package_path = vendor_path / "serde-1.0.0"
    package_path.mkdir(parents=True)
    (package_path / "Cargo.toml").write_text(
        "[package]\nname = \"serde\"\nversion = \"1.0.0\"\nedition = \"2021\"\n"
        "authors = [\"Fixture Author\"]\nbuild = false\n\n[dependencies]\nserde_derive = \"1\"\n",
        encoding="utf-8",
    )
    (package_path / ".cargo-checksum.json").write_text(json.dumps({"files": {}, "package": "a" * 64}), encoding="utf-8")
    (package_path / "lib.rs").write_text("pub fn fixture() {}\n", encoding="utf-8")
    config_path = path / "cargo-home" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[source.crates-io]\nreplace-with = \"vendored-sources\"\n\n[source.vendored-sources]\ndirectory = \"" + str(vendor_path.absolute()) + "\"\n", encoding="utf-8")
    build_metadata = {
        "schema": MODULE.METADATA_SCHEMA,
        "source_commit": COMMIT,
        "candidate_profile_id": MODULE.CANDIDATE_PROFILE_ID,
        "platform_role": "native",
        "target": MODULE.TARGET,
        "profile": MODULE.PROFILE,
        "platform_observation": {
            "stability": "observed-for-this-build-only", "runner_os": "test", "runner_arch": "X64",
            "image_os": "test", "image_version": "test", "kernel": "test", "sanitized_environment_keys": sorted(MODULE.ENV_POLICY_VALUES),
        },
        "build": {
            "argv": ["cargo", "+1.97.1", "build", "--manifest-path", MODULE.CANDIDATE_MANIFEST, "--target", MODULE.TARGET, "--target-dir", "/tmp/target", "--locked", "--offline"],
            "cwd": ".",
            "env_policy": {"mode": "sanitized-env-i", "ambient": "excluded", "variables": {"PATH": "<tool-path>", "HOME": "<build-home>", "CARGO_HOME": "<cargo-home>", "RUSTUP_HOME": "<rustup-home>", "CARGO_NET_OFFLINE": "true", "CARGO_TARGET_DIR": "<fresh-target-dir>", "TMPDIR": "<runner-temp>"}},
            "toolchain": {"rust_toolchain": MODULE.TOOLCHAIN, "rustc": "rustc 1.97.1 (fixture)", "cargo": "cargo 1.97.1 (fixture)", "python": "Python 3.13.0"},
            "cargo_lock_path": MODULE.CANDIDATE_LOCK,
            "dependency_metadata_path": str(dependency_path),
            "vendor_path": str(vendor_path),
            "vendor_role_path": "phase3-gate-b-vendor",
            "cargo_config_path": str(config_path),
            "cargo_config_role_path": "phase3-gate-b-cargo-config",
            "binary_role_path": "candidate-target/x86_64-unknown-linux-gnu/debug/phase3-candidate",
        },
    }
    metadata_path = path / "build-metadata.json"
    metadata_path.write_text(json.dumps(build_metadata), encoding="utf-8")
    return metadata_path


def _elf(path: Path, *, executable: bool = True) -> None:
    header = bytearray(64)
    header[:4] = b"\x7fELF"
    header[4] = 2  # ELF64
    header[5] = 1  # little endian
    header[7] = 0  # System V ABI
    struct.pack_into("<HHQ", header, 16, 3, 62, 0x400000)
    path.write_bytes(header + b"fixture payload")
    path.chmod(0o755 if executable else 0o644)


def _dependency_fixture(repo: Path) -> Path:
    candidate_id = f"path+file://{repo}/{MODULE.CANDIDATE_MANIFEST}#{MODULE.CANDIDATE_PACKAGE_NAME}@{MODULE.CANDIDATE_PACKAGE_VERSION}"
    serde_id = "registry+https://github.com/rust-lang/crates.io-index#serde@1.0.0"
    value = {
        "packages": [
            {
                "id": candidate_id,
                "name": MODULE.CANDIDATE_PACKAGE_NAME,
                "version": MODULE.CANDIDATE_PACKAGE_VERSION,
                "source": None,
                "checksum": None,
                "manifest_path": str(repo / "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml"),
            },
            {"id": serde_id, "name": "serde", "version": "1.0.0", "source": "registry+https://github.com/rust-lang/crates.io-index", "checksum": "a" * 64, "manifest_path": str(repo / "registry/serde/Cargo.toml")},
        ],
        "workspace_members": [candidate_id],
        "workspace_default_members": [candidate_id],
        "workspace_root": str(repo / MODULE.CANDIDATE_MANIFEST.removesuffix("/Cargo.toml")),
        "version": 1,
        "resolve": {"root": candidate_id, "nodes": [{"id": candidate_id, "dependencies": [serde_id]}, {"id": serde_id, "dependencies": []}]},
    }
    path = repo / "cargo-metadata.json"
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


class BuildReceiptTests(unittest.TestCase):
    def test_dependency_identity_normalizes_platform_roots_but_retains_raw_observation(self) -> None:
        with tempfile.TemporaryDirectory() as wsl_directory, tempfile.TemporaryDirectory() as native_directory:
            wsl = Path(wsl_directory)
            native = Path(native_directory)
            wsl_identity = MODULE._dependency_identity(_dependency_fixture(wsl), wsl)
            native_identity = MODULE._dependency_identity(_dependency_fixture(native), native)
            self.assertEqual(wsl_identity["sha256"], native_identity["sha256"])
            self.assertNotEqual(wsl_identity["raw_sha256"], native_identity["raw_sha256"])
            drift_value = json.loads((native / "cargo-metadata.json").read_text())
            drift_value["packages"][1]["checksum"] = "b" * 64
            (native / "cargo-metadata.json").write_text(json.dumps(drift_value, sort_keys=True))
            drifted = MODULE._dependency_identity(native / "cargo-metadata.json", native)
            self.assertNotEqual(native_identity["sha256"], drifted["sha256"])
            drift_value["packages"][1]["checksum"] = "a" * 64
            drift_value["resolve"]["nodes"][0]["dependencies"] = []
            (native / "cargo-metadata.json").write_text(json.dumps(drift_value, sort_keys=True))
            edge_drift = MODULE._dependency_identity(native / "cargo-metadata.json", native)
            self.assertNotEqual(native_identity["sha256"], edge_drift["sha256"])

    def test_self_hash_is_domain_framed_and_rejects_tampering(self) -> None:
        receipt = MODULE.build_receipt(
            source_commit=COMMIT,
            source_closure=CLOSURE,
            build={
                "platform_role": "native", "platform_observation": {"stability": "observed-for-this-build-only", "runner_os": "test", "runner_arch": "X64", "image_os": "test", "image_version": "test", "kernel": "test", "sanitized_environment_keys": sorted(MODULE.ENV_POLICY_VALUES)}, "target": MODULE.TARGET, "profile": MODULE.PROFILE,
                "argv": ["cargo", "+1.97.1", "build", "--manifest-path", MODULE.CANDIDATE_MANIFEST, "--target", MODULE.TARGET, "--target-dir", "/tmp/target", "--locked", "--offline"],
                "cwd": ".", "env_policy": {"mode": "sanitized-env-i", "ambient": "excluded", "variables": {"PATH": "<tool-path>", "HOME": "<build-home>", "CARGO_HOME": "<cargo-home>", "RUSTUP_HOME": "<rustup-home>", "CARGO_NET_OFFLINE": "true", "CARGO_TARGET_DIR": "<fresh-target-dir>", "TMPDIR": "<runner-temp>"}},
                "toolchain": {"rust_toolchain": MODULE.TOOLCHAIN, "rustc": "rustc fixture", "cargo": "cargo fixture", "python": "Python fixture"},
                "cargo_lock": {"path": MODULE.CANDIDATE_LOCK, "sha256": "0" * 64, "bytes": 1},
                "dependency_closure": {"schema": MODULE.DEPENDENCY_SCHEMA, "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1", "sha256": "1" * 64, "raw_sha256": "2" * 64, "bytes": 1, "packages": 1, "nodes": 1},
                "vendor_closure": {"role_path": "phase3-gate-b-vendor", "algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1", "files": 1, "bytes": 1, "path_sha256": "3" * 64, "content_sha256": "4" * 64},
                "cargo_config": {"role_path": "phase3-gate-b-cargo-config", "algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1", "sha256": "5" * 64, "bytes": 1},
                "binary_role_path": "candidate/bin",
            },
            binary={"role": "phase3-candidate", "path": "candidate/bin", "sha256": "0" * 64, "bytes": 1, "mode": "0755", "elf": {"class": "ELF64", "data": "little-endian", "machine": "x86_64", "type": "ET_DYN", "osabi": 0, "entry_point": "0x0000000000000000"}},
        )
        parsed = MODULE.validate_receipt(receipt)
        self.assertEqual(parsed["phase_id"], MODULE.PHASE_ID)
        with self.assertRaises(MODULE.ReceiptError):
            MODULE.validate_receipt(b" " + receipt)
        with self.assertRaises(MODULE.ReceiptError):
            MODULE.validate_receipt(receipt.rstrip(b"\n"))
        tampered = json.loads(receipt)
        tampered["source_commit"] = "b" * 40
        with self.assertRaises(MODULE.ReceiptError):
            MODULE.validate_receipt(json.dumps(tampered).encode())

    def test_pathological_json_nesting_is_a_bounded_receipt_error(self) -> None:
        pathological = b"[" * 2000 + b"0" + b"]" * 2000
        with self.assertRaises(MODULE.ReceiptError):
            MODULE.validate_receipt(pathological)
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "metadata.json"
            metadata.write_bytes(pathological)
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._json_file(metadata, "build metadata")

    def test_source_closure_drift_is_rejected(self) -> None:
        drifted = dict(CLOSURE)
        drifted["content_sha256"] = "f" * 64
        with self.assertRaises(MODULE.ReceiptError):
            MODULE.validate_source_closure(drifted)

    def test_vendor_closure_binds_bytes_paths_and_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vendor = Path(directory) / "vendor"
            (vendor / "pkg").mkdir(parents=True)
            file_path = vendor / "pkg" / "lib.rs"
            file_path.write_bytes(b"one")
            first = MODULE.capture_vendor_closure(vendor)
            file_path.write_bytes(b"two")
            changed_bytes = MODULE.capture_vendor_closure(vendor)
            self.assertNotEqual(first["content_sha256"], changed_bytes["content_sha256"])
            file_path.write_bytes(b"one")
            file_path.chmod(0o600)
            changed_mode = MODULE.capture_vendor_closure(vendor)
            self.assertNotEqual(first["path_sha256"], changed_mode["path_sha256"])
            file_path.chmod(0o644)
            file_path.rename(vendor / "pkg" / "renamed.rs")
            changed_path = MODULE.capture_vendor_closure(vendor)
            self.assertNotEqual(first["path_sha256"], changed_path["path_sha256"])
            (vendor / "pkg" / "link.rs").symlink_to("renamed.rs")
            with self.assertRaises(MODULE.ReceiptError):
                MODULE.capture_vendor_closure(vendor)

    def test_vendor_manifest_parser_accepts_ordinary_cargo_package_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "Cargo.toml"
            manifest.write_text(
                "[package]\nname = \"fixture-crate\"\nversion = \"1.2.3\"\n"
                "edition = \"2024\"\nauthors = [\"A Person\"]\nbuild = \"build.rs\"\n"
                "\n[dependencies]\nserde = { version = \"1\", features = [\"derive\"] }\n",
                encoding="utf-8",
            )
            parsed = MODULE._toml_file(manifest, "representative Cargo.toml")
            self.assertEqual(parsed["package"]["name"], "fixture-crate")
            self.assertEqual(parsed["package"]["version"], "1.2.3")

    def test_binary_hash_changes_when_supplied_binary_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "candidate-bin"
            _elf(binary)
            first = MODULE.capture_binary(root, binary)
            binary.write_bytes(binary.read_bytes() + b"drift")
            second = MODULE.capture_binary(root, binary)
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertNotEqual(first["bytes"], second["bytes"])

    def test_binary_requires_executable_little_endian_x86_64_elf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "candidate"
            _elf(binary, executable=False)
            with self.assertRaises(MODULE.ReceiptError):
                MODULE.capture_binary(root, binary)
            _elf(binary)
            raw = bytearray(binary.read_bytes())
            raw[5] = 2  # big-endian marker
            binary.write_bytes(raw)
            with self.assertRaises(MODULE.ReceiptError):
                MODULE.capture_binary(root, binary)

    def test_capture_is_read_only_and_does_not_launch_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "candidate-bin"
            _elf(binary)
            metadata = _metadata(root)
            with mock.patch.object(MODULE, "_git_head", return_value=COMMIT):
                receipt = MODULE.capture_receipt(root, binary, metadata, closure_capture=lambda _: CLOSURE)
            MODULE.validate_receipt(receipt)
            self.assertEqual(binary.read_bytes()[:4], b"\x7fELF")

    def test_metadata_rejects_candidate_execution_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = _metadata(root)
            value = json.loads(metadata.read_text())
            value["build"]["argv"][1] = "run"
            metadata.write_text(json.dumps(value))
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, value)

    def test_metadata_requires_complete_standalone_resolved_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = _metadata(root)
            value = json.loads((root / "cargo-metadata.json").read_text())
            value["resolve"]["nodes"].pop()
            (root / "cargo-metadata.json").write_text(json.dumps(value))
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, json.loads(metadata.read_text()))

    def test_metadata_rejects_unrelated_vendored_identity_or_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = _metadata(root)
            value = json.loads(metadata.read_text())
            checksum = root / "vendor" / "serde-1.0.0" / ".cargo-checksum.json"
            checksum.write_text(json.dumps({"files": {}, "package": "b" * 64}))
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, value)
            checksum.write_text(json.dumps({"files": {}, "package": "a" * 64}))
            config = Path(value["build"]["cargo_config_path"])
            config.write_text(config.read_text().replace("vendored-sources", "unrelated-source"))
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, value)

    def test_metadata_rejects_build_affecting_extras(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = _metadata(root)
            value = json.loads(metadata.read_text())
            value["build"]["argv"].append("--release")
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, value)
            value = json.loads(metadata.read_text())
            value["build"]["env_policy"]["variables"]["RUSTFLAGS"] = "<forbidden>"
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, value)
            value = json.loads(metadata.read_text())
            value["build"]["env_policy"]["variables"]["PATH"] = "<runner-temp>"
            with self.assertRaises(MODULE.ReceiptError):
                MODULE._validate_metadata(root, value)

    def test_binary_rejects_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            _elf(real)
            link = root / "link"
            link.symlink_to(real)
            with self.assertRaises(MODULE.ReceiptError):
                MODULE.capture_binary(root, link)

    def test_source_has_no_binary_execution_api_and_workflow_is_dispatch_only(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("subprocess.Popen", "subprocess.call", "subprocess.check_call", "os.system", "os.exec", "os.spawn"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("subprocess.run([str(binary)", source)
        workflow = SCRIPT.parents[4] / ".github" / "workflows" / "phase3-gate-b-native-build.yml"
        if workflow.exists():
            text = workflow.read_text(encoding="utf-8")
            self.assertNotIn("phase3_runner.py", text)
            self.assertNotRegex(text, r"cargo(?:\s+\+[^\s]+)?\s+(?:run|test|bench)\b")
            self.assertIn('cargo +1.97.1 vendor "$CK_VENDOR_DIR"', text)
            self.assertIn("--manifest-path experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml", text)
            self.assertIn("--locked --versioned-dirs", text)
            self.assertNotIn("archive: false", text)
            self.assertRegex(text, r"actions/checkout@[0-9a-f]{40}\s+# v7\.0\.1")
            self.assertRegex(text, r"actions/setup-python@[0-9a-f]{40}\s+# v7\.0\.0")
            self.assertRegex(text, r"actions/upload-artifact@[0-9a-f]{40}\s+# v7\.0\.1")
            self.assertIn('line.split("=", 1)[0]', text)
            self.assertIn("observed_env_names != expected_env_names", text)
            self.assertIn("fetch-depth: 0", text)
            self.assertNotIn("fetch-depth: 1", text)
            self.assertIn('cargo +1.97.1 vendor "$CK_VENDOR_DIR" \\', text)


if __name__ == "__main__":
    unittest.main()

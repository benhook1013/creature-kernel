"""Focused non-executing tests for the Phase 3 freeze manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

import phase3_build_receipt as build_receipt
import phase3_freeze_manifest as freeze


BUNDLE_FILES = ("candidate", "build-receipt.json", "build-metadata.json", "cargo-metadata.json")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


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


class FreezeManifestTests(unittest.TestCase):
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
                freeze.check_manifest(path=path)
            self.assertEqual(error.exception.code, "manifest-self-hash")
            tampered = json.loads(_canonical(manifest))
            tampered["raw_inputs"][0]["sha256"] = "0" * 64
            tampered["manifest_sha256"] = freeze._self_hash(tampered)
            path.write_bytes(_canonical(tampered))
            with self.assertRaises(freeze.FreezeManifestError) as error:
                freeze.check_manifest(path=path)
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
                freeze.check_manifest(path=path)
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
                self.assertEqual(freeze.check_manifest(path=path)["candidate_source_commit"], manifest["candidate_source_commit"])

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
                freeze.check_manifest(path=path)
            self.assertIn(error.exception.code, {"manifest-drift", "source-commit"})

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
                    freeze.check_manifest(package=package, path=manifest_path)
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
                self.assertEqual(freeze.check_manifest(package=package, path=manifest_path)["manifest_sha256"], finalized["manifest_sha256"])
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
                    freeze.check_manifest(package=package, path=manifest_path)
            self.assertIn(error.exception.code, {"receipt-drift", "build-receipt"})

    def test_receipt_directory_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package, manifest_path = _copy_package(Path(directory))
            (package / freeze.RECEIPT_DIR_REL / "extra.json").write_text("{}\n", encoding="utf-8")
            with patch.object(freeze, "_validate_candidate_commit_snapshot"):
                with self.assertRaises(freeze.FreezeManifestError) as error:
                    freeze.check_manifest(package=package, path=manifest_path)
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
                    freeze.check_manifest(package=package, path=manifest_path)
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

#!/usr/bin/env python3
"""Synthetic, no-build tests for the exact Phase 3 custody boundary."""

from __future__ import annotations

import hashlib
import fcntl
import importlib.util
import io
import json
import os
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("phase3_exact_custody.py")
SPEC = importlib.util.spec_from_file_location("phase3_exact_custody_test_subject", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

RECEIPT_SCRIPT = SCRIPT.with_name("phase3_build_receipt.py")
RECEIPT_SPEC = importlib.util.spec_from_file_location("phase3_exact_custody_receipt_fixture", RECEIPT_SCRIPT)
assert RECEIPT_SPEC and RECEIPT_SPEC.loader
R = importlib.util.module_from_spec(RECEIPT_SPEC)
RECEIPT_SPEC.loader.exec_module(R)
FREEZE_SCRIPT = SCRIPT.with_name("phase3_freeze_manifest.py")
FREEZE_SPEC = importlib.util.spec_from_file_location("phase3_exact_custody_freeze_fixture", FREEZE_SCRIPT)
assert FREEZE_SPEC and FREEZE_SPEC.loader
F = importlib.util.module_from_spec(FREEZE_SPEC)
FREEZE_SPEC.loader.exec_module(F)

_REAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
_REAL_MODULE_FROM_SPEC = importlib.util.module_from_spec

SOURCE = F.EXPECTED_CANDIDATE_SOURCE_COMMIT
EXECUTION_SOURCE = "e" * 40
PREDECESSOR_HASH = F.EXPECTED_V1_MANIFEST_SHA256
PREDECESSOR_INHERITED_HASH = F.EXPECTED_INHERITED_V1_SHA256
FREEZE_HASH = "d" * 64
NOW = "2026-08-19T00:00:00Z"
LATER = "2026-08-20T00:00:00Z"
FROZEN_WORKFLOW_SHA = "9" * 64
WORKFLOW_REFS = ["actions/checkout@" + "1" * 40]


class _FixtureFreezeValidator:
    """Real pure validator with historical inherited facts isolated from custody."""

    @staticmethod
    def validate_manifest(raw: bytes) -> dict[str, object]:
        with mock.patch.object(
            F,
            "_inherited_v1_hash",
            return_value=F.EXPECTED_INHERITED_V1_SHA256,
        ):
            return F.validate_manifest(raw)


class _NoopFreezeLoader:
    @staticmethod
    def exec_module(_module: object) -> None:
        return None


class _FixtureFreezeSpec:
    loader = _NoopFreezeLoader()


def _fixture_spec_from_file_location(name: str, path: Path):
    if name == "phase3_exact_custody_freeze":
        return _FixtureFreezeSpec()
    return _REAL_SPEC_FROM_FILE_LOCATION(name, path)


def _fixture_module_from_spec(spec):
    if isinstance(spec, _FixtureFreezeSpec):
        return _FixtureFreezeValidator
    return _REAL_MODULE_FROM_SPEC(spec)


def _fixture_identity(path: str, digest: str) -> dict[str, object]:
    return {"path": path, "mode": 0o644, "bytes": 1, "sha256": digest}


def _fixture_toolchain() -> dict[str, object]:
    return {
        "rust_toolchain_file": "rust-toolchain.toml", "rust_toolchain_file_identity": _fixture_identity("rust-toolchain.toml", "6" * 64),
        "channel": F.TOOLCHAIN, "profile": "minimal", "components": ["rustfmt", "clippy"],
        "rustc": {"release": F.TOOLCHAIN, "commit_hash": "8bab26f4f68e0e26f0bb7960be334d5b520ea452", "host": F.TARGET, "llvm": "22.1.6"},
        "cargo": {"release": F.TOOLCHAIN, "commit_hash": "c980f4866141969fab6254a680546a277789d6f0"},
        "receipt_contract": {"rust_toolchain": F.TOOLCHAIN, "rustc_prefix": "rustc 1.97.1", "rustc_commit_hash": "8bab26f4f68e0e26f0bb7960be334d5b520ea452", "rustc_host": F.TARGET, "rustc_llvm": "22.1.6", "cargo_prefix": "cargo 1.97.1", "cargo_commit_hash": "c980f4866141969fab6254a680546a277789d6f0", "cargo_host": F.TARGET, "python_prefix": "Python 3"},
    }


def _fixture_dependencies() -> dict[str, object]:
    return {
        "cargo_lock": _fixture_identity(F.CANDIDATE_LOCK_REL, "7" * 64),
        "dependency_closure_contract": {"schema": "ck.exp-0002.phase3.gate-b-cargo-metadata-1", "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1", "fields": F.RECEIPT_DEPENDENCY_FIELDS},
        "vendor_closure_contract": {"algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1", "fields": F.RECEIPT_VENDOR_FIELDS, "role_path_pattern": "phase3-gate-b-{platform_role}-vendor"},
        "cargo_config_contract": {"algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1", "fields": ["role_path", "algorithm", "sha256", "bytes"], "role_path_pattern": "phase3-gate-b-{platform_role}-cargo-config"},
        "offline": True,
    }


def _fixture_closure() -> dict[str, object]:
    entry = {"path": "experiments/fixture-source.txt", "mode": stat.S_IFREG | 0o644, "bytes": 1, "sha256": "8" * 64}
    encoded = entry["path"].encode()
    path_stream = b"ck.phase3-candidate-source-build-path-set.v1\0" + len(encoded).to_bytes(4, "big") + encoded + int(entry["mode"]).to_bytes(4, "big")
    content_stream = b"ck.phase3-candidate-source-build-content.v1\0" + len(encoded).to_bytes(4, "big") + encoded + int(entry["mode"]).to_bytes(4, "big") + int(entry["bytes"]).to_bytes(8, "big")
    return {"algorithm": "ck.phase3-candidate-source-build-closure.v1", "base_commit": "b" * 40, "count": 1, "total_raw_bytes": 1, "path_set_sha256": hashlib.sha256(path_stream).hexdigest(), "content_sha256": hashlib.sha256(content_stream).hexdigest(), "entries": [entry]}


def _cargo_raw() -> bytes:
    return json.dumps({"version": 1, "packages": [], "resolve": {}}, sort_keys=True).encode()


def _receipt(candidate: bytes, role: str = "wsl") -> bytes:
    build = {
        "platform_role": role,
        "platform_observation": {
            "stability": "observed-for-this-build-only", "runner_os": "fixture", "runner_arch": "x86_64",
            "image_os": "fixture", "image_version": "fixture", "kernel": "fixture",
            "sanitized_environment_keys": sorted(R.ENV_POLICY_VALUES),
        },
        "target": R.TARGET,
        "profile": R.PROFILE,
        "argv": ["cargo", "+1.97.1", "build", "--manifest-path", R.CANDIDATE_MANIFEST, "--target", R.TARGET, "--target-dir", "/tmp/target", "--locked", "--offline"],
        "cwd": ".",
        "env_policy": {"mode": "sanitized-env-i", "ambient": "excluded", "variables": R.ENV_POLICY_VALUES},
        "toolchain": {"rust_toolchain": R.TOOLCHAIN, "rustc": "rustc fixture", "cargo": "cargo fixture", "python": "Python fixture"},
        "cargo_lock": {"path": R.CANDIDATE_LOCK, "sha256": "0" * 64, "bytes": 1},
        "dependency_closure": {"schema": R.DEPENDENCY_SCHEMA, "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1", "sha256": "1" * 64, "raw_sha256": hashlib.sha256(_cargo_raw()).hexdigest(), "bytes": len(_cargo_raw()), "packages": 0, "nodes": 0},
        "vendor_closure": {"role_path": f"phase3-gate-b-{role}-vendor", "algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1", "files": 1, "bytes": 1, "path_sha256": "3" * 64, "content_sha256": "4" * 64},
        "cargo_config": {"role_path": f"phase3-gate-b-{role}-cargo-config", "algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1", "sha256": "5" * 64, "bytes": 1},
        "binary_role_path": f"phase3-gate-b-{role}-target/{R.TARGET}/debug/candidate",
    }
    binary = {
        "role": "phase3-candidate", "path": build["binary_role_path"], "sha256": hashlib.sha256(candidate).hexdigest(), "bytes": len(candidate), "mode": "0755",
        "elf": {"class": "ELF64", "data": "little-endian", "machine": "x86_64", "type": "ET_DYN", "osabi": 0, "entry_point": "0x0000000000000000"},
    }
    return R.build_receipt(
        source_commit=SOURCE,
        source_closure={"algorithm": "ck.phase3-candidate-source-build-closure.v1", "base_commit": "f4125342211a1d1436ae48b685ec2342700f39c4", "files": 47, "bytes": 1494337, "path_sha256": "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc", "content_sha256": "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2"},
        build=build,
        binary=binary,
    )


def _metadata(role: str) -> bytes:
    receipt_build = json.loads(_receipt(b"metadata fixture", role))["build"]
    return json.dumps({
        "schema": M.METADATA_SCHEMA, "source_commit": SOURCE, "candidate_profile_id": M.CANDIDATE_PROFILE_ID,
        "platform_role": role, "target": M.TARGET, "profile": M.PROFILE,
        "platform_observation": receipt_build["platform_observation"],
        "build": {
            "argv": receipt_build["argv"], "cwd": receipt_build["cwd"], "env_policy": receipt_build["env_policy"], "toolchain": receipt_build["toolchain"], "cargo_lock_path": receipt_build["cargo_lock"]["path"],
            "dependency_metadata_path": "cargo-metadata.json", "vendor_path": "vendor", "vendor_role_path": receipt_build["vendor_closure"]["role_path"],
            "cargo_config_path": "config.toml", "cargo_config_role_path": receipt_build["cargo_config"]["role_path"],
            "binary_role_path": receipt_build["binary_role_path"],
        },
    }, sort_keys=True).encode()


def _bundle(candidate: bytes, role: str = "wsl", *, names=M.BUNDLE_MEMBERS, modes: dict[str, int] | None = None) -> bytes:
    receipt = _receipt(candidate, role)
    values = {"candidate": candidate, "build-receipt.json": receipt, "build-metadata.json": _metadata(role), "cargo-metadata.json": _cargo_raw()}
    values["SHA256SUMS"] = "".join(hashlib.sha256(values[name]).hexdigest() + "  " + name + "\n" for name in M.MANIFEST_MEMBERS).encode()
    for name in names:
        values.setdefault(name, b"extra")
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in names:
            item = tarfile.TarInfo(name)
            item.mode = (modes or {}).get(name, 0o755 if name == "candidate" else 0o644)
            item.size = len(values[name])
            archive.addfile(item, io.BytesIO(values[name]))
    return stream.getvalue()


def _zip(bundle: bytes) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("phase3-gate-b-native-build.tar", bundle)
    return stream.getvalue()


def _record(bundle: bytes, root: Path, *, selector: str = "wsl2-x86_64", kind: str = "raw", candidate: bytes = b"tiny candidate") -> tuple[bytes, bytes, Path]:
    global FREEZE_HASH
    if kind == "github":
        selector = "ubuntu-24.04-x86_64"
    role = M.PLATFORM_SELECTORS[selector]
    receipt = _receipt(candidate, role)
    metadata = _metadata(role)
    if kind == "github":
        transfer_bytes = _zip(bundle)
        path = root / "artifact.zip"
        path.write_bytes(transfer_bytes)
        transfer: dict[str, object] = {
            "kind": "github-actions-artifact-zip", "locator": {"kind": "filesystem-path", "value": str(path)},
            "workflow": {"path": M.WORKFLOW_PATH, "commit": SOURCE, "sha256": FROZEN_WORKFLOW_SHA},
            "run": {"id": 123, "attempt": 1}, "artifact": {"id": 456, "digest": "sha256:" + hashlib.sha256(transfer_bytes).hexdigest(), "created_at": "2026-08-18T00:00:00Z", "expires_at": LATER, "retention_days": M.GITHUB_RETENTION_DAYS},
            "archive": {"bytes": len(transfer_bytes), "sha256": hashlib.sha256(transfer_bytes).hexdigest()}, "bundle": {"bytes": len(bundle), "sha256": hashlib.sha256(bundle).hexdigest()},
        }
    else:
        path = root / "bundle.tar"
        path.write_bytes(bundle)
        transfer = {"kind": "invocation-owned-raw-bundle-tar", "locator": {"kind": "filesystem-path", "value": str(path)}, "bundle": {"bytes": len(bundle), "sha256": hashlib.sha256(bundle).hexdigest()}, "created_at": "2026-08-18T00:00:00Z", "expires_at": LATER, "retention_days": 2}
    receipt_sha = hashlib.sha256(receipt).hexdigest()
    receipt_obj = json.loads(receipt)
    record = {
        "schema": M.SCHEMA, "experiment_id": M.EXPERIMENT_ID, "phase_id": M.PHASE_ID, "candidate_profile_id": M.CANDIDATE_PROFILE_ID, "successor_manifest_sha256": FREEZE_HASH,
        "platform": {"selector": selector, "role": M.PLATFORM_SELECTORS[selector]}, "candidate_source_commit": SOURCE,
        "receipt": {"path": "build-receipt.json", "mode": stat.S_IFREG | 0o644, "bytes": len(receipt), "sha256": receipt_sha, "self_hash": receipt_obj["receipt_sha256"]},
        "candidate": {"path": "candidate", "mode": stat.S_IFREG | 0o755, "bytes": len(candidate), "sha256": hashlib.sha256(candidate).hexdigest()},
        "transfer": transfer, "policy": {"custody": "declared", "candidate_execution": "prohibited", "experiment_dispatch": "prohibited", "causal_build_attestation": False}, "custody_record_sha256": None,
    }
    manifest_candidate = {key: record["candidate"][key] for key in ("bytes", "mode", "sha256")}
    slot = {"status": "bound", "binary_identity": manifest_candidate, "receipt_bytes": len(receipt), "receipt_path": "manifests/build-receipts/native.json", "receipt_sha256": receipt_sha, "receipt_self_hash": receipt_obj["receipt_sha256"]}
    wsl_slot = dict(slot)
    wsl_slot["receipt_path"] = "manifests/build-receipts/wsl.json"
    workflow_identity = {"bytes": 1, "mode": 0o644, "path": M.WORKFLOW_PATH, "sha256": FROZEN_WORKFLOW_SHA}
    manifest_value = {
        "attempts": "per-attempt observations and Ben authorization are external to this manifest",
        "binaries": {"wsl2-x86_64": wsl_slot, "ubuntu-24.04-x86_64": slot},
        "binding": {"candidate_profile_id": M.CANDIDATE_PROFILE_ID, "experiment_id": M.EXPERIMENT_ID, "phase_id": M.PHASE_ID},
        "build": {"dependencies": _fixture_dependencies(), "recipe": F._build_recipe(), "toolchain": _fixture_toolchain()},
        "candidate_closure": _fixture_closure(), "candidate_source_commit": SOURCE,
        "canonicalization": F._v2_canonicalization(),
        "execution_permitted": False, "lifecycle": "planned", "manifest_sha256": None,
        "execution_tool_source_commit": EXECUTION_SOURCE,
        "predecessor_manifest_sha256": PREDECESSOR_HASH,
        "predecessor_inherited_sha256": PREDECESSOR_INHERITED_HASH,
        "platform": F._platforms(),
        "protocol": {"request_protocol_id": F.REQUEST_PROTOCOL, "response_protocol_id": F.RESPONSE_PROTOCOL, "request_fields": F.REQUEST_FIELDS, "canonical_wire": "strict UTF-8 JSON object, exact seven request fields, canonical bytes are SHA-256 framed by the evidence contract"},
        "provenance_tool_identities": [_fixture_identity(path, "1" * 64) for path in F.PROVENANCE_TOOLS],
        "raw_inputs": [_fixture_identity(path, "2" * 64) for path in (*F.PACKAGE_INPUTS, F.FIXTURE_REL)],
        "readiness": F._readiness({"wsl2-x86_64": {"status": "bound"}, "ubuntu-24.04-x86_64": {"status": "bound"}}),
        "repository_inputs": {"native_build_workflow": {"identity": workflow_identity, "path": M.WORKFLOW_PATH, "pinned_action_refs": WORKFLOW_REFS, "runner_label": "ubuntu-24.04"}},
        "runtime_tool_identities": [_fixture_identity(path, "4" * 64) for path in F.RUNTIME_TOOLS],
        "exact_runtime_tool_identities": [_fixture_identity(path, "5" * 64) for path in F.EXACT_RUNTIME_TOOLS],
        "schema": M.FREEZE_SCHEMA, "status": "Proposed",
    }
    FREEZE_HASH = F._self_hash(manifest_value)
    manifest_value["manifest_sha256"] = FREEZE_HASH
    manifest_raw = M._canonical(manifest_value) + b"\n"
    record["successor_manifest_sha256"] = FREEZE_HASH
    return M.encode_custody_record(record), manifest_raw, path


def _reseal_manifest(raw: bytes, mutate) -> tuple[bytes, str]:
    """Make a structurally forged manifest with a valid canonical self-hash."""
    value = json.loads(raw)
    mutate(value)
    digest = F._self_hash(value)
    value["manifest_sha256"] = digest
    return M._canonical(value) + b"\n", digest


class ExactCustodyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.freeze_spec_patch = mock.patch.object(
            M.importlib.util,
            "spec_from_file_location",
            side_effect=_fixture_spec_from_file_location,
        )
        self.freeze_module_patch = mock.patch.object(
            M.importlib.util,
            "module_from_spec",
            side_effect=_fixture_module_from_spec,
        )
        self.freeze_spec_patch.start()
        self.freeze_module_patch.start()

    def tearDown(self) -> None:
        self.freeze_module_patch.stop()
        self.freeze_spec_patch.stop()

    def test_raw_wsl_success_materializes_descriptor_bound_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = b"tiny candidate"
            bundle = _bundle(candidate)
            raw, manifest, _ = _record(bundle, root, candidate=candidate)
            invocation = root / "invocation"
            invocation.mkdir()
            verified = M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=invocation, now=NOW)
            self.assertEqual(verified.platform_role, "wsl")
            self.assertEqual(verified.candidate.fd >= 0, True)
            self.assertEqual(fcntl.fcntl(verified.candidate_fd, fcntl.F_GETFL) & os.O_ACCMODE, os.O_RDONLY)
            self.assertEqual(verified.candidate_sha256, hashlib.sha256(candidate).hexdigest())
            self.assertEqual(verified.candidate_path.read_bytes(), candidate)
            self.assertEqual(stat.S_IMODE(verified.candidate.mode), 0o755)
            seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
            self.assertEqual(fcntl.fcntl(verified.candidate_fd, fcntl.F_GET_SEALS), seals)
            with self.assertRaises(OSError):
                os.write(verified.candidate_fd, b"mutation")
            verified.candidate_path.write_bytes(b"diagnostic mutation")
            self.assertEqual(os.pread(verified.candidate_fd, len(candidate), 0), candidate)
            verified_fd = verified.candidate_fd
            verified.close()
            self.assertEqual(verified.candidate_fd, -1)
            replacement_fd = os.open(verified.receipt_path, os.O_RDONLY)
            verified.close()
            os.fstat(replacement_fd)
            os.close(replacement_fd)

    def test_github_zip_success_and_archive_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = b"native tiny candidate"
            bundle = _bundle(candidate, "native")
            raw, manifest, _ = _record(bundle, root, kind="github", candidate=candidate)
            invocation = root / "invocation"
            invocation.mkdir()
            verified = M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=invocation, now=NOW)
            self.assertEqual(verified.platform_role, "native")
            self.assertEqual(json.loads(raw)["transfer"]["workflow"]["sha256"], FROZEN_WORKFLOW_SHA)
            verified.close()
            # A byte change is never repaired by consuming a second locator.
            (root / "artifact.zip").write_bytes((root / "artifact.zip").read_bytes() + b"x")
            with self.assertRaises(M.CustodyError):
                M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=root / "second", now=NOW)

    def test_record_is_canonical_strict_and_binds_successor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(b"tiny")
            raw, manifest, _ = _record(bundle, root)
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(b" " + raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(raw, expected_manifest=manifest, expected_manifest_sha256="c" * 64, now=NOW)
            tampered = json.loads(raw)
            tampered["policy"]["causal_build_attestation"] = True
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(M.encode_custody_record(tampered), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)

    def test_predecessor_freeze_is_rejected_even_when_canonical_owner_accepts_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw, manifest, _ = _record(_bundle(b"tiny"), root)
            predecessor = F._v1_projection(json.loads(manifest))
            predecessor_raw = M._canonical(predecessor) + b"\n"
            with self.assertRaises(M.CustodyError) as context:
                M.validate_custody_record(
                    raw,
                    expected_manifest=predecessor_raw,
                    expected_manifest_sha256=predecessor["manifest_sha256"],
                    now=NOW,
                )
            self.assertEqual(context.exception.code, "record-binding")

            rebound = json.loads(raw)
            rebound["successor_manifest_sha256"] = predecessor["manifest_sha256"]
            with self.assertRaises(M.CustodyError) as context:
                M.validate_custody_record(
                    M.encode_custody_record(rebound),
                    expected_manifest=predecessor_raw,
                    expected_manifest_sha256=predecessor["manifest_sha256"],
                    now=NOW,
                )
            self.assertEqual(context.exception.code, "manifest-version")

    def test_expiry_unavailability_and_fresh_directory_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = b"tiny candidate"
            bundle = _bundle(candidate)
            raw, manifest, path = _record(bundle, root, candidate=candidate)
            expired = json.loads(raw)
            expired["transfer"]["expires_at"] = "2026-08-18T00:00:00Z"
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(M.encode_custody_record(expired), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)
            path.unlink()
            invocation = root / "invocation"
            invocation.mkdir()
            with self.assertRaises(M.CustodyError):
                M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=invocation, now=NOW)
            # Recreate the transfer and ensure a non-fresh invocation dir is rejected.
            _record(bundle, root, candidate=candidate)
            (invocation / "unexpected").write_bytes(b"x")
            with self.assertRaises(M.CustodyError) as error:
                M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=invocation, now=NOW)
            self.assertEqual(error.exception.code, "invocation-dir")

    def test_materialize_cleanup_keeps_preexisting_and_replaced_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invocation = root / "invocation"
            invocation.mkdir()
            directory_fd, _, absolute = M._fresh_directory(invocation)
            try:
                keep = invocation / "candidate"
                keep.write_bytes(b"KEEP")
                with self.assertRaises(M.CustodyError):
                    M._materialize_file(directory_fd, absolute, "candidate", b"owned", 0o755, "candidate")
                self.assertEqual(keep.read_bytes(), b"KEEP")
                keep.unlink()

                def replace_then_fail(_fd: int) -> None:
                    replacement = invocation / "replacement"
                    replacement.write_bytes(b"replacement")
                    os.replace(replacement, keep)
                    raise OSError("injected materialization failure")

                with mock.patch.object(M.os, "fsync", side_effect=replace_then_fail), mock.patch.object(M.os, "unlink") as unlink:
                    with self.assertRaises(M.CustodyError):
                        M._materialize_file(directory_fd, absolute, "candidate", b"owned", 0o755, "candidate")
                    unlink.assert_not_called()
                self.assertEqual(keep.read_bytes(), b"replacement")
            finally:
                os.close(directory_fd)

    def test_failed_invocation_retains_partial_diagnostic_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = b"partial candidate"
            bundle = _bundle(candidate)
            raw, manifest, _ = _record(bundle, root, candidate=candidate)
            invocation = root / "invocation"
            invocation.mkdir()
            original = M._materialize_file

            def fail_receipt(dirfd, path, name, data, mode, label):
                if name == "build-receipt.json":
                    raise M.CustodyError("injected", "receipt failure")
                return original(dirfd, path, name, data, mode, label)

            with mock.patch.object(M, "_materialize_file", side_effect=fail_receipt):
                with self.assertRaises(M.CustodyError):
                    M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=invocation, now=NOW)
            self.assertEqual((invocation / "candidate").read_bytes(), candidate)
            self.assertFalse((invocation / "build-receipt.json").exists())

    def test_tar_closure_rejects_order_extra_path_link_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = b"tiny"
            for names, modes in [
                (M.BUNDLE_MEMBERS[:1] + M.BUNDLE_MEMBERS[2:], None),
                (M.BUNDLE_MEMBERS + ("extra",), None),
                (tuple(name + "/../candidate" if name == "candidate" else name for name in M.BUNDLE_MEMBERS), None),
                (M.BUNDLE_MEMBERS, {"candidate": 0o644}),
            ]:
                bundle = _bundle(candidate, names=names, modes=modes)
                raw, manifest, _ = _record(bundle, root, candidate=candidate)
                with self.assertRaises(M.CustodyError):
                    M.verify_and_materialize(raw, expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=root / f"inv-{len(names)}", now=NOW)

    def test_sha_manifest_and_metadata_tamper_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(b"tiny")
            raw, manifest, path = _record(bundle, root)
            # Change the record's declared tar hash while retaining its self-hash.
            tampered = json.loads(raw)
            tampered["transfer"]["bundle"]["sha256"] = "f" * 64
            with self.assertRaises(M.CustodyError):
                M.verify_and_materialize(M.encode_custody_record(tampered), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=root / "inv", now=NOW)
            # Duplicate JSON members are rejected before identity validation.
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(raw.replace(b'"schema":', b'"schema":"bad","schema":', 1), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)

    def test_tar_links_devices_bombs_and_zip_closure_are_rejected(self) -> None:
        candidate = b"tiny"
        ordinary = _bundle(candidate)
        transfer = {"bundle": {"bytes": len(ordinary), "sha256": hashlib.sha256(ordinary).hexdigest()}}
        for special_type in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                for index, name in enumerate(M.BUNDLE_MEMBERS):
                    item = tarfile.TarInfo(name)
                    item.mode = 0o755 if name == "candidate" else 0o644
                    if index == 0:
                        item.type = special_type
                        item.linkname = "build-receipt.json"
                        item.size = 0
                        archive.addfile(item)
                    else:
                        payload = candidate if name == "build-receipt.json" else b"{}\n"
                        item.size = len(payload)
                        archive.addfile(item, io.BytesIO(payload))
            malformed = stream.getvalue()
            malformed_transfer = {"bundle": {"bytes": len(malformed), "sha256": hashlib.sha256(malformed).hexdigest()}}
            with self.assertRaises(M.CustodyError):
                M._tar_members(malformed, malformed_transfer)
        bomb = bytearray(ordinary)
        # The first tar header's size field is made enormous; the checksum is
        # intentionally left stale, so either header or bounded-size rejection
        # is acceptable and no large allocation is attempted.
        bomb[124:136] = b"77777777777\0"
        with self.assertRaises(M.CustodyError):
            M._tar_members(bytes(bomb), transfer)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_stream = io.BytesIO()
            with zipfile.ZipFile(zip_stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("bundle.tar", ordinary)
                archive.writestr("extra", b"x")
            zraw = zip_stream.getvalue()
            ztransfer = {"archive": {"bytes": len(zraw), "sha256": hashlib.sha256(zraw).hexdigest()}, "artifact": {"digest": "sha256:" + hashlib.sha256(zraw).hexdigest()}, "bundle": transfer["bundle"]}
            with self.assertRaises(M.CustodyError):
                M._zip_bundle(zraw, ztransfer)
            bomb_zip_stream = io.BytesIO()
            with zipfile.ZipFile(bomb_zip_stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("bundle.tar", b"0" * (1024 * 1024))
            zraw = bomb_zip_stream.getvalue()
            ztransfer = {"archive": {"bytes": len(zraw), "sha256": hashlib.sha256(zraw).hexdigest()}, "artifact": {"digest": "sha256:" + hashlib.sha256(zraw).hexdigest()}, "bundle": {"bytes": 1024 * 1024, "sha256": hashlib.sha256(b"0" * (1024 * 1024)).hexdigest()}}
            with self.assertRaises(M.CustodyError):
                M._zip_bundle(zraw, ztransfer)

    def test_symlink_locator_and_json_depth_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(b"tiny")
            raw, manifest, path = _record(bundle, root)
            link = root / "link.tar"
            link.symlink_to(path)
            record = json.loads(raw)
            record["transfer"]["locator"]["value"] = str(link)
            invocation = root / "inv"
            invocation.mkdir()
            with self.assertRaises(M.CustodyError):
                M.verify_and_materialize(M.encode_custody_record(record), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=invocation, now=NOW)
            relative = json.loads(raw)
            relative["transfer"]["locator"]["value"] = "bundle.tar"
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(M.encode_custody_record(relative), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)
        with self.assertRaises(M.CustodyError):
            M._json((b"[" * (M.MAX_JSON_DEPTH + 2)) + b"0" + (b"]" * (M.MAX_JSON_DEPTH + 2)), "depth fixture", M.MAX_JSON_BYTES)

    def test_forged_manifest_metadata_mismatch_parent_swap_hardlink_and_retention_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(b"tiny")
            raw, manifest, path = _record(bundle, root)
            members = M._tar_members(bundle, {"bundle": {"bytes": len(bundle), "sha256": hashlib.sha256(bundle).hexdigest()}})
            metadata_value = json.loads(members["build-metadata.json"])
            metadata_value["build"]["cwd"] = "/forged"
            members["build-metadata.json"] = json.dumps(metadata_value, sort_keys=True).encode()
            with self.assertRaises(M.CustodyError):
                M._validate_metadata(members, "wsl", SOURCE)
            forged = bytearray(manifest)
            forged[-2] = ord(" ") if forged[-2] != ord(" ") else ord("!")
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(raw, expected_manifest=bytes(forged), expected_manifest_sha256=FREEZE_HASH, now=NOW)
            # Each mutation below is re-sealed, so rejection cannot depend on
            # merely noticing a stale manifest self-hash.
            for mutate in (
                lambda value: value["binaries"]["wsl2-x86_64"].__setitem__("receipt_bytes", value["binaries"]["wsl2-x86_64"]["receipt_bytes"] + 1),
                lambda value: value["repository_inputs"]["native_build_workflow"].__setitem__("pinned_action_refs", ["actions/forged@main"]),
                lambda value: value.__setitem__("raw_inputs", []),
            ):
                forged_manifest, forged_hash = _reseal_manifest(manifest, mutate)
                forged_record = json.loads(raw)
                forged_record["successor_manifest_sha256"] = forged_hash
                with self.assertRaises(M.CustodyError):
                    M.validate_custody_record(M.encode_custody_record(forged_record), expected_manifest=forged_manifest, expected_manifest_sha256=forged_hash, now=NOW)
            hardlink = root / "hardlink.tar"
            hardlink.hardlink_to(path)
            hard_record = json.loads(raw)
            hard_record["transfer"]["locator"]["value"] = str(hardlink)
            with self.assertRaises(M.CustodyError):
                M.verify_and_materialize(M.encode_custody_record(hard_record), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=root / "hard-inv", now=NOW)
            swapped = root / "swapped"
            swapped.mkdir()
            (swapped / "bundle.tar").write_bytes(bundle)
            swapped_record = json.loads(raw)
            swapped_record["transfer"]["locator"]["value"] = str(swapped / "bundle.tar")
            other = root / "other"
            other.mkdir()
            (other / "bundle.tar").write_bytes(bundle)
            swapped.rename(root / "old-swapped")
            (root / "swapped").symlink_to(other, target_is_directory=True)
            with self.assertRaises(M.CustodyError):
                M.verify_and_materialize(M.encode_custody_record(swapped_record), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, invocation_dir=root / "swap-inv", now=NOW)
            mismatch = json.loads(raw)
            mismatch["transfer"]["expires_at"] = "2026-08-21T00:00:00Z"
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(M.encode_custody_record(mismatch), expected_manifest=manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)
            github_raw, github_manifest, _ = _record(_bundle(b"native", "native"), root, kind="github", candidate=b"native")
            github_mismatch = json.loads(github_raw)
            github_mismatch["transfer"]["artifact"]["retention_days"] = M.GITHUB_RETENTION_DAYS - 1
            with self.assertRaises(M.CustodyError):
                M.validate_custody_record(M.encode_custody_record(github_mismatch), expected_manifest=github_manifest, expected_manifest_sha256=FREEZE_HASH, now=NOW)


if __name__ == "__main__":
    unittest.main()

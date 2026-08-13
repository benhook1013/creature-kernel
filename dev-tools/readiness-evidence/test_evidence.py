import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("readiness_evidence", HERE / "evidence.py")
assert SPEC is not None and SPEC.loader is not None
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)
preflight = evidence._preflight_module()


class EvidenceTests(unittest.TestCase):
    def make_root(self, *, lock: bytes = b"version = 4\n", parent: Path | None = None) -> Path:
        root = Path(tempfile.mkdtemp(dir=parent))
        for path in evidence.IMPLEMENTATION_PATHS + evidence.ADMISSION_SUPPORT_PATHS:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(lock if path == "Cargo.lock" else path.encode("ascii"))
            target.chmod(0o755 if path.endswith("preflight.py") else 0o644)
        return root

    def metadata_for_root(self, root: Path) -> dict:
        core_id = f"path+file://{root}/crates/creature-kernel-core#0.1.0"
        dep_id = "registry+https://github.com/rust-lang/crates.io-index#dep@1.0.0"
        cli_id = f"path+file://{root}/crates/creature-kernel-cli#0.1.0"
        return {
            "workspace_root": str(root),
            "packages": [
                {
                    "id": cli_id,
                    "name": "creature-kernel-cli",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str(root / "crates/creature-kernel-cli/Cargo.toml"),
                    "targets": [
                        {
                            "crate_types": ["bin"],
                            "doc": True,
                            "doctest": False,
                            "edition": "2024",
                            "kind": ["bin"],
                            "name": "creature-kernel",
                            "src_path": str(root / "crates/creature-kernel-cli/src/main.rs"),
                            "test": True,
                        }
                    ],
                },
                {
                    "id": dep_id,
                    "name": "dep",
                    "version": "1.0.0",
                    "source": "registry+https://github.com/rust-lang/crates.io-index",
                    "license": "MIT",
                },
                {
                    "id": core_id,
                    "name": "creature-kernel-core",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str(root / "crates/creature-kernel-core/Cargo.toml"),
                    "targets": [
                        {
                            "crate_types": ["lib"],
                            "doc": True,
                            "doctest": True,
                            "edition": "2024",
                            "kind": ["lib"],
                            "name": "creature_kernel_core",
                            "src_path": str(root / "crates/creature-kernel-core/src/lib.rs"),
                            "test": True,
                        }
                    ],
                },
            ],
            "workspace_members": [core_id, cli_id],
            "resolve": {
                "nodes": [
                    {"id": cli_id, "features": [], "deps": [{"pkg": core_id}]},
                    {"id": dep_id, "features": ["zeta", "alpha", "alpha"], "deps": []},
                    {"id": core_id, "features": ["default"], "deps": [{"pkg": dep_id}]},
                ]
            },
        }

    def test_raw_binding_golden_framing(self):
        actual = evidence._raw_binding(
            "test.raw.v1",
            [("b", 0o100644, b"z"), ("a", 0o100755, b"")],
        )
        expected_bytes = (
            b"test.raw.v1\0"
            + struct.pack(">I", 1) + b"a" + struct.pack(">I", 0o100755) + struct.pack(">Q", 0)
            + struct.pack(">I", 1) + b"b" + struct.pack(">I", 0o100644) + struct.pack(">Q", 1) + b"z"
        )
        self.assertEqual(actual, hashlib.sha256(expected_bytes).hexdigest())

    def test_exact_paths_and_explicit_absence(self):
        root = self.make_root()
        result = evidence.implementation_binding(str(root))
        self.assertEqual(result["paths"], sorted(evidence.IMPLEMENTATION_PATHS))
        self.assertEqual(result["absent_paths"], [".cargo/config.toml"])

    def test_admission_support_exact_paths_and_changes_for_each_file(self):
        root = self.make_root()
        first = evidence.admission_support_binding(str(root))
        self.assertEqual(first["framing"], "ck.readiness-support-path-set.raw.v1")
        self.assertEqual(first["paths"], sorted(evidence.ADMISSION_SUPPORT_PATHS))
        for path in evidence.ADMISSION_SUPPORT_PATHS:
            (root / path).write_bytes((root / path).read_bytes() + b"changed")
            second = evidence.admission_support_binding(str(root))
            self.assertNotEqual(first["sha256"], second["sha256"], path)
            (root / path).write_bytes((root / path).read_bytes()[:-7])

    def test_implementation_byte_changes_only_implementation(self):
        root = self.make_root()
        first = evidence.implementation_binding(str(root))
        (root / "crates/creature-kernel-core/src/lib.rs").write_bytes(b"changed")
        second = evidence.implementation_binding(str(root))
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["paths"], second["paths"])
        self.assertEqual(first["absent_paths"], second["absent_paths"])

    def test_lock_change_changes_implementation_and_dependency(self):
        root = self.make_root(lock=b"version = 4\n[[package]]\nname = \"a\"\nversion = \"1\"\n")
        first_i = evidence.implementation_binding(str(root))
        first_d = evidence.dependency_closure(str(root), projection={"packages": []})
        (root / "Cargo.lock").write_bytes(b"version = 4\n[[package]]\nname = \"b\"\nversion = \"1\"\n")
        second_i = evidence.implementation_binding(str(root))
        second_d = evidence.dependency_closure(str(root), projection={"packages": []})
        self.assertNotEqual(first_i["sha256"], second_i["sha256"])
        self.assertNotEqual(first_d["sha256"], second_d["sha256"])

    def test_dependency_projection_features_checksum_graph_and_cli_exclusion(self):
        root = self.make_root(
            lock=(
                b"version = 4\n"
                b"[[package]]\nname = \"dep\"\nversion = \"1.0.0\"\n"
                b"source = \"registry+https://github.com/rust-lang/crates.io-index\"\n"
                b"checksum = \"abc\"\n"
            )
        )
        result = evidence.dependency_closure(str(root), metadata=self.metadata_for_root(root))
        packages = result["projection"]["packages"]
        self.assertEqual([package["name"] for package in packages], ["creature-kernel-core", "dep"])
        self.assertEqual(packages[0]["dependencies"], [packages[1]["id"]])
        self.assertEqual(packages[1]["features"], ["alpha", "alpha", "zeta"])
        self.assertEqual(packages[1]["checksum"], "abc")
        self.assertEqual(packages[1]["license"], "MIT")
        self.assertIsNone(packages[1]["links"])
        self.assertEqual(result["projection_json"].encode("ascii"), evidence._ascii_json(result["projection"]))
        self.assertEqual(json.loads(result["projection_json"]), result["projection"])

    def test_dependency_projection_is_checkout_location_independent(self):
        lock = (
            b"version = 4\n"
            b"[[package]]\nname = \"dep\"\nversion = \"1.0.0\"\n"
            b"source = \"registry+https://github.com/rust-lang/crates.io-index\"\n"
            b"checksum = \"abc\"\n"
        )
        first_root = self.make_root(lock=lock)
        second_root = self.make_root(lock=lock)
        first = evidence.dependency_closure(
            str(first_root), metadata=self.metadata_for_root(first_root)
        )
        second = evidence.dependency_closure(
            str(second_root), metadata=self.metadata_for_root(second_root)
        )
        self.assertEqual(first["projection"], second["projection"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(
            first["projection"]["packages"][0]["id"],
            "path+workspace://crates/creature-kernel-core#creature-kernel-core@0.1.0",
        )

    def test_unexpected_workspace_target_cannot_preserve_dependency_evidence(self):
        root = self.make_root(lock=b"version = 4\n")
        metadata = self.metadata_for_root(root)
        metadata["packages"][0]["targets"].append(
            {
                "crate_types": ["bin"],
                "doc": True,
                "doctest": False,
                "edition": "2024",
                "kind": ["bin"],
                "name": "unexpected",
                "src_path": str(root / "crates/creature-kernel-cli/src/unexpected.rs"),
                "test": True,
            }
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence.dependency_closure(str(root), metadata=metadata)

    def test_target_projection_is_bound_and_exact(self):
        root = self.make_root(lock=b"version = 4\n")
        first = evidence.dependency_closure(str(root), metadata=self.metadata_for_root(root))
        metadata = self.metadata_for_root(root)
        metadata["packages"][0]["targets"][0]["src_path"] = str(
            root / "crates/creature-kernel-cli/src/renamed.rs"
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence.dependency_closure(str(root), metadata=metadata)
        self.assertIn("targets", first["projection"])

    def test_sanitized_environment_discards_build_flags_and_wrappers(self):
        root = self.make_root()
        home = Path(tempfile.mkdtemp())
        ambient = {
            "HOME": str(home),
            "CARGO_HOME": str(home / "ambient-cargo"),
            "CARGO_BUILD_TARGET": "bad-target",
            "CARGO_PROFILE_DEV_OPT_LEVEL": "3",
            "RUSTFLAGS": "--cfg ambient",
            "RUSTC_WRAPPER": "/tmp/wrapper",
            "RUSTUP_TOOLCHAIN": "stable",
            "CC": "/tmp/cc",
            "CFLAGS": "-Dambient",
            "PROFILE": "release",
        }
        with patch.dict(os.environ, ambient, clear=False):
            child = evidence.sanitized_environment(str(root))
        self.assertEqual(child["CARGO_HOME"], str(home / ".cargo"))
        self.assertEqual(child["RUSTUP_TOOLCHAIN"], evidence.TOOLCHAIN)
        self.assertNotIn("CARGO_BUILD_TARGET", child)
        self.assertNotIn("CARGO_PROFILE_DEV_OPT_LEVEL", child)
        self.assertNotIn("RUSTFLAGS", child)
        self.assertNotIn("RUSTC_WRAPPER", child)
        self.assertNotIn("CC", child)
        self.assertNotIn("CFLAGS", child)
        self.assertNotIn("PROFILE", child)

    def test_config_files_fail_closed_before_bound_run(self):
        root = self.make_root()
        home = Path(tempfile.mkdtemp())
        (root / ".cargo").mkdir()
        (root / ".cargo/config.toml").write_text("[build]\ntarget = \"bad\"\n")
        with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
            with patch.object(evidence.subprocess, "run") as run:
                with self.assertRaises(evidence.EvidenceError):
                    evidence.run_bound_checks(str(root))
        run.assert_not_called()

        (root / ".cargo/config.toml").unlink()
        (home / ".cargo").mkdir()
        (home / ".cargo/config").write_text("[profile.dev]\nopt-level = 3\n")
        with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
            with patch.object(evidence.subprocess, "run") as run:
                with self.assertRaises(evidence.EvidenceError):
                    evidence.run_bound_checks(str(root))
        run.assert_not_called()

        base = Path(tempfile.mkdtemp())
        ancestor_root = self.make_root(parent=base)
        (base / ".cargo").mkdir()
        (base / ".cargo/config.toml").write_text("[build]\ntarget = \"bad\"\n")
        with patch.dict(os.environ, {"HOME": str(Path(tempfile.mkdtemp()))}, clear=False):
            with self.assertRaises(evidence.EvidenceError):
                evidence.sanitized_environment(str(ancestor_root))

    def test_bound_run_cannot_inherit_rustflags_or_profile_overrides(self):
        root = self.make_root()
        home = Path(tempfile.mkdtemp())
        ambient = {
            "HOME": str(home),
            "RUSTFLAGS": "--cfg ambient",
            "CARGO_PROFILE_DEV_OPT_LEVEL": "3",
            "CARGO_BUILD_TARGET": "bad-target",
        }
        with patch.dict(os.environ, ambient, clear=False):
            with patch.object(evidence.subprocess, "run") as run:
                evidence.run_bound_checks(str(root))
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            child = call.kwargs["env"]
            self.assertNotIn("RUSTFLAGS", child)
            self.assertNotIn("CARGO_PROFILE_DEV_OPT_LEVEL", child)
            self.assertNotIn("CARGO_BUILD_TARGET", child)
            args = call.args[0]
            self.assertEqual(args[args.index("--target") + 1], evidence.TARGET)

    def test_metadata_uses_sanitized_target_filtered_request(self):
        root = self.make_root()
        metadata = self.metadata_for_root(root)
        result = type("Result", (), {"stdout": json.dumps(metadata)})()
        home = Path(tempfile.mkdtemp())
        with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
            with patch.object(evidence.subprocess, "run", return_value=result) as run:
                actual = evidence._cargo_metadata(str(root))
        self.assertEqual(actual, metadata)
        args = run.call_args.args[0]
        self.assertIn("--locked", args)
        self.assertIn("--offline", args)
        self.assertEqual(args[args.index("--filter-platform") + 1], evidence.TARGET)
        child = run.call_args.kwargs["env"]
        self.assertEqual(child["RUSTUP_TOOLCHAIN"], evidence.TOOLCHAIN)
        self.assertNotIn("RUSTFLAGS", child)

    def test_resolved_projection_change_changes_dependency_closure(self):
        root = self.make_root(lock=b"version = 4\n")
        first = evidence.dependency_closure(
            str(root), projection={"packages": [{"id": "a", "features": ["one"]}]}
        )
        second = evidence.dependency_closure(
            str(root), projection={"packages": [{"id": "a", "features": ["two"]}]}
        )
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_shared_reader_rejects_symlink_hardlink_mode_and_escape(self):
        root = self.make_root()
        root_fd = preflight._open_root(str(root))
        try:
            outside = root.parent / "outside.txt"
            outside.write_bytes(b"outside")
            (root / "symlink.txt").symlink_to(outside)
            with self.assertRaises(preflight.PreflightError):
                preflight._read_relative(root_fd, "symlink.txt")
            os.link(root / "Cargo.toml", root / "hardlink.txt")
            with self.assertRaises(preflight.PreflightError):
                preflight._read_relative(root_fd, "hardlink.txt")
            (root / "badmode.txt").write_bytes(b"bad")
            (root / "badmode.txt").chmod(0o600)
            with self.assertRaises(preflight.PreflightError):
                preflight._read_relative(root_fd, "badmode.txt")
            with self.assertRaises(preflight.PreflightError):
                evidence._read_binding_file(root_fd, "../outside.txt")
        finally:
            os.close(root_fd)

    def test_build_request_is_stable_and_explicit(self):
        refs = ("a" * 64, "b" * 64, "c" * 64)
        first = evidence.build_request(*refs)
        second = evidence.build_request(*refs)
        self.assertEqual(first, second)
        self.assertEqual(first["target"], "x86_64-unknown-linux-gnu")
        self.assertEqual(first["toolchain"], "1.97.1")
        self.assertEqual(first["features"], ["default"])
        self.assertEqual(first["environment_policy"], evidence.ENVIRONMENT_POLICY)
        self.assertEqual(first["cargo_config_policy"], evidence.CARGO_CONFIG_POLICY)
        self.assertEqual(first["target_projection_policy"], evidence.TARGET_PROJECTION_POLICY)
        self.assertEqual(first["commands"], evidence.COMMANDS)
        self.assertTrue(all("--target x86_64-unknown-linux-gnu" in command for command in first["commands"]))
        self.assertEqual(first["implementation_sha256"], refs[0])
        self.assertEqual(first["dependency_closure_sha256"], refs[1])
        self.assertEqual(first["admission_support_sha256"], refs[2])
        for index in range(3):
            changed = list(refs)
            changed[index] = "d" * 64
            self.assertNotEqual(first["sha256"], evidence.build_request(*changed)["sha256"])


if __name__ == "__main__":
    unittest.main()

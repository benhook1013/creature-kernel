from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import struct
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("preflight.py")
SPEC = importlib.util.spec_from_file_location("fixture_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
run_exact = preflight.run
preflight.run = lambda root, manifest: preflight._run(
    root, manifest, enforce_exact_r2=False
)


def _resource(profile_id: str, max_source_bytes: int) -> dict:
    return {
        "id": profile_id,
        "max_source_bytes": max_source_bytes,
        "max_nesting_depth": 64,
        "max_json_values": 8192,
        "max_object_members": 4096,
        "max_array_items": 4096,
        "max_string_bytes": 16384,
        "max_number_token_bytes": 256,
        "max_diagnostics": 64,
    }


def _raw_binding(entries: list[tuple[str, int, bytes]]) -> str:
    h = hashlib.sha256(b"ck.path-set.raw.v1\0")
    for path, mode, content in sorted(entries, key=lambda e: e[0].encode()):
        path_bytes = path.encode()
        h.update(struct.pack(">I", len(path_bytes)))
        h.update(path_bytes)
        h.update(struct.pack(">I", mode))
        h.update(struct.pack(">Q", len(content)))
        h.update(content)
    return h.hexdigest()


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "schemas").mkdir()
        (self.root / "fixtures").mkdir()
        self.schema = b'{"$schema":"https://json-schema.org/draft/2020-12/schema"}\n'
        (self.root / "schemas/body.json").write_bytes(self.schema)
        os.chmod(self.root / "schemas/body.json", 0o644)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _manifest(self, fixtures: list[dict], *, resources=None) -> dict:
        return {
            "contract": {"family": "creature-kernel.fixture-manifest", "revision": 1},
            "suite": {"id": "readiness-2", "kind": "body-document-admission"},
            "schema": {
                "path": "schemas/body.json",
                "sha256": hashlib.sha256(self.schema).hexdigest(),
                "draft": "2020-12",
                "contract_family": "creature-kernel.body",
                "revision": 1,
            },
            "profiles": {
                "diagnostic": {"id": "ck.diagnostic.r2"},
                "resources": resources if resources is not None else [
                    _resource("ck.resource.body.r2", 65536),
                    _resource("ck.resource.body.r2-tight", 128),
                ],
            },
            "fixtures": fixtures,
        }

    def _fixture(self, fixture_id="minimal", path="fixtures/minimal.body", content=b"body") -> dict:
        (self.root / path).write_bytes(content)
        os.chmod(self.root / path, 0o644)
        return {
            "id": fixture_id,
            "path": path,
            "sha256": hashlib.sha256(content).hexdigest(),
            "purpose": "minimal valid envelope",
            "provenance": {"kind": "authored", "source": "test", "license": "project"},
            "operation": "validate",
            "profiles": {"diagnostic": "ck.diagnostic.r2", "resource": "ck.resource.body.r2"},
            "expected": {"status": "success", "processing_complete": True, "diagnostics_complete": True},
        }

    def _write_manifest(self, value: dict) -> Path:
        path = self.root / "manifest.json"
        path.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
        os.chmod(path, 0o644)
        return path

    def test_valid_tree_and_deterministic_binding_vector(self) -> None:
        fixture = self._fixture()
        manifest = self._manifest([fixture])
        path = self._write_manifest(manifest)
        result = preflight.run(str(self.root), "manifest.json")
        expected = _raw_binding([
            ("manifest.json", 0o100644, path.read_bytes()),
            ("schemas/body.json", 0o100644, self.schema),
            ("fixtures/minimal.body", 0o100644, b"body"),
        ])
        self.assertEqual(result["path_set"], {"framing": "ck.path-set.raw.v1", "sha256": expected})
        self.assertEqual(result["manifest_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(preflight.run(str(self.root), "manifest.json"), result)

    def test_duplicate_json_member(self) -> None:
        self._fixture()
        path = self.root / "manifest.json"
        raw = json.dumps(self._manifest([self._fixture()]), separators=(",", ":"))
        path.write_bytes(raw.replace('"fixtures":', '"fixtures":', 1).encode() + b"\n")
        # Place a duplicate at the top level without relying on a JSON encoder.
        text = path.read_text()
        path.write_text(text[:-2] + ',"suite":{"id":"x","kind":"body-document-admission"}}\n')
        with self.assertRaisesRegex(preflight.PreflightError, "duplicate JSON member"):
            preflight.run(str(self.root), "manifest.json")

    def test_unsafe_path_and_symlink(self) -> None:
        fixture = self._fixture(path="fixtures/real.body")
        fixture["path"] = "../escape"
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaises(preflight.PreflightError):
            preflight.run(str(self.root), "manifest.json")
        os.unlink(self.root / "manifest.json")
        os.symlink("real.body", self.root / "fixtures/link.body")
        fixture = self._fixture(path="fixtures/real.body")
        fixture["path"] = "fixtures/link.body"
        fixture["sha256"] = hashlib.sha256(b"body").hexdigest()
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "path file is unavailable"):
            preflight.run(str(self.root), "manifest.json")

    def test_non_ascii_and_space_paths_are_rejected(self) -> None:
        for unsafe in ("fixtures/naïve.body", "fixtures/not safe.body"):
            with self.subTest(path=unsafe):
                fixture = self._fixture()
                fixture["path"] = unsafe
                self._write_manifest(self._manifest([fixture]))
                with self.assertRaisesRegex(preflight.PreflightError, "safe ASCII"):
                    preflight.run(str(self.root), "manifest.json")

    def test_hardlink_and_bad_mode(self) -> None:
        fixture = self._fixture()
        os.link(self.root / "fixtures/minimal.body", self.root / "fixtures/other.body")
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "multiple links"):
            preflight.run(str(self.root), "manifest.json")
        os.unlink(self.root / "fixtures/other.body")
        os.chmod(self.root / "fixtures/minimal.body", 0o600)
        with self.assertRaisesRegex(preflight.PreflightError, "mode"):
            preflight.run(str(self.root), "manifest.json")

    def test_hash_mismatch_duplicate_id_path_unknown_field_and_profile(self) -> None:
        fixture = self._fixture()
        fixture["sha256"] = "0" * 64
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "fixture hash mismatch"):
            preflight.run(str(self.root), "manifest.json")
        fixture = self._fixture()
        self._write_manifest(self._manifest([fixture, dict(fixture)]))
        with self.assertRaisesRegex(preflight.PreflightError, "duplicate fixture ID"):
            preflight.run(str(self.root), "manifest.json")
        fixture = self._fixture(fixture_id="other")
        fixture["path"] = "fixtures/minimal.body"
        self._write_manifest(self._manifest([self._fixture(), fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "duplicate fixture path"):
            preflight.run(str(self.root), "manifest.json")
        fixture = self._fixture()
        fixture["unexpected"] = 1
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "unknown or missing"):
            preflight.run(str(self.root), "manifest.json")
        fixture = self._fixture()
        fixture["profiles"]["resource"] = "missing"
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "does not resolve"):
            preflight.run(str(self.root), "manifest.json")

    def test_resource_over_budget_only_expected_limit_is_allowed(self) -> None:
        content = b"x" * 129
        fixture = self._fixture(content=content)
        fixture["profiles"]["resource"] = "ck.resource.body.r2-tight"
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "does not match"):
            preflight.run(str(self.root), "manifest.json")
        fixture = self._fixture(content=content)
        fixture["profiles"]["resource"] = "ck.resource.body.r2-tight"
        fixture["expected"] = {
            "status": "resource-limit",
            "processing_complete": False,
            "diagnostics_complete": True,
            "primary_diagnostic": "ck.resource.source-bytes",
        }
        self._write_manifest(self._manifest([fixture]))
        self.assertEqual(preflight.run(str(self.root), "manifest.json")["path_set"]["framing"], "ck.path-set.raw.v1")

    def test_under_budget_resource_limit_is_rejected(self) -> None:
        fixture = self._fixture()
        fixture["profiles"]["resource"] = "ck.resource.body.r2-tight"
        fixture["expected"] = {
            "status": "resource-limit",
            "processing_complete": False,
            "diagnostics_complete": True,
            "primary_diagnostic": "ck.resource.source-bytes",
        }
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "does not match"):
            preflight.run(str(self.root), "manifest.json")

    def test_exact_r2_profiles(self) -> None:
        fixture = self._fixture()
        wrong_number_limit = [
            _resource("ck.resource.body.r2", 65536),
            _resource("ck.resource.body.r2-tight", 128),
        ]
        wrong_number_limit[0]["max_number_token_bytes"] = 255
        wrong_diagnostic_limit = [
            _resource("ck.resource.body.r2", 65536),
            _resource("ck.resource.body.r2-tight", 128),
        ]
        wrong_diagnostic_limit[1]["max_diagnostics"] = 63
        cases = [
            ([_resource("ck.resource.body.r2", 65535),
              _resource("ck.resource.body.r2-tight", 128)],
             "resource profiles"),
            ([_resource("ck.resource.body.r2", 65536),
              _resource("ck.resource.body.r2-tight", 127)],
             "resource profiles"),
            ([_resource("ck.resource.body.r2", 65536)],
             "resource profiles"),
            ([_resource("ck.resource.body.r2", 65536),
              _resource("ck.resource.body.r2-tight", 128),
              _resource("ck.resource.body.extra", 256)],
             "resource profiles"),
            (wrong_number_limit, "resource profiles"),
            (wrong_diagnostic_limit, "resource profiles"),
        ]
        for resources, message in cases:
            with self.subTest(resources=resources):
                self._write_manifest(self._manifest([fixture], resources=resources))
                with self.assertRaisesRegex(preflight.PreflightError, message):
                    preflight.run(str(self.root), "manifest.json")
        manifest = self._manifest([fixture])
        manifest["profiles"]["diagnostic"]["id"] = "ck.diagnostic.other"
        self._write_manifest(manifest)
        with self.assertRaisesRegex(preflight.PreflightError, "diagnostic profile"):
            preflight.run(str(self.root), "manifest.json")

    def test_primary_diagnostic_must_be_registered(self) -> None:
        fixture = self._fixture()
        fixture["expected"] = {
            "status": "invalid-source",
            "processing_complete": True,
            "diagnostics_complete": True,
            "primary_diagnostic": "ck.source.not-registered",
        }
        self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "R2 registry"):
            preflight.run(str(self.root), "manifest.json")

    def test_exact_r2_suite_and_schema_are_pinned(self) -> None:
        fixture = self._fixture()
        path = self._write_manifest(self._manifest([fixture]))
        with self.assertRaisesRegex(preflight.PreflightError, "suite.id"):
            run_exact(str(self.root), path.name)
        manifest = self._manifest([fixture])
        manifest["suite"]["id"] = "body-document-readiness-2"
        self._write_manifest(manifest)
        with self.assertRaisesRegex(preflight.PreflightError, "schema.path"):
            run_exact(str(self.root), path.name)

    def test_exact_r2_fixture_id_set_is_pinned(self) -> None:
        fixtures = []
        for index, fixture_id in enumerate(sorted(preflight.R2_FIXTURE_IDS)):
            fixture = self._fixture(
                fixture_id=fixture_id,
                path=f"fixtures/item-{index}.body",
            )
            fixtures.append(fixture)
        manifest = self._manifest(fixtures)
        manifest["suite"]["id"] = preflight.R2_SUITE_ID
        manifest["schema"]["path"] = preflight.R2_SCHEMA_PATH
        preflight._validate_manifest(manifest, enforce_exact_r2=True)
        manifest["fixtures"].pop()
        with self.assertRaisesRegex(preflight.PreflightError, "exact R2 corpus"):
            preflight._validate_manifest(manifest, enforce_exact_r2=True)


if __name__ == "__main__":
    unittest.main()

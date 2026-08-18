from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import preregister


PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE.parents[2]
MANIFEST = PACKAGE / "preregistration.json"
SCRIPT = PACKAGE / "scripts" / "preregister.py"


def _fresh_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _write_manifest(root: Path, value: object, name: str = "manifest.json") -> Path:
    path = root / name
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
    return path


class PreregisterTests(unittest.TestCase):
    def test_help_and_default_paths_are_safe(self) -> None:
        help_result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("preflight", help_result.stdout)
        self.assertNotIn("result.json", help_result.stdout)

        default_result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPOSITORY_ROOT,
        )
        self.assertEqual(default_result.returncode, 0, default_result.stderr)
        plan = json.loads(default_result.stdout)
        self.assertFalse(plan["execution_permitted"])
        self.assertFalse(plan["result_or_receipt_created"])
        self.assertEqual(plan["lifecycle"], "draft")

    def test_valid_draft_preflight_is_deterministic_and_portable(self) -> None:
        first = preregister.build_plan(MANIFEST)
        second = preregister.build_plan(MANIFEST)
        self.assertEqual(first, second)
        self.assertEqual(first["corpus_roles"]["role_order"], ["development", "held-out", "adversarial"])
        self.assertEqual(
            [item["id"] for item in first["declared_file_identities"]],
            ["dr-0008-revision-14", "numeric-frame-research-design", "exp-0002-phase-one-boundary"],
        )
        self.assertEqual(len(first["boundary_fixture_roles"]), 5)
        self.assertEqual(first["manifest_identity"]["path"], "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/preregistration.json")
        self.assertFalse(Path(first["manifest_identity"]["path"]).is_absolute())
        self.assertEqual(first["filesystem_scope"], "controlled-local-change-detection-not-adversarial-filesystem-proof")

    def test_unknown_and_missing_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            unknown = _fresh_manifest()
            unknown["unexpected"] = True
            with self.assertRaisesRegex(preregister.PreflightError, "unknown=unexpected"):
                preregister.build_plan(_write_manifest(root, unknown, "unknown.json"))

            missing = _fresh_manifest()
            del missing["rules"]
            with self.assertRaisesRegex(preregister.PreflightError, "missing=rules"):
                preregister.build_plan(_write_manifest(root, missing, "missing.json"))

    def test_every_binding_remains_draft_or_unbound(self) -> None:
        cases = (
            ("protocol_binding", "protocol_binding.state must be draft"),
            ("candidate_binding", "candidate_binding.state must be unbound"),
            ("profile_binding", "profile_binding must remain an unbound"),
            ("semantic_budget_binding", "semantic_budget_binding must remain unbound"),
            ("validation_binding", "validation_binding must remain unbound"),
            ("corpus_binding", "corpus_binding.state must remain unbound"),
            ("activation_bindings", "activation_bindings.state must remain unbound"),
            ("result_binding", "result_binding.state must be unbound"),
            ("receipt_binding", "receipt_binding.state must be unbound"),
        )
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            for index, (field, message) in enumerate(cases):
                with self.subTest(field=field):
                    value = _fresh_manifest()
                    value[field]["state"] = "complete"
                    with self.assertRaisesRegex(preregister.PreflightError, message):
                        preregister.build_plan(_write_manifest(root, value, f"complete-{index}.json"))

            lifecycle = _fresh_manifest()
            lifecycle["lifecycle"] = "complete"
            with self.assertRaisesRegex(preregister.PreflightError, "lifecycle=draft"):
                preregister.build_plan(_write_manifest(root, lifecycle, "complete-lifecycle.json"))

    def test_protocol_and_corpus_metadata_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            protocol = _fresh_manifest()
            protocol["protocol_binding"]["id"] = "ck.r3.another-draft"
            with self.assertRaisesRegex(preregister.PreflightError, "exact unbound-content draft identity"):
                preregister.build_plan(_write_manifest(root, protocol, "protocol.json"))

            order = _fresh_manifest()
            order["corpus_binding"]["role_order"] = ["held-out", "development", "adversarial"]
            with self.assertRaisesRegex(preregister.PreflightError, "corpus role order"):
                preregister.build_plan(_write_manifest(root, order, "order.json"))

            tuning = _fresh_manifest()
            tuning["corpus_binding"]["roles"][1]["tuning_allowed"] = True
            with self.assertRaisesRegex(preregister.PreflightError, "held-out metadata"):
                preregister.build_plan(_write_manifest(root, tuning, "tuning.json"))

    def test_reference_set_and_aggregate_budget_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            changed = _fresh_manifest()
            changed["content_references"][0]["role"] = "different-role"
            with self.assertRaisesRegex(preregister.PreflightError, "identity/path/role set differs"):
                preregister.build_plan(_write_manifest(root, changed, "changed-reference.json"))

            extra = _fresh_manifest()
            extra["content_references"].append(extra["content_references"][0].copy())
            with self.assertRaisesRegex(preregister.PreflightError, "exactly the three"):
                preregister.build_plan(_write_manifest(root, extra, "extra-reference.json"))

            oversized = _fresh_manifest()
            for reference in oversized["content_references"]:
                reference["expected_bytes"] = preregister.MAX_REFERENCE_BYTES
            with self.assertRaisesRegex(preregister.PreflightError, "aggregate byte bound"):
                preregister.build_plan(_write_manifest(root, oversized, "aggregate-reference.json"))

    def test_fixture_definitions_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            profile = _fresh_manifest()
            profile["boundary_fixtures"][2]["request_profile"] = "supported-digitigrade"
            with self.assertRaisesRegex(preregister.PreflightError, "exact DR-0008 Revision 14 definition"):
                preregister.build_plan(_write_manifest(root, profile, "fixture-profile.json"))

            constraints = _fresh_manifest()
            constraints["boundary_fixtures"][4]["graph_constraints"].pop()
            with self.assertRaisesRegex(preregister.PreflightError, "exact DR-0008 Revision 14 definition"):
                preregister.build_plan(_write_manifest(root, constraints, "fixture-constraints.json"))

            complete = _fresh_manifest()
            complete["boundary_fixtures"][0]["state"] = "complete"
            with self.assertRaisesRegex(preregister.PreflightError, "content-unbound"):
                preregister.build_plan(_write_manifest(root, complete, "fixture-complete.json"))

    def test_malformed_null_arrays_fail_cleanly(self) -> None:
        cases = (
            (("corpus_binding", "role_order"), "corpus_binding.role_order must be an array"),
            (("corpus_binding", "roles"), "corpus_binding.roles must be an array"),
            (("boundary_fixtures",), "boundary_fixtures must be an array"),
            (("rules", "outcomes"), "rules.outcomes must be an array"),
            (("rules", "evidence_lineage"), "rules.evidence_lineage must be an array"),
            (("content_references",), "content_references must be an array"),
        )
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            for index, (path, message) in enumerate(cases):
                with self.subTest(path=path):
                    value = _fresh_manifest()
                    cursor = value
                    for component in path[:-1]:
                        cursor = cursor[component]
                    cursor[path[-1]] = None
                    with self.assertRaisesRegex(preregister.PreflightError, message):
                        preregister.build_plan(_write_manifest(root, value, f"null-{index}.json"))

    def test_deep_and_oversized_manifests_fail_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            deep = root / "deep.json"
            deep.write_text("{\"nested\":" * (preregister.MAX_JSON_DEPTH + 2) + "null" + "}" * (preregister.MAX_JSON_DEPTH + 2), encoding="utf-8")
            with self.assertRaisesRegex(preregister.PreflightError, "nesting exceeds"):
                preregister.build_plan(deep)

            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b" " * preregister.MAX_MANIFEST_BYTES + b"}")
            with self.assertRaisesRegex(preregister.PreflightError, "manifest exceeds"):
                preregister.build_plan(oversized)

    def test_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            changed = _fresh_manifest()
            changed["content_references"][0]["expected_sha256"] = "0" * 64
            with self.assertRaisesRegex(preregister.PreflightError, "content reference changed"):
                preregister.build_plan(_write_manifest(root, changed, "hash-mismatch.json"))

    def test_in_repository_symlink_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as temp:
            root = Path(temp)
            target = root / "target.txt"
            target.write_bytes(b"source\n")
            linked_directory = root / "linked"
            os.symlink(root, linked_directory, target_is_directory=True)
            relative = (linked_directory / "target.txt").relative_to(REPOSITORY_ROOT).as_posix()
            reference = {
                "id": "symlink-probe",
                "path": relative,
                "role": "test-probe",
                "expected_sha256": hashlib.sha256(b"source\n").hexdigest(),
                "expected_bytes": 7,
            }
            with self.assertRaisesRegex(preregister.PreflightError, "symlink component"):
                preregister._stream_identity(REPOSITORY_ROOT, reference)

    def test_execution_is_explicitly_rejected(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--execute"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("execution is intentionally unavailable", result.stderr)


if __name__ == "__main__":
    unittest.main()

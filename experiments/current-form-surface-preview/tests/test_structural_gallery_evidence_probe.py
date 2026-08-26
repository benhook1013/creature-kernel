#!/usr/bin/env python3
"""Focused tests for the immutable structural-gallery evidence projection."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parents[1]
VISUAL_REVIEW = HERE.parents[3] / "dev-tools" / "visual-review"
sys.path.insert(0, str(EXPERIMENT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = load_module("structural_gallery_evidence_probe", EXPERIMENT / "structural_gallery_evidence_probe.py")
publication_tests = load_module(
    "structural_embodiment_publication_fixtures",
    VISUAL_REVIEW / "tests" / "test_structural_embodiment_publication.py",
)
publisher = publication_tests.publisher


class StructuralGalleryEvidenceProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="structural-gallery-evidence-probe-")
        cls.base = Path(cls.temp.name) / "gallery"
        cls.base.mkdir()
        publication_tests.StructuralEmbodimentPublicationTests._write_gallery(cls.base)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="structural-gallery-evidence-case-")
        self.root = Path(self.temp.name)
        self.gallery = self.root / "gallery"
        shutil.copytree(self.base, self.gallery)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def manifest(self) -> dict[str, object]:
        return json.loads((self.gallery / publisher.MANIFEST_FILE).read_text(encoding="utf-8"))

    def write_manifest(self, value: dict[str, object]) -> None:
        (self.gallery / publisher.MANIFEST_FILE).write_text(
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def test_successful_projection_contains_only_immutable_gallery_evidence(self) -> None:
        view = probe.project_structural_gallery_evidence(self.gallery)
        self.assertIsNotNone(view)
        assert view is not None
        self.assertEqual(view.profile_ids, tuple(publisher.PROFILE_IDS))
        self.assertEqual(view.pose_id, publisher.POSE_ID)
        self.assertEqual(view.projection_contract, probe.PROJECTION_CONTRACT)
        self.assertEqual(view.pose_artifact.path, publisher.POSE_FILE)
        self.assertEqual(view.candidate_table.path, publisher.CANDIDATE_FILE)
        self.assertEqual(view.source_manifest.path, f"{publisher.SOURCES_DIR}/{publisher.SOURCE_MANIFEST_FILE}")
        self.assertEqual(len(view.profiles), 4)
        self.assertEqual(view.profiles[0].neutral_mesh.path, f"{view.profile_ids[0]}/neutral.ply")
        self.assertEqual(view.profiles[0].skeleton.path, f"{view.profile_ids[0]}/skeleton.json")
        self.assertEqual(view.profiles[0].metrics.neutral_vertex_count, 18)
        self.assertEqual(view.unavailable_evidence, probe.UNAVAILABLE_EVIDENCE)
        self.assertIn(probe.UNAVAILABLE_ORIGINAL_INSPECT_STRUCTURE_BYTES, view.unavailable_evidence)
        self.assertIn(probe.UNAVAILABLE_PER_VERTEX_SEMANTIC_LABELS, view.unavailable_evidence)
        self.assertEqual(
            {field.name for field in fields(view)} & set(probe.EXCLUDED_RENDERED_EVIDENCE),
            set(),
        )
        self.assertTrue(
            all(
                not artifact.path.endswith(publisher.GALLERY_FILE)
                for profile in view.profiles
                for artifact in (
                    profile.neutral_mesh,
                    profile.posed_mesh,
                    profile.skeleton,
                    profile.weights,
                    profile.neutral_proxies,
                    profile.posed_proxies,
                )
            )
        )
        self.assertIsInstance(view.lineage, tuple)
        self.assertIsInstance(view.global_world_bound[0], tuple)
        with self.assertRaises(FrozenInstanceError):
            view.pose_id = "changed"  # type: ignore[misc]
        self.assertEqual(hash(view), hash(view))

    def test_projection_is_deterministic_and_two_profile_identities_are_distinct(self) -> None:
        first = probe.project_structural_gallery_evidence(self.gallery)
        second = probe.load_structural_gallery_evidence(self.gallery)
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        assert first is not None
        identities = {profile.identity.candidate_profile_sha256 for profile in first.profiles}
        self.assertEqual(len(identities), 4)
        self.assertNotEqual(first.profiles[0].profile_id, first.profiles[1].profile_id)
        self.assertNotEqual(
            first.profiles[0].identity.source_document,
            first.profiles[1].identity.source_document,
        )

    def test_review_session_is_not_a_gallery(self) -> None:
        session = self.root / "reviews" / "probe-session"
        (session / "assets").mkdir(parents=True)
        (session / "review.json").write_text("{}", encoding="utf-8")
        self.assertIsNone(probe.project_structural_gallery_evidence(session))

    def test_expected_validator_rejection_returns_no_view(self) -> None:
        rejection_type = publisher.StructuralEmbodimentPublishError

        def reject(_: Path):
            raise rejection_type("expected rejected gallery")

        with patch.object(probe, "_load_validator", return_value=(reject, rejection_type)):
            self.assertIsNone(probe.project_structural_gallery_evidence(self.gallery))

    def test_unexpected_validator_failure_surfaces(self) -> None:
        rejection_type = publisher.StructuralEmbodimentPublishError

        def fail(_: Path):
            raise RuntimeError("unexpected validator failure")

        with patch.object(probe, "_load_validator", return_value=(fail, rejection_type)):
            with self.assertRaisesRegex(RuntimeError, "unexpected validator failure"):
                probe.project_structural_gallery_evidence(self.gallery)

    def test_validator_import_failure_surfaces(self) -> None:
        with patch.object(probe, "_load_validator", side_effect=ModuleNotFoundError("missing validator dependency")):
            with self.assertRaisesRegex(ModuleNotFoundError, "missing validator dependency"):
                probe.project_structural_gallery_evidence(self.gallery)

    def test_validator_loader_works_in_clean_isolated_process(self) -> None:
        probe_path = json.dumps(str(EXPERIMENT / "structural_gallery_evidence_probe.py"))
        child_code = f"""
import importlib.util
import sys
from pathlib import Path

path = Path({probe_path})
spec = importlib.util.spec_from_file_location("clean_structural_gallery_evidence_probe", path)
if spec is None or spec.loader is None:
    raise SystemExit("could not create probe import spec")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
validator, rejection_type = module._load_validator()
assert validator.__name__ == "validate_structural_embodiment_gallery"
assert rejection_type.__name__ == "StructuralEmbodimentPublishError"
"""
        result = subprocess.run(
            [sys.executable, "-I", "-c", child_code],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_tampering_returns_no_view_from_shared_validator(self) -> None:
        value = self.manifest()
        value["profile_ids"] = list(reversed(value["profile_ids"]))
        self.write_manifest(value)
        self.assertIsNone(probe.project_structural_gallery_evidence(self.gallery))

    def test_artifact_tampering_returns_no_view_from_shared_validator(self) -> None:
        path = self.gallery / publisher.PROFILE_IDS[0] / "neutral.ply"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertIsNone(probe.project_structural_gallery_evidence(self.gallery))


if __name__ == "__main__":
    unittest.main()

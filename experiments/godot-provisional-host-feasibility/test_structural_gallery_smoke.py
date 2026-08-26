from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
REPOSITORY_ROOT = HERE.parents[2]
GALLERY = Path("/tmp/ck-godot-structural-inputs/gallery")
LAUNCHER = EXPERIMENT / "launch_godot_4_7_2.sh"
DEFAULTS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_module("structural_gallery_smoke_under_test", EXPERIMENT / "run_structural_gallery_smoke.py")


def integration_available() -> bool:
    if not GALLERY.is_dir() or not LAUNCHER.is_file() or not LAUNCHER.stat().st_mode & 0o111:
        return False
    try:
        result = subprocess.run([str(LAUNCHER), "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return False
    return result.returncode == 0 and smoke.EXPECTED_GODOT_VERSION in result.stdout


class StructuralGallerySmokePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-godot-structural-smoke-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def report_path(self) -> Path:
        return self.root / "report.json"

    def assert_rejected_before_godot(self, gallery: Path, profile_ids=DEFAULTS) -> None:
        with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot was invoked after preflight rejection")):
            with self.assertRaises(smoke.SmokeError):
                smoke.run_smoke(gallery, profile_ids, self.report_path())

    def require_gallery(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"cached completed gallery unavailable: {GALLERY}")

    def test_profile_selection_accepts_two_distinct_frozen_ids_without_gallery(self) -> None:
        self.assertEqual(smoke._validate_profile_ids(DEFAULTS), DEFAULTS)

    def test_duplicate_profile_rejected_without_gallery(self) -> None:
        with self.assertRaisesRegex(smoke.SmokeError, "duplicate profile identity"):
            smoke._validate_profile_ids((DEFAULTS[0], DEFAULTS[0]))

    def test_unknown_profile_rejected_without_gallery(self) -> None:
        with self.assertRaisesRegex(smoke.SmokeError, "unknown frozen profile identity"):
            smoke._validate_profile_ids((DEFAULTS[0], "not-a-frozen-profile"))

    def test_absolute_path_and_report_parent_preconditions_run_without_gallery(self) -> None:
        with patch.object(smoke, "_load_probe", side_effect=AssertionError("probe was reached after relative gallery rejection")):
            with self.assertRaisesRegex(smoke.SmokeError, "gallery path must be an absolute path"):
                smoke.run_smoke(Path("relative-gallery"), DEFAULTS, self.report_path())
        with self.assertRaisesRegex(smoke.SmokeError, "report path must be an absolute path"):
            smoke.run_smoke(Path("/does/not/matter"), DEFAULTS, Path("relative-report.json"))
        with self.assertRaisesRegex(smoke.SmokeError, "report parent directory is unavailable"):
            smoke.run_smoke(Path("/does/not/matter"), DEFAULTS, self.root / "missing-parent" / "report.json")

    def test_report_symlink_is_rejected_without_modifying_target_or_publishing_success(self) -> None:
        target = self.root / "existing.json"
        target.write_bytes(b"pre-existing report\n")
        report = self.root / "report.json"
        report.symlink_to(target)
        with self.assertRaisesRegex(smoke.SmokeError, "symlink"):
            smoke.run_smoke(Path("/does/not/matter"), DEFAULTS, report)
        self.assertEqual(target.read_bytes(), b"pre-existing report\n")
        self.assertTrue(report.is_symlink())

    def test_report_parent_symlink_is_rejected_without_gallery(self) -> None:
        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        symlink_parent = self.root / "symlink-parent"
        symlink_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaisesRegex(smoke.SmokeError, "symlink"):
            smoke.run_smoke(Path("/does/not/matter"), DEFAULTS, symlink_parent / "report.json")

    def test_explicit_empty_godot_binary_override_is_rejected(self) -> None:
        with patch.dict(os.environ, {"CK_GODOT_4_7_2_BINARY": ""}, clear=False):
            with self.assertRaisesRegex(smoke.SmokeError, "must be non-empty"):
                smoke._resolve_pinned_binary()

    def test_changed_postflight_projection_is_rejected_without_publishing_report(self) -> None:
        initial_payload = {"profile_ids": list(DEFAULTS), "projection": "initial"}
        changed_payload = {"profile_ids": list(DEFAULTS), "projection": "changed"}
        with patch.object(
            smoke,
            "preflight",
            side_effect=[(object(), initial_payload), (object(), changed_payload)],
        ):
            with patch.object(smoke, "_launch_godot", return_value=("", "", 0, {"status": "success"})):
                with self.assertRaisesRegex(smoke.SmokeError, "projection changed"):
                    smoke.run_smoke(Path("/does/not/matter"), DEFAULTS, self.report_path())
        self.assertFalse(self.report_path().exists())

    def test_godot_error_and_resource_leak_diagnostics_are_failures(self) -> None:
        self.assertTrue(smoke._has_godot_error_diagnostics("", "ERROR: Failed to load script"))
        self.assertTrue(smoke._has_godot_error_diagnostics("ObjectDB instances leaked at exit", ""))
        self.assertTrue(smoke._has_godot_error_diagnostics("RID allocations leaked", ""))
        self.assertFalse(smoke._has_godot_error_diagnostics("", "normal completion"))

    def test_successful_preflight_selects_exact_two_distinct_view_records(self) -> None:
        self.require_gallery()
        view, payload = smoke.preflight(GALLERY, DEFAULTS)
        self.assertEqual(tuple(payload["profile_ids"]), DEFAULTS)
        self.assertEqual(tuple(profile["profile_id"] for profile in payload["profiles"]), DEFAULTS)
        self.assertEqual(tuple(view.profile_ids), ("compact_broad_short_limb_large_head", "tall_narrow_long_legged", "slender_long_limb", "stocky_broad_chested"))
        self.assertNotEqual(payload["profiles"][0]["candidate_profile_sha256"], payload["profiles"][1]["candidate_profile_sha256"])
        self.assertEqual([artifact["path"] for artifact in payload["profiles"][0]["artifacts"]], [f"{DEFAULTS[0]}/{name}" for name in smoke.EXPECTED_ARTIFACT_NAMES])

    def test_duplicate_profile_rejected_before_godot(self) -> None:
        self.require_gallery()
        self.assert_rejected_before_godot(GALLERY, (DEFAULTS[0], DEFAULTS[0]))

    def test_unknown_profile_rejected_before_godot(self) -> None:
        self.require_gallery()
        self.assert_rejected_before_godot(GALLERY, (DEFAULTS[0], "not-a-frozen-profile"))

    def test_review_session_rejected_before_godot(self) -> None:
        session = self.root / "review-session"
        (session / "assets").mkdir(parents=True)
        (session / "review.json").write_text("{}", encoding="utf-8")
        self.assert_rejected_before_godot(session)

    def test_tampered_gallery_rejected_before_godot(self) -> None:
        self.require_gallery()
        tampered = self.root / "tampered-gallery"
        shutil.copytree(GALLERY, tampered)
        manifest_path = tampered / "structural-embodiment-gallery-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["profile_ids"] = list(reversed(manifest["profile_ids"]))
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        self.assert_rejected_before_godot(tampered)


@unittest.skipUnless(integration_available(), "exact Godot 4.7.2 binary or cached gallery unavailable")
class StructuralGallerySmokeIntegrationTests(unittest.TestCase):
    def test_real_report_symlink_rejection_preserves_target_and_publishes_no_success_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-structural-smoke-report-symlink-") as temporary:
            root = Path(temporary)
            target = root / "existing.json"
            target.write_bytes(b"pre-existing report\n")
            report = root / "report.json"
            report.symlink_to(target)
            with self.assertRaisesRegex(smoke.SmokeError, "symlink"):
                smoke.run_smoke(GALLERY, DEFAULTS, report)
            self.assertEqual(target.read_bytes(), b"pre-existing report\n")
            self.assertTrue(report.is_symlink())

    def test_real_gallery_mutation_after_godot_report_rejects_without_publishing_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-structural-smoke-gallery-mutation-") as temporary:
            root = Path(temporary)
            gallery = root / "gallery"
            shutil.copytree(GALLERY, gallery)
            report_path = root / "report.json"
            real_subprocess_run = subprocess.run

            def run_godot_then_mutate(*args, **kwargs):
                completed = real_subprocess_run(*args, **kwargs)
                manifest_path = gallery / "structural-embodiment-gallery-manifest.json"
                manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
                return completed

            with patch.object(smoke.subprocess, "run", side_effect=run_godot_then_mutate):
                with self.assertRaisesRegex(smoke.SmokeError, "projection changed"):
                    smoke.run_smoke(gallery, DEFAULTS, report_path)
            self.assertFalse(report_path.exists())

    def test_real_two_profile_run_twice_is_deterministic_and_does_not_write_repository_godot_cache(self) -> None:
        before = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        with tempfile.TemporaryDirectory(prefix="ck-godot-structural-smoke-integration-") as temporary:
            root = Path(temporary)
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = smoke.run_smoke(GALLERY, DEFAULTS, first_path)
            second = smoke.run_smoke(GALLERY, DEFAULTS, second_path)
            self.assertEqual(first, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first["profile_ids"], list(DEFAULTS))
            self.assertEqual(first["boundary"], "host_only_smoke")
        after = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

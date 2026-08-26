from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
REPOSITORY_ROOT = HERE.parents[2]
GALLERY = Path("/tmp/ck-godot-structural-inputs/gallery")


def load_module(name: str, path: Path):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


crosscheck = load_module("posed_structural_crosscheck_under_test", EXPERIMENT / "run_posed_structural_crosscheck.py")
DEFAULTS = crosscheck.DEFAULT_PROFILE_IDS


def integration_available() -> bool:
    if not GALLERY.is_dir() or not crosscheck.LAUNCHER.is_file() or not crosscheck.LAUNCHER.stat().st_mode & 0o111:
        return False
    try:
        result = subprocess.run([str(crosscheck.LAUNCHER), "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return False
    return result.returncode == 0 and crosscheck.EXPECTED_GODOT_VERSION in result.stdout


class PosedStructuralCrosscheckPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-godot-posed-crosscheck-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def report_path(self) -> Path:
        return self.root / "report.json"

    def require_gallery(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"cached completed gallery unavailable: {GALLERY}")

    def assert_rejected_before_godot(self, gallery: Path, profile_ids=DEFAULTS) -> None:
        with patch.object(crosscheck, "_launch_godot", side_effect=AssertionError("Godot was invoked after preflight rejection")):
            with self.assertRaises(crosscheck.SmokeError):
                crosscheck.run_crosscheck(gallery, profile_ids, self.report_path())

    def test_default_selection_is_exactly_two_distinct_frozen_profiles_without_fixture(self) -> None:
        self.assertEqual(len(DEFAULTS), 2)
        self.assertNotEqual(DEFAULTS[0], DEFAULTS[1])
        self.assertEqual(crosscheck.neutral_smoke._validate_profile_ids(DEFAULTS), DEFAULTS)

    def test_duplicate_and_unknown_profiles_rejected_without_fixture(self) -> None:
        with self.assertRaisesRegex(crosscheck.SmokeError, "duplicate profile identity"):
            crosscheck.neutral_smoke._validate_profile_ids((DEFAULTS[0], DEFAULTS[0]))
        with self.assertRaisesRegex(crosscheck.SmokeError, "unknown frozen profile identity"):
            crosscheck.neutral_smoke._validate_profile_ids((DEFAULTS[0], "not-a-frozen-profile"))

    def test_report_destination_and_symlink_preconditions_reuse_neutral_runner(self) -> None:
        with self.assertRaisesRegex(crosscheck.SmokeError, "report path must be an absolute path"):
            crosscheck.run_crosscheck(Path("/does/not/matter"), DEFAULTS, Path("relative-report.json"))
        target = self.root / "existing.json"
        target.write_bytes(b"pre-existing report\n")
        report = self.root / "report.json"
        report.symlink_to(target)
        with self.assertRaisesRegex(crosscheck.SmokeError, "symlink"):
            crosscheck.run_crosscheck(Path("/does/not/matter"), DEFAULTS, report)
        self.assertEqual(target.read_bytes(), b"pre-existing report\n")
        self.assertTrue(report.is_symlink())

    def test_diagnostics_helper_rejects_errors_and_resource_leaks(self) -> None:
        self.assertTrue(crosscheck.neutral_smoke._has_godot_error_diagnostics("", "ERROR: Failed to load script"))
        self.assertTrue(crosscheck.neutral_smoke._has_godot_error_diagnostics("ObjectDB instances leaked at exit", ""))
        self.assertTrue(crosscheck.neutral_smoke._has_godot_error_diagnostics("RID allocations leaked", ""))
        self.assertFalse(crosscheck.neutral_smoke._has_godot_error_diagnostics("", "normal completion"))

    def test_validated_projection_carries_all_six_required_artifacts(self) -> None:
        self.require_gallery()
        _, payload = crosscheck.neutral_smoke.preflight(GALLERY, DEFAULTS)
        for profile in payload["profiles"]:
            self.assertEqual(
                [Path(item["path"]).name for item in profile["artifacts"]],
                list(crosscheck.EXPECTED_ARTIFACT_NAMES),
            )

    def test_tampered_projected_artifact_is_rejected_before_godot(self) -> None:
        self.require_gallery()
        tampered = self.root / "tampered-gallery"
        shutil.copytree(GALLERY, tampered)
        posed_path = tampered / DEFAULTS[0] / "posed.ply"
        posed_path.write_bytes(posed_path.read_bytes() + b" ")
        self.assert_rejected_before_godot(tampered)


@unittest.skipUnless(integration_available(), "exact Godot 4.7.2 binary or cached gallery unavailable")
class PosedStructuralCrosscheckIntegrationTests(unittest.TestCase):
    def test_two_runs_are_byte_identical_and_do_not_create_repository_godot_cache(self) -> None:
        before = {path for path in REPOSITORY_ROOT.rglob(".godot")}
        with tempfile.TemporaryDirectory(prefix="ck-godot-posed-crosscheck-integration-") as temporary:
            root = Path(temporary)
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = crosscheck.run_crosscheck(GALLERY, DEFAULTS, first_path)
            second = crosscheck.run_crosscheck(GALLERY, DEFAULTS, second_path)
            self.assertEqual(first, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first["profile_ids"], list(DEFAULTS))
            self.assertEqual(first["claims"], ["host-local posed structural consumption"])
            self.assertEqual(first["scope_flags"], crosscheck.REPORT_FLAGS)
        after = {path for path in REPOSITORY_ROOT.rglob(".godot")}
        self.assertEqual(before, after)

    def test_real_report_records_distinct_default_identities_and_structural_consumption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-posed-crosscheck-report-") as temporary:
            report = crosscheck.run_crosscheck(GALLERY, DEFAULTS, Path(temporary) / "report.json")
        self.assertEqual(report["profile_ids"], list(DEFAULTS))
        self.assertEqual(len(set(report["candidate_profile_sha256"].values())), 2)
        for profile in report["profiles"]:
            self.assertEqual(profile["crosscheck"]["tolerance"], crosscheck.TOLERANCE)
            self.assertTrue(profile["crosscheck"]["neutral_and_posed_faces_identical"])
            self.assertTrue(profile["crosscheck"]["posed_proxy_separation_checked"])
            self.assertTrue(crosscheck._finite_bounds(profile["posed_proxy_aabb"]))
            self.assertEqual(profile["node_counts"]["collision_shape_3d"], 18)

    def test_gallery_change_after_godot_is_rejected_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-posed-crosscheck-gallery-mutation-") as temporary:
            root = Path(temporary)
            gallery = root / "gallery"
            shutil.copytree(GALLERY, gallery)
            report_path = root / "report.json"
            real_subprocess_run = crosscheck.neutral_smoke.subprocess.run

            def run_godot_then_mutate(*args, **kwargs):
                completed = real_subprocess_run(*args, **kwargs)
                manifest_path = gallery / "structural-embodiment-gallery-manifest.json"
                manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
                return completed

            with patch.object(crosscheck.neutral_smoke.subprocess, "run", side_effect=run_godot_then_mutate):
                with self.assertRaisesRegex(crosscheck.SmokeError, "projection changed"):
                    crosscheck.run_crosscheck(gallery, DEFAULTS, report_path)
            self.assertFalse(report_path.exists())


if __name__ == "__main__":
    unittest.main()

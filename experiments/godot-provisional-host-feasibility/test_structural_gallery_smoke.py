from __future__ import annotations

from copy import deepcopy
import hashlib
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
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
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


def _neutral_validation_fixture() -> tuple[dict, dict]:
    payload_profiles = []
    actual_profiles = []
    candidate_hashes = {}
    artifact_identities = {}
    for index, profile_id in enumerate(DEFAULTS):
        candidate_hash = chr(ord("a") + index) * 64
        metrics = {
            "format": "creature-kernel.disposable-structural-embodiment-gallery.v1",
            "profile_id": profile_id,
            "neutral_vertex_count": 3,
            "posed_vertex_count": 3,
            "face_count": 1,
            "bone_count": 2,
            "proxy_count": 1,
            "neutral_bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
            "posed_bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
            "pose_rule_count": 1,
            "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
            "gallery_global_world_bound": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
        }
        payload_profiles.append({"profile_id": profile_id, "candidate_profile_sha256": candidate_hash, "artifacts": [], "metrics": metrics})
        candidate_hashes[profile_id] = candidate_hash
        artifact_identities[profile_id] = []

        actual_metrics = deepcopy(metrics)
        actual_metrics["neutral_bounds"]["max"][0] += 5.0e-7
        actual_counts = {
            "vertex_count": 3,
            "face_count": 1,
            "bone_count": 2,
            "proxy_count": 1,
            "weight_vertex_count": 3,
            "influence_count": 3,
            "host_observation": "preserved",
        }
        actual_profiles.append(
            {
                "profile_id": profile_id,
                "candidate_profile_sha256": candidate_hash,
                "metrics": actual_metrics,
                "counts": actual_counts,
                "mesh_aabb": metrics["neutral_bounds"],
                "profile_translation": list(smoke.EXPECTED_TRANSLATIONS[index]),
                "proxy_segments": {
                    "segment_count": 1,
                    "radius_count": 1,
                    "capsule_height_rule": "segment_length + 2*radius",
                    "positive_y_alignment_checked": True,
                },
                "node_counts": {
                    "profile_root": 1,
                    "mesh_instance_3d": 1,
                    "static_body_3d": 1,
                    "collision_shape_3d": 1,
                    "total_profile_nodes": 4,
                },
            }
        )

    payload = {
        "projection_contract": "test-projection-v1",
        "manifest_sha256": "c" * 64,
        "manifest_bytes": 1,
        "godot_version": smoke.EXPECTED_GODOT_VERSION,
        "profile_ids": list(DEFAULTS),
        "pose_id": "test-pose",
        "pose_sha256": "d" * 64,
        "boundary": "host_only_smoke",
        "profiles": payload_profiles,
    }
    report = {
        "schema": "creature-kernel.disposable-godot-host-load-smoke.v1",
        "status": "success",
        "boundary": "host_only_smoke",
        "godot_version": smoke.EXPECTED_GODOT_VERSION,
        "godot_engine_version_string": smoke.EXPECTED_GODOT_ENGINE_VERSION_STRING,
        "profile_ids": list(DEFAULTS),
        "candidate_profile_sha256": candidate_hashes,
        "validated_gallery": {
            "projection_contract": "test-projection-v1",
            "manifest_sha256": "c" * 64,
            "manifest_bytes": 1,
            "pose_id": "test-pose",
            "pose_sha256": "d" * 64,
            "boundary": "host_only_smoke",
        },
        "artifact_hash_identities": artifact_identities,
        "coordinate_rule": {
            "kind": "disposable_host_local_identity",
            "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
            "scope": "host_only_smoke",
        },
        "host_only_smoke": {
            "boundary": "host_only_smoke",
            "scope": "load two validated neutral structural profiles and instantiate temporary mesh/collision nodes",
            "physics_stepping": False,
            "visual_output": False,
            "claims": [],
        },
        "profiles": actual_profiles,
    }
    return payload, report


def _update_payload_artifact(payload: dict, profile_id: str, artifact_name: str, data: bytes) -> None:
    expected_path = f"{profile_id}/{artifact_name}"
    for profile in payload["profiles"]:
        if profile["profile_id"] != profile_id:
            continue
        for artifact in profile["artifacts"]:
            if artifact["path"] == expected_path:
                artifact["sha256"] = hashlib.sha256(data).hexdigest()
                artifact["bytes"] = len(data)
                return
    raise AssertionError(f"missing payload artifact {expected_path}")


def _mutate_proxy_vector(gallery: Path, payload: dict, profile_id: str, artifact_name: str, replacement: object) -> None:
    path = gallery / profile_id / artifact_name
    value = json.loads(path.read_text(encoding="utf-8"))
    value["proxies"][0]["a"][0] = replacement
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(data)
    _update_payload_artifact(payload, profile_id, artifact_name, data)


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
        self.assertTrue(smoke._has_godot_error_diagnostics("ERROR: ObjectDB instances leaked at exit", ""))
        self.assertTrue(smoke._has_godot_error_diagnostics("ERROR: 1 RID allocations of type 'Mesh' were leaked.", ""))
        self.assertFalse(smoke._has_godot_error_diagnostics("completed without errors; ObjectDB and RID are healthy", ""))
        self.assertFalse(smoke._has_godot_error_diagnostics("", "normal completion"))

    def test_godot_launch_timeout_fails_closed_with_available_diagnostics(self) -> None:
        timeout = subprocess.TimeoutExpired(
            cmd=["godot"],
            timeout=smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
            output="partial stdout",
            stderr="partial stderr",
        )
        with patch.object(smoke, "_resolve_pinned_binary", return_value=Path("/bin/true")):
            with patch.object(smoke.subprocess, "run", side_effect=timeout) as run:
                with self.assertRaisesRegex(smoke.SmokeError, "exceeded 300s.*partial stdout.*partial stderr"):
                    smoke._launch_godot(Path("/missing-gallery"), DEFAULTS, {"profiles": []})
        self.assertEqual(run.call_args.kwargs["timeout"], smoke.GODOT_LAUNCH_TIMEOUT_SECONDS)

    def test_non_dictionary_profile_records_raise_smoke_error(self) -> None:
        payload, report = _neutral_validation_fixture()
        report["profiles"] = [None, None]
        with self.assertRaisesRegex(smoke.SmokeError, "profile records are incomplete or reordered"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_validation_preserves_host_metrics_and_counts(self) -> None:
        payload, report = _neutral_validation_fixture()
        raw_report = deepcopy(report)
        host_metrics = report["profiles"][0]["metrics"]
        host_counts = report["profiles"][0]["counts"]
        smoke._validate_report(report, payload, DEFAULTS)
        self.assertEqual(report, raw_report)
        self.assertIs(report["profiles"][0]["metrics"], host_metrics)
        self.assertIs(report["profiles"][0]["counts"], host_counts)
        self.assertEqual(report["profiles"][0]["counts"]["host_observation"], "preserved")

    def test_host_observed_count_maps_must_use_exact_non_boolean_integers(self) -> None:
        locations = tuple(
            ("counts", key)
            for key in (
                "vertex_count",
                "face_count",
                "bone_count",
                "proxy_count",
                "weight_vertex_count",
                "influence_count",
            )
        ) + (
            ("proxy_segments", "segment_count"),
            ("proxy_segments", "radius_count"),
            ("node_counts", "profile_root"),
            ("node_counts", "mesh_instance_3d"),
            ("node_counts", "static_body_3d"),
            ("node_counts", "collision_shape_3d"),
            ("node_counts", "total_profile_nodes"),
        )
        for location, key in locations:
            for malformed in ("3", None, True, 3.0):
                with self.subTest(location=location, key=key, malformed=malformed):
                    payload, report = _neutral_validation_fixture()
                    report["profiles"][0][location][key] = malformed
                    with self.assertRaisesRegex(smoke.SmokeError, "exact non-boolean integer"):
                        smoke._validate_report(report, payload, DEFAULTS)

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


class StructuralGallerySmokeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not integration_available():
            raise unittest.SkipTest("exact Godot 4.7.2 binary or configured gallery unavailable")

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

    def test_real_godot_rejects_nonnumeric_neutral_proxy_vector_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-structural-smoke-vector-mutation-") as temporary:
            gallery = Path(temporary) / "gallery"
            shutil.copytree(GALLERY, gallery)
            _, payload = smoke.preflight(gallery, DEFAULTS)
            _mutate_proxy_vector(gallery, payload, DEFAULTS[0], "proxies-neutral.json", "0.0")
            with self.assertRaisesRegex(smoke.SmokeError, "proxy endpoint is not a valid finite vector"):
                smoke._launch_godot(gallery, DEFAULTS, payload)

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

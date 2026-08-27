from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
REPOSITORY_ROOT = HERE.parents[2]
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))


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


def _posed_validation_fixture() -> tuple[dict, dict]:
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
            "bone_count": 18,
            "proxy_count": 18,
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
        actual_metrics["posed_bounds"]["max"][0] += 5.0e-7
        actual_counts = {
            "neutral_vertex_count": 3,
            "posed_vertex_count": 3,
            "face_count": 1,
            "bone_count": 18,
            "proxy_count": 18,
            "weight_vertex_count": 3,
            "influence_count": 18,
            "host_observation": "preserved",
        }
        actual_profiles.append(
            {
                "profile_id": profile_id,
                "candidate_profile_sha256": candidate_hash,
                "metrics": actual_metrics,
                "counts": actual_counts,
                "posed_mesh_aabb": metrics["posed_bounds"],
                "posed_proxy_aabb": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
                "profile_translation": list(crosscheck.EXPECTED_TRANSLATIONS[index]),
                "node_counts": {
                    "profile_root": 1,
                    "mesh_instance_3d": 1,
                    "static_body_3d": 1,
                    "collision_shape_3d": 18,
                    "skeleton_3d": 0,
                    "total_profile_nodes": 21,
                },
                "crosscheck": {
                    "tolerance": crosscheck.TOLERANCE,
                    "posed_vertices_recomputed": 3,
                    "posed_normals_recomputed": 3,
                    "posed_proxy_endpoints_recomputed": 36,
                    "neutral_and_posed_faces_identical": True,
                    "at_least_one_vertex_or_normal_changed": True,
                    "bone_ids_parents_lengths_identical": True,
                    "weights_validated": True,
                    "posed_bounds_match_metrics": True,
                    "posed_proxy_separation_checked": True,
                    "skeleton_3d_or_skin_binding": False,
                },
            }
        )

    payload = {
        "projection_contract": "test-projection-v1",
        "manifest_sha256": "c" * 64,
        "manifest_bytes": 1,
        "godot_version": crosscheck.EXPECTED_GODOT_VERSION,
        "profile_ids": list(DEFAULTS),
        "pose_id": "test-pose",
        "pose_sha256": "d" * 64,
        "boundary": crosscheck.REPORT_BOUNDARY,
        "profiles": payload_profiles,
    }
    report = {
        "schema": crosscheck.REPORT_SCHEMA,
        "status": "success",
        "boundary": crosscheck.REPORT_BOUNDARY,
        "godot_version": crosscheck.EXPECTED_GODOT_VERSION,
        "godot_engine_version_string": crosscheck.EXPECTED_GODOT_ENGINE_VERSION_STRING,
        "profile_ids": list(DEFAULTS),
        "candidate_profile_sha256": candidate_hashes,
        "validated_gallery": {
            "projection_contract": "test-projection-v1",
            "manifest_sha256": "c" * 64,
            "manifest_bytes": 1,
            "pose_id": "test-pose",
            "pose_sha256": "d" * 64,
            "boundary": crosscheck.REPORT_BOUNDARY,
        },
        "artifact_hash_identities": artifact_identities,
        "coordinate_rule": {
            "kind": "disposable_host_local_identity",
            "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
            "scope": crosscheck.REPORT_BOUNDARY,
            "profile_translations": [list(value) for value in crosscheck.EXPECTED_TRANSLATIONS],
        },
        "claims": crosscheck.REPORT_CLAIMS,
        "scope_flags": crosscheck.REPORT_FLAGS,
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
        self.assertTrue(crosscheck.neutral_smoke._has_godot_error_diagnostics("ERROR: ObjectDB instances leaked at exit", ""))
        self.assertTrue(crosscheck.neutral_smoke._has_godot_error_diagnostics("ERROR: 1 RID allocations of type 'Mesh' were leaked.", ""))
        self.assertFalse(crosscheck.neutral_smoke._has_godot_error_diagnostics("completed without errors; ObjectDB and RID are healthy", ""))
        self.assertFalse(crosscheck.neutral_smoke._has_godot_error_diagnostics("", "normal completion"))

    def test_non_dictionary_profile_records_raise_smoke_error(self) -> None:
        payload, report = _posed_validation_fixture()
        report["profiles"] = [None, None]
        with self.assertRaisesRegex(crosscheck.SmokeError, "profile records are incomplete or reordered"):
            crosscheck._validate_report(report, payload, DEFAULTS)

    def test_validation_preserves_host_metrics_and_counts(self) -> None:
        payload, report = _posed_validation_fixture()
        raw_report = deepcopy(report)
        host_metrics = report["profiles"][0]["metrics"]
        host_counts = report["profiles"][0]["counts"]
        crosscheck._validate_report(report, payload, DEFAULTS)
        self.assertEqual(report, raw_report)
        self.assertIs(report["profiles"][0]["metrics"], host_metrics)
        self.assertIs(report["profiles"][0]["counts"], host_counts)
        self.assertEqual(report["profiles"][0]["counts"]["host_observation"], "preserved")

    def test_host_observed_count_maps_must_use_exact_non_boolean_integers(self) -> None:
        locations = tuple(
            ("counts", key)
            for key in (
                "neutral_vertex_count",
                "posed_vertex_count",
                "face_count",
                "bone_count",
                "proxy_count",
                "weight_vertex_count",
                "influence_count",
            )
        ) + (
            ("node_counts", "profile_root"),
            ("node_counts", "mesh_instance_3d"),
            ("node_counts", "static_body_3d"),
            ("node_counts", "collision_shape_3d"),
            ("node_counts", "skeleton_3d"),
            ("node_counts", "total_profile_nodes"),
            ("crosscheck", "posed_vertices_recomputed"),
            ("crosscheck", "posed_normals_recomputed"),
            ("crosscheck", "posed_proxy_endpoints_recomputed"),
        )
        for location, key in locations:
            for malformed in ("3", None, True, 3.0):
                with self.subTest(location=location, key=key, malformed=malformed):
                    payload, report = _posed_validation_fixture()
                    report["profiles"][0][location][key] = malformed
                    with self.assertRaisesRegex(crosscheck.SmokeError, "exact non-boolean integer"):
                        crosscheck._validate_report(report, payload, DEFAULTS)

    def test_launch_passes_posed_script_and_validator_without_mutating_neutral_runner(self) -> None:
        original_script = crosscheck.neutral_smoke.GODOT_SCRIPT
        original_validator = crosscheck.neutral_smoke._validate_report
        calls = []
        expected = ("stdout", "stderr", 0, {"status": "success"})

        def fake_launch(*args, **kwargs):
            calls.append((args, kwargs))
            return expected

        with patch.object(crosscheck.neutral_smoke, "_launch_godot", side_effect=fake_launch):
            self.assertEqual(crosscheck._launch_godot(Path("/gallery"), DEFAULTS, {}), expected)
        self.assertEqual(crosscheck.neutral_smoke.GODOT_SCRIPT, original_script)
        self.assertIs(crosscheck.neutral_smoke._validate_report, original_validator)
        self.assertEqual(calls[0][1]["script"], crosscheck.GODOT_SCRIPT)
        self.assertIs(calls[0][1]["validator"], crosscheck._skip_report_validation)

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


class PosedStructuralCrosscheckIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not integration_available():
            raise unittest.SkipTest("exact Godot 4.7.2 binary or configured gallery unavailable")

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

    def test_real_godot_rejects_nonnumeric_posed_proxy_vector_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-posed-crosscheck-vector-mutation-") as temporary:
            gallery = Path(temporary) / "gallery"
            shutil.copytree(GALLERY, gallery)
            _, payload = crosscheck.neutral_smoke.preflight(gallery, DEFAULTS)
            _mutate_proxy_vector(gallery, payload, DEFAULTS[0], "proxies-posed.json", "0.0")
            with self.assertRaisesRegex(crosscheck.SmokeError, "contains a non-finite value"):
                crosscheck._launch_godot(gallery, DEFAULTS, payload)


if __name__ == "__main__":
    unittest.main()

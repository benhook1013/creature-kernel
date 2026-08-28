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
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
REPOSITORY_ROOT = HERE.parents[2]
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
DEFAULTS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
ALTERNATE = ("slender_long_limb", "stocky_broad_chested")
FAIL_CLOSED_PROJECTION_DIAGNOSTIC = (
    "skeletal pose smoke failed: selected profile IDs disagree with the validated projection"
)
CARRIER_IDENTITY = {
    "sha256": "e" * 64,
    "byte_count_decimal": "1234",
    "schema": "creature-kernel.disposable-engine-neutral-avatar-input.v1",
    "boundary": "experiment_input_only_no_runtime_package_or_adapter_contract",
    "experiment_instance_ids": ["avatar-left", "avatar-right"],
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_module("skeletal_pose_smoke_under_test", EXPERIMENT / "run_skeletal_pose_smoke.py")
carrier = load_module("disposable_avatar_carrier_for_skeletal_tests", EXPERIMENT / "disposable_avatar_carrier.py")


def _skeletal_validation_fixture() -> tuple[dict, dict]:
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
            "pose_rule_count": 18,
            "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
            "gallery_global_world_bound": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
        }
        payload_profiles.append(
            {
                "profile_id": profile_id,
                "candidate_profile_sha256": candidate_hash,
                "artifacts": [],
                "metrics": metrics,
            }
        )
        candidate_hashes[profile_id] = candidate_hash
        artifact_identities[profile_id] = []
        actual_profiles.append(
            {
                "profile_id": profile_id,
                "candidate_profile_sha256": candidate_hash,
                "metrics": deepcopy(metrics),
                "counts": {
                    "neutral_vertex_count": 3,
                    "posed_vertex_count": 3,
                    "face_count": 1,
                    "bone_count": 18,
                    "proxy_count": 18,
                    "weight_vertex_count": 3,
                    "influence_count": 18,
                },
                "neutral_mesh_aabb": metrics["neutral_bounds"],
                "posed_mesh_aabb": metrics["posed_bounds"],
                "posed_proxy_aabb": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
                "profile_translation": list(smoke.EXPECTED_TRANSLATIONS[index]),
                "node_counts": {
                    "profile_root": 1,
                    "skeleton_3d": 1,
                    "mesh_instance_3d": 1,
                    "static_body_3d": 1,
                    "collision_shape_3d": 18,
                    "total_profile_nodes": 22,
                },
                "binding": {
                    "skeleton_bone_count": 18,
                    "skin_bind_count": 18,
                    "unique_bone_names": True,
                    "parent_links_match": True,
                    "neutral_rest_matches_published": True,
                    "skin_bind_poses_match_published": True,
                    "mesh_skeleton_path_bound": True,
                    "mesh_skin_bound": True,
                    "neutral_baked_mesh_matches": True,
                    "posed_baked_mesh_matches": True,
                    "pose_rules_applied": 18,
                    "pose_global_matrices_match": 18,
                    "skin_matrices_match": 18,
                    "posed_proxy_nodes_match": 18,
                    "tolerance": smoke.TOLERANCE,
                    "normal_tolerance": smoke.NORMAL_TOLERANCE,
                    "max_neutral_vertex_error": 0.0,
                    "max_neutral_normal_error": 0.0,
                    "max_posed_vertex_error": 0.0,
                    "max_posed_normal_error": 0.0,
                    "max_posed_proxy_endpoint_error": 0.0,
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
        "schema": smoke.REPORT_SCHEMA,
        "status": "success",
        "boundary": smoke.REPORT_BOUNDARY,
        "claims": deepcopy(smoke.REPORT_CLAIMS),
        "scope_flags": deepcopy(smoke.REPORT_FLAGS),
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
            "scope": smoke.REPORT_BOUNDARY,
            "profile_translations": [list(value) for value in smoke.EXPECTED_TRANSLATIONS],
        },
        "pose_binding": {
            "pose_id": "test-pose",
            "pose_sha256": "d" * 64,
            "path": "structural_embodiment_shared_pose.json",
            "rule_count": 18,
            "rules_validated": True,
            "applied_to_skeleton3d": True,
            "ik": False,
            "contact": False,
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


def _mutate_skeleton(gallery: Path, payload: dict, profile_id: str) -> None:
    path = gallery / profile_id / "skeleton.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["neutral"]["bones"] = []
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(data)
    _update_payload_artifact(payload, profile_id, "skeleton.json", data)


def _mutate_pose(gallery: Path, payload: dict) -> None:
    path = gallery / "structural_embodiment_shared_pose.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["rules"][0]["angle_degrees"] = 1.0
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(data)
    payload["pose_sha256"] = hashlib.sha256(data).hexdigest()


def _godot_version_probe_command() -> list[str]:
    return [str(smoke.neutral_smoke.LAUNCHER), "--headless", "--version"]


def integration_available() -> bool:
    if os.environ.get(smoke.VISIBLE_GODOT_OPT_IN) != "1":
        return False
    if not GALLERY.is_dir() or not smoke.neutral_smoke.LAUNCHER.is_file() or not smoke.neutral_smoke.LAUNCHER.stat().st_mode & 0o111:
        return False
    if not os.environ.get("DISPLAY"):
        return False
    try:
        result = subprocess.run(
            _godot_version_probe_command(),
            capture_output=True,
            text=True,
            check=False,
            timeout=smoke.neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and smoke.EXPECTED_GODOT_VERSION in result.stdout


class SkeletalPoseSmokeValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_both_frozen_profile_pairs_are_distinct_and_accepted(self) -> None:
        self.assertEqual(smoke.neutral_smoke._validate_profile_ids(DEFAULTS), DEFAULTS)
        self.assertEqual(smoke.neutral_smoke._validate_profile_ids(ALTERNATE), ALTERNATE)
        self.assertNotEqual(set(DEFAULTS), set(ALTERNATE))

    def test_visible_x11_launch_requires_explicit_attended_opt_in(self) -> None:
        with patch.dict(os.environ, {smoke.VISIBLE_GODOT_OPT_IN: ""}):
            with self.assertRaisesRegex(smoke.SmokeError, "visible X11 Godot launch is disabled"):
                smoke._launch_godot(self.root, DEFAULTS, {})

    def test_integration_availability_probe_times_out_fail_closed(self) -> None:
        with (
            patch.object(sys.modules[__name__], "GALLERY", self.root),
            patch.object(smoke.neutral_smoke, "LAUNCHER", Path(sys.executable)),
            patch.dict(os.environ, {smoke.VISIBLE_GODOT_OPT_IN: "1", "DISPLAY": ":99"}),
            patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired([sys.executable], 1)),
        ):
            self.assertFalse(integration_available())

    def test_availability_version_probe_is_explicitly_headless(self) -> None:
        launcher = self.root / "fake-godot"
        with patch.object(smoke.neutral_smoke, "LAUNCHER", launcher):
            self.assertEqual(
                _godot_version_probe_command(),
                [str(launcher), "--headless", "--version"],
            )
        source = HERE.read_text(encoding="utf-8")
        self.assertIn("result = subprocess.run(", source)
        self.assertIn("timeout=smoke.neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS", source)

    def test_headless_script_compile_reaches_fail_closed_projection_diagnostic(self) -> None:
        launcher = smoke.neutral_smoke.LAUNCHER
        if not launcher.is_file() or not os.access(launcher, os.X_OK):
            self.skipTest(f"exact pinned Godot launcher unavailable: {launcher}")
        try:
            pinned_binary = smoke.neutral_smoke._resolve_pinned_binary()
        except smoke.SmokeError as exc:
            self.skipTest(f"exact pinned Godot binary unavailable: {exc}")
        if not pinned_binary.is_file() or not os.access(pinned_binary, os.X_OK):
            self.skipTest(f"exact pinned Godot binary unavailable: {pinned_binary}")

        project_root = self.root / "headless-project"
        project_root.mkdir()
        project_file = project_root / smoke.neutral_smoke.PROJECT_FILE.name
        script_file = project_root / smoke.GODOT_SCRIPT.name
        report_file = project_root / "unexpected-report.json"
        shutil.copyfile(smoke.neutral_smoke.PROJECT_FILE, project_file)
        shutil.copyfile(smoke.GODOT_SCRIPT, script_file)

        isolated_root = self.root / "isolated-runtime"
        isolated_paths = {
            "HOME": isolated_root / "home",
            "XDG_CACHE_HOME": isolated_root / "cache",
            "XDG_CONFIG_HOME": isolated_root / "config",
            "XDG_DATA_HOME": isolated_root / "data",
            "XDG_STATE_HOME": isolated_root / "state",
            "TMPDIR": isolated_root / "tmp",
            "TMP": isolated_root / "tmp",
            "TEMP": isolated_root / "tmp",
            "XDG_RUNTIME_DIR": isolated_root / "runtime",
        }
        for path in set(isolated_paths.values()):
            path.mkdir(parents=True, exist_ok=True)
        isolated_paths["XDG_RUNTIME_DIR"].chmod(0o700)

        environment = os.environ.copy()
        environment.update({key: str(value) for key, value in isolated_paths.items()})
        environment["CK_GODOT_4_7_2_BINARY"] = str(pinned_binary)
        environment.pop(smoke.VISIBLE_GODOT_OPT_IN, None)
        environment.pop("DISPLAY", None)
        environment.pop("WAYLAND_DISPLAY", None)
        self.assertNotIn(smoke.VISIBLE_GODOT_OPT_IN, environment)

        command = [
            str(launcher),
            "--headless",
            "--audio-driver",
            "Dummy",
            "--path",
            str(project_root),
            "--script",
            str(script_file),
            "--",
            "--gallery",
            str(self.root / "intentionally-missing-gallery"),
            "--profile-id",
            DEFAULTS[0],
            "--profile-id",
            DEFAULTS[1],
            "--report",
            str(report_file),
            "--validated-json",
            "{}",
        ]
        self.assertEqual(command[1], "--headless")
        self.assertEqual(environment["CK_GODOT_4_7_2_BINARY"], str(pinned_binary))

        def repository_godot_snapshot() -> dict[Path, tuple[str, str]]:
            snapshot = {}
            for godot_root in REPOSITORY_ROOT.rglob(".godot"):
                if not godot_root.is_dir():
                    continue
                for path in (godot_root, *godot_root.rglob("*")):
                    relative = path.relative_to(REPOSITORY_ROOT)
                    if path.is_symlink():
                        snapshot[relative] = ("symlink", os.readlink(path))
                    elif path.is_file():
                        snapshot[relative] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
                    elif path.is_dir():
                        snapshot[relative] = ("directory", "")
                    else:
                        snapshot[relative] = ("other", "")
            return snapshot

        before_godot_cache = repository_godot_snapshot()
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=smoke.neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            self.fail(
                f"headless Godot compile check timed out; stdout={exc.stdout!r}; stderr={exc.stderr!r}"
            )
        except OSError as exc:
            self.fail(f"headless Godot compile check could not run: {type(exc).__name__}: {exc}")
        after_godot_cache = repository_godot_snapshot()
        self.assertEqual(before_godot_cache, after_godot_cache)

        if completed.returncode == 78 and "Godot 4.7.2 preflight failed:" in completed.stderr:
            self.skipTest(f"exact pinned Godot binary unavailable: {completed.stderr.strip()}")

        diagnostics = f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        combined_output = f"{completed.stdout}\n{completed.stderr}"
        self.assertEqual(completed.returncode, 1, f"expected fail-closed exit status 1; {diagnostics}")
        self.assertIn(FAIL_CLOSED_PROJECTION_DIAGNOSTIC, combined_output, diagnostics)
        self.assertFalse(report_file.exists(), f"invalid projection unexpectedly produced {report_file}")
        for forbidden_diagnostic in (
            "SCRIPT ERROR:",
            "SCRIPT WARNING:",
            "Parse Error:",
            "Parser Error:",
            "Warning treated as error",
            "Failed to load script",
        ):
            self.assertNotIn(forbidden_diagnostic.casefold(), combined_output.casefold(), diagnostics)
        unexpected_error_lines = [
            line
            for line in combined_output.splitlines()
            if line.lstrip().startswith(("ERROR:", "WARNING:"))
            and FAIL_CLOSED_PROJECTION_DIAGNOSTIC not in line
        ]
        self.assertEqual(unexpected_error_lines, [], diagnostics)

    def test_report_runtime_evidence_is_read_back_not_self_asserted(self) -> None:
        source = (EXPERIMENT / "skeletal_pose_smoke.gd").read_text(encoding="utf-8")
        run_source = source[source.index("func _run_smoke"):source.index("func _parse_arguments")]
        report_source = source[source.index("func _build_report"):source.index("func _parse_ply")]
        binding_source = source[source.index("func _readback_binding"):source.index("func _readback_node_counts")]
        node_source = source[source.index("func _readback_node_counts"):source.index("func _count_profile_nodes")]
        proxy_source = source[source.index("func _build_host_proxies"):source.index("func _read_proxy_geometry")]
        self.assertIn("if report.is_empty():", run_source)
        self.assertIn("runtime evidence report is empty", run_source)
        self.assertIn("var binding := _readback_binding(profile)", report_source)
        self.assertIn("var node_counts := _readback_node_counts(profile)", report_source)
        self.assertIn("var orientation = _basis_for_y_axis", proxy_source)
        self.assertNotIn("Quaternion(Vector3.UP", proxy_source)
        self.assertIn("runtime pose rotation read-back is missing selector", binding_source)
        self.assertNotIn("force_update_all_bone_transforms", source)
        self.assertNotIn("NOTIFICATION_UPDATE_SKELETON", source)
        self.assertIn("skeleton_updated.connect", source)
        self.assertIn("--carrier-identity-json", source)
        self.assertIn("func _validate_carrier_identity", source)
        for field in (
            "unique_bone_names",
            "parent_links_match",
            "neutral_rest_matches_published",
            "skin_bind_poses_match_published",
            "neutral_baked_mesh_matches",
            "posed_baked_mesh_matches",
        ):
            self.assertNotIn(f'"{field}": true', report_source)
            self.assertIn(f'"{field}":', binding_source)
        for field in ("profile_root", "skeleton_3d", "mesh_instance_3d", "static_body_3d"):
            self.assertNotIn(f'"{field}": 1', report_source)
            self.assertIn(f'"{field}":', node_source)
        self.assertNotIn('"collision_shape_3d": profile.body.get_child_count()', report_source)
        self.assertNotIn('"total_profile_nodes": 4 + profile.body.get_child_count()', report_source)
        for expression in (
            "skeleton.get_bone_name",
            "skeleton.get_bone_parent",
            "skeleton.get_bone_rest",
            "skin.get_bind_bone",
            "skin.get_bind_pose",
            "mesh_instance.get_skeleton_path",
            "mesh_instance.get_skin",
            "mesh_instance.get_skin_reference",
            "skeleton.get_bone_pose",
            "body.get_child_count",
            "body_node.get_children",
        ):
            self.assertIn(expression, source)

    def test_report_validator_accepts_complete_binding_evidence(self) -> None:
        payload, report = _skeletal_validation_fixture()
        smoke._validate_report(report, payload, DEFAULTS)

    def test_report_validator_rejects_numeric_boolean_substitutes(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["scope_flags"]["physics_stepping"] = 0
        with self.assertRaisesRegex(smoke.SmokeError, "scope flags are not fail-closed"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["pose_binding"]["rules_validated"] = 1
        with self.assertRaisesRegex(smoke.SmokeError, "pose binding evidence is invalid"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_report_validator_accepts_exact_carrier_identity(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = deepcopy(CARRIER_IDENTITY)
        smoke._validate_report(report, payload, DEFAULTS, deepcopy(CARRIER_IDENTITY))

    def test_report_validator_rejects_invalid_or_unexpected_carrier_identity(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = None
        with self.assertRaisesRegex(smoke.SmokeError, "unexpected validated-carrier"):
            smoke._validate_report(report, payload, DEFAULTS)

        mutations = (
            ("sha256", "f" * 64),
            ("byte_count_decimal", 1234),
            ("byte_count_decimal", "01234"),
            ("byte_count_decimal", "1234.0"),
            ("schema", "unexpected"),
            ("boundary", "unexpected"),
            ("experiment_instance_ids", ["avatar-right", "avatar-left"]),
            ("experiment_instance_ids", ["avatar-left", "avatar-left"]),
            ("experiment_instance_ids", ["avatar-left", 1]),
        )
        for key, replacement in mutations:
            with self.subTest(key=key, replacement=replacement):
                payload, report = _skeletal_validation_fixture()
                report["validated_carrier"] = deepcopy(CARRIER_IDENTITY)
                report["validated_carrier"][key] = replacement
                with self.assertRaisesRegex(smoke.SmokeError, "validated-carrier identity is invalid"):
                    smoke._validate_report(report, payload, DEFAULTS, deepcopy(CARRIER_IDENTITY))

        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = {**deepcopy(CARRIER_IDENTITY), "extra": False}
        with self.assertRaisesRegex(smoke.SmokeError, "validated-carrier identity is incomplete"):
            smoke._validate_report(report, payload, DEFAULTS, deepcopy(CARRIER_IDENTITY))

    def test_carrier_flow_passes_validated_payload_and_identity_through_unchanged(self) -> None:
        payload, report = _skeletal_validation_fixture()
        carrier_value = {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "instances": [
                {"instance_id": "avatar-left"},
                {"instance_id": "avatar-right"},
            ],
        }
        module = SimpleNamespace(SCHEMA=carrier.SCHEMA, BOUNDARY=carrier.BOUNDARY)
        validated = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-right"))
        expected_identity = smoke._carrier_identity(carrier_value, module)
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, validated]) as carrier_input,
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)) as launch,
            patch.object(smoke, "_validate_report") as validate_report,
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            result = smoke.run_skeletal_pose_smoke(
                self.root,
                None,
                self.root / "report.json",
                self.root / "carrier.json",
            )
        self.assertIs(result, report)
        self.assertEqual(carrier_input.call_count, 2)
        self.assertIs(launch.call_args.args[2], payload)
        self.assertEqual(launch.call_args.args[3], expected_identity)
        validate_report.assert_called_once_with(report, payload, DEFAULTS, expected_identity)
        publish.assert_called_once_with(self.root / "report.json", report)

    def test_carrier_profile_mismatch_and_postflight_change_fail_before_publication(self) -> None:
        payload, report = _skeletal_validation_fixture()
        carrier_value = {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "instances": [
                {"instance_id": "avatar-left"},
                {"instance_id": "avatar-right"},
            ],
        }
        module = SimpleNamespace(SCHEMA=carrier.SCHEMA, BOUNDARY=carrier.BOUNDARY)
        validated = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-right"))
        with (
            patch.object(smoke, "_validated_carrier_input", return_value=validated),
            patch.object(smoke, "_launch_godot") as launch,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "profile IDs disagree"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    ALTERNATE,
                    self.root / "report.json",
                    self.root / "carrier.json",
                )
        launch.assert_not_called()

        changed_postflight = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-changed"))
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, changed_postflight]),
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)),
            patch.object(smoke, "_validate_report"),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "changed during"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    self.root / "report.json",
                    self.root / "carrier.json",
                )
        publish.assert_not_called()

    def test_report_validator_rejects_incomplete_or_over_tolerance_binding(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["skin_bind_count"] = 17
        with self.assertRaisesRegex(smoke.SmokeError, "binding.skin_bind_count is invalid"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["max_posed_normal_error"] = smoke.NORMAL_TOLERANCE + 1.0e-7
        with self.assertRaisesRegex(smoke.SmokeError, "max_posed_normal_error exceeds tolerance"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["max_posed_vertex_error"] = -1.0
        with self.assertRaisesRegex(smoke.SmokeError, "max_posed_vertex_error must be non-negative"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_tampered_gallery_is_rejected_before_godot(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"cached completed gallery unavailable: {GALLERY}")
        tampered = self.root / "tampered-gallery"
        shutil.copytree(GALLERY, tampered)
        manifest_path = tampered / "structural-embodiment-gallery-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["profile_ids"] = list(reversed(manifest["profile_ids"]))
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot was invoked after preflight rejection")):
            with self.assertRaises(smoke.SmokeError):
                smoke.run_skeletal_pose_smoke(tampered, DEFAULTS, self.root / "report.json")


@unittest.skipUnless(
    integration_available(),
    "attended X11 opt-in, exact Godot 4.7.2 renderer, X11 display, or configured gallery unavailable",
)
class SkeletalPoseSmokeIntegrationTests(unittest.TestCase):
    def test_real_carrier_load_through_records_exact_input_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-carrier-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, DEFAULTS, ("avatar-left", "avatar-right")),
            )
            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
            )
            carrier_bytes = carrier_path.read_bytes()
        self.assertEqual(report["profile_ids"], list(DEFAULTS))
        self.assertEqual(
            report["validated_carrier"],
            {
                "sha256": hashlib.sha256(carrier_bytes).hexdigest(),
                "byte_count_decimal": str(len(carrier_bytes)),
                "schema": carrier.SCHEMA,
                "boundary": carrier.BOUNDARY,
                "experiment_instance_ids": ["avatar-left", "avatar-right"],
            },
        )

    def test_real_godot_rejects_noncanonical_carrier_byte_count(self) -> None:
        _, payload = smoke.neutral_smoke.preflight(GALLERY, DEFAULTS)
        invalid_identity = deepcopy(CARRIER_IDENTITY)
        invalid_identity["byte_count_decimal"] = 1234
        with self.assertRaisesRegex(smoke.SmokeError, "validated carrier byte count is invalid"):
            smoke._launch_godot(
                GALLERY,
                DEFAULTS,
                payload,
                invalid_identity,
            )

    def test_real_default_pair_produces_skeleton_skin_pose_and_proxy_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-default-") as temporary:
            report = smoke.run_skeletal_pose_smoke(GALLERY, DEFAULTS, Path(temporary) / "report.json")
        self.assertEqual(report["profile_ids"], list(DEFAULTS))
        for profile in report["profiles"]:
            self.assertEqual(profile["binding"]["skeleton_bone_count"], smoke.BONE_COUNT)
            self.assertEqual(profile["binding"]["skin_bind_count"], smoke.BONE_COUNT)
            self.assertEqual(profile["binding"]["pose_rules_applied"], smoke.BONE_COUNT)
            self.assertTrue(profile["binding"]["mesh_skin_bound"])
            self.assertEqual(profile["node_counts"]["collision_shape_3d"], smoke.PROXY_COUNT)

    def test_real_alternate_pair_is_reported_in_requested_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-alternate-") as temporary:
            report = smoke.run_skeletal_pose_smoke(GALLERY, ALTERNATE, Path(temporary) / "report.json")
        self.assertEqual(report["profile_ids"], list(ALTERNATE))
        self.assertEqual([profile["profile_id"] for profile in report["profiles"]], list(ALTERNATE))

    def test_real_malformed_skeleton_and_pose_are_rejected_fail_closed(self) -> None:
        for mutation, expected_error in (("skeleton", "skeleton states must contain exactly 18 bones"), ("pose", "shared pose rule 0 does not match")):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory(prefix=f"ck-godot-skeletal-pose-{mutation}-") as temporary:
                    gallery = Path(temporary) / "gallery"
                    shutil.copytree(GALLERY, gallery)
                    _, payload = smoke.neutral_smoke.preflight(gallery, DEFAULTS)
                    if mutation == "skeleton":
                        _mutate_skeleton(gallery, payload, DEFAULTS[0])
                    else:
                        _mutate_pose(gallery, payload)
                    with self.assertRaisesRegex(smoke.SmokeError, expected_error):
                        smoke._launch_godot(gallery, DEFAULTS, payload)

    def test_real_rerun_is_deterministic_and_does_not_pollute_repository_or_cache(self) -> None:
        before_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        before_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        before_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-deterministic-") as temporary:
            root = Path(temporary)
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = smoke.run_skeletal_pose_smoke(GALLERY, DEFAULTS, first_path)
            second = smoke.run_skeletal_pose_smoke(GALLERY, DEFAULTS, second_path)
            self.assertEqual(first, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        after_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        after_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        after_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(before_godot_dirs, after_godot_dirs)
        self.assertEqual(before_python_cache_dirs, after_python_cache_dirs)
        self.assertEqual(before_status, after_status)


if __name__ == "__main__":
    unittest.main()

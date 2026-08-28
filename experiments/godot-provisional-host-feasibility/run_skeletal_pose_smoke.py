#!/usr/bin/env python3
"""Run a disposable Godot Skeleton3D/Skin shared-pose binding smoke."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


sys.dont_write_bytecode = True

EXPERIMENT_ROOT = Path(__file__).resolve().parent
NEUTRAL_RUNNER_PATH = EXPERIMENT_ROOT / "run_structural_gallery_smoke.py"
CARRIER_MODULE_PATH = EXPERIMENT_ROOT / "disposable_avatar_carrier.py"
GODOT_SCRIPT = EXPERIMENT_ROOT / "skeletal_pose_smoke.gd"
VISIBLE_GODOT_OPT_IN = "CK_ALLOW_VISIBLE_GODOT"


def _load_neutral_runner():
    spec = importlib.util.spec_from_file_location(
        "neutral_structural_gallery_smoke_for_skeletal_pose",
        NEUTRAL_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load existing neutral smoke runner: {NEUTRAL_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_carrier_module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "disposable_avatar_carrier_for_skeletal_pose",
        CARRIER_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load disposable avatar carrier: {CARRIER_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


neutral_smoke = _load_neutral_runner()
SmokeError = neutral_smoke.SmokeError
REPOSITORY_ROOT = neutral_smoke.REPOSITORY_ROOT
PROJECT_FILE = neutral_smoke.PROJECT_FILE
LAUNCHER = neutral_smoke.LAUNCHER
EXPECTED_GODOT_VERSION = neutral_smoke.EXPECTED_GODOT_VERSION
EXPECTED_GODOT_ENGINE_VERSION_STRING = neutral_smoke.EXPECTED_GODOT_ENGINE_VERSION_STRING
DEFAULT_PROFILE_IDS = neutral_smoke.DEFAULT_PROFILE_IDS
EXPECTED_ARTIFACT_NAMES = neutral_smoke.EXPECTED_ARTIFACT_NAMES
EXPECTED_TRANSLATIONS = neutral_smoke.EXPECTED_TRANSLATIONS
BONE_COUNT = 18
PROXY_COUNT = 18
TOLERANCE = 2.0e-5
NORMAL_TOLERANCE = 3.0e-4
REPORT_SCHEMA = "creature-kernel.disposable-godot-skeletal-pose-smoke.v1"
REPORT_BOUNDARY = "host_local_skeleton3d_skin_pose_binding"
REPORT_CLAIMS = [
    "host-local Skeleton3D/Skin pose binding",
    "host-local consumption of the shared structural pose recipe",
]
REPORT_FLAGS = {
    "physics_stepping": False,
    "animation": False,
    "contact": False,
    "deformation": False,
    "render_output": False,
    "adapter": False,
}


def _carrier_identity(carrier: dict[str, Any], carrier_module: Any) -> dict[str, Any]:
    canonical = neutral_smoke._canonical_json(carrier)
    return {
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "byte_count_decimal": str(len(canonical)),
        "schema": carrier_module.SCHEMA,
        "boundary": carrier_module.BOUNDARY,
        "experiment_instance_ids": [instance["instance_id"] for instance in carrier["instances"]],
    }


def _validated_carrier_input(
    gallery: Path,
    carrier_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, Any], tuple[str, str], tuple[str, str]]:
    carrier_module = _load_carrier_module()
    try:
        carrier = carrier_module.load_carrier(carrier_path)
        payload, profile_ids, instance_ids = carrier_module.validate_carrier(carrier, gallery)
    except carrier_module.CarrierError as exc:
        raise SmokeError(f"disposable avatar carrier rejected: {exc}") from exc
    identity = _carrier_identity(carrier, carrier_module)
    if tuple(identity["experiment_instance_ids"]) != instance_ids:
        raise SmokeError("disposable avatar carrier instance order is internally inconsistent")
    return carrier_module, carrier, payload, profile_ids, instance_ids


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _expected_gallery_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_contract": payload["projection_contract"],
        "manifest_sha256": payload["manifest_sha256"],
        "manifest_bytes": payload["manifest_bytes"],
        "pose_id": payload["pose_id"],
        "pose_sha256": payload["pose_sha256"],
        "boundary": payload["boundary"],
    }


def _expected_artifact_identities(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {profile["profile_id"]: profile["artifacts"] for profile in payload["profiles"]}


def _require_exact_bool(value: Any, where: str) -> None:
    if type(value) is not bool:
        raise SmokeError(f"{where} must be an exact boolean")


def _require_finite_metric(value: Any, where: str) -> None:
    if not _finite_number(value):
        raise SmokeError(f"{where} must be a finite number")


def _validate_binding(binding: Any, profile_id: str) -> None:
    if not isinstance(binding, dict):
        raise SmokeError(f"Godot report profile {profile_id} binding evidence is incomplete")
    exact = {
        "skeleton_bone_count": BONE_COUNT,
        "skin_bind_count": BONE_COUNT,
        "unique_bone_names": True,
        "parent_links_match": True,
        "neutral_rest_matches_published": True,
        "skin_bind_poses_match_published": True,
        "mesh_skeleton_path_bound": True,
        "mesh_skin_bound": True,
        "neutral_baked_mesh_matches": True,
        "posed_baked_mesh_matches": True,
        "pose_rules_applied": BONE_COUNT,
        "pose_global_matrices_match": BONE_COUNT,
        "skin_matrices_match": BONE_COUNT,
        "posed_proxy_nodes_match": PROXY_COUNT,
        "tolerance": TOLERANCE,
        "normal_tolerance": NORMAL_TOLERANCE,
    }
    for key, expected in exact.items():
        if key not in binding:
            raise SmokeError(f"Godot report profile {profile_id} binding.{key} is missing")
        actual = binding[key]
        if isinstance(expected, bool):
            _require_exact_bool(actual, f"Godot report profile {profile_id} binding.{key}")
        if actual != expected:
            raise SmokeError(f"Godot report profile {profile_id} binding.{key} is invalid")
    for key in (
        "max_neutral_vertex_error",
        "max_neutral_normal_error",
        "max_posed_vertex_error",
        "max_posed_normal_error",
        "max_posed_proxy_endpoint_error",
    ):
        if key not in binding:
            raise SmokeError(f"Godot report profile {profile_id} binding.{key} is missing")
        _require_finite_metric(binding[key], f"Godot report profile {profile_id} binding.{key}")
        if float(binding[key]) < 0.0:
            raise SmokeError(f"Godot report profile {profile_id} {key} must be non-negative")
        limit = NORMAL_TOLERANCE if "normal" in key else TOLERANCE
        if float(binding[key]) > limit:
            raise SmokeError(f"Godot report profile {profile_id} {key} exceeds tolerance")


def _validate_carrier_report_identity(
    actual: Any,
    expected: dict[str, Any] | None,
    present: bool,
) -> None:
    if expected is None:
        if present:
            raise SmokeError("legacy Godot report contains unexpected validated-carrier evidence")
        return
    keys = {"sha256", "byte_count_decimal", "schema", "boundary", "experiment_instance_ids"}
    if not isinstance(actual, dict) or set(actual) != keys:
        raise SmokeError("Godot report validated-carrier identity is incomplete")
    if (
        not isinstance(actual["sha256"], str)
        or len(actual["sha256"]) != 64
        or not isinstance(actual["byte_count_decimal"], str)
        or not actual["byte_count_decimal"].isascii()
        or not actual["byte_count_decimal"].isdigit()
        or actual["byte_count_decimal"].startswith("0")
        or len(actual["byte_count_decimal"]) > 7
        or int(actual["byte_count_decimal"]) > 4 * 1024 * 1024
        or not isinstance(actual["schema"], str)
        or not isinstance(actual["boundary"], str)
        or not isinstance(actual["experiment_instance_ids"], list)
        or len(actual["experiment_instance_ids"]) != 2
        or any(not isinstance(value, str) for value in actual["experiment_instance_ids"])
        or actual["experiment_instance_ids"][0] == actual["experiment_instance_ids"][1]
        or actual != expected
    ):
        raise SmokeError("Godot report validated-carrier identity is invalid")


def _validate_report(
    report: Any,
    payload: dict[str, Any],
    profile_ids: tuple[str, str],
    carrier_identity: dict[str, Any] | None = None,
) -> None:
    if not isinstance(report, dict):
        raise SmokeError("Godot skeletal-pose report is not a JSON object")
    if report.get("schema") != REPORT_SCHEMA or report.get("status") != "success":
        raise SmokeError("Godot skeletal-pose report schema or status is invalid")
    if report.get("boundary") != REPORT_BOUNDARY:
        raise SmokeError("Godot skeletal-pose report boundary is invalid")
    if report.get("claims") != REPORT_CLAIMS:
        raise SmokeError("Godot skeletal-pose report contains an unexpected claim")
    scope_flags = report.get("scope_flags")
    if (
        not isinstance(scope_flags, dict)
        or scope_flags != REPORT_FLAGS
        or any(type(scope_flags.get(key)) is not bool for key in REPORT_FLAGS)
    ):
        raise SmokeError("Godot skeletal-pose report scope flags are not fail-closed")
    if report.get("godot_version") != EXPECTED_GODOT_VERSION:
        raise SmokeError(f"Godot report version is not exact: {report.get('godot_version')!r}")
    if report.get("godot_engine_version_string") != EXPECTED_GODOT_ENGINE_VERSION_STRING:
        raise SmokeError(f"Godot runtime version string is not exact: {report.get('godot_engine_version_string')!r}")
    if report.get("profile_ids") != list(profile_ids):
        raise SmokeError("Godot report profile IDs do not match the preflight selection")
    expected_hashes = {profile["profile_id"]: profile["candidate_profile_sha256"] for profile in payload["profiles"]}
    if report.get("candidate_profile_sha256") != expected_hashes:
        raise SmokeError("Godot report candidate identity hashes do not match the validated projection")
    if report.get("validated_gallery") != _expected_gallery_identity(payload):
        raise SmokeError("Godot report validated-gallery identity does not match the projection")
    if report.get("artifact_hash_identities") != _expected_artifact_identities(payload):
        raise SmokeError("Godot report artifact identities do not match the validated projection")
    _validate_carrier_report_identity(
        report.get("validated_carrier"),
        carrier_identity,
        "validated_carrier" in report,
    )
    if report.get("coordinate_rule") != {
        "kind": "disposable_host_local_identity",
        "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
        "scope": REPORT_BOUNDARY,
        "profile_translations": [list(value) for value in EXPECTED_TRANSLATIONS],
    }:
        raise SmokeError("Godot skeletal-pose report coordinate rule is invalid")
    expected_pose_binding = {
        "pose_id": payload["pose_id"],
        "pose_sha256": payload["pose_sha256"],
        "path": "structural_embodiment_shared_pose.json",
        "rule_count": BONE_COUNT,
        "rules_validated": True,
        "applied_to_skeleton3d": True,
        "ik": False,
        "contact": False,
    }
    pose_binding = report.get("pose_binding")
    if (
        not isinstance(pose_binding, dict)
        or pose_binding != expected_pose_binding
        or any(
            type(pose_binding.get(key)) is not bool
            for key in ("rules_validated", "applied_to_skeleton3d", "ik", "contact")
        )
    ):
        raise SmokeError("Godot skeletal-pose report pose binding evidence is invalid")

    actual_profiles = report.get("profiles")
    if not isinstance(actual_profiles, list) or any(not isinstance(item, dict) for item in actual_profiles):
        raise SmokeError("Godot skeletal-pose profile records are incomplete or reordered")
    if [item.get("profile_id") for item in actual_profiles] != list(profile_ids):
        raise SmokeError("Godot skeletal-pose profile records are incomplete or reordered")
    for index, (actual, expected) in enumerate(zip(actual_profiles, payload["profiles"])):
        profile_id = profile_ids[index]
        metrics = expected["metrics"]
        if metrics["bone_count"] != BONE_COUNT or metrics["proxy_count"] != PROXY_COUNT:
            raise SmokeError(f"validated gallery profile {profile_id} does not establish the exact 18/18 contract")
        if actual.get("candidate_profile_sha256") != expected["candidate_profile_sha256"]:
            raise SmokeError(f"Godot report profile {profile_id} identity differs from the validated projection")
        if not neutral_smoke._values_close(actual.get("metrics"), metrics):
            raise SmokeError(f"Godot report profile {profile_id} metrics differ from the validated projection")
        if actual.get("profile_translation") != list(EXPECTED_TRANSLATIONS[index]):
            raise SmokeError(f"Godot report profile {profile_id} translation is not fixed host-only separation")
        expected_counts = {
            "neutral_vertex_count": metrics["neutral_vertex_count"],
            "posed_vertex_count": metrics["posed_vertex_count"],
            "face_count": metrics["face_count"],
            "bone_count": BONE_COUNT,
            "proxy_count": PROXY_COUNT,
            "weight_vertex_count": metrics["neutral_vertex_count"],
        }
        counts = actual.get("counts")
        if not isinstance(counts, dict):
            raise SmokeError(f"Godot report profile {profile_id} structural counts are invalid")
        neutral_smoke._validate_exact_count_map(
            counts,
            tuple(expected_counts) + ("influence_count",),
            f"Godot report profile {profile_id} counts",
        )
        if any(counts[key] != value for key, value in expected_counts.items()) or counts["influence_count"] < metrics["neutral_vertex_count"]:
            raise SmokeError(f"Godot report profile {profile_id} structural counts are invalid")
        for bounds_key, expected_bounds in (("neutral_mesh_aabb", metrics["neutral_bounds"]), ("posed_mesh_aabb", metrics["posed_bounds"])):
            if not neutral_smoke._bounds_close(actual.get(bounds_key), expected_bounds, TOLERANCE):
                raise SmokeError(f"Godot report profile {profile_id} {bounds_key} differs from published metrics")
        if not _finite_bounds(actual.get("posed_proxy_aabb")):
            raise SmokeError(f"Godot report profile {profile_id} posed proxy bounds are invalid")
        node_counts = actual.get("node_counts")
        if not isinstance(node_counts, dict):
            raise SmokeError(f"Godot report profile {profile_id} node counts are invalid")
        neutral_smoke._validate_exact_count_map(
            node_counts,
            ("profile_root", "skeleton_3d", "mesh_instance_3d", "static_body_3d", "collision_shape_3d", "total_profile_nodes"),
            f"Godot report profile {profile_id} node_counts",
        )
        if node_counts != {
            "profile_root": 1,
            "skeleton_3d": 1,
            "mesh_instance_3d": 1,
            "static_body_3d": 1,
            "collision_shape_3d": PROXY_COUNT,
            "total_profile_nodes": 4 + PROXY_COUNT,
        }:
            raise SmokeError(f"Godot report profile {profile_id} node counts are invalid")
        _validate_binding(actual.get("binding"), profile_id)
    first_proxy_max = actual_profiles[0]["posed_proxy_aabb"]["max"][0] + EXPECTED_TRANSLATIONS[0][0]
    second_proxy_min = actual_profiles[1]["posed_proxy_aabb"]["min"][0] + EXPECTED_TRANSLATIONS[1][0]
    if first_proxy_max >= second_proxy_min:
        raise SmokeError("Godot report posed proxy bounds are not separated by fixed host-only translations")
    neutral_smoke._reject_absolute_paths(report)


def _finite_bounds(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"min", "max"}:
        return False
    return all(
        isinstance(vector, list)
        and len(vector) == 3
        and all(_finite_number(axis) for axis in vector)
        for vector in value.values()
    )


def _launch_godot(
    gallery: Path,
    profile_ids: tuple[str, str],
    payload: dict[str, Any],
    carrier_identity: dict[str, Any] | None = None,
) -> tuple[str, str, int, dict[str, Any] | None]:
    """Launch with a real renderer; headless mode exposes dummy rendering RIDs."""
    if os.environ.get(VISIBLE_GODOT_OPT_IN) != "1":
        raise SmokeError(
            f"visible X11 Godot launch is disabled; set {VISIBLE_GODOT_OPT_IN}=1 "
            "only for an attended run"
        )
    for required in (neutral_smoke.PROJECT_FILE, GODOT_SCRIPT, neutral_smoke.LAUNCHER):
        if not required.is_file():
            raise SmokeError(f"required Godot skeletal-pose file is unavailable: {required}")
    if not os.access(neutral_smoke.LAUNCHER, os.X_OK):
        raise SmokeError(f"pinned Godot launcher is not executable: {neutral_smoke.LAUNCHER}")
    with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-smoke-") as temporary:
        isolated_root = Path(temporary) / "isolated"
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
        pinned_binary = neutral_smoke._resolve_pinned_binary()
        project = Path(temporary) / "project.godot"
        script_path = Path(temporary) / GODOT_SCRIPT.name
        raw_report_path = Path(temporary) / "godot-report.json"
        shutil.copyfile(neutral_smoke.PROJECT_FILE, project)
        shutil.copyfile(GODOT_SCRIPT, script_path)
        command = [
            str(neutral_smoke.LAUNCHER),
            "--display-driver",
            "x11",
            "--rendering-method",
            "gl_compatibility",
            "--audio-driver",
            "Dummy",
            "--path",
            str(Path(temporary)),
            "--script",
            str(script_path),
            "--",
            "--gallery",
            str(gallery),
            "--profile-id",
            profile_ids[0],
            "--profile-id",
            profile_ids[1],
            "--report",
            str(raw_report_path),
            "--validated-json",
            json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False),
        ]
        if carrier_identity is not None:
            command.extend(
                [
                    "--carrier-identity-json",
                    json.dumps(carrier_identity, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False),
                ]
            )
        environment = os.environ.copy()
        environment.update({key: str(value) for key, value in isolated_paths.items()})
        environment["CK_GODOT_4_7_2_BINARY"] = str(pinned_binary)
        try:
            completed = subprocess.run(
                command,
                cwd=neutral_smoke.REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise SmokeError(
                f"Godot launcher exceeded {neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS}s; "
                f"stdout={exc.stdout!r}; stderr={exc.stderr!r}"
            ) from exc
        except OSError as exc:
            raise SmokeError(f"Godot launcher invocation failed: {type(exc).__name__}: {exc}") from exc
        diagnostic = f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        if neutral_smoke._has_godot_error_diagnostics(completed.stdout, completed.stderr):
            raise SmokeError(f"Godot launcher emitted error/leak diagnostics; {diagnostic}")
        if completed.returncode != 0:
            return completed.stdout, completed.stderr, completed.returncode, None
        report = neutral_smoke._read_report(raw_report_path)
        return completed.stdout, completed.stderr, completed.returncode, report


def run_skeletal_pose_smoke(
    gallery: Path,
    profile_ids: tuple[str, str] | list[str] | None,
    report_path: Path,
    carrier_path: Path | None = None,
) -> dict[str, Any]:
    report_path = neutral_smoke._validate_report_destination(report_path)
    gallery = Path(gallery)
    carrier_identity = None
    if carrier_path is None:
        selected = neutral_smoke._validate_profile_ids(profile_ids if profile_ids is not None else DEFAULT_PROFILE_IDS)
        _, payload = neutral_smoke.preflight(gallery, selected)
    else:
        carrier_module, carrier, payload, selected, instance_ids = _validated_carrier_input(
            gallery,
            Path(carrier_path),
        )
        if profile_ids is not None and neutral_smoke._validate_profile_ids(profile_ids) != selected:
            raise SmokeError("explicit profile IDs disagree with the validated carrier order")
        carrier_identity = _carrier_identity(carrier, carrier_module)
        if tuple(carrier_identity["experiment_instance_ids"]) != instance_ids:
            raise SmokeError("validated carrier instance order is inconsistent")
    stdout, stderr, returncode, report = _launch_godot(
        gallery,
        selected,
        payload,
        carrier_identity,
    )
    if returncode != 0:
        raise SmokeError(f"Godot launcher returned exit code {returncode}; stdout={stdout!r}; stderr={stderr!r}")
    if report is None:
        raise SmokeError("Godot returned success without a skeletal-pose report")
    _validate_report(report, payload, selected, carrier_identity)
    if carrier_path is None:
        _, post_payload = neutral_smoke.preflight(gallery, selected)
        if post_payload != payload:
            raise SmokeError("validated gallery projection changed during the skeletal-pose smoke; refusing to publish a success report")
    else:
        post_module, post_carrier, post_payload, post_profiles, post_instances = _validated_carrier_input(
            gallery,
            Path(carrier_path),
        )
        post_identity = _carrier_identity(post_carrier, post_module)
        if (
            post_payload != payload
            or post_profiles != selected
            or post_instances != instance_ids
            or post_identity != carrier_identity
        ):
            raise SmokeError("validated carrier or gallery changed during the skeletal-pose smoke; refusing to publish a success report")
    neutral_smoke._publish_report(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", required=True, type=Path, help="absolute completed structural gallery directory")
    parser.add_argument("--carrier", type=Path, help="optional absolute disposable avatar-input carrier path")
    parser.add_argument("--profile-id", action="append", dest="profile_ids", help="repeat exactly twice; defaults to the compact and tall frozen IDs")
    parser.add_argument("--report", required=True, type=Path, help="absolute report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        profile_ids = tuple(args.profile_ids) if args.profile_ids is not None else (None if args.carrier is not None else DEFAULT_PROFILE_IDS)
        report = run_skeletal_pose_smoke(args.gallery, profile_ids, args.report, args.carrier)
    except SmokeError as exc:
        print(f"skeletal pose smoke failed: {exc}", file=sys.stderr)
        return 2
    print(neutral_smoke._canonical_json(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

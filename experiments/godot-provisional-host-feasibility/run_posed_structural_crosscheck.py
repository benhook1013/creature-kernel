#!/usr/bin/env python3
"""Run a disposable two-profile Godot posed-structural host cross-check.

The neutral smoke owns the validator, frozen profile selection, pinned launcher
resolution, temporary-project isolation, diagnostics, safe publication, and
post-run gallery revalidation.  This consumer only changes the Godot script
and validates the posed-structural report produced by that script.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any


EXPERIMENT_ROOT = Path(__file__).resolve().parent
NEUTRAL_RUNNER_PATH = EXPERIMENT_ROOT / "run_structural_gallery_smoke.py"
GODOT_SCRIPT = EXPERIMENT_ROOT / "posed_structural_crosscheck.gd"


def _load_neutral_runner():
    spec = importlib.util.spec_from_file_location(
        "neutral_structural_gallery_smoke_for_posed_crosscheck",
        NEUTRAL_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load existing neutral smoke runner: {NEUTRAL_RUNNER_PATH}")
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
REPORT_SCHEMA = "creature-kernel.disposable-godot-posed-structural-crosscheck.v1"
REPORT_BOUNDARY = "host_local_posed_structural_crosscheck"
REPORT_CLAIMS = ["host-local posed structural consumption"]
REPORT_FLAGS = {
    "physics_stepping": False,
    "animation": False,
    "semantic_pose_injection": False,
    "contact": False,
    "deformation": False,
    "render_output": False,
    "adapter": False,
}
TOLERANCE = 2.0e-5


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


def _finite_bounds(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"min", "max"}:
        return False
    return all(
        isinstance(vector, list)
        and len(vector) == 3
        and all(isinstance(axis, (int, float)) and not isinstance(axis, bool) and math.isfinite(axis) for axis in vector)
        for vector in value.values()
    )


def _validate_report(report: Any, payload: dict[str, Any], profile_ids: tuple[str, str]) -> None:
    if not isinstance(report, dict):
        raise SmokeError("Godot report is not a JSON object")
    if report.get("schema") != REPORT_SCHEMA or report.get("status") != "success":
        raise SmokeError("Godot posed-structural report schema or status is invalid")
    if report.get("boundary") != REPORT_BOUNDARY:
        raise SmokeError("Godot report boundary is invalid")
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
    if report.get("coordinate_rule") != {
        "kind": "disposable_host_local_identity",
        "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
        "scope": REPORT_BOUNDARY,
        "profile_translations": [list(value) for value in EXPECTED_TRANSLATIONS],
    }:
        raise SmokeError("Godot report coordinate rule is invalid")
    if report.get("claims") != REPORT_CLAIMS:
        raise SmokeError("Godot report contains a claim outside the host-local posed structural boundary")
    if report.get("scope_flags") != REPORT_FLAGS:
        raise SmokeError("Godot report scope flags are not explicitly fail-closed")

    actual_profiles = report.get("profiles")
    if not isinstance(actual_profiles, list) or any(not isinstance(item, dict) for item in actual_profiles):
        raise SmokeError("Godot report profile records are incomplete or reordered")
    if [item.get("profile_id") for item in actual_profiles] != list(profile_ids):
        raise SmokeError("Godot report profile records are incomplete or reordered")
    for index, (actual, expected) in enumerate(zip(actual_profiles, payload["profiles"])):
        profile_id = profile_ids[index]
        metrics = expected["metrics"]
        if actual.get("candidate_profile_sha256") != expected["candidate_profile_sha256"]:
            raise SmokeError(f"Godot report profile {profile_id} identity differs from the validated projection")
        if not neutral_smoke._values_close(actual.get("metrics"), metrics):
            raise SmokeError(f"Godot report profile {profile_id} metrics differ from the validated projection")
        expected_counts = {
            "neutral_vertex_count": metrics["neutral_vertex_count"],
            "posed_vertex_count": metrics["posed_vertex_count"],
            "face_count": metrics["face_count"],
            "bone_count": 18,
            "proxy_count": 18,
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
        if any(counts[key] != value for key, value in expected_counts.items()):
            raise SmokeError(f"Godot report profile {profile_id} structural counts are invalid")
        if counts["influence_count"] < metrics["neutral_vertex_count"]:
            raise SmokeError(f"Godot report profile {profile_id} has invalid influence counts")
        if not neutral_smoke._bounds_close(actual.get("posed_mesh_aabb"), metrics["posed_bounds"], TOLERANCE):
            raise SmokeError(f"Godot report profile {profile_id} posed bounds differ from metrics")
        if not _finite_bounds(actual.get("posed_proxy_aabb")):
            raise SmokeError(f"Godot report profile {profile_id} posed proxy bounds are invalid")
        if actual.get("profile_translation") != list(EXPECTED_TRANSLATIONS[index]):
            raise SmokeError(f"Godot report profile {profile_id} translation is not fixed host-only separation")
        node_counts = actual.get("node_counts")
        if not isinstance(node_counts, dict):
            raise SmokeError(f"Godot report profile {profile_id} node counts are invalid")
        neutral_smoke._validate_exact_count_map(
            node_counts,
            ("profile_root", "mesh_instance_3d", "static_body_3d", "collision_shape_3d", "skeleton_3d", "total_profile_nodes"),
            f"Godot report profile {profile_id} node_counts",
        )
        if node_counts != {
            "profile_root": 1,
            "mesh_instance_3d": 1,
            "static_body_3d": 1,
            "collision_shape_3d": 18,
            "skeleton_3d": 0,
            "total_profile_nodes": 21,
        }:
            raise SmokeError(f"Godot report profile {profile_id} node counts are invalid")
        crosscheck = actual.get("crosscheck")
        if not isinstance(crosscheck, dict):
            raise SmokeError(f"Godot report profile {profile_id} cross-check evidence is incomplete")
        neutral_smoke._validate_exact_count_map(
            crosscheck,
            ("posed_vertices_recomputed", "posed_normals_recomputed", "posed_proxy_endpoints_recomputed"),
            f"Godot report profile {profile_id} crosscheck",
        )
        if crosscheck != {
            "tolerance": TOLERANCE,
            "posed_vertices_recomputed": metrics["posed_vertex_count"],
            "posed_normals_recomputed": metrics["posed_vertex_count"],
            "posed_proxy_endpoints_recomputed": 36,
            "neutral_and_posed_faces_identical": True,
            "at_least_one_vertex_or_normal_changed": True,
            "bone_ids_parents_lengths_identical": True,
            "weights_validated": True,
            "posed_bounds_match_metrics": True,
            "posed_proxy_separation_checked": True,
            "skeleton_3d_or_skin_binding": False,
        }:
            raise SmokeError(f"Godot report profile {profile_id} cross-check evidence is incomplete")
    first_proxy_max = actual_profiles[0]["posed_proxy_aabb"]["max"][0] + EXPECTED_TRANSLATIONS[0][0]
    second_proxy_min = actual_profiles[1]["posed_proxy_aabb"]["min"][0] + EXPECTED_TRANSLATIONS[1][0]
    if first_proxy_max >= second_proxy_min:
        raise SmokeError("Godot report posed proxy bounds are not separated by the fixed host-only translations")
    neutral_smoke._reject_absolute_paths(report)


def _skip_report_validation(report: Any, payload: dict[str, Any], profile_ids: tuple[str, str]) -> None:
    del report, payload, profile_ids


def _launch_godot(
    gallery: Path,
    profile_ids: tuple[str, str],
    payload: dict[str, Any],
) -> tuple[str, str, int, dict[str, Any] | None]:
    """Reuse the neutral runner's isolated launch with the posed script/report."""
    return neutral_smoke._launch_godot(
        gallery,
        profile_ids,
        payload,
        script=GODOT_SCRIPT,
        validator=_skip_report_validation,
    )


def run_crosscheck(gallery: Path, profile_ids: tuple[str, str] | list[str], report_path: Path) -> dict[str, Any]:
    report_path = neutral_smoke._validate_report_destination(report_path)
    selected = neutral_smoke._validate_profile_ids(profile_ids)
    _, payload = neutral_smoke.preflight(gallery, selected)
    _, stderr, returncode, report = _launch_godot(Path(gallery), selected, payload)
    if returncode != 0:
        raise SmokeError(f"Godot launcher returned exit code {returncode}; stderr={stderr!r}")
    if report is None:
        raise SmokeError("Godot returned success without a report")
    _validate_report(report, payload, selected)
    _, post_payload = neutral_smoke.preflight(gallery, selected)
    if post_payload != payload:
        raise SmokeError("validated gallery projection changed during the posed structural cross-check; refusing to publish a success report")
    neutral_smoke._publish_report(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", required=True, type=Path, help="absolute completed structural gallery directory")
    parser.add_argument("--profile-id", action="append", dest="profile_ids", help="repeat exactly twice; defaults to the compact and tall frozen IDs")
    parser.add_argument("--report", required=True, type=Path, help="absolute report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        profile_ids = tuple(args.profile_ids) if args.profile_ids is not None else DEFAULT_PROFILE_IDS
        report = run_crosscheck(args.gallery, profile_ids, args.report)
    except SmokeError as exc:
        print(f"posed structural cross-check failed: {exc}", file=sys.stderr)
        return 2
    print(neutral_smoke._canonical_json(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run a disposable two-profile Godot structural-gallery host-load smoke."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
PROBE_PATH = REPOSITORY_ROOT / "experiments" / "current-form-surface-preview" / "structural_gallery_evidence_probe.py"
GODOT_SCRIPT = EXPERIMENT_ROOT / "structural_gallery_smoke.gd"
PROJECT_FILE = EXPERIMENT_ROOT / "project.godot"
LAUNCHER = EXPERIMENT_ROOT / "launch_godot_4_7_2.sh"
EXPECTED_GODOT_VERSION = "4.7.2.stable.official.ed1daf0bf"
EXPECTED_GODOT_ENGINE_VERSION_STRING = "4.7.2-stable (official)"
DEFAULT_PROFILE_IDS = (
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
)
FROZEN_PROFILE_IDS = {
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
}
FROZEN_PROFILE_ORDER = (
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
EXPECTED_ARTIFACT_NAMES = (
    "neutral.ply",
    "posed.ply",
    "skeleton.json",
    "weights.json",
    "proxies-neutral.json",
    "proxies-posed.json",
)
EXPECTED_TRANSLATIONS = ((-8.0, 0.0, 0.0), (8.0, 0.0, 0.0))
GODOT_LAUNCH_TIMEOUT_SECONDS = 300


class SmokeError(RuntimeError):
    """A fail-closed preflight, launcher, or report error."""


ReportValidator = Callable[[Any, dict[str, Any], tuple[str, str]], None]
_GODOT_DIAGNOSTIC_RE = re.compile(
    r"(?im)^[ \t]*(?:ERROR:|(?:ERROR:[ \t]*)?(?:ObjectDB|RID)\b.*\b(?:leak|leaked|leaks)\b)"
)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _require_exact_non_boolean_int(value: Any, where: str) -> int:
    if type(value) is not int:
        raise SmokeError(f"{where} must be an exact non-boolean integer")
    return value


def _validate_exact_count_map(value: Any, keys: tuple[str, ...], where: str) -> None:
    if not isinstance(value, dict):
        raise SmokeError(f"{where} must be a JSON object")
    for key in keys:
        if key not in value:
            raise SmokeError(f"{where}.{key} is missing")
        _require_exact_non_boolean_int(value[key], f"{where}.{key}")


def _require_absolute(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise SmokeError(f"{label} must be an absolute path: {path}")
    return path


def _reject_symlink_path_components(path: Path, label: str) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise SmokeError(f"{label} or one of its parent components is a symlink: {path}")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _validate_report_destination(report_path: Path) -> Path:
    report_path = _require_absolute(report_path, "report path")
    _reject_symlink_path_components(report_path, "report path")
    if report_path.exists() and report_path.is_dir():
        raise SmokeError(f"report path is a directory: {report_path}")
    if not report_path.parent.is_dir():
        raise SmokeError(f"report parent directory is unavailable: {report_path.parent}")
    return report_path


def _load_probe():
    if not PROBE_PATH.is_file():
        raise SmokeError(f"structural gallery evidence probe is unavailable: {PROBE_PATH}")
    spec = importlib.util.spec_from_file_location("structural_gallery_evidence_probe_for_godot_smoke", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise SmokeError(f"could not dynamically load structural gallery evidence probe: {PROBE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _validate_profile_ids(profile_ids: tuple[str, str] | list[str]) -> tuple[str, str]:
    selected = tuple(profile_ids)
    if len(selected) != 2:
        raise SmokeError("exactly two profile IDs are required")
    if selected[0] == selected[1]:
        raise SmokeError(f"duplicate profile identity rejected: {selected[0]}")
    for profile_id in selected:
        if profile_id not in FROZEN_PROFILE_IDS:
            raise SmokeError(f"unknown frozen profile identity rejected: {profile_id}")
    return selected


def _artifact_record(artifact: Any) -> dict[str, Any]:
    return {"path": artifact.path, "sha256": artifact.sha256, "bytes": artifact.bytes}


def _bounds_record(bounds: Any) -> dict[str, list[float]]:
    return {"min": list(bounds[0]), "max": list(bounds[1])}


def _metrics_record(metrics: Any) -> dict[str, Any]:
    return {
        "format": metrics.format,
        "profile_id": metrics.profile_id,
        "neutral_vertex_count": metrics.neutral_vertex_count,
        "posed_vertex_count": metrics.posed_vertex_count,
        "face_count": metrics.face_count,
        "bone_count": metrics.bone_count,
        "proxy_count": metrics.proxy_count,
        "neutral_bounds": _bounds_record(metrics.neutral_bounds),
        "posed_bounds": _bounds_record(metrics.posed_bounds),
        "pose_rule_count": metrics.pose_rule_count,
        "source_joint_frame_policy": metrics.source_joint_frame_policy,
        "gallery_global_world_bound": _bounds_record(metrics.gallery_global_world_bound),
    }


def _profile_record(profile: Any) -> dict[str, Any]:
    artifacts = (
        profile.neutral_mesh,
        profile.posed_mesh,
        profile.skeleton,
        profile.weights,
        profile.neutral_proxies,
        profile.posed_proxies,
    )
    return {
        "profile_id": profile.profile_id,
        "label": profile.label,
        "candidate_profile_sha256": profile.identity.candidate_profile_sha256,
        "artifacts": [_artifact_record(artifact) for artifact in artifacts],
        "metrics": _metrics_record(profile.metrics),
    }


def _validated_payload(view: Any, profile_ids: tuple[str, str]) -> dict[str, Any]:
    by_id = {profile.profile_id: profile for profile in view.profiles}
    return {
        "projection_contract": view.projection_contract,
        "manifest_sha256": view.manifest_sha256,
        "manifest_bytes": view.manifest_bytes,
        "godot_version": EXPECTED_GODOT_VERSION,
        "profile_ids": list(profile_ids),
        "pose_id": view.pose_id,
        "pose_sha256": view.pose_sha256,
        "boundary": view.boundary,
        "profiles": [_profile_record(by_id[profile_id]) for profile_id in profile_ids],
    }


def preflight(gallery: Path, profile_ids: tuple[str, str] | list[str]) -> tuple[Any, dict[str, Any]]:
    """Load the exact validator-backed view and select two distinct records."""
    gallery = _require_absolute(gallery, "gallery path")
    selected = _validate_profile_ids(profile_ids)
    if not gallery.exists() or not gallery.is_dir():
        raise SmokeError(f"completed gallery directory is unavailable: {gallery}")
    probe = _load_probe()
    try:
        view = probe.project_structural_gallery_evidence(gallery)
    except Exception as exc:
        raise SmokeError(f"structural gallery validator/probe failed: {type(exc).__name__}: {exc}") from exc
    if view is None:
        raise SmokeError("validator-backed view rejected the gallery; review sessions and tampered galleries are not accepted")
    if tuple(view.profile_ids) != FROZEN_PROFILE_ORDER:
        raise SmokeError("validated gallery profile identity order is not the frozen order")
    by_id = {profile.profile_id: profile for profile in view.profiles}
    if set(by_id) != set(view.profile_ids) or len(by_id) != len(view.profiles):
        raise SmokeError("validated gallery contains duplicate or inconsistent profile identities")
    for profile_id in selected:
        if profile_id not in by_id:
            raise SmokeError(f"selected profile identity is absent from the validated gallery: {profile_id}")
    selected_profiles = [by_id[profile_id] for profile_id in selected]
    candidate_hashes = [profile.identity.candidate_profile_sha256 for profile in selected_profiles]
    if len(set(candidate_hashes)) != 2:
        raise SmokeError("selected profile candidate identities are not distinct")
    payload = _validated_payload(view, selected)
    return view, payload


def _validate_report(report: Any, payload: dict[str, Any], profile_ids: tuple[str, str]) -> None:
    if not isinstance(report, dict):
        raise SmokeError("Godot report is not a JSON object")
    if report.get("schema") != "creature-kernel.disposable-godot-host-load-smoke.v1" or report.get("status") != "success":
        raise SmokeError("Godot report schema or status is invalid")
    if report.get("boundary") != "host_only_smoke":
        raise SmokeError("Godot report does not declare the host_only_smoke boundary")
    if report.get("godot_version") != EXPECTED_GODOT_VERSION:
        raise SmokeError(f"Godot report version is not exact: {report.get('godot_version')!r}")
    if report.get("godot_engine_version_string") != EXPECTED_GODOT_ENGINE_VERSION_STRING:
        raise SmokeError(f"Godot runtime version string is not exact: {report.get('godot_engine_version_string')!r}")
    if report.get("profile_ids") != list(profile_ids):
        raise SmokeError("Godot report profile IDs do not match the preflight selection")
    expected_hashes = {profile["profile_id"]: profile["candidate_profile_sha256"] for profile in payload["profiles"]}
    if report.get("candidate_profile_sha256") != expected_hashes:
        raise SmokeError("Godot report candidate identity hashes do not match the validated projection")
    expected_gallery = {
        "projection_contract": payload["projection_contract"],
        "manifest_sha256": payload["manifest_sha256"],
        "manifest_bytes": payload["manifest_bytes"],
        "pose_id": payload["pose_id"],
        "pose_sha256": payload["pose_sha256"],
        "boundary": payload["boundary"],
    }
    if report.get("validated_gallery") != expected_gallery:
        raise SmokeError("Godot report validated-gallery identity does not match the projection")
    expected_artifacts = {profile["profile_id"]: profile["artifacts"] for profile in payload["profiles"]}
    if report.get("artifact_hash_identities") != expected_artifacts:
        raise SmokeError("Godot report artifact identities do not match the validated projection")
    if report.get("coordinate_rule") != {
        "kind": "disposable_host_local_identity",
        "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
        "scope": "host_only_smoke",
    }:
        raise SmokeError("Godot report coordinate rule is invalid")
    host_boundary = report.get("host_only_smoke")
    if host_boundary != {
        "boundary": "host_only_smoke",
        "scope": "load two validated neutral structural profiles and instantiate temporary mesh/collision nodes",
        "physics_stepping": False,
        "visual_output": False,
        "claims": [],
    }:
        raise SmokeError("Godot report host_only_smoke boundary details are invalid")
    actual_profiles = report.get("profiles")
    if not isinstance(actual_profiles, list) or any(not isinstance(item, dict) for item in actual_profiles):
        raise SmokeError("Godot report profile records are incomplete or reordered")
    if [item.get("profile_id") for item in actual_profiles] != list(profile_ids):
        raise SmokeError("Godot report profile records are incomplete or reordered")
    for index, (actual, expected) in enumerate(zip(actual_profiles, payload["profiles"])):
        metrics = expected["metrics"]
        if actual.get("candidate_profile_sha256") != expected["candidate_profile_sha256"] or not _values_close(actual.get("metrics"), metrics):
            raise SmokeError(f"Godot report profile {profile_ids[index]} does not match validated metrics/identity")
        expected_counts = {
            "vertex_count": metrics["neutral_vertex_count"],
            "face_count": metrics["face_count"],
            "bone_count": metrics["bone_count"],
            "proxy_count": metrics["proxy_count"],
            "weight_vertex_count": metrics["neutral_vertex_count"],
        }
        counts = actual.get("counts")
        if not isinstance(counts, dict):
            raise SmokeError(f"Godot report profile {profile_ids[index]} structural counts are invalid")
        _validate_exact_count_map(
            counts,
            tuple(expected_counts) + ("influence_count",),
            f"Godot report profile {profile_ids[index]} counts",
        )
        if any(counts[key] != value for key, value in expected_counts.items()):
            raise SmokeError(f"Godot report profile {profile_ids[index]} structural counts are invalid")
        if counts["influence_count"] <= 0:
            raise SmokeError(f"Godot report profile {profile_ids[index]} has no weights")
        mesh_aabb = actual.get("mesh_aabb")
        if not _finite_bounds(mesh_aabb) or not _bounds_close(mesh_aabb, metrics["neutral_bounds"]):
            raise SmokeError(f"Godot report profile {profile_ids[index]} mesh AABB differs from metrics")
        proxy_aabb = actual.get("proxy_aabb")
        if not _finite_bounds(proxy_aabb):
            raise SmokeError(f"Godot report profile {profile_ids[index]} proxy AABB is invalid")
        if actual.get("profile_translation") != list(EXPECTED_TRANSLATIONS[index]):
            raise SmokeError(f"Godot report profile {profile_ids[index]} translation is not fixed host-only separation")
        translated_mesh_aabb = actual.get("translated_mesh_aabb")
        if not _finite_bounds(translated_mesh_aabb) or not _bounds_close(
            translated_mesh_aabb,
            _translated_bounds(mesh_aabb, EXPECTED_TRANSLATIONS[index]),
        ):
            raise SmokeError(f"Godot report profile {profile_ids[index]} translated mesh AABB is inconsistent")
        translated_proxy_aabb = actual.get("translated_proxy_aabb")
        if not _finite_bounds(translated_proxy_aabb) or not _bounds_close(
            translated_proxy_aabb,
            _translated_bounds(proxy_aabb, EXPECTED_TRANSLATIONS[index]),
        ):
            raise SmokeError(f"Godot report profile {profile_ids[index]} translated proxy AABB is inconsistent")
        proxy_segments = actual.get("proxy_segments")
        if not isinstance(proxy_segments, dict):
            raise SmokeError(f"Godot report profile {profile_ids[index]} capsule summary is invalid")
        _validate_exact_count_map(
            proxy_segments,
            ("segment_count", "radius_count"),
            f"Godot report profile {profile_ids[index]} proxy_segments",
        )
        if proxy_segments != {
            "segment_count": metrics["proxy_count"],
            "radius_count": metrics["proxy_count"],
            "capsule_height_rule": "segment_length + 2*radius",
            "positive_y_alignment_checked": True,
        }:
            raise SmokeError(f"Godot report profile {profile_ids[index]} capsule summary is invalid")
        node_counts = actual.get("node_counts")
        if not isinstance(node_counts, dict):
            raise SmokeError(f"Godot report profile {profile_ids[index]} node counts are invalid")
        _validate_exact_count_map(
            node_counts,
            ("profile_root", "mesh_instance_3d", "static_body_3d", "collision_shape_3d", "total_profile_nodes"),
            f"Godot report profile {profile_ids[index]} node_counts",
        )
        if node_counts != {
            "profile_root": 1,
            "mesh_instance_3d": 1,
            "static_body_3d": 1,
            "collision_shape_3d": metrics["proxy_count"],
            "total_profile_nodes": 3 + metrics["proxy_count"],
        }:
            raise SmokeError(f"Godot report profile {profile_ids[index]} node counts are invalid")
    _reject_absolute_paths(report)


def _reject_absolute_paths(value: Any) -> None:
    if isinstance(value, str):
        if value.startswith("/") or (len(value) >= 3 and value[1] == ":" and value[2] in "\\/"):
            raise SmokeError("Godot report contains an absolute path")
    elif isinstance(value, list):
        for item in value:
            _reject_absolute_paths(item)
    elif isinstance(value, dict):
        for item in value.values():
            _reject_absolute_paths(item)


def _bounds_close(actual: Any, expected: Any, tolerance: float = 1.0e-5) -> bool:
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return False
    for key in ("min", "max"):
        left = actual.get(key)
        right = expected.get(key)
        if not isinstance(left, list) or not isinstance(right, list) or len(left) != 3 or len(right) != 3:
            return False
        if any(
            not isinstance(axis, (int, float)) or isinstance(axis, bool) or not math.isfinite(axis)
            for axis in (*left, *right)
        ):
            return False
        if any(abs(float(a) - float(b)) > tolerance for a, b in zip(left, right)):
            return False
    return True


def _finite_bounds(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"min", "max"}:
        return False
    return all(
        isinstance(vector, list)
        and len(vector) == 3
        and all(isinstance(axis, (int, float)) and not isinstance(axis, bool) and math.isfinite(axis) for axis in vector)
        for vector in value.values()
    )


def _translated_bounds(bounds: dict[str, list[float]], translation: tuple[float, float, float]) -> dict[str, list[float]]:
    return {
        key: [value + offset for value, offset in zip(bounds[key], translation)]
        for key in ("min", "max")
    }


def _has_godot_error_diagnostics(stdout: str, stderr: str) -> bool:
    return _GODOT_DIAGNOSTIC_RE.search(f"{stdout}\n{stderr}") is not None


def _values_close(actual: Any, expected: Any, tolerance: float = 1.0e-6) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= tolerance
    if isinstance(actual, dict) and isinstance(expected, dict):
        return set(actual) == set(expected) and all(_values_close(actual[key], expected[key], tolerance) for key in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(_values_close(left, right, tolerance) for left, right in zip(actual, expected))
    return actual == expected


def _read_report(report_path: Path) -> dict[str, Any]:
    try:
        report_bytes = report_path.read_bytes()
        report = json.loads(report_bytes.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SmokeError(f"Godot report cannot be read as finite JSON: {type(exc).__name__}: {exc}") from exc
    if not isinstance(report, dict):
        raise SmokeError("Godot report is not a JSON object")
    return report


def _resolve_pinned_binary() -> Path:
    override_name = "CK_GODOT_4_7_2_BINARY"
    if override_name in os.environ:
        inherited_binary = os.environ[override_name]
        if not inherited_binary:
            raise SmokeError(f"{override_name} must be non-empty when explicitly set")
        pinned_binary = Path(inherited_binary)
    else:
        cache_root = os.environ.get("XDG_CACHE_HOME") or str(Path(os.environ.get("HOME", "")) / ".cache")
        pinned_binary = Path(cache_root) / "creature-kernel" / "godot" / "4.7.2-stable" / "Godot_v4.7.2-stable_linux.x86_64"
    if not pinned_binary.is_absolute():
        raise SmokeError(f"pinned Godot binary path is not absolute: {pinned_binary}")
    return pinned_binary


def _launch_godot(
    gallery: Path,
    profile_ids: tuple[str, str],
    payload: dict[str, Any],
    script: Path | None = None,
    validator: ReportValidator | None = None,
) -> tuple[str, str, int, dict[str, Any] | None]:
    script_source = GODOT_SCRIPT if script is None else script
    report_validator = _validate_report if validator is None else validator
    for required in (PROJECT_FILE, script_source, LAUNCHER):
        if not required.is_file():
            raise SmokeError(f"required Godot smoke file is unavailable: {required}")
    if not os.access(LAUNCHER, os.X_OK):
        raise SmokeError(f"pinned Godot launcher is not executable: {LAUNCHER}")
    with tempfile.TemporaryDirectory(prefix="ck-godot-structural-host-load-") as temporary:
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
        pinned_binary = _resolve_pinned_binary()
        project = Path(temporary) / "project.godot"
        script_path = Path(temporary) / script_source.name
        # Godot never receives the caller-controlled report destination.
        raw_report_path = Path(temporary) / "godot-report.json"
        shutil.copyfile(PROJECT_FILE, project)
        shutil.copyfile(script_source, script_path)
        command = [
            str(LAUNCHER),
            "--headless",
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
        environment = os.environ.copy()
        environment.update({key: str(value) for key, value in isolated_paths.items()})
        environment["CK_GODOT_4_7_2_BINARY"] = str(pinned_binary)
        try:
            completed = subprocess.run(
                command,
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=GODOT_LAUNCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise SmokeError(
                f"Godot launcher exceeded {GODOT_LAUNCH_TIMEOUT_SECONDS}s; "
                f"stdout={exc.stdout!r}; stderr={exc.stderr!r}"
            ) from exc
        except OSError as exc:
            raise SmokeError(f"Godot launcher invocation failed: {type(exc).__name__}: {exc}") from exc
        if completed.returncode != 0:
            return completed.stdout, completed.stderr, completed.returncode, None
        diagnostic = f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        if _has_godot_error_diagnostics(completed.stdout, completed.stderr):
            raise SmokeError(f"Godot launcher emitted error/leak diagnostics; {diagnostic}")
        report = _read_report(raw_report_path)
        report_validator(report, payload, profile_ids)
        return completed.stdout, completed.stderr, completed.returncode, report


def _publish_report(report_path: Path, report: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=report_path.parent,
            prefix=f".{report_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(_canonical_json(report))
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, report_path)
        temporary_path = None
    except OSError as exc:
        raise SmokeError(f"canonical report could not be published: {type(exc).__name__}: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def run_smoke(gallery: Path, profile_ids: tuple[str, str] | list[str], report_path: Path) -> dict[str, Any]:
    report_path = _validate_report_destination(report_path)
    selected = _validate_profile_ids(profile_ids)
    _, payload = preflight(gallery, selected)
    stdout, stderr, returncode, report = _launch_godot(Path(gallery), selected, payload)
    if returncode != 0:
        raise SmokeError(f"Godot launcher returned exit code {returncode}; stdout={stdout!r}; stderr={stderr!r}")
    if report is None:
        raise SmokeError("Godot returned success without a report")
    _, post_payload = preflight(gallery, selected)
    if post_payload != payload:
        raise SmokeError("validated gallery projection changed during the Godot smoke; refusing to publish a success report")
    _publish_report(report_path, report)
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
        report = run_smoke(args.gallery, profile_ids, args.report)
    except SmokeError as exc:
        print(f"structural gallery host-load smoke failed: {exc}", file=sys.stderr)
        return 2
    print(_canonical_json(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

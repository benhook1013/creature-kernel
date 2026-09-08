"""Bounded runner for the local pelvis/hip articulation probe."""

from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


HERE = Path(__file__).resolve().parent
SNAPSHOT_SOURCE = Path("source/experiments/pelvis-hip-articulation")
FROZEN_RENDERER = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot"
    "/source/experiments/pelvis-thigh-transition/render.py"
)
CAPTURE_FILES = (
    "binding.py",
    "capture.py",
    "checks.py",
    "runner.py",
    "README.md",
    "protocol.json",
    "tests/test_binding.py",
    "tests/test_capture.py",
    "tests/test_checks.py",
    "tests/test_integration.py",
    "tests/test_runner.py",
)
CASE_FILES = {
    "calibrated_ordinary_human": ("case_05_rest_L0", "case_05_rest_L2"),
    "calibrated_upright_anthropomorphic": ("case_06_rest_L0", "case_06_rest_L2"),
}
CASE_TITLES = {
    "calibrated_ordinary_human": "human",
    "calibrated_upright_anthropomorphic": "anthro",
}
POSE_TITLES = {
    "rest": "rest",
    "left_flex_15": "L15",
    "left_flex_30": "L30",
    "right_flex_15": "R15",
    "both_flex_20": "both20",
}
UNDERSIDE_POSES = {"rest", "left_flex_30"}


class RunnerError(ValueError):
    """Raised when the bounded runner contract cannot be satisfied."""


def _fail(message: str) -> None:
    raise RunnerError(message)


def _canonical(path: str | os.PathLike[str], label: str) -> Path:
    value = Path(path)
    if not value.is_absolute() or os.path.normpath(str(value)) != str(value):
        _fail(f"{label} must be an absolute canonical path")
    return value


def _regular(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} must be a regular file: {path}")


def _directory(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        _fail(f"{label} must be a regular directory: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RunnerError(f"value is not finite JSON: {exc}") from exc


def _read_json(path: Path) -> tuple[Any, bytes]:
    _regular(path, "JSON input")
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _fail(f"invalid finite UTF-8 JSON: {path}: {exc}")
    return value, raw


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _load_module(name: str, path: Path) -> Any:
    """Load a file by path and register it before executing its body."""
    _regular(path, "dynamic module")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail(f"unable to load dynamic module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
        raise
    return module


def _snapshot_capture(snapshot: Path) -> Any:
    return _load_module(
        "ck_pelvis_hip_snapshot_capture",
        snapshot / SNAPSHOT_SOURCE / "capture.py",
    )


def _require_snapshot(snapshot: str | os.PathLike[str]) -> Path:
    path = _canonical(snapshot, "snapshot")
    _directory(path, "snapshot")
    return path


def _require_absent_output(output: str | os.PathLike[str], snapshot: Path) -> Path:
    path = _canonical(output, "output")
    if path.exists() or path.is_symlink():
        _fail(f"output must be absent: {path}")
    if path.parent != snapshot.parent:
        _fail("output must be a sibling of snapshot")
    if path.parent.is_symlink() or not path.parent.is_dir():
        _fail("output parent must be an existing regular directory")
    return path


def _capture_prepare(snapshot: Path) -> dict[str, Any]:
    capture = _load_module("ck_pelvis_hip_worktree_capture", HERE / "capture.py")
    return dict(capture.prepare(snapshot, CAPTURE_FILES))


def prepare(snapshot: str | os.PathLike[str]) -> dict[str, Any]:
    """Capture the exact source/input set into an absent snapshot."""
    path = _canonical(snapshot, "snapshot")
    if path.exists() or path.is_symlink():
        _fail(f"snapshot must be absent: {path}")
    return _capture_prepare(path)


def verify(snapshot: str | os.PathLike[str]) -> dict[str, Any]:
    """Verify a captured snapshot with its captured helper."""
    path = _require_snapshot(snapshot)
    capture = _snapshot_capture(path)
    return dict(capture.verify(path))


def _manifest_mapping(manifest: Mapping[str, Any]) -> dict[str, Path]:
    inputs = manifest.get("inputs")
    mappings = inputs.get("filename_mappings") if isinstance(inputs, Mapping) else None
    if not isinstance(mappings, list):
        _fail("capture manifest has no input filename mappings")
    result: dict[str, Path] = {}
    for row in mappings:
        if not isinstance(row, Mapping) or not isinstance(row.get("name"), str):
            _fail("capture input filename mapping is malformed")
        relative = Path(str(row.get("snapshot_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            _fail("capture input mapping escapes the snapshot")
        if row["name"] in result:
            _fail(f"duplicate capture input mapping: {row['name']}")
        result[row["name"]] = relative
    return result


def _mapped_input(snapshot: Path, mappings: Mapping[str, Path], name: str) -> Path:
    if name not in mappings:
        _fail(f"capture input mapping is missing: {name}")
    path = snapshot / mappings[name]
    try:
        path.relative_to(snapshot)
    except ValueError:
        _fail(f"capture input mapping escapes the snapshot: {name}")
    return path


def _load_run_inputs(snapshot: Path, manifest: Mapping[str, Any]) -> tuple[
        dict[str, Any], dict[str, Any], dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]]:
    mappings = _manifest_mapping(manifest)
    calibration_inputs, _ = _read_json(
        _mapped_input(snapshot, mappings, "calibration_inputs"))
    calibration_protocol, _ = _read_json(
        _mapped_input(snapshot, mappings, "calibration_protocol"))
    protocol, _ = _read_json(snapshot / SNAPSHOT_SOURCE / "protocol.json")
    if not isinstance(protocol, Mapping) or not isinstance(protocol.get("poses"), list):
        _fail("articulation protocol poses are malformed")
    if len(protocol["poses"]) != 5:
        _fail("articulation protocol must declare exactly five poses")
    if not isinstance(calibration_inputs, Mapping) or not isinstance(calibration_protocol, Mapping):
        _fail("calibration inputs or protocol is malformed")
    input_cases = {row.get("id"): row for row in calibration_inputs.get("cases", [])
                   if isinstance(row, Mapping)}
    protocol_cases = {row.get("id"): row for row in calibration_protocol.get("cases", [])
                      if isinstance(row, Mapping)}
    result: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
    for case_id, (l0_name, l2_name) in CASE_FILES.items():
        case = input_cases.get(case_id)
        calibration_case = protocol_cases.get(case_id)
        if not isinstance(case, Mapping) or not isinstance(calibration_case, Mapping):
            _fail(f"calibration case is missing: {case_id}")
        refs = calibration_case.get("reference_landmarks")
        if not isinstance(refs, Mapping):
            _fail(f"reference landmarks are missing: {case_id}")
        base, _ = _read_json(_mapped_input(snapshot, mappings, l0_name))
        rest, _ = _read_json(_mapped_input(snapshot, mappings, l2_name))
        if not isinstance(base, Mapping) or not isinstance(rest, Mapping):
            _fail(f"rest mesh input is malformed: {case_id}")
        result[case_id] = (dict(base), dict(rest), {
            "case": copy.deepcopy(dict(case)),
            "reference_landmarks": copy.deepcopy(dict(refs)),
        })
    return dict(protocol), dict(calibration_protocol), result


def _identity() -> list[list[float]]:
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def _pose_export(mesh: Mapping[str, Any], points: Mapping[str, Any],
                 angles: Mapping[str, float]) -> dict[str, Any]:
    exported = copy.deepcopy(dict(mesh))
    metadata = exported.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["joints"] = {
        "pelvis": {"pose_matrix": _identity()},
        "left_hip": {"pose_matrix": copy.deepcopy(points["left"]["posed_matrix"])},
        "right_hip": {"pose_matrix": copy.deepcopy(points["right"]["posed_matrix"])},
    }
    metadata["pose_angles_degrees"] = {
        "left": float(angles["left"]), "right": float(angles["right"])
    }
    exported["metadata"] = metadata
    return exported


def _matrix_point(matrix: Any, point: Any) -> list[float]:
    return [sum(float(matrix[row][column]) * (float(point[column]) if column < 3 else 1.0)
                for column in range(4)) for row in range(3)]


def _overlays(points: Mapping[str, Any], refs: Mapping[str, Any]) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    colours = {"left": [211, 77, 77], "right": [55, 112, 213]}
    for side in ("left", "right"):
        row = points[side]["posed_points"]
        colour = colours[side]
        overlays.extend([
            {"start": row["J"], "end": row["T"], "color": colour,
             "label": f"diagnostic {side} J-T frame"},
            {"start": row["J"], "end": row["K"], "color": colour,
             "label": f"diagnostic {side} J-K frame"},
        ])
        for name in ("crest", "asis", "psis"):
            key = f"{name}_{side}"
            if key in refs:
                overlays.append({"start": refs[key], "end": refs[key], "color": colour,
                                 "label": f"diagnostic uncertain {key}"})
        if "trochanter_" + side in refs:
            carried = _matrix_point(points[side]["skin_matrix"], refs["trochanter_" + side])
            overlays.append({"start": carried, "end": carried, "color": colour,
                             "label": f"diagnostic uncertain trochanter_{side}"})
    if "pubic_symphysis" in refs:
        point = refs["pubic_symphysis"]
        overlays.append({"start": point, "end": point, "color": [145, 85, 170],
                         "label": "diagnostic uncertain pubic_symphysis"})
    return overlays


def _joint_evidence(points: Mapping[str, Any], angles: Mapping[str, float]) -> dict[str, Any]:
    return {"schema": "pelvis-hip-articulation-joints-v1",
            "angles_degrees": {"left": float(angles["left"]),
                               "right": float(angles["right"])},
            "joints": {"pelvis": {"pose_matrix": _identity()},
                       "left": copy.deepcopy(points["left"]),
                       "right": copy.deepcopy(points["right"])} }


def _exception(phase: str, exc: BaseException) -> dict[str, str]:
    return {"phase": phase, "type": type(exc).__name__, "message": str(exc)}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _run_case(case_id: str, base: Mapping[str, Any], rest: Mapping[str, Any],
              case: Mapping[str, Any], refs: Mapping[str, Any], protocol: Mapping[str, Any],
              output: Path, binding_module: Any, checks_module: Any,
              render_module: Any) -> dict[str, Any]:
    case_dir = output / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    _write_json(case_dir / "case.json", case)
    _write_json(case_dir / "landmarks.json", refs)
    original_vertices = copy.deepcopy(rest.get("vertices"))
    summary: dict[str, Any] = {"id": case_id, "directory": _relative(case_dir, output),
                               "poses": [], "errors": []}
    binding: dict[str, Any] | None = None
    reloaded_binding: Mapping[str, Any] | None = None
    binding_method_pass = False
    pose_records: dict[str, dict[str, Any]] = {}
    try:
        binding = binding_module.bind(base, rest, case, refs)
        _write_json(case_dir / "binding.json", binding)
        reloaded_binding, _ = _read_json(case_dir / "binding.json")
        if not isinstance(reloaded_binding, Mapping):
            raise RunnerError("reloaded binding is not a mapping")
        summary["binding"] = _relative(case_dir / "binding.json", output)
    except Exception as exc:
        error = _exception("bind", exc)
        summary["errors"].append(error)
        _write_json(case_dir / "error-bind.json", error)

    if binding is not None:
        try:
            binding_report = checks_module.check_binding(base, rest, reloaded_binding, protocol)
            if not isinstance(binding_report, Mapping):
                raise RunnerError("binding checker returned a non-mapping report")
            _write_json(case_dir / "binding-checks.json", binding_report)
            binding_method_pass = bool(binding_report.get("pass"))
            summary["binding_checks"] = _relative(case_dir / "binding-checks.json", output)
        except Exception as exc:
            binding_report = {"schema": "pelvis-hip-articulation-binding-checks-v1",
                              "pass": False, "metrics": {},
                              "errors": [_exception("binding-check", exc)]}
            _write_json(case_dir / "binding-checks.json", binding_report)
            summary["binding_checks"] = _relative(case_dir / "binding-checks.json", output)
            summary["errors"].append(_exception("binding-check", exc))
        summary["binding_method_pass"] = binding_method_pass
        for pose_decl in protocol["poses"]:
            pose_id = pose_decl.get("id") if isinstance(pose_decl, Mapping) else None
            angles = {"left": pose_decl.get("left"), "right": pose_decl.get("right")} \
                if isinstance(pose_decl, Mapping) else {}
            pose_summary: dict[str, Any] = {"id": pose_id, "angles_degrees": angles,
                                            "errors": []}
            pose_dir = case_dir / "poses" / str(pose_id)
            pose_dir.mkdir(parents=True, exist_ok=True)
            try:
                posed = binding_module.pose(rest, binding, angles)
                points = binding_module.joint_points(binding, angles)
                posed = _pose_export(posed, points, angles)
                _write_json(pose_dir / "mesh.json", posed)
                _write_json(pose_dir / "joints.json", _joint_evidence(points, angles))
                reloaded_mesh, _ = _read_json(pose_dir / "mesh.json")
                reloaded_joints, _ = _read_json(pose_dir / "joints.json")
                if not isinstance(reloaded_mesh, Mapping) or not isinstance(reloaded_joints, Mapping):
                    raise RunnerError("reloaded pose evidence is malformed")
                check_report = checks_module.check_pose(
                    rest, reloaded_mesh, reloaded_binding, angles, case, refs, protocol)
                _write_json(pose_dir / "checks.json", check_report)
                technical = ("TECHNICAL PASS"
                             if binding_method_pass and check_report.get("pass")
                             else "TECHNICAL REJECTED")
                render_record = None
                try:
                    render_record = render_module.render_views(
                        reloaded_mesh["vertices"], reloaded_mesh["quads"], pose_dir / "surface.png",
                        f"{CASE_TITLES[case_id]} / {POSE_TITLES.get(str(pose_id), str(pose_id))}",
                        technical, protocol["views"]["bounds"],
                        _overlays(reloaded_joints["joints"], refs),
                        underside=str(pose_id) in UNDERSIDE_POSES, allow_crop=True)
                    _write_json(pose_dir / "render.json", render_record)
                except Exception as exc:
                    error = _exception("render", exc)
                    pose_summary["errors"].append(error)
                    summary["errors"].append({"pose": pose_id, **error})
                    _write_json(pose_dir / "error-render.json", error)
                pose_summary.update({
                    "directory": _relative(pose_dir, output),
                    "mesh": _relative(pose_dir / "mesh.json", output),
                    "joints": _relative(pose_dir / "joints.json", output),
                    "checks": _relative(pose_dir / "checks.json", output),
                    "technical_status": technical,
                    "visual_status": "pending",
                })
                if render_record is not None:
                    pose_summary["render"] = {
                        key: _relative(Path(value), output) if value else None
                        for key, value in render_record.items()
                        if key.endswith("path")
                    }
                pose_records[str(pose_id)] = {"mesh": reloaded_mesh,
                                              "checks": check_report,
                                              "binding": reloaded_binding}
            except Exception as exc:
                error = _exception("pose", exc)
                pose_summary["errors"].append(error)
                summary["errors"].append({"pose": pose_id, **error})
                _write_json(pose_dir / "error-pose.json", error)
            summary["poses"].append(pose_summary)

        try:
            nominal = pose_records.get("left_flex_15")
            if nominal is None:
                raise RunnerError("nominal left_flex_15 pose was not captured")
            counterfactual = protocol.get("pivot_counterfactual")
            if not isinstance(counterfactual, Mapping):
                raise RunnerError("protocol pivot_counterfactual is malformed")
            delta = counterfactual.get("J_left_delta")
            counter_angles = counterfactual.get("pose")
            if not isinstance(delta, list) or len(delta) != 3 or not isinstance(counter_angles, Mapping):
                raise RunnerError("protocol pivot counterfactual delta or pose is malformed")
            if set(counter_angles) != {"left", "right"}:
                raise RunnerError("protocol pivot counterfactual pose must contain left and right")
            shifted_refs = copy.deepcopy(dict(refs))
            shifted_refs["joint_left"] = [float(x) for x in shifted_refs["joint_left"]]
            shifted_refs["joint_left"] = [point + float(offset)
                                           for point, offset in zip(shifted_refs["joint_left"], delta)]
            counter = binding_module.bind(base, rest, case, shifted_refs)
            counter_pose = binding_module.pose(rest, counter, counter_angles)
            counter_points = binding_module.joint_points(counter, counter_angles)
            counter_pose = _pose_export(counter_pose, counter_points, counter_angles)
            counter_dir = case_dir / "counterfactual"
            _write_json(counter_dir / "binding.json", counter)
            _write_json(counter_dir / "mesh.json", counter_pose)
            _write_json(counter_dir / "joints.json", _joint_evidence(counter_points, counter_angles))
            reloaded_counter_binding, _ = _read_json(counter_dir / "binding.json")
            reloaded_counter_mesh, _ = _read_json(counter_dir / "mesh.json")
            reloaded_counter_joints, _ = _read_json(counter_dir / "joints.json")
            if not all(isinstance(item, Mapping) for item in
                       (reloaded_counter_binding, reloaded_counter_mesh, reloaded_counter_joints)):
                raise RunnerError("reloaded counterfactual evidence is malformed")
            counter_checks = checks_module.check_pose(
                rest, reloaded_counter_mesh, reloaded_counter_binding, counter_angles,
                case, shifted_refs, protocol)
            _write_json(counter_dir / "checks.json", counter_checks)
            nominal_vertices = nominal["mesh"]["vertices"]
            counter_vertices = reloaded_counter_mesh["vertices"]
            response = max(math.dist(a, b) for a, b in zip(nominal_vertices, counter_vertices))
            scale = float(nominal["checks"].get("metrics", {}).get("scale", 0.0))
            threshold = float(protocol["checks"]["pivot_counterfactual_response_over_L_min"])
            response_over_l = response / scale if scale > 0.0 else math.inf
            comparison = {
                "schema": "pelvis-hip-articulation-counterfactual-v1",
                "diagnostic_only": True,
                "nominal_pose_id": "left_flex_15",
                "counterfactual_pose": copy.deepcopy(dict(counter_angles)),
                "J_left_delta": copy.deepcopy(delta),
                "max_vertex_delta": response,
                "L": scale,
                "response_over_L": response_over_l,
                "threshold_over_L_min": threshold,
                "threshold_observed": response_over_l >= threshold,
                "weights_unchanged": reloaded_counter_binding["evaluated_weights"] == reloaded_binding["evaluated_weights"],
            }
            _write_json(counter_dir / "comparison.json", comparison)
            summary["counterfactual"] = {
                "directory": _relative(counter_dir, output),
                "binding": _relative(counter_dir / "binding.json", output),
                "mesh": _relative(counter_dir / "mesh.json", output),
                "joints": _relative(counter_dir / "joints.json", output),
                "checks": _relative(counter_dir / "checks.json", output),
                "comparison": _relative(counter_dir / "comparison.json", output),
                "diagnostic_only": True,
                "threshold_observed": comparison["threshold_observed"],
            }
        except Exception as exc:
            error = _exception("counterfactual", exc)
            summary["errors"].append(error)
            _write_json(case_dir / "error-counterfactual.json", error)

    unchanged = rest.get("vertices") == original_vertices
    integrity = {"schema": "pelvis-hip-articulation-rest-integrity-v1",
                 "vertices_unchanged": unchanged,
                 "vertex_count": len(original_vertices) if isinstance(original_vertices, list) else None}
    _write_json(case_dir / "rest-integrity.json", integrity)
    summary["rest_vertices_unchanged"] = unchanged
    if not unchanged:
        summary["errors"].append({"phase": "rest-integrity", "message": "rest vertices changed"})
    return summary


def _write_artifact_manifest(output: Path, capture: Any) -> dict[str, Any]:
    inventory = capture.artifact_manifest(output)
    record = {"schema": "creature-kernel.pelvis-hip-articulation-run-artifacts.v1",
              "self": {"path": "artifact-sha-manifest.json", "sha256": "excluded"},
              "files": inventory["files"]}
    _write_json(output / "artifact-sha-manifest.json", record)
    return record


def run(snapshot: str | os.PathLike[str], output: str | os.PathLike[str]) -> dict[str, Any]:
    """Execute the fixed binding/pose/render budget from a captured snapshot."""
    snapshot_path = _require_snapshot(snapshot)
    output_path = _require_absent_output(output, snapshot_path)
    expected_source = (snapshot_path / SNAPSHOT_SOURCE).resolve()
    if Path.cwd().resolve() != expected_source or HERE != expected_source:
        _fail("run must execute from snapshot/source/experiments/pelvis-hip-articulation")

    capture = _snapshot_capture(snapshot_path)
    before = dict(capture.verify(snapshot_path))
    protocol, calibration_protocol, cases = _load_run_inputs(snapshot_path, before)
    del calibration_protocol
    binding_module = _load_module("ck_pelvis_hip_snapshot_binding", expected_source / "binding.py")
    checks_module = _load_module("ck_pelvis_hip_snapshot_checks", expected_source / "checks.py")
    render_module = _load_module("ck_pelvis_hip_frozen_render", FROZEN_RENDERER)
    output_path.mkdir()
    summaries = []
    run_errors = []
    for case_id in CASE_FILES:
        base, rest, evidence = cases[case_id]
        try:
            summaries.append(_run_case(
                case_id, base, rest, evidence["case"], evidence["reference_landmarks"],
                protocol, output_path, binding_module, checks_module, render_module))
        except Exception as exc:
            error = _exception("case", exc)
            run_errors.append({"case": case_id, **error})
            case_dir = output_path / "cases" / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            _write_json(case_dir / "error-case.json", error)

    after = dict(capture.verify(snapshot_path))
    if before.get("frozen_dependency") != after.get("frozen_dependency"):
        run_errors.append({"phase": "capture-verify", "message": "frozen dependency drifted"})
    for summary in summaries:
        run_errors.extend({"case": summary["id"], **error} for error in summary["errors"])
    report = {
        "schema": "pelvis-hip-articulation-run-v1",
        "status": "completed" if not run_errors else "completed_with_errors",
        "geometry_executed": True,
        "snapshot_path": str(snapshot_path),
        "output_path": str(output_path),
        "protocol_id": protocol.get("id"),
        "poses": [pose.get("id") for pose in protocol["poses"]],
        "cases": summaries,
        "errors": run_errors,
        "invocation": {
            "argv": list(sys.argv),
            "cwd": str(Path.cwd()),
            "python": str(sys.executable),
            "environment": {
                "PYTHONDONTWRITEBYTECODE": os.environ.get("PYTHONDONTWRITEBYTECODE"),
                "CK_CURRENT_FORM_SURFACE_PYTHON": os.environ.get("CK_CURRENT_FORM_SURFACE_PYTHON"),
            },
        },
        "provenance": {
            "capture_manifest_sha256": _sha256(snapshot_path / "manifest.json"),
            "capture_status_before": before.get("status"),
            "capture_status_after": after.get("status"),
            "frozen_dependency": before.get("frozen_dependency"),
            "renderer": {"path": str(FROZEN_RENDERER), "sha256": _sha256(FROZEN_RENDERER)},
            "captured_input_mappings": before.get("inputs", {}).get("filename_mappings", []),
        },
        "no_drift": {
            "capture_verify_before_after": True,
            "rest_vertices_unchanged": all(item.get("rest_vertices_unchanged", False) for item in summaries),
        },
        "artifact_manifest": "artifact-sha-manifest.json",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _write_json(output_path / "run-report.json", report)
    _write_artifact_manifest(output_path, capture)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--snapshot", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--snapshot", required=True)
    run_parser.add_argument("--output", required=True)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.snapshot)
            print(json.dumps({"status": result.get("status"), "snapshot": args.snapshot}, sort_keys=True))
        elif args.command == "run":
            result = run(args.snapshot, args.output)
            print(json.dumps({"status": result["status"], "output": args.output,
                              "errors": len(result["errors"])}, sort_keys=True))
        else:
            result = verify(args.snapshot)
            print(json.dumps({"status": result.get("status"), "snapshot": args.snapshot}, sort_keys=True))
    except (RunnerError, Exception) as exc:
        print(f"pelvis-hip-articulation runner error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

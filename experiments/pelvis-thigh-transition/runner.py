"""Bounded pelvis/thigh experiment runner.

This runner is an evidence harness, not a geometry contract.  It consumes a
captured ``inputs.json``, requires the successor construction/check API, and
keeps unverified render evidence separate from later technical status views.
It never writes back to the source worktree.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NEUTRAL_PACKAGE = ROOT / "experiments/owned-root-assembly-successor"
for module_path in (str(HERE), str(NEUTRAL_PACKAGE)):
    if module_path not in sys.path:
        sys.path.insert(0, module_path)

import render
try:  # The authoritative registered-document module; absence is fail-closed.
    import cases  # type: ignore
except ImportError:  # pragma: no cover - exercised through the admission test
    cases = None

try:  # Tests may replace these exact successor-local modules with mocks.
    import construction  # type: ignore
except ImportError:  # pragma: no cover - fail-closed in _require_apis
    construction = None
try:
    import checks  # type: ignore
except ImportError:  # pragma: no cover - fail-closed in _require_apis
    checks = None


class RunnerError(ValueError):
    """Raised for runner admission or output-contract failures."""


PROFILE_CASE_IDS = (
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
HUMAN_CASE_ID = "ordinary_human_reference"
MAX_WORKERS = 2
CASE_ID = re.compile(r"[^A-Za-z0-9._-]+")
REGISTERED_INPUT_SHA256 = "23132147711c792d3617963323d29e86323ed8539c64dbe9f18b32ce6be43db1"


def _reject(condition: bool, message: str) -> None:
    if condition:
        raise RunnerError(message)


def _json_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, indent=2, separators=(",", ": "),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise RunnerError("value is not deterministic finite JSON") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise RunnerError(f"unable to write {path}") from exc


def _write_json(path: Path, value: Any) -> None:
    _write(path, _json_bytes(value))


def _read_json(path: Path) -> tuple[Any, bytes]:
    try:
        raw = _regular_input(path)
        value = json.loads(raw.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RunnerError(f"inputs are not strict finite UTF-8 JSON: {path}") from exc
    return value, raw


def _canonical_path(value: Any, label: str) -> Path:
    _reject(not isinstance(value, (str, os.PathLike)), f"{label} must be a filesystem path")
    path = Path(value)
    _reject(not path.is_absolute() or os.path.normpath(str(path)) != str(path),
            f"{label} must be an absolute canonical path")
    return path


def _regular_input(path: Path) -> bytes:
    _reject(path.is_symlink() or not path.is_file(), f"inputs file is not a regular file: {path}")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RunnerError(f"unable to read inputs: {path}") from exc
    _reject(len(raw) > 16 * 1024 * 1024, "inputs exceed the bounded 16 MiB limit")
    return raw


def _slug(case_id: str) -> str:
    result = CASE_ID.sub("-", case_id).strip("-._") or "case"
    return result[:96]


def _bounded(value: Any, depth: int = 0) -> Any:
    # Real gate diagnostics include levels, frame reports, rays and hit pairs.
    # This serialization safety bound is not a geometry acceptance threshold.
    _reject(depth > 64, "check result nesting exceeds the bounded depth")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        _reject(not math.isfinite(value), "check result contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        return {str(key): _bounded(item, depth + 1) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_bounded(item, depth + 1) for item in value]
    return str(value)


def _require_apis() -> tuple[Any, Any, Any, Any]:
    """Admit only the successor's exact construction and checker API."""
    if construction is None:
        raise RunnerError("successor construction module is unavailable")
    if checks is None:
        raise RunnerError("successor checks module is unavailable")
    try:
        build = construction.build
        evaluate = construction.evaluate
    except AttributeError as exc:
        raise RunnerError("successor construction must provide build/evaluate") from exc
    try:
        check = checks.check_case
        compare = checks.compare_perturbation
    except AttributeError as exc:
        raise RunnerError("successor checks must provide check_case/compare_perturbation") from exc
    if not all(callable(function) for function in (build, evaluate, check, compare)):
        raise RunnerError("successor construction/check entrypoints must be callable")
    return build, evaluate, check, compare


def build_case(case: Mapping[str, Any]) -> Any:
    """Build through the exact successor API; case IDs never enter geometry."""
    build, _, _, _ = _require_apis()
    return build(case["components"], case["attachments"], diagnostic=True)


def evaluate_case(built: Any, case: Mapping[str, Any]) -> Any:
    """Evaluate exactly L0/L1/L2 through the successor API."""
    _, evaluate, _, _ = _require_apis()
    return evaluate(built, levels=2)


def _levels(evaluation: Any) -> tuple[Any, ...]:
    if type(evaluation) is not list or len(evaluation) != 3:
        raise RunnerError("construction.evaluate must return [L0, L1, L2]")
    return tuple(evaluation)


def _mesh_parts(mesh: Any) -> tuple[tuple[tuple[float, float, float], ...], tuple[tuple[int, int, int, int], ...]]:
    _reject(not isinstance(mesh, Mapping), "mesh level must be a mapping")
    vertices, quads = mesh["vertices"], mesh["quads"]
    _reject(not (isinstance(vertices, (list, tuple)) and isinstance(quads, (list, tuple))),
            "mesh must expose concrete vertices and quads")
    points = []
    for index, point in enumerate(vertices):
        _reject(not (isinstance(point, (list, tuple)) and len(point) == 3),
                f"mesh vertex {index} is not a vector3")
        converted = tuple(float(value) for value in point)
        _reject(not all(math.isfinite(value) for value in converted),
                f"mesh vertex {index} is non-finite")
        points.append(converted)
    _reject(not points, "mesh has no vertices")
    faces = []
    for index, face in enumerate(quads):
        _reject(not (isinstance(face, (list, tuple)) and len(face) == 4),
                f"mesh quad {index} is not a quad")
        _reject(not all(type(value) is int for value in face),
                f"mesh quad {index} has a non-integer index")
        converted = tuple(face)
        _reject(not (len(set(converted)) == 4 and all(0 <= value < len(points) for value in converted)),
                f"mesh quad {index} has invalid indices")
        faces.append(converted)
    _reject(not faces, "mesh has no quads")
    return tuple(points), tuple(faces)


def _mesh_record(mesh: Any, level: int) -> tuple[dict[str, Any], tuple[tuple[float, float, float], ...], tuple[tuple[int, int, int, int], ...]]:
    points, faces = _mesh_parts(mesh)
    required_metadata = ("face_owners", "control_owners", "loops",
                         "base_stencils", "frames", "metadata")
    _reject(not isinstance(mesh, Mapping), "mesh level must be a mapping")
    for key in required_metadata:
        _reject(key not in mesh, f"mesh level is missing required metadata: {key}")
    record = {"schema": "creature-kernel.pelvis-thigh-transition-mesh.v1",
              "level": level, "vertices": [list(point) for point in points],
              "quads": [list(face) for face in faces]}
    record.update({key: _bounded(mesh[key]) for key in required_metadata})
    return record, points, faces


def check_case(case: Mapping[str, Any], levels: Any) -> Any:
    """Run the exact successor checker."""
    _, _, check, _ = _require_apis()
    return check(case, levels)


def compare_perturbation(base_case: Mapping[str, Any], base_levels: Any,
                         perturbation_case: Mapping[str, Any], levels: Any) -> Any:
    """Run the exact successor perturbation checker."""
    _, _, _, compare = _require_apis()
    return compare(base_case, base_levels, perturbation_case, levels)


def _case_bounds(case_id: str) -> dict[str, Any]:
    if case_id == HUMAN_CASE_ID:
        lower = [[-0.30, -0.42, -0.20], [0.30, 0.16, 0.20]]
        full = [[-0.56, -0.48, -0.32], [0.56, 0.80, 0.32]]
        return {"lowercrop": lower, "fullroot": full,
                "physical_scale": "human reference uses intentional 0.16 physical scale; not an anthropomorphic size claim"}
    return {"lowercrop": [[-2.40, -2.70, -1.30], [2.40, 1.00, 1.30]],
            "fullroot": [[-3.50, -3.00, -2.00], [3.50, 5.00, 2.00]],
            "physical_scale": "anthropomorphic shared source frame"}


def _source_overlays(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    attachments = case.get("attachments", {})
    overlays = []
    colours = {"left": [48, 112, 210], "right": [210, 72, 56]}
    if isinstance(attachments, Mapping):
        for side in ("left", "right"):
            item = attachments.get(side)
            if not isinstance(item, Mapping) or "centre" not in item or "knee" not in item:
                continue
            overlays.append({"start": list(item["centre"]), "end": list(item["knee"]),
                             "color": colours[side],
                             "label": f"source {side} thigh direction intent"})
    return overlays


def _check_outcome(value: Any) -> tuple[str, Any]:
    checked = _bounded(value)
    _reject(not isinstance(checked, Mapping), "checker report must be a mapping")
    _reject(not isinstance(checked.get("schema"), str) or not checked["schema"],
            "checker report is missing schema")
    if checked["schema"] == "pelvis-thigh-transition/checks-v1":
        technical = checked.get("technical")
        rendering = checked.get("render")
        _reject(not isinstance(technical, Mapping) or type(technical.get("pass")) is not bool,
                "checker report is missing technical.pass")
        _reject(not isinstance(rendering, Mapping) or type(rendering.get("safe")) is not bool,
                "checker report is missing render.safe")
        return ("technical_pass" if technical["pass"] else "rejected"), checked
    outcome = checked.get("outcome")
    _reject(outcome not in ("pass", "reject"),
            "checker report is missing explicit outcome pass/reject")
    return ("technical_pass" if outcome == "pass" else "rejected"), checked


def _exception(value: BaseException, phase: str) -> dict[str, str]:
    return {"phase": phase, "type": type(value).__name__, "message": str(value)[:2000]}


def _render_status(case_dir: Path, points: Any, faces: Any, bounds: dict[str, Any],
                   overlays: list[dict[str, Any]], title: str, status: str,
                   suffix: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    renders, errors = [], []
    for frame_name, allow_crop in (("lowercrop", True), ("fullroot", False)):
        output = case_dir / f"{frame_name}-{suffix}.png"
        try:
            metadata = render.render_views(
                points, faces, output, title, status,
                bounds=bounds[frame_name], overlays=overlays,
                underside=True, allow_crop=allow_crop)
            metadata = dict(metadata)
            for key in ("output_path", "diagnostic_path", "underside_path"):
                value = metadata.get(key)
                if value is not None:
                    metadata[key] = Path(value).relative_to(case_dir).as_posix()
            renders.append({"frame": frame_name, "status": status,
                            "allow_crop": allow_crop, "metadata": metadata})
        except Exception as exc:  # retain render failure and continue the case/check path
            errors.append(_exception(exc, f"render.{frame_name}.{suffix}"))
    return renders, errors


def _case_directory(root: Path, index: int, case_id: str) -> Path:
    path = root / "cases" / f"case-{index:02d}-{_slug(case_id)}"
    _reject(path.exists() or path.is_symlink(), f"case output already exists: {path}")
    path.mkdir(parents=True)
    return path


def _case_manifest(case_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(case_dir.rglob("*"), key=lambda item: item.relative_to(case_dir).as_posix().encode("utf-8")):
        if path.is_file() and path.name != "case-manifest.json":
            data = path.read_bytes()
            rows.append({"path": path.relative_to(case_dir).as_posix(),
                         "bytes": len(data), "sha256": _sha256(data)})
    _write_json(case_dir / "case-manifest.json", {"schema": "creature-kernel.pelvis-thigh-transition-case-manifest.v1", "files": rows})
    return rows


def _execute_case(index: int, case: Mapping[str, Any], case_dir: Path) -> dict[str, Any]:
    case_id = str(case.get("id", f"case-{index:02d}"))
    expected_rejection = "invalid" in case_id.lower()
    bounds = _case_bounds(case_id)
    base = {"index": index, "case_id": case_id, "role": case.get("role"),
            "expected_rejection": expected_rejection, "bounds": bounds,
            "overlay_semantics": "source-intention segments only; not bones or hidden structure",
            "exceptions": [], "renders": [], "artifacts": []}
    try:
        built = build_case(case)
        evaluation = evaluate_case(built, case)
        levels = _levels(evaluation)
        mesh_rows = []
        mesh_arrays = []
        for level, mesh in enumerate(levels):
            record, points, faces = _mesh_record(mesh, level)
            _write_json(case_dir / f"mesh-level-{level}.json", record)
            mesh_rows.append({"level": level, "path": f"mesh-level-{level}.json"})
            mesh_arrays.append((points, faces))
        points, faces = mesh_arrays[-1]
        overlays = _source_overlays(case)
        base["source_frame_segments"] = overlays
        unverified, render_errors = _render_status(
            case_dir, points, faces, bounds, overlays, case_id,
            "UNVERIFIED - VISUAL PENDING", "unverified")
        base["renders"] = unverified
        base["exceptions"].extend(render_errors)
        base["artifacts"] = mesh_rows
        base["phase"] = "render_ready"
        _write_json(case_dir / "case-report-unverified.json", base)
        print(f"case {case_id}: renderready", flush=True)
    except Exception as exc:
        base["exceptions"].append(_exception(exc, "build-or-serialize"))
        base["outcome"] = "error"
        base["phase"] = "checkscomplete"
        _write_json(case_dir / "case-report.json", base)
        _case_manifest(case_dir)
        print(f"case {case_id}: checkscomplete error", flush=True)
        return base

    try:
        raw_check = check_case(case, levels)
        technical_outcome, checked = _check_outcome(raw_check)
    except Exception as exc:
        base["exceptions"].append(_exception(exc, "checks.check_case"))
        technical_outcome, checked = "error", {
            "schema": "creature-kernel.pelvis-thigh-transition-runner-error.v1",
            "outcome": "error", "exception": base["exceptions"][-1]}
    if expected_rejection and technical_outcome == "technical_pass":
        technical_outcome = "unexpected_pass"
    accepted_status = "TECHNICAL PASS - VISUAL PENDING" if technical_outcome == "technical_pass" else "REJECTED"
    final_renders, render_errors = _render_status(
        case_dir, points, faces, bounds, overlays, case_id, accepted_status, "final")
    base["exceptions"].extend(render_errors)
    base.update({"outcome": technical_outcome, "expected_rejection_met": expected_rejection and technical_outcome == "rejected",
                 "check_result": checked, "renders_final": final_renders, "phase": "checkscomplete"})
    _write_json(case_dir / "case-report.json", base)
    _case_manifest(case_dir)
    print(f"case {case_id}: checkscomplete {technical_outcome}", flush=True)
    return base


def _load_mesh_record(case_dir: Path, level: int = 2) -> dict[str, Any]:
    value, _ = _read_json(case_dir / f"mesh-level-{level}.json")
    _reject(not isinstance(value, Mapping), "persisted mesh record is not an object")
    return dict(value)


def _load_levels(case_dir: Path) -> list[dict[str, Any]]:
    levels = [_load_mesh_record(case_dir, level) for level in range(3)]
    _levels(levels)
    return levels


def _comparison_pass(value: Any) -> tuple[bool, Any]:
    checked = _bounded(value)
    _reject(not isinstance(checked, Mapping), "perturbation checker report must be a mapping")
    _reject(not isinstance(checked.get("schema"), str) or not checked["schema"],
            "perturbation checker report is missing schema")
    if checked["schema"] == "pelvis-thigh-transition/perturbation-checks-v1":
        _reject(type(checked.get("pass")) is not bool,
                "perturbation checker report is missing pass")
        return checked["pass"], checked
    outcome = checked.get("outcome")
    if outcome in ("pass", "reject"):
        return outcome == "pass", checked
    _reject(type(checked.get("pass")) is not bool,
            "perturbation checker report is missing explicit pass/reject")
    return checked["pass"], checked


def _validate_registered_inputs(input_path: Path, input_raw: bytes) -> None:
    """Require the exact cases.py-generated document and registered digest."""
    _reject(_sha256(input_raw) != REGISTERED_INPUT_SHA256,
            "inputs do not match the registered inputs SHA-256")
    if cases is None:
        raise RunnerError("registered cases.py module is unavailable")
    try:
        result = cases.main(["--check-inputs", str(input_path)])
    except Exception as exc:
        raise RunnerError("inputs do not match the exact cases.py document/schema/inventory") from exc
    _reject(result != 0, "cases.py rejected the registered inputs")


def _compare_perturbations(root: Path, cases: list[Mapping[str, Any]], results: list[Mapping[str, Any]],
                           input_value: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_id = {str(case.get("id")): (case, result) for case, result in zip(cases, results)}
    baseline_id = "standard_neutral_reference"
    _reject(baseline_id not in by_id, "registered inputs are missing the standard neutral baseline")
    baseline_case, baseline_result = by_id[baseline_id]
    if baseline_result.get("outcome") == "error":
        rows = [{"case_id": str(case.get("id")), "outcome": "unverified",
                 "reason": "baseline case did not load"}
                for case in cases if case.get("id") in input_value["perturbation_case_ids"]]
        _write_json(root / "perturbation-comparisons.json", {
            "schema": "creature-kernel.pelvis-thigh-transition-perturbation-comparisons.v1",
            "rows": rows, "failure_count": len(rows)})
        return rows
    baseline_dir = root / "cases" / f"case-{int(baseline_result['index']):02d}-{_slug(baseline_id)}"
    baseline_levels = _load_levels(baseline_dir)
    rows = []
    perturbation_ids = input_value["perturbation_case_ids"]
    for case in cases:
        case_id = str(case.get("id"))
        if case_id not in perturbation_ids:
            continue
        result = by_id.get(case_id, (case, {}))[1]
        row = {"case_id": case_id, "expected_rejection": "invalid" in case_id.lower()}
        if result.get("outcome") == "error":
            row.update({"outcome": "unverified", "reason": "perturbation case did not load"})
        else:
            directory = root / "cases" / f"case-{int(result['index']):02d}-{_slug(case_id)}"
            try:
                comparison_pass, comparison = _comparison_pass(compare_perturbation(
                    baseline_case, baseline_levels, case, _load_levels(directory)))
                technical_outcome = result.get("outcome")
                row.update({"outcome": ("rejected" if technical_outcome == "rejected" else "unexpected_pass")
                            if row["expected_rejection"] else ("compared" if comparison_pass else "failed"),
                            "comparison_pass": comparison_pass,
                            "expected_rejection_met": (not row["expected_rejection"] or technical_outcome == "rejected"),
                            "comparison": _bounded(comparison),
                            "technical_case_outcome": technical_outcome})
            except Exception as exc:
                row.update({"outcome": "error", "exception": _exception(exc, "compare_perturbation")})
        rows.append(row)
    _write_json(root / "perturbation-comparisons.json", {
        "schema": "creature-kernel.pelvis-thigh-transition-perturbation-comparisons.v1",
        "rows": rows,
        "failure_count": sum(1 for row in rows
                              if row.get("comparison_pass") is not True
                              or row.get("outcome") in {"error", "unverified", "unexpected_pass"}),
    })
    return rows


def _root_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().encode("utf-8")):
        if path.is_file() and path.name != "stable-manifest.json":
            data = path.read_bytes()
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": len(data), "sha256": _sha256(data)})
    return rows


def run(inputs: str | os.PathLike[str], output: str | os.PathLike[str], attempt: int, workers: int = 2) -> dict[str, Any]:
    """Run captured cases into a fresh output directory; never mutate inputs/worktree."""
    _require_apis()
    input_path = _canonical_path(inputs, "inputs")
    output_path = _canonical_path(output, "output")
    _reject(not (type(attempt) is int and attempt in (0, 1, 2)), "attempt must be 0, 1, or 2")
    _reject(not (type(workers) is int and 1 <= workers <= MAX_WORKERS), "workers must be 1 or 2")
    input_value, input_raw = _read_json(input_path)
    _reject(not (isinstance(input_value, Mapping) and isinstance(input_value.get("cases"), list)),
            "inputs must be an object with a cases list")
    cases = list(input_value["cases"])
    _reject(not (cases and all(isinstance(case, Mapping) and isinstance(case.get("id"), str) for case in cases)),
            "inputs cases must be non-empty mappings with string IDs")
    _validate_registered_inputs(input_path, input_raw)
    _reject(os.path.lexists(output_path), "output must be absent before the run")
    _reject(not output_path.parent.is_dir() or output_path.parent.is_symlink(),
            "output parent must be a regular existing directory")
    output_path.mkdir()
    _write(output_path / "inputs.json", input_raw)
    _write(output_path / "runner-source.py", Path(__file__).read_bytes())
    case_root = output_path / "cases"
    case_root.mkdir()
    jobs = []
    for index, case in enumerate(cases):
        jobs.append((index, case, _case_directory(output_path, index, str(case["id"]))))
    if workers == 1:
        results = [_execute_case(index, case, directory) for index, case, directory in jobs]
    else:
        results_by_index = {}
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_execute_case, index, case, directory): index
                       for index, case, directory in jobs}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    results_by_index[index] = future.result()
                except Exception as exc:
                    results_by_index[index] = {"index": index, "case_id": str(cases[index]["id"]),
                                              "outcome": "error", "exceptions": [_exception(exc, "worker")],
                                              "phase": "checkscomplete"}
                    print(f"case {cases[index]['id']}: checkscomplete worker-error", flush=True)
        results = [results_by_index[index] for index in range(len(cases))]
    comparisons = _compare_perturbations(output_path, cases, results, input_value)
    comparison_failures = sum(1 for row in comparisons
                              if row.get("comparison_pass") is not True
                              or row.get("outcome") in {"error", "unverified", "unexpected_pass"})
    case_failures = sum(1 for case_result in results
                        if case_result.get("outcome") != "technical_pass"
                        and not case_result.get("expected_rejection_met"))
    root_outcome = "pass" if case_failures == 0 and comparison_failures == 0 else "failed"
    report = {"schema": "creature-kernel.pelvis-thigh-transition-run-report.v1",
              "attempt": attempt, "inputs": {"path": input_path.name, "bytes": len(input_raw), "sha256": _sha256(input_raw)},
              "workers": workers, "case_count": len(cases),
              "cases": results, "perturbation_comparisons": comparisons,
              "outcome": root_outcome, "case_failure_count": case_failures,
              "comparison_failure_count": comparison_failures,
              "visual_acceptance": "pending; parent-owned visual manifest required",
              "candidate_execution": "not performed by validation; this report is produced only when explicitly invoked"}
    _write_json(output_path / "run-report.json", report)
    manifest = {"schema": "creature-kernel.pelvis-thigh-transition-stable-manifest.v1",
                "attempt": attempt, "files": _root_manifest(output_path)}
    _write_json(output_path / "stable-manifest.json", manifest)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the bounded pelvis/thigh transition evidence harness")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--attempt", required=True, type=int, choices=(0, 1, 2))
    parser.add_argument("--workers", type=int, default=2, choices=(1, 2))
    args = parser.parse_args(argv)
    try:
        run(args.inputs, args.output, args.attempt, args.workers)
    except Exception as exc:
        print(f"runner.py: error: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Prepare and run the bounded pelvis source-calibration evidence set.

``prepare`` is stdlib-only and makes an absent, immutable source snapshot.
``run`` is deliberately fail-closed: it must be invoked through the captured
runner and the frozen runtime, and it never imports geometry from the mutable
worktree.  The runner records diagnostics; it does not accept a policy gate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shutil
import stat
import sys
from typing import Any, Iterable, Mapping


HERE = Path(__file__).resolve().parent
FROZEN_ROOT = Path("/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot")
CALIBRATION_RELATIVE = Path("experiments/pelvis-source-calibration")
CAPTURE_NAMES = (
    "inputs.py",
    "runner.py",
    "section_diagnostic.py",
    "README.md",
    "protocol.json",
    "tests/test_inputs.py",
    "tests/test_section_diagnostic.py",
)
CONTROL_IDS = (
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
RUNNER_SCHEMA = "creature-kernel.pelvis-source-calibration-run.v1"


class RunnerError(ValueError):
    """Raised for snapshot, runtime, or evidence-contract failures."""


def _fail(message: str) -> "NoReturn":
    raise RunnerError(message)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(path: str | os.PathLike[str], label: str) -> Path:
    value = Path(path)
    if not value.is_absolute() or os.path.normpath(str(value)) != str(value):
        _fail(f"{label} must be an absolute canonical path")
    return value


def _regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        _fail(f"{label} is unavailable: {path}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail(f"{label} must be a regular non-symlink file: {path}")


def _strict_json(path: Path) -> tuple[Any, bytes]:
    _regular(path, "JSON input")
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _fail(f"invalid finite UTF-8 JSON: {path}")
    return value, raw


def _json_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, indent=2, separators=(",", ": "), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise RunnerError("value is not deterministic finite JSON") from exc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _inventory(root: Path, paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix().encode("utf-8")):
        _regular(path, "inventory entry")
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        })
    return rows


def _inventory_digest(rows: Any) -> str:
    return _sha256_bytes(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _source_entries(manifest: Mapping[str, Any], root: Path) -> list[dict[str, Any]]:
    entries = manifest.get("source")
    if not isinstance(entries, list) or not entries:
        _fail("frozen manifest source inventory is missing")
    verified = []
    for row in entries:
        if not isinstance(row, Mapping) or set(row) != {"bytes", "path", "sha256", "snapshot_path"}:
            _fail("frozen manifest source row does not match its actual schema")
        relative = Path(str(row["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            _fail(f"frozen source row is not relative: {relative}")
        path = root / "source" / relative
        _regular(path, "frozen source entry")
        actual = {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
        if actual != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            _fail(f"frozen source entry drifted: {relative}")
        verified.append(dict(row))
    return verified


def _runtime_entries(manifest: Mapping[str, Any], root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runtime = manifest.get("runtime")
    if not isinstance(runtime, Mapping):
        _fail("frozen manifest runtime record is missing")
    required = {"clone_root", "executable", "candidate_environment", "files"}
    if not required.issubset(runtime):
        _fail("frozen manifest runtime record does not match its actual schema")
    files = runtime["files"]
    if not isinstance(files, list) or not files:
        _fail("frozen manifest runtime file inventory is missing")
    verified = []
    runtime_root = root / "runtime"
    for row in files:
        if not isinstance(row, Mapping) or set(row) != {"bytes", "path", "runtime_sha256", "sha256", "source_path"}:
            _fail("frozen manifest runtime row does not match its actual schema")
        relative = Path(str(row["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            _fail(f"frozen runtime row is not relative: {relative}")
        path = runtime_root / relative
        _regular(path, "frozen runtime entry")
        actual = {"bytes": path.stat().st_size, "runtime_sha256": _sha256_file(path)}
        if actual != {"bytes": row["bytes"], "runtime_sha256": row["runtime_sha256"]}:
            _fail(f"frozen runtime entry drifted: {relative}")
        verified.append(dict(row))
    return verified, dict(runtime)


def _dependency_identity(root: Path) -> dict[str, Any]:
    root = _canonical(root, "frozen dependency root")
    manifest_path = root / "manifest.json"
    environment_path = root / "environment.json"
    manifest, manifest_raw = _strict_json(manifest_path)
    environment, _environment_raw = _strict_json(environment_path)
    if not isinstance(manifest, Mapping) or manifest.get("schema") != "pelvis-thigh-transition-source-snapshot.v1":
        _fail("frozen dependency manifest schema is not pelvis-thigh-transition-source-snapshot.v1")
    if not isinstance(environment, Mapping):
        _fail("frozen environment record is not an object")
    sources = _source_entries(manifest, root)
    runtime_files, runtime = _runtime_entries(manifest, root)
    if Path(str(runtime["clone_root"])).resolve() != (root / "runtime").resolve():
        _fail("frozen runtime clone_root does not match the selected dependency root")
    executable = root / "runtime/bin/python"
    if Path(str(runtime["executable"])).resolve() != executable.resolve():
        _fail("frozen runtime executable does not match runtime/bin/python")
    source_packages = runtime.get("source_packages_before")
    source_packages_after = runtime.get("source_packages_after")
    if not isinstance(source_packages, Mapping) or not isinstance(source_packages_after, Mapping):
        _fail("frozen runtime package inventories are missing")
    if source_packages.get("inventory_sha256") != source_packages_after.get("inventory_sha256"):
        _fail("frozen runtime package inventory changed between recorded copies")
    source_by_path = {row["path"]: row for row in sources}
    construction = source_by_path.get("experiments/pelvis-thigh-transition/construction.py")
    if construction is None:
        _fail("frozen manifest lacks old pelvis construction.py")
    return {
        "root": str(root),
        "manifest": {
            "path": str(manifest_path),
            "sha256": _sha256_bytes(manifest_raw),
            "schema": manifest["schema"],
            "source_root": manifest.get("source_root"),
            "source_entries": sources,
            "source_inventory_sha256": _inventory_digest(sources),
            "construction": dict(construction),
        },
        "runtime": {
            "clone_root": runtime["clone_root"],
            "executable": runtime["executable"],
            "candidate_environment": runtime["candidate_environment"],
            "file_count": len(runtime_files),
            "files_inventory_sha256": _inventory_digest(runtime_files),
            "files": runtime_files,
        },
        "environment": {
            "path": str(environment_path),
            "python_version": environment.get("python_version"),
            "python_implementation": environment.get("python_implementation"),
            "sys_prefix": environment.get("sys_prefix"),
            "package_versions": environment.get("package_versions"),
            "compiled_import_errors": environment.get("compiled_import_errors"),
            "limitations": [
                "The prepare phase is stdlib-only and does not load compiled geometry/render dependencies.",
                "The run phase is bound to the recorded frozen runtime and source snapshot.",
            ],
        },
    }


def _load_local_inputs(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("ck_calibration_inputs", path)
    if spec is None or spec.loader is None:
        _fail(f"unable to load input preparer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_checked(source: Path, target: Path) -> dict[str, Any]:
    _regular(source, "capture source")
    before = {"bytes": source.stat().st_size, "sha256": _sha256_file(source)}
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    _regular(target, "captured source")
    after = {"bytes": target.stat().st_size, "sha256": _sha256_file(target)}
    if after != before:
        _fail(f"capture differs from source-before identity: {source}")
    return {"path": target.relative_to(target.parents[2]).as_posix(), **before}


def prepare(output: str | os.PathLike[str]) -> dict[str, Any]:
    """Capture the calibration source and concrete cases into an absent path."""
    sys.dont_write_bytecode = True
    output_path = _canonical(output, "prepare output")
    if output_path.exists() or output_path.is_symlink():
        _fail(f"prepare output must be absent: {output_path}")
    if not output_path.parent.is_dir() or output_path.parent.is_symlink():
        _fail("prepare output parent must be an existing regular directory")

    input_module = _load_local_inputs(HERE / "inputs.py")
    protocol_path = HERE / "protocol.json"
    protocol, protocol_raw = _strict_json(protocol_path)
    frozen_root = Path(str(protocol["frozen_dependency_root"])) if isinstance(protocol, Mapping) else FROZEN_ROOT
    dependency_before = _dependency_identity(frozen_root)
    source_paths = [HERE / name for name in CAPTURE_NAMES]
    source_before = _inventory(HERE, source_paths)
    document = input_module.build_document()
    concrete = input_module.json_bytes(document)

    output_path.mkdir()
    captured_root = output_path / "source" / CALIBRATION_RELATIVE
    captured_rows = []
    for source in source_paths:
        target = captured_root / source.relative_to(HERE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        _regular(target, "captured source")
        captured_rows.append({
            "path": target.relative_to(output_path / "source").as_posix(),
            "bytes": target.stat().st_size,
            "sha256": _sha256_file(target),
        })
    input_target = captured_root / "inputs.json"
    input_target.write_bytes(concrete)
    captured_rows.append({
        "path": input_target.relative_to(output_path / "source").as_posix(),
        "bytes": len(concrete),
        "sha256": _sha256_bytes(concrete),
    })
    _write_json(output_path / "source/manifest.json", {
        "schema": "creature-kernel.pelvis-source-calibration-captured-source.v1",
        "files": sorted(captured_rows, key=lambda row: row["path"].encode("utf-8")),
    })

    source_after = _inventory(HERE, source_paths)
    dependency_after = _dependency_identity(frozen_root)
    if source_before != source_after:
        _fail("calibration source changed while being captured")
    if dependency_before != dependency_after:
        _fail("frozen dependency changed while preparing the snapshot")
    report = {
        "schema": "creature-kernel.pelvis-source-calibration-prepare.v1",
        "status": "prepared",
        "geometry_executed": False,
        "render_executed": False,
        "protocol": {"path": "source/experiments/pelvis-source-calibration/protocol.json", "sha256": _sha256_bytes(protocol_raw)},
        "concrete_inputs": {"path": "source/experiments/pelvis-source-calibration/inputs.json", "sha256": _sha256_bytes(concrete), "case_count": len(document["cases"])},
        "captured_source": {"files": captured_rows, "before": source_before, "after": source_after},
        "frozen_dependency": {"before": dependency_before, "after": dependency_after, "reused_without_copy": True},
        "limitations": [
            "No geometry, topology, tuning, renderer, or diagnostic body was executed.",
            "The old dependency source and runtime remain referenced by their frozen absolute snapshot and are verified by manifest hashes.",
        ],
    }
    _write_json(output_path / "prepare-report.json", report)
    return report


def _load_captured_source(snapshot: Path) -> tuple[dict[str, Any], bytes]:
    source_root = snapshot / "source"
    manifest_path = source_root / "manifest.json"
    manifest, raw = _strict_json(manifest_path)
    if not isinstance(manifest, Mapping) or manifest.get("schema") != "creature-kernel.pelvis-source-calibration-captured-source.v1":
        _fail("captured source manifest schema is not admitted")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        _fail("captured source manifest has no files")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"bytes", "path", "sha256"}:
            _fail("captured source manifest row is malformed")
        path = source_root / str(row["path"])
        _regular(path, "captured source entry")
        if {"bytes": path.stat().st_size, "sha256": _sha256_file(path)} != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            _fail(f"captured source entry drifted: {row['path']}")
    required = {f"{CALIBRATION_RELATIVE.as_posix()}/{name}" for name in (*CAPTURE_NAMES, "inputs.json")}
    if not required.issubset({str(row["path"]) for row in rows}):
        _fail("captured source does not contain the complete calibration set")
    return dict(manifest), raw


def _load_module(path: Path, name: str) -> Any:
    _regular(path, "captured geometry/render module")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail(f"unable to load captured module: {path}")
    module = importlib.util.module_from_spec(spec)
    # Some frozen modules (notably dataclasses users) inspect their own
    # sys.modules entry while executing.  Register before exec, then remove a
    # partial module if import fails.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
        raise
    if Path(module.__file__).resolve() != path.resolve():
        _fail(f"module resolved away from its frozen path: {name}")
    return module


def _bounded(value: Any, depth: int = 0) -> Any:
    if depth > 32:
        _fail("diagnostic value is too deeply nested")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("diagnostic value is non-finite")
        return value
    if isinstance(value, Mapping):
        return {str(key): _bounded(item, depth + 1) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_bounded(item, depth + 1) for item in value]
    # Runtime/library scalar conversion is admitted only for the known numpy
    # scalar/array types used by the frozen renderer.  Unknown objects must
    # fail rather than become an untraceable string in evidence.
    if type(value).__module__.split(".", 1)[0] == "numpy":
        if hasattr(value, "tolist"):
            return _bounded(value.tolist(), depth + 1)
        if hasattr(value, "item"):
            return _bounded(value.item(), depth + 1)
    _fail(f"unsupported diagnostic serialization type: {type(value).__name__}")


def _mesh_arrays(mesh: Any) -> tuple[list[list[float]], list[list[int]]]:
    if not isinstance(mesh, Mapping):
        _fail("evaluated level is not a mapping")
    vertices = mesh.get("vertices")
    quads = mesh.get("quads")
    if not isinstance(vertices, (list, tuple)) or not isinstance(quads, (list, tuple)):
        _fail("evaluated level lacks concrete vertices/quads")
    points = []
    for index, point in enumerate(vertices):
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            _fail(f"mesh vertex {index} is not a vector3")
        converted = [float(value) for value in point]
        if not all(math.isfinite(value) for value in converted):
            _fail(f"mesh vertex {index} is non-finite")
        points.append(converted)
    faces = []
    for index, face in enumerate(quads):
        if not isinstance(face, (list, tuple)) or len(face) != 4 or not all(type(value) is int for value in face):
            _fail(f"mesh quad {index} is not an integer quad")
        converted = list(face)
        if len(set(converted)) != 4 or any(value < 0 or value >= len(points) for value in converted):
            _fail(f"mesh quad {index} has invalid indices")
        faces.append(converted)
    if not points or not faces:
        _fail("mesh level is empty")
    return points, faces


def _structural_stats(points: list[list[float]], faces: list[list[int]]) -> dict[str, Any]:
    edges: dict[tuple[int, int], int] = defaultdict(int)
    face_graph = [[] for _ in faces]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for offset in range(4):
            edge = tuple(sorted((face[offset], face[(offset + 1) % 4])))
            edges[edge] += 1
            edge_faces[edge].append(face_index)
    for adjacent in edge_faces.values():
        for left in adjacent:
            for right in adjacent:
                if left != right:
                    face_graph[left].append(right)
    components = 0
    unseen = set(range(len(faces)))
    while unseen:
        components += 1
        start = unseen.pop()
        queue = deque([start])
        while queue:
            for neighbour in face_graph[queue.popleft()]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    queue.append(neighbour)
    lengths = []
    for (left, right), count in edges.items():
        if count:
            lengths.append(math.dist(points[left], points[right]))
    return {
        "classification": "structural_diagnostic_only",
        "policy_acceptance": "not_evaluated",
        "vertex_count": len(points),
        "quad_count": len(faces),
        "finite_vertices": True,
        "valid_quad_indices": True,
        "boundary_edge_count": sum(count == 1 for count in edges.values()),
        "nonmanifold_edge_count": sum(count > 2 for count in edges.values()),
        "connected_face_components": components,
        "edge_length_min": min(lengths),
        "edge_length_max": max(lengths),
    }


def _affine_points(points: list[list[float]], scale: float, translation: list[float]) -> list[list[float]]:
    return [[float(value * scale + translation[axis]) for axis, value in enumerate(point)] for point in points]


def _display_case(case: Mapping[str, Any], points: list[list[float]], protocol: Mapping[str, Any]) -> tuple[list[list[float]], float, str]:
    if case["id"] in CONTROL_IDS:
        transform = protocol["historical_display_transform"]
        return _affine_points(points, float(transform["scale"]), [float(value) for value in transform["translation"]]), float(transform["scale"]), "historical_display_affine"
    return points, 1.0, "native_calibration_frame"


def _overlays(case: Mapping[str, Any], protocol_case: Mapping[str, Any] | None, display_mode: str, protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    colours = {"left": [48, 112, 210], "right": [210, 72, 56]}
    for side in ("left", "right"):
        start = list(case["attachments"][side]["centre"])
        end = list(case["attachments"][side]["knee"])
        overlays.append({"start": start, "end": end, "color": [232, 126, 34], "label": f"T-K {side}"})
        if protocol_case is not None:
            landmarks = protocol_case["reference_landmarks"]
            joint = list(landmarks[f"joint_{side}"])
            thigh = list(case["attachments"][side]["centre"])
            overlays.append({"start": joint, "end": thigh, "color": [132, 70, 190], "label": f"J-T {side}"})
    if protocol_case is not None:
        labels = {
            "joint_left": "J left", "joint_right": "J right",
            "crest_left": "crest left", "crest_right": "crest right",
            "asis_left": "ASIS left", "asis_right": "ASIS right",
            "psis_left": "PSIS left", "psis_right": "PSIS right",
            "pubic_symphysis": "pubis",
            "trochanter_left": "trochanter left", "trochanter_right": "trochanter right",
        }
        for name, value in protocol_case["reference_landmarks"].items():
            point = list(value)
            overlays.append({"start": point, "end": point, "color": [30, 150, 90], "label": labels.get(name, name)})
        for side in ("left", "right"):
            point = list(case["attachments"][side]["centre"])
            overlays.append({"start": point, "end": point, "color": colours[side], "label": f"T {side}"})
    if display_mode == "historical_display_affine":
        display_transform = protocol["historical_display_transform"]
        display_scale = float(display_transform["scale"])
        display_translation = [float(value) for value in display_transform["translation"]]
        transform = lambda point: [value * display_scale + display_translation[axis] for axis, value in enumerate(point)]
        overlays = [{**item, "start": transform(item["start"]), "end": transform(item["end"])} for item in overlays]
    return overlays


def _point_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    result = {key: value[key] for key in ("status", "classification", "reason", "parity", "inside_contour_count", "boundary_distance") if key in value}
    if "signed_boundary_distance" in value:
        result["signed_boundary_distance"] = value["signed_boundary_distance"]
    result["nearest_boundary_distance"] = value.get("boundary_distance")
    result["nearest_boundary_distance_signed"] = value.get("signed_boundary_distance")
    return _bounded(result)


def _section_summary(value: Mapping[str, Any], query_y: float) -> dict[str, Any]:
    diagnostics = value.get("diagnostics")
    closed = bool(diagnostics.get("closed_graph")) if isinstance(diagnostics, Mapping) else bool(value.get("closed_graph", False))
    contours = value.get("closed_contours") if isinstance(value.get("closed_contours"), list) else value.get("contours", [])
    contour_bounds = []
    for contour in contours if isinstance(contours, list) else []:
        if not isinstance(contour, list) or not contour:
            continue
        try:
            xs = [float(point[0]) for point in contour]
            zs = [float(point[1]) for point in contour]
            contour_bounds.append({"min_x": min(xs), "max_x": max(xs), "min_z": min(zs), "max_z": max(zs)})
        except (TypeError, ValueError, IndexError):
            contour_bounds = []
            break
    return {
        "y": query_y,
        "status": value.get("status"),
        "classification": value.get("classification"),
        "closed": closed,
        "loop_count": int(value.get("closed_count", 0) or 0),
        "usable": bool(value.get("usable", False)),
        "contour_bounds": contour_bounds,
        "diagnostics": _bounded(value.get("diagnostics", {})),
    }


def _intervals(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    def nested(bounds: Any) -> bool:
        if not isinstance(bounds, list) or len(bounds) != 2:
            return True
        first, second = bounds
        if not isinstance(first, Mapping) or not isinstance(second, Mapping):
            return True
        return ((first["min_x"] <= second["min_x"] and first["max_x"] >= second["max_x"] and first["min_z"] <= second["min_z"] and first["max_z"] >= second["max_z"]) or
                (second["min_x"] <= first["min_x"] and second["max_x"] >= first["max_x"] and second["min_z"] <= first["min_z"] and second["max_z"] >= first["max_z"]))

    intervals: list[list[float]] = []
    current: list[float] | None = None
    for row in rows:
        qualifies = bool(row.get("usable")) and row.get("status") == "CLOSED_SECTION" and int(row.get("loop_count", 0)) == 2 and not nested(row.get("contour_bounds"))
        y = float(row["y"])
        if qualifies and current is None:
            current = [y, y]
        elif qualifies and current is not None:
            current[1] = y
        elif current is not None:
            intervals.append(current)
            current = None
    if current is not None:
        intervals.append(current)
    brackets = []
    for first, second in zip(rows, rows[1:]):
        counts = {int(first.get("loop_count", 0)), int(second.get("loop_count", 0))}
        if counts == {1, 2}:
            brackets.append({"y": [float(first["y"]), float(second["y"])], "loop_counts": [int(first.get("loop_count", 0)), int(second.get("loop_count", 0))]})
    return {"two_loop_ranges": intervals, "one_to_two_boundary_brackets": brackets}


def _diagnostics(section_module: Any, points: list[list[float]], faces: list[list[int]], case: Mapping[str, Any], protocol_case: Mapping[str, Any] | None, protocol: Mapping[str, Any], scale: float) -> dict[str, Any]:
    inspect = section_module.inspect_section
    evaluate = section_module.evaluate_point
    low, high = (float(value) for value in protocol["section_y_limits"])
    sample_count = int(protocol["section_samples"])
    ys = [low + (high - low) * index / (sample_count - 1) for index in range(sample_count)]
    raw_sections = []
    sections = []
    for y in ys:
        raw = inspect(points, faces, y, scale)
        raw_sections.append({"query_y": y, "result": _bounded(raw)})
        sections.append(_section_summary(raw, y))

    if case["id"] in CONTROL_IDS:
        display_transform = protocol["historical_display_transform"]
        display_scale = float(display_transform["scale"])
        display_translation = [float(value) for value in display_transform["translation"]]
    else:
        display_scale = 1.0
        display_translation = [0.0, 0.0, 0.0]

    def query_point(value: list[float]) -> list[float]:
        return [float(item * display_scale + display_translation[axis]) for axis, item in enumerate(value)]

    raw_points = []

    def point(point: list[float]) -> dict[str, Any]:
        query = query_point(point)
        raw = evaluate(points, faces, query, scale)
        raw_points.append({"point": query, "result": _bounded(raw)})
        return _point_summary(raw)

    attachments = case["attachments"]
    t_k = {}
    for side in ("left", "right"):
        start = [float(value) for value in attachments[side]["centre"]]
        knee = [float(value) for value in attachments[side]["knee"]]
        fractions = [float(value) for value in protocol["thigh_axis_segment_samples"]]
        t_k[side] = {
            "T": point(start),
            "K": point(knee),
            "fractions": [{"fraction": fraction, "point": [start[index] + fraction * (knee[index] - start[index]) for index in range(3)], "result": point([start[index] + fraction * (knee[index] - start[index]) for index in range(3)])} for fraction in fractions],
        }
    reference = {}
    j_t = {}
    if protocol_case is not None:
        raw_landmarks = protocol_case["reference_landmarks"]
        reference = {name: {"point": [float(value) for value in values], "result": point([float(value) for value in values])} for name, values in raw_landmarks.items()}
        fractions = [float(value) for value in protocol["joint_to_thigh_segment_samples"]]
        for side in ("left", "right"):
            joint = [float(value) for value in raw_landmarks[f"joint_{side}"]]
            thigh = [float(value) for value in attachments[side]["centre"]]
            j_t[side] = [{"fraction": fraction, "point": [joint[index] + fraction * (thigh[index] - joint[index]) for index in range(3)], "result": point([joint[index] + fraction * (thigh[index] - joint[index]) for index in range(3)])} for fraction in fractions]
    return {
        "frame": "comparison coordinate frame; controls use a display-only affine copy and saved meshes are unchanged",
        "section_samples": sections,
        "observed_bifurcation_intervals": _intervals(sections),
        "expected_bifurcation_interval": protocol_case.get("expected_skin_bifurcation_y_interval") if protocol_case else None,
        "reference_landmarks": reference,
        "joint_to_thigh": j_t,
        "thigh_to_knee": t_k,
        "_raw_section_evidence": raw_sections,
        "_raw_point_evidence": raw_points,
    }


def _exception(exc: BaseException, phase: str) -> dict[str, str]:
    return {"phase": phase, "type": type(exc).__name__, "message": str(exc)[:2000]}


def _load_old_case_document(frozen_root: Path) -> tuple[dict[str, Any], bytes]:
    return _strict_json(frozen_root / "source/experiments/pelvis-thigh-transition/inputs.json")


def _artifact_files(root: Path) -> list[dict[str, Any]]:
    excluded = {"artifact-sha-manifest-before.json", "artifact-sha-manifest-after.json", "run-report.json"}
    paths = [path for path in root.rglob("*") if path.is_file() and path.name not in excluded]
    return _inventory(root, paths)


def run_snapshot(snapshot: str | os.PathLike[str]) -> dict[str, Any]:
    """Execute all seven captured cases once with the frozen old geometry."""
    snapshot_path = _canonical(snapshot, "snapshot")
    if not snapshot_path.is_dir() or snapshot_path.is_symlink():
        _fail(f"snapshot must be a regular directory: {snapshot_path}")
    captured_runner = snapshot_path / "source" / CALIBRATION_RELATIVE / "runner.py"
    if Path(__file__).resolve() != captured_runner.resolve():
        _fail("run must execute from the captured newsource runner via surface_preview_launcher.sh")
    sys.dont_write_bytecode = True
    _load_captured_source(snapshot_path)
    protocol_path = snapshot_path / "source" / CALIBRATION_RELATIVE / "protocol.json"
    protocol, protocol_raw = _strict_json(protocol_path)
    if not isinstance(protocol, Mapping):
        _fail("captured protocol is not an object")
    frozen_root = _canonical(str(protocol["frozen_dependency_root"]), "frozen dependency root")
    # The dependency snapshot intentionally reuses its already-frozen runtime;
    # prepare never copies the 292 MB runtime into the calibration snapshot.
    runtime_path = frozen_root / "runtime/bin/python"
    if not runtime_path.is_file() or runtime_path.is_symlink():
        _fail("frozen dependency runtime executable is unavailable")
    if Path(sys.executable).resolve() != runtime_path.resolve():
        _fail("run interpreter is not the frozen dependency runtime")
    if os.environ.get("CK_CURRENT_FORM_SURFACE_PYTHON") != str(runtime_path):
        _fail("CK_CURRENT_FORM_SURFACE_PYTHON must name the frozen dependency runtime")
    dependency_before = _dependency_identity(frozen_root)
    expected_construction_sha = str(protocol["construction_sha256"])
    if dependency_before["manifest"]["construction"]["sha256"] != expected_construction_sha:
        _fail("frozen construction hash differs from captured protocol")
    input_path = snapshot_path / "source" / CALIBRATION_RELATIVE / "inputs.json"
    input_value, input_raw = _strict_json(input_path)
    if not isinstance(input_value, Mapping) or not isinstance(input_value.get("cases"), list):
        _fail("captured inputs lack cases")
    cases = list(input_value["cases"])
    ids = tuple(case.get("id") for case in cases if isinstance(case, Mapping))
    if len(cases) != 7 or ids != (*CONTROL_IDS, "calibrated_ordinary_human", "calibrated_upright_anthropomorphic") or len(set(ids)) != 7:
        _fail(f"captured cases are not exactly the frozen seven-case set: {ids!r}")
    old_value, _old_raw = _load_old_case_document(frozen_root)
    if old_value["cases"][:5] != cases[:5]:
        _fail("historical controls differ from the frozen predecessor dictionaries")
    output = snapshot_path / "run"
    if output.exists() or output.is_symlink():
        _fail(f"run output must be absent: {output}")
    output.mkdir()
    source_identity_before = _inventory(snapshot_path / "source", [path for path in (snapshot_path / "source").rglob("*") if path.is_file()])
    _write_json(output / "artifact-sha-manifest-before.json", {"schema": "creature-kernel.pelvis-source-calibration-artifacts.v1", "files": [], "source_identity": source_identity_before, "dependency_identity": dependency_before})

    old_source = frozen_root / "source/experiments/pelvis-thigh-transition"
    construction = _load_module(old_source / "construction.py", "ck_frozen_pelvis_construction")
    renderer = _load_module(old_source / "render.py", "ck_frozen_pelvis_render")
    legacy_checks = _load_module(old_source / "checks.py", "ck_frozen_pelvis_legacy_checks")
    section_path = snapshot_path / "source" / CALIBRATION_RELATIVE / "section_diagnostic.py"
    section_module = _load_module(section_path, "ck_captured_section_diagnostic")
    for name in ("build", "evaluate"):
        if not callable(getattr(construction, name, None)):
            _fail(f"frozen construction lacks callable {name}")
    for name in ("render_views",):
        if not callable(getattr(renderer, name, None)):
            _fail(f"frozen renderer lacks callable {name}")
    if not callable(getattr(legacy_checks, "check_case", None)):
        _fail("frozen legacy checks lack callable check_case")
    for name in ("inspect_section", "evaluate_point"):
        if not callable(getattr(section_module, name, None)):
            _fail(f"captured diagnostic lacks callable {name}")

    protocol_cases = {case["id"]: case for case in protocol["cases"]}
    case_reports = []
    for index, case in enumerate(cases):
        case_id = str(case["id"])
        case_dir = output / "cases" / f"case-{index:02d}-{case_id}"
        case_dir.mkdir(parents=True)
        report: dict[str, Any] = {
            "index": index,
            "case_id": case_id,
            "role": case.get("role"),
            "historical_h_gate": {"status": "HISTORICAL_FAIL", "verdict": "fail", "rerun": False, "reason": "The old individual-side H gate/rejected verdict is retained and is not replaced by this diagnostic."},
            "status": "ERROR",
            "exceptions": [],
            "artifacts": [],
        }
        try:
            built = construction.build(case["components"], case["attachments"], diagnostic=True)
            evaluated = construction.evaluate(built, levels=2)
            if not isinstance(evaluated, list) or len(evaluated) != 3:
                _fail("frozen construction.evaluate did not return L0/L1/L2")
            levels = []
            for level, mesh in enumerate(evaluated):
                points, faces = _mesh_arrays(mesh)
                mesh_path = case_dir / f"mesh-L{level}.json"
                mesh_payload = _bounded(mesh)
                if not isinstance(mesh_payload, Mapping):
                    _fail("evaluated mesh is not JSON-safe mapping data")
                mesh_payload = dict(mesh_payload)
                mesh_payload.update({"schema": "creature-kernel.pelvis-source-calibration-mesh.v1", "level": level})
                _write_json(mesh_path, mesh_payload)
                report["artifacts"].append(mesh_path.relative_to(output).as_posix())
                levels.append((points, faces))
            if case_id not in CONTROL_IDS:
                try:
                    legacy_result = legacy_checks.check_case(case, evaluated)
                    legacy_payload = {
                        "schema": "creature-kernel.pelvis-source-calibration-legacy-checks.v1",
                        "classification": "diagnostic_only_old_trial_gates",
                        "calibration_verdict": "not_evaluated",
                        "check_case": _bounded(legacy_result),
                    }
                    report["legacy_checks"] = {
                        "path": "legacy-checks.json",
                        "classification": "diagnostic_only_old_trial_gates",
                        "calibration_verdict": "not_evaluated",
                        "technical_pass": legacy_result.get("technical", {}).get("pass") if isinstance(legacy_result, Mapping) else None,
                        "lower_intersections": [level.get("nonadjacent_lower_intersections") for level in legacy_result.get("technical", {}).get("levels", [])] if isinstance(legacy_result, Mapping) else [],
                        "lower_folds": legacy_result.get("technical", {}).get("final_L2", {}).get("folds") if isinstance(legacy_result, Mapping) else None,
                        "containment": legacy_result.get("technical", {}).get("final_L2", {}).get("containment") if isinstance(legacy_result, Mapping) else None,
                        "upper_inherited": legacy_result.get("regional", {}).get("upper_inherited") if isinstance(legacy_result, Mapping) else None,
                    }
                except Exception as exc:
                    legacy_payload = {
                        "schema": "creature-kernel.pelvis-source-calibration-legacy-checks.v1",
                        "classification": "diagnostic_only_old_trial_gates",
                        "calibration_verdict": "not_evaluated",
                        "exception": _exception(exc, "legacy-checks"),
                    }
                    report["exceptions"].append(_exception(exc, "legacy-checks"))
                    report["legacy_checks"] = {
                        "path": "legacy-checks.json",
                        "classification": "diagnostic_only_old_trial_gates",
                        "calibration_verdict": "not_evaluated",
                        "status": "ERROR",
                    }
                _write_json(case_dir / "legacy-checks.json", legacy_payload)
                report["artifacts"].append((case_dir / "legacy-checks.json").relative_to(output).as_posix())
            points, faces = levels[-1]
            display_points, diagnostic_scale, display_mode = _display_case(case, points, protocol)
            bounds = protocol["view_bounds"]
            surface_meta = renderer.render_views(display_points, faces, case_dir / "surface.png", case_id, "UNVERIFIED - VISUAL PENDING", bounds=bounds, overlays=None, underside=True, allow_crop=True)
            report["artifacts"].extend(path for path in ("cases/" + case_dir.name + "/surface.png", "cases/" + case_dir.name + "/surface-underside.png"))
            overlays = _overlays(case, protocol_cases.get(case_id), display_mode, protocol)
            landmark_base = case_dir / "landmarks-base.png"
            landmark_meta = renderer.render_views(display_points, faces, landmark_base, case_id, "UNVERIFIED - DIAGNOSTIC OVERLAYS", bounds=bounds, overlays=overlays, underside=False, allow_crop=True)
            diagnostic_path = case_dir / "landmarks-base-diagnostic.png"
            if not diagnostic_path.is_file():
                _fail("renderer did not produce the diagnostic overlay image")
            shutil.copyfile(diagnostic_path, case_dir / "landmarks.png")
            report["artifacts"].extend(path for path in ("cases/" + case_dir.name + "/landmarks.png", "cases/" + case_dir.name + "/landmarks-base.png", "cases/" + case_dir.name + "/landmarks-base-diagnostic.png"))
            diagnostics = _diagnostics(section_module, display_points, faces, case, protocol_cases.get(case_id), protocol, diagnostic_scale)
            section_evidence = {
                "schema": "creature-kernel.pelvis-source-calibration-section-evidence.v1",
                "case_id": case_id,
                "frame": diagnostics["frame"],
                "inspect_section": diagnostics.pop("_raw_section_evidence"),
                "evaluate_point": diagnostics.pop("_raw_point_evidence"),
            }
            section_evidence_path = case_dir / "section-evidence.json"
            _write_json(section_evidence_path, section_evidence)
            report["artifacts"].append(section_evidence_path.relative_to(output).as_posix())
            report.update({"status": "DIAGNOSTIC_ONLY", "display_mode": display_mode, "diagnostic_scale": diagnostic_scale, "render": {"surface": _bounded(surface_meta), "landmarks": _bounded(landmark_meta)}, "levels": [{"level": level, "structural": _structural_stats(level_points, level_faces)} for level, (level_points, level_faces) in enumerate(levels)], "diagnostics": diagnostics})
        except Exception as exc:
            report["exceptions"].append(_exception(exc, "case"))
        _write_json(case_dir / "case-report.json", report)
        case_reports.append(report)

    dependency_after = _dependency_identity(frozen_root)
    source_identity_after = _inventory(snapshot_path / "source", [path for path in (snapshot_path / "source").rglob("*") if path.is_file()])
    drift = dependency_before != dependency_after or source_identity_before != source_identity_after
    after_files = _artifact_files(output)
    _write_json(output / "artifact-sha-manifest-after.json", {"schema": "creature-kernel.pelvis-source-calibration-artifacts.v1", "files": after_files, "source_identity": source_identity_after, "dependency_identity": dependency_after})
    report = {
        "schema": RUNNER_SCHEMA,
        "status": "ERROR" if drift else "DIAGNOSTIC_ONLY",
        "geometry_tuning": False,
        "case_count": len(case_reports),
        "cases": case_reports,
        "protocol": {"path": "source/experiments/pelvis-source-calibration/protocol.json", "sha256": _sha256_bytes(protocol_raw)},
        "inputs": {"path": "source/experiments/pelvis-source-calibration/inputs.json", "bytes": len(input_raw), "sha256": _sha256_bytes(input_raw)},
        "old_h_gate": "HISTORICAL_FAIL",
        "freeze": {"source_before": source_identity_before, "source_after": source_identity_after, "dependency_before": dependency_before, "dependency_after": dependency_after, "drift": drift},
        "artifacts": {"before": "artifact-sha-manifest-before.json", "after": "artifact-sha-manifest-after.json"},
        "limitations": [
            "Structural statistics and sections are evidence only; no policy acceptance is calculated.",
            "J is evaluated only as a protocol reference point. It is not inserted into generator inputs or claimed as executable J-to-skin causality.",
            "K samples outside the represented mesh range are reported by the diagnostic as out_of_represented_range, not as inside failures.",
        ],
    }
    _write_json(output / "run-report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded pelvis source-calibration evidence harness")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="capture the source and concrete inputs")
    prepare_parser.add_argument("--output", required=True)
    run_parser = commands.add_parser("run", help="run the captured seven-case set")
    run_parser.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args.output)
        else:
            run_snapshot(args.snapshot)
    except Exception as exc:
        print(f"runner.py: error: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

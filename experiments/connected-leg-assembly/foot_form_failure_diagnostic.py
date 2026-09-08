"""FOOT-004 rejected-candidate preservation adapter.

This adapter executes against an existing immutable captured snapshot only. It
intercepts the shared validator to retain its raw L0 argument, calls the
original validator unchanged, preserves and reports the original exception,
then derives diagnostic L2/renderings from the retained payload when possible.
It never converts a validator failure into acceptance and never runs binding,
collision, poses, or source-response checks.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

runner: Any = None


SOURCE = Path("source/experiments/connected-leg-assembly")
CASES = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")
FACE_INDEX = 326


def _fail(message: str) -> None:
    raise runner.RunnerError(message)


def _read(path: Path) -> tuple[Any, bytes]:
    return runner._read_json(path)


def _case_row(document: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    rows = [row for row in document.get("cases", [])
            if isinstance(row, Mapping) and row.get("id") == case_id]
    if len(rows) != 1:
        _fail(f"inputs lack unique case {case_id}")
    return rows[0]


def _form_row(document: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    rows = [row for row in document.get("cases", [])
            if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(rows) != 1:
        _fail(f"foot-form inputs lack unique case {case_id}")
    return rows[0]


def _source_base(snapshot: Path, manifest: Mapping[str, Any],
                 case: Mapping[str, Any], construction: Any,
                 root_source: Any) -> Mapping[str, Any]:
    # Match the focused FOOT004 test's frozen candidate method exactly:
    # immutable checked-in root reference, then the captured leg builder.
    root_ref = case.get("root_mesh")
    if not isinstance(root_ref, Mapping):
        _fail(f"{case['id']} lacks root_mesh reference")
    root_path = Path(str(root_ref.get("path")))
    expected = str(root_ref.get("sha256"))
    if not root_path.is_file() or runner._sha256(root_path) != expected:
        _fail(f"immutable root identity drifted: {root_path}")
    root, _ = _read(root_path)
    return construction.build(root, case["leg_inputs"])


def _vector_sub(a: list[float], b: list[float]) -> list[float]:
    return [a[i] - b[i] for i in range(3)]


def _cross(a: list[float], b: list[float]) -> list[float]:
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _triangle_normal(vertices: list[list[float]], triangle: list[int]) -> list[float]:
    normal = _cross(_vector_sub(vertices[triangle[1]], vertices[triangle[0]]),
                    _vector_sub(vertices[triangle[2]], vertices[triangle[0]]))
    length = sum(value * value for value in normal) ** 0.5
    return [value / length for value in normal] if length else [0.0, 0.0, 0.0]


def _face_record(mesh: Mapping[str, Any], face_index: int) -> dict[str, Any]:
    vertices = mesh["vertices"]
    quads = mesh.get("quads", mesh.get("faces"))
    if face_index < 0 or face_index >= len(quads):
        return {"status": "unavailable", "reason": "face index outside retained L0"}
    quad = list(quads[face_index])
    triangles = [[quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]]
    band = None
    side = None
    feet = mesh.get("metadata", {}).get("feet", {})
    for candidate_side, data in feet.items():
        for candidate_band, indices in data.get("face_owner_ranges", {}).items():
            if face_index in indices:
                side, band = candidate_side, candidate_band
    return {
        "status": "retained",
        "face_index": face_index,
        "quad_vertex_indices": quad,
        "vertices": [vertices[index] for index in quad],
        "triangles": triangles,
        "triangle_normals": [_triangle_normal(vertices, triangle)
                             for triangle in triangles],
        "owner": mesh.get("face_owners", [None] * len(quads))[face_index],
        "semantic_side": side,
        "semantic_band": band,
    }


def _detail_mesh(mesh: Mapping[str, Any], cutoff_y: float = -0.50) -> dict[str, Any]:
    vertices = mesh["vertices"]
    quads = mesh.get("quads", mesh.get("faces"))
    selected = [list(face) for face in quads
                if all(vertices[index][1] <= cutoff_y for index in face)]
    if not selected:
        _fail("detail crop selected no complete faces")
    original = sorted({index for face in selected for index in face})
    remap = {old: new for new, old in enumerate(original)}
    return {
        "schema": "creature-kernel.connected-foot-form-detail-mesh.v1",
        "level": 2,
        "vertices": [vertices[index] for index in original],
        "quads": [[remap[index] for index in face] for face in selected],
        "metadata": {"crop": "faces wholly within world Y <= -0.50",
                      "capped": False, "original_vertex_indices": original},
    }


def main(snapshot: str, output: str) -> int:
    snapshot_path = Path(snapshot)
    output_path = Path(output)
    adapter_path = Path(__file__).resolve()
    if output_path.exists() or output_path.is_symlink():
        _fail(f"diagnostic output must be absent: {output_path}")
    captured_runner_path = snapshot_path / SOURCE / "runner.py"
    spec = importlib.util.spec_from_file_location(
        "foot_form_diagnostic_captured_runner", captured_runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load captured runner")
    global runner
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    adapter_before = runner._identity(adapter_path)
    manifest = runner.verify(snapshot_path)
    source_root = snapshot_path / SOURCE
    inputs, inputs_raw = _read(source_root / "inputs.json")
    forms, forms_raw = _read(source_root / "foot-form-inputs.json")
    if not isinstance(inputs, Mapping) or not isinstance(forms, Mapping):
        _fail("captured inputs must be objects")

    output_path.mkdir(parents=True)
    (output_path / "diagnostic-adapter.py").write_bytes(adapter_path.read_bytes())
    adapter_copy = runner._identity(output_path / "diagnostic-adapter.py")
    dependency_before = runner._dependency_identity()
    shared = runner._load_module("foot_construction", source_root / "foot_construction.py")
    sys.modules["foot_construction"] = shared
    construction = runner._load_module("construction", source_root / "construction.py")
    root_source = runner._load_module("root_source", source_root / "root_source.py")
    foot_form = runner._load_module("foot_form_construction",
                                    source_root / "foot_form_construction.py")
    original_validator = shared._validate_output
    retained: dict[str, Any] = {}

    def intercept(*args: Any, **kwargs: Any) -> Any:
        retained["payload"] = copy.deepcopy(args[0]) if args else None
        try:
            return original_validator(*args, **kwargs)
        except Exception as exc:
            retained["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise

    shared._validate_output = intercept
    renderer_path = Path(str(manifest["dependency"]["before"]["renderer"]["path"]))
    renderer = runner._load_module("foot_form_diagnostic_renderer", renderer_path)
    results: list[dict[str, Any]] = []
    render_inputs: list[tuple[Path, Mapping[str, Any], Mapping[str, Any]]] = []

    for index, case_id in enumerate(CASES):
        case_dir = output_path / "cases" / f"case-{index:02d}-{case_id}"
        case_dir.mkdir(parents=True)
        retained.clear()
        case = _case_row(inputs, case_id)
        form = _form_row(forms, case_id)
        result: dict[str, Any] = {
            "id": case_id,
            "accepted": False,
            "execution_origin": (
                "original focused test candidate" if index == 0
                else "supplemental frozen-method case generation; not previously run by focused test"
            ),
            "gates_not_run": ["acceptance", "collision", "source-response", "poses"],
        }
        try:
            base = _source_base(snapshot_path, manifest, case, construction, root_source)
            foot_form.build(base, case["leg_inputs"], form)
        except Exception as exc:
            result["candidate_validation"] = {
                "status": "failed",
                "validator": "foot_construction._validate_output",
                "error": retained.get("error", {"type": type(exc).__name__,
                                                     "message": str(exc)}),
            }
        if retained.get("payload") is None:
            result["status"] = "rejected-diagnostic-unavailable"
            result["reason"] = "validator did not expose an L0 payload"
            runner._write_json(case_dir / "case-report.json", runner._jsonable(result))
            results.append(result)
            continue
        raw_l0 = retained["payload"]
        runner._write_json(case_dir / "rejected-foot-L0.json", runner._jsonable(raw_l0))
        result["status"] = "REJECTED DIAGNOSTIC - RAW L0 RETAINED"
        result["raw_l0"] = {"path": str(case_dir / "rejected-foot-L0.json"),
                             "vertices": len(raw_l0["vertices"]),
                             "quads": len(raw_l0["quads"])}
        result["failing_face_326"] = _face_record(raw_l0, FACE_INDEX)
        try:
            levels = foot_form.evaluate(raw_l0, levels=2)
            for level, mesh in enumerate(levels):
                runner._write_json(case_dir / f"rejected-foot-L{level}.json",
                                   runner._jsonable(mesh))
            l2 = levels[-1]
            detail = _detail_mesh(l2)
            runner._write_json(case_dir / "rejected-foot-detail-L2.json",
                               runner._jsonable(detail))
            result["diagnostic_evaluation"] = {
                "status": "completed",
                "levels": [{"level": level, "vertices": len(mesh["vertices"]),
                            "quads": len(mesh["quads"])}
                           for level, mesh in enumerate(levels)],
            }
            render_inputs.append((case_dir, l2, detail))
        except Exception as exc:
            result["diagnostic_evaluation"] = {
                "status": "failed",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        runner._write_json(case_dir / "case-report.json", runner._jsonable(result))
        results.append(result)

    render_errors: list[dict[str, Any]] = []
    if render_inputs:
        full_bounds = runner._bounds([mesh for _path, mesh, _detail in render_inputs])
        detail_bounds = runner._bounds([detail for _path, _mesh, detail in render_inputs])
        for case_dir, mesh, detail in render_inputs:
            full = runner._render_one(
                renderer, mesh, case_dir / "rejected-full-leg-context.png",
                case_dir.name, "FOOT-004 REJECTED DIAGNOSTIC - FULL LEG CONTEXT",
                full_bounds, [],
            )
            small = runner._render_one(
                renderer, detail, case_dir / "rejected-foot-detail.png",
                case_dir.name, "FOOT-004 REJECTED DIAGNOSTIC - FOOT DETAIL",
                detail_bounds, [],
            )
            for label, record in (("full_leg_context", full), ("foot_detail", small)):
                if record.get("status") == "exception":
                    render_errors.append({"case": case_dir.name, "view": label,
                                          "error": record.get("exception")})
            for result in results:
                if result["id"] in case_dir.name:
                    result["renders"] = {"full_leg_context": runner._jsonable(full),
                                          "foot_detail": runner._jsonable(small)}
                    runner._write_json(case_dir / "case-report.json",
                                       runner._jsonable(result))

    adapter_after = runner._identity(adapter_path)
    dependency_after = runner._dependency_identity()
    snapshot_after = runner.verify(snapshot_path)
    report = {
        "schema": "creature-kernel.connected-foot-form-rejected-diagnostic.v1",
        "status": "rejected-diagnostic",
        "accepted": False,
        "source_snapshot": str(snapshot_path),
        "snapshot_manifest": runner._identity(snapshot_path / "manifest.json"),
        "snapshot_post_verify": snapshot_after.get("schema"),
        "diagnostic_adapter": {"before": adapter_before, "captured": adapter_copy,
                               "after": adapter_after,
                               "unchanged": adapter_before == adapter_after},
        "dependency_before": dependency_before,
        "dependency_after": dependency_after,
        "dependency_drift": dependency_before != dependency_after,
        "collision": "not-run",
        "source_response": "not-run",
        "poses": "not-run",
        "render_errors": render_errors,
        "cases": results,
        "foot_form_inputs_sha256": hashlib.sha256(forms_raw).hexdigest(),
        "inputs_sha256": hashlib.sha256(inputs_raw).hexdigest(),
    }
    runner._write_json(output_path / "diagnostic-report.json", runner._jsonable(report))
    files = []
    for path in sorted(output_path.rglob("*"),
                       key=lambda item: item.relative_to(output_path).as_posix()):
        if path.is_file() and path.name != "artifact-manifest.json":
            files.append({"path": path.relative_to(output_path).as_posix(),
                          **runner._identity(path)})
    runner._write_json(output_path / "artifact-manifest.json", {
        "schema": "creature-kernel.connected-foot-form-rejected-diagnostic-artifacts.v1",
        "files": files,
    })
    return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FOOT-004 rejected diagnostic")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.snapshot, args.output))

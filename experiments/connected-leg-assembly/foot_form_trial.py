"""Thin captured FOOT-004 static-surface adapter.

The adapter is intentionally separate from the legacy FOOT-003 trial.  It
rebuilds the calibrated root and connected legs from captured source inputs,
passes one complete ``foot-form-inputs.json`` case row to
``foot_form_construction.build``, evaluates through the captured generic
Catmull--Clark helper, and renders only the resulting L2 surfaces.  It does
not consume cached displayed meshes, run poses, binding, collision, or
acceptance checks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import runner


SOURCE = Path("source/experiments/connected-leg-assembly")
CASES = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")


def _fail(message: str) -> None:
    raise runner.RunnerError(message)


def _read(path: Path) -> tuple[Any, bytes]:
    return runner._read_json(path)


def _case_row(document: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    rows = [row for row in document.get("cases", [])
            if isinstance(row, Mapping) and row.get("id") == case_id]
    if len(rows) != 1:
        _fail(f"captured inputs lack unique case {case_id}")
    return rows[0]


def _form_row(document: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    rows = [row for row in document.get("cases", [])
            if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(rows) != 1:
        _fail(f"foot-form inputs lack unique case {case_id}")
    return rows[0]


def _source_base(snapshot: Path, manifest: Mapping[str, Any],
                 case: Mapping[str, Any], construction: Any,
                 root_source: Any) -> tuple[Mapping[str, Any], dict[str, Any]]:
    case_id = str(case["id"])
    path_map = runner._path_map(manifest)
    source_relative = path_map.get((case_id, "original_case"))
    if source_relative is None:
        _fail(f"captured path map lacks {case_id}.original_case")
    source_case, _ = _read(runner._snapshot_path(snapshot, str(source_relative)))
    rebuilt = root_source.reconstruct_source_case(source_case)
    levels = rebuilt.get("levels") if isinstance(rebuilt, Mapping) else None
    if not isinstance(levels, Mapping) or not isinstance(levels.get("L0"), Mapping):
        _fail("root_source reconstruction must return an L0 mapping")
    base = construction.build(levels["L0"], case["leg_inputs"])
    return base, {
        "materialization": "source-rebuilt",
        "root_provenance": rebuilt.get("provenance", {}),
        "cache_role": "no cached displayed mesh consumed",
    }


def _detail_mesh(mesh: Mapping[str, Any], cutoff_y: float = -0.50) -> dict[str, Any]:
    """Select whole quads below the fixed world-Y detail cut without capping."""
    vertices = mesh["vertices"]
    quads = mesh.get("quads", mesh.get("faces"))
    selected = [list(face) for face in quads
                if all(vertices[index][1] <= cutoff_y for index in face)]
    if not selected:
        _fail("FOOT-004 detail crop selected no complete faces")
    original_indices = sorted({index for face in selected for index in face})
    remap = {old: new for new, old in enumerate(original_indices)}
    return {
        "schema": "creature-kernel.connected-foot-form-detail-mesh.v1",
        "level": 2,
        "vertices": [vertices[index] for index in original_indices],
        "quads": [[remap[index] for index in face] for face in selected],
        "metadata": {
            "crop": "faces wholly within world Y <= -0.50",
            "capped": False,
            "original_vertex_indices": original_indices,
        },
    }


def main(snapshot: str, output: str) -> int:
    snapshot_path = Path(snapshot)
    output_path = Path(output)
    manifest = runner.verify(snapshot_path)
    captured_trial = snapshot_path / SOURCE / "foot_form_trial.py"
    if Path(__file__).resolve() != captured_trial.resolve():
        _fail("foot-form trial must execute from captured source")
    if output_path.exists() or output_path.is_symlink():
        _fail(f"output must be absent: {output_path}")

    source_root = snapshot_path / SOURCE
    inputs, inputs_raw = _read(source_root / "inputs.json")
    form_document, form_raw = _read(source_root / "foot-form-inputs.json")
    if not isinstance(inputs, Mapping) or not isinstance(form_document, Mapping):
        _fail("captured input documents must be objects")

    dependency_before = runner._dependency_identity()
    shared = runner._load_module("foot_construction", source_root / "foot_construction.py")
    sys.modules["foot_construction"] = shared
    construction = runner._load_module("construction", source_root / "construction.py")
    root_source = runner._load_module("root_source", source_root / "root_source.py")
    foot_form = runner._load_module("foot_form_construction",
                                    source_root / "foot_form_construction.py")
    renderer_path = Path(str(manifest["dependency"]["before"]["renderer"]["path"]))
    renderer = runner._load_module("foot_form_frozen_renderer", renderer_path)

    output_path.mkdir(parents=True)
    (output_path / "inputs.json").write_bytes(inputs_raw)
    (output_path / "foot-form-inputs.json").write_bytes(form_raw)
    (output_path / "runner-source.py").write_bytes((source_root / "runner.py").read_bytes())

    results: list[dict[str, Any]] = []
    render_inputs: list[tuple[Path, Mapping[str, Any], Mapping[str, Any]]] = []
    for index, case_id in enumerate(CASES):
        case_dir = output_path / "cases" / f"case-{index:02d}-{case_id}"
        case_dir.mkdir(parents=True)
        case = _case_row(inputs, case_id)
        form_row = _form_row(form_document, case_id)
        base, provenance = _source_base(snapshot_path, manifest, case,
                                        construction, root_source)
        output_l0 = foot_form.build(base, case["leg_inputs"], form_row)
        levels = foot_form.evaluate(output_l0, levels=2)
        for level, mesh in enumerate(levels):
            runner._write_json(case_dir / f"foot-form-L{level}.json",
                               runner._jsonable(mesh))
        detail = _detail_mesh(levels[-1])
        runner._write_json(case_dir / "foot-detail-L2.json",
                           runner._jsonable(detail))
        result = {
            "id": case_id,
            "status": "STATIC CANDIDATE - PENDING COLLISION/VISUAL",
            "accepted": False,
            "materialization": provenance,
            "base": {"vertices": len(output_l0["vertices"]),
                     "quads": len(output_l0["quads"])},
            "levels": [{"level": level, "vertices": len(mesh["vertices"]),
                        "quads": len(mesh["quads"])}
                       for level, mesh in enumerate(levels)],
            "collision": "not-run",
            "poses": "not-run",
        }
        runner._write_json(case_dir / "case-report.json", runner._jsonable(result))
        results.append(result)
        render_inputs.append((case_dir, levels[-1], detail))

    bounds = runner._bounds([mesh for _case_dir, mesh, _detail in render_inputs])
    detail_bounds = runner._bounds([detail for _case_dir, _mesh, detail in render_inputs])
    render_errors: list[dict[str, Any]] = []
    for case_dir, mesh, detail in render_inputs:
        full_record = runner._render_one(
            renderer, mesh, case_dir / "full-leg-context.png", case_dir.name,
            "FOOT-004 STATIC CANDIDATE - PENDING COLLISION/VISUAL",
            bounds, [],
        )
        detail_record = runner._render_one(
            renderer, detail, case_dir / "foot-detail.png", case_dir.name,
            "FOOT-004 DETAIL - STATIC CANDIDATE - PENDING COLLISION/VISUAL",
            detail_bounds, [],
        )
        if full_record.get("status") == "exception":
            render_errors.append({"case": case_dir.name,
                                  "view": "full-leg-context",
                                  "error": full_record.get("exception")})
        if detail_record.get("status") == "exception":
            render_errors.append({"case": case_dir.name,
                                  "view": "foot-detail",
                                  "error": detail_record.get("exception")})
        for result in results:
            if result["id"] in case_dir.name:
                result["render"] = {
                    "full_leg_context": runner._jsonable(full_record),
                    "foot_detail": runner._jsonable(detail_record),
                }
                runner._write_json(case_dir / "case-report.json",
                                   runner._jsonable(result))

    dependency_after = runner._dependency_identity()
    report = {
        "schema": "creature-kernel.connected-foot-form-static-run.v1",
        "status": "error" if render_errors else "static-candidate",
        "accepted": False,
        "geometry_execution": True,
        "collision": "not-run",
        "poses": "not-run",
        "cases": results,
        "bounds": bounds,
        "render_errors": render_errors,
        "dependency_before": dependency_before,
        "dependency_after": dependency_after,
        "dependency_drift": dependency_before != dependency_after,
        "snapshot_manifest": runner._identity(snapshot_path / "manifest.json"),
        "foot_form_inputs_sha256": hashlib.sha256(form_raw).hexdigest(),
    }
    runner._write_json(output_path / "run-report.json", runner._jsonable(report))
    files = []
    for path in sorted(output_path.rglob("*"),
                       key=lambda item: item.relative_to(output_path).as_posix()):
        if path.is_file() and path.name != "artifact-manifest.json":
            files.append({"path": path.relative_to(output_path).as_posix(),
                          **runner._identity(path)})
    runner._write_json(output_path / "artifact-manifest.json", {
        "schema": "creature-kernel.connected-foot-form-static-artifacts.v1",
        "files": files,
    })
    return 1 if report["status"] == "error" else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Captured FOOT-004 static trial")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.snapshot, args.output))

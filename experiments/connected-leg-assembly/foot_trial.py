"""Thin captured static-foot trial around the existing evidence helpers.

This adapter owns only case selection, immutable-parent provenance, output
serialization, and frozen-renderer calls.  Foot validation and Catmull--Clark
evaluation remain in ``foot_construction`` and the captured ``construction``.
No poses, weights, or collision acceptance are introduced here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import runner


SOURCE = Path("source/experiments/connected-leg-assembly")
CASES = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")
PARENT_ENV = "CONNECTED_LEG_PARENT_RUN"


def _fail(message: str) -> None:
    raise runner.RunnerError(message)


def _identity(path: Path) -> dict[str, Any]:
    return {"path": str(path), **runner._identity(path)}


def _read(path: Path) -> tuple[Any, bytes]:
    return runner._read_json(path)


def _parent_base(parent: Path, index: int, case_id: str) -> Path:
    return parent / "cases" / f"case-{index:02d}-{case_id}" / "base.json"


def _parent_inputs(parent: Path, case_id: str, raw: bytes,
                   document: dict[str, Any]) -> dict[str, Any]:
    path = parent / "inputs.json"
    parent_value, parent_raw = _read(path)
    if parent_raw != raw or parent_value != document:
        _fail("005 parent inputs differ from captured inputs")
    rows = [row for row in document.get("cases", [])
            if isinstance(row, dict) and row.get("id") == case_id]
    if len(rows) != 1:
        _fail(f"005 parent inputs lack unique case {case_id}")
    return rows[0]


def _manifest_hash(parent: Path, relative: str) -> str:
    value, _ = _read(parent / "artifact-manifest.json")
    rows = value.get("files", []) if isinstance(value, dict) else []
    matches = [row for row in rows if isinstance(row, dict) and row.get("path") == relative]
    if len(matches) != 1 or not isinstance(matches[0].get("sha256"), str):
        _fail(f"005 artifact manifest lacks {relative}")
    return str(matches[0]["sha256"])


def _install_rejection_capture(foot: Any) -> tuple[dict[str, Any], Any]:
    """Capture the validator payload while preserving the validator outcome.

    This is a diagnostic-only adapter for a post-failure preservation run. It
    does not relax, replace, or reorder production validation: the original
    ``_validate_output`` is called with the original arguments and its
    exception is re-raised. The retained object is the exact candidate L0
    handed to that validator, before any test, binding, collision, pose, or
    acceptance gate.
    """
    original = getattr(foot, "_validate_output", None)
    if not callable(original):
        _fail("foot construction has no _validate_output interception point")
    captured: dict[str, Any] = {"calls": 0, "payload": None, "error": None}

    def capture(*args: Any, **kwargs: Any) -> Any:
        captured["calls"] += 1
        if args:
            captured["payload"] = args[0]
        try:
            return original(*args, **kwargs)
        except Exception as exc:
            captured["error"] = {
                "type": type(exc).__name__, "message": str(exc),
            }
            raise

    foot._validate_output = capture
    return captured, original


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captured static foot candidate")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--parent-run", default=None)
    args = parser.parse_args(argv)

    snapshot = Path(args.snapshot)
    output = Path(args.output)
    parent = Path(args.parent_run or __import__("os").environ.get(PARENT_ENV, ""))
    captured_trial = snapshot / SOURCE / "foot_trial.py"
    if Path(__file__).resolve() != captured_trial.resolve():
        _fail("foot trial must execute from captured source")
    manifest = runner.verify(snapshot)
    if output.exists() or output.is_symlink():
        _fail(f"output must be absent: {output}")
    if not parent.is_dir() or parent.is_symlink():
        _fail(f"parent run must be a regular directory: {parent}")

    source_root = snapshot / SOURCE
    inputs, inputs_raw = _read(source_root / "inputs.json")
    foot_inputs, foot_inputs_raw = _read(source_root / "foot-inputs.json")
    if not isinstance(inputs, dict) or not isinstance(foot_inputs, dict):
        _fail("captured inputs are not objects")
    foot_rows = {row.get("case_id"): row.get("sides")
                 for row in foot_inputs.get("cases", [])
                 if isinstance(row, dict)}
    if set(foot_rows) != set(CASES):
        _fail("foot inputs are not exactly the two calibrated cases")
    parent_rows = [_parent_inputs(parent, case_id, inputs_raw, inputs)
                   for case_id in CASES]
    parent_bases = [_parent_base(parent, index, case_id)
                    for index, case_id in enumerate(CASES)]
    parent_before = [_identity(path) for path in [parent / "inputs.json", *parent_bases]]
    for index, path in enumerate(parent_bases):
        relative = f"cases/case-{index:02d}-{CASES[index]}/base.json"
        if _manifest_hash(parent, relative) != parent_before[index + 1]["sha256"]:
            _fail(f"005 parent base identity differs from its artifact manifest: {path}")

    dependency_before = runner._dependency_identity()
    construction = runner._load_module("construction", source_root / "construction.py")
    foot = runner._load_module("foot_construction", source_root / "foot_construction.py")
    validation_capture, _original_validator = _install_rejection_capture(foot)
    root_source_path = source_root / "root_source.py"
    hip_source_path = source_root / "hip_source.py"
    if root_source_path.exists() != hip_source_path.exists():
        _fail("root_source.py and hip_source.py must be captured together")
    root_source = None
    source_paths = runner._path_map(manifest)
    if root_source_path.is_file():
        root_source = runner._load_module("root_source", root_source_path)
    renderer_path = Path(str(manifest["dependency"]["before"]["renderer"]["path"]))
    renderer = runner._load_module("foot_trial_frozen_renderer", renderer_path)
    output.mkdir()
    (output / "inputs.json").write_bytes(inputs_raw)
    (output / "foot-inputs.json").write_bytes(foot_inputs_raw)
    (output / "runner-source.py").write_bytes((source_root / "runner.py").read_bytes())
    results: list[dict[str, Any]] = []
    render_inputs: list[tuple[Path, Mapping[str, Any], int]] = []

    for index, (case_id, parent_row, parent_base) in enumerate(zip(CASES, parent_rows, parent_bases)):
        case_dir = output / "cases" / f"case-{index:02d}-{case_id}"
        case_dir.mkdir(parents=True)
        report: dict[str, Any] = {"id": case_id, "status": "error", "exceptions": []}
        validation_capture.update({"calls": 0, "payload": None, "error": None})
        try:
            base, _ = _read(parent_base)
            leg_inputs = parent_row.get("leg_inputs")
            foot_row = foot_rows[case_id]
            if root_source is None:
                leg_base = base
                materialization = "legacy-cached-parent"
                source_comparison = None
            else:
                source_relative = source_paths.get((case_id, "original_case"))
                if source_relative is None:
                    _fail(f"captured path map lacks {case_id}.original_case for source rebuild")
                source_case, _ = _read(runner._snapshot_path(snapshot, str(source_relative)))
                rebuilt = root_source.reconstruct_source_case(source_case)
                levels = rebuilt.get("levels") if isinstance(rebuilt, dict) else None
                if not isinstance(levels, dict) or "L0" not in levels:
                    _fail("root_source reconstruction must return L0")
                leg_base = construction.build(levels["L0"], leg_inputs)
                materialization = "source-rebuilt"
                source_comparison = {
                    "cache_role": "comparison-only; cached parent base is never a construction input",
                    "parent_base_exact": leg_base == base,
                    "root_provenance": rebuilt.get("provenance", {}),
                }
            output_l0 = foot.build(leg_base, leg_inputs, foot_row)
            levels = foot.evaluate(output_l0, levels=2)
            for level, mesh in enumerate(levels):
                runner._write_json(case_dir / f"foot-L{level}.json", runner._jsonable(mesh))
            report.update({
                "status": "STATIC CANDIDATE - PENDING COLLISION/VISUAL",
                "materialization": materialization,
                "source_rebuild": source_comparison,
                "parent_base": parent_before[index + 1],
                "base": {"vertices": len(output_l0["vertices"]), "quads": len(output_l0["quads"])},
                "levels": [{"level": level, "vertices": len(mesh["vertices"]),
                            "quads": len(mesh["quads"])} for level, mesh in enumerate(levels)],
                "render": None,
            })
            render_inputs.append((case_dir, levels[-1], len(levels) - 1))
        except Exception as exc:
            report["exceptions"].append({"type": type(exc).__name__, "message": str(exc)})
            retained = validation_capture.get("payload")
            validator_error = validation_capture.get("error")
            if retained is not None and validator_error is not None:
                report.update({
                    "status": "POST-FAILURE PRESERVATION - REJECTED L0 RETAINED",
                    "accepted": False,
                    "candidate_validation": {
                        "status": "failed",
                        "validator": "foot_construction._validate_output",
                        "calls": validation_capture.get("calls"),
                        "error": validator_error,
                    },
                    "gates_not_run": [
                        "connected-leg test suite",
                        "binding",
                        "collision",
                        "pose",
                        "whole-foot acceptance",
                    ],
                    "diagnostic_adapter": {
                        "purpose": "post-failure preservation",
                        "validator_behavior": "original validator called and exception re-raised",
                        "geometry_changed": False,
                    },
                })
                runner._write_json(case_dir / "rejected-foot-L0.json",
                                   runner._jsonable(retained))
                try:
                    rejected_levels = foot.evaluate(retained, levels=2)
                    for level, mesh in enumerate(rejected_levels):
                        runner._write_json(case_dir / f"rejected-foot-L{level}.json",
                                           runner._jsonable(mesh))
                    report["diagnostic_evaluation"] = {
                        "status": "completed",
                        "levels": [{"level": level,
                                    "vertices": len(mesh["vertices"]),
                                    "quads": len(mesh["quads"])}
                                   for level, mesh in enumerate(rejected_levels)],
                    }
                    render_inputs.append((case_dir, rejected_levels[-1],
                                          len(rejected_levels) - 1))
                except Exception as evaluate_exc:
                    report["diagnostic_evaluation"] = {
                        "status": "failed",
                        "exception": {"type": type(evaluate_exc).__name__,
                                       "message": str(evaluate_exc)},
                    }
                    render_inputs.append((case_dir, retained, 0))
                report["rejected_l0"] = {
                    "path": str(case_dir / "rejected-foot-L0.json"),
                    "vertices": len(retained.get("vertices", [])),
                    "quads": len(retained.get("quads", [])),
                }
        runner._write_json(case_dir / "case-report.json", report)
        results.append(report)

    bounds = runner._bounds([mesh for _path, mesh, _level in render_inputs]) if render_inputs else None
    render_errors = []
    for case_dir, mesh, render_level in render_inputs:
        record = runner._render_one(renderer, mesh, case_dir / "static.png",
                                    str(case_dir.name),
                                    f"POST-FAILURE PRESERVATION - REJECTED L{render_level}",
                                    bounds, [])
        record["source_level"] = render_level
        if record.get("status") == "exception":
            render_errors.append({"case": case_dir.name, "error": record["exception"]})
        for report in results:
            if report["id"] in case_dir.name:
                report["render"] = runner._jsonable(record)
                runner._write_json(case_dir / "case-report.json", report)

    dependency_after = runner._dependency_identity()
    parent_after = [_identity(path) for path in [parent / "inputs.json", *parent_bases]]
    source_manifest_after = runner.verify(snapshot)
    drift = dependency_before != dependency_after or parent_before != parent_after
    candidate_failures = any(
        row.get("candidate_validation", {}).get("status") == "failed"
        for row in results
    )
    status = (
        "error" if drift or render_errors else
        "post-failure-preservation" if candidate_failures else
        "static-candidate"
    )
    report = {
        "schema": "creature-kernel.connected-foot-static-run.v1",
        "status": status,
        "full_pass": False,
        "accepted": False,
        "capture_phase": "post-failure-preservation",
        "pre_execution_capture": False,
        "diagnostic_adapter": {
            "source_path": str(source_root / "foot_trial.py"),
            "source_identity": _identity(source_root / "foot_trial.py"),
            "validator": "foot_construction._validate_output",
            "behavior": "capture validator payload, call original, re-raise original failure",
        },
        "collision": "pending_checker",
        "visual": "pending_parent_appraisal",
        "cases": results,
        "bounds": bounds,
        "render_errors": render_errors,
        "parent_run": str(parent),
        "parent_inputs": parent_before[0],
        "parent_bases": parent_before[1:],
        "parent_after": parent_after,
        "dependency_before": dependency_before,
        "dependency_after": dependency_after,
        "dependency_drift": drift,
        "snapshot_manifest": _identity(snapshot / "manifest.json"),
        "source_manifest_verified": source_manifest_after.get("schema"),
        "foot_inputs_sha256": hashlib.sha256(foot_inputs_raw).hexdigest(),
    }
    runner._write_json(output / "run-report.json", report)
    files = []
    for path in sorted(output.rglob("*"), key=lambda item: item.relative_to(output).as_posix().encode()):
        if path.is_file() and path.name != "artifact-manifest.json":
            files.append({"path": path.relative_to(output).as_posix(), **runner._identity(path)})
    runner._write_json(output / "artifact-manifest.json", {
        "schema": "creature-kernel.connected-foot-static-artifacts.v1", "files": files,
    })
    return 1 if status in {"error", "post-failure-preservation"} else 0


if __name__ == "__main__":
    raise SystemExit(main())

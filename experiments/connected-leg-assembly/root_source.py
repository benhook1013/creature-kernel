"""Regenerate connected-leg roots from recorded calibration source cases.

This is a small downstream bridge for the whole-character prerequisite.  It
accepts the recorded calibration case data, loads the same frozen
pelvis-source-calibration dependency used by its runner, and returns the
serializer-normalized L0 and L2 meshes.  It does not read a cached root mesh,
reinterpret source fields, or introduce a new construction method.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
from collections.abc import Mapping
import json
from pathlib import Path
import stat
import sys
from typing import Any


CALIBRATION_SET_ROOT = Path(
    "/home/ben/.cache/creature-kernel/pelvis-source-calibration-set-1"
)
CALIBRATION_SOURCE_MANIFEST_PATH = CALIBRATION_SET_ROOT / "source/manifest.json"
CALIBRATION_RUNNER_RELATIVE = Path(
    "experiments/pelvis-source-calibration/runner.py"
)
CALIBRATION_RUNNER_PATH = (
    CALIBRATION_SET_ROOT / "source" / CALIBRATION_RUNNER_RELATIVE
)
FROZEN_CONSTRUCTION_RELATIVE = Path(
    "source/experiments/pelvis-thigh-transition/construction.py"
)


class SourceReconstructionError(ValueError):
    """Raised when recorded source data or the frozen dependency is unavailable."""


def _regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise SourceReconstructionError(f"{label} is unavailable: {path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise SourceReconstructionError(
            f"{label} must be a regular non-symlink file: {path}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_calibration_runner() -> tuple[Path, dict[str, Any]]:
    _regular(CALIBRATION_SOURCE_MANIFEST_PATH, "calibration source manifest")
    try:
        manifest = json.loads(CALIBRATION_SOURCE_MANIFEST_PATH.read_text(
            encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceReconstructionError(
            f"invalid calibration source manifest: {CALIBRATION_SOURCE_MANIFEST_PATH}"
        ) from exc
    if not isinstance(manifest, Mapping):
        raise SourceReconstructionError("calibration source manifest is not a mapping")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise SourceReconstructionError("calibration source manifest has no files")
    row = next((item for item in rows
                if isinstance(item, Mapping) and
                item.get("path") == CALIBRATION_RUNNER_RELATIVE.as_posix()), None)
    if not isinstance(row, Mapping) or not isinstance(row.get("sha256"), str):
        raise SourceReconstructionError(
            "immutable calibration source manifest lacks the captured runner"
        )
    relative = Path(str(row["path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise SourceReconstructionError("captured runner manifest path is not relative")
    path = CALIBRATION_SET_ROOT / "source" / relative
    if path.resolve() != CALIBRATION_RUNNER_PATH.resolve():
        raise SourceReconstructionError("captured runner resolved to an unexpected path")
    _regular(path, "captured calibration runner")
    if {"bytes": path.stat().st_size, "sha256": _sha256(path)} != {
        "bytes": row.get("bytes"), "sha256": row["sha256"]
    }:
        raise SourceReconstructionError("captured calibration runner identity drifted")
    return path, {"path": str(path), "sha256": str(row["sha256"]),
                  "manifest_path": str(CALIBRATION_SOURCE_MANIFEST_PATH)}


def _load_calibration_runner() -> tuple[Any, dict[str, Any]]:
    path, identity = _verified_calibration_runner()
    spec = importlib.util.spec_from_file_location(
        "ck_connected_leg_calibration_runner", path
    )
    if spec is None or spec.loader is None:
        raise SourceReconstructionError(
            f"unable to load calibration runner: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        if sys.modules.get(spec.name) is module:
            sys.modules.pop(spec.name, None)
        raise SourceReconstructionError(
            f"unable to load calibration runner: {path}"
        ) from exc
    if Path(module.__file__).resolve() != path.resolve():
        raise SourceReconstructionError("calibration runner resolved away from its source path")
    return module, identity


def _load_frozen_construction() -> tuple[Any, dict[str, str]]:
    calibration_runner, runner_identity = _load_calibration_runner()
    dependency = calibration_runner._dependency_identity(
        calibration_runner.FROZEN_ROOT
    )
    construction_entry = dependency["manifest"]["construction"]
    path = calibration_runner.FROZEN_ROOT / FROZEN_CONSTRUCTION_RELATIVE
    construction = calibration_runner._load_module(
        path, "ck_connected_leg_frozen_pelvis_construction"
    )
    return construction, {
        "calibration_runner": runner_identity,
        "frozen_construction": {
            "path": str(path),
            "sha256": str(construction_entry["sha256"]),
            "manifest_path": str(dependency["manifest"]["path"]),
            "dependency_root": str(dependency["root"]),
        },
        "calibration_runner_module": calibration_runner,
    }


def _source_inputs(source_case: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(source_case, Mapping):
        raise SourceReconstructionError("source_case must be a mapping")
    components = source_case.get("components")
    attachments = source_case.get("attachments")
    if not isinstance(components, Mapping):
        raise SourceReconstructionError("source_case.components must be a mapping")
    if not isinstance(attachments, Mapping):
        raise SourceReconstructionError("source_case.attachments must be a mapping")
    return copy.deepcopy(dict(components)), copy.deepcopy(dict(attachments))


def reconstruct_source_case(
        source_case: Any, *, constructor_transform: Any = None) -> dict[str, Any]:
    """Reconstruct serializer-compatible L0 and L2 from one source case.

    ``source_case`` is the recorded calibration case mapping.  Only its
    ``components`` and ``attachments`` are passed to the frozen constructor;
    the source case's provenance and reference-only fields are not converted
    into geometry inputs.  An optional private transform may install a local
    source provider on the freshly verified constructor before the build and
    return supplemental refinement provenance.
    """
    components, attachments = _source_inputs(source_case)
    construction, provenance = _load_frozen_construction()
    supplemental_provenance: dict[str, Any] | None = None
    if constructor_transform is not None:
        if not callable(constructor_transform):
            raise SourceReconstructionError(
                "constructor_transform must be callable when provided"
            )
        try:
            supplemental = constructor_transform(construction, provenance)
        except Exception as exc:
            raise SourceReconstructionError(
                "source-provider constructor transform failed"
            ) from exc
        if not isinstance(supplemental, Mapping):
            raise SourceReconstructionError(
                "source-provider constructor transform must return provenance mapping"
            )
        supplemental_provenance = copy.deepcopy(dict(supplemental))
    build = getattr(construction, "build", None)
    evaluate = getattr(construction, "evaluate", None)
    if not callable(build) or not callable(evaluate):
        raise SourceReconstructionError("frozen construction lacks build/evaluate")
    try:
        built = build(components, attachments, diagnostic=True)
        evaluated = evaluate(built, levels=2)
    except Exception as exc:
        raise SourceReconstructionError(
            "frozen source-case construction/evaluation failed"
        ) from exc
    if not isinstance(evaluated, (list, tuple)) or len(evaluated) != 3:
        raise SourceReconstructionError(
            "frozen construction.evaluate did not return L0/L1/L2"
        )

    result_provenance = dict(provenance)
    calibration_runner = result_provenance.pop("calibration_runner_module")
    levels: dict[str, Any] = {}
    for level in (0, 2):
        value = calibration_runner._bounded(evaluated[level])
        if not isinstance(value, Mapping):
            raise SourceReconstructionError(f"evaluated L{level} is not a mapping")
        mesh = dict(value)
        mesh.update({
            "schema": "creature-kernel.pelvis-source-calibration-mesh.v1",
            "level": level,
        })
        levels[f"L{level}"] = mesh
    return {
        "schema": "creature-kernel.connected-leg-assembly-source-reconstruction.v1",
        "source_case_id": source_case.get("id"),
        "provenance": {
            **result_provenance,
            **({"source_refinement": supplemental_provenance}
               if supplemental_provenance is not None else {}),
        },
        "levels": levels,
    }


__all__ = ["SourceReconstructionError", "reconstruct_source_case"]

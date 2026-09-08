"""Capture and verify inputs for the local pelvis/hip articulation probe.

This module is intentionally a small, stdlib-only evidence helper.  It does
not import geometry, execute a body, or copy the frozen runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Any, Iterable, Mapping, NoReturn

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
FROZEN_DEPENDENCY_ROOT = Path("/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot")
FROZEN_CALIBRATION_ROOT = Path("/home/ben/.cache/creature-kernel/pelvis-source-calibration-set-1")
FROZEN_CALIBRATION_RUNNER = FROZEN_CALIBRATION_ROOT / "source/experiments/pelvis-source-calibration/runner.py"
CALIBRATION_SOURCE_MANIFEST = FROZEN_CALIBRATION_ROOT / "source/manifest.json"
CALIBRATION_PREPARE_REPORT = FROZEN_CALIBRATION_ROOT / "prepare-report.json"
CALIBRATION_ARTIFACT_MANIFEST = FROZEN_CALIBRATION_ROOT / "run/artifact-sha-manifest-after.json"
CALIBRATION_ARTIFACT_MANIFEST_SHA256 = "f0152de5b6b82a60c35599b0b82af746704d1917446d8fceb88b2ca016275871"
CONSTRUCTION_SHA256 = "7fd457e2206165eb5e404ce81732f4157234a2e13a64008d96ae75d6abcf5cdb"

STANDARD_FILE_NAMES = ("capture.py", "tests/test_capture.py", "README.md", "protocol.json")
INPUT_MAPPINGS = (
    ("case_05_rest_L0", "run/cases/case-05-calibrated_ordinary_human/mesh-L0.json", "case-05-calibrated_ordinary_human-rest-L0.json", "rest_mesh"),
    ("case_05_rest_L2", "run/cases/case-05-calibrated_ordinary_human/mesh-L2.json", "case-05-calibrated_ordinary_human-rest-L2.json", "rest_mesh"),
    ("case_06_rest_L0", "run/cases/case-06-calibrated_upright_anthropomorphic/mesh-L0.json", "case-06-calibrated_upright_anthropomorphic-rest-L0.json", "rest_mesh"),
    ("case_06_rest_L2", "run/cases/case-06-calibrated_upright_anthropomorphic/mesh-L2.json", "case-06-calibrated_upright_anthropomorphic-rest-L2.json", "rest_mesh"),
    ("calibration_protocol", "source/experiments/pelvis-source-calibration/protocol.json", "pelvis-source-calibration-protocol.json", "calibration_protocol"),
    ("calibration_inputs", "source/experiments/pelvis-source-calibration/inputs.json", "pelvis-source-calibration-inputs.json", "calibration_inputs"),
)


class CaptureError(ValueError):
    """Raised when a capture or verification contract is not satisfied."""


def _fail(message: str) -> NoReturn:
    raise CaptureError(message)


def _regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        _fail(f"{label} is unavailable: {path}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail(f"{label} must be a regular non-symlink file: {path}")


def _canonical(path: str | os.PathLike[str], label: str) -> Path:
    value = Path(path)
    if not value.is_absolute() or os.path.normpath(str(value)) != str(value):
        _fail(f"{label} must be an absolute canonical path")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _strict_json(path: Path) -> tuple[Any, bytes]:
    _regular(path, "JSON file")
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _fail(f"invalid finite UTF-8 JSON: {path}")
    return value, raw


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8"))


def _file_identity(path: Path) -> dict[str, Any]:
    _regular(path, "capture file")
    return {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}


def _inventory(paths: Iterable[Path]) -> list[dict[str, Any]]:
    return [{"origin_path": str(path), **_file_identity(path)} for path in sorted(paths, key=lambda item: str(item).encode("utf-8"))]


def _load_frozen_dependency_identity() -> dict[str, Any]:
    """Reuse the frozen calibration runner's stdlib identity implementation."""
    sys.dont_write_bytecode = True
    _regular(FROZEN_CALIBRATION_RUNNER, "frozen calibration runner")
    source_manifest, _ = _strict_json(CALIBRATION_SOURCE_MANIFEST)
    source_rows = {
        str(row.get("path")): row
        for row in source_manifest.get("files", [])
        if isinstance(row, Mapping)
    }
    runner_row = source_rows.get("experiments/pelvis-source-calibration/runner.py")
    if runner_row is None or _file_identity(FROZEN_CALIBRATION_RUNNER) != {
        "bytes": runner_row.get("bytes") if runner_row else None,
        "sha256": runner_row.get("sha256") if runner_row else None,
    }:
        _fail("frozen calibration runner differs from the captured source manifest")
    name = "ck_frozen_pelvis_source_calibration_runner"
    spec = importlib.util.spec_from_file_location(name, FROZEN_CALIBRATION_RUNNER)
    if spec is None or spec.loader is None:
        _fail(f"unable to load frozen calibration runner: {FROZEN_CALIBRATION_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
        raise
    identity = module._dependency_identity(FROZEN_DEPENDENCY_ROOT)
    if not isinstance(identity, dict):
        _fail("frozen calibration runner returned a non-object dependency identity")
    if identity["manifest"]["construction"]["sha256"] != CONSTRUCTION_SHA256:
        _fail("frozen construction identity differs from the required SHA-256")
    return identity


def _capture_names(file_names: Iterable[str] | None) -> list[str]:
    names = list(STANDARD_FILE_NAMES if file_names is None else file_names)
    if not names:
        _fail("at least one experiment file must be captured")
    if len(set(names)) != len(names):
        _fail("file_names contains duplicates")
    selected: list[str] = []
    for name in names:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            _fail(f"experiment filename must be relative and confined to the experiment: {name}")
        path = HERE / relative
        if file_names is None and not os.path.lexists(path):
            continue
        _regular(path, "experiment source")
        selected.append(relative.as_posix())
    if not selected:
        _fail("no requested experiment files exist")
    return selected


def _calibration_inputs() -> list[tuple[str, Path, Path, str]]:
    manifest, _ = _strict_json(CALIBRATION_SOURCE_MANIFEST)
    report, _ = _strict_json(CALIBRATION_PREPARE_REPORT)
    artifact, _ = _strict_json(CALIBRATION_ARTIFACT_MANIFEST)
    if _sha256_file(CALIBRATION_ARTIFACT_MANIFEST) != CALIBRATION_ARTIFACT_MANIFEST_SHA256:
        _fail("calibration artifact manifest differs from its frozen protocol hash")
    if not isinstance(artifact, Mapping) or artifact.get("schema") != "creature-kernel.pelvis-source-calibration-artifacts.v1":
        _fail("calibration artifact manifest is not admitted")
    if not isinstance(manifest, Mapping) or manifest.get("schema") != "creature-kernel.pelvis-source-calibration-captured-source.v1":
        _fail("captured calibration source manifest is not admitted")
    if not isinstance(report, Mapping) or report.get("status") != "prepared":
        _fail("captured calibration prepare report is not admitted")
    artifact_rows = {str(row.get("path")): row for row in artifact.get("files", []) if isinstance(row, Mapping)}
    rows = {str(row.get("path")): row for row in manifest.get("files", []) if isinstance(row, Mapping)}
    result = []
    for name, relative, target_name, kind in INPUT_MAPPINGS:
        source = FROZEN_CALIBRATION_ROOT / relative
        _regular(source, "preserved calibration input")
        expected = rows.get(relative.removeprefix("source/"))
        actual = _file_identity(source)
        if kind == "rest_mesh":
            artifact_path = relative.removeprefix("run/")
            artifact_expected = artifact_rows.get(artifact_path)
            if artifact_expected is None:
                _fail(f"calibration artifact manifest lacks: {artifact_path}")
            if actual != {"bytes": artifact_expected.get("bytes"), "sha256": artifact_expected.get("sha256")}:
                _fail(f"preserved rest mesh differs from the calibration artifact manifest: {source}")
        else:
            if expected is None:
                _fail(f"captured calibration source manifest lacks: {relative}")
            if actual != {"bytes": expected.get("bytes"), "sha256": expected.get("sha256")}:
                _fail(f"preserved calibration input differs from its source manifest: {source}")
        result.append((name, source, Path("inputs") / target_name, kind))
    return result


def _copy_group(output: Path, entries: Iterable[tuple[str, Path, Path, str]]) -> dict[str, Any]:
    entries = list(entries)
    before = [{"name": name, "origin_path": str(source), **_file_identity(source)} for name, source, _target, _kind in entries]
    copies = []
    for name, source, relative_target, kind in entries:
        target = output / relative_target
        if target.exists() or target.is_symlink():
            _fail(f"capture target must be absent: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied = _file_identity(target)
        source_identity = _file_identity(source)
        if copied != source_identity:
            _fail(f"copied bytes differ from source-before identity: {source}")
        copies.append({"name": name, "kind": kind, "origin_path": str(source), "snapshot_path": relative_target.as_posix(), **copied})
    after = [{"name": name, "origin_path": str(source), **_file_identity(source)} for name, source, _target, _kind in entries]
    if before != after:
        _fail("source changed while being captured")
    return {"before": before, "copies": copies, "after": after}


def prepare(output: str | os.PathLike[str], file_names: Iterable[str] | None = None) -> dict[str, Any]:
    """Capture listed experiment files and frozen rest inputs into an absent path."""
    sys.dont_write_bytecode = True
    output_path = _canonical(output, "prepare output")
    if output_path.exists() or output_path.is_symlink():
        _fail(f"prepare output must be absent: {output_path}")
    if not output_path.parent.is_dir() or output_path.parent.is_symlink():
        _fail("prepare output parent must be an existing regular directory")
    names = _capture_names(file_names)
    dependency_before = _load_frozen_dependency_identity()
    source_entries = [(name, HERE / name, Path("source/experiments/pelvis-hip-articulation") / name, "experiment_source") for name in names]
    input_entries = _calibration_inputs()
    output_path.mkdir()
    source_record = _copy_group(output_path, source_entries)
    input_record = _copy_group(output_path, input_entries)
    dependency_after = _load_frozen_dependency_identity()
    if dependency_before != dependency_after:
        _fail("frozen dependency changed while preparing the capture")
    runtime_path = dependency_before["runtime"]["executable"]
    manifest = {
        "schema": "creature-kernel.pelvis-hip-articulation-capture.v1",
        "status": "prepared",
        "geometry_executed": False,
        "body_articulation_executed": False,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime_path": runtime_path,
        "runtime_environment": {"variable": "CK_CURRENT_FORM_SURFACE_PYTHON", "value": runtime_path},
        "frozen_dependency": {"root": str(FROZEN_DEPENDENCY_ROOT), "construction_sha256": CONSTRUCTION_SHA256, "reused_without_copy": True, "before": dependency_before, "after": dependency_after},
        "calibration_provenance": {"prepare_report": {"origin_path": str(CALIBRATION_PREPARE_REPORT), **_file_identity(CALIBRATION_PREPARE_REPORT)}, "source_manifest": {"origin_path": str(CALIBRATION_SOURCE_MANIFEST), **_file_identity(CALIBRATION_SOURCE_MANIFEST)}, "artifact_manifest": {"origin_path": str(CALIBRATION_ARTIFACT_MANIFEST), "sha256": CALIBRATION_ARTIFACT_MANIFEST_SHA256, "bytes": CALIBRATION_ARTIFACT_MANIFEST.stat().st_size}},
        "captured_source": {"file_names": names, **source_record},
        "inputs": {"filename_mappings": [{"name": name, "kind": kind, "origin_path": str(source), "snapshot_path": target.as_posix()} for name, source, target, kind in input_entries], **input_record},
        "limitations": ["This capture is stdlib-only and does not execute geometry or body articulation.", "The shared calibration dependency/runtime is referenced and identity-verified, not copied; the shared stdlib/OS environment is not fully hermetic.", "The captured launcher is not executable; reproduce it with bash and set CK_CURRENT_FORM_SURFACE_PYTHON to the exact recorded frozen runtime path."],
    }
    _write_json(output_path / "manifest.json", manifest)
    return manifest


def verify(snapshot: str | os.PathLike[str]) -> dict[str, Any]:
    """Verify a prepared capture and the unchanged frozen dependency identity."""
    snapshot_path = _canonical(snapshot, "snapshot")
    if not snapshot_path.is_dir() or snapshot_path.is_symlink():
        _fail(f"snapshot must be a regular directory: {snapshot_path}")
    manifest, _ = _strict_json(snapshot_path / "manifest.json")
    if not isinstance(manifest, Mapping) or manifest.get("schema") != "creature-kernel.pelvis-hip-articulation-capture.v1":
        _fail("capture manifest schema is not admitted")
    if manifest.get("geometry_executed") or manifest.get("body_articulation_executed"):
        _fail("capture manifest claims an execution")
    expected_paths = set()
    for group_name in ("captured_source", "inputs"):
        group = manifest.get(group_name)
        if not isinstance(group, Mapping) or group.get("before") != group.get("after"):
            _fail(f"{group_name} source inventory drifted")
        for row in group.get("copies", []):
            if not isinstance(row, Mapping):
                _fail(f"{group_name} copy row is malformed")
            target = snapshot_path / str(row["snapshot_path"])
            try:
                relative_target = target.relative_to(snapshot_path)
            except ValueError:
                _fail(f"captured path escapes snapshot: {target}")
            expected_paths.add(relative_target.as_posix())
            if _file_identity(target) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
                _fail(f"captured file drifted: {target}")
    actual_paths = {path.relative_to(snapshot_path).as_posix() for path in snapshot_path.rglob("*") if path.is_file() and path.name != "manifest.json"}
    if actual_paths != expected_paths:
        _fail("snapshot contains missing or unexpected captured files")
    dependency = _load_frozen_dependency_identity()
    recorded = manifest.get("frozen_dependency", {})
    if dependency != recorded.get("before") or dependency != recorded.get("after"):
        _fail("frozen dependency identity drifted")
    if manifest.get("runtime_path") != dependency["runtime"]["executable"] or manifest.get("frozen_dependency", {}).get("construction_sha256") != CONSTRUCTION_SHA256:
        _fail("runtime or construction identity is not the required frozen identity")
    return dict(manifest)


def artifact_manifest(output: str | os.PathLike[str]) -> dict[str, Any]:
    """Return a small relative-path and SHA-256 inventory for a capture."""
    root = _canonical(output, "artifact output")
    if not root.is_dir() or root.is_symlink():
        _fail(f"artifact output must be a regular directory: {root}")
    files = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().encode("utf-8")):
        if path.is_symlink():
            _fail(f"artifact tree contains a symlink: {path}")
        if path.is_file():
            files.append({"path": path.relative_to(root).as_posix(), **_file_identity(path)})
    return {"schema": "creature-kernel.pelvis-hip-articulation-artifacts.v1", "files": files}

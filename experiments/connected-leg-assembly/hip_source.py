"""Source-driven bridge to the immutable frozen harmonic hip binder.

This adapter owns input mapping and provenance only.  It deliberately accepts
no prior binding and never reads cached weights from the connected-leg inputs.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any


FROZEN_HIP_SNAPSHOT = Path(
    "/home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot"
)
FROZEN_HIP_MANIFEST = FROZEN_HIP_SNAPSHOT / "manifest.json"
FROZEN_HIP_BINDING_RELATIVE = Path(
    "source/experiments/pelvis-hip-articulation/binding.py"
)
FROZEN_HIP_BINDING = FROZEN_HIP_SNAPSHOT / FROZEN_HIP_BINDING_RELATIVE
FROZEN_HIP_MODULE = "ck_connected_leg_frozen_hip_binding"


class HipSourceError(ValueError):
    """Raised when source inputs or frozen hip provenance are incoherent."""


def _fail(message: str) -> None:
    raise HipSourceError(message)


def _regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise HipSourceError(f"{label} is unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not info:
        _fail(f"{label} must be a regular non-symlink file: {path}")


def _identity(path: Path) -> dict[str, Any]:
    _regular(path, "frozen hip file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _manifest() -> dict[str, Any]:
    _regular(FROZEN_HIP_MANIFEST, "frozen hip manifest")
    try:
        value = json.loads(FROZEN_HIP_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HipSourceError(f"invalid frozen hip manifest: {FROZEN_HIP_MANIFEST}") from exc
    if not isinstance(value, Mapping) or value.get("schema") != "creature-kernel.pelvis-hip-articulation-capture.v1":
        _fail("frozen hip manifest schema is not admitted")
    return dict(value)


def _binding_manifest_row(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    captured = manifest.get("captured_source")
    if not isinstance(captured, Mapping) or captured.get("before") != captured.get("after"):
        _fail("frozen hip source manifest has drifted before/after inventories")
    copies = captured.get("copies")
    if not isinstance(copies, list):
        _fail("frozen hip source manifest has no captured source copies")
    row = next((item for item in copies
                if isinstance(item, Mapping)
                and item.get("snapshot_path") == FROZEN_HIP_BINDING_RELATIVE.as_posix()), None)
    if not isinstance(row, Mapping):
        _fail("frozen hip manifest lacks the captured binding module")
    return row


def _load_frozen_binding() -> tuple[Any, dict[str, Any]]:
    manifest = _manifest()
    row = _binding_manifest_row(manifest)
    before = _identity(FROZEN_HIP_BINDING)
    expected = {"bytes": row.get("bytes"), "sha256": row.get("sha256")}
    if before != expected:
        _fail("frozen hip binding identity differs from its manifest")
    spec = importlib.util.spec_from_file_location(FROZEN_HIP_MODULE, FROZEN_HIP_BINDING)
    if spec is None or spec.loader is None:
        _fail(f"unable to load frozen hip binding: {FROZEN_HIP_BINDING}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[FROZEN_HIP_MODULE] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(FROZEN_HIP_MODULE) is module:
            sys.modules.pop(FROZEN_HIP_MODULE, None)
        raise
    if Path(str(module.__file__)).resolve() != FROZEN_HIP_BINDING.resolve():
        _fail("frozen hip binding resolved away from its snapshot path")
    after = _identity(FROZEN_HIP_BINDING)
    if before != after or after != expected:
        _fail("frozen hip binding changed while being loaded")
    return module, {
        "frozen_helper_identity": {
            "manifest_path": str(FROZEN_HIP_MANIFEST),
            "path": str(FROZEN_HIP_BINDING),
            "before": before,
            "after": after,
        },
        "binding_api": "bind(base_mesh, rest_mesh, case, reference_landmarks)",
    }


def _vector(value: Any, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        _fail(f"{label} must be a three-component vector")
    result = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            _fail(f"{label}[{index}] must be numeric")
        result.append(float(item))
    return result


def _sides(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"left", "right"}:
        _fail(f"{label} must contain exactly left and right")
    return value


def _joints(explicit_j: Any, leg_inputs: Any) -> dict[str, list[float]]:
    explicit: dict[str, list[float]] | None = None
    if explicit_j is not None:
        rows = _sides(explicit_j, "explicit_j")
        explicit = {side: _vector(rows[side], f"explicit_j.{side}")
                    for side in ("left", "right")}
    from_legs: dict[str, list[float]] | None = None
    if leg_inputs is not None:
        rows = _sides(leg_inputs, "leg_inputs")
        from_legs = {}
        for side in ("left", "right"):
            row = rows[side]
            if not isinstance(row, Mapping) or "J" not in row:
                _fail(f"leg_inputs.{side}.J is required")
            from_legs[side] = _vector(row["J"], f"leg_inputs.{side}.J")
    if explicit is not None and from_legs is not None and explicit != from_legs:
        _fail("explicit_j conflicts with leg_inputs.J")
    if explicit is not None:
        return explicit
    if from_legs is not None:
        return from_legs
    _fail("explicit_j or leg_inputs is required")


def _source_case_inputs(source_case: Any, leg_inputs: Any) -> tuple[dict[str, Any], dict[str, list[float]]]:
    if not isinstance(source_case, Mapping):
        _fail("source_case must be a mapping")
    components = source_case.get("components")
    attachments = _sides(source_case.get("attachments"), "source_case.attachments")
    if not isinstance(components, Mapping):
        _fail("source_case.components must be a mapping")
    case = copy.deepcopy(dict(source_case))
    expected_tk: dict[str, list[float]] = {}
    for side in ("left", "right"):
        attachment = attachments[side]
        if not isinstance(attachment, Mapping) or "centre" not in attachment or "knee" not in attachment:
            _fail(f"source_case.attachments.{side} must contain centre and knee")
        expected_tk[side] = _vector(attachment["centre"], f"source_case.attachments.{side}.centre")
        expected_tk[side + ".K"] = _vector(attachment["knee"], f"source_case.attachments.{side}.knee")
    if leg_inputs is not None:
        rows = _sides(leg_inputs, "leg_inputs")
        for side in ("left", "right"):
            row = rows[side]
            if not isinstance(row, Mapping):
                _fail(f"leg_inputs.{side} must be a mapping")
            for field, source_key in (("T", "centre"), ("K", "knee")):
                if field in row:
                    actual = _vector(row[field], f"leg_inputs.{side}.{field}")
                    expected = expected_tk[side if field == "T" else side + ".K"]
                    if actual != expected:
                        _fail(f"leg_inputs.{side}.{field} conflicts with source_case.attachments.{side}.{source_key}")
    return case, expected_tk


def bind_source_case(root_l0: Mapping[str, Any], root_l2: Mapping[str, Any],
                     source_case: Mapping[str, Any], explicit_j: Any = None,
                     leg_inputs: Any = None) -> dict[str, Any]:
    """Regenerate hip weights from rebuilt source surfaces and source ownership."""
    if not isinstance(root_l0, Mapping) or not isinstance(root_l2, Mapping):
        _fail("root_l0 and root_l2 must be mesh mappings")
    case, _ = _source_case_inputs(source_case, leg_inputs)
    joints = _joints(explicit_j, leg_inputs)
    references = {"joint_left": joints["left"], "joint_right": joints["right"]}
    binder, provenance = _load_frozen_binding()
    function = getattr(binder, "bind", None)
    if not callable(function):
        _fail("frozen hip binding lacks bind")
    binding = function(root_l0, root_l2, case, references)
    if not isinstance(binding, Mapping):
        _fail("frozen hip binding returned a non-mapping result")
    return {"binding": dict(binding), "provenance": provenance}


__all__ = ["HipSourceError", "bind_source_case"]

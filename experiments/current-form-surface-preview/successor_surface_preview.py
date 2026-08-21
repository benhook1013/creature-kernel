#!/usr/bin/env python3
"""Private successor-surface experiment for the disposable form preview.

This module is intentionally adjacent to, rather than a modification of,
``surface_preview.py``.  It consumes the existing private hybrid guide and
replaces only the torso/shoulder skin consumer with an explicitly identified
profile loft and swept shoulder spans.  Head, limbs, paws, and tail fields are
kept as an explicit temporary bridge so the experiment can still produce a
whole-body mesh without pretending that those regions have been redesigned.

The representation is exploratory and disposable.  It is not a production
surface backend, topology contract, SDF, collision shape, or runtime API.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib
import json
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from skimage.measure import marching_cubes


try:
    _baseline = importlib.import_module("surface_preview")
except ModuleNotFoundError:  # pragma: no cover - direct source-tree execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    _baseline = importlib.import_module("surface_preview")


FORMAT = "creature-kernel.disposable-successor-surface-preview.v1"
CONSUMER_ID = "successor-surface-v1"
SUCCESSOR_REGION_ID = "successor-torso-shoulder-loft-and-sweeps-v1"
DEFAULT_SAMPLES = 48
DEFAULT_PADDING = 0.50
DEFAULT_SMOOTH_K = 0.10
MAX_SAMPLES = 96
MAX_VOXELS = 96**3
MAX_FIELD_VALUES = 16_000_000


class SuccessorPreviewError(RuntimeError):
    """A fail-closed successor experiment error."""


def _fail(message: str) -> None:
    raise SuccessorPreviewError(message)


@dataclass(frozen=True)
class _LoftProfile:
    """The seven ordered cross-sections consumed by the successor loft."""

    names: tuple[str, ...]
    owners: tuple[Any, ...]
    centers: np.ndarray
    lateral_radii: np.ndarray
    depth_radii: np.ndarray


@dataclass(frozen=True)
class _SweptSpan:
    """One source-owned, tapered span of a shoulder support curve."""

    side: str
    curve_name: str
    span_index: int
    owner: Any
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    start_radius: float
    end_radius: float

    @property
    def recipe(self) -> str:
        return f"successor-shoulder-{self.side}-{self.curve_name}-{self.span_index}"


@dataclass(frozen=True)
class SuccessorRegion:
    """Explicit successor torso/shoulder representation.

    ``bridge_fields`` are untouched baseline fields for all regions outside
    this successor region.  They are kept here, rather than silently folded
    into the successor, so later head/limb consumers have a stable extension
    point and the temporary boundary remains inspectable.
    """

    consumer_id: str
    region_id: str
    loft: _LoftProfile
    shoulder_spans: tuple[_SweptSpan, ...]
    bridge_fields: tuple[Any, ...]
    replaced_baseline_recipes: tuple[str, ...]
    source_owners: tuple[Any, ...]

    @property
    def section_names(self) -> tuple[str, ...]:
        return self.loft.names

    @property
    def sections_consumed(self) -> int:
        return len(self.loft.names)

    @property
    def shoulder_inputs_consumed(self) -> int:
        return len(self.shoulder_spans)


@dataclass(frozen=True)
class SuccessorMesh:
    """Deterministic in-memory full-body result for one variant."""

    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray
    labels: tuple[tuple[str, tuple[str, ...], str, str], ...]
    metrics: dict[str, Any]
    representation: SuccessorRegion
    grid: dict[str, Any]


@dataclass(frozen=True)
class _Component:
    owner: Any
    recipe: str
    evaluate: Callable[[np.ndarray], np.ndarray]
    bounds: tuple[np.ndarray, np.ndarray]
    successor: bool


def _finite_positive(values: tuple[float, ...], where: str) -> None:
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        _fail(f"{where} must contain finite positive values")


def _make_loft(guide: Any) -> _LoftProfile:
    sections = tuple(guide.torso_cage.sections)
    names = tuple(section.name for section in sections)
    if len(sections) != 7:
        _fail(f"successor torso loft requires exactly seven sections, got {len(sections)}")
    centers = np.asarray([section.center for section in sections], dtype=np.float64)
    lateral = np.asarray([section.lateral_radius for section in sections], dtype=np.float64)
    depth = np.asarray([section.depth_radius for section in sections], dtype=np.float64)
    if centers.shape != (7, 3) or not np.all(np.isfinite(centers)):
        _fail("successor torso loft centres are invalid")
    if not np.all(np.isfinite(lateral)) or not np.all(np.isfinite(depth)):
        _fail("successor torso loft radii are invalid")
    if np.any(lateral <= 0.0) or np.any(depth <= 0.0) or np.any(np.diff(centers[:, 1]) <= 0.0):
        _fail("successor torso loft requires positive radii and increasing heights")
    # Make copies: the successor owns its representation and cannot mutate
    # the guide's arrays or baseline shape dictionaries through an alias.
    return _LoftProfile(names, tuple(section.owner for section in sections), centers.copy(), lateral.copy(), depth.copy())


def _make_spans(guide: Any) -> tuple[_SweptSpan, ...]:
    spans: list[_SweptSpan] = []
    frame = guide.shoulder_frame
    for side in frame.sides:
        for curve_name, curve in (
            ("anterior-support", side.anterior_support),
            ("posterior-return", side.posterior_return),
            ("deltoid-sweep", side.deltoid_sweep),
        ):
            if len(curve.points) != len(curve.profile) or len(curve.points) < 2:
                _fail(f"successor shoulder input {side.side}/{curve_name} is malformed")
            for index in range(len(curve.points) - 1):
                start = tuple(float(value) for value in curve.points[index])
                end = tuple(float(value) for value in curve.points[index + 1])
                start_radius = float(curve.profile[index])
                end_radius = float(curve.profile[index + 1])
                if not all(math.isfinite(value) for value in (*start, *end)):
                    _fail(f"{side.side}/{curve_name} contains non-finite points")
                _finite_positive((start_radius, end_radius), f"{side.side}/{curve_name}.profile")
                if start == end:
                    _fail(f"successor shoulder input {side.side}/{curve_name} contains a degenerate span")
                spans.append(_SweptSpan(side.side, curve_name, index, curve.owner, start, end, start_radius, end_radius))
    if len(spans) != 16:  # 2 sides: 3 + 3 + 2 spans
        _fail(f"successor shoulder input count is unstable: {len(spans)}")
    return tuple(spans)


def compile_successor_region(guide: Any, baseline_fields: tuple[Any, ...] | None = None) -> SuccessorRegion:
    """Compile the guide into a successor torso/shoulder consumer.

    The baseline torso cage and old deltoid field are replaced.  Every other
    baseline field is carried as a named temporary bridge, including limb root
    connectors that preserve whole-body continuity for this bounded slice.
    """

    _baseline._validate_hybrid_guide(guide)
    if baseline_fields is None:
        baseline_fields = _baseline._compile_hybrid_guide(guide)
    replaced = ("torso-cage", "deltoid-sweep-1")
    torso_fields = tuple(field for field in baseline_fields if field.recipe == "torso-cage")
    expected_torso_owner = guide.torso_cage.torso_owner
    if len(torso_fields) != 1 or torso_fields[0].owner is not expected_torso_owner:
        _fail("baseline inventory must contain exactly one torso-cage field owned by the guide torso")
    deltoid_fields = tuple(field for field in baseline_fields if field.recipe == "deltoid-sweep-1")
    expected_deltoid_owners = tuple(side.owner for side in guide.shoulder_frame.sides)
    if len(deltoid_fields) != 2 or {id(field.owner) for field in deltoid_fields} != {id(owner) for owner in expected_deltoid_owners}:
        _fail("baseline inventory must contain exactly two left/right deltoid-sweep-1 fields")
    replaced_fields = tuple(field for field in baseline_fields if field.recipe in replaced)
    bridge = tuple(field for field in baseline_fields if field.recipe not in replaced)
    if len(bridge) + len(replaced_fields) != len(baseline_fields):
        _fail("baseline bridge selection lost fields")
    return SuccessorRegion(
        consumer_id=CONSUMER_ID,
        region_id=SUCCESSOR_REGION_ID,
        loft=_make_loft(guide),
        shoulder_spans=_make_spans(guide),
        bridge_fields=bridge,
        replaced_baseline_recipes=replaced,
        source_owners=(guide.torso_cage.torso_owner,) + tuple(side.owner for side in guide.shoulder_frame.sides),
    )


def _loft_field(points: np.ndarray, loft: _LoftProfile) -> np.ndarray:
    """Evaluate a piecewise linear elliptical loft with finite rounded caps."""

    points = np.asarray(points, dtype=np.float64)
    y = points[..., 1]
    centres = loft.centers
    heights = centres[:, 1]
    lower, upper = float(heights[0]), float(heights[-1])
    clipped = np.clip(y, lower, upper)
    interval = np.searchsorted(heights, clipped, side="right") - 1
    interval = np.clip(interval, 0, len(heights) - 2)
    y0 = heights[interval]
    y1 = heights[interval + 1]
    t = np.divide(clipped - y0, y1 - y0, out=np.zeros_like(clipped), where=(y1 - y0) != 0.0)
    centre = centres[interval] + t[..., None] * (centres[interval + 1] - centres[interval])
    lateral = loft.lateral_radii[interval] + t * (loft.lateral_radii[interval + 1] - loft.lateral_radii[interval])
    depth = loft.depth_radii[interval] + t * (loft.depth_radii[interval + 1] - loft.depth_radii[interval])
    transverse = points - centre
    radial = (np.sqrt((transverse[..., 0] / lateral) ** 2 + (transverse[..., 2] / depth) ** 2) - 1.0) * np.minimum(lateral, depth)

    # A finite ellipsoidal end cap shares the endpoint cross-section exactly.
    cap_index = np.where(y < lower, 0, len(heights) - 1)
    cap_center = centres[cap_index]
    cap_lateral = loft.lateral_radii[cap_index]
    cap_depth = loft.depth_radii[cap_index]
    cap_height = np.minimum(cap_lateral, cap_depth)
    cap_offset = points - cap_center
    cap_norm = np.sqrt(
        (cap_offset[..., 0] / cap_lateral) ** 2
        + (cap_offset[..., 1] / cap_height) ** 2
        + (cap_offset[..., 2] / cap_depth) ** 2
    )
    cap = (cap_norm - 1.0) * np.minimum(np.minimum(cap_lateral, cap_depth), cap_height)
    return np.where((y >= lower) & (y <= upper), radial, cap)


def _loft_section_indices(points: np.ndarray, loft: _LoftProfile) -> np.ndarray:
    """Choose the nearest source-owned section for deterministic attribution."""

    y = np.asarray(points, dtype=np.float64)[..., 1]
    heights = loft.centers[:, 1]
    index = np.searchsorted(heights, y, side="left")
    index = np.clip(index, 0, len(heights) - 1)
    previous = np.clip(index - 1, 0, len(heights) - 1)
    choose_previous = np.abs(y - heights[previous]) <= np.abs(y - heights[index])
    return np.where(choose_previous, previous, index)


def _loft_owner_keys(points: np.ndarray, loft: _LoftProfile) -> tuple[tuple[str, tuple[str, ...], str, str], ...]:
    """Return source AddressKeys without inventing a loft semantic node."""

    return tuple(loft.owners[int(index)].key for index in _loft_section_indices(points, loft).reshape(-1))


def _span_field(points: np.ndarray, span: _SweptSpan) -> np.ndarray:
    start = np.asarray(span.start, dtype=np.float64)
    end = np.asarray(span.end, dtype=np.float64)
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    t = np.clip(np.sum((points - start) * axis, axis=-1) / length_sq, 0.0, 1.0)
    closest = start + t[..., None] * axis
    radius = span.start_radius + (span.end_radius - span.start_radius) * t
    return np.linalg.norm(points - closest, axis=-1) - radius


def _successor_region_field(points: np.ndarray, region: SuccessorRegion, smooth_k: float) -> np.ndarray:
    values = [_loft_field(points, region.loft)]
    values.extend(_span_field(points, span) for span in region.shoulder_spans)
    return _baseline._smooth_union(values, smooth_k)


def _bounds_for_region(region: SuccessorRegion) -> tuple[np.ndarray, np.ndarray]:
    mins = [np.min(region.loft.centers - np.column_stack((region.loft.lateral_radii, np.minimum(region.loft.lateral_radii, region.loft.depth_radii), region.loft.depth_radii)), axis=0)]
    maxs = [np.max(region.loft.centers + np.column_stack((region.loft.lateral_radii, np.minimum(region.loft.lateral_radii, region.loft.depth_radii), region.loft.depth_radii)), axis=0)]
    for span in region.shoulder_spans:
        start, end = np.asarray(span.start), np.asarray(span.end)
        radius = max(span.start_radius, span.end_radius)
        mins.append(np.minimum(start, end) - radius)
        maxs.append(np.maximum(start, end) + radius)
    return np.min(np.stack(mins), axis=0), np.max(np.stack(maxs), axis=0)


def _make_components(region: SuccessorRegion, smooth_k: float) -> tuple[_Component, ...]:
    region_bounds = _bounds_for_region(region)
    components: list[_Component] = [
        _Component(region.source_owners[0], "successor-torso-loft", lambda points: _loft_field(points, region.loft), region_bounds, True),
    ]
    for span in region.shoulder_spans:
        bounds = (np.minimum(np.asarray(span.start), np.asarray(span.end)) - max(span.start_radius, span.end_radius), np.maximum(np.asarray(span.start), np.asarray(span.end)) + max(span.start_radius, span.end_radius))
        components.append(_Component(span.owner, span.recipe, lambda points, current=span: _span_field(points, current), bounds, True))
    for field in region.bridge_fields:
        shape = field.shape
        if shape["name"] == "ellipsoid":
            radii = shape["radii"]
            centre = shape["center"]
            bounds = (centre - radii, centre + radii)
        elif shape["name"] == "torso-cage":
            _fail("successor bridge unexpectedly contains baseline torso cage")
        else:
            start, end = shape["from"], shape["to"]
            radius = max(float(shape["r0"]), float(shape["r1"]))
            bounds = (np.minimum(start, end) - radius, np.maximum(start, end) + radius)
        components.append(_Component(field.owner, field.recipe, lambda points, current=field: _baseline._field(points, current), bounds, False))
    if len(components) < 2:
        _fail("successor full-body consumer has no temporary bridge")
    return tuple(components)


def _evaluate_components(points: np.ndarray, components: tuple[_Component, ...], smooth_k: float) -> np.ndarray:
    values = [component.evaluate(points) for component in components]
    return _baseline._smooth_union(values, smooth_k)


def _combined_bounds(components: tuple[_Component, ...], padding: float) -> tuple[np.ndarray, np.ndarray]:
    lower = np.min(np.stack([item.bounds[0] for item in components]), axis=0) - padding
    upper = np.max(np.stack([item.bounds[1] for item in components]), axis=0) + padding
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)) or np.any(upper <= lower):
        _fail("successor sampling bounds are invalid")
    return lower, upper


def _orient_mesh(vertices: np.ndarray, faces: np.ndarray, axes: tuple[np.ndarray, np.ndarray, np.ndarray], components: tuple[_Component, ...], smooth_k: float) -> tuple[np.ndarray, np.ndarray, float]:
    e1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    e2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    areas = np.cross(e1, e2)
    centres = (vertices[faces[:, 0]] + vertices[faces[:, 1]] + vertices[faces[:, 2]]) / 3.0
    delta = 0.5 * min(float(axis[1] - axis[0]) for axis in axes)
    gradients = []
    for axis in range(3):
        step = np.eye(3)[axis] * delta
        gradients.append((_evaluate_components(centres + step, components, smooth_k) - _evaluate_components(centres - step, components, smooth_k)) / (2.0 * delta))
    gradient = np.column_stack(gradients)
    if float(np.mean(np.sum(areas * gradient, axis=1))) < 0.0:
        faces = faces[:, [0, 2, 1]]
        areas = -areas
    volume = float(np.sum(np.einsum("ij,ij->i", vertices[faces[:, 0]], areas)) / 6.0)
    if not math.isfinite(volume) or volume <= 0.0:
        _fail("successor mesh has non-positive signed volume")
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], areas)
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= 1.0e-14) or not np.all(np.isfinite(lengths)):
        _fail("successor mesh contains undefined normals")
    return faces, normals / lengths[:, None], volume


def build_variant(form: Any, descriptors: tuple[Any, ...], samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> SuccessorMesh:
    """Build one deterministic full-body mesh through the successor consumer."""

    if type(samples) is not int or samples < 20 or samples > MAX_SAMPLES or samples**3 > MAX_VOXELS:
        _fail("successor sampling configuration exceeds bounded limits")
    if not math.isfinite(float(padding)) or padding < 0.0 or not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("successor padding and smooth-k must be finite and valid")
    guide = _baseline._derive_hybrid_guides(form, descriptors)
    baseline_fields = _baseline._compile_hybrid_guide(guide)
    baseline_signature = tuple((field.owner.key, field.recipe) for field in baseline_fields)
    region = compile_successor_region(guide, baseline_fields)
    components = _make_components(region, smooth_k)
    if len(components) * samples**3 > MAX_FIELD_VALUES:
        _fail("successor field sampling configuration exceeds bounded limits")
    lower, upper = _combined_bounds(components, padding)
    axes = tuple(np.linspace(lower[index], upper[index], samples, dtype=np.float64) for index in range(3))
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    field = _evaluate_components(points, components, smooth_k)
    if not np.all(np.isfinite(field)) or float(np.min(field)) >= 0.0 or float(np.max(field)) <= 0.0:
        _fail("successor field has no finite zero crossing")
    if np.any(field[(0, -1), :, :] <= 0) or np.any(field[:, (0, -1), :] <= 0) or np.any(field[:, :, (0, -1)] <= 0):
        _fail("successor field reaches the sampling domain boundary")
    try:
        raw_vertices, raw_faces, _, _ = marching_cubes(field, level=0.0, spacing=tuple(float(axis[1] - axis[0]) for axis in axes), gradient_direction="descent", allow_degenerate=False)
    except Exception as exc:
        raise SuccessorPreviewError(f"successor surface extraction failed: {exc}") from exc
    vertices = np.asarray(raw_vertices, dtype=np.float64) + lower
    faces = np.asarray(raw_faces, dtype=np.int64)
    faces, normals, volume = _orient_mesh(vertices, faces, axes, components, smooth_k)
    labels: list[tuple[str, tuple[str, ...], str, str]] = []
    for vertex in vertices:
        values = [float(component.evaluate(vertex.reshape(1, 3))[0]) for component in components]
        winner_index = int(np.argmin(values))
        if winner_index == 0:
            labels.append(_loft_owner_keys(vertex.reshape(1, 3), region.loft)[0])
        else:
            labels.append(components[winner_index].owner.key)
    metrics = _baseline._mesh_checks(vertices, faces, labels, (lower, upper), volume)
    metrics.update({
        "consumer_id": CONSUMER_ID,
        "successor_region_id": SUCCESSOR_REGION_ID,
        "successor_region": {
            "torso_representation": "ordered-linear-cross-section-loft",
            "torso_sections_consumed": region.sections_consumed,
            "torso_section_names": list(region.section_names),
            "torso_section_owner_keys": [_baseline._address_json(owner.key) for owner in region.loft.owners],
            "shoulder_support_inputs_consumed": region.shoulder_inputs_consumed,
            "shoulder_support_input_kind": "tapered-swept-curve-spans",
            "replaced_baseline_recipes": list(region.replaced_baseline_recipes),
        },
        "temporary_bridge": {
            "enabled": True,
            "consumer": "baseline-analytic-fields",
            "regions": ["head", "neck", "limbs", "paws", "tail", "limb-root-connectors"],
            "field_count": len(region.bridge_fields),
        },
        "baseline_recipe_signature": [[list(field_key[0]), list(field_key[1]), field_key[2], field_key[3], recipe] for field_key, recipe in baseline_signature],
        "source_descriptor_count": len(descriptors),
        "component_count_for_sampling": len(components),
        "grid": {"samples_per_axis": samples, "axis_order": ["x", "y", "z"], "bounds_min": lower.tolist(), "bounds_max": upper.tolist(), "spacing": [float(axis[1] - axis[0]) for axis in axes]},
    })
    return SuccessorMesh(vertices, faces, normals, tuple(labels), metrics, region, metrics["grid"])


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _write_ply(path: Path, mesh: SuccessorMesh) -> None:
    lines = ["ply", "format ascii 1.0", f"element vertex {len(mesh.vertices)}", "property float x", "property float y", "property float z", "property float nx", "property float ny", "property float nz", f"element face {len(mesh.faces)}", "property list uchar int vertex_indices", "end_header"]
    lines.extend("%.9f %.9f %.9f %.9f %.9f %.9f" % tuple([*vertex, *normal]) for vertex, normal in zip(mesh.vertices, mesh.normals))
    lines.extend("3 %d %d %d" % tuple(int(value) for value in face) for face in mesh.faces)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _sha(path: Path, kind: str, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"kind": kind, "path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _atomic_rename_noreplace(source: Path, target: Path) -> None:
    """Atomically rename a directory without replacing an existing target.

    This experiment is documented for Linux/WSL.  Refuse publication when the
    kernel primitive is unavailable rather than falling back to a
    check-then-rename race.
    """

    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is not None:
            renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            renameat2.restype = ctypes.c_int
            result = renameat2(
                -100,  # AT_FDCWD
                os.fsencode(str(source)),
                -100,
                os.fsencode(str(target)),
                1,  # RENAME_NOREPLACE
            )
            if result == 0:
                return
            error = ctypes.get_errno()
            if error == errno.EEXIST:
                raise FileExistsError(errno.EEXIST, "publication target appeared")
            if error not in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
                raise OSError(error, os.strerror(error))
    raise OSError(errno.ENOTSUP, "atomic no-replace directory rename unavailable")


def generate(input_path: Path, output: Path, *, samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> dict[str, Any]:
    if output.exists() or os.path.lexists(output):
        _fail(f"refusing to overwrite output: {output}")
    if not output.parent.is_dir():
        _fail(f"output parent must exist: {output.parent}")
    data = input_path.read_bytes()
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SuccessorPreviewError(f"input is not finite JSON: {exc}") from exc
    form = _baseline.validate_envelope(value)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        records: list[dict[str, Any]] = []
        for variant_id, descriptors, raw_variant in form.variants:
            mesh = build_variant(form, descriptors, samples=samples, padding=padding, smooth_k=smooth_k)
            variant_dir = stage / variant_id
            variant_dir.mkdir()
            ply = variant_dir / "surface.ply"
            metrics = variant_dir / "metrics.json"
            successor = variant_dir / "successor.json"
            _write_ply(ply, mesh)
            metrics.write_bytes(_canonical(mesh.metrics) + b"\n")
            successor.write_bytes(_canonical({
                "format": FORMAT,
                "variant_id": variant_id,
                "consumer_id": CONSUMER_ID,
                "successor_region_id": SUCCESSOR_REGION_ID,
                "torso": {"representation": "ordered-linear-cross-section-loft", "sections_consumed": mesh.representation.sections_consumed, "section_names": list(mesh.representation.section_names)},
                "shoulders": {"representation": "tapered-swept-curve-spans", "inputs_consumed": mesh.representation.shoulder_inputs_consumed, "curves": sorted({span.curve_name for span in mesh.representation.shoulder_spans})},
                "temporary_bridge": mesh.metrics["temporary_bridge"],
                "replaced_baseline_recipes": list(mesh.representation.replaced_baseline_recipes),
            }) + b"\n")
            records.append({
                "id": variant_id,
                "profile_id": raw_variant["profile_id"],
                "metrics": mesh.metrics,
                "inventory": [_sha(ply, "ply", stage), _sha(metrics, "metrics", stage), _sha(successor, "successor-consumer-sidecar", stage)],
            })
        manifest = {
            "format": FORMAT,
            "status": "success",
            "consumer_id": CONSUMER_ID,
            "source_format": _baseline.SOURCE_FORMAT,
            "source": {"sha256": hashlib.sha256(data).hexdigest(), "document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"]},
            "generator": {"samples_per_axis": samples, "padding": padding, "smooth_k": smooth_k, "consumer_boundary": "successor torso/shoulder; baseline temporary bridge elsewhere", "production_status": "disposable exploratory proof"},
            "variants": records,
        }
        manifest_path = stage / "successor-surface-manifest.json"
        manifest_path.write_bytes(_canonical(manifest) + b"\n")
        try:
            _atomic_rename_noreplace(stage, output)
        except FileExistsError as exc:
            raise SuccessorPreviewError(f"refusing to overwrite existing output: {output}") from exc
        except OSError as exc:
            raise SuccessorPreviewError(f"cannot publish successor output atomically: {exc}") from exc
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the disposable successor torso/shoulder surface preview")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples-per-axis", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--padding", type=float, default=DEFAULT_PADDING)
    parser.add_argument("--smooth-k", type=float, default=DEFAULT_SMOOTH_K)
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.input, args.output, samples=args.samples_per_axis, padding=args.padding, smooth_k=args.smooth_k)
    except (OSError, ValueError, SuccessorPreviewError, _baseline.PreviewError) as exc:
        print(json.dumps({"format": FORMAT, "status": "failure", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"format": FORMAT, "status": "success", "output": str(args.output), "variants": [item["id"] for item in manifest["variants"]]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a bounded, disposable continuous surface from a v4 form envelope.

This module intentionally has no dependency on Creature Kernel runtime code.
It is a small adapter for visual exploration: exact integer form coordinates
are normalized by the supplied reference edge, analytic fields are folded in
stable AddressKey order, and marching cubes produces a temporary mesh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.measure import marching_cubes


FORMAT = "creature-kernel.disposable-surface-preview.v1"
SOURCE_FORMAT = "creature-kernel.provisional-form-preview.v4"
VARIANT_IDS = ("neutral-v0", "broad-soft-v0", "lean-readable-v0", "depth-forward-v0")
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_SAMPLES = 128
MAX_VOXELS = 128**3
MAX_FIELD_VALUES = 32_000_000
MAX_DESCRIPTORS = 64
DEFAULT_SAMPLES = 72
DEFAULT_PADDING = 0.75
DEFAULT_SMOOTH_K = 0.12
CANVAS = (1200, 430)
VIEW_BOXES = {
    "front": (12, 62, 392, 418),
    "side": (410, 62, 790, 418),
    "three-quarter": (808, 62, 1188, 418),
}


class PreviewError(RuntimeError):
    """A fail-closed input, field, extraction, or output error."""


def _fail(message: str) -> None:
    raise PreviewError(message)


def _obj(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{where} must be an object")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{where} must be an array")
    return value


def _int(value: Any, where: str) -> int:
    if type(value) is not int or not -(1 << 63) <= value < (1 << 63):
        _fail(f"{where} must be a signed integer")
    return value


def _vector(value: Any, where: str) -> tuple[int, int, int]:
    values = _array(value, where)
    if len(values) != 3:
        _fail(f"{where} must contain three integers")
    return tuple(_int(item, f"{where}[{index}]") for index, item in enumerate(values))  # type: ignore[return-value]


def _address(value: Any, where: str) -> tuple[str, tuple[str, ...], str, str]:
    obj = _obj(value, where)
    if set(obj) != {"namespace", "anchors", "kind", "role"}:
        _fail(f"{where} has unexpected fields")
    namespace = obj.get("namespace")
    kind = obj.get("kind")
    role = obj.get("role")
    anchors = _array(obj.get("anchors"), f"{where}.anchors")
    if not all(type(item) is str and item for item in anchors):
        _fail(f"{where}.anchors must contain non-empty strings")
    if not all(type(item) is str and item for item in (namespace, kind, role)):
        _fail(f"{where} text fields must be strings")
    return (namespace, tuple(anchors), kind, role)


def _address_json(key: tuple[str, tuple[str, ...], str, str]) -> dict[str, Any]:
    return {"namespace": key[0], "anchors": list(key[1]), "kind": key[2], "role": key[3]}


def _shape(value: Any, where: str) -> dict[str, Any]:
    obj = _obj(value, where)
    name = obj.get("name")
    if name == "ellipsoid":
        if set(obj) != {"name", "center", "axis_extents_permille"}:
            _fail(f"{where} has unexpected ellipsoid fields")
        extents = _vector(obj.get("axis_extents_permille"), f"{where}.axis_extents_permille")
        if any(not 0 < x <= 5000 for x in extents):
            _fail(f"{where}.axis_extents_permille must be in 1..5000")
        return {"name": name, "center": list(_vector(obj.get("center"), f"{where}.center")), "axis_extents_permille": list(extents)}
    if name == "capsule":
        if set(obj) != {"name", "from", "to", "radius_permille"}:
            _fail(f"{where} has unexpected capsule fields")
        start, end = _vector(obj.get("from"), f"{where}.from"), _vector(obj.get("to"), f"{where}.to")
        radius = _int(obj.get("radius_permille"), f"{where}.radius_permille")
        if start == end or not 0 < radius <= 5000:
            _fail(f"{where} capsule is degenerate or has invalid radius")
        return {"name": name, "from": list(start), "to": list(end), "radius_permille": radius}
    if name == "tapered-segment":
        if set(obj) != {"name", "from", "to", "start_radius_permille", "end_radius_permille"}:
            _fail(f"{where} has unexpected tapered-segment fields")
        start, end = _vector(obj.get("from"), f"{where}.from"), _vector(obj.get("to"), f"{where}.to")
        r0 = _int(obj.get("start_radius_permille"), f"{where}.start_radius_permille")
        r1 = _int(obj.get("end_radius_permille"), f"{where}.end_radius_permille")
        if start == end or not 0 < r0 <= 5000 or not 0 < r1 <= 5000:
            _fail(f"{where} tapered segment is degenerate or has invalid radius")
        return {"name": name, "from": list(start), "to": list(end), "start_radius_permille": r0, "end_radius_permille": r1}
    _fail(f"{where}.name is unsupported")


@dataclass(frozen=True)
class Descriptor:
    key: tuple[str, tuple[str, ...], str, str]
    parent: tuple[str, tuple[str, ...], str, str] | None
    point: np.ndarray
    exact_point: tuple[int, int, int]
    shape: dict[str, Any]
    placement_source: str
    profile_id: str
    source: str
    provenance: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class Form:
    raw: dict[str, Any]
    source: dict[str, Any]
    reference_scale: float
    reference_scale_raw: dict[str, Any]
    variants: tuple[tuple[str, tuple[Descriptor, ...], dict[str, Any]], ...]


def validate_envelope(value: Any) -> Form:
    root = _obj(value, "envelope")
    required = {"format", "operation", "status", "stage", "processing_complete", "diagnostics_complete", "diagnostics", "source", "reference_scale", "variants", "limitations"}
    if set(root) != required:
        _fail("envelope has unexpected or missing fields")
    if root["format"] != SOURCE_FORMAT or root["operation"] != "inspect-provisional-form" or root["status"] != "success" or root["stage"] != "provisional-form":
        _fail("envelope is not a successful v4 provisional-form result")
    if root["processing_complete"] is not True or root["diagnostics_complete"] is not True or root["diagnostics"] != []:
        _fail("envelope success flags or diagnostics are invalid")
    if type(root["limitations"]) is not str or "Readiness" not in root["limitations"] or "geometry" not in root["limitations"]:
        _fail("envelope limitations do not state the exploratory boundary")
    source = _obj(root["source"], "source")
    if set(source) != {"document", "namespace", "resource_profile_id"} or any(type(source[x]) is not str for x in source):
        _fail("source is invalid")
    if source["resource_profile_id"] != "ck.resource.body.r2":
        _fail("unsupported resource profile")
    scale = _obj(root["reference_scale"], "reference_scale")
    if set(scale) != {"parent", "child", "axis_delta", "squared_length", "source"} or scale["source"] != "exact-containment-edge":
        _fail("reference_scale is invalid")
    parent_key = _address(scale["parent"], "reference_scale.parent")
    child_key = _address(scale["child"], "reference_scale.child")
    delta = _vector(scale["axis_delta"], "reference_scale.axis_delta")
    squared = _int(scale["squared_length"], "reference_scale.squared_length")
    if squared <= 0 or squared != sum(x * x for x in delta) or parent_key == child_key:
        _fail("reference_scale arithmetic is invalid")
    reference_scale = math.sqrt(float(squared))
    variants = _array(root["variants"], "variants")
    if len(variants) != 4:
        _fail("variants must contain exactly four items")
    normalized: list[tuple[str, tuple[Descriptor, ...], dict[str, Any]]] = []
    canonical: list[tuple[Any, ...]] | None = None
    for index, item in enumerate(variants):
        variant = _obj(item, f"variants[{index}]")
        if set(variant) != {"id", "profile_id", "provenance", "descriptors"} or variant.get("id") != VARIANT_IDS[index] or variant.get("profile_id") != VARIANT_IDS[index]:
            _fail(f"variants[{index}] is not the fixed {VARIANT_IDS[index]} variant")
        provenance = _obj(variant["provenance"], f"variants[{index}].provenance")
        if set(provenance) != {"source", "resource_profile_id"} or provenance.get("source") != "profile-derived-display" or provenance.get("resource_profile_id") != source["resource_profile_id"]:
            _fail(f"variants[{index}].provenance is invalid")
        descriptors = _array(variant["descriptors"], f"variants[{index}].descriptors")
        if not descriptors or len(descriptors) > MAX_DESCRIPTORS:
            _fail(f"variants[{index}].descriptors count is invalid")
        parsed: list[Descriptor] = []
        keys: list[tuple[str, tuple[str, ...], str, str]] = []
        for di, raw_item in enumerate(descriptors):
            raw = _obj(raw_item, f"variants[{index}].descriptors[{di}]")
            expected = {"descriptor_kind", "address", "parent", "placement_source", "reference_point", "profile_id", "source", "provenance", "shape"}
            if set(raw) != expected or raw.get("descriptor_kind") != "display-only-form-descriptor":
                _fail(f"descriptor {index}/{di} has invalid fields")
            key = _address(raw["address"], f"descriptor {index}/{di}.address")
            if key[0] != source["namespace"] or key in keys:
                _fail(f"descriptor {index}/{di} has invalid or duplicate address")
            keys.append(key)
            parent = None if raw["parent"] is None else _address(raw["parent"], f"descriptor {index}/{di}.parent")
            if parent is not None and parent[0] != source["namespace"]:
                _fail(f"descriptor {index}/{di}.parent namespace differs")
            placement = raw["placement_source"]
            if placement not in {"authored-root", "authored-containment", "authored-attachment"}:
                _fail(f"descriptor {index}/{di}.placement_source is invalid")
            if (placement == "authored-root") != (parent is None):
                _fail(f"descriptor {index}/{di} root/parent relationship is invalid")
            if raw["profile_id"] != VARIANT_IDS[index] or raw["source"] != "profile-derived-display":
                _fail(f"descriptor {index}/{di} provenance is invalid")
            descriptor_provenance = _obj(raw["provenance"], f"descriptor {index}/{di}.provenance")
            if set(descriptor_provenance) != {"source", "resource_profile_id"} or descriptor_provenance != provenance:
                _fail(f"descriptor {index}/{di}.provenance is invalid")
            point = _vector(raw["reference_point"], f"descriptor {index}/{di}.reference_point")
            shape = _shape(raw["shape"], f"descriptor {index}/{di}.shape")
            parsed.append(Descriptor(key, parent, np.asarray(point, dtype=np.float64) / reference_scale, point, shape, placement, raw["profile_id"], raw["source"], descriptor_provenance, raw))
        sorted_keys = sorted(keys)
        if keys != sorted_keys:
            _fail(f"variants[{index}].descriptors are not stable AddressKey order")
        keyset = set(keys)
        if sum(x.parent is None for x in parsed) != 1 or parent_key not in keyset or child_key not in keyset:
            _fail(f"variants[{index}] root or reference addresses are invalid")
        by_key = {x.key: x for x in parsed}
        for desc in parsed:
            if desc.parent is not None and desc.parent not in keyset:
                _fail(f"variants[{index}] contains a missing parent")
            lineage: set[Any] = set()
            current: tuple[str, tuple[str, ...], str, str] | None = desc.key
            while current is not None:
                if current in lineage:
                    _fail(f"variants[{index}] contains a parent cycle")
                lineage.add(current)
                current = by_key[current].parent
        signature = [(x.key, x.exact_point, x.parent, x.placement_source, x.shape["name"]) for x in parsed]
        if canonical is None:
            canonical = signature
        elif signature != canonical:
            _fail(f"variants[{index}] do not preserve semantic descriptor identity")
        normalized.append((VARIANT_IDS[index], tuple(parsed), variant))
    if canonical is None:
        _fail("no descriptors")
    candidates = []
    points = {row[0]: row[1] for row in canonical}
    parents = {row[0]: row[2] for row in canonical}
    for child, parent in parents.items():
        if parent is not None:
            d = tuple(points[child][i] - points[parent][i] for i in range(3))
            sq = sum(x * x for x in d)
            if sq:
                candidates.append((sq, child, parent, tuple(d)))
    if not candidates or (squared, child_key, parent_key, delta) != min(candidates, key=lambda x: (x[0], x[1])):
        _fail("reference_scale does not name the selected exact descriptor edge")
    return Form(root, source, reference_scale, scale, tuple(normalized))


def _key_text(key: tuple[str, tuple[str, ...], str, str]) -> str:
    return json.dumps(_address_json(key), sort_keys=True, separators=(",", ":"))


def _segment_field(points: np.ndarray, start: np.ndarray, end: np.ndarray, r0: float, r1: float) -> np.ndarray:
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    t = np.clip(np.sum((points - start) * axis, axis=-1) / length_sq, 0.0, 1.0)
    closest = start + t[..., None] * axis
    radius = r0 + (r1 - r0) * t
    return np.linalg.norm(points - closest, axis=-1) - radius


def _field(points: np.ndarray, desc: Descriptor, scale: float) -> np.ndarray:
    shape = desc.shape
    if shape["name"] == "ellipsoid":
        centre = np.asarray(shape["center"], dtype=np.float64) / scale
        radii = np.asarray(shape["axis_extents_permille"], dtype=np.float64) / 1000.0
        offset = points - centre
        normalized = np.sqrt(np.sum((offset / radii) ** 2, axis=-1))
        return (normalized - 1.0) * float(np.min(radii))
    start = np.asarray(shape["from"], dtype=np.float64) / scale
    end = np.asarray(shape["to"], dtype=np.float64) / scale
    if shape["name"] == "capsule":
        radius = float(shape["radius_permille"]) / 1000.0
        return _segment_field(points, start, end, radius, radius)
    return _segment_field(points, start, end, float(shape["start_radius_permille"]) / 1000.0, float(shape["end_radius_permille"]) / 1000.0)


def _smooth_union(fields: list[np.ndarray], k: float) -> np.ndarray:
    result = fields[0].copy()
    for current in fields[1:]:
        h = np.maximum(k - np.abs(result - current), 0.0)
        result = np.minimum(result, current) - (h**3) / (6.0 * k * k)
    return result


def _bounds(descriptors: tuple[Descriptor, ...], scale: float, padding: float) -> tuple[np.ndarray, np.ndarray]:
    mins: list[np.ndarray] = []
    maxs: list[np.ndarray] = []
    for desc in descriptors:
        shape = desc.shape
        if shape["name"] == "ellipsoid":
            centre = np.asarray(shape["center"], dtype=np.float64) / scale
            radii = np.asarray(shape["axis_extents_permille"], dtype=np.float64) / 1000.0
            mins.append(centre - radii); maxs.append(centre + radii)
        else:
            a = np.asarray(shape["from"], dtype=np.float64) / scale
            b = np.asarray(shape["to"], dtype=np.float64) / scale
            r = max(float(shape.get("radius_permille", shape.get("start_radius_permille", 0))), float(shape.get("radius_permille", shape.get("end_radius_permille", 0)))) / 1000.0
            mins.append(np.minimum(a, b) - r); maxs.append(np.maximum(a, b) + r)
    return np.min(np.stack(mins), axis=0) - padding, np.max(np.stack(maxs), axis=0) + padding


def _orientation(vertices: np.ndarray, faces: np.ndarray, axes: tuple[np.ndarray, np.ndarray, np.ndarray], descriptors: tuple[Descriptor, ...], scale: float, k: float) -> tuple[np.ndarray, np.ndarray, float]:
    e1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    e2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    areas = np.cross(e1, e2)
    centers = (vertices[faces[:, 0]] + vertices[faces[:, 1]] + vertices[faces[:, 2]]) / 3.0
    delta = 0.5 * min(float(axes[i][1] - axes[i][0]) for i in range(3))
    def combined(points: np.ndarray) -> np.ndarray:
        vals = [_field(points, d, scale) for d in descriptors]
        return _smooth_union(vals, k)
    gradient = np.column_stack([(combined(centers + np.eye(3)[i] * delta) - combined(centers - np.eye(3)[i] * delta)) / (2.0 * delta) for i in range(3)])
    alignment = np.sum(areas * gradient, axis=1)
    if float(np.mean(alignment)) < 0.0:
        faces = faces[:, [0, 2, 1]]
        areas = -areas
        alignment = -alignment
    volume = float(np.sum(np.einsum("ij,ij->i", vertices[faces[:, 0]], areas)) / 6.0)
    if not math.isfinite(volume) or volume <= 0:
        _fail("mesh winding has non-positive signed volume")
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], areas)
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= 1e-14) or not np.all(np.isfinite(lengths)):
        _fail("mesh contains undefined normals")
    return faces, normals / lengths[:, None], volume


def _mesh_checks(vertices: np.ndarray, faces: np.ndarray, labels: list[tuple[str, tuple[str, ...], str, str]], bounds: tuple[np.ndarray, np.ndarray], volume: float) -> dict[str, Any]:
    if len(vertices) == 0 or len(faces) == 0 or not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(faces)):
        _fail("mesh is empty or non-finite")
    if np.any(faces < 0) or np.any(faces >= len(vertices)):
        _fail("mesh indices are invalid")
    areas = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]])
    if np.any(np.linalg.norm(areas, axis=1) <= 1e-14):
        _fail("mesh contains degenerate faces")
    edges: dict[tuple[int, int], int] = {}
    adjacency: list[set[int]] = [set() for _ in vertices]
    for face in faces:
        a, b, c = (int(x) for x in face)
        adjacency[a].update((b, c)); adjacency[b].update((a, c)); adjacency[c].update((a, b))
        for x, y in ((a, b), (b, c), (c, a)):
            edge = (min(x, y), max(x, y)); edges[edge] = edges.get(edge, 0) + 1
    if any(count != 2 for count in edges.values()):
        _fail("mesh is not watertight")
    seen: set[int] = set(); components = 0
    for start in range(len(vertices)):
        if start in seen: continue
        components += 1; stack = [start]; seen.add(start)
        while stack:
            for neighbour in adjacency[stack.pop()]:
                if neighbour not in seen: seen.add(neighbour); stack.append(neighbour)
    if components != 1:
        _fail(f"mesh has {components} connected components")
    lower, upper = bounds
    clearance = float(np.min(np.minimum(vertices - lower, upper - vertices)))
    if not math.isfinite(clearance) or clearance <= 0:
        _fail("surface is clipped by the sampling domain")
    unique_winners = sorted(set(labels))
    return {"vertex_count": int(len(vertices)), "face_count": int(len(faces)), "component_count": components, "watertight": True, "finite_vertices": True, "finite_normals": True, "valid_indices": True, "signed_volume": volume, "domain_clearance": clearance, "winner_vertex_count": len(labels), "unique_winner_count": len(unique_winners), "winner_addresses": [_address_json(key) for key in unique_winners]}


def build_variant(form: Form, descriptors: tuple[Descriptor, ...], samples: int, padding: float, smooth_k: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[str, tuple[str, ...], str, str]], dict[str, Any], dict[str, Any]]:
    if type(samples) is not int or samples > MAX_SAMPLES or samples < 16 or samples**3 > MAX_VOXELS:
        _fail("sampling configuration exceeds bounded limits")
    if len(descriptors) * samples**3 > MAX_FIELD_VALUES:
        _fail("descriptor sampling configuration exceeds bounded field-memory limits")
    if not math.isfinite(float(padding)) or padding < 0.0 or not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("padding and smooth-k must be finite, with non-negative padding and positive smooth-k")
    lower, upper = _bounds(descriptors, form.reference_scale, padding)
    axes = tuple(np.linspace(lower[i], upper[i], samples, dtype=np.float64) for i in range(3))
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    fields = [_field(points, desc, form.reference_scale) for desc in descriptors]
    field = _smooth_union(fields, smooth_k)
    if not np.all(np.isfinite(field)) or float(np.min(field)) >= 0 or float(np.max(field)) <= 0:
        _fail("field has no finite zero crossing")
    if np.any(field[(0, -1), :, :] <= 0) or np.any(field[:, (0, -1), :] <= 0) or np.any(field[:, :, (0, -1)] <= 0):
        _fail("field reaches the sampling domain boundary")
    try:
        raw_vertices, raw_faces, _, _ = marching_cubes(field, level=0.0, spacing=tuple(float(a[1]-a[0]) for a in axes), gradient_direction="descent", allow_degenerate=False)
    except Exception as exc:
        raise PreviewError(f"surface extraction failed: {exc}") from exc
    vertices = np.asarray(raw_vertices, dtype=np.float64) + lower
    faces = np.asarray(raw_faces, dtype=np.int64)
    faces, normals, volume = _orientation(vertices, faces, axes, descriptors, form.reference_scale, smooth_k)
    labels: list[tuple[str, tuple[str, ...], str, str]] = []
    # Re-evaluate only at vertices; this avoids carrying a grid-shaped winner channel into artifacts.
    for vertex in vertices:
        values = [_field(vertex.reshape(1, 3), desc, form.reference_scale)[0] for desc in descriptors]
        labels.append(descriptors[int(np.argmin(values))].key)
    metrics = _mesh_checks(vertices, faces, labels, (lower, upper), volume)
    metrics.update({"field_minimum": float(np.min(field)), "field_maximum": float(np.max(field)), "smooth_union": {"operator": "polynomial_cubic_smooth_min", "k": smooth_k, "fold_order": "full_address_key_ascending"}, "grid": {"samples_per_axis": samples, "axis_order": ["x", "y", "z"], "bounds_min": lower.tolist(), "bounds_max": upper.tolist(), "spacing": [float(a[1]-a[0]) for a in axes]}})
    return vertices, faces, normals, labels, metrics, {"bounds_min": lower.tolist(), "bounds_max": upper.tolist(), "spacing": [float(a[1]-a[0]) for a in axes]}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _write_ply(path: Path, vertices: np.ndarray, faces: np.ndarray, normals: np.ndarray) -> None:
    lines = ["ply", "format ascii 1.0", f"element vertex {len(vertices)}", "property float x", "property float y", "property float z", "property float nx", "property float ny", "property float nz", f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header"]
    lines.extend("%.9f %.9f %.9f %.9f %.9f %.9f" % tuple([*v, *n]) for v, n in zip(vertices, normals))
    lines.extend("3 %d %d %d" % tuple(int(x) for x in f) for f in faces)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _render(path: Path, vertices: np.ndarray, faces: np.ndarray, variant_id: str) -> None:
    image = Image.new("RGB", CANVAS, (24, 27, 34)); draw = ImageDraw.Draw(image); font = ImageFont.load_default()
    draw.text((16, 16), f"Disposable continuous-surface preview - {variant_id} - neutral shading", fill=(235, 238, 244), font=font)
    root2 = math.sqrt(2.0)
    views = {"front": np.eye(3), "side": np.array([[0., 0., -1.], [0., 1., 0.], [1., 0., 0.]]), "three-quarter": np.array([[1/root2, 0., -1/root2], [0., 1., 0.], [1/root2, 0., 1/root2]])}
    light = np.asarray((0.35, 0.55, 0.76), dtype=np.float64); light /= np.linalg.norm(light)
    for name, basis in views.items():
        x0, y0, x1, y1 = VIEW_BOXES[name]; camera = vertices @ basis.T; triangles = camera[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]); visible = normals[:, 2] > 0
        order = np.flatnonzero(visible); order = order[np.argsort(np.mean(triangles[order, :, 2], axis=1))]
        projected = camera[:, :2]; lo, hi = projected.min(axis=0), projected.max(axis=0); span = np.maximum(hi - lo, 1e-9); scale = min((x1-x0-34)/span[0], (y1-y0-56)/span[1]); centre = (lo+hi)/2
        def screen(points: np.ndarray) -> list[tuple[float, float]]:
            return [(x0+(x1-x0)/2+float((p[0]-centre[0])*scale), y0+30+(y1-y0-48)/2-float((p[1]-centre[1])*scale)) for p in points]
        for index in order:
            normal = normals[index]; length = np.linalg.norm(normal)
            if length <= 1e-12: continue
            brightness = 0.42 + 0.58 * max(0.0, float(np.dot(normal / length, light))); colour = (int(148 * brightness), int(165 * brightness), int(184 * brightness))
            draw.polygon(screen(triangles[index, :, :2]), fill=colour)
        draw.rectangle((x0, y0, x1, y1), outline=(74, 82, 96), width=2); draw.text((x0+12, y0+10), name, fill=(235, 238, 244), font=font)
    image.save(path, format="PNG")


def _sha(path: Path, kind: str, root: Path) -> dict[str, Any]:
    data = path.read_bytes(); return {"kind": kind, "path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def generate(input_path: Path, output: Path, *, samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> dict[str, Any]:
    if output.exists() or os.path.lexists(output): _fail(f"refusing to overwrite output: {output}")
    if not output.parent.is_dir(): _fail(f"output parent must exist: {output.parent}")
    data = input_path.read_bytes()
    if len(data) > MAX_INPUT_BYTES: _fail("input exceeds bounded size")
    try: value = json.loads(data.decode("utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc: raise PreviewError(f"input is not finite JSON: {exc}") from exc
    form = validate_envelope(value)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        records = []
        for variant_id, descriptors, raw_variant in form.variants:
            vertices, faces, normals, labels, metrics, grid = build_variant(form, descriptors, samples, padding, smooth_k)
            variant_dir = stage / variant_id
            variant_dir.mkdir()
            ply = variant_dir / "surface.ply"; sidecar = variant_dir / "semantic.json"; metrics_path = variant_dir / "metrics.json"; png = variant_dir / "composite.png"
            _write_ply(ply, vertices, faces, normals)
            sidecar.write_bytes(_canonical({"format": "creature-kernel.disposable-surface-preview-semantic-winners.v1", "source_format": SOURCE_FORMAT, "variant_id": variant_id, "vertex_count": len(vertices), "source_node_labels": [_address_json(key) for key in labels]}))
            metrics_path.write_bytes(_canonical(metrics)); _render(png, vertices, faces, variant_id)
            records.append({"id": variant_id, "profile_id": raw_variant["profile_id"], "source": {"document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"]}, "descriptor_address_keys": [_address_json(desc.key) for desc in descriptors], "grid": grid, "metrics": metrics, "inventory": [_sha(ply, "ply", stage), _sha(sidecar, "semantic-sidecar", stage), _sha(metrics_path, "metrics", stage), {**_sha(png, "neutral-composite-png", stage), "width": CANVAS[0], "height": CANVAS[1], "views": ["front", "side", "three-quarter"], "mode": "RGB"}]})
        manifest = {"format": FORMAT, "status": "success", "source_format": SOURCE_FORMAT, "source": {"format": SOURCE_FORMAT, "sha256": hashlib.sha256(data).hexdigest(), "document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"], "reference_scale": form.reference_scale_raw}, "generator": {"samples_per_axis": samples, "padding": padding, "smooth_union": {"operator": "polynomial_cubic_smooth_min", "k": smooth_k, "fold_order": "full_address_key_ascending"}, "field_primitives": ["ellipsoid", "capsule", "linear-radius-tapered-segment"], "boundary": "disposable exploratory visual proof; not production geometry, SDF, collision, rig, topology, or Readiness evidence"}, "variants": records}
        (stage / "surface-preview-manifest.json").write_bytes(_canonical(manifest) + b"\n")
        expected_files = {"surface-preview-manifest.json"}
        expected_directories = set(VARIANT_IDS)
        for record in records:
            expected_files.update(entry["path"] for entry in record["inventory"])
        actual_files: set[str] = set()
        actual_directories: set[str] = set()
        for item in stage.rglob("*"):
            relative = item.relative_to(stage).as_posix()
            if item.is_symlink():
                _fail(f"staging bundle contains a symlink: {relative}")
            if item.is_dir():
                actual_directories.add(relative)
            elif item.is_file():
                actual_files.add(relative)
            else:
                _fail(f"staging bundle contains a non-regular path: {relative}")
        if actual_directories != expected_directories or actual_files != expected_files:
            _fail("staging bundle does not match its explicit artifact inventory")
        os.replace(stage, output)
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True); raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a disposable current-form continuous-surface preview")
    parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--samples-per-axis", type=int, default=DEFAULT_SAMPLES); parser.add_argument("--padding", type=float, default=DEFAULT_PADDING); parser.add_argument("--smooth-k", type=float, default=DEFAULT_SMOOTH_K)
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.input, args.output, samples=args.samples_per_axis, padding=args.padding, smooth_k=args.smooth_k)
    except (OSError, PreviewError, ValueError) as exc:
        print(json.dumps({"format": FORMAT, "status": "failure", "error": str(exc)}, sort_keys=True), file=sys.stderr); return 2
    print(json.dumps({"format": FORMAT, "status": "success", "output": str(args.output), "variants": [x["id"] for x in manifest["variants"]]}, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Exact quad export and same-surface Pillow evidence rendering."""
from __future__ import annotations

import hashlib
import math
import re
import struct
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import owned_root_surface as _surface


class RenderExportError(ValueError):
    """Raised when an export or render input is outside the closed contract."""
WIDTH = HEIGHT = PANEL_WIDTH = PANEL_HEIGHT = 512
FACE_COUNT, VERTEX_COUNT, TRIANGLE_COUNT = 1664, 1737, 3328
PANEL_ORDER = ("front", "side", "45deg")
BACKGROUND_RGB, DIRECT_RGB = (247, 247, 247), (188, 198, 210)
PALETTE = {"domain.pelvis": (214, 83, 83), "domain.abdomen": (226, 157, 68), "domain.thorax": (93, 150, 213), "domain.neck": (153, 102, 204), "domain.left_shoulder": (81, 168, 115), "domain.right_shoulder": (81, 168, 115), "domain.left_hip": (221, 112, 166), "domain.right_hip": (221, 112, 166)}
CAMERAS = (("front", (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), ("side", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)), ("45deg", (0.7071067811865476, 0.0, -0.7071067811865475), (0.0, 1.0, 0.0), (0.7071067811865475, 0.0, 0.7071067811865476)))
CONFIG_KEYS = ("width", "height", "panel_width", "panel_height", "panel_order", "padding", "background_rgb", "direct_rgb", "domain_palette", "cameras", "common_scale_rule", "pixel_center_rule", "barycentric_tolerance", "degenerate_tolerance", "depth_rule", "tie_rule", "quad_split", "shading", "lighting", "labels", "outlines", "anti_aliasing", "alpha", "culling", "pillow_version", "png_compress_level", "png_optimize", "png_metadata")

def _frozen_l2_authority():
    (controls, quads, loops), owners = _surface.symbolic_topology(), tuple(record[1] for record in _surface.FACE_RECORDS)
    mesh = _surface.Mesh((None,) * len(controls), quads, (), (), (), loops)
    for level in (1, 2):
        incidence = _surface.subdivision_incidence(mesh)
        quads, owners = tuple(child[2] for child in incidence["child_emission"]), tuple(owners[child[0]] for child in incidence["child_emission"])
        mesh = _surface.Mesh((None,) * (len(mesh.vertices) + len(incidence["edges"]) + len(mesh.quads)), quads, (), (), (), incidence["propagated_port_loops"], level=level)
    return quads, tuple(item for face in quads for item in ((face[0], face[1], face[2]), (face[0], face[2], face[3]))), owners
_FROZEN_QUADS, _FROZEN_TRIANGLES, _FROZEN_OWNERS = _frozen_l2_authority()

def _fl(value: float) -> float:
    return float(value)
def _reject(condition: bool, message: str) -> None:
    if condition:
        raise RenderExportError(message)
def _finite(value: object, label: str) -> float:
    _reject(type(value) is not float or not math.isfinite(value), f"{label} must be a finite binary64 float")
    return value
def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    x, y, z = (_fl(left[i] * right[i]) for i in range(3))
    return _fl(_fl(x + y) + z)
def _vector(row: object, index: int) -> tuple[float, float, float]:
    _reject(type(row) not in (tuple, list) or len(row) != 3, f"vertex {index} is not a vector3")
    return tuple(_finite(item, f"vertex {index}") for item in row)
def _quad(row: object, index: int, vertex_count: int) -> tuple[int, int, int, int]:
    _reject((type(row) not in (tuple, list) or len(row) != 4 or any(type(item) is not int for item in row) or len(set(row)) != 4 or any(not 0 <= item < vertex_count for item in row)), f"quad {index} is invalid")
    return tuple(row)
def _parts(value: object, quads: object = None, *, level: int | None = None, owners: bool = False) -> tuple[Any, ...]:
    if quads is None:
        vertices, quads = getattr(value, "vertices", None), getattr(value, "quads", None)
        _reject(level is not None and getattr(value, "level", None) != level, f"mesh must be level {level}")
        face_owners = getattr(value, "face_owners", None)
    else:
        vertices, face_owners = value, None
    _reject(type(vertices) not in (tuple, list) or type(quads) not in (tuple, list), "vertices and quads must be concrete sequences")
    points = tuple(_vector(row, index) for index, row in enumerate(vertices))
    _reject(not points, "mesh has no vertices")
    faces = tuple(_quad(row, index, len(points)) for index, row in enumerate(quads))
    _reject(not faces, "mesh has no quads")
    if owners:
        _reject(type(face_owners) not in (tuple, list) or len(face_owners) != len(faces) or any(type(item) is not str for item in face_owners), "level-2 mesh has no exact face ownership")
    return points, faces, tuple(face_owners) if owners else ()
def _coordinate(value: float) -> str:
    value = _finite(value, "coordinate")
    if value == 0.0:
        return "0"
    text = format(value, ".17g")
    if "e" not in text:
        return text
    mantissa, exponent = text.split("e")
    sign = "-" if exponent.startswith("-") else "+"
    digits = exponent.lstrip("+-").lstrip("0") or "0"
    return f"{mantissa}e{sign}{digits}"
def ply_bytes(value: object, quads: object = None) -> bytes:
    points, faces, _ = _parts(value, quads)
    rows = ["ply", "format ascii 1.0", f"element vertex {len(points)}", "property double x", "property double y", "property double z", f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header"]
    rows.extend(" ".join(_coordinate(item) for item in point) for point in points)
    rows.extend("4 " + " ".join(str(item) for item in face) for face in faces)
    data = ("\n".join(rows) + "\n").encode("ascii")
    _reject(len(data) > 2 * 1024 * 1024, "PLY exceeds the frozen 2 MiB limit")
    return data
def render_config_record() -> dict[str, Any]:
    return {
        "width": 512, "height": 1536, "panel_width": 512, "panel_height": 512, "panel_order": list(PANEL_ORDER), "padding": 24, "background_rgb": list(BACKGROUND_RGB),
        "direct_rgb": list(DIRECT_RGB), "domain_palette": {k: list(v) for k, v in PALETTE.items()}, "cameras": [{"name": n, "right": list(r), "up": list(u), "depth": list(d)} for n, r, u, d in CAMERAS],
        "common_scale_rule": "aabb-midpoint-all-views-extent-232.v1", "pixel_center_rule": "column-plus-0.5-row-plus-0.5-y-down.v1",
        "barycentric_tolerance": -1e-12, "degenerate_tolerance": 1e-15, "depth_rule": "larger-depth-wins", "tie_rule": "lower-triangle-index-wins",
        "quad_split": [[0, 1, 2], [0, 2, 3]], "shading": False, "lighting": False, "labels": False, "outlines": False,
        "anti_aliasing": False, "alpha": False, "culling": False, "pillow_version": "11.1.0", "png_compress_level": 9, "png_optimize": False, "png_metadata": {},
    }
def _exact(value: object, expected: object, *, canonical_wire: bool = False) -> bool:
    if canonical_wire and type(expected) is float and expected == 0.0:
        return (type(value) is float and value == expected) or (type(value) is int and value == 0)
    return type(value) is type(expected) and ((all(type(key) is str for key in value) and set(value) == set(expected) and all(_exact(value[key], item, canonical_wire=canonical_wire) for key, item in expected.items())) if type(expected) is dict else (len(value) == len(expected) and all(_exact(item, wanted, canonical_wire=canonical_wire) for item, wanted in zip(value, expected))) if type(expected) is list else value == expected)
def validate_render_config(value: object) -> None:
    _reject(not _exact(value, render_config_record(), canonical_wire=True), "render_config is not the exact closed record")
@dataclass(frozen=True)
class VisibilityBuffer:
    owners: tuple[int | None, ...]
    depths: tuple[float | None, ...]
    triangle_owners: tuple[str, ...]
    triangle_index_sha256: str
    degenerate_triangles: int
def _hash_triangles(triangles: tuple[tuple[int, int, int], ...]) -> str:
    return hashlib.sha256(b"".join(struct.pack("<qqq", *triangle) for triangle in triangles)).hexdigest()
def _accept_sample(owners: list[int | None], depths: list[float | None], index: int, triangle: int, depth: float) -> None:
    prior = depths[index]
    equal = prior is not None and struct.pack("<d", depth) == struct.pack("<d", prior)
    if prior is None or depth > prior or (equal and triangle < owners[index]):
        depths[index], owners[index] = depth, triangle
def visibility_record(value: VisibilityBuffer) -> dict[str, Any]:
    _validate_visibility(value)
    return {"level": 2, "triangle_count": TRIANGLE_COUNT, "triangle_index_sha256": value.triangle_index_sha256, "rule": "larger-depth-then-lower-triangle-index"}
def _pillow() -> Any:
    try:
        import PIL
        from PIL import Image
    except ImportError as exc:
        raise RenderExportError("Pillow 11.1.0 is required") from exc
    _reject(PIL.__version__ != "11.1.0", "renderer requires Pillow 11.1.0")
    return Image
def _validate_visibility(value: object) -> None:
    _reject(type(value) is not VisibilityBuffer, "invalid visibility buffer")
    _reject(not (type(value.owners) is tuple and type(value.depths) is tuple and len(value.owners) == 3 * WIDTH * HEIGHT and len(value.depths) == len(value.owners) and type(value.triangle_owners) is tuple and len(value.triangle_owners) == TRIANGLE_COUNT and type(value.triangle_index_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", value.triangle_index_sha256) is not None and type(value.degenerate_triangles) is int and value.degenerate_triangles >= 0), "visibility buffer has an invalid closed shape")
    _reject(any(item is not None and (type(item) is not int or not 0 <= item < TRIANGLE_COUNT) for item in value.owners), "visibility buffer has an invalid triangle owner")
    _reject(any(item is not None and (type(item) is not float or not math.isfinite(item)) for item in value.depths), "visibility buffer has an invalid depth")
    _reject(any((owner is None) != (depth is None) for owner, depth in zip(value.owners, value.depths)), "visibility buffer owner/depth occupancy disagrees")
    _reject(any(type(item) is not str or item not in PALETTE for item in value.triangle_owners), "visibility buffer has an invalid domain owner")
def _panel_candidates(screen: tuple[tuple[float, float, float], ...], triangles):
    records, rows, degenerate = [], [[] for _ in range(HEIGHT)], 0
    for triangle_index, (a, b, c) in enumerate(triangles):
        ax, ay, za = screen[a]
        bx, by, zb = screen[b]
        cx, cy, zc = screen[c]
        d0, d1, d2, d3 = _fl(by - cy), _fl(ax - cx), _fl(cx - bx), _fl(ay - cy)
        denominator = _fl(_fl(d0 * d1) + _fl(d2 * d3))
        _reject(not math.isfinite(denominator), "barycentric denominator is non-finite")
        if abs(denominator) <= 1e-15:
            records.append(None)
            degenerate += 1
            continue
        c0, c1 = max(0, math.floor(min(ax, bx, cx) - 0.5) - 1), min(511, math.ceil(max(ax, bx, cx) - 0.5) + 1)
        r0, r1 = max(0, math.floor(min(ay, by, cy) - 0.5) - 1), min(511, math.ceil(max(ay, by, cy) - 0.5) + 1)
        records.append((ax, ay, za, bx, by, zb, cx, cy, zc, d0, d2, _fl(cy - ay), _fl(ax - cx), denominator, c0, c1))
        for row in range(r0, r1 + 1):
            rows[row].append((triangle_index, c0, c1))
    return records, rows, degenerate
def build_visibility(mesh: object) -> VisibilityBuffer:
    points, faces, face_owners = _parts(mesh, level=2, owners=True)
    _reject((len(points), len(faces)) != (VERTEX_COUNT, FACE_COUNT), "level-2 mesh has the wrong closed cardinality")
    _reject(faces != _FROZEN_QUADS or face_owners != _FROZEN_OWNERS, "level-2 topology or ancestry differs from frozen public authority")
    triangles, catalog = _FROZEN_TRIANGLES, getattr(mesh, "triangles", None)
    _reject(type(catalog) not in (tuple, list) or tuple(catalog) != triangles, "level-2 triangle catalog differs from frozen public topology")
    expected_ids, face_ids = tuple(f"face.L2.q{i:04d}" for i in range(FACE_COUNT)), getattr(mesh, "face_ids", None)
    _reject(type(face_ids) not in (tuple, list) or tuple(face_ids) != expected_ids, "level-2 face catalog does not match its numeric order")
    low = tuple(min(point[axis] for point in points) for axis in range(3))
    high = tuple(max(point[axis] for point in points) for axis in range(3))
    midpoint = tuple(_fl(_fl(low[axis] + high[axis]) / 2.0) for axis in range(3))
    projected, extent = [], 0.0
    for _, right, up, depth in CAMERAS:
        panel = []
        for point in points:
            relative = tuple(_fl(point[axis] - midpoint[axis]) for axis in range(3))
            u, v, z = _dot(relative, right), _dot(relative, up), _dot(relative, depth)
            _reject(not all(math.isfinite(item) for item in (u, v, z)), "camera projection is non-finite")
            extent = max(extent, abs(u), abs(v))
            panel.append((u, v, z))
        projected.append(panel)
    _reject(not all(math.isfinite(item) for item in midpoint) or not math.isfinite(extent) or extent <= 0.0, "camera extent is not positive and finite")
    scale = _fl(232.0 / extent)
    screens = [tuple((_fl(256.0 + _fl(scale * u)), _fl(256.0 - _fl(scale * v)), z) for u, v, z in panel) for panel in projected]
    owners, depths, degenerate = [None] * (3 * WIDTH * HEIGHT), [None] * (3 * WIDTH * HEIGHT), 0
    for panel_index, screen in enumerate(screens):
        records, rows, count = _panel_candidates(screen, triangles)
        degenerate += count
        base = panel_index * WIDTH * HEIGHT
        for row in range(HEIGHT):
            for column in range(WIDTH):
                for triangle_index, c0, c1 in rows[row]:
                    if not c0 <= column <= c1:
                        continue
                    (_ax, _ay, za, _bx, _by, zb, cx, cy, zc, n0a, n0c, n1a, n1c, denominator, _, _) = records[triangle_index]
                    px, py = _fl(column + 0.5), _fl(row + 0.5)
                    n0 = _fl(_fl(n0a * _fl(px - cx)) + _fl(n0c * _fl(py - cy)))
                    w0 = _fl(n0 / denominator)
                    n1 = _fl(_fl(n1a * _fl(px - cx)) + _fl(n1c * _fl(py - cy)))
                    w1 = _fl(n1 / denominator)
                    w2 = _fl(_fl(1.0 - w0) - w1)
                    sample_depth = _fl(_fl(_fl(w0 * za) + _fl(w1 * zb)) + _fl(w2 * zc))
                    _reject(not all(math.isfinite(item) for item in (n0, w0, n1, w1, w2, sample_depth)), "barycentric evaluation is non-finite")
                    if w0 >= -1e-12 and w1 >= -1e-12 and w2 >= -1e-12:
                        _accept_sample(owners, depths, base + row * WIDTH + column, triangle_index, sample_depth)
    return VisibilityBuffer(tuple(owners), tuple(depths), tuple(_FROZEN_OWNERS[index // 2] for index in range(TRIANGLE_COUNT)), _hash_triangles(triangles), degenerate)
def render_png_bytes(value: VisibilityBuffer | object, *, lineage: bool = False) -> bytes:
    _reject(type(lineage) is not bool, "lineage must be a boolean")
    visibility = value if type(value) is VisibilityBuffer else build_visibility(value)
    _validate_visibility(visibility)
    pixels = (image := _pillow().new("RGB", (WIDTH, 3 * HEIGHT), BACKGROUND_RGB)).load()
    for panel in range(3):
        for row in range(HEIGHT):
            for column in range(WIDTH):
                triangle = visibility.owners[panel * WIDTH * HEIGHT + row * WIDTH + column]
                if triangle is not None:
                    pixels[column, panel * HEIGHT + row] = PALETTE[visibility.triangle_owners[triangle]] if lineage else DIRECT_RGB
    output = BytesIO()
    image.save(output, format="PNG", compress_level=9, optimize=False)
    data = output.getvalue()
    _reject(len(data) > 2 * 1024 * 1024, "PNG exceeds the frozen 2 MiB limit")
    return data
def render_pair_bytes(mesh: object) -> tuple[bytes, bytes, VisibilityBuffer]:
    visibility = build_visibility(mesh)
    return render_png_bytes(visibility), render_png_bytes(visibility, lineage=True), visibility
__all__ = ["RenderExportError", "VisibilityBuffer", "build_visibility", "ply_bytes", "render_config_record", "render_pair_bytes", "render_png_bytes", "validate_render_config", "visibility_record"]

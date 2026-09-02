"""Small, direct evidence renderer for raw evaluated quad meshes.

This module deliberately has no knowledge of the candidate that produced a
mesh.  It validates, triangulates, exports, and draws only the supplied data.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from skimage.draw import polygon as raster_polygon


CANVAS_SIZE = (1800, 600)
PANEL_SIZE = (600, 600)
PANEL_MARGIN = 28
VIEW_NAMES = ("front", "side", "three-quarter")
_SQRT_HALF = 1.0 / np.sqrt(2.0)
_BASE_COLOUR = (92, 145, 196)
_BACKGROUND = (18, 22, 30)
_LIGHT = np.asarray((-0.35, 0.70, 0.58), dtype=np.float64)
_LIGHT /= np.linalg.norm(_LIGHT)
_VIEW_BASES = (
    np.eye(3, dtype=np.float64),
    np.asarray(((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))),
    np.asarray(((_SQRT_HALF, 0.0, -_SQRT_HALF), (0.0, 1.0, 0.0), (_SQRT_HALF, 0.0, _SQRT_HALF))),
)


def _validated_mesh(vertices: object, quads: object) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    try:
        points = np.asarray(vertices, dtype=np.float64)
        raw_faces = np.asarray(quads, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("vertices and quad faces must be numeric arrays") from exc
    if points.ndim != 2 or points.shape[1:] != (3,) or len(points) == 0:
        raise ValueError("vertices must be a non-empty N x 3 array")
    if raw_faces.ndim != 2 or raw_faces.shape[1:] != (4,):
        raise ValueError("quad faces must be an M x 4 array")
    if not np.isfinite(points).all() or not np.isfinite(raw_faces).all():
        raise ValueError("coordinates and indices must be finite")
    if not np.equal(raw_faces, np.floor(raw_faces)).all():
        raise ValueError("quad indices must be integers")
    if (raw_faces < 0).any() or (raw_faces >= len(points)).any():
        raise ValueError("quad index is outside the vertex array")
    faces = raw_faces.astype(np.int64)
    triangles = np.stack((faces[:, (0, 1, 2)], faces[:, (0, 2, 3)]), axis=1).reshape(-1, 3)
    return points, faces, triangles


def triangulate_quads(vertices: object, quads: object) -> np.ndarray:
    """Return the deterministic ``(a,b,c),(a,c,d)`` expansion of each quad."""
    return _validated_mesh(vertices, quads)[2].copy()


def _ply_bytes(vertices: np.ndarray, triangles: np.ndarray) -> bytes:
    header = (
        f"ply\nformat ascii 1.0\nelement vertex {len(vertices)}\n"
        "property double x\nproperty double y\nproperty double z\n"
        f"element face {len(triangles)}\nproperty list uchar int vertex_indices\nend_header"
    )
    lines = [header]
    lines.extend("%.17g %.17g %.17g" % tuple(point) for point in vertices)
    lines.extend("3 %d %d %d" % tuple(face) for face in triangles)
    return ("\n".join(lines) + "\n").encode("ascii")


def _write_new(path: str | Path, data: bytes) -> None:
    with Path(path).open("xb") as stream:
        stream.write(data)


def write_skin_ply(path: str | Path, vertices: object, quads: object) -> None:
    """Write ASCII PLY for exactly the supplied vertices and triangulated quads."""
    points, _, triangles = _validated_mesh(vertices, quads)
    _write_new(path, _ply_bytes(points, triangles))


def _frames(points: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray], float]:
    coordinate_bound = float(np.max(np.abs(points)))
    points = points / coordinate_bound if coordinate_bound > np.finfo(np.float64).max / 4.0 else points
    cameras = [points @ basis.T for basis in _VIEW_BASES]
    if not all(np.isfinite(camera).all() for camera in cameras):
        raise ValueError("projected coordinates must be finite")
    spans = [np.ptp(camera[:, :2], axis=0) for camera in cameras]
    maximum = np.max(np.asarray(spans), axis=0)
    available = np.asarray(PANEL_SIZE, dtype=np.float64) - 2.0 * PANEL_MARGIN
    scale = float(np.min(available / np.maximum(maximum, 1.0e-12)))
    centres = [(camera[:, :2].min(axis=0) + camera[:, :2].max(axis=0)) * 0.5 for camera in cameras]
    return cameras, centres, scale


def _screen(points: np.ndarray, centre: np.ndarray, scale: float, panel: int) -> list[tuple[float, float]]:
    values = (points[:, :2] - centre) * scale
    left = panel * PANEL_SIZE[0]
    return [
        (left + PANEL_SIZE[0] * 0.5 + float(point[0]), PANEL_SIZE[1] * 0.5 - float(point[1]))
        for point in values
    ]


def _rasterize_triangle(pixels: np.ndarray, depth: np.ndarray, camera: np.ndarray, triangle: np.ndarray, centre: np.ndarray, scale: float, panel: int, colour: tuple[int, int, int]) -> None:
    projected = (camera[triangle, :2] - centre) * scale
    left = panel * PANEL_SIZE[0]
    columns = projected[:, 0] + left + PANEL_SIZE[0] * 0.5
    rows = PANEL_SIZE[1] * 0.5 - projected[:, 1]
    rr, cc = raster_polygon(rows, columns, shape=depth.shape)
    denominator = ((columns[1] - columns[2]) * (rows[0] - rows[2]) + (rows[2] - rows[1]) * (columns[0] - columns[2]))
    if denominator == 0.0 or len(rr) == 0:
        return
    x = cc.astype(np.float64) + 0.5
    y = rr.astype(np.float64) + 0.5
    weights = np.asarray(((columns[1] - columns[2]) * (y - rows[2]) + (rows[2] - rows[1]) * (x - columns[2]), (columns[2] - columns[0]) * (y - rows[2]) + (rows[0] - rows[2]) * (x - columns[2]))) / denominator
    z = weights[0] * camera[triangle[0], 2] + weights[1] * camera[triangle[1], 2] + (1.0 - weights.sum(axis=0)) * camera[triangle[2], 2]
    visible = z > depth[rr, cc]
    depth[rr[visible], cc[visible]] = z[visible]
    pixels[rr[visible], cc[visible]] = colour


def _skin_png_bytes(points: np.ndarray, triangles: np.ndarray) -> bytes:
    cameras, centres, scale = _frames(points)
    coordinate_bound = float(np.max(np.abs(points)))
    lighting_points = points / coordinate_bound if coordinate_bound > np.finfo(np.float64).max / 4.0 else points
    pixels = np.full((CANVAS_SIZE[1], CANVAS_SIZE[0], 3), _BACKGROUND, dtype=np.uint8)
    for panel, camera in enumerate(cameras):
        depth = np.full((CANVAS_SIZE[1], CANVAS_SIZE[0]), -np.inf, dtype=np.float64)
        for triangle in triangles:
            normal = np.cross(lighting_points[triangle[1]] - lighting_points[triangle[0]], lighting_points[triangle[2]] - lighting_points[triangle[0]])
            length = float(np.linalg.norm(normal))
            brightness = 0.38 if length == 0.0 else 0.38 + 0.62 * max(0.0, float(np.dot(normal / length, _LIGHT)))
            colour = tuple(int(round(channel * brightness)) for channel in _BASE_COLOUR)
            _rasterize_triangle(pixels, depth, camera, triangle, centres[panel], scale, panel, colour)
    image = Image.fromarray(pixels, mode="RGB")
    draw = ImageDraw.Draw(image)
    for panel, name in enumerate(VIEW_NAMES):
        draw.rectangle((panel * PANEL_SIZE[0], 0, (panel + 1) * PANEL_SIZE[0] - 1, PANEL_SIZE[1] - 1), outline=(51, 59, 72))
        draw.text((panel * PANEL_SIZE[0] + 16, 14), name, fill=(220, 225, 235))
    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


def render_skin_png(path: str | Path, vertices: object, quads: object) -> None:
    """Render a metadata-free RGB sheet from the same triangles used by PLY."""
    points, _, triangles = _validated_mesh(vertices, quads)
    _write_new(path, _skin_png_bytes(points, triangles))


def _cage_png_bytes(points: np.ndarray, quads: np.ndarray) -> bytes:
    cameras, centres, scale = _frames(points)
    image = Image.new("RGB", CANVAS_SIZE, _BACKGROUND)
    draw = ImageDraw.Draw(image)
    for panel, camera in enumerate(cameras):
        draw.rectangle((panel * PANEL_SIZE[0], 0, (panel + 1) * PANEL_SIZE[0] - 1, PANEL_SIZE[1] - 1), outline=(51, 59, 72))
        camera_quads = camera[quads]
        order = np.argsort(camera_quads[:, :, 2].mean(axis=1), kind="mergesort")
        for quad_index in order:
            polygon = _screen(camera[quads[quad_index]], centres[panel], scale, panel)
            draw.polygon(polygon, fill=(34, 48, 65))
            draw.line(polygon + [polygon[0]], fill=(237, 188, 86), width=2, joint="curve")
        for point in _screen(camera, centres[panel], scale, panel):
            draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill=(255, 225, 138))
    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


def render_cage_png(path: str | Path, cage_vertices: object, cage_quads: object) -> None:
    """Render the supplied cage with edges and controls; depth is diagnostic only."""
    points, quads, _ = _validated_mesh(cage_vertices, cage_quads)
    _write_new(path, _cage_png_bytes(points, quads))

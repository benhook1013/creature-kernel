"""Small deterministic headless renderer for the pelvis/thigh experiment.

The renderer consumes the evaluated surface directly.  It has no geometry
repair, silhouette adjustment, hidden structure, or profile-specific path.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


class RenderError(ValueError):
    """Raised when a render input is unsafe or outside this local interface."""


CANVAS_SIZE = (1600, 550)
BACKGROUND = (239, 238, 234)
CLAY = np.array((190.0, 184.0, 174.0), dtype=np.float64)
# Actual fixed experiment lights: a directional key and a softer fill from
# the opposite direction.  These affect colour only; they never move geometry.
AMBIENT = 0.25
KEY_DIFFUSE = 0.60
FILL_DIFFUSE = 0.15
KEY_LIGHT_DIRECTION = np.array((-0.45, 0.78, 0.42), dtype=np.float64)
KEY_LIGHT_DIRECTION /= np.linalg.norm(KEY_LIGHT_DIRECTION)
FILL_LIGHT_DIRECTION = -KEY_LIGHT_DIRECTION
PIXEL_CENTER = 0.5
EPSILON = 1.0e-12


def _reject(condition: bool, message: str) -> None:
    if condition:
        raise RenderError(message)


def _vertices(value: Any) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise RenderError("vertices must be a numeric N x 3 sequence") from exc
    _reject(array.ndim != 2 or array.shape[1] != 3 or array.shape[0] == 0,
            "vertices must be a non-empty N x 3 sequence")
    _reject(np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.number),
            "vertices must contain real numeric values")
    try:
        points = np.asarray(array, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RenderError("vertices must contain real numeric values") from exc
    _reject(not np.isfinite(points).all(), "vertices must be finite")
    return points


def _quads(value: Any, vertex_count: int) -> np.ndarray:
    if isinstance(value, (list, tuple)):
        for row in value:
            if isinstance(row, (list, tuple)) and any(
                    isinstance(item, (bool, np.bool_)) for item in row):
                raise RenderError("quad indices must be integers, not booleans")
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise RenderError("quads must be an integer N x 4 sequence") from exc
    _reject(array.ndim != 2 or array.shape[1] != 4 or array.shape[0] == 0,
            "quads must be a non-empty N x 4 sequence")
    _reject(np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.integer)
            or np.issubdtype(array.dtype, np.bool_),
            "quad indices must be integers")
    indices = np.asarray(array, dtype=np.int64)
    _reject(bool((indices < 0).any()) or bool((indices >= vertex_count).any()),
            "quad index is outside vertices")
    _reject(any(len(set(row.tolist())) != 4 for row in indices),
            "a quad must reference four distinct vertices")
    return indices


def _aabb(value: Any, points: np.ndarray, *, allow_crop: bool) -> tuple[np.ndarray, np.ndarray]:
    if value is None:
        low = points.min(axis=0)
        high = points.max(axis=0)
    elif isinstance(value, dict):
        _reject(set(value) != {"min", "max"},
                "bounds mapping must contain only min and max")
        low = value["min"]
        high = value["max"]
    else:
        try:
            array = np.asarray(value)
        except (TypeError, ValueError) as exc:
            raise RenderError("bounds must be ((xmin, ymin, zmin), (xmax, ymax, zmax))") from exc
        _reject(array.shape != (2, 3),
                "bounds must be ((xmin, ymin, zmin), (xmax, ymax, zmax))")
        low, high = array[0], array[1]
    try:
        low = np.asarray(low, dtype=np.float64)
        high = np.asarray(high, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RenderError("bounds must contain finite numeric values") from exc
    _reject(low.shape != (3,) or high.shape != (3,),
            "bounds must contain two vector3 values")
    _reject(not np.isfinite(low).all() or not np.isfinite(high).all(),
            "bounds must be finite")
    _reject(bool((high < low).any()), "bounds max must not be below bounds min")
    if not allow_crop:
        _reject(bool((points < low).any()) or bool((points > high).any()),
                "vertices must lie inside bounds; pass allow_crop=True for a camera crop")
    return low, high


def _overlay(value: Any, index: int) -> dict[str, Any]:
    _reject(not isinstance(value, dict), f"overlay {index} must be a mapping")
    _reject(set(value) - {"start", "end", "color", "label"}
            or not {"start", "end", "color"}.issubset(value),
            f"overlay {index} has invalid fields")
    try:
        start = np.asarray(value["start"], dtype=np.float64)
        end = np.asarray(value["end"], dtype=np.float64)
        color = np.asarray(value["color"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise RenderError(f"overlay {index} has invalid values") from exc
    _reject(start.shape != (3,) or end.shape != (3,),
            f"overlay {index} endpoints must be vector3 values")
    _reject(not np.isfinite(start).all() or not np.isfinite(end).all(),
            f"overlay {index} endpoints must be finite")
    _reject(color.shape != (3,) or np.iscomplexobj(color)
            or not np.issubdtype(color.dtype, np.integer),
            f"overlay {index} color must contain three integers")
    color = np.asarray(color, dtype=np.int64)
    _reject(bool((color < 0).any()) or bool((color > 255).any()),
            f"overlay {index} color must be in 0..255")
    label = value.get("label", "")
    _reject(not isinstance(label, str), f"overlay {index} label must be text")
    return {"start": start, "end": end, "color": tuple(int(item) for item in color),
            "label": label}


def _validated_inputs(vertices: Any, quads: Any, bounds: Any, overlays: Any, *, allow_crop: bool) -> tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[dict[str, Any], ...]]:
    points = _vertices(vertices)
    faces = _quads(quads, len(points))
    low, high = _aabb(bounds, points, allow_crop=allow_crop)
    if overlays is None:
        checked_overlays: tuple[dict[str, Any], ...] = ()
    else:
        _reject(not isinstance(overlays, (list, tuple)),
                "overlays must be a list or tuple of segment mappings")
        checked_overlays = tuple(_overlay(item, index)
                                 for index, item in enumerate(overlays))
    return points, faces, low, high, checked_overlays


def _camera(name: str, view: tuple[float, float, float]) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
    depth = np.asarray(view, dtype=np.float64)
    depth /= np.linalg.norm(depth)
    world_up = np.array((0.0, 1.0, 0.0), dtype=np.float64)
    right = np.cross(world_up, depth)
    right /= np.linalg.norm(right)
    up = np.cross(depth, right)
    up /= np.linalg.norm(up)
    return name, right, up, depth


CAMERAS = (
    _camera("front", (0.0, 0.0, 1.0)),
    _camera("side", (1.0, 0.0, 0.0)),
    _camera("rear-three-quarter", (1.0, 0.2, -1.0)),
)
UNDERSIDE_CAMERA = _camera("underside", (0.0, -1.0, 0.4))


def _corners(low: np.ndarray, high: np.ndarray) -> np.ndarray:
    return np.asarray([(x, y, z) for x in (low[0], high[0])
                       for y in (low[1], high[1])
                       for z in (low[2], high[2])], dtype=np.float64)


def _extent(corners: np.ndarray, cameras: tuple[tuple[str, np.ndarray, np.ndarray, np.ndarray], ...]) -> float:
    midpoint = (corners[0] + corners[-1]) * 0.5
    relative = corners - midpoint
    extent = 0.0
    for _, right, up, _ in cameras:
        extent = max(extent, float(np.abs(relative @ right).max()),
                     float(np.abs(relative @ up).max()))
    _reject(not math.isfinite(extent) or extent <= 0.0,
            "bounds do not produce a positive camera extent")
    return extent


def _project(points: np.ndarray, midpoint: np.ndarray,
             camera: tuple[str, np.ndarray, np.ndarray, np.ndarray],
             scale: float, origin: tuple[float, float],
             viewport: tuple[int, int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, right, up, depth = camera
    relative = points - midpoint
    u = relative @ right
    v = relative @ up
    z = relative @ depth
    x0, y0, width, height = viewport
    centre_x = x0 + width * 0.5
    centre_y = y0 + height * 0.5
    projected = (centre_x + scale * u, centre_y - scale * v, z)
    _reject(not all(np.isfinite(item).all() for item in projected),
            "camera projection is non-finite")
    return projected


def _triangle_colour(points: np.ndarray, triangle: tuple[int, int, int]) -> tuple[int, int, int]:
    a, b, c = points[list(triangle)]
    normal = np.cross(b - a, c - a)
    length = float(np.linalg.norm(normal))
    _reject(not math.isfinite(length) or length <= 1.0e-15,
            "quad contains a degenerate triangle")
    normal /= length
    key = max(0.0, float(np.dot(normal, KEY_LIGHT_DIRECTION)))
    fill = max(0.0, float(np.dot(normal, FILL_LIGHT_DIRECTION)))
    illumination = AMBIENT + KEY_DIFFUSE * key + FILL_DIFFUSE * fill
    colour = np.clip(np.rint(CLAY * illumination), 0.0, 255.0).astype(np.uint8)
    return tuple(int(item) for item in colour)


def _rasterize(pixel_array: np.ndarray, points: np.ndarray, faces: np.ndarray,
               midpoint: np.ndarray, camera: tuple[str, np.ndarray, np.ndarray, np.ndarray],
               scale: float, viewport: tuple[int, int, int, int]) -> int:
    x0, y0, width, height = viewport
    screen_x, screen_y, depth = _project(points, midpoint, camera, scale, (x0, y0), viewport)
    z_buffer = np.full((height, width), -np.inf, dtype=np.float64)
    visible_pixels = 0
    # Keep quad split order grouped by quad, so equal-depth ties are stable.
    triangles = [item for pair in zip(
        ((int(face[0]), int(face[1]), int(face[2])) for face in faces),
        ((int(face[0]), int(face[2]), int(face[3])) for face in faces))
                 for item in pair]
    for triangle in triangles:
        ia, ib, ic = triangle
        ax, ay, az = float(screen_x[ia]), float(screen_y[ia]), float(depth[ia])
        bx, by, bz = float(screen_x[ib]), float(screen_y[ib]), float(depth[ib])
        cx, cy, cz = float(screen_x[ic]), float(screen_y[ic]), float(depth[ic])
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        _reject(not math.isfinite(denominator), "triangle projection is non-finite")
        if abs(denominator) <= 1.0e-15:
            # A valid 3D face may be edge-on in one orthographic camera.
            continue
        left = max(x0, int(math.ceil(min(ax, bx, cx) - PIXEL_CENTER)))
        right = min(x0 + width - 1, int(math.floor(max(ax, bx, cx) - PIXEL_CENTER)))
        top = max(y0, int(math.ceil(min(ay, by, cy) - PIXEL_CENTER)))
        bottom = min(y0 + height - 1, int(math.floor(max(ay, by, cy) - PIXEL_CENTER)))
        if left > right or top > bottom:
            continue
        columns = np.arange(left, right + 1, dtype=np.float64) + PIXEL_CENTER
        rows = np.arange(top, bottom + 1, dtype=np.float64) + PIXEL_CENTER
        px, py = np.meshgrid(columns, rows)
        w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
        w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -EPSILON) & (w1 >= -EPSILON) & (w2 >= -EPSILON)
        if not inside.any():
            continue
        sample_depth = w0 * az + w1 * bz + w2 * cz
        local_z = z_buffer[top - y0:bottom - y0 + 1, left - x0:right - x0 + 1]
        wins = inside & (sample_depth > local_z)
        if not wins.any():
            continue
        colour = _triangle_colour(points, triangle)
        local_z[wins] = sample_depth[wins]
        pixel_array[top:bottom + 1, left:right + 1][wins] = colour
        visible_pixels += int(wins.sum())
    return visible_pixels


def _viewports(view_count: int, canvas_size: tuple[int, int]) -> tuple[tuple[int, int, int, int], ...]:
    canvas_width, canvas_height = canvas_size
    top = 40
    bottom = 30
    panel_height = canvas_height - top - bottom
    widths = [canvas_width // view_count] * view_count
    for index in range(canvas_width % view_count):
        widths[index] += 1
    viewports = []
    left = 0
    for width in widths:
        viewports.append((left, top, width, panel_height))
        left += width
    return tuple(viewports)


def _draw_text(image: Image.Image, title: str, status: str,
               view_names: tuple[str, ...], viewports: tuple[tuple[int, int, int, int], ...],
               overlays: tuple[dict[str, Any], ...] = ()) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 35), fill=(32, 34, 37))
    draw.text((14, 9), title, fill=(248, 248, 248))
    status_text = f"{status}  |  VISUAL PENDING"
    status_width = draw.textbbox((0, 0), status_text)[2]
    draw.text((image.width - status_width - 14, 9), status_text, fill=(248, 221, 135))
    for index, (name, (left, top, width, height)) in enumerate(zip(view_names, viewports)):
        if index:
            draw.line((left, top, left, top + height), fill=(206, 204, 198), width=1)
        label_width = draw.textbbox((0, 0), name)[2]
        draw.text((left + (width - label_width) // 2, image.height - 23), name,
                  fill=(65, 66, 68))
    if overlays:
        x = 14
        y = image.height - 24
        for item in overlays:
            label = item["label"] or "overlay"
            text = f"  {label}"
            draw.rectangle((x, y + 4, x + 8, y + 12), fill=item["color"])
            draw.text((x + 10, y), text, fill=(65, 66, 68))
            x += draw.textbbox((0, 0), text)[2] + 18
            if x >= image.width - 100:
                break


def _draw_overlays(image: Image.Image, overlays: tuple[dict[str, Any], ...], midpoint: np.ndarray,
                   scale: float, cameras: tuple[tuple[str, np.ndarray, np.ndarray, np.ndarray], ...],
                   viewports: tuple[tuple[int, int, int, int], ...]) -> None:
    draw = ImageDraw.Draw(image)
    for camera, viewport in zip(cameras, viewports):
        for item in overlays:
            projected_start = _project(item["start"][None, :], midpoint, camera, scale, (0, 0), viewport)
            projected_end = _project(item["end"][None, :], midpoint, camera, scale, (0, 0), viewport)
            start = (int(round(projected_start[0][0])), int(round(projected_start[1][0])))
            end = (int(round(projected_end[0][0])), int(round(projected_end[1][0])))
            draw.line((*start, *end), fill=item["color"], width=2)
            radius = 3
            draw.ellipse((start[0] - radius, start[1] - radius,
                          start[0] + radius, start[1] + radius), fill=item["color"])
            draw.ellipse((end[0] - radius, end[1] - radius,
                          end[0] + radius, end[1] + radius), fill=item["color"])


def _save_png(image: Image.Image, output_path: Path) -> None:
    _reject(output_path.suffix.lower() != ".png", "output_path must end in .png")
    try:
        with output_path.open("wb") as handle:
            image.save(handle, format="PNG", compress_level=9, optimize=False)
    except OSError as exc:
        raise RenderError(f"unable to write {output_path}") from exc


def _render_image(points: np.ndarray, faces: np.ndarray, low: np.ndarray, high: np.ndarray,
                  title: str, status: str, cameras: tuple[tuple[str, np.ndarray, np.ndarray, np.ndarray], ...],
                  overlays: tuple[dict[str, Any], ...], canvas_size: tuple[int, int]) -> tuple[Image.Image, int]:
    pixel_array = np.empty((canvas_size[1], canvas_size[0], 3), dtype=np.uint8)
    pixel_array[:, :] = BACKGROUND
    midpoint = (low + high) * 0.5
    extent = _extent(_corners(low, high), cameras)
    top = 40
    bottom = 30
    panel_height = canvas_size[1] - top - bottom
    panel_width = canvas_size[0] // len(cameras)
    usable = min(panel_width - 36, panel_height - 24)
    scale = usable / (2.0 * extent)
    viewports = _viewports(len(cameras), canvas_size)
    visible_pixels = 0
    for camera, viewport in zip(cameras, viewports):
        visible_pixels += _rasterize(pixel_array, points, faces, midpoint, camera, scale, viewport)
    image = Image.fromarray(pixel_array, mode="RGB")
    _draw_text(image, title, status, tuple(camera[0] for camera in cameras), viewports, overlays)
    if overlays:
        _draw_overlays(image, overlays, midpoint, scale, cameras, viewports)
    return image, visible_pixels


def _underside_path(output_path: Path) -> Path:
    suffix = output_path.suffix or ".png"
    return output_path.with_name(f"{output_path.stem}-underside{suffix}")


def render_views(vertices: Any, quads: Any, output_path: str | Path, title: str, status: str,
                bounds: Any = None, overlays: Any = None, *, underside: bool = False,
                allow_crop: bool = False) -> dict[str, Any]:
    """Render matched direct views and return stable, non-acceptance metadata.

    ``bounds`` is an optional world AABB, represented as ``(min_xyz, max_xyz)``
    or ``{"min": min_xyz, "max": max_xyz}``.  Supplying it fixes the camera
    frame for comparisons.  ``allow_crop=True`` changes only camera framing;
    the complete input vertices/quads still go through validation and raster
    clipping.  ``underside=True`` writes a separate sibling PNG; the primary
    artifact remains the fixed 1600x550 three-view capture.
    """
    _reject(not isinstance(title, str) or not title.strip(), "title must be non-empty text")
    _reject(not isinstance(status, str) or not status.strip(), "status must be non-empty text")
    _reject(not isinstance(underside, bool), "underside must be a boolean")
    _reject(not isinstance(allow_crop, bool), "allow_crop must be a boolean")
    points, faces, low, high, checked_overlays = _validated_inputs(
        vertices, quads, bounds, overlays, allow_crop=allow_crop)
    try:
        path = Path(output_path)
    except TypeError as exc:
        raise RenderError("output_path must be a filesystem path") from exc
    _reject(path.suffix.lower() != ".png", "output_path must end in .png")
    _reject(path.exists() and path.is_dir(), "output_path must not be a directory")
    cameras = CAMERAS
    image, visible_pixels = _render_image(points, faces, low, high, title, status,
                                          cameras, (), CANVAS_SIZE)
    _save_png(image, path)
    underside_path: Path | None = None
    underside_visible = None
    diagnostic_path: Path | None = None
    if checked_overlays:
        diagnostic_path = path.with_name(f"{path.stem}-diagnostic.png")
        diagnostic_image, _ = _render_image(
            points, faces, low, high, title, status, cameras, checked_overlays, CANVAS_SIZE)
        _save_png(diagnostic_image, diagnostic_path)
    if underside:
        underside_path = _underside_path(path)
        underside_image, underside_visible = _render_image(
            points, faces, low, high, title, status, (UNDERSIDE_CAMERA,), (),
            CANVAS_SIZE)
        _save_png(underside_image, underside_path)
    return {
        "output_path": str(path),
        "diagnostic_path": str(diagnostic_path) if diagnostic_path else None,
        "underside_path": str(underside_path) if underside_path else None,
        "width": CANVAS_SIZE[0],
        "height": CANVAS_SIZE[1],
        "views": [camera[0] for camera in cameras],
        "triangle_count": len(faces) * 2,
        "visible_pixels": visible_pixels,
        "underside_visible_pixels": underside_visible,
        "bounds": [low.tolist(), high.tolist()],
        "allow_crop": allow_crop,
        "status": status,
        "visual_status": "pending",
        "overlay_count": len(checked_overlays),
        "lighting": {
            "ambient": AMBIENT,
            "key_direction": KEY_LIGHT_DIRECTION.tolist(),
            "key_weight": KEY_DIFFUSE,
            "fill_direction": FILL_LIGHT_DIRECTION.tolist(),
            "fill_weight": FILL_DIFFUSE,
        },
    }


__all__ = ["RenderError", "render_views"]

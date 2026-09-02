"""Bounded, dependency-free geometry checks for the root-complex trial."""

from collections.abc import Mapping

import numpy as np


REQUIRED_LOOPS = ("neck", "left_arm", "right_arm", "left_thigh", "right_thigh")
INTERSECTION_TOLERANCE = 1e-10
MAX_TRIANGLES = 3072
MAX_CANDIDATES = 250000
CLEARANCE_THRESHOLDS = {"neck": .030, "axilla_left": .025, "axilla_right": .025,
                        "groin": .020, "medial_thigh": .025}


def _vertices(raw, scale):
    if isinstance(scale, (bool, np.bool_)):
        raise ValueError("scale must be finite and positive")
    try:
        scale = float(scale)
    except (TypeError, ValueError) as exc:
        raise ValueError("scale must be finite and positive") from exc
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be finite and positive")
    try:
        value = np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("vertices must be a finite N x 3 array") from exc
    if value.ndim != 2 or value.shape[1:] != (3,) or not np.isfinite(value).all():
        raise ValueError("vertices must be a finite N x 3 array")
    value = value / float(scale)
    if not np.isfinite(value).all():
        raise ValueError("vertices must be finite after scaling")
    return value


def _triangles(raw, count):
    try:
        value = np.asarray(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("triangles must be an integer M x 3 array") from exc
    if value.ndim != 2 or value.shape[1:] != (3,) or value.dtype.kind not in "iu":
        raise ValueError("triangles must be an integer M x 3 array")
    if len(value) > MAX_TRIANGLES:
        raise ValueError(f"triangle cap exceeded: {len(value)} > {MAX_TRIANGLES}")
    if ((value < 0) | (value >= count)).any():
        raise ValueError("triangle index out of range")
    if any(len(set(map(int, row))) != 3 for row in value):
        raise ValueError("triangle has repeated vertex index")
    return value.astype(np.int64, copy=False)


def _axes(a, b):
    na = np.cross(a[1] - a[0], a[2] - a[0])
    nb = np.cross(b[1] - b[0], b[2] - b[0])
    if not np.linalg.norm(na) > 0 or not np.linalg.norm(nb) > 0:
        raise ValueError("triangle normal must be nonzero")
    ea = (a[1] - a[0], a[2] - a[1], a[0] - a[2])
    eb = (b[1] - b[0], b[2] - b[1], b[0] - b[2])
    result = [na, nb]
    result.extend(np.cross(x, y) for x in ea for y in eb)
    result.extend(np.cross(na, edge) for edge in ea)
    result.extend(np.cross(nb, edge) for edge in eb)
    return result


def _disjoint(a, b, tolerance):
    for index, axis in enumerate(_axes(a, b)):
        length = np.linalg.norm(axis)
        if not np.isfinite(axis).all() or not np.isfinite(length):
            raise ValueError("SAT axis must be finite")
        if index >= 2 and length <= np.finfo(float).eps:
            continue
        axis = axis / length
        if not np.isfinite(axis).all():
            raise ValueError("SAT axis must be finite")
        left, right = a @ axis, b @ axis
        if not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError("SAT projections must be finite")
        if left.max() < right.min() - tolerance or right.max() < left.min() - tolerance:
            return True
    return False


def intersecting_triangle_pairs(vertices, triangles, scale):
    """Return stable non-adjacent triangle intersection pairs."""
    points = _vertices(vertices, scale)
    faces = _triangles(triangles, len(points))
    if not len(faces):
        return ()
    corners = points[faces]
    bounds = np.concatenate((corners.min(axis=1), corners.max(axis=1)), axis=1)
    order = sorted(range(len(faces)), key=lambda i: (bounds[i, 0], i))
    active, candidates = [], []
    for current in order:
        low_x = bounds[current, 0]
        active = [i for i in active if bounds[i, 3] >= low_x - INTERSECTION_TOLERANCE]
        for other in active:
            if bounds[other, 4] < bounds[current, 1] - INTERSECTION_TOLERANCE:
                continue
            if bounds[current, 4] < bounds[other, 1] - INTERSECTION_TOLERANCE:
                continue
            if bounds[other, 5] < bounds[current, 2] - INTERSECTION_TOLERANCE:
                continue
            if bounds[current, 5] < bounds[other, 2] - INTERSECTION_TOLERANCE:
                continue
            if set(faces[other]) & set(faces[current]):
                continue
            candidates.append(tuple(sorted((other, current))))
            if len(candidates) > MAX_CANDIDATES:
                raise ValueError(f"AABB candidate cap exceeded: >{MAX_CANDIDATES}")
        active.append(current)
    hits = [(i, j) for i, j in candidates if not _disjoint(corners[i], corners[j], INTERSECTION_TOLERANCE)]
    return tuple(sorted(hits))


def validate_triangle_intersections(vertices, triangles, scale):
    """Raise a concise error for non-adjacent contacts or intersections."""
    pairs = intersecting_triangle_pairs(vertices, triangles, scale)
    if pairs:
        raise ValueError(f"{len(pairs)} non-adjacent triangle intersections; first pair {pairs[0]}")
    return pairs


def _frame(raw):
    try:
        axes = [np.asarray(raw[name], dtype=float) for name in ("L", "U", "F")]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("body axes L, U, and F are required") from exc
    if any(axis.shape != (3,) or not np.isfinite(axis).all() for axis in axes):
        raise ValueError("body axes must be finite 3-vectors")
    lengths = [np.linalg.norm(axis) for axis in axes]
    if any(not length > 0 for length in lengths):
        raise ValueError("body axes must be nonzero")
    axes = [axis / length for axis, length in zip(axes, lengths)]
    if any(abs(np.dot(axes[i], axes[j])) > 1e-8 for i in range(3) for j in range(i)):
        raise ValueError("body axes must be orthogonal")
    if np.dot(np.cross(axes[0], axes[1]), axes[2]) <= 1 - 1e-8:
        raise ValueError("body axes must be right-handed")
    return axes


def _loops(raw, vertex_count):
    if not isinstance(raw, Mapping) or set(raw) != set(REQUIRED_LOOPS):
        raise ValueError("exact boundary loops neck, arms, and thighs are required")
    result = {}
    for name in REQUIRED_LOOPS:
        try:
            indices = tuple(raw[name])
            if any(isinstance(index, (bool, np.bool_)) or
                   not isinstance(index, (int, np.integer)) for index in indices):
                raise TypeError
            loop = tuple(int(index) for index in indices)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} boundary loop must contain integer indices") from exc
        if len(loop) < 3 or len(set(loop)) != len(loop):
            raise ValueError(f"{name} boundary loop must be simple")
        if any(index < 0 or index >= vertex_count for index in loop):
            raise ValueError(f"{name} boundary loop index out of range")
        result[name] = loop
    return result


def boundary_clearance_ratios(vertices, boundary_loops, axes, scale):
    """Return named, scale-relative boundary clearances without aggregation."""
    points = _vertices(vertices, scale)
    loops = _loops(boundary_loops, len(points))
    L, U, F = _frame(axes)
    def span(name, axis):
        values = points[list(loops[name])] @ axis
        return float(values.max() - values.min())
    values = {
        "neck": min(span("neck", L), span("neck", F)),
        "axilla_left": min(span("left_arm", U), span("left_arm", F)),
        "axilla_right": min(span("right_arm", U), span("right_arm", F)),
    }
    left_samples = points[list(loops["left_thigh"])]
    right_samples = points[list(loops["right_thigh"])]
    left_lateral = left_samples @ L
    right_lateral = right_samples @ L
    values["groin"] = float(right_lateral.min() - left_lateral.max())
    values["medial_thigh"] = float(((right_samples[:, None, :] - left_samples[None, :, :]) @ L).min())
    if not all(np.isfinite(value) for value in values.values()):
        raise ValueError("boundary clearances must be finite")
    return values


def validate_boundary_clearances(vertices, boundary_loops, axes, scale):
    """Raise when any named negative-space clearance is below its threshold."""
    values = boundary_clearance_ratios(vertices, boundary_loops, axes, scale)
    for name, threshold in CLEARANCE_THRESHOLDS.items():
        if values[name] < threshold:
            raise ValueError(f"{name} clearance {values[name]:.6g} < {threshold:.3f}")
    return values


__all__ = ["CLEARANCE_THRESHOLDS", "boundary_clearance_ratios", "intersecting_triangle_pairs",
           "validate_boundary_clearances", "validate_triangle_intersections"]

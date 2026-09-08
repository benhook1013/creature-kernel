"""Horizontal actual-surface section diagnostics; not a mesh gate or solid test."""
from __future__ import annotations
import math
from collections import Counter
from typing import Any, Sequence

_BOUNDARY_TOLERANCE = 1.0e-6
_SLICE_OFFSET = 1.0e-7
_PLANE_TOLERANCE = 1.0e-12
_POINT_MERGE_TOLERANCE = 1.0e-9
_LIMIT = "Horizontal actual-surface cross-section only; open ports are not capped. This is not a global solid-volume or containment claim."

def _finite(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False

def _vector(value: Any) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError("vertex/point must be a finite 3-vector")
    try:
        values = list(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("vertex/point must be a finite 3-vector") from exc
    if len(values) != 3 or any(not _finite(item) for item in values):
        raise ValueError("vertex/point must be a finite 3-vector")
    return tuple(float(item) for item in values)  # type: ignore[return-value]

def _validated(vertices: Any, quads: Any, scale: Any) -> tuple[Any, ...]:
    if not _finite(scale) or float(scale) <= 0:
        raise ValueError("scale must be finite and positive")
    try:
        raw_vertices, raw_quads = list(vertices), list(quads)
    except (TypeError, ValueError) as exc:
        raise ValueError("vertices and quads must be sequences") from exc
    checked_vertices = tuple(_vector(value) for value in raw_vertices)
    if not checked_vertices:
        raise ValueError("vertices must not be empty")
    checked_quads = []
    for face_index, value in enumerate(raw_quads):
        try:
            face = list(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"quads[{face_index}] must have four indices") from exc
        if len(face) != 4 or any(isinstance(index, bool) or not isinstance(index, int) for index in face):
            raise ValueError(f"quads[{face_index}] must have four integer indices")
        if len(set(face)) != 4 or any(index < 0 or index >= len(checked_vertices) for index in face):
            raise ValueError(f"quads[{face_index}] contains an invalid index")
        checked_quads.append(tuple(face))
    if not checked_quads:
        raise ValueError("quads must not be empty")
    return checked_vertices, tuple(checked_quads), float(scale)

def _invalid(message: str) -> dict[str, Any]:
    return {"status": "INVALID_INPUT", "classification": "invalid_input", "error": message, "interpretation_limit": _LIMIT}

def _point_id(point: tuple[float, float], points: list[tuple[float, float]], buckets: dict[tuple[int, int], list[int]], tolerance: float) -> int:
    cell = (math.floor(point[0] / tolerance), math.floor(point[1] / tolerance))
    best = None
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            for index in buckets.get((cell[0] + dx, cell[1] + dz), ()):
                distance = math.hypot(point[0] - points[index][0], point[1] - points[index][1])
                if distance <= tolerance and (best is None or (distance, index) < best):
                    best = (distance, index)
    if best is not None:
        return best[1]
    index = len(points)
    points.append(point)
    buckets.setdefault(cell, []).append(index)
    return index

def _section_at(vertices: Sequence[tuple[float, float, float]], quads: Sequence[tuple[int, int, int, int]], y: float, scale: float) -> dict[str, Any]:
    plane_tolerance = max(_PLANE_TOLERANCE * scale, 1.0e-15)
    merge_tolerance = max(_POINT_MERGE_TOLERANCE * scale, 1.0e-15)
    points: list[tuple[float, float]] = []
    buckets: dict[tuple[int, int], list[int]] = {}
    segments: set[tuple[int, int]] = set()
    generated = 0
    plane_vertices: set[int] = set()
    coplanar_triangles = 0
    coplanar_edges: set[tuple[int, int]] = set()
    vertex_touches: set[int] = set()
    def point_on(index: int) -> tuple[float, float]:
        return vertices[index][0], vertices[index][2]
    def crossing(first: int, second: int, first_distance: float, second_distance: float) -> tuple[float, float]:
        fraction = first_distance / (first_distance - second_distance)
        a, b = vertices[first], vertices[second]
        return a[0] + fraction * (b[0] - a[0]), a[2] + fraction * (b[2] - a[2])
    def add_segment(first_point: tuple[float, float], second_point: tuple[float, float]) -> None:
        nonlocal generated
        first = _point_id(first_point, points, buckets, merge_tolerance)
        second = _point_id(second_point, points, buckets, merge_tolerance)
        if first != second:
            generated += 1
            segments.add(tuple(sorted((first, second))))
    for quad in quads:
        for triangle in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
            distances = tuple(vertices[index][1] - y for index in triangle)
            on = tuple(abs(distance) <= plane_tolerance for distance in distances)
            plane_vertices.update(triangle[index] for index, is_on in enumerate(on) if is_on)
            coplanar_edges.update(tuple(sorted((triangle[first], triangle[second]))) for first, second in ((0, 1), (1, 2), (2, 0)) if on[first] and on[second])
            if all(on):
                coplanar_triangles += 1
            elif sum(on) == 2:
                on_points = [point_on(triangle[index]) for index, is_on in enumerate(on) if is_on]
                add_segment(on_points[0], on_points[1])
            elif sum(on) == 1:
                on_index = on.index(True)
                off = [index for index, is_on in enumerate(on) if not is_on]
                if distances[off[0]] * distances[off[1]] < 0:
                    add_segment(point_on(triangle[on_index]), crossing(triangle[off[0]], triangle[off[1]], distances[off[0]], distances[off[1]]))
                else:
                    vertex_touches.add(triangle[on_index])
            else:
                crossings = [crossing(triangle[first], triangle[second], distances[first], distances[second]) for first, second in ((0, 1), (1, 2), (2, 0)) if distances[first] * distances[second] < 0]
                if len(crossings) == 2:
                    add_segment(crossings[0], crossings[1])
    adjacency = [set() for _ in points]
    for first, second in segments:
        adjacency[first].add(second)
        adjacency[second].add(first)
    open_nodes = [index for index, neighbours in enumerate(adjacency) if len(neighbours) != 2]
    closed_graph = bool(segments) and not open_nodes
    contours: list[list[list[float]]] = []
    if closed_graph:
        unseen = set(range(len(points)))
        while unseen:
            start = min(unseen)
            current, previous, contour = start, None, []
            while True:
                contour.append([points[current][0], points[current][1]])
                unseen.discard(current)
                neighbours = sorted(adjacency[current])
                next_node = neighbours[0] if previous is None or neighbours[0] != previous else neighbours[1]
                previous, current = current, next_node
                if current == start:
                    break
            contours.append(contour)
    return {"points": points, "segments": [(points[a], points[b]) for a, b in sorted(segments)], "generated_segment_count": generated, "deduplicated_segment_count": len(segments), "adjacency": adjacency, "open_nodes": open_nodes, "closed_graph": closed_graph, "contours": contours, "plane_vertices": plane_vertices, "coplanar_triangles": coplanar_triangles, "coplanar_edges": coplanar_edges, "vertex_touches": vertex_touches, "merge_tolerance": merge_tolerance}

def _orientation(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
def _point_segment_distance(point: Sequence[float], first: Sequence[float], second: Sequence[float]) -> float:
    dx, dz = second[0] - first[0], second[1] - first[1]
    denominator = dx * dx + dz * dz
    if denominator == 0:
        return math.hypot(point[0] - first[0], point[1] - first[1])
    fraction = max(0.0, min(1.0, ((point[0] - first[0]) * dx + (point[1] - first[1]) * dz) / denominator))
    return math.hypot(point[0] - first[0] - fraction * dx, point[1] - first[1] - fraction * dz)
def _signed_distance(a: Sequence[float], b: Sequence[float], p: Sequence[float]) -> float:
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    return _orientation(a, b, p) / length if length else math.inf
def _on_segment(a: Sequence[float], b: Sequence[float], p: Sequence[float], tolerance: float) -> bool:
    return _point_segment_distance(p, a, b) <= tolerance
def _intersects(a: Sequence[float], b: Sequence[float], c: Sequence[float], d: Sequence[float], tolerance: float) -> bool:
    values = (_signed_distance(a, b, c), _signed_distance(a, b, d), _signed_distance(c, d, a), _signed_distance(c, d, b))
    opposite = ((values[0] > tolerance and values[1] < -tolerance) or (values[1] > tolerance and values[0] < -tolerance)) and ((values[2] > tolerance and values[3] < -tolerance) or (values[3] > tolerance and values[2] < -tolerance))
    return opposite or any(_on_segment(first, second, point, tolerance) for first, second, point in ((a, b, c), (a, b, d), (c, d, a), (c, d, b)))
def _self_intersections(contours: Sequence[Sequence[Sequence[float]]], tolerance: float) -> int:
    edges = [(ci, ei, first, contour[(ei + 1) % len(contour)]) for ci, contour in enumerate(contours) for ei, first in enumerate(contour)]
    count = 0
    for index, (ca, ea, a, b) in enumerate(edges):
        for cb, eb, c, d in edges[index + 1:]:
            adjacent = ca == cb and ((ea + 1) % len(contours[ca]) == eb or (eb + 1) % len(contours[cb]) == ea)
            if not adjacent and _intersects(a, b, c, d, tolerance):
                count += 1
    return count
def _bounds(contours: Sequence[Sequence[Sequence[float]]], points: Sequence[tuple[float, float]]) -> dict[str, float] | None:
    values = [point for contour in contours for point in contour] or [[point[0], point[1]] for point in points]
    if not values:
        return None
    xs, zs = [point[0] for point in values], [point[1] for point in values]
    return {"min_x": min(xs), "max_x": max(xs), "min_z": min(zs), "max_z": max(zs)}

def _summary(raw: dict[str, Any], y: float, scale: float, y_range: tuple[float, float]) -> dict[str, Any]:
    if raw["open_nodes"]:
        kind = "INDETERMINATE_OPEN_SECTION"
    elif raw["self_intersection_count"]:
        kind = "INDETERMINATE_SELF_INTERSECTION"
    elif raw["closed_graph"]:
        kind = "CLOSED_SECTION"
    else:
        kind = "EMPTY_SECTION"
    exact = bool(raw["plane_vertices"] or raw["coplanar_triangles"])
    diagnostics = {"surface_y_range": [y_range[0], y_range[1]], "plane_tolerance": max(_PLANE_TOLERANCE * scale, 1.0e-15), "point_merge_tolerance": raw["merge_tolerance"], "generated_segment_count": raw["generated_segment_count"], "deduplicated_segment_count": raw["deduplicated_segment_count"], "node_count": len(raw["points"]), "degree_histogram": {str(key): value for key, value in sorted(Counter(len(row) for row in raw["adjacency"]).items())}, "open_node_count": len(raw["open_nodes"]), "exact_coplanarity": exact, "plane_vertex_count": len(raw["plane_vertices"]), "coplanar_triangle_count": raw["coplanar_triangles"], "coplanar_edge_count": len(raw["coplanar_edges"]), "vertex_touch_count": len(raw["vertex_touches"]), "section_self_intersection_count": raw["self_intersection_count"], "closed_graph": raw["closed_graph"]}
    closed_count = len(raw["contours"]) if raw["closed_graph"] else 0
    diagnostics["segment_count"] = raw["deduplicated_segment_count"]
    diagnostics["closed_contour_count"] = closed_count
    return {"query_y": y, "scale": scale, "status": kind, "classification": kind, "section_classification": kind, "contours": raw["contours"], "closed_contours": raw["contours"] if raw["closed_graph"] else [], "closed_count": closed_count, "closed_contour_count": closed_count, "bounds": _bounds(raw["contours"] if raw["closed_graph"] else (), raw["points"]), "diagnostics": diagnostics, "ambiguous": False, "usable": kind == "CLOSED_SECTION" and not raw["self_intersection_count"], "interpretation_limit": _LIMIT}

def _inspect_valid(vertices: Any, quads: Any, y: Any, scale: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        checked_vertices, checked_quads, checked_scale = _validated(vertices, quads, scale)
        if not _finite(y):
            raise ValueError("query y must be finite")
        query_y = float(y)
    except ValueError as exc:
        return _invalid(str(exc)), None
    y_values = [point[1] for point in checked_vertices]
    y_range = (min(y_values), max(y_values))
    raw = _section_at(checked_vertices, checked_quads, query_y, checked_scale)
    raw["self_intersection_count"] = _self_intersections(raw["contours"], raw["merge_tolerance"]) if raw["closed_graph"] else 0
    result = _summary(raw, query_y, checked_scale, y_range)
    if query_y < y_range[0] or query_y > y_range[1]:
        result.update({"status": "OUT_OF_REPRESENTED_RANGE", "classification": "out_of_range", "section_classification": "OUT_OF_REPRESENTED_RANGE", "usable": False})
        result["diagnostics"]["out_of_represented_range"] = True
        return result, raw
    result["diagnostics"]["out_of_represented_range"] = False
    if result["diagnostics"]["exact_coplanarity"]:
        delta = _SLICE_OFFSET * checked_scale
        slices = []
        for offset in (-delta, delta):
            adjacent = _section_at(checked_vertices, checked_quads, query_y + offset, checked_scale)
            adjacent["self_intersection_count"] = _self_intersections(adjacent["contours"], adjacent["merge_tolerance"]) if adjacent["closed_graph"] else 0
            item = _summary(adjacent, query_y + offset, checked_scale, y_range)
            slices.append({"offset": offset, "query_y": query_y + offset, "section_classification": item["section_classification"], "closed_count": item["closed_count"], "bounds": item["bounds"]})
        disagreement = len({(item["section_classification"], item["closed_count"]) for item in slices}) > 1
        result.update({"status": "INDETERMINATE_AMBIGUOUS_SECTION", "classification": "INDETERMINATE_AMBIGUOUS_SECTION", "section_classification": "INDETERMINATE_AMBIGUOUS_SECTION", "ambiguous": True, "usable": False})
        result["diagnostics"].update({"adjacent_slices": slices, "adjacent_slice_disagreement": disagreement, "ambiguity_reason": "exact_plane_contact_with_fixed_adjacent_slices"})
    return result, raw

def inspect_section(vertices: Any, quads: Any, y: Any, scale: Any) -> dict[str, Any]:
    """Return contours, closure/count, bounds, and fail-closed section diagnostics."""
    result, _ = _inspect_valid(vertices, quads, y, scale)
    return result

def _parity(point: Sequence[float], contours: Sequence[Sequence[Sequence[float]]]) -> tuple[int, int]:
    parity = containing = 0
    for contour in contours:
        inside = False
        for index, first in enumerate(contour):
            second = contour[(index + 1) % len(contour)]
            if (first[1] > point[1]) != (second[1] > point[1]) and point[0] < first[0] + (second[0] - first[0]) * (point[1] - first[1]) / (second[1] - first[1]):
                inside = not inside
        if inside:
            parity ^= 1
            containing += 1
    return parity, containing

def evaluate_point(vertices: Any, quads: Any, point: Any, scale: Any) -> dict[str, Any]:
    """Classify a point using one horizontal actual-surface section."""
    try:
        query_point = _vector(point)
    except ValueError as exc:
        return _invalid(str(exc))
    section, raw = _inspect_valid(vertices, quads, query_point[1], scale)
    if raw is None:
        return section
    tolerance = _BOUNDARY_TOLERANCE * float(scale)
    xz = (query_point[0], query_point[2])
    boundary_distance = min((_point_segment_distance(xz, first, second) for first, second in raw["segments"]), default=None)
    bounds = section["bounds"]
    within_bounds = bool(bounds and bounds["min_x"] - tolerance <= xz[0] <= bounds["max_x"] + tolerance and bounds["min_z"] - tolerance <= xz[1] <= bounds["max_z"] + tolerance)
    result = {"point": [query_point[0], query_point[1], query_point[2]], "query_y": query_point[1], "scale": float(scale), "section": section, "parity": None, "inside_contour_count": None, "boundary_distance": boundary_distance, "boundary_tolerance": tolerance, "within_section_bounds": within_bounds, "interpretation_limit": _LIMIT}
    y_min, y_max = section["diagnostics"]["surface_y_range"]
    if query_point[1] < y_min or query_point[1] > y_max:
        result.update({"status": "OUT_OF_REPRESENTED_RANGE", "classification": "out_of_range", "reason": "out_of_represented_range"})
    elif section["ambiguous"]:
        result.update({"status": "INDETERMINATE_AMBIGUOUS_SECTION", "classification": "INDETERMINATE_AMBIGUOUS_SECTION", "reason": "exact_coplanarity_or_adjacent_slice_disagreement"})
    elif raw["open_nodes"]:
        result.update({"status": "INDETERMINATE_OPEN_SECTION", "classification": "INDETERMINATE_OPEN_SECTION", "reason": "section_graph_has_non_degree_two_nodes"})
    elif raw["self_intersection_count"]:
        result.update({"status": "INDETERMINATE_SELF_INTERSECTION", "classification": "INDETERMINATE_SELF_INTERSECTION", "reason": "section_contours_self_intersect"})
    elif not raw["segments"]:
        result.update({"status": "OUTSIDE", "classification": "outside", "reason": "empty_section_within_represented_range", "parity": 0, "inside_contour_count": 0})
    elif boundary_distance is not None and boundary_distance <= tolerance:
        result.update({"status": "ON_SURFACE", "classification": "on_surface", "reason": "within_section_boundary_tolerance"})
    else:
        parity, containing = _parity(xz, raw["contours"])
        result.update({"parity": parity, "inside_contour_count": containing, "status": "INSIDE" if parity else "OUTSIDE", "classification": "inside" if parity else "outside", "reason": "odd_even_closed_contour_parity"})
    return result

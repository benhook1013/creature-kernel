"""Fail-closed technical checks for the pelvis-to-thigh transition experiment.

This module intentionally consumes only the experiment's generic evaluated
surface API.  It does not call the stopped experiment's frozen geometry
validator and it does not construct or repair geometry.

The public entry points are deliberately total:

``check_case(case, levels)``
    Returns a JSON-safe diagnostic report, including malformed-input failures.

``compare_perturbation(base_case, base_levels, case, levels)``
    Checks the declared response of a pre-declared perturbation without
    selecting a profile or changing either input.
"""

from __future__ import annotations

import importlib.util
import itertools
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


_EXPECTED_BASE_VERTICES = 152
_EXPECTED_BASE_QUADS = 136
_LEVELS = (0, 1, 2)
_SCALE_EDGE_FLOOR = 1.0e-7
_SCALE_TRIANGLE_FLOOR = 1.0e-10
_FRAME_TOLERANCE = 1.0e-10
_POSITION_TOLERANCE = 1.0e-6
_RAY_TOLERANCE = 1.0e-6
_EXIT_DIRECTION_TOLERANCE = 1.0e-6
_EXIT_NORMAL_COS = math.cos(math.radians(5.0))
_EXIT_CONORMAL_COS = math.cos(math.radians(25.0))
_LOWER_FOLD_LIMIT_DEGREES = 60.0
_RAY_RADIUS_MIN = 0.6
_RAY_RADIUS_MAX = 2.5
_PELVIS_WIDTH_RESPONSE_FLOOR = 1.0e-4
_INTERSECTION_GROUP_COUNT = 3

_LOWER_OWNER_WORDS = (
    "pelvis",
    "left_hip",
    "right_hip",
    "hip_left",
    "hip_right",
    "abdomen",
    "groin",
    "left_thigh",
    "right_thigh",
    "thigh_left",
    "thigh_right",
    "proximal_thigh",
)
_PELVIS_RAY_OWNER_WORDS = (
    "pelvis",
    "left_hip",
    "right_hip",
    "hip_left",
    "hip_right",
    "groin",
    "left_thigh",
    "right_thigh",
    "thigh_left",
    "thigh_right",
    "proximal_thigh",
)
_EXIT_NAME_WORDS = ("exit", "thigh", "left_hip", "right_hip")


class _CheckInputError(ValueError):
    """An input-shape error which must become a report diagnostic."""


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value: Any) -> bool:
    return _is_number(value) and math.isfinite(float(value))


def _as_sequence(value: Any, label: str) -> list[Any]:
    if isinstance(value, (str, bytes, bytearray)) or value is None:
        raise _CheckInputError(f"{label} must be a sequence")
    try:
        result = list(value)
    except (TypeError, ValueError) as exc:
        raise _CheckInputError(f"{label} must be a sequence") from exc
    return result


def _vector(value: Any, label: str) -> tuple[float, float, float]:
    values = _as_sequence(value, label)
    if len(values) != 3 or any(not _finite(item) for item in values):
        raise _CheckInputError(f"{label} must be a finite 3-vector")
    return (float(values[0]), float(values[1]), float(values[2]))


def _vec_add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a[i]) + float(b[i]) for i in range(3))  # type: ignore[return-value]


def _vec_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a[i]) - float(b[i]) for i in range(3))  # type: ignore[return-value]


def _vec_scale(a: Sequence[float], factor: float) -> tuple[float, float, float]:
    return tuple(float(a[i]) * factor for i in range(3))  # type: ignore[return-value]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _norm(a: Sequence[float]) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Sequence[float], label: str) -> tuple[float, float, float]:
    length = _norm(a)
    if not math.isfinite(length) or length <= 0.0:
        raise _CheckInputError(f"{label} must be finite and nonzero")
    return _vec_scale(a, 1.0 / length)


def _angle_degrees(a: Sequence[float], b: Sequence[float]) -> float:
    ua = _unit(a, "angle vector A")
    ub = _unit(b, "angle vector B")
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(ua, ub)))))


def _angle_radians(a: Sequence[float], b: Sequence[float]) -> float:
    ua = _unit(a, "angle vector A")
    ub = _unit(b, "angle vector B")
    return math.acos(max(-1.0, min(1.0, _dot(ua, ub))))


def _json_safe(value: Any) -> Any:
    """Convert report values to JSON-compatible primitives, fail-closed."""

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if _is_number(value):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return str(value)


def _error(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _case_name(case: Any) -> str:
    if not _is_mapping(case):
        return "<invalid-case>"
    for key in ("name", "case", "id", "case_name"):
        value = case.get(key)
        if isinstance(value, str) and value:
            return value
    return "<unnamed-case>"


def _normalise_levels(levels: Any) -> dict[int, Any]:
    if isinstance(levels, Mapping):
        if isinstance(levels.get("levels"), (list, tuple, Mapping)):
            return _normalise_levels(levels["levels"])
        result: dict[int, Any] = {}
        for level in _LEVELS:
            if level in levels:
                result[level] = levels[level]
            elif str(level) in levels:
                result[level] = levels[str(level)]
        return result
    values = _as_sequence(levels, "levels")
    return {index: values[index] for index in range(min(len(values), 3))}


def _mesh_parts(mesh: Any, level: int) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int, int]], list[str], list[str], dict[str, list[int]], Any, Any, Any]:
    if not _is_mapping(mesh):
        raise _CheckInputError(f"L{level} mesh must be a mapping")
    raw_vertices = _as_sequence(mesh.get("vertices"), f"L{level}.vertices")
    vertices = [_vector(point, f"L{level}.vertices[{index}]") for index, point in enumerate(raw_vertices)]
    if not vertices:
        raise _CheckInputError(f"L{level}.vertices must not be empty")

    raw_quads = _as_sequence(mesh.get("quads"), f"L{level}.quads")
    quads: list[tuple[int, int, int, int]] = []
    for face_index, raw_face in enumerate(raw_quads):
        face = _as_sequence(raw_face, f"L{level}.quads[{face_index}]")
        if len(face) != 4:
            raise _CheckInputError(f"L{level}.quads[{face_index}] must have four indices")
        if any(isinstance(index, bool) or not isinstance(index, int) for index in face):
            raise _CheckInputError(f"L{level}.quads[{face_index}] indices must be integers")
        checked = tuple(int(index) for index in face)
        if len(set(checked)) != 4 or any(index < 0 or index >= len(vertices) for index in checked):
            raise _CheckInputError(f"L{level}.quads[{face_index}] contains an invalid index")
        quads.append(checked)  # type: ignore[arg-type]
    if not quads:
        raise _CheckInputError(f"L{level}.quads must not be empty")

    face_owners = _owner_rows(mesh.get("face_owners"), len(quads), f"L{level}.face_owners")
    control_owners = _owner_rows(mesh.get("control_owners"), len(vertices), f"L{level}.control_owners")
    loops = _loops(mesh.get("loops"), len(vertices), f"L{level}.loops")
    return vertices, quads, face_owners, control_owners, loops, mesh.get("base_stencils"), mesh.get("frames"), mesh.get("metadata")


def _owner_rows(value: Any, expected: int, label: str) -> list[str]:
    if isinstance(value, Mapping):
        rows: list[Any] = []
        for index in range(expected):
            if index in value:
                rows.append(value[index])
            elif str(index) in value:
                rows.append(value[str(index)])
            else:
                rows.append(None)
    else:
        rows = _as_sequence(value, label)
    if len(rows) != expected:
        raise _CheckInputError(f"{label} must cover all {expected} entries")
    if any(not isinstance(owner, str) or not owner for owner in rows):
        raise _CheckInputError(f"{label} entries must be non-empty strings")
    return list(rows)


def _lineage_rows(value: Any, vertex_count: int, base_vertex_count: int | None, label: str) -> list[list[tuple[int, float]]]:
    rows = _as_sequence(value, label)
    if len(rows) != vertex_count:
        raise _CheckInputError(f"{label} must cover every vertex")
    result: list[list[tuple[int, float]]] = []
    for row_index, raw_row in enumerate(rows):
        terms = _as_sequence(raw_row, f"{label}[{row_index}]")
        if not terms:
            raise _CheckInputError(f"{label}[{row_index}] must not be empty")
        checked: list[tuple[int, float]] = []
        previous = -1
        for term in terms:
            pair = _as_sequence(term, f"{label}[{row_index}] term")
            if len(pair) != 2 or isinstance(pair[0], bool) or not isinstance(pair[0], int):
                raise _CheckInputError(f"{label}[{row_index}] has an invalid base index")
            index = int(pair[0])
            if index <= previous or index < 0 or (base_vertex_count is not None and index >= base_vertex_count):
                raise _CheckInputError(f"{label}[{row_index}] base indices must be sorted and in range")
            if not _finite(pair[1]) or float(pair[1]) == 0.0:
                raise _CheckInputError(f"{label}[{row_index}] has an invalid coefficient")
            checked.append((index, float(pair[1])))
            previous = index
        result.append(checked)
    return result


def _loops(value: Any, vertex_count: int, label: str) -> dict[str, list[int]]:
    if not _is_mapping(value):
        raise _CheckInputError(f"{label} must be a mapping of declared loops")
    result: dict[str, list[int]] = {}
    used: set[int] = set()
    for name, raw_loop in value.items():
        if not isinstance(name, str) or not name:
            raise _CheckInputError(f"{label} names must be non-empty strings")
        loop = _as_sequence(raw_loop, f"{label}.{name}")
        if len(loop) < 3 or any(isinstance(index, bool) or not isinstance(index, int) for index in loop):
            raise _CheckInputError(f"{label}.{name} must be a simple index cycle")
        checked = [int(index) for index in loop]
        if len(set(checked)) != len(checked) or any(index < 0 or index >= vertex_count for index in checked):
            raise _CheckInputError(f"{label}.{name} contains invalid or repeated indices")
        if used.intersection(checked):
            raise _CheckInputError(f"{label} loops must not share boundary vertices")
        used.update(checked)
        result[name] = checked
    if len(result) != 5:
        raise _CheckInputError(f"{label} must contain exactly five declared loops")
    return result


def _edge_incidence(quads: Sequence[Sequence[int]]) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    incidence: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for face_index, face in enumerate(quads):
        for slot, start in enumerate(face):
            end = face[(slot + 1) % len(face)]
            incidence[(min(start, end), max(start, end))].append((face_index, start, end))
    return dict(incidence)


def _canonical_cycle(cycle: Sequence[int]) -> tuple[int, ...]:
    values = tuple(cycle)
    candidates = []
    for sequence in (values, tuple(reversed(values))):
        candidates.extend(sequence[index:] + sequence[:index] for index in range(len(sequence)))
    return min(candidates)


def _cyclic_equal(actual: Sequence[int], expected: Sequence[int]) -> bool:
    actual_values = tuple(actual)
    expected_values = tuple(expected)
    return any(actual_values == target[index:] + target[:index]
               for target in (expected_values, tuple(reversed(expected_values)))
               for index in range(len(target)))


def _boundary_cycles(incidence: Mapping[tuple[int, int], Sequence[tuple[int, int, int]]]) -> list[list[int]]:
    boundary_edges = [uses[0] for uses in incidence.values() if len(uses) == 1]
    outgoing: dict[int, list[int]] = defaultdict(list)
    for _, start, end in boundary_edges:
        outgoing[start].append(end)
    if any(len(targets) != 1 for targets in outgoing.values()):
        raise _CheckInputError("boundary edges do not form directed cycles")
    next_vertex = {start: targets[0] for start, targets in outgoing.items()}
    remaining = set(next_vertex)
    cycles: list[list[int]] = []
    while remaining:
        start = min(remaining)
        current = start
        cycle: list[int] = []
        while current in remaining:
            remaining.remove(current)
            cycle.append(current)
            current = next_vertex[current]
        if current != start or len(cycle) < 3:
            raise _CheckInputError("boundary edge cycle is not closed")
        cycles.append(cycle)
    return cycles


def _connected_components(quads: Sequence[Sequence[int]], vertex_count: int) -> int:
    adjacency: dict[int, set[int]] = {index: set() for index in range(vertex_count)}
    for face in quads:
        for first, second in zip(face, face[1:] + face[:1]):
            adjacency[first].add(second)
            adjacency[second].add(first)
    unseen = set(range(vertex_count))
    count = 0
    while unseen:
        count += 1
        todo = [unseen.pop()]
        while todo:
            neighbours = adjacency[todo.pop()].intersection(unseen)
            unseen.difference_update(neighbours)
            todo.extend(neighbours)
    return count


def _mesh_structural_checks(level: int, mesh: Any, base_quad_count: int | None,
                            base_vertex_count: int | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return a level report and parsed values, or a report on malformed input."""

    level_report: dict[str, Any] = {"level": level, "pass": False, "checks": {}, "errors": []}
    try:
        vertices, quads, face_owners, control_owners, loops, base_stencils, frames, metadata = _mesh_parts(mesh, level)
        lineage = _lineage_rows(base_stencils, len(vertices), len(vertices) if level == 0 else base_vertex_count,
                                f"L{level}.base_stencils")
    except Exception as exc:  # total public report, including malformed mesh input
        level_report["errors"].append(_error("invalid_mesh", str(exc)))
        level_report["render_safe"] = False
        return level_report, None

    level_report["vertex_count"] = len(vertices)
    level_report["quad_count"] = len(quads)
    level_report["checks"]["finite_vertices"] = all(_finite(value) for point in vertices for value in point)
    level_report["checks"]["valid_indices"] = True
    level_report["checks"]["owner_coverage"] = (
        len(face_owners) == len(quads)
        and len(control_owners) == len(vertices)
        and all(isinstance(value, str) and value for value in face_owners + control_owners)
    )
    level_report["checks"]["lineage_coverage"] = len(lineage) == len(vertices)
    level_report["checks"]["all_vertices_used"] = len({index for face in quads for index in face}) == len(vertices)

    incidence = _edge_incidence(quads)
    edge_uses_valid = all(len(uses) in (1, 2) for uses in incidence.values())
    orientation_valid = all(
        len(uses) != 2 or (uses[0][1], uses[0][2]) == (uses[1][2], uses[1][1])
        for uses in incidence.values()
    )
    boundary_cycles: list[list[int]] = []
    boundary_valid = True
    try:
        boundary_cycles = _boundary_cycles(incidence)
    except Exception as exc:
        boundary_valid = False
        level_report["errors"].append(_error("boundary_cycle", str(exc)))
    declared_boundary_match = boundary_valid and len(boundary_cycles) == 5 and all(
        any(_cyclic_equal(actual, declared) for declared in loops.values())
        for actual in boundary_cycles
    )
    level_report["checks"].update({
        "connected_components": _connected_components(quads, len(vertices)),
        "connected_one": _connected_components(quads, len(vertices)) == 1,
        "edge_use_one_or_two": edge_uses_valid,
        "interior_edges_opposite": orientation_valid,
        "boundary_count_exact_five": len(boundary_cycles) == 5,
        "declared_boundary_loops": declared_boundary_match,
        "duplicate_quads": len({_canonical_cycle(face) for face in quads}) == len(quads),
    })
    if not level_report["checks"]["connected_one"]:
        level_report["errors"].append(_error("disconnected_surface", "surface must have one connected component"))
    if not level_report["checks"]["owner_coverage"]:
        level_report["errors"].append(_error("owner_coverage", "face and control owners must cover the mesh exactly"))
    if not level_report["checks"]["lineage_coverage"]:
        level_report["errors"].append(_error("lineage_coverage", "base stencils must cover every evaluated vertex"))
    if base_quad_count is None:
        base_quad_count = len(quads) if level == 0 else None
    if level == 0:
        exact_counts = len(vertices) == _EXPECTED_BASE_VERTICES and len(quads) == _EXPECTED_BASE_QUADS
        level_report["checks"]["exact_initial_counts"] = exact_counts
    elif base_quad_count is not None:
        level_report["checks"]["fourfold_face_count"] = len(quads) == base_quad_count * (4 ** level)
    else:
        level_report["checks"]["fourfold_face_count"] = False
        level_report["errors"].append(_error("missing_base_count", "cannot compare subdivision face count without L0"))

    if not level_report["checks"]["finite_vertices"]:
        level_report["errors"].append(_error("nonfinite_vertices", "vertices contain non-finite coordinates"))
    if not level_report["checks"]["all_vertices_used"]:
        level_report["errors"].append(_error("unused_vertices", "every vertex ID must be used by a quad"))
    if not edge_uses_valid:
        level_report["errors"].append(_error("nonmanifold_edges", "every edge must have one or two incident faces"))
    if not orientation_valid:
        level_report["errors"].append(_error("orientation_conflict", "interior edge directions must be opposite"))
    if not declared_boundary_match:
        level_report["errors"].append(_error("boundary_declaration", "derived boundaries do not match five declared loops"))
    if not level_report["checks"]["duplicate_quads"]:
        level_report["errors"].append(_error("duplicate_quads", "duplicate or reversed/cyclic duplicate quads"))
    if level == 0 and not level_report["checks"]["exact_initial_counts"]:
        level_report["errors"].append(_error(
            "initial_counts", f"L0 must contain exactly {_EXPECTED_BASE_VERTICES} vertices and {_EXPECTED_BASE_QUADS} quads"))
    if level > 0 and not level_report["checks"]["fourfold_face_count"]:
        level_report["errors"].append(_error("subdivision_face_count", "L1/L2 must have fourfold face counts"))

    # A finite, indexed, non-degenerate mesh remains safe to hand to the
    # renderer even when a technical gate fails.
    triangles = [triangle for face in quads for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3]))]
    triangle_areas = [0.5 * _norm(_cross(_vec_sub(vertices[b], vertices[a]), _vec_sub(vertices[c], vertices[a])))
                      for a, b, c in triangles]
    render_safe = bool(level_report["checks"]["finite_vertices"] and level_report["checks"]["valid_indices"]
                       and all(math.isfinite(area) and area > 0.0 for area in triangle_areas))
    level_report["render_safe"] = render_safe
    parsed = {
        "vertices": vertices,
        "quads": quads,
        "face_owners": face_owners,
        "control_owners": control_owners,
        "loops": loops,
        "incidence": incidence,
        "triangles": triangles,
        "triangle_areas": triangle_areas,
        "base_stencils": base_stencils,
        "lineage": lineage,
        "frames": frames,
        "metadata": metadata,
        "boundary_cycles": boundary_cycles,
    }
    level_report["checks"]["topology"] = not level_report["errors"]
    level_report["pass"] = not level_report["errors"]
    return level_report, parsed


def _lookup(mapping: Any, *keys: str) -> Any:
    if not _is_mapping(mapping):
        return None
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _source_mapping(case: Any) -> Mapping[str, Any]:
    if not _is_mapping(case):
        return {}
    source = case.get("source")
    # The preregistered case carrier uses ``source`` for provenance.  Only a
    # physical source metadata mapping is a source mapping for this checker.
    if _is_mapping(source) and any(key in source for key in
                                   ("H", "K", "hip_centres", "knee_centres", "lower_pelvis_width", "radii")):
        return source
    return case


def _find_number(mappings: Iterable[Any], keys: Sequence[str]) -> float | None:
    for mapping in mappings:
        value = _lookup(mapping, *keys)
        if _finite(value):
            return float(value)
    return None


def _point_mapping(value: Any) -> dict[str, tuple[float, float, float]]:
    result: dict[str, tuple[float, float, float]] = {}
    if not _is_mapping(value):
        return result
    for key, raw_point in value.items():
        try:
            result[str(key)] = _vector(raw_point, f"point {key}")
        except Exception:
            continue
    return result


def _pair_distance(points: Mapping[str, Sequence[float]], first_words: Sequence[str], second_words: Sequence[str]) -> float | None:
    first = next((points[key] for key in points if any(word in key.lower() for word in first_words)), None)
    second = next((points[key] for key in points if any(word in key.lower() for word in second_words)), None)
    if first is None or second is None:
        return None
    return _norm(_vec_sub(first, second))


def _source_dimensions(case: Any) -> dict[str, Any]:
    source = _source_mapping(case)
    mappings = (source, case)
    components = case.get("components", {}) if _is_mapping(case) and _is_mapping(case.get("components")) else {}
    component_numbers = lambda *keys: next((float(components[key]) for key in keys
                                             if _finite(components.get(key))), None)
    pelvis_radius = component_numbers("stations.lower_pelvis.rL")
    pelvis_width = _find_number(mappings, ("lower_pelvis_width", "pelvis_width", "width_pelvis"))
    if pelvis_width is None and pelvis_radius is not None:
        pelvis_width = 2.0 * pelvis_radius
    if pelvis_width is None:
        radius = _find_number(mappings, ("rL", "lower_radius", "pelvis_radius"))
        if radius is not None:
            pelvis_width = 2.0 * radius

    attachments = case.get("attachments", {}) if _is_mapping(case) else {}
    hip_points = {str(side): _vector(item["centre"], f"{side} H")
                  for side, item in attachments.items()
                  if _is_mapping(item) and "centre" in item
                  and _is_mapping(case.get("attachments"))}
    knee_points = {str(side): _vector(item["knee"], f"{side} K")
                   for side, item in attachments.items()
                   if _is_mapping(item) and "knee" in item
                   and _is_mapping(case.get("attachments"))}
    hip_points.update({key: value for key, value in
                       _point_mapping(_lookup(source, "hip_centres", "hip_centers", "hips")).items()
                       if key not in hip_points})
    knee_points.update({key: value for key, value in
                        _point_mapping(_lookup(source, "knee_centres", "knee_centers", "knees")).items()
                        if key not in knee_points})
    if not hip_points:
        for side in ("left", "right"):
            values = [component_numbers(f"hips.{side}.P_s.{axis}") for axis in ("x", "y", "z")]
            if all(value is not None for value in values):
                hip_points[side] = tuple(values)  # type: ignore[assignment]
    hip_spacing = _find_number(mappings, ("hip_spacing", "hipSpacing"))
    if hip_spacing is None:
        hip_spacing = _pair_distance(hip_points, ("left",), ("right",))

    hip_knee_distances: dict[str, float] = {}
    explicit_hip_knee = _lookup(source, "hip_knee_distances", "hipKneeDistances")
    if _is_mapping(explicit_hip_knee):
        for key, value in explicit_hip_knee.items():
            if _finite(value):
                hip_knee_distances[str(key)] = float(value)
    for key, hip in hip_points.items():
        side = "left" if "left" in key.lower() else "right" if "right" in key.lower() else key
        knee = next((point for knee_key, point in knee_points.items() if side in knee_key.lower()), None)
        if knee is not None:
            hip_knee_distances[side] = _norm(_vec_sub(knee, hip))
    explicit_distance = _find_number(mappings, ("distance_hip_knee", "hip_knee_distance", "hipKneeDistance"))
    if explicit_distance is not None and not hip_knee_distances:
        hip_knee_distances["all"] = explicit_distance

    declared_axis = _lookup(source, "axis", "source_axis", "sourceAxis")
    try:
        declared_axis = _unit(_vector(declared_axis, "source axis"), "source axis")
    except Exception:
        declared_axis = None

    source_h = _lookup(source, "H", "h", "structural_centre", "structural_center")
    try:
        source_h = _vector(source_h, "source H")
    except Exception:
        source_h = None
    source_k = _lookup(source, "K", "k", "knee", "knee_centre", "knee_center")
    try:
        source_k = _vector(source_k, "source K")
    except Exception:
        source_k = None
    # H is the source thigh-start attachment and K is the source knee
    # landmark.  A joint-frame hint is intentionally never consulted.
    actual_axes: dict[str, tuple[float, float, float]] = {}
    h_by_side: dict[str, tuple[float, float, float]] = {}
    k_by_side: dict[str, tuple[float, float, float]] = {}
    for side, hip in hip_points.items():
        if side in knee_points:
            h_by_side[side] = hip
            k_by_side[side] = knee_points[side]
            try:
                actual_axes[side] = _unit(_vec_sub(knee_points[side], hip), f"{side} H-to-K axis")
            except Exception:
                pass
    if source_h is not None:
        h_by_side.setdefault("default", source_h)
    if source_k is not None:
        k_by_side.setdefault("default", source_k)
    if not actual_axes and source_h is not None and source_k is not None:
        try:
            actual_axes["default"] = _unit(_vec_sub(source_k, source_h), "source H-to-K axis")
        except Exception:
            pass
    source_axis = next(iter(actual_axes.values()), declared_axis)

    radii = _lookup(source, "exit_radii", "radii", "thigh_radii", "source_radii")
    if not _is_mapping(radii):
        radii = {}
    length = _find_number(mappings, ("length", "thigh_length", "hip_knee_length", "hipKneeLength"))
    if length is None and hip_knee_distances:
        length = max(hip_knee_distances.values())
    radii_from_components: dict[str, dict[str, float]] = {}
    for side in ("left", "right"):
        values = {axis: component_numbers(f"hips.{side}.r_{axis}") for axis in ("x", "y", "z")}
        if any(value is not None for value in values.values()):
            radii_from_components[side] = {key: value for key, value in values.items() if value is not None}
    if radii_from_components:
        if not _is_mapping(radii):
            radii = {}
        radii = {**radii, **radii_from_components}
    r_y = {side: values.get("y") for side, values in radii_from_components.items() if values.get("y") is not None}
    scale_inputs = [value for value in (pelvis_width, hip_spacing, max(hip_knee_distances.values(), default=None))
                    if value is not None and value > 0.0]
    scale = max(scale_inputs) if len(scale_inputs) == 3 else None
    return {
        "pelvis_width": pelvis_width,
        "hip_spacing": hip_spacing,
        "hip_knee_distances": hip_knee_distances,
        "scale": scale,
        "scale_inputs_complete": len(scale_inputs) == 3,
        "hip_points": hip_points,
        "knee_points": knee_points,
        "H": source_h or next(iter(h_by_side.values()), None),
        "H_by_side": h_by_side,
        "K_by_side": k_by_side,
        "axis": source_axis,
        "declared_axis": declared_axis,
        "actual_axes": actual_axes,
        "length": length,
        "radii": radii,
        "r_y": r_y,
    }


def _owner_is_lower(owner: str, pelvis_only: bool = False) -> bool:
    normal = owner.lower().replace("-", "_").replace(" ", "_")
    words = _PELVIS_RAY_OWNER_WORDS if pelvis_only else _LOWER_OWNER_WORDS
    return any(word in normal for word in words)


def _triangle_normal(vertices: Sequence[Sequence[float]], triangle: Sequence[int]) -> tuple[float, float, float]:
    return _cross(_vec_sub(vertices[triangle[1]], vertices[triangle[0]]),
                  _vec_sub(vertices[triangle[2]], vertices[triangle[0]]))


def _face_normal(vertices: Sequence[Sequence[float]], face: Sequence[int]) -> tuple[float, float, float]:
    first = _triangle_normal(vertices, (face[0], face[1], face[2]))
    second = _triangle_normal(vertices, (face[0], face[2], face[3]))
    return _unit(_vec_add(first, second), "face normal")


def _triangle_inventory(parsed: Mapping[str, Any]) -> tuple[list[tuple[int, int, int]], list[int]]:
    triangles = list(parsed["triangles"])
    owners = [index // 2 for index in range(len(triangles))]
    return triangles, owners


def _intersection_report(vertices: Sequence[Sequence[float]], triangles: Sequence[Sequence[int]], face_ids: Sequence[int], face_owners: Sequence[str]) -> dict[str, Any]:
    """Run the generic intersection diagnostic under its 4096-triangle cap.

    The new surface may contain 4352 triangles.  Three disjoint groups are
    used for the required pairwise unions; the three within-group calls are
    also made because cross-group unions alone cannot mathematically cover
    pairs whose two triangles share a group.  Every call reuses the original
    vertex array, so unreferenced vertices are intentionally not rewritten.
    """

    result: dict[str, Any] = {
        "available": False,
        "pair_policy_complete": True,
        "collision_inventory_complete": True,
        "vertex_array_reused": True,
        "groups": [],
        "calls": [],
        "hit_pairs": [],
        "lower_hit_pairs": [],
        "upper_only_hit_pairs": [],
        "errors": [],
    }
    try:
        module_path = Path(__file__).resolve().parents[1] / "owned-root-assembly-successor" / "mesh_correctness.py"
        spec = importlib.util.spec_from_file_location("owned_root_generic_mesh_correctness", module_path)
        if spec is None or spec.loader is None:
            raise _CheckInputError("generic intersection diagnostic could not be loaded")
        module = importlib.util.module_from_spec(spec)
        # Dataclasses resolve their declaring module through sys.modules.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        intersection_diagnostics = module.intersection_diagnostics
    except Exception as exc:
        result["errors"].append(_error("intersection_unavailable", str(exc)))
        return result

    triangle_count = len(triangles)
    groups = [list(range(start, min(start + math.ceil(triangle_count / 3), triangle_count)))
              for start in range(0, triangle_count, math.ceil(triangle_count / 3))]
    while len(groups) < _INTERSECTION_GROUP_COUNT:
        groups.append([])
    groups = groups[:_INTERSECTION_GROUP_COUNT]
    result["groups"] = [{"group": index, "triangle_count": len(group), "triangle_ids": group}
                         for index, group in enumerate(groups)]

    # The three disjoint group unions cover every unordered triangle pair:
    # each cross-group pair occurs in its group pair, and every within-group
    # pair occurs in either union containing that group.
    pair_group_specs = list(itertools.combinations(range(3), 2))
    seen_pairs: set[tuple[int, int]] = set()
    for first_group, second_group in pair_group_specs:
        local_ids = groups[first_group] if first_group == second_group else groups[first_group] + groups[second_group]
        local_triangles = [triangles[index] for index in local_ids]
        call: dict[str, Any] = {
            "groups": [first_group, second_group],
            "triangle_count": len(local_triangles),
            "pair_policy_complete": False,
            "hit_pairs": [],
        }
        if not local_triangles:
            call["pair_policy_complete"] = True
            result["calls"].append(call)
            continue
        try:
            diagnostic = intersection_diagnostics(vertices, local_triangles)
            call["pair_policy_complete"] = bool(diagnostic.get("pair_policy_complete"))
            call["pair_count"] = diagnostic.get("pair_count", 0)
            call["intersection_hit_count"] = diagnostic.get("intersection_hit_count", 0)
            call["hit_pairs_truncated"] = bool(diagnostic.get("hit_pairs_truncated", False))
            if call["hit_pairs_truncated"]:
                call["collision_inventory_complete"] = False
                result["collision_inventory_complete"] = False
                result["errors"].append(_error(
                    "incomplete_collision_inventory",
                    "generic intersection helper truncated hit_pairs at its evidence cap",
                    groups=[first_group, second_group],
                    hit_count=diagnostic.get("intersection_hit_count"),
                ))
            for local_first, local_second in diagnostic.get("hit_pairs", ()):
                global_first = local_ids[int(local_first)]
                global_second = local_ids[int(local_second)]
                pair = tuple(sorted((global_first, global_second)))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    result["hit_pairs"].append(pair)
                    face_pair = (face_ids[pair[0]], face_ids[pair[1]])
                    owners = (face_owners[face_pair[0]], face_owners[face_pair[1]])
                    if any(_owner_is_lower(owner) for owner in owners):
                        result["lower_hit_pairs"].append({"triangles": pair, "faces": face_pair, "owners": owners})
                    else:
                        result["upper_only_hit_pairs"].append({"triangles": pair, "faces": face_pair, "owners": owners})
                    call["hit_pairs"].append(pair)
        except Exception as exc:
            call["error"] = _error("intersection_failure", str(exc))
            result["errors"].append(call["error"])
            result["pair_policy_complete"] = False
        result["calls"].append(call)
    result["available"] = not result["errors"]
    result["pair_policy_complete"] = result["available"] and all(call["pair_policy_complete"] for call in result["calls"])
    result["hit_pairs"].sort()
    result["lower_hit_pairs"].sort(key=lambda item: tuple(item["triangles"]))
    result["upper_only_hit_pairs"].sort(key=lambda item: tuple(item["triangles"]))
    result["unreferenced_vertex_count"] = len(vertices) - len({index for triangle in triangles for index in triangle})
    result["pass"] = (result["pair_policy_complete"] and result["collision_inventory_complete"]
                       and not result["lower_hit_pairs"])
    return result


def _dimension_gates(parsed: Mapping[str, Any], scale_info: Mapping[str, Any], level: int) -> dict[str, Any]:
    scale = scale_info.get("scale")
    result: dict[str, Any] = {"scale": scale, "scale_source": "case_source_dimensions" if scale is not None else None}
    edges = parsed["incidence"]
    edge_lengths = [_norm(_vec_sub(parsed["vertices"][edge[1]], parsed["vertices"][edge[0]])) for edge in edges]
    triangle_areas = list(parsed["triangle_areas"])
    if scale is None or not _finite(scale) or float(scale) <= 0.0:
        result.update({"available": False, "pass": False, "edge_min": min(edge_lengths, default=None),
                       "triangle_area_min": min(triangle_areas, default=None)})
        result["error"] = _error("missing_scale", "S requires pelvis width, hip spacing, and hip-knee distance")
        return result
    scale = float(scale)
    edge_threshold = _SCALE_EDGE_FLOOR * scale
    area_threshold = _SCALE_TRIANGLE_FLOOR * scale * scale
    result.update({
        "available": True,
        "edge_min": min(edge_lengths, default=None),
        "edge_threshold": edge_threshold,
        "triangle_area_min": min(triangle_areas, default=None),
        "triangle_area_threshold": area_threshold,
        "edge_floor_pass": bool(edge_lengths) and min(edge_lengths) > edge_threshold,
        "triangle_area_floor_pass": bool(triangle_areas) and min(triangle_areas) > area_threshold,
    })
    result["pass"] = result["edge_floor_pass"] and result["triangle_area_floor_pass"]
    if not result["pass"]:
        result["error"] = _error("scaled_degeneracy", f"L{level} edge/triangle floors failed at case scale S")
    return result


def _frame_sources(case: Any, final_parsed: Mapping[str, Any] | None) -> list[tuple[str, Mapping[str, Any]]]:
    sources: list[tuple[str, Mapping[str, Any]]] = []
    # Final evaluated metadata is authoritative.  Case-level metadata is a
    # fallback for the synthetic unit fixtures only.
    if final_parsed is not None and _is_mapping(final_parsed.get("frames")):
        return [("L2.frames", final_parsed["frames"])]
    if _is_mapping(case):
        for key in ("frames", "frame"):
            value = case.get(key)
            if _is_mapping(value):
                sources.append((f"case.{key}", value))
    if final_parsed is not None and _is_mapping(final_parsed.get("frames")):
        sources.append(("L2.frames", final_parsed["frames"]))
    return sources


def _frame_records(case: Any, final_parsed: Mapping[str, Any] | None) -> list[tuple[str, Mapping[str, Any]]]:
    records: list[tuple[str, Mapping[str, Any]]] = []
    for source_name, source in _frame_sources(case, final_parsed):
        direct_keys = {"H", "h", "X", "x", "U", "u", "Y", "y", "F", "f", "Z", "z", "axis", "d", "direction"}
        if direct_keys.intersection(source):
            records.append((source_name, source))
            continue
        for key, value in source.items():
            if _is_mapping(value):
                records.append((str(key), value))
    # A frame may be stored as a list of side records.
    if final_parsed is not None and isinstance(final_parsed.get("frames"), (list, tuple)):
        for index, value in enumerate(final_parsed["frames"]):
            if _is_mapping(value):
                records.append((f"L2.frames[{index}]", value))
    # Keep one record per label/source to avoid duplicate case and mesh copies.
    unique: list[tuple[str, Mapping[str, Any]]] = []
    seen: set[tuple[str, int]] = set()
    for label, record in records:
        identity = (label, id(record))
        if identity not in seen:
            seen.add(identity)
            unique.append((label, record))
    return unique


def _frame_vectors(record: Mapping[str, Any]) -> tuple[tuple[float, float, float], ...]:
    nested = _lookup(record, "frame", "XYZ", "xyz")
    frame = nested if _is_mapping(nested) else record
    x = _lookup(frame, "X", "x", "right")
    u = _lookup(frame, "U", "u", "Y", "y", "up")
    f = _lookup(frame, "F", "f", "Z", "z", "front")
    return _vector(x, "frame X"), _vector(u, "frame U/Y"), _vector(f, "frame F/Z")


def _metadata_vector(record: Mapping[str, Any], *keys: str) -> tuple[float, float, float] | None:
    value = _lookup(record, *keys)
    try:
        return _vector(value, ".".join(keys))
    except Exception:
        return None


def _metadata_h(record: Mapping[str, Any], scale_info: Mapping[str, Any], side: str | None = None) -> tuple[float, float, float] | None:
    by_side = scale_info.get("H_by_side", {})
    if side and side in by_side:
        return by_side[side]
    if scale_info.get("H") is not None:
        return scale_info["H"]
    return _metadata_vector(record, "H", "h", "structural_center", "structural_centre")


def _metadata_axis(record: Mapping[str, Any], scale_info: Mapping[str, Any], side: str | None = None) -> tuple[float, float, float] | None:
    direct = _metadata_vector(record, "axis", "d", "direction", "source_axis", "sourceAxis")
    if direct is not None:
        try:
            return _unit(direct, "metadata axis")
        except Exception:
            return None
    actual = scale_info.get("actual_axes", {})
    if side and side in actual:
        return actual[side]
    axis = scale_info.get("axis")
    if axis is not None:
        try:
            return _unit(axis, "source axis")
        except Exception:
            return None
    return None


def _record_side(label: str) -> str | None:
    normal = label.lower()
    if "left" in normal:
        return "left"
    if "right" in normal:
        return "right"
    return None


def _expected_mapping(case: Any, final_parsed: Mapping[str, Any] | None) -> Any:
    values = []
    if _is_mapping(case):
        values.extend(case.get(key) for key in ("exitexpected", "exit_expected", "exit_expectations") if key in case)
        source = case.get("source")
        if _is_mapping(source):
            values.extend(source.get(key) for key in ("exitexpected", "exit_expected", "exit_expectations") if key in source)
    if final_parsed is not None:
        frames = final_parsed.get("frames")
        if _is_mapping(frames):
            values.extend(frames.get(key) for key in ("exitexpected", "exit_expected") if key in frames)
        metadata = final_parsed.get("metadata")
        if _is_mapping(metadata):
            values.extend(metadata.get(key) for key in ("exitexpected", "exit_expected") if key in metadata)
    return next((value for value in values if value is not None), None)


def _index_loop_mapping(case: Any, final_parsed: Mapping[str, Any]) -> Any:
    values = []
    if _is_mapping(case):
        values.extend(case.get(key) for key in ("indexloops", "index_loops") if key in case)
        source = case.get("source")
        if _is_mapping(source):
            values.extend(source.get(key) for key in ("indexloops", "index_loops") if key in source)
    frames = final_parsed.get("frames")
    if _is_mapping(frames):
        values.extend(frames.get(key) for key in ("indexloops", "index_loops") if key in frames)
    metadata = final_parsed.get("metadata")
    if _is_mapping(metadata):
        values.extend(metadata.get(key) for key in ("indexloops", "index_loops", "transition_indices") if key in metadata)
    return next((value for value in values if value is not None), None)


def _exit_loop_names(case: Any, parsed: Mapping[str, Any]) -> list[str]:
    loops = parsed["loops"]
    if "port.left_thigh" in loops and "port.right_thigh" in loops:
        return ["port.left_thigh", "port.right_thigh"]
    index_mapping = _index_loop_mapping(case, parsed)
    names: list[str] = []
    if _is_mapping(index_mapping):
        for key, value in index_mapping.items():
            if isinstance(value, str) and value in loops:
                names.append(value)
            elif isinstance(key, str) and key in loops:
                names.append(key)
            elif isinstance(key, str) and isinstance(value, (list, tuple)):
                try:
                    wanted = tuple(int(item) for item in value)
                except Exception:
                    wanted = ()
                for loop_name, loop in loops.items():
                    if tuple(loop) == wanted:
                        names.append(loop_name)
    if not names:
        names = [name for name in loops if any(word in name.lower() for word in _EXIT_NAME_WORDS)]
    if len(names) < 2:
        return []  # Missing exits fail the exit gate; other ports are not substitutes.
    return list(dict.fromkeys(names))[:2]


def _side_value(mapping: Any, loop_name: str, side: str | None) -> Any:
    if not _is_mapping(mapping):
        return mapping
    for key in (loop_name, side, "left" if side == "left" else "right" if side == "right" else None):
        if key is not None and key in mapping:
            return mapping[key]
    return mapping.get("default")


def _expected_exit(case: Any, parsed: Mapping[str, Any], loop_name: str, side: str | None, record: Mapping[str, Any] | None,
                   scale_info: Mapping[str, Any]) -> tuple[tuple[float, float, float] | None, str]:
    # Compute E from the captured source attachments first.  Exported L2
    # metadata is evidence to compare, never the source of truth for E.
    h = scale_info.get("H_by_side", {}).get(side) if side else None
    k = scale_info.get("K_by_side", {}).get(side) if side else None
    if h is None:
        h = scale_info.get("H")
    if k is None:
        k = scale_info.get("K_by_side", {}).get("default")
    if h is not None and k is not None:
        delta = _vec_sub(k, h)
        length = _norm(delta)
        if length > 0.0:
            return _vec_add(h, _vec_scale(delta, 0.45)), "source.H+0.45*(source.K-source.H)"

    explicit = _side_value(_expected_mapping(case, parsed), loop_name, side)
    if _is_mapping(explicit):
        for key in ("centroid", "center", "centre", "E", "expected"):
            if key in explicit:
                try:
                    return _vector(explicit[key], f"expected exit {loop_name}"), f"declared.{key}.fallback"
                except Exception:
                    pass
    elif explicit is not None:
        try:
            return _vector(explicit, f"expected exit {loop_name}"), "declared.fallback"
        except Exception:
            pass
    return None, "unavailable"


def _source_radius(scale_info: Mapping[str, Any], loop_name: str, side: str | None, axis: str) -> float | None:
    radii = scale_info.get("radii", {})
    values: list[Any] = []
    if _is_mapping(radii):
        for key in (loop_name, side, "left" if side == "left" else "right" if side == "right" else None):
            if key is not None and key in radii:
                values.append(radii[key])
        values.append(radii)
    for value in values:
        if _is_mapping(value):
            aliases = ("rx", "r_x", "x", "X") if axis == "X" else ("rz", "r_z", "z", "F", "f")
            candidate = _lookup(value, *aliases)
            if _finite(candidate) and float(candidate) > 0.0:
                return float(candidate)
        elif _finite(value) and float(value) > 0.0:
            return float(value)
    return None


def _loop_geometry(vertices: Sequence[Sequence[float]], loop: Sequence[int]) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    centroid = _vec_scale(tuple(sum(vertices[index][axis] for index in loop) for axis in range(3)), 1.0 / len(loop))
    area = (0.0, 0.0, 0.0)
    for index, vertex in enumerate(loop):
        area = _vec_add(area, _cross(_vec_sub(vertices[vertex], centroid),
                                     _vec_sub(vertices[loop[(index + 1) % len(loop)]], centroid)))
    area = _vec_scale(area, 0.5)
    return centroid, _unit(area, "exit loop plane normal"), _norm(area)


def _exit_checks(case: Any, parsed: Mapping[str, Any], scale_info: Mapping[str, Any]) -> dict[str, Any]:
    loops = parsed["loops"]
    names = _exit_loop_names(case, parsed)
    records = _frame_records(case, parsed)
    result: dict[str, Any] = {
        "exit_loops": names,
        "pass": True,
        "loops": {},
        "frame_records": [],
        "render_metrics": {"pass": True, "loops": {}},
    }
    record_by_side = {_record_side(label): record for label, record in records if _record_side(label) is not None}
    if len(names) != 2:
        result["pass"] = False
        result["errors"] = [_error("exit_loop_count", "two exit loops are required")]

    for label, record in records:
        frame_report: dict[str, Any] = {"label": label, "pass": False}
        try:
            x_axis, u_axis, f_axis = _frame_vectors(record)
            lengths = tuple(_norm(axis) for axis in (x_axis, u_axis, f_axis))
            dots = (_dot(x_axis, u_axis), _dot(x_axis, f_axis), _dot(u_axis, f_axis))
            handed = _dot(_cross(x_axis, u_axis), f_axis)
            frame_report.update({"X": x_axis, "U": u_axis, "F": f_axis, "lengths": lengths, "pairwise_dots": dots,
                                 "right_handed_dot": handed,
                                 "orthonormal": all(abs(length - 1.0) <= _FRAME_TOLERANCE for length in lengths)
                                 and all(abs(dot) <= _FRAME_TOLERANCE for dot in dots),
                                 "right_handed": handed >= 1.0 - _FRAME_TOLERANCE})
            side = _record_side(label)
            reported_axis = _metadata_vector(record, "axis", "d", "direction", "source_axis", "sourceAxis")
            axis = _unit(reported_axis, "evaluated frame axis") if reported_axis is not None else None
            actual_axis = scale_info.get("actual_axes", {}).get(side) if side else scale_info.get("axis")
            source_h = _metadata_h({}, scale_info, side)
            frame_h = _metadata_vector(record, "H", "h")
            frame_report["source_H_matches"] = (source_h is not None and frame_h is not None
                                                  and _norm(_vec_sub(frame_h, source_h)) <= _POSITION_TOLERANCE * float(scale_info.get("scale") or 0.0))
            if axis is not None and actual_axis is not None:
                frame_report["source_axis_angle_radians"] = _angle_radians(axis, actual_axis)
                frame_report["source_axis_matches_actual_H_to_K"] = frame_report["source_axis_angle_radians"] <= _EXIT_DIRECTION_TOLERANCE
            else:
                frame_report["source_axis_matches_actual_H_to_K"] = False
                frame_report["source_axis_error"] = _error("missing_source_axis", "source axis and actual H-to-K axis are required")
            frame_report["pass"] = bool(frame_report["orthonormal"] and frame_report["right_handed"]
                                        and frame_report["source_H_matches"]
                                        and frame_report["source_axis_matches_actual_H_to_K"])
            if not frame_report["pass"]:
                frame_report["error"] = _error("frame_gate", "frame must be finite orthonormal, right-handed, and source-axis aligned")
        except Exception as exc:
            frame_report["error"] = _error("invalid_frame", str(exc))
        result["frame_records"].append(frame_report)
        result["pass"] = result["pass"] and frame_report["pass"]

    for loop_name in names:
        loop = loops[loop_name]
        side = "left" if "left" in loop_name.lower() else "right" if "right" in loop_name.lower() else None
        record = record_by_side.get(side) if side else (records[0][1] if records else None)
        loop_report: dict[str, Any] = {"loop": loop_name, "pass": False}
        render_report: dict[str, Any] = {"pass": False}
        try:
            centroid, plane_normal, area = _loop_geometry(parsed["vertices"], loop)
            axis = _metadata_axis(record or {}, scale_info, side)
            expected, expected_source = _expected_exit(case, parsed, loop_name, side, record, scale_info)
            centroid_error = _norm(_vec_sub(centroid, expected)) if expected is not None else None
            plane_error = max(abs(_dot(_vec_sub(parsed["vertices"][index], centroid), plane_normal)) for index in loop)
            # Declared open-loop winding is inward for this interface.  The
            # geometric outward normal is therefore the negated Newell normal.
            outward_normal = _vec_scale(plane_normal, -1.0)
            outward_dot = _dot(outward_normal, axis) if axis is not None else None
            incidence = parsed["incidence"]
            conormals: list[float] = []
            missing_edges: list[tuple[int, int]] = []
            face_normals = {face_index: _face_normal(parsed["vertices"], face)
                            for face_index, face in enumerate(parsed["quads"])}
            for index, start in enumerate(loop):
                end = loop[(index + 1) % len(loop)]
                uses = incidence.get((min(start, end), max(start, end)), [])
                if len(uses) != 1:
                    missing_edges.append((start, end))
                    continue
                tangent = _unit(_vec_sub(parsed["vertices"][end], parsed["vertices"][start]), "exit loop tangent")
                adjacent_normal = face_normals[uses[0][0]]
                co_normal = _unit(_cross(tangent, adjacent_normal), "exit co-normal")
                conormals.append(_dot(co_normal, axis) if axis is not None else float("nan"))
            min_conormal = min(conormals) if conormals else None
            loop_report.update({"centroid": centroid, "expected_centroid": expected, "expected_source": expected_source,
                                "centroid_error": centroid_error, "plane_normal": plane_normal,
                                "outward_normal": outward_normal, "plane_error": plane_error,
                                "plane_area": area, "outward_dot_direction": outward_dot, "co_normals": conormals,
                                "co_normal_min": min_conormal, "missing_boundary_edges": missing_edges})
            loop_report["pass"] = bool(expected is not None and axis is not None and centroid_error <= _POSITION_TOLERANCE * float(scale_info.get("scale") or 0.0)
                                        and outward_dot is not None and outward_dot >= _EXIT_NORMAL_COS
                                        and plane_error <= _POSITION_TOLERANCE * float(scale_info.get("scale") or 0.0)
                                        and not missing_edges and min_conormal is not None and min_conormal >= _EXIT_CONORMAL_COS)

            x_axis, _, f_axis = _frame_vectors(record or {})
            projections_x = [_dot(_vec_sub(parsed["vertices"][index], centroid), x_axis) for index in loop]
            projections_f = [_dot(_vec_sub(parsed["vertices"][index], centroid), f_axis) for index in loop]
            half_x = 0.5 * (max(projections_x) - min(projections_x))
            half_f = 0.5 * (max(projections_f) - min(projections_f))
            source_rx = _source_radius(scale_info, loop_name, side, "X")
            source_rz = _source_radius(scale_info, loop_name, side, "F")
            ratios = {"X": half_x / source_rx if source_rx else None, "F": half_f / source_rz if source_rz else None}
            render_report.update({"half_spans": {"X": half_x, "F": half_f}, "source_half_spans": {"X": source_rx, "F": source_rz},
                                  "ratios": ratios,
                                  "span_pass": all(ratio is not None and 0.75 <= ratio <= 1.05 for ratio in ratios.values())})
            render_report["pass"] = bool(render_report["span_pass"])
            if not render_report["pass"]:
                render_report["error"] = _error("exit_span_render_metric", "exit projected X/F half-spans must be 0.75..1.05 of source radii")
            loop_report["render_metric_pass"] = render_report["pass"]
            result["render_metrics"]["loops"][loop_name] = render_report
            result["render_metrics"]["pass"] = result["render_metrics"]["pass"] and render_report["pass"]
        except Exception as exc:
            loop_report["error"] = _error("exit_loop_geometry", str(exc))
            result["render_metrics"]["loops"][loop_name] = render_report
            result["render_metrics"]["pass"] = False
        result["loops"][loop_name] = loop_report
        result["pass"] = result["pass"] and loop_report["pass"]
    result["pass"] = result["pass"] and result["render_metrics"]["pass"]
    return result


def _lower_fold_checks(parsed: Mapping[str, Any]) -> dict[str, Any]:
    incidence = parsed["incidence"]
    face_normals = {index: _face_normal(parsed["vertices"], face) for index, face in enumerate(parsed["quads"])}
    lower: list[dict[str, Any]] = []
    upper: list[dict[str, Any]] = []
    for edge, uses in incidence.items():
        if len(uses) != 2:
            continue
        first_face, second_face = uses[0][0], uses[1][0]
        angle = _angle_degrees(face_normals[first_face], face_normals[second_face])
        row = {"edge": edge, "faces": [first_face, second_face], "owners": [parsed["face_owners"][first_face], parsed["face_owners"][second_face]],
               "normal_angle_degrees": angle}
        if any(_owner_is_lower(owner) for owner in row["owners"]):
            lower.append(row)
        else:
            upper.append(row)
    lower_failures = [row for row in lower if row["normal_angle_degrees"] > _LOWER_FOLD_LIMIT_DEGREES]
    return {
        "lower": {"pairs": lower, "failure_count": len(lower_failures), "pass": not lower_failures,
                   "failures": lower_failures, "limit_degrees": _LOWER_FOLD_LIMIT_DEGREES},
        "upper_inherited": {"pairs": upper, "diagnostic_only": True, "failure_count": 0,
                             "pass": True, "note": "upper folds are reported separately"},
        "control_angle_diagnostics": {"available": False, "gate": False,
                                       "note": "control-angle observations are diagnostic only"},
    }


def _lower_quad_normal_checks(parsed: Mapping[str, Any]) -> dict[str, Any]:
    failures = []
    samples = []
    for face_index, face in enumerate(parsed["quads"]):
        if not _owner_is_lower(parsed["face_owners"][face_index]):
            continue
        first = _triangle_normal(parsed["vertices"], (face[0], face[1], face[2]))
        second = _triangle_normal(parsed["vertices"], (face[0], face[2], face[3]))
        value = _dot(first, second)
        row = {"face": face_index, "normal_dot": value, "owner": parsed["face_owners"][face_index]}
        samples.append(row)
        if value < 0.0:
            failures.append(row)
    return {"samples": samples, "failure_count": len(failures), "failures": failures, "pass": not failures}


def _ray_triangle(origin: Sequence[float], direction: Sequence[float], vertices: Sequence[Sequence[float]], triangle: Sequence[int]) -> float | None:
    a, b, c = (vertices[index] for index in triangle)
    edge_one = _vec_sub(b, a)
    edge_two = _vec_sub(c, a)
    pvec = _cross(direction, edge_two)
    determinant = _dot(edge_one, pvec)
    if abs(determinant) <= 1.0e-14:
        return None
    inverse = 1.0 / determinant
    tvec = _vec_sub(origin, a)
    u = _dot(tvec, pvec) * inverse
    if u < -1.0e-12 or u > 1.0 + 1.0e-12:
        return None
    qvec = _cross(tvec, edge_one)
    v = _dot(direction, qvec) * inverse
    if v < -1.0e-12 or u + v > 1.0 + 1.0e-12:
        return None
    distance = _dot(edge_two, qvec) * inverse
    return distance if distance > 0.0 else None


def _deduplicate_hits(values: Sequence[float], tolerance: float) -> list[float]:
    result: list[float] = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return result


def _containment_checks(case: Any, parsed: Mapping[str, Any], scale_info: Mapping[str, Any]) -> dict[str, Any]:
    scale = float(scale_info.get("scale") or 0.0)
    result: dict[str, Any] = {"pass": False, "H_by_side": scale_info.get("H_by_side", {}),
                              "axis_by_side": scale_info.get("actual_axes", {}), "rays": {},
                              "directional_radial_distances": {},
                              "centres": {}, "section_above_H": {"diagnostic_only": True, "rays": {}}}
    if scale <= 0.0:
        result["error"] = _error("containment_inputs", "structural H and case scale S are required")
        return result
    records = _frame_records(case, parsed)
    if not records:
        result["error"] = _error("containment_frame", "actual L2 frame metadata is required")
        return result

    any_record = False
    all_sides_pass = True
    for label, record in records:
        side = _record_side(label)
        h = _metadata_h(record, scale_info, side)
        axis = _metadata_axis(record, scale_info, side)
        try:
            x_axis, _, f_axis = _frame_vectors(record)
        except Exception as exc:
            result["rays"][label] = {"pass": False, "error": _error("containment_frame", str(exc))}
            all_sides_pass = False
            continue
        target_triangles = [triangle for triangle, face_index in zip(parsed["triangles"], range(len(parsed["triangles"])))
                            if _owner_is_lower(parsed["face_owners"][face_index // 2], pelvis_only=True)
                            and (side is None or side in parsed["face_owners"][face_index // 2].lower())]
        if not target_triangles:
            target_triangles = [triangle for triangle, face_index in zip(parsed["triangles"], range(len(parsed["triangles"])))
                                if _owner_is_lower(parsed["face_owners"][face_index // 2], pelvis_only=True)]
        if h is None or not target_triangles:
            result["rays"][label] = {"pass": False, "error": _error("containment_inputs", "H and side-hip/pelvis triangles are required")}
            all_sides_pass = False
            continue
        any_record = True
        side_rays: dict[str, Any] = {}
        side_pass = True
        for direction_name, direction, radius_axis in (
                ("+X", x_axis, "X"), ("-X", _vec_scale(x_axis, -1.0), "X"),
                ("+F", f_axis, "F"), ("-F", _vec_scale(f_axis, -1.0), "F")):
            distances = [_ray_triangle(h, direction, parsed["vertices"], triangle) for triangle in target_triangles]
            hits = _deduplicate_hits([distance for distance in distances if distance is not None], _RAY_TOLERANCE * scale)
            nearest = hits[0] if hits else None
            radius = _source_radius(scale_info, "", side, radius_axis)
            normalized = nearest / radius if nearest is not None and radius else None
            row = {"direction": direction, "hit_distances": hits, "nearest_positive_hit": nearest,
                   "source_radius": radius, "normalized_radius": normalized, "distinct_crossing_count": len(hits),
                   "nearest_radius_pass": normalized is not None and _RAY_RADIUS_MIN <= normalized <= _RAY_RADIUS_MAX,
                   "odd_crossing_pass": bool(hits) and len(hits) % 2 == 1}
            row["pass"] = row["nearest_radius_pass"] and row["odd_crossing_pass"]
            side_rays[direction_name] = row
            key = f"{side}:{direction_name}" if side else direction_name
            result["rays"][key] = row
            result["directional_radial_distances"][key] = nearest
            result["centres"][key] = _vec_add(h, _vec_scale(direction, nearest)) if nearest is not None else None
            side_pass = side_pass and row["pass"]

            section_origin = _vec_sub(h, _vec_scale(axis, 0.1 * float(scale_info.get("length") or scale))) if axis is not None else h
            section_distances = [_ray_triangle(section_origin, direction, parsed["vertices"], triangle) for triangle in target_triangles]
            section_hits = _deduplicate_hits([distance for distance in section_distances if distance is not None], _RAY_TOLERANCE * scale)
            result["section_above_H"]["rays"][key] = {
                "origin": section_origin, "direction": direction, "hit_distances": section_hits,
                "nearest_positive_hit": section_hits[0] if section_hits else None,
                "centre": _vec_add(section_origin, _vec_scale(direction, section_hits[0])) if section_hits else None,
            }
        summary_key = f"{side}:summary" if side else "summary"
        result["rays"][summary_key] = {"pass": side_pass, "H": h, "axis": axis, "directions": side_rays}
        all_sides_pass = all_sides_pass and side_pass
    result["pass"] = any_record and all_sides_pass
    result["inside_proximal_skin"] = result["pass"]
    return result


def _profile_input_check(case: Any) -> dict[str, Any]:
    keys = ("profile_selector", "profile_select", "selected_profile", "profile_formula", "formula_by_profile")
    found = [key for key in keys if _is_mapping(case) and key in case]
    return {"pass": not found, "selected_mechanism_keys": found,
            "note": "case names may identify profiles; formulas must not be selected by profile"}


def _admission_check(case: Any, levels: Any, scale_info: Mapping[str, Any]) -> dict[str, Any]:
    """Report constructor admission separately from finite renderability."""

    failures: list[Any] = []
    if _is_mapping(case) and "admission_failures" in case:
        value = case["admission_failures"]
        failures.extend(value if isinstance(value, (list, tuple)) else [value])
    if _is_mapping(levels) and "admission_failures" in levels:
        value = levels["admission_failures"]
        failures.extend(value if isinstance(value, (list, tuple)) else [value])
    if isinstance(levels, (list, tuple)):
        for mesh in levels:
            if not _is_mapping(mesh):
                continue
            value = mesh.get("admission_failures")
            if value is None and _is_mapping(mesh.get("metadata")):
                value = mesh["metadata"].get("admission_failures")
            if value is not None:
                failures.extend(value if isinstance(value, (list, tuple)) else [value])

    hip_points = scale_info.get("hip_points", {})
    radii = scale_info.get("radii", {})
    try:
        left = hip_points["left"]
        right = hip_points["right"]
        centres_distance = abs(float(right[0]) - float(left[0]))
        left_rx = _source_radius(scale_info, "", "left", "X")
        right_rx = _source_radius(scale_info, "", "right", "X")
        nominal_clearance = (centres_distance - left_rx - right_rx
                             if left_rx is not None and right_rx is not None else None)
    except Exception:
        centres_distance = left_rx = right_rx = nominal_clearance = None
    clearance_admitted = nominal_clearance is not None and nominal_clearance > 0.0
    if nominal_clearance is not None and not clearance_admitted:
        failures.append({"code": "nominal_medial_clearance", "message": "H centres must be separated beyond rx_left + rx_right"})
    return {"pass": not failures, "failures": failures, "nominal_medial_clearance": nominal_clearance,
            "centres_distance": centres_distance, "rx_left": left_rx, "rx_right": right_rx,
            "admission_rule": "centres_distance > rx_left + rx_right",
            "diagnostic_render_allowed": True}


def _level_intersection_and_geometry(level: int, parsed: Mapping[str, Any], scale_info: Mapping[str, Any]) -> dict[str, Any]:
    triangles, face_ids = _triangle_inventory(parsed)
    intersections = _intersection_report(parsed["vertices"], triangles, face_ids, parsed["face_owners"])
    dimension = _dimension_gates(parsed, scale_info, level)
    result = {"intersections": intersections, "scaled_degeneracy": dimension,
              "nonadjacent_lower_intersections": {"count": len(intersections["lower_hit_pairs"]),
                                                    "pass": intersections["available"] and not intersections["lower_hit_pairs"],
                                                    "pairs": intersections["lower_hit_pairs"]},
              "upper_only_intersections": {"count": len(intersections["upper_only_hit_pairs"]),
                                            "status": "inherited-failure" if intersections["upper_only_hit_pairs"] else "pass",
                                            "pairs": intersections["upper_only_hit_pairs"],
                                            "prohibits_full_root_claim": bool(intersections["upper_only_hit_pairs"])}}
    return result


def check_case(case: Any, levels: Any) -> dict[str, Any]:
    """Check L0/L1/L2 and return a JSON-safe diagnostic report, never raise."""

    report: dict[str, Any] = {
        "schema": "pelvis-thigh-transition/checks-v1",
        "case": _case_name(case),
        "technical": {"pass": False, "full_root_claim": False, "levels": []},
        "regional": {"lower_region": {"pass": False}, "upper_inherited": {"status": "unavailable", "pass": False}},
        "render": {"safe_levels": [], "safe": False},
        "diagnostics": [],
    }
    try:
        level_map = _normalise_levels(levels)
    except Exception as exc:
        report["diagnostics"].append(_error("invalid_levels", str(exc)))
        return _json_safe(report)
    if set(level_map) != set(_LEVELS):
        report["diagnostics"].append(_error("level_count", "evaluate must return exactly L0, L1, and L2"))

    scale_info = _source_dimensions(case)
    admission = _admission_check(case, levels, scale_info)
    report["admission"] = admission
    report["source"] = {"H_by_side": scale_info.get("H_by_side", {}), "K_by_side": scale_info.get("K_by_side", {}),
                         "axis_by_side": scale_info.get("actual_axes", {}), "r_y": scale_info.get("r_y", {}),
                         "joint_frame_hints_used": False}
    parsed_levels: dict[int, Mapping[str, Any]] = {}
    base_quad_count: int | None = None
    base_vertex_count: int | None = None
    level_pass = True
    for level in _LEVELS:
        level_report, parsed = _mesh_structural_checks(level, level_map.get(level), base_quad_count, base_vertex_count)
        if level == 0 and parsed is not None:
            base_quad_count = len(parsed["quads"])
            base_vertex_count = len(parsed["vertices"])
        if parsed is not None:
            parsed_levels[level] = parsed
            if level == 0 or base_quad_count is not None:
                geometry = _level_intersection_and_geometry(level, parsed, scale_info)
                level_report.update(geometry)
                level_report["pass"] = level_report["pass"] and geometry["scaled_degeneracy"]["pass"] \
                    and geometry["nonadjacent_lower_intersections"]["pass"]
            else:
                level_report["pass"] = False
        level_pass = level_pass and bool(level_report["pass"])
        report["technical"]["levels"].append(level_report)
        report["render"]["safe_levels"].append(bool(level_report.get("render_safe")))

    report["scale"] = {
        "S": scale_info.get("scale"),
        "inputs": {"lower_pelvis_width": scale_info.get("pelvis_width"), "hip_spacing": scale_info.get("hip_spacing"),
                    "hip_knee_distances": scale_info.get("hip_knee_distances")},
        "complete": scale_info.get("scale_inputs_complete", False),
        "named_per_case": True,
    }
    report["input_contract"] = {"profile_selection": _profile_input_check(case)}

    if parsed_levels.get(2) is not None:
        final = parsed_levels[2]
        final_exit = _exit_checks(case, final, scale_info)
        folds = _lower_fold_checks(final)
        quad_normals = _lower_quad_normal_checks(final)
        containment = _containment_checks(case, final, scale_info)
        report["technical"]["final_L2"] = {"exit_loops": final_exit, "folds": folds,
                                             "lower_quad_triangle_normals": quad_normals,
                                             "containment": containment}
        local_pass = final_exit["pass"] and folds["lower"]["pass"] and quad_normals["pass"] and containment["pass"]
    else:
        report["technical"]["final_L2"] = {"pass": False, "error": _error("missing_L2", "L2 is required for final checks")}
        local_pass = False

    lower_intersection_pass = all(
        level.get("nonadjacent_lower_intersections", {}).get("pass", False)
        for level in report["technical"]["levels"]
    ) and bool(report["technical"]["levels"])
    lower_pass = bool(level_pass and local_pass and lower_intersection_pass
                      and report["input_contract"]["profile_selection"]["pass"]
                      and admission["pass"])
    upper_hit_pairs = [
        pair
        for level in report["technical"]["levels"]
        for pair in level.get("upper_only_intersections", {}).get("pairs", [])
    ]
    report["regional"]["lower_region"] = {
        "pass": lower_pass,
        "nonadjacent_intersections": {"pass": lower_intersection_pass},
        "full_local_gates": local_pass,
    }
    report["regional"]["upper_inherited"] = {
        "status": "inherited-failure" if upper_hit_pairs else "not-reappraised",
        "intersection_pairs": upper_hit_pairs,
        "computed_failures": upper_hit_pairs,
        "prohibits_full_root_claim": True,
        "does_not_change_lower_success": True,
    }
    report["technical"]["pass"] = lower_pass
    report["technical"]["lower_region_pass"] = lower_pass
    # This experiment does not re-appraise the complete upper root.  Even a
    # clean inherited diagnostic therefore cannot become a whole-root claim.
    report["technical"]["full_root_claim"] = False
    report["render"]["safe"] = bool(report["render"]["safe_levels"]) and all(report["render"]["safe_levels"])
    if not admission["pass"]:
        report["diagnostics"].append(_error("admission_failure", "constructor/input admission failed; finite diagnostic rendering remains allowed",
                                             failures=admission["failures"]))
    if not report["render"]["safe"]:
        report["diagnostics"].append(_error("render_unsafe", "one or more levels are not finite, indexed, and non-degenerate"))
    if upper_hit_pairs:
        report["diagnostics"].append(_error("upper_inherited_intersection", "upper-only intersection blocks a full-root claim", pairs=upper_hit_pairs))
    return _json_safe(report)


def _centroids_for_exits(case: Any, levels: Any) -> dict[str, tuple[float, float, float]]:
    level_map = _normalise_levels(levels)
    _, parsed = _mesh_structural_checks(2, level_map.get(2), None)
    if parsed is None:
        return {}
    names = _exit_loop_names(case, parsed)
    return {name: _loop_geometry(parsed["vertices"], parsed["loops"][name])[0] for name in names}


def _declared_response(case: Any) -> tuple[str | None, Mapping[str, Any]]:
    if not _is_mapping(case):
        return None, {}
    value = next((case[key] for key in ("declared_response", "expected_response", "perturbation") if key in case), None)
    if value is None and _is_mapping(case.get("provenance")):
        value = case["provenance"].get("expected_change")
    if isinstance(value, str):
        return value, {}
    if _is_mapping(value):
        kind = _lookup(value, "kind", "type", "name", "response", "direction")
        return str(kind) if kind is not None else None, value
    return None, {}


def _response_delta(response: Mapping[str, Any], loop_name: str, side: str | None) -> tuple[float, float, float] | None:
    value = _side_value(_lookup(response, "delta", "offset", "translation", "expected_delta"), loop_name, side)
    try:
        return _vector(value, "declared response delta")
    except Exception:
        return None


def _response_kind(kind: str) -> str:
    return {
        "neutral_pelvis_width_plus_10pct": "pelvis_width",
        "neutral_left_spacing_minus_005": "centre_offset",
        "neutral_left_direction_tilt_5deg": "direction_tilt",
        "neutral_left_front_offset_plus_005": "centre_offset",
        "neutral_left_asymmetric_xz_and_radius": "centre_offset",
        "neutral_invalid_close_thick": "negative",
    }.get(kind, "unknown")


def _response_source_axis(case: Any, side: str | None) -> tuple[float, float, float] | None:
    info = _source_dimensions(case)
    actual = info.get("actual_axes", {})
    if side in actual:
        return actual[side]
    return info.get("axis")


def compare_perturbation(base_case: Any, base_levels: Any, case: Any, levels: Any) -> dict[str, Any]:
    """Check only the response declared by a pre-declared perturbation."""

    result: dict[str, Any] = {"schema": "pelvis-thigh-transition/perturbation-checks-v1", "pass": False,
                              "declared": {}, "checks": {}, "diagnostics": []}
    try:
        declared_kind, response = _declared_response(case)
        case_kind = _response_kind(_case_name(case))
        result["declared"] = {"case_id": _case_name(case), "kind": declared_kind, "test_kind": case_kind}
        if case_kind == "unknown":
            result["diagnostics"].append(_error("unknown_perturbation_id", "only the six registered perturbation IDs are accepted"))
            return _json_safe(result)
        if declared_kind is None:
            result["diagnostics"].append(_error("missing_declared_response", "perturbation response must be explicitly declared"))
            return _json_safe(result)
        base_info = _source_dimensions(base_case)
        new_info = _source_dimensions(case)
        scale = new_info.get("scale") or base_info.get("scale")
        result["scale"] = scale
        if not _finite(scale) or float(scale) <= 0.0:
            result["diagnostics"].append(_error("missing_scale", "perturbation comparison requires case scale S"))
            return _json_safe(result)
        scale = float(scale)
        base_map = _normalise_levels(base_levels)
        new_map = _normalise_levels(levels)
        _, base_parsed = _mesh_structural_checks(2, base_map.get(2), None)
        _, new_parsed = _mesh_structural_checks(2, new_map.get(2), None)
        if base_parsed is None or new_parsed is None:
            result["diagnostics"].append(_error("missing_L2", "perturbation comparison requires both actual L2 meshes"))
            return _json_safe(result)
        base_centres = {name: _loop_geometry(base_parsed["vertices"], base_parsed["loops"][name])[0]
                        for name in _exit_loop_names(base_case, base_parsed)}
        new_centres = {name: _loop_geometry(new_parsed["vertices"], new_parsed["loops"][name])[0]
                       for name in _exit_loop_names(case, new_parsed)}
        names = sorted(set(base_centres).intersection(new_centres))
        response_kind = case_kind
        centroid_checks: list[dict[str, Any]] = []
        if response_kind in {"centre_offset", "pelvis_width"}:
            for name in names:
                side = "left" if "left" in name.lower() else "right" if "right" in name.lower() else None
                expected_delta = _response_delta(response, name, side)
                if expected_delta is None and response_kind == "centre_offset":
                    base_h = base_info.get("H_by_side", {}).get(side)
                    new_h = new_info.get("H_by_side", {}).get(side)
                    if base_h is not None and new_h is not None:
                        expected_delta = _vec_sub(new_h, base_h)
                if expected_delta is None and response_kind == "pelvis_width":
                    expected_delta = (0.0, 0.0, 0.0)
                observed_delta = _vec_sub(new_centres[name], base_centres[name])
                error = _norm(_vec_sub(observed_delta, expected_delta)) if expected_delta is not None else None
                centroid_checks.append({"loop": name, "observed_delta": observed_delta, "expected_delta": expected_delta,
                                        "error": error, "pass": error is not None and error <= _POSITION_TOLERANCE * scale})
        result["checks"]["exit_centroid_response"] = {"checks": centroid_checks, "applicable": response_kind in {"centre_offset", "pelvis_width"},
                                                        "pass": True if response_kind not in {"centre_offset", "pelvis_width"}
                                                        else bool(centroid_checks) and all(row["pass"] for row in centroid_checks)}

        if _case_name(case) == "neutral_left_asymmetric_xz_and_radius":
            span_rows = []
            source_ratio = (case["components"]["hips.left.r_x"]
                            / base_case["components"]["hips.left.r_x"])
            for name in names:
                if "left" not in name.lower():
                    continue
                half_spans = []
                for parsed, centres in ((base_parsed, base_centres), (new_parsed, new_centres)):
                    x_axis = _unit(_vector(parsed["frames"]["left"]["X"], "L2 frame X"), "L2 frame X")
                    projections = [_dot(_vec_sub(parsed["vertices"][index], centres[name]), x_axis)
                                   for index in parsed["loops"][name]]
                    half_spans.append(0.5 * (max(projections) - min(projections)))
                old_span, new_span = half_spans
                expected_span = old_span * source_ratio
                error = abs(new_span - expected_span)
                span_rows.append({"loop": name, "base_half_span": old_span,
                                  "actual_half_span": new_span, "expected_half_span": expected_span,
                                  "source_radius_ratio": source_ratio,
                                  "actual_span_ratio": new_span / old_span if old_span > 0.0 else None,
                                  "error": error, "tolerance": _POSITION_TOLERANCE * scale,
                                  "pass": old_span > 0.0 and source_ratio > 1.0 and new_span > old_span
                                  and error <= _POSITION_TOLERANCE * scale})
            result["checks"]["asymmetric_lateral_span_response"] = {
                "checks": span_rows, "pass": bool(span_rows) and all(row["pass"] for row in span_rows)}

        actual_axis_checks: list[dict[str, Any]] = []
        if response_kind == "direction_tilt":
            for name in names:
                side = "left" if "left" in name.lower() else "right" if "right" in name.lower() else None
                expected_axis = _response_source_axis(case, side)
                observed_axis = _vec_scale(_loop_geometry(new_parsed["vertices"], new_parsed["loops"][name])[1], -1.0)
                angle = _angle_radians(observed_axis, expected_axis) if observed_axis is not None and expected_axis is not None else None
                actual_axis_checks.append({"loop": name, "observed_axis": observed_axis, "actual_new_H_to_K": expected_axis,
                                           "angle_error_radians": angle,
                                           "pass": angle is not None and angle <= _EXIT_DIRECTION_TOLERANCE})
            result["checks"]["direction_tilt_response"] = {"checks": actual_axis_checks,
                                                              "pass": bool(actual_axis_checks) and all(row["pass"] for row in actual_axis_checks)}

        if response_kind == "pelvis_width":
            base_exit_pass = result["checks"]["exit_centroid_response"]["pass"]
            base_containment = _containment_checks(base_case, base_parsed, base_info)
            new_containment = _containment_checks(case, new_parsed, new_info)
            base_section = base_containment.get("section_above_H", {}).get("rays", {})
            new_section = new_containment.get("section_above_H", {}).get("rays", {})
            extent_rows = []
            for side_name in sorted(set(base_section).intersection(new_section)):
                old = base_section.get(side_name, {}).get("nearest_positive_hit")
                new = new_section.get(side_name, {}).get("nearest_positive_hit")
                extent_rows.append({"direction": side_name, "base": old, "perturbed": new,
                                    "increase": new - old if _finite(new) and _finite(old) else None})
            outer_rows = [row for row in extent_rows if row["direction"].endswith(":+X") or row["direction"].endswith(":-X")]
            extent_pass = any(row["increase"] is not None and row["increase"] >= _PELVIS_WIDTH_RESPONSE_FLOOR * scale
                              for row in outer_rows)
            result["checks"]["pelvis_width_response"] = {"exits_unchanged": base_exit_pass, "ray_extent": extent_rows,
                                                            "at_least_one_side_increases": extent_pass,
                                                            "pass": base_exit_pass and extent_pass}

        coordinates_differ = False
        try:
            base_l2 = _normalise_levels(base_levels)[2]
            new_l2 = _normalise_levels(levels)[2]
            base_vertices = _as_sequence(base_l2.get("vertices"), "base L2 vertices") if _is_mapping(base_l2) else []
            new_vertices = _as_sequence(new_l2.get("vertices"), "new L2 vertices") if _is_mapping(new_l2) else []
            coordinates_differ = base_vertices != new_vertices
        except Exception:
            coordinates_differ = False
        result["checks"]["exported_coordinate_arrays_differ"] = {"pass": coordinates_differ}

        negative = response_kind == "negative"
        if negative:
            points = new_info.get("hip_points", {})
            clearance = _pair_distance(points, ("left",), ("right",))
            left_radius = _source_radius(new_info, "left_exit", "left", "X")
            right_radius = _source_radius(new_info, "right_exit", "right", "X")
            admission = clearance is not None and left_radius is not None and right_radius is not None and clearance > left_radius + right_radius
            rejected = clearance is not None and left_radius is not None and right_radius is not None and clearance <= left_radius + right_radius
            result["checks"]["negative_medial_clearance_admission"] = {"centres_distance": clearance,
                                                                          "rx_left": left_radius, "rx_right": right_radius,
                                                                          "admission_rule": "centres_distance > rx_left + rx_right",
                                                                          "constructor_admitted": admission,
                                                                          "expected_negative_success": rejected,
                                                                          "anatomy_pass": False,
                                                                          "pass": rejected}

        applicable = [value.get("pass") for value in result["checks"].values()]
        result["pass"] = bool(applicable) and all(applicable)
        if negative and result["checks"].get("negative_medial_clearance_admission", {}).get("pass"):
            result["status"] = "expected-negative-success; not an anatomy pass"
        return _json_safe(result)
    except Exception as exc:
        result["diagnostics"].append(_error("perturbation_checker_failure", str(exc)))
        return _json_safe(result)


__all__ = ["check_case", "compare_perturbation"]

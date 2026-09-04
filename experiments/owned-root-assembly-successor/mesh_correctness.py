"""Fail-closed topology, geometry, and intersection checks."""

from __future__ import annotations

import itertools
import math
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import NoReturn

_FIXED_I0 = float.fromhex("0x1.b7cdfd9d7bdbbp-34")
_FIXED_D = float.fromhex("0x1.0000000000000p-46")
_FIXED_S = float.fromhex("0x1.c666666666666p+1")
_FIXED_T = float.fromhex("0x1.c666666666666p-45")
_FIXED_PI = float.fromhex("0x1.921fb54442d18p+1")
_FIXED_FOLD_LIMITS = (90.0, 60.0, 30.0)
_MAX_TRIANGLES = 4096
_MAX_QUADS = _MAX_TRIANGLES // 2
_MAX_BASE_CONTROLS, _MAX_BASE_QUADS = 128, 120
_MAX_CANDIDATES = 1_000_000
_MAX_CLASSIFICATION_DETAILS, _MAX_DIAGNOSTIC_EVIDENCE = 4096, 64
_PORT_ORIENTATION, _PORT_AREA_RATIO, _PORT_CO_NORMAL = 0.99, 0.0001, 0.80
_FINAL_CLASSIFICATION_STAGES = ("aabb-disjoint", "sat-disjoint", "hit", "point-only", "excluded-adjacent")

I0 = INTERSECTION_TOLERANCE = _FIXED_I0
D = DEGENERACY_FLOOR = _FIXED_D
S, T, PI = _FIXED_S, _FIXED_T, _FIXED_PI
FOLD_LIMITS_DEGREES = _FIXED_FOLD_LIMITS
MAX_TRIANGLES, MAX_CANDIDATES = _MAX_TRIANGLES, _MAX_CANDIDATES
_STRUCTURAL_FLOORS = {
    0: {"edge_length": 0.10, "triangle_area": 0.010, "quad_area": 0.010},
    1: {"edge_length": 0.04, "triangle_area": 0.002, "quad_area": 0.002},
    2: {"edge_length": 0.02, "triangle_area": 0.0005, "quad_area": 0.0005},
}
STRUCTURAL_FLOORS = {level: dict(values) for level, values in _STRUCTURAL_FLOORS.items()}
_THRESHOLD_RECORDS = tuple(
    {"threshold_id": f"threshold.intersection.L{level}.broad_phase_candidate_count",
     "relation": "le", "lower": None, "upper": _MAX_CANDIDATES, "unit": "count"}
    for level in range(3)
)

class MeshCorrectnessError(ValueError):
    """A deterministic, fail-closed mesh correctness failure."""

def _fail(message: str) -> NoReturn:
    raise MeshCorrectnessError(message)
def _finite_float(value, label: str) -> float:
    if type(value) is not float or not math.isfinite(value):
        _fail(f"{label} must be a finite binary64 value")
    return value
def _integer(value, label: str) -> int:
    if type(value) is not int:
        _fail(f"{label} must be an integer")
    return value
def _sequence(raw, label: str, cap=None):
    if type(raw) not in (list, tuple):
        _fail(f"{label} must be an exact list or tuple")
    if cap is not None and len(raw) > cap:
        _fail(f"{label.rstrip('s')} cap exceeded: {len(raw)} > {cap}")
    return raw
def _named_mapping(raw, label, count=None):
    if type(raw) is not dict or not raw:
        _fail(f"{label} must be a non-empty exact dict")
    if any(type(name) is not str or not name for name in raw):
        _fail(f"{label} names must be non-empty strings")
    if count is not None and len(raw) != count:
        _fail(f"exactly {count} {label} are required")
    return raw
def _vec(value, label: str) -> tuple[float, float, float]:
    values = _sequence(value, label)
    if len(values) != 3:
        _fail(f"{label} must be a finite 3-vector")
    return tuple(_finite_float(item, f"{label}[{i}]") for i, item in enumerate(values))
def _points(raw):
    values = _sequence(raw, "vertices")
    if not values:
        _fail("vertices must not be empty")
    return tuple(_vec(value, f"vertices[{i}]") for i, value in enumerate(values))
def _simple_indices(raw, vertex_count, label):
    values = tuple(_integer(value, label) for value in _sequence(raw, label))
    if (len(values) < 3 or len(set(values)) != len(values)
            or any(index < 0 or index >= vertex_count for index in values)):
        _fail(f"{label} must be simple and in range")
    return values
def _indexed_rows(raw, width, vertex_count, label, cap=None):
    rows = _sequence(raw, label, cap)
    result = []
    for face_index, row in enumerate(rows):
        values = _sequence(row, f"{label}[{face_index}]")
        if len(values) != width:
            _fail(f"{label}[{face_index}] must have {width} indices")
        face = tuple(_integer(value, f"{label}[{face_index}]") for value in values)
        if any(index < 0 or index >= vertex_count for index in face):
            _fail(f"{label} index out of range at {face_index}")
        if len(set(face)) != width:
            _fail(f"{label[:-1]} has repeated vertex index at {face_index}")
        result.append(face)
    return tuple(result)
def _canonical_cycle(face):
    return min(sequence[i:] + sequence[:i]
               for sequence in (tuple(face), tuple(reversed(face)))
               for i in range(len(face)))
def _quads(raw, vertex_count):
    faces = _indexed_rows(raw, 4, vertex_count, "quads", _MAX_QUADS)
    keys = tuple(_canonical_cycle(face) for face in faces)
    if len(set(keys)) != len(keys):
        _fail("duplicate quad, including reversed/cyclic duplicate")
    return faces
def _add_vec(a, b): return tuple(a[i] + b[i] for i in range(3))
def _sub_vec(a, b): return tuple(a[i] - b[i] for i in range(3))
def _dot_vec(a, b): return (a[0] * b[0] + a[1] * b[1]) + a[2] * b[2]
def _cross_vec(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])
def _norm_vec(value): return math.sqrt(_dot_vec(value, value))
def _normalize_vec(value, label):
    length = _norm_vec(value)
    if not math.isfinite(length) or length <= 0.0:
        _fail(f"{label} must be finite and nonzero")
    return tuple(component / length for component in value)
def add(a, b): return _add_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def sub(a, b): return _sub_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def dot(a, b): return _dot_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def cross(a, b): return _cross_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def norm(value): return _norm_vec(_vec(value, "vector"))
def normalize(value): return _normalize_vec(_vec(value, "vector"), "vector normal")
def _normalize_points(points):
    lower = tuple(min(point[i] for point in points) for i in range(3))
    extent = tuple(max(point[i] for point in points) - lower[i] for i in range(3))
    scale = _norm_vec(extent)
    if not math.isfinite(scale) or scale <= 0.0:
        _fail("mesh normalization scale must be finite and positive")
    normalized = tuple(tuple((point[i] - lower[i]) / scale for i in range(3))
                       for point in points)
    if any(not math.isfinite(value) for point in normalized for value in point):
        _fail("normalized coordinates must be finite")
    return normalized, scale
def interval_disjoint(lower_a, upper_a, lower_b, upper_b):
    values = tuple(_finite_float(value, label) for value, label in zip(
        (lower_a, upper_a, lower_b, upper_b),
        ("lower_A", "upper_A", "lower_B", "upper_B")))
    return _interval_disjoint(*values)
def _interval_disjoint(lower_a, upper_a, lower_b, upper_b):
    return (upper_a < lower_b - _FIXED_I0
            or upper_b < lower_a - _FIXED_I0)
def _edge_incidence(faces):
    result = defaultdict(list)
    for face_index, face in enumerate(faces):
        for slot, start in enumerate(face):
            end = face[(slot + 1) % len(face)]
            result[(min(start, end), max(start, end))].append((face_index, start, end))
    return result
def _validate_loops(raw, vertex_count):
    if raw is None:
        return {}
    raw = _named_mapping(raw, "boundary loops")
    result, used = {}, set()
    for name in sorted(raw, key=lambda value: value.encode("utf-8")):
        loop = _simple_indices(raw[name], vertex_count, f"boundary loop {name}")
        if used.intersection(loop):
            _fail(f"boundary loops overlap at {name}")
        used.update(loop)
        result[name] = loop
    return result
def _cyclic_equal(actual, expected, reverse=False):
    target = tuple(reversed(expected)) if reverse else tuple(expected)
    return len(actual) == len(target) and any(actual == target[i:] + target[:i] for i in range(len(target)))
def _boundary_cycles(edges):
    outgoing = defaultdict(list)
    for _, start, end in edges:
        outgoing[start].append(end)
    if any(len(values) != 1 for values in outgoing.values()):
        _fail("boundary edges do not form directed cycles")
    next_vertex = {start: values[0] for start, values in outgoing.items()}
    remaining, cycles = set(next_vertex), []
    while remaining:
        start = current = min(remaining)
        cycle = []
        while current in remaining:
            remaining.remove(current)
            cycle.append(current)
            current = next_vertex[current]
        if current != start or len(cycle) < 3:
            _fail("boundary cycle is not closed")
        cycles.append(tuple(cycle))
    return tuple(sorted(cycles, key=lambda cycle: min(cycle)))

@dataclass(frozen=True)
class TopologyReport:
    vertex_count: int
    edge_count: int
    face_count: int
    boundary_edge_count: int
    boundary_components: int
    connected_components: int
    euler: int
    non_manifold_edges: int
    orientation_conflicts: int
    boundary_lengths: tuple[int, ...]
    valence_inventory: tuple[tuple[int, int], ...]

    @property
    def euler_characteristic(self):
        return self.euler
def _connected_components(adjacency, vertex_count):
    unseen, components = set(range(vertex_count)), 0
    while unseen:
        todo = [unseen.pop()]
        components += 1
        while todo:
            neighbours = adjacency[todo.pop()].intersection(unseen)
            unseen.difference_update(neighbours)
            todo.extend(neighbours)
    return components
def _topology_report(vertex_count, quads, loops, expected_faces):
    if expected_faces is not None:
        expected = _indexed_rows(
            expected_faces, 4, vertex_count, "expected_faces", _MAX_QUADS)
        if quads != expected:
            _fail("face winding/catalog does not match exactly")
    incidence = _edge_incidence(quads)
    non_manifold = sum(len(items) > 2 for items in incidence.values())
    if non_manifold:
        _fail(f"non-manifold edge count {non_manifold}")
    conflicts = sum(len(items) == 2 and items[0][1:] == items[1][1:]
                    for items in incidence.values())
    if conflicts:
        _fail(f"orientation conflict count {conflicts}")
    boundary = [items[0] for items in incidence.values() if len(items) == 1]
    cycles = _boundary_cycles(boundary) if boundary else ()
    if loops:
        expected = tuple(sorted(loops.values(), key=lambda cycle: min(cycle)))
        if len(cycles) != len(expected) or any(
                sum(_cyclic_equal(actual, wanted) for wanted in expected) != 1
                for actual in cycles):
            _fail("boundary cycle does not match a declared loop orientation")
    adjacency, valence, used = defaultdict(set), defaultdict(int), set()
    for first, second in incidence:
        adjacency[first].add(second)
        adjacency[second].add(first)
        valence[first] += 1
        valence[second] += 1
        used.update((first, second))
    if len(used) != vertex_count:
        _fail("unused vertex IDs are not permitted")
    components = _connected_components(adjacency, vertex_count)
    if components != 1:
        _fail("surface is not connected")
    return TopologyReport(
        vertex_count, len(incidence), len(quads), len(boundary), len(cycles), components,
        vertex_count - len(incidence) + len(quads), non_manifold, conflicts,
        tuple(len(cycle) for cycle in cycles), tuple(sorted(valence.items())))

def validate_topology(vertex_count, faces, boundary_loops=None, expected_faces=None):
    _integer(vertex_count, "vertex_count")
    if vertex_count <= 0:
        _fail("vertex_count must be positive")
    quads = _quads(faces, vertex_count)
    return _topology_report(vertex_count, quads, _validate_loops(boundary_loops, vertex_count),
                            expected_faces)
def _triangle_normal(triangle, points):
    return _cross_vec(_sub_vec(points[triangle[1]], points[triangle[0]]), _sub_vec(points[triangle[2]], points[triangle[0]]))
def _quad_data(quad, points):
    first, second, third, fourth = (points[index] for index in quad)
    normal_a = _cross_vec(_sub_vec(second, first), _sub_vec(third, first))
    normal_b = _cross_vec(_sub_vec(third, first), _sub_vec(fourth, first))
    area = 0.5 * _norm_vec(normal_a) + 0.5 * _norm_vec(normal_b)
    return area, _normalize_vec(_add_vec(normal_a, normal_b), "quad normal")
def _loop_geometry(selected):
    centroid = (0.0, 0.0, 0.0)
    for point in selected:
        centroid = _add_vec(centroid, point)
    centroid = tuple(value / len(selected) for value in centroid)
    area = (0.0, 0.0, 0.0)
    for index, point in enumerate(selected):
        area = _add_vec(area, _cross_vec(_sub_vec(point, centroid),
                                         _sub_vec(selected[(index + 1) % len(selected)], centroid)))
    return centroid, tuple(0.5 * value for value in area)
def port_loop_metrics(points, loop, outward_direction, adjacent_normals):
    points = _points(points)
    loop = _simple_indices(loop, len(points), "port loop")
    direction = _normalize_vec(_vec(outward_direction, "port direction"), "port direction")
    selected = tuple(points[index] for index in loop)
    centroid, area = _loop_geometry(selected)
    area_unit = _normalize_vec(area, "port area normal")
    normals = tuple(_normalize_vec(_vec(value, "adjacent face normal"),
                                   "adjacent face normal")
                    for value in _sequence(adjacent_normals, "adjacent normals"))
    if len(normals) != len(loop):
        _fail("port adjacent-normal count must equal loop edge count")
    result = {
        "orientation": -_dot_vec(area_unit, direction),
        "planarity": max(abs(_dot_vec(_sub_vec(point, centroid), area_unit))
                         for point in selected),
        "area_ratio": _norm_vec(area) / (_FIXED_S * _FIXED_S),
        "co_normal": min(
            _dot_vec(_normalize_vec(_cross_vec(
                _normalize_vec(_sub_vec(selected[(i + 1) % len(selected)], selected[i]),
                               "port tangent"), normal), "port co-normal"), direction)
            for i, normal in enumerate(normals)),
    }
    if any(not math.isfinite(value) for value in result.values()):
        _fail("port metrics must be finite")
    return result

def validate_port_loop(points, loop, outward_direction, adjacent_normals):
    metrics = port_loop_metrics(points, loop, outward_direction, adjacent_normals)
    if metrics["orientation"] < _PORT_ORIENTATION:
        _fail("port orientation gate failed")
    if metrics["planarity"] > _FIXED_T:
        _fail("port planarity gate failed")
    if metrics["area_ratio"] < _PORT_AREA_RATIO:
        _fail("port area-ratio gate failed")
    if metrics["co_normal"] < _PORT_CO_NORMAL:
        _fail("port induced co-normal gate failed")
    return metrics

def _tagged_trace(raw, label):
    items = _sequence(raw, label)
    result, seen = [], set()
    for item in items:
        if type(item) not in (tuple, list) or len(item) != 2:
            _fail(f"{label} contains an invalid tagged sample")
        tag, point = item
        try:
            if tag in seen:
                _fail(f"{label} contains duplicate tags")
            seen.add(tag)
        except TypeError as exc:
            raise MeshCorrectnessError(f"{label} contains an unhashable tag") from exc
        result.append((tag, _vec(point, f"{label}[{tag!r}]")))
    if not result:
        _fail(f"{label} must not be empty")
    return tuple(result)
def junction_continuity_metrics(trace_a, trace_b):
    first, second = _tagged_trace(trace_a, "trace A"), _tagged_trace(trace_b, "trace B")
    first_tags, second_tags = tuple(tag for tag, _ in first), tuple(tag for tag, _ in second)
    if set(first_tags) != set(second_tags):
        _fail("junction trace tag sets differ")
    if not _cyclic_equal(first_tags, second_tags, reverse=True):
        _fail("junction trace directions are not opposite")
    first_values, second_values = dict(first), dict(second)
    try:
        tags = sorted(first_values)
    except TypeError as exc:
        raise MeshCorrectnessError("junction trace tags must be orderable") from exc
    residual = max(max(abs(first_values[tag][axis] - second_values[tag][axis])
                       for axis in range(3)) for tag in tags)
    if not math.isfinite(residual) or residual > _FIXED_T:
        _fail("junction coordinate residual exceeds tolerance")
    return {"tag_identity": True, "opposite_trace_direction": True,
            "coordinate_residual": residual}
def fold_angle_degrees(normal_a, normal_b):
    first = _normalize_vec(_vec(normal_a, "fold normal A"), "fold normal A")
    second = _normalize_vec(_vec(normal_b, "fold normal B"), "fold normal B")
    cosine = max(-1.0, min(1.0, _dot_vec(first, second)))
    angle = math.acos(cosine)
    first_step = angle * 180.0
    return first_step / _FIXED_PI
def validate_fold(normal_a, normal_b, level):
    level = _integer(level, "fold level")
    if level not in range(3):
        _fail("fold level must be 0, 1, or 2")
    angle = fold_angle_degrees(normal_a, normal_b)
    if not angle < _FIXED_FOLD_LIMITS[level]:
        _fail(f"fold angle {angle!r} is not below {_FIXED_FOLD_LIMITS[level]!r}")
    return angle
def _validate_junction_traces(raw):
    raw = _named_mapping(raw, "junction traces", 7)
    result = {}
    for name in sorted(raw, key=lambda value: value.encode("utf-8")):
        pair = _sequence(raw[name], f"{name} trace pair")
        if len(pair) != 2:
            _fail(f"{name} requires two traces")
        result[name] = tuple(_tagged_trace(value, f"{name}.{side}")
                             for side, value in zip(("A", "B"), pair))
    return result
def _face_owners(raw, face_count):
    owners = _sequence(raw, "face_owners", _MAX_QUADS)
    if len(owners) != face_count or any(type(owner) is not str or not owner for owner in owners):
        _fail("face_owners must contain one non-empty string per face")
    return owners
def _boundary_normals(loops, incidence, quad_normals):
    result = {}
    for name, loop in loops.items():
        normals = []
        for slot, start in enumerate(loop):
            end = loop[(slot + 1) % len(loop)]
            uses = incidence.get((min(start, end), max(start, end)), ())
            if len(uses) != 1:
                _fail(f"{name} boundary edge is not uniquely derived")
            normals.append(quad_normals[uses[0][0]])
        result[name] = tuple(normals)
    return result
def _run_fold_gates(incidence, owners, quad_normals, level):
    count = 0
    for uses in incidence.values():
        if len(uses) == 2 and owners[uses[0][0]] != owners[uses[1][0]]:
            validate_fold(quad_normals[uses[0][0]], quad_normals[uses[1][0]], level)
            count += 1
    return count
def _aabb(points, triangle):
    corners = tuple(points[index] for index in triangle)
    return (tuple(min(point[i] for point in corners) for i in range(3))
            + tuple(max(point[i] for point in corners) for i in range(3)))
def _shared_edge_direction(triangle, shared):
    shared = set(shared)
    for i, start in enumerate(triangle):
        end = triangle[(i + 1) % 3]
        if {start, end} == shared:
            return start, end
    _fail("shared edge is absent")
def _axis_list(first, second):
    edges_a = tuple(_sub_vec(first[(i + 1) % 3], first[i]) for i in range(3))
    edges_b = tuple(_sub_vec(second[(i + 1) % 3], second[i]) for i in range(3))
    normal_a = _cross_vec(_sub_vec(first[1], first[0]), _sub_vec(first[2], first[0]))
    normal_b = _cross_vec(_sub_vec(second[1], second[0]), _sub_vec(second[2], second[0]))
    return ((normal_a, normal_b)
            + tuple(_cross_vec(a, b) for a in edges_a for b in edges_b)
            + tuple(_cross_vec(normal_a, edge) for edge in edges_a)
            + tuple(_cross_vec(normal_b, edge) for edge in edges_b))
def _sat_disjoint(first, second):
    for axis in _axis_list(first, second):
        length = _norm_vec(axis)
        if not math.isfinite(length):
            _fail("SAT axis must be finite")
        if length <= _FIXED_D:
            continue
        unit = _normalize_vec(axis, "SAT axis")
        projections = tuple(_dot_vec(point, unit) for point in first + second)
        if not all(math.isfinite(value) for value in projections):
            _fail("SAT projections must be finite")
        if _interval_disjoint(min(projections[:3]), max(projections[:3]),
                              min(projections[3:]), max(projections[3:])):
            return True
    return False
def _rational(value): return Fraction(0, 1) if value == 0.0 else Fraction(*value.as_integer_ratio())
def _ray_difference(first, second): return tuple(_rational(first[i]) - _rational(second[i]) for i in range(3))
def _active_solution(rays, subset):
    matrix = [[rays[index][row] for index in subset] + [Fraction(0, 1)]
              for row in range(3)]
    matrix.append([Fraction(1, 1) for _ in subset] + [Fraction(1, 1)])
    for pivot_row, column in enumerate(range(len(subset))):
        pivot = next((row for row in range(pivot_row, 4) if matrix[row][column]), None)
        if pivot is None:
            return None
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        divisor = matrix[pivot_row][column]
        matrix[pivot_row] = [value / divisor for value in matrix[pivot_row]]
        for row in range(4):
            if row != pivot_row and matrix[row][column]:
                factor = matrix[row][column]
                matrix[row] = [left - factor * right
                               for left, right in zip(matrix[row], matrix[pivot_row])]
    if any(not any(row[:-1]) and row[-1] for row in matrix):
        return None
    solution = [Fraction(0, 1)] * 4
    for row, column in enumerate(range(len(subset))):
        solution[subset[column]] = matrix[row][-1]
    if (any(value < 0 for value in solution)
            or solution[0] + solution[1] <= 0
            or solution[2] + solution[3] <= 0):
        return None
    return tuple(solution)
def shared_one_intersects(shared, a0, a1, b0, b1):
    values = tuple(_vec(value, label) for value, label in (
        (shared, "shared point"), (a0, "A0"), (a1, "A1"), (b0, "B0"), (b1, "B1")))
    shared, a0, a1, b0, b1 = values
    rays = (_ray_difference(a0, shared), _ray_difference(a1, shared),
            _ray_difference(shared, b0), _ray_difference(shared, b1))
    if any(not any(value for value in ray) for ray in rays):
        _fail("shared-one classifier received a zero ray")
    return any(_active_solution(rays, subset) is not None
               for size in (2, 3, 4)
               for subset in itertools.combinations(range(4), size))
def classify_shared_one(shared, a0, a1, b0, b1): return "hit" if shared_one_intersects(shared, a0, a1, b0, b1) else "point-only"
def _classify_shared_one_triangles(first, second, points):
    shared = next(index for index in first if index in second)
    a = [index for index in first if index != shared]
    b = [index for index in second if index != shared]
    return shared_one_intersects(points[shared], points[a[0]], points[a[1]],
                                 points[b[0]], points[b[1]])
def _intersection_inputs(vertices, triangles):
    points = _points(vertices)
    faces = _indexed_rows(triangles, 3, len(points), "triangles", _MAX_TRIANGLES)
    normalized, scale = _normalize_points(points)
    for index, face in enumerate(faces):
        length = _norm_vec(_triangle_normal(face, normalized))
        if not math.isfinite(length) or length <= _FIXED_D:
            _fail(f"normalized triangle normal degeneracy at {index}")
    bounds = tuple(_aabb(normalized, face) for face in faces)
    return faces, normalized, scale, bounds, tuple(frozenset(face) for face in faces)
def _aabb_disjoint(first, second): return any(_interval_disjoint(first[i], first[i + 3], second[i], second[i + 3]) for i in range(3))
def _pair_status(first_index, second_index, faces, normalized, bounds, face_sets):
    pair = (first_index, second_index)
    common = face_sets[first_index].intersection(face_sets[second_index])
    if len(common) == 3:
        _fail(f"duplicate triangle pair {pair}")
    if len(common) == 2:
        first_edge = _shared_edge_direction(faces[first_index], common)
        second_edge = _shared_edge_direction(faces[second_index], common)
        if first_edge != (second_edge[1], second_edge[0]):
            _fail(f"shared-two edge direction conflict at pair {pair}")
        return "excluded-adjacent"
    if len(common) == 1:
        if normalized is None:
            return "shared-one"
        hit = _classify_shared_one_triangles(faces[first_index], faces[second_index], normalized)
        return "hit" if hit else "point-only"
    return "aabb-disjoint" if _aabb_disjoint(bounds[first_index], bounds[second_index]) else "candidate"
def _record_pair_policy(triangle_count, first, second, ordinal, stage, class_counts):
    expected_ordinal = (first * (2 * triangle_count - first - 1) // 2
                        + second - first - 1)
    if ordinal != expected_ordinal:
        _fail("intersection pair coverage is not exhaustive reference order")
    if stage not in _FINAL_CLASSIFICATION_STAGES:
        _fail("intersection pair has an invalid classification")
    class_counts[stage] += 1
def _append_candidate(result, pair, cap):
    if len(result) >= cap:
        _fail(f"AABB candidate cap exceeded: >{cap}")
    result.append(pair)
def _append_bounded(result, value):
    if len(result) < _MAX_DIAGNOSTIC_EVIDENCE:
        result.append(value)
def _collect_candidate_pairs(faces, bounds, face_sets, cap):
    cap = _integer(cap, "candidate cap")
    if cap <= 0:
        _fail("candidate cap must be a positive integer")
    result = []
    for first in range(len(faces)):
        for second in range(first + 1, len(faces)):
            if _pair_status(first, second, faces, None, bounds, face_sets) == "candidate":
                _append_candidate(result, (first, second), cap)
    return tuple(result)
def _enumerate_fixture_candidates(vertices, triangles, cap):
    """Fixture-only cap injection. Production always uses the fixed cap."""
    faces, _, _, bounds, face_sets = _intersection_inputs(vertices, triangles)
    return _collect_candidate_pairs(faces, bounds, face_sets, cap)
def enumerate_broad_phase_candidates(points, triangles):
    faces, _, _, bounds, face_sets = _intersection_inputs(points, triangles)
    return _collect_candidate_pairs(faces, bounds, face_sets, _MAX_CANDIDATES)
def intersection_diagnostics(vertices, triangles, *, include_classifications=False):
    if type(include_classifications) is not bool:
        _fail("include_classifications must be a boolean")
    faces, normalized, scale, bounds, face_sets = _intersection_inputs(vertices, triangles)
    expected_pairs = len(faces) * (len(faces) - 1) // 2
    if include_classifications and expected_pairs > _MAX_CLASSIFICATION_DETAILS:
        _fail(f"classification detail cap exceeded: {expected_pairs} > {_MAX_CLASSIFICATION_DETAILS}")
    candidates, hits, nontrivial_evidence = [], [], []
    candidate_count = hit_count = 0
    first_pair = last_pair = first_hit_pair = None
    classifications = [] if include_classifications else None
    class_counts = {stage: 0 for stage in _FINAL_CLASSIFICATION_STAGES}
    processed_pairs = 0
    for first, second in itertools.combinations(range(len(faces)), 2):
        pair = (first, second)
        stage = _pair_status(first, second, faces, normalized, bounds, face_sets)
        if stage == "candidate":
            candidate_count += 1
            if candidate_count > _MAX_CANDIDATES:
                _fail(f"AABB candidate cap exceeded: >{_MAX_CANDIDATES}")
            _append_bounded(candidates, pair)
            first_points = tuple(normalized[index] for index in faces[first])
            second_points = tuple(normalized[index] for index in faces[second])
            stage = "hit" if not _sat_disjoint(first_points, second_points) else "sat-disjoint"
        _record_pair_policy(
            len(faces), first, second, processed_pairs, stage, class_counts)
        if stage == "hit":
            hit_count += 1
            if first_hit_pair is None:
                first_hit_pair = pair
            _append_bounded(hits, pair)
        if stage != "aabb-disjoint":
            _append_bounded(nontrivial_evidence, (pair, stage))
        if classifications is not None:
            classifications.append((pair, stage))
        if first_pair is None:
            first_pair = pair
        last_pair = pair
        processed_pairs += 1
    pair_policy_complete = (
        processed_pairs == expected_pairs
        and first_pair == ((0, 1) if expected_pairs else None)
        and last_pair == ((len(faces) - 2, len(faces) - 1) if expected_pairs else None)
        and sum(class_counts.values()) == expected_pairs)
    pair_policy_evidence = {
        "expected_pair_count": expected_pairs, "processed_pair_count": processed_pairs,
        "first_pair": first_pair, "last_pair": last_pair,
        "class_counts": tuple((stage, class_counts[stage]) for stage in _FINAL_CLASSIFICATION_STAGES),
        "nontrivial_pair_count": expected_pairs - class_counts["aabb-disjoint"],
        "nontrivial_classifications": tuple(nontrivial_evidence),
        "nontrivial_evidence_truncated": expected_pairs - class_counts["aabb-disjoint"] > len(nontrivial_evidence),
    }
    report = {
        "triangle_count": len(faces), "normalization_scale": scale,
        "pair_count": expected_pairs,
        "broad_phase_candidate_count": candidate_count, "intersection_hit_count": hit_count,
        "pair_policy_complete": pair_policy_complete,
        "pair_policy_evidence": pair_policy_evidence,
        "candidate_pairs": tuple(candidates), "hit_pairs": tuple(hits),
        "candidate_pairs_truncated": candidate_count > len(candidates),
        "hit_pairs_truncated": hit_count > len(hits),
        "first_hit_pair": first_hit_pair,
    }
    if classifications is not None:
        report["classifications"] = tuple(classifications)
    return report

def validate_geometry(vertices, quads, level, boundary_loops, port_directions,
                      expected_faces, junction_traces, face_owners):
    level = _integer(level, "level")
    if level not in _STRUCTURAL_FLOORS:
        _fail("level must be 0, 1, or 2")
    if any(value is None for value in (
            boundary_loops, port_directions, expected_faces, junction_traces, face_owners)):
        _fail("all production geometry selectors and gate data are required")
    points = _points(vertices)
    faces = _quads(quads, len(points))
    if level == 0 and len(points) > _MAX_BASE_CONTROLS:
        _fail(f"level 0 base control cap exceeded: {len(points)} > {_MAX_BASE_CONTROLS}")
    if level == 0 and len(faces) > _MAX_BASE_QUADS:
        _fail(f"level 0 base quad cap exceeded: {len(faces)} > {_MAX_BASE_QUADS}")
    loops = _validate_loops(boundary_loops, len(points))
    if len(loops) != 5:
        _fail("exactly 5 boundary loops are required")
    topology = _topology_report(len(points), faces, loops, expected_faces)
    owners = _face_owners(face_owners, len(faces))
    incidence = _edge_incidence(faces)
    edge_lengths = tuple(_norm_vec(_sub_vec(points[b], points[a])) for a, b in incidence)
    triangles = tuple((face[0], face[1], face[2]) for face in faces) + tuple(
        (face[0], face[2], face[3]) for face in faces)
    triangle_areas = tuple(0.5 * _norm_vec(_triangle_normal(face, points))
                           for face in triangles)
    quad_data = tuple(_quad_data(face, points) for face in faces)
    quad_areas = tuple(value[0] for value in quad_data)
    if any(not math.isfinite(value) for value in edge_lengths + triangle_areas + quad_areas):
        _fail("structural metrics must be finite")
    floor = _STRUCTURAL_FLOORS[level]
    if (min(edge_lengths) < floor["edge_length"]
            or min(triangle_areas) < floor["triangle_area"]
            or min(quad_areas) < floor["quad_area"]):
        _fail("structural floor failed")
    intersection = intersection_diagnostics(points, triangles)
    hit_count = intersection["intersection_hit_count"]
    if hit_count:
        _fail(f"{hit_count} triangle intersections, "
              f"first pair {intersection['first_hit_pair']}")
    port_directions = _named_mapping(port_directions, "port directions", 5)
    if set(port_directions) != set(loops):
        _fail("port directions must match boundary loops")
    quad_normals = tuple(value[1] for value in quad_data)
    normals = _boundary_normals(loops, incidence, quad_normals)
    port_metrics = {}
    for name in sorted(loops, key=lambda value: value.encode("utf-8")):
        port_metrics[name] = validate_port_loop(
            points, loops[name], port_directions[name], normals[name])
    fold_count = _run_fold_gates(incidence, owners, quad_normals, level)
    traces = _validate_junction_traces(junction_traces)
    residuals = []
    for name in traces:
        metrics = junction_continuity_metrics(*traces[name])
        residuals.append((name, metrics["coordinate_residual"]))
    return {
        "topology": topology, "edge_length_min": min(edge_lengths),
        "triangle_area_min": min(triangle_areas), "quad_area_min": min(quad_areas),
        "intersection_hit_count": 0, "port_count": len(loops),
        "port_metrics": port_metrics, "fold_count": fold_count,
        "junction_count": len(traces), "junction_residuals": tuple(residuals),
    }

def intersection_candidate_threshold_records(): return tuple(dict(record) for record in _THRESHOLD_RECORDS)
__all__ = [
    "DEGENERACY_FLOOR", "FOLD_LIMITS_DEGREES", "I0", "INTERSECTION_TOLERANCE",
    "MAX_CANDIDATES", "MAX_TRIANGLES", "PI", "STRUCTURAL_FLOORS", "D",
    "MeshCorrectnessError", "S", "T", "TopologyReport", "add",
    "classify_shared_one", "cross", "dot", "enumerate_broad_phase_candidates",
    "fold_angle_degrees", "intersection_candidate_threshold_records",
    "intersection_diagnostics", "interval_disjoint", "junction_continuity_metrics",
    "norm", "normalize", "port_loop_metrics", "shared_one_intersects", "sub",
    "validate_fold", "validate_geometry", "validate_port_loop", "validate_topology",
]

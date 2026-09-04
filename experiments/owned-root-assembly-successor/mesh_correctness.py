"""Fail-closed topology, geometry, and intersection checks."""

from __future__ import annotations

import itertools
import math
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import wraps
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
_STRUCTURAL_FLOORS = {0: {"edge_length": 0.10, "triangle_area": 0.010, "quad_area": 0.010}, 1: {"edge_length": 0.04, "triangle_area": 0.002, "quad_area": 0.002}, 2: {"edge_length": 0.02, "triangle_area": 0.0005, "quad_area": 0.0005}}
STRUCTURAL_FLOORS = {level: dict(values) for level, values in _STRUCTURAL_FLOORS.items()}
_THRESHOLD_RECORDS = tuple({"threshold_id": f"threshold.intersection.L{level}.broad_phase_candidate_count", "relation": "le", "lower": None, "upper": _MAX_CANDIDATES, "unit": "count"} for level in range(3))
class MeshCorrectnessError(ValueError): """A deterministic, fail-closed mesh correctness failure."""

def _fail(message: str) -> NoReturn: raise MeshCorrectnessError(message)
def _finite_float(value, label: str) -> float:
    if type(value) is not float or not math.isfinite(value): _fail(f"{label} must be a finite binary64 value")
    return value
def _integer(value, label: str) -> int:
    if type(value) is not int: _fail(f"{label} must be an integer")
    return value
def _sequence(raw, label: str, cap=None):
    if type(raw) not in (list, tuple): _fail(f"{label} must be an exact list or tuple")
    if cap is not None and len(raw) > cap: _fail(f"{label.rstrip('s')} cap exceeded: {len(raw)} > {cap}")
    return raw
def _named_mapping(raw, label, count=None):
    if type(raw) is not dict or not raw: _fail(f"{label} must be a non-empty exact dict")
    if any(type(name) is not str or not name for name in raw): _fail(f"{label} names must be non-empty strings")
    if count is not None and len(raw) != count: _fail(f"exactly {count} {label} are required")
    return raw
def _vec(value, label: str) -> tuple[float, float, float]:
    values = _sequence(value, label)
    if len(values) != 3: _fail(f"{label} must be a finite 3-vector")
    return tuple(_finite_float(item, f"{label}[{i}]") for i, item in enumerate(values))
def _points(raw):
    values = _sequence(raw, "vertices")
    if not values: _fail("vertices must not be empty")
    return tuple(_vec(value, f"vertices[{i}]") for i, value in enumerate(values))
def _simple_indices(raw, vertex_count, label):
    values = tuple(_integer(value, label) for value in _sequence(raw, label))
    if len(values) < 3 or len(set(values)) != len(values) or any(index < 0 or index >= vertex_count for index in values): _fail(f"{label} must be simple and in range")
    return values
def _indexed_rows(raw, width, vertex_count, label, cap=None):
    rows = _sequence(raw, label, cap); result = []
    for face_index, row in enumerate(rows):
        values = _sequence(row, f"{label}[{face_index}]")
        if len(values) != width: _fail(f"{label}[{face_index}] must have {width} indices")
        face = tuple(_integer(value, f"{label}[{face_index}]") for value in values)
        if any(index < 0 or index >= vertex_count for index in face): _fail(f"{label} index out of range at {face_index}")
        if len(set(face)) != width: _fail(f"{label[:-1]} has repeated vertex index at {face_index}")
        result.append(face)
    return tuple(result)
def _canonical_cycle(face): return min(sequence[i:] + sequence[:i] for sequence in (tuple(face), tuple(reversed(face))) for i in range(len(face)))
def _quads(raw, vertex_count):
    faces = _indexed_rows(raw, 4, vertex_count, "quads", _MAX_QUADS); keys = tuple(_canonical_cycle(face) for face in faces)
    if len(set(keys)) != len(keys): _fail("duplicate quad, including reversed/cyclic duplicate")
    return faces
def _add_vec(a, b): return tuple(a[i] + b[i] for i in range(3))
def _sub_vec(a, b): return tuple(a[i] - b[i] for i in range(3))
def _dot_vec(a, b): return (a[0] * b[0] + a[1] * b[1]) + a[2] * b[2]
def _cross_vec(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _norm_vec(value): return math.sqrt(_dot_vec(value, value))
def _normalize_vec(value, label):
    length = _norm_vec(value)
    if not math.isfinite(length) or length <= 0.0: _fail(f"{label} must be finite and nonzero")
    return tuple(component / length for component in value)
def add(a, b): return _add_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def sub(a, b): return _sub_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def dot(a, b): return _dot_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def cross(a, b): return _cross_vec(_vec(a, "left vector"), _vec(b, "right vector"))
def norm(value): return _norm_vec(_vec(value, "vector"))
def normalize(value): return _normalize_vec(_vec(value, "vector"), "vector normal")
def _normalize_points(points):
    lower = tuple(min(point[i] for point in points) for i in range(3)); extent = tuple(max(point[i] for point in points) - lower[i] for i in range(3)); scale = _norm_vec(extent)
    if not math.isfinite(scale) or scale <= 0.0: _fail("mesh normalization scale must be finite and positive")
    normalized = tuple(tuple((point[i] - lower[i]) / scale for i in range(3)) for point in points)
    if any(not math.isfinite(value) for point in normalized for value in point): _fail("normalized coordinates must be finite")
    return normalized, scale
def interval_disjoint(lower_a, upper_a, lower_b, upper_b):
    values = tuple(_finite_float(value, label) for value, label in zip((lower_a, upper_a, lower_b, upper_b), ("lower_A", "upper_A", "lower_B", "upper_B")))
    return _interval_disjoint(*values)
def _interval_disjoint(lower_a, upper_a, lower_b, upper_b):
    cut_b = lower_b - _FIXED_I0
    cut_a = lower_a - _FIXED_I0
    return upper_a < cut_b or upper_b < cut_a
def _edge_incidence(faces):
    result = defaultdict(list)
    for face_index, face in enumerate(faces):
        for slot, start in enumerate(face):
            end = face[(slot + 1) % len(face)]; result[(min(start, end), max(start, end))].append((face_index, start, end))
    return result
def _child_face_catalog(faces, vertex_count):
    edges = tuple(sorted(_edge_incidence(faces))); edge_points = {edge: vertex_count + index for index, edge in enumerate(edges)}; face_start = vertex_count + len(edges); children = []
    for face_index, face in enumerate(faces):
        center = face_start + face_index
        for slot, vertex in enumerate(face):
            following = tuple(sorted((vertex, face[(slot + 1) % 4]))); preceding = tuple(sorted((face[(slot - 1) % 4], vertex)))
            children.append((vertex, edge_points[following], center, edge_points[preceding]))
    return tuple(children), face_start + len(faces)
def _expected_face_catalogs(raw):
    rows = _sequence(raw, "expected base faces", _MAX_BASE_QUADS)
    if not rows: _fail("expected base faces must not be empty")
    rows = tuple(_sequence(row, f"expected base faces[{face_index}]") for face_index, row in enumerate(rows))
    if any(len(row) != 4 for row in rows): _fail("expected base faces must contain four-index cycles")
    indices = tuple(_integer(value, f"expected base faces[{face_index}]") for face_index, row in enumerate(rows) for value in row)
    if any(index < 0 for index in indices): _fail("expected base face index must be non-negative")
    vertex_count = max(indices) + 1
    if vertex_count > _MAX_BASE_CONTROLS: _fail("expected base control cap exceeded")
    base = _indexed_rows(rows, 4, vertex_count, "expected base faces", _MAX_BASE_QUADS)
    if len({_canonical_cycle(face) for face in base}) != len(base): _fail("duplicate expected base face")
    level1, count1 = _child_face_catalog(base, vertex_count); level2, _ = _child_face_catalog(level1, count1)
    return base, level1, level2
def derive_expected_face_catalogs(expected_base_faces): return _expected_face_catalogs(expected_base_faces)
def _validate_loops(raw, vertex_count):
    if raw is None: return {}
    raw = _named_mapping(raw, "boundary loops"); result, used = {}, set()
    for name in sorted(raw, key=lambda value: value.encode("utf-8")):
        loop = _simple_indices(raw[name], vertex_count, f"boundary loop {name}")
        if used.intersection(loop): _fail(f"boundary loops overlap at {name}")
        used.update(loop); result[name] = loop
    return result
def _cyclic_equal(actual, expected, reverse=False):
    target = tuple(reversed(expected)) if reverse else tuple(expected)
    return len(actual) == len(target) and any(actual == target[i:] + target[:i] for i in range(len(target)))
def _boundary_cycles(edges):
    outgoing = defaultdict(list)
    for _, start, end in edges: outgoing[start].append(end)
    if any(len(values) != 1 for values in outgoing.values()): _fail("boundary edges do not form directed cycles")
    next_vertex = {start: values[0] for start, values in outgoing.items()}; remaining, cycles = set(next_vertex), []
    while remaining:
        start = current = min(remaining); cycle = []
        while current in remaining: remaining.remove(current); cycle.append(current); current = next_vertex[current]
        if current != start or len(cycle) < 3: _fail("boundary cycle is not closed")
        cycles.append(tuple(cycle))
    return tuple(sorted(cycles, key=lambda cycle: min(cycle)))

@dataclass(frozen=True)
class TopologyReport:
    vertex_count: int; edge_count: int; face_count: int; boundary_edge_count: int; boundary_components: int; connected_components: int; euler: int; non_manifold_edges: int; orientation_conflicts: int; boundary_lengths: tuple[int, ...]; valence_inventory: tuple[tuple[int, int], ...]

    @property
    def euler_characteristic(self): return self.euler
def _connected_components(adjacency, vertex_count):
    unseen, components = set(range(vertex_count)), 0
    while unseen:
        todo = [unseen.pop()]; components += 1
        while todo:
            neighbours = adjacency[todo.pop()].intersection(unseen); unseen.difference_update(neighbours); todo.extend(neighbours)
    return components
def _topology_report(vertex_count, quads, loops, expected_faces):
    if expected_faces is not None:
        expected = _indexed_rows(expected_faces, 4, vertex_count, "expected_faces", _MAX_QUADS)
        if quads != expected: _fail("face winding/catalog does not match exactly")
    incidence = _edge_incidence(quads); non_manifold = sum(len(items) > 2 for items in incidence.values())
    if non_manifold: _fail(f"non-manifold edge count {non_manifold}")
    conflicts = sum(len(items) == 2 and items[0][1:] == items[1][1:] for items in incidence.values())
    if conflicts: _fail(f"orientation conflict count {conflicts}")
    boundary = [items[0] for items in incidence.values() if len(items) == 1]; cycles = _boundary_cycles(boundary) if boundary else ()
    if loops:
        expected = tuple(sorted(loops.values(), key=lambda cycle: min(cycle)))
        if len(cycles) != len(expected) or any(sum(_cyclic_equal(actual, wanted) for wanted in expected) != 1 for actual in cycles): _fail("boundary cycle does not match a declared loop orientation")
    adjacency, valence, used = defaultdict(set), defaultdict(int), set()
    for first, second in incidence:
        adjacency[first].add(second); adjacency[second].add(first); valence[first] += 1; valence[second] += 1; used.update((first, second))
    if len(used) != vertex_count: _fail("unused vertex IDs are not permitted")
    components = _connected_components(adjacency, vertex_count)
    if components != 1: _fail("surface is not connected")
    return TopologyReport(vertex_count, len(incidence), len(quads), len(boundary), len(cycles), components, vertex_count - len(incidence) + len(quads), non_manifold, conflicts, tuple(len(cycle) for cycle in cycles), tuple(sorted(valence.items())))
def validate_topology(vertex_count, faces, boundary_loops=None, expected_faces=None):
    _integer(vertex_count, "vertex_count")
    if vertex_count <= 0: _fail("vertex_count must be positive")
    quads = _quads(faces, vertex_count)
    return _topology_report(vertex_count, quads, _validate_loops(boundary_loops, vertex_count), expected_faces)
def _triangle_normal(triangle, points): return _cross_vec(_sub_vec(points[triangle[1]], points[triangle[0]]), _sub_vec(points[triangle[2]], points[triangle[0]]))
def _quad_data(quad, points):
    first, second, third, fourth = (points[index] for index in quad)
    normal_a = _cross_vec(_sub_vec(second, first), _sub_vec(third, first)); normal_b = _cross_vec(_sub_vec(third, first), _sub_vec(fourth, first))
    return 0.5 * _norm_vec(normal_a) + 0.5 * _norm_vec(normal_b), _normalize_vec(_add_vec(normal_a, normal_b), "quad normal")
def quad_normal(vertices, quad):
    points = _points(vertices); return _quad_data(_indexed_rows((quad,), 4, len(points), "quad")[0], points)[1]
def _loop_geometry(selected):
    centroid = (0.0, 0.0, 0.0)
    for point in selected: centroid = _add_vec(centroid, point)
    centroid = tuple(value / len(selected) for value in centroid); area = (0.0, 0.0, 0.0)
    for index, point in enumerate(selected): area = _add_vec(area, _cross_vec(_sub_vec(point, centroid), _sub_vec(selected[(index + 1) % len(selected)], centroid)))
    return centroid, tuple(0.5 * value for value in area)
def port_loop_metrics(points, loop, outward_direction, adjacent_normals):
    points = _points(points); loop = _simple_indices(loop, len(points), "port loop"); direction = _normalize_vec(_vec(outward_direction, "port direction"), "port direction")
    selected = tuple(points[index] for index in loop); centroid, area = _loop_geometry(selected); area_unit = _normalize_vec(area, "port area normal")
    normals = tuple(_normalize_vec(_vec(value, "adjacent face normal"), "adjacent face normal") for value in _sequence(adjacent_normals, "adjacent normals"))
    if len(normals) != len(loop): _fail("port adjacent-normal count must equal loop edge count")
    planarity = tuple(abs(_dot_vec(_sub_vec(point, centroid), area_unit)) for point in selected)
    co_normal = tuple(_dot_vec(_normalize_vec(_cross_vec(_normalize_vec(_sub_vec(selected[(i + 1) % len(selected)], selected[i]), "port tangent"), normal), "port co-normal"), direction) for i, normal in enumerate(normals))
    result = {
        "orientation": -_dot_vec(area_unit, direction),
        "planarity": max(planarity), "planarity_samples": planarity,
        "area_ratio": _norm_vec(area) / (_FIXED_S * _FIXED_S),
        "co_normal": min(co_normal), "co_normal_samples": co_normal,
    }
    if any(not math.isfinite(value) for value in tuple(result[key] for key in ("orientation", "planarity", "area_ratio", "co_normal")) + planarity + co_normal): _fail("port metrics must be finite")
    return result
def validate_port_loop(points, loop, outward_direction, adjacent_normals):
    metrics = port_loop_metrics(points, loop, outward_direction, adjacent_normals)
    if metrics["orientation"] < _PORT_ORIENTATION: _fail("port orientation gate failed")
    if metrics["planarity"] > _FIXED_T: _fail("port planarity gate failed")
    if metrics["area_ratio"] < _PORT_AREA_RATIO: _fail("port area-ratio gate failed")
    if metrics["co_normal"] < _PORT_CO_NORMAL: _fail("port induced co-normal gate failed")
    return metrics
def _tagged_cycle(cycle, raw, points, label):
    if type(raw) is not dict or not raw or any(type(vertex) is not int for vertex in raw): _fail(f"{label} tags must be a non-empty exact vertex-ID dict")
    if set(raw) != set(cycle): _fail(f"{label} vertex IDs differ from independently derived incidence")
    result, seen = [], set()
    for vertex in cycle:
        tag = raw[vertex]
        try:
            if tag in seen: _fail(f"{label} contains duplicate tags")
            seen.add(tag)
        except TypeError as exc: raise MeshCorrectnessError(f"{label} contains an unhashable tag") from exc
        result.append((tag, vertex, points[vertex]))
    return tuple(result)
def _junction_continuity_metrics(points, faces, owners, incident_domains, domain_vertex_tags, expected_domain_vertex_tags=None):
    domains = _sequence(incident_domains, "incident domains")
    if len(domains) != 2 or any(type(domain) is not str or not domain for domain in domains) or domains[0] == domains[1]: _fail("incident domains must be two distinct non-empty strings")
    tag_maps = _sequence(domain_vertex_tags, "domain vertex tags")
    if len(tag_maps) != 2: _fail("domain vertex tags must contain two independently derived mappings")
    if tag_maps[0] is tag_maps[1]: _fail("domain vertex tags must be independent mappings")
    if expected_domain_vertex_tags is None and all(type(tag) is tuple for mapping in tag_maps for tag in mapping.values()): _fail("frozen rational junction tags require an independent reference")
    if expected_domain_vertex_tags is not None and tuple(tag_maps) != tuple(_sequence(expected_domain_vertex_tags, "expected domain vertex tags")): _fail("junction tags differ from independent reference")
    edge_rows = [[], []]
    for uses in _edge_incidence(faces).values():
        if len(uses) != 2 or frozenset(owners[use[0]] for use in uses) != frozenset(domains): continue
        for side, domain in enumerate(domains):
            selected = [use for use in uses if owners[use[0]] == domain]
            if len(selected) != 1: _fail("junction domain incidence is not independently unique")
            edge_rows[side].append(selected[0])
    cycles = tuple(_boundary_cycles(rows) if rows else () for rows in edge_rows)
    if any(len(value) != 1 for value in cycles): _fail("incident domains do not derive one shared junction cycle each")
    traces = tuple(_tagged_cycle(cycles[side][0], tag_maps[side], points, f"trace {side}") for side in range(2))
    keys = tuple(tuple((tag, vertex) for tag, vertex, _ in trace) for trace in traces)
    if set(keys[0]) != set(keys[1]): _fail("junction trace tags and vertex IDs differ")
    if not _cyclic_equal(keys[0], keys[1], reverse=True): _fail("junction trace directions are not opposite")
    first_values, second_values = ({tag: (vertex, point) for tag, vertex, point in trace} for trace in traces)
    try: tags = sorted(first_values)
    except TypeError as exc: raise MeshCorrectnessError("junction trace tags must be orderable") from exc
    residual_samples = tuple(abs(first_values[tag][1][axis] - second_values[tag][1][axis]) for tag in tags for axis in range(3)); residual = max(residual_samples)
    if not math.isfinite(residual) or residual > _FIXED_T: _fail("junction coordinate residual exceeds tolerance")
    return {"tag_identity": True, "vertex_id_identity": True, "opposite_trace_direction": True, "coordinate_residual": residual, "coordinate_residual_samples": residual_samples, "traces": traces}
def junction_continuity_metrics(vertices, quads, face_owners, incident_domains, domain_vertex_tags, expected_domain_vertex_tags=None):
    points = _points(vertices); faces = _quads(quads, len(points)); owners = _face_owners(face_owners, len(faces))
    return _junction_continuity_metrics(points, faces, owners, incident_domains, domain_vertex_tags, expected_domain_vertex_tags)
def classify_ownership_records(element_keys, obligations, candidate_records):
    keys = tuple(_sequence(element_keys, "ownership element universe"))
    if not keys or len(set(keys)) != len(keys) or type(obligations) is not dict or set(obligations) != set(keys): _fail("ownership universe and obligations must be exact and disjoint")
    required = {}
    for key in keys:
        values = tuple(_sequence(obligations[key], f"ownership obligations for {key}"))
        if not values or len(set(values)) != len(values) or any(type(value) is not str or not value for value in values): _fail("ownership obligations must be non-empty unique strings")
        required[key] = values
    grouped = defaultdict(list)
    for index, row in enumerate(_sequence(candidate_records, "ownership candidate records")):
        if type(row) not in (tuple, list) or len(row) != 3: _fail(f"ownership candidate {index} is not a key/obligation/validity record")
        key, obligation, valid = row
        if key not in required or obligation not in required[key] or type(valid) is not bool: _fail(f"ownership candidate {index} names an unknown obligation or has invalid validity")
        grouped[(key, obligation)].append(valid)
    classifications = []
    for key in keys:
        states = tuple((obligation, "multiple" if len(grouped.get((key, obligation), ())) > 1 else "one" if grouped.get((key, obligation), ()) and grouped[(key, obligation)][0] else "zero") for obligation in required[key])
        classifications.append((key, states))
    overowned = sum(any(state == "multiple" for _, state in states) for _, states in classifications)
    unowned = sum(not any(state == "multiple" for _, state in states) and any(state == "zero" for _, state in states) for _, states in classifications)
    return {"unowned_elements": unowned, "overowned_elements": overowned, "classifications": tuple(classifications)}
def fold_angle_degrees(normal_a, normal_b):
    first = _normalize_vec(_vec(normal_a, "fold normal A"), "fold normal A"); second = _normalize_vec(_vec(normal_b, "fold normal B"), "fold normal B")
    cosine = max(-1.0, min(1.0, _dot_vec(first, second))); angle = math.acos(cosine); first_step = angle * 180.0
    return first_step / _FIXED_PI
def validate_fold(normal_a, normal_b, level):
    level = _integer(level, "fold level")
    if level not in range(3): _fail("fold level must be 0, 1, or 2")
    angle = fold_angle_degrees(normal_a, normal_b)
    if not angle < _FIXED_FOLD_LIMITS[level]: _fail(f"fold angle {angle!r} is not below {_FIXED_FOLD_LIMITS[level]!r}")
    return angle
def _validate_junction_inputs(raw):
    raw = _named_mapping(raw, "junction inputs", 7); result = {}
    for name in sorted(raw, key=lambda value: value.encode("utf-8")):
        row = raw[name]
        if type(row) is not dict or set(row) not in ({"incident_domains", "domain_vertex_tags"}, {"incident_domains", "domain_vertex_tags", "expected_domain_vertex_tags"}): _fail(f"{name} must contain exact junction derivation inputs")
        result[name] = row
    return result
def _face_owners(raw, face_count):
    owners = _sequence(raw, "face_owners", _MAX_QUADS)
    if len(owners) != face_count or any(type(owner) is not str or not owner for owner in owners): _fail("face_owners must contain one non-empty string per face")
    return owners
def _boundary_normals(loops, incidence, quad_normals):
    result = {}
    for name, loop in loops.items():
        normals = []
        for slot, start in enumerate(loop):
            end = loop[(slot + 1) % len(loop)]; uses = incidence.get((min(start, end), max(start, end)), ())
            if len(uses) != 1: _fail(f"{name} boundary edge is not uniquely derived")
            normals.append(quad_normals[uses[0][0]])
        result[name] = tuple(normals)
    return result
def _run_fold_gates(incidence, owners, quad_normals, level):
    count = 0
    for uses in incidence.values():
        if len(uses) == 2 and owners[uses[0][0]] != owners[uses[1][0]]:
            validate_fold(quad_normals[uses[0][0]], quad_normals[uses[1][0]], level); count += 1
    return count
def _aabb(points, triangle):
    corners = tuple(points[index] for index in triangle)
    return tuple(min(point[i] for point in corners) for i in range(3)) + tuple(max(point[i] for point in corners) for i in range(3))
def _shared_edge_direction(triangle, shared):
    shared = set(shared)
    for i, start in enumerate(triangle):
        end = triangle[(i + 1) % 3]
        if {start, end} == shared: return start, end
    _fail("shared edge is absent")
def _axis_list(first, second):
    edges_a = tuple(_sub_vec(first[(i + 1) % 3], first[i]) for i in range(3)); edges_b = tuple(_sub_vec(second[(i + 1) % 3], second[i]) for i in range(3))
    normal_a = _cross_vec(_sub_vec(first[1], first[0]), _sub_vec(first[2], first[0])); normal_b = _cross_vec(_sub_vec(second[1], second[0]), _sub_vec(second[2], second[0]))
    return (normal_a, normal_b) + tuple(_cross_vec(a, b) for a in edges_a for b in edges_b) + tuple(_cross_vec(normal_a, edge) for edge in edges_a) + tuple(_cross_vec(normal_b, edge) for edge in edges_b)
def _sat_disjoint(first, second):
    for axis in _axis_list(first, second):
        length = _norm_vec(axis)
        if not math.isfinite(length): _fail("SAT axis must be finite")
        if length <= _FIXED_D: continue
        unit = _normalize_vec(axis, "SAT axis"); projections = tuple(_dot_vec(point, unit) for point in first + second)
        if not all(math.isfinite(value) for value in projections): _fail("SAT projections must be finite")
        if _interval_disjoint(min(projections[:3]), max(projections[:3]), min(projections[3:]), max(projections[3:])): return True
    return False
def _rational(value): return Fraction(0, 1) if value == 0.0 else Fraction(*value.as_integer_ratio())
def _ray_difference(first, second): return tuple(_rational(first[i]) - _rational(second[i]) for i in range(3))
def _active_solution(rays, subset):
    matrix = [[rays[index][row] for index in subset] + [Fraction(0, 1)] for row in range(3)]
    matrix.append([Fraction(1, 1) for _ in subset] + [Fraction(1, 1)])
    for pivot_row, column in enumerate(range(len(subset))):
        pivot = next((row for row in range(pivot_row, 4) if matrix[row][column]), None)
        if pivot is None: return None
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]; divisor = matrix[pivot_row][column]; matrix[pivot_row] = [value / divisor for value in matrix[pivot_row]]
        for row in range(4):
            if row != pivot_row and matrix[row][column]:
                factor = matrix[row][column]; matrix[row] = [left - factor * right for left, right in zip(matrix[row], matrix[pivot_row])]
    if any(not any(row[:-1]) and row[-1] for row in matrix): return None
    solution = [Fraction(0, 1)] * 4
    for row, column in enumerate(range(len(subset))): solution[subset[column]] = matrix[row][-1]
    if any(value < 0 for value in solution) or solution[0] + solution[1] <= 0 or solution[2] + solution[3] <= 0: return None
    return tuple(solution)
def shared_one_intersects(shared, a0, a1, b0, b1):
    values = tuple(_vec(value, label) for value, label in ((shared, "shared point"), (a0, "A0"), (a1, "A1"), (b0, "B0"), (b1, "B1")))
    shared, a0, a1, b0, b1 = values
    rays = (_ray_difference(a0, shared), _ray_difference(a1, shared), _ray_difference(shared, b0), _ray_difference(shared, b1))
    if any(not any(value for value in ray) for ray in rays): _fail("shared-one classifier received a zero ray")
    return any(_active_solution(rays, subset) is not None for size in (2, 3, 4) for subset in itertools.combinations(range(4), size))
def classify_shared_one(shared, a0, a1, b0, b1): return "hit" if shared_one_intersects(shared, a0, a1, b0, b1) else "point-only"
def _classify_shared_one_triangles(first, second, points):
    shared = next(index for index in first if index in second); a = [index for index in first if index != shared]; b = [index for index in second if index != shared]
    return shared_one_intersects(points[shared], points[a[0]], points[a[1]], points[b[0]], points[b[1]])
def _intersection_inputs(vertices, triangles):
    points = _points(vertices); faces = _indexed_rows(triangles, 3, len(points), "triangles", _MAX_TRIANGLES); normalized, scale = _normalize_points(points)
    for index, face in enumerate(faces):
        length = _norm_vec(_triangle_normal(face, normalized))
        if not math.isfinite(length) or length <= _FIXED_D: _fail(f"normalized triangle normal degeneracy at {index}")
    bounds = tuple(_aabb(normalized, face) for face in faces)
    return faces, normalized, scale, bounds, tuple(frozenset(face) for face in faces)
def _aabb_disjoint(first, second): return any(_interval_disjoint(first[i], first[i + 3], second[i], second[i + 3]) for i in range(3))
def _pair_status(first_index, second_index, faces, normalized, bounds, face_sets):
    pair = (first_index, second_index); common = face_sets[first_index].intersection(face_sets[second_index])
    if len(common) == 3: _fail(f"duplicate triangle pair {pair}")
    if len(common) == 2:
        first_edge = _shared_edge_direction(faces[first_index], common); second_edge = _shared_edge_direction(faces[second_index], common)
        if first_edge != (second_edge[1], second_edge[0]): _fail(f"shared-two edge direction conflict at pair {pair}")
        return "excluded-adjacent"
    if len(common) == 1:
        if normalized is None: return "shared-one"
        return "hit" if _classify_shared_one_triangles(faces[first_index], faces[second_index], normalized) else "point-only"
    return "aabb-disjoint" if _aabb_disjoint(bounds[first_index], bounds[second_index]) else "candidate"
def _record_pair_policy(triangle_count, first, second, ordinal, stage, class_counts):
    expected_ordinal = first * (2 * triangle_count - first - 1) // 2 + second - first - 1
    if ordinal != expected_ordinal: _fail("intersection pair coverage is not exhaustive reference order")
    if stage not in _FINAL_CLASSIFICATION_STAGES: _fail("intersection pair has an invalid classification")
    class_counts[stage] += 1
def _append_candidate(result, pair, cap):
    if len(result) >= cap: _fail(f"AABB candidate cap exceeded: >{cap}")
    result.append(pair)
def _append_bounded(result, value):
    if len(result) < _MAX_DIAGNOSTIC_EVIDENCE: result.append(value)
def _collect_candidate_pairs(faces, bounds, face_sets, cap):
    cap = _integer(cap, "candidate cap")
    if cap <= 0: _fail("candidate cap must be a positive integer")
    result = []
    for first in range(len(faces)):
        for second in range(first + 1, len(faces)):
            if _pair_status(first, second, faces, None, bounds, face_sets) == "candidate": _append_candidate(result, (first, second), cap)
    return tuple(result)
def _enumerate_fixture_candidates(vertices, triangles, cap):
    """Fixture-only cap injection. Production always uses the fixed cap."""
    faces, _, _, bounds, face_sets = _intersection_inputs(vertices, triangles)
    return _collect_candidate_pairs(faces, bounds, face_sets, cap)
def enumerate_broad_phase_candidates(points, triangles):
    faces, _, _, bounds, face_sets = _intersection_inputs(points, triangles)
    return _collect_candidate_pairs(faces, bounds, face_sets, _MAX_CANDIDATES)
def intersection_diagnostics(vertices, triangles, *, include_classifications=False):
    if type(include_classifications) is not bool: _fail("include_classifications must be a boolean")
    faces, normalized, scale, bounds, face_sets = _intersection_inputs(vertices, triangles); expected_pairs = len(faces) * (len(faces) - 1) // 2
    if include_classifications and expected_pairs > _MAX_CLASSIFICATION_DETAILS: _fail(f"classification detail cap exceeded: {expected_pairs} > {_MAX_CLASSIFICATION_DETAILS}")
    candidates, hits, nontrivial_evidence = [], [], []; candidate_count = hit_count = 0; first_pair = last_pair = first_hit_pair = None
    classifications = [] if include_classifications else None; class_counts = {stage: 0 for stage in _FINAL_CLASSIFICATION_STAGES}; processed_pairs = 0
    for first, second in itertools.combinations(range(len(faces)), 2):
        pair = (first, second); stage = _pair_status(first, second, faces, normalized, bounds, face_sets)
        if stage == "candidate":
            candidate_count += 1
            if candidate_count > _MAX_CANDIDATES: _fail(f"AABB candidate cap exceeded: >{_MAX_CANDIDATES}")
            _append_bounded(candidates, pair); first_points = tuple(normalized[index] for index in faces[first]); second_points = tuple(normalized[index] for index in faces[second]); stage = "hit" if not _sat_disjoint(first_points, second_points) else "sat-disjoint"
        _record_pair_policy(len(faces), first, second, processed_pairs, stage, class_counts)
        if stage == "hit":
            hit_count += 1
            if first_hit_pair is None: first_hit_pair = pair
            _append_bounded(hits, pair)
        if stage != "aabb-disjoint": _append_bounded(nontrivial_evidence, (pair, stage))
        if classifications is not None: classifications.append((pair, stage))
        if first_pair is None: first_pair = pair
        last_pair = pair; processed_pairs += 1
    pair_policy_complete = processed_pairs == expected_pairs and first_pair == ((0, 1) if expected_pairs else None) and last_pair == ((len(faces) - 2, len(faces) - 1) if expected_pairs else None) and sum(class_counts.values()) == expected_pairs
    pair_policy_evidence = {"expected_pair_count": expected_pairs, "processed_pair_count": processed_pairs, "first_pair": first_pair, "last_pair": last_pair, "class_counts": tuple((stage, class_counts[stage]) for stage in _FINAL_CLASSIFICATION_STAGES), "nontrivial_pair_count": expected_pairs - class_counts["aabb-disjoint"], "nontrivial_classifications": tuple(nontrivial_evidence), "nontrivial_evidence_truncated": expected_pairs - class_counts["aabb-disjoint"] > len(nontrivial_evidence)}
    report = {"triangle_count": len(faces), "normalization_scale": scale, "pair_count": expected_pairs, "broad_phase_candidate_count": candidate_count, "intersection_hit_count": hit_count, "pair_policy_complete": pair_policy_complete, "pair_policy_evidence": pair_policy_evidence, "candidate_pairs": tuple(candidates), "hit_pairs": tuple(hits), "candidate_pairs_truncated": candidate_count > len(candidates), "hit_pairs_truncated": hit_count > len(hits), "first_hit_pair": first_hit_pair}
    if classifications is not None: report["classifications"] = tuple(classifications)
    return report
_P0 = float.fromhex("0x0.0p+0"); _N0 = -_P0; _ONE = float.fromhex("0x1.0000000000000p+0"); _HALF = float.fromhex("0x1.0000000000000p-1"); _D50 = float.fromhex("0x1.0000000000000p-50"); _MIN_SUBNORMAL = float.fromhex("0x0.0000000000001p-1022")
_FIXTURE_SUFFIXES = ("p000", "p001", "p010", "p011", "p100", "p101", "p110", "p111")
_GENERAL_FIXTURE_IDS = ("shared0.clear-hit-origin", "shared0.clear-hit-translated", "shared0.sub-I0-contact-origin", "shared0.sub-I0-contact-translated", "shared0.aabb-disjoint", "shared0.sat-disjoint", "shared0.extreme-small-hit", "shared0.extreme-large-hit", "normal.boundary-D-reject", "normal.successor-D-accept", "shared2.opposite-edge-valid", "shared2.same-direction-reject", "shared3.duplicate-triangle-reject", "triangle-cap.boundary-4096", "triangle-cap.successor-4097", "candidate-cap.boundary-injected-3", "candidate-cap.successor-injected-3")
def _fixture_pair(a0, a1, b0, b1, shared=(_P0, _P0, _P0)): return ((shared, a0, a1), (shared, b0, b1))
def _transform_fixture(pair, scale, translation): return tuple(tuple(tuple(float(float(scale * value) + offset) for value, offset in zip(point, translation)) for point in triangle) for triangle in pair)
def _negative_zero_fixture(pair): return tuple(tuple(tuple(math.copysign(0.0, -1.0) if value == 0.0 else value for value in point) for point in triangle) for triangle in pair)
_A0, _A1 = (_ONE, _P0, _P0), (_P0, _ONE, _P0)
_SHARED_ONE_FIXTURES = ( ("shared1.offset-d50-point-only", _fixture_pair(_A0, _A1, (_ONE, _P0, _D50), (_P0, _ONE, _D50)), "point-only"), ("shared1.coplanar-duplicate-hit", _fixture_pair(_A0, _A1, _A0, _A1), "hit"), ("shared1.offset-positive-minsub-point-only", _fixture_pair(_A0, _A1, (_ONE, _P0, _MIN_SUBNORMAL), (_P0, _ONE, _MIN_SUBNORMAL)), "point-only"), ("shared1.offset-negative-minsub-point-only", _fixture_pair(_A0, _A1, (_ONE, _P0, -_MIN_SUBNORMAL), (_P0, _ONE, -_MIN_SUBNORMAL)), "point-only"), ("shared1.coplanar-disjoint-fans", _fixture_pair(_A0, _A1, (-_ONE, _P0, _P0), (_P0, -_ONE, _P0)), "point-only"), ("shared1.ray-cone-hit", _fixture_pair(_A0, _A1, (_ONE, _ONE, _P0), (_P0, _P0, _ONE)), "hit"), ("shared1.near-coplanar-full-rank-hit", _fixture_pair(_A0, _A1, (_ONE, _P0, _D50), (_P0, _ONE, -_D50)), "hit"), ("shared1.transformed-point-only", _transform_fixture(_fixture_pair(_A0, _A1, (_ONE, _P0, _D50), (_P0, _ONE, _D50)), 8.0, (4.0, -2.0, 1.0)), "point-only"), ("shared1.transformed-hit", _transform_fixture(_fixture_pair(_A0, _A1, (_ONE, _P0, _D50), (_P0, _ONE, -_D50)), 8.0, (4.0, -2.0, 1.0)), "hit"), ("shared1.negative-zero-hit", _negative_zero_fixture(_fixture_pair(_A0, _A1, _A0, _A1)), "hit"), ("shared1.level2-ply-point-only", _fixture_pair((float.fromhex("0x1.37918e2798bb6p-8"), float.fromhex("0x1.61bcdab8dcc06p-4"), float.fromhex("0x1.43c9e5ce2aeb6p-4")), (float.fromhex("0x1.7bc42ac7f04b0p-7"), float.fromhex("0x1.6cae8c4686bb2p-4"), float.fromhex("0x1.0be935f6a339ep-4")), (float.fromhex("0x1.7888e87a16156p-6"), float.fromhex("0x1.7eec0987f75cdp-4"), float.fromhex("0x1.d5d88ce274e30p-5")), (float.fromhex("0x1.8b59f7e4bf4dfp-6"), float.fromhex("0x1.18982604f83a1p-4"), float.fromhex("0x1.07df2315527a3p-4")), (float.fromhex("0x1.8b59f7e4bf4dfp-7"), float.fromhex("0x1.0a35e0636f7c1p-4"), float.fromhex("0x1.264d28c7c3da4p-4"))), "point-only"), )
INTERSECTION_FIXTURE_IDS = tuple(f"{name}.{suffix}" for name, _, _ in _SHARED_ONE_FIXTURES for suffix in _FIXTURE_SUFFIXES) + _GENERAL_FIXTURE_IDS
_CLEAR_PAIR = (((-_ONE, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0)), ((_P0, -_ONE, _P0), (_HALF, _HALF, _P0), (-_HALF, _HALF, _P0)))
_SUB_I0_PAIR = (((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0)), ((_P0, _P0, float.fromhex("0x1.0000000000000p-34")), (_ONE, _P0, float.fromhex("0x1.0000000000000p-34")), (_P0, _ONE, float.fromhex("0x1.0000000000000p-34"))))
_SHARED_ZERO_FIXTURES = ( (_GENERAL_FIXTURE_IDS[0], _CLEAR_PAIR, "hit"), (_GENERAL_FIXTURE_IDS[1], _transform_fixture(_CLEAR_PAIR, _ONE, (4.0, -2.0, 1.0)), "hit"), (_GENERAL_FIXTURE_IDS[2], _SUB_I0_PAIR, "hit"), (_GENERAL_FIXTURE_IDS[3], _transform_fixture(_SUB_I0_PAIR, _ONE, (4.0, -2.0, 1.0)), "hit"), (_GENERAL_FIXTURE_IDS[4], (((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0)), ((_P0, _P0, _ONE), (_ONE, _P0, _ONE), (_P0, _ONE, _ONE))), "aabb-disjoint"), (_GENERAL_FIXTURE_IDS[5], (((_P0, _P0, _P0), (2.0, _P0, _P0), (_P0, 2.0, _P0)), ((2.0, 2.0, _P0), (2.0, 1.5, _P0), (1.5, 2.0, _P0))), "sat-disjoint"), (_GENERAL_FIXTURE_IDS[6], _transform_fixture(_CLEAR_PAIR, float.fromhex("0x1.0000000000000p-500"), (_P0, _P0, _P0)), "hit"), (_GENERAL_FIXTURE_IDS[7], _transform_fixture(_CLEAR_PAIR, float.fromhex("0x1.0000000000000p+500"), (_P0, _P0, _P0)), "hit"), )
def _fixture_failure(fixture_id, message, function, *args):
    try: function(*args)
    except MeshCorrectnessError as exc:
        if message not in str(exc): _fail(f"{fixture_id} failed at the wrong stage: {exc}")
    else: _fail(f"{fixture_id} did not fail")
    return {"fixture_id": fixture_id, "outcome": "hard-failure"}
def _fixture_pair_result(fixture_id, pair, expected):
    report = intersection_diagnostics(pair[0] + pair[1], ((0, 1, 2), (3, 4, 5)), include_classifications=True)
    actual = report["classifications"][0][1]
    if not report["pair_policy_complete"] or report["pair_count"] != 1 or actual != expected or report["intersection_hit_count"] != (expected == "hit"): _fail(f"{fixture_id} changed: {actual!r}")
    return {"fixture_id": fixture_id, "outcome": actual}
def run_production_intersection_fixtures():
    expected_thresholds = tuple({"threshold_id": f"threshold.intersection.L{level}.broad_phase_candidate_count", "relation": "le", "lower": None, "upper": 1_000_000, "unit": "count"} for level in range(3))
    if _MAX_CANDIDATES != 1_000_000 or intersection_candidate_threshold_records() != expected_thresholds: _fail("intersection production cap or thresholds changed")
    result = []
    for base_name, pair, expected in _SHARED_ONE_FIXTURES:
        points = pair[0] + pair[1][1:]
        for suffix in _FIXTURE_SUFFIXES:
            first, second = [0, 1, 2], [0, 3, 4]
            if suffix[1] == "1": first, second = second, first
            if suffix[2] == "1": first[1], first[2] = first[2], first[1]
            if suffix[3] == "1": second[1], second[2] = second[2], second[1]
            actual = "hit" if _classify_shared_one_triangles(first, second, points) else "point-only"; fixture_id = f"{base_name}.{suffix}"
            if actual != expected: _fail(f"{fixture_id} changed: {actual!r}")
            result.append({"fixture_id": fixture_id, "outcome": actual})
    result.extend(_fixture_pair_result(*fixture) for fixture in _SHARED_ZERO_FIXTURES)
    normal_points = ((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _FIXED_D, _P0)); one_triangle = ((0, 1, 2),)
    result.append(_fixture_failure(_GENERAL_FIXTURE_IDS[8], "normalized triangle normal", intersection_diagnostics, normal_points, one_triangle))
    admitted = intersection_diagnostics((normal_points[0], normal_points[1], (_P0, float.fromhex("0x1.0000000000000p-45"), _P0)), one_triangle)
    if (admitted["triangle_count"], admitted["pair_count"], admitted["intersection_hit_count"]) != (1, 0, 0): _fail(f"{_GENERAL_FIXTURE_IDS[9]} changed")
    result.append({"fixture_id": _GENERAL_FIXTURE_IDS[9], "outcome": "pass"})
    shared2_points = ((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0), (_P0, -_ONE, _P0))
    valid_shared2 = intersection_diagnostics(shared2_points, ((0, 1, 2), (1, 0, 3)), include_classifications=True)
    if valid_shared2["classifications"] != (((0, 1), "excluded-adjacent"),): _fail(f"{_GENERAL_FIXTURE_IDS[10]} changed")
    result.append({"fixture_id": _GENERAL_FIXTURE_IDS[10], "outcome": "excluded-adjacent"})
    result.append(_fixture_failure(_GENERAL_FIXTURE_IDS[11], "shared-two", intersection_diagnostics, shared2_points, ((0, 1, 2), (0, 1, 3))))
    result.append(_fixture_failure(_GENERAL_FIXTURE_IDS[12], "duplicate triangle", intersection_diagnostics, normal_points[:2] + ((_P0, _ONE, _P0),), ((0, 1, 2), (0, 1, 2))))
    cap_points, cap_triangles = [], []
    for row in range(_MAX_TRIANGLES):
        offset = 3 * row; x = float(4 * row); cap_points.extend(((x, _P0, _P0), (float(x + _ONE), _P0, _P0), (x, _ONE, _P0))); cap_triangles.append((offset, offset + 1, offset + 2))
    cap_report = intersection_diagnostics(tuple(cap_points), tuple(cap_triangles)); pair_count = _MAX_TRIANGLES * (_MAX_TRIANGLES - 1) // 2; evidence = cap_report["pair_policy_evidence"]
    cap_actual = (cap_report["triangle_count"], cap_report["pair_count"], cap_report["broad_phase_candidate_count"], cap_report["intersection_hit_count"], cap_report["pair_policy_complete"], cap_report["candidate_pairs"], cap_report["hit_pairs"], cap_report["candidate_pairs_truncated"], cap_report["hit_pairs_truncated"], cap_report["first_hit_pair"], "classifications" in cap_report, evidence["expected_pair_count"], evidence["processed_pair_count"], evidence["first_pair"], evidence["last_pair"], evidence["class_counts"], evidence["nontrivial_pair_count"], evidence["nontrivial_classifications"], evidence["nontrivial_evidence_truncated"])
    cap_expected = (_MAX_TRIANGLES, pair_count, 0, 0, True, (), (), False, False, None, False, pair_count, pair_count, (0, 1), (4094, 4095), (("aabb-disjoint", pair_count), ("sat-disjoint", 0), ("hit", 0), ("point-only", 0), ("excluded-adjacent", 0)), 0, (), False)
    if cap_actual != cap_expected: _fail(f"{_GENERAL_FIXTURE_IDS[13]} changed")
    result.append({"fixture_id": _GENERAL_FIXTURE_IDS[13], "outcome": "pass"})
    overflow_points = tuple(cap_points) + ((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0)); overflow_triangles = tuple(cap_triangles) + ((12288, 12289, 12290),)
    result.append(_fixture_failure(_GENERAL_FIXTURE_IDS[14], "triangle cap", intersection_diagnostics, overflow_points, overflow_triangles))
    candidate_points = tuple(point for _ in range(3) for point in ((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0))); candidate_triangles = tuple((3 * row, 3 * row + 1, 3 * row + 2) for row in range(3)); expected_pairs = ((0, 1), (0, 2), (1, 2))
    candidate_report = intersection_diagnostics(candidate_points, candidate_triangles, include_classifications=True)
    if (_enumerate_fixture_candidates(candidate_points, candidate_triangles, 3), candidate_report["pair_count"], candidate_report["candidate_pairs"], candidate_report["hit_pairs"], candidate_report["intersection_hit_count"], candidate_report["first_hit_pair"], candidate_report["candidate_pairs_truncated"], candidate_report["hit_pairs_truncated"], candidate_report["classifications"]) != (expected_pairs, 3, expected_pairs, expected_pairs, 3, (0, 1), False, False, (((0, 1), "hit"), ((0, 2), "hit"), ((1, 2), "hit"))): _fail(f"{_GENERAL_FIXTURE_IDS[15]} changed")
    result.append({"fixture_id": _GENERAL_FIXTURE_IDS[15], "outcome": "hit"})
    candidate_points += ((_P0, _P0, _P0), (_ONE, _P0, _P0), (_P0, _ONE, _P0)); candidate_triangles += ((9, 10, 11),)
    result.append(_fixture_failure(_GENERAL_FIXTURE_IDS[16], "candidate cap", _enumerate_fixture_candidates, candidate_points, candidate_triangles, 3))
    if len(result) != 105 or tuple(row["fixture_id"] for row in result) != INTERSECTION_FIXTURE_IDS: _fail("intersection fixture execution order or count changed")
    return tuple(result)

def validate_geometry(vertices, quads, level, boundary_loops, port_directions, expected_base_faces, junction_inputs, face_owners):
    level = _integer(level, "level")
    if level not in _STRUCTURAL_FLOORS: _fail("level must be 0, 1, or 2")
    if any(value is None for value in (boundary_loops, port_directions, expected_base_faces, junction_inputs, face_owners)): _fail("all production geometry selectors and gate data are required")
    points = _points(vertices); faces = _quads(quads, len(points))
    if level == 0 and len(points) > _MAX_BASE_CONTROLS: _fail(f"level 0 base control cap exceeded: {len(points)} > {_MAX_BASE_CONTROLS}")
    if level == 0 and len(faces) > _MAX_BASE_QUADS: _fail(f"level 0 base quad cap exceeded: {len(faces)} > {_MAX_BASE_QUADS}")
    loops = _validate_loops(boundary_loops, len(points))
    if len(loops) != 5: _fail("exactly 5 boundary loops are required")
    topology = _topology_report(len(points), faces, loops, _expected_face_catalogs(expected_base_faces)[level]); owners = _face_owners(face_owners, len(faces)); incidence = _edge_incidence(faces)
    edge_lengths = tuple(_norm_vec(_sub_vec(points[b], points[a])) for a, b in incidence)
    triangles = tuple((face[0], face[1], face[2]) for face in faces) + tuple((face[0], face[2], face[3]) for face in faces)
    triangle_areas = tuple(0.5 * _norm_vec(_triangle_normal(face, points)) for face in triangles); quad_data = tuple(_quad_data(face, points) for face in faces); quad_areas = tuple(value[0] for value in quad_data)
    if any(not math.isfinite(value) for value in edge_lengths + triangle_areas + quad_areas): _fail("structural metrics must be finite")
    floor = _STRUCTURAL_FLOORS[level]
    if min(edge_lengths) < floor["edge_length"] or min(triangle_areas) < floor["triangle_area"] or min(quad_areas) < floor["quad_area"]: _fail("structural floor failed")
    intersection = intersection_diagnostics(points, triangles); hit_count = intersection["intersection_hit_count"]
    if hit_count: _fail(f"{hit_count} triangle intersections, first pair {intersection['first_hit_pair']}")
    port_directions = _named_mapping(port_directions, "port directions", 5)
    if set(port_directions) != set(loops): _fail("port directions must match boundary loops")
    quad_normals = tuple(value[1] for value in quad_data); normals = _boundary_normals(loops, incidence, quad_normals)
    port_metrics = {name: validate_port_loop(points, loops[name], port_directions[name], normals[name]) for name in sorted(loops, key=lambda value: value.encode("utf-8"))}
    junctions = _validate_junction_inputs(junction_inputs)
    residuals = tuple((name, _junction_continuity_metrics(points, faces, owners, row["incident_domains"], row["domain_vertex_tags"], row.get("expected_domain_vertex_tags"))["coordinate_residual"]) for name, row in junctions.items())
    fold_count = _run_fold_gates(incidence, owners, quad_normals, level)
    return {"topology": topology, "edge_length_min": min(edge_lengths), "triangle_area_min": min(triangle_areas), "quad_area_min": min(quad_areas), "intersection_hit_count": 0, "port_count": len(loops), "port_metrics": port_metrics, "fold_count": fold_count, "junction_count": len(junctions), "junction_residuals": residuals}

def intersection_candidate_threshold_records(): return tuple(dict(record) for record in _THRESHOLD_RECORDS)
def _normalize_public(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try: return function(*args, **kwargs)
        except MeshCorrectnessError: raise
        except Exception as exc: raise MeshCorrectnessError(f"{function.__name__} rejected malformed public input") from exc
    return checked
_PUBLIC_FUNCTIONS = ("add", "classify_ownership_records", "classify_shared_one", "cross", "derive_expected_face_catalogs", "dot", "enumerate_broad_phase_candidates", "fold_angle_degrees", "intersection_candidate_threshold_records", "intersection_diagnostics", "interval_disjoint", "junction_continuity_metrics", "norm", "normalize", "port_loop_metrics", "quad_normal", "run_production_intersection_fixtures", "shared_one_intersects", "sub", "validate_fold", "validate_geometry", "validate_port_loop", "validate_topology")
for _public_name in _PUBLIC_FUNCTIONS: globals()[_public_name] = _normalize_public(globals()[_public_name])
__all__ = ["DEGENERACY_FLOOR", "FOLD_LIMITS_DEGREES", "I0", "INTERSECTION_FIXTURE_IDS", "INTERSECTION_TOLERANCE", "MAX_CANDIDATES", "MAX_TRIANGLES", "PI", "STRUCTURAL_FLOORS", "D", "MeshCorrectnessError", "S", "T", "TopologyReport", "add", "classify_ownership_records", "classify_shared_one", "cross", "derive_expected_face_catalogs", "dot", "enumerate_broad_phase_candidates", "fold_angle_degrees", "intersection_candidate_threshold_records", "intersection_diagnostics", "interval_disjoint", "junction_continuity_metrics", "norm", "normalize", "port_loop_metrics", "quad_normal", "run_production_intersection_fixtures", "shared_one_intersects", "sub", "validate_fold", "validate_geometry", "validate_port_loop", "validate_topology"]

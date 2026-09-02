"""Experiment-local root-complex cage grammar and deterministic evaluator."""

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from math import cos, isfinite, pi, sin
from typing import Mapping

import numpy as np


RING_NAMES = (
    "neck_collar",
    "upper_ribcage_shoulder",
    "lower_ribcage",
    "waist_abdomen",
    "iliac_overlap",
    "lower_pelvis",
)
CONSTANTS = {"n": 2.6, "lambda": 0.25, "shoulder": 1.0, "axilla": 0.55,
             "eta": 0.25, "gamma": 0.08}
RANGES = {"n": (2.0, 3.2), "lambda": (0.0, 0.5), "shoulder": (0.8, 1.2),
          "axilla": (0.35, 0.75), "eta": (0.0, 0.5), "gamma": (0.04, 0.12)}
EXPECTED_VALENCES = ((3, 22), (4, 32), (5, 10))


@dataclass(frozen=True)
class Mesh:
    vertices: tuple[tuple[float, float, float], ...]
    quads: tuple[tuple[int, int, int, int], ...]
    control_ids: tuple[str, ...]
    formula_ids: tuple[str, ...]
    dependencies: tuple[tuple[str, ...], ...]
    provenance_ids: tuple[tuple[str, ...], ...]
    boundary_loops: tuple[tuple[str, tuple[int, ...]], ...]
    triangles: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True)
class SurfaceEvaluation:
    cage: Mesh
    levels: tuple[Mesh, ...]


@dataclass(frozen=True)
class TopologyReport:
    vertex_count: int
    edge_count: int
    face_count: int
    boundary_edge_count: int
    euler: int
    boundary_lengths: tuple[int, ...]
    valence_inventory: tuple[tuple[int, int], ...]


def _edges(faces):
    uses = defaultdict(list)
    for fi, face in enumerate(faces):
        for i, a in enumerate(face):
            b = face[(i + 1) % 4]
            uses[tuple(sorted((a, b)))].append((fi, a, b))
    return uses


def _orient(faces):
    uses = _edges(faces)
    adjacency = defaultdict(list)
    for edge_uses in uses.values():
        if len(edge_uses) == 2:
            (a, u, v), (b, x, y) = edge_uses
            relation = int((u, v) == (x, y))
            adjacency[a].append((b, relation))
            adjacency[b].append((a, relation))
    flips = {0: 0}
    queue = deque([0])
    while queue:
        face = queue.popleft()
        for other, relation in sorted(adjacency[face]):
            wanted = flips[face] ^ relation
            if other in flips and flips[other] != wanted:
                raise ValueError("symbolic topology is not orientable")
            if other not in flips:
                flips[other] = wanted
                queue.append(other)
    if len(flips) != len(faces):
        raise ValueError("symbolic topology is disconnected")
    return tuple(tuple(reversed(face)) if flips[i] else tuple(face) for i, face in enumerate(faces))


def symbolic_topology():
    """Return fixed control IDs, oriented quads, and named cuff loops."""
    rings = [[r * 8 + i for i in range(8)] for r in range(6)]
    ids = ([f"ring.{name}.{i}" for name in RING_NAMES for i in range(8)] +
           [f"shoulder.{side}.{i}" for side in ("left", "right") for i in range(4)] +
           [f"thigh.{side}.{i}" for side in ("left", "right") for i in range(4)])
    removed, faces = {(1, 0), (1, 3)}, []
    for level in range(5):
        for i in range(8):
            if (level, i) not in removed:
                j = (i + 1) % 8
                faces.append((rings[level][i], rings[level][j], rings[level + 1][j], rings[level + 1][i]))
    for segment, collar in ((3, range(48, 52)), (0, range(52, 56))):
        j = (segment + 1) % 8
        hole = (rings[1][segment], rings[1][j], rings[2][j], rings[2][segment])
        collar = tuple(collar)
        for i in range(4):
            faces.append((hole[i], hole[(i + 1) % 4], collar[(i + 1) % 4], collar[i]))
    # Symmetric pair-of-pants: each pelvic path follows its matching cuff.
    left_path = (rings[5][2], rings[5][3], rings[5][4], rings[5][5], rings[5][6])
    right_path = (rings[5][2], rings[5][1], rings[5][0], rings[5][7], rings[5][6])
    for path, thigh in ((left_path, range(56, 60)), (right_path, range(60, 64))):
        cuff = tuple(thigh) + (thigh.start,)
        for i in range(4):
            faces.append((path[i], path[i + 1], cuff[i + 1], cuff[i]))
    faces.append((rings[5][2], 56, rings[5][6], 60))
    loops = (("neck", tuple(rings[0])), ("left_arm", (48, 51, 50, 49)),
             ("right_arm", (52, 55, 54, 53)),
             ("left_thigh", (56, 59, 58, 57)),
             ("right_thigh", (60, 61, 62, 63)))
    return tuple(ids), _orient(faces), loops


def validate_topology(vertex_count, faces, loops, expected_valences=None):
    if any(len(face) != 4 or len(set(face)) != 4 for face in faces):
        raise ValueError("all faces must be non-degenerate quads")
    if any(not isinstance(i, int) or i < 0 or i >= vertex_count for f in faces for i in f):
        raise ValueError("quad index out of range")
    uses = _edges(faces)
    if any(len(value) not in (1, 2) for value in uses.values()):
        raise ValueError("non-manifold edge")
    _orient(faces)
    boundary = {edge for edge, value in uses.items() if len(value) == 1}
    boundary_directed = {(a, b) for value in uses.values() if len(value) == 1 for _, a, b in value}
    declared, declared_directed = set(), set()
    for _, loop in loops:
        if len(loop) < 3 or len(set(loop)) != len(loop):
            raise ValueError("boundary loop is not simple")
        edges = [(loop[i], loop[(i + 1) % len(loop)]) for i in range(len(loop))]
        declared.update(tuple(sorted(edge)) for edge in edges); declared_directed.update(edges)
    if declared != boundary:
        raise ValueError("declared boundary loops do not match mesh boundary")
    if declared_directed != boundary_directed:
        raise ValueError("declared boundary loops do not follow directed winding")
    neighbors = defaultdict(set)
    for a, b in uses:
        neighbors[a].add(b); neighbors[b].add(a)
    if set(neighbors) != set(range(vertex_count)):
        raise ValueError("isolated control")
    inventory = tuple(sorted(Counter(len(v) for v in neighbors.values()).items()))
    if expected_valences is not None and inventory != tuple(expected_valences):
        raise ValueError(f"unexpected valence inventory: {inventory}")
    report = TopologyReport(vertex_count, len(uses), len(faces), len(boundary),
                            vertex_count - len(uses) + len(faces),
                            tuple(len(loop) for _, loop in loops), inventory)
    if report.euler != 2 - len(loops):
        raise ValueError("Euler characteristic does not match boundary count")
    return report


def _vector(value, path):
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be a finite 3-vector") from exc
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError(f"{path} must be a finite 3-vector")
    return result


def _number(value, path, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{path} must be finite")
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f"{path} must be positive")
    return value


def _record(mapping, key, kind):
    try:
        value = mapping[key]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"missing {kind} {key}") from exc
    if not isinstance(value, Mapping) or not isinstance(value.get("provenance"), str):
        raise ValueError(f"{kind} {key} requires provenance")
    return value


def _prepared(prepared):
    if not isinstance(prepared, Mapping):
        raise ValueError("prepared input must be a mapping")
    forbidden = {"profile", "profile_id", "profile-id"}
    pending = [prepared]
    while pending:
        item = pending.pop()
        if isinstance(item, Mapping):
            if any(str(key).lower() in forbidden for key in item):
                raise ValueError("profile identity is forbidden geometry input")
            pending.extend(item.values())
        elif isinstance(item, (tuple, list)):
            pending.extend(item)
    stations, landmarks = prepared.get("stations"), prepared.get("landmarks")
    frames, scalars = prepared.get("frames"), prepared.get("scalars")
    if not all(isinstance(x, Mapping) for x in (stations, landmarks, frames, scalars)):
        raise ValueError("stations, landmarks, frames, and scalars mappings are required")
    if len(stations) > 10 or len(landmarks) > 24 or len(frames) > 8:
        raise ValueError("prepared input exceeds admission caps")
    frame = _record(frames, "body", "frame")
    axes = tuple(_vector(frame[name], f"frames.body.{name}")
                 for name in ("lateral_axis", "up_axis", "forward_axis"))
    L, U, F = (axis / np.linalg.norm(axis) for axis in axes)
    if any(not np.isfinite(axis).all() for axis in (L, U, F)) or np.dot(np.cross(L, U), F) < 0.999:
        raise ValueError("body frame must be orthonormal and right-handed")
    constants = dict(CONSTANTS)
    for key in constants:
        if key in scalars:
            rec = _record(scalars, key, "scalar")
            constants[key] = _number(rec.get("value"), f"scalars.{key}.value")
        low, high = RANGES[key]
        if not low <= constants[key] <= high:
            raise ValueError(f"scalar {key} outside frozen range")
    return stations, landmarks, scalars, (L, U, F), constants, frame["provenance"]


def build_cage(prepared):
    stations, landmarks, scalars, (L, _, F), constants, frame_prov = _prepared(prepared)
    ids, faces, loops = symbolic_topology()
    validate_topology(64, faces, loops, EXPECTED_VALENCES)
    points, formulas, dependencies, provenance = [], [], [], []

    def station_values(name):
        rec = _record(stations, name, "station")
        center = _vector(rec.get("center"), f"stations.{name}.center")
        values = tuple(_number(rec.get(key), f"stations.{name}.{key}", True)
                       for key in ("lateral_radius", "front_extent", "back_extent"))
        deps = tuple(f"stations.{name}.{key}" for key in
                     ("center", "lateral_radius", "front_extent", "back_extent"))
        return center, values, deps, rec["provenance"]

    ring_sources = RING_NAMES[:4] + ("lower_pelvis",)
    ring_data = {name: station_values(name) for name in ring_sources}
    lower = station_values("lower_abdomen")
    upper = station_values("upper_pelvis")
    lam = constants["lambda"]
    iliac_center = (1 - lam) * lower[0] + lam * upper[0]
    iliac_values = tuple((1 - lam) * a + lam * b for a, b in zip(lower[1], upper[1]))
    ring_data["iliac_overlap"] = (iliac_center, iliac_values,
                                   lower[2] + upper[2] + ("scalars.lambda",),
                                   f"{lower[3]}|{upper[3]}")
    for name in RING_NAMES:
        center, (radius, front, back), deps, prov = ring_data[name]
        depth_center = center + ((front - back) / 2) * F
        depth = (front + back) / 2
        for i in range(8):
            theta = i * pi / 4
            x, z = cos(theta), sin(theta)
            x = 0.0 if abs(x) < 1e-12 else x
            z = 0.0 if abs(z) < 1e-12 else z
            power = 2 / constants["n"]
            point = depth_center + radius * np.sign(x) * abs(x) ** power * L
            point += depth * np.sign(z) * abs(z) ** power * F
            points.append(point); formulas.append("iliac.blend.superellipse" if name == "iliac_overlap" else "station.asymmetric_superellipse")
            dependencies.append(deps + ("frames.body", "scalars.n")); provenance.append((prov, frame_prov))

    def landmark(name):
        rec = _record(landmarks, name, "landmark")
        return _vector(rec.get("point"), f"landmarks.{name}.point"), rec["provenance"]

    arm_depth = _number(_record(scalars, "arm_root_depth", "scalar").get("value"),
                        "scalars.arm_root_depth.value", True)
    arm_out = _number(_record(scalars, "arm_root_outward", "scalar").get("value"),
                      "scalars.arm_root_outward.value", True)
    for side, sign in (("left", -1), ("right", 1)):
        peak, peak_prov = landmark(f"shoulder_peak_{side}")
        axilla, axilla_prov = landmark(f"axilla_{side}")
        upper_center = peak + sign * constants["shoulder"] * arm_out * L
        lower_center = axilla + sign * constants["axilla"] * arm_out * L
        collar = (upper_center - F * arm_depth, upper_center + F * arm_depth,
                  lower_center + F * arm_depth, lower_center - F * arm_depth)
        if side == "left":
            collar = (collar[1], collar[0], collar[3], collar[2])
        for point in collar:
            points.append(point); formulas.append("shoulder.peak_axilla_collar")
            dependencies.append((f"landmarks.shoulder_peak_{side}", f"landmarks.axilla_{side}",
                                 "scalars.arm_root_depth", "scalars.arm_root_outward",
                                 "scalars.shoulder", "scalars.axilla", "frames.body"))
            provenance.append((peak_prov, axilla_prov, frame_prov))

    thigh_radius = _number(_record(scalars, "thigh_lateral_radius", "scalar").get("value"),
                           "scalars.thigh_lateral_radius.value", True)
    thigh_depth = _number(_record(scalars, "thigh_depth", "scalar").get("value"),
                          "scalars.thigh_depth.value", True)
    pelvis_center, (pelvis_radius, _, _), _, pelvis_prov = ring_data["lower_pelvis"]
    for side, sign in (("left", -1), ("right", 1)):
        start, start_prov = landmark(f"thigh_start_{side}")
        mid, mid_prov = landmark(f"thigh_mid_{side}")
        route = mid - start
        length = np.linalg.norm(route)
        if not isfinite(length) or length <= 0:
            raise ValueError(f"thigh route {side} must have positive length")
        seat = start + constants["eta"] * length * route / length
        lateral_offset = sign * float(np.dot(seat - pelvis_center, L))
        medial_radius = min(thigh_radius, lateral_offset - constants["gamma"] * pelvis_radius)
        if medial_radius <= 0:
            raise ValueError(f"thigh medial radius {side} is non-positive")
        loop = (seat - sign * medial_radius * L, seat + thigh_depth * F,
                seat + sign * thigh_radius * L, seat - thigh_depth * F)
        for point in loop:
            points.append(point); formulas.append("thigh.seat_gap_loop")
            dependencies.append((f"landmarks.thigh_start_{side}", f"landmarks.thigh_mid_{side}",
                                 "scalars.thigh_lateral_radius", "scalars.thigh_depth",
                                 "scalars.eta", "scalars.gamma", "stations.lower_pelvis", "frames.body"))
            provenance.append((start_prov, mid_prov, pelvis_prov, frame_prov))
    vertices = tuple(tuple(float(v) for v in point) for point in points)
    mesh = Mesh(vertices, faces, ids, tuple(formulas), tuple(dependencies),
                tuple(provenance), loops)
    validate_geometry(mesh)
    return mesh


def _scale(mesh):
    loop_map = dict(mesh.boundary_loops)
    centroids = []
    for name in ("neck", "left_thigh", "right_thigh"):
        centroids.append(np.mean([mesh.vertices[i] for i in loop_map[name]], axis=0))
    value = np.linalg.norm(centroids[0] - (centroids[1] + centroids[2]) / 2)
    if not isfinite(value) or value <= 0:
        raise ValueError("trial scale must be positive")
    return value


def validate_geometry(mesh, evaluated=False):
    validate_topology(len(mesh.vertices), mesh.quads, mesh.boundary_loops)
    vertices = np.asarray(mesh.vertices, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1:] != (3,) or not np.isfinite(vertices).all():
        raise ValueError("vertices must be finite 3-vectors")
    scale = _scale(mesh)
    for a, b in _edges(mesh.quads):
        if np.linalg.norm(vertices[a] - vertices[b]) <= 1e-8 * scale:
            raise ValueError("edge below length threshold")
    for face in mesh.quads:
        a, b, c, d = vertices[list(face)]
        area = (np.linalg.norm(np.cross(b - a, c - a)) +
                np.linalg.norm(np.cross(c - a, d - a))) / 2
        if area <= 1e-10 * scale * scale:
            raise ValueError("quad below area threshold")
    if evaluated:
        expected = tuple(triangle for q in mesh.quads for triangle in
                         ((q[0], q[1], q[2]), (q[0], q[2], q[3])))
        if mesh.triangles != expected:
            raise ValueError("triangle conversion mismatch")
        for triangle in mesh.triangles:
            a, b, c = vertices[list(triangle)]
            if np.linalg.norm(np.cross(b - a, c - a)) / 2 <= 1e-12 * scale * scale:
                raise ValueError("triangle below area threshold")
    return scale


def subdivide(mesh, level=1):
    if level not in (1, 2):
        raise ValueError("subdivision level must be one or two")
    result = mesh
    for iteration in range(level):
        result = _subdivide_once(result, iteration + 1)
    return result


def _subdivide_once(mesh, level):
    vertices = np.asarray(mesh.vertices, dtype=float)
    uses = _edges(mesh.quads)
    edge_keys = tuple(sorted(uses))
    face_points = np.asarray([np.mean(vertices[list(face)], axis=0) for face in mesh.quads])
    boundary_neighbors = defaultdict(list)
    for edge, edge_uses in uses.items():
        if len(edge_uses) == 1:
            a, b = edge; boundary_neighbors[a].append(b); boundary_neighbors[b].append(a)
    incident_faces = defaultdict(list)
    incident_edges = defaultdict(list)
    for fi, face in enumerate(mesh.quads):
        for vertex in face:
            incident_faces[vertex].append(fi)
    for edge in edge_keys:
        for vertex in edge:
            incident_edges[vertex].append(edge)
    new_vertices, ids, formulas, deps, prov = [], [], [], [], []
    for i, point in enumerate(vertices):
        if i in boundary_neighbors:
            neighbors = sorted(boundary_neighbors[i])
            value = (6 * point + vertices[neighbors[0]] + vertices[neighbors[1]]) / 8
            formula = "catmull_clark.open_boundary_vertex"
            dependency = (mesh.control_ids[i], mesh.control_ids[neighbors[0]], mesh.control_ids[neighbors[1]])
        else:
            faces = incident_faces[i]; edges = incident_edges[i]; n = len(faces)
            favg = np.mean(face_points[faces], axis=0)
            ravg = np.mean([(vertices[a] + vertices[b]) / 2 for a, b in edges], axis=0)
            value = (favg + 2 * ravg + (n - 3) * point) / n
            formula = "catmull_clark.interior_vertex"
            dependency = (mesh.control_ids[i],) + tuple(mesh.control_ids[j] for e in edges for j in e if j != i)
        new_vertices.append(value); ids.append(f"L{level}.v.{mesh.control_ids[i]}")
        formulas.append(formula); deps.append(tuple(dict.fromkeys(dependency))); prov.append(mesh.provenance_ids[i])
    edge_index = {}
    for edge in edge_keys:
        edge_index[edge] = len(new_vertices)
        a, b = edge; edge_uses = uses[edge]
        if len(edge_uses) == 1:
            value = (vertices[a] + vertices[b]) / 2; formula = "catmull_clark.open_boundary_edge"
            dependency = (mesh.control_ids[a], mesh.control_ids[b])
        else:
            value = (vertices[a] + vertices[b] + face_points[edge_uses[0][0]] + face_points[edge_uses[1][0]]) / 4
            formula = "catmull_clark.interior_edge"
            dependency = (mesh.control_ids[a], mesh.control_ids[b]) + tuple(
                mesh.control_ids[v] for use in edge_uses for v in mesh.quads[use[0]])
        new_vertices.append(value); ids.append(f"L{level}.e.{mesh.control_ids[a]}|{mesh.control_ids[b]}")
        formulas.append(formula); deps.append(tuple(dict.fromkeys(dependency)))
        prov.append(tuple(dict.fromkeys(mesh.provenance_ids[a] + mesh.provenance_ids[b])))
    face_indices = []
    for fi, face in enumerate(mesh.quads):
        face_indices.append(len(new_vertices)); new_vertices.append(face_points[fi])
        ids.append(f"L{level}.f.{fi}"); formulas.append("catmull_clark.face_point")
        deps.append(tuple(mesh.control_ids[v] for v in face))
        prov.append(tuple(dict.fromkeys(p for v in face for p in mesh.provenance_ids[v])))
    quads = []
    for fi, face in enumerate(mesh.quads):
        for i, vertex in enumerate(face):
            previous = face[i - 1]; following = face[(i + 1) % 4]
            quads.append((vertex, edge_index[tuple(sorted((vertex, following)))],
                          face_indices[fi], edge_index[tuple(sorted((previous, vertex)))]))
    loops = []
    for name, loop in mesh.boundary_loops:
        expanded = []
        for i, vertex in enumerate(loop):
            expanded += [vertex, edge_index[tuple(sorted((vertex, loop[(i + 1) % len(loop)])))]]
        loops.append((name, tuple(expanded)))
    output_vertices = tuple(tuple(float(x) for x in point) for point in new_vertices)
    triangles = tuple(triangle for q in quads for triangle in ((q[0], q[1], q[2]), (q[0], q[2], q[3])))
    output = Mesh(output_vertices, tuple(quads), tuple(ids), tuple(formulas), tuple(deps),
                  tuple(prov), tuple(loops), triangles)
    validate_geometry(output, evaluated=True)
    return output


def evaluate(prepared, levels=2):
    if levels not in (1, 2):
        raise ValueError("levels must be one or two")
    cage = build_cage(prepared)
    outputs = []
    current = cage
    for level in range(1, levels + 1):
        current = _subdivide_once(current, level)
        outputs.append(current)
    return SurfaceEvaluation(cage, tuple(outputs))

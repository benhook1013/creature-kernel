"""Experiment-local root-complex cage grammar and deterministic evaluator."""

from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass
from math import cos, isfinite, pi, sin

import numpy as np

import mesh_correctness


RING_NAMES = (
    "neck_collar",
    "upper_ribcage_shoulder",
    "axilla_transition",
    "lower_ribcage",
    "waist_abdomen",
    "iliac_overlap",
    "lower_pelvis",
)
CONSTANTS = {"n": 2.6, "lambda": 0.25, "shoulder": 0.80, "axilla": 0.55, "eta": 0.25, "gamma": 0.08, "saddle": 0.45}
RANGES = {"n": (2.0, 3.2), "lambda": (0.0, 0.5), "shoulder": (0.70, 1.00),
          "axilla": (0.35, 0.75), "eta": (0.0, 0.5), "gamma": (0.04, 0.12), "saddle": (0.30, 0.60)}
EXPECTED_VALENCES = ((3, 22), (4, 40), (5, 10))
_FORBIDDEN_KEYS = frozenset("vertex vertices face faces edge edges ring rings connectivity perimeter perimetersample perimetersamples orderedperimetersample orderedperimetersamples pointcloud pointclouds field fields mask masks silhouette silhouettes correctiveoffset correctiveoffsets serialized serializedoutput serializedoutputs serializedoldoutput serializedoldoutputs profiles profileids".split())
_PREPARED_FIELDS = frozenset("source basis frames landmarks stations scalars".split())
_SOURCE_FIELDS = frozenset("document namespace sha256 provenance".split())
_BASIS_FIELDS = frozenset("length_unit handedness up forward".split())
_FRAME_NAMES = frozenset(("body",))
_LANDMARK_NAMES = frozenset(f"{kind}_{side}" for side in ("left", "right") for kind in ("shoulder_peak", "axilla", "thigh_start", "thigh_mid"))
_STATION_NAMES = frozenset("neck_collar upper_ribcage_shoulder lower_ribcage waist_abdomen lower_abdomen upper_pelvis lower_pelvis".split())
_SCALAR_NAMES = frozenset((*CONSTANTS, "arm_root_depth", "arm_root_outward", "thigh_lateral_radius", "thigh_depth")); _REQUIRED_SCALARS = _SCALAR_NAMES - CONSTANTS.keys()
_RECORD_FIELDS = {kind: frozenset(fields.split()) for kind, fields in (
    ("frame", "lateral_axis up_axis forward_axis provenance"), ("landmark", "point provenance"),
    ("station", "center lateral_radius front_extent back_extent provenance"), ("scalar", "value provenance"))}


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
    intersection_counts: tuple[int, ...] = ()
    clearance_ratios: tuple[tuple[str, float], ...] = ()


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
    flips, queue = {0: 0}, deque([0])
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
    rings = [[r * 8 + i for i in range(8)] for r in range(7)]
    ids = ([f"ring.{name}.{i}" for name in RING_NAMES for i in range(8)] +
           [f"shoulder.{side}.{i}" for side in ("left", "right") for i in range(4)] +
           [f"thigh.{side}.{i}" for side in ("left", "right") for i in range(4)])
    removed, faces = {(1, 0), (1, 3)}, []
    for level in range(6):
        for i in range(8):
            if (level, i) not in removed:
                j = (i + 1) % 8
                faces.append((rings[level][i], rings[level][j], rings[level + 1][j], rings[level + 1][i]))
    for segment, collar in ((3, range(56, 60)), (0, range(60, 64))):
        j = (segment + 1) % 8
        hole = (rings[1][segment], rings[1][j], rings[2][j], rings[2][segment])
        collar = tuple(collar)
        for i in range(4):
            faces.append((hole[i], hole[(i + 1) % 4], collar[(i + 1) % 4], collar[i]))
    # Symmetric pair-of-pants: each pelvic path follows its matching cuff.
    left_path = (rings[6][2], rings[6][3], rings[6][4], rings[6][5], rings[6][6])
    right_path = (rings[6][2], rings[6][1], rings[6][0], rings[6][7], rings[6][6])
    for path, thigh in ((left_path, range(64, 68)), (right_path, range(68, 72))):
        cuff = tuple(thigh) + (thigh.start,)
        for i in range(4):
            faces.append((path[i], path[i + 1], cuff[i + 1], cuff[i]))
    faces.append((rings[6][2], 64, rings[6][6], 68))
    loops = (("neck", tuple(rings[0])), ("left_arm", (56, 59, 58, 57)),
             ("right_arm", (60, 63, 62, 61)),
             ("left_thigh", (64, 67, 66, 65)),
             ("right_thigh", (68, 69, 70, 71)))
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
                            vertex_count - len(uses) + len(faces), tuple(len(loop) for _, loop in loops), inventory)
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
    if (not isinstance(value, Mapping) or set(value) != _RECORD_FIELDS[kind] or not
            (isinstance(value.get("provenance"), str) and value["provenance"].strip())):
        raise ValueError(f"{kind} {key} has unknown or missing fields or requires provenance")
    return value


def _exact_keys(value, expected, path, required=None):
    keys = set(value) if isinstance(value, Mapping) else None
    if keys is None or not keys <= expected or not (expected if required is None else required) <= keys: raise ValueError(f"{path} has unknown or missing fields")


def _prepared(prepared):
    if not isinstance(prepared, Mapping):
        raise ValueError("prepared input must be a mapping")
    pending = [prepared]
    for item in pending:
        if isinstance(item, Mapping):
            keys = {"".join(char for char in str(key).lower() if char.isalnum()) for key in item}
            if keys & {"profile", "profileid"}:
                raise ValueError("profile identity is forbidden geometry input")
            if keys & _FORBIDDEN_KEYS:
                raise ValueError("forbidden prepared geometry input")
            pending.extend(item.values())
        elif isinstance(item, (tuple, list)):
            pending.extend(item)
    _exact_keys(prepared, _PREPARED_FIELDS, "prepared input"); _exact_keys(prepared["source"], _SOURCE_FIELDS, "prepared.source"); _exact_keys(prepared["basis"], _BASIS_FIELDS, "prepared.basis")
    for name, expected, required in (("frames", _FRAME_NAMES, None), ("landmarks", _LANDMARK_NAMES, None), ("stations", _STATION_NAMES, None), ("scalars", _SCALAR_NAMES, _REQUIRED_SCALARS)):
        _exact_keys(prepared[name], expected, f"prepared.{name}", required)
    stations, landmarks = prepared.get("stations"), prepared.get("landmarks"); frames, scalars = prepared.get("frames"), prepared.get("scalars")
    if not all(isinstance(x, Mapping) for x in (stations, landmarks, frames, scalars)):
        raise ValueError("stations, landmarks, frames, and scalars mappings are required")
    if len(stations) > 10 or len(landmarks) > 24 or len(frames) > 8:
        raise ValueError("prepared input exceeds admission caps")
    frame = _record(frames, "body", "frame")
    axes = tuple(_vector(frame[name], f"frames.body.{name}") for name in
                 ("lateral_axis", "up_axis", "forward_axis"))
    L, U, F = (axis / np.linalg.norm(axis) for axis in axes)
    if any(not np.isfinite(axis).all() for axis in (L, U, F)) or np.dot(np.cross(L, U), F) < 0.999:
        raise ValueError("body frame must be orthonormal and right-handed")
    constants, constant_provenance = dict(CONSTANTS), {key: f"formula_constant.{key}.v1" for key in CONSTANTS}
    for key in constants:
        if key in scalars:
            rec = _record(scalars, key, "scalar")
            constants[key] = _number(rec.get("value"), f"scalars.{key}.value")
            constant_provenance[key] = rec["provenance"]
        low, high = RANGES[key]
        if not low <= constants[key] <= high:
            raise ValueError(f"scalar {key} outside frozen range")
    return stations, landmarks, scalars, (L, U, F), constants, constant_provenance, frame["provenance"]


def build_cage(prepared):
    stations, landmarks, scalars, (L, U, F), constants, constant_provenance, frame_prov = _prepared(prepared)
    ids, faces, loops = symbolic_topology()
    validate_topology(72, faces, loops, EXPECTED_VALENCES)
    points, formulas, dependencies, provenance = [], [], [], []

    def station_values(name):
        rec = _record(stations, name, "station")
        center = _vector(rec.get("center"), f"stations.{name}.center")
        values = tuple(_number(rec.get(key), f"stations.{name}.{key}", True) for key in
                       ("lateral_radius", "front_extent", "back_extent"))
        deps = tuple(f"stations.{name}.{key}" for key in
                     ("center", "lateral_radius", "front_extent", "back_extent"))
        return center, values, deps, rec["provenance"]

    def landmark(name):
        rec = _record(landmarks, name, "landmark")
        return _vector(rec.get("point"), f"landmarks.{name}.point"), rec["provenance"]

    ring_sources = ("neck_collar", "upper_ribcage_shoulder", "lower_ribcage", "waist_abdomen",
                    "lower_abdomen", "upper_pelvis", "lower_pelvis")
    ring_data = {name: station_values(name) for name in ring_sources}
    thigh_radius_record = _record(scalars, "thigh_lateral_radius", "scalar"); thigh_depth_record = _record(scalars, "thigh_depth", "scalar")
    thigh_radius = _number(thigh_radius_record.get("value"), "scalars.thigh_lateral_radius.value", True); thigh_depth = _number(thigh_depth_record.get("value"), "scalars.thigh_depth.value", True)
    thigh_data = {}
    for side in ("left", "right"):
        start, start_prov = landmark(f"thigh_start_{side}"); mid, mid_prov = landmark(f"thigh_mid_{side}")
        route = mid - start
        if not isfinite(np.linalg.norm(route)) or np.linalg.norm(route) <= 0: raise ValueError(f"thigh route {side} must have positive length")
        thigh_data[side] = (start, mid, start + constants["eta"] * route, start_prov, mid_prov)

    clamp_names = ("lower_ribcage", "lower_abdomen", "lower_pelvis"); clamped_ring_names = set()
    envelope = [(float(np.dot(ring_data[name][0], U)), *ring_data[name][1:]) for name in
                ("upper_ribcage_shoulder", "waist_abdomen", "upper_pelvis")]
    seats = tuple(thigh_data[side][2] for side in ("left", "right"))
    seat_deps = tuple(f"landmarks.thigh_{point}_{side}" for side in ("left", "right") for point in
                      ("start", "mid")) + ("scalars.thigh_lateral_radius", "scalars.thigh_depth", "scalars.eta")
    seat_prov = "|".join((*[item for side in ("left", "right") for item in thigh_data[side][3:]],
                          thigh_radius_record["provenance"], thigh_depth_record["provenance"],
                          constant_provenance["eta"]))
    seat_extents = (max(abs(float(np.dot(seat, L))) for seat in seats) + thigh_radius,
                    thigh_depth, thigh_depth)
    envelope.append((float(np.mean([np.dot(seat, U) for seat in seats])), seat_extents,
                     seat_deps, seat_prov))
    if any(high[0] <= low[0] for high, low in zip(envelope, envelope[1:])): raise ValueError("axial envelope anchors must descend strictly")
    for name in clamp_names:
        center, values, deps, prov = ring_data[name]
        position = float(np.dot(center, U))
        segment = next(((high, low) for high, low in zip(envelope, envelope[1:])
                        if low[0] <= position <= high[0]), None)
        if segment is None: raise ValueError(f"axial envelope does not bracket station {name}")
        high, low = segment; fraction = (position - low[0]) / (high[0] - low[0])
        limit = tuple(lo + fraction * (hi - lo) for hi, lo in zip(high[1], low[1]))
        clamped = tuple(min(value, bound) for value, bound in zip(values, limit))
        if not any(bound <= value for value, bound in zip(values, limit)): continue
        active = tuple(anchor for weight, anchor in ((fraction, high), (1 - fraction, low)) if weight)
        exact_deps = tuple(dict.fromkeys(deps + tuple(item for anchor in active for item in anchor[2]) + ("frames.body",)))
        exact_prov = "|".join(dict.fromkeys((prov, *(anchor[3] for anchor in active))))
        ring_data[name] = (center, clamped, exact_deps, exact_prov)
        clamped_ring_names.add(name)
    lower, upper = ring_data["lower_ribcage"], ring_data["upper_ribcage_shoulder"]
    axilla_left, axilla_left_prov = landmark("axilla_left"); axilla_right, axilla_right_prov = landmark("axilla_right")
    target = float(np.mean((np.dot(axilla_left, U), np.dot(axilla_right, U))))
    denominator = float(np.dot(upper[0] - lower[0], U))
    t = (target - float(np.dot(lower[0], U))) / denominator if denominator else float("nan")
    if not isfinite(t) or not 0.0 < t < 1.0:
        raise ValueError("axilla transition interpolation must have 0 < t < 1")
    transition_center = (1 - t) * lower[0] + t * upper[0]
    transition_values = tuple((1 - t) * a + t * b for a, b in zip(lower[1], upper[1]))
    transition_deps = tuple(dict.fromkeys(lower[2] + upper[2] + ("landmarks.axilla_left",
                                                                  "landmarks.axilla_right", "frames.body")))
    transition_prov = "|".join((lower[3], upper[3], axilla_left_prov, axilla_right_prov))
    ring_data["axilla_transition"] = transition_center, transition_values, transition_deps, transition_prov
    lower, upper = ring_data["lower_abdomen"], ring_data["upper_pelvis"]
    lam = constants["lambda"]; iliac_center = (1 - lam) * lower[0] + lam * upper[0]
    iliac_values = tuple((1 - lam) * a + lam * b for a, b in zip(lower[1], upper[1]))
    ring_data["iliac_overlap"] = (iliac_center, iliac_values, lower[2] + upper[2] + ("scalars.lambda",),
                                  f"{lower[3]}|{upper[3]}|{constant_provenance['lambda']}")

    arm_depth_record = _record(scalars, "arm_root_depth", "scalar"); arm_out_record = _record(scalars, "arm_root_outward", "scalar")
    arm_depth = _number(arm_depth_record.get("value"), "scalars.arm_root_depth.value", True); arm_out = _number(arm_out_record.get("value"), "scalars.arm_root_outward.value", True)
    neck_center, neck_prov = ring_data["neck_collar"][0], ring_data["neck_collar"][3]; upper_center = ring_data["upper_ribcage_shoulder"][0]
    neck_separation = float(np.dot(neck_center - upper_center, U))
    if not isfinite(neck_separation) or neck_separation <= 0:
        raise ValueError("neck must be above upper ribcage")
    branch_data, socket_data = {}, {}
    for side, sign, front_index, back_index in (("left", -1, 3, 4), ("right", 1, 1, 0)):
        peak, peak_prov = landmark(f"shoulder_peak_{side}"); axilla, axilla_prov = landmark(f"axilla_{side}")
        sigma = constants["shoulder"]
        upper_center = axilla + sigma * (peak - axilla) + sign * sigma * arm_out * L
        lower_center = axilla + sign * constants["axilla"] * arm_out * L
        upper_dependencies = (f"landmarks.shoulder_peak_{side}", f"landmarks.axilla_{side}",
                              "scalars.arm_root_depth", "scalars.arm_root_outward",
                              "scalars.shoulder", "frames.body")
        lower_dependencies = (f"landmarks.axilla_{side}", "scalars.arm_root_depth",
                              "scalars.arm_root_outward", "scalars.axilla", "frames.body")
        upper_provenance = (peak_prov, axilla_prov, arm_depth_record["provenance"],
                            arm_out_record["provenance"], constant_provenance["shoulder"], frame_prov)
        lower_provenance = (axilla_prov, arm_depth_record["provenance"],
                            arm_out_record["provenance"], constant_provenance["axilla"], frame_prov)
        branch_data[side] = (upper_center, lower_center, upper_dependencies, lower_dependencies,
                             upper_provenance, lower_provenance)
        for ring_name, center, branch_dependencies, branch_provenance in (
                ("upper_ribcage_shoulder", upper_center, upper_dependencies, upper_provenance),
                ("axilla_transition", lower_center, lower_dependencies, lower_provenance)):
            station_center, (radius, front, back), station_deps, station_prov = ring_data[ring_name]
            anchor = station_center + ((front - back) / 2) * F + sign * radius * L
            for index, depth_sign in ((front_index, 1), (back_index, -1)):
                point = (float(np.dot(anchor, L)) * L + float(np.dot(center, U)) * U +
                         (float(np.dot(center, F)) + depth_sign * arm_depth) * F)
                socket_data[(ring_name, index)] = (point, station_deps + branch_dependencies,
                                                   (station_prov,) + branch_provenance)
    for name in RING_NAMES:
        center, (radius, front, back), deps, prov = ring_data[name]
        depth_center = center + ((front - back) / 2) * F
        depth = (front + back) / 2
        for i in range(8):
            theta = i * pi / 4; x, z = cos(theta), sin(theta)
            x = 0.0 if abs(x) < 1e-12 else x; z = 0.0 if abs(z) < 1e-12 else z
            power = 2 / constants["n"]
            point = depth_center + radius * np.sign(x) * abs(x) ** power * L
            point += depth * np.sign(z) * abs(z) ** power * F
            formula = ("station.axial_envelope.min_clamp" if name in clamped_ring_names else
                       "iliac.blend.superellipse" if name == "iliac_overlap" else
                       "shoulder.axilla_transition" if name == "axilla_transition" else "station.asymmetric_superellipse")
            dependencies_for_point = tuple(dict.fromkeys(deps + ("frames.body", "scalars.n")))
            provenance_for_point = (prov, frame_prov, constant_provenance["n"])
            if (name, i) in socket_data:
                point, dependencies_for_point, provenance_for_point = socket_data[(name, i)]
                formula = "shoulder.peak_axilla_collar"
            elif name == "upper_ribcage_shoulder":
                r = min(1.0, max(0.0, abs(float(np.dot(point - center, L))) / radius))
                point = point + constants["saddle"] * (1.0 - r) * neck_separation * U
                formula = "shoulder.superior_axial_saddle"
                dependencies_for_point = tuple(dict.fromkeys(
                    deps + ("stations.neck_collar.center", "frames.body", "scalars.n", "scalars.saddle")))
                provenance_for_point = (prov, neck_prov, frame_prov,
                                        constant_provenance["n"], constant_provenance["saddle"])
            points.append(point); formulas.append(formula)
            dependencies.append(dependencies_for_point); provenance.append(provenance_for_point)

    for side, sign in (("left", -1), ("right", 1)):
        (upper_center, lower_center, upper_dependencies, lower_dependencies,
         upper_provenance, lower_provenance) = branch_data[side]
        collar = (upper_center - F * arm_depth, upper_center + F * arm_depth,
                  lower_center + F * arm_depth, lower_center - F * arm_depth)
        if side == "left":
            collar = (collar[1], collar[0], collar[3], collar[2])
        for point, point_dependencies, point_provenance in zip(
                collar, (upper_dependencies,) * 2 + (lower_dependencies,) * 2,
                (upper_provenance,) * 2 + (lower_provenance,) * 2):
            points.append(point); formulas.append("shoulder.peak_axilla_collar")
            dependencies.append(point_dependencies); provenance.append(point_provenance)

    for sign, pairs in ((-1, ((11, 56), (12, 57), (19, 59), (20, 58))),
                        (1, ((8, 60), (9, 61), (17, 62), (16, 63)))):
        directions = []
        for socket, collar in pairs:
            delta = points[collar] - points[socket]; lateral_component = float(np.dot(delta, L)) * L
            if np.linalg.norm(delta - lateral_component) > 1e-10:
                raise ValueError("shoulder socket bridge is not purely lateral")
            directions.append(sign * float(np.dot(delta, L)))
        if not directions or any(value * directions[0] <= 0 for value in directions):
            raise ValueError("shoulder socket bridges do not share a direction")

    pelvis_center, (pelvis_radius, _, _), pelvis_deps, pelvis_prov = ring_data["lower_pelvis"]
    for side, sign in (("left", -1), ("right", 1)):
        start, mid, seat, start_prov, mid_prov = thigh_data[side]
        lateral_offset = sign * float(np.dot(seat - pelvis_center, L))
        medial_radius = min(thigh_radius, lateral_offset - constants["gamma"] * pelvis_radius)
        if medial_radius <= 0:
            raise ValueError(f"thigh medial radius {side} is non-positive")
        loop = (seat - sign * medial_radius * L, seat + thigh_depth * F,
                seat + sign * thigh_radius * L, seat - thigh_depth * F)
        for point in loop:
            points.append(point); formulas.append("thigh.seat_gap_loop")
            dependencies.append(tuple(dict.fromkeys((
                f"landmarks.thigh_start_{side}", f"landmarks.thigh_mid_{side}",
                "scalars.thigh_lateral_radius", "scalars.thigh_depth", "scalars.eta",
                "scalars.gamma", *pelvis_deps, "frames.body"))))
            provenance.append((start_prov, mid_prov, pelvis_prov, frame_prov,
                               thigh_radius_record["provenance"], thigh_depth_record["provenance"],
                               constant_provenance["eta"], constant_provenance["gamma"]))
    vertices = tuple(tuple(float(v) for v in point) for point in points)
    mesh = Mesh(vertices, faces, ids, tuple(formulas), tuple(dependencies), tuple(provenance), loops); validate_geometry(mesh); return mesh


def _scale(mesh):
    loop_map = dict(mesh.boundary_loops)
    centroids = [np.mean([mesh.vertices[i] for i in loop_map[name]], axis=0)
                 for name in ("neck", "left_thigh", "right_thigh")]
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
    incident_faces, incident_edges = defaultdict(list), defaultdict(list)
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
            dependency_indices = (i, *neighbors)
            dependency = tuple(mesh.control_ids[j] for j in dependency_indices)
        else:
            faces = incident_faces[i]; edges = incident_edges[i]; n = len(faces)
            favg = np.mean(face_points[faces], axis=0)
            ravg = np.mean([(vertices[a] + vertices[b]) / 2 for a, b in edges], axis=0)
            value = (favg + 2 * ravg + (n - 3) * point) / n
            formula = "catmull_clark.interior_vertex"
            dependency_indices = tuple(v for fi in faces for v in mesh.quads[fi])
            dependency = tuple(mesh.control_ids[j] for j in dependency_indices)
        new_vertices.append(value); ids.append(f"L{level}.v.{mesh.control_ids[i]}")
        formulas.append(formula); deps.append(tuple(dict.fromkeys(dependency)))
        prov.append(tuple(dict.fromkeys(p for j in dependency_indices
                                     for p in mesh.provenance_ids[j])))
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
        source_indices = (a, b) if len(edge_uses) == 1 else (a, b, *(
            vertex for use in edge_uses for vertex in mesh.quads[use[0]]))
        prov.append(tuple(dict.fromkeys(p for index in source_indices
                                       for p in mesh.provenance_ids[index])))
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
                  tuple(prov), tuple(loops), triangles); validate_geometry(output, evaluated=True); return output


def evaluate(prepared, levels=2):
    if levels not in (1, 2):
        raise ValueError("levels must be one or two")
    _, _, _, (lateral, up, forward), _, _, _ = _prepared(prepared)
    cage = build_cage(prepared)
    outputs, intersection_counts, clearance_ratios, current = [], [], (), cage
    for level in range(1, levels + 1):
        current = _subdivide_once(current, level)
        scale = validate_geometry(current, evaluated=True)
        pairs = mesh_correctness.validate_triangle_intersections(
            current.vertices, current.triangles, scale)
        intersection_counts.append(len(pairs))
        if level == 2:
            values = mesh_correctness.validate_boundary_clearances(
                current.vertices, dict(current.boundary_loops),
                {"L": lateral, "U": up, "F": forward}, scale)
            clearance_ratios = tuple((name, float(values[name])) for name in (
                "neck", "axilla_left", "axilla_right", "groin", "medial_thigh"))
        outputs.append(current)
    return SurfaceEvaluation(cage, tuple(outputs), tuple(intersection_counts),
                             clearance_ratios)

"""Bounded six-phase connected head, muzzle, and coarse pinna construction."""
from __future__ import annotations

from collections.abc import Mapping
import copy
import json
import math
from pathlib import Path
from typing import Any


_PORT = "port.neck"
_OWNER = "domain.head"
_STATIONS = ("neck_support", "jaw", "cheek", "brow", "crown")
_PHASE_SET = {(-1.0, -1.0), (1.0, -1.0), (1.0, 0.0),
              (1.0, 1.0), (-1.0, 1.0), (-1.0, 0.0)}
_TOL = 1.0e-8
_AREA_TOL = 1.0e-12
_REFINEMENT_SCHEMA = "creature-kernel.connected-leg-assembly-head-refinement-inputs.v1"
_EAR_ATTACHMENT_FRACTION = 0.12
_EAR_TRANSITION_RULE = {
    "id": "host-decomposed-axial-relaxation-v1",
    "attachment_fraction": _EAR_ATTACHMENT_FRACTION,
    "section_fractions": [0.35, 0.68, 1.0],
    "transverse_blends": [0.45, 0.85, 1.0],
    "formula": (
        "C + f*axis_vector + ((1-f)/(1-a))*h_parallel "
        "+ (1-blend)*h_perp + blend*ideal_transverse_offset; "
        "h=P-C, h_parallel=dot(h,axis)*axis, h_perp=h-h_parallel"
    ),
    "evidence_reference": {
        "run": "INTEGRATED-REFINEMENT-001-rejected-diagnostic-001",
        "artifact": "run/anthro/rejected-head-L0.json",
        "raw_head_l0_sha256": "b8dfed686d7216c3ec5512e37bd39ce0e1a1108bd45f9d1a9fcb7b39a980214a",
        "failed_quad": 673,
        "raw_normal_dot": -1.6094300354600122e-7,
        "normalized_normal_dot": -0.5826717579361298,
    },
}


class HeadConstructionError(ValueError):
    """Raised when the bounded head candidate cannot be admitted."""


def _fail(message: str) -> None:
    raise HeadConstructionError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be a mapping")
    return value


def _finite(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{where} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        _fail(f"{where} must be a finite real number")
    return result


def _positive(value: Any, where: str) -> float:
    result = _finite(value, where)
    if result <= 0.0:
        _fail(f"{where} must be positive")
    return result


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    if type(value) not in (list, tuple) or len(value) != 3:
        _fail(f"{where} must be a three-component vector")
    return tuple(_finite(item, f"{where}[{axis}]")
                 for axis, item in enumerate(value))  # type: ignore[return-value]


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[i] + b[i] for i in range(3))  # type: ignore[return-value]


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]


def _scale(v: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(item * factor for item in v)  # type: ignore[return-value]


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(v: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(v, v))


def _normalise(v: tuple[float, float, float], where: str) -> tuple[float, float, float]:
    length = _norm(v)
    if not math.isfinite(length) or length <= _TOL:
        _fail(f"{where} must have positive finite length")
    return _scale(v, 1.0 / length)


def _edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _edge_uses(quads: list[tuple[int, int, int, int]]) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    uses: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for face_index, face in enumerate(quads):
        for corner, left in enumerate(face):
            right = face[(corner + 1) % 4]
            uses.setdefault(_edge(left, right), []).append((face_index, left, right))
    return uses


def _quads(raw: Any, count: int, where: str) -> list[tuple[int, int, int, int]]:
    if type(raw) not in (list, tuple) or not raw:
        _fail(f"{where} must be a non-empty sequence")
    result = []
    for index, face in enumerate(raw):
        if type(face) not in (list, tuple) or len(face) != 4 or any(type(v) is not int for v in face):
            _fail(f"{where}[{index}] must contain four integer indices")
        checked = tuple(face)
        if len(set(checked)) != 4 or any(v < 0 or v >= count for v in checked):
            _fail(f"{where}[{index}] has invalid indices")
        result.append(checked)
    return result  # type: ignore[return-value]


def _loops(raw: Any, count: int) -> dict[str, list[int]]:
    value = _mapping(raw, "base_mesh.loops")
    result = {}
    for name, loop in value.items():
        if type(name) is not str or type(loop) not in (list, tuple) or len(loop) < 3:
            _fail("base_mesh.loops contains an invalid entry")
        checked = list(loop)
        if len(set(checked)) != len(checked) or any(type(v) is not int or v < 0 or v >= count for v in checked):
            _fail(f"base_mesh.loops.{name} has invalid indices")
        result[name] = checked
    return result


def _topology(vertices: list[tuple[float, float, float]], quads: list[tuple[int, int, int, int]],
              loops: Mapping[str, list[int]], where: str) -> None:
    uses = _edge_uses(quads)
    if any(len(rows) not in (1, 2) for rows in uses.values()):
        _fail(f"{where} has a non-manifold edge")
    if any(len(rows) == 2 and rows[0][1:] == rows[1][1:] for rows in uses.values()):
        _fail(f"{where} has an orientation conflict")
    declared = set()
    for name, loop in loops.items():
        for i, left in enumerate(loop):
            edge = _edge(left, loop[(i + 1) % len(loop)])
            if len(uses.get(edge, ())) != 1 or edge in declared:
                _fail(f"{where} loop {name!r} is not a unique boundary")
            declared.add(edge)
    if declared != {edge for edge, rows in uses.items() if len(rows) == 1}:
        _fail(f"{where} named loops do not cover its boundary")
    adjacency = {i: set() for i in range(len(vertices))}
    for left, right in uses:
        adjacency[left].add(right)
        adjacency[right].add(left)
    seen, pending = {0}, [0]
    while pending:
        current = pending.pop()
        for neighbour in adjacency[current]:
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    if len(seen) != len(vertices):
        _fail(f"{where} is disconnected")


def _stencils(raw: Any, count: int) -> list[list[list[float | int]]]:
    if type(raw) not in (list, tuple) or len(raw) != count:
        _fail("base_mesh.base_stencils must cover every vertex")
    result = []
    for row_index, row in enumerate(raw):
        if type(row) not in (list, tuple) or not row:
            _fail(f"base_mesh.base_stencils[{row_index}] is empty")
        checked, previous, total = [], -1, 0.0
        for term in row:
            if type(term) not in (list, tuple) or len(term) != 2 or type(term[0]) is not int:
                _fail(f"base_mesh.base_stencils[{row_index}] is malformed")
            source, coefficient = term[0], _finite(term[1], "stencil coefficient")
            if source <= previous or source < 0 or coefficient <= 0.0:
                _fail(f"base_mesh.base_stencils[{row_index}] is invalid")
            checked.append([source, coefficient])
            previous, total = source, total + coefficient
        if abs(total - 1.0) > 1.0e-9:
            _fail(f"base_mesh.base_stencils[{row_index}] does not partition unity")
        result.append(checked)
    return result


def _source(source_case: Any) -> dict[str, Any]:
    components = _mapping(_mapping(source_case, "source_case").get("components"),
                          "source_case.components")
    prefix = "stations.neck_upper."
    centre = tuple(_finite(components.get(f"{prefix}C.{axis}"), f"{prefix}C.{axis}")
                   for axis in "xyz")
    pivot_prefix = "stations.neck_collar."
    pivot = tuple(_finite(components.get(f"{pivot_prefix}C.{axis}"),
                          f"{pivot_prefix}C.{axis}") for axis in "xyz")
    return {"centre": centre,
            "pivot": pivot,
            "rL": _positive(components.get(f"{prefix}rL"), f"{prefix}rL"),
            "rA": _positive(components.get(f"{prefix}rA"), f"{prefix}rA"),
            "rP": _positive(components.get(f"{prefix}rP"), f"{prefix}rP")}


def _feature(raw: Any, keys: set[str], where: str) -> dict[str, float] | None:
    if raw is None:
        return None
    row = _mapping(raw, where)
    if set(row) != keys:
        _fail(f"{where} has unsupported or missing fields")
    return {key: _positive(row[key], f"{where}.{key}") if key != "tip_up_offset"
            else _finite(row[key], f"{where}.{key}") for key in keys}


def _muzzle_feature(raw: Any) -> dict[str, float] | None:
    if raw is None:
        return None
    base_keys = {"length", "tip_halfwidth", "tip_halfheight", "tip_up_offset"}
    support_keys = {"support_halfwidth", "support_halfheight"}
    row = _mapping(raw, "head_inputs.muzzle")
    if set(row) not in (base_keys, base_keys | support_keys):
        _fail("head_inputs.muzzle has unsupported or missing fields")
    result = {key: _positive(row[key], f"head_inputs.muzzle.{key}")
              for key in (set(row) - {"tip_up_offset"})}
    result["tip_up_offset"] = _finite(row["tip_up_offset"], "head_inputs.muzzle.tip_up_offset")
    return result


def load_head_refinement_inputs(path: str | Path) -> dict[str, Any]:
    """Load the explicit prospective head-refinement cases for later capture."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"),
                           parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _fail(f"invalid head refinement input document: {path}")
    document = _mapping(value, "head refinement document")
    if document.get("schema") != _REFINEMENT_SCHEMA:
        _fail("head refinement document has an unsupported schema")
    cases = document.get("cases")
    if type(cases) is not list or not cases:
        _fail("head refinement document must contain cases")
    seen = set()
    for index, case in enumerate(cases):
        row = _mapping(case, f"head refinement cases[{index}]")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            _fail("head refinement cases must have unique non-empty case_id values")
        seen.add(case_id)
        _inputs(row.get("head"))
    return copy.deepcopy(dict(document))


def head_inputs_for_refinement(path: str | Path, case_id: str) -> dict[str, Any]:
    """Return one validated resulting head case from the captured document."""
    document = load_head_refinement_inputs(path)
    for case in document["cases"]:
        if case["case_id"] == case_id:
            return copy.deepcopy(case["head"])
    _fail(f"head refinement document has no case: {case_id}")


def _inputs(raw: Any) -> dict[str, Any]:
    value = _mapping(raw, "head_inputs")
    if set(value) != {"stations", "crown_centre_up", "muzzle", "ears"}:
        _fail("head_inputs has unsupported or missing fields")
    stations = _mapping(value["stations"], "head_inputs.stations")
    if set(stations) != set(_STATIONS):
        _fail("head_inputs.stations must contain the five fixed stations")
    parsed, previous = {}, 0.0
    for name in _STATIONS:
        row = _mapping(stations[name], f"head_inputs.stations.{name}")
        if set(row) != {"up", "radii"}:
            _fail(f"head_inputs.stations.{name} has unsupported fields")
        up = _positive(row["up"], f"{name}.up")
        if up <= previous:
            _fail("head station upward offsets must be strictly increasing")
        radii = row["radii"]
        if type(radii) not in (list, tuple) or len(radii) != 3:
            _fail(f"{name}.radii must be [lateral, anterior, posterior]")
        parsed[name] = {"up": up, "radii": tuple(_positive(v, f"{name}.radii") for v in radii)}
        previous = up
    crown_up = _positive(value["crown_centre_up"], "crown_centre_up")
    if crown_up <= previous:
        _fail("crown_centre_up must exceed the crown station")
    muzzle = _muzzle_feature(value["muzzle"])
    ears = _feature(value["ears"], {"tip_up", "lateral_outset", "base_halfwidth_x", "base_halfdepth_z", "tip_scale"}, "head_inputs.ears")
    if ears is not None and ears["tip_scale"] >= 1.0:
        _fail("head_inputs.ears.tip_scale must be less than one")
    return {"stations": parsed, "crown_centre_up": crown_up, "muzzle": muzzle, "ears": ears}


def _neck_port(source: Mapping[str, Any], vertices: list[tuple[float, float, float]],
               loops: Mapping[str, list[int]]) -> tuple[list[int], list[tuple[float, float]]]:
    loop = loops.get(_PORT)
    if loop is None or len(loop) != 6:
        _fail("base_mesh port.neck must contain six vertices")
    centre = source["centre"]
    phase = []
    for index in loop:
        point = vertices[index]
        if abs(point[1] - centre[1]) > _TOL:
            _fail("actual neck port is not in its source plane")
        x = (point[0] - centre[0]) / source["rL"]
        radius = source["rA"] if point[2] >= centre[2] else source["rP"]
        z = (point[2] - centre[2]) / radius
        pair = tuple(0.0 if abs(v) <= _TOL else (1.0 if v > 0.0 else -1.0) for v in (x, z))
        if abs(x - pair[0]) > _TOL or abs(z - pair[1]) > _TOL:
            _fail("actual neck port does not match source neck radii")
        phase.append(pair)  # type: ignore[arg-type]
    if set(phase) != _PHASE_SET:
        _fail("actual neck port does not have the required six-point rectangular phase")
    return list(loop), phase


def _loop_winding(quads: list[tuple[int, int, int, int]], loop: list[int], where: str) -> int:
    uses = _edge_uses(quads)
    signs = []
    for i, left in enumerate(loop):
        right = loop[(i + 1) % len(loop)]
        rows = uses.get(_edge(left, right), ())
        if len(rows) != 1:
            _fail(f"{where} is not a boundary")
        signs.append(1 if rows[0][1:] == (left, right) else -1)
    if len(set(signs)) != 1:
        _fail(f"{where} winding is inconsistent")
    return signs[0]


def _band(source: list[int], target: list[int], orientation: int) -> list[tuple[int, int, int, int]]:
    if len(source) != len(target):
        _fail("band rings must have equal sizes")
    result = []
    for i in range(len(source)):
        j = (i + 1) % len(source)
        result.append((source[j], source[i], target[i], target[j]) if orientation == 1
                      else (source[i], source[j], target[j], target[i]))
    return result


def _six_ring(centre: tuple[float, float, float], radii: tuple[float, float, float],
              phase: list[tuple[float, float]]) -> list[tuple[float, float, float]]:
    lateral, anterior, posterior = radii
    return [(centre[0] + pair[0] * lateral, centre[1],
             centre[2] + pair[1] * (anterior if pair[1] >= 0.0 else posterior))
            for pair in phase]


def _append_ring(points: list[tuple[float, float, float]], vertices: list[list[float]],
                 control_owners: list[str], base_owners: list[str]) -> list[int]:
    result = []
    for point in points:
        result.append(len(vertices))
        vertices.append(list(point))
        control_owners.append(_OWNER)
        base_owners.append(_OWNER)
    return result


def _face_ok(vertices: list[list[float]], face: tuple[int, int, int, int]) -> bool:
    points = [tuple(vertices[index]) for index in face]
    first = _cross(_sub(points[1], points[0]), _sub(points[2], points[0]))
    second = _cross(_sub(points[2], points[0]), _sub(points[3], points[0]))
    return _norm(first) > _AREA_TOL and _norm(second) > _AREA_TOL and _dot(first, second) > 0.0


def _host_loop(quads: list[tuple[int, int, int, int]], skipped: tuple[int, int, int, int],
               where: str) -> tuple[list[int], int]:
    loop = list(skipped)
    return loop, _loop_winding(quads, loop, where)


def _muzzle_support_dimensions(
    points: list[tuple[float, float, float]],
    centre: tuple[float, float, float],
    controls: Mapping[str, float],
) -> tuple[float, float, str]:
    support_fields = {"support_halfwidth", "support_halfheight"} & set(controls)
    if support_fields and support_fields != {"support_halfwidth", "support_halfheight"}:
        _fail("muzzle support_halfwidth and support_halfheight must be supplied together")
    if support_fields:
        return controls["support_halfwidth"], controls["support_halfheight"], "explicit"
    return (
        0.5 * (max(abs(point[0] - centre[0]) for point in points) + controls["tip_halfwidth"]),
        0.5 * (max(abs(point[1] - centre[1]) for point in points) + controls["tip_halfheight"]),
        "legacy-host-tip-average",
    )


def _append_muzzle(host: list[int], orientation: int, controls: Mapping[str, float],
                   vertices: list[list[float]], control_owners: list[str], base_owners: list[str]) -> tuple[list[int], list[tuple[int, int, int, int]], dict[str, Any]]:
    points = [tuple(vertices[index]) for index in host]
    centre = tuple(sum(point[axis] for point in points) / 4.0 for axis in range(3))
    phase = [(1.0 if point[0] > centre[0] else -1.0,
              1.0 if point[1] > centre[1] else -1.0) for point in points]
    support_width, support_height, support_source = _muzzle_support_dimensions(
        points, centre, controls
    )
    rings = []
    for fraction, width, height in ((0.45, support_width, support_height),
                                    (1.0, controls["tip_halfwidth"], controls["tip_halfheight"])):
        ring_points = [(centre[0] + pair[0] * width,
                        centre[1] + controls["tip_up_offset"] * fraction + pair[1] * height,
                        centre[2] + controls["length"] * fraction) for pair in phase]
        rings.append(_append_ring(ring_points, vertices, control_owners, base_owners))
    faces = _band(host, rings[0], orientation) + _band(rings[0], rings[1], orientation)
    cap = tuple(reversed(rings[1])) if orientation == 1 else tuple(rings[1])
    faces.append(cap)  # type: ignore[arg-type]
    return [index for ring in rings for index in ring], faces, {
        "host_indices": host, "support_indices": rings[0], "tip_indices": rings[1],
        "host_phase_xy": [list(pair) for pair in phase], "support_source": support_source,
        "controls": dict(controls)}


def _append_ear(side: str, host: list[int], orientation: int, controls: Mapping[str, float],
                vertices: list[list[float]], control_owners: list[str], base_owners: list[str]) -> tuple[list[int], list[tuple[int, int, int, int]], dict[str, Any]]:
    sign = -1.0 if side == "left" else 1.0
    points = [tuple(vertices[index]) for index in host]
    centre = tuple(sum(point[axis] for point in points) / 4.0 for axis in range(3))
    axis_vector = (sign * controls["lateral_outset"], controls["tip_up"], 0.0)
    axis = _normalise(axis_vector, f"{side} ear axis")
    broad = _normalise(_sub((1.0, 0.0, 0.0), _scale(axis, axis[0])), f"{side} ear broad axis")
    depth = _normalise(_cross(axis, broad), f"{side} ear depth axis")
    vertical = [point[1] - centre[1] for point in points]
    projected_depth = [_dot(_sub(point, centre), depth) for point in points]
    if min(max(abs(v) for v in vertical), max(abs(v) for v in projected_depth)) <= _TOL:
        _fail(f"{side} ear host cannot define corner phase")
    phase = [(-sign * (1.0 if vertical[i] > 0.0 else -1.0),
              1.0 if projected_depth[i] > 0.0 else -1.0) for i in range(4)]
    if len(set(phase)) != 4:
        _fail(f"{side} ear host phase is ambiguous")
    attachment_points = [_add(point, _scale(axis_vector, _EAR_ATTACHMENT_FRACTION))
                         for point in points]
    attachment = _append_ring(attachment_points, vertices, control_owners, base_owners)
    rings = []
    for fraction, scale, blend in ((0.35, 1.0, 0.45),
                                   (0.68, 0.65, 0.85),
                                   (1.0, controls["tip_scale"], 1.0)):
        ring_points = []
        for point, pair in zip(points, phase):
            h = _sub(point, centre)
            h_parallel = _scale(axis, _dot(h, axis))
            h_perp = _sub(h, h_parallel)
            ideal_transverse_offset = _add(
                _scale(broad, pair[0] * controls["base_halfwidth_x"] * scale),
                _scale(depth, pair[1] * controls["base_halfdepth_z"] * scale),
            )
            axial = _add(
                centre,
                _add(
                    _scale(axis_vector, fraction),
                    _scale(
                        h_parallel,
                        (1.0 - fraction) / (1.0 - _EAR_ATTACHMENT_FRACTION),
                    ),
                ),
            )
            transverse = _add(
                _scale(h_perp, 1.0 - blend),
                _scale(ideal_transverse_offset, blend),
            )
            ring_points.append(_add(axial, transverse))
        rings.append(_append_ring(ring_points, vertices, control_owners, base_owners))
    faces = (_band(host, attachment, orientation) + _band(attachment, rings[0], orientation)
             + _band(rings[0], rings[1], orientation)
             + _band(rings[1], rings[2], orientation))
    cap = tuple(reversed(rings[2])) if orientation == 1 else tuple(rings[2])
    faces.append(cap)  # type: ignore[arg-type]
    return attachment + [index for ring in rings for index in ring], faces, {
        "host_indices": host, "attachment_indices": attachment,
        "section_indices": rings, "host_phase": [list(pair) for pair in phase],
        "frame": {"axis": list(axis), "broad": list(broad), "depth": list(depth)},
        "transition_rule": copy.deepcopy(_EAR_TRANSITION_RULE),
        "controls": dict(controls)}


def build(base_mesh: Mapping[str, Any], source_case: Mapping[str, Any],
          head_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Attach one source-owned six-phase coarse head; introduce no binding."""
    base = _mapping(base_mesh, "base_mesh")
    required = {"vertices", "quads", "face_owners", "control_owners", "loops",
                "base_stencils", "frames", "metadata"}
    if not required.issubset(base) or base.get("level") != 0:
        _fail("base_mesh must be a connected L0 mesh")
    base_vertices = [_vector(point, f"base_mesh.vertices[{i}]") for i, point in enumerate(base["vertices"])]
    base_quads = _quads(base["quads"], len(base_vertices), "base_mesh.quads")
    loops = _loops(base["loops"], len(base_vertices))
    if len(base["face_owners"]) != len(base_quads) or len(base["control_owners"]) != len(base_vertices):
        _fail("base_mesh owner arrays do not match its geometry")
    _topology(base_vertices, base_quads, loops, "base_mesh")
    stencils = _stencils(base["base_stencils"], len(base_vertices))
    source, controls = _source(source_case), _inputs(head_inputs)
    neck_loop, phase = _neck_port(source, base_vertices, loops)
    orientation = _loop_winding(base_quads, neck_loop, "neck port")
    base_vertex_count, base_face_count = len(base_vertices), len(base_quads)
    vertices = [list(point) for point in base_vertices]
    quads = [list(face) for face in base_quads]
    face_owners = list(base["face_owners"])
    control_owners = list(base["control_owners"])
    output_loops = {name: list(loop) for name, loop in loops.items() if name != _PORT}
    metadata = copy.deepcopy(dict(_mapping(base["metadata"], "base_mesh.metadata")))
    base_owners = list(metadata.get("base_control_owners", base["control_owners"]))
    if len(base_owners) != base_vertex_count:
        _fail("base_mesh.metadata.base_control_owners does not match vertices")

    rings = {}
    centres = {}
    for name in _STATIONS:
        row = controls["stations"][name]
        centre = _add(source["centre"], (0.0, row["up"], 0.0))
        centres[name] = centre
        rings[name] = _append_ring(_six_ring(centre, row["radii"], phase),
                                   vertices, control_owners, base_owners)

    muzzle_enabled = controls["muzzle"] is not None
    ears_enabled = controls["ears"] is not None
    skipped: dict[str, tuple[int, int, int, int]] = {}
    sequence = [("neck", neck_loop)] + [(name, rings[name]) for name in _STATIONS]
    core_face_indices = []
    for (source_name, source_ring), (target_name, target_ring) in zip(sequence, sequence[1:]):
        faces = _band(source_ring, target_ring, orientation)
        for edge_index, face in enumerate(faces):
            feature_name = None
            if source_name == "jaw" and target_name == "cheek" and edge_index == phase.index((1.0, 1.0)):
                feature_name = "muzzle"
            if source_name == "brow" and target_name == "crown":
                if edge_index == phase.index((-1.0, 0.0)):
                    feature_name = "left_ear"
                elif edge_index == phase.index((1.0, -1.0)):
                    feature_name = "right_ear"
            enabled = muzzle_enabled if feature_name == "muzzle" else ears_enabled if feature_name in ("left_ear", "right_ear") else False
            if feature_name is not None and enabled:
                skipped[feature_name] = face
                continue
            core_face_indices.append(len(quads))
            quads.append(list(face))
            face_owners.append(_OWNER)

    crown_centre = _add(source["centre"], (0.0, controls["crown_centre_up"], 0.0))
    crown_centre_index = len(vertices)
    vertices.append(list(crown_centre))
    control_owners.append(_OWNER)
    base_owners.append(_OWNER)
    crown = rings["crown"]
    crown_faces = [(crown[0], crown[1], crown[2], crown_centre_index),
                   (crown[2], crown[3], crown[4], crown_centre_index),
                   (crown[4], crown[5], crown[0], crown_centre_index)]
    if orientation == 1:
        crown_faces = [tuple(reversed(face)) for face in crown_faces]
    for face in crown_faces:
        core_face_indices.append(len(quads))
        quads.append(list(face))
        face_owners.append(_OWNER)

    features: dict[str, Any] = {"muzzle": {"enabled": False},
                                "ears": {"enabled": False}}
    feature_vertices, feature_faces = [], []
    if muzzle_enabled:
        host, host_orientation = _host_loop(_quads(quads, len(vertices), "head core"), skipped["muzzle"], "muzzle host")
        added_vertices, added_faces, detail = _append_muzzle(host, host_orientation, controls["muzzle"], vertices, control_owners, base_owners)
        features["muzzle"] = {"enabled": True, **detail}
        feature_vertices.extend(added_vertices)
        for face in added_faces:
            feature_faces.append(len(quads)); quads.append(list(face)); face_owners.append(_OWNER)
    if ears_enabled:
        ear_details = {}
        for side in ("left", "right"):
            key = f"{side}_ear"
            host, host_orientation = _host_loop(_quads(quads, len(vertices), "head with feature openings"), skipped[key], key)
            added_vertices, added_faces, detail = _append_ear(side, host, host_orientation, controls["ears"], vertices, control_owners, base_owners)
            ear_details[side] = detail
            feature_vertices.extend(added_vertices)
            for face in added_faces:
                feature_faces.append(len(quads)); quads.append(list(face)); face_owners.append(_OWNER)
        features["ears"] = {"enabled": True, "sides": ear_details}

    new_face_indices = list(range(base_face_count, len(quads)))
    if any(not _face_ok(vertices, tuple(quads[index])) for index in new_face_indices):
        _fail("head contains a degenerate or folded quad")
    new_vertex_indices = list(range(base_vertex_count, len(vertices)))
    metadata["head"] = {
        "owner": _OWNER, "neck_source": "stations.neck_upper", "neck_port_indices": neck_loop,
        "neck_phase": [list(pair) for pair in phase], "winding": orientation,
        "stations": [{"name": name, "centre": list(centres[name]), "indices": rings[name],
                      "radii_lateral_anterior_posterior": list(controls["stations"][name]["radii"])}
                     for name in _STATIONS],
        "crown_centre": {"point": list(crown_centre), "index": crown_centre_index},
        "ear_transition_rule": (copy.deepcopy(_EAR_TRANSITION_RULE)
                                 if ears_enabled else None),
        "features": features, "new_vertex_indices": new_vertex_indices,
        "new_face_indices": new_face_indices, "feature_vertex_indices": feature_vertices,
        "feature_face_indices": feature_faces,
        "binding_handoff": {
            "joint": "neck_head",
            "pivot_source": "stations.neck_collar.C",
            "pivot": list(source["pivot"]),
            "consumed_neck_port_indices": list(neck_loop),
            "neck_support_ring_indices": list(rings["neck_support"]),
            "head_new_vertex_indices": list(new_vertex_indices),
            "feature_new_vertex_indices": list(feature_vertices),
        },
        "binding": "not implemented",
    }
    metadata["base_control_owners"] = base_owners
    metadata["base_vertex_count"] = len(vertices)
    metadata["level"] = 0
    output = {"schema": "creature-kernel.connected-leg-assembly-head-mesh.v1", "level": 0,
              "vertices": vertices, "quads": quads, "face_owners": face_owners,
              "control_owners": control_owners, "loops": output_loops,
              "base_stencils": stencils + [[[index, 1.0]] for index in new_vertex_indices],
              "frames": copy.deepcopy(base["frames"]), "metadata": metadata}
    _topology([tuple(point) for point in vertices], _quads(quads, len(vertices), "output.quads"), output_loops, "output")
    if vertices[:base_vertex_count] != [list(point) for point in base_vertices] or quads[:base_face_count] != [list(face) for face in base_quads]:
        _fail("output changed inherited geometry prefix")
    return output


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Delegate to the current generic connected-leg Catmull--Clark evaluator."""
    if type(levels) is not int or levels < 0 or levels > 2:
        _fail("levels must be an integer from zero through two")
    metadata = _mapping(mesh.get("metadata"), "mesh.metadata") if isinstance(mesh, Mapping) else {}
    if not isinstance(metadata.get("head"), Mapping):
        _fail("mesh must be a head-construction L0 output")
    try:
        import construction
        return construction.evaluate(mesh, levels=levels)
    except Exception as exc:
        if isinstance(exc, HeadConstructionError):
            raise
        raise HeadConstructionError(f"generic evaluator rejected head output: {exc}") from exc


__all__ = [
    "HeadConstructionError",
    "build",
    "evaluate",
    "head_inputs_for_refinement",
    "load_head_refinement_inputs",
]

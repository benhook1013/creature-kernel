"""Bounded connected coarse-arm construction on named root arm ports."""
from __future__ import annotations

from collections.abc import Mapping
import copy
import math
from typing import Any


_SIDES = ("left", "right")
_PORTS = {side: f"port.{side}_arm" for side in _SIDES}
_OWNERS = {side: f"domain.{side}_arm" for side in _SIDES}
_RADII = ("upper", "elbow", "forearm", "wrist", "palm")
_INPUT_KEYS = frozenset(("E", "W", "radii", "hand_length"))
_OPTIONAL_INPUT_KEYS = frozenset(("hand_terminal_scale",))
_DEFAULT_HAND_TERMINAL_SCALE = 0.55
_TOL = 1.0e-8
_FRAME_TOL = 1.0e-7
_AREA_TOL = 1.0e-12


class ArmConstructionError(ValueError):
    """Raised when the bounded arm candidate cannot be admitted."""


def _fail(message: str) -> None:
    raise ArmConstructionError(message)


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
    return tuple(factor * item for item in v)  # type: ignore[return-value]


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


def _lerp(a: tuple[float, float, float], b: tuple[float, float, float], fraction: float) -> tuple[float, float, float]:
    return _add(_scale(a, 1.0 - fraction), _scale(b, fraction))


def _frame(tangent: Any) -> dict[str, tuple[float, float, float]]:
    """Return the settled +Y-projected right-handed frame."""
    t = _normalise(_vector(tangent, "tangent"), "tangent")
    up = (0.0, 1.0, 0.0)
    u = _sub(up, _scale(t, _dot(up, t)))
    u = _normalise(u, "+Y projection")
    f = _normalise(_cross(t, u), "frame forward")
    if _dot(f, (0.0, 0.0, 1.0)) < 0.0:
        u, f = _scale(u, -1.0), _scale(f, -1.0)
    if abs(_dot(t, u)) > _FRAME_TOL or abs(_dot(t, f)) > _FRAME_TOL or abs(_dot(u, f)) > _FRAME_TOL:
        _fail("derived arm frame is not orthogonal")
    if _dot(_cross(t, u), f) < 1.0 - _FRAME_TOL:
        _fail("derived arm frame is not right-handed")
    return {"tangent": t, "U": u, "F": f}


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _edge_uses(quads: list[tuple[int, int, int, int]]) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    uses: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for face_index, face in enumerate(quads):
        for corner, left in enumerate(face):
            right = face[(corner + 1) % 4]
            uses.setdefault(_edge_key(left, right), []).append((face_index, left, right))
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


def _loops(raw: Any, count: int, where: str) -> dict[str, list[int]]:
    value = _mapping(raw, where)
    result: dict[str, list[int]] = {}
    for name, loop in value.items():
        if type(name) is not str or type(loop) not in (list, tuple) or len(loop) < 3:
            _fail(f"{where} contains an invalid named loop")
        checked = list(loop)
        if len(set(checked)) != len(checked) or any(type(v) is not int or v < 0 or v >= count for v in checked):
            _fail(f"{where}.{name} contains invalid indices")
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
            edge = _edge_key(left, loop[(i + 1) % len(loop)])
            if len(uses.get(edge, ())) != 1 or edge in declared:
                _fail(f"{where} loop {name!r} is not a unique boundary")
            declared.add(edge)
    boundary = {edge for edge, rows in uses.items() if len(rows) == 1}
    if boundary != declared:
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


def _stencils(raw: Any, vertex_count: int) -> list[list[list[float | int]]]:
    if type(raw) not in (list, tuple) or len(raw) != vertex_count:
        _fail("base_mesh.base_stencils must cover every base vertex")
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


def _source_rows(source_case: Any) -> dict[str, dict[str, Any]]:
    case = _mapping(source_case, "source_case")
    components = _mapping(case.get("components"), "source_case.components")
    result: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        prefix = f"shoulders.{side}."
        def point(name: str) -> tuple[float, float, float]:
            return tuple(_finite(components.get(f"{prefix}{name}.{axis}"),
                                 f"source_case.components.{prefix}{name}.{axis}")
                         for axis in "xyz")  # type: ignore[return-value]
        result[side] = {
            "J": point("arm_origin"),
            "start_lateral": _positive(components.get(f"{prefix}start_lateral"), f"{prefix}start_lateral"),
            "start_up": _positive(components.get(f"{prefix}start_up"), f"{prefix}start_up"),
            "start_forward": _positive(components.get(f"{prefix}start_forward"), f"{prefix}start_forward"),
        }
    return result


def _input_rows(arm_inputs: Any) -> dict[str, dict[str, Any]]:
    value = _mapping(arm_inputs, "arm_inputs")
    if set(value) != set(_SIDES):
        _fail("arm_inputs must contain exactly left and right")
    result = {}
    for side in _SIDES:
        row = _mapping(value[side], f"arm_inputs.{side}")
        if not _INPUT_KEYS.issubset(row) or set(row) - (_INPUT_KEYS | _OPTIONAL_INPUT_KEYS):
            _fail(f"arm_inputs.{side} has unsupported or missing fields")
        radii = _mapping(row["radii"], f"arm_inputs.{side}.radii")
        if set(radii) != set(_RADII):
            _fail(f"arm_inputs.{side}.radii has unsupported or missing fields")
        parsed_radii = {}
        for name in _RADII:
            pair = radii[name]
            if type(pair) not in (list, tuple) or len(pair) != 2:
                _fail(f"arm_inputs.{side}.radii.{name} must be [up, forward]")
            parsed_radii[name] = (_positive(pair[0], f"{side}.{name}.up"),
                                  _positive(pair[1], f"{side}.{name}.forward"))
        result[side] = {"E": _vector(row["E"], f"arm_inputs.{side}.E"),
                        "W": _vector(row["W"], f"arm_inputs.{side}.W"),
                        "radii": parsed_radii,
                        "hand_length": _positive(row["hand_length"], f"arm_inputs.{side}.hand_length"),
                        "hand_terminal_scale": _positive(
                            row.get("hand_terminal_scale", _DEFAULT_HAND_TERMINAL_SCALE),
                            f"arm_inputs.{side}.hand_terminal_scale")}
    return result


def _port(base: Mapping[str, Any], side: str, source: Mapping[str, Any],
          vertices: list[tuple[float, float, float]], loops: Mapping[str, list[int]]) -> tuple[
              list[int], tuple[float, float, float], list[tuple[float, float]]]:
    name = _PORTS[side]
    loop = loops.get(name)
    if loop is None or len(loop) != 8:
        _fail(f"base_mesh.loops.{name} must be an eight-vertex arm loop")
    points = [vertices[index] for index in loop]
    P = tuple(sum(point[axis] for point in points) / 8.0 for axis in range(3))
    J = source["J"]
    sign = -1.0 if side == "left" else 1.0
    expected_P = (J[0] + sign * source["start_lateral"], J[1], J[2])
    if any(abs(P[axis] - expected_P[axis]) > _TOL for axis in range(3)):
        _fail(f"source_case shoulders.{side} does not own the actual root arm port")
    half_up, forward = 0.5 * source["start_up"], source["start_forward"]
    expected_phase = {(-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
                      (1.0, 0.0), (1.0, 1.0), (0.0, 1.0),
                      (-1.0, 1.0), (-1.0, 0.0)}
    phase = []
    for point in points:
        if abs(point[0] - P[0]) > _TOL:
            _fail(f"{name} is not in its source-owned lateral plane")
        pair = ((point[1] - P[1]) / half_up, (point[2] - P[2]) / forward)
        snapped = tuple(0.0 if abs(value) <= _TOL else (1.0 if value > 0.0 else -1.0)
                        for value in pair)
        if any(abs(pair[i] - snapped[i]) > _TOL for i in range(2)):
            _fail(f"{name} does not match source start_up/start_forward")
        phase.append(snapped)  # type: ignore[arg-type]
    if set(phase) != expected_phase:
        _fail(f"{name} does not contain the expected source-owned eight-point phase")
    return list(loop), P, phase


def _loop_winding(quads: list[tuple[int, int, int, int]], loop: list[int], side: str) -> int:
    uses = _edge_uses(quads)
    signs = []
    for i, left in enumerate(loop):
        right = loop[(i + 1) % 8]
        rows = uses.get(_edge_key(left, right), ())
        if len(rows) != 1:
            _fail(f"{side} arm loop edge is not a unique boundary")
        signs.append(1 if rows[0][1:] == (left, right) else -1)
    if len(set(signs)) != 1:
        _fail(f"{side} arm loop winding is inconsistent")
    return signs[0]


def _ring(center: tuple[float, float, float], frame: Mapping[str, tuple[float, float, float]],
          radii: tuple[float, float], phase: list[tuple[float, float]]) -> list[tuple[float, float, float]]:
    return [_add(center, _add(_scale(frame["U"], uv[0] * radii[0]),
                              _scale(frame["F"], uv[1] * radii[1])))
            for uv in phase]


def _frame_phase(global_phase: list[tuple[float, float]], source: Mapping[str, Any],
                 frame: Mapping[str, tuple[float, float, float]]) -> list[tuple[float, float]]:
    """Project the actual global-Y/Z port phase into the initial arm frame."""
    half_up = 0.5 * source["start_up"]
    forward = source["start_forward"]
    offsets = [(0.0, pair[0] * half_up, pair[1] * forward) for pair in global_phase]
    projected = [(_dot(offset, frame["U"]), _dot(offset, frame["F"]))
                 for offset in offsets]
    scales = (max(abs(pair[0]) for pair in projected),
              max(abs(pair[1]) for pair in projected))
    if min(scales) <= _TOL:
        _fail("actual arm port cannot define both section phase axes")
    return [(pair[0] / scales[0], pair[1] / scales[1]) for pair in projected]


def _band(source: list[int], target: list[int], orientation: int) -> list[tuple[int, int, int, int]]:
    result = []
    for i in range(8):
        j = (i + 1) % 8
        result.append((source[j], source[i], target[i], target[j]) if orientation == 1
                      else (source[i], source[j], target[j], target[i]))
    return result


def _cap(ring: list[int], centre: int, orientation: int) -> list[tuple[int, int, int, int]]:
    faces = [(ring[0], ring[1], ring[2], centre),
             (ring[2], ring[3], ring[4], centre),
             (ring[4], ring[5], ring[6], centre),
             (ring[6], ring[7], ring[0], centre)]
    return [tuple(reversed(face)) for face in faces] if orientation == 1 else faces


def _face_ok(vertices: list[list[float]], face: tuple[int, int, int, int]) -> bool:
    p = [tuple(vertices[index]) for index in face]
    first = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
    second = _cross(_sub(p[2], p[0]), _sub(p[3], p[0]))
    return _norm(first) > _AREA_TOL and _norm(second) > _AREA_TOL and _dot(first, second) > 0.0


def build(base_mesh: Mapping[str, Any], source_case: Mapping[str, Any],
          arm_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Attach bilateral source-owned coarse arms; introduce no binding."""
    base = _mapping(base_mesh, "base_mesh")
    required = {"vertices", "quads", "face_owners", "control_owners", "loops",
                "base_stencils", "frames", "metadata"}
    if not required.issubset(base) or base.get("level") != 0:
        _fail("base_mesh must be a connected L0 mesh")
    vertices = [_vector(point, f"base_mesh.vertices[{i}]") for i, point in enumerate(base["vertices"])]
    quads = _quads(base["quads"], len(vertices), "base_mesh.quads")
    loops = _loops(base["loops"], len(vertices), "base_mesh.loops")
    if not set(_PORTS.values()).issubset(loops):
        _fail("base_mesh lacks the two named arm ports")
    if len(base["face_owners"]) != len(quads) or len(base["control_owners"]) != len(vertices):
        _fail("base_mesh owner arrays do not match its geometry")
    _topology(vertices, quads, loops, "base_mesh")
    stencils = _stencils(base["base_stencils"], len(vertices))
    sources, inputs = _source_rows(source_case), _input_rows(arm_inputs)
    base_vertex_count, base_face_count = len(vertices), len(quads)
    output_vertices = [list(point) for point in vertices]
    output_quads = [list(face) for face in quads]
    output_face_owners = list(base["face_owners"])
    output_control_owners = list(base["control_owners"])
    output_loops = {name: list(loop) for name, loop in loops.items()
                    if name not in _PORTS.values()}
    metadata = copy.deepcopy(dict(_mapping(base["metadata"], "base_mesh.metadata")))
    metadata["arms"] = {}
    base_owners = list(metadata.get("base_control_owners", base["control_owners"]))
    if len(base_owners) != base_vertex_count:
        _fail("base_mesh.metadata.base_control_owners does not match its vertices")

    for side in _SIDES:
        source_loop, P, global_phase = _port(base, side, sources[side], vertices, loops)
        J, E, W = sources[side]["J"], inputs[side]["E"], inputs[side]["W"]
        upper_t = _normalise(_sub(E, P), f"{side} P-to-E")
        fore_t = _normalise(_sub(W, E), f"{side} E-to-W")
        if (side == "left" and (E[0] >= P[0] or W[0] >= E[0])) or \
                (side == "right" and (E[0] <= P[0] or W[0] <= E[0])):
            _fail(f"{side} arm must progress outward from P through E to W")
        collar_center = _add(P, _scale(upper_t, 0.6 * _norm(_sub(P, J))))
        hand_t = fore_t
        hand_length = inputs[side]["hand_length"]
        centres = [
            ("upper_belly", _lerp(P, E, 0.35)),
            ("pre_elbow", _lerp(P, E, 0.85)),
            ("elbow", E),
            ("post_elbow", _lerp(E, W, 0.15)),
            ("forearm_belly", _lerp(E, W, 0.45)),
            ("pre_wrist", _lerp(E, W, 0.85)),
            ("wrist", W),
            ("palm", _add(W, _scale(hand_t, 0.30 * hand_length))),
            ("knuckle", _add(W, _scale(hand_t, 0.68 * hand_length))),
            ("terminal", _add(W, _scale(hand_t, 0.92 * hand_length))),
        ]
        radii = inputs[side]["radii"]
        section_radii = [
            radii["upper"],
            tuple((1.0 - 0.70) * radii["upper"][i] + 0.70 * radii["elbow"][i] for i in range(2)),
            radii["elbow"],
            tuple(0.5 * (radii["elbow"][i] + radii["forearm"][i]) for i in range(2)),
            radii["forearm"],
            tuple(0.25 * radii["forearm"][i] + 0.75 * radii["wrist"][i] for i in range(2)),
            radii["wrist"], radii["palm"],
            tuple(1.03 * value for value in radii["palm"]),
            tuple(inputs[side]["hand_terminal_scale"] * value for value in radii["palm"]),
        ]
        upper_frame = _frame(upper_t)
        phase = _frame_phase(global_phase, sources[side], upper_frame)
        elbow_frame = _frame(_add(upper_t, fore_t))
        frames = [upper_frame, upper_frame, elbow_frame,
                  _frame(fore_t), _frame(fore_t), _frame(fore_t),
                  _frame(fore_t), _frame(hand_t), _frame(hand_t), _frame(hand_t)]
        orientation = _loop_winding(quads, source_loop, side)
        new_vertices, new_faces = [], []
        ring_indices: dict[str, list[int]] = {}

        collar = []
        shift = _sub(collar_center, P)
        for source_index in source_loop:
            index = len(output_vertices)
            output_vertices.append(list(_add(vertices[source_index], shift)))
            output_control_owners.append(_OWNERS[side])
            base_owners.append(_OWNERS[side])
            collar.append(index)
            new_vertices.append(index)
        ring_indices["collar"] = collar

        for (name, centre), radius, frame in zip(centres, section_radii, frames):
            indices = []
            for point in _ring(centre, frame, radius, phase):
                index = len(output_vertices)
                output_vertices.append(list(point))
                output_control_owners.append(_OWNERS[side])
                base_owners.append(_OWNERS[side])
                indices.append(index)
                new_vertices.append(index)
            ring_indices[name] = indices

        cap_center = _add(W, _scale(hand_t, hand_length))
        cap_index = len(output_vertices)
        output_vertices.append(list(cap_center))
        output_control_owners.append(_OWNERS[side])
        base_owners.append(_OWNERS[side])
        new_vertices.append(cap_index)

        sequence = [("port", source_loop), ("collar", collar)] + [
            (name, ring_indices[name]) for name, _ in centres]
        face_ranges = {}
        for (source_name, source_ring), (target_name, target_ring) in zip(sequence, sequence[1:]):
            start = len(output_quads)
            faces = _band(source_ring, target_ring, orientation)
            output_quads.extend([list(face) for face in faces])
            output_face_owners.extend([_OWNERS[side]] * len(faces))
            indices = list(range(start, start + len(faces)))
            face_ranges[f"{source_name}_to_{target_name}"] = indices
            new_faces.extend(indices)
        start = len(output_quads)
        faces = _cap(ring_indices["terminal"], cap_index, orientation)
        output_quads.extend([list(face) for face in faces])
        output_face_owners.extend([_OWNERS[side]] * len(faces))
        cap_faces = list(range(start, start + len(faces)))
        face_ranges["terminal_cap"] = cap_faces
        new_faces.extend(cap_faces)
        if any(not _face_ok(output_vertices, tuple(output_quads[index])) for index in new_faces):
            _fail(f"{side} arm contains a degenerate or folded quad")

        metadata["arms"][side] = {
            "owner": _OWNERS[side], "J_source": f"shoulders.{side}.arm_origin",
            "J": list(J), "P": list(P), "E": list(E), "W": list(W),
            "bone_lengths": {"upper_J_E": _norm(_sub(E, J)), "visible_P_E": _norm(_sub(E, P)),
                             "forearm_E_W": _norm(_sub(W, E))},
            "source_port": {"name": _PORTS[side], "indices": source_loop,
                            "start_lateral": sources[side]["start_lateral"],
                            "full_up_span": sources[side]["start_up"],
                            "full_forward_span": 2.0 * sources[side]["start_forward"],
                            "global_yz_phase": [list(pair) for pair in global_phase],
                            "section_frame_phase": [list(pair) for pair in phase]},
            "collar": {"fraction_of_P_J": 0.6, "centre": list(collar_center),
                       "indices": collar, "exact_port_translation": True},
            "sections": [{"name": name, "centre": list(centre), "indices": ring_indices[name],
                          "radii_up_forward": list(radius),
                          "frame": {key: list(value) for key, value in frame.items()}}
                         for (name, centre), radius, frame in zip(centres, section_radii, frames)],
            "cap": {"centre": list(cap_center), "vertex": cap_index, "faces": cap_faces},
            "hand_terminal_scale": {
                "value": inputs[side]["hand_terminal_scale"],
                "unit": "unitless",
                "role": "terminal station palm-radius scale",
                "source_lineage": f"arm_inputs.{side}.hand_terminal_scale",
                "historical_default": _DEFAULT_HAND_TERMINAL_SCALE,
            },
            "new_vertex_indices": new_vertices, "new_face_indices": new_faces,
            "face_owner_ranges": face_ranges, "winding": orientation,
            "binding": "not implemented; deferred nine-column D0/D1/D2 plan is recorded in arm-stage.md",
        }

    metadata["base_control_owners"] = base_owners
    metadata["base_vertex_count"] = len(output_vertices)
    metadata["level"] = 0
    output = {
        "schema": "creature-kernel.connected-leg-assembly-arm-mesh.v1",
        "level": 0, "vertices": output_vertices, "quads": output_quads,
        "face_owners": output_face_owners, "control_owners": output_control_owners,
        "loops": output_loops,
        "base_stencils": stencils + [[[index, 1.0]] for index in range(base_vertex_count, len(output_vertices))],
        "frames": copy.deepcopy(base["frames"]), "metadata": metadata,
    }
    checked_vertices = [_vector(point, "output vertex") for point in output_vertices]
    checked_quads = _quads(output_quads, len(output_vertices), "output.quads")
    _topology(checked_vertices, checked_quads, output_loops, "output")
    if output_vertices[:base_vertex_count] != [list(point) for point in vertices] or \
            output_quads[:base_face_count] != [list(face) for face in quads]:
        _fail("output changed the inherited geometry prefix")
    return output


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Delegate to the current generic connected-leg Catmull--Clark evaluator."""
    if type(levels) is not int or levels < 0 or levels > 2:
        _fail("levels must be an integer from zero through two")
    metadata = _mapping(mesh.get("metadata"), "mesh.metadata") if isinstance(mesh, Mapping) else {}
    if not isinstance(metadata.get("arms"), Mapping):
        _fail("mesh must be an arm-construction L0 output")
    try:
        import construction
        return construction.evaluate(mesh, levels=levels)
    except Exception as exc:
        if isinstance(exc, ArmConstructionError):
            raise
        raise ArmConstructionError(f"generic evaluator rejected arm output: {exc}") from exc


__all__ = ["ArmConstructionError", "build", "evaluate"]

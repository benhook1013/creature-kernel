"""Bounded connected foot construction attached to the expanded leg L0.

The module consumes the current connected-leg L0 output and the two existing
input maps.  It reuses each ordered eight-vertex ankle loop, resolves its
cyclic phase and direction from the actual ankle frame, and closes a small
longitudinal dorsal/plantar grid.  It does not create weights, a rig, pose
transforms, or a body.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any


_SIDES = ("left", "right")
_ANKLE_PORTS = {side: f"port.{side}_ankle" for side in _SIDES}
_FOOT_OWNERS = {side: f"domain.{side}_foot" for side in _SIDES}
_LONGITUDINAL_ROW_NAMES = (
    "heel", "heel_ankle_midpoint", "ankle", "ankle_quarter",
    "ankle_five_eighths", "ball", "ball_toe_midpoint", "toe",
)
_LONGITUDINAL_ROW_FORMULAS = (
    "H.z", "midpoint(H.z,A.z)", "A.z", "A.z+0.25*(B.z-A.z)",
    "A.z+0.625*(B.z-A.z)", "B.z", "midpoint(B.z,T.z)", "T.z",
)
_LONGITUDINAL_ROW_ROLES = (
    "H source heel control",
    "derived H-to-A transition row",
    "A ankle-z attachment context",
    "derived A-to-B transition row",
    "derived A-to-B transition row",
    "B source ball control",
    "derived B-to-T forefoot row",
    "T source toe control",
)
_LATERAL_FRACTIONS = (-1.0, -0.65, 0.0, 0.65, 1.0)
_HOLE_BOUNDARY_POSITIONS = (
    (1, 1), (2, 1), (3, 1), (3, 2),
    (3, 3), (2, 3), (1, 3), (1, 2),
)
_HOLE_BOUNDARY_NAMES = (
    "mid_ha_left", "ankle_left", "ankle_quarter_left",
    "ankle_quarter_centre", "ankle_quarter_right", "ankle_right",
    "mid_ha_right", "mid_ha_centre",
)
_ANCHORS = ("H", "B", "T")
_LEG_KEYS = frozenset((
    "J", "T", "K", "A", "radii", "mid_thigh_factor", "support_fraction",
    "J_role", "TK_source_role", "distal_design_status",
))
_COORDINATE_TOLERANCE = 1.0e-8
_FRAME_TOLERANCE = 1.0e-6
_AREA_TOLERANCE = 1.0e-12
_CORRESPONDENCE_TIE_TOLERANCE = 1.0e-9
_FROZEN_INTERSECTION_CORE = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/"
    "attempt-2-snapshot/source/experiments/owned-root-assembly-successor/"
    "mesh_correctness.py"
)
_FROZEN_INTERSECTION_MODULE = "connected_leg_frozen_intersection_core"


class FootConstructionError(ValueError):
    """Raised when the bounded foot construction cannot be admitted."""


def _fail(message: str) -> None:
    raise FootConstructionError(message)


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


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    if type(value) not in (list, tuple) or len(value) != 3:
        _fail(f"{where} must be a three-component vector")
    return tuple(_finite(item, f"{where}[{index}]")
                 for index, item in enumerate(value))  # type: ignore[return-value]


def _positive(value: Any, where: str) -> float:
    result = _finite(value, where)
    if not result > 0.0:
        _fail(f"{where} must be positive")
    return result


def _close(left: tuple[float, float, float], right: tuple[float, float, float],
           where: str) -> None:
    if any(abs(left[index] - right[index]) > _COORDINATE_TOLERANCE
           for index in range(3)):
        _fail(f"{where} differs from the source metadata")


def _add(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[index] + right[index] for index in range(3))  # type: ignore[return-value]


def _sub(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


def _scale(value: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(factor * item for item in value)  # type: ignore[return-value]


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _norm(value: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalise(value: tuple[float, float, float], where: str) -> tuple[float, float, float]:
    length = _norm(value)
    if not math.isfinite(length) or not length > 0.0:
        _fail(f"{where} must have positive finite length")
    return _scale(value, 1.0 / length)


def _edge_key(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _edge_uses(quads: list[tuple[int, int, int, int]]) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    uses: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for face_index, face in enumerate(quads):
        for corner, left in enumerate(face):
            right = face[(corner + 1) % 4]
            uses.setdefault(_edge_key(left, right), []).append(
                (face_index, left, right))
    return uses


def _checked_quads(raw: Any, vertex_count: int, where: str) -> list[tuple[int, int, int, int]]:
    if type(raw) not in (list, tuple) or not raw:
        _fail(f"{where} must be a non-empty sequence")
    result: list[tuple[int, int, int, int]] = []
    for face_index, raw_face in enumerate(raw):
        if type(raw_face) not in (list, tuple) or len(raw_face) != 4:
            _fail(f"{where}[{face_index}] must contain four indices")
        face = tuple(raw_face)
        if any(type(index) is not int for index in face):
            _fail(f"{where}[{face_index}] indices must be integers")
        if len(set(face)) != 4 or any(index < 0 or index >= vertex_count for index in face):
            _fail(f"{where}[{face_index}] has invalid indices")
        result.append(face)  # type: ignore[arg-type]
    return result


def _checked_loops(raw: Any, vertex_count: int, where: str) -> dict[str, list[int]]:
    value = _mapping(raw, where)
    if not value:
        _fail(f"{where} must not be empty")
    result: dict[str, list[int]] = {}
    for name, raw_loop in value.items():
        if type(name) is not str or type(raw_loop) not in (list, tuple) or len(raw_loop) < 3:
            _fail(f"{where} entries must be named loops of at least three vertices")
        loop = list(raw_loop)
        if any(type(index) is not int or index < 0 or index >= vertex_count for index in loop):
            _fail(f"{where}.{name} has an invalid vertex")
        if len(set(loop)) != len(loop):
            _fail(f"{where}.{name} repeats a vertex")
        result[name] = loop
    return result


def _validate_topology(vertices: list[tuple[float, float, float]],
                       quads: list[tuple[int, int, int, int]],
                       loops: Mapping[str, list[int]],
                       where: str) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    uses = _edge_uses(quads)
    if any(len(rows) not in (1, 2) for rows in uses.values()):
        _fail(f"{where} has a non-manifold edge")
    if any(len(rows) == 2 and rows[0][1:] == rows[1][1:] for rows in uses.values()):
        _fail(f"{where} has an orientation conflict")
    declared: set[tuple[int, int]] = set()
    for name, loop in loops.items():
        for index, left in enumerate(loop):
            edge = _edge_key(left, loop[(index + 1) % len(loop)])
            if edge not in uses or len(uses[edge]) != 1:
                _fail(f"{where} loop {name!r} is not a boundary loop")
            if edge in declared:
                _fail(f"{where} declares a boundary edge more than once")
            declared.add(edge)
    boundary = {edge for edge, rows in uses.items() if len(rows) == 1}
    if declared != boundary:
        _fail(f"{where} loops do not cover the boundary exactly")
    adjacency = {index: set() for index in range(len(vertices))}
    for left, right in uses:
        adjacency[left].add(right)
        adjacency[right].add(left)
    if any(not neighbours for neighbours in adjacency.values()):
        _fail(f"{where} contains an unused vertex")
    seen = {0}
    pending = [0]
    while pending:
        vertex = pending.pop()
        for neighbour in adjacency[vertex]:
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    if len(seen) != len(vertices):
        _fail(f"{where} is disconnected")
    return uses


def _validate_frame(raw: Any, where: str) -> dict[str, tuple[float, float, float]]:
    frame = _mapping(raw, where)
    result = {key: _vector(frame.get(key), f"{where}.{key}")
              for key in ("tangent", "X", "U", "F")}
    for key, value in result.items():
        if abs(_norm(value) - 1.0) > _FRAME_TOLERANCE:
            _fail(f"{where}.{key} is not unit length")
    if abs(_dot(result["X"], result["U"])) > _FRAME_TOLERANCE:
        _fail(f"{where}.X and U are not orthogonal")
    if abs(_dot(result["X"], result["F"])) > _FRAME_TOLERANCE:
        _fail(f"{where}.X and F are not orthogonal")
    if abs(_dot(result["U"], result["F"])) > _FRAME_TOLERANCE:
        _fail(f"{where}.U and F are not orthogonal")
    if _dot(_cross(result["X"], result["U"]), result["F"]) < 1.0 - _FRAME_TOLERANCE:
        _fail(f"{where} does not use the source X/U/F orientation")
    return result


def _validate_identity_stencils(raw: Any, count: int, where: str) -> None:
    if type(raw) not in (list, tuple) or len(raw) != count:
        _fail(f"{where} must contain one stencil per L0 vertex")
    for index, stencil in enumerate(raw):
        if type(stencil) not in (list, tuple) or len(stencil) != 1:
            _fail(f"{where}[{index}] must be an identity stencil")
        term = stencil[0]
        if type(term) not in (list, tuple) or len(term) != 2:
            _fail(f"{where}[{index}] is malformed")
        if term[0] != index or float(term[1]) != 1.0:
            _fail(f"{where}[{index}] must be [[{index}, 1.0]]")


def _validate_leg_inputs(leg_inputs: Any) -> dict[str, dict[str, Any]]:
    value = _mapping(leg_inputs, "leg_inputs")
    if set(value) != set(_SIDES):
        _fail("leg_inputs must contain exactly left and right")
    result: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        row = _mapping(value[side], f"leg_inputs.{side}")
        if set(row) != _LEG_KEYS:
            _fail(f"leg_inputs.{side} does not match the current connected-leg input schema")
        checked = dict(row)
        checked["A"] = _vector(row["A"], f"leg_inputs.{side}.A")
        for key in ("J", "T", "K"):
            _vector(row[key], f"leg_inputs.{side}.{key}")
        for key in ("J_role", "TK_source_role", "distal_design_status"):
            if type(row[key]) is not str or not row[key]:
                _fail(f"leg_inputs.{side}.{key} must be non-empty text")
        result[side] = checked
    return result


def _parse_anchor(raw: Any, where: str) -> dict[str, float]:
    row = _mapping(raw, where)
    if set(row) != {"z", "plantar_y", "halfwidth", "dorsalthickness"}:
        _fail(f"{where} has unsupported or missing fields")
    return {
        "z": _finite(row["z"], f"{where}.z"),
        "plantar_y": _finite(row["plantar_y"], f"{where}.plantar_y"),
        "halfwidth": _positive(row["halfwidth"], f"{where}.halfwidth"),
        "dorsalthickness": _positive(row["dorsalthickness"], f"{where}.dorsalthickness"),
    }


def _parse_foot_inputs(foot_inputs: Any) -> dict[str, dict[str, Any]]:
    value = _mapping(foot_inputs, "foot_inputs")
    if set(value) != set(_SIDES):
        _fail("foot_inputs must contain exactly left and right")
    result: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        row = _mapping(value[side], f"foot_inputs.{side}")
        if set(row) != {"H", "B", "T", "collar_fraction"}:
            _fail(f"foot_inputs.{side} has unsupported or missing fields")
        anchors = {name: _parse_anchor(row[name], f"foot_inputs.{side}.{name}")
                   for name in _ANCHORS}
        alpha = _finite(row["collar_fraction"], f"foot_inputs.{side}.collar_fraction")
        if not 0.0 < alpha < 1.0:
            _fail(f"foot_inputs.{side}.collar_fraction must be strictly between zero and one")
        result[side] = {**anchors, "collar_fraction": alpha}
    return result


def _ankle_chain(base_mesh: Mapping[str, Any], side: str,
                 leg_row: Mapping[str, Any], vertices: list[tuple[float, float, float]],
                 loops: Mapping[str, list[int]]) -> tuple[list[int], tuple[float, float, float], dict[str, tuple[float, float, float]]]:
    metadata = _mapping(base_mesh["metadata"], "base_mesh.metadata")
    chains = _mapping(metadata.get("chains"), "base_mesh.metadata.chains")
    chain = _mapping(chains.get(side), f"base_mesh.metadata.chains.{side}")
    port = _ANKLE_PORTS[side]
    loop = loops.get(port)
    if loop is None or len(loop) != 8:
        _fail(f"base_mesh.loops.{port} must be an eight-vertex ankle loop")
    if list(chain.get("ankle_port", ())) != loop:
        _fail(f"base_mesh metadata ankle port disagrees with {port}")
    sections = chain.get("sections")
    if type(sections) not in (list, tuple):
        _fail(f"base_mesh.metadata.chains.{side}.sections must be a sequence")
    ankle_rows = [row for row in sections
                  if isinstance(row, Mapping) and row.get("name") == "ankle"]
    if len(ankle_rows) != 1 or list(ankle_rows[0].get("indices", ())) != loop:
        _fail(f"base_mesh metadata ankle section disagrees with {port}")
    ankle = ankle_rows[0]
    centre = _vector(ankle.get("centre"), f"base_mesh.metadata.chains.{side}.ankle.centre")
    A = _vector(leg_row["A"], f"leg_inputs.{side}.A")
    _close(centre, A, f"leg_inputs.{side}.A")
    frame = _validate_frame(ankle.get("frame"), f"base_mesh.metadata.chains.{side}.ankle.frame")
    for index in loop:
        if abs(_dot(_sub(vertices[index], centre), frame["tangent"])) > _COORDINATE_TOLERANCE:
            _fail(f"{port} is not in its declared source frame plane")
    return loop, centre, frame


def _validate_base_mesh(base_mesh: Any, leg_inputs: Mapping[str, Any]) -> tuple[
        list[tuple[float, float, float]], list[tuple[int, int, int, int]], dict[str, list[int]], int, int]:
    value = _mapping(base_mesh, "base_mesh")
    required = {"vertices", "quads", "face_owners", "control_owners", "loops",
                "base_stencils", "frames", "metadata"}
    if not required.issubset(value):
        _fail("base_mesh is missing a required connected-leg field")
    if value.get("level") != 0:
        _fail("base_mesh must be the expanded connected-leg L0")
    raw_vertices = value["vertices"]
    if type(raw_vertices) not in (list, tuple) or not raw_vertices:
        _fail("base_mesh.vertices must be a non-empty sequence")
    vertices = [_vector(point, f"base_mesh.vertices[{index}]")
                for index, point in enumerate(raw_vertices)]
    quads = _checked_quads(value["quads"], len(vertices), "base_mesh.quads")
    face_owners = value["face_owners"]
    control_owners = value["control_owners"]
    if type(face_owners) not in (list, tuple) or len(face_owners) != len(quads):
        _fail("base_mesh.face_owners must match base_mesh.quads")
    if type(control_owners) not in (list, tuple) or len(control_owners) != len(vertices):
        _fail("base_mesh.control_owners must match base_mesh.vertices")
    if any(type(owner) is not str or not owner for owner in (*face_owners, *control_owners)):
        _fail("base_mesh owners must be non-empty strings")
    loops = _checked_loops(value["loops"], len(vertices), "base_mesh.loops")
    expected_loops = {
        "port.neck", "port.left_arm", "port.right_arm",
        "port.left_ankle", "port.right_ankle",
    }
    if set(loops) != expected_loops:
        _fail("base_mesh must expose exactly the three retained ports and two ankle ports")
    _validate_topology(vertices, quads, loops, "base_mesh")
    _validate_identity_stencils(value["base_stencils"], len(vertices), "base_mesh.base_stencils")
    metadata = _mapping(value["metadata"], "base_mesh.metadata")
    if metadata.get("admission_status") != "accepted" or metadata.get("admission_failures") != []:
        _fail("base_mesh admission metadata is not accepted")
    base_owners = metadata.get("base_control_owners")
    if type(base_owners) not in (list, tuple) or len(base_owners) != len(vertices):
        _fail("base_mesh metadata base_control_owners must match L0 vertices")
    if any(type(owner) is not str or not owner for owner in base_owners):
        _fail("base_mesh metadata base_control_owners must be non-empty strings")
    if metadata.get("base_vertex_count", len(base_owners)) != len(base_owners):
        _fail("base_mesh metadata base_vertex_count must match base_control_owners")
    frames = _mapping(value["frames"], "base_mesh.frames")
    if set(frames) != set(_SIDES):
        _fail("base_mesh.frames must contain exactly left and right")
    leg_rows = _validate_leg_inputs(leg_inputs)
    for side in _SIDES:
        _ankle_chain(value, side, leg_rows[side], vertices, loops)
    return vertices, quads, loops, len(vertices), len(quads)


def _source_profile(z: float, controls: Mapping[str, Any], field: str,
                    side: str) -> float:
    """Evaluate one piecewise-linear H/B/T source control without clamping."""
    H, B, T = (controls[name] for name in _ANCHORS)
    if not H["z"] <= z <= T["z"]:
        _fail(f"{side} longitudinal row z lies outside the H..T source profile")
    if z <= B["z"]:
        left, right = H, B
    else:
        left, right = B, T
    fraction = (z - left["z"]) / (right["z"] - left["z"])
    if field == "halfwidth":
        if z <= B["z"]:
            fraction *= fraction
        return left["halfwidth"] + fraction * (right["halfwidth"] - left["halfwidth"])
    if field == "plantar_y":
        left_value, right_value = left["plantar_y"], right["plantar_y"]
    elif field == "dorsal_y":
        left_value = left["plantar_y"] + left["dorsalthickness"]
        right_value = right["plantar_y"] + right["dorsalthickness"]
    else:
        _fail(f"unsupported source profile field: {field}")
    return left_value + fraction * (right_value - left_value)


def _longitudinal_row_zs(A: tuple[float, float, float],
                         controls: Mapping[str, Any], side: str) -> list[float]:
    H, B, T = (controls[name] for name in _ANCHORS)
    if not H["z"] < A[2] < B["z"] < T["z"]:
        _fail(f"{side} footprint must place heel behind A and ball/toe ahead of A")
    rows = [
        H["z"],
        0.5 * (H["z"] + A[2]),
        A[2],
        A[2] + 0.25 * (B["z"] - A[2]),
        A[2] + 0.625 * (B["z"] - A[2]),
        B["z"],
        0.5 * (B["z"] + T["z"]),
        T["z"],
    ]
    if any(not left < right for left, right in zip(rows, rows[1:])):
        _fail(f"{side} longitudinal row z values are not strictly ordered")
    return rows


def _longitudinal_grid_points(x: float, A: tuple[float, float, float],
                              controls: Mapping[str, Any], side: str) -> dict[str, Any]:
    row_zs = _longitudinal_row_zs(A, controls, side)
    rows = []
    top: list[list[tuple[float, float, float]]] = []
    bottom: list[list[tuple[float, float, float]]] = []
    for index, z in enumerate(row_zs):
        width = _source_profile(z, controls, "halfwidth", side)
        rows.append({
            "name": _LONGITUDINAL_ROW_NAMES[index],
            "z": z,
            "z_formula": _LONGITUDINAL_ROW_FORMULAS[index],
            "source_role": _LONGITUDINAL_ROW_ROLES[index],
            "halfwidth": width,
        })
        top.append([(x + lateral * width,
                     _source_profile(z, controls, "dorsal_y", side), z)
                    for lateral in _LATERAL_FRACTIONS])
        bottom.append([(x + lateral * width,
                        _source_profile(z, controls, "plantar_y", side), z)
                       for lateral in _LATERAL_FRACTIONS])
    return {"rows": rows, "top": top, "bottom": bottom}


def _validate_footprint(A: tuple[float, float, float],
                        ankle_halfwidth: float,
                        controls: Mapping[str, Any], side: str) -> None:
    H, B, T = (controls[name] for name in _ANCHORS)
    _longitudinal_row_zs(A, controls, side)
    if not B["halfwidth"] > ankle_halfwidth + _COORDINATE_TOLERANCE:
        _fail(f"{side} ball width must exceed the attached ankle width")
    if H["halfwidth"] > B["halfwidth"] or T["halfwidth"] > B["halfwidth"]:
        _fail(f"{side} footprint width must not bulb beyond its ball section")


def _correspondence(base_loop: list[int], vertices: list[tuple[float, float, float]],
                    centre: tuple[float, float, float],
                    frame: Mapping[str, tuple[float, float, float]],
                    target_points: list[tuple[float, float, float]],
                    target_order: tuple[str, ...], side: str) -> dict[str, Any]:
    def projected(point: tuple[float, float, float], origin: tuple[float, float, float]) -> tuple[float, float]:
        delta = _sub(point, origin)
        return (_dot(delta, frame["X"]), _dot(delta, frame["F"]))

    actual = []
    for index in base_loop:
        pair = projected(vertices[index], centre)
        length = math.hypot(pair[0], pair[1])
        if not length > _COORDINATE_TOLERANCE:
            _fail(f"{side} ankle loop has a degenerate projected vertex")
        actual.append((pair[0] / length, pair[1] / length))
    semantic = []
    for point in target_points:
        pair = projected(point, centre)
        length = math.hypot(pair[0], pair[1])
        if not length > _COORDINATE_TOLERANCE:
            _fail(f"{side} foot semantic direction is degenerate in the ankle frame")
        semantic.append((pair[0] / length, pair[1] / length))

    candidates = []
    for direction in (1, -1):
        for phase in range(8):
            indices = [(phase + direction * offset) % 8 for offset in range(8)]
            score = sum(actual[indices[offset]][0] * semantic[offset][0] +
                        actual[indices[offset]][1] * semantic[offset][1]
                        for offset in range(8))
            candidates.append({"phase": phase, "direction": direction,
                               "score": float(score), "indices": indices})
    candidates.sort(key=lambda row: (-row["score"], row["direction"], row["phase"]))
    best = candidates[0]
    if best["score"] <= 0.0:
        _fail(f"{side} ankle-to-foot correspondence has no positive source-frame match")
    if len(candidates) > 1 and best["score"] - candidates[1]["score"] <= _CORRESPONDENCE_TIE_TOLERANCE:
        _fail(f"{side} ankle-to-foot correspondence is phase or orientation ambiguous")
    return {
        "ankle_loop_order": list(base_loop),
        "target_order": list(target_order),
        "target_to_ankle_indices": [base_loop[index] for index in best["indices"]],
        "phase": best["phase"],
        "direction": best["direction"],
        "score": best["score"],
        "runner_up_score": candidates[1]["score"],
        "candidate_scores": [
            {key: row[key] for key in ("phase", "direction", "score")}
            for row in candidates
        ],
        "method": "maximum cyclic phase/direction score from actual ankle-frame projected positions",
    }


def _band(source: list[int], target: list[int], orientation: int) -> list[tuple[int, int, int, int]]:
    if len(source) != 8 or len(target) != 8 or orientation not in (-1, 1):
        _fail("foot bands require eight-vertex rings and a signed orientation")
    result = []
    for index in range(8):
        next_index = (index + 1) % 8
        if orientation == 1:
            result.append((source[next_index], source[index], target[index], target[next_index]))
        else:
            result.append((source[index], source[next_index], target[next_index], target[index]))
    return result


def _top_grid_faces(grid: list[list[int | None]]) -> list[tuple[int, int, int, int]]:
    if len(grid) != len(_LONGITUDINAL_ROW_NAMES) or any(len(row) != 5 for row in grid):
        _fail("top longitudinal grid must contain eight rows of five vertices")
    result = []
    for row in range(len(grid) - 1):
        for column in range(4):
            corners = (grid[row][column], grid[row + 1][column],
                       grid[row + 1][column + 1], grid[row][column + 1])
            if any(index is None for index in corners):
                continue
            result.append(corners)  # type: ignore[arg-type]
    return result


def _bottom_grid_faces(grid: list[list[int]]) -> list[tuple[int, int, int, int]]:
    if len(grid) != len(_LONGITUDINAL_ROW_NAMES) or any(len(row) != 5 for row in grid):
        _fail("bottom longitudinal grid must contain eight rows of five vertices")
    return [
        (grid[row][column], grid[row][column + 1],
         grid[row + 1][column + 1], grid[row + 1][column])
        for row in range(len(grid) - 1)
        for column in range(4)
    ]


def _outer_grid_faces(top: list[list[int | None]],
                      bottom: list[list[int]]) -> list[tuple[int, int, int, int]]:
    if any(top[row][column] is None for row in (0, len(top) - 1)
           for column in range(5)):
        _fail("longitudinal grid end rows cannot contain omitted vertices")
    result: list[tuple[int, int, int, int]] = []
    for row in range(len(top) - 1):
        left_top, left_next = top[row][0], top[row + 1][0]
        right_top, right_next = top[row][4], top[row + 1][4]
        if left_top is None or left_next is None or right_top is None or right_next is None:
            _fail("longitudinal grid outer side contains an omitted vertex")
        result.extend((
            (left_top, bottom[row][0], bottom[row + 1][0], left_next),
            (right_top, right_next, bottom[row + 1][4], bottom[row][4]),
        ))
    for column in range(4):
        result.extend((
            (top[0][column], top[0][column + 1],
             bottom[0][column + 1], bottom[0][column]),
            (top[-1][column], bottom[-1][column],
             bottom[-1][column + 1], top[-1][column + 1]),
        ))
    return result


def _triangle(points: list[tuple[float, float, float]], face: tuple[int, int, int, int],
              diagonal: int) -> tuple[tuple[float, float, float], ...]:
    if diagonal == 0:
        return points[face[0]], points[face[1]], points[face[2]]
    return points[face[0]], points[face[2]], points[face[3]]


def _triangle_area_normal(triangle: tuple[tuple[float, float, float], ...], where: str) -> tuple[float, float, float]:
    normal = _cross(_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[0]))
    length = _norm(normal)
    if not math.isfinite(length) or length <= _AREA_TOLERANCE:
        _fail(f"{where} is degenerate")
    return normal


def _validate_new_faces(vertices: list[tuple[float, float, float]],
                        quads: list[tuple[int, int, int, int]],
                        new_face_indices: list[int], side: str) -> None:
    for face_index in new_face_indices:
        face = quads[face_index]
        first = _triangle(vertices, face, 0)
        second = _triangle(vertices, face, 1)
        n_first = _triangle_area_normal(first, f"{side} foot quad {face_index} first triangle")
        n_second = _triangle_area_normal(second, f"{side} foot quad {face_index} second triangle")
        if _dot(n_first, n_second) <= 0.0:
            _fail(f"{side} foot quad {face_index} has a cuff fold")


def _core_identity(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise FootConstructionError(f"frozen intersection core is unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not info:
        _fail(f"frozen intersection core must be a regular non-symlink file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _load_intersection_core() -> Any:
    before = _core_identity(_FROZEN_INTERSECTION_CORE)
    spec = importlib.util.spec_from_file_location(
        _FROZEN_INTERSECTION_MODULE, _FROZEN_INTERSECTION_CORE
    )
    if spec is None or spec.loader is None:
        _fail(f"unable to load frozen intersection core: {_FROZEN_INTERSECTION_CORE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_FROZEN_INTERSECTION_MODULE] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(_FROZEN_INTERSECTION_MODULE) is module:
            sys.modules.pop(_FROZEN_INTERSECTION_MODULE, None)
        raise
    if Path(str(module.__file__)).resolve() != _FROZEN_INTERSECTION_CORE.resolve():
        _fail("frozen intersection core resolved away from its pinned path")
    after = _core_identity(_FROZEN_INTERSECTION_CORE)
    if before != after:
        _fail("frozen intersection core changed while being loaded")
    function = getattr(module, "intersection_diagnostics", None)
    if not callable(function):
        _fail("frozen intersection core lacks intersection_diagnostics")
    return function


def _validate_intersections(vertices: list[tuple[float, float, float]],
                            quads: list[tuple[int, int, int, int]],
                            base_face_count: int,
                            new_face_indices: list[int], side: str) -> None:
    triangles = tuple(
        triangle
        for face in quads
        for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3]))
    )
    expected_pairs = len(triangles) * (len(triangles) - 1) // 2
    try:
        diagnostic = _load_intersection_core()(vertices, triangles)
    except FootConstructionError:
        raise
    except Exception as exc:
        _fail(f"frozen intersection core rejected the complete foot mesh: {exc}")
    if not isinstance(diagnostic, Mapping):
        _fail("frozen intersection core returned a non-mapping diagnostic")
    evidence = diagnostic.get("pair_policy_evidence")
    processed = evidence.get("processed_pair_count") if isinstance(evidence, Mapping) else None
    if (diagnostic.get("pair_count") != expected_pairs or
            processed != expected_pairs or
            not diagnostic.get("pair_policy_complete")):
        _fail("frozen intersection core did not account for every triangle pair")
    if diagnostic.get("hit_pairs_truncated"):
        _fail("frozen intersection core truncated the triangle hit list")

    new_faces = set(new_face_indices)
    inherited_hits: list[tuple[int, int]] = []
    new_hits: list[tuple[int, int, tuple[int, int]]] = []
    for raw_pair in diagnostic.get("hit_pairs", ()):
        if (not isinstance(raw_pair, (list, tuple)) or len(raw_pair) != 2 or
                any(type(index) is not int or index < 0 or index >= len(triangles)
                    for index in raw_pair)):
            _fail("frozen intersection core returned a malformed triangle hit")
        triangle_pair = tuple(sorted(raw_pair))
        face_pair = tuple(sorted((triangle_pair[0] // 2, triangle_pair[1] // 2)))
        if any(face in new_faces for face in face_pair):
            new_hits.append((triangle_pair[0], triangle_pair[1], face_pair))
        else:
            inherited_hits.append((triangle_pair[0], triangle_pair[1]))
    if new_hits:
        _fail(f"{side} foot self-intersects or intersects the attached leg; "
              f"triangle hit {new_hits[0][:2]} maps to quad faces {new_hits[0][2]}")


def _validate_output(mesh: Mapping[str, Any], base: Mapping[str, Any],
                     base_vertex_count: int, base_face_count: int,
                     new_face_indices_by_side: Mapping[str, list[int]]) -> None:
    vertices = [_vector(point, f"output.vertices[{index}]")
                for index, point in enumerate(mesh["vertices"])]
    quads = _checked_quads(mesh["quads"], len(vertices), "output.quads")
    expected_prefix = [_vector(point, f"base_mesh.vertices[{index}]")
                       for index, point in enumerate(base["vertices"])]
    if vertices[:base_vertex_count] != expected_prefix:
        _fail("output does not preserve the expanded-leg vertex prefix")
    if quads[:base_face_count] != [tuple(face) for face in base["quads"]]:
        _fail("output does not preserve the expanded-leg face prefix")
    loops = _checked_loops(mesh["loops"], len(vertices), "output.loops")
    _validate_topology(vertices, quads, loops, "output")
    if any(name in loops for name in _ANKLE_PORTS.values()):
        _fail("closed foot output must not retain ankle boundary loops")
    for name in ("port.neck", "port.left_arm", "port.right_arm"):
        if loops.get(name) != list(base["loops"][name]):
            _fail(f"output changed retained boundary loop {name}")
    for side, indices in new_face_indices_by_side.items():
        _validate_new_faces(vertices, quads, indices, side)
        _validate_intersections(vertices, quads, base_face_count, indices, side)


def build(base_mesh: Mapping[str, Any], leg_inputs: Mapping[str, Any],
          foot_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Attach one common closed longitudinal foot grid per side to L0."""
    leg_rows = _validate_leg_inputs(leg_inputs)
    foot_rows = _parse_foot_inputs(foot_inputs)
    base_vertices, base_quads, base_loops, base_vertex_count, base_face_count = (
        _validate_base_mesh(base_mesh, leg_rows)
    )
    output_vertices = [list(point) for point in base_vertices]
    output_quads = [list(face) for face in base_quads]
    output_face_owners = list(base_mesh["face_owners"])
    output_control_owners = list(base_mesh["control_owners"])
    base_metadata = _mapping(base_mesh["metadata"], "base_mesh.metadata")
    base_control_owners = list(base_metadata["base_control_owners"])
    output_loops = {name: list(loop) for name, loop in base_loops.items()
                    if name not in _ANKLE_PORTS.values()}
    metadata = copy.deepcopy(dict(base_metadata))
    metadata["level"] = 0
    metadata["base_control_owners"] = base_control_owners
    metadata["base_vertex_count"] = len(base_control_owners)
    metadata["feet"] = {}
    index_mapping = copy.deepcopy(metadata.get("index_mapping", {}))
    new_face_indices_by_side: dict[str, list[int]] = {}

    for side in _SIDES:
        ankle_loop, ankle_centre, ankle_frame = _ankle_chain(
            base_mesh, side, leg_rows[side], base_vertices, base_loops
        )
        A = leg_rows[side]["A"]
        controls = foot_rows[side]
        ankle_halfwidth = max(abs(_dot(_sub(base_vertices[index], ankle_centre), ankle_frame["X"]))
                              for index in ankle_loop)
        _validate_footprint(A, ankle_halfwidth, controls, side)
        grid = _longitudinal_grid_points(A[0], A, controls, side)
        top_points = grid["top"]
        bottom_points = grid["bottom"]

        top_indices: list[list[int | None]] = [[None] * 5 for _ in top_points]
        bottom_indices: list[list[int]] = [[] for _ in bottom_points]
        new_vertices: list[int] = []

        def append_vertex(point: tuple[float, float, float]) -> int:
            index = len(output_vertices)
            output_vertices.append(list(point))
            output_control_owners.append(_FOOT_OWNERS[side])
            base_control_owners.append(_FOOT_OWNERS[side])
            new_vertices.append(index)
            return index

        for row, points in enumerate(top_points):
            for column, point in enumerate(points):
                if row == 2 and column == 2:
                    continue
                top_indices[row][column] = append_vertex(point)
        for row, points in enumerate(bottom_points):
            for point in points:
                bottom_indices[row].append(append_vertex(point))

        hole_points = [top_points[row][column]
                       for row, column in _HOLE_BOUNDARY_POSITIONS]
        hole_indices = [top_indices[row][column]
                        for row, column in _HOLE_BOUNDARY_POSITIONS]
        if any(index is None for index in hole_indices):
            _fail(f"{side} ankle hole contains an omitted or missing vertex")
        hole_indices = [int(index) for index in hole_indices]
        correspondence = _correspondence(
            ankle_loop, base_vertices, ankle_centre, ankle_frame,
            hole_points, _HOLE_BOUNDARY_NAMES, side
        )
        semantic_ankle = correspondence["target_to_ankle_indices"]
        direction = int(correspondence["direction"])
        ankle_winding = _loop_winding(base_quads, ankle_loop, side)
        orientation = ankle_winding * direction
        if orientation != 1:
            _fail(f"{side} ankle-to-hole winding is incompatible with the global dorsal grid")

        collar_points = [
            _lerp_point(base_vertices[semantic_ankle[index]], hole_points[index],
                        controls["collar_fraction"])
            for index in range(8)
        ]
        collar_indices = [append_vertex(point) for point in collar_points]

        foot_faces: list[int] = []
        face_ranges: dict[str, list[int]] = {}

        def add_faces(name: str, faces: list[tuple[int, int, int, int]]) -> None:
            start = len(output_quads)
            output_quads.extend([list(face) for face in faces])
            output_face_owners.extend([_FOOT_OWNERS[side]] * len(faces))
            indices = list(range(start, start + len(faces)))
            face_ranges[name] = indices
            foot_faces.extend(indices)

        add_faces("dorsal_grid", _top_grid_faces(top_indices))
        add_faces("plantar_grid", _bottom_grid_faces(bottom_indices))
        add_faces("outer_perimeter", _outer_grid_faces(top_indices, bottom_indices))
        add_faces("ankle_to_collar", _band(semantic_ankle, collar_indices, orientation))
        add_faces("collar_to_hole", _band(collar_indices, hole_indices, orientation))
        new_face_indices_by_side[side] = foot_faces

        source_anchors = {
            name: [A[0], controls[name]["plantar_y"], controls[name]["z"]]
            for name in _ANCHORS
        }
        metadata["feet"][side] = {
            "owner": _FOOT_OWNERS[side],
            "source_anchors": source_anchors,
            "anchor_fields": copy.deepcopy({name: controls[name] for name in _ANCHORS}),
            "ankle_source_loop": list(ankle_loop),
            "attachment_loop": {
                "ankle": list(ankle_loop),
                "hole": list(hole_indices),
                "collar": list(collar_indices),
            },
            "ring_order": ["dorsal_grid", "plantar_grid", "ankle_hole", "collar"],
            "ring_indices_by_name": {
                "dorsal_grid": [index for row in top_indices for index in row
                                if index is not None],
                "plantar_grid": [index for row in bottom_indices for index in row],
                "ankle_hole": list(hole_indices),
                "collar": list(collar_indices),
            },
            "grid_indices": {
                "dorsal": [list(row) for row in top_indices],
                "plantar": [list(row) for row in bottom_indices],
            },
            "longitudinal_rows": copy.deepcopy(grid["rows"]),
            "lateral_fractions": list(_LATERAL_FRACTIONS),
            "hole_boundary_positions": [list(position)
                                         for position in _HOLE_BOUNDARY_POSITIONS],
            "new_vertex_indices": list(new_vertices),
            "new_face_indices": list(foot_faces),
            "face_owner": _FOOT_OWNERS[side],
            "face_owner_ranges": face_ranges,
            "collar_fraction": controls["collar_fraction"],
            "correspondence": correspondence,
            "winding": {
                "attached_ankle_loop": ankle_winding,
                "target_direction": direction,
                "output_orientation": orientation,
            },
            "frames": {
                "ankle_source": {key: list(value) for key, value in ankle_frame.items()},
                "foot_staging": {
                    "X": [1.0, 0.0, 0.0], "Y": [0.0, 1.0, 0.0],
                    "Z": [0.0, 0.0, 1.0],
                },
            },
            "source_profiles": {
                "height": "separate piecewise-linear H/B/T plantar_y and plantar_y+dorsalthickness",
                "halfwidth": "H-to-B uses source halfwidth with u^2; B-to-T is linear",
            },
            "binding": "no weights introduced; future foot vertices inherit corresponding shank influence",
        }
        index_mapping[f"{side}_foot_new_vertices"] = list(new_vertices)
        index_mapping[f"{side}_foot_new_faces"] = list(foot_faces)

    metadata["base_vertex_count"] = len(base_control_owners)
    metadata["index_mapping"] = index_mapping
    metadata["scheme"] = copy.deepcopy(metadata.get("scheme", {}))
    metadata["scheme"]["foot"] = {
        "candidate": "closed longitudinal dorsal/plantar grid with a small dorsal ankle-entry hole",
        "row_names": list(_LONGITUDINAL_ROW_NAMES),
        "lateral_fractions": list(_LATERAL_FRACTIONS),
        "row_zs": list(_LONGITUDINAL_ROW_FORMULAS),
        "height_profiles": "plantar and dorsal heights independently follow source piecewise-linear H/B/T controls",
        "halfwidth_profile": "H-to-B source halfwidth interpolated with u^2; B-to-T source halfwidth linear",
        "dorsal_hole": "omit only row 1..2, column 1..2 quads and the unused row-2 column-2 vertex",
        "outer_perimeter": "two longitudinal sides plus heel and toe end strips; 22 quads",
        "attachment": "actual ankle-frame phase and edge winding, existing collar_fraction=.20, two eight-quad bands",
        "source_roles": "H heel support, A ankle-z attachment context, B/T independent longitudinal forefoot controls",
        "source_frame": "actual ankle frame projected correspondence; staging footprint is global X/Y/Z",
        "ankle_boundary": "reused as an interior ring and removed from declared boundaries",
        "evaluator": "read-only current connected-leg generic Catmull-Clark evaluator",
    }
    output = {
        "schema": "creature-kernel.connected-leg-assembly-foot-mesh.v1",
        "level": 0,
        "vertices": output_vertices,
        "quads": output_quads,
        "face_owners": output_face_owners,
        "control_owners": output_control_owners,
        "loops": output_loops,
        "base_stencils": list(base_mesh["base_stencils"]) + [
            [[index, 1.0]] for index in range(base_vertex_count, len(output_vertices))
        ],
        "frames": copy.deepcopy(base_mesh["frames"]),
        "metadata": metadata,
    }
    _validate_output(output, base_mesh, base_vertex_count, base_face_count,
                     new_face_indices_by_side)
    return output


def _lerp_point(left: tuple[float, float, float], right: tuple[float, float, float], fraction: float) -> tuple[float, float, float]:
    return tuple(left[index] + fraction * (right[index] - left[index])
                 for index in range(3))  # type: ignore[return-value]


def _loop_winding(quads: list[tuple[int, int, int, int]], loop: list[int], side: str) -> int:
    uses = _edge_uses(quads)
    signs = []
    for index, left in enumerate(loop):
        right = loop[(index + 1) % len(loop)]
        rows = uses.get(_edge_key(left, right), [])
        if len(rows) != 1:
            _fail(f"{side} ankle loop edge is not a unique boundary edge")
        used_left, used_right = rows[0][1:]
        if (used_left, used_right) == (left, right):
            signs.append(1)
        elif (used_left, used_right) == (right, left):
            signs.append(-1)
        else:  # pragma: no cover - guarded by edge key
            _fail(f"{side} ankle loop winding cannot be resolved")
    if len(set(signs)) != 1:
        _fail(f"{side} ankle loop has inconsistent winding")
    return signs[0]


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Delegate evaluation to the current generic connected-leg evaluator."""
    if type(levels) is not int or levels < 0 or levels > 2:
        _fail("levels must be an integer between zero and two")
    metadata = _mapping(mesh.get("metadata"), "mesh.metadata") if isinstance(mesh, Mapping) else {}
    if not isinstance(metadata.get("feet"), Mapping):
        _fail("mesh must be a foot-construction L0 output")
    try:
        import construction
    except ImportError as exc:  # pragma: no cover - exercised only outside experiment source
        _fail(f"current connected-leg evaluator is unavailable: {exc}")
    evaluator = getattr(construction, "evaluate", None)
    if not callable(evaluator):
        _fail("current connected-leg evaluator has no evaluate function")
    try:
        return evaluator(mesh, levels=levels)
    except Exception as exc:
        if isinstance(exc, FootConstructionError):
            raise
        raise FootConstructionError(
            f"current connected-leg generic evaluator rejected the foot output: {exc}"
        ) from exc


__all__ = ["FootConstructionError", "build", "evaluate"]

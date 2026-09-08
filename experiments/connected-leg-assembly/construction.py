"""Experiment-local connected leg staging from a saved calibrated root.

This module deliberately stops at an open ankle port.  It does not construct
feet, caps, a skeleton, a renderer, or a production topology.  ``build``
copies the supplied calibrated L0 vertices, quads, owners, and metadata
without renumbering them, then appends one welded bilateral chain per side.

The root thigh loop is the existing eight-vertex loop named
``port.{side}_thigh`` and is not duplicated.  Its centre is required to be
``T + .45 * (K - T)``.  Seven new rings are appended in this exact order:

* ``.70(T-K)`` is the mid-thigh row and ``(1-support_fraction)(T-K)`` is
  the pre-knee support row (``.90(T-K)`` at the baseline support fraction);
* ``K`` is the knee row;
* ``K+(1.2*support_fraction)(A-K)`` is the post-knee support row
  (``K+.12(A-K)`` at baseline), followed by ``K+.35(A-K)`` and
  ``K+.72(A-K)``; and
* ``A`` is the open ankle row.

The incoming radius is measured from the saved root exit ellipse.  The
``mid_thigh_factor`` scales that ellipse at the .70 support row; radii then
linearly interpolate from that scaled row to the supplied knee radii.  After
the knee, radii interpolate to the supplied calf radii at .35 and taper
linearly to the supplied ankle radii at 1.0.  The lateral, anterior, and
posterior radii are independent, so posterior calf mass is an input rather
than a shape repair.

The incoming tangent is ``normalize(K-T)`` and the outgoing tangent is
``normalize(A-K)``.  The knee tangent is the normalized incoming/outgoing
bisector; ``support_fraction`` moves support rows only and does not alter the
knee frame.  Each ring projects global +X onto its tangent plane, aligns its
sign to the preceding ring, and derives forward as ``X cross U`` with
``U = -tangent``.  This preserves the saved root frame convention, avoids
arbitrary twist, and does not require a plantigrade direction.  A zero
segment, singular +X projection, inconsistent root exit, or incompatible loop
winding is rejected rather than repaired.

The evaluator delegates the old transition module's generic JSON
Catmull--Clark/stencil step.  Its five-port and anatomy-specific gates are
not called.  L0 uses identity base stencils; L1/L2 carry sparse, nonnegative
stencils back to the returned L0 vertices and propagate every declared loop.
For a fully closed mesh, a private adapter retains this module's exact
boundary checks and supplies the verified empty loop mapping to the same
frozen subdivision function; it does not manufacture a loop.
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
_THIGH_PORTS = {side: f"port.{side}_thigh" for side in _SIDES}
_ANKLE_PORTS = {side: f"port.{side}_ankle" for side in _SIDES}
_LEG_OWNERS = {side: f"domain.{side}_leg" for side in _SIDES}
_COORDINATE_TOLERANCE = 1.0e-8
_STENCIL_TOLERANCE = 1.0e-10
_MID_THIGH_FRACTION = 0.70
_CALF_FRACTION = 0.35
_ANKLE_APPROACH_FRACTION = 0.72
_POST_KNEE_SUPPORT_MULTIPLIER = 1.2
_ROLE_METADATA_KEYS = ("J_role", "TK_source_role", "distal_design_status")
_SIDE_GEOMETRIC_KEYS = (
    "J", "T", "K", "A", "radii", "mid_thigh_factor", "support_fraction"
)
_SIDE_INPUT_KEYS = frozenset((*_SIDE_GEOMETRIC_KEYS, *_ROLE_METADATA_KEYS))
_GENERIC_TRANSITION_PATH = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/"
    "attempt-2-snapshot/source/experiments/pelvis-thigh-transition/"
    "construction.py"
)
_CLOSED_GENERIC_TRANSITION_CACHE: Any | None = None
_SECTION_NAMES = (
    "mid_thigh",
    "knee_pre_support",
    "knee",
    "knee_post_support",
    "calf",
    "ankle_approach",
    "ankle",
)


class ConstructionError(ValueError):
    """Raised when the bounded leg construction cannot be admitted."""


def _fail(message: str) -> None:
    raise ConstructionError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be a mapping")
    return value


def _finite(value: Any, where: str) -> float:
    if type(value) is not float or not math.isfinite(value):
        _fail(f"{where} must be a finite binary64 float")
    return value


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    if type(value) not in (list, tuple) or len(value) != 3:
        _fail(f"{where} must be a three-component vector")
    return tuple(_finite(item, f"{where}[{index}]")
                 for index, item in enumerate(value))  # type: ignore[return-value]


def _scalar(value: Any, where: str, *, lower: float | None = None,
            upper: float | None = None) -> float:
    result = _finite(value, where)
    if lower is not None and not result >= lower:
        _fail(f"{where} must be >= {lower}")
    if upper is not None and not result <= upper:
        _fail(f"{where} must be <= {upper}")
    return result


def _add(*values: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(value[axis] for value in values) for axis in range(3))  # type: ignore[return-value]


def _sub(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[axis] - right[axis] for axis in range(3))  # type: ignore[return-value]


def _scale(value: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(factor * item for item in value)  # type: ignore[return-value]


def _dot(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> float:
    return sum(left[axis] * right[axis] for axis in range(3))


def _cross(left: tuple[float, float, float],
           right: tuple[float, float, float]) -> tuple[float, float, float]:
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


def _lerp(left: tuple[float, float, float],
          right: tuple[float, float, float], fraction: float) -> tuple[float, float, float]:
    return _add(_scale(left, 1.0 - fraction), _scale(right, fraction))


def _close(left: tuple[float, float, float],
           right: tuple[float, float, float], where: str) -> None:
    if any(abs(left[axis] - right[axis]) > _COORDINATE_TOLERANCE
           for axis in range(3)):
        _fail(f"{where} differs from the saved root")


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


def _validate_stencils(raw: Any, vertex_count: int, base_count: int) -> list[list[list[float | int]]]:
    if type(raw) not in (list, tuple) or len(raw) != vertex_count:
        _fail("base_stencils must contain one stencil per vertex")
    result: list[list[list[float | int]]] = []
    for vertex_index, raw_stencil in enumerate(raw):
        if type(raw_stencil) not in (list, tuple) or not raw_stencil:
            _fail(f"base_stencils[{vertex_index}] must not be empty")
        terms: list[list[float | int]] = []
        previous = -1
        total = 0.0
        for term_index, raw_term in enumerate(raw_stencil):
            if type(raw_term) not in (list, tuple) or len(raw_term) != 2:
                _fail(f"base_stencils[{vertex_index}][{term_index}] is malformed")
            base_index, coefficient = raw_term
            if type(base_index) is not int or base_index <= previous:
                _fail(f"base_stencils[{vertex_index}] indices must be sorted and unique")
            if base_index < 0 or base_index >= base_count:
                _fail(f"base_stencils[{vertex_index}] references an unknown base vertex")
            coefficient = _finite(coefficient, "base stencil coefficient")
            if coefficient == 0.0 or coefficient < -_STENCIL_TOLERANCE:
                _fail(f"base_stencils[{vertex_index}] has an invalid coefficient")
            terms.append([base_index, coefficient])
            total += coefficient
            previous = base_index
        if abs(total - 1.0) > _STENCIL_TOLERANCE:
            _fail(f"base_stencils[{vertex_index}] must partition unity")
        result.append(terms)
    return result


def _validate_mesh(mesh: Mapping[str, Any]) -> None:
    required = ("vertices", "quads", "face_owners", "control_owners",
                "loops", "base_stencils", "frames", "metadata")
    if any(key not in mesh for key in required):
        _fail("mesh is missing a required connected-leg field")
    raw_vertices = mesh["vertices"]
    if type(raw_vertices) not in (list, tuple) or not raw_vertices:
        _fail("mesh.vertices must be a non-empty sequence")
    vertices = [_vector(point, f"vertices[{index}]")
                for index, point in enumerate(raw_vertices)]
    raw_quads = mesh["quads"]
    if type(raw_quads) not in (list, tuple) or not raw_quads:
        _fail("mesh.quads must be a non-empty sequence")
    quads: list[tuple[int, int, int, int]] = []
    seen_faces: set[tuple[int, int, int, int]] = set()
    for face_index, raw_face in enumerate(raw_quads):
        if type(raw_face) not in (list, tuple) or len(raw_face) != 4:
            _fail(f"quads[{face_index}] must contain four indices")
        face = tuple(raw_face)
        if any(type(index) is not int for index in face):
            _fail(f"quads[{face_index}] indices must be integers")
        if len(set(face)) != 4 or any(index < 0 or index >= len(vertices)
                                      for index in face):
            _fail(f"quads[{face_index}] has invalid indices")
        canonical = min(face[index:] + face[:index]
                        for index in range(4))
        reverse = tuple(reversed(face))
        canonical = min(canonical, *(
            reverse[index:] + reverse[:index] for index in range(4)))
        if canonical in seen_faces:
            _fail("duplicate quad, including reversed/cyclic duplicate")
        seen_faces.add(canonical)
        quads.append(face)  # type: ignore[arg-type]

    face_owners = mesh["face_owners"]
    if type(face_owners) not in (list, tuple) or len(face_owners) != len(quads):
        _fail("face_owners must match the quad count")
    if any(type(owner) is not str or not owner for owner in face_owners):
        _fail("face_owners must contain non-empty strings")
    control_owners = mesh["control_owners"]
    if type(control_owners) not in (list, tuple) or len(control_owners) != len(vertices):
        _fail("control_owners must match the vertex count")
    if any(type(owner) is not str or not owner for owner in control_owners):
        _fail("control_owners must contain non-empty strings")

    metadata = _mapping(mesh["metadata"], "mesh.metadata")
    base_owners = metadata.get("base_control_owners")
    if type(base_owners) not in (list, tuple) or not base_owners:
        _fail("metadata.base_control_owners must be a non-empty L0 owner list")
    base_vertex_count = metadata.get("base_vertex_count", len(base_owners))
    if type(base_vertex_count) is not int or base_vertex_count != len(base_owners):
        _fail("metadata.base_vertex_count must match the L0 owner count")
    if any(type(owner) is not str or not owner for owner in base_owners):
        _fail("metadata.base_control_owners must contain non-empty strings")
    if metadata.get("admission_status") != "accepted":
        _fail("connected-leg meshes must have accepted admission metadata")
    if metadata.get("admission_failures") != []:
        _fail("accepted connected-leg meshes must have no admission failures")
    if type(metadata.get("dominant_owner_label")) is not str:
        _fail("metadata.dominant_owner_label is required")
    _validate_stencils(mesh["base_stencils"], len(vertices), len(base_owners))

    raw_frames = mesh["frames"]
    if type(raw_frames) is not dict or set(raw_frames) != set(_SIDES):
        _fail("frames must contain exactly left and right")
    for side in _SIDES:
        frame = raw_frames[side]
        if type(frame) is not dict:
            _fail(f"frames.{side} must be a mapping")
        for key in ("H", "d", "X", "U", "F", "exit"):
            _vector(frame.get(key), f"frames.{side}.{key}")
        _finite(frame.get("length"), f"frames.{side}.length")

    loops = _mapping(mesh["loops"], "mesh.loops")
    declared: set[tuple[int, int]] = set()
    for name, raw_loop in loops.items():
        if type(name) is not str or type(raw_loop) not in (list, tuple) or len(raw_loop) < 3:
            _fail("each mesh loop must contain at least three vertex indices")
        loop = tuple(raw_loop)
        if any(type(index) is not int or index < 0 or index >= len(vertices)
               for index in loop) or len(set(loop)) != len(loop):
            _fail(f"loop {name!r} has invalid indices")
        for index, left in enumerate(loop):
            edge = _edge_key(left, loop[(index + 1) % len(loop)])
            if edge in declared:
                _fail("a boundary edge is declared by more than one loop")
            declared.add(edge)

    uses = _edge_uses(quads)
    if any(len(rows) not in (1, 2) for rows in uses.values()):
        _fail("mesh has a non-manifold edge")
    if any(len(rows) == 2 and rows[0][1:] == rows[1][1:]
           for rows in uses.values()):
        _fail("mesh has an orientation conflict")
    boundary = {edge for edge, rows in uses.items() if len(rows) == 1}
    if declared != boundary:
        _fail("declared loops do not cover the mesh boundary exactly")

    adjacency = {index: set() for index in range(len(vertices))}
    for left, right in uses:
        adjacency[left].add(right)
        adjacency[right].add(left)
    if any(not neighbours for neighbours in adjacency.values()):
        _fail("mesh contains an unused vertex")
    seen = {0}
    pending = [0]
    while pending:
        vertex = pending.pop()
        for neighbour in adjacency[vertex]:
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    if len(seen) != len(vertices):
        _fail("mesh is disconnected")


def _identity_stencils(count: int) -> list[list[list[float | int]]]:
    return [[[index, 1.0]] for index in range(count)]


def _parse_leg_inputs(leg_inputs: Any) -> dict[str, dict[str, Any]]:
    value = _mapping(leg_inputs, "leg_inputs")
    if set(value) != set(_SIDES):
        _fail("leg_inputs must contain only left and right side entries")
    parsed: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        row = _mapping(value[side], f"leg_inputs.{side}")
        if set(row) != _SIDE_INPUT_KEYS:
            _fail(
                f"leg_inputs.{side} must contain T/K/A/J, radii, the two "
                "per-side factors, and the declared role metadata"
            )
        factor = _scalar(row["mid_thigh_factor"],
                         f"leg_inputs.{side}.mid_thigh_factor", lower=0.0)
        support = _scalar(row["support_fraction"],
                          f"leg_inputs.{side}.support_fraction",
                          lower=0.0, upper=1.0)
        if not 0.0 < support < min(
                1.0 - _MID_THIGH_FRACTION,
                _CALF_FRACTION / _POST_KNEE_SUPPORT_MULTIPLIER):
            _fail(
                f"leg_inputs.{side}.support_fraction must keep the named "
                "support rings strictly between mid-thigh/knee and knee/calf"
            )
        radii = _mapping(row["radii"], f"leg_inputs.{side}.radii")
        if set(radii) != {"knee", "calf", "ankle"}:
            _fail(f"leg_inputs.{side}.radii must contain knee, calf, and ankle")
        checked_radii = {}
        for name in ("knee", "calf", "ankle"):
            vector = _vector(radii[name], f"leg_inputs.{side}.radii.{name}")
            if any(not item > 0.0 for item in vector):
                _fail(f"leg_inputs.{side}.radii.{name} must be positive")
            checked_radii[name] = vector
        parsed[side] = {
            "J": _vector(row["J"], f"leg_inputs.{side}.J"),
            "T": _vector(row["T"], f"leg_inputs.{side}.T"),
            "K": _vector(row["K"], f"leg_inputs.{side}.K"),
            "A": _vector(row["A"], f"leg_inputs.{side}.A"),
            "radii": checked_radii,
            "mid_thigh_factor": factor,
            "support_fraction": support,
            "role_metadata": {
                key: row[key] for key in _ROLE_METADATA_KEYS
            },
        }
        for key, metadata in parsed[side]["role_metadata"].items():
            if type(metadata) is not str or not metadata:
                _fail(f"leg_inputs.{side}.{key} must be a non-empty string")
    return parsed


def _root_loop(root_mesh: Mapping[str, Any], side: str, vertex_count: int) -> list[int]:
    loops = _mapping(root_mesh["loops"], "root_mesh.loops")
    port = _THIGH_PORTS[side]
    raw_loop = loops.get(port)
    if type(raw_loop) not in (list, tuple) or len(raw_loop) != 8:
        _fail(f"root_mesh.loops.{port} must be an eight-vertex loop")
    loop = [int(index) if type(index) is int else -1 for index in raw_loop]
    if any(index < 0 or index >= vertex_count for index in loop) or len(set(loop)) != 8:
        _fail(f"root_mesh.loops.{port} is invalid")
    metadata = _mapping(root_mesh["metadata"], "root_mesh.metadata")
    transitions = _mapping(metadata.get("transition_indices"),
                           "root_mesh.metadata.transition_indices")
    row = _mapping(transitions.get(side), f"transition_indices.{side}")
    raw_exit = row.get("exit")
    if type(raw_exit) not in (list, tuple) or tuple(raw_exit) != tuple(loop):
        _fail(f"root metadata exit order disagrees with {port}")
    return loop


def _root_edge_signs(root_quads: list[tuple[int, int, int, int]],
                     loop: list[int]) -> int:
    uses = _edge_uses(root_quads)
    signs = []
    for index, left in enumerate(loop):
        right = loop[(index + 1) % len(loop)]
        rows = uses.get(_edge_key(left, right), [])
        if len(rows) != 1:
            _fail("root thigh exit edge is not a unique boundary edge")
        _, used_left, used_right = rows[0]
        if (used_left, used_right) == (left, right):
            signs.append(1)
        elif (used_left, used_right) == (right, left):
            signs.append(-1)
        else:  # pragma: no cover - guarded by the edge key lookup
            _fail("root thigh exit edge direction cannot be inferred")
    if len(set(signs)) != 1:
        _fail("root thigh exit loop has inconsistent winding")
    return signs[0]


def _project_plus_x(tangent: tuple[float, float, float], where: str) -> tuple[float, float, float]:
    world_x = (1.0, 0.0, 0.0)
    projected = _sub(world_x, _scale(tangent, _dot(world_x, tangent)))
    return _normalise(projected, f"{where} projected +X")


def _root_template(root_vertices: list[tuple[float, float, float]],
                   loop: list[int], centre: tuple[float, float, float],
                   frame: Mapping[str, Any], side: str) -> tuple[list[tuple[float, float]], tuple[float, float, float]]:
    x_axis = _vector(frame.get("X"), f"root_mesh.frames.{side}.X")
    f_axis = _vector(frame.get("F"), f"root_mesh.frames.{side}.F")
    direction = _vector(frame.get("d"), f"root_mesh.frames.{side}.d")
    x_axis = _normalise(x_axis, f"root_mesh.frames.{side}.X")
    f_axis = _normalise(f_axis, f"root_mesh.frames.{side}.F")
    direction = _normalise(direction, f"root_mesh.frames.{side}.d")
    up_axis = _scale(direction, -1.0)
    if abs(_dot(x_axis, f_axis)) > _COORDINATE_TOLERANCE:
        _fail(f"root_mesh.frames.{side} X/F are not orthogonal")
    if _dot(_cross(x_axis, up_axis), f_axis) < 1.0 - 1.0e-6:
        _fail(f"root_mesh.frames.{side} uses an incompatible forward convention")
    projected_x = _project_plus_x(direction, f"root_mesh.frames.{side}")
    if _dot(projected_x, x_axis) < 1.0 - 1.0e-6:
        _fail(f"root_mesh.frames.{side}.X is not the projected +X frame")

    projected: list[tuple[float, float]] = []
    anterior = 0.0
    posterior = 0.0
    lateral = 0.0
    for vertex in loop:
        delta = _sub(root_vertices[vertex], centre)
        normal_residual = abs(_dot(delta, direction))
        if normal_residual > _COORDINATE_TOLERANCE:
            _fail(f"root {side} thigh exit is not in its frame plane")
        lateral_value = _dot(delta, x_axis)
        forward_value = _dot(delta, f_axis)
        lateral = max(lateral, abs(lateral_value))
        anterior = max(anterior, forward_value)
        posterior = max(posterior, -forward_value)
        projected.append((lateral_value, forward_value))
    if not lateral > 0.0 or not anterior > 0.0 or not posterior > 0.0:
        _fail(f"root {side} thigh exit has a degenerate ellipse")
    template = [
        (lateral_value / lateral,
         forward_value / (anterior if forward_value >= 0.0 else posterior))
        for lateral_value, forward_value in projected
    ]
    return template, (lateral, anterior, posterior)


def _section_centres(T: tuple[float, float, float],
                     K: tuple[float, float, float],
                     A: tuple[float, float, float],
                     support_fraction: float) -> tuple[list[dict[str, Any]], tuple[float, float, float], tuple[float, float, float]]:
    incoming = _normalise(_sub(K, T), "leg T-K segment")
    outgoing = _normalise(_sub(A, K), "leg K-A segment")
    pre_knee_fraction = 1.0 - support_fraction
    post_knee_fraction = _POST_KNEE_SUPPORT_MULTIPLIER * support_fraction
    return ([
        {"name": "mid_thigh", "path": "T_to_K", "fraction": _MID_THIGH_FRACTION,
         "centre": _lerp(T, K, _MID_THIGH_FRACTION)},
        {"name": "knee_pre_support", "path": "T_to_K", "fraction": pre_knee_fraction,
         "centre": _lerp(T, K, pre_knee_fraction)},
        {"name": "knee", "path": "T_to_K", "fraction": 1.0,
         "centre": K},
        {"name": "knee_post_support", "path": "K_to_A", "fraction": post_knee_fraction,
         "centre": _lerp(K, A, post_knee_fraction)},
        {"name": "calf", "path": "K_to_A", "fraction": _CALF_FRACTION,
         "centre": _lerp(K, A, _CALF_FRACTION)},
        {"name": "ankle_approach", "path": "K_to_A", "fraction": _ANKLE_APPROACH_FRACTION,
         "centre": _lerp(K, A, _ANKLE_APPROACH_FRACTION)},
        {"name": "ankle", "path": "K_to_A", "fraction": 1.0,
         "centre": A},
    ], incoming, outgoing)


def _section_radii(exit_radii: tuple[float, float, float],
                   leg_radii: Mapping[str, tuple[float, float, float]],
                   factor: float, section: Mapping[str, Any]) -> tuple[float, float, float]:
    name = section["name"]
    if section["path"] == "T_to_K":
        fraction = float(section["fraction"])
        mid = _scale(exit_radii, factor)
        if fraction <= 0.70:
            return _lerp(exit_radii, mid, (fraction - 0.45) / 0.25)
        return _lerp(mid, leg_radii["knee"], (fraction - 0.70) / 0.30)
    fraction = float(section["fraction"])
    if fraction <= 0.35:
        return _lerp(leg_radii["knee"], leg_radii["calf"], fraction / 0.35)
    result = _lerp(leg_radii["calf"], leg_radii["ankle"],
                   (fraction - 0.35) / 0.65)
    if name == "ankle":
        return leg_radii["ankle"]
    return result


def _ring_frame(tangent: tuple[float, float, float], previous_x: tuple[float, float, float] | None,
                where: str) -> dict[str, tuple[float, float, float]]:
    x_axis = _project_plus_x(tangent, where)
    if previous_x is not None and _dot(x_axis, previous_x) < 0.0:
        x_axis = _scale(x_axis, -1.0)
    up_axis = _scale(tangent, -1.0)
    forward = _normalise(_cross(x_axis, up_axis), f"{where} forward frame")
    return {"tangent": tangent, "X": x_axis, "U": up_axis, "F": forward}


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _load_generic_transition() -> Any:
    path = _GENERIC_TRANSITION_PATH
    name = "_ck_connected_leg_generic_transition"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail(f"unable to load read-only generic transition evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _closed_generic_validation(mesh: Mapping[str, Any]) -> tuple[Any, ...]:
    """Bridge local closed-mesh admission to the frozen generic evaluator."""
    _validate_mesh(mesh)
    vertices = tuple(tuple(float(value) for value in point)
                     for point in mesh["vertices"])
    quads = tuple(tuple(int(index) for index in face) for face in mesh["quads"])
    uses = _edge_uses([tuple(face) for face in quads])
    loops = {
        str(name): tuple(int(index) for index in loop)
        for name, loop in _mapping(mesh["loops"], "mesh.loops").items()
    }
    stencils = tuple(
        tuple((int(term[0]), float(term[1])) for term in stencil)
        for stencil in mesh["base_stencils"]
    )
    return (
        vertices,
        quads,
        tuple(mesh["face_owners"]),
        tuple(mesh["control_owners"]),
        loops,
        stencils,
        uses,
    )


def _load_closed_generic_transition() -> Any:
    """Load the frozen subdivision code with only its loop admission bridged."""
    global _CLOSED_GENERIC_TRANSITION_CACHE
    if _CLOSED_GENERIC_TRANSITION_CACHE is not None:
        return _CLOSED_GENERIC_TRANSITION_CACHE
    path = _GENERIC_TRANSITION_PATH.resolve()
    path_digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    owner = "".join(character if character.isalnum() else "_"
                     for character in __name__)
    name = (f"_ck_connected_leg_closed_generic_{owner}_{path_digest}_"
            f"{id(_closed_generic_validation):x}")
    spec = importlib.util.spec_from_file_location(
        name, path)
    if spec is None or spec.loader is None:
        _fail(f"unable to load closed-mesh generic evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module._validate_mesh = _closed_generic_validation
    _CLOSED_GENERIC_TRANSITION_CACHE = module
    return module


def build(root_mesh: Mapping[str, Any], leg_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Append the bounded bilateral T/K/A chain to a saved calibrated L0 root."""
    root = _mapping(root_mesh, "root_mesh")
    _validate_mesh(root)
    vertices = [_vector(point, f"root_mesh.vertices[{index}]")
                for index, point in enumerate(root["vertices"])]
    root_quads = [tuple(face) for face in root["quads"]]
    root_count = len(vertices)
    root_face_count = len(root_quads)
    root_loops = {str(name): list(loop) for name, loop in _mapping(root["loops"], "root_mesh.loops").items()}
    frames = _mapping(root["frames"], "root_mesh.frames")
    parsed = _parse_leg_inputs(leg_inputs)

    face_owners = list(root["face_owners"])
    control_owners = list(root["control_owners"])
    root_metadata = _mapping(root["metadata"], "root_mesh.metadata")
    base_owners = list(root_metadata["base_control_owners"])
    output_vertices = copy.deepcopy(root["vertices"])
    output_quads = [list(face) for face in root_quads]
    output_face_owners = list(face_owners)
    output_control_owners = list(control_owners)
    output_loops = {name: list(loop) for name, loop in root_loops.items()
                    if name not in _THIGH_PORTS.values()}
    chain_metadata: dict[str, Any] = {}
    mapping_metadata: dict[str, Any] = {
        "root_vertex_old_to_new": [[index, index] for index in range(root_count)],
        "root_face_old_to_new": [[index, index] for index in range(root_face_count)],
    }

    for side in _SIDES:
        row = parsed[side]
        T, K, A = row["T"], row["K"], row["A"]
        factor = row["mid_thigh_factor"]
        support = row["support_fraction"]
        root_frame = _mapping(frames.get(side), f"root_mesh.frames.{side}")
        _close(T, _vector(root_frame.get("H"), f"root_mesh.frames.{side}.H"),
               f"leg_inputs.{side}.T")
        root_exit = _add(T, _scale(_sub(K, T), 0.45))
        _close(root_exit, _vector(root_frame.get("exit"),
                                  f"root_mesh.frames.{side}.exit"),
               f"computed {side} root exit")
        loop = _root_loop(root, side, root_count)
        centre = _scale(_add(*(vertices[index] for index in loop)), 1.0 / len(loop))
        _close(centre, root_exit, f"root {side} thigh exit centre")
        signs = _root_edge_signs(root_quads, loop)
        template, exit_radii = _root_template(vertices, loop, root_exit,
                                               root_frame, side)
        sections, incoming, outgoing = _section_centres(T, K, A, support)
        knee_tangent = _normalise(
            _add(incoming, outgoing), f"{side} knee bisector tangent")
        tangents = (incoming, incoming, knee_tangent, outgoing, outgoing,
                    outgoing, outgoing)
        section_radii = []
        section_frames = []
        previous_x = None
        for section, tangent in zip(sections, tangents):
            radii = _section_radii(exit_radii, row["radii"], factor, section)
            frame = _ring_frame(tangent, previous_x,
                                f"{side}.{section['name']}")
            previous_x = frame["X"]
            section_radii.append(radii)
            section_frames.append(frame)

        ring_indices: list[list[int]] = []
        new_vertex_indices: list[int] = []
        for section, radii, frame in zip(sections, section_radii, section_frames):
            ring: list[int] = []
            for lateral, forward in template:
                depth_radius = radii[1] if forward >= 0.0 else radii[2]
                point = _add(
                    section["centre"],
                    _scale(frame["X"], lateral * radii[0]),
                    _scale(frame["F"], forward * depth_radius),
                )
                index = len(output_vertices)
                output_vertices.append(list(point))
                output_control_owners.append(_LEG_OWNERS[side])
                base_owners.append(_LEG_OWNERS[side])
                ring.append(index)
                new_vertex_indices.append(index)
            ring_indices.append(ring)

        source_rings = [loop, *ring_indices]
        new_face_indices: list[int] = []
        for index, (source, target) in enumerate(zip(source_rings, source_rings[1:])):
            for corner, source_left in enumerate(source):
                source_right = source[(corner + 1) % len(source)]
                target_left = target[corner]
                target_right = target[(corner + 1) % len(target)]
                if index == 0:
                    if signs == 1:
                        face = [source_right, source_left, target_left, target_right]
                    else:
                        face = [source_left, source_right, target_right, target_left]
                elif signs == 1:
                    face = [source_right, source_left, target_left, target_right]
                else:
                    face = [source_left, source_right, target_right, target_left]
                new_face_indices.append(len(output_quads))
                output_quads.append(face)
                output_face_owners.append(_LEG_OWNERS[side])

        ankle_loop = ring_indices[-1]
        output_loops[_ANKLE_PORTS[side]] = list(ankle_loop)
        section_records = []
        for section_index, (section, radii, frame, ring) in enumerate(
                zip(sections, section_radii, section_frames, ring_indices)):
            section_records.append({
                "name": section["name"],
                "path": section["path"],
                "fraction": float(section["fraction"]),
                "indices": list(ring),
                "centre": list(section["centre"]),
                "radii": list(radii),
                "frame": {key: list(value) for key, value in frame.items()},
                "order": section_index,
            })
        chain_metadata[side] = {
            "owner": _LEG_OWNERS[side],
            "pose_only_J": list(row["J"]),
            "pose_only_J_usage": "recorded context; unused by rest construction",
            "role_metadata": copy.deepcopy(row["role_metadata"]),
            "mid_thigh_factor": factor,
            "support_fraction": support,
            "root_exit": list(loop),
            "root_exit_centre": list(root_exit),
            "root_exit_radii": list(exit_radii),
            "root_edge_winding": signs,
            "sections": section_records,
            "ring_order": [section["name"] for section in section_records],
            "ring_indices_by_name": {
                section["name"]: list(section["indices"])
                for section in section_records
            },
            "ankle_port": list(ankle_loop),
            "new_vertex_indices": list(new_vertex_indices),
            "new_face_indices": list(new_face_indices),
            "incoming_tangent": list(incoming),
            "outgoing_tangent": list(outgoing),
            "knee_tangent": list(knee_tangent),
        }
        chain_metadata[side]["frames"] = {
            "H": list(T),
            "knee": list(K),
            "ankle": list(A),
            "length": _norm(_sub(K, T)),
            "d": list(incoming),
            "X": list(section_frames[0]["X"]),
            "U": list(section_frames[0]["U"]),
            "F": list(section_frames[0]["F"]),
            "exit": list(root_exit),
        }
        mapping_metadata[f"{side}_new_vertices"] = list(new_vertex_indices)
        mapping_metadata[f"{side}_new_faces"] = list(new_face_indices)

    metadata = {
        "level": 0,
        "admission_status": "accepted",
        "admission_failures": [],
        "base_control_owners": base_owners,
        "base_vertex_count": len(base_owners),
        "dominant_owner_label": (
            "display representative only; authoritative ownership is "
            "base_control_owners plus full base_stencils"
        ),
        "root": {
            "schema": root.get("schema"),
            "level": root.get("level", 0),
            "vertex_count": root_count,
            "face_count": root_face_count,
            "old_thigh_ports_closed": {
                side: list(_root_loop(root, side, root_count)) for side in _SIDES
            },
        },
        "index_mapping": mapping_metadata,
        "chains": chain_metadata,
        "scheme": {
            "root_exit_fraction": 0.45,
            "new_sections": [
                ".70(T-K)", "(1-support_fraction)(T-K)", "K",
                "K+(1.2*support_fraction)(A-K)",
                "K+.35(A-K)", "K+.72(A-K)", "A",
            ],
            "per_side_controls": ["mid_thigh_factor", "support_fraction"],
            "pose_only_input": "J is recorded per side and does not reshape rest geometry",
            "radius_order": ["lateral", "anterior", "posterior"],
            "weld_rule": "reuse-root-exit-loop-no-duplicate-ring",
            "terminal_rule": "open-ankle-port-no-foot-or-cap",
            "frame_rule": "projected-plus-X-and-forward-X-cross-U",
            "knee_tangent_rule": (
                "normalized-incoming-plus-outgoing-bisector-independent-of-"
                "support_fraction"
            ),
            "evaluator": "read-only-generic-transition-catmull-clark-two-levels",
        },
    }
    output = {
        "schema": "creature-kernel.connected-leg-assembly-mesh.v1",
        "level": 0,
        "vertices": output_vertices,
        "quads": output_quads,
        "face_owners": output_face_owners,
        "control_owners": output_control_owners,
        "loops": output_loops,
        "base_stencils": _identity_stencils(len(output_vertices)),
        "frames": {
            side: copy.deepcopy(chain_metadata[side]["frames"])
            for side in _SIDES
        },
        "metadata": metadata,
    }
    _validate_mesh(output)
    return output


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Evaluate the connected-leg mesh through zero, one, or two CC levels."""
    if type(levels) is not int or levels < 0 or levels > 2:
        _fail("levels must be an integer between 0 and 2")
    _validate_mesh(mesh)
    current: Any = _jsonable(mesh)
    result = [current]
    loops = _mapping(mesh["loops"], "mesh.loops")
    generic = (_load_closed_generic_transition() if not loops
               else _load_generic_transition())
    for level in range(1, levels + 1):
        current = generic._subdivide_once(current, level)
        current = _jsonable(current)
        _validate_mesh(current)
        result.append(current)
    return result


__all__ = ["ConstructionError", "build", "evaluate"]

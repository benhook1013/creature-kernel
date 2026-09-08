"""Small, experiment-local harmonic hip binding and rigid hip pose.

The binding is deliberately separated from construction.  ``base_mesh`` is
the L0 carrier used for the graph solve and ``rest_mesh`` is the stored L2
surface whose sparse ``base_stencils`` provide the evaluated weights.  The
rest surface is never regenerated or repaired here.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

import numpy as np


_SIDES = ("left", "right")
_GROUPS = ("socket", "ringA", "ringB", "exit")
_PORTS = {"left": "port.left_thigh", "right": "port.right_thigh"}
_TOLERANCE = 1.0e-12


def _fail(message: str) -> None:
    raise ValueError(message)


def _check_weight_bounds(weights: np.ndarray, where: str) -> None:
    if np.any(weights < -_TOLERANCE) or np.any(weights > 1.0 + _TOLERANCE):
        _fail(f"{where} contains a weight outside [-1e-12, 1+1e-12]")


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        _fail(f"{where} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        _fail(f"{where} must be a finite number")
    return result


def _vector(value: Any, where: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        _fail(f"{where} must be a three-component vector")
    return [_number(item, f"{where}[{index}]") for index, item in enumerate(value)]


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be a mapping")
    return value


def _mesh_vertices(mesh: Mapping[str, Any], where: str) -> list[list[float]]:
    raw = mesh.get("vertices")
    if not isinstance(raw, (list, tuple)) or not raw:
        _fail(f"{where}.vertices must be a non-empty list")
    return [_vector(point, f"{where}.vertices[{index}]")
            for index, point in enumerate(raw)]


def _integer(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{where} must be an integer index")
    return value


def _quads(mesh: Mapping[str, Any], count: int, where: str) -> list[list[int]]:
    raw = mesh.get("quads")
    if not isinstance(raw, (list, tuple)):
        _fail(f"{where}.quads must be a list")
    result: list[list[int]] = []
    for qi, quad in enumerate(raw):
        if not isinstance(quad, (list, tuple)) or len(quad) != 4:
            _fail(f"{where}.quads[{qi}] must contain four indices")
        checked = [_integer(vertex, f"{where}.quads[{qi}][{i}]")
                   for i, vertex in enumerate(quad)]
        if any(vertex < 0 or vertex >= count for vertex in checked):
            _fail(f"{where}.quads[{qi}] contains an out-of-range vertex")
        result.append(checked)
    if not result:
        _fail(f"{where}.quads must not be empty")
    return result


def _boundary_graph(mesh: Mapping[str, Any], count: int) -> list[set[int]]:
    graph = [set() for _ in range(count)]
    for quad in _quads(mesh, count, "base_mesh"):
        for index, left in enumerate(quad):
            right = quad[(index + 1) % 4]
            if left == right:
                _fail("base_mesh quad has a zero-length boundary edge")
            graph[left].add(right)
            graph[right].add(left)

    seen = {0}
    pending = [0]
    while pending:
        vertex = pending.pop()
        for neighbour in graph[vertex]:
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    if len(seen) != count:
        _fail("L0 quad-boundary graph is disconnected")
    return graph


def _transition_indices(base_mesh: Mapping[str, Any], count: int) -> dict[str, dict[str, list[int]]]:
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    raw = _mapping(metadata.get("transition_indices"),
                   "base_mesh.metadata.transition_indices")
    if set(raw) != set(_SIDES):
        _fail("transition_indices must contain exactly left and right")

    result: dict[str, dict[str, list[int]]] = {}
    used: set[int] = set()
    for side in _SIDES:
        row = _mapping(raw[side], f"transition_indices.{side}")
        if set(row) != set(_GROUPS):
            _fail(f"transition_indices.{side} must contain socket, ringA, ringB and exit")
        result[side] = {}
        for group in _GROUPS:
            values = row[group]
            if not isinstance(values, (list, tuple)) or not values:
                _fail(f"transition_indices.{side}.{group} must be a non-empty list")
            checked = [_integer(value, f"transition_indices.{side}.{group}[{i}]")
                       for i, value in enumerate(values)]
            if len(set(checked)) != len(checked):
                _fail(f"transition_indices.{side}.{group} contains duplicates")
            if any(value < 0 or value >= count for value in checked):
                _fail(f"transition_indices.{side}.{group} contains an out-of-range index")
            if used.intersection(checked):
                _fail("transition_indices groups must be disjoint")
            used.update(checked)
            result[side][group] = checked
    return result


def _rest_stencils(rest_mesh: Mapping[str, Any], l0_count: int,
                   l2_count: int) -> list[list[tuple[int, float]]]:
    raw = rest_mesh.get("base_stencils")
    if not isinstance(raw, (list, tuple)) or len(raw) != l2_count:
        _fail("rest_mesh.base_stencils must have one stencil per L2 vertex")
    result: list[list[tuple[int, float]]] = []
    for vi, stencil in enumerate(raw):
        if not isinstance(stencil, (list, tuple)) or not stencil:
            _fail(f"rest_mesh.base_stencils[{vi}] must be non-empty")
        checked: list[tuple[int, float]] = []
        total = 0.0
        for si, pair in enumerate(stencil):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                _fail(f"rest_mesh.base_stencils[{vi}][{si}] must be [index, coefficient]")
            index = _integer(pair[0], f"rest_mesh.base_stencils[{vi}][{si}][0]")
            if index < 0 or index >= l0_count:
                _fail(f"rest_mesh.base_stencils[{vi}] contains an out-of-range index")
            coefficient = _number(pair[1], f"rest_mesh.base_stencils[{vi}][{si}][1]")
            checked.append((index, coefficient))
            total += coefficient
        if not math.isfinite(total) or abs(total - 1.0) > _TOLERANCE:
            _fail(f"rest_mesh.base_stencils[{vi}] does not partition unity")
        result.append(checked)
    return result


def _solve_base_weights(base_mesh: Mapping[str, Any], transitions: dict[str, dict[str, list[int]]],
                        graph: list[set[int]]) -> np.ndarray:
    count = len(graph)
    unknown = sorted({index for side in _SIDES for group in ("socket", "ringA")
                      for index in transitions[side][group]})
    if not unknown:
        _fail("transition_indices has no unknown vertices")
    unknown_position = {vertex: index for index, vertex in enumerate(unknown)}
    columns: list[np.ndarray] = []

    for leg_side in _SIDES:
        leg_anchors = set(transitions[leg_side]["ringB"])
        leg_anchors.update(transitions[leg_side]["exit"])
        if leg_anchors.intersection(unknown):
            _fail("leg anchors may not overlap unknown socket/ringA vertices")
        matrix = np.zeros((len(unknown), len(unknown)), dtype=np.float64)
        rhs = np.zeros(len(unknown), dtype=np.float64)
        for vertex, row in unknown_position.items():
            matrix[row, row] = float(len(graph[vertex]))
            for neighbour in graph[vertex]:
                if neighbour in unknown_position:
                    matrix[row, unknown_position[neighbour]] -= 1.0
                elif neighbour in leg_anchors:
                    rhs[row] += 1.0
        try:
            solved = np.linalg.solve(matrix, rhs)
        except np.linalg.LinAlgError as exc:
            raise ValueError(f"harmonic solve failed for {leg_side} leg") from exc
        if not np.all(np.isfinite(solved)):
            _fail(f"harmonic solve produced non-finite {leg_side} weights")

        column = np.zeros(count, dtype=np.float64)
        column[unknown] = solved
        column[list(leg_anchors)] = 1.0
        columns.append(column)

    left, right = columns
    pelvis = 1.0 - left - right
    weights = np.column_stack((pelvis, left, right))
    if not np.all(np.isfinite(weights)):
        _fail("base weights are non-finite")
    _check_weight_bounds(weights, "base weights")
    sums = np.sum(weights, axis=1)
    if not np.all(np.abs(sums - 1.0) <= _TOLERANCE):
        _fail("base weights do not partition unity")
    return weights


def _propagate_weights(stencils: list[list[tuple[int, float]]],
                       base_weights: np.ndarray) -> np.ndarray:
    evaluated = np.zeros((len(stencils), 3), dtype=np.float64)
    for vertex, stencil in enumerate(stencils):
        for base_index, coefficient in stencil:
            evaluated[vertex] += coefficient * base_weights[base_index]
    if not np.all(np.isfinite(evaluated)):
        _fail("evaluated weights are non-finite")
    _check_weight_bounds(evaluated, "evaluated weights")
    sums = np.sum(evaluated, axis=1)
    if not np.all(np.abs(sums - 1.0) <= _TOLERANCE):
        _fail("evaluated weights do not partition unity")
    return evaluated


def _validate_distal_ports(rest_mesh: Mapping[str, Any], weights: np.ndarray) -> dict[str, int]:
    loops = _mapping(rest_mesh.get("loops"), "rest_mesh.loops")
    counts: dict[str, int] = {}
    expected = {"left": np.array([0.0, 1.0, 0.0]),
                "right": np.array([0.0, 0.0, 1.0])}
    for side in _SIDES:
        name = _PORTS[side]
        raw_loop = loops.get(name)
        if not isinstance(raw_loop, (list, tuple)) or not raw_loop:
            _fail(f"rest_mesh.loops.{name} must be a non-empty list")
        checked = [_integer(value, f"rest_mesh.loops.{name}[{i}]")
                   for i, value in enumerate(raw_loop)]
        if any(value < 0 or value >= len(weights) for value in checked):
            _fail(f"rest_mesh.loops.{name} contains an out-of-range vertex")
        for vertex in checked:
            if not np.all(np.abs(weights[vertex] - expected[side]) <= _TOLERANCE):
                _fail(f"{name} is not full strength for the {side} leg")
        counts[name] = len(checked)
    return counts


def _case_points(case: Mapping[str, Any], reference_landmarks: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, list[float]], dict[str, list[float]], dict[str, list[float]]]:
    components = case.get("components")
    if not isinstance(components, Mapping):
        _fail("case.components must be a mapping")
    attachments = _mapping(case.get("attachments"), "case.attachments")
    if set(attachments) != set(_SIDES):
        _fail("case.attachments must contain exactly left and right")
    landmarks = _mapping(reference_landmarks, "reference_landmarks")
    result: dict[str, Any] = {}
    joints: dict[str, list[float]] = {}
    targets: dict[str, list[float]] = {}
    knees: dict[str, list[float]] = {}
    for side in _SIDES:
        row = _mapping(attachments[side], f"case.attachments.{side}")
        if "centre" not in row or "knee" not in row:
            _fail(f"case.attachments.{side} must contain centre and knee")
        target = _vector(row["centre"], f"case.attachments.{side}.centre")
        knee = _vector(row["knee"], f"case.attachments.{side}.knee")
        joint = _vector(landmarks.get(f"joint_{side}"),
                        f"reference_landmarks.joint_{side}")
        if np.linalg.norm(np.asarray(target) - joint) <= _TOLERANCE:
            _fail(f"{side} T must differ from J")
        if np.linalg.norm(np.asarray(knee) - joint) <= _TOLERANCE:
            _fail(f"{side} K must differ from J")
        joints[side], targets[side], knees[side] = joint, target, knee
    result["id"] = case.get("id")
    result["components"] = copy.deepcopy(dict(components))
    result["attachments"] = copy.deepcopy(dict(attachments))
    return result, joints, targets, knees


def _frame(joint: list[float], target: list[float], knee: list[float]) -> dict[str, Any]:
    j = np.asarray(joint, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    k = np.asarray(knee, dtype=np.float64)
    y = j - k
    y /= np.linalg.norm(y)
    x = np.asarray([1.0, 0.0, 0.0], dtype=np.float64)
    x -= np.dot(x, y) * y
    x_norm = np.linalg.norm(x)
    if not math.isfinite(float(x_norm)) or x_norm <= _TOLERANCE:
        _fail("global +X has no usable projection for the joint frame")
    x /= x_norm
    z = np.cross(x, y)
    rotation = np.column_stack((x, y, z))
    rest_matrix = np.eye(4, dtype=np.float64)
    rest_matrix[:3, :3] = rotation
    rest_matrix[:3, 3] = j
    return {
        "J": joint,
        "T": target,
        "K": knee,
        "rotation": rotation.tolist(),
        "rest_matrix": rest_matrix.tolist(),
        "T_local": (rotation.T @ (t - j)).tolist(),
        "K_local": (rotation.T @ (k - j)).tolist(),
    }


def _json_matrix(value: Any, where: str) -> np.ndarray:
    raw = np.asarray(value, dtype=np.float64)
    if raw.shape != (4, 4) or not np.all(np.isfinite(raw)):
        _fail(f"{where} must be a finite 4x4 matrix")
    return raw


def _angles(angles_degrees: Mapping[str, Any]) -> dict[str, float]:
    values = _mapping(angles_degrees, "angles_degrees")
    if set(values) != set(_SIDES):
        _fail("angles_degrees must contain exactly left and right")
    return {side: _number(values[side], f"angles_degrees.{side}")
            for side in _SIDES}


def _local_rotation_x(theta_degrees: float) -> np.ndarray:
    if theta_degrees == 0.0:
        return np.eye(4, dtype=np.float64)
    radians = math.radians(-theta_degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    return np.array([[1.0, 0.0, 0.0, 0.0],
                     [0.0, cosine, -sine, 0.0],
                     [0.0, sine, cosine, 0.0],
                     [0.0, 0.0, 0.0, 1.0]], dtype=np.float64)


def _joint_transforms(binding: Mapping[str, Any], angles_degrees: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    angles = _angles(angles_degrees)
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    if set(frames) != set(_SIDES):
        _fail("binding.rest_frames must contain exactly left and right")
    result: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        frame = _mapping(frames[side], f"binding.rest_frames.{side}")
        rest = _json_matrix(frame.get("rest_matrix"),
                            f"binding.rest_frames.{side}.rest_matrix")
        local = _local_rotation_x(angles[side])
        posed = rest @ local
        try:
            skin = posed @ np.linalg.inv(rest)
        except np.linalg.LinAlgError as exc:
            raise ValueError(f"rest frame for {side} is singular") from exc
        if not np.all(np.isfinite(skin)):
            _fail(f"skin matrix for {side} is non-finite")

        def carried(name: str) -> list[float]:
            point = np.asarray(_vector(frame.get(name),
                                       f"binding.rest_frames.{side}.{name}"))
            return (skin @ np.r_[point, 1.0])[:3].tolist()

        rest_points = {
            "J": _vector(frame.get("J"), f"binding.rest_frames.{side}.J"),
            "T": _vector(frame.get("T"), f"binding.rest_frames.{side}.T"),
            "K": _vector(frame.get("K"), f"binding.rest_frames.{side}.K"),
        }
        posed_points = {name: carried(name) for name in ("J", "T", "K")}
        result[side] = {
            # J/T/K are the posed diagnostic points; J remains fixed.  The
            # explicit rest/posed maps make the convention unambiguous.
            **posed_points,
            "rest_points": rest_points,
            "posed_points": posed_points,
            "rest_J": rest_points["J"],
            "rest_T": rest_points["T"],
            "rest_K": rest_points["K"],
            "posed_J": posed_points["J"],
            "posed_T": posed_points["T"],
            "posed_K": posed_points["K"],
            "rest_matrix": rest.tolist(),
            "posed_matrix": posed.tolist(),
            "skin_matrix": skin.tolist(),
            "angle_degrees": angles[side],
        }
    return result


def bind(base_mesh: Mapping[str, Any], rest_mesh: Mapping[str, Any], case: Mapping[str, Any],
         reference_landmarks: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe L0-harmonic/L2-stencil hip binding."""
    base = _mapping(base_mesh, "base_mesh")
    rest = _mapping(rest_mesh, "rest_mesh")
    base_vertices = _mesh_vertices(base, "base_mesh")
    rest_vertices = _mesh_vertices(rest, "rest_mesh")
    if "level" in base and base["level"] != 0:
        _fail("base_mesh must be level 0")
    if "level" in rest and rest["level"] != 2:
        _fail("rest_mesh must be level 2")
    graph = _boundary_graph(base, len(base_vertices))
    transitions = _transition_indices(base, len(base_vertices))
    stencils = _rest_stencils(rest, len(base_vertices), len(rest_vertices))
    base_weights = _solve_base_weights(base, transitions, graph)
    evaluated_weights = _propagate_weights(stencils, base_weights)
    port_counts = _validate_distal_ports(rest, evaluated_weights)
    case_copy, joints, targets, knees = _case_points(case, reference_landmarks)
    frames = {side: _frame(joints[side], targets[side], knees[side])
              for side in _SIDES}

    return {
        "schema": "creature-kernel.pelvis-hip-articulation-binding.v1",
        "base_weights": base_weights.tolist(),
        "evaluated_weights": evaluated_weights.tolist(),
        "l0_anchor_indices": copy.deepcopy(transitions),
        "rest_frames": frames,
        "t_local": {side: frames[side]["T_local"] for side in _SIDES},
        "k_local": {side: frames[side]["K_local"] for side in _SIDES},
        "case": case_copy,
        "metadata": {
            "algorithm": "uniform_l0_quad_boundary_harmonic_then_l2_sparse_stencil_3joint_lbs",
            "tolerance": _TOLERANCE,
            "rest_geometry_regenerated": False,
            "base_graph": "undirected quad boundary edges; quad diagonals excluded",
            "weight_columns": ["pelvis", "left_leg", "right_leg"],
            "stencil_provenance": "REST",
            "posed_cage_evaluation": False,
            "l2_distal_port_loop_counts": port_counts,
            "transition_indices": copy.deepcopy(transitions),
        },
    }


def joint_points(binding: Mapping[str, Any], angles: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return rest/posed joint points and matrices for both experimental pivots."""
    return _joint_transforms(_mapping(binding, "binding"), angles)


def pose(rest_mesh: Mapping[str, Any], binding: Mapping[str, Any],
         angles_degrees: Mapping[str, Any]) -> dict[str, Any]:
    """Pose stored L2 rest vertices with conventional three-joint LBS."""
    rest = _mapping(rest_mesh, "rest_mesh")
    vertices = _mesh_vertices(rest, "rest_mesh")
    weights_raw = _mapping(binding, "binding").get("evaluated_weights")
    if not isinstance(weights_raw, (list, tuple)) or len(weights_raw) != len(vertices):
        _fail("binding.evaluated_weights must match rest_mesh vertex count")
    weights = np.asarray([_vector(row, f"binding.evaluated_weights[{i}]")
                          for i, row in enumerate(weights_raw)], dtype=np.float64)
    if weights.shape != (len(vertices), 3) or not np.all(np.isfinite(weights)):
        _fail("binding.evaluated_weights must be finite N x 3 data")
    _check_weight_bounds(weights, "binding.evaluated_weights")
    if not np.all(np.abs(np.sum(weights, axis=1) - 1.0) <= _TOLERANCE):
        _fail("binding.evaluated_weights do not partition unity")
    transforms = _joint_transforms(_mapping(binding, "binding"), angles_degrees)
    skins = {side: _json_matrix(transforms[side]["skin_matrix"],
                                f"{side}.skin_matrix") for side in _SIDES}
    angles = _angles(angles_degrees)
    if all(value == 0.0 for value in angles.values()):
        posed_vertices = copy.deepcopy(vertices)
    else:
        posed_vertices = []
        for index, point in enumerate(vertices):
            homogeneous = np.r_[np.asarray(point, dtype=np.float64), 1.0]
            left_point = (skins["left"] @ homogeneous)[:3]
            right_point = (skins["right"] @ homogeneous)[:3]
            value = (weights[index, 0] * homogeneous[:3]
                     + weights[index, 1] * left_point
                     + weights[index, 2] * right_point)
            if not np.all(np.isfinite(value)):
                _fail(f"posed vertex {index} is non-finite")
            posed_vertices.append(value.tolist())

    output = copy.deepcopy(dict(rest))
    output["vertices"] = posed_vertices
    provenance = copy.deepcopy(output.get("provenance", {}))
    if not isinstance(provenance, dict):
        provenance = {}
    provenance.update({"vertices": "POSED_BY_REST_L2_3JOINT_LBS",
                       "base_stencils": "REST",
                       "stencil_evaluation": "not posed cage evaluation"})
    output["provenance"] = provenance
    metadata = copy.deepcopy(output.get("metadata", {}))
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update({"stencil_provenance": "REST",
                     "base_stencils_provenance": "REST",
                     "posed_cage_evaluation": False,
                     "rest_geometry_regenerated": False,
                     "pose_angles_degrees": {side: angles[side] for side in _SIDES}})
    output["metadata"] = metadata
    return output

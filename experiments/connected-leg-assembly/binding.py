"""Bounded source-station binding for the connected-leg staging experiment.

This module consumes the L0/L2 meshes produced by ``construction.py``.  It
does not construct geometry or infer ownership from labels.  The L0 mesh is
expected to contain the exact 152-vertex root prefix followed by seven
eight-vertex station rings for each side.  The construction metadata must
expose those rings explicitly under one of
``metadata["chains"][side]["sections"]``::

    metadata["chains"][side]["sections"] = [
        {"name": ..., "indices": [eight L0 indices], "centre": [...]}, ...
    ]

The section names and order are the construction contract.  This binder does
not regenerate station geometry or infer ownership from labels.  The rest L2
mesh supplies the actual ``base_stencils`` used to propagate the five leg
weights, or the nine weights when source-owned arm metadata is present.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

import numpy as np


_SIDES = ("left", "right")
_LEG_JOINT_ORDER = ("pelvis", "left_hip", "left_knee", "right_hip", "right_knee")
_LEG_WEIGHT_COLUMNS = ("pelvis", "left_thigh", "left_shank", "right_thigh", "right_shank")
_ARM_JOINT_ORDER = (*_LEG_JOINT_ORDER,
                    "left_shoulder", "left_elbow", "right_shoulder", "right_elbow")
_ARM_WEIGHT_COLUMNS = (*_LEG_WEIGHT_COLUMNS,
                       "left_upper_arm", "left_forearm",
                       "right_upper_arm", "right_forearm")
_HEAD_JOINT_ORDER = (*_LEG_JOINT_ORDER, "neck")
_HEAD_WEIGHT_COLUMNS = (*_LEG_WEIGHT_COLUMNS, "neck")
_ARM_HEAD_JOINT_ORDER = (*_ARM_JOINT_ORDER, "neck")
_ARM_HEAD_WEIGHT_COLUMNS = (*_ARM_WEIGHT_COLUMNS, "neck")
_JOINT_ORDER = _LEG_JOINT_ORDER
_WEIGHT_COLUMNS = _LEG_WEIGHT_COLUMNS
_STATION_NAMES = (
    "mid_thigh",
    "knee_pre_support",
    "knee",
    "knee_post_support",
    "calf",
    "ankle_approach",
    "ankle",
)
_SOURCE_STATION_IDS = (".70TK", ".90TK", "K", "K+.12KA", "K+.35KA", "K+.72KA", "A")
_STATION_SHANK_WEIGHTS = (0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 1.0)
_ROOT_VERTEX_COUNT = 152
_STATION_COUNT = len(_STATION_NAMES)
_RING_VERTEX_COUNT = 8
_TOLERANCE = 1.0e-12
_FRAME_TOLERANCE = 1.0e-10
_CONSTRUCTION_COORDINATE_TOLERANCE = 1.0e-8
_SUPPORT_MULTIPLIER = 1.2
_MID_THIGH_FRACTION = 0.70
_CALF_FRACTION = 0.35
_ANKLE_APPROACH_FRACTION = 0.72
_TAIL_SUPPORT_OWN = 0.55
_TAIL_SUPPORT_OTHER = 0.15
_ARM_SECTION_NAMES = (
    "upper_belly", "pre_elbow", "elbow", "post_elbow", "forearm_belly",
    "pre_wrist", "wrist", "palm", "knuckle", "terminal",
)


def _binding_layout(has_arms: bool, has_head: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if has_arms and has_head:
        return _ARM_HEAD_JOINT_ORDER, _ARM_HEAD_WEIGHT_COLUMNS
    if has_arms:
        return _ARM_JOINT_ORDER, _ARM_WEIGHT_COLUMNS
    if has_head:
        return _HEAD_JOINT_ORDER, _HEAD_WEIGHT_COLUMNS
    return _LEG_JOINT_ORDER, _LEG_WEIGHT_COLUMNS


def _fail(message: str) -> None:
    raise ValueError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be a mapping")
    return value


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
    return [_number(item, f"{where}[{index}]")
            for index, item in enumerate(value)]


def _integer(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{where} must be an integer index")
    return value


def _vertices(mesh: Mapping[str, Any], where: str) -> list[list[float]]:
    raw = mesh.get("vertices")
    if not isinstance(raw, (list, tuple)) or not raw:
        _fail(f"{where}.vertices must be a non-empty list")
    return [_vector(point, f"{where}.vertices[{index}]")
            for index, point in enumerate(raw)]


def _quads(mesh: Mapping[str, Any], count: int, where: str) -> list[list[int]]:
    raw = mesh.get("quads")
    if not isinstance(raw, (list, tuple)):
        _fail(f"{where}.quads must be a list")
    result: list[list[int]] = []
    for quad_index, quad in enumerate(raw):
        if not isinstance(quad, (list, tuple)) or len(quad) != 4:
            _fail(f"{where}.quads[{quad_index}] must contain four indices")
        checked = [_integer(value, f"{where}.quads[{quad_index}][{slot}]")
                   for slot, value in enumerate(quad)]
        if any(value < 0 or value >= count for value in checked):
            _fail(f"{where}.quads[{quad_index}] contains an out-of-range vertex")
        result.append(checked)
    if not result:
        _fail(f"{where}.quads must not be empty")
    return result


def _check_weight_bounds(weights: np.ndarray, where: str) -> None:
    if not np.all(np.isfinite(weights)):
        _fail(f"{where} must be finite")
    # Numeric guard recovery matching the prior baseline binding: this is a
    # validation tolerance only, not a binding-method retune.  Do not clamp
    # or renormalize the source/stencil result.
    if np.any(weights < -_TOLERANCE) or np.any(weights > 1.0 + _TOLERANCE):
        _fail(f"{where} contains a weight outside [-{_TOLERANCE}, 1 + {_TOLERANCE}]")
    if not np.all(np.abs(np.sum(weights, axis=1) - 1.0) <= _TOLERANCE):
        _fail(f"{where} do not partition unity")


def _weight_matrix(value: Any, rows: int, columns: int, where: str) -> np.ndarray:
    if not isinstance(value, (list, tuple)) or len(value) != rows:
        _fail(f"{where} must have shape {rows}x{columns}")
    parsed = []
    for row_index, row in enumerate(value):
        if not isinstance(row, (list, tuple)) or len(row) != columns:
            _fail(f"{where}[{row_index}] must have {columns} columns")
        parsed.append([_number(item, f"{where}[{row_index}][{column}]")
                       for column, item in enumerate(row)])
    result = np.asarray(parsed, dtype=np.float64)
    _check_weight_bounds(result, where)
    return result


def _validate_levels(base: Mapping[str, Any], rest: Mapping[str, Any]) -> None:
    if "level" in base and base["level"] != 0:
        _fail("base_mesh must be level 0")
    if "level" in rest and rest["level"] != 2:
        _fail("rest_mesh must be level 2")


def _tail_contract(base_mesh: Mapping[str, Any], base_count: int,
                   base_quads: list[list[int]], prior_quads: list[list[int]]) -> dict[str, Any] | None:
    """Validate the explicit local host-58 replacement and tail weight handoff."""
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    raw_tail = metadata.get("tail")
    if raw_tail is None:
        return None
    tail = _mapping(raw_tail, "base_mesh.metadata.tail")
    if tail.get("enabled") is not True:
        _fail("base_mesh.metadata.tail.enabled must be true for a tail allocation")

    identity = _mapping(tail.get("source_host_identity"),
                        "base_mesh.metadata.tail.source_host_identity")
    host_face = _integer(identity.get("face_index"),
                         "base_mesh.metadata.tail.source_host_identity.face_index")
    host_vertices = identity.get("vertex_indices")
    if not isinstance(host_vertices, (list, tuple)) or len(host_vertices) != 4:
        _fail("tail source_host_identity.vertex_indices must contain four vertices")
    host_vertices = [_integer(index, f"tail source host vertex {slot}")
                     for slot, index in enumerate(host_vertices)]
    if len(set(host_vertices)) != 4 or host_face < 0 or host_face >= len(prior_quads):
        _fail("tail source host identity is outside the supplied original root")
    if identity.get("owner") != "domain.pelvis":
        _fail("tail source host identity must name the domain.pelvis owner")
    if host_vertices != prior_quads[host_face]:
        _fail("tail source host identity does not match the supplied original root face")

    replacement = _mapping(tail.get("face_replacement"),
                           "base_mesh.metadata.tail.face_replacement")
    if replacement.get("original_face_index") != host_face:
        _fail("tail face replacement does not name the declared original host face")
    if list(replacement.get("original_quad", ())) != host_vertices:
        _fail("tail face replacement does not repeat the declared original host quad")
    if replacement.get("original_host_retained") is not False:
        _fail("tail host replacement must explicitly remove the original host face")
    replacement_indices = replacement.get("replacement_face_indices")
    if not isinstance(replacement_indices, (list, tuple)) or not replacement_indices:
        _fail("tail face replacement must declare replacement face indices")
    replacement_indices = [_integer(index, "tail replacement face index")
                           for index in replacement_indices]
    if len(set(replacement_indices)) != len(replacement_indices):
        _fail("tail replacement face indices must be unique")
    if host_face not in replacement_indices:
        _fail("tail replacement must retain the host face slot for the first annulus face")
    one_to_many = replacement.get("one_to_many")
    if one_to_many != [[host_face, *replacement_indices]]:
        _fail("tail one-to-many face correspondence disagrees with replacement_face_indices")
    if any(index < 0 or index >= len(base_quads) for index in replacement_indices):
        _fail("tail replacement face index is outside base_mesh.quads")
    if base_quads[host_face] == prior_quads[host_face]:
        _fail("declared tail host replacement did not replace the original host quad")

    index_mapping = _mapping(metadata.get("index_mapping"),
                             "base_mesh.metadata.index_mapping")
    kept_raw = index_mapping.get("root_face_mappings_excluding_tail_host")
    expected_kept = [[index, index] for index in range(len(prior_quads))
                     if index != host_face]
    if kept_raw != expected_kept:
        _fail("tail kept-face correspondence must explicitly preserve every non-host root face")
    for old_index, new_index in expected_kept:
        if base_quads[new_index] != prior_quads[old_index]:
            _fail(f"tail kept-face correspondence changed root face {old_index}")

    raw_indices = tail.get("new_vertex_indices")
    if not isinstance(raw_indices, (list, tuple)) or not raw_indices:
        _fail("base_mesh.metadata.tail.new_vertex_indices must be non-empty")
    new_indices = [_integer(index, f"tail.new_vertex_indices[{slot}]")
                   for slot, index in enumerate(raw_indices)]
    if len(set(new_indices)) != len(new_indices):
        _fail("tail.new_vertex_indices must be unique")
    if any(index < _ROOT_VERTEX_COUNT or index >= base_count for index in new_indices):
        _fail("tail.new_vertex_indices must reference appended L0 vertices")

    raw_rings = tail.get("ring_indices")
    if not isinstance(raw_rings, (list, tuple)) or not raw_rings:
        _fail("tail.ring_indices must contain ordered tail rings")
    rings: list[list[int]] = []
    for ring_index, raw_ring in enumerate(raw_rings):
        if not isinstance(raw_ring, (list, tuple)) or not raw_ring:
            _fail(f"tail.ring_indices[{ring_index}] must be a non-empty ring")
        ring = [_integer(index, f"tail.ring_indices[{ring_index}][{slot}]")
                for slot, index in enumerate(raw_ring)]
        if len(set(ring)) != len(ring) or any(index not in new_indices for index in ring):
            _fail("tail ring allocations must be unique members of new_vertex_indices")
        rings.append(ring)
    if [index for ring in rings for index in ring] != new_indices:
        _fail("tail ring_indices must cover new_vertex_indices in declared order")
    if any(len(ring) != 4 for ring in rings):
        _fail("tail rings must retain the four-corner source phase correspondence")
    raw_phase = tail.get("source_phase")
    if not isinstance(raw_phase, (list, tuple)) or len(raw_phase) != 4:
        _fail("tail source_phase must contain four host-corner phases")
    source_phase: list[list[int]] = []
    for corner, phase in enumerate(raw_phase):
        if (not isinstance(phase, (list, tuple)) or len(phase) != 2 or
                any(type(value) is not int or value not in (-1, 1) for value in phase)):
            _fail(f"tail.source_phase[{corner}] must be a signed two-component phase")
        source_phase.append(list(phase))
    if len({tuple(phase) for phase in source_phase}) != 4:
        _fail("tail source_phase must contain four distinct host-corner phases")
    host_record = _mapping(tail.get("host"), "base_mesh.metadata.tail.host")
    if host_record.get("source_phase") != source_phase:
        _fail("tail host and tail source_phase declarations must agree")
    fractions = tail.get("station_fractions")
    if not isinstance(fractions, (list, tuple)) or len(fractions) != len(rings):
        _fail("tail station_fractions must match tail ring_indices")
    fractions = [_number(value, f"tail.station_fractions[{index}]")
                 for index, value in enumerate(fractions)]
    if any(value < 0.0 or value > 1.0 for value in fractions) or fractions != sorted(fractions):
        _fail("tail station_fractions must be ordered inside [0, 1]")
    if fractions[0] != 0.0 or fractions[-1] != 1.0:
        _fail("tail station_fractions must begin at collar 0 and end at distal 1")

    transition = _mapping(tail.get("transition_weights"),
                          "base_mesh.metadata.tail.transition_weights")
    blend_value = transition.get("collar_blend_strength")
    if blend_value is None:
        _fail("tail transition_weights must explicitly declare collar_blend_strength; no hidden default is permitted")
    collar_blend = _number(blend_value,
                           "tail.transition_weights.collar_blend_strength")
    if collar_blend < 0.0 or collar_blend > 1.0:
        _fail("tail collar_blend_strength must lie in [0, 1]")
    supports = _mapping(transition.get("supports"),
                        "tail.transition_weights.supports")
    if set(supports) != {str(index) for index in new_indices}:
        _fail("tail transition supports must cover every new tail vertex exactly once")
    checked_supports: dict[int, tuple[list[int], list[float]]] = {}
    for index in new_indices:
        row = _mapping(supports[str(index)], f"tail.transition_weights.supports.{index}")
        if row.get("target_joint") != "pelvis":
            _fail(f"tail transition support {index} must target the existing pelvis joint")
        support_indices = row.get("host_vertex_indices")
        values = row.get("convex_weights")
        if list(support_indices or ()) != host_vertices:
            _fail(f"tail transition support {index} must use the declared original host corners")
        corner = _integer(row.get("host_corner"),
                          f"tail transition support {index}.host_corner")
        expected_corner = new_indices.index(index) % 4
        if corner != expected_corner:
            _fail(f"tail transition support {index} has the wrong retained source corner")
        if row.get("source_phase") != source_phase[corner]:
            _fail(f"tail transition support {index} has the wrong source phase")
        if not isinstance(values, (list, tuple)) or len(values) != len(host_vertices):
            _fail(f"tail transition support {index} must provide one weight per host corner")
        weights = [_number(value, f"tail support {index} weight {slot}")
                   for slot, value in enumerate(values)]
        if any(value < -_TOLERANCE for value in weights) or abs(sum(weights) - 1.0) > _TOLERANCE:
            _fail(f"tail transition support {index} must be a convex host-corner combination")
        expected_weights = [
            _TAIL_SUPPORT_OWN if slot == corner else _TAIL_SUPPORT_OTHER
            for slot in range(4)
        ]
        if any(abs(actual - expected) > _TOLERANCE
               for actual, expected in zip(weights, expected_weights)):
            _fail(f"tail transition support {index} must match the declared inset-corner rule")
        checked_supports[index] = (host_vertices[:], weights)
    return {
        "host_face": host_face,
        "host_vertices": host_vertices,
        "replacement_faces": replacement_indices,
        "kept_faces": expected_kept,
        "new_vertex_indices": new_indices,
        "rings": rings,
        "station_fractions": fractions,
        "source_phase": source_phase,
        "collar_blend_strength": collar_blend,
        "supports": checked_supports,
    }


def _validate_root(base_vertices: list[list[float]], base_quads: list[list[int]],
                   prior_vertices: list[list[float]], prior_quads: list[list[int]],
                   base_mesh: Mapping[str, Any]) -> dict[str, Any] | None:
    if len(prior_vertices) != _ROOT_VERTEX_COUNT:
        _fail("prior_root_mesh must contain exactly 152 L0 vertices")
    if len(base_vertices) < _ROOT_VERTEX_COUNT:
        _fail("base_mesh must retain the 152-vertex root prefix")
    if base_vertices[:_ROOT_VERTEX_COUNT] != prior_vertices:
        _fail("base_mesh root coordinates do not exactly match prior_root_mesh")
    if len(base_quads) < len(prior_quads):
        _fail("base_mesh must retain all prior_root_mesh quads")
    tail = _tail_contract(base_mesh, len(base_vertices), base_quads, prior_quads)
    if tail is None and base_quads[:len(prior_quads)] != prior_quads:
        _fail("base_mesh root quads do not exactly match prior_root_mesh")
    return tail


def _validate_constructor_root_metadata(base_mesh: Mapping[str, Any],
                                        prior_quad_count: int,
                                        tail: Mapping[str, Any] | None) -> None:
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    root = _mapping(metadata.get("root"), "base_mesh.metadata.root")
    if root.get("vertex_count") != _ROOT_VERTEX_COUNT:
        _fail("base_mesh.metadata.root.vertex_count must be 152")
    if root.get("face_count") != prior_quad_count:
        _fail("base_mesh.metadata.root.face_count must match prior_root_mesh")
    index_mapping = _mapping(metadata.get("index_mapping"),
                             "base_mesh.metadata.index_mapping")
    expected_vertices = [[index, index] for index in range(_ROOT_VERTEX_COUNT)]
    if index_mapping.get("root_vertex_old_to_new") != expected_vertices:
        _fail("base_mesh root vertex index mapping does not preserve the supplied root")
    expected_faces = [[index, index] for index in range(prior_quad_count)]
    if tail is None and index_mapping.get("root_face_old_to_new") != expected_faces:
        _fail("base_mesh root face index mapping does not preserve the supplied root")


def _prior_root_weights(prior_hip_binding: Mapping[str, Any]) -> np.ndarray:
    raw = prior_hip_binding.get("base_weights")
    result = _weight_matrix(raw, _ROOT_VERTEX_COUNT, 3,
                            "prior_hip_binding.base_weights")
    return result


def _expanded_root_weights(prior: np.ndarray, base_count: int,
                           columns: tuple[str, ...]) -> np.ndarray:
    minimum_count = _ROOT_VERTEX_COUNT + 2 * _STATION_COUNT * _RING_VERTEX_COUNT
    if base_count < minimum_count:
        _fail("base_mesh must retain all seven eight-vertex stations per side after the 152 root vertices")
    result = np.zeros((base_count, len(columns)), dtype=np.float64)
    result[:_ROOT_VERTEX_COUNT, 0] = prior[:, 0]
    result[:_ROOT_VERTEX_COUNT, 1] = prior[:, 1]
    result[:_ROOT_VERTEX_COUNT, 3] = prior[:, 2]
    return result


def _expected_station_centres(points: Mapping[str, list[float]], support: float) -> list[np.ndarray]:
    T = np.asarray(points["T"], dtype=np.float64)
    K = np.asarray(points["K"], dtype=np.float64)
    A = np.asarray(points["A"], dtype=np.float64)
    fractions = (_MID_THIGH_FRACTION, 1.0 - support, 1.0,
                 _SUPPORT_MULTIPLIER * support, _CALF_FRACTION,
                 _ANKLE_APPROACH_FRACTION, 1.0)
    return [T + fraction * (K - T) for fraction in fractions[:3]] + [
        K + fraction * (A - K) for fraction in fractions[3:]
    ]


def _chain_rings(base_mesh: Mapping[str, Any], base_count: int,
                 legs: dict[str, dict[str, list[float]]],
                 declared_support: dict[str, float]) -> tuple[dict[str, list[list[int]]],
                                                               dict[str, list[list[float]]]]:
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    chains = _mapping(metadata.get("chains"), "base_mesh.metadata.chains")
    if set(chains) != set(_SIDES):
        _fail("base_mesh.metadata.chains must contain exactly left and right")

    rings: dict[str, list[list[int]]] = {}
    centres: dict[str, list[list[float]]] = {}
    for side in _SIDES:
        chain = _mapping(chains[side], f"base_mesh.metadata.chains.{side}")
        sections = chain.get("sections")
        if not isinstance(sections, (list, tuple)) or len(sections) != _STATION_COUNT:
            _fail(f"base_mesh.metadata.chains.{side}.sections must contain seven records")
        if chain.get("ring_order") != list(_STATION_NAMES):
            _fail(f"base_mesh.metadata.chains.{side}.ring_order does not match the constructor section order")
        named = _mapping(chain.get("ring_indices_by_name"),
                         f"base_mesh.metadata.chains.{side}.ring_indices_by_name")
        if set(named) != set(_STATION_NAMES):
            _fail(f"base_mesh.metadata.chains.{side}.ring_indices_by_name has the wrong section names")
        support = declared_support[side]
        expected_centres = _expected_station_centres(legs[side], support)
        side_rings: list[list[int]] = []
        side_centres: list[list[float]] = []
        for station_index, raw_section in enumerate(sections):
            section = _mapping(raw_section,
                               f"base_mesh.metadata.chains.{side}.sections[{station_index}]")
            if section.get("name") != _STATION_NAMES[station_index]:
                _fail(f"construction section order/name mismatch for {side} station {station_index}")
            if section.get("order") != station_index:
                _fail(f"construction section order mismatch for {side} station {station_index}")
            ring_value = section.get("indices")
            if not isinstance(ring_value, (list, tuple)) or len(ring_value) != _RING_VERTEX_COUNT:
                _fail(f"construction section {side}.{_STATION_NAMES[station_index]} must contain eight indices")
            ring = [_integer(index, f"construction section {side}.{_STATION_NAMES[station_index]}.indices[{slot}]")
                    for slot, index in enumerate(ring_value)]
            if len(set(ring)) != _RING_VERTEX_COUNT:
                _fail(f"construction section {side}.{_STATION_NAMES[station_index]} contains duplicate indices")
            named_ring = named[_STATION_NAMES[station_index]]
            if list(named_ring) != ring:
                _fail(f"construction named ring disagrees with section for {side}.{_STATION_NAMES[station_index]}")
            fraction = _number(section.get("fraction"),
                               f"construction section {side}.{_STATION_NAMES[station_index]}.fraction")
            expected_fraction = (_MID_THIGH_FRACTION, 1.0 - support, 1.0,
                                 _SUPPORT_MULTIPLIER * support, _CALF_FRACTION,
                                 _ANKLE_APPROACH_FRACTION, 1.0)[station_index]
            if not math.isclose(fraction, expected_fraction, rel_tol=0.0,
                                abs_tol=_CONSTRUCTION_COORDINATE_TOLERANCE):
                _fail(f"construction section fraction disagrees with support_fraction for {side}.{_STATION_NAMES[station_index]}")
            centre = _vector(section.get("centre"),
                             f"construction section {side}.{_STATION_NAMES[station_index]}.centre")
            if not np.allclose(centre, expected_centres[station_index],
                               atol=_CONSTRUCTION_COORDINATE_TOLERANCE, rtol=0.0):
                _fail(f"construction section centre disagrees with T/K/A for {side}.{_STATION_NAMES[station_index]}")
            side_rings.append(ring)
            side_centres.append(centre)
        new_indices = chain.get("new_vertex_indices")
        expected_indices = [index for ring in side_rings for index in ring]
        if not isinstance(new_indices, (list, tuple)) or list(new_indices) != expected_indices:
            _fail(f"construction new_vertex_indices disagrees with sections for {side}")
        rings[side] = side_rings
        centres[side] = side_centres

    all_indices = [index for side in _SIDES for ring in rings[side] for index in ring]
    if any(index < _ROOT_VERTEX_COUNT or index >= base_count for index in all_indices):
        _fail("construction sections must reference only appended L0 station vertices")
    if len(set(all_indices)) != len(all_indices):
        _fail("construction sections must not overlap")
    return rings, centres


def _arm_vertex_indices(base_mesh: Mapping[str, Any], base_count: int,
                        rings: dict[str, list[list[int]]],
                        excluded_indices: set[int] | None = None) -> dict[str, dict[str, Any]]:
    """Validate the semantic appended-arm allocation, without fixed counts."""
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    raw_arms = metadata.get("arms")
    if raw_arms is None:
        return {}
    arms = _mapping(raw_arms, "base_mesh.metadata.arms")
    if set(arms) != set(_SIDES):
        _fail("base_mesh.metadata.arms must contain exactly left and right")
    leg_indices = {index for side in _SIDES for ring in rings[side] for index in ring}
    result: dict[str, dict[str, Any]] = {}
    used: set[int] = set()
    for side in _SIDES:
        row = _mapping(arms[side], f"base_mesh.metadata.arms.{side}")
        source_port = _mapping(row.get("source_port"),
                               f"base_mesh.metadata.arms.{side}.source_port")
        port = [_integer(index, f"base_mesh.metadata.arms.{side}.source_port.indices[{i}]")
                for i, index in enumerate(source_port.get("indices", []))]
        if len(port) != _RING_VERTEX_COUNT or len(set(port)) != _RING_VERTEX_COUNT:
            _fail(f"base_mesh.metadata.arms.{side}.source_port.indices must contain eight unique vertices")
        if any(index < 0 or index >= _ROOT_VERTEX_COUNT for index in port):
            _fail(f"base_mesh.metadata.arms.{side}.source_port.indices must reference root vertices")
        collar = _mapping(row.get("collar"), f"base_mesh.metadata.arms.{side}.collar")
        collar_value = collar.get("indices")
        if not isinstance(collar_value, (list, tuple)) or len(collar_value) != _RING_VERTEX_COUNT:
            _fail(f"base_mesh.metadata.arms.{side}.collar.indices must contain eight vertices")
        collar_indices = [_integer(index, f"base_mesh.metadata.arms.{side}.collar.indices[{i}]")
                          for i, index in enumerate(collar_value)]
        if len(set(collar_indices)) != _RING_VERTEX_COUNT:
            _fail(f"base_mesh.metadata.arms.{side}.collar.indices must be unique")
        sections_value = row.get("sections")
        if not isinstance(sections_value, (list, tuple)) or len(sections_value) != len(_ARM_SECTION_NAMES):
            _fail(f"base_mesh.metadata.arms.{side}.sections must contain the named arm sections")
        section_indices: dict[str, list[int]] = {}
        for expected_name, raw_section in zip(_ARM_SECTION_NAMES, sections_value):
            section = _mapping(raw_section,
                               f"base_mesh.metadata.arms.{side}.sections.{expected_name}")
            if section.get("name") != expected_name:
                _fail(f"base_mesh.metadata.arms.{side}.sections order/name mismatch")
            value = section.get("indices")
            if not isinstance(value, (list, tuple)) or len(value) != _RING_VERTEX_COUNT:
                _fail(f"base_mesh.metadata.arms.{side}.sections.{expected_name}.indices must contain eight vertices")
            indices = [_integer(index, f"base_mesh.metadata.arms.{side}.sections.{expected_name}.indices[{i}]")
                       for i, index in enumerate(value)]
            if len(set(indices)) != _RING_VERTEX_COUNT:
                _fail(f"base_mesh.metadata.arms.{side}.sections.{expected_name}.indices must be unique")
            section_indices[expected_name] = indices
        cap = _mapping(row.get("cap"), f"base_mesh.metadata.arms.{side}.cap")
        cap_index = _integer(cap.get("vertex"), f"base_mesh.metadata.arms.{side}.cap.vertex")
        new_value = row.get("new_vertex_indices")
        if not isinstance(new_value, (list, tuple)):
            _fail(f"base_mesh.metadata.arms.{side}.new_vertex_indices must be a list")
        new_indices = [_integer(index, f"base_mesh.metadata.arms.{side}.new_vertex_indices[{i}]")
                       for i, index in enumerate(new_value)]
        expected = collar_indices + [index for name in _ARM_SECTION_NAMES
                                     for index in section_indices[name]] + [cap_index]
        if new_indices != expected:
            _fail(f"base_mesh.metadata.arms.{side}.new_vertex_indices disagrees with semantic sections")
        if len(set(new_indices)) != len(new_indices):
            _fail(f"base_mesh.metadata.arms.{side} contains overlapping vertex allocations")
        if any(index < _ROOT_VERTEX_COUNT or index >= base_count for index in new_indices):
            _fail(f"base_mesh.metadata.arms.{side} contains an invalid appended vertex")
        if (set(new_indices) & leg_indices or used & set(new_indices)
                or (excluded_indices and set(new_indices) & excluded_indices)):
            _fail(f"base_mesh.metadata.arms.{side} overwrites another allocation")
        used.update(new_indices)
        result[side] = {
            "J": _vector(row.get("J"), f"base_mesh.metadata.arms.{side}.J"),
            "E": _vector(row.get("E"), f"base_mesh.metadata.arms.{side}.E"),
            "W": _vector(row.get("W"), f"base_mesh.metadata.arms.{side}.W"),
            "source_port": port,
            "collar": collar_indices,
            "sections": section_indices,
            "cap": cap_index,
            "new_vertex_indices": new_indices,
        }
    return result


def _foot_vertex_indices(base_mesh: Mapping[str, Any], base_count: int,
                         rings: dict[str, list[list[int]]],
                         arms: Mapping[str, Any] | None = None,
                         heads: Mapping[str, Any] | None = None,
                         excluded_indices: set[int] | None = None) -> dict[str, list[int]]:
    """Validate explicit foot allocation as the complement of known appendages."""
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    leg_indices = {index for side in _SIDES for ring in rings[side] for index in ring}
    appended = set(range(_ROOT_VERTEX_COUNT, base_count))
    arm_indices = {index for row in (arms or {}).values()
                   for index in row["new_vertex_indices"]}
    head_indices = set((heads or {}).get("new_vertex_indices", ()))
    excluded = set(excluded_indices or ())
    raw_feet = metadata.get("feet")
    if raw_feet is None:
        if leg_indices | arm_indices | head_indices | excluded != appended:
            _fail("base_mesh appended vertices require metadata.feet for non-leg allocations")
        return {side: [] for side in _SIDES}

    feet = _mapping(raw_feet, "base_mesh.metadata.feet")
    if set(feet) != set(_SIDES):
        _fail("base_mesh.metadata.feet must contain exactly left and right")
    result: dict[str, list[int]] = {}
    foot_indices: set[int] = set()
    for side in _SIDES:
        row = _mapping(feet[side], f"base_mesh.metadata.feet.{side}")
        raw_indices = row.get("new_vertex_indices")
        if not isinstance(raw_indices, (list, tuple)) or not raw_indices:
            _fail(f"base_mesh.metadata.feet.{side}.new_vertex_indices must be non-empty")
        checked = [_integer(index, f"base_mesh.metadata.feet.{side}.new_vertex_indices[{slot}]")
                   for slot, index in enumerate(raw_indices)]
        if len(set(checked)) != len(checked):
            _fail(f"base_mesh.metadata.feet.{side}.new_vertex_indices must be disjoint")
        if any(index < _ROOT_VERTEX_COUNT or index >= base_count for index in checked):
            _fail(f"base_mesh.metadata.feet.{side}.new_vertex_indices contains an invalid L0 vertex")
        if set(checked) & (leg_indices | excluded):
            _fail(f"base_mesh.metadata.feet.{side}.new_vertex_indices overwrites a leg allocation")
        if foot_indices & set(checked):
            _fail("base_mesh.metadata.feet left and right allocations must be disjoint")
        result[side] = checked
        foot_indices.update(checked)

    if leg_indices | arm_indices | head_indices | foot_indices | excluded != appended:
        _fail("base_mesh leg and foot allocations must cover every appended L0 vertex exactly once")
    if ((leg_indices & arm_indices) or (foot_indices & arm_indices) or
            (leg_indices & head_indices) or (foot_indices & head_indices) or
            (arm_indices & head_indices) or (excluded & (leg_indices | arm_indices |
                                                         head_indices | foot_indices))):
        _fail("base_mesh leg, foot, arm, and head allocations must be disjoint")
    return result


def _head_vertex_indices(base_mesh: Mapping[str, Any], base_count: int,
                         rings: dict[str, list[list[int]]],
                         arms: Mapping[str, Any],
                         excluded_indices: set[int] | None = None) -> dict[str, Any]:
    """Validate the source-linked head handoff without inferring its pivot."""
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    raw_head = metadata.get("head")
    if raw_head is None:
        return {}
    head = _mapping(raw_head, "base_mesh.metadata.head")
    handoff = _mapping(head.get("binding_handoff"),
                       "base_mesh.metadata.head.binding_handoff")
    if handoff.get("pivot_source") != "stations.neck_collar.C":
        _fail("base_mesh.metadata.head binding pivot must be stations.neck_collar.C")
    pivot = _vector(handoff.get("pivot"),
                    "base_mesh.metadata.head.binding_handoff.pivot")

    def checked_indices(value: Any, where: str, lower: int, upper: int) -> list[int]:
        if not isinstance(value, (list, tuple)) or not value:
            _fail(f"{where} must be a non-empty index list")
        values = [_integer(index, f"{where}[{slot}]")
                  for slot, index in enumerate(value)]
        if len(set(values)) != len(values):
            _fail(f"{where} must contain unique indices")
        if any(index < lower or index >= upper for index in values):
            _fail(f"{where} contains an out-of-range vertex")
        return values

    port = checked_indices(head.get("neck_port_indices"),
                           "base_mesh.metadata.head.neck_port_indices",
                           0, _ROOT_VERTEX_COUNT)
    consumed_port = checked_indices(
        handoff.get("consumed_neck_port_indices"),
        "base_mesh.metadata.head.binding_handoff.consumed_neck_port_indices",
        0, _ROOT_VERTEX_COUNT,
    )
    if consumed_port != port:
        _fail("head binding handoff disagrees with neck_port_indices")

    stations = head.get("stations")
    if not isinstance(stations, (list, tuple)):
        _fail("base_mesh.metadata.head.stations must be a list")
    support_records = [
        _mapping(row, "base_mesh.metadata.head.stations entry")
        for row in stations if isinstance(row, Mapping) and row.get("name") == "neck_support"
    ]
    if len(support_records) != 1:
        _fail("head metadata must contain exactly one neck_support station")
    support = checked_indices(
        support_records[0].get("indices"),
        "base_mesh.metadata.head.stations.neck_support.indices",
        _ROOT_VERTEX_COUNT, base_count,
    )
    handoff_support = checked_indices(
        handoff.get("neck_support_ring_indices"),
        "base_mesh.metadata.head.binding_handoff.neck_support_ring_indices",
        _ROOT_VERTEX_COUNT, base_count,
    )
    if handoff_support != support:
        _fail("head binding handoff disagrees with neck_support station")

    new_indices = checked_indices(
        head.get("new_vertex_indices"),
        "base_mesh.metadata.head.new_vertex_indices",
        _ROOT_VERTEX_COUNT, base_count,
    )
    handoff_new = checked_indices(
        handoff.get("head_new_vertex_indices"),
        "base_mesh.metadata.head.binding_handoff.head_new_vertex_indices",
        _ROOT_VERTEX_COUNT, base_count,
    )
    if handoff_new != new_indices:
        _fail("head binding handoff disagrees with head.new_vertex_indices")
    if not set(support).issubset(new_indices):
        _fail("head neck_support ring must be part of head.new_vertex_indices")

    leg_indices = {index for side in _SIDES for ring in rings[side] for index in ring}
    arm_indices = {index for row in arms.values() for index in row["new_vertex_indices"]}
    head_set = set(new_indices)
    if (head_set & leg_indices or head_set & arm_indices
            or (excluded_indices and head_set & excluded_indices)):
        _fail("head allocation overwrites an existing appendage allocation")
    return {
        "J": pivot,
        "pivot_source": "stations.neck_collar.C",
        "source_port": port,
        "support": support,
        "new_vertex_indices": new_indices,
    }


def _root_edge_graph(base_mesh: Mapping[str, Any],
                     base_quads: list[list[int]],
                     attachments: Mapping[str, Mapping[str, Any]],
                     source_root_quads: list[list[int]] | None = None) -> tuple[list[set[int]], dict[str, Any]]:
    """Build the root graph and verify every semantic port-to-support weld."""
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    root = _mapping(metadata.get("root"), "base_mesh.metadata.root")
    root_count = _integer(root.get("vertex_count"),
                          "base_mesh.metadata.root.vertex_count")
    root_face_count = _integer(root.get("face_count"),
                               "base_mesh.metadata.root.face_count")
    if root_count != _ROOT_VERTEX_COUNT:
        _fail("base_mesh.metadata.root.vertex_count must be 152")
    if root_face_count <= 0 or root_face_count > len(base_quads):
        _fail("base_mesh.metadata.root.face_count is outside the base quad range")

    source_faces = base_quads[:root_face_count] if source_root_quads is None else source_root_quads
    if len(source_faces) != root_face_count:
        _fail("source root face correspondence does not cover the declared root face count")
    graph = [set() for _ in range(root_count)]
    for face_index, face in enumerate(source_faces):
        if any(index < 0 or index >= root_count for index in face):
            _fail(f"root face {face_index} references a non-root vertex")
        for corner, left in enumerate(face):
            right = face[(corner + 1) % 4]
            graph[left].add(right)
            graph[right].add(left)

    all_edges = set()
    for face in base_quads:
        for corner, left in enumerate(face):
            all_edges.add((left, face[(corner + 1) % 4]) if left < face[(corner + 1) % 4]
                          else (face[(corner + 1) % 4], left))
    connections: dict[str, list[list[int]]] = {}
    for name, row in attachments.items():
        port = row["port"]
        support = row["support"]
        pairs = []
        for port_index, support_index in zip(port, support):
            edge = ((port_index, support_index) if port_index < support_index
                    else (support_index, port_index))
            if edge not in all_edges:
                _fail(f"base_mesh {name} lacks a port-to-support connection")
            pairs.append([port_index, support_index])
        connections[name] = pairs
    return graph, {"connections": connections, "root_face_count": root_face_count}


def _graph_distance_neighbourhood(graph: list[set[int]], seeds: set[int], distance: int) -> set[int]:
    current = set(seeds)
    reached = set(seeds)
    for _ in range(distance):
        current = {neighbour for index in current for neighbour in graph[index]} - reached
        reached.update(current)
    return reached


def _root_free_field(graph: list[set[int]], connections: list[list[int]],
                     port: list[int], support: list[int], where: str) -> dict[str, Any]:
    """Solve one D0/D1 free field with an explicit support=1, D2=0 boundary."""
    d0 = set(port)
    d1 = {neighbour for index in d0 for neighbour in graph[index]} - d0
    d2 = {neighbour for index in d1 for neighbour in graph[index]} - d0 - d1
    if not d0 or not d1 or not d2:
        _fail(f"{where} requires non-empty D0, D1, and D2 root regions")
    if any(index < 0 or index >= _ROOT_VERTEX_COUNT for index in d0 | d1 | d2):
        _fail(f"{where} graph region escaped the root")
    free = sorted(d0 | d1)
    seeds = d2
    support_set = set(support)
    if not support_set:
        _fail(f"{where} support ring is empty")
    node_neighbours: dict[int, set[int]] = {index: set(graph[index]) for index in free}
    for port_index, support_index in connections:
        if port_index in node_neighbours:
            node_neighbours[port_index].add(support_index)
    positions = {index: row for row, index in enumerate(free)}
    matrix = np.eye(len(free), dtype=np.float64)
    rhs = np.zeros(len(free), dtype=np.float64)
    for index in free:
        neighbours = node_neighbours[index]
        if not neighbours:
            _fail(f"{where} has an unassigned free graph component")
        row = positions[index]
        for neighbour in neighbours:
            if neighbour in positions:
                matrix[row, positions[neighbour]] -= 1.0 / len(neighbours)
            elif neighbour in support_set:
                rhs[row] += 1.0 / len(neighbours)
            elif neighbour in seeds:
                # D2 is the zero boundary. Shared D2 nodes are allowed.
                pass
            else:
                _fail(f"{where} free graph has an unassigned neighbour")
    try:
        values = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"{where} free graph is not anchored") from exc
    if not np.all(np.isfinite(values)):
        _fail(f"{where} free graph produced non-finite influence")
    field = {index: float(value) for index, value in zip(free, values)}
    return {
        "field": field,
        "D0": sorted(d0),
        "D1": sorted(d1),
        "D2": sorted(d2),
        "D0_count": len(d0),
        "D1_count": len(d1),
        "free_count": len(free),
        "seed_count": len(d2),
        "support_count": len(support_set),
        "support_anchor_value": 1.0,
        "collar_anchor_value": 1.0,
        "D2_anchor_value": 0.0,
        "values": {str(index): field[index] for index in free},
    }


def _arm_root_influence(base_mesh: Mapping[str, Any],
                        base_quads: list[list[int]],
                        arms: Mapping[str, Any],
                        rings: dict[str, list[list[int]]],
                        source_root_quads: list[list[int]] | None = None) -> dict[str, Any]:
    """Compute the arm scalar field on root D0/D1 using source topology."""
    attachments = {
        side: {"port": arms[side]["source_port"],
               "support": arms[side]["collar"]}
        for side in _SIDES
    }
    graph, graph_metadata = _root_edge_graph(
        base_mesh, base_quads, attachments, source_root_quads,
    )
    metadata = _mapping(base_mesh.get("metadata"), "base_mesh.metadata")
    chains = _mapping(metadata.get("chains"), "base_mesh.metadata.chains")
    per_side: dict[str, Any] = {}
    all_free: dict[str, set[int]] = {}
    all_seed: dict[str, set[int]] = {}

    for side in _SIDES:
        record = _root_free_field(
            graph, graph_metadata["connections"][side],
            arms[side]["source_port"], arms[side]["collar"],
            f"base_mesh arm {side}",
        )
        per_side[side] = record
        all_free[side] = set(record["D0"]) | set(record["D1"])
        all_seed[side] = set(record["D2"])

    left_free, right_free = all_free["left"], all_free["right"]
    if left_free & right_free:
        _fail("bilateral arm D0/D1 regions overlap")
    if left_free & all_seed["right"] or right_free & all_seed["left"]:
        _fail("arm free region overlaps the opposite arm seed region")

    thigh_neighbourhood: set[int] = set()
    for side in _SIDES:
        chain = _mapping(chains.get(side), f"base_mesh.metadata.chains.{side}")
        root_exit = chain.get("root_exit")
        if not isinstance(root_exit, (list, tuple)) or not root_exit:
            _fail(f"base_mesh.metadata.chains.{side}.root_exit is required for arm separation")
        thigh = {_integer(index, f"base_mesh.metadata.chains.{side}.root_exit[{i}]")
                 for i, index in enumerate(root_exit)}
        if any(index < 0 or index >= _ROOT_VERTEX_COUNT for index in thigh):
            _fail(f"base_mesh.metadata.chains.{side}.root_exit must reference root vertices")
        thigh_neighbourhood.update(_graph_distance_neighbourhood(graph, thigh, 2))
    if (left_free | right_free) & thigh_neighbourhood:
        _fail("arm D0/D1 region overlaps a thigh-port neighbourhood")

    fields: dict[str, dict[int, float]] = {
        side: per_side[side].pop("field") for side in _SIDES
    }
    for side in _SIDES:
        per_side[side]["collar_count"] = len(arms[side]["collar"])
    return {
        "fields": fields,
        "per_side": per_side,
        "bilateral_shared_D2": sorted(all_seed["left"] & all_seed["right"]),
        "thigh_neighbourhood_count": len(thigh_neighbourhood),
        "connections": graph_metadata["connections"],
    }


def _head_root_influence(base_mesh: Mapping[str, Any],
                         base_quads: list[list[int]],
                         head: Mapping[str, Any],
                         arm_influence: Mapping[str, Any] | None,
                         source_root_quads: list[list[int]] | None = None) -> dict[str, Any]:
    """Compute the head D0/D1 field and make shoulder overlap explicit."""
    graph, graph_metadata = _root_edge_graph(
        base_mesh, base_quads,
        {"head": {"port": head["source_port"], "support": head["support"]}},
        source_root_quads,
    )
    record = _root_free_field(
        graph, graph_metadata["connections"]["head"],
        head["source_port"], head["support"], "base_mesh head",
    )
    shoulder_nodes = set()
    if arm_influence is not None:
        shoulder_nodes = {
            index for field in arm_influence["fields"].values() for index in field
        }
    overlap = sorted((set(record["D0"]) | set(record["D1"])) & shoulder_nodes)
    record["shoulder_overlap"] = overlap
    if overlap:
        _fail(f"base_mesh head D0/D1 overlaps shoulder modified nodes: {overlap}")
    field = record.pop("field")
    return {
        "field": field,
        "per_root": record,
        "connections": graph_metadata["connections"],
    }


def _leg_inputs(value: Any) -> tuple[dict[str, dict[str, list[float]]],
                                  dict[str, float], dict[str, float]]:
    raw = _mapping(value, "leg_inputs")
    if set(raw) != set(_SIDES):
        _fail("leg_inputs must contain exactly left and right sides")
    result: dict[str, dict[str, list[float]]] = {}
    supports: dict[str, float] = {}
    factors: dict[str, float] = {}
    for side in _SIDES:
        row = _mapping(raw[side], f"leg_inputs.{side}")
        missing = [name for name in ("J", "T", "K", "A", "mid_thigh_factor",
                                     "support_fraction") if name not in row]
        if missing:
            _fail(f"leg_inputs.{side} is missing {', '.join(missing)}")
        points = {name: _vector(row[name], f"leg_inputs.{side}.{name}")
                  for name in ("J", "T", "K", "A")}
        j, t, k, a = (np.asarray(points[name], dtype=np.float64)
                      for name in ("J", "T", "K", "A"))
        if np.linalg.norm(j - k) <= _TOLERANCE:
            _fail(f"leg_inputs.{side}.J and K must be distinct")
        if np.linalg.norm(t - k) <= _TOLERANCE:
            _fail(f"leg_inputs.{side}.T and K must be distinct")
        if np.linalg.norm(k - a) <= _TOLERANCE:
            _fail(f"leg_inputs.{side}.K and A must be distinct")
        factor = _number(row["mid_thigh_factor"],
                         f"leg_inputs.{side}.mid_thigh_factor")
        support = _number(row["support_fraction"],
                          f"leg_inputs.{side}.support_fraction")
        if factor < 0.0:
            _fail(f"leg_inputs.{side}.mid_thigh_factor must be non-negative")
        if not 0.0 < support < 1.0:
            _fail(f"leg_inputs.{side}.support_fraction must be strictly between zero and one")
        result[side] = points
        factors[side] = factor
        supports[side] = support
    return result, supports, factors


def _frame(origin: list[float], distal: list[float], where: str) -> dict[str, Any]:
    origin_array = np.asarray(origin, dtype=np.float64)
    distal_array = np.asarray(distal, dtype=np.float64)
    y = origin_array - distal_array
    y_norm = float(np.linalg.norm(y))
    if not math.isfinite(y_norm) or y_norm <= _TOLERANCE:
        _fail(f"{where} frame has a degenerate Y axis")
    y /= y_norm
    x = np.asarray([1.0, 0.0, 0.0], dtype=np.float64)
    x -= np.dot(x, y) * y
    x_norm = float(np.linalg.norm(x))
    if not math.isfinite(x_norm) or x_norm <= _TOLERANCE:
        _fail(f"{where} frame has no usable +X projection")
    x /= x_norm
    z = np.cross(x, y)
    z_norm = float(np.linalg.norm(z))
    if not math.isfinite(z_norm) or z_norm <= _TOLERANCE:
        _fail(f"{where} frame has a degenerate Z axis")
    z /= z_norm
    rotation = np.column_stack((x, y, z))
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = origin_array
    return {"rotation": rotation.tolist(), "rest_global": matrix.tolist()}


def _arm_frame(origin: list[float], distal: list[float], where: str) -> dict[str, Any]:
    """Build the arm pivot frame from a near-horizontal source bone."""
    origin_array = np.asarray(origin, dtype=np.float64)
    distal_array = np.asarray(distal, dtype=np.float64)
    y = origin_array - distal_array
    y_norm = float(np.linalg.norm(y))
    if not math.isfinite(y_norm) or y_norm <= _TOLERANCE:
        _fail(f"{where} frame has a degenerate Y axis")
    y /= y_norm
    global_up = np.asarray([0.0, 1.0, 0.0], dtype=np.float64)
    x = global_up - np.dot(global_up, y) * y
    x_norm = float(np.linalg.norm(x))
    if not math.isfinite(x_norm) or x_norm <= _TOLERANCE:
        _fail(f"{where} frame has no usable global +Y projection")
    x /= x_norm
    z = np.cross(x, y)
    z_norm = float(np.linalg.norm(z))
    if not math.isfinite(z_norm) or z_norm <= _TOLERANCE:
        _fail(f"{where} frame has a degenerate Z axis")
    z /= z_norm
    if float(np.dot(z, [0.0, 0.0, 1.0])) < 0.0:
        x, z = -x, -z
    rotation = np.column_stack((x, y, z))
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = origin_array
    return {
        "rotation": rotation.tolist(),
        "rest_global": matrix.tolist(),
        "frame_rule": "Y=normalize(origin-distal); X=projected global +Y; Z=X cross Y; flip X/Z toward +Z",
    }


def _matrix(value: Any, where: str) -> np.ndarray:
    raw = np.asarray(value, dtype=np.float64)
    if raw.shape != (4, 4) or not np.all(np.isfinite(raw)):
        _fail(f"{where} must be a finite 4x4 matrix")
    if not np.allclose(raw[3], [0.0, 0.0, 0.0, 1.0], atol=_FRAME_TOLERANCE, rtol=0.0):
        _fail(f"{where} must be an affine rigid matrix")
    rotation = raw[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3),
                       atol=_FRAME_TOLERANCE, rtol=0.0):
        _fail(f"{where} rotation must be orthonormal")
    determinant = float(np.linalg.det(rotation))
    if not math.isfinite(determinant) or abs(determinant - 1.0) > _FRAME_TOLERANCE:
        _fail(f"{where} rotation must have positive unit determinant")
    return raw


def _inverse_rigid(value: np.ndarray, where: str) -> np.ndarray:
    # _matrix has already established the rigid affine contract, but use the
    # requested inverse operation so the stored rest-local relation is clear.
    try:
        inverse = np.linalg.inv(value)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"{where} is singular") from exc
    if not np.all(np.isfinite(inverse)):
        _fail(f"{where} inverse is non-finite")
    return inverse


def _matrix_rotation_x(angle_degrees: float) -> np.ndarray:
    radians = math.radians(angle_degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    return np.array([[1.0, 0.0, 0.0, 0.0],
                     [0.0, cosine, -sine, 0.0],
                     [0.0, sine, cosine, 0.0],
                     [0.0, 0.0, 0.0, 1.0]], dtype=np.float64)


def _matrix_rotation_y(angle_degrees: float) -> np.ndarray:
    radians = math.radians(angle_degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    return np.array([[cosine, 0.0, sine, 0.0],
                     [0.0, 1.0, 0.0, 0.0],
                     [-sine, 0.0, cosine, 0.0],
                     [0.0, 0.0, 0.0, 1.0]], dtype=np.float64)


def _matrix_rotation_z(angle_degrees: float) -> np.ndarray:
    radians = math.radians(angle_degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    return np.array([[cosine, -sine, 0.0, 0.0],
                     [sine, cosine, 0.0, 0.0],
                     [0.0, 0.0, 1.0, 0.0],
                     [0.0, 0.0, 0.0, 1.0]], dtype=np.float64)


def _angles(value: Any) -> dict[str, dict[str, float]]:
    raw = _mapping(value, "angles_degrees")
    if not set(_SIDES).issubset(raw) or set(raw).difference(set(_SIDES) | {"head"}):
        _fail("angles_degrees must contain left and right, with optional head angles")
    result: dict[str, dict[str, float]] = {}
    for side in _SIDES:
        row = _mapping(raw[side], f"angles_degrees.{side}")
        allowed = {"hip", "knee", "ankle", "shoulder_raise",
                   "shoulder_forward", "elbow"}
        if not {"hip", "knee"}.issubset(row) or set(row).difference(allowed):
            _fail(f"angles_degrees.{side} must contain hip and knee, with optional arm angles")
        parsed = {name: _number(row[name], f"angles_degrees.{side}.{name}")
                  for name in ("hip", "knee")}
        if "ankle" in row:
            ankle = _number(row["ankle"], f"angles_degrees.{side}.ankle")
            if ankle != 0.0:
                _fail("ankle angle is staging-only and must be zero")
        parsed["ankle"] = 0.0
        for name in ("shoulder_raise", "shoulder_forward", "elbow"):
            parsed[name] = _number(row.get(name, 0.0),
                                   f"angles_degrees.{side}.{name}")
        result[side] = parsed
    head = raw.get("head", {})
    head_row = _mapping(head, "angles_degrees.head")
    if set(head_row).difference({"yaw", "nod"}):
        _fail("angles_degrees.head may contain only yaw and nod")
    result["head"] = {
        name: _number(head_row.get(name, 0.0), f"angles_degrees.head.{name}")
        for name in ("yaw", "nod")
    }
    return result


def _point(matrix: np.ndarray, point: list[float], where: str) -> list[float]:
    result = matrix @ np.r_[np.asarray(point, dtype=np.float64), 1.0]
    if not np.all(np.isfinite(result)):
        _fail(f"{where} is non-finite")
    return result[:3].tolist()


def _frame_matrices(frame: Mapping[str, Any], side: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    thigh = _mapping(frame.get("thigh"), f"binding.rest_frames.{side}.thigh")
    knee = _mapping(frame.get("knee"), f"binding.rest_frames.{side}.knee")
    thigh_value = thigh.get("rest_global", thigh.get("rest_matrix"))
    knee_value = knee.get("rest_global", knee.get("rest_matrix"))
    thigh_rest = _matrix(thigh_value, f"binding.rest_frames.{side}.thigh.rest_global")
    knee_rest = _matrix(knee_value, f"binding.rest_frames.{side}.knee.rest_global")
    knee_local = _matrix(knee.get("rest_local"),
                         f"binding.rest_frames.{side}.knee.rest_local")
    expected_local = _inverse_rigid(thigh_rest, f"binding.rest_frames.{side}.thigh.rest_global") @ knee_rest
    if not np.allclose(knee_local, expected_local, atol=_FRAME_TOLERANCE, rtol=0.0):
        _fail(f"binding.rest_frames.{side}.knee.rest_local does not match inverse(thigh)*knee")
    return thigh_rest, knee_rest, knee_local


def _joint_transforms(binding: Mapping[str, Any], angles_degrees: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    angles = _angles(angles_degrees)
    joint_order = tuple(binding.get("joint_order", ()))
    valid_layouts = {
        _LEG_JOINT_ORDER: (False, False),
        _ARM_JOINT_ORDER: (True, False),
        _HEAD_JOINT_ORDER: (False, True),
        _ARM_HEAD_JOINT_ORDER: (True, True),
    }
    if joint_order not in valid_layouts:
        _fail("binding.joint_order must be a five-, six-, nine-, or ten-joint layout")
    has_arms, has_head = valid_layouts[joint_order]
    if not has_arms and any(angles[side][joint] != 0.0
                            for side in _SIDES
                            for joint in ("shoulder_raise", "shoulder_forward", "elbow")):
        _fail("arm pose angles require a nine- or ten-joint arm binding")
    if not has_head and any(angles["head"][joint] != 0.0
                            for joint in ("yaw", "nod")):
        _fail("head pose angles require a six- or ten-joint head binding")
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    expected_frames = set(_SIDES) | ({"head"} if has_head else set())
    if set(frames) != expected_frames:
        _fail("binding.rest_frames does not match the selected joint layout")
    result: dict[str, dict[str, Any]] = {}
    identity = np.eye(4, dtype=np.float64)
    result["pelvis"] = {
        "rest_global": identity.tolist(),
        "posed_global": identity.tolist(),
        "skin_matrix": identity.tolist(),
        "angle_degrees": {"hip": 0.0, "knee": 0.0, "ankle": 0.0},
    }
    for side in _SIDES:
        frame = _mapping(frames[side], f"binding.rest_frames.{side}")
        thigh_rest, knee_rest, knee_local = _frame_matrices(frame, side)
        thigh_inverse = _inverse_rigid(thigh_rest,
                                       f"binding.rest_frames.{side}.thigh.rest_global")
        hip_rotation = _matrix_rotation_x(-angles[side]["hip"])
        knee_rotation = _matrix_rotation_x(angles[side]["knee"])
        thigh_pose = thigh_rest @ hip_rotation
        knee_pose = thigh_pose @ thigh_inverse @ knee_rest @ knee_rotation
        thigh_skin = thigh_pose @ thigh_inverse
        knee_skin = knee_pose @ _inverse_rigid(
            knee_rest, f"binding.rest_frames.{side}.knee.rest_global"
        )
        for name, matrix in (("thigh posed", thigh_pose), ("knee posed", knee_pose),
                             ("thigh skin", thigh_skin), ("knee skin", knee_skin)):
            if not np.all(np.isfinite(matrix)):
                _fail(f"{side} {name} matrix is non-finite")

        points = {}
        for name in ("J", "T", "K", "A"):
            points[name] = _vector(frame.get(name),
                                   f"binding.rest_frames.{side}.{name}")
        rest_knee_from_parent = _point(np.eye(4), points["K"],
                                       f"{side} rest K")
        posed_j = _point(thigh_skin, points["J"], f"{side} posed J")
        posed_t = _point(thigh_skin, points["T"], f"{side} posed T")
        posed_k_parent = _point(thigh_skin, points["K"], f"{side} posed K parent")
        posed_k_knee = _point(knee_skin, points["K"], f"{side} posed K knee")
        if not np.allclose(posed_k_parent, posed_k_knee,
                           atol=_FRAME_TOLERANCE, rtol=0.0):
            _fail(f"{side} posed K differs between parent hip and knee")
        posed_a = _point(knee_skin, points["A"], f"{side} posed A")
        rest_points = {name: points[name] for name in ("J", "T", "K", "A")}
        posed_points = {"J": posed_j, "T": posed_t, "K": posed_k_parent, "A": posed_a}
        result[side] = {
            "J": posed_j,
            "T": posed_t,
            "K": posed_k_parent,
            "A": posed_a,
            "rest_points": rest_points,
            "posed_points": posed_points,
            "rest_J": rest_points["J"],
            "rest_T": rest_points["T"],
            "rest_K": rest_points["K"],
            "rest_A": rest_points["A"],
            "posed_J": posed_points["J"],
            "posed_T": posed_points["T"],
            "posed_K": posed_points["K"],
            "posed_A": posed_points["A"],
            "posed_K_from_parent": posed_k_parent,
            "posed_K_from_knee": posed_k_knee,
            "thigh": {
                "rest_global": thigh_rest.tolist(),
                "posed_global": thigh_pose.tolist(),
                "skin_matrix": thigh_skin.tolist(),
            },
            "knee": {
                "rest_global": knee_rest.tolist(),
                "rest_local": knee_local.tolist(),
                "posed_global": knee_pose.tolist(),
                "skin_matrix": knee_skin.tolist(),
            },
            # Short aliases keep the diagnostic convenient while the nested
            # records above make the hierarchy and matrix roles explicit.
            "rest_matrix": thigh_rest.tolist(),
            "posed_matrix": thigh_pose.tolist(),
            "skin_matrix": thigh_skin.tolist(),
            "knee_rest_matrix": knee_rest.tolist(),
            "knee_rest_local_matrix": knee_local.tolist(),
            "knee_posed_matrix": knee_pose.tolist(),
            "knee_skin_matrix": knee_skin.tolist(),
            "angle_degrees": copy.deepcopy(angles[side]),
            "rest_K_from_parent": rest_knee_from_parent,
        }
        if has_arms:
            frame = _mapping(frames[side], f"binding.rest_frames.{side}")
            shoulder = _mapping(frame.get("shoulder"),
                                f"binding.rest_frames.{side}.shoulder")
            elbow = _mapping(frame.get("elbow"),
                             f"binding.rest_frames.{side}.elbow")
            shoulder_rest = _matrix(
                shoulder.get("rest_global", shoulder.get("rest_matrix")),
                f"binding.rest_frames.{side}.shoulder.rest_global")
            elbow_rest = _matrix(
                elbow.get("rest_global", elbow.get("rest_matrix")),
                f"binding.rest_frames.{side}.elbow.rest_global")
            expected_elbow_local = _inverse_rigid(
                shoulder_rest, f"binding.rest_frames.{side}.shoulder.rest_global") @ elbow_rest
            elbow_local = _matrix(
                elbow.get("rest_local"),
                f"binding.rest_frames.{side}.elbow.rest_local")
            if not np.allclose(elbow_local, expected_elbow_local,
                               atol=_FRAME_TOLERANCE, rtol=0.0):
                _fail(f"binding.rest_frames.{side}.elbow.rest_local does not match shoulder hierarchy")
            arm_points = _mapping(frame.get("arm_source_points"),
                                  f"binding.rest_frames.{side}.arm_source_points")
            arm_J = _vector(arm_points.get("J"),
                            f"binding.rest_frames.{side}.arm_source_points.J")
            arm_E = _vector(arm_points.get("E"),
                            f"binding.rest_frames.{side}.arm_source_points.E")
            arm_W = _vector(arm_points.get("W"),
                            f"binding.rest_frames.{side}.arm_source_points.W")
            side_sign = -1.0 if side == "left" else 1.0
            shoulder_rotation = (
                _matrix_rotation_z(side_sign * angles[side]["shoulder_raise"]) @
                _matrix_rotation_x(-angles[side]["shoulder_forward"])
            )
            elbow_rotation = _matrix_rotation_x(-angles[side]["elbow"])
            shoulder_pose = shoulder_rest @ shoulder_rotation
            elbow_pose = (
                shoulder_pose @
                _inverse_rigid(shoulder_rest,
                               f"binding.rest_frames.{side}.shoulder.rest_global") @
                elbow_rest @ elbow_rotation
            )
            shoulder_skin = shoulder_pose @ _inverse_rigid(
                shoulder_rest, f"binding.rest_frames.{side}.shoulder.rest_global")
            elbow_skin = elbow_pose @ _inverse_rigid(
                elbow_rest, f"binding.rest_frames.{side}.elbow.rest_global")
            posed_arm_J = _point(shoulder_skin, arm_J, f"{side} posed arm J")
            posed_arm_E_parent = _point(shoulder_skin, arm_E,
                                        f"{side} posed arm E parent")
            posed_arm_E_elbow = _point(elbow_skin, arm_E,
                                       f"{side} posed arm E elbow")
            if not np.allclose(posed_arm_E_parent, posed_arm_E_elbow,
                               atol=_FRAME_TOLERANCE, rtol=0.0):
                _fail(f"{side} posed arm E differs between shoulder and elbow")
            posed_arm_W = _point(elbow_skin, arm_W, f"{side} posed arm W")
            result[side].update({
                "arm_rest_points": {"J": arm_J, "E": arm_E, "W": arm_W},
                "arm_posed_points": {
                    "J": posed_arm_J, "E": posed_arm_E_parent, "W": posed_arm_W,
                },
                "rest_arm_J": arm_J,
                "rest_arm_E": arm_E,
                "rest_arm_W": arm_W,
                "posed_arm_J": posed_arm_J,
                "posed_arm_E": posed_arm_E_parent,
                "posed_arm_W": posed_arm_W,
                "posed_arm_E_from_shoulder": posed_arm_E_parent,
                "posed_arm_E_from_elbow": posed_arm_E_elbow,
                "shoulder": {
                    "rest_global": shoulder_rest.tolist(),
                    "posed_global": shoulder_pose.tolist(),
                    "skin_matrix": shoulder_skin.tolist(),
                },
                "elbow": {
                    "rest_global": elbow_rest.tolist(),
                    "rest_local": elbow_local.tolist(),
                    "posed_global": elbow_pose.tolist(),
                    "skin_matrix": elbow_skin.tolist(),
                },
                "arm_angle_degrees": {
                    "shoulder_raise": angles[side]["shoulder_raise"],
                    "shoulder_forward": angles[side]["shoulder_forward"],
                    "elbow": angles[side]["elbow"],
                },
            })
    if has_head:
        head_frame = _mapping(frames.get("head"), "binding.rest_frames.head")
        head_rest = _matrix(
            head_frame.get("rest_global", head_frame.get("rest_matrix")),
            "binding.rest_frames.head.rest_global",
        )
        head_J = _vector(head_frame.get("J"), "binding.rest_frames.head.J")
        if not np.allclose(head_rest[:3, 3], head_J,
                           atol=_FRAME_TOLERANCE, rtol=0.0):
            _fail("binding.rest_frames.head pivot does not match its rest frame")
        head_rotation = (
            _matrix_rotation_y(angles["head"]["yaw"]) @
            _matrix_rotation_x(angles["head"]["nod"])
        )
        head_pose = head_rest @ head_rotation
        head_skin = head_pose @ _inverse_rigid(
            head_rest, "binding.rest_frames.head.rest_global")
        forward_rest = np.asarray(head_J, dtype=np.float64) + [0.0, 0.0, 1.0]
        posed_head_J = _point(head_skin, head_J, "posed head J")
        posed_forward = _point(head_skin, forward_rest.tolist(),
                                "posed head forward endpoint")
        result["head"] = {
            "rest_J": head_J,
            "posed_J": posed_head_J,
            "rest_forward_endpoint": forward_rest.tolist(),
            "posed_forward_endpoint": posed_forward,
            "rest_forward_direction": [0.0, 0.0, 1.0],
            "posed_forward_direction": (np.asarray(posed_forward) -
                                         np.asarray(posed_head_J)).tolist(),
            "rest_global": head_rest.tolist(),
            "posed_global": head_pose.tolist(),
            "skin_matrix": head_skin.tolist(),
            "angle_degrees": copy.deepcopy(angles["head"]),
            "pose_rotation_order": "Ry(yaw) @ Rx(nod)",
            "pivot_source": head_frame.get("pivot_source"),
        }
    return result


def _rest_stencils(rest_mesh: Mapping[str, Any], base_count: int,
                   rest_count: int) -> list[list[tuple[int, float]]]:
    raw = rest_mesh.get("base_stencils")
    if not isinstance(raw, (list, tuple)) or len(raw) != rest_count:
        _fail("rest_mesh.base_stencils must have one stencil per L2 vertex")
    result: list[list[tuple[int, float]]] = []
    for vertex_index, stencil in enumerate(raw):
        if not isinstance(stencil, (list, tuple)) or not stencil:
            _fail(f"rest_mesh.base_stencils[{vertex_index}] must be non-empty")
        row: list[tuple[int, float]] = []
        total = 0.0
        for term_index, term in enumerate(stencil):
            if not isinstance(term, (list, tuple)) or len(term) != 2:
                _fail(f"rest_mesh.base_stencils[{vertex_index}][{term_index}] must be [index, coefficient]")
            base_index = _integer(term[0],
                                  f"rest_mesh.base_stencils[{vertex_index}][{term_index}][0]")
            if base_index < 0 or base_index >= base_count:
                _fail(f"rest_mesh.base_stencils[{vertex_index}] contains an out-of-range index")
            coefficient = _number(term[1],
                                  f"rest_mesh.base_stencils[{vertex_index}][{term_index}][1]")
            if coefficient < -_TOLERANCE:
                _fail(f"rest_mesh.base_stencils[{vertex_index}] contains a negative coefficient")
            row.append((base_index, coefficient))
            total += coefficient
        if abs(total - 1.0) > _TOLERANCE:
            _fail(f"rest_mesh.base_stencils[{vertex_index}] does not partition unity")
        result.append(row)
    return result


def _propagate_weights(stencils: list[list[tuple[int, float]]],
                       base_weights: np.ndarray) -> np.ndarray:
    evaluated = np.zeros((len(stencils), base_weights.shape[1]), dtype=np.float64)
    for vertex_index, stencil in enumerate(stencils):
        for base_index, coefficient in stencil:
            evaluated[vertex_index] += coefficient * base_weights[base_index]
    _check_weight_bounds(evaluated, "evaluated_weights")
    return evaluated


def _apply_station_weights(base_weights: np.ndarray,
                           rings: dict[str, list[list[int]]]) -> None:
    for side, thigh_column, shank_column in (
        ("left", 1, 2), ("right", 3, 4)
    ):
        for station_index, ring in enumerate(rings[side]):
            shank = _STATION_SHANK_WEIGHTS[station_index]
            thigh = 1.0 - shank
            for vertex_index in ring:
                base_weights[vertex_index, thigh_column] = thigh
                base_weights[vertex_index, shank_column] = shank


def _apply_foot_weights(base_weights: np.ndarray,
                        feet: dict[str, list[int]]) -> None:
    for side, shank_column in (("left", 2), ("right", 4)):
        for vertex_index in feet[side]:
            if np.any(base_weights[vertex_index] != 0.0):
                _fail(f"base_mesh.metadata.feet.{side} overwrites an existing base allocation")
            base_weights[vertex_index, shank_column] = 1.0


def _arm_appendage_blends(base_quads: list[list[int]],
                          arms: Mapping[str, Any]) -> dict[str, dict[int, float]]:
    """Solve the separate arm elbow blend with semantic section anchors."""
    result: dict[str, dict[int, float]] = {}
    for side in _SIDES:
        row = arms[side]
        sections = row["sections"]
        zero = set(row["collar"]) | set(sections["upper_belly"]) | set(sections["pre_elbow"])
        free = set(sections["elbow"])
        one = (set(sections["post_elbow"]) | set(sections["forearm_belly"]) |
               set(sections["pre_wrist"]) | set(sections["wrist"]) |
               set(sections["palm"]) | set(sections["knuckle"]) |
               set(sections["terminal"]) | {row["cap"]})
        if not zero or not free or not one or zero & free or zero & one or free & one:
            _fail(f"base_mesh arm {side} has overlapping elbow blend regions")
        graph: dict[int, set[int]] = {index: set() for index in zero | free | one}
        for face in base_quads:
            for corner, left in enumerate(face):
                right = face[(corner + 1) % 4]
                if left in graph and right in graph:
                    graph[left].add(right)
                    graph[right].add(left)
        free_sorted = sorted(free)
        positions = {index: row_index for row_index, index in enumerate(free_sorted)}
        matrix = np.eye(len(free_sorted), dtype=np.float64)
        rhs = np.zeros(len(free_sorted), dtype=np.float64)
        for index in free_sorted:
            neighbours = graph[index]
            if not neighbours or not (neighbours & (zero | one)):
                _fail(f"base_mesh arm {side} elbow blend is not anchored")
            row_index = positions[index]
            for neighbour in neighbours:
                if neighbour in positions:
                    matrix[row_index, positions[neighbour]] -= 1.0 / len(neighbours)
                elif neighbour in one:
                    rhs[row_index] += 1.0 / len(neighbours)
        try:
            values = np.linalg.solve(matrix, rhs)
        except np.linalg.LinAlgError as exc:
            raise ValueError(f"base_mesh arm {side} elbow blend is singular") from exc
        if not np.all(np.isfinite(values)):
            _fail(f"base_mesh arm {side} elbow blend is non-finite")
        result[side] = {index: 0.0 for index in zero}
        result[side].update({index: float(value) for index, value in zip(free_sorted, values)})
        result[side].update({index: 1.0 for index in one})
    return result


def _apply_arm_weights(base_weights: np.ndarray,
                       arms: Mapping[str, Any],
                       arm_blends: Mapping[str, Mapping[int, float]],
                       influence: Mapping[str, Any]) -> None:
    for side, upper_column, fore_column in (
        ("left", 5, 6), ("right", 7, 8)
    ):
        for vertex_index, blend in arm_blends[side].items():
            if np.any(base_weights[vertex_index] != 0.0):
                _fail(f"base_mesh arm {side} overwrites an existing base allocation")
            if blend < -_TOLERANCE or blend > 1.0 + _TOLERANCE:
                _fail(f"base_mesh arm {side} elbow blend is outside [0, 1]")
            base_weights[vertex_index, upper_column] = 1.0 - blend
            base_weights[vertex_index, fore_column] = blend
    for side, upper_column in (("left", 5), ("right", 7)):
        for vertex_index, value in influence["fields"][side].items():
            if value < -_TOLERANCE or value > 1.0 + _TOLERANCE:
                _fail(f"base_mesh arm {side} shoulder influence is outside [0, 1]")
            old = np.array(base_weights[vertex_index, :5], copy=True)
            if np.any(base_weights[vertex_index, 5:] != 0.0):
                _fail(f"base_mesh arm {side} root influence overwrites an arm allocation")
            base_weights[vertex_index, :5] = old * (1.0 - value)
            base_weights[vertex_index, upper_column] = value


def _apply_head_weights(base_weights: np.ndarray,
                        head: Mapping[str, Any],
                        influence: Mapping[str, Any],
                        neck_column: int) -> None:
    """Apply the head one-hot appendage and its root D0/D1 transition field."""
    for vertex_index in head["new_vertex_indices"]:
        if np.any(base_weights[vertex_index] != 0.0):
            _fail("base_mesh head overwrites an existing base allocation")
        base_weights[vertex_index, neck_column] = 1.0
    for vertex_index, value in influence["field"].items():
        if value < -_TOLERANCE or value > 1.0 + _TOLERANCE:
            _fail("base_mesh head neck influence is outside [0, 1]")
        if base_weights[vertex_index, neck_column] != 0.0:
            _fail("base_mesh head root influence overwrites the neck allocation")
        base_weights[vertex_index] *= 1.0 - value
        base_weights[vertex_index, neck_column] = value


def _apply_tail_weights(base_weights: np.ndarray,
                        tail: Mapping[str, Any]) -> dict[str, Any]:
    """Blend validated original-host support into the existing pelvis joint."""
    pelvis = np.zeros(base_weights.shape[1], dtype=np.float64)
    pelvis[0] = 1.0
    applied: dict[str, Any] = {}
    collar_strength = float(tail["collar_blend_strength"])
    for ring, fraction in zip(tail["rings"], tail["station_fractions"]):
        pelvis_fraction = collar_strength + (1.0 - collar_strength) * float(fraction)
        support_fraction = 1.0 - pelvis_fraction
        for vertex_index in ring:
            if np.any(base_weights[vertex_index] != 0.0):
                _fail(f"tail vertex {vertex_index} overwrites an existing allocation")
            host_indices, convex = tail["supports"][vertex_index]
            host_support = np.zeros(base_weights.shape[1], dtype=np.float64)
            for host_index, coefficient in zip(host_indices, convex):
                host_support += coefficient * base_weights[host_index]
            row = support_fraction * host_support + pelvis_fraction * pelvis
            _check_weight_bounds(row.reshape(1, -1), f"tail base weight {vertex_index}")
            base_weights[vertex_index] = row
            applied[str(vertex_index)] = {
                "ring_fraction": float(fraction),
                "pelvis_fraction": pelvis_fraction,
                "host_support_fraction": support_fraction,
                "host_vertex_indices": list(host_indices),
                "convex_weights": list(convex),
            }
    return {
        "collar_blend_strength": collar_strength,
        "distal_joint": "pelvis",
        "vertices": applied,
        "no_tail_joint": True,
    }


def _frame_records(legs: dict[str, dict[str, list[float]]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        points = legs[side]
        thigh = _frame(points["J"], points["K"], f"{side} thigh")
        knee = _frame(points["K"], points["A"], f"{side} knee")
        thigh_rest = _matrix(thigh["rest_global"], f"{side} thigh rest frame")
        knee_rest = _matrix(knee["rest_global"], f"{side} knee rest frame")
        knee_local = _inverse_rigid(thigh_rest, f"{side} thigh rest frame") @ knee_rest
        result[side] = {
            **copy.deepcopy(points),
            "thigh": {
                "rotation": thigh["rotation"],
                "rest_global": thigh_rest.tolist(),
                "rest_matrix": thigh_rest.tolist(),
            },
            "knee": {
                "rotation": knee["rotation"],
                "rest_global": knee_rest.tolist(),
                "rest_matrix": knee_rest.tolist(),
                "rest_local": knee_local.tolist(),
            },
            "rest_matrix": thigh_rest.tolist(),
            "knee_rest_matrix": knee_rest.tolist(),
            "knee_rest_local_matrix": knee_local.tolist(),
            "T_local": (_inverse_rigid(thigh_rest, f"{side} thigh rest frame") @
                        np.r_[np.asarray(points["T"]), 1.0]).tolist()[:3],
            "K_local": (_inverse_rigid(thigh_rest, f"{side} thigh rest frame") @
                        np.r_[np.asarray(points["K"]), 1.0]).tolist()[:3],
            "A_local_knee": (_inverse_rigid(knee_rest, f"{side} knee rest frame") @
                             np.r_[np.asarray(points["A"]), 1.0]).tolist()[:3],
        }
    return result


def _head_frame_record(frames: Mapping[str, Any], head: Mapping[str, Any]) -> dict[str, Any]:
    """Record a world-aligned neck frame at the source-owned head pivot."""
    result = copy.deepcopy(dict(frames))
    J = _vector(head["J"], "base_mesh.metadata.head.binding_handoff.pivot")
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, 3] = np.asarray(J, dtype=np.float64)
    result["head"] = {
        "J": J,
        "pivot_source": head["pivot_source"],
        "rotation": np.eye(3, dtype=np.float64).tolist(),
        "rest_global": matrix.tolist(),
        "rest_matrix": matrix.tolist(),
        "frame_rule": "world-aligned at source stations.neck_collar.C",
        "pose_rotation_order": "Ry(yaw) @ Rx(nod)",
    }
    return result


def _arm_frame_records(frames: dict[str, dict[str, Any]],
                       arms: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Add pivot frames derived from the source J->E and E->W bones."""
    result = copy.deepcopy(frames)
    for side in _SIDES:
        row = arms[side]
        J = _vector(row["J"], f"base_mesh.metadata.arms.{side}.J")
        E = _vector(row["E"], f"base_mesh.metadata.arms.{side}.E")
        W = _vector(row["W"], f"base_mesh.metadata.arms.{side}.W")
        shoulder = _arm_frame(J, E, f"{side} shoulder")
        elbow = _arm_frame(E, W, f"{side} elbow")
        shoulder_rest = _matrix(shoulder["rest_global"],
                                f"{side} shoulder rest frame")
        elbow_rest = _matrix(elbow["rest_global"],
                             f"{side} elbow rest frame")
        shoulder_local_elbow = _inverse_rigid(
            shoulder_rest, f"{side} shoulder rest frame") @ elbow_rest
        result[side]["shoulder"] = {
            "rotation": shoulder["rotation"],
            "rest_global": shoulder_rest.tolist(),
            "rest_matrix": shoulder_rest.tolist(),
            "frame_rule": shoulder["frame_rule"],
        }
        result[side]["elbow"] = {
            "rotation": elbow["rotation"],
            "rest_global": elbow_rest.tolist(),
            "rest_matrix": elbow_rest.tolist(),
            "rest_local": shoulder_local_elbow.tolist(),
            "frame_rule": elbow["frame_rule"],
        }
        result[side]["arm_source_points"] = {
            "J": J, "E": E, "W": W,
            "frame_source": "source J->E and E->W bones; not construction P->E/E->W sections",
            "pose_rotation_order": (
                "shoulder Rz(side_sign*shoulder_raise) @ Rx(-shoulder_forward); "
                "elbow Rx(-elbow)"
            ),
        }
    return result


def _joint_records(frames: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str | None]]:
    identity = np.eye(4, dtype=np.float64)
    joints: dict[str, dict[str, Any]] = {
        "pelvis": {
            "rest_matrix": identity.tolist(),
            "inverse_bind_matrix": identity.tolist(),
        }
    }
    parents: dict[str, str | None] = {"pelvis": None}
    for side in _SIDES:
        frame = _mapping(frames[side], f"binding.rest_frames.{side}")
        thigh_rest, knee_rest, _ = _frame_matrices(frame, side)
        joints[f"{side}_hip"] = {
            "rest_matrix": thigh_rest.tolist(),
            "inverse_bind_matrix": _inverse_rigid(
                thigh_rest, f"binding.rest_frames.{side}.thigh.rest_global"
            ).tolist(),
        }
        joints[f"{side}_knee"] = {
            "rest_matrix": knee_rest.tolist(),
            "inverse_bind_matrix": _inverse_rigid(
                knee_rest, f"binding.rest_frames.{side}.knee.rest_global"
            ).tolist(),
        }
        parents[f"{side}_hip"] = "pelvis"
        parents[f"{side}_knee"] = f"{side}_hip"
        if "shoulder" in frame or "elbow" in frame:
            if "shoulder" not in frame or "elbow" not in frame:
                _fail(f"binding.rest_frames.{side} must contain both arm pivot frames")
            shoulder = _matrix(
                _mapping(frame["shoulder"], f"binding.rest_frames.{side}.shoulder").get("rest_global"),
                f"binding.rest_frames.{side}.shoulder.rest_global")
            elbow = _matrix(
                _mapping(frame["elbow"], f"binding.rest_frames.{side}.elbow").get("rest_global"),
                f"binding.rest_frames.{side}.elbow.rest_global")
            joints[f"{side}_shoulder"] = {
                "rest_matrix": shoulder.tolist(),
                "inverse_bind_matrix": _inverse_rigid(
                    shoulder, f"binding.rest_frames.{side}.shoulder.rest_global"
                ).tolist(),
            }
            joints[f"{side}_elbow"] = {
                "rest_matrix": elbow.tolist(),
                "inverse_bind_matrix": _inverse_rigid(
                    elbow, f"binding.rest_frames.{side}.elbow.rest_global"
                ).tolist(),
            }
            parents[f"{side}_shoulder"] = "pelvis"
            parents[f"{side}_elbow"] = f"{side}_shoulder"
    if "head" in frames:
        head = _mapping(frames["head"], "binding.rest_frames.head")
        head_rest = _matrix(
            head.get("rest_global", head.get("rest_matrix")),
            "binding.rest_frames.head.rest_global",
        )
        joints["neck"] = {
            "rest_matrix": head_rest.tolist(),
            "inverse_bind_matrix": _inverse_rigid(
                head_rest, "binding.rest_frames.head.rest_global"
            ).tolist(),
        }
        parents["neck"] = "pelvis"
    return joints, parents


def bind(base_mesh: Mapping[str, Any], rest_mesh: Mapping[str, Any],
         prior_root_mesh: Mapping[str, Any], prior_hip_binding: Mapping[str, Any],
         leg_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Bind legs plus optional source-owned arms and one neck/head joint."""
    base = _mapping(base_mesh, "base_mesh")
    rest = _mapping(rest_mesh, "rest_mesh")
    prior_root = _mapping(prior_root_mesh, "prior_root_mesh")
    prior_binding = _mapping(prior_hip_binding, "prior_hip_binding")
    legs, declared_support, mid_thigh_factor = _leg_inputs(leg_inputs)
    base_vertices = _vertices(base, "base_mesh")
    rest_vertices = _vertices(rest, "rest_mesh")
    prior_vertices = _vertices(prior_root, "prior_root_mesh")
    base_quads = _quads(base, len(base_vertices), "base_mesh")
    prior_quads = _quads(prior_root, len(prior_vertices), "prior_root_mesh")
    _quads(rest, len(rest_vertices), "rest_mesh")
    _validate_levels(base, rest)
    tail = _validate_root(base_vertices, base_quads, prior_vertices, prior_quads, base)
    _validate_constructor_root_metadata(base, len(prior_quads), tail)
    prior_weights = _prior_root_weights(prior_binding)
    rings, station_points = _chain_rings(
        base, len(base_vertices), legs, declared_support
    )
    tail_indices = set(tail["new_vertex_indices"]) if tail is not None else set()
    leg_indices = {index for side in _SIDES for ring in rings[side] for index in ring}
    if tail_indices & leg_indices:
        _fail("tail allocation overwrites an existing leg station allocation")
    arms = _arm_vertex_indices(base, len(base_vertices), rings, tail_indices)
    head = _head_vertex_indices(base, len(base_vertices), rings, arms, tail_indices)
    feet = _foot_vertex_indices(base, len(base_vertices), rings, arms, head, tail_indices)
    joint_order, columns = _binding_layout(bool(arms), bool(head))
    base_weights = _expanded_root_weights(prior_weights, len(base_vertices), columns)
    _apply_station_weights(base_weights, rings)
    _apply_foot_weights(base_weights, feet)
    arm_influence = None
    arm_blends = None
    if arms:
        arm_influence = _arm_root_influence(
            base, base_quads, arms, rings, prior_quads,
        )
        arm_blends = _arm_appendage_blends(base_quads, arms)
        _apply_arm_weights(base_weights, arms, arm_blends, arm_influence)
    head_influence = None
    if head:
        head_influence = _head_root_influence(
            base, base_quads, head, arm_influence, prior_quads,
        )
        _apply_head_weights(base_weights, head, head_influence, columns.index("neck"))
    tail_weighting = None
    if tail is not None:
        tail_weighting = _apply_tail_weights(base_weights, tail)
    _check_weight_bounds(base_weights, "base_weights")
    stencils = _rest_stencils(rest, len(base_vertices), len(rest_vertices))
    evaluated_weights = _propagate_weights(stencils, base_weights)
    frames = _frame_records(legs)
    if arms:
        frames = _arm_frame_records(frames, arms)
    if head:
        frames = _head_frame_record(frames, head)
    joints, parents = _joint_records(frames)
    ring_mapping = copy.deepcopy(rings)
    bound_leg_inputs: dict[str, Any] = {
        side: copy.deepcopy(dict(_mapping(leg_inputs[side], f"leg_inputs.{side}")))
        for side in _SIDES
    }
    for side in _SIDES:
        for name in ("J", "T", "K", "A"):
            bound_leg_inputs[side][name] = copy.deepcopy(legs[side][name])
        bound_leg_inputs[side]["support_fraction"] = declared_support[side]
        bound_leg_inputs[side]["mid_thigh_factor"] = mid_thigh_factor[side]
    result = {
        "schema": "creature-kernel.connected-leg-assembly-binding.v1",
        "joint_order": list(joint_order),
        "weight_columns": list(columns),
        "joints": joints,
        "parents": parents,
        "base_weights": base_weights.tolist(),
        "evaluated_weights": evaluated_weights.tolist(),
        "rest_frames": frames,
        "leg_inputs": bound_leg_inputs,
        "station_names": list(_STATION_NAMES),
        "source_station_ids": list(_SOURCE_STATION_IDS),
        "station_points": station_points,
        "station_shank_weights": list(_STATION_SHANK_WEIGHTS),
        "source_station_knee": list(_STATION_SHANK_WEIGHTS),
        "prior_column_map": [0, 1, 3],
        "chain_ring_mapping": ring_mapping,
        "metadata": {
            "algorithm": (
                "preserved_prior_root_hip_weights_plus_explicit_source_station_knee_blend_"
                + ("source_root_arm_harmonic_and_source_root_neck_field_"
                   if arms and head else
                   "source_root_neck_field_" if head else
                   "source_root_arm_harmonic_" if arms else "")
                + ("tail_host_support_to_pelvis_transition_" if tail is not None else "")
                + f"then_l2_rest_stencil_{len(joint_order)}joint_lbs"
            ),
            "weight_method": "shared_source_station_knee_blend_with_explicit_center_and_support_rows",
            "harmonic_knee_solver": False,
            "numeric_guard": (
                "prior-baseline bound tolerance [-1e-12,1+1e-12]; validation "
                "guard only, with no clamping, renormalization, or method retune"
            ),
            "tolerance": _TOLERANCE,
            "coordinate_system": "metres; Y up; Z front",
            "weight_columns": list(columns),
            "joint_order": list(joint_order),
            "parents": parents,
            "root_vertex_count": _ROOT_VERTEX_COUNT,
            "root_quad_count": len(prior_quads),
            "station_count_per_side": _STATION_COUNT,
            "ring_vertex_count": _RING_VERTEX_COUNT,
            "station_names": list(_STATION_NAMES),
            "source_station_ids": list(_SOURCE_STATION_IDS),
            "station_points": station_points,
            "station_shank_weights": list(_STATION_SHANK_WEIGHTS),
            "source_station_knee": list(_STATION_SHANK_WEIGHTS),
            "prior_column_map": [0, 1, 3],
            "support_fraction": copy.deepcopy(declared_support),
            "mid_thigh_factor": copy.deepcopy(mid_thigh_factor),
            "chain_ring_mapping": ring_mapping,
            "stencil_provenance": "REST",
            "posed_cage_evaluation": False,
            "rest_geometry_regenerated": False,
            "root_weight_source": "prior_hip_binding.base_weights positional 152x3 captured calibration table",
            "root_weight_mapping": {
                "pelvis": "prior column 0",
                "left_thigh": "prior column 1",
                "left_shank": "zero",
                "right_thigh": "prior column 2",
                "right_shank": "zero",
            },
            "hierarchy": {
                "pelvis": "identity",
                "left_shank": "left_thigh_parent",
                "right_shank": "right_thigh_parent",
                "ankle_joint": "not_present; later distal extension",
                "tail_joint": "not_present; tail vertices transition to pelvis only",
            },
        },
    }
    if arms:
        arm_indices = {
            side: copy.deepcopy(row["new_vertex_indices"])
            for side, row in arms.items()
        }
        result["arm_vertex_indices"] = arm_indices
        result["arm_root_influence"] = copy.deepcopy(arm_influence)
        result["arm_elbow_blend"] = {
            side: {str(index): value for index, value in values.items()}
            for side, values in arm_blends.items()
        }
        result["metadata"]["arm_vertex_indices"] = copy.deepcopy(arm_indices)
        result["metadata"]["arm_root_influence"] = copy.deepcopy(arm_influence)
        result["metadata"]["arm_elbow_blend"] = copy.deepcopy(result["arm_elbow_blend"])
        result["metadata"]["arm_weighting"] = {
            "root": "D0/D1 free root graph field; collar value 1; D2 zero boundary",
            "collar_pre_elbow": 0.0,
            "elbow": "free arm-appendage harmonic blend",
            "post_elbow_onward": 1.0,
        }
        result["metadata"]["root_weight_mapping"].update({
            "left_upper_arm": "source arm harmonic influence",
            "left_forearm": "zero on root; arm elbow blend on appended arm",
            "right_upper_arm": "source arm harmonic influence",
            "right_forearm": "zero on root; arm elbow blend on appended arm",
        })
        result["metadata"]["hierarchy"].update({
            "left_forearm": "left_upper_arm_parent",
            "right_forearm": "right_upper_arm_parent",
            "left_shoulder": "pelvis",
            "left_elbow": "left_shoulder_parent",
            "right_shoulder": "pelvis",
            "right_elbow": "right_shoulder_parent",
            "pivot_frame_source": "source J->E and E->W bones; visible P->E frame excluded",
        })
    if head:
        head_indices = copy.deepcopy(head["new_vertex_indices"])
        result["head_vertex_indices"] = head_indices
        result["head_root_influence"] = copy.deepcopy(head_influence)
        result["metadata"]["head_vertex_indices"] = copy.deepcopy(head_indices)
        result["metadata"]["head_root_influence"] = copy.deepcopy(head_influence)
        result["metadata"]["head_weighting"] = {
            "root": "D0/D1 free root graph field; neck support ring value 1; D2 zero boundary",
            "appendage": "head, muzzle, and ears neck one-hot",
            "shoulder_overlap": copy.deepcopy(head_influence["per_root"]["shoulder_overlap"]),
            "pivot_source": "stations.neck_collar.C",
            "neck_upper_port_is_pivot": False,
        }
        result["metadata"]["root_weight_mapping"]["neck"] = (
            "source head neck harmonic influence"
        )
        result["metadata"]["hierarchy"].update({
            "neck": "pelvis",
            "head_pivot": "stations.neck_collar.C",
            "head_frame": "world-aligned at source pivot; neck_upper is connection port only",
        })
    if any(feet.values()):
        result["foot_vertex_indices"] = copy.deepcopy(feet)
        result["metadata"]["foot_vertex_indices"] = copy.deepcopy(feet)
        result["metadata"]["foot_weighting"] = {
            "left": "left_shank_onehot",
            "right": "right_shank_onehot",
            "ankle_joint": "not_present",
        }
    if tail is not None:
        result["tail_vertex_indices"] = copy.deepcopy(tail["new_vertex_indices"])
        result["tail_weighting"] = copy.deepcopy(tail_weighting)
        result["metadata"]["tail_vertex_indices"] = copy.deepcopy(tail["new_vertex_indices"])
        result["metadata"]["tail_weighting"] = copy.deepcopy(tail_weighting)
        result["metadata"]["tail_weighting_contract"] = {
            "host_face": tail["host_face"],
            "host_vertex_indices": copy.deepcopy(tail["host_vertices"]),
            "kept_root_face_correspondence": copy.deepcopy(tail["kept_faces"]),
            "replacement_face_indices": copy.deepcopy(tail["replacement_faces"]),
            "collar_blend_strength": tail["collar_blend_strength"],
            "distal_target_joint": "pelvis",
            "tail_joint": "not_present",
        }
    return result


def joint_points(binding: Mapping[str, Any], angles: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return rest/posed hierarchy diagnostics for pelvis, hips, knees, and landmarks."""
    return _joint_transforms(_mapping(binding, "binding"), angles)


def pose(rest_mesh: Mapping[str, Any], binding: Mapping[str, Any],
         angles: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the bound five-, six-, nine-, or ten-column LBS to rest L2."""
    rest = _mapping(rest_mesh, "rest_mesh")
    bound = _mapping(binding, "binding")
    vertices = _vertices(rest, "rest_mesh")
    joint_order = tuple(bound.get("joint_order", ()))
    valid_layouts = {
        _LEG_JOINT_ORDER: (False, False),
        _ARM_JOINT_ORDER: (True, False),
        _HEAD_JOINT_ORDER: (False, True),
        _ARM_HEAD_JOINT_ORDER: (True, True),
    }
    if joint_order not in valid_layouts:
        _fail("binding.joint_order must be a five-, six-, nine-, or ten-joint layout")
    has_arms, has_head = valid_layouts[joint_order]
    _expected_joint_order, columns = _binding_layout(has_arms, has_head)
    weights = _weight_matrix(bound.get("evaluated_weights"), len(vertices),
                             len(columns), "binding.evaluated_weights")
    transforms = _joint_transforms(bound, angles)
    skins = {
        "pelvis": np.eye(4, dtype=np.float64),
        "left_hip": _matrix(transforms["left"]["thigh"]["skin_matrix"],
                             "left hip skin_matrix"),
        "left_knee": _matrix(transforms["left"]["knee"]["skin_matrix"],
                              "left knee skin_matrix"),
        "right_hip": _matrix(transforms["right"]["thigh"]["skin_matrix"],
                              "right hip skin_matrix"),
        "right_knee": _matrix(transforms["right"]["knee"]["skin_matrix"],
                               "right knee skin_matrix"),
    }
    if has_arms:
        skins.update({
            "left_shoulder": _matrix(transforms["left"]["shoulder"]["skin_matrix"],
                                      "left shoulder skin_matrix"),
            "left_elbow": _matrix(transforms["left"]["elbow"]["skin_matrix"],
                                   "left elbow skin_matrix"),
            "right_shoulder": _matrix(transforms["right"]["shoulder"]["skin_matrix"],
                                       "right shoulder skin_matrix"),
            "right_elbow": _matrix(transforms["right"]["elbow"]["skin_matrix"],
                                    "right elbow skin_matrix"),
        })
    if has_head:
        skins["neck"] = _matrix(transforms["head"]["skin_matrix"],
                                 "neck skin_matrix")
    parsed_angles = _angles(angles)
    if not has_arms and any(parsed_angles[side][joint] != 0.0
                            for side in _SIDES
                            for joint in ("shoulder_raise", "shoulder_forward", "elbow")):
        _fail("arm pose angles require a nine-column arm binding")
    if not has_head and any(parsed_angles["head"][joint] != 0.0
                            for joint in ("yaw", "nod")):
        _fail("head pose angles require a six- or ten-column head binding")
    pose_angle_names = ("hip", "knee", "shoulder_raise", "shoulder_forward", "elbow")
    no_body_motion = all(parsed_angles[side][joint] == 0.0
                         for side in _SIDES for joint in pose_angle_names)
    no_head_motion = all(parsed_angles["head"][joint] == 0.0
                         for joint in ("yaw", "nod"))
    if no_body_motion and no_head_motion:
        posed_vertices = copy.deepcopy(vertices)
    else:
        posed_vertices = []
        for vertex_index, point in enumerate(vertices):
            homogeneous = np.r_[np.asarray(point, dtype=np.float64), 1.0]
            transformed = np.column_stack([
                (skins[name] @ homogeneous)[:3] for name in joint_order
            ])
            value = transformed @ weights[vertex_index]
            if not np.all(np.isfinite(value)):
                _fail(f"posed vertex {vertex_index} is non-finite")
            posed_vertices.append(value.tolist())

    output = copy.deepcopy(dict(rest))
    output["vertices"] = posed_vertices
    provenance = output.get("provenance", {})
    provenance = copy.deepcopy(dict(provenance)) if isinstance(provenance, Mapping) else {}
    provenance.update({
        "vertices": f"POSED_BY_EVALUATED_REST_L2_{len(joint_order)}JOINT_LBS",
        "rest_vertices": "INPUT_REST_L2",
        "base_stencils": "REST",
        "stencil_evaluation": "evaluated rest mesh; posed cage not evaluated",
    })
    output["provenance"] = provenance
    metadata = output.get("metadata", {})
    metadata = copy.deepcopy(dict(metadata)) if isinstance(metadata, Mapping) else {}
    metadata.update({
        "representation": "pose",
        "rest_geometry_regenerated": False,
        "stencil_provenance": "REST",
        "posed_cage_evaluation": False,
        "pose_angles_degrees": copy.deepcopy(parsed_angles),
        "joint_order": list(joint_order),
    })
    output["metadata"] = metadata
    return output


__all__ = ["bind", "joint_points", "pose"]

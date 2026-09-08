"""FOOT-004 source/form candidate attached to expanded connected-leg L0.

This candidate keeps the FOOT-003 grid connectivity and delegates its mesh,
topology, collision, and evaluation helpers to ``foot_construction``.  It
changes only the source representation: five local centre controls and three
local-normal radii per control produce rounded ten-point transverse sections.
It does not create a joint, weights, a rig, poses, or a body.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
import math
from typing import Any

import foot_construction as _shared


_SIDES = ("left", "right")
_ANCHORS = ("H", "R", "M", "B", "T")
_LATERAL_FRACTIONS = (-1.0, -0.65, 0.0, 0.65, 1.0)
_ROW_NAMES = (
    "rear_heel", "heel_ankle_midpoint", "ankle_body",
    "ankle_body_quarter", "ankle_body_five_eighths", "forefoot_start",
    "forefoot_body", "terminal",
)
_ROW_FORMULAS = (
    "H", "midpoint(H,R)", "R", "R+0.25*(M-R)",
    "R+0.625*(M-R)", "M", "B", "T",
)
_ROW_ROLES = (
    "H rear heel source control",
    "derived H-to-R centre row",
    "R ankle-body surface-centre source control; not a joint",
    "derived R-to-M centre row",
    "derived R-to-M centre row",
    "M forefoot-start source control",
    "B forefoot-body source control",
    "T terminal source control",
)
_HOLE_BOUNDARY_POSITIONS = _shared._HOLE_BOUNDARY_POSITIONS
_HOLE_BOUNDARY_NAMES = _shared._HOLE_BOUNDARY_NAMES
_GLOBAL_Y = (0.0, 1.0, 0.0)
_GLOBAL_Z = (0.0, 0.0, 1.0)
_COORDINATE_TOLERANCE = 1.0e-8
_FRAME_TOLERANCE = 1.0e-6
_FORWARD_TOLERANCE = 1.0e-8
_EXPECTED_CONSTRUCTION = {
    "midpoint_fraction": 0.5,
    "rise_row_fractions": (0.25, 0.625),
    "rise_width_exponent": 2.0,
    "cross_section_rounding": 0.94,
    "collar_fraction": 0.20,
}


FootFormConstructionError = _shared.FootConstructionError


def _fail(message: str) -> None:
    raise FootFormConstructionError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    return _shared._mapping(value, where)


def _finite(value: Any, where: str) -> float:
    return _shared._finite(value, where)


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    return _shared._vector(value, where)


def _add(*values: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(value[axis] for value in values)
                 for axis in range(3))  # type: ignore[return-value]


def _sub(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[axis] - right[axis]
                 for axis in range(3))  # type: ignore[return-value]


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
    if not math.isfinite(length) or length <= _COORDINATE_TOLERANCE:
        _fail(f"{where} must have positive finite length")
    return _scale(value, 1.0 / length)


def _lerp(left: tuple[float, float, float],
          right: tuple[float, float, float], fraction: float) -> tuple[float, float, float]:
    return _add(_scale(left, 1.0 - fraction), _scale(right, fraction))


def _parse_anchor(raw: Any, where: str) -> dict[str, float]:
    row = _mapping(raw, where)
    if set(row) != {"local_y", "local_z", "rL", "rD", "rP"}:
        _fail(f"{where} must contain exactly local_y, local_z, rL, rD, and rP")
    result = {
        "local_y": _finite(row["local_y"], f"{where}.local_y"),
        "local_z": _finite(row["local_z"], f"{where}.local_z"),
        "rL": _finite(row["rL"], f"{where}.rL"),
        "rD": _finite(row["rD"], f"{where}.rD"),
        "rP": _finite(row["rP"], f"{where}.rP"),
    }
    if any(result[key] <= 0.0 for key in ("rL", "rD", "rP")):
        _fail(f"{where} radii must be positive")
    return result


def _parse_construction(raw: Any) -> dict[str, Any]:
    row = _mapping(raw, "foot_form_inputs.construction")
    if set(row) != {
            "midpoint_fraction", "rise_row_fractions", "rise_width_exponent",
            "cross_section_rounding", "collar_fraction"}:
        _fail("foot_form_inputs.construction has unsupported or missing fields")
    midpoint = _finite(row["midpoint_fraction"], "construction.midpoint_fraction")
    fractions = row["rise_row_fractions"]
    if type(fractions) not in (list, tuple) or len(fractions) != 2:
        _fail("construction.rise_row_fractions must contain two fractions")
    rise_fractions = tuple(_finite(value, "construction.rise_row_fractions")
                           for value in fractions)
    exponent = _finite(row["rise_width_exponent"], "construction.rise_width_exponent")
    rounding = _finite(row["cross_section_rounding"], "construction.cross_section_rounding")
    collar = _finite(row["collar_fraction"], "construction.collar_fraction")
    if abs(midpoint - _EXPECTED_CONSTRUCTION["midpoint_fraction"]) > _FRAME_TOLERANCE:
        _fail("construction.midpoint_fraction differs from the settled FOOT-004 value")
    if any(abs(left - right) > _FRAME_TOLERANCE
           for left, right in zip(rise_fractions, _EXPECTED_CONSTRUCTION["rise_row_fractions"])):
        _fail("construction.rise_row_fractions differ from the settled FOOT-004 values")
    if abs(exponent - _EXPECTED_CONSTRUCTION["rise_width_exponent"]) > _FRAME_TOLERANCE:
        _fail("construction.rise_width_exponent differs from the settled FOOT-004 value")
    if abs(rounding - _EXPECTED_CONSTRUCTION["cross_section_rounding"]) > _FRAME_TOLERANCE:
        _fail("construction.cross_section_rounding differs from the settled FOOT-004 value")
    if abs(collar - _EXPECTED_CONSTRUCTION["collar_fraction"]) > _FRAME_TOLERANCE:
        _fail("construction.collar_fraction differs from the settled FOOT-004 value")
    if not 0.0 < rise_fractions[0] < rise_fractions[1] < 1.0:
        _fail("construction.rise_row_fractions must be increasing inside R..M")
    if not 0.0 < rounding < 1.0:
        _fail("construction.cross_section_rounding must be between zero and one")
    if not 0.0 < collar < 1.0:
        _fail("construction.collar_fraction must be between zero and one")
    return {
        "midpoint_fraction": midpoint,
        "rise_row_fractions": list(rise_fractions),
        "rise_width_exponent": exponent,
        "cross_section_rounding": rounding,
        "collar_fraction": collar,
    }


def _parse_form_inputs(raw: Any) -> dict[str, Any]:
    value = _mapping(raw, "foot_form_inputs")
    if set(value) != {"case_id", "construction", "sides"}:
        _fail("foot_form_inputs must be one exact case row with case_id, construction, and sides")
    if type(value["case_id"]) is not str or not value["case_id"]:
        _fail("foot_form_inputs.case_id must be non-empty text")
    construction = _parse_construction(value["construction"])
    sides = _mapping(value["sides"], "foot_form_inputs.sides")
    if set(sides) != set(_SIDES):
        _fail("foot_form_inputs.sides must contain exactly left and right")
    parsed_sides: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        source = _mapping(sides[side], f"foot_form_inputs.sides.{side}")
        if set(source) != {"reference_y", *_ANCHORS}:
            _fail(f"foot_form_inputs.sides.{side} has unsupported or missing fields")
        parsed = {name: _parse_anchor(source[name],
                                      f"foot_form_inputs.sides.{side}.{name}")
                  for name in _ANCHORS}
        parsed["reference_y"] = _finite(
            source["reference_y"], f"foot_form_inputs.sides.{side}.reference_y"
        )
        local_zs = [parsed[name]["local_z"] for name in _ANCHORS]
        if any(not left < right for left, right in zip(local_zs, local_zs[1:])):
            _fail(f"foot_form_inputs.sides.{side} source centres must move forward H<R<M<B<T")
        parsed_sides[side] = parsed
    return {"case_id": value["case_id"], "construction": construction,
            "sides": parsed_sides}


def _source_frame(base_mesh: Mapping[str, Any], side: str,
                  attachment_frame: Mapping[str, tuple[float, float, float]]) -> dict[str, tuple[float, float, float]]:
    # ``base_mesh.frames.<side>`` is the construction's leg-summary frame. It
    # is retained as metadata, but it is not the terminal ankle section frame.
    # The validated attachment frame returned by _ankle_chain is the sole
    # source of the foot-local lateral axis.
    X = _vector(attachment_frame.get("X"),
                f"{side} attachment_frame.X")
    projection = _sub(_GLOBAL_Y, _scale(X, _dot(_GLOBAL_Y, X)))
    U = _normalise(projection, f"{side} source-frame up")
    if _dot(U, _GLOBAL_Y) <= _FORWARD_TOLERANCE:
        _fail(f"{side} source-frame up does not point toward global +Y")
    F = _normalise(_cross(X, U), f"{side} source-frame forward")
    if _dot(F, _GLOBAL_Z) <= _FORWARD_TOLERANCE:
        _fail(f"{side} source-frame forward is not positively consistent with global +Z")
    if _dot(_cross(X, U), F) < 1.0 - _FRAME_TOLERANCE:
        _fail(f"{side} source frame is not right-handed")
    return {"X": X, "U": U, "F": F}


def _world_point(origin: tuple[float, float, float],
                 frame: Mapping[str, tuple[float, float, float]],
                 local_y: float, local_z: float) -> tuple[float, float, float]:
    return _add(origin, _scale(frame["U"], local_y),
                 _scale(frame["F"], local_z))


def _segment_for_z(z: float, controls: Mapping[str, Mapping[str, float]]) -> int:
    for index in range(len(_ANCHORS) - 1):
        if z <= controls[_ANCHORS[index + 1]]["local_z"]:
            return index
    return len(_ANCHORS) - 2


def _piecewise_value(z: float, controls: Mapping[str, Mapping[str, float]],
                     field: str, *, rise_exponent: float | None = None) -> tuple[float, int, float]:
    segment = _segment_for_z(z, controls)
    left_name, right_name = _ANCHORS[segment], _ANCHORS[segment + 1]
    left, right = controls[left_name], controls[right_name]
    fraction = ((z - left["local_z"]) /
                (right["local_z"] - left["local_z"]))
    used_fraction = fraction
    if rise_exponent is not None and left_name == "R" and right_name == "M":
        used_fraction = fraction ** rise_exponent
    value = left[field] + used_fraction * (right[field] - left[field])
    return value, segment, fraction


def _unit_secants(origin: tuple[float, float, float],
                  frame: Mapping[str, tuple[float, float, float]],
                  controls: Mapping[str, Mapping[str, float]],
                  side: str) -> list[tuple[float, float, float]]:
    centres = [
        _world_point(origin, frame, controls[name]["local_y"], controls[name]["local_z"])
        for name in _ANCHORS
    ]
    result = []
    for index, (left, right) in enumerate(zip(centres, centres[1:])):
        tangent = _normalise(_sub(right, left), f"{side} source secant {index}")
        if _dot(tangent, frame["F"]) <= _FORWARD_TOLERANCE:
            _fail(f"{side} source secant reverses source-frame forward")
        result.append(tangent)
    return result


def _row_tangent(row_index: int, z: float, origin: tuple[float, float, float],
                 frame: Mapping[str, tuple[float, float, float]],
                 controls: Mapping[str, Mapping[str, float]],
                 secants: list[tuple[float, float, float]], side: str) -> tuple[float, float, float]:
    if row_index == 0:
        tangent = secants[0]
    elif row_index == len(_ROW_NAMES) - 1:
        tangent = secants[-1]
    else:
        control_index = next(
            (index for index, name in enumerate(_ANCHORS)
             if abs(z - controls[name]["local_z"]) <= _COORDINATE_TOLERANCE),
            None,
        )
        if control_index is not None:
            tangent = _normalise(
                _add(secants[control_index - 1], secants[control_index]),
                f"{side} row {row_index} interior tangent",
            )
        else:
            tangent = secants[_segment_for_z(z, controls)]
    if _dot(tangent, frame["F"]) <= _FORWARD_TOLERANCE:
        _fail(f"{side} row {row_index} tangent reverses source-frame forward")
    return tangent


def _grid_points(origin: tuple[float, float, float],
                 frame: Mapping[str, tuple[float, float, float]],
                 controls: Mapping[str, Mapping[str, float]],
                 construction: Mapping[str, Any], side: str) -> dict[str, Any]:
    zs = [
        controls["H"]["local_z"],
        construction["midpoint_fraction"] * (
            controls["H"]["local_z"] + controls["R"]["local_z"]),
        controls["R"]["local_z"],
        controls["R"]["local_z"] + construction["rise_row_fractions"][0] * (
            controls["M"]["local_z"] - controls["R"]["local_z"]),
        controls["R"]["local_z"] + construction["rise_row_fractions"][1] * (
            controls["M"]["local_z"] - controls["R"]["local_z"]),
        controls["M"]["local_z"],
        controls["B"]["local_z"],
        controls["T"]["local_z"],
    ]
    if any(not left < right for left, right in zip(zs, zs[1:])):
        _fail(f"{side} FOOT-004 row z values are not strictly ordered")
    secants = _unit_secants(origin, frame, controls, side)
    rows: list[dict[str, Any]] = []
    top: list[list[tuple[float, float, float]]] = []
    bottom: list[list[tuple[float, float, float]]] = []
    for row_index, z in enumerate(zs):
        centre_y, segment, fraction = _piecewise_value(z, controls, "local_y")
        rL, _, _ = _piecewise_value(
            z, controls, "rL", rise_exponent=construction["rise_width_exponent"]
        )
        rD, _, _ = _piecewise_value(z, controls, "rD")
        rP, _, _ = _piecewise_value(z, controls, "rP")
        centre = _world_point(origin, frame, centre_y, z)
        tangent = _row_tangent(row_index, z, origin, frame, controls, secants, side)
        normal = _normalise(_cross(tangent, frame["X"]),
                            f"{side} row {row_index} local normal")
        if _dot(normal, frame["U"]) <= _FORWARD_TOLERANCE:
            _fail(f"{side} row {row_index} local normal points below the source frame")
        rows.append({
            "name": _ROW_NAMES[row_index],
            "formula": _ROW_FORMULAS[row_index],
            "source_role": _ROW_ROLES[row_index],
            "local_z": z,
            "local_centre_y": centre_y,
            "source_segment": f"{_ANCHORS[segment]}-{_ANCHORS[segment + 1]}",
            "segment_fraction": fraction,
            "centre": list(centre),
            "tangent": list(tangent),
            "normal": list(normal),
            "rL": rL,
            "rD": rD,
            "rP": rP,
        })
        row_top: list[tuple[float, float, float]] = []
        row_bottom: list[tuple[float, float, float]] = []
        for q in _LATERAL_FRACTIONS:
            radicand = 1.0 - (construction["cross_section_rounding"] * q) ** 2
            if radicand <= 0.0:
                _fail(f"{side} row {row_index} rounded section radicand is not positive")
            arc = math.sqrt(radicand)
            lateral = _scale(frame["X"], q * rL)
            row_top.append(_add(centre, lateral, _scale(normal, arc * rD)))
            row_bottom.append(_add(centre, lateral, _scale(normal, -arc * rP)))
        top.append(row_top)
        bottom.append(row_bottom)
    return {"rows": rows, "top": top, "bottom": bottom,
            "secants": [list(value) for value in secants]}


def _append_vertex(output_vertices: list[list[float]], output_owners: list[str],
                   owners: list[str], new_vertices: list[int],
                   point: tuple[float, float, float], owner: str) -> int:
    index = len(output_vertices)
    output_vertices.append(list(point))
    output_owners.append(owner)
    owners.append(owner)
    new_vertices.append(index)
    return index


def _default_connector_builder(context: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve the original FOOT-004 collar connector in the default path."""
    append_vertex = context["append_vertex"]
    semantic_ankle = context["semantic_ankle"]
    hole_points = context["hole_points"]
    orientation = context["orientation"]
    form = context["form"]
    collar_points = [
        _shared._lerp_point(context["base_vertices"][semantic_ankle[index]],
                            hole_points[index],
                            form["construction"]["collar_fraction"])
        for index in range(8)
    ]
    collar_indices = [append_vertex(point) for point in collar_points]
    return {
        "ring_order": ["collar"],
        "rings": {"collar": collar_indices},
        "band_order": ["ankle_to_collar", "collar_to_hole"],
        "bands": {
            "ankle_to_collar": _shared._band(
                semantic_ankle, collar_indices, orientation),
            "collar_to_hole": _shared._band(
                collar_indices, context["hole_indices"], orientation),
        },
        "metadata": {},
    }


def _connector_result(raw: Any, output_vertex_count: int, side: str) -> dict[str, Any]:
    result = _mapping(raw, f"{side} connector result")
    if set(result) != {"ring_order", "rings", "band_order", "bands", "metadata"}:
        _fail(f"{side} connector result has unsupported or missing fields")
    ring_order = result["ring_order"]
    band_order = result["band_order"]
    if (type(ring_order) not in (list, tuple) or
            type(band_order) not in (list, tuple) or
            not ring_order or not band_order or
            any(type(name) is not str or not name
                for name in (*ring_order, *band_order))):
        _fail(f"{side} connector ring and band orders must be non-empty names")
    rings = _mapping(result["rings"], f"{side} connector rings")
    bands = _mapping(result["bands"], f"{side} connector bands")
    if set(rings) != set(ring_order) or set(bands) != set(band_order):
        _fail(f"{side} connector order does not match its named rings and bands")
    parsed_rings: dict[str, list[int]] = {}
    for name in ring_order:
        raw_ring = rings[name]
        if type(raw_ring) not in (list, tuple) or len(raw_ring) != 8:
            _fail(f"{side} connector ring {name} must contain eight vertices")
        ring = list(raw_ring)
        if (any(type(index) is not int or index < 0 or index >= output_vertex_count
                for index in ring) or len(set(ring)) != 8):
            _fail(f"{side} connector ring {name} has invalid or duplicate vertices")
        parsed_rings[name] = ring
    parsed_bands: dict[str, list[tuple[int, int, int, int]]] = {}
    for name in band_order:
        raw_band = bands[name]
        if type(raw_band) not in (list, tuple) or len(raw_band) != 8:
            _fail(f"{side} connector band {name} must contain eight quads")
        parsed_bands[name] = _shared._checked_quads(
            raw_band, output_vertex_count, f"{side} connector band {name}"
        )
    return {
        "ring_order": list(ring_order),
        "rings": parsed_rings,
        "band_order": list(band_order),
        "bands": parsed_bands,
        "metadata": copy.deepcopy(dict(_mapping(
            result["metadata"], f"{side} connector metadata"))),
    }


def build(base_mesh: Mapping[str, Any], leg_inputs: Mapping[str, Any],
          foot_form_inputs: Mapping[str, Any], *,
          connector_builder: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None
          ) -> dict[str, Any]:
    """Attach the FOOT-004 rounded-source grid to expanded connected-leg L0."""
    leg_rows = _shared._validate_leg_inputs(leg_inputs)
    form = _parse_form_inputs(foot_form_inputs)
    base_vertices, base_quads, base_loops, base_vertex_count, base_face_count = (
        _shared._validate_base_mesh(base_mesh, leg_rows)
    )
    output_vertices = [list(point) for point in base_vertices]
    output_quads = [list(face) for face in base_quads]
    output_face_owners = list(base_mesh["face_owners"])
    output_control_owners = list(base_mesh["control_owners"])
    base_metadata = _mapping(base_mesh["metadata"], "base_mesh.metadata")
    base_control_owners = list(base_metadata["base_control_owners"])
    output_loops = {
        name: list(loop) for name, loop in base_loops.items()
        if name not in _shared._ANKLE_PORTS.values()
    }
    metadata = copy.deepcopy(dict(base_metadata))
    metadata["level"] = 0
    metadata["base_control_owners"] = base_control_owners
    metadata["base_vertex_count"] = len(base_control_owners)
    metadata["feet"] = {}
    index_mapping = copy.deepcopy(metadata.get("index_mapping", {}))
    new_face_indices_by_side: dict[str, list[int]] = {}

    for side in _SIDES:
        ankle_loop, ankle_centre, attachment_frame = _shared._ankle_chain(
            base_mesh, side, leg_rows[side], base_vertices, base_loops
        )
        source_frame = _source_frame(base_mesh, side, attachment_frame)
        controls = form["sides"][side]
        grid = _grid_points(
            ankle_centre, source_frame,
            {name: controls[name] for name in _ANCHORS},
            form["construction"], side,
        )
        top_points = grid["top"]
        bottom_points = grid["bottom"]
        top_indices: list[list[int | None]] = [[None] * 5 for _ in top_points]
        bottom_indices: list[list[int]] = [[] for _ in bottom_points]
        new_vertices: list[int] = []
        owner = _shared._FOOT_OWNERS[side]

        def append_vertex(point: tuple[float, float, float]) -> int:
            return _append_vertex(
                output_vertices, output_control_owners, base_control_owners,
                new_vertices, point, owner
            )

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
            _fail(f"{side} FOOT-004 ankle hole contains a missing vertex")
        hole_indices = [int(index) for index in hole_indices]
        correspondence = _shared._correspondence(
            ankle_loop, base_vertices, ankle_centre, attachment_frame,
            hole_points, _HOLE_BOUNDARY_NAMES, side,
        )
        semantic_ankle = correspondence["target_to_ankle_indices"]
        direction = int(correspondence["direction"])
        ankle_winding = _shared._loop_winding(base_quads, ankle_loop, side)
        orientation = ankle_winding * direction
        if orientation != 1:
            _fail(f"{side} FOOT-004 ankle-to-hole winding is incompatible")
        dorsal_faces = _shared._top_grid_faces(top_indices)
        plantar_faces = _shared._bottom_grid_faces(bottom_indices)
        perimeter_faces = _shared._outer_grid_faces(top_indices, bottom_indices)
        builder = _default_connector_builder if connector_builder is None else connector_builder
        if not callable(builder):
            _fail("connector_builder must be callable")
        connector = _connector_result(builder({
            "side": side,
            "base_vertices": base_vertices,
            "base_quads": base_quads,
            "output_vertices": output_vertices,
            "output_control_owners": output_control_owners,
            "base_control_owners": base_control_owners,
            "new_vertices": new_vertices,
            "append_vertex": append_vertex,
            "ankle_loop": ankle_loop,
            "ankle_centre": ankle_centre,
            "attachment_frame": attachment_frame,
            "semantic_ankle": semantic_ankle,
            "hole_points": hole_points,
            "hole_indices": hole_indices,
            "orientation": orientation,
            "owner": owner,
            "top_indices": top_indices,
            "bottom_indices": bottom_indices,
            "retained_faces": {
                "dorsal_grid": dorsal_faces,
                "plantar_grid": plantar_faces,
                "outer_perimeter": perimeter_faces,
            },
            "grid": grid,
            "controls": controls,
            "form": form,
        }), len(output_vertices), side)

        foot_faces: list[int] = []
        face_ranges: dict[str, list[int]] = {}

        def add_faces(name: str, faces: list[tuple[int, int, int, int]]) -> None:
            start = len(output_quads)
            output_quads.extend([list(face) for face in faces])
            output_face_owners.extend([owner] * len(faces))
            indices = list(range(start, start + len(faces)))
            face_ranges[name] = indices
            foot_faces.extend(indices)

        add_faces("dorsal_grid", dorsal_faces)
        add_faces("plantar_grid", plantar_faces)
        add_faces("outer_perimeter", perimeter_faces)
        for name in connector["band_order"]:
            add_faces(name, connector["bands"][name])
        new_face_indices_by_side[side] = foot_faces

        source_anchors = {
            name: list(_world_point(ankle_centre, source_frame,
                                    controls[name]["local_y"],
                                    controls[name]["local_z"]))
            for name in _ANCHORS
        }
        metadata["feet"][side] = {
            "owner": owner,
            "source_anchors": source_anchors,
            "anchor_fields": copy.deepcopy({name: controls[name] for name in _ANCHORS}),
            "ankle_source_loop": list(ankle_loop),
            "attachment_loop": {
                "ankle": list(ankle_loop),
                "hole": list(hole_indices),
                **{name: list(connector["rings"][name])
                   for name in connector["ring_order"]},
            },
            "ring_order": ["dorsal_grid", "plantar_grid", "ankle_hole",
                           *connector["ring_order"]],
            "ring_indices_by_name": {
                "dorsal_grid": [index for row in top_indices for index in row
                                if index is not None],
                "plantar_grid": [index for row in bottom_indices for index in row],
                "ankle_hole": list(hole_indices),
                **{name: list(connector["rings"][name])
                   for name in connector["ring_order"]},
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
            "face_owner": owner,
            "face_owner_ranges": face_ranges,
            "collar_fraction": form["construction"]["collar_fraction"],
            "correspondence": correspondence,
            "winding": {
                "attached_ankle_loop": ankle_winding,
                "target_direction": direction,
                "output_orientation": orientation,
            },
            "frames": {
                "attachment": {key: list(value)
                               for key, value in attachment_frame.items()},
                "source": {key: list(value) for key, value in source_frame.items()},
                "origin": list(ankle_centre),
            },
            "source_form": {
                "input_schema": "creature-kernel.connected-leg-assembly-foot-form-inputs.v1",
                "case_id": form["case_id"],
                "construction": copy.deepcopy(form["construction"]),
                "local_controls": copy.deepcopy(controls),
                "reference_y": controls["reference_y"],
                "reference_y_usage": "contact-plane measurement only; no floor projection",
                "centre_rule": "piecewise-linear H/R/M/B/T local centres",
                "radius_rule": "rL linear except R-to-M uses rise_width_exponent; rD/rP linear",
                "normal_rule": "N=normalize(tangent cross attachment_frame.X)",
                "cross_section_rule": "top/bottom use rounded q-section and distinct rD/rP local-normal radii",
                "joint_rule": "R is ankle-body surface centre and is not a joint; actual A remains attachment origin",
                "row_derivation": "rows use the explicit FOOT-004 formulas and adjacent-secant tangent rule",
            },
            "binding": "no weights introduced; future foot vertices inherit corresponding shank influence",
        }
        if connector["metadata"]:
            metadata["feet"][side]["connector"] = connector["metadata"]
        index_mapping[f"{side}_foot_new_vertices"] = list(new_vertices)
        index_mapping[f"{side}_foot_new_faces"] = list(foot_faces)

    metadata["base_vertex_count"] = len(base_control_owners)
    metadata["index_mapping"] = index_mapping
    metadata["scheme"] = copy.deepcopy(metadata.get("scheme", {}))
    metadata["scheme"]["foot_form"] = {
        "candidate": "FOOT-004 rounded longitudinal source/form grid",
        "source_controls": list(_ANCHORS),
        "rows": list(_ROW_FORMULAS),
        "lateral_fractions": list(_LATERAL_FRACTIONS),
        "hole": "reuse FOOT-003 row-2 centre omission and eight-vertex boundary",
        "outer_perimeter": "reuse FOOT-003 22-quad closure",
        "attachment": "reuse actual ankle phase/winding and collar_fraction=.20",
        "frame": "origin actual A, X validated ankle attachment_frame.X, U projected global +Y, F=X cross U",
        "radii": "local-normal rL/rD/rP; top and bottom remain distinct",
        "evaluator": "read-only current connected-leg generic Catmull-Clark evaluator",
    }
    output = {
        "schema": "creature-kernel.connected-leg-assembly-foot-form-mesh.v1",
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
    _shared._validate_output(output, base_mesh, base_vertex_count, base_face_count,
                             new_face_indices_by_side)
    return output


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Reuse FOOT-003's current generic connected-leg evaluator."""
    return _shared.evaluate(mesh, levels=levels)


__all__ = ["FootFormConstructionError", "build", "evaluate"]

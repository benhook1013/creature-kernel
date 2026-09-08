"""Bounded connected-tail host adapter for the connected-leg experiment.

This is intentionally local to the current source-built mesh.  It pins one
pelvis host quad, replaces that quad in place with an inset annulus, and
appends a small capped tail.  It does not infer a universal pelvis region,
modify the source construction, assign weights, or add a tail joint.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy
import math
from typing import Any

import construction


_HOST_FACE_INDEX = 58
_HOST_VERTEX_INDICES = (41, 44, 66, 63)
_HOST_OWNER = "domain.pelvis"
_TAIL_OWNER = "domain.tail"
_INSET_FRACTION = 0.4
_TAIL_RING_COUNT = 5
_COORDINATE_TOLERANCE = 1.0e-10
_NORMAL_TOLERANCE = 1.0e-12


class TailConstructionError(ValueError):
    """Raised when the explicit local tail host or candidate is incoherent."""


def _fail(message: str) -> None:
    raise TailConstructionError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be a mapping")
    return value


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{where} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        _fail(f"{where} must be a finite number")
    return result


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        _fail(f"{where} must be a three-component vector")
    return tuple(_number(item, f"{where}[{index}]")
                 for index, item in enumerate(value))  # type: ignore[return-value]


def _normalise(value: tuple[float, float, float], where: str) -> tuple[float, float, float]:
    length = math.sqrt(sum(item * item for item in value))
    if not math.isfinite(length) or length <= _NORMAL_TOLERANCE:
        _fail(f"{where} must have positive finite length")
    return tuple(item / length for item in value)  # type: ignore[return-value]


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


def _bezier(control: tuple[tuple[float, float, float], ...], fraction: float) -> tuple[float, float, float]:
    one = 1.0 - fraction
    terms = (one ** 3, 3.0 * one * one * fraction,
             3.0 * one * fraction * fraction, fraction ** 3)
    return tuple(sum(terms[index] * control[index][axis] for index in range(4))
                 for axis in range(3))  # type: ignore[return-value]


def _bezier_tangent(control: tuple[tuple[float, float, float], ...], fraction: float,
                    where: str) -> tuple[float, float, float]:
    one = 1.0 - fraction
    value = tuple(
        3.0 * (one * one * (control[1][axis] - control[0][axis]) +
                2.0 * one * fraction * (control[2][axis] - control[1][axis]) +
                fraction * fraction * (control[3][axis] - control[2][axis]))
        for axis in range(3)
    )
    return _normalise(value, f"{where} tangent")


def _project_plus_x(tangent: tuple[float, float, float], where: str) -> tuple[float, float, float]:
    world_x = (1.0, 0.0, 0.0)
    return _normalise(_sub(world_x, _scale(tangent, _dot(world_x, tangent))),
                      f"{where} projected +X")


def _parse_controls(value: Any) -> dict[str, Any]:
    raw = _mapping(value, "tail_inputs")
    required = {"case_id", "enabled", "host_identity", "length",
                "terminal_direction", "radii", "station_fractions",
                "collar_distance", "binding_controls"}
    if set(raw) != required:
        _fail("tail_inputs has unsupported or missing fields")
    if not isinstance(raw["case_id"], str) or not raw["case_id"]:
        _fail("tail_inputs.case_id must be a non-empty string")
    if type(raw["enabled"]) is not bool:
        _fail("tail_inputs.enabled must be a boolean")
    host = _mapping(raw["host_identity"], "tail_inputs.host_identity")
    if set(host) != {"face_index", "vertex_indices", "owner"}:
        _fail("tail_inputs.host_identity has unsupported or missing fields")
    if type(host["face_index"]) is not int:
        _fail("tail_inputs.host_identity.face_index must be an integer")
    vertex_indices = host["vertex_indices"]
    if (not isinstance(vertex_indices, (list, tuple)) or
            tuple(vertex_indices) != _HOST_VERTEX_INDICES):
        _fail("tail_inputs.host_identity.vertex_indices does not match the pinned host")
    if host["owner"] != _HOST_OWNER:
        _fail("tail_inputs.host_identity.owner does not match the pinned host")
    if host["face_index"] != _HOST_FACE_INDEX:
        _fail("tail_inputs.host_identity.face_index does not match the pinned host")
    length = _number(raw["length"], "tail_inputs.length")
    if length <= 0.0:
        _fail("tail_inputs.length must be positive")
    direction = _normalise(_vector(raw["terminal_direction"],
                                   "tail_inputs.terminal_direction"),
                           "tail_inputs.terminal_direction")
    radii = _mapping(raw["radii"], "tail_inputs.radii")
    if set(radii) != {"base", "middle", "tip"}:
        _fail("tail_inputs.radii must contain base, middle, and tip")
    parsed_radii = {name: _number(radii[name], f"tail_inputs.radii.{name}")
                    for name in ("base", "middle", "tip")}
    if any(radius <= 0.0 for radius in parsed_radii.values()):
        _fail("tail_inputs.radii values must be positive")
    fractions = raw["station_fractions"]
    if (not isinstance(fractions, (list, tuple)) or
            len(fractions) != _TAIL_RING_COUNT):
        _fail("tail_inputs.station_fractions must contain five fractions")
    parsed_fractions = [_number(item, f"tail_inputs.station_fractions[{index}]")
                        for index, item in enumerate(fractions)]
    if (parsed_fractions[0] != 0.0 or parsed_fractions[-1] != 1.0 or
            any(left >= right for left, right in zip(parsed_fractions, parsed_fractions[1:]))):
        _fail("tail_inputs.station_fractions must increase from 0 to 1")
    collar_distance = _number(raw["collar_distance"], "tail_inputs.collar_distance")
    if collar_distance <= 0.0:
        _fail("tail_inputs.collar_distance must be positive")
    binding_controls = _mapping(raw["binding_controls"],
                                "tail_inputs.binding_controls")
    if set(binding_controls) != {"collar_blend_strength"}:
        _fail("tail_inputs.binding_controls must contain only collar_blend_strength")
    collar_blend_strength = _number(
        binding_controls["collar_blend_strength"],
        "tail_inputs.binding_controls.collar_blend_strength",
    )
    if not 0.0 <= collar_blend_strength <= 1.0:
        _fail("tail_inputs.binding_controls.collar_blend_strength must lie in [0, 1]")
    return {
        "case_id": raw["case_id"], "enabled": raw["enabled"],
        "host_identity": {
            "face_index": host["face_index"],
            "vertex_indices": list(vertex_indices), "owner": host["owner"],
        },
        "length": length, "terminal_direction": direction,
        "radii": parsed_radii, "station_fractions": parsed_fractions,
        "collar_distance": collar_distance,
        "binding_controls": {
            "collar_blend_strength": collar_blend_strength,
        },
    }


def _host_data(mesh: Mapping[str, Any], controls: Mapping[str, Any]) -> dict[str, Any]:
    vertices = mesh["vertices"]
    quads = mesh["quads"]
    owners = mesh["face_owners"]
    host = controls["host_identity"]
    face_index = host["face_index"]
    if face_index >= len(quads):
        _fail("source-built mesh does not contain the pinned tail host face")
    if face_index >= _mapping(mesh["metadata"], "source_mesh.metadata")["root"]["face_count"]:
        _fail("pinned tail host face is not in the source root")
    original_quad = list(quads[face_index])
    if original_quad != host["vertex_indices"]:
        _fail("source-built mesh tail host face vertices do not match the pinned identity")
    if owners[face_index] != host["owner"]:
        _fail("source-built mesh tail host face owner does not match the pinned identity")
    points = [tuple(float(value) for value in vertices[index])
              for index in original_quad]
    centre = _scale(tuple(sum(point[axis] for point in points) for axis in range(3)),
                    0.25)
    raw_normal = _add(_cross(_sub(points[1], points[0]), _sub(points[2], points[0])),
                      _cross(_sub(points[2], points[0]), _sub(points[3], points[0])))
    normal = _normalise(raw_normal, "pinned tail host normal")
    return {
        "face_index": face_index, "original_quad": original_quad,
        "owner": owners[face_index], "coordinates": [list(point) for point in points],
        "centre": list(centre), "normal": list(normal),
    }


def _radius_at(fraction: float, radii: Mapping[str, float]) -> float:
    if fraction <= 0.5:
        amount = fraction / 0.5
        return (1.0 - amount) * radii["base"] + amount * radii["middle"]
    amount = (fraction - 0.5) / 0.5
    return (1.0 - amount) * radii["middle"] + amount * radii["tip"]


def _convex_supports(new_indices: list[int], host_indices: list[int],
                     source_phase: list[list[int]]) -> dict[str, Any]:
    if len(host_indices) != 4 or len(source_phase) != 4:
        _fail("tail support derivation requires four host corners and four source phases")
    result: dict[str, Any] = {}
    for offset, index in enumerate(new_indices):
        corner = offset % 4
        weights = [0.15] * 4
        weights[corner] = 0.55
        result[str(index)] = {
            "host_vertex_indices": list(host_indices),
            "host_corner": corner,
            "source_phase": list(source_phase[corner]),
            "convex_weights": weights,
            "target_joint": "pelvis",
            "support_rule": "q=.4*P_i+.6*C; own corner=.55, other corners=.15",
        }
    return result


def build(source_mesh: Mapping[str, Any], tail_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Build one explicit host-58 tail candidate or return a disabled case unchanged."""
    mesh = _mapping(source_mesh, "source_mesh")
    construction._validate_mesh(mesh)
    controls = _parse_controls(tail_inputs)
    if not controls["enabled"]:
        return copy.deepcopy(dict(mesh))

    vertices = copy.deepcopy(mesh["vertices"])
    quads = [list(face) for face in mesh["quads"]]
    face_owners = list(mesh["face_owners"])
    control_owners = list(mesh["control_owners"])
    base_stencils = copy.deepcopy(mesh["base_stencils"])
    metadata = copy.deepcopy(dict(_mapping(mesh["metadata"], "source_mesh.metadata")))
    host = _host_data(mesh, controls)
    host_indices = host["original_quad"]
    points = [tuple(point) for point in host["coordinates"]]
    centre = tuple(host["centre"])
    normal = tuple(host["normal"])
    direction = controls["terminal_direction"]
    tangent0 = direction
    x0 = _project_plus_x(tangent0, "tail host path")
    v0 = _normalise(_cross(x0, tangent0), "tail host path ring axis")
    if _dot(normal, tangent0) <= _NORMAL_TOLERANCE:
        _fail("pinned tail host normal is incompatible with the rear/down path")

    source_phase: list[list[int]] = []
    for corner, point in enumerate(points):
        delta = _sub(point, centre)
        lateral = _dot(delta, x0)
        vertical = _dot(delta, v0)
        if abs(lateral) <= _COORDINATE_TOLERANCE or abs(vertical) <= _COORDINATE_TOLERANCE:
            _fail(f"pinned tail host corner {corner} has an ambiguous source phase")
        source_phase.append([1 if lateral > 0.0 else -1,
                             1 if vertical > 0.0 else -1])
    if len({tuple(phase) for phase in source_phase}) != 4:
        _fail("pinned tail host does not expose four distinct source phases")

    inset = [_add(centre, _scale(_sub(point, centre), _INSET_FRACTION))
             for point in points]
    translation = _scale(normal, controls["collar_distance"])
    collar = [_add(point, translation) for point in inset]
    collar_centre = _scale(tuple(sum(point[axis] for point in collar)
                                 for axis in range(3)), 0.25)
    length = controls["length"]
    terminal = _add(collar_centre, _scale(direction, length))
    control = (collar_centre,
               _add(collar_centre, _scale(direction, length / 3.0)),
               _add(collar_centre, _scale(direction, 2.0 * length / 3.0)),
               terminal)

    original_vertex_count = len(vertices)
    collar_indices = []
    for point in collar:
        collar_indices.append(len(vertices))
        vertices.append(list(point))
        control_owners.append(_TAIL_OWNER)
    ring_indices = [collar_indices]
    ring_frames = [{
        "fraction": 0.0,
        "centre": list(collar_centre),
        "tangent": list(tangent0), "X": list(x0), "V": list(v0),
        "radius": None, "source_phase": copy.deepcopy(source_phase),
    }]
    tail_new_indices = list(collar_indices)
    for fraction in controls["station_fractions"][1:]:
        centre_at = _bezier(control, fraction)
        tangent = _bezier_tangent(control, fraction, f"tail station {fraction}")
        x_axis = _project_plus_x(tangent, f"tail station {fraction}")
        v_axis = _normalise(_cross(x_axis, tangent),
                            f"tail station {fraction} ring axis")
        radius = _radius_at(fraction, controls["radii"])
        ring = []
        for lateral_phase, vertical_phase in source_phase:
            point = _add(centre_at,
                         _add(_scale(x_axis, lateral_phase * radius),
                              _scale(v_axis, vertical_phase * radius)))
            index = len(vertices)
            vertices.append(list(point))
            control_owners.append(_TAIL_OWNER)
            ring.append(index)
            tail_new_indices.append(index)
        ring_indices.append(ring)
        ring_frames.append({
            "fraction": fraction, "centre": list(centre_at),
            "tangent": list(tangent), "X": list(x_axis), "V": list(v_axis),
            "radius": radius, "source_phase": copy.deepcopy(source_phase),
        })

    annulus_faces = []
    for corner in range(4):
        next_corner = (corner + 1) % 4
        annulus_faces.append([
            host_indices[corner], host_indices[next_corner],
            collar_indices[next_corner], collar_indices[corner],
        ])
    tail_faces = []
    for source_ring, target_ring in zip(ring_indices, ring_indices[1:]):
        for corner in range(4):
            next_corner = (corner + 1) % 4
            tail_faces.append([
                source_ring[corner], source_ring[next_corner],
                target_ring[next_corner], target_ring[corner],
            ])
    cap_face = list(ring_indices[-1])
    original_face_count = len(quads)
    quads[_HOST_FACE_INDEX] = annulus_faces[0]
    face_owners[_HOST_FACE_INDEX] = _TAIL_OWNER
    for face in annulus_faces[1:] + tail_faces + [cap_face]:
        quads.append(face)
        face_owners.append(_TAIL_OWNER)
    for index in range(original_vertex_count, len(vertices)):
        base_stencils.append([[index, 1.0]])

    new_face_indices = [_HOST_FACE_INDEX] + list(
        range(original_face_count, len(quads)))
    annulus_face_indices = [_HOST_FACE_INDEX] + list(
        range(original_face_count, original_face_count + len(annulus_faces) - 1))
    tail_face_start = original_face_count + len(annulus_faces) - 1
    tail_face_indices = list(range(tail_face_start,
                                  tail_face_start + len(tail_faces)))
    cap_face_index = tail_face_start + len(tail_faces)

    index_mapping = copy.deepcopy(dict(
        _mapping(metadata.get("index_mapping", {}), "source_mesh.metadata.index_mapping")
    ))
    root_face_count = _mapping(metadata["root"], "source_mesh.metadata.root")["face_count"]
    index_mapping["root_face_mappings_excluding_tail_host"] = [
        [index, index] for index in range(root_face_count) if index != _HOST_FACE_INDEX
    ]
    index_mapping["tail_new_vertices"] = list(tail_new_indices)
    index_mapping["tail_new_faces"] = list(new_face_indices)
    index_mapping["tail_face_replacement"] = {
        "original_face_index": _HOST_FACE_INDEX,
        "original_quad": list(host_indices),
        "replacement_face_indices": list(annulus_face_indices),
        "one_to_many": [[_HOST_FACE_INDEX, *annulus_face_indices]],
        "original_host_retained": False,
    }
    metadata["index_mapping"] = index_mapping
    old_base_owners = list(metadata.get("base_control_owners", []))
    if len(old_base_owners) != len(mesh["vertices"]):
        _fail("source_mesh metadata base_control_owners does not cover the source vertices")
    metadata["base_control_owners"] = old_base_owners + [_TAIL_OWNER] * len(tail_new_indices)
    metadata["base_vertex_count"] = len(vertices)
    metadata["tail"] = {
        "owner": _TAIL_OWNER,
        "enabled": True,
        "host": {
            **host,
            "inset_fraction": _INSET_FRACTION,
            "inset_corners": [list(point) for point in inset],
            "collar_vertices": [list(point) for point in collar],
            "collar_translation": list(translation),
            "collar_distance": controls["collar_distance"],
            "source_phase": copy.deepcopy(source_phase),
        },
        "source_host_identity": copy.deepcopy(controls["host_identity"]),
        "ring_indices": copy.deepcopy(ring_indices),
        "ring_frames": ring_frames,
        "host_normal": list(normal),
        "source_phase": copy.deepcopy(source_phase),
        "frame_rule": "project global +X onto each cubic tangent plane; V=X cross tangent",
        "station_fractions": list(controls["station_fractions"]),
        "centreline": {
            "kind": "cubic_bezier",
            "control_points": [list(point) for point in control],
            "terminal_direction": list(direction),
            "length": length,
        },
        "radii": copy.deepcopy(controls["radii"]),
        "new_vertex_indices": list(tail_new_indices),
        "new_face_indices": list(new_face_indices),
        "annulus_face_indices": list(annulus_face_indices),
        "tail_face_indices": list(tail_face_indices),
        "cap_face_index": cap_face_index,
        "face_replacement": copy.deepcopy(index_mapping["tail_face_replacement"]),
        "transition_weights": {
            "status": "binding_declared_no_tail_joint",
            "future_target_joint": "pelvis",
            "collar_blend_strength": controls["binding_controls"]["collar_blend_strength"],
            "support_rule": "q=.4*P_i+.6*C; own corner=.55, other corners=.15",
            "supports": _convex_supports(
                tail_new_indices, host_indices, source_phase
            ),
        },
    }
    scheme = copy.deepcopy(dict(_mapping(metadata.get("scheme", {}),
                                         "source_mesh.metadata.scheme")))
    scheme["tail_adapter"] = {
        "adapter": "explicit pinned host-58 pelvis tail; not universal anatomy",
        "host_face_replacement": "replace slot 58 with first annulus face; append remaining annulus, tail sides, and cap",
        "root_geometry_preservation": "all inherited vertices and every non-host face remain exact",
        "tail_ring_count": _TAIL_RING_COUNT,
        "tail_joint": "not implemented",
        "binding": "pelvis-only transition; no tail joint",
    }
    metadata["scheme"] = scheme

    output = {
        "schema": "creature-kernel.connected-tail-assembly-mesh.v1",
        "level": mesh.get("level", 0),
        "vertices": vertices,
        "quads": quads,
        "face_owners": face_owners,
        "control_owners": control_owners,
        "loops": copy.deepcopy(mesh["loops"]),
        "base_stencils": base_stencils,
        "frames": copy.deepcopy(dict(mesh["frames"])),
        "metadata": metadata,
    }
    construction._validate_mesh(output)
    return output


__all__ = ["TailConstructionError", "build"]

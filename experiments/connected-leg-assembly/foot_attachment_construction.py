"""FOOT-005 attachment-only connector over the frozen FOOT-004 bulk producer.

The bulk source, grid arithmetic, source controls, phase, and winding come
from ``foot_form_construction``.  This module owns only the two support rings
between the existing ankle ring and existing dorsal hole.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy
import math
from typing import Any

import foot_construction as _shared
import foot_form_construction as _bulk


_SIDES = ("left", "right")
_RING_NAMES = ("support_s0", "support_s1")
_SECTOR_COUNT = 8
_COORDINATE_TOLERANCE = 1.0e-10
_AREA_TOLERANCE = 1.0e-12


AttachmentConstructionError = _shared.FootConstructionError


def _fail(message: str) -> None:
    raise AttachmentConstructionError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    return _shared._mapping(value, where)


def _finite(value: Any, where: str) -> float:
    return _shared._finite(value, where)


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
    if not math.isfinite(length) or length <= _COORDINATE_TOLERANCE:
        _fail(f"{where} must have positive finite length")
    return _scale(value, 1.0 / length)


def _parse_inputs(raw: Any) -> dict[str, Any]:
    value = _mapping(raw, "foot_attachment_inputs")
    if set(value) != {"schema", "status", "bulk_source", "connector", "budget"}:
        _fail("foot_attachment_inputs has unsupported or missing fields")
    if value["schema"] != "creature-kernel.connected-leg-assembly-foot-attachment-inputs.v1":
        _fail("foot_attachment_inputs schema is not FOOT-005")
    if value["status"] != "FOOT-005-initial-candidate-frozen":
        _fail("foot_attachment_inputs status is not the frozen initial candidate")
    bulk = _mapping(value["bulk_source"], "foot_attachment_inputs.bulk_source")
    if set(bulk) != {"module", "input", "callback_seam"}:
        _fail("foot_attachment_inputs.bulk_source has unsupported or missing fields")
    if (bulk["module"] != "foot_form_construction.py" or
            bulk["input"] != "foot-form-inputs.json" or
            bulk["callback_seam"] != "foot_form_construction.build.connector_builder"):
        _fail("FOOT-005 must reuse the settled FOOT-004 bulk producer and inputs")
    connector = _mapping(value["connector"], "foot_attachment_inputs.connector")
    expected_connector = {
        "ring_names", "chord_fraction", "edge_fraction", "incoming_fraction",
        "outside_fraction", "ray_fraction", "ray_origin_tolerance",
        "orientation_tolerance",
    }
    if set(connector) != expected_connector:
        _fail("foot_attachment_inputs.connector has unsupported or missing fields")
    if (type(connector["ring_names"]) not in (list, tuple) or
            list(connector["ring_names"]) != list(_RING_NAMES)):
        _fail("FOOT-005 connector must expose support_s0 and support_s1")
    parsed = {
        "chord_fraction": _finite(connector["chord_fraction"], "connector.chord_fraction"),
        "edge_fraction": _finite(connector["edge_fraction"], "connector.edge_fraction"),
        "incoming_fraction": _finite(connector["incoming_fraction"], "connector.incoming_fraction"),
        "outside_fraction": _finite(connector["outside_fraction"], "connector.outside_fraction"),
        "ray_fraction": _finite(connector["ray_fraction"], "connector.ray_fraction"),
        "ray_origin_tolerance": _finite(connector["ray_origin_tolerance"], "connector.ray_origin_tolerance"),
        "orientation_tolerance": _finite(connector["orientation_tolerance"], "connector.orientation_tolerance"),
    }
    if (parsed["chord_fraction"] != 1.0 / 3.0 or
            parsed["edge_fraction"] != 0.5 or
            parsed["incoming_fraction"] != 0.5 or
            parsed["outside_fraction"] != 0.5 or
            parsed["ray_fraction"] != 0.5):
        _fail("FOOT-005 connector length fractions differ from the settled formulas")
    if not parsed["ray_origin_tolerance"] > 0.0 or not parsed["orientation_tolerance"] > 0.0:
        _fail("FOOT-005 connector tolerances must be positive")
    budget = _mapping(value["budget"], "foot_attachment_inputs.budget")
    if set(budget) != {"initial_candidate_count", "shared_correction_max", "input_retuning", "hole_rim_edits"}:
        _fail("foot_attachment_inputs.budget has unsupported or missing fields")
    if budget != {
            "initial_candidate_count": 1,
            "shared_correction_max": 1,
            "input_retuning": False,
            "hole_rim_edits": False,
    }:
        _fail("FOOT-005 budget or freeze policy differs from the settled record")
    return parsed


def _ray_triangle(start: tuple[float, float, float], direction: tuple[float, float, float],
                  a: tuple[float, float, float], b: tuple[float, float, float],
                  c: tuple[float, float, float], origin_tolerance: float) -> float | None:
    edge1, edge2 = _sub(b, a), _sub(c, a)
    h = _cross(direction, edge2)
    determinant = _dot(edge1, h)
    if abs(determinant) <= _AREA_TOLERANCE:
        return None
    inverse = 1.0 / determinant
    source = _sub(start, a)
    u = inverse * _dot(source, h)
    if u < -_AREA_TOLERANCE or u > 1.0 + _AREA_TOLERANCE:
        return None
    q = _cross(source, edge1)
    v = inverse * _dot(direction, q)
    if v < -_AREA_TOLERANCE or u + v > 1.0 + _AREA_TOLERANCE:
        return None
    travel = inverse * _dot(edge2, q)
    if travel <= origin_tolerance:
        return None
    return travel


def _first_body_ray_hit(vertices: list[tuple[float, float, float]],
                        faces: list[tuple[int, int, int, int]],
                        start: tuple[float, float, float],
                        direction: tuple[float, float, float],
                        origin_tolerance: float) -> float | None:
    hits: list[float] = []
    for face in faces:
        for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3])):
            hit = _ray_triangle(start, direction, vertices[triangle[0]],
                                vertices[triangle[1]], vertices[triangle[2]],
                                origin_tolerance)
            if hit is not None:
                hits.append(hit)
    return min(hits) if hits else None


def _quad_area_vector(vertices: list[tuple[float, float, float]],
                      face: tuple[int, int, int, int]) -> tuple[float, float, float]:
    return _add(
        _cross(_sub(vertices[face[1]], vertices[face[0]]),
               _sub(vertices[face[2]], vertices[face[0]])),
        _cross(_sub(vertices[face[2]], vertices[face[0]]),
               _sub(vertices[face[3]], vertices[face[0]])),
    )


def _mean(points: list[tuple[float, float, float]], where: str) -> tuple[float, float, float]:
    if not points:
        _fail(f"{where} has no points")
    return tuple(sum(point[index] for point in points) / len(points)
                 for index in range(3))  # type: ignore[return-value]


def _support_connector(context: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    side = context["side"]
    vertices = [tuple(point) for point in context["output_vertices"]]
    base_vertices = [tuple(point) for point in context["base_vertices"]]
    base_quads = [tuple(face) for face in context["base_quads"]]
    ankle_indices = list(context["semantic_ankle"])
    hole_indices = list(context["hole_indices"])
    retained_faces_by_name = context["retained_faces"]
    retained_faces = [tuple(face) for name in ("dorsal_grid", "plantar_grid", "outer_perimeter")
                      for face in retained_faces_by_name[name]]
    hole_set = set(hole_indices)
    chain = _mapping(context["base_mesh_metadata"]["chains"][side],
                     f"base_mesh.metadata.chains.{side}")
    ankle_loop = list(context["ankle_loop"])
    approach_loop = list(_mapping(chain["ring_indices_by_name"], "ankle ring metadata")["ankle_approach"])
    approach_by_ankle = dict(zip(ankle_loop, approach_loop))
    append_vertex = context["append_vertex"]
    orientation_tolerance = config["orientation_tolerance"]

    s0_points: list[tuple[float, float, float]] = []
    s1_points: list[tuple[float, float, float]] = []
    diagnostics: list[dict[str, Any]] = []
    for index in range(_SECTOR_COUNT):
        ankle = base_vertices[ankle_indices[index]]
        hole = vertices[hole_indices[index]]
        previous_ankle = base_vertices[approach_by_ankle[ankle_indices[index]]]
        d_in = _normalise(_sub(ankle, previous_ankle), f"{side} sector {index} incoming meridian")
        previous_hole = vertices[hole_indices[(index - 1) % _SECTOR_COUNT]]
        next_hole = vertices[hole_indices[(index + 1) % _SECTOR_COUNT]]
        t_boundary = _normalise(_sub(next_hole, previous_hole),
                                f"{side} sector {index} hole boundary tangent")

        incident_faces = [face for face in retained_faces if hole_indices[index] in face]
        if not incident_faces:
            _fail(f"{side} sector {index} hole has no retained incident foot faces")
        area_vector = _mean([_quad_area_vector(vertices, face) for face in incident_faces],
                            f"{side} sector {index} area vectors")
        n_area = _normalise(area_vector, f"{side} sector {index} retained area normal")
        outside_indices = sorted({
            neighbour for face in incident_faces for neighbour in face
            if neighbour not in hole_set
        })
        outside_centroid = _mean([vertices[neighbour] for neighbour in outside_indices],
                                 f"{side} sector {index} outside neighbours")
        outside_vector = _sub(outside_centroid, hole)
        outside_projection = _sub(outside_vector, _scale(n_area, _dot(outside_vector, n_area)))
        outside_projection = _normalise(
            outside_projection, f"{side} sector {index} projected outside direction"
        )
        c_out = _normalise(_cross(n_area, t_boundary),
                           f"{side} sector {index} outgoing conormal")
        outside_alignment = _dot(c_out, outside_projection)
        if abs(outside_alignment) <= orientation_tolerance:
            _fail(f"{side} sector {index} outgoing conormal orientation is ambiguous")
        if outside_alignment < 0.0:
            c_out = _scale(c_out, -1.0)
            outside_alignment = -outside_alignment

        chord = _sub(hole, ankle)
        chord_length = _norm(chord)
        if chord_length <= _COORDINATE_TOLERANCE:
            _fail(f"{side} sector {index} ankle-to-hole chord has no room")
        adjacent_edges = [
            _norm(_sub(base_vertices[ankle_indices[(index - 1) % 8]], ankle)),
            _norm(_sub(base_vertices[ankle_indices[(index + 1) % 8]], ankle)),
            _norm(_sub(vertices[hole_indices[(index - 1) % 8]], hole)),
            _norm(_sub(vertices[hole_indices[(index + 1) % 8]], hole)),
        ]
        if any(edge <= _COORDINATE_TOLERANCE for edge in adjacent_edges):
            _fail(f"{side} sector {index} has a degenerate adjacent A/H edge")
        edge_cap = config["edge_fraction"] * min(adjacent_edges)
        incoming_length = _norm(_sub(ankle, previous_ankle))
        outside_distances = [_norm(_sub(vertices[neighbour], hole))
                             for neighbour in outside_indices]
        outside_mean = sum(outside_distances) / len(outside_distances)
        l0_hit = _first_body_ray_hit(
            vertices, retained_faces, ankle, d_in, config["ray_origin_tolerance"]
        )
        l1_hit = _first_body_ray_hit(
            vertices, retained_faces, hole, _scale(c_out, -1.0),
            config["ray_origin_tolerance"]
        )
        l0_candidates = {
            "chord_third": config["chord_fraction"] * chord_length,
            "half_adjacent_A_H_edge": edge_cap,
            "half_incoming_meridian": config["incoming_fraction"] * incoming_length,
        }
        if l0_hit is not None:
            l0_candidates["half_first_positive_body_ray_hit"] = config["ray_fraction"] * l0_hit
        l1_candidates = {
            "chord_third": config["chord_fraction"] * chord_length,
            "half_adjacent_A_H_edge": edge_cap,
            "half_mean_outside_neighbour_distance": config["outside_fraction"] * outside_mean,
        }
        if l1_hit is not None:
            l1_candidates["half_first_positive_body_ray_hit"] = config["ray_fraction"] * l1_hit
        l0 = min(l0_candidates.values())
        l1 = min(l1_candidates.values())
        if l0 <= _COORDINATE_TOLERANCE or l1 <= _COORDINATE_TOLERANCE:
            _fail(f"{side} sector {index} has no positive bounded connector length")
        s0 = _add(ankle, _scale(d_in, l0))
        s1 = _sub(hole, _scale(c_out, l1))
        s0_points.append(s0)
        s1_points.append(s1)
        chord_unit = _normalise(chord, f"{side} sector {index} chord")
        diagnostics.append({
            "sector": index,
            "name": _bulk._HOLE_BOUNDARY_NAMES[index],
            "ankle_index": ankle_indices[index],
            "hole_index": hole_indices[index],
            "approach_index": approach_by_ankle[ankle_indices[index]],
            "d_in": list(d_in),
            "boundary_previous_direction": list(_normalise(_sub(hole, previous_hole),
                                                            f"{side} sector {index} previous boundary")),
            "boundary_next_direction": list(_normalise(_sub(next_hole, hole),
                                                        f"{side} sector {index} next boundary")),
            "boundary_tangent": list(t_boundary),
            "n_area": list(n_area),
            "c_out": list(c_out),
            "outside_neighbour_indices": outside_indices,
            "outside_alignment_dot": outside_alignment,
            "chord_length": chord_length,
            "chord_dot_d_in": _dot(chord_unit, d_in),
            "chord_dot_c_out": _dot(chord_unit, c_out),
            "adjacent_A_H_edge_lengths": adjacent_edges,
            "incoming_meridian_length": incoming_length,
            "outside_mean_neighbour_distance": outside_mean,
            "first_body_ray_hit_in": l0_hit,
            "first_body_ray_hit_out": l1_hit,
            "l0_candidates": l0_candidates,
            "l1_candidates": l1_candidates,
            "l0": l0,
            "l1": l1,
        })

    for name, ring in (("support_s0", s0_points), ("support_s1", s1_points)):
        if len(ring) != _SECTOR_COUNT or any(
                _norm(_sub(ring[(index + 1) % _SECTOR_COUNT], ring[index]))
                <= _COORDINATE_TOLERANCE for index in range(_SECTOR_COUNT)):
            _fail(f"{side} {name} has a degenerate ring edge")
    s0_indices = [append_vertex(point) for point in s0_points]
    s1_indices = [append_vertex(point) for point in s1_points]
    orientation = context["orientation"]
    return {
        "ring_order": list(_RING_NAMES),
        "rings": {"support_s0": s0_indices, "support_s1": s1_indices},
        "band_order": ["ankle_to_s0", "s0_to_s1", "s1_to_hole"],
        "bands": {
            "ankle_to_s0": _shared._band(ankle_indices, s0_indices, orientation),
            "s0_to_s1": _shared._band(s0_indices, s1_indices, orientation),
            "s1_to_hole": _shared._band(s1_indices, hole_indices, orientation),
        },
        "metadata": {
            "candidate": "FOOT-005 two measured-support-ring attachment",
            "formula": "S0=A+l0*d_in; S1=H-l1*c_out",
            "length_rule": "min(chord/3, half adjacent A/H edge cap, respective half-neighbour cap, optional half first positive retained-body ray hit)",
            "ray_origin_rule": "strictly positive ray travel; t <= ray_origin_tolerance is ignored as an incident-origin hit",
            "orientation_rule": "c_out=normalize(n_area cross boundary_tangent), sign selected by projected outside-neighbour dot; zero/ambiguous fails",
            "diagnostic_policy": "chord/conormal/adjacent-direction dots are evidence only, not positive gates",
            "diagnostics": diagnostics,
            "source_lineage": "FOOT-004 rounded bulk grid and fixed ankle/hole endpoints; no source-control or binding changes",
            "gates": "shared quad-fold threshold, topology/orientation/degeneracy, ring, retained-body intersection, and later L2 surface checks",
        },
    }


def build(base_mesh: Mapping[str, Any], leg_inputs: Mapping[str, Any],
          foot_form_inputs: Mapping[str, Any],
          foot_attachment_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Build FOOT-005 using the live FOOT-004 bulk builder callback seam."""
    config = _parse_inputs(foot_attachment_inputs)
    metadata = _mapping(base_mesh["metadata"], "base_mesh.metadata")

    def connector_builder(context: Mapping[str, Any]) -> Mapping[str, Any]:
        enriched = dict(context)
        enriched["base_mesh_metadata"] = metadata
        return _support_connector(enriched, config)

    output = _bulk.build(
        base_mesh, leg_inputs, foot_form_inputs,
        connector_builder=connector_builder,
    )
    output = copy.deepcopy(output)
    output["schema"] = "creature-kernel.connected-leg-assembly-foot-attachment-mesh.v1"
    output_metadata = output["metadata"]
    output_metadata["scheme"] = copy.deepcopy(output_metadata.get("scheme", {}))
    output_metadata["scheme"]["foot_form"] = copy.deepcopy(
        output_metadata["scheme"].get("foot_form", {})
    )
    output_metadata["scheme"]["foot_form"]["attachment"] = (
        "bulk grid only; FOOT-005 supplies the attachment connector"
    )
    output_metadata["scheme"]["foot_attachment"] = {
        "candidate": "FOOT-005 two measured-support-ring attachment",
        "bulk_producer": "foot_form_construction.build with explicit connector_builder",
        "fixed_endpoints": "existing actual ankle ring and existing dorsal hole ring",
        "rings": ["support_s0", "support_s1"],
        "bands": ["ankle_to_s0", "s0_to_s1", "s1_to_hole"],
        "no_caps": True,
        "binding": "existing shank binding/source stencils unchanged; no new ankle articulation",
    }
    for side in _SIDES:
        foot = output_metadata["feet"][side]
        foot["attachment_candidate"] = copy.deepcopy(foot.pop("connector"))
        foot["attachment_candidate"]["input_schema"] = (
            "creature-kernel.connected-leg-assembly-foot-attachment-inputs.v1"
        )
    return output


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Reuse the current generic connected-leg evaluator."""
    return _bulk.evaluate(mesh, levels=levels)


__all__ = ["AttachmentConstructionError", "build", "evaluate"]

"""JUNCTION-001 direct ankle-port / proximal-cage foot construction.

This module owns one explicit local junction candidate.  It reuses only the
pure FOOT-004 source-frame and bulk-grid helpers; it does not call either
FOOT-004/005 builder and then repair its output.  The old eight-vertex dorsal
hole is a Dirichlet boundary for a coordinatewise harmonic displacement field.
The existing connected-leg ankle vertices remain the mouth vertices in the
result, so no collar or support ring is created here.

Execution, L2 evaluation, collision, and visual acceptance remain downstream
capture work.  This file deliberately has no post-L2 correction path.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy
import math
from typing import Any

import foot_construction as _shared
import foot_form_construction as _bulk


_SIDES = ("left", "right")
_COMPONENTS = ("X", "U", "F")
_ROW_COUNT = 8
_COLUMN_COUNT = 5
_HOLE_POSITIONS = tuple(_shared._HOLE_BOUNDARY_POSITIONS)
_CENTRE_POSITION = (2, 2)
_COORDINATE_TOLERANCE = 1.0e-8
_SOLVE_PIVOT_TOLERANCE = 1.0e-12
_FACE_AREA_TOLERANCE = 1.0e-12


class FootJunctionConstructionError(ValueError):
    """Raised when the explicit JUNCTION-001 contract is incoherent."""


def _fail(message: str) -> None:
    raise FootJunctionConstructionError(message)


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


def _add(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[index] + right[index] for index in range(3))  # type: ignore[return-value]


def _sub(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


def _scale(value: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(factor * item for item in value)  # type: ignore[return-value]


def _dot(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(left: tuple[float, float, float],
           right: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _norm(value: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(value, value))


def _edge_key(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _policy(raw: Any) -> dict[str, Any]:
    value = _mapping(raw, "junction_policy")
    required = {"schema", "candidate", "status", "source", "graph",
                "constraints", "output", "budget"}
    if set(value) != required:
        _fail("junction_policy has unsupported or missing fields")
    if value["schema"] != "creature-kernel.connected-leg-assembly-foot-junction-policy.v1":
        _fail("junction_policy schema is not JUNCTION-001 v1")
    if value["candidate"] != "JUNCTION-001":
        _fail("junction_policy candidate must be JUNCTION-001")
    if value["status"] != "prospective-static-only":
        _fail("junction_policy status must remain prospective-static-only")

    source = _mapping(value["source"], "junction_policy.source")
    if set(source) != {"bulk_origin", "pure_helpers", "forbidden_builders"}:
        _fail("junction_policy.source has unsupported or missing fields")
    if source["bulk_origin"] != "FOOT-004":
        _fail("junction_policy must use the FOOT-004 bulk source")
    if list(source["pure_helpers"]) != ["foot_form_construction._source_frame",
                                          "foot_form_construction._grid_points"]:
        _fail("junction_policy pure helper lineage is not the settled FOOT-004 seam")
    if list(source["forbidden_builders"]) != ["foot_form_construction.build",
                                               "foot_attachment_construction.build"]:
        _fail("junction_policy must forbid old builder-then-repair paths")

    graph = _mapping(value["graph"], "junction_policy.graph")
    if set(graph) != {"local_vertex_count", "body_quad_count", "row_names",
                      "columns", "frontier_row", "frontier_source", "hole_positions",
                      "omitted_position"}:
        _fail("junction_policy.graph has unsupported or missing fields")
    if graph["local_vertex_count"] != 79 or graph["body_quad_count"] != 74:
        _fail("junction_policy graph must be the 79-vertex/74-quad FOOT-004 bulk graph")
    if list(graph["row_names"]) != list(_bulk._ROW_NAMES):
        _fail("junction_policy row names do not match FOOT-004")
    if graph["columns"] != _COLUMN_COUNT or graph["frontier_row"] != 5 or graph["frontier_source"] != "M":
        _fail("junction_policy must keep row 5=M as the distal frontier")
    if [list(position) for position in graph["hole_positions"]] != [list(position) for position in _HOLE_POSITIONS]:
        _fail("junction_policy hole positions do not match FOOT-004")
    if list(graph["omitted_position"]) != list(_CENTRE_POSITION):
        _fail("junction_policy omitted centre does not match FOOT-004")

    constraints = _mapping(value["constraints"], "junction_policy.constraints")
    if set(constraints) != {"basis_order", "edge_weight", "fixed_rows", "plantar_u_rows",
                            "solver", "residual_tolerance"}:
        _fail("junction_policy.constraints has unsupported or missing fields")
    if list(constraints["basis_order"]) != list(_COMPONENTS):
        _fail("junction_policy basis order must be X/U/F")
    if constraints["edge_weight"] != "uniform_quad_edge":
        _fail("junction_policy must use uniform quad-edge weights")
    if list(constraints["fixed_rows"]) != [0, 5, 6, 7] or list(constraints["plantar_u_rows"]) != [1, 2, 3, 4]:
        _fail("junction_policy fixed rows do not preserve row 5=M and plantar rows 1..4")
    if constraints["solver"] != "coordinatewise_dirichlet_harmonic_no_regularizer":
        _fail("junction_policy solver is not the settled displacement solve")
    residual_tolerance = _finite(constraints["residual_tolerance"], "constraints.residual_tolerance")
    if not residual_tolerance > 0.0:
        _fail("constraints.residual_tolerance must be positive")

    output = _mapping(value["output"], "junction_policy.output")
    if set(output) != {"omit_old_hole_vertices", "use_existing_actual_A_indices",
                       "connector_rings", "post_l2_correction"}:
        _fail("junction_policy.output has unsupported or missing fields")
    if output["omit_old_hole_vertices"] is not True or output["use_existing_actual_A_indices"] is not True:
        _fail("junction_policy must use direct existing ankle-port vertices")
    if output["connector_rings"] is not False or output["post_l2_correction"] is not False:
        _fail("junction_policy cannot add connector rings or a post-L2 correction")

    budget = _mapping(value["budget"], "junction_policy.budget")
    if set(budget) != {"initial_candidate_count", "shared_correction_max",
                       "parameter_search", "input_retuning"}:
        _fail("junction_policy.budget has unsupported or missing fields")
    if budget["initial_candidate_count"] != 1 or budget["shared_correction_max"] != 1:
        _fail("junction_policy budget must be one initial candidate plus one correction")
    if budget["parameter_search"] is not False or budget["input_retuning"] is not False:
        _fail("junction_policy cannot authorize parameter search or input retuning")
    return copy.deepcopy(dict(value))


def _local_grid(grid: Mapping[str, Any]) -> dict[str, Any]:
    top_points = grid["top"]
    bottom_points = grid["bottom"]
    top: list[list[int | None]] = [[None] * _COLUMN_COUNT for _ in range(_ROW_COUNT)]
    bottom: list[list[int]] = [[] for _ in range(_ROW_COUNT)]
    points: list[tuple[float, float, float]] = []
    rows: list[int] = []
    regions: list[str] = []

    for row, row_points in enumerate(top_points):
        for column, point in enumerate(row_points):
            if (row, column) == _CENTRE_POSITION:
                continue
            index = len(points)
            top[row][column] = index
            points.append(tuple(point))
            rows.append(row)
            regions.append("dorsal")
    for row, row_points in enumerate(bottom_points):
        for point in row_points:
            index = len(points)
            bottom[row].append(index)
            points.append(tuple(point))
            rows.append(row)
            regions.append("plantar")
    if len(points) != 79:
        _fail(f"FOOT-004 local grid produced {len(points)} vertices, expected 79")
    if any(len(row) != _COLUMN_COUNT for row in bottom):
        _fail("FOOT-004 local plantar grid is not eight rows of five vertices")
    return {"top": top, "bottom": bottom, "points": points,
            "rows": rows, "regions": regions}


def _body_faces(local: Mapping[str, Any]) -> dict[str, list[tuple[int, int, int, int]]]:
    faces = {
        "dorsal_grid": _shared._top_grid_faces(local["top"]),
        "plantar_grid": _shared._bottom_grid_faces(local["bottom"]),
        "outer_perimeter": _shared._outer_grid_faces(local["top"], local["bottom"]),
    }
    if sum(len(value) for value in faces.values()) != 74:
        _fail("JUNCTION-001 local body graph does not contain 74 quads")
    return faces


def _adjacency(vertex_count: int, faces: list[tuple[int, int, int, int]]) -> list[set[int]]:
    adjacency = [set() for _ in range(vertex_count)]
    for face_index, face in enumerate(faces):
        if len(set(face)) != 4:
            _fail(f"local face {face_index} repeats a vertex")
        for corner, left in enumerate(face):
            right = face[(corner + 1) % 4]
            if left == right:
                _fail(f"local face {face_index} has a zero-length edge")
            adjacency[left].add(right)
            adjacency[right].add(left)
    if any(not neighbours for neighbours in adjacency):
        _fail("JUNCTION-001 local graph contains an unused vertex")
    return adjacency


def _components(adjacency: list[set[int]], nodes: set[int]) -> list[list[int]]:
    remaining = set(nodes)
    result: list[list[int]] = []
    while remaining:
        start = min(remaining)
        pending = [start]
        remaining.remove(start)
        component = []
        while pending:
            node = pending.pop()
            component.append(node)
            for neighbour in sorted(adjacency[node]):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    pending.append(neighbour)
        result.append(sorted(component))
    return result


def _solve_dense(matrix: list[list[float]], rhs: list[float], where: str,
                 residual_tolerance: float) -> tuple[list[float], float]:
    size = len(rhs)
    if size == 0:
        return [], 0.0
    augmented = [list(row) + [rhs[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        pivot = augmented[pivot_row][column]
        if not math.isfinite(pivot) or abs(pivot) <= _SOLVE_PIVOT_TOLERANCE:
            _fail(f"{where} has an undefined or singular harmonic system")
        if pivot_row != column:
            augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        for row in range(column + 1, size):
            factor = augmented[row][column] / augmented[column][column]
            if factor == 0.0:
                continue
            for entry in range(column, size + 1):
                augmented[row][entry] -= factor * augmented[column][entry]
    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        tail = augmented[row][size]
        for column in range(row + 1, size):
            tail -= augmented[row][column] * solution[column]
        solution[row] = tail / augmented[row][row]
        if not math.isfinite(solution[row]):
            _fail(f"{where} produced a non-finite displacement")
    residual = 0.0
    for row in range(size):
        residual = max(residual, abs(sum(matrix[row][column] * solution[column]
                                        for column in range(size)) - rhs[row]))
    if residual > residual_tolerance:
        _fail(f"{where} residual {residual} exceeds {residual_tolerance}")
    return solution, residual


def _harmonic_values(adjacency: list[set[int]], fixed: Mapping[int, float],
                     residual_tolerance: float, where: str) -> tuple[dict[int, float], dict[str, Any]]:
    vertex_count = len(adjacency)
    if any(index < 0 or index >= vertex_count for index in fixed):
        _fail(f"{where} has a fixed vertex outside the graph")
    free = set(range(vertex_count)) - set(fixed)
    values = {index: float(value) for index, value in fixed.items()}
    residuals: list[float] = []
    component_count = 0
    for component in _components(adjacency, free):
        component_count += 1
        component_set = set(component)
        boundary = sorted({neighbour for node in component
                           for neighbour in adjacency[node] if neighbour in fixed})
        if not boundary:
            _fail(f"{where} free component {component[0]} has no Dirichlet boundary")
        positions = {node: index for index, node in enumerate(component)}
        matrix = []
        rhs = []
        for node in component:
            row = [0.0] * len(component)
            row[positions[node]] = float(len(adjacency[node]))
            boundary_sum = 0.0
            for neighbour in sorted(adjacency[node]):
                if neighbour in component_set:
                    row[positions[neighbour]] -= 1.0
                elif neighbour in fixed:
                    boundary_sum += values[neighbour]
                else:  # pragma: no cover - adjacency is the source of both sets
                    _fail(f"{where} encountered an unclassified graph neighbour")
            matrix.append(row)
            rhs.append(boundary_sum)
        solution, residual = _solve_dense(
            matrix, rhs, f"{where} component {component[0]}", residual_tolerance
        )
        residuals.append(residual)
        values.update({node: solution[index] for node, index in positions.items()})
    return values, {
        "free_vertex_count": len(free),
        "fixed_vertex_count": len(fixed),
        "free_component_count": component_count,
        "max_residual": max(residuals, default=0.0),
    }


def _world_from_components(frame: Mapping[str, tuple[float, float, float]],
                           values: tuple[float, float, float]) -> tuple[float, float, float]:
    return _add(_add(_scale(frame["X"], values[0]), _scale(frame["U"], values[1])),
                _scale(frame["F"], values[2]))


def _displacements(local: Mapping[str, Any], faces: list[tuple[int, int, int, int]],
                   frame: Mapping[str, tuple[float, float, float]],
                   hole_local: list[int], hole_deltas: list[tuple[float, float, float]],
                   policy: Mapping[str, Any], side: str) -> tuple[list[tuple[float, float, float]], dict[str, Any]]:
    if len(hole_local) != len(hole_deltas) or len(hole_local) != 8:
        _fail(f"{side} junction needs eight hole/ankle displacement correspondences")
    adjacency = _adjacency(len(local["points"]), faces)
    rows = local["rows"]
    fixed_rows = tuple(policy["constraints"]["fixed_rows"])
    plantar_rows = tuple(policy["constraints"]["plantar_u_rows"])
    residual_tolerance = float(policy["constraints"]["residual_tolerance"])
    hole_values = {
        local_index: tuple(_dot(delta, frame[component]) for component in _COMPONENTS)
        for local_index, delta in zip(hole_local, hole_deltas)
    }
    component_values: dict[str, dict[int, float]] = {}
    solve_records: dict[str, dict[str, Any]] = {}
    for component_index, component in enumerate(_COMPONENTS):
        fixed: dict[int, float] = {}
        for index, row in enumerate(rows):
            if row in fixed_rows:
                fixed[index] = 0.0
        for index, delta in hole_values.items():
            if index in fixed:
                _fail(f"{side} hole displacement overlaps an all-coordinate fixed row")
            fixed[index] = delta[component_index]
        if component == "U":
            for index, row in enumerate(rows):
                if local["regions"][index] == "plantar" and row in plantar_rows:
                    if index in fixed and abs(fixed[index]) > _COORDINATE_TOLERANCE:
                        _fail(f"{side} plantar U constraint conflicts with a Dirichlet value")
                    fixed[index] = 0.0
        values, record = _harmonic_values(
            adjacency, fixed, residual_tolerance, f"{side} {component} displacement"
        )
        component_values[component] = values
        solve_records[component] = record

    displacements = [tuple(component_values[component][index]
                            for component in _COMPONENTS)
                     for index in range(len(local["points"]))]
    return displacements, {
        "basis_order": list(_COMPONENTS),
        "fixed_rows": list(fixed_rows),
        "plantar_u_rows": list(plantar_rows),
        "hole_local_displacements": [list(delta) for delta in hole_deltas],
        "hole_local_components": [list(hole_values[index]) for index in hole_local],
        "component_solves": solve_records,
        "max_residual": max(record["max_residual"] for record in solve_records.values()),
    }


def _triangle_normal(vertices: list[tuple[float, float, float]],
                     face: tuple[int, int, int, int], where: str) -> tuple[float, float, float]:
    first = _cross(_sub(vertices[face[1]], vertices[face[0]]),
                   _sub(vertices[face[2]], vertices[face[0]]))
    second = _cross(_sub(vertices[face[2]], vertices[face[0]]),
                    _sub(vertices[face[3]], vertices[face[0]]))
    if _norm(first) <= _FACE_AREA_TOLERANCE or _norm(second) <= _FACE_AREA_TOLERANCE:
        _fail(f"{where} has a degenerate triangle")
    if _dot(first, second) <= 0.0:
        _fail(f"{where} has a local quad fold")
    return first


def _validate_side_output(vertices: list[tuple[float, float, float]],
                          quads: list[tuple[int, int, int, int]],
                          new_faces: list[int], actual_loop: list[int], side: str) -> None:
    if len(new_faces) != 74:
        _fail(f"{side} JUNCTION-001 output does not contain 74 new body quads")
    for face_index in new_faces:
        face = quads[face_index]
        if len(set(face)) != 4:
            _fail(f"{side} junction face {face_index} repeats a mouth or body vertex")
        _triangle_normal(vertices, face, f"{side} junction face {face_index}")
    if len(set(actual_loop)) != 8:
        _fail(f"{side} ankle mouth repeats an existing port vertex")
    uses = _shared._edge_uses(quads)
    for index, left in enumerate(actual_loop):
        edge = _edge_key(left, actual_loop[(index + 1) % len(actual_loop)])
        if len(uses.get(edge, ())) != 2:
            _fail(f"{side} ankle mouth edge {edge} is not welded to exactly two quads")


def _map_local_face(face: tuple[int, int, int, int], local_to_output: Mapping[int, int],
                    hole_to_actual: Mapping[int, int], where: str) -> tuple[int, int, int, int]:
    mapped = tuple(hole_to_actual.get(index, local_to_output.get(index, -1)) for index in face)
    if any(index < 0 for index in mapped):
        _fail(f"{where} references a local vertex that was not retained or mapped to A")
    if len(set(mapped)) != 4:
        _fail(f"{where} maps to a duplicate output vertex")
    return mapped  # type: ignore[return-value]


def build(base_mesh: Mapping[str, Any], leg_inputs: Mapping[str, Any],
          foot_form_inputs: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    """Build JUNCTION-001 from an expanded connected-leg L0 and one FOOT-004 case."""
    settled_policy = _policy(policy)
    leg_rows = _shared._validate_leg_inputs(leg_inputs)
    form = _bulk._parse_form_inputs(foot_form_inputs)
    base_vertices, base_quads, base_loops, base_vertex_count, base_face_count = (
        _shared._validate_base_mesh(base_mesh, leg_rows)
    )
    base_metadata = _mapping(base_mesh["metadata"], "base_mesh.metadata")
    if base_metadata.get("feet") not in (None, {}):
        _fail("JUNCTION-001 expects an L0 without an already-attached foot")
    output_vertices = [list(point) for point in base_vertices]
    output_quads = [list(face) for face in base_quads]
    output_face_owners = list(base_mesh["face_owners"])
    output_control_owners = list(base_mesh["control_owners"])
    base_control_owners = list(base_metadata["base_control_owners"])
    if len(base_control_owners) != base_vertex_count:
        _fail("base_mesh metadata base_control_owners does not match the L0 prefix")
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
        source_frame = _bulk._source_frame(base_mesh, side, attachment_frame)
        controls = form["sides"][side]
        grid = _bulk._grid_points(
            ankle_centre, source_frame,
            {name: controls[name] for name in _bulk._ANCHORS},
            form["construction"], side,
        )
        local = _local_grid(grid)
        faces_by_name = _body_faces(local)
        body_faces = [face for name in ("dorsal_grid", "plantar_grid", "outer_perimeter")
                      for face in faces_by_name[name]]
        hole_local = [local["top"][row][column]
                      for row, column in _HOLE_POSITIONS]
        if any(index is None for index in hole_local):
            _fail(f"{side} JUNCTION-001 hole correspondence contains a missing local vertex")
        hole_local = [int(index) for index in hole_local]
        hole_points = [grid["top"][row][column] for row, column in _HOLE_POSITIONS]
        correspondence = _shared._correspondence(
            ankle_loop, base_vertices, ankle_centre, attachment_frame,
            hole_points, _shared._HOLE_BOUNDARY_NAMES, side,
        )
        semantic_ankle = list(correspondence["target_to_ankle_indices"])
        direction = int(correspondence["direction"])
        ankle_winding = _shared._loop_winding(base_quads, ankle_loop, side)
        if len(semantic_ankle) != len(ankle_loop) or set(semantic_ankle) != set(ankle_loop):
            _fail(f"{side} JUNCTION-001 correspondence is not a permutation of the ankle loop")
        if ankle_winding * direction != 1:
            _fail(f"{side} JUNCTION-001 direct mouth phase/winding is incompatible")
        # _correspondence already returns global vertex IDs, not offsets into
        # ankle_loop.  Keep its semantic phase/order while validating that it
        # is exactly a permutation of the declared port.
        actual_loop = list(semantic_ankle)
        hole_deltas = [_sub(base_vertices[actual_loop[index]], hole_points[index])
                       for index in range(8)]
        displacements, solve_metadata = _displacements(
            local, body_faces, source_frame, hole_local, hole_deltas,
            settled_policy, side,
        )
        moved_points = [
            _add(local["points"][index],
                 _world_from_components(source_frame, displacements[index]))
            for index in range(len(local["points"]))
        ]

        hole_to_actual = dict(zip(hole_local, actual_loop))
        local_to_output: dict[int, int] = {}
        new_vertices: list[int] = []
        for local_index, point in enumerate(moved_points):
            if local_index in hole_to_actual:
                continue
            output_index = len(output_vertices)
            local_to_output[local_index] = output_index
            output_vertices.append(list(point))
            output_control_owners.append(_shared._FOOT_OWNERS[side])
            base_control_owners.append(_shared._FOOT_OWNERS[side])
            new_vertices.append(output_index)

        new_faces: list[int] = []
        face_ranges: dict[str, list[int]] = {}
        for name in ("dorsal_grid", "plantar_grid", "outer_perimeter"):
            face_ranges[name] = []
            for face in faces_by_name[name]:
                mapped = _map_local_face(
                    face, local_to_output, hole_to_actual,
                    f"{side} {name} face",
                )
                output_face_owners.append(_shared._FOOT_OWNERS[side])
                output_quads.append(list(mapped))
                face_index = len(output_quads) - 1
                face_ranges[name].append(face_index)
                new_faces.append(face_index)
        output_vertices_typed = [_vector(point, f"output.vertices[{index}]")
                                 for index, point in enumerate(output_vertices)]
        output_quads_typed = [tuple(face) for face in output_quads]
        _validate_side_output(output_vertices_typed, output_quads_typed, new_faces,
                              actual_loop, side)
        new_face_indices_by_side[side] = new_faces

        old_grid_indices = {
            "dorsal": [list(row) for row in local["top"]],
            "plantar": [list(row) for row in local["bottom"]],
        }
        output_grid_indices = {
            "dorsal": [
                [None if index is None else (
                    hole_to_actual[index] if index in hole_to_actual
                    else local_to_output[index]
                )
                 for index in row]
                for row in local["top"]
            ],
            "plantar": [[local_to_output[index] for index in row]
                        for row in local["bottom"]],
        }
        source_baseline = {
            "case_id": form["case_id"],
            "construction": copy.deepcopy(form["construction"]),
            "local_controls": copy.deepcopy(controls),
            "longitudinal_rows": copy.deepcopy(grid["rows"]),
            "pure_helpers": ["foot_form_construction._source_frame",
                             "foot_form_construction._grid_points"],
            "control_semantics": {
                "H": "FOOT-004 rear heel surface-centre control",
                "R": "FOOT-004 ankle-body surface-centre control; not a joint",
                "rL_rD_rP": "FOOT-004 local-normal bulk-section radii; not mouth/aperture dimensions",
            },
            "coordinates": "authoritative FOOT-004 foot-rest X/U/F; U constraint is mixed-coordinate, not a full world-rest differential",
        }
        metadata["feet"][side] = {
            "owner": _shared._FOOT_OWNERS[side],
            "ankle_source_loop": list(ankle_loop),
            "junction_mouth_loop": list(actual_loop),
            "old_grid_indices": old_grid_indices,
            "output_grid_indices": output_grid_indices,
            "omitted_old_hole_local_indices": list(hole_local),
            "hole_boundary_positions": [list(position) for position in _HOLE_POSITIONS],
            "new_vertex_indices": list(new_vertices),
            "new_face_indices": list(new_faces),
            "face_owner_ranges": face_ranges,
            "correspondence": {
                "target_order": list(_shared._HOLE_BOUNDARY_NAMES),
                "old_hole_to_actual_A": [
                    {"old_local_index": hole_local[index],
                     "actual_A_index": actual_loop[index],
                     "old_point": list(hole_points[index]),
                     "actual_point": list(base_vertices[actual_loop[index]]),
                     "world_displacement": list(hole_deltas[index])}
                    for index in range(8)
                ],
                "direction": direction,
                "attached_ankle_loop_winding": ankle_winding,
            },
            "frames": {
                "attachment": {key: list(value) for key, value in attachment_frame.items()},
                "source": {key: list(value) for key, value in source_frame.items()},
                "origin": list(ankle_centre),
            },
            "source_baseline": source_baseline,
            "displacement_solve": solve_metadata,
            "method": {
                "candidate": "JUNCTION-001 direct owned-port plus coupled proximal-cage displacement",
                "graph": "79 FOOT-004 local vertices and 74 uniform quad-edge body faces",
                "frontier_row": "row 5=M; rows 5+ are all-coordinate Dirichlet zero",
                "plantar_constraint": "rows 1..4 hold local U displacement at zero; X/F remain harmonic unknowns",
                "hole_boundary": "actual A minus old H is prescribed in X/U/F",
                "output": "old H vertices omitted; existing A indices used directly; no collar/support connector rings",
                "binding": "incoming leg controls and A ownership/stencils/coordinates are unchanged; no ankle joint",
            },
            "gates": {
                "l0_topology_and_local_quad_fold": "implemented in this constructor",
                "l2_stencils_source_response_and_intersections": "pending captured downstream execution",
                "visual_and_anatomical_acceptance": "not evaluated",
            },
        }
        index_mapping[f"{side}_foot_junction_new_vertices"] = list(new_vertices)
        index_mapping[f"{side}_foot_junction_new_faces"] = list(new_faces)

    metadata["base_vertex_count"] = len(base_control_owners)
    metadata["index_mapping"] = index_mapping
    metadata["scheme"] = copy.deepcopy(metadata.get("scheme", {}))
    metadata["scheme"]["foot_junction"] = {
        "candidate": "JUNCTION-001",
        "source": "FOOT-004 pure source-frame/grid helpers",
        "graph": "79 local vertices, 74 body quads, row 5=M frontier",
        "displacement": "uniform quad-edge coordinatewise Dirichlet harmonic solve in foot-rest X/U/F",
        "mouth": "existing actual ankle A indices replace the eight old dorsal H slots",
        "connector_rings": False,
        "post_l2_correction": False,
    }
    output = {
        "schema": "creature-kernel.connected-leg-assembly-foot-junction-mesh.v1",
        "level": 0,
        "vertices": output_vertices,
        "quads": output_quads,
        "face_owners": output_face_owners,
        "control_owners": output_control_owners,
        "loops": output_loops,
        "base_stencils": copy.deepcopy(base_mesh["base_stencils"]) + [
            [[index, 1.0]] for index in range(base_vertex_count, len(output_vertices))
        ],
        "frames": copy.deepcopy(base_mesh["frames"]),
        "metadata": metadata,
    }
    if output["vertices"][:base_vertex_count] != [list(point) for point in base_mesh["vertices"]]:
        _fail("JUNCTION-001 changed the inherited L0 vertex prefix")
    if output["quads"][:base_face_count] != [list(face) for face in base_mesh["quads"]]:
        _fail("JUNCTION-001 changed the inherited L0 face prefix")
    output_vertices_typed = [_vector(point, f"output.vertices[{index}]")
                             for index, point in enumerate(output["vertices"])]
    output_quads_typed = [tuple(face) for face in output["quads"]]
    _shared._validate_topology(output_vertices_typed, output_quads_typed,
                               output["loops"], "JUNCTION-001 output")
    return output


__all__ = ["FootJunctionConstructionError", "build"]

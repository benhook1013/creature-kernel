"""Bounded, experiment-local perturbation evidence for connected-leg staging.

The helper in this module is deliberately separate from construction, binding,
and the runner.  It calls each collaborator exactly once per declared
perturbation, computes independent source/frame expectations, and returns
JSON-compatible records for a captured runner to serialize or render.  It
does not tune, repair, or call the real calibrated bodies during preparation.

The calf posterior metric treats a source-template seam as a numerical domain,
not as an anatomical threshold: a response is stable only when its projected
analytic displacement exceeds the baseline coordinate ULP bound.  Smaller
responses remain recorded as bounded ``indeterminate`` samples.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any


_PERTURBATION_IDS = (
    "left_A_y_minus_0.02",
    "left_calf_posterior_radius_times_1.10",
    "left_J_y_plus_0.01_at_hip15",
)
_SIDES = ("left", "right")
_SECTIONS = (
    "mid_thigh",
    "knee_pre_support",
    "knee",
    "knee_post_support",
    "calf",
    "ankle_approach",
    "ankle",
)
_SOURCE_FRACTIONS = (0.70, None, 1.0, None, 0.35, 0.72, 1.0)
_CALF_FRACTION = 0.35
_ANKLE_APPROACH_FRACTION = 0.72
_ROOT_EXIT_FRACTION = 0.45
_POST_KNEE_SUPPORT_MULTIPLIER = 1.2
_RING_SIZE = 8
_CALF_POSTERIOR_METRIC_DEFINITION = {
    "id": "calf-posterior-expansion-ulp-domain.v3",
    "stable_rule": (
        "projected analytic response in -localF exceeds the conservative "
        "baseline-coordinate ULP projection"
    ),
    "indeterminate_rule": (
        "responses at or below that ULP projection are recorded and actual "
        "response must remain within the same representability bound"
    ),
    "support_envelope": (
        "all L2 vertices with nonzero baseline stencil support from any of "
        "the eight L0 calf-ring controls; extent is measured from the fixed "
        "calf centre along -localF; this is not an exact planar calf section"
    ),
    "source_frame": "the baseline left K-to-A calf frame is used for every projection",
}


class PerturbationUnavailable(ValueError):
    """Raised when a collaborator or evidence input is incoherent."""


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PerturbationUnavailable(f"{where} must be a mapping")
    return value


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PerturbationUnavailable(f"{where} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise PerturbationUnavailable(f"{where} must be finite")
    return result


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise PerturbationUnavailable(f"{where} must be a three-component vector")
    return tuple(_number(item, f"{where}[{index}]")
                 for index, item in enumerate(value))  # type: ignore[return-value]


def _jsonable(value: Any) -> Any:
    """Convert collaborator output without allowing non-finite JSON values."""
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if type(value) is float:
        if not math.isfinite(value):
            raise PerturbationUnavailable("non-finite collaborator output")
        return value
    if type(value) is int or type(value) is bool or value is None or type(value) is str:
        return value
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return _jsonable(tolist())
    if isinstance(value, Real):
        result = float(value)
        if not math.isfinite(result):
            raise PerturbationUnavailable("non-finite collaborator output")
        return result
    raise PerturbationUnavailable(f"value of type {type(value).__name__} is not JSON-compatible")


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


def _unit(value: tuple[float, float, float], where: str) -> tuple[float, float, float]:
    length = _norm(value)
    if not math.isfinite(length) or length <= 0.0:
        raise PerturbationUnavailable(f"{where} has no finite positive length")
    return _scale(value, 1.0 / length)


def _lerp(left: tuple[float, float, float],
          right: tuple[float, float, float], fraction: float) -> tuple[float, float, float]:
    return _add(_scale(left, 1.0 - fraction), _scale(right, fraction))


def _max_abs(left: tuple[float, float, float],
             right: tuple[float, float, float]) -> float:
    return max(abs(left[axis] - right[axis]) for axis in range(3))


def _zero(value: tuple[float, float, float], tolerance: float) -> bool:
    return _norm(value) <= tolerance


def _mesh_vertices(mesh: Any, where: str) -> list[tuple[float, float, float]]:
    raw = _mapping(mesh, where).get("vertices")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise PerturbationUnavailable(f"{where}.vertices must be non-empty")
    return [_vector(point, f"{where}.vertices[{index}]")
            for index, point in enumerate(raw)]


def _quads(mesh: Any, where: str) -> list[list[int]]:
    raw = _mapping(mesh, where).get("quads")
    if not isinstance(raw, (list, tuple)):
        raise PerturbationUnavailable(f"{where}.quads must be a sequence")
    return [list(face) for face in raw]


def _stencil_rows(mesh: Any, where: str) -> list[list[tuple[int, float]]]:
    value = _mapping(mesh, where)
    raw = value.get("base_stencils", value.get("stencils"))
    if not isinstance(raw, (list, tuple)):
        raise PerturbationUnavailable(f"{where} has no full base stencils")
    result: list[list[tuple[int, float]]] = []
    for row_index, row in enumerate(raw):
        if not isinstance(row, (list, tuple)) or not row:
            raise PerturbationUnavailable(f"{where}.stencils[{row_index}] is empty")
        parsed: list[tuple[int, float]] = []
        for term_index, term in enumerate(row):
            if not isinstance(term, (list, tuple)) or len(term) != 2:
                raise PerturbationUnavailable(
                    f"{where}.stencils[{row_index}][{term_index}] is malformed"
                )
            index = term[0]
            if isinstance(index, bool) or not isinstance(index, int):
                raise PerturbationUnavailable("stencil index must be an integer")
            coefficient = _number(term[1], "stencil coefficient")
            if coefficient < 0.0:
                raise PerturbationUnavailable("stencil coefficient must be non-negative")
            parsed.append((index, coefficient))
        result.append(parsed)
    return result


def _loop(mesh: Any, name: str, where: str) -> list[int]:
    raw = _mapping(mesh, where).get("loops")
    if not isinstance(raw, Mapping) or name not in raw:
        raise PerturbationUnavailable(f"{where}.loops.{name} is unavailable")
    values = raw[name]
    if not isinstance(values, (list, tuple)) or not values:
        raise PerturbationUnavailable(f"{where}.loops.{name} is empty")
    return [int(index) for index in values]


def _root_loop(root: Any, side: str) -> list[int]:
    raw = _mapping(root, "root").get("loops")
    name = f"port.{side}_thigh"
    if isinstance(raw, Mapping) and name in raw:
        values = raw[name]
    else:
        metadata = _mapping(root, "root").get("metadata")
        transitions = _mapping(metadata, "root.metadata").get("transition_indices")
        row = _mapping(transitions, "root.metadata.transition_indices").get(side)
        values = _mapping(row, f"root.metadata.transition_indices.{side}").get("exit")
    if not isinstance(values, (list, tuple)) or len(values) != _RING_SIZE:
        raise PerturbationUnavailable(f"root {name} must contain eight vertices")
    return [int(index) for index in values]


def _frames_for_tangents(tangents: Sequence[tuple[float, float, float]]) -> list[dict[str, tuple[float, float, float]]]:
    previous_x: tuple[float, float, float] | None = None
    result = []
    for index, tangent in enumerate(tangents):
        x_axis = _unit(_sub((1.0, 0.0, 0.0),
                            _scale(tangent, _dot((1.0, 0.0, 0.0), tangent))),
                       f"source frame {index} projected +X")
        if previous_x is not None and _dot(x_axis, previous_x) < 0.0:
            x_axis = _scale(x_axis, -1.0)
        up_axis = _scale(tangent, -1.0)
        forward = _unit(_cross(x_axis, up_axis), f"source frame {index} forward")
        frame = {"tangent": tangent, "X": x_axis, "U": up_axis, "F": forward}
        result.append(frame)
        previous_x = x_axis
    return result


def _normalised_root_template(root: Any, side: str,
                              points: Mapping[str, tuple[float, float, float]],
                              tolerance: float) -> tuple[list[tuple[float, float]], tuple[float, float, float]]:
    vertices = _mesh_vertices(root, "root")
    loop = _root_loop(root, side)
    incoming = _unit(_sub(points["K"], points["T"]), f"{side} source T-K")
    frame = _frames_for_tangents([incoming])[0]
    exit_centre = _add(points["T"], _scale(_sub(points["K"], points["T"]), _ROOT_EXIT_FRACTION))
    projected: list[tuple[float, float]] = []
    lateral_radius = 0.0
    anterior_radius = 0.0
    posterior_radius = 0.0
    for vertex_index in loop:
        if vertex_index < 0 or vertex_index >= len(vertices):
            raise PerturbationUnavailable(f"root {side} loop index is out of range")
        delta = _sub(vertices[vertex_index], exit_centre)
        if abs(_dot(delta, incoming)) > tolerance:
            raise PerturbationUnavailable(f"root {side} loop is not in the source exit plane")
        lateral = _dot(delta, frame["X"])
        forward = _dot(delta, frame["F"])
        lateral_radius = max(lateral_radius, abs(lateral))
        anterior_radius = max(anterior_radius, forward)
        posterior_radius = max(posterior_radius, -forward)
        projected.append((lateral, forward))
    if min(lateral_radius, anterior_radius, posterior_radius) <= 0.0:
        raise PerturbationUnavailable(f"root {side} template has a degenerate radius")
    template = [
        (lateral / lateral_radius,
         forward / (anterior_radius if forward >= 0.0 else posterior_radius))
        for lateral, forward in projected
    ]
    return template, (lateral_radius, anterior_radius, posterior_radius)


_ROLE_METADATA_KEYS = ("J_role", "TK_source_role", "distal_design_status")


def _leg_values(value: Any) -> tuple[dict[str, dict[str, Any]], dict[str, float], dict[str, float]]:
    raw = _mapping(value, "leg_inputs")
    if set(raw) != set(_SIDES):
        raise PerturbationUnavailable("leg_inputs must contain exactly left and right sides")
    result = copy.deepcopy(dict(raw))
    factors: dict[str, float] = {}
    supports: dict[str, float] = {}
    for side in _SIDES:
        row = _mapping(result.get(side), f"leg_inputs.{side}")
        required = {"J", "T", "K", "A", "radii", "mid_thigh_factor",
                    "support_fraction", *_ROLE_METADATA_KEYS}
        if set(row) != required:
            raise PerturbationUnavailable(
                f"leg_inputs.{side} must use the canonical per-side fields and role metadata"
            )
        for name in ("J", "T", "K", "A"):
            _vector(row.get(name), f"leg_inputs.{side}.{name}")
        radii = _mapping(row.get("radii"), f"leg_inputs.{side}.radii")
        for name in ("knee", "calf", "ankle"):
            values = _vector(radii.get(name), f"leg_inputs.{side}.radii.{name}")
            if any(item <= 0.0 for item in values):
                raise PerturbationUnavailable(f"leg_inputs.{side}.radii.{name} must be positive")
        for name in _ROLE_METADATA_KEYS:
            if type(row[name]) is not str or not row[name]:
                raise PerturbationUnavailable(f"leg_inputs.{side}.{name} must be a non-empty string")
        factor = _number(row["mid_thigh_factor"], f"leg_inputs.{side}.mid_thigh_factor")
        support = _number(row["support_fraction"], f"leg_inputs.{side}.support_fraction")
        if factor < 0.0 or not 0.0 < support < 1.0:
            raise PerturbationUnavailable(f"leg_inputs.{side} factors are outside their declared domains")
        factors[side] = factor
        supports[side] = support
    return {side: result[side] for side in _SIDES}, factors, supports


def _apply_declared_change(value: Mapping[str, Any], spec: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = copy.deepcopy(dict(value))
    change = _mapping(spec.get("change"), f"perturbation {spec.get('id')}.change")
    path = str(change.get("path", ""))
    prefix = "cases[*].leg_inputs."
    if not path.startswith(prefix):
        raise PerturbationUnavailable(f"unsupported declared perturbation path: {path}")
    tail = path[len(prefix):]
    try:
        side, field_path = tail.split(".", 1)
        field, index_text = field_path.rsplit("[", 1)
        index = int(index_text.rstrip("]"))
    except (ValueError, TypeError):
        raise PerturbationUnavailable(f"malformed declared perturbation path: {path}")
    if side not in _SIDES:
        raise PerturbationUnavailable(f"unsupported perturbation side: {side}")
    target: Any = result[side]
    for part in field.split("."):
        target = target[part]
    old = _number(target[index], path)
    operation = change.get("operation")
    amount = _number(change.get("value"), f"{path} change")
    if operation == "add":
        new = old + amount
    elif operation == "multiply":
        new = old * amount
    else:
        raise PerturbationUnavailable(f"unsupported perturbation operation: {operation}")
    target[index] = new
    return result, {"path": path, "operation": operation, "old": old, "new": new}


def _source_plan(root: Any, legs: Mapping[str, Any], side: str,
                 factor: float, support: float, tolerance: float) -> dict[str, Any]:
    row = _mapping(legs[side], f"legs.{side}")
    points = {name: _vector(row[name], f"legs.{side}.{name}")
              for name in ("J", "T", "K", "A")}
    incoming = _unit(_sub(points["K"], points["T"]), f"{side} source T-K")
    outgoing = _unit(_sub(points["A"], points["K"]), f"{side} source K-A")
    knee_tangent = _unit(_add(incoming, outgoing), f"{side} source knee bisector")
    frames = _frames_for_tangents([
        incoming, incoming, knee_tangent, outgoing, outgoing, outgoing, outgoing
    ])
    template, exit_radii = _normalised_root_template(root, side, points, tolerance)
    fractions = (
        0.70,
        1.0 - support,
        1.0,
        _POST_KNEE_SUPPORT_MULTIPLIER * support,
        _CALF_FRACTION,
        _ANKLE_APPROACH_FRACTION,
        1.0,
    )
    centres = [
        _lerp(points["T"], points["K"], fractions[0]),
        _lerp(points["T"], points["K"], fractions[1]),
        points["K"],
        _lerp(points["K"], points["A"], fractions[3]),
        _lerp(points["K"], points["A"], fractions[4]),
        _lerp(points["K"], points["A"], fractions[5]),
        points["A"],
    ]
    radii = {name: _vector(_mapping(row["radii"], f"legs.{side}.radii")[name],
                           f"legs.{side}.radii.{name}")
             for name in ("knee", "calf", "ankle")}
    mid_radii = _scale(exit_radii, factor)
    section_radii: list[tuple[float, float, float]] = []
    for name, fraction in zip(_SECTIONS, fractions):
        if name in ("mid_thigh", "knee_pre_support", "knee"):
            if fraction <= 0.70:
                section_radii.append(_lerp(exit_radii, mid_radii,
                                           (fraction - 0.45) / 0.25))
            else:
                section_radii.append(_lerp(mid_radii, radii["knee"],
                                           (fraction - 0.70) / 0.30))
        elif fraction <= _CALF_FRACTION:
            section_radii.append(_lerp(radii["knee"], radii["calf"],
                                       fraction / _CALF_FRACTION))
        elif name == "ankle":
            section_radii.append(radii["ankle"])
        else:
            section_radii.append(_lerp(radii["calf"], radii["ankle"],
                                       (fraction - _CALF_FRACTION) / 0.65))
    section_points: list[list[tuple[float, float, float]]] = []
    for centre, section_radius, frame in zip(centres, section_radii, frames):
        ring = []
        for lateral, forward in template:
            depth_radius = section_radius[1] if forward >= 0.0 else section_radius[2]
            ring.append(_add(centre,
                             _scale(frame["X"], lateral * section_radius[0]),
                             _scale(frame["F"], forward * depth_radius)))
        section_points.append(ring)
    return {
        "points": points,
        "incoming": incoming,
        "outgoing": outgoing,
        "knee_tangent": knee_tangent,
        "template": template,
        "exit_radii": exit_radii,
        "fractions": fractions,
        "centres": centres,
        "radii": section_radii,
        "frames": frames,
        "section_points": section_points,
    }


def _ring_mapping(mesh: Any, side: str) -> dict[str, list[int]]:
    metadata = _mapping(_mapping(mesh, "mesh").get("metadata"), "mesh.metadata")
    chains = _mapping(metadata.get("chains"), "mesh.metadata.chains")
    chain = _mapping(chains.get(side), f"mesh.metadata.chains.{side}")
    sections = chain.get("sections")
    if not isinstance(sections, (list, tuple)) or len(sections) != len(_SECTIONS):
        raise PerturbationUnavailable(f"mesh.metadata.chains.{side}.sections is incomplete")
    result: dict[str, list[int]] = {}
    for name, raw in zip(_SECTIONS, sections):
        row = _mapping(raw, f"mesh.metadata.chains.{side}.{name}")
        values = row.get("indices")
        if not isinstance(values, (list, tuple)) or len(values) != _RING_SIZE:
            raise PerturbationUnavailable(f"mesh metadata ring {side}.{name} is incomplete")
        result[name] = [int(index) for index in values]
    return result


def _analytic_l0_vertices(baseline_l0: Any, root: Any,
                          legs: Mapping[str, Any],
                          factors: Mapping[str, float],
                          supports: Mapping[str, float],
                          tolerance: float) -> tuple[list[tuple[float, float, float]], dict[str, dict[str, list[int]]], dict[str, dict[str, Any]]]:
    vertices = _mesh_vertices(baseline_l0, "baseline_L0")
    ring_maps = {side: _ring_mapping(baseline_l0, side) for side in _SIDES}
    plans = {side: _source_plan(root, legs, side, factors[side], supports[side], tolerance)
             for side in _SIDES}
    expected = list(vertices)
    for side in _SIDES:
        for name, ring in ring_maps[side].items():
            expected_points = plans[side]["section_points"][_SECTIONS.index(name)]
            for index, point in zip(ring, expected_points):
                if index < 0 or index >= len(expected):
                    raise PerturbationUnavailable(f"analytic ring index {side}.{name} is out of range")
                expected[index] = point
    return expected, ring_maps, plans


def _delta(actual: Sequence[tuple[float, float, float]],
           baseline: Sequence[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    if len(actual) != len(baseline):
        raise PerturbationUnavailable("baseline and perturbed vertex counts differ")
    return [_sub(left, right) for left, right in zip(actual, baseline)]


def _max_delta_error(actual: Sequence[tuple[float, float, float]],
                     expected: Sequence[tuple[float, float, float]]) -> float:
    if len(actual) != len(expected):
        raise PerturbationUnavailable("actual and expected delta lengths differ")
    return max((_norm(_sub(left, right)) for left, right in zip(actual, expected)), default=0.0)


def _expected_l2_delta(l0_delta: Sequence[tuple[float, float, float]],
                       rest_l2: Any) -> list[tuple[float, float, float]]:
    rows = _stencil_rows(rest_l2, "baseline_L2")
    result = []
    for row in rows:
        result.append(_add(*(_scale(l0_delta[index], coefficient)
                             for index, coefficient in row)))
    return result


def _coordinate_ulps(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(math.ulp(float(value)) for value in point)  # type: ignore[return-value]


def _signed_ulp_bound(point: tuple[float, float, float],
                      direction: tuple[float, float, float]) -> float:
    """Bound a projected one-ULP coordinate change without a profile threshold."""
    ulps = _coordinate_ulps(point)
    return sum(abs(direction[index]) * ulps[index] for index in range(3))


def _calf_posterior_measurement(
        baseline_l0_vertices: Sequence[tuple[float, float, float]],
        actual_l0_delta: Sequence[tuple[float, float, float]],
        expected_l0_delta: Sequence[tuple[float, float, float]],
        calf_indices: Sequence[int],
        template: Sequence[tuple[float, float]],
        baseline_l2_vertices: Sequence[tuple[float, float, float]],
        baseline_l2_stencils: Sequence[Sequence[tuple[int, float]]],
        actual_l2_delta: Sequence[tuple[float, float, float]],
        expected_l2_delta: Sequence[tuple[float, float, float]],
        frame: Mapping[str, Any], centre: Any, tolerance: Any) -> dict[str, Any]:
    """Measure posterior response in a source-frame numerical domain.

    L0 records the exact eight-sample calf ring.  The L2 support envelope is
    every vertex with nonzero baseline stencil support from any of the eight
    calf controls, independent of observed or expected displacement.  Its
    before/after maximum extent is not a planar section.
    No sample is discarded: source samples and L2 support samples are each
    labelled stable, indeterminate, or direction-invalid.
    """
    if len(calf_indices) != _RING_SIZE or len(template) != _RING_SIZE:
        raise PerturbationUnavailable("calf ring and source template must contain eight samples")
    if (len(actual_l0_delta) != len(expected_l0_delta) or
            len(actual_l0_delta) != len(baseline_l0_vertices)):
        raise PerturbationUnavailable("L0 posterior measurement arrays do not cover the mesh")
    if (len(actual_l2_delta) != len(expected_l2_delta) or
            len(actual_l2_delta) != len(baseline_l2_vertices)):
        raise PerturbationUnavailable("L2 posterior measurement arrays do not cover the mesh")
    if len(baseline_l2_stencils) != len(baseline_l2_vertices):
        raise PerturbationUnavailable("L2 posterior measurement stencils do not cover the mesh")
    source_forward = _vector(_mapping(frame, "calf source frame").get("F"),
                             "calf source frame.F")
    direction = _scale(source_forward, -1.0)
    centre_point = _vector(centre, "calf source centre")
    comparison_tolerance = _number(tolerance, "calf comparison tolerance")
    if comparison_tolerance <= 0.0:
        raise PerturbationUnavailable("calf comparison tolerance must be positive")
    source_samples: list[dict[str, Any]] = []
    for slot, (vertex_index, local) in enumerate(zip(calf_indices, template)):
        if vertex_index < 0 or vertex_index >= len(baseline_l0_vertices):
            raise PerturbationUnavailable(f"calf sample {slot} is out of range")
        expected_signed = _dot(expected_l0_delta[vertex_index], direction)
        actual_signed = _dot(actual_l0_delta[vertex_index], direction)
        ulps = _coordinate_ulps(baseline_l0_vertices[vertex_index])
        ulp_bound = _signed_ulp_bound(baseline_l0_vertices[vertex_index], direction)
        if expected_signed > 0.0:
            if expected_signed > ulp_bound:
                domain = "posterior-stable"
                response_pass = actual_signed > 0.0
                response_status = "positive" if response_pass else "failed-nonpositive"
            else:
                domain = "posterior-indeterminate"
                response_pass = abs(actual_signed) <= ulp_bound
                response_status = (
                    "indeterminate-bounded" if response_pass
                    else "indeterminate-out-of-bound"
                )
        elif expected_signed == 0.0:
            domain = "zero-source-response"
            response_pass = True
            response_status = "outside-posterior-support"
        else:
            domain = "opposite-frame-response"
            response_pass = False
            response_status = "failed-opposite-frame"
        source_samples.append({
            "slot": slot,
            "l0_vertex_id": int(vertex_index),
            "template_local": [float(local[0]), float(local[1])],
            "expected_signed_minus_localF": expected_signed,
            "actual_signed_minus_localF": actual_signed,
            "coordinate_ulps": list(ulps),
            "projected_ulp_bound": ulp_bound,
            "domain": domain,
            "response_status": response_status,
            "pass": response_pass,
        })

    stable_source = [row for row in source_samples
                     if row["domain"] == "posterior-stable"]
    indeterminate_source = [row for row in source_samples
                            if row["domain"] == "posterior-indeterminate"]
    stable_source_extremum = max(
        stable_source, key=lambda row: row["expected_signed_minus_localF"],
        default=None,
    )

    calf_controls = set(calf_indices)
    support_samples: list[dict[str, Any]] = []
    for index, (baseline_point, stencil, actual_delta, expected_delta) in enumerate(
            zip(baseline_l2_vertices, baseline_l2_stencils,
                actual_l2_delta, expected_l2_delta)):
        if not any(base_index in calf_controls and coefficient != 0.0
                   for base_index, coefficient in stencil):
            continue
        expected_norm = _norm(expected_delta)
        expected_signed = _dot(expected_delta, direction)
        actual_signed = _dot(actual_delta, direction)
        ulps = _coordinate_ulps(baseline_point)
        ulp_bound = _signed_ulp_bound(baseline_point, direction)
        if expected_norm == 0.0:
            domain = "zero-source-response"
            response_pass = True
            response_status = "outside-posterior-response"
        elif expected_signed <= 0.0:
            domain = "opposite-frame-response"
            response_pass = False
            response_status = "failed-opposite-frame"
        elif expected_signed > ulp_bound:
            domain = "posterior-stable"
            response_pass = actual_signed > 0.0
            response_status = "positive" if response_pass else "failed-nonpositive"
        else:
            domain = "posterior-indeterminate"
            response_pass = abs(actual_signed) <= ulp_bound
            response_status = (
                "indeterminate-bounded" if response_pass
                else "indeterminate-out-of-bound"
            )
        support_samples.append({
            "l2_vertex_id": index,
            "expected_signed_minus_localF": expected_signed,
            "actual_signed_minus_localF": actual_signed,
            "expected_vector_norm": expected_norm,
            "baseline_extent_from_calf_centre_in_minus_localF": _dot(
                _sub(baseline_point, centre_point), direction
            ),
            "actual_extent_from_calf_centre_in_minus_localF": _dot(
                _sub(_add(baseline_point, actual_delta), centre_point), direction
            ),
            "coordinate_ulps": list(ulps),
            "projected_ulp_bound": ulp_bound,
            "domain": domain,
            "response_status": response_status,
            "pass": response_pass,
        })

    stable_support = [row for row in support_samples
                      if row["domain"] == "posterior-stable"]
    indeterminate_support = [row for row in support_samples
                             if row["domain"] == "posterior-indeterminate"]
    stable_support_extremum = max(
        stable_support, key=lambda row: row["expected_signed_minus_localF"],
        default=None,
    )
    baseline_extent_row = max(
        support_samples,
        key=lambda row: row["baseline_extent_from_calf_centre_in_minus_localF"],
        default=None,
    )
    actual_extent_row = max(
        support_samples,
        key=lambda row: row["actual_extent_from_calf_centre_in_minus_localF"],
        default=None,
    )
    baseline_extent = (
        baseline_extent_row["baseline_extent_from_calf_centre_in_minus_localF"]
        if baseline_extent_row is not None else 0.0
    )
    actual_extent = (
        actual_extent_row["actual_extent_from_calf_centre_in_minus_localF"]
        if actual_extent_row is not None else 0.0
    )
    envelope_expansion = actual_extent - baseline_extent
    meaningful_expansion = envelope_expansion > comparison_tolerance
    source_pass = bool(stable_source) and all(
        row["pass"] for row in source_samples
    ) and stable_source_extremum is not None
    support_pass = bool(support_samples) and bool(stable_support) and all(
        row["pass"] for row in support_samples
    ) and stable_support_extremum is not None and meaningful_expansion
    return {
        "metric_definition": copy.deepcopy(_CALF_POSTERIOR_METRIC_DEFINITION),
        "source_frame_F": list(source_forward),
        "projection_direction": list(direction),
        "exact_planar_section": {
            "l0_calf_ring_vertex_ids": [int(index) for index in calf_indices],
            "definition": "the eight exact L0 calf-ring samples only",
        },
        "source_samples": source_samples,
        "stable_source_sample_count": len(stable_source),
        "indeterminate_source_sample_count": len(indeterminate_source),
        "stable_source_extremum": stable_source_extremum,
        "stable_source_responses_positive_or_bounded": source_pass,
        "support_envelope": {
            "definition": _CALF_POSTERIOR_METRIC_DEFINITION["support_envelope"],
            "l2_vertex_count": len(support_samples),
            "stable_vertex_count": len(stable_support),
            "indeterminate_vertex_count": len(indeterminate_support),
            "samples": support_samples,
            "stable_extremum": stable_support_extremum,
            "stable_responses_positive_or_bounded": support_pass,
            "baseline_extremum": None if baseline_extent_row is None else {
                "l2_vertex_id": baseline_extent_row["l2_vertex_id"],
                "extent_m": baseline_extent,
            },
            "actual_extremum": None if actual_extent_row is None else {
                "l2_vertex_id": actual_extent_row["l2_vertex_id"],
                "extent_m": actual_extent,
            },
            "extent_difference_m": envelope_expansion,
            "comparison_tolerance_m": comparison_tolerance,
            "actual_expansion_in_minus_localF": meaningful_expansion,
        },
        "pass": bool(source_pass and support_pass),
    }


def _topology_equal(left: Any, right: Any) -> bool:
    lmap, rmap = _mapping(left, "left mesh"), _mapping(right, "right mesh")
    if lmap.get("quads") != rmap.get("quads"):
        return False
    lloops, rloops = lmap.get("loops"), rmap.get("loops")
    return lloops == rloops


def _same_stencils(left: Any, right: Any) -> bool:
    try:
        return _stencil_rows(left, "left mesh") == _stencil_rows(right, "right mesh")
    except PerturbationUnavailable:
        return False


def _pose_only_j_metadata(mesh: Any, side: str, where: str) -> tuple[float, float, float]:
    """Read the one rest-mesh metadata field allowed to follow a J perturbation."""
    value = _mapping(mesh, where)
    metadata = _mapping(value.get("metadata"), f"{where}.metadata")
    chains = _mapping(metadata.get("chains"), f"{where}.metadata.chains")
    chain = _mapping(chains.get(side), f"{where}.metadata.chains.{side}")
    if "pose_only_J" not in chain:
        raise PerturbationUnavailable(
            f"{where}.metadata.chains.{side}.pose_only_J is unavailable"
        )
    return _vector(chain["pose_only_J"],
                   f"{where}.metadata.chains.{side}.pose_only_J")


def _without_pose_only_j_metadata(mesh: Any, side: str, where: str) -> dict[str, Any]:
    """Copy a mesh while removing only the identified pose-only J field."""
    result = copy.deepcopy(dict(_mapping(mesh, where)))
    metadata = _mapping(result.get("metadata"), f"{where}.metadata")
    chains = _mapping(metadata.get("chains"), f"{where}.metadata.chains")
    chain = _mapping(chains.get(side), f"{where}.metadata.chains.{side}")
    if "pose_only_J" not in chain:
        raise PerturbationUnavailable(
            f"{where}.metadata.chains.{side}.pose_only_J is unavailable"
        )
    del chain["pose_only_J"]
    return result


def _compare_rest_construction(baseline: Any, actual: Any, side: str,
                               expected_J: Any, where: str) -> dict[str, Any]:
    """Compare rest construction exactly except the declared pose-only J field.

    The redaction is deliberately a single, structural path. Comparing the
    resulting dictionaries keeps vertices, quads, ports, stencils, frames,
    owners, and every other shape-bearing field exact; a changed or missing
    field cannot be hidden by this exception.
    """
    baseline_map = _mapping(baseline, f"{where}.baseline")
    actual_map = _mapping(actual, f"{where}.actual")
    expected = _vector(expected_J, f"{where}.expected pose-only J")
    baseline_j = _pose_only_j_metadata(baseline_map, side, f"{where}.baseline")
    actual_j = _pose_only_j_metadata(actual_map, side, f"{where}.actual")
    baseline_without_j = _without_pose_only_j_metadata(
        baseline_map, side, f"{where}.baseline")
    actual_without_j = _without_pose_only_j_metadata(
        actual_map, side, f"{where}.actual")

    vertices_equal = baseline_map.get("vertices") == actual_map.get("vertices")
    topology_equal = (
        baseline_map.get("quads") == actual_map.get("quads") and
        baseline_map.get("loops") == actual_map.get("loops")
    )
    stencil_keys = {"base_stencils", "stencils"} & (
        set(baseline_map) | set(actual_map)
    )
    stencils_equal = bool(stencil_keys) and all(
        baseline_map.get(key) == actual_map.get(key) for key in stencil_keys
    ) and {key for key in baseline_map if key in ("base_stencils", "stencils")} == {
        key for key in actual_map if key in ("base_stencils", "stencils")
    }
    all_other_fields_equal = baseline_without_j == actual_without_j
    pose_only_j_matches = actual_j == expected
    only_declared_metadata_changed = (
        all_other_fields_equal and pose_only_j_matches and actual_j != baseline_j
    )
    return {
        "vertices_equal": vertices_equal,
        "quads_and_ports_equal": topology_equal,
        "stencils_equal": stencils_equal,
        "all_other_fields_equal": all_other_fields_equal,
        "pose_only_J_matches_intended_source": pose_only_j_matches,
        "only_declared_pose_only_J_metadata_changed": only_declared_metadata_changed,
        "baseline_pose_only_J": list(baseline_j),
        "actual_pose_only_J": list(actual_j),
        "expected_pose_only_J": list(expected),
    }


def _metadata_centres(mesh: Any, side: str) -> list[tuple[float, float, float]]:
    metadata = _mapping(_mapping(mesh, "mesh").get("metadata"), "mesh.metadata")
    chain = _mapping(_mapping(metadata.get("chains"), "mesh.metadata.chains").get(side),
                     f"mesh.metadata.chains.{side}")
    sections = chain.get("sections")
    if not isinstance(sections, (list, tuple)) or len(sections) != len(_SECTIONS):
        raise PerturbationUnavailable(f"mesh metadata centres for {side} are unavailable")
    return [_vector(_mapping(row, f"{side} section").get("centre"),
                    f"{side} section centre") for row in sections]


def _mean(vertices: Sequence[tuple[float, float, float]]) -> tuple[float, float, float]:
    if not vertices:
        raise PerturbationUnavailable("cannot average an empty loop")
    return _scale(tuple(sum(point[axis] for point in vertices) for axis in range(3)),
                  1.0 / len(vertices))  # type: ignore[return-value]


def _check(checks: dict[str, Any], name: str, passed: bool, **details: Any) -> None:
    checks[name] = {"pass": bool(passed), **_jsonable(details)}


def _protocol_tolerance(protocol: Mapping[str, Any]) -> float:
    checks = _mapping(protocol.get("checks"), "protocol.checks")
    binding = _mapping(checks.get("binding_and_pose"), "protocol.checks.binding_and_pose")
    value = _number(binding.get("source_effect_response_max_abs_error"),
                    "protocol source effect tolerance")
    if value <= 0.0:
        raise PerturbationUnavailable("protocol source effect tolerance must be positive")
    return value


def _normalised_inputs(value: Any) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, float], dict[str, float]]:
    raw = _mapping(value, "leg_inputs")
    normalised = copy.deepcopy(dict(raw))
    legs, factors, supports = _leg_values(normalised)
    return normalised, legs, factors, supports


def _construct(root: Any, inputs: Mapping[str, Any], construction_module: Any) -> tuple[Any, Any, Any]:
    build = getattr(construction_module, "build", None)
    evaluate = getattr(construction_module, "evaluate", None)
    if not callable(build) or not callable(evaluate):
        raise PerturbationUnavailable("construction module lacks build/evaluate")
    built = build(copy.deepcopy(root), copy.deepcopy(dict(inputs)))
    levels = evaluate(built)
    if not isinstance(levels, (list, tuple)) or len(levels) < 2:
        raise PerturbationUnavailable("construction evaluator did not return L0 and L2")
    return built, levels[0], levels[-1]


def _bind(base: Any, rest: Any, root: Any, prior_binding: Any,
          inputs: Mapping[str, Any], binding_module: Any) -> Any:
    bind = getattr(binding_module, "bind", None)
    if not callable(bind):
        raise PerturbationUnavailable("binding module lacks bind")
    return bind(copy.deepcopy(base), copy.deepcopy(rest), copy.deepcopy(root),
                copy.deepcopy(prior_binding), copy.deepcopy(dict(inputs)))


def _record_exception(record: dict[str, Any], status: str, exc: Exception) -> dict[str, Any]:
    record["status"] = status
    record.setdefault("exceptions", []).append({
        "type": type(exc).__name__,
        "message": str(exc),
    })
    return record


def _base_record(spec: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(spec.get("id")),
        "status": "unavailable",
        "intermediate_input": {"before": _jsonable(inputs)},
        "expected": {},
        "checks": {},
        "diagnostic_meshes": {},
        "exceptions": [],
    }


def _run_A(record: dict[str, Any], spec: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    mutated, change = _apply_declared_change(context["inputs"], spec)
    record["intermediate_input"]["change"] = change
    record["intermediate_input"]["after"] = _jsonable(mutated)
    _normalised, mutated_legs, factors, supports = _normalised_inputs(mutated)
    built, l0, l2 = _construct(context["root"], _normalised, context["construction"])
    record["diagnostic_meshes"].update({"built_L0": _jsonable(built),
                                        "perturbed_L0": _jsonable(l0),
                                        "perturbed_L2": _jsonable(l2)})
    binding = _bind(l0, l2, context["root"], context["prior_binding"],
                    _normalised, context["binding"])
    record["binding"] = _jsonable(binding)

    expected_l0, ring_maps, plans = _analytic_l0_vertices(
        context["baseline_L0"], context["root"], mutated_legs, factors, supports,
        context["tolerance"]
    )
    baseline_vertices = _mesh_vertices(context["baseline_L0"], "baseline_L0")
    actual_vertices = _mesh_vertices(l0, "perturbed_L0")
    actual_delta = _delta(actual_vertices, baseline_vertices)
    expected_delta = _delta(expected_l0, context["baseline_expected_L0"])
    ankle_index = _SECTIONS.index("ankle")
    left_plan = plans["left"]
    left_ankle_mean = _mean(left_plan["section_points"][ankle_index])
    ankle_loop = _loop(l2, "port.left_ankle", "perturbed_L2")
    ankle_points = [_mesh_vertices(l2, "perturbed_L2")[index] for index in ankle_loop]
    outgoing = left_plan["outgoing"]
    ankle_frame = left_plan["frames"][ankle_index]
    A = left_plan["points"]["A"]
    ankle_radii = left_plan["radii"][ankle_index]
    expected_l0_mesh = copy.deepcopy(context["baseline_L0"])
    expected_l0_mesh["vertices"] = [list(point) for point in expected_l0]
    record["expected"].update({
        "source_section_centres": {
            side: [list(point) for point in plans[side]["centres"]]
            for side in _SIDES
        },
        "changed_source_sections": [
            name for name, before, after in zip(
                _SECTIONS, context["plans"]["left"]["centres"], plans["left"]["centres"]
            ) if not _zero(_sub(after, before), context["tolerance"])
        ],
        "ankle_expected_world_loop_mean": list(left_ankle_mean),
        "open_boundary_mean_rule": (
            "Each Catmull-Clark open-boundary level emits old boundary vertices "
            "and edge midpoints; the arithmetic loop mean is preserved."
        ),
        "ankle_source_frame": {key: list(value) for key, value in ankle_frame.items()},
        "ankle_radii": list(ankle_radii),
        "l0_delta": [list(point) for point in expected_delta],
    })
    record["diagnostic_meshes"]["expected_L0"] = _jsonable(expected_l0_mesh)
    checks = record["checks"]
    _check(checks, "topology_unchanged",
           _topology_equal(context["baseline_L0"], l0) and
           _topology_equal(context["baseline_L2"], l2),
           correspondence="same face/loop topology; support locality uses full stencils")
    _check(checks, "source_driven_l0_response",
           _max_delta_error(actual_delta, expected_delta) <= context["tolerance"],
           max_abs_error=_max_delta_error(actual_delta, expected_delta),
           tolerance=context["tolerance"])
    _check(checks, "source_section_centres_follow_TKA",
           all(_max_abs(actual, expected) <= context["tolerance"]
               for side in _SIDES
               for actual, expected in zip(
                   _metadata_centres(l0, side), plans[side]["centres"])),
           metadata_is_diagnostic_only=True)
    l2_mean = _mean(ankle_points)
    _check(checks, "l2_ankle_mean_matches_analytic_l0_mean",
           _max_abs(l2_mean, left_ankle_mean) <= context["tolerance"],
           actual=list(l2_mean), expected=list(left_ankle_mean),
           tolerance=context["tolerance"])
    coplanar = max((abs(_dot(_sub(point, A), outgoing)) for point in ankle_points),
                   default=math.inf)
    _check(checks, "ankle_boundary_coplanar_with_source_KA_frame",
           coplanar <= context["tolerance"], max_abs_plane_residual=coplanar,
           tolerance=context["tolerance"])
    within = True
    envelope_residual = 0.0
    for point in ankle_points + [A]:
        local = _sub(point, A)
        lateral = abs(_dot(local, ankle_frame["X"]))
        forward = _dot(local, ankle_frame["F"])
        depth = ankle_radii[1] if forward >= 0.0 else ankle_radii[2]
        envelope_residual = max(envelope_residual,
                                lateral - ankle_radii[0], abs(forward) - depth)
        within = within and lateral <= ankle_radii[0] + context["tolerance"]
        within = within and abs(forward) <= depth + context["tolerance"]
    _check(checks, "A_within_ankle_radial_envelope", within,
           max_envelope_residual=envelope_residual,
           tolerance=context["tolerance"])
    root_count = len(_mesh_vertices(context["root"], "root"))
    root_unchanged = all(_zero(actual_delta[index], context["tolerance"])
                         for index in range(min(root_count, len(actual_delta))))
    _check(checks, "upper_root_unaffected_by_source_A", root_unchanged,
           proof="original root vertex prefix compared by preserved face topology")
    support_indices = {index for index, point in enumerate(expected_delta)
                       if not _zero(point, context["tolerance"])}
    far_root = all(_zero(actual_delta[index], context["tolerance"])
                   for index in range(len(actual_delta)) if index not in support_indices)
    _check(checks, "contralateral_and_far_L0_unchanged", far_root,
           support_index_count=len(support_indices))
    baseline_l2_vertices = _mesh_vertices(context["baseline_L2"], "baseline_L2")
    l2_vertices = _mesh_vertices(l2, "perturbed_L2")
    l2_rows = _stencil_rows(context["baseline_L2"], "baseline_L2")
    far_l2_indices = [index for index, row in enumerate(l2_rows)
                      if not any(base_index in support_indices for base_index, _ in row)]
    far_l2 = all(_zero(_sub(l2_vertices[index], baseline_l2_vertices[index]),
                        context["tolerance"]) for index in far_l2_indices)
    _check(checks, "far_L2_unchanged_by_full_stencil_support", far_l2,
           far_vertex_count=len(far_l2_indices),
           correspondence="full L2 stencil support; not old/new vertex-ID inference")
    _check(checks, "full_L2_stencils_preserved", _same_stencils(context["baseline_L2"], l2))
    record["status"] = "pass" if all(item["pass"] for item in checks.values()) else "failed"


def _run_calf(record: dict[str, Any], spec: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    mutated, change = _apply_declared_change(context["inputs"], spec)
    record["intermediate_input"]["change"] = change
    record["intermediate_input"]["after"] = _jsonable(mutated)
    _normalised, mutated_legs, factors, supports = _normalised_inputs(mutated)
    built, l0, l2 = _construct(context["root"], _normalised, context["construction"])
    record["diagnostic_meshes"].update({"built_L0": _jsonable(built),
                                        "perturbed_L0": _jsonable(l0),
                                        "perturbed_L2": _jsonable(l2)})
    binding = _bind(l0, l2, context["root"], context["prior_binding"],
                    _normalised, context["binding"])
    record["binding"] = _jsonable(binding)
    expected_l0, ring_maps, plans = _analytic_l0_vertices(
        context["baseline_L0"], context["root"], mutated_legs, factors, supports,
        context["tolerance"]
    )
    baseline_expected, _, baseline_plans = _analytic_l0_vertices(
        context["baseline_L0"], context["root"], context["legs"],
        context["factors"], context["supports"], context["tolerance"]
    )
    expected_delta = _delta(expected_l0, baseline_expected)
    baseline_vertices = _mesh_vertices(context["baseline_L0"], "baseline_L0")
    actual_vertices = _mesh_vertices(l0, "perturbed_L0")
    actual_delta = _delta(actual_vertices, baseline_vertices)
    calf_coefficients: dict[str, float] = {}
    for name, fraction in zip(_SECTIONS, plans["left"]["fractions"]):
        if name in ("mid_thigh", "knee_pre_support", "knee", "ankle"):
            coefficient = 0.0
        elif fraction <= _CALF_FRACTION:
            coefficient = fraction / _CALF_FRACTION
        else:
            coefficient = (1.0 - fraction) / (1.0 - _CALF_FRACTION)
        calf_coefficients[name] = coefficient
    posterior_input_delta = (
        _vector(mutated_legs["left"]["radii"]["calf"], "mutated calf")[2] -
        _vector(context["legs"]["left"]["radii"]["calf"], "baseline calf")[2]
    )
    explicit_delta = [(0.0, 0.0, 0.0) for _ in baseline_vertices]
    template = baseline_plans["left"]["template"]
    for name in ("knee_post_support", "calf", "ankle_approach"):
        coefficient = calf_coefficients[name]
        frame = baseline_plans["left"]["frames"][_SECTIONS.index(name)]
        for vertex_index, (_, forward) in zip(ring_maps["left"][name], template):
            if forward < 0.0:
                explicit_delta[vertex_index] = _scale(
                    frame["F"], forward * posterior_input_delta * coefficient
                )
    record["expected"].update({
        "piecewise_calf_posterior_coefficients": calf_coefficients,
        "analytic_L0_delta": [list(point) for point in explicit_delta],
        "posterior_template_direction": "negative forward-template vertices move in -localF",
    })
    l2_expected_delta = _expected_l2_delta(explicit_delta, context["baseline_L2"])
    baseline_l2_vertices = _mesh_vertices(context["baseline_L2"], "baseline_L2")
    actual_l2_vertices = _mesh_vertices(l2, "perturbed_L2")
    actual_l2_delta = _delta(actual_l2_vertices, baseline_l2_vertices)
    checks = record["checks"]
    _check(checks, "topology_unchanged",
           _topology_equal(context["baseline_L0"], l0) and
           _topology_equal(context["baseline_L2"], l2))
    l0_error = _max_delta_error(actual_delta, explicit_delta)
    _check(checks, "analytic_L0_parameter_response",
           l0_error <= context["tolerance"], max_abs_error=l0_error,
           tolerance=context["tolerance"])
    l2_error = _max_delta_error(actual_l2_delta, l2_expected_delta)
    _check(checks, "analytic_full_stencil_L2_response",
           l2_error <= context["tolerance"], max_abs_error=l2_error,
           tolerance=context["tolerance"],
           comparison="baseline full L2 stencils propagated from analytic L0 delta")
    _check(checks, "source_KA_frame_unchanged",
           baseline_plans["left"]["outgoing"] == plans["left"]["outgoing"] and
           baseline_plans["left"]["frames"] == plans["left"]["frames"])
    points_unchanged = all(
        _vector(mutated_legs[side][name], f"mutated {side}.{name}") ==
        _vector(context["legs"][side][name], f"baseline {side}.{name}")
        for side in _SIDES for name in ("J", "T", "K", "A")
    )
    _check(checks, "J_T_K_A_unchanged", points_unchanged)
    ankle_loop_before = _loop(context["baseline_L2"], "port.left_ankle", "baseline_L2")
    ankle_loop_after = _loop(l2, "port.left_ankle", "perturbed_L2")
    ankle_same = ankle_loop_before == ankle_loop_after and all(
        _zero(actual_l2_delta[index], context["tolerance"])
        for index in ankle_loop_after
    )
    _check(checks, "ankle_boundary_and_loop_mean_unchanged", ankle_same,
           reason="calf is an internal station, not an open boundary")
    root_count = len(_mesh_vertices(context["root"], "root"))
    root_same = all(_zero(actual_delta[index], context["tolerance"])
                    for index in range(min(root_count, len(actual_delta))))
    right_same = all(_zero(actual_delta[index], context["tolerance"])
                     for index in ring_maps["right"]["mid_thigh"] +
                     ring_maps["right"]["knee_pre_support"] +
                     ring_maps["right"]["knee"] +
                     ring_maps["right"]["knee_post_support"] +
                     ring_maps["right"]["calf"] +
                     ring_maps["right"]["ankle_approach"] +
                     ring_maps["right"]["ankle"])
    _check(checks, "root_and_other_leg_unchanged", root_same and right_same)
    calf_indices = ring_maps["left"]["calf"]
    calf_frame = baseline_plans["left"]["frames"][_SECTIONS.index("calf")]
    posterior_measurement = _calf_posterior_measurement(
        baseline_vertices, actual_delta, explicit_delta, calf_indices, template,
        baseline_l2_vertices,
        _stencil_rows(context["baseline_L2"], "baseline_L2"),
        actual_l2_delta, l2_expected_delta, calf_frame,
        baseline_plans["left"]["centres"][_SECTIONS.index("calf")],
        context["tolerance"],
    )
    record["metadata"] = {
        "measurement_definition": copy.deepcopy(
            _CALF_POSTERIOR_METRIC_DEFINITION
        ),
        "frozen_protocol_unchanged": True,
    }
    _check(checks, "signed_calf_posterior_expansion",
           posterior_measurement["pass"], **posterior_measurement)
    _check(checks, "full_L2_stencils_available",
           len(_stencil_rows(context["baseline_L2"], "baseline_L2")) == len(baseline_l2_vertices))
    record["diagnostic_meshes"]["expected_L2_delta"] = [list(point) for point in l2_expected_delta]
    record["status"] = "pass" if all(item["pass"] for item in checks.values()) else "failed"


def _rotation_about_axis(point: tuple[float, float, float],
                         pivot: tuple[float, float, float],
                         axis: tuple[float, float, float],
                         degrees: float) -> tuple[float, float, float]:
    radians = math.radians(degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    value = _sub(point, pivot)
    cross = _cross(axis, value)
    parallel = _scale(axis, _dot(axis, value))
    rotated = _add(_scale(value, cosine), _scale(cross, sine),
                   _scale(parallel, 1.0 - cosine))
    return _add(pivot, rotated)


def _hip_axis(J: tuple[float, float, float],
              K: tuple[float, float, float]) -> tuple[float, float, float]:
    y_axis = _unit(_sub(J, K), "independent hip J-K axis")
    return _unit(_sub((1.0, 0.0, 0.0),
                      _scale(y_axis, _dot((1.0, 0.0, 0.0), y_axis))),
                 "independent hip projected +X axis")


def _weights(binding: Any, count: int) -> list[list[float]]:
    raw = _mapping(binding, "binding").get("evaluated_weights")
    if not isinstance(raw, (list, tuple)) or len(raw) != count:
        raise PerturbationUnavailable("binding evaluated_weights do not cover L2")
    result = []
    for index, row in enumerate(raw):
        if not isinstance(row, (list, tuple)) or len(row) != 5:
            raise PerturbationUnavailable(f"binding evaluated_weights[{index}] must have five columns")
        result.append([_number(value, f"binding weight {index}") for value in row])
    return result


def _independent_hip_pose(vertices: Sequence[tuple[float, float, float]],
                          weights: Sequence[Sequence[float]],
                          J: tuple[float, float, float],
                          K: tuple[float, float, float],
                          hip_degrees: float) -> tuple[list[tuple[float, float, float]], tuple[float, float, float]]:
    axis = _hip_axis(J, K)
    result = []
    for point, row in zip(vertices, weights):
        transformed = _rotation_about_axis(point, J, axis, -hip_degrees)
        left_weight = row[1] + row[2]
        result.append(_add(_scale(point, 1.0 - left_weight),
                           _scale(transformed, left_weight)))
    return result, axis


def _pose_spec(protocol: Mapping[str, Any]) -> Mapping[str, Any]:
    poses = protocol.get("baseline_poses")
    if not isinstance(poses, (list, tuple)):
        raise PerturbationUnavailable("protocol baseline_poses is unavailable")
    for pose in poses:
        if isinstance(pose, Mapping) and pose.get("id") == "Lhip15_knee0":
            return pose
    raise PerturbationUnavailable("protocol does not declare Lhip15_knee0")


def _angles(pose: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    result = {}
    for side in _SIDES:
        row = _mapping(pose.get(side), f"pose.{side}")
        result[side] = {
            "hip": _number(row.get("hip"), f"pose.{side}.hip"),
            "knee": _number(row.get("knee"), f"pose.{side}.knee"),
            "ankle": _number(row.get("ankle", 0.0), f"pose.{side}.ankle"),
        }
    return result


def _run_J(record: dict[str, Any], spec: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    mutated, change = _apply_declared_change(context["inputs"], spec)
    record["intermediate_input"]["change"] = change
    record["intermediate_input"]["after"] = _jsonable(mutated)
    _normalised, mutated_legs, factors, supports = _normalised_inputs(mutated)
    built, l0, l2 = _construct(context["root"], _normalised, context["construction"])
    record["diagnostic_meshes"].update({"built_L0": _jsonable(built),
                                        "perturbed_L0": _jsonable(l0),
                                        "perturbed_L2": _jsonable(l2)})
    binding = _bind(l0, l2, context["root"], context["prior_binding"],
                    _normalised, context["binding"])
    record["binding"] = _jsonable(binding)
    checks = record["checks"]
    l0_rest = _compare_rest_construction(
        context["baseline_L0"], l0, "left", mutated_legs["left"]["J"],
        "rest_L0")
    l2_rest = _compare_rest_construction(
        context["baseline_L2"], l2, "left", mutated_legs["left"]["J"],
        "rest_L2")
    for level, comparison in (("L0", l0_rest), ("L2", l2_rest)):
        _check(
            checks, f"rest_{level}_shape_exactly_unchanged_except_pose_only_J",
            comparison["all_other_fields_equal"], **comparison,
        )
        _check(
            checks, f"rest_{level}_pose_only_J_matches_intended_source",
            comparison["pose_only_J_matches_intended_source"], **comparison,
        )
        _check(
            checks, f"rest_{level}_only_declared_pose_only_J_metadata_changed",
            comparison["only_declared_pose_only_J_metadata_changed"], **comparison,
        )
    baseline_l2_vertices = _mesh_vertices(context["baseline_L2"], "baseline_L2")
    base_weights = _weights(context["baseline_binding"], len(baseline_l2_vertices))
    perturbed_weights = _weights(binding, len(baseline_l2_vertices))
    _check(checks, "weights_exactly_unchanged", perturbed_weights == base_weights)
    pose = _pose_spec(context["protocol"])
    angles = _angles(pose)
    _check(checks, "declared_Lhip15_knee0_has_zero_knee", angles["left"]["knee"] == 0.0)
    pose_call = getattr(context["binding"], "pose", None)
    if not callable(pose_call):
        raise PerturbationUnavailable("binding module lacks pose")
    baseline_pose = pose_call(copy.deepcopy(context["baseline_L2"]),
                              copy.deepcopy(context["baseline_binding"]), angles)
    perturbed_pose = pose_call(copy.deepcopy(l2), copy.deepcopy(binding), angles)
    baseline_pose_vertices = _mesh_vertices(baseline_pose, "baseline pose")
    perturbed_pose_vertices = _mesh_vertices(perturbed_pose, "perturbed pose")
    expected_baseline, baseline_axis = _independent_hip_pose(
        baseline_l2_vertices, base_weights,
        _vector(context["legs"]["left"]["J"], "baseline left J"),
        _vector(context["legs"]["left"]["K"], "baseline left K"),
        angles["left"]["hip"],
    )
    expected_perturbed, perturbed_axis = _independent_hip_pose(
        baseline_l2_vertices, perturbed_weights,
        _vector(mutated_legs["left"]["J"], "perturbed left J"),
        _vector(mutated_legs["left"]["K"], "perturbed left K"),
        angles["left"]["hip"],
    )
    actual_response = _delta(perturbed_pose_vertices, baseline_pose_vertices)
    expected_response = _delta(expected_perturbed, expected_baseline)
    response_error = _max_delta_error(actual_response, expected_response)
    expected_pose_mesh = copy.deepcopy(perturbed_pose)
    expected_pose_mesh["vertices"] = [list(point) for point in expected_perturbed]
    record["diagnostic_meshes"].update({
        "baseline_pose": _jsonable(baseline_pose),
        "perturbed_pose": _jsonable(perturbed_pose),
        "expected_perturbed_pose": _jsonable(expected_pose_mesh),
    })
    record["expected"].update({
        "pose_id": pose.get("id"),
        "angles": _jsonable(angles),
        "independent_oracle": "Rodrigues rotation about projected +X perpendicular to J-K, with positive hip Rx(-angle); knee is not used as an oracle",
        "baseline_hip_axis": list(baseline_axis),
        "perturbed_hip_axis": list(perturbed_axis),
        "response": [list(point) for point in expected_response],
    })
    _check(checks, "independent_weighted_Rodrigues_pose_response",
           response_error <= context["tolerance"],
           max_abs_error=response_error, tolerance=context["tolerance"],
           oracle="independent weighted export, not binding.pose output")
    _check(checks, "rest_points_TKA_unchanged",
           all(_vector(mutated_legs[side][name], f"mutated {side}.{name}") ==
               _vector(context["legs"][side][name], f"baseline {side}.{name}")
               for side in _SIDES for name in ("T", "K", "A")))
    record["status"] = "pass" if all(item["pass"] for item in checks.values()) else "failed"


def run_case(root: Any, prior_rest: Any, prior_binding: Any,
             leg_inputs: Any, baseline_L0: Any, baseline_L2: Any,
             baseline_binding: Any, protocol: Any,
             construction_module: Any, binding_module: Any) -> dict[str, Any]:
    """Run exactly the three declared perturbations for one captured case.

    The function performs no real-body call by itself.  A captured runner may
    supply real collaborator modules; unit tests should supply synthetic ones.
    Any incoherent input or collaborator returns an explicit ``unavailable``
    record rather than silently treating a missing check as a pass.
    """
    result: dict[str, Any] = {
        "schema": "creature-kernel.connected-leg-assembly-perturbation-evidence.v1",
        "status": "unavailable",
        "declared_perturbation_ids": [],
        "perturbations": [],
        "exceptions": [],
    }
    try:
        protocol_map = _mapping(protocol, "protocol")
        raw_specs = protocol_map.get("input_perturbations")
        if not isinstance(raw_specs, (list, tuple)):
            raise PerturbationUnavailable("protocol.input_perturbations must be a list")
        specs = [_mapping(spec, "protocol perturbation") for spec in raw_specs]
        ids = [str(spec.get("id")) for spec in specs]
        result["declared_perturbation_ids"] = ids
        if ids != list(_PERTURBATION_IDS):
            raise PerturbationUnavailable(
                "protocol must declare exactly the three bounded perturbations in order"
            )
        tolerance = _protocol_tolerance(protocol_map)
        inputs, legs, factors, supports = _normalised_inputs(leg_inputs)
        # This source plan is an independent baseline reference, not expected
        # geometry copied from construction metadata.
        baseline_expected, _, baseline_plans = _analytic_l0_vertices(
            baseline_L0, root, legs, factors, supports, tolerance
        )
        _mesh_vertices(prior_rest, "prior_rest")
        _mesh_vertices(baseline_L2, "baseline_L2")
        _mesh_vertices(baseline_L0, "baseline_L0")
        context = {
            "root": root,
            "prior_rest": prior_rest,
            "prior_binding": prior_binding,
            "inputs": inputs,
            "legs": legs,
            "factors": factors,
            "supports": supports,
            "baseline_L0": baseline_L0,
            "baseline_L2": baseline_L2,
            "baseline_binding": baseline_binding,
            "protocol": protocol_map,
            "construction": construction_module,
            "binding": binding_module,
            "tolerance": tolerance,
            "plans": baseline_plans,
            "baseline_expected_L0": baseline_expected,
        }
        handlers = {
            _PERTURBATION_IDS[0]: _run_A,
            _PERTURBATION_IDS[1]: _run_calf,
            _PERTURBATION_IDS[2]: _run_J,
        }
        for spec in specs:
            record = _base_record(spec, inputs)
            try:
                handlers[str(spec["id"])](record, spec, context)
            except PerturbationUnavailable as exc:
                _record_exception(record, "unavailable", exc)
            except Exception as exc:  # explicit capture for runner serialization
                _record_exception(record, "unavailable", exc)
            result["perturbations"].append(record)
        statuses = [record["status"] for record in result["perturbations"]]
        if all(status == "pass" for status in statuses):
            result["status"] = "pass"
        elif any(status == "failed" for status in statuses):
            result["status"] = "failed"
        else:
            result["status"] = "unavailable"
        result["thresholds"] = {"analytic_response_tolerance": tolerance}
    except PerturbationUnavailable as exc:
        result["status"] = "unavailable"
        result["exceptions"].append({"type": type(exc).__name__, "message": str(exc)})
    except Exception as exc:
        result["status"] = "unavailable"
        result["exceptions"].append({"type": type(exc).__name__, "message": str(exc)})
    return _jsonable(result)


__all__ = ["PerturbationUnavailable", "run_case"]

"""Local owned-root pelvis/thigh transition construction.

This module is deliberately a small experiment-local seam.  It consumes the
predecessor's identity-free numeric component names and upper-context formula
authority, but owns the transition topology and subdivision implementation.
The returned meshes are plain mappings so the experiment does not inherit the
predecessor's frozen mesh class, profile admission, or validation gates.

base_stencils uses a sparse, sorted tuple representation:
((base_vertex_index, coefficient), ...).  Level zero is identity and each
later level contains the actual linear Catmull--Clark coefficients back to
those level-zero vertices.

``control_owners`` is only a dominant-owner display label for each evaluated
vertex.  The authoritative ownership and provenance are the base ownership
labels in metadata and the complete propagated ``base_stencils`` weights.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
_SOURCE_DIR = ROOT / "experiments" / "owned-root-assembly-successor"
_SOURCE_PATH = _SOURCE_DIR / "owned_root_surface.py"
_MESH_CORRECTNESS_PATH = _SOURCE_DIR / "mesh_correctness.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load experiment source module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_source() -> Any:
    # The predecessor uses a top-level mesh_correctness import when loaded
    # from its own directory.  Bind exactly that read-only dependency only
    # while loading the source module, then restore any caller-owned binding.
    marker = object()
    previous = sys.modules.get("mesh_correctness", marker)
    try:
        dependency = _load_module("_ck_transition_mesh_correctness",
                                  _MESH_CORRECTNESS_PATH)
        sys.modules["mesh_correctness"] = dependency
        return _load_module("_ck_transition_owned_root_surface", _SOURCE_PATH)
    finally:
        if previous is marker:
            sys.modules.pop("mesh_correctness", None)
        else:
            sys.modules["mesh_correctness"] = previous


_SOURCE = _load_source()

# This is the only component universe admitted by this local package.  In
# particular, attachments are semantic additions, not new carrier fields.
GEOMETRY_COMPONENT_IDS = tuple(_SOURCE.GEOMETRY_COMPONENT_IDS)

_SIDES = ("left", "right")
_SIDE_SIGN = {"left": -1.0, "right": 1.0}
_SIDE_DOMAIN = {
    "left": "domain.left_hip",
    "right": "domain.right_hip",
}
_SIDE_PORT = {
    "left": "port.left_thigh",
    "right": "port.right_thigh",
}
_SIDE_JUNCTION = {
    "left": "junction.pelvis__left_hip",
    "right": "junction.pelvis__right_hip",
}
_DOWN = (0.0, -1.0, 0.0)
_GLOBAL_X = (1.0, 0.0, 0.0)
_STENCIL_TOLERANCE = 1.0e-12


def _fail(message: str) -> None:
    raise ValueError(message)


def _finite_float(value: Any, where: str) -> float:
    if type(value) is not float or not math.isfinite(value):
        _fail(f"{where} must be a finite binary64 float")
    return value


def _vector(value: Any, where: str) -> tuple[float, float, float]:
    if type(value) not in (list, tuple) or len(value) != 3:
        _fail(f"{where} must be a three-component vector")
    return tuple(_finite_float(item, f"{where}[{index}]")
                 for index, item in enumerate(value))  # type: ignore[return-value]


def _positive(value: float, where: str) -> float:
    if not math.isfinite(value) or not value > 0.0:
        _fail(f"{where} must be positive and finite")
    return value


def _validate_inputs(
    components: dict[str, float],
    attachments: dict[str, dict[str, list[float]]],
) -> tuple[Any, dict[str, dict[str, tuple[float, float, float]]]]:
    if type(components) is not dict:
        _fail("components must be a dict")
    if set(components) != set(GEOMETRY_COMPONENT_IDS):
        _fail("components must use exactly GEOMETRY_COMPONENT_IDS")
    for component in GEOMETRY_COMPONENT_IDS:
        _finite_float(components[component], f"components[{component!r}]")

    if type(attachments) is not dict or set(attachments) != set(_SIDES):
        _fail("attachments must contain exactly left and right")
    checked: dict[str, dict[str, tuple[float, float, float]]] = {}
    for side in _SIDES:
        row = attachments[side]
        if type(row) is not dict or set(row) != {"centre", "knee"}:
            _fail(f"attachments[{side!r}] must contain exactly centre and knee")
        checked[side] = {
            field: _vector(row[field], f"attachments[{side!r}][{field!r}]")
            for field in ("centre", "knee")
        }

    carrier = _SOURCE.GeometryComponents(
        tuple(components[component] for component in GEOMETRY_COMPONENT_IDS)
    )
    for side in _SIDES:
        expected = tuple(
            _component(carrier, f"hips.{side}.P_s.{axis}")
            for axis in "xyz"
        )
        if checked[side]["centre"] != expected:
            _fail(f"attachments.{side}.centre must equal hips.{side}.P_s")
    return carrier, checked


def _dot(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _sub(left: tuple[float, float, float],
         right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


def _scale(value: tuple[float, float, float],
           factor: float) -> tuple[float, float, float]:
    return tuple(factor * item for item in value)  # type: ignore[return-value]


def _add(*values: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(value[index] for value in values) for index in range(3))  # type: ignore[return-value]


def _cross(left: tuple[float, float, float],
           right: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalise(value: tuple[float, float, float],
               where: str) -> tuple[float, float, float]:
    length = math.sqrt(_dot(value, value))
    if not math.isfinite(length) or not length > 0.0:
        _fail(f"{where} must have positive finite length")
    return _scale(value, 1.0 / length)


def _component(components: Any, name: str) -> float:
    return components.values[GEOMETRY_COMPONENT_IDS.index(name)]


def _station(components: Any, name: str) -> dict[str, Any]:
    prefix = f"stations.{name}"
    return {
        "C": tuple(_component(components, f"{prefix}.C.{axis}")
                   for axis in "xyz"),
        "rL": _component(components, f"{prefix}.rL"),
        "rA": _component(components, f"{prefix}.rA"),
        "rP": _component(components, f"{prefix}.rP"),
    }


def _hip_radius(components: Any, side: str, field: str) -> float:
    return _component(components, f"hips.{side}.{field}")


def _frame_and_dimensions(
    components: Any,
    attachments: dict[str, dict[str, tuple[float, float, float]]],
) -> dict[str, dict[str, Any]]:
    lower = _station(components, "lower_pelvis")
    for field in ("rL", "rA", "rP"):
        _positive(lower[field], f"stations.lower_pelvis.{field}")

    result: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        H = attachments[side]["centre"]
        knee = attachments[side]["knee"]
        delta = _sub(knee, H)
        length = math.sqrt(_dot(delta, delta))
        if not math.isfinite(length):
            _fail(f"attachments.{side} knee distance must be finite")
        _positive(length, f"attachments.{side} knee distance")
        d = _scale(delta, 1.0 / length)
        if not _dot(d, _DOWN) > 0.9:
            _fail(f"attachments.{side} thigh direction must be within the down-axis gate")

        projected_x = _sub(_GLOBAL_X, _scale(d, _dot(_GLOBAL_X, d)))
        X = _normalise(projected_x, f"attachments.{side} frame X")
        U = _scale(d, -1.0)
        F = _cross(X, U)

        rx = _positive(_hip_radius(components, side, "r_x"),
                       f"hips.{side}.r_x")
        _positive(_hip_radius(components, side, "r_y"),
                  f"hips.{side}.r_y")
        rz = _positive(_hip_radius(components, side, "r_z"),
                       f"hips.{side}.r_z")
        D = lower["C"][1] - H[1]
        _positive(D, f"{side} pelvis rise D")

        outward_radius = (
            lower["rL"] - abs(H[0] - lower["C"][0]) + rx
        ) / 2.0
        inward_radius = 1.10 * rx
        relative_z = lower["C"][2] - H[2]
        front_radius = (lower["rA"] + relative_z + rz) / 2.0
        back_radius = (lower["rP"] - relative_z + rz) / 2.0
        for name, value in (
            ("outward lateral radius", outward_radius),
            ("inward lateral radius", inward_radius),
            ("front depth radius", front_radius),
            ("back depth radius", back_radius),
        ):
            _positive(value, f"{side} {name}")

        E = _add(H, _scale(d, 0.45 * length))
        ring_b_centre = _add(H, _scale(d, 0.30 * length))
        result[side] = {
            "H": H,
            "knee": knee,
            "length": length,
            "d": d,
            "X": X,
            "U": U,
            "F": F,
            "exit": E,
            "ring_b_centre": ring_b_centre,
            "rx": rx,
            "ry": _hip_radius(components, side, "r_y"),
            "rz": rz,
            "D": D,
            "outward_sign": _SIDE_SIGN[side],
            "outward_radius": outward_radius,
            "inward_radius": inward_radius,
            "front_radius": front_radius,
            "back_radius": back_radius,
        }
    return result


def _perimeter(control_id: str, side: str) -> tuple[float, float]:
    i, _j, k = _SOURCE.COORDINATE_BY_CONTROL[control_id]
    u = float(i) - (1.0 if side == "left" else 4.0)
    q = float(k - 1)
    length = math.sqrt(u * u + q * q)
    if not length > 0.0:
        _fail(f"{control_id} is not a perimeter control")
    return u / length, q / length


def _socket_point(info: dict[str, Any],
                  a: float,
                  b: float) -> tuple[float, float, float]:
    lateral = (
        info["outward_radius"]
        if info["outward_sign"] * a > 0.0
        else info["inward_radius"]
    )
    depth = info["front_radius"] if b >= 0.0 else info["back_radius"]
    # r_y is proximal vertical flesh extent and is an explicit consumer.
    w = 0.5 * (1.0 + info["outward_sign"] * a)
    y = (
        info["H"][1] + w * (0.50 * info["D"] + 0.25 * info["ry"])
        - (1.0 - w) * 0.10 * info["length"]
    )
    return _add(
        (info["H"][0], y, info["H"][2]),
        _scale(info["X"], a * lateral),
        _scale(info["F"], b * depth),
    )


def _port_point(info: dict[str, Any],
                a: float,
                b: float,
                centre: tuple[float, float, float]) -> tuple[float, float, float]:
    return _add(
        centre,
        _scale(info["X"], a * info["rx"]),
        _scale(info["F"], b * info["rz"]),
    )


def _transition_rings(
    frames: dict[str, dict[str, Any]],
) -> dict[str, dict[str, list[tuple[float, float, float]]]]:
    result: dict[str, dict[str, list[tuple[float, float, float]]]] = {}
    for side in _SIDES:
        port_controls = tuple(_SOURCE.PORT_INFO[_SIDE_PORT[side]][2])
        junction_controls = tuple(_SOURCE.JUNCTION_TRACES[_SIDE_JUNCTION[side]])
        if len(port_controls) != len(junction_controls):
            _fail(f"{side} transition loops have different lengths")
        socket: list[tuple[float, float, float]] = []
        port: list[tuple[float, float, float]] = []
        ring_a: list[tuple[float, float, float]] = []
        ring_b: list[tuple[float, float, float]] = []
        for port_control, junction_control in zip(port_controls, junction_controls):
            a, b = _perimeter(port_control, side)
            if _perimeter(junction_control, side) != (a, b):
                _fail(f"{side} transition loops are not perimeter aligned")
            socket_point = _socket_point(frames[side], a, b)
            port_point = _port_point(frames[side], a, b, frames[side]["exit"])
            ring_b_point = _port_point(
                frames[side], a, b, frames[side]["ring_b_centre"]
            )
            socket.append(socket_point)
            port.append(port_point)
            ring_b.append(ring_b_point)
            ring_a.append(_scale(_add(socket_point, ring_b_point), 0.5))
        result[side] = {
            "socket": socket,
            "port": port,
            "ringA": ring_a,
            "ringB": ring_b,
        }
    return result


def _pelvic_abdominal_point(
    components: Any, i: float, k: float,
) -> tuple[float, float, float]:
    """Refinement 1: blend the j=1 station row onto a normalized ellipse."""
    u = (i - 2.5) / 2.5
    q = k - 1.0
    t = u * u
    denom = math.sqrt(u * u + q * q)
    if not denom > 0.0:
        _fail("j=1 control must have a nonzero perimeter direction")
    upper = _station(components, "upper_pelvis")
    abdomen = _station(components, "lower_abdomen")
    interior = (
        abdomen["C"][0],
        0.5 * (upper["C"][1] + abdomen["C"][1]),
        abdomen["C"][2],
    )
    centre = tuple(
        (1.0 - t) * interior[axis] + t * upper["C"][axis]
        for axis in range(3)
    )
    radii = {
        field: (1.0 - t) * abdomen[field] + t * upper[field]
        for field in ("rL", "rA", "rP")
    }
    return (
        centre[0] + u / denom * radii["rL"],
        centre[1],
        centre[2] + q / denom * radii["rA" if q >= 0.0 else "rP"],
    )


def _original_vertices(
    carrier: Any,
    transitions: dict[str, dict[str, list[tuple[float, float, float]]]],
) -> list[tuple[float, float, float]]:
    control_index = {
        control_id: index for index, control_id in enumerate(_SOURCE.CONTROL_IDS)
    }
    port_positions = {
        side: {
            control_id: index
            for index, control_id in enumerate(
                _SOURCE.PORT_INFO[_SIDE_PORT[side]][2]
            )
        }
        for side in _SIDES
    }
    junction_positions = {
        side: {
            control_id: index
            for index, control_id in enumerate(
                _SOURCE.JUNCTION_TRACES[_SIDE_JUNCTION[side]]
            )
        }
        for side in _SIDES
    }
    vertices: list[tuple[float, float, float]] = []
    for control_id in _SOURCE.CONTROL_IDS:
        i, j, k = _SOURCE.COORDINATE_BY_CONTROL[control_id]
        if j == -1:
            side = "left" if i <= 2 else "right"
            position = port_positions[side].get(control_id)
            if position is None:
                _fail(f"{control_id} is not in its declared thigh port")
            point = transitions[side]["port"][position]
        elif j == 0:
            side = "left" if i <= 2 else "right"
            position = junction_positions[side].get(control_id)
            if position is None:
                _fail(f"{control_id} is not in its declared hip junction")
            point = transitions[side]["socket"][position]
        elif j == 1:
            point = _pelvic_abdominal_point(carrier, i, k)
        else:
            # This is the settled upper-context source formula.  No
            # predecessor builder or validator is called here.
            _formula, _dependencies, point, _parameters = (
                _SOURCE._formula_for_control(carrier, control_id)
            )
            point = tuple(float(value) for value in point)
        if len(point) != 3 or any(not math.isfinite(value) for value in point):
            _fail(f"{control_id} produced a non-finite point")
        vertices.append(tuple(point))
    if len(vertices) != len(control_index):
        _fail("source control catalog changed while constructing vertices")
    return vertices


def _edge_key(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _transition_faces(
    base_vertices: list[tuple[float, float, float]],
    transitions: dict[str, dict[str, list[tuple[float, float, float]]]],
) -> tuple[Any, ...]:
    control_index = {
        control_id: index for index, control_id in enumerate(_SOURCE.CONTROL_IDS)
    }
    ring_indices: dict[str, dict[str, tuple[int, ...]]] = {}
    vertices = list(base_vertices)
    for side in _SIDES:
        ring_a = tuple(range(
            len(vertices), len(vertices) + len(transitions[side]["ringA"])
        ))
        vertices.extend(transitions[side]["ringA"])
        ring_b = tuple(range(
            len(vertices), len(vertices) + len(transitions[side]["ringB"])
        ))
        vertices.extend(transitions[side]["ringB"])
        ring_indices[side] = {"ringA": ring_a, "ringB": ring_b}

    port_indices = {
        side: {
            control_id: control_index[control_id]
            for control_id in _SOURCE.PORT_INFO[_SIDE_PORT[side]][2]
        }
        for side in _SIDES
    }
    junction_indices = {
        side: {
            control_id: control_index[control_id]
            for control_id in _SOURCE.JUNCTION_TRACES[_SIDE_JUNCTION[side]]
        }
        for side in _SIDES
    }
    port_positions = {
        side: {
            vertex_index: position
            for position, control_id in enumerate(
                _SOURCE.PORT_INFO[_SIDE_PORT[side]][2]
            )
            for vertex_index in (control_index[control_id],)
        }
        for side in _SIDES
    }
    quads: list[tuple[int, int, int, int]] = []
    owners: list[str] = []
    for _face_id, owner, controls in _SOURCE.FACE_RECORDS:
        face = tuple(control_index[control_id] for control_id in controls)
        side = next((candidate for candidate in _SIDES
                     if owner == _SIDE_DOMAIN[candidate]), None)
        if side is None:
            quads.append(face)  # type: ignore[arg-type]
            owners.append(owner)
            continue

        port_set = set(port_indices[side].values())
        junction_set = set(junction_indices[side].values())
        starts = [
            slot for slot in range(4)
            if face[slot] in port_set and face[(slot + 1) % 4] in port_set
        ]
        if len(starts) != 1:
            _fail("hip face does not expose one directed port edge")
        start = starts[0]
        # Rotation keeps the original directed cycle; no global inversion is
        # applied.  Its shape is p0,p1,j1,j0.
        p0, p1, j1, j0 = tuple(
            face[(start + offset) % 4] for offset in range(4)
        )
        if (
            p0 not in port_set or p1 not in port_set
            or j0 not in junction_set or j1 not in junction_set
        ):
            _fail("hip face is not a port-to-junction quad")
        a0 = ring_indices[side]["ringA"][port_positions[side][p0]]
        a1 = ring_indices[side]["ringA"][port_positions[side][p1]]
        b0 = ring_indices[side]["ringB"][port_positions[side][p0]]
        b1 = ring_indices[side]["ringB"][port_positions[side][p1]]
        quads.extend(((j1, j0, a0, a1),
                      (a1, a0, b0, b1),
                      (b1, b0, p0, p1)))
        owners.extend((owner, owner, owner))

    loops = {
        port: tuple(control_index[control_id] for control_id in info[2])
        for port, info in _SOURCE.PORT_INFO.items()
    }
    transition_index_metadata = {
        side: {
            "socket": tuple(control_index[control_id] for control_id in
                            _SOURCE.JUNCTION_TRACES[_SIDE_JUNCTION[side]]),
            "ringA": ring_indices[side]["ringA"],
            "ringB": ring_indices[side]["ringB"],
            "exit": tuple(control_index[control_id] for control_id in
                          _SOURCE.PORT_INFO[_SIDE_PORT[side]][2]),
        }
        for side in _SIDES
    }
    return vertices, quads, owners, transition_index_metadata, loops


def _metadata(
    frames: dict[str, dict[str, Any]],
    transition_indices: dict[str, dict[str, tuple[int, ...]]],
    admission_failures: tuple[dict[str, Any], ...],
    base_control_owners: tuple[str, ...],
) -> dict[str, Any]:
    exported_frames = {}
    for side in _SIDES:
        info = frames[side]
        exported_frames[side] = {
            key: info[key]
            for key in ("H", "knee", "length", "d", "X", "U", "F", "exit")
        }
    return {
        "level": 0,
        "admission_status": "rejected" if admission_failures else "accepted",
        "admission_failures": admission_failures,
        "base_control_owners": base_control_owners,
        "dominant_owner_label": (
            "display representative only; authoritative ownership is "
            "base_control_owners plus full base_stencils"
        ),
        "frames": exported_frames,
        "transition_indices": transition_indices,
        "exit_expected": {side: frames[side]["exit"] for side in _SIDES},
    }


def _identity_stencils(count: int) -> tuple[tuple[tuple[int, float], ...], ...]:
    return tuple(((index, 1.0),) for index in range(count))


def _incidence(
    quads: Any,
    _vertex_count: int,
) -> tuple[dict[tuple[int, int], list[tuple[int, int, int]]],
           set[tuple[int, int]]]:
    uses: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for face_index, face in enumerate(quads):
        for slot, left in enumerate(face):
            right = face[(slot + 1) % 4]
            uses[_edge_key(left, right)].append((face_index, left, right))
    boundary = {edge for edge, rows in uses.items() if len(rows) == 1}
    return dict(uses), boundary


def _validate_mesh(mesh: Mapping[str, Any]) -> tuple[Any, ...]:
    required = {"vertices", "quads", "face_owners", "control_owners",
                "loops", "base_stencils", "frames", "metadata"}
    if not isinstance(mesh, Mapping) or not required.issubset(mesh):
        _fail("mesh must provide the generic transition fields")
    raw_vertices = mesh["vertices"]
    raw_quads = mesh["quads"]
    raw_face_owners = mesh["face_owners"]
    raw_control_owners = mesh["control_owners"]
    raw_loops = mesh["loops"]
    raw_stencils = mesh["base_stencils"]
    raw_frames = mesh["frames"]
    metadata = mesh["metadata"]
    if type(metadata) is not dict:
        _fail("metadata must be a dict")
    status = metadata.get("admission_status")
    failures = metadata.get("admission_failures")
    base_control_owners = metadata.get("base_control_owners")
    dominant_owner_label = metadata.get("dominant_owner_label")
    if status not in {"accepted", "rejected"}:
        _fail("metadata must declare admission_status")
    if type(failures) not in (list, tuple):
        _fail("metadata must retain admission_failures")
    if status == "accepted" and failures:
        _fail("accepted metadata cannot retain admission failures")
    if status == "rejected" and not failures:
        _fail("rejected metadata must retain admission failures")
    if type(base_control_owners) not in (list, tuple) or not base_control_owners:
        _fail("metadata must retain base control owners")
    if any(type(owner) is not str for owner in base_control_owners):
        _fail("metadata base control owners must contain strings")
    if type(dominant_owner_label) is not str or not dominant_owner_label:
        _fail("metadata must explain the dominant owner label")
    if type(raw_frames) is not dict or set(raw_frames) != set(_SIDES):
        _fail("frames must contain exactly left and right")
    for side in _SIDES:
        frame = raw_frames[side]
        if type(frame) is not dict:
            _fail(f"frames.{side} must be a mapping")
        for key in ("H", "d", "X", "U", "F", "exit"):
            _vector(frame.get(key), f"frames.{side}.{key}")
        _finite_float(frame.get("length"), f"frames.{side}.length")
    if type(raw_vertices) not in (list, tuple) or not raw_vertices:
        _fail("mesh vertices must be a non-empty sequence")
    vertices = tuple(_vector(point, f"vertices[{index}]")
                     for index, point in enumerate(raw_vertices))
    if type(raw_quads) not in (list, tuple) or not raw_quads:
        _fail("mesh quads must be a non-empty sequence")
    quads: list[tuple[int, int, int, int]] = []
    for face_index, face in enumerate(raw_quads):
        if type(face) not in (list, tuple) or len(face) != 4:
            _fail(f"quads[{face_index}] must have four indices")
        if any(type(index) is not int for index in face):
            _fail(f"quads[{face_index}] indices must be integers")
        checked = tuple(face)
        if len(set(checked)) != 4 or any(index < 0 or index >= len(vertices)
                                         for index in checked):
            _fail(f"quads[{face_index}] has invalid indices")
        quads.append(checked)  # type: ignore[arg-type]
    if type(raw_face_owners) not in (list, tuple):
        _fail("face_owners must be a sequence")
    face_owners = tuple(raw_face_owners)
    if len(face_owners) != len(quads) or any(type(owner) is not str
                                             for owner in face_owners):
        _fail("face_owners must have one string owner per quad")
    if type(raw_control_owners) not in (list, tuple) or not raw_control_owners:
        _fail("control_owners must be a non-empty sequence")
    control_owners = tuple(raw_control_owners)
    if len(control_owners) != len(vertices) or any(
        type(owner) is not str for owner in control_owners
    ):
        _fail("control_owners must contain one string owner per vertex")
    if type(raw_stencils) not in (list, tuple) or len(raw_stencils) != len(vertices):
        _fail("base_stencils must match the vertex count")
    stencils: list[tuple[tuple[int, float], ...]] = []
    for vertex_index, stencil in enumerate(raw_stencils):
        if type(stencil) not in (list, tuple) or not stencil:
            _fail(f"base_stencils[{vertex_index}] must be non-empty")
        checked_stencil: list[tuple[int, float]] = []
        previous = -1
        for item in stencil:
            if type(item) not in (list, tuple) or len(item) != 2:
                _fail(f"base_stencils[{vertex_index}] has an invalid term")
            base_index, coefficient = item
            if type(base_index) is not int or base_index <= previous:
                _fail(f"base_stencils[{vertex_index}] must be sorted and unique")
            if base_index < 0 or base_index >= len(base_control_owners):
                _fail(f"base_stencils[{vertex_index}] references an unknown base vertex")
            coefficient = _finite_float(coefficient, "base stencil coefficient")
            if coefficient == 0.0:
                _fail(f"base_stencils[{vertex_index}] contains a zero coefficient")
            checked_stencil.append((base_index, coefficient))
            previous = base_index
        stencil_sum = sum(coefficient for _base_index, coefficient in checked_stencil)
        if abs(stencil_sum - 1.0) > _STENCIL_TOLERANCE:
            _fail(f"base_stencils[{vertex_index}] must sum to one")
        if any(coefficient < -_STENCIL_TOLERANCE
               for _base_index, coefficient in checked_stencil):
            _fail(f"base_stencils[{vertex_index}] must be nonnegative")
        stencils.append(tuple(checked_stencil))

    if type(raw_loops) is not dict or not raw_loops:
        _fail("loops must be a non-empty dict")
    loops: dict[str, tuple[int, ...]] = {}
    for name, loop in raw_loops.items():
        if type(name) is not str or type(loop) not in (list, tuple) or len(loop) < 3:
            _fail("each loop must be a named sequence of at least three vertices")
        if any(type(index) is not int or index < 0 or index >= len(vertices)
               for index in loop) or len(set(loop)) != len(loop):
            _fail(f"loop {name!r} has invalid vertices")
        loops[name] = tuple(loop)

    uses, boundary = _incidence(quads, len(vertices))
    if any(len(rows) not in (1, 2) for rows in uses.values()):
        _fail("mesh has a non-manifold edge")
    for rows in uses.values():
        if len(rows) == 2 and rows[0][1:] == rows[1][1:]:
            _fail("mesh has an orientation conflict")
    declared: set[tuple[int, int]] = set()
    for name, loop in loops.items():
        for index, left in enumerate(loop):
            edge = _edge_key(left, loop[(index + 1) % len(loop)])
            if edge not in boundary:
                _fail(f"loop {name!r} contains a non-boundary edge")
            if edge in declared:
                _fail("boundary edge is declared by more than one loop")
            declared.add(edge)
    if declared != boundary:
        _fail("loops do not cover the mesh boundary exactly")

    return (vertices, tuple(quads), face_owners, control_owners, loops,
            tuple(stencils), uses)


def _medial_admission(
    frames: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    distance = frames["right"]["H"][0] - frames["left"]["H"][0]
    required = frames["left"]["rx"] + frames["right"]["rx"]
    clearance = distance - required
    if clearance > 0.0:
        return ()
    return ({
        "gate": "medial-clearance",
        "outcome": "reject",
        "observed_clearance": clearance,
        "lateral_centre_distance": distance,
        "required_distance": required,
    },)


def build(
    components: dict[str, float],
    attachments: dict[str, dict[str, list[float]]],
    diagnostic: bool = False,
) -> dict[str, Any]:
    """Construct the fixed local L0 transition mesh."""
    if type(diagnostic) is not bool:
        _fail("diagnostic must be a bool")
    carrier, checked_attachments = _validate_inputs(components, attachments)
    frames = _frame_and_dimensions(carrier, checked_attachments)
    admission_failures = _medial_admission(frames)
    if admission_failures and not diagnostic:
        _fail("medial clearance admission failed; use diagnostic=True to retain it")
    transitions = _transition_rings(frames)
    base_vertices = _original_vertices(carrier, transitions)
    vertices, quads, face_owners, transition_indices, loops = _transition_faces(
        base_vertices, transitions
    )
    control_owners = tuple(
        _SOURCE.CONTROL_OWNERS[control_id]
        for control_id in _SOURCE.CONTROL_IDS
    )
    control_owners += tuple(
        _SIDE_DOMAIN[side]
        for side in _SIDES
        for _index in range(2 * len(transitions[side]["ringA"]))
    )
    metadata = _metadata(frames, transition_indices, admission_failures,
                         control_owners)
    mesh = {
        "vertices": tuple(vertices),
        "quads": tuple(quads),
        "face_owners": tuple(face_owners),
        "control_owners": control_owners,
        "loops": loops,
        "base_stencils": _identity_stencils(len(vertices)),
        "frames": metadata["frames"],
        "metadata": metadata,
    }
    _validate_mesh(mesh)
    return mesh


def _combine_stencils(
    parent_stencils: tuple[tuple[tuple[int, float], ...], ...],
    terms: list[tuple[int, float]],
) -> tuple[tuple[int, float], ...]:
    values: dict[int, float] = defaultdict(float)
    for parent_index, factor in terms:
        for base_index, coefficient in parent_stencils[parent_index]:
            values[base_index] += factor * coefficient
    return tuple((base_index, coefficient)
                 for base_index, coefficient in sorted(values.items())
                 if coefficient != 0.0)


def _owners_from_stencils(
    base_owners: tuple[str, ...],
    stencils: tuple[tuple[tuple[int, float], ...], ...],
) -> tuple[str, ...]:
    owners = []
    for stencil in stencils:
        base_index, _coefficient = min(
            stencil,
            key=lambda item: (-abs(item[1]), item[0]),
        )
        owners.append(base_owners[base_index])
    return tuple(owners)


def _blend_points(
    points: tuple[tuple[float, float, float], ...],
    terms: list[tuple[int, float]],
) -> tuple[float, float, float]:
    result = [0.0, 0.0, 0.0]
    for point_index, factor in terms:
        point = points[point_index]
        for axis in range(3):
            result[axis] += factor * point[axis]
    return tuple(result)  # type: ignore[return-value]


def _subdivide_once(mesh: Mapping[str, Any], level: int) -> dict[str, Any]:
    points, quads, face_owners, control_owners, loops, parent_stencils, uses = (
        _validate_mesh(mesh)
    )
    if type(level) is not int or level < 1:
        _fail("subdivision level must be a positive integer")

    edges = tuple(sorted(uses))
    boundary = {edge for edge, rows in uses.items() if len(rows) == 1}
    faces_at_vertex: dict[int, list[int]] = defaultdict(list)
    edges_at_vertex: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for face_index, face in enumerate(quads):
        for vertex in face:
            faces_at_vertex[vertex].append(face_index)
    for edge in edges:
        left, right = edge
        edges_at_vertex[left].append(edge)
        edges_at_vertex[right].append(edge)

    vertex_terms: list[list[tuple[int, float]]] = []
    for vertex in range(len(points)):
        boundary_edges = [edge for edge in boundary if vertex in edge]
        if boundary_edges:
            neighbours = sorted({
                other
                for edge in boundary_edges
                for other in edge
                if other != vertex
            })
            if len(neighbours) != 2:
                _fail("boundary vertex does not have exactly two boundary neighbours")
            vertex_terms.append([(vertex, 6.0 / 8.0),
                                 (neighbours[0], 1.0 / 8.0),
                                 (neighbours[1], 1.0 / 8.0)])
            continue
        incident_faces = sorted(faces_at_vertex[vertex])
        incident_edges = sorted(edges_at_vertex[vertex])
        valence = len(incident_faces)
        if valence == 0 or len(incident_edges) != valence:
            _fail("interior vertex has inconsistent Catmull--Clark valence")
        terms: list[tuple[int, float]] = []
        for face_index in incident_faces:
            terms.extend((corner, 1.0 / (4.0 * valence * valence))
                         for corner in quads[face_index])
        for left, right in incident_edges:
            terms.extend(((left, 1.0 / (valence * len(incident_edges))),
                          (right, 1.0 / (valence * len(incident_edges)))))
        terms.append((vertex, (valence - 3.0) / valence))
        vertex_terms.append(terms)

    edge_terms: list[list[tuple[int, float]]] = []
    for edge in edges:
        left, right = edge
        rows = uses[edge]
        if len(rows) == 1:
            edge_terms.append([(left, 0.5), (right, 0.5)])
            continue
        terms = [(left, 0.25), (right, 0.25)]
        for face_index, _face_left, _face_right in sorted(rows):
            terms.extend((corner, 0.25 * 0.25)
                         for corner in quads[face_index])
        edge_terms.append(terms)

    face_terms = [
        [(corner, 0.25) for corner in face]
        for face in quads
    ]
    vertices: list[tuple[float, float, float]] = []
    stencils: list[tuple[tuple[int, float], ...]] = []
    for terms in vertex_terms + edge_terms + face_terms:
        vertices.append(_blend_points(points, terms))
        stencils.append(_combine_stencils(parent_stencils, terms))

    vertex_count = len(points)
    edge_indices = {
        edge: vertex_count + index for index, edge in enumerate(edges)
    }
    face_start = vertex_count + len(edges)
    child_quads: list[tuple[int, int, int, int]] = []
    child_owners: list[str] = []
    for face_index, face in enumerate(quads):
        face_point = face_start + face_index
        for corner, vertex in enumerate(face):
            next_vertex = face[(corner + 1) % 4]
            previous_vertex = face[(corner - 1) % 4]
            child_quads.append((
                vertex,
                edge_indices[_edge_key(vertex, next_vertex)],
                face_point,
                edge_indices[_edge_key(previous_vertex, vertex)],
            ))
            child_owners.append(face_owners[face_index])

    child_loops = {
        name: tuple(
            item
            for index, vertex in enumerate(loop)
            for item in (
                vertex,
                edge_indices[_edge_key(vertex, loop[(index + 1) % len(loop)])],
            )
        )
        for name, loop in loops.items()
    }
    metadata = dict(mesh["metadata"])
    metadata["level"] = level
    child = {
        "vertices": tuple(vertices),
        "quads": tuple(child_quads),
        "face_owners": tuple(child_owners),
        "control_owners": _owners_from_stencils(
            tuple(metadata["base_control_owners"]), tuple(stencils)
        ),
        "loops": child_loops,
        "base_stencils": tuple(stencils),
        "frames": mesh["frames"],
        "metadata": metadata,
    }
    _validate_mesh(child)
    return child


def evaluate(mesh: Mapping[str, Any], levels: int = 2) -> list[dict[str, Any]]:
    """Return the ordered sequence beginning with the supplied L0 mesh."""
    if type(levels) is not int or levels < 0 or levels > 2:
        _fail("the local transition evaluates between zero and two CC levels")
    _validate_mesh(mesh)
    result = [dict(mesh)]
    current: Mapping[str, Any] = mesh
    for level in range(1, levels + 1):
        current = _subdivide_once(current, level)
        result.append(current)
    return result


def build_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Runner adapter; evidence runs opt into diagnostic retention."""
    if not isinstance(case, Mapping):
        _fail("case must be a mapping")
    return build(case["components"], case["attachments"], diagnostic=True)


def evaluate_case(mesh: Mapping[str, Any], _case: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Runner adapter for the fixed two-step evaluation."""
    return evaluate(mesh, levels=2)


__all__ = [
    "GEOMETRY_COMPONENT_IDS",
    "build",
    "build_case",
    "evaluate",
    "evaluate_case",
]

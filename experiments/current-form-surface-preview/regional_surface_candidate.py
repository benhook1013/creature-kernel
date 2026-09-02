"""Source-faithful Stage-1 regional surface candidate.

This module is the small bridge between the validated current-form preview
envelope and :mod:`regional_hybrid_surface`.  It intentionally owns no body
dimensions: torso controls, source descriptor reference points, and the
variant-projected authored profiles are the only geometric inputs.  The
result is an experiment-local candidate, not a geometry or topology contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

import numpy as np
from skimage.measure import marching_cubes


class RegionalSurfaceCandidateError(ValueError):
    """Raised when the prepared-form adapter cannot prove its bounded output."""


CandidateError = RegionalSurfaceCandidateError


_ROOT = Path(__file__).resolve().parent
_TORSO_NAMES = (
    "lower-pelvis",
    "upper-pelvis",
    "lower-abdomen",
    "waist-abdomen",
    "upper-abdomen",
    "lower-ribcage",
    "upper-ribcage-shoulder",
)
_TORSO_OWNER_ROLES = ("pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso")
_REGION_NAMES = ("pelvis", "abdominal-bridge", "ribcage")
_REGION_INTERVALS = ((0, 2), (2, 4), (4, 6))
_ROUTE_NAMES = ("head-neck", "left-arm", "right-arm", "left-leg", "right-leg", "left-foot", "right-foot")
_HEAD_NECK_NAMES = ("neck-collar", "neck-upper", "head-base", "cranium-mid", "cranium-crown", "muzzle-root", "muzzle-mid", "muzzle-tip")
_HEAD_NECK_CONNECTIONS = (
    ("neck-collar-to-neck-upper", 0, 1, "vertical-neck-cranium"),
    ("neck-upper-to-head-base", 1, 2, "vertical-neck-cranium"),
    ("head-base-to-cranium-mid", 2, 3, "vertical-neck-cranium"),
    ("cranium-mid-to-cranium-crown", 3, 4, "vertical-neck-cranium"),
    ("cranium-mid-to-muzzle-root", 3, 5, "forward-muzzle"),
    ("muzzle-root-to-muzzle-mid", 5, 6, "forward-muzzle"),
    ("muzzle-mid-to-muzzle-tip", 6, 7, "forward-muzzle"),
)
_LIMB_NAMES = {
    "arm": ("upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "forearm-distal"),
    "leg": ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
}
_HIP_CUP_NAMES = ("pelvis-seat", "hip-cup-rim", "femoral-neck")
_CANDIDATE_FORMAT = "creature-kernel.disposable-regional-surface-candidate.v3"
_MESH_MAX_SAMPLES = 80
_MESH_MAX_VOXELS = 80**3
_MESH_MIN_SAMPLES = 20
_MESH_DEFAULT_SAMPLES = 56
_MESH_DEFAULT_PADDING = 0.20
_MESH_AXIAL_PHASE_FRACTION = 0.50
_GEOMETRY_TOLERANCE = 1.0e-8
_DEFAULT_SOURCE_NAMESPACE = "main"
_SHOULDER_CONTROL_SOURCE_PREFIX = "source-landmark:"
_SHOULDER_CONTROL_FRAME_ROLE = "form_shoulder_control"
_SHOULDER_CONTROL_ROLES = ("form_shoulder_peak", "form_axilla")
_BILATERAL_CENTER_TOLERANCE = 1.0e-8
_BILATERAL_RADIUS_TOLERANCE = 1.0e-12

# Candidate-only interface and anatomy hypotheses.  These values are kept in
# one place so every prepared variant reconstructs from the source profiles
# and named controls rather than from profile-specific coordinates.
INTERFACE_PAD = 0.75
HOCK_INTERFACE_PAD = 1.25
INTERFACE_COLLAR_FRACTION = 0.22
INTERFACE_BLEND_FRACTION = 0.15
ENDPOINT_CONNECTOR_DEPTH_FRACTION = 0.25
JOINT_RADIUS_FACTOR = 0.82
HIP_CUP_SEAT_DEPTH_FRACTION = 0.25
HIP_CUP_RIM_RADIUS_FACTOR = 1.0
FEMORAL_NECK_CENTER_FACTOR = 0.55
FEMORAL_NECK_RADIUS_FACTOR = 0.72
TORSO_LOWER_CAP_FACTOR = 1.10
TORSO_UPPER_CAP_FACTOR = 0.50
MIDPOINT_BELLY_FACTORS = {
    "upper-arm-midpoint": 1.08,
    "forearm-midpoint": 1.06,
    "thigh-midpoint": 1.10,
    "shin-midpoint": 1.06,
}
TORSO_RADIUS_FACTORS = {
    "lower-pelvis": (0.82, 0.78, 0.82),
    "upper-pelvis": (0.98, 0.90, 0.92),
    "lower-abdomen": (1.00, 1.00, 1.00),
    "waist-abdomen": (0.88, 0.88, 0.88),
    "upper-abdomen": (1.00, 1.00, 1.00),
    "lower-ribcage": (1.00, 1.00, 1.00),
    "upper-ribcage-shoulder": (0.86, 0.82, 0.82),
}
HEAD_RADIUS_FACTORS = {
    "cranium-mid": (0.90, 1.08, 0.82),
    "cranium-crown": (0.88, 1.00, 0.82),
    "muzzle-root": (0.82, 0.90, 1.00),
    "muzzle-mid": (0.78, 0.90, 0.90),
    "muzzle-tip": (0.72, 0.85, 0.75),
}
MUZZLE_CENTER_FACTORS = {"muzzle-mid": 1.15, "muzzle-tip": 1.25}


def _fail(message: str) -> None:
    raise RegionalSurfaceCandidateError(message)


def _finite_float(value: Any, where: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} must be numeric: {exc}")
    if not math.isfinite(result):
        _fail(f"{where} must be finite")
    return result


def _positive_float(value: Any, where: str) -> float:
    result = _finite_float(value, where)
    if result <= 0.0:
        _fail(f"{where} must be positive")
    return result


def _vec3(value: Any, where: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} must be a finite three-vector: {exc}")
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        _fail(f"{where} must be a finite three-vector")
    return result


def _tuple3(value: Any, where: str) -> tuple[float, float, float]:
    result = _vec3(value, where)
    return tuple(float(item) for item in result)


def _key_json(key: tuple[str, tuple[str, ...], str, str]) -> dict[str, Any]:
    if type(key) is not tuple or len(key) != 4:
        _fail("source key is not a four-part AddressKey")
    namespace, anchors, kind, role = key
    if type(namespace) is not str or not namespace or type(anchors) is not tuple or any(
        type(item) is not str or not item for item in anchors
    ) or type(kind) is not str or not kind or type(role) is not str or not role:
        _fail("source key is not a valid AddressKey")
    return {"namespace": namespace, "anchors": list(anchors), "kind": kind, "role": role}


def _key_text(key: tuple[str, tuple[str, ...], str, str]) -> str:
    return json.dumps(_key_json(key), sort_keys=True, separators=(",", ":"))


def _key_from_json(value: Any, where: str) -> tuple[str, tuple[str, ...], str, str]:
    if type(value) is not dict or set(value) != {"namespace", "anchors", "kind", "role"}:
        _fail(f"{where} is not a canonical AddressKey object")
    namespace = value.get("namespace")
    anchors = value.get("anchors")
    kind = value.get("kind")
    role = value.get("role")
    if (
        type(namespace) is not str
        or not namespace
        or type(anchors) is not list
        or not anchors
        or any(type(item) is not str or not item for item in anchors)
        or type(kind) is not str
        or not kind
        or type(role) is not str
        or not role
    ):
        _fail(f"{where} is not a valid canonical AddressKey object")
    return namespace, tuple(anchors), kind, role


def _canonical_shoulder_control_source_key(namespace: str, side: str, role: str) -> str:
    if type(namespace) is not str or not namespace:
        _fail("shoulder control namespace is not exact")
    if side not in {"left", "right"} or role not in _SHOULDER_CONTROL_ROLES:
        _fail("shoulder control side or role is not exact")
    owner = (namespace, (side,), "part", "upper_arm")
    payload = {
        "frame": {"owner": _key_json(owner), "role": _SHOULDER_CONTROL_FRAME_ROLE},
        "namespace": namespace,
        "owner": _key_json(owner),
        "role": role,
        "side": side,
    }
    return _SHOULDER_CONTROL_SOURCE_PREFIX + json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_shoulder_control_source_key(
    source_key: Any,
    *,
    expected_namespace: str | None = None,
    expected_side: str | None = None,
    expected_role: str | None = None,
) -> dict[str, Any]:
    if type(source_key) is not str or not source_key.startswith(_SHOULDER_CONTROL_SOURCE_PREFIX):
        _fail("shoulder control source key is not the canonical source binding")
    encoded = source_key[len(_SHOULDER_CONTROL_SOURCE_PREFIX):]
    try:
        payload = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        _fail(f"shoulder control source key is not canonical JSON: {exc}")
    if type(payload) is not dict or set(payload) != {"frame", "namespace", "owner", "role", "side"}:
        _fail("shoulder control source key has an unexpected binding schema")
    namespace = payload.get("namespace")
    side = payload.get("side")
    role = payload.get("role")
    if type(namespace) is not str or not namespace or side not in {"left", "right"} or role not in _SHOULDER_CONTROL_ROLES:
        _fail("shoulder control source key has an invalid namespace, side, or role")
    owner = _key_from_json(payload.get("owner"), "shoulder control owner")
    frame = payload.get("frame")
    if type(frame) is not dict or set(frame) != {"owner", "role"}:
        _fail("shoulder control source key has an invalid frame binding")
    frame_owner = _key_from_json(frame.get("owner"), "shoulder control frame owner")
    frame_role = frame.get("role")
    expected_owner = (namespace, (side,), "part", "upper_arm")
    if owner != expected_owner or frame_owner != expected_owner or frame_role != _SHOULDER_CONTROL_FRAME_ROLE:
        _fail("shoulder control source key has a forged owner or frame binding")
    if _canonical_shoulder_control_source_key(namespace, side, role) != source_key:
        _fail("shoulder control source key is not canonically serialized")
    if expected_namespace is not None and namespace != expected_namespace:
        _fail("shoulder control source key has the wrong namespace")
    if expected_side is not None and side != expected_side:
        _fail("shoulder control source key has the wrong side")
    if expected_role is not None and role != expected_role:
        _fail("shoulder control source key has the wrong role")
    return {
        "namespace": namespace,
        "side": side,
        "owner": owner,
        "role": role,
        "frame": (frame_owner, frame_role),
        "frame_role": frame_role,
        "source_key": source_key,
    }


def _load_surface_preview() -> Any:
    module_name = "regional_surface_candidate_surface_preview"
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        return loaded
    path = _ROOT / "surface_preview.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        _fail(f"could not load current-form compiler from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        _fail(f"could not load current-form compiler: {exc}")
    return module


def _load_hybrid() -> Any:
    module_name = "regional_surface_candidate_hybrid"
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        return loaded
    path = _ROOT / "regional_hybrid_surface.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        _fail(f"could not load regional hybrid primitives from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        _fail(f"could not load regional hybrid primitives: {exc}")
    return module


def _as_form(prepared: Any) -> Any:
    if isinstance(prepared, Mapping):
        return _load_surface_preview().validate_envelope(prepared)
    if not hasattr(prepared, "variants") or not hasattr(prepared, "authored_torso_profile"):
        _fail("adapter input must be a validated prepared form or its v11 mapping")
    return prepared


def _variant(form: Any, profile_id: str) -> tuple[int, tuple[Any, ...], Any]:
    if type(profile_id) is not str or not profile_id:
        _fail("surface variant id must be a non-empty string")
    for index, item in enumerate(form.variants):
        if len(item) != 3:
            _fail("prepared form variant record is malformed")
        variant_id, descriptors, raw = item
        if variant_id == profile_id:
            return index, tuple(descriptors), raw
    _fail(f"prepared form has no surface variant {profile_id!r}")


def _descriptor_map(descriptors: tuple[Any, ...], namespace: str) -> dict[tuple[str, tuple[str, ...], str, str], Any]:
    result: dict[tuple[str, tuple[str, ...], str, str], Any] = {}
    for descriptor in descriptors:
        key = getattr(descriptor, "key", None)
        if key is None or key in result:
            _fail("prepared form variant has duplicate or missing descriptor keys")
        if key[0] != namespace or key[2] != "part":
            _fail("prepared form descriptor is outside the source Part namespace")
        result[key] = descriptor
    return result


def _shoulder_control_binding(
    form: Any,
    descriptors: tuple[Any, ...],
    side: str,
    role: str,
) -> dict[str, Any]:
    """Resolve one shoulder control from the exact source/form binding."""

    if side not in {"left", "right"} or role not in _SHOULDER_CONTROL_ROLES:
        _fail("shoulder control binding has an invalid side or role")
    source = getattr(form, "source", None)
    if type(source) is not dict:
        _fail("shoulder control binding has no exact source document")
    namespace = source.get("namespace")
    document = source.get("document")
    if type(namespace) is not str or not namespace or type(document) is not str or not document:
        _fail("shoulder control binding source identity is incomplete")
    owner_key = (namespace, (side,), "part", "upper_arm")
    by_key = _descriptor_map(tuple(descriptors), namespace)
    owner = by_key.get(owner_key)
    if owner is None:
        _fail(f"{side} shoulder control has no exact upper-arm owner")

    frames = tuple(
        frame for frame in tuple(getattr(form, "authored_frames", ()))
        if getattr(frame, "owner", None) == owner_key
        and getattr(frame, "role", None) == _SHOULDER_CONTROL_FRAME_ROLE
    )
    landmarks = tuple(
        landmark for landmark in tuple(getattr(form, "authored_landmarks", ()))
        if getattr(landmark, "owner", None) == owner_key
        and getattr(landmark, "role", None) == role
    )
    if len(frames) != 1 or len(landmarks) != 1:
        _fail(f"{side} shoulder control {role} does not have one exact source frame and landmark")
    frame = frames[0]
    landmark = landmarks[0]
    expected_frame = (owner_key, _SHOULDER_CONTROL_FRAME_ROLE)
    if getattr(landmark, "frame", None) != expected_frame:
        _fail(f"{side} shoulder control {role} has a forged frame owner or role")
    expected_provenance = {"source": "source-authored", "document": document, "namespace": namespace}
    if getattr(frame, "provenance", None) != expected_provenance or getattr(landmark, "provenance", None) != expected_provenance:
        _fail(f"{side} shoulder control {role} has forged source provenance")
    return {
        "namespace": namespace,
        "side": side,
        "owner": owner_key,
        "role": role,
        "frame": expected_frame,
        "frame_role": _SHOULDER_CONTROL_FRAME_ROLE,
        "semantic_key": f"control:{side}-{'shoulder-peak' if role == 'form_shoulder_peak' else 'axilla'}",
        "source_key": _canonical_shoulder_control_source_key(namespace, side, role),
        "owner_descriptor": owner,
        "frame_record": frame,
        "landmark": landmark,
    }


def _validate_shoulder_control_identity(
    control: Any,
    *,
    namespace: str | None = None,
    side: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    """Validate every public identity field of a shoulder control exactly."""

    parsed = _parse_shoulder_control_source_key(
        getattr(control, "source_key", None),
        expected_namespace=namespace,
        expected_side=side,
        expected_role=role,
    )
    suffix = "shoulder-peak" if parsed["role"] == "form_shoulder_peak" else "axilla"
    expected_name = f"{parsed['side']}-{suffix}"
    expected_semantic_key = f"control:{expected_name}"
    if getattr(control, "name", None) != expected_name:
        _fail("shoulder control name is not derived from its exact source role and side")
    if getattr(control, "semantic_key", None) != expected_semantic_key:
        _fail("shoulder control semantic key is not derived from its exact source role and side")
    parsed["name"] = expected_name
    parsed["semantic_key"] = expected_semantic_key
    return parsed


def _descriptor_source(module: Any, descriptor: Any, scale: float) -> dict[str, Any]:
    try:
        source = module._source_shape(descriptor, scale)
    except Exception as exc:
        _fail(f"could not map source descriptor {getattr(descriptor, 'key', None)!r}: {exc}")
    if not isinstance(source, dict) or source.get("name") not in {"capsule", "tapered-segment", "ellipsoid"}:
        _fail("prepared descriptor has an unsupported source shape")
    return source


def _basis(hybrid: Any, angle: float) -> Any:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return hybrid.RegionBasis(
        axial_axis=(0.0, 1.0, 0.0),
        lateral_axis=(cosine, 0.0, sine),
        forward_axis=(-sine, 0.0, cosine),
    )


def _source_route_key(owner: tuple[str, tuple[str, ...], str, str], route: str) -> str:
    return f"source-route:{route}:{_key_text(owner)}"


def _projected_profile_radii3(section: Any) -> tuple[float, float, float]:
    values = []
    for axis in ("lateral", "up", "forward"):
        field_name = {
            "lateral": "lateral_radius_permille",
            "up": "up_radius_permille",
            "forward": "forward_radius_permille",
        }[axis]
        values.append(_positive_float(getattr(section, field_name, None), f"{section.name}.{field_name}") / 1000.0)
    return values[0], values[1], values[2]


def _owner_point(owner: Any, scale: float, local_position: Any, where: str) -> np.ndarray:
    return _vec3(getattr(owner, "point", None), f"{where}.owner_point") + _vec3(local_position, f"{where}.local_position") / scale


@dataclass(frozen=True, slots=True)
class SurfaceMeshProof:
    """Small in-memory mesh plus finite topology proof."""

    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray
    lower: tuple[float, float, float]
    upper: tuple[float, float, float]
    samples: int
    connected_components: int
    boundary_edge_count: int
    nonmanifold_edge_count: int
    nonmanifold_vertex_count: int
    watertight: bool

    @property
    def connected(self) -> bool:
        """Whether all faces are connected through shared undirected edges."""

        return self.connected_components == 1

    @property
    def closed_triangle_2_manifold(self) -> bool:
        """Whether extraction proved one connected closed triangle 2-manifold."""

        return (
            self.connected
            and self.watertight
            and self.boundary_edge_count == 0
            and self.nonmanifold_edge_count == 0
            and self.nonmanifold_vertex_count == 0
        )

    @property
    def topology_proven(self) -> bool:
        return self.closed_triangle_2_manifold


@dataclass(frozen=True, slots=True)
class RegionalSurfaceCandidate:
    """The source-bound Stage-1 regional candidate."""

    profile_id: str
    source: dict[str, Any]
    chain: Any
    regions: tuple[Any, ...]
    stations: tuple[Any, ...]
    routes: tuple[Any, ...]
    controls: tuple[Any, ...]
    field: Any
    metadata: dict[str, Any]
    binding_evidence: tuple[dict[str, Any], ...]
    mesh: SurfaceMeshProof | None = None

    @property
    def scalar_field(self) -> Any:
        return self.field

    @property
    def attachments(self) -> tuple[Any, ...]:
        return self.routes

    @property
    def interfaces(self) -> tuple[Any, ...]:
        """Independent parent-targeted interface patches used by the skin."""

        return self.field.interfaces

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.field.bounds

    def evaluate(self, points: Any) -> float | np.ndarray:
        return self.field.evaluate(points)

    scalar_evaluator = evaluate

    def operation_trace(self, point: Any) -> Any:
        return self.field.operation_trace(point)

    trace = operation_trace

    def contribution_report(self, point: Any) -> dict[str, Any]:
        return self.field.contribution_report(point)

    contributors = contribution_report

    def mesh_candidate(self, samples: int = _MESH_DEFAULT_SAMPLES, padding: float = _MESH_DEFAULT_PADDING) -> SurfaceMeshProof:
        return _mesh_candidate(self, samples, padding)


def _make_regions(hybrid: Any) -> tuple[Any, ...]:
    # The abdominal interior retains its source-driven regional frame.  The
    # terminal endpoint neighborhoods use the source sagittal basis so
    # endpoint-derived bilateral connectors and hip cups reflect exactly.
    pelvis_interior = _basis(hybrid, 0.0)
    abdomen_interior = _basis(hybrid, 0.23)
    ribcage_interior = _basis(hybrid, 0.0)
    seam_pelvis_abdomen = _basis(hybrid, 0.04)
    sagittal_endpoint = _basis(hybrid, 0.0)
    return (
        hybrid.AxialRegion(
            _REGION_NAMES[0],
            *_REGION_INTERVALS[0],
            basis=pelvis_interior,
            start_basis=sagittal_endpoint,
            end_basis=seam_pelvis_abdomen,
            semantic_key="region:pelvis",
        ),
        hybrid.AxialRegion(
            _REGION_NAMES[1],
            *_REGION_INTERVALS[1],
            basis=abdomen_interior,
            start_basis=seam_pelvis_abdomen,
            end_basis=sagittal_endpoint,
            semantic_key="region:abdominal-bridge",
        ),
        hybrid.AxialRegion(
            _REGION_NAMES[2],
            *_REGION_INTERVALS[2],
            basis=ribcage_interior,
            start_basis=sagittal_endpoint,
            end_basis=sagittal_endpoint,
            semantic_key="region:ribcage",
        ),
    )


def _make_torso(
    form: Any,
    descriptors: tuple[Any, ...],
    variant_index: int,
    module: Any,
    hybrid: Any,
) -> tuple[tuple[Any, ...], tuple[Any, ...], dict[str, Any], tuple[dict[str, Any], ...]]:
    scale = _positive_float(form.reference_scale, "prepared form reference_scale")
    namespace = form.source["namespace"]
    by_key = _descriptor_map(descriptors, namespace)
    authored = tuple(form.authored_torso_profile.sections)
    projected = tuple(form.variant_torso_profiles[variant_index].sections)
    if len(authored) != 7 or len(projected) != 7:
        _fail("prepared form torso projection must contain exactly seven sections")
    if tuple(section.name for section in authored) != _TORSO_NAMES or tuple(section.name for section in projected) != _TORSO_NAMES:
        _fail("prepared form torso station order is not the exact seven-section route")

    source_radii: list[np.ndarray] = []
    source_centers: list[np.ndarray] = []
    for index, (source_section, variant_section) in enumerate(zip(authored, projected)):
        owner = by_key.get(source_section.owner)
        if owner is None or source_section.owner[3] != _TORSO_OWNER_ROLES[index]:
            _fail(f"torso station {source_section.name} lost its source owner")
        if variant_section.source_section_index != index or variant_section.name != source_section.name:
            _fail(f"torso station {source_section.name} lost its projected source index")
        if source_section.landmark.owner != source_section.owner or source_section.frame != source_section.landmark.frame:
            _fail(f"torso station {source_section.name} lost its authored frame/landmark binding")
        center = _owner_point(owner, scale, variant_section.position, f"torso.{source_section.name}")
        radii = np.asarray(tuple(
            _positive_float(getattr(variant_section, f"{axis}_radius_permille", None), f"torso.{source_section.name}.{axis}") / 1000.0
            for axis in ("lateral", "anterior", "posterior")
        ), dtype=np.float64)
        source_centers.append(center.copy())
        source_radii.append(radii)

    stations: list[Any] = []
    station_evidence: list[dict[str, Any]] = []
    for index, (source_section, variant_section) in enumerate(zip(authored, projected)):
        center = source_centers[index]
        source_value = source_radii[index]
        if source_section.name == "waist-abdomen":
            radii_array = np.maximum(
                source_value,
                0.88 * np.minimum(source_radii[2], source_radii[4]),
            )
            derivation = "max(source,0.88*min(lower-abdomen,upper-abdomen))"
        elif source_section.name == "upper-ribcage-shoulder":
            factors = np.asarray(TORSO_RADIUS_FACTORS[source_section.name], dtype=np.float64)
            radii_array = np.minimum(source_value, source_radii[5] * factors)
            derivation = "min(source,lower-ribcage*(0.86,0.82,0.82))"
        elif source_section.name == "upper-pelvis":
            factors = np.asarray(TORSO_RADIUS_FACTORS[source_section.name], dtype=np.float64)
            final_lower_pelvis = source_radii[0] * np.asarray(
                TORSO_RADIUS_FACTORS["lower-pelvis"], dtype=np.float64,
            )
            radii_array = np.minimum(source_value * factors, final_lower_pelvis)
            derivation = "min(source*(0.98,0.90,0.92),final-lower-pelvis)"
        else:
            factors = np.asarray(TORSO_RADIUS_FACTORS[source_section.name], dtype=np.float64)
            radii_array = source_value * factors
            derivation = "source*" + repr(tuple(float(item) for item in factors))
        radii = tuple(float(item) for item in radii_array)
        station_key = f"station:{source_section.name}:{_key_text(source_section.owner)}"
        stations.append(
            hybrid.AxialStation(
                source_section.name,
                float(center[1]),
                _tuple3(center, f"torso.{source_section.name}.center"),
                radii,
                station_key,
            )
        )
        station_evidence.append(
            {
                "index": index,
                "name": source_section.name,
                "owner": _key_json(source_section.owner),
                "semantic_key": station_key,
                "center": [float(value) for value in center],
                "position": [float(value) for value in variant_section.position],
                "source_index": index,
                "source_center": [float(value) for value in source_centers[index]],
                "source_radii": [float(value) for value in source_value],
                "derivation": derivation,
                "radii": [float(value) for value in radii],
                "source_frame": {"owner": _key_json(source_section.frame[0]), "role": source_section.frame[1]},
                "source_landmark": source_section.landmark.role,
                "radius_controls": [
                    {"owner": _key_json(control.owner), "role": control.role, "source_index": control.source_index}
                    for control in (source_section.lateral, source_section.anterior, source_section.posterior)
                ],
            }
        )

    regions = _make_regions(hybrid)
    region_evidence = []
    for index, (region, (start, end)) in enumerate(zip(regions, _REGION_INTERVALS)):
        region_evidence.append(
            {
                "index": index,
                "name": region.name,
                "interval": [start, end],
                "semantic_key": region.semantic_key,
                "interior_lateral_axis": list(region.basis.lateral_axis),
                "start_seam_lateral_axis": list(region.first_basis.lateral_axis),
                "end_seam_lateral_axis": list(region.last_basis.lateral_axis),
                "shared_seam_with_next": index < len(regions) - 1,
            }
        )
    evidence = tuple(station_evidence)
    return tuple(stations), regions, {"stations": station_evidence, "regions": region_evidence}, evidence


def _source_shape_radii(source: dict[str, Any], where: str) -> tuple[float, float, float]:
    if source.get("name") == "ellipsoid":
        return tuple(_positive_float(value, f"{where}.radius") for value in source["radii"])
    if source.get("name") in {"capsule", "tapered-segment"}:
        return tuple(_positive_float(max(float(source["r0"]), float(source["r1"])), f"{where}.radius") for _ in range(3))
    _fail(f"{where} has an unsupported source shape")


def _source_section_center(owner: Any, source: dict[str, Any], role: str, position: Any, scale: float, where: str) -> np.ndarray:
    local = _vec3(position, f"{where}.position") / scale
    if source["name"] in {"capsule", "tapered-segment"}:
        start = np.asarray(source["from"], dtype=np.float64)
        end = np.asarray(source["to"], dtype=np.float64)
        if role == "neck":
            center = np.asarray(getattr(owner, "point", None), dtype=np.float64) + local
        else:
            fraction = -float(position[1])
            if not -_GEOMETRY_TOLERANCE <= fraction <= 1.0 + _GEOMETRY_TOLERANCE:
                _fail(f"{where} source-local station is outside its segment")
            center = start + float(np.clip(fraction, 0.0, 1.0)) * (end - start)
    else:
        center = np.asarray(getattr(owner, "point", None), dtype=np.float64) + local
    return _vec3(center, f"{where}.center")


def _section_station(
    form: Any,
    by_key: dict[Any, Any],
    frame_by_key: dict[Any, Any],
    authored: Any,
    projected: Any,
    route_name: str,
    section_index: int,
    expected_role: str,
    frame_role: str,
    module: Any,
    hybrid: Any,
    *,
    route_position: float | None = None,
) -> tuple[Any, dict[str, Any]]:
    scale = _positive_float(form.reference_scale, "prepared form reference_scale")
    if (
        authored.section_index != section_index
        or projected.source_section_index != section_index
        or projected.name != authored.name
    ):
        _fail(f"{route_name} section {authored.name!r} lost source section order")
    if tuple(projected.position) != tuple(authored.landmark.position):
        _fail(f"{route_name} section {authored.name!r} lost its source landmark position")
    owner = by_key.get(authored.owner)
    if owner is None or owner.key != authored.owner or owner.key[3] != expected_role:
        _fail(f"{route_name} section {authored.name!r} lost descriptor ownership")
    if authored.landmark.owner != authored.owner or authored.frame != authored.landmark.frame:
        _fail(f"{route_name} section {authored.name!r} lost frame/landmark binding")
    frame_record = frame_by_key.get(authored.frame)
    if frame_record is None or frame_record.role != frame_role:
        _fail(f"{route_name} section {authored.name!r} lost its identity frame")
    source = _descriptor_source(module, owner, scale)
    center = _source_section_center(owner, source, expected_role, projected.position, scale, f"{route_name}.{authored.name}")
    radii = _projected_profile_radii3(projected)
    radii = tuple(_positive_float(value, f"{route_name}.{authored.name}.radius") for value in radii)
    source_key = _source_route_key(owner.key, f"{route_name}:{authored.name}")
    semantic_key = f"section:{route_name}:{authored.name}:{_key_text(owner.key)}"
    station_position = float(section_index if route_position is None else route_position)
    evidence_index: int | float = int(station_position) if station_position.is_integer() else station_position
    station = hybrid.SectionStation(
        authored.name,
        station_position,
        _tuple3(center, f"{route_name}.{authored.name}.center"),
        radii,
        semantic_key,
        source_key,
        int(projected.source_section_index),
    )
    evidence = {
        "index": evidence_index,
        "name": authored.name,
        "owner": _key_json(owner.key),
        "source_key": source_key,
        "semantic_key": semantic_key,
        "center": [float(value) for value in center],
        "radii": [float(value) for value in radii],
        "source_center": [float(value) for value in center],
        "source_radii": [float(value) for value in radii],
        "source_index": int(projected.source_section_index),
        "derived": False,
        "derivation": "projected source profile",
        "source_position": [float(value) for value in projected.position],
        "source_shape": {
            "name": source["name"],
            "center": [float(value) for value in source["center"]] if source["name"] == "ellipsoid" else None,
            "from": [float(value) for value in source["from"]] if source["name"] != "ellipsoid" else None,
            "to": [float(value) for value in source["to"]] if source["name"] != "ellipsoid" else None,
            "radii": list(_source_shape_radii(source, f"{route_name}.{authored.name}.source")),
        },
        "source_frame": {"owner": _key_json(authored.frame[0]), "role": authored.frame[1]},
        "source_landmark": {"role": authored.landmark.role, "owner": _key_json(authored.landmark.owner)},
        "profile_provenance": dict(projected.provenance),
    }
    return station, evidence


def _transform_section_station(
    hybrid: Any,
    station: Any,
    evidence: dict[str, Any],
    *,
    center: np.ndarray | None = None,
    radii: np.ndarray | tuple[float, float, float] | None = None,
    derivation: str,
    provenance: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Apply a named candidate derivation while retaining source identity."""

    selected_center = np.asarray(station.center if center is None else center, dtype=np.float64)
    selected_radii = np.asarray(station.radii if radii is None else radii, dtype=np.float64)
    selected_center = _vec3(selected_center, f"{station.name}.derived.center")
    selected_radii = np.asarray(
        tuple(_positive_float(value, f"{station.name}.derived.radius") for value in selected_radii),
        dtype=np.float64,
    )
    transformed = hybrid.SectionStation(
        station.name,
        station.position,
        _tuple3(selected_center, f"{station.name}.derived.center"),
        tuple(float(value) for value in selected_radii),
        station.semantic_key,
        station.source_key,
        station.source_index,
    )
    evidence = dict(evidence)
    evidence["source_center"] = list(evidence.get("source_center", station.center))
    evidence["source_radii"] = list(evidence.get("source_radii", station.radii))
    evidence["center"] = [float(value) for value in transformed.center]
    evidence["radii"] = [float(value) for value in transformed.radii]
    evidence["derived"] = bool(evidence.get("derived", False))
    evidence["transformed"] = True
    evidence["derivation"] = derivation
    if provenance is not None:
        evidence["provenance"] = provenance
    return transformed, evidence


def _route_attachment(hybrid: Any, route_name: str, field: Any, semantic_key: str) -> tuple[Any, dict[str, Any]]:
    """Register a complete route as a component, without route authority."""

    attachment = hybrid.SectionAttachment(route_name, field, None, None, semantic_key)
    lower, upper = field.bounds
    return attachment, {
        "name": route_name,
        "authority": None,
        "bounds": {"lower": [float(value) for value in lower], "upper": [float(value) for value in upper]},
        "blend_radius": None,
        "semantic_key": semantic_key,
        "skin_component": True,
    }


def _interface_authority(
    hybrid: Any,
    identifier: str,
    points: Iterable[Any],
    interface_radii: Iterable[Any],
    pad: float,
    authority_controls: Iterable[Any] = (),
    *,
    source_namespace: str | None = None,
    allow_control_subset: bool = False,
    control_subset_side: str | None = None,
) -> tuple[Any, float, dict[str, Any]]:
    """Derive one authority from interface samples and authority-only controls.

    The interface samples continue to determine ``k``.  Controls can only
    enlarge the finite authority volume; they are never scalar-field operands.
    """

    point_array = np.asarray(tuple(_vec3(point, f"{identifier}.point") for point in points), dtype=np.float64)
    radii_array = np.asarray(
        tuple(
            tuple(_positive_float(value, f"{identifier}.radius") for value in _vec3(radii, f"{identifier}.radii"))
            for radii in interface_radii
        ),
        dtype=np.float64,
    )
    if point_array.ndim != 2 or point_array.shape[0] == 0 or point_array.shape[1] != 3:
        _fail(f"{identifier} requires at least one interface point")
    if radii_array.shape != point_array.shape:
        _fail(f"{identifier} interface point/radius counts do not match")
    pad_value = _positive_float(pad, f"{identifier}.pad")
    padding_radii = np.max(radii_array, axis=0)
    lower = np.min(point_array, axis=0) - pad_value * padding_radii
    upper = np.max(point_array, axis=0) + pad_value * padding_radii
    control_records: list[dict[str, Any]] = []
    control_bindings: list[dict[str, Any]] = []
    controls_tuple = tuple(authority_controls)
    expected_namespace = _DEFAULT_SOURCE_NAMESPACE if source_namespace is None else source_namespace
    if controls_tuple and len(controls_tuple) != 2 and not allow_control_subset:
        _fail(f"{identifier} authority requires exactly one peak and one axilla control")
    if allow_control_subset and len(controls_tuple) not in {1, 2}:
        _fail(f"{identifier} counterfactual authority requires a non-empty exact control subset")
    for control in controls_tuple:
        binding = _validate_shoulder_control_identity(control, namespace=expected_namespace)
        if control_subset_side is not None and binding["side"] != control_subset_side:
            _fail(f"{identifier} counterfactual authority control has the wrong side")
        control_bindings.append(binding)
        center = _vec3(getattr(control, "center", None), f"{identifier}.authority-control.center")
        control_radii = np.asarray(
            tuple(
                _positive_float(value, f"{identifier}.authority-control.radius")
                for value in _vec3(getattr(control, "radii", None), f"{identifier}.authority-control.radii")
            ),
            dtype=np.float64,
        )
        name = binding["name"]
        semantic_key = binding["semantic_key"]
        source_key = binding["source_key"]
        lower = np.minimum(lower, center - control_radii)
        upper = np.maximum(upper, center + control_radii)
        control_records.append({
            "name": name,
            "center": [float(value) for value in center],
            "radii": [float(value) for value in control_radii],
            "semantic_key": semantic_key,
            "source_key": source_key,
            "canonical_source_key": source_key,
            "namespace": binding["namespace"],
            "side": binding["side"],
            "owner": _key_json(binding["owner"]),
            "role": binding["role"],
            "frame": {"owner": _key_json(binding["frame"][0]), "role": binding["frame"][1]},
        })
    if control_bindings and (
        {item["side"] for item in control_bindings} != {control_bindings[0]["side"]}
        or len({item["role"] for item in control_bindings}) != len(control_bindings)
        or (not allow_control_subset and {item["role"] for item in control_bindings} != set(_SHOULDER_CONTROL_ROLES))
    ):
        _fail(f"{identifier} authority controls are not one exact side-matched pair")
    center = (lower + upper) * 0.5
    authority_radii = (upper - lower) * 0.5
    authority = hybrid.AuthorityVolume(
        f"authority:{identifier}",
        _tuple3(center, f"{identifier}.authority.center"),
        _tuple3(authority_radii, f"{identifier}.authority.radii"),
        collar_fraction=INTERFACE_COLLAR_FRACTION,
    )
    normalized_interface_radii = authority.normalized_radius(point_array)
    if np.any(normalized_interface_radii > 1.0):
        _fail(f"{identifier} authority does not contain every declared interface point")
    blend_radius = INTERFACE_BLEND_FRACTION * float(np.min(radii_array))
    blend_radius = _positive_float(blend_radius, f"{identifier}.k")
    record = {
        "identifier": identifier,
        "points": [[float(value) for value in point] for point in point_array],
        "interface_radii": [[float(value) for value in radii] for radii in radii_array],
        "authority_controls": control_records,
        "pad": pad_value,
        "padding_radii": [float(value) for value in padding_radii],
        "lower": [float(value) for value in lower],
        "upper": [float(value) for value in upper],
        "center": [float(value) for value in center],
        "radii": [float(value) for value in authority_radii],
        "collar_fraction": INTERFACE_COLLAR_FRACTION,
        "blend_fraction": INTERFACE_BLEND_FRACTION,
        "k": blend_radius,
        "authority": authority.identifier,
        "contains_all_points": True,
        "max_point_normalized_radius": float(np.max(normalized_interface_radii)),
    }
    return authority, blend_radius, record


def _interface_patch(
    hybrid: Any,
    parent_name: str,
    child_name: str,
    parent: Any,
    child: Any,
    points: Iterable[Any],
    interface_radii: Iterable[Any],
    pad: float,
    semantic_key: str,
    authority_controls: Iterable[Any] = (),
    *,
    source_namespace: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    identifier = f"{parent_name}->{child_name}"
    authority, blend_radius, authority_record = _interface_authority(
        hybrid,
        identifier,
        points,
        interface_radii,
        pad,
        authority_controls,
        source_namespace=source_namespace,
    )
    patch = hybrid.ParentTargetedInterfacePatch(
        f"interface:{identifier}",
        parent_name,
        child_name,
        parent,
        child,
        authority,
        blend_radius,
        semantic_key,
    )
    return patch, {
        "identifier": patch.identifier,
        "parent": parent_name,
        "child": child_name,
        "authority": authority_record,
        "semantic_key": semantic_key,
    }


def _live_endpoint_trace_leaf(
    chain: Any,
    point: Any,
    station: Any,
    region: Any,
    lower: bool,
    where: str,
) -> Any:
    trace = chain.operation_trace(point)
    expected_dominance = "start-cap" if lower else "end-cap"
    if (
        trace.operator != "regional-axial-chain"
        or len(trace.children) != 1
        or trace.children[0].operator != "axial-cap-leaf"
        or trace.children[0].dominance != expected_dominance
    ):
        _fail(f"{where} is not consumed by the live endpoint constituent")
    leaf = trace.children[0]
    expected_keys = (station.semantic_key, region.semantic_key)
    if leaf.semantic_keys != expected_keys or leaf.value != trace.value:
        _fail(f"{where} has the wrong endpoint constituent trace")
    return leaf


def _derive_torso_arm_connector(
    hybrid: Any,
    chain: Any,
    parent_station: Any,
    terminal_region: Any,
    terminal_basis: Any,
    child_station: Any,
    torso_key: Any,
    upper_arm_key: Any,
    route_name: str,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Derive one connector from the exact live terminal cap constituent."""

    if not isinstance(chain, hybrid.AxialMassChain):
        _fail(f"{route_name} connector parent must be the live axial mass chain")
    if route_name not in {"left-arm", "right-arm"}:
        _fail(f"{route_name} connector has the wrong side-specific route owner")
    if parent_station.name != "upper-ribcage-shoulder" or child_station.name != "upper-arm-start":
        _fail(f"{route_name} connector requires terminal torso and upper-arm-start stations")
    expected_parent_semantic_key = f"station:{parent_station.name}:{_key_text(torso_key)}"
    expected_child_source_key = _source_route_key(upper_arm_key, f"{route_name}:upper-arm-start")
    expected_child_semantic_key = f"section:{route_name}:upper-arm-start:{_key_text(upper_arm_key)}"
    if parent_station.semantic_key != expected_parent_semantic_key:
        _fail(f"{route_name} connector has the wrong terminal torso owner")
    if (
        child_station.source_index != 0
        or child_station.source_key != expected_child_source_key
        or child_station.semantic_key != expected_child_semantic_key
    ):
        _fail(f"{route_name} connector has the wrong upper-arm source binding")

    constituent = chain._terminal_constituent(parent_station, terminal_region, terminal_basis)
    connector_radii = np.minimum(
        np.asarray(parent_station.radii, dtype=np.float64),
        np.asarray(child_station.radii, dtype=np.float64),
    )
    mu = ENDPOINT_CONNECTOR_DEPTH_FRACTION * float(np.min(connector_radii))
    boundary_center, connector_center, rho = constituent.analytic_ray_boundary_and_interior(
        child_station.center,
        mu,
    )
    boundary_value = float(constituent.evaluate(boundary_center))
    constituent_value = float(constituent.evaluate(connector_center))
    parent_value = float(chain.evaluate(connector_center))
    boundary_leaf = _live_endpoint_trace_leaf(
        chain, boundary_center, parent_station, terminal_region, False, f"{route_name} connector boundary",
    )
    interior_leaf = _live_endpoint_trace_leaf(
        chain, connector_center, parent_station, terminal_region, False, f"{route_name} connector interior",
    )
    if abs(boundary_value) > _GEOMETRY_TOLERANCE or boundary_leaf.value != float(chain.evaluate(boundary_center)):
        _fail(f"{route_name} connector did not reconstruct the terminal constituent boundary")
    if abs(constituent_value + mu) > _GEOMETRY_TOLERANCE:
        _fail(f"{route_name} connector did not reconstruct negative mu")
    if parent_value > constituent_value or interior_leaf.value != parent_value:
        _fail(f"{route_name} connector parent is not bounded by its live terminal constituent")

    connector_source_key = (
        f"derived-torso-arm-interface:torso={_key_text(torso_key)}:upper-arm={_key_text(upper_arm_key)}"
    )
    connector_semantic_key = f"section:{route_name}:torso-arm-interface:{connector_source_key}"
    connector_station = hybrid.SectionStation(
        "torso-arm-interface",
        float(child_station.position) - 1.0,
        _tuple3(connector_center, f"{route_name}.torso-arm-interface.center"),
        tuple(float(value) for value in connector_radii),
        connector_semantic_key,
        connector_source_key,
        None,
    )
    evidence = {
        "index": -1,
        "name": connector_station.name,
        "source_index": None,
        "derived": True,
        "center": list(connector_station.center),
        "radii": list(connector_station.radii),
        "derivation": "analytic terminal-constituent ellipsoid ray boundary/interior at normalized level 1-mu/constituent-field-scale",
        "source_key": connector_source_key,
        "semantic_key": connector_semantic_key,
        "constituent_boundary_center": [float(value) for value in boundary_center],
        "constituent_boundary_value": boundary_value,
        "constituent_interior_value": constituent_value,
        "parent_value_at_interior": parent_value,
        "mu": mu,
        "rho": rho,
        "constituent_field_scale": constituent.field_scale,
        "parent_depth_fraction": ENDPOINT_CONNECTOR_DEPTH_FRACTION,
        "provenance": {
            "kind": "torso+upper-arm",
            "torso": _key_json(torso_key),
            "upper_arm": _key_json(upper_arm_key),
            "torso_station": parent_station.name,
            "upper_arm_station": child_station.name,
            "upper_arm_source_index": child_station.source_index,
            "terminal_region": terminal_region.name,
            "terminal_region_semantic_key": terminal_region.semantic_key,
        },
    }
    return connector_station, evidence, {
        "constituent": constituent,
        "connector": connector_station,
        "child": child_station,
        "evidence": evidence,
    }


def _certify_torso_arm_overlap(hybrid: Any, chain: Any, route: Any, context: dict[str, Any]) -> None:
    """Record exact finite-open-overlap operands for one completed arm route."""

    if not isinstance(chain, hybrid.AxialMassChain) or not isinstance(route, hybrid.AnisotropicSectionSweep):
        _fail("torso-arm overlap certificate requires live chain and arm route operands")
    if len(route.sections) != 6 or len(route.connections) != 5:
        _fail(f"{route.route_name} overlap certificate requires exact six-station/five-span inventory")
    connector = context["connector"]
    child = context["child"]
    constituent = context["constituent"]
    if route.sections[0] is not connector or route.sections[1] is not child:
        _fail(f"{route.route_name} overlap certificate has the wrong connector or child object identity")
    if constituent.chain is not chain or constituent.station is not chain.stations[-1]:
        _fail(f"{route.route_name} overlap certificate has the wrong parent constituent identity")
    connector_span = route.connections[0]
    authored_arm_span = route.connections[1]
    if (connector_span.from_section_index, connector_span.to_section_index) != (0, 1):
        _fail(f"{route.route_name} overlap certificate has the wrong connector span")
    if (authored_arm_span.from_section_index, authored_arm_span.to_section_index) != (1, 2):
        _fail(f"{route.route_name} overlap certificate has the wrong authored arm span")

    interior = np.asarray(connector.center, dtype=np.float64).reshape(1, 3)
    child_point = np.asarray(child.center, dtype=np.float64).reshape(1, 3)
    constituent_at_interior = float(constituent.evaluate(interior[0]))
    parent_at_interior = float(chain.evaluate(interior[0]))
    connector_at_interior = float(route._connection_value(interior, connector_span)[0])
    connector_at_child = float(route._connection_value(child_point, connector_span)[0])
    authored_arm_at_child = float(route._connection_value(child_point, authored_arm_span)[0])
    positive_connector_radii = bool(
        np.all(np.asarray(connector.radii, dtype=np.float64) > 0.0)
        and np.all(np.asarray(child.radii, dtype=np.float64) > 0.0)
    )
    if not (
        constituent_at_interior < 0.0
        and parent_at_interior <= constituent_at_interior
        and connector_at_interior < 0.0
        and positive_connector_radii
        and connector_at_child < 0.0
        and authored_arm_at_child < 0.0
    ):
        _fail(f"{route.route_name} lacks the required finite open torso-arm overlap")
    context["evidence"]["finite_open_overlap_certificate"] = {
        "kind": "finite-open-overlap",
        "parent_operand": "live-terminal-constituent-ellipsoid",
        "connector_operand": connector_span.name,
        "authored_arm_operand": authored_arm_span.name,
        "constituent_at_interior": constituent_at_interior,
        "parent_at_interior": parent_at_interior,
        "connector_at_interior": connector_at_interior,
        "positive_connector_radii_along_centerline": positive_connector_radii,
        "connector_at_upper_arm_start": connector_at_child,
        "authored_arm_at_upper_arm_start": authored_arm_at_child,
    }


def _derive_pelvis_leg_connector(
    hybrid: Any,
    chain: Any,
    parent_station: Any,
    initial_region: Any,
    initial_basis: Any,
    hip_station: Any,
    thigh_station: Any,
    pelvis_key: Any,
    thigh_key: Any,
    route_name: str,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Derive one pelvis-leg connector from the exact live initial cap."""

    if not isinstance(chain, hybrid.AxialMassChain):
        _fail(f"{route_name} connector parent must be the live axial mass chain")
    if route_name not in {"left-leg", "right-leg"}:
        _fail(f"{route_name} connector has the wrong side-specific leg owner")
    if (
        parent_station.name != "lower-pelvis"
        or hip_station.name != "hip-interface"
        or thigh_station.name != "thigh-start"
    ):
        _fail(f"{route_name} connector requires lower-pelvis, hip-interface and thigh-start stations")
    expected_parent_semantic_key = f"station:{parent_station.name}:{_key_text(pelvis_key)}"
    expected_hip_source_key = f"derived-hip-interface:thigh={_key_text(thigh_key)}:pelvis={_key_text(pelvis_key)}"
    expected_hip_semantic_key = f"section:{route_name}:hip-interface:{expected_hip_source_key}"
    expected_thigh_source_key = _source_route_key(thigh_key, f"{route_name}:thigh-start")
    expected_thigh_semantic_key = f"section:{route_name}:thigh-start:{_key_text(thigh_key)}"
    if parent_station.semantic_key != expected_parent_semantic_key:
        _fail(f"{route_name} connector has the wrong lower-pelvis owner")
    if (
        hip_station.source_index is not None
        or hip_station.source_key != expected_hip_source_key
        or hip_station.semantic_key != expected_hip_semantic_key
    ):
        _fail(f"{route_name} connector has the wrong derived hip binding")
    if (
        thigh_station.source_index != 0
        or thigh_station.source_key != expected_thigh_source_key
        or thigh_station.semantic_key != expected_thigh_semantic_key
    ):
        _fail(f"{route_name} connector has the wrong thigh-start source binding")

    constituent = chain._initial_constituent(parent_station, initial_region, initial_basis)
    connector_radii = np.minimum.reduce((
        np.asarray(parent_station.radii, dtype=np.float64),
        np.asarray(hip_station.radii, dtype=np.float64),
        np.asarray(thigh_station.radii, dtype=np.float64),
    ))
    mu = ENDPOINT_CONNECTOR_DEPTH_FRACTION * float(np.min(connector_radii))
    boundary_center, connector_center, rho = constituent.analytic_ray_boundary_and_interior(
        hip_station.center,
        mu,
    )
    boundary_value = float(constituent.evaluate(boundary_center))
    constituent_value = float(constituent.evaluate(connector_center))
    parent_value = float(chain.evaluate(connector_center))
    boundary_leaf = _live_endpoint_trace_leaf(
        chain, boundary_center, parent_station, initial_region, True, f"{route_name} connector boundary",
    )
    interior_leaf = _live_endpoint_trace_leaf(
        chain, connector_center, parent_station, initial_region, True, f"{route_name} connector interior",
    )
    if abs(boundary_value) > _GEOMETRY_TOLERANCE or boundary_leaf.value != float(chain.evaluate(boundary_center)):
        _fail(f"{route_name} connector did not reconstruct the initial constituent boundary")
    if abs(constituent_value + mu) > _GEOMETRY_TOLERANCE:
        _fail(f"{route_name} connector did not reconstruct negative mu")
    if parent_value > constituent_value or interior_leaf.value != parent_value:
        _fail(f"{route_name} connector parent is not bounded by its live initial constituent")

    connector_source_key = f"derived-pelvis-leg-interface:pelvis={_key_text(pelvis_key)}:thigh={_key_text(thigh_key)}"
    connector_semantic_key = f"section:{route_name}:pelvis-leg-interface:{connector_source_key}"
    connector_station = hybrid.SectionStation(
        "pelvis-leg-interface",
        float(hip_station.position) - 1.0,
        _tuple3(connector_center, f"{route_name}.pelvis-leg-interface.center"),
        tuple(float(value) for value in connector_radii),
        connector_semantic_key,
        connector_source_key,
        None,
    )
    evidence = {
        "index": -1,
        "name": connector_station.name,
        "source_index": None,
        "derived": True,
        "center": list(connector_station.center),
        "radii": list(connector_station.radii),
        "derivation": "analytic initial-constituent ellipsoid ray boundary/interior at normalized level 1-mu/constituent-field-scale",
        "source_key": connector_source_key,
        "semantic_key": connector_semantic_key,
        "constituent_boundary_center": [float(value) for value in boundary_center],
        "constituent_boundary_value": boundary_value,
        "constituent_interior_value": constituent_value,
        "parent_value_at_interior": parent_value,
        "mu": mu,
        "rho": rho,
        "constituent_field_scale": constituent.field_scale,
        "parent_depth_fraction": ENDPOINT_CONNECTOR_DEPTH_FRACTION,
        "provenance": {
            "kind": "pelvis+thigh",
            "pelvis": _key_json(pelvis_key),
            "thigh": _key_json(thigh_key),
            "pelvis_station": parent_station.name,
            "hip_interface_station": hip_station.name,
            "thigh_start_station": thigh_station.name,
            "thigh_start_source_index": thigh_station.source_index,
            "initial_region": initial_region.name,
            "initial_region_semantic_key": initial_region.semantic_key,
        },
    }
    return connector_station, evidence, {
        "constituent": constituent,
        "connector": connector_station,
        "hip": hip_station,
        "thigh": thigh_station,
        "evidence": evidence,
    }


def _route_section(route: Any, name: str, where: str) -> Any:
    matches = tuple(section for section in route.sections if section.name == name)
    if len(matches) != 1:
        _fail(f"{where} requires exactly one {name} section")
    return matches[0]


def _route_section_from_sequence(sections: Iterable[Any], name: str, where: str) -> Any:
    matches = tuple(section for section in sections if section.name == name)
    if len(matches) != 1:
        _fail(f"{where} requires exactly one {name} section")
    return matches[0]


def _route_connection(route: Any, from_name: str, to_name: str, where: str) -> Any:
    matches = tuple(
        connection
        for connection in route.connections
        if route.sections[connection.from_section_index].name == from_name
        and route.sections[connection.to_section_index].name == to_name
    )
    if len(matches) != 1:
        _fail(f"{where} requires exactly one {from_name}-to-{to_name} connection")
    return matches[0]


def _derive_pelvis_hip_cup_chain(
    hybrid: Any,
    chain: Any,
    parent_station: Any,
    initial_region: Any,
    initial_basis: Any,
    thigh_station: Any,
    pelvis_key: Any,
    thigh_key: Any,
    route_name: str,
) -> tuple[tuple[Any, ...], tuple[dict[str, Any], ...], dict[str, Any]]:
    """Derive the shared three-section hip-cup prefix from live pelvis data."""

    if not isinstance(chain, hybrid.AxialMassChain):
        _fail(f"{route_name} hip cup parent must be the live axial mass chain")
    if route_name not in {"left-leg", "right-leg"}:
        _fail(f"{route_name} hip cup has the wrong side-specific leg owner")
    if parent_station.name != "lower-pelvis" or thigh_station.name != "thigh-start":
        _fail(f"{route_name} hip cup requires lower-pelvis and thigh-start stations")
    expected_parent_semantic_key = f"station:{parent_station.name}:{_key_text(pelvis_key)}"
    expected_thigh_source_key = _source_route_key(thigh_key, f"{route_name}:thigh-start")
    expected_thigh_semantic_key = f"section:{route_name}:thigh-start:{_key_text(thigh_key)}"
    if parent_station.semantic_key != expected_parent_semantic_key:
        _fail(f"{route_name} hip cup has the wrong lower-pelvis owner")
    if (
        thigh_station.source_index != 0
        or thigh_station.source_key != expected_thigh_source_key
        or thigh_station.semantic_key != expected_thigh_semantic_key
    ):
        _fail(f"{route_name} hip cup has the wrong thigh-start source binding")

    constituent = chain._initial_constituent(parent_station, initial_region, initial_basis)
    pelvis_radii = np.asarray(parent_station.radii, dtype=np.float64)
    thigh_radii = np.asarray(thigh_station.radii, dtype=np.float64)
    rim_radii = np.minimum(pelvis_radii, thigh_radii)
    mu = HIP_CUP_SEAT_DEPTH_FRACTION * float(np.min(rim_radii))
    boundary_center, seat_center_raw, rho = constituent.analytic_ray_boundary_and_interior(
        thigh_station.center,
        mu,
    )
    boundary_value = float(constituent.evaluate(boundary_center))
    seat_value = float(constituent.evaluate(seat_center_raw))
    parent_value = float(chain.evaluate(seat_center_raw))
    boundary_leaf = _live_endpoint_trace_leaf(
        chain, boundary_center, parent_station, initial_region, True, f"{route_name} hip-cup-rim boundary",
    )
    interior_leaf = _live_endpoint_trace_leaf(
        chain, seat_center_raw, parent_station, initial_region, True, f"{route_name} pelvis-seat interior",
    )
    if abs(boundary_value) > _GEOMETRY_TOLERANCE or boundary_leaf.value != float(chain.evaluate(boundary_center)):
        _fail(f"{route_name} hip-cup-rim did not reconstruct the live pelvis boundary")
    if not (0.0 < rho < 1.0 and seat_value < 0.0 and abs(seat_value + mu) <= _GEOMETRY_TOLERANCE):
        _fail(f"{route_name} pelvis-seat is not strictly inside the live pelvis constituent")
    if parent_value > seat_value or interior_leaf.value != parent_value:
        _fail(f"{route_name} pelvis-seat parent is not bounded by its live constituent")
    if not np.all(rim_radii <= np.minimum(pelvis_radii, thigh_radii)):
        _fail(f"{route_name} hip-cup-rim radii exceed the pelvis/thigh bound")
    rim_center = _tuple3(boundary_center, f"{route_name}.hip-cup-rim.center")
    seat_center = _tuple3(seat_center_raw, f"{route_name}.pelvis-seat.center")
    thigh_center = np.asarray(thigh_station.center, dtype=np.float64)
    neck_center = np.asarray(rim_center, dtype=np.float64) + FEMORAL_NECK_CENTER_FACTOR * (
        thigh_center - np.asarray(rim_center, dtype=np.float64)
    )
    neck_radii = FEMORAL_NECK_RADIUS_FACTOR * rim_radii
    if not (0.0 < FEMORAL_NECK_CENTER_FACTOR < 1.0 and np.all(neck_radii < rim_radii)):
        _fail(f"{route_name} femoral-neck is not a narrower seated-root transition")

    provenance = {
        "kind": "pelvis+thigh",
        "pelvis": _key_json(pelvis_key),
        "thigh": _key_json(thigh_key),
        "pelvis_station": parent_station.name,
        "thigh_start_station": thigh_station.name,
        "thigh_start_source_index": thigh_station.source_index,
        "initial_region": initial_region.name,
        "initial_region_semantic_key": initial_region.semantic_key,
    }

    common_evidence = {
        "constituent_boundary_center": [float(value) for value in boundary_center],
        "constituent_boundary_value": boundary_value,
        "constituent_field_scale": constituent.field_scale,
        "seat_constituent_value": seat_value,
        "seat_parent_value": parent_value,
        "mu": mu,
        "rho": rho,
        "seat_depth_fraction": HIP_CUP_SEAT_DEPTH_FRACTION,
        "rim_radius_factor": HIP_CUP_RIM_RADIUS_FACTOR,
        "neck_center_factor": FEMORAL_NECK_CENTER_FACTOR,
        "neck_radius_factor": FEMORAL_NECK_RADIUS_FACTOR,
    }

    def make_derived(
        name: str,
        position: float,
        center: tuple[float, float, float],
        radii: np.ndarray,
        derivation: str,
        source_key: str,
    ) -> tuple[Any, dict[str, Any]]:
        semantic_key = f"section:{route_name}:{name}:{source_key}"
        station = hybrid.SectionStation(
            name,
            position,
            center,
            tuple(float(value) for value in radii),
            semantic_key,
            source_key,
            None,
        )
        return station, {
            "index": int(position),
            "route_index": int(position + 2),
            "name": name,
            "source_index": None,
            "derived": True,
            "center": list(station.center),
            "radii": list(station.radii),
            "derivation": derivation,
            "source_key": source_key,
            "semantic_key": semantic_key,
            "provenance": dict(provenance),
            **common_evidence,
        }

    seat, seat_evidence = make_derived(
        "pelvis-seat",
        -2.0,
        seat_center,
        rim_radii,
        "analytic live initial-constituent interior toward authored thigh-start",
        f"derived-pelvis-seat:pelvis={_key_text(pelvis_key)}:thigh={_key_text(thigh_key)}",
    )
    rim, rim_evidence = make_derived(
        "hip-cup-rim",
        -1.0,
        rim_center,
        HIP_CUP_RIM_RADIUS_FACTOR * rim_radii,
        "analytic live initial-constituent ray boundary toward authored thigh-start",
        f"derived-hip-cup-rim:pelvis={_key_text(pelvis_key)}:thigh={_key_text(thigh_key)}",
    )
    neck, neck_evidence = make_derived(
        "femoral-neck",
        0.0,
        _tuple3(neck_center, f"{route_name}.femoral-neck.center"),
        neck_radii,
        "hip-cup-rim+0.55*(authored-thigh-start-hip-cup-rim);hip-cup-rim-radii*0.72",
        f"derived-femoral-neck:pelvis={_key_text(pelvis_key)}:thigh={_key_text(thigh_key)}",
    )
    return (seat, rim, neck), (seat_evidence, rim_evidence, neck_evidence), {
        "constituent": constituent,
        "seat": seat,
        "rim": rim,
        "neck": neck,
        "thigh": thigh_station,
        "evidence": (seat_evidence, rim_evidence, neck_evidence),
    }


def _certify_pelvis_leg_overlap(hybrid: Any, chain: Any, route: Any, context: dict[str, Any]) -> None:
    """Certify every adjacent span in the named hip-cup chain."""

    if not isinstance(chain, hybrid.AxialMassChain) or not isinstance(route, hybrid.AnisotropicSectionSweep):
        _fail("pelvis-leg overlap certificate requires live chain and leg route operands")
    if len(route.sections) != 8 or len(route.connections) != 7:
        _fail(f"{route.route_name} overlap certificate requires exact eight-station/seven-span inventory")
    if tuple(section.name for section in route.sections[:4]) != (*_HIP_CUP_NAMES, "thigh-start"):
        _fail(f"{route.route_name} overlap certificate has the wrong named cup order")
    seat = _route_section(route, "pelvis-seat", route.route_name)
    rim = _route_section(route, "hip-cup-rim", route.route_name)
    neck = _route_section(route, "femoral-neck", route.route_name)
    thigh = _route_section(route, "thigh-start", route.route_name)
    constituent = context["constituent"]
    if seat is not context["seat"] or rim is not context["rim"] or neck is not context["neck"] or thigh is not context["thigh"]:
        _fail(f"{route.route_name} overlap certificate has the wrong cup or thigh object identity")
    if constituent.chain is not chain or constituent.station is not chain.stations[0] or not constituent.lower:
        _fail(f"{route.route_name} overlap certificate has the wrong parent constituent identity")
    spans = tuple(
        _route_connection(route, from_name, to_name, route.route_name)
        for from_name, to_name in (
            ("pelvis-seat", "hip-cup-rim"),
            ("hip-cup-rim", "femoral-neck"),
            ("femoral-neck", "thigh-start"),
        )
    )
    samples = np.linspace(0.0, 1.0, 33, dtype=np.float64)
    span_certificate = []
    for connection in spans:
        start = np.asarray(route.sections[connection.from_section_index].center, dtype=np.float64)
        end = np.asarray(route.sections[connection.to_section_index].center, dtype=np.float64)
        points = start[None, :] + samples[:, None] * (end - start)[None, :]
        values = np.asarray(route._connection_value(points, connection), dtype=np.float64)
        if not np.all(np.isfinite(values)) or not np.all(values < 0.0):
            _fail(f"{route.route_name} has a non-open adjacent hip-cup span: {connection.name}")
        span_certificate.append({"name": connection.name, "max_value": float(np.max(values)), "sample_count": len(values)})

    interior = np.asarray(seat.center, dtype=np.float64)
    constituent_at_interior = float(constituent.evaluate(interior))
    parent_at_interior = float(chain.evaluate(interior))
    boundary_value = float(constituent.evaluate(rim.center))
    positive_radii = bool(
        np.all(np.asarray(seat.radii, dtype=np.float64) > 0.0)
        and np.all(np.asarray(rim.radii, dtype=np.float64) > 0.0)
        and np.all(np.asarray(neck.radii, dtype=np.float64) > 0.0)
        and np.all(np.asarray(thigh.radii, dtype=np.float64) > 0.0)
    )
    if not (
        constituent_at_interior < 0.0
        and parent_at_interior <= constituent_at_interior
        and abs(boundary_value) <= _GEOMETRY_TOLERANCE
        and positive_radii
    ):
        _fail(f"{route.route_name} lacks the required finite open hip-cup overlap")
    certificate = {
        "kind": "finite-open-overlap-through-named-hip-cup-chain",
        "parent_operand": "live-initial-constituent-ellipsoid",
        "seat_operand": "pelvis-seat",
        "rim_operand": "hip-cup-rim",
        "neck_operand": "femoral-neck",
        "authored_thigh_operand": "thigh-start",
        "constituent_at_interior": constituent_at_interior,
        "parent_at_interior": parent_at_interior,
        "rim_constituent_boundary_value": boundary_value,
        "adjacent_cup_spans": span_certificate,
        "positive_radii_along_both_centerlines": positive_radii,
    }
    for evidence in context["evidence"]:
        evidence["finite_open_overlap_certificate"] = certificate


def _make_full_routes(
    form: Any,
    descriptors: tuple[Any, ...],
    variant_index: int,
    module: Any,
    hybrid: Any,
    chain: Any,
) -> tuple[tuple[Any, ...], tuple[Any, ...], tuple[Any, ...], dict[str, Any], tuple[dict[str, Any], ...]]:
    """Build complete routes while retaining each source station identity."""

    namespace = form.source["namespace"]
    by_key = _descriptor_map(descriptors, namespace)
    frame_by_key = {(frame.owner, frame.role): frame for frame in form.authored_frames}
    route_records: list[dict[str, Any]] = []
    binding_evidence: list[dict[str, Any]] = []
    routes: list[Any] = []
    attachments: list[Any] = []

    def make_route_record(
        route_name: str,
        kind: str,
        side: str | None,
        route: Any,
        section_evidence: list[dict[str, Any]],
        attachment_evidence: dict[str, Any],
        shared_station_indices: list[int],
        authored_section_count: int | None = None,
    ) -> None:
        record = {
            "name": route_name,
            "kind": kind,
            "side": side,
            "section_count": len(route.sections),
            "sections": section_evidence,
            "connection_count": len(route.connections),
            "connections": [
                {
                    "name": item.name,
                    "from_section_index": item.from_section_index,
                    "to_section_index": item.to_section_index,
                    "route": item.route,
                }
                for item in route.connections
            ],
            "shared_station_indices": shared_station_indices,
            "endpoint_closures": [
                {"name": item.name, "center": list(item.center), "radii": list(item.radii), "source_key": item.source_key}
                for item in route.endpoint_closures
            ],
            "attachment": attachment_evidence,
        }
        if authored_section_count is not None:
            record["authored_section_count"] = authored_section_count
            record["section_names"] = [item.name for item in route.sections]
        route_records.append(record)

    def transform_route_station(
        authored: Any,
        projected: Any,
        route_name: str,
        section_index: int,
        expected_role: str,
        frame_role: str,
        projected_sections: tuple[Any, ...],
        *,
        route_position: float | None = None,
        joint_next_radii: np.ndarray | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        station, evidence = _section_station(
            form, by_key, frame_by_key, authored, projected, route_name, section_index,
            expected_role, frame_role, module, hybrid, route_position=route_position,
        )
        source_radii = np.asarray(station.radii, dtype=np.float64)
        derived_radii: np.ndarray | None = None
        derivation = "projected source profile"
        if authored.name in MIDPOINT_BELLY_FACTORS:
            factor = MIDPOINT_BELLY_FACTORS[authored.name]
            derived_radii = source_radii * factor
            derivation = f"source*{factor:g}"
        if authored.name in {"elbow", "knee", "hock-endpoint"}:
            previous = np.asarray(_projected_profile_radii3(projected_sections[authored.section_index - 1]), dtype=np.float64)
            following = (
                np.asarray(_projected_profile_radii3(projected_sections[authored.section_index + 1]), dtype=np.float64)
                if joint_next_radii is None
                else joint_next_radii
            )
            derived_radii = np.minimum(source_radii, JOINT_RADIUS_FACTOR * np.minimum(previous, following))
            derivation = "min(source,0.82*min(previous,next))"
        if derived_radii is not None:
            station, evidence = _transform_section_station(
                hybrid, station, evidence, radii=derived_radii,
                derivation=derivation,
            )
        return station, evidence

    authored_head = tuple(form.authored_head_neck_profile.sections)
    projected_head = tuple(form.variant_head_neck_profiles[variant_index].sections)
    authored_connections = tuple(form.authored_head_neck_profile.connections)
    projected_connections = tuple(form.variant_head_neck_profiles[variant_index].connections)
    if tuple(item.name for item in authored_head) != _HEAD_NECK_NAMES or tuple(item.name for item in projected_head) != _HEAD_NECK_NAMES:
        _fail("head/neck route does not contain the exact eight source sections")
    if projected_connections != authored_connections or tuple(
        (item.name, item.from_section_index, item.to_section_index, item.route) for item in authored_connections
    ) != _HEAD_NECK_CONNECTIONS:
        _fail("head/neck route does not retain the exact seven source connections")
    head_source_stations: list[Any] = []
    head_evidence: list[dict[str, Any]] = []
    for index, (authored, projected) in enumerate(zip(authored_head, projected_head)):
        station, evidence = _section_station(
            form, by_key, frame_by_key, authored, projected, "head-neck", index,
            "neck" if index < 2 else "head", module.HEAD_NECK_PROFILE_FRAME_ROLE, module, hybrid,
        )
        head_source_stations.append(station)
        head_evidence.append(evidence)
    muzzle_root_center = np.asarray(head_source_stations[5].center, dtype=np.float64)
    head_sections: list[Any] = []
    transformed_head_evidence: list[dict[str, Any]] = []
    for station, evidence in zip(head_source_stations, head_evidence):
        radii = None
        center = None
        derivation_parts: list[str] = []
        if station.name in HEAD_RADIUS_FACTORS:
            radii = np.asarray(station.radii, dtype=np.float64) * np.asarray(HEAD_RADIUS_FACTORS[station.name], dtype=np.float64)
            derivation_parts.append(f"source*{HEAD_RADIUS_FACTORS[station.name]}")
        if station.name in MUZZLE_CENTER_FACTORS:
            factor = MUZZLE_CENTER_FACTORS[station.name]
            center = muzzle_root_center + factor * (np.asarray(station.center, dtype=np.float64) - muzzle_root_center)
            derivation_parts.append(f"root+{factor:g}*(source-root)")
        if derivation_parts:
            station, evidence = _transform_section_station(
                hybrid, station, evidence, center=center, radii=radii,
                derivation=";".join(derivation_parts),
            )
        head_sections.append(station)
        transformed_head_evidence.append(evidence)
    head_route_connections = tuple(
        hybrid.SectionConnection(item.name, item.from_section_index, item.to_section_index, item.route)
        for item in authored_connections
    )
    head_closures = tuple(
        hybrid.EndpointClosure(
            name,
            head_sections[index].center,
            head_sections[index].radii,
            f"closure:{name}:{_key_text(authored_head[index].owner)}",
            head_sections[index].source_key,
        )
        for name, index in (("neck-collar-closure", 0), ("cranium-crown-closure", 4), ("muzzle-tip-closure", 7))
    )
    head_route = hybrid.AnisotropicSectionSweep(tuple(head_sections), head_route_connections, head_closures, "head-neck")
    head_attachment, head_attachment_evidence = _route_attachment(hybrid, "head-neck", head_route, "route:head-neck")
    routes.append(head_route)
    attachments.append(head_attachment)
    make_route_record("head-neck", "head-neck-branch", None, head_route, transformed_head_evidence, head_attachment_evidence, [3])
    binding_evidence.extend(transformed_head_evidence)

    authored_arms = tuple(form.authored_arm_profile.sides)
    projected_arms = tuple(form.variant_arm_profiles[variant_index].sides)
    authored_legs = tuple(form.authored_leg_profile.sides)
    projected_legs = tuple(form.variant_leg_profiles[variant_index].sides)
    authored_feet = tuple(form.authored_foot_profile.sides)
    projected_feet = tuple(form.variant_foot_profiles[variant_index].sides)
    if tuple(item.side for item in authored_arms) != ("left", "right") or tuple(item.side for item in projected_arms) != ("left", "right"):
        _fail("arm profile does not retain bilateral source order")
    if tuple(item.side for item in authored_legs) != ("left", "right") or tuple(item.side for item in projected_legs) != ("left", "right"):
        _fail("leg profile does not retain bilateral source order")
    if tuple(item.side for item in authored_feet) != ("left", "right") or tuple(item.side for item in projected_feet) != ("left", "right"):
        _fail("foot profile does not retain bilateral source order")
    projected_foot_by_side = {item.side: item for item in projected_feet}
    leg_by_side: dict[str, Any] = {}
    for kind, authored_sides, projected_sides, owner_roles, frame_role, names in (
        ("arm", authored_arms, projected_arms, ("upper_arm", "upper_arm", "upper_arm", "forearm", "forearm"), module.ARM_PROFILE_CONTROL_FRAME_ROLE, _LIMB_NAMES["arm"]),
        ("leg", authored_legs, projected_legs, ("thigh", "thigh", "thigh", "shin", "shin"), module.LEG_PROFILE_CONTROL_FRAME_ROLE, _LIMB_NAMES["leg"]),
    ):
        for authored_side, projected_side in zip(authored_sides, projected_sides):
            route_name = f"{authored_side.side}-{kind}"
            authored_sections = tuple(authored_side.sections)
            projected_sections = tuple(projected_side.sections)
            if projected_side.side != authored_side.side or tuple(item.name for item in authored_sections) != names or tuple(item.name for item in projected_sections) != names:
                _fail(f"{route_name} does not retain its exact five-section route")
            route_sections: list[Any] = []
            section_evidence: list[dict[str, Any]] = []
            if kind == "leg":
                next_radii = np.asarray(
                    _projected_profile_radii3(projected_foot_by_side[authored_side.side].sections[0]),
                    dtype=np.float64,
                )
            else:
                next_radii = None
            for section_index, (authored, projected) in enumerate(zip(authored_sections, projected_sections)):
                station, evidence = transform_route_station(
                    authored, projected, route_name,
                    section_index,
                    owner_roles[section_index], frame_role, projected_sections,
                    route_position=section_index + (1 if kind == "leg" else 0),
                    joint_next_radii=next_radii if authored.name == "hock-endpoint" else None,
                )
                route_sections.append(station)
                section_evidence.append(evidence)
            connector_context = None
            pelvis_leg_context = None
            if kind == "arm":
                parent_station = chain.stations[-1]
                child_station = route_sections[0]
                torso_source = tuple(form.authored_torso_profile.sections)[-1]
                terminal_region = chain.regions[-1]
                connector_station, connector_evidence, connector_context = _derive_torso_arm_connector(
                    hybrid,
                    chain,
                    parent_station,
                    terminal_region,
                    terminal_region.last_basis,
                    child_station,
                    torso_source.owner,
                    authored_sections[0].owner,
                    route_name,
                )
                route_sections.insert(0, connector_station)
                section_evidence.insert(0, connector_evidence)
            if kind == "leg":
                thigh_key = (namespace, (authored_side.side,), "part", "thigh")
                pelvis_key = (namespace, (), "part", "pelvis")
                thigh = by_key.get(thigh_key)
                pelvis = by_key.get(pelvis_key)
                if thigh is None or pelvis is None:
                    _fail(f"{route_name} is missing source thigh/pelvis descriptors")
                initial_region = chain.regions[0]
                cup_sections, cup_evidence, pelvis_leg_context = _derive_pelvis_hip_cup_chain(
                    hybrid,
                    chain,
                    chain.stations[0],
                    initial_region,
                    initial_region.first_basis,
                    route_sections[0],
                    pelvis_key,
                    thigh_key,
                    route_name,
                )
                route_sections[0:0] = list(cup_sections)
                section_evidence[0:0] = list(cup_evidence)
            connections = tuple(
                hybrid.SectionConnection(
                    f"{route_name}:{route_sections[index].name}-to-{route_sections[index + 1].name}",
                    index,
                    index + 1,
                    "upper-arm-forearm" if kind == "arm" else "thigh-knee-shin-hock",
                )
                for index in range(len(route_sections) - 1)
            )
            if kind == "arm":
                hand_key = (namespace, (authored_side.side,), "part", "hand")
                hand = by_key.get(hand_key)
                if hand is None:
                    _fail(f"{route_name} has no source hand endpoint")
                hand_source = _descriptor_source(module, hand, form.reference_scale)
                closures = (
                    hybrid.EndpointClosure(
                        f"{route_name}:shoulder-closure", route_sections[1].center, route_sections[1].radii,
                        f"closure:{route_name}:shoulder", route_sections[1].source_key,
                    ),
                    hybrid.EndpointClosure(
                        f"{route_name}:wrist-closure", _tuple3(hand_source["center"], f"{route_name}.wrist.center") if hand_source["name"] == "ellipsoid" else _tuple3(hand_source["to"], f"{route_name}.wrist.center"),
                        _source_shape_radii(hand_source, f"{route_name}.wrist"),
                        f"closure:{route_name}:wrist", _source_route_key(hand_key, "wrist"),
                    ),
                )
                shared_station_indices = [3]
            else:
                rim = _route_section_from_sequence(route_sections, "hip-cup-rim", route_name)
                closures = (
                    hybrid.EndpointClosure(
                        f"{route_name}:hip-cup-rim-closure", rim.center, rim.radii,
                        f"closure:{route_name}:hip-cup-rim", rim.source_key,
                    ),
                    hybrid.EndpointClosure(
                        f"{route_name}:hock-closure", route_sections[-1].center, route_sections[-1].radii,
                        f"closure:{route_name}:hock", route_sections[-1].source_key,
                    ),
                )
                shared_station_indices = [5, 7]
            route = hybrid.AnisotropicSectionSweep(tuple(route_sections), connections, closures, route_name)
            if kind == "arm":
                if connector_context is None:
                    _fail(f"{route_name} is missing its connector derivation context")
                _certify_torso_arm_overlap(hybrid, chain, route, connector_context)
            else:
                if pelvis_leg_context is None:
                    _fail(f"{route_name} is missing its pelvis-leg connector derivation context")
                _certify_pelvis_leg_overlap(hybrid, chain, route, pelvis_leg_context)
            attachment, attachment_evidence = _route_attachment(hybrid, route_name, route, f"route:{route_name}")
            routes.append(route)
            attachments.append(attachment)
            make_route_record(
                route_name,
                f"{kind}-route",
                authored_side.side,
                route,
                section_evidence,
                attachment_evidence,
                shared_station_indices,
                authored_section_count=5,
            )
            binding_evidence.extend(section_evidence)
            if kind == "leg":
                leg_by_side[authored_side.side] = route

    for authored_side, projected_side in zip(authored_feet, projected_feet):
        route_name = f"{authored_side.side}-foot"
        if projected_side.hock_binding != ("authored_leg_profile", authored_side.leg_profile_side_index, authored_side.leg_profile_section_index):
            _fail(f"{route_name} lost its authored hock binding")
        leg_route = leg_by_side.get(authored_side.side)
        if leg_route is None:
            _fail(f"{route_name} has no matching leg route")
        hock = _route_section(leg_route, "hock-endpoint", route_name)
        authored_sections = tuple(authored_side.sections)
        projected_sections = tuple(projected_side.sections)
        if tuple(item.name for item in authored_sections) != ("pad", "toe") or tuple(item.name for item in projected_sections) != ("pad", "toe"):
            _fail(f"{route_name} does not retain its exact two authored sections")
        foot_sections: list[Any] = [hock]
        section_evidence = [{
            "index": 0,
            "route_index": 0,
            "name": hock.name,
            "binding_kind": "borrowed-shared-leg-station",
            "authored_in_foot_route": False,
            "shared_with": f"{authored_side.side}-leg",
            "source_route": f"{authored_side.side}-leg",
            "owner": _key_json((namespace, (authored_side.side,), "part", "shin")),
            "source_index": hock.source_index,
            "source_key": hock.source_key,
            "semantic_key": hock.semantic_key,
            "center": list(hock.center),
            "radii": list(hock.radii),
            "derived": False,
            "leg_authored_identity": {
                "route": f"{authored_side.side}-leg",
                "name": hock.name,
                "source_index": hock.source_index,
                "owner": _key_json((namespace, (authored_side.side,), "part", "shin")),
                "source_key": hock.source_key,
                "semantic_key": hock.semantic_key,
            },
        }]
        for source_section_index, (authored, projected) in enumerate(zip(authored_sections, projected_sections)):
            route_index = source_section_index + 1
            station, evidence = _section_station(
                form, by_key, frame_by_key, authored, projected, route_name, source_section_index,
                "foot", module.FOOT_PROFILE_CONTROL_FRAME_ROLE, module, hybrid,
                route_position=source_section_index + 6,
            )
            foot_sections.append(station)
            evidence["route_index"] = route_index
            section_evidence.append(evidence)
        foot_owner = by_key[(namespace, (authored_side.side,), "part", "foot")]
        if not np.array_equal(np.asarray(foot_sections[0].center), np.asarray(_vec3(foot_owner.point, f"{route_name}.hock_owner_point"))):
            _fail(f"{route_name} hock is not the exact shared shin-owned foot interface")
        connections = (
            hybrid.SectionConnection(f"{route_name}:hock-to-pad", 0, 1, "hock-pad-toe"),
            hybrid.SectionConnection(f"{route_name}:pad-to-toe", 1, 2, "hock-pad-to-toe"),
        )
        closures = (
            hybrid.EndpointClosure(f"{route_name}:hock-closure", hock.center, hock.radii, f"closure:{route_name}:hock", hock.source_key),
            hybrid.EndpointClosure(f"{route_name}:toe-closure", foot_sections[2].center, foot_sections[2].radii, f"closure:{route_name}:toe", foot_sections[2].source_key),
        )
        route = hybrid.AnisotropicSectionSweep(tuple(foot_sections), connections, closures, route_name)
        attachment, attachment_evidence = _route_attachment(hybrid, route_name, route, f"route:{route_name}")
        routes.append(route)
        attachments.append(attachment)
        make_route_record(route_name, "foot-route", authored_side.side, route, section_evidence, attachment_evidence, [0], authored_section_count=2)
        binding_evidence.extend(section_evidence[1:])

    expected_order = ("head-neck", "left-arm", "right-arm", "left-leg", "right-leg", "left-foot", "right-foot")
    if tuple(item.route_name for item in routes) != expected_order:
        _fail("full regional route order is not deterministic")
    if tuple(len(route.sections) for route in routes) != (8, 6, 6, 8, 8, 3, 3):
        _fail("full regional route station inventory is not exact")
    if tuple(len(route.connections) for route in routes) != (7, 5, 5, 7, 7, 2, 2):
        _fail("full regional route connection inventory is not exact")
    if len(binding_evidence) != 40:
        _fail("full regional route binding evidence cardinality is not exact")
    return tuple(routes), tuple(attachments), tuple(binding_evidence), {"routes": route_records}, tuple(route_records)


def _make_shoulder_controls(
    form: Any,
    descriptors: tuple[Any, ...],
    variant_index: int,
    module: Any,
    hybrid: Any,
 ) -> tuple[tuple[Any, ...], tuple[dict[str, Any], ...]]:
    namespace = form.source["namespace"]
    authored_arms = tuple(form.authored_arm_profile.sides)
    if tuple(side.side for side in authored_arms) != ("left", "right"):
        _fail("shoulder controls require the exact bilateral authored arm profile")
    controls: list[Any] = []
    evidence: list[dict[str, Any]] = []
    for authored_side in authored_arms:
        side = authored_side.side
        binding_for_side = {
            role: _shoulder_control_binding(form, descriptors, side, role)
            for role in _SHOULDER_CONTROL_ROLES
        }
        upper = binding_for_side["form_shoulder_peak"]["owner_descriptor"]
        projected = form.variant_arm_profiles[variant_index].sides[0 if authored_side.side == "left" else 1].sections[0]
        radii = _projected_profile_radii3(projected)
        for role in _SHOULDER_CONTROL_ROLES:
            binding = binding_for_side[role]
            landmark = binding["landmark"]
            center = _owner_point(upper, form.reference_scale, landmark.position, f"{authored_side.side}.{role}")
            control_name = f"{authored_side.side}-{'shoulder-peak' if role.endswith('peak') else 'axilla'}"
            source_key = binding["source_key"]
            semantic_key = binding["semantic_key"]
            control = hybrid.SectionControl(control_name, _tuple3(center, f"{control_name}.center"), radii, semantic_key, source_key)
            _validate_shoulder_control_identity(control, namespace=namespace, side=side, role=role)
            controls.append(control)
            evidence.append({
                "name": control_name,
                "namespace": binding["namespace"],
                "side": binding["side"],
                "owner": _key_json(binding["owner"]),
                "role": role,
                "frame": {"owner": _key_json(binding["frame"][0]), "role": binding["frame"][1]},
                "frame_role": binding["frame_role"],
                "authority_only": True,
                "skin_consumer": False,
                "counterfactual_authority_bound_influence": "proven",
                "control_local_final_skin_influence": False,
                "control_local_final_skin_influence_status": "unverified",
                "visual_floor_satisfaction": "unverified",
                "interface_id": f"interface:torso->{authored_side.side}-arm",
                "source_key": source_key,
                "canonical_source_key": source_key,
                "center": list(control.center),
                "radii": list(control.radii),
                "semantic_key": semantic_key,
            })
    return tuple(controls), tuple(evidence)


def _side_matched_shoulder_controls(
    controls: tuple[Any, ...],
    side: str,
    namespace: str | None = None,
) -> tuple[Any, Any]:
    """Return the exact peak/axilla pair, rejecting cross-side identity clones."""

    if side not in {"left", "right"} or type(controls) is not tuple or len(controls) != 4:
        _fail("shoulder authority requires the exact bilateral control inventory")
    expected_names = (
        "left-shoulder-peak", "left-axilla", "right-shoulder-peak", "right-axilla",
    )
    if tuple(getattr(control, "name", None) for control in controls) != expected_names:
        _fail("shoulder authority control order or identity is invalid")
    if len({id(control) for control in controls}) != 4 or len({control.source_key for control in controls}) != 4:
        _fail("shoulder authority controls contain cloned bindings")
    expected_namespace = _DEFAULT_SOURCE_NAMESPACE if namespace is None else namespace
    for control, expected_side, expected_role in zip(
        controls,
        ("left", "left", "right", "right"),
        ("form_shoulder_peak", "form_axilla", "form_shoulder_peak", "form_axilla"),
    ):
        _validate_shoulder_control_identity(
            control,
            namespace=expected_namespace,
            side=expected_side,
            role=expected_role,
        )
    selected = controls[:2] if side == "left" else controls[2:]
    return selected[0], selected[1]


def _remaining_shoulder_controls_for_counterfactual(
    controls: tuple[Any, ...],
    side: str,
    omitted: Any,
    namespace: str,
) -> tuple[Any, ...]:
    """Return a validated one-control omission subset for authority replay."""

    matched = _side_matched_shoulder_controls(controls, side, namespace)
    if omitted not in matched or sum(item is omitted for item in matched) != 1:
        _fail(f"{getattr(omitted, 'name', '<unknown>')} is not the exact side-matched authority input")
    remaining = tuple(item for item in matched if item is not omitted)
    if len(remaining) != 1:
        _fail("counterfactual shoulder authority omission did not leave exactly one control")
    omitted_role = "form_shoulder_peak" if omitted.name.endswith("shoulder-peak") else "form_axilla"
    remaining_role = "form_axilla" if omitted_role == "form_shoulder_peak" else "form_shoulder_peak"
    _validate_shoulder_control_identity(
        remaining[0], namespace=namespace, side=side, role=remaining_role,
    )
    return remaining


def _torso_arm_interface_samples(hybrid: Any, chain: Any, arm: Any) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Use only the live terminal constituent and exact authored child station.

    The parent sample is the analytic zero boundary of the exact terminal cap
    ellipsoid on the source-derived ray toward upper-arm-start.  Both samples
    use the componentwise minimum of the endpoint radii.  Diagnostic shoulder
    controls are supplied separately as authority-only inputs by the caller.
    """

    parent_station = chain.stations[-1]
    child_station = arm.sections[1]
    if parent_station.name != "upper-ribcage-shoulder" or child_station.name != "upper-arm-start":
        _fail(f"{arm.route_name} interface requires the terminal torso and upper-arm-start stations")
    parent_center = _vec3(parent_station.center, f"{arm.route_name}.parent.center")
    parent_radii = np.asarray(
        tuple(_positive_float(value, f"{arm.route_name}.parent.radius") for value in parent_station.radii),
        dtype=np.float64,
    )
    child_center = _vec3(child_station.center, f"{arm.route_name}.child.center")
    child_radii = np.asarray(
        tuple(_positive_float(value, f"{arm.route_name}.child.radius") for value in child_station.radii),
        dtype=np.float64,
    )
    terminal_region = chain.regions[-1]
    constituent = chain._terminal_constituent(
        parent_station,
        terminal_region,
        terminal_region.last_basis,
    )
    parent_point = constituent.analytic_ray_boundary(child_center)
    _live_endpoint_trace_leaf(
        chain,
        parent_point,
        parent_station,
        terminal_region,
        False,
        f"{arm.route_name} interface parent sample",
    )
    shared_radii = tuple(float(value) for value in np.minimum(parent_radii, child_radii))
    return (parent_point, child_center), (shared_radii, shared_radii)


def _make_interface_patches(
    hybrid: Any,
    chain: Any,
    routes: tuple[Any, ...],
    controls: tuple[Any, ...],
    source_namespace: str | None = None,
) -> tuple[tuple[Any, ...], tuple[dict[str, Any], ...]]:
    """Declare the seven parent/child interfaces and nothing else."""

    route_by_name = {route.route_name: route for route in routes}
    required_routes = set(_ROUTE_NAMES)
    if set(route_by_name) != required_routes:
        _fail("interface construction received an incomplete route inventory")

    head = route_by_name["head-neck"]
    specifications = [
        (
            "torso", "head-neck", chain, head,
            (chain.stations[-1].center, head.sections[0].center),
            (chain.stations[-1].radii, head.sections[0].radii),
            INTERFACE_PAD,
            "interface:torso->head-neck",
        ),
    ]
    for side in ("left", "right"):
        arm = route_by_name[f"{side}-arm"]
        points, radii = _torso_arm_interface_samples(hybrid, chain, arm)
        authority_controls = _side_matched_shoulder_controls(controls, side, source_namespace)
        specifications.append(
            (
                "torso", f"{side}-arm", chain, arm,
                points,
                radii,
                INTERFACE_PAD,
                f"interface:torso->{side}-arm",
                authority_controls,
            )
        )
    for side in ("left", "right"):
        leg = route_by_name[f"{side}-leg"]
        cup_sections = tuple(_route_section(leg, name, f"{side}-leg torso authority") for name in _HIP_CUP_NAMES)
        specifications.append(
            (
                "torso", f"{side}-leg", chain, leg,
                tuple(section.center for section in cup_sections),
                tuple(section.radii for section in cup_sections),
                INTERFACE_PAD,
                f"interface:torso->{side}-leg",
                (),
            )
        )
    for side in ("left", "right"):
        leg = route_by_name[f"{side}-leg"]
        foot = route_by_name[f"{side}-foot"]
        hock = _route_section(leg, "hock-endpoint", f"{side}-leg hock authority")
        if hock is not foot.sections[0]:
            _fail(f"{side} hock interface is not the exact shared station")
        specifications.append(
            (
                f"{side}-leg", f"{side}-foot", leg, foot,
                (hock.center,),
                (hock.radii,),
                HOCK_INTERFACE_PAD,
                f"interface:{side}-leg->{side}-foot",
                (),
            )
        )

    patches: list[Any] = []
    records: list[dict[str, Any]] = []
    # The head record predates authority-only controls and has no such inputs.
    specifications[0] = (*specifications[0], ())
    for parent_name, child_name, parent, child, points, radii, pad, semantic_key, authority_controls in specifications:
        patch, record = _interface_patch(
            hybrid, parent_name, child_name, parent, child, points, radii, pad, semantic_key,
            authority_controls,
            source_namespace=source_namespace,
        )
        patches.append(patch)
        records.append(record)
    if tuple((patch.parent_name, patch.child_name) for patch in patches) != (
        ("torso", "head-neck"),
        ("torso", "left-arm"),
        ("torso", "right-arm"),
        ("torso", "left-leg"),
        ("torso", "right-leg"),
        ("left-leg", "left-foot"),
        ("right-leg", "right-foot"),
    ):
        _fail("interface declarations are not in canonical parent/child order")
    return tuple(patches), tuple(records)


def _reflect_x(value: Any, where: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64).copy()
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} is not numeric: {exc}")
    if result.ndim == 0 or result.shape[-1] != 3 or not np.all(np.isfinite(result)):
        _fail(f"{where} must contain finite three-vectors")
    result[..., 0] *= -1.0
    return result


def _assert_mirrored_centers(left: Any, right: Any, where: str) -> None:
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    reflected = _reflect_x(left_array, f"{where}.left")
    if reflected.shape != right_array.shape or not np.all(np.isfinite(right_array)):
        _fail(f"{where} has a malformed bilateral center/sample shape")
    residual = float(np.max(np.abs(reflected - right_array)))
    if residual > _BILATERAL_CENTER_TOLERANCE:
        _fail(f"{where} has a bilateral center/sample mirror residual {residual:.3e}")


def _assert_mirrored_radii(left: Any, right: Any, where: str) -> None:
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if left_array.shape != right_array.shape or not np.all(np.isfinite(left_array)) or not np.all(np.isfinite(right_array)):
        _fail(f"{where} has malformed bilateral radii")
    residual = float(np.max(np.abs(left_array - right_array)))
    if residual > _BILATERAL_RADIUS_TOLERANCE:
        _fail(f"{where} has a bilateral radius mirror residual {residual:.3e}")


def _validate_exact_bilateral_source_profile(
    form: Any,
    descriptors: tuple[Any, ...],
    variant_index: int,
) -> None:
    """Prove the current source/profile inputs are exactly bilateral before use."""

    source = getattr(form, "source", None)
    namespace = source.get("namespace") if isinstance(source, dict) else None
    if type(namespace) is not str or not namespace:
        _fail("bilateral source proof has no exact source namespace")
    by_key = _descriptor_map(tuple(descriptors), namespace)
    profile_pairs = (
        ("authored arm", form.authored_arm_profile, None),
        ("variant arm", form.variant_arm_profiles[variant_index], form.authored_arm_profile),
        ("authored leg", form.authored_leg_profile, None),
        ("variant leg", form.variant_leg_profiles[variant_index], form.authored_leg_profile),
        ("authored foot", form.authored_foot_profile, None),
        ("variant foot", form.variant_foot_profiles[variant_index], form.authored_foot_profile),
    )
    for profile_name, profile, authored_profile in profile_pairs:
        sides = tuple(profile.sides)
        if tuple(getattr(side, "side", None) for side in sides) != ("left", "right"):
            _fail(f"{profile_name} source profile is not the exact left/right pair required for bilateral proof")
        left_sections = tuple(sides[0].sections)
        right_sections = tuple(sides[1].sections)
        if len(left_sections) != len(right_sections):
            _fail(f"{profile_name} source profile has asymmetric section counts")
        authored_sides = None if authored_profile is None else tuple(authored_profile.sides)
        for index, (left_section, right_section) in enumerate(zip(left_sections, right_sections)):
            authored_left_section = None if authored_sides is None else authored_sides[0].sections[index]
            authored_right_section = None if authored_sides is None else authored_sides[1].sections[index]
            left_owner_key = left_section.owner if authored_left_section is None else authored_left_section.owner
            right_owner_key = right_section.owner if authored_right_section is None else authored_right_section.owner
            left_position = (
                left_section.position
                if hasattr(left_section, "position")
                else left_section.landmark.position
            )
            right_position = (
                right_section.position
                if hasattr(right_section, "position")
                else right_section.landmark.position
            )
            if left_section.name != right_section.name or left_owner_key[0] != namespace or right_owner_key[0] != namespace:
                _fail(f"{profile_name} section {index} has an asymmetric owner/name binding")
            left_owner = by_key.get(left_owner_key)
            right_owner = by_key.get(right_owner_key)
            if left_owner is None or right_owner is None:
                _fail(f"{profile_name} section {index} has an owner outside the exact descriptor source")
            left_center = _owner_point(left_owner, form.reference_scale, left_position, f"{profile_name}.left.{left_section.name}")
            right_center = _owner_point(right_owner, form.reference_scale, right_position, f"{profile_name}.right.{right_section.name}")
            if not np.array_equal(_reflect_x(left_center, f"{profile_name}.left.{left_section.name}"), right_center):
                _fail(f"{profile_name} section {left_section.name} source centers are not exactly mirrored")
            if hasattr(left_section, "lateral_radius_permille"):
                left_radii = np.asarray(_projected_profile_radii3(left_section), dtype=np.float64)
                right_radii = np.asarray(_projected_profile_radii3(right_section), dtype=np.float64)
            else:
                left_radii = np.asarray(
                    (left_section.lateral.value_permille, left_section.up.value_permille, left_section.forward.value_permille),
                    dtype=np.float64,
                ) / 1000.0
                right_radii = np.asarray(
                    (right_section.lateral.value_permille, right_section.up.value_permille, right_section.forward.value_permille),
                    dtype=np.float64,
                ) / 1000.0
            if not np.array_equal(left_radii, right_radii):
                _fail(f"{profile_name} section {left_section.name} source radii are not exactly mirrored")

    for role in _SHOULDER_CONTROL_ROLES:
        left_binding = _shoulder_control_binding(form, descriptors, "left", role)
        right_binding = _shoulder_control_binding(form, descriptors, "right", role)
        if not np.array_equal(
            _reflect_x(left_binding["landmark"].position, f"left {role} source position"),
            np.asarray(right_binding["landmark"].position, dtype=np.float64),
        ):
            _fail(f"shoulder source landmark {role} is not exactly mirrored")
    left_upper = by_key.get((namespace, ("left",), "part", "upper_arm"))
    right_upper = by_key.get((namespace, ("right",), "part", "upper_arm"))
    if left_upper is None or right_upper is None:
        _fail("bilateral source proof has no exact upper-arm descriptor pair")
    if not np.array_equal(
        _reflect_x(left_upper.point, "left upper-arm source point"),
        np.asarray(right_upper.point, dtype=np.float64),
    ):
        _fail("upper-arm source descriptor points are not exactly mirrored")


def _validate_bilateral_candidate_exactness(
    form: Any,
    descriptors: tuple[Any, ...],
    variant_index: int,
    routes: tuple[Any, ...],
    controls: tuple[Any, ...],
    interfaces: tuple[Any, ...],
    interface_evidence: tuple[dict[str, Any], ...],
) -> None:
    """Validate computed bilateral objects without modifying them post-evaluation."""

    _validate_exact_bilateral_source_profile(form, descriptors, variant_index)
    route_by_name = {route.route_name: route for route in routes}
    for left_name, right_name in (
        ("left-arm", "right-arm"),
        ("left-leg", "right-leg"),
        ("left-foot", "right-foot"),
    ):
        left_route = route_by_name[left_name]
        right_route = route_by_name[right_name]
        if tuple(section.name for section in left_route.sections) != tuple(section.name for section in right_route.sections):
            _fail(f"{left_name}/{right_name} connector section names are not bilateral")
        for index, (left_section, right_section) in enumerate(zip(left_route.sections, right_route.sections)):
            _assert_mirrored_centers(left_section.center, right_section.center, f"{left_name}/{right_name} section {index}")
            _assert_mirrored_radii(left_section.radii, right_section.radii, f"{left_name}/{right_name} section {index}")

    control_by_name = {control.name: control for control in controls}
    for suffix, role in (("shoulder-peak", "form_shoulder_peak"), ("axilla", "form_axilla")):
        left_control = control_by_name[f"left-{suffix}"]
        right_control = control_by_name[f"right-{suffix}"]
        _validate_shoulder_control_identity(left_control, namespace=form.source["namespace"], side="left", role=role)
        _validate_shoulder_control_identity(right_control, namespace=form.source["namespace"], side="right", role=role)
        _assert_mirrored_centers(left_control.center, right_control.center, f"{suffix} controls")
        _assert_mirrored_radii(left_control.radii, right_control.radii, f"{suffix} controls")

    interface_by_identifier = {item.identifier: item for item in interfaces}
    evidence_by_identifier = {item["identifier"]: item["authority"] for item in interface_evidence}
    for left_identifier, right_identifier in (
        ("interface:torso->left-arm", "interface:torso->right-arm"),
        ("interface:torso->left-leg", "interface:torso->right-leg"),
        ("interface:left-leg->left-foot", "interface:right-leg->right-foot"),
    ):
        left_patch = interface_by_identifier[left_identifier]
        right_patch = interface_by_identifier[right_identifier]
        left_authority = left_patch.authority
        right_authority = right_patch.authority
        left_record = evidence_by_identifier[left_identifier]
        right_record = evidence_by_identifier[right_identifier]
        _assert_mirrored_centers(left_record["points"], right_record["points"], f"{left_identifier} interface samples")
        _assert_mirrored_radii(left_record["interface_radii"], right_record["interface_radii"], f"{left_identifier} interface radii")
        _assert_mirrored_centers(left_record["center"], right_record["center"], f"{left_identifier} authority center")
        _assert_mirrored_radii(left_record["radii"], right_record["radii"], f"{left_identifier} authority radii")
        left_lower = np.asarray(left_record["lower"], dtype=np.float64)
        left_upper = np.asarray(left_record["upper"], dtype=np.float64)
        right_lower = np.asarray(right_record["lower"], dtype=np.float64)
        right_upper = np.asarray(right_record["upper"], dtype=np.float64)
        expected_lower = np.minimum(_reflect_x(left_lower, f"{left_identifier} authority lower"), _reflect_x(left_upper, f"{left_identifier} authority upper"))
        expected_upper = np.maximum(_reflect_x(left_lower, f"{left_identifier} authority lower"), _reflect_x(left_upper, f"{left_identifier} authority upper"))
        if np.max(np.abs(expected_lower - right_lower)) > _BILATERAL_CENTER_TOLERANCE or np.max(np.abs(expected_upper - right_upper)) > _BILATERAL_CENTER_TOLERANCE:
            _fail(f"{left_identifier}/{right_identifier} authority bounds have a bilateral mirror residual")
        if abs(float(left_record["k"]) - float(right_record["k"])) > _BILATERAL_RADIUS_TOLERANCE:
            _fail(f"{left_identifier}/{right_identifier} interface k values have a bilateral mirror residual")
        left_controls = {item["role"]: item for item in left_record["authority_controls"]}
        right_controls = {item["role"]: item for item in right_record["authority_controls"]}
        if set(left_controls) != set(right_controls):
            _fail(f"{left_identifier}/{right_identifier} authority control roles are not bilateral")
        for role in _SHOULDER_CONTROL_ROLES if left_controls else ():
            _assert_mirrored_centers(left_controls[role]["center"], right_controls[role]["center"], f"{role} authority controls")
            _assert_mirrored_radii(left_controls[role]["radii"], right_controls[role]["radii"], f"{role} authority controls")

        sample_offsets = np.asarray(
            ((0.0, 0.0, 0.0), (0.37, 0.0, 0.0), (-0.37, 0.0, 0.0), (0.0, 0.37, 0.0), (0.0, -0.37, 0.0), (0.0, 0.0, 0.37), (0.0, 0.0, -0.37)),
            dtype=np.float64,
        )
        samples = np.asarray(left_authority.center) + sample_offsets * np.asarray(left_authority.radii)
        reflected_samples = _reflect_x(samples, f"{left_identifier} patch samples")
        gate_residual = float(np.max(np.abs(left_authority.gate(samples) - right_authority.gate(reflected_samples))))
        patch_values_left = np.asarray(left_patch.evaluate(samples), dtype=np.float64)
        patch_values_right = np.asarray(right_patch.evaluate(reflected_samples), dtype=np.float64)
        patch_residual = float(np.max(np.abs(patch_values_left - patch_values_right)))
        if gate_residual > _BILATERAL_RADIUS_TOLERANCE:
            _fail(f"{left_identifier}/{right_identifier} authority gates have a bilateral mirror residual {gate_residual:.3e}")
        if patch_residual > _BILATERAL_RADIUS_TOLERANCE:
            _fail(f"{left_identifier}/{right_identifier} patch values have a bilateral mirror residual {patch_residual:.3e}")


def build_regional_surface_candidate(
    prepared: Any,
    profile_id: str = "neutral-v0",
    *,
    mesh_samples: int | None = _MESH_DEFAULT_SAMPLES,
    mesh_padding: float = _MESH_DEFAULT_PADDING,
) -> RegionalSurfaceCandidate:
    """Build the bounded candidate from a validated current prepared form.

    ``prepared`` may be a validated ``surface_preview.Form`` or the raw v11
    mapping emitted by the current Rust inspection command.  The public default
    builds the 56-sample mesh proof; pass ``mesh_samples=None`` when a caller
    explicitly needs the graph without a mesh.
    """

    form = _as_form(prepared)
    variant_index, descriptors, raw_variant = _variant(form, profile_id)
    module = _load_surface_preview()
    hybrid = _load_hybrid()
    if not isinstance(form.source, dict) or form.source.get("resource_profile_id") != "ck.resource.body.r2":
        _fail("adapter requires the current ck.resource.body.r2 prepared form")
    stations, regions, torso_metadata, station_evidence = _make_torso(form, descriptors, variant_index, module, hybrid)
    # The accepted regional torso remains the base skin field.
    projected_legs = tuple(form.variant_leg_profiles[variant_index].sides)
    if len(projected_legs) != 2:
        _fail("prepared form leg profile must contain left and right sides")
    thigh_start_up = tuple(
        _projected_profile_radii3(side.sections[0])[1]
        for side in projected_legs
    )
    neck_collar_up = _projected_profile_radii3(
        tuple(form.variant_head_neck_profiles[variant_index].sections)[0]
    )[1]
    start_cap_radius = TORSO_LOWER_CAP_FACTOR * float(np.mean(thigh_start_up))
    end_cap_radius = TORSO_UPPER_CAP_FACTOR * neck_collar_up
    chain = hybrid.AxialMassChain(
        stations,
        regions,
        start_cap_radius=start_cap_radius,
        end_cap_radius=end_cap_radius,
    )
    routes, route_attachments, route_binding, route_metadata, route_records = _make_full_routes(
        form, descriptors, variant_index, module, hybrid, chain,
    )
    controls, control_evidence = _make_shoulder_controls(
        form, descriptors, variant_index, module, hybrid,
    )
    interfaces, interface_evidence = _make_interface_patches(
        hybrid, chain, routes, controls, form.source["namespace"],
    )
    _validate_bilateral_candidate_exactness(
        form,
        descriptors,
        variant_index,
        routes,
        controls,
        interfaces,
        interface_evidence,
    )
    field = hybrid.FullSectionComposite(chain, route_attachments, interfaces=interfaces)
    authority_ids = tuple(item.authority.identifier for item in interfaces)
    parent_relations = tuple((item.parent_name, item.child_name) for item in interfaces)
    metadata = {
        "format": _CANDIDATE_FORMAT,
        "source": dict(form.source),
        "profile_id": profile_id,
        "variant_source": {
            "id": profile_id,
            "raw_record_present": raw_variant is not None,
            "descriptor_count": len(descriptors),
            "reference_scale": float(form.reference_scale),
        },
        "torso": {
            **torso_metadata,
            "station_count": len(stations),
            "region_count": len(regions),
            "region_intervals": [list(item) for item in _REGION_INTERVALS],
            "axial_caps": {
                "lower": start_cap_radius,
                "upper": end_cap_radius,
                "lower_formula": "1.10*mean(bilateral thigh-start up radius)",
                "upper_formula": "0.50*neck-collar up radius",
            },
        },
        "routes": {
            **route_metadata,
            "count": len(routes),
            "names": [route.route_name for route in routes],
            "binding_evidence_count": len(route_binding),
            "required_head_neck_sections": len(routes[0].sections) == 8,
            "required_head_neck_connections": len(routes[0].connections) == 7,
            "bilateral_arm_authored_sections": [record["authored_section_count"] for record in route_records if record["kind"] == "arm-route"],
            "bilateral_arm_total_sections": [len(route.sections) for route in routes[1:3]],
            "arm_connector_method": "analytic live terminal-constituent ellipsoid ray level",
            "bilateral_leg_sections": [len(route.sections) for route in routes[3:5]],
            "bilateral_leg_authored_sections": [record["authored_section_count"] for record in route_records if record["kind"] == "leg-route"],
            "bilateral_leg_derived_sections": [list(_HIP_CUP_NAMES), list(_HIP_CUP_NAMES)],
            "hip_cup_chain_method": "shared analytic live initial-constituent ray boundary/interior with profile-independent factors",
            "hip_cup_factors": {
                "seat_depth_fraction": HIP_CUP_SEAT_DEPTH_FRACTION,
                "rim_radius_factor": HIP_CUP_RIM_RADIUS_FACTOR,
                "neck_center_factor": FEMORAL_NECK_CENTER_FACTOR,
                "neck_radius_factor": FEMORAL_NECK_RADIUS_FACTOR,
            },
            "bilateral_foot_authored_sections": [record["authored_section_count"] for record in route_records if record["kind"] == "foot-route"],
            "endpoint_closures_explicit": all(record["endpoint_closures"] for record in route_records),
            "shared_interfaces": {
                "cranium_mid": {"head_section_index": 3, "connection_indices": [2, 3, 4]},
                "elbows": [3, 3],
                "knees": [5, 5],
                "hocks": [7, 7],
                "hip_cup_sections": list(_HIP_CUP_NAMES),
                "feet_use_leg_hock_identity": all(
                    _route_section(routes[3 + side_index], "hock-endpoint", "metadata") is routes[5 + side_index].sections[0]
                    for side_index in (0, 1)
                ),
            },
        },
        "interfaces": {
            "count": len(interfaces),
            "parent_relations": [list(item) for item in parent_relations],
            "patches": list(interface_evidence),
            "registration_order_independent": True,
            "authority_source": "interface samples plus side-matched authority-only shoulder controls",
        },
        "shoulder_controls": {
            "count": len(controls),
            "names": [item.name for item in controls],
            "semantic_binding_complete": len(control_evidence) == 4,
            "authority_only": True,
            "skin_consumer": False,
            "counterfactual_authority_bound_influence": "proven",
            "control_local_final_skin_influence": False,
            "control_local_final_skin_influence_status": "unverified",
            "shoulder_visual_floor_satisfaction": "unverified",
            "axilla_visual_floor_satisfaction": "unverified",
            "controls": list(control_evidence),
        },
        "proof": {
            "seven_ordered_torso_stations": len(stations) == 7,
            "three_explicit_regions": len(regions) == 3,
            "complete_head_neck_route": len(routes[0].sections) == 8 and len(routes[0].connections) == 7,
            "complete_bilateral_arm_routes": all(len(route.sections) == 6 for route in routes[1:3]),
            "complete_bilateral_leg_routes": all(len(route.sections) == 8 and len(route.connections) == 7 for route in routes[3:5]),
            "complete_bilateral_foot_routes": all(len(route.sections) == 3 for route in routes[5:]),
            "semantic_binding_complete": len(station_evidence) == 7 and len(route_binding) == 40 and len(control_evidence) == 4,
            "finite_interface_authorities": len(authority_ids) == len(set(authority_ids)) and all(np.all(np.isfinite(item.authority.bounds[0])) and np.all(np.isfinite(item.authority.bounds[1])) for item in interfaces),
            "route_authorities_absent": all(item.authority is None and item.blend_radius is None for item in route_attachments),
            "explicit_source_derived_endpoint_closures": all(record["endpoint_closures"] and all(item["source_key"] for item in record["endpoint_closures"]) for record in route_records),
            "shared_hock_interfaces": all(_route_section(routes[3 + side_index], "hock-endpoint", "metadata") is routes[5 + side_index].sections[0] for side_index in (0, 1)),
            "exact_parent_relations": parent_relations == (
                ("torso", "head-neck"),
                ("torso", "left-arm"),
                ("torso", "right-arm"),
                ("torso", "left-leg"),
                ("torso", "right-leg"),
                ("left-leg", "left-foot"),
                ("right-leg", "right-foot"),
            ),
        },
    }
    candidate = RegionalSurfaceCandidate(
        profile_id,
        dict(form.source),
        chain,
        tuple(regions),
        tuple(stations),
        tuple(routes),
        tuple(controls),
        field,
        metadata,
        tuple(station_evidence) + tuple(route_binding) + tuple(control_evidence),
    )
    if mesh_samples is not None:
        mesh = candidate.mesh_candidate(mesh_samples, mesh_padding)
        object.__setattr__(candidate, "mesh", mesh)
    return candidate


def _face_component_count(faces: np.ndarray) -> int:
    """Count face components using adjacency across shared undirected edges."""

    if len(faces) == 0:
        return 0
    edge_to_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(faces):
        for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = tuple(sorted((int(first), int(second))))
            edge_to_faces.setdefault(edge, []).append(face_index)

    adjacency = [set() for _ in range(len(faces))]
    for incident_faces in edge_to_faces.values():
        for first, second in zip(incident_faces, incident_faces[1:]):
            adjacency[first].add(second)
            adjacency[second].add(first)

    remaining = set(range(len(faces)))
    components = 0
    while remaining:
        components += 1
        pending = [remaining.pop()]
        while pending:
            face_index = pending.pop()
            for neighbor in adjacency[face_index]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
    return components


def _nonmanifold_vertex_count(faces: np.ndarray) -> int:
    """Count used vertices whose triangle link is not one connected cycle."""

    links: dict[int, list[tuple[int, int]]] = {}
    for face in faces:
        first, second, third = (int(item) for item in face)
        for vertex, left, right in (
            (first, second, third),
            (second, third, first),
            (third, first, second),
        ):
            links.setdefault(vertex, []).append((left, right))

    nonmanifold = 0
    for link_edges in links.values():
        adjacency: dict[int, set[int]] = {}
        degrees: dict[int, int] = {}
        for left, right in link_edges:
            adjacency.setdefault(left, set()).add(right)
            adjacency.setdefault(right, set()).add(left)
            degrees[left] = degrees.get(left, 0) + 1
            degrees[right] = degrees.get(right, 0) + 1
        if not degrees or any(degree != 2 for degree in degrees.values()):
            nonmanifold += 1
            continue
        pending = [next(iter(degrees))]
        visited = set(pending)
        while pending:
            node = pending.pop()
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        if len(visited) != len(degrees):
            nonmanifold += 1
    return nonmanifold


def _mesh_candidate(candidate: RegionalSurfaceCandidate, samples: int, padding: float) -> SurfaceMeshProof:
    if type(samples) is not int or samples < _MESH_MIN_SAMPLES or samples > _MESH_MAX_SAMPLES or samples**3 > _MESH_MAX_VOXELS:
        _fail(f"mesh samples must be an integer in {_MESH_MIN_SAMPLES}..{_MESH_MAX_SAMPLES}")
    padding = _finite_float(padding, "mesh padding")
    if padding < 0.0:
        _fail("mesh padding must be non-negative")
    lower, upper = candidate.bounds
    lower = lower - padding
    upper = upper + padding
    # A symmetric coarse lattice can place a narrow, valid shared-interface
    # bridge between two axial slices.  Shift the whole sampling domain by a
    # bounded fraction of the caller's guard padding; this changes neither
    # the field nor its bounds coverage, but makes the finite topology proof
    # deterministic against that lattice phase alias.
    axial_phase = min(_MESH_AXIAL_PHASE_FRACTION * padding, 0.25 * float(upper[1] - lower[1]))
    lower[1] += axial_phase
    upper[1] += axial_phase
    axes = tuple(np.linspace(lower[index], upper[index], samples, dtype=np.float64) for index in range(3))
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    values = np.asarray(candidate.evaluate(points), dtype=np.float64).reshape((samples, samples, samples))
    if not np.all(np.isfinite(values)) or float(np.min(values)) >= 0.0 or float(np.max(values)) <= 0.0:
        _fail("candidate mesh field has no finite zero crossing")
    if np.any(values[(0, -1), :, :] <= 0.0) or np.any(values[:, (0, -1), :] <= 0.0) or np.any(values[:, :, (0, -1)] <= 0.0):
        _fail("candidate mesh field reaches the sampling domain boundary")
    try:
        raw_vertices, raw_faces, raw_normals, _ = marching_cubes(
            values,
            level=0.0,
            spacing=tuple(float(axis[1] - axis[0]) for axis in axes),
            method="lewiner",
            allow_degenerate=False,
        )
    except Exception as exc:
        raise RegionalSurfaceCandidateError(f"candidate surface extraction failed: {exc}") from exc
    vertices = np.asarray(raw_vertices, dtype=np.float64) + lower
    faces = np.asarray(raw_faces, dtype=np.int64)
    normals = np.asarray(raw_normals, dtype=np.float64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3 or normals.shape != vertices.shape:
        _fail("candidate mesh extraction returned malformed arrays")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(normals)) or np.any(faces < 0) or np.any(faces >= len(vertices)):
        _fail("candidate mesh contains non-finite vertices, normals, or indices")
    if len(faces) == 0:
        _fail("candidate mesh contains no faces")
    degenerate_face_count = int(
        np.count_nonzero(
            (faces[:, 0] == faces[:, 1])
            | (faces[:, 1] == faces[:, 2])
            | (faces[:, 2] == faces[:, 0])
        )
    )
    if degenerate_face_count:
        _fail(f"candidate mesh contains {degenerate_face_count} degenerate faces")
    canonical_faces = np.sort(faces, axis=1)
    _, face_counts = np.unique(canonical_faces, axis=0, return_counts=True)
    duplicate_face_count = int(sum(int(count) - 1 for count in face_counts if count > 1))
    if duplicate_face_count:
        _fail(f"candidate mesh contains {duplicate_face_count} duplicate faces")

    face_edges = np.stack((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)]), axis=1)
    edges = np.sort(face_edges.reshape(-1, 2), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    boundary_edge_count = int(np.count_nonzero(counts == 1))
    nonmanifold_edge_count = int(np.count_nonzero(counts > 2))
    connected_components = _face_component_count(faces)
    nonmanifold_vertex_count = _nonmanifold_vertex_count(faces)
    watertight = boundary_edge_count == 0 and nonmanifold_edge_count == 0 and bool(np.all(counts == 2))
    if connected_components != 1 or not watertight or nonmanifold_vertex_count != 0:
        _fail(
            "candidate mesh topology is not proven: "
            f"face_components={connected_components}, boundary_edges={boundary_edge_count}, "
            f"nonmanifold_edges={nonmanifold_edge_count}, nonmanifold_vertices={nonmanifold_vertex_count}"
        )
    return SurfaceMeshProof(
        vertices,
        faces,
        normals,
        _tuple3(lower, "mesh lower"),
        _tuple3(upper, "mesh upper"),
        samples,
        connected_components,
        boundary_edge_count,
        nonmanifold_edge_count,
        nonmanifold_vertex_count,
        watertight,
    )


def adapt_prepared_form(prepared: Any, profile_id: str = "neutral-v0", **kwargs: Any) -> RegionalSurfaceCandidate:
    """Alias used by callers that name the input as a prepared form."""

    return build_regional_surface_candidate(prepared, profile_id, **kwargs)


def build_candidate(prepared: Any, profile_id: str = "neutral-v0", **kwargs: Any) -> RegionalSurfaceCandidate:
    """Short compatibility alias for the experiment workbench."""

    return build_regional_surface_candidate(prepared, profile_id, **kwargs)


__all__ = [
    "CandidateError",
    "RegionalSurfaceCandidate",
    "RegionalSurfaceCandidateError",
    "SurfaceMeshProof",
    "adapt_prepared_form",
    "build_candidate",
    "build_regional_surface_candidate",
]

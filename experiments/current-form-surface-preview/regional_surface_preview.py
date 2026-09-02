"""Disposable exact-five renderer for the regional surface candidate.

The renderer is deliberately a consumer of the candidate adapter.  It does
not derive a second guide, field, or mesh for the skin panels: the skin
consumer receives the exact arrays in :class:`SurfaceMeshProof`.  The lower
diagnostic row is a separate, bounded visualization of the candidate's
authority-only controls and trace/report witnesses.  The middle row consumes the
actual base, route, and derived interface operands from the final graph.

This is an experiment-local visual slice.  It is not a publication format,
topology contract, or production renderer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from io import BytesIO
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.measure import marching_cubes


_ROOT = Path(__file__).resolve().parent
_SURFACE_MODULE_NAME = "regional_surface_preview_surface_preview"
_CANDIDATE_MODULE_NAME = "regional_surface_preview_candidate"

FORMAT = "creature-kernel.disposable-regional-surface-preview.v2"
EXTERNAL_PROFILE_ID = "standard_neutral_reference"
EXTERNAL_PROFILE_IDS = (
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
SOURCE_VARIANT_ID = "neutral-v0"
SOURCE_DOCUMENT_PREFIX = "stylized_digitigrade_biped_authored_form__structural_profile__"
SOURCE_NAMESPACE = "main"
SOURCE_RESOURCE_PROFILE_ID = "ck.resource.body.r2"
_SAFE_EXTERNAL_PROFILE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
CANDIDATE_FORMAT = "creature-kernel.disposable-regional-surface-candidate.v3"
FORM_REDUCED_INVENTORY_HASH_KIND = "validated-form-reduced-inventory"
DEFAULT_MESH_SAMPLES = 56
DEFAULT_MESH_PADDING = 0.20
DIAGNOSTIC_SAMPLES = 16
DIAGNOSTIC_PADDING_FRACTION = 0.12
TRACE_TOLERANCE = 2.0e-9
INFLUENCE_TOLERANCE = 1.0e-12
MESH_DEGENERACY_TOLERANCE = 1.0e-15
CANVAS = (1800, 1500)
PANEL_CONTENTS = ("skin", "field-contributors", "source-diagnostics")
VIEW_NAMES = ("front", "side", "three-quarter")
EXPECTED_ROUTE_NAMES = (
    "head-neck",
    "left-arm",
    "right-arm",
    "left-leg",
    "right-leg",
    "left-foot",
    "right-foot",
)
EXPECTED_CONTROL_NAMES = (
    "left-shoulder-peak",
    "left-axilla",
    "right-shoulder-peak",
    "right-axilla",
)
EXPECTED_ARM_AUTHORED_SECTIONS = (
    "upper-arm-start",
    "upper-arm-midpoint",
    "elbow",
    "forearm-midpoint",
    "forearm-distal",
)
EXPECTED_ARM_SOURCE_INDICES = tuple(range(len(EXPECTED_ARM_AUTHORED_SECTIONS)))
EXPECTED_LEG_AUTHORED_SECTIONS = (
    "thigh-start",
    "thigh-midpoint",
    "knee",
    "shin-midpoint",
    "hock-endpoint",
)
EXPECTED_LEG_SOURCE_INDICES = tuple(range(len(EXPECTED_LEG_AUTHORED_SECTIONS)))
EXPECTED_ROUTE_SECTIONS = {
    "head-neck": (
        "neck-collar",
        "neck-upper",
        "head-base",
        "cranium-mid",
        "cranium-crown",
        "muzzle-root",
        "muzzle-mid",
        "muzzle-tip",
    ),
    "left-arm": (
        "torso-arm-interface",
        *EXPECTED_ARM_AUTHORED_SECTIONS[:4],
        "wrist-transition",
        EXPECTED_ARM_AUTHORED_SECTIONS[4],
    ),
    "right-arm": (
        "torso-arm-interface",
        *EXPECTED_ARM_AUTHORED_SECTIONS[:4],
        "wrist-transition",
        EXPECTED_ARM_AUTHORED_SECTIONS[4],
    ),
    "left-leg": ("pelvis-seat", "hip-cup-rim", "femoral-neck", *EXPECTED_LEG_AUTHORED_SECTIONS),
    "right-leg": ("pelvis-seat", "hip-cup-rim", "femoral-neck", *EXPECTED_LEG_AUTHORED_SECTIONS),
    "left-foot": ("hock-endpoint", "pad", "toe"),
    "right-foot": ("hock-endpoint", "pad", "toe"),
}
EXPECTED_INTERFACE_RELATIONS = (
    ("torso", "head-neck"),
    ("torso", "left-arm"),
    ("torso", "right-arm"),
    ("torso", "left-leg"),
    ("torso", "right-leg"),
    ("left-leg", "left-foot"),
    ("right-leg", "right-foot"),
)
EXPECTED_HEAD_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (3, 5),
    (5, 6),
    (6, 7),
)


class RegionalSurfacePreviewError(ValueError):
    """Raised when the bounded render cannot prove its input or output."""


PreviewError = RegionalSurfacePreviewError


def _fail(message: str) -> None:
    raise RegionalSurfacePreviewError(message)


def _load_module(name: str, path: Path) -> Any:
    loaded = sys.modules.get(name)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        _fail(f"could not load {path}: {exc}")
    return module


surface_preview = _load_module(_SURFACE_MODULE_NAME, _ROOT / "surface_preview.py")
regional_surface_candidate = _load_module(
    _CANDIDATE_MODULE_NAME,
    _ROOT / "regional_surface_candidate.py",
)

PROJECTIONS = tuple(surface_preview.PROJECTIONS)


def _source_document(external_profile_id: str) -> str:
    return f"{SOURCE_DOCUMENT_PREFIX}{external_profile_id}"


EXPECTED_SOURCE_DOCUMENT = _source_document(EXTERNAL_PROFILE_ID)


def _panel_box(column: int, row: int) -> tuple[int, int, int, int]:
    return tuple(surface_preview._panel_box(column, row))


PANEL_LAYOUT = tuple(
    {
        "id": f"{name}-{content}",
        "projection": name,
        "content": content,
        "box": _panel_box(index, row),
    }
    for row, content in enumerate(PANEL_CONTENTS)
    for index, (name, _, _) in enumerate(PROJECTIONS)
)


@dataclass(frozen=True, slots=True)
class RegionalSurfacePreviewResult:
    """Immutable result envelope returned by the stable renderer callable."""

    png_bytes: bytes
    metadata: dict[str, Any]

    @property
    def image_bytes(self) -> bytes:
        """Compatibility spelling for consumers that call the image payload."""

        return self.png_bytes


RegionalSurfacePreview = RegionalSurfacePreviewResult


@dataclass(frozen=True, slots=True)
class _DiagnosticOperand:
    identifier: str
    kind: str
    semantic_identity: str
    evaluator: Any
    lower: np.ndarray
    upper: np.ndarray


@dataclass(frozen=True, slots=True)
class _DiagnosticMesh:
    operand: _DiagnosticOperand
    vertices: np.ndarray
    faces: np.ndarray
    samples: int
    padding: float
    value_minimum: float
    value_maximum: float


def _jsonable(value: Any) -> Any:
    """Convert candidate records into ordinary JSON-compatible values."""

    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            _fail("metadata contains a non-finite number")
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if is_dataclass(value):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Path):
        return value.as_posix()
    _fail(f"metadata contains an unsupported value of type {type(value).__name__}")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise RegionalSurfacePreviewError(f"metadata is not JSON-ready: {exc}") from exc


def _validate_external_profile_id(external_profile_id: Any) -> str:
    if type(external_profile_id) is not str or not _SAFE_EXTERNAL_PROFILE_ID.fullmatch(external_profile_id):
        _fail("external_profile_id must be a safe lowercase identifier")
    if external_profile_id not in EXTERNAL_PROFILE_IDS:
        _fail(f"unsupported external_profile_id: {external_profile_id!r}")
    return external_profile_id


def _prepared_form(prepared: Any, external_profile_id: str = EXTERNAL_PROFILE_ID) -> Any:
    external_profile_id = _validate_external_profile_id(external_profile_id)
    expected_source_document = _source_document(external_profile_id)
    if isinstance(prepared, Mapping):
        try:
            form = surface_preview.validate_envelope(prepared)
        except Exception as exc:
            raise RegionalSurfacePreviewError(f"prepared form validation failed: {exc}") from exc
    elif isinstance(prepared, surface_preview.Form):
        form = prepared
    else:
        _fail("prepared must be a validated current prepared form or its mapping")
    source = getattr(form, "source", None)
    if not isinstance(source, Mapping) or source.get("document") != expected_source_document:
        _fail(
            "prepared source document does not match external_profile_id: "
            f"expected {expected_source_document!r}"
        )
    if source.get("namespace") != SOURCE_NAMESPACE:
        _fail("structural-profile source must use the main namespace")
    if source.get("resource_profile_id") != SOURCE_RESOURCE_PROFILE_ID:
        _fail("structural-profile source must use the current resource profile")
    return form


def _prepared_identity(prepared: Any, form: Any) -> dict[str, Any]:
    if isinstance(prepared, Mapping):
        # ``form.raw`` is the successful envelope after the full validator has
        # accepted it.  Hash that validated envelope, rather than an arbitrary
        # mapping representation supplied by the caller.
        identity_bytes = _canonical(_jsonable(form.raw))
        hash_kind = "canonical-prepared-envelope"
    else:
        # A Form is a validated in-memory object, not the canonical wire
        # envelope.  Keep this fallback useful, but label its smaller identity
        # honestly so it cannot be mistaken for the full envelope hash.
        identity_bytes = _canonical(
            {
                "source": _jsonable(form.source),
                "reference_scale": _jsonable(form.reference_scale),
                "variants": [
                    {
                        "id": variant_id,
                        "descriptor_keys": [_jsonable(descriptor.key) for descriptor in descriptors],
                    }
                    for variant_id, descriptors, _ in form.variants
                ],
            }
        )
        hash_kind = FORM_REDUCED_INVENTORY_HASH_KIND
    source = _jsonable(form.source)
    result = {
        "format": getattr(form, "source_format", None) or surface_preview.SOURCE_FORMAT,
        "sha256": hashlib.sha256(identity_bytes).hexdigest(),
        "hash_kind": hash_kind,
        "document": source.get("document"),
        "namespace": source.get("namespace"),
        "resource_profile_id": source.get("resource_profile_id"),
        "reference_scale": _jsonable(form.reference_scale),
    }
    return result


def _vector(value: Any, where: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} is not a numeric vector: {exc}")
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        _fail(f"{where} must be a finite three-vector")
    return result


def _operand_bounds(operand: Any, where: str) -> tuple[np.ndarray, np.ndarray]:
    bounds = getattr(operand, "bounds", None)
    if bounds is None:
        _fail(f"{where} has no bounds")
    try:
        bounds = bounds() if callable(bounds) else bounds
        if not isinstance(bounds, tuple) or len(bounds) != 2:
            raise ValueError("expected lower/upper tuple")
        lower = _vector(bounds[0], f"{where}.lower")
        upper = _vector(bounds[1], f"{where}.upper")
    except Exception as exc:
        if isinstance(exc, RegionalSurfacePreviewError):
            raise
        raise RegionalSurfacePreviewError(f"{where} bounds are invalid: {exc}") from exc
    if np.any(upper <= lower):
        _fail(f"{where} bounds are not strictly ordered")
    return lower, upper


def _named_route_section(route: Any, name: str, where: str) -> Any:
    matches = tuple(section for section in route.sections if section.name == name)
    if len(matches) != 1:
        _fail(f"{where} requires exactly one {name} section")
    return matches[0]


def _validate_candidate_graph(candidate: Any) -> tuple[Any, Any, tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]:
    expected_candidate_type = getattr(regional_surface_candidate, "RegionalSurfaceCandidate", None)
    if expected_candidate_type is None or type(candidate) is not expected_candidate_type:
        _fail("candidate is not the exact regional surface candidate type")

    candidate_source = getattr(candidate, "source", None)
    if type(candidate_source) is not dict or type(candidate_source.get("namespace")) is not str or not candidate_source.get("namespace"):
        _fail("candidate source namespace is missing or invalid")
    source_namespace = candidate_source["namespace"]

    hybrid_loader = getattr(regional_surface_candidate, "_load_hybrid", None)
    if not callable(hybrid_loader):
        _fail("candidate does not expose its exact hybrid graph loader")
    hybrid = hybrid_loader()
    expected_types = {
        name: getattr(hybrid, name, None)
        for name in (
            "AxialMassChain",
            "AxialRegion",
            "AxialStation",
            "SectionStation",
            "AnisotropicSectionSweep",
            "SectionControl",
            "SectionAttachment",
            "FullSectionComposite",
            "ParentTargetedInterfacePatch",
            "SectionConnection",
            "EndpointClosure",
            "AuthorityVolume",
        )
    }
    if any(value is None for value in expected_types.values()):
        _fail("candidate hybrid graph types are incomplete")

    def require_exact(value: Any, type_name: str, where: str) -> Any:
        expected = expected_types[type_name]
        if type(value) is not expected:
            _fail(f"{where} is not the exact {type_name} graph type")
        return value

    chain = getattr(candidate, "chain", None)
    regions = getattr(candidate, "regions", None)
    stations = getattr(candidate, "stations", None)
    routes = getattr(candidate, "routes", None)
    controls = getattr(candidate, "controls", None)
    field = getattr(candidate, "field", None)
    interfaces = getattr(candidate, "interfaces", None)
    if chain is None or field is None or type(regions) is not tuple or type(stations) is not tuple:
        _fail("candidate final field graph is incomplete")
    require_exact(chain, "AxialMassChain", "candidate.chain")
    require_exact(field, "FullSectionComposite", "candidate.field")
    if type(routes) is not tuple or len(routes) != len(EXPECTED_ROUTE_NAMES):
        _fail("candidate complete route inventory is incomplete")
    if type(controls) is not tuple or len(controls) != len(EXPECTED_CONTROL_NAMES):
        _fail("candidate shoulder-control inventory is incomplete")
    if getattr(chain, "stations", None) is not stations or getattr(chain, "regions", None) is not regions:
        _fail("candidate chain does not retain candidate stations and regions by identity")
    if getattr(field, "base", None) is not chain:
        _fail("candidate final field does not retain candidate.chain as its base")
    if type(interfaces) is not tuple:
        _fail("candidate.interfaces is missing; the parent-targeted interface API is required")
    field_interfaces = getattr(field, "interfaces", None)
    if type(field_interfaces) is not tuple:
        _fail("candidate.field.interfaces is missing; the final graph has no explicit interface inventory")
    if interfaces is not field_interfaces:
        _fail("candidate.interfaces does not retain candidate.field.interfaces by identity")
    if getattr(candidate, "scalar_field", None) is not field:
        _fail("candidate.scalar_field does not retain candidate.field by identity")

    route_names = tuple(getattr(route, "route_name", None) for route in routes)
    if route_names != EXPECTED_ROUTE_NAMES:
        _fail("candidate complete route order is invalid")
    control_names = tuple(getattr(control, "name", None) for control in controls)
    if control_names != EXPECTED_CONTROL_NAMES:
        _fail("candidate complete control order is invalid")
    for index, region in enumerate(regions):
        require_exact(region, "AxialRegion", f"candidate.regions[{index}]")
    for index, station in enumerate(stations):
        require_exact(station, "AxialStation", f"candidate.stations[{index}]")
    for index, control in enumerate(controls):
        require_exact(control, "SectionControl", f"candidate.controls[{index}]")
        expected_side = "left" if index < 2 else "right"
        expected_role = "form_shoulder_peak" if index % 2 == 0 else "form_axilla"
        regional_surface_candidate._validate_shoulder_control_identity(
            control,
            namespace=source_namespace,
            side=expected_side,
            role=expected_role,
        )

    for route in routes:
        route_name = route.route_name
        require_exact(route, "AnisotropicSectionSweep", f"candidate route {route_name}")
        expected_sections = EXPECTED_ROUTE_SECTIONS.get(route_name)
        if expected_sections is None or tuple(section.name for section in route.sections) != expected_sections:
            _fail(f"candidate route {route_name} does not retain its complete section route")
        if any(type(section) is not expected_types["SectionStation"] for section in route.sections):
            _fail(f"candidate route {route_name} has an invalid section station type")
        if any(not section.semantic_key or not section.source_key for section in route.sections):
            _fail(f"candidate route {route_name} has incomplete section source identity")
        expected_edges = EXPECTED_HEAD_CONNECTIONS if route_name == "head-neck" else tuple(
            (index, index + 1) for index in range(len(expected_sections) - 1)
        )
        actual_edges = tuple((item.from_section_index, item.to_section_index) for item in route.connections)
        if actual_edges != expected_edges:
            _fail(f"candidate route {route_name} does not retain its complete connection graph")
        if any(type(item) is not expected_types["SectionConnection"] for item in route.connections):
            _fail(f"candidate route {route_name} has an invalid connection type")
        expected_closure_count = 3 if route_name == "head-neck" else 2
        if len(route.endpoint_closures) != expected_closure_count:
            _fail(f"candidate route {route_name} has an incomplete endpoint closure graph")
        if any(type(item) is not expected_types["EndpointClosure"] for item in route.endpoint_closures):
            _fail(f"candidate route {route_name} has an invalid endpoint closure type")
        if any(not item.semantic_key or not item.source_key for item in route.endpoint_closures):
            _fail(f"candidate route {route_name} has incomplete endpoint source identity")
        if route_name.endswith("-arm"):
            connector = route.sections[0]
            authored_sections = tuple(
                _named_route_section(route, name, f"candidate route {route_name}")
                for name in EXPECTED_ARM_AUTHORED_SECTIONS
            )
            if connector.source_index is not None:
                _fail(f"candidate route {route_name} torso-arm interface is not derived")
            if tuple(section.source_index for section in authored_sections) != EXPECTED_ARM_SOURCE_INDICES:
                _fail(f"candidate route {route_name} does not retain authored source indices 0..4")
            wrist = _named_route_section(route, "wrist-transition", f"candidate route {route_name}")
            if wrist.source_index is not None:
                _fail(f"candidate route {route_name} wrist transition is not derived")
            if route.sections[3].name != "elbow" or route.sections[3].source_index != 2:
                _fail(f"candidate route {route_name} does not retain the authored elbow identity")
            shoulder_closure = route.endpoint_closures[0]
            upper_arm_start = route.sections[1]
            if (
                shoulder_closure.name != f"{route_name}:shoulder-closure"
                or shoulder_closure.center != upper_arm_start.center
                or shoulder_closure.radii != upper_arm_start.radii
                or shoulder_closure.source_key != upper_arm_start.source_key
            ):
                _fail(f"candidate route {route_name} shoulder closure does not retain upper-arm-start")
        elif route_name.endswith("-leg"):
            cup_sections = tuple(
                _named_route_section(route, name, f"candidate route {route_name}")
                for name in ("pelvis-seat", "hip-cup-rim", "femoral-neck")
            )
            authored_sections = tuple(
                _named_route_section(route, name, f"candidate route {route_name}")
                for name in EXPECTED_LEG_AUTHORED_SECTIONS
            )
            if any(section.source_index is not None for section in cup_sections):
                _fail(f"candidate route {route_name} hip-cup sections are not derived")
            if tuple(section.source_index for section in authored_sections) != EXPECTED_LEG_SOURCE_INDICES:
                _fail(f"candidate route {route_name} does not retain authored source indices 0..4")
            if route.sections[3] is not authored_sections[0] or authored_sections[0].name != "thigh-start":
                _fail(f"candidate route {route_name} does not retain the exact authored thigh-start identity")
            if _named_route_section(route, "knee", f"candidate route {route_name}").source_index != 2:
                _fail(f"candidate route {route_name} does not retain the authored knee identity")
            if _named_route_section(route, "hock-endpoint", f"candidate route {route_name}").source_index != 4:
                _fail(f"candidate route {route_name} does not retain the authored hock identity")
            hip_closure = route.endpoint_closures[0]
            if (
                hip_closure.name != f"{route_name}:hip-cup-rim-closure"
                or hip_closure.center != cup_sections[1].center
                or hip_closure.radii != cup_sections[1].radii
                or hip_closure.source_key != cup_sections[1].source_key
            ):
                _fail(f"candidate route {route_name} hip closure does not retain hip-cup-rim")
    for side_index in (0, 1):
        leg = routes[3 + side_index]
        foot = routes[5 + side_index]
        hock = _named_route_section(leg, "hock-endpoint", "candidate foot interface")
        if foot.sections[0] is not hock or hock.source_index != 4:
            _fail("candidate feet do not retain the exact leg-authored hock interfaces")

    attachments = getattr(field, "attachments", None)
    if type(attachments) is not tuple or len(attachments) != len(routes):
        _fail("candidate final field must contain exactly the seven route attachments")
    if any(type(item) is not expected_types["SectionAttachment"] for item in attachments):
        _fail("candidate final field contains an invalid attachment type")
    attachment_by_name: dict[str, Any] = {}
    for attachment in attachments:
        if attachment.name in attachment_by_name:
            _fail(f"candidate final field declares route {attachment.name} more than once")
        if attachment.name not in EXPECTED_ROUTE_NAMES:
            _fail(f"candidate final field contains undeclared skin attachment {attachment.name!r}")
        attachment_by_name[attachment.name] = attachment
        route = next(route for route in routes if route.route_name == attachment.name)
        if attachment.field is not route or attachment.semantic_key != f"route:{route.route_name}":
            _fail(f"candidate final field lost route attachment {route.route_name} by identity")
        if attachment.authority is not None or attachment.blend_radius is not None:
            _fail(f"candidate route attachment {route.route_name} carries interface authority")
    if set(attachment_by_name) != set(EXPECTED_ROUTE_NAMES):
        _fail("candidate final field route attachment names are incomplete")
    if tuple(getattr(field, "components", ())) != tuple(item.field for item in attachments):
        _fail("candidate final field component view does not retain route attachments by identity")
    field_routes = getattr(field, "routes", None)
    if type(field_routes) is not tuple or {id(item) for item in field_routes} != {id(item) for item in routes}:
        _fail("candidate final field route view does not retain complete routes by identity")
    if any(any(item.field is control for item in attachments) for control in controls):
        _fail("candidate shoulder control is incorrectly present as a final skin term")
    if any(any(component is control for component in field.components) for control in controls):
        _fail("candidate shoulder control is incorrectly present in the final component view")

    if len(field_interfaces) != len(EXPECTED_INTERFACE_RELATIONS):
        _fail("candidate final field must contain exactly seven interface patches")
    if getattr(field, "patches", None) is not field_interfaces:
        _fail("candidate final field patches view does not retain interfaces by identity")
    patch_by_relation: dict[tuple[str, str], Any] = {}
    for patch in field_interfaces:
        require_exact(patch, "ParentTargetedInterfacePatch", f"candidate interface {getattr(patch, 'identifier', '<unknown>')}")
        relation = (patch.parent_name, patch.child_name)
        if relation in patch_by_relation:
            _fail(f"candidate final field declares interface {relation!r} more than once")
        if relation not in EXPECTED_INTERFACE_RELATIONS:
            _fail(f"candidate final field contains an undeclared interface {relation!r}")
        patch_by_relation[relation] = patch
        identifier = f"interface:{patch.parent_name}->{patch.child_name}"
        if patch.identifier != identifier or patch.interface_id != identifier or patch.name != identifier:
            _fail(f"candidate interface {relation!r} has an invalid identifier")
        if patch.parent_id != patch.parent_name or patch.child_id != patch.child_name or patch.k != patch.blend_radius:
            _fail(f"candidate interface {identifier} lost its public identity aliases")
        if patch.semantic_key != identifier:
            _fail(f"candidate interface {identifier} lost its semantic identity")
        expected_parent = chain if patch.parent_name == "torso" else next(
            route for route in routes if route.route_name == patch.parent_name
        )
        expected_child = next(route for route in routes if route.route_name == patch.child_name)
        if patch.parent is not expected_parent or patch.child is not expected_child:
            _fail(f"candidate interface {identifier} does not retain exact parent/child object identity")
        if patch.parent is field or patch.child is field or any(patch.parent is control or patch.child is control for control in controls):
            _fail(f"candidate interface {identifier} targets an aggregate or shoulder control")
        if type(patch.authority) is not expected_types["AuthorityVolume"]:
            _fail(f"candidate interface {identifier} has an invalid authority type")
        if patch.authority.identifier != f"authority:{patch.parent_name}->{patch.child_name}":
            _fail(f"candidate interface {identifier} has an invalid authority identity")
        lower, upper = _operand_bounds(patch.authority, f"candidate interface {identifier} authority")
        if not np.all(np.isfinite(np.concatenate((lower, upper)))):
            _fail(f"candidate interface {identifier} authority is non-finite")
    if set(patch_by_relation) != set(EXPECTED_INTERFACE_RELATIONS):
        _fail("candidate final field interface relation inventory is incomplete")
    if tuple(patch.identifier for patch in field_interfaces) != tuple(
        sorted(f"interface:{parent}->{child}" for parent, child in EXPECTED_INTERFACE_RELATIONS)
    ):
        _fail("candidate final field interface order is not deterministic")

    # Reconstruct both torso->arm authorities from live graph objects.  This
    # rejects swapped controls and renamed clones without trusting metadata.
    for side in ("left", "right"):
        relation = ("torso", f"{side}-arm")
        patch = patch_by_relation[relation]
        arm = next(route for route in routes if route.route_name == f"{side}-arm")
        points, radii = regional_surface_candidate._torso_arm_interface_samples(hybrid, chain, arm)
        matched_controls = regional_surface_candidate._side_matched_shoulder_controls(controls, side, source_namespace)
        expected_authority, expected_k, _ = regional_surface_candidate._interface_authority(
            hybrid,
            f"torso->{side}-arm",
            points,
            radii,
            regional_surface_candidate.INTERFACE_PAD,
            matched_controls,
            source_namespace=source_namespace,
        )
        if (
            patch.authority.center != expected_authority.center
            or patch.authority.radii != expected_authority.radii
            or patch.authority.collar_fraction != expected_authority.collar_fraction
            or patch.blend_radius != expected_k
        ):
            _fail(f"candidate {side} torso-arm authority lost exact interface/control geometry or k")
        if not all(patch.authority.contains(point) for point in points):
            _fail(f"candidate {side} torso-arm authority excludes an original interface sample")
        if not all(patch.authority.contains(control.center) for control in matched_controls):
            _fail(f"candidate {side} torso-arm authority excludes a side-matched control center")

    expected_candidate_methods = expected_candidate_type
    expected_field_methods = expected_types["FullSectionComposite"]
    for method_name in ("evaluate", "operation_trace", "contribution_report"):
        candidate_function = getattr(type(candidate), method_name, None)
        if candidate_function is not getattr(expected_candidate_methods, method_name, None):
            _fail(f"candidate.{method_name} is not the expected candidate graph method")
        candidate_method = getattr(candidate, method_name, None)
        if getattr(candidate_method, "__self__", None) is not candidate:
            _fail(f"candidate.{method_name} is not bound to the candidate")
        field_function = getattr(type(field), method_name, None)
        if field_function is not getattr(expected_field_methods, method_name, None):
            _fail(f"candidate.field.{method_name} is not the expected final graph method")
        field_method = getattr(field, method_name, None)
        if getattr(field_method, "__self__", None) is not field:
            _fail(f"candidate.field.{method_name} is not bound to the final field graph")
    return field, chain, routes, field_interfaces, controls


def _validate_candidate_contract(
    candidate: Any,
    form: Any | None = None,
) -> tuple[Any, Any, tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]:
    field, chain, routes, interfaces, controls = _validate_candidate_graph(candidate)
    candidate_source = getattr(candidate, "source", None)
    if getattr(candidate, "profile_id", None) != SOURCE_VARIANT_ID:
        _fail("candidate source variant is not neutral-v0")
    if not isinstance(candidate_source, Mapping):
        _fail("candidate source binding is absent")
    if form is not None and candidate_source != form.source:
        _fail("candidate source is not the validated prepared source")
    return field, chain, routes, interfaces, controls


def _candidate_metadata_summary(
    candidate: Any,
    form: Any,
    field: Any,
    chain: Any,
    routes: tuple[Any, ...],
    interfaces: tuple[Any, ...],
    controls: tuple[Any, ...],
) -> dict[str, Any]:
    """Build the compact renderer-facing candidate summary from live objects.

    The candidate adapter retains a detailed evidence sidecar for its own
    tests, but that sidecar is not a renderer authority.  This summary keeps
    only source/semantic identity, graph structure, counts, and live-derived
    proof booleans.  In particular, it intentionally contains no independent
    centers, radii, interface samples, blend ``k`` values, or saddle record.
    """

    selected = tuple(item for item in form.variants if item[0] == SOURCE_VARIANT_ID)
    if len(selected) != 1:
        _fail("validated prepared form does not contain one neutral-v0 variant")
    variant_id, descriptors, raw_variant = selected[0]
    source = form.source
    source_fields = ("document", "namespace", "resource_profile_id")
    if any(key not in source for key in source_fields):
        _fail("validated prepared source is missing candidate summary identity")
    control_bindings = []
    for index, control in enumerate(controls):
        side = "left" if index < 2 else "right"
        role = "form_shoulder_peak" if index % 2 == 0 else "form_axilla"
        binding = regional_surface_candidate._shoulder_control_binding(
            form, tuple(descriptors), side, role,
        )
        identity = regional_surface_candidate._validate_shoulder_control_identity(
            control,
            namespace=source["namespace"],
            side=side,
            role=role,
        )
        if identity["source_key"] != binding["source_key"] or identity["semantic_key"] != binding["semantic_key"]:
            _fail(f"candidate shoulder control {control.name} is not bound to the exact prepared source")
        control_bindings.append(binding)

    def route_kind(route_name: str) -> str:
        if route_name == "head-neck":
            return "head-neck-branch"
        if route_name.endswith("-arm"):
            return "arm-route"
        if route_name.endswith("-leg"):
            return "leg-route"
        return "foot-route"

    def shared_station_indices(route: Any) -> list[int]:
        route_name = route.route_name
        if route_name == "head-neck":
            return [3]
        if route_name.endswith("-arm"):
            return [3]
        if route_name.endswith("-leg"):
            return [
                next(index for index, section in enumerate(route.sections) if section.name == "knee"),
                next(index for index, section in enumerate(route.sections) if section.name == "hock-endpoint"),
            ]
        return [0]

    def section_record(route: Any, index: int, section: Any) -> dict[str, Any]:
        record = {
            "index": index,
            "name": section.name,
            "source_key": section.source_key,
            "semantic_key": section.semantic_key,
            "source_index": section.source_index,
            "derived": section.source_index is None,
        }
        if route.route_name.endswith("-foot") and index == 0:
            side = route.route_name.split("-", 1)[0]
            source_route = f"{side}-leg"
            owner = {
                "namespace": source["namespace"],
                "anchors": [side],
                "kind": "part",
                "role": "shin",
            }
            leg_authored_identity = {
                "route": source_route,
                "name": section.name,
                "source_index": section.source_index,
                "owner": owner,
                "source_key": section.source_key,
                "semantic_key": section.semantic_key,
            }
            record.update(
                {
                    "route_index": index,
                    "binding_kind": "borrowed-shared-leg-station",
                    "authored_in_foot_route": False,
                    "shared_with": source_route,
                    "source_route": source_route,
                    "owner": owner,
                    "leg_authored_identity": leg_authored_identity,
                }
            )
        return record

    route_records = []
    for route in routes:
        route_records.append(
            {
                "name": route.route_name,
                "kind": route_kind(route.route_name),
                "side": None if route.route_name == "head-neck" else route.route_name.split("-", 1)[0],
                "section_count": len(route.sections),
                "sections": [section_record(route, index, section) for index, section in enumerate(route.sections)],
                "connection_count": len(route.connections),
                "connections": [
                    {
                        "name": connection.name,
                        "from_section_index": connection.from_section_index,
                        "to_section_index": connection.to_section_index,
                        "route": connection.route,
                    }
                    for connection in route.connections
                ],
                "shared_station_indices": shared_station_indices(route),
                "hip_cup_sections": [
                    section.name for section in route.sections if section.name in {"pelvis-seat", "hip-cup-rim", "femoral-neck"}
                ] if route.route_name.endswith("-leg") else [],
                "endpoint_closures": [
                    {"name": closure.name, "source_key": closure.source_key}
                    for closure in route.endpoint_closures
                ],
                "attachment": {
                    "name": route.route_name,
                    "semantic_key": f"route:{route.route_name}",
                    "authority": None,
                    "blend_radius": None,
                    "skin_component": True,
                },
            }
        )

    interface_by_relation = {
        (interface.parent_name, interface.child_name): interface
        for interface in interfaces
    }
    ordered_interfaces = tuple(
        interface_by_relation[relation] for relation in EXPECTED_INTERFACE_RELATIONS
    )
    route_binding_evidence_count = sum(
        len(route.sections) - (1 if route.route_name.endswith("-foot") else 0)
        for route in routes
    )
    total_binding_evidence_count = len(chain.stations) + route_binding_evidence_count + len(control_bindings)

    semantic_binding_complete = all(
        bool(station.semantic_key)
        for station in chain.stations
    ) and all(
        bool(section.semantic_key and section.source_key)
        for route in routes
        for section in route.sections
    ) and len(control_bindings) == len(EXPECTED_CONTROL_NAMES)
    proof = {
        "seven_ordered_torso_stations": len(chain.stations) == 7 and all(
            chain.stations[index].position < chain.stations[index + 1].position
            for index in range(len(chain.stations) - 1)
        ),
        "three_explicit_regions": len(chain.regions) == 3 and all(
            region.start_index < region.end_index for region in chain.regions
        ),
        "complete_head_neck_route": len(routes[0].sections) == 8 and len(routes[0].connections) == 7,
        "complete_bilateral_limb_routes": all(
            len(route.sections) == 7
            and len(route.connections) == 6
            and route.sections[0].source_index is None
            and tuple(
                _named_route_section(route, name, f"{route.route_name} summary").source_index
                for name in EXPECTED_ARM_AUTHORED_SECTIONS
            ) == EXPECTED_ARM_SOURCE_INDICES
            and _named_route_section(route, "wrist-transition", f"{route.route_name} summary").source_index is None
            for route in routes[1:3]
        ) and all(
            len(route.sections) == 8
            and len(route.connections) == 7
            and all(
                _named_route_section(route, name, f"{route.route_name} summary").source_index is None
                for name in ("pelvis-seat", "hip-cup-rim", "femoral-neck")
            )
            and tuple(
                _named_route_section(route, name, f"{route.route_name} summary").source_index
                for name in EXPECTED_LEG_AUTHORED_SECTIONS
            ) == EXPECTED_LEG_SOURCE_INDICES
            for route in routes[3:5]
        ),
        "complete_bilateral_foot_routes": all(
            len(route.sections) == 3 and len(route.connections) == 2 for route in routes[5:]
        ),
        "semantic_binding_complete": semantic_binding_complete,
        "finite_interface_authorities": all(
            np.all(np.isfinite(interface.authority.bounds[0]))
            and np.all(np.isfinite(interface.authority.bounds[1]))
            for interface in interfaces
        ),
        "route_authorities_absent": all(
            attachment.authority is None and attachment.blend_radius is None
            for attachment in field.attachments
        ),
        "explicit_source_derived_endpoint_closures": all(
            route.endpoint_closures and all(closure.source_key for closure in route.endpoint_closures)
            for route in routes
        ),
        "shared_hock_interfaces": _named_route_section(routes[3], "hock-endpoint", "summary") is routes[5].sections[0]
        and _named_route_section(routes[4], "hock-endpoint", "summary") is routes[6].sections[0],
        "exact_parent_relations": tuple(
            (interface.parent_name, interface.child_name) for interface in ordered_interfaces
        ) == tuple(EXPECTED_INTERFACE_RELATIONS),
    }

    return {
        "format": CANDIDATE_FORMAT,
        "source": {key: source[key] for key in source_fields},
        "profile_id": candidate.profile_id,
        "variant_source": {
            "id": variant_id,
            "raw_record_present": raw_variant is not None,
            "descriptor_count": len(descriptors),
            "reference_scale": float(form.reference_scale),
        },
        "torso": {
            "stations": [
                {"index": index, "name": station.name, "semantic_key": station.semantic_key}
                for index, station in enumerate(chain.stations)
            ],
            "regions": [
                {
                    "index": index,
                    "name": region.name,
                    "interval": [region.start_index, region.end_index],
                    "semantic_key": region.semantic_key,
                }
                for index, region in enumerate(chain.regions)
            ],
            "station_count": len(chain.stations),
            "region_count": len(chain.regions),
            "region_intervals": [[region.start_index, region.end_index] for region in chain.regions],
        },
        "routes": {
            "routes": route_records,
            "count": len(routes),
            "names": [route.route_name for route in routes],
            "required_head_neck_sections": len(routes[0].sections) == 8,
            "required_head_neck_connections": len(routes[0].connections) == 7,
            "bilateral_arm_authored_sections": [
                sum(section.source_index is not None for section in route.sections)
                for route in routes[1:3]
            ],
            "bilateral_arm_total_sections": [len(route.sections) for route in routes[1:3]],
            "binding_evidence_count": route_binding_evidence_count,
            "total_binding_evidence_count": total_binding_evidence_count,
            "bilateral_leg_authored_sections": [
                sum(section.source_index is not None for section in route.sections)
                for route in routes[3:5]
            ],
                "bilateral_leg_total_sections": [len(route.sections) for route in routes[3:5]],
            "bilateral_leg_derived_sections": [["pelvis-seat", "hip-cup-rim", "femoral-neck"] for _ in routes[3:5]],
            "bilateral_foot_authored_sections": [2, 2],
            "endpoint_closures_explicit": all(route.endpoint_closures for route in routes),
            "shared_interfaces": {
                "cranium_mid": {"head_section_index": 3, "connection_indices": [2, 3, 4]},
                "elbows": [3, 3],
                "wrist_transitions": [5, 5],
                "knees": [5, 5],
                "hocks": [7, 7],
                "hip_cup_sections": ["pelvis-seat", "hip-cup-rim", "femoral-neck"],
                "feet_use_leg_hock_identity": _named_route_section(routes[3], "hock-endpoint", "summary") is routes[5].sections[0]
                and _named_route_section(routes[4], "hock-endpoint", "summary") is routes[6].sections[0],
            },
        },
        "interfaces": {
            "count": len(ordered_interfaces),
            "parent_relations": [[interface.parent_name, interface.child_name] for interface in ordered_interfaces],
            "patches": [
                {
                    "identifier": interface.identifier,
                    "parent": interface.parent_name,
                    "child": interface.child_name,
                    "semantic_key": interface.semantic_key,
                    "authority": interface.authority.identifier,
                }
                for interface in ordered_interfaces
            ],
            "registration_order_independent": True,
            "authority_source": "interface samples plus side-matched authority-only shoulder controls",
        },
        "shoulder_controls": {
            "count": len(controls),
            "names": [control.name for control in controls],
            "semantic_binding_complete": semantic_binding_complete,
            "authority_only": True,
            "skin_consumer": False,
            "counterfactual_authority_bound_influence": "proven",
            "control_local_final_skin_influence": False,
            "control_local_final_skin_influence_status": "unverified",
            "shoulder_visual_floor_satisfaction": "unverified",
            "axilla_visual_floor_satisfaction": "unverified",
            "controls": [
                {
                    "name": control.name,
                    "namespace": binding["namespace"],
                    "side": binding["side"],
                    "owner": regional_surface_candidate._key_json(binding["owner"]),
                    "role": binding["role"],
                    "frame": {
                        "owner": regional_surface_candidate._key_json(binding["frame"][0]),
                        "role": binding["frame"][1],
                    },
                    "frame_role": binding["frame_role"],
                    "semantic_key": control.semantic_key,
                    "source_key": control.source_key,
                    "canonical_source_key": binding["source_key"],
                    "authority_only": True,
                    "skin_consumer": False,
                    "counterfactual_authority_bound_influence": "proven",
                    "control_local_final_skin_influence": False,
                    "control_local_final_skin_influence_status": "unverified",
                    "visual_floor_satisfaction": "unverified",
                    "interface_id": f"interface:torso->{control.name.split('-', 1)[0]}-arm",
                }
                for control, binding in zip(controls, control_bindings)
            ],
        },
        "proof": proof,
    }


def _candidate_operands(candidate: Any) -> tuple[_DiagnosticOperand, ...]:
    _, chain, routes, interfaces, controls = _validate_candidate_contract(candidate)
    records: list[_DiagnosticOperand] = []
    interface_by_relation = {(item.parent_name, item.child_name): item for item in interfaces}
    route_by_name = {item.route_name: item for item in routes}
    entries = [("base", "skin-source", "chain:regional-surface", chain)]
    entries.extend(
        (f"route:{name}", "skin-source", f"route:{name}", route_by_name[name])
        for name in EXPECTED_ROUTE_NAMES
    )
    entries.extend(
        (
            f"patch:{parent}->{child}",
            "derived-interface-patch",
            f"interface:{parent}->{child}",
            interface_by_relation[(parent, child)],
        )
        for parent, child in EXPECTED_INTERFACE_RELATIONS
    )
    for identifier, kind, semantic_identity, operand in entries:
        if not callable(getattr(operand, "evaluate", None)):
            _fail(f"candidate operand {identifier} has no evaluator")
        lower, upper = _operand_bounds(operand, f"candidate operand {identifier}")
        if not semantic_identity:
            _fail(f"candidate operand {identifier} has no semantic identity")
        records.append(_DiagnosticOperand(identifier, kind, semantic_identity, operand, lower, upper))
    return tuple(records)


def _operand_metadata(operand: _DiagnosticOperand, diagnostic: _DiagnosticMesh | None = None) -> dict[str, Any]:
    record = {
        "identifier": operand.identifier,
        "kind": operand.kind,
        "semantic_identity": operand.semantic_identity,
        "evaluator": f"{type(operand.evaluator).__module__}.{type(operand.evaluator).__qualname__}.evaluate",
        "bounds": {"min": _jsonable(operand.lower), "max": _jsonable(operand.upper)},
    }
    if diagnostic is not None:
        record["surface"] = {
            "samples_per_axis": diagnostic.samples,
            "padding": diagnostic.padding,
            "vertex_count": len(diagnostic.vertices),
            "face_count": len(diagnostic.faces),
            "sample_value_range": [diagnostic.value_minimum, diagnostic.value_maximum],
        }
    return record


def _operand_values(operand: _DiagnosticOperand, points: np.ndarray) -> np.ndarray:
    try:
        values = np.asarray(operand.evaluator.evaluate(points), dtype=np.float64)
    except Exception as exc:
        raise RegionalSurfacePreviewError(
            f"candidate diagnostic evaluator {operand.identifier} failed: {exc}"
        ) from exc
    if values.shape != (len(points),) or not np.all(np.isfinite(values)):
        _fail(f"candidate diagnostic evaluator {operand.identifier} returned invalid values")
    return values


def _diagnostic_mesh(operand: _DiagnosticOperand) -> _DiagnosticMesh:
    span = operand.upper - operand.lower
    padding = max(0.02, float(np.max(span)) * DIAGNOSTIC_PADDING_FRACTION)
    lower = operand.lower - padding
    upper = operand.upper + padding
    axes = tuple(
        np.linspace(lower[index], upper[index], DIAGNOSTIC_SAMPLES, dtype=np.float64)
        for index in range(3)
    )
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    values = _operand_values(operand, points).reshape((DIAGNOSTIC_SAMPLES,) * 3)
    if float(np.min(values)) >= 0.0 or float(np.max(values)) <= 0.0:
        _fail(f"candidate diagnostic operand {operand.identifier} has no zero crossing")
    boundary = np.concatenate(
        (
            values[0].ravel(),
            values[-1].ravel(),
            values[:, 0, :].ravel(),
            values[:, -1, :].ravel(),
            values[:, :, 0].ravel(),
            values[:, :, -1].ravel(),
        )
    )
    if np.any(boundary <= 0.0):
        _fail(f"candidate diagnostic operand {operand.identifier} is clipped by its bounds")
    try:
        raw_vertices, raw_faces, _, _ = marching_cubes(
            values,
            level=0.0,
            spacing=tuple(float(axis[1] - axis[0]) for axis in axes),
            method="lewiner",
            allow_degenerate=False,
        )
    except Exception as exc:
        raise RegionalSurfacePreviewError(
            f"candidate diagnostic operand {operand.identifier} extraction failed: {exc}"
        ) from exc
    vertices = np.asarray(raw_vertices, dtype=np.float64) + lower
    faces = np.asarray(raw_faces, dtype=np.int64)
    if (
        vertices.ndim != 2
        or vertices.shape[1] != 3
        or faces.ndim != 2
        or faces.shape[1] != 3
        or len(vertices) == 0
        or len(faces) == 0
        or not np.all(np.isfinite(vertices))
        or np.any(faces < 0)
        or np.any(faces >= len(vertices))
    ):
        _fail(f"candidate diagnostic operand {operand.identifier} produced invalid mesh arrays")
    return _DiagnosticMesh(
        operand,
        vertices,
        faces,
        DIAGNOSTIC_SAMPLES,
        padding,
        float(np.min(values)),
        float(np.max(values)),
    )


def _diagnostic_colour(identity: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return tuple(88 + int(digest[index]) * 144 // 255 for index in range(3))  # type: ignore[return-value]


def _projection_frame(bounds: tuple[np.ndarray, np.ndarray], basis: np.ndarray, box: tuple[int, int, int, int]) -> dict[str, Any]:
    return surface_preview._projection_frame(bounds, basis, box)


def _frame_screen(frame: dict[str, Any], points: np.ndarray) -> list[tuple[float, float]]:
    return surface_preview._frame_screen(frame, points)


def _draw_skin(draw: ImageDraw.ImageDraw, frame: dict[str, Any], vertices: np.ndarray, faces: np.ndarray) -> None:
    """Forward the exact candidate arrays to the compatible skin primitive."""

    surface_preview._draw_skin(draw, frame, vertices, faces)


def _draw_field_contributors(
    image: Image.Image,
    frame: dict[str, Any],
    diagnostic_meshes: tuple[_DiagnosticMesh, ...],
    font: ImageFont.ImageFont,
) -> None:
    diagnostic_meshes = tuple(
        item for item in diagnostic_meshes
    )
    ordered = sorted(
        enumerate(diagnostic_meshes),
        key=lambda item: float(np.mean((item[1].vertices @ frame["basis"].T)[:, 2])),
    )
    for _, diagnostic in ordered:
        triangles = diagnostic.vertices[diagnostic.faces]
        camera = triangles @ frame["basis"].T
        triangle_order = np.argsort(np.mean(camera[:, :, 2], axis=1), kind="stable")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        colour = _diagnostic_colour(diagnostic.operand.semantic_identity)
        for triangle_index in triangle_order:
            projected = _frame_screen(frame, triangles[int(triangle_index)])
            overlay_draw.polygon(projected, fill=(*colour, 82))
        image.alpha_composite(overlay)

    draw = ImageDraw.Draw(image)
    x0, y0, _, _ = frame["box"]
    draw.text(
        (x0 + 10, y0 + 30),
        "actual final terms: skin sources + derived interface patches",
        fill=(215, 222, 233, 255),
        font=font,
    )
    for index, diagnostic in enumerate(diagnostic_meshes):
        label = f"{diagnostic.operand.identifier} / {diagnostic.operand.semantic_identity}"
        draw.text(
            (x0 + 10, y0 + 44 + index * 12),
            label,
            fill=(*_diagnostic_colour(diagnostic.operand.semantic_identity), 255),
            font=font,
        )


def _draw_source_diagnostics(
    draw: ImageDraw.ImageDraw,
    frame: dict[str, Any],
    witnesses: tuple[dict[str, Any], ...],
    font: ImageFont.ImageFont,
) -> None:
    x0, y0, _, _ = frame["box"]
    draw.text(
        (x0 + 10, y0 + 30),
        "authority-only controls: exact source identity; authority-bound influence proven; local final skin influence and visual-floor satisfaction unverified",
        fill=(215, 222, 233, 255),
        font=font,
    )
    for index, witness in enumerate(witnesses):
        point = np.asarray(witness["point"], dtype=np.float64).reshape(1, 3)
        screen = _frame_screen(frame, point)[0]
        colour = _diagnostic_colour(witness["expected_semantic_identity"])
        radius = 4.0
        draw.ellipse(
            (screen[0] - radius, screen[1] - radius, screen[0] + radius, screen[1] + radius),
            fill=(*colour, 255),
        )
        status = "ok" if witness["reconstruction_error"] <= TRACE_TOLERANCE else "FAIL"
        influence = witness.get("influence_status", "nonzero")
        text = f"{witness['identifier']}: {status}, {len(witness['trace_semantic_keys'])} semantic ids, {influence}"
        draw.text(
            (x0 + 10, y0 + 44 + index * 12),
            text,
            fill=(190, 198, 211, 255),
            font=font,
        )


def _render_png(
    mesh: Any,
    diagnostic_meshes: tuple[_DiagnosticMesh, ...],
    witnesses: tuple[dict[str, Any], ...],
    bounds: tuple[np.ndarray, np.ndarray],
    profile_id: str,
) -> tuple[bytes, tuple[dict[str, Any], ...]]:
    image = Image.new("RGBA", CANVAS, (20, 23, 29, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text(
        (16, 16),
        f"{FORMAT} - {profile_id}",
        fill=(235, 238, 244, 255),
        font=font,
    )
    draw.text(
        (16, 42),
        "SKIN is the exact candidate mesh    FINAL TERMS are actual sources/patches    SOURCE-ONLY DIAGNOSTICS are controls",
        fill=(167, 176, 190, 255),
        font=font,
    )
    projection_lookup = {name: np.asarray(basis, dtype=np.float64) for name, basis, _ in PROJECTIONS}
    shared_frames: dict[str, dict[str, Any]] = {}
    camera_metadata: list[dict[str, Any]] = []
    first_box_by_view = {
        item["projection"]: item["box"]
        for item in PANEL_LAYOUT
        if item["content"] == PANEL_CONTENTS[0]
    }
    for name in VIEW_NAMES:
        base_frame = _projection_frame(bounds, projection_lookup[name], first_box_by_view[name])
        shared_frames[name] = base_frame
        camera_metadata.append(
            {
                "name": name,
                "basis": _jsonable(projection_lookup[name]),
                "base": next(base for view, _, base in PROJECTIONS if view == name),
                "centre": _jsonable(base_frame["centre"]),
                "scale": float(base_frame["scale"]),
            }
        )

    for item in PANEL_LAYOUT:
        name = item["projection"]
        box = item["box"]
        frame = {**shared_frames[name], "box": box}
        panel_colour = {
            "skin": (24, 27, 34, 255),
            "field-contributors": (24, 31, 39, 255),
            "source-diagnostics": (28, 35, 43, 255),
        }[item["content"]]
        draw.rectangle(box, fill=panel_colour)
        if item["content"] == "skin":
            # These are deliberately the proof arrays themselves.  Do not
            # substitute a diagnostic mesh or call a second surface builder.
            _draw_skin(draw, frame, mesh.vertices, mesh.faces)
            panel_label = "SKIN (exact SurfaceMeshProof)"
        elif item["content"] == "field-contributors":
            _draw_field_contributors(image, frame, diagnostic_meshes, font)
            panel_label = "FIELD CONTRIBUTORS (actual operands)"
        else:
            _draw_source_diagnostics(draw, frame, witnesses, font)
            panel_label = "SOURCE DIAGNOSTICS (reports/traces)"
        draw.rectangle(box, outline=(74, 82, 96, 255), width=2)
        draw.text(
            (box[0] + 10, box[1] + 8),
            f"{name} -- {panel_label}",
            fill=(235, 238, 244, 255),
            font=font,
        )

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue(), tuple(camera_metadata)


def _validate_png(png_bytes: bytes) -> None:
    if not isinstance(png_bytes, bytes) or len(png_bytes) < 8 or png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        _fail("renderer did not produce a PNG signature")
    try:
        with Image.open(BytesIO(png_bytes)) as image:
            if image.format != "PNG" or image.mode != "RGB" or image.size != CANVAS:
                _fail("renderer produced an invalid PNG mode or dimensions")
            image.load()
    except RegionalSurfacePreviewError:
        raise
    except Exception as exc:
        raise RegionalSurfacePreviewError(f"renderer produced an invalid PNG: {exc}") from exc


def _face_component_count(faces: np.ndarray) -> int:
    """Count face components through shared undirected edges."""

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


def _mesh_topology_proof(vertices: np.ndarray, faces: np.ndarray) -> dict[str, Any]:
    if len(vertices) == 0 or len(faces) == 0:
        _fail("candidate mesh proof arrays must not be empty")
    repeated_indices = (
        (faces[:, 0] == faces[:, 1])
        | (faces[:, 1] == faces[:, 2])
        | (faces[:, 2] == faces[:, 0])
    )
    triangles = vertices[faces]
    cross_products = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    zero_area = np.sum(cross_products * cross_products, axis=1) <= MESH_DEGENERACY_TOLERANCE**2
    if np.any(repeated_indices) or np.any(zero_area):
        _fail("candidate mesh contains degenerate faces")
    canonical_faces = np.sort(faces, axis=1)
    _, face_counts = np.unique(canonical_faces, axis=0, return_counts=True)
    duplicate_face_count = int(sum(int(count) - 1 for count in face_counts if count > 1))
    if duplicate_face_count:
        _fail(f"candidate mesh contains {duplicate_face_count} duplicate faces")

    face_edges = np.stack((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)]), axis=1)
    edges = np.sort(face_edges.reshape(-1, 2), axis=1)
    _, edge_counts = np.unique(edges, axis=0, return_counts=True)
    boundary_edge_count = int(np.count_nonzero(edge_counts == 1))
    nonmanifold_edge_count = int(np.count_nonzero(edge_counts > 2))
    invalid_edge_incidence = int(np.count_nonzero(edge_counts != 2))
    if invalid_edge_incidence:
        _fail(
            "candidate mesh has invalid edge incidence: "
            f"boundary_edges={boundary_edge_count}, nonmanifold_edges={nonmanifold_edge_count}"
        )
    connected_components = _face_component_count(faces)
    if connected_components != 1:
        _fail(f"candidate mesh face graph is disconnected: components={connected_components}")
    nonmanifold_vertex_count = _nonmanifold_vertex_count(faces)
    if nonmanifold_vertex_count != 0:
        _fail(f"candidate mesh has nonmanifold vertex links: count={nonmanifold_vertex_count}")
    return {
        "connected": True,
        "closed_triangle_2_manifold": True,
        "proven": True,
        "watertight": True,
        "connected_components": connected_components,
        "boundary_edge_count": boundary_edge_count,
        "nonmanifold_edge_count": nonmanifold_edge_count,
        "nonmanifold_vertex_count": nonmanifold_vertex_count,
    }


def _mesh_metadata(mesh: Any, padding: float) -> dict[str, Any]:
    expected = (
        "vertices",
        "faces",
        "normals",
        "lower",
        "upper",
        "samples",
        "connected",
        "closed_triangle_2_manifold",
        "topology_proven",
        "watertight",
        "connected_components",
        "boundary_edge_count",
        "nonmanifold_edge_count",
        "nonmanifold_vertex_count",
    )
    if not all(hasattr(mesh, item) for item in expected):
        _fail("candidate mesh proof is absent or malformed")
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    normals = np.asarray(mesh.normals)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3 or normals.shape != vertices.shape:
        _fail("candidate mesh proof arrays are malformed")
    if not np.issubdtype(vertices.dtype, np.floating) or not np.issubdtype(normals.dtype, np.floating) or not np.issubdtype(faces.dtype, np.integer):
        _fail("candidate mesh proof arrays have invalid dtypes")
    if len(vertices) == 0 or len(faces) == 0 or len(normals) == 0:
        _fail("candidate mesh proof arrays must not be empty")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(normals)) or np.any(faces < 0) or np.any(faces >= len(vertices)):
        _fail("candidate mesh proof arrays are non-finite or out of range")
    lower = _vector(mesh.lower, "candidate mesh lower")
    upper = _vector(mesh.upper, "candidate mesh upper")
    if np.any(upper <= lower):
        _fail("candidate mesh proof bounds are not ordered")
    try:
        proof = _mesh_topology_proof(vertices, faces)
    except (IndexError, TypeError, ValueError) as exc:
        raise RegionalSurfacePreviewError(f"candidate mesh topology proof failed: {exc}") from exc

    def _reported_count(name: str) -> int:
        value = getattr(mesh, name)
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) < 0:
            _fail(f"candidate mesh {name} is not a non-negative integer")
        return int(value)

    reported_flags = {}
    for name in ("connected", "closed_triangle_2_manifold", "topology_proven", "watertight"):
        value = getattr(mesh, name)
        if type(value) is not bool:
            _fail(f"candidate mesh {name} is not a boolean proof flag")
        reported_flags[name] = value
    reported_counts = {
        name: _reported_count(name)
        for name in (
            "connected_components",
            "boundary_edge_count",
            "nonmanifold_edge_count",
            "nonmanifold_vertex_count",
        )
    }
    for name, expected_value in proof.items():
        actual_name = "topology_proven" if name == "proven" else name
        actual = reported_flags.get(actual_name, reported_counts.get(actual_name))
        if actual != expected_value:
            _fail(f"candidate mesh {name} proof flag/count disagrees with independent topology proof")
    if type(getattr(mesh, "samples")) is not int or mesh.samples <= 0:
        _fail("candidate mesh samples are invalid")
    try:
        padding_value = float(padding)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RegionalSurfacePreviewError(f"candidate mesh padding is invalid: {exc}") from exc
    if not math.isfinite(padding_value) or padding_value < 0.0:
        _fail("candidate mesh padding is invalid")

    def array_hash(array: np.ndarray) -> str:
        return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()

    return {
        "samples_per_axis": mesh.samples,
        "padding": padding_value,
        "bounds": {"min": _jsonable(lower), "max": _jsonable(upper)},
        "topology_proof": proof,
        "arrays": {
            "vertices": {"shape": list(vertices.shape), "dtype": str(vertices.dtype), "sha256": array_hash(vertices)},
            "faces": {"shape": list(faces.shape), "dtype": str(faces.dtype), "sha256": array_hash(faces)},
            "normals": {"shape": list(normals.shape), "dtype": str(normals.dtype), "sha256": array_hash(normals)},
        },
    }


def _source_semantic_keys(report: Any) -> tuple[str, ...]:
    keys: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key == "source_semantic_keys" and isinstance(item, (tuple, list)):
                    keys.extend(str(entry) for entry in item)
                else:
                    visit(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                visit(item)

    visit(report)
    return tuple(dict.fromkeys(keys))


def _trace_active_evidence(
    trace: Any,
    expected_identity: str,
    *,
    target_kind: str = "semantic",
    expected_authority_id: str | None = None,
    expected_parent_id: str | None = None,
    expected_child_id: str | None = None,
) -> tuple[float, tuple[str, ...]]:
    """Return an exact source or parent-targeted patch weight from active branches."""

    matches: list[tuple[str, float]] = []

    def visit(node: Any, incoming_weight: float) -> None:
        try:
            semantic_keys = tuple(str(item) for item in node.semantic_keys)
            children = tuple(node.children)
            sensitivities = tuple(float(item) for item in node.sensitivity)
        except Exception as exc:
            raise RegionalSurfacePreviewError(f"operation trace contributor record is malformed: {exc}") from exc
        if not semantic_keys or not math.isfinite(incoming_weight) or incoming_weight < 0.0:
            _fail("operation trace contributor record has invalid semantic or weight data")
        if target_kind == "interface" and getattr(node, "operator", None) == "parent-targeted-interface-patch":
            if (
                node.authority_id == expected_authority_id
                and node.parent_id == expected_parent_id
                and node.child_id == expected_child_id
            ):
                matches.append(("active-interface-patch", incoming_weight))
            return
        if target_kind == "semantic" and getattr(node, "operator", None) == "parent-targeted-interface-patch":
            if len(sensitivities) != 2 or any(
                not math.isfinite(item) or item < 0.0 for item in sensitivities
            ):
                _fail("operation trace interface patch sensitivities are invalid")
            if expected_identity == f"route:{node.parent_id}":
                matches.append(("active-route-patch-parent", incoming_weight * sensitivities[0]))
                return
            if expected_identity == f"route:{node.child_id}":
                matches.append(("active-route-patch-child", incoming_weight * sensitivities[1]))
                return
        if (
            target_kind == "semantic"
            and expected_identity in semantic_keys
            and getattr(node, "operator", None) == "section-sweep-hard-min"
            and expected_identity.startswith("route:")
        ):
            # The public trace adds the route identity to this component-root
            # node.  Stop there so the source witness measures the final
            # component term, including any parent-targeted patch coefficient,
            # rather than the route's internal hard-min tie weights.
            matches.append(("active-route-term", incoming_weight))
            return
        if children:
            if len(sensitivities) != len(children) or any(not math.isfinite(item) or item < 0.0 for item in sensitivities):
                _fail("operation trace child sensitivities are invalid")
            for child, sensitivity in zip(children, sensitivities):
                visit(child, incoming_weight * sensitivity)
            return
        if len(sensitivities) != 1 or not math.isfinite(sensitivities[0]) or sensitivities[0] < 0.0:
            _fail("operation trace leaf sensitivity is invalid")
        if target_kind == "semantic" and expected_identity in semantic_keys:
            matches.append(("active-trace-leaf", incoming_weight * sensitivities[0]))

    visit(trace, 1.0)
    return sum(weight for _, weight in matches), tuple(kind for kind, _ in matches)


def _capture_witness(
    candidate: Any,
    identifier: str,
    point: Any,
    expected_identity: str,
    expected_component_name: str,
    *,
    target_kind: str = "component",
    trace_identity: str | None = None,
    expected_path: str | None = None,
    patch: Any | None = None,
) -> dict[str, Any]:
    point_array = _vector(point, f"witness {identifier}.point")
    try:
        value = float(candidate.evaluate(point_array))
        report = candidate.contribution_report(point_array)
        trace = candidate.operation_trace(point_array)
        trace_dict = trace.as_dict()
        reconstructed = float(trace.reconstruct())
    except Exception as exc:
        raise RegionalSurfacePreviewError(f"witness {identifier} diagnostics failed: {exc}") from exc
    if not isinstance(trace_dict, dict) or not math.isfinite(value) or not math.isfinite(reconstructed):
        _fail(f"witness {identifier} has invalid trace or evaluation")
    error = abs(reconstructed - value)
    if error > TRACE_TOLERANCE:
        _fail(f"witness {identifier} trace does not reconstruct candidate.evaluate")
    trace_keys = tuple(str(item) for item in trace.semantic_keys)
    source_keys = _source_semantic_keys(report)
    if not trace_keys or not source_keys:
        _fail(f"witness {identifier} lost contributor semantic identity")
    if target_kind == "interface":
        if patch is None:
            _fail(f"witness {identifier} has no patch object")
        if patch.semantic_key != expected_identity:
            _fail(f"witness {identifier} patch semantic identity is inconsistent")
        active_trace_weight, active_trace_kinds = _trace_active_evidence(
            trace,
            expected_identity,
            target_kind="interface",
            expected_authority_id=patch.authority.identifier,
            expected_parent_id=patch.parent_name,
            expected_child_id=patch.child_name,
        )
    else:
        trace_identity = expected_identity if trace_identity is None else trace_identity
        if trace_identity not in trace_keys:
            _fail(f"witness {identifier} lost contributor semantic identity")
        active_trace_weight, active_trace_kinds = _trace_active_evidence(trace, trace_identity)
    if active_trace_weight <= INFLUENCE_TOLERANCE:
        _fail(f"witness {identifier} expected contributor is present only on inactive trace branches")

    influence = report.get("geometric_influence") if isinstance(report, Mapping) else None
    if not isinstance(influence, Mapping):
        _fail(f"witness {identifier} has no geometric influence report")
    if target_kind == "interface":
        interfaces = influence.get("interfaces")
        if not isinstance(interfaces, Mapping):
            _fail(f"witness {identifier} has no final interface influence map")
        raw_report_weight = interfaces.get(expected_component_name)
    elif expected_component_name == "base":
        raw_report_weight = influence.get("base")
    else:
        components = influence.get("components")
        if not isinstance(components, Mapping):
            _fail(f"witness {identifier} has no final component influence map")
        raw_report_weight = components.get(expected_component_name)
    if raw_report_weight is None:
        _fail(f"witness {identifier} has no influence for final component {expected_component_name!r}")
    try:
        expected_report_weight = float(raw_report_weight)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RegionalSurfacePreviewError(f"witness {identifier} component influence is invalid: {exc}") from exc
    if not math.isfinite(expected_report_weight) or expected_report_weight < 0.0:
        _fail(f"witness {identifier} component influence is invalid")
    if expected_report_weight <= INFLUENCE_TOLERANCE:
        _fail(f"witness {identifier} expected final component has zero geometric influence")
    if abs(expected_report_weight - active_trace_weight) > TRACE_TOLERANCE:
        _fail(f"witness {identifier} trace and final component influence weights disagree")

    result = {
        "identifier": identifier,
        "point": _jsonable(point_array),
        "evaluated_value": value,
        "reconstructed_value": reconstructed,
        "reconstruction_error": error,
        "expected_semantic_identity": expected_identity,
        "expected_path": expected_path or identifier,
        "trace_semantic_keys": list(trace_keys),
        "source_semantic_keys": list(source_keys),
        "trace_identity": trace_identity,
        "active_trace_contribution": active_trace_weight,
        "active_trace_kinds": list(active_trace_kinds),
        "expected_component_name": expected_component_name,
        "final_term_kind": "derived-interface-patch" if target_kind == "interface" else "skin-source",
        "expected_component_influence": expected_report_weight,
        "nonzero_geometric_influence": True,
        "influence_status": "nonzero final interface influence" if target_kind == "interface" else "nonzero final skin-source influence",
        "contribution_report": _jsonable(report),
        "operation_trace": _jsonable(trace_dict),
    }
    if target_kind == "interface":
        result["interface"] = {
            "identifier": patch.identifier,
            "semantic_identity": patch.semantic_key,
            "parent": patch.parent_name,
            "child": patch.child_name,
            "authority": patch.authority.identifier,
        }
    return result


def _influence_weight(report: Any, component_name: str, *, target_kind: str = "component") -> float:
    if not isinstance(report, Mapping):
        _fail("candidate contribution report is not a mapping")
    influence = report.get("geometric_influence")
    if not isinstance(influence, Mapping):
        _fail("candidate contribution report has no geometric influence map")
    if target_kind == "interface":
        interfaces = influence.get("interfaces")
        if not isinstance(interfaces, Mapping):
            _fail("candidate contribution report has no final interface map")
        raw_weight = interfaces.get(component_name)
    elif component_name == "base":
        raw_weight = influence.get("base")
    else:
        components = influence.get("components")
        if not isinstance(components, Mapping):
            _fail("candidate contribution report has no final component map")
        raw_weight = components.get(component_name)
    if raw_weight is None:
        _fail(f"candidate contribution report has no component {component_name!r}")
    try:
        weight = float(raw_weight)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RegionalSurfacePreviewError(f"candidate component {component_name} influence is invalid: {exc}") from exc
    if not math.isfinite(weight) or weight < 0.0:
        _fail(f"candidate component {component_name} influence is invalid")
    return weight


def _active_region_witness_point(candidate: Any, region: Any, station: Any) -> np.ndarray:
    center = _vector(station.center, f"region {region.name}.witness_center")
    radius = max(0.5, float(np.min(np.asarray(station.radii, dtype=np.float64))) * 0.9)
    directions = [(0.0, 0.0, 0.0)]
    directions.extend(
        (float(x), float(y), float(z))
        for x in (-1, 0, 1)
        for y in (-1, 0, 1)
        for z in (-1, 0, 1)
        if (x, y, z) != (0, 0, 0)
    )
    for direction in directions:
        if direction == (0.0, 0.0, 0.0):
            point = center
        else:
            unit = np.asarray(direction, dtype=np.float64)
            unit /= np.linalg.norm(unit)
            point = center + radius * unit
        trace = candidate.operation_trace(point)
        weight, _ = _trace_active_evidence(trace, region.semantic_key)
        if weight > INFLUENCE_TOLERANCE and _influence_weight(candidate.contribution_report(point), "base") > INFLUENCE_TOLERANCE:
            return point
    _fail(f"region {region.name} has no finite active trace witness")


def _active_component_witness_point(
    candidate: Any,
    component: Any,
    identity: str,
    component_name: str,
    *,
    target_kind: str = "component",
) -> np.ndarray:
    """Find a finite point where a final field component is trace- and report-active."""

    seeds: list[np.ndarray] = []
    if hasattr(component, "center"):
        seeds.append(_vector(component.center, f"component {component_name}.center"))
    if target_kind == "interface" and hasattr(component, "authority"):
        seeds.append(_vector(component.authority.center, f"component {component_name}.authority.center"))
    for section in getattr(component, "sections", ()):
        seeds.append(_vector(section.center, f"component {component_name}.{section.name}.center"))
    for closure in getattr(component, "endpoint_closures", ()):
        seeds.append(_vector(closure.center, f"component {component_name}.{closure.name}.center"))
    lower, upper = _operand_bounds(component, f"component {component_name}")
    seeds.append((lower + upper) * 0.5)
    directions = (
        np.asarray((1.0, 0.0, 0.0)),
        np.asarray((-1.0, 0.0, 0.0)),
        np.asarray((0.0, 1.0, 0.0)),
        np.asarray((0.0, -1.0, 0.0)),
        np.asarray((0.0, 0.0, 1.0)),
        np.asarray((0.0, 0.0, -1.0)),
    )
    for seed in seeds:
        radii = getattr(component, "radii", None)
        if radii is None and hasattr(component, "sections") and component.sections:
            radii = component.sections[0].radii
        radius = max(0.05, float(np.min(np.asarray(radii, dtype=np.float64))) if radii is not None else float(np.max(upper - lower)) * 0.1)
        points = [seed]
        for direction in directions:
            points.extend(seed + fraction * radius * direction for fraction in (0.5, 1.0, 1.5, 2.0, 2.5))
        for point in points:
            report = candidate.contribution_report(point)
            if _influence_weight(report, component_name, target_kind=target_kind) <= INFLUENCE_TOLERANCE:
                continue
            trace = candidate.operation_trace(point)
            if target_kind == "interface":
                active_weight, _ = _trace_active_evidence(
                    trace,
                    identity,
                    target_kind="interface",
                    expected_authority_id=component.authority.identifier,
                    expected_parent_id=component.parent_name,
                    expected_child_id=component.child_name,
                )
            else:
                active_weight, _ = _trace_active_evidence(trace, identity)
            if active_weight > INFLUENCE_TOLERANCE:
                return _vector(point, f"component {component_name}.witness")
    _fail(f"component {component_name} has no finite active trace/report witness")


def _control_counterfactual(candidate: Any, control: Any) -> tuple[Any, Any, Any]:
    """Rebuild only the matching authority with one exact control omitted."""

    hybrid = regional_surface_candidate._load_hybrid()
    side = control.name.split("-", 1)[0]
    arm = next(route for route in candidate.routes if route.route_name == f"{side}-arm")
    patch = next(
        item for item in candidate.interfaces
        if (item.parent_name, item.child_name) == ("torso", f"{side}-arm")
    )
    source_namespace = candidate.source["namespace"]
    remaining = regional_surface_candidate._remaining_shoulder_controls_for_counterfactual(
        candidate.controls,
        side,
        control,
        source_namespace,
    )
    points, radii = regional_surface_candidate._torso_arm_interface_samples(hybrid, candidate.chain, arm)
    authority, k, _ = regional_surface_candidate._interface_authority(
        hybrid,
        f"torso->{side}-arm",
        points,
        radii,
        regional_surface_candidate.INTERFACE_PAD,
        remaining,
        source_namespace=source_namespace,
        allow_control_subset=True,
        control_subset_side=side,
    )
    if k != patch.blend_radius:
        _fail(f"control {control.name} counterfactual changed interface k")
    counterfactual_patch = replace(patch, authority=authority)
    counterfactual_interfaces = tuple(
        counterfactual_patch if item is patch else item for item in candidate.interfaces
    )
    counterfactual_field = hybrid.FullSectionComposite(
        candidate.chain,
        candidate.field.attachments,
        interfaces=counterfactual_interfaces,
    )
    return patch, counterfactual_patch, counterfactual_field


def _surface_edge_roots(field: Any, lower: np.ndarray, upper: np.ndarray, samples: int = 15) -> tuple[np.ndarray, ...]:
    """Return deterministic linearly interpolated roots on a bounded grid."""

    axes = tuple(np.linspace(lower[index], upper[index], samples, dtype=np.float64) for index in range(3))
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    values = np.asarray(field.evaluate(grid.reshape(-1, 3)), dtype=np.float64).reshape((samples,) * 3)
    roots: list[np.ndarray] = []
    for axis in range(3):
        first_slices = [slice(None)] * 3
        second_slices = [slice(None)] * 3
        first_slices[axis] = slice(0, -1)
        second_slices[axis] = slice(1, None)
        first_values = values[tuple(first_slices)]
        second_values = values[tuple(second_slices)]
        crossings = np.argwhere(first_values * second_values <= 0.0)
        for crossing in crossings:
            first_index = list(int(item) for item in crossing)
            second_index = list(first_index)
            second_index[axis] += 1
            first = grid[tuple(first_index)]
            second = grid[tuple(second_index)]
            first_value = float(values[tuple(first_index)])
            second_value = float(values[tuple(second_index)])
            denominator = first_value - second_value
            fraction = 0.5 if denominator == 0.0 else float(np.clip(first_value / denominator, 0.0, 1.0))
            roots.append(first + fraction * (second - first))
    return tuple(roots)


def _capture_authority_control_witness(candidate: Any, control: Any) -> dict[str, Any]:
    """Prove authority-bound control causality without claiming local skin use."""

    patch, counterfactual_patch, counterfactual_field = _control_counterfactual(candidate, control)
    control_center = _vector(control.center, f"control {control.name}.center")
    control_radii = _vector(control.radii, f"control {control.name}.radii")
    lower = np.minimum(control_center - 1.5 * control_radii, np.asarray(patch.authority.bounds[0]))
    upper = np.maximum(control_center + 1.5 * control_radii, np.asarray(patch.authority.bounds[1]))
    best: tuple[float, dict[str, Any]] | None = None
    roots = np.asarray(_surface_edge_roots(candidate, lower, upper), dtype=np.float64)
    if roots.ndim != 2 or roots.shape[1] != 3 or len(roots) == 0:
        _fail(f"control {control.name} authority bounds have no final-surface crossings")
    root_values = np.asarray(candidate.evaluate(roots), dtype=np.float64)
    counterfactual_values = np.asarray(counterfactual_field.evaluate(roots), dtype=np.float64)
    full_gates = np.asarray(patch.authority.gate(roots), dtype=np.float64)
    omitted_gates = np.asarray(counterfactual_patch.authority.gate(roots), dtype=np.float64)
    scores = np.abs(counterfactual_values - root_values) * np.abs(full_gates - omitted_gates)
    local_root_indices = np.flatnonzero(
        np.sum(((roots - control_center) / control_radii) ** 2, axis=1) <= 1.0
    )
    ordered_indices = np.argsort(-scores, kind="stable")
    selected_indices = list(int(index) for index in ordered_indices[:8])
    selected_indices.extend(
        int(local_root_indices[local_position])
        for local_position in np.argsort(-scores[local_root_indices], kind="stable")[:8]
        if int(local_root_indices[local_position]) not in selected_indices
    )
    best_local: tuple[float, dict[str, Any]] | None = None
    for root_index in selected_indices:
        if scores[root_index] <= INFLUENCE_TOLERANCE:
            continue
        point = roots[root_index].copy()
        for _ in range(6):
            value = float(candidate.evaluate(point))
            if abs(value) <= TRACE_TOLERANCE:
                break
            gradient = np.asarray(candidate.field.gradient(point), dtype=np.float64)
            gradient_squared = float(np.dot(gradient, gradient))
            if not math.isfinite(gradient_squared) or gradient_squared <= 1.0e-16:
                break
            point -= value * gradient / gradient_squared
        final_value = float(candidate.evaluate(point))
        if abs(final_value) > TRACE_TOLERANCE:
            continue
        counterfactual_value = float(counterfactual_field.evaluate(point))
        delta = abs(counterfactual_value - final_value)
        if delta <= INFLUENCE_TOLERANCE:
            continue
        report = candidate.contribution_report(point)
        interface_influence = _influence_weight(report, patch.identifier, target_kind="interface")
        if interface_influence <= INFLUENCE_TOLERANCE:
            continue
        trace = candidate.operation_trace(point)
        active_weight, _ = _trace_active_evidence(
            trace,
            patch.semantic_key,
            target_kind="interface",
            expected_authority_id=patch.authority.identifier,
            expected_parent_id=patch.parent_name,
            expected_child_id=patch.child_name,
        )
        reconstructed = float(trace.reconstruct())
        if active_weight <= INFLUENCE_TOLERANCE or abs(reconstructed - final_value) > TRACE_TOLERANCE:
            continue
        full_gate = float(patch.authority.gate(point.reshape(1, 3))[0])
        omitted_gate = float(counterfactual_patch.authority.gate(point.reshape(1, 3))[0])
        if abs(full_gate - omitted_gate) <= INFLUENCE_TOLERANCE:
            continue
        source_trace = control.operation_trace(point)
        source_report = control.source_provenance(point)
        source_keys = _source_semantic_keys(source_report)
        if control.semantic_key not in source_trace.semantic_keys or control.semantic_key not in source_keys:
            _fail(f"control {control.name} lost source identity")
        normalized_control_radius = float(np.sqrt(np.sum(((point - control_center) / control_radii) ** 2)))
        inside_control_ellipsoid = normalized_control_radius <= 1.0
        record = {
            "identifier": f"control:{control.name}",
            "expected_path": f"authority:{patch.identifier}",
            "point": _jsonable(point),
            "evaluated_value": final_value,
            "reconstructed_value": reconstructed,
            "reconstruction_error": abs(reconstructed - final_value),
            "counterfactual_value": counterfactual_value,
            "counterfactual_delta": delta,
            "near_zero": abs(final_value) <= TRACE_TOLERANCE,
            "expected_semantic_identity": control.semantic_key,
            "trace_semantic_keys": list(trace.semantic_keys),
            "source_trace_semantic_keys": list(source_trace.semantic_keys),
            "source_semantic_keys": list(source_keys),
            "expected_component_name": control.name,
            "final_term_kind": "authority-only-control",
            "interface": {
                "identifier": patch.identifier,
                "semantic_identity": patch.semantic_key,
                "parent": patch.parent_name,
                "child": patch.child_name,
                "authority": patch.authority.identifier,
            },
            "expected_component_influence": interface_influence,
            "authority_bound_influence_weight": interface_influence,
            "counterfactual_authority_bound_influence": "proven",
            "control_local_final_skin_influence": False,
            "control_local_final_skin_influence_status": "unverified",
            "visual_floor_satisfaction": "unverified",
            "control_ellipsoid_normalized_radius": normalized_control_radius,
            "control_ellipsoid_near_zero_omission_witness": inside_control_ellipsoid,
            "influence_status": "proven through matching interface authority; local control influence unverified",
            "full_authority_gate": full_gate,
            "omitted_input_gate": omitted_gate,
            "blend_radius": patch.blend_radius,
            "maximum_displacement": patch.blend_radius * math.log(2.0),
            "contribution_report": _jsonable(report),
            "source_report": _jsonable(source_report),
            "operation_trace": _jsonable(trace.as_dict()),
            "source_trace": _jsonable(source_trace.as_dict()),
        }
        score = delta
        if best is None or score > best[0]:
            best = (score, record)
        if inside_control_ellipsoid and (best_local is None or score > best_local[0]):
            best_local = (score, record)
    if best is None:
        _fail(f"control {control.name} has no near-zero counterfactual authority witness")
    return (best_local or best)[1]


def _capture_witnesses(candidate: Any) -> tuple[dict[str, Any], ...]:
    field, _, routes, interfaces, controls = _validate_candidate_contract(candidate)
    regions = tuple(candidate.regions)
    stations = tuple(candidate.stations)
    if len(regions) != 3 or len(stations) != 7:
        _fail("candidate witness inventory is incomplete")
    records: list[dict[str, Any]] = []
    for region in regions:
        identity = getattr(region, "semantic_key", None)
        if not isinstance(identity, str) or not identity:
            _fail("candidate region witness identity is missing")
        station_index = region.start_index + max(1, (region.end_index - region.start_index) // 2)
        records.append(
            _capture_witness(
                candidate,
                f"region:{region.name}",
                _active_region_witness_point(candidate, region, stations[station_index]),
                identity,
                "base",
            )
        )
    for route in routes:
        identity = f"route:{route.route_name}"
        if not isinstance(identity, str) or not identity:
            _fail(f"candidate route {route.route_name} witness identity is missing")
        records.append(
            _capture_witness(
                candidate,
                f"route:{route.route_name}",
                _active_component_witness_point(candidate, route, identity, route.route_name),
                identity,
                route.route_name,
                expected_path=f"route:{route.route_name}",
            )
        )
    interface_by_relation = {(item.parent_name, item.child_name): item for item in interfaces}
    for parent_name, child_name in EXPECTED_INTERFACE_RELATIONS:
        interface = interface_by_relation[(parent_name, child_name)]
        records.append(
            _capture_witness(
                candidate,
                f"patch:{parent_name}->{child_name}",
                _active_component_witness_point(
                    candidate,
                    interface,
                    interface.semantic_key,
                    interface.identifier,
                    target_kind="interface",
                ),
                interface.semantic_key,
                interface.identifier,
                target_kind="interface",
                expected_path=f"patch:{parent_name}->{child_name}",
                patch=interface,
            )
        )
    for control in controls:
        records.append(_capture_authority_control_witness(candidate, control))
    return tuple(records)


def _layout_metadata() -> dict[str, Any]:
    return {
        "panel_order": [item["id"] for item in PANEL_LAYOUT],
        "panels": [
            {
                "id": item["id"],
                "projection": item["projection"],
                "content": item["content"],
                "box": list(item["box"]),
            }
            for item in PANEL_LAYOUT
        ],
        "pairing": "exact skin/actual final terms/authority-only diagnostics per projection",
        "frame": "one shared candidate mesh bounds and projection basis per view",
    }


def render_regional_surface_preview(
    prepared: Any,
    *,
    external_profile_id: str = EXTERNAL_PROFILE_ID,
    mesh_samples: int = DEFAULT_MESH_SAMPLES,
    mesh_padding: float = DEFAULT_MESH_PADDING,
) -> RegionalSurfacePreviewResult:
    """Render one exact-five regional surface slice.

    ``prepared`` must be a validated current-form ``Form`` or its successful
    current prepared-form mapping whose generated structural-profile document
    matches ``external_profile_id``.  The candidate source variant remains
    the separate ``neutral-v0`` binding.  Neither identity is used to branch
    geometry.
    """

    external_profile_id = _validate_external_profile_id(external_profile_id)
    form = _prepared_form(prepared, external_profile_id)
    try:
        candidate = regional_surface_candidate.build_regional_surface_candidate(
            form,
            profile_id="neutral-v0",
            mesh_samples=mesh_samples,
            mesh_padding=mesh_padding,
        )
    except RegionalSurfacePreviewError:
        raise
    except Exception as exc:
        raise RegionalSurfacePreviewError(f"regional surface candidate construction failed: {exc}") from exc

    if getattr(candidate, "profile_id", None) != SOURCE_VARIANT_ID:
        _fail("candidate source variant is not neutral-v0")
    field, chain, routes, interfaces, controls = _validate_candidate_contract(candidate, form)
    mesh = getattr(candidate, "mesh", None)
    if mesh is None:
        _fail("candidate did not return a SurfaceMeshProof")
    mesh_metadata = _mesh_metadata(mesh, mesh_padding)
    operands = _candidate_operands(candidate)
    diagnostic_meshes = tuple(_diagnostic_mesh(operand) for operand in operands)
    witnesses = _capture_witnesses(candidate)
    bounds = (
        _vector(mesh.lower, "mesh camera lower"),
        _vector(mesh.upper, "mesh camera upper"),
    )
    png_bytes, camera_metadata = _render_png(
        mesh,
        diagnostic_meshes,
        witnesses,
        bounds,
        external_profile_id,
    )
    _validate_png(png_bytes)

    diagnostic_by_identifier = {
        diagnostic.operand.identifier: diagnostic
        for diagnostic in diagnostic_meshes
    }
    operand_inventory = {
        operand.identifier: _operand_metadata(operand)
        for operand in operands
    }
    operand_surfaces = {
        identifier: _operand_metadata(operand, diagnostic_by_identifier[identifier])
        for identifier, operand in ((item.identifier, item) for item in operands)
    }
    skin_sources = tuple(item for item in operands if item.kind == "skin-source")
    derived_patches = tuple(item for item in operands if item.kind == "derived-interface-patch")
    if len(skin_sources) != 1 + len(routes) or len(derived_patches) != len(interfaces) or len(operands) != 15:
        _fail("candidate diagnostic inventories are not split by truthful type")
    authority_controls = [
        {
            "identifier": f"control:{control.name}",
            "kind": "authority-only-control",
            "semantic_identity": control.semantic_key,
            "source_key": control.source_key,
            "canonical_source_key": control.source_key,
            "namespace": candidate.source["namespace"],
            "side": control.name.split("-", 1)[0],
            "owner": {
                "namespace": candidate.source["namespace"],
                "anchors": [control.name.split("-", 1)[0]],
                "kind": "part",
                "role": "upper_arm",
            },
            "role": "form_shoulder_peak" if control.name.endswith("shoulder-peak") else "form_axilla",
            "frame": {
                "owner": {
                    "namespace": candidate.source["namespace"],
                    "anchors": [control.name.split("-", 1)[0]],
                    "kind": "part",
                    "role": "upper_arm",
                },
                "role": "form_shoulder_control",
            },
            "interface_id": f"interface:torso->{control.name.split('-', 1)[0]}-arm",
            "authority_only": True,
            "skin_consumer": False,
            "counterfactual_authority_bound_influence": "proven",
            "control_local_final_skin_influence": False,
            "control_local_final_skin_influence_status": "unverified",
            "visual_floor_satisfaction": "unverified",
        }
        for control in controls
    ]
    diagnostic_inventory = {
        "skin_sources": [operand_inventory[item.identifier] for item in skin_sources],
        "derived_patches": [operand_inventory[item.identifier] for item in derived_patches],
        "authority_controls": authority_controls,
    }
    diagnostics_operands = {
        "skin_sources": [operand_surfaces[item.identifier] for item in skin_sources],
        "derived_patches": [operand_surfaces[item.identifier] for item in derived_patches],
        "authority_controls": authority_controls,
    }
    diagnostics = {
        **diagnostics_operands,
        "operands": [operand_surfaces[item.identifier] for item in operands],
        "base_operand": "base",
        "skin_source_count": len(skin_sources),
        "derived_patch_count": len(derived_patches),
        "authority_control_count": len(authority_controls),
        "attachment_count": len(field.attachments),
        "final_field_type": f"{type(field).__module__}.{type(field).__qualname__}",
        "final_field_graph": {
            "base": "candidate.chain",
            "attachments": [item.name for item in field.attachments],
            "interfaces": [item.identifier for item in interfaces],
            "skin_sources": ["candidate.chain", *(f"candidate.routes[{index}]" for index in range(len(routes)))],
            "derived_patches": [item.identifier for item in interfaces],
            "authority_controls": [item.name for item in controls],
            "final_term_count": 1 + len(routes) + len(interfaces),
        },
        "source_identity": "candidate base/routes and parent-targeted patches; controls influence skin only through matching authority",
        "witness_count": len(witnesses),
        "witnesses": list(witnesses),
    }
    prepared_identity = _prepared_identity(prepared, form)
    candidate_metadata = _candidate_metadata_summary(
        candidate,
        form,
        field,
        chain,
        routes,
        interfaces,
        controls,
    )
    candidate_identity = {
        "format": CANDIDATE_FORMAT,
        "source_variant_id": SOURCE_VARIANT_ID,
        "profile_id": SOURCE_VARIANT_ID,
        "field_type": f"{type(field).__module__}.{type(field).__qualname__}",
        "base_type": f"{type(chain).__module__}.{type(chain).__qualname__}",
        "authority_control_names": [control.name for control in controls],
        "route_names": [route.route_name for route in routes],
        "interface_ids": [item.identifier for item in interfaces],
        "interface_relations": [[item.parent_name, item.child_name] for item in interfaces],
        "skin_source_count": 1 + len(routes),
        "derived_patch_count": len(interfaces),
        "authority_control_count": len(controls),
        "attachment_count": len(field.attachments),
        "interface_count": len(interfaces),
    }
    binding_identity = {
        "external_profile_id": external_profile_id,
        "source_variant_id": SOURCE_VARIANT_ID,
        "geometry_selection": "fixed neutral-v0; external profile identity does not branch geometry",
    }
    core_identity = {
        "axial_base": "candidate.chain",
        "final_field": "candidate.field",
        "final_skin_sources": 1 + len(routes),
        "derived_interface_patches": len(interfaces),
        "authority_only_controls": len(controls),
        "final_attachments": len(field.attachments),
        "final_term_count": 1 + len(routes) + len(interfaces),
        "graph_semantics": "order-independent hard envelope plus exact parent-targeted interface patches",
    }
    renderer_identity = {"format": FORMAT, "views": list(VIEW_NAMES), "canvas": list(CANVAS)}
    metadata = {
        "format": FORMAT,
        "status": "success",
        "profile_id": external_profile_id,
        "source_variant_id": SOURCE_VARIANT_ID,
        "source": {
            **prepared_identity,
            "format": surface_preview.SOURCE_FORMAT,
            "variant_id": SOURCE_VARIANT_ID,
            "hash_kind": prepared_identity["hash_kind"],
        },
        "prepared_input": prepared_identity,
        "identity": {
            "candidate": candidate_identity,
            "binding": binding_identity,
            "core": core_identity,
            "renderer": renderer_identity,
            "png_sha256": hashlib.sha256(png_bytes).hexdigest(),
        },
        "diagnostic_inventory": diagnostic_inventory,
        "candidate_binding": {
            "module": "regional_surface_candidate",
            "callable": "build_regional_surface_candidate",
            "candidate_format": candidate_identity["format"],
            **binding_identity,
        },
        "candidate_graph": {
            "candidate_type": f"{type(candidate).__module__}.{type(candidate).__qualname__}",
            "base": "candidate.chain",
            "base_type": f"{type(chain).__module__}.{type(chain).__qualname__}",
            "authority_controls": [control.name for control in controls],
            "routes": [route.route_name for route in routes],
            "attachments": [item.name for item in field.attachments],
            "interfaces": [item.identifier for item in interfaces],
            "interface_relations": [[item.parent_name, item.child_name] for item in interfaces],
            "skin_source_count": 1 + len(routes),
            "derived_patch_count": len(interfaces),
            "final_field_type": f"{type(field).__module__}.{type(field).__qualname__}",
        },
        "candidate_metadata": candidate_metadata,
        "mesh": mesh_metadata,
        "camera": {
            "canvas": {"width": CANVAS[0], "height": CANVAS[1], "mode": "RGB"},
            "views": list(VIEW_NAMES),
            "bounds": {"min": _jsonable(bounds[0]), "max": _jsonable(bounds[1])},
            "projections": camera_metadata,
        },
        "layout": _layout_metadata(),
        "diagnostics": diagnostics,
        "png": {
            "format": "PNG",
            "mode": "RGB",
            "width": CANVAS[0],
            "height": CANVAS[1],
            "sha256": hashlib.sha256(png_bytes).hexdigest(),
            "bytes": len(png_bytes),
        },
    }
    # Round-trip through the canonical encoder so callers receive ordinary
    # JSON-ready values and the renderer fails closed on any hidden numpy or
    # non-finite value.
    metadata = json.loads(_canonical(_jsonable(metadata)).decode("utf-8"))
    return RegionalSurfacePreviewResult(png_bytes, metadata)


def render(
    prepared: Any,
    *,
    external_profile_id: str = EXTERNAL_PROFILE_ID,
    mesh_samples: int = DEFAULT_MESH_SAMPLES,
    mesh_padding: float = DEFAULT_MESH_PADDING,
) -> RegionalSurfacePreviewResult:
    """Short alias for the stable regional renderer callable."""

    return render_regional_surface_preview(
        prepared,
        external_profile_id=external_profile_id,
        mesh_samples=mesh_samples,
        mesh_padding=mesh_padding,
    )


__all__ = [
    "CANVAS",
    "DEFAULT_MESH_PADDING",
    "DEFAULT_MESH_SAMPLES",
    "EXTERNAL_PROFILE_ID",
    "EXTERNAL_PROFILE_IDS",
    "FORMAT",
    "PANEL_LAYOUT",
    "PreviewError",
    "PROJECTIONS",
    "RegionalSurfacePreview",
    "RegionalSurfacePreviewError",
    "RegionalSurfacePreviewResult",
    "SOURCE_VARIANT_ID",
    "render",
    "render_regional_surface_preview",
]

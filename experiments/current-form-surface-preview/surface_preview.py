#!/usr/bin/env python3
"""Build a bounded, disposable continuous surface from a v8 form envelope.

This module intentionally has no dependency on Creature Kernel runtime code.
It is a small adapter for visual exploration: exact integer form coordinates
are normalized by the supplied reference edge, analytic fields are folded in
stable AddressKey order, and marching cubes produces a temporary mesh.

The recipe compiler first derives a private backend-neutral hybrid guide graph
from the validated descriptors. The current analytic-field implementation is
only an adapter over those guides; the guide graph is not semantic data or a
serialized contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.measure import marching_cubes


FORMAT = "creature-kernel.disposable-surface-preview.v2"
REGIONAL_GUIDE_FORMAT = "creature-kernel.disposable-surface-preview-regional-guide.v7"
SOURCE_FORMAT = "creature-kernel.provisional-form-preview.v8"
AUTHORED_TORSO_PROFILE_FORMAT = "creature-kernel.provisional-form-torso-profile.v1"
AUTHORED_HEAD_NECK_PROFILE_FORMAT = "creature-kernel.provisional-form-head-neck-profile.v1"
VARIANT_IDS = ("neutral-v0", "broad-soft-v0", "lean-readable-v0", "depth-forward-v0")
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_SAMPLES = 128
MAX_VOXELS = 128**3
MAX_FIELD_VALUES = 32_000_000
MAX_DESCRIPTORS = 64
MAX_AUTHORED_DIMENSIONS = 256
MAX_AUTHORED_LANDMARKS = 32
MAX_AUTHORED_FRAMES = 8
CONTROL_COORDINATE_BOUND = 1.0
GUIDE_TOLERANCE = 1.0e-12
TORSO_PROFILE_FRAME_ROLE = "form_torso_profile_control"
TORSO_PROFILE_LANDMARK_PREFIX = "form_torso_profile_"
TORSO_PROFILE_DIMENSION_PREFIX = "form_torso_profile_"
TORSO_PROFILE_DIMENSION_SUFFIXES = ("lateral_radius", "anterior_radius", "posterior_radius")
TORSO_PROFILE_SECTION_NAMES = (
    "lower-pelvis",
    "upper-pelvis",
    "lower-abdomen",
    "waist-abdomen",
    "upper-abdomen",
    "lower-ribcage",
    "upper-ribcage-shoulder",
)
HEAD_NECK_PROFILE_FRAME_ROLE = "form_head_neck_profile_control"
HEAD_NECK_PROFILE_LANDMARK_PREFIX = "form_head_neck_profile_"
HEAD_NECK_PROFILE_DIMENSION_PREFIX = "form_head_neck_profile_"
HEAD_NECK_PROFILE_DIMENSION_SUFFIXES = ("lateral_radius", "up_radius", "forward_radius")
HEAD_NECK_PROFILE_SECTION_NAMES = (
    "neck-collar",
    "neck-upper",
    "head-base",
    "cranium-mid",
    "cranium-crown",
    "muzzle-root",
    "muzzle-mid",
    "muzzle-tip",
)
HEAD_NECK_PROFILE_OWNER_ROLES = ("neck", "neck", "head", "head", "head", "head", "head", "head")
HEAD_NECK_PROFILE_CONNECTIONS = (
    ("neck-collar-to-neck-upper", 0, 1, "vertical-neck-cranium"),
    ("neck-upper-to-head-base", 1, 2, "vertical-neck-cranium"),
    ("head-base-to-cranium-mid", 2, 3, "vertical-neck-cranium"),
    ("cranium-mid-to-cranium-crown", 3, 4, "vertical-neck-cranium"),
    ("cranium-mid-to-muzzle-root", 3, 5, "forward-muzzle"),
    ("muzzle-root-to-muzzle-mid", 5, 6, "forward-muzzle"),
    ("muzzle-mid-to-muzzle-tip", 6, 7, "forward-muzzle"),
)
REGIONAL_ROUTE_ORDER_TORSO = (("torso", (0, 1, 2, 3, 4, 5, 6), 1, "y"),)
REGIONAL_ROUTE_ORDER_AUTHORED_HEAD_NECK = (
    ("neck", (0, 1), 1, "y"),
    ("cranium", (2, 3, 4), 1, "y"),
    ("forward-muzzle", (3, 5, 6, 7), 2, "z"),
)
REGIONAL_ROUTE_ORDER_GUIDE_HEAD_NECK = (
    ("vertical-neck-cranium", (0, 1, 2, 3, 4), 1, "y"),
    ("forward-muzzle", (3, 5, 6, 7), 2, "z"),
)
# A source descriptor may intentionally expand into a small deterministic
# recipe.  This is an implementation bound on the disposable preview, not a
# promise about a future geometry compiler.
MAX_GENERATED_FIELDS = 256
DEFAULT_SAMPLES = 72
DEFAULT_PADDING = 0.75
DEFAULT_SMOOTH_K = 0.12
# The image is intentionally a fixed, private diagnostic layout.  Each view
# gets adjacent guide and skin panels.  The two panels for a view share the
# exact same projected frame; all variants use the same world-space bounds.
CANVAS = (1800, 570)
PANEL_TOP = 72
PANEL_BOTTOM = 548
PANEL_WIDTH = 280
PANEL_GAP = 18
PANEL_LEFT = 12
PROJECTIONS = (
    ("front", ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), "x-right/y-up/z-depth"),
    ("side", ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)), "-z-right/y-up/x-depth"),
    ("three-quarter", ((1.0 / math.sqrt(2.0), 0.0, -1.0 / math.sqrt(2.0),), (0.0, 1.0, 0.0), (1.0 / math.sqrt(2.0), 0.0, 1.0 / math.sqrt(2.0))), "front-right/y-up/depth"),
)


def _panel_box(index: int) -> tuple[int, int, int, int]:
    left = PANEL_LEFT + index * (PANEL_WIDTH + PANEL_GAP)
    return left, PANEL_TOP, left + PANEL_WIDTH, PANEL_BOTTOM


PANEL_LAYOUT = tuple(
    {
        "id": f"{name}-{content}",
        "projection": name,
        "content": content,
        "box": _panel_box(index * 2 + (0 if content == "guide" else 1)),
    }
    for index, (name, _, _) in enumerate(PROJECTIONS)
    for content in ("guide", "skin")
)
# Kept as a simple view-to-bounds map for callers of the original preview
# helper.  Rendering now uses PANEL_LAYOUT for the two adjacent panels.
VIEW_BOXES = {name: (_panel_box(index * 2)[0], PANEL_TOP, _panel_box(index * 2 + 1)[2], PANEL_BOTTOM) for index, (name, _, _) in enumerate(PROJECTIONS)}


class PreviewError(RuntimeError):
    """A fail-closed input, field, extraction, or output error."""


def _fail(message: str) -> None:
    raise PreviewError(message)


def _obj(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{where} must be an object")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{where} must be an array")
    return value


def _int(value: Any, where: str) -> int:
    if type(value) is not int or not -(1 << 63) <= value < (1 << 63):
        _fail(f"{where} must be a signed integer")
    return value


def _number(value: Any, where: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        _fail(f"{where} must be a finite number")
    return float(value)


def _vector(value: Any, where: str) -> tuple[int, int, int]:
    values = _array(value, where)
    if len(values) != 3:
        _fail(f"{where} must contain three integers")
    return tuple(_int(item, f"{where}[{index}]") for index, item in enumerate(values))  # type: ignore[return-value]


def _source_vector(value: Any, where: str, length: int) -> tuple[float, ...]:
    values = _array(value, where)
    if len(values) != length:
        _fail(f"{where} must contain {length} finite numbers")
    result = tuple(_number(item, f"{where}[{index}]") for index, item in enumerate(values))
    if length == 3 and any(abs(item) > CONTROL_COORDINATE_BOUND for item in result):
        _fail(f"{where} components must be within +/-{CONTROL_COORDINATE_BOUND} source units")
    return result


def _address(value: Any, where: str) -> tuple[str, tuple[str, ...], str, str]:
    obj = _obj(value, where)
    if set(obj) != {"namespace", "anchors", "kind", "role"}:
        _fail(f"{where} has unexpected fields")
    namespace = obj.get("namespace")
    kind = obj.get("kind")
    role = obj.get("role")
    anchors = _array(obj.get("anchors"), f"{where}.anchors")
    if not all(type(item) is str and item for item in anchors):
        _fail(f"{where}.anchors must contain non-empty strings")
    if not all(type(item) is str and item for item in (namespace, kind, role)):
        _fail(f"{where} text fields must be strings")
    return (namespace, tuple(anchors), kind, role)


def _address_json(key: tuple[str, tuple[str, ...], str, str]) -> dict[str, Any]:
    return {"namespace": key[0], "anchors": list(key[1]), "kind": key[2], "role": key[3]}


def _shape(value: Any, where: str) -> dict[str, Any]:
    obj = _obj(value, where)
    name = obj.get("name")
    if name == "ellipsoid":
        if set(obj) != {"name", "center", "axis_extents_permille"}:
            _fail(f"{where} has unexpected ellipsoid fields")
        extents = _vector(obj.get("axis_extents_permille"), f"{where}.axis_extents_permille")
        if any(not 0 < x <= 5000 for x in extents):
            _fail(f"{where}.axis_extents_permille must be in 1..5000")
        return {"name": name, "center": list(_vector(obj.get("center"), f"{where}.center")), "axis_extents_permille": list(extents)}
    if name == "capsule":
        if set(obj) != {"name", "from", "to", "radius_permille"}:
            _fail(f"{where} has unexpected capsule fields")
        start, end = _vector(obj.get("from"), f"{where}.from"), _vector(obj.get("to"), f"{where}.to")
        radius = _int(obj.get("radius_permille"), f"{where}.radius_permille")
        if start == end or not 0 < radius <= 5000:
            _fail(f"{where} capsule is degenerate or has invalid radius")
        return {"name": name, "from": list(start), "to": list(end), "radius_permille": radius}
    if name == "tapered-segment":
        if set(obj) != {"name", "from", "to", "start_radius_permille", "end_radius_permille"}:
            _fail(f"{where} has unexpected tapered-segment fields")
        start, end = _vector(obj.get("from"), f"{where}.from"), _vector(obj.get("to"), f"{where}.to")
        r0 = _int(obj.get("start_radius_permille"), f"{where}.start_radius_permille")
        r1 = _int(obj.get("end_radius_permille"), f"{where}.end_radius_permille")
        if start == end or not 0 < r0 <= 5000 or not 0 < r1 <= 5000:
            _fail(f"{where} tapered segment is degenerate or has invalid radius")
        return {"name": name, "from": list(start), "to": list(end), "start_radius_permille": r0, "end_radius_permille": r1}
    _fail(f"{where}.name is unsupported")


def _display_factors(profile_id: str, role: str, shape_name: str) -> tuple[int, ...]:
    """Return the fixed Rust display factors for the closed shape controls."""

    if shape_name == "ellipsoid":
        if profile_id == "neutral-v0":
            return (1_000, 1_000, 1_000)
        if profile_id == "broad-soft-v0":
            if role in {"pelvis", "torso", "head"}:
                return (1_200, 1_000, 1_150)
            if role in {"hand", "foot"}:
                return (1_150, 1_000, 1_150)
            return (1_000, 1_000, 1_000)
        if profile_id == "lean-readable-v0":
            return (800, 1_000, 800)
        if profile_id == "depth-forward-v0":
            if role in {"torso", "head", "foot"}:
                return (1_000, 1_000, 1_300)
            return (1_000, 1_000, 1_000)
    elif shape_name in {"capsule", "tapered-segment"}:
        if profile_id == "broad-soft-v0":
            factor = 1_150
        elif profile_id == "lean-readable-v0":
            factor = 800
        else:
            factor = 1_000
        return (factor,) * (1 if shape_name == "capsule" else 2)
    _fail(f"unsupported display factor combination: {profile_id}/{role}/{shape_name}")


def _scaled_display_value(value: int, factor: int, where: str) -> int:
    """Apply the Rust fixed-factor integer operation and its result bound."""

    scaled = value * factor // 1_000
    if not 0 < scaled <= 5_000:
        _fail(f"{where} fixed display factor produces invalid permille {scaled}")
    return scaled


def _validate_regional_route_order(
    positions: Any,
    routes: tuple[tuple[str, tuple[int, ...], int, str], ...],
    where: str,
) -> None:
    """Reject non-monotone station coordinates for every regional route."""

    try:
        position_count = len(positions)
    except (TypeError, AttributeError):
        _fail(f"{where} route positions are invalid")
    for route_name, indices, axis, axis_name in routes:
        previous: float | None = None
        for index in indices:
            if index < 0 or index >= position_count:
                _fail(f"{where} {route_name} route index {index} is out of range")
            try:
                value = float(positions[index][axis])
            except (IndexError, KeyError, TypeError, ValueError, OverflowError):
                _fail(f"{where} {route_name} route position {index} is invalid")
            if not math.isfinite(value):
                _fail(f"{where} {route_name} route position {index} is not finite")
            if previous is not None and value <= previous:
                _fail(f"{where} {route_name} route must be strictly increasing along {axis_name}")
            previous = value


def _shoulder_depth_factor(profile_id: str) -> int:
    if profile_id == "broad-soft-v0":
        return 1_150
    if profile_id == "lean-readable-v0":
        return 800
    if profile_id in {"neutral-v0", "depth-forward-v0"}:
        return 1_000
    _fail(f"unsupported shoulder depth profile: {profile_id}")


def _authored_dimension(
    form: Form,
    owner: tuple[str, tuple[str, ...], str, str],
    role: str,
) -> tuple[int, dict[str, Any]]:
    matches = tuple(item for item in form.authored_dimensions if item[0] == owner and item[1] == role)
    if len(matches) != 1:
        _fail(f"source-authored dimension {role!r} is not uniquely bound to {_key_text(owner)}")
    return matches[0][2], matches[0][3]


@dataclass(frozen=True)
class Descriptor:
    key: tuple[str, tuple[str, ...], str, str]
    parent: tuple[str, tuple[str, ...], str, str] | None
    point: np.ndarray
    exact_point: tuple[int, int, int]
    shape: dict[str, Any]
    dimension_roles: tuple[str, ...]
    placement_source: str
    profile_id: str
    source: str
    provenance: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class Field:
    """One analytic field owned by a source descriptor.

    Recipe components are deliberately not semantic nodes.  ``owner`` is the
    only identity that can be emitted as a winner label, so a compound recipe
    cannot accidentally introduce synthetic body-part IDs.
    """

    owner: Descriptor
    recipe: str
    shape: dict[str, Any]


@dataclass(frozen=True)
class _GuideAxes:
    """The fixed prototype frame carried by every derived guide.

    These are guide-space directions, not a public coordinate contract.  The
    current experiment intentionally admits only +Y-up, +Z-forward and the
    mirrored +/-X bilateral frame validated below.
    """

    lateral: tuple[float, float, float]
    up: tuple[float, float, float]
    forward: tuple[float, float, float]


@dataclass(frozen=True)
class _AxialStation:
    """One ordered source-owned axial station in the private form guide."""

    name: str
    center: tuple[float, float, float]
    radii: tuple[float, float, float]


@dataclass(frozen=True)
class _AxialTransition:
    """A short bridge between adjacent axial stations.

    The transitions are deliberately separate fields rather than one broad
    trunk fill.  They keep the waist visible while still making the three
    stations a connected guide for the disposable field adapter.
    """

    name: str
    centerline: tuple[tuple[float, float, float], tuple[float, float, float]]
    thickness: tuple[float, float]



@dataclass(frozen=True)
class _AxialGuide:
    """Regional axial controls derived directly from pelvis and torso source data."""

    owner: Descriptor
    girdle_center: tuple[float, float, float] | None
    girdle_radii: tuple[float, float, float] | None
    pelvic_core_center: tuple[float, float, float] | None
    pelvic_core_radii: tuple[float, float, float] | None
    chest_center: tuple[float, float, float] | None
    chest_radii: tuple[float, float, float] | None
    waist_center: tuple[float, float, float] | None
    waist_radii: tuple[float, float, float] | None
    trunk_centerline: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    trunk_thickness: tuple[float, float] | None
    stations: tuple[_AxialStation, ...]
    transitions: tuple[_AxialTransition, ...]
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance

    @property
    def station_controls(self) -> tuple[_AxialStation, ...]:
        return self.stations

    @property
    def transition_controls(self) -> tuple[_AxialTransition, ...]:
        return self.transitions

    @property
    def pelvic_station(self) -> _AxialStation | None:
        return next((station for station in self.stations if station.name == "pelvic-girdle"), None)

    @property
    def waist_station(self) -> _AxialStation | None:
        return next((station for station in self.stations if station.name == "waist"), None)

    @property
    def chest_station(self) -> _AxialStation | None:
        return next((station for station in self.stations if station.name == "chest-girdle"), None)


@dataclass(frozen=True)
class _TorsoCageSection:
    """One source-owned cross-section in the private torso cage prototype.

    The section is intentionally smaller than a surface primitive: it records
    the centre and two transverse radii that a later loft/field evaluator can
    consume.  Its orientation is inherited from the containing cage.
    """

    name: str
    section_index: int
    frame_index: int
    landmark_index: int
    owner: Descriptor
    frame: AuthoredFrame
    landmark: AuthoredLandmark
    center: tuple[float, float, float]
    lateral_radius: float
    anterior_radius: float
    posterior_radius: float
    depth_radius: float
    lateral_lineage: "_TorsoRadiusLineage"
    anterior_lineage: "_TorsoRadiusLineage"
    posterior_lineage: "_TorsoRadiusLineage"

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance


@dataclass(frozen=True)
class _TorsoRadiusLineage:
    """Exact source-to-guide lineage for one authored torso radius."""

    base: int
    factor: int
    scaled: int
    reference: tuple[tuple[str, tuple[str, ...], str, str], str]
    reference_index: int
    provenance: dict[str, Any]
    consumed_section: str


@dataclass(frozen=True)
class _TorsoCage:
    """Private ordered torso profile, derived without adding body parts."""

    pelvis_owner: Descriptor
    torso_owner: Descriptor
    sections: tuple[_TorsoCageSection, ...]
    axes: _GuideAxes

    @property
    def source_owners(self) -> tuple[Descriptor, Descriptor]:
        return (self.pelvis_owner, self.torso_owner)

    @property
    def source_keys(self) -> tuple[tuple[str, tuple[str, ...], str, str], ...]:
        return tuple(owner.key for owner in self.source_owners)

    def section(self, name: str) -> _TorsoCageSection:
        """Return a named cage control without exposing positional topology."""

        matches = tuple(section for section in self.sections if section.name == name)
        if len(matches) != 1:
            _fail(f"torso cage requires one named {name!r} section")
        return matches[0]

    @property
    def lower_boundary(self) -> _TorsoCageSection:
        return self.section("lower-pelvis")

    @property
    def upper_boundary(self) -> _TorsoCageSection:
        return self.section("upper-ribcage-shoulder")

    @property
    def upper_ribcage(self) -> _TorsoCageSection:
        return self.upper_boundary


@dataclass(frozen=True)
class _ShoulderCurve:
    """One private multi-control shoulder wrap owned by a source part."""

    name: str
    owner: Descriptor
    points: tuple[tuple[float, float, float], ...]
    profile: tuple[float, ...]
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance


@dataclass(frozen=True)
class _ShoulderSideGuide:
    """One bilateral shoulder frame side derived from authored controls."""

    side: str
    owner: Descriptor
    authored_frame: AuthoredFrame
    authored_peak: AuthoredLandmark
    authored_axilla: AuthoredLandmark
    peak_anchor: tuple[float, float, float]
    axilla_anchor: tuple[float, float, float]
    vertical_midpoint: float
    vertical_radius: float
    depth_radius: float
    depth_value_permille: int
    depth_scaled_permille: int
    depth_profile_factor: int
    depth_provenance: dict[str, Any]
    socket_anchor: tuple[float, float, float]
    shoulder_extremum: tuple[float, float, float]
    span: float
    slope: float
    anterior_support: _ShoulderCurve
    posterior_return: _ShoulderCurve
    deltoid_sweep: _ShoulderCurve
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance

    @property
    def authored_peak_anchor(self) -> tuple[float, float, float]:
        return self.peak_anchor

    @property
    def authored_axilla_anchor(self) -> tuple[float, float, float]:
        return self.axilla_anchor


@dataclass(frozen=True)
class _ShoulderFrame:
    """Private trapezius/shoulder frame for a later surface consumer.

    Its central anchor remains torso-owned, while its two socket anchors and
    deltoid controls remain upper-arm-owned.  The anterior/posterior support
    curves are private guide-only controls in this adapter; only the
    upper-arm-owned deltoid sweep, together with the separate torso-cage and
    root consumers, drives disposable analytic skin.  The adapter does not
    infer a second shoulder representation or restore the old round masses.
    """

    torso_owner: Descriptor
    neck_owner: Descriptor
    central_anchor: tuple[float, float, float]
    central_profile: tuple[float, float]
    sides: tuple[_ShoulderSideGuide, _ShoulderSideGuide]
    axes: _GuideAxes

    @property
    def source_owners(self) -> tuple[Descriptor, Descriptor, Descriptor, Descriptor]:
        return (self.torso_owner, self.neck_owner, self.sides[0].owner, self.sides[1].owner)

    @property
    def source_keys(self) -> tuple[tuple[str, tuple[str, ...], str, str], ...]:
        return tuple(owner.key for owner in self.source_owners)

    @property
    def left(self) -> _ShoulderSideGuide:
        return self.sides[0]

    @property
    def right(self) -> _ShoulderSideGuide:
        return self.sides[1]

    @property
    def authored_peak_anchors(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        return tuple(side.peak_anchor for side in self.sides)  # type: ignore[return-value]

    @property
    def authored_axilla_anchors(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        return tuple(side.axilla_anchor for side in self.sides)  # type: ignore[return-value]


@dataclass(frozen=True)
class _HeadNeckRadiusLineage:
    """Exact source-to-guide lineage for one authored head/neck radius."""

    base: int
    factor: int
    scaled: int
    reference: tuple[tuple[str, tuple[str, ...], str, str], str]
    reference_index: int
    provenance: dict[str, Any]
    consumed_section: str


@dataclass(frozen=True)
class _HeadNeckGuideSection:
    """One projected head/neck station retained in the regional guide."""

    name: str
    section_index: int
    source_section_index: int
    frame_index: int
    landmark_index: int
    owner: Descriptor
    frame: AuthoredFrame
    landmark: AuthoredLandmark
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    lateral_lineage: _HeadNeckRadiusLineage
    up_lineage: _HeadNeckRadiusLineage
    forward_lineage: _HeadNeckRadiusLineage

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key


@dataclass(frozen=True)
class _HeadNeckGuideConnection:
    """One authored connection with its direct guide path and thickness."""

    spec: HeadNeckConnection
    from_section: _HeadNeckGuideSection
    to_section: _HeadNeckGuideSection
    centerline: tuple[tuple[float, float, float], tuple[float, float, float]]
    thickness: tuple[float, float]


@dataclass(frozen=True)
class _HeadNeckProfileGuide:
    """Complete eight-station/seven-connection projected head/neck guide."""

    sections: tuple[_HeadNeckGuideSection, ...]
    connections: tuple[_HeadNeckGuideConnection, ...]
    provenance: dict[str, Any]
    axes: _GuideAxes


@dataclass(frozen=True)
class _HeadGuide:
    """Cranium/muzzle and neck-transition controls for the head region."""

    head_owner: Descriptor
    neck_owner: Descriptor
    profile: "_HeadNeckProfileGuide"
    cranium_center: tuple[float, float, float]
    cranium_radii: tuple[float, float, float]
    muzzle_center: tuple[float, float, float]
    muzzle_radii: tuple[float, float, float]
    head_transition: tuple[tuple[float, float, float], tuple[float, float, float]]
    head_transition_thickness: tuple[float, float]
    neck_transition: tuple[tuple[float, float, float], tuple[float, float, float]]
    neck_transition_thickness: tuple[float, float]
    neck_collar_center: tuple[float, float, float]
    neck_collar_radii: tuple[float, float, float]
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.head_owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.head_owner.provenance


@dataclass(frozen=True)
class _LimbGuide:
    """One source limb with named tapered sections and endpoint joint station."""

    owner: Descriptor
    sections: tuple[_LimbSection, ...]
    joint: _LimbJoint | None
    root_centerline: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    root_thickness: tuple[float, float] | None
    hip_centerline: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    hip_thickness: tuple[float, float] | None
    hip_center: tuple[float, float, float] | None
    hip_radii: tuple[float, float, float] | None
    shoulder_center: tuple[float, float, float] | None
    shoulder_radii: tuple[float, float, float] | None
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance

    @property
    def shoulder_girdle_center(self) -> tuple[float, float, float] | None:
        return self.shoulder_center

    @property
    def shoulder_girdle_radii(self) -> tuple[float, float, float] | None:
        return self.shoulder_radii

    @property
    def hip_girdle_center(self) -> tuple[float, float, float] | None:
        return self.hip_center

    @property
    def hip_girdle_radii(self) -> tuple[float, float, float] | None:
        return self.hip_radii

    @property
    def joint_center(self) -> tuple[float, float, float] | None:
        return None if self.joint is None else self.joint.center

    @property
    def joint_radii(self) -> tuple[float, float, float] | None:
        return None if self.joint is None else self.joint.radii

    @property
    def profile_controls(self) -> tuple[float, float, float]:
        """The three consumed radii at root, section break, and distal end."""
        if len(self.sections) != 2:
            return ()
        return (self.sections[0].thickness[0], self.sections[0].thickness[1], self.sections[1].thickness[1])


@dataclass(frozen=True)
class _FootChainGuide:
    """Private source-derived controls for one digitigrade foot chain.

    The source foot descriptor supplies proportions, but does not pretend to
    author a fixed anatomical mass layout.  The shin-owned hock is the
    proximal joint; this guide then derives the sloping metatarsal, a planted
    pad, a forward toe box, and a display-only contact datum.  The hock stays
    owned by the shin; this guide owns only the three foot fields that follow
    it.
    """

    hock_anchor: tuple[float, float, float]
    hock_radii: tuple[float, float, float]
    metatarsal_centerline: tuple[tuple[float, float, float], tuple[float, float, float]]
    metatarsal_profile: tuple[float, float]
    pad_center: tuple[float, float, float]
    pad_radii: tuple[float, float, float]
    toe_center: tuple[float, float, float]
    toe_radii: tuple[float, float, float]
    contact_height: float
    axes: _GuideAxes


@dataclass(frozen=True)
class _PawGuide:
    """Structured hand paw or source-derived digitigrade foot guide."""

    owner: Descriptor
    paw_center: tuple[float, float, float] | None
    paw_radii: tuple[float, float, float] | None
    foot_chain: _FootChainGuide | None
    attachment_centerline: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    attachment_radius: float | None
    attachment_kind: str | None
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance

@dataclass(frozen=True)
class _TailGuide:
    """Tail centerline and taper controls for one source tail descriptor."""

    owner: Descriptor
    centerline: tuple[tuple[float, float, float], tuple[float, float, float]]
    taper: tuple[float, float]
    extension_centerline: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    extension_taper: tuple[float, float] | None
    cap_center: tuple[float, float, float] | None
    cap_radii: tuple[float, float, float] | None
    root_attachment_centerline: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    root_attachment_taper: tuple[float, float] | None
    root_collar_center: tuple[float, float, float] | None
    root_collar_radii: tuple[float, float, float] | None
    axes: _GuideAxes

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance


@dataclass(frozen=True)
class _GuideTopology:
    """Stable source-owned topology and axes for one validated variant."""

    owner_keys: tuple[tuple[str, tuple[str, ...], str, str], ...]
    parent_edges: tuple[tuple[tuple[str, tuple[str, ...], str, str], tuple[str, tuple[str, ...], str, str]], ...]
    bilateral_pairs: tuple[tuple[tuple[str, tuple[str, ...], str, str], tuple[str, tuple[str, ...], str, str]], ...]
    axes: _GuideAxes


@dataclass(frozen=True)
class _HybridGuide:
    """Private regional guide graph derived from one fixed-form variant."""

    topology: _GuideTopology
    source_descriptors: tuple[Descriptor, ...]
    axial_guides: tuple[_AxialGuide, ...]
    torso_cage: _TorsoCage
    shoulder_frame: _ShoulderFrame
    head_guide: _HeadGuide
    limb_guides: tuple[_LimbGuide, ...]
    paw_guides: tuple[_PawGuide, ...]
    tail_guides: tuple[_TailGuide, ...]

    @property
    def source_owners(self) -> tuple[Descriptor, ...]:
        return self.source_descriptors

    @property
    def axial(self) -> tuple[_AxialGuide, ...]:
        return self.axial_guides

    @property
    def axial_stations(self) -> tuple[_AxialStation, ...]:
        return tuple(station for axial in self.axial_guides for station in axial.stations)

    @property
    def axial_transitions(self) -> tuple[_AxialTransition, ...]:
        return tuple(transition for axial in self.axial_guides for transition in axial.transitions)

    @property
    def torso_sections(self) -> tuple[_TorsoCageSection, ...]:
        return self.torso_cage.sections

    @property
    def shoulders(self) -> _ShoulderFrame:
        return self.shoulder_frame

    @property
    def limbs(self) -> tuple[_LimbGuide, ...]:
        return self.limb_guides

    @property
    def paws(self) -> tuple[_PawGuide, ...]:
        return self.paw_guides

    @property
    def head(self) -> _HeadGuide:
        return self.head_guide

    @property
    def tail(self) -> tuple[_TailGuide, ...]:
        return self.tail_guides


@dataclass(frozen=True)
class AuthoredFrame:
    """One source-authored identity-only control frame."""

    owner: tuple[str, tuple[str, ...], str, str]
    role: str
    translation: tuple[float, float, float]
    rotation_xyzw: tuple[float, float, float, float]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class AuthoredLandmark:
    """One source-local landmark bound to an authored control frame."""

    owner: tuple[str, tuple[str, ...], str, str]
    role: str
    frame: tuple[tuple[str, tuple[str, ...], str, str], str]
    position: tuple[float, float, float]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class AuthoredRadius:
    """One source-authored axial radius control in the torso profile."""

    owner: tuple[str, tuple[str, ...], str, str]
    role: str
    value_permille: int
    provenance: dict[str, Any]
    source_index: int


@dataclass(frozen=True)
class AuthoredTorsoSection:
    """One of the seven ordered source-authored torso profile sections."""

    name: str
    section_index: int
    frame_index: int
    landmark_index: int
    owner: tuple[str, tuple[str, ...], str, str]
    frame: tuple[tuple[str, tuple[str, ...], str, str], str]
    landmark: AuthoredLandmark
    lateral: AuthoredRadius
    anterior: AuthoredRadius
    posterior: AuthoredRadius


@dataclass(frozen=True)
class AuthoredTorsoProfile:
    """Validated authored_torso_profile v1 controls."""

    sections: tuple[AuthoredTorsoSection, ...]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class HeadNeckConnection:
    """One exact named connection in the authored head/neck profile."""

    name: str
    from_section_index: int
    to_section_index: int
    route: str


@dataclass(frozen=True)
class AuthoredHeadNeckSection:
    """One indexed source-authored head/neck profile station."""

    name: str
    section_index: int
    frame_index: int
    landmark_index: int
    owner: tuple[str, tuple[str, ...], str, str]
    frame: tuple[tuple[str, tuple[str, ...], str, str], str]
    landmark: AuthoredLandmark
    lateral: AuthoredRadius
    up: AuthoredRadius
    forward: AuthoredRadius


@dataclass(frozen=True)
class AuthoredHeadNeckProfile:
    """Validated authored_head_neck_profile v1 controls."""

    sections: tuple[AuthoredHeadNeckSection, ...]
    connections: tuple[HeadNeckConnection, ...]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class VariantTorsoProfileSection:
    """One producer-projected per-variant torso profile section."""

    source_section_index: int
    name: str
    position: tuple[float, float, float]
    lateral_radius_permille: int
    anterior_radius_permille: int
    posterior_radius_permille: int
    lateral_factor: int
    anterior_factor: int
    posterior_factor: int
    provenance: dict[str, Any]


@dataclass(frozen=True)
class VariantTorsoProfile:
    sections: tuple[VariantTorsoProfileSection, ...]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class VariantHeadNeckProfileSection:
    """One producer-projected per-variant head/neck profile station."""

    source_section_index: int
    name: str
    position: tuple[float, float, float]
    lateral_radius_permille: int
    up_radius_permille: int
    forward_radius_permille: int
    lateral_factor: int
    up_factor: int
    forward_factor: int
    provenance: dict[str, Any]


@dataclass(frozen=True)
class VariantHeadNeckProfile:
    sections: tuple[VariantHeadNeckProfileSection, ...]
    connections: tuple[HeadNeckConnection, ...]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class Form:
    raw: dict[str, Any]
    source: dict[str, Any]
    reference_scale: float
    reference_scale_raw: dict[str, Any]
    authored_dimensions: tuple[tuple[tuple[str, tuple[str, ...], str, str], str, int, dict[str, Any]], ...]
    authored_landmarks: tuple[AuthoredLandmark, ...]
    authored_frames: tuple[AuthoredFrame, ...]
    authored_torso_profile: AuthoredTorsoProfile
    authored_head_neck_profile: AuthoredHeadNeckProfile
    variant_torso_profiles: tuple[VariantTorsoProfile, ...]
    variant_head_neck_profiles: tuple[VariantHeadNeckProfile, ...]
    variants: tuple[tuple[str, tuple[Descriptor, ...], dict[str, Any]], ...]


def _authored_torso_provenance(value: Any, expected: dict[str, str], where: str) -> dict[str, Any]:
    provenance = _obj(value, where)
    if set(provenance) != {"source", "document", "namespace"} or provenance != expected:
        _fail(f"{where} is invalid")
    return provenance


def _parse_authored_torso_profile(
    value: Any,
    source: dict[str, Any],
    dimensions: tuple[tuple[tuple[str, tuple[str, ...], str, str], str, int, dict[str, Any]], ...],
    landmarks: tuple[AuthoredLandmark, ...],
    frames: tuple[AuthoredFrame, ...],
) -> AuthoredTorsoProfile:
    """Validate the exact index-bound authored_torso_profile v1 slice."""

    profile = _obj(value, "authored_torso_profile")
    required = {"format", "provenance", "sections"}
    if set(profile) != required or profile["format"] != AUTHORED_TORSO_PROFILE_FORMAT:
        _fail("authored_torso_profile is not format v1")
    source_provenance = {"source": "source-authored", "document": source["document"], "namespace": source["namespace"]}
    provenance = _authored_torso_provenance(profile["provenance"], source_provenance, "authored_torso_profile.provenance")
    raw_sections = _array(profile["sections"], "authored_torso_profile.sections")
    if len(raw_sections) != len(TORSO_PROFILE_SECTION_NAMES):
        _fail("authored_torso_profile.sections must contain exactly seven sections")
    expected_owner_roles = ("pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso")
    parsed: list[AuthoredTorsoSection] = []
    for index, raw in enumerate(raw_sections):
        where = f"authored_torso_profile.sections[{index}]"
        section = _obj(raw, where)
        expected_fields = {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}
        if set(section) != expected_fields:
            _fail(f"{where} has unexpected fields")
        if section["section_index"] != index or section["name"] != TORSO_PROFILE_SECTION_NAMES[index]:
            _fail(f"{where} is not the required ordered section")
        frame_index = _int(section["frame_index"], f"{where}.frame_index")
        landmark_index = _int(section["landmark_index"], f"{where}.landmark_index")
        if not 0 <= frame_index < len(frames) or not 0 <= landmark_index < len(landmarks):
            _fail(f"{where} references an out-of-range authored control")
        owner_role = expected_owner_roles[index]
        landmark = landmarks[landmark_index]
        frame = frames[frame_index]
        expected_owner = (source["namespace"], (), "part", owner_role)
        expected_landmark_role = TORSO_PROFILE_LANDMARK_PREFIX + section["name"].replace("-", "_")
        if landmark.owner != expected_owner or landmark.role != expected_landmark_role:
            _fail(f"{where}.landmark_index does not retain the exact owner/landmark role")
        if frame.owner != expected_owner or frame.role != TORSO_PROFILE_FRAME_ROLE:
            _fail(f"{where}.frame_index does not retain the exact owner/frame role")
        if landmark.frame != (frame.owner, frame.role):
            _fail(f"{where} landmark/frame binding is invalid")
        indices = _obj(section["dimension_indices"], f"{where}.dimension_indices")
        if set(indices) != {"lateral", "anterior", "posterior"}:
            _fail(f"{where}.dimension_indices has unexpected fields")
        controls: list[AuthoredRadius] = []
        expected_roles = tuple(TORSO_PROFILE_DIMENSION_PREFIX + section["name"].replace("-", "_") + "_" + suffix for suffix in TORSO_PROFILE_DIMENSION_SUFFIXES)
        for axis, expected_role in zip(("lateral", "anterior", "posterior"), expected_roles):
            dimension_index = _int(indices[axis], f"{where}.dimension_indices.{axis}")
            if not 0 <= dimension_index < len(dimensions):
                _fail(f"{where}.dimension_indices.{axis} is out of range")
            owner, role, value_permille, control_provenance = dimensions[dimension_index]
            if (owner, role) != (expected_owner, expected_role):
                _fail(f"{where}.dimension_indices.{axis} does not retain the exact owner/role")
            controls.append(AuthoredRadius(owner, role, value_permille, control_provenance, dimension_index))
        _authored_torso_provenance(section["provenance"], source_provenance, f"{where}.provenance")
        parsed.append(
            AuthoredTorsoSection(
                section["name"],
                index,
                frame_index,
                landmark_index,
                expected_owner,
                (frame.owner, frame.role),
                landmark,
                controls[0],
                controls[1],
                controls[2],
            )
        )
    _validate_regional_route_order(
        tuple(section.landmark.position for section in parsed),
        REGIONAL_ROUTE_ORDER_TORSO,
        "authored_torso_profile.sections",
    )
    return AuthoredTorsoProfile(tuple(parsed), provenance)


def _parse_head_neck_connections(value: Any, where: str) -> tuple[HeadNeckConnection, ...]:
    raw_connections = _array(value, where)
    if len(raw_connections) != len(HEAD_NECK_PROFILE_CONNECTIONS):
        _fail(f"{where} must contain exactly seven connections")
    parsed: list[HeadNeckConnection] = []
    for index, (expected_name, expected_from, expected_to, expected_route) in enumerate(HEAD_NECK_PROFILE_CONNECTIONS):
        connection_where = f"{where}[{index}]"
        connection = _obj(raw_connections[index], connection_where)
        if set(connection) != {"name", "from_section_index", "to_section_index", "route"}:
            _fail(f"{connection_where} has unexpected fields")
        from_section_index = _int(connection["from_section_index"], f"{connection_where}.from_section_index")
        to_section_index = _int(connection["to_section_index"], f"{connection_where}.to_section_index")
        if (connection["name"], from_section_index, to_section_index, connection["route"]) != (
            expected_name,
            expected_from,
            expected_to,
            expected_route,
        ):
            _fail(f"{connection_where} is not the required ordered named route")
        parsed.append(HeadNeckConnection(expected_name, expected_from, expected_to, expected_route))
    return tuple(parsed)


def _parse_authored_head_neck_profile(
    value: Any,
    source: dict[str, Any],
    dimensions: tuple[tuple[tuple[str, tuple[str, ...], str, str], str, int, dict[str, Any]], ...],
    landmarks: tuple[AuthoredLandmark, ...],
    frames: tuple[AuthoredFrame, ...],
) -> AuthoredHeadNeckProfile:
    """Validate the exact index-bound authored_head_neck_profile v1 slice."""

    profile = _obj(value, "authored_head_neck_profile")
    if set(profile) != {"format", "provenance", "sections", "connections"} or profile["format"] != AUTHORED_HEAD_NECK_PROFILE_FORMAT:
        _fail("authored_head_neck_profile is not format v1")
    source_provenance = {"source": "source-authored", "document": source["document"], "namespace": source["namespace"]}
    provenance = _authored_torso_provenance(profile["provenance"], source_provenance, "authored_head_neck_profile.provenance")
    raw_sections = _array(profile["sections"], "authored_head_neck_profile.sections")
    if len(raw_sections) != len(HEAD_NECK_PROFILE_SECTION_NAMES):
        _fail("authored_head_neck_profile.sections must contain exactly eight sections")
    parsed: list[AuthoredHeadNeckSection] = []
    expected_owner_roles = HEAD_NECK_PROFILE_OWNER_ROLES
    for index, raw in enumerate(raw_sections):
        where = f"authored_head_neck_profile.sections[{index}]"
        section = _obj(raw, where)
        expected_fields = {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}
        if set(section) != expected_fields:
            _fail(f"{where} has unexpected fields")
        if section["section_index"] != index or section["name"] != HEAD_NECK_PROFILE_SECTION_NAMES[index]:
            _fail(f"{where} is not the required ordered section")
        frame_index = _int(section["frame_index"], f"{where}.frame_index")
        landmark_index = _int(section["landmark_index"], f"{where}.landmark_index")
        if not 0 <= frame_index < len(frames) or not 0 <= landmark_index < len(landmarks):
            _fail(f"{where} references an out-of-range authored control")
        owner = (source["namespace"], (), "part", expected_owner_roles[index])
        landmark = landmarks[landmark_index]
        frame = frames[frame_index]
        expected_landmark_role = HEAD_NECK_PROFILE_LANDMARK_PREFIX + section["name"].replace("-", "_")
        if landmark.owner != owner or landmark.role != expected_landmark_role:
            _fail(f"{where}.landmark_index does not retain the exact owner/landmark role")
        if frame.owner != owner or frame.role != HEAD_NECK_PROFILE_FRAME_ROLE:
            _fail(f"{where}.frame_index does not retain the exact owner/frame role")
        if landmark.frame != (frame.owner, frame.role):
            _fail(f"{where} landmark/frame binding is invalid")
        indices = _obj(section["dimension_indices"], f"{where}.dimension_indices")
        if set(indices) != set(HEAD_NECK_PROFILE_DIMENSION_SUFFIXES[i].removesuffix("_radius") for i in range(3)):
            _fail(f"{where}.dimension_indices has unexpected fields")
        controls: list[AuthoredRadius] = []
        expected_roles = tuple(
            HEAD_NECK_PROFILE_DIMENSION_PREFIX + section["name"].replace("-", "_") + "_" + suffix
            for suffix in HEAD_NECK_PROFILE_DIMENSION_SUFFIXES
        )
        for axis, expected_role in zip(("lateral", "up", "forward"), expected_roles):
            dimension_index = _int(indices[axis], f"{where}.dimension_indices.{axis}")
            if not 0 <= dimension_index < len(dimensions):
                _fail(f"{where}.dimension_indices.{axis} is out of range")
            dimension_owner, role, value_permille, control_provenance = dimensions[dimension_index]
            if (dimension_owner, role) != (owner, expected_role):
                _fail(f"{where}.dimension_indices.{axis} does not retain the exact owner/role")
            controls.append(AuthoredRadius(dimension_owner, role, value_permille, control_provenance, dimension_index))
        _authored_torso_provenance(section["provenance"], source_provenance, f"{where}.provenance")
        parsed.append(
            AuthoredHeadNeckSection(
                section["name"],
                index,
                frame_index,
                landmark_index,
                owner,
                (frame.owner, frame.role),
                landmark,
                controls[0],
                controls[1],
                controls[2],
            )
        )
    _validate_regional_route_order(
        tuple(section.landmark.position for section in parsed),
        REGIONAL_ROUTE_ORDER_AUTHORED_HEAD_NECK,
        "authored_head_neck_profile.sections",
    )
    return AuthoredHeadNeckProfile(
        tuple(parsed),
        _parse_head_neck_connections(profile["connections"], "authored_head_neck_profile.connections"),
        provenance,
    )


def _torso_profile_factors(profile_id: str, owner_role: str) -> tuple[int, int]:
    shared = _display_factors(profile_id, owner_role, "ellipsoid")
    return shared[0], shared[2]


def _head_neck_profile_factors(profile_id: str, owner_role: str) -> tuple[int, int, int]:
    if owner_role == "head":
        return _display_factors(profile_id, owner_role, "ellipsoid")
    if owner_role == "neck":
        factor = _display_factors(profile_id, owner_role, "capsule")[0]
        return (factor, factor, factor)
    _fail(f"unsupported head/neck profile owner role: {owner_role}")


def _parse_variant_torso_profile(
    value: Any,
    source: dict[str, Any],
    authored: AuthoredTorsoProfile,
    profile_id: str,
) -> VariantTorsoProfile:
    profile = _obj(value, f"{profile_id}.torso_profile")
    if set(profile) != {"format", "source", "provenance", "sections"} or profile["format"] != AUTHORED_TORSO_PROFILE_FORMAT or profile["source"] != "authored_torso_profile":
        _fail(f"{profile_id}.torso_profile is invalid")
    expected_provenance = {"source": "source-authored", "document": source["document"], "namespace": source["namespace"]}
    provenance = _authored_torso_provenance(profile["provenance"], expected_provenance, f"{profile_id}.torso_profile.provenance")
    raw_sections = _array(profile["sections"], f"{profile_id}.torso_profile.sections")
    if len(raw_sections) != len(authored.sections):
        _fail(f"{profile_id}.torso_profile must contain exactly seven sections")
    parsed: list[VariantTorsoProfileSection] = []
    for index, raw in enumerate(raw_sections):
        where = f"{profile_id}.torso_profile.sections[{index}]"
        section = _obj(raw, where)
        expected_fields = {"source_section_index", "name", "position", "lateral_radius_permille", "anterior_radius_permille", "posterior_radius_permille", "scaling", "provenance"}
        if set(section) != expected_fields or section["source_section_index"] != index or section["name"] != authored.sections[index].name:
            _fail(f"{where} is not the required ordered section")
        position = _source_vector(section["position"], f"{where}.position", 3)
        if position != authored.sections[index].landmark.position:
            _fail(f"{where}.position is not the source-authored landmark position")
        scaling = _obj(section["scaling"], f"{where}.scaling")
        if set(scaling) != {"lateral_factor_permille", "anterior_factor_permille", "posterior_factor_permille"}:
            _fail(f"{where}.scaling has unexpected fields")
        lateral_factor = _int(scaling["lateral_factor_permille"], f"{where}.scaling.lateral_factor_permille")
        anterior_factor = _int(scaling["anterior_factor_permille"], f"{where}.scaling.anterior_factor_permille")
        posterior_factor = _int(scaling["posterior_factor_permille"], f"{where}.scaling.posterior_factor_permille")
        expected_lateral, expected_depth = _torso_profile_factors(profile_id, authored.sections[index].owner[3])
        if (lateral_factor, anterior_factor, posterior_factor) != (expected_lateral, expected_depth, expected_depth):
            _fail(f"{where}.scaling does not use the shared torso variant factors")
        scaled: list[int] = []
        for field, control, factor in (
            ("lateral_radius_permille", authored.sections[index].lateral, lateral_factor),
            ("anterior_radius_permille", authored.sections[index].anterior, anterior_factor),
            ("posterior_radius_permille", authored.sections[index].posterior, posterior_factor),
        ):
            scaled_value = _int(section[field], f"{where}.{field}")
            if scaled_value != _scaled_display_value(control.value_permille, factor, f"{where}.{field}"):
                _fail(f"{where}.{field} is not the exact scaled authored radius")
            scaled.append(scaled_value)
        _authored_torso_provenance(section["provenance"], expected_provenance, f"{where}.provenance")
        parsed.append(VariantTorsoProfileSection(index, section["name"], position, scaled[0], scaled[1], scaled[2], lateral_factor, anterior_factor, posterior_factor, provenance))
    return VariantTorsoProfile(tuple(parsed), provenance)


def _parse_variant_head_neck_profile(
    value: Any,
    source: dict[str, Any],
    authored: AuthoredHeadNeckProfile,
    profile_id: str,
) -> VariantHeadNeckProfile:
    profile = _obj(value, f"{profile_id}.head_neck_profile")
    if set(profile) != {"format", "source", "provenance", "sections", "connections"} or profile["format"] != AUTHORED_HEAD_NECK_PROFILE_FORMAT or profile["source"] != "authored_head_neck_profile":
        _fail(f"{profile_id}.head_neck_profile is invalid")
    expected_provenance = {"source": "source-authored", "document": source["document"], "namespace": source["namespace"]}
    provenance = _authored_torso_provenance(profile["provenance"], expected_provenance, f"{profile_id}.head_neck_profile.provenance")
    raw_sections = _array(profile["sections"], f"{profile_id}.head_neck_profile.sections")
    if len(raw_sections) != len(authored.sections):
        _fail(f"{profile_id}.head_neck_profile must contain exactly eight sections")
    parsed: list[VariantHeadNeckProfileSection] = []
    for index, raw in enumerate(raw_sections):
        where = f"{profile_id}.head_neck_profile.sections[{index}]"
        section = _obj(raw, where)
        expected_fields = {
            "source_section_index", "name", "position", "lateral_radius_permille", "up_radius_permille",
            "forward_radius_permille", "scaling", "provenance",
        }
        if set(section) != expected_fields or section["source_section_index"] != index or section["name"] != authored.sections[index].name:
            _fail(f"{where} is not the required ordered section")
        position = _source_vector(section["position"], f"{where}.position", 3)
        if position != authored.sections[index].landmark.position:
            _fail(f"{where}.position is not the source-authored landmark position")
        scaling = _obj(section["scaling"], f"{where}.scaling")
        if set(scaling) != {"lateral_factor_permille", "up_factor_permille", "forward_factor_permille"}:
            _fail(f"{where}.scaling has unexpected fields")
        factors = tuple(
            _int(scaling[f"{axis}_factor_permille"], f"{where}.scaling.{axis}_factor_permille")
            for axis in ("lateral", "up", "forward")
        )
        expected_factors = _head_neck_profile_factors(profile_id, authored.sections[index].owner[3])
        if factors != expected_factors:
            _fail(f"{where}.scaling does not use the producer head/neck variant factors")
        scaled: list[int] = []
        for axis, field, control, factor in (
            ("lateral", "lateral_radius_permille", authored.sections[index].lateral, factors[0]),
            ("up", "up_radius_permille", authored.sections[index].up, factors[1]),
            ("forward", "forward_radius_permille", authored.sections[index].forward, factors[2]),
        ):
            scaled_value = _int(section[field], f"{where}.{field}")
            if scaled_value != _scaled_display_value(control.value_permille, factor, f"{where}.{field}"):
                _fail(f"{where}.{field} is not the exact scaled authored radius")
            scaled.append(scaled_value)
        _authored_torso_provenance(section["provenance"], expected_provenance, f"{where}.provenance")
        parsed.append(
            VariantHeadNeckProfileSection(
                index,
                section["name"],
                position,
                scaled[0],
                scaled[1],
                scaled[2],
                factors[0],
                factors[1],
                factors[2],
                provenance,
            )
        )
    _validate_regional_route_order(
        tuple(section.position for section in parsed),
        REGIONAL_ROUTE_ORDER_AUTHORED_HEAD_NECK,
        f"{profile_id}.head_neck_profile.sections",
    )
    connections = _parse_head_neck_connections(profile["connections"], f"{profile_id}.head_neck_profile.connections")
    if connections != authored.connections:
        _fail(f"{profile_id}.head_neck_profile.connections do not retain the authored topology")
    return VariantHeadNeckProfile(tuple(parsed), connections, provenance)


def validate_envelope(value: Any) -> Form:
    root = _obj(value, "envelope")
    required = {"format", "operation", "status", "stage", "processing_complete", "diagnostics_complete", "diagnostics", "source", "reference_scale", "authored_dimensions", "authored_landmarks", "authored_frames", "authored_torso_profile", "authored_head_neck_profile", "variants", "limitations"}
    if set(root) != required:
        _fail("envelope has unexpected or missing fields")
    if root["format"] != SOURCE_FORMAT or root["operation"] != "inspect-provisional-form" or root["status"] != "success" or root["stage"] != "provisional-form":
        _fail("envelope is not a successful v8 provisional-form result")
    if root["processing_complete"] is not True or root["diagnostics_complete"] is not True or root["diagnostics"] != []:
        _fail("envelope success flags or diagnostics are invalid")
    if type(root["limitations"]) is not str or "Readiness" not in root["limitations"] or "geometry" not in root["limitations"]:
        _fail("envelope limitations do not state the exploratory boundary")
    source = _obj(root["source"], "source")
    if set(source) != {"document", "namespace", "resource_profile_id"} or any(type(source[x]) is not str for x in source):
        _fail("source is invalid")
    if source["resource_profile_id"] != "ck.resource.body.r2":
        _fail("unsupported resource profile")
    authored_dimensions = _array(root["authored_dimensions"], "authored_dimensions")
    if not authored_dimensions or len(authored_dimensions) > MAX_AUTHORED_DIMENSIONS:
        _fail("authored_dimensions count is invalid")
    parsed_dimensions: list[tuple[tuple[str, tuple[str, ...], str, str], str, int, dict[str, Any]]] = []
    for index, item in enumerate(authored_dimensions):
        dimension = _obj(item, f"authored_dimensions[{index}]")
        if set(dimension) != {"owner", "role", "value_permille", "provenance"}:
            _fail(f"authored_dimensions[{index}] has invalid fields")
        owner = _address(dimension["owner"], f"authored_dimensions[{index}].owner")
        if owner[0] != source["namespace"] or owner[2] != "part":
            _fail(f"authored_dimensions[{index}].owner is invalid")
        role = dimension["role"]
        if type(role) is not str or not role:
            _fail(f"authored_dimensions[{index}].role is invalid")
        value_permille = _int(dimension["value_permille"], f"authored_dimensions[{index}].value_permille")
        if not 0 < value_permille <= 5000:
            _fail(f"authored_dimensions[{index}].value_permille is outside 1..5000")
        provenance = _obj(dimension["provenance"], f"authored_dimensions[{index}].provenance")
        if set(provenance) != {"source", "document", "namespace"} or provenance != {"source": "source-authored", "document": source["document"], "namespace": source["namespace"]}:
            _fail(f"authored_dimensions[{index}].provenance is invalid")
        parsed_dimensions.append((owner, role, value_permille, provenance))
    if parsed_dimensions != sorted(parsed_dimensions, key=lambda item: (item[0], item[1])):
        _fail("authored_dimensions are not stable owner/role order")
    dimension_keys = {(owner, role) for owner, role, _, _ in parsed_dimensions}
    if len(dimension_keys) != len(parsed_dimensions):
        _fail("authored_dimensions contain duplicates")
    dimension_values = {
        (owner, role): value for owner, role, value, _ in parsed_dimensions
    }

    control_provenance = {
        "source": "source-authored",
        "document": source["document"],
        "namespace": source["namespace"],
    }
    authored_frames = _array(root["authored_frames"], "authored_frames")
    if len(authored_frames) != 6 or len(authored_frames) > MAX_AUTHORED_FRAMES:
        _fail("authored_frames must contain exactly six controls")
    parsed_frames: list[AuthoredFrame] = []
    frame_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    for index, item in enumerate(authored_frames):
        frame = _obj(item, f"authored_frames[{index}]")
        if set(frame) != {"owner", "role", "transform", "provenance"}:
            _fail(f"authored_frames[{index}] has invalid fields")
        owner = _address(frame["owner"], f"authored_frames[{index}].owner")
        if owner[0] != source["namespace"] or owner[2] != "part" or owner[1] not in ((), ("left",), ("right",)) or owner[3] not in {"head", "neck", "pelvis", "torso", "upper_arm"}:
            _fail(f"authored_frames[{index}].owner is not a supported authored-control owner")
        role = frame["role"]
        if role not in {"form_shoulder_control", TORSO_PROFILE_FRAME_ROLE, HEAD_NECK_PROFILE_FRAME_ROLE}:
            _fail(f"authored_frames[{index}].role is invalid")
        if role == "form_shoulder_control" and owner[1] not in (("left",), ("right",)):
            _fail(f"authored_frames[{index}] shoulder frame owner is invalid")
        if role == TORSO_PROFILE_FRAME_ROLE and (owner[1] != () or owner[3] not in {"pelvis", "torso"}):
            _fail(f"authored_frames[{index}] torso profile frame owner is invalid")
        if role == HEAD_NECK_PROFILE_FRAME_ROLE and (owner[1] != () or owner[3] not in {"head", "neck"}):
            _fail(f"authored_frames[{index}] head/neck profile frame owner is invalid")
        provenance = _obj(frame["provenance"], f"authored_frames[{index}].provenance")
        if set(provenance) != set(control_provenance) or provenance != control_provenance:
            _fail(f"authored_frames[{index}].provenance is invalid")
        transform = _obj(frame["transform"], f"authored_frames[{index}].transform")
        if set(transform) != {"translation", "rotation_xyzw"}:
            _fail(f"authored_frames[{index}].transform has invalid fields")
        translation = _source_vector(transform["translation"], f"authored_frames[{index}].transform.translation", 3)
        rotation = _source_vector(transform["rotation_xyzw"], f"authored_frames[{index}].transform.rotation_xyzw", 4)
        if translation != (0.0, 0.0, 0.0) or rotation != (0.0, 0.0, 0.0, 1.0):
            _fail(f"authored_frames[{index}] must be an identity control frame")
        key = (owner, role)
        if key in frame_keys:
            _fail("authored_frames contain duplicates")
        frame_keys.append(key)
        parsed_frames.append(AuthoredFrame(owner, role, translation, rotation, provenance))
    if frame_keys != sorted(frame_keys):
        _fail("authored_frames are not stable owner/role order")
    expected_frame_keys = [
        ((source["namespace"], (), "part", "head"), HEAD_NECK_PROFILE_FRAME_ROLE),
        ((source["namespace"], (), "part", "neck"), HEAD_NECK_PROFILE_FRAME_ROLE),
        ((source["namespace"], (), "part", "pelvis"), TORSO_PROFILE_FRAME_ROLE),
        ((source["namespace"], (), "part", "torso"), TORSO_PROFILE_FRAME_ROLE),
        ((source["namespace"], ("left",), "part", "upper_arm"), "form_shoulder_control"),
        ((source["namespace"], ("right",), "part", "upper_arm"), "form_shoulder_control"),
    ]
    if frame_keys != expected_frame_keys:
        _fail("authored_frames do not have the closed shoulder-and-torso control inventory")

    authored_landmarks = _array(root["authored_landmarks"], "authored_landmarks")
    if len(authored_landmarks) != 19 or len(authored_landmarks) > MAX_AUTHORED_LANDMARKS:
        _fail("authored_landmarks must contain exactly nineteen controls")
    parsed_landmarks: list[AuthoredLandmark] = []
    landmark_keys: list[tuple[tuple[str, tuple[str, ...], str, str], str]] = []
    for index, item in enumerate(authored_landmarks):
        landmark = _obj(item, f"authored_landmarks[{index}]")
        if set(landmark) != {"owner", "role", "frame", "position", "provenance"}:
            _fail(f"authored_landmarks[{index}] has invalid fields")
        owner = _address(landmark["owner"], f"authored_landmarks[{index}].owner")
        if owner[0] != source["namespace"] or owner[2] != "part" or owner[1] not in ((), ("left",), ("right",)) or owner[3] not in {"head", "neck", "pelvis", "torso", "upper_arm"}:
            _fail(f"authored_landmarks[{index}].owner is not a supported authored-control owner")
        role = landmark["role"]
        if role not in {"form_shoulder_peak", "form_axilla"} and not role.startswith(TORSO_PROFILE_LANDMARK_PREFIX) and not role.startswith(HEAD_NECK_PROFILE_LANDMARK_PREFIX):
            _fail(f"authored_landmarks[{index}].role is invalid")
        frame = _obj(landmark["frame"], f"authored_landmarks[{index}].frame")
        if set(frame) != {"owner", "role"}:
            _fail(f"authored_landmarks[{index}].frame has invalid fields")
        frame_owner = _address(frame["owner"], f"authored_landmarks[{index}].frame.owner")
        frame_role = frame["role"]
        if frame_role not in {"form_shoulder_control", TORSO_PROFILE_FRAME_ROLE, HEAD_NECK_PROFILE_FRAME_ROLE} or (frame_owner, frame_role) != (owner, frame_role):
            _fail(f"authored_landmarks[{index}] must reference its same-owner control frame")
        if (frame_owner, frame_role) not in frame_keys:
            _fail(f"authored_landmarks[{index}] references a missing control frame")
        position = _source_vector(landmark["position"], f"authored_landmarks[{index}].position", 3)
        if role.startswith(TORSO_PROFILE_LANDMARK_PREFIX) and (owner[1] != () or owner[3] not in {"pelvis", "torso"} or position[0] != 0.0 or position[2] != 0.0):
            _fail(f"authored_landmarks[{index}] torso profile landmark must be axial and unanchored")
        if role.startswith(HEAD_NECK_PROFILE_LANDMARK_PREFIX) and (owner[1] != () or owner[3] not in {"head", "neck"} or position[0] != 0.0):
            _fail(f"authored_landmarks[{index}] head/neck profile landmark must be unanchored with zero lateral position")
        provenance = _obj(landmark["provenance"], f"authored_landmarks[{index}].provenance")
        if set(provenance) != set(control_provenance) or provenance != control_provenance:
            _fail(f"authored_landmarks[{index}].provenance is invalid")
        key = (owner, role)
        if key in landmark_keys:
            _fail("authored_landmarks contain duplicates")
        landmark_keys.append(key)
        parsed_landmarks.append(AuthoredLandmark(owner, role, (frame_owner, frame_role), position, provenance))
    if landmark_keys != sorted(landmark_keys):
        _fail("authored_landmarks are not stable owner/role order")
    expected_landmark_keys = [
        ((source["namespace"], (), "part", "pelvis"), TORSO_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))
        for name in TORSO_PROFILE_SECTION_NAMES[:2]
    ] + [
        ((source["namespace"], (), "part", "torso"), TORSO_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))
        for name in TORSO_PROFILE_SECTION_NAMES[2:]
    ] + [
        ((source["namespace"], (), "part", owner_role), HEAD_NECK_PROFILE_LANDMARK_PREFIX + name.replace("-", "_"))
        for name, owner_role in zip(HEAD_NECK_PROFILE_SECTION_NAMES, HEAD_NECK_PROFILE_OWNER_ROLES)
    ] + [
        ((source["namespace"], (side,), "part", "upper_arm"), role)
        for side in ("left", "right")
        for role in ("form_axilla", "form_shoulder_peak")
    ]
    expected_landmark_keys.sort()
    if landmark_keys != expected_landmark_keys:
        _fail("authored_landmarks do not have the closed shoulder-and-torso control inventory")
    scale = _obj(root["reference_scale"], "reference_scale")
    if set(scale) != {"parent", "child", "axis_delta", "squared_length", "source"} or scale["source"] != "exact-containment-edge":
        _fail("reference_scale is invalid")
    parent_key = _address(scale["parent"], "reference_scale.parent")
    child_key = _address(scale["child"], "reference_scale.child")
    delta = _vector(scale["axis_delta"], "reference_scale.axis_delta")
    squared = _int(scale["squared_length"], "reference_scale.squared_length")
    if squared <= 0 or squared != sum(x * x for x in delta) or parent_key == child_key:
        _fail("reference_scale arithmetic is invalid")
    reference_scale = math.sqrt(float(squared))
    authored_torso_profile = _parse_authored_torso_profile(
        root["authored_torso_profile"],
        source,
        tuple(parsed_dimensions),
        tuple(parsed_landmarks),
        tuple(parsed_frames),
    )
    authored_head_neck_profile = _parse_authored_head_neck_profile(
        root["authored_head_neck_profile"],
        source,
        tuple(parsed_dimensions),
        tuple(parsed_landmarks),
        tuple(parsed_frames),
    )
    variants = _array(root["variants"], "variants")
    if len(variants) != 4:
        _fail("variants must contain exactly four items")
    normalized: list[tuple[str, tuple[Descriptor, ...], dict[str, Any]]] = []
    variant_torso_profiles: list[VariantTorsoProfile] = []
    variant_head_neck_profiles: list[VariantHeadNeckProfile] = []
    canonical: list[tuple[Any, ...]] | None = None
    consumed_dimension_keys: set[tuple[tuple[str, tuple[str, ...], str, str], str]] = set()
    for index, item in enumerate(variants):
        variant = _obj(item, f"variants[{index}]")
        if set(variant) != {"id", "profile_id", "provenance", "descriptors", "torso_profile", "head_neck_profile"} or variant.get("id") != VARIANT_IDS[index] or variant.get("profile_id") != VARIANT_IDS[index]:
            _fail(f"variants[{index}] is not the fixed {VARIANT_IDS[index]} variant")
        provenance = _obj(variant["provenance"], f"variants[{index}].provenance")
        if set(provenance) != {"source", "resource_profile_id", "shape_basis"} or provenance.get("source") != "profile-derived-display" or provenance.get("resource_profile_id") != source["resource_profile_id"] or provenance.get("shape_basis") != "source-authored-dimensions-plus-fixed-display-factor":
            _fail(f"variants[{index}].provenance is invalid")
        descriptors = _array(variant["descriptors"], f"variants[{index}].descriptors")
        if not descriptors or len(descriptors) > MAX_DESCRIPTORS:
            _fail(f"variants[{index}].descriptors count is invalid")
        parsed: list[Descriptor] = []
        keys: list[tuple[str, tuple[str, ...], str, str]] = []
        for di, raw_item in enumerate(descriptors):
            raw = _obj(raw_item, f"variants[{index}].descriptors[{di}]")
            expected = {"descriptor_kind", "address", "parent", "placement_source", "reference_point", "dimension_roles", "profile_id", "source", "provenance", "shape"}
            if set(raw) != expected or raw.get("descriptor_kind") != "display-only-form-descriptor":
                _fail(f"descriptor {index}/{di} has invalid fields")
            key = _address(raw["address"], f"descriptor {index}/{di}.address")
            if key[0] != source["namespace"] or key in keys:
                _fail(f"descriptor {index}/{di} has invalid or duplicate address")
            keys.append(key)
            parent = None if raw["parent"] is None else _address(raw["parent"], f"descriptor {index}/{di}.parent")
            if parent is not None and parent[0] != source["namespace"]:
                _fail(f"descriptor {index}/{di}.parent namespace differs")
            placement = raw["placement_source"]
            if placement not in {"authored-root", "authored-containment", "authored-attachment"}:
                _fail(f"descriptor {index}/{di}.placement_source is invalid")
            if (placement == "authored-root") != (parent is None):
                _fail(f"descriptor {index}/{di} root/parent relationship is invalid")
            if raw["profile_id"] != VARIANT_IDS[index] or raw["source"] != "profile-derived-display":
                _fail(f"descriptor {index}/{di} provenance is invalid")
            descriptor_provenance = _obj(raw["provenance"], f"descriptor {index}/{di}.provenance")
            if set(descriptor_provenance) != {"source", "resource_profile_id", "shape_basis"} or descriptor_provenance != provenance:
                _fail(f"descriptor {index}/{di}.provenance is invalid")
            point = _vector(raw["reference_point"], f"descriptor {index}/{di}.reference_point")
            shape = _shape(raw["shape"], f"descriptor {index}/{di}.shape")
            dimension_roles = _array(raw["dimension_roles"], f"descriptor {index}/{di}.dimension_roles")
            if not all(type(role) is str and role for role in dimension_roles):
                _fail(f"descriptor {index}/{di}.dimension_roles is invalid")
            expected_roles = {
                "ellipsoid": ("form_extent_x", "form_extent_y", "form_extent_z"),
                "capsule": ("form_radius",),
                "tapered-segment": ("form_start_radius", "form_end_radius"),
            }[shape["name"]]
            if key[3] == "upper_arm":
                expected_roles = ("form_radius", "form_shoulder_depth_radius")
            if tuple(dimension_roles) != expected_roles or any((key, role) not in dimension_keys for role in dimension_roles):
                _fail(f"descriptor {index}/{di}.dimension_roles do not identify its source controls")
            consumed_dimension_keys.update((key, role) for role in dimension_roles)
            factors = _display_factors(VARIANT_IDS[index], key[3], shape["name"])
            if shape["name"] == "ellipsoid":
                controls = tuple(shape["axis_extents_permille"])
            elif shape["name"] == "capsule":
                controls = (shape["radius_permille"],)
            else:
                controls = (
                    shape["start_radius_permille"],
                    shape["end_radius_permille"],
                )
            expected_controls = tuple(
                _scaled_display_value(
                    dimension_values[(key, role)],
                    factor,
                    f"descriptor {index}/{di}.shape.{role}",
                )
                for role, factor in zip(dimension_roles[: len(factors)], factors)
            )
            if controls != expected_controls:
                _fail(
                    f"descriptor {index}/{di}.shape numeric controls do not match "
                    "source-authored dimensions after the fixed display factor"
                )
            parsed.append(Descriptor(key, parent, np.asarray(point, dtype=np.float64) / reference_scale, point, shape, tuple(dimension_roles), placement, raw["profile_id"], raw["source"], descriptor_provenance, raw))
        sorted_keys = sorted(keys)
        if keys != sorted_keys:
            _fail(f"variants[{index}].descriptors are not stable AddressKey order")
        keyset = set(keys)
        if sum(x.parent is None for x in parsed) != 1 or parent_key not in keyset or child_key not in keyset:
            _fail(f"variants[{index}] root or reference addresses are invalid")
        by_key = {x.key: x for x in parsed}
        for desc in parsed:
            if desc.parent is not None and desc.parent not in keyset:
                _fail(f"variants[{index}] contains a missing parent")
            lineage: set[Any] = set()
            current: tuple[str, tuple[str, ...], str, str] | None = desc.key
            while current is not None:
                if current in lineage:
                    _fail(f"variants[{index}] contains a parent cycle")
                lineage.add(current)
                current = by_key[current].parent
        signature = [(x.key, x.exact_point, x.parent, x.placement_source, x.shape["name"], x.dimension_roles) for x in parsed]
        if canonical is None:
            canonical = signature
        elif signature != canonical:
            _fail(f"variants[{index}] do not preserve semantic descriptor identity")
        normalized.append((VARIANT_IDS[index], tuple(parsed), variant))
        variant_torso_profiles.append(
            _parse_variant_torso_profile(
                variant["torso_profile"],
                source,
                authored_torso_profile,
                VARIANT_IDS[index],
            )
        )
        variant_head_neck_profiles.append(
            _parse_variant_head_neck_profile(
                variant["head_neck_profile"],
                source,
                authored_head_neck_profile,
                VARIANT_IDS[index],
            )
        )
    if canonical is None:
        _fail("no descriptors")
    profile_dimension_keys = {
        (control.owner, control.role)
        for section in authored_torso_profile.sections
        for control in (section.lateral, section.anterior, section.posterior)
    }
    consumed_dimension_keys.update(profile_dimension_keys)
    consumed_dimension_keys.update(
        (control.owner, control.role)
        for section in authored_head_neck_profile.sections
        for control in (section.lateral, section.up, section.forward)
    )
    if consumed_dimension_keys != dimension_keys:
        _fail("authored_dimensions must equal the complete descriptor-consumed control set")
    candidates = []
    points = {row[0]: row[1] for row in canonical}
    parents = {row[0]: row[2] for row in canonical}
    for child, parent in parents.items():
        if parent is not None:
            d = tuple(points[child][i] - points[parent][i] for i in range(3))
            sq = sum(x * x for x in d)
            if sq:
                candidates.append((sq, child, parent, tuple(d)))
    if not candidates or (squared, child_key, parent_key, delta) != min(candidates, key=lambda x: (x[0], x[1])):
        _fail("reference_scale does not name the selected exact descriptor edge")
    descriptor_keys = {descriptor.key for _, descriptors, _ in normalized for descriptor in descriptors}
    if any(frame.owner not in descriptor_keys for frame in parsed_frames) or any(landmark.owner not in descriptor_keys for landmark in parsed_landmarks):
        _fail("source-authored shoulder controls must be owned by variant descriptors")
    if any(section.owner not in descriptor_keys for section in authored_torso_profile.sections):
        _fail("authored_torso_profile sections must be owned by variant descriptors")
    if any(section.owner not in descriptor_keys for section in authored_head_neck_profile.sections):
        _fail("authored_head_neck_profile sections must be owned by variant descriptors")
    return Form(
        root,
        source,
        reference_scale,
        scale,
        tuple(parsed_dimensions),
        tuple(parsed_landmarks),
        tuple(parsed_frames),
        authored_torso_profile,
        authored_head_neck_profile,
        tuple(variant_torso_profiles),
        tuple(variant_head_neck_profiles),
        tuple(normalized),
    )


def _key_text(key: tuple[str, tuple[str, ...], str, str]) -> str:
    return json.dumps(_address_json(key), sort_keys=True, separators=(",", ":"))


def _segment_field(points: np.ndarray, start: np.ndarray, end: np.ndarray, r0: float, r1: float) -> np.ndarray:
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    t = np.clip(np.sum((points - start) * axis, axis=-1) / length_sq, 0.0, 1.0)
    closest = start + t[..., None] * axis
    radius = r0 + (r1 - r0) * t
    return np.linalg.norm(points - closest, axis=-1) - radius


def _normalise_shape(shape: dict[str, Any], scale: float) -> dict[str, Any]:
    """Convert an envelope shape into the small numeric shape representation."""

    if shape["name"] == "ellipsoid":
        return {
            "name": "ellipsoid",
            "center": np.asarray(shape["center"], dtype=np.float64) / scale,
            "radii": np.asarray(shape["axis_extents_permille"], dtype=np.float64) / 1000.0,
        }
    start = np.asarray(shape["from"], dtype=np.float64) / scale
    end = np.asarray(shape["to"], dtype=np.float64) / scale
    if shape["name"] == "capsule":
        radius = float(shape["radius_permille"]) / 1000.0
        return {"name": "capsule", "from": start, "to": end, "r0": radius, "r1": radius}
    return {
        "name": "tapered-segment",
        "from": start,
        "to": end,
        "r0": float(shape["start_radius_permille"]) / 1000.0,
        "r1": float(shape["end_radius_permille"]) / 1000.0,
    }


def _ellipsoid(center: np.ndarray, radii: np.ndarray) -> dict[str, Any]:
    return {"name": "ellipsoid", "center": np.asarray(center, dtype=np.float64), "radii": np.asarray(radii, dtype=np.float64)}


def _segment(name: str, start: np.ndarray, end: np.ndarray, r0: float, r1: float | None = None) -> dict[str, Any]:
    radius_end = r0 if r1 is None else r1
    return {"name": name, "from": np.asarray(start, dtype=np.float64), "to": np.asarray(end, dtype=np.float64), "r0": float(r0), "r1": float(radius_end)}


def _torso_cage_shape(cage: _TorsoCage) -> dict[str, Any]:
    """Materialise the private ordered cage for the disposable field adapter.

    The field is intentionally an oriented, axis-aligned prototype.  Each
    section supplies a centre and two transverse radii; the evaluator uses a
    deterministic monotone piecewise-cubic (PCHIP-style) interpolation between
    adjacent sections and clamps at the finite end caps.  The limiter preserves
    each interval's endpoint bounds while making the first derivative shared at
    interior sections.

    ``section_owners`` is retained on the private shape so mesh winner labels
    can expose the existing source ownership policy even though the whole
    continuous cage is one compiled field.  The canonical recipe owner is the
    torso descriptor; local labels select the source owner of the nearest
    axial cage section, with ties resolved toward the lower section index.
    """

    if len(cage.sections) < 2:
        _fail("torso cage requires at least two sections")
    centers = np.asarray([section.center for section in cage.sections], dtype=np.float64)
    heights = centers[:, 1]
    lateral = np.asarray([section.lateral_radius for section in cage.sections], dtype=np.float64)
    depth = np.asarray([section.depth_radius for section in cage.sections], dtype=np.float64)
    if (
        centers.shape != (len(cage.sections), 3)
        or not np.all(np.isfinite(centers))
        or not np.all(np.isfinite(lateral))
        or not np.all(np.isfinite(depth))
        or np.any(lateral <= 0.0)
        or np.any(depth <= 0.0)
        or np.any(np.diff(heights) <= 0.0)
    ):
        _fail("torso cage field controls are invalid")
    cap_radius = np.minimum(lateral, depth)
    return {
        "name": "torso-cage",
        "centers": centers,
        "heights": heights,
        "lateral_radii": lateral,
        "depth_radii": depth,
        "cap_radii": cap_radius,
        "center_slopes": _monotone_cubic_slopes(heights, centers),
        "lateral_slopes": _monotone_cubic_slopes(heights, lateral),
        "depth_slopes": _monotone_cubic_slopes(heights, depth),
        "section_owners": tuple(section.owner for section in cage.sections),
    }


def _monotone_cubic_slopes(x: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Return shape-preserving PCHIP-style slopes for one or more value axes.

    This is the Fritsch--Carlson/Hyman-limited form of monotone cubic Hermite
    interpolation.  It is intentionally local and dependency-free: every
    interior tangent is the weighted harmonic mean of neighbouring secants
    when they have the same sign, and is zero at a turning point.  One-sided
    endpoint tangents receive the usual sign and three-slope limiter.  The
    result is therefore safe for positive radii and does not invent extrema
    between two source sections.
    """

    try:
        x = np.asarray(x, dtype=np.float64)
        values = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError):
        _fail("monotone cubic controls are not numeric")
    if x.ndim != 1 or values.ndim not in (1, 2) or values.shape[0] != x.size or x.size < 2:
        _fail("monotone cubic controls have invalid dimensions")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(values)) or np.any(np.diff(x) <= 0.0):
        _fail("monotone cubic controls are invalid")

    scalar_axis = values.ndim == 1
    controls = values[:, None] if scalar_axis else values
    spacing = np.diff(x)
    if not np.all(np.isfinite(spacing)) or np.any(spacing <= 0.0):
        _fail("monotone cubic spacing is not finite and strictly increasing")
    differences = np.diff(controls, axis=0)
    if not np.all(np.isfinite(differences)):
        _fail("monotone cubic control differences are not finite")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        secants = differences / spacing[:, None]
    if not np.all(np.isfinite(secants)):
        _fail("monotone cubic secants are not finite")
    slopes = np.zeros_like(controls)

    if x.size == 2:
        slopes[0] = secants[0]
        slopes[1] = secants[0]
    else:
        previous = secants[:-1]
        following = secants[1:]
        same_sign = previous * following > 0.0
        # For knot i, h_(i-1) is spacing[i-1] and h_i is spacing[i].
        with np.errstate(over="ignore", invalid="ignore"):
            left_weight = 2.0 * spacing[1:] + spacing[:-1]
            right_weight = spacing[1:] + 2.0 * spacing[:-1]
        if not np.all(np.isfinite(left_weight)) or not np.all(np.isfinite(right_weight)):
            _fail("monotone cubic tangent weights are not finite")
        with np.errstate(divide="ignore", invalid="ignore"):
            denominator = left_weight[:, None] / previous + right_weight[:, None] / following
            if np.any(same_sign & ~np.isfinite(denominator)) or np.any(same_sign & (denominator == 0.0)):
                _fail("monotone cubic tangent denominator is invalid")
            interior = np.divide(
                left_weight[:, None] + right_weight[:, None],
                denominator,
                out=np.zeros_like(denominator),
                where=same_sign,
            )
        slopes[1:-1] = np.where(same_sign, interior, 0.0)

        first = ((2.0 * spacing[0] + spacing[1]) * secants[0] - spacing[0] * secants[1]) / (spacing[0] + spacing[1])
        first = np.where(first * secants[0] <= 0.0, 0.0, first)
        first = np.where(
            (secants[0] * secants[1] < 0.0) & (np.abs(first) > np.abs(3.0 * secants[0])),
            3.0 * secants[0],
            first,
        )
        last = ((2.0 * spacing[-1] + spacing[-2]) * secants[-1] - spacing[-1] * secants[-2]) / (spacing[-1] + spacing[-2])
        last = np.where(last * secants[-1] <= 0.0, 0.0, last)
        last = np.where(
            (secants[-1] * secants[-2] < 0.0) & (np.abs(last) > np.abs(3.0 * secants[-1])),
            3.0 * secants[-1],
            last,
        )
        slopes[0] = first
        slopes[-1] = last

    if not np.all(np.isfinite(slopes)):
        _fail("monotone cubic slopes are not finite")
    return slopes[:, 0] if scalar_axis else slopes


def _monotone_cubic_sample(
    x: np.ndarray,
    values: np.ndarray,
    slopes: np.ndarray,
    query: np.ndarray | float,
) -> np.ndarray:
    """Evaluate a bounded cubic Hermite profile at scalar or array queries."""

    try:
        x = np.asarray(x, dtype=np.float64)
        values = np.asarray(values, dtype=np.float64)
        slopes = np.asarray(slopes, dtype=np.float64)
        query_array = np.asarray(query, dtype=np.float64)
    except (TypeError, ValueError, OverflowError):
        _fail("monotone cubic sample controls are not numeric")
    scalar_axis = values.ndim == 1
    controls = values[:, None] if scalar_axis else values
    tangent = slopes[:, None] if scalar_axis else slopes
    if x.ndim != 1 or controls.ndim != 2 or tangent.shape != controls.shape or x.size != controls.shape[0] or x.size < 2:
        _fail("monotone cubic sample controls have invalid dimensions")
    spacing = np.diff(x)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(spacing)) or np.any(spacing <= 0.0):
        _fail("monotone cubic sample axis is not finite and strictly increasing")
    if not np.all(np.isfinite(controls)) or not np.all(np.isfinite(tangent)):
        _fail("monotone cubic sample controls are not finite")
    if not np.all(np.isfinite(query_array)):
        _fail("monotone cubic sample query is invalid")

    clipped = np.clip(query_array, x[0], x[-1])
    interval = np.clip(np.searchsorted(x, clipped, side="right") - 1, 0, x.size - 2)
    h = x[interval + 1] - x[interval]
    t = np.divide(clipped - x[interval], h)
    y0 = controls[interval]
    y1 = controls[interval + 1]
    m0 = tangent[interval]
    m1 = tangent[interval + 1]
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    terms = (
        h00[..., None] * y0,
        h10[..., None] * h[..., None] * m0,
        h01[..., None] * y1,
        h11[..., None] * h[..., None] * m1,
    )
    if not np.all(np.isfinite(h)) or not np.all(np.isfinite(t)) or not all(np.all(np.isfinite(term)) for term in terms):
        _fail("monotone cubic sample arithmetic is not finite")
    sampled = terms[0] + terms[1] + terms[2] + terms[3]
    if not np.all(np.isfinite(sampled)):
        _fail("monotone cubic sample result is not finite")

    # Explicitly restore source values at representable section coordinates;
    # this makes the exact-section contract independent of floating-point
    # cancellation in the Hermite basis.
    for index, coordinate in enumerate(x):
        exact = clipped == coordinate
        if np.any(exact):
            sampled = np.where(exact[..., None], controls[index], sampled)
    result = sampled[..., 0] if scalar_axis else sampled
    return result


def _torso_cage_sample_controls(shape: dict[str, Any], axial: np.ndarray | float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample the shared torso controls used by both field and root anchors."""

    query = np.asarray(axial, dtype=np.float64)
    clipped = np.clip(query, shape["heights"][0], shape["heights"][-1])
    center = _monotone_cubic_sample(shape["heights"], shape["centers"], shape["center_slopes"], clipped).copy()
    center[..., 1] = clipped
    lateral = _monotone_cubic_sample(shape["heights"], shape["lateral_radii"], shape["lateral_slopes"], clipped)
    depth = _monotone_cubic_sample(shape["heights"], shape["depth_radii"], shape["depth_slopes"], clipped)
    return center, lateral, depth


def _torso_cage_field(points: np.ndarray, shape: dict[str, Any]) -> np.ndarray:
    """Evaluate a clamped, swept elliptical torso cage with rounded end caps."""

    points = np.asarray(points, dtype=np.float64)
    heights = shape["heights"]
    centers = shape["centers"]
    lateral = shape["lateral_radii"]
    depth = shape["depth_radii"]
    cap_radii = shape["cap_radii"]
    y = points[..., 1]
    lower = float(heights[0])
    upper = float(heights[-1])
    inside = (y >= lower) & (y <= upper)

    centre, lateral_radius, depth_radius = _torso_cage_sample_controls(shape, y)
    transverse = points - centre
    transverse_norm = np.sqrt(
        (transverse[..., 0] / lateral_radius) ** 2
        + (transverse[..., 2] / depth_radius) ** 2
    )
    inside_value = (transverse_norm - 1.0) * np.minimum(lateral_radius, depth_radius)

    # Outside the ordered profile, use an ellipsoidal cap centred at the end
    # section.  It is finite, rounded, and shares the exact boundary equation
    # with the swept section at the profile endpoint.
    cap_index = np.where(y < lower, 0, len(heights) - 1)
    cap_center = centers[cap_index]
    cap_lateral = lateral[cap_index]
    cap_depth = depth[cap_index]
    cap_height = cap_radii[cap_index]
    cap_offset = points - cap_center
    cap_norm = np.sqrt(
        (cap_offset[..., 0] / cap_lateral) ** 2
        + (cap_offset[..., 1] / cap_height) ** 2
        + (cap_offset[..., 2] / cap_depth) ** 2
    )
    cap_value = (cap_norm - 1.0) * np.minimum(np.minimum(cap_lateral, cap_depth), cap_height)
    return np.where(inside, inside_value, cap_value)


def _torso_cage_boundary_anchor(
    cage: _TorsoCage,
    axial_coordinate: float,
    direction: np.ndarray | tuple[float, float, float],
) -> np.ndarray:
    """Return a deterministic attachment point on the swept cage boundary.

    Limb roots use the lateral/forward ellipse at the nearest cage end when
    their source point lies below or above the profile.  A direction without a
    lateral/forward component is only valid outside the profile, where it
    selects the rounded bottom or top cap.  This keeps junctions on the one
    torso field rather than silently falling back to the obsolete source
    ellipsoid.
    """

    axial = float(axial_coordinate)
    direction_value = np.asarray(direction, dtype=np.float64)
    if direction_value.shape != (3,) or not math.isfinite(axial) or not np.all(np.isfinite(direction_value)):
        _fail("torso cage boundary query requires finite scalar and three-vector")
    sections = cage.sections
    if len(sections) < 2:
        _fail("torso cage boundary query requires at least two sections")
    shape = _torso_cage_shape(cage)
    centers = shape["centers"]
    heights = shape["heights"]
    lateral = shape["lateral_radii"]
    depth = shape["depth_radii"]
    lower, upper = float(heights[0]), float(heights[-1])
    lateral_forward = direction_value[[0, 2]]
    lateral_forward_length = float(np.linalg.norm(lateral_forward))

    # An axial direction is unambiguous only in the rounded end-cap regions.
    # It is useful for the neck, whose source target sits above the upper
    # profile, and prevents a centreline query from inventing a side.
    if lateral_forward_length <= 1.0e-12:
        if axial < lower:
            return centers[0] - np.asarray([0.0, min(lateral[0], depth[0]), 0.0])
        if axial > upper:
            return centers[-1] + np.asarray([0.0, min(lateral[-1], depth[-1]), 0.0])
        _fail("torso cage boundary direction is ambiguous inside profile")

    # Clamp out-of-range root heights to the corresponding end section.  The
    # path bridge then spans the remaining axial difference while its start is
    # exactly on the cage perimeter.
    if axial <= lower:
        index = 0
        center = centers[index]
        lateral_radius = float(lateral[index])
        depth_radius = float(depth[index])
    elif axial >= upper:
        index = len(sections) - 1
        center = centers[index]
        lateral_radius = float(lateral[index])
        depth_radius = float(depth[index])
    else:
        center, lateral_radius, depth_radius = _torso_cage_sample_controls(shape, axial)
        lateral_radius = float(lateral_radius)
        depth_radius = float(depth_radius)

    dx, dz = lateral_forward / lateral_forward_length
    denominator = math.sqrt((dx / lateral_radius) ** 2 + (dz / depth_radius) ** 2)
    if not math.isfinite(denominator) or denominator <= 0.0:
        _fail("torso cage boundary direction is invalid")
    return center + np.asarray([dx / denominator, 0.0, dz / denominator])


_FIXED_GUIDE_AXES = _GuideAxes(
    lateral=(1.0, 0.0, 0.0),
    up=(0.0, 1.0, 0.0),
    forward=(0.0, 0.0, 1.0),
)
_LIMB_PROFILE_FACTORS = {
    "upper_arm": (1.05, 0.90, 0.70),
    "forearm": (0.82, 0.70, 0.88),
    "thigh": (1.10, 0.88, 0.72),
    "shin": (0.80, 0.62, 0.70),
}


@dataclass(frozen=True)
class _LimbSection:
    """One named source-owned tapered piece of a limb axis."""

    name: str
    centerline: tuple[tuple[float, float, float], tuple[float, float, float]]
    thickness: tuple[float, float]
    path_kind: str


@dataclass(frozen=True)
class _LimbJoint:
    """A source-owned joint station at the end of its proximal limb."""

    name: str
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    adjacent_profiles: tuple[float, float]


def _guide_point(value: np.ndarray | tuple[float, float, float], where: str) -> tuple[float, float, float]:
    point = tuple(float(item) for item in value)
    if len(point) != 3 or not all(math.isfinite(item) for item in point):
        _fail(f"{where} must be a finite three-vector")
    return point


def _guide_radii(value: np.ndarray | tuple[float, float, float], where: str) -> tuple[float, float, float]:
    radii = _guide_point(value, where)
    if any(item <= 0.0 for item in radii):
        _fail(f"{where} must contain positive values")
    return radii


def _guide_profile(value: tuple[float, ...], where: str) -> tuple[float, ...]:
    profile = tuple(float(item) for item in value)
    if not profile or not all(math.isfinite(item) and item > 0.0 for item in profile):
        _fail(f"{where} must contain finite positive values")
    return profile


def _derive_foot_chain_profile(
    source_radii: np.ndarray | tuple[float, float, float],
    where: str,
) -> tuple[tuple[float, float, float], tuple[float, float]]:
    """Derive the shared pad proportions and metatarsal taper interface.

    This is intentionally source-derived and independent of the shin hock:
    the hock can bind its distal adjacent profile to the first returned value,
    while the foot guide consumes the same pair after the hock exists.
    """

    pad_radii = _guide_radii(
        np.asarray(source_radii, dtype=np.float64) * np.asarray([1.08, 0.32, 0.42]),
        f"{where}.pad_radii",
    )
    metatarsal_profile = _guide_profile(
        (
            0.34 * math.sqrt(pad_radii[0] * pad_radii[2]),
            0.72 * min(pad_radii),
        ),
        f"{where}.metatarsal_profile",
    )
    return pad_radii, (float(metatarsal_profile[0]), float(metatarsal_profile[1]))


def _guide_path(
    start: np.ndarray | tuple[float, float, float],
    end: np.ndarray | tuple[float, float, float],
    profile: tuple[float, ...],
    where: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    path = (_guide_point(start, f"{where}.start"), _guide_point(end, f"{where}.end"))
    if path[0] == path[1]:
        _fail(f"{where} must not be zero length")
    _guide_profile(profile, f"{where}.profile")
    return path


def _guide_curve(
    points: tuple[np.ndarray | tuple[float, float, float], ...],
    profile: tuple[float, ...],
    where: str,
) -> tuple[tuple[float, float, float], ...]:
    """Validate a private polyline control set for a later curve consumer."""

    if len(points) < 3 or len(points) != len(profile):
        _fail(f"{where} must have matching three-or-more controls and profile")
    controls = tuple(_guide_point(point, f"{where}.point[{index}]") for index, point in enumerate(points))
    _guide_profile(profile, f"{where}.profile")
    if any(controls[index] == controls[index + 1] for index in range(len(controls) - 1)):
        _fail(f"{where} contains a zero-length adjacent segment")
    return controls


def _embed_boundary_connector(
    path: tuple[tuple[float, float, float], tuple[float, float, float]],
    profile: tuple[float, ...],
    where: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Move a connector's centreline start inside its owning cage boundary.

    ``path[0]`` remains the semantic boundary anchor exposed by the guide.
    In this fixed fixture the source limb root target lies inside the cage
    boundary. Therefore “toward the child” means toward that child root point,
    not toward the branch-facing outward side. The analytic connector
    centreline starts one support radius toward the child in the
    lateral/forward plane, so its spherical support meets the cage boundary
    rather than projecting a full radius outside the torso. The axial
    component remains in the path itself, preserving the intended limb
    direction.
    """

    _guide_profile(profile, f"{where}.profile")
    boundary = np.asarray(path[0], dtype=np.float64)
    target = np.asarray(path[1], dtype=np.float64)
    direction = target - boundary
    lateral_forward = direction[[0, 2]]
    lateral_forward_length = float(np.linalg.norm(lateral_forward))
    support = float(profile[0])
    if not math.isfinite(lateral_forward_length) or lateral_forward_length <= 1.0e-12 or not math.isfinite(support) or support <= 0.0:
        _fail(f"{where} cannot embed a degenerate boundary connector")
    if support >= lateral_forward_length:
        _fail(f"{where} support radius consumes its boundary-to-child span")
    lateral_direction = lateral_forward / lateral_forward_length
    compiled_start = boundary + np.asarray([lateral_direction[0], 0.0, lateral_direction[1]]) * support
    return _guide_path(compiled_start, target, profile, f"{where}.compiled")


def _guide_topology(descriptors: tuple[Descriptor, ...]) -> _GuideTopology:
    by_role = {(desc.key[1], desc.key[3]): desc for desc in descriptors}
    owner_keys = tuple(desc.key for desc in descriptors)
    parent_edges = tuple(
        (desc.parent, desc.key) for desc in descriptors if desc.parent is not None
    )
    bilateral_pairs = tuple(
        (by_role[("left",), role].key, by_role[("right",), role].key)
        for role in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot")
    )
    return _GuideTopology(owner_keys, parent_edges, bilateral_pairs, _FIXED_GUIDE_AXES)


def _field(points: np.ndarray, field: Field | Descriptor, scale: float | None = None) -> np.ndarray:
    """Evaluate a source-owned field or a legacy source descriptor.

    Keeping the descriptor form as a compatibility path makes this helper
    useful to focused tests while the renderer itself evaluates ``Field``
    recipes.
    """

    if isinstance(field, Field):
        shape = field.shape
    else:
        if scale is None:
            raise TypeError("scale is required when evaluating a descriptor")
        shape = _normalise_shape(field.shape, scale)
    if shape["name"] == "ellipsoid":
        centre = shape["center"]
        radii = shape["radii"]
        offset = points - centre
        normalized = np.sqrt(np.sum((offset / radii) ** 2, axis=-1))
        return (normalized - 1.0) * float(np.min(radii))
    if shape["name"] == "torso-cage":
        return _torso_cage_field(points, shape)
    return _segment_field(points, shape["from"], shape["to"], shape["r0"], shape["r1"])


def _field_owner_keys(points: np.ndarray, field: Field) -> tuple[tuple[str, tuple[str, ...], str, str], ...]:
    """Return deterministic source labels for sampled points on a field."""

    shape = field.shape
    if shape["name"] != "torso-cage":
        return tuple(field.owner.key for _ in range(len(points)))
    heights = shape["heights"]
    y = np.asarray(points, dtype=np.float64)[:, 1]
    # Nearest axial cage section is the ownership rule for the one blended
    # field. A midpoint tie is resolved toward the lower section index by
    # searchsorted. Lateral/depth offsets do not affect this spine-profile
    # attribution decision.
    section_index = np.searchsorted(heights, y, side="left")
    section_index = np.clip(section_index, 0, len(heights) - 1)
    previous = np.clip(section_index - 1, 0, len(heights) - 1)
    choose_previous = np.abs(y - heights[previous]) <= np.abs(y - heights[section_index])
    section_index = np.where(choose_previous, previous, section_index)
    owners = shape["section_owners"]
    return tuple(owners[int(index)].key for index in section_index)


def _source_shape(desc: Descriptor, scale: float) -> dict[str, Any]:
    return _normalise_shape(desc.shape, scale)


def _parent_surface_anchor(parent: Descriptor, target: np.ndarray, scale: float) -> np.ndarray:
    """Find the parent-field boundary in the parent-to-child direction.

    The current fixture convention is axis-aligned, so this intentionally
    avoids claiming arbitrary orientation support.  Segment fields use their
    nearest centreline point and interpolated radius.  A target exactly on an
    endpoint takes the outward cap; an interior centreline target is ambiguous
    and fails closed.
    """

    shape = _source_shape(parent, scale)
    if shape["name"] == "ellipsoid":
        delta = np.asarray(target, dtype=np.float64) - shape["center"]
        denominator = float(np.sum((delta / shape["radii"]) ** 2))
        if denominator > 1e-18 and math.isfinite(denominator):
            return shape["center"] + delta / math.sqrt(denominator)
        _fail(f"parent surface direction is ambiguous for {_key_text(parent.key)}")
    start, end = shape["from"], shape["to"]
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    if not math.isfinite(length_sq) or length_sq <= 1e-18:
        _fail(f"parent segment is degenerate for {_key_text(parent.key)}")
    raw_t = float(np.dot(np.asarray(target, dtype=np.float64) - start, axis) / length_sq)
    if not math.isfinite(raw_t):
        _fail(f"parent surface projection is non-finite for {_key_text(parent.key)}")
    t = min(max(raw_t, 0.0), 1.0)
    centreline = start + t * axis
    radius = float(shape["r0"] + (shape["r1"] - shape["r0"]) * t)
    offset = np.asarray(target, dtype=np.float64) - centreline
    offset_length = float(np.linalg.norm(offset))
    if offset_length > 1e-12 and math.isfinite(offset_length):
        return centreline + offset / offset_length * radius
    axis_length = math.sqrt(length_sq)
    if t <= 1e-12:
        return start - axis / axis_length * float(shape["r0"])
    if t >= 1.0 - 1e-12:
        return end + axis / axis_length * float(shape["r1"])
    _fail(f"parent surface direction is ambiguous on segment centreline for {_key_text(parent.key)}")


def _descriptor_children(descriptors: tuple[Descriptor, ...]) -> dict[tuple[str, tuple[str, ...], str, str], tuple[Descriptor, ...]]:
    children: dict[tuple[str, tuple[str, ...], str, str], list[Descriptor]] = {}
    for desc in descriptors:
        if desc.parent is not None:
            children.setdefault(desc.parent, []).append(desc)
    return {key: tuple(sorted(value, key=lambda item: item.key)) for key, value in children.items()}


def _child_for(desc: Descriptor, role: str, children: dict[tuple[str, tuple[str, ...], str, str], tuple[Descriptor, ...]]) -> Descriptor | None:
    matches = tuple(item for item in children.get(desc.key, ()) if item.key[3] == role)
    return matches[0] if matches else None


def _radius_from_shape(shape: dict[str, Any]) -> float:
    if shape["name"] == "ellipsoid":
        return float(np.min(shape["radii"]))
    return max(float(shape["r0"]), float(shape["r1"]), 1e-6)


def _validate_recipe_convention(descriptors: tuple[Descriptor, ...], scale: float) -> None:
    """Fail closed outside the one axis-aligned biped fixture convention."""

    expected = {
        ((), "pelvis"),
        ((), "torso"),
        ((), "neck"),
        ((), "head"),
        (("left",), "upper_arm"),
        (("left",), "forearm"),
        (("left",), "hand"),
        (("right",), "upper_arm"),
        (("right",), "forearm"),
        (("right",), "hand"),
        (("left",), "thigh"),
        (("left",), "shin"),
        (("left",), "foot"),
        (("right",), "thigh"),
        (("right",), "shin"),
        (("right",), "foot"),
        (("tail",), "tail_root"),
        (("tail",), "tail_tip"),
    }
    actual = {(desc.key[1], desc.key[3]) for desc in descriptors}
    if actual != expected or len(descriptors) != len(expected) or any(desc.key[2] != "part" for desc in descriptors):
        _fail("role recipes require the exact fixed 18-Part stylized-biped fixture")
    by_role = {(desc.key[1], desc.key[3]): desc for desc in descriptors}

    def item(anchors: tuple[str, ...], role: str) -> Descriptor:
        return by_role[(anchors, role)]

    pelvis = item((), "pelvis")
    expected_parents = {
        ((), "pelvis"): None,
        ((), "torso"): pelvis,
        ((), "neck"): item((), "torso"),
        ((), "head"): item((), "neck"),
        (("left",), "upper_arm"): item((), "torso"),
        (("left",), "forearm"): item(("left",), "upper_arm"),
        (("left",), "hand"): item(("left",), "forearm"),
        (("right",), "upper_arm"): item((), "torso"),
        (("right",), "forearm"): item(("right",), "upper_arm"),
        (("right",), "hand"): item(("right",), "forearm"),
        (("left",), "thigh"): pelvis,
        (("left",), "shin"): item(("left",), "thigh"),
        (("left",), "foot"): item(("left",), "shin"),
        (("right",), "thigh"): pelvis,
        (("right",), "shin"): item(("right",), "thigh"),
        (("right",), "foot"): item(("right",), "shin"),
        (("tail",), "tail_root"): pelvis,
        (("tail",), "tail_tip"): item(("tail",), "tail_root"),
    }
    for logical_key, expected_parent in expected_parents.items():
        descriptor = item(*logical_key)
        parent_key = None if expected_parent is None else expected_parent.key
        if descriptor.parent != parent_key:
            _fail(f"fixed-fixture parent relationship is invalid for {_key_text(descriptor.key)}")

    epsilon = 1e-12

    def expect_direction(child: Descriptor, parent: Descriptor, pattern: tuple[int, int, int]) -> None:
        delta = child.point - parent.point
        for axis, sign in enumerate(pattern):
            value = float(delta[axis])
            valid = abs(value) <= epsilon if sign == 0 else value > epsilon if sign > 0 else value < -epsilon
            if not valid:
                _fail(
                    "role recipes support only the fixed +Y-up/+Z-forward axis convention; "
                    f"invalid edge at {_key_text(child.key)}"
                )

    torso, neck, head = item((), "torso"), item((), "neck"), item((), "head")
    expect_direction(torso, pelvis, (0, 1, 0))
    expect_direction(neck, torso, (0, 1, 0))
    expect_direction(head, neck, (0, 1, 0))
    for anchors, side in ((('left',), -1), (('right',), 1)):
        upper_arm = item(anchors, "upper_arm")
        forearm = item(anchors, "forearm")
        hand = item(anchors, "hand")
        thigh = item(anchors, "thigh")
        shin = item(anchors, "shin")
        foot = item(anchors, "foot")
        expect_direction(upper_arm, torso, (side, 1, 0))
        expect_direction(forearm, upper_arm, (side, 0, 0))
        expect_direction(hand, forearm, (side, 0, 0))
        expect_direction(thigh, pelvis, (side, -1, 0))
        expect_direction(shin, thigh, (0, -1, 0))
        expect_direction(foot, shin, (0, -1, 1))
    tail_root, tail_tip = item(("tail",), "tail_root"), item(("tail",), "tail_tip")
    expect_direction(tail_root, pelvis, (0, 0, -1))
    expect_direction(tail_tip, tail_root, (0, 0, -1))

    for central in (torso, neck, head):
        if abs(float(central.point[0] - pelvis.point[0])) > epsilon or abs(float(central.point[2] - pelvis.point[2])) > epsilon:
            _fail("fixed-fixture torso chain must remain on the +Y centreline")
    for role in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot"):
        left, right = item(("left",), role), item(("right",), role)
        if not np.allclose(left.point[[1, 2]], right.point[[1, 2]], rtol=0.0, atol=epsilon) or abs(float(left.point[0] + right.point[0] - 2.0 * pelvis.point[0])) > epsilon:
            _fail(f"fixed-fixture bilateral placement is not mirrored for role {role!r}")

    ellipsoid_roles = (((), "pelvis"), ((), "torso"), ((), "head"), (("left",), "hand"), (("right",), "hand"), (("left",), "foot"), (("right",), "foot"))
    for logical_key in ellipsoid_roles:
        descriptor = item(*logical_key)
        shape = _source_shape(descriptor, scale)
        if shape["name"] != "ellipsoid" or not np.allclose(shape["center"], descriptor.point, rtol=0.0, atol=epsilon):
            _fail(f"fixed-fixture ellipsoid binding is invalid for {_key_text(descriptor.key)}")
    segment_children = {
        ((), "neck"): item((), "head"),
        (("left",), "upper_arm"): item(("left",), "forearm"),
        (("left",), "forearm"): item(("left",), "hand"),
        (("right",), "upper_arm"): item(("right",), "forearm"),
        (("right",), "forearm"): item(("right",), "hand"),
        (("left",), "thigh"): item(("left",), "shin"),
        (("left",), "shin"): item(("left",), "foot"),
        (("right",), "thigh"): item(("right",), "shin"),
        (("right",), "shin"): item(("right",), "foot"),
    }
    for logical_key, child in segment_children.items():
        descriptor = item(*logical_key)
        shape = _source_shape(descriptor, scale)
        if shape["name"] != "capsule" or not np.allclose(shape["from"], descriptor.point, rtol=0.0, atol=epsilon) or not np.allclose(shape["to"], child.point, rtol=0.0, atol=epsilon):
            _fail(f"fixed-fixture capsule binding is invalid for {_key_text(descriptor.key)}")
    for descriptor in (tail_root, tail_tip):
        shape = _source_shape(descriptor, scale)
        expected_parent = by_role[(descriptor.parent[1], descriptor.parent[3])] if descriptor.parent is not None else None
        if expected_parent is None or shape["name"] != "tapered-segment" or not np.allclose(shape["from"], expected_parent.point, rtol=0.0, atol=epsilon) or not np.allclose(shape["to"], descriptor.point, rtol=0.0, atol=epsilon):
            _fail(f"fixed-fixture tail binding is invalid for {_key_text(descriptor.key)}")


def _derive_torso_cage(
    form: Form,
    descriptors: tuple[Descriptor, ...],
    profile: AuthoredTorsoProfile,
) -> _TorsoCage:
    """Derive the seven-section torso cage from authored controls only.

    The source profile owns both depth sides.  The baseline analytic field is
    intentionally symmetric, so its one depth radius is the arithmetic mean
    of the independently scaled anterior and posterior controls.  The guide
    retains both exact controls and their lineage for the frame-aware
    successor and for review.
    """

    by_key = {descriptor.key: descriptor for descriptor in descriptors}
    expected_owner_roles = ("pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso")
    if tuple(section.name for section in profile.sections) != TORSO_PROFILE_SECTION_NAMES:
        _fail("authored torso profile sections have unstable order")
    if tuple(section.owner[3] for section in profile.sections) != expected_owner_roles:
        _fail("authored torso profile sections have invalid source owners")

    pelvis = by_key.get(profile.sections[0].owner)
    torso = by_key.get(profile.sections[2].owner)
    if pelvis is None or torso is None or pelvis.key[3] != "pelvis" or torso.key[3] != "torso":
        _fail("authored torso profile must bind pelvis and torso descriptors")
    variant_index = VARIANT_IDS.index(descriptors[0].profile_id)
    if len(form.variant_torso_profiles) != len(VARIANT_IDS):
        _fail("authored torso profile is missing a variant projection")
    variant_profile = form.variant_torso_profiles[variant_index]

    def lineage(
        control: AuthoredRadius,
        factor: int,
        section_name: str,
        where: str,
    ) -> _TorsoRadiusLineage:
        scaled = _scaled_display_value(control.value_permille, factor, where)
        return _TorsoRadiusLineage(
            base=control.value_permille,
            factor=factor,
            scaled=scaled,
            reference=(control.owner, control.role),
            reference_index=control.source_index,
            provenance=dict(control.provenance),
            consumed_section=section_name,
        )

    sections: list[_TorsoCageSection] = []
    frame_by_key = {(frame.owner, frame.role): frame for frame in form.authored_frames}
    for index, authored in enumerate(profile.sections):
        projected = variant_profile.sections[index]
        owner = by_key.get(authored.owner)
        if owner is None or owner.key[3] != expected_owner_roles[index]:
            _fail(f"authored torso profile section {authored.name!r} lost descriptor ownership")
        if authored.landmark.owner != authored.owner or authored.frame != authored.landmark.frame:
            _fail(f"authored torso profile section {authored.name!r} lost frame/landmark binding")
        frame = authored.frame
        if frame[1] != TORSO_PROFILE_FRAME_ROLE:
            _fail(f"authored torso profile section {authored.name!r} has an invalid frame role")
        if projected.source_section_index != index or projected.name != authored.name:
            _fail(f"torso-cage.{authored.name} variant projection order is invalid")
        center = _guide_point(
            np.asarray(owner.point, dtype=np.float64)
            + np.asarray(projected.position, dtype=np.float64) / form.reference_scale,
            f"torso-cage.{authored.name}.landmark",
        )
        frame_record = frame_by_key.get(authored.frame)
        if frame_record is None:
            _fail(f"torso-cage.{authored.name} lost its authored control frame")
        lateral_lineage = lineage(
            authored.lateral,
            projected.lateral_factor,
            authored.name,
            f"torso-cage.{authored.name}.lateral",
        )
        anterior_lineage = lineage(
            authored.anterior,
            projected.anterior_factor,
            authored.name,
            f"torso-cage.{authored.name}.anterior",
        )
        posterior_lineage = lineage(
            authored.posterior,
            projected.posterior_factor,
            authored.name,
            f"torso-cage.{authored.name}.posterior",
        )
        if (lateral_lineage.scaled, anterior_lineage.scaled, posterior_lineage.scaled) != (
            projected.lateral_radius_permille,
            projected.anterior_radius_permille,
            projected.posterior_radius_permille,
        ):
            _fail(f"torso-cage.{authored.name} lost exact variant-scaled radii")
        lateral_radius = projected.lateral_radius_permille / 1000.0
        anterior_radius = projected.anterior_radius_permille / 1000.0
        posterior_radius = projected.posterior_radius_permille / 1000.0
        depth_radius = 0.5 * (anterior_radius + posterior_radius)
        if not all(
            math.isfinite(value) and value > 0.0
            for value in (lateral_radius, anterior_radius, posterior_radius, depth_radius)
        ):
            _fail(f"torso-cage.{authored.name} authored radii are invalid")
        sections.append(
            _TorsoCageSection(
                name=authored.name,
                section_index=authored.section_index,
                frame_index=authored.frame_index,
                landmark_index=authored.landmark_index,
                owner=owner,
                frame=frame_record,
                landmark=authored.landmark,
                center=center,
                lateral_radius=lateral_radius,
                anterior_radius=anterior_radius,
                posterior_radius=posterior_radius,
                depth_radius=depth_radius,
                lateral_lineage=lateral_lineage,
                anterior_lineage=anterior_lineage,
                posterior_lineage=posterior_lineage,
            )
        )
    _validate_regional_route_order(
        tuple(section.center for section in sections),
        REGIONAL_ROUTE_ORDER_TORSO,
        "torso-cage.sections",
    )
    return _TorsoCage(
        pelvis_owner=pelvis,
        torso_owner=torso,
        sections=tuple(sections),
        axes=_FIXED_GUIDE_AXES,
    )


def _head_neck_transition_radius(section: _HeadNeckGuideSection) -> float:
    """Use the smallest authored cross-axis radius as the direct path radius."""

    radius = min(section.radii)
    if not math.isfinite(radius) or radius <= 0.0:
        _fail(f"head/neck station {section.name!r} has no valid transition radius")
    return float(radius)


def _derive_head_neck_profile(
    form: Form,
    descriptors: tuple[Descriptor, ...],
    profile: AuthoredHeadNeckProfile,
) -> _HeadNeckProfileGuide:
    """Project all authored head/neck stations and retain their exact lineage."""

    by_key = {descriptor.key: descriptor for descriptor in descriptors}
    variant_index = VARIANT_IDS.index(descriptors[0].profile_id)
    if len(form.variant_head_neck_profiles) != len(VARIANT_IDS):
        _fail("authored head/neck profile is missing a variant projection")
    variant_profile = form.variant_head_neck_profiles[variant_index]
    if variant_profile.connections != profile.connections:
        _fail("head/neck variant projection lost authored connections")
    frame_by_key = {(frame.owner, frame.role): frame for frame in form.authored_frames}
    sections: list[_HeadNeckGuideSection] = []

    def lineage(control: AuthoredRadius, factor: int, section_name: str, where: str) -> _HeadNeckRadiusLineage:
        scaled = _scaled_display_value(control.value_permille, factor, where)
        return _HeadNeckRadiusLineage(
            base=control.value_permille,
            factor=factor,
            scaled=scaled,
            reference=(control.owner, control.role),
            reference_index=control.source_index,
            provenance=dict(control.provenance),
            consumed_section=section_name,
        )

    for index, authored in enumerate(profile.sections):
        projected = variant_profile.sections[index]
        if projected.source_section_index != authored.section_index or projected.name != authored.name:
            _fail(f"head/neck guide section {authored.name!r} lost source section order")
        owner = by_key.get(authored.owner)
        if owner is None or owner.key[3] != HEAD_NECK_PROFILE_OWNER_ROLES[index]:
            _fail(f"head/neck guide section {authored.name!r} lost descriptor ownership")
        if authored.landmark.owner != authored.owner or authored.frame != authored.landmark.frame:
            _fail(f"head/neck guide section {authored.name!r} lost frame/landmark binding")
        frame_record = frame_by_key.get(authored.frame)
        if frame_record is None or frame_record.role != HEAD_NECK_PROFILE_FRAME_ROLE:
            _fail(f"head/neck guide section {authored.name!r} lost its identity frame")
        center = _guide_point(
            np.asarray(owner.point, dtype=np.float64) + np.asarray(projected.position, dtype=np.float64) / form.reference_scale,
            f"head-neck.{authored.name}.landmark",
        )
        factors = (projected.lateral_factor, projected.up_factor, projected.forward_factor)
        controls = (authored.lateral, authored.up, authored.forward)
        lineages = tuple(
            lineage(control, factor, authored.name, f"head-neck.{authored.name}.{axis}")
            for axis, control, factor in zip(("lateral", "up", "forward"), controls, factors)
        )
        scaled = (lineages[0].scaled, lineages[1].scaled, lineages[2].scaled)
        projected_scaled = (
            projected.lateral_radius_permille,
            projected.up_radius_permille,
            projected.forward_radius_permille,
        )
        if scaled != projected_scaled:
            _fail(f"head/neck guide section {authored.name!r} lost exact projected radii")
        radii = tuple(value / 1000.0 for value in scaled)
        _guide_radii(radii, f"head-neck.{authored.name}.radii")
        sections.append(
            _HeadNeckGuideSection(
                name=authored.name,
                section_index=authored.section_index,
                source_section_index=projected.source_section_index,
                frame_index=authored.frame_index,
                landmark_index=authored.landmark_index,
                owner=owner,
                frame=frame_record,
                landmark=authored.landmark,
                center=center,
                radii=radii,  # type: ignore[arg-type]
                lateral_lineage=lineages[0],
                up_lineage=lineages[1],
                forward_lineage=lineages[2],
            )
        )
    _validate_regional_route_order(
        tuple(section.center for section in sections),
        REGIONAL_ROUTE_ORDER_GUIDE_HEAD_NECK,
        "head-neck.sections",
    )
    connections: list[_HeadNeckGuideConnection] = []
    for spec in profile.connections:
        if not 0 <= spec.from_section_index < len(sections) or not 0 <= spec.to_section_index < len(sections):
            _fail(f"head/neck connection {spec.name!r} has an invalid station index")
        from_section = sections[spec.from_section_index]
        to_section = sections[spec.to_section_index]
        thickness = (_head_neck_transition_radius(from_section), _head_neck_transition_radius(to_section))
        connections.append(
            _HeadNeckGuideConnection(
                spec=spec,
                from_section=from_section,
                to_section=to_section,
                centerline=_guide_path(
                    from_section.center,
                    to_section.center,
                    thickness,
                    f"head-neck.{spec.name}",
                ),
                thickness=thickness,
            )
        )
    return _HeadNeckProfileGuide(
        sections=tuple(sections),
        connections=tuple(connections),
        provenance=dict(profile.provenance),
        axes=_FIXED_GUIDE_AXES,
    )


def _derive_shoulder_frame(
    form: Form,
    torso_cage: _TorsoCage,
    head_guide: _HeadGuide,
    limb_guides: tuple[_LimbGuide, ...],
) -> _ShoulderFrame:
    """Derive a bilateral trapezius/shoulder frame without compiling skin.

    The source-authored peak and axilla landmarks supply the shoulder vertical
    profile, while the source-authored depth dimension supplies the wrap span.
    The named control frames are identity-only records: this adapter adds each
    source-local landmark position to the matching descriptor reference point
    after reference-scale normalization and performs no general frame/world
    resolution.
    """

    upper = torso_cage.upper_ribcage
    arms = tuple(item for item in limb_guides if item.owner.key[3] == "upper_arm")
    if len(arms) != 2:
        _fail("shoulder frame requires exactly two upper-arm guides")
    by_side = {item.owner.key[1][0]: item for item in arms if len(item.owner.key[1]) == 1}
    if set(by_side) != {"left", "right"}:
        _fail("shoulder frame requires one left and one right upper-arm guide")
    if any(item.root_centerline is None or item.root_thickness is None for item in arms):
        _fail("shoulder frame requires paired upper-arm root bridges")

    central_anchor = _guide_point(head_guide.neck_transition[0], "shoulder-frame.central-anchor")
    central_size = max(min(upper.lateral_radius, upper.depth_radius) * 0.24, 1.0e-9)
    central_profile = _guide_profile(
        (central_size, central_size * 0.82),
        "shoulder-frame.central-profile",
    )
    sides: list[_ShoulderSideGuide] = []
    descriptors_by_key = {item.owner.key: item.owner for item in limb_guides}
    for side in ("left", "right"):
        limb = by_side[side]
        owner = limb.owner
        source_start = _guide_point(limb.sections[0].centerline[0], f"{_key_text(owner.key)}.shoulder.socket-anchor")
        if descriptors_by_key.get(owner.key) is not owner:
            _fail(f"{_key_text(owner.key)} shoulder guide lost source descriptor ownership")
        frames = tuple(frame for frame in form.authored_frames if frame.owner == owner.key and frame.role == "form_shoulder_control")
        peaks = tuple(landmark for landmark in form.authored_landmarks if landmark.owner == owner.key and landmark.role == "form_shoulder_peak")
        axillae = tuple(landmark for landmark in form.authored_landmarks if landmark.owner == owner.key and landmark.role == "form_axilla")
        if len(frames) != 1 or len(peaks) != 1 or len(axillae) != 1:
            _fail(f"{_key_text(owner.key)} shoulder authored controls are incomplete")
        authored_frame, authored_peak, authored_axilla = frames[0], peaks[0], axillae[0]
        if authored_peak.frame != (authored_frame.owner, authored_frame.role) or authored_axilla.frame != (authored_frame.owner, authored_frame.role):
            _fail(f"{_key_text(owner.key)} shoulder landmarks do not retain their source control frame")
        peak_anchor = _guide_point(
            np.asarray(owner.point, dtype=np.float64) + np.asarray(authored_peak.position, dtype=np.float64) / form.reference_scale,
            f"{_key_text(owner.key)}.shoulder.peak-anchor",
        )
        axilla_anchor = _guide_point(
            np.asarray(owner.point, dtype=np.float64) + np.asarray(authored_axilla.position, dtype=np.float64) / form.reference_scale,
            f"{_key_text(owner.key)}.shoulder.axilla-anchor",
        )
        if not math.isclose(authored_peak.position[0], authored_axilla.position[0], rel_tol=0.0, abs_tol=GUIDE_TOLERANCE):
            _fail(f"{_key_text(owner.key)} shoulder landmarks must share a local lateral coordinate")
        if peak_anchor[1] <= axilla_anchor[1] + GUIDE_TOLERANCE:
            _fail(f"{_key_text(owner.key)} shoulder peak must be above axilla")
        if not math.isfinite(source_start[0]) or source_start[0] == 0.0:
            _fail(f"{_key_text(owner.key)} shoulder socket must be laterally placed")
        expected_sign = -1.0 if side == "left" else 1.0
        if any(point[0] * expected_sign <= 0.0 for point in (source_start, peak_anchor, axilla_anchor)):
            _fail(f"{_key_text(owner.key)} shoulder controls are on the wrong side")
        vertical_midpoint = 0.5 * (peak_anchor[1] + axilla_anchor[1])
        vertical_radius = 0.5 * (peak_anchor[1] - axilla_anchor[1])
        if not math.isfinite(vertical_midpoint) or not math.isfinite(vertical_radius) or vertical_radius <= GUIDE_TOLERANCE:
            _fail(f"{_key_text(owner.key)} shoulder vertical profile is invalid")
        depth_value_permille, depth_provenance = _authored_dimension(form, owner.key, "form_shoulder_depth_radius")
        depth_profile_factor = _shoulder_depth_factor(owner.profile_id)
        depth_scaled_permille = _scaled_display_value(
            depth_value_permille,
            depth_profile_factor,
            f"{_key_text(owner.key)}.form_shoulder_depth_radius",
        )
        depth_radius = float(depth_scaled_permille) / 1000.0
        if not math.isfinite(depth_radius) or depth_radius <= GUIDE_TOLERANCE:
            _fail(f"{_key_text(owner.key)} shoulder depth profile is invalid")
        span = abs(float(peak_anchor[0] - central_anchor[0]))
        if not math.isfinite(span) or span <= 0.0:
            _fail(f"{_key_text(owner.key)} shoulder span is invalid")
        slope = (float(peak_anchor[1]) - float(central_anchor[1])) / span
        if not math.isfinite(slope):
            _fail(f"{_key_text(owner.key)} shoulder slope is invalid")

        root_profile = _guide_profile(limb.root_thickness, f"{_key_text(owner.key)}.shoulder.root-profile")  # type: ignore[arg-type]
        arm_profile = _guide_profile(limb.sections[0].thickness, f"{_key_text(owner.key)}.shoulder.arm-profile")
        forward = np.asarray(_FIXED_GUIDE_AXES.forward, dtype=np.float64)
        extremum = np.asarray(peak_anchor, dtype=np.float64)
        wrap_anchor = np.asarray(
            (peak_anchor[0], vertical_midpoint, 0.5 * (peak_anchor[2] + axilla_anchor[2])),
            dtype=np.float64,
        )
        anterior_wrap = tuple(wrap_anchor + forward * depth_radius)
        posterior_wrap = tuple(wrap_anchor - forward * depth_radius)
        anterior_profile = tuple(float(value) for value in (central_profile[0], max(root_profile) * 0.94, max(root_profile) * 0.86, arm_profile[0]))
        posterior_profile = tuple(float(value) for value in (central_profile[1], max(root_profile) * 0.94, max(root_profile) * 0.86, arm_profile[0]))
        deltoid_profile = tuple(float(value) for value in (max(root_profile) * 0.86, arm_profile[0], arm_profile[1]))
        anterior_points = _guide_curve(
            (central_anchor, anterior_wrap, peak_anchor, source_start),
            anterior_profile,
            f"{_key_text(owner.key)}.shoulder.anterior-support",
        )
        posterior_points = _guide_curve(
            (central_anchor, posterior_wrap, peak_anchor, source_start),
            posterior_profile,
            f"{_key_text(owner.key)}.shoulder.posterior-return",
        )
        first_section_end = np.asarray(limb.sections[0].centerline[1], dtype=np.float64)
        socket = np.asarray(source_start, dtype=np.float64)
        first_quarter = socket + 0.25 * (first_section_end - socket)
        deltoid_points = _guide_curve(
            (peak_anchor, source_start, first_quarter),
            deltoid_profile,
            f"{_key_text(owner.key)}.shoulder.deltoid",
        )
        sides.append(
            _ShoulderSideGuide(
                side=side,
                owner=owner,
                authored_frame=authored_frame,
                authored_peak=authored_peak,
                authored_axilla=authored_axilla,
                peak_anchor=peak_anchor,
                axilla_anchor=axilla_anchor,
                vertical_midpoint=float(vertical_midpoint),
                vertical_radius=float(vertical_radius),
                depth_radius=depth_radius,
                depth_value_permille=depth_value_permille,
                depth_scaled_permille=depth_scaled_permille,
                depth_profile_factor=depth_profile_factor,
                depth_provenance=depth_provenance,
                socket_anchor=source_start,
                shoulder_extremum=peak_anchor,
                span=span,
                slope=float(slope),
                anterior_support=_ShoulderCurve("anterior-support", torso_cage.torso_owner, anterior_points, anterior_profile, _FIXED_GUIDE_AXES),
                posterior_return=_ShoulderCurve("posterior-return", torso_cage.torso_owner, posterior_points, posterior_profile, _FIXED_GUIDE_AXES),
                deltoid_sweep=_ShoulderCurve("deltoid-sweep", owner, deltoid_points, deltoid_profile, _FIXED_GUIDE_AXES),
                axes=_FIXED_GUIDE_AXES,
            )
        )
    return _ShoulderFrame(
        torso_owner=torso_cage.torso_owner,
        neck_owner=head_guide.neck_owner,
        central_anchor=central_anchor,
        central_profile=central_profile,
        sides=(sides[0], sides[1]),
        axes=_FIXED_GUIDE_AXES,
    )


def _derive_hybrid_guides(form: Form, descriptors: tuple[Descriptor, ...]) -> _HybridGuide:
    """Derive regional guide controls directly from validated source data."""

    _validate_recipe_convention(descriptors, form.reference_scale)
    by_key = {desc.key: desc for desc in descriptors}
    by_role = {(desc.key[1], desc.key[3]): desc for desc in descriptors}

    def item(anchors: tuple[str, ...], role: str) -> Descriptor:
        return by_role[(anchors, role)]

    def path_source(desc: Descriptor) -> dict[str, Any]:
        source = _source_shape(desc, form.reference_scale)
        if source["name"] not in {"capsule", "tapered-segment"}:
            _fail(f"guide path source is invalid for {_key_text(desc.key)}")
        return source

    pelvis = item((), "pelvis")
    torso = item((), "torso")
    neck = item((), "neck")
    head = item((), "head")
    pelvis_source = _source_shape(pelvis, form.reference_scale)
    torso_source = _source_shape(torso, form.reference_scale)

    pelvis_center = _guide_point(pelvis_source["center"], "pelvis.center")
    pelvis_radii = _guide_radii(pelvis_source["radii"], "pelvis.radii")
    torso_center = _guide_point(torso_source["center"], "torso.center")
    torso_radii = _guide_radii(torso_source["radii"], "torso.radii")
    # Keep the axial silhouette legible as three stations.  The broad source
    # torso is only a placement/provenance input here; it is not emitted as a
    # competing fill.  Station proportions are private visual controls and
    # intentionally remain derived from the source pelvis/torso radii.
    pelvic_girdle_radii = _guide_radii(
        pelvis_source["radii"] * np.asarray([1.00, 0.70, 0.96]),
        "pelvis.girdle_radii",
    )
    pelvic_station_center = pelvis_center
    pelvic_station_radii = pelvic_girdle_radii
    pelvic_core_center = _guide_point(
        pelvis_center + np.asarray([0.0, 0.10 * pelvis_source["radii"][1], 0.0]),
        "pelvis.pelvic_core_center",
    )
    pelvic_core_radii = _guide_radii(
        pelvis_source["radii"] * np.asarray([0.78, 0.52, 0.75]),
        "pelvis.pelvic_core_radii",
    )
    waist_center = _guide_point(
        torso_source["center"] + np.asarray([0.0, -0.18 * torso_source["radii"][1], 0.0]),
        "torso.waist_center",
    )
    waist_radii = _guide_radii(
        torso_source["radii"] * np.asarray([0.62, 0.40, 0.72]),
        "torso.waist_radii",
    )
    chest_center = _guide_point(
        torso_source["center"] + np.asarray([0.0, 0.35 * torso_source["radii"][1], 0.0]),
        "torso.chest_center",
    )
    chest_radii = _guide_radii(
        torso_source["radii"] * np.asarray([0.92, 0.78, 1.00]),
        "torso.chest_radii",
    )
    torso_cage = _derive_torso_cage(form, descriptors, form.authored_torso_profile)
    pelvic_waist_path = _guide_path(
        np.asarray(pelvic_station_center) + np.asarray([0.0, 0.42 * pelvic_station_radii[1], 0.0]),
        np.asarray(waist_center) - np.asarray([0.0, 0.30 * waist_radii[1], 0.0]),
        (float(pelvic_station_radii[0] * 0.46), float(waist_radii[0] * 0.88)),
        "axial.pelvis_waist_transition",
    )
    waist_chest_path = _guide_path(
        np.asarray(waist_center) + np.asarray([0.0, 0.30 * waist_radii[1], 0.0]),
        np.asarray(chest_center) - np.asarray([0.0, 0.42 * chest_radii[1], 0.0]),
        (float(waist_radii[0] * 0.88), float(chest_radii[0] * 0.56)),
        "axial.waist_chest_transition",
    )
    transitions = (
        _AxialTransition("pelvis-waist", pelvic_waist_path, (float(pelvic_station_radii[0] * 0.46), float(waist_radii[0] * 0.88))),
        _AxialTransition("waist-chest", waist_chest_path, (float(waist_radii[0] * 0.88), float(chest_radii[0] * 0.56))),
    )
    # Keep one private compatibility centerline for the in-memory guide
    # validator.  It is a display spine only; field compilation consumes the
    # two short transitions above, never this full-line trunk.  The sidecar
    # deliberately omits this legacy diagnostic so consumers see the actual
    # compiled axial controls.
    display_centerline = _guide_path(
        pelvic_waist_path[0],
        waist_chest_path[1],
        (transitions[0].thickness[0], transitions[1].thickness[-1]),
        "axial.display_centerline",
    )
    axial_guides = (
        _AxialGuide(
            owner=pelvis,
            girdle_center=pelvis_center,
            girdle_radii=pelvic_girdle_radii,
            pelvic_core_center=_guide_point(
                pelvic_core_center,
                "pelvis.pelvic_core_center",
            ),
            pelvic_core_radii=pelvic_core_radii,
            chest_center=None,
            chest_radii=None,
            waist_center=None,
            waist_radii=None,
            trunk_centerline=None,
            trunk_thickness=None,
            stations=(_AxialStation("pelvic-girdle", pelvic_station_center, pelvic_station_radii),),
            transitions=(),
            axes=_FIXED_GUIDE_AXES,
        ),
        _AxialGuide(
            owner=torso,
            girdle_center=None,
            girdle_radii=None,
            pelvic_core_center=None,
            pelvic_core_radii=None,
            chest_center=chest_center,
            chest_radii=chest_radii,
            waist_center=waist_center,
            waist_radii=waist_radii,
            trunk_centerline=display_centerline,
            trunk_thickness=(transitions[0].thickness[0], transitions[1].thickness[-1]),
            stations=(
                _AxialStation("waist", waist_center, waist_radii),
                _AxialStation("chest-girdle", chest_center, chest_radii),
            ),
            transitions=transitions,
            axes=_FIXED_GUIDE_AXES,
        ),
    )

    head_neck_profile = _derive_head_neck_profile(form, descriptors, form.authored_head_neck_profile)
    stations_by_name = {section.name: section for section in head_neck_profile.sections}
    cranium_station = stations_by_name["cranium-mid"]
    muzzle_station = stations_by_name["muzzle-mid"]
    neck_collar_station = stations_by_name["neck-collar"]
    neck_upper_station = stations_by_name["neck-upper"]
    head_base_station = stations_by_name["head-base"]
    cranium_center = cranium_station.center
    cranium_radii = cranium_station.radii
    muzzle_center = muzzle_station.center
    muzzle_radii = muzzle_station.radii
    head_transition = (neck_upper_station.center, head_base_station.center)
    head_transition_thickness = (
        _head_neck_transition_radius(neck_upper_station),
        _head_neck_transition_radius(head_base_station),
    )
    neck_transition = (neck_collar_station.center, neck_upper_station.center)
    neck_transition_thickness = (
        _head_neck_transition_radius(neck_collar_station),
        _head_neck_transition_radius(neck_upper_station),
    )
    head_guide = _HeadGuide(
        head_owner=head,
        neck_owner=neck,
        profile=head_neck_profile,
        cranium_center=cranium_center,
        cranium_radii=cranium_radii,
        muzzle_center=muzzle_center,
        muzzle_radii=muzzle_radii,
        head_transition=_guide_path(head_transition[0], head_transition[1], head_transition_thickness, "head.transition"),
        head_transition_thickness=head_transition_thickness,
        neck_transition=_guide_path(neck_transition[0], neck_transition[1], neck_transition_thickness, "neck.transition"),
        neck_transition_thickness=neck_transition_thickness,
        neck_collar_center=neck_collar_station.center,
        neck_collar_radii=neck_collar_station.radii,
        axes=_FIXED_GUIDE_AXES,
    )

    limb_guides: list[_LimbGuide] = []
    for desc in descriptors:
        role = desc.key[3]
        if role not in _LIMB_PROFILE_FACTORS:
            continue
        source = path_source(desc)
        start = _guide_point(source["from"], f"{_key_text(desc.key)}.start")
        end = _guide_point(source["to"], f"{_key_text(desc.key)}.end")
        factors = _LIMB_PROFILE_FACTORS[role]
        source_r0, source_r1 = float(source["r0"]), float(source["r1"])
        middle_radius = 0.5 * (source_r0 + source_r1)
        profile_controls = _guide_profile(
            (source_r0 * factors[0], middle_radius * factors[1], source_r1 * factors[2]),
            f"{_key_text(desc.key)}.profile_controls",
        )
        midpoint = np.asarray(source["from"]) + 0.5 * (np.asarray(source["to"]) - np.asarray(source["from"]))
        section_names = {
            "upper_arm": ("pre-joint", "joint"),
            "forearm": ("proximal", "distal"),
            "thigh": ("pre-joint", "joint"),
            "shin": ("pre-joint", "joint"),
        }[role]
        sections = (
            _LimbSection(
                section_names[0],
                _guide_path(start, midpoint, (profile_controls[0], profile_controls[1]), f"{_key_text(desc.key)}.{section_names[0]}"),
                (profile_controls[0], profile_controls[1]),
                str(source["name"]),
            ),
            _LimbSection(
                section_names[1],
                _guide_path(midpoint, end, (profile_controls[1], profile_controls[2]), f"{_key_text(desc.key)}.{section_names[1]}"),
                (profile_controls[1], profile_controls[2]),
                str(source["name"]),
            ),
        )
        root_centerline = None
        root_thickness = None
        hip_centerline = None
        hip_thickness = None
        hip_center = None
        hip_radii = None
        shoulder_center = None
        shoulder_radii = None
        parent = by_key.get(desc.parent) if desc.parent is not None else None
        radius = _radius_from_shape(source)
        if role in {"upper_arm", "thigh"} and parent is not None:
            if role == "upper_arm":
                anchor = _torso_cage_boundary_anchor(
                    torso_cage,
                    float(source["from"][1]),
                    np.asarray(source["from"], dtype=np.float64) - np.asarray(torso_cage.upper_boundary.center, dtype=np.float64),
                )
            else:
                anchor = _torso_cage_boundary_anchor(
                    torso_cage,
                    float(source["from"][1]),
                    np.asarray(source["from"], dtype=np.float64) - np.asarray(torso_cage.lower_boundary.center, dtype=np.float64),
                )
            # The guide retains the exact cage boundary anchor.  Compilation
            # embeds the connector by this restrained support radius so the
            # branch meets the torso instead of projecting a round shelf.
            root_centerline = _guide_path(anchor, start, (radius * 0.82, radius * 0.68), f"{_key_text(desc.key)}.root")
            root_thickness = (radius * 0.82, radius * 0.68)
            if role == "thigh":
                transition_end = source["from"] + 0.35 * (source["to"] - source["from"])
                hip_centerline = _guide_path(anchor, transition_end, (radius * 0.78, radius * 0.66), f"{_key_text(desc.key)}.hip")
                hip_thickness = (radius * 0.78, radius * 0.66)
                hip_center = _guide_point(
                    anchor,
                    f"{_key_text(desc.key)}.hip_center",
                )
                hip_radii = _guide_radii(
                    radius * np.asarray([1.12, 0.98, 1.08]),
                    f"{_key_text(desc.key)}.hip_radii",
                )
        if role == "upper_arm":
            shoulder_anchor = _torso_cage_boundary_anchor(
                torso_cage,
                float(source["from"][1]),
                np.asarray(source["from"], dtype=np.float64) - np.asarray(torso_cage.upper_boundary.center, dtype=np.float64),
            )
            shoulder_center = _guide_point(shoulder_anchor, f"{_key_text(desc.key)}.shoulder_center")
            # Keep this as a compact root control, not a second shoulder
            # ellipsoid capable of recreating the old lateral shelf.
            shoulder_radii = _guide_radii(radius * np.asarray([0.88, 1.02, 0.94]), f"{_key_text(desc.key)}.shoulder_radii")

        joint = None
        if role in {"upper_arm", "thigh", "shin"}:
            joint_name = {"upper_arm": "elbow", "thigh": "knee", "shin": "hock"}[role]
            side = desc.key[1]
            adjacent_role = {"upper_arm": "forearm", "thigh": "shin", "shin": "foot"}[role]
            adjacent = by_role.get((side, adjacent_role))
            if adjacent is None:
                _fail(f"missing adjacent source geometry for {_key_text(desc.key)}.{joint_name}")
            adjacent_source = _source_shape(adjacent, form.reference_scale)
            if adjacent_role == "foot":
                _, foot_profile = _derive_foot_chain_profile(
                    adjacent_source["radii"],
                    f"{_key_text(desc.key)}.foot_chain",
                )
                adjacent_profile = foot_profile[0]
            else:
                adjacent_profile = float(_LIMB_PROFILE_FACTORS[adjacent_role][0]) * _radius_from_shape(adjacent_source)
            own_profile = profile_controls[-1]
            adjacent_profiles = (own_profile, adjacent_profile)
            joint_radius = 0.70 * min(adjacent_profiles)
            joint = _LimbJoint(
                joint_name,
                end,
                _guide_radii((joint_radius, joint_radius, joint_radius), f"{_key_text(desc.key)}.{joint_name}.radii"),
                adjacent_profiles,
            )
        limb_guides.append(
            _LimbGuide(
                owner=desc,
                sections=sections,
                joint=joint,
                root_centerline=root_centerline,
                root_thickness=root_thickness,
                hip_centerline=hip_centerline,
                hip_thickness=hip_thickness,
                hip_center=hip_center,
                hip_radii=hip_radii,
                shoulder_center=shoulder_center,
                shoulder_radii=shoulder_radii,
                axes=_FIXED_GUIDE_AXES,
            )
        )

    shoulder_frame = _derive_shoulder_frame(form, torso_cage, head_guide, tuple(limb_guides))

    paw_guides: list[_PawGuide] = []
    limb_by_owner = {item.owner.key: item for item in limb_guides}
    for desc in descriptors:
        role = desc.key[3]
        if role not in {"hand", "foot"}:
            continue
        source = _source_shape(desc, form.reference_scale)
        if source["name"] != "ellipsoid":
            _fail(f"paw source is not an ellipsoid for {_key_text(desc.key)}")
        if role == "hand":
            paw_center = _guide_point(source["center"] + np.asarray([0.0, 0.0, 0.10 * source["radii"][2]]), f"{_key_text(desc.key)}.paw_center")
            paw_radii = _guide_radii(source["radii"] * np.asarray([1.08, 0.94, 1.22]), f"{_key_text(desc.key)}.paw_radii")
            foot_chain = None
        else:
            # The hock already owns the proximal joint; derive the foot chain
            # from the source proportions and a guide-only contact datum.
            parent = by_key.get(desc.parent) if desc.parent is not None else None
            parent_limb = None if parent is None else limb_by_owner.get(parent.key)
            if parent is None or parent.key[3] != "shin" or parent_limb is None or parent_limb.joint is None or parent_limb.joint.name != "hock":
                _fail(f"digitigrade foot is missing its shin-owned hock for {_key_text(desc.key)}")
            hock = parent_limb.joint
            hock_anchor = _guide_point(hock.center, f"{_key_text(desc.key)}.foot_chain.hock_anchor")
            hock_radii = _guide_radii(hock.radii, f"{_key_text(desc.key)}.foot_chain.hock_radii")
            source_center = np.asarray(source["center"], dtype=np.float64)
            source_radii = np.asarray(source["radii"], dtype=np.float64)
            contact_height = float(source_center[1] - source_radii[1])
            pad_radii, metatarsal_profile = _derive_foot_chain_profile(
                source_radii,
                f"{_key_text(desc.key)}.foot_chain",
            )
            pad_center = _guide_point(
                np.asarray([source_center[0], contact_height + pad_radii[1], hock_anchor[2] + 0.34 * source_radii[2]]),
                f"{_key_text(desc.key)}.foot_chain.pad_center",
            )
            toe_radii = _guide_radii(
                source_radii * np.asarray([0.92, 0.28, 0.30]),
                f"{_key_text(desc.key)}.foot_chain.toe_radii",
            )
            toe_center = _guide_point(
                np.asarray([source_center[0], contact_height + toe_radii[1], pad_center[2] + 0.54 * source_radii[2]]),
                f"{_key_text(desc.key)}.foot_chain.toe_center",
            )
            if metatarsal_profile[0] != hock.adjacent_profiles[1]:
                _fail(f"{_key_text(desc.key)}.foot_chain profile does not bind its shin-owned hock")
            metatarsal_centerline = _guide_path(
                hock_anchor,
                pad_center,
                metatarsal_profile,
                f"{_key_text(desc.key)}.foot_chain.metatarsal_centerline",
            )
            foot_chain = _FootChainGuide(
                hock_anchor=hock_anchor,
                hock_radii=hock_radii,
                metatarsal_centerline=metatarsal_centerline,
                metatarsal_profile=metatarsal_profile,
                pad_center=pad_center,
                pad_radii=pad_radii,
                toe_center=toe_center,
                toe_radii=toe_radii,
                contact_height=contact_height,
                axes=_FIXED_GUIDE_AXES,
            )
            paw_center = None
            paw_radii = None
        parent = by_key.get(desc.parent) if desc.parent is not None else None
        attachment_centerline = None
        attachment_radius = None
        attachment_kind = None
        if parent is not None:
            if role == "hand":
                parent_source = _source_shape(parent, form.reference_scale)
                assert paw_center is not None
                attachment_start = _parent_surface_anchor(parent, paw_center, form.reference_scale)
                attachment_centerline = _guide_path(
                    attachment_start,
                    paw_center,
                    (max(_radius_from_shape(parent_source) * 0.72, float(np.min(source["radii"])) * 0.62),),
                    f"{_key_text(desc.key)}.attachment",
                )
                attachment_radius = max(_radius_from_shape(parent_source) * 0.72, float(np.min(source["radii"])) * 0.62)
                attachment_kind = "capsule"
        paw_guides.append(
            _PawGuide(
                owner=desc,
                paw_center=paw_center,
                paw_radii=paw_radii,
                foot_chain=foot_chain,
                attachment_centerline=attachment_centerline,
                attachment_radius=attachment_radius,
                attachment_kind=attachment_kind,
                axes=_FIXED_GUIDE_AXES,
            )
        )

    tail_guides: list[_TailGuide] = []
    for desc in descriptors:
        role = desc.key[3]
        if role not in {"tail_root", "tail_tip"}:
            continue
        source = path_source(desc)
        start = _guide_point(source["from"], f"{_key_text(desc.key)}.start")
        end = _guide_point(source["to"], f"{_key_text(desc.key)}.end")
        extension_centerline = None
        extension_taper = None
        cap_center = None
        cap_radii = None
        root_attachment_centerline = None
        root_attachment_taper = None
        root_collar_center = None
        root_collar_radii = None
        if role == "tail_tip":
            axis = source["to"] - source["from"]
            extension_end = source["to"] + 0.50 * axis
            extension_centerline = _guide_path(source["to"], extension_end, (float(source["r0"]) * 0.90, float(source["r0"]) * 0.55), f"{_key_text(desc.key)}.extension")
            extension_taper = (float(source["r0"]) * 0.90, float(source["r0"]) * 0.55)
            cap_center = _guide_point(extension_end, f"{_key_text(desc.key)}.cap_center")
            cap_radii = _guide_radii((float(source["r0"]) * 0.70,) * 3, f"{_key_text(desc.key)}.cap_radii")
            taper = (float(source["r0"]) * 1.35, float(source["r0"]) * 0.90)
        else:
            taper = (float(source["r0"]) * 1.15, float(source["r1"]) * 1.35)
            parent = by_key.get(desc.parent) if desc.parent is not None else None
            if parent is not None:
                anchor = _parent_surface_anchor(parent, source["to"], form.reference_scale)
                root_attachment_centerline = _guide_path(anchor, source["to"], (float(source["r0"]) * 1.28, float(source["r0"])), f"{_key_text(desc.key)}.root_attachment")
                root_attachment_taper = (float(source["r0"]) * 1.28, float(source["r0"]))
                root_collar_center = _guide_point(source["to"], f"{_key_text(desc.key)}.root_collar_center")
                root_collar_radii = _guide_radii(source["r1"] * np.asarray([1.50, 1.50, 1.80]), f"{_key_text(desc.key)}.root_collar_radii")
        tail_guides.append(
            _TailGuide(
                owner=desc,
                centerline=_guide_path(start, end, taper, f"{_key_text(desc.key)}.centerline"),
                taper=taper,
                extension_centerline=extension_centerline,
                extension_taper=extension_taper,
                cap_center=cap_center,
                cap_radii=cap_radii,
                root_attachment_centerline=root_attachment_centerline,
                root_attachment_taper=root_attachment_taper,
                root_collar_center=root_collar_center,
                root_collar_radii=root_collar_radii,
                axes=_FIXED_GUIDE_AXES,
            )
        )

    return _HybridGuide(
        topology=_guide_topology(descriptors),
        source_descriptors=descriptors,
        axial_guides=tuple(axial_guides),
        torso_cage=torso_cage,
        shoulder_frame=shoulder_frame,
        head_guide=head_guide,
        limb_guides=tuple(limb_guides),
        paw_guides=tuple(paw_guides),
        tail_guides=tuple(tail_guides),
    )


def _guide_point_checked(
    value: tuple[float, float, float],
    where: str,
    bounds: tuple[np.ndarray, np.ndarray] | None,
) -> tuple[float, float, float]:
    point = _guide_point(value, where)
    if bounds is not None:
        lower, upper = bounds
        if any(float(item) < float(lower[index]) or float(item) > float(upper[index]) for index, item in enumerate(point)):
            _fail(f"{where} is outside the shared guide bounds")
    return point


def _guide_mass_checked(
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
    where: str,
    bounds: tuple[np.ndarray, np.ndarray] | None,
) -> None:
    _guide_radii(radii, f"{where}.radii")
    centre = _guide_point_checked(center, f"{where}.center", bounds)
    if bounds is not None:
        lower, upper = bounds
        for index, radius in enumerate(radii):
            if centre[index] - radius < float(lower[index]) or centre[index] + radius > float(upper[index]):
                _fail(f"{where} extends outside the shared guide bounds")


def _guide_masses_overlap(
    first_center: tuple[float, float, float],
    first_radii: tuple[float, float, float],
    second_center: tuple[float, float, float],
    second_radii: tuple[float, float, float],
    where: str,
) -> None:
    """Require positive AABB overlap for fixed-axis ellipsoid connection."""

    if any(
        abs(first_center[index] - second_center[index])
        >= first_radii[index] + second_radii[index]
        for index in range(3)
    ):
        _fail(f"{where} masses must overlap on every fixed guide axis")


def _guide_path_checked(
    path: tuple[tuple[float, float, float], tuple[float, float, float]],
    profile: tuple[float, ...],
    where: str,
    bounds: tuple[np.ndarray, np.ndarray] | None,
) -> None:
    _guide_path(path[0], path[1], profile, where)
    for index, point in enumerate(path):
        _guide_point_checked(point, f"{where}.point[{index}]", bounds)
    if bounds is not None:
        lower, upper = bounds
        radius = max(profile)
        for point in path:
            if any(point[index] - radius < float(lower[index]) or point[index] + radius > float(upper[index]) for index in range(3)):
                _fail(f"{where} thickness extends outside the shared guide bounds")


def _guide_curve_checked(
    points: tuple[tuple[float, float, float], ...],
    profile: tuple[float, ...],
    where: str,
    bounds: tuple[np.ndarray, np.ndarray] | None,
) -> None:
    _guide_curve(tuple(points), profile, where)
    if bounds is not None:
        lower, upper = bounds
        radius = max(profile)
        for index, point in enumerate(points):
            _guide_point_checked(point, f"{where}.point[{index}]", bounds)
            if any(point[axis] - radius < float(lower[axis]) or point[axis] + radius > float(upper[axis]) for axis in range(3)):
                _fail(f"{where} thickness extends outside the shared guide bounds")


def _validate_hybrid_guide(guide: _HybridGuide, bounds: tuple[np.ndarray, np.ndarray] | None = None) -> None:
    """Validate guide controls before either field compilation or rendering.

    This deliberately walks only the private regional controls.  It never
    inspects a Descriptor shape, so the guide artifact and guide renderer
    cannot accidentally become a second descriptor/field projection.
    """

    def mass(center: tuple[float, float, float] | None, radii: tuple[float, float, float] | None, where: str) -> None:
        if (center is None) != (radii is None):
            _fail(f"{where} center/radii controls must be paired")
        if center is not None and radii is not None:
            _guide_mass_checked(center, radii, where, bounds)

    def path(path: tuple[tuple[float, float, float], tuple[float, float, float]] | None, profile: tuple[float, ...] | None, where: str) -> None:
        if (path is None) != (profile is None):
            _fail(f"{where} path/profile controls must be paired")
        if path is not None and profile is not None:
            _guide_path_checked(path, profile, where, bounds)

    cage = guide.torso_cage
    expected_cage_names = (
        "lower-pelvis",
        "upper-pelvis",
        "lower-abdomen",
        "waist-abdomen",
        "upper-abdomen",
        "lower-ribcage",
        "upper-ribcage-shoulder",
    )
    if tuple(section.name for section in cage.sections) != expected_cage_names:
        _fail("torso cage sections have unstable topology or order")
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    if cage.pelvis_owner.key not in source_by_key or cage.torso_owner.key not in source_by_key:
        _fail("torso cage owners must remain source descriptors")
    if any(source_by_key[owner.key] is not owner for owner in cage.source_owners):
        _fail("torso cage ownership must retain descriptor identity")
    if cage.pelvis_owner.key[3] != "pelvis" or cage.torso_owner.key[3] != "torso":
        _fail("torso cage owners must be the pelvis and torso descriptors")
    expected_section_owners = (
        cage.pelvis_owner,
        cage.pelvis_owner,
        cage.torso_owner,
        cage.torso_owner,
        cage.torso_owner,
        cage.torso_owner,
        cage.torso_owner,
    )
    for index, section in enumerate(cage.sections):
        if not any(section.owner is owner for owner in cage.source_owners):
            _fail(f"torso-cage[{index}] has an unexpected owner")
        if section.owner is not expected_section_owners[index]:
            _fail(f"torso-cage[{index}] has an invalid source owner")
        if not all(
            math.isfinite(value) and value > 0.0
            for value in (
                section.lateral_radius,
                section.anterior_radius,
                section.posterior_radius,
                section.depth_radius,
            )
        ):
            _fail(f"torso-cage[{index}] radii must be finite and positive")
        if not math.isclose(
            section.depth_radius,
            0.5 * (section.anterior_radius + section.posterior_radius),
            rel_tol=0.0,
            abs_tol=GUIDE_TOLERANCE,
        ):
            _fail(f"torso-cage[{index}] baseline depth is not bound to both authored sides")
        for control_name, control in (
            ("lateral", section.lateral_lineage),
            ("anterior", section.anterior_lineage),
            ("posterior", section.posterior_lineage),
        ):
            expected_factor = _display_factors(
                section.owner.profile_id,
                section.owner.key[3],
                "ellipsoid",
            )[0 if control_name == "lateral" else 2]
            expected_role = TORSO_PROFILE_DIMENSION_PREFIX + section.name.replace("-", "_") + "_" + {
                "lateral": TORSO_PROFILE_DIMENSION_SUFFIXES[0],
                "anterior": TORSO_PROFILE_DIMENSION_SUFFIXES[1],
                "posterior": TORSO_PROFILE_DIMENSION_SUFFIXES[2],
            }[control_name]
            if control.consumed_section != section.name or control.base <= 0 or control.factor != expected_factor or control.scaled != control.base * control.factor // 1000:
                _fail(f"torso-cage[{index}].{control_name} lineage is invalid")
            if control.reference != (section.owner.key, expected_role):
                _fail(f"torso-cage[{index}].{control_name} lineage lost source ownership")
            if set(control.provenance) != {"source", "document", "namespace"}:
                _fail(f"torso-cage[{index}].{control_name} lineage provenance is invalid")
        if section.landmark.owner != section.owner.key or section.frame.role != TORSO_PROFILE_FRAME_ROLE:
            _fail(f"torso-cage[{index}] frame/landmark ownership is invalid")
        _guide_point_checked(section.center, f"torso-cage[{index}].center", bounds)
    if cage.axes != guide.topology.axes or cage.axes != _FIXED_GUIDE_AXES:
        _fail("torso cage axes must match the guide topology and fixed prototype axes")
    _validate_regional_route_order(
        tuple(section.center for section in cage.sections),
        REGIONAL_ROUTE_ORDER_TORSO,
        "torso-cage.sections",
    )

    frame = guide.shoulder_frame
    if frame.axes != guide.topology.axes or frame.axes != _FIXED_GUIDE_AXES:
        _fail("shoulder frame axes must match the guide topology and fixed prototype axes")
    if frame.torso_owner is not cage.torso_owner or frame.neck_owner is not guide.head_guide.neck_owner:
        _fail("shoulder frame central owners must retain torso and neck descriptor identity")
    if frame.torso_owner.key[3] != "torso" or frame.neck_owner.key[3] != "neck":
        _fail("shoulder frame central owners must be torso and neck descriptors")
    _guide_point_checked(frame.central_anchor, "shoulder-frame.central-anchor", bounds)
    _guide_profile(frame.central_profile, "shoulder-frame.central-profile")
    if len(frame.central_profile) != 2:
        _fail("shoulder-frame central profile has unstable topology")
    if frame.central_anchor != guide.head_guide.neck_transition[0]:
        _fail("shoulder frame central anchor must equal the neck-base guide anchor")
    if len(frame.sides) != 2 or tuple(item.side for item in frame.sides) != ("left", "right"):
        _fail("shoulder frame sides must be ordered left then right")
    limb_by_key = {item.owner.key: item for item in guide.limb_guides if item.owner.key[3] == "upper_arm"}
    if len(limb_by_key) != 2:
        _fail("shoulder frame requires two source-owned upper-arm guides")
    for index, side in enumerate(frame.sides):
        where = f"shoulder-frame[{index}]"
        limb = limb_by_key.get(side.owner.key)
        if limb is None or limb.owner is not side.owner or side.owner.key[1] != (side.side,):
            _fail(f"{where} owner must be the matching source upper-arm descriptor")
        if limb.root_centerline is None or limb.root_thickness is None:
            _fail(f"{where} upper-arm root controls are missing")
        socket = limb.sections[0].centerline[0]
        if side.socket_anchor != socket:
            _fail(f"{where} socket anchor must equal the existing upper-arm source start")
        if side.shoulder_extremum != side.peak_anchor:
            _fail(f"{where} shoulder extremum must equal the authored peak anchor")
        if side.authored_peak.owner != side.owner.key or side.authored_axilla.owner != side.owner.key:
            _fail(f"{where} authored landmarks must retain upper-arm source ownership")
        if side.authored_frame.owner != side.owner.key or side.authored_frame.role != "form_shoulder_control":
            _fail(f"{where} authored frame must retain the matching upper-arm source ownership")
        if side.authored_peak.frame != (side.authored_frame.owner, side.authored_frame.role) or side.authored_axilla.frame != (side.authored_frame.owner, side.authored_frame.role):
            _fail(f"{where} authored landmarks must reference the matching identity frame")
        if side.authored_frame.translation != (0.0, 0.0, 0.0) or side.authored_frame.rotation_xyzw != (0.0, 0.0, 0.0, 1.0):
            _fail(f"{where} authored shoulder frame must remain identity-only")
        if not math.isclose(side.authored_peak.position[0], side.authored_axilla.position[0], rel_tol=0.0, abs_tol=GUIDE_TOLERANCE):
            _fail(f"{where} authored landmarks must share local lateral coordinate")
        expected_sign = -1.0 if side.side == "left" else 1.0
        if any(point[0] * expected_sign <= 0.0 for point in (side.peak_anchor, side.axilla_anchor, side.socket_anchor)):
            _fail(f"{where} authored shoulder controls must remain on the owner side")
        if side.peak_anchor[1] <= side.axilla_anchor[1] + GUIDE_TOLERANCE:
            _fail(f"{where} authored peak must remain above axilla")
        expected_midpoint = 0.5 * (side.peak_anchor[1] + side.axilla_anchor[1])
        expected_radius = 0.5 * (side.peak_anchor[1] - side.axilla_anchor[1])
        if not math.isclose(side.vertical_midpoint, expected_midpoint, rel_tol=0.0, abs_tol=GUIDE_TOLERANCE) or not math.isclose(side.vertical_radius, expected_radius, rel_tol=0.0, abs_tol=GUIDE_TOLERANCE) or side.vertical_radius <= GUIDE_TOLERANCE:
            _fail(f"{where} authored vertical midpoint/radius are invalid")
        expected_depth_factor = _shoulder_depth_factor(side.owner.profile_id)
        if side.depth_profile_factor != expected_depth_factor or side.depth_scaled_permille != _scaled_display_value(side.depth_value_permille, expected_depth_factor, f"{where}.depth") or not math.isclose(side.depth_radius, side.depth_scaled_permille / 1000.0, rel_tol=0.0, abs_tol=GUIDE_TOLERANCE) or side.depth_radius <= GUIDE_TOLERANCE:
            _fail(f"{where} authored shoulder depth radius is invalid")
        expected_span = abs(float(side.peak_anchor[0] - frame.central_anchor[0]))
        if not math.isfinite(expected_span) or expected_span <= 0.0:
            _fail(f"{where} derived shoulder span is invalid")
        expected_slope = (float(side.peak_anchor[1]) - float(frame.central_anchor[1])) / expected_span
        if not math.isclose(side.span, expected_span, rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(side.slope, expected_slope, rel_tol=1.0e-9, abs_tol=1.0e-12):
            _fail(f"{where} span and slope are not derived from authored shoulder controls")
        if not math.isfinite(side.span) or side.span <= 0.0 or not math.isfinite(side.slope):
            _fail(f"{where} span and slope must be finite")
        for curve_name, curve in (
            ("anterior", side.anterior_support),
            ("posterior", side.posterior_return),
            ("deltoid", side.deltoid_sweep),
        ):
            curve_where = f"{where}.{curve_name}"
            expected_name = {"anterior": "anterior-support", "posterior": "posterior-return", "deltoid": "deltoid-sweep"}[curve_name]
            expected_controls = 3 if curve_name == "deltoid" else 4
            if curve.name != expected_name or len(curve.points) != expected_controls or len(curve.profile) != expected_controls:
                _fail(f"{curve_where} has unstable name or topology")
            if curve.axes != frame.axes:
                _fail(f"{curve_where} axes must match the shoulder frame")
            if curve_name in {"anterior", "posterior"} and curve.owner is not frame.torso_owner:
                _fail(f"{curve_where} must be torso-owned")
            if curve_name == "deltoid" and curve.owner is not side.owner:
                _fail(f"{curve_where} must be upper-arm-owned")
            _guide_curve_checked(curve.points, curve.profile, curve_where, bounds)
        for curve in (side.anterior_support, side.posterior_return):
            if curve.points[0] != frame.central_anchor or curve.points[2] != side.shoulder_extremum or curve.points[-1] != side.socket_anchor:
                _fail(f"{where} support curves must join central, extremum, and socket controls")
        if not math.isclose(side.anterior_support.profile[0], frame.central_profile[0], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(side.posterior_return.profile[0], frame.central_profile[1], rel_tol=1.0e-9, abs_tol=1.0e-12):
            _fail(f"{where} support profiles must join the central trapezius profile")
        if side.anterior_support.profile[1:] != side.posterior_return.profile[1:]:
            _fail(f"{where} anterior and posterior support profiles must rejoin identically")
        if not math.isclose(side.anterior_support.profile[-1], limb.sections[0].thickness[0], rel_tol=1.0e-9, abs_tol=1.0e-12):
            _fail(f"{where} support profile must overlap the upper-arm root profile")
        expected_wrap = np.asarray((side.peak_anchor[0], side.vertical_midpoint, 0.5 * (side.peak_anchor[2] + side.axilla_anchor[2])), dtype=np.float64)
        if not np.allclose(side.anterior_support.points[1], expected_wrap + np.asarray(frame.axes.forward) * side.depth_radius, rtol=0.0, atol=GUIDE_TOLERANCE) or not np.allclose(side.posterior_return.points[1], expected_wrap - np.asarray(frame.axes.forward) * side.depth_radius, rtol=0.0, atol=GUIDE_TOLERANCE):
            _fail(f"{where} support wraps are not derived from authored shoulder depth")
        if side.anterior_support.points[1][2] <= side.shoulder_extremum[2] or side.posterior_return.points[1][2] >= side.shoulder_extremum[2]:
            _fail(f"{where} anterior and posterior wraps must occupy distinct depth")
        first_quarter = np.asarray(limb.sections[0].centerline[0]) + 0.25 * (
            np.asarray(limb.sections[0].centerline[1]) - np.asarray(limb.sections[0].centerline[0])
        )
        if side.deltoid_sweep.points[0] != side.shoulder_extremum or side.deltoid_sweep.points[1] != side.socket_anchor or not np.allclose(side.deltoid_sweep.points[2], first_quarter, rtol=0.0, atol=1.0e-12):
            _fail(f"{where} deltoid sweep must overlap the root and first quarter of the upper-arm guide")
        if not math.isclose(side.deltoid_sweep.profile[0], side.anterior_support.profile[2], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(side.deltoid_sweep.profile[1], limb.sections[0].thickness[0], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(side.deltoid_sweep.profile[2], limb.sections[0].thickness[1], rel_tol=1.0e-9, abs_tol=1.0e-12):
            _fail(f"{where} deltoid profile must overlap the root and upper-arm guide profiles")

    for index, axial in enumerate(guide.axial_guides):
        mass(axial.girdle_center, axial.girdle_radii, f"axial[{index}].girdle")
        mass(axial.pelvic_core_center, axial.pelvic_core_radii, f"axial[{index}].pelvic_core")
        mass(axial.chest_center, axial.chest_radii, f"axial[{index}].chest")
        mass(axial.waist_center, axial.waist_radii, f"axial[{index}].waist")
        path(axial.trunk_centerline, axial.trunk_thickness, f"axial[{index}].trunk")
        for station_index, station in enumerate(axial.stations):
            if station.name not in {"pelvic-girdle", "waist", "chest-girdle"}:
                _fail(f"axial[{index}].stations[{station_index}] has an unknown station")
            _guide_mass_checked(station.center, station.radii, f"axial[{index}].stations[{station_index}]", bounds)
        for transition_index, transition in enumerate(axial.transitions):
            if transition.name not in {"pelvis-waist", "waist-chest"}:
                _fail(f"axial[{index}].transitions[{transition_index}] has an unknown transition")
            _guide_path_checked(transition.centerline, transition.thickness, f"axial[{index}].transitions[{transition_index}]", bounds)
    stations = tuple(station for axial in guide.axial_guides for station in axial.stations)
    if tuple(station.name for station in stations) != ("pelvic-girdle", "waist", "chest-girdle"):
        _fail("axial stations must be ordered pelvic-girdle, waist, chest-girdle")
    if any(stations[index].center[1] >= stations[index + 1].center[1] for index in range(len(stations) - 1)):
        _fail("axial stations must rise monotonically from pelvis to chest")
    transitions = tuple(transition for axial in guide.axial_guides for transition in axial.transitions)
    if tuple(transition.name for transition in transitions) != ("pelvis-waist", "waist-chest"):
        _fail("axial transitions must be ordered pelvis-waist, waist-chest")
    head = guide.head_guide
    head_profile = head.profile
    if head_profile.axes != guide.topology.axes or head_profile.axes != _FIXED_GUIDE_AXES:
        _fail("head/neck profile axes must match the guide topology and fixed prototype axes")
    if tuple(section.name for section in head_profile.sections) != HEAD_NECK_PROFILE_SECTION_NAMES:
        _fail("head/neck profile stations have unstable topology or order")
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    for index, section in enumerate(head_profile.sections):
        where = f"head-neck[{index}]"
        if section.section_index != index or section.source_section_index != index:
            _fail(f"{where} source section indices are not exact")
        if section.owner.key not in source_by_key or source_by_key[section.owner.key] is not section.owner:
            _fail(f"{where} owner must retain descriptor identity")
        if section.owner.key[1] != () or section.owner.key[3] != HEAD_NECK_PROFILE_OWNER_ROLES[index]:
            _fail(f"{where} owner role is invalid")
        if section.frame.owner != section.owner.key or section.frame.role != HEAD_NECK_PROFILE_FRAME_ROLE:
            _fail(f"{where} frame ownership is invalid")
        if section.landmark.owner != section.owner.key or section.landmark.frame != (section.frame.owner, section.frame.role):
            _fail(f"{where} landmark/frame binding is invalid")
        if section.frame.translation != (0.0, 0.0, 0.0) or section.frame.rotation_xyzw != (0.0, 0.0, 0.0, 1.0):
            _fail(f"{where} control frame must remain identity-only")
        if section.landmark.position[0] != 0.0:
            _fail(f"{where} landmark must retain zero lateral source position")
        controls = (section.lateral_lineage, section.up_lineage, section.forward_lineage)
        for axis, control, suffix in zip(("lateral", "up", "forward"), controls, HEAD_NECK_PROFILE_DIMENSION_SUFFIXES):
            expected_factor = _head_neck_profile_factors(section.owner.profile_id, section.owner.key[3])[{"lateral": 0, "up": 1, "forward": 2}[axis]]
            expected_role = HEAD_NECK_PROFILE_DIMENSION_PREFIX + section.name.replace("-", "_") + "_" + suffix
            if control.consumed_section != section.name or control.base <= 0 or control.factor != expected_factor or control.scaled != control.base * control.factor // 1000:
                _fail(f"{where}.{axis} lineage is invalid")
            if control.reference != (section.owner.key, expected_role) or control.reference_index < 0:
                _fail(f"{where}.{axis} lineage lost source ownership or index")
            if set(control.provenance) != {"source", "document", "namespace"}:
                _fail(f"{where}.{axis} lineage provenance is invalid")
            if not math.isclose(section.radii[{"lateral": 0, "up": 1, "forward": 2}[axis]], control.scaled / 1000.0, rel_tol=0.0, abs_tol=GUIDE_TOLERANCE):
                _fail(f"{where}.{axis} radius was not retained from lineage")
        _guide_mass_checked(section.center, section.radii, f"{where}.station", bounds)
    _validate_regional_route_order(
        tuple(section.center for section in head_profile.sections),
        REGIONAL_ROUTE_ORDER_GUIDE_HEAD_NECK,
        "head-neck.sections",
    )
    expected_connections = tuple(HeadNeckConnection(*connection) for connection in HEAD_NECK_PROFILE_CONNECTIONS)
    if tuple(connection.spec for connection in head_profile.connections) != expected_connections:
        _fail("head/neck profile connections have unstable names, indices, or routes")
    for index, connection in enumerate(head_profile.connections):
        where = f"head-neck-connection[{index}]"
        from_section = head_profile.sections[connection.spec.from_section_index]
        to_section = head_profile.sections[connection.spec.to_section_index]
        if connection.from_section is not from_section or connection.to_section is not to_section:
            _fail(f"{where} lost exact station references")
        expected_thickness = (_head_neck_transition_radius(from_section), _head_neck_transition_radius(to_section))
        if connection.thickness != expected_thickness or connection.centerline != (from_section.center, to_section.center):
            _fail(f"{where} is not directly derived from its authored endpoints")
        _guide_path_checked(connection.centerline, connection.thickness, where, bounds)
    selected = {section.name: section for section in head_profile.sections}
    if head.cranium_center != selected["cranium-mid"].center or head.cranium_radii != selected["cranium-mid"].radii:
        _fail("head cranium compatibility controls must select cranium-mid directly")
    if head.muzzle_center != selected["muzzle-mid"].center or head.muzzle_radii != selected["muzzle-mid"].radii:
        _fail("head muzzle compatibility controls must select muzzle-mid directly")
    if head.head_transition != (selected["neck-upper"].center, selected["head-base"].center):
        _fail("head-base bridge compatibility path must select neck-upper to head-base")
    if head.head_transition_thickness != (
        _head_neck_transition_radius(selected["neck-upper"]),
        _head_neck_transition_radius(selected["head-base"]),
    ):
        _fail("head-base bridge thickness must be the direct endpoint-radius function")
    if head.neck_transition != (selected["neck-collar"].center, selected["neck-upper"].center):
        _fail("tapered-neck compatibility path must select neck-collar to neck-upper")
    if head.neck_transition_thickness != (
        _head_neck_transition_radius(selected["neck-collar"]),
        _head_neck_transition_radius(selected["neck-upper"]),
    ):
        _fail("tapered-neck thickness must be the direct endpoint-radius function")
    if head.neck_collar_center != selected["neck-collar"].center or head.neck_collar_radii != selected["neck-collar"].radii:
        _fail("neck-collar compatibility controls must select neck-collar directly")
    mass(head.cranium_center, head.cranium_radii, "head.cranium")
    mass(head.muzzle_center, head.muzzle_radii, "head.muzzle")
    path(head.head_transition, head.head_transition_thickness, "head.transition")
    path(head.neck_transition, head.neck_transition_thickness, "head.neck_transition")
    mass(head.neck_collar_center, head.neck_collar_radii, "head.neck_collar")
    for index, limb in enumerate(guide.limb_guides):
        if not limb.sections or len(limb.profile_controls) != 3:
            _fail(f"limb[{index}] must contain piecewise sections and three profile controls")
        _guide_profile(limb.profile_controls, f"limb[{index}].profile_controls")
        for section_index, section in enumerate(limb.sections):
            if section.name not in {"pre-joint", "joint", "proximal", "distal"}:
                _fail(f"limb[{index}].sections[{section_index}] has an unknown section")
            path(section.centerline, section.thickness, f"limb[{index}].sections[{section_index}]")
        if limb.joint is not None:
            if limb.joint.name not in {"elbow", "knee", "hock"}:
                _fail(f"limb[{index}].joint has an unknown station")
            mass(limb.joint.center, limb.joint.radii, f"limb[{index}].joint")
            if len(limb.joint.adjacent_profiles) != 2 or any(value <= 0.0 for value in limb.joint.adjacent_profiles):
                _fail(f"limb[{index}].joint adjacent profiles are invalid")
            if not math.isclose(limb.joint.radii[0], 0.70 * min(limb.joint.adjacent_profiles), rel_tol=1e-9, abs_tol=1e-12):
                _fail(f"limb[{index}].joint radius is not derived from adjacent profiles")
            if any(radius >= adjacent for radius in limb.joint.radii for adjacent in limb.joint.adjacent_profiles):
                _fail(f"limb[{index}].joint radius must be smaller than adjacent profiles")
        path(limb.root_centerline, limb.root_thickness, f"limb[{index}].root")
        path(limb.hip_centerline, limb.hip_thickness, f"limb[{index}].hip")
        mass(limb.hip_center, limb.hip_radii, f"limb[{index}].hip_girdle")
        mass(limb.shoulder_center, limb.shoulder_radii, f"limb[{index}].shoulder")
    limb_by_owner = {item.owner.key: item for item in guide.limb_guides}
    for index, paw in enumerate(guide.paw_guides):
        mass(paw.paw_center, paw.paw_radii, f"paw[{index}].paw")
        if paw.owner.key[3] == "hand":
            if paw.foot_chain is not None:
                _fail(f"paw[{index}] hand must not contain a foot chain")
        elif paw.owner.key[3] == "foot":
            if paw.paw_center is not None or paw.paw_radii is not None:
                _fail(f"paw[{index}] foot must not contain a hand paw mass")
            if paw.foot_chain is None:
                _fail(f"paw[{index}] foot is missing its private chain")
        else:
            _fail(f"paw[{index}] has an unsupported source role")
        if paw.foot_chain is not None:
            chain = paw.foot_chain
            where = f"paw[{index}].foot_chain"
            if chain.axes != guide.topology.axes or chain.axes != _FIXED_GUIDE_AXES:
                _fail(f"{where} axes must match the fixed guide axes")
            _guide_mass_checked(chain.hock_anchor, chain.hock_radii, f"{where}.hock", bounds)
            _guide_path_checked(chain.metatarsal_centerline, chain.metatarsal_profile, f"{where}.metatarsal", bounds)
            _guide_mass_checked(chain.pad_center, chain.pad_radii, f"{where}.pad", bounds)
            _guide_mass_checked(chain.toe_center, chain.toe_radii, f"{where}.toe", bounds)
            if not math.isfinite(chain.contact_height):
                _fail(f"{where}.contact_height must be finite")
            parent_key = paw.owner.parent
            parent_limb = limb_by_owner.get(parent_key) if parent_key is not None else None
            if parent_limb is None or parent_limb.joint is None or parent_limb.joint.name != "hock":
                _fail(f"{where} must bind to a shin-owned hock")
            hock = parent_limb.joint
            if chain.hock_anchor != hock.center or chain.hock_radii != hock.radii:
                _fail(f"{where}.hock must retain the shin joint identity")
            start, metatarsal_end = chain.metatarsal_centerline
            if start != chain.hock_anchor:
                _fail(f"{where}.metatarsal must start at the hock anchor")
            if metatarsal_end[2] <= start[2] or metatarsal_end[1] >= start[1]:
                _fail(f"{where}.metatarsal must descend forward from the hock")
            if chain.pad_center[2] <= start[2] or chain.toe_center[2] <= chain.pad_center[2]:
                _fail(f"{where} controls must progress forward from hock to toe")
            if not chain.metatarsal_profile[0] > chain.metatarsal_profile[-1]:
                _fail(f"{where}.metatarsal must taper toward the pad")
            if not math.isclose(chain.pad_center[1] - chain.pad_radii[1], chain.contact_height, rel_tol=0.0, abs_tol=1.0e-12):
                _fail(f"{where}.pad must share the contact datum")
            if not math.isclose(chain.toe_center[1] - chain.toe_radii[1], chain.contact_height, rel_tol=0.0, abs_tol=1.0e-12):
                _fail(f"{where}.toe must share the contact datum")
            _guide_masses_overlap(
                chain.pad_center,
                chain.pad_radii,
                chain.toe_center,
                chain.toe_radii,
                f"{where}.pad-toe",
            )
            if paw.attachment_centerline is not None or paw.attachment_radius is not None or paw.attachment_kind is not None:
                _fail(f"{where} must not contain a legacy attachment bridge")
        if paw.attachment_centerline is not None:
            if paw.attachment_radius is None or paw.attachment_kind is None:
                _fail(f"paw[{index}].attachment controls are incomplete")
            path(paw.attachment_centerline, (float(paw.attachment_radius),), f"paw[{index}].attachment")
        elif paw.attachment_radius is not None or paw.attachment_kind is not None:
            _fail(f"paw[{index}].attachment controls are incomplete")
    for index, tail in enumerate(guide.tail_guides):
        path(tail.centerline, tail.taper, f"tail[{index}].centerline")
        path(tail.extension_centerline, tail.extension_taper, f"tail[{index}].extension")
        mass(tail.cap_center, tail.cap_radii, f"tail[{index}].cap")
        path(tail.root_attachment_centerline, tail.root_attachment_taper, f"tail[{index}].root_attachment")
        mass(tail.root_collar_center, tail.root_collar_radii, f"tail[{index}].root_collar")


def _point_json(value: tuple[float, float, float]) -> list[float]:
    return [float(item) for item in value]


def _mass_json(name: str, center: tuple[float, float, float] | None, radii: tuple[float, float, float] | None) -> dict[str, Any] | None:
    if center is None or radii is None:
        return None
    return {"control": name, "center": _point_json(center), "radii": _point_json(radii)}


def _path_json(
    name: str,
    path: tuple[tuple[float, float, float], tuple[float, float, float]] | None,
    profile: tuple[float, ...] | None,
    *,
    path_kind: str | None = None,
) -> dict[str, Any] | None:
    if path is None or profile is None:
        return None
    result: dict[str, Any] = {"control": name, "points": [_point_json(path[0]), _point_json(path[1])], "thickness": [float(item) for item in profile]}
    if path_kind is not None:
        result["path_kind"] = path_kind
    return result


def _curve_json(name: str, owner: Descriptor, curve: _ShoulderCurve) -> dict[str, Any]:
    """Serialize every private shoulder curve, including uncompiled spans.

    Support curves remain inspectable guide controls, but this disposable
    analytic adapter does not consume them as skin fields.  The explicit
    consumption label keeps that boundary truthful in the sidecar.
    """

    return {
        "name": name,
        "owner": _address_json(owner.key),
        "points": [_point_json(point) for point in curve.points],
        "profile": [float(item) for item in curve.profile],
        "consumption": "skin-driving" if name == "deltoid-sweep" else "guide-only",
    }


def _authored_frame_json(frame: AuthoredFrame) -> dict[str, Any]:
    return {
        "owner": _address_json(frame.owner),
        "role": frame.role,
        "transform": {
            "translation": [float(item) for item in frame.translation],
            "rotation_xyzw": [float(item) for item in frame.rotation_xyzw],
        },
        "provenance": dict(frame.provenance),
    }


def _authored_landmark_json(landmark: AuthoredLandmark) -> dict[str, Any]:
    return {
        "owner": _address_json(landmark.owner),
        "role": landmark.role,
        "frame": {"owner": _address_json(landmark.frame[0]), "role": landmark.frame[1]},
        "position": [float(item) for item in landmark.position],
        "provenance": dict(landmark.provenance),
    }


def _torso_radius_lineage_json(lineage: _TorsoRadiusLineage) -> dict[str, Any]:
    return {
        "base": lineage.base,
        "factor": lineage.factor,
        "scaled": lineage.scaled,
        "reference": {
            "owner": _address_json(lineage.reference[0]),
            "role": lineage.reference[1],
            "index": lineage.reference_index,
        },
        "provenance": dict(lineage.provenance),
        "consumed_section": lineage.consumed_section,
    }


def _torso_section_json(section: _TorsoCageSection) -> dict[str, Any]:
    """Serialize authored controls and exact guide lineage for one section."""

    return {
        "name": section.name,
        "section_index": section.section_index,
        "frame_index": section.frame_index,
        "landmark_index": section.landmark_index,
        "owner": _address_json(section.owner.key),
        "frame": {
            "owner": _address_json(section.frame.owner),
            "role": section.frame.role,
        },
        "landmark": _authored_landmark_json(section.landmark),
        "center": _point_json(section.center),
        "lateral_radius": float(section.lateral_radius),
        "anterior_radius": float(section.anterior_radius),
        "posterior_radius": float(section.posterior_radius),
        "depth_radius": float(section.depth_radius),
        "lateral": _torso_radius_lineage_json(section.lateral_lineage),
        "anterior": _torso_radius_lineage_json(section.anterior_lineage),
        "posterior": _torso_radius_lineage_json(section.posterior_lineage),
        "lineage": {
            "lateral": _torso_radius_lineage_json(section.lateral_lineage),
            "anterior": _torso_radius_lineage_json(section.anterior_lineage),
            "posterior": _torso_radius_lineage_json(section.posterior_lineage),
        },
    }


def _head_neck_radius_lineage_json(lineage: _HeadNeckRadiusLineage) -> dict[str, Any]:
    return {
        "base": lineage.base,
        "factor": lineage.factor,
        "scaled": lineage.scaled,
        "reference": {
            "owner": _address_json(lineage.reference[0]),
            "role": lineage.reference[1],
            "index": lineage.reference_index,
        },
        "provenance": dict(lineage.provenance),
        "consumed_section": lineage.consumed_section,
    }


def _head_neck_section_json(section: _HeadNeckGuideSection) -> dict[str, Any]:
    lineage = {
        "lateral": _head_neck_radius_lineage_json(section.lateral_lineage),
        "up": _head_neck_radius_lineage_json(section.up_lineage),
        "forward": _head_neck_radius_lineage_json(section.forward_lineage),
    }
    return {
        "name": section.name,
        "section_index": section.section_index,
        "source_section_index": section.source_section_index,
        "frame_index": section.frame_index,
        "landmark_index": section.landmark_index,
        "owner": _address_json(section.owner.key),
        "frame": {"owner": _address_json(section.frame.owner), "role": section.frame.role},
        "landmark": _authored_landmark_json(section.landmark),
        "center": _point_json(section.center),
        "radii": {
            "lateral": float(section.radii[0]),
            "up": float(section.radii[1]),
            "forward": float(section.radii[2]),
        },
        "lateral_radius": float(section.radii[0]),
        "up_radius": float(section.radii[1]),
        "forward_radius": float(section.radii[2]),
        "lineage": lineage,
    }


def _head_neck_connection_json(connection: _HeadNeckGuideConnection) -> dict[str, Any]:
    spec = connection.spec
    return {
        "name": spec.name,
        "from_section_index": spec.from_section_index,
        "to_section_index": spec.to_section_index,
        "route": spec.route,
        "from": {"name": connection.from_section.name, "owner": _address_json(connection.from_section.owner.key)},
        "to": {"name": connection.to_section.name, "owner": _address_json(connection.to_section.owner.key)},
        "path": _path_json(spec.name, connection.centerline, connection.thickness, path_kind="tapered-segment"),
    }


def _shoulder_source_control_json(side: _ShoulderSideGuide) -> dict[str, Any]:
    """Return the exact authored records and consumed dimension lineage."""

    depth_control = {
        "owner": _address_json(side.owner.key),
        "role": "form_shoulder_depth_radius",
        "value_permille": side.depth_value_permille,
        "scaled_value_permille": side.depth_scaled_permille,
        "profile_factor": side.depth_profile_factor,
        "provenance": dict(side.depth_provenance),
        "consumption": "guide-derived shoulder wrap depth; baseline field remains guide-only",
    }
    return {
        "side": side.side,
        "owner": _address_json(side.owner.key),
        "frame": _authored_frame_json(side.authored_frame),
        "landmarks": [
            _authored_landmark_json(side.authored_axilla),
            _authored_landmark_json(side.authored_peak),
        ],
        "depth_control": depth_control,
    }


def _shoulder_source_controls_json(frame: _ShoulderFrame) -> list[dict[str, Any]]:
    return [_shoulder_source_control_json(side) for side in frame.sides]


def _projection_json() -> list[dict[str, Any]]:
    return [
        {"name": name, "basis": [[float(item) for item in row] for row in basis], "base": base}
        for name, basis, base in PROJECTIONS
    ]


def _layout_json() -> dict[str, Any]:
    return {
        "panel_order": [item["id"] for item in PANEL_LAYOUT],
        "panels": [
            {"id": item["id"], "projection": item["projection"], "content": item["content"], "box": list(item["box"])}
            for item in PANEL_LAYOUT
        ],
        "pairing": "guide-left/skin-right per projection",
        "frame": "shared-world-bounds-and-projection-basis",
    }


def _regional_guide_json(
    variant_id: str,
    guide: _HybridGuide,
    shared_render_bounds: tuple[np.ndarray, np.ndarray],
    compiled_fields: tuple[Field, ...] | None = None,
) -> dict[str, Any]:
    _validate_hybrid_guide(guide, shared_render_bounds)
    if compiled_fields is None:
        compiled_fields = _compile_hybrid_guide(guide)
    lower, upper = shared_render_bounds
    station_recipes = {
        "pelvic-girdle": "hips",
        "waist": "waist",
        "chest-girdle": "chest",
    }
    axial_core: dict[str, Any] | None = None
    stations: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    for item in guide.axial_guides:
        if item.pelvic_core_center is not None and item.pelvic_core_radii is not None:
            axial_core = {
                "owner": _address_json(item.owner.key),
                "recipe": "pelvic-core",
                "mass": _mass_json("pelvic-core", item.pelvic_core_center, item.pelvic_core_radii),
            }
        for station in item.stations:
            recipe = station_recipes[station.name]
            stations.append({
                "name": station.name,
                "owner": _address_json(item.owner.key),
                "recipe": recipe,
                "mass": _mass_json(station.name, station.center, station.radii),
            })
        for transition in item.transitions:
            recipe = transition.name + "-bridge"
            transitions.append({
                "name": transition.name,
                "owner": _address_json(item.owner.key),
                "recipe": recipe,
                "path": _path_json(transition.name, transition.centerline, transition.thickness, path_kind="tapered-segment"),
            })
    if axial_core is None:
        _fail("axial guide is missing the pelvic core control")
    axial_controls = {
        "status": "compatibility-diagnostic-not-rendered",
        "core": axial_core,
        "stations": stations,
        "transitions": transitions,
    }
    torso_cage = guide.torso_cage
    cage_axes = {
        "lateral": _point_json(torso_cage.axes.lateral),
        "up": _point_json(torso_cage.axes.up),
        "forward": _point_json(torso_cage.axes.forward),
    }
    torso_cage_controls = {
        "status": "skin-driving torso controls",
        "profile_format": AUTHORED_TORSO_PROFILE_FORMAT,
        "owners": [_address_json(torso_cage.pelvis_owner.key), _address_json(torso_cage.torso_owner.key)],
        "axes": cage_axes,
        "orientation": "elliptical cross-section rings lie in the lateral/forward plane and rise along the up axis",
        "sections": [_torso_section_json(section) for section in torso_cage.sections],
        "connections": [
            {"from": torso_cage.sections[index].name, "to": torso_cage.sections[index + 1].name}
            for index in range(len(torso_cage.sections) - 1)
        ],
    }
    frame = guide.shoulder_frame
    shoulder_sides = []
    for side in frame.sides:
        shoulder_sides.append({
            "side": side.side,
            "owner": _address_json(side.owner.key),
            "socket": {"owner": _address_json(side.owner.key), "point": _point_json(side.socket_anchor)},
            "extremum": {"owner": _address_json(side.owner.key), "point": _point_json(side.shoulder_extremum)},
            "authored_controls": {
                "peak": _authored_landmark_json(side.authored_peak),
                "axilla": _authored_landmark_json(side.authored_axilla),
                "frame": _authored_frame_json(side.authored_frame),
            },
            "peak_anchor": _point_json(side.peak_anchor),
            "axilla_anchor": _point_json(side.axilla_anchor),
            "vertical_midpoint": float(side.vertical_midpoint),
            "vertical_radius": float(side.vertical_radius),
            "depth_radius": float(side.depth_radius),
            "depth_control": _shoulder_source_control_json(side)["depth_control"],
            "span": float(side.span),
            "slope": float(side.slope),
            "curves": [
                _curve_json("anterior-support", frame.torso_owner, side.anterior_support),
                _curve_json("posterior-return", frame.torso_owner, side.posterior_return),
                _curve_json("deltoid-sweep", side.owner, side.deltoid_sweep),
            ],
        })
    shoulder_frame_controls = {
        "status": "private shoulder frame; support curves guide-only; deltoid sweep skin-driving",
        "owners": {
            "torso": _address_json(frame.torso_owner.key),
            "neck": _address_json(frame.neck_owner.key),
            "left_upper_arm": _address_json(frame.left.owner.key),
            "right_upper_arm": _address_json(frame.right.owner.key),
        },
        "central": {
            "owner": _address_json(frame.torso_owner.key),
            "anchor": _point_json(frame.central_anchor),
            "profile": [float(item) for item in frame.central_profile],
        },
        "source_controls": _shoulder_source_controls_json(frame),
        "sides": shoulder_sides,
    }
    head = guide.head_guide
    head_controls = {
        "owners": [_address_json(head.head_owner.key), _address_json(head.neck_owner.key)],
        "profile_format": AUTHORED_HEAD_NECK_PROFILE_FORMAT,
        "provenance": dict(head.profile.provenance),
        "sections": [_head_neck_section_json(section) for section in head.profile.sections],
        "connections": [_head_neck_connection_json(connection) for connection in head.profile.connections],
        "masses": [
            _mass_json("cranium", head.cranium_center, head.cranium_radii),
            _mass_json("muzzle", head.muzzle_center, head.muzzle_radii),
            _mass_json("neck-collar", head.neck_collar_center, head.neck_collar_radii),
        ],
        "paths": [
            value for value in (
                _path_json("head-transition", head.head_transition, head.head_transition_thickness),
                _path_json("neck-transition", head.neck_transition, head.neck_transition_thickness),
            ) if value is not None
        ],
    }
    limb_controls = []
    paw_by_parent: dict[tuple[str, tuple[str, ...], str, str], list[_PawGuide]] = {}
    for paw in guide.paw_guides:
        if paw.owner.parent is not None:
            paw_by_parent.setdefault(paw.owner.parent, []).append(paw)
    for item in guide.limb_guides:
        sections = [
            _path_json(section.name, section.centerline, section.thickness, path_kind=section.path_kind)
            for section in item.sections
        ]
        bridges = [
            value for value in (
                _path_json("root", item.root_centerline, item.root_thickness, path_kind="tapered-segment"),
                _path_json("hip", item.hip_centerline, item.hip_thickness, path_kind="tapered-segment"),
            ) if value is not None
        ]
        masses = [
            value for value in (
                _mass_json("shoulder-girdle", item.shoulder_center, item.shoulder_radii),
                _mass_json("hip-girdle", item.hip_center, item.hip_radii),
            ) if value is not None
        ]
        joints = []
        if item.joint is not None:
            joints.append({
                "name": item.joint.name,
                "owner": _address_json(item.owner.key),
                "mass": _mass_json(item.joint.name, item.joint.center, item.joint.radii),
                "adjacent_profiles": [float(value) for value in item.joint.adjacent_profiles],
            })
        anchors = []
        for paw in paw_by_parent.get(item.owner.key, []):
            anchor_point = (
                paw.attachment_centerline[0]
                if paw.attachment_centerline is not None
                else paw.foot_chain.hock_anchor
                if paw.foot_chain is not None
                else None
            )
            if anchor_point is None:
                _fail(f"paw source anchor is incomplete for {_key_text(paw.owner.key)}")
            anchors.append({
                "name": "forearm-distal-boundary" if paw.owner.key[3] == "hand" else "hock-endpoint",
                "kind": "parent-surface-anchor" if paw.owner.key[3] == "hand" else "endpoint",
                "point": _point_json(anchor_point),
                "boundary_point": _point_json(item.sections[-1].centerline[1]),
            })
        limb_controls.append({
            "owner": _address_json(item.owner.key),
            "profile_controls": [float(value) for value in item.profile_controls],
            "sections": sections,
            "bridges": bridges,
            "masses": masses,
            "joints": joints,
            "anchors": anchors,
        })
    paw_controls = []
    limb_by_owner = {item.owner.key: item for item in guide.limb_guides}
    owners_by_key = {item.key: item for item in guide.source_owners}
    for item in guide.paw_guides:
        if item.owner.parent is None or item.owner.parent not in owners_by_key:
            _fail(f"paw parent source is incomplete for {_key_text(item.owner.key)}")
        parent = owners_by_key[item.owner.parent]
        parent_limb = limb_by_owner.get(parent.key)
        if parent_limb is None or not parent_limb.sections:
            _fail(f"paw parent limb is missing for {_key_text(item.owner.key)}")
        if item.owner.key[3] == "hand":
            attachment = _path_json("attachment", item.attachment_centerline, (item.attachment_radius,) if item.attachment_radius is not None else None, path_kind=item.attachment_kind)
            if attachment is None or item.paw_center is None or item.paw_radii is None:
                _fail(f"hand paw controls are incomplete for {_key_text(item.owner.key)}")
            attachment_source = {
                "owner": _address_json(parent.key),
                "anchor": "forearm-distal-boundary",
                "point": _point_json(item.attachment_centerline[0]),  # type: ignore[index]
                "boundary_point": _point_json(parent_limb.sections[-1].centerline[1]),
            }
            paw_controls.append({
                "owner": _address_json(item.owner.key),
                "masses": [_mass_json("paw", item.paw_center, item.paw_radii)],
                "attachment": attachment,
                "attachment_source": attachment_source,
            })
            continue
        chain = item.foot_chain
        if chain is None or item.attachment_centerline is not None:
            _fail(f"foot chain controls are incomplete for {_key_text(item.owner.key)}")
        hock_source = {
            "owner": _address_json(parent.key),
            "anchor": "hock-endpoint",
            "point": _point_json(chain.hock_anchor),
            "boundary_point": _point_json(parent_limb.sections[-1].centerline[1]),
        }
        paw_controls.append({
            "owner": _address_json(item.owner.key),
            "chain": {
                "hock": _mass_json("hock-anchor", chain.hock_anchor, chain.hock_radii),
                "metatarsal": _path_json("metatarsal", chain.metatarsal_centerline, chain.metatarsal_profile, path_kind="tapered-segment"),
                "masses": [
                    _mass_json("paw-pad", chain.pad_center, chain.pad_radii),
                    _mass_json("toe-box", chain.toe_center, chain.toe_radii),
                ],
                "contact_height": float(chain.contact_height),
                "axes": {
                    "lateral": _point_json(chain.axes.lateral),
                    "up": _point_json(chain.axes.up),
                    "forward": _point_json(chain.axes.forward),
                },
            },
            "hock_source": hock_source,
        })
    tail_controls = []
    for item in guide.tail_guides:
        tail_controls.append({
            "owner": _address_json(item.owner.key),
            "centerline": _path_json("segment", item.centerline, item.taper, path_kind="tapered-segment"),
            "sections": [
                value for value in (
                    _path_json("tip-extension", item.extension_centerline, item.extension_taper, path_kind="tapered-segment"),
                    _path_json("root-attachment", item.root_attachment_centerline, item.root_attachment_taper, path_kind="tapered-segment"),
                ) if value is not None
            ],
            "masses": [
                value for value in (
                    _mass_json("tip-cap", item.cap_center, item.cap_radii),
                    _mass_json("root-collar", item.root_collar_center, item.root_collar_radii),
                ) if value is not None
            ],
        })
    recipe_counts: dict[str, int] = {}
    for field in compiled_fields:
        recipe_counts[field.recipe] = recipe_counts.get(field.recipe, 0) + 1
    return {
        "format": REGIONAL_GUIDE_FORMAT,
        "variant": variant_id,
        "owners": [_address_json(item.key) for item in guide.source_owners],
        "counts": {
            "owners": len(guide.source_owners),
            "axial_stations": len(stations),
            "axial_transitions": len(transitions),
            "axial_core_masses": 1,
            "torso_cage_sections": len(torso_cage.sections),
            "torso_cage_connections": len(torso_cage.sections) - 1,
            "shoulder_frame_sides": len(frame.sides),
            "shoulder_frame_curves": sum(3 for _ in frame.sides),
            "shoulder_frame_compiled_fields": sum(1 for _ in frame.sides),
            "head_neck_profile_sections": len(head.profile.sections),
            "head_neck_profile_connections": len(head.profile.connections),
            "head": 1,
            "limbs": len(guide.limb_guides),
            "paws": len(guide.paw_guides),
            "tails": len(guide.tail_guides),
            "compiled_fields": len(compiled_fields),
            "compiled_field_recipe_counts": recipe_counts,
        },
        "projections": _projection_json(),
        "shared_render_bounds": {"min": [float(item) for item in lower], "max": [float(item) for item in upper]},
        "canvas": {"width": CANVAS[0], "height": CANVAS[1], "mode": "RGB"},
        "layout": _layout_json(),
        "controls": {
            "axes": {"lateral": _point_json(guide.topology.axes.lateral), "up": _point_json(guide.topology.axes.up), "forward": _point_json(guide.topology.axes.forward)},
            "axial": axial_controls,
            "torso_cage": torso_cage_controls,
            "shoulder_frame": shoulder_frame_controls,
            "head": head_controls,
            "limbs": limb_controls,
            "paws": paw_controls,
            "tails": tail_controls,
        },
        "boundary": "private disposable regional controls; source-owned AddressKeys only; not a semantic or runtime contract",
    }


def _compile_hybrid_guide(guide: _HybridGuide) -> tuple[Field, ...]:
    """Adapt regional guides to the disposable analytic-field backend."""

    _validate_hybrid_guide(guide)
    fields: list[Field] = []
    limbs_by_owner = {item.owner.key: item for item in guide.limb_guides}
    paws_by_owner = {item.owner.key: item for item in guide.paw_guides}
    tails_by_owner = {item.owner.key: item for item in guide.tail_guides}
    head = guide.head_guide
    shoulder_frame = guide.shoulder_frame

    def add_ellipsoid(owner: Descriptor, recipe: str, center: tuple[float, float, float], radii: tuple[float, float, float]) -> None:
        values = (*center, *radii)
        if not all(math.isfinite(value) for value in values) or any(value <= 0.0 for value in radii):
            _fail(f"guide field {recipe!r} has invalid mass data")
        fields.append(Field(owner, recipe, _ellipsoid(np.asarray(center), np.asarray(radii))))

    def add_path(owner: Descriptor, recipe: str, path: tuple[tuple[float, float, float], tuple[float, float, float]], profile: tuple[float, ...], primitive: str) -> None:
        values = (*path[0], *path[1], *profile)
        if not all(math.isfinite(value) for value in values) or any(value <= 0.0 for value in profile) or path[0] == path[1]:
            _fail(f"guide field {recipe!r} has invalid path data")
        if primitive not in {"capsule", "tapered-segment"}:
            _fail(f"guide field {recipe!r} has invalid path primitive")
        fields.append(Field(owner, recipe, _segment(primitive, np.asarray(path[0]), np.asarray(path[1]), profile[0], profile[-1])))

    def add_curve(owner: Descriptor, recipe_prefix: str, curve: _ShoulderCurve, span_indices: tuple[int, ...]) -> None:
        if curve.owner is not owner:
            _fail(f"guide curve {recipe_prefix!r} lost source descriptor ownership")
        if len(curve.points) < 2 or len(curve.points) != len(curve.profile):
            _fail(f"guide curve {recipe_prefix!r} has invalid controls")
        if not span_indices or tuple(sorted(set(span_indices))) != span_indices or any(index < 0 or index >= len(curve.points) - 1 for index in span_indices):
            _fail(f"guide curve {recipe_prefix!r} has invalid compiled span selection")
        for index in span_indices:
            add_path(
                owner,
                f"{recipe_prefix}-{index}",
                (curve.points[index], curve.points[index + 1]),
                (curve.profile[index], curve.profile[index + 1]),
                "tapered-segment",
            )

    torso_cage = guide.torso_cage

    def add_head(desc: Descriptor) -> None:
        add_ellipsoid(desc, "cranium", head.cranium_center, head.cranium_radii)
        add_ellipsoid(desc, "muzzle", head.muzzle_center, head.muzzle_radii)
        add_path(desc, "head-base-bridge", head.head_transition, head.head_transition_thickness, "tapered-segment")

    def add_neck(desc: Descriptor) -> None:
        add_path(desc, "tapered-neck", head.neck_transition, head.neck_transition_thickness, "tapered-segment")
        add_ellipsoid(desc, "neck-collar", head.neck_collar_center, head.neck_collar_radii)

    def validate_shoulder_support_guide(desc: Descriptor) -> None:
        if desc is not shoulder_frame.torso_owner:
            _fail("shoulder support guide owner must retain torso descriptor identity")
        # Keep the private anterior/posterior curves in the guide for x-ray
        # inspection, but do not feed them to this isotropic skin adapter.
        # Their outer contour currently produces the underarm lobes; the
        # torso cage and upper-arm-owned deltoid sweep remain consumed.

    def add_deltoid(desc: Descriptor) -> None:
        matches = tuple(side for side in shoulder_frame.sides if side.owner is desc)
        if len(matches) != 1:
            _fail(f"upper-arm shoulder frame match is missing for {_key_text(desc.key)}")
        add_curve(desc, "deltoid-sweep", matches[0].deltoid_sweep, (1,))

    def add_limb(desc: Descriptor, limb: _LimbGuide) -> None:
        if len(limb.profile_controls) != 3 or not all(math.isfinite(value) and value > 0.0 for value in limb.profile_controls):
            _fail(f"limb profile controls are invalid for {_key_text(limb.owner.key)}")
        if len(limb.sections) != 2:
            _fail(f"limb piecewise sections are invalid for {_key_text(limb.owner.key)}")
        for section in limb.sections:
            add_path(desc, f"{limb.owner.key[3]}-{section.name}", section.centerline, section.thickness, section.path_kind)
        if limb.root_centerline is not None:
            add_path(
                desc,
                "root-bridge",
                _embed_boundary_connector(limb.root_centerline, limb.root_thickness, f"{_key_text(limb.owner.key)}.root"),
                limb.root_thickness,
                "tapered-segment",
            )  # type: ignore[arg-type]
        if limb.hip_centerline is not None:
            add_path(
                desc,
                "hip-transition",
                _embed_boundary_connector(limb.hip_centerline, limb.hip_thickness, f"{_key_text(limb.owner.key)}.hip"),
                limb.hip_thickness,
                "tapered-segment",
            )  # type: ignore[arg-type]
        if limb.joint is not None:
            if not math.isclose(limb.joint.radii[0], 0.70 * min(limb.joint.adjacent_profiles), rel_tol=1e-9, abs_tol=1e-12):
                _fail(f"joint radius is not derived from adjacent profiles for {_key_text(limb.owner.key)}")
            add_ellipsoid(desc, limb.joint.name, limb.joint.center, limb.joint.radii)

    def add_paw(desc: Descriptor, paw: _PawGuide) -> None:
        if paw.foot_chain is None:
            if paw.paw_center is None or paw.paw_radii is None:
                _fail(f"hand paw controls are incomplete for {_key_text(paw.owner.key)}")
            add_ellipsoid(desc, "paw", paw.paw_center, paw.paw_radii)
            if paw.attachment_centerline is None:
                _fail(f"hand paw attachment is incomplete for {_key_text(paw.owner.key)}")
            add_path(desc, "extremity-bridge", paw.attachment_centerline, (paw.attachment_radius,), paw.attachment_kind or "capsule")
        else:
            chain = paw.foot_chain
            add_path(desc, "metatarsal", chain.metatarsal_centerline, chain.metatarsal_profile, "tapered-segment")
            add_ellipsoid(desc, "paw-pad", chain.pad_center, chain.pad_radii)
            add_ellipsoid(desc, "toe-box", chain.toe_center, chain.toe_radii)

    def add_tail(desc: Descriptor, tail: _TailGuide) -> None:
        add_path(desc, "tail-segment", tail.centerline, tail.taper, "tapered-segment")
        if tail.extension_centerline is not None:
            add_path(desc, "tail-tip-extension", tail.extension_centerline, tail.extension_taper, "tapered-segment")  # type: ignore[arg-type]
        if tail.cap_center is not None:
            add_ellipsoid(desc, "tail-tip-cap", tail.cap_center, tail.cap_radii)  # type: ignore[arg-type]
        if tail.root_attachment_centerline is not None:
            add_path(desc, "tail-root-bridge", tail.root_attachment_centerline, tail.root_attachment_taper, "tapered-segment")  # type: ignore[arg-type]
        if tail.root_collar_center is not None:
            add_ellipsoid(desc, "tail-root-collar", tail.root_collar_center, tail.root_collar_radii)  # type: ignore[arg-type]

    for desc in guide.source_descriptors:
        # Keep the new compound field at the torso descriptor's canonical
        # source-address position rather than prepending it ahead of the
        # descriptor-ordered recipe stream.
        if desc.key == torso_cage.torso_owner.key:
            fields.append(Field(torso_cage.torso_owner, "torso-cage", _torso_cage_shape(torso_cage)))
            validate_shoulder_support_guide(desc)
        if desc.key == head.head_owner.key:
            add_head(desc)
        if desc.key == head.neck_owner.key:
            add_neck(desc)
        if desc.key in limbs_by_owner:
            add_limb(desc, limbs_by_owner[desc.key])
            if desc.key[3] == "upper_arm":
                add_deltoid(desc)
        if desc.key in paws_by_owner:
            add_paw(desc, paws_by_owner[desc.key])
        if desc.key in tails_by_owner:
            add_tail(desc, tails_by_owner[desc.key])
    if not fields or len(fields) > MAX_GENERATED_FIELDS:
        _fail(f"generated field count {len(fields)} exceeds bound {MAX_GENERATED_FIELDS}")
    return tuple(fields)


def _compound_fields(form: Form, descriptors: tuple[Descriptor, ...]) -> tuple[Field, ...]:
    """Compile private regional guides for the current analytic-field backend."""

    return _compile_hybrid_guide(_derive_hybrid_guides(form, descriptors))

def _smooth_union(fields: list[np.ndarray], k: float) -> np.ndarray:
    result = fields[0].copy()
    for current in fields[1:]:
        h = np.maximum(k - np.abs(result - current), 0.0)
        result = np.minimum(result, current) - (h**3) / (6.0 * k * k)
    return result


def _bounds(fields: tuple[Field, ...], padding: float) -> tuple[np.ndarray, np.ndarray]:
    mins: list[np.ndarray] = []
    maxs: list[np.ndarray] = []
    for field in fields:
        shape = field.shape
        if shape["name"] == "ellipsoid":
            centre = shape["center"]
            radii = shape["radii"]
            mins.append(centre - radii); maxs.append(centre + radii)
        elif shape["name"] == "torso-cage":
            centres = shape["centers"]
            lateral = shape["lateral_radii"]
            depth = shape["depth_radii"]
            cap_height = shape["cap_radii"]
            mins.append(
                np.asarray([
                    float(np.min(centres[:, 0] - lateral)),
                    float(np.min(shape["heights"] - cap_height)),
                    float(np.min(centres[:, 2] - depth)),
                ])
            )
            maxs.append(
                np.asarray([
                    float(np.max(centres[:, 0] + lateral)),
                    float(np.max(shape["heights"] + cap_height)),
                    float(np.max(centres[:, 2] + depth)),
                ])
            )
        else:
            a = shape["from"]
            b = shape["to"]
            r = max(float(shape["r0"]), float(shape["r1"]))
            mins.append(np.minimum(a, b) - r); maxs.append(np.maximum(a, b) + r)
    return np.min(np.stack(mins), axis=0) - padding, np.max(np.stack(maxs), axis=0) + padding


def _shared_render_bounds(field_sets: tuple[tuple[Field, ...], ...], padding: float) -> tuple[np.ndarray, np.ndarray]:
    """Return one deterministic display bound for every fixed variant.

    This bound is intentionally separate from each variant's marching-cubes
    extraction domain. It is used only for guide validation and guide/skin
    projection framing.
    """

    if not field_sets:
        _fail("cannot derive shared bounds without variants")
    bounds = [_bounds(fields, 0.0) for fields in field_sets]
    lower = np.min(np.stack([item[0] for item in bounds]), axis=0) - padding
    upper = np.max(np.stack([item[1] for item in bounds]), axis=0) + padding
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)) or np.any(upper <= lower):
        _fail("shared render bounds are invalid")
    return lower, upper


def _orientation(vertices: np.ndarray, faces: np.ndarray, axes: tuple[np.ndarray, np.ndarray, np.ndarray], fields: tuple[Field, ...], k: float) -> tuple[np.ndarray, np.ndarray, float]:
    e1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    e2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    areas = np.cross(e1, e2)
    centers = (vertices[faces[:, 0]] + vertices[faces[:, 1]] + vertices[faces[:, 2]]) / 3.0
    delta = 0.5 * min(float(axes[i][1] - axes[i][0]) for i in range(3))
    def combined(points: np.ndarray) -> np.ndarray:
        vals = [_field(points, field) for field in fields]
        return _smooth_union(vals, k)
    gradient = np.column_stack([(combined(centers + np.eye(3)[i] * delta) - combined(centers - np.eye(3)[i] * delta)) / (2.0 * delta) for i in range(3)])
    alignment = np.sum(areas * gradient, axis=1)
    if float(np.mean(alignment)) < 0.0:
        faces = faces[:, [0, 2, 1]]
        areas = -areas
        alignment = -alignment
    volume = float(np.sum(np.einsum("ij,ij->i", vertices[faces[:, 0]], areas)) / 6.0)
    if not math.isfinite(volume) or volume <= 0:
        _fail("mesh winding has non-positive signed volume")
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], areas)
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= 1e-14) or not np.all(np.isfinite(lengths)):
        _fail("mesh contains undefined normals")
    return faces, normals / lengths[:, None], volume


def _mesh_checks(vertices: np.ndarray, faces: np.ndarray, labels: list[tuple[str, tuple[str, ...], str, str]], bounds: tuple[np.ndarray, np.ndarray], volume: float) -> dict[str, Any]:
    if len(vertices) == 0 or len(faces) == 0 or not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(faces)):
        _fail("mesh is empty or non-finite")
    if np.any(faces < 0) or np.any(faces >= len(vertices)):
        _fail("mesh indices are invalid")
    areas = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]])
    if np.any(np.linalg.norm(areas, axis=1) <= 1e-14):
        _fail("mesh contains degenerate faces")
    edges: dict[tuple[int, int], int] = {}
    adjacency: list[set[int]] = [set() for _ in vertices]
    for face in faces:
        a, b, c = (int(x) for x in face)
        adjacency[a].update((b, c)); adjacency[b].update((a, c)); adjacency[c].update((a, b))
        for x, y in ((a, b), (b, c), (c, a)):
            edge = (min(x, y), max(x, y)); edges[edge] = edges.get(edge, 0) + 1
    if any(count != 2 for count in edges.values()):
        _fail("mesh is not watertight")
    seen: set[int] = set(); components = 0
    for start in range(len(vertices)):
        if start in seen: continue
        components += 1; stack = [start]; seen.add(start)
        while stack:
            for neighbour in adjacency[stack.pop()]:
                if neighbour not in seen: seen.add(neighbour); stack.append(neighbour)
    if components != 1:
        _fail(f"mesh has {components} connected components")
    lower, upper = bounds
    clearance = float(np.min(np.minimum(vertices - lower, upper - vertices)))
    if not math.isfinite(clearance) or clearance <= 0:
        _fail("surface is clipped by the sampling domain")
    unique_winners = sorted(set(labels))
    return {"vertex_count": int(len(vertices)), "face_count": int(len(faces)), "component_count": components, "watertight": True, "finite_vertices": True, "finite_normals": True, "valid_indices": True, "signed_volume": volume, "domain_clearance": clearance, "winner_vertex_count": len(labels), "unique_winner_count": len(unique_winners), "winner_addresses": [_address_json(key) for key in unique_winners]}


def build_variant(
    form: Form,
    descriptors: tuple[Descriptor, ...],
    samples: int,
    padding: float,
    smooth_k: float,
    guide: _HybridGuide | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[str, tuple[str, ...], str, str]], dict[str, Any], dict[str, Any]]:
    if type(samples) is not int or samples > MAX_SAMPLES or samples < 16 or samples**3 > MAX_VOXELS:
        _fail("sampling configuration exceeds bounded limits")
    if not math.isfinite(float(padding)) or padding < 0.0 or not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("padding and smooth-k must be finite, with non-negative padding and positive smooth-k")
    if guide is None:
        guide = _derive_hybrid_guides(form, descriptors)
    fields = _compile_hybrid_guide(guide)
    if len(fields) * samples**3 > MAX_FIELD_VALUES:
        _fail("generated field sampling configuration exceeds bounded field-memory limits")
    lower, upper = _bounds(fields, padding)
    axes = tuple(np.linspace(lower[i], upper[i], samples, dtype=np.float64) for i in range(3))
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    grid_fields = [_field(points, generated) for generated in fields]
    field = _smooth_union(grid_fields, smooth_k)
    if not np.all(np.isfinite(field)) or float(np.min(field)) >= 0 or float(np.max(field)) <= 0:
        _fail("field has no finite zero crossing")
    if np.any(field[(0, -1), :, :] <= 0) or np.any(field[:, (0, -1), :] <= 0) or np.any(field[:, :, (0, -1)] <= 0):
        _fail("field reaches the sampling domain boundary")
    try:
        raw_vertices, raw_faces, _, _ = marching_cubes(field, level=0.0, spacing=tuple(float(a[1]-a[0]) for a in axes), gradient_direction="descent", allow_degenerate=False)
    except Exception as exc:
        raise PreviewError(f"surface extraction failed: {exc}") from exc
    vertices = np.asarray(raw_vertices, dtype=np.float64) + lower
    faces = np.asarray(raw_faces, dtype=np.int64)
    faces, normals, volume = _orientation(vertices, faces, axes, fields, smooth_k)
    labels: list[tuple[str, tuple[str, ...], str, str]] = []
    # Re-evaluate only at vertices; this avoids carrying a grid-shaped winner channel into artifacts.
    for vertex in vertices:
        values = [_field(vertex.reshape(1, 3), generated)[0] for generated in fields]
        winning_field = fields[int(np.argmin(values))]
        labels.append(_field_owner_keys(vertex.reshape(1, 3), winning_field)[0])
    metrics = _mesh_checks(vertices, faces, labels, (lower, upper), volume)
    recipe_counts: dict[str, int] = {}
    for generated in fields:
        recipe_counts[generated.recipe] = recipe_counts.get(generated.recipe, 0) + 1
    metrics.update({
        "field_minimum": float(np.min(field)),
        "field_maximum": float(np.max(field)),
        "source_descriptor_count": len(descriptors),
        "generated_field_count": len(fields),
        "generated_field_limit": MAX_GENERATED_FIELDS,
        "field_memory_values": len(fields) * samples**3,
        "field_memory_limit": MAX_FIELD_VALUES,
        "field_recipe_counts": recipe_counts,
        "smooth_union": {"operator": "polynomial_cubic_smooth_min", "k": smooth_k, "fold_order": "source_address_then_recipe_order"},
        "grid": {"samples_per_axis": samples, "axis_order": ["x", "y", "z"], "bounds_min": lower.tolist(), "bounds_max": upper.tolist(), "spacing": [float(a[1]-a[0]) for a in axes]},
        "source_control_consumption": {
            "format": SOURCE_FORMAT,
            "shoulder": _shoulder_source_controls_json(guide.shoulder_frame),
        },
    })
    return vertices, faces, normals, labels, metrics, {"bounds_min": lower.tolist(), "bounds_max": upper.tolist(), "spacing": [float(a[1]-a[0]) for a in axes]}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _write_ply(path: Path, vertices: np.ndarray, faces: np.ndarray, normals: np.ndarray) -> None:
    lines = ["ply", "format ascii 1.0", f"element vertex {len(vertices)}", "property float x", "property float y", "property float z", "property float nx", "property float ny", "property float nz", f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header"]
    lines.extend("%.9f %.9f %.9f %.9f %.9f %.9f" % tuple([*v, *n]) for v, n in zip(vertices, normals))
    lines.extend("3 %d %d %d" % tuple(int(x) for x in f) for f in faces)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _projection_frame(bounds: tuple[np.ndarray, np.ndarray], basis: np.ndarray, box: tuple[int, int, int, int]) -> dict[str, Any]:
    lower, upper = bounds
    corners = np.asarray([
        [lower[0] if mask & 1 else upper[0], lower[1] if mask & 2 else upper[1], lower[2] if mask & 4 else upper[2]]
        for mask in range(8)
    ], dtype=np.float64)
    projected = corners @ basis.T
    lo, hi = projected[:, :2].min(axis=0), projected[:, :2].max(axis=0)
    x0, y0, x1, y1 = box
    span = np.maximum(hi - lo, 1e-9)
    scale = min((x1 - x0 - 28) / span[0], (y1 - y0 - 48) / span[1])
    if not math.isfinite(float(scale)) or scale <= 0.0:
        _fail("projection frame is invalid")
    centre = (lo + hi) / 2.0
    return {"basis": basis, "box": box, "centre": centre, "scale": float(scale)}


def _frame_screen(frame: dict[str, Any], points: np.ndarray) -> list[tuple[float, float]]:
    basis = frame["basis"]
    camera = np.asarray(points, dtype=np.float64) @ basis.T
    x0, y0, x1, y1 = frame["box"]
    centre = frame["centre"]
    scale = frame["scale"]
    return [
        (
            x0 + (x1 - x0) / 2.0 + float((point[0] - centre[0]) * scale),
            y0 + 26.0 + (y1 - y0 - 42.0) / 2.0 - float((point[1] - centre[1]) * scale),
        )
        for point in camera
    ]


def _draw_guide_mass(draw: ImageDraw.ImageDraw, frame: dict[str, Any], center: tuple[float, float, float], radii: tuple[float, float, float], colour: tuple[int, int, int]) -> None:
    # The projected outline is an orthographic ellipse enclosing the private
    # guide mass.  It uses only guide center/radii controls, never a descriptor
    # shape or analytic field.
    basis = frame["basis"]
    centre = np.asarray(center, dtype=np.float64) @ basis.T
    projected_radius = np.asarray([
        float(np.sum(np.abs(basis[row] * np.asarray(radii, dtype=np.float64))))
        for row in (0, 1)
    ])
    x0, y0, x1, y1 = frame["box"]
    scale = frame["scale"]
    cx = x0 + (x1 - x0) / 2.0 + float((centre[0] - frame["centre"][0]) * scale)
    cy = y0 + 26.0 + (y1 - y0 - 42.0) / 2.0 - float((centre[1] - frame["centre"][1]) * scale)
    rx, ry = projected_radius * scale
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=colour, width=2)


def _draw_guide_path(draw: ImageDraw.ImageDraw, frame: dict[str, Any], path: tuple[tuple[float, float, float], tuple[float, float, float]], profile: tuple[float, ...], colour: tuple[int, int, int], *, narrowing: tuple[float, ...] | None = None, dashed: bool = False) -> None:
    points = _frame_screen(frame, np.asarray(path, dtype=np.float64))
    if dashed:
        start, end = np.asarray(points[0]), np.asarray(points[1])
        for fraction in np.linspace(0.0, 0.85, 6):
            a = start + (end - start) * fraction
            b = start + (end - start) * min(fraction + 0.10, 1.0)
            draw.line((float(a[0]), float(a[1]), float(b[0]), float(b[1])), fill=colour, width=2)
    else:
        draw.line((points[0], points[1]), fill=colour, width=2)
    scale = frame["scale"]
    for index, point in enumerate(points):
        radius = float(profile[min(index, len(profile) - 1)])
        if narrowing is not None:
            radius *= float(narrowing[min(index, len(narrowing) - 1)])
        radius_px = max(2.0, min(28.0, radius * scale))
        draw.ellipse((point[0] - radius_px, point[1] - radius_px, point[0] + radius_px, point[1] + radius_px), outline=colour, width=1)


def _draw_guide_curve(
    draw: ImageDraw.ImageDraw,
    frame: dict[str, Any],
    curve: _ShoulderCurve,
    colour: tuple[int, int, int],
) -> None:
    """Draw a complete private multi-control curve without adding labels."""

    points = _frame_screen(frame, np.asarray(curve.points, dtype=np.float64))
    for index in range(len(points) - 1):
        draw.line((points[index], points[index + 1]), fill=colour, width=2)
    scale = frame["scale"]
    for index, point in enumerate(points):
        radius_px = max(2.0, min(12.0, float(curve.profile[index]) * scale * 0.55))
        draw.ellipse(
            (point[0] - radius_px, point[1] - radius_px, point[0] + radius_px, point[1] + radius_px),
            outline=colour,
            width=1,
        )


def _draw_shoulder_frame(draw: ImageDraw.ImageDraw, frame: dict[str, Any], shoulder: _ShoulderFrame, colour: tuple[int, int, int]) -> None:
    """Draw the skin-driving shoulder frame; old circular diagnostics are excluded."""

    _draw_guide_mass(draw, frame, shoulder.central_anchor, shoulder.central_profile + (shoulder.central_profile[0],), colour)
    for side in shoulder.sides:
        _draw_guide_curve(draw, frame, side.anterior_support, colour)
        _draw_guide_curve(draw, frame, side.posterior_return, colour)
        _draw_guide_curve(draw, frame, side.deltoid_sweep, colour)
        for point in (side.shoulder_extremum, side.socket_anchor):
            screen = _frame_screen(frame, np.asarray([point], dtype=np.float64))[0]
            draw.ellipse((screen[0] - 3, screen[1] - 3, screen[0] + 3, screen[1] + 3), fill=colour)


def _draw_torso_cage(draw: ImageDraw.ImageDraw, frame: dict[str, Any], cage: _TorsoCage, colour: tuple[int, int, int]) -> None:
    """Render the skin-driving cage as section rings and longitudinal seams."""

    section_points: list[list[tuple[float, float]]] = []
    lateral_axis = np.asarray(cage.axes.lateral, dtype=np.float64)
    forward_axis = np.asarray(cage.axes.forward, dtype=np.float64)
    for section in cage.sections:
        angles = np.linspace(0.0, 2.0 * math.pi, 33)
        ring = (
            np.asarray(section.center, dtype=np.float64)[None, :]
            + np.cos(angles)[:, None] * float(section.lateral_radius) * lateral_axis[None, :]
            + np.sin(angles)[:, None] * float(section.depth_radius) * forward_axis[None, :]
        )
        projected = _frame_screen(frame, ring)
        points = [(float(point[0]), float(point[1])) for point in projected]
        section_points.append(points)
        draw.line(points, fill=colour, width=2, joint="curve")

    # A sparse set of longitudinal seams makes the ordered sweep readable in
    # front and side projections, where an ellipse's depth or lateral axis can
    # otherwise collapse to a single contour.
    for ring_index in range(len(section_points) - 1):
        for point_index in range(0, 32, 4):
            draw.line(
                (section_points[ring_index][point_index], section_points[ring_index + 1][point_index]),
                fill=colour,
                width=1,
            )
    centreline = _frame_screen(frame, np.asarray([section.center for section in cage.sections], dtype=np.float64))
    draw.line([tuple(float(value) for value in point) for point in centreline], fill=colour, width=1)


def _draw_guide(draw: ImageDraw.ImageDraw, frame: dict[str, Any], guide: _HybridGuide) -> None:
    colours = {
        "cage": (244, 174, 76),
        "shoulder": (244, 104, 186),
        "head": (204, 121, 190),
        "limb": (96, 174, 218),
        "joint": (235, 124, 100),
        "paw": (134, 198, 135),
        "tail": (225, 181, 88),
    }
    _draw_torso_cage(draw, frame, guide.torso_cage, colours["cage"])
    _draw_shoulder_frame(draw, frame, guide.shoulder_frame, colours["shoulder"])
    head = guide.head_guide
    _draw_guide_mass(draw, frame, head.cranium_center, head.cranium_radii, colours["head"])
    _draw_guide_mass(draw, frame, head.muzzle_center, head.muzzle_radii, colours["head"])
    _draw_guide_mass(draw, frame, head.neck_collar_center, head.neck_collar_radii, colours["head"])
    _draw_guide_path(draw, frame, head.head_transition, head.head_transition_thickness, colours["head"])
    _draw_guide_path(draw, frame, head.neck_transition, head.neck_transition_thickness, colours["head"])
    for item in guide.limb_guides:
        for section in item.sections:
            _draw_guide_path(draw, frame, section.centerline, section.thickness, colours["limb"])
        for path, profile in ((item.root_centerline, item.root_thickness), (item.hip_centerline, item.hip_thickness)):
            if path is not None and profile is not None:
                _draw_guide_path(draw, frame, path, profile, colours["limb"])
        if item.hip_center is not None and item.hip_radii is not None:
            _draw_guide_mass(draw, frame, item.hip_center, item.hip_radii, colours["limb"])
        if item.joint is not None:
            _draw_guide_mass(draw, frame, item.joint.center, item.joint.radii, colours["joint"])
    for item in guide.paw_guides:
        if item.foot_chain is not None:
            chain = item.foot_chain
            _draw_guide_path(draw, frame, chain.metatarsal_centerline, chain.metatarsal_profile, colours["paw"])
            _draw_guide_mass(draw, frame, chain.pad_center, chain.pad_radii, colours["paw"])
            _draw_guide_mass(draw, frame, chain.toe_center, chain.toe_radii, colours["paw"])
        else:
            _draw_guide_mass(draw, frame, item.paw_center, item.paw_radii, colours["paw"])
            if item.attachment_centerline is not None and item.attachment_radius is not None:
                _draw_guide_path(draw, frame, item.attachment_centerline, (item.attachment_radius,), colours["paw"])
    for item in guide.tail_guides:
        _draw_guide_path(draw, frame, item.centerline, item.taper, colours["tail"])
        if item.extension_centerline is not None and item.extension_taper is not None:
            _draw_guide_path(draw, frame, item.extension_centerline, item.extension_taper, colours["tail"])
        if item.cap_center is not None and item.cap_radii is not None:
            _draw_guide_mass(draw, frame, item.cap_center, item.cap_radii, colours["tail"])
        if item.root_attachment_centerline is not None and item.root_attachment_taper is not None:
            _draw_guide_path(draw, frame, item.root_attachment_centerline, item.root_attachment_taper, colours["tail"])
        if item.root_collar_center is not None and item.root_collar_radii is not None:
            _draw_guide_mass(draw, frame, item.root_collar_center, item.root_collar_radii, colours["tail"])


def _draw_skin(draw: ImageDraw.ImageDraw, frame: dict[str, Any], vertices: np.ndarray, faces: np.ndarray) -> None:
    basis = frame["basis"]
    # Keep world-space triangles for screen mapping.  ``_frame_screen`` owns
    # the one world-to-camera projection; passing camera-space points here
    # would apply the basis a second time (most visible in the side view,
    # where the basis swaps the wide lateral and narrow depth spans).
    triangles = vertices[faces]
    camera = triangles @ basis.T
    normals = np.cross(camera[:, 1] - camera[:, 0], camera[:, 2] - camera[:, 0])
    visible = normals[:, 2] > 0
    order = np.flatnonzero(visible)
    order = order[np.argsort(np.mean(camera[order, :, 2], axis=1))]
    light = np.asarray((0.35, 0.55, 0.76), dtype=np.float64)
    light /= np.linalg.norm(light)
    for index in order:
        normal = normals[index]
        length = np.linalg.norm(normal)
        if length <= 1e-12:
            continue
        brightness = 0.42 + 0.58 * max(0.0, float(np.dot(normal / length, light)))
        colour = (int(148 * brightness), int(165 * brightness), int(184 * brightness))
        draw.polygon(_frame_screen(frame, triangles[index]), fill=colour)


def _render(
    path: Path,
    vertices: np.ndarray,
    faces: np.ndarray,
    variant_id: str,
    *,
    guide: _HybridGuide,
    bounds: tuple[np.ndarray, np.ndarray],
) -> None:
    _validate_hybrid_guide(guide, bounds)
    image = Image.new("RGB", CANVAS, (20, 23, 29))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((16, 16), f"Disposable guide + compiled skin - {variant_id}", fill=(235, 238, 244), font=font)
    draw.text((16, 42), "guide: skin-driving torso cage rings / regional limb sections / endpoint joints / digitigrade foot chains    skin: deterministic compiled field", fill=(167, 176, 190), font=font)
    projection_lookup = {name: np.asarray(basis, dtype=np.float64) for name, basis, _ in PROJECTIONS}
    shared_frames: dict[str, dict[str, Any]] = {}
    for item in PANEL_LAYOUT:
        name = item["projection"]
        box = item["box"]
        if name not in shared_frames:
            # Establish the projected world frame once per view.  Each panel
            # receives its own destination box below, while the guide/skin
            # pair cannot drift to independently fitted frames.
            shared_frames[name] = _projection_frame(bounds, projection_lookup[name], box)
        frame = {**shared_frames[name], "box": box}
        panel_colour = (28, 35, 43) if item["content"] == "guide" else (24, 27, 34)
        draw.rectangle(box, fill=panel_colour)
        if item["content"] == "guide":
            _draw_guide(draw, frame, guide)
        else:
            _draw_skin(draw, frame, vertices, faces)
        draw.rectangle(box, outline=(74, 82, 96), width=2)
        draw.text((box[0] + 10, box[1] + 8), f"{name} -- {item['content']}", fill=(235, 238, 244), font=font)
    image.save(path, format="PNG")


def _sha(path: Path, kind: str, root: Path) -> dict[str, Any]:
    data = path.read_bytes(); return {"kind": kind, "path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def generate(input_path: Path, output: Path, *, samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> dict[str, Any]:
    if output.exists() or os.path.lexists(output):
        _fail(f"refusing to overwrite output: {output}")
    if not output.parent.is_dir():
        _fail(f"output parent must exist: {output.parent}")
    data = input_path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        _fail("input exceeds bounded size")
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise PreviewError(f"input is not finite JSON: {exc}") from exc
    form = validate_envelope(value)

    # Derive every private guide and compiled field set before extracting any
    # mesh.  This gives the four variants one shared world-space frame while
    # retaining each variant's own guide controls and skin geometry.
    prepared: list[tuple[str, tuple[Descriptor, ...], dict[str, Any], _HybridGuide, tuple[Field, ...]]] = []
    for variant_id, descriptors, raw_variant in form.variants:
        guide = _derive_hybrid_guides(form, descriptors)
        _validate_hybrid_guide(guide)
        fields = _compile_hybrid_guide(guide)
        prepared.append((variant_id, descriptors, raw_variant, guide, fields))
    shared_render_bounds = _shared_render_bounds(tuple(item[4] for item in prepared), padding)
    for _, _, _, guide, _ in prepared:
        _validate_hybrid_guide(guide, shared_render_bounds)

    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        records = []
        for variant_id, descriptors, raw_variant, guide, fields in prepared:
            vertices, faces, normals, labels, metrics, grid = build_variant(
                form,
                descriptors,
                samples,
                padding,
                smooth_k,
                guide=guide,
            )
            variant_dir = stage / variant_id
            variant_dir.mkdir()
            ply = variant_dir / "surface.ply"
            sidecar = variant_dir / "semantic.json"
            metrics_path = variant_dir / "metrics.json"
            png = variant_dir / "guide-skin-composite.png"
            guide_path = variant_dir / "regional-guide.json"
            _write_ply(ply, vertices, faces, normals)
            sidecar.write_bytes(_canonical({
                "format": "creature-kernel.disposable-surface-preview-semantic-winners.v1",
                "source_format": SOURCE_FORMAT,
                "variant_id": variant_id,
                "vertex_count": len(vertices),
                "source_node_labels": [_address_json(key) for key in labels],
                "attribution": "every recipe component resolves to its source descriptor owner; no synthetic node identity is emitted",
            }))
            metrics_path.write_bytes(_canonical(metrics))
            guide_path.write_bytes(_canonical(_regional_guide_json(variant_id, guide, shared_render_bounds, compiled_fields=fields)) + b"\n")
            _render(png, vertices, faces, variant_id, guide=guide, bounds=shared_render_bounds)
            records.append({
                "id": variant_id,
                "profile_id": raw_variant["profile_id"],
                "source": {"document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"]},
                "descriptor_address_keys": [_address_json(desc.key) for desc in descriptors],
                "grid": grid,
                "metrics": metrics,
                "inventory": [
                    _sha(ply, "ply", stage),
                    _sha(sidecar, "semantic-sidecar", stage),
                    _sha(metrics_path, "metrics", stage),
                    {**_sha(png, "guide-skin-composite-png", stage), "width": CANVAS[0], "height": CANVAS[1], "views": ["front", "side", "three-quarter"], "panels_per_view": 2, "mode": "RGB"},
                    {**_sha(guide_path, "regional-guide-json", stage), "format": REGIONAL_GUIDE_FORMAT, "variant": variant_id},
                ],
            })
        lower, upper = shared_render_bounds
        manifest = {
            "format": FORMAT,
            "status": "success",
            "source_format": SOURCE_FORMAT,
            "source": {"format": SOURCE_FORMAT, "sha256": hashlib.sha256(data).hexdigest(), "document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"], "reference_scale": form.reference_scale_raw},
            "shared_render_bounds": {"min": [float(item) for item in lower], "max": [float(item) for item in upper]},
            "canvas": {"width": CANVAS[0], "height": CANVAS[1], "mode": "RGB"},
            "layout": _layout_json(),
            "projections": _projection_json(),
            "generator": {"bundle_version": 2, "samples_per_axis": samples, "padding": padding, "smooth_union": {"operator": "polynomial_cubic_smooth_min", "k": smooth_k, "fold_order": "source_address_then_recipe_order"}, "field_primitives": ["torso-cage", "ellipsoid", "capsule", "linear-radius-tapered-segment"], "field_recipes": ["torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar", "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal", "thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint", "elbow", "knee", "hock", "root-bridge", "hip-transition", "deltoid-sweep-1", "paw", "metatarsal", "paw-pad", "toe-box", "extremity-bridge", "tail-segment", "tail-tip-extension", "tail-tip-cap", "tail-root-bridge", "tail-root-collar"], "ownership": "recipe fields are source-owned; the blended torso-cage is torso-owned; shoulder support curves remain torso-owned guide-only controls and are not consumed by this adapter; deltoid recipes retain their upper-arm owners; winner labels expose only source AddressKeys", "boundary": "disposable exploratory visual proof; not production geometry, SDF, collision, rig, topology, or Readiness evidence"},
            "variants": records,
        }
        (stage / "surface-preview-manifest.json").write_bytes(_canonical(manifest) + b"\n")
        expected_files = {"surface-preview-manifest.json"}
        expected_directories = set(VARIANT_IDS)
        for record in records:
            expected_files.update(entry["path"] for entry in record["inventory"])
        actual_files: set[str] = set()
        actual_directories: set[str] = set()
        for item in stage.rglob("*"):
            relative = item.relative_to(stage).as_posix()
            if item.is_symlink():
                _fail(f"staging bundle contains a symlink: {relative}")
            if item.is_dir():
                actual_directories.add(relative)
            elif item.is_file():
                actual_files.add(relative)
            else:
                _fail(f"staging bundle contains a non-regular path: {relative}")
        if actual_directories != expected_directories or actual_files != expected_files:
            _fail("staging bundle does not match its explicit artifact inventory")
        os.replace(stage, output)
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a disposable current-form continuous-surface preview")
    parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--samples-per-axis", type=int, default=DEFAULT_SAMPLES); parser.add_argument("--padding", type=float, default=DEFAULT_PADDING); parser.add_argument("--smooth-k", type=float, default=DEFAULT_SMOOTH_K)
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.input, args.output, samples=args.samples_per_axis, padding=args.padding, smooth_k=args.smooth_k)
    except (OSError, PreviewError, ValueError) as exc:
        print(json.dumps({"format": FORMAT, "status": "failure", "error": str(exc)}, sort_keys=True), file=sys.stderr); return 2
    print(json.dumps({"format": FORMAT, "status": "success", "output": str(args.output), "variants": [x["id"] for x in manifest["variants"]]}, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

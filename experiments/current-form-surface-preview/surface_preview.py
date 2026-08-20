#!/usr/bin/env python3
"""Build a bounded, disposable continuous surface from a v4 form envelope.

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
REGIONAL_GUIDE_FORMAT = "creature-kernel.disposable-surface-preview-regional-guide.v4"
SOURCE_FORMAT = "creature-kernel.provisional-form-preview.v4"
VARIANT_IDS = ("neutral-v0", "broad-soft-v0", "lean-readable-v0", "depth-forward-v0")
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_SAMPLES = 128
MAX_VOXELS = 128**3
MAX_FIELD_VALUES = 32_000_000
MAX_DESCRIPTORS = 64
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


def _vector(value: Any, where: str) -> tuple[int, int, int]:
    values = _array(value, where)
    if len(values) != 3:
        _fail(f"{where} must contain three integers")
    return tuple(_int(item, f"{where}[{index}]") for index, item in enumerate(values))  # type: ignore[return-value]


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


@dataclass(frozen=True)
class Descriptor:
    key: tuple[str, tuple[str, ...], str, str]
    parent: tuple[str, tuple[str, ...], str, str] | None
    point: np.ndarray
    exact_point: tuple[int, int, int]
    shape: dict[str, Any]
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
    owner: Descriptor
    center: tuple[float, float, float]
    lateral_radius: float
    depth_radius: float

    @property
    def source_key(self) -> tuple[str, tuple[str, ...], str, str]:
        return self.owner.key

    @property
    def provenance(self) -> dict[str, Any]:
        return self.owner.provenance


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
    """One bilateral shoulder frame side derived from cage and arm geometry."""

    side: str
    owner: Descriptor
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


@dataclass(frozen=True)
class _ShoulderFrame:
    """Private trapezius/shoulder frame for a later surface consumer.

    The frame is deliberately not compiled by the current analytic-field
    adapter.  Its central anchor remains torso-owned, while its two socket
    anchors and deltoid controls remain upper-arm-owned.  This keeps a later
    consumer from having to infer a shoulder girdle from two round masses.
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


@dataclass(frozen=True)
class _HeadGuide:
    """Cranium/muzzle and neck-transition controls for the head region."""

    head_owner: Descriptor
    neck_owner: Descriptor
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
class _PawGuide:
    """Structured hand paw or digitigrade heel/forefoot controls."""

    owner: Descriptor
    paw_center: tuple[float, float, float]
    paw_radii: tuple[float, float, float]
    heel_center: tuple[float, float, float] | None
    heel_radii: tuple[float, float, float] | None
    forefoot_center: tuple[float, float, float] | None
    forefoot_radii: tuple[float, float, float] | None
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

    @property
    def center(self) -> tuple[float, float, float]:
        """Compatibility alias for the source display center."""
        return self.paw_center

    @property
    def radii(self) -> tuple[float, float, float]:
        """Compatibility alias for the hand paw mass."""
        return self.paw_radii


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
class Form:
    raw: dict[str, Any]
    source: dict[str, Any]
    reference_scale: float
    reference_scale_raw: dict[str, Any]
    variants: tuple[tuple[str, tuple[Descriptor, ...], dict[str, Any]], ...]


def validate_envelope(value: Any) -> Form:
    root = _obj(value, "envelope")
    required = {"format", "operation", "status", "stage", "processing_complete", "diagnostics_complete", "diagnostics", "source", "reference_scale", "variants", "limitations"}
    if set(root) != required:
        _fail("envelope has unexpected or missing fields")
    if root["format"] != SOURCE_FORMAT or root["operation"] != "inspect-provisional-form" or root["status"] != "success" or root["stage"] != "provisional-form":
        _fail("envelope is not a successful v4 provisional-form result")
    if root["processing_complete"] is not True or root["diagnostics_complete"] is not True or root["diagnostics"] != []:
        _fail("envelope success flags or diagnostics are invalid")
    if type(root["limitations"]) is not str or "Readiness" not in root["limitations"] or "geometry" not in root["limitations"]:
        _fail("envelope limitations do not state the exploratory boundary")
    source = _obj(root["source"], "source")
    if set(source) != {"document", "namespace", "resource_profile_id"} or any(type(source[x]) is not str for x in source):
        _fail("source is invalid")
    if source["resource_profile_id"] != "ck.resource.body.r2":
        _fail("unsupported resource profile")
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
    variants = _array(root["variants"], "variants")
    if len(variants) != 4:
        _fail("variants must contain exactly four items")
    normalized: list[tuple[str, tuple[Descriptor, ...], dict[str, Any]]] = []
    canonical: list[tuple[Any, ...]] | None = None
    for index, item in enumerate(variants):
        variant = _obj(item, f"variants[{index}]")
        if set(variant) != {"id", "profile_id", "provenance", "descriptors"} or variant.get("id") != VARIANT_IDS[index] or variant.get("profile_id") != VARIANT_IDS[index]:
            _fail(f"variants[{index}] is not the fixed {VARIANT_IDS[index]} variant")
        provenance = _obj(variant["provenance"], f"variants[{index}].provenance")
        if set(provenance) != {"source", "resource_profile_id"} or provenance.get("source") != "profile-derived-display" or provenance.get("resource_profile_id") != source["resource_profile_id"]:
            _fail(f"variants[{index}].provenance is invalid")
        descriptors = _array(variant["descriptors"], f"variants[{index}].descriptors")
        if not descriptors or len(descriptors) > MAX_DESCRIPTORS:
            _fail(f"variants[{index}].descriptors count is invalid")
        parsed: list[Descriptor] = []
        keys: list[tuple[str, tuple[str, ...], str, str]] = []
        for di, raw_item in enumerate(descriptors):
            raw = _obj(raw_item, f"variants[{index}].descriptors[{di}]")
            expected = {"descriptor_kind", "address", "parent", "placement_source", "reference_point", "profile_id", "source", "provenance", "shape"}
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
            if set(descriptor_provenance) != {"source", "resource_profile_id"} or descriptor_provenance != provenance:
                _fail(f"descriptor {index}/{di}.provenance is invalid")
            point = _vector(raw["reference_point"], f"descriptor {index}/{di}.reference_point")
            shape = _shape(raw["shape"], f"descriptor {index}/{di}.shape")
            parsed.append(Descriptor(key, parent, np.asarray(point, dtype=np.float64) / reference_scale, point, shape, placement, raw["profile_id"], raw["source"], descriptor_provenance, raw))
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
        signature = [(x.key, x.exact_point, x.parent, x.placement_source, x.shape["name"]) for x in parsed]
        if canonical is None:
            canonical = signature
        elif signature != canonical:
            _fail(f"variants[{index}] do not preserve semantic descriptor identity")
        normalized.append((VARIANT_IDS[index], tuple(parsed), variant))
    if canonical is None:
        _fail("no descriptors")
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
    return Form(root, source, reference_scale, scale, tuple(normalized))


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
    pelvis: Descriptor,
    torso: Descriptor,
    pelvis_center: tuple[float, float, float],
    pelvis_radii: tuple[float, float, float],
    torso_center: tuple[float, float, float],
    waist_center: tuple[float, float, float],
    torso_radii: tuple[float, float, float],
    chest_center: tuple[float, float, float],
) -> _TorsoCage:
    """Build the fixed-topology torso profile consumed by the next evaluator.

    This is deliberately a profile derivation, not another field recipe.  The
    pelvis and torso descriptors remain the only source owners.  The seven
    sections are deterministic functions of their already-derived guides: the
    abdomen gets a short, broad waist band instead of one point-like minimum.
    """

    pelvis_origin = np.asarray(pelvis_center, dtype=np.float64)
    waist = np.asarray(waist_center, dtype=np.float64)
    chest = np.asarray(chest_center, dtype=np.float64)
    pelvis_size = np.asarray(pelvis_radii, dtype=np.float64)
    torso_size = np.asarray(torso_radii, dtype=np.float64)
    # The source convention guarantees that the torso centre is above the
    # pelvis centre, but source radii are intentionally allowed to vary.  Use
    # the raw guide-derived heights, then project them into a deterministic
    # expanded centre interval with a small stable gap.  This keeps the
    # private profile ordered without rejecting an otherwise admitted source
    # merely because one body is unusually deep/tall.
    pelvis_y = float(pelvis_origin[1])
    torso_y = float(torso_center[1])
    span = torso_y - pelvis_y
    if not math.isfinite(span) or span <= 0.0:
        _fail("torso-cage source centres must have positive axial separation")
    # Use the existing waist and chest controls only as normalized placement
    # inputs.  The additional abdomen controls make the narrow region occupy a
    # real axial interval while remaining proportional for every variant.
    upper_pelvis_y = float(pelvis_origin[1] + 0.24 * pelvis_size[1])
    chest_y = float(chest[1])
    # Extremely disproportionate source radii can place the derived pelvis
    # control above the chest control. Keep the profile ordered by moving only
    # this private start control into the available source-centre interval;
    # ordinary variants retain the unmodified upper-pelvis height.
    profile_start_y = min(upper_pelvis_y, chest_y - max(0.20 * span, 1.0e-6))
    abdomen_span = chest_y - profile_start_y
    if not math.isfinite(abdomen_span) or abdomen_span <= 0.0:
        _fail("torso-cage abdomen profile requires positive axial separation")
    waist_t = (float(waist[1]) - profile_start_y) / abdomen_span
    waist_t = min(max(waist_t, 0.28), 0.58)
    # Named profile relationships, rather than world-space offsets, keep the
    # band stable as the source proportions change.
    band_half_span = 0.10
    lower_abdomen_t = max(0.20, waist_t - band_half_span)
    upper_abdomen_t = min(0.70, waist_t + band_half_span)
    lower_rib_t = max(upper_abdomen_t + 0.10, 0.76)
    lower_rib_t = min(lower_rib_t, 0.88)
    raw_heights = (
        float(pelvis_origin[1] - 0.32 * pelvis_size[1]),
        profile_start_y,
        profile_start_y + lower_abdomen_t * abdomen_span,
        profile_start_y + waist_t * abdomen_span,
        profile_start_y + upper_abdomen_t * abdomen_span,
        profile_start_y + lower_rib_t * abdomen_span,
        float(chest[1]),
    )
    lower_limit = pelvis_y - 0.50 * span
    upper_limit = torso_y + 0.50 * span
    minimum_gap = max(span * 1.0e-6, 1.0e-6)
    heights: list[float] = []
    for index, raw_height in enumerate(raw_heights):
        lower = lower_limit + index * minimum_gap
        upper = upper_limit - (len(raw_heights) - index - 1) * minimum_gap
        height = min(max(raw_height, lower), upper)
        if heights and height <= heights[-1]:
            height = heights[-1] + minimum_gap
        heights.append(height)
    section_centres = (
        pelvis_origin.copy(),
        pelvis_origin.copy(),
        np.array([torso_center[0], raw_heights[2], torso_center[2]], dtype=np.float64),
        np.array([torso_center[0], raw_heights[3], torso_center[2]], dtype=np.float64),
        np.array([torso_center[0], raw_heights[4], torso_center[2]], dtype=np.float64),
        np.array([torso_center[0], raw_heights[5], torso_center[2]], dtype=np.float64),
        chest.copy(),
    )
    for centre, height in zip(section_centres, heights):
        centre[1] = height

    # The abdomen controls intentionally share one derived cross-section
    # factor in each transverse axis. This creates a short flat waist band;
    # the neighboring pelvis and ribcage factors still provide the gradual
    # transitions into and out of it.
    abdomen_lateral_factor = 0.76
    abdomen_depth_factor = 0.82

    def section(
        name: str,
        owner: Descriptor,
        center: np.ndarray,
        lateral: float,
        depth: float,
    ) -> _TorsoCageSection:
        point = _guide_point(center, f"torso-cage.{name}.center")
        lateral_value, depth_value = float(lateral), float(depth)
        if not all(math.isfinite(value) and value > 0.0 for value in (lateral_value, depth_value)):
            _fail(f"torso-cage.{name} radii must be finite and positive")
        return _TorsoCageSection(
            name=name,
            owner=owner,
            center=point,
            lateral_radius=lateral_value,
            depth_radius=depth_value,
        )

    sections = (
        section(
            "lower-pelvis",
            pelvis,
            section_centres[0],
            pelvis_size[0] * 0.92,
            pelvis_size[2] * 0.94,
        ),
        section(
            "upper-pelvis",
            pelvis,
            section_centres[1],
            pelvis_size[0] * 0.84,
            pelvis_size[2] * 0.88,
        ),
        section(
            "lower-abdomen",
            torso,
            section_centres[2],
            torso_size[0] * abdomen_lateral_factor,
            torso_size[2] * abdomen_depth_factor,
        ),
        section(
            "waist-abdomen",
            torso,
            section_centres[3],
            torso_size[0] * abdomen_lateral_factor,
            torso_size[2] * abdomen_depth_factor,
        ),
        section(
            "upper-abdomen",
            torso,
            section_centres[4],
            torso_size[0] * abdomen_lateral_factor,
            torso_size[2] * abdomen_depth_factor,
        ),
        section(
            "lower-ribcage",
            torso,
            section_centres[5],
            torso_size[0] * 0.80,
            torso_size[2] * 0.86,
        ),
        section(
            "upper-ribcage-shoulder",
            torso,
            section_centres[6],
            torso_size[0] * 0.90,
            torso_size[2] * 0.96,
        ),
    )
    return _TorsoCage(pelvis_owner=pelvis, torso_owner=torso, sections=sections, axes=_FIXED_GUIDE_AXES)


def _derive_shoulder_frame(
    torso_cage: _TorsoCage,
    head_guide: _HeadGuide,
    limb_guides: tuple[_LimbGuide, ...],
) -> _ShoulderFrame:
    """Derive a bilateral trapezius/shoulder frame without compiling skin.

    The upper-ribcage boundary supplies the shoulder extrema and the existing
    upper-arm root bridge supplies the socket-to-cage relationship.  Anterior
    and posterior four-control wraps deliberately share their central,
    extremum, and socket controls while bowing in opposite forward directions.
    A separate upper-arm-owned deltoid sweep continues through the first
    quarter of the existing upper-arm guide.  No variant-specific values are
    used; all dimensions are consequences of the cage and limb controls.
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
    for side in ("left", "right"):
        limb = by_side[side]
        owner = limb.owner
        source_start = _guide_point(limb.sections[0].centerline[0], f"{_key_text(owner.key)}.shoulder.socket-anchor")
        root_anchor = _guide_point(limb.root_centerline[0], f"{_key_text(owner.key)}.shoulder.extremum")  # type: ignore[index]
        if not math.isfinite(source_start[0]) or source_start[0] == 0.0:
            _fail(f"{_key_text(owner.key)} shoulder socket must be laterally placed")
        expected_sign = -1.0 if side == "left" else 1.0
        if source_start[0] * expected_sign <= 0.0 or root_anchor[0] * expected_sign <= 0.0:
            _fail(f"{_key_text(owner.key)} shoulder controls are on the wrong side")
        span = abs(float(root_anchor[0] - central_anchor[0]))
        if not math.isfinite(span) or span <= 0.0:
            _fail(f"{_key_text(owner.key)} shoulder span is invalid")
        slope = (float(root_anchor[1]) - float(central_anchor[1])) / span
        if not math.isfinite(slope):
            _fail(f"{_key_text(owner.key)} shoulder slope is invalid")

        root_profile = _guide_profile(limb.root_thickness, f"{_key_text(owner.key)}.shoulder.root-profile")  # type: ignore[arg-type]
        arm_profile = _guide_profile(limb.sections[0].thickness, f"{_key_text(owner.key)}.shoulder.arm-profile")
        wrap_depth = max(
            min(upper.depth_radius, max(root_profile)) * 0.62,
            min(arm_profile) * 0.55,
            1.0e-9,
        )
        forward = np.asarray(_FIXED_GUIDE_AXES.forward, dtype=np.float64)
        extremum = np.asarray(root_anchor, dtype=np.float64)
        anterior_wrap = tuple(extremum + forward * wrap_depth)
        posterior_wrap = tuple(extremum - forward * wrap_depth)
        anterior_profile = tuple(float(value) for value in (central_profile[0], max(root_profile) * 0.94, max(root_profile) * 0.86, arm_profile[0]))
        posterior_profile = tuple(float(value) for value in (central_profile[1], max(root_profile) * 0.94, max(root_profile) * 0.86, arm_profile[0]))
        deltoid_profile = tuple(float(value) for value in (max(root_profile) * 0.86, arm_profile[0], arm_profile[1]))
        anterior_points = _guide_curve(
            (central_anchor, anterior_wrap, root_anchor, source_start),
            anterior_profile,
            f"{_key_text(owner.key)}.shoulder.anterior-support",
        )
        posterior_points = _guide_curve(
            (central_anchor, posterior_wrap, root_anchor, source_start),
            posterior_profile,
            f"{_key_text(owner.key)}.shoulder.posterior-return",
        )
        first_section_end = np.asarray(limb.sections[0].centerline[1], dtype=np.float64)
        socket = np.asarray(source_start, dtype=np.float64)
        first_quarter = socket + 0.25 * (first_section_end - socket)
        deltoid_points = _guide_curve(
            (root_anchor, source_start, first_quarter),
            deltoid_profile,
            f"{_key_text(owner.key)}.shoulder.deltoid",
        )
        sides.append(
            _ShoulderSideGuide(
                side=side,
                owner=owner,
                socket_anchor=source_start,
                shoulder_extremum=root_anchor,
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
    head_source = _source_shape(head, form.reference_scale)
    neck_source = path_source(neck)

    pelvis_center = _guide_point(pelvis_source["center"], "pelvis.center")
    pelvis_radii = _guide_radii(pelvis_source["radii"], "pelvis.radii")
    torso_center = _guide_point(torso_source["center"], "torso.center")
    torso_radii = _guide_radii(torso_source["radii"], "torso.radii")
    head_center = _guide_point(head_source["center"], "head.center")
    head_radii = _guide_radii(head_source["radii"], "head.radii")

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
    torso_cage = _derive_torso_cage(
        pelvis,
        torso,
        pelvis_center,
        pelvis_radii,
        torso_center,
        waist_center,
        torso_radii,
        chest_center,
    )
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

    cranium_center = _guide_point(
        head_source["center"] + np.asarray([0.0, 0.10 * head_source["radii"][1], -0.04 * head_source["radii"][2]]),
        "head.cranium_center",
    )
    cranium_radii = _guide_radii(
        head_source["radii"] * np.asarray([0.85, 1.00, 0.85]),
        "head.cranium_radii",
    )
    muzzle_center = _guide_point(
        head_source["center"] + np.asarray([0.0, -0.10 * head_source["radii"][1], 0.62 * head_source["radii"][2]]),
        "head.muzzle_center",
    )
    muzzle_radii = _guide_radii(
        head_source["radii"] * np.asarray([0.50, 0.48, 0.50]),
        "head.muzzle_radii",
    )
    head_anchor = _parent_surface_anchor(neck, head.point, form.reference_scale)
    head_base = _guide_point(
        np.asarray(cranium_center) - np.asarray([0.0, 0.84 * cranium_radii[1], 0.0]),
        "head.transition_end",
    )
    neck_radius = max(min(cranium_radii), _radius_from_shape(neck_source), 0.12)
    neck_start = _torso_cage_boundary_anchor(
        torso_cage,
        float(neck.point[1]),
        np.asarray(neck.point, dtype=np.float64) - np.asarray(torso_cage.upper_boundary.center, dtype=np.float64),
    )
    neck_end = np.asarray(head.point, dtype=np.float64).copy()
    neck_end[1] -= 0.70 * head_source["radii"][1]
    neck_guide = _guide_path(
        neck_start,
        neck_end,
        (float(_radius_from_shape(neck_source) * 1.05), float(_radius_from_shape(neck_source) * 0.78)),
        "neck.transition",
    )
    head_guide = _HeadGuide(
        head_owner=head,
        neck_owner=neck,
        cranium_center=cranium_center,
        cranium_radii=cranium_radii,
        muzzle_center=muzzle_center,
        muzzle_radii=muzzle_radii,
        head_transition=_guide_path(
            head_anchor,
            head_base,
            (neck_radius * 0.82, neck_radius * 0.62),
            "head.transition",
        ),
        head_transition_thickness=(neck_radius * 0.82, neck_radius * 0.62),
        neck_transition=neck_guide,
        neck_transition_thickness=(float(_radius_from_shape(neck_source) * 1.05), float(_radius_from_shape(neck_source) * 0.78)),
        neck_collar_center=_guide_point(neck_start, "neck.collar_center"),
        neck_collar_radii=_guide_radii(
            (float(_radius_from_shape(neck_source) * 1.18), float(_radius_from_shape(neck_source) * 0.72), float(_radius_from_shape(neck_source) * 1.18)),
            "neck.collar_radii",
        ),
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
            adjacent_profile = (
                float(_LIMB_PROFILE_FACTORS[adjacent_role][0]) * _radius_from_shape(adjacent_source)
                if adjacent_role in _LIMB_PROFILE_FACTORS
                else float(np.min(adjacent_source["radii"] * np.asarray([1.02, 0.68, 0.78])))
            )
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

    shoulder_frame = _derive_shoulder_frame(torso_cage, head_guide, tuple(limb_guides))

    paw_guides: list[_PawGuide] = []
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
            heel_center = None
            heel_radii = None
            forefoot_center = None
            forefoot_radii = None
        else:
            # Digitigrade feet are deliberately two masses: a rear heel under
            # the hock and a forward, wider/flatter forefoot pad.  The old
            # single paw oval is not compiled for feet.
            heel_center = _guide_point(source["center"] + np.asarray([0.0, -0.08 * source["radii"][1], -0.20 * source["radii"][2]]), f"{_key_text(desc.key)}.heel_center")
            heel_radii = _guide_radii(source["radii"] * np.asarray([1.02, 0.68, 0.78]), f"{_key_text(desc.key)}.heel_radii")
            forefoot_center = _guide_point(source["center"] + np.asarray([0.0, -0.18 * source["radii"][1], 0.38 * source["radii"][2]]), f"{_key_text(desc.key)}.forefoot_center")
            forefoot_radii = _guide_radii(source["radii"] * np.asarray([1.30, 0.42, 0.82]), f"{_key_text(desc.key)}.forefoot_radii")
            paw_center = heel_center
            paw_radii = heel_radii
        parent = by_key.get(desc.parent) if desc.parent is not None else None
        attachment_centerline = None
        attachment_radius = None
        attachment_kind = None
        if parent is not None:
            parent_source = _source_shape(parent, form.reference_scale)
            attachment_target = heel_center if heel_center is not None else paw_center
            attachment_start = (
                parent_source["to"]
                if role == "foot" and parent.key[3] == "shin"
                else _parent_surface_anchor(parent, attachment_target, form.reference_scale)
            )
            attachment_centerline = _guide_path(
                attachment_start,
                attachment_target,
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
                heel_center=heel_center,
                heel_radii=heel_radii,
                forefoot_center=forefoot_center,
                forefoot_radii=forefoot_radii,
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
        if not all(math.isfinite(value) and value > 0.0 for value in (section.lateral_radius, section.depth_radius)):
            _fail(f"torso-cage[{index}] radii must be finite and positive")
        _guide_point_checked(section.center, f"torso-cage[{index}].center", bounds)
    if cage.axes != guide.topology.axes or cage.axes != _FIXED_GUIDE_AXES:
        _fail("torso cage axes must match the guide topology and fixed prototype axes")
    if any(cage.sections[index].center[1] >= cage.sections[index + 1].center[1] for index in range(len(cage.sections) - 1)):
        _fail("torso cage sections must rise monotonically from pelvis to shoulders")

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
        extremum = limb.root_centerline[0]
        if side.socket_anchor != socket:
            _fail(f"{where} socket anchor must equal the existing upper-arm source start")
        if side.shoulder_extremum != extremum:
            _fail(f"{where} shoulder extremum must equal the existing torso root anchor")
        expected_span = abs(float(extremum[0] - frame.central_anchor[0]))
        if not math.isfinite(expected_span) or expected_span <= 0.0:
            _fail(f"{where} derived shoulder span is invalid")
        expected_slope = (float(extremum[1]) - float(frame.central_anchor[1])) / expected_span
        if not math.isclose(side.span, expected_span, rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(side.slope, expected_slope, rel_tol=1.0e-9, abs_tol=1.0e-12):
            _fail(f"{where} span and slope are not derived from cage and root controls")
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
        if side.anterior_support.points[1][2] <= side.shoulder_extremum[2] or side.posterior_return.points[1][2] >= side.shoulder_extremum[2]:
            _fail(f"{where} anterior and posterior wraps must occupy distinct depth")
        first_quarter = np.asarray(limb.sections[0].centerline[0]) + 0.25 * (
            np.asarray(limb.sections[0].centerline[1]) - np.asarray(limb.sections[0].centerline[0])
        )
        if side.deltoid_sweep.points[0] != side.shoulder_extremum or side.deltoid_sweep.points[1] != side.socket_anchor or not np.allclose(side.deltoid_sweep.points[2], first_quarter, rtol=0.0, atol=1.0e-12):
            _fail(f"{where} deltoid sweep must overlap the root and first quarter of the upper-arm guide")

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
    for index, paw in enumerate(guide.paw_guides):
        mass(paw.paw_center, paw.paw_radii, f"paw[{index}].paw")
        mass(paw.heel_center, paw.heel_radii, f"paw[{index}].heel")
        mass(paw.forefoot_center, paw.forefoot_radii, f"paw[{index}].forefoot")
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
        "owners": [_address_json(torso_cage.pelvis_owner.key), _address_json(torso_cage.torso_owner.key)],
        "axes": cage_axes,
        "orientation": "elliptical cross-section rings lie in the lateral/forward plane and rise along the up axis",
        "sections": [
            {
                "name": section.name,
                "owner": _address_json(section.owner.key),
                "center": _point_json(section.center),
                "lateral_radius": float(section.lateral_radius),
                "depth_radius": float(section.depth_radius),
            }
            for section in torso_cage.sections
        ],
        "connections": [
            {"from": torso_cage.sections[index].name, "to": torso_cage.sections[index + 1].name}
            for index in range(len(torso_cage.sections) - 1)
        ],
    }
    head = guide.head_guide
    head_controls = {
        "owners": [_address_json(head.head_owner.key), _address_json(head.neck_owner.key)],
        "masses": [
            _mass_json("cranium", head.cranium_center, head.cranium_radii),
            _mass_json("muzzle", head.muzzle_center, head.muzzle_radii),
            _mass_json("neck-collar", head.neck_collar_center, head.neck_collar_radii),
        ],
        "sections": [
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
            if paw.attachment_centerline is None:
                _fail(f"paw attachment anchor is incomplete for {_key_text(paw.owner.key)}")
            anchors.append({
                "name": "forearm-distal-boundary" if paw.owner.key[3] == "hand" else "hock-endpoint",
                "kind": "parent-surface-anchor" if paw.owner.key[3] == "hand" else "endpoint",
                "point": _point_json(paw.attachment_centerline[0]),
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
        attachment = _path_json("attachment", item.attachment_centerline, (item.attachment_radius,) if item.attachment_radius is not None else None, path_kind=item.attachment_kind)
        if attachment is None or item.owner.parent is None or item.owner.parent not in owners_by_key:
            _fail(f"paw attachment source is incomplete for {_key_text(item.owner.key)}")
        parent = owners_by_key[item.owner.parent]
        parent_limb = limb_by_owner.get(parent.key)
        if parent_limb is None or not parent_limb.sections:
            _fail(f"paw attachment parent limb is missing for {_key_text(item.owner.key)}")
        attachment_source = {
            "owner": _address_json(parent.key),
            "anchor": "forearm-distal-boundary" if item.owner.key[3] == "hand" else "hock-endpoint",
            "point": _point_json(item.attachment_centerline[0]),
            "boundary_point": _point_json(parent_limb.sections[-1].centerline[1]),
        }
        paw_masses = (
            (_mass_json("paw", item.paw_center, item.paw_radii),)
            if item.heel_center is None
            else (_mass_json("heel", item.heel_center, item.heel_radii), _mass_json("forefoot", item.forefoot_center, item.forefoot_radii))
        )
        paw_controls.append({
            "owner": _address_json(item.owner.key),
            "masses": [value for value in paw_masses if value is not None],
            "attachment": attachment,
            "attachment_source": attachment_source,
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
            "head": head_controls,
            "limbs": limb_controls,
            "paws": paw_controls,
            "tails": tail_controls,
        },
        "boundary": "private disposable regional controls; source-owned AddressKeys only; not a semantic or runtime contract",
    }


def _compile_hybrid_guide(guide: _HybridGuide) -> tuple[Field, ...]:
    """Adapt regional guides to the disposable analytic-field backend."""

    fields: list[Field] = []
    limbs_by_owner = {item.owner.key: item for item in guide.limb_guides}
    paws_by_owner = {item.owner.key: item for item in guide.paw_guides}
    tails_by_owner = {item.owner.key: item for item in guide.tail_guides}
    head = guide.head_guide

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

    torso_cage = guide.torso_cage

    def add_head(desc: Descriptor) -> None:
        add_ellipsoid(desc, "cranium", head.cranium_center, head.cranium_radii)
        add_ellipsoid(desc, "muzzle", head.muzzle_center, head.muzzle_radii)
        add_path(desc, "head-base-bridge", head.head_transition, head.head_transition_thickness, "tapered-segment")

    def add_neck(desc: Descriptor) -> None:
        add_path(desc, "tapered-neck", head.neck_transition, head.neck_transition_thickness, "tapered-segment")
        add_ellipsoid(desc, "neck-collar", head.neck_collar_center, head.neck_collar_radii)

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
        if paw.heel_center is None:
            add_ellipsoid(desc, "paw", paw.paw_center, paw.paw_radii)
        else:
            add_ellipsoid(desc, "heel", paw.heel_center, paw.heel_radii)  # type: ignore[arg-type]
            if paw.forefoot_center is None or paw.forefoot_radii is None:
                _fail(f"foot forefoot controls are incomplete for {_key_text(paw.owner.key)}")
            add_ellipsoid(desc, "forefoot", paw.forefoot_center, paw.forefoot_radii)
        if paw.attachment_centerline is not None:
            add_path(desc, "extremity-bridge", paw.attachment_centerline, (paw.attachment_radius,), paw.attachment_kind or "capsule")

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
        if desc.key == head.head_owner.key:
            add_head(desc)
        if desc.key == head.neck_owner.key:
            add_neck(desc)
        if desc.key in limbs_by_owner:
            add_limb(desc, limbs_by_owner[desc.key])
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[str, tuple[str, ...], str, str]], dict[str, Any], dict[str, Any]]:
    if type(samples) is not int or samples > MAX_SAMPLES or samples < 16 or samples**3 > MAX_VOXELS:
        _fail("sampling configuration exceeds bounded limits")
    if not math.isfinite(float(padding)) or padding < 0.0 or not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("padding and smooth-k must be finite, with non-negative padding and positive smooth-k")
    fields = _compound_fields(form, descriptors)
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
        "head": (204, 121, 190),
        "limb": (96, 174, 218),
        "joint": (235, 124, 100),
        "paw": (134, 198, 135),
        "tail": (225, 181, 88),
    }
    _draw_torso_cage(draw, frame, guide.torso_cage, colours["cage"])
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
        if item.shoulder_center is not None and item.shoulder_radii is not None:
            _draw_guide_mass(draw, frame, item.shoulder_center, item.shoulder_radii, colours["limb"])
        if item.joint is not None:
            _draw_guide_mass(draw, frame, item.joint.center, item.joint.radii, colours["joint"])
    for item in guide.paw_guides:
        if item.heel_center is None:
            _draw_guide_mass(draw, frame, item.paw_center, item.paw_radii, colours["paw"])
        else:
            _draw_guide_mass(draw, frame, item.heel_center, item.heel_radii, colours["paw"])
        if item.forefoot_center is not None and item.forefoot_radii is not None:
            _draw_guide_mass(draw, frame, item.forefoot_center, item.forefoot_radii, colours["paw"])
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
    draw.text((16, 42), "guide: skin-driving torso cage rings / regional limb sections / endpoint joints / heel-pad paws    skin: deterministic compiled field", fill=(167, 176, 190), font=font)
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
            "generator": {"bundle_version": 2, "samples_per_axis": samples, "padding": padding, "smooth_union": {"operator": "polynomial_cubic_smooth_min", "k": smooth_k, "fold_order": "source_address_then_recipe_order"}, "field_primitives": ["torso-cage", "ellipsoid", "capsule", "linear-radius-tapered-segment"], "field_recipes": ["torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar", "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal", "thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint", "elbow", "knee", "hock", "root-bridge", "hip-transition", "paw", "heel", "forefoot", "extremity-bridge", "tail-segment", "tail-tip-extension", "tail-tip-cap", "tail-root-bridge", "tail-root-collar"], "ownership": "recipe fields are source-owned; the blended torso-cage recipe is torso-owned and winner labels select the nearest axial cage-section owner (lower-index tie break), exposing only source AddressKeys", "boundary": "disposable exploratory visual proof; not production geometry, SDF, collision, rig, topology, or Readiness evidence"},
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

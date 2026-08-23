#!/usr/bin/env python3
"""Private successor-surface experiment for the disposable form preview.

This module is intentionally adjacent to, rather than a modification of,
``surface_preview.py``.  It consumes the existing private hybrid guide and
replaces the torso/shoulder, head/neck, four limb-chain, hand/foot, and tail
skin consumers with explicitly identified profile sweeps. Thigh/hip connector
fields remain an explicit temporary bridge so the
experiment can still produce a whole-body mesh without pretending that those
connectors have been redesigned.

The representation is exploratory and disposable.  It is not a production
surface backend, topology contract, SDF, collision shape, or runtime API.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib
import json
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
from skimage.measure import marching_cubes


try:
    _baseline = importlib.import_module("surface_preview")
except ModuleNotFoundError:  # pragma: no cover - direct source-tree execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    _baseline = importlib.import_module("surface_preview")


# V8 consumes the current v10 regional guide's seven source-authored torso,
# eight-station branched head/neck, bilateral five-station arm profile, and
# bilateral five-station authored leg profile.  The torso evaluator and every
# non-profile consumer remain shared with the predecessor.
FORMAT = "creature-kernel.disposable-successor-surface-preview.v8"
REGIONAL_GUIDE_FORMAT = _baseline.REGIONAL_GUIDE_FORMAT
CONSUMER_ID = "successor-surface-v1"
SUCCESSOR_REGION_ID = "successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-profile-sweeps-v12"
TORSO_PROFILE_OPERATION = "rounded-superellipse-axial-profile-sweep-v1"
_HEAD_NECK_PROFILE_OPERATION = "authored-head-neck-branched-route-profile-v1"
_ARM_PROFILE_OPERATION = "authored-arm-profile-route-v1"
_LEG_PROFILE_OPERATION = "authored-leg-profile-route-v1"
_FOOT_PROFILE_OPERATION = "authored-foot-profile-route-v1"
_FOOT_PROFILE_SECTION_NAMES = ("hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe")
_FOOT_PROFILE_OWNER_ROLES = ("shin", "foot", "foot", "foot", "foot")
_HEAD_NECK_ROUTE_TOPOLOGY = (
    ("vertical-neck-cranium", (0, 1, 2, 3, 4), "up", ("lateral", "forward")),
    ("forward-muzzle", (3, 5, 6, 7), "forward", ("lateral", "up")),
)
# These are the exact indexed bindings retained by producer v11 for the v1
# authored head/neck profile.  They are lineage admission checks, not new
# source controls or geometry parameters.
_HEAD_NECK_FRAME_INDICES = {"head": 0, "neck": 1}
_HEAD_NECK_LANDMARK_INDICES = (6, 7, 2, 1, 0, 4, 3, 5)
_HEAD_NECK_RADIUS_REFERENCE_INDICES = (
    (22, 23, 21), (25, 26, 24), (10, 11, 9), (7, 8, 6),
    (4, 5, 3), (16, 17, 15), (13, 14, 12), (19, 20, 18),
)
TORSO_SUPERELLIPSE_EXPONENT = 4.0
DEFAULT_SAMPLES = 56
DEFAULT_PADDING = 0.50
# Capture framing is a baseline-compatible concern, separate from the
# successor mesh sampling domain.  Source this value from the baseline
# generator so the two consumers cannot silently drift apart.
DEFAULT_CAPTURE_PADDING = _baseline.DEFAULT_PADDING
DEFAULT_SMOOTH_K = 0.10
MAX_SAMPLES = 96
MAX_VOXELS = 96**3
MAX_FIELD_VALUES = 16_000_000


class SuccessorPreviewError(RuntimeError):
    """A fail-closed successor experiment error."""


def _fail(message: str) -> None:
    raise SuccessorPreviewError(message)


@dataclass(frozen=True)
class _ProfileSection:
    """One ordered, source-owned section in a frame-aware profile sweep.

    Tuples are used instead of mutable arrays so a compiled private profile
    cannot alias or mutate the guide.  ``transverse_axes`` are ordered as
    (first transverse axis, second transverse axis) and retain a deterministic
    orientation with ``tangent``.  The representation is intentionally private and
    disposable; it is a reusable evaluator input, not a geometry contract.
    """

    name: str
    owner: Any
    center: tuple[float, float, float]
    tangent: tuple[float, float, float]
    transverse_axes: tuple[tuple[float, float, float], tuple[float, float, float]]
    transverse_radii: tuple[float, float]
    path_length: float
    # Only the successor torso profile populates this optional triple.  The
    # generic limb/head/tail sweeps retain their existing two-radius profile.
    # The first value is lateral, the second is +forward/anterior, and the
    # third is -forward/posterior.
    torso_cardinal_radii: tuple[float, float, float] | None = None
    axial_position: float | None = None
    # Generic station-volume extension.  Head/neck route stations retain the
    # authored radius along their route tangent here; ordinary two-radius
    # sweeps leave it unset and therefore retain their existing evaluator.
    tangent_radius: float | None = None
    source_section_index: int | None = None
    station_volume_axes: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ] | None = None
    station_volume_radii: tuple[float, float, float] | None = None

    @property
    def radii(self) -> tuple[float, float]:
        return self.transverse_radii

    @property
    def axes(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        return self.transverse_axes

    @property
    def cardinal_radii(self) -> tuple[float, float, float] | None:
        """Return (lateral, anterior, posterior) for a torso section."""

        return self.torso_cardinal_radii


@dataclass(frozen=True)
class _ProfileEndpointCap:
    """Finite oriented ellipsoidal cap at one profile endpoint."""

    side: str
    center: tuple[float, float, float]
    outward_tangent: tuple[float, float, float]
    transverse_axes: tuple[tuple[float, float, float], tuple[float, float, float]]
    transverse_radii: tuple[float, float]
    axial_radius: float


@dataclass(frozen=True)
class _ProfileJointTransition:
    """A source-section-owned transition at a genuinely bent station."""

    section_index: int
    owner: Any
    center: tuple[float, float, float]
    tangent: tuple[float, float, float]
    transverse_axes: tuple[tuple[float, float, float], tuple[float, float, float]]
    transverse_radii: tuple[float, float]
    axial_radius: float


@dataclass(frozen=True)
class _ProfileSweep:
    """Ordered profile sections and their finite oriented endpoint caps."""

    sections: tuple[_ProfileSection, ...]
    endpoint_caps: tuple[_ProfileEndpointCap, _ProfileEndpointCap]
    internal_transitions: tuple[_ProfileJointTransition, ...] = ()
    _validated: bool = field(default=False, compare=False, repr=False)
    profile_operation: str = "symmetric-ellipse"

    def __post_init__(self) -> None:
        if not self.internal_transitions:
            if self.profile_operation == _HEAD_NECK_PROFILE_OPERATION:
                object.__setattr__(self, "internal_transitions", ())
            else:
                object.__setattr__(self, "internal_transitions", _derive_bend_transitions(self.sections))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(section.name for section in self.sections)

    @property
    def owners(self) -> tuple[Any, ...]:
        return tuple(section.owner for section in self.sections)

    # These compatibility views keep existing attribution/bounds diagnostics
    # readable while the evaluator consumes the generic section records.
    @property
    def centers(self) -> np.ndarray:
        return np.asarray([section.center for section in self.sections], dtype=np.float64)

    @property
    def lateral_radii(self) -> np.ndarray:
        return np.asarray([section.transverse_radii[0] for section in self.sections], dtype=np.float64)

    @property
    def depth_radii(self) -> np.ndarray:
        return np.asarray([section.transverse_radii[1] for section in self.sections], dtype=np.float64)


@dataclass(frozen=True)
class _RegionalProfileSweep:
    """One guide-derived profile sweep with source ownership and a recipe label."""

    recipe: str
    owner: Any
    sweep: _ProfileSweep


@dataclass(frozen=True)
class _ShoulderEnvelopeSweep:
    """One authored shoulder branch with its guide-relative frame axes."""

    side: str
    owner: Any
    sweep: _ProfileSweep
    preferred_up: tuple[float, float, float]
    preferred_forward: tuple[float, float, float]

    @property
    def recipe(self) -> str:
        return f"{self.side}-shoulder-envelope"


@dataclass(frozen=True)
class _ExtremitySweep:
    """One named hand or foot sweep with section-level source ownership."""

    name: str
    side: str
    source_owners: tuple[Any, ...]
    sweep: _ProfileSweep
    kind: str

    @property
    def recipe(self) -> str:
        """Stable diagnostic label matching the element name."""

        return self.name

    @property
    def owners(self) -> tuple[Any, ...]:
        return self.sweep.owners

    @property
    def section_names(self) -> tuple[str, ...]:
        return self.sweep.names

    @property
    def sections_consumed(self) -> int:
        return len(self.sweep.sections)


@dataclass(frozen=True)
class _RouteStation:
    """One full-volume route station assembled from guide-owned controls."""

    name: str
    owner: Any
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    source_section_index: int


@dataclass(frozen=True)
class _LimbChainSweep:
    """One bilateral limb-chain sweep with per-section source ownership."""

    chain_name: str
    source_owners: tuple[Any, ...]
    sweep: _ProfileSweep
    route_kind: str = "limb"
    source_stations: tuple[Any, ...] = ()

    @property
    def name(self) -> str:
        return self.chain_name

    @property
    def owners(self) -> tuple[Any, ...]:
        return self.sweep.owners

    @property
    def section_names(self) -> tuple[str, ...]:
        return self.sweep.names

    @property
    def sections_consumed(self) -> int:
        return len(self.sweep.sections)

    @property
    def is_arm_profile_route(self) -> bool:
        return self.route_kind == "arm-profile"

    @property
    def is_leg_profile_route(self) -> bool:
        return self.route_kind == "leg-profile"

    @property
    def is_foot_profile_route(self) -> bool:
        return self.route_kind == "foot-profile"


@dataclass(frozen=True)
class _TailElement:
    """One explicitly named, source-owned successor tail element.

    Tail elements deliberately retain the guide's source owner while exposing
    the generic profile sweep consumed by the evaluator.  ``kind`` describes
    the guide control family; it is diagnostic metadata, not a new semantic
    owner.
    """

    name: str
    owner: Any
    sweep: _ProfileSweep
    kind: str

    @property
    def source_owners(self) -> tuple[Any, ...]:
        return (self.owner,)

    @property
    def owners(self) -> tuple[Any, ...]:
        return self.sweep.owners

    @property
    def section_names(self) -> tuple[str, ...]:
        return self.sweep.names

    @property
    def sections_consumed(self) -> int:
        return len(self.sweep.sections)


# Keep a descriptive alias available to focused consumers of this disposable
# experiment; the region stores the concrete named elements above.
_TailSweep = _TailElement


@dataclass(frozen=True)
class SuccessorRegion:
    """Explicit successor torso/shoulder/head/neck/limb/extremity/tail representation.

    ``bridge_fields`` are untouched baseline fields for all regions outside
    this successor region.  They are kept here, rather than silently folded
    into the successor, so the remaining root/hip connector consumers have a
    stable extension point and the temporary boundary remains inspectable.
    """

    consumer_id: str
    region_id: str
    loft: _ProfileSweep
    shoulder_sweeps: tuple[_ShoulderEnvelopeSweep, ...]
    bridge_fields: tuple[Any, ...]
    replaced_baseline_recipes: tuple[str, ...]
    source_owners: tuple[Any, ...]
    head_neck_sweeps: tuple[_RegionalProfileSweep, ...] = ()
    head_neck_profile: Any | None = None
    leg_profile: Any | None = None
    foot_profile: Any | None = None
    limb_sweeps: tuple[_LimbChainSweep, ...] = ()
    extremity_sweeps: tuple[_ExtremitySweep, ...] = ()
    tail_elements: tuple[_TailElement, ...] = ()

    @property
    def section_names(self) -> tuple[str, ...]:
        return self.loft.names

    @property
    def sections_consumed(self) -> int:
        return len(self.loft.names)

    @property
    def shoulder_sweeps_consumed(self) -> int:
        return len(self.shoulder_sweeps)

    @property
    def chain_sweeps(self) -> tuple[_LimbChainSweep, ...]:
        """Compatibility alias for the named successor limb chains."""

        return self.limb_sweeps

    @property
    def arm_sweeps(self) -> tuple[_LimbChainSweep, ...]:
        """The four shared authored upper-arm/forearm route sweeps."""

        return tuple(item for item in self.limb_sweeps if item.is_arm_profile_route)

    @property
    def leg_sweeps(self) -> tuple[_LimbChainSweep, ...]:
        """The two shared authored leg-profile routes."""

        return tuple(item for item in self.limb_sweeps if item.is_leg_profile_route)

    @property
    def hand_sweeps(self) -> tuple[_ExtremitySweep, ...]:
        return tuple(item for item in self.extremity_sweeps if item.kind in {"hand-attachment", "hand-paw"})

    @property
    def foot_sweeps(self) -> tuple[_ExtremitySweep, ...]:
        return tuple(item for item in self.extremity_sweeps if item.kind == "foot-chain")

    @property
    def tail_sweeps(self) -> tuple[_TailElement, ...]:
        """Compatibility/readability view of the explicit tail elements."""

        return self.tail_elements


@dataclass(frozen=True)
class SuccessorMesh:
    """Deterministic in-memory full-body result for one variant."""

    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray
    labels: tuple[tuple[str, tuple[str, ...], str, str], ...]
    metrics: dict[str, Any]
    representation: SuccessorRegion
    grid: dict[str, Any]


@dataclass(frozen=True)
class _Component:
    owner: Any
    recipe: str
    evaluate: Callable[[np.ndarray], np.ndarray]
    bounds: tuple[np.ndarray, np.ndarray]
    successor: bool
    attribution: Callable[[np.ndarray], tuple[tuple[str, tuple[str, ...], str, str], ...]] | None = None


def _finite_positive(values: tuple[float, ...], where: str) -> None:
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        _fail(f"{where} must contain finite positive values")


_FRAME_TOLERANCE = 1.0e-7
_DEGENERATE_TOLERANCE = 1.0e-12
_BEND_COLLINEAR_TOLERANCE = 1.0e-8
_TANGENT_ALIGNMENT_TOLERANCE = 1.0e-7
_SHOULDER_BOUNDARY_TOLERANCE = 1.0e-10
_SHOULDER_BOUNDARY_ITERATIONS = 64
_SHOULDER_BOUNDARY_MAX_EXTENSION = 4.0


def _vec3(value: Any, where: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        _fail(f"{where} must be a finite three-vector")
    return result


def _unit(value: np.ndarray, where: str) -> np.ndarray:
    length = float(np.linalg.norm(value))
    if not math.isfinite(length) or length <= _DEGENERATE_TOLERANCE:
        _fail(f"{where} must be non-degenerate")
    return value / length


def _derive_bend_transitions(sections: tuple[_ProfileSection, ...]) -> tuple[_ProfileJointTransition, ...]:
    """Create transitions only where adjacent centerline spans genuinely bend."""

    transitions: list[_ProfileJointTransition] = []
    for index in range(1, len(sections) - 1):
        previous = _vec3(sections[index - 1].center, f"profile section[{index - 1}] center")
        center = _vec3(sections[index].center, f"profile section[{index}] center")
        following = _vec3(sections[index + 1].center, f"profile section[{index + 1}] center")
        incoming = center - previous
        outgoing = following - center
        incoming_length = float(np.linalg.norm(incoming))
        outgoing_length = float(np.linalg.norm(outgoing))
        if incoming_length <= _DEGENERATE_TOLERANCE or outgoing_length <= _DEGENERATE_TOLERANCE:
            continue
        direction_alignment = float(np.dot(incoming / incoming_length, outgoing / outgoing_length))
        if direction_alignment <= -1.0 + _BEND_COLLINEAR_TOLERANCE:
            _fail(f"profile section[{index}] reverses its ordered centerline")
        if direction_alignment >= 1.0 - _BEND_COLLINEAR_TOLERANCE:
            continue
        section = sections[index]
        transitions.append(_ProfileJointTransition(
            section_index=index,
            owner=section.owner,
            center=section.center,
            tangent=section.tangent,
            transverse_axes=section.transverse_axes,
            transverse_radii=section.transverse_radii,
            axial_radius=min(section.transverse_radii),
        ))
    return tuple(transitions)


def _frame_from_tangent(
    tangent: np.ndarray,
    preferred_first: np.ndarray,
    preferred_second: np.ndarray,
    where: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Derive a deterministic oriented transverse frame."""

    tangent = _unit(tangent, f"{where}.tangent")
    first = preferred_first - float(np.dot(preferred_first, tangent)) * tangent
    if float(np.linalg.norm(first)) <= _DEGENERATE_TOLERANCE:
        first = preferred_second - float(np.dot(preferred_second, tangent)) * tangent
    first = _unit(first, f"{where}.transverse-first")
    second = _unit(np.cross(first, tangent), f"{where}.transverse-second")
    if float(np.dot(second, preferred_second)) < 0.0:
        first = -first
        second = -second
    return tangent, first, second


def _validate_profile_sweep(sweep: _ProfileSweep) -> None:
    """Fail closed on malformed profile frames, spans, path lengths or caps."""

    if sweep._validated:
        return
    sections = sweep.sections
    if len(sections) < 2:
        _fail("profile sweep requires at least two ordered sections")
    if sweep.profile_operation not in {
        "symmetric-ellipse",
        TORSO_PROFILE_OPERATION,
        _HEAD_NECK_PROFILE_OPERATION,
        _ARM_PROFILE_OPERATION,
        _LEG_PROFILE_OPERATION,
        _FOOT_PROFILE_OPERATION,
    }:
        _fail(f"profile sweep has unknown profile operation {sweep.profile_operation!r}")
    is_head_neck_route = sweep.profile_operation == _HEAD_NECK_PROFILE_OPERATION
    is_authored_profile_route = sweep.profile_operation in {
        _ARM_PROFILE_OPERATION,
        _LEG_PROFILE_OPERATION,
        _FOOT_PROFILE_OPERATION,
    }
    centers = tuple(_vec3(section.center, f"profile-section[{index}].center") for index, section in enumerate(sections))
    previous_path = None
    for index, section in enumerate(sections):
        where = f"profile-section[{index}]"
        center = centers[index]
        tangent = _vec3(section.tangent, f"{where}.tangent")
        first = _vec3(section.transverse_axes[0], f"{where}.transverse-first")
        second = _vec3(section.transverse_axes[1], f"{where}.transverse-second")
        _finite_positive(tuple(float(value) for value in section.transverse_radii), f"{where}.radii")
        if section.tangent_radius is not None:
            _finite_positive((float(section.tangent_radius),), f"{where}.tangent-radius")
        elif is_head_neck_route:
            _fail(f"{where} is missing its authored tangent-axis radius")
        if (is_head_neck_route or is_authored_profile_route) and type(section.source_section_index) is not int:
            _fail(f"{where} is missing its authored source section index")
        station_axes = section.station_volume_axes
        station_radii = section.station_volume_radii
        if (station_axes is None) != (station_radii is None):
            _fail(f"{where} station-volume axes and radii must be provided together")
        if is_authored_profile_route and station_axes is None:
            _fail(f"{where} is missing its full authored station volume")
        if station_axes is not None and station_radii is not None:
            if len(station_axes) != 3 or len(station_radii) != 3:
                _fail(f"{where} station volume must have exactly three axes and radii")
            station_vectors = tuple(_vec3(axis, f"{where}.station-volume-axis[{axis_index}]") for axis_index, axis in enumerate(station_axes))
            _finite_positive(tuple(float(value) for value in station_radii), f"{where}.station-volume-radii")
            if any(
                not math.isclose(float(np.linalg.norm(axis)), 1.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE)
                for axis in station_vectors
            ):
                _fail(f"{where} station-volume axes must be unit length")
            if max(
                abs(float(np.dot(station_vectors[first], station_vectors[second])))
                for first in range(3) for second in range(first + 1, 3)
            ) > _FRAME_TOLERANCE:
                _fail(f"{where} station-volume axes must be orthogonal")
        cardinal_radii = section.cardinal_radii
        if sweep.profile_operation == TORSO_PROFILE_OPERATION:
            if cardinal_radii is None:
                _fail(f"{where} is missing torso cardinal radii")
            _finite_positive(tuple(float(value) for value in cardinal_radii), f"{where}.cardinal-radii")
            if not math.isclose(
                float(section.transverse_radii[0]),
                float(cardinal_radii[0]),
                rel_tol=0.0,
                abs_tol=_FRAME_TOLERANCE,
            ):
                _fail(f"{where} lateral compatibility radius disagrees with cardinal radius")
            if float(section.transverse_radii[1]) + _FRAME_TOLERANCE < max(float(cardinal_radii[1]), float(cardinal_radii[2])):
                _fail(f"{where} compatibility depth radius does not enclose cardinal radii")
        elif cardinal_radii is not None:
            _fail(f"{where} symmetric profile cannot carry torso cardinal radii")
        tangent_length = float(np.linalg.norm(tangent))
        first_length = float(np.linalg.norm(first))
        second_length = float(np.linalg.norm(second))
        if not all(math.isclose(length, 1.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE) for length in (tangent_length, first_length, second_length)):
            _fail(f"{where} frame vectors must be unit length")
        if max(abs(float(np.dot(tangent, first))), abs(float(np.dot(tangent, second))), abs(float(np.dot(first, second)))) > _FRAME_TOLERANCE:
            _fail(f"{where} frame vectors must be orthogonal")
        if not is_head_neck_route:
            if index == 0:
                expected_tangent = centers[1] - centers[0]
            elif index == len(sections) - 1:
                expected_tangent = centers[-1] - centers[-2]
            else:
                expected_tangent = centers[index + 1] - centers[index - 1]
            expected_length = float(np.linalg.norm(expected_tangent))
            if expected_length <= _DEGENERATE_TOLERANCE:
                _fail(f"{where} expected centerline tangent is degenerate")
            expected_tangent /= expected_length
            if float(np.dot(tangent / tangent_length, expected_tangent)) < 1.0 - _TANGENT_ALIGNMENT_TOLERANCE:
                _fail(f"{where}.tangent must follow the ordered centerline")
        path = float(section.path_length)
        if not math.isfinite(path) or (previous_path is not None and path <= previous_path):
            _fail(f"{where}.path_length must be finite and strictly increasing")
        if previous_path is not None and float(np.linalg.norm(center - centers[index - 1])) <= _DEGENERATE_TOLERANCE:
            _fail(f"{where} span is degenerate")
        previous_path = path

    if len(sweep.endpoint_caps) != 2:
        _fail("profile sweep requires exactly two endpoint caps")
    for index, cap in enumerate(sweep.endpoint_caps):
        where = f"profile-cap[{index}]"
        _vec3(cap.center, f"{where}.center")
        outward = _vec3(cap.outward_tangent, f"{where}.outward_tangent")
        first = _vec3(cap.transverse_axes[0], f"{where}.transverse-first")
        second = _vec3(cap.transverse_axes[1], f"{where}.transverse-second")
        _finite_positive((*tuple(float(value) for value in cap.transverse_radii), float(cap.axial_radius)), f"{where}.radii")
        if not all(math.isclose(float(np.linalg.norm(vector)), 1.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE) for vector in (outward, first, second)):
            _fail(f"{where} frame vectors must be unit length")
        if max(abs(float(np.dot(outward, first))), abs(float(np.dot(outward, second))), abs(float(np.dot(first, second)))) > _FRAME_TOLERANCE:
            _fail(f"{where} frame vectors must be orthogonal")
        endpoint = sections[0 if index == 0 else -1]
        if not np.allclose(_vec3(cap.center, where), _vec3(endpoint.center, f"profile endpoint[{index}]"), rtol=0.0, atol=_FRAME_TOLERANCE):
            _fail(f"{where}.center must close the corresponding profile endpoint")
        if not all(np.allclose(cap.transverse_axes[axis], endpoint.transverse_axes[axis], rtol=0.0, atol=_FRAME_TOLERANCE) for axis in (0, 1)):
            _fail(f"{where} transverse axes must close the corresponding profile endpoint")
        outward_alignment = float(np.dot(outward, _vec3(endpoint.tangent, f"profile endpoint[{index}].tangent")))
        expected_alignment = -1.0 if index == 0 else 1.0
        if outward_alignment * expected_alignment < 1.0 - _FRAME_TOLERANCE:
            _fail(f"{where} orientation does not point away from the profile")
    expected_transitions = () if is_head_neck_route else _derive_bend_transitions(sections)
    if tuple(item.section_index for item in sweep.internal_transitions) != tuple(item.section_index for item in expected_transitions):
        _fail("profile sweep internal transitions must match genuinely bent stations")
    for transition in sweep.internal_transitions:
        where = f"profile-transition[{transition.section_index}]"
        if transition.section_index <= 0 or transition.section_index >= len(sections) - 1:
            _fail(f"{where} must be an internal section")
        section = sections[transition.section_index]
        if transition.owner is not section.owner:
            _fail(f"{where} must retain its source section owner")
        if not np.allclose(transition.center, section.center, rtol=0.0, atol=_FRAME_TOLERANCE):
            _fail(f"{where} must be centered at its source section")
        if transition.tangent != section.tangent or transition.transverse_axes != section.transverse_axes or transition.transverse_radii != section.transverse_radii:
            _fail(f"{where} must reuse its source section frame and profile")
        _vec3(transition.tangent, f"{where}.tangent")
        first = _vec3(transition.transverse_axes[0], f"{where}.transverse-first")
        second = _vec3(transition.transverse_axes[1], f"{where}.transverse-second")
        tangent = _vec3(transition.tangent, f"{where}.tangent")
        if max(abs(float(np.dot(tangent, first))), abs(float(np.dot(tangent, second))), abs(float(np.dot(first, second)))) > _FRAME_TOLERANCE:
            _fail(f"{where} frame vectors must be orthogonal")
        _finite_positive((*transition.transverse_radii, transition.axial_radius), f"{where}.radii")
        if transition.axial_radius > min(transition.transverse_radii) + _FRAME_TOLERANCE:
            _fail(f"{where}.axial_radius must not exceed its source profile")
    object.__setattr__(sweep, "_validated", True)


def _guide_member(value: Any, name: str, where: str, *, required: bool = True) -> Any:
    """Read a private guide member from either an object or a v6-like map."""

    if isinstance(value, dict):
        result = value.get(name)
    else:
        result = getattr(value, name, None)
    if result is None and required:
        _fail(f"{where} is missing {name!r}")
    return result


def _torso_section_center(
    source: Any,
    index: int,
    axis_anchor: np.ndarray | None,
    axial_axis: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Resolve a v6 exact axial position while retaining v5 center fallback.

    The v6 guide carries the exact section center (and therefore its axial
    position in the fixed guide frame).  A scalar ``axial_position`` is also
    accepted for focused private consumers that provide that equivalent form.
    """

    name = _guide_member(source, "name", f"torso guide section[{index}]")
    center_value = _guide_member(source, "center", f"torso guide section {name}", required=False)
    axial_value = _guide_member(source, "axial_position", f"torso guide section {name}", required=False)
    if axial_value is not None:
        try:
            axial_array = np.asarray(axial_value, dtype=np.float64)
        except (TypeError, ValueError, OverflowError) as exc:
            _fail(f"torso guide section {name}.axial_position is not numeric: {exc}")
        if axial_array.shape == ():
            axial = float(axial_array)
            if not math.isfinite(axial):
                _fail(f"torso guide section {name}.axial_position must be finite")
            if center_value is None:
                if axis_anchor is None:
                    axis_anchor = np.zeros(3, dtype=np.float64)
                center = axis_anchor + axial * axial_axis
            else:
                center = _vec3(center_value, f"torso guide section {name}.center")
                center = center + (axial - float(np.dot(center, axial_axis))) * axial_axis
            return center, np.asarray(axial, dtype=np.float64)
        if axial_array.shape == (3,):
            center = _vec3(axial_value, f"torso guide section {name}.axial_position")
            return center, np.asarray(float(np.dot(center, axial_axis)), dtype=np.float64)
        _fail(f"torso guide section {name}.axial_position must be a scalar or three-vector")
    if center_value is None:
        _fail(f"torso guide section {name} requires center or axial_position")
    center = _vec3(center_value, f"torso guide section {name}.center")
    return center, np.asarray(float(np.dot(center, axial_axis)), dtype=np.float64)


def _torso_section_cardinal_radii(source: Any, name: str) -> tuple[float, float, float]:
    """Read exact v7 lateral/anterior/posterior controls."""

    lateral = _guide_member(source, "lateral_radius", f"torso guide section {name}")
    anterior = _guide_member(source, "anterior_radius", f"torso guide section {name}")
    posterior = _guide_member(source, "posterior_radius", f"torso guide section {name}")
    try:
        radii = (float(lateral), float(anterior), float(posterior))
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"torso guide section {name}.cardinal-radii are not numeric: {exc}")
    _finite_positive(radii, f"torso guide section {name}.cardinal-radii")
    return radii


def _make_profile_sweep(guide: Any) -> _ProfileSweep:
    """Compile the exact seven v7 torso sections into one continuous sweep."""

    guide_sections = tuple(guide.torso_cage.sections)
    if len(guide_sections) != 7:
        _fail(f"successor torso profile sweep requires exactly seven sections, got {len(guide_sections)}")
    if guide.torso_cage.axes != guide.topology.axes:
        _fail("successor torso profile sweep axes must match guide topology")
    prototype = guide.torso_cage.axes
    preferred_first = _vec3(prototype.lateral, "torso profile lateral axis")
    preferred_second = _vec3(prototype.forward, "torso profile forward axis")
    axial_axis = _unit(_vec3(prototype.up, "torso profile axial axis"), "torso profile axial axis")
    centers: list[np.ndarray] = []
    axial_positions: list[float | None] = []
    axis_anchor: np.ndarray | None = None
    for index, source in enumerate(guide_sections):
        center, explicit_axial = _torso_section_center(source, index, axis_anchor, axial_axis)
        if axis_anchor is None:
            axis_anchor = center - float(np.dot(center, axial_axis)) * axial_axis
        centers.append(center)
        axial_positions.append(None if explicit_axial is None else float(explicit_axial))
    if any(
        axial_positions[index] is None
        or axial_positions[index + 1] is None
        or not axial_positions[index] < axial_positions[index + 1]
        for index in range(len(axial_positions) - 1)
    ):
        _fail("successor torso profile axial positions must be finite and strictly increasing")
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for index, source in enumerate(guide_sections):
        if index == 0:
            direction = centers[1] - centers[0]
        elif index == len(centers) - 1:
            direction = centers[-1] - centers[-2]
        else:
            direction = centers[index + 1] - centers[index - 1]
        name = str(_guide_member(source, "name", f"torso guide section[{index}]"))
        tangent, first, second = _frame_from_tangent(direction, preferred_first, preferred_second, f"torso profile section {name}")
        if index:
            span_length = float(np.linalg.norm(centers[index] - centers[index - 1]))
            if span_length <= _DEGENERATE_TOLERANCE:
                _fail(f"torso profile section {name} follows a degenerate span")
            path_length += span_length
        cardinal_radii = _torso_section_cardinal_radii(source, name)
        owner = _guide_member(source, "owner", f"torso guide section {name}")
        expected_owner = guide.torso_cage.pelvis_owner if index < 2 else guide.torso_cage.torso_owner
        if owner is not expected_owner:
            _fail(f"torso profile section {name} lost its canonical pelvis/torso owner")
        sections.append(_ProfileSection(
            name=name,
            owner=owner,
            center=tuple(float(value) for value in centers[index]),
            tangent=tuple(float(value) for value in tangent),
            transverse_axes=(tuple(float(value) for value in first), tuple(float(value) for value in second)),
            transverse_radii=(cardinal_radii[0], max(cardinal_radii[1], cardinal_radii[2])),
            path_length=path_length,
            torso_cardinal_radii=cardinal_radii,
            axial_position=axial_positions[index] if axial_positions[index] is not None else path_length,
        ))
    ordered = tuple(sections)
    caps = (
        _ProfileEndpointCap("start", ordered[0].center, tuple(-float(value) for value in ordered[0].tangent), ordered[0].transverse_axes, ordered[0].transverse_radii, min(ordered[0].cardinal_radii or ordered[0].transverse_radii)),
        _ProfileEndpointCap("end", ordered[-1].center, ordered[-1].tangent, ordered[-1].transverse_axes, ordered[-1].transverse_radii, min(ordered[-1].cardinal_radii or ordered[-1].transverse_radii)),
    )
    sweep = _ProfileSweep(ordered, caps, profile_operation=TORSO_PROFILE_OPERATION)
    _validate_profile_sweep(sweep)
    return sweep


# Retain the old private constructor name as a narrow source-compatible alias
# for callers of this disposable experiment.  It now returns the generic
# frame-aware representation rather than a world-Y-only loft.
def _make_loft(guide: Any) -> _ProfileSweep:
    return _make_profile_sweep(guide)


def _shoulder_torso_boundary(
    loft: _ProfileSweep,
    side: Any,
) -> tuple[np.ndarray, np.ndarray]:
    """Return a local interior station and exact loft boundary on the peak ray."""

    _validate_profile_sweep(loft)
    torso_center = _vec3(
        loft.sections[-1].center,
        f"{side.side}.shoulder.torso-ray-origin",
    )
    peak = _vec3(side.peak_anchor, f"{side.side}.shoulder.peak-ray-target")
    displacement = peak - torso_center
    target_distance = float(np.linalg.norm(displacement))
    if not math.isfinite(target_distance) or target_distance <= _DEGENERATE_TOLERANCE:
        _fail(f"{side.side} shoulder torso-boundary ray is degenerate")
    ray = displacement / target_distance
    origin_value = float(_loft_field(torso_center.reshape(1, 3), loft)[0])
    if not math.isfinite(origin_value) or origin_value >= 0.0:
        _fail(f"{side.side} shoulder torso-boundary ray does not start inside the loft")

    lower = 0.0
    upper = target_distance
    upper_value = float(_loft_field((torso_center + upper * ray).reshape(1, 3), loft)[0])
    while upper_value < 0.0 and upper < target_distance * _SHOULDER_BOUNDARY_MAX_EXTENSION:
        upper = min(upper * 1.5, target_distance * _SHOULDER_BOUNDARY_MAX_EXTENSION)
        upper_value = float(_loft_field((torso_center + upper * ray).reshape(1, 3), loft)[0])
    if not math.isfinite(upper_value) or upper_value < 0.0:
        _fail(f"{side.side} shoulder torso-boundary ray has no bounded loft exit")
    for _ in range(_SHOULDER_BOUNDARY_ITERATIONS):
        midpoint = 0.5 * (lower + upper)
        midpoint_value = float(
            _loft_field((torso_center + midpoint * ray).reshape(1, 3), loft)[0]
        )
        if not math.isfinite(midpoint_value):
            _fail(f"{side.side} shoulder torso-boundary bisection became non-finite")
        if midpoint_value < 0.0:
            lower = midpoint
        else:
            upper = midpoint
    boundary = torso_center + 0.5 * (lower + upper) * ray
    boundary_value = float(_loft_field(boundary.reshape(1, 3), loft)[0])
    if not math.isfinite(boundary_value) or abs(boundary_value) > _SHOULDER_BOUNDARY_TOLERANCE:
        _fail(f"{side.side} shoulder torso boundary did not converge")

    overlap = max(float(side.vertical_radius), 0.10)
    interior = boundary - overlap * ray
    interior_value = float(_loft_field(interior.reshape(1, 3), loft)[0])
    if not math.isfinite(interior_value) or interior_value >= 0.0:
        _fail(f"{side.side} shoulder torso-interior station is not inside the loft")
    return interior, boundary


def _make_shoulder_sweep(
    side: Any,
    torso_owner: Any,
    upper_arm: Any,
    loft: _ProfileSweep,
) -> _ShoulderEnvelopeSweep:
    """Build one disposable five-section authored shoulder envelope.

    The first two sections follow the existing torso interior/boundary and
    upper-arm root controls.  The middle section is the source-authored
    peak/axilla midpoint, with its two transverse radii retained exactly as
    the vertical and depth controls.  The final two sections overlap the
    existing upper-arm profile at its socket and first midpoint; no deltoid
    curve or analytic root bridge is consumed by this construction.
    """

    if upper_arm.root_centerline is None or upper_arm.root_thickness is None:
        _fail(f"{side.side} shoulder sweep requires an upper-arm root control")
    if len(upper_arm.sections) != 2:
        _fail(f"{side.side} shoulder sweep requires two upper-arm source sections")
    if side.authored_frame.owner != side.owner.key or side.authored_frame.role != "form_shoulder_control":
        _fail(f"{side.side} shoulder sweep lost its authored control frame")
    if side.authored_peak.owner != side.owner.key or side.authored_axilla.owner != side.owner.key:
        _fail(f"{side.side} shoulder sweep lost authored landmark ownership")
    peak = _vec3(side.peak_anchor, f"{side.side}.shoulder.peak")
    axilla = _vec3(side.axilla_anchor, f"{side.side}.shoulder.axilla")
    authored_center = 0.5 * (peak + axilla)
    vertical_radius = float(side.vertical_radius)
    depth_radius = float(side.depth_radius)
    _finite_positive((vertical_radius, depth_radius), f"{side.side}.shoulder.authored-profile")

    upper_start, upper_midpoint = upper_arm.sections[0].centerline
    torso_interior, torso_boundary = _shoulder_torso_boundary(loft, side)
    root_thickness = tuple(float(value) for value in upper_arm.root_thickness)
    centers = (
        tuple(float(value) for value in torso_interior),
        tuple(float(value) for value in torso_boundary),
        tuple(float(value) for value in authored_center),
        tuple(float(value) for value in side.socket_anchor),
        tuple(float(value) for value in upper_midpoint),
    )
    if tuple(float(value) for value in upper_start) != centers[3]:
        _fail(f"{side.side} shoulder sweep socket does not overlap upper-arm start")
    if not np.all(np.isfinite(np.asarray(centers, dtype=np.float64))):
        _fail(f"{side.side} shoulder sweep contains non-finite centers")

    root_radius = float(root_thickness[0])
    socket_radius = float(upper_arm.sections[0].thickness[0])
    midpoint_radius = float(upper_arm.sections[0].thickness[1])
    radii = (
        (root_radius * 1.08, root_radius * 1.08),
        (root_radius, root_radius),
        (vertical_radius, depth_radius),
        (socket_radius, socket_radius),
        (midpoint_radius, midpoint_radius),
    )
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for index, (name, owner, center, profile) in enumerate(zip(
        ("torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"),
        (torso_owner, torso_owner, side.owner, side.owner, side.owner),
        centers,
        radii,
    )):
        current = _vec3(center, f"{side.side}.shoulder.{name}.center")
        if index:
            span_length = float(np.linalg.norm(current - _vec3(centers[index - 1], "shoulder previous center")))
            if span_length <= _DEGENERATE_TOLERANCE:
                _fail(f"{side.side} shoulder sweep section {name!r} follows a degenerate span")
            path_length += span_length
        _finite_positive(tuple(float(value) for value in profile), f"{side.side}.shoulder.{name}.radii")
        direction = (
            _vec3(centers[1], "shoulder next center") - current
            if index == 0
            else _vec3(centers[-1], "shoulder previous endpoint") - _vec3(centers[-2], "shoulder endpoint predecessor")
            if index == len(centers) - 1
            else _vec3(centers[index + 1], "shoulder following center") - _vec3(centers[index - 1], "shoulder preceding center")
        )
        tangent, first, second = _frame_from_tangent(
            direction,
            _vec3(side.axes.up, f"{side.side}.shoulder.up-axis"),
            _vec3(side.axes.forward, f"{side.side}.shoulder.forward-axis"),
            f"{side.side}.shoulder.{name}",
        )
        sections.append(_ProfileSection(
            name=name,
            owner=owner,
            center=tuple(float(value) for value in current),
            tangent=tuple(float(value) for value in tangent),
            transverse_axes=(tuple(float(value) for value in first), tuple(float(value) for value in second)),
            transverse_radii=tuple(float(value) for value in profile),
            path_length=path_length,
        ))
    sweep = _ProfileSweep(tuple(sections), (
        _ProfileEndpointCap("start", sections[0].center, tuple(-float(value) for value in sections[0].tangent), sections[0].transverse_axes, sections[0].transverse_radii, min(sections[0].transverse_radii)),
        _ProfileEndpointCap("end", sections[-1].center, sections[-1].tangent, sections[-1].transverse_axes, sections[-1].transverse_radii, min(sections[-1].transverse_radii)),
    ))
    _validate_profile_sweep(sweep)
    return _ShoulderEnvelopeSweep(
        side=side.side,
        owner=side.owner,
        sweep=sweep,
        preferred_up=tuple(float(value) for value in side.axes.up),
        preferred_forward=tuple(float(value) for value in side.axes.forward),
    )


def _make_shoulder_sweeps(
    guide: Any,
    loft: _ProfileSweep,
) -> tuple[_ShoulderEnvelopeSweep, ...]:
    """Build exactly one source-owned shoulder envelope per bilateral side."""

    upper_arms = {
        item.owner.key[1][0]: item
        for item in guide.limb_guides
        if item.owner.key[3] == "upper_arm" and len(item.owner.key[1]) == 1
    }
    if set(upper_arms) != {"left", "right"}:
        _fail("successor shoulder sweep inventory must contain exactly two upper arms")
    result = tuple(
        _make_shoulder_sweep(
            side,
            guide.shoulder_frame.torso_owner,
            upper_arms[side.side],
            loft,
        )
        for side in guide.shoulder_frame.sides
    )
    if tuple(item.recipe for item in result) != ("left-shoulder-envelope", "right-shoulder-envelope"):
        _fail("successor shoulder sweep order is unstable")
    return result


# Tail masses use a compact symmetric station layout.  The centre station is
# intentionally unscaled so the exact guide centre and the first two guide
# radii remain directly observable.  The third guide radius bounds the axial
# extent; it is not folded into either transverse profile radius.
_TAIL_MASS_PROFILE = (
    (-0.50, 0.82, 0.82),
    (0.00, 1.00, 1.00),
    (0.50, 0.82, 0.82),
)

_TAIL_ELEMENT_ORDER = (
    "tail-root-source",
    "tail-root-attachment",
    "tail-root-collar",
    "tail-tip-source",
    "tail-tip-extension",
    "tail-tip-cap",
)

_TAIL_ELEMENT_KINDS = (
    "source-centerline",
    "root-attachment",
    "root-collar-mass",
    "source-centerline",
    "tip-extension",
    "tip-cap-mass",
)

_SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE = 1.0e-10
_SUCCESSOR_TAIL_ATTACHMENT_BISECTION_ITERATIONS = 64

# These controls are shared by every hand and foot in every fixed fixture.
# Hand offsets are measured in the outward lateral-radius units of the exact
# guide paw.  The hand profile's two transverse axes are explicitly up and
# forward; feet use the generic lateral/forward frame derivation below.
_HAND_PAW_PROFILE = (
    (-0.55, 0.62, 0.66),
    (-0.15, 1.00, 1.00),
    (0.35, 0.92, 1.05),
    (0.78, 0.55, 0.60),
)
_HAND_PAW_SECTION_NAMES = ("hand-paw-base", "hand-paw-palm", "hand-paw-knuckle", "hand-paw-tip")


def _make_transition_sweep(
    recipe: str,
    owner: Any,
    path: tuple[tuple[float, float, float], tuple[float, float, float]],
    thickness: tuple[float, float],
    axes: Any,
) -> _ProfileSweep:
    """Compile one guide path with exact endpoint and thickness ownership."""

    if len(path) != 2 or len(thickness) != 2:
        _fail(f"successor {recipe} requires two path endpoints and two thicknesses")
    start = _vec3(path[0], f"{recipe}.start")
    end = _vec3(path[1], f"{recipe}.end")
    direction = end - start
    length = float(np.linalg.norm(direction))
    if not math.isfinite(length) or length <= _DEGENERATE_TOLERANCE:
        _fail(f"successor {recipe} path is degenerate")
    _finite_positive(tuple(float(value) for value in thickness), f"{recipe}.thickness")
    tangent, first, second = _frame_from_tangent(
        direction,
        _vec3(axes.lateral, f"{recipe}.lateral-axis"),
        _vec3(axes.forward, f"{recipe}.forward-axis"),
        recipe,
    )
    first_radii = (float(thickness[0]), float(thickness[0]))
    second_radii = (float(thickness[1]), float(thickness[1]))
    sections = (
        _ProfileSection(
            f"{recipe}-start", owner, tuple(float(value) for value in start),
            tuple(float(value) for value in tangent),
            (tuple(float(value) for value in first), tuple(float(value) for value in second)),
            first_radii, 0.0,
        ),
        _ProfileSection(
            f"{recipe}-end", owner, tuple(float(value) for value in end),
            tuple(float(value) for value in tangent),
            (tuple(float(value) for value in first), tuple(float(value) for value in second)),
            second_radii, length,
        ),
    )
    caps = (
        _ProfileEndpointCap(
            "start", sections[0].center, tuple(-float(value) for value in tangent),
            sections[0].transverse_axes, sections[0].transverse_radii,
            min(sections[0].transverse_radii),
        ),
        _ProfileEndpointCap(
            "end", sections[-1].center, sections[-1].tangent,
            sections[-1].transverse_axes, sections[-1].transverse_radii,
            min(sections[-1].transverse_radii),
        ),
    )
    sweep = _ProfileSweep(sections, caps)
    _validate_profile_sweep(sweep)
    return sweep


def _make_mass_profile_sweep(
    recipe: str,
    owner: Any,
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
    tangent_axis: tuple[float, float, float],
    axial_radius: float,
    transverse_radii: tuple[float, float],
    transverse_axis_preferences: tuple[tuple[float, float, float], tuple[float, float, float]],
    controls: tuple[tuple[float, float, float], ...],
) -> _ProfileSweep:
    """Compile a compact mass with explicit guide-derived axial/transverse mapping."""

    centre = _vec3(center, f"{recipe}.center")
    base_radii = _vec3(radii, f"{recipe}.radii")
    _finite_positive(tuple(float(value) for value in base_radii), f"{recipe}.radii")
    transverse = tuple(float(value) for value in transverse_radii)
    if len(transverse) != 2:
        _fail(f"{recipe}.transverse-radii must contain two values")
    _finite_positive(transverse, f"{recipe}.transverse-radii")
    if len(transverse_axis_preferences) != 2:
        _fail(f"{recipe}.transverse-axis-preferences must contain two axes")
    axial = float(axial_radius)
    if not math.isfinite(axial) or axial <= 0.0:
        _fail(f"{recipe}.axial-radius must be finite and positive")
    if len(controls) < 2:
        _fail(f"{recipe} requires at least two ordered profile sections")
    tangent, first, second = _frame_from_tangent(
        _vec3(tangent_axis, f"{recipe}.tangent-axis"),
        _vec3(transverse_axis_preferences[0], f"{recipe}.transverse-first-axis"),
        _vec3(transverse_axis_preferences[1], f"{recipe}.transverse-second-axis"),
        recipe,
    )
    sections: list[_ProfileSection] = []
    path_length = 0.0
    previous_offset: float | None = None
    for index, control in enumerate(controls):
        if len(control) != 3:
            _fail(f"{recipe} profile section {index} must have offset and two scales")
        offset, first_scale, second_scale = (float(value) for value in control)
        if (
            not all(math.isfinite(value) for value in (offset, first_scale, second_scale))
            or abs(offset) >= 0.90
            or first_scale <= 0.0
            or second_scale <= 0.0
        ):
            _fail(f"{recipe} profile section {index} has invalid shared controls")
        if previous_offset is not None and offset <= previous_offset:
            _fail(f"{recipe} profile offsets must be strictly increasing")
        previous_offset = offset
        if index:
            path_length += (offset - float(controls[index - 1][0])) * axial
        section_center = centre + offset * axial * tangent
        section_radii = (float(transverse[0] * first_scale), float(transverse[1] * second_scale))
        _finite_positive(section_radii, f"{recipe} profile section {index}.radii")
        sections.append(_ProfileSection(
            f"{recipe}-section-{index}", owner,
            tuple(float(value) for value in section_center),
            tuple(float(value) for value in tangent),
            (tuple(float(value) for value in first), tuple(float(value) for value in second)),
            section_radii, path_length,
        ))
    ordered = tuple(sections)
    endpoint_caps: list[_ProfileEndpointCap] = []
    for index, section in ((0, ordered[0]), (-1, ordered[-1])):
        offset = float(controls[0 if index == 0 else -1][0])
        remaining_axial = axial * (1.0 - abs(offset))
        # Keep the rounded profile within the guide's declared axial extent.
        cap_axial = min(min(section.transverse_radii), 0.85 * remaining_axial)
        _finite_positive((cap_axial,), f"{recipe} endpoint cap axial radius")
        endpoint_caps.append(_ProfileEndpointCap(
            "start" if index == 0 else "end", section.center,
            tuple(-float(value) for value in tangent) if index == 0 else section.tangent,
            section.transverse_axes, section.transverse_radii, cap_axial,
        ))
    sweep = _ProfileSweep(ordered, tuple(endpoint_caps))
    _validate_profile_sweep(sweep)
    return sweep


def _make_tail_mass_profile_sweep(
    recipe: str,
    owner: Any,
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
    tangent_axis: tuple[float, float, float],
    axes: Any,
) -> _ProfileSweep:
    """Compile one bounded tail mass from exact guide centre/radii controls.

    This is the same generic ``_ProfileSweep`` representation used by the
    other successor regions, with a fixed three-station symmetric layout. The
    first two guide radii author the transverse profiles; the third radius is
    the complete axial half-extent (half-station spacing plus half-cap).
    """

    centre = _vec3(center, f"{recipe}.center")
    base_radii = _vec3(radii, f"{recipe}.radii")
    _finite_positive(tuple(float(value) for value in base_radii), f"{recipe}.radii")
    axial_radius = float(base_radii[2])
    tangent, first, second = _frame_from_tangent(
        _vec3(tangent_axis, f"{recipe}.tangent-axis"),
        _vec3(axes.lateral, f"{recipe}.lateral-axis"),
        _vec3(axes.up, f"{recipe}.up-axis"),
        recipe,
    )
    sections: list[_ProfileSection] = []
    path_length = 0.0
    previous_offset: float | None = None
    for index, control in enumerate(_TAIL_MASS_PROFILE):
        offset, first_scale, second_scale = (float(value) for value in control)
        if previous_offset is not None and offset <= previous_offset:
            _fail(f"{recipe} profile offsets must be strictly increasing")
        previous_offset = offset
        if index:
            path_length += (offset - float(_TAIL_MASS_PROFILE[index - 1][0])) * axial_radius
        section_center = centre + offset * axial_radius * tangent
        section_radii = (
            float(base_radii[0]) * first_scale,
            float(base_radii[1]) * second_scale,
        )
        _finite_positive(section_radii, f"{recipe}.section[{index}].radii")
        sections.append(_ProfileSection(
            f"{recipe}-section-{index}", owner,
            tuple(float(value) for value in section_center),
            tuple(float(value) for value in tangent),
            (tuple(float(value) for value in first), tuple(float(value) for value in second)),
            section_radii, path_length,
        ))
    ordered = tuple(sections)
    # Stations occupy +/- half the exact third guide radius. The endpoint cap
    # supplies the other half, so the mass cannot exceed the guide-derived
    # axial extent in the tangent direction.
    cap_axial = 0.5 * axial_radius
    endpoint_caps = (
        _ProfileEndpointCap(
            "start", ordered[0].center, tuple(-float(value) for value in tangent),
            ordered[0].transverse_axes, ordered[0].transverse_radii, cap_axial,
        ),
        _ProfileEndpointCap(
            "end", ordered[-1].center, ordered[-1].tangent,
            ordered[-1].transverse_axes, ordered[-1].transverse_radii, cap_axial,
        ),
    )
    sweep = _ProfileSweep(ordered, endpoint_caps)
    _validate_profile_sweep(sweep)
    return sweep


def _tail_axis(tail: Any, where: str) -> tuple[float, float, float]:
    """Return the exact ordered source-tail axis used by path and mass sweeps."""

    start = _vec3(tail.centerline[0], f"{where}.centerline.start")
    end = _vec3(tail.centerline[1], f"{where}.centerline.end")
    axis = end - start
    return tuple(float(value) for value in _unit(axis, f"{where}.axis"))


def _guide_reference_scale_for_connection(guide: Any) -> float:
    """Recover the validated guide normalization for an exact source anchor."""

    candidates: list[float] = []
    for descriptor in guide.source_descriptors:
        for exact, normalized in zip(descriptor.exact_point, descriptor.point):
            if exact != 0 and math.isfinite(float(normalized)) and abs(float(normalized)) > _DEGENERATE_TOLERANCE:
                candidates.append(float(exact) / float(normalized))
    if not candidates or any(not math.isfinite(value) or value <= 0.0 for value in candidates):
        _fail("successor tail cannot recover the validated guide reference scale")
    scale = candidates[0]
    if any(not math.isclose(value, scale, rel_tol=0.0, abs_tol=1.0e-9) for value in candidates[1:]):
        _fail("successor tail guide reference scale is inconsistent")
    return scale


def _derive_successor_tail_attachment_start(guide: Any, loft: _ProfileSweep) -> np.ndarray:
    """Find the successor-loft boundary on the guide attachment ray.

    The guide attachment start is a baseline-parent boundary point.  It is
    retained as the ray target and validated by the baseline inventory, but it
    is not necessarily a boundary point of the successor loft.  This helper
    re-anchors the successor sweep from the known interior lower-pelvis
    section centre by a fixed, bounded bisection.
    """

    _validate_profile_sweep(loft)
    tails = tuple(guide.tail_guides)
    if len(tails) != 2 or tails[0].root_attachment_centerline is None:
        _fail("successor tail attachment ray requires the canonical root guide")
    root = tails[0]
    interior = _vec3(loft.sections[0].center, "successor tail attachment interior centre")
    guide_start = _vec3(root.root_attachment_centerline[0], "successor tail guide attachment start")
    ray_vector = guide_start - interior
    ray_length = float(np.linalg.norm(ray_vector))
    if not math.isfinite(ray_length) or ray_length <= _DEGENERATE_TOLERANCE:
        _fail("successor tail attachment ray is degenerate")
    ray = ray_vector / ray_length

    lower = 0.0
    lower_value = float(_loft_field(interior.reshape(1, 3), loft)[0])
    if not math.isfinite(lower_value) or lower_value >= 0.0:
        _fail("successor tail attachment ray does not start inside the loft")
    upper = ray_length
    upper_point = interior + upper * ray
    upper_value = float(_loft_field(upper_point.reshape(1, 3), loft)[0])
    if not math.isfinite(upper_value):
        _fail("successor tail attachment ray boundary query is non-finite")
    if upper_value < 0.0:
        _fail("successor tail attachment ray has no bounded loft boundary bracket")
    if upper_value == 0.0:
        boundary = upper_point
    else:
        for _ in range(_SUCCESSOR_TAIL_ATTACHMENT_BISECTION_ITERATIONS):
            midpoint = 0.5 * (lower + upper)
            midpoint_value = float(_loft_field((interior + midpoint * ray).reshape(1, 3), loft)[0])
            if not math.isfinite(midpoint_value):
                _fail("successor tail attachment bisection became non-finite")
            if midpoint_value < 0.0:
                lower = midpoint
            else:
                upper = midpoint
        boundary = interior + 0.5 * (lower + upper) * ray
    boundary_value = float(_loft_field(boundary.reshape(1, 3), loft)[0])
    if not math.isfinite(boundary_value) or abs(boundary_value) > _SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE:
        _fail("successor tail attachment boundary did not converge")
    if float(np.dot(boundary - interior, ray)) <= 0.0:
        _fail("successor tail attachment boundary has invalid ray orientation")
    if float(np.linalg.norm(np.cross(boundary - interior, ray))) > _SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE:
        _fail("successor tail attachment boundary left its source ray")
    return boundary


def _make_tail_elements(guide: Any, loft: _ProfileSweep | None = None) -> tuple[_TailElement, ...]:
    """Build the fixed six-element, source-owned successor tail topology."""

    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    tails = tuple(guide.tail_guides)
    if tuple(item.owner.key[3] for item in tails) != ("tail_root", "tail_tip"):
        _fail("successor tail guide order must be tail_root then tail_tip")
    if len(tails) != 2:
        _fail("successor tail guide inventory must contain exactly root and tip")
    if any(source_by_key.get(item.owner.key) is not item.owner for item in tails):
        _fail("successor tail owner must be the canonical source descriptor")
    if any(item.axes != guide.topology.axes or item.axes != _baseline._FIXED_GUIDE_AXES for item in tails):
        _fail("successor tail axes must match the fixed guide axes")
    tail_root, tail_tip = tails
    expected_root_parent = guide.torso_cage.pelvis_owner
    if source_by_key.get(expected_root_parent.key) is not expected_root_parent:
        _fail("successor tail root parent pelvis owner is not canonical")
    if tail_root.owner.parent != expected_root_parent.key or source_by_key.get(tail_root.owner.parent) is not expected_root_parent:
        _fail("successor tail root parent must be the canonical pelvis owner")
    if tail_tip.owner.parent != tail_root.owner.key or source_by_key.get(tail_tip.owner.parent) is not tail_root.owner:
        _fail("successor tail tip parent must be tail_root")
    if tail_root.root_attachment_centerline is None or tail_root.root_attachment_taper is None:
        _fail("successor tail root attachment controls are incomplete")
    if tail_root.root_collar_center is None or tail_root.root_collar_radii is None:
        _fail("successor tail root collar controls are incomplete")
    if tail_tip.extension_centerline is None or tail_tip.extension_taper is None:
        _fail("successor tail tip extension controls are incomplete")
    if tail_tip.cap_center is None or tail_tip.cap_radii is None:
        _fail("successor tail tip cap controls are incomplete")
    parent = source_by_key.get(tail_root.owner.parent)
    if parent is None:
        _fail("successor tail root parent is not present in the source inventory")
    reference_scale = _guide_reference_scale_for_connection(guide)
    expected_anchor = _baseline._parent_surface_anchor(
        parent,
        _vec3(tail_root.centerline[1], "tail-root source endpoint"),
        reference_scale,
    )
    _require_exact_same_point(
        tail_root.root_attachment_centerline[0], expected_anchor,
        "tail-root attachment/source parent surface anchor",
    )
    anchor_field = _baseline._field(expected_anchor.reshape(1, 3), parent, reference_scale)
    if not np.all(np.isfinite(anchor_field)) or float(abs(anchor_field[0])) > _FRAME_TOLERANCE:
        _fail("tail-root attachment start is not on its exact source parent boundary")

    if loft is None:
        loft = _make_loft(guide)
    successor_attachment_start = _derive_successor_tail_attachment_start(guide, loft)
    root_attachment_path = (
        tuple(float(value) for value in successor_attachment_start),
        tuple(float(value) for value in tail_root.root_attachment_centerline[1]),
    )

    root_axis = _tail_axis(tail_root, "tail-root")
    tip_axis = _tail_axis(tail_tip, "tail-tip")
    root_source = _TailElement(
        "tail-root-source", tail_root.owner,
        _make_transition_sweep("tail-root-source", tail_root.owner, tail_root.centerline, tail_root.taper, tail_root.axes),
        "source-centerline",
    )
    root_attachment = _TailElement(
        "tail-root-attachment", tail_root.owner,
        _make_transition_sweep("tail-root-attachment", tail_root.owner, root_attachment_path, tail_root.root_attachment_taper, tail_root.axes),  # type: ignore[arg-type]
        "root-attachment",
    )
    root_collar = _TailElement(
        "tail-root-collar", tail_root.owner,
        _make_tail_mass_profile_sweep(
            "tail-root-collar", tail_root.owner, tail_root.root_collar_center,
            tail_root.root_collar_radii, root_axis, tail_root.axes,  # type: ignore[arg-type]
        ),
        "root-collar-mass",
    )
    tip_source = _TailElement(
        "tail-tip-source", tail_tip.owner,
        _make_transition_sweep("tail-tip-source", tail_tip.owner, tail_tip.centerline, tail_tip.taper, tail_tip.axes),
        "source-centerline",
    )
    tip_extension = _TailElement(
        "tail-tip-extension", tail_tip.owner,
        _make_transition_sweep("tail-tip-extension", tail_tip.owner, tail_tip.extension_centerline, tail_tip.extension_taper, tail_tip.axes),  # type: ignore[arg-type]
        "tip-extension",
    )
    tip_cap = _TailElement(
        "tail-tip-cap", tail_tip.owner,
        _make_tail_mass_profile_sweep(
            "tail-tip-cap", tail_tip.owner, tail_tip.cap_center,
            tail_tip.cap_radii, tip_axis, tail_tip.axes,  # type: ignore[arg-type]
        ),
        "tip-cap-mass",
    )
    result = (root_source, root_attachment, root_collar, tip_source, tip_extension, tip_cap)
    _validate_tail_elements(guide, result, loft)
    return result


def _validate_tail_elements(guide: Any, elements: tuple[_TailElement, ...], loft: _ProfileSweep | None = None) -> None:
    """Fail closed on tail ownership, topology, exact controls, and joins."""

    if tuple(item.name for item in elements) != _TAIL_ELEMENT_ORDER:
        _fail("successor tail element order is unstable")
    if tuple(item.kind for item in elements) != _TAIL_ELEMENT_KINDS:
        _fail("successor tail element kinds are unstable")
    tails = tuple(guide.tail_guides)
    if len(tails) != 2 or tuple(item.owner.key[3] for item in tails) != ("tail_root", "tail_tip"):
        _fail("successor tail guide inventory is not the exact root/tip pair")
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    root, tip = tails
    expected_root_parent = guide.torso_cage.pelvis_owner
    if source_by_key.get(expected_root_parent.key) is not expected_root_parent:
        _fail("successor tail root parent pelvis owner is not canonical")
    if root.owner.parent != expected_root_parent.key or source_by_key.get(root.owner.parent) is not expected_root_parent:
        _fail("successor tail root parent must be the canonical pelvis owner")
    if tip.owner.parent != root.owner.key or source_by_key.get(tip.owner.parent) is not root.owner:
        _fail("successor tail tip parent relationship is not canonical")
    if any(item.owner not in (root.owner, tip.owner) for item in elements):
        _fail("successor tail element has an unexpected owner")
    if any(source_by_key.get(item.owner.key) is not item.owner for item in elements):
        _fail("successor tail element owner identity is not canonical")
    if any(any(section.owner is not item.owner for section in item.sweep.sections) for item in elements):
        _fail("successor tail sweep sections must retain one canonical owner")
    if any(item.sweep.internal_transitions for item in elements):
        _fail("successor tail topology must not invent internal bend transitions")
    if any(len(item.sweep.endpoint_caps) != 2 for item in elements):
        _fail("successor tail elements must have exactly two outer caps")

    root_source, root_attachment, root_collar, tip_source, tip_extension, tip_cap = elements
    if loft is None:
        loft = _make_loft(guide)
    expected_successor_start = _derive_successor_tail_attachment_start(guide, loft)
    actual_successor_start = _vec3(root_attachment.sweep.sections[0].center, "tail-root successor attachment start")
    if not np.allclose(actual_successor_start, expected_successor_start, rtol=0.0, atol=_SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE):
        _fail("tail-root successor attachment start is not the derived loft boundary")
    successor_start_value = float(_loft_field(actual_successor_start.reshape(1, 3), loft)[0])
    if not math.isfinite(successor_start_value) or abs(successor_start_value) > _SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE:
        _fail("tail-root successor attachment start is not on the successor loft boundary")
    interior = _vec3(loft.sections[0].center, "tail-root successor attachment interior centre")
    guide_start = _vec3(root.root_attachment_centerline[0], "tail-root guide attachment start")
    ray = guide_start - interior
    ray_length = float(np.linalg.norm(ray))
    if not math.isfinite(ray_length) or ray_length <= _DEGENERATE_TOLERANCE:
        _fail("tail-root successor attachment ray is degenerate")
    ray /= ray_length
    displacement = actual_successor_start - interior
    if float(np.dot(displacement, ray)) <= 0.0 or float(np.linalg.norm(np.cross(displacement, ray))) > _SUCCESSOR_TAIL_ATTACHMENT_BOUNDARY_TOLERANCE:
        _fail("tail-root successor attachment start has invalid ray orientation")
    expected_root_attachment_path = (
        tuple(float(value) for value in expected_successor_start),
        tuple(float(value) for value in root.root_attachment_centerline[1]),  # type: ignore[index]
    )
    for element, path, profile, where in (
        (root_source, root.centerline, root.taper, "tail-root source"),
        (root_attachment, expected_root_attachment_path, root.root_attachment_taper, "tail-root attachment"),
        (tip_source, tip.centerline, tip.taper, "tail-tip source"),
        (tip_extension, tip.extension_centerline, tip.extension_taper, "tail-tip extension"),
    ):
        if path is None or profile is None:
            _fail(f"{where} guide controls are incomplete")
        sections = element.sweep.sections
        if len(sections) != 2:
            _fail(f"{where} must have exactly two profile stations")
        for section, expected_center, expected_radius in zip(sections, path, profile):
            if not np.array_equal(_vec3(section.center, f"{where}.center"), _vec3(expected_center, f"{where}.guide-center")):
                _fail(f"{where} does not retain exact guide path controls")
            if section.transverse_radii != (float(expected_radius), float(expected_radius)):
                _fail(f"{where} does not retain exact guide taper controls")
            if section.owner is not element.owner:
                _fail(f"{where} section owner is not canonical")

    _require_exact_same_point(
        root_attachment.sweep.sections[-1].center,
        root_source.sweep.sections[-1].center,
        "tail-root attachment/source endpoint",
    )
    _require_exact_same_point(
        root_collar.sweep.sections[len(root_collar.sweep.sections) // 2].center,
        root_source.sweep.sections[-1].center,
        "tail-root collar/source endpoint",
    )
    _require_exact_same_point(
        root_source.sweep.sections[-1].center,
        tip_source.sweep.sections[0].center,
        "tail-root/tip source join",
    )
    _require_exact_same_point(
        tip_source.sweep.sections[-1].center,
        tip_extension.sweep.sections[0].center,
        "tail-tip source/extension shared endpoint",
    )
    _require_exact_same_point(
        tip_extension.sweep.sections[-1].center,
        tip_cap.sweep.sections[len(tip_cap.sweep.sections) // 2].center,
        "tail-tip extension/cap endpoint",
    )
    # Preserve both independently authored endpoint profiles. Do not average
    # or infer a replacement radius at their shared endpoint; the current
    # guide happens to author equal values, but each control remains exact.
    core_profile = tip_source.sweep.sections[-1].transverse_radii
    extension_profile = tip_extension.sweep.sections[0].transverse_radii
    if core_profile != (float(tip.taper[-1]), float(tip.taper[-1])):
        _fail("tail-tip source endpoint lost its exact guide taper")
    if extension_profile != (float(tip.extension_taper[0]), float(tip.extension_taper[0])):  # type: ignore[index]
        _fail("tail-tip extension lost its exact guide start taper")

    for element, centre, radii, axis, where in (
        (root_collar, root.root_collar_center, root.root_collar_radii, _tail_axis(root, "tail-root"), "tail-root collar"),
        (tip_cap, tip.cap_center, tip.cap_radii, _tail_axis(tip, "tail-tip"), "tail-tip cap"),
    ):
        if centre is None or radii is None:
            _fail(f"{where} guide controls are incomplete")
        sections = element.sweep.sections
        if len(sections) != len(_TAIL_MASS_PROFILE) or tuple(float(value) for value in sections[len(sections) // 2].center) != tuple(float(value) for value in centre):
            _fail(f"{where} must retain its exact guide centre at the centre station")
        if sections[len(sections) // 2].transverse_radii != (float(radii[0]), float(radii[1])):  # type: ignore[index]
            _fail(f"{where} must retain its exact guide transverse radii")
        expected_tangent = _vec3(axis, f"{where}.axis")
        _, expected_first, expected_second = _frame_from_tangent(
            expected_tangent,
            _vec3(guide.topology.axes.lateral, f"{where}.lateral-axis"),
            _vec3(guide.topology.axes.up, f"{where}.up-axis"),
            where,
        )
        for section in sections:
            if section.tangent != tuple(float(value) for value in expected_tangent):
                _fail(f"{where} must use the fixed guide tail axis")
            if section.transverse_axes != (tuple(float(value) for value in expected_first), tuple(float(value) for value in expected_second)):
                _fail(f"{where} must use the fixed guide transverse axes")
        centre_vector = _vec3(centre, f"{where}.centre")
        axial = float(radii[2])  # type: ignore[index]
        # The oriented extent along the tail axis is bounded by the exact
        # third guide radius. Transverse extents are intentionally independent.
        for section in sections:
            axial_distance = abs(float(np.dot(_vec3(section.center, f"{where}.section-center") - centre_vector, expected_tangent)))
            if axial_distance > axial + _FRAME_TOLERANCE:
                _fail(f"{where} axial bounds exceed its guide third radius")
        for cap in element.sweep.endpoint_caps:
            axial_distance = abs(float(np.dot(_vec3(cap.center, f"{where}.cap-center") - centre_vector, expected_tangent))) + float(cap.axial_radius)
            if axial_distance > axial + _FRAME_TOLERANCE:
                _fail(f"{where} cap exceeds its guide third radius")


def _tail_element_metadata(elements: tuple[_TailElement, ...]) -> list[dict[str, Any]]:
    """Serialize every consumed tail station/cap control for the sidecar."""

    return [
        {
            "name": item.name,
            "kind": item.kind,
            "owner": _baseline._address_json(item.owner.key),
            "sections": [
                {
                    "name": section.name,
                    "center": [float(value) for value in section.center],
                    "tangent": [float(value) for value in section.tangent],
                    "transverse_axes": [[float(value) for value in axis] for axis in section.transverse_axes],
                    "transverse_radii": [float(value) for value in section.transverse_radii],
                    "path_length": float(section.path_length),
                }
                for section in item.sweep.sections
            ],
            "endpoint_caps": [
                {
                    "side": cap.side,
                    "center": [float(value) for value in cap.center],
                    "outward_tangent": [float(value) for value in cap.outward_tangent],
                    "transverse_axes": [[float(value) for value in axis] for axis in cap.transverse_axes],
                    "transverse_radii": [float(value) for value in cap.transverse_radii],
                    "axial_radius": float(cap.axial_radius),
                }
                for cap in item.sweep.endpoint_caps
            ],
        }
        for item in elements
    ]


def _validate_authored_head_neck_guide(guide: Any) -> Any:
    """Validate the exact producer/guide head/neck envelope before compiling."""

    try:
        head = guide.head_guide
        profile = head.profile
        axes = profile.axes
        topology_axes = guide.topology.axes
        sections = tuple(profile.sections)
        connections = tuple(profile.connections)
        source_descriptors = tuple(guide.source_descriptors)
    except (AttributeError, TypeError, ValueError) as exc:
        _fail(f"successor authored head/neck guide is incomplete: {exc}")
    if axes != topology_axes or axes != _baseline._FIXED_GUIDE_AXES:
        _fail("successor authored head/neck axes must match the fixed guide topology")
    if len(sections) != 8 or len(connections) != 7:
        _fail("successor authored head/neck guide must contain exactly eight sections and seven connections")
    provenance = getattr(profile, "provenance", None)
    if not isinstance(provenance, dict) or set(provenance) != {"source", "document", "namespace"}:
        _fail("successor authored head/neck guide provenance is incomplete")
    source_by_key = {descriptor.key: descriptor for descriptor in source_descriptors}
    expected_connections = tuple(_baseline.HeadNeckConnection(*item) for item in _baseline.HEAD_NECK_PROFILE_CONNECTIONS)
    expected_route_indices = {name: indices for name, indices, _, _ in _HEAD_NECK_ROUTE_TOPOLOGY}
    for index, section in enumerate(sections):
        where = f"successor head/neck section[{index}]"
        try:
            name = section.name
            owner = section.owner
            frame = section.frame
            landmark = section.landmark
            controls = (section.lateral_lineage, section.up_lineage, section.forward_lineage)
            radii = tuple(float(value) for value in section.radii)
        except (AttributeError, TypeError, ValueError) as exc:
            _fail(f"{where} is malformed: {exc}")
        if name != _baseline.HEAD_NECK_PROFILE_SECTION_NAMES[index]:
            _fail(f"{where} has unstable authored section name/order")
        if section.section_index != index or section.source_section_index != index:
            _fail(f"{where} lost exact producer source section indices")
        if owner.key not in source_by_key or source_by_key[owner.key] is not owner:
            _fail(f"{where} lost canonical source ownership")
        if owner.key[1] != () or owner.key[3] != _baseline.HEAD_NECK_PROFILE_OWNER_ROLES[index]:
            _fail(f"{where} has an invalid source owner role")
        if frame.owner != owner.key or frame.role != _baseline.HEAD_NECK_PROFILE_FRAME_ROLE:
            _fail(f"{where} lost exact source frame ownership")
        if section.frame_index != _HEAD_NECK_FRAME_INDICES[owner.key[3]] or section.landmark_index != _HEAD_NECK_LANDMARK_INDICES[index]:
            _fail(f"{where} lost exact source frame/landmark indices")
        if landmark.owner != owner.key or landmark.frame != (frame.owner, frame.role):
            _fail(f"{where} lost exact source landmark/frame binding")
        if frame.translation != (0.0, 0.0, 0.0) or frame.rotation_xyzw != (0.0, 0.0, 0.0, 1.0):
            _fail(f"{where} source frame is not the fixed identity frame")
        if len(radii) != 3:
            _fail(f"{where} must retain all three authored radii")
        _finite_positive(radii, f"{where}.radii")
        expected_roles = tuple(
            _baseline.HEAD_NECK_PROFILE_DIMENSION_PREFIX + name.replace("-", "_") + "_" + suffix
            for suffix in _baseline.HEAD_NECK_PROFILE_DIMENSION_SUFFIXES
        )
        for axis, control, expected_role, expected_index in zip(
            ("lateral", "up", "forward"), controls, expected_roles, _HEAD_NECK_RADIUS_REFERENCE_INDICES[index]
        ):
            if control.consumed_section != name or control.reference != (owner.key, expected_role):
                _fail(f"{where}.{axis} lineage lost source role or section")
            if control.reference_index != expected_index:
                _fail(f"{where}.{axis} lineage lost source index")
            if control.provenance != provenance:
                _fail(f"{where}.{axis} lineage provenance does not match the producer profile")
            if control.base <= 0 or control.factor <= 0 or control.scaled <= 0:
                _fail(f"{where}.{axis} lineage contains a non-positive authored value")
        _vec3(section.center, f"{where}.center")
    for index, connection in enumerate(connections):
        where = f"successor head/neck connection[{index}]"
        try:
            spec = connection.spec
            actual = (spec.name, spec.from_section_index, spec.to_section_index, spec.route)
        except (AttributeError, TypeError, ValueError) as exc:
            _fail(f"{where} is malformed: {exc}")
        expected = _baseline.HEAD_NECK_PROFILE_CONNECTIONS[index]
        if actual != expected or spec != expected_connections[index]:
            _fail(f"{where} lost exact authored name/route/index topology")
        if not 0 <= spec.from_section_index < len(sections) or not 0 <= spec.to_section_index < len(sections):
            _fail(f"{where} has an out-of-range station index")
        from_section = sections[spec.from_section_index]
        to_section = sections[spec.to_section_index]
        if connection.from_section is not from_section or connection.to_section is not to_section:
            _fail(f"{where} lost exact station identity references")
        expected_thickness = (min(from_section.radii), min(to_section.radii))
        if connection.thickness != expected_thickness or connection.centerline != (from_section.center, to_section.center):
            _fail(f"{where} lost direct producer/guide endpoint lineage")
        if not math.isfinite(float(connection.thickness[0])) or not math.isfinite(float(connection.thickness[1])):
            _fail(f"{where} thickness is not finite")
    for route_name, indices in expected_route_indices.items():
        route_connections = tuple(
            connection.spec for connection in connections if connection.spec.route == route_name
        )
        if tuple(spec.from_section_index for spec in route_connections) != indices[:-1] or tuple(spec.to_section_index for spec in route_connections) != indices[1:]:
            _fail(f"successor {route_name} route topology does not match the authored branch")
    return profile


def _make_authored_head_neck_route_sweep(
    profile: Any,
    recipe: str,
    section_indices: tuple[int, ...],
    tangent_axis_name: str,
    transverse_axis_names: tuple[str, str],
) -> _RegionalProfileSweep:
    """Compile one exact authored route, including full station ellipsoids."""

    axes = profile.axes
    tangent = tuple(float(value) for value in _vec3(getattr(axes, tangent_axis_name), f"{recipe}.tangent-axis"))
    first = tuple(float(value) for value in _vec3(getattr(axes, transverse_axis_names[0]), f"{recipe}.transverse-first-axis"))
    second = tuple(float(value) for value in _vec3(getattr(axes, transverse_axis_names[1]), f"{recipe}.transverse-second-axis"))
    axis_index = {"lateral": 0, "up": 1, "forward": 2}
    tangent_index = axis_index[tangent_axis_name]
    transverse_indices = tuple(axis_index[name] for name in transverse_axis_names)
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for route_index, source_index in enumerate(section_indices):
        source = profile.sections[source_index]
        center = _vec3(source.center, f"{recipe}.{source.name}.center")
        radii = tuple(float(value) for value in source.radii)
        _finite_positive(radii, f"{recipe}.{source.name}.authored-radii")
        if route_index:
            span = float(np.linalg.norm(center - _vec3(sections[-1].center, f"{recipe}.previous-center")))
            if not math.isfinite(span) or span <= _DEGENERATE_TOLERANCE:
                _fail(f"{recipe}.{source.name} follows a degenerate authored span")
            path_length += span
        sections.append(_ProfileSection(
            name=source.name,
            owner=source.owner,
            center=tuple(float(value) for value in center),
            tangent=tangent,
            transverse_axes=(first, second),
            transverse_radii=(radii[transverse_indices[0]], radii[transverse_indices[1]]),
            path_length=path_length,
            tangent_radius=radii[tangent_index],
            source_section_index=source_index,
        ))
    ordered = tuple(sections)
    caps = (
        _ProfileEndpointCap(
            "start", ordered[0].center, tuple(-value for value in tangent),
            ordered[0].transverse_axes, ordered[0].transverse_radii,
            float(ordered[0].tangent_radius),
        ),
        _ProfileEndpointCap(
            "end", ordered[-1].center, tangent,
            ordered[-1].transverse_axes, ordered[-1].transverse_radii,
            float(ordered[-1].tangent_radius),
        ),
    )
    sweep = _ProfileSweep(ordered, caps, profile_operation=_HEAD_NECK_PROFILE_OPERATION)
    _validate_profile_sweep(sweep)
    return _RegionalProfileSweep(recipe, ordered[0].owner, sweep)


def _make_head_neck_sweeps(guide: Any) -> tuple[_RegionalProfileSweep, ...]:
    """Build exactly the shared vertical and forward authored route sweeps."""

    profile = _validate_authored_head_neck_guide(guide)
    return tuple(
        _make_authored_head_neck_route_sweep(profile, name, indices, tangent_axis, transverse_axes)
        for name, indices, tangent_axis, transverse_axes in _HEAD_NECK_ROUTE_TOPOLOGY
    )


def _head_neck_radius_lineage_json(lineage: Any) -> dict[str, Any]:
    return {
        "base": int(lineage.base),
        "factor": int(lineage.factor),
        "scaled": int(lineage.scaled),
        "reference": {
            "owner": _baseline._address_json(lineage.reference[0]),
            "role": lineage.reference[1],
            "index": int(lineage.reference_index),
        },
        "provenance": dict(lineage.provenance),
        "consumed_section": lineage.consumed_section,
    }


def _head_neck_section_json(section: Any) -> dict[str, Any]:
    return {
        "name": section.name,
        "section_index": int(section.section_index),
        "source_section_index": int(section.source_section_index),
        "frame_index": int(section.frame_index),
        "landmark_index": int(section.landmark_index),
        "owner": _baseline._address_json(section.owner.key),
        "center": [float(value) for value in section.center],
        "radii": {
            "lateral": float(section.radii[0]),
            "up": float(section.radii[1]),
            "forward": float(section.radii[2]),
        },
        "lineage": {
            "lateral": _head_neck_radius_lineage_json(section.lateral_lineage),
            "up": _head_neck_radius_lineage_json(section.up_lineage),
            "forward": _head_neck_radius_lineage_json(section.forward_lineage),
        },
    }


def _head_neck_connection_json(connection: Any) -> dict[str, Any]:
    return {
        "name": connection.spec.name,
        "from_section_index": int(connection.spec.from_section_index),
        "to_section_index": int(connection.spec.to_section_index),
        "route": connection.spec.route,
        "centerline": [[float(value) for value in point] for point in connection.centerline],
        "thickness": [float(value) for value in connection.thickness],
    }


def _head_neck_route_json(item: _RegionalProfileSweep) -> dict[str, Any]:
    route = next((entry for entry in _HEAD_NECK_ROUTE_TOPOLOGY if entry[0] == item.recipe), None)
    if route is None:
        _fail(f"unknown successor head/neck route {item.recipe!r}")
    name, section_indices, tangent_axis, transverse_axes = route
    axis_index = {"lateral": 0, "up": 1, "forward": 2}
    tangent_index = axis_index[tangent_axis]
    transverse_indices = tuple(axis_index[axis] for axis in transverse_axes)

    def full_radii(section: _ProfileSection) -> dict[str, float]:
        values = [0.0, 0.0, 0.0]
        values[tangent_index] = float(section.tangent_radius)
        values[transverse_indices[0]] = float(section.transverse_radii[0])
        values[transverse_indices[1]] = float(section.transverse_radii[1])
        return {axis: values[index] for axis, index in axis_index.items()}

    return {
        "name": name,
        "operation": _HEAD_NECK_PROFILE_OPERATION,
        "section_indices": list(section_indices),
        "section_names": list(item.sweep.names),
        "connection_names": [
            connection[0]
            for connection in _baseline.HEAD_NECK_PROFILE_CONNECTIONS
            if connection[3] == name
        ],
        "tangent_axis": tangent_axis,
        "transverse_axes": list(transverse_axes),
        "owner_keys": [_baseline._address_json(owner.key) for owner in item.sweep.owners],
        "station_radii": [full_radii(section) for section in item.sweep.sections],
        "endpoint_cap_count": len(item.sweep.endpoint_caps),
        "internal_transition_count": len(item.sweep.internal_transitions),
    }


def _head_neck_metadata(region: SuccessorRegion) -> dict[str, Any]:
    profile = region.head_neck_profile
    if profile is None:
        _fail("successor region is missing the consumed authored head/neck profile")
    return {
        "profile_format": _baseline.AUTHORED_HEAD_NECK_PROFILE_FORMAT,
        "operation": _HEAD_NECK_PROFILE_OPERATION,
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "provenance": dict(profile.provenance),
        "sections_consumed": len(profile.sections),
        "connections_consumed": len(profile.connections),
        "sections": [_head_neck_section_json(section) for section in profile.sections],
        "connections": [_head_neck_connection_json(connection) for connection in profile.connections],
        "route_topology": [_head_neck_route_json(item) for item in region.head_neck_sweeps],
    }


def _limb_chain_sweep(
    chain_name: str,
    station_specs: tuple[tuple[str, Any, tuple[float, float, float], tuple[float, float]], ...],
    axes: Any,
) -> _LimbChainSweep:
    """Compile one ordered chain using the shared generalized sweep machinery."""

    if len(station_specs) != 5:
        _fail(f"successor {chain_name} requires exactly five ordered stations")
    centers = tuple(_vec3(spec[2], f"{chain_name}.{spec[0]}.center") for spec in station_specs)
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for index, (name, owner, _center, radii) in enumerate(station_specs):
        if index == 0:
            direction = centers[1] - centers[0]
        elif index == len(centers) - 1:
            direction = centers[-1] - centers[-2]
        else:
            direction = centers[index + 1] - centers[index - 1]
        tangent, first, second = _frame_from_tangent(
            direction,
            _vec3(axes.lateral, f"{chain_name}.lateral-axis"),
            _vec3(axes.forward, f"{chain_name}.forward-axis"),
            f"{chain_name}.{name}",
        )
        if index:
            span_length = float(np.linalg.norm(centers[index] - centers[index - 1]))
            if span_length <= _DEGENERATE_TOLERANCE:
                _fail(f"{chain_name}.{name} follows a degenerate station")
            path_length += span_length
        _finite_positive(tuple(float(value) for value in radii), f"{chain_name}.{name}.radii")
        sections.append(_ProfileSection(
            name=name,
            owner=owner,
            center=tuple(float(value) for value in centers[index]),
            tangent=tuple(float(value) for value in tangent),
            transverse_axes=(tuple(float(value) for value in first), tuple(float(value) for value in second)),
            transverse_radii=tuple(float(value) for value in radii),
            path_length=path_length,
        ))
    ordered = tuple(sections)
    start_cap_axial = max(min(ordered[0].transverse_radii), min(ordered[1].transverse_radii))
    end_cap_axial = max(min(ordered[-1].transverse_radii), min(ordered[-2].transverse_radii))
    caps = (
        _ProfileEndpointCap(
            "start", ordered[0].center, tuple(-float(value) for value in ordered[0].tangent),
            ordered[0].transverse_axes, ordered[0].transverse_radii,
            start_cap_axial,
        ),
        _ProfileEndpointCap(
            "end", ordered[-1].center, ordered[-1].tangent,
            ordered[-1].transverse_axes, ordered[-1].transverse_radii,
            end_cap_axial,
        ),
    )
    sweep = _ProfileSweep(ordered, caps)
    _validate_profile_sweep(sweep)
    owners: list[Any] = []
    for section in ordered:
        if not any(section.owner is owner for owner in owners):
            owners.append(section.owner)
    return _LimbChainSweep(chain_name, tuple(owners), sweep)


def _authored_arm_profile_from_guide(guide: Any) -> Any:
    """Read the v10 bilateral arm profile through the guide control boundary."""

    controls = getattr(guide, "controls", None)
    profile = getattr(controls, "arm_profile", None) if controls is not None else None
    if profile is None:
        profile = getattr(guide, "arm_profile", None)
    if profile is None:
        _fail("successor guide is missing controls.arm_profile")
    return profile


def _effective_authored_radius(
    direction: np.ndarray,
    axes: tuple[np.ndarray, np.ndarray, np.ndarray],
    radii: tuple[float, float, float],
    where: str,
) -> float:
    """Return the exact ellipsoid support radius along a route-frame axis."""

    direction = _unit(direction, where)
    value = math.sqrt(sum((float(np.dot(direction, axis)) * radius) ** 2 for axis, radius in zip(axes, radii)))
    if not math.isfinite(value) or value <= 0.0:
        _fail(f"{where} produced an invalid authored support radius")
    return value


def _validate_arm_profile_guide(guide: Any) -> Any:
    """Fail closed on exact v10 arm station topology and guide lineage."""

    profile = _authored_arm_profile_from_guide(guide)
    topology_axes = getattr(getattr(guide, "topology", None), "axes", None)
    if topology_axes is None or getattr(profile, "axes", None) != topology_axes:
        _fail("successor arm profile axes must match guide topology")
    if profile.axes != _baseline._FIXED_GUIDE_AXES:
        _fail("successor arm profile axes must match the fixed guide axes")
    if tuple(side.side for side in profile.sides) != ("left", "right"):
        _fail("successor arm profile sides must be ordered left then right")
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    expected_names = (
        "upper-arm-start",
        "upper-arm-midpoint",
        "elbow",
        "forearm-midpoint",
        "forearm-distal",
    )
    expected_roles = ("upper_arm", "upper_arm", "upper_arm", "forearm", "forearm")
    expected_axis_lineages = ("lateral_lineage", "up_lineage", "forward_lineage")
    for side_index, side in enumerate(profile.sides):
        if tuple(section.name for section in side.sections) != expected_names:
            _fail(f"arm profile side {side_index} stations are not the exact five-station topology")
        if len(side.sections) != 5:
            _fail(f"arm profile side {side_index} must contain exactly five stations")
        previous_by_owner: dict[Any, float] = {}
        for index, station in enumerate(side.sections):
            where = f"arm-profile.{side.side}.{station.name}"
            if station.section_index != index or station.source_section_index != index:
                _fail(f"{where} source indices are not exact")
            if station.owner.key not in source_by_key or source_by_key[station.owner.key] is not station.owner:
                _fail(f"{where} lost canonical descriptor identity")
            if station.owner.key[1] != (side.side,) or station.owner.key[3] != expected_roles[index]:
                _fail(f"{where} lost source ownership")
            if station.frame.owner != station.owner.key or station.frame.role != _baseline.ARM_PROFILE_CONTROL_FRAME_ROLE:
                _fail(f"{where} lost frame/landmark ownership")
            expected_landmark_role = _baseline.ARM_PROFILE_LANDMARK_PREFIX + station.name.replace("-", "_")
            if station.landmark.owner != station.owner.key or station.landmark.role != expected_landmark_role:
                _fail(f"{where} lost authored landmark ownership")
            if station.landmark.frame != (station.frame.owner, station.frame.role):
                _fail(f"{where} lost frame/landmark binding")
            if station.frame.translation != (0.0, 0.0, 0.0) or station.frame.rotation_xyzw != (0.0, 0.0, 0.0, 1.0):
                _fail(f"{where} control frame is not identity-only")
            if station.landmark.position[0] != 0.0 or station.landmark.position[2] != 0.0:
                _fail(f"{where} moved its source-local landmark off the arm path")
            local_y = float(station.landmark.position[1])
            previous = previous_by_owner.get(station.owner.key)
            if previous is not None and local_y >= previous:
                _fail(f"{where} stations are not ordered toward the distal end")
            previous_by_owner[station.owner.key] = local_y
            _vec3(station.center, f"{where}.center")
            _finite_positive(tuple(float(value) for value in station.radii), f"{where}.radii")
            for axis_name, lineage_name, radius in zip(("lateral", "up", "forward"), expected_axis_lineages, station.radii):
                lineage = getattr(station, lineage_name, None)
                if lineage is None:
                    _fail(f"{where} is missing {lineage_name}")
                expected_role = (
                    _baseline.ARM_PROFILE_DIMENSION_PREFIX
                    + station.name.replace("-", "_")
                    + "_"
                    + _baseline.ARM_PROFILE_DIMENSION_SUFFIXES[("lateral", "up", "forward").index(axis_name)]
                )
                if lineage.reference != (station.owner.key, expected_role):
                    _fail(f"{where}.{lineage_name} has invalid source reference")
                if (
                    lineage.consumed_section != station.name
                    or lineage.reference_index < 0
                    or lineage.reference_index >= _baseline.MAX_AUTHORED_DIMENSIONS
                    or lineage.base <= 0
                    or lineage.factor <= 0
                ):
                    _fail(f"{where}.{lineage_name} has invalid consumed section or factor")
                if lineage.scaled != lineage.base * lineage.factor // 1000:
                    _fail(f"{where}.{lineage_name} lost exact producer projection")
                if not math.isclose(float(radius), lineage.scaled / 1000.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE):
                    _fail(f"{where}.{lineage_name} is not the skin-consumed radius")
                if lineage.provenance != profile.provenance:
                    _fail(f"{where}.{lineage_name} lost producer provenance")
    return profile


def _make_full_volume_profile_route(
    route_name: str,
    source_stations: tuple[Any, ...],
    axes: Any,
    operation: str,
    route_kind: str,
) -> _LimbChainSweep:
    """Compile a route whose station volumes retain all authored axes."""

    if len(source_stations) < 2:
        _fail(f"{route_name} requires at least two authored stations")
    guide_axes = tuple(
        _unit(_vec3(getattr(axes, axis), f"{route_name}.{axis}-axis"), f"{route_name}.{axis}-axis")
        for axis in ("lateral", "up", "forward")
    )
    centers = tuple(_vec3(station.center, f"{route_name}.{station.name}.center") for station in source_stations)
    full_radii = tuple(tuple(float(value) for value in station.radii) for station in source_stations)
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for index, (station, center, radii) in enumerate(zip(source_stations, centers, full_radii)):
        if index == 0:
            direction = centers[1] - centers[0]
        elif index == len(centers) - 1:
            direction = centers[-1] - centers[-2]
        else:
            direction = centers[index + 1] - centers[index - 1]
        tangent, first, second = _frame_from_tangent(
            direction,
            guide_axes[0],
            guide_axes[1],
            f"{route_name}.{station.name}",
        )
        if index:
            span_length = float(np.linalg.norm(centers[index] - centers[index - 1]))
            if span_length <= _DEGENERATE_TOLERANCE:
                _fail(f"{route_name}.{station.name} follows a degenerate station")
            path_length += span_length
        transverse_radii = (
            _effective_authored_radius(first, guide_axes, radii, f"{route_name}.{station.name}.transverse-first"),
            _effective_authored_radius(second, guide_axes, radii, f"{route_name}.{station.name}.transverse-second"),
        )
        sections.append(_ProfileSection(
            name=station.name,
            owner=station.owner,
            center=tuple(float(value) for value in center),
            tangent=tuple(float(value) for value in tangent),
            transverse_axes=(
                tuple(float(value) for value in first),
                tuple(float(value) for value in second),
            ),
            transverse_radii=transverse_radii,
            path_length=path_length,
            tangent_radius=_effective_authored_radius(tangent, guide_axes, radii, f"{route_name}.{station.name}.tangent"),
            source_section_index=int(station.source_section_index),
            station_volume_axes=tuple(tuple(float(value) for value in axis) for axis in guide_axes),
            station_volume_radii=radii,
        ))
    ordered = tuple(sections)
    caps = (
        _ProfileEndpointCap(
            "start", ordered[0].center, tuple(-float(value) for value in ordered[0].tangent),
            ordered[0].transverse_axes, ordered[0].transverse_radii,
            ordered[0].tangent_radius or min(ordered[0].transverse_radii),
        ),
        _ProfileEndpointCap(
            "end", ordered[-1].center, ordered[-1].tangent,
            ordered[-1].transverse_axes, ordered[-1].transverse_radii,
            ordered[-1].tangent_radius or min(ordered[-1].transverse_radii),
        ),
    )
    sweep = _ProfileSweep(ordered, caps, profile_operation=operation)
    _validate_profile_sweep(sweep)
    owners: list[Any] = []
    for station in source_stations:
        if not any(station.owner is owner for owner in owners):
            owners.append(station.owner)
    return _LimbChainSweep(route_name, tuple(owners), sweep, route_kind, source_stations)


def _make_arm_profile_route(
    route_name: str,
    side: str,
    source_stations: tuple[Any, ...],
    axes: Any,
) -> _LimbChainSweep:
    """Compile one shared route from exact authored arm stations."""

    if len(source_stations) != 3:
        _fail(f"{route_name} requires exactly three authored arm stations")
    result = _make_full_volume_profile_route(
        route_name,
        source_stations,
        axes,
        _ARM_PROFILE_OPERATION,
        "arm-profile",
    )
    return result


def _make_arm_profile_sweeps(guide: Any) -> tuple[_LimbChainSweep, ...]:
    """Build exactly two authored routes per side with one shared elbow seam."""

    profile = _validate_arm_profile_guide(guide)
    result: list[_LimbChainSweep] = []
    for side in profile.sides:
        stations = tuple(side.sections)
        result.append(_make_arm_profile_route(f"{side.side}-upper-arm-route", side.side, stations[:3], profile.axes))
        result.append(_make_arm_profile_route(f"{side.side}-forearm-route", side.side, stations[2:], profile.axes))
        if result[-2].source_stations[-1] is not result[-1].source_stations[0]:
            _fail(f"{side.side} arm routes do not share the single authored elbow seam")
        if result[-2].source_stations[-1].owner.key[3] != "upper_arm":
            _fail(f"{side.side} authored elbow seam is not upper-arm owned")
    return tuple(result)


def _authored_leg_profile_from_guide(guide: Any) -> Any:
    """Read the v9 bilateral authored leg profile through the guide boundary."""

    controls = getattr(guide, "controls", None)
    profile = getattr(controls, "leg_profile", None) if controls is not None else None
    if profile is None:
        profile = getattr(guide, "leg_profile", None)
    if profile is None:
        _fail("successor guide is missing controls.leg_profile")
    return profile


def _validate_leg_profile_guide(guide: Any) -> Any:
    """Fail closed on exact v10 authored leg station topology and lineage."""

    profile = _authored_leg_profile_from_guide(guide)
    topology_axes = getattr(getattr(guide, "topology", None), "axes", None)
    if topology_axes is None or getattr(profile, "axes", None) != topology_axes:
        _fail("successor leg profile axes must match guide topology")
    if profile.axes != _baseline._FIXED_GUIDE_AXES:
        _fail("successor leg profile axes must match the fixed guide axes")
    if tuple(side.side for side in profile.sides) != ("left", "right"):
        _fail("successor leg profile sides must be ordered left then right")

    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    limb_by_key = {
        item.owner.key: item
        for item in guide.limb_guides
        if item.owner.key[3] in {"thigh", "shin"}
    }
    expected_names = (
        "thigh-start",
        "thigh-midpoint",
        "knee",
        "shin-midpoint",
        "hock-endpoint",
    )
    expected_roles = ("thigh", "thigh", "thigh", "shin", "shin")
    expected_axis_lineages = ("lateral_lineage", "up_lineage", "forward_lineage")
    expected_suffixes = _baseline.LEG_PROFILE_DIMENSION_SUFFIXES
    for side_index, side in enumerate(profile.sides):
        where_side = f"leg-profile.{side.side}"
        if tuple(section.name for section in side.sections) != expected_names:
            _fail(f"{where_side} stations are not the exact five-station topology")
        if len(side.sections) != 5:
            _fail(f"{where_side} must contain exactly five stations")
        previous_by_owner: dict[Any, float] = {}
        for index, station in enumerate(side.sections):
            where = f"{where_side}.{station.name}"
            if station.section_index != index or station.source_section_index != index:
                _fail(f"{where} source indices are not exact")
            canonical_owner = source_by_key.get(station.owner.key)
            if canonical_owner is None or canonical_owner is not station.owner:
                _fail(f"{where} lost canonical descriptor identity")
            if station.owner.key[1] != (side.side,) or station.owner.key[3] != expected_roles[index]:
                _fail(f"{where} lost source ownership")
            if station.frame.owner != station.owner.key or station.frame.role != _baseline.LEG_PROFILE_CONTROL_FRAME_ROLE:
                _fail(f"{where} lost frame ownership")
            if (
                station.frame_index < 0
                or station.frame_index >= _baseline.MAX_AUTHORED_FRAMES
                or station.landmark_index < 0
                or station.landmark_index >= _baseline.MAX_AUTHORED_LANDMARKS
            ):
                _fail(f"{where} has an invalid source frame or landmark index")
            expected_landmark_role = _baseline.LEG_PROFILE_LANDMARK_PREFIX + station.name.replace("-", "_")
            if station.landmark.owner != station.owner.key or station.landmark.role != expected_landmark_role:
                _fail(f"{where} lost landmark ownership")
            if station.landmark.frame != (station.frame.owner, station.frame.role):
                _fail(f"{where} lost frame/landmark binding")
            if station.frame.translation != (0.0, 0.0, 0.0) or station.frame.rotation_xyzw != (0.0, 0.0, 0.0, 1.0):
                _fail(f"{where} control frame is not identity-only")
            if station.landmark.position[0] != 0.0 or station.landmark.position[2] != 0.0:
                _fail(f"{where} moved its source-local landmark off the leg path")
            local_y = float(station.landmark.position[1])
            previous = previous_by_owner.get(station.owner.key)
            if previous is not None and local_y >= previous:
                _fail(f"{where} stations are not ordered toward the distal end")
            previous_by_owner[station.owner.key] = local_y

            _vec3(station.center, f"{where}.center")
            _finite_positive(tuple(float(value) for value in station.radii), f"{where}.radii")
            for axis_name, lineage_name, suffix, radius in zip(
                ("lateral", "up", "forward"),
                expected_axis_lineages,
                expected_suffixes,
                station.radii,
            ):
                lineage = getattr(station, lineage_name, None)
                if lineage is None:
                    _fail(f"{where} is missing {lineage_name}")
                expected_role = (
                    _baseline.LEG_PROFILE_DIMENSION_PREFIX
                    + station.name.replace("-", "_")
                    + "_"
                    + suffix
                )
                if lineage.reference != (station.owner.key, expected_role):
                    _fail(f"{where}.{lineage_name} has invalid source reference")
                if (
                    lineage.consumed_section != station.name
                    or lineage.reference_index < 0
                    or lineage.reference_index >= _baseline.MAX_AUTHORED_DIMENSIONS
                    or lineage.base <= 0
                    or lineage.factor <= 0
                ):
                    _fail(f"{where}.{lineage_name} has invalid consumed section or factor")
                if lineage.scaled != lineage.base * lineage.factor // 1000:
                    _fail(f"{where}.{lineage_name} lost exact producer projection")
                if not math.isclose(float(radius), lineage.scaled / 1000.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE):
                    _fail(f"{where}.{lineage_name} is not the skin-consumed radius")
                if lineage.provenance != profile.provenance:
                    _fail(f"{where}.{lineage_name} lost producer provenance")
                if axis_name not in {"lateral", "up", "forward"}:
                    _fail(f"{where} has an unknown authored axis")
            if station.profile_provenance != profile.provenance:
                _fail(f"{where} lost authored profile provenance")
            if station.variant_provenance != profile.variant_provenance:
                _fail(f"{where} lost variant projection provenance")

        thigh = limb_by_key.get(profile.sides[side_index].sections[0].owner.key)
        shin = limb_by_key.get(profile.sides[side_index].sections[3].owner.key)
        if thigh is None or shin is None or thigh.owner.key[3] != "thigh" or shin.owner.key[3] != "shin":
            _fail(f"{where_side} is missing its thigh/shin centerlines")
        route_points = (
            thigh.sections[0].centerline[0],
            thigh.sections[0].centerline[1],
            thigh.sections[1].centerline[1],
            shin.sections[0].centerline[1],
            shin.sections[1].centerline[1],
        )
        for index, point in enumerate(route_points):
            _require_exact_same_point(side.sections[index].center, point, f"{where_side}.{expected_names[index]} centerline binding")
        _require_exact_same_point(side.sections[2].center, shin.sections[0].centerline[0], f"{where_side}.knee/thigh-shin seam")
        if thigh.joint is None or thigh.joint.name != "knee":
            _fail(f"{where_side} is missing its thigh-owned knee")
        if thigh.joint.center != side.sections[2].center:
            _fail(f"{where_side} knee seam is not thigh-owned")
        if shin.joint is None or shin.joint.name != "hock":
            _fail(f"{where_side} is missing its shin-owned hock")
        if shin.joint.center != side.sections[4].center:
            _fail(f"{where_side} hock endpoint is not shin-owned")
    return profile


def _make_leg_profile_route(
    route_name: str,
    side: str,
    source_stations: tuple[Any, ...],
    axes: Any,
) -> _LimbChainSweep:
    """Compile one exact five-station authored leg route."""

    if len(source_stations) != 5:
        _fail(f"{route_name} requires exactly five authored leg stations")
    return _make_full_volume_profile_route(
        route_name,
        source_stations,
        axes,
        _LEG_PROFILE_OPERATION,
        "leg-profile",
    )


def _make_leg_profile_sweeps(guide: Any) -> tuple[_LimbChainSweep, ...]:
    """Build exactly one authored five-station route per bilateral side."""

    profile = _validate_leg_profile_guide(guide)
    result = tuple(
        _make_leg_profile_route(f"{side.side}-leg", side.side, tuple(side.sections), profile.axes)
        for side in profile.sides
    )
    if tuple(item.chain_name for item in result) != ("left-leg", "right-leg"):
        _fail("successor authored leg route order is unstable")
    for route, side in zip(result, profile.sides):
        if route.source_stations != tuple(side.sections):
            _fail(f"{route.chain_name} lost its exact authored station binding")
        if route.source_stations[2].owner.key[3] != "thigh":
            _fail(f"{route.chain_name} knee seam is not thigh-owned")
        if route.source_stations[4].owner.key[3] != "shin":
            _fail(f"{route.chain_name} hock endpoint is not shin-owned")
    return result


def _authored_foot_profile_from_guide(guide: Any) -> Any:
    """Read the exact bilateral authored foot profile from the guide boundary."""

    profile = getattr(guide, "foot_profile", None)
    if profile is None:
        _fail("successor guide is missing foot_profile")
    return profile


def _validate_foot_profile_guide(guide: Any) -> Any:
    """Fail closed on the authored pad/toe profile and its derived foot chain."""

    profile = _authored_foot_profile_from_guide(guide)
    leg_profile = _validate_leg_profile_guide(guide)
    topology_axes = getattr(getattr(guide, "topology", None), "axes", None)
    if topology_axes is None or profile.axes != topology_axes or profile.axes != _baseline._FIXED_GUIDE_AXES:
        _fail("successor foot profile axes must match the guide topology and fixed axes")
    if tuple(side.side for side in profile.sides) != tuple(_baseline.FOOT_PROFILE_SIDE_NAMES):
        _fail("successor foot profile sides must be ordered left then right")
    if not isinstance(profile.provenance, dict) or set(profile.provenance) != {"source", "document", "namespace"}:
        _fail("successor foot profile provenance is incomplete")

    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    paws = {
        item.owner.key[1][0]: item
        for item in guide.paw_guides
        if item.owner.key[3] == "foot"
    }
    if set(paws) != set(_baseline.FOOT_PROFILE_SIDE_NAMES):
        _fail("successor foot guide inventory must contain exactly two bilateral feet")
    expected_names = tuple(_baseline.FOOT_PROFILE_SECTION_NAMES)
    expected_axis_lineages = ("lateral_lineage", "up_lineage", "forward_lineage")
    axis_names = ("lateral", "up", "forward")
    for side_index, side in enumerate(profile.sides):
        where_side = f"foot-profile.{side.side}"
        if side.hock_binding != (
            "authored_leg_profile",
            side_index,
            _baseline.FOOT_PROFILE_HOCK_SECTION_INDEX,
        ):
            _fail(f"{where_side} lost its exact authored leg hock binding")
        leg_side = leg_profile.sides[side_index]
        hock = leg_side.sections[_baseline.FOOT_PROFILE_HOCK_SECTION_INDEX]
        if hock.name != "hock-endpoint" or hock.owner.key[1] != (side.side,) or hock.owner.key[3] != "shin":
            _fail(f"{where_side} hock binding is not shin-owned")
        if len(side.sections) != 2 or tuple(station.name for station in side.sections) != expected_names:
            _fail(f"{where_side} must contain exactly ordered pad and toe stations")
        foot_key = (hock.owner.key[0], (side.side,), "part", "foot")
        foot_owner = source_by_key.get(foot_key)
        if foot_owner is None:
            _fail(f"{where_side} is missing its canonical foot owner")
        paw = paws.get(side.side)
        if paw is None or paw.owner is not foot_owner or paw.foot_chain is None:
            _fail(f"{where_side} lost its canonical foot chain owner")
        if foot_owner.parent != hock.owner.key or source_by_key.get(foot_owner.parent) is not hock.owner:
            _fail(f"{where_side} foot parent is not the canonical shin owner")
        chain = paw.foot_chain
        if chain.profile is not profile or chain.axes != profile.axes:
            _fail(f"{where_side} chain does not retain the exact authored foot profile")
        if chain.hock_anchor != hock.center or chain.hock_radii != hock.radii:
            _fail(f"{where_side} chain hock is not cross-bound to the authored shin station")
        if chain.pad_center != side.sections[0].center or chain.pad_radii != side.sections[0].radii:
            _fail(f"{where_side} chain pad is not cross-bound to the authored guide")
        if chain.toe_center != side.sections[1].center or chain.toe_radii != side.sections[1].radii:
            _fail(f"{where_side} chain toe is not cross-bound to the authored guide")
        expected_metatarsal_midpoint = tuple(
            float(value)
            for value in 0.5 * (
                np.asarray(chain.metatarsal_centerline[0], dtype=np.float64)
                + np.asarray(chain.metatarsal_centerline[1], dtype=np.float64)
            )
        )
        expected_pad_toe_midpoint = tuple(
            float(value)
            for value in 0.5 * (
                np.asarray(chain.pad_center, dtype=np.float64)
                + np.asarray(chain.toe_center, dtype=np.float64)
            )
        )
        if chain.metatarsal_midpoint != expected_metatarsal_midpoint:
            _fail(f"{where_side} metatarsal midpoint is not the exact derived guide control")
        if chain.pad_toe_midpoint != expected_pad_toe_midpoint:
            _fail(f"{where_side} pad-toe midpoint is not the exact derived guide control")
        expected_metatarsal_midpoint_radii = tuple(
            float(value)
            for value in 0.5 * (
                np.asarray(chain.hock_radii, dtype=np.float64)
                + np.asarray(chain.pad_radii, dtype=np.float64)
            )
        )
        expected_pad_toe_midpoint_radii = tuple(
            float(value)
            for value in 0.5 * (
                np.asarray(chain.pad_radii, dtype=np.float64)
                + np.asarray(chain.toe_radii, dtype=np.float64)
            )
        )
        if chain.metatarsal_midpoint_radii != expected_metatarsal_midpoint_radii:
            _fail(f"{where_side} metatarsal midpoint radii are not exact derived guide controls")
        if chain.pad_toe_midpoint_radii != expected_pad_toe_midpoint_radii:
            _fail(f"{where_side} pad-toe midpoint radii are not exact derived guide controls")
        for index, station in enumerate(side.sections):
            where = f"{where_side}.{station.name}"
            if station.section_index != index or station.source_section_index != index:
                _fail(f"{where} source section indices are not exact")
            if station.owner is not foot_owner or station.owner.key[1] != (side.side,) or station.owner.key[3] != "foot":
                _fail(f"{where} lost canonical foot ownership")
            if station.frame.owner != station.owner.key or station.frame.role != _baseline.FOOT_PROFILE_CONTROL_FRAME_ROLE:
                _fail(f"{where} lost its exact control frame ownership")
            if station.landmark.owner != station.owner.key or station.landmark.frame != (station.frame.owner, station.frame.role):
                _fail(f"{where} lost its exact landmark/frame binding")
            if station.frame.translation != (0.0, 0.0, 0.0) or station.frame.rotation_xyzw != (0.0, 0.0, 0.0, 1.0):
                _fail(f"{where} control frame is not identity-only")
            if station.landmark.role != _baseline.FOOT_PROFILE_LANDMARK_PREFIX + station.name:
                _fail(f"{where} lost its exact authored landmark role")
            _vec3(station.center, f"{where}.center")
            _finite_positive(tuple(float(value) for value in station.radii), f"{where}.radii")
            for axis_name, lineage_name, suffix, radius in zip(
                axis_names,
                expected_axis_lineages,
                _baseline.FOOT_PROFILE_DIMENSION_SUFFIXES,
                station.radii,
            ):
                lineage = getattr(station, lineage_name, None)
                if lineage is None:
                    _fail(f"{where} is missing {lineage_name}")
                expected_role = _baseline.FOOT_PROFILE_DIMENSION_PREFIX + station.name + "_" + suffix
                expected_factor = _baseline._foot_profile_factors(station.owner.profile_id)[axis_names.index(axis_name)]
                if lineage.reference != (station.owner.key, expected_role):
                    _fail(f"{where}.{axis_name} lineage lost its source role")
                if (
                    lineage.consumed_section != station.name
                    or lineage.reference_index < 0
                    or lineage.reference_index >= _baseline.MAX_AUTHORED_DIMENSIONS
                    or lineage.base <= 0
                    or lineage.factor != expected_factor
                    or lineage.scaled != lineage.base * lineage.factor // 1000
                ):
                    _fail(f"{where}.{axis_name} lineage is not the exact producer projection")
                if not math.isclose(float(radius), lineage.scaled / 1000.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE):
                    _fail(f"{where}.{axis_name} radius is not the exact guide radius")
                if lineage.provenance != profile.provenance:
                    _fail(f"{where}.{axis_name} lineage provenance does not match the profile")
            if station.profile_provenance != profile.provenance or station.variant_provenance != profile.variant_provenance:
                _fail(f"{where} lost exact profile/variant provenance")
    return profile


def _require_same_point(first: Any, second: Any, where: str) -> None:
    if not np.allclose(_vec3(first, f"{where}.first"), _vec3(second, f"{where}.second"), rtol=0.0, atol=_FRAME_TOLERANCE):
        _fail(f"{where} controls do not overlap")


def _require_exact_same_point(first: Any, second: Any, where: str) -> None:
    """Require two guide controls to be the same endpoint, not merely close."""

    first_vector = _vec3(first, f"{where}.first")
    second_vector = _vec3(second, f"{where}.second")
    if not np.array_equal(first_vector, second_vector):
        _fail(f"{where} controls must join exactly")


def _require_path_shape(
    shape: Any,
    path: tuple[tuple[float, float, float], tuple[float, float, float]],
    profile: tuple[float, ...],
    where: str,
    *,
    expected_name: str = "tapered-segment",
) -> None:
    """Require a retained baseline segment to reproduce its guide controls."""

    if not isinstance(shape, dict) or shape.get("name") != expected_name:
        _fail(f"{where} must retain a {expected_name!r} field shape")
    if not profile:
        _fail(f"{where} guide profile must provide endpoint controls")
    _require_exact_same_point(shape.get("from"), path[0], f"{where}.from")
    _require_exact_same_point(shape.get("to"), path[1], f"{where}.to")
    try:
        shape_profile = (float(shape["r0"]), float(shape["r1"]))
    except (KeyError, TypeError, ValueError):
        _fail(f"{where} field shape is missing endpoint profile controls")
    expected_profile = (float(profile[0]), float(profile[-1]))
    if shape_profile != expected_profile:
        _fail(f"{where} field profile controls do not match the guide")


def _require_mass_shape(
    shape: Any,
    center: Any,
    radii: Any,
    where: str,
    *,
    expected_name: str = "ellipsoid",
) -> None:
    """Require a retained baseline mass to reproduce exact guide controls."""

    if not isinstance(shape, dict) or shape.get("name") != expected_name:
        _fail(f"{where} must retain an {expected_name!r} field shape")
    try:
        shape_center = _vec3(shape["center"], f"{where}.center")
        shape_radii = _vec3(shape["radii"], f"{where}.radii")
    except (KeyError, TypeError, ValueError):
        _fail(f"{where} field shape is missing mass controls")
    if not np.array_equal(shape_center, _vec3(center, f"{where}.guide-center")):
        _fail(f"{where} field center does not match the guide")
    if not np.array_equal(shape_radii, _vec3(radii, f"{where}.guide-radii")):
        _fail(f"{where} field radii do not match the guide")


def _validate_extremity_baseline_fields(guide: Any, baseline_fields: tuple[Any, ...]) -> None:
    """Validate the exact bilateral hand/foot baseline inventory being removed."""

    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    paws = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.paw_guides}
    expected_counts = {recipe: 2 for recipe in ("paw", "extremity-bridge", "metatarsal", "paw-pad", "toe-box")}
    for recipe, expected_count in expected_counts.items():
        fields = tuple(field for field in baseline_fields if field.recipe == recipe)
        if len(fields) != expected_count:
            _fail(f"baseline extremity recipe {recipe!r} must contain exactly two mirrored fields")
        seen: set[tuple[str, str]] = set()
        for field in fields:
            canonical = source_by_key.get(field.owner.key)
            if canonical is not field.owner or len(field.owner.key[1]) != 1 or field.owner.key[1][0] not in ("left", "right"):
                _fail(f"baseline extremity field {recipe!r} has a non-canonical owner")
            side = field.owner.key[1][0]
            role = field.owner.key[3]
            expected_role = "hand" if recipe in {"paw", "extremity-bridge"} else "foot"
            if role != expected_role or (side, role) in seen:
                _fail(f"baseline extremity field {recipe!r} has an invalid mirrored owner inventory")
            seen.add((side, role))
            paw = paws.get((side, role))
            if paw is None:
                _fail(f"baseline extremity field {recipe!r} has no matching guide")
            where = f"baseline {side} {recipe}"
            if recipe == "paw":
                _require_mass_shape(field.shape, paw.paw_center, paw.paw_radii, where)
            elif recipe == "extremity-bridge":
                if paw.attachment_centerline is None or paw.attachment_radius is None or paw.attachment_kind is None:
                    _fail(f"{where} guide attachment is incomplete")
                _require_path_shape(
                    field.shape, paw.attachment_centerline, (paw.attachment_radius,), where,
                    expected_name=paw.attachment_kind,
                )
            else:
                chain = paw.foot_chain
                if chain is None:
                    _fail(f"{where} guide chain is incomplete")
                if recipe == "metatarsal":
                    _require_path_shape(field.shape, chain.metatarsal_centerline, chain.metatarsal_profile, where)
                elif recipe == "paw-pad":
                    _require_mass_shape(field.shape, chain.pad_center, chain.pad_radii, where)
                else:
                    _require_mass_shape(field.shape, chain.toe_center, chain.toe_radii, where)


def _validate_extremity_sweeps(
    guide: Any,
    limb_sweeps: tuple[_LimbChainSweep, ...],
    extremity_sweeps: tuple[_ExtremitySweep, ...],
) -> None:
    """Fail closed on bilateral hand/foot topology, controls and ownership."""

    expected_names = (
        "left-hand-attachment", "left-hand-paw", "left-foot",
        "right-hand-attachment", "right-hand-paw", "right-foot",
    )
    if tuple(item.name for item in extremity_sweeps) != expected_names:
        _fail("successor extremity sweep order is unstable")
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    paws = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.paw_guides}
    chains = {item.chain_name: item for item in limb_sweeps}
    for side in ("left", "right"):
        hand = paws.get((side, "hand"))
        foot = paws.get((side, "foot"))
        arm = chains.get(f"{side}-forearm-route")
        leg = chains.get(f"{side}-leg")
        if hand is None or foot is None or arm is None or leg is None:
            _fail(f"{side} extremity guide inventory is incomplete")
        attachment, paw, foot_sweep = (item for item in extremity_sweeps if item.side == side)
        if attachment.kind != "hand-attachment" or paw.kind != "hand-paw" or foot_sweep.kind != "foot-chain":
            _fail(f"{side} extremity sweep kinds are unstable")
        if attachment.source_owners != (hand.owner,) or paw.source_owners != (hand.owner,):
            _fail(f"{side} hand sweeps must be hand-owned")
        if any(section.owner is not hand.owner for section in attachment.sweep.sections + paw.sweep.sections):
            _fail(f"{side} hand sweep sections must retain canonical hand ownership")
        if source_by_key.get(hand.owner.key) is not hand.owner or source_by_key.get(foot.owner.key) is not foot.owner:
            _fail(f"{side} extremity owner identity is not canonical")
        if hand.owner.parent != arm.sweep.sections[-1].owner.key or source_by_key.get(hand.owner.parent) is not arm.sweep.sections[-1].owner:
            _fail(f"{side} hand parent must be the same-side successor forearm owner")
        if hand.attachment_centerline is None or hand.attachment_radius is None:
            _fail(f"{side} hand attachment guide is incomplete")
        _require_exact_same_point(attachment.sweep.sections[0].center, hand.attachment_centerline[0], f"{side} hand attachment start")
        _require_exact_same_point(attachment.sweep.sections[-1].center, hand.attachment_centerline[1], f"{side} hand attachment end")
        if any(section.transverse_radii != (float(hand.attachment_radius), float(hand.attachment_radius)) for section in attachment.sweep.sections):
            _fail(f"{side} hand attachment must use the exact guide radius at both stations")
        if len(attachment.sweep.endpoint_caps) != 2 or attachment.sweep.internal_transitions:
            _fail(f"{side} hand attachment must have only two outer endpoint caps")
        if len(paw.sweep.sections) != 4 or len(paw.sweep.endpoint_caps) != 2:
            _fail(f"{side} hand paw must have four stations and two outer caps")
        outward = _vec3(hand.axes.lateral, f"{side}.hand-paw.outward-axis") * (-1.0 if side == "left" else 1.0)
        outward = _unit(outward, f"{side}.hand-paw.outward-axis")
        for index, (section, control) in enumerate(zip(paw.sweep.sections, _HAND_PAW_PROFILE)):
            expected_center = _vec3(hand.paw_center, f"{side}.paw-center") + float(control[0]) * float(hand.paw_radii[0]) * outward
            if not np.array_equal(_vec3(section.center, f"{side}.hand-paw.section[{index}]"), expected_center):
                _fail(f"{side} hand paw section {index} does not follow shared outward offsets")
            expected_radii = (float(hand.paw_radii[1]) * control[1], float(hand.paw_radii[2]) * control[2])
            if section.transverse_radii != expected_radii:
                _fail(f"{side} hand paw section {index} does not retain exact guide profile controls")
            if section.tangent != tuple(float(value) for value in outward):
                _fail(f"{side} hand paw path must point outward, never reverse")
            if section.transverse_axes != (tuple(float(value) for value in hand.axes.up), tuple(float(value) for value in hand.axes.forward)):
                _fail(f"{side} hand paw must use guide up/forward transverse axes")
        hand_center = np.asarray(hand.paw_center, dtype=np.float64).reshape(1, 3)
        if float(_profile_sweep_field(hand_center, paw.sweep)[0]) > 0.0:
            _fail(f"{side} hand paw must contain its exact guide paw center")
        forearm_end = np.asarray(arm.sweep.sections[-1].center, dtype=np.float64).reshape(1, 3)
        if float(_profile_sweep_field(forearm_end, attachment.sweep)[0]) > 0.0:
            _fail(f"{side} hand attachment must overlap its successor forearm endpoint")
        if float(_profile_sweep_field(forearm_end, paw.sweep)[0]) > 0.0:
            _fail(f"{side} hand paw must contain its successor forearm endpoint")

        chain = foot.foot_chain
        if chain is None or foot_sweep.source_owners != (leg.sweep.sections[-1].owner, foot.owner):
            _fail(f"{side} foot sweep must retain shin then foot ownership")
        if foot.owner.parent != leg.sweep.sections[-1].owner.key or source_by_key.get(foot.owner.parent) is not leg.sweep.sections[-1].owner:
            _fail(f"{side} foot parent must be the same-side successor shin owner")
        sections = foot_sweep.sweep.sections
        if tuple(section.name for section in sections) != ("hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe"):
            _fail(f"{side} foot sweep station names are unstable")
        if tuple(section.owner for section in sections) != (leg.sweep.sections[-1].owner, foot.owner, foot.owner, foot.owner, foot.owner):
            _fail(f"{side} foot sweep section ownership is not shin then foot")
        if foot_sweep.sweep.profile_operation != _FOOT_PROFILE_OPERATION:
            _fail(f"{side} foot sweep must use the full-volume authored foot operation")
        if len(sections) - 1 != 4:
            _fail(f"{side} foot sweep must contain exactly four route segments")
        expected_centers = (
            chain.hock_anchor,
            chain.metatarsal_midpoint,
            chain.pad_center,
            chain.pad_toe_midpoint,
            chain.toe_center,
        )
        expected_volume_radii = (
            chain.hock_radii,
            chain.metatarsal_midpoint_radii,
            chain.pad_radii,
            chain.pad_toe_midpoint_radii,
            chain.toe_radii,
        )
        for index, (section, center, volume_radii) in enumerate(zip(sections, expected_centers, expected_volume_radii)):
            if not np.array_equal(_vec3(section.center, f"{side}.foot.section[{index}]"), _vec3(expected_centers[index], f"{side}.foot.expected[{index}]")):
                _fail(f"{side} foot section {index} does not retain exact guide center")
            if section.station_volume_radii != tuple(float(value) for value in volume_radii):
                _fail(f"{side} foot section {index} does not retain exact full guide volume")
            if section.station_volume_axes != tuple(tuple(float(value) for value in getattr(chain.axes, axis)) for axis in ("lateral", "up", "forward")):
                _fail(f"{side} foot section {index} does not retain exact guide volume axes")
        if len(foot_sweep.sweep.endpoint_caps) != 2 or tuple(cap.side for cap in foot_sweep.sweep.endpoint_caps) != ("start", "end"):
            _fail(f"{side} foot sweep must have hock/toe outer caps only")
        if any(cap.center not in {sections[0].center, sections[-1].center} for cap in foot_sweep.sweep.endpoint_caps):
            _fail(f"{side} foot sweep contains a non-outer cap")
        _require_exact_same_point(sections[0].center, leg.sweep.sections[-1].center, f"{side} foot hock/successor leg endpoint")
        _require_exact_same_point(sections[0].center, chain.metatarsal_centerline[0], f"{side} foot hock/metatarsal start")
        if sections[-1].center[2] <= sections[0].center[2] or sections[2].center[2] <= sections[0].center[2]:
            _fail(f"{side} foot stations must preserve hock/contact/forward ordering")


_LIMB_SECTION_NAMES = {
    "upper_arm": ("pre-joint", "joint"),
    "forearm": ("proximal", "distal"),
    "thigh": ("pre-joint", "joint"),
    "shin": ("pre-joint", "joint"),
}


def _limb_inventory(guide: Any) -> dict[tuple[str, str], Any]:
    """Require the exact bilateral eight-guide inventory used by this slice."""

    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    expected = {(side, role) for side in ("left", "right") for role in ("upper_arm", "forearm", "thigh", "shin")}
    inventory: dict[tuple[str, str], Any] = {}
    for item in guide.limb_guides:
        if item.axes != guide.topology.axes:
            _fail(f"limb guide axes do not match topology for {item.owner.key}")
        key = item.owner.key
        canonical_owner = source_by_key.get(key)
        if canonical_owner is None or canonical_owner is not item.owner:
            _fail("successor limb guide owner must be the canonical source descriptor")
        if key[1] not in (("left",), ("right",)) or key[3] not in _LIMB_SECTION_NAMES:
            _fail("successor limb guide owner is not one of the eight source limb AddressKeys")
        slot = (key[1][0], key[3])
        if slot in inventory:
            _fail(f"successor limb guide inventory duplicates {slot}")
        if len(item.sections) != 2:
            _fail(f"successor limb guide {slot} must contain exactly two source sections")
        expected_names = _LIMB_SECTION_NAMES[key[3]]
        if tuple(section.name for section in item.sections) != expected_names:
            _fail(f"successor limb guide {slot} must use the exact ordered sections {expected_names!r}")
        _require_exact_same_point(
            item.sections[0].centerline[1],
            item.sections[1].centerline[0],
            f"successor limb guide {slot} adjacent section endpoint",
        )
        inventory[slot] = item
    if set(inventory) != expected:
        _fail(f"successor limb guide inventory must contain exactly {len(expected)} bilateral guides")
    return inventory


def _make_limb_sweeps(guide: Any) -> tuple[_LimbChainSweep, ...]:
    """Build fixed-order authored arm and bilateral leg profile routes."""

    inventory = _limb_inventory(guide)
    sweeps: list[_LimbChainSweep] = list(_make_arm_profile_sweeps(guide))
    sweeps.extend(_make_leg_profile_sweeps(guide))
    chains = {item.chain_name: item for item in sweeps}
    for side in ("left", "right"):
        thigh = inventory[(side, "thigh")]
        shin = inventory[(side, "shin")]
        if thigh.joint is None or thigh.joint.name != "knee":
            _fail(f"{side} thigh guide must provide one knee station")
        if shin.joint is None or shin.joint.name != "hock":
            _fail(f"{side} shin guide must provide one hock station")
        thigh_start, thigh_mid = thigh.sections[0].centerline
        knee = thigh.joint
        _require_same_point(thigh.sections[1].centerline[1], knee.center, f"{side}.knee source endpoint")
        _require_same_point(shin.sections[0].centerline[0], knee.center, f"{side}.knee shin start")
        shin_mid = shin.sections[0].centerline[1]
        hock = shin.joint
        _require_same_point(shin.sections[1].centerline[1], hock.center, f"{side}.hock source endpoint")
        leg = chains.get(f"{side}-leg")
        if leg is None:
            _fail(f"{side}-leg authored profile route is missing")
        _require_exact_same_point(leg.sweep.sections[0].center, thigh_start, f"{side}.leg authored start")
        _require_exact_same_point(leg.sweep.sections[1].center, thigh_mid, f"{side}.leg authored midpoint")
        _require_exact_same_point(leg.sweep.sections[2].center, knee.center, f"{side}.leg authored knee")
        _require_exact_same_point(leg.sweep.sections[3].center, shin_mid, f"{side}.leg authored shin midpoint")
        _require_exact_same_point(leg.sweep.sections[4].center, hock.center, f"{side}.leg authored hock")
    if tuple(item.chain_name for item in sweeps) != (
        "left-upper-arm-route", "left-forearm-route", "right-upper-arm-route", "right-forearm-route",
        "left-leg", "right-leg",
    ):
        _fail("successor limb chain order is unstable")
    return tuple(sweeps)


def _make_hand_paw_sweep(paw: Any, side: str) -> _ProfileSweep:
    """Build the four-station outward hand profile from exact paw controls."""

    if paw.paw_center is None or paw.paw_radii is None:
        _fail(f"{side} hand paw controls are incomplete")
    axes = paw.axes
    outward = _vec3(axes.lateral, f"{side}.hand-paw.lateral-axis")
    if side == "left":
        outward = -outward
    outward = _unit(outward, f"{side}.hand-paw.outward-axis")
    up = _unit(_vec3(axes.up, f"{side}.hand-paw.up-axis"), f"{side}.hand-paw.up-axis")
    forward = _unit(_vec3(axes.forward, f"{side}.hand-paw.forward-axis"), f"{side}.hand-paw.forward-axis")
    if max(abs(float(np.dot(outward, up))), abs(float(np.dot(outward, forward))), abs(float(np.dot(up, forward)))) > _FRAME_TOLERANCE:
        _fail(f"{side}.hand-paw guide axes must be orthogonal")
    centre = _vec3(paw.paw_center, f"{side}.hand-paw.center")
    paw_radii = _vec3(paw.paw_radii, f"{side}.hand-paw.radii")
    _finite_positive(tuple(float(value) for value in paw_radii), f"{side}.hand-paw.radii")
    axial_radius = float(paw_radii[0])
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for index, (offset, up_scale, forward_scale) in enumerate(_HAND_PAW_PROFILE):
        center = centre + float(offset) * axial_radius * outward
        radii = (float(paw_radii[1]) * float(up_scale), float(paw_radii[2]) * float(forward_scale))
        _finite_positive(radii, f"{side}.hand-paw.section[{index}].radii")
        if index:
            path_length += abs(float(_HAND_PAW_PROFILE[index][0] - _HAND_PAW_PROFILE[index - 1][0])) * axial_radius
        sections.append(_ProfileSection(
            _HAND_PAW_SECTION_NAMES[index], paw.owner,
            tuple(float(value) for value in center),
            tuple(float(value) for value in outward),
            (tuple(float(value) for value in up), tuple(float(value) for value in forward)),
            radii, path_length,
        ))
    ordered = tuple(sections)
    caps = (
        _ProfileEndpointCap(
            "start", ordered[0].center, tuple(-float(value) for value in outward),
            ordered[0].transverse_axes, ordered[0].transverse_radii,
            min(min(ordered[0].transverse_radii), 0.85 * (1.0 - abs(_HAND_PAW_PROFILE[0][0])) * axial_radius),
        ),
        _ProfileEndpointCap(
            "end", ordered[-1].center, ordered[-1].tangent,
            ordered[-1].transverse_axes, ordered[-1].transverse_radii,
            min(min(ordered[-1].transverse_radii), 0.85 * (1.0 - abs(_HAND_PAW_PROFILE[-1][0])) * axial_radius),
        ),
    )
    sweep = _ProfileSweep(ordered, caps)
    _validate_profile_sweep(sweep)
    return sweep


def _make_foot_chain_sweep(paw: Any, side: str, leg: _LimbChainSweep) -> _ExtremitySweep:
    """Build one five-station shin/foot-owned full-volume digitigrade sweep."""

    chain = paw.foot_chain
    if chain is None:
        _fail(f"{side} foot chain controls are incomplete")
    hock = _vec3(chain.hock_anchor, f"{side}.foot.hock")
    leg_end = _vec3(leg.sweep.sections[-1].center, f"{side}.leg.hock-endpoint")
    if not np.array_equal(hock, leg_end):
        _fail(f"{side} foot hock must join the successor leg endpoint exactly")
    _require_exact_same_point(chain.metatarsal_centerline[0], hock, f"{side}.foot.metatarsal start")
    if not np.array_equal(
        _vec3(chain.metatarsal_centerline[1], f"{side}.foot.metatarsal end"),
        _vec3(chain.pad_center, f"{side}.foot.pad center"),
    ):
        _fail(f"{side} foot metatarsal must end at the pad exactly")
    stations = (
        _RouteStation(
            "hock",
            leg.sweep.sections[-1].owner,
            tuple(float(value) for value in hock),
            tuple(float(value) for value in chain.hock_radii),
            _baseline.FOOT_PROFILE_HOCK_SECTION_INDEX,
        ),
        _RouteStation(
            "metatarsal-midpoint",
            paw.owner,
            tuple(float(value) for value in chain.metatarsal_midpoint),
            tuple(float(value) for value in chain.metatarsal_midpoint_radii),
            0,
        ),
        _RouteStation(
            "pad",
            paw.owner,
            tuple(float(value) for value in chain.pad_center),
            tuple(float(value) for value in chain.pad_radii),
            0,
        ),
        _RouteStation(
            "pad-toe-midpoint",
            paw.owner,
            tuple(float(value) for value in chain.pad_toe_midpoint),
            tuple(float(value) for value in chain.pad_toe_midpoint_radii),
            1,
        ),
        _RouteStation(
            "toe",
            paw.owner,
            tuple(float(value) for value in chain.toe_center),
            tuple(float(value) for value in chain.toe_radii),
            1,
        ),
    )
    limb = _make_full_volume_profile_route(
        f"{side}-foot",
        stations,
        chain.axes,
        _FOOT_PROFILE_OPERATION,
        "foot-profile",
    )
    return _ExtremitySweep(f"{side}-foot", side, limb.source_owners, limb.sweep, "foot-chain")


def _make_extremity_sweeps(guide: Any, limb_sweeps: tuple[_LimbChainSweep, ...]) -> tuple[_ExtremitySweep, ...]:
    """Compile identical bilateral hand attachment/paw and foot topologies."""

    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    paw_by_side_role = {(item.owner.key[1][0], item.owner.key[3]): item for item in guide.paw_guides}
    chains = {item.chain_name: item for item in limb_sweeps}
    result: list[_ExtremitySweep] = []
    for side in ("left", "right"):
        hand = paw_by_side_role.get((side, "hand"))
        foot = paw_by_side_role.get((side, "foot"))
        arm = chains.get(f"{side}-forearm-route")
        leg = chains.get(f"{side}-leg")
        if hand is None or foot is None or arm is None or leg is None:
            _fail(f"{side} extremity guide inventory is incomplete")
        if source_by_key.get(hand.owner.key) is not hand.owner or source_by_key.get(foot.owner.key) is not foot.owner:
            _fail(f"{side} extremity guide owner is not canonical")
        if hand.axes != guide.topology.axes or hand.axes != _baseline._FIXED_GUIDE_AXES:
            _fail(f"{side} hand guide axes must match the fixed guide axes")
        if hand.owner.parent != arm.sweep.sections[-1].owner.key or source_by_key.get(hand.owner.parent) is not arm.sweep.sections[-1].owner:
            _fail(f"{side} hand parent must be the successor forearm owner")
        if hand.attachment_centerline is None or hand.attachment_radius is None or hand.attachment_kind is None:
            _fail(f"{side} hand attachment guide is incomplete")
        _require_exact_same_point(hand.attachment_centerline[1], hand.paw_center, f"{side} hand attachment/paw endpoint")
        radius = float(hand.attachment_radius)
        attachment = _make_transition_sweep(
            "hand-attachment", hand.owner, hand.attachment_centerline,
            (radius, radius), hand.axes,
        )
        result.append(_ExtremitySweep(f"{side}-hand-attachment", side, (hand.owner,), attachment, "hand-attachment"))
        paw_sweep = _make_hand_paw_sweep(hand, side)
        result.append(_ExtremitySweep(f"{side}-hand-paw", side, (hand.owner,), paw_sweep, "hand-paw"))
        result.append(_make_foot_chain_sweep(foot, side, leg))
    return tuple(result)


_LIMB_CHAIN_BASELINE_RECIPES = (
    "upper_arm-pre-joint",
    "upper_arm-joint",
    "forearm-proximal",
    "forearm-distal",
    "thigh-pre-joint",
    "thigh-joint",
    "shin-pre-joint",
    "shin-joint",
    "elbow",
    "knee",
    "hock",
)

_EXTREMITY_BASELINE_RECIPES = (
    "paw",
    "extremity-bridge",
    "metatarsal",
    "paw-pad",
    "toe-box",
)

_TAIL_BASELINE_RECIPES = (
    "tail-segment",
    "tail-root-bridge",
    "tail-root-collar",
    "tail-tip-extension",
    "tail-tip-cap",
)


def _validate_tail_baseline_inventory(guide: Any, baseline_fields: tuple[Any, ...]) -> tuple[Any, ...]:
    """Validate and remove the exact six baseline tail fields."""

    tails = tuple(guide.tail_guides)
    if len(tails) != 2 or tuple(item.owner.key[3] for item in tails) != ("tail_root", "tail_tip"):
        _fail("baseline tail inventory requires ordered tail_root and tail_tip guides")
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    root, tip = tails
    if any(source_by_key.get(item.owner.key) is not item.owner for item in tails):
        _fail("baseline tail fields must retain canonical source owners")
    observed: list[Any] = []
    for owner, expected_recipes in (
        (root.owner, ("tail-segment", "tail-root-bridge", "tail-root-collar")),
        (tip.owner, ("tail-segment", "tail-tip-extension", "tail-tip-cap")),
    ):
        fields = tuple(field for field in baseline_fields if field.owner is owner and field.recipe in _TAIL_BASELINE_RECIPES)
        if tuple(field.recipe for field in fields) != expected_recipes:
            _fail(f"baseline {owner.key[3]} tail inventory is not the exact ordered recipe set")
        observed.extend(fields)

    tail_fields = tuple(field for field in baseline_fields if field.recipe in _TAIL_BASELINE_RECIPES)
    if len(tail_fields) != 6 or len(observed) != 6 or {id(field) for field in observed} != {id(field) for field in tail_fields}:
        _fail("baseline tail inventory must contain exactly six fields")
    for field in tail_fields:
        if field.owner.key[3] not in {"tail_root", "tail_tip"} or source_by_key.get(field.owner.key) is not field.owner:
            _fail(f"baseline tail field {field.recipe!r} has a non-canonical owner")

    root_fields = {field.recipe: field for field in observed if field.owner is root.owner}
    tip_fields = {field.recipe: field for field in observed if field.owner is tip.owner}
    _require_path_shape(root_fields["tail-segment"].shape, root.centerline, root.taper, "baseline tail-root segment")
    _require_path_shape(root_fields["tail-root-bridge"].shape, root.root_attachment_centerline, root.root_attachment_taper, "baseline tail-root bridge")  # type: ignore[arg-type]
    _require_mass_shape(root_fields["tail-root-collar"].shape, root.root_collar_center, root.root_collar_radii, "baseline tail-root collar")  # type: ignore[arg-type]
    _require_path_shape(tip_fields["tail-segment"].shape, tip.centerline, tip.taper, "baseline tail-tip segment")
    _require_path_shape(tip_fields["tail-tip-extension"].shape, tip.extension_centerline, tip.extension_taper, "baseline tail-tip extension")  # type: ignore[arg-type]
    _require_mass_shape(tip_fields["tail-tip-cap"].shape, tip.cap_center, tip.cap_radii, "baseline tail-tip cap")  # type: ignore[arg-type]
    if tip.owner.parent != root.owner.key or source_by_key.get(tip.owner.parent) is not root.owner:
        _fail("baseline tail_tip parent must be tail_root")
    return tuple(field for field in baseline_fields if field.recipe not in _TAIL_BASELINE_RECIPES)


def _point_to_segment_distance(point: Any, start: Any, end: Any) -> float:
    point_vector = _vec3(point, "connector overlap point")
    start_vector = _vec3(start, "connector overlap start")
    end_vector = _vec3(end, "connector overlap end")
    axis = end_vector - start_vector
    length_sq = float(np.dot(axis, axis))
    if length_sq <= _DEGENERATE_TOLERANCE:
        return float(np.linalg.norm(point_vector - start_vector))
    t = float(np.clip(np.dot(point_vector - start_vector, axis) / length_sq, 0.0, 1.0))
    return float(np.linalg.norm(point_vector - (start_vector + t * axis)))


def _validate_limb_bridge_inventory(
    guide: Any,
    baseline_fields: tuple[Any, ...],
    limb_sweeps: tuple[_LimbChainSweep, ...],
) -> tuple[Any, ...]:
    """Remove only limb-chain fields and verify every retained bridge joins them."""

    inventory = _limb_inventory(guide)
    source_by_key = {descriptor.key: descriptor for descriptor in guide.source_descriptors}
    removed = tuple(field for field in baseline_fields if field.recipe in _LIMB_CHAIN_BASELINE_RECIPES)
    expected_roles = {
        "upper_arm-pre-joint": "upper_arm", "upper_arm-joint": "upper_arm", "elbow": "upper_arm",
        "forearm-proximal": "forearm", "forearm-distal": "forearm",
        "thigh-pre-joint": "thigh", "thigh-joint": "thigh", "knee": "thigh",
        "shin-pre-joint": "shin", "shin-joint": "shin", "hock": "shin",
    }
    expected_removed = tuple(sorted(
        (side, expected_roles[recipe], recipe)
        for side in ("left", "right")
        for recipe in _LIMB_CHAIN_BASELINE_RECIPES
    ))
    observed_removed: list[tuple[str, str, str]] = []
    for field in removed:
        canonical_owner = source_by_key.get(field.owner.key)
        if canonical_owner is None or canonical_owner is not field.owner:
            _fail(f"baseline limb field {field.recipe!r} must retain its canonical source owner")
        key = field.owner.key
        role = expected_roles.get(field.recipe)
        if role is None or len(key[1]) != 1 or key[1][0] not in ("left", "right"):
            _fail(f"baseline limb field {field.recipe!r} has an invalid side/role owner")
        if key[3] != role:
            _fail(f"baseline limb field {field.recipe!r} has the wrong source owner")
        if (key[1][0], role) not in inventory:
            _fail(f"baseline limb field {field.recipe!r} has a non-guide owner")
        observed_removed.append((key[1][0], role, field.recipe))
    if len(removed) != len(expected_removed) or tuple(sorted(observed_removed)) != expected_removed:
        _fail("baseline limb inventory must contain exactly the mirrored 22 (side, role, recipe) fields")

    expected_bridge_slots = {
        "root-bridge": tuple(sorted((side, role) for side in ("left", "right") for role in ("upper_arm", "thigh"))),
        "hip-transition": tuple(sorted((side, "thigh") for side in ("left", "right"))),
        "metatarsal": tuple(sorted((side, "foot") for side in ("left", "right"))),
        "extremity-bridge": tuple(sorted((side, "hand") for side in ("left", "right"))),
    }
    for recipe, expected_slots in expected_bridge_slots.items():
        fields = tuple(field for field in baseline_fields if field.recipe == recipe)
        observed_slots: list[tuple[str, str]] = []
        for field in fields:
            canonical_owner = source_by_key.get(field.owner.key)
            if canonical_owner is None or canonical_owner is not field.owner:
                _fail(f"baseline {recipe!r} field must retain its canonical source owner")
            key = field.owner.key
            if len(key[1]) != 1 or key[1][0] not in ("left", "right"):
                _fail(f"baseline {recipe!r} field has an invalid side owner")
            observed_slots.append((key[1][0], key[3]))
        if tuple(sorted(observed_slots)) != expected_slots:
            _fail(f"baseline {recipe!r} bridge owner inventory is not the exact bilateral set")

    chains = {item.chain_name: item for item in limb_sweeps}
    for side in ("left", "right"):
        for kind, proximal_role, distal_role, root_role in (
            ("arm", "upper_arm", "forearm", "upper_arm"),
            ("leg", "thigh", "shin", "thigh"),
        ):
            chain = chains[f"{side}-forearm-route"] if kind == "arm" else chains[f"{side}-leg"]
            start = chain.sweep.sections[0].center
            end = chain.sweep.sections[-1].center
            proximal = inventory[(side, proximal_role)]
            distal = inventory[(side, distal_role)]
            root_fields = tuple(field for field in baseline_fields if field.recipe == "root-bridge" and field.owner is proximal.owner)
            if proximal.root_centerline is None or proximal.root_thickness is None or len(root_fields) != 1:
                _fail(f"{side}-{kind} must retain one source-owned root bridge")
            root_shape = root_fields[0].shape
            root_path = _baseline._embed_boundary_connector(
                proximal.root_centerline,
                proximal.root_thickness,
                f"{side}-{kind}.root",
            )
            _require_path_shape(root_shape, root_path, proximal.root_thickness, f"{side}-{kind} root connector")
            if kind != "arm":
                _require_exact_same_point(root_shape.get("to"), start, f"{side}-{kind} root connector")
            if root_role == "thigh":
                hip_fields = tuple(field for field in baseline_fields if field.recipe == "hip-transition" and field.owner is proximal.owner)
                if proximal.hip_centerline is None or proximal.hip_thickness is None or len(hip_fields) != 1:
                    _fail(f"{side}-{kind} must retain one source-owned hip transition")
                hip_path = _baseline._embed_boundary_connector(
                    proximal.hip_centerline,
                    proximal.hip_thickness,
                    f"{side}-{kind}.hip",
                )
                _require_path_shape(hip_fields[0].shape, hip_path, proximal.hip_thickness, f"{side}-{kind} hip transition")

            if kind == "arm":
                hand_guides = tuple(item for item in guide.paw_guides if item.owner.key[1] == (side,) and item.owner.key[3] == "hand")
                if len(hand_guides) != 1:
                    _fail(f"{side}-arm must retain one canonical source hand paw guide")
                hand_paw = hand_guides[0]
                hand_owner = source_by_key.get(hand_paw.owner.key)
                if hand_owner is None or hand_owner is not hand_paw.owner:
                    _fail(f"{side}-arm hand paw guide owner is not canonical")
                if hand_paw.owner.parent != distal.owner.key or source_by_key.get(hand_paw.owner.parent) is not distal.owner:
                    _fail(f"{side}-arm hand paw must retain canonical parent linkage to the distal forearm")
                hand_fields = tuple(field for field in baseline_fields if field.recipe == "extremity-bridge" and field.owner is hand_paw.owner)
                if len(hand_fields) != 1 or hand_paw.attachment_centerline is None or hand_paw.attachment_radius is None:
                    _fail(f"{side}-arm must retain one hand extremity bridge")
                shape = hand_fields[0].shape
                _require_path_shape(
                    shape,
                    hand_paw.attachment_centerline,
                    (hand_paw.attachment_radius,),
                    f"{side}-arm hand extremity bridge",
                    expected_name=hand_paw.attachment_kind or "capsule",
                )
                chain_radius = max(chain.sweep.sections[-1].transverse_radii)
                bridge_radius = max(float(shape.get("r0", 0.0)), float(shape.get("r1", 0.0)))
                if _point_to_segment_distance(end, shape.get("from"), shape.get("to")) > chain_radius + bridge_radius + _FRAME_TOLERANCE:
                    _fail(f"{side}-arm forearm endpoint does not overlap its hand extremity bridge")
            else:
                foot_guides = tuple(item for item in guide.paw_guides if item.owner.key[1] == (side,) and item.owner.key[3] == "foot")
                if len(foot_guides) != 1 or foot_guides[0].foot_chain is None:
                    _fail(f"{side}-leg must retain one source-owned foot metatarsal")
                foot_paw = foot_guides[0]
                foot_fields = tuple(
                    field for field in baseline_fields
                    if field.recipe == "metatarsal" and field.owner is foot_paw.owner
                )
                if len(foot_fields) != 1:
                    _fail(f"{side}-leg must retain one source-owned foot metatarsal")
                if source_by_key.get(foot_paw.owner.key) is not foot_paw.owner:
                    _fail(f"{side}-leg foot guide owner is not canonical")
                if foot_paw.owner.parent != distal.owner.key or source_by_key.get(foot_paw.owner.parent) is not distal.owner:
                    _fail(f"{side}-leg foot must retain canonical parent linkage to the distal shin")
                foot_chain = foot_paw.foot_chain
                _require_path_shape(
                    foot_fields[0].shape,
                    foot_chain.metatarsal_centerline,
                    foot_chain.metatarsal_profile,
                    f"{side}-leg foot metatarsal",
                )
                _require_exact_same_point(foot_fields[0].shape.get("from"), foot_chain.hock_anchor, f"{side}-leg hock/metatarsal connector")
                _require_exact_same_point(foot_chain.hock_anchor, end, f"{side}-leg hock/foot guide connector")

            # Ensure the distal source guide actually supplies the endpoint
            # consumed by this chain; this catches accidental field/guide drift.
            if kind == "arm":
                _require_exact_same_point(distal.sections[1].centerline[1], end, f"{side}-arm distal endpoint")
            else:
                _require_exact_same_point(distal.joint.center if distal.joint is not None else None, end, f"{side}-leg hock endpoint")
    bridge = tuple(field for field in baseline_fields if field.recipe not in _LIMB_CHAIN_BASELINE_RECIPES)
    if len(bridge) != len(baseline_fields) - 22:
        _fail("baseline bridge selection removed more or fewer than the 22 limb fields")
    return bridge


def compile_successor_region(guide: Any, baseline_fields: tuple[Any, ...] | None = None) -> SuccessorRegion:
    """Compile the guide into the successor regional profile-sweep consumer.

    The torso cage, one authored shoulder envelope per side, two authored head/neck route fields,
    four bilateral limb chains, ten bilateral hand/foot fields, and six tail
    fields are replaced. Every other baseline field is carried as a named
    temporary bridge: two thigh-root bridges and two hip transitions.
    """

    _baseline._validate_hybrid_guide(guide)
    head_neck_profile = _validate_authored_head_neck_guide(guide)
    leg_profile = _validate_leg_profile_guide(guide)
    if baseline_fields is None:
        baseline_fields = _baseline._compile_hybrid_guide(guide)
    replaced = (
        "torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
        "deltoid-sweep-1", *_LIMB_CHAIN_BASELINE_RECIPES, *_EXTREMITY_BASELINE_RECIPES, *_TAIL_BASELINE_RECIPES,
    )
    torso_fields = tuple(field for field in baseline_fields if field.recipe == "torso-cage")
    expected_torso_owner = guide.torso_cage.torso_owner
    if len(torso_fields) != 1 or torso_fields[0].owner is not expected_torso_owner:
        _fail("baseline inventory must contain exactly one torso-cage field owned by the guide torso")
    deltoid_fields = tuple(field for field in baseline_fields if field.recipe == "deltoid-sweep-1")
    expected_deltoid_owners = tuple(side.owner for side in guide.shoulder_frame.sides)
    if len(deltoid_fields) != 2 or {id(field.owner) for field in deltoid_fields} != {id(owner) for owner in expected_deltoid_owners}:
        _fail("baseline inventory must contain exactly two left/right deltoid-sweep-1 fields")
    head = guide.head_guide
    head_recipe_fields = tuple(field for field in baseline_fields if field.recipe in {"cranium", "muzzle", "head-base-bridge"})
    if (
        len(head_recipe_fields) != 3
        or any(field.owner is not head.head_owner for field in head_recipe_fields)
        or {field.recipe for field in head_recipe_fields} != {"cranium", "muzzle", "head-base-bridge"}
    ):
        _fail("baseline inventory must contain exactly the head-owned cranium/muzzle/bridge fields")
    neck_recipe_fields = tuple(field for field in baseline_fields if field.recipe in {"tapered-neck", "neck-collar"})
    if (
        len(neck_recipe_fields) != 2
        or any(field.owner is not head.neck_owner for field in neck_recipe_fields)
        or {field.recipe for field in neck_recipe_fields} != {"tapered-neck", "neck-collar"}
    ):
        _fail("baseline inventory must contain exactly the neck-owned transition/collar fields")
    limb_sweeps = _make_limb_sweeps(guide)
    bridge_before_extremities = _validate_limb_bridge_inventory(guide, baseline_fields, limb_sweeps)
    _validate_extremity_baseline_fields(guide, baseline_fields)
    bridge_before_tail = _validate_tail_baseline_inventory(guide, bridge_before_extremities)
    extremity_sweeps = _make_extremity_sweeps(guide, limb_sweeps)
    foot_profile = _validate_foot_profile_guide(guide)
    _validate_extremity_sweeps(guide, limb_sweeps, extremity_sweeps)
    loft = _make_loft(guide)
    shoulder_sweeps = _make_shoulder_sweeps(guide, loft)
    upper_arm_owner_ids = {id(side.owner) for side in guide.shoulder_frame.sides}
    replaced_fields = tuple(
        field for field in baseline_fields
        if field.recipe in replaced
        or (field.recipe == "root-bridge" and id(field.owner) in upper_arm_owner_ids)
    )
    bridge = tuple(
        field for field in bridge_before_tail
        if field.recipe not in {"torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar", "deltoid-sweep-1", *_EXTREMITY_BASELINE_RECIPES}
        and not (field.recipe == "root-bridge" and id(field.owner) in upper_arm_owner_ids)
    )
    if len(bridge) + len(replaced_fields) != len(baseline_fields):
        _fail("baseline bridge selection lost fields")
    if len(bridge) != 4 or tuple(field.recipe for field in bridge).count("root-bridge") != 2 or tuple(field.recipe for field in bridge).count("hip-transition") != 2:
        _fail("successor bridge must contain exactly two thigh root bridges and two hip transitions")
    head_neck_sweeps = _make_head_neck_sweeps(guide)
    tail_elements = _make_tail_elements(guide, loft)
    source_keys = {descriptor.key for descriptor in guide.source_descriptors}
    if any(sweep.owner.key not in source_keys for sweep in head_neck_sweeps):
        _fail("successor head/neck sweep owner is not an existing source AddressKey")
    return SuccessorRegion(
        consumer_id=CONSUMER_ID,
        region_id=SUCCESSOR_REGION_ID,
        loft=loft,
        shoulder_sweeps=shoulder_sweeps,
        bridge_fields=bridge,
        replaced_baseline_recipes=replaced,
        source_owners=(guide.torso_cage.torso_owner,) + tuple(side.owner for side in guide.shoulder_frame.sides) + (head.head_owner, head.neck_owner),
        head_neck_sweeps=head_neck_sweeps,
        head_neck_profile=head_neck_profile,
        leg_profile=leg_profile,
        foot_profile=foot_profile,
        limb_sweeps=limb_sweeps,
        extremity_sweeps=extremity_sweeps,
        tail_elements=tail_elements,
    )


def _interpolated_span_frame(left: _ProfileSection, right: _ProfileSection, t: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate a span frame without referring to a world-up coordinate."""

    left_tangent = _vec3(left.tangent, "profile span left tangent")
    right_tangent = _vec3(right.tangent, "profile span right tangent")
    left_first = _vec3(left.transverse_axes[0], "profile span left transverse axis")
    right_first = _vec3(right.transverse_axes[0], "profile span right transverse axis")
    left_second = _vec3(left.transverse_axes[1], "profile span left transverse axis")
    right_second = _vec3(right.transverse_axes[1], "profile span right transverse axis")
    if float(np.dot(left_first, right_first)) < 0.0 and float(np.dot(left_second, right_second)) < 0.0:
        # A paired sign flip describes the same transverse frame, but direct
        # linear interpolation would cancel both axes at the midpoint.  Align
        # the pair to the left frame before interpolation; flipping both
        # preserves the frame orientation.
        right_first = -right_first
        right_second = -right_second
    tangent = (1.0 - t)[..., None] * left_tangent + t[..., None] * right_tangent
    tangent_norm = np.linalg.norm(tangent, axis=-1)
    tangent = np.divide(tangent, tangent_norm[..., None], out=np.zeros_like(tangent), where=tangent_norm[..., None] > _DEGENERATE_TOLERANCE)
    first_raw = (1.0 - t)[..., None] * left_first + t[..., None] * right_first
    first_projected = first_raw - np.sum(first_raw * tangent, axis=-1)[..., None] * tangent
    first_norm = np.linalg.norm(first_projected, axis=-1)
    second_raw = (1.0 - t)[..., None] * left_second + t[..., None] * right_second
    second_projected = second_raw - np.sum(second_raw * tangent, axis=-1)[..., None] * tangent
    second_norm = np.linalg.norm(second_projected, axis=-1)
    use_second = first_norm <= _DEGENERATE_TOLERANCE
    first_projected = np.where(use_second[..., None], second_projected, first_projected)
    first_norm = np.where(use_second, second_norm, first_norm)
    if np.any(first_norm <= _DEGENERATE_TOLERANCE) or np.any(tangent_norm <= _DEGENERATE_TOLERANCE):
        _fail("profile span frame interpolation became degenerate")
    first = first_projected / first_norm[..., None]
    second = np.cross(first, tangent)
    second_norm = np.linalg.norm(second, axis=-1)
    if np.any(second_norm <= _DEGENERATE_TOLERANCE):
        _fail("profile span transverse frame became degenerate")
    second = second / second_norm[..., None]
    orientation = np.where(np.sum(second * second_raw, axis=-1) < 0.0, -1.0, 1.0)
    first *= orientation[..., None]
    second *= orientation[..., None]
    return tangent, first, second


def _shape_preserving_slopes(path: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Compute local monotone-cubic slopes without inventing profile extrema."""

    path = np.asarray(path, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if path.ndim != 1 or values.shape != (path.size, 3) or path.size < 2:
        _fail("torso profile interpolation controls have invalid dimensions")
    if not np.all(np.isfinite(path)) or not np.all(np.isfinite(values)) or np.any(np.diff(path) <= 0.0):
        _fail("torso profile interpolation controls are invalid")
    spacing = np.diff(path)
    secants = np.diff(values, axis=0) / spacing[:, None]
    if not np.all(np.isfinite(secants)):
        _fail("torso profile interpolation secants are not finite")
    slopes = np.zeros_like(values)
    if path.size == 2:
        slopes[0] = secants[0]
        slopes[1] = secants[0]
        return slopes
    for index in range(1, path.size - 1):
        previous = secants[index - 1]
        following = secants[index]
        if np.all(previous * following > 0.0):
            left_weight = 2.0 * spacing[index] + spacing[index - 1]
            right_weight = spacing[index] + 2.0 * spacing[index - 1]
            slopes[index] = (left_weight + right_weight) / (left_weight / previous + right_weight / following)
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
        _fail("torso profile interpolation slopes are not finite")
    return slopes


def _shape_preserving_sample(path: np.ndarray, values: np.ndarray, slopes: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Evaluate the bounded shape-preserving interpolation at profile arc positions."""

    index = np.searchsorted(path, query, side="right") - 1
    index = np.clip(index, 0, path.size - 2)
    left_path = path[index]
    width = path[index + 1] - left_path
    t = np.divide(query - left_path, width, out=np.zeros_like(query), where=width > 0.0)
    left = values[index]
    right = values[index + 1]
    left_slope = slopes[index]
    right_slope = slopes[index + 1]
    h00 = 2.0 * t**3 - 3.0 * t**2 + 1.0
    h10 = t**3 - 2.0 * t**2 + t
    h01 = -2.0 * t**3 + 3.0 * t**2
    h11 = t**3 - t**2
    return h00[..., None] * left + h10[..., None] * width[..., None] * left_slope + h01[..., None] * right + h11[..., None] * width[..., None] * right_slope


def _torso_superellipse_field(
    lateral_distance: np.ndarray,
    forward_distance: np.ndarray,
    radii: np.ndarray,
    axial_distance: np.ndarray | None = None,
    axial_radius: float | None = None,
) -> np.ndarray:
    """Evaluate one rounded, asymmetric cardinal profile or endpoint cap."""

    lateral_radius = radii[..., 0]
    anterior_radius = radii[..., 1]
    posterior_radius = radii[..., 2]
    forward_radius = np.where(forward_distance >= 0.0, anterior_radius, posterior_radius)
    lateral_term = np.abs(lateral_distance / lateral_radius) ** TORSO_SUPERELLIPSE_EXPONENT
    forward_term = np.abs(forward_distance / forward_radius) ** TORSO_SUPERELLIPSE_EXPONENT
    terms = [lateral_term, forward_term]
    if axial_distance is not None and axial_radius is not None:
        terms.append(np.abs(axial_distance / axial_radius) ** TORSO_SUPERELLIPSE_EXPONENT)
    radial = np.power(np.sum(np.stack(terms, axis=0), axis=0), 1.0 / TORSO_SUPERELLIPSE_EXPONENT) - 1.0
    scale = np.minimum(lateral_radius, np.minimum(anterior_radius, posterior_radius))
    if axial_radius is not None:
        scale = np.minimum(scale, axial_radius)
    return radial * scale


def _torso_span_field(
    points: np.ndarray,
    left: _ProfileSection,
    right: _ProfileSection,
    path: np.ndarray,
    radii: np.ndarray,
    slopes: np.ndarray,
) -> np.ndarray:
    start = _vec3(left.center, "torso profile span start")
    end = _vec3(right.center, "torso profile span end")
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    if length_sq <= _DEGENERATE_TOLERANCE:
        _fail("torso profile span has degenerate centres")
    raw_t = np.sum((points - start) * axis, axis=-1) / length_sq
    t = np.clip(raw_t, 0.0, 1.0)
    centre = start + t[..., None] * axis
    if left.tangent == right.tangent and left.transverse_axes == right.transverse_axes:
        first = np.broadcast_to(_vec3(left.transverse_axes[0], "torso profile span transverse axis"), points.shape)
        second = np.broadcast_to(_vec3(left.transverse_axes[1], "torso profile span transverse axis"), points.shape)
    else:
        _, first, second = _interpolated_span_frame(left, right, t)
    span_length = math.sqrt(length_sq)
    query_path = float(left.path_length) + t * span_length
    local_radii = _shape_preserving_sample(path, radii, slopes, query_path)
    offset = points - centre
    lateral_distance = np.sum(offset * first, axis=-1)
    forward_distance = np.sum(offset * second, axis=-1)
    radial = _torso_superellipse_field(lateral_distance, forward_distance, local_radii)
    return np.where((raw_t >= 0.0) & (raw_t <= 1.0), radial, np.inf)


def _torso_cap_field(points: np.ndarray, cap: _ProfileEndpointCap, cardinal_radii: tuple[float, float, float]) -> np.ndarray:
    center = _vec3(cap.center, "torso profile cap center")
    outward = _vec3(cap.outward_tangent, "torso profile cap outward tangent")
    first = _vec3(cap.transverse_axes[0], "torso profile cap transverse axis")
    second = _vec3(cap.transverse_axes[1], "torso profile cap transverse axis")
    offset = points - center
    axial_distance = np.sum(offset * outward, axis=-1)
    lateral_distance = np.sum(offset * first, axis=-1)
    forward_distance = np.sum(offset * second, axis=-1)
    return _torso_superellipse_field(
        lateral_distance,
        forward_distance,
        np.broadcast_to(np.asarray(cardinal_radii, dtype=np.float64), points.shape[:-1] + (3,)),
        axial_distance,
        float(cap.axial_radius),
    )


def _torso_profile_sweep_field(points: np.ndarray, sweep: _ProfileSweep) -> np.ndarray:
    """Evaluate one finite seven-section asymmetric torso field."""

    _validate_profile_sweep(sweep)
    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 3 or not np.all(np.isfinite(points)):
        _fail("torso profile query points must be finite three-vectors")
    cardinal = np.asarray([section.cardinal_radii for section in sweep.sections], dtype=np.float64)
    path = np.asarray([section.path_length for section in sweep.sections], dtype=np.float64)
    slopes = _shape_preserving_slopes(path, cardinal)
    values = [
        *(_torso_span_field(points, left, right, path, cardinal, slopes) for left, right in zip(sweep.sections, sweep.sections[1:])),
        *(_torso_cap_field(points, cap, tuple(float(value) for value in cardinal[index])) for index, cap in ((0, sweep.endpoint_caps[0]), (-1, sweep.endpoint_caps[1]))),
    ]
    return np.min(np.stack(values, axis=0), axis=0)


def _profile_span_field(points: np.ndarray, left: _ProfileSection, right: _ProfileSection) -> np.ndarray:
    start = _vec3(left.center, "profile span start")
    end = _vec3(right.center, "profile span end")
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    if length_sq <= _DEGENERATE_TOLERANCE:
        _fail("profile span has degenerate centres")
    raw_t = np.sum((points - start) * axis, axis=-1) / length_sq
    t = np.clip(raw_t, 0.0, 1.0)
    centre = start + t[..., None] * axis
    if left.tangent == right.tangent and left.transverse_axes == right.transverse_axes:
        # The compiled torso currently uses one fixed prototype frame.  Keep
        # the generic interpolation path for bent/rotated profiles, but avoid
        # allocating several large frame arrays for the common fixed-frame
        # case during mesh orientation and diagnostics.
        first = np.broadcast_to(_vec3(left.transverse_axes[0], "profile span transverse axis"), points.shape)
        second = np.broadcast_to(_vec3(left.transverse_axes[1], "profile span transverse axis"), points.shape)
    else:
        _, first, second = _interpolated_span_frame(left, right, t)
    radii = (1.0 - t)[..., None] * np.asarray(left.transverse_radii, dtype=np.float64) + t[..., None] * np.asarray(right.transverse_radii, dtype=np.float64)
    offset = points - centre
    first_distance = np.sum(offset * first, axis=-1) / radii[..., 0]
    second_distance = np.sum(offset * second, axis=-1) / radii[..., 1]
    radial = (np.sqrt(first_distance**2 + second_distance**2) - 1.0) * np.minimum(radii[..., 0], radii[..., 1])
    # Spans are finite primitives.  Internal station closure belongs to the
    # neighbouring span's shared endpoint, not to a synthetic cap on every
    # span; only the two declared sweep endpoint caps close the full profile.
    return np.where((raw_t >= 0.0) & (raw_t <= 1.0), radial, np.inf)


def _profile_cap_field(points: np.ndarray, cap: _ProfileEndpointCap) -> np.ndarray:
    center = _vec3(cap.center, "profile cap center")
    outward = _vec3(cap.outward_tangent, "profile cap outward tangent")
    first = _vec3(cap.transverse_axes[0], "profile cap transverse axis")
    second = _vec3(cap.transverse_axes[1], "profile cap transverse axis")
    offset = points - center
    axial = np.sum(offset * outward, axis=-1) / float(cap.axial_radius)
    transverse_first = np.sum(offset * first, axis=-1) / float(cap.transverse_radii[0])
    transverse_second = np.sum(offset * second, axis=-1) / float(cap.transverse_radii[1])
    return (np.sqrt(axial**2 + transverse_first**2 + transverse_second**2) - 1.0) * min(*cap.transverse_radii, cap.axial_radius)


def _profile_station_volume_field(points: np.ndarray, section: _ProfileSection) -> np.ndarray:
    """Evaluate a full three-radius station volume when one is authored."""

    if section.station_volume_axes is not None or section.station_volume_radii is not None:
        if section.station_volume_axes is None or section.station_volume_radii is None:
            _fail(f"profile station {section.name!r} has incomplete station-volume controls")
        if len(section.station_volume_axes) != 3 or len(section.station_volume_radii) != 3:
            _fail(f"profile station {section.name!r} station-volume controls must have three axes")
        center = _vec3(section.center, f"profile station {section.name}.center")
        axes = tuple(
            _vec3(axis, f"profile station {section.name}.station-volume-axis[{index}]")
            for index, axis in enumerate(section.station_volume_axes)
        )
        radii = tuple(float(value) for value in section.station_volume_radii)
        _finite_positive(radii, f"profile station {section.name}.station-volume-radii")
        offset = points - center
        distances = tuple(
            np.sum(offset * axis, axis=-1) / radius
            for axis, radius in zip(axes, radii)
        )
        return (np.sqrt(sum(distance**2 for distance in distances)) - 1.0) * min(radii)

    if section.tangent_radius is None:
        _fail(f"profile station {section.name!r} is missing its tangent-axis radius")
    center = _vec3(section.center, f"profile station {section.name}.center")
    tangent = _vec3(section.tangent, f"profile station {section.name}.tangent")
    first = _vec3(section.transverse_axes[0], f"profile station {section.name}.transverse-first")
    second = _vec3(section.transverse_axes[1], f"profile station {section.name}.transverse-second")
    offset = points - center
    axial = np.sum(offset * tangent, axis=-1) / float(section.tangent_radius)
    transverse_first = np.sum(offset * first, axis=-1) / float(section.transverse_radii[0])
    transverse_second = np.sum(offset * second, axis=-1) / float(section.transverse_radii[1])
    return (np.sqrt(axial**2 + transverse_first**2 + transverse_second**2) - 1.0) * min(
        *section.transverse_radii, float(section.tangent_radius)
    )


def _profile_transition_field(points: np.ndarray, transition: _ProfileJointTransition) -> np.ndarray:
    """Evaluate a bounded source-section-owned internal bend transition."""

    center = _vec3(transition.center, "profile transition center")
    tangent = _vec3(transition.tangent, "profile transition tangent")
    first = _vec3(transition.transverse_axes[0], "profile transition transverse axis")
    second = _vec3(transition.transverse_axes[1], "profile transition transverse axis")
    offset = points - center
    axial = np.sum(offset * tangent, axis=-1) / transition.axial_radius
    transverse_first = np.sum(offset * first, axis=-1) / transition.transverse_radii[0]
    transverse_second = np.sum(offset * second, axis=-1) / transition.transverse_radii[1]
    return (np.sqrt(axial**2 + transverse_first**2 + transverse_second**2) - 1.0) * min(*transition.transverse_radii, transition.axial_radius)


def _profile_sweep_field(points: np.ndarray, sweep: _ProfileSweep) -> np.ndarray:
    """Evaluate finite tapered spans and oriented endpoint caps by minimum."""

    if sweep.profile_operation == TORSO_PROFILE_OPERATION:
        return _torso_profile_sweep_field(points, sweep)
    _validate_profile_sweep(sweep)
    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 3 or not np.all(np.isfinite(points)):
        _fail("profile sweep query points must be finite three-vectors")
    values = [
        *(_profile_span_field(points, left, right) for left, right in zip(sweep.sections, sweep.sections[1:])),
        *(_profile_transition_field(points, transition) for transition in sweep.internal_transitions),
        *(_profile_cap_field(points, cap) for cap in sweep.endpoint_caps),
        *(
            _profile_station_volume_field(points, section)
            for section in sweep.sections
            if section.tangent_radius is not None or section.station_volume_radii is not None
        ),
    ]
    return np.min(np.stack(values, axis=0), axis=0)


def _shoulder_span_field(
    points: np.ndarray,
    left: _ProfileSection,
    right: _ProfileSection,
    preferred_up: np.ndarray,
    preferred_forward: np.ndarray,
) -> np.ndarray:
    """Evaluate one bounded shoulder span in its actual straight-span frame.

    Generic profile sweeps interpolate station tangents to smooth ordinary
    bends.  A shoulder branch can double back locally between an authored
    surface profile and an embedded arm socket; using the interpolated tangent
    there leaves a radial direction unbounded and creates remote satellite
    lobes.  This bounded consumer instead projects the guide-relative up and
    forward axes around each actual finite span.
    """

    start = _vec3(left.center, "shoulder span start")
    end = _vec3(right.center, "shoulder span end")
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    if length_sq <= _DEGENERATE_TOLERANCE:
        _fail("shoulder span has degenerate centres")
    raw_t = np.sum((points - start) * axis, axis=-1) / length_sq
    t = np.clip(raw_t, 0.0, 1.0)
    center = start + t[..., None] * axis
    _, first, second = _frame_from_tangent(
        axis,
        preferred_up,
        preferred_forward,
        "shoulder finite span",
    )
    radii = (
        (1.0 - t)[..., None] * np.asarray(left.transverse_radii, dtype=np.float64)
        + t[..., None] * np.asarray(right.transverse_radii, dtype=np.float64)
    )
    offset = points - center
    first_distance = np.sum(offset * first, axis=-1) / radii[..., 0]
    second_distance = np.sum(offset * second, axis=-1) / radii[..., 1]
    radial = (
        np.sqrt(first_distance**2 + second_distance**2) - 1.0
    ) * np.minimum(radii[..., 0], radii[..., 1])
    return np.where((raw_t >= 0.0) & (raw_t <= 1.0), radial, np.inf)


def _shoulder_sweep_field(
    points: np.ndarray,
    shoulder: _ShoulderEnvelopeSweep,
) -> np.ndarray:
    """Evaluate one five-section authored shoulder branch without ghost lobes."""

    sweep = shoulder.sweep
    _validate_profile_sweep(sweep)
    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 3 or not np.all(np.isfinite(points)):
        _fail("shoulder sweep query points must be finite three-vectors")
    preferred_up = _vec3(shoulder.preferred_up, "shoulder preferred up")
    preferred_forward = _vec3(
        shoulder.preferred_forward,
        "shoulder preferred forward",
    )
    values = [
        *(
            _shoulder_span_field(
                points,
                left,
                right,
                preferred_up,
                preferred_forward,
            )
            for left, right in zip(sweep.sections, sweep.sections[1:])
        ),
        *(
            _profile_transition_field(points, transition)
            for transition in sweep.internal_transitions
        ),
        *(_profile_cap_field(points, cap) for cap in sweep.endpoint_caps),
    ]
    return np.min(np.stack(values, axis=0), axis=0)


def _loft_field(points: np.ndarray, loft: _ProfileSweep) -> np.ndarray:
    """Compatibility name for the frame-aware successor profile evaluator."""

    return _profile_sweep_field(points, loft)


def _loft_section_indices(points: np.ndarray, loft: _ProfileSweep) -> np.ndarray:
    """Choose the nearest source-owned section, retaining lower-index ties."""

    points = np.asarray(points, dtype=np.float64)
    centers = loft.centers
    distances = np.sum((points[..., None, :] - centers) ** 2, axis=-1)
    # np.argmin returns the first equal minimum, which is the required lower
    # source-section index at an exact midpoint tie.
    return np.argmin(distances, axis=-1)


def _loft_owner_keys(points: np.ndarray, loft: _ProfileSweep) -> tuple[tuple[str, tuple[str, ...], str, str], ...]:
    """Return source AddressKeys without inventing a profile semantic node."""

    return tuple(loft.owners[int(index)].key for index in _loft_section_indices(points, loft).reshape(-1))


def _successor_region_field(points: np.ndarray, region: SuccessorRegion, smooth_k: float) -> np.ndarray:
    values = [_loft_field(points, region.loft)]
    values.extend(_profile_sweep_field(points, item.sweep) for item in region.head_neck_sweeps)
    values.extend(_profile_sweep_field(points, item.sweep) for item in region.limb_sweeps)
    values.extend(_profile_sweep_field(points, item.sweep) for item in region.extremity_sweeps)
    values.extend(_profile_sweep_field(points, item.sweep) for item in region.tail_elements)
    values.extend(_shoulder_sweep_field(points, item) for item in region.shoulder_sweeps)
    return _baseline._smooth_union(values, smooth_k)


def _arm_profile_lineage_json(lineage: Any) -> dict[str, Any]:
    return {
        "base": int(lineage.base),
        "factor": int(lineage.factor),
        "scaled": int(lineage.scaled),
        "reference": {
            "owner": _baseline._address_json(lineage.reference[0]),
            "role": lineage.reference[1],
            "index": int(lineage.reference_index),
        },
        "provenance": dict(lineage.provenance),
        "consumed_section": lineage.consumed_section,
    }


def _arm_profile_station_json(station: Any) -> dict[str, Any]:
    return {
        "name": station.name,
        "section_index": int(station.section_index),
        "source_section_index": int(station.source_section_index),
        "owner": _baseline._address_json(station.owner.key),
        "center": [float(value) for value in station.center],
        "radii": {
            "lateral": float(station.radii[0]),
            "up": float(station.radii[1]),
            "forward": float(station.radii[2]),
        },
        "lineage": {
            "lateral": _arm_profile_lineage_json(station.lateral_lineage),
            "up": _arm_profile_lineage_json(station.up_lineage),
            "forward": _arm_profile_lineage_json(station.forward_lineage),
        },
        "consumption": "skin-driving; elbow seam owned by upper_arm station" if station.name == "elbow" else "skin-driving",
    }


def _arm_profile_metadata(region: SuccessorRegion) -> dict[str, Any]:
    routes = region.arm_sweeps
    return {
        "format": _baseline.AUTHORED_ARM_PROFILE_FORMAT,
        "source": "authored_arm_profile",
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "operation": _ARM_PROFILE_OPERATION,
        "topology": "two-routes-per-side-shared-upper-arm-elbow-seam",
        "route_order": [item.chain_name for item in routes],
        "routes": [
            {
                "name": item.chain_name,
                "side": item.chain_name.split("-", 1)[0],
                "route": "upper-arm" if "upper-arm-route" in item.chain_name else "forearm",
                "station_names": list(item.section_names),
                "source_section_indices": [int(station.source_section_index) for station in item.source_stations],
                "owner_keys": [_baseline._address_json(section.owner.key) for section in item.source_stations],
                "station_count": item.sections_consumed,
            }
            for item in routes
        ],
        "stations": [
            {
                "side": side,
                "sections": [_arm_profile_station_json(item.source_stations[0]) for item in routes if item.chain_name == f"{side}-upper-arm-route"]
                + [_arm_profile_station_json(item.source_stations[1]) for item in routes if item.chain_name == f"{side}-upper-arm-route"]
                + [_arm_profile_station_json(item.source_stations[2]) for item in routes if item.chain_name == f"{side}-upper-arm-route"]
                + [_arm_profile_station_json(item.source_stations[1]) for item in routes if item.chain_name == f"{side}-forearm-route"]
                + [_arm_profile_station_json(item.source_stations[2]) for item in routes if item.chain_name == f"{side}-forearm-route"]
            }
            for side in ("left", "right")
        ],
        "elbow_ownership": "upper_arm",
    }


def _leg_profile_lineage_json(lineage: Any) -> dict[str, Any]:
    return {
        "base": int(lineage.base),
        "factor": int(lineage.factor),
        "scaled": int(lineage.scaled),
        "reference": {
            "owner": _baseline._address_json(lineage.reference[0]),
            "role": lineage.reference[1],
            "index": int(lineage.reference_index),
        },
        "provenance": dict(lineage.provenance),
        "consumed_section": lineage.consumed_section,
    }


def _leg_profile_station_json(station: Any) -> dict[str, Any]:
    if station.name == "knee":
        consumption = "skin-driving; knee seam owned by thigh station"
    elif station.name == "hock-endpoint":
        consumption = "skin-driving; hock endpoint owned by shin station"
    else:
        consumption = "skin-driving"
    return {
        "name": station.name,
        "section_index": int(station.section_index),
        "source_section_index": int(station.source_section_index),
        "frame_index": int(station.frame_index),
        "landmark_index": int(station.landmark_index),
        "owner": _baseline._address_json(station.owner.key),
        "center": [float(value) for value in station.center],
        "radii": {
            "lateral": float(station.radii[0]),
            "up": float(station.radii[1]),
            "forward": float(station.radii[2]),
        },
        "lineage": {
            "lateral": _leg_profile_lineage_json(station.lateral_lineage),
            "up": _leg_profile_lineage_json(station.up_lineage),
            "forward": _leg_profile_lineage_json(station.forward_lineage),
        },
        "profile_provenance": dict(station.profile_provenance),
        "variant_provenance": dict(station.variant_provenance),
        "consumption": consumption,
    }


def _leg_profile_metadata(region: SuccessorRegion) -> dict[str, Any]:
    routes = region.leg_sweeps
    if tuple(item.chain_name for item in routes) != ("left-leg", "right-leg"):
        _fail("successor leg profile metadata route order is unstable")
    if any(item.route_kind != "leg-profile" for item in routes):
        _fail("successor leg profile metadata contains a non-authored route")
    route_by_side = {item.chain_name.split("-", 1)[0]: item for item in routes}
    side_metadata = []
    for side in ("left", "right"):
        route = route_by_side[side]
        stations = tuple(route.source_stations)
        if len(stations) != 5:
            _fail(f"{side} leg profile metadata has the wrong station count")
        side_metadata.append({
            "side": side,
            "route": route.chain_name,
            "route_kind": route.route_kind,
            "station_count": len(stations),
            "source_section_indices": [int(station.source_section_index) for station in stations],
            "owner_keys": [_baseline._address_json(station.owner.key) for station in stations],
            "stations": [_leg_profile_station_json(station) for station in stations],
        })
    first_station = routes[0].source_stations[0]
    return {
        "format": _baseline.AUTHORED_LEG_PROFILE_FORMAT,
        "source": "authored_leg_profile",
        "source_format": _baseline.SOURCE_FORMAT,
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "operation": _LEG_PROFILE_OPERATION,
        "topology": "one-five-station-route-per-side-thigh-knee-shin-hock",
        "route_order": [item.chain_name for item in routes],
        "route_kinds": [item.route_kind for item in routes],
        "section_names": list(_baseline.LEG_PROFILE_SECTION_NAMES),
        "owner_roles": list(_baseline.LEG_PROFILE_OWNER_ROLES),
        "knee_seam": {"name": "knee", "index": 2, "owner_role": "thigh"},
        "hock_endpoint": {"name": "hock-endpoint", "index": 4, "owner_role": "shin"},
        "station_count": 10,
        "radius_count": 30,
        "provenance": dict(first_station.profile_provenance),
        "variant_provenance": dict(first_station.variant_provenance),
        "sides": side_metadata,
    }


def _foot_profile_lineage_json(lineage: Any) -> dict[str, Any]:
    return {
        "base": int(lineage.base),
        "factor": int(lineage.factor),
        "scaled": int(lineage.scaled),
        "reference": {
            "owner": _baseline._address_json(lineage.reference[0]),
            "role": lineage.reference[1],
            "index": int(lineage.reference_index),
        },
        "provenance": dict(lineage.provenance),
        "consumed_section": lineage.consumed_section,
    }


def _foot_profile_metadata(region: SuccessorRegion) -> dict[str, Any]:
    """Serialize the exact authored and derived five-station foot routes."""

    profile = region.foot_profile
    if profile is None:
        _fail("successor region is missing the consumed authored foot profile")
    if tuple(item.name for item in region.foot_sweeps) != ("left-foot", "right-foot"):
        _fail("successor foot profile metadata route order is unstable")
    leg_by_side = {item.chain_name.split("-", 1)[0]: item for item in region.leg_sweeps}
    profile_by_side = {item.side: item for item in profile.sides}
    side_metadata: list[dict[str, Any]] = []
    for route in region.foot_sweeps:
        side = route.side
        profile_side = profile_by_side.get(side)
        leg = leg_by_side.get(side)
        if profile_side is None or leg is None or len(route.sweep.sections) != 5:
            _fail(f"{side} foot profile metadata source binding is incomplete")
        # The route's source stations are the exact derived controls assembled
        # by _make_foot_chain_sweep; the profile side supplies authored lineage
        # for pad/toe and the leg route supplies the shin-owned hock lineage.
        hock_source = leg.source_stations[-1]
        pad_source, toe_source = profile_side.sections
        route_sections = route.sweep.sections
        station_metadata: list[dict[str, Any]] = []
        for index, (section, source) in enumerate(zip(route_sections, (hock_source, None, pad_source, None, toe_source))):
            payload: dict[str, Any] = {
                "name": section.name,
                "section_index": index,
                "source_section_index": int(section.source_section_index),
                "owner": _baseline._address_json(section.owner.key),
                "center": [float(value) for value in section.center],
                "volume_radii": [float(value) for value in section.station_volume_radii or ()],
            }
            if source is hock_source:
                payload["lineage"] = {
                    "kind": "authored-leg-hock",
                    "profile": _baseline.AUTHORED_LEG_PROFILE_FORMAT,
                    "source": "authored_leg_profile",
                    "radii": {
                        "lateral": _foot_profile_lineage_json(source.lateral_lineage),
                        "up": _foot_profile_lineage_json(source.up_lineage),
                        "forward": _foot_profile_lineage_json(source.forward_lineage),
                    },
                    "profile_provenance": dict(source.profile_provenance),
                    "variant_provenance": dict(source.variant_provenance),
                }
            elif source is None:
                inputs = ("hock", "pad") if index == 1 else ("pad", "toe")
                payload["lineage"] = {
                    "kind": "derived-guide-midpoint",
                    "inputs": list(inputs),
                    "profile_provenance": dict(profile.provenance),
                    "variant_provenance": dict(profile.variant_provenance),
                }
            else:
                payload["lineage"] = {
                    "kind": "authored-foot-profile",
                    "profile": _baseline.AUTHORED_FOOT_PROFILE_FORMAT,
                    "source": "authored_foot_profile",
                    "radii": {
                        "lateral": _foot_profile_lineage_json(source.lateral_lineage),
                        "up": _foot_profile_lineage_json(source.up_lineage),
                        "forward": _foot_profile_lineage_json(source.forward_lineage),
                    },
                    "profile_provenance": dict(source.profile_provenance),
                    "variant_provenance": dict(source.variant_provenance),
                }
            station_metadata.append(payload)
        side_metadata.append({
            "side": side,
            "route": route.name,
            "route_kind": "foot-profile",
            "station_count": len(route_sections),
            "source_section_indices": [int(section.source_section_index) for section in route_sections],
            "owner_roles": [section.owner.key[3] for section in route_sections],
            "stations": station_metadata,
        })
    return {
        "format": _baseline.AUTHORED_FOOT_PROFILE_FORMAT,
        "source": "authored_foot_profile",
        "source_format": _baseline.SOURCE_FORMAT,
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "operation": _FOOT_PROFILE_OPERATION,
        "topology": "one-five-station-hock-to-toe-route-per-side",
        "route_order": [item.name for item in region.foot_sweeps],
        "route_kinds": ["foot-profile", "foot-profile"],
        "section_names": list(_FOOT_PROFILE_SECTION_NAMES),
        "owner_roles": list(_FOOT_PROFILE_OWNER_ROLES),
        "route_station_count": 10,
        "authored_station_count": 4,
        "route_volume_radius_count": 30,
        "authored_radius_count": 12,
        "provenance": dict(profile.provenance),
        "variant_provenance": dict(profile.variant_provenance),
        "sides": side_metadata,
    }


def _bounds_for_region(region: SuccessorRegion) -> tuple[np.ndarray, np.ndarray]:
    profile_lower, profile_upper = _profile_sweep_bounds(region.loft)
    mins = [profile_lower]
    maxs = [profile_upper]
    for item in region.head_neck_sweeps:
        lower, upper = _profile_sweep_bounds(item.sweep)
        mins.append(lower)
        maxs.append(upper)
    for item in region.limb_sweeps:
        lower, upper = _profile_sweep_bounds(item.sweep)
        mins.append(lower)
        maxs.append(upper)
    for item in region.extremity_sweeps:
        lower, upper = _profile_sweep_bounds(item.sweep)
        mins.append(lower)
        maxs.append(upper)
    for item in region.tail_elements:
        lower, upper = _profile_sweep_bounds(item.sweep)
        mins.append(lower)
        maxs.append(upper)
    for item in region.shoulder_sweeps:
        lower, upper = _profile_sweep_bounds(item.sweep)
        mins.append(lower)
        maxs.append(upper)
    return np.min(np.stack(mins), axis=0), np.max(np.stack(maxs), axis=0)


def _profile_sweep_bounds(sweep: _ProfileSweep) -> tuple[np.ndarray, np.ndarray]:
    """Return conservative finite world-axis bounds including both caps."""

    _validate_profile_sweep(sweep)
    lower: list[np.ndarray] = []
    upper: list[np.ndarray] = []
    for section in sweep.sections:
        center = _vec3(section.center, "profile bounds center")
        first = _vec3(section.transverse_axes[0], "profile bounds transverse axis")
        second = _vec3(section.transverse_axes[1], "profile bounds transverse axis")
        extent = np.abs(first) * section.transverse_radii[0] + np.abs(second) * section.transverse_radii[1]
        if section.tangent_radius is not None:
            tangent = _vec3(section.tangent, "profile bounds tangent axis")
            extent = extent + np.abs(tangent) * float(section.tangent_radius)
        if section.station_volume_axes is not None and section.station_volume_radii is not None:
            extent = np.sum(
                np.abs(np.asarray(section.station_volume_axes, dtype=np.float64).T)
                * np.asarray(section.station_volume_radii, dtype=np.float64),
                axis=1,
            )
        lower.append(center - extent)
        upper.append(center + extent)
    for left, right in zip(sweep.sections, sweep.sections[1:]):
        left_center = _vec3(left.center, "profile span bounds start")
        right_center = _vec3(right.center, "profile span bounds end")
        radius = math.hypot(
            max(left.transverse_radii[0], right.transverse_radii[0]),
            max(left.transverse_radii[1], right.transverse_radii[1]),
        )
        # Interpolated frames can tilt out of the endpoint planes. Expanding
        # every world axis by the two maximum transverse radii's Euclidean
        # norm conservatively encloses any oriented elliptical cross-section.
        lower.append(np.minimum(left_center, right_center) - radius)
        upper.append(np.maximum(left_center, right_center) + radius)
    for transition in sweep.internal_transitions:
        center = _vec3(transition.center, "profile transition bounds center")
        tangent = _vec3(transition.tangent, "profile transition bounds tangent")
        first = _vec3(transition.transverse_axes[0], "profile transition bounds transverse axis")
        second = _vec3(transition.transverse_axes[1], "profile transition bounds transverse axis")
        extent = np.abs(tangent) * transition.axial_radius + np.abs(first) * transition.transverse_radii[0] + np.abs(second) * transition.transverse_radii[1]
        lower.append(center - extent)
        upper.append(center + extent)
    for cap in sweep.endpoint_caps:
        center = _vec3(cap.center, "profile cap bounds center")
        outward = _vec3(cap.outward_tangent, "profile cap bounds tangent")
        first = _vec3(cap.transverse_axes[0], "profile cap bounds transverse axis")
        second = _vec3(cap.transverse_axes[1], "profile cap bounds transverse axis")
        extent = np.abs(outward) * cap.axial_radius + np.abs(first) * cap.transverse_radii[0] + np.abs(second) * cap.transverse_radii[1]
        lower.append(center - extent)
        upper.append(center + extent)
    return np.min(np.stack(lower), axis=0), np.max(np.stack(upper), axis=0)


def _make_components(region: SuccessorRegion, smooth_k: float) -> tuple[_Component, ...]:
    region_bounds = _bounds_for_region(region)
    components: list[_Component] = [
        _Component(region.source_owners[0], "successor-torso-loft", lambda points: _loft_field(points, region.loft), region_bounds, True),
    ]
    for item in region.head_neck_sweeps:
        bounds = _profile_sweep_bounds(item.sweep)
        components.append(_Component(
            item.owner,
            f"successor-{item.recipe}",
            lambda points, current=item.sweep: _profile_sweep_field(points, current),
            bounds,
            True,
            lambda points, current=item.sweep: _loft_owner_keys(points, current),
        ))
    for item in region.limb_sweeps:
        bounds = _profile_sweep_bounds(item.sweep)
        components.append(_Component(
            item.sweep.sections[0].owner,
            f"successor-{item.chain_name}",
            lambda points, current=item.sweep: _profile_sweep_field(points, current),
            bounds,
            True,
            lambda points, current=item.sweep: _loft_owner_keys(points, current),
        ))
    for item in region.extremity_sweeps:
        bounds = _profile_sweep_bounds(item.sweep)
        components.append(_Component(
            item.sweep.sections[0].owner,
            f"successor-{item.name}",
            lambda points, current=item.sweep: _profile_sweep_field(points, current),
            bounds,
            True,
            lambda points, current=item.sweep: _loft_owner_keys(points, current),
        ))
    for item in region.tail_elements:
        bounds = _profile_sweep_bounds(item.sweep)
        components.append(_Component(
            item.owner,
            f"successor-{item.name}",
            lambda points, current=item.sweep: _profile_sweep_field(points, current),
            bounds,
            True,
            lambda points, current=item.sweep: _loft_owner_keys(points, current),
        ))
    for item in region.shoulder_sweeps:
        bounds = _profile_sweep_bounds(item.sweep)
        components.append(_Component(
            item.owner,
            f"successor-{item.recipe}",
            lambda points, current=item: _shoulder_sweep_field(points, current),
            bounds,
            True,
            lambda points, current=item.sweep: _loft_owner_keys(points, current),
        ))
    for field in region.bridge_fields:
        shape = field.shape
        if shape["name"] == "ellipsoid":
            radii = shape["radii"]
            centre = shape["center"]
            bounds = (centre - radii, centre + radii)
        elif shape["name"] == "torso-cage":
            _fail("successor bridge unexpectedly contains baseline torso cage")
        else:
            start, end = shape["from"], shape["to"]
            radius = max(float(shape["r0"]), float(shape["r1"]))
            bounds = (np.minimum(start, end) - radius, np.maximum(start, end) + radius)
        components.append(_Component(field.owner, field.recipe, lambda points, current=field: _baseline._field(points, current), bounds, False))
    if len(components) < 2:
        _fail("successor full-body consumer has no temporary bridge")
    return tuple(components)


def _evaluate_components(points: np.ndarray, components: tuple[_Component, ...], smooth_k: float) -> np.ndarray:
    values = [component.evaluate(points) for component in components]
    return _baseline._smooth_union(values, smooth_k)


def _combined_bounds(components: tuple[_Component, ...], padding: float) -> tuple[np.ndarray, np.ndarray]:
    lower = np.min(np.stack([item.bounds[0] for item in components]), axis=0) - padding
    upper = np.max(np.stack([item.bounds[1] for item in components]), axis=0) + padding
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)) or np.any(upper <= lower):
        _fail("successor sampling bounds are invalid")
    return lower, upper


def _orient_mesh(vertices: np.ndarray, faces: np.ndarray, axes: tuple[np.ndarray, np.ndarray, np.ndarray], components: tuple[_Component, ...], smooth_k: float) -> tuple[np.ndarray, np.ndarray, float]:
    e1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    e2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    areas = np.cross(e1, e2)
    centres = (vertices[faces[:, 0]] + vertices[faces[:, 1]] + vertices[faces[:, 2]]) / 3.0
    delta = 0.5 * min(float(axis[1] - axis[0]) for axis in axes)
    gradients = []
    for axis in range(3):
        step = np.eye(3)[axis] * delta
        gradients.append((_evaluate_components(centres + step, components, smooth_k) - _evaluate_components(centres - step, components, smooth_k)) / (2.0 * delta))
    gradient = np.column_stack(gradients)
    if float(np.mean(np.sum(areas * gradient, axis=1))) < 0.0:
        faces = faces[:, [0, 2, 1]]
        areas = -areas
    volume = float(np.sum(np.einsum("ij,ij->i", vertices[faces[:, 0]], areas)) / 6.0)
    if not math.isfinite(volume) or volume <= 0.0:
        _fail("successor mesh has non-positive signed volume")
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], areas)
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= 1.0e-14) or not np.all(np.isfinite(lengths)):
        _fail("successor mesh contains undefined normals")
    return faces, normals / lengths[:, None], volume


def build_variant(form: Any, descriptors: tuple[Any, ...], samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> SuccessorMesh:
    """Build one deterministic full-body mesh through the successor consumer."""

    if type(samples) is not int or samples < 20 or samples > MAX_SAMPLES or samples**3 > MAX_VOXELS:
        _fail("successor sampling configuration exceeds bounded limits")
    if not math.isfinite(float(padding)) or padding < 0.0 or not math.isfinite(float(smooth_k)) or smooth_k <= 0.0:
        _fail("successor padding and smooth-k must be finite and valid")
    guide = _baseline._derive_hybrid_guides(form, descriptors)
    baseline_fields = _baseline._compile_hybrid_guide(guide)
    baseline_signature = tuple((field.owner.key, field.recipe) for field in baseline_fields)
    region = compile_successor_region(guide, baseline_fields)
    components = _make_components(region, smooth_k)
    if len(components) * samples**3 > MAX_FIELD_VALUES:
        _fail("successor field sampling configuration exceeds bounded limits")
    lower, upper = _combined_bounds(components, padding)
    axes = tuple(np.linspace(lower[index], upper[index], samples, dtype=np.float64) for index in range(3))
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    field = _evaluate_components(points, components, smooth_k)
    if not np.all(np.isfinite(field)) or float(np.min(field)) >= 0.0 or float(np.max(field)) <= 0.0:
        _fail("successor field has no finite zero crossing")
    if np.any(field[(0, -1), :, :] <= 0) or np.any(field[:, (0, -1), :] <= 0) or np.any(field[:, :, (0, -1)] <= 0):
        _fail("successor field reaches the sampling domain boundary")
    try:
        raw_vertices, raw_faces, _, _ = marching_cubes(field, level=0.0, spacing=tuple(float(axis[1] - axis[0]) for axis in axes), gradient_direction="descent", allow_degenerate=False)
    except Exception as exc:
        raise SuccessorPreviewError(f"successor surface extraction failed: {exc}") from exc
    vertices = np.asarray(raw_vertices, dtype=np.float64) + lower
    faces = np.asarray(raw_faces, dtype=np.int64)
    faces, normals, volume = _orient_mesh(vertices, faces, axes, components, smooth_k)
    labels: list[tuple[str, tuple[str, ...], str, str]] = []
    for vertex in vertices:
        values = [float(component.evaluate(vertex.reshape(1, 3))[0]) for component in components]
        winner_index = int(np.argmin(values))
        winner = components[winner_index]
        if winner.attribution is not None:
            labels.append(winner.attribution(vertex.reshape(1, 3))[0])
        elif winner_index == 0:
            labels.append(_loft_owner_keys(vertex.reshape(1, 3), region.loft)[0])
        else:
            labels.append(winner.owner.key)
    metrics = _baseline._mesh_checks(vertices, faces, labels, (lower, upper), volume)
    metrics.update({
        "consumer_id": CONSUMER_ID,
        "successor_region_id": SUCCESSOR_REGION_ID,
        "source_format": _baseline.SOURCE_FORMAT,
        "successor_region": {
            "regional_guide_format": REGIONAL_GUIDE_FORMAT,
            "torso_representation": TORSO_PROFILE_OPERATION,
            "torso_profile_exponent": TORSO_SUPERELLIPSE_EXPONENT,
            "torso_sections_consumed": region.sections_consumed,
            "torso_section_names": list(region.section_names),
            "torso_section_owner_keys": [_baseline._address_json(owner.key) for owner in region.loft.owners],
            "torso_section_controls": [
                {
                    "name": section.name,
                    "owner": _baseline._address_json(section.owner.key),
                    "center": [float(value) for value in section.center],
                    "axial_position": float(section.axial_position if section.axial_position is not None else section.path_length),
                    "lateral_radius": float(section.cardinal_radii[0]),
                    "anterior_radius": float(section.cardinal_radii[1]),
                    "posterior_radius": float(section.cardinal_radii[2]),
                }
                for section in region.loft.sections
            ],
            "shoulder_representation": "authored-five-section-frame-aware-profile-sweeps",
            "shoulder_sweeps_consumed": region.shoulder_sweeps_consumed,
            "shoulder_sweep_order": [item.recipe for item in region.shoulder_sweeps],
            "shoulder_sweep_section_counts": [len(item.sweep.sections) for item in region.shoulder_sweeps],
            "shoulder_sweep_section_names": [list(item.sweep.names) for item in region.shoulder_sweeps],
            "shoulder_sweep_section_owner_keys": [
                [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                for item in region.shoulder_sweeps
            ],
            "shoulder_sweep_controls": [
                {
                    "side": item.recipe.split("-", 1)[0],
                    "authored_center": [float(value) for value in item.sweep.sections[2].center],
                    "vertical_radius": float(item.sweep.sections[2].transverse_radii[0]),
                    "depth_radius": float(item.sweep.sections[2].transverse_radii[1]),
                }
                for item in region.shoulder_sweeps
            ],
            "head_neck": _head_neck_metadata(region),
            "arm_profile": _arm_profile_metadata(region),
            "leg_profile": _leg_profile_metadata(region),
            "foot_profile": _foot_profile_metadata(region),
            "limb_representation": "shared-guide-derived-authored-arm-and-leg-profile-routes",
            "limb_sweeps_consumed": len(region.limb_sweeps),
            "limb_sweep_order": [item.chain_name for item in region.limb_sweeps],
            "limb_sweep_route_kinds": [item.route_kind for item in region.limb_sweeps],
            "limb_sweep_station_counts": [item.sections_consumed for item in region.limb_sweeps],
            "limb_sweep_station_names": [list(item.section_names) for item in region.limb_sweeps],
            "limb_sweep_section_owner_keys": [
                [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                for item in region.limb_sweeps
            ],
            "limb_sweep_station_owner_keys": [
                [_baseline._address_json(section.owner.key) for section in item.sweep.sections]
                for item in region.limb_sweeps
            ],
            "limb_sweep_endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in region.limb_sweeps],
            "limb_sweep_internal_transition_counts": [len(item.sweep.internal_transitions) for item in region.limb_sweeps],
            "limb_source_owner_keys": [
                _baseline._address_json(owner.key)
                for item in region.limb_sweeps
                for owner in item.source_owners
            ],
            "extremity_representation": "shared-guide-derived-hand-and-digitigrade-foot-profile-sweeps",
            "extremity_sweeps_consumed": len(region.extremity_sweeps),
            "extremity_sweep_order": [item.name for item in region.extremity_sweeps],
            "extremity_sweep_kinds": [item.kind for item in region.extremity_sweeps],
            "extremity_sweep_station_counts": [item.sections_consumed for item in region.extremity_sweeps],
            "extremity_sweep_station_names": [list(item.section_names) for item in region.extremity_sweeps],
            "extremity_sweep_section_owner_keys": [
                [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                for item in region.extremity_sweeps
            ],
            "extremity_sweep_endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in region.extremity_sweeps],
            "extremity_sweep_internal_transition_counts": [len(item.sweep.internal_transitions) for item in region.extremity_sweeps],
            "extremity_source_owner_keys": [
                _baseline._address_json(owner.key)
                for item in region.extremity_sweeps
                for owner in item.source_owners
            ],
            "tail_representation": "shared-guide-derived-profile-sweep-elements",
            "tail_elements_consumed": len(region.tail_elements),
            "tail_element_order": [item.name for item in region.tail_elements],
            "tail_element_kinds": [item.kind for item in region.tail_elements],
            "tail_element_section_counts": [item.sections_consumed for item in region.tail_elements],
            "tail_element_section_names": [list(item.section_names) for item in region.tail_elements],
            "tail_element_owner_keys": [_baseline._address_json(item.owner.key) for item in region.tail_elements],
            "tail_element_endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in region.tail_elements],
            "tail_element_internal_transition_counts": [len(item.sweep.internal_transitions) for item in region.tail_elements],
            "tail_source_owner_keys": [_baseline._address_json(item.owner.key) for item in region.tail_elements[::3]],
            "tail_element_controls": _tail_element_metadata(region.tail_elements),
            "tail_tip_shared_endpoint": {
                "point": [float(value) for value in region.tail_elements[3].sweep.sections[-1].center],
                "source_end_profile": [float(value) for value in region.tail_elements[3].sweep.sections[-1].transverse_radii],
                "extension_start_profile": [float(value) for value in region.tail_elements[4].sweep.sections[0].transverse_radii],
            },
            "replaced_baseline_field_count": len(baseline_fields) - len(region.bridge_fields),
            "replaced_baseline_recipes": list(region.replaced_baseline_recipes),
        },
        "temporary_bridge": {
            "enabled": True,
            "consumer": "baseline-analytic-fields",
            "regions": ["thigh-root-connectors", "hip-transitions"],
            "field_count": len(region.bridge_fields),
            "retained_recipes": sorted({field.recipe for field in region.bridge_fields}),
        },
        "baseline_recipe_signature": [[list(field_key[0]), list(field_key[1]), field_key[2], field_key[3], recipe] for field_key, recipe in baseline_signature],
        "source_descriptor_count": len(descriptors),
        "component_count_for_sampling": len(components),
        "grid": {"samples_per_axis": samples, "axis_order": ["x", "y", "z"], "bounds_min": lower.tolist(), "bounds_max": upper.tolist(), "spacing": [float(axis[1] - axis[0]) for axis in axes]},
    })
    return SuccessorMesh(vertices, faces, normals, tuple(labels), metrics, region, metrics["grid"])


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _write_ply(path: Path, mesh: SuccessorMesh) -> None:
    lines = ["ply", "format ascii 1.0", f"element vertex {len(mesh.vertices)}", "property float x", "property float y", "property float z", "property float nx", "property float ny", "property float nz", f"element face {len(mesh.faces)}", "property list uchar int vertex_indices", "end_header"]
    lines.extend("%.9f %.9f %.9f %.9f %.9f %.9f" % tuple([*vertex, *normal]) for vertex, normal in zip(mesh.vertices, mesh.normals))
    lines.extend("3 %d %d %d" % tuple(int(value) for value in face) for face in mesh.faces)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _sha(path: Path, kind: str, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"kind": kind, "path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _atomic_rename_noreplace(source: Path, target: Path) -> None:
    """Atomically rename a directory without replacing an existing target.

    This experiment is documented for Linux/WSL.  Refuse publication when the
    kernel primitive is unavailable rather than falling back to a
    check-then-rename race.
    """

    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is not None:
            renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            renameat2.restype = ctypes.c_int
            result = renameat2(
                -100,  # AT_FDCWD
                os.fsencode(str(source)),
                -100,
                os.fsencode(str(target)),
                1,  # RENAME_NOREPLACE
            )
            if result == 0:
                return
            error = ctypes.get_errno()
            if error == errno.EEXIST:
                raise FileExistsError(errno.EEXIST, "publication target appeared")
            if error not in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
                raise OSError(error, os.strerror(error))
    raise OSError(errno.ENOTSUP, "atomic no-replace directory rename unavailable")


def _read_bounded_input(input_path: Path) -> bytes:
    """Read at most the shared limit plus one sentinel byte."""

    try:
        with input_path.open("rb") as stream:
            data = stream.read(_baseline.MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise SuccessorPreviewError(f"could not read input: {exc}") from exc
    if len(data) > _baseline.MAX_INPUT_BYTES:
        _fail("input exceeds bounded size")
    return data


def generate(input_path: Path, output: Path, *, samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> dict[str, Any]:
    if output.exists() or os.path.lexists(output):
        _fail(f"refusing to overwrite output: {output}")
    if not output.parent.is_dir():
        _fail(f"output parent must exist: {output.parent}")
    data = _read_bounded_input(input_path)
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SuccessorPreviewError(f"input is not finite JSON: {exc}") from exc
    form = _baseline.validate_envelope(value)

    # Prepare every private guide and its canonical baseline field set before
    # any mesh is published.  The capture frame deliberately follows the
    # baseline consumer's bounds rather than the successor's mesh bounds so
    # the two consumers remain directly comparable across all four variants.
    prepared: list[tuple[str, tuple[Any, ...], dict[str, Any], Any, tuple[Any, ...]]] = []
    for variant_id, descriptors, raw_variant in form.variants:
        guide = _baseline._derive_hybrid_guides(form, descriptors)
        _baseline._validate_hybrid_guide(guide)
        fields = _baseline._compile_hybrid_guide(guide)
        prepared.append((variant_id, descriptors, raw_variant, guide, fields))
    shared_render_bounds = _baseline._shared_render_bounds(
        tuple(item[4] for item in prepared), DEFAULT_CAPTURE_PADDING
    )
    for _, _, _, guide, _ in prepared:
        _baseline._validate_hybrid_guide(guide, shared_render_bounds)

    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        records: list[dict[str, Any]] = []
        lower, upper = shared_render_bounds
        shared_bounds_json = {"min": [float(item) for item in lower], "max": [float(item) for item in upper]}
        canvas = {"width": _baseline.CANVAS[0], "height": _baseline.CANVAS[1], "mode": "RGB"}
        layout = _baseline._layout_json()
        projections = _baseline._projection_json()
        for variant_id, descriptors, raw_variant, guide, _ in prepared:
            source_variant_sha256 = hashlib.sha256(_canonical(raw_variant)).hexdigest()
            mesh = build_variant(form, descriptors, samples=samples, padding=padding, smooth_k=smooth_k)
            variant_dir = stage / variant_id
            variant_dir.mkdir()
            ply = variant_dir / "surface.ply"
            metrics = variant_dir / "metrics.json"
            successor = variant_dir / "successor.json"
            png = variant_dir / "guide-skin-composite.png"
            _write_ply(ply, mesh)
            metrics.write_bytes(_canonical(mesh.metrics) + b"\n")
            successor.write_bytes(_canonical({
                "format": FORMAT,
                "variant_id": variant_id,
                "profile_id": raw_variant["profile_id"],
                "source_variant_sha256": source_variant_sha256,
                "consumer_id": CONSUMER_ID,
                "successor_region_id": SUCCESSOR_REGION_ID,
                "capture": {
                    "canvas": canvas,
                    "projections": projections,
                    "layout": layout,
                    "shared_render_bounds": shared_bounds_json,
                },
                "torso": {
                    "representation": TORSO_PROFILE_OPERATION,
                    "regional_guide_format": REGIONAL_GUIDE_FORMAT,
                    "superellipse_exponent": TORSO_SUPERELLIPSE_EXPONENT,
                    "sections_consumed": mesh.representation.sections_consumed,
                    "section_names": list(mesh.representation.section_names),
                    "section_controls": mesh.metrics["successor_region"]["torso_section_controls"],
                },
                "shoulders": {
                    "representation": "authored-five-section-frame-aware-profile-sweeps",
                    "sweeps_consumed": mesh.representation.shoulder_sweeps_consumed,
                    "sweep_order": [item.recipe for item in mesh.representation.shoulder_sweeps],
                    "section_counts": [len(item.sweep.sections) for item in mesh.representation.shoulder_sweeps],
                    "section_names": [list(item.sweep.names) for item in mesh.representation.shoulder_sweeps],
                },
                "head_neck": {
                    **_head_neck_metadata(mesh.representation),
                },
                "limbs": {
                    "representation": "shared-guide-derived-authored-arm-and-leg-profile-routes",
                    "sweeps_consumed": len(mesh.representation.limb_sweeps),
                    "sweep_order": [item.chain_name for item in mesh.representation.limb_sweeps],
                    "route_kinds": [item.route_kind for item in mesh.representation.limb_sweeps],
                    "station_counts": [item.sections_consumed for item in mesh.representation.limb_sweeps],
                    "station_names": [list(item.section_names) for item in mesh.representation.limb_sweeps],
                    "section_owner_keys": [
                        [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                        for item in mesh.representation.limb_sweeps
                    ],
                    "station_owner_keys": [
                        [_baseline._address_json(section.owner.key) for section in item.sweep.sections]
                        for item in mesh.representation.limb_sweeps
                    ],
                    "endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in mesh.representation.limb_sweeps],
                    "arm_profile": _arm_profile_metadata(mesh.representation),
                    "leg_profile": _leg_profile_metadata(mesh.representation),
                    "foot_profile": _foot_profile_metadata(mesh.representation),
                },
                "extremities": {
                    "representation": "shared-guide-derived-hand-and-digitigrade-foot-profile-sweeps",
                    "sweeps_consumed": len(mesh.representation.extremity_sweeps),
                    "sweep_order": [item.name for item in mesh.representation.extremity_sweeps],
                    "sweep_kinds": [item.kind for item in mesh.representation.extremity_sweeps],
                    "station_counts": [item.sections_consumed for item in mesh.representation.extremity_sweeps],
                    "station_names": [list(item.section_names) for item in mesh.representation.extremity_sweeps],
                    "section_owner_keys": [
                        [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                        for item in mesh.representation.extremity_sweeps
                    ],
                    "endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in mesh.representation.extremity_sweeps],
                    "internal_transition_counts": [len(item.sweep.internal_transitions) for item in mesh.representation.extremity_sweeps],
                },
                "tail": {
                    "representation": "shared-guide-derived-profile-sweep-elements",
                    "elements_consumed": len(mesh.representation.tail_elements),
                    "element_order": [item.name for item in mesh.representation.tail_elements],
                    "element_kinds": [item.kind for item in mesh.representation.tail_elements],
                    "section_counts": [item.sections_consumed for item in mesh.representation.tail_elements],
                    "section_names": [list(item.section_names) for item in mesh.representation.tail_elements],
                    "owner_keys": [_baseline._address_json(item.owner.key) for item in mesh.representation.tail_elements],
                    "endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in mesh.representation.tail_elements],
                    "internal_transition_counts": [len(item.sweep.internal_transitions) for item in mesh.representation.tail_elements],
                    "controls": mesh.metrics["successor_region"]["tail_element_controls"],
                    "tip_shared_endpoint": mesh.metrics["successor_region"]["tail_tip_shared_endpoint"],
                },
                "temporary_bridge": mesh.metrics["temporary_bridge"],
                "replaced_baseline_recipes": list(mesh.representation.replaced_baseline_recipes),
            }) + b"\n")
            _baseline._render(png, mesh.vertices, mesh.faces, variant_id, guide=guide, bounds=shared_render_bounds)
            records.append({
                "id": variant_id,
                "profile_id": raw_variant["profile_id"],
                "source_variant_sha256": source_variant_sha256,
                "metrics": mesh.metrics,
                "inventory": [
                    _sha(ply, "ply", stage),
                    _sha(metrics, "metrics", stage),
                    _sha(successor, "successor-consumer-sidecar", stage),
                    {**_sha(png, "guide-skin-composite-png", stage), "width": _baseline.CANVAS[0], "height": _baseline.CANVAS[1], "views": ["front", "side", "three-quarter"], "panels_per_view": 2, "mode": "RGB"},
                ],
            })
        manifest = {
            "format": FORMAT,
            "status": "success",
            "consumer_id": CONSUMER_ID,
            "source_format": _baseline.SOURCE_FORMAT,
            "source": {"format": _baseline.SOURCE_FORMAT, "sha256": hashlib.sha256(data).hexdigest(), "document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"], "reference_scale": form.reference_scale_raw},
            "shared_render_bounds": shared_bounds_json,
            "canvas": canvas,
            "layout": layout,
            "projections": projections,
            "generator": {"samples_per_axis": samples, "padding": padding, "capture_padding": DEFAULT_CAPTURE_PADDING, "smooth_k": smooth_k, "consumer_boundary": "successor torso/shoulder/head/neck, authored arm and leg profile routes, bilateral hands, digitigrade feet, and tail; baseline temporary bridge for thigh-root/hip connectors", "production_status": "disposable exploratory proof"},
            "variants": records,
        }
        manifest_path = stage / "successor-surface-manifest.json"
        manifest_path.write_bytes(_canonical(manifest) + b"\n")
        expected_files = {"successor-surface-manifest.json"}
        expected_directories = set(_baseline.VARIANT_IDS)
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
        try:
            _atomic_rename_noreplace(stage, output)
        except FileExistsError as exc:
            raise SuccessorPreviewError(f"refusing to overwrite existing output: {output}") from exc
        except OSError as exc:
            raise SuccessorPreviewError(f"cannot publish successor output atomically: {exc}") from exc
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the disposable successor torso/shoulder/head/neck/limb/extremity/tail surface preview")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples-per-axis", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--padding", type=float, default=DEFAULT_PADDING)
    parser.add_argument("--smooth-k", type=float, default=DEFAULT_SMOOTH_K)
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.input, args.output, samples=args.samples_per_axis, padding=args.padding, smooth_k=args.smooth_k)
    except (OSError, ValueError, SuccessorPreviewError, _baseline.PreviewError) as exc:
        print(json.dumps({"format": FORMAT, "status": "failure", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"format": FORMAT, "status": "success", "output": str(args.output), "variants": [item["id"] for item in manifest["variants"]]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

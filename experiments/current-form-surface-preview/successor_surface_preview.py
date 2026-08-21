#!/usr/bin/env python3
"""Private successor-surface experiment for the disposable form preview.

This module is intentionally adjacent to, rather than a modification of,
``surface_preview.py``.  It consumes the existing private hybrid guide and
replaces the torso/shoulder, head/neck, and four limb-chain skin consumers with
explicitly identified profile sweeps and swept shoulder spans.  Paws, tail, and
root/hip connector fields remain an explicit temporary bridge so the experiment
can still produce a whole-body mesh without pretending that those regions have
been redesigned.

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


FORMAT = "creature-kernel.disposable-successor-surface-preview.v1"
CONSUMER_ID = "successor-surface-v1"
SUCCESSOR_REGION_ID = "successor-torso-shoulder-head-neck-limb-profile-sweeps-v3"
DEFAULT_SAMPLES = 56
DEFAULT_PADDING = 0.50
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

    @property
    def radii(self) -> tuple[float, float]:
        return self.transverse_radii

    @property
    def axes(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        return self.transverse_axes


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

    def __post_init__(self) -> None:
        if not self.internal_transitions:
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
class _SweptSpan:
    """One source-owned, tapered span of a shoulder support curve."""

    side: str
    curve_name: str
    span_index: int
    owner: Any
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    start_radius: float
    end_radius: float

    @property
    def recipe(self) -> str:
        return f"successor-shoulder-{self.side}-{self.curve_name}-{self.span_index}"


@dataclass(frozen=True)
class _RegionalProfileSweep:
    """One guide-derived profile sweep with source ownership and a recipe label."""

    recipe: str
    owner: Any
    sweep: _ProfileSweep


@dataclass(frozen=True)
class _LimbChainSweep:
    """One bilateral limb-chain sweep with per-section source ownership."""

    chain_name: str
    source_owners: tuple[Any, ...]
    sweep: _ProfileSweep

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


@dataclass(frozen=True)
class SuccessorRegion:
    """Explicit successor torso/shoulder/head/neck/limb representation.

    ``bridge_fields`` are untouched baseline fields for all regions outside
    this successor region.  They are kept here, rather than silently folded
    into the successor, so later limb/paw/tail consumers have a stable
    extension point and the temporary boundary remains inspectable.
    """

    consumer_id: str
    region_id: str
    loft: _ProfileSweep
    shoulder_spans: tuple[_SweptSpan, ...]
    bridge_fields: tuple[Any, ...]
    replaced_baseline_recipes: tuple[str, ...]
    source_owners: tuple[Any, ...]
    head_neck_sweeps: tuple[_RegionalProfileSweep, ...] = ()
    limb_sweeps: tuple[_LimbChainSweep, ...] = ()

    @property
    def section_names(self) -> tuple[str, ...]:
        return self.loft.names

    @property
    def sections_consumed(self) -> int:
        return len(self.loft.names)

    @property
    def shoulder_inputs_consumed(self) -> int:
        return len(self.shoulder_spans)

    @property
    def chain_sweeps(self) -> tuple[_LimbChainSweep, ...]:
        """Compatibility alias for the named successor limb chains."""

        return self.limb_sweeps


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
    centers = tuple(_vec3(section.center, f"profile-section[{index}].center") for index, section in enumerate(sections))
    previous_path = None
    for index, section in enumerate(sections):
        where = f"profile-section[{index}]"
        center = centers[index]
        tangent = _vec3(section.tangent, f"{where}.tangent")
        first = _vec3(section.transverse_axes[0], f"{where}.transverse-first")
        second = _vec3(section.transverse_axes[1], f"{where}.transverse-second")
        _finite_positive(tuple(float(value) for value in section.transverse_radii), f"{where}.radii")
        tangent_length = float(np.linalg.norm(tangent))
        first_length = float(np.linalg.norm(first))
        second_length = float(np.linalg.norm(second))
        if not all(math.isclose(length, 1.0, rel_tol=0.0, abs_tol=_FRAME_TOLERANCE) for length in (tangent_length, first_length, second_length)):
            _fail(f"{where} frame vectors must be unit length")
        if max(abs(float(np.dot(tangent, first))), abs(float(np.dot(tangent, second))), abs(float(np.dot(first, second)))) > _FRAME_TOLERANCE:
            _fail(f"{where} frame vectors must be orthogonal")
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
    expected_transitions = _derive_bend_transitions(sections)
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


def _make_profile_sweep(guide: Any) -> _ProfileSweep:
    """Compile the exact seven torso guides into the generic sweep."""

    guide_sections = tuple(guide.torso_cage.sections)
    if len(guide_sections) != 7:
        _fail(f"successor torso profile sweep requires exactly seven sections, got {len(guide_sections)}")
    if guide.torso_cage.axes != guide.topology.axes:
        _fail("successor torso profile sweep axes must match guide topology")
    prototype = guide.torso_cage.axes
    preferred_first = _vec3(prototype.lateral, "torso profile lateral axis")
    preferred_second = _vec3(prototype.forward, "torso profile forward axis")
    centers = [_vec3(section.center, f"torso guide section {section.name}.center") for section in guide_sections]
    sections: list[_ProfileSection] = []
    path_length = 0.0
    for index, source in enumerate(guide_sections):
        if index == 0:
            direction = centers[1] - centers[0]
        elif index == len(centers) - 1:
            direction = centers[-1] - centers[-2]
        else:
            direction = centers[index + 1] - centers[index - 1]
        tangent, first, second = _frame_from_tangent(direction, preferred_first, preferred_second, f"torso profile section {source.name}")
        if index:
            span_length = float(np.linalg.norm(centers[index] - centers[index - 1]))
            if span_length <= _DEGENERATE_TOLERANCE:
                _fail(f"torso profile section {source.name} follows a degenerate span")
            path_length += span_length
        radii = (float(source.lateral_radius), float(source.depth_radius))
        _finite_positive(radii, f"torso profile section {source.name}.radii")
        sections.append(_ProfileSection(
            name=source.name,
            owner=source.owner,
            center=tuple(float(value) for value in centers[index]),
            tangent=tuple(float(value) for value in tangent),
            transverse_axes=(tuple(float(value) for value in first), tuple(float(value) for value in second)),
            transverse_radii=radii,
            path_length=path_length,
        ))
    ordered = tuple(sections)
    caps = (
        _ProfileEndpointCap("start", ordered[0].center, tuple(-float(value) for value in ordered[0].tangent), ordered[0].transverse_axes, ordered[0].transverse_radii, min(ordered[0].transverse_radii)),
        _ProfileEndpointCap("end", ordered[-1].center, ordered[-1].tangent, ordered[-1].transverse_axes, ordered[-1].transverse_radii, min(ordered[-1].transverse_radii)),
    )
    sweep = _ProfileSweep(ordered, caps)
    _validate_profile_sweep(sweep)
    return sweep


# Retain the old private constructor name as a narrow source-compatible alias
# for callers of this disposable experiment.  It now returns the generic
# frame-aware representation rather than a world-Y-only loft.
def _make_loft(guide: Any) -> _ProfileSweep:
    return _make_profile_sweep(guide)


def _make_spans(guide: Any) -> tuple[_SweptSpan, ...]:
    spans: list[_SweptSpan] = []
    frame = guide.shoulder_frame
    for side in frame.sides:
        for curve_name, curve in (
            ("anterior-support", side.anterior_support),
            ("posterior-return", side.posterior_return),
            ("deltoid-sweep", side.deltoid_sweep),
        ):
            if len(curve.points) != len(curve.profile) or len(curve.points) < 2:
                _fail(f"successor shoulder input {side.side}/{curve_name} is malformed")
            for index in range(len(curve.points) - 1):
                start = tuple(float(value) for value in curve.points[index])
                end = tuple(float(value) for value in curve.points[index + 1])
                start_radius = float(curve.profile[index])
                end_radius = float(curve.profile[index + 1])
                if not all(math.isfinite(value) for value in (*start, *end)):
                    _fail(f"{side.side}/{curve_name} contains non-finite points")
                _finite_positive((start_radius, end_radius), f"{side.side}/{curve_name}.profile")
                if start == end:
                    _fail(f"successor shoulder input {side.side}/{curve_name} contains a degenerate span")
                spans.append(_SweptSpan(side.side, curve_name, index, curve.owner, start, end, start_radius, end_radius))
    if len(spans) != 16:  # 2 sides: 3 + 3 + 2 spans
        _fail(f"successor shoulder input count is unstable: {len(spans)}")
    return tuple(spans)


# These compact controls are deliberately shared by every fixed variant.  The
# guide supplies all centres, radii, and axes; these values only describe the
# disposable profile shape around those controls.  Offsets are fractions of
# the profile's selected axial radius, while the other two values scale its
# declared transverse radii.
_CRANIUM_PROFILE = (
    (-0.52, 0.68, 0.72),
    (-0.26, 0.94, 0.93),
    (0.00, 1.00, 1.00),
    (0.28, 0.93, 0.92),
    (0.52, 0.70, 0.75),
)
_MUZZLE_PROFILE = (
    (-0.32, 0.86, 0.84),
    (-0.05, 0.98, 0.94),
    (0.24, 0.84, 0.76),
    (0.56, 0.58, 0.52),
)
_COLLAR_PROFILE = (
    (-0.36, 0.76, 0.72),
    (0.00, 1.00, 0.96),
    (0.36, 0.78, 0.73),
)
# Shared sample-grid visibility correction for the disposable collar only.
_COLLAR_TRANSVERSE_SCALE = 1.50


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


def _make_head_neck_sweeps(guide: Any) -> tuple[_RegionalProfileSweep, ...]:
    """Build the fixed-order shared head/neck successor construction."""

    head = guide.head_guide
    if head.axes != guide.topology.axes:
        _fail("successor head/neck axes must match guide topology")
    axes = head.axes
    head_owner = head.head_owner
    neck_owner = head.neck_owner
    return (
        _RegionalProfileSweep(
            "cranium", head_owner,
            _make_mass_profile_sweep(
                "cranium", head_owner, head.cranium_center, head.cranium_radii,
                axes.up, float(head.cranium_radii[1]),
                (float(head.cranium_radii[0]), float(head.cranium_radii[2])),
                (axes.lateral, axes.forward), _CRANIUM_PROFILE,
            ),
        ),
        _RegionalProfileSweep(
            "muzzle", head_owner,
            _make_mass_profile_sweep(
                "muzzle", head_owner, head.muzzle_center, head.muzzle_radii,
                axes.forward, float(head.muzzle_radii[2]),
                (float(head.muzzle_radii[0]), float(head.muzzle_radii[1])),
                (axes.lateral, axes.up), _MUZZLE_PROFILE,
            ),
        ),
        _RegionalProfileSweep(
            "head-base-bridge", head_owner,
            _make_transition_sweep(
                "head-base-bridge", head_owner, head.head_transition,
                head.head_transition_thickness, axes,
            ),
        ),
        _RegionalProfileSweep(
            "tapered-neck", neck_owner,
            _make_transition_sweep(
                "tapered-neck", neck_owner, head.neck_transition,
                head.neck_transition_thickness, axes,
            ),
        ),
        _RegionalProfileSweep(
            "neck-collar", neck_owner,
            _make_mass_profile_sweep(
                "neck-collar", neck_owner, head.neck_collar_center, head.neck_collar_radii,
                axes.up, float(head.neck_collar_radii[1]),
                (
                    float(head.neck_collar_radii[0]) * _COLLAR_TRANSVERSE_SCALE,
                    float(head.neck_collar_radii[2]) * _COLLAR_TRANSVERSE_SCALE,
                ),
                (axes.lateral, axes.forward), _COLLAR_PROFILE,
            ),
        ),
    )


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
    """Build the fixed-order left/right arm and leg chain sweeps."""

    inventory = _limb_inventory(guide)
    sweeps: list[_LimbChainSweep] = []
    for side in ("left", "right"):
        upper = inventory[(side, "upper_arm")]
        forearm = inventory[(side, "forearm")]
        if upper.joint is None or upper.joint.name != "elbow":
            _fail(f"{side} upper-arm guide must provide one elbow station")
        upper_start, upper_mid = upper.sections[0].centerline
        upper_joint_endpoint = upper.sections[1].centerline[1]
        forearm_joint_start = forearm.sections[0].centerline[0]
        elbow = upper.joint
        _require_same_point(upper_joint_endpoint, elbow.center, f"{side}.elbow source endpoint")
        _require_same_point(forearm_joint_start, elbow.center, f"{side}.elbow forearm start")
        forearm_mid = forearm.sections[0].centerline[1]
        forearm_end = forearm.sections[1].centerline[1]
        # The frame is derived by _limb_chain_sweep. The current guide exposes
        # scalar profile controls, so each station is circular in its local
        # transverse plane.
        sweeps.append(_limb_chain_sweep(
            f"{side}-arm",
            (
                ("upper-arm-start", upper.owner, upper_start, (upper.sections[0].thickness[0],) * 2),
                ("upper-arm-midpoint", upper.owner, upper_mid, (upper.sections[0].thickness[1],) * 2),
                ("elbow", upper.owner, elbow.center, (float(elbow.radii[0]), float(elbow.radii[1]))),
                ("forearm-midpoint", forearm.owner, forearm_mid, (forearm.sections[0].thickness[1],) * 2),
                ("forearm-distal", forearm.owner, forearm_end, (forearm.sections[1].thickness[1],) * 2),
            ),
            upper.axes,
        ))

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
        sweeps.append(_limb_chain_sweep(
            f"{side}-leg",
            (
                ("thigh-start", thigh.owner, thigh_start, (thigh.sections[0].thickness[0],) * 2),
                ("thigh-midpoint", thigh.owner, thigh_mid, (thigh.sections[0].thickness[1],) * 2),
                ("knee", thigh.owner, knee.center, (float(knee.radii[0]), float(knee.radii[1]))),
                ("shin-midpoint", shin.owner, shin_mid, (shin.sections[0].thickness[1],) * 2),
                ("hock-endpoint", shin.owner, hock.center, (float(hock.radii[0]), float(hock.radii[1]))),
            ),
            thigh.axes,
        ))
    if tuple(item.chain_name for item in sweeps) != ("left-arm", "left-leg", "right-arm", "right-leg"):
        _fail("successor limb chain order is unstable")
    return tuple(sweeps)


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
            chain = chains[f"{side}-{kind}"]
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

    The torso cage, shoulder deltoid spans, five baseline head/neck fields, and
    the four bilateral limb chains are replaced. Every other baseline field is
    carried as a named temporary bridge, including root/hip connectors and
    paws, feet, and tail that preserve whole-body continuity for this slice.
    """

    _baseline._validate_hybrid_guide(guide)
    if baseline_fields is None:
        baseline_fields = _baseline._compile_hybrid_guide(guide)
    replaced = (
        "torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
        "deltoid-sweep-1", *_LIMB_CHAIN_BASELINE_RECIPES,
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
    replaced_fields = tuple(field for field in baseline_fields if field.recipe in replaced)
    limb_sweeps = _make_limb_sweeps(guide)
    bridge = tuple(
        field for field in _validate_limb_bridge_inventory(guide, baseline_fields, limb_sweeps)
        if field.recipe not in {"torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar", "deltoid-sweep-1"}
    )
    if len(bridge) + len(replaced_fields) != len(baseline_fields):
        _fail("baseline bridge selection lost fields")
    head_neck_sweeps = _make_head_neck_sweeps(guide)
    source_keys = {descriptor.key for descriptor in guide.source_descriptors}
    if any(sweep.owner.key not in source_keys for sweep in head_neck_sweeps):
        _fail("successor head/neck sweep owner is not an existing source AddressKey")
    return SuccessorRegion(
        consumer_id=CONSUMER_ID,
        region_id=SUCCESSOR_REGION_ID,
        loft=_make_loft(guide),
        shoulder_spans=_make_spans(guide),
        bridge_fields=bridge,
        replaced_baseline_recipes=replaced,
        source_owners=(guide.torso_cage.torso_owner,) + tuple(side.owner for side in guide.shoulder_frame.sides) + (head.head_owner, head.neck_owner),
        head_neck_sweeps=head_neck_sweeps,
        limb_sweeps=limb_sweeps,
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

    _validate_profile_sweep(sweep)
    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 3 or not np.all(np.isfinite(points)):
        _fail("profile sweep query points must be finite three-vectors")
    values = [
        *(_profile_span_field(points, left, right) for left, right in zip(sweep.sections, sweep.sections[1:])),
        *(_profile_transition_field(points, transition) for transition in sweep.internal_transitions),
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


def _span_field(points: np.ndarray, span: _SweptSpan) -> np.ndarray:
    start = np.asarray(span.start, dtype=np.float64)
    end = np.asarray(span.end, dtype=np.float64)
    axis = end - start
    length_sq = float(np.dot(axis, axis))
    t = np.clip(np.sum((points - start) * axis, axis=-1) / length_sq, 0.0, 1.0)
    closest = start + t[..., None] * axis
    radius = span.start_radius + (span.end_radius - span.start_radius) * t
    return np.linalg.norm(points - closest, axis=-1) - radius


def _successor_region_field(points: np.ndarray, region: SuccessorRegion, smooth_k: float) -> np.ndarray:
    values = [_loft_field(points, region.loft)]
    values.extend(_profile_sweep_field(points, item.sweep) for item in region.head_neck_sweeps)
    values.extend(_profile_sweep_field(points, item.sweep) for item in region.limb_sweeps)
    values.extend(_span_field(points, span) for span in region.shoulder_spans)
    return _baseline._smooth_union(values, smooth_k)


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
    for span in region.shoulder_spans:
        start, end = np.asarray(span.start), np.asarray(span.end)
        radius = max(span.start_radius, span.end_radius)
        mins.append(np.minimum(start, end) - radius)
        maxs.append(np.maximum(start, end) + radius)
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
    for span in region.shoulder_spans:
        bounds = (np.minimum(np.asarray(span.start), np.asarray(span.end)) - max(span.start_radius, span.end_radius), np.maximum(np.asarray(span.start), np.asarray(span.end)) + max(span.start_radius, span.end_radius))
        components.append(_Component(span.owner, span.recipe, lambda points, current=span: _span_field(points, current), bounds, True))
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
        "successor_region": {
            "torso_representation": "frame-aware-ordered-profile-sweep",
            "torso_sections_consumed": region.sections_consumed,
            "torso_section_names": list(region.section_names),
            "torso_section_owner_keys": [_baseline._address_json(owner.key) for owner in region.loft.owners],
            "shoulder_support_inputs_consumed": region.shoulder_inputs_consumed,
            "shoulder_support_input_kind": "tapered-swept-curve-spans",
            "head_neck_representation": "shared-guide-derived-profile-sweeps",
            "head_neck_sweeps_consumed": len(region.head_neck_sweeps),
            "head_neck_sweep_order": [item.recipe for item in region.head_neck_sweeps],
            "head_neck_sweep_section_counts": [len(item.sweep.sections) for item in region.head_neck_sweeps],
            "head_neck_sweep_owner_keys": [_baseline._address_json(item.owner.key) for item in region.head_neck_sweeps],
            "head_neck_source_owner_keys": [_baseline._address_json(owner.key) for owner in (region.head_neck_sweeps[0].owner, region.head_neck_sweeps[3].owner)],
            "limb_representation": "shared-guide-derived-ordered-profile-sweeps",
            "limb_sweeps_consumed": len(region.limb_sweeps),
            "limb_sweep_order": [item.chain_name for item in region.limb_sweeps],
            "limb_sweep_station_counts": [item.sections_consumed for item in region.limb_sweeps],
            "limb_sweep_station_names": [list(item.section_names) for item in region.limb_sweeps],
            "limb_sweep_section_owner_keys": [
                [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                for item in region.limb_sweeps
            ],
            "limb_sweep_endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in region.limb_sweeps],
            "limb_sweep_internal_transition_counts": [len(item.sweep.internal_transitions) for item in region.limb_sweeps],
            "limb_source_owner_keys": [
                _baseline._address_json(owner.key)
                for item in region.limb_sweeps
                for owner in item.source_owners
            ],
            "replaced_baseline_recipes": list(region.replaced_baseline_recipes),
        },
        "temporary_bridge": {
            "enabled": True,
            "consumer": "baseline-analytic-fields",
            "regions": ["paws", "tail", "limb-root-connectors", "hip-transitions"],
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


def generate(input_path: Path, output: Path, *, samples: int = DEFAULT_SAMPLES, padding: float = DEFAULT_PADDING, smooth_k: float = DEFAULT_SMOOTH_K) -> dict[str, Any]:
    if output.exists() or os.path.lexists(output):
        _fail(f"refusing to overwrite output: {output}")
    if not output.parent.is_dir():
        _fail(f"output parent must exist: {output.parent}")
    data = input_path.read_bytes()
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SuccessorPreviewError(f"input is not finite JSON: {exc}") from exc
    form = _baseline.validate_envelope(value)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        records: list[dict[str, Any]] = []
        for variant_id, descriptors, raw_variant in form.variants:
            mesh = build_variant(form, descriptors, samples=samples, padding=padding, smooth_k=smooth_k)
            variant_dir = stage / variant_id
            variant_dir.mkdir()
            ply = variant_dir / "surface.ply"
            metrics = variant_dir / "metrics.json"
            successor = variant_dir / "successor.json"
            _write_ply(ply, mesh)
            metrics.write_bytes(_canonical(mesh.metrics) + b"\n")
            successor.write_bytes(_canonical({
                "format": FORMAT,
                "variant_id": variant_id,
                "consumer_id": CONSUMER_ID,
                "successor_region_id": SUCCESSOR_REGION_ID,
                "torso": {"representation": "frame-aware-ordered-profile-sweep", "sections_consumed": mesh.representation.sections_consumed, "section_names": list(mesh.representation.section_names)},
                "shoulders": {"representation": "tapered-swept-curve-spans", "inputs_consumed": mesh.representation.shoulder_inputs_consumed, "curves": sorted({span.curve_name for span in mesh.representation.shoulder_spans})},
                "head_neck": {
                    "representation": "shared-guide-derived-profile-sweeps",
                    "sweeps_consumed": len(mesh.representation.head_neck_sweeps),
                    "sweep_order": [item.recipe for item in mesh.representation.head_neck_sweeps],
                    "section_counts": [len(item.sweep.sections) for item in mesh.representation.head_neck_sweeps],
                    "owner_keys": [_baseline._address_json(item.owner.key) for item in mesh.representation.head_neck_sweeps],
                },
                "limbs": {
                    "representation": "shared-guide-derived-ordered-profile-sweeps",
                    "sweeps_consumed": len(mesh.representation.limb_sweeps),
                    "sweep_order": [item.chain_name for item in mesh.representation.limb_sweeps],
                    "station_counts": [item.sections_consumed for item in mesh.representation.limb_sweeps],
                    "station_names": [list(item.section_names) for item in mesh.representation.limb_sweeps],
                    "section_owner_keys": [
                        [_baseline._address_json(owner.key) for owner in item.sweep.owners]
                        for item in mesh.representation.limb_sweeps
                    ],
                    "endpoint_cap_counts": [len(item.sweep.endpoint_caps) for item in mesh.representation.limb_sweeps],
                },
                "temporary_bridge": mesh.metrics["temporary_bridge"],
                "replaced_baseline_recipes": list(mesh.representation.replaced_baseline_recipes),
            }) + b"\n")
            records.append({
                "id": variant_id,
                "profile_id": raw_variant["profile_id"],
                "metrics": mesh.metrics,
                "inventory": [_sha(ply, "ply", stage), _sha(metrics, "metrics", stage), _sha(successor, "successor-consumer-sidecar", stage)],
            })
        manifest = {
            "format": FORMAT,
            "status": "success",
            "consumer_id": CONSUMER_ID,
            "source_format": _baseline.SOURCE_FORMAT,
            "source": {"sha256": hashlib.sha256(data).hexdigest(), "document": form.source["document"], "namespace": form.source["namespace"], "resource_profile_id": form.source["resource_profile_id"]},
            "generator": {"samples_per_axis": samples, "padding": padding, "smooth_k": smooth_k, "consumer_boundary": "successor torso/shoulder/head/neck and four limb chains; baseline temporary bridge for root/hip connectors, paws/feet, and tail", "production_status": "disposable exploratory proof"},
            "variants": records,
        }
        manifest_path = stage / "successor-surface-manifest.json"
        manifest_path.write_bytes(_canonical(manifest) + b"\n")
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
    parser = argparse.ArgumentParser(description="Build the disposable successor torso/shoulder/head/neck/limb surface preview")
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

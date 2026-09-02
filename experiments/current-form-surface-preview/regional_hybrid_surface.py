"""Reusable, experiment-local regional hybrid surface primitives.

This module is deliberately independent of ``surface_preview`` and
``successor_surface_preview``.  It contains only bounded scalar-field
primitives for a later adapter: piecewise regional axial masses, explicit
section routes and attachments, authority-scoped parent-targeted interface
patches, and an order-independent full-section composite.

The values are signed field values (negative means inside).  They are useful
for experiments and diagnostics; they are not an SDF, mesh, topology, or
runtime contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Iterable

import numpy as np


class RegionalHybridSurfaceError(ValueError):
    """Raised when an experiment-local primitive cannot be validated safely."""


_EPS = 1.0e-12
_FRAME_TOLERANCE = 1.0e-8
_BOUNDARY_TOLERANCE = 2.0e-7
_TIE_TOLERANCE = 1.0e-10
_ASYMMETRIC_BLEND_POLYNOMIAL = (0.5, 0.75, 0.0, -0.25)

# The interface composition constants are candidate-local algebraic controls.
# They describe only the finite authority collar and never become scalar-field
# masses or source-semantic identities.
INTERFACE_PAD = 0.75
HOCK_INTERFACE_PAD = 1.25
INTERFACE_COLLAR_FRACTION = 0.22
INTERFACE_BLEND_FRACTION = 0.15


__all__ = (
    "RegionalHybridSurfaceError",
    "RegionBasis",
    "AxialStation",
    "AxialRegion",
    "OperationTrace",
    "AxialMassChain",
    "SectionStation",
    "SectionConnection",
    "EndpointClosure",
    "SectionControl",
    "AnisotropicSectionSweep",
    "AuthorityVolume",
    "SectionAttachment",
    "ParentTargetedInterfacePatch",
    "FullSectionComposite",
)


def _fail(message: str) -> None:
    raise RegionalHybridSurfaceError(message)


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


def _vec3(value: Any, where: str) -> tuple[float, float, float]:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} must be a finite three-vector: {exc}")
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        _fail(f"{where} must be a finite three-vector")
    return tuple(float(item) for item in array)


def _positive_tuple(value: Any, length: int, where: str) -> tuple[float, ...]:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} must contain {length} positive values: {exc}")
    if array.shape != (length,) or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        _fail(f"{where} must contain {length} finite positive values")
    return tuple(float(item) for item in array)


def _unit(value: Any, where: str) -> np.ndarray:
    vector = np.asarray(_vec3(value, where), dtype=np.float64)
    length = float(np.linalg.norm(vector))
    if not math.isfinite(length) or length <= _EPS:
        _fail(f"{where} must be non-degenerate")
    return vector / length


def _validate_frame(axial: Any, lateral: Any, forward: Any, where: str) -> tuple[tuple[float, float, float], ...]:
    axial_vector = _unit(axial, f"{where}.axial_axis")
    lateral_vector = _unit(lateral, f"{where}.lateral_axis")
    forward_vector = _unit(forward, f"{where}.forward_axis")
    vectors = (axial_vector, lateral_vector, forward_vector)
    if max(
        abs(float(np.dot(vectors[first], vectors[second])))
        for first in range(3) for second in range(first + 1, 3)
    ) > _FRAME_TOLERANCE:
        _fail(f"{where} axes must be mutually orthogonal")
    if float(np.dot(np.cross(lateral_vector, axial_vector), forward_vector)) < 1.0 - _FRAME_TOLERANCE:
        _fail(f"{where} axes must use the lateral-cross-axial orientation")
    return tuple(tuple(float(item) for item in vector) for vector in vectors)


def _as_points(value: Any, where: str) -> tuple[np.ndarray, bool]:
    try:
        points = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} must contain finite three-vectors: {exc}")
    scalar = points.shape == (3,)
    if scalar:
        points = points.reshape(1, 3)
    if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)):
        _fail(f"{where} must contain finite three-vectors")
    return points, scalar


def _restore(values: np.ndarray, scalar: bool) -> float | np.ndarray:
    if scalar:
        return float(np.asarray(values).reshape(-1)[0])
    return np.asarray(values, dtype=np.float64)


def _finite_values(values: Any, expected_shape: tuple[int, ...], where: str) -> np.ndarray:
    try:
        result = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} is not numeric: {exc}")
    if result.shape != expected_shape or not np.all(np.isfinite(result)):
        _fail(f"{where} must be finite and shape {expected_shape}")
    return result


def _pchip_slopes(axis: np.ndarray, values: np.ndarray, where: str) -> np.ndarray:
    """Return shape-preserving Hermite slopes for one or more value axes."""

    axis = np.asarray(axis, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if axis.ndim != 1 or values.ndim != 2 or values.shape[0] != axis.size or axis.size < 2:
        _fail(f"{where} has invalid interpolation dimensions")
    if not np.all(np.isfinite(axis)) or not np.all(np.isfinite(values)) or np.any(np.diff(axis) <= 0.0):
        _fail(f"{where} must be finite with a strictly increasing axis")
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        spacing = np.diff(axis)
        secants = np.diff(values, axis=0) / spacing[:, None]
    if not np.all(np.isfinite(secants)):
        _fail(f"{where} has non-finite secants")
    slopes = np.zeros_like(values)
    if axis.size == 2:
        slopes[0] = secants[0]
        slopes[1] = secants[0]
        return slopes

    for index in range(1, axis.size - 1):
        previous = secants[index - 1]
        following = secants[index]
        monotone = previous * following > 0.0
        left_weight = 2.0 * spacing[index] + spacing[index - 1]
        right_weight = spacing[index] + 2.0 * spacing[index - 1]
        safe_previous = np.where(monotone, previous, 1.0)
        safe_following = np.where(monotone, following, 1.0)
        denominator = left_weight / safe_previous + right_weight / safe_following
        if np.any(monotone & (~np.isfinite(denominator) | (denominator == 0.0))):
            _fail(f"{where} has an invalid interior tangent")
        slopes[index] = np.where(monotone, (left_weight + right_weight) / denominator, 0.0)

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
        _fail(f"{where} produced non-finite slopes")
    return slopes


def _hermite_sample(axis: np.ndarray, values: np.ndarray, slopes: np.ndarray, query: np.ndarray, where: str) -> np.ndarray:
    query = np.asarray(query, dtype=np.float64)
    if not np.all(np.isfinite(query)):
        _fail(f"{where} query is non-finite")
    clipped = np.clip(query, axis[0], axis[-1])
    flat = clipped.reshape(-1)
    indices = np.clip(np.searchsorted(axis, flat, side="right") - 1, 0, axis.size - 2)
    width = axis[indices + 1] - axis[indices]
    t = (flat - axis[indices]) / width
    y0 = values[indices]
    y1 = values[indices + 1]
    m0 = slopes[indices]
    m1 = slopes[indices + 1]
    t2 = t * t
    t3 = t2 * t
    sampled = (
        (2.0 * t3 - 3.0 * t2 + 1.0)[:, None] * y0
        + (t3 - 2.0 * t2 + t)[:, None] * width[:, None] * m0
        + (-2.0 * t3 + 3.0 * t2)[:, None] * y1
        + (t3 - t2)[:, None] * width[:, None] * m1
    )
    for index, coordinate in enumerate(axis):
        exact = flat == coordinate
        if np.any(exact):
            sampled[exact] = values[index]
    if not np.all(np.isfinite(sampled)):
        _fail(f"{where} interpolation became non-finite")
    return sampled.reshape(query.shape + (values.shape[1],))


def _hermite_derivative(axis: np.ndarray, values: np.ndarray, slopes: np.ndarray, query: np.ndarray, where: str) -> np.ndarray:
    query = np.asarray(query, dtype=np.float64)
    clipped = np.clip(query, axis[0], axis[-1])
    flat = clipped.reshape(-1)
    indices = np.clip(np.searchsorted(axis, flat, side="right") - 1, 0, axis.size - 2)
    width = axis[indices + 1] - axis[indices]
    t = (flat - axis[indices]) / width
    y0 = values[indices]
    y1 = values[indices + 1]
    m0 = slopes[indices]
    m1 = slopes[indices + 1]
    derivative = (
        (6.0 * t * t - 6.0 * t)[:, None] * y0 / width[:, None]
        + (3.0 * t * t - 4.0 * t + 1.0)[:, None] * m0
        + (-6.0 * t * t + 6.0 * t)[:, None] * y1 / width[:, None]
        + (3.0 * t * t - 2.0 * t)[:, None] * m1
    )
    if not np.all(np.isfinite(derivative)):
        _fail(f"{where} derivative became non-finite")
    return derivative.reshape(query.shape + (values.shape[1],))


def _asymmetric_forward_radius(forward: np.ndarray, anterior: np.ndarray, posterior: np.ndarray, where: str) -> np.ndarray:
    anterior = np.asarray(anterior, dtype=np.float64)
    posterior = np.asarray(posterior, dtype=np.float64)
    if not np.all(np.isfinite(anterior)) or not np.all(np.isfinite(posterior)) or np.any(anterior <= 0.0) or np.any(posterior <= 0.0):
        _fail(f"{where} asymmetric radii are invalid")
    width = np.minimum(anterior, posterior)
    normalized = np.clip(np.asarray(forward, dtype=np.float64) / width, -1.0, 1.0)
    blend = np.polynomial.polynomial.polyval(normalized, _ASYMMETRIC_BLEND_POLYNOMIAL)
    result = posterior + blend * (anterior - posterior)
    if not np.all(np.isfinite(result)) or np.any(result <= 0.0):
        _fail(f"{where} asymmetric interpolation is invalid")
    return result


def _asymmetric_cap_ray_level_fraction(
    lateral: float,
    forward: float,
    axial: float,
    lateral_radius: float,
    anterior_radius: float,
    posterior_radius: float,
    axial_radius: float,
    normalized_level: float,
) -> float:
    """Solve one exact asymmetric cap constituent centre-ray level polynomial."""

    values = np.asarray(
        (lateral, forward, axial, lateral_radius, anterior_radius, posterior_radius, axial_radius),
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)) or np.any(values[3:] <= 0.0):
        _fail("asymmetric cap ray inputs are invalid")
    level = _positive_float(normalized_level, "asymmetric cap ray normalized level")
    transverse_squared = (lateral / lateral_radius) ** 2 + (axial / axial_radius) ** 2
    width = min(anterior_radius, posterior_radius)
    candidates: list[float] = []
    if abs(forward) <= _EPS:
        forward_radius = float(_asymmetric_forward_radius(
            np.asarray((0.0,)),
            np.asarray((anterior_radius,)),
            np.asarray((posterior_radius,)),
            "asymmetric cap ray",
        )[0])
        denominator = transverse_squared + (forward / forward_radius) ** 2
        if denominator <= _EPS or not math.isfinite(denominator):
            _fail("asymmetric cap ray is non-degenerate only outside its forward axis")
        candidates.append(level / math.sqrt(denominator))
    else:
        normalized_slope = forward / width
        difference = anterior_radius - posterior_radius
        radius_polynomial = np.asarray(
            (
                posterior_radius + difference * _ASYMMETRIC_BLEND_POLYNOMIAL[0],
                difference * _ASYMMETRIC_BLEND_POLYNOMIAL[1] * normalized_slope,
                0.0,
                difference * _ASYMMETRIC_BLEND_POLYNOMIAL[3] * normalized_slope**3,
            ),
            dtype=np.float64,
        )
        radius_squared = np.polynomial.polynomial.polymul(radius_polynomial, radius_polynomial)
        equation = np.polynomial.polynomial.polymul(
            np.asarray((-level**2, 0.0, transverse_squared), dtype=np.float64),
            radius_squared,
        )
        if len(equation) < 3:
            equation = np.pad(equation, (0, 3 - len(equation)))
        equation[2] += forward**2
        saturation_fraction = width / abs(forward)
        for root in np.polynomial.polynomial.polyroots(equation):
            if abs(float(root.imag)) <= 1.0e-9 and 0.0 < float(root.real) <= saturation_fraction + _FRAME_TOLERANCE:
                candidates.append(float(root.real))
        saturated_forward_radius = anterior_radius if forward > 0.0 else posterior_radius
        saturated_denominator = transverse_squared + (forward / saturated_forward_radius) ** 2
        if saturated_denominator > _EPS and math.isfinite(saturated_denominator):
            saturated = level / math.sqrt(saturated_denominator)
            if saturated >= saturation_fraction - _FRAME_TOLERANCE:
                candidates.append(saturated)

    exact: list[float] = []
    for candidate in sorted(candidates):
        forward_radius = float(_asymmetric_forward_radius(
            np.asarray((forward * candidate,)),
            np.asarray((anterior_radius,)),
            np.asarray((posterior_radius,)),
            "asymmetric cap ray root",
        )[0])
        normalized = math.sqrt(
            (lateral * candidate / lateral_radius) ** 2
            + (forward * candidate / forward_radius) ** 2
            + (axial * candidate / axial_radius) ** 2
        )
        if math.isfinite(normalized) and abs(normalized - level) <= _BOUNDARY_TOLERANCE:
            if not exact or abs(candidate - exact[-1]) > _BOUNDARY_TOLERANCE:
                exact.append(candidate)
    if len(exact) != 1:
        _fail("asymmetric cap ray must have exactly one finite positive analytic level")
    return exact[0]


@dataclass(frozen=True, slots=True)
class RegionBasis:
    """A regional cross-section basis; axial direction is region-local."""

    axial_axis: tuple[float, float, float] = (0.0, 1.0, 0.0)
    lateral_axis: tuple[float, float, float] = (1.0, 0.0, 0.0)
    forward_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)

    def __post_init__(self) -> None:
        axes = _validate_frame(self.axial_axis, self.lateral_axis, self.forward_axis, "regional basis")
        object.__setattr__(self, "axial_axis", axes[0])
        object.__setattr__(self, "lateral_axis", axes[1])
        object.__setattr__(self, "forward_axis", axes[2])


@dataclass(frozen=True, slots=True)
class AxialStation:
    """One source-independent ordered station with an asymmetric profile."""

    name: str
    position: float
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    semantic_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("axial station name must be a non-empty string")
        object.__setattr__(self, "position", _finite_float(self.position, f"station {self.name}.position"))
        object.__setattr__(self, "center", _vec3(self.center, f"station {self.name}.center"))
        object.__setattr__(self, "radii", _positive_tuple(self.radii, 3, f"station {self.name}.radii"))
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"station {self.name}.semantic_key must be a non-empty string")


@dataclass(frozen=True, slots=True)
class AxialRegion:
    """An explicit station interval with its own profile base.

    ``start_basis`` and ``end_basis`` are optional seam frames.  When given,
    the interior basis is reached through a smoothstep collar with zero frame
    derivative at both station boundaries.  This permits pelvis, abdomen and
    ribcage bases to be oriented independently while still making the shared
    station a C1 boundary when adjacent seam values/derivatives agree.
    """

    name: str
    start_index: int
    end_index: int
    basis: RegionBasis = field(default_factory=RegionBasis)
    start_basis: RegionBasis | None = None
    end_basis: RegionBasis | None = None
    semantic_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("axial region name must be a non-empty string")
        if type(self.start_index) is not int or type(self.end_index) is not int or self.start_index < 0 or self.end_index <= self.start_index:
            _fail(f"axial region {self.name} has an invalid station interval")
        for label, value in (("basis", self.basis), ("start_basis", self.start_basis), ("end_basis", self.end_basis)):
            if value is not None and not isinstance(value, RegionBasis):
                _fail(f"axial region {self.name}.{label} must be a RegionBasis")
        start_basis = self.start_basis or self.basis
        end_basis = self.end_basis or self.basis
        if not np.allclose(start_basis.axial_axis, self.basis.axial_axis, rtol=0.0, atol=_FRAME_TOLERANCE) or not np.allclose(end_basis.axial_axis, self.basis.axial_axis, rtol=0.0, atol=_FRAME_TOLERANCE):
            _fail(f"axial region {self.name} seam bases must share its axial axis")
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"axial region {self.name}.semantic_key must be a non-empty string")

    @property
    def start(self) -> int:
        return self.start_index

    @property
    def end(self) -> int:
        return self.end_index

    @property
    def first_basis(self) -> RegionBasis:
        return self.start_basis or self.basis

    @property
    def last_basis(self) -> RegionBasis:
        return self.end_basis or self.basis


@dataclass(frozen=True, slots=True)
class OperationTrace:
    """Candidate-only reconstruction record; semantic ownership is separate."""

    operator: str
    value: float
    authority_id: str | None
    blend_coefficient: float | None
    sensitivity: tuple[float, ...]
    dominance: str
    tie_state: str
    semantic_keys: tuple[str, ...]
    children: tuple["OperationTrace", ...] = ()
    parameters: tuple[tuple[str, float], ...] = ()
    parent_id: str | None = None
    child_id: str | None = None

    def __post_init__(self) -> None:
        _finite_float(self.value, "operation trace value")
        if self.authority_id is not None and (not isinstance(self.authority_id, str) or not self.authority_id):
            _fail("operation trace authority id must be non-empty when present")
        if not all(math.isfinite(float(item)) and float(item) >= 0.0 for item in self.sensitivity):
            _fail("operation trace sensitivity must be finite and non-negative")
        if self.blend_coefficient is not None and (not math.isfinite(float(self.blend_coefficient)) or not 0.0 <= float(self.blend_coefficient) <= 1.0):
            _fail("operation trace blend coefficient must be within [0, 1]")
        for label, value in (("parent", self.parent_id), ("child", self.child_id)):
            if value is not None and (not isinstance(value, str) or not value):
                _fail(f"operation trace {label} id must be non-empty when present")

    def as_dict(self) -> dict[str, Any]:
        return {
            "operator": self.operator,
            "value": self.value,
            "authority_id": self.authority_id,
            "blend_coefficient": self.blend_coefficient,
            "sensitivity": list(self.sensitivity),
            "dominance": self.dominance,
            "tie_state": self.tie_state,
            "semantic_keys": list(self.semantic_keys),
            "parameters": {key: value for key, value in self.parameters},
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "children": [child.as_dict() for child in self.children],
        }

    def reconstruct(self) -> float:
        """Reconstruct this candidate value from the recorded active tree."""

        if self.operator in {
            "leaf",
            "regional-axial-leaf",
            "regional-span-leaf",
            "axial-cap-leaf",
            "section-span-leaf",
            "section-closure-leaf",
            "section-control-leaf",
        }:
            return self.value
        if self.operator == "regional-axial-chain":
            return self.children[0].reconstruct()
        if self.operator in {
            "axial-regional-hard-min",
            "section-sweep-hard-min",
            "full-section-hard-min",
            "full-section-interface-hard-min",
        }:
            if not self.children:
                _fail(f"{self.operator} trace has no scalar leaves")
            return min(child.reconstruct() for child in self.children)
        if self.operator == "parent-targeted-interface-patch":
            if len(self.children) != 2:
                _fail("interface patch trace does not contain parent and child children")
            parent = self.children[0].reconstruct()
            child = self.children[1].reconstruct()
            radius = dict(self.parameters).get("blend_radius")
            if radius is None or self.blend_coefficient is None:
                _fail("interface patch trace is missing reconstruction parameters")
            hard = min(parent, child)
            soft, _, _ = _stable_soft_min(np.asarray((parent,)), np.asarray((child,)), radius)
            return float(hard + self.blend_coefficient * (soft[0] - hard))
        if self.operator == "full-section-interface-composite":
            if not self.children:
                _fail("full section interface composite trace has no operands")
            return min(child.reconstruct() for child in self.children)
        _fail(f"operation trace has unknown operator {self.operator!r}")


def _leaf_trace(value: float, key: str, operator: str = "leaf") -> OperationTrace:
    return OperationTrace(operator, float(value), None, None, (1.0,), "leaf", "none", (key,))


def _exact_hard_min_selection(values: Iterable[float], where: str) -> tuple[float, tuple[int, ...], tuple[float, ...]]:
    """Select exact hard-min operands; tolerance belongs nowhere in this operator."""

    values = tuple(_finite_float(value, f"{where} operand") for value in values)
    if not values:
        _fail(f"{where} has no operands")
    minimum = min(values)
    active = tuple(index for index, value in enumerate(values) if value == minimum)
    if not active:
        _fail(f"{where} could not select its minimum")
    sensitivity = tuple(1.0 / len(active) if index in active else 0.0 for index in range(len(values)))
    return minimum, active, sensitivity


def _field_evaluate(field_value: Any, points: np.ndarray, where: str) -> np.ndarray:
    evaluator = getattr(field_value, "evaluate", None)
    if evaluator is None:
        if not callable(field_value):
            _fail(f"{where} is not an evaluator")
        evaluator = field_value
    result = evaluator(points)
    try:
        array = np.asarray(result, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        _fail(f"{where} returned non-numeric values: {exc}")
    if array.shape == ():
        array = np.full(points.shape[0], float(array), dtype=np.float64)
    if array.shape != (points.shape[0],) or not np.all(np.isfinite(array)):
        _fail(f"{where} must return finite values shaped ({points.shape[0]},)")
    return array


def _field_bounds(field_value: Any, where: str) -> tuple[np.ndarray, np.ndarray] | None:
    value = getattr(field_value, "bounds", None)
    if value is None:
        return None
    value = value() if callable(value) else value
    if not isinstance(value, tuple) or len(value) != 2:
        _fail(f"{where}.bounds must be a lower/upper tuple")
    lower = np.asarray(value[0], dtype=np.float64)
    upper = np.asarray(value[1], dtype=np.float64)
    if lower.shape != (3,) or upper.shape != (3,) or not np.all(np.isfinite(np.concatenate((lower, upper)))) or np.any(upper < lower):
        _fail(f"{where}.bounds are invalid")
    return lower.copy(), upper.copy()


def _finite_difference_gradient(field_value: Any, point: np.ndarray, where: str) -> np.ndarray:
    scale = max(1.0, float(np.max(np.abs(point))))
    step = 1.0e-6 * scale
    probes = np.repeat(point.reshape(1, 3), 6, axis=0)
    for axis in range(3):
        probes[2 * axis, axis] += step
        probes[2 * axis + 1, axis] -= step
    values = _field_evaluate(field_value, probes, where)
    gradient = np.asarray([(values[2 * axis] - values[2 * axis + 1]) / (2.0 * step) for axis in range(3)])
    if not np.all(np.isfinite(gradient)):
        _fail(f"{where} gradient became non-finite")
    return gradient


def _basis_frame_at(region: AxialRegion, fraction: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate transverse bases with zero derivative at region ends."""

    fraction = np.asarray(fraction, dtype=np.float64)
    first = np.asarray(region.first_basis.lateral_axis, dtype=np.float64)
    middle = np.asarray(region.basis.lateral_axis, dtype=np.float64)
    last = np.asarray(region.last_basis.lateral_axis, dtype=np.float64)
    axial = np.asarray(region.basis.axial_axis, dtype=np.float64)
    left = np.clip(fraction * 2.0, 0.0, 1.0)
    right = np.clip((fraction - 0.5) * 2.0, 0.0, 1.0)
    left_smooth = left * left * (3.0 - 2.0 * left)
    right_smooth = right * right * (3.0 - 2.0 * right)
    lateral = np.where(
        (fraction <= 0.5)[..., None],
        first + left_smooth[..., None] * (middle - first),
        middle + right_smooth[..., None] * (last - middle),
    )
    lateral = lateral - np.sum(lateral * axial, axis=-1, keepdims=True) * axial
    lateral_norm = np.linalg.norm(lateral, axis=-1)
    if np.any(lateral_norm <= _EPS) or not np.all(np.isfinite(lateral_norm)):
        _fail(f"axial region {region.name} frame interpolation is ambiguous")
    lateral = lateral / lateral_norm[..., None]
    forward = np.cross(lateral, axial)
    forward_norm = np.linalg.norm(forward, axis=-1)
    if np.any(forward_norm <= _EPS) or not np.all(np.isfinite(forward_norm)):
        _fail(f"axial region {region.name} frame interpolation is degenerate")
    return axial, lateral, forward / forward_norm[..., None]


@dataclass(frozen=True, slots=True, init=False)
class AxialMassChain:
    """Piecewise regional asymmetric axial mass with C1 seam validation."""

    stations: tuple[AxialStation, ...]
    regions: tuple[AxialRegion, ...]
    start_cap_radius: float
    end_cap_radius: float
    _runtimes: tuple[Any, ...] = field(default=(), init=False, repr=False, compare=False)
    _bounds: tuple[np.ndarray, np.ndarray] = field(default=(np.zeros(3), np.ones(3)), init=False, repr=False, compare=False)

    def __init__(
        self,
        stations: Iterable[AxialStation],
        regions: Iterable[AxialRegion],
        start_cap_radius: float | None = None,
        end_cap_radius: float | None = None,
    ) -> None:
        station_tuple = tuple(stations)
        region_tuple = tuple(regions)
        object.__setattr__(self, "stations", station_tuple)
        object.__setattr__(self, "regions", region_tuple)
        self._validate_and_cache(start_cap_radius, end_cap_radius)

    def _validate_and_cache(self, start_cap_radius: float | None, end_cap_radius: float | None) -> None:
        if len(self.stations) < 2 or any(not isinstance(item, AxialStation) for item in self.stations):
            _fail("axial mass chain requires at least two AxialStation values")
        if len(self.regions) < 1 or any(not isinstance(item, AxialRegion) for item in self.regions):
            _fail("axial mass chain requires explicit AxialRegion intervals")
        if len({item.name for item in self.stations}) != len(self.stations):
            _fail("axial station names must be unique")
        if len({item.name for item in self.regions}) != len(self.regions):
            _fail("axial region names must be unique")
        positions = np.asarray([item.position for item in self.stations], dtype=np.float64)
        if np.any(np.diff(positions) <= 0.0):
            _fail("axial station positions must be strictly increasing")
        all_centers = np.asarray([station.center for station in self.stations], dtype=np.float64)
        all_radii = np.asarray([station.radii for station in self.stations], dtype=np.float64)
        # Derive source tangents exactly once.  Regional runtimes slice these
        # arrays so both sides of every shared station use the same Hermite
        # center and radius derivative, including uneven seven-knot layouts.
        global_center_slopes = _pchip_slopes(positions, all_centers, "axial station centers")
        global_radius_slopes = _pchip_slopes(positions, all_radii, "axial station radii")
        for index, station in enumerate(self.stations):
            if index and np.linalg.norm(np.asarray(station.center) - np.asarray(self.stations[index - 1].center)) <= _EPS:
                _fail("axial station centers must be non-degenerate")
        previous_end = None
        runtimes: list[dict[str, Any]] = []
        for region_index, region in enumerate(self.regions):
            if region.start_index >= len(self.stations) or region.end_index >= len(self.stations):
                _fail(f"axial region {region.name} is outside the station inventory")
            if previous_end is not None and region.start_index != previous_end:
                _fail("axial regions must be ordered, contiguous and non-overlapping")
            if region_index == 0 and region.start_index != 0:
                _fail("axial regions must start at station zero")
            if region_index == len(self.regions) - 1 and region.end_index != len(self.stations) - 1:
                _fail("axial regions must end at the final station")
            previous_end = region.end_index
            indices = np.arange(region.start_index, region.end_index + 1)
            local_positions = positions[indices]
            centers = all_centers[indices]
            radii = all_radii[indices]
            axis = np.asarray(region.basis.axial_axis, dtype=np.float64)
            origin = centers[0] - local_positions[0] * axis
            projected = np.sum((centers - origin) * axis, axis=1)
            if not np.allclose(projected, local_positions, rtol=0.0, atol=_FRAME_TOLERANCE):
                _fail(f"axial region {region.name} stations do not follow its axial basis")
            center_slopes = global_center_slopes[indices]
            radius_slopes = global_radius_slopes[indices]
            runtimes.append({
                "region": region,
                "station_objects": tuple(self.stations[index] for index in indices),
                "indices": indices,
                "positions": local_positions,
                "centers": centers,
                "radii": radii,
                "center_slopes": center_slopes,
                "radius_slopes": radius_slopes,
                "origin": origin,
            })
        for left, right in zip(runtimes, runtimes[1:]):
            if left["indices"][-1] != right["indices"][0]:
                _fail("axial regions have an invalid shared boundary")
            boundary = int(left["indices"][-1])
            if not np.allclose(left["centers"][-1], right["centers"][0], rtol=0.0, atol=_FRAME_TOLERANCE):
                _fail(f"axial region boundary at station {boundary} has mismatched centers")
            if not np.allclose(left["center_slopes"][-1], right["center_slopes"][0], rtol=0.0, atol=_FRAME_TOLERANCE):
                _fail(f"axial region boundary at station {boundary} lacks a shared C1 center derivative")
            left_basis = left["region"].last_basis
            right_basis = right["region"].first_basis
            if not np.allclose(left_basis.axial_axis, right_basis.axial_axis, rtol=0.0, atol=_FRAME_TOLERANCE) or not np.allclose(left_basis.lateral_axis, right_basis.lateral_axis, rtol=0.0, atol=_FRAME_TOLERANCE):
                _fail(f"axial region boundary at station {boundary} lacks a shared seam frame")
            if not np.allclose(left["radii"][-1], right["radii"][0], rtol=0.0, atol=_FRAME_TOLERANCE) or not np.allclose(left["radius_slopes"][-1], right["radius_slopes"][0], rtol=0.0, atol=_FRAME_TOLERANCE):
                _fail(f"axial region boundary at station {boundary} lacks shared C1 radius values/derivatives")
        start_radii = self.stations[0].radii
        end_radii = self.stations[-1].radii
        start_cap = min(start_radii) if start_cap_radius is None else _positive_float(start_cap_radius, "axial start cap radius")
        end_cap = min(end_radii) if end_cap_radius is None else _positive_float(end_cap_radius, "axial end cap radius")
        object.__setattr__(self, "start_cap_radius", start_cap)
        object.__setattr__(self, "end_cap_radius", end_cap)
        object.__setattr__(self, "_runtimes", tuple(runtimes))
        object.__setattr__(self, "_bounds", self._compute_bounds(runtimes))

    def _compute_bounds(self, runtimes: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        lowers = []
        uppers = []
        for runtime in runtimes:
            centers = runtime["centers"]
            radius = float(np.max(runtime["radii"]))
            lowers.append(np.min(centers, axis=0) - radius)
            uppers.append(np.max(centers, axis=0) + radius)
        first = self.stations[0]
        last = self.stations[-1]
        for station, cap_radius, region in ((first, self.start_cap_radius, self.regions[0]), (last, self.end_cap_radius, self.regions[-1])):
            center = np.asarray(station.center)
            basis = region.first_basis if station is first else region.last_basis
            extent = (
                np.abs(np.asarray(basis.lateral_axis)) * station.radii[0]
                + np.abs(np.asarray(basis.forward_axis)) * max(station.radii[1], station.radii[2])
                + np.abs(np.asarray(basis.axial_axis)) * cap_radius
            )
            lowers.append(center - extent)
            uppers.append(center + extent)
        return np.min(np.stack(lowers), axis=0), np.max(np.stack(uppers), axis=0)

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self._bounds[0].copy(), self._bounds[1].copy()

    @property
    def field(self) -> Callable[[Any], float | np.ndarray]:
        return self.evaluate

    def _region_value(self, points: np.ndarray, runtime: dict[str, Any]) -> np.ndarray:
        positions = runtime["positions"]
        region = runtime["region"]
        axis = np.asarray(region.basis.axial_axis)
        origin = runtime["origin"]
        query = np.sum((points - origin) * axis, axis=-1)
        clipped = np.clip(query, positions[0], positions[-1])
        center = _hermite_sample(positions, runtime["centers"], runtime["center_slopes"], clipped, f"axial region {region.name} center")
        center = center - np.sum((center - origin) * axis, axis=-1, keepdims=True) * axis + origin + clipped[..., None] * axis
        radii = _hermite_sample(positions, runtime["radii"], runtime["radius_slopes"], clipped, f"axial region {region.name} radii")
        fraction = np.divide(clipped - positions[0], positions[-1] - positions[0])
        _, lateral, forward_axis = _basis_frame_at(region, fraction)
        offset = points - center
        lateral_coordinate = np.sum(offset * lateral, axis=-1)
        forward_coordinate = np.sum(offset * forward_axis, axis=-1)
        forward_radius = _asymmetric_forward_radius(forward_coordinate, radii[..., 1], radii[..., 2], f"axial region {region.name}")
        normalized = np.sqrt((lateral_coordinate / radii[..., 0]) ** 2 + (forward_coordinate / forward_radius) ** 2)
        value = (normalized - 1.0) * radii[..., 0]
        inside = (query >= positions[0]) & (query <= positions[-1])
        return np.where(inside, value, np.inf)

    def _cap_normalized_and_scale(
        self,
        points: np.ndarray,
        endpoint: AxialStation,
        basis: RegionBasis,
        cap_radius: float,
    ) -> tuple[np.ndarray, float]:
        center = np.asarray(endpoint.center)
        offset = points - center
        lateral = offset @ np.asarray(basis.lateral_axis)
        forward = offset @ np.asarray(basis.forward_axis)
        axial = offset @ np.asarray(basis.axial_axis)
        forward_radius = _asymmetric_forward_radius(
            forward,
            np.full(points.shape[0], endpoint.radii[1]),
            np.full(points.shape[0], endpoint.radii[2]),
            "axial cap",
        )
        normalized = np.sqrt((lateral / endpoint.radii[0]) ** 2 + (forward / forward_radius) ** 2 + (axial / cap_radius) ** 2)
        scale = min(endpoint.radii[0], endpoint.radii[1], endpoint.radii[2], cap_radius)
        if not np.all(np.isfinite(normalized)) or not math.isfinite(scale) or scale <= 0.0:
            _fail("axial cap constituent became invalid")
        return normalized, scale

    def _cap_value(self, points: np.ndarray, endpoint: AxialStation, region: AxialRegion, cap_radius: float, lower: bool) -> np.ndarray:
        basis = region.first_basis if lower else region.last_basis
        normalized, scale = self._cap_normalized_and_scale(points, endpoint, basis, cap_radius)
        return (normalized - 1.0) * scale

    def _endpoint_constituent(
        self,
        station: AxialStation,
        region: AxialRegion,
        basis: RegionBasis,
        lower: bool,
    ) -> "_EndpointAxialConstituent":
        """Bind one exact live endpoint cap constituent by object identity."""

        if type(lower) is not bool:
            _fail("endpoint constituent lower selector must be boolean")
        endpoint_index = 0 if lower else -1
        runtime = self._runtimes[endpoint_index]
        expected_station = self.stations[endpoint_index]
        expected_region = self.regions[endpoint_index]
        runtime_station_index = 0 if lower else -1
        expected_source_index = 0 if lower else len(self.stations) - 1
        expected_basis = expected_region.first_basis if lower else expected_region.last_basis
        endpoint_name = "initial" if lower else "terminal"
        if station is not expected_station:
            _fail(f"{endpoint_name} constituent station must be the exact live {endpoint_name} station object")
        if region is not expected_region or runtime["region"] is not region:
            _fail(f"{endpoint_name} constituent region must be the exact live {endpoint_name} region object")
        if (
            runtime["station_objects"][runtime_station_index] is not station
            or int(runtime["indices"][runtime_station_index]) != expected_source_index
        ):
            _fail(f"{endpoint_name} constituent station is not consumed by the live {endpoint_name} region")
        if basis is not expected_basis:
            _fail(f"{endpoint_name} constituent basis must be the exact live {endpoint_name} region basis object")
        return _EndpointAxialConstituent(self, station, region, basis, lower)

    def _initial_constituent(
        self,
        station: AxialStation,
        region: AxialRegion,
        basis: RegionBasis,
    ) -> "_EndpointAxialConstituent":
        return self._endpoint_constituent(station, region, basis, True)

    def _terminal_constituent(
        self,
        station: AxialStation,
        region: AxialRegion,
        basis: RegionBasis,
    ) -> "_EndpointAxialConstituent":
        return self._endpoint_constituent(station, region, basis, False)

    def _base_evaluate(self, points: np.ndarray) -> np.ndarray:
        values = np.stack([self._region_value(points, runtime) for runtime in self._runtimes], axis=0)
        result = np.min(values, axis=0)
        first_region = self.regions[0]
        last_region = self.regions[-1]
        first_position = self.stations[0].position
        last_position = self.stations[-1].position
        first_axis = np.asarray(first_region.basis.axial_axis)
        last_axis = np.asarray(last_region.basis.axial_axis)
        first_origin = self._runtimes[0]["origin"]
        last_origin = self._runtimes[-1]["origin"]
        first_query = np.sum((points - first_origin) * first_axis, axis=-1)
        last_query = np.sum((points - last_origin) * last_axis, axis=-1)
        lower_cap = self._cap_value(points, self.stations[0], first_region, self.start_cap_radius, True)
        upper_cap = self._cap_value(points, self.stations[-1], last_region, self.end_cap_radius, False)
        result = np.where(first_query < first_position, lower_cap, result)
        result = np.where(last_query > last_position, upper_cap, result)
        if not np.all(np.isfinite(result)):
            _fail("axial mass chain evaluation became non-finite")
        return result

    def evaluate(self, points: Any) -> float | np.ndarray:
        query, scalar = _as_points(points, "axial mass chain query")
        base = self._base_evaluate(query)
        if not np.all(np.isfinite(base)):
            _fail("axial mass chain final evaluation became non-finite")
        return _restore(base, scalar)

    scalar_evaluator = evaluate

    def gradient(self, point: Any) -> np.ndarray:
        query, scalar = _as_points(point, "axial gradient query")
        if not scalar:
            return np.stack([_finite_difference_gradient(self, item, "axial mass chain") for item in query], axis=0)
        return _finite_difference_gradient(self, query[0], "axial mass chain")

    def value_and_gradient(self, point: Any) -> tuple[float, np.ndarray]:
        query, scalar = _as_points(point, "axial value and gradient query")
        if not scalar:
            _fail("value_and_gradient requires one point")
        return float(self.evaluate(query[0])), self.gradient(query[0])

    def _regional_leaf_trace(self, point: np.ndarray, region_index: int) -> OperationTrace:
        runtime = self._runtimes[region_index]
        region = runtime["region"]
        axis = np.asarray(region.basis.axial_axis)
        parameter = float(np.dot(point - runtime["origin"], axis))
        positions = runtime["positions"]
        clipped = float(np.clip(parameter, positions[0], positions[-1]))
        local_span = int(np.clip(np.searchsorted(positions, clipped, side="right") - 1, 0, len(positions) - 2))
        global_span = int(runtime["indices"][local_span])
        support_start = max(0, global_span - 1)
        support_end = min(len(self.stations) - 1, global_span + 2)
        station_keys = tuple(
            self.stations[index].semantic_key or f"station:{self.stations[index].name}"
            for index in range(support_start, support_end + 1)
        )
        region_key = region.semantic_key or f"region:{region.name}"
        value = float(self._region_value(point.reshape(1, 3), runtime)[0])
        return OperationTrace(
            "regional-span-leaf",
            value,
            None,
            None,
            (1.0,),
            f"{region.name}:{self.stations[global_span].name}->{self.stations[global_span + 1].name}",
            "none",
            station_keys + (region_key,),
            (),
            (("region_index", float(region_index)), ("span_index", float(global_span)), ("parameter", clipped)),
        )

    def _cap_leaf_trace(self, point: np.ndarray, lower: bool) -> OperationTrace:
        station = self.stations[0] if lower else self.stations[-1]
        region = self.regions[0] if lower else self.regions[-1]
        cap_radius = self.start_cap_radius if lower else self.end_cap_radius
        value = float(self._cap_value(point.reshape(1, 3), station, region, cap_radius, lower)[0])
        station_key = station.semantic_key or f"station:{station.name}"
        region_key = region.semantic_key or f"region:{region.name}"
        return OperationTrace(
            "axial-cap-leaf",
            value,
            None,
            None,
            (1.0,),
            "start-cap" if lower else "end-cap",
            "none",
            (station_key, region_key),
            (),
            (("cap_end", 0.0 if lower else 1.0),),
        )

    def _base_operation_trace(self, point: np.ndarray) -> OperationTrace:
        first_region = self.regions[0]
        last_region = self.regions[-1]
        first_query = float(np.dot(point - self._runtimes[0]["origin"], np.asarray(first_region.basis.axial_axis)))
        last_query = float(np.dot(point - self._runtimes[-1]["origin"], np.asarray(last_region.basis.axial_axis)))
        if first_query < self.stations[0].position:
            return self._cap_leaf_trace(point, True)
        if last_query > self.stations[-1].position:
            return self._cap_leaf_trace(point, False)

        children = tuple(
            self._regional_leaf_trace(point, index)
            for index, runtime in enumerate(self._runtimes)
            if math.isfinite(float(self._region_value(point.reshape(1, 3), runtime)[0]))
        )
        if not children:
            _fail("axial mass chain has no finite regional scalar leaf")
        minimum, active, sensitivity = _exact_hard_min_selection(
            (child.value for child in children),
            "axial regional hard-min",
        )
        tie = len(active) > 1
        dominance = "tie" if tie else children[active[0]].dominance
        semantic_keys = tuple(dict.fromkeys(key for child in children for key in child.semantic_keys))
        return OperationTrace(
            "axial-regional-hard-min",
            minimum,
            None,
            None,
            sensitivity,
            dominance,
            "tie" if tie else "ordered",
            semantic_keys,
            children,
            tuple((f"region_{index}_value", child.value) for index, child in enumerate(children)),
        )

    def source_provenance(self, point: Any) -> dict[str, Any]:
        """Report selected source leaves; these are not geometric weights."""

        query, scalar = _as_points(point, "axial source provenance query")
        if not scalar:
            return {"points": [self.source_provenance(item) for item in query]}
        trace = self._base_operation_trace(query[0])
        if trace.operator == "axial-regional-hard-min":
            leaves = tuple(child for child, sensitivity in zip(trace.children, trace.sensitivity) if sensitivity > 0.0)
        else:
            leaves = (trace,)
        return {
            "diagnostic_kind": "source-provenance",
            "geometric_influence": False,
            "selected_leaves": tuple(leaf.dominance for leaf in leaves),
            "tie_state": trace.tie_state,
            "source_semantic_keys": tuple(dict.fromkeys(key for leaf in leaves for key in leaf.semantic_keys)),
            "leaf_parameters": tuple(dict(leaf.parameters) for leaf in leaves),
        }

    def contribution_report(self, point: Any) -> dict[str, Any]:
        """Backward-compatible name for source provenance, never influence."""

        return self.source_provenance(point)

    contributors = source_provenance

    def operation_trace(self, point: Any) -> OperationTrace | tuple[OperationTrace, ...]:
        query, scalar = _as_points(point, "axial trace query")
        if not scalar:
            return tuple(self.operation_trace(item) for item in query)  # type: ignore[return-value]
        point_value = query[0]
        base_trace = self._base_operation_trace(point_value)
        base_value = base_trace.value
        return OperationTrace("regional-axial-chain", base_value, None, None, (1.0,), base_trace.dominance, base_trace.tie_state, base_trace.semantic_keys, (base_trace,))


@dataclass(frozen=True, slots=True)
class _EndpointAxialConstituent:
    """Identity-bound endpoint cap ellipsoid used by the live axial chain."""

    chain: AxialMassChain
    station: AxialStation
    region: AxialRegion
    basis: RegionBasis
    lower: bool

    @property
    def cap_radius(self) -> float:
        return self.chain.start_cap_radius if self.lower else self.chain.end_cap_radius

    @property
    def endpoint_name(self) -> str:
        return "initial" if self.lower else "terminal"

    @property
    def field_scale(self) -> float:
        _, scale = self.chain._cap_normalized_and_scale(
            np.asarray(self.station.center, dtype=np.float64).reshape(1, 3),
            self.station,
            self.basis,
            self.cap_radius,
        )
        return scale

    def evaluate(self, points: Any) -> float | np.ndarray:
        query, scalar = _as_points(points, "endpoint axial constituent query")
        values = self.chain._cap_value(
            query,
            self.station,
            self.region,
            self.cap_radius,
            self.lower,
        )
        return _restore(values, scalar)

    def operation_trace(self, point: Any) -> OperationTrace:
        query, scalar = _as_points(point, "endpoint axial constituent trace query")
        if not scalar:
            _fail("endpoint axial constituent trace requires one point")
        return self.chain._cap_leaf_trace(query[0], self.lower)

    def analytic_ray_boundary_and_interior(
        self,
        toward: Any,
        interior_depth: float,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Solve one centre ray using the constituent's exact normalized scale."""

        boundary, boundary_fraction = self._analytic_ray_level(toward, 1.0)
        mu = _positive_float(interior_depth, "terminal constituent interior depth")
        interior_normalized = 1.0 - mu / self.field_scale
        if not math.isfinite(interior_normalized) or interior_normalized <= 0.0:
            _fail(f"{self.endpoint_name} constituent interior normalized level must be finite and positive")
        interior, interior_fraction = self._analytic_ray_level(toward, interior_normalized)
        rho = interior_fraction / boundary_fraction
        if not math.isfinite(rho) or not 0.0 < rho < 1.0:
            _fail(f"{self.endpoint_name} constituent interior fraction rho must be finite and strictly between zero and one")
        interior_value = float(self.evaluate(interior))
        if abs(interior_value + mu) > _BOUNDARY_TOLERANCE:
            _fail(f"{self.endpoint_name} constituent analytic interior did not reconstruct negative mu")
        return boundary, interior, rho

    def analytic_ray_boundary(self, toward: Any) -> np.ndarray:
        """Solve this live terminal ellipsoid's zero boundary in closed form."""

        boundary, _ = self._analytic_ray_level(toward, 1.0)
        boundary_value = float(self.evaluate(boundary))
        if abs(boundary_value) > _BOUNDARY_TOLERANCE:
            _fail(f"{self.endpoint_name} constituent analytic boundary did not reconstruct zero")
        return boundary

    def _analytic_ray_level(self, toward: Any, normalized_level: float) -> tuple[np.ndarray, float]:
        """Return a point and ray fraction from the shared exact polynomial."""

        origin = np.asarray(self.station.center, dtype=np.float64)
        toward_array = np.asarray(_vec3(toward, f"{self.endpoint_name} constituent ray target"), dtype=np.float64)
        delta = toward_array - origin
        length = float(np.linalg.norm(delta))
        if not math.isfinite(length) or length <= _EPS:
            _fail(f"{self.endpoint_name} constituent ray must be non-degenerate")
        axial_progress = float(np.dot(delta, np.asarray(self.basis.axial_axis, dtype=np.float64)))
        enters_live_domain = axial_progress < -_EPS if self.lower else axial_progress > _EPS
        if not math.isfinite(axial_progress) or not enters_live_domain:
            _fail(f"{self.endpoint_name} constituent ray must enter the live {self.endpoint_name} cap domain")
        ray_fraction = _asymmetric_cap_ray_level_fraction(
            float(np.dot(delta, np.asarray(self.basis.lateral_axis, dtype=np.float64))),
            float(np.dot(delta, np.asarray(self.basis.forward_axis, dtype=np.float64))),
            axial_progress,
            self.station.radii[0],
            self.station.radii[1],
            self.station.radii[2],
            self.cap_radius,
            normalized_level,
        )
        return origin + ray_fraction * delta, ray_fraction


@dataclass(frozen=True, slots=True)
class SectionStation:
    """One source-bound, fully anisotropic station in a regional route."""

    name: str
    position: float
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    semantic_key: str | None = None
    source_key: str | None = None
    source_index: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("section station name must be a non-empty string")
        object.__setattr__(self, "position", _finite_float(self.position, f"section station {self.name}.position"))
        object.__setattr__(self, "center", _vec3(self.center, f"section station {self.name}.center"))
        object.__setattr__(self, "radii", _positive_tuple(self.radii, 3, f"section station {self.name}.radii"))
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"section station {self.name}.semantic_key must be non-empty when present")
        if self.source_key is not None and (not isinstance(self.source_key, str) or not self.source_key):
            _fail(f"section station {self.name}.source_key must be non-empty when present")
        if self.source_index is not None and (type(self.source_index) is not int or self.source_index < 0):
            _fail(f"section station {self.name}.source_index must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class SectionConnection:
    """One directed route edge between two exact shared section stations."""

    name: str
    from_section_index: int
    to_section_index: int
    route: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("section connection name must be a non-empty string")
        if type(self.from_section_index) is not int or type(self.to_section_index) is not int:
            _fail(f"section connection {self.name} indices must be integers")
        if self.from_section_index < 0 or self.to_section_index <= self.from_section_index:
            _fail(f"section connection {self.name} must move forward through ordered stations")
        if not isinstance(self.route, str) or not self.route:
            _fail(f"section connection {self.name}.route must be non-empty")

    @property
    def from_index(self) -> int:
        return self.from_section_index

    @property
    def to_index(self) -> int:
        return self.to_section_index


@dataclass(frozen=True, slots=True)
class EndpointClosure:
    """A finite source-derived terminal mass for one regional route."""

    name: str
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    semantic_key: str | None = None
    source_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("endpoint closure name must be a non-empty string")
        object.__setattr__(self, "center", _vec3(self.center, f"endpoint closure {self.name}.center"))
        object.__setattr__(self, "radii", _positive_tuple(self.radii, 3, f"endpoint closure {self.name}.radii"))
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"endpoint closure {self.name}.semantic_key must be non-empty when present")
        if self.source_key is not None and (not isinstance(self.source_key, str) or not self.source_key):
            _fail(f"endpoint closure {self.name}.source_key must be non-empty when present")


@dataclass(frozen=True, slots=True)
class SectionControl:
    """A source-bound local control mass used by a composed route."""

    name: str
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    semantic_key: str | None = None
    source_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("section control name must be a non-empty string")
        object.__setattr__(self, "center", _vec3(self.center, f"section control {self.name}.center"))
        object.__setattr__(self, "radii", _positive_tuple(self.radii, 3, f"section control {self.name}.radii"))
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"section control {self.name}.semantic_key must be non-empty when present")
        if self.source_key is not None and (not isinstance(self.source_key, str) or not self.source_key):
            _fail(f"section control {self.name}.source_key must be non-empty when present")

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        center = np.asarray(self.center)
        radii = np.asarray(self.radii)
        return center - radii, center + radii

    def evaluate(self, points: Any) -> float | np.ndarray:
        query, scalar = _as_points(points, f"section control {self.name} query")
        return _restore(_section_ellipsoid_value(query, self.center, self.radii, f"section control {self.name}"), scalar)

    scalar_evaluator = evaluate

    def operation_trace(self, point: Any) -> OperationTrace | tuple[OperationTrace, ...]:
        query, scalar = _as_points(point, f"section control {self.name} trace query")
        if not scalar:
            return tuple(self.operation_trace(item) for item in query)  # type: ignore[return-value]
        value = float(self.evaluate(query[0]))
        key = self.semantic_key or self.source_key or f"control:{self.name}"
        return _leaf_trace(value, key, "section-control-leaf")

    trace = operation_trace

    def source_provenance(self, point: Any) -> dict[str, Any]:
        trace = self.operation_trace(point)
        if not isinstance(trace, OperationTrace):
            _fail(f"section control {self.name} trace returned an invalid record")
        return {
            "diagnostic_kind": "source-provenance",
            "geometric_influence": False,
            "selected_leaves": (self.name,),
            "source_semantic_keys": trace.semantic_keys,
        }


def _section_ellipsoid_value(points: np.ndarray, center: Any, radii: Any, where: str) -> np.ndarray:
    center_array = np.asarray(_vec3(center, f"{where}.center"), dtype=np.float64)
    radii_array = np.asarray(_positive_tuple(radii, 3, f"{where}.radii"), dtype=np.float64)
    normalized = np.sqrt(np.sum(((points - center_array) / radii_array) ** 2, axis=-1))
    values = (normalized - 1.0) * float(np.min(radii_array))
    if not np.all(np.isfinite(values)):
        _fail(f"{where} evaluation became non-finite")
    return values


@dataclass(frozen=True, slots=True, init=False)
class AnisotropicSectionSweep:
    """Deterministic linear full-section sweeps over an explicit route graph.

    A connection is an anisotropic capsule whose section radii are linearly
    interpolated between the exact shared stations.  The representation keeps
    all three source axes, uses the same station object at shared interfaces,
    and closes only with explicit finite endpoint controls.
    """

    sections: tuple[SectionStation, ...]
    connections: tuple[SectionConnection, ...]
    endpoint_closures: tuple[EndpointClosure, ...]
    route_name: str
    _bounds: tuple[np.ndarray, np.ndarray] = field(default=(np.zeros(3), np.ones(3)), init=False, repr=False, compare=False)

    def __init__(
        self,
        sections: Iterable[SectionStation],
        connections: Iterable[SectionConnection],
        endpoint_closures: Iterable[EndpointClosure] = (),
        route_name: str = "regional-section-route",
        *,
        closures: Iterable[EndpointClosure] | None = None,
    ) -> None:
        if closures is not None:
            endpoint_tuple = tuple(endpoint_closures)
            closure_tuple = tuple(closures)
            if endpoint_tuple and endpoint_tuple != closure_tuple:
                _fail("section sweep received conflicting endpoint closures")
            endpoint_tuple = closure_tuple
        else:
            endpoint_tuple = tuple(endpoint_closures)
        object.__setattr__(self, "sections", tuple(sections))
        object.__setattr__(self, "connections", tuple(connections))
        object.__setattr__(self, "endpoint_closures", endpoint_tuple)
        if not isinstance(route_name, str) or not route_name:
            _fail("section sweep route_name must be non-empty")
        object.__setattr__(self, "route_name", route_name)
        self._validate_and_cache()

    def _validate_and_cache(self) -> None:
        if len(self.sections) < 2 or any(not isinstance(item, SectionStation) for item in self.sections):
            _fail("section sweep requires at least two SectionStation values")
        if not self.connections or any(not isinstance(item, SectionConnection) for item in self.connections):
            _fail(f"section sweep {self.route_name} requires explicit SectionConnection values")
        if not self.endpoint_closures or any(not isinstance(item, EndpointClosure) for item in self.endpoint_closures):
            _fail(f"section sweep {self.route_name} requires explicit endpoint closures")
        if len({item.name for item in self.sections}) != len(self.sections):
            _fail(f"section sweep {self.route_name} section names must be unique")
        if len({item.name for item in self.connections}) != len(self.connections):
            _fail(f"section sweep {self.route_name} connection names must be unique")
        if len({item.name for item in self.endpoint_closures}) != len(self.endpoint_closures):
            _fail(f"section sweep {self.route_name} endpoint closure names must be unique")
        positions = np.asarray([item.position for item in self.sections], dtype=np.float64)
        if np.any(np.diff(positions) <= 0.0):
            _fail(f"section sweep {self.route_name} station positions must be strictly increasing")

        edge_keys: set[tuple[int, int]] = set()
        degrees = [0] * len(self.sections)
        bounds: list[tuple[np.ndarray, np.ndarray]] = []
        for connection in self.connections:
            if connection.from_section_index >= len(self.sections) or connection.to_section_index >= len(self.sections):
                _fail(f"section sweep {self.route_name} connection {connection.name} is outside the station inventory")
            edge_key = (connection.from_section_index, connection.to_section_index)
            if edge_key in edge_keys:
                _fail(f"section sweep {self.route_name} consumes connection {connection.name} more than once")
            edge_keys.add(edge_key)
            degrees[connection.from_section_index] += 1
            degrees[connection.to_section_index] += 1
            first = self.sections[connection.from_section_index]
            second = self.sections[connection.to_section_index]
            delta = np.asarray(second.center) - np.asarray(first.center)
            if not np.all(np.isfinite(delta)) or float(np.linalg.norm(delta)) <= _EPS:
                _fail(f"section sweep {self.route_name} connection {connection.name} has a degenerate centerline")
            lower = np.minimum(np.asarray(first.center), np.asarray(second.center)) - np.maximum(np.asarray(first.radii), np.asarray(second.radii))
            upper = np.maximum(np.asarray(first.center), np.asarray(second.center)) + np.maximum(np.asarray(first.radii), np.asarray(second.radii))
            bounds.append((lower, upper))
        if any(degree == 0 for degree in degrees):
            _fail(f"section sweep {self.route_name} has an unconnected station")
        adjacency = [set() for _ in self.sections]
        for first, second in edge_keys:
            adjacency[first].add(second)
            adjacency[second].add(first)
        pending = [0]
        visited: set[int] = set()
        while pending:
            section_index = pending.pop()
            if section_index in visited:
                continue
            visited.add(section_index)
            pending.extend(adjacency[section_index] - visited)
        if len(visited) != len(self.sections):
            _fail(f"section sweep {self.route_name} connection graph must be connected")
        for closure in self.endpoint_closures:
            center = np.asarray(closure.center)
            radii = np.asarray(closure.radii)
            bounds.append((center - radii, center + radii))
        lower = np.min(np.stack([item[0] for item in bounds]), axis=0)
        upper = np.max(np.stack([item[1] for item in bounds]), axis=0)
        if not np.all(np.isfinite(np.concatenate((lower, upper)))) or np.any(upper <= lower):
            _fail(f"section sweep {self.route_name} bounds are invalid")
        object.__setattr__(self, "_bounds", (lower, upper))

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self._bounds[0].copy(), self._bounds[1].copy()

    @property
    def closures(self) -> tuple[EndpointClosure, ...]:
        return self.endpoint_closures

    @property
    def field(self) -> Callable[[Any], float | np.ndarray]:
        return self.evaluate

    def _connection_value(self, points: np.ndarray, connection: SectionConnection) -> np.ndarray:
        first = self.sections[connection.from_section_index]
        second = self.sections[connection.to_section_index]
        first_center = np.asarray(first.center, dtype=np.float64)
        delta = np.asarray(second.center, dtype=np.float64) - first_center
        denominator = float(np.dot(delta, delta))
        fraction = np.clip(np.sum((points - first_center) * delta, axis=-1) / denominator, 0.0, 1.0)
        center = first_center + fraction[..., None] * delta
        radii = np.asarray(first.radii) + fraction[..., None] * (np.asarray(second.radii) - np.asarray(first.radii))
        normalized = np.sqrt(np.sum(((points - center) / radii) ** 2, axis=-1))
        values = (normalized - 1.0) * np.min(radii, axis=-1)
        if not np.all(np.isfinite(values)):
            _fail(f"section sweep {self.route_name} connection {connection.name} evaluation became non-finite")
        return values

    def _closure_value(self, points: np.ndarray, closure: EndpointClosure) -> np.ndarray:
        return _section_ellipsoid_value(points, closure.center, closure.radii, f"section closure {closure.name}")

    def evaluate(self, points: Any) -> float | np.ndarray:
        query, scalar = _as_points(points, f"section sweep {self.route_name} query")
        values = [self._connection_value(query, item) for item in self.connections]
        values.extend(self._closure_value(query, item) for item in self.endpoint_closures)
        result = np.min(np.stack(values, axis=0), axis=0)
        if not np.all(np.isfinite(result)):
            _fail(f"section sweep {self.route_name} final evaluation became non-finite")
        return _restore(result, scalar)

    scalar_evaluator = evaluate

    def gradient(self, point: Any) -> np.ndarray:
        query, scalar = _as_points(point, f"section sweep {self.route_name} gradient query")
        if not scalar:
            return np.stack([_finite_difference_gradient(self, item, f"section sweep {self.route_name}") for item in query], axis=0)
        return _finite_difference_gradient(self, query[0], f"section sweep {self.route_name}")

    def value_and_gradient(self, point: Any) -> tuple[float, np.ndarray]:
        query, scalar = _as_points(point, f"section sweep {self.route_name} value and gradient query")
        if not scalar:
            _fail("value_and_gradient requires one point")
        return float(self.evaluate(query[0])), self.gradient(query[0])

    def _span_leaf_trace(self, point: np.ndarray, connection: SectionConnection) -> OperationTrace:
        first = self.sections[connection.from_section_index]
        second = self.sections[connection.to_section_index]
        value = float(self._connection_value(point.reshape(1, 3), connection)[0])
        keys = tuple(dict.fromkeys(
            item
            for item in (
                first.semantic_key or first.source_key or f"section:{first.name}",
                second.semantic_key or second.source_key or f"section:{second.name}",
                connection.route,
            )
            if item
        ))
        return OperationTrace(
            "section-span-leaf",
            value,
            None,
            None,
            (1.0,),
            connection.name,
            "none",
            keys,
            (),
            (("from_section_index", float(connection.from_section_index)), ("to_section_index", float(connection.to_section_index))),
        )

    def _closure_leaf_trace(self, point: np.ndarray, closure: EndpointClosure) -> OperationTrace:
        value = float(self._closure_value(point.reshape(1, 3), closure)[0])
        key = closure.semantic_key or closure.source_key or f"closure:{closure.name}"
        return OperationTrace("section-closure-leaf", value, None, None, (1.0,), closure.name, "none", (key,), (), ())

    def operation_trace(self, point: Any) -> OperationTrace | tuple[OperationTrace, ...]:
        query, scalar = _as_points(point, f"section sweep {self.route_name} trace query")
        if not scalar:
            return tuple(self.operation_trace(item) for item in query)  # type: ignore[return-value]
        children = tuple(self._span_leaf_trace(query[0], item) for item in self.connections)
        children += tuple(self._closure_leaf_trace(query[0], item) for item in self.endpoint_closures)
        minimum, active, sensitivity = _exact_hard_min_selection(
            (child.value for child in children),
            f"section sweep {self.route_name} hard-min",
        )
        tie = len(active) > 1
        return OperationTrace(
            "section-sweep-hard-min",
            minimum,
            None,
            None,
            sensitivity,
            "tie" if tie else children[active[0]].dominance,
            "tie" if tie else "ordered",
            tuple(dict.fromkeys(key for child in children for key in child.semantic_keys)),
            children,
            (("connection_count", float(len(self.connections))), ("closure_count", float(len(self.endpoint_closures)))),
        )

    trace = operation_trace

    def source_provenance(self, point: Any) -> dict[str, Any]:
        query, scalar = _as_points(point, f"section sweep {self.route_name} provenance query")
        if not scalar:
            return {"points": [self.source_provenance(item) for item in query]}
        trace = self.operation_trace(query[0])
        if not isinstance(trace, OperationTrace):
            _fail(f"section sweep {self.route_name} trace returned an invalid record")
        leaves = tuple(child for child, sensitivity in zip(trace.children, trace.sensitivity) if sensitivity > 0.0)
        return {
            "diagnostic_kind": "source-provenance",
            "geometric_influence": False,
            "route": self.route_name,
            "selected_leaves": tuple(leaf.dominance for leaf in leaves),
            "tie_state": trace.tie_state,
            "source_semantic_keys": tuple(dict.fromkeys(key for leaf in leaves for key in leaf.semantic_keys)),
            "leaf_parameters": tuple(dict(leaf.parameters) for leaf in leaves),
        }

    def contribution_report(self, point: Any) -> dict[str, Any]:
        return self.source_provenance(point)

    contributors = source_provenance


@dataclass(frozen=True, slots=True)
class AuthorityVolume:
    """Ellipsoidal authority with a finite C1 collar at its outer boundary."""

    identifier: str
    center: tuple[float, float, float]
    radii: tuple[float, float, float]
    collar_fraction: float = 0.25

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier:
            _fail("authority identifier must be a non-empty string")
        object.__setattr__(self, "center", _vec3(self.center, f"authority {self.identifier}.center"))
        object.__setattr__(self, "radii", _positive_tuple(self.radii, 3, f"authority {self.identifier}.radii"))
        fraction = _finite_float(self.collar_fraction, f"authority {self.identifier}.collar_fraction")
        if not 0.0 < fraction <= 1.0:
            _fail(f"authority {self.identifier} requires a finite positive collar fraction at most one")
        object.__setattr__(self, "collar_fraction", fraction)

    @property
    def collar_widths(self) -> tuple[float, float, float]:
        widths = tuple(self.collar_fraction * radius for radius in self.radii)
        if not all(math.isfinite(value) and value > 0.0 for value in widths):
            _fail(f"authority {self.identifier} collar is not finite")
        return widths

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        center = np.asarray(self.center)
        radii = np.asarray(self.radii)
        return center - radii, center + radii

    def normalized_radius(self, points: np.ndarray) -> np.ndarray:
        return np.sqrt(np.sum(((points - np.asarray(self.center)) / np.asarray(self.radii)) ** 2, axis=-1))

    def gate(self, points: np.ndarray) -> np.ndarray:
        radius = self.normalized_radius(points)
        collar = self.collar_fraction
        normalized = np.clip((1.0 - radius) / collar, 0.0, 1.0)
        return normalized * normalized * (3.0 - 2.0 * normalized)

    def contains(self, point: Any, tolerance: float = _FRAME_TOLERANCE) -> bool:
        value = self.normalized_radius(np.asarray(_vec3(point, f"authority {self.identifier} point")).reshape(1, 3))[0]
        return bool(value <= 1.0 + tolerance)

    def sampled_boundary_points(self) -> np.ndarray:
        """Return the deterministic 26-point boundary sample set."""

        directions = []
        for x in (-1.0, 0.0, 1.0):
            for y in (-1.0, 0.0, 1.0):
                for z in (-1.0, 0.0, 1.0):
                    vector = np.asarray((x, y, z), dtype=np.float64)
                    if np.linalg.norm(vector) > 0.0:
                        directions.append(vector / np.linalg.norm(vector))
        return np.asarray(self.center) + np.asarray(directions) * np.asarray(self.radii)

    def boundary_points(self) -> np.ndarray:
        """Backward-compatible alias returning samples, not a full boundary."""

        return self.sampled_boundary_points()

    def overlaps(self, other: "AuthorityVolume") -> bool:
        lower, upper = self.bounds
        other_lower, other_upper = other.bounds
        return bool(np.all(lower < other_upper - _FRAME_TOLERANCE) and np.all(other_lower < upper - _FRAME_TOLERANCE))


def _stable_soft_min(first: np.ndarray, second: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    delta = (second - first) / radius
    correction = radius * np.log1p(np.exp(-np.abs(delta)))
    result = np.minimum(first, second) - correction
    with np.errstate(over="ignore", under="ignore"):
        first_weight = np.where(delta >= 0.0, 1.0 / (1.0 + np.exp(-delta)), np.exp(delta) / (1.0 + np.exp(delta)))
    second_weight = 1.0 - first_weight
    if not np.all(np.isfinite(result)) or not np.all(np.isfinite(first_weight)) or not np.all(np.isfinite(second_weight)):
        _fail("smooth-min arithmetic became non-finite")
    return result, first_weight, second_weight


@dataclass(frozen=True, slots=True)
class SectionAttachment:
    """One named route/control component in a section composite.

    Older callers may still provide an authority and blend radius.  The
    parent-targeted interface path leaves those fields empty on component
    records and carries interface authority on the independent patch itself.
    """

    name: str
    field: Any
    authority: AuthorityVolume | None = None
    blend_radius: float | None = None
    semantic_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            _fail("section attachment name must be a non-empty string")
        if self.field is None or not callable(getattr(self.field, "evaluate", self.field)):
            _fail(f"section attachment {self.name} requires an evaluator")
        if self.authority is not None and not isinstance(self.authority, AuthorityVolume):
            _fail(f"section attachment {self.name}.authority must be an AuthorityVolume when present")
        if self.blend_radius is not None:
            _positive_float(self.blend_radius, f"section attachment {self.name}.blend_radius")
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"section attachment {self.name}.semantic_key must be non-empty when present")


@dataclass(frozen=True, slots=True)
class ParentTargetedInterfacePatch:
    """One independent, parent-targeted soft patch at a declared interface.

    The parent and child are evaluated directly.  No previously patched field
    is ever used as an operand, which keeps each patch independent of
    registration order.  ``blend_radius`` is the interface ``k`` value.
    """

    identifier: str
    parent_name: str
    child_name: str
    parent: Any
    child: Any
    authority: AuthorityVolume
    blend_radius: float
    semantic_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier:
            _fail("interface patch identifier must be a non-empty string")
        for label, value in (("parent", self.parent_name), ("child", self.child_name)):
            if not isinstance(value, str) or not value:
                _fail(f"interface patch {label} name must be a non-empty string")
        if self.parent is self.child:
            _fail(f"interface patch {self.identifier} parent and child must be distinct")
        if self.parent is None or not callable(getattr(self.parent, "evaluate", self.parent)):
            _fail(f"interface patch {self.identifier} parent is not an evaluator")
        if self.child is None or not callable(getattr(self.child, "evaluate", self.child)):
            _fail(f"interface patch {self.identifier} child is not an evaluator")
        if not isinstance(self.authority, AuthorityVolume):
            _fail(f"interface patch {self.identifier} requires an AuthorityVolume")
        object.__setattr__(self, "blend_radius", _positive_float(self.blend_radius, f"interface patch {self.identifier}.k"))
        if self.semantic_key is not None and (not isinstance(self.semantic_key, str) or not self.semantic_key):
            _fail(f"interface patch {self.identifier}.semantic_key must be non-empty when present")

    @property
    def name(self) -> str:
        return self.identifier

    @property
    def interface_id(self) -> str:
        return self.identifier

    @property
    def parent_id(self) -> str:
        return self.parent_name

    @property
    def child_id(self) -> str:
        return self.child_name

    @property
    def k(self) -> float:
        return self.blend_radius

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray] | None:
        bounds = [
            _field_bounds(self.parent, f"interface patch {self.identifier} parent"),
            _field_bounds(self.child, f"interface patch {self.identifier} child"),
            self.authority.bounds,
        ]
        known = [item for item in bounds if item is not None]
        if not known:
            return None
        return np.min(np.stack([item[0] for item in known]), axis=0), np.max(np.stack([item[1] for item in known]), axis=0)

    def _values_and_coefficients(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        parent = _field_evaluate(self.parent, points, f"interface patch {self.identifier} parent")
        child = _field_evaluate(self.child, points, f"interface patch {self.identifier} child")
        hard = np.minimum(parent, child)
        gate = self.authority.gate(points)
        soft, parent_soft_weight, child_soft_weight = _stable_soft_min(parent, child, self.blend_radius)
        parent_hard_weight = np.where(parent < child, 1.0, 0.0)
        child_hard_weight = np.where(child < parent, 1.0, 0.0)
        equality = parent == child
        parent_hard_weight = np.where(equality, 0.5, parent_hard_weight)
        child_hard_weight = np.where(equality, 0.5, child_hard_weight)
        result = hard + gate * (soft - hard)
        effective_parent = (1.0 - gate) * parent_hard_weight + gate * parent_soft_weight
        effective_child = (1.0 - gate) * child_hard_weight + gate * child_soft_weight
        if not all(np.all(np.isfinite(value)) for value in (result, effective_parent, effective_child, parent, child, hard)):
            _fail(f"interface patch {self.identifier} evaluation became non-finite")
        return result, effective_parent, effective_child, parent, child, hard

    def evaluate(self, points: Any) -> float | np.ndarray:
        query, scalar = _as_points(points, f"interface patch {self.identifier} query")
        values, _, _, _, _, _ = self._values_and_coefficients(query)
        return _restore(values, scalar)

    scalar_evaluator = evaluate

    def blend_coefficients(self, points: Any) -> np.ndarray:
        query, scalar = _as_points(points, f"interface patch {self.identifier} coefficient query")
        _, parent, child, _, _, _ = self._values_and_coefficients(query)
        result = np.stack((parent, child), axis=-1)
        return result[0] if scalar else result

    smooth_min_coefficients = blend_coefficients
    contributor_coefficients = blend_coefficients

    def validate_outside_hard_min(self, points: Any | None = None, tolerance: float = _BOUNDARY_TOLERANCE) -> bool:
        """Validate exact hard-min behavior at supplied outside samples."""

        samples = self.authority.sampled_boundary_points() if points is None else np.asarray(points, dtype=np.float64)
        if samples.ndim != 2 or samples.shape[1] != 3 or not np.all(np.isfinite(samples)):
            _fail(f"interface patch {self.identifier} outside samples must be finite three-vectors")
        if np.any(self.authority.normalized_radius(samples) < 1.0 - 1.0e-6):
            _fail(f"interface patch {self.identifier} outside samples must not be inside authority")
        parent = _field_evaluate(self.parent, samples, f"interface patch {self.identifier} outside parent")
        child = _field_evaluate(self.child, samples, f"interface patch {self.identifier} outside child")
        result = _field_evaluate(self, samples, f"interface patch {self.identifier} outside result")
        expected = np.minimum(parent, child)
        if np.max(np.abs(result - expected)) > tolerance:
            _fail(f"interface patch {self.identifier} does not retain its exact hard minimum outside authority")
        return True

    def gradient(self, point: Any) -> np.ndarray:
        query, scalar = _as_points(point, f"interface patch {self.identifier} gradient query")
        if not scalar:
            return np.stack([_finite_difference_gradient(self, item, f"interface patch {self.identifier}") for item in query], axis=0)
        return _finite_difference_gradient(self, query[0], f"interface patch {self.identifier}")

    def value_and_gradient(self, point: Any) -> tuple[float, np.ndarray]:
        query, scalar = _as_points(point, f"interface patch {self.identifier} value and gradient query")
        if not scalar:
            _fail("value_and_gradient requires one point")
        return float(self.evaluate(query[0])), self.gradient(query[0])

    def operation_trace(self, point: Any) -> OperationTrace | tuple[OperationTrace, ...]:
        query, scalar = _as_points(point, f"interface patch {self.identifier} trace query")
        if not scalar:
            return tuple(self.operation_trace(item) for item in query)  # type: ignore[return-value]
        result, parent_coefficient, child_coefficient, parent, child, hard = self._values_and_coefficients(query)
        parent_trace = _trace_field(self.parent, query[0], f"interface patch {self.identifier} parent")
        child_trace = _trace_field(self.child, query[0], f"interface patch {self.identifier} child")
        parent_value = float(parent[0])
        child_value = float(child[0])
        exact_tie = parent_value == child_value
        dominance = "tie" if exact_tie else self.parent_name if parent_value < child_value else self.child_name
        gate = float(self.authority.gate(query)[0])
        return OperationTrace(
            "parent-targeted-interface-patch",
            float(result[0]),
            self.authority.identifier,
            gate,
            (float(parent_coefficient[0]), float(child_coefficient[0])),
            dominance,
            "tie" if exact_tie else "ordered",
            tuple(dict.fromkeys(
                parent_trace.semantic_keys
                + child_trace.semantic_keys
                + (() if self.semantic_key is None else (self.semantic_key,))
            )),
            (parent_trace, child_trace),
            (
                ("blend_radius", self.blend_radius),
                ("parent_value", parent_value),
                ("child_value", child_value),
                ("hard_value", float(hard[0])),
            ),
            self.parent_name,
            self.child_name,
        )

    trace = operation_trace


@dataclass(frozen=True, slots=True, init=False)
class FullSectionComposite:
    """Order-independent hard envelope plus parent-targeted interface patches."""

    base: Any
    attachments: tuple[SectionAttachment, ...]
    interfaces: tuple[ParentTargetedInterfacePatch, ...]
    _junctions: tuple[ParentTargetedInterfacePatch, ...] = field(default=(), init=False, repr=False, compare=False)
    _bounds: tuple[np.ndarray, np.ndarray] | None = field(default=None, init=False, repr=False, compare=False)

    def __init__(
        self,
        base: Any,
        attachments: Iterable[SectionAttachment],
        interfaces: Iterable[ParentTargetedInterfacePatch] | None = None,
        *,
        patches: Iterable[ParentTargetedInterfacePatch] | None = None,
    ) -> None:
        if base is None or not callable(getattr(base, "evaluate", base)):
            _fail("full section composite requires an evaluator base")
        attachment_tuple = tuple(sorted(tuple(attachments), key=lambda item: item.name))
        if any(not isinstance(item, SectionAttachment) for item in attachment_tuple):
            _fail("full section composite attachments must be SectionAttachment values")
        if len({item.name for item in attachment_tuple}) != len(attachment_tuple):
            _fail("full section composite attachment names must be unique")
        interface_values_arg = tuple(interfaces) if interfaces is not None else None
        patch_values_arg = tuple(patches) if patches is not None else None
        if interface_values_arg is not None and patch_values_arg is not None:
            if interface_values_arg != patch_values_arg:
                _fail("full section composite received conflicting interfaces and patches")
        interface_values = patch_values_arg if patch_values_arg is not None else interface_values_arg
        if interface_values is None:
            legacy: list[ParentTargetedInterfacePatch] = []
            for attachment in attachment_tuple:
                if attachment.authority is None or attachment.blend_radius is None:
                    _fail(f"full section composite attachment {attachment.name} has no interface patch")
                legacy.append(
                    ParentTargetedInterfacePatch(
                        f"base->{attachment.name}",
                        "base",
                        attachment.name,
                        base,
                        attachment.field,
                        attachment.authority,
                        attachment.blend_radius,
                        attachment.semantic_key,
                    )
                )
            interface_tuple = tuple(legacy)
        else:
            interface_tuple = tuple(interface_values)
        interface_tuple = tuple(sorted(interface_tuple, key=lambda item: item.identifier))
        if any(not isinstance(item, ParentTargetedInterfacePatch) for item in interface_tuple):
            _fail("full section composite interfaces must be ParentTargetedInterfacePatch values")
        if len({item.identifier for item in interface_tuple}) != len(interface_tuple):
            _fail("full section composite interface identifiers must be unique")
        # ``torso`` is the canonical parent name used by the candidate.  Keep
        # ``base`` as a compatibility alias for small experiment callers.
        component_by_name = {"base": base, "torso": base}
        component_by_name.update({item.name: item.field for item in attachment_tuple})
        for interface in interface_tuple:
            if interface.parent_name not in component_by_name:
                _fail(f"full section composite interface {interface.identifier} has an unknown parent {interface.parent_name!r}")
            if interface.child_name not in component_by_name:
                _fail(f"full section composite interface {interface.identifier} has an unknown child {interface.child_name!r}")
            if interface.parent is not component_by_name[interface.parent_name] or interface.child is not component_by_name[interface.child_name]:
                _fail(f"full section composite interface {interface.identifier} does not target its named fields")
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "attachments", attachment_tuple)
        object.__setattr__(self, "interfaces", interface_tuple)
        object.__setattr__(self, "_junctions", interface_tuple)
        bounds = [_field_bounds(base, "full section composite base")]
        bounds.extend(_field_bounds(item.field, f"full section composite {item.name}") for item in attachment_tuple)
        bounds.extend(item.authority.bounds for item in interface_tuple)
        known = [item for item in bounds if item is not None]
        if not known:
            _fail("full section composite has no finite bounds")
        object.__setattr__(self, "_bounds", (np.min(np.stack([item[0] for item in known]), axis=0), np.max(np.stack([item[1] for item in known]), axis=0)))

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        if self._bounds is None:
            _fail("full section composite bounds are unavailable")
        return self._bounds[0].copy(), self._bounds[1].copy()

    @property
    def junctions(self) -> tuple[ParentTargetedInterfacePatch, ...]:
        return self._junctions

    @property
    def patches(self) -> tuple[ParentTargetedInterfacePatch, ...]:
        return self.interfaces

    @property
    def components(self) -> tuple[Any, ...]:
        return tuple(item.field for item in self.attachments)

    @property
    def routes(self) -> tuple[Any, ...]:
        return tuple(item.field for item in self.attachments if isinstance(item.field, AnisotropicSectionSweep))

    @property
    def field(self) -> Callable[[Any], float | np.ndarray]:
        return self.evaluate

    def evaluate(self, points: Any) -> float | np.ndarray:
        query, scalar = _as_points(points, "full section composite query")
        component_values = [_field_evaluate(self.base, query, "full section composite base")]
        component_values.extend(_field_evaluate(item.field, query, f"full section composite {item.name}") for item in self.attachments)
        envelope = np.min(np.stack(component_values, axis=0), axis=0)
        if not self.interfaces:
            values = envelope
        else:
            patch_values = [_field_evaluate(item, query, f"full section composite patch {item.identifier}") for item in self.interfaces]
            values = np.min(np.stack((envelope, *patch_values), axis=0), axis=0)
        if not np.all(np.isfinite(values)):
            _fail("full section composite evaluation became non-finite")
        return _restore(values, scalar)

    scalar_evaluator = evaluate

    def gradient(self, point: Any) -> np.ndarray:
        query, scalar = _as_points(point, "full section composite gradient query")
        if not scalar:
            return np.stack([_finite_difference_gradient(self, item, "full section composite") for item in query], axis=0)
        return _finite_difference_gradient(self, query[0], "full section composite")

    def contribution_report(self, point: Any) -> dict[str, Any]:
        query, scalar = _as_points(point, "full section composite contribution query")
        if not scalar:
            return {"points": [self.contribution_report(item) for item in query]}
        component_names = ("base",) + tuple(item.name for item in self.attachments)
        component_fields = (self.base,) + tuple(item.field for item in self.attachments)
        component_values = np.asarray([float(_field_evaluate(item, query, "full section composite contribution")[0]) for item in component_fields])
        envelope_value, envelope_active, envelope_sensitivity = _exact_hard_min_selection(component_values, "full section composite envelope")
        patch_values = np.asarray([float(_field_evaluate(item, query, "full section composite patch contribution")[0]) for item in self.interfaces])
        final_values = np.concatenate((np.asarray((envelope_value,)), patch_values))
        _, final_active, final_sensitivity = _exact_hard_min_selection(final_values, "full section composite final")
        component_weights = {name: 0.0 for name in component_names}
        interface_weights = {item.identifier: 0.0 for item in self.interfaces}
        for final_index in final_active:
            final_weight = final_sensitivity[final_index]
            if final_weight <= 0.0:
                continue
            if final_index == 0:
                for component_index in envelope_active:
                    sensitivity = envelope_sensitivity[component_index]
                    component_weights[component_names[component_index]] += final_weight * sensitivity
            else:
                interface = self.interfaces[final_index - 1]
                interface_weights[interface.identifier] += final_weight
                coefficients = np.asarray(interface.blend_coefficients(query[0]), dtype=np.float64)
                parent_component = "base" if interface.parent_name == "torso" else interface.parent_name
                child_component = "base" if interface.child_name == "torso" else interface.child_name
                component_weights[parent_component] += final_weight * float(coefficients[0])
                component_weights[child_component] += final_weight * float(coefficients[1])
        return {
            "diagnostic_kind": "full-section-composite-diagnostics",
            "geometric_influence": {
                "diagnostic_kind": "exact-operator-sensitivity",
                "base": component_weights["base"],
                "torso": component_weights["base"],
                "components": {item.name: component_weights[item.name] for item in self.attachments},
                "interfaces": interface_weights,
            },
            "source_provenance": {
                "base": getattr(self.base, "source_provenance", lambda value: {"diagnostic_kind": "source-provenance", "geometric_influence": False})(query[0]),
                "components": {
                    item.name: getattr(item.field, "source_provenance", lambda value: {"diagnostic_kind": "source-provenance", "geometric_influence": False})(query[0])
                    for item in self.attachments
                },
                "interfaces": {
                    item.identifier: {
                        "parent": item.parent_name,
                        "child": item.child_name,
                        "authority": item.authority.identifier,
                    }
                    for item in self.interfaces
                },
            },
        }

    contributors = contribution_report

    def operation_trace(self, point: Any) -> OperationTrace | tuple[OperationTrace, ...]:
        query, scalar = _as_points(point, "full section composite trace query")
        if not scalar:
            return tuple(self.operation_trace(item) for item in query)  # type: ignore[return-value]
        component_traces = [_trace_field(self.base, query[0], "base")]
        component_traces.extend(
            _trace_with_semantic_key(_trace_field(item.field, query[0], item.name), item.semantic_key)
            for item in self.attachments
        )
        component_values = tuple(item.value for item in component_traces)
        envelope, envelope_active, envelope_sensitivity = _exact_hard_min_selection(component_values, "full section composite trace envelope")
        envelope_trace = OperationTrace(
            "full-section-hard-min",
            envelope,
            None,
            None,
            envelope_sensitivity,
            "tie" if len(envelope_active) > 1 else component_traces[envelope_active[0]].dominance,
            "tie" if len(envelope_active) > 1 else "ordered",
            tuple(dict.fromkeys(key for trace in component_traces for key in trace.semantic_keys)),
            tuple(component_traces),
            (("component_count", float(len(component_traces))),),
        )
        if not self.interfaces:
            return envelope_trace
        patch_traces = tuple(item.operation_trace(query[0]) for item in self.interfaces)
        if any(not isinstance(item, OperationTrace) for item in patch_traces):
            _fail("full section composite patch trace returned an invalid record")
        final_children = (envelope_trace,) + patch_traces
        final_value, final_active, final_sensitivity = _exact_hard_min_selection(
            (item.value for item in final_children),
            "full section composite trace final",
        )
        return OperationTrace(
            "full-section-interface-composite",
            final_value,
            None,
            None,
            final_sensitivity,
            "tie" if len(final_active) > 1 else final_children[final_active[0]].dominance,
            "tie" if len(final_active) > 1 else "ordered",
            tuple(dict.fromkeys(key for trace in final_children for key in trace.semantic_keys)),
            final_children,
            (("patch_count", float(len(patch_traces))),),
        )

    trace = operation_trace


def _trace_field(field_value: Any, point: np.ndarray, fallback_key: str) -> OperationTrace:
    tracer = getattr(field_value, "operation_trace", None)
    if tracer is not None:
        result = tracer(point)
        if not isinstance(result, OperationTrace):
            _fail("field operation trace returned an invalid record")
        return result
    value = float(_field_evaluate(field_value, point.reshape(1, 3), f"{fallback_key} trace")[0])
    return _leaf_trace(value, fallback_key)


def _trace_with_semantic_key(trace: OperationTrace, semantic_key: str | None) -> OperationTrace:
    """Add a component binding without changing its operator or children."""

    if semantic_key is None or semantic_key in trace.semantic_keys:
        return trace
    return OperationTrace(
        trace.operator,
        trace.value,
        trace.authority_id,
        trace.blend_coefficient,
        trace.sensitivity,
        trace.dominance,
        trace.tie_state,
        tuple(dict.fromkeys(trace.semantic_keys + (semantic_key,))),
        trace.children,
        trace.parameters,
        trace.parent_id,
        trace.child_id,
    )

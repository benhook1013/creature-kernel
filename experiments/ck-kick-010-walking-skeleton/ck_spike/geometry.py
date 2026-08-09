"""Disposable analytic-field and surface seam for CK-KICK-010.

The objects in this module deliberately form a small, project-owned boundary.
Scientific-library arrays are used while building a surface, but the returned
surface contains ordinary Python tuples so that a later adapter can serialize
it without exposing NumPy, scikit-image, or trimesh in the graph interface.
This is a debug field and mesh exploration, not an SDF or collision contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from skimage.measure import marching_cubes
import trimesh

from .diagnostics import Diagnostic, Phase, Severity
from .model import Primitive, ResolvedGraph, ResolvedNode


SMOOTH_MIN_OPERATOR = "polynomial_cubic_smooth_min"
SMOOTH_MIN_FORMULA = (
    "min(a,b) - max(k - abs(a-b), 0)^3 / (6*k^2)"
)
SMOOTH_MIN_FOLD_ORDER = "sorted_source_label"


class GeometryError(Exception):
    """A fail-fast field or mesh error with structured diagnostics only."""

    def __init__(self, diagnostics: Sequence[Diagnostic]):
        self.diagnostics = tuple(diagnostics)
        super().__init__(
            "; ".join(f"{item.code} at {item.path}" for item in self.diagnostics)
        )


@dataclass(frozen=True)
class GeometryConfig:
    """Immutable configuration for the disposable surface builder."""

    samples_per_axis: int = 128
    padding: float = 0.10
    isovalue: float = 0.0
    smooth_min_k: float = 0.10

    def __post_init__(self) -> None:
        if (
            not isinstance(self.samples_per_axis, int)
            or isinstance(self.samples_per_axis, bool)
            or self.samples_per_axis < 2
        ):
            raise ValueError("samples_per_axis must be an integer >= 2")
        for name, value in (
            ("padding", self.padding),
            ("isovalue", self.isovalue),
            ("smooth_min_k", self.smooth_min_k),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{name} must be a finite number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.padding < 0.0:
            raise ValueError("padding must be non-negative")
        if self.smooth_min_k <= 0.0:
            raise ValueError("smooth_min_k must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Return exact operator, formula, and fold-order metadata."""

        return {
            "samples_per_axis": self.samples_per_axis,
            "padding": float(self.padding),
            "isovalue": float(self.isovalue),
            "smooth_min": {
                "operator": SMOOTH_MIN_OPERATOR,
                "formula": SMOOTH_MIN_FORMULA,
                "k": float(self.smooth_min_k),
                "fold_order": SMOOTH_MIN_FOLD_ORDER,
            },
        }

    @property
    def metadata(self) -> dict[str, Any]:
        """Alias used by adapters that call configuration metadata directly."""

        return self.to_dict()


@dataclass(frozen=True)
class GridMetadata:
    """Fixed-grid definition in the selected ``(x, y, z)`` basis."""

    samples_per_axis: int
    axis_order: tuple[str, str, str]
    origin: tuple[float, float, float]
    spacing: tuple[float, float, float]
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    padding: float
    isovalue: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "samples_per_axis": self.samples_per_axis,
            "axis_order": list(self.axis_order),
            "origin": list(self.origin),
            "spacing": list(self.spacing),
            "bounds": {
                "min": list(self.bounds_min),
                "max": list(self.bounds_max),
            },
            "padding": self.padding,
            "isovalue": self.isovalue,
        }


@dataclass(frozen=True)
class MeshMetrics:
    """Objective field and structural checks returned with a surface."""

    vertex_count: int
    face_count: int
    component_count: int
    watertight: bool
    finite_vertices: bool
    finite_faces: bool
    finite_normals: bool
    valid_indices: bool
    degenerate_face_count: int
    attribution_count: int
    attribution_labels: tuple[str, ...]
    field_minimum: float
    field_maximum: float
    domain_face_minimum: float
    signed_volume: float
    orientation_alignment: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
            "component_count": self.component_count,
            "watertight": self.watertight,
            "finite_vertices": self.finite_vertices,
            "finite_faces": self.finite_faces,
            "finite_normals": self.finite_normals,
            "valid_indices": self.valid_indices,
            "degenerate_face_count": self.degenerate_face_count,
            "attribution_count": self.attribution_count,
            "attribution_labels": list(self.attribution_labels),
            "field_minimum": self.field_minimum,
            "field_maximum": self.field_maximum,
            "domain_face_minimum": self.domain_face_minimum,
            "signed_volume": self.signed_volume,
            "orientation_alignment": self.orientation_alignment,
        }


@dataclass(frozen=True)
class SurfaceResult:
    """Serializable result of :func:`build_surface`."""

    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, int, int], ...]
    normals: tuple[tuple[float, float, float], ...]
    source_labels: tuple[str, ...]
    config_metadata: Mapping[str, Any]
    grid: GridMetadata
    metrics: MeshMetrics

    @property
    def attribution(self) -> tuple[str, ...]:
        """The winner-only source label for each generated vertex."""

        return self.source_labels

    @property
    def attribution_labels(self) -> tuple[str, ...]:
        """Descriptive alias for callers serializing the winner channel."""

        return self.source_labels

    @property
    def grid_metadata(self) -> GridMetadata:
        """Descriptive alias for the derived grid metadata."""

        return self.grid

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "config": dict(self.config_metadata),
            "grid": self.grid.to_dict(),
            "metrics": self.metrics.to_dict(),
            "source_labels": list(self.source_labels),
        }

    def to_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {"metadata": self.metadata}
        if include_arrays:
            result["vertices"] = [list(value) for value in self.vertices]
            result["faces"] = [list(value) for value in self.faces]
            result["normals"] = [list(value) for value in self.normals]
            result["source_labels"] = list(self.source_labels)
        return result


def _error(
    code: str,
    phase: Phase,
    path: str,
    message: str,
    related: Iterable[str] = (),
) -> GeometryError:
    return GeometryError(
        (
            Diagnostic(
                code=code,
                severity=Severity.ERROR,
                phase=phase,
                path=path,
                related_source_labels=tuple(related),
                message=message,
            ),
        )
    )


def _points_array(points: Any) -> tuple[np.ndarray, tuple[int, ...]]:
    values = np.asarray(points, dtype=np.float64)
    if values.ndim == 0 or values.shape[-1:] != (3,):
        raise _error("FIELD_INVALID_INPUT", Phase.FIELD, "/points", "points must have shape (..., 3)")
    if not np.all(np.isfinite(values)):
        raise _error("FIELD_NON_FINITE_INPUT", Phase.FIELD, "/points", "points must be finite")
    shape = values.shape[:-1]
    return values.reshape(-1, 3), shape


def _matrix_parts(world_matrix: Any) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.asarray(world_matrix, dtype=np.float64)
    if matrix.size != 16:
        raise _error(
            "FIELD_INVALID_TRANSFORM",
            Phase.FIELD,
            "/world_transform",
            "world transform must contain sixteen values",
        )
    matrix = matrix.reshape(4, 4)
    if not np.all(np.isfinite(matrix)):
        raise _error(
            "FIELD_NON_FINITE_TRANSFORM",
            Phase.FIELD,
            "/world_transform",
            "world transform must be finite",
        )
    rotation = matrix[:3, :3]
    translation = matrix[:3, 3]
    # Resolver transforms are rigid.  Refusing scale/shear here prevents a
    # silently incorrect primitive interpretation in this temporary seam.
    if not np.allclose(rotation.T @ rotation, np.eye(3), rtol=0.0, atol=1e-7):
        raise _error(
            "FIELD_NON_RIGID_TRANSFORM",
            Phase.FIELD,
            "/world_transform",
            "world transform must be rigid",
        )
    if not math.isclose(float(np.linalg.det(rotation)), 1.0, rel_tol=0.0, abs_tol=1e-7):
        raise _error(
            "FIELD_NON_RIGID_TRANSFORM",
            Phase.FIELD,
            "/world_transform",
            "world transform must preserve the selected orientation",
        )
    return rotation, translation


def _local_points(points: np.ndarray, world_matrix: Any | None) -> np.ndarray:
    if world_matrix is None:
        return points
    rotation, translation = _matrix_parts(world_matrix)
    # Points are rows here; multiplying by R is equivalent to R.T * p as
    # column vectors, which is the inverse rigid transform.
    return (points - translation) @ rotation


def capsule_raw_field(
    points: Any,
    endpoints: Sequence[Sequence[float]],
    radius: float,
    world_matrix: Any | None = None,
) -> np.ndarray:
    """Evaluate the normalized capsule field at world-space points."""

    values, shape = _points_array(points)
    endpoint_array = np.asarray(endpoints, dtype=np.float64)
    if endpoint_array.shape != (2, 3) or not np.all(np.isfinite(endpoint_array)):
        raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/capsule/endpoints", "capsule endpoints must be finite")
    if not math.isfinite(float(radius)) or radius <= 0.0:
        raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/capsule/radius", "capsule radius must be finite and positive")
    local = _local_points(values, world_matrix)
    segment = endpoint_array[1] - endpoint_array[0]
    denominator = float(np.dot(segment, segment))
    if denominator == 0.0:
        closest = np.broadcast_to(endpoint_array[0], local.shape)
    else:
        parameter = np.clip(
            np.sum((local - endpoint_array[0]) * segment, axis=1) / denominator,
            0.0,
            1.0,
        )
        closest = endpoint_array[0] + parameter[:, None] * segment
    field = np.linalg.norm(local - closest, axis=1) / float(radius) - 1.0
    if not np.all(np.isfinite(field)):
        raise _error("FIELD_NON_FINITE", Phase.FIELD, "/capsule", "capsule field is non-finite")
    return field.reshape(shape)


def ellipsoid_raw_field(
    points: Any,
    radii: Sequence[float],
    world_matrix: Any | None = None,
) -> np.ndarray:
    """Evaluate the normalized ellipsoid field at world-space points."""

    values, shape = _points_array(points)
    radius_array = np.asarray(radii, dtype=np.float64)
    if radius_array.shape != (3,) or not np.all(np.isfinite(radius_array)):
        raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/ellipsoid/radii", "ellipsoid radii must be finite")
    if np.any(radius_array <= 0.0):
        raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/ellipsoid/radii", "ellipsoid radii must be positive")
    local = _local_points(values, world_matrix)
    field = np.sqrt(np.sum((local / radius_array) ** 2, axis=1)) - 1.0
    if not np.all(np.isfinite(field)):
        raise _error("FIELD_NON_FINITE", Phase.FIELD, "/ellipsoid", "ellipsoid field is non-finite")
    return field.reshape(shape)


evaluate_capsule_field = capsule_raw_field
evaluate_ellipsoid_field = ellipsoid_raw_field


def primitive_raw_field(
    points: Any,
    primitive: Primitive,
    world_matrix: Any | None = None,
) -> np.ndarray:
    """Evaluate one resolved primitive in world coordinates."""

    if primitive.kind == "capsule":
        if primitive.radius is None:
            raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/primitive", "capsule radius is missing")
        return capsule_raw_field(points, primitive.endpoints, primitive.radius, world_matrix)
    if primitive.kind == "ellipsoid":
        if primitive.radii is None:
            raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/primitive", "ellipsoid radii are missing")
        return ellipsoid_raw_field(points, primitive.radii, world_matrix)
    raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, "/primitive/kind", "unsupported primitive kind")


def resolved_node_raw_field(node: ResolvedNode, points: Any) -> np.ndarray:
    """Evaluate a resolved node's raw field at world-space points."""

    return primitive_raw_field(points, node.node.primitive, node.world_matrix)


evaluate_primitive_field = primitive_raw_field
evaluate_node_field = resolved_node_raw_field


# Short descriptive aliases keep the seam convenient for focused callers.
capsule_field = capsule_raw_field
ellipsoid_field = ellipsoid_raw_field
raw_field = resolved_node_raw_field


def _primitive_world_aabb(node: ResolvedNode) -> tuple[np.ndarray, np.ndarray]:
    rotation, translation = _matrix_parts(node.world_matrix)
    primitive = node.node.primitive
    if primitive.kind == "capsule":
        if primitive.radius is None or len(primitive.endpoints) != 2:
            raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, f"/nodes/{node.node.label}/primitive", "invalid capsule")
        endpoints = np.asarray(primitive.endpoints, dtype=np.float64)
        if not np.all(np.isfinite(endpoints)) or not math.isfinite(float(primitive.radius)):
            raise _error("FIELD_NON_FINITE", Phase.FIELD, f"/nodes/{node.node.label}/primitive", "primitive is non-finite")
        world_endpoints = endpoints @ rotation.T + translation
        radius = float(primitive.radius)
        return np.min(world_endpoints, axis=0) - radius, np.max(world_endpoints, axis=0) + radius
    if primitive.kind == "ellipsoid":
        if primitive.radii is None:
            raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, f"/nodes/{node.node.label}/primitive", "invalid ellipsoid")
        radii = np.asarray(primitive.radii, dtype=np.float64)
        if radii.shape != (3,) or not np.all(np.isfinite(radii)) or np.any(radii <= 0.0):
            raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, f"/nodes/{node.node.label}/primitive", "invalid ellipsoid radii")
        center = translation
        extent = np.abs(rotation) @ radii
        return center - extent, center + extent
    raise _error("FIELD_INVALID_PRIMITIVE", Phase.FIELD, f"/nodes/{node.node.label}/primitive/kind", "unsupported primitive kind")


def primitive_world_aabb(node: ResolvedNode) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return the exact conservative world AABB of one rigid primitive."""

    lower, upper = _primitive_world_aabb(node)
    return tuple(float(value) for value in lower), tuple(float(value) for value in upper)


world_aabb = primitive_world_aabb


def _sorted_nodes(graph: ResolvedGraph) -> tuple[ResolvedNode, ...]:
    nodes = tuple(sorted(graph.nodes, key=lambda item: item.node.label))
    labels = tuple(node.node.label for node in nodes)
    if not nodes:
        raise _error("FIELD_EMPTY_GRAPH", Phase.FIELD, "/nodes", "graph contains no primitives")
    if len(set(labels)) != len(labels):
        raise _error("FIELD_DUPLICATE_SOURCE_LABEL", Phase.FIELD, "/nodes", "source labels must be unique", labels)
    return nodes


def derive_grid_metadata(graph: ResolvedGraph, config: GeometryConfig | None = None) -> GridMetadata:
    """Derive padded fixed-grid bounds from resolved rigid primitive AABBs."""

    chosen = config or GeometryConfig()
    nodes = _sorted_nodes(graph)
    bounds = [_primitive_world_aabb(node) for node in nodes]
    lower = np.min(np.stack([pair[0] for pair in bounds]), axis=0) - float(chosen.padding)
    upper = np.max(np.stack([pair[1] for pair in bounds]), axis=0) + float(chosen.padding)
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)) or np.any(upper <= lower):
        raise _error("FIELD_INVALID_GRID", Phase.FIELD, "/grid", "derived grid bounds are invalid")
    spacing = (upper - lower) / float(chosen.samples_per_axis - 1)
    return GridMetadata(
        samples_per_axis=chosen.samples_per_axis,
        axis_order=("x", "y", "z"),
        origin=tuple(float(value) for value in lower),
        spacing=tuple(float(value) for value in spacing),
        bounds_min=tuple(float(value) for value in lower),
        bounds_max=tuple(float(value) for value in upper),
        padding=float(chosen.padding),
        isovalue=float(chosen.isovalue),
    )


def _smooth_min(left: np.ndarray, right: np.ndarray, k: float) -> np.ndarray:
    distance = np.abs(left - right)
    h = np.maximum(k - distance, 0.0)
    return np.minimum(left, right) - (h * h * h) / (6.0 * k * k)


def _combined_field(points: Any, nodes: Sequence[ResolvedNode], config: GeometryConfig) -> np.ndarray:
    """Fold one temporary raw field at a time in sorted source-label order."""

    combined: np.ndarray | None = None
    for node in nodes:
        raw = np.asarray(resolved_node_raw_field(node, points), dtype=np.float64)
        if not np.all(np.isfinite(raw)):
            raise _error("FIELD_NON_FINITE", Phase.FIELD, f"/nodes/{node.node.label}", "raw field is non-finite", (node.node.label,))
        combined = raw if combined is None else _smooth_min(combined, raw, float(config.smooth_min_k))
    if combined is None or not np.all(np.isfinite(combined)):
        raise _error("FIELD_NON_FINITE", Phase.FIELD, "/field", "combined field is non-finite")
    return combined


def _domain_face_values(field: np.ndarray) -> np.ndarray:
    face = np.zeros(field.shape, dtype=bool)
    face[0, :, :] = True
    face[-1, :, :] = True
    face[:, 0, :] = True
    face[:, -1, :] = True
    face[:, :, 0] = True
    face[:, :, -1] = True
    return field[face]


def _winner_labels(vertices: np.ndarray, nodes: Sequence[ResolvedNode]) -> tuple[str, ...]:
    best = np.full(vertices.shape[0], np.inf, dtype=np.float64)
    winners: list[str] = [""] * vertices.shape[0]
    for node in nodes:
        values = np.asarray(resolved_node_raw_field(node, vertices), dtype=np.float64).reshape(-1)
        if values.shape != best.shape or not np.all(np.isfinite(values)):
            raise _error("FIELD_NON_FINITE", Phase.FIELD, f"/nodes/{node.node.label}", "vertex raw field is non-finite", (node.node.label,))
        # Strict comparison is intentional: sorted traversal preserves exact
        # ties in favour of the lexicographically first source label.
        update = values < best
        best[update] = values[update]
        for index in np.flatnonzero(update):
            winners[int(index)] = node.node.label
    if any(not value for value in winners):
        raise _error("MESH_ATTRIBUTION_INVALID", Phase.MESH, "/source_labels", "every vertex needs one source label")
    return tuple(winners)


def attribute_winners(graph: ResolvedGraph, vertices: Any) -> tuple[str, ...]:
    """Return one raw-field winner per world-space vertex.

    Traversal is lexicographically sorted and updates only on a strict lower
    value, making an exact tie deterministic without introducing weights.
    """

    points, shape = _points_array(vertices)
    if len(shape) != 1:
        raise ValueError("vertices must have shape (vertex_count, 3)")
    return _winner_labels(points, _sorted_nodes(graph))


def _orient_mesh(vertices: np.ndarray, faces: np.ndarray, nodes: Sequence[ResolvedNode], config: GeometryConfig) -> tuple[np.ndarray, np.ndarray, float, float]:
    edges = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    edges_two = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    area_vectors = np.cross(edges, edges_two)
    lengths = np.linalg.norm(area_vectors, axis=1)
    if not np.all(np.isfinite(lengths)):
        raise _error("MESH_NON_FINITE", Phase.MESH, "/faces", "face geometry is non-finite")
    centers = (vertices[faces[:, 0]] + vertices[faces[:, 1]] + vertices[faces[:, 2]]) / 3.0
    # A central difference against the actual folded field gives an objective
    # outward direction: raw fields increase from the interior to the exterior.
    delta = max(min(config.padding if config.padding > 0.0 else 0.01, 0.05), 1e-5)
    gradient = np.column_stack(
        (
            (_combined_field(centers + np.array([delta, 0.0, 0.0]), nodes, config) - _combined_field(centers - np.array([delta, 0.0, 0.0]), nodes, config)) / (2.0 * delta),
            (_combined_field(centers + np.array([0.0, delta, 0.0]), nodes, config) - _combined_field(centers - np.array([0.0, delta, 0.0]), nodes, config)) / (2.0 * delta),
            (_combined_field(centers + np.array([0.0, 0.0, delta]), nodes, config) - _combined_field(centers - np.array([0.0, 0.0, delta]), nodes, config)) / (2.0 * delta),
        )
    )
    normal_lengths = np.linalg.norm(area_vectors, axis=1) * np.linalg.norm(gradient, axis=1)
    alignment = np.divide(
        np.sum(area_vectors * gradient, axis=1),
        normal_lengths,
        out=np.zeros_like(normal_lengths),
        where=normal_lengths > 0.0,
    )
    mean_alignment = float(np.mean(alignment))
    if not np.all(np.isfinite(alignment)) or abs(mean_alignment) <= 1e-8:
        raise _error("MESH_ORIENTATION_UNRESOLVED", Phase.MESH, "/faces", "field-gradient orientation is unresolved")
    if mean_alignment < 0.0:
        faces = faces[:, [0, 2, 1]]
        area_vectors = -area_vectors
        alignment = -alignment
    signed_volume = float(np.sum(np.einsum("ij,ij->i", vertices[faces[:, 0]], area_vectors)) / 6.0)
    if not math.isfinite(signed_volume) or signed_volume <= 0.0:
        raise _error("MESH_ORIENTATION_UNRESOLVED", Phase.MESH, "/faces", "signed volume is not positive in the selected basis")
    return faces, area_vectors, signed_volume, float(np.mean(alignment))


def _validate_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    normals: np.ndarray,
    labels: tuple[str, ...],
    known_labels: tuple[str, ...],
    field: np.ndarray,
    face_values: np.ndarray,
    signed_volume: float,
    orientation_alignment: float,
) -> MeshMetrics:
    finite_vertices = bool(np.all(np.isfinite(vertices)))
    finite_faces = bool(np.all(np.isfinite(faces)))
    finite_normals = bool(np.all(np.isfinite(normals)))
    valid_indices = bool(
        faces.ndim == 2
        and faces.shape[1:] == (3,)
        and faces.size > 0
        and np.all(faces >= 0)
        and np.all(faces < len(vertices))
    )
    if valid_indices:
        area_vectors = np.cross(
            vertices[faces[:, 1]] - vertices[faces[:, 0]],
            vertices[faces[:, 2]] - vertices[faces[:, 0]],
        )
        degenerate = int(np.count_nonzero(np.linalg.norm(area_vectors, axis=1) <= 1e-14))
    else:
        degenerate = 0
    try:
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        components = tuple(mesh.split(only_watertight=False))
        component_count = len(components)
        watertight = bool(mesh.is_watertight)
    except Exception:
        component_count = 0
        watertight = False
    metrics = MeshMetrics(
        vertex_count=int(len(vertices)),
        face_count=int(len(faces)),
        component_count=component_count,
        watertight=watertight,
        finite_vertices=finite_vertices,
        finite_faces=finite_faces,
        finite_normals=finite_normals,
        valid_indices=valid_indices,
        degenerate_face_count=degenerate,
        attribution_count=len(labels),
        attribution_labels=tuple(sorted(set(labels))),
        field_minimum=float(np.min(field)),
        field_maximum=float(np.max(field)),
        domain_face_minimum=float(np.min(face_values)),
        signed_volume=signed_volume,
        orientation_alignment=orientation_alignment,
    )
    if (
        metrics.vertex_count == 0
        or metrics.face_count == 0
        or not metrics.finite_vertices
        or not metrics.finite_faces
        or not metrics.finite_normals
        or not metrics.valid_indices
        or metrics.degenerate_face_count != 0
        or metrics.component_count != 1
        or not metrics.watertight
        or metrics.attribution_count != metrics.vertex_count
        or any(label not in known_labels for label in labels)
    ):
        raise _error("MESH_STRUCTURAL_INVALID", Phase.MESH, "/mesh", "surface failed structural validation", known_labels)
    return metrics


def build_surface(graph: ResolvedGraph, config: GeometryConfig | None = None) -> SurfaceResult:
    """Build one deterministic, attributed marching-cubes surface."""

    chosen = config or GeometryConfig()
    nodes = _sorted_nodes(graph)
    grid = derive_grid_metadata(graph, chosen)
    n = chosen.samples_per_axis
    axes = tuple(
        np.linspace(grid.bounds_min[index], grid.bounds_max[index], n, dtype=np.float64)
        for index in range(3)
    )
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    field = _combined_field(points, nodes, chosen)
    if field.shape != (n, n, n) or not np.all(np.isfinite(field)):
        raise _error("FIELD_NON_FINITE", Phase.FIELD, "/field", "sampled field is non-finite")
    face_values = _domain_face_values(field)
    face_minimum = float(np.min(face_values))
    # Treat round-off at an analytically tangent AABB face as non-positive;
    # otherwise a zero-clearance domain can appear valid by a few ulps.
    face_tolerance = max(1e-12, abs(float(chosen.isovalue)) * 1e-12)
    if not np.isfinite(face_minimum) or face_minimum <= chosen.isovalue + face_tolerance:
        raise _error("FIELD_DOMAIN_FACE_NOT_POSITIVE", Phase.FIELD, "/grid/domain_faces", "every domain-face sample must be positive")
    minimum, maximum = float(np.min(field)), float(np.max(field))
    if not (minimum < chosen.isovalue < maximum):
        raise _error("FIELD_NO_ZERO_CROSSING", Phase.FIELD, "/field", "sampled field must contain both signs")
    try:
        raw_vertices, raw_faces, _raw_normals, _values = marching_cubes(
            field,
            level=float(chosen.isovalue),
            spacing=grid.spacing,
            gradient_direction="descent",
            allow_degenerate=False,
        )
    except Exception as error:
        raise _error("MESH_EXTRACTION_FAILED", Phase.MESH, "/marching_cubes", "marching-cubes extraction failed") from error
    vertices = np.asarray(raw_vertices, dtype=np.float64) + np.asarray(grid.origin, dtype=np.float64)
    faces = np.asarray(raw_faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1:] != (3,) or faces.ndim != 2 or faces.shape[1:] != (3,):
        raise _error("MESH_EXTRACTION_FAILED", Phase.MESH, "/mesh", "marching-cubes output has invalid shape")
    faces, area_vectors, signed_volume, orientation_alignment = _orient_mesh(vertices, faces, nodes, chosen)
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], area_vectors)
    normal_lengths = np.linalg.norm(normals, axis=1)
    if np.any(normal_lengths <= 1e-14):
        raise _error("MESH_NORMALS_INVALID", Phase.MESH, "/normals", "vertex normals are undefined")
    normals /= normal_lengths[:, None]
    labels = _winner_labels(vertices, nodes)
    metrics = _validate_mesh(
        vertices,
        faces,
        normals,
        labels,
        tuple(node.node.label for node in nodes),
        field,
        face_values,
        signed_volume,
        orientation_alignment,
    )
    return SurfaceResult(
        vertices=tuple(tuple(float(value) for value in row) for row in vertices),
        faces=tuple(tuple(int(value) for value in row) for row in faces),
        normals=tuple(tuple(float(value) for value in row) for row in normals),
        source_labels=labels,
        config_metadata=chosen.to_dict(),
        grid=grid,
        metrics=metrics,
    )


build = build_surface


__all__ = [
    "GeometryConfig",
    "GeometryError",
    "GridMetadata",
    "MeshMetrics",
    "SurfaceResult",
    "SMOOTH_MIN_OPERATOR",
    "SMOOTH_MIN_FORMULA",
    "SMOOTH_MIN_FOLD_ORDER",
    "capsule_raw_field",
    "capsule_field",
    "evaluate_capsule_field",
    "ellipsoid_raw_field",
    "ellipsoid_field",
    "evaluate_ellipsoid_field",
    "primitive_raw_field",
    "evaluate_primitive_field",
    "resolved_node_raw_field",
    "evaluate_node_field",
    "raw_field",
    "attribute_winners",
    "primitive_world_aabb",
    "world_aabb",
    "derive_grid_metadata",
    "build_surface",
    "build",
]

"""Deterministic export and export-validation helpers for CK-KICK-010.

The walking skeleton uses the temporary resolver coordinate convention directly:
the export transform is the identity.  This module still records and validates
the transform explicitly so a later host adapter cannot silently change the
coordinate basis.  It intentionally does not implement a second coordinate
adapter or repair winding for a negative-determinant transform.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Sequence

import numpy as np

from .diagnostics import Diagnostic, Phase, Severity
from .geometry import (
    FACE_AREA_TOLERANCE,
    FACE_ORIENTATION_ALIGNMENT_TOLERANCE,
    SurfaceResult,
    _directed_edge_orientation_mismatches,
)
from .model import ResolvedGraph


EXPORT_FORMAT = "ck-kick-010-identity-export-v1"
SEMANTIC_REGIONS_FORMAT = "ck-kick-010-semantic-regions-v1"
SEMANTIC_REGIONS_REVISION = 1

# Row-major homogeneous identity matrix.  The graph and mesh both use the
# temporary glTF-following basis, so no coordinate conversion is applied.
IDENTITY_EXPORT_MATRIX: tuple[float, ...] = (
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
)


class ExportError(Exception):
    """An export or export-validation failure with typed diagnostics."""

    def __init__(self, diagnostics: Iterable[Diagnostic]):
        self.diagnostics = tuple(diagnostics)
        super().__init__(
            "; ".join(f"{item.code} at {item.path}" for item in self.diagnostics)
        )


@dataclass(frozen=True)
class ExportValidationResult:
    """Structured proof that the identity export preserves the spike invariants."""

    ok: bool
    diagnostics: tuple[Diagnostic, ...]
    transform: tuple[float, ...]
    determinant: float
    landmark: dict[str, Any]
    mesh: dict[str, Any]


def _diagnostic(code: str, path: str, message: str) -> Diagnostic:
    # Export validation belongs to the pre-publication mesh/field gate in this
    # disposable host.  The existing diagnostic enum intentionally has no
    # permanent export phase.
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        phase=Phase.MESH,
        path=path,
        related_source_labels=(),
        message=message,
    )


def _matrix_array(matrix: Sequence[float]) -> np.ndarray:
    values = np.asarray(tuple(matrix), dtype=np.float64)
    if values.size != 16 or not np.all(np.isfinite(values)):
        raise ExportError(
            (_diagnostic("EXPORT_INVALID_TRANSFORM", "/export/transform", "transform must contain sixteen finite values"),)
        )
    return values.reshape(4, 4)


def _transform_point(matrix: np.ndarray, point: Sequence[float]) -> tuple[float, float, float]:
    value = np.asarray(tuple(point), dtype=np.float64)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ExportError(
            (_diagnostic("EXPORT_INVALID_LANDMARK", "/landmark/source_position", "landmark position must contain three finite values"),)
        )
    homogeneous = matrix @ np.array([value[0], value[1], value[2], 1.0], dtype=np.float64)
    if not np.all(np.isfinite(homogeneous)) or abs(float(homogeneous[3])) <= 1e-15:
        raise ExportError(
            (_diagnostic("EXPORT_INVALID_LANDMARK", "/landmark/export_position", "exported landmark is not finite"),)
        )
    return tuple(float(component / homogeneous[3]) for component in homogeneous[:3])


def _world_translation(graph: ResolvedGraph, label: str) -> tuple[float, float, float]:
    for node in graph.nodes:
        if node.node.label == label:
            matrix = np.asarray(node.world_matrix, dtype=np.float64).reshape(4, 4)
            position = matrix[:3, 3]
            if not np.all(np.isfinite(position)):
                raise ExportError(
                    (_diagnostic("EXPORT_INVALID_LANDMARK", f"/landmark/{label}", "world landmark is not finite"),)
                )
            return tuple(float(value) for value in position)
    raise ExportError(
        (_diagnostic("EXPORT_MISSING_LANDMARK", f"/landmark/{label}", "required asymmetric landmark is not resolved"),)
    )


def _mesh_checks(surface: SurfaceResult, matrix: np.ndarray, determinant: float) -> dict[str, Any]:
    vertices = np.asarray(surface.vertices, dtype=np.float64)
    normals = np.asarray(surface.normals, dtype=np.float64)
    faces = np.asarray(surface.faces, dtype=np.int64)
    finite_vertices = bool(vertices.ndim == 2 and vertices.shape[1:] == (3,) and np.all(np.isfinite(vertices)))
    finite_normals = bool(normals.ndim == 2 and normals.shape[1:] == (3,) and np.all(np.isfinite(normals)))
    finite_faces = bool(faces.ndim == 2 and faces.shape[1:] == (3,) and np.all(np.isfinite(faces)))
    counts_match = bool(len(vertices) == len(normals) and len(faces) > 0)
    valid_indices = bool(
        finite_faces
        and counts_match
        and np.all(faces >= 0)
        and np.all(faces < len(vertices))
    )
    transformed_vertices = np.empty_like(vertices)
    if finite_vertices:
        homogeneous = np.column_stack((vertices, np.ones(len(vertices), dtype=np.float64)))
        transformed = (matrix @ homogeneous.T).T
        valid_w = np.isfinite(transformed).all(axis=1) & (np.abs(transformed[:, 3]) > 1e-15)
        if np.all(valid_w):
            transformed_vertices = transformed[:, :3] / transformed[:, 3, None]
        else:
            finite_vertices = False
    signed_volume = float("nan")
    outward_winding = False
    face_normal_alignment = np.empty(0, dtype=np.float64)
    radial_alignment = np.empty(0, dtype=np.float64)
    directed_edge_orientation_mismatches = -1
    if finite_vertices and valid_indices:
        area_vectors = np.cross(
            transformed_vertices[faces[:, 1]] - transformed_vertices[faces[:, 0]],
            transformed_vertices[faces[:, 2]] - transformed_vertices[faces[:, 0]],
        )
        signed_volume = float(
            np.sum(np.einsum("ij,ij->i", transformed_vertices[faces[:, 0]], area_vectors)) / 6.0
        )
        centers = (
            transformed_vertices[faces[:, 0]]
            + transformed_vertices[faces[:, 1]]
            + transformed_vertices[faces[:, 2]]
        ) / 3.0
        centroid = np.mean(transformed_vertices, axis=0)
        alignment = np.einsum("ij,ij->i", area_vectors, centers - centroid)
        # Retain the centroid/radial alignment as an aggregate diagnostic only;
        # it is intentionally not an acceptance gate because a local winding
        # error can disappear in its mean.
        radial_alignment = alignment
        face_lengths = np.linalg.norm(area_vectors, axis=1)
        try:
            normal_transform = np.linalg.inv(matrix[:3, :3])
        except np.linalg.LinAlgError:
            normal_transform = np.full((3, 3), np.nan, dtype=np.float64)
        transformed_normals = normals @ normal_transform
        face_normals = (
            transformed_normals[faces[:, 0]]
            + transformed_normals[faces[:, 1]]
            + transformed_normals[faces[:, 2]]
        ) / 3.0
        face_normal_lengths = np.linalg.norm(face_normals, axis=1)
        face_normal_alignment = np.divide(
            np.einsum("ij,ij->i", area_vectors, face_normals),
            face_lengths * face_normal_lengths,
            out=np.full(len(faces), np.nan, dtype=np.float64),
            where=(face_lengths > FACE_AREA_TOLERANCE) & (face_normal_lengths > FACE_AREA_TOLERANCE),
        )
        nondegenerate = face_lengths > FACE_AREA_TOLERANCE
        directed_edge_orientation_mismatches = _directed_edge_orientation_mismatches(faces)
        outward_winding = bool(
            math.isfinite(signed_volume)
            and signed_volume > 0.0
            # Positive volume is only the global winding check.  Each
            # nondegenerate face must also agree with the exported vertex
            # normals at the documented cosine tolerance, so a local reversed
            # face cannot be hidden by the aggregate mean.  Shared edges must
            # also be oppositely directed between their two incident faces.
            and np.all(np.isfinite(face_normal_alignment[nondegenerate]))
            and np.all(face_normal_alignment[nondegenerate] >= FACE_ORIENTATION_ALIGNMENT_TOLERANCE)
            and directed_edge_orientation_mismatches == 0
            and float(determinant) > 0.0
        )
    minimum_face_normal_alignment = float("nan")
    mean_face_normal_alignment = float("nan")
    if face_normal_alignment.size:
        nondegenerate = np.isfinite(face_normal_alignment)
        if np.any(nondegenerate):
            minimum_face_normal_alignment = float(np.min(face_normal_alignment[nondegenerate]))
            mean_face_normal_alignment = float(np.mean(face_normal_alignment[nondegenerate]))
    radial_alignment_mean = float("nan")
    if radial_alignment.size and np.all(np.isfinite(radial_alignment)):
        radial_alignment_mean = float(np.mean(radial_alignment))
    checks = {
        "vertex_count": int(len(vertices)),
        "normal_count": int(len(normals)),
        "face_count": int(len(faces)),
        "finite_vertices": finite_vertices,
        "finite_normals": finite_normals,
        "finite_faces": finite_faces,
        "counts_match": counts_match,
        "valid_indices": valid_indices,
        "signed_volume": signed_volume,
        "outward_winding": outward_winding,
        "radial_alignment_mean": radial_alignment_mean,
        "directed_edge_orientation_mismatches": directed_edge_orientation_mismatches,
        "face_normal_alignment_minimum": minimum_face_normal_alignment,
        "face_normal_alignment_mean": mean_face_normal_alignment,
        "face_normal_alignment_tolerance": FACE_ORIENTATION_ALIGNMENT_TOLERANCE,
    }
    return checks


def validate_export(
    surface: SurfaceResult,
    graph: ResolvedGraph,
    *,
    transform: Sequence[float] = IDENTITY_EXPORT_MATRIX,
    landmark_label: str = "left_ear",
) -> ExportValidationResult:
    """Validate mesh and asymmetric-landmark invariants after export.

    The identity transform is the only adapter currently implemented.  A
    negative determinant is reported as a failure; this seam deliberately does
    not alter winding or normals for such a transform.
    """

    diagnostics: list[Diagnostic] = []
    try:
        matrix = _matrix_array(transform)
    except ExportError as error:
        return ExportValidationResult(False, error.diagnostics, tuple(transform), float("nan"), {}, {})
    determinant = float(np.linalg.det(matrix[:3, :3]))
    if not math.isfinite(determinant) or determinant <= 0.0:
        diagnostics.append(
            _diagnostic(
                "EXPORT_NEGATIVE_DETERMINANT",
                "/export/determinant",
                "export transform determinant must be positive; winding correction is not implemented",
            )
        )
    if not np.allclose(matrix[3], (0.0, 0.0, 0.0, 1.0), rtol=0.0, atol=1e-12):
        diagnostics.append(
            _diagnostic("EXPORT_INVALID_TRANSFORM", "/export/transform", "export transform must be affine homogeneous")
        )

    try:
        source_position = _world_translation(graph, landmark_label)
        export_position = _transform_point(matrix, source_position)
    except ExportError as error:
        diagnostics.extend(error.diagnostics)
        source_position = ()
        export_position = ()

    landmark_pass = bool(
        len(source_position) == 3
        and len(export_position) == 3
        and all(math.isfinite(value) for value in (*source_position, *export_position))
        and source_position[0] > 0.0
        and export_position[0] > 0.0
        and np.allclose(export_position, source_position, rtol=0.0, atol=0.0)
    )
    if not landmark_pass:
        diagnostics.append(
            _diagnostic(
                "EXPORT_ASYMMETRIC_LANDMARK_FAILED",
                f"/landmark/{landmark_label}",
                "left_ear must remain on positive X under the identity export",
            )
        )
    mesh = _mesh_checks(surface, matrix, determinant)
    for key, code, message in (
        ("finite_vertices", "EXPORT_MESH_NON_FINITE", "exported vertices must be finite"),
        ("finite_normals", "EXPORT_MESH_NON_FINITE", "exported normals must be finite"),
        ("finite_faces", "EXPORT_MESH_NON_FINITE", "exported faces must be finite"),
        ("counts_match", "EXPORT_MESH_COUNTS_INVALID", "mesh vertex and normal counts must match and faces must be non-empty"),
        ("valid_indices", "EXPORT_MESH_INDICES_INVALID", "mesh face indices must be valid"),
        (
            "outward_winding",
            "EXPORT_MESH_ORIENTATION_INVALID",
            "exported mesh must have positive volume, outward winding, and per-face normal alignment",
        ),
    ):
        if not mesh[key]:
            diagnostics.append(_diagnostic(code, "/mesh", message))

    landmark = {
        "label": landmark_label,
        "source_world_position": list(source_position),
        "export_position": list(export_position),
        "expected_rule": "left_ear world/export X > 0 and export position equals source under identity transform",
        "pass": landmark_pass,
    }
    return ExportValidationResult(
        ok=not diagnostics,
        diagnostics=tuple(diagnostics),
        transform=tuple(float(value) for value in matrix.reshape(-1)),
        determinant=determinant,
        landmark=landmark,
        mesh=mesh,
    )


def require_valid_export(
    surface: SurfaceResult,
    graph: ResolvedGraph,
    *,
    transform: Sequence[float] = IDENTITY_EXPORT_MATRIX,
    landmark_label: str = "left_ear",
) -> ExportValidationResult:
    """Return export proof or raise :class:`ExportError`."""

    result = validate_export(
        surface,
        graph,
        transform=transform,
        landmark_label=landmark_label,
    )
    if not result.ok:
        raise ExportError(result.diagnostics)
    return result


def _format_float(value: float) -> str:
    """Format one finite float with explicit, locale-independent round-trip precision."""

    number = float(value)
    if not math.isfinite(number):
        raise ExportError((_diagnostic("EXPORT_NON_FINITE_VALUE", "/mesh", "PLY values must be finite"),))
    # 17 significant digits round-trip every IEEE-754 binary64 value.  Python's
    # format grammar is locale-independent and emits a stable ASCII token.
    return format(number, ".17g")


def serialize_ply(surface: SurfaceResult) -> bytes:
    """Serialize vertices, outward normals, and triangular faces as ASCII PLY 1.0."""

    vertices = surface.vertices
    normals = surface.normals
    faces = surface.faces
    if len(vertices) != len(normals) or not faces:
        raise ExportError(
            (_diagnostic("EXPORT_MESH_COUNTS_INVALID", "/mesh", "PLY mesh counts are invalid"),)
        )
    lines = [
        "ply",
        "format ascii 1.0",
        "comment CK-KICK-010 deterministic ASCII mesh",
        f"element vertex {len(vertices)}",
        "property double x",
        "property double y",
        "property double z",
        "property double nx",
        "property double ny",
        "property double nz",
        f"element face {len(faces)}",
        "property list uchar int vertex_indices",
        "end_header",
    ]
    for vertex, normal in zip(vertices, normals):
        if len(vertex) != 3 or len(normal) != 3:
            raise ExportError((_diagnostic("EXPORT_MESH_COUNTS_INVALID", "/mesh", "PLY vertices and normals must be three-dimensional"),))
        lines.append(" ".join(_format_float(value) for value in (*vertex, *normal)))
    vertex_count = len(vertices)
    for face in faces:
        if len(face) != 3 or any(isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= vertex_count for index in face):
            raise ExportError((_diagnostic("EXPORT_MESH_INDICES_INVALID", "/mesh/faces", "PLY faces must contain three valid vertex indices"),))
        lines.append(f"3 {face[0]} {face[1]} {face[2]}")
    return ("\n".join(lines) + "\n").encode("ascii")


def semantic_regions_bytes(surface: SurfaceResult) -> bytes:
    """Serialize winner-only source attribution in PLY vertex order."""

    if len(surface.vertices) != len(surface.source_labels):
        raise ExportError(
            (_diagnostic("EXPORT_ATTRIBUTION_INVALID", "/semantic_regions/source_node_labels", "one source label is required per PLY vertex"),)
        )
    payload = {
        "format": SEMANTIC_REGIONS_FORMAT,
        "revision": SEMANTIC_REGIONS_REVISION,
        "mesh_vertex_indices": "artifact-local",
        "mesh_vertex_indices_are_artifact_local": True,
        "durable_semantic_identity": "not-claimed",
        "attribution_mode": "winner-only raw-field source label",
        "source_node_labels": list(surface.source_labels),
    }
    from .artifacts import canonical_json_bytes

    return canonical_json_bytes(payload)


def export_transform_metadata(
    result: ExportValidationResult,
) -> dict[str, Any]:
    """Return deterministic manifest metadata for the validated export."""

    matrix = np.asarray(result.transform, dtype=np.float64).reshape(4, 4)
    return {
        "format": EXPORT_FORMAT,
        "basis": "identity in resolver glTF-following coordinate convention",
        "matrix": [list(float(value) for value in row) for row in matrix],
        "determinant": float(result.determinant),
        "landmark_verification": result.landmark,
        "mesh_validation": result.mesh,
    }


__all__ = [
    "EXPORT_FORMAT",
    "ExportError",
    "ExportValidationResult",
    "IDENTITY_EXPORT_MATRIX",
    "SEMANTIC_REGIONS_FORMAT",
    "SEMANTIC_REGIONS_REVISION",
    "export_transform_metadata",
    "require_valid_export",
    "semantic_regions_bytes",
    "serialize_ply",
    "validate_export",
]

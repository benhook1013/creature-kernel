#!/usr/bin/env python3
"""Project non-rendered structural-ingredient evidence into an immutable view.

This is a disposable experiment consumer.  It does not read or write the
gallery itself: the developer-tool validator owns all gallery I/O and exact
validation, including the complete rendered gallery source, and this module
only projects its returned non-rendered structural records. Rendered gallery
PNGs, canvas metadata, and display metadata are intentionally outside this
view and are not prospective runtime ingredients.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPOSITORY_ROOT / "dev-tools" / "visual-review" / "publish_structural_embodiment.py"
PROJECTION_CONTRACT = "non-rendered-structural-ingredient-evidence-v1"
EXCLUDED_RENDERED_EVIDENCE = (
    "rendered_gallery_pngs",
    "gallery_canvas",
    "display_metadata",
)
UNAVAILABLE_ORIGINAL_INSPECT_STRUCTURE_BYTES = "original_inspect_structure_bytes"
UNAVAILABLE_PER_VERTEX_SEMANTIC_LABELS = "per_vertex_semantic_labels"
UNAVAILABLE_EVIDENCE = (
    UNAVAILABLE_ORIGINAL_INSPECT_STRUCTURE_BYTES,
    UNAVAILABLE_PER_VERTEX_SEMANTIC_LABELS,
)
_VALIDATOR_MODULE: ModuleType | None = None

Vector = tuple[float, float, float]
Bounds = tuple[Vector, Vector]


@dataclass(frozen=True, slots=True)
class ArtifactEvidence:
    """One validator-declared non-rendered structural artifact identity."""

    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True, slots=True)
class MetricsEvidence:
    """Existing scalar and bound metrics retained from one profile record."""

    format: str
    profile_id: str
    neutral_vertex_count: int
    posed_vertex_count: int
    face_count: int
    bone_count: int
    proxy_count: int
    neutral_bounds: Bounds
    posed_bounds: Bounds
    pose_rule_count: int
    source_joint_frame_policy: str
    gallery_global_world_bound: Bounds


@dataclass(frozen=True, slots=True)
class ProfileIdentityEvidence:
    """Hash and byte evidence carried for one generated profile."""

    source_document: str
    source_namespace: str
    source_candidate_sha256: str
    source_request_sha256: str
    bridge_manifest_sha256: str
    bridge_json_sha256: str
    neutral_source_sha256: str
    neutral_source_bytes: int
    structure_source_sha256: str
    structure_source_bytes: int
    generated_source: ArtifactEvidence
    candidate_profile_sha256: str


@dataclass(frozen=True, slots=True)
class StructuralProfileEvidence:
    """Validated evidence and declared artifact identities for one profile."""

    profile_id: str
    label: str
    identity: ProfileIdentityEvidence
    neutral_mesh: ArtifactEvidence
    posed_mesh: ArtifactEvidence
    skeleton: ArtifactEvidence
    weights: ArtifactEvidence
    neutral_proxies: ArtifactEvidence
    posed_proxies: ArtifactEvidence
    metrics: MetricsEvidence


@dataclass(frozen=True, slots=True)
class StructuralGalleryEvidenceView:
    """Immutable non-rendered structural ingredients for later assessment.

    This view deliberately excludes rendered gallery PNGs, canvas metadata,
    and display metadata even though the shared validator validates the full
    source gallery before this projection is built.
    """

    projection_contract: str
    manifest_sha256: str
    manifest_bytes: int
    profile_ids: tuple[str, ...]
    pose_id: str
    pose_sha256: str
    pose_artifact: ArtifactEvidence
    candidate_table: ArtifactEvidence
    source_manifest: ArtifactEvidence
    base_source_sha256: str
    lineage: tuple[tuple[str, str | tuple[tuple[str, str], ...]], ...]
    boundary: str
    global_world_bound: Bounds
    profiles: tuple[StructuralProfileEvidence, ...]
    unavailable_evidence: tuple[str, ...] = UNAVAILABLE_EVIDENCE


def _load_validator() -> tuple[
    ModuleType,
    Callable[[Path], tuple[dict[str, Any], dict[str, dict[str, Any]], str, int]],
    type[Exception],
]:
    global _VALIDATOR_MODULE
    if _VALIDATOR_MODULE is not None:
        return (
            _VALIDATOR_MODULE,
            _VALIDATOR_MODULE.validate_structural_embodiment_gallery,
            _VALIDATOR_MODULE.StructuralEmbodimentPublishError,
        )

    sibling_module_path = str(VALIDATOR_PATH.parent)
    if sibling_module_path not in sys.path:
        sys.path.insert(0, sibling_module_path)
    spec = importlib.util.spec_from_file_location("structural_gallery_publisher_for_evidence", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load structural gallery validator from {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _VALIDATOR_MODULE = module
    return module, module.validate_structural_embodiment_gallery, module.StructuralEmbodimentPublishError


def _artifact(value: dict[str, Any]) -> ArtifactEvidence:
    return ArtifactEvidence(path=value["path"], sha256=value["sha256"], bytes=value["bytes"])


def _bounds(value: dict[str, Any]) -> Bounds:
    return tuple(tuple(axis) for axis in (value["min"], value["max"]))  # type: ignore[return-value]


def _lineage(value: dict[str, Any]) -> tuple[tuple[str, str | tuple[tuple[str, str], ...]], ...]:
    scenario = value["scenario"]
    return (
        ("source", value["source"]),
        ("build", value["build"]),
        (
            "scenario",
            tuple((key, scenario[key]) for key in ("id", "surface_variant_id", "pose_id")),
        ),
    )


def _metrics(value: dict[str, Any]) -> MetricsEvidence:
    return MetricsEvidence(
        format=value["format"],
        profile_id=value["profile_id"],
        neutral_vertex_count=value["neutral_vertex_count"],
        posed_vertex_count=value["posed_vertex_count"],
        face_count=value["face_count"],
        bone_count=value["bone_count"],
        proxy_count=value["proxy_count"],
        neutral_bounds=_bounds(value["neutral_bounds"]),
        posed_bounds=_bounds(value["posed_bounds"]),
        pose_rule_count=value["pose_rule_count"],
        source_joint_frame_policy=value["source_joint_frame_policy"],
        gallery_global_world_bound=_bounds(value["gallery_global_world_bound"]),
    )


def _profile(profile: dict[str, Any], validator_module: ModuleType) -> StructuralProfileEvidence:
    profile_id = profile["id"]
    artifacts = {item["path"]: item for item in profile["artifacts"]}
    profile_artifacts = tuple(
        _artifact(artifacts[f"{profile_id}/{name}"])
        for name in validator_module.PROFILE_ARTIFACT_NAMES
    )
    (
        neutral_mesh,
        posed_mesh,
        skeleton,
        weights,
        neutral_proxies,
        posed_proxies,
        _metrics_artifact,
        _gallery_artifact,
    ) = profile_artifacts
    identity_source = profile["source"]
    identity = ProfileIdentityEvidence(
        source_document=identity_source["document"],
        source_namespace=identity_source["namespace"],
        source_candidate_sha256=identity_source["candidate_sha256"],
        source_request_sha256=identity_source["request_sha256"],
        bridge_manifest_sha256=profile["bridge_manifest_sha256"],
        bridge_json_sha256=profile["bridge_json_sha256"],
        neutral_source_sha256=profile["neutral_source_sha256"],
        neutral_source_bytes=profile["neutral_source_bytes"],
        structure_source_sha256=profile["structure_source_sha256"],
        structure_source_bytes=profile["structure_source_bytes"],
        generated_source=_artifact({
            "path": profile["generated_source_path"],
            "sha256": profile["generated_source_sha256"],
            "bytes": profile["generated_source_bytes"],
        }),
        candidate_profile_sha256=profile["candidate_profile_sha256"],
    )
    return StructuralProfileEvidence(
        profile_id=profile_id,
        label=profile["label"],
        identity=identity,
        neutral_mesh=neutral_mesh,
        posed_mesh=posed_mesh,
        skeleton=skeleton,
        weights=weights,
        neutral_proxies=neutral_proxies,
        posed_proxies=posed_proxies,
        metrics=_metrics(profile["metrics"]),
    )


def project_structural_gallery_evidence(gallery: Path) -> StructuralGalleryEvidenceView | None:
    """Return a view only when the shared exact gallery validator succeeds."""
    validator_module, validator, rejection_type = _load_validator()
    try:
        manifest, profiles_by_id, manifest_sha256, manifest_bytes = validator(Path(gallery).absolute())
    except rejection_type:
        return None

    inventory = {item["path"]: item for item in manifest["artifacts"]}
    return StructuralGalleryEvidenceView(
        projection_contract=PROJECTION_CONTRACT,
        manifest_sha256=manifest_sha256,
        manifest_bytes=manifest_bytes,
        profile_ids=tuple(manifest["profile_ids"]),
        pose_id=manifest["pose_id"],
        pose_sha256=manifest["pose_sha256"],
        pose_artifact=_artifact(inventory[validator_module.POSE_FILE]),
        candidate_table=_artifact(inventory[manifest["candidate_table"]["path"]]),
        source_manifest=_artifact(inventory[manifest["source_manifest"]["path"]]),
        base_source_sha256=manifest["source_manifest"]["base_source_sha256"],
        lineage=_lineage(manifest["lineage"]),
        boundary=manifest["boundary"],
        global_world_bound=_bounds(manifest["global_world_bound"]),
        profiles=tuple(
            _profile(profiles_by_id[profile_id], validator_module)
            for profile_id in manifest["profile_ids"]
        ),
    )


load_structural_gallery_evidence = project_structural_gallery_evidence
